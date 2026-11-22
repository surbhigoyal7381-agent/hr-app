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
import alvoraa_portal.punch_fix as punch_fix
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


def qualifying_changes(month, employees=None, scope=None, with_content=False):
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

	`with_content` is False for the list and True for a sheet, and that is the SEC-2 line:
	the reason, the times and the snapshots are fetched only when one person's page is being
	built, never for a list of many people.

	It does NOT test whether the change is still open: a person whose changes are all
	confirmed or signed still belongs in the list, shown as done (AC-4). `is_open` on each
	row says which is which.

	**It returns no reason, no time and no hours.** Only what the list and the state need.
	The sheet reads the request itself, under its own permission check, when it is printed.
	"""
	# **The scope is resolved to people, not spread onto the request.** The first version
	# did `dict(permitted_employee_filters())` straight into these filters, and it worked
	# only because no test held a Branch permission: Attendance Request has a `company`
	# column but no `branch` one, so the first time a store's HR person opened the list it
	# would have died on "Unknown column 'branch'". Found by the branch test that the
	# break-and-restore pass showed was missing. One extra query returning the permitted
	# employee ids is the honest cost of a scope with two levels in it.
	scope = scope if scope is not None else access.permitted_employee_filters()
	allowed = set(frappe.get_all("Employee", filters=dict(scope), pluck="name",
	                             ignore_permissions=True))
	employees = [e for e in (employees or allowed) if e in allowed]
	if not employees:
		return []
	filters = {}
	# `alvoraa_review_status`, not `status`: Attendance Request has no `status` column at
	# all. The first version of this query used one, read from the spec's prose rather than
	# from the table, and every list test died on "Unknown column 'status'". The approval
	# marker is written by `attendance_correction.decide` (:259) and nowhere else.
	filters.update({"docstatus": 1, "alvoraa_review_status": "Approved",
	                "from_date": ("between", [str(month), str(get_last_day(month))]),
	                "alvoraa_undone_on": ("is", "not set")})
	filters["employee"] = ("in", list(employees))
	fields = ["name", "employee", "owner", "modified", "from_date",
	          "alvoraa_missing_time", "alvoraa_set_aside",
	          "alvoraa_confirmed_on", "alvoraa_needs_confirm", SIGNED_NOTICE]
	if with_content:
		fields += ["creation", "to_date", "reason", "explanation", "half_day", "half_day_date",
		           "alvoraa_missing_log", "alvoraa_fix_before", "alvoraa_fix_after"]
	rows = frappe.get_all(REQUEST, filters=filters, order_by="from_date asc", fields=fields,
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


# ── the printed sheet ────────────────────────────────────────────────────────

#: Changes per A4 page. The designer's number, checked on a real printer (spec section 21).
PER_PAGE = 5

#: People per print. Above this the whole call is refused and nothing is written (AC-13).
MAX_PEOPLE = 100

#: The four sentences the approved prototype prints, and nothing else (prototype-v1
#: `k_out`, `k_in`, `k_brk`, `k_aside`; spec section 5.2). Kept here as plain English on
#: purpose: the paper is English whatever language the screen is in (D-1, and Surbhi's
#: 21 Nov decision that Hindi is not built), so these must NOT go through `_()`, or an HR
#: user working in Hindi would hand a worker a page in a language nobody agreed to print.
WHAT = {
	"out": "Out time {0} added",
	"in": "In time {0} added",
	"brk": "Back after break at {0} added",
	"aside": "Scan at {0} not counted",
}

#: `punch_fix.kind_for`'s four answers, mapped onto the three "added" sentences the
#: prototype draws. A punch that goes out mid-day and one that ends the day are both
#: "Out time added" to the person reading it; the difference matters to the engine, not
#: to them.
KIND_SENTENCE = {"Arrival": "in", "Leaving": "out", "Out for a break": "out",
                 "Back in after a break": "brk"}


def _hm(minutes):
	"""Minutes as the sheet says them: "8 h 30 m"."""
	minutes = int(round(minutes or 0))
	return "%d h %d m" % (minutes // 60, minutes % 60)


def _day_words(date):
	""""Fri 13 Nov" - the real weekday, because a worker finds the day by its name."""
	d = getdate(date)
	return "%s %d %s" % (d.strftime("%a"), d.day, d.strftime("%b"))


def _counts_after(change):
	"""What the day comes to now, from the snapshot written at approval
	(`punch_fix.alvoraa_fix_after`). Read, never recomputed: the sentence on the paper has
	to be the figure the approval actually produced, and recomputing it months later from a
	day that has since been edited again would print a number the employee never agreed to."""
	try:
		after = frappe.parse_json(change.get("alvoraa_fix_after") or "{}")
		return _hm(float(after.get("working_hours") or 0) * 60)
	except Exception:
		return None


def _added_sentence(change):
	"""Which of the three "added" sentences this change earns, worked out from the day as it
	was BEFORE the fix (`alvoraa_fix_before`) rather than from the day as it is now.

	The four-way kind is not stored anywhere - `derive` computes it at filing time and
	`punch_fix` keeps only the IN/OUT it produced. Recomputing from today's punches would
	count the fix's own punch and could word the sentence differently from the page the
	employee signed. The snapshot is the only honest source.
	"""
	when = change.get("alvoraa_missing_time")
	if not when:
		return None
	label = None
	try:
		before_day = frappe.parse_json(change.get("alvoraa_fix_before") or "{}")
		punches = before_day.get("punches") or []
		mins = _minutes(when)
		earlier = sum(1 for p in punches if _minutes(p) < mins)
		label = punch_fix.kind_for(earlier, len(punches) - earlier,
		                           change.get("alvoraa_missing_log") or "IN")
	except Exception:
		label = None
	key = KIND_SENTENCE.get(label) or ("out" if (change.get("alvoraa_missing_log") == "OUT") else "in")
	return WHAT[key].format(_clock(when))


def _minutes(value):
	""""18:30", or a timedelta printed as "18:30:00", as minutes past midnight."""
	text = str(value or "")
	if ":" not in text:
		return 0
	bits = text.split(":")
	return int(bits[0]) * 60 + int(bits[1])


def _clock(value):
	text = str(value or "")
	return text[:5] if ":" in text else text


def _aside_sentences(change):
	"""One "Scan at {t} not counted" per punch this change set aside."""
	out = []
	for name in punch_fix.aside_names(change):
		when = frappe.db.get_value("Employee Checkin", name, "time")
		out.append(WHAT["aside"].format(_clock(str(when).split(" ")[-1]) if when else "?"))
	return out


def _content_hash(change):
	"""A fingerprint of what the request SAID when the page was printed, so a later edit can
	be told from the page the employee actually read (SEC-3). The fields are 087's own
	`CONFIRMED_CONTENT` - what a Confirm vouches for - because the paper vouches for exactly
	the same thing. The hash holds no reason text; that is the point of hashing it."""
	import hashlib

	parts = [str(change.get(f) or "") for f in punch_fix.CONFIRMED_CONTENT]
	return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def sheet_rows(change, filer_login):
	"""One row of the table on the sheet: the day, what changed, who filed it, and why.

	Who filed it follows Surbhi's OQ-1 decision and 087 decision 7: HR is "HR" with no
	name, a manager is named. The approved prototype printed HR's name; she reversed that
	on 21 Nov so the paper matches what the app already shows the employee. The name is
	still on the HR-only notice record, which is where counsel allowed it.
	"""
	kind, who = punch_fix._filer(change.owner, filer_login)
	what = [s for s in [_added_sentence(change)] if s] + _aside_sentences(change)
	return {
		"day": _day_words(change.from_date),
		"what": what,
		"counts": _counts_after(change),
		"filed_role": "HR" if kind == "HR" else "Manager",
		"filed_by": None if kind == "HR" else who,
		"filed_on": str(getdate(change.get("creation") or change.from_date)),
		"why": punch_fix._reason_of(change.get("explanation")),
		"blocks_pay": bool(cint(change.get("alvoraa_needs_confirm"))),
	}


@frappe.whitelist(methods=["POST"])
@_limited(SELF_KEY, "user", limit=10, window=60)
def open_notices(employees, month=None):
	"""Open the printable notices for these people (spec section 8.2, US-2).

	**The record is written before the content leaves, and that order is the requirement.**
	"Printed" means the server released the page, not that paper came out of a machine
	(SEC-2) - there is no way to know the second thing, and a log that only records
	successful printing records nothing about the HR person who opened fifty pages and
	printed none. So every sheet is inserted first; if any insert fails, nothing is
	returned and nothing was printed. AC-12 is the test for exactly this, and the way to
	break it is to move the insert after the return.

	**No sheet is built for a person who is already done.** A page with no changes on it is
	a page that says nothing, and printing one would still write a record claiming the
	employee was shown something.

	All or nothing, in one transaction: a partly written batch would leave some people with
	a record saying they were shown a page that nobody ever handed them.
	"""
	_hr_or_refuse("register_notice.open_notices")
	if isinstance(employees, str):
		employees = frappe.parse_json(employees) if employees.strip().startswith("[") else [employees]
	employees = [e for e in dict.fromkeys(employees or []) if e]
	if not employees:
		frappe.throw(_("Pick at least one person."))
	if len(employees) > MAX_PEOPLE:
		# Refused whole, before a single row is written (AC-13). The number is in the message
		# because "too many" tells HR nothing about what to do next.
		frappe.throw(_("Print up to {0} at a time, then the rest.").format(MAX_PEOPLE))
	if not columns_ready():
		frappe.throw(_("This site has not been updated for the signed register yet."))

	first = _month_of(month)
	scope = access.permitted_employee_filters()
	outside = [e for e in employees if not access.employee_in_scope(e)]
	if outside:
		# The names are not in the message: a refusal must not tell the caller who exists.
		access.refuse(_("Some of those people are outside the ones you look after."),
		              "088-SEC-1", "register_notice.open_notices")

	changes = qualifying_changes(first, employees=employees, scope=scope, with_content=True)
	people = {}
	for c in changes:
		if c.is_open:
			people.setdefault(c.employee, []).append(c)
	if not people:
		frappe.throw(_("Those people have no changed days waiting in {0}.").format(str(first)))

	emps = {e.name: e for e in frappe.get_all(
		"Employee", filters={"name": ("in", list(people))},
		fields=["name", "employee_name", "employee_number", "branch", "company"],
		ignore_permissions=True)}
	asks = {}
	sheets = []
	for employee, mine in sorted(people.items(), key=lambda kv: emps[kv[0]].employee_name or ""):
		e = emps[employee]
		if e.company not in asks:
			asks[e.company] = confirms_are_on(e.company)
		if not asks[e.company]:
			continue
		login = frappe.db.get_value("Employee", employee, "user_id")
		pages = [mine[i:i + PER_PAGE] for i in range(0, len(mine), PER_PAGE)]
		notice = _write_the_notice(e, first, pages)
		for page_no, page in enumerate(pages, start=1):
			rows = [sheet_rows(c, login) for c in page]
			sheets.append({
				"notice": notice.name,
				"employee": employee,
				"employee_name": e.employee_name,
				"employee_number": e.employee_number,
				"branch": e.branch,
				"company": e.company,
				"month": str(first),
				"page_no": page_no,
				"pages": len(pages),
				# Spec section 5.2 and parity P-9: the page reference, plus the print number
				# so a reprint can be told from the page before it.
				"ref": "%s/%s/%d-%d" % (e.employee_number or employee, first.strftime("%Y-%m"),
				                        page_no, len(pages)),
				"print_no": notice.name,
				# D-7: the "your slip waits" line prints only where this page actually holds
				# a change that holds pay. A page of manager additions would make it a lie.
				"pay_line": any(r["blocks_pay"] for r in rows),
				"changes": rows,
			})
	if not sheets:
		frappe.throw(_("Those people have no changed days waiting in {0}.").format(str(first)))
	access.security_logger().info(
		"register_notice printed people=%d sheets=%d month=%s user=%s",
		len({s["employee"] for s in sheets}), len(sheets), str(first), frappe.session.user)
	return {"month": str(first), "sheets": sheets}


def _write_the_notice(employee_row, month, pages):
	"""One notice record for one person's print, with a row per change saying which page it
	went on and what it said at the time. Written under the module's flag, which is what the
	controller checks: a client cannot send a flag."""
	frappe.flags.in_register_notice = True
	try:
		doc = frappe.get_doc({
			"doctype": NOTICE,
			"employee": employee_row.name,
			"month": str(month),
			"printed_by": frappe.session.user,
			"printed_at": frappe.utils.now_datetime(),
			"page_count": len(pages),
			"outcome": "Printed",
			"changes": [{"request": c.name, "page_no": page_no, "content_hash": _content_hash(c)}
			            for page_no, page in enumerate(pages, start=1) for c in page],
		})
		doc.insert(ignore_permissions=True)
		return doc
	finally:
		frappe.flags.in_register_notice = False


# ── recording what came back ─────────────────────────────────────────────────

def _latest_for(employee, month):
	"""The newest notice for this person and month, by `printed_at`."""
	rows = frappe.get_all(NOTICE, filters={"employee": employee, "month": str(month)},
	                      fields=["name"], order_by="printed_at desc, creation desc",
	                      limit=1, ignore_permissions=True)
	return rows[0].name if rows else None


def _still_the_same(change_row):
	"""Is the request still saying what it said when the page was printed?

	SEC-3, and the reason the hash exists. A change whose confirmed content has been edited
	since the print is NOT marked signed: the employee put their thumb on a page describing
	something else. It is left open and named back to HR, who print again. Nothing is
	refused and nothing is lost - the other changes on the page are still marked, because
	they are still true.
	"""
	stored = frappe.db.get_value(REQUEST, change_row.request,
	                             list(punch_fix.CONFIRMED_CONTENT), as_dict=True)
	if not stored:
		return False
	return _content_hash(stored) == change_row.content_hash


def _photo_bytes(payload):
	"""081's decoder and 081's caps, called and not copied (spec section 3).

	A PDF is refused here although 081 accepts one: this is a photograph of a page
	somebody signed, taken on a phone in a shop. A PDF would be a scan made somewhere
	else, which is a different claim about what happened.
	"""
	from alvoraa_portal import expense_evidence as ev

	blob, is_pdf = ev._decode(payload)
	if is_pdf:
		frappe.throw(_("Add a photo of the signed page, not a PDF."), frappe.ValidationError)
	return ev._shrink_to_cap(blob)


def _refuse_a_reused_photo(blob):
	"""SEC-7: the same picture cannot stand for two pages, two people or two months.

	Frappe stores a `content_hash` on every File, so this is one indexed lookup rather
	than a scan. It is the cheapest honest check available: without it one clear photo of
	one signed page could be submitted for a whole shop.
	"""
	import hashlib

	digest = hashlib.md5(blob).hexdigest()           # Frappe's own File.content_hash
	clash = frappe.get_all("File", filters={"content_hash": digest,
	                                        "attached_to_doctype": NOTICE},
	                       fields=["name"], limit=1, ignore_permissions=True)
	if clash:
		frappe.throw(_("That photo was already used."), frappe.ValidationError)
	return digest


def _save_the_photo(notice, page_no, payload):
	"""One private File per signed page, attached to the notice and to nothing else.

	**Attached to the NOTICE and never to the Attendance Request**, which is what keeps the
	employee and their line manager out: a request is readable by both of them, so a photo
	hanging off it would be fetchable by both (SEC-8). The notice has no role row for
	either. AC-44 is the test, and the way to break it is to attach it to the request.
	"""
	from alvoraa_portal import expense_evidence as ev

	blob = _photo_bytes(payload)
	_refuse_a_reused_photo(blob)
	doc = frappe.get_doc({
		"doctype": "File",
		"file_name": ev._stored_name(NOTICE, False),
		"attached_to_doctype": NOTICE,
		"attached_to_name": notice,
		"is_private": 1,
		"content": blob,
		"decode": False,
	})
	doc.save(ignore_permissions=True)
	access.security_logger().info(
		"register_notice photo stored notice=%s page=%d bytes=%d user=%s",
		notice, page_no, len(blob), frappe.session.user)
	return doc.file_url


@frappe.whitelist(methods=["POST"])
@_limited(SELF_KEY, "user", limit=20, window=60)
def record(notice, outcome, photos=None, reason=None):
	"""Record what came back from the paper: signed, or the worker says it is not right
	(spec section 8.3, US-4 and US-5).

	**All or nothing.** One transaction: the notice, the photos and the marks on the changes
	go together. A half-written record would leave a change marked signed with no photo
	behind it, or a photo of a signature that marks nothing - and the first of those is the
	shape of fault this whole slice exists to remove.

	**The covered changes come from the record, never from the caller.** The caller sends a
	notice name and nothing else about which days it covers (SEC-3, AC-31). A list of change
	ids in the body is ignored, because a caller who could choose them could mark a day the
	employee never saw.

	**Nobody records their own, and nobody records a change they filed.** Two different
	rules: `refuse_own_decision` keeps an HR person who is also this employee out, and the
	filer rule keeps out whoever typed the change. The filer is read from the database
	`owner`, never from the screen.
	"""
	_hr_or_refuse("register_notice.record")
	if outcome not in ("Signed", "Not right"):
		frappe.throw(_("Say whether it was signed or not right."))
	doc = frappe.get_doc(NOTICE, notice)
	if not access.employee_in_scope(doc.employee):
		access.refuse(_("That person is outside the ones you look after."),
		              "088-SEC-1", "register_notice.record", NOTICE, notice)
	access.refuse_own_decision(doc.employee, NOTICE, notice, "register_notice.record")
	if doc.outcome in ("Signed", "Not right"):
		frappe.throw(_("This notice has already been answered."))
	if _latest_for(doc.employee, doc.month) != doc.name:
		frappe.throw(_("A newer notice was printed. Use the newer one."))

	covered = list(doc.changes or [])
	mine = [c for c in covered
	        if frappe.db.get_value(REQUEST, c.request, "owner") == frappe.session.user]
	if mine:
		access.refuse(_("You filed a change on this page, so another HR person records "
		                "the signature."),
		              "088-SEC-4", "register_notice.record", NOTICE, notice)

	if outcome == "Not right":
		if not (reason or "").strip():
			frappe.throw(_("Write what they said is not right."))
		return _write_the_answer(doc, "Not right", reason=reason.strip())

	photos = frappe.parse_json(photos) if isinstance(photos, str) else (photos or [])
	if not isinstance(photos, list):
		photos = [photos]
	photos = [p for p in photos if p]
	if len(photos) != cint(doc.page_count):
		# The number is in the message both ways round, because "wrong number of photos"
		# does not tell HR what to do next.
		frappe.throw(_("Add {0} photos, one for each page. You added {1}.").format(
			cint(doc.page_count), len(photos)))
	return _write_the_answer(doc, "Signed", photos=photos)


def _write_the_answer(doc, outcome, photos=None, reason=None):
	"""The one write. Photos first, then the marks, then the notice - so that a refused
	photo stops the whole thing before any change is marked signed."""
	pages = []
	for page_no, payload in enumerate(photos or [], start=1):
		pages.append({"page_no": page_no, "photo": _save_the_photo(doc.name, page_no, payload)})

	marked, stale = [], []
	if outcome == "Signed":
		for c in (doc.changes or []):
			(marked if _still_the_same(c) else stale).append(c.request)
		if marked:
			punch_fix.record_register_signature(marked, doc.name)

	frappe.flags.in_register_notice = True
	try:
		doc.outcome = outcome
		doc.recorded_by = frappe.session.user
		doc.recorded_on = frappe.utils.now_datetime()
		if reason:
			doc.dispute_reason = reason
		for page in pages:
			doc.append("pages", page)
		doc.save(ignore_permissions=True)
	finally:
		frappe.flags.in_register_notice = False

	access.security_logger().info(
		"register_notice recorded notice=%s outcome=%s marked=%d stale=%d photos=%d user=%s",
		doc.name, outcome, len(marked), len(stale), len(pages), frappe.session.user)
	return {"notice": doc.name, "outcome": outcome, "marked": len(marked),
	        "stale": stale, "photos": len(pages)}


@frappe.whitelist(methods=["POST"])
@_limited(SELF_KEY, "user", limit=60, window=60)
def open_photo(notice, page):
	"""Stream one signed page to HR in scope, and write one line saying who looked.

	There is no screen for this in slice 088 (Surbhi's P-14 decision). It exists so that
	the one way to see a signature is a way that gets logged: without it an HR person with
	the file address would open it unlogged, which is the question an employee is entitled
	to have answered."""
	_hr_or_refuse("register_notice.open_photo")
	from alvoraa_portal import expense_evidence as ev

	doc = frappe.get_doc(NOTICE, notice)
	if not access.employee_in_scope(doc.employee):
		access.refuse(_("That person is outside the ones you look after."),
		              "088-SEC-8", "register_notice.open_photo", NOTICE, notice)
	row = next((p for p in (doc.pages or []) if cint(p.page_no) == cint(page)), None)
	if not row or not row.photo:
		frappe.throw(_("There is no photo for that page."))
	ev.log_view(NOTICE, doc.name)
	frappe.local.response.filename = row.photo.split("/")[-1]
	frappe.local.response.filecontent = frappe.get_doc(
		"File", {"file_url": row.photo}).get_content()
	frappe.local.response.type = "download"


# ── who may see a notice at all ──────────────────────────────────────────────

def _scope_sql(table, user=None):
	"""`permitted_employee_filters` as a SQL condition on a table that links Employee.

	Company AND branch, because the helper answers both. A company-only filter would let a
	store's HR person list every store's signed pages, and AC-57's "fails first" is exactly
	that substitution."""
	filters = access.permitted_employee_filters(user)
	if filters.get("name") == ["!=", ""]:
		return ""                                     # everybody
	if filters.get("name") == ["in", []]:
		return "1=0"                                  # nobody
	# The helper returns only these two keys, and the names are checked against this list
	# rather than escaped, because a column name is not a value: escaping one as a value
	# produces a quoted string, not an identifier. Anything unexpected means the helper has
	# changed shape, and the safe answer to that is nobody.
	allowed_fields = ("company", "branch")
	wheres = []
	for field, (op, values) in filters.items():
		if field not in allowed_fields or op != "in":
			return "1=0"
		if not values:
			return "1=0"
		allowed = ", ".join(frappe.db.escape(v) for v in values)
		wheres.append("`tabEmployee`.`%s` in (%s)" % (field, allowed))
	if not wheres:
		return "1=0"
	return ("`tab%s`.employee in (select name from `tabEmployee` where %s)"
	        % (table, " and ".join(wheres)))


def notice_query_conditions(user=None):
	"""Row filter for the notice: HR sees only the people they look after (SEC-1)."""
	return _scope_sql(NOTICE, user)


def notice_has_permission(doc, user=None, permission_type=None):
	"""The same rule for one record opened by name or through the API."""
	if not doc.get("employee"):
		return False
	return bool(access.employee_in_scope(doc.employee, user))


def photo_log_query_conditions(user=None):
	"""SEC-10, AC-47: company-A HR must not list company-B's rows in the photo access log.
	The log had no row filter at all before this slice (`hooks.py` had no entry for it),
	which is the gap 01c found."""
	return _scope_sql("Alvoraa Photo Access Log", user)


# ── the employee's own small view ────────────────────────────────────────────

#: What the employee's row says about where a change has got to (US-7, AC-51 and AC-53).
#: Returned as a code; the screen owns the words, so they can be translated. The employee's
#: screen IS translated, unlike the paper.
MINE_STATES = {
	"waiting": "Not confirmed by you yet.",
	"confirmed": "You confirmed it.",
	"signed": "You signed for it on the register.",
	"shown": "Shown to you. Say if it is not right.",
}


@frappe.whitelist(methods=["POST"])
@_limited(SELF_KEY, "user", limit=60, window=60)
def my_changes(month=None):
	"""This month's days somebody else changed, for the employee themselves (section 8.6).

	**Own record only, and there is no argument for whose.** The call takes a month and
	nothing else: the employee is read from the session, so there is no id a caller could
	swap for a colleague's. That is a stronger guarantee than checking an id and refusing
	the wrong one, and it is cheaper to keep true.

	Unlike the HR list, this one DOES carry the reason and the times - it is this person's
	own record, and the whole point is that they can read what was done to their day and
	say if it is wrong. It carries no photo, no file and no address of one: a signature
	photo is HR's evidence about the employee, not something to hand back to them through
	an API (PRIV-5).

	A Left employee gets nothing: `attendance_correction._me()` is Active only.
	"""
	import alvoraa_portal.attendance_correction as ac

	me = ac._me()
	first = _month_of(month)
	if not columns_ready() or not confirms_are_on(me.company):
		return {"month": str(first), "days": [], "changed": 0}

	mine = qualifying_changes(first, employees=[me.name],
	                          scope=dict(access.ALL_EMPLOYEES), with_content=True)
	days = []
	for c in mine:
		if c.alvoraa_confirmed_on:
			state = "confirmed"
		elif c.get(SIGNED_NOTICE):
			state = "signed"
		elif cint(c.alvoraa_needs_confirm):
			state = "waiting"
		else:
			# A manager's plain addition never waited for a confirm (087), so "not confirmed
			# by you yet" would be a demand the system is not actually making. AC-53.
			state = "shown"
		# `sheet_rows` wants the EMPLOYEE's login, to tell an HR filing from a manager's.
		# Here the caller is the employee, so it is this session's user - named rather than
		# passed as `frappe.session.user` inline, because the two being the same is the
		# reason this works and not a coincidence worth leaving unexplained.
		my_login = frappe.session.user
		row = sheet_rows(c, my_login)
		days.append({
			"request": c.name,
			"date": str(c.from_date),
			"day": row["day"],
			"what": row["what"],
			"counts": row["counts"],
			"filed_role": row["filed_role"],
			"filed_by": row["filed_by"],
			"why": row["why"],
			"state": state,
		})
	return {"month": str(first), "days": days, "changed": len({d["date"] for d in days})}
