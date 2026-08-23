"""Wave 2 — the Module Profile that hides unsold modules.

These tests assert what it does AND what it does not do. The second part matters:
hiding a module is not a boundary, and a test suite that only proves the hiding
would let someone believe otherwise.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import module_access as ma
from alvoraa_portal import subscription as sub


class TestModuleProfile(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.db.rollback()

	def test_profile_hides_unsold_modules(self):
		ma.sync_module_profile(sub.plan_features("starter"))
		hidden = set(ma.get_hidden_modules()["blocked"])
		self.assertIn("Payroll", hidden, "starter does not include payroll")
		self.assertIn("Accounts", hidden, "no ERPNext module was ticked")

	def test_profile_keeps_sold_modules_visible(self):
		ma.sync_module_profile(sub.plan_features("business"))
		hidden = set(ma.get_hidden_modules()["blocked"])
		self.assertNotIn("Payroll", hidden, "business includes payroll")

	def test_ticked_erpnext_module_is_not_hidden(self):
		selection = sub.plan_features("starter") + ["erp_accounts"]
		ma.sync_module_profile(selection)
		hidden = set(ma.get_hidden_modules()["blocked"])
		self.assertNotIn("Accounts", hidden)
		self.assertIn("Stock", hidden, "modules not ticked stay hidden")

	def test_only_modules_that_exist_here_are_blocked(self):
		"""A site without alvoraa_goals has no such Module Def, and Frappe
		rejects a link to one that does not exist."""
		ma.sync_module_profile(sub.plan_features("starter"))
		existing = {m.name for m in frappe.get_all("Module Def", fields=["name"])}
		for m in ma.get_hidden_modules()["blocked"]:
			self.assertIn(m, existing, "%s does not exist on this site" % m)

	def test_syncing_twice_does_not_duplicate(self):
		ma.sync_module_profile(sub.plan_features("starter"))
		first = ma.get_hidden_modules()["blocked"]
		ma.sync_module_profile(sub.plan_features("starter"))
		self.assertEqual(first, ma.get_hidden_modules()["blocked"])

	def test_a_plan_change_updates_the_profile(self):
		ma.sync_module_profile(sub.plan_features("starter"))
		self.assertIn("Payroll", ma.get_hidden_modules()["blocked"])
		ma.sync_module_profile(sub.plan_features("business"))
		self.assertNotIn("Payroll", ma.get_hidden_modules()["blocked"])


class TestUserApplication(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		ma.sync_module_profile(sub.plan_features("starter"))
		self.user = "module.access.test@example.com"
		if not frappe.db.exists("User", self.user):
			u = frappe.get_doc({
				"doctype": "User", "email": self.user, "first_name": "Module Access",
				"send_welcome_email": 0, "enabled": 1,
			})
			u.flags.ignore_permissions = True
			u.insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()

	def test_applying_copies_the_blocks_onto_the_user(self):
		ma.apply_to_users([self.user])
		user = frappe.get_doc("User", self.user)
		self.assertEqual(user.module_profile, ma.PROFILE_NAME)
		blocked = {d.module for d in user.block_modules}
		self.assertIn("Payroll", blocked, "Frappe should copy the profile on save")

	def test_administrator_is_never_touched(self):
		"""If a profile is ever built wrong, support still needs a way in."""
		before = frappe.db.get_value("User", "Administrator", "module_profile")
		ma.apply_to_users(["Administrator"])
		self.assertEqual(frappe.db.get_value("User", "Administrator", "module_profile"), before)


class TestThisIsNotABoundary(FrappeTestCase):
	"""Recorded deliberately: wave 2 hides, wave 4 denies."""

	def test_blocking_a_module_does_not_remove_doctype_access(self):
		"""A blocked module is still reachable by API if the role allows it.

		This test exists so nobody reads the suite above and concludes the
		subscription boundary is enforced. It is not, until roles land.
		"""
		ma.sync_module_profile(sub.plan_features("starter"))
		self.assertIn("Payroll", ma.get_hidden_modules()["blocked"])

		# Administrator still reads a Payroll doctype, blocked module or not.
		frappe.set_user("Administrator")
		self.assertTrue(
			frappe.has_permission("Salary Slip", "read"),
			"hiding a module does not deny doctype access - that is wave 4",
		)
