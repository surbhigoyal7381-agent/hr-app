"""Slice 082: the public event form. One phone page per CRM form, one save.

An attendee scans a QR code at an event, fills in a short form on their own
phone and presses Send. The entry becomes a CRM Lead stamped with the form it
came from. No login.

Why our own page and save, and not CRM's `/crm-form/<route>`: CRM's page saves
through Frappe's `web_form.accept`, which allows 10 saves a minute per address.
A 300-person hall shares one Wi-Fi, so most of the hall would be refused. Ours
allows 300 a minute per event form (`_limited`, keyed on the hashed route).

What this module does NOT do:
  * It never edits CRM. It reads CRM's Web Form record and inserts a CRM Lead
    through CRM's own controller, so all of CRM's validation still runs.
  * It never reads a lead back to a guest. A save answers one fixed body.
  * It never writes a value the form does not ask for (SEC-1). The writable
    fields are the form's own rows of an allowed type, nothing else.

Bypasses (data-doors.md), both listed in 00/03:
  1. The guest insert, `ignore_permissions=True`. Counted in
     `TestSec16IgnorePermissionsCeiling.CEILINGS` at 1.
  2. `_erase_copies`: `frappe.db.delete` of the Deleted Document, Version and
     Comment rows of an event lead someone with delete right has just deleted.
     Takes no user input.
"""

import functools
import json
import re
from datetime import date

import frappe
from frappe import _

from alvoraa_portal.field_app_errors import FieldAppRefusal, desk_request, refuse
from alvoraa_portal.field_app_limits import EVENT_KEY, _hash, _limited

LEAD = "CRM Lead"
FORM_MODULE = "FCRM"  # CRM's own forms, the same test crm.api.form._get_crm_form uses

EVENT_FORM = "custom_event_form"
RATING = "custom_event_rating"
COMMENT = "custom_event_comment"
CONSENT_EVENT = "custom_consent_event"
CONSENT_NEWS = "custom_consent_news"

RATINGS = (
	"5 · Very good · बहुत अच्छा",
	"4 · Good · अच्छा",
	"3 · OK · ठीक-ठाक",
	"2 · Poor · खराब",
	"1 · Very poor · बहुत खराब",
)

# Made on every site with CRM by after_migrate, and by after_app_install when CRM
# arrives later. Never a fixture: a fixture on CRM Lead breaks `migrate` on every
# tenant without CRM.
FIELDS = [
	{"fieldname": EVENT_FORM, "label": "Event form", "fieldtype": "Link", "options": "Web Form",
	 "read_only": 1, "in_standard_filter": 1, "insert_after": "source"},
	{"fieldname": RATING, "label": "Event rating", "fieldtype": "Select",
	 "options": "\n" + "\n".join(RATINGS), "insert_after": EVENT_FORM},
	{"fieldname": COMMENT, "label": "Event comment", "fieldtype": "Small Text",
	 "insert_after": RATING},
	{"fieldname": CONSENT_EVENT, "label": "Consent: this event", "fieldtype": "Check",
	 "set_only_once": 1, "insert_after": COMMENT},
	{"fieldname": CONSENT_NEWS, "label": "News OK", "fieldtype": "Check",
	 "insert_after": CONSENT_EVENT},
]

# The "standard seven": every other question on a form is an extra (D9).
STANDARD = {"first_name", "mobile_no", "email", RATING, COMMENT, CONSENT_EVENT, CONSENT_NEWS}

# An allow list, not a ban list: a field type Frappe adds later stays refused until
# someone adds it here (SEC-4). Link is the staff-name leak (G2); editors would let
# a guest write HTML into staff screens (SEC-9).
ALLOWED = {"Data", "Phone", "Small Text", "Text", "Long Text", "Int", "Float", "Select", "Check", "Date"}
LAYOUT = {"Section Break", "Column Break"}
TEXT = {"Small Text", "Text", "Long Text"}
DATA_MAX = 140
TEXT_MAX = 2000

# Never writable by a guest, whatever a form says.
NEVER = {"lead_owner", "status", "owner", "name", "naming_series", "_assign", "docstatus", EVENT_FORM}

