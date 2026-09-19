"""Slice 012 push 1 · G2: one settings call cannot unlock named leave data.

US-10, SEC-18, SEC-19 (Q6), AC-51 to AC-54. Calls the endpoints, never the page:
they are whitelisted, and anyone with a portal login can call them directly.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import attendance_analytics as aa
from alvoraa_portal import hr_api


def _user(first, *roles):
	email = f"{first.lower()}.s012g2@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
		                "send_welcome_email": 0}).insert(ignore_permissions=True)
	if roles:
		frappe.get_doc("User", email).add_roles(*roles)
	return email


class G2Case(FrappeTestCase):
	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		for role in ("Leadership", "Employee Self Service"):
			if not frappe.db.exists("Role", role):
				frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
		self.priya = _user("PriyaG2", "HR Manager")

	def tearDown(self):
		frappe.set_user(self.caller)


class TestSetOrgSettingAllowList(G2Case):
	def test_kra_link_mandatory_still_saves(self):
		"""AC-51, AC-54: the one key the Org Settings screen writes."""
		frappe.set_user(self.priya)
		self.assertEqual(hr_api.set_org_setting("kra_link_mandatory", "1"), {"ok": True})
		self.assertEqual(frappe.db.get_default("kra_link_mandatory"), "1")
		hr_api.set_org_setting("kra_link_mandatory", "0")
		self.assertEqual(frappe.db.get_default("kra_link_mandatory"), "0")

	def test_every_other_key_is_refused_unchanged_and_logged(self):
		"""AC-51: the G2 leak. One security line per refused call."""
		frappe.set_user("Administrator")
		before = {k: frappe.db.get_default(k)
		          for k in ("alvoraa_attendance_org_roles", "currency", "made_up_key")}
		frappe.set_user(self.priya)
		with patch("hrms.alvoraa_hr_core.access.log_refusal") as logged:
			for key, value in (("alvoraa_attendance_org_roles", "HR Manager,Employee"),
			                   ("currency", "USD"), ("made_up_key", "x")):
				with self.assertRaises(frappe.PermissionError):
					hr_api.set_org_setting(key, value)
			self.assertEqual(logged.call_count, 3)
			for call in logged.call_args_list:
				self.assertEqual(call.args[0], "SEC-18")
				# No key and no value in the log line.
				self.assertNotIn("Employee", repr(call))
				self.assertNotIn("USD", repr(call))
		frappe.set_user("Administrator")
		for k, v in before.items():
			self.assertEqual(frappe.db.get_default(k), v, k)

	def test_a_value_outside_zero_and_one_is_refused(self):
		frappe.set_user(self.priya)
		with self.assertRaises(frappe.PermissionError):
			hr_api.set_org_setting("kra_link_mandatory", "HR Manager")

	def test_reading_is_limited_to_the_same_keys(self):
		"""AC-52."""
		frappe.set_user(self.priya)
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_org_setting("currency")
		hr_api.get_org_setting("kra_link_mandatory")

	def test_a_system_manager_is_held_to_the_same_list(self):
		"""The console is still there for them; this endpoint is not a back door."""
		frappe.set_user(_user("VikramG2", "System Manager"))
		with self.assertRaises(frappe.PermissionError):
			hr_api.set_org_setting("alvoraa_attendance_org_roles", "HR User")

	def test_the_page_still_calls_only_the_allowed_key(self):
		"""AC-54 at the source: a new key written from the page needs this list changed too."""
		import os
		import re

		path = os.path.join(os.path.dirname(hr_api.__file__), "www", "hrms-employee.html")
		with open(path, encoding="utf-8-sig") as f:
			page = f.read()
		keys = set(re.findall(r'_org_setting",\s*\{key:\s*"([^"]+)"', page))
		self.assertTrue(keys)
		self.assertLessEqual(keys, set(hr_api.ALLOWED_ORG_SETTINGS))


class TestOrgRolesGuard(G2Case):
	"""AC-53: even a value stored from the console cannot open the organisation view."""

	STORED = "HR User,Leadership,Employee,Employee Self Service"

	def setUp(self):
		super().setUp()
		self._saved = frappe.db.get_default(aa.ORG_ROLES_KEY)
		frappe.db.set_default(aa.ORG_ROLES_KEY, self.STORED)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_default(aa.ORG_ROLES_KEY, self._saved or "")
		super().tearDown()

	def _refused_everywhere(self, user):
		frappe.set_user(user)
		with self.assertRaises(frappe.PermissionError):
			aa.summary(view="organisation")
		with self.assertRaises(frappe.PermissionError):
			aa.filter_options()

	def test_a_leadership_only_user_is_refused(self):
		with patch("frappe.logger") as logger:
			self._refused_everywhere(_user("LeaderG2", "Leadership"))
		lines = [c.args[0] for c in logger.return_value.warning.call_args_list]
		self.assertTrue(any('"org_roles_ignored"' in line for line in lines))
		for line in lines:
			if "org_roles_ignored" in line:
				# Role names and nothing else.
				self.assertIn("Leadership", line)
				self.assertNotIn("LeaderG2", line)

	def test_a_plain_employee_is_refused(self):
		self._refused_everywhere(_user("SunilG2", "Employee"))

	def test_frappe_automatic_roles_never_count(self):
		"""D-11: "All" and "Guest" are held by every user."""
		frappe.db.set_default(aa.ORG_ROLES_KEY, "All,Guest,Desk User")
		self._refused_everywhere(_user("NobodyG2", "Employee"))

	def test_an_hr_user_still_gets_the_organisation_view(self):
		frappe.set_user(_user("StoreHRG2", "HR User"))
		self.assertEqual(aa.summary(view="organisation")["view"], "organisation")
		self.assertNotIn("Leadership", aa._org_roles())
		self.assertIn("HR User", aa._org_roles())
