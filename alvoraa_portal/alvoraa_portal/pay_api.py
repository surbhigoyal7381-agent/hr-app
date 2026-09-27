"""Wave 3, Pay: why a deduction happened, told to the person it happened to.

This module exists for one screen: the **Why?** sheet behind a loss-of-pay line
on a payslip. It is the most sensitive thing in this wave, and it is the first
place in this product where an employee is told that a decision about their pay
was made by a machine.

**What is actually automated here.** The weekly late-coming job decides that a
person loses a quarter of a day, then half a day of pay. That decision is made
by code, on a schedule, with nobody looking at the week. There is no step
between the calculation and the submitted Additional Salary. Wave 3 does not
change that. It makes it visible, and - within the limits below - contestable.

**It adds no automation of its own.** No recomputation, no automatic reversal.
A correction approved after a deduction was submitted must NOT quietly move
money; that would be more automation applied to a decision that already has too
little. (043 AC-58.)

**The remedy on the screen is the remedy that exists.** Verified in
`hrms/hrms/alvoraa_late_rules/late_rules.py`: `_process_week` does

    if found and found.docstatus == 1:
        existing += 1
        continue

so a submitted Attendance Deduction is skipped by every later run, including
HR's catch-up `run_for_range`. Correcting 4 August in September leaves the
deduction, and the lost pay, exactly where they are. An earlier draft of the
spec would have told 400 people that correcting the day undoes the deduction
because the rule re-reads the attendance record. It does not, and
`test_why_sheet_043` keeps that promise out - the false sentence is not written
out anywhere here, including in this docstring, because the check that keeps it
out has to read the strings.

**Nothing is written on this path.** Showing a person a decision about them must
not create a second record about them - not a read log, not an "acknowledged"
flag, not a timestamp inferred from closing the sheet (AC-61). The record is the
deduction; this is a rendering of it.

**Refusals.** Every refusal from this module is the same sentence `hr_api` gives
for a payslip, `PAYSLIP_UNAVAILABLE`, whatever the cause - somebody else's
deduction, one that does not exist, one still in draft, or a tenant that never
bought payroll. A refusal that varies lets a caller walk names and learn what
exists (AC-31).

No module-level mutable state; every constant here is a tuple (Wave 1 SEC-15).
No `ignore_permissions` anywhere in this file (Wave 1 SEC-6, AC-43).
"""

import frappe
from frappe import _
from frappe.utils import flt

from alvoraa_portal.hr_api import (
	PAYSLIP_UNAVAILABLE,
	_get_employee,
	_me_block,
	_own_payslip,
	_own_slips,
	_payslip_payload,
)
from alvoraa_portal.subscription import requires_feature

# Every top-level key the Why? sheet returns. A fixed list, the same discipline
# as `frame_api.FRAME_KEYS` - "what can this payload contain" is one short list,
# not something worked out per caller.
WHY_KEYS = (
	"deduction",        # the record's own name, so the client can tell two apart
	"rule_name",        # WHICH rule decided it (AC-57.2)
	"decided_on",       # WHEN it was decided (AC-57.2)
	"week_start",
	"week_end",
	"violations",       # the inputs, with which ones were free (AC-57.3)
	"total_violations",
	"counted_violations",
	"free_per_week",
	"per_violation_days",
	"computed_days",
	"deduction_days",
	"rounded_up",       # whether the rounding rule moved the figure
	"round_up_from",
	"round_up_to",
	"taken_from_leave",  # where the days came from (AC-57.5)
	"lwp_days",
	"currency",
	"how_it_was_decided",     # AC-59, one whole sentence each, never fragments
	"if_a_day_is_wrong",
	"what_a_correction_does_not_do",
	"getting_it_put_back",
	"who_to_go_to",
	"accountable_named",      # false when D-7's fallback wording is in use
)

# The violation fields that leave this module. `attendance` (the linked
# Attendance name) is deliberately NOT one of them: it is a document id the
# sheet has no use for, and every extra id is a thing to look up.
VIOLATION_FIELDS = ("attendance_date", "violation_type", "expected_time",
                    "actual_time", "minutes", "counted")


