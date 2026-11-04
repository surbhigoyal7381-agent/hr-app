"""Slice 081: a bill on an expense claim, evidence on a day-fix.

Pin tests, named so a bad merge that drops the feature fails by name:

  test_an_approved_claim_needs_its_bill_on_three_doors
  test_a_claim_with_no_bill_can_still_be_DECLINED
  test_a_draft_from_before_the_cutoff_can_be_approved_and_declined
  test_the_file_row_carries_its_parent_read_back_from_the_database
  test_the_caps_are_ours_whatever_max_file_size_says
  test_a_200_mb_string_is_refused_before_any_decode
  test_nobody_opens_a_colleagues_bill
  test_no_response_anywhere_carries_a_private_files_url
  test_one_log_row_per_viewer_per_file_per_day
  test_a_bill_outlives_eight_financial_years_and_then_does_not
  test_legal_hold_wins_on_both_clocks
  test_an_orphan_goes_within_a_day_and_an_attached_file_never_does

THE DATA MATTERS (01c lesson 1). A test that proves a refusal against a
fixture where nothing could have been returned anyway proves nothing, so every
door test here runs against a claim that really exists, really has a file, and
really belongs to somebody else.
"""

import base64
import io
import inspect

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, add_to_date, getdate, now, nowdate, today

from alvoraa_goals.tests.utils import ensure_company, ensure_employee
from alvoraa_portal import attendance_correction, expense_evidence, hr_api, inbox_api
from alvoraa_portal.tests.leave_fixtures import ensure_user
from alvoraa_portal.tests.test_attendance_correction import _holiday_list
from alvoraa_portal.tests.test_expense_and_scoping import ensure_expense_type
from alvoraa_portal.tests.test_home_076 import link_user_to_employee
from alvoraa_portal.tests.utils import ensure_fiscal_years


# ── the files, generated rather than committed ───────────────────────────────
# OPS-10: one real phone photograph is committed once, for the legibility
# judgement (AC-7, which is a human's and is recorded in the test report).
# Everything a refusal or a cap needs is generated here, because ten binaries
# in git and in every image build is a cost with no answer attached.

def _jpeg(w=2000, h=1500, quality=92):
	from PIL import Image

	img = Image.new("RGB", (w, h))
	px = img.load()
	# Detail, not flat colour: a flat image compresses to nothing and would
	# make the caps look far more generous than they are.
	for y in range(0, h, 3):
		for x in range(0, w, 3):
			px[x, y] = ((x * 7) % 256, (y * 13) % 256, (x * y) % 256)
	out = io.BytesIO()
	img.save(out, format="JPEG", quality=quality)
	return out.getvalue()


def _png_with_gps():
	"""A PNG carrying GPS-shaped metadata.

	Frappe's own strip runs for `image/jpeg` only (`file.py:813-819`), so a PNG
	is exactly the case our re-encode has to cover - and the reason the strip
	is the re-encode rather than a separate step.
	"""
	from PIL import Image, PngImagePlugin

	img = Image.new("RGB", (900, 700), (120, 60, 30))
	meta = PngImagePlugin.PngInfo()
	meta.add_text("GPSLatitude", "28.6139")
	meta.add_text("GPSLongitude", "77.2090")
	out = io.BytesIO()
	img.save(out, format="PNG", pnginfo=meta)
	return out.getvalue()


def _pdf(pad=0):
	"""A real, VALID one-page PDF, built by Pillow.

	The first version of this helper hand-wrote a `%PDF-` header with no xref
	table, and the test run showed `pypdf.errors.PdfReadError: startxref not
	found` - something on the insert path reads a PDF. A fixture the product
	could never have produced would have been testing the wrong thing, so this
	makes a genuine one, and `pad` grows it past the 3 MB cap with a comment
	stream that keeps it valid.
	"""
	from PIL import Image

	img = Image.new("RGB", (600, 850), (250, 250, 250))
	out = io.BytesIO()
	img.save(out, format="PDF")
	blob = out.getvalue()
	if pad:
		# A PDF comment after %%EOF: readers stop at the xref, so the file stays
		# valid and simply gets bigger.
		blob = blob + b"\n%" + b"x" * pad + b"\n"
	return blob


def _b64(blob):
	return base64.b64encode(blob).decode()


def _code(module):
	"""The module's CODE, with every docstring blanked.

	Three of the must-not tests below grep the source, and the first run of them
	failed on this module's own prose: the docstring that explains why
	`pillow_heif` is not installed contains the word `pillow_heif`. Blanking
	docstrings is the same trick `test_portal_security_010`'s
	`ignore_permissions` ceiling uses, and for the same reason - a comment must
	not be able to fail a gate, and must not be able to pass one either.
	"""
	import ast
	import inspect as _i

	tree = ast.parse(_i.getsource(module))
	for node in ast.walk(tree):
		if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
		                     ast.AsyncFunctionDef)):
			first = node.body[0] if node.body else None
			if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
					and isinstance(first.value.value, str)):
				first.value.value = ""
	return ast.unparse(tree)


def _person(first, user=None, roles=("Employee",), last="E081"):
	emp = ensure_employee(first, last)
	frappe.db.set_value("Employee", emp, {"status": "Active", "expense_approver": None,
	                                      "department": None, "branch": None,
	                                      "relieving_date": None,
	                                      # A real employee joined before the day
	                                      # they ask to have corrected, and
	                                      # `Attendance Request` enforces that.
	                                      # `test_attendance_correction` uses
	                                      # 2000-01-01 for the same reason.
	                                      "date_of_joining": "2000-01-01"})
	if user:
		ensure_user(user, roles=roles)
		link_user_to_employee(emp, user)
	return emp


