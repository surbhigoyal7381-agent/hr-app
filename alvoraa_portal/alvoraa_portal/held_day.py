"""Held days (slice 085, ALV-392).

A day with an odd number of punches (one in and never out) is neither paid nor
refused until a human has looked. At a company that has switched it on, such a
day is written as an Attendance row with status **Held**. It is unpaid on the
slip. It ends in one of two ways: the machine delivers the missing punch late
(`release_on_machine_punch`), or HR approves a request that carries the missing
time (slice 087: `punch_fix.apply` adds that punch for real). Everything here is a `doc_events` hook, a Custom Field
or a Property Setter: no file in the vendored Frappe HR tree is edited.

The order of the file is the life of a Held day: install, hold, release, slip.
"""

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, getdate, now_datetime

HELD = "Held"
ATTENDANCE = "Attendance"
REQUEST = "Attendance Request"
COMPANY = "Company"

SWITCH = "alvoraa_hold_odd_punch_days"
LIMIT = "alvoraa_monthly_request_limit"
EXEMPT = "alvoraa_limit_exempt_roles"
COMPANY_SETTINGS = (SWITCH, LIMIT, EXEMPT)

# The order matters: Held sits last so the existing options keep their places.
FIELDS = {
	COMPANY: [
		{"fieldname": "alvoraa_held_section", "fieldtype": "Section Break",
		 "label": "Held Days", "insert_after": "default_holiday_list", "collapsible": 1},
		{"fieldname": SWITCH, "fieldtype": "Check", "default": "0",
		 "label": "Hold Days With A Missing Punch", "insert_after": "alvoraa_held_section",
		 "description": "A day with an odd number of punches is held, not paid, until "
		                "HR looks at it. Days already held stay held if this is switched off."},
		{"fieldname": LIMIT, "fieldtype": "Int", "default": "0",
		 "label": "Monthly Request Limit", "insert_after": SWITCH,
		 "description": "How many attendance requests one employee may raise in a "
		                "month. 0 means no limit. Held days do not count."},
		{"fieldname": EXEMPT, "fieldtype": "Small Text",
		 "label": "Exempt From The Limit", "insert_after": LIMIT,
		 "description": "Role or designation names, separated by commas."},
	],
	ATTENDANCE: [
		{"fieldname": "alvoraa_release_how", "fieldtype": "Select", "read_only": 1,
		 "allow_on_submit": 1, "options": "\nHR decision\nMachine punch",
		 "label": "Released By", "insert_after": "alvoraa_evaluated_on"},
		{"fieldname": "alvoraa_release_by", "fieldtype": "Data", "read_only": 1,
		 "allow_on_submit": 1, "label": "Released By (User Or Punch)",
		 "insert_after": "alvoraa_release_how"},
		{"fieldname": "alvoraa_release_on", "fieldtype": "Datetime", "read_only": 1,
		 "allow_on_submit": 1, "label": "Released On", "insert_after": "alvoraa_release_by"},
	],
	REQUEST: [
		{"fieldname": "alvoraa_missing_time", "fieldtype": "Time",
		 "label": "Missing Punch Time", "insert_after": "explanation"},
		{"fieldname": "alvoraa_missing_log", "fieldtype": "Select", "options": "\nIN\nOUT",
		 "label": "Missing Punch Was", "insert_after": "alvoraa_missing_time"},
	],
}


# ── install ──────────────────────────────────────────────────────────────────

def after_migrate():
	"""The Held option, and the fields. Wired to after_migrate AND after_install:
	a site built with `bench install-app` never runs a migrate (OPS-6, OPS-10)."""
	if not (frappe.db.exists("DocType", ATTENDANCE) and frappe.db.exists("DocType", REQUEST)
	        and frappe.db.exists("DocType", COMPANY)):
		return False

	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	# A Property Setter, not an edit to attendance.json: the fork is vendored and
	# a JSON edit would clash on every rebase. Widens; never replaces.
	field = frappe.get_meta(ATTENDANCE).get_field("status")
	shipped = (field.options or "").split("\n") if field else []
	if HELD not in shipped:
		make_property_setter(ATTENDANCE, "status", "options", "\n".join(shipped + [HELD]),
		                     "Text", validate_fields_for_doctype=False)
		frappe.clear_cache(doctype=ATTENDANCE)

	create_custom_fields(FIELDS)
	return True


