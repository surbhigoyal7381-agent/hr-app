"""Slice 079: the joiner's bearer link becomes a restricted sign-in.

Four things, all safe to run twice, and **none of them touches live data at any
tenant** - the pre-onboarding form ships off (`alvoraa_joiner_form_on = 0`) and
no joiner has ever submitted anything anywhere. There is no backfill and no
residue; this exists to clean up dev sites and to make the permission change
real on a site that has ever touched permissions.

1. **The `Alvoraa Joiner` role**, made here so it exists before Frappe could
   meet the name anywhere and create it *with* desk access - the trap
   `announcements.make_role` already records.

2. **HR Manager loses `report` and `export`, and HR User loses `report`**, on
   `Alvoraa Joiner Submission`. Counsel's ruling 9, and 078 finding F3 turned
   from "accept in writing" into a requirement: those two rows are a
   spreadsheet of every joiner's name, mobile, personal email, home address and
   emergency contact, unlogged. **`Custom DocPerm` is the real table** on a site
   that has ever opened Role Permissions Manager - Frappe ignores the shipped
   rows entirely once any custom row exists for a doctype - so both tables are
   cleaned. That is the 27 October lesson.

3. **Every `Web Form Request` row for this doctype is deleted**, with the
   unpublished `Web Form` anchor that existed only so those rows had something
   to point at. Each of those rows holds a **clear-text key** with nothing left
   to open, which is exactly what the login replaced.

4. Nothing is recreated on a rollback. A rollback of the code refuses every
   joiner sign-in, which is the shipped state anyway.
"""

import frappe

DOCTYPE = "Alvoraa Joiner Submission"


def execute():
	_make_the_role()
	_narrow_the_rows()
	_drop_the_token_store()
	frappe.db.commit()


def _make_the_role():
	"""Delegates to `joiner_invite.make_role`, which is also run by after_install.

	It used to be implemented here, and that was the bug: a patch never runs on a
	site built from scratch, so no new site ever got the role. One implementation,
	two callers - the same shape as `announcements.make_role`.
	"""
	from alvoraa_portal.joiner_invite import make_role

	make_role()


def _narrow_the_rows():
	"""Counsel's ruling 9, in both permission tables."""
	for table in ("DocPerm", "Custom DocPerm"):
		if not frappe.db.exists("DocType", table):
			continue
		for role, columns in (("HR Manager", ("report", "export")),
		                      ("HR User", ("report",))):
			for name in frappe.get_all(table, filters={"parent": DOCTYPE, "role": role},
			                           pluck="name", ignore_permissions=True):
				frappe.db.set_value(table, name, {c: 0 for c in columns},
				                    update_modified=False)
	frappe.clear_cache(doctype=DOCTYPE)


def _drop_the_token_store():
	"""The clear-text keys, and the anchor record they pointed at."""
	if frappe.db.exists("DocType", "Web Form Request"):
		anchors = frappe.get_all("Web Form", filters={"doc_type": DOCTYPE},
		                         pluck="name", ignore_permissions=True)
		for name in frappe.get_all("Web Form Request",
		                           filters={"web_form": ("in", anchors or [""])},
		                           pluck="name", ignore_permissions=True):
			frappe.delete_doc("Web Form Request", name, force=True,
			                  ignore_permissions=True, delete_permanently=True)
		for name in anchors:
			frappe.delete_doc("Web Form", name, force=True,
			                  ignore_permissions=True, delete_permanently=True)
