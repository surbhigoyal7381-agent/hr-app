"""082 - the button, the link, and the delete that had to be stopped.

**The test this file exists for is `TestTheDocumentsSurviveTheNightlyJob`.**
Everything else proves the two endpoints behave; that class proves the slice did
not destroy the customer's own records on the way past.

Before 082, `Alvoraa Joiner Submission.employee` was `read_only: 1` and nothing
in the product wrote it, so the status *Made an employee* was unreachable and
`joiner_housekeeping._erase_the_redundant_copies` had never fired on a real row.
That pass calls `erase`, which calls `delete_the_documents`, which deletes the
uploaded identity documents permanently, bytes included - and it runs FIRST in
`run_daily`. Building the link switches it on. The guard is what keeps the files.

**What is deliberately not tested here, because it is not built:** the document
move. No file goes onto an `Employee` in this slice, so there is no
`Employee Document` row, no tick, no checklist and no moved `File` to assert on.

Two of these tests are written from metadata rather than from a list of field
names, on purpose: a hand-written list is a test that passes while the thing it
guards rots.

  * `test_no_date_or_datetime_is_in_the_payload` reads `Employee`'s own meta, so
    a `Date` field added to the payload later cannot escape it (082-SEC-1).
  * `test_nothing_at_a_locked_field_level_crosses_except_the_name` reads
    `employee_field_rights.LEVEL_1` and `LEVEL_2`, so adding a field to either
    constant automatically tightens the test (082-SEC-4).
"""

import ast
import inspect

import frappe
from frappe.utils import add_to_date, now

from alvoraa_portal import joiner_housekeeping as hk
from alvoraa_portal import joiner_to_employee as j2e
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission.alvoraa_joiner_submission import (
	COLUMN_FOR_TICK,
)
from alvoraa_portal.employee_field_rights import LEVEL_1, LEVEL_2
from alvoraa_portal.tests import fixtures_078 as fx
from alvoraa_portal.tests.fixtures_045 import Wave4Base, own_user

DOCTYPE = "Alvoraa Joiner Submission"

# One value per column, so a map that crosses two of them over is visible.
SENT = {
	"full_name": "Rakesh Kumar",
	"mobile": "9811112222",
	"personal_email": "rakesh082@example.com",
	"current_address": "12 Nehru Road, Pune",
	"emergency_contact_name": "Sunita Kumar",
	"emergency_relation": "Sister",
	"emergency_phone": "9822223333",
}


def _without_the_prose(source):
	"""The module's code with every docstring and comment taken out.

	`ast.unparse` drops comments by itself; the docstrings have to be blanked
	one node at a time, which is `test_portal_security_010`'s own approach and
	the reason its ceilings stopped carrying prose as headroom.
	"""
	tree = ast.parse(source)
	for node in ast.walk(tree):
		if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
		                         ast.AsyncFunctionDef)):
			continue
		first = node.body[0] if node.body else None
		if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
				and isinstance(first.value.value, str)):
			first.value.value = ""
	return ast.unparse(tree)


