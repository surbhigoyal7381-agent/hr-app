"""The joiner's side: three endpoints, a live token, and nothing else.

Slice 078, step 6. US-32, US-33, US-35, US-39. **The first public write path in
this product's history**, which is why every paragraph below is about what it
refuses.

## What a stranger can learn: nothing

078-SEC-13. Frappe's own validator gives four different answers - key missing,
key unknown, key used, key expired - and two of them are a different exception
class. **Our page flattens them into ONE** for missing, unknown, expired and
cancelled, and gives the narrower "already used" answer only for a key that was
genuinely burnt, which SEC-13 allows as *"a deliberate, narrower disclosure to a
person who already held a live token"*.

So a stranger posting a random string cannot tell whether it was wrong, whether
it once existed, or whether anybody has been invited at all.

## The token

In the **URL fragment** (`#t=…`), which a browser never sends to a server -
so it reaches no access log, no `Referer` and no proxy. The page posts it in the
**request body** under the name **`web_form_request_key`**, and that exact name
is load-bearing: Frappe's error-snapshot redaction masks any form key whose name
contains `key`, `token`, `secret`, `password`, `passwd` or `pwd`
(`frappe/utils/logger.py`). **Rename it and the redaction silently stops.**

Validation is Frappe's `get_web_form_request`: expiry, the single-use burn and a
row lock on submit, all maintained by the framework. The moment a key stops
being usable, `joiner_invite._drop_request` deletes the row that holds it - see
that module for why.

## Nothing is stored before the token is checked

OPS-29. No partial row, no file, nothing. And **no document bytes ever go into
`localStorage`**: a joiner may be on a borrowed phone, and an image in
`localStorage` also blows the quota and fails silently. "Your answers are kept
on this phone" means the typed answers only, which is what the page does.

## Uploads are ours, because `upload_file` is token-blind

`frappe/handler.py`'s `upload_file` never looks at `web_form_request_key`: a
guest upload there is gated only by `allow_guests_to_upload_files` plus the
`allowed_doctypes_for_guest_uploads` list. So **that switch stays OFF and the
allow-list stays empty** (DevOps OPS-40) - the site-wide hole is never opened,
not even for a minute - and `upload_invite_file` below does the work with the
token checked first.
"""

import base64
import binascii

import frappe
import hrms.alvoraa_org_structure.settings as org_settings
from frappe import _
from frappe.utils import cint, cstr, now

from alvoraa_portal import joiner_invite
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission.alvoraa_joiner_submission import (
	JOINER_FIELDS,
)
from alvoraa_portal.field_app_limits import JOINER_KEY, _limited

DOCTYPE = "Alvoraa Joiner Submission"

# JPEG, PNG and PDF. Nothing else, and checked on MAGIC BYTES - not the
# extension, not the browser's content type. An `.exe` renamed `.pdf` is
# refused here.
MAGIC = {
	b"\xff\xd8\xff": ("jpg", "image"),
	b"\x89PNG\r\n\x1a\n": ("png", "image"),
	b"%PDF": ("pdf", "pdf"),
}

# Per file, and per submission in total. The per-token byte ceiling is the one
# that matters: without it, nginx's 120 requests a minute per address allows
# about 3 GB a minute at the site's default file size.
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILE_B64 = int(MAX_FILE_BYTES * 4 / 3) + 128
MAX_FILES_PER_TOKEN = 6
MAX_BYTES_PER_TOKEN = 20 * 1024 * 1024


# ── one answer for every dead token ─────────────────────────────────────────

def _gone():
	"""J-E1. The SAME answer for missing, unknown, expired and cancelled."""
	frappe.throw(
		_("This link has run out. Links are short-lived so your details cannot "
		  "be opened by anybody else. Nothing you sent is lost. What to do: "
		  "ring or message the person who sent it and ask for a new link."),
		frappe.PermissionError)


def _used():
	"""The one narrower answer, to somebody who once held a live token."""
	frappe.throw(
		_("You have already sent your details, so this link will not open "
		  "again. There is nothing else to do."),
		frappe.PermissionError)


def _open(web_form_request_key, for_update=False):
	"""The token to its one submission row, or a refusal that tells you nothing.

	Every guest endpoint starts here. There is no other way in and there is no
	submission argument anywhere in this module - so there is nothing a caller
	can post that reaches a row other than their own.
	"""
	if not joiner_invite.form_is_on():
		# Off at this tenant: the same answer as a dead link, because whether a
		# feature is switched on is not a stranger's business either.
		_gone()
	if not isinstance(web_form_request_key, str) or not web_form_request_key.strip():
		_gone()

	# The anchor, found by what it is. It is never rendered and never published,
	# so Frappe serves no form for it - which is why the query-string problem
	# that option (a) would have had never arises here at all.
	try:
		web_form = joiner_invite._web_form()
	except Exception:
		_gone()

	try:
		request = web_form.get_web_form_request(
			web_form_request_key.strip(), for_update=for_update, allow_used=False)
	except frappe.exceptions.LinkExpired as e:
		# Frappe raises this for BOTH "already used" and "expired", with
		# different messages. Only the first earns the narrower answer.
		if "used" in cstr(e).lower():
			_used()
		_gone()
	except Exception:
		# PermissionError for a missing or an unknown key, and anything else we
		# did not foresee. All one answer.
		_gone()

	if not request:
		_gone()

	name = next((r.link_name for r in (request.references or [])
	             if r.link_doctype == DOCTYPE), None)
	if not name or not frappe.db.exists(DOCTYPE, name):
		_gone()

	doc = frappe.get_doc(DOCTYPE, name)
	if doc.status == "Submitted":
		_used()
	if doc.status != "Invited":
		# Cancelled, Expired, already an employee: one answer.
		_gone()
	return doc, request


