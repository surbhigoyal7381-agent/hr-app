"""Who may see a punch and its photo, and a record of who looked at a face.

Moved out of `field_checkin.py` unchanged. `hooks.py` still names
`alvoraa_portal.field_checkin.checkin_query_conditions`,
`...checkin_has_permission` and `...log_photo_view`; those names are imported
back into `field_checkin`, so every hook path still resolves.

The spec found NO row filter on Employee Checkin anywhere in Frappe HR or in
this app. The `Employee` role holds plain read on it, so the only thing
standing between a curious colleague and everybody's faces and coordinates was
whether ERPNext happened to create a User Permission row for each user. That
is a setting, not a control: one missing row and the whole tenant is readable.

Two hooks, because they answer different questions. The query condition filters
LISTS and reports; has_permission guards opening ONE record by name. A list
filter alone leaves /app/employee-checkin/EMP-CKIN-00042 wide open.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_to_date, cint, get_datetime, getdate, now, now_datetime, today

_HR_ROLES = {"HR Manager", "HR User", "System Manager", "Administrator"}

ACCESS_LOG = "Alvoraa Photo Access Log"

# The role a biometric machine account holds (ALV-302). It files punches. It is
# not HR and has no employee record, so it reads none of them.
SYNC_ROLE = "Biometric Sync"

# Roles Frappe gives everybody, which say nothing about who a user is.
_AUTOMATIC_ROLES = {"All", "Guest", "Desk User"}

# How far a machine punch may be from today before attendance ignores it. A backlog
# can be weeks old; a date outside this is a broken clock, or a misused key.
MACHINE_PUNCH_DAYS_BACK = 90
MACHINE_PUNCH_DAYS_AHEAD = 1
PUNCH_OUT_OF_RANGE = "Machine punch outside the date window"

# The one field on Shift Type the role may change, and how far ahead of the server
# clock it may go: the bridge sits on the customer's computer and its clock drifts.
MARKER = "last_sync_of_checkin"
MARKER_FUTURE_TOLERANCE_MINUTES = 15


def is_machine_account(user: str | None = None) -> bool:
	"""True for exactly this role and no Employee record.

	Holding the role is not enough: a person given it by mistake must not be able
	to file for colleagues or choose the time of their own punch.
	"""
	user = user or frappe.session.user
	if set(frappe.get_roles(user)) - _AUTOMATIC_ROLES != {SYNC_ROLE}:
		return False
	return not frappe.db.exists("Employee", {"user_id": user})


def check_machine_punch(doc: Document, method: str | None = None) -> None:
	"""before_insert Employee Checkin. A machine punch keeps the time the machine
	recorded, and a far-off date is flagged so attendance does not use it (ALV-302).

	`time` is permlevel 1 on Employee Checkin. For a role with no write at that
	level Frappe replaces the value with the field's default, "Now", without
	an error - so a punch sent late, after a dropped line or a retry, would be
	filed at the moment it arrived. Frappe calls before_insert just before that
	reset. Only for a machine account: a person's own punch still gets "Now".

	Flagged and not refused, because the sync tool stops a machine's whole batch on
	a refusal it does not recognise and tries the same punch again on every run, so
	one bad date would hold back every later punch from that machine. Frappe's
	attendance job skips a flagged punch. Our own month view and pay rules read
	punches without looking at the flag, as they do for every flagged punch.

	One Error Log row a day per machine, however many punches: a machine whose clock
	was reset can send thousands, and one row for the whole site would hide a second
	bad machine. The row gives the machine and the date. Frappe also copies the
	request into its metadata, badge number included, so that is cleared. A fault
	here must never fail the punch, or that machine's batch stops.
	"""
	if not is_machine_account():
		return
	doc.flags.ignore_permlevel_for_fields = ["time"]
	date = getdate(doc.time)
	if add_days(today(), -MACHINE_PUNCH_DAYS_BACK) <= str(date) <= add_days(today(), MACHINE_PUNCH_DAYS_AHEAD):
		return
	doc.skip_auto_attendance = 1
	title = f"{PUNCH_OUT_OF_RANGE}: {doc.device_id}"[:140]
	try:
		if not frappe.db.exists("Error Log", {"method": title, "creation": (">=", today())}):
			row = frappe.log_error(
				title=title,
				message=f"Machine {doc.device_id} sent a punch dated {date}. It was filed but attendance "
				        "will not use it, and its later ones today are not logged here. Check that "
				        "machine's clock.",
			)
			row.db_set("metadata", None, update_modified=False)
	except Exception:
		frappe.logger("alvoraa_portal").warning(f"{title}: could not write the Error Log row")


def _only_moves_the_marker(user: str | None = None) -> bool:
	"""True when this user's write on Shift Type can only have come from the role.

	Wider than is_machine_account on purpose: a person holding Employee plus this
	role is not a machine, but the role's write must not let them edit a shift.
	"""
	roles = set(frappe.get_roles(user or frappe.session.user))
	return SYNC_ROLE in roles and not (roles & _HR_ROLES)


def shift_type_has_permission(doc: Document, user: str | None = None, ptype: str | None = None) -> bool:
	"""has_permission Shift Type. The role reads and writes, and guard_shift_type_change
	limits the write. A tenant's permission row is data; this arrives with the release."""
	return not _only_moves_the_marker(user) or ptype in ("read", "write")


