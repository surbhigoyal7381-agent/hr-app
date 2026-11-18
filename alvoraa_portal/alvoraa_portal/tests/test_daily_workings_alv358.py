"""Daily Attendance Workings (ALV-358): one person's month, a day per row.

The report owns no arithmetic - each day is `judge`, the total row is
`month_summary` - so what is tested is what it owns:

  Frappe can find it, and only HR roles may open it;
  one row per day of the month, plus the total row;
  each day says what the engine says, and the totals are the slip's totals;
  a day with one punch shows Held (Surbhi, 18 Nov 2026);
  somebody who may not read the employee is refused;
  it writes nothing;
  the link sits under Shift & Attendance -> Reports, once, after a re-run.
"""

import io
import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, get_first_day, get_last_day, getdate, nowdate

from alvoraa_portal import payroll_menu
from alvoraa_portal.alvoraa_portal.report.daily_attendance_workings import (
	daily_attendance_workings as report,
)
from alvoraa_portal.payroll_rules_apply import judge, prepare
from alvoraa_portal.payroll_slip import month_summary
from alvoraa_portal.tests import test_salary_report as base

REPORT = "Daily Attendance Workings"
MONTHS = report.MONTHS


def setUpModule():
	base.setUpModule()


def _month_start():
	"""Last month: every day of it is in the past, so attendance may be marked."""
	return get_first_day(add_months(nowdate(), -1))


class DailyCase(FrappeTestCase):
	def setUp(self):
		self.start = _month_start()
		doc = frappe.get_doc({
			"doctype": "Employee", "first_name": "Daily Subject", "company": base.COMPANY,
			"date_of_birth": "1990-01-01", "date_of_joining": str(self.start),
			"gender": base._gender(), "status": "Active", "default_shift": base.SHIFT,
		})
		doc.flags.ignore_permissions = True
		doc.insert()
		self.emp = doc.name

	def day(self, i, times, status="Present"):
		d = add_days(self.start, i)
		att = frappe.get_doc({"doctype": "Attendance", "employee": self.emp,
		                      "company": base.COMPANY, "attendance_date": d,
		                      "status": status, "shift": base.SHIFT})
		att.flags.ignore_permissions = True
		att.insert()
		att.submit()
		for t in times:
			c = frappe.get_doc({"doctype": "Employee Checkin", "employee": self.emp,
			                    "time": "%s %s" % (d, t), "shift": base.SHIFT})
			c.flags.ignore_permissions = True
			c.insert()
		return str(d)

	def run_it(self, **kw):
		args = {"employee": self.emp, "month": MONTHS[self.start.month - 1],
		        "year": self.start.year}
		args.update(kw)
		cols, rows, msg = report.execute(args)
		return cols, rows, msg


class TestFrappeCanFindIt(FrappeTestCase):
	JSON = os.path.join(
		os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
		"alvoraa_portal", "report", "daily_attendance_workings",
		"daily_attendance_workings.json")

	def setUp(self):
		with io.open(self.JSON, encoding="utf-8") as fh:
			self.spec = json.load(fh)

	def test_folder_and_name_agree(self):
		self.assertEqual(os.path.basename(os.path.dirname(self.JSON)), frappe.scrub(self.spec["name"]))

	def test_the_dotted_path_resolves(self):
		dotted = "alvoraa_portal.%s.report.%s.%s.execute" % (
			frappe.scrub(self.spec["module"]), frappe.scrub(self.spec["name"]),
			frappe.scrub(self.spec["name"]))
		self.assertTrue(callable(frappe.get_attr(dotted)))

	def test_only_hr_roles_may_open_it(self):
		roles = {r["role"] for r in self.spec.get("roles", [])}
		self.assertEqual(roles, {"HR Manager", "HR User", "System Manager"})


