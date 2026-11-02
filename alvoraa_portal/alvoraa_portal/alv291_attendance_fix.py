"""ALV-291: a one-time, preview-first fix of a company's attendance for a period.

Built for DTC's October 2026. Run by hand, one step at a time, from
`bench --site <site> execute alvoraa_portal.alv291_attendance_fix.<step>`.
The runbook is docs/slices/alv-291-attendance-fix/runbook.md.

NOT WEB-CALLABLE. Nothing here is whitelisted, so no browser or API call can
reach it, and every step refuses anyone but Administrator. No step uses
ignore_permissions: Administrator has the rights already.

THE ORDER, and why, from Frappe HR's own code (hrms/hr/doctype):

  preview -> pause -> set_start -> preview again -> cancel_wrong -> retag
  -> enable_and_mark -> verify. undo puts back shift settings and punch tags.

- preview works out the people (punches with no attendance, or punches on a
  shift that is not theirs), prints them and FREEZES the list in the state
  file. Every later step acts on that list only, and refuses without it.
- pause first. The hourly scheduler marks attendance on every switched-on
  shift, and would re-mark a day the moment it is freed.
- cancel BEFORE retag. EmployeeCheckin.fetch_shift only re-tags a punch whose
  `attendance` is empty. Cancelling unlinks it (Attendance.on_cancel).
- enable_and_mark runs Frappe's own ShiftType._process, limited to the list,
  in two passes: every shift's punches first, then the Absent days. Absent
  first would block a punch on a same-hours shift and flag it skip.
- last_sync_of_checkin is the CEILING (shift_actual_end < last_sync). It is
  never written here; the run uses the value Frappe's hourly step would give.

Every step is safe to run twice, prints its counts, commits in batches, and
saves what it changed to sites/<site>/alv291_before.json for undo. The console
shows employee id and name only, never punch times.
"""

import json
import os
import time
from datetime import datetime, timedelta

import frappe
from frappe.utils import add_days, get_datetime, get_time, getdate, now_datetime, time_diff_in_seconds

STATE_FILE = "alv291_before.json"
START = "2026-10-01"
BATCH = 100
PAUSE_SECONDS = 2
SYSTEM_USERS = {"Administrator"}
# Frappe's own words on an Absent it made because a day had no punch.
AUTO_ABSENT_COMMENT = "Employee was marked Absent due to missing Employee Checkins."
# A row the job makes is saved and submitted in one go. One changed later was
# changed by somebody, even when they were logged in as Administrator.
CHANGED_AFTER_SECONDS = 300
PUNCH_FIELDS = ["shift", "shift_start", "shift_end", "shift_actual_start", "shift_actual_end",
                "offshift", "overtime_type"]


# ── small shared pieces ────────────────────────────────────────────────────


def _admin():
	if frappe.session.user != "Administrator":
		frappe.throw("Refused: only Administrator may run this, from bench execute.")


def _list(value):
	if not value:
		return []
	if isinstance(value, str):
		return [v.strip() for v in value.split(",") if v.strip()]
	return list(value)


def _state_path():
	return frappe.get_site_path(STATE_FILE)


def _state():
	path = _state_path()
	if os.path.exists(path):
		with open(path) as f:
			return json.load(f)
	return {"shifts": {}, "punches": {}, "cancelled": []}


def _save_state(state):
	path = _state_path()
	with open(path + ".tmp", "w") as f:
		json.dump(state, f, indent=1, default=str)
	os.replace(path + ".tmp", path)


def _scope(company, from_date, to_date):
	"""The frozen list from the last preview. No list, or another period: refuse."""
	scope = _state().get("scope")
	if not scope or [scope["company"], scope["from_date"], scope["to_date"]] != [
		company, str(from_date), str(to_date)]:
		frappe.throw("Refused: no frozen list of people for this company and period. Run preview first.")
	return scope


def _pause_between_batches(done):
	if done % BATCH == 0:
		frappe.db.commit()
		time.sleep(PAUSE_SECONDS)


def _period(from_date, to_date):
	return ("between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"])


def _employees(company, employees=None):
	filters = {"company": company}
	if employees:
		filters["name"] = ("in", _list(employees))
	return {
		e.name: e
		for e in frappe.get_all(
			"Employee",
			filters=filters,
			fields=["name", "employee_name", "default_shift", "status", "employment_type", "designation"],
			limit_page_length=0,
		)
	}


def _paid(company, from_date, to_date):
	"""Employees with a submitted salary slip overlapping the period. Refused."""
	return set(
		frappe.get_all(
			"Salary Slip",
			filters={
				"docstatus": 1,
				"company": company,
				"start_date": ("<=", to_date),
				"end_date": (">=", from_date),
			},
			pluck="employee",
		)
	)


def _target_shifts(company, from_date):
	"""Shifts a person is on: an active employee's default, or an active assignment."""
	emps = _employees(company)
	names = {e.default_shift for e in emps.values() if e.default_shift and e.status == "Active"}
	if emps:
		names |= set(frappe.get_all(
			"Shift Assignment",
			filters={"employee": ("in", list(emps)), "docstatus": 1, "status": "Active"},
			or_filters=[["end_date", ">=", from_date], ["end_date", "is", "not set"]],
			pluck="shift_type", distinct=True))
	return names


