"""Reads a day out of Frappe, asks the engine, writes the verdict back.

This is the only part of the rules that knows what a DocType is. The judgment
itself lives in `payroll_rules.evaluate_day`, which touches no database and is
tested against the client's own worked examples. Keeping the two apart is what
lets the rules be tested at all.

TWO THINGS THIS FILE IS CAREFUL ABOUT.

  It does nothing unless a rule set exists for the company and is switched on.
  Every other tenant on this image has no rule set, so for them these functions
  return without a single write. That is how one engine serves every tenant
  without a branch per client, and it is worth stating plainly because the
  failure mode - a tenant silently acquiring DTC's slab table - would be found
  in a payslip rather than in a test.

  It fetches per day, but accepts what a caller already has. A month of 312
  employees is 9,000 days; looking up the rule set, the special-day list and
  the shift once per day would be 27,000 queries. `prepare` builds that once
  and every call takes it as an argument.

Nothing here decides pay. It records what the rules say about a day, on the day.
The monthly roll-up and the salary slip read these figures later.
"""

import frappe
from frappe.utils import get_datetime, getdate, now

from alvoraa_portal.payroll_rules import break_gaps, evaluate_day, minutes_on_break, punch_minutes

# Values of a tenant's double-deduction field that mean "yes, double it".
# Frappe Select fields store the label, so a tenant may have Yes/No, 1/0 or
# YES/NO. Anything else is read as no, which is the safer default: failing to
# double is an underpayment the employee will not complain about, while
# doubling by mistake takes money from somebody who was not expected to work.
DOUBLE_YES = {"yes", "1", "true", "y"}

# Green eligibility, as the tenant's Select field spells it.
GREEN_MORNING = {"", "morning green", "both"}
GREEN_NIGHT = {"night green", "both"}

# The fields the engine owns on Attendance. Listed once so a reprocess can
# clear them and nothing drifts out of step with the writer.
VERDICT_FIELDS = (
	"alvoraa_held",
	"alvoraa_attendance_percent",
	"alvoraa_slab_quarters",
	"alvoraa_extra_quarters",
	"alvoraa_special_day_doubled",
	"alvoraa_reds",
	"alvoraa_greens",
	"alvoraa_late_arrival",
	"alvoraa_early_departure",
	"alvoraa_rules_why",
	"alvoraa_evaluated_on",
)

# The Attendance fields `judge` needs to tell a half-day LEAVE from a short
# shift, and to see an approved half-day correction (slice 063). Every reader
# that hands rows to `judge` asks for these, so none can drift.
LEAVE_FIELDS = ("leave_type", "leave_application", "attendance_request")

# The leave type whose days are drawn from the month's credits (slice 063, D1).
# Found by its exact name, created by hand at DTC only.
PAID_LEAVES = "Paid Leaves"


def rule_set_for(company):
	"""The enabled rule set for a company, or None.

	None is the normal answer on every tenant that is not DTC, and it means
	every function here does nothing. Not an error.
	"""
	if not company:
		return None
	name = frappe.db.get_value("Alvoraa Payroll Rule Set",
	                           {"company": company, "enabled": 1}, "name")
	return frappe.get_cached_doc("Alvoraa Payroll Rule Set", name) if name else None