def _switch_on(company):
	"""The company's switch. Off when the column is missing (a deploy without a
	migrate) or unreadable: never an error on the path that marks attendance."""
	try:
		return bool(cint(frappe.get_cached_value(COMPANY, company, SWITCH)))
	except Exception:
		return False


# ── who may change the settings (SEC-6) ──────────────────────────────────────

def guard_company_settings(doc, method=None):
	"""Company validate. Only an HR Manager looking after THIS company, a System
	Manager or Administrator changes the three settings, on every door (Desk,
	REST, import). A hook and not a permlevel: it reads company scope, and it
	needs no Custom DocPerm row on any tenant."""
	before = doc.get_doc_before_save()
	changed = [f for f in COMPANY_SETTINGS if _norm(doc.get(f)) != _norm(before.get(f) if before else None)]
	if changed and not _may_change_settings(doc.name):
		from hrms.alvoraa_hr_core.access import refuse
		refuse(_("Only an HR Manager of this company or a System Manager can change the "
		         "held-day settings."), "SEC-6", "Company save", COMPANY, doc.name)
	if cint(doc.get(LIMIT)) < 0:
		frappe.throw(_("The monthly request limit cannot be below 0. Use 0 for no limit."))
	roles = exempt_roles(doc)
	missing = [r for r in roles if not (frappe.db.exists("Role", r) or frappe.db.exists("Designation", r))]
	if missing:
		frappe.throw(_("These are not roles or designations on this site: {0}. Check the spelling in "
		               "\"Exempt From The Limit\".").format(", ".join(missing)))


def _norm(value):
	"""0, None and empty are one value: a field nobody has touched."""
	return str(value or "").strip() if str(value or "").strip() not in ("0",) else ""


def exempt_roles(company_doc_or_value):
	value = company_doc_or_value.get(EXEMPT) if hasattr(company_doc_or_value, "get") \
		else company_doc_or_value
	return [r.strip() for r in (value or "").split(",") if r.strip()]


def _may_change_settings(company):
	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or "System Manager" in roles:
		return True
	if "HR Manager" not in roles:
		return False
	from hrms.alvoraa_hr_core.access import permitted_companies
	return company in permitted_companies(user)


@frappe.whitelist()
def held_settings():
	"""The settings card's rows: only the companies this caller looks after, and
	whether they may change each (the Company validate hook is the real rule)."""
	from hrms.alvoraa_hr_core.access import permitted_companies
	companies = permitted_companies()
	if not companies:
		return []
	rows = frappe.get_all(COMPANY, filters={"name": ("in", companies)},
	                      fields=["name", SWITCH, LIMIT, EXEMPT], order_by="name asc")
	return [{"company": r.name, "hold": cint(r.get(SWITCH)), "limit": cint(r.get(LIMIT)),
	         "roles": r.get(EXEMPT) or "", "can_edit": _may_change_settings(r.name)} for r in rows]


@frappe.whitelist(methods=["POST"])  # ALV-411: a change is never a GET link
def save_settings(company, hold, limit, roles):
	"""The settings card's Save. The Company validate hook above is the rule;
	this only turns the card's three values into one save."""
	from hrms.alvoraa_hr_core.access import permitted_companies, refuse
	if company not in permitted_companies():
		refuse(_("That company is outside the companies you look after."), "SEC-4",
		       "held_day.save_settings", COMPANY, company)
	doc = frappe.get_doc(COMPANY, company)
	doc.set(SWITCH, cint(hold))
	doc.set(LIMIT, cint(limit))
	doc.set(EXEMPT, ", ".join(exempt_roles(roles or "")))
	doc.save()
	return {"hold": cint(doc.get(SWITCH)), "limit": cint(doc.get(LIMIT)),
	        "roles": doc.get(EXEMPT) or ""}