# ── J1: what the joiner is told before the first question ───────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
@_limited(JOINER_KEY, "web_form_request_key", limit=20)
def open_invite(web_form_request_key=None):
	"""Everything the welcome screen draws. **The notice comes first.**

	078-PRIV-8: it is before the first question, not under a tick at the end,
	and every period in it is **the configured number** - never the prototype's
	literal 90. A notice carrying a number we invented is worse than no notice,
	because the joiner relies on it.
	"""
	doc, _request = _open(web_form_request_key)
	contact = _hr_contact()
	if not contact.get("phone") and not contact.get("email"):
		# **The screen refuses to render with a blank contact.** A notice that
		# tells somebody to get in touch, with nobody to get in touch with, is
		# the notice failing at the only thing it is for.
		frappe.throw(
			_("This link is not ready yet. Please ring the person who sent it "
			  "to you."), frappe.ValidationError)

	return {
		"full_name": doc.full_name or "",
		"fields": list(JOINER_FIELDS),
		"documents": _document_types(),
		"contact": contact,
		"brand": _brand(),
		# The real numbers, read now, so the screen cannot drift from the
		# setting. Named in plain words because "retention" and "expiry" have
		# already been read as the same thing once.
		"link_days": cint(org_settings.get("alvoraa_joiner_link_days")),
		"not_hired_days": cint(org_settings.get("alvoraa_joiner_not_hired_days")),
		"backstop_days": cint(org_settings.get("alvoraa_joiner_backstop_days")),
		"max_file_mb": MAX_FILE_BYTES // (1024 * 1024),
		"max_files": MAX_FILES_PER_TOKEN,
	}


def _hr_contact():
	"""A REAL way to reach a person, from the tenant's own settings.

	Never ours. The joiner's business is with the employer, and counsel was
	explicit that the rights footer carries the employer's details.
	"""
	out = {}
	for key, field in (("phone", "alvoraa_hr_contact_phone"),
	                   ("email", "alvoraa_hr_contact_email")):
		try:
			value = frappe.db.get_default(field)
		except Exception:
			value = None
		if value:
			out[key] = cstr(value)
	if not out.get("email"):
		# The company's own email, if the tenant set one. Still the employer's,
		# never ours.
		try:
			company = frappe.db.get_default("company")
			if company:
				email = frappe.db.get_value("Company", company, "email")
				if email:
					out["email"] = cstr(email)
		except Exception:
			pass
	return out


def _brand():
	"""The tenant's name and colour only. Both are already on its login page,
	so neither is a disclosure; nothing else about the tenant goes out."""
	try:
		return {"name": cstr(frappe.db.get_default("company") or "")}
	except Exception:
		return {"name": ""}


def _document_types():
	"""The ticked types, by name, so the joiner knows what to bring.

	The same list the Positions page shows, read from the same setting, so a
	type nobody chose is never asked for.
	"""
	from alvoraa_portal.employee_documents_read import ticked_types

	out = []
	for name in ticked_types():
		row = frappe.db.get_value("Employee Document Type", name,
		                          ["name", "category", "description"], as_dict=True)
		if row:
			out.append({"name": row.name, "category": row.category or "",
			            "description": row.description or ""})
	return out


# ── J5: sending it ──────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
@_limited(JOINER_KEY, "web_form_request_key", limit=3)
def submit_invite(web_form_request_key=None, values=None, bringing=None):
	"""Write the closed allow-list, burn the key, and destroy the key's row.

	Three at a time is the limit, per token, per hour - a joiner correcting a
	typo twice is ordinary; a hundred submissions from one link is not.
	"""
	doc, request = _open(web_form_request_key, for_update=True)

	if isinstance(values, str):
		try:
			values = frappe.parse_json(values)
		except Exception:
			values = None
	if not isinstance(values, dict):
		frappe.throw(_("Nothing to send."), frappe.ValidationError)

	# **THE CLOSED ALLOW-LIST (078-PRIV-9).** Anything not on it is not stored.
	# Dropped silently rather than refused, deliberately and unlike the
	# employee's own save: an error naming a field a stranger guessed at tells
	# them the field exists.
	for field in JOINER_FIELDS:
		if field in values:
			doc.set(field, cstr(values.get(field) or "").strip()[:500] or None)

	if isinstance(bringing, str):
		try:
			bringing = frappe.parse_json(bringing)
		except Exception:
			bringing = None
	if isinstance(bringing, (list, tuple)):
		# The TYPE NAMES they ticked, intersected with what the organisation
		# actually asked for. Never their own words.
		asked = {t["name"] for t in _document_types()}
		doc.bring_on_day_one = ", ".join(
			sorted({cstr(b) for b in bringing if cstr(b) in asked})) or None

	doc.status = "Submitted"
	doc.submitted_at = now()
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)

	# **The purge that makes option (c) acceptable.** The clear-text key is
	# destroyed the instant it stops being usable.
	joiner_invite._drop_request(doc)
	frappe.db.commit()

	# The row and the time. Never a field, never a name, never the key.
	frappe.logger("alvoraa").info(
		f"joiner submission received: {doc.name} at {now()}")

	return {
		"sent": True,
		"contact": _hr_contact(),
		"bringing": doc.bring_on_day_one or "",
	}


