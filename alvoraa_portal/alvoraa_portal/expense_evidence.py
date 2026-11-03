"""A bill on an expense claim, evidence on a day-fix (slice 081).

One module for the whole server side: taking the file, binding it to the
document that justifies it, refusing a claim that has none, streaming it to the
one person who decides it, recording who looked, and erasing it when its time is
up.

WHY ANY OF THIS IS NEW CODE. Desk already accepts an attachment on both
doctypes - the sidebar shows on any saved document with `write`, and
`allow_attachments` no longer exists as a DocType field. The portal is the gap:
`request-modals.html` had four fields and no file control, and
`apply_expense_claim` took no file. Rung 4 on the ladder; rungs 0-3 were all
read and rejected in `00-impact-analysis.md` section 6.1.

FIVE THINGS THIS MODULE DOES NOT DO, each for a reason:

  * **No `upload_file`.** The upload is our own base64 endpoint, not Frappe's
    `/api/method/upload_file`. Four independent reasons, and the first is the
    one that matters: Frappe's `File.check_max_file_size` runs inside
    `File.before_insert` -> `save_file`, so the RAW photo would be measured
    against System Settings `max_file_size` before our code ever saw it. Taking
    base64 and re-encoding first means only the FINAL bytes become a `File`, so
    the site-wide ceiling never sees a 4 MB camera frame. The others: we read
    the magic bytes before anything touches the disk; we choose the stored name
    at the only moment that is possible (below); and we skip Frappe's
    `ALLOWED_MIMETYPES` check, which guesses from the device's file name and is
    weaker than a magic-byte test anyway.

  * **No OCR, no page count, no text extraction, no PDF parsing.** The person
    knows the amount - they are standing at the pump. A parser is
    attacker-chosen input inside a library (081-PRIV-4).

  * **No second copy of the bytes.** No thumbnail, no derived preview, no cache,
    no object store, no CDN. One `File` row per document, and the row is MOVED
    onto its parent, never copied.

  * **No `/private/files/...` address reaches a browser.** `open_evidence`
    streams the bytes, following `employee_documents_read.open_employee_document`.

  * **Nothing here is called protected, secure, hidden, masked or redacted**,
    and nothing may be. We cannot mask the inside of a photograph. What is true,
    and all that may be said: who can open it, that every opening is recorded,
    and how long it is kept (081-PRIV-5).

THE STORED NAME IS OURS - ON THE PORTAL PATH, AND ONLY THERE. A device name
discloses on its own: `apollo-hospital-receipt.pdf` tells a reader what the
claim was for before they open anything, and any staff login can LIST file
names (Frappe's own `File` query condition is wider than the parent's read -
081-PRIV-2, R-2). So the portal generates the name.

**It cannot be made true on the other doors, and this file is where that is
written down.** There is no hook that fires before the bytes are written:
`File.before_insert` calls `save_file` itself, and an app `doc_events` handler
for `before_insert` runs AFTER the controller's own method
(`frappe/model/document.py` `Document.hook` -> `compose`), by which time the
file is on disk and `file_url` points at it. Renaming afterwards is worse than
useless - `save_file` de-duplicates by content hash, so a second row can share
the first row's `file_url`, and renaming that file on disk would break the other
row. So a bill attached in Desk, through REST `upload_file`, or by a data import
keeps the uploader's name, and is also not re-encoded, not capped and - if it is
a PNG - not stripped. HR is the uploader there, the volume is small, and capping
Desk would refuse a scanned self-declaration. Named limit, accepted by Surbhi on
3 November 2026 (OQ-7), and recorded beside R-7 rather than papered over.

The name also cannot carry the claim reference, for the same two-call reason the
design chose: the file is uploaded BEFORE the claim exists. It is
`bill-<date>-<hash>.jpg`, which is the shape the prototype draws.

WHY THE MANDATORY RULE IS NOT SIMPLY "A SUBMIT NEEDS A FILE". Read
`require_bill_before_submit`. A portal claim waits for its approver as a DRAFT,
and `hr_api.decide_expense` submits it - for Approve AND for Decline. A bare
gate would make declining impossible and would strand every claim already
waiting. Two conditions, both settled by Surbhi on 3 November 2026.
"""

import base64
import binascii
import hashlib
import io
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_months, add_to_date, cint, getdate, now, nowdate, today

from alvoraa_portal.field_app_limits import SELF_KEY, _limited

# ── the two documents, and the only names a browser may send ─────────────────

CLAIM = "Expense Claim"
REQUEST = "Attendance Request"

# A browser sends a KIND, never a doctype. There is no value a client can post
# that selects a code path or a table we did not choose here (081-SEC-5 cl. 5).
KINDS: dict[str, str] = {"bill": CLAIM, "dayfix": REQUEST}

ACCESS_LOG = "Alvoraa Photo Access Log"
SOURCE = {CLAIM: "Expense bill", REQUEST: "Day-fix evidence"}
NAME_PREFIX = {CLAIM: "bill", REQUEST: "dayfix"}

RULE_SUBMIT = "081-SEC-3"
RULE_TYPE = "081-SEC-4"
RULE_BIND = "081-SEC-5"
RULE_READ = "081-SEC-6"
RULE_RETAIN = "081-PRIV-1"

# ── the numbers, and where each one comes from ───────────────────────────────

# What we STORE. Surbhi, 3 Nov 2026: "File size not more than 1 mb", and "ok" to
# 3 MB for a PDF. A PDF cannot be recompressed the way an image can, and a
# two-page hotel invoice legitimately exceeds 1 MB.
STORED_IMAGE_MAX = 1 * 1024 * 1024
STORED_PDF_MAX = 3 * 1024 * 1024

# What we ACCEPT before any of that. The spec gave the stored caps and said
# "length before decode" without saying what length; these are the numbers
# Surbhi approved on 3 Nov 2026 (OQ-8). A current phone photograph is 2-8 MB, so
# 12 MB takes the ordinary case and refuses the outlier. A PDF is stored exactly
# as it arrived, so its raw and stored ceilings are necessarily the same number.
RAW_IMAGE_MAX = 12 * 1024 * 1024
RAW_PDF_MAX = STORED_PDF_MAX

