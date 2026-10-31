"""An employee's own photograph: taking it, bounding it, and deleting it.

Slice 078, step 1. There is no non-Desk way to put a picture on
`Employee.image` today, and a frontline worker neither has nor should have
Desk - which is the whole reason nobody at any tenant has a photograph.

The order of the checks in `_decode` is the point of this module, and it is
copied from `field_app_photos.attach_photo` line for line:

  1. the length of the **string**, before anything is decoded. The other way
     round, a 200 MB payload is fully expanded in a worker's memory before we
     get to say we did not want it;
  2. base64 decode, strictly;
  3. **magic bytes** - not the file extension, not the browser's content type.
     A zip renamed `.jpg` is refused here;
  4. re-encode through Pillow to JPEG, longest edge 512, quality 82. One call
     does the resize AND the metadata strip, which matters: Frappe's own
     `strip_exif_metadata_from_uploaded_images` runs for `image/jpeg` only
     (`file.py:813-819`), so a PNG selfie keeps its GPS coordinates.

**HEIC is refused, not converted.** Pillow 12.3.0 in this image has no HEIC
reader (measured), so a HEIC file can be neither resized nor stripped - and
storing one unchanged would mean keeping an original-resolution photograph with
its location in it. Refusing is the honest answer, and most phones can be told
to hand over a JPEG.

**Writing `Employee.image`.** Through `frappe.db.set_value`, not `doc.save()`,
because the `Employee` role holds **read only** on `Employee` in ERPNext
(checked in `employee.json`: `{'read': 1, 'report': 1, 'print': 1, 'email': 1}`
and no `write`). The write is authorised by this endpoint - own Active record,
one field - not by a doctype permission, and granting the Employee role write
on the HR master to avoid saying so would be a far wider change than this slice
asked for. `set_value` does not fire `on_update`, so the upload derives the
thumbnail itself; the hook stays on `on_update` as well, so Desk, an import and
a script are all covered too.
"""

import base64
import binascii
import io

import frappe
from frappe import _
from frappe.utils import now

# Imported as a MODULE, not `from ... import THUMB_FIELD`: the cross-app import
# check in `scripts/check_app_integrity.py` resolves an `ImportFrom` against the
# functions and classes defined in the target, so importing a CONSTANT by name
# fails that gate even though Python is perfectly happy with it.
import hrms.alvoraa_org_structure.people_fields as people_fields
from alvoraa_portal.field_app_limits import SELF_KEY, _limited

EMPLOYEE = "Employee"
IMAGE_FIELD = "image"

# The 48 px copy's own `attached_to_field`. Declared beside the allow-lists
# because the chart and the table - which live in hrms - are the only two things
# that read it, and only this module ever writes it.
THUMB_FIELD = people_fields.THUMB_FIELD

# ── the numbers, and where each comes from ───────────────────────────────────

# 5 MB, matching the site-wide `max_file_size` this slice sets (OPS-24). A phone
# photograph is 3-8 MB, so this accepts the ordinary case and refuses the
# outlier. Checked against the STRING first, so the outlier costs us a length
# comparison rather than 5 MB of a worker's memory.
MAX_PHOTO_BYTES = 5 * 1024 * 1024

# Base64 costs about a third on top, plus room for a `data:` prefix.
MAX_PHOTO_B64_CHARS = int(MAX_PHOTO_BYTES * 4 / 3) + 128

# 512 px is the common profile-photo size and it is the largest this product
# ever draws: the enlargement in the mini profile is about 240 px, so 512 covers
# it on a 2x phone screen with nothing wasted. Quality 82 is the usual floor
# before a face starts showing artefacts.
#
# MEASURED, not estimated (DevOps OPS-42, 31 Oct 2026, Pillow 12.3.0): a face
# on a plain background lands at 30-60 KB, but a worst-case detailed source -
# 4000x3000 of full-colour noise, the hardest thing JPEG has to compress - comes
# out at **82 KB**. So the spec's "p95 <= 50 KB" is a good TARGET and a bad
# assertion: it would fail a build on one employee's busy photograph. The build
# ceiling is 120 KB, recorded below, and the real figure is logged on every
# upload so the target can be judged against actual faces rather than noise.
STORED_EDGE = 512
STORED_QUALITY = 82
STORED_CEILING_BYTES = 120 * 1024

# 48 px is exactly 2x the 24 px circle the chart draws, which is what a phone's
# 2x display needs to look sharp. Smaller blurs on every phone; larger is bytes
# the screen cannot use.
#
# MEASURED: **0.4-0.7 KB**, not the 2-3 KB the design estimated. So a 16-face
# first paint is about **10 KB**, not 48 KB - well under a second on slow 3G,
# and cheaper than anybody claimed. Making it costs **~4 ms** inside the
# request, which is the number that says no queue and no background job.
THUMB_EDGE = 48
THUMB_QUALITY = 80