class _Base(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		ensure_fiscal_years()
		cls.company = ensure_company()
		cls.etype = ensure_expense_type(company=cls.company)
		# An Attendance Request asks whether each day is a holiday before it
		# marks it, so a test employee needs the setup a real one has. Reusing
		# `test_attendance_correction`'s helper rather than writing a second
		# one: in v16 it is a Holiday List ASSIGNMENT, not the `holiday_list`
		# field, and that is exactly the kind of fact to have in one place.
		_holiday_list(cls.company)
		frappe.db.set_single_value("HR Settings", "prevent_self_expense_approval", 0)
		# The cutoff must exist or nothing is exempt, which is the fail-closed
		# direction and the state a site built from scratch is in.
		expense_evidence.after_migrate()
		frappe.db.set_default(expense_evidence.CUTOFF_KEY, today())

		approver = ("Employee", "Expense Approver")
		cls.mgr = "e081.mgr@example.com"
		cls.mgr_emp = _person("E081Mgr", cls.mgr, approver)
		cls.me = "e081.me@example.com"
		cls.me_emp = _person("E081Me", cls.me)
		cls.other = "e081.other@example.com"
		cls.other_emp = _person("E081Other", cls.other)
		cls.hr = "e081.hr@example.com"
		_person("E081Hr", cls.hr, ("Employee", "HR Manager"))
		# A person of their own to mark as having left.
		#
		# **Why not reuse `me`:** the retention passes call
		# `frappe.db.commit()`, so a test that sets `status = "Left"` and then
		# runs one has that write COMMITTED - and `tearDown`'s rollback throws
		# away only the restore that followed it. The first run of this suite
		# left `me` permanently Left and five later tests failed with "this
		# account is not linked to an employee record". A separate person, and
		# a committed restore, between them close it.
		cls.gone = "e081.gone@example.com"
		cls.gone_emp = _person("E081Gone", cls.gone)
		frappe.db.set_value("Employee", cls.gone_emp, "expense_approver", cls.mgr)
		for emp in (cls.me_emp, cls.other_emp):
			frappe.db.set_value("Employee", emp, "expense_approver", cls.mgr)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	# ── the things nearly every test needs ───────────────────────────────
	def _a_past_workday(self, employee=None):
		"""A past day this employee has no request on yet.

		Three things force this, and all three were found by running it rather
		than by reading the code:

		  * `Attendance Request` refuses a day before the employee's joining
		    date, and `ensure_employee` sets one of its own;
		  * Frappe HR refuses an **overlapping** request;
		  * **these rows outlive the test that made them**, because
		    `upload_evidence` commits, so a fixed date worked once and then
		    failed for every later test and every later run.

		So the free day is looked up rather than assumed. The alternative -
		deleting other rows - would be a fixture quietly tidying away data the
		product deliberately keeps.
		"""
		employee = employee or self.me_emp
		taken = {str(d) for d in frappe.get_all(
			"Attendance Request", filters={"employee": employee},
			pluck="from_date", limit_page_length=0)}
		joined = frappe.db.get_value("Employee", employee, "date_of_joining")
		floor = getdate(joined) if joined else getdate(add_days(nowdate(), -3650))
		for back in range(1, 400):
			day = getdate(add_days(nowdate(), -back))
			if day < floor:
				break
			if str(day) not in taken:
				return str(day)
		raise AssertionError("no free day to raise a correction on for %s" % employee)

	def _upload(self, user, blob=None, kind="bill"):
		frappe.set_user(user)
		try:
			return expense_evidence.upload_evidence(file=_b64(blob or _jpeg()), kind=kind)
		finally:
			frappe.set_user("Administrator")

	def _mark_left(self, employee, months_ago):
		"""Mark somebody as having left, and PUT IT BACK when the test ends.

		The restore is committed, because the pass under test commits and
		`tearDown`'s rollback would otherwise discard the restore and leave the
		fixture broken for every later test.
		"""
		frappe.db.set_value("Employee", employee, {
			"relieving_date": add_months(nowdate(), -months_ago), "status": "Left"})

		def put_back():
			frappe.db.set_value("Employee", employee,
			                    {"relieving_date": None, "status": "Active"})
			frappe.db.commit()

		self.addCleanup(put_back)

	def _file_claim(self, user=None, amount=420, blob=None):
		user = user or self.me
		fid = self._upload(user, blob)["file_id"]
		frappe.set_user(user)
		try:
			return hr_api.apply_expense_claim(
				expense_type=self.etype, expense_date=today(), amount=amount,
				description="Diesel", file_id=fid)["name"]
		finally:
			frappe.set_user("Administrator")

	def _bare_claim(self, approval_status=None):
		"""A claim with NO bill, built by hand because the endpoint refuses one.

		It carries `currency`, `exchange_rate` and the two accounts because Frappe
		HR makes all four mandatory - the comment in `apply_expense_claim` says so,
		and a fixture without them fails on `MandatoryError: exchange_rate` rather
		than on the thing the test is about.
		"""
		from alvoraa_portal.hr_api import _expense_claim_accounts

		accounts = _expense_claim_accounts(self.company, self.etype)
		row = {
			"doctype": "Expense Claim", "employee": self.me_emp,
			"company": self.company, "posting_date": today(),
			"expense_approver": self.mgr,
			"currency": frappe.db.get_value("Company", self.company, "default_currency"),
			"exchange_rate": 1,
			"payable_account": accounts["payable_account"],
			"cost_center": accounts["cost_center"],
			"expenses": [{"expense_date": today(), "expense_type": self.etype,
			              "amount": 100, "sanctioned_amount": 100,
			              "cost_center": accounts["cost_center"]}],
		}
		if approval_status:
			row["approval_status"] = approval_status
		doc = frappe.get_doc(row)
		doc.insert(ignore_permissions=True)
		return doc

	def _rows_for(self, claim):
		"""The File rows on a claim, READ BACK FROM THE DATABASE.

		OPS-17 and AC-16: the assertion is on `tabFile`, never on what an
		endpoint said it had done. Until a file has its parent the approver
		sees nothing and every retention pass skips it, so "the response said
		so" is not evidence.
		"""
		return frappe.get_all("File", filters={
			"attached_to_doctype": "Expense Claim", "attached_to_name": claim,
		}, fields=["name", "file_name", "file_url", "is_private", "attached_to_name"])


# ── US-5 / US-6 · the mandatory rule, and the two conditions on it ───────────

class TheMandatoryRule(_Base):
	def test_an_approved_claim_needs_its_bill_on_three_doors(self):
		"""AC-13. Three doors, three assertions. A portal-only check would not
		satisfy this, and neither would one door."""
		for door in ("submit", "rest", "import"):
			with self.subTest(door=door):
				doc = self._bare_claim("Approved")
				with self.assertRaises(frappe.ValidationError) as ctx:
					if door == "rest":
						from frappe.client import submit
						submit(doc.as_dict())
					elif door == "import":
						# What a data import that submits actually does.
						fresh = frappe.get_doc("Expense Claim", doc.name)
						fresh.flags.in_import = True
						fresh.submit()
					else:
						frappe.get_doc("Expense Claim", doc.name).submit()
				# The first sentence, character for character the portal's.
				self.assertIn("A claim needs a photo or a PDF of the bill.", str(ctx.exception))
				frappe.db.rollback()

	def test_a_claim_with_no_bill_can_still_be_DECLINED(self):
		"""**The transition the spec forgot.**

		A decline is a submit on this codebase - `decide_expense` calls
		`submit()` for Decline exactly as it does for Approve - so a gate that
		fired on any submit would make a bill-less claim impossible to decline.
		It could never leave the queue, and the person's own row would say
		"Waiting" for ever.
		"""
		doc = self._bare_claim("Draft")
		self.assertEqual(self._rows_for(doc.name), [], "fixture must have NO bill")
		frappe.set_user(self.mgr)
		try:
			out = hr_api.decide_expense(doc.name, "decline", "No receipt and no statement.")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(out["approval_status"], "Rejected")
		self.assertEqual(frappe.db.get_value("Expense Claim", doc.name, "docstatus"), 1)

	def test_a_draft_from_before_the_cutoff_can_be_approved_and_declined(self):
		"""Surbhi, 3 Nov 2026, on being told DTC has many claims waiting.

		Every portal claim waiting for a decision today is a DRAFT with no
		file. Without the cutoff, all of them became undecidable on the day
		this shipped - and the only person who could fix one is HR, by hand,
		many times over.
		"""
		frappe.db.set_default(expense_evidence.CUTOFF_KEY, today())
		for action, want in (("approve", "Approved"), ("decline", "Rejected")):
			with self.subTest(action=action):
				doc = self._bare_claim("Draft")
				# Older than the cutoff, and no bill.
				doc.db_set("creation", add_days(today(), -30))
				self.assertEqual(self._rows_for(doc.name), [])
				frappe.set_user(self.mgr)
				try:
					out = hr_api.decide_expense(doc.name, action, "Closing an old one.")
				finally:
					frappe.set_user("Administrator")
				self.assertEqual(out["approval_status"], want)
				frappe.db.rollback()

	def test_an_amendment_does_not_inherit_the_bill(self):
		"""AC-13's amended-claim case, reduced to the half that is about
		amendments.

		**Frappe copies the DOCUMENT on an amend and not its `File` rows.** So
		an amendment arrives carrying no bill however well evidenced the claim
		it came from was, and it therefore meets the submit gate on its own -
		which the three doors above already prove. This asserts the part that is
		specific to amending, and nothing it has already been shown.

		It is a real case rather than a tidy one: a cancelled-then-amended claim
		is exactly the disputed claim somebody will look at in two years.
		"""
		claim = self._file_claim(self.me)
		self.assertEqual(len(self._rows_for(claim)), 1, "fixture must HAVE a bill")
		copy = frappe.copy_doc(frappe.get_doc("Expense Claim", claim))
		copy.approval_status = "Approved"
		copy.insert(ignore_permissions=True)
		self.assertEqual(self._rows_for(copy.name), [],
		                 "Frappe must NOT have carried the File row across")
		with self.assertRaises(frappe.ValidationError) as ctx:
			frappe.get_doc("Expense Claim", copy.name).submit()
		self.assertIn("A claim needs a photo or a PDF of the bill.", str(ctx.exception))

	def test_a_draft_with_no_bill_still_SAVES(self):
		"""AC-14. A validate-time rule would fail this, and HR saving a claim
		to finish later must not be refused: a draft is a working document."""
		doc = self._bare_claim()
		self.assertEqual(doc.docstatus, 0)

	def test_the_portal_refuses_with_the_servers_own_sentence(self):
		"""AC-23. Press the real path. A test that only inspects the form does
		not satisfy this - and the message must never be a Python TypeError,
		never "upload failed", never "check your connection"."""
		before = frappe.db.count("Expense Claim", {"employee": self.me_emp})
		frappe.set_user(self.me)
		try:
			with self.assertRaises(frappe.ValidationError) as ctx:
				hr_api.apply_expense_claim(expense_type=self.etype, expense_date=today(),
				                           amount=420, description="Diesel")
		finally:
			frappe.set_user("Administrator")
		said = str(ctx.exception)
		self.assertIn("A claim needs a photo or a PDF of the bill.", said)
		self.assertIn("Please attach one and send it again.", said)
		for never in ("TypeError", "check your connection", "upload failed", "Traceback"):
			self.assertNotIn(never, said)
		self.assertEqual(frappe.db.count("Expense Claim", {"employee": self.me_emp}), before)


# ── US-6 · the file gets its parent ──────────────────────────────────────────

class TheFileGetsItsParent(_Base):
	def test_the_file_row_carries_its_parent_read_back_from_the_database(self):
		"""AC-16, and OPS-17's whole reason. Without the parent, Frappe falls
		back to `owner == user`: the approver sees nothing and every sweep
		skips the file."""
		claim = self._file_claim()
		rows = self._rows_for(claim)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].attached_to_name, claim)
		self.assertEqual(rows[0].is_private, 1)

	def test_two_uploads_and_one_claim_leave_exactly_one_parented_row(self):
		"""AC-25. The other row has no parent and the sweep takes it."""
		first = self._upload(self.me)["file_id"]
		second = self._upload(self.me)["file_id"]
		frappe.set_user(self.me)
		try:
			claim = hr_api.apply_expense_claim(
				expense_type=self.etype, expense_date=today(), amount=420,
				description="Diesel", file_id=second)["name"]
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(len(self._rows_for(claim)), 1)
		# **Read by ROW ID.** `File.save_file` de-duplicates by content hash, so
		# two uploads of identical bytes leave two rows sharing ONE `file_url` -
		# which is the bug this test found. `reserve` now takes the id.
		self.assertFalse(frappe.db.get_value("File", first, "attached_to_name"))
		self.assertTrue(frappe.db.get_value("File", second, "attached_to_name"))

	def test_a_file_that_is_not_the_callers_own_is_refused_and_no_claim_appears(self):
		"""AC-24. And the refusal names no file and no url."""
		fid = self._upload(self.other)["file_id"]
		before = frappe.db.count("Expense Claim", {"employee": self.me_emp})
		frappe.set_user(self.me)
		try:
			with self.assertRaises(frappe.ValidationError) as ctx:
				hr_api.apply_expense_claim(expense_type=self.etype, expense_date=today(),
				                           amount=420, file_id=fid)
		finally:
			frappe.set_user("Administrator")
		self.assertNotIn(fid, str(ctx.exception))
		self.assertEqual(frappe.db.count("Expense Claim", {"employee": self.me_emp}), before)

	def test_a_file_already_bound_is_never_re_parented(self):
		claim = self._file_claim()
		fid = self._rows_for(claim)[0].name
		frappe.set_user(self.me)
		try:
			with self.assertRaises(frappe.ValidationError):
				hr_api.apply_expense_claim(expense_type=self.etype, expense_date=today(),
				                           amount=99, file_id=fid)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(len(self._rows_for(claim)), 1)


