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


# ── Commit 8 · R8, SEC-26, SEC-30 · HR cycle screens read the review record ──


class _CycleScreens(_Team):
	"""One cycle: the subject's review in Manager Review, the stranger's in HR
	Review (frozen, with a fact approved after), another company's in HR Review,
	and an HR Manager's own review in HR Review."""

	MARK = "S010D-comment"

	def _review_in(self, cycle, start, employee, status, freeze=False):
		import alvoraa_goals.review_items as review_items

		kpi = self._kpi(employee, cycle, target=100, weightage=100)
		self._reading(kpi, _day(start, 1), 40)
		ap = self._appraisal(employee, cycle, status="Employee Review")
		review_items.ensure_review_items(self._ext(ap))
		ext = self._ext(ap)
		for row in ext.review_items:
			row.self_rating, row.manager_rating, row.potential_rating = 3, 4, 5
			row.self_comment = row.manager_comment = self.MARK
			review_items.stamp_rating(row, "self")
			review_items.stamp_rating(row, "manager")
		ext.overall_rating, ext.potential_rating = 4, 5
		review_items.stamp_overall_rating(ext)
		if freeze:
			ext.frozen, ext.frozen_on = 1, frappe.utils.now_datetime()
		review_items.save_review_record(ext)
		frappe.db.commit()
		self._set_status(ap, status)
		return frappe._dict(ap=ap, kpi=kpi, row=_row_for(self._ext(ap), kpi).name)

	def _setup_cycle(self):
		start, end = self._window()
		cycle = self._cycle(start, end)
		c = frappe._dict(cycle=cycle, start=start)
		c.mr = self._review_in(cycle, start, self.subject, "Manager Review")
		c.hrr = self._review_in(cycle, start, self.stranger, "HR Review", freeze=True)
		c.other = self._review_in(cycle, start, self.subject_b, "HR Review")
		c.own = self._review_in(cycle, start, self.hr_subject, "HR Review")
		# Dated in the period, approved after the frozen review stopped taking facts (R10).
		self._reading(c.hrr.kpi, _day(start, 3), 15,
		              approved_on=frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=1))
		return c


