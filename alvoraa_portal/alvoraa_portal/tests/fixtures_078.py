"""Slice 078's fixtures - US-41, and without them nothing in this slice is observable.

**Measured before this was written: 0 of 403 employees at PP Jewellers have a
photograph, 0 of 363 on dev, and dev holds no `Employee Document` rows and no
`Employee Document Type` rows at all.** So a photo or document test run against
either site today reports "0 findings" and has proved exactly nothing. That is
lesson 1 from slice 028, and it is worse here because the numbers were already
known when this slice was specified.

Four things this file provides, and the reason each one exists:

  * **A PNG carrying GPS EXIF**, built in code. It is the ONLY way the metadata
    strip in `employee_photo._reencode` is ever proved: Frappe's own
    `strip_exif_metadata_from_uploaded_images` runs for `image/jpeg` only
    (`file.py:813-819`), so a PNG selfie keeps the coordinates of somebody's
    home. Generated rather than committed, so there is no binary in the
    repository and **no real person's photograph anywhere near a test**.
  * **Three people for photographs**: one with, one with none - so the initials
    fallback is exercised rather than assumed - and one whose picture arrives
    with the GPS block on it.
  * **Two HR users**: one HR Manager with a Branch User Permission, one with
    none. **They behave differently, and only the second is the common demo
    shape**, so testing only that one proves the easy half.
  * **Document rows with real files**, on an employee inside and outside the
    reader's scope, of a ticked and a non-ticked type.

It is layered on `fixtures_045`, which already owns a backdated company, two
branches and the role-setting helpers. Building a second company here would
have made `ensure_company()` hand every other suite a company with no holiday
list and no fiscal year, which slice 010 already paid to learn.
"""

import io

import frappe

from alvoraa_portal.tests.fixtures_045 import (
	STORE_A,
	STORE_B,
	own_branches,
	own_company,
	own_employee,
	own_user,
)

TAG = "S078"


# ── pictures, built in code ──────────────────────────────────────────────────

def plain_png(size=(900, 700), colour=(120, 40, 40)):
	"""A PNG with no metadata at all."""
	from PIL import Image

	buf = io.BytesIO()
	Image.new("RGB", size, colour).save(buf, format="PNG")
	return buf.getvalue()


def png_with_gps(size=(900, 700)):
	"""A PNG carrying a GPS block and a camera name - the fixture AC-5 needs.

	A photograph of a document, or of a person, taken at home carries the
	location of somebody's home. After `_reencode` the stored file must be a
	JPEG whose EXIF reads back EMPTY.
	"""
	from PIL import Image

	exif = Image.Exif()
	exif[0x8825] = {1: "N", 2: (28.0, 36.0, 0.0), 3: "E", 4: (77.0, 12.0, 0.0)}
	exif[0x010F] = "S078 TestPhone"
	buf = io.BytesIO()
	Image.new("RGB", size, (30, 90, 140)).save(buf, format="PNG", exif=exif.tobytes())
	return buf.getvalue()


def plain_jpeg(size=(900, 700)):
	from PIL import Image

	buf = io.BytesIO()
	Image.new("RGB", size, (200, 180, 60)).save(buf, format="JPEG", quality=90)
	return buf.getvalue()


def zip_named_jpg():
	"""A zip's magic bytes. Posted as a picture, it must be refused on the
	BYTES - not on the extension and not on the browser's content type."""
	return b"PK\x03\x04" + b"\x00" * 400


def heic_like():
	"""The shape of a HEIC file. Pillow 12.3.0 in this image cannot read HEIC
	(measured), so it can be neither resized nor stripped - which is why the
	answer is a plain refusal rather than storing it unchanged."""
	return b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00heicmif1" + b"\x00" * 400


def as_data_url(blob, mime="image/png"):
	import base64

	return "data:%s;base64,%s" % (mime, base64.b64encode(blob).decode())


def as_b64(blob):
	import base64

	return base64.b64encode(blob).decode()


# ── people ───────────────────────────────────────────────────────────────────

