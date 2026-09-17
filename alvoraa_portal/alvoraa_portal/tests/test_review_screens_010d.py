"""Slice 010 group D, phase 2: pin tests for review screens, writes on copies,
freezing, write-back and the definition lock (commits 4 to 7).

Requirements: docs/slices/010-portal-security-fixes/00c (R1-R16), 00d (strategy),
01d (VIS / SEC / PRIV) and 00e (the approved decisions, which win).

Each test is named after the rule it keeps closed, so a merge that drops a fix
fails CI here. Refusals are tested, not only the allowed path. Synthetic people
and records only, tagged S010D.
"""

import ast
import json
import re
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, now_datetime

from alvoraa_portal.tests.test_portal_security_010 import _employee, _user
from alvoraa_portal.tests.test_review_copies_010d import _day, _row_for, _Team, _uid


TAG_D = "S010D"


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

	def _flagged_review(self, manager_user, subject, subject_user):
		import alvoraa_portal.performance_api as pa

		start, end = self._window()
		cycle = self._cycle(start, end)
		kpi = self._kpi(subject, cycle, target=100)
		self._reading(kpi, _day(start, 1), 40)
		ap = self._appraisal(subject, cycle, status="Employee Review")
		self._as(subject_user)
		pa.get_my_review(ap)
		self._set_status(ap, "Manager Review")
		row = _row_for(self._ext(ap), kpi).name
		self._as(manager_user)
		pa.save_review_item_rating(ap, row, 4)
		pa.save_manager_review(ap, "feedback", overall_rating=4)
		self._reading(kpi, _day(start, 2), 30)
		self._as(manager_user)
		pa.get_manager_review(ap)     # the refresh raises the flags
		frappe.set_user("Administrator")
		ext = self._ext(ap)
		self.assertEqual((_row_for(ext, kpi).manager_flag, ext.overall_rating_flag), (1, 1))
		return ap, row

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
		# Frozen after the setup readings were approved.
		ext.frozen, ext.frozen_on = 1, now_datetime()
		review_items.save_review_record(ext)
		frappe.db.commit()
		# Dated inside the period, approved after the numbers froze.
		self._reading(r.alone, _day(r.start, 5), 15, approved_on=add_to_date(now_datetime(), hours=1))
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


# ── Commit 5 · Ratings, removals and definition changes are made on the copies ─


class TestSec1SelfReviewWritesOnlyThisReviewsCopies(_Screens):
	def test_sec1_the_self_review_writes_only_this_reviews_copies_and_never_progress(self):
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		r = self._review()
		ext = self._ext(r.ap)
		kpi_row, goal_row = _row_for(ext, r.alone), _row_for(ext, r.goal)
		live_progress = frappe.db.get_value("Individual Goal", r.goal, "actual_progress")

		# A colleague's review, and a page that names its copy and its live KPI.
		other = self._review_of(self.stranger, "Employee Review")
		other_kpi = self._kpi(self.stranger, frappe.db.get_value("Appraisal", other, "appraisal_cycle"))
		review_items.ensure_review_items(self._ext(other))
		foreign_row = _row_for(self._ext(other), other_kpi).name
		for bad in (foreign_row, other_kpi, r.alone):
			self._as(self.subject_user)
			with self.assertRaises(frappe.PermissionError, msg=bad):
				pa.save_review_page(r.ap, "past-objectives", json.dumps({"kpis": {bad: {"self_rating": 5}}}))
		frappe.db.set_value("Alvoraa Appraisal Extension", r.ap, "page_data",
		                    json.dumps({"past-objectives": {"kpis": {foreign_row: {"self_rating": 5}}}}))
		frappe.db.commit()
		self._as(self.subject_user)
		with self.assertRaises(frappe.PermissionError):
			pa.submit_employee_review(r.ap)
		frappe.db.rollback()
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Alvoraa Appraisal Extension", r.ap, "review_status"), "Employee Review")
		self.assertFalse(_row_for(self._ext(other), other_kpi).self_rating)

		page = {"kpis": {kpi_row.name: {"self_rating": 4, "self_comment": "went well"}},
		        "objectives": {goal_row.name: {"actual_progress": 999, "reflection": "learned a lot"}}}
		self._as(self.subject_user)
		pa.save_review_page(r.ap, "past-objectives", json.dumps(page))
		pa.submit_employee_review(r.ap)

		frappe.set_user("Administrator")
		ext = self._ext(r.ap)
		row = _row_for(ext, r.alone)
		self.assertEqual((row.self_rating, row.self_comment, row.self_basis_actual), (4, "went well", 10))
		self.assertEqual(_row_for(ext, r.goal).self_comment, "learned a lot")
		self.assertEqual(ext.review_status, "Manager Review")
		# Nothing reached the live records.
		self.assertFalse(frappe.db.get_value("KPI", r.alone, "self_rating"))
		self.assertEqual(frappe.db.get_value("Individual Goal", r.goal, "actual_progress"), live_progress)

	def test_vis15_a_future_objective_that_cannot_be_created_stops_the_submission(self):
		import alvoraa_portal.performance_api as pa

		r = self._review()
		frappe.db.set_value("Alvoraa Appraisal Extension", r.ap, "page_data", json.dumps(
			{"future-objectives": {"new_goals": [{"name": f"{TAG_D} next", "target_value": 0}]}}))
		frappe.db.commit()
		self._as(self.subject_user)
		with self.assertRaises(frappe.ValidationError):
			pa.submit_employee_review(r.ap)
		frappe.db.rollback()
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Alvoraa Appraisal Extension", r.ap, "review_status"), "Employee Review")

		frappe.db.set_value("Alvoraa Appraisal Extension", r.ap, "page_data", json.dumps(
			{"future-objectives": {"new_goals": [{"name": f"{TAG_D} next {_uid()}", "target_value": 10,
			                                        "start_date": r.start, "end_date": r.end}]}}))
		frappe.db.commit()
		self._as(self.subject_user)
		pa.submit_employee_review(r.ap)
		frappe.set_user("Administrator")
		made = frappe.get_all("Individual Goal",
		                      filters={"employee": self.subject, "goal_name": ["like", f"{TAG_D} next %"]},
		                      fields=["name", "appraisal_cycle"])
		for g in made:
			self._cleanup.append(("Individual Goal", g.name))
		self.assertEqual(len(made), 1)
		self.assertFalse(made[0].appraisal_cycle)
		self.assertNotIn(made[0].name, {x.source_name for x in self._ext(r.ap).review_items})


