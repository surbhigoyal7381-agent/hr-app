"""Wave 3, Time: one person's month, their shift, their leave and the rule that
costs them money - in one call, and in words they can check.

**Why this module exists at all.** Appendix C did not find that people distrust
the portal in the abstract. It measured a 09:25 arrival on a 09:30 shift being
called 25 minutes late, and 27 late days in a month where the real rule counted
four. Slices 017 and 035 fixed the numbers. What was left is the other half of
the same problem: *a correct number nobody can check is still not trusted.* So
this module's job is explanation, not more numbers.

**One call.** `get_time` answers the whole Time screen. The page made about
35-40 queries across several calls before; a screen that asks five questions
shows five different ages of the truth, and on a shop floor phone it shows them
slowly.

**Own record, with one deliberate exception.** Everything here - leave, the
rule, the shift, the year's record - is the caller's own. The month calendar
alone follows `attendance_correction._subject`, which is the control that
already decides whose day-by-day movements a manager or HR may open. When the
subject is not the caller, THIS MODULE RETURNS THE MONTH AND NOTHING ELSE: no
leave balances, no rule, no year record, no shift card. A wider view of a
person's pay or leave is not created here, and adding a key to the non-self
branch is a visibility change, not a convenience.

**Nothing in the copy is a number.** The late-rule explanation is built from the
rule record, clause by clause: the threshold, the free count, the week's start
day, where the days come from. `test_time_rule_043` proves every figure moves
when the record moves, and a static check refuses a `60`, a `Monday` or a leave
type name written into the copy. The old calendar hard-coded Saturday and Sunday
as the weekend and was wrong for every tenant that does not work that way.

**Whole sentences, never fragments** (AC-40). Each clause is one `_()` message
with placeholders, because the figures move in word order between English, Hindi
and Punjabi. Joining "Arriving more than " + n + " minutes" cannot be translated.

No `ignore_permissions` anywhere in this file (Wave 1 SEC-6, 043 AC-43).
No module-level mutable state; every constant is a tuple (Wave 1 SEC-15).
Nothing on this path writes (043 AC-61) - it is a rendering of records that
already exist.
"""

import calendar as _calendar

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from alvoraa_portal import call_cache
from alvoraa_portal.attendance_correction import month as _month_payload

# Every top-level key `get_time` can return, for a caller looking at their own
# month. The same discipline as `frame_api.FRAME_KEYS`: "what can this payload
# contain" is one short list somebody decided, not something worked out per
# caller. `test_time_api_043` asserts the payload's keys against this tuple, so
# a new key is a decision rather than something that arrives by accident.
TIME_KEYS = (
	"me",
	"is_self",
	"month",
	"shift",
	"days_off",
	"leave",
	"rule",
	"record_this_year",
)

# What a caller looking at SOMEBODY ELSE'S month gets. Strictly smaller, and
# strictly the same data the review screen already shows through the same
# control. A test asserts this tuple is a subset of TIME_KEYS and that the
# non-self payload carries nothing outside it.
SUBJECT_KEYS = ("me", "is_self", "month")

# The Employee fields this module reads. A fixed list for the same reason
# `hr_api.ME_FIELDS` is one: five of this product's endpoints hand the browser a
# whole Employee row - date of birth, gender, phone number - and that is pinned
# as declared debt. This module does not become the sixth.
EMP_FIELDS = ("name", "employee_name", "designation", "department", "image",
              "company", "default_shift", "date_of_joining")

# How many weekly-off rows are read to work out which weekdays a person is off.
# A holiday list covers one year, so 104 is already the whole answer for a
# two-day weekend; 400 is room for a list that was built oddly, and a bound so
# that a malformed list cannot become an unbounded read.
WEEKLY_OFF_SCAN = 400

# The year table's ceiling. One row per submitted Attendance Deduction in the
# financial year. At the real PP Jewellers rate - about 212 a tenant a quarter
# across 400 people - one person's own year is a handful of rows. The cap is
# here so that a tenant with a misconfigured weekly job cannot turn one person's
# screen into an unbounded read, and the payload says when it bit (AC-11).
YEAR_ROW_CAP = 120


def _weekday_names(dates):
	"""The distinct weekday names behind a set of dates, in week order.

	Derived, never hard-coded. `get_attendance_calendar` - the endpoint this
	slice retires - assumed Saturday and Sunday, which is wrong for most of the
	tenants this product serves.
	"""
	found = {getdate(d).weekday() for d in dates if d}
	return [_calendar.day_name[n] for n in sorted(found)]