# Base64 costs about a third on top, plus room for a `data:` prefix. Checked
# against the STRING first, so a 200 MB payload costs a length comparison rather
# than 200 MB of a worker's memory - the whole reason `employee_photo._decode`
# is ordered the way it is, copied here.
RAW_B64_MAX_CHARS = int(RAW_IMAGE_MAX * 4 / 3) + 128

# DevOps and the designer measured independently and landed on the same width.
# At 200 dpi - the floor in document-imaging guidance - a 210 mm A4 invoice needs
# about 1650 px across. 1600 px puts a frame-filling A4 at roughly 190 dpi and a
# thermal till receipt far above 300. The A4 hotel invoice is the hard case.
EDGE = 1600

# Quality steps down BEFORE width, and that order is the designer's one argued
# point: width loses characters, quality loses smoothness. A printed amount
# survives a soft JPEG and does not survive being 1024 px wide, so the width is
# the last thing touched rather than the first.
LADDER: tuple[tuple[int, int], ...] = (
	(EDGE, 82), (EDGE, 72), (EDGE, 62), (1280, 82), (1024, 82),
)

# What an accepted file starts with. Checked on the bytes, never on the
# extension and never on the browser's content type: a zip or an HTML file
# renamed `.jpg` is refused here (081-SEC-4 cl. 1).
MAGIC_IMAGE = (
	b"\xff\xd8\xff",                     # JPEG
	b"\x89PNG\r\n\x1a\n",                # PNG
)
MAGIC_PDF = b"%PDF-"

# ── retention ────────────────────────────────────────────────────────────────

# Companies Act 2013 s.128(5): books of account TOGETHER WITH THE VOUCHERS
# relevant to any entry, for not less than eight financial years immediately
# preceding the current one. CGST s.36's 72 months sits inside that, and its
# appeal/investigation proviso is our legal hold.
#
# A CONSTANT AND NOT A SETTING, and that is an open question rather than a
# decision. The analyst recommended a tenant setting with a floor of 8, and I
# agree with the reasoning - the employer is the Data Fiduciary and the duty is
# theirs. But this product's settings mechanism renders an organisation settings
# screen, and the approved design says in so many words that this slice adds no
# settings screen. Shipping the key would put two rows on a screen Surbhi has
# not seen. So: the floor is the default, the floor is enforced here, and
# `OQ-1` stays open. Making it a setting later is one entry in `DEFAULTS` and
# one range in `_DAYS`; nothing below has to change.
BILL_YEARS = 8

# Counsel, 18 Sep 2026, on performance-type records: the duration of employment,
# then a strict six-month buffer, then automatic permanent erasure. A day-fix
# file is not a financial record, so the statutory voucher clock cannot apply to
# it, and counsel's prohibition on indefinite soft deletion rules out "for ever".
DAYFIX_MONTHS = 6

# A file uploaded for a claim that was never filed has no purpose at all.
# OPS-15's 24 hours sits inside 081-PRIV-1 clause 5's outer bound of 7 days, so
# the rule is 24 hours and the 7 days is the window `counts()` reports over.
ORPHAN_HOURS = 24
# Never a file younger than this, whatever else is true. An upload in flight
# while the job runs must survive it.
ORPHAN_FLOOR_HOURS = 2
# Bounded per run, so one bad day cannot turn the daily job into an outage.
ORPHAN_LIMIT = 500
RETAIN_LIMIT = 500

LEGAL_HOLD = "alvoraa_legal_hold"

# The day the rule starts applying, stored once rather than written into the
# code. Surbhi, 3 Nov 2026, on being told DTC has many claims waiting: a claim
# filed before the release must stay fully decidable with no file. Set by
# `after_migrate` on the first run that finds it unset - which on DTC's release
# is the release date, and on a site built from scratch is the install date,
# where there are no older claims for it to exempt.
CUTOFF_KEY = "alvoraa_expense_bill_required_from"

# Off until the site config says otherwise, following `grooming.erase_daily`.
# This is the pass that deletes real data a person may still care about; the
# bill pass finds nothing for eight years and the orphan sweep deletes rubbish.
DAYFIX_ERASE_KEY = "alvoraa_dayfix_erase_enabled"


# ── the sentences ────────────────────────────────────────────────────────────
# Every one of these is the server's own words, reaching the screen verbatim.
# Never "upload failed", never "check your connection", never a Python error.

def _msg_wrong_type() -> str:
	return _("We can take a JPG, a PNG or a PDF. Most phones can take a JPG "
	         "- try again from the camera.")


def _msg_image_too_big(actual: str) -> str:
	return _("This photo is still {0} after we shrank it. The limit is 1 MB "
	         "- take it again with just the bill in the frame.").format(actual)


def _msg_pdf_too_big(actual: str) -> str:
	return _("This PDF is {0} and the limit is 3 MB. Send one page with the "
	         "bill on it, or photograph the bill instead.").format(actual)


def _msg_no_bill() -> str:
	"""The one sentence, in one voice, on every surface.

	Word for word the first sentence of the Desk refusal, so the rule does not
	change its story between the driver's phone and HR's screen.
	"""
	return _("A claim needs a photo or a PDF of the bill.")


def _human(size: int) -> str:
	"""A size a person can read. Never bytes, never "1048576"."""
	if size >= 1024 * 1024:
		return _("{0} MB").format(round(size / (1024 * 1024), 1))
	return _("{0} KB").format(max(1, round(size / 1024)))


# ── taking the file ──────────────────────────────────────────────────────────