# What an accepted picture starts with. JPEG, PNG and WEBP: all three are
# re-encoded to JPEG, so the stored artefact is identical whichever arrived and
# "a format we cannot strip" does not apply to any of them.
MAGIC = (
	b"\xff\xd8\xff",                    # JPEG
	b"\x89PNG\r\n\x1a\n",               # PNG
)


def _refused_type_message():
	# One sentence for every refused type, HEIC included. No technical words:
	# "unsupported MIME type" tells a shop assistant nothing.
	return _("We can only take a JPG or PNG picture. Most phones can take one "
	         "- try again from the camera.")


def _looks_like_an_image(blob):
	if blob.startswith(MAGIC):
		return True
	# WEBP is RIFF....WEBP - the size sits between the two markers.
	return len(blob) > 12 and blob[:4] == b"RIFF" and blob[8:12] == b"WEBP"


def _decode(photo):
	"""The posted string to raw bytes, or a refusal. Nothing is stored yet."""
	if not isinstance(photo, str) or not photo.strip():
		frappe.throw(_refused_type_message(), frappe.ValidationError)
	if len(photo) > MAX_PHOTO_B64_CHARS:
		# Before any decode. This is the line the whole ordering exists for.
		frappe.throw(_("That picture is too large. Please take a new one with "
		               "the camera rather than sending a file."),
		             frappe.ValidationError)
	try:
		raw = photo.split(",", 1)[1] if photo.startswith("data:") else photo
		blob = base64.b64decode(raw, validate=True)
	except (binascii.Error, ValueError, IndexError):
		frappe.throw(_refused_type_message(), frappe.ValidationError)
	if len(blob) > MAX_PHOTO_BYTES or not _looks_like_an_image(blob):
		frappe.throw(_refused_type_message(), frappe.ValidationError)
	return blob


def _reencode(blob, edge, quality):
	"""One Pillow call: resize to `edge` on the longest side, strip everything,
	write JPEG.

	The strip is not a separate step. A new `Image` is built from the pixels
	only, so no EXIF, no ICC profile, no GPS block and no thumbnail-in-the-file
	survives - which is the only way a PNG selfie's coordinates are removed,
	because Frappe's own strip never looks at a PNG.
	"""
	from PIL import Image

	with Image.open(io.BytesIO(blob)) as img:
		img = img.convert("RGB")
		img.thumbnail((edge, edge), Image.LANCZOS)
		out = io.BytesIO()
		# No `exif=` and no `icc_profile=`: anything not passed is not written.
		img.save(out, format="JPEG", quality=quality, optimize=True)
	return out.getvalue()


# ── storing and deleting the two files ───────────────────────────────────────

def _file_rows(employee, field):
	"""The File row names on this employee for one picture field."""
	return frappe.get_all("File", filters={
		"attached_to_doctype": EMPLOYEE,
		"attached_to_name": employee,
		"attached_to_field": field,
	}, pluck="name", ignore_permissions=True)


def _delete_rows(names, employee):
	"""Delete File rows, **bytes included**.

	`delete_permanently` is what takes the bytes as well. Without it the sites
	volume grows one orphan per re-upload for ever, which on ten replace cycles
	is twenty-one files for one person's face (OPS-15).
	"""
	for name in names or ():
		try:
			frappe.delete_doc("File", name, force=True, ignore_permissions=True,
			                  delete_permanently=True)
		except Exception:
			# Losing the old file is untidy; failing the upload over it is worse.
			frappe.log_error(f"Could not delete the old picture file {name} on "
			                 f"{employee}", "Employee photo")


def _delete_files(employee, field):
	_delete_rows(_file_rows(employee, field), employee)


