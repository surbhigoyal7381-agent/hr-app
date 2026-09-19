"""The organisation's three switches for the field attendance app (slice 013, US-3).

Who may have the app (a list of designations), whether the app is on at all,
and how long a joining code works. They live on **HR Settings** as custom
fields, not in a Single of our own, because `CLAUDE.md` section 4 puts
organisation settings there, and because HR Settings already does the two
things the story needs: HR Manager writes and HR User only reads (its own
permissions), and every save leaves a Version row (its `track_changes`).

Three rules hold the feature together, and each has a test:

  * **Every read fails closed.** If the fields cannot be read - the site has not
    been migrated, the database is unhappy - the app is treated as OFF and the
    designation list as EMPTY. A false "off" costs a support call; a false "on"
    lets a phone punch that nobody allowed (AC-21).
  * **Turning the app off, or removing a designation, needs a reason in the
    same save.** The reason is a fixed list, it is refused on every door (desk,
    REST, `set_value`) by the `validate` hook, and it is emptied again after the
    Version row has recorded it - the pattern `Alvoraa Leader View Settings`
    already uses (AC-17 to AC-19).
  * **A change is live on the next request.** The values are read with
    `get_single_value(cache=False)`, which the step-1 probe showed is fresh on
    the next request with no restart - well inside the 60 seconds AC-22 asks for.
    Nothing here is cached, so there is nothing to invalidate.

The words the phone is shown for the two refusals are in the app's own screens
(`appOff`, `notField`); the server sends the code and, for `NOT_FIELD_ROLE`, the
person's designation, which is the one value that table allows.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, get_fullname

from alvoraa_portal.field_app_errors import refuse, requires_field_app_plan

SETTINGS = "HR Settings"
CHILD = "Alvoraa Field Worker Designation"
DEVICE = "Alvoraa Field Device"

# The custom fields. `alvoraa_field_app_` is this feature's prefix, as the
# parallel-work rules ask, so nobody else's installer can collide with them.
F_TAB = "alvoraa_field_app_tab"
F_SECTION = "alvoraa_field_app_section"
F_DESIGNATIONS = "alvoraa_field_worker_designations"
F_SWITCH_SECTION = "alvoraa_field_app_switch_section"
F_ENABLED = "alvoraa_field_app_enabled"
F_LIFETIME = "alvoraa_app_code_lifetime"
F_REASON = "alvoraa_field_app_change_reason"
F_INFO_SECTION = "alvoraa_field_app_info_section"
F_INFO = "alvoraa_field_app_info"

# The fields whose changes the history on the screen is about. Layout fields
# never appear in a Version row, so they are not here.
TRACKED_FIELDS = (F_DESIGNATIONS, F_ENABLED, F_LIFETIME, F_REASON)

# How long a joining code works. The user's decision: 24 hours by default, at
# most 7 days. Held as a Select rather than a number so a REST save cannot
# choose 90 days (AC-20).
LIFETIME_HOURS = {
	"1 hour": 1,
	"4 hours": 4,
	"12 hours": 12,
	"1 day": 24,
	"3 days": 72,
	"7 days": 168,
}
DEFAULT_LIFETIME = "1 day"
MAX_LIFETIME_HOURS = 168

# Why the app was turned off or a designation removed. A fixed list, not free
# text: it is kept in a change history that HR User and (through the desk)
# every Employee-role user can read, so it must never be able to hold a name.
CHANGE_REASONS = (
	"Pausing the pilot",
	"Field workers use the reception machine again",
	"Other",
)

# For the change history: what each field is called on the screen.
LABELS = {
	F_DESIGNATIONS: "Field worker designations",
	F_ENABLED: "Field workers can use the app",
	F_LIFETIME: "App codes work for",
	F_REASON: "Why?",
}

HISTORY_LIMIT = 20

# How many Version rows to read looking for the last 20 that touched our fields.
# HR Settings holds many other settings, so most rows are somebody else's.
# Bounded, so a tenant that has saved HR Settings ten thousand times still gets
# one small query.
VERSION_SCAN_LIMIT = 200


# ── reading ──────────────────────────────────────────────────────────────────

def settings():
	"""The three values, or the fail-closed answer if they cannot be read.

	`get_single_value` with `cache=False` goes to the database every time. The
	step-1 probe measured this read as live on the next request across worker
	processes; the whole point of AC-22 is that HR can stop the app in a minute.
	"""
	try:
		enabled = cint(frappe.db.get_single_value(SETTINGS, F_ENABLED, cache=False))
		lifetime = frappe.db.get_single_value(SETTINGS, F_LIFETIME, cache=False)
		designations = frappe.get_all(
			CHILD,
			filters={"parent": SETTINGS, "parenttype": SETTINGS, "parentfield": F_DESIGNATIONS},
			pluck="designation",
		)
	except Exception:
		# A site that has not been migrated, a field somebody deleted, a database
		# error. Whatever it is, nobody gets the app until it is fixed. The row
		# names no person, so the log line can say what happened.
		frappe.log_error("field app settings could not be read; the app is treated as off",
		                 "Field app settings")
		return {"enabled": False, "designations": [], "lifetime": DEFAULT_LIFETIME,
		        "lifetime_hours": LIFETIME_HOURS[DEFAULT_LIFETIME], "readable": False}

	if lifetime not in LIFETIME_HOURS:
		lifetime = DEFAULT_LIFETIME

	return {
		"enabled": bool(enabled),
		"designations": [d for d in designations if d],
		"lifetime": lifetime,
		"lifetime_hours": LIFETIME_HOURS[lifetime],
		"readable": True,
	}


def refuse_unless_eligible(designation):
	"""Refuse with `APP_OFF_FOR_FIELD` or `NOT_FIELD_ROLE`, or return quietly.

	The one eligibility check, used by every endpoint that has to ask (E4 and E5
	now; E1, E3 and E7 in step 3). Three copies of "is this person a field
	worker" would drift; this is the only one.

	The app is asked about first, so a switched-off tenant answers the same for
	everybody and does not say who is or is not on the list.
	"""
	current = settings()
	if not current["enabled"]:
		refuse("APP_OFF_FOR_FIELD",
		       _("The app is not switched on for field staff."))
	if not designation or designation not in current["designations"]:
		refuse("NOT_FIELD_ROLE",
		       _("This app is not for your job yet. Keep marking attendance the "
		         "usual way."),
		       designation=designation or "")


# ── the rules, on every door into HR Settings ────────────────────────────────

def _designations_on(doc):
	return {row.designation for row in (doc.get(F_DESIGNATIONS) or []) if row.designation}


def validate_hr_settings(doc, method=None):
	"""doc_events HR Settings validate.

	Runs beside `alvoraa_goals.review_items.validate_hr_settings`, which checks
	its own three fields on the same Single. Each only looks at its own fields
	and each only throws for its own, so HR can always save the page when both
	are happy - a test saves HR Settings with both apps installed.
	"""
	if not doc.meta.has_field(F_ENABLED):
		# Fields not installed yet on this site (the installer has not run).
		return

	lifetime = doc.get(F_LIFETIME)
	if lifetime and lifetime not in LIFETIME_HOURS:
		frappe.throw(_("Choose how long app codes work from the list: 1 hour to 7 days."),
		             frappe.ValidationError)

	reason = doc.get(F_REASON)
	if reason and reason not in CHANGE_REASONS:
		frappe.throw(_("Choose a reason from the list."), frappe.ValidationError)

	before = doc.get_doc_before_save()
	if before is None:
		return

	turning_off = cint(before.get(F_ENABLED)) and not cint(doc.get(F_ENABLED))
	removed = _designations_on(before) - _designations_on(doc)
	if (turning_off or removed) and not reason:
		frappe.throw(_("Choose a reason. It is kept in the change history."),
		             frappe.ValidationError)


def clear_reason_after_save(doc, method=None):
	"""doc_events HR Settings on_change.

	`on_change` runs after Frappe has written the Version row, so the reason is
	recorded with THIS change and then gone before the next one. Written with
	`update_modified=False`: it is housekeeping, not a change anybody made.
	"""
	if not doc.meta.has_field(F_REASON) or not doc.get(F_REASON):
		return
	frappe.db.set_single_value(SETTINGS, F_REASON, None, update_modified=False)
	# The desk form is handed this same document back after the save. Emptied
	# here too, so the screen does not keep showing a reason the record no longer
	# holds - and so a second save cannot quietly reuse it.
	doc.set(F_REASON, None)


# ── what the settings screen shows: counts, the retention line, the history ──

def _hr_only():
	"""The counts are about the whole tenant and carry no names, but they are
	HR's business: an Employee-role user can read HR Settings and must not be
	handed a tally of who has the app."""
	roles = set(frappe.get_roles())
	if frappe.session.user == "Administrator" or roles & {"HR Manager", "HR User", "System Manager"}:
		return
	frappe.throw(_("Only HR can see this."), frappe.PermissionError)


def _parse_designations(raw):
	"""The list the screen currently shows, as sent by the form script."""
	if raw in (None, ""):
		return None
	if isinstance(raw, str):
		try:
			raw = json.loads(raw)
		except ValueError:
			frappe.throw(_("We could not read that request."), frappe.ValidationError)
	if not isinstance(raw, list) or len(raw) > 200:
		frappe.throw(_("We could not read that request."), frappe.ValidationError)
	out = []
	for item in raw:
		if not isinstance(item, str) or len(item) > 140:
			frappe.throw(_("We could not read that request."), frappe.ValidationError)
		if item.strip():
			out.append(item.strip())
	return out


def _employees_by_designation(designations):
	"""Active employees per designation, in ONE grouped query."""
	if not designations:
		return {}
	from frappe.query_builder.functions import Count

	Employee = frappe.qb.DocType("Employee")
	rows = (
		frappe.qb.from_(Employee)
		.select(Employee.designation, Count(Employee.name).as_("n"))
		.where(Employee.status == "Active")
		.where(Employee.designation.isin(designations))
		.groupby(Employee.designation)
	).run(as_dict=True)
	return {r.designation: cint(r.n) for r in rows}


def _app_phones_by_designation(designations):
	"""Active app phones per designation, in ONE grouped query with a join.

	Only app phones: a phone set up on the web check-in page is not stopped by
	these settings, so it must not be counted as one that will be.
	"""
	if not designations:
		return {}
	from frappe.query_builder.functions import Count

	Device = frappe.qb.DocType(DEVICE)
	Employee = frappe.qb.DocType("Employee")
	rows = (
		frappe.qb.from_(Device)
		.join(Employee).on(Device.employee == Employee.name)
		.select(Employee.designation, Count(Device.name).as_("n"))
		.where(Device.status == "Active")
		.where(Device.join_method == "App QR code")
		.where(Employee.designation.isin(designations))
		.groupby(Employee.designation)
	).run(as_dict=True)
	return {r.designation: cint(r.n) for r in rows}


def _waiting_codes():
	"""Codes made, not yet used, and not yet run out - the ones the switch would
	stop (AC-17). One count, no names."""
	from frappe.utils import now
	return frappe.db.count("Alvoraa App Invite",
	                       {"status": "Waiting", "expires_at": [">", now()]})


def _active_app_phones():
	return frappe.db.count(DEVICE, {"status": "Active", "join_method": "App QR code"})


def _retention_line():
	from alvoraa_portal import field_app_notice as notice
	return notice.retention_line()


def _describe(field, old, new):
	"""One line of history, in the screen's own words."""
	label = _(LABELS.get(field, field))
	if field == F_ENABLED:
		old, new = (_("on") if cint(old) else _("off")), (_("on") if cint(new) else _("off"))
	return f"{label}: {old or '—'} → {new or '—'}"