def _has_time(doc):
	"""A missing time was given. Midnight is a time: a zero timedelta is falsy."""
	return doc.get("alvoraa_missing_time") not in (None, "")


# ── the monthly limit (US-10) ────────────────────────────────────────────────

def _filed_by_hr(filer, employee_user):
	"""A request HR files for somebody. Told apart by who filed it: not the
	employee's own login, and a login holding HR Manager, HR User or System
	Manager (or Administrator). A manager's request on behalf holds none of those,
	so it counts, like the employee's own. An HR person who is also that
	employee's manager counts as HR here: the roles cannot tell the two hats apart."""
	if filer == employee_user:
		return False
	return filer == "Administrator" or bool(
		{"HR Manager", "HR User", "System Manager"} & set(frappe.get_roles(filer)))


def enforce_monthly_limit(doc, method=None):
	"""Attendance Request validate, on every door and on every edit of a draft, so
	a held-day draft edited into an ordinary request is counted (F4). Counts as
	Grace's script did (AC-44): requests whose from_date is in the same month, not
	cancelled, not Declined (Grace: not Rejected), never this request itself.
	A request raised for a Held day neither counts nor is refused here. That is
	`alvoraa_for_held_day`, set by the server when the request is created (slice
	087): a punch fix on an ordinary day carries a time too, and must count. A
	request HR files is never refused and never counted: only the employee's own
	and a manager's on behalf are (the filer is the request's owner)."""
	# A replacement the employee files after saying "Not right" to a request filed for them was not their
	# choice, so it neither counts nor is refused (slice 087, V4).
	if doc.get("alvoraa_for_held_day") or doc.get("alvoraa_replaces") or doc.docstatus:
		return
	company = frappe.db.get_value("Employee", doc.employee, "company")
	try:
		limit = cint(frappe.get_cached_value(COMPANY, company, LIMIT))
	except Exception:
		return
	if limit <= 0:
		return
	# Exempt by designation (Grace's script exempted "Sales Executive" this way)
	# or by a role the employee's login holds.
	user, designation = frappe.db.get_value("Employee", doc.employee, ["user_id", "designation"])
	if _filed_by_hr(frappe.session.user, user):
		return
	exempt = set(exempt_roles(frappe.get_cached_value(COMPANY, company, EXEMPT)))
	if designation in exempt or (user and exempt & set(frappe.get_roles(user))):
		return
	first = getdate(doc.from_date).replace(day=1)
	last = first.replace(day=28) + timedelta(days=4)
	last = last - timedelta(days=last.day)
	filters = {
		"employee": doc.employee, "docstatus": ("!=", 2),
		"from_date": ("between", [first, last]),
		"alvoraa_for_held_day": 0, "alvoraa_replaces": ("is", "not set"),
		"alvoraa_review_status": ("not in", ["Declined"]),
	}
	if not doc.is_new():
		filters["name"] = ("!=", doc.name)
	rows = frappe.get_all(REQUEST, filters=filters, pluck="owner")
	used = sum(1 for o in rows if not _filed_by_hr(o, user))
	if used >= limit:
		frappe.throw(_("You have used your {0} requests this month. Held days do not count. "
		               "For another day, ask HR to file it for you: a request HR files "
		               "does not count against your limit.").format(limit))


def validate_missing_time(doc, method=None):
	"""Attendance Request validate. Since slice 087 a time may be sent for any fixable
	day (`punch_fix.validate` judges the day and works out In or Out); this keeps only
	the In/Out rule for a site whose migrate has not run yet."""
	if _has_time(doc) and not doc.get("alvoraa_missing_log"):
		frappe.throw(_("Say whether the missing punch was in or out."))


# ── the hold (US-3) ──────────────────────────────────────────────────────────

def hold_odd_punch_day(doc, method=None):
	"""Attendance validate, before the first save, so the row is written once as
	Held and never created then rewritten (AC-11). Only auto-attendance sets a
	punch time, so a hand-marked row and a request-made row are never touched.
	Either time counts: a lone OUT punch on a log-type shift has an `out_time`
	and no `in_time`, and was marked Absent until ALV-404."""
	if not doc.is_new() or doc.status not in ("Present", "Absent", "Half Day"):
		return
	if not (doc.in_time or doc.out_time) or doc.get("attendance_request") or doc.get("leave_application"):
		return
	if not _switch_on(doc.company):
		return
	from alvoraa_portal.payroll_rules_apply import _punches
	if _punches(doc.employee, doc.attendance_date)[2] % 2 == 1:
		doc.status = HELD
		doc.half_day_status = None


