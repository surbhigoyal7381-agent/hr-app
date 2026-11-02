"""Slice 080: "Alternative number" - who writes it, who sees it, and that it exists.

Surbhi's decision of 2 November 2026. Every test name carries `alt080`, so a
merge that drops the feature fails CI rather than quietly shipping a field with
no permission level on it.

**The one that matters is the permission level.** A Custom Field on `Employee`
with no level is level 0 - "the employee's own details" - which means the
EMPLOYEE can write it over the REST API. This field is a number the company
hands out, so HR writes it and the person does not. That is level 2, and it
reaches the field by two different routes which are tested separately:

  * `employee_field_rights.lock_fields()`, inside `apply()`, which runs on every
    migrate AND on install - the fresh-site path;
  * `lock_new_custom_field`, the `Custom Field` `after_insert` hook - the
    created-at-run-time path.

Level 1 would have been the other wrong answer: it is HR Manager only for READ
as well as write, and would hide the number from the colleagues it exists for.
"""

import frappe
from frappe.tests import IntegrationTestCase

import hrms.alvoraa_org_structure.people_fields as people_fields

from alvoraa_portal import alternative_number as alt
from alvoraa_portal import employee_field_rights as ef
from alvoraa_portal import positions_profile, staff_api

# The module's own name for it, not a second copy - a test that spells the
# fieldname out again would still pass after a rename.
FIELD = alt.FIELD
NUMBER = "+91 98765 00080"
HR_NUMBER = "+91 98765 00081"


def _level(fieldname):
	df = frappe.get_meta("Employee").get_field(fieldname)
	return df.permlevel if df else None


class AltNumberExists080(IntegrationTestCase):
	"""The field itself, and the words on it."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		alt.after_migrate()
		frappe.clear_cache(doctype="Employee")

	def test_alt080_the_field_is_on_employee_with_her_label_and_her_help_text(self):
		"""Her words, word for word. She rejected "Work phone"."""
		df = frappe.get_meta("Employee").get_field(FIELD)
		self.assertIsNotNone(df, "the field was never created")
		self.assertEqual(df.label, "Alternative number")
		self.assertEqual(
			df.description,
			"A number colleagues may use to reach this person. "
			"Everyone in the company can see it.")
		# A dialable number, not free text - the same shape as `cell_number`.
		self.assertEqual(df.fieldtype, "Data")
		self.assertEqual(df.options, "Phone")

	def test_alt080_it_is_wired_into_both_hook_lists_not_a_patch(self):
		"""**A patch would never run on a new install**, so a new tenant would
		have the tick and the directory column reading a column that is not
		there. Both hook lists, or this field does not exist somewhere."""
		entry = "alvoraa_portal.alternative_number.after_migrate"
		self.assertIn(entry, frappe.get_hooks("after_migrate"))
		self.assertIn(entry, frappe.get_hooks("after_install"))
		self.assertFalse(
			[p for p in frappe.get_hooks("patches") or [] if "alternative_number" in str(p)],
			"a patch as well as the hooks is a third path to the same field")


class AltNumberLevel080(IntegrationTestCase):
	"""Level 2, by both routes. Two paths, two tests, as asked."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		alt.after_migrate()
		ef.apply()
		frappe.clear_cache(doctype="Employee")

	def test_alt080_the_fieldname_is_on_level_2_and_not_on_level_1(self):
		"""Without this line `lock_new_custom_field` gives it level 0 - readable
		by all and writable by the EMPLOYEE, which is the wrong half of her
		decision. Level 1 is the other wrong answer: HR Manager only for read
		as well, so colleagues would not see it at all."""
		self.assertIn(FIELD, ef.LEVEL_2)
		self.assertNotIn(FIELD, ef.LEVEL_1)

	def test_alt080_a_fresh_site_has_it_at_level_2_through_lock_fields(self):
		"""The fresh-install path: `apply()` runs on install as well as migrate,
		and `lock_fields()` is what sets the level there. Proved by taking the
		Property Setter away and running the install path again - a check that
		cannot fail proves nothing."""
		frappe.db.delete("Property Setter", {"doc_type": "Employee",
		                                     "field_name": FIELD,
		                                     "property": "permlevel"})
		frappe.clear_cache(doctype="Employee")
		self.assertEqual(_level(FIELD), 0, "the level was not really taken away")
		try:
			ef.lock_fields()
			frappe.clear_cache(doctype="Employee")
			self.assertEqual(_level(FIELD), 2)
		finally:
			ef.apply()
			frappe.clear_cache(doctype="Employee")

	def test_alt080_a_field_made_at_run_time_is_locked_by_the_after_insert_hook(self):
		"""The second path: the `Custom Field` `after_insert` hook. Removed and
		made again through `create_custom_fields`, which is what the hook on a
		live site actually sees."""
		self.assertIn("alvoraa_portal.employee_field_rights.lock_new_custom_field",
		              frappe.get_hooks("doc_events")["Custom Field"]["after_insert"])
		frappe.db.delete("Property Setter", {"doc_type": "Employee",
		                                     "field_name": FIELD,
		                                     "property": "permlevel"})
		for name in frappe.get_all("Custom Field",
		                           filters={"dt": "Employee", "fieldname": FIELD},
		                           pluck="name"):
			frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
		frappe.clear_cache(doctype="Employee")
		self.assertIsNone(_level(FIELD), "the field was not really taken away")
		try:
			alt.after_migrate()
			frappe.clear_cache(doctype="Employee")
			self.assertEqual(_level(FIELD), 2, "the after_insert hook did not lock it")
		finally:
			alt.after_migrate()
			ef.apply()
			# The column's DDL is committed, so the class-end rollback must not
			# bring the deleted record back without it.
			frappe.db.commit()
			frappe.clear_cache(doctype="Employee")