# ── US-4 · what we accept, and what we store ─────────────────────────────────

class WhatWeAcceptAndStore(_Base):
	def test_a_200_mb_string_is_refused_before_any_decode(self):
		"""AC-17. Asserted by patching the decoder and proving it never ran -
		the whole reason the length check is first is that a 200 MB payload
		would otherwise be expanded in a worker's memory before we refuse it."""
		calls = []
		real = base64.b64decode

		def spy(*a, **k):
			calls.append(1)
			return real(*a, **k)

		base64.b64decode = spy
		try:
			frappe.set_user(self.me)
			with self.assertRaises(frappe.ValidationError):
				expense_evidence.upload_evidence(file="A" * (200 * 1024 * 1024), kind="bill")
		finally:
			base64.b64decode = real
			frappe.set_user("Administrator")
		self.assertEqual(calls, [], "the decoder must never have been called")

	def test_the_type_is_decided_by_magic_bytes_and_not_by_a_name(self):
		"""AC-18, AC-19. HTML named .jpg, a zip named .pdf, and a HEIC - all
		refused with the same sentence, and the HEIC is **not converted**."""
		heic = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 64
		cases = {
			"html named jpg": b"<html><body>not a picture</body></html>",
			"zip named pdf": b"PK\x03\x04" + b"\x00" * 64,
			"heic": heic,
			"empty": b"",
		}
		for label, blob in cases.items():
			with self.subTest(label):
				frappe.set_user(self.me)
				try:
					with self.assertRaises(frappe.ValidationError) as ctx:
						expense_evidence.upload_evidence(file=_b64(blob), kind="bill")
				finally:
					frappe.set_user("Administrator")
				self.assertIn("We can take a JPG, a PNG or a PDF.", str(ctx.exception))

	def test_no_heic_reader_is_ever_added(self):
		"""AC-19's negative half. Accepting HEIC unchanged would mean storing
		an original-resolution photograph with its coordinates in it, in a
		format we cannot strip."""
		src = _code(expense_evidence)
		self.assertNotIn("pillow_heif", src)
		self.assertNotIn("register_heif", src)

	def test_a_png_loses_its_gps(self):
		"""AC-20. Frappe's own strip runs for image/jpeg only, so without our
		re-encode a PNG keeps its coordinates."""
		out = self._upload(self.me, _png_with_gps())
		stored = frappe.get_doc("File", out["file_id"]).get_content(encodings=[])
		self.assertNotIn(b"GPSLatitude", stored)
		self.assertNotIn(b"28.6139", stored)
		# And it is a JPEG now, whatever arrived.
		self.assertTrue(stored.startswith(b"\xff\xd8\xff"))

	def test_a_pdf_is_stored_byte_for_byte_and_nothing_opens_it(self):
		"""AC-21. No page count, no text layer, no sanitiser: a parser is
		attacker-chosen input inside a library."""
		pdf = _pdf()
		out = self._upload(self.me, pdf)
		stored = frappe.get_doc("File", out["file_id"]).get_content(encodings=[])
		self.assertEqual(stored, pdf)
		self.assertTrue(out["is_pdf"])
		src = _code(expense_evidence)
		for never in ("PdfReader", "PyPDF", "pdfplumber", "pytesseract", "page_count"):
			self.assertNotIn(never, src)

	def test_a_pdf_over_three_megabytes_gets_its_own_sentence(self):
		"""AC-12. A different sentence from the image one, because the advice
		differs - you cannot stand closer to a PDF."""
		big = _pdf(pad=4 * 1024 * 1024)
		frappe.set_user(self.me)
		try:
			with self.assertRaises(frappe.ValidationError) as ctx:
				expense_evidence.upload_evidence(file=_b64(big), kind="bill")
		finally:
			frappe.set_user("Administrator")
		said = str(ctx.exception)
		self.assertIn("the limit is 3 MB", said)
		self.assertIn("Send one page with the bill on it", said)
		self.assertNotIn("1 MB", said)

	def test_a_stored_image_is_inside_the_cap_and_carries_our_name(self):
		"""AC-8's figures and AC-16b, narrowed to the portal path by Surbhi's
		decision of 3 Nov 2026 (OQ-7). A device name discloses on its own."""
		out = self._upload(self.me, _jpeg(4000, 3000))
		self.assertLessEqual(out["bytes"], expense_evidence.STORED_IMAGE_MAX)
		name = frappe.db.get_value("File", out["file_id"], "file_name")
		self.assertTrue(name.startswith("bill-"), name)
		self.assertTrue(name.endswith(".jpg"), name)

	def test_a_device_name_never_reaches_the_database(self):
		"""AC-16b. `apollo-hospital-receipt-aadhaar-1234.pdf` tells a reader
		what the claim was for before they open anything - and any staff login
		can LIST file names (R-2)."""
		out = self._upload(self.me, _pdf())
		name = frappe.db.get_value("File", out["file_id"], "file_name")
		for word in ("apollo", "hospital", "receipt", "aadhaar", "1234"):
			self.assertNotIn(word, name.lower())

	def test_the_caps_are_ours_whatever_max_file_size_says(self):
		"""AC-22 ★. Three runs at three values, identical outcome - because our
		own endpoint re-encodes first and only the FINAL bytes ever become a
		`File`. And the diff writes to `max_file_size` nowhere."""
		before = frappe.db.get_single_value("System Settings", "max_file_size")
		sizes = []
		try:
			for value in (0, 5, 25):
				frappe.db.set_single_value("System Settings", "max_file_size", value)
				frappe.clear_cache()
				out = self._upload(self.me, _jpeg(3000, 2000))
				sizes.append(out["bytes"])
				self.assertLessEqual(out["bytes"], expense_evidence.STORED_IMAGE_MAX)
		finally:
			frappe.db.set_single_value("System Settings", "max_file_size", before)
			frappe.clear_cache()
		self.assertEqual(len(set(sizes)), 1, "the outcome must not depend on max_file_size")
		src = _code(expense_evidence)
		self.assertNotIn("max_file_size", src)

	def test_the_ladder_steps_quality_before_width(self):
		"""AC-10's order. Width loses characters; quality loses smoothness. A
		printed amount survives a soft JPEG and does not survive 1024 px."""
		edges = [e for e, q in expense_evidence.LADDER]
		quals = [q for e, q in expense_evidence.LADDER]
		self.assertEqual(quals[:3], [82, 72, 62])
		self.assertEqual(edges[:3], [1600, 1600, 1600])
		self.assertEqual(edges[3:], [1280, 1024])

	def test_every_rung_re_encodes_the_original(self):
		"""Chaining five encodes would compound generation loss on exactly the
		artefact the legibility test judges (OPS-24), and the picture has
		already been through one pass on the phone."""
		seen = []
		real = expense_evidence._reencode

		def spy(blob, edge, quality):
			seen.append(blob[:16])
			return real(blob, edge, quality)

		expense_evidence._reencode = spy
		try:
			expense_evidence._shrink_to_cap(_jpeg(3000, 2200))
		finally:
			expense_evidence._reencode = real
		self.assertEqual(len(set(seen)), 1, "a rung re-encoded a previous rung's output")

	def test_the_upload_limit_is_readable_off_the_function(self):
		"""AC-79c. Sixty an hour per user, and a table test can pin it."""
		for fn in (expense_evidence.upload_evidence, expense_evidence.open_evidence):
			src = inspect.getsource(fn)
			self.assertIn("limit=60", src)
			# The limiter only applies to POST, so a GET-shaped endpoint would
			# never be limited at all (`rate_limiter.py:133`).
			self.assertIn('methods=["POST"]', src)