def _decode(payload: Any) -> tuple[bytes, bool]:
	"""The posted string to raw bytes, or a refusal. Nothing is stored yet.

	The ORDER is the point of this function, and it is copied from
	`employee_photo._decode` line for line:

	  1. the length of the **string**, before anything is decoded;
	  2. base64, strictly;
	  3. **magic bytes** - not the extension, not the browser's content type;
	  4. the raw ceiling for the type we actually found.

	Returns (bytes, is_pdf).
	"""
	if not isinstance(payload, str) or not payload.strip():
		frappe.throw(_msg_wrong_type(), frappe.ValidationError)
	if len(payload) > RAW_B64_MAX_CHARS:
		# Before any decode. This is the line the whole ordering exists for.
		frappe.throw(_msg_image_too_big(_("over {0}").format(_human(RAW_IMAGE_MAX))),
		             frappe.ValidationError)
	try:
		raw = payload.split(",", 1)[1] if payload.startswith("data:") else payload
		blob = base64.b64decode(raw, validate=True)
	except (binascii.Error, ValueError, IndexError):
		frappe.throw(_msg_wrong_type(), frappe.ValidationError)

	if blob.startswith(MAGIC_PDF):
		if len(blob) > RAW_PDF_MAX:
			frappe.throw(_msg_pdf_too_big(_human(len(blob))), frappe.ValidationError)
		return blob, True
	if blob.startswith(MAGIC_IMAGE):
		if len(blob) > RAW_IMAGE_MAX:
			frappe.throw(_msg_image_too_big(_human(len(blob))), frappe.ValidationError)
		return blob, False
	# A HEIC lands here, and it is REFUSED rather than converted. Pillow 12.3.0
	# in this image has no HEIC reader and `pillow_heif` is absent (measured),
	# so a HEIC could be neither resized nor stripped - and storing one
	# unchanged would mean keeping an original-resolution photograph with its
	# location in it, in a format we cannot strip. The phone's own canvas
	# re-encode is what makes the ordinary iPhone case a JPEG; this is the
	# backstop for when it is not (081-SEC-4 cl. 4).
	frappe.throw(_msg_wrong_type(), frappe.ValidationError)


def _reencode(blob: bytes, edge: int, quality: int) -> bytes:
	"""One Pillow call: resize to `edge` on the longest side, strip everything,
	write JPEG. The same call `employee_photo._reencode` makes, with the edge and
	the quality as arguments.

	The strip is not a separate step. A new image is built from the pixels only,
	so no EXIF, no ICC profile, no GPS block and no thumbnail-in-the-file
	survives. That matters for a PNG in particular: Frappe's own
	`strip_exif_metadata_from_uploaded_images` runs for `image/jpeg` only
	(`file.py:813-819`), so a PNG would otherwise keep its coordinates.
	"""
	from PIL import Image

	with Image.open(io.BytesIO(blob)) as img:
		img = img.convert("RGB")
		img.thumbnail((edge, edge), Image.LANCZOS)
		out = io.BytesIO()
		# No `exif=` and no `icc_profile=`: anything not passed is not written.
		img.save(out, format="JPEG", quality=quality, optimize=True)
	return out.getvalue()


def _shrink_to_cap(blob: bytes) -> bytes:
	"""Down the ladder until it fits, or refuse naming the real size.

	**Every rung re-encodes the ORIGINAL bytes**, never the previous rung's
	output. Chaining five encodes would compound JPEG generation loss on exactly
	the artefact the legibility test judges (OPS-24), and the picture has already
	been through one pass on the phone.
	"""
	last = b""
	for edge, quality in LADDER:
		try:
			last = _reencode(blob, edge, quality)
		except Exception:
			# Pillow could not read it: it is not a picture we can bound or
			# strip, whatever its first three bytes said.
			frappe.throw(_msg_wrong_type(), frappe.ValidationError)
		if len(last) <= STORED_IMAGE_MAX:
			return last
	frappe.throw(_msg_image_too_big(_human(len(last))), frappe.ValidationError)


def _stored_name(parent_doctype: str, is_pdf: bool) -> str:
	"""Our name, and never the device's.

	It carries the day, which is what the prototype draws, and a random hash,
	which makes it unique by construction. It cannot carry the claim reference:
	the file is uploaded before the claim exists, which is the cost of the
	design's own two-call shape.

	The extension comes from the MAGIC BYTES WE READ, not from anything the
	uploader supplied - and that pairing is what closes stored cross-site
	scripting, because `File.save_file` sets the served content type from the
	stored file name (`file.py:813`). Magic bytes alone would still let an
	accepted `x.html` be served as HTML from our own origin.
	"""
	stamp = getdate(nowdate()).strftime("%d-%b").lower()
	return "%s-%s-%s.%s" % (NAME_PREFIX[parent_doctype], stamp,
	                        frappe.generate_hash(length=10),
	                        "pdf" if is_pdf else "jpg")


def _my_employee() -> frappe._dict | None:
	"""The caller's own ACTIVE employee record, or None.

	Active, always. ERPNext does not disable a leaver's login on every path, so
	this filter is what stops somebody who has left using a session they already
	had open.
	"""
	return frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user, "status": "Active"},
		["name", "employee_name"], as_dict=True)


def _require_signed_in_employee() -> frappe._dict:
	if frappe.session.user in ("Guest", ""):
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	me = _my_employee()
	if not me:
		frappe.throw(_("This account is not linked to an employee record, so "
		               "there is nothing to attach a file to. Ask HR to link it "
		               "to this account."), frappe.PermissionError)
	return me


def _kind_to_doctype(kind: Any) -> str:
	"""A browser sends "bill" or "dayfix". Anything else is refused here, so no
	client-supplied doctype ever selects a table or a code path."""
	doctype = KINDS.get(str(kind or "").strip())
	if not doctype:
		frappe.throw(_("That is not something a file can be attached to."),
		             frappe.ValidationError)
	return doctype