class _Base(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.p = fx.people()
		cls.hr = cls.p["hr_wide_user"]
		cls.hr_user_role = own_user("s082hruser", ("Employee", "HR User"))
		cls.staff = own_user("s082staff", ("Employee",))
		# A login holding ONLY the joiner's role, built directly rather than
		# through `make_sign_in`: the sign-in needs the employer's own settings
		# and a site-wide mobile-login switch, and none of that is what these
		# tests are about. What matters is the roles the session holds.
		from alvoraa_portal.joiner_invite import JOINER_ROLE, make_role

		make_role()
		cls.joiner = own_user("s082joiner", (JOINER_ROLE,))
		cls.employee = cls.p["no_photo"]
		cls.other_employee = cls.p["gps"]
		frappe.db.commit()

	def setUp(self):
		super().setUp()
		self._made = []
		self._files = []
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in self._files:
			if frappe.db.exists("File", name):
				frappe.delete_doc("File", name, force=True,
				                  ignore_permissions=True,
				                  delete_permanently=True)
		for name in self._made:
			if frappe.db.exists(DOCTYPE, name):
				frappe.delete_doc(DOCTYPE, name, force=True,
				                  ignore_permissions=True)
		frappe.db.commit()
		super().tearDown()

	def _submission(self, status="Submitted", **extra):
		values = {"doctype": DOCTYPE, "status": status,
		          "invited_by": self.hr, **SENT, **extra}
		row = frappe.get_doc(values).insert(ignore_permissions=True)
		self._made.append(row.name)
		return row.name

	def _a_file_on(self, submission, name="joiner-082-Aadhaar.pdf"):
		row = frappe.get_doc({
			"doctype": "File", "file_name": name,
			"attached_to_doctype": DOCTYPE, "attached_to_name": submission,
			"is_private": 1, "content": fx._one_page_pdf(),
		}).insert(ignore_permissions=True)
		self._files.append(row.name)
		return row.name

	def _age(self, submission, days):
		"""Push `creation` and `closed_on` back. SQL, because `set_value` will
		not move `creation` and a controller save stamps `closed_on` with
		today."""
		stamp = add_to_date(now(), days=-days)
		frappe.db.sql("update `tabAlvoraa Joiner Submission` "
		              "set creation = %s, closed_on = %s where name = %s",
		              (stamp, stamp, submission))
		frappe.db.commit()


class TestThePrefill(_Base):
	def test_it_returns_the_six_details_and_the_name_character_for_character(self):
		"""AC-2. The mobile number is the one that matters: it is where payslip
		and attendance messages go, and a one-digit typo is invisible until
		somebody says they never got anything."""
		name = self._submission()
		frappe.set_user(self.hr)
		got = j2e.details_for_a_new_employee(submission=name)
		self.assertEqual(got, {
			"first_name": "Rakesh Kumar",
			"cell_number": "9811112222",
			"personal_email": "rakesh082@example.com",
			"current_address": "12 Nehru Road, Pune",
			"person_to_be_contacted": "Sunita Kumar",
			"relation": "Sister",
			"emergency_phone_number": "9822223333",
		})

	def test_the_keys_are_the_one_map_inverted_and_nothing_else(self):
		"""AC-5. `COLUMN_FOR_TICK` is the single source of truth for what may
		cross, and it is inverted at runtime so no second list exists - not here
		and not in the browser."""
		name = self._submission()
		frappe.set_user(self.hr)
		got = j2e.details_for_a_new_employee(submission=name)
		self.assertEqual(set(got), set(COLUMN_FOR_TICK) | {"first_name"})

	def test_every_key_is_returned_even_when_the_joiner_left_it_blank(self):
		"""Seven, always. A key that appears and disappears would make the
		browser's behaviour depend on the data."""
		name = self._submission(current_address=None, emergency_relation=None)
		frappe.set_user(self.hr)
		got = j2e.details_for_a_new_employee(submission=name)
		self.assertEqual(set(got), set(COLUMN_FOR_TICK) | {"first_name"})
		self.assertIsNone(got["current_address"])

	def test_no_date_or_datetime_is_in_the_payload(self):
		"""**082-SEC-1, and the test the whole protection rests on.**

		Written from `Employee`'s own meta, not from a list of names, so a date
		field added to the payload later cannot escape it. A back-dated joining
		date makes Frappe mark the person Absent for every day since, and
		deleting those rows does not help - a logged DTC fault.
		"""
		name = self._submission()
		frappe.set_user(self.hr)
		got = j2e.details_for_a_new_employee(submission=name)
		meta = frappe.get_meta("Employee")
		dated = [key for key in got
		         if (meta.get_field(key) or frappe._dict()).get("fieldtype")
		         in ("Date", "Datetime")]
		self.assertEqual(dated, [], "no date may ever be prefilled")
		self.assertNotIn("date_of_joining", got)
		self.assertNotIn("date_of_birth", got)

	def test_the_joining_date_is_mandatory_on_employee_so_hr_must_type_it(self):
		"""The second half of 082-SEC-1, and it is Frappe's own check rather
		than ours. If this ever goes false, the protection rests on a sentence
		on a screen and the button must not exist in this shape."""
		field = frappe.get_meta("Employee").get_field("date_of_joining")
		self.assertTrue(field.reqd, "Employee.date_of_joining must stay mandatory")

	def test_nothing_at_a_locked_field_level_crosses_except_the_name(self):
		"""**082-SEC-4**, the half of 078-SEC-12 that stops the drift.

		Generated from `LEVEL_1` and `LEVEL_2`, so adding a field to either
		constant tightens this test by itself.

		`first_name` is the one permitted exception and it is deliberate: it is
		mandatory on `Employee`, it sits at level 2, and the person's own name
		is the one thing HR is not relied upon to have verified independently.
		The joiner's typed claim must never land in a column HR is trusted to
		have checked - no `pan_number`, no bank field, no `designation`, no
		`grade`, no `company`, no `status`, no `user_id`.
		"""
		name = self._submission()
		frappe.set_user(self.hr)
		keys = set(j2e.details_for_a_new_employee(submission=name))
		self.assertEqual(keys & set(LEVEL_1), set(),
		                 "nothing at level 1 may be prefilled")
		self.assertEqual(keys & set(LEVEL_2), {"first_name"},
		                 "only the name may cross at level 2")

	def test_it_creates_nothing_and_does_not_move_the_naming_series(self):
		"""AC-3. HR's own Save is the only writer in this slice."""
		name = self._submission()
		before = frappe.db.count("Employee")
		frappe.set_user(self.hr)
		j2e.details_for_a_new_employee(submission=name)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count("Employee"), before)
		self.assertFalse(frappe.db.exists(
			"Employee", {"personal_email": SENT["personal_email"]}))

	def test_it_is_refused_in_every_state_but_submitted(self):
		"""AC-4. The message names the state, because a control that refuses
		without saying why is a guess."""
		for status in ("Invited", "Expired", "Cancelled"):
			name = self._submission(status=status)
			frappe.set_user(self.hr)
			with self.assertRaises(frappe.ValidationError):
				j2e.details_for_a_new_employee(submission=name)
			frappe.set_user("Administrator")

	def test_it_is_refused_once_somebody_is_already_linked(self):
		"""AC-4. Prefilling a second time would invite a second Employee."""
		name = self._submission()
		frappe.db.set_value(DOCTYPE, name, {"employee": self.employee,
		                                    "status": "Made an employee"},
		                    update_modified=False)
		frappe.set_user(self.hr)
		with self.assertRaises(frappe.ValidationError):
			j2e.details_for_a_new_employee(submission=name)

	def test_it_is_refused_on_an_erased_row(self):
		"""AC-4. Prefilling from an erased row would look like data loss rather
		than deletion."""
		name = self._submission(erased_on=now(), erased_why="test")
		frappe.set_user(self.hr)
		with self.assertRaises(frappe.ValidationError):
			j2e.details_for_a_new_employee(submission=name)

	def test_a_missing_or_unknown_reference_is_refused(self):
		frappe.set_user(self.hr)
		with self.assertRaises(frappe.ValidationError):
			j2e.details_for_a_new_employee()
		with self.assertRaises(frappe.DoesNotExistError):
			j2e.details_for_a_new_employee(submission="not-a-real-row")