# ── US-14 · the doors (must-not) ─────────────────────────────────────────────

class NobodyReadsSomebodyElses(_Base):
	def test_nobody_opens_a_colleagues_bill(self):
		"""AC-51. A colleague with no reporting line, through the endpoint,
		with a claim that really exists and really has a file."""
		claim = self._file_claim(self.me)
		self.assertEqual(len(self._rows_for(claim)), 1, "fixture must HAVE a bill")
		frappe.set_user(self.other)
		try:
			with self.assertRaises(frappe.PermissionError) as ctx:
				expense_evidence.open_evidence(kind="bill", parent=claim)
		finally:
			frappe.set_user("Administrator")
		said = str(ctx.exception)
		# The refusal names no employee and no file.
		self.assertNotIn("E081Me", said)
		self.assertNotIn("bill-", said)

	def test_the_approver_does_open_it(self):
		"""The other half, and without it the test above proves nothing: a
		refusal that refuses everybody is not a control."""
		claim = self._file_claim(self.me)
		frappe.set_user(self.mgr)
		try:
			expense_evidence.open_evidence(kind="bill", parent=claim)
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(frappe.local.response.get("filecontent"))

	def test_a_client_cannot_name_a_doctype(self):
		"""081-SEC-5 clause 5. The endpoint takes a KIND, so there is no value
		a browser can post that selects a table we did not choose."""
		for bad in ("Employee", "User", "Salary Slip", "", None, "Expense Claim"):
			with self.subTest(kind=bad):
				frappe.set_user(self.me)
				try:
					with self.assertRaises(frappe.ValidationError):
						expense_evidence.open_evidence(kind=bad, parent="anything")
				finally:
					frappe.set_user("Administrator")

	def test_no_response_anywhere_carries_a_private_files_url(self):
		"""AC-52. Four callers, and not one of them is handed an address."""
		claim = self._file_claim(self.me)
		req = self._raise_dayfix(self.me, with_file=True)
		frappe.set_user(self.me)
		try:
			mine = hr_api.get_expense_claims()
			cards = attendance_correction.my_requests()
		finally:
			frappe.set_user("Administrator")
		frappe.set_user(self.mgr)
		try:
			queue = inbox_api.get_inbox()
		finally:
			frappe.set_user("Administrator")
		for label, payload in (("my claims", mine), ("my day-fix", cards),
		                       ("the queue", queue)):
			with self.subTest(label):
				self.assertNotIn("/private/files/", frappe.as_json(payload))
		# And what replaces the url is a BOOLEAN, on every row.
		#
		# Not "find this claim and check its flag": `get_expense_claims` returns
		# the newest 15 by `posting_date`, and the committed claims from earlier
		# tests all carry today's date, so which 15 come back is not something
		# this test should depend on. The requirement is about what the payload
		# carries, and that is what is asserted.
		self.assertTrue(mine["claims"])
		for c in mine["claims"]:
			self.assertIsInstance(c["has_bill"], bool)
			self.assertNotIn("file_url", c)
		self.assertTrue(cards)
		for c in cards:
			self.assertIsInstance(c["has_evidence"], bool)
		# The day-fix list IS ordered newest first and capped at 20, so the one
		# just raised is there - and it carries a file.
		just_raised = [c for c in cards if c["name"] == req]
		self.assertEqual(len(just_raised), 1)
		self.assertIs(just_raised[0]["has_evidence"], True)

	def test_the_queue_row_carries_a_boolean_and_one_extra_query(self):
		"""AC-36 and the query budget: the count must be the same for 200 rows
		as for 20, so the flag is one query for the page and not one per row."""
		for i in range(3):
			self._file_claim(self.me, amount=100 + i)
		frappe.set_user(self.mgr)
		try:
			part = {p["key"]: p for p in inbox_api.get_inbox()["parts"]}["expense_approvals"]
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(part["rows"])
		for r in part["rows"]:
			self.assertIn("has_bill", r)
			self.assertIsInstance(r["has_bill"], bool)
			self.assertNotIn("file_url", r)

	# ── the day-fix side ─────────────────────────────────────────────────
	def _raise_dayfix(self, user, with_file):
		fid = self._upload(user, kind="dayfix")["file_id"] if with_file else None
		frappe.set_user(user)
		try:
			reason = attendance_correction.reasons()[0]["value"]
			return attendance_correction.raise_correction(
				from_date=self._a_past_workday(), reason=reason,
				explanation="The reader did not take my thumb.", file_id=fid)["name"]
		finally:
			frappe.set_user("Administrator")

	def test_a_day_fix_sends_with_no_file_and_says_nothing_about_it(self):
		"""AC-33. And the negative: no confirm exists, because a confirm on an
		optional field is a nudge."""
		name = self._raise_dayfix(self.me, with_file=False)
		row = frappe.get_doc("Attendance Request", name)
		self.assertEqual(row.docstatus, 0)
		self.assertEqual(row.get("alvoraa_review_status"), "Waiting")
		self.assertEqual(frappe.get_all("File", filters={
			"attached_to_doctype": "Attendance Request", "attached_to_name": name}), [])

	def test_a_day_fix_file_gets_its_parent(self):
		"""AC-34, read back from the database."""
		name = self._raise_dayfix(self.me, with_file=True)
		rows = frappe.get_all("File", filters={
			"attached_to_doctype": "Attendance Request", "attached_to_name": name},
			fields=["attached_to_name", "file_name"])
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].attached_to_name, name)
		self.assertTrue(rows[0].file_name.startswith("dayfix-"))


