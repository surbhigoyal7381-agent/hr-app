"""Slice 010 (Wave 0a): pin tests for the portal security and privacy fixes.

One class per requirement in
docs/slices/010-portal-security-fixes/01c-security-privacy-requirements.md.
Each test is named after the rule it keeps closed, so a merge that drops a fix
fails CI here instead of in front of a user. The refusal is always tested, not
only the allowed case.

These live in alvoraa_portal because CI runs only the alvoraa_portal and
alvoraa_goals suites; tests in our hrms modules never run there.

Synthetic people only, all carrying the S010 tag.
"""

import json
import os
import re
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_goals.tests.utils import _ensure_erpnext_company_prerequisites, ensure_company, ensure_gender
from alvoraa_portal.tests.leave_fixtures import (
	WEEK_MON,
	ensure_employee_with_leave,
	ensure_leave_type,
	ensure_user,
	link_user_to_employee,
	reset_leave_applications,
)

TAG = "S010"
SECOND_COMPANY = "S010 Second Company"


# ── fixtures ────────────────────────────────────────────────────────────────


def _user(local, roles):
	return ensure_user(f"s010.{local}@example.com", roles=roles)


def _employee(first, company=None, reports_to=None, user=None):
	"""A test employee, reset to the given company, manager and login.

	Saved through the document so Employee's nested set (lft/rgt) follows
	reports_to - the people-search scope reads it.
	"""
	name = frappe.db.get_value("Employee", {"first_name": first, "last_name": TAG}, "name")
	if name:
		doc = frappe.get_doc("Employee", name)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": first,
				"last_name": TAG,
				"gender": ensure_gender(),
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2025-01-01",
			}
		)
	doc.company = company or ensure_company()
	doc.status = "Active"
	doc.reports_to = reports_to
	doc.user_id = user
	# No automatic "Employee = self" User Permission. It narrows every list the
	# user sees, so a test about OUR rules would pass or fail because of it.
	doc.create_user_permission = 0
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	if user:
		frappe.db.delete("User Permission", {"user": user})
		frappe.clear_cache(user=user)
	frappe.db.commit()
	return doc.name


def _second_company():
	"""A second company, kept the OLDEST company on the site.

	ensure_company() hands every other test the newest company. A company
	created here would quietly become every other test's company - one with no
	holiday list or fiscal year - so its creation date is set far back.
	Call this BEFORE ensure_company().
	"""
	if not frappe.db.exists("Company", SECOND_COMPANY):
		ensure_company()   # on a fresh site the ordinary test company must exist first
		_ensure_erpnext_company_prerequisites()
		doc = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": SECOND_COMPANY,
				"abbr": "S10SC",
				"default_currency": "INR",
				"country": "India",
			}
		)
		doc.insert(ignore_permissions=True)
	frappe.db.set_value("Company", SECOND_COMPANY, "creation", "2000-01-01 00:00:00", update_modified=False)
	frappe.db.commit()
	return SECOND_COMPANY


def _goal(employee, suffix=""):
	doc = frappe.get_doc(
		{
			"doctype": "Individual Goal",
			"employee": employee,
			"goal_name": f"{TAG} Goal {suffix}",
			"target_value": 100,
			"start_date": add_days(nowdate(), -10),
			"end_date": add_days(nowdate(), 50),
		}
	)
	doc.append("progress_updates", {"log_date": nowdate(), "value": 5, "approval_status": "Pending"})
	doc.append(
		"evidence_items",
		{"evidence_type": "Manual Entry", "value": 5, "validation_status": "Pending", "uploaded_by": "Administrator"},
	)
	doc.insert(ignore_permissions=True)
	return doc


def _kpi(employee, suffix=""):
	doc = frappe.get_doc(
		{"doctype": "KPI", "kpi_name": f"{TAG} KPI {suffix}", "employee": employee, "target_value": 10}
	)
	doc.append("progress_log", {"log_date": nowdate(), "value": 1, "approval_status": "Pending"})
	doc.insert(ignore_permissions=True)
	return doc


def _all_keys(value):
	"""Every dict key anywhere inside a JSON-like value."""
	if isinstance(value, dict):
		keys = set(value)
		for v in value.values():
			keys |= _all_keys(v)
		return keys
	if isinstance(value, (list, tuple)):
		keys = set()
		for v in value:
			keys |= _all_keys(v)
		return keys
	return set()


