"""ALV-291: the one-time October attendance fix, run end to end on fixtures.

One scenario test walks the runbook in order, because every step acts on whole
shifts and commits: separate tests would fight over the same shifts. Smaller
tests cover the refusals and the last-sync ceiling trap.

The fixtures copy DTC's shape:
  ABH    - Abhishek-like. Default 10:00-19:00, punches 09:35 and 19:16 tagged to
           10:30-20:30, attendance marked on that wrong shift. Day 3 is leave: KEPT.
  HAND   - same wrong tag; a person (not Administrator) edited the row: KEPT.
  FIXADM - same wrong tag; the row was corrected later AS ADMINISTRATOR: KEPT.
  GRPA   - shift with auto attendance OFF; no attendance on days 1-2, and an
           automatic Absent (Frappe's comment) on day 3 although badged in: CANCELLED.
  AMEND, HANDABS, REQ, CONF - Group A people whose day-1 Absent is amended,
           made by hand as Administrator, from an Attendance Request, or
           confirmed by a manager: all KEPT.
  SAME   - tagged to a shift with identical timings, no attendance (the M1 case).
"""

import os
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, getdate, now_datetime, nowdate

from alvoraa_portal import alv291_attendance_fix as fix

COMPANY = "ALV291 Test Co"
TRAP_COMPANY = "ALV291 Trap Co"
RIGHT = "A291 10:00-19:00"
WRONG = "A291 10:30-20:30"
OFF = "A291 Off 09:00-18:00"
SAME = "A291 Same 10:00-19:00"
TRAP = "A291 Trap 10:00-19:00"
STEPS = ("preview", "pause", "set_start", "cancel_wrong", "retag", "enable_and_mark", "verify", "undo")


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


def _absent(emp, day, auto=False, shift=OFF):
	doc = frappe.get_doc({"doctype": "Attendance", "employee": emp, "company": COMPANY,
	                      "attendance_date": day, "status": "Absent", "shift": shift}).insert()
	doc.submit()
	if auto:
		doc.add_comment("Comment", fix.AUTO_ABSENT_COMMENT)
	return doc


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


def _slip(emp, frm, to):
	"""A submitted slip row, written straight to the table: building a real
	salary structure is not what this test is about, the query is."""
	doc = frappe.new_doc("Salary Slip")
	doc.update({"name": f"A291-SLIP-{emp}", "employee": emp, "company": COMPANY, "start_date": frm,
	            "end_date": to, "posting_date": to, "docstatus": 1})
	doc.db_insert()
	return doc.name


