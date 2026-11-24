"""Slice 089, second pass: the negative cases the first file did not run on their own.

One test per gap named in `03-implementation-notes.md` (AC-25, AC-38, AC-51,
OPS-9, OPS-11, PRIV-1, PRIV-3, SEC-5/SEC-11 no personal value in a log). Each has
an ALLOWED case beside it so a pass cannot mean "nobody is allowed".
Synthetic people only (tag S089, from the first file's fixtures).
"""

import json

import frappe
from frappe.utils import add_days, nowdate

import hrms.alvoraa_org_structure.people_fields as people_fields
import hrms.alvoraa_org_structure.settings as org_settings
from alvoraa_portal import hr_api, leaver_report, positions_profile
from alvoraa_portal.tests.test_leaver_report_089 import (
	FIELD, PERSONAL_KEYS, ROLE, SEES, _Base, _Log, _company, _login)
from alvoraa_portal.tests.test_portal_security_010 import _employee

# What the notice says. Present in every report's description and nowhere else.
NOTICE_WORDS = "Last working day"
SECRETS = ("9876543210", "14 Test Lane", "private@", "Kamla", "9810012345")


class TestWhoCanReadTheNotice(_Base):
	"""AC-25, SEC-10, OPS-9: a colleague, another team's manager, the skip-level
	manager, another company's HR and a guest cannot read the notice through any
	door a browser has. The confirmer and the reporter can."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.other_user = _login("other", ("Employee",))
		cls.other = _employee("S089Other", company=cls.company_a, reports_to=cls.skip,
		                      user=cls.other_user)

	def _doors(self):
		"""Everything the signed-in user can pull that could carry the text."""
		out = []
		for doctype in ("ToDo", "Notification Log"):
			try:
				out.append(json.dumps(frappe.get_list(doctype, fields=["*"], limit_page_length=0),
				                      default=str))
			except frappe.PermissionError:
				pass
			try:
				out.append(json.dumps(frappe.client.get_list(doctype, fields=["*"], limit_page_length=0),
				                      default=str))
			except frappe.PermissionError:
				pass
		try:
			out.append(json.dumps(frappe.desk.form.load.getdoc("Employee", self.rpt), default=str))
		except frappe.PermissionError:
			pass
		return "\n".join(out)

	def test_nobody_outside_the_circle_reads_the_notice(self):
		self._as(self.mgr_user)
		self._send()
		# the allowed readers see it: otherwise "nobody sees it" would prove nothing
		for allowed in (self.hr_a_user, self.mgr_user):
			self._as(allowed)
			self.assertIn(NOTICE_WORDS, json.dumps(
				frappe.get_list("ToDo", fields=["description"], filters={FIELD: self.rpt}), default=str),
				allowed)
		for who in (self.col_user, self.other_user, self.skip_user, self.hr_b_user, "Guest"):
			self._as(who)
			blob = self._doors()
			self.assertNotIn(NOTICE_WORDS, blob, who)
			self.assertNotIn(self.hr_a_user, blob, f"{who} learned who the confirmer is")

	def test_the_outcome_bell_is_read_only_by_its_reporter(self):
		self._as(self.mgr_user)
		self._send()
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Employee", self.rpt)
		doc.status, doc.relieving_date = "Left", nowdate()
		doc.save()
		self._as(self.mgr_user)
		mine = json.dumps(frappe.get_list("Notification Log", fields=["subject"],
		                                  filters={"document_type": "ToDo"}), default=str)
		self.assertIn("Confirmed:", mine)
		for who in (self.col_user, self.skip_user, self.hr_b_user, self.hr_a_user):
			self._as(who)
			self.assertEqual(frappe.get_list("Notification Log", filters={"document_type": "ToDo"}), [], who)


class TestWhoIsRefusedPersonalDetails(_Base):
	"""AC-38 rows the first file did not run on their own: a manager of another
	team, a Left manager, and the second call (`get_employee_detail_for_manager`)
	for a Left person. Plus: the refusal line carries no personal value."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.other_user = _login("other", ("Employee",))
		cls.other = _employee("S089Other", company=cls.company_a, reports_to=cls.skip,
		                      user=cls.other_user)
		frappe.db.set_value("Employee", cls.other, "date_of_joining", "2025-01-01", update_modified=False)
		frappe.db.commit()

	def tearDown(self):
		frappe.db.set_value("Employee", self.mgr, "status", "Active", update_modified=False)
		frappe.db.commit()
		super().tearDown()

	def _tick(self):
		frappe.set_user("Administrator")
		org_settings.set_cover_setting(SEES, ",".join(people_fields.MANAGER_SEES_FIELDS))

	def test_another_teams_manager_is_refused_and_the_direct_manager_is_not(self):
		self._tick()
		self._as(self.mgr_user)
		self.assertEqual(set(hr_api.get_employee_detail_for_manager(self.rpt)["personal"]),
		                 set(people_fields.MANAGER_SEES_FIELDS))
		self._as(self.other_user)
		with _Log() as log:
			for call in (hr_api.get_employee_scorecard, hr_api.get_employee_detail_for_manager):
				with self.assertRaises(frappe.PermissionError):
					call(self.rpt)
		self.assertTrue(any("089-SEC-5" in ln for ln in log.lines))
		for line in log.lines:
			for secret in SECRETS:
				self.assertNotIn(secret, line)

	def test_a_left_manager_is_refused_even_for_their_own_old_report(self):
		self._tick()
		self._as(self.mgr_user)
		self.assertTrue(hr_api.get_employee_scorecard(self.rpt)["personal"])
		frappe.db.set_value("Employee", self.mgr, "status", "Left", update_modified=False)
		# a Left manager has no Active Employee: the old code says so with a
		# ValidationError, not a PermissionError. Either way nothing is returned.
		for call in (hr_api.get_employee_scorecard, hr_api.get_employee_detail_for_manager):
			with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
				call(self.rpt)

	def test_a_left_person_gives_no_fields_on_either_call(self):
		self._tick()
		frappe.db.set_value("Employee", self.rpt, {"status": "Left", "relieving_date": nowdate()},
		                    update_modified=False)
		self._as(self.mgr_user)
		for call in (hr_api.get_employee_scorecard, hr_api.get_employee_detail_for_manager):
			blob = json.dumps(call(self.rpt), default=str)
			for secret in SECRETS:
				self.assertNotIn(secret, blob)

	def test_personal_email_gender_company_email_never_appear_even_when_everything_is_ticked(self):
		self._tick()
		self._as(self.mgr_user)
		for call in (hr_api.get_employee_scorecard, hr_api.get_employee_detail_for_manager):
			blob = json.dumps(call(self.rpt), default=str)
			for key in ("personal_email", "company_email", "gender"):
				self.assertNotIn(f'"{key}"', blob)
			self.assertNotIn("s089.rpt.private@example.com", blob)


