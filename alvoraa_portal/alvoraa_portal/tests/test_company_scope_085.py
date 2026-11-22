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


# ── fix round 3 (20 Nov 2026) ───────────────────────────────────────────────

class PunchMovedAcrossCompanies(_Base):
	"""Review P1: a save is judged on the punch as it will be stored, so the
	employee can be changed in the same request. The stored employee is judged too."""

	def _moved(self, punch, to):
		doc = frappe.get_doc("Employee Checkin", punch.name)
		doc.employee = to
		return doc

	def test_hr_cannot_move_a_punch_into_or_out_of_their_company(self):
		a_other = self.h._employee("Aother")
		theirs = self._punch_doc(self.b_worker, saved=True)
		mine = self._punch_doc(self.a_worker, saved=True)
		fake = MagicMock()
		with patch("hrms.alvoraa_hr_core.access.security_logger", return_value=fake):
			# another company's punch moved to one of mine
			self.assertFalse(faa.checkin_has_permission(self._moved(theirs, a_other), self.h.hr, "write"))
		self.assertIn('"rule": "R4"', fake.warning.call_args.args[0])
		# my punch moved to another company's person
		self.assertFalse(faa.checkin_has_permission(self._moved(mine, self.b_worker), self.h.hr, "write"))
		# control: inside my company, either person
		self.assertTrue(faa.checkin_has_permission(self._moved(mine, a_other), self.h.hr, "write"))
		# and on a real save through the API path
		frappe.set_user(self.h.hr)
		try:
			doc = self._moved(theirs, a_other)
			with self.assertRaises(frappe.PermissionError):
				doc.save()
			self.assertEqual(frappe.db.get_value("Employee Checkin", theirs.name, "employee"), self.b_worker)
			self._moved(mine, a_other).save()  # control
		finally:
			frappe.set_user("Administrator")

	def test_hr_cannot_move_their_own_punch_or_pull_one_onto_their_own_record(self):
		a_other = self.a_worker
		own = self._punch_doc(self.h.hr_emp, saved=True)
		colleague = self._punch_doc(a_other, saved=True)
		self.assertFalse(faa.checkin_has_permission(self._moved(own, a_other), self.h.hr, "write"))
		self.assertFalse(faa.checkin_has_permission(self._moved(colleague, self.h.hr_emp), self.h.hr, "write"))
		self.assertTrue(faa.checkin_has_permission(colleague, self.h.hr, "write"))  # control

	def test_a_leaver_with_an_hr_login_is_still_refused_their_own_punch(self):
		"""F7: the own-record refusals do not depend on the Employee being Active."""
		own = self._punch_doc(self.h.hr_emp, saved=True)
		# a Company row keeps the company rule (R4) satisfied, so only the own-record rule can refuse
		frappe.get_doc({"doctype": "User Permission", "user": self.h.hr, "allow": "Company",
		                "for_value": self.h.company}).insert(ignore_permissions=True)
		frappe.clear_cache()
		self.assertTrue(faa.checkin_has_permission(self._punch_doc(self.a_worker, True), self.h.hr, "write"))
		frappe.db.set_value("Employee", self.h.hr_emp, "status", "Left")
		self.assertFalse(faa.checkin_has_permission(own, self.h.hr, "write"))
		self.assertFalse(faa.checkin_has_permission(self._punch_doc(self.h.hr_emp), self.h.hr, "create"))

	def test_the_refusal_log_names_the_user_being_checked(self):
		fake = MagicMock()
		with patch("hrms.alvoraa_hr_core.access.security_logger", return_value=fake):
			self.assertFalse(faa.checkin_has_permission(self._punch_doc(self.b_worker), self.h.hr, "create"))
		line = json.loads(fake.warning.call_args.args[0])
		self.assertEqual(line["user"], self.h.hr)  # the user checked, not the session user (Administrator)


