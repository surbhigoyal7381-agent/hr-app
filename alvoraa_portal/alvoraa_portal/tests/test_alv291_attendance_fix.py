"""ALV-291: the one-time October attendance fix, run end to end on fixtures.

One scenario test walks the runbook in order, because every step acts on whole
shifts and commits: separate tests would fight over the same shifts. Smaller
tests cover the refusals and the last-sync ceiling trap.

The fixtures copy DTC's shape:
  ABH  - Abhishek-like. Default 10:00-19:00, punches 09:35 and 19:16 tagged to
         10:30-20:30, attendance already marked on that wrong shift.
         Day 3 is a leave day and must be KEPT.
  HAND - same wrong tag, but a person edited the attendance. KEPT.
  GRPA - on a shift with auto attendance OFF and a start date after the
         period; no attendance for days 1-2, and an Absent on day 3 although
         badged in.
  SAME - tagged to a shift with identical timings. Left alone by default.
"""

import os
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime, nowdate

from alvoraa_portal import alv291_attendance_fix as fix

COMPANY = "ALV291 Test Co"
TRAP_COMPANY = "ALV291 Trap Co"
RIGHT = "A291 10:00-19:00"
WRONG = "A291 10:30-20:30"
OFF = "A291 Off 09:00-18:00"
SAME = "A291 Same 10:00-19:00"
TRAP = "A291 Trap 10:00-19:00"


def _company(name, abbr):
	if not frappe.db.exists("Company", name):
		frappe.get_doc({"doctype": "Company", "company_name": name, "abbr": abbr,
		                "default_currency": "INR", "country": "India"}).insert()


def _gender():
	return frappe.db.get_value("Gender", {}, "name") or frappe.get_doc(
		{"doctype": "Gender", "gender": "Other"}).insert().name


def _shift(name, start, end, **extra):
	if frappe.db.exists("Shift Type", name):
		frappe.delete_doc("Shift Type", name, force=True)
	frappe.get_doc({
		"doctype": "Shift Type", "name": name, "start_time": start, "end_time": end,
		"begin_check_in_before_shift_start_time": 180,
		"allow_check_out_after_shift_end_time": 180,
		"determine_check_in_and_check_out": "Alternating entries as IN and OUT during the same shift",
		"working_hours_calculation_based_on": "First Check-in and Last Check-out",
		**extra,
	}).insert()


def _employee(first, company, shift):
	return frappe.get_doc({
		"doctype": "Employee", "first_name": first, "last_name": "A291",
		"company": company, "date_of_joining": add_days(nowdate(), -200),
		"date_of_birth": "1990-01-01", "gender": _gender(), "status": "Active",
		"default_shift": shift,
	}).insert().name


def _punch(emp, day, hhmm):
	return frappe.get_doc({"doctype": "Employee Checkin", "employee": emp,
	                       "time": f"{day} {hhmm}:00"}).insert().name


def _set_default(emp, shift):
	frappe.db.set_value("Employee", emp, "default_shift", shift)
	frappe.db.value_cache.clear()


def _rule_set():
	if frappe.db.get_value("Alvoraa Payroll Rule Set", {"company": COMPANY}):
		return
	frappe.get_doc({
		"doctype": "Alvoraa Payroll Rule Set", "company": COMPANY, "enabled": 1,
		"grace_minutes": 6, "free_reds_per_month": 2, "special_day_multiplier": 2,
		"leave_threshold_days": 15, "accrual_month_days": 30,
		"slabs": [
			{"percent_from": 0, "percent_to": 20, "quarters_off": 4, "raises_red": 0},
			{"percent_from": 20, "percent_to": 68, "quarters_off": 2, "raises_red": 0},
			{"percent_from": 68, "percent_to": 90, "quarters_off": 1, "raises_red": 0},
			{"percent_from": 90, "percent_to": 98.9, "quarters_off": 0, "raises_red": 1},
			{"percent_from": 98.9, "percent_to": 100, "quarters_off": 0, "raises_red": 0},
		],
		"mark_rates": [{"grade": "Junior", "amount_per_mark": 100}],
	}).insert()


def _live(emp, day):
	return frappe.get_all("Attendance", filters={"employee": emp, "attendance_date": day, "docstatus": 1},
	                      fields=["name", "status", "shift", "alvoraa_attendance_percent"])