# ── releasing ────────────────────────────────────────────────────────────────

def _held_row(employee, date):
	return frappe.db.get_value(
		ATTENDANCE, {"employee": employee, "attendance_date": getdate(date),
		             "docstatus": 1, "status": HELD},
		["name", "shift", "company"], as_dict=True)


def _day_logs(employee, date, shift, aside=()):
	"""The punches a day is judged from. `aside` are punch names to leave out (slice 087:
	a punch a pending fix would set aside; once approved it is out through its own
	`skip_auto_attendance`).

	ALV-402's rule, the same as `payroll_rules_apply._punches`: a punch belongs to the day its
	shift started (`shift_start`), not to its calendar date, and a punch with no shift keeps its
	calendar date. So this reads the day and the next and keeps what is this day's: leaving at
	00:00 after a 20:30 shift end is the last punch of the day before, here as in the engine."""
	date = getdate(date)
	filters = {"employee": employee, "skip_auto_attendance": 0, "offshift": 0,
	           "time": ("between", [f"{date} 00:00:00", f"{add_days(date, 1)} 23:59:59"])}
	if aside:
		filters["name"] = ("not in", list(aside))
	rows = frappe.get_all("Employee Checkin", filters=filters,
	                      fields=["name", "time", "log_type", "shift_start", "shift_end"],
	                      order_by="time asc")
	return [r for r in rows if getdate(r.shift_start or r.time) == date]


def extra_when(shift, date, when, first_time=None):
	"""When an added punch happened: on the day, or after midnight on a night shift
	whose out time is earlier than the first punch. One rule, for the preview and the insert."""
	if not isinstance(when, datetime):
		when = datetime.combine(getdate(date), when)
	if first_time and shift.get("start_time") and shift.get("end_time") \
			and shift.start_time > shift.end_time and when < get_datetime(first_time):
		when += timedelta(days=1)
	return when


def worked_out(row, extra=None, aside=(), logs=None):
	"""(status, working_hours, late, early, in_time, out_time) for a day, by the Shift
	Type's own `get_attendance`: no threshold rule of ours. `extra` is a punch not yet
	stored, as (time, log_type); `aside` are punch names to leave out."""
	shift = frappe.get_cached_doc("Shift Type", row.shift)
	# `logs` lets a caller that has just read the day's punches pass them in (slice 087's card).
	logs = (_day_logs(row.employee, row.attendance_date, row.shift, aside) if logs is None
	        else [frappe._dict(x) for x in logs])
	if extra:
		when, log_type = extra
		first = logs[0] if logs else frappe._dict()
		when = extra_when(shift, row.attendance_date, when, logs[0].time if logs else None)
		logs.append(frappe._dict(time=when, log_type=log_type,
		                         shift_start=first.get("shift_start"), shift_end=first.get("shift_end")))
		logs.sort(key=lambda x: get_datetime(x["time"]))
	for log in logs:
		log["time"] = get_datetime(log["time"])
		if not log.get("shift_start"):
			log["shift_start"] = datetime.combine(getdate(row.attendance_date), _as_time(shift.start_time))
			log["shift_end"] = log["shift_start"] + timedelta(hours=24)
		log["shift_start"] = get_datetime(log["shift_start"])
		log["shift_end"] = get_datetime(log["shift_end"])
	logs = [frappe._dict(x) for x in logs]
	absent, half = flt(shift.working_hours_threshold_for_absent), flt(shift.working_hours_threshold_for_half_day)
	if shift.is_half_holiday(row.employee, row.attendance_date):
		absent, half = absent / 2, half / 2
	return shift.get_attendance(logs, absent, half)


def _as_time(value):
	return (datetime.min + value).time() if isinstance(value, timedelta) else value