class TestVis6RatingsLiveOnCopies(_Screens):
	def test_vis6_r13_ratings_are_saved_on_copies_and_the_old_rating_endpoints_are_retired(self):
		import alvoraa_portal.performance_api as pa

		r = self._review()
		row = _row_for(self._ext(r.ap), r.alone).name

		self._as(self.subject_user)
		pa.save_review_item_rating(r.ap, row, 4, "mine")
		with self.assertRaises(frappe.PermissionError):
			pa.save_review_item_rating(r.ap, row, 4, potential_rating=5)
		# A live record's name is never accepted in place of a copy (VIS-3).
		with self.assertRaises(frappe.PermissionError):
			pa.save_review_item_rating(r.ap, r.alone, 4)
		self._as(self.manager_user)
		with self.assertRaises(frappe.PermissionError):
			pa.save_review_item_rating(r.ap, row, 3)

		self._set_status(r.ap, "Manager Review")
		self._as(self.manager_user)
		pa.save_review_item_rating(r.ap, row, 3, "theirs", potential_rating=4)
		self._as(self.subject_user)
		with self.assertRaises(frappe.PermissionError):
			pa.save_review_item_rating(r.ap, row, 5)
		self._set_status(r.ap, "HR Review")
		self._as(self.hr_user)
		with self.assertRaises(frappe.PermissionError):
			pa.save_review_item_rating(r.ap, row, 1)

		frappe.set_user("Administrator")
		copy = _row_for(self._ext(r.ap), r.alone)
		self.assertEqual((copy.self_rating, copy.manager_rating, copy.potential_rating), (4, 3, 4))
		self.assertEqual((copy.manager_rated_by, copy.manager_basis_actual), (self.manager_user, 10))
		live = frappe.db.get_value("KPI", r.alone, ["self_rating", "manager_rating", "potential_rating"], as_dict=True)
		self.assertEqual((live.self_rating, live.manager_rating, live.potential_rating), (0, 0, 0))

		for user, call in (
			(self.subject_user, lambda: pa.save_kpi_self_review(r.alone, 5)),
			(self.manager_user, lambda: pa.save_kpi_manager_review(r.alone, 5)),
			(self.manager_user, lambda: pa.add_additional_reviewer(r.alone, self.stranger)),
			(self.hr_user, lambda: pa.save_additional_reviewer_rating(r.alone, "x", 5)),
		):
			self._as(user)
			with self.assertRaises(frappe.PermissionError):
				call()


class TestR12Removal(_Screens):
	def _count_audit(self, ap, row):
		return frappe.db.count("Comment", {"reference_doctype": "Alvoraa Appraisal Extension",
		                                   "reference_name": ap, "content": ["like", f"%{row}%"]})

	def test_r12_sec24_who_removes_when_and_a_rated_copy_is_always_kept(self):
		import alvoraa_portal.performance_api as pa

		r = self._review()
		ext = self._ext(r.ap)
		self.assertEqual(ext.removal_mode, "Discard the copy")
		unrated, rated = _row_for(ext, r.under).name, _row_for(ext, r.alone).name

		self._as(self.subject_user)
		with self.assertRaises(frappe.ValidationError):
			pa.remove_review_item(r.ap, unrated)          # not confirmed
		self.assertEqual(pa.remove_review_item(r.ap, unrated, acknowledge=1)["outcome"], "discarded")
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Alvoraa Review Item", unrated))
		self.assertEqual(self._count_audit(r.ap, unrated), 1)
		# The live record stays, in its cycle.
		self.assertEqual(frappe.db.get_value("KPI", r.under, "appraisal_cycle"), r.cycle)

		self._as(self.subject_user)
		pa.save_review_item_rating(r.ap, rated, 2)
		self._set_status(r.ap, "Manager Review")
		self._as(self.subject_user)
		with self.assertRaises(frappe.PermissionError):
			pa.remove_review_item(r.ap, rated, "x", acknowledge=1)
		self._as(self.manager_user)
		with self.assertRaises(frappe.ValidationError):
			pa.remove_review_item(r.ap, rated, "", acknowledge=1)   # no reason
		reason = f"{TAG_D}-reason-{_uid()}"
		# A rated copy is kept, whatever the setting (decision 9).
		self.assertEqual(pa.remove_review_item(r.ap, rated, reason, acknowledge=1)["outcome"], "kept")
		frappe.set_user("Administrator")
		copy = frappe.get_doc("Alvoraa Review Item", rated)
		self.assertEqual((copy.removed, copy.removed_by, copy.removal_reason), (1, self.manager_user, reason))

		# The employee does not see the manager's removal until Employee Final
		# Review; then label, date and reason (decision 10).
		self._as(self.subject_user)
		self.assertNotIn(reason, _names_in(pa.get_my_review(r.ap)))
		self._set_status(r.ap, "Employee Final Review")
		self._as(self.subject_user)
		removed = pa.get_my_review(r.ap)["removed_items"]
		self.assertEqual([(x["name"], x["removal_reason"]) for x in removed], [(rated, reason)])
		self.assertNotIn("removed_by", removed[0])

		# Nobody removes anything from a completed review.
		self._set_status(r.ap, "Completed")
		self._as(self.hr_user)
		with self.assertRaises(frappe.PermissionError):
			pa.remove_review_item(r.ap, rated, "late", acknowledge=1)

	def test_vis5_the_dialog_adds_and_removes_copies_and_never_moves_a_live_record(self):
		import alvoraa_portal.performance_api as pa

		r = self._review()
		new_kpi = self._kpi(self.subject, None, start=r.start, end=r.end)
		elsewhere = self._kpi(self.stranger, None, start=r.start, end=r.end)

		self._as(self.subject_user)
		available = {k["name"]: k["selected"] for k in pa.get_available_for_review(r.ap)["kpis"]}
		self.assertEqual((available[r.alone], available[new_kpi]), (True, False))
		pa.set_review_selection(r.ap, selected_kpis_json=json.dumps([r.alone, new_kpi]))
		frappe.set_user("Administrator")
		added = _row_for(self._ext(r.ap), new_kpi)
		self.assertEqual((added.added_in_review, added.added_by), (1, self.subject_user))
		self.assertFalse(frappe.db.get_value("KPI", new_kpi, "appraisal_cycle"))

		self._as(self.subject_user)
		with self.assertRaises(frappe.PermissionError):
			pa.set_review_selection(r.ap, selected_kpis_json=json.dumps([r.alone, new_kpi, elsewhere]))
		with self.assertRaises(frappe.ValidationError):
			pa.set_review_selection(r.ap, selected_kpis_json=json.dumps([new_kpi]))
		pa.set_review_selection(r.ap, selected_kpis_json=json.dumps([new_kpi]), acknowledge_removal=1)
		frappe.set_user("Administrator")
		self.assertNotIn(r.alone, {x.source_name for x in self._ext(r.ap).review_items if not x.removed})
		self.assertEqual(frappe.db.get_value("KPI", r.alone, "appraisal_cycle"), r.cycle)

		self._as(self.manager_user)
		with self.assertRaises(frappe.PermissionError):
			pa.set_review_selection(r.ap, selected_kpis_json=json.dumps([r.alone]))
		self._set_status(r.ap, "Manager Review")
		self._as(self.subject_user)
		with self.assertRaises(frappe.PermissionError):
			pa.set_review_selection(r.ap, selected_kpis_json=json.dumps([r.alone, new_kpi]))


