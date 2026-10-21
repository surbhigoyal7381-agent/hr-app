"""Slice 063: DTC's leave rules, on every door.

Everything here applies only where the employee's company has an ENABLED
`Alvoraa Payroll Rule Set` - asked through `rule_set_for(company)`, the switch
the pay engine already uses (SEC-15). No company or site name appears in code.
Every other tenant gets nothing from this module.

What lives here, and why here rather than in hr_api.py: the hooks need a home,
`hr_api.py` is the busiest server file, and keeping every DTC rule beside the
others makes "each one asks rule_set_for" checkable in one read.

- `validate_leave_application`  Leave Application validate: current month only
                                (SEC-6) and Leave Without Pay up to 5 a calendar
                                month (SEC-13). Runs at filing AND at approval,
                                from the portal, REST, the desk and imports.
- `notify_chain_on_approval`    Leave Application on_submit: every manager up the
                                Reports To chain gets four facts (PRIV-1).
- `lock_paid_leaves`            Leave Type: "Paid Leaves" is created once with the
                                right flags and then cannot be changed (D1).
- `prepare_half_day_correction` Attendance Request before_insert: lets a half-day
                                correction reach a half-day leave day (OD-1 iv).
- `paid_leaves_card`, `types_offered`, `preview_facts`, notices N-5 and N-6.

No `ignore_permissions` anywhere in this file (ceiling 0 in the SEC-16 test).
Reads use `frappe.get_all`, which does not check permissions, so EVERY read here
is filtered on an employee the caller has already been checked for.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_first_day, get_last_day, getdate, nowdate

from alvoraa_portal.payroll_rules_apply import PAID_LEAVES, rule_set_for

# Surbhi, 21 Oct 2026: "not more than 5" Leave Without Pay days, per calendar
# month, counting requests that are waiting or approved; a half day is 0.5.
# A constant on purpose - no setting, no field (SEC-13).
LWP_MONTH_LIMIT = 5

# How far up Reports To a notice walks. DTC's longest line is 2; the cap only
# stops a broken tree (PRIV-1).
CHAIN_CAP = 10

HR_ROLES = ("HR Manager", "HR User")

# The flags "Paid Leaves" must be created with (spec 7.3, D1).
PAID_LEAVES_FLAGS = (("is_lwp", 0), ("allow_negative", 1), ("allow_encashment", 0),
                     ("is_carry_forward", 0), ("is_earned_leave", 0))

# The card's keys, named one by one (SEC-1). The test asserts the block's keys
# are a subset of this list and never anything else, so a field added to
# MonthSummary later cannot reach the employee by accident.
CARD_KEYS = ("month", "class", "category", "earns", "credited", "used", "used_dates",
             "waiting", "waiting_from", "to_be_paid_out", "approver", "lwp_in_play",
             "lwp_limit", "attended_so_far", "attended_up_to", "gate")


# ── small facts ──────────────────────────────────────────────────────────────


def rules_for_employee(employee):
	"""The enabled rule set of this employee's company, or None."""
	return rule_set_for(frappe.db.get_value("Employee", employee, "company"))


def rule_set_switched_off(company):
	"""A rule set exists for the company but is not enabled (DTC today, SEC-2)."""
	return bool(company and frappe.db.exists("Alvoraa Payroll Rule Set",
	                                         {"company": company, "enabled": 0}))


def is_lwp(leave_type):
	return bool(leave_type and frappe.db.get_value("Leave Type", leave_type, "is_lwp"))


def lwp_type():
	"""The Leave Without Pay type offered in the Apply list (D5): Frappe's own
	name if it exists, otherwise the first type marked leave without pay."""
	if frappe.db.get_value("Leave Type", "Leave Without Pay", "is_lwp"):
		return "Leave Without Pay"
	return frappe.db.get_value("Leave Type", {"is_lwp": 1}, "name", order_by="name asc")


def day_label(d):
	"""'Fri 30 Oct'. English: the notices are English (spec assumption)."""
	d = getdate(d)
	return "{0} {1} {2}".format(d.strftime("%a"), d.day, d.strftime("%b"))


def range_label(a, b):
	return day_label(a) if getdate(a) == getdate(b) else "{0} to {1}".format(day_label(a), day_label(b))