def _history():
	"""The last 20 changes to OUR fields on HR Settings, newest first.

	Read from Frappe's own Version rows - the same rows the desk's timeline
	shows - so there is one record, not a second one that could disagree. HR
	Settings holds many other settings, so the rows are read in one bounded query
	and filtered here to the ones that touched these fields.
	"""
	rows = frappe.get_all(
		"Version",
		filters={"ref_doctype": SETTINGS, "docname": SETTINGS},
		fields=["owner", "creation", "data"],
		order_by="creation desc",
		limit=VERSION_SCAN_LIMIT,
	)
	out = []
	for row in rows:
		try:
			data = json.loads(row.data or "{}")
		except ValueError:
			continue
		lines, reason = [], None
		for field, old, new in data.get("changed") or []:
			if field == F_REASON:
				reason = new
			elif field in TRACKED_FIELDS:
				lines.append(_describe(field, old, new))
		for table, child in data.get("added") or []:
			if table == F_DESIGNATIONS:
				lines.append(_("{0}: added {1}").format(_(LABELS[F_DESIGNATIONS]),
				                                        (child or {}).get("designation") or "—"))
		for table, child in data.get("removed") or []:
			if table == F_DESIGNATIONS:
				lines.append(_("{0}: removed {1}").format(_(LABELS[F_DESIGNATIONS]),
				                                          (child or {}).get("designation") or "—"))
		if not lines:
			continue
		out.append({
			"when": str(row.creation),
			"who": get_fullname(row.owner),
			"lines": lines,
			"reason": reason or "",
		})
		if len(out) >= HISTORY_LIMIT:
			break
	return out