class TestWhoMayPrefill(_Base):
	"""082-SEC-2. Two doors, both checked server side, before one field is
	returned: `create` on `Employee`, and `read` on THIS row."""

	def test_a_joiner_session_is_refused(self):
		"""AC-18. The one abuse case this slice creates: a curious joiner
		account calling the endpoint with somebody's row name."""
		name = self._submission()
		frappe.set_user(self.joiner)
		with self.assertRaises(frappe.PermissionError):
			j2e.details_for_a_new_employee(submission=name)

	def test_a_plain_staff_login_is_refused(self):
		"""AC-19. The Employee role holds no permission at all on this doctype,
		and no `create` on `Employee`."""
		name = self._submission()
		frappe.set_user(self.staff)
		with self.assertRaises(frappe.PermissionError):
			j2e.details_for_a_new_employee(submission=name)

	def test_neither_endpoint_is_reachable_without_signing_in(self):
		"""Pre-onboarding's public write surface is zero and must stay zero.

		`test_joiner_079` sweeps `joiner_public`, `joiner_invite` and
		`joiner_housekeeping` for guest methods; **it does not know this module
		exists**, so the same claim is made here rather than by editing a test
		file another session may be in. Static, on `frappe.guest_methods`, so it
		cannot pass by accident.
		"""
		guests = [name for name, fn in inspect.getmembers(j2e, inspect.isfunction)
		          if fn in frappe.guest_methods]
		self.assertEqual(guests, [],
		                 f"a joiner-to-employee endpoint is open to the "
		                 f"public: {guests}")

	def test_hr_user_may_prefill_but_hr_user_may_not_link(self):
		"""AC-21. The existing 078/079 split: HR User reads submissions and HR
		Manager writes them. HR User may fill the form in; committing is not
		theirs."""
		name = self._submission()
		frappe.set_user(self.hr_user_role)
		self.assertTrue(j2e.details_for_a_new_employee(submission=name))
		with self.assertRaises(frappe.PermissionError):
			j2e.link_the_employee(submission=name, employee=self.employee)


