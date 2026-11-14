"""One set of rules for every shift, so the same day cannot pay two amounts (ALV-337).

A Shift Type should differ from its neighbours ONLY in its timings. Everything
else on the record is company policy, and when it varies two people doing the
same thing on the same floor are paid differently. At DTC on 13 Nov 2026, 45
shifts disagreed four ways:

- 20 shifts computed hours from "Every Valid Check-in and Check-out" and 25 from
  "First Check-in and Last Check-out". Over twelve days that was 867 hours of
  difference across 177 people - about 34 minutes each a day.
- seven shifts had no Absent and no Half Day threshold at all, and one of those
  seven was switched on, so a single punch there became a whole present day.
  (Superseded the same day: Surbhi ruled that one punch IS a present day, held
  for the missing time, so the standard is now no hour thresholds on any shift -
  see STANDARD.)
- one shift called half a day six hours while the rest called it 4.5.
- every shift allowed three hours either side of itself. 86 November punches
  landed past that, got no shift, and vanished: the day then held an arrival
  with no departure, scored 0.0 hours, and was marked Absent. 74 of the 86 were
  within half an hour of the cut-off.

WHY FOUR HOURS. A window is where data is CAPTURED, not where policy is applied.
Overtime belongs in approval and in the pay rules; a window that cuts work off
does not prevent overtime, it only hides it and then calls the day absent. Four
hours catches 103 of November's 110 orphaned punches. Five hours catches all
110, and was not chosen: five hours either side of a shift ending at 10 PM
reaches 3 AM, and the day a person holds two shift assignments a punch could be
claimed by the wrong one. The seven punches past four hours are genuinely
exceptional and belong in the correction screen, which reads them correctly
since ALV-315. Frappe refuses a shift whose length plus both windows reaches 24
hours (`validate_circular_shift`); DTC's longest shift is twelve hours, so four
hours each side leaves four hours of headroom.

WHAT THIS NEVER TOUCHES, and why it matters more than what it does:

  enable_auto_attendance   ALV-291's October repair switches the paused shifts
  process_attendance_after back on itself, from the day after its period, and
                           refuses to run at all while any of them is on. If
                           this module switched shifts on, October's repair
                           would refuse, and if it moved the start date,
                           October would be re-processed for everybody on that
                           shift. Those two fields are October's, and the
                           user's. Not this module's.
  start_time, end_time     changing start_time with unmarked punches present is
                           refused by Frappe outright, and the timings are the
                           one thing a shift is allowed to differ in.
  holiday_list, company    tenant data, not policy.

So the order is (changed 13 Nov 2026): October's repair pauses the shifts, THEN
this is applied, then the repair carries on (set_start, preview, cancel, retag,
enable_and_mark). It must come before enable_and_mark: the repair rebuilds days
with whatever thresholds the shifts carry at that moment, and with the old
2-hour one a one-punch day is rebuilt Absent again (the 13 Nov rule says it is a
present day). Applied before `pause` it corrupts nothing, but the repair refuses
until its own `pause` step switches the shifts off again. See ALV-291's runbook,
step 3a.

Saving a Shift Type starts no marking run: the doctype has no `on_update`, and
only the hourly job and the Desk button call `process_auto_attendance`. So this
module changes settings and nothing moves until the next hourly tick.

Every step is reversible. `apply` writes the old values to the site folder first,
and `undo` puts them back.

Read-only first, always:

    bench --site <site> execute alvoraa_portal.shift_standard.preview
    bench --site <site> execute alvoraa_portal.shift_standard.apply
    bench --site <site> execute alvoraa_portal.shift_standard.undo
"""

import json
import os

import frappe
from frappe.utils import get_time

STATE_FILE = "alv337_shift_standard_before.json"