@frappe.whitelist()
@requires_field_app_plan
def settings_info(designations=None):
	"""What the Field attendance app tab shows beside the fields.

	Counts for the confirm dialogs (AC-17, AC-18), the live employee count for
	the list on screen (AC-25), the photo retention line (AC-23) and the change
	history (AC-24). Read-only. Every count is one bounded query; nothing here
	loops over rows.

	`designations` is the list the screen currently shows, which may differ from
	the saved one while HR is editing. Absent, the saved list is used.
	"""
	_hr_only()
	shown = _parse_designations(designations)
	if shown is None:
		shown = settings()["designations"]

	employees = _employees_by_designation(shown)
	phones = _app_phones_by_designation(shown)
	return {
		"designations": shown,
		"employees_with_designations": sum(employees.values()),
		"per_designation": {d: {"employees": employees.get(d, 0), "phones": phones.get(d, 0)}
		                    for d in shown},
		"waiting_codes": _waiting_codes(),
		"active_app_phones": _active_app_phones(),
		"retention_line": _retention_line(),
		"history": _history(),
		"history_note": _("HR cannot change this list."),
		"app_off_words": _("The app is not switched on for field staff."),
		"not_field_words": _("This app is not for your job yet."),
	}


# ── install ──────────────────────────────────────────────────────────────────

