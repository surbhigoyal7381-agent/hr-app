"""Who may open an appraisal that is still being written.

HR should not read somebody's appraisal while that person and their manager
are still working on it. The guard that enforces this asked the wrong question:
"do you hold an HR role?" rather than "is this somebody else's appraisal?"

So anybody holding HR Manager was blocked from their OWN review, and from
their team's. On PP Jewellers that is the Owner and Managing Director - he
holds HR Manager, and could not open his own appraisal. The message he got was
"This appraisal is not yet in HR Review stage.", which is true and useless.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import performance_api as pa

CYCLE = "AV Test Cycle"


def _company():
	return frappe.db.get_value("Company", {}, "name")


class VisibilityCase(FrappeTestCase):
	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		self.company = _company()
		if not frappe.db.exists("Appraisal Cycle", CYCLE):
			frappe.get_doc({
				"doctype": "Appraisal Cycle", "cycle_name": CYCLE,
				"company": self.company, "start_date": "2026-04-01",
				"end_date": "2026-06-30", "status": "In Progress",
			}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user(self.caller)

	def person(self, first, roles=(), reports_to=None):
		email = "%s.av@example.com" % first.lower()
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		user = frappe.get_doc("User", email)
		held = {r.role for r in user.roles}
		for r in roles:
			if r not in held:
				user.add_roles(r)

		existing = frappe.db.get_value("Employee", {"user_id": email, "status": "Active"})
		if existing:
			if reports_to:
				frappe.db.set_value("Employee", existing, "reports_to", reports_to)
			return existing, email

		emp = frappe.get_doc({
			"doctype": "Employee", "first_name": first, "company": self.company,
			"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "user_id": email, "reports_to": reports_to,
		}).insert(ignore_permissions=True)
		return emp.name, email

	def appraisal(self, employee, review_status):
		ap = frappe.get_doc({
			"doctype": "Appraisal", "employee": employee, "appraisal_cycle": CYCLE,
			"company": self.company,
		}).insert(ignore_permissions=True)
		ext = frappe.db.get_value("Alvoraa Appraisal Extension", {"appraisal": ap.name})
		if ext:
			frappe.db.set_value("Alvoraa Appraisal Extension", ext,
			                    "review_status", review_status)
		else:
			frappe.get_doc({
				"doctype": "Alvoraa Appraisal Extension", "appraisal": ap.name,
				"review_status": review_status,
			}).insert(ignore_permissions=True)
		return ap.name

	def blocked(self, appraisal):
		try:
			pa._assert_hr_can_view(appraisal)
			return False
		except frappe.PermissionError:
			return True


class YourOwnReview(VisibilityCase):
	def test_holding_an_hr_role_does_not_hide_your_own_appraisal(self):
		"""The bug, exactly. An Owner and MD who also holds HR Manager could
		not open his own review."""
		me, email = self.person("AVOwner", roles=("Employee", "HR Manager"))
		ap = self.appraisal(me, "Employee Review")
		frappe.set_user(email)
		self.assertTrue(pa._is_hr(), "this test is pointless unless they read as HR")
		self.assertFalse(self.blocked(ap), "blocked from their own appraisal")

	def test_an_ordinary_employee_was_never_affected(self):
		"""The guard exits early for anyone without an HR role, and must keep
		doing so."""
		me, email = self.person("AVPlain", roles=("Employee",))
		ap = self.appraisal(me, "Employee Review")
		frappe.set_user(email)
		self.assertFalse(self.blocked(ap))


class YourTeamsReview(VisibilityCase):
	def test_a_manager_who_is_also_hr_can_still_do_a_manager_review(self):
		"""Manager Review is exactly the stage when they are supposed to be in
		there. Blocking them because they also hold an HR role stops the
		review happening at all."""
		boss, boss_email = self.person("AVBoss", roles=("Employee", "HR Manager"))
		report, _e = self.person("AVReport", roles=("Employee",), reports_to=boss)
		ap = self.appraisal(report, "Manager Review")
		frappe.set_user(boss_email)
		self.assertFalse(self.blocked(ap))

	def test_it_reaches_the_whole_line_not_just_direct_reports(self):
		boss, boss_email = self.person("AVHead", roles=("Employee", "HR Manager"))
		mid, _e = self.person("AVMid", roles=("Employee",), reports_to=boss)
		junior, _e2 = self.person("AVJunior", roles=("Employee",), reports_to=mid)
		ap = self.appraisal(junior, "Employee Review")
		frappe.set_user(boss_email)
		self.assertFalse(self.blocked(ap))


class SomebodyElsesReview(VisibilityCase):
	def test_hr_still_cannot_read_a_stranger_mid_review(self):
		"""The rule the guard exists for, which must survive the fix."""
		hr, hr_email = self.person("AVHR", roles=("Employee", "HR Manager"))
		stranger, _e = self.person("AVStranger", roles=("Employee",))
		ap = self.appraisal(stranger, "Employee Review")
		frappe.set_user(hr_email)
		self.assertTrue(self.blocked(ap),
		                "HR reading a stranger's unfinished appraisal is the "
		                "thing this guard is for")

	def test_hr_may_read_it_once_it_is_finished(self):
		hr, hr_email = self.person("AVHR2", roles=("Employee", "HR Manager"))
		stranger, _e = self.person("AVStranger2", roles=("Employee",))
		ap = self.appraisal(stranger, "Completed")
		frappe.set_user(hr_email)
		self.assertFalse(self.blocked(ap))

	def test_the_refusal_says_what_has_to_happen_first(self):
		"""'Not yet in HR Review stage' is true and tells the reader nothing
		about who is holding it or when it will arrive."""
		hr, hr_email = self.person("AVHR3", roles=("Employee", "HR Manager"))
		stranger, _e = self.person("AVStranger3", roles=("Employee",))
		ap = self.appraisal(stranger, "Manager Review")
		frappe.set_user(hr_email)
		with self.assertRaises(frappe.PermissionError) as caught:
			pa._assert_hr_can_view(ap)
		said = str(caught.exception).lower()
		self.assertIn("employee and their manager", said)