def days_label(n):
	n = flt(n)
	shown = int(n) if n == int(n) else n
	return _("{0} day").format(shown) if n == 1 else _("{0} days").format(shown)


def _month_bounds(day):
	day = getdate(day)
	return get_first_day(day), get_last_day(day)


def _days_inside(employee, leave_type, from_date, to_date, half_day, half_day_date, start, end):
	"""The days of one request that fall between start and end, counted the way
	Frappe counts them (holidays per the type's include_holiday, a half day 0.5)."""
	from hrms.hr.doctype.leave_application.leave_application import get_number_of_leave_days

	a, b = max(getdate(from_date), getdate(start)), min(getdate(to_date), getdate(end))
	if a > b:
		return 0.0
	hd = bool(cint(half_day) and half_day_date and a <= getdate(half_day_date) <= b)
	return flt(get_number_of_leave_days(employee, leave_type, a, b, 1 if hd else 0,
	                                    half_day_date if hd else None))


def lwp_rows_in_month(employee, day, exclude=None):
	"""This employee's Leave Without Pay requests that are waiting or approved
	and touch the month of `day`, with their days inside that month. One query."""
	start, end = _month_bounds(day)
	lwp_types = frappe.get_all("Leave Type", filters={"is_lwp": 1}, pluck="name")
	if not lwp_types:
		return []
	filters = {"employee": employee, "leave_type": ["in", lwp_types],
	           "status": ["in", ["Open", "Approved"]], "docstatus": ["<", 2],
	           "from_date": ["<=", end], "to_date": [">=", start]}
	if exclude:
		filters["name"] = ["!=", exclude]
	rows = frappe.get_all("Leave Application", filters=filters,
	                      fields=["name", "leave_type", "from_date", "to_date", "half_day",
	                              "half_day_date", "status"],
	                      order_by="from_date asc")
	for r in rows:
		r["days"] = _days_inside(employee, r.leave_type, r.from_date, r.to_date,
		                         r.half_day, r.half_day_date, start, end)
	return rows


def lwp_in_play(employee, day, exclude=None):
	return sum(r["days"] for r in lwp_rows_in_month(employee, day, exclude))


# ── SEC-6 and SEC-13, on Leave Application validate ─────────────────────────


def validate_leave_application(doc, method=None):
	"""Current month only; Leave Without Pay up to 5 a calendar month.

	Runs when a request is filed and again when it is approved (approving is a
	submit, and submit validates), whichever door it comes through. A request
	being withdrawn, declined or cancelled is never refused: freeing days must
	always work. Reads only.
	"""
	if doc.status in ("Cancelled", "Rejected") or doc.docstatus == 2:
		return
	company = doc.company or frappe.db.get_value("Employee", doc.employee, "company")
	if not rule_set_for(company):
		return

	today = getdate(nowdate())
	first = get_first_day(today)
	if getdate(doc.from_date) < first:
		if doc.status == "Approved":
			frappe.throw(
				_("This leave is for a day before 1 {0}, so it can no longer be approved.")
				.format(_(today.strftime("%B"))),
				title=_("Leave not approved"))
		frappe.throw(_("Leave can only be asked for days in {0}.").format(_(today.strftime("%B"))),
		             title=_("Leave not sent"))

	if not is_lwp(doc.leave_type):
		return
	month = get_first_day(doc.from_date)
	while month <= getdate(doc.to_date):
		end = get_last_day(month)
		mine = _days_inside(doc.employee, doc.leave_type, doc.from_date, doc.to_date,
		                    doc.half_day, doc.half_day_date, month, end)
		total = lwp_in_play(doc.employee, month, exclude=doc.name) + mine
		if mine and total > LWP_MONTH_LIMIT:
			frappe.throw(
				_("This leave would take Leave Without Pay in {0} to {1} days. The limit is {2} "
				  "days a month, counting requests that are waiting or approved.")
				.format(_(month.strftime("%B")), _fmt_days(total), LWP_MONTH_LIMIT),
				title=_("Over the Leave Without Pay limit"))
		month = add_days(end, 1)


def _fmt_days(n):
	n = flt(n)
	return int(n) if n == int(n) else n


# ── PRIV-1: the chain notice ─────────────────────────────────────────────────