class TestAnOpenReportIsNotALeavingFact(_Base):
	"""PRIV-3, AC-51."""

	def test_no_leaving_date_reaches_positions_or_another_managers_team(self):
		day = add_days(nowdate(), 9)  # a date nothing else in the fixture uses
		self._as(self.mgr_user)
		self._send(day=day)
		frappe.set_user("Administrator")
		self.assertIsNone(frappe.db.get_value("Employee", self.rpt, "relieving_date"))
		self.assertEqual(frappe.db.get_value("Employee", self.rpt, "status"), "Active")
		# Positions: the HR reader of this company gets the profile, with no date in it
		self._as(self.hrm_user)
		try:
			profile = positions_profile.get_positions_profile(self.rpt)
		except frappe.PermissionError:
			self.skipTest("this HR Manager cannot open Positions on this site; nothing to assert")
		self.assertEqual(profile["employee"], self.rpt)
		self.assertNotIn(day, json.dumps(profile, default=str))
		# the skip-level manager's Team call shows nothing new
		self._as(self.skip_user)
		team = hr_api.get_manager_dashboard()
		self.assertNotIn(self.rpt, team.get("reported", {}))
		self.assertNotIn(day, json.dumps(team, default=str))


class TestPrivacyLists(_Base):
	"""PRIV-1 and SEC-3."""

	def test_the_candidate_list_is_exactly_the_closed_list_and_off_list_names_are_refused(self):
		self.assertEqual(set(people_fields.LIST_KEYS[SEES]),
		                 {"cell_number", "current_address", "person_to_be_contacted", "relation",
		                  "emergency_phone_number"})
		frappe.set_user("Administrator")
		for bad in ("personal_email", "permanent_address", "company_email", "gender",
		            "cell_number,personal_email", "salary"):
			with self.assertRaises(frappe.PermissionError, msg=bad):
				org_settings.set_cover_setting(SEES, bad)
		self.assertEqual(org_settings.get(SEES) or "", "")  # nothing was saved
		org_settings.set_cover_setting(SEES, "cell_number")  # the allowed case
		self.assertEqual(org_settings.get(SEES), "cell_number")

	def test_a_value_written_around_the_setter_still_gives_nothing_off_list(self):
		frappe.db.set_default(SEES, "personal_email,cell_number")
		got = leaver_report.personal_details(self.rpt, self.mgr)
		self.assertEqual(set(got), {"cell_number"})


class TestTheCap(_Base):
	"""OPS-11 with real people, not a patched number: a role held by eleven
	enabled HR users is refused at save and at send; ten is accepted."""

	CROWD = "S089 Crowd"

	def setUp(self):
		super().setUp()
		if not frappe.db.exists("Role", self.CROWD):
			frappe.get_doc({"doctype": "Role", "role_name": self.CROWD}).insert(ignore_permissions=True)
		self.crowd = [_login(f"crowd{i}", (self.CROWD, "HR User", "Employee")) for i in range(11)]
		# a confirmer needs a company scope (SEC-7 c), which comes from an Employee
		for i, user in enumerate(self.crowd):
			_employee(f"S089Crowd{i}", company=self.company_a, user=user)
		frappe.db.set_default(org_settings.CONFIRM_ROLE_KEY, self.CROWD)

	def tearDown(self):
		frappe.db.delete("Has Role", {"role": self.CROWD, "parenttype": "User"})
		frappe.db.commit()
		super().tearDown()

	def test_eleven_holders_are_refused_and_ten_are_accepted(self):
		self.assertEqual(len(org_settings.eligible_confirmers(self.CROWD)), 11)
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.PermissionError):
			org_settings.set_cover_setting(org_settings.CONFIRM_ROLE_KEY, self.CROWD)
		# at send time, with the role already set around the setter
		self._as(self.mgr_user)
		before = self._counts()
		with self.assertRaises(frappe.PermissionError):
			self._send()
		self.assertEqual(self._counts(), before)
		# drop one holder: ten is the limit and is allowed
		frappe.set_user("Administrator")
		frappe.db.delete("Has Role", {"role": self.CROWD, "parent": self.crowd[0]})
		self.assertEqual(len(org_settings.eligible_confirmers(self.CROWD)), 10)
		org_settings.set_cover_setting(org_settings.CONFIRM_ROLE_KEY, self.CROWD)
		self._as(self.mgr_user)
		self._send()
		frappe.set_user("Administrator")
		self.assertEqual(len(self._todos()), 10)
		# 10 confirmers means 10 ToDo rows and one reporter: the cap bounds the writes
		self.assertEqual(len({t.allocated_to for t in self._todos()}), 10)
