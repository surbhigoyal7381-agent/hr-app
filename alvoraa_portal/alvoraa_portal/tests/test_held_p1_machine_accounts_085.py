"""Slice 085 (ALV-392), P1: the biometric sync accounts keep working.

On 2 Nov a role change made every DTC machine punch get refused (ALV-302). The
real accounts, biometric.sync@dtc and biometric.sync@grace, hold the machine
role PLUS HR roles, have no company permission and no Employee record. Each test
files the punch the way the account does: a real insert as that user, with
permissions ON (the other 085 tests insert as Administrator, which proves nothing
about rights).
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal.tests import test_held_day_085 as hd
from alvoraa_portal.tests.test_alv302_sync_punch import _grant, _take_back

SHAPES = {
	"machine_role_only": ["Biometric Sync"],
	"machine_and_hr_user": ["Biometric Sync", "HR User"],
	"machine_and_hr_manager": ["Biometric Sync", "HR Manager"],
}


class SyncAccounts(FrappeTestCase):
	def setUp(self):
		# Borrow the Held day fixtures; do not inherit (and re-run) its 30 tests.
		self.h = hd.HeldDayCase("test_held_is_a_status_and_the_fields_exist")
		self.h.setUp()
		for role in {r for roles in SHAPES.values() for r in roles}:
			if not frappe.db.exists("Role", role):
				frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
		# The machine role's create right on the punch is tenant setup, not code
		# (ALV-302 does the same). Put back exactly what we added.
		self._had_rows = _grant("Employee Checkin", read=0, write=0, create=1, delete=0)

	def tearDown(self):
		frappe.set_user("Administrator")
		_take_back("Employee Checkin", self._had_rows)

	def _account(self, shape):
		return self.h._login("sync" + shape.replace("_", ""), SHAPES[shape])

	def _file_as(self, user, employee, hhmm, log_type="OUT"):
		"""A punch filed the way the sync tool does: that user, permissions on."""
		frappe.set_user(user)
		try:
			return frappe.get_doc({"doctype": "Employee Checkin", "employee": employee,
			                       "time": "%s %s:00" % (self.h.day, hhmm), "log_type": log_type,
			                       "device_id": "ALV085-M1"}).insert()
		finally:
			frappe.set_user("Administrator")

	def test_every_sync_account_shape_can_still_insert_a_punch_for_an_employee(self):
		for shape in SHAPES:
			with self.subTest(shape=shape):
				user = self._account(shape)
				self.assertFalse(frappe.db.exists("Employee", {"user_id": user}))
				self.assertFalse(frappe.db.exists("User Permission", {"user": user}))
				punch = self._file_as(user, self.h.worker, "09:%02d" % (10 + list(SHAPES).index(shape)), "IN")
				self.assertTrue(frappe.db.exists("Employee Checkin", punch.name))

	def _late_punch_releases(self, shape):
		"""The late machine punch path (US-5). Held day with one punch at 09:00; the
		account then files the 18:30 Out. The day must release as 'Machine punch'."""
		worker = self.h._employee("W" + shape.replace("_", ""))
		att = self.h._held(worker)
		punch = self._file_as(self._account(shape), worker, "18:30")
		row = frappe.db.get_value("Attendance", att.name,
		                          ["status", "alvoraa_release_how", "alvoraa_release_by"], as_dict=True)
		self.assertEqual((row.status, row.alvoraa_release_how, row.alvoraa_release_by),
		                 ("Present", "Machine punch", punch.name))

	def test_a_machine_role_only_account_releases_a_held_day(self):
		self._late_punch_releases("machine_role_only")

	def test_the_real_tenant_accounts_with_hr_roles_release_a_held_day(self):
		"""DEFECT (P1): biometric.sync@dtc and @grace hold HR roles. is_machine_account()
		wants the machine role and nothing else, so for them US-5 never fires."""
		for shape in ("machine_and_hr_user", "machine_and_hr_manager"):
			with self.subTest(shape=shape):
				self._late_punch_releases(shape)
