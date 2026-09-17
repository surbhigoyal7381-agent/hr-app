"""Slice 012 F1 (SEC-18): pin tests for the org chart access settings.

set_cover_setting used to let an HR Manager write any of its keys. Two of them
decide who sees the whole org chart, so one call could add "Employee" to the
full-reach roles and show every employee the whole company, with no record of
who did it. These tests keep that closed:

- an HR Manager (or anyone else without System Manager) is refused on every
  access-granting key, the refusal is logged, and nothing is written;
- a System Manager may change them, and each change leaves a Version record
  with who, when, the key, the old value and the new one;
- an HR Manager still changes the ordinary cover settings as before.

They live in alvoraa_portal because CI runs only the alvoraa_portal and
alvoraa_goals suites.
"""

import json
from unittest.mock import patch

import frappe

from alvoraa_portal.tests.test_portal_security_010 import _Base, _user

FULL_REACH = "alvoraa_org_full_reach_roles"
MANAGERS_SEE_ALL = "alvoraa_org_managers_see_all"
ORDINARY = "alvoraa_cover_max_days"


def _settings():
	import hrms.alvoraa_org_structure.settings as settings

	return settings


def _records(key):
	return frappe.get_all(
		"Version",
		filters={"ref_doctype": "DefaultValue", "docname": key},
		fields=["name", "owner", "creation", "data"],
		order_by="creation desc",
	)


class TestSec18OrgAccessSettingsNeedSystemManager(_Base):
	KEYS = (FULL_REACH, MANAGERS_SEE_ALL, "alvoraa_org_reach_up", "alvoraa_org_reach_down", ORDINARY)

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hr_manager = _user("f1.hrmanager", ("HR Manager", "Employee"))
		cls.sysman = _user("f1.sysman", ("System Manager",))
		cls.employee = _user("f1.employee", ("Employee",))

	def setUp(self):
		super().setUp()
		self._saved = {k: frappe.db.get_default(k) for k in self.KEYS}
		self._versions_before = set(
			frappe.get_all("Version", filters={"ref_doctype": "DefaultValue"}, pluck="name")
		)
		frappe.db.set_default(FULL_REACH, "HR Manager,HR User,System Manager")
		frappe.db.set_default(MANAGERS_SEE_ALL, 1)
		frappe.db.set_default(ORDINARY, 90)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in frappe.get_all("Version", filters={"ref_doctype": "DefaultValue"}, pluck="name"):
			if name not in self._versions_before:
				frappe.delete_doc("Version", name, force=True, ignore_permissions=True)
		for k, v in self._saved.items():
			frappe.db.set_default(k, v if v is not None else "")
		frappe.db.commit()
		super().tearDown()

	def test_sec18_the_two_named_keys_are_access_granting(self):
		s = _settings()
		self.assertIn(FULL_REACH, s.ACCESS_GRANTING)
		self.assertIn(MANAGERS_SEE_ALL, s.ACCESS_GRANTING)
		self.assertNotIn(ORDINARY, s.ACCESS_GRANTING)
		# Every access-granting key is a real setting, so none is silently unused.
		self.assertTrue(s.ACCESS_GRANTING <= set(s.DEFAULTS))

	def test_sec18_hr_manager_is_refused_on_both_access_keys_and_nothing_is_written(self):
		s = _settings()
		for key, value in ((FULL_REACH, "HR Manager,HR User,System Manager,Employee"), (MANAGERS_SEE_ALL, 0)):
			before = frappe.db.get_default(key)
			frappe.set_user(self.hr_manager)
			with patch("hrms.alvoraa_hr_core.access.log_refusal") as logged:
				with self.assertRaises(frappe.PermissionError):
					s.set_cover_setting(key, value)
			frappe.set_user("Administrator")
			self.assertEqual(frappe.db.get_default(key), before, key)
			self.assertEqual(_records(key), [], key)
			logged.assert_called_once()
			self.assertEqual(logged.call_args.args[0], "SEC-18")

	def test_sec18_an_employee_is_refused_and_the_refusal_is_logged(self):
		s = _settings()
		frappe.set_user(self.employee)
		with patch("hrms.alvoraa_hr_core.access.log_refusal") as logged:
			with self.assertRaises(frappe.PermissionError):
				s.set_cover_setting(FULL_REACH, "Employee")
		frappe.set_user("Administrator")
		logged.assert_called_once()
		self.assertEqual(logged.call_args.args[0], "SEC-18")
		self.assertEqual(frappe.db.get_default(FULL_REACH), "HR Manager,HR User,System Manager")

	def test_sec18_system_manager_may_change_it_and_a_change_record_is_kept(self):
		s = _settings()
		frappe.set_user(self.sysman)
		out = s.set_cover_setting(FULL_REACH, "HR Manager,System Manager")
		frappe.set_user("Administrator")
		self.assertTrue(out["ok"])
		self.assertEqual(frappe.db.get_default(FULL_REACH), "HR Manager,System Manager")

		records = _records(FULL_REACH)
		self.assertEqual(len(records), 1)
		self.assertEqual(records[0].owner, self.sysman)
		self.assertTrue(records[0].creation)
		self.assertEqual(
			json.loads(records[0].data)["changed"],
			[[FULL_REACH, "HR Manager,HR User,System Manager", "HR Manager,System Manager"]],
		)

	def test_sec18_saving_the_same_value_again_writes_no_record(self):
		s = _settings()
		frappe.set_user(self.sysman)
		s.set_cover_setting(MANAGERS_SEE_ALL, 1)
		frappe.set_user("Administrator")
		self.assertEqual(_records(MANAGERS_SEE_ALL), [])

	def test_sec18_hr_manager_still_changes_an_ordinary_cover_setting(self):
		s = _settings()
		frappe.set_user(self.hr_manager)
		out = s.set_cover_setting(ORDINARY, 60)
		frappe.set_user("Administrator")
		self.assertTrue(out["ok"])
		self.assertEqual(s.get(ORDINARY), 60)