class SyncAccountWriteAndDelete(_Base):
	_sync = R2SyncAccounts._sync

	def _scoped(self, **row):
		user = self._sync()
		frappe.get_doc({"doctype": "User Permission", "user": user, "allow": "Company",
		                "for_value": self.h.company, **row}).insert(ignore_permissions=True)
		frappe.clear_cache()
		return user

	def test_a_scoped_sync_account_writes_and_deletes_only_for_its_companies(self):
		user = self._scoped()
		for ptype in ("write", "delete"):
			with self.subTest(ptype=ptype):
				self.assertTrue(faa.checkin_has_permission(self._punch_doc(self.a_worker, True), user, ptype))
				self.assertFalse(faa.checkin_has_permission(self._punch_doc(self.b_worker, True), user, ptype))
		# and a punch cannot be moved out of its scope in the same save
		mine = self._punch_doc(self.a_worker, True)
		mine.employee = self.b_worker
		self.assertFalse(faa.checkin_has_permission(mine, user, "write"))

	def test_a_sync_account_with_no_rows_is_still_unscoped(self):
		user = self._sync("norows")
		for ptype in ("write", "delete"):
			self.assertTrue(faa.checkin_has_permission(self._punch_doc(self.b_worker, True), user, ptype))

	def test_s3_a_row_that_does_not_apply_to_punches_does_not_scope_the_account(self):
		# A row for another doctype only: with the old read, this one row would
		# have refused every punch for any other company.
		user = self._scoped(apply_to_all_doctypes=0, applicable_for="Leave Application")
		self.assertTrue(faa.checkin_has_permission(self._punch_doc(self.b_worker), user, "create"))
		# A row that applies to Employee Checkin does scope it
		other = self._sync("narrow")
		frappe.get_doc({"doctype": "User Permission", "user": other, "allow": "Company",
		                "for_value": self.h.company, "apply_to_all_doctypes": 0,
		                "applicable_for": "Employee Checkin"}).insert(ignore_permissions=True)
		frappe.clear_cache()
		self.assertTrue(faa.checkin_has_permission(self._punch_doc(self.a_worker), other, "create"))
		self.assertFalse(faa.checkin_has_permission(self._punch_doc(self.b_worker), other, "create"))


class R5CancelAndAmend(_Base):
	_request = R5ApproveInScope._request

	def _submitted_attendance(self, employee, company):
		att = frappe.get_doc({"doctype": "Attendance", "employee": employee, "company": company,
		                      "attendance_date": add_days(nowdate(), -6), "status": "Present"})
		att.insert(ignore_permissions=True)
		att.submit()
		return att

	def _cancel_as(self, user, doc):
		frappe.set_user(user)
		try:
			frappe.get_doc(doc.doctype, doc.name).cancel()
		finally:
			frappe.set_user("Administrator")

	def test_an_hr_login_cannot_cancel_attendance_of_another_company(self):
		theirs = self._submitted_attendance(self.b_worker, self.h.other_company)
		mine = self._submitted_attendance(self.a_worker, self.h.company)
		fake = MagicMock()
		with patch("hrms.alvoraa_hr_core.access.security_logger", return_value=fake):
			with self.assertRaises(frappe.PermissionError):
				self._cancel_as(self.h.hr, theirs)
		self.assertIn('"rule": "R5"', fake.warning.call_args.args[0])
		self.assertEqual(frappe.db.get_value("Attendance", theirs.name, "docstatus"), 1)
		self._cancel_as(self.h.hr, mine)  # control
		self.assertEqual(frappe.db.get_value("Attendance", mine.name, "docstatus"), 2)

	def test_an_hr_login_cannot_cancel_a_request_of_another_company(self):
		theirs = self._request(self.b_worker)
		mine = self._request(self.a_worker)
		for doc in (theirs, mine):
			frappe.get_doc(doc.doctype, doc.name).submit()
		with self.assertRaises(frappe.PermissionError):
			self._cancel_as(self.h.hr, theirs)
		self.assertEqual(frappe.db.get_value(REQUEST, theirs.name, "docstatus"), 1)
		self._cancel_as(self.h.hr, mine)  # control
		self.assertEqual(frappe.db.get_value(REQUEST, mine.name, "docstatus"), 2)

	def test_update_after_submit_is_wired_and_scoped(self):
		events = frappe.get_hooks("doc_events")
		for doctype in ("Attendance", "Attendance Request"):
			self.assertIn("alvoraa_portal.attendance_doors.refuse_outside_company",
			              events[doctype]["before_update_after_submit"])
			self.assertIn("alvoraa_portal.attendance_doors.refuse_outside_company",
			              events[doctype]["before_cancel"])
		att = self._submitted_attendance(self.b_worker, self.h.other_company)
		frappe.set_user(self.h.hr)
		try:
			with self.assertRaises(frappe.PermissionError):
				doors.refuse_outside_company(att, "before_update_after_submit")
		finally:
			frappe.set_user("Administrator")