@frappe.whitelist(methods=["POST"])
@_limited(SELF_KEY, "user", limit=60)
def upload_evidence(file: str | None = None, kind: str | None = None) -> dict:
	"""Take one file and hold it, UNPARENTED, until its document is created.

	Sixty an hour per user (OPS-12). `upload_file` with `is_private=1` is
	reachable by every logged-in staff member, and a mandatory attachment
	multiplies legitimate traffic, which is what makes abuse hard to spot. A full
	disk is the failure that took production down for nine days on 10 September.

	**The row it writes is private, owned by the caller, and has no parent**, so
	until it is bound the only person who can read it is the person who sent it -
	Frappe's gate falls through to `owner == user` and then to False
	(`file.py:989-1026`). An upload for a claim that is never filed is therefore
	harmless as well as useless, and `sweep_orphans` takes it within a day.

	No `ignore_permissions`: the role `All` holds create and write on `File`, and
	`File.has_permission` answers True on `owner == user`, so the framework's own
	gate is enough. Checked rather than assumed (`file.json`).
	"""
	_require_signed_in_employee()
	parent_doctype = _kind_to_doctype(kind)

	blob, is_pdf = _decode(file)
	if is_pdf:
		# **Accepted exactly as it arrived, and nothing opens it.** A PDF is the
		# one accepted type we cannot strip, and saying so is better than a
		# sanitiser: a parser is attacker-chosen input in a library. No page
		# count, no text layer, no re-write (081-SEC-4 cl. 6).
		stored = blob
	else:
		stored = _shrink_to_cap(blob)

	name = _stored_name(parent_doctype, is_pdf)
	row = frappe.get_doc({
		"doctype": "File",
		"file_name": name,
		"is_private": 1,
		"content": stored,
	}).insert()
	# **No `frappe.db.commit()` here, deliberately.** Frappe commits a request
	# that succeeded, so the row is durable by the time the browser has its
	# answer and the next call can lock it - and if anything later in THIS
	# request fails, rolling the upload back is the better outcome: no orphan at
	# all rather than one for the sweep to find.
	#
	# An explicit commit also reaches further than it looks. It was here at
	# first, and it broke slice 076's suite: a commit in the middle of a test
	# makes that test's fixture writes permanent, so `tearDown`'s rollback
	# cannot undo them and a later test reads a half-applied fixture. The
	# failure looked nothing like this line - "Department ... does not belong to
	# company" - which is the kind of cost an unnecessary commit has.
	#
	# **The ROW ID is what comes back, and never the url.** Found by a test:
	# `File.save_file` de-duplicates by content hash (`file.py:823-840`), so two
	# uploads of byte-identical content produce TWO rows that share ONE
	# `file_url`. Looking a file up by url therefore returns an arbitrary one of
	# them - possibly another person's - which is both wrong and a way to touch
	# a row the caller never uploaded. A row id is unique and unambiguous, and
	# it is what `employee_documents_read` already takes.
	#
	# It also means no response on this path carries a `/private/files/...`
	# address at all, not even the uploader's (081-SEC-6, AC-52).

	# The size, the type and the document NAME. Never the file name a device
	# supplied, never the url, never anything about the person (081-PRIV-2).
	frappe.logger("alvoraa").info(
		"evidence upload: %s %s bytes for %s by %s at %s"
		% ("pdf" if is_pdf else "image", len(stored), parent_doctype,
		   frappe.session.user, now()))

	return {
		"file_id": row.name,
		"bytes": len(stored),
		"is_pdf": is_pdf,
		# What the screen shows back, so the person can judge their own photo.
		"label": "%s · %s" % (_human(len(stored)), name) if is_pdf
		else "%s · %s px · %s" % (_human(len(stored)), EDGE, name),
	}


# ── binding it to the document that justifies it ─────────────────────────────

def reserve(file_id: Any, parent_doctype: str) -> str | None:
	"""Claim the uploaded file for this call, **before** the parent is created.

	Two steps rather than one, and the split is the answer to a real race, not
	tidiness. `submitExpenseClaim` has **no duplicate guard** - two taps can be
	two calls - and the parent's name does not exist until it has been inserted.
	Bind-after-insert alone would let both calls pass the "not yet bound" check,
	both create a claim, and one end up with a claim it can never get a file
	onto. So the lock is taken here, first, and the loser is refused before its
	caller has inserted anything.

	**The read is a LOCKING read, and that matters on this database.** MariaDB
	runs REPEATABLE READ, so an ordinary `SELECT` would hand the second caller
	the row as it looked when its transaction started - unbound - however long
	it waited. `for_update` both serialises the two callers and makes the second
	one see the latest committed row (slice 021's lesson).

	**It takes the row's ID, not its url**, and that is not a style choice.
	`File.save_file` de-duplicates by content hash, so two uploads of identical
	bytes leave two rows sharing one `file_url`; a lookup by url would return an
	arbitrary one of them, which could be a row this caller never uploaded. A
	test found that, and the id closes it (081-SEC-5 clause 5).

	Returns the `File` row name, or None when no file was offered - the ordinary
	case on a day-fix, where attaching is the person's own choice.
	"""
	file_id = str(file_id or "").strip()
	if not file_id:
		return None

	row = frappe.db.get_value(
		"File", file_id,
		["name", "owner", "is_private", "attached_to_name"],
		as_dict=True, for_update=True)

	# ONE refusal for every failure, so the message never says which check
	# failed. The log line carries the row id, the rule and the doctype - never
	# a file name and never a url (081-PRIV-2).
	def refuse(why: str) -> None:
		frappe.log_error(
			title="081 evidence bind refused",
			message="%s rule %s for %s row %s"
			        % (why, RULE_BIND, parent_doctype,
			           (row or {}).get("name") or "none"))
		frappe.throw(_("That file could not be attached. Please choose it again."),
		             frappe.ValidationError)

	if not row:
		refuse("no such file row")
	if not cint(row.is_private):
		refuse("not private")
	if row.owner != frappe.session.user:
		refuse("not the caller's own upload")
	if row.attached_to_name:
		# A file already bound to something is never re-parented. Frappe's
		# `find_file_by_url` returns a file when ANY row with that url is
		# readable, so a second row for the same bytes would mean the gate is
		# satisfied by the weakest row. One row, moved once (081-SEC-5 cl. 5).
		refuse("already bound")
	return row.name


