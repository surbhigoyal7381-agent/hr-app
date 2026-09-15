"""Slice 010 group D, phase 3: pin tests for what screens outside the review may
show, HR's cycle screens, the reviewer picker, the lock reminder and the copy of
existing reviews (commits 8, 9, 10 and 12; decisions 26 and 28).

Requirements: docs/slices/010-portal-security-fixes/00c (R1-R16), 00d (strategy),
01d (VIS / SEC / PRIV) and 00e (the approved decisions, which win).

Each test is named after the rule it keeps closed, so a merge that drops a fix
fails CI here. Refusals are tested, not only the allowed path. Synthetic people
and records only, tagged S010D.
"""

import importlib
import json
import os
import re

import frappe

from alvoraa_portal.tests.test_review_copies_010d import _day, _row_for, _shipped_permissions, _Team, _uid

RATING_FIELDS = ("self_rating", "self_comment", "manager_rating", "manager_comment",
                 "potential_rating", "potential_comment")


def _source(app, *path):
	"""A source file read the way Python reads it: a byte-order mark is not code."""
	root = os.path.dirname(importlib.import_module(app).__file__)
	with open(os.path.join(root, *path), encoding="utf-8-sig") as f:
		return f.read()


def _legacy_ratings(kpi, **values):
	"""Ratings an earlier cycle stored on the live KPI, written the one way still allowed."""
	from alvoraa_goals.controllers.kpi import RATING_REPAIR_FLAG

	doc = frappe.get_doc("KPI", kpi)
	doc.update(values)
	doc.flags[RATING_REPAIR_FLAG] = True
	doc.save(ignore_permissions=True)
	frappe.db.commit()


# ── Commit 8 · SEC-2, PRIV-9 · nobody writes or sees ratings on a live KPI ───


class TestSec2RatingsNeverChangeOnTheLiveKpi(_Team):
	def test_sec2_rating_fields_sit_at_level_1_and_nobody_is_given_write_there(self):
		doctype = _shipped_permissions("alvoraa_goals", "alvoraa_goals", "doctype", "kpi", "kpi.json")
		level_one = [p for p in doctype if p.get("permlevel") == 1]
		self.assertEqual({p["role"] for p in level_one}, {"HR Manager", "HR User", "System Manager"})
		self.assertFalse([p for p in level_one if p.get("write") or p.get("create")])

		meta = frappe.get_meta("KPI")
		for field in (*RATING_FIELDS, "additional_reviewers"):
			self.assertEqual(meta.get_field(field).permlevel, 1, field)

	def test_sec2_nobody_writes_a_rating_on_a_live_kpi_by_any_path(self):
		from frappe.client import set_value as desk_set_value

		cycle = self._cycle()
		self._as(self.subject_user)
		own = frappe.get_doc({"doctype": "KPI", "kpi_name": f"S010D own {_uid()}", "employee": self.subject,
		                      "appraisal_cycle": cycle, "target_value": 10}).insert()
		frappe.set_user("Administrator")
		self._cleanup.append(("KPI", own.name))
		frappe.db.commit()
		_legacy_ratings(own.name, manager_rating=3, potential_rating=2)

		# Creator, manager, HR Manager and System Manager through the desk or REST:
		# Frappe resets a level-1 field they may not write, or the guard refuses.
		for user in (self.subject_user, self.manager_user, self.hr_user, self.sysman_user):
			self._as(user)
			try:
				desk_set_value("KPI", own.name, "manager_rating", 5)
			except (frappe.PermissionError, frappe.ValidationError):
				pass
			frappe.db.rollback()
			frappe.set_user("Administrator")
			self.assertEqual(frappe.db.get_value("KPI", own.name, "manager_rating"), 3, user)

		# Code that skips permissions, validation, or both; and Administrator.
		for flags in ({}, {"ignore_validate": True}):
			doc = frappe.get_doc("KPI", own.name)
			doc.potential_rating = 5
			doc.flags.update(flags)
			with self.assertRaises(frappe.PermissionError, msg=str(flags)):
				doc.save(ignore_permissions=True)
			frappe.db.rollback()

		doc = frappe.get_doc("KPI", own.name)
		doc.append("additional_reviewers", {"reviewer": self.stranger, "rating": 4})
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)
		frappe.db.rollback()

		rated_new = frappe.get_doc({"doctype": "KPI", "kpi_name": f"S010D new {_uid()}", "employee": self.subject,
		                            "target_value": 10, "self_rating": 4})
		with self.assertRaises(frappe.PermissionError):
			rated_new.insert(ignore_permissions=True)
		frappe.db.rollback()

		self.assertEqual(frappe.db.get_value("KPI", own.name, ["manager_rating", "potential_rating"]), (3, 2))

		# A fact still saves, and a save that leaves the old ratings alone passes.
		doc = frappe.get_doc("KPI", own.name)
		doc.actual_value = 7
		doc.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("KPI", own.name, "actual_value"), 7)

	def test_sec2_static_no_code_writes_kpi_ratings_around_the_document(self):
		pattern = re.compile(r"set_value\(\s*[\"']KPI[\"'][^\n]*(" + "|".join(RATING_FIELDS) + ")")
		sql = re.compile(r"update\s+`?tabKPI`?\s+set[^\n]*(" + "|".join(RATING_FIELDS) + ")", re.IGNORECASE)
		scanned = 0
		for app, folder in (("alvoraa_portal", ""), ("alvoraa_goals", ""), ("hrms", "alvoraa_hr_core")):
			root = os.path.join(os.path.dirname(importlib.import_module(app).__file__), folder)
			for dirpath, _dirs, files in os.walk(root):
				if "tests" in dirpath.split(os.sep):
					continue
				for name in files:
					if not name.endswith(".py"):
						continue
					with open(os.path.join(dirpath, name), encoding="utf-8-sig") as f:
						text = f.read()
					scanned += 1
					self.assertFalse(pattern.search(text), name)
					self.assertFalse(sql.search(text), name)
		self.assertGreater(scanned, 20)