def people():
	"""The three for photographs, plus the two HR readers and their scopes."""
	own_company()
	own_branches()

	out = {}
	out["with_photo_user"] = own_user("s078withphoto", ("Employee",))
	out["no_photo_user"] = own_user("s078nophoto", ("Employee",))
	out["gps_user"] = own_user("s078gps", ("Employee",))

	out["with_photo"] = own_employee("S078WithPhoto", user=out["with_photo_user"],
	                                 branch=STORE_A)
	out["no_photo"] = own_employee("S078NoPhoto", user=out["no_photo_user"],
	                               branch=STORE_A)
	out["gps"] = own_employee("S078Gps", user=out["gps_user"], branch=STORE_A)

	# Somebody in the OTHER store, so "out of scope" has a real person in it.
	out["other_branch"] = own_employee("S078OtherBranch", branch=STORE_B)

	# Two HR Managers. `hr_wide` sees the whole company; `hr_store` is tied to
	# one branch by a User Permission and must not learn that STORE_B exists.
	out["hr_wide_user"] = own_user("s078hrwide", ("Employee", "HR Manager"))
	out["hr_store_user"] = own_user("s078hrstore", ("Employee", "HR Manager"))
	out["hr_wide"] = own_employee("S078HrWide", user=out["hr_wide_user"], branch=STORE_A)
	out["hr_store"] = own_employee("S078HrStore", user=out["hr_store_user"], branch=STORE_A)
	_branch_permission(out["hr_store_user"], STORE_A)

	# A caller with NO company at all, so "fails closed" has somebody to fail
	# closed on. Holds HR Manager and is permitted exactly one company that is
	# not ours, which is how `permitted_companies` comes back empty for ours.
	out["nobody_user"] = own_user("s078nobody", ("Employee", "HR Manager"))

	frappe.db.commit()
	return out


def _branch_permission(user, branch):
	if frappe.db.exists("User Permission", {"user": user, "allow": "Branch",
	                                        "for_value": branch}):
		return
	frappe.get_doc({
		"doctype": "User Permission",
		"user": user,
		"allow": "Branch",
		"for_value": branch,
		# Narrow on purpose. A Branch permission with `apply_to_all_doctypes`
		# RESTRICTS every doctype carrying a branch link, which is not what a
		# store's HR person needs (the DTC pattern, 26 Oct 2026).
		"apply_to_all_doctypes": 1,
	}).insert(ignore_permissions=True)
	frappe.db.commit()


# ── the settings keys ────────────────────────────────────────────────────────

def set_lists(profile_fields=None, document_types=None, my_profile_fields=None):
	"""Write the ticked lists straight into `DefaultValue`.

	Straight in, deliberately: a test that goes through the setter proves the
	setter. The reader has to be proved separately, because the setter is the
	half a future UI can bypass and the reader is the half that cannot be.
	"""
	for key, value in (
			("alvoraa_positions_profile_fields", profile_fields),
			("alvoraa_positions_document_types", document_types),
			("alvoraa_my_profile_fields", my_profile_fields)):
		if value is None:
			continue
		frappe.db.set_default(key, ",".join(value) if isinstance(value, (list, tuple)) else value)
	frappe.db.commit()


def clear_lists():
	for key in ("alvoraa_positions_profile_fields", "alvoraa_positions_document_types",
	            "alvoraa_my_profile_fields", "alvoraa_joiner_retention_days"):
		frappe.db.set_default(key, "")
	frappe.db.commit()


# ── photographs on a record ──────────────────────────────────────────────────

def give_photo(employee, blob=None):
	"""Put a stored picture on somebody, the way the endpoint would.

	Used where the test is about READING a face rather than about uploading
	one - the chart, the table, the drawer.
	"""
	from alvoraa_portal import employee_photo

	jpeg = employee_photo._reencode(blob or plain_jpeg(),
	                                employee_photo.STORED_EDGE,
	                                employee_photo.STORED_QUALITY)
	employee_photo._delete_files(employee, employee_photo.IMAGE_FIELD)
	url = employee_photo._store(employee, employee_photo.IMAGE_FIELD, jpeg, "photo")
	frappe.db.set_value("Employee", employee, employee_photo.IMAGE_FIELD, url)
	employee_photo.derive_thumbnail(employee, url)
	frappe.db.commit()
	return url


