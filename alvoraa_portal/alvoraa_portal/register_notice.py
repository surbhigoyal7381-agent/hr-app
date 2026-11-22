# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""Slice 088 - the monthly change notice.

When somebody else changes an employee's attendance, that employee has to be able to see
it and agree to it before their pay is locked. In the app that is the Confirm button
(slice 087). On the shop floor most of the people this matters to have no app at all, so
the same agreement happens the way it already happens in the customer's shop: a printed
page, read out if needed, and a signature or a thumb print.

This module owns that paper round:

- which changed days are waiting for which person this month;
- writing one record per print, BEFORE any content leaves the server, so there is always
  a row saying who the page was released to (088 SEC-2);
- the page itself, one A4 sheet per person;
- recording what came back - signed, with a photo of each page, or "not right" with what
  the person said - and nothing in between.

What it does NOT own: whether the change counts, whether pay is held, or what the employee
sees in the app. All of that is `punch_fix`'s, and this module reaches it through exactly
one function, `punch_fix.record_register_signature`.

**None of it appears unless the organisation has asked for it.** The switch is ALV-430's
`punch_fix.CONFIRM_SWITCH` on Company, and it ships off. Off, there is nothing to confirm,
so there is nothing to print, nothing in the list and no sentence on anybody's screen.
DTC and Grace will run with it off (Surbhi, 21 Nov 2026).
"""

import frappe
from frappe import _
from frappe.utils import cint, get_first_day, get_last_day, getdate, nowdate

import hrms.alvoraa_hr_core.access as access
from alvoraa_portal.field_app_limits import SELF_KEY, _limited
from alvoraa_portal.punch_fix import SIGNED_NOTICE, confirms_are_on, signed_column_ready

REQUEST = "Attendance Request"
NOTICE = "Alvoraa Register Notice"
HR_ROLES = {"HR User", "HR Manager", "System Manager"}

#: How many people one response carries. "Show more" asks for the next page
#: (spec AC-7). The number is the designer's, not a database limit.
PAGE = 25

#: Slice 088's own schema. The field itself is read by `punch_fix` - see
#: `punch_fix.SIGNED_NOTICE` for why the name lives there and the column is created here.
FIELDS = {
	REQUEST: [
		{"fieldname": SIGNED_NOTICE, "fieldtype": "Link", "options": NOTICE,
		 "read_only": 1, "label": "Signed On Register Notice",
		 "insert_after": "alvoraa_replaces",
		 "description": "The printed page this change was signed on, for an employee with no app. "
		                "Set only by slice 088 when HR records the signature. The signer and the "
		                "date are read from that notice, never copied here."},
	],
}


def after_migrate():
	"""The one custom field. In both hook lists, because a site built with
	`bench install-app` never runs a migrate (the reason `punch_fix.after_migrate` gives)."""
	if not frappe.db.exists("DocType", REQUEST):
		return False
	if not frappe.db.exists("DocType", NOTICE):
		# The Link's target has to exist first, or the field is created pointing at nothing.
		return False
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(FIELDS)
	_index()
	return True


def _index():
	"""One index on (employee, month): every read in this module asks "this person, this
	month", and without it the notice list scans the table once per person in the list
	(088 OPS-21)."""
	try:
		frappe.db.add_index(NOTICE, ["employee", "month"], index_name="employee_month")
	except Exception:
		# An index that cannot be added is a slow list, not a broken one, and a migrate
		# must not fail on it.
		pass


def columns_ready():
	"""False on a site whose image is newer than its migrate. The readers then behave as
	they did before 088 rather than failing on an unknown column."""
	return signed_column_ready() and frappe.db.exists("DocType", NOTICE)


# ── who needs a notice this month ────────────────────────────────────────────

def _month_of(month):
	"""The first of the month asked for, defaulting to this one. A month we cannot read is
	this month and not an error: a bad argument must not become a stack trace on HR's screen."""
	try:
		return get_first_day(getdate(month)) if month else get_first_day(nowdate())
	except Exception:
		return get_first_day(nowdate())


def _hr_or_refuse(endpoint):
	if not (HR_ROLES & set(frappe.get_roles())):
		access.refuse(_("Change notices are for HR."), "088-SEC-1", endpoint)