class HrDoesNotSubmitTheirOwnDraft(_Base):
	def test_sec2_an_hr_login_cannot_submit_a_draft_attendance_on_their_own_record(self):
		draft = frappe.get_doc({"doctype": "Attendance", "employee": self.h.hr_emp, "company": self.h.company,
		                        "attendance_date": add_days(nowdate(), -6), "status": "Present"}
		                       ).insert(ignore_permissions=True)  # made by someone else
		frappe.set_user(self.h.hr)
		try:
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Attendance", draft.name).submit()
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Attendance", draft.name, "docstatus"), 0)
		# control: a colleague's draft in the same company submits
		other = frappe.get_doc({"doctype": "Attendance", "employee": self.a_worker, "company": self.h.company,
		                        "attendance_date": add_days(nowdate(), -6), "status": "Present"}
		                       ).insert(ignore_permissions=True)
		frappe.set_user(self.h.hr)
		try:
			frappe.get_doc("Attendance", other.name).submit()
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Attendance", other.name, "docstatus"), 1)


class LeaveApprovalSubmitsAttendanceInTheApproversSession(_Base):
	"""S-2. Stock leave approval inserts and submits an Attendance as the approver,
	so the company scope applies to it."""

	def _leave(self, employee, approver):
		lt = "Hd085 LWP"
		if not frappe.db.exists("Leave Type", lt):
			frappe.get_doc({"doctype": "Leave Type", "leave_type_name": lt, "is_lwp": 1}).insert(
				ignore_permissions=True)
		day = add_days(nowdate(), -7)
		return frappe.get_doc({"doctype": "Leave Application", "employee": employee, "leave_type": lt,
		                       "from_date": day, "to_date": day, "status": "Approved",
		                       "leave_approver": approver, "posting_date": nowdate(),
		                       "company": frappe.db.get_value("Employee", employee, "company"),
		                       }).insert(ignore_permissions=True)

	def _approve(self, user, leave):
		frappe.set_user(user)
		try:
			frappe.get_doc("Leave Application", leave.name).submit()
		finally:
			frappe.set_user("Administrator")

	def test_an_in_scope_approver_still_approves(self):
		mine = self._leave(self.a_worker, self.h.hr)
		self._approve(self.h.hr, mine)
		self.assertEqual(frappe.db.get_value("Leave Application", mine.name, "docstatus"), 1)
		self.assertTrue(frappe.db.exists("Attendance", {"leave_application": mine.name, "docstatus": 1}))

	def test_r5_does_not_apply_to_the_attendance_a_leave_approval_writes(self):
		"""What really happens out of scope (proven by running, 20 Nov): stock
		`update_attendance` sets `ignore_validate` on the Attendance, and Frappe then
		skips every before_submit hook, R5 included. So the company scope here comes
		from the Leave Application's own permissions, not from R5. This test pins the
		behaviour so a change to it is noticed; it is not a statement that it is right."""
		theirs = self._leave(self.b_worker, self.h.hr)
		self._approve(self.h.hr, theirs)
		self.assertTrue(frappe.db.exists("Attendance", {"leave_application": theirs.name, "docstatus": 1}))


class SettingsSaveThroughTheApiDoor(_Base):
	"""F5: the SEC-6 gate holds on the REST/client save, and the change leaves a Version row (AC-54)."""

	def test_set_value_is_refused_for_a_stranger_and_versioned_for_the_hr_manager(self):
		from alvoraa_portal import held_day
		other = self.h._login("ohr5", ("HR Manager",))
		self.h._employee("Ohr5", other, company=self.h.other_company)
		frappe.set_user(other)
		try:
			with self.assertRaises(frappe.PermissionError):
				frappe.client.set_value("Company", self.h.company, held_day.LIMIT, 5)
		finally:
			frappe.set_user("Administrator")
		def versions():
			return len(frappe.get_all("Version", filters={"ref_doctype": "Company", "docname": self.h.company}))
		frappe.set_user(self.h.hr)  # the API door, allowed for the company's own HR Manager
		try:
			frappe.client.set_value("Company", self.h.company, held_day.LIMIT, 4)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Company", self.h.company, held_day.LIMIT), 4)
		# Frappe skips Version rows while testing unless asked, so ask (AC-54).
		before = versions()
		frappe.set_user(self.h.hr)
		try:
			doc = frappe.get_doc("Company", self.h.company)
			doc.update({held_day.LIMIT: 5})
			doc.save(ignore_version=False)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Company", self.h.company, held_day.LIMIT), 5)
		self.assertEqual(versions(), before + 1)