class TestPriv9KpiRatingsHiddenFromEmployeesAndManagers(_Team):
	def test_priv9_only_hr_reads_the_old_ratings_on_a_live_kpi(self):
		from frappe.client import get as desk_get

		kpi = self._kpi(self.subject, self._cycle(), target=10)
		_legacy_ratings(kpi, manager_rating=4, potential_rating=5, self_comment="S010D-marker")

		for user in (self.subject_user, self.manager_user):
			self._as(user)
			doc = desk_get("KPI", kpi)
			self.assertFalse({"manager_rating", "potential_rating", "self_comment"} & {
				k for k, v in doc.items() if v not in (None, "", 0)}, user)
			try:
				rows = frappe.get_list("KPI", filters={"name": kpi}, fields=["name", "potential_rating"])
			except frappe.PermissionError:
				rows = []
			for row in rows:
				self.assertFalse(row.get("potential_rating"), user)

		self._as(self.hr_user)
		self.assertEqual(desk_get("KPI", kpi)["potential_rating"], 5)


# ── Decision 26 · Employee has no permission on HRMS Appraisal ──────────────


class TestDecision26EmployeeCannotReadHrmsAppraisal(_Team):
	def test_decision26_employee_reads_appraisals_only_through_the_portal(self):
		from frappe.client import get as desk_get

		shipped = _shipped_permissions("hrms", "hr", "doctype", "appraisal", "appraisal.json")
		self.assertNotIn("Employee", {p["role"] for p in shipped})
		self.assertNotIn("Employee", {p.role for p in frappe.get_meta("Appraisal").permissions})

		ap = self._review_of(self.subject, "Employee Review")
		self._as(self.subject_user)
		with self.assertRaises(frappe.PermissionError):
			desk_get("Appraisal", ap)

		# The portal's own self-assessment save still works for the owner, and
		# only for the owner.
		import alvoraa_portal.goals_api as goals_api

		goals_api.save_self_assessment(ap, "<p>S010D reflections</p>")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Appraisal", ap, "reflections"), "<p>S010D reflections</p>")
		self._as(self.manager_user)
		with self.assertRaises(frappe.PermissionError):
			goals_api.save_self_assessment(ap, "not mine")


class TestR8DeskListsAreLabelled(_Team):
	def test_r8_vis12_desk_lists_say_they_are_live_records(self):
		for doctype, path in (("KPI", ("kpi", "kpi_list.js")),
		                      ("Individual Goal", ("individual_goal", "individual_goal_list.js"))):
			text = _source("alvoraa_goals", "alvoraa_goals", "doctype", *path)
			self.assertIn(f'frappe.listview_settings["{doctype}"]', text)
			self.assertIn('add_inner_message(__("Live records, not the review record"))', text)