def _shift_card(emp):
	"""Today's shift, and where it came from.

	Frappe HR's own precedence: a Shift Assignment covering today beats
	`Employee.default_shift`. Anything else would show a person the shift they
	are normally on while they are covering somebody else's.

	Returns `{"shift": ..., "starts": ..., "ends": ..., "source": ...}` or a
	`note` when there is nothing to show - never blank times (AC-34). A card
	with empty times reads as "your shift is nothing", which is not a fact.
	"""
	today = nowdate()
	assigned = frappe.get_all(
		"Shift Assignment",
		filters={"employee": emp.name, "docstatus": 1, "status": "Active",
		         "start_date": ("<=", today)},
		or_filters=[["end_date", ">=", today], ["end_date", "is", "not set"]],
		fields=["shift_type"],
		order_by="start_date desc",
		limit=1,
	)
	shift = (assigned[0].shift_type if assigned else None) or emp.get("default_shift")
	source = "assignment" if assigned else ("default" if emp.get("default_shift") else None)
	if not shift:
		return {"shift": None, "source": None,
		        "note": _("No shift is set for you. Ask HR.")}

	row = frappe.db.get_value("Shift Type", shift,
	                          ["name", "start_time", "end_time"], as_dict=True)
	if not row:
		return {"shift": None, "source": None,
		        "note": _("No shift is set for you. Ask HR.")}
	return {
		"shift": row.name,
		"starts": _clock(row.start_time),
		"ends": _clock(row.end_time),
		"source": source,
		"note": None,
	}