def qualifying_changes(month, employees=None, scope=None):
	"""Every change a notice can be about, for the whole month (spec section 5.1).

	A change qualifies when it is an approved punch fix that somebody OTHER than the
	employee filed. Five tests, each one of them load-bearing:

	- a punch fix, not a leave or a plain attendance request;
	- Approved and submitted - "this day now counts X h" is only true after approval, and
	  the figure behind that sentence is written at approval (D-6). A waiting change on a
	  printed page would be a promise, not a record;
	- filed by somebody else. `Administrator` is the break-glass account and is not a
	  person filing for somebody (087 AC-104), so it does not count either;
	- the day falls in the month;
	- not undone, declined or withdrawn.

	It does NOT test whether the change is still open: a person whose changes are all
	confirmed or signed still belongs in the list, shown as done (AC-4). `is_open` on each
	row says which is which.

	**It returns no reason, no time and no hours.** Only what the list and the state need.
	The sheet reads the request itself, under its own permission check, when it is printed.
	"""
	scope = scope if scope is not None else access.permitted_employee_filters()
	filters = dict(scope)
	# `alvoraa_review_status`, not `status`: Attendance Request has no `status` column at
	# all. The first version of this query used one, read from the spec's prose rather than
	# from the table, and every list test died on "Unknown column 'status'". The approval
	# marker is written by `attendance_correction.decide` (:259) and nowhere else.
	filters.update({"docstatus": 1, "alvoraa_review_status": "Approved",
	                "from_date": ("between", [str(month), str(get_last_day(month))]),
	                "alvoraa_undone_on": ("is", "not set")})
	if employees:
		filters["employee"] = ("in", list(employees))
	rows = frappe.get_all(REQUEST, filters=filters, order_by="from_date asc",
	                      fields=["name", "employee", "owner", "modified", "from_date",
	                              "alvoraa_missing_time", "alvoraa_set_aside",
	                              "alvoraa_confirmed_on", "alvoraa_needs_confirm",
	                              SIGNED_NOTICE],
	                      ignore_permissions=True)
	if not rows:
		return []
	logins = {e: u for e, u in frappe.get_all(
		"Employee", filters={"name": ("in", list({r.employee for r in rows}))},
		fields=["name", "user_id"], as_list=True, ignore_permissions=True)}
	out = []
	for r in rows:
		if not (r.alvoraa_missing_time or (r.alvoraa_set_aside or "").strip()):
			continue                                   # not a punch fix at all
		if r.owner == "Administrator" or r.owner == logins.get(r.employee):
			continue                                   # the employee's own, or break-glass
		r["is_open"] = not (r.alvoraa_confirmed_on or r.get(SIGNED_NOTICE))
		out.append(r)
	return out


def _latest_notices(month, employees):
	"""The most recent notice per person for this month, with the requests it covered."""
	if not employees:
		return {}
	rows = frappe.get_all(NOTICE, filters={"month": str(month), "employee": ("in", list(employees))},
	                      fields=["name", "employee", "outcome", "printed_at", "printed_by",
	                              "recorded_by", "recorded_on", "dispute_reason", "page_count"],
	                      order_by="printed_at asc", ignore_permissions=True)
	latest = {}
	for r in rows:
		latest[r.employee] = r                         # ordered ascending, so the last wins
	if latest:
		covered = frappe.get_all("Alvoraa Register Notice Change",
		                         filters={"parent": ("in", [r.name for r in latest.values()])},
		                         fields=["parent", "request", "content_hash"],
		                         ignore_permissions=True)
		for r in latest.values():
			r["covered"] = {c.request: c.content_hash for c in covered if c.parent == r.name}
	return latest


def _state(open_changes, notice, me=None):
	"""One row's state, from the changes and the latest notice (spec section 5.3).

	Returned as a code and the numbers behind it, never as a finished sentence: the words
	are the screen's and have to be translatable, and a server that sends prose cannot be
	checked against the design without comparing strings.

	The `filer` state is last on purpose. It is not a different stage of the paper round -
	the page is printed and waiting either way - it is about WHO is looking. Nobody records
	a signature for a change they filed themselves (SEC-4, and 087's own
	`refuse_own_decision` rule in another shape), so for that one user the row offers Print
	again and nothing else. Computed here rather than left to the screen, because a button
	the browser decides to hide is not a permission.
	"""
	me = me or frappe.session.user
	if not open_changes:
		return {"code": "done", "uncovered": 0, "i_filed": False}
	i_filed = any(c.owner == me for c in open_changes)
	if not notice:
		return {"code": "not_printed", "uncovered": len(open_changes), "i_filed": i_filed}
	covered = notice.get("covered") or {}
	uncovered = [c for c in open_changes if c.name not in covered]
	if uncovered:
		# A change filed or edited since the print is not on the page the employee read.
		return {"code": "changed_after_print", "uncovered": len(uncovered), "i_filed": i_filed}
	if i_filed:
		return {"code": "filer", "uncovered": 0, "i_filed": True}
	if notice.outcome == "Not right":
		return {"code": "not_right", "uncovered": 0, "i_filed": False}
	return {"code": "printed", "uncovered": 0, "i_filed": False}