class TestR8Sec26HrCycleScreens(_CycleScreens):
	def test_sec26_hr_cycle_screens_list_only_permitted_companies_and_follow_the_stage(self):
		import alvoraa_portal.performance_api as pa

		c = self._setup_cycle()
		self._as(self.hr_user)

		table = {r["name"]: r for r in pa.hr_list_appraisals(c.cycle)}
		self.assertTrue({c.mr.ap, c.hrr.ap, c.own.ap} <= set(table))
		self.assertNotIn(c.other.ap, table)
		self.assertIsNone(table[c.mr.ap]["overall_rating"])
		self.assertEqual(table[c.hrr.ap]["overall_rating"], 4)

		kpis = {r["name"]: r for r in pa.hr_list_kpis(c.cycle)}
		self.assertEqual(set(kpis) & {c.mr.row, c.hrr.row, c.other.row}, {c.mr.row, c.hrr.row})
		self.assertFalse(set(RATING_FIELDS) & set(kpis[c.mr.row]))
		self.assertEqual((kpis[c.hrr.row]["manager_rating"], kpis[c.hrr.row]["potential_rating"]), (4, 5))
		text = json.dumps(list(kpis.values()), default=str)
		for live in (c.mr.kpi, c.hrr.kpi):
			self.assertNotIn(live, text)

		summary = {r["appraisal"]: r for r in pa.hr_cycle_summary(c.cycle)["rows"]}
		self.assertNotIn(c.other.ap, summary)
		self.assertFalse({"final_score", "rated"} & set(summary[c.mr.ap]))
		self.assertEqual(summary[c.hrr.ap]["rated"], 1)

		overview = {r["appraisal"]: r for r in pa.get_calibration_overview(c.cycle)["rows"]}
		self.assertNotIn(c.other.ap, overview)
		self.assertFalse({"overall_rating", "avg_potential_rating", "avg_potential", "rated_count",
		                  "potential_category"} & set(overview[c.mr.ap]))
		self.assertEqual(overview[c.hrr.ap]["overall_rating"], 4)
		self.assertEqual(overview[c.mr.ap]["kpi_count"], 1)

		matrix = pa.get_calibration_matrix(c.cycle)
		self.assertEqual({r["appraisal"] for r in matrix["rows"]} & {c.mr.ap, c.hrr.ap, c.other.ap, c.own.ap},
		                 {c.hrr.ap, c.own.ap})

	def test_r8_sec26_the_csv_export_holds_copies_only_what_the_stage_allows_and_logs_counts(self):
		import csv
		import io
		from unittest.mock import MagicMock, patch

		import alvoraa_portal.performance_api as pa

		c = self._setup_cycle()
		logger = MagicMock()
		self._as(self.hr_user)
		with patch("frappe.logger", return_value=logger):
			result = pa.export_cycle_kpis_csv(c.cycle)
		rows = list(csv.DictReader(io.StringIO(result["csv"])))
		by_id = {r["KPI ID"]: r for r in rows}

		self.assertNotIn(c.other.row, by_id)
		for live in (c.mr.kpi, c.hrr.kpi, c.other.kpi):
			self.assertNotIn(live, result["csv"])
		self.assertEqual((by_id[c.mr.row]["Manager Rating"], by_id[c.mr.row]["Self Comment"],
		                  by_id[c.mr.row]["Potential Rating"]), ("", "", ""))
		self.assertEqual(float(by_id[c.hrr.row]["Manager Rating"]), 4)
		self.assertEqual(by_id[c.hrr.row]["Facts Approved After Close"], "1")
		self.assertEqual(by_id[c.mr.row]["Facts Approved After Close"], "0")

		logged = [json.loads(call.args[0]) for call in logger.info.call_args_list]
		self.assertEqual([(e["event"], e["rows"]) for e in logged], [("export", len(rows))])
		self.assertNotIn(self.MARK, json.dumps(logged))

	def test_priv1_sec26_your_own_row_on_hr_screens_never_carries_potential(self):
		import alvoraa_portal.performance_api as pa

		c = self._setup_cycle()
		self._as(self.hr_subject_user)
		own_kpi = next(r for r in pa.hr_list_kpis(c.cycle) if r["name"] == c.own.row)
		self.assertNotIn("potential_rating", own_kpi)
		own = next(r for r in pa.get_calibration_overview(c.cycle)["rows"] if r["appraisal"] == c.own.ap)
		self.assertFalse({"avg_potential", "avg_potential_rating", "potential_category"} & set(own))
		plotted = next(r for r in pa.get_calibration_matrix(c.cycle)["rows"] if r["appraisal"] == c.own.ap)
		self.assertNotIn("potential_rating", plotted)

	def test_sec26_sec30_reminders_archive_and_sign_off_stay_inside_hrs_companies(self):
		from unittest.mock import patch

		import alvoraa_portal.performance_api as pa

		c = self._setup_cycle()
		self._as(self.hr_user)
		for call in (pa.send_review_reminder, pa.archive_review, pa.unarchive_review):
			with self.assertRaises(frappe.PermissionError, msg=call.__name__):
				call(c.other.ap)

		# A reminder for a review with no record yet creates none (SEC-6).
		fresh = self._appraisal(self.manager, self._cycle(), with_extension=False)
		self._as(self.hr_user)
		with patch("frappe.sendmail"):
			try:
				pa.send_review_reminder(fresh)
			except frappe.ValidationError:
				pass   # no email address on the test employee
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Alvoraa Appraisal Extension", fresh))

		self._as(self.stranger_user)
		with self.assertRaises(frappe.PermissionError):
			pa.get_calibration_signoff(c.cycle)
		self._as(self.hr_user)
		self.assertIsNone(pa.get_calibration_signoff(c.cycle))


