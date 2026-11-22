"""Slice 088, part 1: the record of a printed notice, and the seam with 087.

**What this file proves, and what it does not.** It covers the data model and the join
with slice 087: the three record types exist with the permissions the spec states, the
record refuses to be typed, edited or deleted by hand, signing the register marks the
changed days, and a marked day stops holding the salary slip. The page itself, the HR
list and the photos are later parts of the slice and are not tested here - and are not
built here either, so nothing below passes by accident on code that does not exist.

Three habits the earlier slices paid for:

- the new behaviour is also tested from the OTHER side: not only "a signed change leaves
  the unconfirmed list" but "the same change, unsigned, is still on it". A test that only
  asserts the new state passes just as well when the gate is removed altogether.
- the controller refusals each have a control beside them proving the module's own write
  works, so "refused" never silently means "broken".
- `record_register_signature` is tested through the stored row, not through its return
  value. The return value is what the code believes; the row is what payroll will read.
"""

import frappe
from frappe.utils import now_datetime

from alvoraa_portal import punch_fix, register_notice
from alvoraa_portal.tests import test_punch_fix_087 as p87
from alvoraa_portal.tests.test_punch_fix_087 import PunchFixCase

NOTICE = "Alvoraa Register Notice"
REQUEST = "Attendance Request"


def setUpModule():
	"""087's fixture, plus 088's own column and record types."""
	p87.setUpModule()
	register_notice.after_migrate()
	frappe.clear_cache()


class RegisterNoticeCase(PunchFixCase):
	def notice(self, requests, pages=1, employee=None, month=None):
		"""A notice written the way the module writes one: under its own flag."""
		frappe.flags.in_register_notice = True
		try:
			doc = frappe.get_doc({
				"doctype": NOTICE,
				"employee": employee or self.emp,
				"month": month or frappe.utils.get_first_day(self.day),
				"printed_by": frappe.session.user,
				"printed_at": now_datetime(),
				"page_count": pages,
				"outcome": "Printed",
				"changes": [{"request": r, "page_no": 1,
				             "content_hash": "0" * 64} for r in requests],
			})
			doc.insert(ignore_permissions=True)
			return doc
		finally:
			frappe.flags.in_register_notice = False

	def held_on(self, day):
		"""Three punches on `day`, so the system holds it: nothing to pay against, which is
		the one case where HR may file a punch fix for somebody else."""
		from alvoraa_portal.tests import test_held_day_085 as hd

		for t, kind in (("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")):
			frappe.get_doc({"doctype": "Employee Checkin", "employee": self.emp,
			                "log_type": kind, "time": "%s %s:00" % (day, t)}
			               ).insert(ignore_permissions=True)
		att = frappe.get_doc({"doctype": "Attendance", "employee": self.emp,
		                      "company": self.h.company, "attendance_date": day,
		                      "status": "Present", "shift": hd.SHIFT,
		                      "in_time": "%s 09:00:00" % day})
		att.insert(ignore_permissions=True)
		att.submit()
		return att.name

	def an_approved_hr_change(self, time="18:30"):
		"""One approved, unconfirmed, HR-filed change: exactly what a notice is printed for.

		**Each call needs its own day, and that is not test plumbing.** HR may only file a
		punch fix for a day the system has HELD (three punches, nothing to pay against). The
		approval fixes the day, so the same day is ordinary afterwards and HR is refused on
		it - 087 working exactly as it should. So a test that wants two approved HR changes
		has to hold two days, which is also what really happens."""
		day = self.day if not getattr(self, "_days", None) else \
			frappe.utils.add_days(self.day, -len(self._days))
		self._days = (getattr(self, "_days", None) or []) + [day]
		self.held_on(day)
		name = self.fix(time=time, by=self.hr, day=day)  # HR files it
		self.decide(name, 1, by=self.h.hr2)  # a second HR person decides: nobody decides their own
		self.assertEqual(frappe.db.get_value(REQUEST, name, "alvoraa_needs_confirm"), 1,
		                 "fixture is wrong: the change does not need a confirm, so there is "
		                 "nothing for a notice to be about")
		return name