def _keep_the_login_in_step(employee, url):
	"""Put the same picture on the person's User record, by value.

	**This is not a nicety. Without it, saving that Employee in Desk RAISES.**

	ERPNext's `Employee.update_user()` (`employee.py:240-251`) inserts a `File`
	carrying only a `file_url` whenever `image` has changed OR the linked
	User's `user_image` is empty. Frappe's `File.save_file` then fills
	`_content` with the DECODING `get_content()` (`file.py:795-796`) and hands
	that `str` to `strip_exif_data` at line 819, which wants bytes:
	`TypeError: a bytes-like object is required, not 'str'`.

	This endpoint writes with `db.set_value`, so `update_user()` never runs and
	`user_image` would stay empty - and then the NEXT time anybody saved that
	employee in Desk, ERPNext would see an empty `user_image`, try the insert,
	and raise. Every time. So an employee adding their own picture would have
	quietly made their own record unsaveable.

	Setting `user_image` to the same url, by value, removes the trigger: there
	is nothing for ERPNext to create. It is also simply correct - the Desk
	avatar and the portal avatar are then the same picture.

	The underlying fault is upstream and is NOT fixed here. HR uploading a
	photograph in Desk still raises, because ERPNext's own path is what calls
	`save_file`. That is an escalation, not a line of code in this slice.
	"""
	try:
		user = frappe.db.get_value(EMPLOYEE, employee, "user_id")
		if user:
			frappe.db.set_value("User", user, "user_image", url,
			                    update_modified=False)
	except Exception:
		# A picture that reached the Employee but not the User is untidy, not
		# broken. Never fail the upload over it.
		frappe.log_error(f"Could not mirror the picture onto the login for "
		                 f"{employee}", "Employee photo")


def _store(employee, field, jpeg, suffix):
	"""One private File row, and its url."""
	f = frappe.get_doc({
		"doctype": "File",
		"file_name": f"employee-{employee}-{suffix}.jpg",
		"attached_to_doctype": EMPLOYEE,
		"attached_to_name": employee,
		"attached_to_field": field,
		"is_private": 1,
		"content": jpeg,
		# A File insert is one of the two deliberate bypasses in this slice:
		# an employee holds no create permission on File, and the row is written
		# only after this endpoint has established it is their own record.
	}).insert(ignore_permissions=True)
	return f.file_url


# ── the 48 px copy ───────────────────────────────────────────────────────────

def _raw_bytes(file_url):
	"""The file's bytes, UNDECODED.

	**`File.get_content()` with no argument tries to DECODE what it read**, by
	looping over `FILE_ENCODING_OPTIONS` until one of them does not raise
	(`frappe/core/doctype/file/file.py:715-731`). On a JPEG one of them
	succeeds - lossily - and hands back a `str` with bytes changed or dropped:
	a probe showed a stored JPEG coming back with its first four bytes
	changed, so Pillow could not identify it at all.

	So `encodings=[]`. The loop body then never runs and the raw bytes come
	back untouched.

	**This was a live bug, found by running the tests rather than by reading the
	code.** With the decode in place, `derive_thumbnail` raised
	`UnidentifiedImageError` on every real photograph, was caught by its own
	"never fail an Employee save" guard, and left NO 48 px copy for anybody -
	silently, with only an Error Log row. The chart would have fallen back to
	the full 512 px picture for every face, which is the ~720 KB first paint the
	derived copy exists to avoid, and nothing would have gone red.
	"""
	return frappe.get_doc("File", {"file_url": file_url}).get_content(encodings=[])


def derive_thumbnail(employee, image_url=None):
	"""Make (or remake, or remove) the 48 px copy for one employee.

	**This can never fail an Employee save.** It catches everything, writes an
	Error Log and leaves no thumbnail - and the renderer then falls back to the
	full photograph and then to the person's initials. `Employee.on_update`
	fires on every save of every employee, payroll work included, so a
	photograph Pillow cannot read must not take an unrelated HR edit down.
	"""
	try:
		if image_url is None:
			image_url = frappe.db.get_value(EMPLOYEE, employee, IMAGE_FIELD)
		_delete_files(employee, THUMB_FIELD)
		if not image_url:
			return None
		blob = _raw_bytes(image_url)
		return _store(employee, THUMB_FIELD, _reencode(blob, THUMB_EDGE, THUMB_QUALITY), "48")
	except Exception:
		frappe.log_error(f"Could not make the 48 px copy for {employee}",
		                 "Employee photo")
		return None


def on_employee_update(doc, method=None):
	"""`Employee.on_update`, last in the chain and guarded.

	Guarded on `has_value_changed("image")`, so the four handlers that run
	before this one are untouched on an ordinary save and no Pillow call is made
	when nothing about the picture changed.

	It is on `on_update` rather than only in the portal endpoint so that EVERY
	route is covered: HR attaching a picture in Desk, a bulk import carrying an
	`image` column, a script. A portal-only derivation would mean Desk uploads
	silently had no thumbnail.

	**The two-part guard, and why the obvious one-part version is wrong.**
	`has_value_changed` returns **True whenever there is no previous document**
	(`frappe/model/document.py:699-706`), so it is True on every INSERT -
	including every Employee created while a tenant is being provisioned. DevOps
	found that (OPS §4) and suggested `has_value_changed(...) and doc.image`.
	That fixes the insert but opens a second hole: clearing a photograph in Desk
	would then skip this handler and leave the old 48 px copy behind, so the
	chart would keep drawing a face that has been removed. So: skip an INSERT
	that carries no picture, and otherwise run - `derive_thumbnail` with no url
	deletes the copy, which is exactly what clearing should do.
	"""
	try:
		if not doc.has_value_changed(IMAGE_FIELD):
			return
		if not doc.get_doc_before_save() and not doc.get(IMAGE_FIELD):
			# A new Employee with no photograph: nothing to derive, and nothing
			# of an earlier one to delete.
			return
	except Exception:
		return
	derive_thumbnail(doc.name, doc.get(IMAGE_FIELD))