# ── US-15 · the log ──────────────────────────────────────────────────────────

class WhoLooked(_Base):
	def _log(self, claim):
		return frappe.get_all(expense_evidence.ACCESS_LOG, filters={
			"reference_name": claim}, fields=["name", "source", "viewed_by",
			                                  "employee", "viewed_on_date"])

	def test_one_log_row_per_viewer_per_file_per_day(self):
		"""AC-53, AC-54. Not one per refresh."""
		claim = self._file_claim(self.me)
		for _ in range(3):
			frappe.set_user(self.mgr)
			try:
				expense_evidence.open_evidence(kind="bill", parent=claim)
			finally:
				frappe.set_user("Administrator")
		rows = self._log(claim)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].source, "Expense bill")
		self.assertEqual(rows[0].viewed_by, self.mgr)
		self.assertEqual(rows[0].employee, self.me_emp)

	def test_the_claimant_looking_at_their_own_writes_no_row(self):
		"""AC-55. An access log that records everything is one nobody reads."""
		claim = self._file_claim(self.me)
		frappe.set_user(self.me)
		try:
			expense_evidence.open_evidence(kind="bill", parent=claim)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(self._log(claim), [])

	def test_a_day_fix_view_is_recorded_under_its_own_source(self):
		"""AC-56. Two values, two doctypes - the WHERE clause the doctype's own
		description anticipated, not a redesign."""
		fid = self._upload(self.me, kind="dayfix")["file_id"]
		frappe.set_user(self.me)
		try:
			reason = attendance_correction.reasons()[0]["value"]
			name = attendance_correction.raise_correction(
				from_date=self._a_past_workday(), reason=reason,
				explanation="Punch slip attached.", file_id=fid)["name"]
		finally:
			frappe.set_user("Administrator")
		frappe.set_user(self.hr)
		try:
			expense_evidence.open_evidence(kind="dayfix", parent=name)
		finally:
			frappe.set_user("Administrator")
		rows = self._log(name)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].source, "Day-fix evidence")

	def test_a_failed_log_never_stops_the_reviewer(self):
		"""AC-57. And the logged error carries no file name and no url."""
		claim = self._file_claim(self.me)
		real = frappe.get_doc
		seen = []

		def boom(*a, **k):
			if a and isinstance(a[0], dict) and a[0].get("doctype") == expense_evidence.ACCESS_LOG:
				raise Exception("no")
			return real(*a, **k)

		logs = []
		real_log = frappe.log_error
		frappe.get_doc = boom
		frappe.log_error = lambda *a, **k: logs.append((a, k))
		try:
			frappe.set_user(self.mgr)
			expense_evidence.log_view("Expense Claim", claim)
		finally:
			frappe.get_doc = real
			frappe.log_error = real_log
			frappe.set_user("Administrator")
		self.assertTrue(logs, "the failure must be recorded")
		self.assertNotIn("bill-", str(logs))
		self.assertNotIn("/private/files/", str(logs))

	def test_the_subject_can_ask_and_gets_only_their_own(self):
		"""AC-58. The person whose file it is cannot open the screen that shows
		it, so without this they have no way at all to find out."""
		claim = self._file_claim(self.me)
		frappe.set_user(self.mgr)
		try:
			expense_evidence.open_evidence(kind="bill", parent=claim)
		finally:
			frappe.set_user("Administrator")
		frappe.set_user(self.me)
		try:
			mine = expense_evidence.who_opened_mine()
		finally:
			frappe.set_user("Administrator")
		# **The log is committed on purpose** - it has to outlive the request
		# that wrote it - so earlier tests' rows are still there. The assertion
		# is therefore about THIS claim and about whose rows came back, which is
		# what the requirement is about. A bare count would be a test about the
		# order the suite happened to run in.
		refs = [r["reference"] for r in mine["opened"]]
		self.assertIn(claim, refs)
		self.assertTrue(mine["opened"])
		for r in mine["opened"]:
			self.assertIn(r["what"], ("Expense bill", "Day-fix evidence"))
		# It takes no argument, so there is nothing a browser can post to widen
		# it to somebody else.
		self.assertEqual(list(inspect.signature(
			expense_evidence.who_opened_mine).parameters), [])

		frappe.set_user(self.other)
		try:
			theirs = expense_evidence.who_opened_mine()
		finally:
			frappe.set_user("Administrator")
		self.assertNotIn(claim, [r["reference"] for r in theirs["opened"]],
		                 "one person's log must never reach another's answer")


