"""Slice 012 push 1 · every persona against G1, G2, G3 and Data to review (test engineer).

The first tests covered HR Manager, store HR and not-linked HR. This module adds
the people most leaks are found with: System Manager with and without an HR role,
HR User (central and in another company), a line manager, a plain employee, a
Leadership-only user, store HR with no Employee record, and an HR role revoked
mid-session. Every call goes to the whitelisted function directly, not the page.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from alvoraa_portal import attendance_analytics as aa
from alvoraa_portal import data_review as dr
from alvoraa_portal import hr_api
from alvoraa_portal.tests import leader_fixtures_012 as fx
from alvoraa_portal.tests.test_data_review_012 import _clear_limit, environment


def setUpModule():
	fx.setup_module_fixtures()


class PersonaCase(FrappeTestCase):
	"""Kavya: Lakeside (doubtful day, D18-1), Station Road; company-wide D6 and D18-2.
	Other Co: a doubtful day at a branch with the SAME name as Kavya's Lakeside."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.env = environment()
		cls.env.__enter__()
		from alvoraa_portal.tests.test_data_review_012 import _leave_year_start

		ys = _leave_year_start()
		cls.lakeside, cls.station = fx.branch("PLake"), fx.branch("PStation")
		cls.day = getdate(add_days(today(), -2))
		cls.staff = {}
		for company, branch, n in ((fx.KAVYA, cls.lakeside, 6), (fx.KAVYA, cls.station, 6),
		                           (fx.OTHER, cls.lakeside, 6)):
			people = [fx.employee(f"P{i}", company, branch, fast=True) for i in range(n)]
			cls.staff[(company, branch)] = people
			for emp in people:
				fx.attendance(emp, company, branch, cls.day, "Absent" if branch == cls.lakeside else "Present")
				fx.allocation(emp, company, branch, ys, add_days(ys, 364), 30)
		fx.employee("PGone", fx.KAVYA, cls.lakeside, status="Left", fast=True)
		dr.run_morning_checks([fx.KAVYA, fx.OTHER])

		cls.priya = fx.user("ppriya", ["HR Manager"])
		fx.permission(cls.priya, "Company", fx.KAVYA)
		cls.central_user = fx.user("pcentralhruser", ["HR User"])
		fx.permission(cls.central_user, "Company", fx.KAVYA)
		cls.other_hr = fx.user("potherhr", ["HR User"])
		fx.permission(cls.other_hr, "Company", fx.OTHER)
		cls.store_hr = fx.user("pstorehr", ["HR User"])
		fx.employee("PStoreHR", fx.KAVYA, cls.lakeside, user_id=cls.store_hr)
		fx.permission(cls.store_hr, "Branch", cls.lakeside)
		cls.store_hr_no_emp = fx.user("pstorehrnoemp", ["HR User"])
		fx.permission(cls.store_hr_no_emp, "Branch", cls.lakeside)
		cls.sysman = fx.user("psysman", ["System Manager"])
		cls.sysman_hr = fx.user("psysmanhr", ["System Manager", "HR Manager"])
		cls.manager = fx.user("pmanager", ["Employee"])
		mgr = fx.employee("PManager", fx.KAVYA, cls.station, user_id=cls.manager)
		cls.report = fx.employee("PReport", fx.KAVYA, cls.station, reports_to=mgr)
		cls.employee = fx.user("pemployee", ["Employee"])
		fx.employee("PEmployee", fx.KAVYA, cls.station, user_id=cls.employee)
		if not frappe.db.exists("Role", "Leadership"):
			frappe.get_doc({"doctype": "Role", "role_name": "Leadership"}).insert(ignore_permissions=True)
		cls.leader = fx.user("pleader", ["Leadership"])
		fx.employee("PLeader", fx.KAVYA, cls.station, user_id=cls.leader)
		for u in (cls.priya, cls.central_user, cls.other_hr, cls.store_hr, cls.sysman_hr):
			_clear_limit(u)

	@classmethod
	def tearDownClass(cls):
		cls.env.__exit__(None, None, None)
		super().tearDownClass()

	def setUp(self):
		self.caller = frappe.session.user

	def tearDown(self):
		frappe.set_user(self.caller)

	def as_user(self, user, fn, *args, **kwargs):
		frappe.set_user(user)
		try:
			return fn(*args, **kwargs)
		finally:
			frappe.set_user("Administrator")

	def item(self, company, rule, branch=None):
		return frappe.db.get_value(fx.DRI, {"company": company, "rule": rule,
		                                    "alvoraa_branch": branch or ("is", "not set")}, "name")

	def refused(self, user, fn, *args, **kwargs):
		with self.assertRaises(frappe.PermissionError, msg=user):
			self.as_user(user, fn, *args, **kwargs)


