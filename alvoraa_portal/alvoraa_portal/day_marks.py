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
from frappe.utils import flt, getdate, now_datetime

from alvoraa_portal.payroll_rules import (
	MORNING_GREEN_EARLY_MINUTES,
	NIGHT_GREEN_LATE_MINUTES,
	break_gaps,
	charge_for,
	collapse_duplicate_punches,
	late_charge,
)
from alvoraa_portal.payroll_rules_apply import day_rules_on


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


def _grace_minutes(shift_row):
	"""The shift's own grace, for a tenant with no payroll rule set.

	With a rule set the engine answers instead (`day_rules_on`), because there
	the employee's category can override the shift.
	"""
	if shift_row and shift_row.get("enable_late_entry_marking"):
		return flt(shift_row.get("late_entry_grace_period") or 0)
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
	# The engine's own answer for this person today: greens, grace (category
	# first), whether they earn marks, and the ALV-326 settings. Asked once and
	# never worked out here, so the banner and the payslip cannot disagree
	# (review P2-1: contract staff were shown the shift's grace, not theirs).
	rules = None
	if rule_set:
		shift_grace = (int(row.get("late_entry_grace_period") or 0)
		               if row.get("enable_late_entry_marking") else None)
		rules = day_rules_on(employee, getdate(date_), rule_set, shift_grace)
	grace = rules["grace_minutes"] if rules else _grace_minutes(row)

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
		# The ladder: what leaving at each time would cost. None on a tenant
		# with no rule set, because quarters are a rule-set idea.
		"ladder": None,
		# The SITE's clock, sent so the page can place "now" on the ladder
		# without trusting the device's own. A phone an hour out would
		# otherwise light the wrong rung (042 AC-53).
		"now": _clock(_mins(now_datetime())),
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

	out["green"] = _green(rules, start, end, checkin_rows)
	marks = rules["earns_marks"]
	out["red"] = _red(row, rule_set, start, end, grace, first_in,
	                  rules["late_quarter_after_minutes"], marks)

	# ALV-326: the ladder counts the way the engine will. With shift hours only,
	# from the shift start for anybody within grace and from their real arrival
	# past it; otherwise from the arrival, as always. Any break already over the
	# allowance moves every rung later.
	shift_only = rules["shift_hours_only"]
	late = (out["red"] or {}).get("late_charge") or ""
	if shift_only and first_in is not None and first_in <= start + grace:
		counted_from = start
	else:
		counted_from = anchor
	times = collapse_duplicate_punches(
		[t for t in (_mins(r["time"]) for r in checkin_rows) if t is not None])
	over = _break_over(break_gaps(times), counted_from,
	                   end if shift_only else 24 * 60, rules["break_allowance_minutes"])
	out["ladder"] = _ladder(rule_set, start, end, counted_from,
	                        (out["red"] or {}).get("in_late_window"), late, over, shift_only,
	                        marks)
	return out


def _break_over(gaps: list, counted_from: int, end: int, allowance: int) -> int:
	"""Minutes of breaks already over beyond the allowance (0 = no break rule).

	Only breaks with both punches count: somebody out at lunch right now has
	not finished it, and the engine cannot see an unfinished break either.
	"""
	if allowance <= 0:
		return 0
	on_break = sum(max(0, min(back, end) - max(out, counted_from)) for out, back in gaps)
	return max(0, on_break - allowance)