def _changed_fieldnames(doc: Document, before: Document) -> set:
	"""Every fieldname whose raw value differs. Not Frappe's get_diff: it compares
	formatted values, so a threshold moved within rounding would count as unchanged."""
	from frappe.model import no_value_fields, table_fields

	def norm(value):
		return "" if value is None else str(value)

	def rows(source, fieldname):
		skip = {"modified", "modified_by", "creation", "owner", "idx", "docstatus"}
		return [sorted((k, norm(v)) for k, v in row.as_dict(no_default_fields=False).items()
		               if k not in skip and not k.startswith("_"))
		        for row in (source.get(fieldname) or [])]

	changed = set()
	for df in doc.meta.fields:
		if df.fieldtype in table_fields:
			if rows(doc, df.fieldname) != rows(before, df.fieldname):
				changed.add(df.fieldname)
		elif df.fieldtype not in no_value_fields and norm(doc.get(df.fieldname)) != norm(before.get(df.fieldname)):
			changed.add(df.fieldname)
	return changed


def guard_shift_type_change(doc: Document, method: str | None = None) -> None:
	"""before_validate Shift Type. The role may move the marker forward and nothing else.

	Attendance is worked out only for shifts that ended before the marker, and the
	same doctype holds the hours and thresholds that decide pay. Moving it back makes
	decided days get worked out again; emptying it stops attendance; a future value
	claims punches that have not happened. Another field in the same save refuses the
	whole save. `before_validate` because the document is still as it arrived and it
	runs even with ignore_validate set.
	"""
	if not _only_moves_the_marker():
		return

	before = doc.get_doc_before_save()
	if before is None:
		frappe.throw(_("This account may only record that attendance has been synced. "
		               "It cannot create a shift."), frappe.PermissionError)

	changed = _changed_fieldnames(doc, before)
	if not changed:
		return
	if changed != {MARKER}:
		frappe.throw(_("This account may only update when attendance was last synced. It cannot "
		               "change a shift's other settings. Ask HR to make this change."),
		             frappe.PermissionError)

	new_value = doc.get(MARKER)
	if not new_value:
		frappe.throw(_("The last sync time cannot be emptied. Attendance would stop being marked."),
		             frappe.PermissionError)
	new_time = get_datetime(new_value)
	if before.get(MARKER) and new_time <= get_datetime(before.get(MARKER)):
		frappe.throw(_("The last sync time can only move forwards. Attendance already marked "
		               "would be worked out again."), frappe.PermissionError)
	if new_time > add_to_date(now_datetime(), minutes=MARKER_FUTURE_TOLERANCE_MINUTES):
		frappe.throw(_("The last sync time cannot be in the future. Check the clock on the "
		               "computer that sends attendance."), frappe.PermissionError)


