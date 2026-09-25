"""Holding an HR role is not a company scope.

`goals_api._require_manages` returned early for anybody holding an HR role, with
no company check at all. Its one scoped sibling, `approve_goal_update`, calls
`access.permitted_companies()` and refuses outside it. So on a tenant with more
than one company, HR at company A could raise a goal for somebody at company B,
read it, rewrite it, log progress on it and set its number by hand - everything
except approve an update on it.

Seven guards had the same shape. They all now ask `_hr_may_act_for()`, which is
one call to `permitted_companies()` - not a third definition of which companies
a person looks after.

**What must keep working, and is checked here:** a System Manager reaches every
company; HR reaches their own company exactly as before; and somebody who is
genuinely this person's manager keeps their reach even across a company line,
because that reach comes from the org chart and not from a role.

Synthetic people only, on the shared S010D fixture: `_Team` already builds HR in
company A and an employee in company B, which is the whole shape of the bug.
"""

import frappe

from alvoraa_portal import goals_api
from alvoraa_portal.tests.test_portal_security_010 import _employee, _user
from alvoraa_portal.tests.test_review_copies_010d import _Team


def _goal_for(employee, name="S045 scope goal"):
	"""An Individual Goal owned by Administrator, so `owner` never decides."""
	frappe.set_user("Administrator")
	existing = frappe.db.get_value("Individual Goal",
	                               {"employee": employee, "goal_name": name}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Individual Goal",
		"employee": employee,
		"goal_name": name,
		"target_value": 100,
		"start_date": "2026-01-01",
		"end_date": "2026-12-31",
		"status": "Active",
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


class _Scope(_Team):
	"""_Team, plus one pair the base class does not have: an HR Manager in
	company A who is the actual manager of somebody in company B."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hr_a_user = cls.hr_user           # HR Manager, own Employee in company A
		cls.hr_a = cls.hr
		cls.in_b = cls.subject_b              # plain Employee, company B
		cls.in_a = cls.stranger               # plain Employee, company A

		cls.cross_boss_user = _user("s045.crossboss", ("HR Manager", "Employee"))
		cls.cross_boss = _employee("S045CrossBoss", company=cls.company_a,
		                           user=cls.cross_boss_user)
		cls.cross_report = _employee("S045CrossReport", company=cls.company_b,
		                             reports_to=cls.cross_boss)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _as(self, user):
		frappe.set_user(user)

	def _new_goal_args(self, employee):
		return dict(goal_name="S045 made by HR", target_value=10,
		            start_date="2026-02-01", end_date="2026-11-30",
		            employee=employee)


class TestHrCannotReachAnotherCompany(_Scope):
	"""The reported fault, at every guard that had the same shape."""

	def test_hr_cannot_create_a_goal_for_someone_at_another_company(self):
		"""The one that was reported. Red before the fix."""
		self._as(self.hr_a_user)
		with self.assertRaises(frappe.PermissionError):
			goals_api.create_goal(**self._new_goal_args(self.in_b))

	def test_hr_cannot_list_another_company_as_someone_to_raise_goals_for(self):
		"""The picker that feeds create_goal is scoped with it, not left wide."""
		self._as(self.hr_a_user)
		names = {r["name"] for r in goals_api.get_manageable_employees()}
		self.assertNotIn(self.in_b, names)
		self.assertIn(self.in_a, names)

	def test_hr_cannot_ask_which_objectives_another_company_may_align_to(self):
		self._as(self.hr_a_user)
		with self.assertRaises(frappe.PermissionError):
			goals_api.get_linkable_objectives(employee=self.in_b)

	def test_hr_cannot_rewrite_another_companys_goal(self):
		goal = _goal_for(self.in_b)
		self._as(self.hr_a_user)
		with self.assertRaises(frappe.PermissionError):
			goals_api.update_goal(goal, goal_name="renamed by the wrong company")

	def test_hr_cannot_read_another_companys_goal(self):
		goal = _goal_for(self.in_b)
		self._as(self.hr_a_user)
		with self.assertRaises(frappe.PermissionError):
			goals_api.get_goal_detail(goal)

	def test_hr_cannot_read_another_companys_progress_log(self):
		goal = _goal_for(self.in_b)
		self._as(self.hr_a_user)
		with self.assertRaises(frappe.PermissionError):
			goals_api.get_goal_update_log(goal)

	def test_hr_cannot_log_progress_on_another_companys_goal(self):
		goal = _goal_for(self.in_b)
		self._as(self.hr_a_user)
		with self.assertRaises(frappe.PermissionError):
			goals_api.submit_goal_update(goal, 5, note="not mine to log")

	def test_hr_cannot_set_another_companys_number_by_hand(self):
		goal = _goal_for(self.in_b)
		self._as(self.hr_a_user)
		with self.assertRaises(frappe.PermissionError):
			goals_api.set_goal_progress(goal, 42)


class TestWhatMustKeepWorking(_Scope):
	"""The other half of a scope change, and the reason it is a release note."""

	def test_hr_still_raises_goals_inside_their_own_company(self):
		self._as(self.hr_a_user)
		made = goals_api.create_goal(**self._new_goal_args(self.in_a))
		self.assertTrue(made.get("name"))
		frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.get_value("Individual Goal", made["name"], "employee"),
			self.in_a)

	def test_system_manager_still_reaches_every_company(self):
		"""`permitted_companies` gives System Manager every company, so a CXO
		view is unchanged by this narrowing."""
		self._as(self.sysman_user)
		made = goals_api.create_goal(**dict(self._new_goal_args(self.in_b),
		                                    goal_name="S045 made by sysman"))
		self.assertTrue(made.get("name"))

	def test_a_real_manager_keeps_their_reach_across_a_company_line(self):
		"""The reporting line is checked FIRST, on purpose.

		Somebody who is genuinely this person's manager reaches them because of
		the org chart, not because of a role - so the company narrowing must not
		take that away. This person is HR in company A and manages somebody in
		company B.
		"""
		self._as(self.cross_boss_user)
		made = goals_api.create_goal(**dict(self._new_goal_args(self.cross_report),
		                                    goal_name="S045 made by their manager"))
		self.assertTrue(made.get("name"))

	def test_an_employee_still_raises_a_goal_for_themselves(self):
		self._as(self.subject_user)
		made = goals_api.create_goal(goal_name="S045 my own goal", target_value=3,
		                             start_date="2026-03-01", end_date="2026-09-30")
		self.assertTrue(made.get("name"))


class TestOneDefinitionOfWhichCompanies(_Scope):
	"""A rule written twice is a rule that drifts. This keeps it written once."""

	def test_the_guards_all_go_through_one_helper(self):
		import inspect

		src = inspect.getsource(goals_api)
		self.assertIn("def _hr_may_act_for(", src)
		# `permitted_companies` is imported in exactly one place in this module:
		# the helper. Anything else calling it directly is a second definition
		# of the rule waiting to disagree with the first.
		self.assertEqual(
			src.count("import permitted_companies"), 1,
			"permitted_companies is imported more than once in goals_api. One "
			"definition of which companies a person looks after, please - that "
			"is exactly the gap this slice closed.")

	def test_the_helper_fails_closed_on_an_employee_with_no_company(self):
		self._as(self.hr_a_user)
		self.assertFalse(goals_api._hr_may_act_for(None))
		self.assertFalse(goals_api._hr_may_act_for("Employee-that-does-not-exist"))
