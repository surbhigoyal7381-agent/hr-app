"""ALV-302: a biometric sync account with no HR role can file a punch, and only that.

On DTC an account holding only `Biometric Sync` was refused every device punch
from 2 Nov to 3 Nov 2026, because `checkin_has_permission` let through only HR
and people with an employee record.

Two faults sat on top of each other, and these tests pin both:

  * the hook's third parameter was spelled `permission_type`. Frappe passes
    `ptype=`, and `frappe.call` drops a keyword the function does not declare,
    so the hook could never tell a create from a read;
  * `Employee Checkin.time` is permlevel 1. A role with no write at that level
    has the value replaced by the default, "Now", on insert. The punch would be
    filed with no error at the moment it was SENT, not the moment it happened.

Every check runs under two shapes of the role's permission row, because the row
is hand-made per tenant and we cannot assume which one a tenant has: create only,
and create plus read. Under the second the hook is the only thing refusing a read.

Fail-without-fix recipe:
  * undo the fix: `test_files_a_punch...` fails (PermissionError);
  * spell the parameter `permission_type` again: the same test fails;
  * drop the `before_insert` line in hooks.py: the same test fails on the time;
  * let the role through the hook for every operation: the reading, photo and
    changing tests fail;
  * drop `doc.is_new()` from the hook: the changing test fails (create on a saved punch);
  * drop the role check from the hook: the colleague test fails;
  * drop the role check from `keep_machine_punch_time`: the own-time test fails;
  * give the role every row in `checkin_query_conditions`: the list test fails.

The reading and colleague tests pass with no fix at all, because they describe
what is already true. They exist to catch a fix that opens too much.
"""

import frappe
import frappe.client
import frappe.share
from frappe.desk.reportview import execute as report_execute
from frappe.desk.search import search_link
from frappe.permissions import add_permission
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_datetime, today

from alvoraa_goals.tests.utils import ensure_company
from alvoraa_portal.field_app_access import SYNC_ROLE
from alvoraa_portal.tests.test_field_app_step2_013 import _employee
from alvoraa_portal.tests.test_portal_security_010 import _user
from hrms.hr.doctype.employee_checkin.employee_checkin import add_log_based_on_employee_field

CHECKIN = "Employee Checkin"
SHIFT = "ALV302 Shift"
MACHINE = "ALV302-M1"
AUTOMATIC_ROLES = {"All", "Guest", "Desk User"}


def _rows(read) -> list:
	"""What a read door gave back. A refusal and an empty answer both show nothing."""
	try:
		return read() or []
	except frappe.PermissionError:
		return []
	finally:
		frappe.clear_messages()