# ── Commit 8 · R14, PRIV-9, R5, PRIV-10 · outside screens and the badge ─────


ITEM_SCORE_KEYS = set(RATING_FIELDS) | {"rated_count", "score", "score_earned", "goal_score"}
TOTAL_KEYS = ("total_score", "self_score", "avg_feedback_score", "final_score")


def _keys(value):
	from alvoraa_portal.tests.test_portal_security_010 import _all_keys

	return _all_keys(value)


class _Outside(_Team):
	"""The subject's review in Manager Review, its copies rated, and old ratings
	still stored on the live KPI."""

	def _rated_review(self, status="Manager Review", start=None, end=None):
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		if not start:
			start, end = self._window()
		cycle = self._cycle(start, end)
		goal = self._goal(self.subject, cycle, start, end, target=100)
		kpi = self._kpi(self.subject, cycle, target=100, goal=goal)
		self._reading(kpi, _day(start, 1), 40)
		_legacy_ratings(kpi, self_rating=3, manager_rating=4, potential_rating=5, manager_comment="S010D-old")
		ap = self._appraisal(self.subject, cycle, status="Employee Review")
		self._as(self.subject_user)
		pa.get_my_review(ap)
		frappe.set_user("Administrator")
		ext = self._ext(ap)
		for row in ext.review_items:
			row.self_rating, row.manager_rating, row.potential_rating = 3, 4, 5
			review_items.stamp_rating(row, "self")
			review_items.stamp_rating(row, "manager")
		review_items.save_review_record(ext)
		frappe.db.set_value("Appraisal", ap, {"total_score": 3.5, "final_score": 3.7})
		frappe.db.commit()
		self._set_status(ap, status)
		return frappe._dict(ap=ap, cycle=cycle, goal=goal, kpi=kpi, start=start, end=end)


class TestR14OutsideScreensShowNoItemRating(_Outside):
	def test_r14_priv9_outside_payloads_carry_no_objective_or_kpi_rating(self):
		import alvoraa_portal.performance_api as pa

		r = self._rated_review()
		payloads = []
		self._as(self.subject_user)
		payloads += [pa.get_my_kpis(cycle=r.cycle), pa.get_performance_tree(cycle=r.cycle, scope="mine"),
		             pa.get_cycle_items(r.cycle), pa.get_my_appraisal(r.cycle), pa.get_appraisal(r.ap)]
		self._as(self.manager_user)
		payloads += [pa.get_team_kpis(cycle=r.cycle), pa.get_performance_tree(cycle=r.cycle, scope="team"),
		             pa.get_cycle_items(r.cycle, self.subject), pa.get_team_appraisal(self.subject, r.cycle),
		             pa.get_appraisal(r.ap)]
		self._as(self.hr_user)
		payloads.append(pa.get_performance_tree(cycle=r.cycle, scope="organisation"))

		for payload in payloads:
			self.assertFalse(ITEM_SCORE_KEYS & _keys(payload), sorted(ITEM_SCORE_KEYS & _keys(payload)))
			self.assertNotIn("S010D-old", json.dumps(payload, default=str))
		self.assertFalse({"self_rating", "manager_rating", "potential_rating"} & set(pa.KPI_FIELDS))

	def test_priv9_the_appraisal_summary_has_no_item_score_and_totals_follow_the_release_rule(self):
		import alvoraa_portal.goals_api as goals_api
		import alvoraa_portal.performance_api as pa

		r = self._rated_review(start="2999-01-01", end="2999-03-31")

		def totals(payload):
			return tuple(payload["appraisal"].get(k) for k in ("total_score", "final_score"))

		self._as(self.subject_user)
		self.assertEqual(totals(pa.get_my_appraisal(r.cycle)), (None, None))
		self.assertEqual(totals(pa.get_appraisal(r.ap)), (None, None))
		data = goals_api.get_appraisal_data()
		if data.get("appraisal") and data["appraisal"]["name"] == r.ap:
			self.assertEqual(totals(data), (None, None))
		own = next(x for x in pa.list_appraisals()["appraisals"] if x["name"] == r.ap)
		self.assertEqual((own["total_score"], own["final_score"]), (None, None))

		self._as(self.manager_user)
		self.assertEqual(totals(pa.get_team_appraisal(self.subject, r.cycle)), (3.5, 3.7))
		line = next(x for x in pa.list_appraisals()["appraisals"] if x["name"] == r.ap)
		self.assertEqual(line["total_score"], 3.5)

		self._as(self.hr_user)
		outside = next(x for x in pa.list_appraisals()["appraisals"] if x["name"] == r.ap)
		self.assertEqual(outside["total_score"], None)

		self._set_status(r.ap, "Employee Final Review")
		self._as(self.subject_user)
		self.assertEqual(totals(pa.get_my_appraisal(r.cycle)), (3.5, 3.7))
		data = goals_api.get_appraisal_data()
		if data.get("appraisal") and data["appraisal"]["name"] == r.ap:
			self.assertEqual(totals(data), (3.5, 3.7))
			self.assertFalse(ITEM_SCORE_KEYS & _keys(data))

		self._set_status(r.ap, "HR Review")
		self._as(self.hr_user)
		outside = next(x for x in pa.list_appraisals()["appraisals"] if x["name"] == r.ap)
		self.assertEqual(outside["total_score"], 3.5)

	def test_vis3_get_cycle_items_uses_the_copies_once_the_caller_may_open_the_review(self):
		import alvoraa_portal.performance_api as pa

		r = self._rated_review()
		rows = {x.name for x in self._ext(r.ap).review_items}
		self._as(self.manager_user)
		items = pa.get_cycle_items(r.cycle, self.subject)
		self.assertEqual(items["source"], "review")
		self.assertEqual({i["name"] for i in items["goals"] + items["kpis"]}, rows)
		text = json.dumps(items, default=str)
		self.assertNotIn(r.kpi, text)
		self.assertNotIn(r.goal, text)

		# While the self-review is a draft the manager gets the live list (PRIV-2),
		# still with no rating.
		self._set_status(r.ap, "Employee Review")
		self._as(self.manager_user)
		self.assertEqual(pa.get_cycle_items(r.cycle, self.subject)["source"], "live")

		# HR for another company is refused, and so is a manager for someone else's report.
		self._as(self.hr_user)
		with self.assertRaises(frappe.PermissionError):
			pa.get_cycle_items(r.cycle, self.subject_b)
		with self.assertRaises(frappe.PermissionError):
			pa.get_team_appraisal(self.subject_b, r.cycle)
		self._as(self.stranger_user)
		with self.assertRaises(frappe.PermissionError):
			pa.get_cycle_items(r.cycle, self.subject)


