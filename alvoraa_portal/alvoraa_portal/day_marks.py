"""What today's shift is worth to the person standing in front of it.

Surbhi, 17 Oct 2026: on the home banner, "show, according to their alloted
shift whether the employee is eligible for green pay / red pay for that day,
what is their half day according to their shift timing".

IN CLOCK TIMES, NOT RULES. "Leave after 21:30 for a night green" is something
somebody can act on at 21:15. "A night green is an hour past shift end" is a
rule they have to do arithmetic on, at the end of a ten-hour day. Every figure
here is resolved against THEIR shift and THEIR first punch, and comes out as a
time on a clock.

NOTHING IS PROMISED. A green is "if you leave after 21:30", never "you have
earned a green" - the day is judged when it is complete, by the engine, from
the punches. This screen says what the rules will look for. It does not decide.

WHY THE CONSTANTS ARE IMPORTED. `MORNING_GREEN_EARLY_MINUTES` and its
neighbours live in `payroll_rules`, which is what actually judges the day. A
copy here would drift, and the first anybody would know is an employee who
stayed late on the strength of this screen and earned nothing.

A TENANT WITHOUT THESE RULES SEES NOTHING OF THEM. Green and red marks are a
rule-set idea; a company without a rule set gets the half-day and late times
only, which are plain Shift Type settings every tenant has. There is no new
switch: the presence of the rule set IS the switch, and it is the same one the
engine reads.
"""

import frappe
from frappe.utils import flt, getdate

from alvoraa_portal.payroll_rules import (
	MORNING_GREEN_EARLY_MINUTES,
	NIGHT_GREEN_LATE_MINUTES,
)
from alvoraa_portal.payroll_rules_apply import green_eligibility_on


def _mins(value):
	"""A Time field, or a datetime, as minutes from midnight."""
	if value is None:
		return None
	s = str(value)
	if " " in s:
		s = s.split(" ", 1)[1]
	bits = s.split(":")
	try:
		return int(bits[0]) * 60 + int(bits[1])
	except (ValueError, IndexError):
		return None


