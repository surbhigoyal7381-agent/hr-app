"""What people can see and change about each other - the card's own endpoints.

Slice 078, step 3 (the field picker) and step 5 (the document types).

**The card is ABSENT for anyone who is not a System Manager, never greyed.** A
greyed control is a statement that somebody else can do this, which is both
true and useless; an absent one is the answer. `get_people_settings` refuses
everybody else, and `orgLoadPeople()` hides the card when it is refused - the
same shape the birthdays switch already uses.

**Saving goes through `alvoraa_org_structure.settings.set_cover_setting`**, not
through anything here, because all four keys are in its `ACCESS_GRANTING` set
and that path already does the three things that matter: System Manager only,
anybody else refused and logged as a structured line, and a `Version` row in
the same transaction naming the key, the old value and the new one. Writing a
second setter would have been a second place for those three things to be got
wrong.

**The audience figure counts PEOPLE, not accounts.** On the PP Jewellers copy
five accounts hold HR Manager and three of them are real people, so "7 people"
had to mean seven people or the sentence beside it is a lie. Disabled logins,
`Administrator` and `Guest` are all out.
"""

import frappe
import hrms.alvoraa_org_structure.people_fields as people_fields
import hrms.alvoraa_org_structure.settings as org_settings
from frappe import _
from frappe.utils import cint

from alvoraa_portal.joiner_invite import what_the_employer_has_not_set

POSITION = "Alvoraa Position"
DOC_TYPE = "Employee Document Type"

PROFILE_KEY = "alvoraa_positions_profile_fields"
DOCS_KEY = "alvoraa_positions_document_types"
MY_KEY = "alvoraa_my_profile_fields"
NOT_HIRED_KEY = "alvoraa_joiner_not_hired_days"
BACKSTOP_KEY = "alvoraa_joiner_backstop_days"
WARN_KEY = "alvoraa_joiner_warn_days"
FORM_ON_KEY = "alvoraa_joiner_form_on"
LINK_KEY = "alvoraa_joiner_link_days"
EMAIL_PHOTO_KEY = "alvoraa_photo_in_emails"
# Slice 079. The joiner section stops being facts only: 078 DECISION B made it
# a read-only panel because the Web Form owned the joiner's field list, and
# decision 5 reverses that - the tick is ours now, so the fourth picker is
# built, with its own "must fill in" tick inside it.
JOINER_FIELDS_KEY = "alvoraa_joiner_fields"
JOINER_REQUIRED_KEY = "alvoraa_joiner_required_fields"
MY_REQUIRED_KEY = "alvoraa_my_profile_required_fields"
JOINER_DOCS_KEY = "alvoraa_joiner_required_documents"
DOCUMENT_DAYS_KEY = "alvoraa_joiner_document_days"
NOTICE_KEY = "alvoraa_joiner_notice_text"
# The employer's own contact. Read by every joiner screen since 078 and written
# by nothing but a test, so at every real tenant that page would have refused to
# render for ever. NOT access-granting: a phone number is HR's own detail, not a
# decision about who sees whom.
HR_PHONE_KEY = "alvoraa_hr_contact_phone"
HR_EMAIL_KEY = "alvoraa_hr_contact_email"

# A document of one of these categories is an identity, statutory or
# background-check paper. Ticking one puts the FILE itself one click from a
# structure page, so the card says so standing, in amber, without anybody
# having to open a dialog (AC-84).
SENSITIVE_CATEGORIES = ("Identity", "Statutory", "Verification", "Employment", "Address")


def _require_system_manager(endpoint):
	if frappe.session.user in ("Guest", ""):
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	if "System Manager" not in frappe.get_roles():
		from hrms.alvoraa_hr_core.access import refuse

		# Neither the key nor the value is logged: the rule id says enough.
		refuse(_("Only a System Manager can change who may see the org chart. "
		         "Ask your System Manager to make this change."),
		       "078-SEC-5", endpoint)