class TestR11DeleteInsideTheReview(_Screens):
	def test_r11_only_an_item_created_inside_the_review_with_no_facts_can_be_deleted(self):
		import alvoraa_portal.performance_api as pa

		r = self._review()
		fresh = self._kpi(self.subject, None, start=r.start, end=r.end)
		with_facts = self._kpi(self.subject, None, start=r.start, end=r.end)
		self._reading(with_facts, _day(r.start, 3), 1, status="Pending")
		self._as(self.subject_user)
		pa.set_review_selection(r.ap, selected_kpis_json=json.dumps([r.alone, fresh, with_facts]))
		frappe.set_user("Administrator")
		ext = self._ext(r.ap)
		rows = {s: _row_for(ext, s).name for s in (r.alone, fresh, with_facts)}

		self._as(self.subject_user)
		for source in (r.alone, with_facts):
			with self.assertRaises(frappe.PermissionError, msg=source):
				pa.delete_review_item(r.ap, rows[source], acknowledge=1)
		with self.assertRaises(frappe.ValidationError):
			pa.delete_review_item(r.ap, rows[fresh])
		pa.delete_review_item(r.ap, rows[fresh], acknowledge=1)

		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("KPI", fresh))
		self.assertTrue(frappe.db.exists("KPI", r.alone))
		self.assertTrue(frappe.db.exists("KPI", with_facts))


class TestR2DefinitionChangesInsideTheReview(_Screens):
	def test_r2_decision6_the_employee_then_the_manager_change_a_copys_definition(self):
		import alvoraa_portal.performance_api as pa

		r = self._review()
		row = _row_for(self._ext(r.ap), r.alone).name

		self._as(self.subject_user)
		for bad in ({"target_value": 0}, {"weightage": 120}, {"period_start": r.end, "period_end": r.start}):
			with self.assertRaises(frappe.ValidationError, msg=str(bad)):
				pa.save_review_item_definition(r.ap, row, **bad)
		self.assertEqual(pa.save_review_item_definition(r.ap, row, target_value=20)["changed"], ["target_value"])
		self._as(self.manager_user)
		with self.assertRaises(frappe.PermissionError):
			pa.save_review_item_definition(r.ap, row, target_value=40)

		frappe.set_user("Administrator")
		copy = _row_for(self._ext(r.ap), r.alone)
		self.assertEqual((copy.target_value, copy.attainment_pct, copy.definition_changed_by), (20, 50, self.subject_user))
		self.assertEqual(frappe.db.get_value("KPI", r.alone, "target_value"), 50)
		self._as(self.subject_user)
		changed = next(k for k in pa.get_my_review(r.ap)["standalone_kpis"] if k["name"] == row)["definition_changed"]
		self.assertEqual(changed, {"target_value": 50.0})

		self._set_status(r.ap, "Manager Review")
		self._as(self.manager_user)
		pa.save_review_item_rating(r.ap, row, 3)
		pa.save_review_item_definition(r.ap, row, title="Renamed", target_value=40)
		self._as(self.subject_user)
		with self.assertRaises(frappe.PermissionError):
			pa.save_review_item_definition(r.ap, row, target_value=10)
		self._set_status(r.ap, "HR Review")
		self._as(self.hr_user)
		with self.assertRaises(frappe.PermissionError):
			pa.save_review_item_definition(r.ap, row, target_value=10)

		frappe.set_user("Administrator")
		copy = _row_for(self._ext(r.ap), r.alone)
		self.assertEqual((copy.title, copy.target_value), ("Renamed", 40))
		# The manager rated at target 20; the target moved, so the rating is flagged (R7).
		self.assertEqual(copy.manager_flag, 1)


