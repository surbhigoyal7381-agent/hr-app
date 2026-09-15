"""Slice 010 group D, phase 2: pin tests for review screens, writes on copies,
freezing, write-back and the definition lock (commits 4 to 7).

Requirements: docs/slices/010-portal-security-fixes/00c (R1-R16), 00d (strategy),
01d (VIS / SEC / PRIV) and 00e (the approved decisions, which win).

Each test is named after the rule it keeps closed, so a merge that drops a fix
fails CI here. Refusals are tested, not only the allowed path. Synthetic people
and records only, tagged S010D.
"""

import json
from unittest.mock import patch

import frappe
from frappe.utils import add_days, add_to_date, now_datetime

from alvoraa_portal.tests.test_review_copies_010d import _day, _row_for, _Team


def _names_in(payload):
	return json.dumps(payload, default=str)


class _Screens(_Team):
	"""A review of the manager's report with one Objective, a KPI under it and a standalone KPI."""

	def _review(self, status="Employee Review", readings=True):
		start, end = self._window()
		cycle = self._cycle(start, end)
		goal = self._goal(self.subject, cycle, start, end, target=100)
		under = self._kpi(self.subject, cycle, target=100, goal=goal)
		alone = self._kpi(self.subject, cycle, target=50)
		if readings:
			self._reading(under, _day(start, 1), 40)
			self._reading(alone, _day(start, 2), 10)
		ap = self._appraisal(self.subject, cycle, status="Employee Review")
		# The subject's first open takes the copies.
		self._as(self.subject_user)
		import alvoraa_portal.performance_api as pa

		pa.get_my_review(ap)
		frappe.set_user("Administrator")
		if status != "Employee Review":
			self._set_status(ap, status)
		return frappe._dict(ap=ap, cycle=cycle, start=start, end=end, goal=goal, under=under, alone=alone)

	def _invite(self, ap, employee, pages):
		user = frappe.db.get_value("Employee", employee, "user_id")
		frappe.db.set_value(
			"Alvoraa Appraisal Extension", ap, "invited_reviewers",
			json.dumps([{"employee": employee, "user": user, "status": "Invited", "allowed_pages": pages}]),
		)
		frappe.db.commit()


# ── Commit 4 · Review screens show the review's copies ──────────────────────


class TestVis3ReviewScreensShowCopies(_Screens):
	def test_vis3_review_screens_return_copies_and_never_a_live_record_name(self):
		import alvoraa_portal.performance_api as pa

		r = self._review(status="Manager Review")
		originals = (r.goal, r.under, r.alone)
		rows = {x.source_name: x.name for x in self._ext(r.ap).review_items}
		# A live number changed behind the review does not reach the screen.
		frappe.db.set_value("KPI", r.alone, "actual_value", 999)
		frappe.db.commit()
		self._invite(r.ap, self.stranger, ["past-objectives"])

		payloads = []
		self._as(self.subject_user)
		payloads.append(pa.get_my_review(r.ap))
		self._as(self.manager_user)
		payloads.append(pa.get_manager_review(r.ap))
		self._as(self.stranger_user)
		payloads.append(pa.get_reviewer_view(r.ap))

		for payload in payloads:
			text = _names_in(payload)
			for name in originals:
				self.assertNotIn(name, text)

		mine = payloads[0]
		self.assertEqual([g["name"] for g in mine["goals"]], [rows[r.goal]])
		self.assertEqual([k["name"] for k in mine["goals"][0]["kpis"]], [rows[r.under]])
		self.assertEqual([k["name"] for k in mine["standalone_kpis"]], [rows[r.alone]])
		self.assertEqual(mine["standalone_kpis"][0]["actual_value"], 10)
		self.assertEqual(mine["goals"][0]["kpis"][0]["actual_value"], 40)

	def test_vis15_future_objectives_list_leaves_out_what_this_review_holds(self):
		import alvoraa_portal.performance_api as pa

		year_start, year_end = self._window()
		first = self._cycle(year_start, year_end)
		second = self._cycle(add_days(year_end, 1), add_days(year_end, 90))
		held = self._kpi(self.subject, first, start=year_start, end=add_days(year_end, 90))
		annual = self._goal(self.subject, first, year_start, add_days(year_end, 90))
		q1 = self._appraisal(self.subject, first, status="Manager Review")
		import alvoraa_goals.review_items as review_items

		review_items.ensure_review_items(self._ext(q1))
		q2 = self._appraisal(self.subject, second)
		self._as(self.subject_user)
		payload = pa.get_my_review(q2)
		# The annual goal is held by Q1 and copied into Q2 too (R16); its live
		# name must not come back beside the copy.
		self.assertNotIn(annual, _names_in(payload))
		self.assertNotIn(held, _names_in(payload))
		self.assertEqual(len(payload["goals"]), 1)