def _clock(value):
	"""A Shift Type time as "09:30".

	Frappe stores a Time field as a `timedelta`, whose `str()` is "9:30:00" -
	no leading zero, and a trailing colon once it is cut to five characters.
	`attendance_correction._hhmm` gets this right by doing the arithmetic, so
	the day sheet read "09:30" while the shift card above it read "9:30:" -
	the same fact in two shapes on one screen.
	"""
	if value is None:
		return None
	try:
		minutes = int(round(value.total_seconds() / 60.0))
	except AttributeError:
		# Already a string, from a caller or a fixture that set it that way.
		return str(value)[:5]
	minutes %= 24 * 60
	return "%02d:%02d" % (minutes // 60, minutes % 60)


def _days_off(emp):
	"""The named holidays ahead, and which weekdays this person is off.

	Both come from the employee's OWN holiday list, found the way payroll and
	leave find it - `hr_api._own_upcoming_holidays` wraps ERPNext's
	`get_holiday_list_for_employee`, which Frappe HR answers from Holiday List
	Assignment only. Home used to read every list on the site, so store staff
	were told Head Office's holidays were theirs (slice 035).

	The weekly-off weekdays come from the same list's `weekly_off` rows. This is
	the second question in this call about the same list, which is exactly what
	`call_cache` is for: `get_time` opens a memo, both lookups ask once, and the
	memo dies with the call.
	"""
	from alvoraa_portal.call_cache import holiday_list_for
	from alvoraa_portal.hr_api import _own_upcoming_holidays

	holidays, note = _own_upcoming_holidays(emp.name, nowdate())
	weekdays = []
	holiday_list = holiday_list_for(emp.name, nowdate())
	if holiday_list:
		offs = frappe.get_all(
			"Holiday",
			filters={"parent": holiday_list, "weekly_off": 1},
			pluck="holiday_date",
			limit=WEEKLY_OFF_SCAN,
		)
		weekdays = _weekday_names(offs)
	return {
		"holidays": [{"date": str(h.holiday_date), "description": h.description}
		             for h in holidays],
		"note": note,
		"weekly_off_weekdays": weekdays,
	}


def _past_leave(employee, since):
	"""Leave taken, from both places days actually leave a balance.

	AC-15. A Leave Application is not the only way leave goes: the late-coming
	rule takes days straight out of the ledger, and until this screen showed
	them the balance and the history disagreed by exactly those days. A person
	looking at "8 allocated, 2 applications, 3 left" has no way to find the
	missing three, and the support ticket that follows is the product's fault.

	The ledger rows are labelled, so nobody reads them as leave they asked for.
	"""
	applications = frappe.get_all(
		"Leave Application",
		filters={"employee": employee, "docstatus": 1,
		         "from_date": (">=", since)},
		fields=["name", "leave_type", "from_date", "to_date", "total_leave_days",
		        "status", "half_day"],
		order_by="from_date desc",
		limit=40,
	)
	taken_by_rule = frappe.get_all(
		"Leave Ledger Entry",
		filters={"employee": employee, "docstatus": 1,
		         "transaction_type": "Attendance Deduction",
		         "from_date": (">=", since)},
		fields=["name", "leave_type", "from_date", "to_date", "leaves"],
		order_by="from_date desc",
		limit=40,
	)
	rows = [{
		"kind": "application",
		"name": row.name,
		"leave_type": row.leave_type,
		"from_date": str(row.from_date),
		"to_date": str(row.to_date),
		"days": flt(row.total_leave_days),
		"status": row.status,
		"label": None,
	} for row in applications]
	rows += [{
		"kind": "rule",
		"name": row.name,
		"leave_type": row.leave_type,
		"from_date": str(row.from_date),
		"to_date": str(row.to_date),
		# The ledger stores days going out as a negative number. The screen
		# shows how many days went, so it is flipped here rather than in the
		# browser - a minus sign that means "taken" is a puzzle, not a fact.
		"days": abs(flt(row.leaves)),
		"status": None,
		"label": _("Taken by the late-coming rule"),
	} for row in taken_by_rule]
	rows.sort(key=lambda r: r["from_date"], reverse=True)
	return rows


def _rule_explained(emp):
	"""The late-coming rule that would actually act on this person, in words.

	**Every figure comes from the record** (AC-12). There is no `60` and no
	`Monday` in this function, and no leave type is named in the copy - the
	names come from the rule's own child table. A static check in
	`test_time_rule_043` fails on any of those written into the words.

	Returns `{"covered": False, "note": ...}` when no enabled rule covers this
	person. The tab still exists and says so (AC-35); showing zeros instead
	would read as "the rule is satisfied", which is a different thing entirely
	and the one a person would not query.
	"""
	from hrms.alvoraa_hr_core.features import late_rules_on

	from alvoraa_portal.hr_api import _late_rule_for

	# Switched off in Organisation Settings (26 Sep 2026): the company has no
	# late-coming rule at all, so the tab is not drawn - `switched_on` tells the
	# page. AC-35's "the tab says so" is for a company that HAS a rule which
	# does not cover this person.
	if not late_rules_on():
		return {"covered": False, "switched_on": False, "note": "",
		        "clauses": [], "accountable": None, "accountable_named": False}

	rule = _late_rule_for(emp.name)
	if not rule:
		return {"covered": False, "switched_on": True,
		        "note": _("No late-coming rule applies to you."),
		        "clauses": [], "accountable": None, "accountable_named": False}

	from alvoraa_portal.pay_api import _accountable_contact

	accountable, named = _accountable_contact(rule)
	start_day = rule.week_start_day or _calendar.day_name[0]
	end_day = _week_end_day(start_day)
	leave_types = [row.leave_type for row in (rule.get("leave_types") or [])
	               if row.leave_type]

	# One whole sentence per clause, each with its own placeholders. Never a
	# sentence assembled from pieces - see the module docstring.
	clauses = [
		# The words say "more than" because the code uses `>`
		# (`late_rules.py:75`). 009 design correction D5 chose to change the
		# words rather than the code, and this is where the two meet.
		_("Arriving more than {0} minutes after your shift starts counts as one late day.")
		.format(cint(rule.late_threshold_minutes)),
	]
	if rule.count_early_exit:
		clauses.append(
			_("Leaving more than {0} minutes before your shift ends counts as one as well.")
			.format(cint(rule.early_exit_threshold_minutes)))

	free = cint(rule.free_violations_per_week)
	clauses.append(
		_("Every one of them counts, from the first.") if not free
		else _("The first {0} in a week cost you nothing.").format(free))

	clauses.append(_("Weeks are counted from {0} to {1}.").format(
		_(start_day), _(end_day)))
	clauses.append(
		_("Each one after the free ones costs {0} of a day.")
		.format(flt(rule.deduction_per_violation_days)))
	clauses.append(
		_("When a week's total reaches {0} days it is rounded up to {1}.")
		.format(flt(rule.round_up_from_days), flt(rule.round_up_to_days)))
	clauses.append(
		_("The days come out of your leave balance first, and out of your pay "
		  "once there is no leave left.") if (rule.deduct_from_leave_first and leave_types)
		else _("The days come out of your pay."))

	return {
		"covered": True,
		"note": None,
		"rule_name": rule.rule_name,
		"late_threshold_minutes": cint(rule.late_threshold_minutes),
		"counts_early_exit": bool(rule.count_early_exit),
		"early_exit_threshold_minutes": (cint(rule.early_exit_threshold_minutes)
		                                 if rule.count_early_exit else 0),
		"free_violations_per_week": free,
		"deduction_per_violation_days": flt(rule.deduction_per_violation_days),
		"round_up_from_days": flt(rule.round_up_from_days),
		"round_up_to_days": flt(rule.round_up_to_days),
		"week_start_day": start_day,
		"week_end_day": end_day,
		"deduct_from_leave_first": bool(rule.deduct_from_leave_first),
		"leave_types": leave_types,
		"clauses": clauses,
		# AC-60. A person, where the rule names one; otherwise the fail-closed
		# fallback, which never implies that anybody reviewed the week.
		"accountable": accountable,
		"accountable_named": named,
	}


def _week_end_day(start_day):
	"""The day before the week's start day, by name.

	Derived from the record's own `week_start_day` rather than written down, so
	a tenant whose week runs Sunday to Saturday reads Sunday to Saturday.
	"""
	names = list(_calendar.day_name)
	try:
		index = names.index(start_day)
	except ValueError:
		index = 0
	return names[(index - 1) % 7]


def _record_this_year(employee, company):
	"""Every week the rule took days off this person, grouped by month.

	**The money lands in the `week_end` month** (AC-13). A week that runs 29
	September to 5 October is paid in October, so it belongs in October's row -
	grouping by `week_start` would put it in September and the row would not
	match the payslip it appears on.

	One query, grouped in Python from the same rows the months are built from,
	so a month's figure and the weeks listed under it cannot be worked out two
	ways (§6, AC-11).
	"""
	from alvoraa_portal.hr_api import _leave_year_start

	since = _leave_year_start(nowdate(), company)
	rows = frappe.get_all(
		"Attendance Deduction",
		filters={"employee": employee, "docstatus": 1,
		         "week_end": (">=", since)},
		fields=["name", "week_start", "week_end", "deduction_days", "lwp_days",
		        "counted_violations"],
		order_by="week_end desc",
		limit=YEAR_ROW_CAP,
	)
	months = {}
	for row in rows:
		end = getdate(row.week_end)
		key = "%04d-%02d" % (end.year, end.month)
		bucket = months.setdefault(key, {"month": key, "days": 0.0, "weeks": []})
		bucket["days"] = round(bucket["days"] + flt(row.deduction_days), 2)
		bucket["weeks"].append({
			"deduction": row.name,
			"week_start": str(row.week_start),
			"week_end": str(row.week_end),
			"days": flt(row.deduction_days),
			"lwp_days": flt(row.lwp_days),
			"counted_violations": cint(row.counted_violations),
		})
	ordered = [months[k] for k in sorted(months, reverse=True)]
	return {
		"from_date": str(since),
		"months": ordered,
		# The one number at the top equals the sum of the months below it,
		# which equal the weeks below them. Computed once, here, from the rows
		# the lists are rendered from (AC-11).
		"total_days": round(sum(m["days"] for m in ordered), 2),
		"weeks_listed": len(rows),
		# Surbhi's standing rule: a count that could be short says so, rather
		# than quietly disagreeing with the list it links to.
		"capped": len(rows) >= YEAR_ROW_CAP,
		"cap": YEAR_ROW_CAP,
	}


def _me_block(emp):
	"""The six-key `me` block, named key by key.

	Deliberately not a comprehension over a row: the point of a fixed key list
	is that a reviewer reads the payload here rather than working out what the
	Employee query happens to select today.
	"""
	return {
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"designation": emp.get("designation"),
		"department": emp.get("department"),
		"image": emp.get("image"),
		"company": emp.get("company"),
	}


@frappe.whitelist()
def get_time(year=None, month=None, employee=None):
	"""The whole Time screen, in one call.

	`employee` is how a manager or HR opens somebody else's month, and it goes
	through `attendance_correction._subject` - the control that already governs
	that, refusals and wording included. When the subject is not the caller the
	answer stops at the month: see SUBJECT_KEYS and the module docstring.
	"""
	# The memo lives for this call and is thrown away in the `finally`, whatever
	# happens. It exists because two things in this call ask the same question -
	# which holiday list is this person on - and the answer cannot change
	# between two lines that do not write. It is not a cache: nothing here
	# outlives the call, so a person moved to another list at 10:00 is on the
	# new one at 10:00.
	call_cache.open_cache()
	try:
		return _get_time(year, month, employee)
	finally:
		call_cache.close_cache()


def _get_time(year, month, employee):
	payload = _month_payload(year=year, month=month, employee=employee)
	is_self = bool(payload.get("is_self"))
	subject = payload.get("employee")

	if not is_self:
		# Somebody else's month. The month and who it is about, and nothing
		# else. Adding a key here widens what a manager may see about a person's
		# pay or leave, which §5 forbids for every persona including HR.
		return {
			"me": {"employee": subject,
			       "employee_name": payload.get("employee_name")},
			"is_self": False,
			"month": _month_block(payload, None),
		}

	emp = frappe.db.get_value("Employee", subject, list(EMP_FIELDS), as_dict=True)
	if not emp:
		# `_subject` already proved this caller has an Active Employee record,
		# so this is a record that vanished between two statements. Fail closed
		# rather than draw a screen with nothing behind it.
		frappe.throw(_("Your user is not linked to an employee record, so there is "
		               "no attendance to show."), frappe.PermissionError)

	return {
		"me": _me_block(emp),
		"is_self": True,
		"month": _month_block(payload, emp.get("date_of_joining")),
		"shift": _shift_card(emp),
		"days_off": _days_off(emp),
		"leave": _leave_block(emp),
		"rule": _rule_explained(emp),
		"record_this_year": _record_this_year(emp.name, emp.get("company")),
	}


def _leave_block(emp):
	"""What is left, and where the rest went.

	The balance is Frappe HR's ledger figure through `_ledger_leave_balances`
	(slice 035), which is the same number the apply-leave preview and the late
	rule read. Before that the portal worked leave out for itself and 97 people
	at PP Jewellers were shown 76 days of Casual Leave they did not have.

	`_ledger_leave_balances`'s own docstring says every caller must check who
	may see this employee first. The caller here is the employee themselves -
	`_get_time` only reaches this branch when `_subject` returned `is_self`.
	"""
	from alvoraa_portal.hr_api import _ledger_leave_balances, _leave_year_start

	balances = _ledger_leave_balances(emp.name, nowdate())
	since = _leave_year_start(nowdate(), emp.get("company"))
	return {
		"balances": [{
			"leave_type": row["leave_type"],
			"total": row["total"],
			"taken": row["taken"],
			"pending": row["pending"],
			"expired": row["expired"],
			"left": row["balance"],
		} for row in balances],
		"past": _past_leave(emp.name, since),
		"since": str(since),
	}


def _month_block(payload, joined_on):
	"""The calendar, with the two things the month payload did not carry.

	`attendance_correction.month` already assembles the days, the punches, the
	true minutes and the grace. Two things Wave 3 needs were not in it:

	  * **a weekly off told apart from a public holiday** (AC-1). Both arrive as
	    Holiday rows; only `weekly_off` says which is which, and drawing a
	    weekly off in the same colour as Diwali makes a person's week look wrong.
	  * **the joining date** (AC-45). Days before a person joined are not drawn
	    as anything and are not counted, so a mid-month joiner does not read
	    twelve red days as their own record.

	Both are added in `attendance_correction` itself rather than re-derived
	here, so the review screen and this screen cannot disagree about a day.
	"""
	days = payload.get("days") or []
	if joined_on:
		joined = getdate(joined_on)
		for day in days:
			day["before_joining"] = getdate(day["date"]) < joined
	else:
		for day in days:
			day["before_joining"] = False

	return {
		"year": payload.get("year"),
		"month": payload.get("month"),
		"last_day": payload.get("last_day"),
		"days": days,
		# Recomputed from the same array the list is rendered from, now that
		# the before-joining days are marked (AC-11, AC-45).
		"totals": _totals(days),
		"late_grace_mins": payload.get("late_grace_mins"),
		"tolerance_mins": payload.get("tolerance_mins"),
		"can_request": payload.get("can_request"),
		"can_review": payload.get("can_review"),
		"joined_on": str(joined_on) if joined_on else None,
	}


def _totals(days):
	"""The month's figures, over the days the person was actually employed.

	`attendance_correction._totals` counts every day in the month. That is right
	for the review screen, which has no joining date to hand; it is wrong for a
	mid-month joiner's own screen, where the eleven days before they started
	would be counted as days with no record (AC-45).

	Each figure is taken from the same array the day list renders, so the number
	and the list it links to cannot be worked out two ways (§6, AC-11).
	"""
	from alvoraa_portal.attendance_correction import _totals as _base_totals

	live = [d for d in days if not d.get("before_joining")]
	totals = _base_totals(live)
	totals["weekly_offs"] = len([d for d in live if d.get("weekly_off")])
	# A public holiday is a named day off; a weekly off is the shape of the
	# week. `_base_totals` counts both as `holiday`, so the named ones are the
	# difference - and the two rows below the calendar then add up to what the
	# calendar draws.
	totals["named_holidays"] = max(totals.get("holiday", 0) - totals["weekly_offs"], 0)
	totals["before_joining"] = len(days) - len(live)
	return totals
