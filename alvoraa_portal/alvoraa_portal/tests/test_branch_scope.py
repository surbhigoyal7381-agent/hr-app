"""Store HR see their own store (slice 011).

A location HR person holds HR User and a User Permission on their Branch. Frappe
applies that only to records with a Link to Branch, so attendance, check-ins,
leave and the rest showed every store. What is proven here: the field is on every
record type, it is filled from the employee, old records get it once, and a store's
HR person then sees their store only - in the desk list and in the portal's
organisation attendance view. Central HR, with no Branch permission, still sees all.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime, nowdate

from alvoraa_portal import attendance_analytics as aa
from alvoraa_portal import branch_scope as bs

STORE_A = "BS Test Store A"
STORE_B = "BS Test Store B"


def setUpModule():
	"""The field arrives through after_install and after_migrate in production.
	A test run must not depend on which of those this site went through."""
	bs.after_migrate()
	for dt in bs.SOURCES:
		frappe.clear_cache(doctype=dt)


def _company():
	return frappe.db.get_value("Company", {}, "name")


class BranchCase(FrappeTestCase):
	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		self.company = _company()
		for b in (STORE_A, STORE_B):
			if not frappe.db.exists("Branch", b):
				frappe.get_doc({"doctype": "Branch", "branch": b}).insert(ignore_permissions=True)

	def tearDown(self):
		# No commit: FrappeTestCase rolls each test back.
		frappe.set_user(self.caller)

	def person(self, first, branch):
		return frappe.get_doc({
			"doctype": "Employee", "first_name": first, "company": self.company,
			"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "branch": branch,
		}).insert(ignore_permissions=True).name

	def day(self, employee, days_ago):
		a = frappe.get_doc({
			"doctype": "Attendance", "employee": employee, "status": "Present",
			"attendance_date": add_days(nowdate(), -days_ago), "company": self.company,
		}).insert(ignore_permissions=True)
		a.submit()
		return a

	def hr_user(self, first, branch=None):
		email = "%s.bs@example.com" % first.lower()
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		frappe.get_doc("User", email).add_roles("HR User")
		if branch:
			frappe.get_doc({"doctype": "User Permission", "user": email, "allow": "Branch",
			                "for_value": branch, "apply_to_all_doctypes": 1}
			               ).insert(ignore_permissions=True)
		return email


class TheField(BranchCase):
	def test_every_record_type_carries_a_read_only_branch(self):
		for dt, (link, source, _after) in bs.SOURCES.items():
			f = frappe.get_meta(dt).get_field(bs.FIELD)
			self.assertIsNotNone(f, "%s has no branch field" % dt)
			self.assertEqual((f.fieldtype, f.options), ("Link", "Branch"), dt)
			self.assertEqual(f.fetch_from, "%s.%s" % (link, source), dt)
			self.assertTrue(f.read_only, dt)
			self.assertTrue(f.search_index, "%s: 45,000 check-ins need the index" % dt)

	def test_installing_twice_changes_nothing(self):
		before = frappe.db.count("Custom Field", {"fieldname": bs.FIELD})
		bs.after_migrate()
		self.assertEqual(frappe.db.count("Custom Field", {"fieldname": bs.FIELD}), before)


class TheValue(BranchCase):
	def test_new_attendance_and_checkin_carry_the_employees_store(self):
		p = self.person("BSNew", STORE_A)
		self.assertEqual(self.day(p, 3).get(bs.FIELD), STORE_A)
		c = frappe.get_doc({"doctype": "Employee Checkin", "employee": p, "log_type": "IN",
		                    "time": now_datetime()}).insert(ignore_permissions=True)
		self.assertEqual(c.get(bs.FIELD), STORE_A)

	def test_after_a_move_old_records_stay_with_the_old_store(self):
		"""Decided 2026-09-14: history says where the work happened."""
		p = self.person("BSMover", STORE_A)
		old = self.day(p, 5)
		frappe.db.set_value("Employee", p, "branch", STORE_B)
		new = self.day(p, 4)
		self.assertEqual(frappe.db.get_value("Attendance", old.name, bs.FIELD), STORE_A)
		self.assertEqual(new.get(bs.FIELD), STORE_B)

	def test_the_one_time_fill_fills_blanks_and_nothing_else(self):
		p = self.person("BSOld", STORE_A)
		blank = self.day(p, 7)
		kept = self.day(p, 6)
		frappe.db.set_value("Attendance", blank.name, bs.FIELD, None)
		frappe.db.set_value("Attendance", kept.name, bs.FIELD, STORE_B)   # saved before a move

		bs.fill_existing()

		self.assertEqual(frappe.db.get_value("Attendance", blank.name, bs.FIELD), STORE_A)
		self.assertEqual(frappe.db.get_value("Attendance", kept.name, bs.FIELD), STORE_B)

	def test_the_patch_runs_on_a_site_that_already_has_the_field(self):
		from alvoraa_portal.patches.v1_0 import fill_branch_on_hr_records
		fill_branch_on_hr_records.execute()


class WhoSeesWhat(BranchCase):
	def setUp(self):
		super().setUp()
		self.a = self.person("BSAtA", STORE_A)
		self.b = self.person("BSAtB", STORE_B)
		self.day_a = self.day(self.a, 2).name
		self.day_b = self.day(self.b, 2).name

	def visible_days(self, user):
		frappe.set_user(user)
		try:
			return set(frappe.get_list("Attendance", filters={"name": ("in", [self.day_a, self.day_b])},
			                           pluck="name"))
		finally:
			frappe.set_user("Administrator")

	def test_store_hr_sees_only_their_store_in_the_desk(self):
		store_hr = self.hr_user("BSStoreHR", STORE_A)
		self.assertEqual(self.visible_days(store_hr), {self.day_a})

	def test_central_hr_still_sees_every_store(self):
		central = self.hr_user("BSCentralHR")
		self.assertEqual(self.visible_days(central), {self.day_a, self.day_b})

	def test_store_hr_sees_only_their_store_in_the_portal_view(self):
		"""The organisation view read employees with no permission check, so a
		store's HR person saw every store even with the field in place."""
		frappe.set_user(self.hr_user("BSPortalHR", STORE_A))
		staff, _me = aa._population("organisation", None, None, {})
		self.assertIn(self.a, staff)
		self.assertNotIn(self.b, staff)
		with self.assertRaises(frappe.PermissionError):
			aa._population("organisation", None, [self.a, self.b], {})

	def test_central_hr_sees_every_store_in_the_portal_view(self):
		frappe.set_user(self.hr_user("BSPortalCentral"))
		staff, _me = aa._population("organisation", None, None, {})
		self.assertIn(self.a, staff)
		self.assertIn(self.b, staff)