class AltNumberWhoWrites080(IntegrationTestCase):
	"""HR fills it in; the employee cannot. Through a real save, as each person."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		alt.after_migrate()
		ef.apply()
		frappe.clear_cache(doctype="Employee")
		cls.company = _company()
		cls.hr = _user("hr080", "Employee", "HR User")
		cls.staff = _user("staff080", "Employee", "Employee Self Service")
		cls.staff_emp = _employee("Staff080", cls.company, cls.staff)
		cls.hr_emp = _employee("Hr080", cls.company, cls.hr)
		frappe.get_doc("User", cls.staff).add_roles("Employee Self Service")
		# ERPNext ties every login to its own Employee by User Permission; HR
		# people work across records, so a tenant switches that off for them.
		frappe.db.delete("User Permission", {"user": cls.hr})
		if not frappe.db.exists("User Permission", {"user": cls.staff,
		                                            "allow": "Employee",
		                                            "for_value": cls.staff_emp}):
			frappe.get_doc({"doctype": "User Permission", "user": cls.staff,
			                "allow": "Employee",
			                "for_value": cls.staff_emp}).insert(ignore_permissions=True)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")

	def _save_as(self, user, employee, value):
		frappe.set_user(user)
		doc = frappe.get_doc("Employee", employee)
		doc.set(FIELD, value)
		doc.save()
		frappe.set_user("Administrator")
		return frappe.get_doc("Employee", employee)

	def test_alt080_an_employee_cannot_write_their_own_alternative_number(self):
		"""**The door that matters.** Frappe puts the old value back rather than
		raising, so the assertion is on the stored value and not on an
		exception. Not hiding the field on a screen - that is not a permission."""
		frappe.db.set_value("Employee", self.staff_emp, FIELD, "",
		                    update_modified=False)
		frappe.clear_document_cache("Employee", self.staff_emp)
		after = self._save_as(self.staff, self.staff_emp, NUMBER)
		self.assertFalse(after.get(FIELD),
		                 "an employee wrote their own alternative number")

	def test_alt080_hr_writes_a_colleagues_alternative_number(self):
		after = self._save_as(self.hr, self.staff_emp, HR_NUMBER)
		self.assertEqual(after.get(FIELD), HR_NUMBER)

	def test_alt080_hr_cannot_write_it_on_their_own_record(self):
		"""`refuse_own_locked_change` already covers every high-permlevel field,
		so this field is covered with no new rule - asserted, because "it
		should be covered" and "it is covered" are different statements."""
		frappe.set_user(self.hr)
		doc = frappe.get_doc("Employee", self.hr_emp)
		doc.set(FIELD, NUMBER)
		with self.assertRaises(frappe.PermissionError):
			doc.save()
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value("Employee", self.hr_emp, FIELD))