class TestQueryCountOfHrCycleScreens(_CycleScreens):
	def _queries(self, reviews):
		from unittest.mock import patch

		import alvoraa_portal.performance_api as pa
		from alvoraa_portal.tests.test_portal_security_010 import _employee

		start, end = self._window()
		cycle = self._cycle(start, end)
		for i in range(reviews):
			employee = _employee(f"DCount{i}", company=self.company_a)
			self._review_in(cycle, start, employee, "HR Review")
		self._as(self.hr_user)
		counts = {}
		for name, call in (("hr_list_appraisals", pa.hr_list_appraisals), ("hr_list_kpis", pa.hr_list_kpis),
		                   ("hr_cycle_summary", pa.hr_cycle_summary),
		                   ("get_calibration_overview", pa.get_calibration_overview),
		                   ("get_calibration_matrix", pa.get_calibration_matrix),
		                   ("export_cycle_kpis_csv", pa.export_cycle_kpis_csv)):
			call(cycle)   # warm the caches
			with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
				call(cycle)
			counts[name] = sql.call_count
		frappe.set_user("Administrator")
		self.measured = counts
		return counts

	def test_query_count_hr_cycle_screens_do_not_grow_with_the_number_of_reviews(self):
		small = self._queries(2)
		large = self._queries(7)
		print("HR cycle screen queries (2 vs 7 reviews):", small, large)
		self.assertEqual(small, large)


# ── Decision 28 · HR opens scorecards only for the companies it looks after ──


class TestDecision28ScorecardCompanyScope(_Team):
	def test_decision28_hr_opens_an_employee_scorecard_only_in_its_companies_and_managers_keep_their_line(self):
		import alvoraa_portal.hr_api as hr_api

		for call in (hr_api.get_employee_scorecard, hr_api.get_employee_detail_for_manager):
			self._as(self.hr_user)
			with self.assertRaises(frappe.PermissionError, msg=call.__name__):
				call(self.subject_b)
			self.assertTrue(call(self.subject), call.__name__)

			# The manager line still opens its own report, and nobody else's.
			self._as(self.manager_user)
			self.assertTrue(call(self.subject), call.__name__)
			with self.assertRaises(frappe.PermissionError, msg=call.__name__):
				call(self.subject_b)


# ── Decision 33 · HR opens goal details only for the companies it looks after ─


class TestDecision33GoalDetailCompanyScope(_Team):
	def test_decision33_hr_opens_a_goal_only_in_its_companies_and_managers_keep_their_line(self):
		import alvoraa_portal.hr_api as hr_api

		start, end = self._window()
		goal_a = self._goal(self.subject, self._cycle(start, end), start, end)
		goal_b = self._goal(self.subject_b, self._cycle(start, end, company=self.company_b), start, end)

		self._as(self.hr_user)
		self.assertEqual(hr_api.get_goal_detail(goal_a)["goal"]["name"], goal_a)
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_goal_detail(goal_b)
		# A goal that does not exist gets the same refusal, so HR cannot probe names.
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_goal_detail("S010D no such goal")

		# The manager line still opens its own report's goal, and nobody else's.
		self._as(self.manager_user)
		self.assertEqual(hr_api.get_goal_detail(goal_a)["goal"]["name"], goal_a)
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_goal_detail(goal_b)
		# The owner still opens their own goal; a colleague outside the line does not.
		self._as(self.subject_user)
		self.assertTrue(hr_api.get_goal_detail(goal_a)["is_owner"])
		self._as(self.stranger_user)
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_goal_detail(goal_a)


# ── Commit 9 · SEC-7, decisions 2 and 17 · reviewers from the reviewed person's company ─