# The policy. A shift may differ from these only if somebody decides it should,
# in which case the decision belongs in this dict with a reason beside it.
STANDARD = {
	# DTC's readers send no log type at all, so alternating entries is the only
	# setting that can pair a day's punches (see dtc-log-type-empty). Already
	# true on all 45 shifts; stated here so a new shift cannot drift.
	"determine_check_in_and_check_out": "Alternating entries as IN and OUT during the same shift",
	# First and last, not every pair. Every pair treats each step out as unpaid,
	# which punishes the honest third punch; first-and-last plus the 40-minute
	# break allowance ALV-326 built lands in the same place without doing that.
	"working_hours_calculation_based_on": "First Check-in and Last Check-out",
	# Surbhi's rule, 13 Nov 2026: a day with at least one punch is NOT an absence.
	# It is present but incomplete - a missing punch - and the pay engine holds it
	# (ATT-06) until somebody confirms the missing time. So Frappe marks Absent only
	# a day with no punch at all, and never Half Day from hours: one punch scores
	# 0.0 hours and any threshold above 0 would call it Absent or Half Day, which
	# would cut base-salary paid days for a day the engine is holding. Short days
	# are measured by the engine from the real punches, not by this status. DTC's
	# own muster roll has no half days either (PP / AA only).
	"working_hours_threshold_for_absent": 0.0,
	"working_hours_threshold_for_half_day": 0.0,
	"begin_check_in_before_shift_start_time": 240,
	"allow_check_out_after_shift_end_time": 240,
}

# Named so a reader can see the omission is deliberate. See the module docstring.
NEVER_TOUCHED = (
	"enable_auto_attendance",
	"process_attendance_after",
	"start_time",
	"end_time",
	"holiday_list",
	"company",
)

FRAPPE_WINDOW_CEILING_MINUTES = 1440


def _state_path():
	return frappe.get_site_path(STATE_FILE)


def _state():
	path = _state_path()
	if os.path.exists(path):
		with open(path) as f:
			return json.load(f)
	return {"shifts": {}}


def _save_state(state):
	path = _state_path()
	with open(path + ".tmp", "w") as f:
		json.dump(state, f, indent=1, default=str)
	os.replace(path + ".tmp", path)


def _admin():
	if frappe.session.user != "Administrator":
		frappe.throw("Refused: run this as Administrator, through bench execute.")


def _shifts(company=None):
	"""Every shift type, with the fields this module reads or writes.

	Shift Type carries no company field in Frappe HR, so `company` narrows by
	the shifts actually in use by that company's people rather than by a column
	that does not exist.
	"""
	names = None
	if company:
		employees = frappe.get_all("Employee", filters={"company": company}, pluck="name")
		names = set(frappe.get_all("Shift Assignment",
		                           filters={"employee": ("in", employees), "docstatus": 1},
		                           pluck="shift_type", distinct=True)) if employees else set()
		names |= set(frappe.get_all("Employee", filters={"company": company, "default_shift": ("is", "set")},
		                            pluck="default_shift", distinct=True))
		if not names:
			return []
	filters = {"name": ("in", sorted(names))} if names is not None else {}
	return frappe.get_all("Shift Type", filters=filters,
	                      fields=["name", "start_time", "end_time"] + list(STANDARD),
	                      order_by="name")


def _minutes_into_the_day(t):
	return t.hour * 60 + t.minute + t.second / 60.0


def _window_would_be_refused(row):
	"""Frappe's own ceiling: shift length plus both windows must stay under 24 h.

	Checked here so a shift that cannot take the standard is REPORTED rather
	than throwing half way through a run with the earlier shifts written and
	the later ones not.

	Mirrors `ShiftType.get_total_shift_duration_in_minutes`, which rounds the
	length to whole minutes and treats an end before the start as the next day.
	Done with arithmetic rather than by formatting the times into a string and
	parsing them back: Frappe stores a Time field as a timedelta, and whether
	`str()` of one gives "09:00:00" or "9:00:00" is not something this should
	depend on.
	"""
	start, end = get_time(row.start_time), get_time(row.end_time)
	if start == end:
		return None  # Frappe refuses that outright, so it cannot reach here.
	length = _minutes_into_the_day(end) - _minutes_into_the_day(start)
	if length < 0:
		length += 24 * 60
	total = (round(length)
	         + STANDARD["begin_check_in_before_shift_start_time"]
	         + STANDARD["allow_check_out_after_shift_end_time"])
	return total if total >= FRAPPE_WINDOW_CEILING_MINUTES else None


