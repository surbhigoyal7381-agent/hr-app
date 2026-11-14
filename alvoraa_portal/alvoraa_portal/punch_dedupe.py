"""One punch per scan, whatever the reader sends (ALV-337).

A DTC reader stores the same scan up to nine times within seconds. Frappe pairs
a day's punches alternately as IN and OUT, so a double read becomes an instant
departure. In November 2026 that was 984 of 9,072 punches - eleven per cent -
and 139 days were marked Absent on exactly 0.0 recorded hours because of it.
Paid days come from that status, so the fault reaches base salary, not only the
red and green marks.

The rule itself is not new. `payroll_rules.DUPLICATE_PUNCH_MINUTES` is already
applied in the pay engine, in the day marks, and since ALV-315 in the correction
screen. What never happened is applying it where the punches arrive, so Frappe
HR's own marking job has never once seen clean data. This module is that one
place, and it imports the rule rather than restating it.

WHY THE ROW IS KEPT. A repeat read is flagged `skip_auto_attendance`, never
deleted. The device really did send it, so it is evidence, and HR needs to see
it when an employee disputes a day. Frappe's marking job already filters on that
flag - `get_employee_checkins` in hrms shift_type.py - so the flag is the whole
mechanism. Setting it back to 0 undoes this completely, which is why there is no
patch and no migration here.

WHY `before_insert`. It runs once, on new rows only, so a later save can never
re-judge a punch somebody has since corrected by hand. It runs before Frappe's
`fetch_shift`, and that has one deliberate consequence: on a shift set to
"Strictly based on Log Type in Employee Checkin", a punch carrying no log type
is normally REFUSED outright. A repeat read now holds the skip flag by the time
that check runs, so it is kept and ignored instead of being thrown away. That is
the better outcome, because a refused punch is simply lost. It changes nothing at
DTC, where all 45 shifts use alternating entries and no punch carries a log type
at all.

TWO SCANS AT ONCE. Two requests inserting the same scan in parallel can both
find no anchor and both be kept. The pay engine, the day marks and the
correction screen all collapse duplicates again when they read, so the money is
not exposed; only Frappe's own marking could see the pair. It has not happened
at DTC - the sync posts a batch in one request - and a lock on every punch
insert would cost far more than the case is worth.

WHAT THIS DOES NOT FIX. A punch that falls outside the shift window gets no
shift and is invisible to marking whatever this module does. That is the other
half of ALV-337 and it lives in `shift_standard`.

PUNCHES ALREADY STORED. The hook only sees new rows. 916 of November's 984
repeats are already linked to an Attendance row, and Frappe never re-reads a
linked punch, so flagging them on its own changes nothing a person would see -
the wrong Absent days have to be cancelled and marked again. That matters here
because ALV-291's `cancel_wrong` CLEARS the skip flag on every punch it frees,
deliberately, so the marking job can use them. Freeing November's days and
marking them again without flagging the repeats in between would reproduce the
same 169 wrong Absents. `flag_existing` is that in-between step, and the order
is the whole point of it:

    ALV-291's cancel for November  ->  flag_existing  ->  mark again

Read first, always, and name the dates: there is no default range, so this can
never quietly reach into October, which belongs to ALV-291.

    bench --site <site> execute alvoraa_portal.punch_dedupe.preview_existing \\
        --kwargs "{'from_date': '2026-11-01', 'to_date': '2026-11-30'}"
    bench --site <site> execute alvoraa_portal.punch_dedupe.flag_existing \\
        --kwargs "{'from_date': '2026-11-01', 'to_date': '2026-11-30'}"
    bench --site <site> execute alvoraa_portal.punch_dedupe.unflag_existing
"""

import json
import os

import frappe
from frappe.utils import add_to_date, get_datetime, getdate

from alvoraa_portal.payroll_rules import DUPLICATE_PUNCH_MINUTES

STATE_FILE = "alv337_flagged_punches.json"