def chain_of(employee):
	"""Managers above this employee in Reports To, nearest first.

	Stops at the top, at a person seen before (a loop: one security-log line,
	ids only), at a manager who is not Active (a leaver's own reports_to is
	stale), or after CHAIN_CAP steps. Not the seat tree (slice 064). One read
	per step.
	"""
	from hrms.alvoraa_hr_core.access import log_refusal

	out, seen = [], {employee}
	node = frappe.db.get_value("Employee", employee, "reports_to")
	while node and len(out) < CHAIN_CAP:
		if node in seen:
			log_refusal("063-PRIV-1-loop", "leave_rules.chain_of", "Employee", employee)
			break
		seen.add(node)
		row = frappe.db.get_value("Employee", node,
		                          ["name", "employee_name", "user_id", "status", "reports_to"],
		                          as_dict=True)
		if not row or row.status != "Active":
			break
		out.append(row)
		node = row.reports_to
	return out


def _notice_users(user_ids, exclude=None):
	"""Enabled users, as the e-mail addresses Frappe's notification helper takes."""
	ids = [u for u in dict.fromkeys(user_ids) if u and u not in ("Administrator", "Guest")
	       and u != exclude]
	if not ids:
		return []
	return frappe.get_all("User", filters={"name": ["in", ids], "enabled": 1}, pluck="email")


def _send(doc, emails, subject, body):
	"""One desk bell each, and the e-mail where the user's settings allow it.
	Frappe's own helper, called directly so the rows exist before the caller
	reads them back (the "who was told" line counts real rows)."""
	if not emails:
		return
	from frappe.desk.doctype.notification_log.notification_log import make_notification_logs

	make_notification_logs(frappe._dict({
		"type": "Alert", "document_type": "Leave Application", "document_name": doc.name,
		"subject": subject, "email_content": body, "from_user": frappe.session.user,
	}), emails)


CHAIN_SUBJECT_MARK = " will be away on "


def notify_chain_on_approval(doc, method=None):
	"""On approval: every manager up the chain gets four facts - name, dates,
	days, "approved". Never the leave type, the reason, the approver or a job
	title (PRIV-1, S1). Nothing on decline, withdraw or cancel (S2). DTC only.

	Built in code, not as a Frappe Notification record, which any System
	Manager could edit to add the reason. Never blocks the approval: a failure
	is logged with the document name only.
	"""
	try:
		if doc.status != "Approved" or not rule_set_for(doc.company):
			return
		chain = chain_of(doc.employee)
		own_user = frappe.db.get_value("Employee", doc.employee, "user_id")
		emails = _notice_users([m.user_id for m in chain], exclude=own_user)
		name = doc.employee_name or doc.employee
		first = name.split(" ")[0]
		dates = range_label(doc.from_date, doc.to_date)
		subject = _("{0} will be away on {1}").format(name, dates)
		body = "<p>{0}</p><p>{1}</p><p>{2}</p>".format(
			frappe.utils.escape_html(_("{0}'s leave for {1} ({2}) has been approved.")
			                         .format(name, dates, days_label(doc.total_leave_days))),
			frappe.utils.escape_html(_("You are told because {0} is in your team. There is "
			                           "nothing for you to do.").format(first)),
			frappe.utils.escape_html(_("You can see your team's leave on the Team View page.")))
		_send(doc, emails, subject, body)
	except Exception:
		frappe.log_error(title="Leave chain notice not sent for {0}".format(doc.name),
		                 message=frappe.get_traceback())


def told_for(application_names):
	"""{application: users told} from the chain notices actually created."""
	if not application_names:
		return {}
	out = {}
	for r in frappe.get_all("Notification Log",
	                        filters={"document_type": "Leave Application",
	                                 "document_name": ["in", list(application_names)],
	                                 "subject": ["like", "%" + CHAIN_SUBJECT_MARK + "%"]},
	                        fields=["document_name", "for_user"]):
		out.setdefault(r.document_name, set()).add(r.for_user)
	return out


def told_top(employee, users):
	"""(how many were told, the highest of them in the chain) - from real rows."""
	if not users:
		return 0, None
	chain = chain_of(employee)
	told = [m for m in chain if m.user_id in users]
	return len(users), (told[-1].employee_name if told else None)