class TestR5Priv10InReviewBadge(_Outside):
	def test_r5_priv10_the_badge_says_in_review_and_the_period_end_and_nothing_else(self):
		import alvoraa_portal.goals_api as goals_api
		import alvoraa_portal.hr_api as hr_api
		import alvoraa_portal.performance_api as pa

		r = self._rated_review()
		free = self._kpi(self.subject, r.cycle, target=10)   # tagged to the cycle, not in the review
		expected = {"in_review": 1, "updates_after": str(r.end)}

		self._as(self.manager_user)
		tree = pa.get_performance_tree(cycle=r.cycle, scope="team")
		kpis = {k["name"]: k for g in tree["roots"] for k in g["kpis"]}
		kpis.update({k["name"]: k for k in tree["unattached_kpis"]})
		goals = {g["name"]: g for g in tree["roots"]}
		self.assertEqual(kpis[r.kpi]["review_badge"], expected)
		self.assertEqual(goals[r.goal]["review_badge"], expected)
		self.assertEqual(kpis[r.kpi]["in_cycle"], r.cycle)
		self.assertIsNone(kpis[free]["review_badge"])
		self.assertEqual(kpis[free]["in_cycle"], "")

		self._as(self.subject_user)
		mine = {k["name"]: k for k in pa.get_my_kpis(cycle=r.cycle)["kpis"]}
		self.assertEqual(mine[r.kpi]["review_badge"], expected)
		self.assertEqual(goals_api.get_goal_detail(r.goal)["review_badge"], expected)
		self.assertEqual(hr_api.get_goal_detail(r.goal)["goal"]["review_badge"], expected)

		# A completed review holds nothing: no badge.
		self._set_status(r.ap, "Completed")
		self._as(self.subject_user)
		mine = {k["name"]: k for k in pa.get_my_kpis(cycle=r.cycle)["kpis"]}
		self.assertIsNone(mine[r.kpi]["review_badge"])
