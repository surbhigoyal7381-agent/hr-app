"""045 - the staff directory carries work contact, and only work contact.

Surbhi's decision of 24 September 2026: the directory is for employees too,
and contact details are IN. Her reason: *"the companies have NDAs"*.

**What shipped: work email, and no phone number at all.**

`Employee.company_email` exists and is genuinely a work field, so it is in.
**There is no work phone or extension field in the data model.** `cell_number`
is labelled "Mobile", `personal_email` says what it is, and
`emergency_phone_number` is somebody else's number entirely. Her instruction
had a stop condition for exactly this - *"If the data model has only a
personal mobile field, say so and stop rather than shipping a personal
number"* - so no phone number ships, and adding a work-phone field needs her
word.

**The NDA point, because it is the half that is easy to get backwards:** an
NDA binds the employee who LOOKS. It is not the same as the employer's own
duty to the person whose data it is. Keeping the directory to work contact is
what makes the wider audience safe.
"""

import frappe

from alvoraa_portal import staff_api
from alvoraa_portal.tests.fixtures_045 import FORBIDDEN_VALUES, Wave4Base
from alvoraa_portal.tests.test_team_payload_045 import find_key, find_value

WORK_EMAIL = "s045.work.contact@example.com"
PERSONAL_EMAIL = "S045-PERSONAL-do-not-show@example.com"


class TestTheDirectoryCarriesWorkContactOnly(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Populated on purpose. An empty fixture would let every "must not
		# contain" assertion below pass while the field was still going out.
		frappe.db.set_value("Employee", cls.rahul, "company_email", WORK_EMAIL,
		                    update_modified=False)
		frappe.db.set_value("Employee", cls.rahul, "personal_email", PERSONAL_EMAIL,
		                    update_modified=False)
		frappe.db.commit()

	def test_the_fixture_really_carries_both_emails(self):
		"""The check on the check."""
		row = frappe.db.get_value("Employee", self.rahul,
		                          ["company_email", "personal_email", "cell_number"],
		                          as_dict=True)
		self.assertEqual(WORK_EMAIL, row.company_email)
		self.assertEqual(PERSONAL_EMAIL, row.personal_email)
		self.assertTrue(row.cell_number, "the fixture has no mobile number, so "
		                                 "the assertion about it proves nothing")

	def test_work_email_is_in_the_row_keys(self):
		self.assertIn("work_email", staff_api.ROW_KEYS)

	def test_no_personal_contact_field_is_anywhere_in_the_key_list(self):
		for field in ("cell_number", "personal_email", "emergency_phone_number",
		              "date_of_birth", "current_address", "permanent_address",
		              "passport_number"):
			with self.subTest(field=field):
				self.assertNotIn(field, staff_api.ROW_KEYS)
				self.assertNotIn(field, " ".join(staff_api.ROW_FIELDS))

	def setUp(self):
		super().setUp()
		# **Turn the feature ON rather than skipping when it is off.**
		#
		# The first version of this test skipped itself with
		# "the staff_list feature is not on for this tenant" - and reported
		# "OK (skipped=1)", which reads as a pass and proves nothing at all.
		# A test that skips the only assertion it exists for is worse than no
		# test, because it appears in the count.
		import alvoraa_portal.subscription as sub

		self._saved_features = frappe.conf.get("features")
		frappe.conf["features"] = list(sub.DEFAULT_ON) + [staff_api.FEATURE]

	def tearDown(self):
		if self._saved_features is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = self._saved_features
		super().tearDown()

	def test_a_plain_employee_still_cannot_open_the_directory_at_all(self):
		"""**The half of Surbhi's decision 4 that is NOT built, asserted so it
		cannot be mistaken for done.**

		She said the directory is *"for employees too"*. Today
		`get_staff_list` refuses any caller with no HR entitlement -
		`permitted_employee_filters()` returns `NO_EMPLOYEES` for a plain
		employee and the endpoint refuses before it reads anything.

		Adding the **field** was the small half and it is done. Opening the
		**audience** is the other half, and it needs a scope decision that is
		Surbhi's, not mine: does a shop assistant see their own store, or their
		whole company? Those are very different directories, and guessing
		would widen visibility as a side effect - which is the one thing this
		wave is not allowed to do.

		So this test pins today's behaviour, and it is expected to be REPLACED
		by a test of the new scope once that is decided - not deleted.
		"""
		self.as_user(self.rahul_user)
		with self.assertRaises(frappe.PermissionError):
			staff_api.get_staff_list()

	def test_the_payload_carries_the_work_email_and_not_the_personal_one(self):
		"""Searched recursively over the real payload, for values that are
		really in the database.

		Driven as **Priya**, who is HR, because a plain employee cannot open
		this endpoint at all yet (see the test above). What is under test here
		is which FIELDS the rows carry, and that is the same for every caller.
		"""
		self.as_user(self.priya_user)
		out = staff_api.get_staff_list()
		self.assertTrue(out.get("rows"),
		                "the staff list came back empty, so this proves nothing")
		self.assertTrue(find_value(out, WORK_EMAIL),
		                "the work email did not reach the directory at all")
		self.assertEqual([], find_value(out, PERSONAL_EMAIL),
		                 "a personal email reached the staff directory")
		self.assertEqual([], find_value(out, FORBIDDEN_VALUES["cell_number"]),
		                 "a personal mobile number reached the staff directory")
		self.assertEqual([], find_key(out, "cell_number"))
		self.assertEqual([], find_key(out, "personal_email"))

	def test_no_phone_number_ships_because_the_field_does_not_exist(self):
		"""The stop condition, asserted rather than described.

		If somebody later adds a work-phone custom field, this test does not
		fail - it is not a ban on work phones. What it bans is the PERSONAL
		one being used as a substitute, which is what would have happened if
		"contact details are in" had been read as "whatever contact fields
		exist".
		"""
		joined = " ".join(staff_api.ROW_FIELDS)
		self.assertNotIn("cell_number", joined)
		self.assertIn("company_email", joined)