def attach(row_name: str | None, parent_doctype: str, parent_name: str) -> None:
	"""Give the reserved file its parent. One row, two fields, MOVED not copied.

	**This is the step OPS-17 calls a P1, and it is right.** Until a file has
	`attached_to_doctype` and `attached_to_name`, Frappe's gate falls back to
	`owner == user` and then to False (`file.py:989-1026`): an unparented bill is
	invisible to the approver, absent from the Desk sidebar, and silently skipped
	by every retention pass that walks the claim. So the acceptance criterion
	reads the row back out of `tabFile` rather than trusting this function.

	Called by the same server call that created the parent, inside the same
	transaction, while the lock `reserve` took is still held.
	"""
	if not row_name:
		return
	doc = frappe.get_doc("File", row_name)
	doc.attached_to_doctype = parent_doctype
	doc.attached_to_name = parent_name
	doc.save()


def has_evidence(parent_doctype: str, names: list[str]) -> set[str]:
	"""Which of these documents carry a file. **One query for the whole page.**

	The queue row needs a boolean, so the cost must not be one query per row:
	the count is the same for 200 rows as for 20 (`nfr-budget.md` section 2).
	`get_all` checks no permissions, and that is safe here only because every
	caller has already filtered its parents through `get_list` - the same
	reasoning, and the same ordering, as the existing single read of
	`Expense Claim Detail` in `inbox_api`. Callers must keep that order.
	"""
	if not names:
		return set()
	return set(frappe.get_all("File", filters={
		"attached_to_doctype": parent_doctype,
		"attached_to_name": ("in", list(names)),
	}, pluck="attached_to_name", limit_page_length=0))


# ── the mandatory rule, on the document ──────────────────────────────────────

def bill_required_from() -> str | None:
	"""The day the rule starts applying, or None when nothing has set it."""
	return frappe.db.get_default(CUTOFF_KEY) or None


def require_bill_before_submit(doc, method: str | None = None) -> None:
	"""`before_submit` on `Expense Claim`: an APPROVED claim carries its bill.

	On the document rather than in `apply_expense_claim`, because that endpoint
	inserts with `ignore_permissions=True` - a rule written inside a bypass is a
	rule inside a bypass. Here it holds for Desk, for
	`PUT /api/resource/Expense Claim`, for a data import and for anything else
	that ever submits a claim (081-SEC-3).

	**TWO CONDITIONS, AND NEITHER IS AN OPTIONAL EXTRA.** A bare "a submit needs
	a file" gate is wrong on this codebase, and both reasons were found by
	reading it rather than by testing it afterwards:

	1. **Only an APPROVAL needs evidence.** A portal claim waits for its
	   approver as a DRAFT - `apply_expense_claim` inserts, it does not submit -
	   and `hr_api.decide_expense` calls `submit()` for Decline exactly as it
	   does for Approve. A gate that fires on any submit would make it impossible
	   to DECLINE a claim that has no bill: the claim could never leave the
	   queue, and the person's own row would say "Waiting" for ever. Money only
	   moves on an approval, so an approval is where the evidence is needed.

	2. **Only claims created on or after the cutoff.** Surbhi, 3 November 2026,
	   on being told DTC has many claims waiting: an older draft stays fully
	   decidable, approve or decline, with no file. Without this, every claim in
	   every approver's queue on release day would have become undecidable at
	   once, and the only person who could fix one - HR, attaching the employee's
	   signed statement - would have had to do it by hand, many times over.

	With the cutoff unset nothing is exempt. That is the fail-closed direction
	and it is also simply right: a site with no cutoff is a site built from
	scratch, where there are no older claims to exempt. `after_migrate` sets it
	on the first run that finds it missing.
	"""
	if doc.get("approval_status") != "Approved":
		return

	cutoff = bill_required_from()
	if cutoff and doc.get("creation") and getdate(doc.creation) < getdate(cutoff):
		return

	if has_evidence(CLAIM, [doc.name]):
		return

	# Three sentences, in order, and the first is word for word the one the
	# driver sees. The second exists only here, because HR is the only person
	# who can attach a statement on somebody else's behalf - and a sentence only
	# one reader can act on belongs at the end of the message, not the start.
	frappe.throw(
		_msg_no_bill() + "<br>"
		+ _("Where there is no bill, attach the employee's signed statement of "
		    "what was spent and why there is no bill.") + "<br>"
		+ _("The draft is still saved. Only Submit is blocked."),
		title=_("This claim cannot be submitted yet"))