class _Base(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._cleanup = []

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		# Some endpoints commit, so rollback alone does not remove what they wrote.
		for doctype, name in reversed(self._cleanup):
			if frappe.db.exists(doctype, name):
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
		frappe.db.commit()


# ── SEC-9 · Nobody decides their own request (S7) ───────────────────────────


class TestSec9NobodyDecidesTheirOwnRequest(_Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from alvoraa_portal import attendance_correction as ac

		ac.after_migrate()
		frappe.clear_cache(doctype=ac.REQUEST)
		cls.hr_self = _user("hr.self", ("HR Manager", "Employee"))
		cls.hr_other = _user("hr.other", ("HR Manager", "Employee"))
		cls.emp_self = _employee("HrSelf", user=cls.hr_self)
		cls.emp_other = _employee("HrOther", user=cls.hr_other)

	def _correction(self, employee):
		doc = frappe.get_doc(
			{
				"doctype": "Attendance Request",
				"employee": employee,
				"company": ensure_company(),
				"from_date": add_days(nowdate(), -3),
				"to_date": add_days(nowdate(), -3),
				"reason": "On Duty",
				"alvoraa_review_status": "Waiting",
			}
		)
		# Frappe HR's own date and holiday checks are not what is under test.
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True)
		return doc

	def test_sec9_decide_refuses_own_attendance_correction(self):
		from alvoraa_portal import attendance_correction as ac

		doc = self._correction(self.emp_self)
		frappe.set_user(self.hr_self)
		with self.assertRaisesRegex(frappe.PermissionError, "cannot decide your own request"):
			ac.decide(doc.name, approve=1)
		with self.assertRaisesRegex(frappe.PermissionError, "cannot decide your own request"):
			ac.decide(doc.name, approve=0, note="declining my own")
		frappe.set_user("Administrator")
		row = frappe.db.get_value(ac.REQUEST, doc.name, ["docstatus", "alvoraa_review_status"], as_dict=True)
		self.assertEqual(row.docstatus, 0)
		self.assertEqual(row.alvoraa_review_status, "Waiting")

	def test_sec9_to_review_leaves_out_own_requests(self):
		from alvoraa_portal import attendance_correction as ac

		doc = self._correction(self.emp_self)
		frappe.set_user(self.hr_self)
		self.assertNotIn(doc.name, [r["name"] for r in ac.to_review(limit=500)])
		frappe.set_user(self.hr_other)
		self.assertIn(doc.name, [r["name"] for r in ac.to_review(limit=500)])

	def test_sec9_desk_submit_of_own_attendance_request_is_refused(self):
		hooks = frappe.get_hooks("doc_events").get("Attendance Request", {}).get("before_submit", [])
		self.assertIn("hrms.alvoraa_hr_core.access.refuse_own_submit", hooks)
		doc = self._correction(self.emp_self)
		frappe.set_user(self.hr_self)
		with self.assertRaisesRegex(frappe.PermissionError, "cannot decide your own request"):
			doc.run_method("before_submit")
		frappe.set_user(self.hr_other)
		doc.run_method("before_submit")  # someone else: allowed

	def test_sec9_desk_submit_of_own_leave_is_refused_even_when_hr_settings_allow_it(self):
		lt = ensure_leave_type("Alvoraa Casual")
		emp = ensure_employee_with_leave("S010Leave", lt, days=10, last_name="Self")
		link_user_to_employee(emp, self.hr_self)
		frappe.db.set_value("Employee", self.emp_self, "user_id", None)
		frappe.db.delete("User Permission", {"user": ["in", [self.hr_self, self.hr_other]]})
		frappe.clear_cache(user=self.hr_self)
		frappe.clear_cache(user=self.hr_other)
		reset_leave_applications(emp)
		was = frappe.db.get_single_value("HR Settings", "prevent_self_leave_approval")
		frappe.db.set_single_value("HR Settings", "prevent_self_leave_approval", 0)
		try:
			la = frappe.get_doc(
				{
					"doctype": "Leave Application",
					"employee": emp,
					"leave_type": lt,
					"from_date": WEEK_MON,
					"to_date": WEEK_MON,
					"status": "Open",
					"company": frappe.db.get_value("Employee", emp, "company"),
				}
			)
			la.insert(ignore_permissions=True)
			la.status = "Approved"
			frappe.set_user(self.hr_self)
			with self.assertRaisesRegex(frappe.PermissionError, "cannot decide your own request"):
				la.submit()
			frappe.set_user("Administrator")
			self.assertEqual(frappe.db.get_value("Leave Application", la.name, "docstatus"), 0)

			# HR submitting SOMEONE ELSE's leave is still allowed.
			la.reload()
			la.status = "Approved"
			frappe.set_user(self.hr_other)
			la.submit()
			frappe.set_user("Administrator")
			self.assertEqual(frappe.db.get_value("Leave Application", la.name, "docstatus"), 1)
		finally:
			frappe.set_user("Administrator")
			frappe.db.rollback()
			frappe.db.set_single_value("HR Settings", "prevent_self_leave_approval", was)
			frappe.db.set_value("Employee", emp, "user_id", None)
			_employee("HrSelf", user=self.hr_self)
			reset_leave_applications(emp)

	def test_sec9_action_leave_refuses_own_even_as_named_approver(self):
		from alvoraa_portal import hr_api

		lt = ensure_leave_type("Alvoraa Casual")
		emp = ensure_employee_with_leave("S010Leave", lt, days=10, last_name="Self")
		link_user_to_employee(emp, self.hr_self)
		frappe.db.set_value("Employee", self.emp_self, "user_id", None)
		reset_leave_applications(emp)
		try:
			la = frappe.get_doc(
				{
					"doctype": "Leave Application",
					"employee": emp,
					"leave_type": lt,
					"from_date": WEEK_MON,
					"to_date": WEEK_MON,
					"status": "Open",
					"leave_approver": self.hr_self,
					"company": frappe.db.get_value("Employee", emp, "company"),
				}
			)
			la.insert(ignore_permissions=True)
			frappe.set_user(self.hr_self)
			self.assertFalse(hr_api._can_action_leave(la.name))
			with self.assertRaisesRegex(frappe.PermissionError, "cannot decide your own request"):
				hr_api.action_leave(la.name, "approve")
			frappe.set_user("Administrator")
			row = frappe.db.get_value("Leave Application", la.name, ["docstatus", "status"], as_dict=True)
			self.assertEqual((row.docstatus, row.status), (0, "Open"))
		finally:
			frappe.set_user("Administrator")
			frappe.db.rollback()
			frappe.db.set_value("Employee", emp, "user_id", None)
			_employee("HrSelf", user=self.hr_self)
			reset_leave_applications(emp)

	def test_sec9_approve_kpi_update_refuses_own(self):
		from alvoraa_portal import performance_api

		kpi = _kpi(self.emp_self, "own")
		frappe.db.commit()
		self._cleanup.append(("KPI", kpi.name))
		row = kpi.progress_log[0].name
		frappe.set_user(self.hr_self)
		with self.assertRaisesRegex(frappe.PermissionError, "cannot decide your own request"):
			performance_api.approve_kpi_update(kpi.name, row, "Approved")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("KPI Progress Log", row, "approval_status"), "Pending")

		frappe.set_user(self.hr_other)
		performance_api.approve_kpi_update(kpi.name, row, "Approved")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("KPI Progress Log", row, "approval_status"), "Approved")

	def test_sec9_approve_goal_update_refuses_own_and_the_flag_agrees(self):
		from alvoraa_portal import goals_api

		goal = _goal(self.emp_self, "own-update")
		frappe.db.commit()
		self._cleanup.append(("Individual Goal", goal.name))
		row = goal.progress_updates[0].name
		frappe.set_user(self.hr_self)
		self.assertFalse(any(r["can_action"] for r in goals_api.get_goal_update_log(goal.name)))
		with self.assertRaisesRegex(frappe.PermissionError, "cannot decide your own request"):
			goals_api.approve_goal_update(goal.name, row, "Approved")
		pending = goals_api.get_pending_approvals()
		self.assertNotIn(goal.name, [g["goal"] for g in pending["goal_updates"]])
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Goal Progress Update", row, "approval_status"), "Pending")

		frappe.set_user(self.hr_other)
		self.assertTrue(all(r["can_action"] for r in goals_api.get_goal_update_log(goal.name)))

	def test_sec9_evidence_approve_and_reject_refuse_own(self):
		from alvoraa_goals.controllers import evidence

		goal = _goal(self.emp_self, "own-evidence")
		row = goal.evidence_items[0].name
		frappe.set_user(self.hr_self)
		self.assertFalse(evidence.can_validate_evidence(goal.name))
		with self.assertRaisesRegex(frappe.PermissionError, "cannot decide your own request"):
			evidence.approve_evidence(goal.name, 0)
		with self.assertRaisesRegex(frappe.PermissionError, "cannot decide your own request"):
			evidence.reject_evidence(goal.name, 0, "no")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Goal Evidence", row, "validation_status"), "Pending")

	def test_sec17_a_refusal_is_logged_without_field_values(self):
		from hrms.alvoraa_hr_core import access

		logger = MagicMock()
		frappe.set_user(self.hr_self)
		with patch("frappe.logger", return_value=logger):
			with self.assertRaisesRegex(frappe.PermissionError, "cannot decide your own request"):
				access.refuse_own_decision(self.emp_self, "KPI", "KPI-X", "test.endpoint")
		line = json.loads(logger.warning.call_args[0][0])
		self.assertEqual(
			{k: line[k] for k in ("user", "endpoint", "doctype", "name", "rule")},
			{"user": self.hr_self, "endpoint": "test.endpoint", "doctype": "KPI", "name": "KPI-X", "rule": "SEC-9"},
		)
		self.assertEqual(set(line), {"event", "at", "user", "endpoint", "doctype", "name", "rule"})


