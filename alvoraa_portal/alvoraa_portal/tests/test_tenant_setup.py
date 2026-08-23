"""Every tenant starts with two real logins, not a shared Administrator."""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import module_access as ma
from alvoraa_portal import subscription as sub
from alvoraa_portal import tenant_setup as ts

HR = "hr@tenantsetup.test"
ADMIN = "admin@tenantsetup.test"


class TestDefaultUsers(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		ma.sync_site(sub.plan_features("business"))
		for u in (HR, ADMIN):
			if frappe.db.exists("User", u):
				frappe.delete_doc("User", u, force=True, ignore_permissions=True)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _create(self):
		return ts.create_default_users(
			hr_email=HR, admin_email=ADMIN,
			hr_password="SetupHr#2026", admin_password="SetupAd#2026",
			tenant_name="Setup Test",
		)

	def test_both_accounts_are_created(self):
		created = self._create()
		self.assertEqual(created["hr"], HR)
		self.assertEqual(created["admin"], ADMIN)

	def test_they_get_the_right_roles(self):
		self._create()
		hr_roles = {r.role for r in frappe.get_doc("User", HR).roles}
		self.assertIn("HR Manager", hr_roles)
		admin_roles = {r.role for r in frappe.get_doc("User", ADMIN).roles}
		self.assertIn("System Manager", admin_roles)

	def test_module_access_follows_their_roles(self):
		"""Applied AFTER the roles are set, or the HR user would be treated as
		an ordinary employee and lose the desk they are meant to work in."""
		self._create()
		self.assertEqual(frappe.db.get_value("User", HR, "module_profile"),
		                 ma.HR_PROFILE_NAME)
		self.assertFalse(frappe.db.get_value("User", ADMIN, "module_profile"),
		                 "a tenant admin is exempt")

	def test_each_is_offered_the_right_switch(self):
		self._create()
		frappe.set_user(HR)
		self.assertEqual(ma.get_switch_target()["url"], "/app/hr")
		frappe.set_user(ADMIN)
		self.assertEqual(ma.get_switch_target()["url"], "/app")

	def test_running_twice_does_not_duplicate(self):
		"""Provisioning can be retried after a partial failure."""
		self._create()
		self._create()
		self.assertEqual(frappe.db.count("User", {"name": HR}), 1)

	def test_passwords_are_set(self):
		self._create()
		from frappe.utils.password import check_password
		self.assertTrue(check_password(HR, "SetupHr#2026"))

	def test_no_welcome_email_is_sent(self):
		"""Provisioning must not mail a new tenant's staff. The password goes
		back to the operator on screen instead."""
		self._create()
		self.assertFalse(frappe.db.get_value("User", HR, "send_welcome_email"))