# ── reading it ───────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
@_limited(SELF_KEY, "user", limit=60)
def open_evidence(kind: str | None = None, parent: str | None = None) -> None:
	"""Stream ONE file, after asking the PARENT's own read permission.

	**POST, and the method matters.** `_limited` wraps Frappe's `rate_limit`
	with `methods=["POST"]`, and `rate_limit` skips any request whose method is
	not in that list (`frappe/rate_limiter.py:133-134`). Declared as a GET, the
	sixty-an-hour limit would never have fired at all.

	The permission is asked on the PARENT and never on a child row:
	`frappe.has_permission` on a child table answers False for everybody
	(ALV-256), so asking there would refuse the feature to its own audience.

	**The honest half, stated once and never contradicted anywhere.** This
	endpoint is defence in depth plus the access log, not a boundary. A reader
	who already holds the `/private/files/...` url can fetch it on Frappe's own
	route, where the decision is Administrator, then not private, then
	`owner == user`, then a DocShare row, then **the parent's read permission** -
	which is the same question this endpoint asks. The browser is never handed
	such a url, which is what makes that matter less; it is not the same as it
	not mattering (081-SEC-6).

	One file per call. There is no "open all": a single tap that put a person's
	whole file through eight worker slots is not something any screen here needs
	(OPS-7).
	"""
	from hrms.alvoraa_hr_core.access import refuse

	if frappe.session.user in ("Guest", ""):
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	parent_doctype = _kind_to_doctype(kind)
	parent_name = str(parent or "").strip()

	# One refusal, naming no employee and no file. The log carries the rule, the
	# endpoint, the doctype and the parent id - a reference and an actor, never
	# a value.
	if not parent_name or not frappe.db.exists(parent_doctype, parent_name):
		refuse(_("You cannot open that file."), RULE_READ,
		       "expense_evidence.open_evidence", parent_doctype, parent_name or None)
	# `frappe.has_permission` is the top-level wrapper, and its signature is NOT
	# `frappe.permissions.has_permission`'s - it takes no `print_logs`. Checked
	# in `frappe/__init__.py:600-610` after a test raised a TypeError on it.
	if not frappe.has_permission(parent_doctype, "read", doc=parent_name):
		refuse(_("You cannot open that file."), RULE_READ,
		       "expense_evidence.open_evidence", parent_doctype, parent_name)

	row = frappe.db.get_value("File", {
		"attached_to_doctype": parent_doctype,
		"attached_to_name": parent_name,
	}, ["name", "file_name"], as_dict=True)
	if not row:
		refuse(_("There is nothing attached to open."), RULE_READ,
		       "expense_evidence.open_evidence", parent_doctype, parent_name)

	f = frappe.get_doc("File", row.name)
	# `encodings=[]`, because `get_content()` with no argument tries to DECODE
	# what it read and hands back a lossy `str` for anything binary - which for
	# a photographed bill means serving a file that opens as nothing. The trace
	# is written out at `employee_photo._raw_bytes`.
	content = f.get_content(encodings=[])

	log_view(parent_doctype, parent_name)

	frappe.local.response.filename = f.file_name or "evidence"
	frappe.local.response.filecontent = content
	frappe.local.response.type = "download"
	# The parent's name and the actor. Never the file, never the url, never
	# anything about the document's contents.
	frappe.logger("alvoraa").info(
		"evidence opened: %s %s by %s" % (parent_doctype, parent_name,
		                                  frappe.session.user))


# ── who looked ───────────────────────────────────────────────────────────────

def log_view(parent_doctype: str, parent_name: str) -> None:
	"""One row per viewer per file per day, on the table that already answers
	"who looked at my face" and "who looked at my Aadhaar".

	A SIBLING of `employee_documents_read.log_document_view`, not a change to it:
	changing that function would alter document logging, which is not this
	slice's. The three narrowing rules are copied, because an access log that
	records everything is one nobody reads:

	  * only when there is something to look at;
	  * **never a person looking at their own**;
	  * one row per viewer per file per day, not one per refresh.

	It holds no file, no url and no value from the document itself.

	**The one argued `ignore_permissions` in this module.** The
	`Alvoraa Photo Access Log` DocType grants read to System Manager and
	HR Manager and `create` to nobody at all - Frappe's own pattern for a record
	the system writes about a person. `employee_documents_read` carries exactly
	one for exactly this reason. Nothing else here bypasses anything: the `File`
	insert, the bind and the deletes all go through the framework's own gate.
	"""
	user = frappe.session.user
	if user in ("Guest", "Administrator", ""):
		return
	if not frappe.db.exists("DocType", ACCESS_LOG):
		return
	try:
		employee = frappe.db.get_value(parent_doctype, parent_name, "employee")
		if not employee:
			return
		mine = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"},
		                           "name")
		if mine and mine == employee:
			# Never a person looking at their own.
			return
		if frappe.db.exists(ACCESS_LOG, {
			"employee": employee,
			"reference_name": parent_name,
			"viewed_by": user,
			"viewed_on_date": today(),
			"source": SOURCE[parent_doctype],
		}):
			return
		frappe.get_doc({
			"doctype": ACCESS_LOG,
			"employee": employee,
			"employee_name": frappe.db.get_value("Employee", employee, "employee_name"),
			"reference_name": parent_name,
			"source": SOURCE[parent_doctype],
			"viewed_by": user,
			"viewed_at": now(),
			"viewed_on_date": today(),
		}).insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		# Never let the record stop somebody doing their job. The same rule the
		# check-in photo log and the document log already follow. The message
		# names the parent and nothing else - no file name, no url.
		frappe.log_error("Could not record the evidence view on %s %s"
		                 % (parent_doctype, parent_name), "081 evidence access log")


@frappe.whitelist()
def who_opened_mine() -> dict:
	"""The caller's own answer to "who opened my bill".

	The same reasoning as `employee_documents_read.what_is_shown_about_me`: the
	person whose file it is cannot open the screen that shows it, and without
	this they have no way at all to find out. Scoped to their OWN documents, and
	it takes no argument - so there is no value a browser can post that asks
	about anybody else.

	**The second of this module's two bypasses, and it is a read, not a write.**
	`Alvoraa Photo Access Log` grants read to System Manager and HR Manager and
	nothing at all to an employee, so a plain `get_all` here would hand the
	person an empty list and call it an answer. The filter is pinned to the
	caller's own employee record and the function takes no argument, so there is
	no id a browser can post to widen it. The alternative was to deny an employee
	the answer 081-PRIV-3 promises them, or to add a query condition to the
	doctype and change what HR sees in Desk as a side effect - a wider change
	than this endpoint earns.
	"""
	me = _require_signed_in_employee()
	rows = frappe.get_all(
		ACCESS_LOG,
		filters={"employee": me.name, "source": ("in", list(SOURCE.values()))},
		fields=["viewed_by", "viewed_on_date", "source", "reference_name"],
		order_by="viewed_on_date desc", limit_page_length=200,
		ignore_permissions=True) if frappe.db.exists("DocType", ACCESS_LOG) else []
	return {"opened": [{
		"by": frappe.db.get_value("User", r.viewed_by, "full_name") or r.viewed_by,
		"on": str(r.viewed_on_date),
		"what": r.source,
		"reference": r.reference_name,
	} for r in rows]}


