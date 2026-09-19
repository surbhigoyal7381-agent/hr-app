"""Slice 030: a store's HR person sees only their store, in every reader.

On ppj.dev a Store HR & Admin Executive (HR User, Branch User Permission on one
store inside one company) was correctly limited to their store everywhere except
three places that handed them the whole company: the HR review list, the
calibration matrix and the Cumulative KPI Readings Check report. Those readers
scoped by company only (access.permitted_companies) and never learned about
branches, while the attendance screens had their own private branch rule.

What is pinned here: one shared definition (access.permitted_employees) that the
attendance screens, the review list, the matrix and the report all use; a store
HR User sees only their store in all three readers and no out-of-store name
appears; an employee with no branch is outside a store (fail closed, DEF-6); a
plain manager with no HR role is refused; System Manager and company-wide HR
still see everyone (decision 2); and the matrix ships nobody's gender
(decision 3). Synthetic people and records only, tagged S010D / S030.
"""

import importlib
import os

import frappe

from alvoraa_goals.alvoraa_goals.report.cumulative_kpi_readings_check import (
	cumulative_kpi_readings_check as report,
)
from alvoraa_portal import attendance_analytics as aa
from alvoraa_portal import performance_api as papi
from alvoraa_portal.tests.test_portal_security_010 import _employee, _user
from alvoraa_portal.tests.test_review_copies_010d import _day, _Team
import hrms.alvoraa_hr_core.access as access

STORE_A = "S030 Store A"
STORE_B = "S030 Store B"


class _Stores(_Team):
	"""One company, two stores. A store HR User limited to store A; two people
	in store A, one in store B, one with no branch at all (head office)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for branch in (STORE_A, STORE_B):
			if not frappe.db.exists("Branch", branch):
				frappe.get_doc({"doctype": "Branch", "branch": branch}).insert(ignore_permissions=True)
		cls.store_hr_user = _user("s030.storehr", ("HR User", "Employee"))
		cls.store_hr = _employee("S030StoreHR", company=cls.company_a, user=cls.store_hr_user)
		cls.a1 = _employee("S030AtAOne", company=cls.company_a)
		cls.a2 = _employee("S030AtATwo", company=cls.company_a)
		cls.b1 = _employee("S030AtB", company=cls.company_a)
		cls.n1 = _employee("S030NoBranch", company=cls.company_a)
		for emp, branch in ((cls.store_hr, STORE_A), (cls.a1, STORE_A), (cls.a2, STORE_A),
		                    (cls.b1, STORE_B), (cls.n1, None)):
			frappe.db.set_value("Employee", emp, "branch", branch, update_modified=False)
		frappe.db.commit()
		cls.in_store = {cls.a1, cls.a2}
		cls.outside = {cls.b1, cls.n1}

	def setUp(self):
		super().setUp()
		# _employee strips every User Permission off a login, so the store limit
		# is given per test and taken away again afterwards.
		frappe.get_doc({"doctype": "User Permission", "user": self.store_hr_user, "allow": "Branch",
		                "for_value": STORE_A, "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
		frappe.clear_cache(user=self.store_hr_user)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete("User Permission", {"user": self.store_hr_user, "allow": "Branch"})
		frappe.clear_cache(user=self.store_hr_user)
		frappe.db.commit()
		super().tearDown()

	def _reviews_at_hr(self):
		"""One cycle with every fixture person's review at HR Review."""
		start, end = self._window()
		cycle = self._cycle(start, end)
		for emp in (self.a1, self.a2, self.b1, self.n1):
			self._appraisal(emp, cycle, status="HR Review")
		return cycle

	def _names_of(self, *employees):
		return {frappe.db.get_value("Employee", e, "employee_name") for e in employees}


class TestOneDefinitionOfWhoHrMaySee(_Stores):
	def test_the_attendance_screens_and_the_shared_helper_read_the_same_branches(self):
		self._as(self.store_hr_user)
		self.assertEqual(access.permitted_branches(), [STORE_A])
		self.assertEqual(aa._linked_branches(), [STORE_A])
		self._as(self.hr_user)
		self.assertIsNone(access.permitted_branches())
		self.assertIsNone(aa._linked_branches())

	def test_store_hr_may_see_their_store_only_and_nobody_with_an_empty_branch(self):
		self._as(self.store_hr_user)
		allowed = access.permitted_employees()
		self.assertEqual(allowed, {self.store_hr, self.a1, self.a2})
		self.assertFalse(allowed & self.outside)

	def test_company_wide_hr_and_system_manager_see_everyone_and_a_manager_sees_nobody(self):
		everyone = {self.store_hr, *self.in_store, *self.outside}
		self._as(self.hr_user)
		self.assertTrue(everyone <= access.permitted_employees())
		self._as(self.sysman_user)
		self.assertTrue(everyone <= access.permitted_employees())
		self._as(self.manager_user)
		self.assertEqual(access.permitted_employees(), set())

	def test_the_attendance_organisation_view_did_not_move(self):
		"""test_branch_scope is the proof; this keeps the wrapper honest here too."""
		self._as(self.store_hr_user)
		staff, _me = aa._population("organisation", None, None, {})
		self.assertTrue(self.in_store <= set(staff))
		self.assertFalse(self.outside & set(staff))