def _viewer(user=None):
	"""(is_hr, employee_id) for the user asking."""
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	is_hr = bool(_HR_ROLES & roles)
	emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	return is_hr, emp


# ALV-328: an organisation may let managers see punches - and the break worked out
# from them - for their whole reporting line, not only their direct reports. Off
# unless a System Manager ticks it (field_app_settings guards the change).
WHOLE_LINE_SETTING = "alvoraa_manager_sees_whole_line_punches"

# The rights anybody outside HR may have on a punch that is not a new one of their
# own (ALV-332, ALV-333): look, and pick it in a link field. A punch decides pay,
# so changing, deleting or sharing one is HR's.
_READ_RIGHTS = ("read", "select")


def whole_line_on() -> bool:
	"""The organisation switch, read fresh. Off when missing or unreadable (PRIV-4)."""
	try:
		return bool(cint(frappe.db.get_single_value("HR Settings", WHOLE_LINE_SETTING, cache=False)))
	except Exception:
		return False


def _line_sql(manager_sql: str) -> str:
	"""The people besides themselves whose punches this manager may read, as SQL.

	ONE TEXT FOR BOTH HOOKS, so the list and the single record cannot disagree
	(SEC-6). Active at every level, as `attendance_analytics._reports_to` is: a
	report under a manager who has left is not reached. With the switch off,
	direct reports only. The scope stays in the database rather than a list of
	ids read into Python (nfr-budget §2); `union` ends a loop in `reports_to`.
	"""
	if not whole_line_on():
		return ("select name from `tabEmployee` "
		        f"where reports_to = {manager_sql} and status = 'Active'")
	return ("with recursive line (name) as ("
	        f"select name from `tabEmployee` where reports_to = {manager_sql} and status = 'Active' "
	        "union select e.name from `tabEmployee` e join line on e.reports_to = line.name "
	        "where e.status = 'Active') select name from line")


def checkin_query_conditions(user=None):
	"""Row filter for the Employee Checkin list.

	HR sees everything. A manager sees their own and their direct reports' - or
	their whole line, where the organisation allows it (ALV-328). An employee
	sees their own. Anybody with no employee record sees nothing, which is
	deliberately stricter than "sees everything" - the failure mode of a
	permission rule should be silence, not disclosure.
	"""
	is_hr, emp = _viewer(user)
	if is_hr:
		return ""
	if not emp:
		return "1=0"
	me = frappe.db.escape(emp)
	return (f"(`tabEmployee Checkin`.employee = {me} "
	        f"or `tabEmployee Checkin`.employee in ({_line_sql(me)}))")


def checkin_has_permission(doc: Document, user: str | None = None, ptype: str | None = None) -> bool:
	"""Guards ONE record, opened by name or through the API.

	Outside HR a punch is read-only (ALV-332, ALV-333): a person may file a new
	punch of their own and read the punches the list above shows them, and that
	is all. Frappe's role rows still give the Employee role write and delete;
	this hook can only take rights away, which is what it does.

	The third parameter must be called `ptype`. Frappe calls this with `ptype=`
	(`frappe/permissions.py`, has_controller_permissions) and `frappe.call` drops
	any keyword the function does not declare, so under another name it is always
	None and a create looks the same as a read.
	"""
	is_hr, emp = _viewer(user)
	if is_hr:
		return True
	# ALV-302. The machine account files a new punch for anybody, and that is all.
	if ptype == "create" and doc.is_new() and is_machine_account(user):
		return True
	if not emp:
		return False
	if doc.employee == emp:
		return ptype in _READ_RIGHTS or (ptype == "create" and doc.is_new())
	if ptype not in _READ_RIGHTS or not doc.employee:
		return False
	return bool(frappe.db.sql(
		f"select 1 from `tabEmployee` where name = %(employee)s and name in ({_line_sql('%(me)s')})",
		{"employee": doc.employee, "me": emp}))