def _clock(minutes):
	"""Minutes from midnight as "21:30". Past midnight wraps, and says so by
	staying inside the day rather than printing 25:30."""
	if minutes is None:
		return None
	minutes = int(round(minutes)) % (24 * 60)
	return "%02d:%02d" % (minutes // 60, minutes % 60)


def _grace_minutes(shift_row, rule_set):
	"""The grace that will actually be applied, asked the way the engine asks.

	The shift wins when it marks late entry itself; otherwise the rule set's
	figure applies. Copying "six minutes" in here would be wrong the day a
	shift sets its own.
	"""
	if shift_row and shift_row.get("enable_late_entry_marking"):
		return flt(shift_row.get("late_entry_grace_period") or 0)
	if rule_set:
		return flt(rule_set.get("grace_minutes") or 0)
	return 0.0


def marks_today(employee, employee_row, shift, checkin_rows, date_):
	"""What to show beside the check-in button.

	`shift` is the dict `_shift_today` already built - name, start, end.
	`checkin_rows` is today's punches, earliest first.

	Returns None where there is nothing useful to say: no shift means no
	shift length to measure against, which is the same answer the engine gives.
	"""
	if not shift or not shift.get("name"):
		return None

	row = frappe.db.get_value(
		"Shift Type", shift["name"],
		["enable_late_entry_marking", "late_entry_grace_period",
		 "working_hours_threshold_for_half_day",
		 "working_hours_threshold_for_absent"], as_dict=True) or {}

	company = employee_row.get("company")
	rule_set = None
	if company:
		name = frappe.db.get_value("Alvoraa Payroll Rule Set",
		                           {"company": company}, "name")
		if name:
			rule_set = frappe.get_cached_doc("Alvoraa Payroll Rule Set", name)

	start = _mins(shift.get("start"))
	end = _mins(shift.get("end"))
	if start is None or end is None:
		return None

	first_in = _mins(checkin_rows[0]["time"]) if checkin_rows else None
	grace = _grace_minutes(row, rule_set)

	out = {
		"shift": {"name": shift["name"], "start": _clock(start), "end": _clock(end)},
		# When they got in, or None if they have not. The screen needs this to
		# tell "not arrived yet" from "arrived on time" - both of which leave
		# `red.late` false, and which want opposite sentences.
		"arrived": _clock(first_in),
		# The two every tenant has, because they are Shift Type settings and
		# not a rule-set idea.
		"on_time_until": _clock(start + grace),
		"grace_minutes": int(grace),
		"half_day_before": None,
		"absent_before": None,
		"green": None,
		"red": None,
	}

	half = flt(row.get("working_hours_threshold_for_half_day") or 0)
	absent = flt(row.get("working_hours_threshold_for_absent") or 0)
	# Measured from when they actually arrived, which is the only honest
	# anchor: somebody who came in late reaches their half-day mark later.
	anchor = first_in if first_in is not None else start
	if half:
		out["half_day_before"] = _clock(anchor + half * 60)
		out["half_day_hours"] = half
	if absent:
		out["absent_before"] = _clock(anchor + absent * 60)
		out["absent_hours"] = absent

	if not rule_set:
		# No rule set: no green, no red, and no pretending otherwise.
		return out

	out["green"] = _green(employee, rule_set, start, end, checkin_rows,
	                      getdate(date_))
	out["red"] = _red(row, rule_set, start, end, grace, first_in)
	return out


def _green(employee, rule_set, start, end, checkin_rows, date_):
	"""What a green would take today, and whether it is still reachable.

	Two separate marks with separate rules, and somebody may be eligible for
	one and not the other.

	WHO IS ELIGIBLE IS NOT DECIDED HERE. `green_eligibility_on` is the engine's
	own answer, and asking it is the whole point: the first version of this
	function worked the rules out again and got every one of them wrong -
	including telling somebody with a blank field that they could earn nothing,
	when a blank field earns a morning green. Deciding it twice means the
	screen and the payslip can disagree, and the employee acts on the screen.
	"""
	able = green_eligibility_on(employee, date_, rule_set)
	morning_ok, night_ok = able["morning"], able["night"]
	if not morning_ok and not night_ok:
		return {"eligible": False, "why": "Not set up for green marks."}

	first_in = _mins(checkin_rows[0]["time"]) if checkin_rows else None
	out = {"eligible": True, "morning": None, "night": None}

	if morning_ok:
		by = start - MORNING_GREEN_EARLY_MINUTES
		got = first_in is not None and first_in <= by
		out["morning"] = {
			"by": _clock(by),
			"earned": got,
			# Once they are in, the morning mark is settled either way. Saying
			# "still possible" to somebody already at their desk would be a lie
			# they could act on.
			"still_possible": first_in is None,
		}

	if night_ok:
		after = end + NIGHT_GREEN_LATE_MINUTES
		out["night"] = {
			"after": _clock(after),
			"earned": False,
			"still_possible": True,
		}
		last_out = _mins(checkin_rows[-1]["time"]) if len(checkin_rows) > 1 else None
		if last_out is not None and len(checkin_rows) % 2 == 0:
			# An even number of punches means they have gone. The night mark is
			# decided.
			out["night"]["earned"] = last_out >= after
			out["night"]["still_possible"] = False

	return out


def _red(shift_row, rule_set, start, end, grace, first_in):
	"""Whether a red is in play today, and what avoids it.

	A red comes from the band the day lands in, and the bands are about how
	much of the shift was worked - so until somebody leaves there is no band
	and no red. What CAN be said before then is whether they are already late,
	because a late arrival is what puts the early bands within reach.
	"""
	late_by = None
	if first_in is not None and first_in > start + grace:
		late_by = int(first_in - (start + grace))

	window_from = _mins(rule_set.get("late_window_from"))
	window_to = _mins(rule_set.get("late_window_to"))
	in_window = False
	# The window is a clock time, not an offset, and it cannot bite somebody
	# whose shift starts at or after it - arriving 11:00 on an 11:00 shift is
	# punctual. The engine refuses it in that case and so does this.
	if (window_from is not None and window_to is not None
			and first_in is not None and start < window_from):
		in_window = window_from <= first_in <= window_to

	return {
		"late": late_by is not None,
		"late_by_minutes": late_by,
		"on_time_until": _clock(start + grace),
		"late_window": ({"from": _clock(window_from), "to": _clock(window_to)}
		                if window_from is not None and start < window_from else None),
		"in_late_window": in_window,
		"free_per_month": int(flt(rule_set.get("free_reds_per_month") or 0)),
	}