class TestSec7ReviewersComeFromTheReviewedPersonsCompany(_Team):
	def _found(self, **kwargs):
		import alvoraa_portal.performance_api as pa

		return {r["name"] for r in pa.search_employees(query="DTeam", **kwargs)}

	def test_sec7_decision2_the_picker_finds_the_reviewed_persons_company_not_only_the_managers_line(self):
		import alvoraa_portal.performance_api as pa

		ap = self._review_of(self.subject, "Manager Review")

		self._as(self.manager_user)
		found = self._found(appraisal=ap)
		self.assertIn(self.stranger, found)          # same company, outside the line
		self.assertNotIn(self.subject_b, found)      # another company
		self.assertNotIn(self.subject, found)        # never the person reviewed
		self.assertLessEqual(len(pa.search_employees(appraisal=ap)), 50)

		# Somebody who may not invite for this review finds nobody.
		self._as(self.stranger_user)
		with self.assertRaises(frappe.PermissionError):
			pa.search_employees(query="DTeam", appraisal=ap)
		self._as(self.subject_user)
		with self.assertRaises(frappe.PermissionError):
			pa.search_employees(query="DTeam", appraisal=ap)
		self._as(self.hr_user)                       # a stranger to HR, still in Manager Review
		with self.assertRaises(frappe.PermissionError):
			pa.search_employees(query="DTeam", appraisal=ap)

		# Without a review: a manager gets their company, HR its companies, others nobody.
		self._as(self.manager_user)
		found = self._found()
		self.assertIn(self.stranger, found)
		self.assertNotIn(self.subject_b, found)
		self._as(self.hr_user)
		self.assertNotIn(self.subject_b, self._found())
		self._as(self.stranger_user)
		self.assertEqual(pa.search_employees(query="DTeam"), [])

	def test_sec7_invitees_must_belong_to_the_reviewed_persons_company(self):
		from unittest.mock import patch

		import alvoraa_portal.performance_api as pa

		ap = self._review_of(self.subject, "Manager Review")
		self._as(self.manager_user)
		with patch("frappe.sendmail"):
			with self.assertRaises(frappe.PermissionError):
				pa.invite_reviewer(ap, self.subject_b)
			with self.assertRaises(frappe.PermissionError):
				pa.invite_reviewers_batch(ap, json.dumps([{"employee": self.stranger}, {"employee": self.subject_b}]))
			frappe.set_user("Administrator")
			self.assertEqual(json.loads(frappe.db.get_value("Alvoraa Appraisal Extension", ap, "invited_reviewers")
			                            or "[]"), [])

			self._as(self.manager_user)
			pa.invite_reviewer(ap, self.stranger, json.dumps(["past-dev"]))
		frappe.set_user("Administrator")
		invited = json.loads(frappe.db.get_value("Alvoraa Appraisal Extension", ap, "invited_reviewers"))
		self.assertEqual([r["employee"] for r in invited], [self.stranger])

	def test_decision17_an_invited_reviewer_loses_access_once_manager_review_ends(self):
		import alvoraa_portal.performance_api as pa

		ap = self._review_of(self.subject, "Manager Review")
		user = frappe.db.get_value("Employee", self.stranger, "user_id")
		frappe.db.set_value("Alvoraa Appraisal Extension", ap, "invited_reviewers", json.dumps(
			[{"employee": self.stranger, "user": user, "status": "Invited", "allowed_pages": ["past-dev"]}]))
		frappe.db.commit()
		self._as(self.stranger_user)
		pa.get_reviewer_view(ap)
		pa.submit_reviewer_comments(ap, "fine")

		for status in ("Employee Final Review", "HR Review", "Completed"):
			self._set_status(ap, status)
			self._as(self.stranger_user)
			with self.assertRaises(frappe.PermissionError, msg=status):
				pa.get_reviewer_view(ap)
			with self.assertRaises(frappe.ValidationError, msg=status):
				pa.submit_reviewer_comments(ap, "later")


# ── Commit 10 · R9, SEC-22, PRIV-15 · HR is reminded about items still locked ─