class TestTheDays(DailyCase):
	def test_a_row_for_every_day_and_a_total_row(self):
		cols, rows, _msg = self.run_it()
		days = (get_last_day(self.start) - getdate(self.start)).days + 1
		self.assertEqual(len(rows), days + 1)
		self.assertTrue(rows[-1].get("is_total"))
		for c in cols:
			self.assertTrue(c.get("fieldname") and c.get("label"), c)

	def test_a_day_says_what_the_engine_says(self):
		d = self.day(0, ("10:20:00", "17:30:00"))
		_cols, rows, _msg = self.run_it()
		row = next(r for r in rows if r.get("date") == d)
		rs = frappe.get_doc("Alvoraa Payroll Rule Set", {"company": base.COMPANY})
		att = frappe.get_all("Attendance", filters={"employee": self.emp, "attendance_date": d,
		                     "docstatus": 1}, fields=["*"])[0]
		v = judge(att, prepare(rs, d, d, employee=self.emp))
		self.assertEqual(row["status"], "P")
		self.assertEqual((row["in_time"], row["out_time"]), ("10:20", "17:30"))
		self.assertEqual(row["quarters"] or 0, v.total_quarters)
		self.assertEqual(row["red"] or 0, v.reds)
		self.assertEqual(row["green"] or 0, v.greens)
		self.assertEqual(row["shift_minutes"], 480)
		self.assertEqual(row["difference"], row["minutes"] - 480)
		self.assertTrue(row["remarks"])

	def test_break_is_the_time_out_between_first_and_last_punch(self):
		d = self.day(4, ("10:00:00", "13:00:00", "13:40:00", "18:00:00"))
		_cols, rows, _msg = self.run_it()
		row = next(r for r in rows if r.get("date") == d)
		self.assertEqual(row["break_minutes"], 40)
		self.assertEqual(rows[-1]["break_minutes"], 40)

	def test_break_is_not_measured_on_an_odd_number_of_punches(self):
		d = self.day(5, ("10:00:00", "13:00:00", "13:40:00"))
		_cols, rows, _msg = self.run_it()
		row = next(r for r in rows if r.get("date") == d)
		self.assertIsNone(row.get("break_minutes"))
		self.assertIn("Break not measured", row["remarks"])

	def test_the_salary_working_also_hides_people_scoped_away_through_attendance(self):
		"""ALV-359: the live monthly report had the same gap."""
		from alvoraa_portal.alvoraa_portal.report.salary_components_and_workings import (
			salary_components_and_workings as salary,
		)
		other = frappe.get_doc({
			"doctype": "Employee", "first_name": "Salary Scope", "company": base.COMPANY,
			"date_of_birth": "1990-01-01", "date_of_joining": str(self.start),
			"gender": base._gender(), "status": "Active"})
		other.flags.ignore_permissions = True
		other.insert()
		self.day(0, ("10:00:00", "18:00:00"))
		user = "alv358.salary.hr@example.com"
		if not frappe.db.exists("User", user):
			u = frappe.get_doc({"doctype": "User", "email": user, "first_name": "Salary",
			                    "send_welcome_email": 0})
			u.insert(ignore_permissions=True)
			u.add_roles("HR User")
		frappe.get_doc({"doctype": "User Permission", "user": user, "allow": "Employee",
		                "for_value": other.name, "apply_to_all_doctypes": 0,
		                "applicable_for": "Attendance"}).insert(ignore_permissions=True)
		args = {"company": base.COMPANY, "from_date": str(self.start),
		        "to_date": str(get_last_day(self.start))}
		as_admin = salary.execute(args)[1]
		self.assertIn(self.emp, [r["employee"] for r in as_admin])
		frappe.set_user(user)
		try:
			rows = salary.execute(args)[1]
		finally:
			frappe.set_user("Administrator")
		self.assertNotIn(self.emp, [r["employee"] for r in rows])

	def test_one_punch_shows_held_with_no_minutes(self):
		d = self.day(1, ("10:05:00",))
		_cols, rows, _msg = self.run_it()
		row = next(r for r in rows if r.get("date") == d)
		self.assertEqual(row["status"], "Held")
		self.assertIsNone(row.get("minutes"))
		self.assertIsNone(row.get("out_time"))

	def test_the_totals_are_the_slips_totals(self):
		self.day(0, ("10:20:00", "17:30:00"))
		self.day(1, ("10:00:00", "18:00:00"))
		self.day(2, ("11:30:00", "15:00:00"))
		_cols, rows, _msg = self.run_it()
		total = rows[-1]
		rs = frappe.get_doc("Alvoraa Payroll Rule Set", {"company": base.COMPANY})
		s = month_summary(self.emp, base.COMPANY, self.start, get_last_day(self.start), rule_set=rs)
		self.assertEqual(total["quarters"], s.total_quarters)
		self.assertEqual(total["red"], s.reds)
		self.assertEqual(total["green"], s.greens)
		self.assertEqual(sum(r.get("quarters") or 0 for r in rows[:-1]), s.total_quarters)

	def test_running_it_writes_nothing(self):
		self.day(0, ("10:20:00", "17:30:00"))
		before = (frappe.db.count("Attendance"), frappe.db.count("Employee Checkin"),
		          frappe.db.count("Additional Salary"))
		self.run_it()
		self.assertEqual((frappe.db.count("Attendance"), frappe.db.count("Employee Checkin"),
		                  frappe.db.count("Additional Salary")), before)

	def test_it_refuses_without_an_employee(self):
		with self.assertRaises(frappe.ValidationError):
			report.execute({"month": MONTHS[0], "year": 2026})

	def test_a_half_day_leave_counts_against_half_the_shift(self):
		"""The engine judges the other half against half the shift; the minutes
		must be a share of that half, not of the whole 480."""
		d = self.day(3, ("10:00:00", "14:00:00"), status="Half Day")
		frappe.db.set_value("Attendance", {"employee": self.emp, "attendance_date": d},
		                    {"leave_application": "ALV358-TEST-LEAVE", "leave_type": "Casual Leave"},
		                    update_modified=False)
		_cols, rows, _msg = self.run_it()
		row = next(r for r in rows if r.get("date") == d)
		self.assertEqual(row["minutes"], 240)
		self.assertEqual(row["difference"], 0)
		self.assertEqual(row["status"], "P (half leave)")

	def test_an_hr_user_scoped_to_somebody_else_is_refused(self):
		"""The report's own refusal, not Frappe's: an HR User whose User
		Permission names another employee gets an empty list and a refusal."""
		other = frappe.get_doc({
			"doctype": "Employee", "first_name": "Somebody Else", "company": base.COMPANY,
			"date_of_birth": "1990-01-01", "date_of_joining": str(self.start),
			"gender": base._gender(), "status": "Active"})
		other.flags.ignore_permissions = True
		other.insert()
		user = "alv358.scoped.hr@example.com"
		if not frappe.db.exists("User", user):
			u = frappe.get_doc({"doctype": "User", "email": user, "first_name": "Scoped",
			                    "send_welcome_email": 0})
			u.insert(ignore_permissions=True)
			u.add_roles("HR User")
		frappe.get_doc({"doctype": "User Permission", "user": user, "allow": "Employee",
		                "for_value": other.name, "apply_to_all_doctypes": 1}
		               ).insert(ignore_permissions=True)
		frappe.set_user(user)
		try:
			with self.assertRaises(frappe.PermissionError):
				self.run_it()
		finally:
			frappe.set_user("Administrator")

	def test_an_hr_user_scoped_only_through_attendance_is_refused(self):
		"""DTC's pattern: the User Permission applies to Attendance only. The
		Employee list still shows the person, so only the report's own check
		stands between this user and somebody else's days."""
		other = frappe.get_doc({
			"doctype": "Employee", "first_name": "Attendance Scope", "company": base.COMPANY,
			"date_of_birth": "1990-01-01", "date_of_joining": str(self.start),
			"gender": base._gender(), "status": "Active"})
		other.flags.ignore_permissions = True
		other.insert()
		user = "alv358.attendance.hr@example.com"
		if not frappe.db.exists("User", user):
			u = frappe.get_doc({"doctype": "User", "email": user, "first_name": "Attendance",
			                    "send_welcome_email": 0})
			u.insert(ignore_permissions=True)
			u.add_roles("HR User")
		frappe.get_doc({"doctype": "User Permission", "user": user, "allow": "Employee",
		                "for_value": other.name, "apply_to_all_doctypes": 0,
		                "applicable_for": "Attendance"}).insert(ignore_permissions=True)
		frappe.set_user(user)
		try:
			self.assertTrue(frappe.get_list("Employee", filters={"name": self.emp}),
			                "the Employee list must still show the person, or this test proves nothing")
			with self.assertRaises(frappe.PermissionError):
				self.run_it()
		finally:
			frappe.set_user("Administrator")

	def test_a_user_who_cannot_read_the_employee_is_refused(self):
		user = "alv358.nobody@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc({"doctype": "User", "email": user, "first_name": "Nobody",
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		frappe.set_user(user)
		try:
			with self.assertRaises(frappe.PermissionError):
				self.run_it()
		finally:
			frappe.set_user("Administrator")


