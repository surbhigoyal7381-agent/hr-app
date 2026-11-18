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


class TestTheMenu(FrappeTestCase):
	def test_it_sits_after_monthly_attendance_sheet_once(self):
		if not frappe.db.exists("Workspace", "Shift & Attendance"):
			self.skipTest("no Shift & Attendance workspace on this site")
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
		payroll_menu.after_migrate()
		payroll_menu.after_migrate()
		items = [i.link_to for i in frappe.get_doc("Workspace Sidebar", "Shift & Attendance").items]
		self.assertEqual(items.count(REPORT), 1)
		if "Monthly Attendance Sheet" in items:
			self.assertEqual(items.index(REPORT), items.index("Monthly Attendance Sheet") + 1)

	def test_the_salary_working_link_is_still_placed(self):
		if not frappe.db.exists("Workspace", "Payroll"):
			self.skipTest("no Payroll workspace on this site")
		payroll_menu.after_migrate()
		w = frappe.get_doc("Workspace", "Payroll")
		self.assertEqual([l.link_to for l in w.links].count("Salary Components and Workings"), 1)
