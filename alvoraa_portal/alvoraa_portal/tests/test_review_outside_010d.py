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