def decision_facts(doc):
	"""After Approve or Decline in the Inbox (R-58, R-59, X-4). Says "has been
	told" only when it is true: Frappe e-mails the employee only where an
	address exists and leave notifications are on. DTC only."""
	if not rule_set_for(doc.company):
		return {}
	from hrms.utils import get_employee_email

	out = {"first": (doc.employee_name or doc.employee).split(" ")[0],
	       "leave_type": doc.leave_type,
	       "dates": range_label(doc.from_date, doc.to_date),
	       "employee_emailed": bool(
		       get_employee_email(doc.employee)
		       and frappe.db.get_single_value("HR Settings", "send_leave_notification"))}
	if doc.status == "Approved":
		users = told_for([doc.name]).get(doc.name, set())
		out["told_n"], out["told_top"] = told_top(doc.employee, users)
	return out


# ── N-5 and N-6: who is told when a request is withdrawn or cancelled ────────


def hr_users_in_scope(employee):
	"""HR Managers and HR Users whose scope (companies AND branches) holds this
	employee, never the employee themselves. A handful of people per tenant (7 at
	DTC), each asked with the same rule the Inbox uses."""
	from hrms.alvoraa_hr_core.access import permitted_employee_filters

	own = frappe.db.get_value("Employee", employee, "user_id")
	users = frappe.get_all("Has Role", filters={"role": ["in", list(HR_ROLES)],
	                                            "parenttype": "User"},
	                       pluck="parent", distinct=True)
	users = frappe.get_all("User", filters={"name": ["in", users or [""]], "enabled": 1,
	                                        "user_type": "System User"},
	                       pluck="name", order_by="full_name asc")
	out = []
	for u in users:
		if u in ("Administrator", own):
			continue
		if frappe.db.exists("Employee", dict(permitted_employee_filters(u), name=employee)):
			out.append(u)
	return out


def notify_withdrawn(doc):
	"""N-5: the approver (Paid Leaves) or HR in scope (LWP) learn a waiting
	request was withdrawn. No type, no reason."""
	if is_lwp(doc.leave_type):
		users = hr_users_in_scope(doc.employee)
	else:
		users = [doc.leave_approver] if doc.leave_approver else []
	name = doc.employee_name or doc.employee
	_send(doc, _notice_users(users, exclude=frappe.session.user),
	      _("{0} cancelled a leave request").format(name),
	      "<p>{0}</p>".format(frappe.utils.escape_html(
		      _("{0} cancelled the request for {1} ({2}). There is nothing for you to do.")
		      .format(name, range_label(doc.from_date, doc.to_date),
		              days_label(doc.total_leave_days)))))
	return users


def notify_cancelled(doc):
	"""N-6: HR in scope learn an approved leave was cancelled before it began.
	Managers up the chain are NOT told (S2); the employee's confirm says so."""
	users = hr_users_in_scope(doc.employee)
	name = doc.employee_name or doc.employee
	_send(doc, _notice_users(users, exclude=frappe.session.user),
	      _("{0} cancelled approved leave").format(name),
	      "<p>{0}</p>".format(frappe.utils.escape_html(
		      _("{0} cancelled their approved leave for {1} ({2}) and is expected at work.")
		      .format(name, range_label(doc.from_date, doc.to_date),
		              days_label(doc.total_leave_days)))))
	return users


# ── D1: "Paid Leaves" is locked ──────────────────────────────────────────────


def lock_paid_leaves(doc, method=None, *args, **kwargs):
	"""Created once with the right flags; after that nobody but Administrator
	may change, rename or delete it. Only where some company has an enabled rule
	set - everywhere else "Paid Leaves" is an ordinary name (AC-96..98)."""
	if (doc.get("leave_type_name") or doc.name) != PAID_LEAVES:
		return
	if not frappe.db.exists("Alvoraa Payroll Rule Set", {"enabled": 1}):
		return
	if frappe.session.user == "Administrator":
		return
	if method == "validate" and doc.is_new():
		if any(cint(doc.get(f)) != v for f, v in PAID_LEAVES_FLAGS):
			frappe.throw(_("Paid Leaves must be created with: not leave without pay, negative "
			               "balance allowed, no encashment, no carry forward, not earned leave."))
		return
	frappe.throw(_("Paid Leaves is set up for the pay rules and cannot be changed or deleted."),
	             frappe.PermissionError)


