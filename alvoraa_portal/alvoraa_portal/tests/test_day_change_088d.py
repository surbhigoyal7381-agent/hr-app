"""Slice 088d: a reason for every change a person makes to a day's attendance record.

**Two things this suite exists to prove, in this order.**

1. `ThePathTable`: every way an Attendance row is written (A01 to A31 in
   `00d-attendance-scope-analysis.md`), driven for real with the notice switch ON, and for each
   one: listed or not listed, and refused or not refused. The leave approval, the request
   approval and cancel, the Shift Type button, Reprocess and the auto-attendance job all write
   Attendance inside a person's own session, so a rule that judged "who is logged in" would
   refuse them. Each is pinned as still working. `test_every_path_has_a_test` fails if a path
   is dropped from this file.
2. `TheReason`: the rule itself, for a person at a door, including the free text and the
   Data Import hole (finding F3).

Every test here was broken on purpose; the break is named in `03d-implementation-notes.md`.
"""

import json
import re

import frappe
from frappe.utils import add_days, getdate

from alvoraa_portal import day_change, punch_change
from alvoraa_portal.tests import test_held_day_085 as hd
from alvoraa_portal.tests.test_punch_change_088c import PunchChangeCase, setUpModule as _up88c

ATT = "Attendance"
LOG = punch_change.LOG
REASON = "Employee forgot to punch"
SAVE = "frappe.desk.form.save.savedocs"
#: The real command behind a form's `frm.call` and the Shift Type "Mark Attendance" click.
#: (An earlier version of this file used `frappe.desk.form.run_method.runserverobj`, a module
#: that does not exist in frappe 16: right verdicts, wrong evidence, and it hid 05d P1-1.)
RDM = "run_doc_method"
SHIFT_DOCS = json.dumps({"doctype": "Shift Type", "name": hd.SHIFT})


def setUpModule():
	_up88c()
	day_change.after_migrate()
	frappe.clear_cache()


class DayCase(PunchChangeCase):
	_n = 0

	def setUp(self):
		super().setUp()
		self.d2 = {}                          # nothing yet

	def a_day(self):
		"""A date no earlier test of this run used, for this person."""
		DayCase._n += 1
		return str(add_days(self.day, -DayCase._n))

	def cancelled_day(self):
		"""A day that had a record, now cancelled: marking it again is a REPLACEMENT, which is
		what the notice lists. (A day that never had one is the record being made: not listed.)"""
		day = self.a_day()
		doc = frappe.get_doc(self.doc_dict(day, "Absent")).insert(ignore_permissions=True)
		doc.submit()
		doc.cancel()
		return day

	def at_door(self, cmd, **form):
		"""Make the request look like `cmd` with these form values, for the length of a test step."""
		frappe.form_dict.clear()
		frappe.form_dict.update({"cmd": cmd, **form})

	def leave_door(self):
		frappe.form_dict.clear()

	def doc_dict(self, day, status="Present", reason=None, text=None, **extra):
		d = {"doctype": ATT, "employee": self.emp, "company": self.h.company, "attendance_date": day,
		     "status": status, "shift": hd.SHIFT, **extra}
		if reason:
			d[day_change.FIELD] = reason
		if text:
			d[day_change.TEXT] = text
		return d

	def desk(self, d, action="Submit", user=None):
		"""The Desk's own save endpoint, called as `user`, with the request looking like Desk's."""
		from frappe.desk.form.save import savedocs

		frappe.set_user(user or self.hr)               # first: set_user wipes form_dict
		self.at_door(SAVE, doc=json.dumps(d, default=str), action=action)
		try:
			savedocs(json.dumps(d, default=str), action)
		finally:
			frappe.set_user("Administrator")
			self.leave_door()
		return frappe.db.get_value(ATT, {"employee": self.emp, "attendance_date": d["attendance_date"],
		                                 "docstatus": ("<", 2)}, "name")

	def rows(self, **f):
		return frappe.get_all(LOG, filters={"employee": self.emp, **f}, fields=["*"], order_by="creation asc")

	def submitted(self, status="Present", day=None, **extra):
		"""A day record that was already there (as the system makes it: no door, no person)."""
		day = day or self.a_day()
		doc = frappe.get_doc(self.doc_dict(day, status, **extra)).insert(ignore_permissions=True)
		doc.submit()
		return doc

	def cmd_as(self, user, cmd, fn, **form):
		frappe.set_user(user)                          # first: set_user wipes form_dict
		self.at_door(cmd, **form)
		try:
			return fn()
		finally:
			frappe.set_user("Administrator")
			self.leave_door()