def _take_out(doctype, name, table):
	"""Remove the report's link first, so the test proves after_migrate PUTS it
	back - not merely that an earlier run left it there."""
	doc = frappe.get_doc(doctype, name)
	rows = [r for r in doc.get(table) if r.link_to != REPORT]
	if len(rows) != len(doc.get(table)):
		doc.set(table, rows)
		doc.flags.ignore_permissions = True
		doc.save()
		frappe.db.commit()


class TestTheMenu(FrappeTestCase):
	def test_it_sits_after_monthly_attendance_sheet_once(self):
		if not frappe.db.exists("Workspace", "Shift & Attendance"):
			self.skipTest("no Shift & Attendance workspace on this site")
		_take_out("Workspace", "Shift & Attendance", "links")
		payroll_menu.after_migrate()
		payroll_menu.after_migrate()
		w = frappe.get_doc("Workspace", "Shift & Attendance")
		links = [l.link_to for l in w.links]
		self.assertEqual(links.count(REPORT), 1)
		if "Monthly Attendance Sheet" in links:
			self.assertEqual(links.index(REPORT), links.index("Monthly Attendance Sheet") + 1)

	def test_the_sidebar_has_it_once(self):
		if not frappe.db.exists("Workspace Sidebar", "Shift & Attendance"):
			self.skipTest("no Shift & Attendance sidebar on this site")
		_take_out("Workspace Sidebar", "Shift & Attendance", "items")
		payroll_menu.after_migrate()
		payroll_menu.after_migrate()
		items = [i.link_to for i in frappe.get_doc("Workspace Sidebar", "Shift & Attendance").items]
		self.assertEqual(items.count(REPORT), 1)
		if "Monthly Attendance Sheet" in items:
			self.assertEqual(items.index(REPORT), items.index("Monthly Attendance Sheet") + 1)

	def test_the_salary_working_link_is_still_placed(self):
		if not frappe.db.exists("Workspace", "Payroll"):
			self.skipTest("no Payroll workspace on this site")
		salary = "Salary Components and Workings"
		w = frappe.get_doc("Workspace", "Payroll")
		w.set("links", [l for l in w.links if l.link_to != salary])
		w.set("shortcuts", [s for s in (w.shortcuts or []) if s.link_to != salary])
		w.flags.ignore_permissions = True
		w.save()
		frappe.db.commit()
		payroll_menu.after_migrate()
		payroll_menu.after_migrate()
		w = frappe.get_doc("Workspace", "Payroll")
		links = [l.link_to for l in w.links]
		self.assertEqual(links.count(salary), 1)
		if "Salary Register" in links:
			self.assertEqual(links.index(salary), links.index("Salary Register") + 1)
		self.assertEqual([s.link_to for s in w.shortcuts].count(salary), 1)