def _in_use_shifts(company, from_date, to_date):
	"""Target shifts, plus any shift still on a punch in the period."""
	names = _target_shifts(company, from_date)
	emps = list(_employees(company))
	if emps:
		names |= set(frappe.get_all(
			"Employee Checkin",
			filters={"employee": ("in", emps), "time": _period(from_date, to_date), "shift": ("is", "set")},
			pluck="shift", distinct=True))
	return sorted(names)


def _enabled(shifts):
	return [s for s in shifts if frappe.db.get_value("Shift Type", s, "enable_auto_attendance")]


def _refuse_while_enabled(shifts, step):
	on = _enabled(shifts)
	if on:
		frappe.throw(
			f"Refused: {len(on)} shift(s) still have auto attendance on ({', '.join(on)}). "
			f"The scheduler would undo {step} within the hour. Run pause first."
		)


def _remember_shift(state, doc):
	state["shifts"].setdefault(
		doc.name,
		{
			"enable_auto_attendance": doc.enable_auto_attendance,
			"process_attendance_after": str(doc.process_attendance_after or "") or None,
		},
	)


def _ceiling(doc):
	"""The last_sync_of_checkin Frappe's hourly step (update_last_sync_of_checkin)
	would give this shift now. Only shifts with auto_update_last_sync ticked move."""
	from hrms.hr.doctype.shift_type.shift_type import get_actual_shift_end

	last = get_datetime(doc.last_sync_of_checkin) if doc.last_sync_of_checkin else None
	if doc.auto_update_last_sync:
		now = now_datetime()
		end = get_actual_shift_end(doc, now)
		if end < now and (not last or last < end):
			last = end + timedelta(minutes=1)
	return last


def _was_off(state, doc):
	"""Off before pause (from the saved values), or off now if pause has not run."""
	return not int(state["shifts"].get(doc.name, {}).get("enable_auto_attendance", doc.enable_auto_attendance))


def _absent_dates(doc, emp, punch_days, marked):
	"""The days Frappe's mark_absent_for_dates_with_no_attendance would mark,
	with its own per-day check that this shift is the person's shift that day."""
	from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift

	out = []
	for d in doc.get_dates_for_attendance(emp):
		# A day with a punch, or with attendance on another shift (Frappe's
		# overlap check refuses it), gets no Absent.
		if getdate(d) in punch_days or (emp, str(getdate(d))) in marked:
			continue
		shift = get_employee_shift(emp, datetime.combine(getdate(d), get_time(doc.start_time)), True)
		if shift and shift.shift_type.name == doc.name:
			out.append(d)
	return out


def _outside(people, shifts, after):
	"""What Frappe's hourly job does, once these formerly-off shifts are on, to
	everyone on them who is NOT in the list: Absent days from `after`, and the
	half-day rows it may set to Absent (any month)."""
	absent, outsiders = {}, set()
	for s in shifts:
		doc = frappe.get_doc("Shift Type", s)
		doc.process_attendance_after = after
		doc.last_sync_of_checkin = _ceiling(doc)
		emps = set(doc.get_assigned_employees(getdate(after), True)) - set(people)
		outsiders |= emps
		if not emps or not doc.last_sync_of_checkin:
			continue
		punch_days = {}
		for x in frappe.get_all("Employee Checkin", filters={"employee": ("in", list(emps)), "time": (">=", after)},
		                        fields=["employee", "time"], limit_page_length=0):
			punch_days.setdefault(x.employee, set()).add(getdate(x.time))
		marked = {(a.employee, str(a.attendance_date)) for a in frappe.get_all(
			"Attendance", filters={"employee": ("in", list(emps)), "docstatus": 1, "attendance_date": (">=", after)},
			fields=["employee", "attendance_date"], limit_page_length=0)}
		for emp in emps:
			n = len(_absent_dates(doc, emp, punch_days.get(emp, ()), marked))
			if n:
				absent[emp] = absent.get(emp, 0) + n
	return absent, outsiders, _half_day_rows(outsiders)


def _half_day_rows(people):
	"""Half Day rows Frappe's mark_absent_for_half_day_dates may set to Absent for
	the other half. It reads them with no start date and no docstatus filter."""
	if not people:
		return []
	return frappe.get_all(
		"Attendance",
		filters={"employee": ("in", list(people)), "status": "Half Day", "modify_half_day_status": 1},
		fields=["name", "employee", "attendance_date"],
		limit_page_length=0,
	)


# ── the plan: what is wrong, and what is safe to change ────────────────────


