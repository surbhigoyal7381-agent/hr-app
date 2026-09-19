"""Slice 030, decision 4: a store's HR Manager cannot change organisation-wide settings.

set_org_setting writes a tenant-wide default after checking only the role. An HR
Manager whose reach is one store (a Branch User Permission) could therefore
change a setting for every store. The write now refuses anyone limited to a
store, using the same Branch User Permission read as access.permitted_employees,
so "limited to a store" has one definition. Reading stays open to them; System
Manager is unchanged; an HR User is refused as before (slice 012 G2).
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import hr_api

BRANCH = "S030 D4 Store"
KEY = "kra_link_mandatory"


def _user(first, *roles):
	email = f"{first.lower()}.s030d4@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
		                "send_welcome_email": 0}).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(*roles)
	return email


def _limit_to_store(user):
	if not frappe.db.exists("User Permission", {"user": user, "allow": "Branch", "for_value": BRANCH}):
		frappe.get_doc({"doctype": "User Permission", "user": user, "allow": "Branch",
		                "for_value": BRANCH, "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
	frappe.clear_cache(user=user)


class TestStoreHrManagerCannotWriteOrgSettings(FrappeTestCase):
	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		if not frappe.db.exists("Branch", BRANCH):
			frappe.get_doc({"doctype": "Branch", "branch": BRANCH}).insert(ignore_permissions=True)
		self.before = frappe.db.get_default(KEY) or "0"
		self.store_manager = _user("StoreMgrD4", "HR Manager")
		_limit_to_store(self.store_manager)
		self.central = _user("CentralD4", "HR Manager")
		self.hr_user = _user("HrUserD4", "HR User")
		self.sysman = _user("SysmanD4", "System Manager")
		frappe.db.commit()

	def tearDown(self):
		# set_org_setting commits, so the rollback alone would not undo this.
		frappe.set_user("Administrator")
		frappe.db.set_default(KEY, self.before)
		for user in (self.store_manager, self.sysman):
			frappe.db.delete("User Permission", {"user": user, "allow": "Branch"})
			frappe.clear_cache(user=user)
		frappe.db.commit()
		frappe.set_user(self.caller)

	def _flip(self):
		return "0" if self.before == "1" else "1"

	def test_a_store_hr_manager_is_refused_logged_and_the_value_does_not_move(self):
		frappe.set_user(self.store_manager)
		with patch("hrms.alvoraa_hr_core.access.log_refusal") as logged:
			with self.assertRaises(frappe.PermissionError):
				hr_api.set_org_setting(KEY, self._flip())
		self.assertEqual(logged.call_count, 1)
		self.assertEqual(logged.call_args.args[0], "030-D4")
		self.assertEqual(frappe.db.get_default(KEY) or "0", self.before)

	def test_a_store_hr_manager_may_still_read_the_setting(self):
		frappe.set_user(self.store_manager)
		self.assertEqual(hr_api.get_org_setting(KEY) or "0", self.before)

	def test_company_wide_hr_manager_and_system_manager_still_write(self):
		for user in (self.central, self.sysman):
			frappe.set_user(user)
			self.assertEqual(hr_api.set_org_setting(KEY, self._flip()), {"ok": True}, user)
			self.assertEqual(frappe.db.get_default(KEY), self._flip(), user)
			hr_api.set_org_setting(KEY, self.before)

	def test_a_system_manager_with_a_branch_permission_is_unchanged(self):
		frappe.set_user("Administrator")
		_limit_to_store(self.sysman)
		frappe.db.commit()
		frappe.set_user(self.sysman)
		self.assertEqual(hr_api.set_org_setting(KEY, self._flip()), {"ok": True})
		hr_api.set_org_setting(KEY, self.before)

	def test_an_hr_user_is_still_refused_as_before(self):
		frappe.set_user(self.hr_user)
		with self.assertRaises(frappe.PermissionError):
			hr_api.set_org_setting(KEY, self._flip())