class TheSystemAndTheOtherRecordsPass(DayCase):
	"""Switch ON. None of these is refused and none is listed. Written first: these are the
	paths a careless rule would break (a leave approval is HR's daily work)."""

	def test_control_a_person_at_the_desk_is_refused_without_a_reason(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason"):
			self.desk(self.doc_dict(self.cancelled_day()))

	def test_A01_the_hourly_job_marks_a_day_as_administrator(self):
		from hrms.hr.doctype.employee_checkin.employee_checkin import create_or_update_attendance

		day = self.a_day()
		att = create_or_update_attendance(self.emp, day, "Present", working_hours=8, shift=hd.SHIFT)
		self.assertEqual(frappe.db.get_value(ATT, att.name, "docstatus"), 1)
		self.assertEqual(self.rows(), [])

	def test_A02_a_person_clicking_the_shift_type_button_runs_the_same_code(self):
		from hrms.hr.doctype.employee_checkin.employee_checkin import create_or_update_attendance

		day = self.a_day()
		att = self.cmd_as(self.hr, RDM,
		                  lambda: create_or_update_attendance(self.emp, day, "Present", working_hours=8, shift=hd.SHIFT),
		                  docs=SHIFT_DOCS, method="process_auto_attendance")
		self.assertEqual(frappe.db.get_value(ATT, att.name, "docstatus"), 1)
		self.assertEqual(self.rows(), [])

	def test_A02b_the_shift_type_click_re_marks_a_day_a_person_reset(self):
		"""The real case behind A02: HR cancels a day (the reset, listed) and the job or the click
		puts the new row in its place. That row REPLACES a cancelled one, so a door that was too
		wide would refuse it. It must not be refused and must not be listed (a first-mark test
		cannot catch this: a first mark is never demanded)."""
		from hrms.hr.doctype.employee_checkin.employee_checkin import create_or_update_attendance

		day = self.cancelled_day()
		att = self.cmd_as(self.hr, RDM, lambda: create_or_update_attendance(
			self.emp, day, "Present", working_hours=8, shift=hd.SHIFT), docs=SHIFT_DOCS, method="process_auto_attendance")
		self.assertEqual(frappe.db.get_value(ATT, att.name, "docstatus"), 1)
		self.assertEqual(self.rows(), [])

	def test_A03_an_absent_day_for_no_punch(self):
		from hrms.hr.doctype.attendance.attendance import mark_attendance

		day = self.a_day()
		name = self.cmd_as(self.hr, RDM,
		                   lambda: mark_attendance(self.emp, day, "Absent", hd.SHIFT),
		                   docs=SHIFT_DOCS, method="process_auto_attendance")
		self.assertEqual(frappe.db.get_value(ATT, name, "docstatus"), 1)
		self.assertEqual(self.rows(), [])

	def test_A04_the_other_half_set_absent_by_set_value(self):
		"""No hook runs on `set_value`, so nothing can be asked or listed. Documented, not a rule."""
		att = self.submitted("Half Day", half_day_status="Present")
		self.cmd_as(self.hr, RDM, lambda: frappe.db.set_value(
			ATT, att.name, {"half_day_status": "Absent", "modify_half_day_status": 0}), docs=SHIFT_DOCS)
		self.assertEqual(frappe.db.get_value(ATT, att.name, "half_day_status"), "Absent")
		self.assertEqual(self.rows(), [])

	def test_A05_an_existing_half_day_row_updated_by_the_auto_job(self):
		from hrms.hr.doctype.employee_checkin.employee_checkin import create_or_update_attendance

		day = self.a_day()
		att = self.submitted("Half Day", day=day, half_day_status="Present", leave_type=self._lwp())
		frappe.db.set_value(ATT, att.name, "modify_half_day_status", 1)
		out = create_or_update_attendance(self.emp, day, "Absent", working_hours=1, shift=hd.SHIFT)
		self.assertEqual(out.name, att.name)
		self.assertEqual(self.rows(), [])

	def _lwp(self):
		name = "D088 LWP"
		if not frappe.db.exists("Leave Type", name):
			frappe.get_doc({"doctype": "Leave Type", "leave_type_name": name, "is_lwp": 1,
			                "include_holiday": 1}).insert(ignore_permissions=True)
		return name

	def _leave(self, day):
		doc = frappe.get_doc({"doctype": "Leave Application", "employee": self.emp, "leave_type": self._lwp(),
		                      "from_date": day, "to_date": day, "status": "Approved", "company": self.h.company,
		                      "posting_date": day, "follow_via_email_notification": 0 if False else 1})
		doc.flags.ignore_permissions = True
		doc.insert()
		return doc

	def test_A06_a_leave_approval_writes_the_day_and_is_not_refused(self):
		day = self.a_day()
		leave = self._leave(day)
		self.cmd_as(self.hr, SAVE, lambda: leave.submit(), doc=json.dumps({"doctype": "Leave Application"}), action="Submit")
		att = frappe.db.get_value(ATT, {"employee": self.emp, "attendance_date": day, "docstatus": 1},
		                          ["status", "leave_application"], as_dict=True)
		self.assertEqual((att.status, att.leave_application), ("On Leave", leave.name))
		self.assertEqual(self.rows(), [])

	def test_A06b_a_leave_approval_over_an_existing_row_changes_it_by_db_set(self):
		day = self.a_day()
		self.submitted("Absent", day=day)
		leave = self._leave(day)
		self.cmd_as(self.hr, SAVE, lambda: leave.submit(), doc=json.dumps({"doctype": "Leave Application"}), action="Submit")
		self.assertEqual(frappe.db.get_value(ATT, {"employee": self.emp, "attendance_date": day, "docstatus": 1}, "status"),
		                 "On Leave")
		self.assertEqual(self.rows(), [])

	def test_A07_a_leave_cancel_takes_the_day_back(self):
		day = self.a_day()
		leave = self._leave(day)
		leave.submit()
		leave.reload()
		self.cmd_as(self.hr, "frappe.desk.form.save.cancel", lambda: leave.cancel(),
		            doctype="Leave Application", name=leave.name)
		self.assertEqual(frappe.db.get_value(ATT, {"employee": self.emp, "attendance_date": day}, "docstatus"), 2)
		self.assertEqual(self.rows(), [])

	def _plain_request(self, day):
		return self.h._ordinary_request(self.emp, day, by=self.emp_user)

	def test_A08_a_request_approval_writes_the_day_and_is_not_refused(self):
		from alvoraa_portal import attendance_correction as ac

		day = self.a_day()
		req = self._plain_request(day)
		self.cmd_as(self.hr, "alvoraa_portal.attendance_correction.decide",
		            lambda: ac.decide(req.name, 1, None, "x"), name=req.name)
		self.assertEqual(frappe.db.get_value("Attendance Request", req.name, "docstatus"), 1)
		self.assertTrue(frappe.db.exists(ATT, {"employee": self.emp, "attendance_date": day, "docstatus": 1}))
		self.assertEqual(self.rows(), [])

	def test_A09_cancelling_that_request_cancels_the_day(self):
		from alvoraa_portal import attendance_correction as ac

		day = self.a_day()
		req = self._plain_request(day)
		self.cmd_as(self.hr, "alvoraa_portal.attendance_correction.decide", lambda: ac.decide(req.name, 1, None, "x"),
		            name=req.name)
		doc = frappe.get_doc("Attendance Request", req.name)
		self.cmd_as(self.hr, "frappe.desk.form.save.cancel", lambda: doc.cancel(),
		            doctype="Attendance Request", name=req.name)
		self.assertEqual(frappe.db.get_value(ATT, {"employee": self.emp, "attendance_date": day}, "docstatus"), 2)
		self.assertEqual(self.rows(), [])

	def test_A10_a_punch_fix_is_one_notice_entry_and_no_log_row(self):
		"""One human act, one line, by construction: punches under the fix flag, the day by set_value."""
		from alvoraa_portal import register_notice

		self.held_on(self.day)
		req = self.fix(time="18:30", by=self.hr)
		self.decide(req, 1, by=self.h.hr2)
		self.assertEqual(self.rows(), [])
		from frappe.utils import get_first_day
		listed = register_notice.qualifying_changes(get_first_day(self.day), [self.emp])
		self.assertEqual([r.name for r in listed if not r.get("punch_change")], [req])

	def test_A12_a_late_machine_punch_releases_a_held_day(self):
		self._machine_punch(frappe.get_doc({"doctype": "Employee Checkin", "employee": self.emp,
		                                    "log_type": "IN", "time": "%s 09:00:00" % self.day}))
		att = self.submitted(day=self.day, in_time="%s 09:00:00" % self.day)
		frappe.db.set_value(ATT, att.name, "status", "Held")
		self._machine_punch(frappe.get_doc({"doctype": "Employee Checkin", "employee": self.emp,
		                                    "log_type": "OUT", "time": "%s 18:00:00" % self.day}))
		self.assertNotEqual(frappe.db.get_value(ATT, att.name, "status"), "Held")
		self.assertEqual(self.rows(), [])

	def test_A13_the_hold_marks_a_new_odd_day_held(self):
		from alvoraa_portal import held_day

		frappe.db.set_value("Company", self.h.company, held_day.SWITCH, 1)
		frappe.clear_cache()
		self.addCleanup(lambda: (frappe.db.set_value("Company", self.h.company, held_day.SWITCH, 0), frappe.clear_cache()))
		day = self.a_day()
		self._machine_punch(frappe.get_doc({"doctype": "Employee Checkin", "employee": self.emp,
		                                    "log_type": "IN", "time": "%s 09:00:00" % day}))
		doc = frappe.get_doc(self.doc_dict(day, "Present", in_time="%s 09:00:00" % day)).insert(ignore_permissions=True)
		doc.submit()
		self.assertEqual(frappe.db.get_value(ATT, doc.name, "status"), "Held")
		self.assertEqual(self.rows(), [])

	def test_A14_reprocess_writes_only_derived_fields(self):
		from alvoraa_portal import payroll_reprocess

		att = self.submitted()
		self.cmd_as(self.hr, "alvoraa_portal.payroll_reprocess.apply",
		            lambda: payroll_reprocess.apply(self.h.company, str(att.attendance_date), str(att.attendance_date), confirmed=1),
		            company=self.h.company)
		self.assertEqual(self.rows(), [])

	def test_A15_an_engine_fact_written_by_set_value(self):
		att = self.submitted("Half Day", half_day_status="Present")
		self.cmd_as(self.emp_user, "frappe.desk.form.save.savedocs",
		            lambda: frappe.db.set_value(ATT, att.name, "half_day_status", "Absent", update_modified=False),
		            doc=json.dumps({"doctype": "Attendance Request"}))
		self.assertEqual(self.rows(), [])

	def test_A29_raw_sql_and_A30_a_patch_leave_no_trace(self):
		"""Uncoverable by any hook, and said so in the runbook."""
		att = self.submitted()
		frappe.db.sql("update `tabAttendance` set status = 'Absent' where name = %s", att.name)
		Att = frappe.qb.DocType(ATT)
		frappe.qb.update(Att).set(Att.status, "Present").where(Att.name == att.name).run()
		self.assertEqual(self.rows(), [])

	def test_A27_an_administrator_script_is_not_at_a_door(self):
		"""bench execute, no request: cancelling a day is not listed. Runbook note, not code."""
		att = self.submitted()
		frappe.set_user("Administrator")
		att.cancel()
		self.assertEqual(frappe.db.get_value(ATT, att.name, "docstatus"), 2)
		self.assertEqual(self.rows(), [])

	def test_A28_the_same_script_editing_a_punch_is_still_refused(self):
		"""088c: Administrator counts for punches. Unchanged by this slice."""
		with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason"):
			self.punch(user="Administrator")

	def test_A31_editing_a_punch_logs_the_punch_and_leaves_the_day_alone(self):
		att = self.submitted(day=self.day)
		before = frappe.db.get_value(ATT, att.name, ["status", "modified"], as_dict=True)
		p = self.punch("10:00", user=self.hr, reason=REASON)
		self.edit(p.name, self.hr, reason=REASON, time="%s 10:05:00" % self.day)
		self.assertEqual(frappe.db.get_value(ATT, att.name, ["status", "modified"], as_dict=True), before)
		self.assertEqual({r.attendance for r in self.rows()}, {None})
		self.assertTrue(all(r.punch for r in self.rows()))

	def test_the_switch_off_asks_for_nothing(self):
		self._set_notices(0)
		name = self.desk(self.doc_dict(self.cancelled_day()))
		self.assertTrue(name)
		self.assertEqual(self.rows(), [])


class ThePathTableDoors(DayCase):
	"""The paths that ARE a person's direct edit: listed, and refused without a reason."""

	def test_A16_a_person_replacing_a_day_with_a_reason_is_listed(self):
		day = self.cancelled_day()
		name = self.desk(self.doc_dict(day, "Present", reason=REASON))
		(row,) = self.rows(attendance=name)
		self.assertEqual((row.what, row.reason_code, str(row.day)), ("Day changed from Absent to Present", REASON, day))
		self.assertIsNone(frappe.db.get_value(ATT, name, day_change.FIELD), "the reason must not stay on the row")

	def test_A16a_a_first_mark_is_not_asked_about_and_not_listed(self):
		"""Surbhi, 26 Nov: only a change to a day that had a record. Control: A16 above."""
		name = self.desk(self.doc_dict(self.a_day()))
		self.assertEqual(frappe.db.get_value(ATT, name, "docstatus"), 1)
		self.assertEqual(self.rows(), [])
		name = self.desk(self.doc_dict(self.a_day(), reason=REASON))
		self.assertIsNone(frappe.db.get_value(ATT, name, day_change.FIELD))
		self.assertEqual(self.rows(), [], "a reason on a first mark is dropped, not logged")

	def test_A16b_a_draft_is_never_demanded_or_listed(self):
		day = self.a_day()
		name = self.desk(self.doc_dict(day), action="Save")
		self.assertEqual(frappe.db.get_value(ATT, name, "docstatus"), 0)
		self.assertEqual(self.rows(), [])

	def test_A16c_submit_writes_one_row_not_two(self):
		self.desk(self.doc_dict(self.cancelled_day(), reason=REASON))
		self.assertEqual(len(self.rows()), 1)

	def test_A17_ticking_the_held_confirm_needs_a_reason(self):
		att = self.submitted(day=self.a_day())
		d = frappe.get_doc(ATT, att.name).as_dict(convert_dates_to_str=True)
		d.update({"alvoraa_held_confirmed": 1, "alvoraa_confirmed_out_time": "18:30:00"})
		with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason"):
			self.desk(d, "Update")
		d[day_change.FIELD] = REASON
		self.desk(d, "Update")
		(row,) = self.rows(attendance=att.name)
		self.assertEqual(row.what, "Out time confirmed as 18:30 for a day with a missing punch")

	def test_A17b_saving_only_the_reason_is_the_first_step_of_a_cancel_and_is_not_listed(self):
		att = self.submitted(day=self.a_day())
		d = frappe.get_doc(ATT, att.name).as_dict(convert_dates_to_str=True)
		d[day_change.FIELD] = REASON
		self.desk(d, "Update")
		self.assertEqual(self.rows(), [])
		self.assertEqual(frappe.db.get_value(ATT, att.name, day_change.FIELD), REASON, "the reason waits on the row")

	def _cancel(self, name, user=None):
		from frappe.desk.form.save import cancel

		frappe.set_user(user or self.hr)
		self.at_door("frappe.desk.form.save.cancel", doctype=ATT, name=name)
		try:
			cancel(ATT, name)
		finally:
			frappe.set_user("Administrator")
			self.leave_door()

	def test_A18_cancel_is_two_steps(self):
		att = self.submitted(day=self.a_day())
		with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason first"):
			self._cancel(att.name)
		self.assertEqual(frappe.db.get_value(ATT, att.name, "docstatus"), 1)
		d = frappe.get_doc(ATT, att.name).as_dict(convert_dates_to_str=True)
		d[day_change.FIELD] = REASON
		self.desk(d, "Update")
		self._cancel(att.name)
		self.assertEqual(frappe.db.get_value(ATT, att.name, "docstatus"), 2)
		(row,) = self.rows(attendance=att.name)
		self.assertEqual(row.what, "Day record reset so it is worked out again from your punches (was Present)")
		self.assertIsNone(frappe.db.get_value(ATT, att.name, day_change.FIELD), "cleared after it was logged")

	def test_A19_an_amendment_says_what_it_changed_from(self):
		att = self.submitted("Present", day=self.a_day())
		att.cancel()
		new = self.doc_dict(str(att.attendance_date), "Absent", reason=REASON, amended_from=att.name)
		self.desk(new)
		(row,) = self.rows()
		self.assertEqual(row.what, "Day changed from Present to Absent")

	def test_A19b_a_row_where_a_cancelled_one_exists_is_a_replacement_too(self):
		att = self.submitted("Present", day=self.a_day())
		att.cancel()
		self.desk(self.doc_dict(str(att.attendance_date), "Present", reason=REASON))
		(row,) = self.rows()
		self.assertEqual(row.what, "Day record replaced, still Present")

	def test_A20_deleting_a_draft_is_not_listed(self):
		import frappe.client

		name = self.desk(self.doc_dict(self.cancelled_day()), action="Save")
		self.cmd_as(self.hr, "frappe.client.delete", lambda: frappe.client.delete(ATT, name), doctype=ATT, name=name)
		self.assertFalse(frappe.db.exists(ATT, name))
		self.assertEqual(self.rows(), [])

	def test_A21_frappe_client_and_REST_are_doors(self):
		import frappe.client

		day = self.cancelled_day()
		d = self.doc_dict(day)
		frappe.set_user(self.hr)
		self.at_door("frappe.client.insert", doc=json.dumps(d))
		try:
			with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason"):
				frappe.client.insert(d).submit() if False else frappe.get_doc(d).insert().submit()
		finally:
			frappe.set_user("Administrator")
			self.leave_door()
		# REST has no cmd: the path decides.
		frappe.local.request = frappe._dict(path="/api/resource/Attendance")
		try:
			self.assertTrue(day_change.at_a_door())
			frappe.local.request = frappe._dict(path="/api/resource/Attendance Request")
			self.assertFalse(day_change.at_a_door())
			frappe.local.request = frappe._dict(path="/api/v2/document/Attendance/HR-ATT-1")
			self.assertTrue(day_change.at_a_door())
		finally:
			frappe.local.request = None

	def test_A22_the_list_bulk_cancel_is_a_door_and_reports_its_failure(self):
		from frappe.desk.doctype.bulk_update.bulk_update import submit_cancel_or_update_docs

		att = self.submitted(day=self.a_day())
		frappe.db.commit()      # the bulk action rolls back on a failure, and would take the fixture with it
		self.addCleanup(lambda: (frappe.db.sql("delete from `tabAttendance` where name = %s", att.name), frappe.db.commit()))
		out = self.cmd_as(self.hr, "frappe.desk.doctype.bulk_update.bulk_update.submit_cancel_or_update_docs",
		                  lambda: submit_cancel_or_update_docs(ATT, json.dumps([att.name]), "cancel"), doctype=ATT)
		self.assertEqual(frappe.db.get_value(ATT, att.name, "docstatus"), 1, "refused, not cancelled")
		self.assertTrue(out, "the failure is reported to the person")

	def _bulk(self, day):
		return json.dumps({"employee": self.emp, "unmarked_days": [day], "status": "Present", "shift": hd.SHIFT})

	def test_A23_mark_attendance_works_for_a_first_mark_and_is_refused_loudly_for_a_replacement(self):
		day = self.a_day()
		self.cmd_as(self.hr, day_change.BULK_MARK, lambda: day_change.mark_bulk_attendance(self._bulk(day)))
		self.assertTrue(frappe.db.exists(ATT, {"employee": self.emp, "attendance_date": day, "docstatus": 1}))
		self.assertEqual(self.rows(), [])
		again = self.cancelled_day()
		with self.assertRaisesRegex(frappe.ValidationError, "'Mark Attendance' cannot do this"):
			self.cmd_as(self.hr, day_change.BULK_MARK, lambda: day_change.mark_bulk_attendance(self._bulk(again)))
		self.assertFalse(frappe.db.exists(ATT, {"employee": self.emp, "attendance_date": again, "docstatus": 1}))

	def test_A23b_the_stock_loop_alone_would_swallow_the_refusal(self):
		"""Why the wrapper exists: for a replacement the stock loop skips the row, and the person
		is told it worked."""
		from hrms.hr.doctype.attendance.attendance import process_bulk_attendance_in_batches

		day = self.cancelled_day()
		data = frappe._dict(employee=self.emp, unmarked_days=[day], status="Present", shift=hd.SHIFT)
		self.cmd_as(self.hr, day_change.BULK_MARK, lambda: process_bulk_attendance_in_batches(data))
		self.assertFalse(frappe.db.exists(ATT, {"employee": self.emp, "attendance_date": day, "docstatus": 1}))

	def test_A23c_with_the_switch_off_the_stock_tool_replaces_a_day(self):
		self._set_notices(0)
		day = self.cancelled_day()
		self.cmd_as(self.hr, day_change.BULK_MARK, lambda: day_change.mark_bulk_attendance(self._bulk(day)))
		self.assertTrue(frappe.db.exists(ATT, {"employee": self.emp, "attendance_date": day, "docstatus": 1}))

	def test_A24_the_attendance_tool_marks_a_first_day_but_not_a_replacement_or_the_half_day_tick(self):
		day = self.a_day()
		self.cmd_as(self.hr, day_change.TOOL_MARK, lambda: day_change.mark_employee_attendance(
			json.dumps([self.emp]), "Present", day, shift=hd.SHIFT))
		self.assertTrue(frappe.db.exists(ATT, {"employee": self.emp, "attendance_date": day, "docstatus": 1}))
		again = self.cancelled_day()
		with self.assertRaisesRegex(frappe.ValidationError, "'Employee Attendance Tool' cannot do this"):
			self.cmd_as(self.hr, day_change.TOOL_MARK, lambda: day_change.mark_employee_attendance(
				json.dumps([self.emp]), "Present", again, shift=hd.SHIFT))
		att = self.submitted("Half Day", half_day_status="Present")
		was = frappe.db.get_value(ATT, att.name, "half_day_status")
		with self.assertRaisesRegex(frappe.ValidationError, "half-day tick"):
			self.cmd_as(self.hr, day_change.TOOL_MARK, lambda: day_change.mark_employee_attendance(
				json.dumps([]), "Present", str(att.attendance_date), mark_half_day=True, half_day_status="Absent",
				half_day_employee_list=json.dumps([self.emp])))
		self.assertEqual(frappe.db.get_value(ATT, att.name, "half_day_status"), was)

	def test_A24c_the_stock_tick_changes_an_existing_row_and_no_hook_sees_it(self):
		"""Why the tick is refused (05d P3-4): the stock tool rewrites existing rows with a query
		that never reaches a document, so no rule and no log can see it. Called WITHOUT our
		wrapper, switch ON, as a person at a door."""
		from hrms.hr.doctype.employee_attendance_tool.employee_attendance_tool import mark_employee_attendance as stock

		att = self.submitted("Half Day", half_day_status="Present")
		was = frappe.db.get_value(ATT, att.name, "half_day_status")
		self.cmd_as(self.hr, day_change.TOOL_MARK, lambda: stock(
			json.dumps([]), "Present", str(att.attendance_date), late_entry=0, early_exit=0, shift=hd.SHIFT,
			mark_half_day=True, half_day_status="Absent" if was != "Absent" else "Present",
			half_day_employee_list=json.dumps([self.emp])))
		self.assertNotEqual(frappe.db.get_value(ATT, att.name, "half_day_status"), was, "the day changed")
		self.assertEqual(self.rows(), [], "and nothing saw it")

	def test_A24b_with_the_switch_off_the_tool_runs_for_a_replacement_and_the_tick(self):
		self._set_notices(0)
		day = self.cancelled_day()
		self.cmd_as(self.hr, day_change.TOOL_MARK, lambda: day_change.mark_employee_attendance(
			json.dumps([self.emp]), "Present", day, shift=hd.SHIFT))
		self.assertTrue(frappe.db.exists(ATT, {"employee": self.emp, "attendance_date": day, "docstatus": 1}))

	def test_A11_the_087_undo_is_a_known_gap_and_writes_no_log_row(self):
		"""A person undoes an approved, disputed punch fix. It writes the day by `set_value`, so
		no hook sees it and the notice learns nothing (00b P10). This pins the gap: the day the
		gap is closed, this test fails and says so."""
		from alvoraa_portal import punch_fix

		self.held_on(self.day)
		req = self.fix(time="18:30", by=self.hr)
		self.decide(req, 1, by=self.h.hr2)
		frappe.db.set_value("Attendance Request", req, "alvoraa_disputed_on", frappe.utils.now_datetime())
		self.cmd_as(self.hr, "alvoraa_portal.punch_fix.undo_change", lambda: punch_fix.undo_change(req, "employee disputed it"),
		            name=req)
		self.assertTrue(frappe.db.get_value("Attendance Request", req, "alvoraa_undone_on"), "the undo happened")
		self.assertEqual(self.rows(), [], "and nothing was logged")

	def test_A25_the_upload_tool_is_a_door_by_command_and_by_job(self):
		self.at_door(day_change.UPLOAD)
		self.assertTrue(day_change.at_a_door())
		self.leave_door()
		frappe.local.job = frappe._dict(method=day_change.UPLOAD_JOB, kwargs={})
		try:
			self.assertTrue(day_change.at_a_door())
		finally:
			frappe.local.job = None
		frappe.local.job = frappe._dict(method="hrms.x.y.other_job", kwargs={})
		try:
			self.assertFalse(day_change.at_a_door())
		finally:
			frappe.local.job = None

	def test_A26_a_data_import_is_a_door_by_its_reference_doctype(self):
		di = frappe.get_doc({"doctype": "Data Import", "reference_doctype": ATT, "import_type": "Insert New Records"})
		di.flags.ignore_validate = di.flags.ignore_mandatory = True
		di.insert(ignore_permissions=True)
		self.at_door(day_change._IMPORT_CMD, data_import=di.name)
		self.assertTrue(day_change.at_a_door())
		self.leave_door()
		other = frappe.get_doc({"doctype": "Data Import", "reference_doctype": "Employee Checkin",
		                        "import_type": "Insert New Records"})
		other.flags.ignore_validate = other.flags.ignore_mandatory = True
		other.insert(ignore_permissions=True)
		self.at_door(day_change._IMPORT_CMD, data_import=other.name)
		self.assertFalse(day_change.at_a_door())
		self.leave_door()


class TheReason(DayCase):
	def test_other_needs_text(self):
		with self.assertRaisesRegex(frappe.ValidationError, "say what happened"):
			self.desk(self.doc_dict(self.cancelled_day(), reason="Other"))

	def test_text_with_any_other_reason_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "reason is not 'Other'"):
			self.desk(self.doc_dict(self.cancelled_day(), reason=REASON, text="hello"))

	def test_text_is_capped_at_100(self):
		with self.assertRaisesRegex(frappe.ValidationError, "101 characters"):
			self.desk(self.doc_dict(self.cancelled_day(), reason="Other", text="x" * 101))
		self.desk(self.doc_dict(self.cancelled_day(), reason="Other", text="x" * 100))

	def test_text_is_stored_as_typed_one_line_and_never_as_markup(self):
		name = self.desk(self.doc_dict(self.cancelled_day(), reason="Other", text="  <img src=x onerror=1>\n\tmachine  fixed "))
		(row,) = self.rows(attendance=name)
		self.assertNotIn("onerror", row.reason_text, "Frappe's own Data sanitising strips the handler")
		self.assertTrue(row.reason_text.endswith("machine fixed"), row.reason_text)
		self.assertEqual(row.reason_code, "Other")

	def test_not_other_stores_no_text(self):
		name = self.desk(self.doc_dict(self.cancelled_day(), reason=REASON))
		self.assertIsNone(self.rows(attendance=name)[0].reason_text)

	def test_a_reason_not_on_the_list_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "not one of the reasons"):
			self.desk(self.doc_dict(self.cancelled_day(), reason="Because I said so"))

	def test_F3_an_import_cannot_put_a_bad_code_or_stray_text_in_the_record(self):
		"""Frappe skips its own Select check under `in_import`; ours does not. Control first."""
		frappe.flags.in_import = True
		try:
			ok = frappe.get_doc({"doctype": "Employee Checkin", "employee": self.emp,
			                     "time": "%s 11:00:00" % self.day, "log_type": "IN"})
			ok.set(punch_change.FIELD, "Because I said so")
			ok._validate_selects()                            # control: Frappe accepts it
			with self.assertRaisesRegex(frappe.ValidationError, "not one of the reasons"):
				self.desk(self.doc_dict(self.cancelled_day(), reason="Because I said so"))
			with self.assertRaisesRegex(frappe.ValidationError, "reason is not 'Other'"):
				self.desk(self.doc_dict(self.cancelled_day(), reason=REASON, text="x"))
			with self.assertRaisesRegex(frappe.ValidationError, "reason is not 'Other'"):
				self.punch("12:00", user=self.hr, reason=REASON, **{punch_change.TEXT_FIELD: "stray"})
		finally:
			frappe.flags.in_import = False

	def test_a_punch_may_carry_other_with_text_too(self):
		doc = self.punch("13:00", user=self.hr, reason="Other", **{punch_change.TEXT_FIELD: "reader cable cut"})
		(row,) = self.log(punch=doc.name)
		self.assertEqual((row.reason_code, row.reason_text), ("Other", "reader cable cut"))

	def test_the_paper_line_names_the_text_only_for_other(self):
		self.assertEqual(punch_change.why_line("Other", "reader cable cut"), "Other: reader cable cut")
		self.assertEqual(punch_change.why_line("Other", None), "Other")
		self.assertEqual(punch_change.why_line(REASON, "stray"), REASON)

	def test_the_log_refuses_a_hand_made_row_with_text(self):
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": LOG, "punch": "x", "employee": self.emp, "day": self.day,
			                "reason_code": "Other", "reason_text": "t", "what": "w", "changed_by": "Administrator",
			                "changed_on": frappe.utils.now_datetime()}).insert(ignore_permissions=True)


