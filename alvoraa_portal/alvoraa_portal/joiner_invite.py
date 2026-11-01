"""The invite link: who issues one, who can take it back, and the token store.

Slice 078, step 6, HR's side. US-31, US-36, and counsel's Export and Purge.

## Where the token lives, and the one place this departs from 078-SEC-9

Surbhi's decision of 31 October 2026, option (c) **plus a purge**:
**Frappe's own `Web Form Request` is the token store and the validator.** It
mints a 32-byte `secrets.token_urlsafe` key, holds `expires_on`, burns the key
once with `first_used_on`, takes a row lock on the submit path, and ships
`Website Manager`-only so Guest cannot enumerate it. We re-implement none of
that.

**But it stores the key in CLEAR.** `Web Form Request.key` is a plain `Data`
field, looked up by direct comparison, and nothing in Frappe ever purges the
row - it appears nowhere in `frappe/hooks.py` and nowhere in Log Settings. So
option (c) cannot satisfy 078-SEC-9's *"only its SHA-256 hash is stored"*, nor
AC-101 as that criterion is currently worded.

**What we do instead, and it is a real narrowing rather than a restatement:**
our submit path **deletes the request row the moment it is used**
(`joiner_public.submit_invite`), and the daily job deletes expired ones
(`joiner_housekeeping`). So a clear-text key exists only while the link still
works - never after. The fragment half of SEC-9 is kept in full: the token
travels in the URL fragment, is posted in the request body, and the parameter is
named **`web_form_request_key`** so that Frappe's own error-snapshot redaction
masks it (`frappe/utils/logger.py` masks any form key containing `key`, `token`,
`secret`, `password`, `passwd` or `pwd`). **Renaming that parameter silently
stops the redaction.**

`03-implementation-notes.md` carries this as a documented deviation with her
name and the date, and says that AC-101 needs rewording to match what is built.

## The Web Form record is an anchor, not a form

`Web Form Request.web_form` is mandatory, so one `Web Form` record has to
exist. Ours is **unpublished**, and we never call Frappe's `accept()` - so
**Frappe renders no public form at all**, which is why the query-string problem
in the impact analysis's §0.1 never arises. The only public surface is our own
page. We write our own doctype with our own closed field list, so PRIV-9's
allow-list is ours rather than a Web Form's field table.
"""

import frappe
import hrms.alvoraa_org_structure.settings as org_settings
from frappe import _
from frappe.utils import add_to_date, cint, now

from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission.alvoraa_joiner_submission import (
	JOINER_FIELDS,
	erase,
)
from alvoraa_portal.field_app_limits import HR_KEY, _limited

DOCTYPE = "Alvoraa Joiner Submission"
REQUEST = "Web Form Request"
# An INTERNAL anchor record, never rendered and never read by a person, so it
# is named for what it is. Deliberately not a brand string: a visible
# "Alvoraa" has to be "Alvora" (ALV-149), and the cleanest way to honour that
# rule is not to put a brand name where nobody needs one.
WEB_FORM = "Joiner details (internal anchor, not a form)"
HR_ROLES = ("HR Manager", "System Manager")
ENDPOINT = "joiner_invite"


# ── the switch, and the one gate left on it ─────────────────────────────────

def form_is_on():
	"""Is pre-onboarding switched on at this tenant? **Off unless ticked.**

	078-PRIV-7's special precondition - that a retention period had to be set
	deliberately before this could be turned on - is **gone**, because counsel
	answered the question it existed for on 29 October 2026. The periods now
	have counsel-backed defaults, so they are no longer numbers we invented.
	What is left is the ordinary reason: a tenant turns a feature on
	deliberately.
	"""
	try:
		return bool(cint(org_settings.get("alvoraa_joiner_form_on")))
	except Exception:
		return False


def require_form_on():
	if not form_is_on():
		frappe.throw(
			_("Asking new joiners for their details before day one is switched "
			  "off. A System Manager turns it on in Organisation Settings."),
			frappe.ValidationError)