# ── who may see a phone record (slice 013 step 2, C-11c) ─────────────────────
#
# `Alvoraa Field Device` links Employee and nothing else - no Company. Frappe's
# User Permissions only follow link fields that are ON the doctype, so an HR
# user restricted to one company could list every company's phones: employee
# name, device model, last punch, check-in count. The step-1 probe found it;
# it had been open since slice 008. These two hooks close it the way the punch
# is closed above: the query condition filters lists and reports, has_permission
# guards opening one record by name.
#
# The scope is the shared one every HR endpoint already uses,
# `hrms.alvoraa_hr_core.access.permitted_companies`: a System Manager sees every
# company; an HR Manager or HR User sees the companies in their Company User
# Permissions, or failing that their own employee record's company, or failing
# that nothing. Nobody else has a role on this doctype, and if one ever appears
# the fallback here is "nothing", not "everything".

DEVICE = "Alvoraa Field Device"
INVITE = "Alvoraa App Invite"
ACKNOWLEDGEMENT = "Alvoraa Notice Acknowledgement"


def _device_companies(user):
	"""The companies whose phones this user may see, or None for every company."""
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or "System Manager" in roles:
		return None
	if not (_HR_ROLES & roles):
		return []
	from hrms.alvoraa_hr_core.access import permitted_companies
	return permitted_companies(user)


def _scoped_by_employee_company(doctype, user):
	"""Row filter for a doctype that links Employee and nothing else."""
	companies = _device_companies(user)
	if companies is None:
		return ""
	if not companies:
		return "1=0"
	allowed = ", ".join(frappe.db.escape(c) for c in companies)
	return (f"`tab{doctype}`.employee in (select name from `tabEmployee` "
	        f"where company in ({allowed}))")


def _one_row_by_employee_company(doc, user):
	"""Guards ONE record of such a doctype, opened by name or through the API."""
	companies = _device_companies(user)
	if companies is None:
		return True
	if not companies or not doc.get("employee"):
		return False
	company = frappe.db.get_value("Employee", doc.employee, "company")
	return bool(company) and company in companies


def device_query_conditions(user=None):
	"""Row filter for the phone list and every report on it."""
	return _scoped_by_employee_company(DEVICE, user)


def device_has_permission(doc, user=None, permission_type=None):
	"""Guards ONE phone record, opened by name or through the API."""
	return _one_row_by_employee_company(doc, user)


# The code record and the acknowledgement record (slice 013 step 3) link only
# Employee too, so they get the same pair, for the same reason.

def invite_query_conditions(user=None):
	return _scoped_by_employee_company(INVITE, user)


def invite_has_permission(doc, user=None, permission_type=None):
	return _one_row_by_employee_company(doc, user)


def acknowledgement_query_conditions(user=None):
	return _scoped_by_employee_company(ACKNOWLEDGEMENT, user)


def acknowledgement_has_permission(doc, user=None, permission_type=None):
	return _one_row_by_employee_company(doc, user)


def log_photo_view(doc, method=None):
	"""Record that somebody opened a check-in carrying a photo.

	A face is the most sensitive thing this feature stores, and "who has looked
	at my photo" is a question an employee is entitled to ask. Without this the
	only honest answer is "we do not know".

	Deliberately narrow, because an access log that records everything is one
	nobody reads:
	  * only check-ins that actually HAVE a photo
	  * never the employee looking at their own
	  * one row per viewer per record per day, not one per page refresh
	"""
	if not doc.get("alvoraa_checkin_photo"):
		return
	if not frappe.db.exists("DocType", ACCESS_LOG):
		return

	user = frappe.session.user
	if user in ("Guest", "Administrator"):
		return

	is_hr, emp = _viewer(user)
	if emp and doc.employee == emp:
		return

	try:
		if frappe.db.exists(ACCESS_LOG, {
			"checkin": doc.name, "viewed_by": user, "viewed_on_date": today()}):
			return
		frappe.get_doc({
			"doctype": ACCESS_LOG,
			"checkin": doc.name,
			"employee": doc.employee,
			"employee_name": doc.employee_name,
			"viewed_by": user,
			"viewed_at": now(),
			"viewed_on_date": today(),
		}).insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		# Never let the log stop somebody doing their job.
		frappe.log_error(f"Could not record photo access on {doc.name}",
		                 "Field check-in access log")