@frappe.whitelist()
def get_people_settings():
	"""Everything the card draws, in one call. System Manager only."""
	_require_system_manager("people_settings.get_people_settings")

	chosen_docs = _chosen_docs()
	audience = position_readers()
	joiner_asked, joiner_required = people_fields.asked_and_required(
		JOINER_FIELDS_KEY, JOINER_REQUIRED_KEY)
	_my_asked, my_required = people_fields.asked_and_required(MY_KEY, MY_REQUIRED_KEY)
	return {
		"profile_fields": list(people_fields.allowed(
			PROFILE_KEY, frappe.db.get_default(PROFILE_KEY))),
		"profile_choices": list(people_fields.POSITIONS_PROFILE_FIELDS),
		"my_profile_fields": list(people_fields.allowed(
			MY_KEY, frappe.db.get_default(MY_KEY))),
		"my_profile_choices": list(people_fields.MY_PROFILE_WRITE_FIELDS),
		"document_types": chosen_docs,
		"sensitive": [d["name"] for d in chosen_docs
		              if d.get("category") in SENSITIVE_CATEGORIES],
		# AC-84, and this is the one wording change asked for in exchange for
		# 078-SEC-3 being declined: the amber line names the ACTUAL ROLES that
		# hold Read on Alvoraa Position, not only a count. With one-click tag
		# removal refused, it is the only automatic detection left - a System
		# Manager ticking a sensitive type sees "HR Manager, System Manager",
		# or sees a third role appear the day somebody widens it.
		"audience_count": audience["people"],
		"audience_roles": audience["roles"],
		# Four numbers that are easy to read as one another, so the card words
		# each of them rather than calling any of them "retention" or "expiry".
		"link_days": org_settings.get(LINK_KEY),
		"not_hired_days": org_settings.get(NOT_HIRED_KEY),
		"backstop_days": org_settings.get(BACKSTOP_KEY),
		"warn_days": org_settings.get(WARN_KEY),
		"joiner_form_on": bool(cint(org_settings.get(FORM_ON_KEY))),
		"photo_in_emails": photo_in_emails(),
		# ── slice 079 ──────────────────────────────────────────────────────
		# Both ticked lists for each surface, and `required` is always a SUBSET
		# of `asked`, computed by the one helper both readers use. A name on a
		# required list that is not being asked for is dropped here as well as
		# refused at the setter - which is the half that survives a future UI.
		"joiner_fields": list(joiner_asked),
		"joiner_required_fields": list(joiner_required),
		"my_profile_required_fields": list(my_required),
		# The candidate list is `MY_PROFILE_WRITE_FIELDS` BY IDENTITY, for all
		# three ticks, so a third list cannot appear and drift from the six the
		# code actually allows. The prototype drew sixteen rows - including bank
		# account and IFSC - and the drawing was wrong, not the code: offering
		# those would give an employee self-service write on their own bank
		# details (decision 6b).
		"joiner_choices": list(people_fields.MY_PROFILE_WRITE_FIELDS),
		"joiner_required_documents": _joiner_required_documents(),
		"document_days": org_settings.get(DOCUMENT_DAYS_KEY),
		"notice_text": frappe.db.get_default(NOTICE_KEY) or "",
		"hr_contact_phone": frappe.db.get_default(HR_PHONE_KEY) or "",
		"hr_contact_email": frappe.db.get_default(HR_EMAIL_KEY) or "",
		# What HR cannot invite anybody until somebody sets. The same list the
		# refusal names, from the same function, so the card and the refusal
		# can never disagree.
		"joiner_not_ready": [m["what"] for m in what_the_employer_has_not_set()],
		"last_changed": _last_changed(),
	}


def _joiner_required_documents():
	"""The compulsory document types, intersected with the ones actually ticked.

	Marking a type compulsory can never ADD a type to the joiner's form.
	"""
	from alvoraa_portal.employee_documents_read import ticked_types

	wanted = {v.strip() for v in
	          str(frappe.db.get_default(JOINER_DOCS_KEY) or "").split(",")
	          if v.strip()}
	try:
		offered = set(ticked_types())
	except Exception:
		offered = set()
	return sorted(wanted & offered)