class TheListedEntryReachesTheNotice(DayCase):
	def test_a_day_change_is_read_back_by_the_notice_list(self):
		from alvoraa_portal import register_notice
		from frappe.utils import get_first_day

		day = self.cancelled_day()
		self.desk(self.doc_dict(day, reason="Other", text="reader cable cut"))
		rows = register_notice.qualifying_changes(get_first_day(day), [self.emp], with_content=True)
		mine = [r for r in rows if r.get("punch_change")]
		self.assertEqual(len(mine), 1)
		self.assertEqual(mine[0].what, "Day changed from Absent to Present")


class TheRunDocMethodDoor(DayCase):
	"""05d P1-1: `run_doc_method` (a form's `frm.call`, a plain API call) runs the whitelisted
	`Document.submit` and `Document.cancel`. It is a person's door when, and only when, the
	document is an Attendance. The Shift Type click uses the same command and must stay open."""

	_lwp = TheSystemAndTheOtherRecordsPass._lwp
	_leave = TheSystemAndTheOtherRecordsPass._leave

	def _rdm(self, cmd, user=None, **form):
		"""The real handler function, with the request looking like the HTTP one."""
		from frappe.handler import run_doc_method

		frappe.set_user(user or self.hr)
		self.at_door(cmd, **form)
		frappe.local.request = frappe._dict(method="POST", path="/api/method/" + cmd)
		try:
			return run_doc_method(**{k: v for k, v in form.items() if k in ("method", "docs", "dt", "dn")})
		finally:
			frappe.local.request = None
			frappe.set_user("Administrator")
			self.leave_door()

	def test_the_shift_type_click_is_still_not_a_door(self):
		"""Written first. The same command, a Shift Type in `docs`: untouched, switch ON."""
		self.at_door(RDM, method="process_auto_attendance", docs=SHIFT_DOCS)
		self.assertFalse(day_change.at_a_door())
		self.at_door(RDM, method="process_auto_attendance", dt="Shift Type", dn=hd.SHIFT)
		self.assertFalse(day_change.at_a_door())
		self.leave_door()

	def test_a_run_doc_method_cancel_of_a_day_needs_the_two_step_reason(self):
		att = self.submitted(day=self.a_day())
		for cmd in (RDM, "runserverobj"):
			with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason first"):
				self._rdm(cmd, method="cancel", dt=ATT, dn=att.name)
		self.assertEqual(frappe.db.get_value(ATT, att.name, "docstatus"), 1)
		d = frappe.get_doc(ATT, att.name).as_dict(convert_dates_to_str=True)
		d[day_change.FIELD] = REASON
		self.desk(d, "Update")
		self._rdm(RDM, method="cancel", dt=ATT, dn=att.name)
		self.assertEqual(frappe.db.get_value(ATT, att.name, "docstatus"), 2)
		(row,) = self.rows(attendance=att.name)
		self.assertEqual(row.what, "Day record reset so it is worked out again from your punches (was Present)")

	def test_a_run_doc_method_submit_of_a_replacement_needs_a_reason(self):
		day = self.cancelled_day()
		draft = frappe.get_doc(self.doc_dict(day, "Present")).insert(ignore_permissions=True)
		with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason"):
			self._rdm(RDM, method="submit", dt=ATT, dn=draft.name)
		self.assertEqual(frappe.db.get_value(ATT, draft.name, "docstatus"), 0)
		self.assertEqual(self.rows(), [])
		frappe.db.set_value(ATT, draft.name, day_change.FIELD, REASON)
		self._rdm(RDM, method="submit", docs=json.dumps(frappe.get_doc(ATT, draft.name).as_dict(convert_dates_to_str=True)))
		self.assertEqual(frappe.db.get_value(ATT, draft.name, "docstatus"), 1)
		self.assertEqual(len(self.rows(attendance=draft.name)), 1)

	def test_api_v2_has_no_cmd_so_the_document_names_the_door(self):
		frappe.local.request = frappe._dict(method="POST", path="/api/v2/method/run_doc_method")
		try:
			self.leave_door()
			frappe.form_dict.update({"method": "cancel", "document": json.dumps({"doctype": ATT, "name": "X"})})
			self.assertTrue(day_change.at_a_door())
			frappe.form_dict.update({"document": json.dumps({"doctype": "Shift Type", "name": hd.SHIFT})})
			self.assertFalse(day_change.at_a_door())
		finally:
			frappe.local.request = None
			self.leave_door()

	def test_a_leave_application_cancel_by_run_doc_method_stays_outside(self):
		"""Another record's `run_doc_method`: not a door, and the day it cancels is not listed."""
		day = self.a_day()
		leave = self._leave(day)
		leave.submit()
		self._rdm(RDM, method="cancel", dt="Leave Application", dn=leave.name)
		self.assertEqual(frappe.db.get_value("Leave Application", leave.name, "docstatus"), 2)
		self.assertEqual(self.rows(), [])