def _require_hr():
	if frappe.session.user in ("Guest", ""):
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	if not set(HR_ROLES) & set(frappe.get_roles()):
		from hrms.alvoraa_hr_core.access import refuse

		refuse(_("Only HR can invite a joiner."), "078-SEC-14",
		       f"{ENDPOINT}.invite_joiner")


def _web_form():
	"""The anchor record, created on first use and never rendered.

	**Found by what it IS, never by a guessed name.** Frappe autonames a Web
	Form from its title - "Alvoraa Joiner Details" becomes
	`alvoraa-joiner-details` - so looking it up by the title collided with its
	own row on every call after the first, which is how 28 tests failed at once.

	`published = 0` and `login_required = 0` are both deliberate: nothing of
	Frappe's own form is ever served, so there is no route that could put a key
	in a query string, and `key_required = 1` means
	`get_web_form_request` refuses a missing key rather than returning None.
	"""
	name = frappe.db.get_value("Web Form", {"doc_type": DOCTYPE}, "name")
	if name:
		return frappe.get_doc("Web Form", name)
	doc = frappe.get_doc({
		"doctype": "Web Form",
		"title": WEB_FORM,
		"route": "alvoraa-joiner-anchor",
		"doc_type": DOCTYPE,
		"module": "Alvoraa Portal",
		# NOT published. Frappe serves nothing for this record; it exists so
		# that `Web Form Request.web_form` has something to point at.
		"published": 0,
		"login_required": 0,
		"key_required": 1,
		"allow_multiple": 0,
		"allow_edit": 0,
		"allow_delete": 0,
		"show_list": 0,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return doc


# ── issuing one ──────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
@_limited(HR_KEY, "user", limit=30)
def invite_joiner(full_name=None):
	"""Make one invite and hand back its link ONCE.

	The link is returned by this call and stored nowhere we can read it back -
	the row holds Frappe's key, which our submit path then deletes. HR sends it
	on; if it is lost, HR cancels and issues another.
	"""
	_require_hr()
	require_form_on()
	name = (full_name or "").strip()
	if not name:
		frappe.throw(_("Give the joiner's name."), frappe.ValidationError)

	days = max(1, cint(org_settings.get("alvoraa_joiner_link_days")) or 7)
	expires = add_to_date(now(), days=days)

	sub = frappe.get_doc({
		"doctype": DOCTYPE,
		"status": "Invited",
		"full_name": name,
		"invited_by": frappe.session.user,
		"expires_on": expires,
	}).insert()

	# Frappe mints the key. We never generate, never store and never log one.
	request = frappe.get_doc({
		"doctype": REQUEST,
		"web_form": _web_form().name,
		"expires_on": expires,
		# Forced onto the document by Frappe on its own paths, and read by ours
		# as the binding between this key and this one row.
		"doc_values": frappe.as_json({"full_name": name}),
		"references": [{"link_doctype": DOCTYPE, "link_name": sub.name}],
	}).insert(ignore_permissions=True)

	sub.db_set("web_form_request", request.name, update_modified=False)
	frappe.db.commit()

	# The row id and who issued it. **Never the key**, and never the name.
	frappe.logger("alvoraa").info(
		f"joiner invite issued: {sub.name} by {frappe.session.user} at {now()}, "
		f"{days} day link")

	return {
		"submission": sub.name,
		# The ONE time this is returned. In the FRAGMENT, so it never reaches a
		# server log, a Referer header or a synced browser history.
		"link": f"{frappe.utils.get_url()}/joiner#t={request.key}",
		"expires_on": str(expires),
		"link_days": days,
	}


@frappe.whitelist(methods=["POST"])
@_limited(HR_KEY, "user", limit=30)
def cancel_invite(submission=None, reason=None):
	"""Take a link back. Terminal, like every other move out of Invited."""
	_require_hr()
	doc = frappe.get_doc(DOCTYPE, submission)
	if doc.status not in ("Invited", "Submitted"):
		frappe.throw(_("This invite is already {0}.").format(_(doc.status)),
		             frappe.ValidationError)
	doc.status = "Cancelled"
	doc.cancel_reason = reason or "By HR"
	doc.save()
	_drop_request(doc)
	frappe.db.commit()
	frappe.logger("alvoraa").info(
		f"joiner invite cancelled: {doc.name} by {frappe.session.user} at {now()}")
	return {"status": doc.status}


def _drop_request(doc):
	"""Delete Frappe's request row, which is where the clear-text key lives.

	Called the moment a key stops being usable - on submit, on cancel, and by
	the daily job for an expired one. **This is the whole of the narrowing that
	makes option (c) acceptable**, so it is one function with one caller per
	path rather than three copies that can drift.
	"""
	if not doc.get("web_form_request"):
		return
	try:
		if frappe.db.exists(REQUEST, doc.web_form_request):
			frappe.delete_doc(REQUEST, doc.web_form_request, force=True,
			                  ignore_permissions=True, delete_permanently=True)
		doc.db_set("web_form_request", None, update_modified=False)
	except Exception:
		# Worth knowing about: a key we meant to destroy is still there.
		frappe.log_error(f"Could not delete the request row for {doc.name}",
		                 "Joiner invite")


# ── counsel's two actions for a candidate's own request ─────────────────────

@frappe.whitelist()
def export_submission(submission=None):
	"""Everything held about one joiner, as a file HR can send them.

	Counsel, 29 October 2026: a candidate who never joined **has no login**, so
	they cannot see or export anything themselves. HR has to be able to answer
	"what do you hold about me" in one click, without a developer.

	It lists the files by NAME AND TYPE and does not include their bytes: the
	request is "what do you hold", the documents are the person's own and HR can
	send them separately, and putting identity scans into a JSON attachment is
	a second copy nobody asked for.
	"""
	_require_hr()
	doc = frappe.get_doc(DOCTYPE, submission)
	files = frappe.get_all("File", filters={
		"attached_to_doctype": DOCTYPE, "attached_to_name": doc.name,
	}, fields=["file_name", "creation"], limit_page_length=0, ignore_permissions=True)

	body = {
		"what_this_is": "Everything held about one person who was invited to "
		                "send their details before their first day.",
		"reference": doc.name,
		"status": doc.status,
		"invited_on": str(doc.creation),
		"sent_on": str(doc.submitted_at) if doc.submitted_at else None,
		"erased_on": str(doc.erased_on) if doc.erased_on else None,
		"details": {f: doc.get(f) for f in JOINER_FIELDS},
		"bringing_on_the_first_day": doc.bring_on_day_one or None,
		"files": [{"name": f.file_name, "given_on": str(f.creation)} for f in files],
	}
	frappe.local.response.filename = f"what-we-hold-{doc.name}.json"
	frappe.local.response.filecontent = frappe.as_json(body, indent=2).encode("utf-8")
	frappe.local.response.type = "download"
	frappe.logger("alvoraa").info(
		f"joiner submission exported: {doc.name} by {frappe.session.user} at {now()}")


@frappe.whitelist(methods=["POST"])
def purge_submission(submission=None):
	"""Erase one joiner's details and files now, on their own request.

	`force=True`: this is the one case where a legal hold does not stop an
	erasure, because the person has asked and HR has decided. The hold exists to
	stop a CLOCK deleting something somebody wants preserved, not to override a
	human acting on a request.
	"""
	_require_hr()
	doc = frappe.get_doc(DOCTYPE, submission)
	_drop_request(doc)
	done = erase(doc.name, why="HR purged it on request", force=True)
	frappe.logger("alvoraa").info(
		f"joiner submission purged: {doc.name} by {frappe.session.user} at {now()}")
	return {"erased": bool(done)}