class TestReviewListIsStoreScoped(_Stores):
	def test_store_hr_lists_only_their_stores_reviews(self):
		cycle = self._reviews_at_hr()
		self._as(self.store_hr_user)
		rows = papi.hr_list_appraisals(cycle)
		self.assertEqual({r["employee"] for r in rows}, self.in_store)
		self.assertEqual(len(rows), 2)
		self.assertFalse({r["employee_name"] for r in rows} & self._names_of(*self.outside))

	def test_a_plain_manager_is_refused_the_review_list(self):
		cycle = self._reviews_at_hr()
		self._as(self.manager_user)
		with self.assertRaises(frappe.PermissionError):
			papi.hr_list_appraisals(cycle)

	def test_system_manager_and_company_wide_hr_list_every_store(self):
		cycle = self._reviews_at_hr()
		for user in (self.sysman_user, self.hr_user):
			self._as(user)
			listed = {r["employee"] for r in papi.hr_list_appraisals(cycle)}
			self.assertEqual(listed, self.in_store | self.outside, user)


class TestCalibrationMatrixIsStoreScoped(_Stores):
	def test_store_hr_plots_only_their_stores_reviews(self):
		cycle = self._reviews_at_hr()
		self._as(self.store_hr_user)
		matrix = papi.get_calibration_matrix(cycle)
		self.assertEqual({r["employee"] for r in matrix["rows"]}, self.in_store)
		self.assertEqual(matrix["all_participants"], 2)
		self.assertEqual(matrix["stage_counts"], {"HR Review": 2})
		self.assertFalse({r["employee_name"] for r in matrix["rows"]} & self._names_of(*self.outside))

	def test_a_plain_manager_is_refused_the_matrix(self):
		cycle = self._reviews_at_hr()
		self._as(self.manager_user)
		with self.assertRaises(frappe.PermissionError):
			papi.get_calibration_matrix(cycle)

	def test_system_manager_and_company_wide_hr_plot_every_store(self):
		cycle = self._reviews_at_hr()
		for user in (self.sysman_user, self.hr_user):
			self._as(user)
			plotted = {r["employee"] for r in papi.get_calibration_matrix(cycle)["rows"]}
			self.assertEqual(plotted, self.in_store | self.outside, user)

	def test_nobodys_gender_leaves_the_server(self):
		"""Decision 3: the matrix carried every plotted person's gender to the
		browser for a filter chip. The chip is gone and so is the value."""
		cycle = self._reviews_at_hr()
		self._as(self.sysman_user)
		matrix = papi.get_calibration_matrix(cycle)
		self.assertTrue(matrix["rows"])
		for row in matrix["rows"]:
			self.assertNotIn("gender", row)
		self.assertNotIn("genders", matrix["filter_options"])

		page = os.path.join(os.path.dirname(importlib.import_module("alvoraa_portal").__file__),
		                    "www", "hrms-employee.html")
		with open(page, encoding="utf-8-sig") as f:
			html = f.read()
		for marker in ("cal-f-gender", "pd-f-gender", "opts.genders", "r.gender"):
			self.assertNotIn(marker, html, marker)


class TestKpiReadingsReportIsStoreScoped(_Stores):
	def _running_totals_for(self, cycle, *employees):
		start = frappe.db.get_value("Appraisal Cycle", cycle, "start_date")
		out = {}
		for emp in employees:
			kpi = self._kpi(emp, cycle, target=100)
			for i, value in enumerate((10, 25, 40), start=1):
				self._reading(kpi, _day(start, i), value)
			out[emp] = kpi
		return out

	def test_store_hr_sees_only_their_stores_kpis(self):
		start, end = self._window()
		cycle = self._cycle(start, end)
		kpis = self._running_totals_for(cycle, self.a1, self.b1, self.n1)

		self._as(self.store_hr_user)
		_columns, rows = report.execute({"appraisal_cycle": cycle})
		self.assertEqual({r["kpi"] for r in rows}, {kpis[self.a1]})
		self.assertFalse({r["employee_name"] for r in rows} & self._names_of(*self.outside))
		# The company filter narrows the store; it never widens it.
		self.assertEqual({r["kpi"] for r in report.execute({"appraisal_cycle": cycle, "company": self.company_a})[1]},
		                 {kpis[self.a1]})
		self.assertEqual(report.execute({"appraisal_cycle": cycle, "company": self.company_b})[1], [])

	def test_a_plain_manager_is_refused_the_report(self):
		self._as(self.manager_user)
		with self.assertRaises(frappe.PermissionError):
			report.execute({})

	def test_system_manager_and_company_wide_hr_see_every_store(self):
		start, end = self._window()
		cycle = self._cycle(start, end)
		kpis = self._running_totals_for(cycle, self.a1, self.b1, self.n1)
		for user in (self.sysman_user, self.hr_user):
			self._as(user)
			listed = {r["kpi"] for r in report.execute({"appraisal_cycle": cycle})[1]}
			self.assertEqual(listed, set(kpis.values()), user)