# CRM fills these itself (status from CRM Lead.validate_status; naming_series from
# its default), so a form need not ask for them.
SYSTEM_FILLED = {"status", "naming_series"}

# PRIV-2: a seatbelt for honest mistakes, not a guarantee. "pan" only as a whole
# word, so "Company" and "Japan" do not close a form. Security owns the list (O-6).
_SENSITIVE = re.compile(
	r"aadhaar|aadhar|(?<![a-z])pan(?![a-z])|passport|voter|bank|ifsc|account no|health|medical"
	r"|disease|disability|religion|caste|sexual|आधार|धर्म|जाति|स्वास्थ्य"
)

ORGANISER_ROLES = {"Sales Manager", "System Manager"}


def log():
	"""The refusal and erasure log (OPS-26). Never a name, a mobile, an email or an answer."""
	return frappe.logger("event_form", allow_site=True)


# ── the open check, used by the page (GET) and by the save (POST) ────────────


def form_state(route: str) -> dict:
	"""What this route's form is, and whether it may open for the public.

	`problem` is None for a form that may open. Otherwise one of: "missing" (no
	such CRM event form - also used for a login-only or non-CRM Web Form),
	"draft", "link", "type", "hidden", "sensitive", "consent", "required".
	`label` names the question at fault. Guests are told none of this (SEC-4).

	Reads Web Form configuration without a permission check: it is the form's
	layout, not anybody's personal data, and a guest has no right on Web Form.
	"""
	state = {"form": None, "problem": "missing", "label": "", "fields": [], "extras": 0}
	if not isinstance(route, str) or not route or len(route) > 140:
		return state
	if not frappe.db.exists("DocType", LEAD):
		return state
	name = frappe.db.get_value(
		"Web Form",
		{"route": route, "doc_type": LEAD, "module": FORM_MODULE, "login_required": 0},
		"name",
	)
	if not name:
		return state

	form = frappe.get_doc("Web Form", name)
	meta = frappe.get_meta(LEAD)
	state["form"] = form

	fields = []
	for row in form.web_form_fields:
		if row.hidden:
			continue  # not drawn, not accepted
		df = meta.get_field(row.fieldname) if row.fieldname else None
		label = row.label or (df.label if df else row.fieldname) or ""
		if row.fieldtype in LAYOUT and not df:
			continue  # a layout row carries no value
		problem = _row_problem(df, row, label)
		if problem:
			state.update(problem=problem, label=label)
			return state
		fields.append((row, df))

	names = {df.fieldname for _row, df in fields}
	consent = next((row for row, df in fields if df.fieldname == CONSENT_EVENT), None)
	if CONSENT_NEWS not in names or not consent or not (consent.description or "").strip():
		state.update(problem="consent")
		return state

	for df in meta.fields:
		if df.reqd and df.fieldname not in SYSTEM_FILLED and df.fieldname not in names:
			state.update(problem="required", label=df.label or df.fieldname)
			return state

	state["fields"] = fields
	state["extras"] = len(names - STANDARD)
	state["problem"] = None if form.get("crm_published") else "draft"
	return state


def _row_problem(df, row, label: str) -> str | None:
	if not df or df.fieldname in NEVER or df.read_only:
		return "type"
	if df.hidden:
		return "hidden"
	if df.fieldtype not in ALLOWED:
		return "link" if df.fieldtype == "Link" else "type"
	words = " ".join([label, row.label or "", df.label or "", df.fieldname]).lower()
	if _SENSITIVE.search(words):
		return "sensitive"
	return None


def english(label: str) -> str:
	"""The English half of a bilingual label: the text before " / " or a line break."""
	return re.split(r" / |\n|<br\s*/?>", label or "", maxsplit=1)[0].strip()


# ── the save ────────────────────────────────────────────────────────────────


