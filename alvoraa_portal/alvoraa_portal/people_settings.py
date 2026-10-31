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

POSITION = "Alvoraa Position"
DOC_TYPE = "Employee Document Type"

PROFILE_KEY = "alvoraa_positions_profile_fields"
DOCS_KEY = "alvoraa_positions_document_types"
MY_KEY = "alvoraa_my_profile_fields"
RETENTION_KEY = "alvoraa_joiner_retention_days"
LINK_KEY = "alvoraa_joiner_link_days"

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
		# Two numbers that are easy to read as one, so the card words each of
		# them rather than calling either "retention" or "expiry".
		"retention_days": frappe.db.get_default(RETENTION_KEY) or "",
		"link_days": org_settings.get(LINK_KEY),
		"last_changed": _last_changed(),
	}


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
	if key not in (PROFILE_KEY, DOCS_KEY, MY_KEY, RETENTION_KEY, LINK_KEY):
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
		         "docname": ("in", [PROFILE_KEY, DOCS_KEY, MY_KEY, RETENTION_KEY,
		                            LINK_KEY])},
		fields=["owner", "creation"], order_by="creation desc", limit=1)
	if not rows:
		return {"by": "", "on": ""}
	return {"by": frappe.db.get_value("User", rows[0].owner, "full_name")
	              or rows[0].owner,
	        "on": str(rows[0].creation)}