class TestHrAnalyticsPersonas(PersonaCase):
	"""G1 / SEC-16."""

	def test_people_without_an_hr_role_are_refused(self):
		for user in (self.sysman, self.manager, self.employee, self.leader, "Guest"):
			self.refused(user, hr_api.get_hr_analytics)

	def test_system_manager_with_hr_sees_every_company(self):
		"""Slice 010's CXO decision: System Manager counts as every company."""
		d = self.as_user(self.sysman_hr, hr_api.get_hr_analytics)
		self.assertEqual(d["scope"]["kind"], "company")
		self.assertEqual(d["scope"]["companies"], frappe.db.count("Company"))

	def test_hr_user_of_another_company_gets_only_that_company(self):
		"""AC-42 from the other side: Other Co's HR sees nothing of Kavya's same-named branch."""
		d = self.as_user(self.other_hr, hr_api.get_hr_analytics)
		text = frappe.as_json(d)
		for emp in self.staff[(fx.KAVYA, self.lakeside)] + self.staff[(fx.KAVYA, self.station)]:
			self.assertNotIn(emp, text)
		self.assertEqual(d["review"]["open_count"],
		                 frappe.db.count(fx.DRI, {"company": fx.OTHER, "status": "Open"}))

	def test_store_hr_with_no_employee_and_no_company_permission_is_not_linked(self):
		"""BA-Q5: a Branch permission alone does not say which company; fail closed."""
		self.assertEqual(self.as_user(self.store_hr_no_emp, hr_api.get_hr_analytics), {"not_linked": True})


class TestDataReviewPersonas(PersonaCase):
	"""SEC-7 / SEC-13."""

	def test_people_without_an_hr_role_are_refused_on_both_endpoints(self):
		name = self.item(fx.KAVYA, "D5", self.lakeside)
		self.assertTrue(name)
		for user in (self.sysman, self.manager, self.employee, self.leader, "Guest"):
			self.refused(user, dr.data_review_items)
			self.refused(user, dr.data_review_confirm, items=[name], action="absence_real")
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Open")

	def test_hr_of_another_company_cannot_list_or_confirm_kavya_records(self):
		out = self.as_user(self.other_hr, dr.data_review_items)
		self.assertNotIn(fx.KAVYA, frappe.as_json(out))
		for rule, branch, action in (("D5", self.lakeside, "absence_real"), ("D6", None, "figure_right")):
			name = self.item(fx.KAVYA, rule, branch)
			self.refused(self.other_hr, dr.data_review_confirm, items=[name], action=action)
			self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Open")

	def test_store_hr_same_branch_name_in_another_company_is_refused(self):
		"""Branch has no company: store HR's Lakeside permission must not reach Other Co's Lakeside."""
		name = self.item(fx.OTHER, "D5", self.lakeside)
		self.assertTrue(name)
		self.assertNotIn(name, frappe.as_json(self.as_user(self.store_hr, dr.data_review_items)))
		self.refused(self.store_hr, dr.data_review_confirm, items=[name], action="absence_real")

	def test_store_hr_with_no_employee_is_not_linked(self):
		self.assertEqual(self.as_user(self.store_hr_no_emp, dr.data_review_items), {"not_linked": True})
		self.refused(self.store_hr_no_emp, dr.data_review_confirm,
		             items=[self.item(fx.KAVYA, "D5", self.lakeside)], action="absence_real")

	def test_system_manager_with_hr_lists_every_company(self):
		out = self.as_user(self.sysman_hr, dr.data_review_items)
		companies = {c["company"] for c in out["cards"]}
		self.assertTrue({fx.KAVYA, fx.OTHER} <= companies)