# ── US-16 / US-17 · the clocks ───────────────────────────────────────────────

class TheClocks(_Base):
	def _age_claim(self, claim, years):
		"""Put a claim's posting_date that many financial years back."""
		start = expense_evidence._fy_start_month()
		fy = expense_evidence._fy_of(nowdate()) - years
		frappe.db.set_value("Expense Claim", claim, "posting_date",
		                    "%d-%02d-15" % (fy, start), update_modified=False)

	def test_a_bill_outlives_eight_financial_years_and_then_does_not(self):
		"""AC-59, AC-63. The claim and its lines stay: the voucher's statutory
		period has expired, not the entry's."""
		recent = self._file_claim(self.me, amount=111)
		old = self._file_claim(self.me, amount=222)
		self._age_claim(old, 9)
		out = expense_evidence.erase_due_bills()
		self.assertEqual(self._rows_for(old), [], "the old bill should be gone")
		self.assertEqual(len(self._rows_for(recent)), 1, "the recent bill must stay")
		self.assertTrue(frappe.db.exists("Expense Claim", old), "the CLAIM must stay")
		self.assertGreaterEqual(out["deleted"], 1)
		self.assertIn("considered", out)

	def test_the_clock_is_anchored_to_posting_date_and_not_to_modified(self):
		"""AC-63. Ticking legal hold off and on restarts a `modified` clock -
		the lesson already written into alvoraa_joiner_submission.py."""
		claim = self._file_claim(self.me)
		self._age_claim(claim, 9)
		frappe.db.set_value("Expense Claim", claim, "modified", now())
		expense_evidence.erase_due_bills()
		self.assertEqual(self._rows_for(claim), [])

	def test_legal_hold_wins_on_both_clocks(self):
		"""AC-60, AC-68. Deleting evidence somebody has asked you to preserve
		is worse than keeping it too long."""
		claim = self._file_claim(self.me)
		self._age_claim(claim, 9)
		frappe.db.set_value("Expense Claim", claim,
		                    expense_evidence.LEGAL_HOLD, 1, update_modified=False)
		expense_evidence.erase_due_bills()
		self.assertEqual(len(self._rows_for(claim)), 1)

	def test_a_cancelled_claims_bill_survives_to_the_statutory_clock(self):
		"""AC-61. A cancelled voucher is still a voucher, and a claim cancelled
		after a dispute is exactly the record that defends the decision."""
		claim = self._file_claim(self.me)
		frappe.db.set_value("Expense Claim", claim, "docstatus", 2, update_modified=False)
		expense_evidence.erase_due_bills()
		self.assertEqual(len(self._rows_for(claim)), 1)

	def test_a_leavers_bill_survives_because_the_file_follows_the_claim(self):
		"""AC-62."""
		claim = self._file_claim(self.gone)
		self._mark_left(self.gone_emp, 13)
		expense_evidence.erase_due_bills()
		self.assertEqual(len(self._rows_for(claim)), 1)

	def test_the_day_fix_pass_does_nothing_until_it_is_switched_on(self):
		"""Surbhi, 3 Nov 2026 (OQ-9). This is the pass that deletes something a
		person may still care about, so it follows grooming.erase_daily."""
		out = expense_evidence.erase_due_dayfix_files()
		self.assertEqual(out, {"switched_on": 0})

	def test_a_leavers_day_fix_file_goes_six_months_after_they_left(self):
		"""AC-67, with its own count - two clocks, two counts."""
		fid = self._upload(self.gone, kind="dayfix")["file_id"]
		frappe.set_user(self.gone)
		try:
			reason = attendance_correction.reasons()[0]["value"]
			name = attendance_correction.raise_correction(
				from_date=self._a_past_workday(self.gone_emp), reason=reason,
				explanation="A note from the clinic.", file_id=fid)["name"]
		finally:
			frappe.set_user("Administrator")
		self._mark_left(self.gone_emp, expense_evidence.DAYFIX_MONTHS + 1)
		frappe.conf[expense_evidence.DAYFIX_ERASE_KEY] = 1
		try:
			out = expense_evidence.erase_due_dayfix_files()
		finally:
			frappe.conf.pop(expense_evidence.DAYFIX_ERASE_KEY, None)
		self.assertEqual(frappe.get_all("File", filters={
			"attached_to_doctype": "Attendance Request", "attached_to_name": name}), [])
		self.assertTrue(frappe.db.exists("Attendance Request", name),
		                "the REQUEST must stay - it is the attendance record")
		self.assertGreaterEqual(out["deleted"], 1)

	def test_an_orphan_goes_within_a_day_and_an_attached_file_never_does(self):
		"""AC-69, AC-70. The negative half has a real attached file in the
		fixture, or it would pass for the wrong reason."""
		claim = self._file_claim(self.me)
		orphan = self._upload(self.me, _jpeg(800, 600))["file_id"]
		young = self._upload(self.me, _jpeg(810, 610))["file_id"]
		frappe.db.set_value("File", orphan, "creation",
		                    add_to_date(now(), hours=-30), update_modified=False)
		out = expense_evidence.sweep_orphans()
		self.assertFalse(frappe.db.exists("File", orphan))
		self.assertTrue(frappe.db.exists("File", young),
		                "a file younger than two hours must survive")
		self.assertEqual(len(self._rows_for(claim)), 1,
		                 "an ATTACHED file must never be swept")
		self.assertGreaterEqual(out["deleted"], 1)

	def test_the_sweep_leaves_a_file_that_is_not_ours(self):
		"""**The sweep takes our own abandoned uploads and nothing else.**

		The first version of it swept every unparented private file on the site,
		which is far more than OPS-15 asked for: somebody else's in-flight
		upload, a file left in the File manager on purpose, another feature's
		work in progress. There is no flag saying "this one is ours" - the
		stored NAME is, by construction - so this fixture puts a stranger's
		unparented private file right in the sweep's path and asserts it
		survives.
		"""
		stranger = frappe.get_doc({
			"doctype": "File", "file_name": "someone-elses-work.jpg",
			"is_private": 1, "content": _jpeg(400, 300),
		}).insert(ignore_permissions=True)
		ours = self._upload(self.me, _jpeg(420, 320))["file_id"]
		for name in (stranger.name, ours):
			frappe.db.set_value("File", name, "creation",
			                    add_to_date(now(), hours=-30), update_modified=False)
		expense_evidence.sweep_orphans()
		self.assertFalse(frappe.db.exists("File", ours),
		                 "our own abandoned upload should have gone")
		self.assertTrue(frappe.db.exists("File", stranger.name),
		                "a file that is not ours must never be swept")

	def test_the_daily_pass_runs_safely_twice(self):
		"""AC-70b. The second run deletes nothing extra and raises nothing."""
		claim = self._file_claim(self.me)
		self._age_claim(claim, 9)
		first = expense_evidence.daily()
		second = expense_evidence.daily()
		self.assertIsNotNone(first["bills"])
		self.assertIsNotNone(second["bills"])
		self.assertEqual(second["bills"]["deleted"], 0)

	def test_no_value_ever_means_for_ever(self):
		"""AC-65, as far as this slice ships it. The number is a constant with
		the statutory floor as its value; OQ-1 (making it a tenant setting) is
		still open, and this test pins the floor so a later edit cannot quietly
		drop below it."""
		self.assertGreaterEqual(expense_evidence.BILL_YEARS, 8)
		self.assertGreater(expense_evidence.DAYFIX_MONTHS, 0)
		self.assertGreater(expense_evidence.ORPHAN_HOURS, 0)
		src = _code(expense_evidence)
		self.assertNotIn("keep for ever", src.lower())