@frappe.whitelist(methods=["POST"])
@_limited(SELF_KEY, "user", limit=60, window=60)
def list_people(month=None, start=0):
	"""The people whose attendance somebody else changed in a month, and where each one is
	up to (spec section 8.1, US-1).

	**What the response deliberately does not carry.** No reason, no explanation, no time,
	no hours, no request id - only the person, a count and a state (SEC-2). The reason text
	is the most sensitive thing on the whole sheet, it is written by one person about
	another, and a list is the one screen that puts many people's data in one payload. It is
	read once, by the print call, for one person at a time.

	**It is empty when the organisation has not asked for confirmations.** With ALV-430's
	switch off there is nothing waiting for the employee and nothing holding their pay, so
	there is nothing for a notice to say. This is a departure from the approved spec, which
	was written before the switch existed and dropped the idea of a tenant gate (D-5)
	because none existed at the time; recorded as a departure rather than slipped in. It
	has a consequence worth saying out loud: a tenant running with the switch off gets no
	monthly notice, and the monthly notice is one of the four things counsel asked of DTC
	and Grace. Surbhi's decision of 22 Nov 2026, counsel informed.
	"""
	_hr_or_refuse("register_notice.list_people")
	first, start = _month_of(month), max(0, cint(start))
	empty = {"month": str(first), "rows": [], "total": 0, "done": 0, "waiting": 0,
	         "start": start, "page": PAGE}
	if not columns_ready():
		return empty

	scope = access.permitted_employee_filters()
	changes = qualifying_changes(first, scope=scope)
	if not changes:
		return empty

	# One company lookup per company, not per person: a store's list is one branch and
	# nearly always one company, and this call is on HR's critical path before payroll.
	people = {}
	for c in changes:
		people.setdefault(c.employee, []).append(c)
	emps = frappe.get_all("Employee",
	                      filters={"name": ("in", list(people))},
	                      fields=["name", "employee_name", "employee_number", "branch", "company"],
	                      order_by="employee_name asc", ignore_permissions=True)
	asks = {}
	kept = []
	for e in emps:
		if e.company not in asks:
			asks[e.company] = confirms_are_on(e.company)
		if asks[e.company]:
			kept.append(e)
	if not kept:
		return empty

	notices = _latest_notices(first, [e.name for e in kept])
	rows, done, waiting = [], 0, 0
	for e in kept:
		mine = people[e.name]
		open_changes = [c for c in mine if c.is_open]
		state = _state(open_changes, notices.get(e.name))
		if state["code"] == "done":
			done += 1
		else:
			waiting += 1
		notice = notices.get(e.name) or {}
		rows.append({
			"employee": e.name,
			"employee_name": e.employee_name,
			"employee_number": e.employee_number,
			"branch": e.branch,
			"changed_days": len({str(c.from_date) for c in mine}),
			"open_days": len({str(c.from_date) for c in open_changes}),
			"state": state["code"],
			"uncovered": state["uncovered"],
			"i_filed": state["i_filed"],
			# Who printed it and when, so the screen can say "Print opened on {d} by {name}".
			# A name HR may already see on this page, and no change content.
			"printed_at": str(notice.get("printed_at") or "") or None,
			"printed_by": notice.get("printed_by"),
			"recorded_by": notice.get("recorded_by"),
			"recorded_on": str(notice.get("recorded_on") or "") or None,
			"said": notice.get("dispute_reason") if notice.get("outcome") == "Not right" else None,
			"notice": notice.get("name"),
			# Print again is always offered; recording is not offered to the filer.
			"can_tick": state["code"] != "done",
			"can_record": state["code"] in ("printed", "not_right"),
		})
	return {"month": str(first), "rows": rows[start:start + PAGE], "total": len(rows),
	        "done": done, "waiting": waiting, "start": start, "page": PAGE}