class TestTheLink(_Base):
	def test_it_links_moves_the_status_on_and_stamps_the_closing(self):
		"""AC-9, the half of it that is in scope. The status and `closed_on`
		follow from the controller's own `validate` - no second copy of that
		rule lives in the endpoint."""
		name = self._submission()
		frappe.set_user(self.hr)
		out = j2e.link_the_employee(submission=name, employee=self.employee)
		row = frappe.get_doc(DOCTYPE, name)
		self.assertEqual(row.employee, self.employee)
		self.assertEqual(row.status, "Made an employee")
		self.assertTrue(row.closed_on)
		self.assertEqual(out["employee"], self.employee)

	def test_the_reply_names_the_employee_it_was_told_to_link(self):
		"""082-SEC-6, tested on what the call SENDS and returns rather than on
		what a screen draws. Linking the wrong person is the worst outcome in
		this slice and it cannot be undone."""
		name = self._submission()
		frappe.set_user(self.hr)
		out = j2e.link_the_employee(submission=name, employee=self.employee)
		self.assertEqual(out["employee"], self.employee)
		self.assertEqual(out["employee_name"],
		                 frappe.db.get_value("Employee", self.employee,
		                                     "employee_name"))

	def test_it_reports_the_real_count_of_details(self):
		"""AC-16. Computed from what was actually on the row, never a fixed
		string. Six here; five when the person left one blank."""
		name = self._submission()
		frappe.set_user(self.hr)
		self.assertEqual(
			j2e.link_the_employee(submission=name,
			                      employee=self.employee)["details"], 6)
		frappe.set_user("Administrator")
		thin = self._submission(current_address=None)
		frappe.set_user(self.hr)
		self.assertEqual(
			j2e.link_the_employee(submission=thin,
			                      employee=self.other_employee)["details"], 5)

	def test_it_says_how_many_documents_it_did_not_move(self):
		"""The honest half of AC-17. The document move is out of scope, so the
		reply must not claim a tick that does not exist - it says what is still
		on the invite so HR can download it."""
		name = self._submission()
		self._a_file_on(name)
		self._a_file_on(name, "joiner-082-PAN.pdf")
		frappe.set_user(self.hr)
		out = j2e.link_the_employee(submission=name, employee=self.employee)
		self.assertEqual(out["documents_left_behind"], 2)

	def test_it_says_nothing_about_documents_when_there_are_none(self):
		"""AC-12. Not a count of zero dressed up as a tick."""
		name = self._submission()
		frappe.set_user(self.hr)
		out = j2e.link_the_employee(submission=name, employee=self.employee)
		self.assertEqual(out["documents_left_behind"], 0)

	def test_a_second_link_is_refused_and_changes_nothing(self):
		"""AC-11, including the Employee named in the SECOND call: a refused
		link must not touch the record it was pointed at either."""
		name = self._submission()
		frappe.set_user(self.hr)
		j2e.link_the_employee(submission=name, employee=self.employee)
		with self.assertRaises(frappe.ValidationError):
			j2e.link_the_employee(submission=name, employee=self.other_employee)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(DOCTYPE, name, "employee"),
		                 self.employee)

	def test_the_link_is_read_from_the_database_not_from_the_form(self):
		"""The race: two HR users press at the same moment, both having seen the
		field empty on their own screen. The endpoint re-reads it under a row
		lock, so the second one is refused by name.

		Simulated by writing the link behind the endpoint's back after the row
		was loaded - which is exactly what the other session would have done.
		"""
		name = self._submission()
		frappe.db.set_value(DOCTYPE, name, "employee", self.employee,
		                    update_modified=False)
		frappe.set_user(self.hr)
		with self.assertRaises(frappe.ValidationError):
			j2e.link_the_employee(submission=name, employee=self.other_employee)

		# The same locked read covers the other two conditions, so a nightly
		# erase or a cancellation landing in the same instant cannot be worked
		# on as though it had not happened.
		frappe.set_user("Administrator")
		other = self._submission()
		frappe.db.set_value(DOCTYPE, other, "erased_on", now(),
		                    update_modified=False)
		frappe.set_user(self.hr)
		with self.assertRaises(frappe.ValidationError):
			j2e.link_the_employee(submission=other, employee=self.employee)

	def test_it_is_refused_in_every_state_but_submitted(self):
		for status in ("Invited", "Expired", "Cancelled"):
			name = self._submission(status=status)
			frappe.set_user(self.hr)
			with self.assertRaises(frappe.ValidationError):
				j2e.link_the_employee(submission=name, employee=self.employee)
			frappe.set_user("Administrator")

	def test_a_missing_or_unknown_employee_is_refused(self):
		name = self._submission()
		frappe.set_user(self.hr)
		with self.assertRaises(frappe.ValidationError):
			j2e.link_the_employee(submission=name)
		with self.assertRaises(frappe.DoesNotExistError):
			j2e.link_the_employee(submission=name, employee="HR-EMP-99999082")

	def test_a_refused_caller_cannot_tell_a_real_reference_from_a_made_up_one(self):
		"""The existence oracle, closed. A caller with no right on the doctype
		gets the same refusal for a real row and for a name they invented, so
		the difference between the two tells them nothing."""
		real = self._submission()
		frappe.set_user(self.staff)
		for reference in (real, "not-a-real-row"):
			with self.assertRaises(frappe.PermissionError):
				j2e.link_the_employee(submission=reference, employee=self.employee)

	def test_a_plain_staff_login_and_a_joiner_are_both_refused(self):
		"""AC-19 and AC-18 for the write side. Afterwards the row is unchanged -
		a refusal that half-wrote something is not a refusal."""
		name = self._submission()
		for who in (self.staff, self.joiner):
			frappe.set_user(who)
			with self.assertRaises(frappe.PermissionError):
				j2e.link_the_employee(submission=name, employee=self.employee)
			frappe.set_user("Administrator")
			self.assertFalse(frappe.db.get_value(DOCTYPE, name, "employee"))
			self.assertEqual(frappe.db.get_value(DOCTYPE, name, "status"),
			                 "Submitted")

	def test_a_failure_part_way_through_writes_nothing(self):
		"""AC-10 and FR-ORDER. If the save raises, the link is not written - so
		the status never becomes *Made an employee*, so the nightly pass never
		picks the row up at all. Safe by construction, not by timing."""
		name = self._submission()
		from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission import (
			alvoraa_joiner_submission as controller,
		)

		was = controller.AlvoraaJoinerSubmission._stamp_the_closing

		def explode(self):
			raise frappe.ValidationError("forced, in a test")

		controller.AlvoraaJoinerSubmission._stamp_the_closing = explode
		try:
			frappe.set_user(self.hr)
			with self.assertRaises(frappe.ValidationError):
				j2e.link_the_employee(submission=name, employee=self.employee)
		finally:
			# Put the real method back whatever happened: slice 013's lesson is
			# that a patched attribute left behind fails a later suite for a
			# reason that is not in its code.
			controller.AlvoraaJoinerSubmission._stamp_the_closing = was
			frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value(DOCTYPE, name, "employee"))
		self.assertEqual(frappe.db.get_value(DOCTYPE, name, "status"),
		                 "Submitted")

	def test_it_commits_nothing_and_borrows_nobodys_rights(self):
		"""Two pins on the source, because neither can be seen from outside.

		**No `frappe.db.commit()`** (FR-ORDER): one inside this path would let
		the link land while a later step failed, and the night would then erase
		the originals. A behaviour test cannot see a commit that is not there.

		**No `ignore_permissions`** (082-SEC-3): the ceiling test in
		`test_portal_security_010` counts it too, but a bad merge can drop a
		ceiling row silently. This fails in the suite that owns the surface.

		Docstrings and comments are blanked first, the same way the 010 ceiling
		test does it - otherwise a file that *writes about* a bypass reads as one.
		"""
		code = _without_the_prose(inspect.getsource(j2e))
		self.assertNotIn("frappe.db.commit", code)
		self.assertNotIn("ignore_permissions", code)


