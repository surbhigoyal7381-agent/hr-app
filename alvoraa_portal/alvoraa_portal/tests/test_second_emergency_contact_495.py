"""ALV-495: a second emergency contact on the joiner form, and on Employee.

Surbhi's decision of 28 November 2026, approved with her labels. Three new
columns the joiner may fill in, optional, carried onto the employee record when
they are hired.

**The test this file exists for is `test_every_column_the_form_can_write_is_erased`.**
Everything else proves the three fields reach the screens they should. That one
proves the retention promise still holds, and it is written from
`COLUMN_FOR_TICK` rather than from a list of names, so **a tenth column added
later cannot escape it either.** `strip_personal_fields` loops over
`JOINER_FIELDS`; a column on the form and not on that tuple would survive an
erasure we have already told the person happened, and nothing else in the suite
would have noticed.

No site fixture: only `status` and `invited_by` are mandatory on the submission,
so these run on an empty site.
"""

import frappe

from alvoraa_portal import joiner_to_employee as j2e
from alvoraa_portal import employee_field_rights as efr
from alvoraa_portal import second_emergency_contact as sec
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission.alvoraa_joiner_submission import (
	COLUMN_FOR_TICK,
	JOINER_FIELDS,
	erase,
)
from alvoraa_portal.employee_field_rights import LEVEL_1, LEVEL_2, LEVEL_3, SELF_EDITABLE
from frappe.tests import IntegrationTestCase
import hrms.alvoraa_org_structure.people_fields as people_fields

DOCTYPE = "Alvoraa Joiner Submission"

# A different person in each set, so crossing the two over is visible.
FIRST = {"emergency_contact_name": "Sunita Kumar",
         "emergency_relation": "Sister",
         "emergency_phone": "9822223333"}
SECOND = {"second_emergency_contact_name": "Vijay Kumar",
          "second_emergency_relation": "Brother",
          "second_emergency_phone": "9833334444"}