def _wrong_punches(company, from_date, to_date, employees=None, include_same_timings=0):
	"""Punches whose shift is not the one Frappe would give them today.

	The target is exactly what EmployeeCheckin.fetch_shift would set: the
	person's Shift Assignment for that time, otherwise their default shift.
	Only punches tagged differently from the default shift are asked, to keep
	the query count bounded on a month of punches.
	"""
	from hrms.hr.doctype.shift_assignment.shift_assignment import get_actual_start_end_datetime_of_shift

	emps = _employees(company, employees)
	timings = {
		s.name: (str(s.start_time), str(s.end_time))
		for s in frappe.get_all("Shift Type", fields=["name", "start_time", "end_time"])
	}
	out = {"retag": [], "same_timings": [], "blocked_days": set()}
	if not emps:
		return out
	rows = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": ("in", list(emps)),
			"time": _period(from_date, to_date),
			"offshift": 0,
			"skip_auto_attendance": 0,
			"shift": ("is", "set"),
		},
		fields=["name", "employee", "time", "attendance"] + PUNCH_FIELDS,
		order_by="employee asc, time asc",
		limit_page_length=0,
	)
	for r in rows:
		if r.shift == emps[r.employee].default_shift:
			continue
		day = (r.employee, str(getdate(r.time)))
		target = get_actual_start_end_datetime_of_shift(r.employee, get_datetime(r.time), True)
		if not target:
			# fetch_shift would make it off-shift, and it would never count.
			out["blocked_days"].add(day)
			continue
		r.target = target.shift_type.name
		if r.target == r.shift:
			continue
		r.day = day
		r.differs = timings.get(r.shift) != timings.get(r.target)
		if r.differs or int(include_same_timings or 0):
			out["retag"].append(r)
		else:
			out["same_timings"].append(r)
	# A day with one punch that would go off-shift is left whole, for a person.
	out["retag"] = [r for r in out["retag"] if r.day not in out["blocked_days"]]
	return out


def _attendance(company, from_date, to_date, employees=None):
	filters = {
		"docstatus": 1,
		"company": company,
		"attendance_date": ("between", [from_date, to_date]),
	}
	if employees:
		filters["employee"] = ("in", _list(employees))
	return frappe.get_all(
		"Attendance",
		filters=filters,
		fields=[
			"name", "employee", "employee_name", "attendance_date", "status", "shift",
			"leave_application", "leave_type", "attendance_request", "amended_from",
			"owner", "modified_by", "creation", "modified", "alvoraa_held_confirmed",
		],
		limit_page_length=0,
	)


def _unlinked_days(employees, from_date, to_date):
	if not employees:
		return set()
	return {
		(p.employee, str(getdate(p.time)))
		for p in frappe.get_all(
			"Employee Checkin",
			filters={"employee": ("in", list(employees)), "time": _period(from_date, to_date),
			         "attendance": ("is", "not set"), "skip_auto_attendance": 0, "offshift": 0},
			fields=["employee", "time"],
			limit_page_length=0,
		)
	}


def _derive_people(company, from_date, to_date, employees=None):
	"""The people this fix is for: a punch with no attendance that day, or a
	punch on a shift that is not theirs (any timings)."""
	emps = list(_employees(company, employees))
	wrong = _wrong_punches(company, from_date, to_date, emps, include_same_timings=1)
	people = {r.employee for r in wrong["retag"]} | {e for e, _d in wrong["blocked_days"]}
	marked = {(a.employee, str(a.attendance_date)) for a in _attendance(company, from_date, to_date, emps)}
	people |= {e for e, d in _unlinked_days(emps, from_date, to_date) if (e, d) not in marked}
	return sorted(people)


def _plan(company, from_date, to_date, people, include_same_timings=0):
	"""What cancel_wrong and retag would do for these people. Writes nothing."""
	paid = _paid(company, from_date, to_date)
	if not people:
		return {"paid": paid, "retag": [], "retag_kept_days": 0, "same_timings": [],
		        "blocked_days": set(), "cancel": [], "skipped": []}
	wrong = _wrong_punches(company, from_date, to_date, people, include_same_timings)
	retag_days = {r.day for r in wrong["retag"]}
	linked = {r.attendance for r in wrong["retag"] if r.attendance}
	unlinked_days = _unlinked_days(people, from_date, to_date)

	rows = _attendance(company, from_date, to_date, people)
	auto_absent = set(frappe.get_all(
		"Comment",
		filters={"reference_doctype": "Attendance", "content": ("like", f"%{AUTO_ABSENT_COMMENT}%"),
		         "reference_name": ("in", [a.name for a in rows if a.status == "Absent"] or [""])},
		pluck="reference_name"))

	cancel, skipped = [], []
	for a in rows:
		day = (a.employee, str(a.attendance_date))
		absent_badged = a.status == "Absent" and day in unlinked_days
		if day not in retag_days and not absent_badged:
			continue
		if day in wrong["blocked_days"]:
			why = "left for a person (a punch is outside the new shift's window)"
		elif a.employee in paid:
			why = "submitted salary slip"
		elif a.amended_from:
			why = "corrected by hand (amended)"
		elif a.leave_application or a.leave_type or a.status == "On Leave":
			why = "leave"
		elif a.attendance_request:
			why = "attendance request"
		elif a.alvoraa_held_confirmed:
			why = "confirmed by a manager"
		elif a.owner not in SYSTEM_USERS or a.modified_by not in SYSTEM_USERS:
			why = "made or changed by a person"
		elif time_diff_in_seconds(a.modified, a.creation) > CHANGED_AFTER_SECONDS:
			why = "changed after it was made"
		elif a.name in linked or (absent_badged and a.name in auto_absent):
			# Proof the job made it: it holds the job's punches, or it carries
			# Frappe's own "missing Employee Checkins" comment.
			cancel.append(a)
			continue
		else:
			why = "not proven to be automatic"
		a.why = why
		skipped.append(a)

	kept_days = {(a.employee, str(a.attendance_date)) for a in skipped}
	retag = [r for r in wrong["retag"] if r.employee not in paid and r.day not in kept_days]
	return {
		"paid": paid,
		"retag": retag,
		"retag_kept_days": len(wrong["retag"]) - len(retag),
		"same_timings": wrong["same_timings"],
		"blocked_days": wrong["blocked_days"],
		"cancel": cancel,
		"skipped": skipped,
	}