# ── SEC-13 / PRIV-6 · HR acts only for their companies (S10) ────────────────


class TestSec13HrActsOnlyForTheirCompanies(_Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company_b = _second_company()
		cls.company_a = ensure_company()
		assert cls.company_a != cls.company_b
		cls.lt = ensure_leave_type("Alvoraa Casual")
		cls.hr_a = _user("hr.companya", ("HR User", "Employee"))
		cls.hr_a_emp = _employee("HrCompanyA", company=cls.company_a, user=cls.hr_a)
		cls.emp_a = _employee("StaffA", company=cls.company_a)
		cls.emp_b = _employee("StaffB", company=cls.company_b)
		cls.hr_nowhere = _user("hr.nowhere", ("HR Manager",))
		cls.sysman = _user("sysman", ("System Manager",))

	def test_sec13_apply_leave_for_another_company_is_refused(self):
		from alvoraa_portal import hr_api

		before = frappe.db.count("Leave Application", {"employee": self.emp_b})
		frappe.set_user(self.hr_a)
		with self.assertRaises(frappe.PermissionError):
			hr_api.apply_leave(self.lt, WEEK_MON, WEEK_MON, on_behalf_of=self.emp_b)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count("Leave Application", {"employee": self.emp_b}), before)

	def test_sec13_preview_and_summary_for_another_company_are_refused(self):
		from alvoraa_portal import hr_api

		frappe.set_user(self.hr_a)
		with self.assertRaises(frappe.PermissionError):
			hr_api.preview_leave_request(self.lt, WEEK_MON, WEEK_MON, on_behalf_of=self.emp_b)
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_leave_summary(employee_id=self.emp_b)

	def test_sec13_unknown_employee_gets_the_same_refusal(self):
		from alvoraa_portal import hr_api

		frappe.set_user(self.hr_a)
		with self.assertRaises(frappe.PermissionError) as unknown:
			hr_api.get_leave_summary(employee_id="S010-NOBODY")
		with self.assertRaises(frappe.PermissionError) as elsewhere:
			hr_api.get_leave_summary(employee_id=self.emp_b)
		self.assertEqual(str(unknown.exception), str(elsewhere.exception))

	def test_sec13_employee_picker_lists_only_own_company_without_permissions(self):
		from alvoraa_portal import hr_api

		frappe.set_user(self.hr_a)
		names = [e.name for e in hr_api.get_all_active_employees()["employees"]]
		self.assertIn(self.emp_a, names)
		self.assertNotIn(self.emp_b, names)

	def test_sec13_company_user_permission_decides_the_scope(self):
		from alvoraa_portal import hr_api
		from hrms.alvoraa_hr_core.access import permitted_companies

		up = frappe.get_doc(
			{"doctype": "User Permission", "user": self.hr_a, "allow": "Company", "for_value": self.company_b,
			 "apply_to_all_doctypes": 1}
		)
		up.insert(ignore_permissions=True)
		frappe.db.commit()
		try:
			self.assertEqual(permitted_companies(self.hr_a), [self.company_b])
			frappe.set_user(self.hr_a)
			names = [e.name for e in hr_api.get_all_active_employees()["employees"]]
			self.assertIn(self.emp_b, names)
			self.assertNotIn(self.emp_a, names)
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User Permission", up.name, force=True, ignore_permissions=True)
			frappe.db.commit()

	def test_sec13_hr_with_no_company_and_no_employee_gets_nobody(self):
		from alvoraa_portal import hr_api
		from hrms.alvoraa_hr_core.access import permitted_companies

		self.assertEqual(permitted_companies(self.hr_nowhere), [])
		frappe.set_user(self.hr_nowhere)
		self.assertEqual(hr_api.get_all_active_employees()["employees"], [])
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_leave_summary(employee_id=self.emp_a)

	def test_sec13_system_manager_covers_every_company(self):
		from hrms.alvoraa_hr_core.access import permitted_companies

		companies = permitted_companies(self.sysman)
		self.assertIn(self.company_a, companies)
		self.assertIn(self.company_b, companies)

	def test_priv6_leave_summary_returns_only_the_fields_the_screen_uses(self):
		from alvoraa_portal import hr_api

		allowed = {"name", "employee_name", "company", "department"}
		frappe.set_user(self.hr_a)
		for_other = hr_api.get_leave_summary(employee_id=self.emp_a)
		own = hr_api.get_leave_summary()
		for res in (for_other, own):
			self.assertEqual(set(res["employee"]), allowed)
		self.assertEqual(for_other["employee"]["name"], self.emp_a)