def _minutes(value):
	"""A Time field as minutes from midnight.

	Frappe hands a Time back as a timedelta from the database and as a string
	from a form, and both reach here.
	"""
	if value is None:
		return None
	if hasattr(value, "total_seconds"):
		return int(value.total_seconds() // 60)
	parts = str(value).split(":")
	return int(parts[0]) * 60 + int(parts[1])


def _green_windows(from_date=None, to_date=None, employee=None):
	"""Every dated green grant that could touch this period, by employee.

	Loaded once. Resolving per day would be a query per employee per day -
	9,000 of them for a month of 312 people - and the table is small enough to
	hold whole.
	"""
	# ONE person, for the home banner. This table has a row per employee, so
	# the unfiltered load is the whole headcount - 363 rows on DTC - fetched
	# to answer a question about one of them, on the page every employee
	# opens. A batch still asks for all of them by leaving it out.
	one = " AND employee = %(employee)s" if employee else ""
	if from_date and to_date:
		# A grant overlaps the window if it starts before the window ends and
		# ends after the window starts. An open-ended grant has no to_date, so
		# it is caught by the OR below rather than by a filter.
		rows = frappe.db.sql("""
			SELECT employee, from_date, to_date, eligibility
			FROM `tabAlvoraa Green Eligibility`
			WHERE from_date <= %(to_date)s
			  AND (to_date IS NULL OR to_date >= %(from_date)s)""" + one + """
			ORDER BY employee, from_date""",
			{"to_date": to_date, "from_date": from_date,
			 "employee": employee}, as_dict=True)
	else:
		rows = frappe.get_all(
			"Alvoraa Green Eligibility",
			filters={"employee": employee} if employee else None,
			fields=["employee", "from_date", "to_date", "eligibility"],
			order_by="employee asc, from_date asc", limit_page_length=0)

	windows = {}
	for r in rows:
		windows.setdefault(r["employee"], []).append(
			(getdate(r["from_date"]),
			 getdate(r["to_date"]) if r["to_date"] else None,
			 (r["eligibility"] or "").strip().lower()))
	return windows


def prepare(rule_set, from_date=None, to_date=None, employee=None):
	"""Everything the per-day calls would otherwise look up 9,000 times.

	`employee` narrows the dated green grants to one person. Leave it out
	for a batch; pass it where the caller only ever asks about one, so a
	per-employee table is not read whole on a page every employee loads.
	"""
	special = set()
	if rule_set.special_day_holiday_list:
		special = {
			getdate(d) for d in frappe.get_all(
				"Holiday",
				filters={"parent": rule_set.special_day_holiday_list},
				pluck="holiday_date")
		}

	# (start, end, grace) per shift. Grace is None when the shift has nothing
	# to say about it.
	#
	# `enable_late_entry_marking` is what separates "this shift allows no
	# grace" from "nobody set this shift up". Both leave the minutes at 0 and
	# Frappe has no other way to tell them apart, so without reading the tick
	# every unconfigured shift would silently mean zero grace - a red mark for
	# arriving one minute late, for everybody on that shift.
	shifts = {}
	for s in frappe.get_all("Shift Type",
	                        fields=["name", "start_time", "end_time",
	                                "enable_late_entry_marking",
	                                "late_entry_grace_period"]):
		start, end = _minutes(s.start_time), _minutes(s.end_time)
		if start is not None and end is not None:
			shifts[s.name] = (
				start, end,
				int(s.late_entry_grace_period or 0)
				if s.enable_late_entry_marking else None)

	return {
		"rule_set": rule_set,
		"slabs": list(rule_set.slabs),
		"special_days": special,
		"shifts": shifts,
		"grace": int(rule_set.grace_minutes or 0),
		"multiplier": int(rule_set.special_day_multiplier or 1),
		"window_from": _minutes(rule_set.late_window_from),
		"window_to": _minutes(rule_set.late_window_to),
		"window_quarters": int(rule_set.late_window_extra_quarters or 0),
		# ALV-326. Off unless the rule set says; the last two can be overridden
		# per category, in `_employee_flags`.
		"shift_hours_only": bool(rule_set.get("count_shift_hours_only")),
		"late_quarter_after": int(rule_set.get("late_quarter_after_minutes") or 0),
		"break_allowance": int(rule_set.get("break_allowance_minutes") or 0),
		"window_field": (rule_set.late_window_employee_field or "").strip(),
		"double_field": (rule_set.double_deduction_field or "").strip(),
		"green_field": (rule_set.green_eligibility_field or "").strip(),
		"green_windows": _green_windows(from_date, to_date, employee),
		"class_field": (rule_set.leave_class_field or "").strip(),
		"category_field": (rule_set.category_field or "").strip(),
		"leave_threshold": int(rule_set.leave_threshold_days or 0),
		"class_credits": {
			(r.leave_class or "").strip(): float(r.monthly_credits or 0)
			for r in rule_set.leave_classes
		},
		# A category not listed takes the defaults: the standard grace, marks
		# on, leave on. So adding a category is how an exception is made, and
		# forgetting to add one cannot quietly strip somebody's marks.
		"categories": {
			(r.category or "").strip().lower(): {
				"grace_minutes": int(r.grace_minutes or 0),
				"earns_marks": bool(r.earns_marks),
				"earns_leave_credits": bool(r.earns_leave_credits),
				"doubles_deduction": bool(r.doubles_deduction),
				"late_quarter_after": int(r.get("late_quarter_after_minutes") or 0),
				"break_allowance": int(r.get("break_allowance_minutes") or 0),
			}
			for r in rule_set.categories
		},
	}


def _employee_flags(employee, date, ctx, shift_grace=None):
	"""The per-employee switches, read through the field names the rule set
	names rather than field names written into this file.

	A field the tenant has not created yet reads as absent, and the rule that
	depends on it simply does not fire. That is deliberate: DTC have not sent
	the employee-category mapping, so the CAT-06 exemption cannot be applied
	yet, and guessing it would be worse than leaving it off.

	`shift_grace` is the grace the employee's shift allows on arrival, or None
	where that shift does not set one. See the grace note below.
	"""
	wanted = [f for f in (ctx["window_field"], ctx["double_field"],
	                      ctx["green_field"], ctx["category_field"]) if f]
	meta = frappe.get_meta("Employee")
	present = [f for f in wanted if meta.has_field(f)]
	values = frappe.db.get_value("Employee", employee, present, as_dict=True) or {} \
		if present else {}

	def raw(fieldname):
		return str(values.get(fieldname) or "").strip().lower() if fieldname else ""

	# A dated grant wins over the Employee field. The field is what was true
	# the day somebody last edited it; the grant is what was true on THIS day,
	# which is the only thing a reprocess may use. Without this, re-running
	# October in December would apply December's eligibility to October.
	green = _green_on(employee, date, ctx) or raw(ctx["green_field"])
	# The category override, if this tenant has any and this employee matches
	# one. Falling through to the defaults is the safe direction: an unlisted
	# category keeps its marks rather than silently losing them.
	override = ctx["categories"].get(raw(ctx["category_field"]), {})

	# ── grace comes from the most specific place that has an answer ──────────
	#
	# 1. The employee's CATEGORY. Contract staff get a longer grace because of
	#    their contract, not because of their shift - they work the same shifts
	#    as everybody else, so letting a shift overrule it would quietly take
	#    the concession away the first time somebody edited that shift. A
	#    category grace of 0 means "no override", which is how an ordinary
	#    category leaves the decision to the shift.
	# 2. The employee's SHIFT, where it sets one. This is the number HR
	#    actually maintains, and the same number Frappe uses for its own Late
	#    Entry tick - so the two can no longer drift apart.
	# 3. The rule set's own number, as the fallback for a shift that sets none
	#    and for any tenant not using shift-level grace at all.
	#
	# Only arrival. Leaving early carries no grace in these rules (GBL-04
	# grants it on arrival only), so Shift Type's early exit grace is read
	# nowhere - using it would change DTC's rules rather than tidy them.
	grace = override.get("grace_minutes")
	if not grace:
		grace = ctx["grace"] if shift_grace is None else shift_grace

	# ── WSD-05/06: whose quarters are doubled on a special day ───────────────
	#
	# The CATEGORY decides first. Settled 15 October 2026: nobody is exempt
	# except contract staff, and that follows from their employment type, which
	# every employee already carries. A yes/no box on each of 363 records would
	# be a second copy of a fact we hold correctly once.
	#
	# A category that says no means no, whatever any per-employee field says.
	# Otherwise the field decides, and a tenant that names no field doubles for
	# everybody.
	doubles = override.get("doubles_deduction", True)
	if doubles and ctx["double_field"]:
		doubles = raw(ctx["double_field"]) in DOUBLE_YES

	return {
		"grace_minutes": grace,
		# ALV-326: a category figure wins; 0 there means "use the rule set's",
		# the same convention as grace above.
		"late_quarter_after_minutes": override.get("late_quarter_after") or ctx["late_quarter_after"],
		"break_allowance_minutes": override.get("break_allowance") or ctx["break_allowance"],
		"earns_marks": override.get("earns_marks", True),
		# ── ATT-04: who the late window applies to ───────────────────────────
		#
		# No field named means EVERYBODY, which is how the doubling above has
		# always behaved. These two read the same blank and used to answer it
		# oppositely - the window fired for nobody - so a tenant who set a
		# window and no field got a rule that silently did nothing.
		#
		# Surbhi, 15 October 2026: it applies to everyone, and the employee's
		# shift timing is what decides whether it bites. That gate is
		# `_window_applies`, which skips any shift starting at or after the
		# window. Naming a field still narrows it, if a tenant ever wants to.
		"late_window_flagged": bool(values.get(ctx["window_field"]))
		if ctx["window_field"] else True,
		"double_deduction_applies": doubles,
		"morning_green_eligible": (green in GREEN_MORNING)
		if ctx["green_field"] else True,
		"night_green_eligible": (green in GREEN_NIGHT)
		if ctx["green_field"] else True,
	}


def _green_on(employee, date, ctx):
	"""The dated grant covering this day, or "" if there is none.

	Where more than one grant covers a day, THE ONE THAT STARTS LATEST WINS.

	That rule exists so a festive season can be a single row. DTC keep a
	standing, open-ended grant per employee and then widen it for Diwali. If
	the standing grant simply won, the festive row would do nothing; if
	overlaps were banned, granting Diwali would mean ending the standing
	period, adding the season, and starting a new standing period afterwards -
	three edits each, for two hundred and fifty people.

	"The most recent decision applies" is how a person reads it anyway, and it
	is deterministic: two grants cannot share a start date, because the record
	is named after the employee and that date.
	"""
	best, best_start = "", None
	for start, end, value in ctx["green_windows"].get(employee, ()):
		if start <= date and (end is None or date <= end):
			if best_start is None or start > best_start:
				best, best_start = value, start
	return best


def day_rules_on(employee: str, date, rule_set, shift_grace=None) -> dict:
	"""Which green marks this person can earn on this day (morning, night, both
	or neither), and the rest of what the engine will judge them by: the grace
	in force (category first, then `shift_grace`, then the rule set - exactly
	as `judge` works it out), whether they earn marks at all, and the ALV-326
	settings with any category override. Named `green_eligibility_on` until
	ALV-326; the review (P2-1) found the banner using a different grace.

	THE HOME BANNER ASKS THIS. It tells somebody what is still worth doing
	today, so it has to be the same answer the engine will pay on - and that is
	why it is answered here instead of worked out again beside the banner. Four
	rules decide it, and a second copy got all four wrong: a blank field earns a
	morning green but NOT a night one, a rule set naming no field earns both,
	the stored values are compared folded to lower case, and a dated grant beats
	the Employee field. Somebody told "no green marks" who could in fact have
	earned one by arriving early loses money on the strength of our screen.

	Three queries for one person on one day. The caller is a page every employee
	loads, so this must never grow a loop over people - `prepare` exists to be
	built once and reused for a batch.
	"""
	ctx = prepare(rule_set, date, date, employee=employee)
	flags = _employee_flags(employee, date, ctx, shift_grace=shift_grace)
	return {"morning": bool(flags["morning_green_eligible"]),
	        "night": bool(flags["night_green_eligible"]),
	        "grace_minutes": flags["grace_minutes"],
	        "earns_marks": bool(flags["earns_marks"]),
	        "shift_hours_only": ctx["shift_hours_only"],
	        "late_quarter_after_minutes": flags["late_quarter_after_minutes"],
	        "break_allowance_minutes": flags["break_allowance_minutes"]}


def _punches(employee, date):
	"""First and last punch of the day, how many there were, and the gaps
	between them that may be breaks (`break_gaps`).

	Whole minutes (ALV-326, Surbhi's D3, 2026-11-11): DTC's sheet and the home
	banner both read 10:36:40 as 10:36, so the engine does too. Without it a
	punch inside the grace minute could be late by seconds.

	Read from Employee Checkin, never from Attendance.working_hours. On DTC all
	22 shifts compute working hours by alternating in/out pairs, and 1,023
	present days record zero hours while only 186 genuinely lack a check-out.
	Trusting that field would hold five times as many days as it should.
	"""
	rows = frappe.get_all("Employee Checkin",
	                      filters={"employee": employee, "time": ("between", [
		                      "{0} 00:00:00".format(date), "{0} 23:59:59".format(date)])},
	                      pluck="time", order_by="time asc")
	if not rows:
		return None, None, 0, []
	# A reader that scans twice in a second has not recorded a working day of
	# one second. Collapse before counting, or ATT-06 never sees the day as the
	# single punch it really is.
	distinct = punch_minutes(map(get_datetime, rows))
	if not distinct:
		return None, None, 0, []
	return distinct[0], distinct[-1], len(distinct), break_gaps(distinct)


def breaks_by_day(employee: str, company: str | None, days: dict, times_by_date: dict) -> tuple:
	"""The break the engine would count on each day, for one person (ALV-328).

	`days` maps "YYYY-MM-DD" to (status, shift) for the person's submitted
	Attendance rows; `times_by_date` maps the same dates to that calendar day's
	punch datetimes, already read by the caller with `get_list` - so a caller
	who may not read this person's punches passes none and gets no break.

	Returns (allowance, {date: values}). Values hold only keys that have one:
	`break_state` "measured" or "not_measured", `break_minutes`, `break_over`.
	(0, {}) when there is nothing to show: no punches, no enabled rule set, or
	no break rule for this person. A constant handful of queries, never one a day.
	"""
	if not any(times_by_date.values()):
		return 0, {}
	rule_set = rule_set_for(company)
	if not rule_set:
		return 0, {}
	dates = sorted(days)
	ctx = prepare(rule_set, dates[0], dates[-1], employee=employee) if dates else None
	if not ctx:
		return 0, {}
	allowance = int(_employee_flags(employee, getdate(dates[0]), ctx)["break_allowance_minutes"] or 0)
	if allowance <= 0:
		return 0, {}

	out = {}
	for date in dates:
		status, shift_name = days[date]
		shift = ctx["shifts"].get(shift_name)
		# The engine holds a day with no shift, or a shift with no length (a night
		# shift ending after midnight), and deducts nothing for an approved leave.
		if status == "On Leave" or not shift or shift[1] <= shift[0]:
			continue
		distinct = punch_minutes(times_by_date.get(date) or ())
		if len(distinct) <= 2:
			continue
		if len(distinct) % 2:
			out[date] = {"break_state": "not_measured"}
			continue
		# The engine's window, as far as a break can tell: every break starts after
		# the first punch, so with shift hours only it is the shift start up to the
		# earlier of the last punch and the shift end, whatever the grace.
		if ctx["shift_hours_only"]:
			start, end = shift[0], min(distinct[-1], shift[1])
		else:
			start, end = distinct[0], distinct[-1]
		minutes = int(round(minutes_on_break(break_gaps(distinct), start, end)))
		values = {"break_state": "measured", "break_minutes": minutes}
		if minutes > allowance:
			values["break_over"] = minutes - allowance
		out[date] = values
	return (allowance, out) if out else (0, {})


def judge(attendance, ctx):
	"""The verdict for one Attendance record. No writes.

	`attendance` is a dict or doc with name, employee, attendance_date, status
	and shift.
	"""
	date = getdate(attendance.attendance_date)
	shift_name = attendance.shift or frappe.db.get_value(
		"Employee", attendance.employee, "default_shift")
	shift = ctx["shifts"].get(shift_name)

	if not shift:
		from alvoraa_portal.payroll_rules import DayVerdict
		v = DayVerdict()
		v.held = True
		v.reasons.append(
			"Held: no shift on this day and none on the employee, so there is no "
			"shift length to measure against.")
		return v

	first_in, last_out, count, gaps = _punches(attendance.employee, date)

	# Slice 063. A half-day LEAVE is Frappe's "Half Day" with a leave
	# application behind it. A "Half Day" with nothing behind it is a short
	# shift marked by Frappe itself, and keeps today's treatment (01d).
	half_day_leave = (attendance.status == "Half Day"
	                  and bool(attendance.get("leave_application")))
	# OD-1 remedy (iv): HR approved a half-day correction for the other half.
	# Frappe links the request to the day only when it is submitted; the
	# docstatus is read to be sure it still stands. Asked only on the rare day
	# that needs it - a half-day leave with a punch missing.
	regularised = bool(
		half_day_leave and count < 2 and attendance.get("attendance_request")
		and frappe.db.get_value("Attendance Request",
		                        attendance.get("attendance_request"), "docstatus") == 1)

	# ATT-06: a confirmation supplies the time the employee left. Only a
	# CONFIRMED record counts - a time typed in and not yet confirmed is a
	# proposal, and the day stays held until somebody stands behind it.
	confirmed_out = None
	if (attendance.get("alvoraa_held_confirmed")
			and attendance.get("alvoraa_confirmed_out_time")):
		confirmed_out = _minutes(attendance.get("alvoraa_confirmed_out_time"))
	flags = _employee_flags(attendance.employee, date, ctx,
	                        shift_grace=shift[2])

	return evaluate_day(
		shift_start=shift[0],
		shift_end=shift[1],
		first_in=first_in,
		last_out=last_out,
		punch_count=count,
		marked_absent=(attendance.status == "Absent"),
		marked_on_leave=(attendance.status == "On Leave"),
		confirmed_out=confirmed_out,
		slabs=ctx["slabs"],
		is_special_day=(date in ctx["special_days"]),
		special_day_multiplier=ctx["multiplier"],
		late_window_from=ctx["window_from"],
		late_window_to=ctx["window_to"],
		late_window_extra_quarters=ctx["window_quarters"],
		half_day_leave=half_day_leave,
		other_half_regularised=regularised,
		shift_hours_only=ctx["shift_hours_only"],
		break_gaps=gaps,
		**flags)


def write_verdict(attendance_name, verdict):
	"""Store the verdict on the Attendance record.

	Written straight to the table rather than through the document, because
	these are read-only computed fields on records that are already submitted.
	`update_modified=False` keeps another session's conflict detection out of
	it - the engine has not changed what a person entered, only what it worked
	out about it.
	"""
	frappe.db.set_value("Attendance", attendance_name, {
		"alvoraa_held": 1 if verdict.held else 0,
		"alvoraa_attendance_percent": round(verdict.attendance_percent, 2),
		"alvoraa_slab_quarters": verdict.slab_quarters,
		"alvoraa_extra_quarters": verdict.extra_quarters,
		"alvoraa_special_day_doubled": 1 if verdict.doubled else 0,
		"alvoraa_reds": verdict.reds,
		"alvoraa_greens": verdict.greens,
		"alvoraa_late_arrival": 1 if verdict.late_arrival else 0,
		"alvoraa_early_departure": 1 if verdict.early_departure else 0,
		"alvoraa_rules_why": " ".join(verdict.reasons),
		"alvoraa_evaluated_on": now(),
	}, update_modified=False)


def evaluate_attendance(attendance_name):
	"""Judge one Attendance record and store the result.

	Returns the verdict, or None if the company has no rule set switched on -
	which is the case for every tenant but DTC, and is not an error.
	"""
	att = frappe.db.get_value(
		"Attendance", attendance_name,
		["name", "employee", "attendance_date", "status", "shift", "company"]
		+ list(LEAVE_FIELDS),
		as_dict=True)
	if not att:
		return None
	rule_set = rule_set_for(att.company)
	if not rule_set:
		return None
	verdict = judge(att, prepare(rule_set, att.attendance_date,
	                             att.attendance_date))
	write_verdict(att.name, verdict)
	return verdict


def on_attendance_submit(doc, method=None):
	"""doc_events hook. Judges the day as it is submitted.

	Wrapped so a rules problem can never block an attendance record being
	saved. Attendance is the input to payroll, and a day that cannot be judged
	still has to be recorded - the reprocess (ATT-07) will pick it up once the
	rule set is fixed.
	"""
	try:
		rule_set = rule_set_for(doc.company)
		if not rule_set:
			return
		write_verdict(doc.name, judge(doc, prepare(
			rule_set, doc.attendance_date, doc.attendance_date)))
	except Exception:
		frappe.log_error(
			title="Payroll rules could not judge {0}".format(doc.name),
			message=frappe.get_traceback())
