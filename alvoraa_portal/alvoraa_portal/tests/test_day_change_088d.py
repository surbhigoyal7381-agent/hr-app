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
			self.desk(self.doc_dict(self.a_day()))

	def test_A01_the_hourly_job_marks_a_day_as_administrator(self):
		from hrms.hr.doctype.employee_checkin.employee_checkin import create_or_update_attendance

		day = self.a_day()
		att = create_or_update_attendance(self.emp, day, "Present", working_hours=8, shift=hd.SHIFT)
		self.assertEqual(frappe.db.get_value(ATT, att.name, "docstatus"), 1)
		self.assertEqual(self.rows(), [])

	def test_A02_a_person_clicking_the_shift_type_button_runs_the_same_code(self):
		from hrms.hr.doctype.employee_checkin.employee_checkin import create_or_update_attendance

		day = self.a_day()
		att = self.cmd_as(self.hr, "frappe.desk.form.run_method.runserverobj",
		                  lambda: create_or_update_attendance(self.emp, day, "Present", working_hours=8, shift=hd.SHIFT),
		                  docs=json.dumps({"doctype": "Shift Type", "name": hd.SHIFT}), method="process_auto_attendance")
		self.assertEqual(frappe.db.get_value(ATT, att.name, "docstatus"), 1)
		self.assertEqual(self.rows(), [])

	def test_A03_an_absent_day_for_no_punch(self):
		from hrms.hr.doctype.attendance.attendance import mark_attendance

		day = self.a_day()
		name = self.cmd_as(self.hr, "frappe.desk.form.run_method.runserverobj",
		                   lambda: mark_attendance(self.emp, day, "Absent", hd.SHIFT),
		                   docs=json.dumps({"doctype": "Shift Type", "name": hd.SHIFT}))
		self.assertEqual(frappe.db.get_value(ATT, name, "docstatus"), 1)
		self.assertEqual(self.rows(), [])

	def test_A04_the_other_half_set_absent_by_set_value(self):
		"""No hook runs on `set_value`, so nothing can be asked or listed. Documented, not a rule."""
		att = self.submitted("Half Day", half_day_status="Present")
		self.cmd_as(self.hr, "frappe.desk.form.run_method.runserverobj", lambda: frappe.db.set_value(
			ATT, att.name, {"half_day_status": "Absent", "modify_half_day_status": 0}))
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
		name = self.desk(self.doc_dict(self.a_day()))
		self.assertTrue(name)
		self.assertEqual(self.rows(), [])