class TestPriv1Priv13FieldFilter(_Screens):
	STAMPS = {"manager_basis_actual", "manager_flag", "self_flag", "self_basis_actual", "manager_rated_by"}

	def _rate(self, ap):
		import alvoraa_goals.review_items as review_items

		ext = self._ext(ap)
		for row in ext.review_items:
			row.self_rating, row.manager_rating, row.potential_rating = 3, 4, 5
			review_items.stamp_rating(row, "self")
			review_items.stamp_rating(row, "manager")
		review_items.save_review_record(ext)
		frappe.db.commit()

	def _keys(self, payload):
		items = [k for g in payload["goals"] for k in [g, *g["kpis"]]] + payload["standalone_kpis"]
		return set().union(*(set(i) for i in items))

	def test_priv1_priv13_each_viewer_receives_only_what_the_stage_allows(self):
		import alvoraa_portal.performance_api as pa

		r = self._review(status="Manager Review")
		self._rate(r.ap)
		self._invite(r.ap, self.stranger, ["past-objectives"])

		self._as(self.subject_user)
		keys = self._keys(pa.get_my_review(r.ap))
		self.assertIn("self_rating", keys)
		self.assertFalse({"manager_rating", "potential_rating", "late_facts"} & keys)
		self.assertFalse(self.STAMPS & keys)

		self._as(self.stranger_user)
		keys = self._keys(pa.get_reviewer_view(r.ap))
		self.assertIn("self_rating", keys)
		self.assertFalse({"manager_rating", "potential_rating", "definition_changed"} & keys)
		self.assertFalse(self.STAMPS & keys)

		self._as(self.manager_user)
		keys = self._keys(pa.get_manager_review(r.ap))
		self.assertTrue({"manager_rating", "potential_rating"} <= keys)
		self.assertTrue(self.STAMPS <= keys)
		self.assertNotIn("late_facts", keys)

		# From Employee Final Review the subject sees item manager ratings
		# (decision 11), still never potential, stamps or flags.
		self._set_status(r.ap, "Employee Final Review")
		self._as(self.subject_user)
		keys = self._keys(pa.get_my_review(r.ap))
		self.assertIn("manager_rating", keys)
		self.assertFalse({"potential_rating", "potential_comment"} & keys)
		self.assertFalse(self.STAMPS & keys)


class TestSec7ReviewerPages(_Screens):
	def test_sec7_an_invited_reviewer_reads_only_their_pages_and_only_during_manager_review(self):
		import alvoraa_portal.performance_api as pa

		r = self._review(status="Manager Review")
		frappe.db.set_value("Alvoraa Appraisal Extension", r.ap, "page_data",
		                    json.dumps({"past-dev": {"achievements": "a"}, "past-objectives": {"kpis": {}},
		                                "future-dev": {"development_goals": "d"}}))
		frappe.db.commit()

		self._invite(r.ap, self.stranger, ["past-dev"])
		self._as(self.stranger_user)
		view = pa.get_reviewer_view(r.ap)
		self.assertEqual(set(view["page_data"]), {"past-dev"})
		self.assertEqual((view["goals"], view["standalone_kpis"]), ([], []))

		self._invite(r.ap, self.stranger, [])
		self._as(self.stranger_user)
		view = pa.get_reviewer_view(r.ap)
		self.assertEqual((view["page_data"], view["goals"]), ({}, []))

		self._invite(r.ap, self.stranger, ["past-objectives"])
		self._as(self.stranger_user)
		self.assertTrue(pa.get_reviewer_view(r.ap)["goals"])

		for status in ("Employee Review", "Employee Final Review", "HR Review", "Completed"):
			self._set_status(r.ap, status)
			self._as(self.stranger_user)
			with self.assertRaises(frappe.PermissionError, msg=status):
				pa.get_reviewer_view(r.ap)


class TestR10LateFacts(_Screens):
	def test_r10_facts_approved_after_the_freeze_are_shown_to_hr_and_never_change_the_score(self):
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		r = self._review(status="HR Review")
		ext = self._ext(r.ap)
		ext.frozen, ext.frozen_on = 1, add_to_date(now_datetime(), hours=-1)
		review_items.save_review_record(ext)
		frappe.db.commit()
		# Dated inside the period, approved after the numbers froze.
		self._reading(r.alone, _day(r.start, 5), 15, approved_on=now_datetime())
		row = _row_for(self._ext(r.ap), r.alone)

		self._as(self.hr_user)
		kpi = next(k for k in pa.get_manager_review(r.ap)["standalone_kpis"] if k["name"] == row.name)
		self.assertEqual(kpi["late_facts"], {"count": 1, "actual_with_late": 25})
		self.assertEqual(kpi["actual_value"], 10)
		self.assertEqual(_row_for(self._ext(r.ap), r.alone).actual_value, 10)

		# Nobody else sees them (PRIV-11).
		self._as(self.subject_user)
		self.assertNotIn("late_facts", _names_in(pa.get_my_review(r.ap)))
		self._as(self.manager_user)
		self.assertNotIn("late_facts", _names_in(pa.get_manager_review(r.ap)))


class TestQueryCountOfOpeningAReview(_Screens):
	def _queries_to_open(self, goals, kpis):
		import alvoraa_portal.performance_api as pa

		start, end = self._window()
		cycle = self._cycle(start, end)
		for _i in range(goals):
			self._goal(self.stranger, cycle, start, end)
		for _i in range(kpis):
			self._reading(self._kpi(self.stranger, cycle), _day(start, 1), 1)
		ap = self._appraisal(self.stranger, cycle, status="Employee Review")
		self._as(self.stranger_user)
		pa.get_my_review(ap)   # first open takes the copies
		with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
			pa.get_my_review(ap)
		frappe.set_user("Administrator")
		return sql.call_count

	def test_query_count_opening_a_review_does_not_grow_with_its_items(self):
		small = self._queries_to_open(goals=1, kpis=2)
		large = self._queries_to_open(goals=4, kpis=12)
		self.assertEqual(small, large)
