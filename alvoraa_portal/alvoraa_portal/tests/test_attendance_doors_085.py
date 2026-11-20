"""Slice 085 (ALV-392), Release 1: the safety doors.

SEC-2: nobody confirms, cancels, deletes or makes their OWN attendance, or
changes or deletes their own punch. SEC-3: nobody decides a request they raised
(Administrator, who is nobody's colleague, is exempt). SEC-4: an HR login with
no company and no branch looks after nobody.

Each refusal test has a positive control beside it: the same act, done for
somebody else or by somebody else, still works. Without the control a test that
is red for another reason would pass.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal import field_app_access as faa
from alvoraa_portal.tests.test_attendance_correction import (_company,
                                                             _holiday_list,
                                                             setUpModule)

REQUEST = "Attendance Request"


class SafetyDoors(FrappeTestCase):
	# Per test, never committed (a committed user survives rollback).
	_slot = 0

	def setUp(self):
		frappe.set_user("Administrator")
		SafetyDoors._slot += 1
		self.tag = "Sd%d" % SafetyDoors._slot
		self.company = _company()
		_holiday_list(self.company)
		self.hr = self._login("hr", ("HR Manager",))
		self.hr_emp = self._employee("Hremp", self.hr)
		self.colleague_hr = self._login("hr2", ("HR Manager",))
		self.colleague_emp = self._employee("Hr2emp", self.colleague_hr)
		self.worker = self._employee("Worker")

	def tearDown(self):
		frappe.set_user("Administrator")

	def _login(self, local, roles):
		email = "%s.%s.sd085@example.com" % (self.tag.lower(), local)
		u = frappe.get_doc({"doctype": "User", "email": email, "first_name": self.tag + local,
		                    "send_welcome_email": 0}).insert(ignore_permissions=True)
		for r in roles:
			u.add_roles(r)
		return email

	def _employee(self, first, user=None):
		doc = {"doctype": "Employee", "first_name": self.tag + first, "company": self.company,
		       "date_of_birth": "1970-01-01", "date_of_joining": "2000-01-01",
		       "gender": frappe.db.get_value("Gender", {}, "name") or "Male", "status": "Active"}
		if user:
			doc["user_id"] = user
			doc["create_user_permission"] = 0
		return frappe.get_doc(doc).insert(ignore_permissions=True).name

	def _attendance(self, employee, day=None):
		doc = frappe.get_doc({"doctype": "Attendance", "employee": employee,
		                      "attendance_date": day or add_days(nowdate(), -20),
		                      "status": "Present", "company": self.company})
		doc.insert(ignore_permissions=True)
		doc.submit()
		return doc

	def _as(self, user, fn):
		frappe.set_user(user)
		try:
			return fn()
		finally:
			frappe.set_user("Administrator")

	# ── SEC-2: own attendance ──────────────────────────────────────────────

	def test_cannot_cancel_own_attendance(self):
		own = self._attendance(self.hr_emp)
		with self.assertRaises(frappe.PermissionError):
			self._as(self.hr, lambda: frappe.get_doc("Attendance", own.name).cancel())
		self.assertEqual(frappe.db.get_value("Attendance", own.name, "docstatus"), 1)

	def test_can_cancel_a_colleagues_attendance(self):
		other = self._attendance(self.worker)
		self._as(self.hr, lambda: frappe.get_doc("Attendance", other.name).cancel())
		self.assertEqual(frappe.db.get_value("Attendance", other.name, "docstatus"), 2)

	def test_cannot_change_a_submitted_own_attendance(self):
		own = self._attendance(self.hr_emp)

		def edit():
			doc = frappe.get_doc("Attendance", own.name)
			doc.status = "Half Day"
			doc.save()
		with self.assertRaises(frappe.PermissionError):
			self._as(self.hr, edit)
		self.assertEqual(frappe.db.get_value("Attendance", own.name, "status"), "Present")

	def test_cannot_delete_own_attendance(self):
		own = self._attendance(self.hr_emp)
		own.cancel()  # Administrator cancels, so only the delete door is under test
		with self.assertRaises(frappe.PermissionError):
			self._as(self.hr, lambda: frappe.delete_doc("Attendance", own.name))
		self.assertTrue(frappe.db.exists("Attendance", own.name))

	def test_can_delete_a_colleagues_attendance(self):
		other = self._attendance(self.worker)
		other.cancel()
		self._as(self.hr, lambda: frappe.delete_doc("Attendance", other.name))
		self.assertFalse(frappe.db.exists("Attendance", other.name))

	def test_cannot_make_own_attendance(self):
		def make():
			frappe.get_doc({"doctype": "Attendance", "employee": self.hr_emp,
			                "attendance_date": add_days(nowdate(), -20), "status": "Present",
			                "company": self.company}).insert()
		with self.assertRaises(frappe.PermissionError):
			self._as(self.hr, make)

	def test_can_make_a_colleagues_attendance(self):
		def make():
			frappe.get_doc({"doctype": "Attendance", "employee": self.worker,
			                "attendance_date": add_days(nowdate(), -20), "status": "Present",
			                "company": self.company}).insert()
		self._as(self.hr, make)

	# ── SEC-2: own punch ───────────────────────────────────────────────────

	def _punch(self, employee):
		return frappe.get_doc({"doctype": "Employee Checkin", "employee": employee,
		                       "time": add_days(nowdate(), -20) + " 09:00:00",
		                       "log_type": "IN"}).insert(ignore_permissions=True)

	def test_hr_cannot_write_or_delete_own_punch_but_can_a_colleagues(self):
		own, other = self._punch(self.hr_emp), self._punch(self.worker)
		for ptype in ("write", "delete"):
			self.assertFalse(faa.checkin_has_permission(own, self.hr, ptype), ptype)
			self.assertTrue(faa.checkin_has_permission(other, self.hr, ptype), ptype)

	def test_hr_can_still_read_own_punch(self):
		own = self._punch(self.hr_emp)
		self.assertTrue(faa.checkin_has_permission(own, self.hr, "read"))

	def test_f1_hr_cannot_add_a_back_dated_punch_to_their_own_record(self):
		"""Review F1: HR may choose `time`, so a new punch of one's own is refused,
		through the hook and through a real insert with permissions on."""
		new = frappe.get_doc({"doctype": "Employee Checkin", "employee": self.hr_emp,
		                      "time": add_days(nowdate(), -3) + " 18:30:00", "log_type": "OUT"})
		self.assertFalse(faa.checkin_has_permission(new, self.hr, "create"))
		with self.assertRaises(frappe.PermissionError):
			self._as(self.hr, lambda: frappe.get_doc(new.as_dict()).insert())
		self.assertFalse(frappe.db.exists("Employee Checkin", {"employee": self.hr_emp}))
		# control: the same act for a colleague is still HR's
		other = frappe.get_doc({"doctype": "Employee Checkin", "employee": self.worker,
		                        "time": add_days(nowdate(), -3) + " 18:30:00", "log_type": "OUT"})
		self.assertTrue(faa.checkin_has_permission(other, self.hr, "create"))
		self._as(self.hr, lambda: frappe.get_doc(other.as_dict()).insert())
		self.assertTrue(frappe.db.exists("Employee Checkin", {"employee": self.worker}))

	# ── SEC-3: the raiser ──────────────────────────────────────────────────

	def _raise(self, by, employee):
		def go():
			day = add_days(nowdate(), -3)
			doc = frappe.get_doc({"doctype": REQUEST, "employee": employee,
			                      "from_date": day, "to_date": day, "reason": "Forgot to Punch In",
			                      "explanation": "I was at the gate by nine, the reader did not beep"})
			doc.insert(ignore_permissions=True)
			return doc.name
		return self._as(by, go)

	def _submit(self, by, name):
		return self._as(by, lambda: frappe.get_doc(REQUEST, name).submit())

	def test_raiser_cannot_submit_but_a_colleague_can(self):
		name = self._raise(self.hr, self.worker)
		with self.assertRaises(frappe.PermissionError):
			self._submit(self.hr, name)
		self.assertEqual(frappe.db.get_value(REQUEST, name, "docstatus"), 0)
		self._submit(self.colleague_hr, name)
		self.assertEqual(frappe.db.get_value(REQUEST, name, "docstatus"), 1)

	def test_a_named_system_manager_raiser_is_refused_too(self):
		sm = self._login("sm", ("System Manager",))
		name = self._raise(sm, self.worker)
		with self.assertRaises(frappe.PermissionError):
			self._submit(sm, name)

	def test_administrator_raising_and_submitting_is_exempt(self):
		name = self._raise("Administrator", self.worker)
		self._submit("Administrator", name)
		self.assertEqual(frappe.db.get_value(REQUEST, name, "docstatus"), 1)

	# ── SEC-4: scope fails closed ──────────────────────────────────────────

	def test_hr_login_with_no_company_and_no_branch_sees_nobody(self):
		nobody = self._login("nobody", ("HR Manager",))  # no Employee record, no permissions
		frappe.set_user(nobody)
		try:
			self.assertEqual(ac._scope_conditions(), [["name", "in", []]])
			with self.assertRaises(frappe.PermissionError):
				ac._refuse_outside_scope(self.worker, "test")
			self.assertEqual(ac.whose_months_i_can_open(), [])
		finally:
			frappe.set_user("Administrator")

	def test_hr_with_a_company_is_still_scoped_to_it(self):
		frappe.set_user(self.hr)
		try:
			ac._refuse_outside_scope(self.worker, "test")  # same company: no refusal
			self.assertIn(self.worker, [r["name"] for r in ac.whose_months_i_can_open(limit=500)])
		finally:
			frappe.set_user("Administrator")

	def test_system_manager_still_sees_everyone(self):
		sm = self._login("sm2", ("System Manager",))
		frappe.set_user(sm)
		try:
			ac._refuse_outside_scope(self.worker, "test")
		finally:
			frappe.set_user("Administrator")
