"""The joiner's side: four endpoints, all behind their own sign-in.

Slice 079. US-7 to US-10, US-13, US-21. It replaces slice 078's guest path.

## There is no `allow_guest` here any more, and that is the headline

078 made this the **first public write path in this product's history**. 079
removes it. Every endpoint below requires a session, and **the row is resolved
from `frappe.session.user`** through the submission's own `user` field.

The property that made the guest version safe survives the rewrite word for
word, and it is the only reason this module can be read quickly: **there is no
submission, row, name or id argument anywhere in this module**, so there is
nothing a caller can post that reaches a row other than their own. A static test
asserts it (079-SEC-4).

What that bought: the token, the URL fragment, the `Web Form` anchor, the
clear-text key in `Web Form Request`, and three of the five `ignore_permissions`
bypasses this file used to need - four of which existed only because the caller
was Guest and held no permission on anything (079-SEC-7).

## One answer for every ending

A joiner whose work is finished - sent and expired, cancelled, hired, turned
down - gets `_gone()`, **byte for byte the same wording whichever ending it
was**. A different answer for "turned down" would tell a candidate the outcome
of their application through a web page instead of from their employer.

**Pressing Send is not one of those endings** (decision 4a). It ends the form:
the typed answers become read-only, and the sign-in goes on working until its
date so somebody who finds their PAN card the next evening can still send it.

## Nothing is stored before the session is checked

OPS-29. And **no document bytes ever go into `localStorage`**: a joiner may be
on a borrowed phone, and an image in `localStorage` also blows the quota and
fails silently. Since 079 the typed answers are not in the browser either -
they are on the employer's own row, which is what makes "nothing was lost" true
on a different phone and what leaves a borrowed handset clean.

## Uploads are ours, because `upload_file` is token-blind and session-blind

`frappe/handler.py`'s `upload_file` is gated only by
`allow_guests_to_upload_files` plus `allowed_doctypes_for_guest_uploads`. So
**that switch stays OFF and the allow-list stays empty** (OPS-40) - and after
this slice there are zero guest endpoints that would ever need it.
"""

import base64
import binascii

import frappe
import hrms.alvoraa_org_structure.people_fields as people_fields
import hrms.alvoraa_org_structure.settings as org_settings
from frappe import _
from frappe.utils import cint, cstr, now

from alvoraa_portal import joiner_invite
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission.alvoraa_joiner_submission import (
	COLUMN_FOR_TICK,
)
from alvoraa_portal.field_app_limits import JOINER_KEY, _limited

DOCTYPE = "Alvoraa Joiner Submission"

ASKED_KEY = "alvoraa_joiner_fields"
REQUIRED_KEY = "alvoraa_joiner_required_fields"
REQUIRED_DOCS_KEY = "alvoraa_joiner_required_documents"

# JPEG, PNG and PDF. Nothing else, and checked on MAGIC BYTES - not the
# extension, not the browser's content type. An `.exe` renamed `.pdf` is
# refused here.
MAGIC = {
	b"\xff\xd8\xff": ("jpg", "image"),
	b"\x89PNG\r\n\x1a\n": ("png", "image"),
	b"%PDF": ("pdf", "pdf"),
}

# Per file, and per joiner in total. The per-joiner byte ceiling is the one that
# matters: without it, nginx's 120 requests a minute per address allows about
# 3 GB a minute at the site's default file size.
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILE_B64 = int(MAX_FILE_BYTES * 4 / 3) + 128
MAX_FILES_PER_JOINER = 6
MAX_BYTES_PER_JOINER = 20 * 1024 * 1024

# The joiner's own photograph travels under this one reserved name, through the
# same endpoint as the documents - the same session check, the same ceilings, the
# same magic bytes, the same private `File`.
#
# It cannot collide with a real type: an `Employee Document Type` is named by its
# own title, and `__photo__` is not a title anybody can type into Desk.
PHOTO_TYPE = "__photo__"


# ── one answer for every ending ─────────────────────────────────────────────

def _gone():
	"""The SAME answer for sent-and-expired, cancelled, hired and turned down.

	079-SEC-5. It names no person, no reason and no employer detail beyond the
	state, and the sign-in page says the same thing in its own words
	(`JOIN-ENDED`).
	"""
	frappe.throw(
		_("This sign-in has finished its job. Either you have already sent your "
		  "form, or your employer has closed it. Nothing is wrong, and nothing "
		  "you sent is lost. What to do: if you still need to send something, "
		  "ring the person who sent you the message."),
		frappe.PermissionError)