def _refuse():
	"""One sentence, every cause. See the module docstring."""
	frappe.throw(_(PAYSLIP_UNAVAILABLE), frappe.PermissionError)


def _own_deduction(name):
	"""The caller's own submitted Attendance Deduction, or a refusal.

	Ownership is the whole check and it happens HERE, on the server, before
	anything is read - the same shape as `hr_api._own_payslip`, and for the same
	reason: the Employee role holds no read on these records, so there is no
	second line of defence behind this one.
	"""
	emp = _get_employee()
	row = None
	if name and isinstance(name, str):
		row = frappe.db.get_value(
			"Attendance Deduction", name,
			["name", "employee", "docstatus"], as_dict=True)
	if not emp or not row or row.docstatus != 1 or row.employee != emp.name:
		_refuse()
	return frappe.get_doc("Attendance Deduction", row.name)


def _own_additional_salary(additional_salary, employee):
	"""The caller's own Additional Salary row, or a refusal.

	Takes the two things it needs, never a caller-supplied filters dict (043
	`01c` SEC-5). A function that accepts a dict of filters accepts whatever the
	browser sends, and the ownership check is then only as good as the caller's
	manners.

	**Why this refuses rather than answering "nothing behind it".** An earlier
	version returned `{"hand_entered": True}` for anything it could not resolve,
	including somebody else's line. That is uniform, but it breaks AC-28: a line
	belonging to another person must give the SAME refusal as a line that does
	not exist, and "hand entered" is not a refusal - it is an answer about a
	document. Refusing here keeps all four causes identical and keeps
	`hand_entered` meaning exactly one thing: this line is yours, and payroll
	put it there by hand.
	"""
	row = None
	if additional_salary and isinstance(additional_salary, str):
		row = frappe.db.get_value(
			"Additional Salary", additional_salary,
			["name", "employee", "docstatus", "ref_doctype", "ref_docname"],
			as_dict=True)
	if not row or row.docstatus != 1 or row.employee != employee:
		_refuse()
	return row


@frappe.whitelist()
@requires_feature("payroll", message=PAYSLIP_UNAVAILABLE)
def get_deduction_explanation(additional_salary):
	"""Why one loss-of-pay line on the caller's own payslip is what it is.

	Takes the `additional_salary` link `hr_api.get_payslip` puts on the line, so
	the caller never has to know an Attendance Deduction name, and never gets to
	choose one.

	Returns `{"hand_entered": True}` when the line has no Attendance Deduction
	behind it - a component HR typed in by hand. The sheet says so in words
	(AC-29) rather than drawing an empty week, which would read as "the system
	thinks you were late on no days and took your money anyway".
	"""
	emp = _get_employee()
	if not emp:
		_refuse()

	row = _own_additional_salary(additional_salary, emp.name)

	if row.ref_doctype != "Attendance Deduction" or not row.ref_docname:
		# Not a refusal. The line IS the caller's; there is simply nothing
		# behind it, because payroll typed the component in. Saying "not
		# available" here would be a lie to somebody about their own payslip.
		return {"hand_entered": True}

	doc = _own_deduction(row.ref_docname)
	rule = frappe.get_cached_doc("Attendance Deduction Rule", doc.rule)
	return _explanation(doc, rule)