class TheRecordExists(RegisterNoticeCase):
	def test_the_three_record_types_are_installed(self):
		for dt in (NOTICE, "Alvoraa Register Notice Change", "Alvoraa Register Notice Page"):
			self.assertTrue(frappe.db.exists("DocType", dt), dt + " is not installed")
		meta = frappe.get_meta(NOTICE)
		for field in ("employee", "month", "printed_by", "printed_at", "page_count", "outcome",
		              "recorded_by", "recorded_on", "dispute_reason", "changes", "pages"):
			self.assertTrue(meta.get_field(field), "no field " + field)
		self.assertEqual(meta.get_field("changes").options, "Alvoraa Register Notice Change")
		self.assertEqual(meta.get_field("pages").options, "Alvoraa Register Notice Page")

	def test_the_signed_notice_column_is_on_the_request(self):
		self.assertTrue(frappe.db.has_column(REQUEST, punch_fix.SIGNED_NOTICE))
		self.assertTrue(punch_fix.signed_column_ready())
		self.assertTrue(register_notice.columns_ready())
		field = frappe.get_meta(REQUEST).get_field(punch_fix.SIGNED_NOTICE)
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, NOTICE)
		self.assertTrue(field.read_only, "a client must not be able to type a signature")

	def test_nobody_creates_exports_or_deletes_a_notice(self):
		"""Spec section 6, stated as a count: three roles read it and no role may do anything else."""
		perms = frappe.get_all("DocPerm", filters={"parent": NOTICE},
		                       fields=["role", "`read`", "`write`", "`create`", "`delete`",
		                               "report", "export"])
		self.assertEqual(sorted(p.role for p in perms),
		                 ["HR Manager", "HR User", "System Manager"])
		for p in perms:
			self.assertTrue(p.read, p.role + " cannot read")
			self.assertFalse(p.create, p.role + " can create a notice by hand")
			self.assertFalse(p.delete, p.role + " can delete a notice")
			self.assertFalse(p.report, p.role + " can report on notices")
			self.assertFalse(p.export, p.role + " can export notices")
			if p.role != "System Manager":
				self.assertFalse(p.write, p.role + " can edit a notice")

	def test_no_other_role_has_a_row_at_all(self):
		roles = {p.role for p in frappe.get_all("DocPerm", filters={"parent": NOTICE},
		                                        fields=["role"])}
		for outsider in ("Employee", "Employee Self Service", "All", "Biometric Sync"):
			self.assertNotIn(outsider, roles, outsider + " can see other people's notices")


class TheRecordRefusesToBeTyped(RegisterNoticeCase):
	def test_the_module_may_write_one_and_a_person_may_not(self):
		"""The control first: the module's own write works."""
		doc = self.notice([self.an_approved_hr_change()])
		self.assertTrue(doc.name.startswith("RN-"), doc.name)
		self.assertEqual(doc.outcome, "Printed")
		self.assertEqual(len(doc.changes), 1)
		# Now the same thing by hand, with no flag.
		self.refused(lambda: frappe.get_doc({
			"doctype": NOTICE, "employee": self.emp,
			"month": frappe.utils.get_first_day(self.day),
			"printed_by": "Administrator", "printed_at": now_datetime(),
			"page_count": 1, "outcome": "Printed",
			"changes": [{"request": self.an_approved_hr_change("19:30"), "page_no": 1,
			             "content_hash": "0" * 64}],
		}).insert(ignore_permissions=True), "created by printing it")

	def test_what_was_printed_cannot_be_edited_afterwards(self):
		doc = self.notice([self.an_approved_hr_change()])
		doc.reload()
		doc.page_count = 9
		self.refused(lambda: doc.save(ignore_permissions=True), "cannot be changed")
		doc.reload()
		doc.changes[0].page_no = 7
		self.refused(lambda: doc.save(ignore_permissions=True), "cannot be changed")
		self.assertEqual(frappe.db.get_value(NOTICE, doc.name, "page_count"), 1)

	def test_an_answer_cannot_be_rewritten_once_it_is_recorded(self):
		doc = self.notice([self.an_approved_hr_change()])
		frappe.flags.in_register_notice = True
		try:
			doc.outcome, doc.recorded_by, doc.recorded_on = "Signed", "Administrator", now_datetime()
			doc.save(ignore_permissions=True)
		finally:
			frappe.flags.in_register_notice = False
		doc.reload()
		doc.outcome = "Not right"
		self.refused(lambda: doc.save(ignore_permissions=True), "already been answered")
		self.assertEqual(frappe.db.get_value(NOTICE, doc.name, "outcome"), "Signed")

	def test_a_notice_is_never_deleted_by_anyone(self):
		doc = self.notice([self.an_approved_hr_change()])
		self.refused(lambda: frappe.delete_doc(NOTICE, doc.name, force=True,
		                                       ignore_permissions=True), "cannot be deleted")
		self.assertTrue(frappe.db.exists(NOTICE, doc.name),
		                "the record of what the employee was shown is gone")


