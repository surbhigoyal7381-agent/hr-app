"""ALV-291: a one-time, preview-first fix of a company's attendance for a period.

Built for DTC's October 2026. Run by hand, one step at a time, from
`bench --site <site> execute alvoraa_portal.alv291_attendance_fix.<step>`.
The runbook is docs/slices/alv-291-attendance-fix/runbook.md.

NOT WEB-CALLABLE. Nothing here is whitelisted, so no browser or API call can
reach it, and every step refuses anyone but Administrator. No step uses
ignore_permissions: Administrator has the rights already.

THE ORDER, and why, from Frappe HR's own code (hrms/hr/doctype):

  preview -> pause -> set_start -> cancel_wrong -> retag -> enable_and_mark -> verify
  undo puts back shift settings and punch tags. It cannot un-cancel attendance.

- pause first. The hourly scheduler marks attendance on every switched-on
  shift, and would re-mark a day the moment it is freed.
- cancel BEFORE retag. EmployeeCheckin.fetch_shift only re-tags a punch whose
  `attendance` is empty. A punch still linked to its old attendance keeps its
  old shift however often it is saved. Cancelling unlinks it (Attendance.on_cancel).
- Frappe never redoes a day that has attendance. Cancelling frees the day.
- last_sync_of_checkin is the CEILING (shift_actual_end < last_sync), never the
  start. It is never set by hand here; see set_start.

Every step is safe to run twice, prints its counts, commits in batches, and
saves what it changed to sites/<site>/alv291_before.json for undo. The console
shows employee id and name only, never punch times or reasons.
"""

import json
import os
import time
from datetime import timedelta

import frappe
from frappe.utils import add_days, get_datetime, getdate, now_datetime

STATE_FILE = "alv291_before.json"
BATCH = 100
PAUSE_SECONDS = 2
# Who the scheduler and bench run as. A row owned or last changed by anybody
# else was made or touched by a person, and is kept.
SYSTEM_USERS = {"Administrator"}
PUNCH_FIELDS = ["shift", "shift_start", "shift_end", "shift_actual_start", "shift_actual_end"]


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


def _pause_between_batches(done):
	if done % BATCH == 0:
		frappe.db.commit()
		time.sleep(PAUSE_SECONDS)