# ── OD-1 remedy (iv): a half-day correction on a half-day leave day ──────────


def prepare_half_day_correction(doc, method=None):
	"""Attendance Request before_insert, which runs before Frappe's validate.

	Frappe refuses a correction on a date that already carries an approved
	half-day leave ("Attendance status unchanged" / "On Leave" - proved on the
	bench, 21 Oct 2026), because the leave wrote the other half as Present.
	When that half really has no complete pair of punches, record the truth -
	the other half is Absent - and Frappe's own designed path then accepts the
	half-day correction and, on HR's approval, marks the half Present and links
	the request to the day. The engine reads that link (payroll_rules_apply.judge).

	The request also takes the attendance row's shift. DTC's rows carry a shift
	and DTC has no Shift Assignments, so without it Frappe would not find the row
	and would make a second attendance for the same day (proved, 21 Oct).

	If the request then fails for any other reason, the whole save rolls back
	and the row is as it was.
	"""
	if not cint(doc.half_day) or not doc.half_day_date:
		return
	day = getdate(doc.half_day_date)
	if getdate(doc.from_date) != day or getdate(doc.to_date) != day:
		return
	if day >= getdate(nowdate()):
		return
	company = doc.company or frappe.db.get_value("Employee", doc.employee, "company")
	if not rule_set_for(company):
		return
	att = frappe.db.get_value(
		"Attendance",
		{"employee": doc.employee, "attendance_date": day, "docstatus": 1,
		 "status": "Half Day", "leave_application": ["is", "set"]},
		["name", "shift", "half_day_status"], as_dict=True)
	if not att:
		return
	from alvoraa_portal.payroll_rules_apply import _punches

	if _punches(doc.employee, day)[2] >= 2:
		return
	if att.shift:
		doc.shift = att.shift
	if att.half_day_status != "Absent":
		# The engine owns this fact: no punches for the other half. Written as a
		# value, like the engine's verdict fields, after the checks above.
		frappe.db.set_value("Attendance", att.name, "half_day_status", "Absent",
		                    update_modified=False)


def missing_punch(employee, day):
	"""For an approved half-day leave in the past: 'check-in', 'check-out' or
	None. DTC punches carry no log type, so the count decides: one punch means
	the check-in is there and the check-out is missing (memory, dtc-log-type)."""
	from alvoraa_portal.payroll_rules_apply import _punches

	count = _punches(employee, getdate(day))[2]
	if count >= 2:
		return None
	return "check-out" if count == 1 else "check-in"


# ── the Leave page card (SEC-1) ──────────────────────────────────────────────


def _class_and_category(employee, rs):
	fields = [f for f in (rs.leave_class_field, rs.category_field) if f]
	meta = frappe.get_meta("Employee")
	fields = [f for f in fields if meta.has_field(f)]
	row = frappe.db.get_value("Employee", employee, fields, as_dict=True) if fields else {}
	row = row or {}
	cls = str(row.get(rs.leave_class_field) or "").strip() if rs.leave_class_field else ""
	cat = str(row.get(rs.category_field) or "").strip() if rs.category_field else ""
	cls_row = next((c for c in rs.leave_classes if (c.leave_class or "").strip() == cls), None)
	cat_row = next((c for c in rs.categories
	                if (c.category or "").strip().lower() == cat.lower()), None) if cat else None
	return cls, cat, cls_row, cat_row


def credit_facts(employee, rs):
	"""What the rule set gives this person this month, in days."""
	cls, cat, cls_row, cat_row = _class_and_category(employee, rs)
	credited = flt(cls_row.monthly_credits) if cls_row else 0.0
	cat_earns = bool(cat_row.earns_leave_credits) if cat_row else True
	return {"class": cls, "category": cat, "credited": credited,
	        "earns": bool(credited > 0 and cat_earns), "category_earns": cat_earns}