# ── the two numbers HR can read on demand ────────────────────────────────────

HR_ROLES = ("HR Manager", "HR User", "System Manager")


@frappe.whitelist()
def counts(days: int = 7) -> dict:
	"""Two numbers, on demand, HR only. **No dashboard, no alert, no new tool.**

	They catch the two failure modes this slice can have: the rule quietly
	stopping (an approved claim with no file, which must be 0) and the path
	half-failing (people uploading and never filing). Reuses the `joiner_counts`
	shape from slice 078 (OPS-19).
	"""
	if not set(HR_ROLES) & set(frappe.get_roles()):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	since = add_to_date(now(), days=-max(1, cint(days)))
	approved = frappe.get_all(CLAIM, filters={
		"docstatus": 1, "approval_status": "Approved",
		"creation": (">", bill_required_from() or "1900-01-01"),
	}, pluck="name", limit_page_length=0)
	with_file = has_evidence(CLAIM, approved)
	return {
		"days": cint(days),
		# The one that must be 0.
		"approved_claims_with_no_bill": len([n for n in approved if n not in with_file]),
		"orphan_uploads": frappe.db.count("File", {
			"is_private": 1,
			"attached_to_name": ("is", "not set"),
			"creation": (">", since),
		}),
	}


# ── erasing it when its time is up ───────────────────────────────────────────

def _fy_start_month() -> int:
	"""April in India, and read rather than assumed where we can.

	A financial year is the unit Companies Act s.128(5) counts in, so the clock
	cannot be "eight times 365 days". We take the month from the oldest Fiscal
	Year record this site has, and fall back to April, which is what every
	Indian tenant uses.
	"""
	rows = frappe.get_all("Fiscal Year", fields=["year_start_date"],
	                      order_by="year_start_date asc", limit=1)
	return getdate(rows[0].year_start_date).month if rows else 4


def _fy_of(date_value) -> int:
	"""The financial year a date belongs to, named by the year it STARTS in."""
	d = getdate(date_value)
	return d.year if d.month >= _fy_start_month() else d.year - 1


def erase_due_bills() -> dict:
	"""Delete a bill once the 8th financial year after its claim's has ended.

	**The clock is anchored to the claim's `posting_date`, never to
	`File.creation` and never to `modified`** (OPS-16). A `modified` clock
	restarts every time somebody ticks legal hold off and on again - the lesson
	already written into `alvoraa_joiner_submission.py`.

	The `File` row and its bytes go. **The claim, its lines and its ledger
	entries stay**: they are the record, and the voucher's statutory period is
	what has expired, not the entry's.

	**Legal hold wins, always.** An appeal, a GST proceeding or a company-law
	investigation extends the period - s.36's proviso and s.128(5)'s - and
	deleting evidence somebody has asked you to preserve is worse than keeping
	it too long.
	"""
	keep_from_fy = _fy_of(nowdate()) - BILL_YEARS
	filters: dict[str, Any] = {"posting_date": ("<", "%d-%02d-01" % (keep_from_fy, _fy_start_month()))}
	if frappe.db.has_column(CLAIM, LEGAL_HOLD):
		filters[LEGAL_HOLD] = 0
	claims = frappe.get_all(CLAIM, filters=filters, pluck="name", limit=RETAIN_LIMIT)
	deleted, failed = _delete_files_of(CLAIM, claims)
	if deleted:
		_tell_hr_the_bills_went(deleted)
	# Its OWN count. Two clocks, two counts: "did the files actually go" must
	# have an answer per pass, or the clock is a claim rather than a control.
	frappe.logger("alvoraa").info(
		"081 retention bills: considered %s deleted %s failed %s before FY %s"
		% (len(claims), deleted, failed, keep_from_fy))
	return {"considered": len(claims), "deleted": deleted, "failed": failed}


def erase_due_dayfix_files() -> dict:
	"""Delete a day-fix file six months after the person left.

	Counsel, 18 September 2026. The request itself stays - it is the attendance
	record - and only the file goes.

	**OFF until the site config says otherwise**, following
	`grooming.erase_daily`. This is the pass that deletes something a person may
	still care about, and a six-month clock applied by surprise is not something
	to switch on for a tenant without their word.
	"""
	if cint(frappe.conf.get(DAYFIX_ERASE_KEY)) != 1:
		return {"switched_on": 0}

	cutoff = add_months(getdate(nowdate()), -DAYFIX_MONTHS)
	people = frappe.get_all("Employee", filters={
		"relieving_date": ("is", "set"),
	}, fields=["name", "relieving_date"], limit_page_length=0)
	left = [p.name for p in people if getdate(p.relieving_date) < cutoff]
	if not left:
		return {"considered": 0, "deleted": 0, "failed": 0}

	filters: dict[str, Any] = {"employee": ("in", left)}
	if frappe.db.has_column(REQUEST, LEGAL_HOLD):
		filters[LEGAL_HOLD] = 0
	requests = frappe.get_all(REQUEST, filters=filters, pluck="name", limit=RETAIN_LIMIT)
	deleted, failed = _delete_files_of(REQUEST, requests)
	frappe.logger("alvoraa").info(
		"081 retention day-fix: considered %s deleted %s failed %s left before %s"
		% (len(requests), deleted, failed, cutoff))
	return {"considered": len(requests), "deleted": deleted, "failed": failed}