def _explanation(doc, rule):
	"""The payload, built key by key from the stored record.

	**Every figure is READ, not recomputed** (AC-27). The record is what the
	payroll run acted on. Recomputing from today's rule would show a person a
	number that was never applied to them, the moment somebody edits the rule.
	"""
	accountable, named = _accountable_contact(rule)
	rounded_up = flt(doc.deduction_days) != flt(doc.computed_days)

	return {
		"deduction": doc.name,
		"rule_name": rule.rule_name,
		"decided_on": doc.creation,
		"week_start": doc.week_start,
		"week_end": doc.week_end,
		"violations": [
			{field: row.get(field) for field in VIOLATION_FIELDS}
			for row in (doc.violations or [])
		],
		"total_violations": doc.total_violations,
		"counted_violations": doc.counted_violations,
		"free_per_week": int(rule.free_violations_per_week or 0),
		"per_violation_days": flt(rule.deduction_per_violation_days),
		"computed_days": flt(doc.computed_days),
		"deduction_days": flt(doc.deduction_days),
		"rounded_up": rounded_up,
		"round_up_from": flt(rule.round_up_from_days),
		"round_up_to": flt(rule.round_up_to_days),
		"taken_from_leave": [
			{"leave_type": row.leave_type, "days": flt(row.days)}
			for row in (doc.leave_deductions or [])
		],
		"lwp_days": flt(doc.lwp_days),
		"currency": frappe.db.get_value("Company", doc.company, "default_currency"),

		# ── AC-59: the words, one whole message each ──────────────────
		#
		# Whole sentences with placeholders, never a sentence built from
		# fragments, because the figures move in word order between English,
		# Hindi and Punjabi (AC-40).
		"how_it_was_decided": _(
			"This was worked out automatically by the {0} rule on {1}. "
			"Nobody looked at your week by hand."
		).format(rule.rule_name, frappe.format(doc.creation, "Date")),

		"if_a_day_is_wrong": _(
			"If a day in this week is wrong, get it corrected. That puts your "
			"attendance record right and it counts for the weeks after it."
		),

		# The sentence this slice exists to get right. The earlier wording -
		# the one that told people a correction undoes a deduction - is
		# false, and a static check in test_why_sheet_043 keeps it out.
		"what_a_correction_does_not_do": _(
			"It does not undo this deduction. Once the rule has worked a week "
			"out, it does not work it out again."
		),

		"getting_it_put_back": _(
			"Only {0} can cancel a deduction, and only before that month's "
			"payslip is finalised. After that it has to be put right in a "
			"later payroll run."
		).format(accountable),

		"who_to_go_to": _(
			"If you think this is wrong, contact {0}."
		).format(accountable),

		"accountable_named": named,
	}


def _accountable_contact(rule):
	"""Who is accountable for this rule, and whether anybody actually is.

	**D-7 is unanswered and this is its fail-closed default.** `Attendance
	Deduction Rule` has no owner field - checked field by field in
	`attendance_deduction_rule.json`, whose fields are rule_name, company,
	shift_type, enabled, the week and violation settings, deduct_from_leave_
	first, leave_types, lwp_salary_component, daily_wage_basis, exempt_grades,
	notify_employee and notify_manager. There is no per-site "HR contact"
	setting either: HR Settings has none, and the tenant's `hr_email` becomes a
	real HR Manager LOGIN during provisioning, not a contact record. The spec
	marked that `[UNVERIFIED]`; it is verified now, and the answer is that there
	is nowhere to read a name from.

	So the fallback names nobody, says so plainly, and still gives a real route.
	It must never:
      - be blank, which leaves a person with nothing;
      - name "HR", a function that cannot be contacted or held to an answer;
      - imply that a person reviewed this case, because none did.

	When D-7 is answered - a field on the rule is the recommendation - this
	function is the only place that changes.
	"""
	owner = rule.get("accountable_person") if rule.meta.has_field(
		"accountable_person") else None
	if owner:
		full_name = frappe.db.get_value("User", owner, "full_name")
		if full_name:
			return full_name, True
	return _("your HR team - no individual is named on this rule yet"), False


# ── The Pay screen ───────────────────────────────────────────────────────────

# Every top-level key `get_pay` returns. The same fixed-list discipline as
# `WHY_KEYS` above and `frame_api.FRAME_KEYS`.
PAY_KEYS = (
	"me",
	"payslips",
	"latest",
	"year_to_date",
	"take_home",
	"currency",
	"note",
)

# What the screen calls take-home, and why (§20 D-2). The ROUNDED total, because
# that is the figure a person can check against their bank statement; the exact
# net is in the breakdown below it. Wave 2's "your payslip is ready" row must
# make the same choice or the two screens disagree by a rupee, so the choice is
# named here as a constant rather than left implicit in a template.
TAKE_HOME_FIELD = "rounded_total"

NO_PAYSLIPS = "No payslips have been issued to you yet."


