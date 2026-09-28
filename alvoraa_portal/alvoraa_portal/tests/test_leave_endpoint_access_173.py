"""ALV-173: three leave endpoints that any logged-in user could call.

Frappe HR carries its own guard, `validate_leave_access(employee)`. It lets the
call through only for the employee themselves, their leave approver, or somebody
holding read access to that Employee record.

Our copy of Frappe HR was taken from their development branch on 16 June 2026.
Upstream added that guard to three more endpoints AFTER that date, on both the
version-16 and develop lines, so our copy never had it:

  * get_leave_approver        - returns the approver's login for any employee
  * get_holidays              - a holiday count for any employee
  * get_number_of_leave_days  - a day count for any employee

None of them returns a balance or a pay figure, so this was never severe. But on
a tenant with 300 staff logins "any logged-in user" stops being a small set, and
the reporting line is personal data.

THE TRAP THIS FILE ALSO PINS. `validate_leave_access` has to know who the
approver is in order to decide. Guarding `get_leave_approver` directly therefore
made it call the guard, which called it again, until the request died. The fix
is upstream's own shape: an unguarded `get_employee_leave_approver` holding the
rule, and a thin guarded `get_leave_approver` in front of it. The recursion test
below is the one that would have caught the naive version.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal.tests import fixtures_043 as fx

ENDPOINTS = ("get_holidays", "get_number_of_leave_days", "get_leave_approver")


def _call(name, employee):
	"""Call one endpoint the way the web would, with only `employee` varying."""
	from hrms.hr.doctype.leave_application.leave_application import (
		get_holidays,
		get_leave_approver,
		get_number_of_leave_days,
	)

	if name == "get_holidays":
		return get_holidays(employee, "2026-01-01", "2026-01-31")
	if name == "get_number_of_leave_days":
		return get_number_of_leave_days(employee, "_Test Leave Type", "2026-01-05", "2026-01-06")
	return get_leave_approver(employee)


class TestLeaveEndpointsRefuseAStranger(FrappeTestCase):
	"""A colleague with no relationship to the employee gets nothing."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fx.ensure_company()
		fx.ensure_branches()

		# The subject.
		cls.subject_login = fx.user("alv173subject", ["Employee"])
		cls.subject = fx.employee("Alv173Subject", branch=fx.STORE_A, login=cls.subject_login)

		# Their approver.
		cls.approver_login = fx.user("alv173approver", ["Employee"])
		cls.approver_emp = fx.employee("Alv173Approver", branch=fx.STORE_A, login=cls.approver_login)
		frappe.db.set_value("Employee", cls.subject, "leave_approver", cls.approver_login,
		                    update_modified=False)

		# An unrelated colleague. Employee role only - no HR rights, not the
		# approver, not the subject. This is the person the guard exists for.
		cls.stranger_login = fx.user("alv173stranger", ["Employee"])
		cls.stranger = fx.employee("Alv173Stranger", branch=fx.STORE_B, login=cls.stranger_login)

		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_a_stranger_is_refused_by_every_one_of_the_three(self):
		frappe.set_user(self.stranger_login)
		for name in ENDPOINTS:
			with self.subTest(endpoint=name):
				with self.assertRaises(frappe.PermissionError):
					_call(name, self.subject)

	def test_the_employee_may_still_ask_about_themselves(self):
		"""The guard must not lock people out of their own data."""
		frappe.set_user(self.subject_login)
		for name in ENDPOINTS:
			with self.subTest(endpoint=name):
				_call(name, self.subject)  # must not raise

	def test_the_named_approver_may_still_ask(self):
		"""Approval routing depends on this. If it breaks, leave stops moving."""
		frappe.set_user(self.approver_login)
		for name in ENDPOINTS:
			with self.subTest(endpoint=name):
				_call(name, self.subject)  # must not raise

	def test_somebody_with_read_access_to_the_employee_may_still_ask(self):
		frappe.set_user("Administrator")
		for name in ENDPOINTS:
			with self.subTest(endpoint=name):
				_call(name, self.subject)  # must not raise


class TestTheGuardDoesNotCallItself(FrappeTestCase):
	"""The bug the obvious one-line fix would have introduced.

	`validate_leave_access` asks who the approver is. If it asks the WHITELISTED
	`get_leave_approver`, that function runs the guard again, which asks again.
	A naive fix passes every permission test above and then dies here.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fx.ensure_company()
		fx.ensure_branches()
		cls.login = fx.user("alv173rec", ["Employee"])
		cls.emp = fx.employee("Alv173Rec", branch=fx.STORE_A, login=cls.login)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_asking_for_your_own_approver_terminates(self):
		from hrms.hr.doctype.leave_application.leave_application import get_leave_approver

		frappe.set_user(self.login)
		try:
			get_leave_approver(self.emp)
		except RecursionError:
			self.fail("get_leave_approver recursed - the guard is calling the "
			          "whitelisted function instead of get_employee_leave_approver")
		except frappe.PermissionError:
			self.fail("the employee was refused their own approver")

	def test_the_guard_uses_the_unguarded_helper(self):
		"""Named directly, so a future edit that re-points it fails here."""
		import inspect

		from hrms.hr.doctype.leave_application.leave_application import validate_leave_access

		src = inspect.getsource(validate_leave_access)
		self.assertIn("get_employee_leave_approver(employee)", src)
		self.assertNotIn("= get_leave_approver(", src)


class TestTheRuleItselfStillWorks(FrappeTestCase):
	"""Splitting the function must not change what answer it gives."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fx.ensure_company()
		fx.ensure_branches()
		cls.login = fx.user("alv173dept", ["Employee"])
		cls.emp = fx.employee("Alv173Dept", branch=fx.STORE_A, login=cls.login)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_a_personal_approver_wins(self):
		from hrms.hr.doctype.leave_application.leave_application import (
			get_employee_leave_approver,
		)

		frappe.db.set_value("Employee", self.emp, "leave_approver", self.login,
		                    update_modified=False)
		self.assertEqual(get_employee_leave_approver(self.emp), self.login)

	def test_no_approver_and_no_department_returns_nothing(self):
		from hrms.hr.doctype.leave_application.leave_application import (
			get_employee_leave_approver,
		)

		frappe.db.set_value("Employee", self.emp,
		                    {"leave_approver": None, "department": None},
		                    update_modified=False)
		self.assertFalse(get_employee_leave_approver(self.emp))