class AltNumberOnTheScreens080(IntegrationTestCase):
	"""The Positions tick and the directory payload."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		alt.after_migrate()
		frappe.clear_cache(doctype="Employee")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_default(positions_profile.PROFILE_KEY, "")
		frappe.db.commit()

	def test_alt080_it_is_the_eleventh_positions_field_and_nothing_else_moved(self):
		"""**The regression that would matter.** Widening My Profile would reach
		the pre-onboarding form for free, because 079 AC-104 binds the three
		joiner keys to `MY_PROFILE_WRITE_FIELDS` by identity rather than by
		copy. So the assertion is identity, not equality."""
		self.assertIn(FIELD, people_fields.POSITIONS_PROFILE_FIELDS)
		self.assertEqual(people_fields.POSITIONS_PROFILE_FIELDS[-1], FIELD)

		self.assertEqual(people_fields.MY_PROFILE_WRITE_FIELDS, (
			"cell_number", "personal_email", "current_address",
			"person_to_be_contacted", "relation", "emergency_phone_number"))
		self.assertNotIn(FIELD, people_fields.MY_PROFILE_WRITE_FIELDS)
		for key in ("alvoraa_joiner_fields", "alvoraa_joiner_required_fields",
		            "alvoraa_my_profile_required_fields"):
			with self.subTest(key=key):
				self.assertIs(people_fields.LIST_KEYS[key],
				              people_fields.MY_PROFILE_WRITE_FIELDS)

		# It is meant to be seen, so it is NOT on the deny list - said out loud,
		# because "we forgot" and "we decided" look the same from here.
		self.assertNotIn(FIELD, people_fields.NEVER)
		self.assertFalse(people_fields.is_denied(FIELD))

	def test_alt080_it_is_off_until_a_tenant_ticks_it(self):
		frappe.db.set_default(positions_profile.PROFILE_KEY, "")
		frappe.db.commit()
		self.assertNotIn(FIELD, positions_profile.ticked_fields())

		frappe.db.set_default(positions_profile.PROFILE_KEY,
		                      "designation," + FIELD)
		frappe.db.commit()
		self.assertEqual(positions_profile.ticked_fields(), ("designation", FIELD))

	def test_alt080_the_reader_still_refuses_an_off_list_name_written_direct(self):
		"""`frappe.db.set_default` bypasses the setter, its refusal and its
		Version row. The reader has to produce nothing anyway - the eleventh
		field arriving must not have opened that door."""
		frappe.db.set_default(positions_profile.PROFILE_KEY,
		                      FIELD + ",cell_number,bank_ac_no,date_of_birth")
		frappe.db.commit()
		self.assertEqual(positions_profile.ticked_fields(), (FIELD,))
		self.assertEqual(
			people_fields.off_list(positions_profile.PROFILE_KEY,
			                       FIELD + ",cell_number,bank_ac_no"),
			("bank_ac_no", "cell_number"))

	def test_alt080_it_is_in_the_directory_payload_beside_the_work_email(self):
		"""Asserted on the keys the row LEAVES with, not on the query, because
		the rows are built key by key from `ROW_KEYS`."""
		self.assertIn("alt_number", staff_api.ROW_KEYS)
		self.assertEqual(staff_api.ROW_KEYS.index("alt_number"),
		                 staff_api.ROW_KEYS.index("work_email") + 1)
		self.assertIn(FIELD + " as alt_number", staff_api.ROW_FIELDS)
		# And the personal mobile is still not there, which is the half of
		# "contact details are in" that was always the risk.
		self.assertNotIn("cell_number", " ".join(staff_api.ROW_FIELDS))


# ── fixtures ────────────────────────────────────────────────────────────────
#
# Deliberately this module's own company and people. A fixture that hires into a
# shared company changes every other test's data - the lesson slice 045 paid
# for, written down in `fixtures_045.py`.

COMPANY = "Alt080 Numbers Co"


def _company():
	if not frappe.db.exists("Company", COMPANY):
		if not frappe.db.exists("Warehouse Type", "Transit"):
			frappe.get_doc({"doctype": "Warehouse Type",
			                "name": "Transit"}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Company", "company_name": COMPANY,
		                "abbr": "A080", "default_currency": "INR",
		                "country": "India"}).insert(ignore_permissions=True)
	return COMPANY


def _user(label, *roles):
	email = f"alt080.{label}@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email,
		                "first_name": "Alt080" + label,
		                "send_welcome_email": 0}).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(*roles)
	return email


def _employee(label, company, user=None):
	name = frappe.db.get_value("Employee", {"first_name": label})
	if name:
		return name
	gender = frappe.db.get_value("Gender", {}, "name") or frappe.get_doc(
		{"doctype": "Gender", "gender": "Other"}).insert(ignore_permissions=True).name
	return frappe.get_doc({
		"doctype": "Employee", "first_name": label, "company": company,
		"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
		"gender": gender, "status": "Active", "user_id": user,
	}).insert(ignore_permissions=True).name