def _cleanup(company):
	emps = frappe.get_all("Employee", filters={"company": company}, pluck="name")
	if emps:
		atts = frappe.get_all("Attendance", filters={"employee": ("in", emps)}, pluck="name")
		if atts:
			frappe.db.delete("Comment", {"reference_doctype": "Attendance", "reference_name": ("in", atts)})
		frappe.db.delete("Attendance", {"employee": ("in", emps)})
		frappe.db.delete("Employee Checkin", {"employee": ("in", emps)})
		frappe.db.delete("Salary Slip", {"employee": ("in", emps)})
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
		if os.path.exists(fix._state_path()):
			os.remove(fix._state_path())

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

	def test_not_web_callable_and_every_step_admin_only(self):
		args = {"preview": (COMPANY, nowdate(), nowdate()), "undo": ()}
		for name in STEPS:
			self.assertNotIn(getattr(fix, name), frappe.whitelisted, name)
		frappe.set_user("Guest")
		try:
			for name in STEPS:
				with self.assertRaises(frappe.ValidationError, msg=name):
					getattr(fix, name)(*args.get(name, (COMPANY, nowdate(), nowdate())))
		finally:
			frappe.set_user("Administrator")

	def test_steps_refuse_without_a_frozen_list(self):
		for name in ("cancel_wrong", "retag", "enable_and_mark", "verify"):
			with self.assertRaises(frappe.ValidationError, msg=name):
				getattr(fix, name)("No Such Co", "2026-10-01", "2026-10-31")

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
		frappe.db.set_value("Shift Type", TRAP, "last_sync_of_checkin", now_datetime())
		frappe.get_doc("Shift Type", TRAP).process_auto_attendance(is_manually_triggered=1)
		self.assertEqual(len(_live(emp, day)), 1)
		frappe.db.set_value("Shift Type", TRAP, "enable_auto_attendance", 0)
		frappe.db.commit()

	def test_the_runbook_end_to_end(self):
		d1, d2, d3 = (getdate(add_days(nowdate(), -12 + i)) for i in range(3))
		start = d1          # "1 Oct": the first day of the period
		frm, to = str(d1), str(d3)
		old_start = add_days(d1, -5)   # N2: the shifts that were on must get this back

		_shift(RIGHT, "10:00:00", "19:00:00", enable_auto_attendance=1, auto_update_last_sync=1,
		       process_attendance_after=old_start, last_sync_of_checkin=now_datetime())
		_shift(WRONG, "10:30:00", "20:30:00", enable_auto_attendance=1, auto_update_last_sync=1,
		       process_attendance_after=old_start, last_sync_of_checkin=now_datetime())
		_shift(OFF, "09:00:00", "18:00:00", enable_auto_attendance=0, auto_update_last_sync=1,
		       process_attendance_after=d3, last_sync_of_checkin=f"{d1} 08:00:00")
		_shift(SAME, "10:00:00", "19:00:00", enable_auto_attendance=0, auto_update_last_sync=1,
		       process_attendance_after=start, last_sync_of_checkin=now_datetime())

		# Wrong tags: they punch while their default is WRONG, and WRONG marks them.
		abh = _employee("Abh", COMPANY, WRONG)
		hand = _employee("Hand", COMPANY, WRONG)
		fixadm = _employee("FixAdm", COMPANY, WRONG)
		for d in (d1, d2, d3):
			_punch(abh, d, "09:35")
			_punch(abh, d, "19:16")
		for e in (hand, fixadm):
			_punch(e, d1, "09:40")
			_punch(e, d1, "19:10")
		frappe.get_doc("Shift Type", WRONG).process_auto_attendance(is_manually_triggered=1)
		self.assertLess(_live(abh, d1)[0].alvoraa_attendance_percent, 100)
		frappe.db.set_value("Attendance", _live(abh, d3)[0].name,
		                    {"leave_application": "HR-LAP-A291", "status": "On Leave"})
		frappe.db.set_value("Attendance", _live(hand, d1)[0].name, "modified_by", "hr291@example.com",
		                    update_modified=False)
		# B1: corrected as Administrator an hour after the job made it.
		fix_row = _live(fixadm, d1)[0].name
		frappe.db.set_value("Attendance", fix_row, "creation", add_to_date(now_datetime(), hours=-1),
		                    update_modified=False)
		frappe.db.set_value("Attendance", fix_row, "status", "Half Day")
		for e in (abh, hand, fixadm):
			_set_default(e, RIGHT)

		grpa = _employee("GrpA", COMPANY, OFF)
		for d in (d1, d2, d3):
			_punch(grpa, d, "09:05")
			_punch(grpa, d, "18:10")
		_absent(grpa, d3, auto=True)
		kept_absent = {}
		for name in ("Amend", "HandAbs", "Req", "Conf"):
			e = _employee(name, COMPANY, OFF)
			for d in (d1, d2):
				_punch(e, d, "09:05")
				_punch(e, d, "18:10")
			row = _absent(e, d1, auto=name != "HandAbs")
			if name == "Amend":
				row.cancel()
				new = frappe.copy_doc(row)
				new.amended_from = row.name
				new.docstatus = 0
				new.insert()
				new.submit()
				row = new
			elif name == "Req":
				frappe.db.set_value("Attendance", row.name, "attendance_request", "HR-ARQ-A291")
			elif name == "Conf":
				frappe.db.set_value("Attendance", row.name, "alvoraa_held_confirmed", 1)
			kept_absent[e] = row.name
		same = _employee("Same", COMPANY, SAME)
		_punch(same, d1, "10:01")
		_punch(same, d1, "19:02")
		_set_default(same, RIGHT)  # tag SAME, default RIGHT: identical timings
		# M3: on a shift that is switched on, but no punches: not one of "the 73".
		outsider = _employee("Outsider", COMPANY, RIGHT)
		# N1: on the formerly-off shift, not in the list, with an open half-day row.
		offout = _employee("OffOut", COMPANY, OFF)
		half = frappe.get_doc({"doctype": "Attendance", "employee": offout, "company": COMPANY,
		                       "attendance_date": add_days(d1, -20), "status": "Half Day", "shift": OFF}).insert()
		half.submit()
		frappe.db.set_value("Attendance", half.name, "modify_half_day_status", 1)
		# N4: a punch at 23:00 is outside the new shift's window, and the day holds
		# Frappe's automatic Absent. The day is left for a person.
		blk = _employee("Blk", COMPANY, WRONG)
		_punch(blk, d2, "09:00")
		_punch(blk, d2, "23:00")
		blk_absent = _absent(blk, d2, auto=True, shift=WRONG).name
		_set_default(blk, RIGHT)
		# m-a: default RIGHT, but assigned to OFF for the period.
		asg = _employee("Asg", COMPANY, RIGHT)
		frappe.get_doc({"doctype": "Shift Assignment", "employee": asg, "shift_type": OFF, "company": COMPANY,
		                "start_date": d1, "end_date": d3, "status": "Active"}).insert().submit()
		_punch(asg, d1, "09:05")
		_punch(asg, d1, "18:10")
		frappe.db.commit()

		# ── 0. preview: nothing written to the database; the list is frozen ──
		before = (frappe.db.count("Attendance"), frappe.db.count("Employee Checkin", {"shift": WRONG}))
		out = fix.preview(COMPANY, frm, to, start=start)
		self.assertEqual(before, (frappe.db.count("Attendance"),
		                          frappe.db.count("Employee Checkin", {"shift": WRONG})))
		scope = fix._state()["scope"]
		people = {abh, hand, fixadm, grpa, same, blk, asg} | set(kept_absent)
		self.assertEqual(set(scope["employees"]), people)
		self.assertEqual(out["retag_punches"], 4)        # ABH days 1-2
		self.assertEqual(out["cancel"], 3)               # ABH d1, d2 + GRPA's automatic Absent
		self.assertEqual(out["skipped"], 8)              # ... and BLK's day, left for a person
		self.assertEqual(out["blocked_days"], 1)
		self.assertEqual(out["same_timing_people"], 1)
		self.assertNotIn(outsider, scope["employees"])
		# N1: the person outside the list on the formerly-off shift is named and counted.
		self.assertEqual(out["outside_people"], [offout])
		self.assertGreater(out["absent_outside_list"], 0)
		self.assertEqual(out["half_day_rows"], 1)
		# N2: a narrower list names who it drops.
		narrow = sorted(people - {same})
		self.assertEqual(fix.preview(COMPANY, frm, to, employees=narrow, start=start)["dropped"], [same])
		fix.preview(COMPANY, frm, to, start=start)

		# ── 1. pause ──
		fix.pause(COMPANY, frm, to)
		self.assertEqual(fix._enabled([RIGHT, WRONG, OFF, SAME]), [])
		self.assertEqual(fix.pause(COMPANY, frm, to)["paused"], 0)
		with self.assertRaises(frappe.ValidationError):   # the list may not change after pause
			fix.preview(COMPANY, frm, to, employees=narrow, start=start)

		# A real submitted slip refuses that person.
		slip = _slip(abh, frm, to)
		self.assertEqual(fix._paid(COMPANY, frm, to), {abh})
		self.assertEqual(fix.preview(COMPANY, frm, to, start=start)["refused"], 1)
		self.assertEqual(fix._state()["scope"]["cancel"], 1)   # only GRPA's
		with self.assertRaises(frappe.ValidationError):
			fix.enable_and_mark(COMPANY, frm, to, half_day_rows=1, absent_outside_list=out["absent_outside_list"])
		frappe.db.delete("Salary Slip", {"name": slip})
		frappe.db.commit()

		# ── 2. set_start, then preview again ──
		fix.set_start(COMPANY, frm, to, date=start)
		self.assertEqual(getdate(frappe.db.get_value("Shift Type", OFF, "process_attendance_after")), start)
		self.assertEqual(str(fix._state()["shifts"][OFF]["process_attendance_after"]), str(d3))
		self.assertEqual(fix.set_start(COMPANY, frm, to, date=start)["changed"], 0)
		again = fix.preview(COMPANY, frm, to, start=start)
		self.assertEqual(again["cancel"], 3)
		self.assertGreater(again["absent_people"], 0)
		ack = {"half_day_rows": again["half_day_rows"], "absent_outside_list": again["absent_outside_list"]}

		# Retag before cancel (the plan's first order) cannot move linked punches.
		self.assertEqual(fix.retag(COMPANY, frm, to)["still_linked"], 4)

		# ── 3. cancel_wrong: refuses if the count moved since preview ──
		state = fix._state()
		state["scope"]["cancel"] = 99
		fix._save_state(state)
		with self.assertRaises(frappe.ValidationError):
			fix.cancel_wrong(COMPANY, frm, to)
		state["scope"]["cancel"] = 3
		fix._save_state(state)
		self.assertEqual(fix.cancel_wrong(COMPANY, frm, to)["cancelled"], 3)
		self.assertEqual(_live(abh, d1), [])
		self.assertEqual(len(_live(abh, d3)), 1)          # leave
		self.assertEqual(len(_live(hand, d1)), 1)         # edited by a person
		self.assertEqual(_live(fixadm, d1)[0].name, fix_row)   # B1: corrected as Administrator
		for e, name in kept_absent.items():               # B1: amended, by hand, request, confirmed
			self.assertEqual(_live(e, d1)[0].name, name)
		self.assertEqual(_live(grpa, d3), [])
		self.assertEqual(_live(blk, d2)[0].name, blk_absent)   # N4: left for a person
		self.assertEqual(fix.cancel_wrong(COMPANY, frm, to)["cancelled"], 0)

		# ── 4. retag ──
		abh_d1 = frappe.get_all("Employee Checkin", filters={"employee": abh, "time": ("like", f"{d1}%")},
		                        fields=["name", "shift", "shift_start", "shift_end"])
		with self.assertRaises(frappe.ValidationError):   # not before retag
			fix.enable_and_mark(COMPANY, frm, to, **ack)
		self.assertEqual(fix.retag(COMPANY, frm, to)["retagged"], 4)
		for p in abh_d1:
			now = frappe.db.get_value("Employee Checkin", p.name, ["shift", "shift_start", "shift_end"], as_dict=True)
			self.assertEqual((now.shift, str(now.shift_start), str(now.shift_end)),
			                 (RIGHT, f"{d1} 10:00:00", f"{d1} 19:00:00"))
		self.assertEqual(fix.retag(COMPANY, frm, to)["retagged"], 0)

		# ── 5. enable_and_mark ──
		count = frappe.db.count("Attendance")
		with self.assertRaises(frappe.ValidationError):   # nothing acknowledged
			fix.enable_and_mark(COMPANY, frm, to)
		with self.assertRaises(frappe.ValidationError):   # a wrong half-day number above 0
			fix.enable_and_mark(COMPANY, frm, to, half_day_rows=0, absent_outside_list=ack["absent_outside_list"])
		with self.assertRaises(frappe.ValidationError):   # a wrong outside Absent number
			fix.enable_and_mark(COMPANY, frm, to, half_day_rows=1, absent_outside_list=0)
		# N3: a shift whose last sync is empty and will not move: refused BEFORE marking.
		frappe.db.set_value("Shift Type", SAME, {"last_sync_of_checkin": None, "auto_update_last_sync": 0})
		with self.assertRaises(frappe.ValidationError):
			fix.enable_and_mark(COMPANY, frm, to, **ack)
		frappe.db.set_value("Shift Type", SAME, {"last_sync_of_checkin": now_datetime(), "auto_update_last_sync": 1})
		# m-b: set_start not run with the frozen date.
		frappe.db.set_value("Shift Type", RIGHT, "process_attendance_after", add_days(d1, -2))
		with self.assertRaises(frappe.ValidationError):
			fix.enable_and_mark(COMPANY, frm, to, **ack)
		frappe.db.set_value("Shift Type", RIGHT, "process_attendance_after", d1)
		frappe.db.commit()
		self.assertEqual(frappe.db.count("Attendance"), count)   # the refusals marked nothing
		kept_leave = _live(abh, d3)[0].name
		absent_before = frappe.db.count("Attendance", {"docstatus": 1, "status": "Absent", "company": COMPANY})
		fix.enable_and_mark(COMPANY, frm, to, **ack)
		# M2: the preview named exactly the Absent days the job then made.
		self.assertEqual(frappe.db.count("Attendance", {"docstatus": 1, "status": "Absent", "company": COMPANY})
		                 - absent_before, again["absent"])
		# M3: nobody outside the frozen list was touched.
		self.assertEqual(frappe.db.count("Attendance", {"employee": outsider}), 0)
		for d in (d1, d2):
			row = _live(abh, d)
			self.assertEqual([(r.shift, r.status, r.alvoraa_attendance_percent) for r in row],
			                 [(RIGHT, "Present", 100)])
		self.assertEqual(_live(abh, d3)[0].name, kept_leave)
		self.assertEqual(set(frappe.get_all("Employee Checkin", filters={"employee": abh, "time": ("like", f"{d3}%")},
		                                    pluck="attendance")), {kept_leave})
		for d in (d1, d2, d3):
			self.assertEqual([(r.shift, r.status) for r in _live(grpa, d)], [(OFF, "Present")])
		# M1: the same-timing day is Present, not Absent with its punches flagged skip.
		self.assertEqual([r.status for r in _live(same, d1)], ["Present"])
		self.assertEqual(frappe.get_all("Employee Checkin", filters={"employee": same}, pluck="skip_auto_attendance"),
		                 [0, 0])
		# N4: the day left for a person is untouched; its punches are not linked.
		self.assertEqual([r.name for r in _live(blk, d2)], [blk_absent])
		self.assertEqual(set(frappe.get_all("Employee Checkin", filters={"employee": blk}, pluck="attendance")), {None})
		# N2: the formerly-off shift is on from the day after the period; the shifts
		# that were on get their old start back; the old-punch shift is put back.
		shift_now = lambda s: frappe.db.get_value(  # noqa: E731
			"Shift Type", s, ["enable_auto_attendance", "process_attendance_after"])
		self.assertEqual(shift_now(OFF), (1, add_days(d3, 1)))
		self.assertEqual(shift_now(RIGHT), (1, old_start))
		self.assertEqual(shift_now(WRONG), (1, old_start))
		self.assertEqual(shift_now(SAME), (0, d1))
		with self.assertRaises(frappe.ValidationError):   # a second run refuses: shifts are on
			fix.enable_and_mark(COMPANY, frm, to, **ack)
		# N1: Frappe's hourly job on the formerly-off shift does to the person outside
		# the list exactly what preview said.
		from hrms.hr.doctype.shift_type.shift_type import update_last_sync_of_checkin
		update_last_sync_of_checkin()
		frappe.get_doc("Shift Type", OFF).process_auto_attendance()
		self.assertEqual(frappe.db.count("Attendance", {"employee": offout, "status": "Absent", "docstatus": 1}),
		                 again["absent_outside_list"])
		self.assertEqual(frappe.db.get_value("Attendance", half.name, "half_day_status"), "Absent")

		# ── 6. verify ──
		v = fix.verify(COMPANY, frm, to, reds_for=[abh])
		self.assertEqual(v["duplicates"], 0)
		self.assertEqual(v["days_punched_no_attendance"], 0)
		self.assertEqual(v["wrong_tag_unlinked"], 0)
		self.assertEqual(v["wrong_tag_on_kept_days"], 6)   # ABH leave, HAND, FIXADM
		self.assertEqual(v["left_for_a_person"], 1)                    # N4: shown, not hidden
		self.assertEqual(v["absent_on_days_with_a_punch"], 5)          # the four kept Absents and BLK
		self.assertEqual(v["skip_flagged_punches_on_absent_days"], 8)  # Frappe flags their punches
		self.assertEqual(v[f"reds_before_free_{abh}"], 0)

		# ── 7. undo ──
		u = fix.undo()
		self.assertEqual(u["linked"], 4)
		self.assertEqual(frappe.db.get_value("Shift Type", OFF, "enable_auto_attendance"), 0)
		self.assertEqual(getdate(frappe.db.get_value("Shift Type", OFF, "process_attendance_after")), d3)
		frappe.get_doc("Attendance", _live(abh, d1)[0].name).cancel()
		frappe.db.commit()
		fix.undo()
		for p in abh_d1:
			now = frappe.db.get_value("Employee Checkin", p.name, ["shift", "shift_start", "shift_end"], as_dict=True)
			self.assertEqual((now.shift, now.shift_start, now.shift_end), (WRONG, p.shift_start, p.shift_end))