class TestR7FlagAnswers(_Screens):
	def test_r7_decision12_the_rater_answers_a_flag_and_nobody_else_does(self):
		import alvoraa_portal.performance_api as pa

		ap, row = self._flagged_review(self.manager_user, self.subject, self.subject_user)
		for user in (self.subject_user, self.hr_user, self.stranger_user):
			self._as(user)
			with self.assertRaises(frappe.PermissionError, msg=user):
				pa.answer_rating_flag(ap, row, keep=1)

		self._as(self.manager_user)
		pa.answer_rating_flag(ap, row, keep=1)
		pa.answer_rating_flag(ap, "overall", keep=0, rating=2)
		frappe.set_user("Administrator")
		ext = self._ext(ap)
		copy = next(x for x in ext.review_items if x.name == row)
		self.assertEqual((copy.manager_flag, copy.manager_rating, copy.manager_basis_actual), (0, 4, 70))
		self.assertEqual((copy.manager_flag_answered_by, copy.manager_rated_by), (self.manager_user, self.manager_user))
		self.assertEqual((ext.overall_rating_flag, ext.overall_rating, ext.overall_flag_answered_by),
		                 (0, 2, self.manager_user))

	def test_r7_decision12_hr_answers_with_a_reason_when_the_manager_has_left(self):
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		company = frappe.db.get_value("Employee", self.hr, "company")
		boss_user = _user("d.flag.boss", ("Employee",))
		boss = _employee("DFlagBoss", company=company, user=boss_user)
		worker_user = _user("d.flag.worker", ("Employee",))
		worker = _employee("DFlagWorker", company=company, reports_to=boss, user=worker_user)
		ap, row = self._flagged_review(boss_user, worker, worker_user)
		self._set_status(ap, "HR Review")
		frappe.db.set_value("Employee", boss, "status", "Left")
		frappe.db.commit()
		try:
			self._as(self.hr_user)
			with self.assertRaises(frappe.ValidationError):
				pa.answer_rating_flag(ap, "overall", keep=1)        # no reason
			with patch("alvoraa_portal.performance_api._send_notification") as mail:
				pa.answer_rating_flag(ap, row, keep=1, reason="manager left")
				self.assertFalse(mail.called)
				pa.answer_rating_flag(ap, "overall", keep=0, rating=3, reason="manager left")
				self.assertEqual(mail.call_count, 1)
				self.assertEqual(mail.call_args[0][0], worker_user)
				self.assertNotIn("3", mail.call_args[0][1] + mail.call_args[0][2])
			frappe.set_user("Administrator")
			ext = self._ext(ap)
			self.assertEqual((ext.overall_rating, ext.overall_flag_answered_by, ext.overall_rated_by),
			                 (3, self.hr_user, self.hr_user))
			self.assertEqual(next(x for x in ext.review_items if x.name == row).manager_flag_answered_by, self.hr_user)
			self.assertEqual(review_items.open_blocking_flags(ext), 0)
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", boss, "status", "Active")
			frappe.db.commit()


# ── Commit 6 · Freeze at the review's freeze point, and write back once ────


class TestR6FreezeAndUnfreeze(_Screens):
	def test_r6_decision18_numbers_freeze_at_the_stamped_point_and_a_return_unfreezes_them(self):
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		r = self._review()
		frappe.db.set_value("Alvoraa Appraisal Extension", r.ap, "freeze_point", review_items.FREEZE_SELF_SENT)
		frappe.db.commit()

		self._as(self.subject_user)
		pa.submit_employee_review(r.ap)
		frappe.set_user("Administrator")
		ext = self._ext(r.ap)
		self.assertEqual(ext.frozen, 1)
		self.assertTrue(ext.frozen_on)

		self._reading(r.alone, _day(r.start, 6), 5)
		self._as(self.manager_user)
		pa.get_manager_review(r.ap)
		frappe.set_user("Administrator")
		self.assertEqual(_row_for(self._ext(r.ap), r.alone).actual_value, 10)

		# Sent back before the freeze point: facts flow again (decision 18).
		self._as(self.manager_user)
		pa.return_for_revision(r.ap, "")
		frappe.set_user("Administrator")
		ext = self._ext(r.ap)
		self.assertEqual((ext.frozen, _row_for(ext, r.alone).actual_value), (0, 15))

	def test_r6_with_the_default_the_numbers_freeze_when_hr_completes_the_review(self):
		import alvoraa_portal.performance_api as pa

		r = self._review(status="HR Review")
		self.assertEqual(self._ext(r.ap).freeze_point, "HR sent")
		self._reading(r.alone, _day(r.start, 7), 5)
		self._as(self.hr_user)
		self.assertEqual(pa.advance_review_status(r.ap)["review_status"], "Completed")
		frappe.set_user("Administrator")
		ext = self._ext(r.ap)
		self.assertEqual((ext.frozen, ext.review_status), (1, "Completed"))
		self.assertTrue(ext.completed_on)
		# The last count happened on the way out.
		self.assertEqual(_row_for(ext, r.alone).actual_value, 15)


class TestSec23CompletionWaitsForAnswers(_Screens):
	def test_r7_sec23_hr_cannot_complete_while_a_manager_or_overall_rating_waits_for_an_answer(self):
		import alvoraa_portal.performance_api as pa

		ap, row = self._flagged_review(self.manager_user, self.subject, self.subject_user)
		self._set_status(ap, "HR Review")
		self._as(self.hr_user)
		with self.assertRaises(frappe.PermissionError):
			pa.advance_review_status(ap)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Alvoraa Appraisal Extension", ap, "review_status"), "HR Review")

		self._as(self.manager_user)
		pa.answer_rating_flag(ap, row, keep=1)
		self._as(self.hr_user)
		with self.assertRaises(frappe.PermissionError):
			pa.advance_review_status(ap)            # the overall rating still waits
		self._as(self.manager_user)
		pa.answer_rating_flag(ap, "overall", keep=1)

		# A self-rating question is information only (decision 13).
		frappe.set_user("Administrator")
		frappe.db.set_value("Alvoraa Review Item", row, "self_flag", 1)
		frappe.db.commit()
		self._as(self.hr_user)
		self.assertEqual(pa.advance_review_status(ap)["review_status"], "Completed")