def preview(employee, date, missing_time, missing_log, aside=()):
	"""What the day would become on approval, for the HR card (Q3). The same
	function approval runs, so the card cannot promise something else."""
	row = _held_row(employee, date)
	if not row or not row.shift:
		return None
	row = frappe._dict(row, employee=employee, attendance_date=getdate(date))
	status, hours, *_rest = worked_out(row, (frappe.utils.get_time(missing_time), missing_log), aside)
	return {"status": status, "working_hours": flt(hours, 2),
	        "punches": [get_datetime(x.time).strftime("%H:%M") for x in _day_logs(employee, date, row.shift, aside)],
	        "slip_final": is_in_final_slip(employee, date)}


def is_in_final_slip(employee, date):
	return bool(frappe.db.exists("Salary Slip", {"employee": employee, "docstatus": 1,
	                                             "start_date": ("<=", date), "end_date": (">=", date)}))


def _write_release(att_name, row, outcome, how, by):
	status, hours, late, early, in_time, out_time = outcome
	values = {"status": status, "working_hours": flt(hours, 3), "late_entry": cint(late),
	          "early_exit": cint(early), "in_time": in_time, "out_time": out_time,
	          "half_day_status": "Absent" if status == "Half Day" else None,
	          "modify_half_day_status": 0,
	          "alvoraa_release_how": how, "alvoraa_release_by": by,
	          "alvoraa_release_on": now_datetime()}
	# set_value skips the Version row, which is why the three release fields exist
	# (PRIV-3, SEC-7): they carry the who, how and when. The engine's own
	# `write_verdict` writes the same way.
	frappe.db.set_value(ATTENDANCE, att_name, values)
	return status


def note_held_day(doc, method=None):
	"""Attendance Request before_submit. Refuses what cannot be worked out. A punch fix
	(slice 087) is written by `punch_fix.apply`, which also judges the day; here it
	is only held to what 085 promised: a request raised for a Held day that has been
	released since says so, and is declined."""
	from alvoraa_portal.punch_fix import is_punch_fix

	if is_punch_fix(doc):
		if doc.get("alvoraa_for_held_day") and not _held_row(doc.employee, doc.from_date):
			frappe.throw(_("That day is no longer held, so there is nothing to release. "
			               "Decline this request."))
		return
	row = _held_row(doc.employee, doc.from_date) if str(doc.from_date) == str(doc.to_date) else None
	if not row:
		# A request for several days would make a Held day Present with no hours worked
		# out and no release record (review F3). The one door is a request for that
		# one day, carrying the missing time.
		if frappe.db.exists(ATTENDANCE, {
				"employee": doc.employee, "docstatus": 1, "status": HELD,
				"attendance_date": ("between", [doc.from_date, doc.to_date])}):
			frappe.throw(_("This request covers a held day. A held day is released only by a "
			               "request for that one day with the missing punch time. Decline this "
			               "request and ask for the held day on its own."))
		return
	if not row.shift:
		frappe.throw(_("This day has no shift, so its hours cannot be worked out. Ask a "
		               "System Manager to set the shift on the day, then approve again."))
	frappe.throw(_("This day is held. The request needs the missing punch time so the "
	               "hours can be worked out. Ask the employee to send it, or decline."))


def release_on_machine_punch(doc, method=None):
	"""Employee Checkin after_insert. Cheapest test first, so an ordinary punch
	costs one role check. Judged by who filed it, never by `device_id` (SEC-5).
	A fault never fails the punch: the sync tool halts a machine's batch on a
	refusal it does not know."""
	try:
		from alvoraa_portal.field_app_access import files_as_machine
		if not files_as_machine() or doc.skip_auto_attendance:
			return
		date = get_datetime(doc.time).date()
		row = _held_row(doc.employee, date)
		if not row or not row.shift:
			return
		from alvoraa_portal.payroll_rules_apply import _punches
		count = _punches(doc.employee, date)[2]
		if count < 2 or count % 2:
			return
		frappe.db.savepoint("held_release")
		try:
			full = frappe._dict(row, employee=doc.employee, attendance_date=date)
			_write_release(row.name, full, worked_out(full), "Machine punch", doc.name)
			# Link the punch to the day, so the 3-minute job does not take it for an unmarked one.
			frappe.db.set_value("Employee Checkin", doc.name, "attendance", row.name)
		except Exception:
			frappe.db.rollback(save_point="held_release")
			raise
		frappe.enqueue("alvoraa_portal.held_day.refresh_slip_job", employee=doc.employee,
		               date=str(date), enqueue_after_commit=True, queue="short")
	except Exception:
		frappe.log_error(title=f"Held day not released by punch {doc.name}",
		                 message=frappe.get_traceback())


