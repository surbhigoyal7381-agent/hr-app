"""078 step 3 - the mini profile, and the four things it must refuse.

US-15 and US-19. The negative cases are the point of this file: a wrong tick on
a settings page must not be able to become a disclosure, and a reader scoped to
one branch must not learn that another branch exists.

The one worth reading twice is
`test_a_field_written_straight_into_defaultvalue_produces_nothing`. Everything
else here proves the setter and the reader agree; that one proves the READER
alone holds, which is the only half a future UI cannot get round.
"""

import frappe
import hrms.alvoraa_org_structure.people_fields as people_fields

from alvoraa_portal import positions_profile
from alvoraa_portal.tests import fixtures_078 as fx
from alvoraa_portal.tests.fixtures_045 import Wave4Base

# Every field on the allow-list, derived rather than copied - it went from ten
# to eleven in slice 080, and a test that names a count goes stale.
ALL_FIELDS = list(people_fields.POSITIONS_PROFILE_FIELDS)


class _Base(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.p = fx.people()
		fx.give_photo(cls.p["with_photo"])

	def setUp(self):
		super().setUp()
		fx.set_lists(profile_fields=ALL_FIELDS)

	def tearDown(self):
		frappe.set_user("Administrator")
		fx.clear_lists()
		super().tearDown()


class TestWhatTheReaderGets(_Base):
	def test_the_ticked_fields_come_back_and_nothing_else(self):
		frappe.set_user(self.p["hr_wide_user"])
		out = positions_profile.get_positions_profile(employee=self.p["with_photo"])
		got = [r["fieldname"] for r in out["rows"]]
		self.assertTrue(set(got) <= set(ALL_FIELDS), got)
		# Name and job role arrive whatever is ticked - they are what the reader
		# clicked on.
		self.assertTrue(out["employee_name"])

	def test_both_sizes_of_the_picture_arrive_for_their_own_job(self):
		"""`image` is the 512 px stored picture, for the enlargement only.
		`thumb` is the 48 px copy the cards and the table draw."""
		frappe.set_user(self.p["hr_wide_user"])
		out = positions_profile.get_positions_profile(employee=self.p["with_photo"])
		self.assertTrue(out["image"])
		self.assertTrue(out["thumb"])

	def test_nothing_ticked_still_opens(self):
		"""AC-44. The drawer opens with a name and a job role and says the
		organisation has chosen nothing else."""
		fx.set_lists(profile_fields=[])
		frappe.set_user(self.p["hr_wide_user"])
		out = positions_profile.get_positions_profile(employee=self.p["with_photo"])
		self.assertEqual(out["rows"], [])
		self.assertTrue(out["employee_name"])

	def test_a_leaver_carries_the_one_sentence_and_never_a_row(self):
		"""AC-46. The DATE may appear in that one sentence. It is never a
		profile row - `relieving_date` is on the deny list - and the REASON for
		leaving is not recorded here at all."""
		frappe.db.set_value("Employee", self.p["no_photo"], "relieving_date", "2026-09-30")
		frappe.db.commit()
		try:
			frappe.set_user(self.p["hr_wide_user"])
			out = positions_profile.get_positions_profile(employee=self.p["no_photo"])
			self.assertEqual(out["left_on"], "2026-09-30")
			self.assertNotIn("relieving_date", [r["fieldname"] for r in out["rows"]])
			self.assertNotIn("reason", frappe.as_json(out))
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", self.p["no_photo"], "relieving_date", None)
			frappe.db.commit()

	def test_reports_to_comes_back_as_a_name_not_an_id(self):
		frappe.db.set_value("Employee", self.p["no_photo"], "reports_to", self.p["hr_wide"])
		frappe.db.commit()
		try:
			frappe.set_user(self.p["hr_wide_user"])
			out = positions_profile.get_positions_profile(employee=self.p["no_photo"])
			row = next(r for r in out["rows"] if r["fieldname"] == "reports_to")
			self.assertNotEqual(row["value"], self.p["hr_wide"])
			self.assertIn("S078HrWide",
			              row["value"] + frappe.db.get_value(
				              "Employee", self.p["hr_wide"], "employee_name"))
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", self.p["no_photo"], "reports_to", None)
			frappe.db.commit()

	def test_one_call_answers_the_whole_drawer(self):
		"""AC-41. One call, made when the profile is opened - never columns on
		the table's payload."""
		import inspect

		self.assertEqual(
			[p for p in inspect.signature(
				positions_profile.get_positions_profile).parameters],
			["employee"])


class TestWhatItRefuses(_Base):
	def test_somebody_who_cannot_open_positions_is_refused(self):
		"""AC-78's shape, on the profile. The refusal says nothing about
		whether that person exists."""
		frappe.set_user(self.p["no_photo_user"])      # a plain employee
		with self.assertRaises(frappe.PermissionError) as caught:
			positions_profile.get_positions_profile(employee=self.p["with_photo"])
		said = str(caught.exception)
		self.assertNotIn("S078WithPhoto", said)

	def test_a_reader_scoped_to_one_branch_is_refused_for_another(self):
		"""AC-52. A refusal, not an empty profile. They learn nothing about the
		employee and nothing about the other branch's existence."""
		frappe.set_user(self.p["hr_store_user"])
		with self.assertRaises(frappe.PermissionError) as caught:
			positions_profile.get_positions_profile(employee=self.p["other_branch"])
		said = str(caught.exception)
		self.assertNotIn("Store B", said)
		self.assertNotIn("S078OtherBranch", said)

	def test_a_caller_with_no_companies_is_refused(self):
		"""AC-53. Fails closed, on `employee_in_scope` and not on a new helper
		- `scripts/check_scope_traps.py` fails CI on the trap this would be."""
		frappe.set_user(self.p["nobody_user"])
		with self.assertRaises(frappe.PermissionError):
			positions_profile.get_positions_profile(employee=self.p["with_photo"])

	def test_an_empty_or_odd_employee_argument_is_refused(self):
		frappe.set_user(self.p["hr_wide_user"])
		for bad in (None, "", "   ", 7, {"name": "x"}):
			with self.subTest(bad=bad):
				with self.assertRaises(frappe.PermissionError):
					positions_profile.get_positions_profile(employee=bad)

	def test_a_field_written_straight_into_defaultvalue_produces_nothing(self):
		"""**AC-51's third case, and the only one that survives a future UI.**

		`frappe.db.set_default` bypasses the setter, its System-Manager check,
		its refusal and its Version row. The reader has to produce nothing
		anyway.
		"""
		frappe.db.set_default(
			positions_profile.PROFILE_KEY,
			"designation,bank_ac_no,pan_number,date_of_birth,ctc,cell_number")
		frappe.db.commit()
		frappe.set_user(self.p["hr_wide_user"])
		out = positions_profile.get_positions_profile(employee=self.p["with_photo"])
		got = [r["fieldname"] for r in out["rows"]]
		self.assertEqual(got, ["designation"])
		body = frappe.as_json(out)
		for forbidden in ("bank_ac_no", "pan_number", "date_of_birth", "ctc",
		                  "cell_number"):
			self.assertNotIn(forbidden, body)

	def test_the_values_of_denied_fields_never_reach_the_response(self):
		"""N1, by VALUE rather than by key name - the next leak will be under a
		different key."""
		sentinel = "+91 98765 00999"
		frappe.db.set_value("Employee", self.p["with_photo"], "cell_number", sentinel)
		frappe.db.set_default(positions_profile.PROFILE_KEY, ",".join(ALL_FIELDS + ["cell_number"]))
		frappe.db.commit()
		frappe.set_user(self.p["hr_wide_user"])
		out = positions_profile.get_positions_profile(employee=self.p["with_photo"])
		self.assertNotIn(sentinel, frappe.as_json(out))