class TestR9LockReminder(_Team):
	def setUp(self):
		super().setUp()
		from alvoraa_portal.tests.test_portal_security_010 import _employee, _user

		self.hr_b_user = _user("d.remind.hrb", ("HR Manager", "Employee"))
		self.hr_b = _employee("DRemindHrB", company=self.company_b, user=self.hr_b_user)
		self._release_days(30)

	def _release_days(self, days):
		frappe.db.set_single_value("HR Settings", "alvoraa_review_lock_release_days", days)
		frappe.db.value_cache.pop("HR Settings", None)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		self._release_days(30)
		frappe.db.delete("Notification Log", {"subject": "Objectives and KPIs are still locked in open reviews"})
		frappe.db.commit()
		super().tearDown()

	def _ended(self, days_ago, employee, marker):
		import alvoraa_goals.review_items as review_items

		end = frappe.utils.add_days(frappe.utils.nowdate(), -days_ago)
		start = frappe.utils.add_days(end, -80)
		cycle = self._cycle(start, end)
		frappe.db.set_value("Appraisal Cycle", cycle, "cycle_name", f"{cycle} {marker}")
		kpi = self._kpi(employee, cycle, target=10)
		frappe.db.set_value("KPI", kpi, "kpi_name", f"S010D {marker} secret title")
		ap = self._appraisal(employee, cycle, status="Manager Review")
		review_items.ensure_review_items(self._ext(ap))
		frappe.db.commit()
		return cycle

	def _reminders(self, user, marker):
		return [n.email_content for n in frappe.get_all(
			"Notification Log", filters={"for_user": user, "email_content": ["like", f"%{marker}%"]},
			fields=["email_content"])]

	def test_r9_hr_is_reminded_on_day_15_then_weekly_without_names_and_only_for_its_companies(self):
		import alvoraa_goals.review_items as review_items

		self._ended(15, self.subject, "M15")
		self._ended(16, self.stranger, "M16")
		self._ended(22, self.subject_b, "M22")
		review_items.remind_hr_of_held_items()

		day15 = self._reminders(self.hr_user, "M15")
		self.assertEqual(len(day15), 1)
		self.assertIn("1 review(s) are still open 15 days after the cycle ended", day15[0])
		self.assertEqual(self._reminders(self.hr_user, "M16"), [])       # not a reminder day
		self.assertEqual(self._reminders(self.hr_user, "M22"), [])       # another company
		self.assertEqual(len(self._reminders(self.hr_b_user, "M22")), 1)  # day 22, its company
		self.assertEqual(self._reminders(self.hr_b_user, "M15"), [])

		everything = json.dumps(frappe.get_all("Notification Log", filters={
			"subject": "Objectives and KPIs are still locked in open reviews"}, fields=["subject", "email_content"]))
		for secret in ("secret title", "DTeam", self.subject, self.subject_b):
			self.assertNotIn(secret, everything)

	def test_r9_decision32_no_reminder_once_the_lock_is_released_or_when_it_never_releases(self):
		import alvoraa_goals.review_items as review_items

		self._ended(29, self.subject, "M29")
		self._release_days(15)
		self.assertEqual(review_items.remind_hr_of_held_items(), 0)

		self._release_days(20)
		review_items.remind_hr_of_held_items()     # released on day 20: day 29 is after it
		self.assertEqual(self._reminders(self.hr_user, "M29"), [])

		# Decision 32: 0 means the lock never releases, and then nobody is reminded.
		# Day 29 is a reminder day (15 + 14), so a 30-day release does remind.
		self._release_days(0)
		self.assertEqual(review_items.remind_hr_of_held_items(), 0)
		self.assertEqual(self._reminders(self.hr_user, "M29"), [])
		self._release_days(30)
		review_items.remind_hr_of_held_items()
		self.assertEqual(len(self._reminders(self.hr_user, "M29")), 1)

	def test_r9_the_reminder_runs_daily_from_the_goals_app(self):
		import alvoraa_goals.hooks as hooks

		self.assertEqual(hooks.scheduler_events["daily"][-1], "alvoraa_goals.review_items.remind_hr_of_held_items")


# ── Commit 12 · 00d section 10 · existing reviews get their copies ──────────