def refresh_slip_job(employee, date):
	refresh_draft_slip(employee, date)


# ── the slip ─────────────────────────────────────────────────────────────────

def refresh_draft_slip(employee, date):
	"""Re-save that ONE employee's draft slip so the day is priced again.
	Returns "refreshed", "final" (the slip is submitted and was NOT changed),
	or "none". Its own savepoint and try; an error goes to the Error Log by
	slip name and the release stands. `ignore_permissions` is deliberate: the
	caller may be the machine account, which holds no Salary Slip right, and
	the act is owed by the system."""
	slip = None
	try:
		slip = frappe.db.get_value("Salary Slip", {"employee": employee, "docstatus": 0,
		                                           "start_date": ("<=", date), "end_date": (">=", date)})
		if slip:
			frappe.db.savepoint("held_slip")
			try:
				frappe.get_doc("Salary Slip", slip).save(ignore_permissions=True)
			except Exception:
				frappe.db.rollback(save_point="held_slip")
				raise
			return "refreshed"
		if is_in_final_slip(employee, date):
			return "final"
	except Exception:
		frappe.log_error(title=f"Slip {slip or employee} not refreshed after a held day",
		                 message=frappe.get_traceback())
	return "none"


def deduct_held_days(doc, method=None):
	"""Salary Slip validate, wired AFTER the pay-rule engine's hook. Held is not a
	status stock Frappe reads, so it would be paid. Frappe works `payment_days`
	out from scratch on every save, so subtracting here is safe to run twice.
	It also runs on SUBMIT: Frappe validates again after setting docstatus to 1
	and recounts every day as paid, so skipping it there paid the Held days
	(review B-1). Validate does not run on a slip that is already final, so a
	day released after that never changes it (Q4). Does nothing on a cancelled
	slip or at a company with a pay rule set (that path prices from the engine,
	which already treats an odd count as held)."""
	if doc.docstatus == 2 or not doc.employee:
		return
	from alvoraa_portal.payroll_rules_apply import rule_set_for
	if rule_set_for(doc.company):
		return
	days = held_dates(doc.employee, doc.start_date, doc.end_date)
	if not days:
		return
	doc.payment_days = max(0, flt(doc.payment_days) - len(days))
	doc.absent_days = flt(doc.absent_days) + len(days)
	doc.calculate_net_pay()
	doc.compute_year_to_date()
	doc.compute_month_to_date()
	doc.compute_component_wise_year_to_date()


def held_dates(employee, start, end):
	"""The Held days in a period that cost pay (a holiday is not a working day).
	The slip hook and the payslip line read the same list."""
	dates = frappe.get_all(ATTENDANCE, filters={
		"employee": employee, "docstatus": 1, "status": HELD,
		"attendance_date": ("between", [start, end])}, pluck="attendance_date",
		order_by="attendance_date asc")
	if not dates:
		return []
	holidays = _holidays(employee, start, end)
	return [d for d in dates if str(d) not in holidays]


def _holidays(employee, start, end):
	"""The days the slip itself leaves out of the working days: the same two
	calls `SalarySlip.get_holidays_for_employee` makes (the employee's Holiday
	List Assignment, then the employee, then the company), so a Held day on a
	weekly off is not taken off twice (review M-3)."""
	from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
	from hrms.utils.holiday_list import get_holiday_dates_between

	holiday_list = get_holiday_list_for_employee(employee, False)
	if not holiday_list:
		return set()
	return {str(d) for d in get_holiday_dates_between(holiday_list, start, end)}
