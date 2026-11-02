"""078 step 5 - documents on a person's profile, and the five ordered checks.

US-22 to US-25. Two tests here carry the step:

  * **AC-69/AC-70.** What a direct GET of a private file actually does is
    RECORDED, not asserted to be a refusal. Frappe's private-file gate falls
    back to the parent Employee's read permission and no `has_permission` hook
    fires on that path, so the url route stays open for somebody who already
    holds a url. Asserting a refusal there would be a green test for a boundary
    that does not exist.
  * **AC-79.** The scope check runs BEFORE the ticked-type check, so a refusal
    never reveals whether a type was ticked.

And the one nobody asked for, which is why it is checked hardest: the access
record. It is the only way an employee who cannot open the Positions page can
ever ask "who looked at my Aadhaar" and get an answer that is not "we do not
know".
"""

import frappe

from alvoraa_portal import employee_documents_read as docs
from alvoraa_portal.tests import fixtures_078 as fx
from alvoraa_portal.tests.fixtures_045 import Wave4Base


class _Base(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.p = fx.people()
		cls.ticked, cls.unticked = fx.document_types()
		cls.inside = fx.give_documents(cls.p["no_photo"])
		cls.outside = fx.give_documents(cls.p["other_branch"])

	def setUp(self):
		super().setUp()
		# The plan has to be ON, or every case here tests the plan gate rather
		# than the five checks. `test_site` ships `"features": []`.
		self._plan = fx.with_documents_plan().__enter__()
		self.addCleanup(self._plan.__exit__)
		fx.set_lists(profile_fields=["designation"], document_types=[self.ticked])
		for row in fx.document_views():
			frappe.delete_doc("Alvoraa Photo Access Log", row.name, force=True,
			                  ignore_permissions=True)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		fx.clear_lists()
		super().tearDown()


class TestTheList(_Base):
	def test_only_the_ticked_types_appear(self):
		"""AC-65. Two types exist on this employee; one is ticked."""
		frappe.set_user(self.p["hr_wide_user"])
		out = docs.get_employee_documents(employee=self.p["no_photo"])
		names = [d["document_type"] for d in out["documents"]]
		self.assertEqual(names, [self.ticked])
		self.assertNotIn(self.unticked, frappe.as_json(out))

	def test_nothing_ticked_means_no_section_at_all(self):
		"""AC-45. Not an empty heading, not a greyed tab, not a count of zero."""
		fx.set_lists(document_types=[])
		frappe.set_user(self.p["hr_wide_user"])
		self.assertEqual(
			docs.get_employee_documents(employee=self.p["no_photo"])["documents"], [])

	def test_a_ticked_type_with_no_file_says_who_collects_it(self):
		"""AC-64. A dead row becomes an action rather than a shrug."""
		fx.set_lists(document_types=[self.ticked])
		frappe.set_user(self.p["hr_wide_user"])
		out = docs.get_employee_documents(employee=self.p["gps"])   # has none
		row = out["documents"][0]
		self.assertIsNone(row["row"])
		self.assertTrue(row["collect_from"])

	def test_the_list_never_carries_a_file_address(self):
		"""AC-66. The browser is never handed a /private/files/ url for a
		document. It gets the ROW's name, which only our endpoint accepts."""
		frappe.set_user(self.p["hr_wide_user"])
		out = docs.get_employee_documents(employee=self.p["no_photo"])
		self.assertNotIn("/private/files", frappe.as_json(out))
		self.assertNotIn("attachment", frappe.as_json(out))


class TestTheFiveChecks(_Base):
	def _open(self, row):
		frappe.local.response = frappe._dict()
		docs.open_employee_document(row=row)
		return frappe.local.response

	def test_a_reader_in_scope_gets_the_file_as_a_download(self):
		"""AC-66, AC-116. `type = "download"`, which Frappe serves with
		`Content-Disposition: attachment`.

		**That has not changed, and what this asserts is unchanged - but what
		the browser then does with the bytes has.** Since ALV-287 (2 Nov 2026)
		the portal fetches this response with `fetch`, keeps the blob, and
		RENDERS it in a viewer of its own instead of saving it; the header
		never reaches a navigation, so it never decides anything. A PDF is
		shown in an iframe with no sandbox, which is Surbhi's decision and her
		reasons are written at `mpfShowDoc` in portal.js. This docstring used to
		end "so a PDF is never rendered inline". That is no longer true, the
		assertion below never tested it, and a sentence like that is how a
		reader comes to believe the server enforces something it does not."""
		frappe.set_user(self.p["hr_wide_user"])
		res = self._open(self.inside[self.ticked])
		self.assertEqual(res.type, "download")
		self.assertTrue(res.filecontent)
		self.assertTrue(res.filename)

	def test_a_non_ticked_type_is_refused(self):
		"""AC-68. So the ticked list is not decoration."""
		frappe.set_user(self.p["hr_wide_user"])
		with self.assertRaises(frappe.PermissionError):
			self._open(self.inside[self.unticked])

	def test_somebody_who_cannot_open_positions_is_refused(self):
		"""AC-78, and the response carries no document type name and no
		employee name."""
		frappe.set_user(self.p["no_photo_user"])
		with self.assertRaises(frappe.PermissionError) as caught:
			self._open(self.inside[self.ticked])
		said = str(caught.exception)
		self.assertNotIn(self.ticked, said)
		self.assertNotIn("S078NoPhoto", said)

	def test_the_scope_check_runs_before_the_ticked_check(self):
		"""**AC-79.** A reader out of scope asks for an employee's row of a
		NON-ticked type. They must be refused by the SCOPE, so the refusal does
		not reveal whether the type was ticked - and the two refusals must be
		indistinguishable."""
		frappe.set_user(self.p["hr_store_user"])      # Branch A only
		with self.assertRaises(frappe.PermissionError) as a:
			self._open(self.outside[self.unticked])
		with self.assertRaises(frappe.PermissionError) as b:
			self._open(self.outside[self.ticked])
		self.assertEqual(str(a.exception), str(b.exception))

	def test_a_row_id_cannot_be_walked_onto_another_person(self):
		"""The endpoint takes the ROW only and reads its parent itself. There is
		no employee argument to disagree with it - which is the version of this
		function with the hole in it."""
		import inspect

		params = set(inspect.signature(docs.open_employee_document).parameters)
		self.assertEqual(params, {"row"})

	def test_an_empty_or_unknown_row_is_refused(self):
		frappe.set_user(self.p["hr_wide_user"])
		for bad in (None, "", "   ", "S078-NOT-A-ROW", 7):
			with self.subTest(bad=bad):
				with self.assertRaises(frappe.PermissionError):
					self._open(bad)

	def test_the_limit_is_sixty_an_hour_and_readable_off_the_function(self):
		"""AC-71. Keyed through field_app_limits, so the limiter's Redis key is a
		hash rather than a row id."""
		field, source, limit, window = docs.open_employee_document.__alvoraa_limit__
		self.assertEqual((source, limit, window), ("user", 60, 3600))

	def test_what_a_direct_get_of_the_private_file_actually_does(self):
		"""**AC-69 and AC-70, RECORDED rather than asserted.**

		Frappe's private-file download path is
		`app.py:163` -> `utils/response.py:294` -> `file/utils.py:452` ->
		`file.py:896` -> `file.py:989`, and that last function decides:
		Administrator, then not private, then `owner == user`, then a DocShare
		row, then **the attached parent's own read permission**.
		`permissions.py:483` is the only place Frappe reads the `has_permission`
		hook, and this path never enters it - so a hook on `File` cannot close
		this, and a hook on `Employee` would run inside all twenty endpoints
		that read an Employee, including one with `limit=999999`.

		So this test records the real behaviour: a reader who may read the
		PARENT employee can fetch the file by url whatever the ticked list says.
		The ticked list is defence in depth, the browser is never handed a url,
		and no product copy may claim otherwise.
		"""
		from frappe.core.doctype.file.file import has_permission as file_has_permission

		url = frappe.db.get_value("Employee Document", self.inside[self.unticked],
		                          "attachment")
		f = frappe.get_doc("File", {"file_url": url})
		frappe.set_user(self.p["hr_wide_user"])
		reachable = bool(file_has_permission(f, "read"))
		# NOT an assertion that it is refused. The documented behaviour is that
		# it follows the parent Employee's read permission, so for an HR Manager
		# in scope it is reachable - and that is the residual risk R1, accepted.
		self.assertTrue(
			reachable,
			"If this ever becomes False, Frappe has changed the private-file "
			"gate and R1 can be revisited - which would be good news, not a "
			"failure. Read the docstring before changing the assertion.")

	def test_no_product_copy_claims_an_unticked_type_is_protected(self):
		"""AC-65's honest half, as a string test over the real source."""
		import os

		import alvoraa_portal

		root = os.path.dirname(alvoraa_portal.__file__)
		import re

		js = open(os.path.join(root, "public", "js", "ess", "portal.js"),
		          encoding="utf-8").read()
		# The sentence that IS said.
		self.assertIn("Opening one is recorded", js)
		# COMMENTS STRIPPED FIRST. This file's own comments explain at length
		# that nothing may imply the other types are hidden - and the first run
		# of this test failed on that very sentence. A comment cannot mislead a
		# reader of the screen. Same reasoning as
		# `test_portal_security_010`'s ignore_permissions ceiling, which blanks
		# docstrings for exactly this reason.
		code = re.sub(r"/\*[\s\S]*?\*/", " ", js)
		code = re.sub(r"(?m)^\s*//.*$", " ", code)
		for word in ("types are hidden", "types are protected", "types are secure"):
			self.assertNotIn(word, code)


class TestTheAccessRecord(_Base):
	def _open(self, row, user):
		frappe.set_user(user)
		frappe.local.response = frappe._dict()
		docs.open_employee_document(row=row)

	def test_opening_a_document_writes_one_row_with_the_right_columns(self):
		"""AC-73."""
		self._open(self.inside[self.ticked], self.p["hr_wide_user"])
		rows = fx.document_views(self.p["no_photo"])
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].document_type, self.ticked)
		self.assertEqual(rows[0].viewed_by, self.p["hr_wide_user"])

	def test_the_row_holds_nothing_from_the_document_itself(self):
		"""AC-74. No file, no file address, no document number, no value."""
		self._open(self.inside[self.ticked], self.p["hr_wide_user"])
		row = frappe.get_doc("Alvoraa Photo Access Log",
		                     fx.document_views(self.p["no_photo"])[0].name)
		body = frappe.as_json(row.as_dict())
		self.assertNotIn("/private/files", body)
		self.assertNotIn("attachment", body)
		self.assertNotIn("document_number", body)

	def test_twice_in_one_day_is_one_row(self):
		"""AC-75. One per viewer per document per day, not one per refresh."""
		self._open(self.inside[self.ticked], self.p["hr_wide_user"])
		self._open(self.inside[self.ticked], self.p["hr_wide_user"])
		self.assertEqual(len(fx.document_views(self.p["no_photo"])), 1)

	def test_a_person_opening_their_own_writes_nothing(self):
		"""AC-76. Never a person looking at their own."""
		docs.log_document_view(self.p["no_photo"], self.ticked)
		frappe.set_user(self.p["no_photo_user"])
		docs.log_document_view(self.p["no_photo"], self.ticked)
		rows = fx.document_views(self.p["no_photo"])
		self.assertTrue(all(r.viewed_by != self.p["no_photo_user"] for r in rows))

	def test_an_ordinary_employee_cannot_read_the_record(self):
		"""AC-77. Read is System Manager and HR Manager only, unchanged."""
		meta = frappe.get_meta("Alvoraa Photo Access Log")
		roles = {p.role for p in meta.permissions if p.read}
		self.assertEqual(roles, {"System Manager", "HR Manager"})

	def test_existing_rows_keep_the_right_source(self):
		"""Every row written before this slice was a check-in photo view, so the
		new column's default is correct and no patch is needed."""
		meta = frappe.get_meta("Alvoraa Photo Access Log")
		self.assertEqual(meta.get_field("source").default, "Check-in photo")
		self.assertFalse(meta.get_field("checkin").reqd,
		                 "a document view has no check-in")


class TestWhatTheEmployeeIsTold(_Base):
	def test_an_employee_can_find_out_what_of_theirs_is_shown(self):
		"""Surbhi's ⚠ DECISION O. The person whose documents these are cannot
		open the Positions page, so this is their only way to know. Types only -
		never a reader and never a person."""
		frappe.set_user(self.p["no_photo_user"])
		out = docs.what_is_shown_about_me()
		self.assertEqual(out["types"], [self.ticked])
		self.assertNotIn("hr_wide", frappe.as_json(out))