class TestBackfillCopiesExistingReviews(_Team):
	"""Reviews made before group D: no copies, ratings still on the live KPIs."""

	def _old_review(self, employee, status, overall=0, page_data=None):
		start, end = self._window()
		cycle = self._cycle(start, end)
		kpi = self._kpi(employee, cycle, target=100, weightage=60)
		goal = self._goal(employee, cycle, start, end, target=10, weightage=40)
		frappe.db.set_value("KPI", kpi, {"actual_value": 80, "attainment_pct": 80}, update_modified=False)
		frappe.db.set_value("Individual Goal", goal, {"actual_progress": 5, "progress_pct": 50}, update_modified=False)
		_legacy_ratings(kpi, self_rating=3, manager_rating=4, potential_rating=5, manager_comment="old comment")
		# Two approved readings in the period that add up to 50, not the stored 80.
		self._reading(kpi, _day(start, 1), 20)
		self._reading(kpi, _day(start, 2), 30)
		ap = self._appraisal(employee, cycle, status=status)
		values = {"overall_rating": overall}
		if page_data is not None:
			values["page_data"] = json.dumps(page_data(kpi, goal))
		frappe.db.set_value("Alvoraa Appraisal Extension", ap, values, update_modified=False)
		frappe.db.commit()
		return frappe._dict(ap=ap, cycle=cycle, kpi=kpi, goal=goal)

	def _setup(self):
		c = frappe._dict()
		c.done = self._old_review(self.stranger, "Completed", overall=4)
		c.open = self._old_review(self.subject, "Manager Review", overall=3, page_data=lambda k, g: {
			"past-objectives": {"kpis": {k: {"self_rating": 3}, "gone-kpi": {"self_rating": 1}},
			                    "objectives": {g: {"reflection": "r"}}}})
		c.fresh = self._old_review(self.hr_report, "Not Started")
		start, end = self._window()
		c.empty = self._appraisal(self.subject_b, self._cycle(start, end, company=self.company_b), status="Completed")
		c.names = [c.done.ap, c.open.ap, c.fresh.ap, c.empty]
		return c

	def test_backfill_dry_run_counts_and_changes_nothing(self):
		import alvoraa_goals.review_backfill as review_backfill

		c = self._setup()
		before = (frappe.db.count("Alvoraa Review Item", {"parent": ["in", c.names]}),
		          [frappe.db.get_value("Alvoraa Appraisal Extension", n, "modified") for n in c.names])
		out = review_backfill.report(c.names)
		after = (frappe.db.count("Alvoraa Review Item", {"parent": ["in", c.names]}),
		         [frappe.db.get_value("Alvoraa Appraisal Extension", n, "modified") for n in c.names])
		self.assertEqual(before, after)

		self.assertEqual(out["reviews"], 4)
		self.assertEqual(out["will_copy"], {"reviews": 2, "items": 4, "completed": 1, "open": 1, "open_already_frozen": 0})
		self.assertEqual(out["items_per_review"], {"average": 2, "most": 2})
		self.assertEqual(out["skipped"], {"not started: copied when first opened": 1})
		self.assertEqual(out["cannot_copy_nothing_tagged"], {"completed": [c.empty], "open": []})
		self.assertEqual(out["rated_items_copied"], 2)
		# The open review's KPI counts 50 from its readings, not the stored 80:
		# one number moves, and a manager rating and the overall rating are asked about.
		self.assertEqual(out["open_items_whose_number_changes_on_first_open"], 2)
		self.assertEqual(out["rating_questions_expected_on_first_open"], 2)
		self.assertEqual(out["draft_keys_dropped"], 1)
		self.assertEqual(out["by_cycle_and_stage"][c.open.cycle], {"Manager Review": 1})

	def test_backfill_copies_history_as_stored_and_open_reviews_once_and_keeps_completed_copies_locked(self):
		import alvoraa_goals.review_backfill as review_backfill
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		c = self._setup()
		result = review_backfill.run(c.names)
		self.assertEqual((result["reviews_copied"], result["copies_made"], result["failed"]), (2, 4, []))

		done = self._ext(c.done.ap)
		kpi = _row_for(done, c.done.kpi)
		self.assertEqual((done.frozen, bool(done.completed_on), bool(done.items_taken_on)), (1, True, True))
		self.assertEqual((kpi.backfilled, kpi.actual_value, kpi.attainment_pct), (1, 80, 80))
		self.assertEqual((kpi.self_rating, kpi.manager_rating, kpi.potential_rating, kpi.manager_comment),
		                 (3, 4, 5, "old comment"))
		self.assertEqual((kpi.manager_basis_actual, kpi.manager_flag), (80, 0))
		self.assertEqual(_row_for(done, c.done.goal).actual_value, 5)
		self.assertEqual(_row_for(done, c.done.kpi).parent_item, "")

		opened = self._ext(c.open.ap)
		open_kpi = _row_for(opened, c.open.kpi)
		self.assertEqual((opened.frozen, opened.freeze_point), (0, review_items.FREEZE_HR_SENT))
		self.assertEqual(review_items.open_blocking_flags(opened), 0)
		draft = json.loads(opened.page_data)["past-objectives"]
		self.assertEqual(draft["kpis"], {open_kpi.name: {"self_rating": 3}})
		self.assertEqual(draft["objectives"], {_row_for(opened, c.open.goal).name: {"reflection": "r"}})
		self.assertEqual(frappe.db.count("Alvoraa Review Item", {"parent": c.fresh.ap}), 0)

		# Twice is the same as once.
		self.assertEqual(review_backfill.run(c.names)["reviews_copied"], 0)
		self.assertEqual(frappe.db.count("Alvoraa Review Item", {"parent": ["in", c.names]}), 4)

		# The live records were not touched.
		self.assertEqual(frappe.db.get_value("KPI", c.done.kpi, ["actual_value", "manager_rating"]), (80, 4))

		# A completed review's copies still cannot change through the review record (VIS-10).
		done = self._ext(c.done.ap)
		done.review_items[0].manager_rating = 1
		with self.assertRaises(frappe.PermissionError):
			review_items.save_review_record(done)
		frappe.db.rollback()

		# The first open recounts the open review from facts, and asks the manager
		# about the ratings given on the old number (R7).
		self._as(self.manager_user)
		pa.get_manager_review(c.open.ap)
		frappe.set_user("Administrator")
		opened = self._ext(c.open.ap)
		self.assertEqual(_row_for(opened, c.open.kpi).actual_value, 50)
		self.assertEqual(review_items.open_blocking_flags(opened), 2)

	def test_backfill_undo_leaves_changed_reviews_and_ratings_go_back_before_a_rollback(self):
		import alvoraa_goals.review_backfill as review_backfill
		import alvoraa_goals.review_items as review_items

		c = self._setup()
		review_backfill.run(c.names)

		# Someone rates the open review's KPI copy after the copy was made.
		opened = self._ext(c.open.ap)
		row = _row_for(opened, c.open.kpi)
		row.manager_rating = 2
		row.manager_rated_on = frappe.utils.add_to_date(opened.items_taken_on, minutes=5)
		review_items.save_review_record(opened)
		frappe.db.commit()

		plan = review_backfill.undo_backfill(dry_run=1, names=c.names)
		self.assertIn(c.open.ap, plan["kept_because_changed_since"])
		self.assertEqual(frappe.db.count("Alvoraa Review Item", {"parent": c.done.ap}), 2)

		ratings = review_backfill.copy_ratings_back_for_rollback(dry_run=1, names=c.names)
		self.assertIn(c.open.kpi, ratings["kpis"])
		self.assertNotIn(c.done.kpi, ratings["kpis"])       # completed reviews are history
		self.assertEqual(frappe.db.get_value("KPI", c.open.kpi, "manager_rating"), 4)
		review_backfill.copy_ratings_back_for_rollback(dry_run=0, names=c.names)
		self.assertEqual(frappe.db.get_value("KPI", c.open.kpi, "manager_rating"), 2)

		review_backfill.undo_backfill(dry_run=0, names=c.names)
		self.assertEqual(frappe.db.count("Alvoraa Review Item", {"parent": c.done.ap}), 0)
		self.assertFalse(frappe.db.get_value("Alvoraa Appraisal Extension", c.done.ap, "items_taken_on"))
		self.assertEqual(frappe.db.count("Alvoraa Review Item", {"parent": c.open.ap}), 2)

	def test_backfill_patch_is_listed_last_and_syncs_its_tables_first(self):
		lines = [line.strip() for line in _source("alvoraa_goals", "patches.txt").splitlines() if line.strip()]
		self.assertEqual(lines[-1], "alvoraa_goals.patches.v1_0.take_review_copies")
		patch_text = _source("alvoraa_goals", "patches", "v1_0", "take_review_copies.py")
		for doctype in ("alvoraa_review_item", "alvoraa_appraisal_extension", "kpi"):
			self.assertIn(f'frappe.reload_doc("alvoraa_goals", "doctype", "{doctype}")', patch_text)


class TestDecision26TenantReadGrantIsReported(_Team):
	def test_decision26_m3_report_lists_a_tenant_read_grant_on_appraisal_and_changes_nothing(self):
		import alvoraa_goals.review_items as review_items

		grant = frappe.get_doc({
			"doctype": "Custom DocPerm", "parent": "Appraisal", "parenttype": "DocType",
			"parentfield": "permissions", "role": "Employee", "permlevel": 0, "read": 1,
		})
		grant.name = frappe.generate_hash(length=10)
		grant.db_insert()
		try:
			found = {(r["doctype"], r["role"]) for r in review_items.custom_docperm_report()}
			self.assertIn(("Appraisal", "Employee"), found)
			self.assertTrue(frappe.db.exists("Custom DocPerm", grant.name), "the report must never remove a row")
		finally:
			frappe.db.rollback()