# ── step 0 ─────────────────────────────────────────────────────────────────


def preview(company, from_date, to_date, employees=None, start=START, include_same_timings=0):
	"""Writes nothing to the database. Prints every change, and freezes the list
	of people in the state file for the later steps."""
	_admin()
	from_date, to_date = str(from_date), str(to_date)
	people = _derive_people(company, from_date, to_date, employees)
	state = _state()
	old = state.get("scope") or {}
	if state["shifts"] and old.get("from_date") == from_date and old.get("employees") != people:
		# pause has run: the list the later steps rely on may not move under them.
		frappe.throw(f"Refused: pause has run, and the people differ from the frozen list. Added:"
		             f" {sorted(set(people) - set(old['employees']))}; removed:"
		             f" {sorted(set(old['employees']) - set(people))}. Pass employees= the frozen list, or undo first.")
	p = _plan(company, from_date, to_date, people, include_same_timings)
	emps = _employees(company)
	label = lambda emp: f"{emp} {emps[emp].employee_name if emp in emps else ''}".strip()  # noqa: E731

	print(f"\n== ALV-291 PREVIEW · {company} · {from_date} to {to_date} · nothing written to the database ==")
	print(f"\nPEOPLE ({len(people)}): punches with no attendance, or punches on another shift."
	      " Every later step acts on these people only.")
	print("   " + ", ".join(people))
	dropped = []
	if employees:
		dropped = sorted(set(_derive_people(company, from_date, to_date)) - set(people))
		print(f"\nDROPPED, found by preview but not in your list ({len(dropped)}). The job will NOT mark their"
		      " October; fix those days by Attendance Request:")
		for e in dropped:
			print("  ", label(e))
		missing = sorted(set(_list(employees)) - set(people))
		if missing:
			print(f"   In your list but nothing to fix ({len(missing)}): {', '.join(missing)}")
	if p["paid"] & set(people):
		print(f"\nREFUSED, submitted salary slip in the period ({len(p['paid'] & set(people))}):")
		for e in sorted(p["paid"] & set(people)):
			print("  ", label(e))

	print(f"\nRETAG (step retag): {len(p['retag'])} punches, old tag -> shift Frappe gives today")
	per = {}
	for r in p["retag"]:
		k = (r.employee, r.shift, r.target, r.differs)
		per[k] = per.get(k, 0) + 1
	for (emp, old, new, differs), n in sorted(per.items()):
		print(f"   {label(emp)}: {n} punches  {old} -> {new}  {'TIMINGS DIFFER' if differs else 'same timings'}")
	same_people = sorted({r.employee for r in p["same_timings"]})
	print(f"   Not retagged, same timings ({len(p['same_timings'])} punches, {len(same_people)} people): "
	      + ", ".join(same_people))
	if p["retag_kept_days"]:
		print(f"   Not retagged, day kept or person refused: {p['retag_kept_days']} punches")
	if p["blocked_days"]:
		print(f"   LEFT FOR A PERSON, a punch would fall outside the new shift's window: {len(p['blocked_days'])} days")
		for emp, day in sorted(p["blocked_days"]):
			print(f"      {label(emp)} {day}")

	print(f"\nCANCEL (step cancel_wrong): {len(p['cancel'])} attendance records")
	per = {}
	for a in p["cancel"]:
		per[a.employee] = per.get(a.employee, 0) + 1
	for emp, n in sorted(per.items()):
		print(f"   {label(emp)}: {n}")
	print(f"   SKIPPED, kept as they are: {len(p['skipped'])}")
	for a in sorted(p["skipped"], key=lambda a: (a.employee, a.attendance_date)):
		print(f"      {a.name} {label(a.employee)} {a.attendance_date}: {a.why}")

	# What enable_and_mark would do, for these people only.
	targets = _target_shifts(company, from_date)
	retag_to = {r.name: r.target for r in p["retag"]}
	cancelled = {a.name for a in p["cancel"]}
	kept = {(a.employee, str(a.attendance_date)) for a in frappe.get_all(
		"Attendance", filters={"docstatus": 1, "attendance_date": (">=", start), "employee": ("in", people or [""])},
		fields=["name", "employee", "attendance_date"], limit_page_length=0) if a.name not in cancelled}
	punches = frappe.get_all(
		"Employee Checkin",
		filters={"time": (">=", start), "skip_auto_attendance": 0, "offshift": 0, "employee": ("in", people or [""])},
		fields=["name", "employee", "time", "shift", "attendance", "shift_actual_end"],
		limit_page_length=0)
	punch_days = {}
	for x in punches:
		punch_days.setdefault(x.employee, set()).add(getdate(x.time))

	print(f"\nSHIFTS: {len(_in_use_shifts(company, from_date, to_date))} in use, paused by pause."
	      f" enable_and_mark switches ON these {len(targets)} (someone's shift) and leaves the rest as they were:")
	absent_per, new_days, flagged = {}, set(), 0
	for s in _in_use_shifts(company, from_date, to_date):
		doc = frappe.get_doc("Shift Type", s)
		ceiling = _ceiling(doc)
		print(f"   {s}{'' if s in targets else ' (only on old punches: punches marked, NOT switched on)'}:"
		      f" auto={doc.enable_auto_attendance} after={doc.process_attendance_after}"
		      f" last_sync={doc.last_sync_of_checkin or 'EMPTY'} auto_update_last_sync={doc.auto_update_last_sync}"
		      + ("" if ceiling else "  WARNING: last_sync is empty and will not move - marks NOTHING")
		      + ("" if not ceiling or ceiling >= get_datetime(f"{add_days(to_date, 1)} 00:00:00")
		         else f"  WARNING: ceiling {ceiling} is before the end of the period"))
		if not ceiling:
			continue
		for x in punches:
			if retag_to.get(x.name, x.shift) != s or (x.attendance and x.attendance not in cancelled):
				continue
			if not x.shift_actual_end or get_datetime(x.shift_actual_end) >= ceiling:
				continue
			day = (x.employee, str(getdate(x.time)))
			if day in p["blocked_days"]:
				continue  # left for a person: enable_and_mark leaves these punches alone
			if day in kept:
				flagged += 1  # Frappe flags these skip: the day already has attendance
			else:
				new_days.add(day)
		if s not in targets:
			continue
		doc.process_attendance_after = start
		doc.last_sync_of_checkin = ceiling
		for emp in set(doc.get_assigned_employees(getdate(start), True)) & set(people):
			n = len(_absent_dates(doc, emp, punch_days.get(emp, ()), kept))
			if n:
				absent_per[emp] = absent_per.get(emp, 0) + n

	print(f"\nNEW DAYS from punches: {len(new_days)}. Punches Frappe will flag skip (day already has attendance): {flagged}")
	print(f"\n!! LOUD WARNING: ABSENT will be marked on {sum(absent_per.values())} working days with no attendance and"
	      f" no punch, from {start}, for {len(absent_per)} people. Agency (Contract) staff and drivers are the"
	      " likely wrong ones. Check every line:")
	for emp, n in sorted(absent_per.items(), key=lambda kv: -kv[1]):
		e = emps.get(emp, frappe._dict())
		print(f"   {label(emp)}: {n} Absent days  [{e.get('employment_type') or '-'} / {e.get('designation') or '-'}]")

	# The formerly-off shifts act on EVERYONE on them from the next hourly run.
	after = str(getdate(add_days(to_date, 1)))
	turning_on = [s for s in targets if _was_off(state, frappe.get_doc("Shift Type", s))]
	out_absent, outsiders, out_half = _outside(people, turning_on, after)
	print(f"\n!! OUTSIDE THE LIST: {len(turning_on)} shifts that were off get switched on: {', '.join(turning_on)}."
	      f" From the next hourly run Frappe acts on EVERYONE on them. {len(outsiders)} people outside the list"
	      f" are on them; {sum(out_absent.values())} Absent days from {after} for {len(out_absent)} of them:")
	for emp in sorted(outsiders):
		e = emps.get(emp, frappe._dict())
		print(f"   {label(emp)}: {out_absent.get(emp, 0)} Absent days"
		      f"  [{e.get('employment_type') or '-'} / {e.get('designation') or '-'}]")

	half = _half_day_rows(people) + out_half
	print(f"\nHALF-DAY ROWS Frappe may set to Absent for the other half (any month, list and outside): {len(half)}")
	for h in half:
		print(f"   {h.name} {label(h.employee)} {h.attendance_date}")
	print(f"   enable_and_mark needs half_day_rows={len(half)} and"
	      f" absent_outside_list={sum(out_absent.values())} to go ahead.")

	state["scope"] = {"company": company, "from_date": from_date, "to_date": to_date,
	                  "employees": people, "include_same_timings": int(include_same_timings or 0),
	                  "start": str(start), "cancel": len(p["cancel"])}
	_save_state(state)
	result = {
		"people": len(people),
		"refused": len(p["paid"] & set(people)),
		"retag_punches": len(p["retag"]),
		"retag_people": len({r.employee for r in p["retag"]}),
		"same_timing_people": len(same_people),
		"blocked_days": len(p["blocked_days"]),
		"cancel": len(p["cancel"]),
		"skipped": len(p["skipped"]),
		"new_days": len(new_days),
		"flagged_skip": flagged,
		"absent": sum(absent_per.values()),
		"absent_people": len(absent_per),
		"half_day_rows": len(half),
		"absent_outside_list": sum(out_absent.values()),
		"outside_people": sorted(outsiders),
		"dropped": dropped,
	}
	print(f"\nTOTALS {result}\nThe list of people is frozen in {_state_path()}.")
	return result