class TestCentralHrUserConfirmsCompanyRecords(PersonaCase):
	def test_hr_user_with_company_permission_confirms_leave_used(self):
		"""An HR User (not Manager) whose scope is the whole company may confirm D6."""
		name = self.item(fx.KAVYA, "D6")
		self.as_user(self.central_user, dr.data_review_confirm, items=[name], action="figure_right")
		self.assertEqual(frappe.db.get_value(fx.DRI, name, ["status", "confirmed_by"]),
		                 ("Confirmed", self.central_user))


class TestARevokedHrRole(PersonaCase):
	def test_access_ends_as_soon_as_the_role_is_removed(self):
		user = fx.user("prevoked", ["HR User"])
		fx.permission(user, "Company", fx.KAVYA)
		self.assertFalse(self.as_user(user, dr.data_review_items)["not_linked"])
		fx.user("prevoked", ["Employee"])            # role taken away mid-session
		self.refused(user, dr.data_review_items)
		self.refused(user, hr_api.get_hr_analytics)
		self.refused(user, dr.data_review_confirm, items=[self.item(fx.KAVYA, "D6")], action="figure_right")


class TestOrgSettingPersonas(PersonaCase):
	"""G2 / SEC-18: only HR Manager and System Manager reach the setter at all."""

	def test_everyone_else_is_refused_even_for_the_allowed_key(self):
		for user in (self.central_user, self.store_hr, self.manager, self.employee, self.leader):
			self.refused(user, hr_api.set_org_setting, "kra_link_mandatory", "1")
			self.refused(user, hr_api.get_org_setting, "kra_link_mandatory")


class TestPersonPersonas(PersonaCase):
	"""G3 / SEC-17 / AC-53."""

	def setUp(self):
		super().setUp()
		self._saved_roles = frappe.db.get_default(aa.ORG_ROLES_KEY)
		frappe.db.set_default(aa.ORG_ROLES_KEY, "HR User,HR Manager,Leadership,Employee,Employee Self Service")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_default(aa.ORG_ROLES_KEY, self._saved_roles or "")
		super().tearDown()

	def test_leadership_and_employees_cannot_open_another_person_even_if_listed(self):
		"""AC-53, the person() part: a stored role list naming them opens nothing."""
		target = self.staff[(fx.KAVYA, self.lakeside)][0]
		for user in (self.leader, self.employee):
			self.refused(user, aa.person, target)

	def test_a_line_manager_keeps_their_report_only(self):
		self.assertEqual(self.as_user(self.manager, aa.person, self.report)["employee"], self.report)
		self.refused(self.manager, aa.person, self.staff[(fx.KAVYA, self.lakeside)][0])

	def test_store_hr_cannot_open_other_co_employee_at_a_same_named_branch(self):
		self.refused(self.store_hr, aa.person, self.staff[(fx.OTHER, self.lakeside)][0])

	def test_store_hr_opens_their_branch_but_not_the_next_one(self):
		"""SEC-17, repeated on this fixture so the same-named branch case above is not a fluke."""
		self.assertEqual(self.as_user(self.store_hr, aa.person, self.staff[(fx.KAVYA, self.lakeside)][0])["employee"],
		                 self.staff[(fx.KAVYA, self.lakeside)][0])
		self.refused(self.store_hr, aa.person, self.staff[(fx.KAVYA, self.station)][0])

	def test_filter_options_refused_for_leadership_and_employee(self):
		for user in (self.leader, self.employee):
			self.refused(user, aa.filter_options)