class TestR15WriteBack(_Screens):
	def test_r15_sec25_agreed_changes_go_back_once_and_nobody_elses_change_is_overwritten(self):
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		r = self._review()
		ext = self._ext(r.ap)
		rows = {s: _row_for(ext, s).name for s in (r.alone, r.under)}
		# Not in the review: it arrived after the copies were taken.
		self._kpi(self.subject, r.cycle, target=10, weightage=50)

		self._as(self.subject_user)
		pa.save_review_item_definition(r.ap, rows[r.alone], target_value=80)
		pa.save_review_item_definition(r.ap, rows[r.under], weightage=90)
		self._set_status(r.ap, "Manager Review")
		self._as(self.manager_user)
		pa.save_review_item_rating(r.ap, rows[r.alone], 4)
		self._set_status(r.ap, "HR Review")

		self._as(self.hr_user)
		result = pa.advance_review_status(r.ap)
		self.assertEqual((result["review_status"], result["write_back_notes"]), ("Completed", 2))

		frappe.set_user("Administrator")
		ext = self._ext(r.ap)
		self.assertEqual(frappe.db.get_value("KPI", r.alone, "target_value"), 80)
		written = _row_for(ext, r.alone)
		self.assertTrue(written.written_back_on)
		self.assertIn("Written back", written.write_back_note)
		self.assertEqual(frappe.db.count("Comment", {"reference_doctype": "KPI", "reference_name": r.alone,
		                                             "content": ["like", f"%{r.ap}%"]}), 1)
		# The 90% weight would take this person past 100% on the live cycle: the
		# save is refused, the review still completes, and the reason is kept.
		refused = _row_for(ext, r.under)
		self.assertIn("Not written back", refused.write_back_note)
		self.assertEqual(frappe.db.get_value("KPI", r.under, "weightage"), 0)
		# Ratings are never written back (R13).
		self.assertFalse(frappe.db.get_value("KPI", r.alone, "manager_rating"))

		# Once only.
		self.assertEqual(review_items.write_back(self._ext(r.ap)), 0)

	def test_sec25_a_live_record_changed_after_the_review_started_keeps_its_value(self):
		import alvoraa_goals.review_items as review_items

		r = self._review(status="HR Review")
		ext = self._ext(r.ap)
		row = _row_for(ext, r.alone)
		review_items.change_definition(ext, row, {"target_value": 70})
		review_items.save_review_record(ext)
		# Someone changed the live target after the lock was released.
		frappe.db.set_value("KPI", r.alone, "target_value", 60)
		frappe.db.commit()

		ext = self._ext(r.ap)
		self.assertEqual(review_items.write_back(ext), 1)
		self.assertIn("changed after the review started", _row_for(ext, r.alone).write_back_note)
		self.assertEqual(frappe.db.get_value("KPI", r.alone, "target_value"), 60)

	def test_decision30_an_agreed_objective_target_goes_back_although_progress_exists(self):
		import alvoraa_portal.performance_api as pa

		r = self._review()
		# Progress is already on the live Objective: the older rule refuses any
		# target change on it outside a review.
		frappe.db.set_value("Individual Goal", r.goal, "actual_progress", 20)
		frappe.db.commit()
		row = _row_for(self._ext(r.ap), r.goal).name
		self._as(self.subject_user)
		pa.save_review_item_definition(r.ap, row, target_value=80)
		self._set_status(r.ap, "HR Review")

		self._as(self.hr_user)
		self.assertEqual(pa.advance_review_status(r.ap)["review_status"], "Completed")
		frappe.set_user("Administrator")
		written = _row_for(self._ext(r.ap), r.goal)
		self.assertIn("Written back", written.write_back_note)
		self.assertEqual(frappe.db.get_value("Individual Goal", r.goal, "target_value"), 80)
		# Its audit entry names the review and says why the rule was passed.
		note = frappe.get_all("Comment", filters={"reference_doctype": "Individual Goal", "reference_name": r.goal,
		                                          "comment_type": "Info", "content": ["like", f"%{r.ap}%"]},
		                      pluck="content")
		self.assertEqual(len(note), 1)
		self.assertIn("although progress was already recorded", note[0])

	def test_decision30_the_older_target_rule_still_holds_outside_a_review(self):
		import alvoraa_goals.review_items as review_items

		start, end = self._window()
		goal = self._goal(self.subject, self._cycle(start, end), start, end, target=100)
		frappe.db.set_value("Individual Goal", goal, "actual_progress", 20)
		frappe.db.commit()

		doc = frappe.get_doc("Individual Goal", goal)
		doc.target_value = 80
		with self.assertRaisesRegex(frappe.ValidationError, "Cannot change target after progress"):
			doc.save(ignore_permissions=True)
		frappe.db.rollback()
		# The flag is the only way past it, and only code can set a document flag.
		doc = frappe.get_doc("Individual Goal", goal)
		doc.target_value = 80
		doc.flags[review_items.WRITE_BACK_FLAG] = True
		doc.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Individual Goal", goal, "target_value"), 80)
		frappe.db.rollback()


class TestVis10CompletedReviewsNeverChange(_Screens):
	def test_vis10_a_completed_reviews_copies_cannot_change_by_any_path(self):
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		r = self._review(status="HR Review")
		self._as(self.hr_user)
		pa.advance_review_status(r.ap)
		frappe.set_user("Administrator")

		ext = self._ext(r.ap)
		_row_for(ext, r.alone).manager_rating = 1
		with self.assertRaises(frappe.PermissionError):
			review_items.save_review_record(ext)
		frappe.db.rollback()
		self.assertFalse(_row_for(self._ext(r.ap), r.alone).manager_rating)


class TestVis7ScoringReadsCopies(_Screens):
	def test_vis7_scores_come_from_the_reviews_copies_never_the_live_records(self):
		import alvoraa_portal.performance_api as pa

		r = self._review(status="Manager Review")
		row = _row_for(self._ext(r.ap), r.alone).name
		self._as(self.manager_user)
		pa.save_review_item_definition(r.ap, row, weightage=100, title="Copy title")
		pa.save_review_item_rating(r.ap, row, 4)
		frappe.set_user("Administrator")
		frappe.db.set_value("KPI", r.alone, {"manager_rating": 1, "weightage": 30, "kpi_name": "Live title"})
		frappe.db.commit()

		scored = pa._scored_items(frappe.get_doc("Appraisal", r.ap))
		self.assertEqual([(x["label"], x["weightage"], x["score"]) for x in scored], [("Copy title", 100, 4)])
		self._as(self.manager_user)
		suggestions = pa.suggest_ratings(self.subject, r.cycle)
		self.assertEqual({s["item"] for s in suggestions}, {x.name for x in self._ext(r.ap).review_items
		                                                       if x.item_type == "KPI"})

		# A review with no copies is never scored from the live records.
		start, end = self._window()
		cycle = self._cycle(start, end)
		self._kpi(self.stranger, cycle, weightage=100)
		bare = self._appraisal(self.stranger, cycle, status="Manager Review")
		with self.assertRaises(frappe.ValidationError):
			pa._scored_items(frappe.get_doc("Appraisal", bare))


# ── Commit 7 · The definition lock on the live Objective and KPI ───────────


