"""Fixtures for slice 079, pre-onboarding — invented data only.

**Its own file, deliberately.** `fixtures_078.py` is being changed by another
session (ALV-278) while this slice is built, so nothing here touches it.

**Everything is invented.** No real person's name, number, email or document is
a fixture here, on any site, at any time.

AC-117 asks for a dev tenant where these controls are observable, and the first
line of it is the one that matters: **the form ships off, so a run that reports
"0 findings" without switching it on has proved nothing.** `switch_the_form_on`
is therefore called by the suite's own `setUp`, not left to a tenant.
"""

import frappe
from frappe.utils import cstr

DOCTYPE = "Alvoraa Joiner Submission"
DOC_TYPE = "Employee Document Type"

# The employer's own values, without which HR cannot invite anybody at all
# (US-2). Invented, and they are the Fiduciary's to set - ours are only what a
# test needs in order to get past the precondition.
TENANT = {
	"alvoraa_joiner_form_on": "1",
	"alvoraa_joiner_not_hired_days": "180",
	"alvoraa_joiner_document_days": "30",
	"alvoraa_joiner_notice_text":
		"We ask for these details so that your staff record is ready on your "
		"first day. Only our HR team reads them. Ring us if you would rather "
		"give them in person.",
	"alvoraa_hr_contact_phone": "+91 98100 00079",
	"alvoraa_hr_contact_email": "joining@example.com",
}

# Three of the six ticked, one of them compulsory - AC-117's shape. Three
# rather than all six so that "a field nobody ticked is not asked for" is a
# real check and not a vacuous one.
ASKED = ("cell_number", "personal_email", "current_address")
REQUIRED = ("cell_number",)

# One non-statutory type, ticked and compulsory. **Not an identity document**:
# the Aadhaar masker is held, so nothing here may look like a card.
DOC_NAME = "S079 Appointment letter"


def switch_the_form_on():
	for key, value in TENANT.items():
		frappe.db.set_default(key, value)
	frappe.db.set_default("alvoraa_joiner_fields", ",".join(ASKED))
	frappe.db.set_default("alvoraa_joiner_required_fields", ",".join(REQUIRED))
	frappe.db.commit()


def switch_the_form_off():
	for key in list(TENANT) + ["alvoraa_joiner_fields",
	                           "alvoraa_joiner_required_fields",
	                           "alvoraa_joiner_required_documents",
	                           "alvoraa_my_profile_required_fields"]:
		frappe.db.set_default(key, "")
	frappe.db.commit()


def a_document_type(required=False):
	"""One ticked document type, optionally compulsory.

	It is ticked through `alvoraa_positions_document_types`, which is the one
	list `ticked_types()` reads - the joiner's form offers what the organisation
	already chose to collect, so a type nobody chose is never asked for.
	"""
	if not frappe.db.exists(DOC_TYPE, DOC_NAME):
		frappe.get_doc({
			"doctype": DOC_TYPE,
			"document_type_name": DOC_NAME,
			"category": "Employment",
			"collect_from": "Employee",
			"description": "Invented for the 079 tests. Not an identity document.",
		}).insert(ignore_permissions=True)
	frappe.db.set_default("alvoraa_positions_document_types", DOC_NAME)
	frappe.db.set_default("alvoraa_joiner_required_documents",
	                      DOC_NAME if required else "")
	frappe.db.commit()
	return DOC_NAME


def a_row(full_name="S079 Priya Khanna", login_id="+91 98100 10079", invited_by=None):
	"""One submission row, as HR would type it before pressing the button.

	`login_id` is HR's OWN field and is deliberately not the joiner's `mobile`
	column: putting it there made HR's typing answer "has this joiner sent us
	anything yet?" on every row.
	"""
	doc = frappe.get_doc({
		"doctype": DOCTYPE,
		"status": "Invited",
		"full_name": full_name,
		"login_id": login_id,
		"invited_by": invited_by or frappe.session.user,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return doc


def allow_sign_in_by_mobile(on=True):
	"""Frappe's own site-wide switch, which the joiner's username needs.

	**It is site-wide**: with it on, every employee at that tenant can sign in
	with their mobile number too. Surbhi accepted that side effect by name
	(decision 6b), and the product refuses a mobile login id while it is off
	rather than turning it on for a tenant - so a test has to turn it on, and
	put it back.
	"""
	frappe.db.set_single_value("System Settings",
	                           "allow_login_using_mobile_number", 1 if on else 0)
	frappe.clear_cache(doctype="System Settings")
	frappe.db.commit()


def clear_the_rows():
	"""Every 079 row, its files and its accounts. Permanently."""
	for name in frappe.get_all(DOCTYPE, pluck="name", ignore_permissions=True):
		doc = frappe.get_doc(DOCTYPE, name)
		for f in frappe.get_all("File", filters={
			"attached_to_doctype": DOCTYPE, "attached_to_name": name,
		}, pluck="name", ignore_permissions=True):
			frappe.delete_doc("File", f, force=True, ignore_permissions=True,
			                  delete_permanently=True)
		user = cstr(doc.get("user") or "")
		frappe.db.delete("Version", {"ref_doctype": DOCTYPE, "docname": name})
		frappe.delete_doc(DOCTYPE, name, force=True, ignore_permissions=True,
		                  delete_permanently=True)
		if user and frappe.db.exists("User", user):
			frappe.delete_doc("User", user, force=True, ignore_permissions=True,
			                  delete_permanently=True)
	frappe.db.commit()


class FakeRequest:
	"""Just enough of a werkzeug request for the gate to read.

	The gate reads `request.path` and `frappe.local.form_dict["cmd"]` and
	nothing else, so a real HTTP request is not needed to drive it - and the one
	thing a unit test genuinely cannot see is the ordering, which has its own
	static test.
	"""

	def __init__(self, path):
		self.path = path