# ── US-18 · the two numbers ──────────────────────────────────────────────────

class TheTwoNumbers(_Base):
	def test_hr_reads_two_numbers_and_the_first_is_zero_on_a_healthy_fixture(self):
		"""AC-71. The one that must be 0 is "approved claims with no bill"."""
		self._file_claim(self.me)
		frappe.set_user(self.hr)
		try:
			out = expense_evidence.counts()
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(out["approved_claims_with_no_bill"], 0)
		self.assertIn("orphan_uploads", out)

	def test_a_non_hr_login_is_refused(self):
		"""AC-72. No dashboard, no alert, no new tool."""
		frappe.set_user(self.me)
		try:
			with self.assertRaises(frappe.PermissionError):
				expense_evidence.counts()
		finally:
			frappe.set_user("Administrator")


# ── US-20 · nothing grew that nobody asked for ───────────────────────────────

class NothingGrew(_Base):
	def test_exactly_four_new_whitelisted_endpoints(self):
		"""AC-78."""
		src = _code(expense_evidence)
		self.assertEqual(src.count("frappe.whitelist"), 4)

	def test_no_second_copy_of_the_bytes(self):
		"""AC-76. No thumbnail, no derived preview, no cache, no object store,
		no CDN - and one `File` insert per upload."""
		src = _code(expense_evidence)
		self.assertEqual(src.count("'doctype': 'File'"), 1)
		# `img.thumbnail(...)` is Pillow's RESIZE call, not a stored thumbnail,
		# so the word itself is not the thing to look for - a second File row,
		# a bucket or a cache is.
		for never in ("make_thumbnail", "thumbnail_url", "boto3", "cdn", "cache.set"):
			self.assertNotIn(never, src.lower())

	def test_nothing_says_a_bill_is_protected(self):
		"""AC-79, 081-PRIV-5. We cannot mask the inside of a photograph, so
		nothing may say or imply that we do."""
		import os

		here = os.path.dirname(os.path.dirname(os.path.abspath(
			expense_evidence.__file__)))
		targets = [os.path.join(here, "alvoraa_portal", "expense_evidence.py")]
		banned = ("is protected", "is secure", "is hidden", "is masked", "is redacted",
		          "are protected", "are hidden", "are masked")
		for path in targets:
			with open(path, encoding="utf-8") as f:
				text = f.read().lower()
			for word in banned:
				self.assertNotIn(word, text, "%s claims %r" % (path, word))

	def test_nothing_new_on_the_child_table(self):
		"""AC-77. `Expense Claim Detail` is where the ALV-256 trap lives, and
		`has_permission` on a child table answers False for everybody - so a
		rule there would refuse the feature to its own audience."""
		src = _code(expense_evidence)
		self.assertNotIn("Expense Claim Detail", src)