def skip_repeat_scan(doc, method=None):
	"""Flag a punch that repeats one the marking job would already count.

	Hooked on Employee Checkin `before_insert`, so it covers every path that
	creates a punch: the biometric endpoint, the field app, the Desk form and
	any script. One hook rather than one guard per caller, because a new path
	added later would otherwise arrive unprotected.
	"""
	if doc.skip_auto_attendance:
		return
	if not doc.employee or not doc.time:
		return
	if earlier_kept_punch(doc.employee, doc.time):
		doc.skip_auto_attendance = 1


def earlier_kept_punch(employee, time, window_minutes=DUPLICATE_PUNCH_MINUTES):
	"""The nearest punch before `time` that marking would still count, or None.

	Only KEPT punches are looked at, exactly as `collapse_duplicate_punches`
	measures each gap from the last punch it kept rather than from the raw
	previous one.

	That is not a nicety, and a burst of scans does not show why: nine reads a
	second apart are all inside two minutes of the FIRST one, so measuring from
	the last kept punch or from the raw previous one folds them the same way.
	The difference shows on a DRIFTING chain. Take 09:00:00, 09:01:30, 09:03:00.
	Measured from the last kept punch, 09:03:00 is three minutes from 09:00:00
	and is a real punch - two punches, which is right. Measured from whatever row
	came last, each one is 90 seconds after the one before, so the chain swallows
	itself and the whole day becomes a single punch with no departure. That is
	the fault this module exists to stop, reproduced by the fix.

	The window is inclusive at both ends, which matches that helper's `<=`: two
	punches exactly `window_minutes` apart are one punch.
	"""
	when = get_datetime(time)
	return frappe.db.get_value(
		"Employee Checkin",
		{
			"employee": employee,
			"skip_auto_attendance": 0,
			"time": ("between", [add_to_date(when, minutes=-window_minutes), when]),
		},
		"name",
		order_by="time desc",
	)


# ── punches already stored ───────────────────────────────────────────────────


def repeat_scans(times, window_minutes=DUPLICATE_PUNCH_MINUTES):
	"""Of a person's punches in time order, the positions that repeat an earlier one.

	The same rule as `collapse_duplicate_punches`, measured from the last punch
	KEPT rather than the raw previous one. Returns the indexes to flag, so a
	caller can act on rows rather than on clock readings.

	Measuring from the raw previous row instead looks harmless on a burst of
	scans and is not: on a drifting chain - 09:00:00, 09:01:30, 09:03:00, each
	90 seconds after the last - every punch after the first is inside the window
	of the one before it, so the day collapses to one punch and loses its
	departure. See `earlier_kept_punch`, which has to agree with this.

	One deliberate difference from that helper: this compares whole date-times,
	so a double read either side of midnight is one punch. The helper counts
	minutes from midnight, where the same pair looks 1,439 minutes apart. Whole
	date-times are the stricter and the correct reading; the helper is only ever
	given a single day at a time, so the two never disagree in practice.
	"""
	repeats, last_kept = [], None
	for i, t in enumerate(times):
		when = get_datetime(t)
		if last_kept is not None and (when - last_kept).total_seconds() <= window_minutes * 60:
			repeats.append(i)
			continue
		last_kept = when
	return repeats


def _state():
	path = frappe.get_site_path(STATE_FILE)
	if os.path.exists(path):
		with open(path) as f:
			return json.load(f)
	return {"flagged": []}


def _save_state(state):
	path = frappe.get_site_path(STATE_FILE)
	with open(path + ".tmp", "w") as f:
		json.dump(state, f, indent=1, default=str)
	os.replace(path + ".tmp", path)


def _admin():
	if frappe.session.user != "Administrator":
		frappe.throw("Refused: run this as Administrator, through bench execute.")