def paid_leave_rows(employee, day):
	"""Paid Leaves requests waiting or approved that touch the month, with their
	days inside it (half 0.5). One query."""
	start, end = _month_bounds(day)
	rows = frappe.get_all("Leave Application",
	                      filters={"employee": employee, "leave_type": PAID_LEAVES,
	                               "status": ["in", ["Open", "Approved"]],
	                               "docstatus": ["<", 2],
	                               "from_date": ["<=", end], "to_date": [">=", start]},
	                      fields=["name", "from_date", "to_date", "half_day", "half_day_date",
	                              "status", "leave_approver"],
	                      order_by="from_date asc")
	for r in rows:
		r["days"] = _days_inside(employee, PAID_LEAVES, r.from_date, r.to_date,
		                         r.half_day, r.half_day_date, start, end)
	return rows


def paid_leaves_left(employee, rs, day=None):
	day = day or nowdate()
	facts = credit_facts(employee, rs)
	taken = sum(r["days"] for r in paid_leave_rows(employee, day))
	return max(0.0, facts["credited"] - taken)


def paid_leaves_card(emp):
	"""The card's block for the caller's OWN record, days only. None where the
	company has no enabled rule set. Never raises: a failure gives {"error": 1}
	and the Error Log row names the employee id only (PRIV-5)."""
	rs = rule_set_for(emp.company)
	if not rs:
		return None
	try:
		return _card(emp, rs)
	except Exception:
		frappe.log_error(title="Paid Leaves card could not be built for {0}".format(emp.name),
		                 message=frappe.get_traceback())
		return {"error": 1}


def _card(emp, rs):
	from alvoraa_portal.payroll_rules_apply import prepare
	from alvoraa_portal.payroll_slip import month_summary

	today = getdate(nowdate())
	start, end = _month_bounds(today)
	facts = credit_facts(emp.name, rs)
	out = {
		"month": _(today.strftime("%B")),
		"class": facts["class"] or None,
		"category": None if facts["category_earns"] else (facts["category"] or None),
		"earns": facts["earns"],
		"lwp_in_play": lwp_in_play(emp.name, today),
		"lwp_limit": LWP_MONTH_LIMIT,
	}
	if not facts["earns"]:
		return out

	rows = paid_leave_rows(emp.name, today)
	used = [r for r in rows if r.status == "Approved"]
	waiting = [r for r in rows if r.status == "Open"]
	used_days = sum(r["days"] for r in used)
	waiting_days = sum(r["days"] for r in waiting)
	out.update({
		"credited": facts["credited"],
		"used": used_days,
		"used_dates": [{"date": str(r.from_date), "to": str(r.to_date), "half": bool(r.half_day)}
		               for r in sorted(used, key=lambda r: r.from_date, reverse=True)],
		"waiting": waiting_days,
		"waiting_from": str(waiting[0].from_date) if waiting else None,
		"approver": (frappe.db.get_value("User", waiting[0].leave_approver, "full_name")
		             if waiting and waiting[0].leave_approver else None),
		"to_be_paid_out": max(0.0, facts["credited"] - used_days - waiting_days),
	})

	gate = cint(rs.leave_threshold_days)
	summary = month_summary(emp.name, emp.company, start, end, rule_set=rs,
	                        ctx=prepare(rs, start, end, employee=emp.name))
	attended = flt(summary.days_for_gate) if summary else 0.0
	if attended < gate:
		last = frappe.get_all("Attendance", filters={"employee": emp.name, "docstatus": 1,
		                                             "attendance_date": ["between", [start, today]]},
		                      pluck="attendance_date", order_by="attendance_date desc", limit=1)
		up_to = last[0] if last else None
		out.update({"attended_so_far": attended, "gate": gate,
		            "attended_up_to": str(up_to) if up_to else None})
	return out


