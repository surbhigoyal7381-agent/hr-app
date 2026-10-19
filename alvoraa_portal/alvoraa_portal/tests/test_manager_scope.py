"""A manager may act for their own reports, through the permission system.

Not past it. The whole point of `manager_scope` is that the decision lives in
User Permission records somebody can list, rather than in an
`ignore_permissions` nobody can audit - so these tests are about what the
PERMISSION DATA says, and about the doors it deliberately leaves shut.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import manager_scope as ms


def _company():
	return (frappe.db.get_value("Company", {}, "name")
	        or frappe.get_doc({"doctype": "Company", "company_name": "MS Test Co",
	                           "abbr": "MSTC", "default_currency": "INR"}
	                          ).insert(ignore_permissions=True).name)


class ScopeCase(FrappeTestCase):
	_n = 0

	def setUp(self):
		self.company = _company()
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		ScopeCase._n += 1
		self.tag = ScopeCase._n

	def tearDown(self):
		frappe.set_user(self.caller)

	def person(self, label):
		email = "ms%s%d@example.com" % (label.lower(), self.tag)
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email,
			                "first_name": "Ms" + label, "send_welcome_email": 0}
			               ).insert(ignore_permissions=True).add_roles("Employee")
		e = frappe.get_doc({
			"doctype": "Employee", "first_name": "Ms" + label + str(self.tag),
			"company": self.company, "date_of_birth": "1990-01-01",
			"date_of_joining": "2015-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "user_id": email,
		}).insert(ignore_permissions=True)
		return e.name, email

	def perms(self, user, **extra):
		f = {"user": user, "allow": "Employee"}
		f.update(extra)
		return frappe.get_all("User Permission", filters=f,
		                      fields=["for_value", "applicable_for",
		                              "apply_to_all_doctypes"],
		                      limit_page_length=0)


class WhatAManagerIsGranted(ScopeCase):
	def setUp(self):
		super().setUp()
		self.boss, self.boss_email = self.person("Boss")
		self.rep, _ = self.person("Rep")

	def test_a_report_grants_one_permission_per_doctype_and_no_more(self):
		ms.grant(self.boss, self.rep)
		got = {p.applicable_for for p in self.perms(self.boss_email,
		                                            for_value=self.rep)}
		self.assertEqual(got, set(ms.SCOPED_DOCTYPES))

	def test_none_of_them_applies_to_all_document_types(self):
		"""THE WHOLE SAFETY OF THIS. A blanket permission would scope the
		manager to their reports EVERYWHERE - and the Employee role can read
		Salary Slip, so it would hand every manager their team's payslips as a
		side effect of a correction workflow."""
		ms.grant(self.boss, self.rep)
		for p in self.perms(self.boss_email, for_value=self.rep):
			self.assertFalse(p.apply_to_all_doctypes,
			                 "%s must be scoped to one doctype" % p.applicable_for)
			self.assertTrue(p.applicable_for)

	def test_pay_is_not_among_them(self):
		ms.grant(self.boss, self.rep)
		got = {p.applicable_for for p in self.perms(self.boss_email)}
		for shut in ("Salary Slip", "Salary Structure Assignment",
		             "Employee Tax Exemption Declaration", "Expense Claim"):
			self.assertNotIn(shut, got, "%s is not a manager's business here" % shut)

	def test_the_employee_record_itself_is_not_granted(self):
		"""A manager reads a report's name, branch and shift through
		`team_days`, which decides permission explicitly and returns those
		fields alone. Granting Employee would additionally open date of birth
		and the rest of the record to solve a problem already solved."""
		ms.grant(self.boss, self.rep)
		got = {p.applicable_for for p in self.perms(self.boss_email)}
		self.assertNotIn("Employee", got)

	def test_granting_twice_changes_nothing(self):
		ms.grant(self.boss, self.rep)
		before = len(self.perms(self.boss_email, for_value=self.rep))
		ms.grant(self.boss, self.rep)
		self.assertEqual(len(self.perms(self.boss_email, for_value=self.rep)), before)

	def test_revoking_takes_them_all_back(self):
		ms.grant(self.boss, self.rep)
		ms.revoke(self.boss, self.rep)
		self.assertEqual(self.perms(self.boss_email, for_value=self.rep), [])

	def test_revoking_leaves_a_blanket_permission_somebody_made_by_hand(self):
		"""`applicable_for` is always set by this module, so a reporting-line
		change must never delete a permission an administrator created."""
		ms.grant(self.boss, self.rep)
		byhand = frappe.get_doc({
			"doctype": "User Permission", "user": self.boss_email,
			"allow": "Employee", "for_value": self.rep,
			"apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
		ms.revoke(self.boss, self.rep)
		self.assertTrue(frappe.db.exists("User Permission", byhand.name),
		                "a hand-made blanket permission is not ours to remove")


class WhenTheReportingLineMoves(ScopeCase):
	def setUp(self):
		super().setUp()
		self.old, self.old_email = self.person("Old")
		self.new, self.new_email = self.person("New")
		self.rep, _ = self.person("Moved")

	def test_moving_somebody_moves_the_permission_with_them(self):
		"""Both managers in one save, so a reporting line and its permissions
		can never disagree."""
		e = frappe.get_doc("Employee", self.rep)
		e.reports_to = self.old
		e.save(ignore_permissions=True)
		self.assertTrue(self.perms(self.old_email, for_value=self.rep))

		e.reports_to = self.new
		e.save(ignore_permissions=True)
		self.assertEqual(self.perms(self.old_email, for_value=self.rep), [],
		                 "the old manager must lose them")
		self.assertTrue(self.perms(self.new_email, for_value=self.rep),
		                "the new manager must gain them")

	def test_a_leaver_is_taken_off_their_managers_list(self):
		"""The line may still read the same, but there is nothing to act on."""
		e = frappe.get_doc("Employee", self.rep)
		e.reports_to = self.old
		e.save(ignore_permissions=True)
		self.assertTrue(self.perms(self.old_email, for_value=self.rep))

		e.status = "Left"
		e.relieving_date = nowdate()
		e.save(ignore_permissions=True)
		self.assertEqual(self.perms(self.old_email, for_value=self.rep), [])

	def test_sync_brings_an_existing_line_into_step(self):
		"""For the lines that existed before this feature, and any that drifted
		through a direct database write."""
		frappe.db.set_value("Employee", self.rep, "reports_to", self.old)
		out = ms.sync_for_manager(self.old)
		self.assertEqual(out["granted"], len(ms.SCOPED_DOCTYPES))
		self.assertTrue(self.perms(self.old_email, for_value=self.rep))

	def test_sync_removes_somebody_who_no_longer_reports_there(self):
		ms.grant(self.old, self.rep)
		frappe.db.set_value("Employee", self.rep, "reports_to", self.new)
		out = ms.sync_for_manager(self.old)
		self.assertEqual(out["revoked"], len(ms.SCOPED_DOCTYPES))
		self.assertEqual(self.perms(self.old_email, for_value=self.rep), [])

	def test_only_direct_reports_not_the_whole_tree(self):
		"""A manager two levels up reviews their own reports, who review
		theirs. Granting the subtree would give a regional head every punch in
		the region - a different decision from the one taken here."""
		below, _ = self.person("Below")
		frappe.db.set_value("Employee", self.rep, "reports_to", self.old)
		frappe.db.set_value("Employee", below, "reports_to", self.rep)
		ms.sync_for_manager(self.old)
		self.assertTrue(self.perms(self.old_email, for_value=self.rep))
		self.assertEqual(self.perms(self.old_email, for_value=below), [],
		                 "the grandchild is their own manager's business")