# ── PRIV-3 / PRIV-4 · Managers get days, never the amount (S5) ──────────────


class TestPriv3ManagersNeverReceiveTheLossOfPayAmount(_Base):
	RULE = frappe._dict(
		name="S010 Rule", late_threshold_minutes=60, early_exit_threshold_minutes=0, count_early_exit=0,
		free_violations_per_week=1, deduction_per_violation_days=0.25, round_up_from_days=0, round_up_to_days=0,
	)
	PROJECTION = {"week_start": "2026-09-14", "violations": [], "counted": 0, "projected_days": 0}

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.mgr_user = _user("late.manager", ("Employee",))
		cls.mgr = _employee("LateManager", user=cls.mgr_user)
		cls.rep_user = _user("late.report", ("Employee",))
		cls.rep = _employee("LateReport", reports_to=cls.mgr, user=cls.rep_user)

	def _deduction(self):
		doc = frappe.get_doc(
			{
				"doctype": "Attendance Deduction",
				"employee": self.rep,
				"employee_name": f"LateReport {TAG}",
				"rule": "S010 Rule",
				"week_start": add_days(nowdate(), -7),
				"week_end": add_days(nowdate(), -1),
			}
		)
		doc.flags.ignore_validate = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		frappe.db.set_value(
			"Attendance Deduction", doc.name,
			{"docstatus": 1, "deduction_days": 1, "lwp_days": 0.5, "lwp_amount": 548.39,
			 "explanation": "Taken: 0.5 from Casual Leave, 0.5 as loss of pay."},
		)
		return doc.name

	def test_priv3_manager_late_list_has_days_but_no_amount_or_explanation(self):
		from alvoraa_portal import hr_api

		self._deduction()
		frappe.set_user(self.mgr_user)
		with patch("alvoraa_portal.hr_api._late_rule_for", return_value=self.RULE), patch(
			"hrms.alvoraa_late_rules.late_rules.current_week_projection", return_value=self.PROJECTION
		):
			res = hr_api.get_team_late_list(weeks=4)
		self.assertTrue(res["recent"])
		keys = _all_keys(res)
		self.assertNotIn("lwp_amount", keys)
		self.assertNotIn("explanation", keys)
		self.assertNotIn("548", json.dumps(res, default=str))
		self.assertEqual(res["recent"][0]["lwp_days"], 0.5)

	def test_priv3_employee_still_sees_their_own_amount(self):
		from alvoraa_portal import hr_api

		self._deduction()
		frappe.set_user(self.rep_user)
		with patch("alvoraa_portal.hr_api._late_rule_for", return_value=self.RULE), patch(
			"hrms.alvoraa_late_rules.late_rules.current_week_projection", return_value=dict(self.PROJECTION)
		):
			res = hr_api.get_my_attendance_deductions()
		self.assertEqual(res["rows"][0]["lwp_amount"], 548.39)

	def test_priv3_deduction_email_names_leave_type_and_days_but_no_amount(self):
		"""Decision 9 (2026-09-14): the email to employee and manager keeps the
		leave type and the days, and never carries a money figure."""
		rule = frappe.get_doc(
			{"doctype": "Attendance Deduction Rule", "rule_name": "S010 Email Rule", "company": ensure_company(),
			 "enabled": 0, "week_start_day": "Monday", "late_threshold_minutes": 60, "free_violations_per_week": 0,
			 "deduction_per_violation_days": 0.5, "notify_employee": 1, "notify_manager": 1}
		)
		rule.flags.ignore_validate = True
		rule.flags.ignore_links = True
		rule.flags.ignore_mandatory = True
		rule.insert(ignore_permissions=True)
		doc = frappe.get_doc(
			{
				"doctype": "Attendance Deduction", "employee": self.rep, "employee_name": f"LateReport {TAG}",
				"rule": rule.name, "week_start": "2026-09-07", "week_end": "2026-09-13",
				"total_violations": 2, "counted_violations": 2, "computed_days": 1, "deduction_days": 1,
				"lwp_days": 0.5, "lwp_amount": 548.39,
				"leave_deductions": [{"leave_type": "Casual Leave", "days": 0.5}],
			}
		)
		doc.docstatus = 1
		doc.explanation = doc.build_explanation()
		with patch("frappe.sendmail") as sendmail:
			doc.notify()
		kwargs = sendmail.call_args.kwargs
		self.assertIn(self.mgr_user, kwargs["recipients"])
		self.assertIn("Casual Leave", kwargs["message"])
		self.assertIn("0.5", kwargs["message"])
		for text in (kwargs["message"], kwargs["subject"]):
			self.assertNotIn("548", text)

	def test_priv4_amount_fields_are_hr_only_in_the_shipped_doctype(self):
		import hrms

		path = os.path.join(
			os.path.dirname(hrms.__file__),
			"alvoraa_late_rules", "doctype", "attendance_deduction", "attendance_deduction.json",
		)
		with open(path) as f:
			meta = json.load(f)
		fields = {d["fieldname"]: d for d in meta["fields"]}
		for fieldname in ("lwp_amount", "additional_salary"):
			self.assertGreaterEqual(fields[fieldname].get("permlevel", 0), 1, fieldname)
		level1_readers = {p["role"] for p in meta["permissions"] if p.get("permlevel", 0) >= 1 and p.get("read")}
		self.assertEqual(level1_readers, {"HR Manager", "HR User", "System Manager"})

	def test_priv4_manager_desk_read_does_not_return_the_amount(self):
		if not frappe.get_meta("Attendance Deduction").get_field("lwp_amount").permlevel:
			self.skipTest("test_site has not been migrated to the permlevel change yet")
		name = self._deduction()
		frappe.set_user(self.mgr_user)
		doc = frappe.get_doc("Attendance Deduction", name)
		doc.apply_fieldlevel_read_permissions()
		self.assertFalse(doc.get("lwp_amount"))
		rows = frappe.get_list("Attendance Deduction", filters={"name": name}, fields=["name", "lwp_amount"])
		self.assertTrue(all(not r.get("lwp_amount") for r in rows))