def _logged(fn):
	"""One log line per refusal, whatever refused it - including the limiter below."""

	@functools.wraps(fn)
	def wrapper(*args, **kwargs):
		frappe.flags.event_form_reason = None
		try:
			return fn(*args, **kwargs)
		except FieldAppRefusal as exc:
			route = kwargs.get("route")
			reason = frappe.flags.get("event_form_reason") or {
				"TOO_MANY_TRIES": "limit", "FORM_CLOSED": "closed", "SERVER_ERROR": "error",
			}.get(exc.alvoraa_code, "invalid")
			log().info(f"refused reason={reason} route={_hash(route if isinstance(route, str) else '')[:16]}")
			raise

	return wrapper


@frappe.whitelist(allow_guest=True, methods=["POST"])
@desk_request
@_logged
@_limited(EVENT_KEY, "route", limit=300, window=60)
def save(route: str = "", values: str = "") -> dict:
	"""Save one attendee's answers as one CRM Lead. Guest, POST only.

	Answers one fixed body on success - no lead name, no echo (SEC-2). Every
	refusal carries a code from field_app_errors.CODES. Values travel in the POST
	body only (OPS-8); a GET is refused by the whitelist.
	"""
	state = form_state(route)
	if state["problem"]:
		frappe.flags.event_form_reason = "closed" if state["problem"] in ("missing", "draft") else "banned_field"
		refuse("FORM_CLOSED", _("This form is not taking answers."))

	answers = _parse(values)
	writable = {df.fieldname: (row, df) for row, df in state["fields"]}
	if set(answers) - set(writable):
		refuse("INVALID_REQUEST", _("Not sent."))

	doc = {"doctype": LEAD, EVENT_FORM: state["form"].name}
	for fieldname, (row, df) in writable.items():
		doc[fieldname] = _clean(row, df, answers.get(fieldname))

	try:
		frappe.get_doc(doc).insert(ignore_permissions=True)
	except Exception as exc:
		# Never let Frappe log this one itself: its default traceback carries the
		# local variables, which hold the attendee's answers (PRIV-6, OPS-28).
		frappe.db.rollback()
		frappe.log_error(
			title="Event form save failed",
			message=f"route={_hash(route)[:16]} error={type(exc).__name__}",
		)
		frappe.clear_messages()
		frappe.flags.event_form_reason = "error"
		refuse("SERVER_ERROR", _("Not sent."))
	return {"saved": 1}


def _parse(values) -> dict:
	if isinstance(values, str):
		try:
			values = json.loads(values or "{}")
		except ValueError:
			refuse("INVALID_REQUEST", _("Not sent."))
	if not isinstance(values, dict) or not all(isinstance(k, str) for k in values):
		refuse("INVALID_REQUEST", _("Not sent."))
	return values


def _bad(label: str):
	refuse(
		"FIELD_INVALID",
		_("Please check “{0}”, then press Send again.").format(english(label)),
		label=english(label),
	)


def _clean(row, df, raw):
	"""One answer, checked and converted, or a FIELD_INVALID naming its label."""
	label = row.label or df.label or df.fieldname
	kind = df.fieldtype
	required = bool(row.reqd or df.reqd or df.fieldname == CONSENT_EVENT)

	if kind == "Check":
		# Never pre-set: a tick that did not arrive is 0, whatever the form's default.
		if raw in (1, "1", True, "true", "on"):
			value = 1
		elif raw in (0, "0", False, "false", "", None):
			value = 0
		else:
			_bad(label)
		if required and not value:
			_bad(label)
		return value

	if raw is None or raw == "":
		if required:
			_bad(label)
		return None
	if not isinstance(raw, str | int | float) or isinstance(raw, bool):
		_bad(label)
	text = str(raw).strip()
	if required and not text:
		_bad(label)

	if kind == "Int":
		if not re.fullmatch(r"-?\d{1,15}", text):
			_bad(label)
		return int(text)
	if kind == "Float":
		if not re.fullmatch(r"-?\d{1,15}(\.\d{1,9})?", text):
			_bad(label)
		return float(text)
	if kind == "Date":
		try:
			if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
				raise ValueError
			date.fromisoformat(text)
		except ValueError:
			_bad(label)
		return text
	if kind == "Select":
		options = [o for o in (df.options or "").split("\n") if o]
		if text not in options:
			_bad(label)
		return text

	if len(text) > (TEXT_MAX if kind in TEXT else DATA_MAX):
		_bad(label)
	if kind == "Data" and df.options == "Email" and not frappe.utils.validate_email_address(text):
		_bad(label)
	if (kind == "Phone" or (kind == "Data" and df.options == "Phone")) and not frappe.utils.validate_phone_number(text):
		_bad(label)
	return text  # stored as typed; nothing builds HTML from it (SEC-9)


