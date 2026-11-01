"""078 step 1 - my picture, my details, and the two closed lists.

The three tests that matter most, said plainly, because the rest are ordinary:

  * **AC-5, and it is the only proof the strip ever gets.** A PNG carrying a
    GPS block goes in; what comes out must be a JPEG whose EXIF reads back
    EMPTY, at 512 px. Frappe's own strip runs for `image/jpeg` only, so without
    this test a PNG selfie keeps the coordinates of somebody's home and
    everything looks fine.
  * **AC-51's third case.** An off-list field name is written STRAIGHT into
    `DefaultValue`, bypassing the setter entirely, and the reader must still
    produce nothing. The setter's refusal is a courtesy; this is the control,
    and it is the only half that survives a future UI.
  * **AC-25b's guard, and the bug in the obvious version of it.**
    `has_value_changed` is True on every INSERT, so the naive guard fires a
    Pillow call for every Employee created while a tenant is provisioned.
"""

import io

import frappe
import hrms.alvoraa_org_structure.people_fields as people_fields

from alvoraa_portal import employee_photo, my_profile
from alvoraa_portal.tests import fixtures_078 as fx
from alvoraa_portal.tests.fixtures_045 import Wave4Base


class _Base(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.p = fx.people()
		fx.clear_lists()

	def tearDown(self):
		frappe.set_user("Administrator")
		fx.clear_lists()
		super().tearDown()


# ── the two closed lists ─────────────────────────────────────────────────────


class TestTheListsAreClosed(_Base):
	def test_the_ten_positions_fields_are_exactly_these(self):
		"""Pinned literally. A later slice adding an eleventh has to come here
		first, which is the point: this tuple is the whole of 078-SEC-1."""
		self.assertEqual(people_fields.POSITIONS_PROFILE_FIELDS, (
			"designation", "department", "branch", "company", "reports_to",
			"grade", "employment_type", "date_of_joining", "default_shift",
			"company_email"))
		# Ten, not eleven. "Work phone" has no field on Employee.
		self.assertEqual(len(people_fields.POSITIONS_PROFILE_FIELDS), 10)
		self.assertNotIn("work_phone", people_fields.POSITIONS_PROFILE_FIELDS)

	def test_the_six_my_profile_fields_are_exactly_these(self):
		self.assertEqual(people_fields.MY_PROFILE_WRITE_FIELDS, (
			"cell_number", "personal_email", "current_address",
			"person_to_be_contacted", "relation", "emergency_phone_number"))

	def test_pay_bank_identity_and_date_of_birth_are_denied(self):
		"""N1. Whatever is ticked, whatever the reader's permission level."""
		for field in ("ctc", "salary_mode", "bank_ac_no", "ifsc_code",
		              "pan_number", "esi_number", "provident_fund_account",
		              "date_of_birth", "marital_status", "blood_group",
		              "relieving_date", "permanent_address"):
			with self.subTest(field=field):
				self.assertTrue(people_fields.is_denied(field))
				self.assertNotIn(field, people_fields.POSITIONS_PROFILE_FIELDS)
				self.assertNotIn(field, people_fields.MY_PROFILE_WRITE_FIELDS)

	def test_an_off_list_name_is_named_back_as_off_list(self):
		self.assertEqual(
			people_fields.off_list("alvoraa_positions_profile_fields",
			                       "designation,bank_ac_no,date_of_birth"),
			("bank_ac_no", "date_of_birth"))

	def test_the_reader_intersects_again_so_a_direct_write_produces_nothing(self):
		"""**AC-51's third case - the one that matters.**

		`frappe.db.set_default` bypasses the setter, its refusal, its
		System-Manager check and its Version row. The reader has to produce
		nothing anyway, because that is the only half a future UI cannot get
		round.
		"""
		frappe.db.set_default("alvoraa_positions_profile_fields",
		                      "designation,bank_ac_no,pan_number,date_of_birth")
		frappe.db.set_default("alvoraa_my_profile_fields",
		                      "cell_number,ctc,bank_ac_no")
		frappe.db.commit()

		self.assertEqual(
			people_fields.allowed("alvoraa_positions_profile_fields",
			                      frappe.db.get_default("alvoraa_positions_profile_fields")),
			("designation",))
		self.assertEqual(my_profile._ticked(), ("cell_number",))

	def test_the_order_comes_from_the_allow_list_not_from_what_was_ticked(self):
		"""So the screen reads the same whatever order somebody ticked things."""
		self.assertEqual(
			people_fields.allowed("alvoraa_positions_profile_fields",
			                      "company_email,designation,branch"),
			("designation", "branch", "company_email"))


# ── the stored picture ───────────────────────────────────────────────────────


class TestTheStoredPicture(_Base):
	def _upload(self, blob, user=None):
		frappe.set_user(user or self.p["gps_user"])
		return employee_photo.upload_my_photo(photo=fx.as_b64(blob))

	def test_a_png_carrying_gps_is_stored_as_a_jpeg_with_no_exif_at_512px(self):
		"""**AC-5. The only proof the metadata strip ever gets.**"""
		from PIL import Image

		source = fx.png_with_gps(size=(1600, 1200))
		# The GPS really is in the source - otherwise this test passes on a
		# fixture that never carried anything.
		self.assertIn(0x8825, fx.exif_of(source))

		out = self._upload(source)
		blob = fx.file_bytes(out["image"])
		self.assertIsInstance(blob, bytes,
		                      "a stored picture must read back as BYTES - the "
		                      "default get_content() decodes it lossily")

		with Image.open(io.BytesIO(blob)) as img:
			self.assertEqual(img.format, "JPEG")
			self.assertEqual(max(img.size), employee_photo.STORED_EDGE)
		self.assertEqual(fx.exif_of(blob), {})

	def test_the_stored_file_is_private(self):
		out = self._upload(fx.plain_jpeg())
		self.assertEqual(
			frappe.db.get_value("File", {"file_url": out["image"]}, "is_private"), 1)

		# **The 48 px copy too**, and it is the one that matters most: its URL
		# is what `people_fields.thumbnails_for` hands to every chart reader,
		# with `ignore_permissions=True`. The URL being to a PRIVATE file is
		# what makes that read safe - a public one would be a face anybody
		# could fetch. Both copies come out of one `_store`, so this is a pin
		# rather than a second behaviour.
		# Read the way a chart reader's path reads it: THUMB_FIELD is not a
		# column on Employee at all, it is the File row's `attached_to_field`,
		# which is exactly what `people_fields.thumbnails_for` selects on.
		thumb = frappe.get_all("File", filters={
			"attached_to_doctype": "Employee",
			"attached_to_field": employee_photo.THUMB_FIELD,
			"attached_to_name": self.p["gps"],
		}, fields=["file_url", "is_private"], ignore_permissions=True)
		self.assertTrue(thumb, "the 48 px copy was not made")
		for row in thumb:
			self.assertEqual(row.is_private, 1,
			                 "the 48 px copy is the one whose URL every chart "
			                 "reader is handed, so it has to be private")

	def test_the_stored_size_is_inside_the_build_ceiling(self):
		"""Recorded, not asserted at 50 KB.

		DevOps measured a worst-case detailed source at **82 KB** through these
		exact parameters, so "p95 <= 50 KB" is a good target and a bad
		assertion: it fails a build on one employee's busy photograph. 120 KB is
		the ceiling; the real figure is logged on every upload (OPS-42).
		"""
		out = self._upload(fx.plain_jpeg(size=(2400, 1800)))
		self.assertLessEqual(out["bytes"], employee_photo.STORED_CEILING_BYTES)

	def test_a_zip_renamed_as_a_picture_is_refused_on_its_bytes(self):
		"""AC-9. Not on the extension, not on the browser's content type."""
		frappe.set_user(self.p["gps_user"])
		before = fx.picture_rows(self.p["gps"])
		with self.assertRaises(frappe.ValidationError):
			employee_photo.upload_my_photo(
				photo=fx.as_data_url(fx.zip_named_jpg(), "image/jpeg"))
		self.assertEqual(fx.picture_rows(self.p["gps"]), before)

	def test_a_heic_file_is_refused_in_plain_words_and_stores_nothing(self):
		"""AC-4. Pillow here cannot read HEIC, so it can be neither resized nor
		stripped, and storing it unchanged would keep a full-resolution
		photograph with its location in it."""
		# Start from nothing. Another class deliberately leaves a broken file on
		# this person, and "stores nothing" has to mean nothing was stored BY
		# THIS CALL rather than that nobody had ever stored anything.
		fx.strip_photo(self.p["no_photo"])
		frappe.set_user(self.p["no_photo_user"])
		with self.assertRaises(frappe.ValidationError) as caught:
			employee_photo.upload_my_photo(photo=fx.as_b64(fx.heic_like()))
		self.assertIn("JPG or PNG", str(caught.exception))
		self.assertFalse(frappe.db.get_value("Employee", self.p["no_photo"], "image"))
		self.assertEqual(fx.picture_rows(self.p["no_photo"]), [])

	def test_an_oversized_payload_is_refused_before_anything_is_decoded(self):
		"""The ORDER is the control. A 200 MB payload must not be expanded in a
		worker's memory before we get to say we did not want it."""
		frappe.set_user(self.p["no_photo_user"])
		huge = "A" * (employee_photo.MAX_PHOTO_B64_CHARS + 10)
		with self.assertRaises(frappe.ValidationError):
			employee_photo.upload_my_photo(photo=huge)

	def test_ten_replace_cycles_leave_exactly_two_files(self):
		"""AC-11, AC-13. Two, not twenty-one. No orphan in the sites volume."""
		for i in range(10):
			self._upload(fx.plain_jpeg(size=(600 + i * 10, 500)))
		self.assertEqual(len(fx.picture_rows(self.p["gps"])), 2)

	def test_removing_clears_the_field_and_deletes_both_files(self):
		"""AC-10. PRIV-2 is an erasure right, so the bytes go too."""
		self._upload(fx.plain_jpeg())
		self.assertTrue(frappe.db.get_value("Employee", self.p["gps"], "image"))
		employee_photo.remove_my_photo()
		self.assertFalse(frappe.db.get_value("Employee", self.p["gps"], "image"))
		self.assertEqual(fx.picture_rows(self.p["gps"]), [])

	def test_there_is_no_employee_argument_to_post(self):
		"""AC-23, and it is stronger than a check.

		A test that signs in as A and posts B's id can only prove the check it
		happens to exercise. Having **no employee parameter at all** means there
		is nothing a browser can post that reaches another person's record.
		"""
		import inspect

		for fn in (employee_photo.upload_my_photo, employee_photo.remove_my_photo,
		           my_profile.save_my_profile, my_profile.get_my_profile):
			params = set(inspect.signature(fn).parameters)
			with self.subTest(fn=fn.__name__):
				self.assertFalse(params & {"employee", "employee_id", "name", "user"})

	def test_a_leaver_with_a_live_session_is_refused(self):
		"""AC-24. ERPNext does not disable a leaver's login, so the Active
		filter on every lookup is the whole control."""
		frappe.db.set_value("Employee", self.p["no_photo"], "status", "Left")
		frappe.db.commit()
		try:
			frappe.set_user(self.p["no_photo_user"])
			with self.assertRaises(frappe.PermissionError):
				employee_photo.upload_my_photo(photo=fx.as_b64(fx.plain_jpeg()))
			# My profile answers with the designed empty state, not a failure.
			self.assertTrue(my_profile.get_my_profile().get("no_employee"))
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", self.p["no_photo"], "status", "Active")
			frappe.db.commit()


# ── the 48 px copy ───────────────────────────────────────────────────────────


class TestThe48pxCopy(_Base):
	def test_it_is_made_on_a_desk_save_too_not_only_in_the_portal(self):
		"""AC-25b. The handler is on `Employee.on_update`, so Desk, an import
		and a script are all covered. A portal-only derivation is a failure.

		Run on an employee with NO login, so it is testing THIS handler rather
		than the Frappe fault that `test_a_desk_save_for_an_employee_with_a_login`
		covers - that one needs a login to reach `update_user()` at all.
		"""
		who = fx.employee_without_a_login()
		fx.strip_photo(who)
		jpeg = employee_photo._reencode(fx.plain_jpeg(), 512, 82)
		url = employee_photo._store(who, employee_photo.IMAGE_FIELD, jpeg, "photo")
		doc = frappe.get_doc("Employee", who)
		doc.image = url
		doc.save(ignore_permissions=True)   # the Desk route
		frappe.db.commit()
		self.assertTrue(people_fields.thumbnails_for([who]))

	def test_a_desk_save_for_an_employee_with_a_login(self):
		"""The Frappe fault behind AC-25b's Desk route, asserted BOTH WAYS.

		`frappe/core/doctype/file/file.py`'s `save_file` fills
		`flags.original_content` with the DECODING `get_content()`, which for a
		jpeg returns a lossy `str`; `strip_exif_data` a few lines later wants
		bytes and raises `TypeError`. ERPNext's `Employee.update_user()` walks
		into it whenever `image` changes or the linked User's `user_image` is
		empty - so HR adding a photograph in Desk raised, in ERPNext's own
		`on_update`, before this slice's handler ever ran.

		**Surbhi's decision, 31 Oct 2026: patch it in our own image and report
		it upstream.** `scripts/patch_frappe_binary_file_content.py` does that,
		and runs in both `deploy/Dockerfile` and `ci.yml`.

		So this test asks the bench which Frappe it is running and asserts the
		matching behaviour:

		  * **patched** - the Desk route WORKS and the 48 px copy is made,
		    which is AC-25b in full;
		  * **not patched** - it raises the `TypeError`, recorded so an
		    unpatched image (an older release, or a bench somebody built by
		    hand) is described rather than silently passing.

		Written this way on purpose. A test pinned to one of the two would go
		red the day the other became true, and the reason would be invisible.
		"""
		import inspect

		from frappe.core.doctype.file.file import File

		from alvoraa_portal.tests.fixtures_078 import strip_photo

		# Detect the FIX, not our marker comment. Reading the source of the one
		# method that matters means this is also True the day upstream fixes it
		# their own way - which is the whole point of reporting it.
		patched = "encodings=[]" in inspect.getsource(File.before_insert)

		strip_photo(self.p["with_photo"])
		jpeg = employee_photo._reencode(fx.plain_jpeg(), 512, 82)
		url = employee_photo._store(self.p["with_photo"],
		                            employee_photo.IMAGE_FIELD, jpeg, "photo")
		doc = frappe.get_doc("Employee", self.p["with_photo"])
		self.assertTrue(doc.user_id, "this test needs an employee WITH a login")
		doc.image = url

		if patched:
			doc.save(ignore_permissions=True)      # the Desk route, working
			frappe.db.commit()
			self.assertTrue(
				people_fields.thumbnails_for([self.p["with_photo"]]),
				"AC-25b: with Frappe patched, a DESK save must make the 48 px copy")
		else:
			with self.assertRaises(TypeError) as caught:
				doc.save(ignore_permissions=True)
			self.assertIn("bytes-like object is required", str(caught.exception))
			frappe.db.rollback()


	def test_a_save_that_does_not_touch_the_picture_does_no_picture_work(self):
		"""The guard. `Employee.on_update` fires on every save of every
		employee, payroll work included."""
		calls = []
		real = employee_photo.derive_thumbnail
		employee_photo.derive_thumbnail = lambda *a, **k: calls.append(a)
		try:
			doc = frappe.get_doc("Employee", self.p["no_photo"])
			doc.cell_number = "+91 90000 00078"
			doc.save(ignore_permissions=True)
			frappe.db.commit()
		finally:
			employee_photo.derive_thumbnail = real
		self.assertEqual(calls, [])

	def test_a_new_employee_with_no_picture_does_no_picture_work(self):
		"""**The bug in the obvious guard.** `has_value_changed` returns True
		whenever there is no previous document, so it is True on every INSERT -
		which would fire a Pillow call for every Employee created while a
		tenant is being provisioned."""
		calls = []
		real = employee_photo.derive_thumbnail
		employee_photo.derive_thumbnail = lambda *a, **k: calls.append(a)
		try:
			fresh = own_employee_quietly("S078FreshNoPic")
		finally:
			employee_photo.derive_thumbnail = real
		self.assertTrue(fresh)
		self.assertEqual(calls, [])

	def test_the_guard_is_right_in_all_four_corners(self):
		"""**The whole truth table, because each half has its own hole.**

		`has_value_changed` is True on every INSERT (there is no previous
		document), so the one-part guard fires a Pillow call for every Employee
		created while a tenant is being provisioned. DevOps' suggested fix -
		`has_value_changed(...) and doc.image` - closes that and opens the
		opposite hole: clearing a photograph in Desk would then skip this
		handler and leave the 48 px copy behind, so the chart would keep drawing
		a face that has been removed.

		The test above proves only the first corner, which means the guard could
		be over-tightened to "return on any insert" and still pass. This asserts
		all four, so neither hole can be reopened quietly.
		"""
		class _Doc:
			name = "HR-EMP-GUARD-078"

			def __init__(self, inserting, image):
				self._inserting, self._image = inserting, image

			def has_value_changed(self, _field):
				# True on an INSERT and on a real change alike - the framework's
				# own behaviour, which is the thing being guarded against.
				return True

			def get_doc_before_save(self):
				return None if self._inserting else self

			def get(self, _field):
				return self._image

		cases = [
			(True, None, False, "a new Employee with no picture"),
			(True, "/private/files/new.jpg", True, "a new Employee arriving WITH one"),
			(False, "/private/files/set.jpg", True, "an existing picture changed"),
			(False, None, True, "a picture CLEARED in Desk - the copy must go too"),
		]
		for inserting, image, should_run, why in cases:
			calls = []
			real = employee_photo.derive_thumbnail
			employee_photo.derive_thumbnail = lambda *a, **k: calls.append(a)
			try:
				employee_photo.on_employee_update(_Doc(inserting, image))
			finally:
				employee_photo.derive_thumbnail = real
			with self.subTest(case=why):
				self.assertEqual(bool(calls), should_run, why)

	def test_a_picture_pillow_cannot_read_does_not_fail_the_save(self):
		"""AC-25a. The save succeeds, an Error Log row appears, there is no
		thumbnail, and the renderer falls back to the full photo and then to
		initials."""
		fx.strip_photo(self.p["no_photo"])
		# A `.dat` name, so Frappe does not guess `image/jpeg` and try to strip
		# EXIF from something that is not an image - that would raise inside
		# the FIXTURE and prove nothing about the handler.
		broken = frappe.get_doc({
			"doctype": "File", "file_name": "s078-broken.dat",
			"attached_to_doctype": "Employee",
			"attached_to_name": self.p["no_photo"],
			"attached_to_field": employee_photo.IMAGE_FIELD,
			"is_private": 1, "content": b"\xff\xd8\xff" + b"\x00" * 200,
		}).insert(ignore_permissions=True)
		doc = frappe.get_doc("Employee", self.p["no_photo"])
		doc.image = broken.file_url
		doc.save(ignore_permissions=True)   # must NOT raise
		frappe.db.commit()
		self.assertEqual(people_fields.thumbnails_for([self.p["no_photo"]]), {})


def own_employee_quietly(first):
	"""One more person, created the ordinary way, so the INSERT path runs."""
	from alvoraa_portal.tests.fixtures_045 import own_employee

	return own_employee(first)


# ── my details ───────────────────────────────────────────────────────────────


class TestMyDetails(_Base):
	def test_only_the_ticked_fields_are_offered(self):
		"""AC-16. The others are ABSENT - not disabled, not greyed."""
		fx.set_lists(my_profile_fields=["cell_number", "personal_email"])
		frappe.set_user(self.p["no_photo_user"])
		out = my_profile.get_my_profile()
		self.assertEqual([f["fieldname"] for f in out["fields"]],
		                 ["cell_number", "personal_email"])

	def test_nothing_ticked_still_answers(self):
		"""AC-17. The card stays and says so; the picture card is unaffected
		because the photograph is always on."""
		frappe.set_user(self.p["no_photo_user"])
		out = my_profile.get_my_profile()
		self.assertEqual(out["fields"], [])
		self.assertFalse(out.get("no_employee"))

	def test_a_save_writes_the_value_and_one_version_row_owned_by_the_employee(self):
		"""AC-15, and the Version row is also the brief's own instrumentation
		for self-edits."""
		fx.set_lists(my_profile_fields=["cell_number"])
		frappe.set_user(self.p["no_photo_user"])
		before = frappe.get_all("Version", filters={
			"ref_doctype": "Employee", "docname": self.p["no_photo"]}, pluck="name")
		my_profile.save_my_profile(values={"cell_number": "+91 98765 00078"})
		self.assertEqual(
			frappe.db.get_value("Employee", self.p["no_photo"], "cell_number"),
			"+91 98765 00078")
		rows = frappe.get_all("Version", filters={
			"ref_doctype": "Employee", "docname": self.p["no_photo"]},
			fields=["name", "owner", "data"])
		new = [r for r in rows if r.name not in before]
		self.assertEqual(len(new), 1)
		self.assertEqual(new[0].owner, self.p["no_photo_user"])
		self.assertIn("cell_number", new[0].data)

	def test_an_off_list_field_is_refused_not_quietly_dropped(self):
		"""AC-21. A save that silently ignored a field is how somebody comes to
		believe the field is editable."""
		fx.set_lists(my_profile_fields=["cell_number"])
		frappe.set_user(self.p["no_photo_user"])
		for field, value in (("designation", "Director"), ("ctc", "9900000"),
		                     ("bank_ac_no", "000111222")):
			with self.subTest(field=field):
				with self.assertRaises(frappe.PermissionError):
					my_profile.save_my_profile(values={field: value})

	def test_a_ticked_but_off_list_field_is_still_not_writable(self):
		"""The setter can be bypassed with `set_default`; the save cannot."""
		frappe.db.set_default("alvoraa_my_profile_fields", "cell_number,date_of_birth")
		frappe.db.commit()
		frappe.set_user(self.p["no_photo_user"])
		with self.assertRaises(frappe.PermissionError):
			my_profile.save_my_profile(values={"date_of_birth": "1990-01-01"})

	def test_a_login_with_no_employee_gets_the_designed_state_not_a_failure(self):
		"""AC-18. This threw a 500 on dev before this slice, on what is about
		to be every employee's main screen."""
		frappe.set_user(self.p["nobody_user"])
		out = my_profile.get_my_profile()
		self.assertTrue(out.get("no_employee"))


class TestTheLoginStaysSaveable(_Base):
	"""The upstream bug's real cost, and the two lines that remove its trigger.

	Without `_keep_the_login_in_step`, an employee who added their own picture
	through the portal would have made their OWN RECORD UNSAVEABLE: the portal
	writes with `db.set_value`, so `User.user_image` stays empty, and the next
	time anybody saved that Employee in Desk ERPNext would see an empty
	`user_image`, insert a `File` carrying only a url, and raise inside
	Frappe's EXIF strip. Every time, for ever.
	"""

	def test_the_login_gets_the_same_picture_by_value(self):
		frappe.set_user(self.p["with_photo_user"])
		out = employee_photo.upload_my_photo(photo=fx.as_b64(fx.plain_jpeg()))
		user = frappe.db.get_value("Employee", self.p["with_photo"], "user_id")
		self.assertEqual(frappe.db.get_value("User", user, "user_image"),
		                 out["image"])

	def test_and_the_employee_can_still_be_saved_afterwards(self):
		"""**The one that matters.** This is what was broken."""
		frappe.set_user(self.p["with_photo_user"])
		employee_photo.upload_my_photo(photo=fx.as_b64(fx.plain_jpeg()))
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Employee", self.p["with_photo"])
		doc.cell_number = "+91 90000 00079"
		doc.save(ignore_permissions=True)     # must NOT raise
		frappe.db.commit()
		self.assertEqual(
			frappe.db.get_value("Employee", self.p["with_photo"], "cell_number"),
			"+91 90000 00079")

	def test_removing_the_picture_clears_the_login_too(self):
		frappe.set_user(self.p["with_photo_user"])
		employee_photo.upload_my_photo(photo=fx.as_b64(fx.plain_jpeg()))
		employee_photo.remove_my_photo()
		user = frappe.db.get_value("Employee", self.p["with_photo"], "user_id")
		self.assertFalse(frappe.db.get_value("User", user, "user_image"))


class TestAPhotoNeverReachesAModel(_Base):
	"""078-PRIV-3, AC-25. A STATIC test over the real source tree.

	A directory picture must never become facial recognition at work. There is
	nothing to assert at runtime, because the point is that the code does not
	exist - so this reads the tree and proves it.

	Three greps, and each one is a different way the line gets crossed:

	  1. **A photo field inside an AI module.** `alvoraa_portal/ai_leads/` is
	     the only place in this product that talks to a model. If
	     `Employee.image` or the 48 px copy is ever named in there, somebody is
	     putting a face in a prompt.
	  2. **The two photo stores being joined.** `alvoraa_checkin_photo` is the
	     attendance selfie - evidence, kept 90 days. `Employee.image` is a
	     directory picture the employee chose. Reading one into the other, in
	     either direction, is how "is this the person who punched in" gets
	     built without anybody deciding to build it.
	  3. **A chart that downloads as an image.** A page of faces saved as a
	     file leaves the permission system behind entirely.
	"""

	@classmethod
	def _tree(cls):
		import os

		import alvoraa_portal

		root = os.path.dirname(alvoraa_portal.__file__)
		out = {}
		for base, dirs, names in os.walk(root):
			dirs[:] = [d for d in dirs
			           if d not in ("__pycache__", "node_modules", "tests")]
			for n in names:
				if n.endswith((".py", ".js", ".html")):
					path = os.path.join(base, n)
					out[os.path.relpath(path, root).replace(os.sep, "/")] = open(
						path, encoding="utf-8", errors="ignore").read()
		return out

	def test_no_photo_field_is_named_inside_an_ai_module(self):
		from alvoraa_portal import employee_photo

		fields = ("alvoraa_photo_48", "employee_photo", "Employee.image")
		for rel, text in self._tree().items():
			if not rel.startswith("ai_leads/"):
				continue
			for field in fields:
				with self.subTest(file=rel, field=field):
					self.assertNotIn(field, text,
					                 f"{rel} names {field}. A face must not reach "
					                 f"a model (078-PRIV-3)")
		# And the constant really is what the grep looked for, so a rename
		# cannot make this test pass by looking for nothing.
		self.assertEqual(employee_photo.THUMB_FIELD, "alvoraa_photo_48")

	def test_the_two_photo_stores_are_never_joined(self):
		"""The check-in selfie and the directory picture never meet."""
		import re

		both = re.compile(r"alvoraa_checkin_photo")
		for rel, text in self._tree().items():
			if not both.search(text):
				continue
			with self.subTest(file=rel):
				# A module may mention the check-in photo. It may NOT mention
				# the directory picture's own field in the same breath.
				self.assertNotIn("alvoraa_photo_48", text,
				                 f"{rel} names BOTH photo stores")
				if rel != "field_app_photos.py":
					self.assertNotRegex(
						text, r"alvoraa_checkin_photo[^\n]{0,80}\bimage\b",
						f"{rel} reads the check-in photo into an image field")

	def test_nothing_turns_the_chart_or_a_profile_into_an_image(self):
		"""A page of faces saved as a file leaves the permission system behind.

		Two separate assertions, because one broad grep over the whole tree was
		WRONG and this test caught itself being wrong: the check-in camera in
		`employee_field_app.js` legitimately calls `canvas.toBlob` to capture a
		selfie the employee is deliberately taking, which has nothing to do with
		turning a chart into a picture. Banning canvas everywhere would have
		been a rule nobody could keep.

		So: the DOM-to-image LIBRARIES are banned outright, because they have no
		legitimate use anywhere in this product; and a canvas export is banned
		in the files that draw the chart, the table and the profile.
		"""
		import re

		libs = re.compile(r"html2canvas|dom-to-image|domtoimage|html-to-image", re.I)
		export = re.compile(r"toPng|toJpeg|toBlob|toDataURL", re.I)
		chart_files = ("public/js/ess/portal.js",
		               "templates/includes/ess/parts/positions.html",
		               "templates/includes/ess/parts/drawers.html",
		               "templates/includes/ess/parts/org-settings.html")
		tree = self._tree()
		for rel, text in tree.items():
			with self.subTest(file=rel):
				self.assertNotRegex(text, libs,
				                    f"{rel} pulls in a DOM-to-image library")
		for rel in chart_files:
			self.assertIn(rel, tree, f"{rel} moved - fix this test's list")
			with self.subTest(file=rel):
				self.assertNotRegex(
					tree[rel], export,
					f"{rel} can export the chart, the table or a profile as an image")


	def test_no_matching_scoring_or_emotion_wording_exists_about_a_face(self):
		"""Not a grep for a library - a grep for the INTENTION, so a hand-rolled
		one is caught too."""
		import re

		banned = re.compile(
			r"face_match|face_recognit|facial_recognit|face_score|face_verif"
			r"|verify_face|match_face|emotion", re.I)
		for rel, text in self._tree().items():
			with self.subTest(file=rel):
				self.assertNotRegex(text, banned, f"{rel} looks like face matching")