def _ladder(rule_set, start, end, anchor, in_late_window, late="", break_over=0,
            shift_only=False, marks=True):
	"""What leaving at each time would cost, as clock times.

	The whole thing rests on one line of the engine:

	    percent = (last_out - anchor - breaks over the allowance) / shift_minutes * 100

	with `last_out` capped at the shift end when the rule set counts only shift
	hours.

	The band depends only on how long somebody was here against how long their
	shift is - so every boundary is a DEPARTURE CLOCK TIME measured from where
	counting started. "Leave before 16:58 and it costs you a quarter" is
	something a person can act on at 16:45. A percentage is not.

	BANDS WITH THE SAME COST ARE MERGED. DTC's table has twelve rows and only
	five distinct costs: 68-75% and 75-90% both take one quarter, so showing
	them apart is noise somebody has to read past. What survives the merge is
	one rung per cost, plus the narrow window just after each cliff where the
	band ALSO raises a red - which is worth keeping, because those are the
	minutes where leaving costs twice.

	THE ROWS COME FROM THE RULE SET, never from a copy here. This module got
	green eligibility wrong once by working the rules out a second time, and a
	ladder that disagrees with the payslip is that same bug with more at stake:
	somebody stays two hours on the strength of it.

	ALV-326 (DTC, 2026-11-11). `anchor` is where counting starts. With
	`shift_only`, a rung later than the shift end cannot be reached and is left
	out. Each band's cost goes through the engine's own `charge_for`, so a late
	arrival's red or quarter (when the rule set sets one) is already in every
	rung. A late-red arrival keeps a red window only where the two-red rule adds
	a second red: the no-quarter red band, left before the shift end.
	`break_over` moves every rung later. All three are no-ops on a rule set that
	sets none of the ALV-326 settings. Somebody who earns no marks (`marks`
	off) is shown no red window at all: the payslip will never give them one.
	"""
	length = end - start
	if length <= 0:
		return None
	rows = sorted(rule_set.get("slabs") or [], key=lambda r: flt(r.percent_from))
	if not rows:
		return None

	# Walked from the best band downwards, so the first rung is the best case
	# and a merge only ever joins a band onto the rung above it.
	rungs = []
	for r in reversed(rows):
		quarters, _ = charge_for(late, int(r.quarters_off or 0), bool(r.raises_red))
		if not marks:
			raises_red = False
		elif late == "red":
			raises_red = bool(r.raises_red) and not int(r.quarters_off or 0)
		else:
			raises_red = bool(r.raises_red) and late != "quarter"
		if rungs and rungs[-1]["quarters"] == quarters:
			top = rungs[-1]
			top["percent_from"] = flt(r.percent_from)
			if raises_red:
				# The red sub-band sits at the bottom of the merged rung: it is
				# the first stretch somebody enters when they drop into it.
				top["red_from"] = flt(r.percent_from)
				top["red_to"] = flt(r.percent_to)
			continue
		rungs.append({
			"quarters": quarters,
			"percent_from": flt(r.percent_from),
			"red_from": flt(r.percent_from) if raises_red else None,
			"red_to": flt(r.percent_to) if raises_red else None,
		})

	# A second red is for leaving early, so it ends a minute before the shift.
	# Without shift hours only, nothing is clipped, exactly as before.
	last_red = (end - 1 if late == "red" else end) if shift_only else float("inf")
	steps = []
	for rung in rungs:
		leave_after = anchor + break_over + rung["percent_from"] / 100.0 * length
		if shift_only and leave_after > end:
			continue
		step = {
			"leave_after": _clock(leave_after),
			"quarters": rung["quarters"],
			"percent_from": rung["percent_from"],
			"red_from": None,
			"red_to": None,
		}
		red_from = (None if rung["red_from"] is None
		            else anchor + break_over + rung["red_from"] / 100.0 * length)
		if red_from is not None and red_from <= last_red:
			step["red_from"] = _clock(red_from)
			step["red_to"] = _clock(min(last_red,
			                            anchor + break_over + rung["red_to"] / 100.0 * length))
		steps.append(step)

	return {
		"anchor": _clock(anchor),
		"break_over": int(break_over),
		"shift_hours_only": bool(shift_only),
		"shift_minutes": int(length),
		"steps": steps,
		# ATT-04 stacks on whatever the band decides and is never doubled, so it
		# cannot be folded into a rung: that would make every rung wrong by one
		# for the people it applies to, and right for everybody else.
		"extra_quarter": bool(in_late_window),
	}


def _green(able, start, end, checkin_rows):
	"""What a green would take today, and whether it is still reachable.

	Two separate marks with separate rules, and somebody may be eligible for
	one and not the other.

	WHO IS ELIGIBLE IS NOT DECIDED HERE. `able` is `day_rules_on`, the engine's
	own answer, and asking it is the whole point: the first version of this
	function worked the rules out again and got every one of them wrong -
	including telling somebody with a blank field that they could earn nothing,
	when a blank field earns a morning green. Deciding it twice means the
	screen and the payslip can disagree, and the employee acts on the screen.
	"""
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


def _red(shift_row, rule_set, start, end, grace, first_in, late_quarter_after=0, marks=True):
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

	charge = late_charge(first_in - start, grace, late_quarter_after) if first_in is not None else ""
	if charge == "red" and not marks:
		# Staff who earn no marks never get a red (review P2-1); a late quarter
		# still applies to them.
		charge = ""

	return {
		"late": late_by is not None,
		"late_by_minutes": late_by,
		"earns_marks": marks,
		# ALV-326: what the arrival costs where the rule set sets a late limit -
		# "red" up to it, "quarter" beyond - and the clock time where one becomes
		# the other. "" and None where it sets none.
		"late_charge": charge,
		"late_red_until": (_clock(start + late_quarter_after)
		                   if late_quarter_after > 0 else None),
		"on_time_until": _clock(start + grace),
		"late_window": ({"from": _clock(window_from), "to": _clock(window_to)}
		                if window_from is not None and start < window_from else None),
		"in_late_window": in_window,
		"free_per_month": int(flt(rule_set.get("free_reds_per_month") or 0)),
	}