def sweep_orphans() -> dict:
	"""Delete private files that never got a parent.

	**Confirmed: nothing in Frappe tidies these.** No job in `frappe/hooks.py`
	`scheduler_events` deletes an unattached file, so with two calls and a
	mandatory field an abandoned claim at a petrol pump would leave a real file
	on the volume for ever. On one disk (ALV-299) rubbish is not harmless.

	Bounded per run, and **never a file younger than two hours**, so an upload in
	flight while the job runs survives it. A file that HAS a parent is never
	touched - asserted as a negative, with an attached file in the fixture.
	"""
	oldest = add_to_date(now(), hours=-ORPHAN_HOURS)
	floor = add_to_date(now(), hours=-ORPHAN_FLOOR_HOURS)
	cutoff = min(oldest, floor)
	rows = frappe.get_all("File", filters={
		"is_private": 1,
		"attached_to_name": ("is", "not set"),
		"creation": ("<", cutoff),
	}, pluck="name", limit=ORPHAN_LIMIT)
	deleted = failed = 0
	for name in rows:
		try:
			frappe.delete_doc("File", name, force=True, delete_permanently=True)
			deleted += 1
		except Exception:
			failed += 1
			frappe.log_error("Could not sweep the orphan upload %s" % name,
			                 "081 evidence housekeeping")
	frappe.db.commit()
	frappe.logger("alvoraa").info(
		"081 orphan sweep: considered %s deleted %s failed %s"
		% (len(rows), deleted, failed))
	return {"considered": len(rows), "deleted": deleted, "failed": failed}


def _delete_files_of(parent_doctype: str, names: list[str]) -> tuple[int, int]:
	"""The `File` rows of these documents, bytes included.

	`delete_permanently` is what takes the bytes as well. Without it the sites
	volume keeps the picture and only loses the row, which is the worst of both:
	the file is unreachable AND still there.

	**Terminal and permanent. There is no soft delete and no "deleted" flag
	anywhere** - counsel, 18 September 2026, on indefinite soft deletion.

	No `ignore_permissions`: these passes run from the scheduler, which runs as
	Administrator, and `File.has_permission` answers True for Administrator
	before it asks anything else. A pass somehow run by anybody else fails
	closed, which is the right way round.
	"""
	deleted = failed = 0
	for parent in names:
		try:
			for f in frappe.get_all("File", filters={
				"attached_to_doctype": parent_doctype,
				"attached_to_name": parent,
			}, pluck="name"):
				frappe.delete_doc("File", f, force=True, delete_permanently=True)
				deleted += 1
		except Exception:
			failed += 1
			# The document name, never the person and never the file.
			frappe.log_error("Could not erase the evidence on %s %s"
			                 % (parent_doctype, parent), "081 evidence retention")
	frappe.db.commit()
	return deleted, failed


def _tell_hr_the_bills_went(count: int) -> None:
	"""081-PRIV-1 clause 4, through the `Notification Log` the housekeeping jobs
	already use. **It names the count and the statute, never a person and never a
	claim's employee.** An email would be a copy we cannot erase.

	No `ignore_permissions`, because this runs from the scheduler as
	Administrator. If it ever fails, the deletion still happened and one Error
	Log line says the message did not go - the record of the deletion is the
	pass's own count line, not this.
	"""
	for user in frappe.get_all("Has Role", filters={"role": "HR Manager",
	                                                "parenttype": "User"},
	                           pluck="parent", limit_page_length=0):
		try:
			frappe.get_doc({
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"subject": _("Expense bills reached the end of their retention period"),
				"email_content": _(
					"{0} expense bill(s) were permanently erased because the "
					"eighth financial year after their claim's had ended, which "
					"is the period Companies Act 2013 s.128(5) requires. The "
					"claims and their ledger entries are untouched. A claim "
					"flagged for legal hold was skipped.").format(cint(count)),
			}).insert()
		except Exception:
			frappe.log_error("Could not tell HR that bills had been erased",
			                 "081 evidence retention")
	frappe.db.commit()


def daily() -> dict:
	"""What `hooks.py` names. Three passes, three counts, one entry in a `daily`
	list that already holds eight.

	**Each pass is caught on its own**, so one failing does not stop the other
	two: they answer different questions and the orphan sweep in particular must
	keep running on a site where a retention pass is unhappy.

	Safe to run twice in a day: every pass selects on what is still there, so a
	second run finds nothing left to do and raises nothing.
	"""
	out: dict[str, Any] = {}
	for key, fn in (("bills", erase_due_bills),
	                ("dayfix", erase_due_dayfix_files),
	                ("orphans", sweep_orphans)):
		try:
			out[key] = fn()
		except Exception:
			frappe.db.rollback()
			# A title and a key. A traceback here would carry local variables -
			# and therefore document ids - into the Scheduled Job Log.
			frappe.log_error(title="081 evidence housekeeping stopped",
			                 message="the %s pass did not finish" % key)
			out[key] = None
	return out


# ── install and migrate ──────────────────────────────────────────────────────

def after_migrate() -> None:
	"""The legal-hold flag on both documents, and the cutoff, once.

	On migrate AND on install, for the reason already written into
	`attendance_correction.after_migrate`: a site built with `bench install-app`
	never runs a migrate. Safe to run again.
	"""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	# The same field name and the same read pattern as
	# `Employee Checkin.alvoraa_legal_hold`, so one grep finds every holder.
	# Created the way `branch_scope.after_migrate` creates `alvoraa_branch` on
	# these very two doctypes. Additive and default 0, so a rollback can leave
	# them in place harmlessly.
	create_custom_fields({
		dt: [{
			"fieldname": LEGAL_HOLD,
			"label": "Legal hold",
			"fieldtype": "Check",
			"default": "0",
			"insert_after": "company",
			"description": "Stops the retention job erasing the attached "
			               "evidence. Set it while an appeal, a tax proceeding "
			               "or an investigation touching this record is live.",
		}] for dt in (CLAIM, REQUEST)
	}, ignore_validate=True)

	# Set once, never moved. On a tenant upgrading on release day this becomes
	# the release date, which is exactly what exempts the claims already waiting
	# in their approvers' queues. On a site built from scratch it becomes the
	# install date, and there are no older claims for it to exempt.
	if not bill_required_from():
		frappe.db.set_default(CUTOFF_KEY, today())