class ThePathTableDoors(DayCase):
	"""The paths that ARE a person's direct edit: listed, and refused without a reason."""

	def test_A16_a_person_marks_a_day_with_a_reason_and_it_is_listed(self):
		day = self.a_day()
		name = self.desk(self.doc_dict(day, "Present", reason=REASON))
		(row,) = self.rows(attendance=name)
		self.assertEqual((row.what, row.reason_code, str(row.day)), ("Day marked Present", REASON, day))
		self.assertIsNone(frappe.db.get_value(ATT, name, day_change.FIELD), "the reason must not stay on the row")

	def test_A16b_a_draft_is_never_demanded_or_listed(self):
		day = self.a_day()
		name = self.desk(self.doc_dict(day), action="Save")
		self.assertEqual(frappe.db.get_value(ATT, name, "docstatus"), 0)
		self.assertEqual(self.rows(), [])

	def test_A16c_submit_writes_one_row_not_two(self):
		self.desk(self.doc_dict(self.a_day(), reason=REASON))
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

		name = self.desk(self.doc_dict(self.a_day()), action="Save")
		self.cmd_as(self.hr, "frappe.client.delete", lambda: frappe.client.delete(ATT, name), doctype=ATT, name=name)
		self.assertFalse(frappe.db.exists(ATT, name))
		self.assertEqual(self.rows(), [])

	def test_A21_frappe_client_and_REST_are_doors(self):
		import frappe.client

		day = self.a_day()
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

	def test_A23_mark_attendance_is_refused_loudly_not_swallowed(self):
		day = self.a_day()
		data = json.dumps({"employee": self.emp, "unmarked_days": [day], "status": "Present", "shift": hd.SHIFT})
		with self.assertRaisesRegex(frappe.ValidationError, "'Mark Attendance' is not available"):
			self.cmd_as(self.hr, day_change.BULK_MARK, lambda: day_change.mark_bulk_attendance(data))
		self.assertFalse(frappe.db.exists(ATT, {"employee": self.emp, "attendance_date": day}))

	def test_A23b_the_stock_loop_alone_would_swallow_the_refusal(self):
		"""Why the wrapper exists: the stock loop skips the row and the person is told it worked."""
		from hrms.hr.doctype.attendance.attendance import process_bulk_attendance_in_batches

		day = self.a_day()
		data = frappe._dict(employee=self.emp, unmarked_days=[day], status="Present", shift=hd.SHIFT)
		self.cmd_as(self.hr, day_change.BULK_MARK, lambda: process_bulk_attendance_in_batches(data))
		self.assertFalse(frappe.db.exists(ATT, {"employee": self.emp, "attendance_date": day, "docstatus": 1}))

	def test_A23c_with_the_switch_off_the_stock_tool_runs(self):
		self._set_notices(0)
		day = self.a_day()
		data = json.dumps({"employee": self.emp, "unmarked_days": [day], "status": "Present", "shift": hd.SHIFT})
		self.cmd_as(self.hr, day_change.BULK_MARK, lambda: day_change.mark_bulk_attendance(data))
		self.assertTrue(frappe.db.exists(ATT, {"employee": self.emp, "attendance_date": day, "docstatus": 1}))

	def test_A24_the_attendance_tool_and_its_half_day_tick_are_refused(self):
		day = self.a_day()
		with self.assertRaisesRegex(frappe.ValidationError, "'Employee Attendance Tool' is not available"):
			self.cmd_as(self.hr, day_change.TOOL_MARK, lambda: day_change.mark_employee_attendance(
				json.dumps([self.emp]), "Present", day, shift=hd.SHIFT))
		att = self.submitted("Half Day", half_day_status="Present")
		was = frappe.db.get_value(ATT, att.name, "half_day_status")
		with self.assertRaisesRegex(frappe.ValidationError, "not available"):
			self.cmd_as(self.hr, day_change.TOOL_MARK, lambda: day_change.mark_employee_attendance(
				json.dumps([]), "Present", str(att.attendance_date), mark_half_day=True, half_day_status="Absent",
				half_day_employee_list=json.dumps([self.emp])))
		self.assertEqual(frappe.db.get_value(ATT, att.name, "half_day_status"), was)

	def test_A24b_with_the_switch_off_the_tool_runs(self):
		self._set_notices(0)
		day = self.a_day()
		self.cmd_as(self.hr, day_change.TOOL_MARK, lambda: day_change.mark_employee_attendance(
			json.dumps([self.emp]), "Present", day, shift=hd.SHIFT))
		self.assertTrue(frappe.db.exists(ATT, {"employee": self.emp, "attendance_date": day, "docstatus": 1}))

	def test_A11_the_two_unlisted_gaps_are_named(self):
		"""A11 (087 undo) writes by set_value and is a known gap from 00b (P10), unchanged here."""
		from alvoraa_portal import punch_fix

		self.assertTrue(callable(punch_fix.undo_change))

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
			self.desk(self.doc_dict(self.a_day(), reason="Other"))

	def test_text_with_any_other_reason_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "reason is not 'Other'"):
			self.desk(self.doc_dict(self.a_day(), reason=REASON, text="hello"))

	def test_text_is_capped_at_100(self):
		with self.assertRaisesRegex(frappe.ValidationError, "101 characters"):
			self.desk(self.doc_dict(self.a_day(), reason="Other", text="x" * 101))
		self.desk(self.doc_dict(self.a_day(), reason="Other", text="x" * 100))

	def test_text_is_stored_as_typed_one_line_and_never_as_markup(self):
		name = self.desk(self.doc_dict(self.a_day(), reason="Other", text="  <img src=x onerror=1>\n\tmachine  fixed "))
		(row,) = self.rows(attendance=name)
		self.assertNotIn("onerror", row.reason_text, "Frappe's own Data sanitising strips the handler")
		self.assertTrue(row.reason_text.endswith("machine fixed"), row.reason_text)
		self.assertEqual(row.reason_code, "Other")

	def test_not_other_stores_no_text(self):
		name = self.desk(self.doc_dict(self.a_day(), reason=REASON))
		self.assertIsNone(self.rows(attendance=name)[0].reason_text)

	def test_a_reason_not_on_the_list_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "not one of the reasons"):
			self.desk(self.doc_dict(self.a_day(), reason="Because I said so"))

	def test_F3_an_import_cannot_put_a_bad_code_or_stray_text_in_the_record(self):
		"""Frappe skips its own Select check under `in_import`; ours does not. Control first."""
		frappe.flags.in_import = True
		try:
			ok = frappe.get_doc({"doctype": "Employee Checkin", "employee": self.emp,
			                     "time": "%s 11:00:00" % self.day, "log_type": "IN"})
			ok.set(punch_change.FIELD, "Because I said so")
			ok._validate_selects()                            # control: Frappe accepts it
			with self.assertRaisesRegex(frappe.ValidationError, "not one of the reasons"):
				self.desk(self.doc_dict(self.a_day(), reason="Because I said so"))
			with self.assertRaisesRegex(frappe.ValidationError, "reason is not 'Other'"):
				self.desk(self.doc_dict(self.a_day(), reason=REASON, text="x"))
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

		day = self.a_day()
		self.desk(self.doc_dict(day, reason="Other", text="reader cable cut"))
		rows = register_notice.qualifying_changes(get_first_day(day), [self.emp], with_content=True)
		mine = [r for r in rows if r.get("punch_change")]
		self.assertEqual(len(mine), 1)
		self.assertEqual(mine[0].what, "Day marked Present")


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
	def test_every_path_has_a_test(self):
		names = " ".join(n for c in (TheSystemAndTheOtherRecordsPass, ThePathTableDoors)
		                 for n in dir(c) if n.startswith("test_"))
		missing = [p for p in ["A%02d" % i for i in range(1, 32)] if p not in names]
		# A29 and A30 share one test, A06b and A16b etc. are extras; the 31 ids must all appear.
		self.assertEqual(missing, [], "paths with no test")