# ── SEC-12 · The server never pushes script to a browser (S9) ───────────────


class TestSec12NoScriptPush(_Base):
	NEEDLE = "eval" + "_js"

	def test_sec12_no_script_push_event_in_our_apps(self):
		import alvoraa_goals
		import alvoraa_portal
		import hrms

		roots = [os.path.dirname(alvoraa_portal.__file__), os.path.dirname(alvoraa_goals.__file__)]
		hrms_root = os.path.dirname(hrms.__file__)
		roots += [os.path.join(hrms_root, d) for d in os.listdir(hrms_root) if d.startswith("alvoraa_")]
		hits = []
		for root in roots:
			for folder, _dirs, files in os.walk(root):
				for fname in files:
					if fname.endswith((".py", ".js", ".html")):
						path = os.path.join(folder, fname)
						with open(path, encoding="utf-8", errors="ignore") as f:
							if self.NEEDLE in f.read():
								hits.append(path)
		self.assertEqual(hits, [])

	def test_sec12_notification_sends_email_only_and_logs_failure_without_names(self):
		from alvoraa_portal import performance_api

		with patch("frappe.sendmail") as sendmail, patch("frappe.publish_realtime") as realtime:
			performance_api._send_notification("someone@example.com", "Review for Asha", "<p>Hi Asha</p>")
		sendmail.assert_called_once()
		realtime.assert_not_called()

		with patch("frappe.sendmail", side_effect=Exception("smtp down")), patch("frappe.log_error") as log_error:
			performance_api._send_notification("someone@example.com", "Review for Asha", "<p>Hi Asha</p>")
		log_error.assert_called_once()
		logged = json.dumps(log_error.call_args.kwargs) + json.dumps(log_error.call_args.args)
		for secret in ("someone@example.com", "Asha"):
			self.assertNotIn(secret, logged)