class TheSeamWith087(RegisterNoticeCase):
	def test_signing_marks_the_changed_day_and_the_row_says_so(self):
		name = self.an_approved_hr_change()
		doc = self.notice([name])
		marked = punch_fix.record_register_signature([name], doc.name)
		self.assertEqual(marked, [name])
		self.assertEqual(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE), doc.name,
		                 "the stored row does not carry the notice")

	def test_an_unsigned_change_still_holds_the_slip_and_a_signed_one_does_not(self):
		"""Both directions. Without the first assertion the second proves nothing:
		removing the gate entirely would also make the list empty."""
		name = self.an_approved_hr_change()
		before = punch_fix.unconfirmed_changes([self.emp], self.day, self.day)
		self.assertEqual([r["name"] for r in before], [name],
		                 "fixture is wrong: the change was not holding the slip to begin with")
		doc = self.notice([name])
		punch_fix.record_register_signature([name], doc.name)
		after = punch_fix.unconfirmed_changes([self.emp], self.day, self.day)
		self.assertEqual([r["name"] for r in after], [],
		                 "a change signed on the register is still holding the salary slip")

	def test_a_change_the_employee_already_confirmed_in_the_app_is_left_alone(self):
		name = self.an_approved_hr_change()
		self.confirm_as_employee(name)
		doc = self.notice([name])
		self.assertEqual(punch_fix.record_register_signature([name], doc.name), [])
		self.assertFalse(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE),
		                 "a confirm in the app was overwritten by a paper signature")

	def test_an_undone_or_declined_change_is_left_alone(self):
		undone = self.an_approved_hr_change("18:30")
		frappe.db.set_value(REQUEST, undone, "alvoraa_undone_on", now_datetime())
		declined = self.an_approved_hr_change("19:30")
		frappe.db.set_value(REQUEST, declined, "alvoraa_review_status", "Declined")
		doc = self.notice([undone, declined])
		self.assertEqual(punch_fix.record_register_signature([undone, declined], doc.name), [])
		for name in (undone, declined):
			self.assertFalse(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE))

	def test_signing_twice_marks_nothing_the_second_time(self):
		name = self.an_approved_hr_change()
		first = self.notice([name])
		second = self.notice([name])
		self.assertEqual(punch_fix.record_register_signature([name], first.name), [name])
		self.assertEqual(punch_fix.record_register_signature([name], second.name), [],
		                 "a reprint re-signed a day that was already signed")
		self.assertEqual(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE), first.name,
		                 "the second page took the first page's signature")

	def test_a_notice_that_does_not_exist_is_refused(self):
		name = self.an_approved_hr_change()
		self.refused(lambda: punch_fix.record_register_signature([name], "RN-99999"),
		             "does not exist")
		self.refused(lambda: punch_fix.record_register_signature([name], None),
		             "does not exist")
		self.assertFalse(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE))

	def test_a_client_cannot_sign_its_own_change(self):
		"""Two walls, and the first run of this test found the second one.

		On an APPROVED request Frappe itself refuses the field outright, because it is not
		`allow_on_submit` - the same as 087's confirm fields, and the reason both are written
		with `db.set_value` rather than a save. On a request still WAITING there is no such
		wall, so `_own_the_confirm_fields` puts the stored value back and the client's value
		is silently dropped. Tested both ways round, because either on its own would let the
		other regress unnoticed."""
		name = self.an_approved_hr_change()
		doc = self.notice([name])

		approved = frappe.get_doc(REQUEST, name)
		approved.set(punch_fix.SIGNED_NOTICE, doc.name)
		self.refused(lambda: approved.save(ignore_permissions=True), "after submission")
		self.assertFalse(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE))

		waiting = self.fix(time="09:30", by=self.emp_user, day=self.day)
		req = frappe.get_doc(REQUEST, waiting)
		req.set(punch_fix.SIGNED_NOTICE, doc.name)
		req.save(ignore_permissions=True)
		self.assertFalse(frappe.db.get_value(REQUEST, waiting, punch_fix.SIGNED_NOTICE),
		                 "a client signed its own waiting change by sending the field")

		# And the module's own write still works on the approved one.
		punch_fix.record_register_signature([name], doc.name)
		self.assertEqual(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE), doc.name)

	def test_a_new_request_never_arrives_already_signed(self):
		doc = self.notice([self.an_approved_hr_change()])
		frappe.set_user(self.emp_user)
		try:
			req = frappe.get_doc({"doctype": REQUEST, "employee": self.emp,
			                      "from_date": self.day, "to_date": self.day,
			                      "reason": "Forgot to Punch In", "alvoraa_missing_time": "19:45",
			                      "alvoraa_review_status": "Waiting"})
			req.set(punch_fix.SIGNED_NOTICE, doc.name)
			req.insert(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value(REQUEST, req.name, punch_fix.SIGNED_NOTICE),
		                 "a request was created pre-signed")

	def test_the_signature_is_written_to_the_security_log(self):
		from alvoraa_portal.tests.test_punch_fix_087 import security_lines_from_a_fresh_process

		name = self.an_approved_hr_change()
		doc = self.notice([name])
		lines = security_lines_from_a_fresh_process(
			lambda: punch_fix.record_register_signature([name], doc.name))
		self.assertTrue(any("register signature" in l and doc.name in l for l in lines),
		                "no security line for a recorded signature: " + repr(lines))
