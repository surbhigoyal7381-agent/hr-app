"""Slice 010 group D, decision 34 (security review M3, Q2, R4).

Nobody in the subject's reporting line - their manager or anyone above them -
does the HR steps on that review, even when they hold an HR role. A different
HR person does them. The manager steps stay with the manager.

HR steps: calibration, HR removal (and deletion) of review items, HR's answer to
a rating question, sending a review back from HR Review, and completing it; and,
in the desk, changing the HRMS Appraisal from HR Review on.

Starts from the shipped permissions, like the other 010 tests. Synthetic people
and records only, tagged S010D.
"""

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal.tests.test_portal_security_010 import _employee, _user
from alvoraa_portal.tests.test_review_copies_010d import _day, _row_for, _uid
from alvoraa_portal.tests.test_review_screens_010d import _Screens

ASK_ANOTHER = "Ask another HR person in"


class _LineHr(_Screens):
	"""hr_boss (HR Manager) manages hr_report. top (HR Manager) is two levels
	above leaf, through mid, who holds no HR role."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.top_user = _user("d.line.top", ("HR Manager", "Employee"))
		cls.top = _employee("DLineTop", company=cls.company_a, user=cls.top_user)
		cls.mid_user = _user("d.line.mid", ("Employee",))
		cls.mid = _employee("DLineMid", company=cls.company_a, reports_to=cls.top, user=cls.mid_user)
		cls.leaf_user = _user("d.line.leaf", ("Employee",))
		cls.leaf = _employee("DLineLeaf", company=cls.company_a, reports_to=cls.mid, user=cls.leaf_user)

	def _review_for(self, employee, employee_user, status):
		"""A review with copies of one Objective, a KPI under it and a standalone KPI."""
		import alvoraa_portal.performance_api as pa

		start, end = self._window()
		cycle = self._cycle(start, end)
		goal = self._goal(employee, cycle, start, end, target=100)
		under = self._kpi(employee, cycle, target=100, goal=goal)
		alone = self._kpi(employee, cycle, target=50)
		self._reading(under, _day(start, 1), 40)
		self._reading(alone, _day(start, 2), 10)
		ap = self._appraisal(employee, cycle, status="Employee Review")
		self._as(employee_user)
		pa.get_my_review(ap)
		frappe.set_user("Administrator")
		self._set_status(ap, status)
		return frappe._dict(ap=ap, cycle=cycle, start=start, goal=goal, under=under, alone=alone)

	def _flag_from_a_rater_who_left(self, r, manager_user):
		"""The manager rates in Manager Review; a later fact raises questions on the
		item and overall ratings; the rater is then recorded as someone who has left.
		Leaves the review in HR Review with both questions open."""
		import alvoraa_portal.performance_api as pa

		self._set_status(r.ap, "Manager Review")
		alone = _row_for(self._ext(r.ap), r.alone).name
		self._as(manager_user)
		pa.save_review_item_rating(r.ap, alone, 4)
		pa.save_manager_review(r.ap, "feedback", overall_rating=4)
		frappe.set_user("Administrator")
		self._reading(r.alone, _day(r.start, 5), 7)
		left = _user(f"d.line.left.{_uid()}", ("Employee",))
		frappe.db.set_value("User", left, "enabled", 0)
		frappe.db.set_value("Alvoraa Review Item", alone, "manager_rated_by", left)
		frappe.db.set_value("Alvoraa Appraisal Extension", r.ap, "overall_rated_by", left)
		self._set_status(r.ap, "HR Review")
		self._as(self.hr_user)
		pa.get_manager_review(r.ap)     # the refresh raises the questions
		frappe.set_user("Administrator")
		ext = self._ext(r.ap)
		self.assertEqual((_row_for(ext, r.alone).manager_flag, ext.overall_rating_flag), (1, 1))
		return alone

	def _refusal_lines(self, user, calls):
		"""Run each call as `user`; return {name: (refused with the D34 message, logged rule)}."""
		out = {}
		for name, call in calls:
			logger = MagicMock()
			self._as(user)
			try:
				with patch("frappe.logger", return_value=logger):
					call()
				out[name] = (False, None)
			except frappe.PermissionError as e:
				rules = [json.loads(c[0][0]) for c in logger.warning.call_args_list]
				out[name] = (ASK_ANOTHER in str(e), [(r["rule"], r["endpoint"], r["name"]) for r in rules])
			finally:
				frappe.set_user("Administrator")
		return out


class TestD34ManagerWithHrRoleIsRefusedEveryHrStep(_LineHr):
	def test_d34_a_manager_with_hr_manager_is_refused_each_hr_step_and_each_refusal_is_logged(self):
		import alvoraa_portal.performance_api as pa

		r = self._review_for(self.hr_report, self.hr_report_user, "HR Review")
		under = _row_for(self._ext(r.ap), r.under).name
		alone = self._flag_from_a_rater_who_left(r, self.hr_boss_user)
		company = frappe.db.get_value("Employee", self.hr_report, "company")

		results = self._refusal_lines(self.hr_boss_user, (
			("save_calibration_note", lambda: pa.save_calibration_note(r.ap, "calibrated", 2)),
			("remove_review_item", lambda: pa.remove_review_item(r.ap, under, reason="why", acknowledge=1)),
			("delete_review_item", lambda: pa.delete_review_item(r.ap, under, acknowledge=1)),
			("answer_rating_flag", lambda: pa.answer_rating_flag(r.ap, alone, keep=1, reason="left")),
			("answer_rating_flag overall", lambda: pa.answer_rating_flag(r.ap, "overall", keep=0, rating=2, reason="left")),
			("return_for_revision", lambda: pa.return_for_revision(r.ap, "back")),
			("advance_review_status", lambda: pa.advance_review_status(r.ap)),
		))
		for name, (message, lines) in results.items():
			self.assertTrue(message, f"{name} was not refused with the decision 34 message: {lines}")
			endpoint = name.split(" ")[0]
			self.assertEqual(lines, [("D34", endpoint, r.ap)], name)

		# Nothing moved.
		ext = self._ext(r.ap)
		self.assertEqual(ext.review_status, "HR Review")
		self.assertEqual(ext.overall_rating, 4)
		self.assertEqual((ext.overall_rating_flag, _row_for(ext, r.alone).manager_flag), (1, 1))
		self.assertFalse(_row_for(ext, r.under).removed)

		# The message names the company, never a person.
		self._as(self.hr_boss_user)
		with self.assertRaises(frappe.PermissionError) as refused:
			pa.advance_review_status(r.ap)
		frappe.set_user("Administrator")
		self.assertIn(f"Ask another HR person in {company} to do this step.", str(refused.exception))
		self.assertNotIn(frappe.db.get_value("Employee", self.hr_report, "employee_name"), str(refused.exception))

	def test_d34_a_skip_level_manager_with_an_hr_role_is_refused(self):
		import alvoraa_portal.performance_api as pa

		r = self._review_for(self.leaf, self.leaf_user, "HR Review")
		under = _row_for(self._ext(r.ap), r.under).name
		results = self._refusal_lines(self.top_user, (
			("save_calibration_note", lambda: pa.save_calibration_note(r.ap, "calibrated", 2)),
			("remove_review_item", lambda: pa.remove_review_item(r.ap, under, reason="why", acknowledge=1)),
			("return_for_revision", lambda: pa.return_for_revision(r.ap, "back")),
			("advance_review_status", lambda: pa.advance_review_status(r.ap)),
		))
		for name, (message, lines) in results.items():
			self.assertTrue(message, f"{name}: {lines}")
			self.assertEqual(lines, [("D34", name, r.ap)], name)
		self.assertEqual(self._ext(r.ap).review_status, "HR Review")

	def test_d34_the_hr_stand_in_for_someone_with_no_manager_is_refused(self):
		import alvoraa_portal.performance_api as pa
		from alvoraa_goals.permissions import get_hr_manager_employee

		stand_in = get_hr_manager_employee()
		if not stand_in:
			self.skipTest("no HR Manager employee on this site")
		stand_in_user = frappe.db.get_value("Employee", stand_in, "user_id")
		company = frappe.db.get_value("Employee", stand_in, "company")
		user = _user(f"d.line.lone.{_uid()}", ("Employee",))
		lone = _employee(f"DLineLone{_uid()}", company=company, user=user)
		self._cleanup.append(("Employee", lone))
		ap = self._review_of(lone, "HR Review", company=company)
		results = self._refusal_lines(stand_in_user, (
			("advance_review_status", lambda: pa.advance_review_status(ap)),
		))
		self.assertEqual(results["advance_review_status"], (True, [("D34", "advance_review_status", ap)]))


class TestD34AnotherHrPersonDoesTheHrSteps(_LineHr):
	def test_d34_a_different_hr_person_removes_answers_and_completes(self):
		import alvoraa_portal.performance_api as pa

		r = self._review_for(self.hr_report, self.hr_report_user, "HR Review")
		under = _row_for(self._ext(r.ap), r.under).name
		alone = self._flag_from_a_rater_who_left(r, self.hr_boss_user)

		self._as(self.hr_user)
		self.assertEqual(pa.remove_review_item(r.ap, under, reason="not this cycle", acknowledge=1)["ok"], True)
		pa.answer_rating_flag(r.ap, alone, keep=1, reason="manager left")
		pa.answer_rating_flag(r.ap, "overall", keep=1, reason="manager left")
		self.assertEqual(pa.advance_review_status(r.ap)["review_status"], "Completed")
		frappe.set_user("Administrator")

	def test_d34_a_different_hr_person_calibrates_and_sends_back(self):
		import alvoraa_portal.performance_api as pa

		r = self._review_for(self.leaf, self.leaf_user, "HR Review")
		self._as(self.hr_user)
		try:
			pa.save_calibration_note(r.ap, "calibrated", 2)
		except frappe.PermissionError:
			self.fail("another HR person was refused calibration")
		except Exception:
			frappe.db.rollback()   # past every permission check; the note column is a separate bug (F-D8)
		frappe.set_user("Administrator")
		self._set_status(r.ap, "HR Review")
		self._as(self.hr_user)
		self.assertEqual(pa.return_for_revision(r.ap, "please add evidence")["review_status"], "Employee Review")
		frappe.set_user("Administrator")


class TestD34ManagerStepsStayWithTheManager(_LineHr):
	def test_d34_the_manager_with_an_hr_role_still_rates_in_manager_review(self):
		import alvoraa_portal.performance_api as pa

		r = self._review_for(self.hr_report, self.hr_report_user, "Manager Review")
		alone = _row_for(self._ext(r.ap), r.alone).name
		self._as(self.hr_boss_user)
		review = pa.get_manager_review(r.ap)
		self.assertEqual((review["viewer_role"], review["hr_steps_elsewhere"]), ("manager", 0))
		pa.save_review_item_rating(r.ap, alone, 4, comment="good")
		pa.save_overall_rating(r.ap, 4)
		frappe.set_user("Administrator")
		ext = self._ext(r.ap)
		self.assertEqual((_row_for(ext, r.alone).manager_rating, ext.overall_rating), (4, 4))

	def test_d34_the_manager_still_reads_the_review_in_hr_review(self):
		import alvoraa_portal.performance_api as pa

		r = self._review_for(self.hr_report, self.hr_report_user, "HR Review")
		self._as(self.hr_boss_user)
		review = pa.get_manager_review(r.ap)
		frappe.set_user("Administrator")
		self.assertEqual(review["appraisal"], r.ap)


class TestD34PageHidesHrButtonsForTheLine(_LineHr):
	def test_d34_screens_tell_the_page_who_must_not_see_hr_buttons(self):
		import alvoraa_portal.performance_api as pa

		r = self._review_for(self.hr_report, self.hr_report_user, "HR Review")

		self._as(self.hr_boss_user)
		review = pa.get_manager_review(r.ap)
		self.assertEqual((review["viewer_role"], review["hr_steps_elsewhere"]), ("manager", 1))
		listed = {a["name"]: a for a in pa.hr_list_appraisals(r.cycle)}
		self.assertEqual(listed[r.ap]["hr_steps_elsewhere"], 1)
		calibration = {c["appraisal"]: c for c in pa.get_calibration_overview(r.cycle)["rows"]}
		self.assertEqual(calibration[r.ap]["hr_steps_elsewhere"], 1)
		team = {t["appraisal"]: t for t in pa.get_team_reviews(r.cycle)["team"] if t.get("appraisal")}
		self.assertEqual(team[r.ap]["hr_steps_elsewhere"], 1)

		self._as(self.hr_user)
		review = pa.get_manager_review(r.ap)
		self.assertEqual((review["viewer_role"], review["hr_steps_elsewhere"]), ("hr", 0))
		listed = {a["name"]: a for a in pa.hr_list_appraisals(r.cycle)}
		self.assertEqual(listed[r.ap]["hr_steps_elsewhere"], 0)
		calibration = {c["appraisal"]: c for c in pa.get_calibration_overview(r.cycle)["rows"]}
		self.assertEqual(calibration[r.ap]["hr_steps_elsewhere"], 0)
		frappe.set_user("Administrator")

	def test_d34_the_desk_refuses_the_line_a_change_to_the_hrms_appraisal_from_hr_review(self):
		r = self._review_for(self.hr_report, self.hr_report_user, "HR Review")
		doc = frappe.get_doc("Appraisal", r.ap)
		self.assertFalse(frappe.has_permission("Appraisal", "write", doc, user=self.hr_boss_user))
		self.assertTrue(frappe.has_permission("Appraisal", "read", doc, user=self.hr_boss_user))
		self.assertTrue(frappe.has_permission("Appraisal", "write", doc, user=self.hr_user))
		self._set_status(r.ap, "Manager Review")
		self.assertTrue(frappe.has_permission("Appraisal", "write", doc, user=self.hr_boss_user))


class TestD34Page(FrappeTestCase):
	def test_d34_the_page_shows_a_note_instead_of_hr_buttons_for_the_line(self):
		from alvoraa_portal.tests.test_review_page_010d import _between, _page

		page = _page()
		note = _between(page, "window.pfHrStepsElsewhereNote = function()", "window.pfFinishHrReview")
		self.assertIn("Another HR person needs to do the HR steps for this review, because they report to you.", note)

		team_row = _between(page, 'status === "HR Review" && m.hr_steps_elsewhere', '} else if (status === "HR Review") {')
		self.assertNotIn("pfFinishHrReview", team_row)
		self.assertIn("pfHrStepsElsewhereNote()", team_row)

		hr_row = _between(page, 'a.review_status === "HR Review" && a.hr_steps_elsewhere', '} else if (a.review_status === "HR Review")')
		self.assertNotIn("pfFinishHrReview", hr_row)
		self.assertIn("pfHrStepsElsewhereNote()", hr_row)

		calibration = _between(page, "function pfHrCalibration(r, cycle)", "function pfHrLeadershipPrinciples")
		self.assertIn("row.appraisal && row.hr_steps_elsewhere\n            ? pfHrStepsElsewhereNote()",
		              calibration.replace("\r\n", "\n"))

		finalize = _between(page, "function prRenderHrFinalizePage(d)", "window.prFinishHrReview")
		self.assertIn("var elsewhere = !!d.hr_steps_elsewhere;", finalize)
		self.assertIn('(elsewhere ? "" :', finalize)
		submit = _between(page, "function prRenderManagerSubmitPage(d, editable)", "var mgfPS")
		self.assertIn('(_pr.viewerRole === "hr" || d.hr_steps_elsewhere) && d.review_status === "HR Review"', submit)
