"""Slice 012 push 1 · G1: HR Analytics shows each HR person their own scope only.

US-8, SEC-16, AC-41 to AC-46, AC-10 (HR and the calculation agree), AC-44 (not
linked), OPS-63 (fixed query count). Before this, a store's HR person received
every store's and every company's names, gender and joining dates.
"""

import inspect
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_first_day, getdate, today

from alvoraa_portal import hr_api
from alvoraa_portal import org_figures as of
from alvoraa_portal.tests import leader_fixtures_012 as fx


def setUpModule():
	fx.setup_module_fixtures()


def _plan_allows_analytics():
	return patch("alvoraa_portal.subscription.has_feature", return_value=True)


class AnalyticsScopeCase(FrappeTestCase):
	"""The fixture tenant, built once per class: Kavya with two branches and a
	person with no branch; Other Co using the SAME branch name (V6)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.lakeside = fx.branch("Lakeside")
		cls.station = fx.branch("Station")
		td = getdate(today())
		cls.day1, cls.day2 = get_first_day(td), getdate(f"{td.year}-{td.month:02d}-02")
		confirm_on = get_first_day(td)

		cls.store_hr = fx.user("g1storehr", ["HR User"])
		fx.employee("G1StoreHR", fx.KAVYA, cls.lakeside, user_id=cls.store_hr)
		fx.permission(cls.store_hr, "Branch", cls.lakeside)

		cls.lake = [fx.employee(f"G1Lake{i}", fx.KAVYA, cls.lakeside) for i in range(3)]
		cls.stat = [fx.employee(f"G1Stat{i}", fx.KAVYA, cls.station) for i in range(2)]
		cls.nobranch = fx.employee("G1NoBranch", fx.KAVYA, None)
		cls.other = [fx.employee(f"G1Other{i}", fx.OTHER, cls.lakeside) for i in range(2)]
		for emp in (cls.lake[0], cls.stat[0], cls.other[0]):
			frappe.db.set_value("Employee", emp, "scheduled_confirmation_date", confirm_on)

		for emp in cls.lake + [cls.nobranch]:
			fx.attendance(emp, fx.KAVYA, cls.lakeside if emp != cls.nobranch else None, cls.day1, "Present")
			fx.attendance(emp, fx.KAVYA, cls.lakeside if emp != cls.nobranch else None, cls.day2, "Absent")
		for emp in cls.stat:
			fx.attendance(emp, fx.KAVYA, cls.station, cls.day1, "Present")
			fx.attendance(emp, fx.KAVYA, cls.station, cls.day2, "Absent")
		for emp in cls.other:
			fx.attendance(emp, fx.OTHER, cls.lakeside, cls.day1, "Absent")

		cls.company_hr = fx.user("g1companyhr", ["HR User"])
		fx.permission(cls.company_hr, "Company", fx.KAVYA)
		cls.priya = fx.user("g1priya", ["HR Manager"])
		fx.permission(cls.priya, "Company", fx.KAVYA)
		cls.unlinked = fx.user("g1unlinked", ["HR Manager"])

	def setUp(self):
		self.caller = frappe.session.user

	def tearDown(self):
		frappe.set_user(self.caller)

	def analytics_as(self, user):
		frappe.set_user(user)
		try:
			with _plan_allows_analytics():
				return hr_api.get_hr_analytics()
		finally:
			frappe.set_user("Administrator")

	@staticmethod
	def names(rows):
		return {r["name"] for r in rows}


class TestStoreHr(AnalyticsScopeCase):
	def test_store_hr_sees_only_their_store(self):
		"""AC-41: counts, distributions and both name lists are Lakeside only."""
		d = self.analytics_as(self.store_hr)
		self.assertFalse(d["not_linked"])
		self.assertEqual(d["scope"]["kind"], "branch")
		self.assertEqual(d["headcount"]["active"], 4)          # three staff and store HR
		self.assertEqual([r["location"] for r in d["location_distribution"]], [self.lakeside])
		self.assertEqual(sum(r["count"] for r in d["gender_distribution"]), 4)
		self.assertEqual(sum(r["count"] for r in d["desig_distribution"]), 4)
		self.assertEqual(self.names(d["confirmations_due"]), {self.lake[0]})
		lake_people = set(self.lake) | {frappe.db.get_value("Employee", {"user_id": self.store_hr})}
		self.assertTrue(self.names(d["recent_employees"]) <= lake_people)
		# Lakeside attendance only: 3 present, 3 absent (Other Co's Lakeside rows excluded).
		self.assertEqual((d["org_health"]["present_this_month"], d["org_health"]["absent_this_month"]), (3, 3))


class TestReviewItemsInScope(AnalyticsScopeCase):
	"""Its own class: the review records it makes would change the other tests' figures."""

	def test_open_items_and_doubtful_days_of_other_stores_do_not_reach_store_hr(self):
		"""AC-46."""
		fx.review_item(fx.KAVYA, self.lakeside, check_date=self.day2)
		fx.review_item(fx.KAVYA, self.station, check_date=self.day2)
		fx.review_item(fx.KAVYA, None, rule="D6", item_type="Leave used", check_date=self.day1)
		d = self.analytics_as(self.store_hr)
		self.assertEqual(d["review"], {"open_count": 1, "doubtful_dates": [str(self.day2)]})
		self.assertEqual((d["org_health"]["present_this_month"], d["org_health"]["absent_this_month"]), (3, 0))
		self.assertEqual(d["kpis"]["attendance_rate"], 100.0)

		central = self.analytics_as(self.priya)
		self.assertEqual(central["review"]["open_count"], 3)
		# Station Road's doubtful day is left out for central HR too; the no-branch person's row stays.
		self.assertEqual(central["org_health"]["absent_this_month"], 1)