# ── steps 1 and 2: the shift settings ──────────────────────────────────────


def pause(company, from_date, to_date):
	"""Switch auto attendance off on every in-use shift. Saves the old values."""
	_admin()
	state = _state()
	shifts = _in_use_shifts(company, from_date, to_date)
	paused = 0
	for s in shifts:
		doc = frappe.get_doc("Shift Type", s)
		_remember_shift(state, doc)
		_save_state(state)
		if doc.enable_auto_attendance:
			doc.enable_auto_attendance = 0
			doc.save()
			paused += 1
	frappe.db.commit()
	print(f"pause: {paused} switched off, {len(shifts) - paused} were already off. Old values in {_state_path()}")
	return {"shifts": len(shifts), "paused": paused}


def set_start(company, from_date, to_date, date=START):
	"""process_attendance_after = date on the in-use shifts.

	process_attendance_after is the START (the job takes time >= it).
	last_sync_of_checkin is the CEILING (shift_actual_end < it) and is left
	alone: setting it before the period would make the job mark nothing there.
	"""
	_admin()
	shifts = _in_use_shifts(company, from_date, to_date)
	_refuse_while_enabled(shifts, "set_start")
	state = _state()
	changed = 0
	for s in shifts:
		doc = frappe.get_doc("Shift Type", s)
		_remember_shift(state, doc)
		_save_state(state)
		if str(doc.process_attendance_after or "") != str(getdate(date)):
			doc.process_attendance_after = date
			doc.save()
			changed += 1
	frappe.db.commit()
	print(f"set_start: process_attendance_after = {date} on {changed} shifts, {len(shifts) - changed} already had it.")
	return {"shifts": len(shifts), "changed": changed}