# ── hooks ───────────────────────────────────────────────────────────────────


GUEST_CLOSED = ("User", "Employee", LEAD)


def refuse_guest_perm(doc, method=None):
	"""Custom DocPerm validate (SEC-6): no Guest row on User, Employee or CRM Lead.

	CRM's form builder offers a one-click "let guests pick from this list" on any
	Link target, User included - which would publish the staff list to anyone
	holding a poster link. This refuses that row, and the same row made by hand.
	"""
	if doc.role == "Guest" and doc.parent in GUEST_CLOSED:
		frappe.throw(
			_("Guests (anyone on the internet, not signed in) cannot be given access to {0}. "
			  "It would make that list public. Remove the field that needs it from the form instead.")
			.format(_(doc.parent)),
			frappe.PermissionError,
		)


def after_lead_delete(doc, method=None):
	"""CRM Lead after_delete (PRIV-5): an erased event lead leaves no copy behind.

	Frappe writes the Deleted Document row AFTER this hook runs, so the clean-up
	is put just before the commit of the same transaction. Frappe's own
	after-commit job removes Version and Comment rows too; doing it here as well
	means a failed job cannot leave them. Leads without an event stamp (CRM's
	own, slice 057's email intake) keep Frappe's normal behaviour.
	"""
	if not doc.get(EVENT_FORM):
		return
	name, form = doc.name, doc.get(EVENT_FORM)
	frappe.db.before_commit.add(lambda: _erase_copies(name))
	log().info(f"erased lead={name} form={form} by={frappe.session.user}")


def _erase_copies(name: str) -> None:
	frappe.db.delete("Deleted Document", {"deleted_doctype": LEAD, "deleted_name": name})
	frappe.db.delete("Version", {"ref_doctype": LEAD, "docname": name})
	frappe.db.delete("Comment", {"reference_doctype": LEAD, "reference_name": name})


def forget_unlinked_record(doc, method=None):
	"""FCRM Note / CRM Task / CRM Call Log on_update (PRIV-5, D1).

	CRM's own delete (crm.api.doc.delete_bulk_docs with "delete linked") first
	clears the record's link to the lead, saves it, then deletes it. Frappe keeps a
	Deleted Document copy - text included - and by then the copy no longer names
	the lead. So the moment a record is unlinked from an EVENT lead is the last
	moment we can tell; if the record is gone by the commit, its copies go too.
	A record only unlinked, not deleted, is left alone.
	"""
	before = doc.get_doc_before_save()
	if not before or before.get("reference_doctype") != LEAD or doc.get("reference_docname"):
		return
	lead = before.get("reference_docname")
	if not lead or not frappe.db.get_value(LEAD, lead, EVENT_FORM):
		return
	doctype, name = doc.doctype, doc.name
	frappe.db.before_commit.add(lambda: _erase_record_copies(doctype, name))


def _erase_record_copies(doctype: str, name: str) -> None:
	if frappe.db.exists(doctype, name):
		return
	frappe.db.delete("Deleted Document", {"deleted_doctype": doctype, "deleted_name": name})
	frappe.db.delete("Version", {"ref_doctype": doctype, "docname": name})


def ensure_fields() -> bool:
	"""after_migrate: the five fields on every site with CRM; nothing without it.

	update=False, the same as slice 057: made where missing, never changed after,
	so a tenant's own Customize Form choice is not undone at the next migrate.
	"""
	if not frappe.db.exists("DocType", LEAD):
		return False
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({LEAD: FIELDS}, ignore_validate=True, update=False)
	return True


def on_app_install(app_name: str) -> None:
	"""after_app_install: CRM installed after this app gets the fields at once."""
	if app_name == "crm":
		ensure_fields()
