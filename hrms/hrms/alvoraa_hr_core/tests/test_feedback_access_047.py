"""ALV-117: who may do what with an Employee Performance Feedback record.

The permission surface IS the product here, so this module walks every one of
the ten actions Frappe HR grants the plain Employee role - read, write, create,
submit, cancel, export, print, share, report and email - against every persona
that exists in a real tenant.

`export` and `report` are the ones that bite: a filtered list with an
unfiltered export is the same leak. They are permission types with no document,
so `has_permission` is never consulted for them and only the query condition
stands there. Both are exercised end to end, through the same
`frappe.desk.reportview` entry points the desk uses.

The fixtures own their own company, their own two stores, their own people and
their own roles, so nothing here depends on another test's leftovers, and
nothing here changes what another test can see.

Names used below:

  subj    the person the main feedback is about; reports to mgr; store North
  auth    wrote it; store North
  unrel   nothing to do with any of it; store North
  mgr     subj's manager; store North
  mgr2    other's manager; store South
  other   reports to mgr2; store South
  hq      no branch at all - head office (DEF-6)
  leaver  status Left, login still enabled, used to manage exrep
  exrep   reports to leaver; store South
  hr_in   HR Manager limited to store North by a Branch User Permission
  hr_out  HR Manager limited to store South
  hr_co   HR Manager for the whole company, no Branch permission
  hr_read HR User (the read-only HR role) limited to store North
  sysmgr  System Manager, standing in for the CXO
"""

import json
from typing import ClassVar

import frappe
from frappe.tests import IntegrationTestCase

from hrms.alvoraa_hr_core.feedback_access import (
	feedback_query_conditions,
	has_feedback_permission,
)

DOCTYPE = "Employee Performance Feedback"
COMPANY = "ALV117 Feedback Co"
ABBR = "A117"
NORTH = "ALV117 Store North"
SOUTH = "ALV117 Store South"
CYCLE = "ALV117 Cycle"
TEMPLATE = "ALV117 Template"

PEOPLE = {
	# key:      (branch, reports_to key, extra roles)
	"subj": (NORTH, "mgr", []),
	"auth": (NORTH, "mgr", []),
	"unrel": (NORTH, "mgr2", []),
	"mgr": (NORTH, None, []),
	"mgr2": (SOUTH, None, []),
	"other": (SOUTH, "mgr2", []),
	"hq": (None, None, []),
	"leaver": (SOUTH, None, []),
	"exrep": (SOUTH, "leaver", []),
	"hr_in": (NORTH, None, ["HR Manager"]),
	"hr_out": (SOUTH, None, ["HR Manager"]),
	"hr_co": (NORTH, None, ["HR Manager"]),
	"hr_read": (NORTH, None, ["HR User"]),
	"sysmgr": (NORTH, None, ["System Manager"]),
}

# A Branch User Permission makes somebody a store's HR person; hr_co gets only
# the Company one, which is what company-wide HR looks like.
BRANCH_LIMIT = {"hr_in": NORTH, "hr_out": SOUTH, "hr_read": NORTH}


def _email(key):
	return f"alv117.{key}@example.com"


def _ensure(doctype, name, **values):
	if name and frappe.db.exists(doctype, name):
		return frappe.get_doc(doctype, name)
	doc = frappe.get_doc({"doctype": doctype, **values})
	if name:
		doc.name = name
		doc.set("__newname", name)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_mandatory=True, ignore_if_duplicate=True)
	return doc