def strip_photo(employee):
	from alvoraa_portal import employee_photo

	employee_photo._delete_files(employee, employee_photo.IMAGE_FIELD)
	employee_photo._delete_files(employee, employee_photo.THUMB_FIELD)
	frappe.db.set_value("Employee", employee, employee_photo.IMAGE_FIELD, None)
	frappe.db.commit()


def exif_of(blob):
	"""What EXIF a stored file still carries. Empty is the answer we want."""
	from PIL import Image

	with Image.open(io.BytesIO(blob)) as img:
		ex = img.getexif()
		return dict(ex or {})


def file_bytes(url):
	return frappe.get_doc("File", {"file_url": url}).get_content()


def picture_rows(employee):
	"""Every File row holding one person's picture, both sizes."""
	from alvoraa_portal import employee_photo

	return frappe.get_all("File", filters={
		"attached_to_doctype": "Employee",
		"attached_to_name": employee,
		"attached_to_field": ("in", [employee_photo.IMAGE_FIELD,
		                             employee_photo.THUMB_FIELD]),
	}, pluck="name", ignore_permissions=True)


# ── documents, with real files ───────────────────────────────────────────────
#
# AC-136, and it is the fixture without which every document control in this
# slice passes against nothing: **dev holds no `Employee Document` rows and no
# `Employee Document Type` rows at all**, so a document test there today
# reports "0 findings" and has proved exactly nothing.
#
# Four rows: a TICKED and a NON-TICKED type, on an employee INSIDE the reader's
# scope and on one OUTSIDE it. The ticked/non-ticked pair is what proves the
# list is a control rather than decoration; the inside/outside pair is what
# proves the scope check runs first.
#
# Made as fixtures, with invented content. **Never a real person's scan.**

TICKED_TYPE = "S078 Ticked Identity Paper"
UNTICKED_TYPE = "S078 Unticked Paper"


def document_types():
	"""Two types: one in a sensitive category, one not."""
	for name, category in ((TICKED_TYPE, "Identity"), (UNTICKED_TYPE, "Education")):
		if frappe.db.exists("Employee Document Type", name):
			continue
		frappe.get_doc({
			"doctype": "Employee Document Type",
			"document_type_name": name,
			"category": category,
			"collect_from": "HR",
		}).insert(ignore_permissions=True)
	frappe.db.commit()
	return TICKED_TYPE, UNTICKED_TYPE


def give_documents(employee):
	"""One row of each type on this employee, each with a real file.

	Returns {type: row name}. The file content is invented text, which is the
	point: a test that needs a real scan is a test nobody should write.
	"""
	document_types()
	emp = frappe.get_doc("Employee", employee)
	out = {}
	have = {d.document_type: d for d in (emp.get("employee_documents") or [])}
	for kind in (TICKED_TYPE, UNTICKED_TYPE):
		if kind in have and have[kind].attachment:
			out[kind] = have[kind].name
			continue
		row = emp.append("employee_documents", {"document_type": kind, "status": "Received"})
		emp.save(ignore_permissions=True)
		f = frappe.get_doc({
			"doctype": "File",
			"file_name": f"s078-{kind.replace(' ', '-')}-{employee}.pdf",
			"attached_to_doctype": "Employee",
			"attached_to_name": employee,
			"is_private": 1,
			"content": b"%PDF-1.4\nS078 invented document, not a real person's.\n",
		}).insert(ignore_permissions=True)
		frappe.db.set_value("Employee Document", row.name, "attachment", f.file_url)
		out[kind] = row.name
	frappe.db.commit()
	return out


def document_views(employee=None):
	"""Rows in the access log for document views. A count, for the tests."""
	filters = {"source": "Employee document"}
	if employee:
		filters["employee"] = employee
	return frappe.get_all("Alvoraa Photo Access Log", filters=filters,
	                      fields=["name", "employee", "document_type", "viewed_by",
	                              "viewed_on_date"], limit_page_length=0,
	                      ignore_permissions=True)
