"""Slice 085 (ALV-392), residual risks R2, R4 and R5 closed.

R2  a sync account that has Company permissions files punches only for those
    companies, and a refusal is logged;
R4  a human HR login adds, changes and deletes punches only for the companies it
    may act for (`permitted_companies`);
R5  approving an Attendance Request or an Attendance (a submit) is scoped to the
    same companies on every door, not only in the portal.

Each refusal has an allowed case beside it. Fixtures are borrowed from
test_held_day_085 by composition, so its tests do not run twice.
"""

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_doors as doors
from alvoraa_portal import field_app_access as faa
from alvoraa_portal.tests import test_held_day_085 as hd

REQUEST = "Attendance Request"


class _Base(FrappeTestCase):
	def setUp(self):
		self.h = hd.HeldDayCase("test_held_is_a_status_and_the_fields_exist")
		self.h.setUp()
		self.a_worker = self.h.worker                                   # company A
		self.b_worker = self.h._employee("Bworker", company=self.h.other_company)

	def tearDown(self):
		frappe.set_user("Administrator")

	_n = 0

	def _punch_doc(self, employee, saved=False):
		_Base._n += 1  # a different minute each time: one punch per employee per timestamp
		doc = frappe.get_doc({"doctype": "Employee Checkin", "employee": employee, "log_type": "IN",
		                      "time": "%s 09:%02d:00" % (add_days(nowdate(), -4), _Base._n % 60)})
		if saved:
			doc.insert(ignore_permissions=True)
		return doc


class R4HumanHrPunches(_Base):
	def test_hr_touches_punches_of_their_own_company_only(self):
		for ptype in ("create", "write", "delete"):
			saved = ptype != "create"
			with self.subTest(ptype=ptype):
				mine = self._punch_doc(self.a_worker, saved)
				theirs = self._punch_doc(self.b_worker, saved)
				self.assertTrue(faa.checkin_has_permission(mine, self.h.hr, ptype))
				self.assertFalse(faa.checkin_has_permission(theirs, self.h.hr, ptype))

	def test_a_real_insert_for_another_company_is_refused_and_logged(self):
		fake = MagicMock()
		with patch("hrms.alvoraa_hr_core.access.security_logger", return_value=fake):
			frappe.set_user(self.h.hr)
			with self.assertRaises(frappe.PermissionError):
				self._punch_doc(self.b_worker).insert()
			frappe.set_user("Administrator")
		self.assertIn('"rule": "R4"', fake.warning.call_args.args[0])
		frappe.set_user(self.h.hr)
		self._punch_doc(self.a_worker).insert()  # control: own company
		frappe.set_user("Administrator")

	def test_a_company_user_permission_widens_it_and_no_company_at_all_locks_it(self):
		other = self.h._login("hrwide", ("HR Manager",))
		self.h._employee("Hrwide", other)  # company A by the Employee record
		self.assertFalse(faa.checkin_has_permission(self._punch_doc(self.b_worker), other, "create"))
		frappe.get_doc({"doctype": "User Permission", "user": other, "allow": "Company",
		                "for_value": self.h.other_company}).insert(ignore_permissions=True)
		frappe.clear_cache()
		self.assertTrue(faa.checkin_has_permission(self._punch_doc(self.b_worker), other, "create"))
		# no Employee record and no User Permission: nothing (the M-2 lock-out, on purpose)
		nobody = self.h._login("hrnone", ("HR Manager",))
		self.assertFalse(faa.checkin_has_permission(self._punch_doc(self.a_worker), nobody, "create"))
		# a System Manager is every company
		boss = self.h._login("boss", ("System Manager",))
		self.assertTrue(faa.checkin_has_permission(self._punch_doc(self.b_worker), boss, "create"))


class R2SyncAccounts(_Base):
	def _sync(self, shape="hr"):
		if not frappe.db.exists("Role", "Biometric Sync"):
			frappe.get_doc({"doctype": "Role", "role_name": "Biometric Sync"}).insert(ignore_permissions=True)
		return self.h._login("sync" + shape, ("Biometric Sync", "HR User"))

	def test_a_scoped_sync_account_files_only_for_its_companies_and_it_is_logged(self):
		user = self._sync()
		self.assertTrue(faa.files_as_machine(user))
		# no Company permission yet: unscoped, as today (ALV-302)
		self.assertTrue(faa.checkin_has_permission(self._punch_doc(self.b_worker), user, "create"))
		frappe.get_doc({"doctype": "User Permission", "user": user, "allow": "Company",
		                "for_value": self.h.company}).insert(ignore_permissions=True)
		frappe.clear_cache()
		self.assertTrue(faa.checkin_has_permission(self._punch_doc(self.a_worker), user, "create"))
		fake = MagicMock()
		with patch("hrms.alvoraa_hr_core.access.security_logger", return_value=fake):
			self.assertFalse(faa.checkin_has_permission(self._punch_doc(self.b_worker), user, "create"))
		self.assertIn('"rule": "R2"', fake.warning.call_args.args[0])
		self.assertEqual(json.loads(fake.warning.call_args.args[0])["endpoint"], "Employee Checkin")


class R5ApproveInScope(_Base):
	def _request(self, employee):
		day = add_days(nowdate(), -3)
		return frappe.get_doc({"doctype": REQUEST, "employee": employee, "from_date": day, "to_date": day,
		                       "reason": "Marked Absent by Mistake",
		                       "alvoraa_review_status": "Waiting"}).insert(ignore_permissions=True)

	def _submit_as(self, user, doc):
		frappe.set_user(user)
		try:
			frappe.get_doc(doc.doctype, doc.name).submit()
		finally:
			frappe.set_user("Administrator")

	def test_an_hr_login_cannot_submit_a_request_for_another_company_on_any_door(self):
		theirs = self._request(self.b_worker)
		fake = MagicMock()
		with patch("hrms.alvoraa_hr_core.access.security_logger", return_value=fake):
			with self.assertRaises(frappe.PermissionError):
				self._submit_as(self.h.hr, theirs)
		self.assertIn('"rule": "R5"', fake.warning.call_args.args[0])
		self.assertEqual(frappe.db.get_value(REQUEST, theirs.name, "docstatus"), 0)
		mine = self._request(self.a_worker)
		self._submit_as(self.h.hr, mine)  # control: own company
		self.assertEqual(frappe.db.get_value(REQUEST, mine.name, "docstatus"), 1)

	def test_the_same_check_stands_alone_and_covers_an_attendance(self):
		att = frappe.get_doc({"doctype": "Attendance", "employee": self.b_worker,
		                      "company": self.h.other_company, "attendance_date": add_days(nowdate(), -3),
		                      "status": "Present"}).insert(ignore_permissions=True)
		frappe.set_user(self.h.hr)
		try:
			with self.assertRaises(frappe.PermissionError):
				doors.refuse_outside_company(att)
		finally:
			frappe.set_user("Administrator")
		doors.refuse_outside_company(att)  # Administrator is exempt
		self.assertIn("alvoraa_portal.attendance_doors.refuse_outside_company",
		              frappe.get_hooks("doc_events")["Attendance"]["before_submit"])
		self.assertIn("alvoraa_portal.attendance_doors.refuse_outside_company",
		              frappe.get_hooks("doc_events")["Attendance Request"]["before_submit"])