def _cleanup(company):
	emps = frappe.get_all("Employee", filters={"company": company}, pluck="name")
	if emps:
		atts = frappe.get_all("Attendance", filters={"employee": ("in", emps)}, pluck="name")
		if atts:
			frappe.db.delete("Comment", {"reference_doctype": "Attendance", "reference_name": ("in", atts)})
		frappe.db.delete("Attendance", {"employee": ("in", emps)})
		frappe.db.delete("Employee Checkin", {"employee": ("in", emps)})
		frappe.db.delete("Employee", {"name": ("in", emps)})
	frappe.db.commit()


class TestAlv291AttendanceFix(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.state_patch = patch.object(fix, "STATE_FILE", "alv291_test_state.json")
		cls.sleep_patch = patch.object(fix, "PAUSE_SECONDS", 0)
		cls.state_patch.start()
		cls.sleep_patch.start()
		_company(COMPANY, "A291")
		_company(TRAP_COMPANY, "A291T")
		_cleanup(COMPANY)
		_cleanup(TRAP_COMPANY)
		_rule_set()

	@classmethod
	def tearDownClass(cls):
		_cleanup(COMPANY)
		_cleanup(TRAP_COMPANY)
		for s in (RIGHT, WRONG, OFF, SAME, TRAP):
			if frappe.db.exists("Shift Type", s):
				frappe.delete_doc("Shift Type", s, force=True)
		if os.path.exists(fix._state_path()):
			os.remove(fix._state_path())
		frappe.db.commit()
		cls.state_patch.stop()
		cls.sleep_patch.stop()
		super().tearDownClass()

	def test_not_web_callable_and_admin_only(self):
		for name in ("preview", "pause", "set_start", "cancel_wrong", "retag",
		             "enable_and_mark", "verify", "undo"):
			fn = getattr(fix, name)
			self.assertNotIn(fn, frappe.whitelisted, name)
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.ValidationError):
				fix.preview(COMPANY, nowdate(), nowdate())
			with self.assertRaises(frappe.ValidationError):
				fix.undo()
		finally:
			frappe.set_user("Administrator")

	def test_last_sync_set_before_the_period_marks_nothing(self):
		"""The trap from 16 Oct: last_sync is a CEILING. Set it before the
		period and the job marks nothing there. Nobody should 'reset' it."""
		day = add_days(nowdate(), -20)
		_shift(TRAP, "10:00:00", "19:00:00", enable_auto_attendance=1,
		       process_attendance_after=add_days(day, -1),
		       last_sync_of_checkin=f"{add_days(day, -1)} 23:00:00")
		emp = _employee("Trap", TRAP_COMPANY, TRAP)
		_punch(emp, day, "09:55")
		_punch(emp, day, "19:05")
		frappe.get_doc("Shift Type", TRAP).process_auto_attendance(is_manually_triggered=1)
		self.assertEqual(_live(emp, day), [])
		# The same shift with the ceiling after the period does mark it.
		frappe.db.set_value("Shift Type", TRAP, "last_sync_of_checkin", now_datetime())
		frappe.get_doc("Shift Type", TRAP).process_auto_attendance(is_manually_triggered=1)
		self.assertEqual(len(_live(emp, day)), 1)
		frappe.db.set_value("Shift Type", TRAP, "enable_auto_attendance", 0)
		frappe.db.commit()

	def test_the_runbook_end_to_end(self):
		d1, d2, d3 = (getdate(add_days(nowdate(), -12 + i)) for i in range(3))
		start = add_days(d1, -1)
		frm, to = str(d1), str(d3)

		_shift(RIGHT, "10:00:00", "19:00:00", enable_auto_attendance=1, auto_update_last_sync=1,
		       process_attendance_after=start, last_sync_of_checkin=now_datetime())
		_shift(WRONG, "10:30:00", "20:30:00", enable_auto_attendance=1, auto_update_last_sync=1,
		       process_attendance_after=start, last_sync_of_checkin=now_datetime())
		# Group A: switched off, start date after the period (the "28 Oct" case),
		# and a stale ceiling that only Frappe's own hourly step moves.
		_shift(OFF, "09:00:00", "18:00:00", enable_auto_attendance=0, auto_update_last_sync=1,
		       process_attendance_after=d3, last_sync_of_checkin=f"{d1} 08:00:00")
		_shift(SAME, "10:00:00", "19:00:00", enable_auto_attendance=0, auto_update_last_sync=1,
		       process_attendance_after=start, last_sync_of_checkin=now_datetime())

		# ABH and HAND punch while their default is the wrong shift, so the punches
		# carry the wrong tag, and the wrong shift marks their attendance.
		abh = _employee("Abh", COMPANY, WRONG)
		hand = _employee("Hand", COMPANY, WRONG)
		grpa = _employee("GrpA", COMPANY, OFF)
		same = _employee("Same", COMPANY, SAME)
		for d in (d1, d2, d3):
			_punch(abh, d, "09:35")
			_punch(abh, d, "19:16")
		_punch(hand, d1, "09:40")
		_punch(hand, d1, "19:10")
		frappe.get_doc("Shift Type", WRONG).process_auto_attendance(is_manually_triggered=1)
		for d in (d1, d2, d3):
			self.assertEqual(_live(abh, d)[0].shift, WRONG)
		self.assertLess(_live(abh, d1)[0].alvoraa_attendance_percent, 100)
		# Day 3 became a leave day; HAND's day was changed by a person.
		frappe.db.set_value("Attendance", _live(abh, d3)[0].name,
		                    {"leave_application": "HR-LAP-A291", "status": "On Leave"})
		frappe.db.set_value("Attendance", _live(hand, d1)[0].name, "modified_by", "hr291@example.com",
		                    update_modified=False)
		_set_default(abh, RIGHT)
		_set_default(hand, RIGHT)

		for d in (d1, d2, d3):
			_punch(grpa, d, "09:05")
			_punch(grpa, d, "18:10")
		absent = frappe.get_doc({"doctype": "Attendance", "employee": grpa, "company": COMPANY,
		                         "attendance_date": d3, "status": "Absent", "shift": OFF}).insert()
		absent.submit()
		_punch(same, d1, "10:01")
		_punch(same, d1, "19:02")
		_set_default(same, RIGHT)  # tag SAME, default RIGHT: identical timings
		frappe.db.commit()

		# ── 0. preview writes nothing ──
		before = (frappe.db.count("Attendance"), frappe.db.count("Employee Checkin", {"shift": WRONG}))
		out = fix.preview(COMPANY, frm, to, start=start)
		self.assertEqual(before, (frappe.db.count("Attendance"),
		                          frappe.db.count("Employee Checkin", {"shift": WRONG})))
		self.assertFalse(os.path.exists(fix._state_path()))
		self.assertEqual(out["retag_punches"], 4)        # ABH days 1-2; day 3 kept
		self.assertEqual(out["retag_people"], 1)
		self.assertEqual(out["same_timing_people"], 1)
		self.assertEqual(out["cancel"], 3)               # ABH d1, d2 + GRPA's Absent
		self.assertEqual(out["skipped"], 2)              # leave + hand-edited
		self.assertGreater(out["absent"], 0)             # the loud warning has a number

		# ── 1. pause ──
		fix.pause(COMPANY, frm, to)
		self.assertEqual(fix._enabled([RIGHT, WRONG, OFF, SAME]), [])
		self.assertEqual(fix._state()["shifts"][RIGHT]["enable_auto_attendance"], 1)
		self.assertEqual(fix.pause(COMPANY, frm, to)["paused"], 0)   # twice is fine

		# A person with a submitted slip is refused by every step that names people.
		with patch.object(fix, "_paid", return_value={abh, hand, grpa, same}):
			self.assertEqual(fix.cancel_wrong(COMPANY, frm, to)["cancelled"], 0)
			self.assertEqual(fix.retag(COMPANY, frm, to)["retagged"], 0)
			with self.assertRaises(frappe.ValidationError):
				fix.enable_and_mark(COMPANY, frm, to)
		self.assertEqual(fix._enabled([RIGHT, WRONG, OFF, SAME]), [])

		# ── 2. set_start ──
		fix.set_start(COMPANY, frm, to, date=start)
		self.assertEqual(getdate(frappe.db.get_value("Shift Type", OFF, "process_attendance_after")), getdate(start))
		self.assertEqual(str(fix._state()["shifts"][OFF]["process_attendance_after"]), str(d3))
		self.assertEqual(fix.set_start(COMPANY, frm, to, date=start)["changed"], 0)

		# Retag before cancel (the plan's order) cannot move linked punches.
		self.assertEqual(fix.retag(COMPANY, frm, to)["still_linked"], 4)

		# ── 3. cancel_wrong ──
		self.assertEqual(fix.cancel_wrong(COMPANY, frm, to)["cancelled"], 3)
		self.assertEqual(_live(abh, d1), [])
		self.assertEqual(len(_live(abh, d3)), 1)          # leave day kept
		self.assertEqual(len(_live(hand, d1)), 1)         # hand-edited kept
		self.assertEqual(fix.cancel_wrong(COMPANY, frm, to)["cancelled"], 0)

		# ── 4. retag ──
		abh_d1 = frappe.get_all("Employee Checkin", filters={"employee": abh, "time": ("like", f"{d1}%")},
		                        fields=["name", "shift", "shift_start", "shift_end"])
		self.assertEqual(fix.retag(COMPANY, frm, to)["retagged"], 4)
		for p in abh_d1:
			now = frappe.db.get_value("Employee Checkin", p.name, ["shift", "shift_start", "shift_end"], as_dict=True)
			self.assertEqual(now.shift, RIGHT)
			self.assertEqual(str(now.shift_start), f"{d1} 10:00:00")
			self.assertEqual(str(now.shift_end), f"{d1} 19:00:00")
		self.assertEqual(frappe.db.get_value("Employee Checkin", {"employee": same}, "shift"), SAME)
		self.assertEqual(fix.retag(COMPANY, frm, to)["retagged"], 0)

		# ── 5. enable_and_mark ──
		kept_leave = _live(abh, d3)[0].name
		fix.enable_and_mark(COMPANY, frm, to)
		self.assertEqual(sorted(fix._enabled([RIGHT, WRONG, OFF, SAME])), sorted([RIGHT, WRONG, OFF, SAME]))
		for d in (d1, d2):
			row = _live(abh, d)
			self.assertEqual(len(row), 1)
			self.assertEqual((row[0].shift, row[0].status), (RIGHT, "Present"))
			self.assertEqual(row[0].alvoraa_attendance_percent, 100)
		self.assertEqual(_live(abh, d3)[0].name, kept_leave)
		# The kept day's punches stay linked to the kept record: only unlinked punches are processed.
		self.assertEqual(set(frappe.get_all("Employee Checkin", filters={"employee": abh, "time": ("like", f"{d3}%")},
		                                    pluck="attendance")), {kept_leave})
		for d in (d1, d2, d3):
			self.assertEqual([(r.shift, r.status) for r in _live(grpa, d)], [(OFF, "Present")])
		self.assertEqual(frappe.get_doc("Shift Type", OFF).enable_auto_attendance, 1)   # stays on
		fix.enable_and_mark(COMPANY, frm, to)   # twice: no duplicates

		# ── 6. verify ──
		v = fix.verify(COMPANY, frm, to, reds_for=[abh])
		self.assertEqual(v["duplicates"], 0)
		self.assertEqual(v["days_punched_no_attendance"], 0)
		self.assertEqual(v["wrong_tag_unlinked"], 0)
		self.assertEqual(v["wrong_tag_on_kept_days"], 4)   # ABH's leave day + HAND's edited day
		self.assertEqual(v[f"reds_{abh}"], 0)

		# ── 7. undo ──
		u = fix.undo()
		self.assertEqual(u["linked"], 4)          # rebuilt days hold them
		self.assertEqual(u["cancelled_not_undone"], 3)
		self.assertEqual(frappe.db.get_value("Shift Type", OFF, "enable_auto_attendance"), 0)
		self.assertEqual(getdate(frappe.db.get_value("Shift Type", OFF, "process_attendance_after")), d3)
		self.assertEqual(frappe.db.get_value("Shift Type", RIGHT, "enable_auto_attendance"), 1)
		# Once the rebuilt day is cancelled, undo puts the old tag and times back.
		frappe.get_doc("Attendance", _live(abh, d1)[0].name).cancel()
		frappe.db.commit()
		fix.undo()
		for p in abh_d1:
			now = frappe.db.get_value("Employee Checkin", p.name, ["shift", "shift_start", "shift_end"], as_dict=True)
			self.assertEqual((now.shift, now.shift_start, now.shift_end), (WRONG, p.shift_start, p.shift_end))