def after_migrate():
	"""Add the fields to HR Settings, on migrate AND on install.

	Both, because a site built with `bench install-app` never runs a migrate
	(`alvoraa_portal/hooks.py` says why). Safe to run twice: fields are updated
	in place, and a value a tenant already saved is never overwritten (AC-14).
	"""
	if not frappe.db.exists("DocType", SETTINGS) or not frappe.db.exists("DocType", CHILD):
		return False

	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({
		SETTINGS: [
			{
				"fieldname": F_TAB,
				"fieldtype": "Tab Break",
				"label": "Field attendance app",
				"insert_after": "hiring_sender_email",
			},
			{
				"fieldname": F_SECTION,
				"fieldtype": "Section Break",
				"label": "Who is a field worker",
				"insert_after": F_TAB,
			},
			{
				"fieldname": F_DESIGNATIONS,
				"fieldtype": "Table MultiSelect",
				"label": "Field worker designations",
				"options": CHILD,
				"insert_after": F_SECTION,
				"description": "Only people with these designations can get the app and check in with a photo.",
			},
			{
				"fieldname": F_SWITCH_SECTION,
				"fieldtype": "Section Break",
				"label": "The app",
				"insert_after": F_DESIGNATIONS,
			},
			{
				"fieldname": F_ENABLED,
				"fieldtype": "Check",
				"label": "Field workers can use the app",
				"default": "1",
				"insert_after": F_SWITCH_SECTION,
				"description": "When this is off, you cannot make codes, and phones that joined stop marking attendance. Field workers can still use the web check-in page.",
			},
			{
				"fieldname": F_LIFETIME,
				"fieldtype": "Select",
				"label": "App codes work for",
				"options": "\n".join(LIFETIME_HOURS),
				"default": DEFAULT_LIFETIME,
				"insert_after": F_ENABLED,
				"description": "From 1 hour to 7 days. Shorter is safer. Longer is easier when you hand out printed codes before a joining day. HR can choose a shorter time for one code.",
			},
			{
				"fieldname": F_REASON,
				"fieldtype": "Select",
				"label": "Why? (kept in the change history)",
				"options": "\n" + "\n".join(CHANGE_REASONS),
				"insert_after": F_LIFETIME,
				"no_copy": 1,
				"description": "Needed when you turn the app off or remove a designation. It is emptied again after the save.",
			},
			{
				"fieldname": F_INFO_SECTION,
				"fieldtype": "Section Break",
				"label": "Photos and change history",
				"insert_after": F_REASON,
			},
			{
				"fieldname": F_INFO,
				"fieldtype": "HTML",
				"insert_after": F_INFO_SECTION,
			},
		]
	}, ignore_validate=True)

	# A Check custom field with default 1 is only 1 for a record that is CREATED
	# after the field exists. HR Settings already exists on every site, so the
	# switch would read as off on every existing tenant - the opposite of AC-14.
	# Seed the two values once, where no value has ever been stored.
	for fieldname, value in ((F_ENABLED, 1), (F_LIFETIME, DEFAULT_LIFETIME)):
		stored = frappe.qb.get_query(
			table="Singles",
			filters={"doctype": SETTINGS, "field": fieldname},
			fields="value",
		).run()
		if not stored:
			frappe.db.set_single_value(SETTINGS, fieldname, value, update_modified=False)

	frappe.clear_cache(doctype=SETTINGS)
	return True