# ── step 3: cancel the attendance that is wrong ────────────────────────────


def cancel_wrong(company, from_date, to_date):
	"""Cancel the safe rows only, for the frozen people. Frappe unlinks their punches."""
	_admin()
	scope = _scope(company, from_date, to_date)
	_refuse_while_enabled(_in_use_shifts(company, from_date, to_date), "cancel_wrong")
	p = _plan(company, from_date, to_date, scope["employees"], scope["include_same_timings"])
	if p["cancel"] and len(p["cancel"]) != scope["cancel"]:
		frappe.throw(f"Refused: {len(p['cancel'])} rows to cancel now, but the last preview showed {scope['cancel']}."
		             " Something changed. Run preview again and read it.")
	state = _state()
	done, failed = 0, []
	for a in p["cancel"]:
		frappe.db.savepoint("alv291")
		try:
			frappe.get_doc("Attendance", a.name).cancel()
		except Exception:
			frappe.db.rollback(save_point="alv291")
			failed.append(a.name)
			continue
		if a.name not in state["cancelled"]:
			state["cancelled"].append(a.name)
		done += 1
		if done % BATCH == 0:
			_save_state(state)
		_pause_between_batches(done)
	_save_state(state)
	frappe.db.commit()
	print(f"cancel_wrong: cancelled {done}, skipped {len(p['skipped'])} (see preview for why),"
	      f" refused {len(p['paid'] & set(scope['employees']))} people with a submitted slip, failed {len(failed)}.")
	for name in failed:
		print("   failed:", name)
	return {"cancelled": done, "skipped": len(p["skipped"]),
	        "refused": len(p["paid"] & set(scope["employees"])), "failed": len(failed)}


# ── step 4: retag the punches ──────────────────────────────────────────────


def retag(company, from_date, to_date):
	"""Re-derive each wrong punch's shift the way Frappe HR's bulk_fetch_shift does."""
	_admin()
	scope = _scope(company, from_date, to_date)
	_refuse_while_enabled(_in_use_shifts(company, from_date, to_date), "retag")
	p = _plan(company, from_date, to_date, scope["employees"], scope["include_same_timings"])
	state = _state()
	todo = [r for r in p["retag"] if not r.attendance]
	still_linked = len(p["retag"]) - len(todo)
	for r in todo:
		state["punches"].setdefault(r.name, {f: str(r[f]) if r[f] is not None else None for f in PUNCH_FIELDS})
	_save_state(state)  # before any write, so undo always knows the old tag

	done, wrong_after = 0, []
	for r in todo:
		doc = frappe.get_doc("Employee Checkin", r.name)
		doc.fetch_shift()
		doc.flags.ignore_validate = True
		doc.save()
		if doc.shift != r.target:
			wrong_after.append(r.name)
		done += 1
		_pause_between_batches(done)
	frappe.db.commit()
	print(f"retag: {done} punches retagged for {len({r.employee for r in todo})} people.")
	if still_linked:
		print(f"   NOT retagged: {still_linked} punches still linked to attendance. Run cancel_wrong, then retag again.")
	if wrong_after:
		print(f"   CHECK: {len(wrong_after)} punches did not get the expected shift: {', '.join(wrong_after[:20])}")
	return {"retagged": done, "still_linked": still_linked, "unexpected": len(wrong_after)}


