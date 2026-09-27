"""Slice 043 AC-17 (ALV-113): the manager's deduction email stops naming the leave type.

**The leak, and why the first version of this test would have missed it.**

`AttendanceDeduction.notify` put the employee's and the manager's `user_id` in
ONE `recipients` list and sent both the identical stored `explanation`. Revision
1 of the spec said the leak was the rupee amount and wrote a check for it. There
was never a rupee amount in that text - `build_explanation` uses `lwp_days` -
so that check would have gone green on the day it was written while the real
leak carried on going out by email every week.

The real leak is plainer: the explanation names the **leave type**.

    "Taken: 0.5 from Sick Leave, 0.5 as loss of pay"

A manager reads that about his report, for a leave type the product hides on
every screen. So the fixture here is a week whose days came from **Sick Leave**,
and the assertions are on the **rendered body per recipient**.

Four rules, all four asserted:

  1. separate bodies - the employee's is byte-identical to the stored explanation
  2. days only in the manager's body - no amount, no minutes, no per-day list
  3. no leave type in the manager's body - checked against EVERY Leave Type on
     the site, not just the one the fixture used
  4. separate sends, one recipient each

Rule 4 is the one that makes the other three survive. Two people on one
recipients list share a body by construction, and the next person to add a
helpful line to "the email" adds it to both.

**This slice's own company and people**, tagged S043E. Shared fixtures have cost
this project four slices' time.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

TAG = "S043E"
COMPANY = "S043E Email Company"
ABBR = "S43E"
SHIFT = "S043E Shift"
RULE = "S043E Rule"
COMPONENT = "S043E Loss Of Pay"
LEAVE_TYPE = "S043E Sick Leave"
HOLIDAYS = "S043E Holidays"


class MailCapture:
	"""Every frappe.sendmail call, with its recipients and its rendered body.

	This is a mail capture, not a patched permission check - the thing AC-30(b)
	forbids is patching the FEATURE GATE, because that makes an entitlement test
	prove nothing. Here the boundary being observed IS the thing under test.
	"""

	def __init__(self):
		self.sends = []
		self._real = None

	def __enter__(self):
		self._real = frappe.sendmail

		def capture(**kwargs):
			self.sends.append({
				"recipients": list(kwargs.get("recipients") or []),
				"subject": kwargs.get("subject") or "",
				"message": kwargs.get("message") or "",
			})

		frappe.sendmail = capture
		return self

	def __exit__(self, *exc):
		frappe.sendmail = self._real
		return False

	def to(self, recipient):
		return [s for s in self.sends if s["recipients"] == [recipient]]


def _ensure(doctype, name, **values):
	if name and frappe.db.exists(doctype, name):
		return frappe.get_doc(doctype, name)
	doc = frappe.get_doc({"doctype": doctype, **values})
	if name:
		doc.name = name
		doc.set("__newname", name)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_mandatory=True)
	return doc


class TestTheManagersDeductionEmail(IntegrationTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure(
			"Company", COMPANY, company_name=COMPANY, abbr=ABBR,
			default_currency="INR", country="India").name
		cls.shift = _ensure("Shift Type", SHIFT, shift_type=SHIFT,
		                    start_time="09:30:00", end_time="18:30:00").name
		cls.component = _ensure(
			"Salary Component", COMPONENT, salary_component=COMPONENT,
			salary_component_abbr="S43LOP", type="Deduction").name
		_ensure("Leave Type", LEAVE_TYPE, leave_type_name=LEAVE_TYPE)
		holidays = _ensure("Holiday List", HOLIDAYS, holiday_list_name=HOLIDAYS,
		                   from_date="2026-01-01", to_date="2026-12-31").name

		cls.mgr_login = _user("manager")
		cls.emp_login = _user("employee")
		cls.manager = _employee("Sandeep", cls.company, cls.mgr_login, holidays)
		cls.employee = _employee("Rahul", cls.company, cls.emp_login, holidays,
		                         reports_to=cls.manager)

		cls.rule = _ensure(
			"Attendance Deduction Rule", RULE, rule_name=RULE,
			company=cls.company, shift_type=cls.shift, enabled=1,
			week_start_day="Monday", late_threshold_minutes=60,
			count_early_exit=1, early_exit_threshold_minutes=60,
			free_violations_per_week=1, deduction_per_violation_days=0.25,
			round_up_from_days=0.75, round_up_to_days=1.0,
			deduct_from_leave_first=1,
			leave_types=[{"leave_type": LEAVE_TYPE, "priority": 1}],
			lwp_salary_component=cls.component,
			notify_employee=1, notify_manager=1,
		).name
		frappe.db.commit()

	def setUp(self):
		super().setUp()
		for name in frappe.get_all("Attendance Deduction",
		                           {"employee": self.employee}, pluck="name"):
			frappe.delete_doc("Attendance Deduction", name,
			                  ignore_permissions=True, force=True)
		frappe.db.commit()

	def _deduction(self):
		"""A DRAFT deduction whose days already came out of Sick Leave.

		The leave rows are set on the document rather than consumed through the
		ledger, because what is under test is the EMAIL, not the ledger. The
		stored `explanation` is built by the real `build_explanation`, so the
		text the employee gets is the real text.
		"""
		doc = frappe.get_doc({
			"doctype": "Attendance Deduction",
			"employee": self.employee,
			"employee_name": frappe.db.get_value("Employee", self.employee,
			                                     "employee_name"),
			"company": self.company,
			"rule": self.rule,
			"week_start": "2026-08-17",
			"week_end": "2026-08-23",
			# No violation on the 17th ON PURPOSE. The week START is 2026-08-17
			# and the manager's body names the week, legitimately. If a
			# violation shared that date, the "no per-day list" assertion below
			# could not tell the two apart and would be worthless.
			"violations": [
				{"attendance_date": "2026-08-18", "actual_time": "10:47:00",
				 "minutes_late": 77, "violation_type": "Late Arrival"},
				{"attendance_date": "2026-08-19", "actual_time": "10:35:00",
				 "minutes_late": 65, "violation_type": "Late Arrival"},
				{"attendance_date": "2026-08-20", "actual_time": "10:40:00",
				 "minutes_late": 70, "violation_type": "Late Arrival"},
			],
			"leave_deductions": [
				{"leave_type": LEAVE_TYPE, "days": 0.5},
			],
			"lwp_days": 0.5,
			"lwp_amount": 548.39,
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_mandatory=True)
		return doc

	def _bodies(self):
		doc = self._deduction()
		doc.explanation = doc.build_explanation()
		with MailCapture() as mail:
			doc.notify()
		return doc, mail

	# ── The fixture itself ───────────────────────────────────────────────

	def test_the_explanation_really_does_name_the_leave_type(self):
		"""If it does not, every assertion below passes for the wrong reason.
		This is the exact sentence that was going to a manager's inbox."""
		doc = self._deduction()
		self.assertIn(LEAVE_TYPE, doc.build_explanation())

	def test_the_explanation_carries_no_rupee_figure(self):
		"""Revision 1 of the spec said the leak was the amount. It was not, and
		this pins that so nobody 'fixes' a number that was never there."""
		text = self._deduction().build_explanation()
		self.assertNotIn("₹", text)
		self.assertNotIn("548", text)

	# ── Rule 4: separate sends ───────────────────────────────────────────

	def test_there_are_two_sends_with_one_recipient_each(self):
		doc, mail = self._bodies()
		self.assertEqual(len(mail.sends), 2)
		self.assertEqual([len(s["recipients"]) for s in mail.sends], [1, 1])
		self.assertEqual(
			sorted(s["recipients"][0] for s in mail.sends),
			sorted([self.emp_login, self.mgr_login]))

	# ── Rule 1: separate bodies ──────────────────────────────────────────

	def test_the_employees_body_is_byte_identical_to_the_stored_explanation(self):
		doc, mail = self._bodies()
		sent = mail.to(self.emp_login)
		self.assertEqual(len(sent), 1)
		self.assertEqual(sent[0]["message"], doc.explanation)

	def test_the_two_bodies_are_not_the_same_string(self):
		doc, mail = self._bodies()
		self.assertNotEqual(mail.to(self.emp_login)[0]["message"],
		                    mail.to(self.mgr_login)[0]["message"])

	# ── Rule 3: no leave type ────────────────────────────────────────────

	def test_no_leave_type_on_this_site_appears_in_the_managers_body(self):
		"""Against EVERY Leave Type, not just the fixture's - a body that names
		'Casual Leave' would pass a check written only for Sick Leave."""
		doc, mail = self._bodies()
		body = mail.to(self.mgr_login)[0]["message"]
		types = frappe.get_all("Leave Type", pluck="name")
		self.assertTrue(types, "no Leave Types on the site - check is vacuous")
		for leave_type in types:
			self.assertNotIn(leave_type, body,
			                 "the manager's email names a leave type (AC-17)")

	def test_none_of_the_stored_explanation_reaches_the_manager(self):
		doc, mail = self._bodies()
		body = mail.to(self.mgr_login)[0]["message"]
		self.assertNotIn(doc.explanation, body)

	# ── Rule 2: days only ────────────────────────────────────────────────

	def test_the_managers_body_carries_no_currency_and_no_minutes(self):
		import re
		doc, mail = self._bodies()
		body = mail.to(self.mgr_login)[0]["message"]
		self.assertNotIn("₹", body)
		self.assertNotIn("548", body)
		self.assertIsNone(
			re.search(r"\d+\s*min", body, re.I),
			"the manager's email carries a minute figure (AC-17)")

	def test_the_managers_body_carries_no_per_day_violation_list(self):
		doc, mail = self._bodies()
		body = mail.to(self.mgr_login)[0]["message"]
		for row in doc.violations:
			self.assertNotIn(str(row.attendance_date), body)
			self.assertNotIn(str(row.actual_time), body)

	def test_the_managers_body_does_carry_the_days(self):
		"""A manager keeps a duty of care. Days are what they may know."""
		doc, mail = self._bodies()
		body = mail.to(self.mgr_login)[0]["message"]
		self.assertIn(str(flt(doc.deduction_days)), body)

	# ── The subject ──────────────────────────────────────────────────────

	def test_the_subject_is_the_same_for_both_and_names_no_leave_type(self):
		doc, mail = self._bodies()
		subjects = {s["subject"] for s in mail.sends}
		self.assertEqual(len(subjects), 1)
		subject = subjects.pop()
		for leave_type in frappe.get_all("Leave Type", pluck="name"):
			self.assertNotIn(leave_type, subject)

	# ── The switches still work ──────────────────────────────────────────

	def test_manager_off_means_one_send(self):
		frappe.db.set_value("Attendance Deduction Rule", self.rule,
		                    "notify_manager", 0)
		frappe.clear_cache(doctype="Attendance Deduction Rule")
		try:
			doc, mail = self._bodies()
			self.assertEqual(len(mail.sends), 1)
			self.assertEqual(mail.sends[0]["recipients"], [self.emp_login])
		finally:
			frappe.db.set_value("Attendance Deduction Rule", self.rule,
			                    "notify_manager", 1)
			frappe.clear_cache(doctype="Attendance Deduction Rule")

	def test_both_off_means_no_send_at_all(self):
		for field in ("notify_employee", "notify_manager"):
			frappe.db.set_value("Attendance Deduction Rule", self.rule, field, 0)
		frappe.clear_cache(doctype="Attendance Deduction Rule")
		try:
			doc, mail = self._bodies()
			self.assertEqual(mail.sends, [])
		finally:
			for field in ("notify_employee", "notify_manager"):
				frappe.db.set_value("Attendance Deduction Rule", self.rule,
				                    field, 1)
			frappe.clear_cache(doctype="Attendance Deduction Rule")


def _user(local):
	email = "s043e.%s@example.com" % local
	if not frappe.db.exists("User", email):
		doc = frappe.get_doc({"doctype": "User", "email": email,
		                      "first_name": local.title(),
		                      "send_welcome_email": 0,
		                      "roles": [{"role": "Employee"}]})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
	return email


def _employee(first, company, login, holidays, reports_to=None):
	name = frappe.db.get_value("Employee", {"first_name": first, "last_name": TAG},
	                           "name")
	if name:
		doc = frappe.get_doc("Employee", name)
	else:
		doc = frappe.get_doc({"doctype": "Employee", "first_name": first,
		                      "last_name": TAG, "date_of_birth": "1990-01-01",
		                      "gender": _gender()})
	doc.company = company
	doc.date_of_joining = "2024-01-01"
	doc.status = "Active"
	doc.user_id = login
	doc.reports_to = reports_to
	doc.holiday_list = holidays
	doc.create_user_permission = 0
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


def _gender():
	existing = frappe.db.get_value("Gender", {"name": "Male"}, "name")
	if existing:
		return existing
	return frappe.get_all("Gender", pluck="name", limit=1)[0]
