"""078 - the four lists are access-granting settings, and HR cannot change them.

US-28, US-30, N3. The point of this file is the negative half: at DTC the
Positions audience IS HR Manager, so if an HR Manager could change what a
Positions reader sees, the audience would be able to widen its own view. That
is the whole of conflict 1 in the spec, and the reason the tick is NOT a Check
on `Employee Document Type` - that doctype ships `write: 1` to HR Manager.
"""

import frappe
import hrms.alvoraa_org_structure.settings as org_settings

from alvoraa_portal import people_settings
from alvoraa_portal.tests import fixtures_078 as fx
from alvoraa_portal.tests.fixtures_045 import Wave4Base, own_user

# The three LIST keys plus the email switch. The joiner's own five periods and
# its switch are asserted in `test_joiner_078`, where the rules that read them
# live - `alvoraa_joiner_retention_days` is gone, replaced by counsel's two
# periods on 29 Oct 2026.
KEYS = ("alvoraa_positions_profile_fields", "alvoraa_positions_document_types",
        "alvoraa_my_profile_fields", "alvoraa_photo_in_emails")


class _Base(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.p = fx.people()
		cls.sm_user = own_user("s078sm", ("Employee", "System Manager"))

	def tearDown(self):
		frappe.set_user("Administrator")
		fx.clear_lists()
		super().tearDown()


class TestTheyAreAccessGranting(_Base):
	def test_they_are_all_in_the_access_granting_set(self):
		"""So they inherit System-Manager-only, the logged refusal and the
		Version row without any of it being written a second time."""
		for key in KEYS:
			with self.subTest(key=key):
				self.assertIn(key, org_settings.ACCESS_GRANTING)
				self.assertIn(key, org_settings.DEFAULTS)
				self.assertIn(key, org_settings.LABELS)

	def test_they_ship_empty_or_off(self):
		"""The safest value at every existing tenant: nothing a tenant sees
		changes until a System Manager ticks something. It is also the rollback
		- three levers, all data, none needing a release."""
		for key in KEYS:
			with self.subTest(key=key):
				# "" for the lists, 0 for the switch. Both are "nothing yet".
				self.assertIn(org_settings.DEFAULTS[key], ("", 0))

	def test_they_are_logged_under_their_own_rule_id(self):
		"""Slice 012's four keys are SEC-18; these four are 078-SEC-5. One grep
		must not conflate them - plain SEC-17 and SEC-18 already mean field
		rights and org-chart access in this codebase."""
		# Each key is logged under the rule it actually serves, not under one
		# blanket id: the three lists and the switch are access decisions
		# (078-SEC-5), and the email tick is about who sees a face, which is
		# PRIV-1's whole subject. A reviewer grepping either id should find the
		# right change.
		expected = {
			"alvoraa_positions_profile_fields": "078-SEC-5",
			"alvoraa_positions_document_types": "078-SEC-5",
			"alvoraa_my_profile_fields": "078-SEC-5",
			"alvoraa_photo_in_emails": "078-PRIV-1",
		}
		for key in KEYS:
			with self.subTest(key=key):
				self.assertEqual(org_settings.RULE_FOR_KEY.get(key), expected[key])
		self.assertEqual(org_settings.RULE_FOR_KEY.get("alvoraa_org_reach_up"), None)
		self.assertEqual(org_settings.DEFAULT_RULE, "SEC-18")

	def test_a_system_manager_change_writes_exactly_one_version_row(self):
		"""AC-94. Naming the old value and the new one, in the same transaction."""
		frappe.set_user(self.sm_user)
		before = frappe.get_all("Version", filters={
			"ref_doctype": "DefaultValue",
			"docname": "alvoraa_positions_profile_fields"}, pluck="name")
		people_settings.set_people_setting(key="alvoraa_positions_profile_fields",
		                                   value="designation,branch")
		rows = frappe.get_all("Version", filters={
			"ref_doctype": "DefaultValue",
			"docname": "alvoraa_positions_profile_fields"},
			fields=["name", "owner", "data"])
		new = [r for r in rows if r.name not in before]
		self.assertEqual(len(new), 1)
		self.assertEqual(new[0].owner, self.sm_user)
		self.assertIn("designation,branch", new[0].data)

	def test_a_value_set_straight_into_defaultvalue_writes_no_version_row(self):
		"""AC-97. A default that was never deliberately set has no history, and
		that is exactly why "a Version row exists" was a usable precondition.

		078-PRIV-7 USED to depend on this: the joiner form could not be switched
		on until somebody had set a retention period on purpose, proved by a
		Version row. Counsel answered the question that gate existed for on
		29 October 2026, so the gate is gone - but the property it rested on is
		still true and still worth pinning, because it is what makes every
		access-granting change attributable a year later.
		"""
		key = "alvoraa_positions_document_types"
		before = frappe.get_all("Version", filters={
			"ref_doctype": "DefaultValue", "docname": key}, pluck="name")
		frappe.db.set_default(key, "Aadhaar card")
		frappe.db.commit()
		after = frappe.get_all("Version", filters={
			"ref_doctype": "DefaultValue", "docname": key}, pluck="name")
		self.assertEqual(sorted(before), sorted(after))


class TestWhatItRefuses(_Base):
	def test_an_hr_manager_is_refused_on_every_one_of_them(self):
		"""N3, AC-93. **This is the one that matters at DTC**, where the
		Positions audience IS HR Manager: without it the audience could widen
		its own view."""
		frappe.set_user(self.p["hr_wide_user"])
		for key in KEYS:
			with self.subTest(key=key):
				with self.assertRaises(frappe.PermissionError):
					people_settings.set_people_setting(key=key, value="designation")

	def test_an_hr_manager_cannot_even_read_the_card(self):
		"""AC-96: the whole card is absent, not greyed - so the endpoint behind
		it refuses rather than returning a read-only view."""
		frappe.set_user(self.p["hr_wide_user"])
		with self.assertRaises(frappe.PermissionError):
			people_settings.get_people_settings()

	def test_an_off_list_field_is_refused_at_the_setter(self):
		"""AC-22, AC-51. Refused, not silently dropped: "a setting that
		silently does nothing is how a tenant comes to believe a field is
		editable"."""
		frappe.set_user(self.sm_user)
		for value in ("designation,bank_ac_no", "date_of_birth", "ctc",
		              "designation,pan_number"):
			with self.subTest(value=value):
				with self.assertRaises(frappe.PermissionError):
					people_settings.set_people_setting(
						key="alvoraa_positions_profile_fields", value=value)

	def test_a_my_profile_tick_outside_the_six_is_refused(self):
		frappe.set_user(self.sm_user)
		with self.assertRaises(frappe.PermissionError):
			people_settings.set_people_setting(key="alvoraa_my_profile_fields",
			                                   value="cell_number,date_of_birth")

	def test_a_key_that_is_not_one_of_the_four_is_refused(self):
		frappe.set_user(self.sm_user)
		for key in ("alvoraa_org_reach_up", "max_file_size", "", None, 7):
			with self.subTest(key=key):
				with self.assertRaises(frappe.PermissionError):
					people_settings.set_people_setting(key=key, value="1")

	def test_the_link_lifetime_must_be_a_number_of_days(self):
		"""Surbhi's decision of 31 Oct 2026: the invite link's lifetime is a
		setting, seven days by default. A BLANK is refused rather than read as
		"for ever" - a link with no expiry is the thing the whole token design
		exists to avoid."""
		frappe.set_user(self.sm_user)
		for value in ("0", "", "-1", "for ever", "91", "7 days", "1.5"):
			with self.subTest(value=value):
				with self.assertRaises(frappe.PermissionError):
					people_settings.set_people_setting(
						key="alvoraa_joiner_link_days", value=value)
		people_settings.set_people_setting(key="alvoraa_joiner_link_days",
		                                   value="30")
		self.assertEqual(frappe.db.get_default("alvoraa_joiner_link_days"), "30")

	def test_employee_document_type_has_no_show_in_positions_field(self):
		"""AC-95, and the whole of conflict 1. `Employee Document Type` grants
		HR Manager `write: 1`, so a Check there would be editable in Desk by
		exactly the role the card excludes - and at DTC that role is the
		Positions audience. The reason is a permission row, not taste."""
		meta = frappe.get_meta("Employee Document Type")
		self.assertFalse(meta.has_field("show_in_positions"))
		self.assertFalse(meta.has_field("alvoraa_show_in_positions"))
		# And the permission row that is the reason is still what it was.
		self.assertTrue(frappe.db.exists("DocPerm", {
			"parent": "Employee Document Type", "role": "HR Manager", "write": 1})
			or frappe.db.exists("Custom DocPerm", {
				"parent": "Employee Document Type", "role": "HR Manager", "write": 1}),
			"if HR Manager no longer holds write here, conflict 1 can be revisited")


class TestTheAudienceFigure(_Base):
	def test_it_counts_people_and_names_the_roles(self):
		"""AC-98, AC-84. On the PP Jewellers copy five accounts hold HR Manager
		and three of them are real people, so "7 people" had to mean seven
		people or the sentence beside it is a lie. And the ROLES are named, not
		only counted - with one-click tag removal refused, that line is the only
		automatic detection of a widening left."""
		frappe.set_user(self.sm_user)
		out = people_settings.position_readers()
		self.assertIsInstance(out["people"], int)
		self.assertTrue(out["roles"], "some role must hold Read on Alvoraa Position")
		self.assertNotIn("Administrator", frappe.as_json(out))
		self.assertNotIn("Guest", out["roles"])

	def test_the_names_behind_the_figure_are_system_manager_only(self):
		frappe.set_user(self.p["hr_wide_user"])
		with self.assertRaises(frappe.PermissionError):
			people_settings.who_can_open_positions()


class TestPhotographsInEmails(_Base):
	"""Counsel, 29 October 2026: the employer must be able to stop photographs
	going out in company-wide mail **without** turning off the photograph
	feature and without turning off the reminders.

	This is the widest reach a photograph has in the product and the only one
	the person in it cannot see, cannot check and cannot recall. `hrms` puts the
	photograph's URL straight into the mail body, and
	`send_work_anniversary_reminders` is switched on on dev - so the gap was
	live, not theoretical.
	"""

	def test_it_is_off_unless_somebody_ticks_it_on(self):
		"""A changed default, said out loud. Nothing visible changes on the day
		this ships, because no employee at any tenant has a photograph."""
		self.assertEqual(org_settings.DEFAULTS["alvoraa_photo_in_emails"], 0)
		self.assertFalse(people_settings.photo_in_emails())

	def test_a_system_manager_can_tick_it_on(self):
		frappe.set_user(self.sm_user)
		people_settings.set_people_setting(key="alvoraa_photo_in_emails", value="1")
		self.assertTrue(people_settings.photo_in_emails())

	def test_an_hr_manager_cannot(self):
		"""It decides whether a face goes to every colleague, so it belongs in
		the access-granting set like the other five."""
		self.assertIn("alvoraa_photo_in_emails", org_settings.ACCESS_GRANTING)
		frappe.set_user(self.p["hr_wide_user"])
		with self.assertRaises(frappe.PermissionError):
			people_settings.set_people_setting(key="alvoraa_photo_in_emails", value="1")

	def test_only_0_or_1_can_be_saved(self):
		"""A typo must not read as "on"."""
		frappe.set_user(self.sm_user)
		for bad in ("", "yes", "2", "true", "-1"):
			with self.subTest(bad=bad):
				with self.assertRaises(frappe.PermissionError):
					people_settings.set_people_setting(
						key="alvoraa_photo_in_emails", value=bad)

	def test_it_fails_closed(self):
		"""An unreadable setting means NO photograph in the mail. A missing face
		in a birthday email is nobody noticing; the other answer is a face in
		every colleague's inbox."""
		real = org_settings.get
		org_settings.get = lambda key: (_ for _ in ()).throw(RuntimeError("boom"))
		try:
			self.assertFalse(people_settings.photo_in_emails())
		finally:
			org_settings.get = real

	def test_our_own_copies_of_the_two_templates_win_the_search(self):
		"""Frappe's Jinja loader searches installed apps in REVERSED install
		order, and `alvoraa_portal` is installed after `hrms` on every site - so
		our copies are found first. Proved by asking the loader, not assumed."""
		import frappe.utils.jinja as fj

		for name in ("birthday_reminder", "anniversary_reminder"):
			with self.subTest(template=name):
				src = fj.get_jenv().loader.get_source(
					fj.get_jenv(), f"templates/emails/{name}.html")[0]
				self.assertIn("photo_in_emails()", src,
				              f"hrms' own {name}.html won the search - our "
				              f"override is not being used")
				self.assertIn("Slice 078", src)

	def test_the_templates_ask_before_putting_a_face_in_the_mail(self):
		"""The one changed condition, in both files, read from the real source."""
		import os

		import alvoraa_portal

		base = os.path.join(os.path.dirname(alvoraa_portal.__file__),
		                    "templates", "emails")
		for name in ("birthday_reminder", "anniversary_reminder"):
			with self.subTest(template=name):
				text = open(os.path.join(base, f"{name}.html"),
				            encoding="utf-8").read()
				self.assertIn("{% if person.image and photo_in_emails() %}", text)
				# And the initials block upstream already draws is still there,
				# so the email looks like itself with the setting off.
				self.assertIn("get_abbr(person.name)", text)

	def test_the_jinja_method_is_registered(self):
		"""A template calling an unregistered method renders nothing and says
		nothing, so the email would silently lose every face - or every face
		would silently come back."""
		from alvoraa_portal import hooks

		self.assertIn("alvoraa_portal.people_settings.photo_in_emails",
		              hooks.jinja["methods"])