@frappe.whitelist()
def get_document_type_choices():
	"""Every document type, for the picker dialog, grouped by its real category.

	Includes whether anybody has actually given one, because a type nobody has
	ever supplied is a different decision from one everybody has.
	"""
	_require_system_manager("people_settings.get_document_type_choices")
	rows = frappe.get_all(DOC_TYPE,
	                      fields=["name", "category", "collect_from",
	                              "mandatory_for_joining", "has_expiry", "description"],
	                      order_by="category asc, name asc", limit_page_length=0)
	given = _how_many_given([r.name for r in rows])
	out = []
	for r in rows:
		out.append({
			"name": r.name,
			"category": r.category or "",
			"collect_from": r.collect_from or "",
			"mandatory": bool(r.mandatory_for_joining),
			"has_expiry": bool(r.has_expiry),
			"description": r.description or "",
			"given": given.get(r.name, 0),
			"sensitive": (r.category or "") in SENSITIVE_CATEGORIES,
		})
	return {"types": out, "sensitive_categories": list(SENSITIVE_CATEGORIES)}


def _how_many_given(names):
	"""A COUNT per type, never a person. One statement."""
	if not names:
		return {}
	try:
		rows = frappe.get_all(
			"Employee Document",
			filters={"document_type": ("in", names), "attachment": ("is", "set")},
			fields=["document_type", "count(name) as n"],
			group_by="document_type", limit_page_length=0)
		return {r.document_type: r.n for r in rows}
	except Exception:
		# The doctype is not installed on this site, or has no `attachment`
		# column. A missing count is not a reason to refuse the dialog.
		return {}


def _chosen_docs():
	"""The ticked types, by NAME and with their real category - not a count.

	A name whose type has since been deleted is reported as unknown rather than
	dropped silently, so the card can say so instead of quietly shrinking
	(E17). The endpoint that serves a file refuses it either way.
	"""
	raw = frappe.db.get_default(DOCS_KEY) or ""
	wanted = [v.strip() for v in str(raw).split(",") if v.strip()]
	if not wanted:
		return []
	known = {r.name: r.category or "" for r in frappe.get_all(
		DOC_TYPE, filters={"name": ("in", wanted)},
		fields=["name", "category"], limit_page_length=0)}
	return [{"name": n, "category": known.get(n, ""), "known": n in known}
	        for n in wanted]


def position_readers():
	"""Who can open the Positions page: how many PEOPLE, and which roles.

	Counts enabled Users, excluding `Administrator` and `Guest`, and it comes
	from the server - a figure worked out in a browser is a figure a browser can
	be wrong about.
	"""
	roles = sorted({r.role for r in frappe.get_all(
		"Custom DocPerm", filters={"parent": POSITION, "read": 1}, fields=["role"],
		limit_page_length=0)})
	if not roles:
		# Frappe ignores the SHIPPED rows entirely once any custom row exists
		# for a doctype, and uses them when none does.
		roles = sorted({r.role for r in frappe.get_all(
			"DocPerm", filters={"parent": POSITION, "read": 1}, fields=["role"],
			limit_page_length=0)})
	if not roles:
		return {"people": 0, "roles": []}

	users = {r.parent for r in frappe.get_all(
		"Has Role", filters={"role": ("in", roles), "parenttype": "User"},
		fields=["parent"], limit_page_length=0)}
	users -= {"Administrator", "Guest"}
	if not users:
		return {"people": 0, "roles": roles}
	live = frappe.get_all("User", filters={"name": ("in", list(users)), "enabled": 1},
	                      pluck="name", limit_page_length=0)
	return {"people": len(live), "roles": roles}