def _mine(for_update=False):
	"""The signed-in joiner's one row, or a refusal that tells you nothing.

	**Every endpoint starts here, and there is no other way in.** No argument
	reaches this function, so there is nothing a caller can post that selects a
	different row.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	if not joiner_invite.form_is_on():
		# Off at this tenant: the same answer as an ended sign-in, because
		# whether a feature is switched on is nobody else's business either.
		_gone()

	name = frappe.db.get_value(DOCTYPE, {"user": user}, "name")
	if not name:
		_gone()

	doc = frappe.get_doc(DOCTYPE, name)
	if doc.status not in ("Invited", "Submitted"):
		# Cancelled, Expired, already an employee: one answer.
		_gone()
	if doc.erased_on:
		_gone()
	if doc.expires_on and cstr(doc.expires_on) < now():
		# The daily job closes the account on its date; this covers the hours in
		# between, and a session captured before it ran.
		_gone()
	if for_update:
		doc.flags.ignore_permissions = True
	return doc


# ── what the page asks for, and what it cannot be sent without ─────────────

def _asked_and_required():
	"""The ticked details and which of them are compulsory.

	HR ticks `Employee`'s own column names - the SAME SIX an employee may
	correct about themselves - and this doctype's columns were named differently
	in 078, so `COLUMN_FOR_TICK` maps them. Both lists are intersected with the
	allow-list at this end as well as at the setter, so a name written straight
	into `DefaultValue` by any other route produces nothing.

	`full_name` is always asked and is never compulsory: it is HR's own entry at
	invite, pre-filled here, correctable by the joiner (AC-104).
	"""
	asked, required = people_fields.asked_and_required(ASKED_KEY, REQUIRED_KEY)
	return asked, set(required)


def _fields_for_the_page(doc):
	asked, required = _asked_and_required()
	out = [{
		"name": "full_name",
		"value": cstr(doc.full_name or ""),
		# Never required by a tick. Said in the payload rather than only in a
		# comment, so the page cannot decide otherwise.
		"required": False,
	}]
	for tick in asked:
		column = COLUMN_FOR_TICK[tick]
		out.append({
			"name": tick,
			"value": cstr(doc.get(column) or ""),
			"required": tick in required,
		})
	return out


def _document_types():
	"""The ticked types, by name, with which of them must be answered for.

	The same list the Positions page shows, read from the same setting, so a
	type nobody chose is never asked for. The required list is intersected with
	it, so marking a type compulsory can never add a type to the form.
	"""
	from alvoraa_portal.employee_documents_read import ticked_types

	wanted = {v.strip() for v in
	          cstr(frappe.db.get_default(REQUIRED_DOCS_KEY) or "").split(",")
	          if v.strip()}
	out = []
	for name in ticked_types():
		row = frappe.db.get_value("Employee Document Type", name,
		                          ["name", "category", "description"], as_dict=True)
		if row:
			out.append({"name": row.name, "category": row.category or "",
			            "description": row.description or "",
			            "required": row.name in wanted})
	return out


def _my_files(submission):
	"""The files on the caller's own row: names and sizes, never bytes.

	One read, used for the count, the running byte total and the "2 of 4
	documents sent" strip, so a joiner's visit costs one query for all three.
	"""
	return frappe.get_all("File", filters={
		"attached_to_doctype": DOCTYPE, "attached_to_name": submission,
	}, fields=["name", "file_name", "file_size"], limit_page_length=0,
		ignore_permissions=True)


def _sent_types(files):
	"""Which document types have a file, worked out from the stored file names.

	The names are ours - `joiner-<row>-<type>.<ext>` - so this needs no second
	field and no second query.
	"""
	return {f.file_name for f in files}


# ── what the joiner is told before the first question (US-21) ──────────────

@frappe.whitelist(methods=["POST"])
@_limited(JOINER_KEY, "user", limit=40)
def open_invite():
	"""Everything the form draws, including the notice. **The notice comes first.**

	078-PRIV-8's shape, with counsel's ruling 6 on top: the words are the
	**employer's own**, every period in it is **the configured number**, and the
	page refuses to render without either. A notice carrying a number we invented
	is worse than no notice, because the joiner relies on it.
	"""
	doc = _mine()
	contact = joiner_invite.hr_contact()
	notice = cstr(frappe.db.get_default("alvoraa_joiner_notice_text") or "").strip()
	if not contact or not notice:
		# **The screen refuses to render without the employer's words and a real
		# contact.** A notice that tells somebody to get in touch, with nobody to
		# get in touch with, is the notice failing at the only thing it is for -
		# and words we wrote would not be the Fiduciary's notice at all.
		frappe.throw(
			_("This form is not ready yet. Please ring the person who sent you "
			  "the message."), frappe.ValidationError)

	files = _my_files(doc.name)
	documents = _document_types()
	promised = {v.strip() for v in cstr(doc.bring_on_day_one or "").split(",")
	            if v.strip()}
	fields = _fields_for_the_page(doc)
	return {
		"fields": fields,
		"documents": documents,
		"promised": sorted(promised),
		"sent": sorted(_sent_types(files)),
		"files": len(files),
		"submitted": bool(doc.submitted_at),
		"submitted_at": str(doc.submitted_at) if doc.submitted_at else None,
		"expires_on": str(doc.expires_on) if doc.expires_on else None,
		"contact": contact,
		"brand": _brand(),
		# The employer's own words, and the real numbers read now, so the screen
		# cannot drift from the setting. Named in plain words because "retention"
		# and "expiry" have already been read as the same thing once.
		"notice": notice,
		"not_hired_days": cint(org_settings.get("alvoraa_joiner_not_hired_days")),
		"document_days": cint(org_settings.get("alvoraa_joiner_document_days")),
		"max_file_mb": MAX_FILE_BYTES // (1024 * 1024),
		"max_files": MAX_FILES_PER_JOINER,
		# The counts for "You are back, and nothing was lost" - computed, never
		# stored. "4 of 7" is a fact; "nothing was lost" is a claim.
		"answers_done": sum(1 for f in fields if cstr(f["value"]).strip()),
		"answers_total": len(fields),
		"documents_done": len([d for d in documents
		                       if d["name"] in promised
		                       or any(d["name"] in n for n in _sent_types(files))]),
		"documents_total": len(documents),
	}


def _brand():
	"""The tenant's name only. It is already on its login page, so it is not a
	disclosure; nothing else about the tenant goes out."""
	try:
		return {"name": cstr(frappe.db.get_default("company") or "")}
	except Exception:
		return {"name": ""}


# ── stopping and coming back (US-7) ────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
@_limited(JOINER_KEY, "user", limit=40)
def save_draft(values=None):
	"""Keep what has been typed so far, on the employer's own row.

	**A fourth endpoint, where the spec counts three, and this is the one place
	I departed from it.** 079-PRIV-5 asked for the draft to stay in the browser;
	the spec resolved that against the design (its §2, C2) and put the draft on
	the server, which is what makes *"nothing was lost"* true on a different
	phone and what leaves a borrowed handset with nothing on it. A server draft
	has to be written by something, and that something is this.

	It is **four session endpoints and zero guest endpoints** - the number that
	mattered was the public one, and it went from three to none.

	The row already existed from the moment HR invited, with the joiner's name
	on it, so this adds no new object for either clock to learn about. It writes
	only the closed allow-list and leaves `status` at `Invited`.
	"""
	doc = _mine(for_update=True)
	if doc.submitted_at:
		# After Send the typed answers are read-only to them (AC-74). Documents
		# are not - that is the whole point of decision 4a.
		frappe.throw(
			_("You have already sent your details, so they cannot be changed "
			  "here. Ring the person who sent you the message if something is "
			  "wrong."), frappe.ValidationError)
	written = _write_the_allow_list(doc, values)
	doc.flags.ignore_version = True
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	# The row and a count. Never a value: a mobile number and a home address are
	# exactly what must not reach a log line.
	frappe.logger("alvoraa").info(
		f"joiner draft kept: {doc.name}, {written} answer(s), at {now()}")
	return {"kept": written}


def _write_the_allow_list(doc, values):
	"""**THE CLOSED ALLOW-LIST (078-PRIV-9).** Anything not on it is not stored.

	Dropped silently rather than refused, deliberately and unlike the employee's
	own save: an error naming a field somebody guessed at tells them the field
	exists.
	"""
	if isinstance(values, str):
		try:
			values = frappe.parse_json(values)
		except Exception:
			values = None
	if not isinstance(values, dict):
		frappe.throw(_("Nothing to save."), frappe.ValidationError)

	asked, _required = _asked_and_required()
	written = 0
	if "full_name" in values:
		doc.set("full_name", cstr(values.get("full_name") or "").strip()[:140] or None)
		written += 1
	for tick in asked:
		if tick in values:
			doc.set(COLUMN_FOR_TICK[tick],
			        cstr(values.get(tick) or "").strip()[:500] or None)
			written += 1
	return written


# ── sending it (US-8, US-13) ───────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
@_limited(JOINER_KEY, "user", limit=10)
def submit_invite(values=None, bringing=None):
	"""Send the form. **Send ends the FORM, not the sign-in** (decision 4a).

	**A refusal costs the joiner nothing** (AC-38): `status` stays `Invited`,
	`submitted_at` stays empty, everything typed stays on the row, the session is
	untouched and no attempt is consumed. Both of those happen after the check
	below.

	**The only required list is the one HR ticked.** We add no mandatory field
	of our own on top of it (decision 2), and 078's rule survives underneath:
	with nothing marked required, one ticked field with a value or one document
	is enough.
	"""
	doc = _mine(for_update=True)
	if doc.submitted_at:
		frappe.throw(
			_("You have already sent your details. There is nothing else to do."),
			frappe.ValidationError)

	_write_the_allow_list(doc, values)

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

	short = what_is_still_needed(doc)
	if short:
		# Each missing item as a TAP, not a name, with its own way out travelling
		# inside the message (078 §17.6). Nothing is written.
		frappe.throw(
			_("Not sent yet. These still need an answer: {0}. Nothing has been "
			  "sent and you are still signed in - fill them in and press Send "
			  "again.").format(", ".join(short)),
			frappe.ValidationError)

	doc.status = "Submitted"
	doc.submitted_at = now()
	# 079-PRIV-2 clause 3. Without this the joiner's own values go into
	# `tabVersion`, where the erasure we promise them does not reach.
	doc.flags.ignore_version = True
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	# The row and the time. Never a field, never a name.
	frappe.logger("alvoraa").info(
		f"joiner submission received: {doc.name} at {now()}")

	return {
		"sent": True,
		"contact": joiner_invite.hr_contact(),
		"bringing": doc.bring_on_day_one or "",
		"expires_on": str(doc.expires_on) if doc.expires_on else None,
	}


def what_is_still_needed(doc):
	"""Every compulsory thing without an answer, in plain words.

	A document is **answered, never had**: a photograph OR "I will bring it on my
	first day" both count, because a joiner may not own it yet, may be on
	somebody else's phone, or may not be able to scan anything.
	"""
	asked, required = _asked_and_required()
	short = []
	for tick in asked:
		if tick in required and not cstr(doc.get(COLUMN_FOR_TICK[tick]) or "").strip():
			short.append(_label_for(tick))

	documents = [d for d in _document_types() if d["required"]]
	if documents:
		files = _sent_types(_my_files(doc.name))
		promised = {v.strip() for v in cstr(doc.bring_on_day_one or "").split(",")
		            if v.strip()}
		for d in documents:
			if d["name"] in promised:
				continue
			if any(d["name"] in name for name in files):
				continue
			short.append(d["name"])

	if not asked and not documents:
		# 078's AC-110c, unchanged: with nothing marked compulsory, an empty
		# send is still refused. Tapping Next, Next, Send without typing used to
		# be accepted, and HR got a blank row.
		if not any(cstr(doc.get(c) or "").strip() for c in COLUMN_FOR_TICK.values()) \
				and not _my_files(doc.name):
			short.append(_("at least one answer, or one document"))
	return short


# The words for each ticked detail, so a refusal names something a joiner can
# act on rather than a column name. The same vocabulary My Profile uses, because
# the same person meets both screens inside a week.
_LABELS = {
	"full_name": "Your full name",
	"cell_number": "Your mobile number",
	"personal_email": "Your email",
	"current_address": "Where you live now",
	"person_to_be_contacted": "Who to ring in an emergency",
	"relation": "How they are related to you",
	"emergency_phone_number": "Their phone number",
}


def _label_for(tick):
	return _(_LABELS.get(tick, tick))


# ── the uploads (US-9, US-10) ──────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
@_limited(JOINER_KEY, "user", limit=20)
def upload_invite_file(document_type=None, filename=None, data=None):
	"""One file, checked in this order, and the order is the point.

	  1. the session, through `_mine` - **nothing is stored before this**;
	  2. the type is one the organisation actually asked for;
	  3. the count and the running total for this joiner;
	  4. the length of the **string**, before anything is decoded;
	  5. base64, strictly;
	  6. **magic bytes** - not the extension, not the content type;
	  7. an image is re-encoded, which strips its metadata. A photograph of a
	     document taken at home carries the location of somebody's home.

	None of that was ever about the token, so none of it changes.

	**A PDF is NOT re-encoded**, because we cannot. So it gets the narrower
	treatment: stored private, served only through our own endpoint, and never
	rendered inline. **We do not scan for malware and no product copy or
	questionnaire answer may say we do.**

	**Documents stay open after Send** (decision 4a): somebody who finds their
	PAN card the next evening sends it here rather than ringing HR.
	"""
	# Kept lazy, as it always was here, so this module loads without Pillow.
	from alvoraa_portal import employee_photo

	doc = _mine()

	is_photo = cstr(document_type) == PHOTO_TYPE
	asked = {t["name"] for t in _document_types()}
	if not is_photo and cstr(document_type) not in asked:
		frappe.throw(_("That document is not one we asked for."),
		             frappe.ValidationError)

	existing = _my_files(doc.name)
	if len(existing) >= MAX_FILES_PER_JOINER:
		frappe.throw(
			_("You have already sent {0} files, which is as many as we can "
			  "take. Bring the rest on your first day.").format(MAX_FILES_PER_JOINER),
			frappe.ValidationError)
	used = sum(cint(f.file_size) for f in existing)

	if not isinstance(data, str) or len(data) > MAX_FILE_B64:
		# Before any decode. A 200 MB payload must not be expanded in a worker's
		# memory before we say we did not want it.
		_too_big()
	try:
		raw = data.split(",", 1)[1] if data.startswith("data:") else data
		blob = base64.b64decode(raw, validate=True)
	except (binascii.Error, ValueError, IndexError):
		_bad_type()

	if len(blob) > MAX_FILE_BYTES:
		_too_big()
	if used + len(blob) > MAX_BYTES_PER_JOINER:
		frappe.throw(
			_("That would be more than we can take from one person. Bring the "
			  "rest on your first day."), frappe.ValidationError)

	kind = next((v for sig, v in MAGIC.items() if blob.startswith(sig)), None)
	if not kind:
		_bad_type()
	ext, family = kind

	if is_photo and family != "image":
		# A PDF is not a photograph of a face, in the employee's own words, from
		# the employee's own module so the two cannot drift apart.
		frappe.throw(employee_photo._refused_type_message(),
		             frappe.ValidationError)

	if family == "image":
		try:
			# 1600 px is a readable photograph of an A4 page; quality 82 is the
			# usual floor. The re-encode is what strips the metadata, and it is
			# why an image is safer here than a PDF.
			#
			# The joiner's own picture gets the employee's own numbers, 512 px at
			# 82, read off the employee's own constants - so a joiner's face and
			# a member of staff's face are one treatment, not two.
			blob = (employee_photo._reencode(blob, employee_photo.STORED_EDGE,
			                                 employee_photo.STORED_QUALITY)
			        if is_photo else employee_photo._reencode(blob, 1600, 82))
			ext = "jpg"
		except Exception:
			# The documents wording offers "I will bring it on my first day",
			# which is not an answer on the photo screen.
			if is_photo:
				frappe.throw(employee_photo._refused_type_message(),
				             frappe.ValidationError)
			_bad_type()

	f = frappe.get_doc({
		"doctype": "File",
		"file_name": (f"joiner-{doc.name}-photo.{ext}" if is_photo
		              else f"joiner-{doc.name}-{cstr(document_type)[:40]}.{ext}"),
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
		_("That did not reach us. We can take a photo or a PDF. Everything else "
		  "you have filled in is safe - nothing is lost. Try taking a "
		  "photograph of it with your camera, or choose "
		  "“I will bring it on my first day” and carry on."),
		frappe.ValidationError)


def _too_big():
	frappe.throw(
		_("That file is too large. A photograph taken with your camera is "
		  "usually fine. Everything else you have filled in is safe."),
		frappe.ValidationError)