class TestCompanyScope(AnalyticsScopeCase):
	def test_a_company_hr_user_sees_nothing_of_another_company(self):
		"""AC-42: not even the same-named branch."""
		d = self.analytics_as(self.company_hr)
		self.assertEqual(d["scope"]["kind"], "company")
		everything = frappe.as_json(d)
		for emp in self.other:
			self.assertNotIn(emp, everything)
			self.assertNotIn(frappe.db.get_value("Employee", emp, "employee_name"), everything)
		lake_row = [r for r in d["location_distribution"] if r["location"] == self.lakeside]
		self.assertEqual(lake_row[0]["count"], 4)
		self.assertEqual(d["org_health"]["absent_this_month"], 6)

	def test_central_hr_sees_every_branch_of_their_company(self):
		"""AC-43."""
		d = self.analytics_as(self.priya)
		locations = {r["location"] for r in d["location_distribution"]}
		self.assertTrue({self.lakeside, self.station, "HQ"} <= locations)
		self.assertEqual(self.names(d["confirmations_due"]), {self.lake[0], self.stat[0]})

	def test_hr_analytics_and_the_calculation_agree(self):
		"""AC-10: zero difference for the same scope and period."""
		d = self.analytics_as(self.priya)
		scope = of.hr_scope(self.priya)
		start, end = of.period(scope)
		self.assertEqual(d["kpis"]["attendance_rate"], of.attendance_figures(scope, start, end)["rate"])
		self.assertEqual(d["kpis"]["leave_utilization"], of.leave_figures(scope)["used_pct"])
		self.assertEqual(d["headcount"]["active"], of.people_figures(scope)["active"])
		self.assertEqual(d["data_up_to"], str(end))


class TestNotLinked(AnalyticsScopeCase):
	def test_hr_with_no_company_and_no_employee_gets_no_figures(self):
		"""AC-44 / BA-Q5: the message, and nothing else."""
		self.assertEqual(self.analytics_as(self.unlinked), {"not_linked": True})

	def test_an_employee_is_still_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self.analytics_as(fx.user("g1employee", ["Employee"]))


class TestTheCodeItself(FrappeTestCase):
	def test_no_ignore_permissions_and_the_gates_stay(self):
		"""AC-45."""
		source = inspect.getsource(hr_api.get_hr_analytics)
		self.assertNotIn("ignore_permissions", source)
		self.assertIn("frappe.get_list", source)
		self.assertIn('frappe.throw("Access denied", frappe.PermissionError)', source)
		self.assertEqual(getattr(hr_api.get_hr_analytics, "__alvoraa_feature__", None), "analytics")

	def test_a_branch_name_with_a_quote_is_just_a_value(self):
		"""SEC-8: scope values are parameters, never part of the SQL text."""
		scope = of.Scope((fx.KAVYA,), ("Lake'side\" or 1=1 -- ",))
		self.assertIsNone(of.attendance_figures(scope, "2026-09-01", "2026-09-13")["rate"])
		self.assertEqual(of.people_figures(scope)["total"], 0)


class TestQueryCount(FrappeTestCase):
	"""OPS-63: the same number of queries at 10 and 100 people, 2 and 8 branches."""

	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user(self.caller)

	def count_for(self, people, branches):
		names = [fx.branch("G1QC") for _ in range(branches)]
		hr = fx.user(f"g1qc{people}x{branches}", ["HR Manager"])
		fx.permission(hr, "Company", fx.KAVYA)
		for i in range(people):
			b = names[i % branches]
			emp = fx.employee(f"G1QC{i}", fx.KAVYA, b, fast=True)
			fx.attendance(emp, fx.KAVYA, b, get_first_day(today()), "Present")
		frappe.set_user(hr)
		try:
			with _plan_allows_analytics():
				hr_api.get_hr_analytics()          # warm Frappe's own caches for this user
				with fx.QueryCounter() as q:
					hr_api.get_hr_analytics()
		finally:
			frappe.set_user("Administrator")
		return q.count

	def test_query_count_is_fixed(self):
		counts = {k: self.count_for(*k) for k in ((10, 2), (100, 2), (10, 8), (100, 8))}
		self.assertEqual(len(set(counts.values())), 1, counts)