# ── SEC-16 · ignore_permissions does not grow in the files this slice touches ─


class TestSec16IgnorePermissionsCeiling(FrappeTestCase):
	# Counts at 4e3ba28, lowered whenever a use is removed. Never raised.
	CEILINGS = {
		("alvoraa_portal", "performance_api.py"): 88,
		("alvoraa_portal", "hr_api.py"): 77,
		("alvoraa_portal", "goals_api.py"): 15,
		("alvoraa_portal", "attendance_correction.py"): 2,
		("alvoraa_goals", "api/goal_api.py"): 0,
		("alvoraa_goals", "controllers/evidence.py"): 0,
		("hrms", "alvoraa_org_structure/api.py"): 2,
		("hrms", "alvoraa_hr_core/access.py"): 0,
	}

	def test_sec16_ignore_permissions_does_not_grow(self):
		import importlib

		for (app, rel), ceiling in self.CEILINGS.items():
			root = os.path.dirname(importlib.import_module(app).__file__)
			with open(os.path.join(root, rel), encoding="utf-8") as f:
				count = len(re.findall(r"ignore_permissions", f.read()))
			self.assertLessEqual(count, ceiling, f"{app}/{rel}")


# ── PRIV-5 · People search finds only what the searcher may see (S6) ────────


class _OrgBase(_Base):
	"""Person-mode org chart with the shipped reach defaults."""

	REACH = {"alvoraa_org_reach_up": 2, "alvoraa_org_reach_down": 2,
	         "alvoraa_org_full_reach_roles": "HR Manager,HR User,System Manager",
	         "alvoraa_org_managers_see_all": 1}

	def setUp(self):
		super().setUp()
		self._saved = {k: frappe.db.get_default(k) for k in self.REACH}
		for k, v in self.REACH.items():
			frappe.db.set_default(k, v)
		# Positions are a paid layer; these tests are about people.
		self._positions = patch("hrms.alvoraa_org_structure.api._enabled", return_value=False)
		self._positions.start()
		frappe.local._alvoraa_leads = {}

	def tearDown(self):
		self._positions.stop()
		frappe.set_user("Administrator")
		for k, v in self._saved.items():
			frappe.db.set_default(k, v if v is not None else "")
		frappe.db.commit()
		frappe.local._alvoraa_leads = {}
		super().tearDown()

	def _as(self, user):
		frappe.set_user(user)
		frappe.local._alvoraa_leads = {}