def _differences(row):
	"""The fields on one shift that do not match the standard."""
	out = {}
	for field, want in STANDARD.items():
		have = row.get(field)
		if isinstance(want, float):
			if float(have or 0) != want:
				out[field] = (have, want)
		elif isinstance(want, int):
			if int(have or 0) != want:
				out[field] = (have, want)
		elif (have or "") != want:
			out[field] = (have, want)
	return out


def preview(company=None):
	"""Say what would change. Writes nothing.

	Run with no changes outstanding and it prints a clean bill, which makes it
	the drift check as well as the plan.
	"""
	rows = _shifts(company)
	per_field, refused, changing = {}, [], 0
	for row in rows:
		over = _window_would_be_refused(row)
		if over:
			refused.append((row.name, over))
			continue
		diff = _differences(row)
		if not diff:
			continue
		changing += 1
		print("{0}".format(row.name))
		for field, (have, want) in sorted(diff.items()):
			print("    {0}: {1} -> {2}".format(field, have, want))
			per_field[field] = per_field.get(field, 0) + 1
	print("\nSHIFTS {0} read, {1} would change, {2} already match".format(
		len(rows), changing, len(rows) - changing - len(refused)))
	for field, n in sorted(per_field.items(), key=lambda kv: -kv[1]):
		print("    {0}: {1} shift(s)".format(field, n))
	if refused:
		print("\nREFUSED, left alone - Frappe caps length plus both windows at {0} minutes:".format(
			FRAPPE_WINDOW_CEILING_MINUTES))
		for name, total in refused:
			print("    {0}: would be {1} minutes".format(name, total))
	print("\nNOT touched by this module, on purpose: {0}".format(", ".join(NEVER_TOUCHED)))
	return {"read": len(rows), "changing": changing, "refused": len(refused), "fields": per_field}


def apply(company=None):
	"""Write the standard onto every shift that does not match it.

	The old values go to the site folder BEFORE any write, so `undo` always has
	something to put back even if this stops half way.
	"""
	_admin()
	rows = _shifts(company)
	plan = []
	for row in rows:
		if _window_would_be_refused(row):
			continue
		diff = _differences(row)
		if diff:
			plan.append((row, diff))

	state = _state()
	for row, _unused in plan:
		state["shifts"].setdefault(row.name, {f: row.get(f) for f in STANDARD})
	_save_state(state)

	done = 0
	for row, diff in plan:
		doc = frappe.get_doc("Shift Type", row.name)
		for field, (_have, want) in diff.items():
			doc.set(field, want)
		doc.flags.ignore_permissions = True
		doc.save()
		done += 1
	frappe.db.commit()
	print("apply: {0} shift(s) brought to the standard, {1} already matched.".format(
		done, len(rows) - len(plan)))
	print("Old values are in {0} - run undo to put them back.".format(_state_path()))
	print("Nothing has been marked. The next hourly tick is what acts on this.")
	print("A day ALREADY marked keeps the hours it was given: Frappe does not go back")
	print("over them. So until the period is marked again, a month holds some days")
	print("counted the old way and some the new way. Mark the period again, or expect")
	print("a mixed month and say so to whoever reads the report.")
	return {"changed": done}


def undo():
	"""Put every value this module changed back as it was."""
	_admin()
	state = _state()
	shifts = state.get("shifts") or {}
	if not shifts:
		print("undo: nothing recorded, so nothing to put back.")
		return {"restored": 0}
	for name, before in sorted(shifts.items()):
		if not frappe.db.exists("Shift Type", name):
			print("    {0}: gone, skipped".format(name))
			continue
		doc = frappe.get_doc("Shift Type", name)
		for field, value in before.items():
			doc.set(field, value)
		doc.flags.ignore_permissions = True
		doc.save()
	frappe.db.commit()
	print("undo: {0} shift(s) restored.".format(len(shifts)))
	state["shifts"] = {}
	_save_state(state)
	return {"restored": len(shifts)}