@frappe.whitelist()
@requires_feature("payroll", message=PAYSLIP_UNAVAILABLE)
def get_pay():
	"""The whole Pay screen, in one call: the slips, the newest one, the year.

	**Own record only, for everybody, including HR.** There is no wider view of
	this anywhere in the product; HR uses the desk. `_own_payslip` is the whole
	check and it runs on the one slip this opens.

	**The year figure is READ, never added up** (AC-25). Frappe HR stores
	`year_to_date` and `gross_year_to_date` on the slip itself, worked out by
	the payroll run against the payroll period. Summing the twelve slips this
	screen happens to list would give a different number for a mid-year joiner,
	for anyone whose slips do not start in April, and for anyone whose list is
	capped at twelve - and it would be the portal's number rather than payroll's.

	**No comparison with last month** (§20 D-4). August was ₹11,851.61 above
	July at PP Jewellers because of a one-off Diamond Incentive, and there is no
	field anywhere that says a component was one-off. A green "+₹11,851.61 more
	than July" on a payslip reads as a raise, and it is what people screenshot.

	**Payroll rounding is not touched here.** 555 of 800 PP Jewellers slips
	print a net the bank does not pay. That is an open decision, and this screen
	must not make the wrong figure look more authoritative than it is - which is
	why `take_home` is the rounded total, the figure actually paid, with the
	exact net shown beside it rather than instead of it.
	"""
	# A Guest is refused before anything else, and this is not belt-and-braces
	# for its own sake. `@frappe.whitelist()` without `allow_guest` stops a
	# Guest at the REQUEST layer, so in production this line is unreachable -
	# but the empty payload below was written for "a signed-in person with no
	# Employee record", and a Guest fell into it. `test_guest_is_refused` found
	# that by calling the function the way a later caller inside the product
	# would: directly, with no request layer above it. A signed-out caller is
	# not the same thing as a person who has no payroll record, and answering
	# them the same way is how a soft answer ends up behind a hard door.
	if frappe.session.user == "Guest":
		_refuse()

	emp = _get_employee()
	if not emp:
		# Not a refusal: a person with no Employee record has no payslips, and
		# saying "not available" would suggest there is something being kept
		# from them. The frame does not offer Pay to them at all (034 §3).
		return {"me": None, "payslips": [], "latest": None, "year_to_date": None,
		        "take_home": None, "currency": None, "note": _(NO_PAYSLIPS)}

	# `hr_api._own_slips`, not a second copy of the query. This file carries no
	# `ignore_permissions` at all (AC-43), and every payslip read in this
	# product needs one, because the Employee role deliberately holds no read
	# on Salary Slip. So the flag stays in the one module where that pattern is
	# declared and tested, and this list cannot drift from the list the payslip
	# page shows. A cancelled slip is excluded there (AC-53); an amended one is
	# a new document at docstatus 1 while the original sits at 2, so an
	# amendment is listed once, under the name it has now.
	#
	# The first version of this function had the query inline, flag and all.
	# `test_no_ignore_permissions_anywhere_in_these_files` caught it.
	slips = _own_slips(emp.name)
	if not slips:
		return {"me": _me_block(emp), "payslips": [], "latest": None,
		        "year_to_date": None, "take_home": None, "currency": None,
		        "note": _(NO_PAYSLIPS)}

	# The newest slip in full, through the SAME ownership check a direct call
	# to `get_payslip` goes through. The name comes from the list above, which
	# was already filtered to this employee, so the check cannot fail here - and
	# it runs anyway, because a check that is skipped when the caller "must" be
	# right is a check that stops existing the day the list changes.
	latest = _payslip_payload(_own_payslip(slips[0].name))

	stored = frappe.db.get_value(
		"Salary Slip", slips[0].name,
		["year_to_date", "gross_year_to_date"], as_dict=True) or {}

	return {
		"me": _me_block(emp),
		"payslips": slips,
		"latest": latest,
		"year_to_date": {
			"net": flt(stored.get("year_to_date")),
			"gross": flt(stored.get("gross_year_to_date")),
			# Which slip the figure was read off, so a person who thinks it is
			# wrong can point at the document rather than at the screen.
			"from_slip": latest["name"],
			"up_to": latest["end_date"],
		},
		"take_home": flt(latest.get(TAKE_HOME_FIELD)),
		"currency": latest.get("currency"),
		"note": None,
	}