# ── step 5: mark, then switch on ───────────────────────────────────────────


def enable_and_mark(company, from_date, to_date, half_day_rows=None, absent_outside_list=None):
	"""Mark the frozen people with Frappe's own job, then switch the shifts on.

	The job runs while the shifts are still off, on the shift documents in
	memory, with the ceiling Frappe's hourly step would give. Then:
	- a shift that was OFF before pause is switched on from the day after the
	  period, so the hourly job does not redo October for everyone on it;
	- a shift that was ON gets its old start date back, as it was;
	- a shift only on old punches gets its old switch and start date back.
	"""
	from hrms.hr.doctype.shift_type.shift_type import ShiftType

	_admin()
	scope = _scope(company, from_date, to_date)
	people = set(scope["employees"])
	paid = _paid(company, from_date, to_date) & people
	if paid:
		frappe.throw(f"Refused: {len(paid)} of the people have a submitted salary slip in the period.")
	wrong = _wrong_punches(company, from_date, to_date, people, scope["include_same_timings"])
	left = [r for r in wrong["retag"] if not r.attendance]
	if left:
		frappe.throw(f"Refused: {len(left)} punches are still on the wrong shift. Run cancel_wrong and retag first.")
	shifts = _in_use_shifts(company, from_date, to_date)
	_refuse_while_enabled(shifts, "enable_and_mark")
	targets = sorted(_target_shifts(company, from_date))
	state = _state()
	docs = {s: frappe.get_doc("Shift Type", s) for s in shifts}
	# Every check before anything is marked: a shift skipped half way could not
	# be redone once the shifts are on.
	for s, doc in docs.items():
		if str(doc.process_attendance_after or "") != scope["start"]:
			frappe.throw(f"Refused: {s} starts on {doc.process_attendance_after}, not {scope['start']}. Run set_start.")
		doc.last_sync_of_checkin = _ceiling(doc)
		if not doc.last_sync_of_checkin:
			frappe.throw(f"Refused: {s} has an empty last sync that will not move, so nothing would be marked."
			             " See the runbook, 'If step 8 refuses'.")
	after = str(getdate(add_days(to_date, 1)))
	turning_on = [s for s in targets if _was_off(state, docs[s])]
	out_absent, _outsiders, out_half = _outside(people, turning_on, after)
	half = len(_half_day_rows(people)) + len(out_half)
	if half_day_rows is None or int(half_day_rows) != half or absent_outside_list is None \
			or int(absent_outside_list) != sum(out_absent.values()):
		frappe.throw(f"Refused: pass half_day_rows={half} and absent_outside_list={sum(out_absent.values())},"
		             " after reading both lists in preview.")

	blocked = wrong["blocked_days"]
	# Pass 1 marks every shift's punches; pass 2 the Absent days. The other way
	# round, an Absent on the default shift blocks a punch on a same-hours shift
	# and Frappe flags that punch skip for good.
	for absent_pass in (False, True):
		for s in (targets if absent_pass else shifts):
			doc = docs[s]
			doc.get_assigned_employees = (lambda d, on: lambda *a, **k: [
				e for e in ShiftType.get_assigned_employees(d, *a, **k) if on and e in people])(doc, absent_pass)
			logs = [] if absent_pass else [x for x in doc.get_employee_checkins() if x.employee in people
			                               and (x.employee, str(getdate(x.time))) not in blocked]
			started = time.monotonic()
			doc._process(logs)
			frappe.db.commit()
			print(f"   {s}: {'absent pass' if absent_pass else f'{len(logs)} punches'} [{time.monotonic() - started:.1f}s]")

	for s in shifts:
		doc = frappe.get_doc("Shift Type", s)
		old = state["shifts"].get(s, {})
		if s in turning_on:
			doc.enable_auto_attendance = 1
			doc.process_attendance_after = max(after, old.get("process_attendance_after") or after)
		else:
			doc.enable_auto_attendance = 1 if s in targets else old.get("enable_auto_attendance", 0)
			doc.process_attendance_after = old.get("process_attendance_after")
		doc.save()
	frappe.db.commit()
	print(f"enable_and_mark: {len(turning_on)} formerly-off shifts on from {after};"
	      f" {len(targets) - len(turning_on)} shifts back on with their old start date;"
	      f" {len(shifts) - len(targets)} shifts only on old punches put back as they were. Run verify.")
	return {"turned_on": len(turning_on), "back_on": len(targets) - len(turning_on),
	        "put_back": len(shifts) - len(targets)}


# ── step 6: check the result ───────────────────────────────────────────────