class TestPriv5PeopleSearchScope(_OrgBase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company_b = _second_company()
		cls.company_a = ensure_company()
		assert cls.company_a != cls.company_b
		cls.boss_user = _user("search.boss", ("Employee",))
		cls.boss = _employee("SearchBoss", user=cls.boss_user)
		cls.mid = _employee("SearchMid", reports_to=cls.boss)
		cls.leaf_user = _user("search.leaf", ("Employee",))
		cls.leaf = _employee("SearchLeaf", reports_to=cls.mid, user=cls.leaf_user)
		cls.stranger = _employee("SearchStranger")
		cls.other_co = _employee("SearchOtherCo", company=cls.company_b)
		cls.hr_user = _user("search.hr", ("HR User", "Employee"))
		cls.hr_emp = _employee("SearchHr", user=cls.hr_user)
		cls.sysman = _user("search.sysman", ("System Manager",))
		cls.nobody = _user("search.nobody", ("Employee",))

	def _found(self, user):
		from hrms.alvoraa_org_structure import api

		self._as(user)
		return {r["employee"] for r in api.search_people("Search", limit=50)}

	def test_priv5_someone_with_no_reports_finds_only_themselves(self):
		self.assertEqual(self._found(self.leaf_user), {self.leaf})

	def test_priv5_a_manager_finds_their_whole_line_and_nobody_else(self):
		found = self._found(self.boss_user)
		self.assertTrue({self.boss, self.mid, self.leaf} <= found)
		self.assertNotIn(self.stranger, found)
		self.assertNotIn(self.other_co, found)

	def test_priv5_hr_without_company_permission_finds_only_their_company(self):
		found = self._found(self.hr_user)
		self.assertIn(self.stranger, found)
		self.assertNotIn(self.other_co, found)

	def test_priv5_system_manager_finds_every_company(self):
		found = self._found(self.sysman)
		self.assertIn(self.stranger, found)
		self.assertIn(self.other_co, found)

	def test_priv5_a_login_with_no_employee_finds_nobody(self):
		self.assertEqual(self._found(self.nobody), set())


# ── SEC-8 · Every org-chart endpoint obeys reach (S6) ───────────────────────


class TestSec8OrgChartObeysReach(_OrgBase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.top = _employee("ReachTop")
		cls.l1 = _employee("ReachL1", reports_to=cls.top)
		cls.l2 = _employee("ReachL2", reports_to=cls.l1)
		cls.leaf_user = _user("reach.leaf", ("Employee",))
		cls.leaf = _employee("ReachLeaf", reports_to=cls.l2, user=cls.leaf_user)
		cls.side = _employee("ReachSide")
		cls.hr_user = _user("reach.hr", ("HR Manager", "Employee"))
		cls.hr_emp = _employee("ReachHr", user=cls.hr_user)
		cls.nobody = _user("reach.nobody", ("Employee",))

	def test_sec8_my_view_of_someone_out_of_reach_is_refused(self):
		from hrms.alvoraa_org_structure import api

		self._as(self.leaf_user)
		with self.assertRaises(frappe.PermissionError):
			api.my_view(employee=self.top)          # three levels up
		with self.assertRaises(frappe.PermissionError):
			api.my_view(employee=self.side)         # another branch
		self.assertEqual(api.my_view(employee=self.l1)["me"]["employee"], self.l1)   # two up: fine
		self.assertEqual(api.my_view()["me"]["employee"], self.leaf)

	def test_sec8_chain_to_top_of_someone_out_of_reach_is_refused(self):
		from hrms.alvoraa_org_structure import api

		self._as(self.leaf_user)
		with self.assertRaises(frappe.PermissionError):
			api.chain_to_top(node=self.side)
		self.assertTrue(api.chain_to_top())

	def test_sec8_get_children_checks_reach_too(self):
		from hrms.alvoraa_org_structure import api

		self._as(self.leaf_user)
		with self.assertRaises(frappe.PermissionError):
			api.get_children(parent=self.top)
		with self.assertRaises(frappe.PermissionError):
			api.get_children()                      # the top of the company

	def test_sec8_a_login_with_no_employee_sees_nothing(self):
		from hrms.alvoraa_org_structure import api

		self._as(self.nobody)
		self.assertFalse(api._within_reach(self.leaf, nowdate()))
		with self.assertRaises(frappe.PermissionError):
			api.subtree(root=self.leaf)
		with self.assertRaises(frappe.PermissionError):
			api.my_view(employee=self.leaf)

	def test_sec8_hr_still_roams(self):
		from hrms.alvoraa_org_structure import api

		self._as(self.hr_user)
		self.assertEqual(api.my_view(employee=self.top)["me"]["employee"], self.top)
		api.chain_to_top(node=self.leaf)
		api.get_children(parent=self.top)