class FeedbackFixtures047(IntegrationTestCase):
	"""The company, the two stores, the people, the roles and the feedback.

	Split from the tests so finding F1's proof can reuse it without re-running
	the whole matrix.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		# Frappe 16 throttles new-user creation (ALV-119). The fixtures reuse
		# users when they already exist, and this keeps a repeated run honest.
		frappe.conf.throttle_user_limit = 5000

		_ensure("Company", COMPANY, company_name=COMPANY, abbr=ABBR, default_currency="INR")
		for branch in (NORTH, SOUTH):
			_ensure("Branch", branch, branch=branch)

		cls.emp = {}
		for key in PEOPLE:
			cls.emp[key] = cls._person(key)
		# The reporting lines need every record to exist first.
		for key, (_branch, boss, _roles) in PEOPLE.items():
			if boss:
				frappe.db.set_value("Employee", cls.emp[key], "reports_to", cls.emp[boss])
		frappe.db.commit()

		cls._user_permissions()
		cls._appraisal()
		cls.fb = cls._feedback()
		cls._make_leaver()
		frappe.db.commit()
		frappe.clear_cache()

	@classmethod
	def _person(cls, key):
		branch, _boss, roles = PEOPLE[key]
		email = _email(key)
		if not frappe.db.exists("User", email):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": f"ALV117 {key}",
					"send_welcome_email": 0,
					"enabled": 1,
				}
			)
			user.flags.ignore_permissions = True
			user.insert(ignore_permissions=True)
		user = frappe.get_doc("User", email)
		for role in ["Employee", *roles]:
			if role not in [r.role for r in user.roles]:
				user.append("roles", {"role": role})
		user.enabled = 1
		user.flags.ignore_permissions = True
		user.save(ignore_permissions=True)

		existing = frappe.db.get_value("Employee", {"user_id": email, "company": COMPANY}, "name")
		if existing:
			return existing
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": f"ALV117 {key}",
				"gender": "Female",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"company": COMPANY,
				"status": "Active",
				"branch": branch,
				"user_id": email,
				# ERPNext defaults this to 1, which quietly writes a User
				# Permission tying the login to its own Employee record on
				# EVERY doctype with an `employee` link - including this one.
				# It is a setting, not a control (see finding F5 and
				# test_erpnexts_own_user_permission_is_a_setting_not_a_control),
				# and it also blocks the manager and HR access this slice is
				# meant to allow. The fixtures turn it off so the tests measure
				# the hooks, and one test measures the setting on its own.
				"create_user_permission": 0,
			}
		)
		employee.flags.ignore_permissions = True
		employee.insert(ignore_permissions=True)
		return employee.name

	@classmethod
	def _user_permissions(cls):
		# Clear anything ERPNext wrote for these logins before, so a re-run on
		# an existing site starts from the same place as a fresh one.
		frappe.db.delete("User Permission", {"user": ("like", "alv117.%"), "allow": "Employee"})
		frappe.db.commit()
		for key in ("hr_in", "hr_out", "hr_co", "hr_read"):
			cls._user_permission(_email(key), "Company", COMPANY)
		for key, branch in BRANCH_LIMIT.items():
			cls._user_permission(_email(key), "Branch", branch)

	@classmethod
	def _user_permission(cls, user, allow, for_value):
		if frappe.db.exists("User Permission", {"user": user, "allow": allow, "for_value": for_value}):
			return
		doc = frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": allow,
				"for_value": for_value,
				"apply_to_all_doctypes": 1,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)

	@classmethod
	def _appraisal(cls):
		_ensure("KRA", "ALV117 Delivery", title="ALV117 Delivery")
		_ensure(
			"Appraisal Template",
			TEMPLATE,
			template_title=TEMPLATE,
			goals=[{"key_result_area": "ALV117 Delivery", "per_weightage": 100}],
		)
		_ensure(
			"Appraisal Cycle",
			CYCLE,
			cycle_name=CYCLE,
			company=COMPANY,
			start_date="2026-01-01",
			end_date="2026-12-31",
			status="In Progress",
			kra_evaluation_method="Manual Rating",
		)
		cls.appraisal = {}
		for key in ("subj", "other", "leaver", "exrep", "hq"):
			employee = cls.emp[key]
			existing = frappe.db.get_value(
				"Appraisal", {"employee": employee, "appraisal_cycle": CYCLE}, "name"
			)
			if existing:
				cls.appraisal[key] = existing
				continue
			doc = frappe.get_doc(
				{
					"doctype": "Appraisal",
					"employee": employee,
					"company": COMPANY,
					"appraisal_cycle": CYCLE,
					"appraisal_template": TEMPLATE,
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			cls.appraisal[key] = doc.name

	@classmethod
	def _one_feedback(cls, subject, reviewer, submit=False):
		doc = frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"employee": cls.emp[subject],
				"reviewer": cls.emp[reviewer],
				"appraisal": cls.appraisal[subject],
				"feedback": "ALV117 fixture",
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		if submit:
			doc.flags.ignore_permissions = True
			doc.submit()
		return doc.name

	@classmethod
	def _feedback(cls):
		frappe.db.delete(DOCTYPE, {"feedback": "ALV117 fixture"})
		return {
			# about subj, written by auth - the record the matrix is built on
			"main": cls._one_feedback("subj", "auth"),
			# the same thing, submitted, so cancel can be tested honestly
			"submitted": cls._one_feedback("subj", "auth", submit=True),
			# written BY subj about somebody else: the decision under test
			"by_subj": cls._one_feedback("other", "subj"),
			# about the leaver, so a leaver can still read their own
			"leaver": cls._one_feedback("leaver", "mgr"),
			# about the leaver's ex-report
			"exrep": cls._one_feedback("exrep", "mgr"),
			# about somebody with no branch at all (DEF-6)
			"hq": cls._one_feedback("hq", "mgr"),
		}

	@classmethod
	def _make_leaver(cls):
		# Written straight to the row on purpose. ERPNext refuses to relieve
		# somebody who still has people reporting to them
		# (InactiveEmployeeStatusError), which is a good rule and closes most
		# of this case in practice. It does not close all of it: a reports_to
		# can be set afterwards, and data loads and imports do not go through
		# that validation. The hook has to fail closed either way, so the
		# fixture forces the state the validation would not let us reach.
		frappe.db.set_value(
			"Employee",
			cls.emp["leaver"],
			{"status": "Left", "relieving_date": "2026-06-30"},
			update_modified=False,
		)
		# The login stays enabled on purpose - that is the case ALV-117 asked
		# about, and it is what a real tenant looks like the week after someone
		# leaves.

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local.form_dict = frappe._dict()

	# ── helpers ──────────────────────────────────────────────────────────────

	def _as(self, key):
		frappe.set_user("Administrator" if key == "sysmgr_admin" else _email(key))

	def _may(self, key, ptype, doc):
		"""What the framework says, roles and controller hook together."""
		return bool(frappe.has_permission(DOCTYPE, ptype, doc=doc, user=_email(key)))

	def _my_names(self):
		return set(self.fb.values())

	def _visible(self, key):
		self._as(key)
		try:
			rows = frappe.get_list(DOCTYPE, fields=["name"], limit_page_length=0)
		finally:
			frappe.set_user("Administrator")
		return {r.name for r in rows} & self._my_names()


class TestFeedbackAccess047(FeedbackFixtures047):
	# ── 1. the hooks are registered at all (pin test) ────────────────────────

	def test_both_hooks_are_registered(self):
		"""If a merge drops either line from hrms/hooks.py, this goes red."""
		self.assertIn(
			"hrms.alvoraa_hr_core.feedback_access.feedback_query_conditions",
			frappe.get_hooks("permission_query_conditions").get(DOCTYPE, []),
		)
		self.assertIn(
			"hrms.alvoraa_hr_core.feedback_access.has_feedback_permission",
			frappe.get_hooks("has_permission").get(DOCTYPE, []),
		)

	def test_the_doctype_still_grants_the_employee_role_everything(self):
		"""The fault being fixed is still there in the JSON - on purpose.

		We fix it with hooks, not by narrowing the doctype or by adding a
		Custom DocPerm row (one of those makes Frappe ignore every standard
		row for the doctype). If somebody ever does narrow it, this test says
		so, and the reviewer can decide whether the hooks are still needed.
		"""
		rows = {
			p.role: p
			for p in frappe.get_all(
				"DocPerm", filters={"parent": DOCTYPE}, fields=["role", "read", "export", "report"]
			)
		}
		self.assertEqual(rows["Employee"].read, 1)
		self.assertEqual(rows["Employee"].export, 1)
		self.assertEqual(rows["Employee"].report, 1)
		self.assertFalse(
			frappe.db.exists("Custom DocPerm", {"parent": DOCTYPE}),
			"a Custom DocPerm row here makes Frappe ignore every standard row for this doctype",
		)

	# ── 2. the query condition never opens the door by accident ─────────────

	def test_the_condition_is_never_empty_for_somebody_who_is_not_the_cxo(self):
		for key in PEOPLE:
			if key == "sysmgr":
				continue
			with self.subTest(person=key):
				condition = feedback_query_conditions(_email(key))
				self.assertTrue(condition, f"{key} got an empty condition, which means everybody")

	def test_a_caller_with_nothing_gets_1_equals_0(self):
		self.assertEqual(feedback_query_conditions("Guest"), "1=0")
		self.assertEqual(feedback_query_conditions(_email("unrel")).count("1=0"), 0)

	def test_the_cxo_still_sees_everything(self):
		self.assertEqual(feedback_query_conditions(_email("sysmgr")), "")
		self.assertTrue(self._my_names() <= self._visible("sysmgr"))

	# ── 3. every action, every persona, on one draft record ─────────────────

	DRAFT_ACTIONS: ClassVar = ("read", "write", "create", "submit", "print", "email", "share")

	# True means the framework must allow it; False means it must refuse.
	DRAFT_EXPECTED: ClassVar = {
		#          read   write  create submit print  email  share
		"subj": (True, False, False, False, False, False, False),
		"auth": (True, True, True, True, True, True, True),
		"unrel": (False, False, False, False, False, False, False),
		"mgr": (True, False, False, False, False, False, False),
		"mgr2": (False, False, False, False, False, False, False),
		"other": (False, False, False, False, False, False, False),
		"hq": (False, False, False, False, False, False, False),
		"leaver": (False, False, False, False, False, False, False),
		"exrep": (False, False, False, False, False, False, False),
		"hr_in": (True, True, True, True, True, True, True),
		"hr_out": (False, False, False, False, False, False, False),
		"hr_co": (True, True, True, True, True, True, True),
		# Finding F6: HR User is read-only in the doctype's own rows, but every
		# HR person also holds the Employee role, and that row grants write,
		# create, submit and cancel. So a "read-only" HR user can write. The
		# hooks do not widen that - before them the same person could write on
		# every record in the tenant, and now only inside their HR scope - but
		# the doctype's read-only HR row has never meant what it says.
		"hr_read": (True, True, True, True, True, True, True),
		"sysmgr": (True, True, True, True, True, True, True),
	}

	def test_every_action_on_a_draft_for_every_persona(self):
		doc = frappe.get_doc(DOCTYPE, self.fb["main"])
		for key, expected in self.DRAFT_EXPECTED.items():
			for ptype, want in zip(self.DRAFT_ACTIONS, expected, strict=True):
				with self.subTest(person=key, action=ptype):
					self.assertEqual(
						self._may(key, ptype, doc),
						want,
						f"{key} / {ptype}: expected {want}",
					)

	SUBMITTED_ACTIONS: ClassVar = ("read", "cancel", "print", "email", "share")

	SUBMITTED_EXPECTED: ClassVar = {
		#          read   cancel print  email  share
		"subj": (True, False, False, False, False),
		"auth": (True, True, True, True, True),
		"unrel": (False, False, False, False, False),
		"mgr": (True, False, False, False, False),
		"mgr2": (False, False, False, False, False),
		"hr_in": (True, True, True, True, True),
		"hr_out": (False, False, False, False, False),
		"hr_co": (True, True, True, True, True),
		# finding F6 again: the Employee role carries cancel, so "read-only" HR
		# can cancel. Inside their HR scope now, rather than anywhere.
		"hr_read": (True, True, True, True, True),
		"leaver": (False, False, False, False, False),
		"sysmgr": (True, True, True, True, True),
	}

	def test_every_action_on_a_submitted_record_for_every_persona(self):
		doc = frappe.get_doc(DOCTYPE, self.fb["submitted"])
		for key, expected in self.SUBMITTED_EXPECTED.items():
			for ptype, want in zip(self.SUBMITTED_ACTIONS, expected, strict=True):
				with self.subTest(person=key, action=ptype):
					self.assertEqual(
						self._may(key, ptype, doc),
						want,
						f"{key} / {ptype} on a submitted record: expected {want}",
					)

	def test_guest_is_refused_every_action(self):
		doc = frappe.get_doc(DOCTYPE, self.fb["main"])
		for ptype in (*self.DRAFT_ACTIONS, "cancel", "export", "report", "delete"):
			with self.subTest(action=ptype):
				self.assertFalse(frappe.has_permission(DOCTYPE, ptype, doc=doc, user="Guest"))

	def test_the_hook_itself_refuses_every_action_for_an_unrelated_employee(self):
		"""Straight at the hook, so a change in role rows cannot mask it."""
		doc = frappe.get_doc(DOCTYPE, self.fb["main"])
		for ptype in (
			"read",
			"write",
			"create",
			"submit",
			"cancel",
			"export",
			"print",
			"share",
			"report",
			"email",
		):
			with self.subTest(action=ptype):
				self.assertFalse(has_feedback_permission(doc, ptype, _email("unrel")))

	# ── 4. opening one record at its own URL ────────────────────────────────

	def test_the_record_is_refused_at_its_own_url(self):
		"""A list filter alone would leave this open - that is why there are two hooks."""
		for key in ("unrel", "mgr2", "hr_out", "leaver"):
			with self.subTest(person=key):
				self._as(key)
				try:
					with self.assertRaises(frappe.PermissionError):
						frappe.client.get(DOCTYPE, self.fb["main"])
				finally:
					frappe.set_user("Administrator")

	def test_the_people_who_should_read_it_still_can_at_its_url(self):
		for key in ("subj", "auth", "mgr", "hr_in", "hr_co", "hr_read"):
			with self.subTest(person=key):
				self._as(key)
				try:
					got = frappe.client.get(DOCTYPE, self.fb["main"])
					self.assertEqual(got["name"], self.fb["main"])
				finally:
					frappe.set_user("Administrator")

	# ── 5. lists ────────────────────────────────────────────────────────────

	LIST_EXPECTED: ClassVar = {
		"subj": {"main", "submitted", "by_subj"},
		"auth": {"main", "submitted"},
		"unrel": set(),
		# mgr sees the two about subj (a direct report) AND the three they
		# wrote themselves about leaver, exrep and hq.
		"mgr": {"main", "submitted", "leaver", "exrep", "hq"},
		"mgr2": {"by_subj"},
		"other": {"by_subj"},
		"hq": {"hq"},
		"exrep": {"exrep"},
		# store North: subj, auth, unrel, mgr, hr_in, hr_co, hr_read, sysmgr
		"hr_in": {"main", "submitted"},
		# hr_read has the same Branch permission as hr_in
		# store South: mgr2, other, leaver, exrep, hr_out
		"hr_out": {"by_subj", "leaver", "exrep"},
		"hr_co": {"main", "submitted", "by_subj", "leaver", "exrep", "hq"},
		"hr_read": {"main", "submitted"},
	}

	def test_what_each_persona_sees_in_a_list(self):
		for key, expected in self.LIST_EXPECTED.items():
			with self.subTest(person=key):
				self.assertEqual(
					self._visible(key),
					{self.fb[k] for k in expected},
					f"{key} sees the wrong set",
				)

	def test_a_leaver_reads_their_own_and_not_their_old_teams(self):
		"""The login is still enabled, so this is the real week-after case."""
		visible = self._visible("leaver")
		self.assertIn(self.fb["leaver"], visible)
		self.assertNotIn(self.fb["exrep"], visible)

	def test_a_store_hr_person_does_not_see_head_office(self):
		"""An employee with no branch is outside a store's scope (DEF-6)."""
		self.assertNotIn(self.fb["hq"], self._visible("hr_in"))
		self.assertNotIn(self.fb["hq"], self._visible("hr_out"))
		self.assertIn(self.fb["hq"], self._visible("hr_co"))

	def test_a_manager_does_not_see_what_their_report_wrote_about_someone_else(self):
		"""The decision of 2026-09-24, written down as a test.

		mgr manages subj. subj wrote feedback about other. It is not about
		mgr's report, the subject never agreed to it, and a manager who can
		read their team's outgoing opinions is how honest feedback stops being
		given. mgr2 - other's own manager - does see it.
		"""
		self.assertNotIn(self.fb["by_subj"], self._visible("mgr"))
		self.assertIn(self.fb["by_subj"], self._visible("mgr2"))
		self.assertIn(self.fb["by_subj"], self._visible("subj"))

		doc = frappe.get_doc(DOCTYPE, self.fb["by_subj"])
		self.assertFalse(self._may("mgr", "read", doc))
		self.assertTrue(self._may("mgr2", "read", doc))

	def test_the_feedback_text_never_comes_back_in_a_filtered_list(self):
		"""A row filter that only hides `name` would still leak the words."""
		self._as("unrel")
		try:
			rows = frappe.get_list(
				DOCTYPE, fields=["name", "feedback", "employee"], limit_page_length=0
			)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual([r for r in rows if r.name in self._my_names()], [])

	def test_the_desk_count_endpoint_is_filtered_too(self):
		"""The list view's "x of y" number goes through reportview.get_count,
		which is a DatabaseQuery, so the condition applies there as well."""
		from frappe.desk.reportview import get_count

		self._as("unrel")
		try:
			frappe.local.form_dict = frappe._dict(
				{"doctype": DOCTYPE, "filters": json.dumps({"feedback": "ALV117 fixture"})}
			)
			self.assertEqual(get_count(), 0)
		finally:
			frappe.local.form_dict = frappe._dict()
			frappe.set_user("Administrator")

	# ── 6. export and report ────────────────────────────────────────────────

	def _report_view_names(self, key):
		from frappe.desk.reportview import get as reportview_get

		self._as(key)
		try:
			frappe.local.form_dict = frappe._dict(
				{
					"doctype": DOCTYPE,
					"fields": json.dumps([f"`tab{DOCTYPE}`.`name`", f"`tab{DOCTYPE}`.`feedback`"]),
					"start": 0,
					"page_length": 0,
				}
			)
			data = reportview_get()
		finally:
			frappe.local.form_dict = frappe._dict()
			frappe.set_user("Administrator")
		# reportview.get returns either the compressed {keys, values} shape or
		# a plain list of rows, depending on the arguments the desk sent.
		if isinstance(data, dict):
			rows = data.get("values") or []
			return {row[0] for row in rows} & self._my_names()
		return {(row[0] if isinstance(row, list | tuple) else row.get("name")) for row in data} & self._my_names()

	def _export_text(self, key):
		from frappe.desk.reportview import export_query

		self._as(key)
		try:
			frappe.local.form_dict = frappe._dict(
				{
					"doctype": DOCTYPE,
					"fields": json.dumps([f"`tab{DOCTYPE}`.`name`", f"`tab{DOCTYPE}`.`feedback`"]),
					"file_format_type": "CSV",
					"title": DOCTYPE,
				}
			)
			frappe.response = frappe._dict()
			export_query()
			content = frappe.response.get("filecontent") or b""
		finally:
			frappe.local.form_dict = frappe._dict()
			frappe.response = frappe._dict()
			frappe.set_user("Administrator")
		if isinstance(content, bytes):
			content = content.decode("utf-8", "replace")
		return content

	def test_report_view_is_filtered_for_every_persona(self):
		for key, expected in self.LIST_EXPECTED.items():
			with self.subTest(person=key):
				self.assertEqual(
					self._report_view_names(key),
					{self.fb[k] for k in expected},
					f"{key} gets the wrong rows in the report view",
				)

	def test_export_is_filtered_for_every_persona(self):
		"""A filtered list with an unfiltered export is the same leak."""
		for key, expected in self.LIST_EXPECTED.items():
			with self.subTest(person=key):
				text = self._export_text(key)
				for name in self._my_names():
					should_be_there = name in {self.fb[k] for k in expected}
					self.assertEqual(
						name in text,
						should_be_there,
						f"{key}: {name} {'missing from' if should_be_there else 'leaked into'} the export",
					)

	def test_an_unrelated_employee_exports_nothing_at_all(self):
		text = self._export_text("unrel")
		self.assertNotIn("ALV117 fixture", text)

	def test_the_doctype_level_report_and_export_flags_are_untouched(self):
		"""We do not change the role rows, so these stay True - which is
		exactly why the query condition has to do the work."""
		for ptype in ("export", "report"):
			with self.subTest(action=ptype):
				self.assertTrue(frappe.has_permission(DOCTYPE, ptype, user=_email("unrel")))

	# ── 7. the flows that must keep working ─────────────────────────────────

	def test_the_dotted_line_insert_still_works(self):
		"""dotted_line.py inserts with ignore_permissions=True as whoever saved
		the appraisal. That must still go through, and its duplicate check -
		frappe.db.exists - must still see the row."""
		self._as("unrel")
		try:
			doc = frappe.get_doc(
				{
					"doctype": DOCTYPE,
					"employee": self.emp["subj"],
					"reviewer": self.emp["mgr2"],
					"appraisal": self.appraisal["subj"],
					"feedback": "ALV117 dotted line",
				}
			)
			doc.insert(ignore_permissions=True)
			self.assertTrue(
				frappe.db.exists(
					DOCTYPE, {"appraisal": self.appraisal["subj"], "reviewer": self.emp["mgr2"]}
				)
			)
			# and the person who inserted it still cannot read it
			self.assertFalse(self._may("unrel", "read", doc))
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc(DOCTYPE, doc.name, force=True, ignore_permissions=True)

	def test_an_author_can_still_write_their_own_feedback_the_normal_way(self):
		"""appraisal.add_feedback sets reviewer to the caller's own Employee."""
		self._as("mgr")
		try:
			appraisal = frappe.get_doc("Appraisal", self.appraisal["subj"])
			doc = frappe.get_doc(
				{
					"doctype": DOCTYPE,
					"employee": self.emp["subj"],
					"reviewer": self.emp["mgr"],
					"appraisal": appraisal.name,
					"feedback": "ALV117 by mgr",
				}
			)
			doc.insert()
			self.assertTrue(frappe.db.exists(DOCTYPE, doc.name))
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc(DOCTYPE, doc.name, force=True, ignore_permissions=True)

	def test_nobody_can_write_feedback_in_somebody_elses_name(self):
		"""create is refused when the reviewer is not the caller - otherwise
		anyone could publish an opinion under a colleague's name."""
		self._as("unrel")
		try:
			doc = frappe.get_doc(
				{
					"doctype": DOCTYPE,
					"employee": self.emp["subj"],
					"reviewer": self.emp["mgr"],
					"appraisal": self.appraisal["subj"],
					"feedback": "ALV117 forged",
				}
			)
			with self.assertRaises(frappe.PermissionError):
				doc.insert()
		finally:
			frappe.set_user("Administrator")

	def test_the_subject_cannot_change_or_withdraw_what_was_written_about_them(self):
		self._as("subj")
		try:
			doc = frappe.get_doc(DOCTYPE, self.fb["main"])
			doc.feedback = "ALV117 edited by the subject"
			with self.assertRaises(frappe.PermissionError):
				doc.save()
			submitted = frappe.get_doc(DOCTYPE, self.fb["submitted"])
			with self.assertRaises(frappe.PermissionError):
				submitted.cancel()
		finally:
			frappe.set_user("Administrator")

	# ── 8. the known gap, written down ──────────────────────────────────────

	def test_erpnexts_own_user_permission_is_a_setting_not_a_control(self):
		"""Finding F5, measured rather than assumed.

		ERPNext's Employee has `create_user_permission`, and it defaults to 1.
		When it is on, linking a login to an Employee record writes a User
		Permission that ties that login to its own Employee record on EVERY
		doctype with an `employee` link - this one included. So on a tenant
		where those rows exist, an ordinary employee was already limited to
		feedback about themselves.

		That is not a reason to skip ALV-117, for three reasons this test
		shows: the row is one tick away from not existing, it is per employee
		rather than per tenant, and while it is on it also blocks the manager
		and HR access the product actually needs. The hooks give the rule; the
		setting only ever gave an accident.
		"""
		user = _email("unrel")
		doc = frappe.get_doc(DOCTYPE, self.fb["main"])
		self.assertFalse(self._may("unrel", "read", doc))  # the hook refuses anyway

		# With the row removed - which is what `create_user_permission = 0`
		# leaves behind - the hook is the only thing standing there.
		self.assertFalse(
			frappe.db.exists("User Permission", {"user": user, "allow": "Employee"}),
			"fixtures deliberately have no per-employee User Permission",
		)
		self.assertEqual(self._visible("unrel"), set())

		# And the manager access the product needs is blocked by that same
		# setting when it is on, which is why it cannot be the control.
		self._user_permission(_email("mgr"), "Employee", self.emp["mgr"])
		try:
			frappe.clear_cache(user=_email("mgr"))
			self.assertNotIn(self.fb["main"], self._visible("mgr"))
		finally:
			frappe.db.delete("User Permission", {"user": _email("mgr"), "allow": "Employee"})
			frappe.db.commit()
			frappe.clear_cache(user=_email("mgr"))
		self.assertIn(self.fb["main"], self._visible("mgr"))

	def test_a_docshare_beats_both_hooks_for_read_print_and_email(self):
		"""Finding F3, measured rather than assumed - and worse than expected.

		Two places in Frappe put a share above a permission rule:

		* `frappe/model/db_query.py` ORs the share condition onto the
		  permission conditions, so a shared row appears in the list;
		* `frappe/permissions.py has_permission` falls back to
		  `false_if_not_shared()` AFTER the controller hook has refused, and
		  that fallback covers read, write, share, submit, email and print.

		So a share defeats both hooks. What still holds is who may create one:
		`share` itself goes through the hook, so only the author or HR in
		scope can share a feedback record at all. The residue is "the author
		may hand their own feedback to anyone", which is a deliberate act on
		their own text rather than a tenant-wide leak.

		Closing it properly means dropping `share` (and probably `email`) from
		the Employee row in the doctype JSON. That is a change to a standard
		Frappe HR doctype and a decision of its own, so it is recorded here
		rather than made quietly.
		"""
		doc = frappe.get_doc(DOCTYPE, self.fb["main"])
		# Only the people the hook allows can create the share in the first
		# place - that is the part that still holds.
		self.assertFalse(self._may("unrel", "share", doc))
		self.assertTrue(self._may("auth", "share", doc))

		frappe.share.add(DOCTYPE, self.fb["main"], _email("unrel"), read=1)
		try:
			self.assertIn(self.fb["main"], self._visible("unrel"))
			# The hook itself still says no...
			self.assertFalse(has_feedback_permission(doc, "read", _email("unrel")))
			# ...and the framework overrides it for exactly these three.
			for ptype in ("read", "print", "email"):
				with self.subTest(action=ptype, beaten_by_the_share=True):
					self.assertTrue(self._may("unrel", ptype, doc))
			# These the share does not carry.
			for ptype in ("write", "submit", "cancel", "share"):
				with self.subTest(action=ptype):
					self.assertFalse(self._may("unrel", ptype, doc))
		finally:
			frappe.db.delete(
				"DocShare", {"share_doctype": DOCTYPE, "share_name": self.fb["main"]}
			)
			frappe.db.commit()
		self.assertNotIn(self.fb["main"], self._visible("unrel"))