class TestR2DefinitionLockOnLiveRecords(_Screens):
	def test_r2_sec19_a_held_definition_cannot_change_by_any_path(self):
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.goals_api as ga
		import alvoraa_portal.performance_api as pa
		from frappe.client import set_value as desk_set_value

		r = self._review()
		self._as(self.hr_user)
		with self.assertRaisesRegex(frappe.PermissionError, "open review"):
			desk_set_value("KPI", r.alone, "target_value", 1)                     # desk and REST
		with self.assertRaisesRegex(frappe.PermissionError, "open review"):
			pa.hr_save_kpi(self.subject, "Renamed", 50, r.cycle, kpi=r.alone)     # portal
		with self.assertRaisesRegex(frappe.PermissionError, "open review"):
			ga.update_goal(r.goal, target_value=5)

		# Code that skips validation meets it too, for every locked field (decision 8).
		frappe.set_user("Administrator")
		for field, value in (("progress_mode", "Absolute"), ("direction", "Lower is Better"), ("unit", "Days"),
		                     ("baseline_value", 3), ("individual_goal", None), ("weightage", 5),
		                     ("appraisal_cycle", None), ("period_end", add_days(r.end, 1))):
			doc = frappe.get_doc("KPI", r.under)
			doc.set(field, value)
			doc.flags.ignore_validate = True
			with self.assertRaisesRegex(frappe.PermissionError, "open review", msg=field):
				doc.save(ignore_permissions=True)
			frappe.db.rollback()
		goal = frappe.get_doc("Individual Goal", r.goal)
		goal.end_date = add_days(r.end, 1)
		goal.flags.ignore_validate = True
		with self.assertRaisesRegex(frappe.PermissionError, "open review"):
			goal.save(ignore_permissions=True)
		frappe.db.rollback()

		# Facts and status are not locked; cancelling stays possible (decision 20).
		doc = frappe.get_doc("KPI", r.alone)
		doc.actual_value = 7
		doc.save(ignore_permissions=True)
		doc = frappe.get_doc("KPI", r.under)
		doc.status = "Cancelled"
		doc.save(ignore_permissions=True)
		frappe.db.commit()

		# Taken out of the review, the live record is editable again.
		row = _row_for(self._ext(r.ap), r.alone).name
		self._as(self.subject_user)
		pa.remove_review_item(r.ap, row, acknowledge=1)
		frappe.set_user("Administrator")
		self.assertFalse(review_items.holds("KPI", [r.alone]))
		doc = frappe.get_doc("KPI", r.alone)
		doc.target_value = 55
		doc.save(ignore_permissions=True)

	def test_r9_sec22_the_lock_releases_n_days_after_the_cycle_ends_and_0_means_never(self):
		import alvoraa_goals.review_items as review_items

		r = self._review()
		end = frappe.db.get_value("Appraisal Cycle", r.cycle, "end_date")

		def held_on(day):
			with patch("alvoraa_goals.review_items.nowdate", return_value=str(add_days(end, day))):
				return r.alone in review_items.holds("KPI", [r.alone])

		self.assertTrue(held_on(29))
		self.assertFalse(held_on(30))
		# The review keeps the days stamped when its copies were taken (m1): 0 on
		# the review means never.
		frappe.db.set_value("Alvoraa Appraisal Extension", r.ap, "lock_release_days", 0)
		frappe.db.commit()
		self.assertTrue(held_on(400))
		frappe.db.set_value("Alvoraa Appraisal Extension", r.ap, "lock_release_days", 30)
		frappe.db.commit()

		# On the release day an edit goes through, and the copy keeps its own target.
		with patch("alvoraa_goals.review_items.nowdate", return_value=str(add_days(end, 30))):
			doc = frappe.get_doc("KPI", r.alone)
			doc.target_value = 77
			doc.save(ignore_permissions=True)
		frappe.db.commit()
		self.assertEqual(_row_for(self._ext(r.ap), r.alone).target_value, 50)

		# A completed review releases its items at once.
		self._set_status(r.ap, "Completed")
		self.assertFalse(review_items.holds("Individual Goal", [r.goal]))

	def test_r11_a_held_record_cannot_be_deleted_by_any_path(self):
		import alvoraa_portal.performance_api as pa

		r = self._review()
		self._as(self.hr_user)
		with self.assertRaisesRegex(frappe.PermissionError, "open review"):
			pa.delete_kpi(r.alone)
		frappe.set_user("Administrator")
		with self.assertRaisesRegex(frappe.PermissionError, "open review"):
			frappe.delete_doc("Individual Goal", r.goal, force=True, ignore_permissions=True)
		frappe.db.rollback()
		self.assertTrue(frappe.db.exists("KPI", r.alone))
		self.assertTrue(frappe.db.exists("Individual Goal", r.goal))

	def test_decision21_progress_cannot_be_set_by_hand_while_a_review_holds_the_goal(self):
		import alvoraa_portal.goals_api as ga

		r = self._review()
		before = frappe.db.get_value("Individual Goal", r.goal, "actual_progress")
		self._as(self.hr_user)
		with self.assertRaisesRegex(frappe.PermissionError, "open review"):
			ga.set_goal_progress(r.goal, 99)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Individual Goal", r.goal, "actual_progress"), before)

	def test_sec20_only_hr_pulls_work_into_a_cycle_for_their_companies_and_held_items_stay(self):
		import alvoraa_portal.performance_api as pa

		r = self._review()
		# The review's cycle closes while its review is still open, so its items
		# look free to claim. The review still holds them.
		frappe.db.set_value("Appraisal Cycle", r.cycle, "status", "Completed")
		frappe.db.commit()
		later = self._cycle(r.start, r.end)
		loose = self._kpi(self.subject, None, start=r.start, end=r.end)

		self._as(self.subject_user)
		with self.assertRaises(frappe.PermissionError):
			pa.attach_ongoing_to_cycle(later)
		self._as(self.hr_user)
		with self.assertRaises(frappe.PermissionError):
			pa.attach_ongoing_to_cycle(later, employee=self.subject_b)
		out = pa.attach_ongoing_to_cycle(later, employee=self.subject)
		with self.assertRaisesRegex(frappe.PermissionError, "open review"):
			pa.set_cycle_membership("kpi", r.alone, later, 1)

		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("KPI", r.alone, "appraisal_cycle"), r.cycle)
		self.assertEqual(frappe.db.get_value("Individual Goal", r.goal, "appraisal_cycle"), r.cycle)
		self.assertEqual(frappe.db.get_value("KPI", loose, "appraisal_cycle"), later)
		self.assertIn(frappe.db.get_value("KPI", r.alone, "kpi_name"), out["held_by_open_review"]["kpis"])