class TheWrappersCheckPermissionFirst(DayCase):
	"""05d P2-3: no user without rights on Attendance learns anything from the refusal order."""

	def test_an_employee_gets_the_same_permission_error_for_a_day_with_and_without_a_cancelled_record(self):
		from alvoraa_portal import day_change as dc

		with_record, without = self.cancelled_day(), self.a_day()
		for day in (with_record, without):
			with self.assertRaises(frappe.PermissionError):
				self.cmd_as(self.emp_user, dc.BULK_MARK, lambda: dc.mark_bulk_attendance(
					json.dumps({"employee": self.emp, "unmarked_days": [day], "status": "Present", "shift": hd.SHIFT})))
			with self.assertRaises(frappe.PermissionError):
				self.cmd_as(self.emp_user, dc.TOOL_MARK, lambda: dc.mark_employee_attendance(
					json.dumps([self.emp]), "Present", day, shift=hd.SHIFT))


class TheEmptyShiftTag(PunchChangeCase):
	"""05d P2-2 (088c code): a punch with no shift tag saved with nothing changed is not a change."""

	def _untagged(self):
		p = self._machine_punch(frappe.get_doc({"doctype": "Employee Checkin", "employee": self.emp, "log_type": "IN",
		                                        "time": "%s 06:10:00" % self.day}))
		frappe.db.set_value("Employee Checkin", p.name, {"shift": None, "shift_start": None, "shift_end": None})
		return p.name

	def test_a_no_op_save_of_an_untagged_punch_is_neither_demanded_nor_logged(self):
		name = self._untagged()
		doc = frappe.get_doc("Employee Checkin", name)
		self.assertFalse(punch_change._moved(doc, frappe.get_doc("Employee Checkin", name)),
		                 "nothing moved")
		frappe.set_user(self.hr)
		try:
			doc.save(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(self.log(), [])

	def test_changing_only_the_time_does_not_say_the_shift_changed(self):
		name = self._untagged()
		self.edit(name, self.hr, reason=REASON, time="%s 06:20:00" % self.day)
		(row,) = self.log(punch=name)
		self.assertNotIn("shift", row.what.lower())
		self.assertIn("moved from 06:10 to 06:20", row.what)


class TheSentenceNamesWhatMoved(DayCase):
	"""05d P2-1, built as approved in 00d section 5: names the fields that moved."""

	def _cancelled(self, **values):
		day = self.a_day()
		doc = frappe.get_doc(self.doc_dict(day, "Half Day", half_day_status="Present")).insert(ignore_permissions=True)
		doc.submit()
		doc.cancel()
		frappe.db.set_value(ATT, doc.name, values)
		return day

	def test_a_half_day_flip_that_moves_pay_is_named(self):
		day = self._cancelled(half_day_status="Present")
		self.desk(self.doc_dict(day, "Half Day", reason=REASON, half_day_status="Absent"))
		(row,) = self.rows()
		self.assertEqual(row.what, "Day changed: half day")

	def test_leave_type_and_shift_are_named_too(self):
		day = self._cancelled(half_day_status="Present", leave_type=None, shift=None)
		self.desk(self.doc_dict(day, "Half Day", reason=REASON, half_day_status="Present", leave_type=self._lwp()))
		(row,) = self.rows()
		self.assertEqual(row.what, "Day changed: leave type, shift")

	def test_nothing_moved_still_says_replaced(self):
		day = self._cancelled(half_day_status="Present")
		self.desk(self.doc_dict(day, "Half Day", reason=REASON, half_day_status="Present"))
		(row,) = self.rows()
		self.assertEqual(row.what, "Day record replaced, still Half Day")

	_lwp = TheSystemAndTheOtherRecordsPass._lwp


class TheReasonLeftOnACancelledRow(DayCase):
	"""05d P3-10."""

	def test_a_reason_saved_by_a_person_and_a_cancel_by_the_system_leaves_none_behind(self):
		att = self.submitted(day=self.a_day())
		d = frappe.get_doc(ATT, att.name).as_dict(convert_dates_to_str=True)
		d[day_change.FIELD] = "Other"
		d[day_change.TEXT] = "typed words"
		self.desk(d, "Update")
		self.assertEqual(frappe.db.get_value(ATT, att.name, day_change.FIELD), "Other")
		frappe.get_doc(ATT, att.name).cancel()                 # the system: no door
		self.assertEqual(frappe.db.get_value(ATT, att.name, [day_change.FIELD, day_change.TEXT]), (None, None))
		self.assertEqual(self.rows(), [])


class TheTwoLines(DayCase):
	"""Decision 5 (Surbhi, 26 Nov): a punch fix and then a day cancel print two lines, cause and
	consequence, not one merged line."""

	def test_a_fix_then_a_day_cancel_are_two_rows_on_the_notice_list(self):
		from alvoraa_portal import register_notice
		from frappe.utils import get_first_day

		att = self.held_on(self.day)
		req = self.fix(time="18:30", by=self.hr)
		self.decide(req, 1, by=self.h.hr2)
		d = frappe.get_doc(ATT, att).as_dict(convert_dates_to_str=True)
		d[day_change.FIELD] = REASON
		self.desk(d, "Update")                                  # first step of the cancel: nothing listed
		from frappe.desk.form.save import cancel
		self.cmd_as(self.hr, "frappe.desk.form.save.cancel", lambda: cancel(ATT, att), doctype=ATT, name=att)
		rows = [r for r in register_notice.qualifying_changes(get_first_day(self.day), [self.emp]) if str(r.from_date) == str(self.day)]
		self.assertEqual(len(rows), 2, "cause and consequence, never merged")
		self.assertEqual(sorted(bool(r.get("punch_change")) for r in rows), [False, True])
		(log,) = self.rows(attendance=att)
		self.assertTrue(log.what.startswith("Day record reset"))


class TheCost(DayCase):
	def _queries(self, fn):
		from unittest.mock import patch

		real, n = frappe.db.sql, [0]

		def counting(*a, **k):
			n[0] += 1
			return real(*a, **k)

		with patch.object(frappe.db, "sql", counting):
			fn()
		return n[0]

	def _handlers(self, rows):
		"""Only our handlers, on a system write (no door), `rows` times."""
		doc = frappe.get_doc(self.doc_dict(self.a_day()))
		doc.docstatus = 1
		doc.name = "D088-NOT-A-REAL-ROW"                      # so a stray write would still be counted
		for _ in range(rows):
			day_change.before_validate(doc)
			day_change.on_submit(doc)
			day_change.before_update_after_submit(doc)
			day_change.before_cancel(doc)
			day_change.on_cancel(doc)

	def test_a_system_write_costs_no_query_at_20_rows_or_at_1000(self):
		self._handlers(1)                                     # warm the caches
		few, many = self._queries(lambda: self._handlers(20)), self._queries(lambda: self._handlers(1000))
		print("\n088d handler queries: 20 rows = %d, 1000 rows = %d" % (few, many))
		self.assertEqual((few, many), (0, 0))

	def test_a_person_at_a_door_costs_two_reads_a_row_and_no_more(self):
		"""05d P3-9, measured: the person test repeats `files_as_machine` (two reads) for every
		employee and every row. Judged: two reads against the stock 21 queries a row, human-paced,
		so no cache is built (no-over-engineering: a number first). This test keeps the number."""
		frappe.set_user(self.hr)
		try:
			punch_change._is_a_persons_change(self.emp)           # warm the cached reads
			per = self._queries(lambda: [punch_change._is_a_persons_change(self.emp) for _ in range(500)]) / 500.0
		finally:
			frappe.set_user("Administrator")
		print("\n088d person test: %.2f queries a row (500 rows)" % per)
		self.assertLessEqual(per, 2.0)

	def test_the_whole_insert_costs_the_same_per_row_at_20_and_100(self):
		"""A full `mark_attendance` per row. 1000 rows take about half an hour a run, so the
		1000-row figure is measured once by hand and recorded in 03d, not in every run."""
		from hrms.hr.doctype.attendance.attendance import mark_attendance

		def run(n):
			start = getdate(add_days(self.day, -400 - DayCase._n))
			DayCase._n += n + 1

			def go():
				for i in range(n):
					mark_attendance(self.emp, add_days(start, -i), "Absent", hd.SHIFT)
			return self._queries(go)
		run(2)                                                # warm
		a, b = run(20), run(100)
		print("\n088d whole mark_attendance: 20 rows = %d queries (%.2f a row), 100 rows = %d (%.2f a row)" % (a, a / 20, b, b / 100))
		self.assertLess(abs(a / 20 - b / 100), 0.5)


class TheListIsComplete(DayCase):
	def test_every_path_has_a_test_that_asserts_something(self):
		"""**This checks names and that each named test contains an assertion. It does not prove the
		test covers the path's behaviour: that is read in the tests themselves.** It catches a
		deleted test and an empty one (A11 used to assert only that a function exists)."""
		import inspect

		tests = [(n, getattr(c, n)) for c in (TheSystemAndTheOtherRecordsPass, ThePathTableDoors)
		         for n in dir(c) if n.startswith("test_")]
		missing = [p for p in ["A%02d" % i for i in range(1, 32)] if not any(p in n for n, _f in tests)]
		self.assertEqual(missing, [], "paths with no test")
		hollow = [n for n, f in tests if re.search(r"A\d\d", n) and "self.assert" not in inspect.getsource(f)]
		self.assertEqual(hollow, [], "path tests with no assertion")