def _repeats_in_range(from_date, to_date, company=None):
	"""Every stored punch in the range that repeats an earlier kept one.

	Reads punches a person at a time, in time order, across the WHOLE range
	rather than day by day, so a double read either side of midnight is caught.
	Only rows that still count are read: a punch already flagged is one the
	marking job ignores, so it is neither a repeat to find nor an anchor.
	"""
	start, end = getdate(from_date), getdate(to_date)
	filters = {
		"skip_auto_attendance": 0,
		"time": ("between", ["{0} 00:00:00".format(start), "{0} 23:59:59".format(end)]),
	}
	if company:
		people = frappe.get_all("Employee", filters={"company": company}, pluck="name")
		if not people:
			return []
		filters["employee"] = ("in", people)
	rows = frappe.get_all("Employee Checkin", filters=filters,
	                      fields=["name", "employee", "time", "attendance"],
	                      order_by="employee asc, time asc")
	found, bucket, who = [], [], None
	for row in rows + [None]:
		if row is None or row.employee != who:
			if bucket:
				found += [bucket[i] for i in repeat_scans([r.time for r in bucket])]
			bucket, who = [], row.employee if row else None
		if row is not None:
			bucket.append(row)
	return found


def preview_existing(from_date, to_date, company=None):
	"""Say which stored punches would be flagged. Writes nothing."""
	found = _repeats_in_range(from_date, to_date, company)
	linked = [r for r in found if r.attendance]
	people = {r.employee for r in found}
	print("REPEATS {0} punch(es) across {1} people, {2} to {3}".format(
		len(found), len(people), getdate(from_date), getdate(to_date)))
	print("    already linked to an attendance row: {0}".format(len(linked)))
	print("    loose, so the next marking run would read them: {0}".format(len(found) - len(linked)))
	if linked:
		print("\nA linked punch is never re-read by Frappe, so flagging it changes nothing a")
		print("person would see. Those days have to be cancelled and marked again - ALV-291's")
		print("cancel step - and this must run BETWEEN the cancel and the marking, because")
		print("cancel_wrong clears the skip flag on every punch it frees.")
	return {"repeats": len(found), "people": len(people), "linked": len(linked)}


def flag_existing(from_date, to_date, company=None):
	"""Flag every stored repeat in the range, and record it so `unflag_existing` can undo.

	Refuses if anybody in the range has a submitted salary slip covering it:
	changing what a paid month counted is never a repair, it is a restatement,
	and it is the user's decision, not a script's.
	"""
	_admin()
	slip_filters = {"docstatus": 1,
	                "start_date": ("<=", getdate(to_date)),
	                "end_date": (">=", getdate(from_date))}
	if company:
		slip_filters["company"] = company
	paid = frappe.get_all("Salary Slip", filters=slip_filters,
	                      fields=["name", "employee"], limit_page_length=5)
	if paid:
		frappe.throw("Refused: {0} has a submitted salary slip covering this range. "
		             "Changing a paid month is a restatement, not a repair.".format(paid[0].name))

	found = _repeats_in_range(from_date, to_date, company)
	state = _state()
	known = set(state["flagged"])
	state["flagged"] += [r.name for r in found if r.name not in known]
	_save_state(state)  # before any write, so undo always knows what we touched

	for row in found:
		frappe.db.set_value("Employee Checkin", row.name, "skip_auto_attendance", 1,
		                    update_modified=False)
	frappe.db.commit()
	print("flag_existing: {0} repeat(s) flagged across {1} people.".format(
		len(found), len({r.employee for r in found})))
	print("Recorded in {0} - run unflag_existing to put them back.".format(
		frappe.get_site_path(STATE_FILE)))
	return {"flagged": len(found)}


def unflag_existing():
	"""Clear the flag on every punch `flag_existing` set, and forget them."""
	_admin()
	state = _state()
	names = state.get("flagged") or []
	if not names:
		print("unflag_existing: nothing recorded, so nothing to put back.")
		return {"restored": 0}
	for name in names:
		if frappe.db.exists("Employee Checkin", name):
			frappe.db.set_value("Employee Checkin", name, "skip_auto_attendance", 0,
			                    update_modified=False)
	frappe.db.commit()
	print("unflag_existing: {0} punch(es) put back.".format(len(names)))
	state["flagged"] = []
	_save_state(state)
	return {"restored": len(names)}