def annotate_applications(emp, rows):
	"""The facts the Leave Applications list shows (R-17..R-27), added to the
	rows the caller already reads for `emp` (at most ten). The chain is walked
	once for all of them; the notices are read in one query."""
	today = getdate(nowdate())
	told = told_for([r.name for r in rows if r.status == "Approved" and r.docstatus == 1])
	chain = chain_of(emp.name) if told else []
	names = {}
	for r in rows:
		lwp = is_lwp(r.leave_type)
		if lwp:
			r["approver_label"] = "HR"
		elif r.leave_approver:
			if r.leave_approver not in names:
				names[r.leave_approver] = frappe.db.get_value("User", r.leave_approver, "full_name")
			r["approver_label"] = names[r.leave_approver]
		else:
			r["approver_label"] = None
		r["half_day"] = cint(r.half_day)
		approved = r.status == "Approved" and r.docstatus == 1
		r["can_cancel"] = bool((r.status == "Open" and r.docstatus == 0)
		                       or (approved and getdate(r.from_date) > today))
		if approved:
			users = told.get(r.name, set())
			mine = [m for m in chain if m.user_id in users]
			r["told_count"] = len(users)
			r["told_top_name"] = mine[-1].employee_name if mine else None
		if approved and r.half_day and r.half_day_date and getdate(r.half_day_date) < today:
			att = frappe.db.get_value(
				"Attendance", {"employee": emp.name, "attendance_date": r.half_day_date,
				               "docstatus": 1, "leave_application": r.name},
				["attendance_request"], as_dict=True)
			regularised = bool(att and att.attendance_request and frappe.db.get_value(
				"Attendance Request", att.attendance_request, "docstatus") == 1)
			r["missing_punch"] = None if regularised else missing_punch(emp.name, r.half_day_date)
			if r["missing_punch"]:
				rs = rule_set_for(emp.company)
				r["special_day"] = bool(_special_day(rs, r.half_day_date, r.half_day_date))
		r.pop("leave_approver", None)
		if r.get("half_day_date"):
			r["half_day_date"] = str(r.half_day_date)
	return rows


# ── what the Apply list offers, and what the preview needs to say ────────────


def types_offered(emp, own, balance_types):
	"""The Apply list (D5, SEC-2). `balance_types` are the types the ledger
	already offers. At an enabled-rule-set company: Paid Leaves (if the person
	earns) and Leave Without Pay, plus their other balance types. Where the
	rule set exists but is off: neither of the two. Elsewhere: Leave Without
	Pay beside the balance types, with today's approval."""
	lwp = lwp_type()
	rs = rule_set_for(emp.company)
	others = [t for t in balance_types if t not in (PAID_LEAVES, lwp)]
	if not rs:
		if rule_set_switched_off(emp.company):
			return [{"leave_type": t} for t in others]
		return [{"leave_type": t} for t in others] + ([{"leave_type": lwp, "lwp": 1}] if lwp else [])
	facts = credit_facts(emp.name, rs)
	out = []
	if facts["earns"]:
		row = {"leave_type": PAID_LEAVES, "paid_leaves": 1}
		if own:
			# X-2: HR acting for someone gets no Paid Leaves figure (SEC-1c).
			row["left"] = paid_leaves_left(emp.name, rs)
		out.append(row)
	if lwp:
		out.append({"leave_type": lwp, "lwp": 1, "lwp_in_play": lwp_in_play(emp.name, nowdate()),
		            "lwp_limit": LWP_MONTH_LIMIT})
	return out + [{"leave_type": t} for t in others]


def refuse_type_not_offered(emp, leave_type, endpoint):
	"""SEC-2: the server refuses what the list would not have offered."""
	from hrms.alvoraa_hr_core.access import refuse

	message = _("This leave type is not available. Ask HR.")
	if rule_set_switched_off(emp.company) and (leave_type == PAID_LEAVES or is_lwp(leave_type)):
		refuse(message, "063-SEC-2", endpoint, "Employee", emp.name)
	if leave_type == PAID_LEAVES:
		rs = rule_set_for(emp.company)
		if not rs or not credit_facts(emp.name, rs)["earns"]:
			refuse(message, "063-SEC-2", endpoint, "Employee", emp.name)


def paid_leaves_approver(emp):
	"""SEC-12: the named approver for a Paid Leaves request, or a refusal that
	says what to do. A disabled approver counts as none."""
	from hrms.hr.doctype.leave_application.leave_application import get_employee_leave_approver

	approver = get_employee_leave_approver(emp.name)
	if not approver or not frappe.db.get_value("User", approver, "enabled"):
		frappe.throw(_("Your request could not be sent because nobody is set to approve your "
		               "Paid Leaves. Ask HR to name someone, or ask for Leave Without Pay, which "
		               "HR approves."), title=_("Leave not sent"))
	return approver


def hr_name(employee):
	"""One HR person in scope, named in the sentences that say who to speak to
	("speak to Ritika (HR)")."""
	users = hr_users_in_scope(employee)
	if not users:
		return None
	return frappe.db.get_value("User", users[0], "first_name") or users[0]