def verify(company, from_date, to_date, reds_for=None):
	"""Punches against attendance, for the frozen people. Writes nothing."""
	from alvoraa_portal.payroll_rules_apply import judge, prepare, rule_set_for

	_admin()
	people = _scope(company, from_date, to_date)["employees"]
	emps = _employees(company, people)
	punch_days, all_punch_days, unlinked, skip_on = {}, {}, 0, []
	for x in frappe.get_all(
		"Employee Checkin",
		filters={"employee": ("in", people or [""]), "time": _period(from_date, to_date), "offshift": 0},
		fields=["name", "employee", "time", "attendance", "skip_auto_attendance"],
		limit_page_length=0,
	):
		day = str(getdate(x.time))
		all_punch_days.setdefault(x.employee, set()).add(day)
		if x.skip_auto_attendance:
			skip_on.append((x.employee, day))
		else:
			punch_days.setdefault(x.employee, set()).add(day)
			unlinked += not x.attendance
	att_days, dups = {}, []
	for a in _attendance(company, from_date, to_date, people):
		days = att_days.setdefault(a.employee, {})
		day = str(a.attendance_date)
		if day in days:
			dups.append((a.employee, day))
		days[day] = a

	missing_total = absent_punched = 0
	for emp in sorted(emps):
		days = att_days.get(emp, {})
		missing = sorted(punch_days.get(emp, set()) - set(days))
		missing_total += len(missing)
		if missing:
			print(f"   {emp} {emps[emp].employee_name}: {len(missing)} days with punches but no attendance: {', '.join(missing)}")
		# A badge-in on a day marked Absent, skip flag or not: kept hand-made
		# Absents show here too, and so would the M1 collision.
		absent = sorted(d for d in all_punch_days.get(emp, ()) if d in days and days[d].status == "Absent")
		absent_punched += len(absent)
		if absent:
			print(f"   {emp} {emps[emp].employee_name}: Absent on {len(absent)} days with a punch: {', '.join(absent)}")
	for emp, day in dups:
		print(f"   DUPLICATE: {emp} {emps[emp].employee_name} {day}")
	skip_on_absent = sum(1 for e, d in skip_on if d in att_days.get(e, {}) and att_days[e][d].status == "Absent")

	wrong = _wrong_punches(company, from_date, to_date, people)
	for emp, day in sorted(wrong["blocked_days"]):
		print(f"   LEFT FOR A PERSON: {emp} {emps[emp].employee_name} {day}")
	result = {
		"left_for_a_person": len(wrong["blocked_days"]),
		"people": len(emps),
		"days_punched_no_attendance": missing_total,
		"absent_on_days_with_a_punch": absent_punched,
		"skip_flagged_punches_on_absent_days": skip_on_absent,
		"duplicates": len(dups),
		"unlinked_punches": unlinked,
		# Punches on a kept day (leave, a person's edit) stay linked to it and keep
		# their old tag on purpose. Only an unlinked wrong punch is still a fault.
		"wrong_tag_unlinked": sum(1 for r in wrong["retag"] if not r.attendance),
		"wrong_tag_on_kept_days": sum(1 for r in wrong["retag"] if r.attendance),
	}

	rule_set = rule_set_for(company)
	for emp in _list(reds_for):
		if not rule_set:
			print(f"   reds for {emp}: not counted, {company} has no pay rule set switched on")
			break
		ctx = prepare(rule_set, from_date, to_date)
		rows = _attendance(company, from_date, to_date, [emp])
		reds = sum(judge(a, ctx).reds for a in rows)
		result[f"reds_before_free_{emp}"] = reds
		print(f"   reds for {emp}: {reds} over {len(rows)} days, BEFORE the {rule_set.free_reds_per_month or 0}"
		      " free reds a month are taken off")
	print("VERIFY", result)
	return result


# ── step 7: undo ───────────────────────────────────────────────────────────


def undo():
	"""Put back punch tags and shift settings from the saved file.

	It does not touch attendance. To bring back a cancelled day: cancel the
	rebuilt row, then amend the cancelled one (runbook).
	"""
	_admin()
	state = _state()
	restored, linked = 0, []
	for name, old in state["punches"].items():
		if not frappe.db.exists("Employee Checkin", name):
			continue
		if frappe.db.get_value("Employee Checkin", name, "attendance"):
			# The rebuilt attendance uses this punch. Restoring its tag under
			# that attendance would make the two disagree.
			linked.append(name)
			continue
		# Written straight to the row: a save would run fetch_shift and put
		# today's shift straight back.
		frappe.db.set_value("Employee Checkin", name, old, update_modified=False)
		restored += 1
		_pause_between_batches(restored)
	for name, old in state["shifts"].items():
		doc = frappe.get_doc("Shift Type", name)
		doc.enable_auto_attendance = old["enable_auto_attendance"]
		doc.process_attendance_after = old["process_attendance_after"]
		doc.save()
	frappe.db.commit()
	print(f"undo: {restored} punch tags and {len(state['shifts'])} shift settings put back.")
	if linked:
		print(f"   NOT restored: {len(linked)} punches are linked to rebuilt attendance. Cancel that attendance,"
		      " then run undo again.")
	print(f"   {len(state['cancelled'])} attendance records were cancelled. To bring one back: cancel the rebuilt"
	      " row for that day, then Amend the cancelled one (runbook).")
	return {"punches": restored, "linked": len(linked), "shifts": len(state["shifts"]),
	        "cancelled": len(state["cancelled"])}