class TestTheDocumentsSurviveTheNightlyJob(_Base):
	"""**US-7, and the reason this slice needed a guard.**

	The link made *Made an employee* reachable, which switched on
	`_erase_the_redundant_copies`, which deletes the uploaded identity documents
	permanently. The document move that would make that safe is out of scope, so
	the pass skips any hired row that still holds its files.
	"""

	def test_a_hired_joiners_documents_survive_the_nightly_job(self):
		"""The headline. Hire the person, run the job, and the Aadhaar photo
		they sent from their phone is still there the next morning."""
		name = self._submission()
		a_file = self._a_file_on(name)
		frappe.set_user(self.hr)
		j2e.link_the_employee(submission=name, employee=self.employee)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(DOCTYPE, name, "status"),
		                 "Made an employee")

		hk.run_daily()

		self.assertTrue(frappe.db.exists("File", a_file),
		                "a hired joiner's uploaded document must not be deleted "
		                "while nothing has moved it to the employee record")
		self.assertFalse(frappe.db.get_value(DOCTYPE, name, "erased_on"))
		self.assertTrue(frappe.db.get_value(DOCTYPE, name, "mobile"),
		                "the row is skipped whole, so its details stay with its "
		                "files until something moves them")

	def test_the_hired_pass_reports_it_erased_nothing(self):
		"""The count stays honest: a skipped row is not an erased row."""
		name = self._submission()
		self._a_file_on(name)
		frappe.set_user(self.hr)
		j2e.link_the_employee(submission=name, employee=self.employee)
		frappe.set_user("Administrator")
		self.assertEqual(hk._erase_the_redundant_copies(), 0)

	def test_a_hired_row_with_no_documents_is_still_erased(self):
		"""The existing behaviour, kept. The typed details really are redundant
		once HR has saved them onto the Employee - it is only the files that
		have nowhere to go yet."""
		name = self._submission()
		frappe.set_user(self.hr)
		j2e.link_the_employee(submission=name, employee=self.employee)
		frappe.set_user("Administrator")
		self.assertEqual(hk._erase_the_redundant_copies(), 1)
		self.assertFalse(frappe.db.get_value(DOCTYPE, name, "mobile"))
		self.assertTrue(frappe.db.get_value(DOCTYPE, name, "erased_on"))
		self.assertEqual(frappe.db.get_value(DOCTYPE, name, "employee"),
		                 self.employee,
		                 "the Employee link survives the erase deliberately - it "
		                 "is what answers 'who did this become' a year later")

	def test_the_guard_keeps_the_files_when_it_cannot_tell(self):
		"""**Fail closed.** If the count itself fails, the answer is "keep".

		A false yes costs one row an extra erase cycle. A false no destroys a
		person's identity documents for good.
		"""
		name = self._submission()
		a_file = self._a_file_on(name)
		frappe.set_user(self.hr)
		j2e.link_the_employee(submission=name, employee=self.employee)
		frappe.set_user("Administrator")

		def refuse(*args, **kwargs):
			raise Exception("forced, in a test")

		frappe.db.count = refuse
		try:
			self.assertTrue(hk._still_holds_its_documents(name))
			self.assertEqual(hk._erase_the_redundant_copies(), 0)
		finally:
			# `del`, not re-assignment: putting the bound method back would
			# leave an instance attribute shadowing the real one for every
			# later suite on this site.
			del frappe.db.count
		self.assertTrue(frappe.db.exists("File", a_file))
		self.assertFalse(frappe.db.get_value(DOCTYPE, name, "erased_on"))

	def test_the_thirty_day_document_clock_is_untouched(self):
		"""Counsel's ruling 4, and the honest size of the remaining gap: a hired
		joiner's documents still go 30 days after hire, on the clock they were
		already on. This slice neither extends nor shortens it. If this test
		ever has to change, that is counsel's question, not an engineering one.
		"""
		name = self._submission()
		a_file = self._a_file_on(name)
		frappe.set_user(self.hr)
		j2e.link_the_employee(submission=name, employee=self.employee)
		frappe.set_user("Administrator")
		self._age(name, 40)
		self.assertEqual(hk._delete_the_documents_sooner(), 1)
		self.assertFalse(frappe.db.exists("File", a_file))
		self.assertTrue(frappe.db.get_value(DOCTYPE, name, "mobile"),
		                "the document clock must not touch the typed fields")