def preview_facts(emp, leave_type, from_date, to_date, half_day, half_day_date, days, own):
	"""What the Apply pop-up needs to say before anything is sent, at an
	enabled-rule-set company. Reads only; the server checks the same rules on
	validate, so a stale preview can never let a request through."""
	rs = rule_set_for(emp.company)
	if not rs:
		return {}
	today = getdate(nowdate())
	first = get_first_day(today)
	lwp = is_lwp(leave_type)
	chain = chain_of(emp.name)
	hr = hr_name(emp.name)
	out = {
		"dtc": 1,
		"month": _(today.strftime("%B")),
		"prev_month": _(add_days(first, -1).strftime("%B")),
		"month_end": day_label(get_last_day(today)),
		"hr_name": hr,
		"chain_top": chain[-1].employee_name if chain else None,
		"chain_n": len(chain),
		"lwp_limit": LWP_MONTH_LIMIT,
		"past_day": getdate(from_date) < today,
	}
	if lwp:
		out["approver_label"] = "HR"
	else:
		from hrms.hr.doctype.leave_application.leave_application import get_employee_leave_approver

		a = get_employee_leave_approver(emp.name)
		out["approver_label"] = frappe.db.get_value("User", a, "full_name") if a else None
		if not a or not frappe.db.get_value("User", a, "enabled"):
			out.update(verdict="block", reason_code="no_approver")
			return out

	if getdate(from_date) < first:
		out.update(verdict="block", reason_code="earlier_month")
		return out

	# A day already worked, or already on leave: Frappe refuses both on save.
	worked = frappe.get_all("Attendance", filters={
		"employee": emp.name, "docstatus": 1,
		"attendance_date": ["between", [from_date, to_date]],
		"status": ["in", ["Present", "Work From Home", "Half Day"]],
		"leave_application": ["is", "not set"]}, pluck="attendance_date", limit=1)
	if worked:
		out.update(verdict="block", reason_code="worked_day", date=day_label(worked[0]))
		return out
	clash = frappe.get_all("Leave Application", filters={
		"employee": emp.name, "status": ["in", ["Open", "Approved"]], "docstatus": ["<", 2],
		"from_date": ["<=", to_date], "to_date": [">=", from_date]}, fields=["from_date"], limit=1)
	if clash:
		out.update(verdict="block", reason_code="overlap",
		           date=day_label(max(getdate(clash[0].from_date), getdate(from_date))))
		return out

	special = _special_day(rs, from_date, to_date)
	if special:
		out["special_day"] = special

	if lwp:
		rows = lwp_rows_in_month(emp.name, from_date)
		used = sum(r["days"] for r in rows)
		out.update(lwp_in_play=used, lwp_left=max(0.0, LWP_MONTH_LIMIT - used),
		           lwp_waiting=[{"from": str(r.from_date), "to": str(r.to_date), "days": r["days"],
		                         "label": range_label(r.from_date, r.to_date)}
		                        for r in rows if r.status == "Open"])
		if flt(days) > out["lwp_left"]:
			out.update(verdict="block", reason_code="lwp_over")
			return out
	elif own and leave_type == PAID_LEAVES:
		facts = credit_facts(emp.name, rs)
		left = paid_leaves_left(emp.name, rs, from_date)
		out.update(credited=facts["credited"], pl_left=left,
		           lwp_in_play=lwp_in_play(emp.name, from_date))
		if flt(days) > left:
			out.update(verdict="block", reason_code="pl_short")
			return out
	out["verdict"] = "ok"
	return out


def _special_day(rs, from_date, to_date):
	"""The first special day in the dates, with its name: the Holiday's
	description in the rule set's special-day list, tags stripped."""
	if not rs.special_day_holiday_list:
		return None
	row = frappe.get_all("Holiday", filters={"parent": rs.special_day_holiday_list,
	                                         "holiday_date": ["between", [from_date, to_date]]},
	                     fields=["holiday_date", "description"], order_by="holiday_date asc", limit=1)
	if not row:
		return None
	name = frappe.utils.strip_html(row[0].description or "").strip()
	return {"date": str(row[0].holiday_date), "label": day_label(row[0].holiday_date),
	        "name": name or None}