class _Checks:
	"""The checks. Each subclass runs them under one shape of the permission row."""

	CAN_READ_ROW = 0

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		if not frappe.db.exists("Role", SYNC_ROLE):
			frappe.get_doc({"doctype": "Role", "role_name": SYNC_ROLE}).insert(ignore_permissions=True)

		cls.custom_rows_before = bool(frappe.db.exists("Custom DocPerm", {"parent": CHECKIN}))
		add_permission(CHECKIN, SYNC_ROLE, ptype="create")
		frappe.db.set_value("Custom DocPerm", {"parent": CHECKIN, "role": SYNC_ROLE},
		                    {"create": 1, "read": cls.CAN_READ_ROW, "write": 0})

		if not frappe.db.exists("Shift Type", SHIFT):
			frappe.get_doc({"doctype": "Shift Type", "name": SHIFT, "start_time": "09:00:00",
			                "end_time": "18:00:00"}).insert(ignore_permissions=True)

		company = ensure_company()
		cls.sync = _user("alv302.sync", [SYNC_ROLE])
		cls.staff = _user("alv302.staff", ["Employee"])
		cls.worker = _employee("Alv302 Worker", company)
		cls.colleague = _employee("Alv302 Colleague", company, user=cls.staff)
		frappe.db.set_value("Employee", cls.worker,
		                    {"attendance_device_id": "ALV302-W", "default_shift": SHIFT})
		frappe.db.set_value("Employee", cls.colleague, "attendance_device_id", "ALV302-C")
		frappe.clear_cache()
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		frappe.db.delete("Custom DocPerm", {"parent": CHECKIN, "role": SYNC_ROLE})
		if not cls.custom_rows_before:
			# We caused the copy of the standard rows, so we take it away again.
			frappe.db.delete("Custom DocPerm", {"parent": CHECKIN})
		frappe.clear_cache()
		frappe.db.commit()
		super().tearDownClass()

	def setUp(self):
		frappe.set_user("Administrator")
		self.when = f"{add_days(today(), -3)} 09:05:00"
		self.addCleanup(self._clean)

	def _clean(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Employee Checkin", {"employee": ["in", (self.worker, self.colleague)]})
		frappe.db.delete("File", {"file_name": "alv302-face.txt"})
		frappe.db.commit()

	def _a_punch_already_on_file(self) -> str:
		"""Somebody else's punch, filed by Administrator."""
		frappe.set_user("Administrator")
		doc = frappe.get_doc({"doctype": CHECKIN, "employee": self.worker,
		                      "time": f"{add_days(today(), -4)} 09:00:00", "device_id": MACHINE})
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_the_account_really_holds_only_the_sync_role(self):
		self.assertEqual(set(frappe.get_roles(self.sync)) - AUTOMATIC_ROLES, {SYNC_ROLE})
		self.assertFalse(frappe.db.exists("Employee", {"user_id": self.sync}))

	def test_files_a_punch_with_the_machine_time_and_the_shift(self):
		frappe.set_user(self.sync)
		name = add_log_based_on_employee_field(
			"ALV302-W", self.when, device_id=MACHINE, latitude=28.6, longitude=77.2).name
		frappe.set_user("Administrator")

		row = frappe.db.get_value(CHECKIN, name, ["employee", "time", "owner", "device_id", "shift"],
		                          as_dict=True)
		self.assertEqual(row.employee, self.worker)
		self.assertEqual(get_datetime(row.time), get_datetime(self.when),
		                 "the punch must keep the time the machine recorded, not the time it arrived")
		self.assertEqual(row.owner, self.sync)
		self.assertEqual(row.device_id, MACHINE)
		self.assertEqual(row.shift, SHIFT, "the shift lookup must work for this account")

	def test_cannot_read_a_punch_it_filed_itself(self):
		frappe.set_user(self.sync)
		name = add_log_based_on_employee_field("ALV302-W", self.when, device_id=MACHINE).name
		self.assertFalse(frappe.has_permission(CHECKIN, "read", doc=name, user=self.sync))

	def test_cannot_read_another_persons_punch_by_name(self):
		name = self._a_punch_already_on_file()
		frappe.set_user(self.sync)
		for ptype in ("read", "select", "print", "email", "report", "export"):
			self.assertFalse(frappe.has_permission(CHECKIN, ptype, doc=name, user=self.sync),
			                 f"{ptype} must be refused")
		with self.assertRaises(frappe.PermissionError):
			frappe.client.get(CHECKIN, name)
		self.assertFalse(_rows(lambda: frappe.client.get_value(CHECKIN, "employee", {"name": name})))

	def test_cannot_list_punches_through_any_door(self):
		name = self._a_punch_already_on_file()
		frappe.set_user(self.sync)

		def names(rows):
			return [r.get("name") if isinstance(r, dict) else r for r in rows]

		self.assertNotIn(name, names(_rows(lambda: frappe.get_list(CHECKIN, fields=["name"]))))
		self.assertNotIn(name, names(_rows(lambda: frappe.client.get_list(CHECKIN, fields=["name"]))))
		self.assertNotIn(name, names(_rows(lambda: report_execute(CHECKIN, fields=["name"]))))
		self.assertEqual(_rows(lambda: search_link(CHECKIN, name)), [])

	def test_cannot_change_share_or_remove_an_existing_punch(self):
		name = self._a_punch_already_on_file()
		frappe.set_user(self.sync)
		for ptype in ("write", "delete", "share", "create"):
			self.assertFalse(frappe.has_permission(CHECKIN, ptype, doc=name, user=self.sync),
			                 f"{ptype} on a saved punch must be refused")
		with self.assertRaises(frappe.PermissionError):
			frappe.client.set_value(CHECKIN, name, "device_id", "changed")
		with self.assertRaises(frappe.PermissionError):
			frappe.client.delete(CHECKIN, name)
		with self.assertRaises(frappe.PermissionError):
			frappe.share.add_docshare(CHECKIN, name, self.sync, read=1)
		frappe.clear_messages()

		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(CHECKIN, name, "device_id"), MACHINE)

	def test_cannot_read_the_photo_on_a_punch(self):
		name = self._a_punch_already_on_file()
		photo = frappe.get_doc({
			"doctype": "File", "file_name": "alv302-face.txt", "content": b"not a real face",
			"is_private": 1, "attached_to_doctype": CHECKIN, "attached_to_name": name,
		}).insert(ignore_permissions=True)
		self.assertFalse(frappe.has_permission("File", "read", doc=photo.name, user=self.sync))

	def test_an_employee_still_cannot_file_for_a_colleague(self):
		frappe.set_user(self.staff)
		with self.assertRaises(frappe.PermissionError):
			add_log_based_on_employee_field("ALV302-W", self.when, device_id=MACHINE)
		frappe.clear_messages()

		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists(CHECKIN, {"employee": self.worker}))

	def test_an_employee_still_cannot_choose_the_time_of_their_own_punch(self):
		"""Keeping the sent time is for the machine role. A person gets "Now"."""
		frappe.set_user(self.staff)
		name = add_log_based_on_employee_field("ALV302-C", self.when, device_id=MACHINE).name

		frappe.set_user("Administrator")
		self.assertNotEqual(get_datetime(frappe.db.get_value(CHECKIN, name, "time")),
		                    get_datetime(self.when))


class TestAlv302RowGrantsCreateOnly(_Checks, FrappeTestCase):
	CAN_READ_ROW = 0


class TestAlv302RowAlsoGrantsRead(_Checks, FrappeTestCase):
	"""The hook alone must hold when the tenant's row also says read."""

	CAN_READ_ROW = 1
