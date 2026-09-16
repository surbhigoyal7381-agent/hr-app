"""Slice 012 push 1 · G3: nobody opens another store's employee's days.

US-9, SEC-17, AC-47 to AC-50. `person()` returned every day's status and leave
type for ANY employee to anyone in the organisation roles; `filter_options()`
listed every store's manager names.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, getdate, nowdate

from alvoraa_portal import attendance_analytics as aa
from alvoraa_portal import branch_scope

LAKESIDE = "S012 G3 Lakeside"
STATION = "S012 G3 Station Road"


def setUpModule():
	branch_scope.after_migrate()


class G3Case(FrappeTestCase):
	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		self.company = frappe.db.get_value("Company", {}, "name")
		for b in (LAKESIDE, STATION):
			if not frappe.db.exists("Branch", b):
				frappe.get_doc({"doctype": "Branch", "branch": b}).insert(ignore_permissions=True)
		self._saved_roles = frappe.db.get_default(aa.ORG_ROLES_KEY)
		frappe.db.set_default(aa.ORG_ROLES_KEY, aa.DEFAULT_ORG_ROLES)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_default(aa.ORG_ROLES_KEY, self._saved_roles or "")
		frappe.set_user(self.caller)

	def user(self, first, *roles):
		email = f"{first.lower()}.s012g3@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		frappe.get_doc("User", email).add_roles(*roles)
		return email

	def person(self, first, branch, user=None, reports_to=None, department=None):
		# Frappe 16 rolls back at the end of the class, not after each test, so a
		# login already linked by an earlier test is reused rather than linked twice.
		if user and (existing := frappe.db.get_value("Employee", {"user_id": user}, "name")):
			return existing
		return frappe.get_doc({
			"doctype": "Employee", "first_name": first, "company": self.company,
			"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "branch": branch, "user_id": user, "reports_to": reports_to,
			"department": department,
			# ERPNext would otherwise limit this login to its own Employee record,
			# which is how a tenant sets up an employee, not an HR person.
			"create_user_permission": 0,
		}).insert(ignore_permissions=True).name

	def branch_permission(self, user, branch):
		if frappe.db.exists("User Permission", {"user": user, "allow": "Branch", "for_value": branch}):
			return
		frappe.get_doc({"doctype": "User Permission", "user": user, "allow": "Branch",
		                "for_value": branch, "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)


class TestPersonIsScoped(G3Case):
	def setUp(self):
		super().setUp()
		self.store_hr = self.user("LakesideHRG3", "HR User")
		self.store_hr_emp = self.person("LakesideHRG3", LAKESIDE, user=self.store_hr)
		self.branch_permission(self.store_hr, LAKESIDE)
		self.lakeside_cashier = self.person("LakeCashierG3", LAKESIDE)
		self.station_cashier = self.person("StationCashierG3", STATION)

	def test_store_hr_cannot_open_another_stores_employee(self):
		"""AC-47: refused, with one security line naming the rule and no person."""
		frappe.set_user(self.store_hr)
		with patch("hrms.alvoraa_hr_core.access.log_refusal") as logged:
			with self.assertRaises(frappe.PermissionError):
				aa.person(self.station_cashier)
		self.assertEqual(logged.call_count, 1)
		self.assertEqual(logged.call_args.args[0], "SEC-17")
		self.assertNotIn("StationCashierG3", repr(logged.call_args))

	def test_store_hr_opens_their_own_stores_employee(self):
		"""AC-47."""
		frappe.set_user(self.store_hr)
		self.assertEqual(aa.person(self.lakeside_cashier)["employee"], self.lakeside_cashier)

	def test_a_left_employee_inside_the_store_can_still_be_opened(self):
		"""D-7."""
		frappe.db.set_value("Employee", self.lakeside_cashier,
		                    {"status": "Left", "relieving_date": add_days(nowdate(), -5)})
		frappe.set_user(self.store_hr)
		self.assertEqual(aa.person(self.lakeside_cashier)["employee"], self.lakeside_cashier)

	def test_another_company_is_refused_even_for_central_hr(self):
		other = frappe.db.get_value("Company", {"name": ("!=", self.company)}, "name")
		central = self.user("CentralHRG3", "HR Manager")
		self.person("CentralHRG3", LAKESIDE, user=central)
		elsewhere = frappe.get_doc({
			"doctype": "Employee", "first_name": "OtherCoG3", "company": other,
			"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male", "status": "Active",
		}).insert(ignore_permissions=True).name
		frappe.set_user(central)
		with self.assertRaises(frappe.PermissionError):
			aa.person(elsewhere)
		self.assertEqual(aa.person(self.station_cashier)["employee"], self.station_cashier)

	def test_store_hr_cannot_open_someone_with_no_branch(self):
		"""DEF-6 (2026-09-16): Frappe's User Permissions are not strict, so an empty
		branch used to pass a Branch permission. HR Analytics leaves those people out
		for store HR (D-8); person() and filter_options now do the same.
		"""
		head_office = self.person("HeadOfficeG3", None)
		frappe.set_user(self.store_hr)
		with self.assertRaises(frappe.PermissionError):
			aa.person(head_office)

	def test_a_long_range_is_cut_to_twelve_months(self):
		"""AC-48."""
		frappe.set_user(self.store_hr)
		end = nowdate()
		out = aa.person(self.lakeside_cashier, date_from="2020-01-01", date_to=end)
		self.assertEqual(getdate(out["to"]), getdate(end))
		self.assertEqual(getdate(out["from"]), getdate(add_days(add_months(end, -12), 1)))

	def test_a_line_manager_keeps_their_line_and_nothing_else(self):
		"""AC-50."""
		mgr_user = self.user("ManagerG3", "Employee")
		mgr = self.person("ManagerG3", STATION, user=mgr_user)
		report = self.person("ReportG3", STATION, reports_to=mgr)
		frappe.set_user(mgr_user)
		self.assertEqual(aa.person(report)["employee"], report)
		with self.assertRaises(frappe.PermissionError):
			aa.person(self.lakeside_cashier)

	def test_system_manager_is_unchanged(self):
		"""AC-50: CXO for now (slice 010), so every store in their company."""
		sm = self.user("VikramG3", "System Manager")
		self.person("VikramG3", LAKESIDE, user=sm)
		frappe.set_user(sm)
		self.assertEqual(aa.person(self.station_cashier)["employee"], self.station_cashier)


class TestFilterOptionsAreScoped(G3Case):
	def test_store_hr_sees_only_their_stores_options(self):
		"""AC-49."""
		depts = frappe.get_all("Department", filters={"is_group": 0}, pluck="name", limit=2)
		store_hr = self.user("FiltersHRG3", "HR User")
		self.person("FiltersHRG3", LAKESIDE, user=store_hr, department=depts[0] if depts else None)
		self.branch_permission(store_hr, LAKESIDE)
		lake_mgr = self.person("LakeMgrG3", LAKESIDE)
		self.person("LakeStaffG3", LAKESIDE, reports_to=lake_mgr)
		station_mgr = self.person("StationMgrG3", STATION)
		self.person("StationStaffG3", STATION, reports_to=station_mgr,
		            department=depts[1] if len(depts) > 1 else None)

		frappe.set_user(store_hr)
		opts = aa.filter_options()
		self.assertEqual(opts["branch"], [LAKESIDE])
		# DEF-6: a no-branch colleague's manager and department stay out too.
		no_branch_mgr = self.person("NoBranchMgrG3", None)
		self.person("NoBranchStaffG3", None, reports_to=no_branch_mgr)
		self.assertNotIn(no_branch_mgr, {m["id"] for m in aa.filter_options()["manager"]})
		ids = {m["id"] for m in opts["manager"]}
		self.assertIn(lake_mgr, ids)
		self.assertNotIn(station_mgr, ids)
		if len(depts) > 1 and depts[0] != depts[1]:
			self.assertNotIn(depts[1], opts["department"])