class TestR3RefreshHook(_Screens):
	def test_r3_approving_a_fact_updates_the_open_reviews_copy_without_opening_it(self):
		import alvoraa_portal.performance_api as pa

		r = self._review()
		pending = self._reading(r.alone, _day(r.start, 9), 7, status="Pending")
		self._as(self.manager_user)
		pa.approve_kpi_update(r.alone, pending, "Approved")
		frappe.set_user("Administrator")
		self.assertEqual(_row_for(self._ext(r.ap), r.alone).actual_value, 17)

	def test_query_count_the_refresh_hook_costs_one_query_when_no_open_review_holds_the_record(self):
		import alvoraa_goals.review_items as review_items

		start, end = self._window()
		loose = frappe.get_doc("KPI", self._kpi(self.stranger, self._cycle(start, end)))
		with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
			review_items.refresh_copies_of(loose)
		self.assertEqual(sql.call_count, 1)

		r = self._review()
		held = frappe.get_doc("KPI", r.alone)
		with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
			review_items.refresh_copies_of(held)
		self.assertLessEqual(sql.call_count, 12)


class TestR2NoUnguardedWritesToLockedFields(FrappeTestCase):
	def _fields(self, call):
		if len(call.args) < 3:
			return None
		arg = call.args[2]
		if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
			return {arg.value}
		if isinstance(arg, ast.Dict) and all(isinstance(k, ast.Constant) for k in arg.keys):
			return {k.value for k in arg.keys}
		return None

	def test_r2_static_no_code_writes_a_locked_field_around_the_lock(self):
		"""frappe.db.set_value skips before_validate. Any function in our apps that
		writes a locked field of a KPI or Objective that way must ask
		review_items.holds() itself (SEC-19)."""
		import importlib
		import os

		from alvoraa_goals.review_items import LOCKED_FIELDS

		every_locked = set().union(*LOCKED_FIELDS.values())
		roots = [os.path.dirname(importlib.import_module(a).__file__) for a in ("alvoraa_portal", "alvoraa_goals")]
		hrms_root = os.path.dirname(importlib.import_module("hrms").__file__)
		roots += [os.path.join(hrms_root, d) for d in os.listdir(hrms_root) if d.startswith("alvoraa_")]

		offenders, guarded_writers = [], set()
		seen = {"db_set": 0, "sql": 0}
		locked_update = re.compile(r"update\s+`?tab(KPI|Individual Goal)`?", re.I)
		for root in roots:
			for dirpath, _dirs, files in os.walk(root):
				if "tests" in dirpath.split(os.sep) or "patches" in dirpath.split(os.sep):
					continue
				for filename in files:
					if not filename.endswith(".py"):
						continue
					path = os.path.join(dirpath, filename)
					with open(path, encoding="utf-8-sig") as f:
						text = f.read()
					for fn in ast.walk(ast.parse(text)):
						if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
							continue
						source = ast.get_source_segment(text, fn) or ""
						guarded = "review_items.holds(" in source
						for call in ast.walk(fn):
							if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.args):
								continue
							# Fix round, security review m6: doc.db_set, raw SQL and
							# query-builder updates skip before_validate as well.
							if call.func.attr == "db_set":
								seen["db_set"] += 1
								arg = call.args[0]
								fields = ({arg.value} if isinstance(arg, ast.Constant) else
								          {k.value for k in arg.keys if isinstance(k, ast.Constant)} if isinstance(arg, ast.Dict)
								          else set())
								if fields & every_locked and not guarded:
									offenders.append(f"{path}:{call.lineno} db_set")
								continue
							if call.func.attr in ("sql", "multisql"):
								seen["sql"] += 1
								if locked_update.search(ast.get_source_segment(text, call.args[0]) or "") and not guarded:
									offenders.append(f"{path}:{call.lineno} sql")
								continue
							if (call.func.attr == "update" and isinstance(call.func.value, ast.Attribute)
							        and call.func.value.attr == "qb"):
								if (re.search(r"DocType\(\s*[\"'](KPI|Individual Goal)[\"']", source)
								        and any(f".{field})" in source or f".{field}," in source for field in every_locked)
								        and not guarded):
									offenders.append(f"{path}:{call.lineno} qb.update")
								continue
							if call.func.attr != "set_value":
								continue
							target, fields = call.args[0], self._fields(call)
							if isinstance(target, ast.Constant):
								if target.value not in LOCKED_FIELDS:
									continue
								risky = fields is None or bool(fields & set(LOCKED_FIELDS[target.value]))
							else:
								# A doctype in a variable: flag it when it names a locked field.
								risky = bool(fields and fields & every_locked)
							if risky and not guarded:
								offenders.append(f"{path}:{call.lineno}")
							elif risky:
								guarded_writers.add(fn.name)
		self.assertEqual(sorted(set(offenders)), [])
		self.assertTrue(seen["db_set"] and seen["sql"], seen)
		# The scan really read the code: the two writers that ask first were found.
		self.assertTrue({"attach_ongoing_to_cycle", "set_cycle_membership"} <= guarded_writers, guarded_writers)


# ── Decision 2 · The person says which day a KPI reading is for ─────────────


