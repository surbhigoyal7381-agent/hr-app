"""The salary components report: does it run, and does it agree with the slip?

The report itself is deliberately thin - every figure comes from
`payroll_slip.month_summary`, the same call the salary slip makes, and the
arithmetic behind that has its own 105 tests. So what is worth testing here is
the part the report owns:

  it runs at all, with the right columns;
  it says something useful on a company with no rules rather than showing an
  empty grid;
  its numbers are the slip's numbers, not a second opinion;
  and it writes nothing, because it will be run against months that are closed.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from alvoraa_portal.report.salary_components_workings import (
	salary_components_workings as report,
)

COMPANY = "Salary Report Test Co"
ABBR = "SRTC"
SHIFT = "Salary Report Test Shift"
BASE = 31000


def _gender():
	"""Whatever this site calls a gender. Hard-coding one fails on a bench
	that has never had the fixtures loaded, which is how CI builds its site."""
	existing = frappe.db.get_value("Gender", {}, "name")
	if existing:
		return existing
	return frappe.get_doc({"doctype": "Gender", "gender": "Other"}
	                      ).insert(ignore_permissions=True).name


def setUpModule():
	if not frappe.db.exists("Company", COMPANY):
		frappe.get_doc({"doctype": "Company", "company_name": COMPANY,
		                "abbr": ABBR, "default_currency": "INR",
		                "country": "India"}).insert(ignore_permissions=True)
	if not frappe.db.exists("Shift Type", SHIFT):
		frappe.get_doc({"doctype": "Shift Type", "name": SHIFT,
		                "start_time": "10:00:00", "end_time": "18:00:00"}
		               ).insert(ignore_permissions=True)
	if not frappe.db.get_value("Alvoraa Payroll Rule Set", {"company": COMPANY}):
		doc = frappe.get_doc({
			"doctype": "Alvoraa Payroll Rule Set", "company": COMPANY,
			"enabled": 1, "grace_minutes": 6, "free_reds_per_month": 2,
			"special_day_multiplier": 2, "leave_threshold_days": 15,
			"accrual_month_days": 30,
			"slabs": [
				{"percent_from": 0, "percent_to": 50, "quarters_off": 2,
				 "raises_red": 1},
				{"percent_from": 50, "percent_to": 90, "quarters_off": 1,
				 "raises_red": 0},
				{"percent_from": 90, "percent_to": 100, "quarters_off": 0,
				 "raises_red": 0},
			],
			"mark_rates": [{"grade": "Junior", "amount_per_mark": 100}],
		})
		doc.flags.ignore_permissions = True
		doc.insert()
	frappe.db.commit()


class SalaryReportCase(FrappeTestCase):
	def setUp(self):
		self.start = getdate(add_days(nowdate(), -6))
		self.emp = self._employee()

	def _employee(self):
		doc = frappe.get_doc({
			"doctype": "Employee", "first_name": "Report Subject",
			"company": COMPANY, "date_of_birth": "1990-01-01",
			"date_of_joining": "2024-01-01", "gender": _gender(),
			"status": "Active", "default_shift": SHIFT,
		})
		doc.flags.ignore_permissions = True
		doc.insert()
		return doc.name

	def _paid(self, base=BASE):
		"""A monthly basic, which every money column hangs off."""
		ss = frappe.db.get_value("Salary Structure",
		                         {"docstatus": 1, "company": COMPANY}, "name")
		if not ss:
			comp = ABBR + " Basic"
			if not frappe.db.exists("Salary Component", comp):
				frappe.get_doc({"doctype": "Salary Component",
				                "salary_component": comp, "type": "Earning",
				                "salary_component_abbr": "SRB"}
				               ).insert(ignore_permissions=True)
			d = frappe.get_doc({
				"doctype": "Salary Structure", "name": ABBR + " Structure",
				"company": COMPANY, "payroll_frequency": "Monthly",
				"currency": "INR",
				"earnings": [{"salary_component": comp,
				              "amount_based_on_formula": 1, "formula": "base"}]})
			d.flags.ignore_permissions = True
			d.insert()
			d.submit()
			ss = d.name
		a = frappe.get_doc({"doctype": "Salary Structure Assignment",
		                    "employee": self.emp, "salary_structure": ss,
		                    "from_date": "2024-01-01", "base": base,
		                    "company": COMPANY})
		a.flags.ignore_permissions = True
		a.insert()
		a.submit()

	def _days(self, n=5):
		for i in range(n):
			day = add_days(self.start, i)
			att = frappe.get_doc({"doctype": "Attendance", "employee": self.emp,
			                      "company": COMPANY, "attendance_date": day,
			                      "status": "Present", "shift": SHIFT})
			att.flags.ignore_permissions = True
			att.insert()
			att.submit()
			for t in ("10:02:00", "17:45:00"):
				c = frappe.get_doc({"doctype": "Employee Checkin",
				                    "employee": self.emp,
				                    "time": "%s %s" % (day, t), "shift": SHIFT})
				c.flags.ignore_permissions = True
				c.insert()

	def run_it(self, **kw):
		args = {"company": COMPANY, "from_date": str(self.start),
		        "to_date": nowdate()}
		args.update(kw)
		out = report.execute(args)
		return out[0], out[1], out[2]


class TestItRuns(SalaryReportCase):
	def test_it_returns_columns_and_a_row_per_person(self):
		self._paid()
		self._days()
		cols, rows, _msg = self.run_it()
		self.assertTrue(cols)
		mine = [r for r in rows if r["employee"] == self.emp]
		self.assertEqual(len(mine), 1)

	def test_every_column_has_a_fieldname_and_a_label(self):
		"""A column missing either renders as a blank header somebody then
		has to guess at."""
		cols, _rows, _msg = self.run_it()
		for c in cols:
			self.assertTrue(c.get("fieldname"), c)
			self.assertTrue(c.get("label"), c)

	def test_a_company_with_no_rules_is_told_so_in_words(self):
		"""Rather than an empty grid, which reads as "no data" when the truth
		is "this company does not use these rules"."""
		# A company with no rule set, not merely a different one - this site
		# carries several test companies and some of them have one.
		with_rules = set(frappe.get_all("Alvoraa Payroll Rule Set",
		                                pluck="company"))
		other = next((c for c in frappe.get_all("Company", pluck="name")
		              if c not in with_rules and c != COMPANY), None)
		if not other:
			self.skipTest("every company on this site has a rule set")
		_cols, rows, msg = self.run_it(company=other)
		self.assertEqual(rows, [])
		self.assertIn("no payroll rule set", msg)

	def test_it_refuses_without_a_company(self):
		with self.assertRaises(frappe.ValidationError):
			report.execute({"from_date": str(self.start), "to_date": nowdate()})


class TestTheNumbers(SalaryReportCase):
	def test_the_money_can_be_checked_by_hand(self):
		"""The whole point of this report: somebody has to be able to redo it
		on paper. Seven days in the period, so the daily rate is the monthly
		basic over seven, and five worked days are five of those."""
		self._paid(base=31000)
		self._days(5)
		_cols, rows, _msg = self.run_it()
		row = [r for r in rows if r["employee"] == self.emp][0]

		days_in_period = 7
		self.assertEqual(row["days_with_record"], 5)
		self.assertAlmostEqual(row["daily_rate"], 31000.0 / days_in_period, 1)
		self.assertAlmostEqual(row["basic"], row["daily_rate"] * row["paid_days"], 1)
		self.assertAlmostEqual(
			row["net"],
			row["gross"] - row["other_deductions"], 2)

	def test_it_agrees_with_what_the_slip_would_use(self):
		"""The one thing that must never drift. A report with its own
		arithmetic eventually disagrees with the payslip it is being checked
		against, and then nobody knows which is right."""
		from alvoraa_portal.payroll_slip import month_summary
		self._paid()
		self._days()
		_cols, rows, _msg = self.run_it()
		row = [r for r in rows if r["employee"] == self.emp][0]

		direct = month_summary(self.emp, COMPANY, str(self.start), nowdate())
		self.assertEqual(row["paid_days"], round(direct.paid_days, 2))
		self.assertEqual(row["days_worked"], direct.days_worked)
		self.assertEqual(row["reds"], direct.reds)
		self.assertEqual(row["greens"], direct.greens)

	def test_somebody_with_nothing_at_all_is_named_rather_than_shown_empty(self):
		"""An active employee with no attendance and no salary gets no row of
		noughts - a row of noughts reads like a finding."""
		_cols, rows, msg = self.run_it()
		self.assertFalse([r for r in rows if r["employee"] == self.emp])
		self.assertIn("neither an attendance record", msg)

	def test_running_it_writes_nothing(self):
		"""It will be run against months that are closed."""
		self._paid()
		self._days()
		before = frappe.db.count("Salary Slip"), frappe.db.count("Attendance")
		self.run_it()
		self.assertEqual(
			(frappe.db.count("Salary Slip"), frappe.db.count("Attendance")),
			before)