class TestTheRetentionPromiseStillHolds(IntegrationTestCase):
	"""The erasure half. This is the file's reason to exist."""

	def setUp(self):
		frappe.set_user("Administrator")
		self._made = []

	def tearDown(self):
		for name in self._made:
			if frappe.db.exists(DOCTYPE, name):
				frappe.delete_doc(DOCTYPE, name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _row(self, **extra):
		row = frappe.get_doc({
			"doctype": DOCTYPE, "status": "Submitted",
			"invited_by": "Administrator", "full_name": "Rakesh Kumar",
			"mobile": "9811112222", "personal_email": "rakesh495@example.com",
			"current_address": "12 Nehru Road, Pune",
			**FIRST, **SECOND, **extra,
		}).insert(ignore_permissions=True)
		self._made.append(row.name)
		frappe.db.commit()
		return row

	def test_every_column_the_form_can_write_is_erased(self):
		"""**Written from the map, not from a list of names.** Add a tenth
		column to `COLUMN_FOR_TICK` and forget `JOINER_FIELDS`, and this is
		what fails - which is the only reason the erasure can be trusted a year
		from now."""
		missing = sorted(set(COLUMN_FOR_TICK.values()) - set(JOINER_FIELDS))
		self.assertEqual(missing, [], (
			"these columns can be filled in on the joiner form but are NOT in "
			"JOINER_FIELDS, so strip_personal_fields leaves them behind and the "
			"erasure is a lie: " + ", ".join(missing)))
		# Not vacuous: the map must actually have the new columns in it.
		for column in SECOND:
			with self.subTest(column=column):
				self.assertIn(column, set(COLUMN_FOR_TICK.values()))

	def test_erase_really_clears_the_second_contact_in_the_database(self):
		"""The real `erase`, then read the columns back off the table rather
		than off the document in memory."""
		row = self._row()
		for column, value in {**FIRST, **SECOND}.items():
			self.assertEqual(frappe.db.get_value(DOCTYPE, row.name, column), value)

		self.assertTrue(erase(row.name, why="ALV-495 test"))

		left = frappe.db.get_value(
			DOCTYPE, row.name, list(SECOND) + list(FIRST), as_dict=True)
		still_there = {k: v for k, v in left.items() if v}
		self.assertEqual(still_there, {}, (
			"erase left emergency contact details on the row: "
			+ ", ".join(sorted(still_there))))

	def test_the_erased_values_are_not_left_in_the_history(self):
		"""079-PRIV-2. The doctype carries `track_changes: 1`, so a careless
		save would write the OLD value into `tabVersion` - the very details we
		have just said were deleted."""
		row = self._row()
		erase(row.name, why="ALV-495 test")
		blob = " ".join(
			v or "" for v in frappe.get_all(
				"Version", filters={"ref_doctype": DOCTYPE, "docname": row.name},
				pluck="data"))
		for value in SECOND.values():
			with self.subTest(value=value):
				self.assertNotIn(value, blob)


class TestTheThreeFieldsReachTheRightScreens(IntegrationTestCase):
	def test_they_are_on_the_list_hr_can_tick(self):
		self.assertEqual(len(people_fields.MY_PROFILE_WRITE_FIELDS), 9)
		for field in sec.FIELDS:
			with self.subTest(field=field):
				self.assertIn(field, people_fields.MY_PROFILE_WRITE_FIELDS)

	def test_the_joiner_keys_still_follow_that_list_by_identity(self):
		"""079 AC-104. If this ever became a copy, widening My Profile would
		stop reaching the joiner form and the two would drift apart."""
		for key in ("alvoraa_joiner_fields", "alvoraa_joiner_required_fields",
		            "alvoraa_my_profile_required_fields"):
			with self.subTest(key=key):
				self.assertIs(people_fields.LIST_KEYS[key],
				              people_fields.MY_PROFILE_WRITE_FIELDS)

	def test_each_tick_has_a_column_to_write_to(self):
		for field in sec.FIELDS:
			with self.subTest(field=field):
				self.assertIn(field, COLUMN_FOR_TICK)

	def test_no_positions_tick_can_ever_reach_next_of_kin(self):
		"""The same refusal the FIRST emergency contact already has. A
		colleague's org-chart page is not where next of kin belongs."""
		for field in sec.FIELDS:
			with self.subTest(field=field):
				self.assertIn(field, people_fields.NEVER)
				self.assertTrue(people_fields.is_denied(field))
				self.assertNotIn(field, people_fields.POSITIONS_PROFILE_FIELDS)

	def test_the_manager_list_is_untouched(self):
		"""Not an oversight - a decision. ALV-495 did not widen what a manager
		sees of a team member, and five is still five."""
		self.assertEqual(len(people_fields.MANAGER_SEES_FIELDS), 5)
		for field in sec.FIELDS:
			with self.subTest(field=field):
				self.assertNotIn(field, people_fields.MANAGER_SEES_FIELDS)

	def test_the_employee_may_edit_them_later(self):
		"""Surbhi's second decision of 28 November 2026: "yes employee can edit
		later".

		**`SELF_EDITABLE` is the control, and being absent from the locked
		lists is not enough.** ALV-266's rule is the other way round - every
		Employee field that is NOT on `SELF_EDITABLE` is forced to level 2, in
		two places (`lock_fields` and the `Custom Field` after_insert hook). The
		first version of this test asserted only the absences, passed, and the
		three fields were created at level 2 anyway. That is why the membership
		assertion comes first."""
		for field in sec.FIELDS:
			with self.subTest(field=field):
				self.assertIn(field, SELF_EDITABLE)
				self.assertNotIn(field, LEVEL_1)
				self.assertNotIn(field, LEVEL_2)
				self.assertNotIn(field, LEVEL_3)


class TestTheColumnsExistOnEmployee(IntegrationTestCase):
	def _as_if_the_release_had_not_landed(self):
		"""Take the three fields off this site, Property Setters included.

		**Not tidiness - the precondition.** The levels are decided when the
		Custom Field is INSERTED (`employee_field_rights` runs on
		`Custom Field.after_insert`), so a site where these three already exist
		from an earlier run cannot show what a real deploy does. Worse, a
		level-2 Property Setter left from such a run is never lowered again:
		`lock_fields` only ever raises, and it skips `SELF_EDITABLE` fields
		entirely. Starting clean is the only way this test measures the code
		rather than the site's history.
		"""
		for field in sec.FIELDS:
			for name in frappe.get_all(
					"Property Setter",
					filters={"doc_type": "Employee", "field_name": field},
					pluck="name"):
				frappe.delete_doc("Property Setter", name, force=True,
				                  ignore_permissions=True)
			cf = frappe.db.get_value("Custom Field",
			                         {"dt": "Employee", "fieldname": field})
			if cf:
				frappe.delete_doc("Custom Field", cf, force=True,
				                  ignore_permissions=True)
		frappe.clear_cache(doctype="Employee")
		frappe.db.commit()

	def test_after_migrate_creates_all_three_and_runs_twice_safely(self):
		"""`create_custom_fields` writes only what is missing, so the second
		call must change nothing rather than raise."""
		self._as_if_the_release_had_not_landed()
		self.assertTrue(sec.after_migrate())
		before = frappe.db.count("Custom Field", {"dt": "Employee"})
		self.assertTrue(sec.after_migrate())
		self.assertEqual(frappe.db.count("Custom Field", {"dt": "Employee"}), before)

		# **Both halves, in the order `hooks.py` runs them.** Creating the field
		# leaves it at level 2; `apply` is what puts a SELF_EDITABLE field back
		# to 0. Asserting the level without this would be asserting against a
		# half-finished migrate.
		efr.apply()
		frappe.clear_cache(doctype="Employee")
		meta = frappe.get_meta("Employee")
		for field in sec.FIELDS:
			with self.subTest(field=field):
				df = meta.get_field(field)
				self.assertIsNotNone(df, f"{field} is not on Employee")
				self.assertEqual(df.fieldtype, "Data")
				self.assertEqual(df.permlevel or 0, 0)

	def test_the_prefill_carries_the_second_contact_across(self):
		"""What makes "when they become employees" true. The keys are
		`Employee`'s own column names, which is what the new-employee dialog
		writes straight onto the record."""
		row = frappe.get_doc({
			"doctype": DOCTYPE, "status": "Submitted",
			"invited_by": "Administrator", "full_name": "Rakesh Kumar",
			**SECOND,
		}).insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, DOCTYPE, row.name,
		                force=True, ignore_permissions=True)
		got = j2e.details_for_a_new_employee(submission=row.name)
		self.assertEqual(got["alvoraa_second_person_to_be_contacted"], "Vijay Kumar")
		self.assertEqual(got["alvoraa_second_relation"], "Brother")
		self.assertEqual(got["alvoraa_second_emergency_phone_number"], "9833334444")
		# and the first set is not confused with the second
		self.assertIsNone(got["person_to_be_contacted"])