# ── J3: the uploads ─────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
@_limited(JOINER_KEY, "web_form_request_key", limit=12)
def upload_invite_file(web_form_request_key=None, document_type=None,
                       filename=None, data=None):
	"""One file, checked in this order, and the order is the point.

	  1. the token, through `_open` - **nothing is stored before this**;
	  2. the type is one the organisation actually asked for;
	  3. the count and the running total for this token;
	  4. the length of the **string**, before anything is decoded;
	  5. base64, strictly;
	  6. **magic bytes** - not the extension, not the content type;
	  7. an image is re-encoded, which strips its metadata. A photograph of a
	     document taken at home carries the location of somebody's home.

	**A PDF is NOT re-encoded**, because we cannot. So it gets the narrower
	treatment: stored private, served only through our own endpoint, and
	**never rendered inline**. We do not scan for malware and no product copy
	or questionnaire answer may say we do.
	"""
	doc, _request = _open(web_form_request_key)

	asked = {t["name"] for t in _document_types()}
	if cstr(document_type) not in asked:
		frappe.throw(_("That document is not one we asked for."),
		             frappe.ValidationError)

	existing = frappe.get_all("File", filters={
		"attached_to_doctype": DOCTYPE, "attached_to_name": doc.name,
	}, fields=["name", "file_size"], limit_page_length=0, ignore_permissions=True)
	if len(existing) >= MAX_FILES_PER_TOKEN:
		frappe.throw(
			_("You have already sent {0} files, which is as many as we can "
			  "take. Bring the rest on your first day.").format(MAX_FILES_PER_TOKEN),
			frappe.ValidationError)
	used = sum(cint(f.file_size) for f in existing)

	if not isinstance(data, str) or len(data) > MAX_FILE_B64:
		# Before any decode. A 200 MB payload must not be expanded in a
		# worker's memory before we say we did not want it.
		_too_big()
	try:
		raw = data.split(",", 1)[1] if data.startswith("data:") else data
		blob = base64.b64decode(raw, validate=True)
	except (binascii.Error, ValueError, IndexError):
		_bad_type()

	if len(blob) > MAX_FILE_BYTES:
		_too_big()
	if used + len(blob) > MAX_BYTES_PER_TOKEN:
		frappe.throw(
			_("That would be more than we can take from one link. Bring the "
			  "rest on your first day."), frappe.ValidationError)

	kind = next((v for sig, v in MAGIC.items() if blob.startswith(sig)), None)
	if not kind:
		_bad_type()
	ext, family = kind

	if family == "image":
		try:
			from alvoraa_portal.employee_photo import _reencode

			# 1600 px is a readable photograph of an A4 page; quality 82 is the
			# usual floor. The re-encode is what strips the metadata, and it is
			# why an image is safer here than a PDF.
			blob = _reencode(blob, 1600, 82)
			ext = "jpg"
		except Exception:
			_bad_type()

	f = frappe.get_doc({
		"doctype": "File",
		"file_name": f"joiner-{doc.name}-{cstr(document_type)[:40]}.{ext}",
		"attached_to_doctype": DOCTYPE,
		"attached_to_name": doc.name,
		"is_private": 1,
		"content": blob,
	}).insert(ignore_permissions=True)
	frappe.db.commit()

	# The row, the type and the size. Never the bytes, never the file's address.
	frappe.logger("alvoraa").info(
		f"joiner file received: {doc.name}, type {cstr(document_type)}, "
		f"{len(blob)} bytes, at {now()}")
	return {"stored": True, "files": len(existing) + 1,
	        "file_name": f.file_name}


def _bad_type():
	"""J-E2's wording: it always offers a way forward that is not "try again".
	A joiner may not own a scanner, may be on somebody else's phone, or may not
	have the document yet."""
	frappe.throw(
		_("That did not reach us. We can take a photo or a PDF. Your other "
		  "answers are safe on this phone - nothing is lost. Try taking a "
		  "photograph of it with your camera, or choose "
		  "“I will bring it on my first day” and carry on."),
		frappe.ValidationError)


def _too_big():
	frappe.throw(
		_("That file is too large. A photograph taken with your camera is "
		  "usually fine. Your other answers are safe on this phone."),
		frappe.ValidationError)