# ── the endpoints ────────────────────────────────────────────────────────────

def _my_employee():
	"""The caller's own ACTIVE Employee, or None.

	Active, always. ERPNext does not disable a leaver's login, so this filter is
	the whole control that stops somebody who has left changing their record
	with a session they already had open.
	"""
	return frappe.db.get_value(
		EMPLOYEE, {"user_id": frappe.session.user, "status": "Active"},
		["name", "employee_name", IMAGE_FIELD], as_dict=True)


def _require_my_employee():
	if frappe.session.user in ("Guest", ""):
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	me = _my_employee()
	if not me:
		frappe.throw(_("This account is not linked to an employee record, so "
		               "there is no picture to change. Ask HR to link it to "
		               "this account."), frappe.PermissionError)
	return me


@frappe.whitelist(methods=["POST"])
@_limited(SELF_KEY, "user", limit=20)
def upload_my_photo(photo=None):
	"""Put a picture on the caller's OWN record. There is no employee argument.

	No employee argument is the point: there is no value a browser can post that
	makes this write somebody else's record, so "post a photograph with
	Employee B's id" has nothing to post.
	"""
	me = _require_my_employee()
	blob = _decode(photo)
	jpeg = None
	try:
		# MEASURED at ~240 ms for a 10.5 MB source (decode, resize, re-encode).
		# This is the first thing in this product to spend a quarter of a second
		# of CPU inside a user's own request, in one of 8 gunicorn slots. Fine
		# for one person adding their picture; said out loud so the next person
		# does not discover it in a flame graph. The 48 px copy that follows is
		# 4 ms, because the expensive decode has already happened here.
		jpeg = _reencode(blob, STORED_EDGE, STORED_QUALITY)
	except Exception:
		# Pillow could not read it: it is not a picture we can bound or strip.
		frappe.throw(_refused_type_message(), frappe.ValidationError)

	# The OLD rows are noted first and deleted LAST. Deleting before storing
	# would mean a store that failed had already taken away the picture the
	# employee had, which is the worst of the three possible outcomes.
	old = _file_rows(me.name, IMAGE_FIELD)
	url = _store(me.name, IMAGE_FIELD, jpeg, "photo")
	frappe.db.set_value(EMPLOYEE, me.name, IMAGE_FIELD, url)
	_keep_the_login_in_step(me.name, url)
	derive_thumbnail(me.name, url)
	_delete_rows(old, me.name)
	# Who and when, on the person's own record. Frappe writes its own Version
	# row for the field change; this is the readable half.
	try:
		frappe.get_doc(EMPLOYEE, me.name).add_comment("Info", _("Added their own picture"))
	except Exception:
		pass
	frappe.db.commit()
	# WHEN, by name: counsel asked for the upload timestamp for audit
	# (29 Oct 2026). The document name, the actor, the size and the time - and
	# nothing about the person.
	frappe.logger("alvoraa").info(
		f"employee photo: set on {me.name} by {frappe.session.user} at "
		f"{now()}, {len(jpeg)} bytes")
	return {"image": url, "bytes": len(jpeg)}


@frappe.whitelist(methods=["POST"])
@_limited(SELF_KEY, "user", limit=20)
def remove_my_photo():
	"""Take the picture off. The employee's own route out of 078-PRIV-1.

	Both files go, bytes included. Every surface falls back to initials, with no
	broken-image icon anywhere, because the field is cleared rather than left
	pointing at a file that is gone.
	"""
	me = _require_my_employee()
	_delete_files(me.name, IMAGE_FIELD)
	_delete_files(me.name, THUMB_FIELD)
	frappe.db.set_value(EMPLOYEE, me.name, IMAGE_FIELD, None)
	_keep_the_login_in_step(me.name, None)
	try:
		frappe.get_doc(EMPLOYEE, me.name).add_comment("Info", _("Removed their own picture"))
	except Exception:
		pass
	frappe.db.commit()
	frappe.logger("alvoraa").info(
		f"employee photo: removed from {me.name} by {frappe.session.user} "
		f"at {now()}")
	return {"image": None}