def _employees(company, employees=None):
	filters = {"company": company}
	if employees:
		filters["name"] = ("in", _list(employees))
	return {
		e.name: e
		for e in frappe.get_all(
			"Employee",
			filters=filters,
			fields=["name", "employee_name", "default_shift", "status"],
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


def _in_use_shifts(company, from_date, to_date):
	"""Default shift of an active employee, or the tag of a punch in the period."""
	emps = _employees(company)
	names = {e.default_shift for e in emps.values() if e.default_shift and e.status == "Active"}
	if emps:
		names |= set(
			frappe.get_all(
				"Employee Checkin",
				filters={
					"employee": ("in", list(emps)),
					"time": ("between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]),
					"shift": ("is", "set"),
				},
				pluck="shift",
				distinct=True,
			)
		)
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
	"""The last_sync_of_checkin the shift will have when the job runs.

	Frappe's own scheduler step (update_last_sync_of_checkin) moves it forward
	only for a switched-on shift with auto_update_last_sync ticked.
	"""
	from hrms.hr.doctype.shift_type.shift_type import get_actual_shift_end

	last = get_datetime(doc.last_sync_of_checkin) if doc.last_sync_of_checkin else None
	if doc.auto_update_last_sync:
		now = now_datetime()
		end = get_actual_shift_end(doc, now)
		if end < now and (not last or last < end):
			last = end + timedelta(minutes=1)
	return last


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
			"time": ("between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]),
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
			"name",
			"employee",
			"employee_name",
			"attendance_date",
			"status",
			"shift",
			"leave_application",
			"leave_type",
			"attendance_request",
			"owner",
			"modified_by",
			"alvoraa_held_confirmed",
		],
		limit_page_length=0,
	)


def _plan(company, from_date, to_date, employees=None, include_same_timings=0):
	"""What cancel_wrong and retag would do. Writes nothing."""
	paid = _paid(company, from_date, to_date)
	wrong = _wrong_punches(company, from_date, to_date, employees, include_same_timings)
	retag_days = {r.day for r in wrong["retag"]}
	linked = {r.attendance for r in wrong["retag"] if r.attendance}

	# Absent although badged in: a day with an Absent row and a punch that
	# no attendance uses. Usually the job ran before the punches were right.
	emps = list(_employees(company, employees))
	unlinked_days = set()
	if emps:
		for p in frappe.get_all(
			"Employee Checkin",
			filters={
				"employee": ("in", emps),
				"time": ("between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]),
				"attendance": ("is", "not set"),
				"skip_auto_attendance": 0,
				"offshift": 0,
			},
			fields=["employee", "time"],
			limit_page_length=0,
		):
			unlinked_days.add((p.employee, str(getdate(p.time))))

	cancel, skipped = [], []
	for a in _attendance(company, from_date, to_date, employees):
		day = (a.employee, str(a.attendance_date))
		absent_badged = a.status == "Absent" and day in unlinked_days
		if day not in retag_days and not absent_badged:
			continue
		if a.employee in paid:
			why = "submitted salary slip"
		elif a.leave_application or a.leave_type or a.status == "On Leave":
			why = "leave"
		elif a.attendance_request:
			why = "attendance request"
		elif a.alvoraa_held_confirmed:
			why = "confirmed by a manager"
		elif a.owner not in SYSTEM_USERS or a.modified_by not in SYSTEM_USERS:
			why = "made or changed by a person"
		elif a.name not in linked and not absent_badged:
			why = "no linked punches"
		else:
			cancel.append(a)
			continue
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


def preview(company, from_date, to_date, employees=None, start="2026-09-30", include_same_timings=0):
	"""Writes NOTHING. Prints every change the later steps would make."""
	_admin()
	p = _plan(company, from_date, to_date, employees, include_same_timings)
	names = {e.name: e.employee_name for e in _employees(company).values()}
	label = lambda emp: f"{emp} {names.get(emp, '')}".strip()  # noqa: E731

	print(f"\n== ALV-291 PREVIEW · {company} · {from_date} to {to_date} · nothing written ==")
	if p["paid"]:
		print(f"\nREFUSED, submitted salary slip in the period ({len(p['paid'])}):")
		for e in sorted(p["paid"]):
			print("  ", label(e))

	print(f"\nRETAG (step retag): {len(p['retag'])} punches, old tag -> shift Frappe gives today")
	per = {}
	for r in p["retag"]:
		k = (r.employee, r.shift, r.target, r.differs)
		per[k] = per.get(k, 0) + 1
	for (emp, old, new, differs), n in sorted(per.items()):
		print(f"   {label(emp)}: {n} punches  {old} -> {new}  {'TIMINGS DIFFER' if differs else 'same timings'}")
	same_people = sorted({r.employee for r in p["same_timings"]})
	print(f"   Not retagged, same timings ({len(p['same_timings'])} punches, {len(same_people)} people;"
	      " include_same_timings=1 to add them): " + ", ".join(same_people))
	if p["retag_kept_days"]:
		print(f"   Not retagged, day kept or person refused: {p['retag_kept_days']} punches")
	if p["blocked_days"]:
		print(f"   LEFT FOR A PERSON, a punch would fall outside the new shift's window: "
		      f"{len(p['blocked_days'])} days")
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

	# The shift steps act on whole shifts: everybody on them, not only `employees`.
	shifts = _in_use_shifts(company, from_date, to_date)
	retag_to = {r.name: r.target for r in p["retag"]}
	cancelled = {a.name for a in p["cancel"]}
	kept = {(a.employee, str(a.attendance_date)) for a in frappe.get_all(
		"Attendance", filters={"docstatus": 1, "attendance_date": (">=", start)},
		fields=["name", "employee", "attendance_date"], limit_page_length=0)
		if a.name not in cancelled}
	punches = frappe.get_all(
		"Employee Checkin",
		filters={"time": (">=", start), "skip_auto_attendance": 0, "offshift": 0},
		fields=["name", "employee", "time", "shift", "attendance", "shift_actual_end"],
		limit_page_length=0)
	punch_days = {}
	for x in punches:
		punch_days.setdefault(x.employee, set()).add(getdate(x.time))

	print(f"\nSHIFTS (steps pause, set_start, enable_and_mark) - {len(shifts)} in use."
	      " These steps act on EVERYONE on the shift, not only the people above.")
	print(f"   start = process_attendance_after will become {start}")
	totals = {"new_days": 0, "absent": 0, "absent_on_start_day": 0, "flagged_skip": 0}
	for s in shifts:
		doc = frappe.get_doc("Shift Type", s)
		ceiling = _ceiling(doc)
		new_days, flagged = set(), 0
		for x in punches:
			if retag_to.get(x.name, x.shift) != s:
				continue
			if x.attendance and x.attendance not in cancelled:
				continue
			if not ceiling or not x.shift_actual_end or get_datetime(x.shift_actual_end) >= ceiling:
				continue
			day = (x.employee, str(getdate(x.time)))
			if day in kept:
				flagged += 1  # Frappe flags these skip_auto_attendance=1, day already has attendance
			else:
				new_days.add(day)
		absent = on_start = 0
		if ceiling:
			doc.process_attendance_after = start
			doc.last_sync_of_checkin = ceiling
			for emp in doc.get_assigned_employees(getdate(start), True):
				for d in doc.get_dates_for_attendance(emp):
					if getdate(d) not in punch_days.get(emp, ()):
						absent += 1
						on_start += getdate(d) == getdate(start)
		totals["new_days"] += len(new_days)
		totals["absent"] += absent
		totals["absent_on_start_day"] += on_start
		totals["flagged_skip"] += flagged
		print(f"   {s}\n      now: auto={doc.enable_auto_attendance} after={frappe.db.get_value('Shift Type', s, 'process_attendance_after')}"
		      f" last_sync={doc.last_sync_of_checkin or 'EMPTY'} auto_update_last_sync={doc.auto_update_last_sync}"
		      f"\n      job would mark {len(new_days)} days from punches, ABSENT on {absent} days"
		      f" (of which {on_start} on {start}), flag {flagged} punches skip"
		      + ("" if ceiling else "\n      WARNING: last_sync is empty and will not move - this shift marks NOTHING")
		      + ("" if not ceiling or ceiling >= get_datetime(f"{add_days(to_date, 1)} 00:00:00")
		         else f"\n      WARNING: ceiling {ceiling} is before the end of the period - days after it are not marked"))

	print(f"\n!! LOUD WARNING: once switched on, the job marks ABSENT every working day with no attendance"
	      f" and no punch, from {start} to the ceiling, for everyone on these shifts:"
	      f" {totals['absent']} Absent records (upper bound; {totals['absent_on_start_day']} of them on {start})."
	      " Check this number before running enable_and_mark.")
	result = {
		"refused": len(p["paid"]),
		"retag_punches": len(p["retag"]),
		"retag_people": len({r.employee for r in p["retag"]}),
		"same_timing_people": len(same_people),
		"blocked_days": len(p["blocked_days"]),
		"cancel": len(p["cancel"]),
		"skipped": len(p["skipped"]),
		"shifts": len(shifts),
		**totals,
	}
	print("\nTOTALS", result)
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


def set_start(company, from_date, to_date, date="2026-09-30"):
	"""process_attendance_after = date on the in-use shifts.

	process_attendance_after is the START (the job takes time >= it).
	last_sync_of_checkin is the CEILING (shift_actual_end < it) and is left
	alone: setting it before the period would make the job mark nothing there,
	and Frappe's hourly step moves it forward by itself.
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


def cancel_wrong(company, from_date, to_date, employees=None, include_same_timings=0):
	"""Cancel the safe rows only. Frappe unlinks their punches on cancel."""
	_admin()
	_refuse_while_enabled(_in_use_shifts(company, from_date, to_date), "cancel_wrong")
	p = _plan(company, from_date, to_date, employees, include_same_timings)
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
		state["cancelled"].append(a.name)
		done += 1
		if done % BATCH == 0:
			_save_state(state)
		_pause_between_batches(done)
	_save_state(state)
	frappe.db.commit()
	print(f"cancel_wrong: cancelled {done}, skipped {len(p['skipped'])} (see preview for why),"
	      f" refused {len(p['paid'])} people with a submitted slip, failed {len(failed)}.")
	for name in failed:
		print("   failed:", name)
	return {"cancelled": done, "skipped": len(p["skipped"]), "refused": len(p["paid"]), "failed": len(failed)}


# ── step 4: retag the punches ──────────────────────────────────────────────


def retag(company, from_date, to_date, employees=None, include_same_timings=0):
	"""Re-derive each wrong punch's shift the way Frappe HR's bulk_fetch_shift does."""
	_admin()
	_refuse_while_enabled(_in_use_shifts(company, from_date, to_date), "retag")
	p = _plan(company, from_date, to_date, employees, include_same_timings)
	state = _state()
	todo = [r for r in p["retag"] if not r.attendance]
	still_linked = len(p["retag"]) - len(todo)
	for r in todo:
		state["punches"].setdefault(r.name, {f: str(r[f]) if r[f] else None for f in PUNCH_FIELDS})
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


# ── step 5: switch on and mark ─────────────────────────────────────────────


def enable_and_mark(company, from_date, to_date):
	"""Switch auto attendance on (and leave it on) and run Frappe's own job per shift."""
	from hrms.hr.doctype.shift_type.shift_type import update_last_sync_of_checkin

	_admin()
	paid = _paid(company, from_date, to_date)
	if paid:
		frappe.throw(
			f"Refused: {len(paid)} people have a submitted salary slip in the period. Switching shifts on"
			" marks attendance for everyone on them. Cancel or exclude those slips first."
		)
	shifts = _in_use_shifts(company, from_date, to_date)
	for s in shifts:
		doc = frappe.get_doc("Shift Type", s)
		if not doc.enable_auto_attendance:
			doc.enable_auto_attendance = 1
			doc.save()
	frappe.db.commit()
	# The scheduler's own hourly step, run now: moves the ceiling forward on
	# shifts with auto_update_last_sync ticked. Shifts that sat switched off
	# have a stale ceiling, and would otherwise mark nothing past it.
	update_last_sync_of_checkin()
	frappe.db.commit()

	end = get_datetime(f"{add_days(to_date, 1)} 00:00:00")
	for s in shifts:
		doc = frappe.get_doc("Shift Type", s)
		started = time.monotonic()
		message = doc.process_auto_attendance(is_manually_triggered=1)
		frappe.db.commit()
		last = get_datetime(doc.last_sync_of_checkin) if doc.last_sync_of_checkin else None
		print(f"   {s}: {message or 'nothing to do (check last_sync)'} [{time.monotonic() - started:.1f}s]")
		if not last or last < end:
			print(f"      WARNING: last_sync is {last or 'EMPTY'}, before the end of the period. Days after it are"
			      " NOT marked. Set it by hand only after reading the runbook.")
	print(f"enable_and_mark: {len(shifts)} shifts switched on and processed. Queued jobs need a worker; run verify after.")
	return {"shifts": len(shifts)}


# ── step 6: check the result ───────────────────────────────────────────────


def verify(company, from_date, to_date, employees=None, reds_for=None):
	"""Punches against attendance, per person. Writes nothing."""
	from alvoraa_portal.payroll_rules_apply import judge, prepare, rule_set_for

	_admin()
	emps = _employees(company, employees)
	punch_days, unlinked = {}, 0
	if emps:
		for x in frappe.get_all(
			"Employee Checkin",
			filters={
				"employee": ("in", list(emps)),
				"time": ("between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]),
				"skip_auto_attendance": 0,
				"offshift": 0,
			},
			fields=["employee", "time", "attendance"],
			limit_page_length=0,
		):
			punch_days.setdefault(x.employee, set()).add(str(getdate(x.time)))
			unlinked += not x.attendance
	att = _attendance(company, from_date, to_date, list(emps) if employees else None)
	att_days, dups = {}, []
	for a in att:
		days = att_days.setdefault(a.employee, {})
		day = str(a.attendance_date)
		if day in days:
			dups.append((a.employee, day))
		days[day] = a

	missing_total = 0
	for emp in sorted(emps):
		missing = sorted(punch_days.get(emp, set()) - set(att_days.get(emp, {})))
		missing_total += len(missing)
		if missing:
			print(f"   {emp} {emps[emp].employee_name}: {len(missing)} days with punches but no attendance: {', '.join(missing)}")
	for emp, day in dups:
		print(f"   DUPLICATE: {emp} {emps[emp].employee_name} {day}")

	wrong = _wrong_punches(company, from_date, to_date, employees)
	result = {
		"people": len(emps),
		"attendance": len(att),
		"days_punched_no_attendance": missing_total,
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
		rows = [a for a in _attendance(company, from_date, to_date, [emp])]
		reds = sum(judge(a, ctx).reds for a in rows)
		result[f"reds_{emp}"] = reds
		print(f"   reds for {emp} {emps.get(emp, frappe._dict()).get('employee_name', '')}: {reds} over {len(rows)} days")
	print("VERIFY", result)
	return result


# ── step 7: undo ───────────────────────────────────────────────────────────


def undo():
	"""Put back punch tags and shift settings from the saved file.

	Cancelled attendance CANNOT be un-cancelled. The database backup taken
	before the run is the only way back for those.
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
	print(f"   CANNOT be undone: {len(state['cancelled'])} cancelled attendance records. Restore the backup if"
	      " they are needed.")
	return {"punches": restored, "linked": len(linked), "shifts": len(state["shifts"]),
	        "cancelled_not_undone": len(state["cancelled"])}