@frappe.whitelist()
def who_can_open_positions():
	"""The names behind the figure (AC-99, Surbhi's ⚠ DECISION J).

	"7 people" with no way to see who is the exact failure the card exists to
	avoid, so the names are offered. System Manager only, like the card.
	"""
	_require_system_manager("people_settings.who_can_open_positions")
	audience = position_readers()
	if not audience["roles"]:
		return {"roles": [], "people": []}
	users = {r.parent for r in frappe.get_all(
		"Has Role", filters={"role": ("in", audience["roles"]), "parenttype": "User"},
		fields=["parent"], limit_page_length=0)} - {"Administrator", "Guest"}
	rows = frappe.get_all("User", filters={"name": ("in", list(users) or [""]),
	                                       "enabled": 1},
	                      fields=["name", "full_name"], order_by="full_name asc",
	                      limit_page_length=0) if users else []
	return {"roles": audience["roles"],
	        "people": [{"full_name": r.full_name or r.name} for r in rows]}


@frappe.whitelist(methods=["POST"])
def set_people_setting(key=None, value=None):
	"""Save one list. Thin on purpose.

	It checks the key is one of ours and then hands over to the access-granting
	path, which is where the System-Manager rule, the logged refusal and the
	`Version` row live. Nothing about who may change these settings is decided
	twice.
	"""
	if key not in (PROFILE_KEY, DOCS_KEY, MY_KEY, LINK_KEY, EMAIL_PHOTO_KEY,
	               NOT_HIRED_KEY, BACKSTOP_KEY, WARN_KEY, FORM_ON_KEY,
	               JOINER_FIELDS_KEY, JOINER_REQUIRED_KEY, MY_REQUIRED_KEY,
	               JOINER_DOCS_KEY, DOCUMENT_DAYS_KEY, NOTICE_KEY,
	               HR_PHONE_KEY, HR_EMAIL_KEY):
		from hrms.alvoraa_hr_core.access import refuse

		refuse(_("That setting cannot be changed here."), "078-SEC-5",
		       "people_settings.set_people_setting")
	if isinstance(value, (list, tuple)):
		value = ",".join(str(v).strip() for v in value if str(v).strip())
	return org_settings.set_cover_setting(key, value or "")


def _last_changed():
	"""Who changed any of the four, and when. From the `Version` rows the
	access-granting path writes - which Log Settings does not clear."""
	rows = frappe.get_all(
		"Version",
		filters={"ref_doctype": "DefaultValue",
		         "docname": ("in", [PROFILE_KEY, DOCS_KEY, MY_KEY, LINK_KEY,
		                            EMAIL_PHOTO_KEY, NOT_HIRED_KEY,
		                            BACKSTOP_KEY, WARN_KEY, FORM_ON_KEY,
		                            JOINER_FIELDS_KEY, JOINER_REQUIRED_KEY,
		                            MY_REQUIRED_KEY, JOINER_DOCS_KEY,
		                            DOCUMENT_DAYS_KEY, NOTICE_KEY])},
		fields=["owner", "creation"], order_by="creation desc", limit=1)
	if not rows:
		return {"by": "", "on": ""}
	return {"by": frappe.db.get_value("User", rows[0].owner, "full_name")
	              or rows[0].owner,
	        "on": str(rows[0].creation)}


# ── the one thing a Jinja email template is allowed to ask us ────────────────

def photo_in_emails():
	"""May an employee's photograph go into a company-wide reminder email?

	Counsel, 29 October 2026: the employer must be able to stop photographs
	going out in mail without turning off the photograph feature and without
	turning off the reminders. **Off unless a System Manager has ticked it on**
	(`alvoraa_org_structure.settings`, in the access-granting set, so the change
	leaves a `Version` row).

	Read from two Jinja templates in `templates/emails/`, which is why it is
	registered in `hooks.py`'s `jinja.methods`. It takes no arguments and
	returns a bool, so a template cannot ask it about anybody in particular.

	**Fails CLOSED.** Anything unreadable means no photograph in the mail - the
	cost of a missing face in a birthday email is nobody noticing; the cost of
	the other answer is a face in every colleague's inbox.
	"""
	try:
		return bool(cint(org_settings.get("alvoraa_photo_in_emails")))
	except Exception:
		return False