class TestDecision2ReadingDate(_Screens):
	"""log_kpi_progress takes a date, checks it, and keeps the live number honest."""

	def _kpi_of_subject(self, mode="Cumulative", start=None, end=None, target=100, cycle=True):
		"""A KPI of the subject's, with a period around today unless told otherwise.

		A KPI with no period of its own takes its cycle's, so "no period" means
		no cycle either.
		"""
		if cycle:
			cycle = self._cycle(add_days(frappe.utils.today(), -60), add_days(frappe.utils.today(), 60))
		else:
			cycle = None
		return self._kpi(self.subject, cycle, target=target, mode=mode, start=start, end=end)

	def test_decision2_a_blank_date_means_today_and_a_chosen_day_is_kept(self):
		import alvoraa_portal.performance_api as pa

		kpi = self._kpi_of_subject(start=add_days(frappe.utils.today(), -40),
		                           end=add_days(frappe.utils.today(), 40))
		self._as(self.subject_user)
		pa.log_kpi_progress(kpi, 10, note="today")
		chosen = add_days(frappe.utils.today(), -5)
		pa.log_kpi_progress(kpi, 15, note="back-dated", log_date=chosen)
		frappe.set_user("Administrator")

		dates = [str(r.log_date) for r in frappe.get_doc("KPI", kpi).progress_log]
		self.assertIn(str(frappe.utils.getdate(frappe.utils.today())), dates)
		self.assertIn(str(frappe.utils.getdate(chosen)), dates)

	def test_decision2_a_future_day_or_a_day_before_the_period_is_refused(self):
		import alvoraa_portal.performance_api as pa

		start = add_days(frappe.utils.today(), -10)
		kpi = self._kpi_of_subject(start=start, end=add_days(frappe.utils.today(), 30))
		self._as(self.subject_user)
		with self.assertRaises(frappe.ValidationError):
			pa.log_kpi_progress(kpi, 5, log_date=add_days(frappe.utils.today(), 1))
		with self.assertRaises(frappe.ValidationError):
			pa.log_kpi_progress(kpi, 5, log_date=add_days(start, -1))
		with self.assertRaises(frappe.ValidationError):
			pa.log_kpi_progress(kpi, 5, log_date="not a date")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.get_doc("KPI", kpi).progress_log, [])

	def test_decision2_a_kpi_with_no_period_accepts_a_year_back_and_no_more(self):
		import alvoraa_portal.performance_api as pa

		kpi = self._kpi_of_subject(cycle=False)
		self.assertFalse(frappe.db.get_value("KPI", kpi, "period_start"))
		self._as(self.subject_user)
		pa.log_kpi_progress(kpi, 5, log_date=add_days(frappe.utils.today(), -300))
		with self.assertRaises(frappe.ValidationError):
			pa.log_kpi_progress(kpi, 5, log_date=add_days(frappe.utils.today(), -400))
		frappe.set_user("Administrator")
		self.assertEqual(len(frappe.get_doc("KPI", kpi).progress_log), 1)

	def test_decision1_a_cumulative_reading_adds_up_and_an_absolute_one_replaces(self):
		"""The dialog asks for the amount since the last update, so the server adds
		it - once the reading is approved (fix round, code review M2)."""
		import alvoraa_portal.performance_api as pa

		cumulative = self._kpi_of_subject()
		absolute = self._kpi_of_subject(mode="Absolute")
		self._as(self.subject_user)
		rows = [
			pa.log_kpi_progress(cumulative, 10)["row_name"],
			pa.log_kpi_progress(cumulative, 15)["row_name"],
		]
		latest = pa.log_kpi_progress(absolute, 60)["row_name"]
		# Dated before the reading already logged, so it is history, not the number now.
		older = pa.log_kpi_progress(absolute, 20, log_date=add_days(frappe.utils.today(), -3))["row_name"]
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("KPI", cumulative, "actual_value"), 0)
		self.assertEqual(frappe.db.get_value("KPI", absolute, "actual_value"), 0)

		self._as(self.manager_user)
		for row in rows:
			pa.approve_kpi_update(cumulative, row, "Approved")
		pa.approve_kpi_update(absolute, latest, "Approved")
		pa.approve_kpi_update(absolute, older, "Approved")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("KPI", cumulative, "actual_value"), 25)
		self.assertEqual(frappe.db.get_value("KPI", absolute, "actual_value"), 60)


# ── Decision 23 · The three review settings on the portal's Org Settings ────


class TestDecision23ReviewSettingsScreen(_Screens):
	"""HR reads and writes the three settings; they live on HR Settings (SEC-28)."""

	def setUp(self):
		super().setUp()
		import alvoraa_goals.review_items as review_items

		self._before = {
			field: frappe.db.get_single_value("HR Settings", field)
			for field in review_items.SETTING_FIELDS.values()
		}

	def tearDown(self):
		for field, value in self._before.items():
			frappe.db.set_single_value("HR Settings", field, value)
		frappe.db.commit()
		super().tearDown()

	def test_decision23_an_hr_manager_reads_and_saves_the_three_settings(self):
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		self._as(self.hr_user)
		shown = pa.get_review_settings()
		self.assertEqual(set(shown["freeze_points"]), set(review_items.FREEZE_POINTS))
		self.assertEqual(set(shown["removal_modes"]), set(review_items.REMOVAL_MODES))
		self.assertTrue(shown["can_edit"])

		saved = pa.save_review_settings(review_items.FREEZE_SELF_SENT, "45", review_items.REMOVAL_KEEP)
		frappe.set_user("Administrator")
		self.assertEqual(saved["lock_release_days"], 45)
		self.assertEqual(review_items.review_settings(), {
			"freeze_point": review_items.FREEZE_SELF_SENT,
			"lock_release_days": 45,
			"removal_mode": review_items.REMOVAL_KEEP,
		})

	def test_decision23_a_value_outside_the_list_is_refused(self):
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		self._as(self.hr_user)
		for args in (
			("Whenever", "30", review_items.REMOVAL_DISCARD),
			(review_items.FREEZE_HR_SENT, "30", "Shred it"),
			(review_items.FREEZE_HR_SENT, "-1", review_items.REMOVAL_DISCARD),
			(review_items.FREEZE_HR_SENT, "9999", review_items.REMOVAL_DISCARD),
			(review_items.FREEZE_HR_SENT, "thirty", review_items.REMOVAL_DISCARD),
		):
			with self.assertRaises(frappe.ValidationError, msg=args):
				pa.save_review_settings(*args)
		frappe.set_user("Administrator")

	def test_sec28_an_employee_cannot_read_or_change_the_review_settings(self):
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		for user in (self.subject_user, self.manager_user):
			self._as(user)
			with self.assertRaises(frappe.PermissionError, msg=user):
				pa.get_review_settings()
			with self.assertRaises(frappe.PermissionError, msg=user):
				pa.save_review_settings(review_items.FREEZE_SELF_SENT, "5", review_items.REMOVAL_KEEP)
		frappe.set_user("Administrator")

	def test_sec28_an_hr_user_reads_the_settings_but_only_an_hr_manager_saves_them(self):
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		self._as(self.hr_desk_user)
		self.assertFalse(pa.get_review_settings()["can_edit"])
		with self.assertRaises(frappe.PermissionError):
			pa.save_review_settings(review_items.FREEZE_SELF_SENT, "5", review_items.REMOVAL_KEEP)
		frappe.set_user("Administrator")
