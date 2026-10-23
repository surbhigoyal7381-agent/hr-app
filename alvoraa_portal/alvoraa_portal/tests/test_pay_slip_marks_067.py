"""Slice 067 (ALV-208): red and green money reaches the salary slip.

Before this, the month's reds and greens were worked out, shown in the desk
report, and then reached no payslip at all: the function meant to write them
was called by nothing and could not have worked (no currency). These tests
build REAL draft Salary Slips through Frappe HR's own calculation, so the slip
hook is proven on a site, not only the arithmetic behind it.

Most tests hand the hook a chosen month summary, because what they prove is
the record-keeping (replace, never add; cancel and amend; never touch HR's own
lines). The ones that prove the money is right use real attendance and real
punches, and compare the slip with the desk report row by row.

Every name starts with L067, so nothing else on the test site collides.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, getdate, nowdate

from alvoraa_portal import pay_api, payroll_slip
from alvoraa_portal.payroll_month import MonthSummary
from alvoraa_portal.tests.utils import ensure_fiscal_years

from alvoraa_portal.alvoraa_portal.report.salary_components_and_workings import (
	salary_components_and_workings as report,
)

COMPANY = "L067 Slip Co"
ABBR = "L067S"
HOLIDAYS = "L067 Holidays"
SHIFT = "L067 Shift"
JUNIOR, SENIOR = "L067 Junior", "L067 Senior"
CONTRACT = "L067 Contract"
BASIC = "L067 Basic"
INCENTIVE = "L067 Incentive"
ARREAR_WHOLE = "L067 Arrear"            # Depends on Payment Days OFF (the fix)
ARREAR_SCALED = "L067 Arrear Scaled"    # ON, as DTC's Arrear is today
STRUCTURE = "L067 Structure"
BASE = 31000.0
PAYROLL_ON = ("portal", "leaves", "attendance", "expenses", "payroll")

# Last full month: every day is in the past, so attendance can cover it.
START = getdate(get_first_day(add_months(nowdate(), -1)))
END = getdate(get_last_day(START))
DAYS = (END - START).days + 1


def _insert(d, submit=False):
	doc = frappe.get_doc(d)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc


def _component(name, abbr, kind, by_payment_days=0):
	if not frappe.db.exists("Salary Component", name):
		_insert({"doctype": "Salary Component", "salary_component": name,
		         "salary_component_abbr": abbr, "type": kind,
		         "depends_on_payment_days": by_payment_days,
		         "remove_if_zero_valued": 1, "is_tax_applicable": 0})
	frappe.db.set_value("Salary Component", name, "depends_on_payment_days", by_payment_days)
	return name


def _gender():
	return frappe.db.get_value("Gender", {}, "name") or _insert(
		{"doctype": "Gender", "gender": "Other"}).name


def _employee(first, grade=None, category=None, relieving=None):
	name = frappe.db.get_value("Employee", {"first_name": first, "last_name": "L067"}, "name")
	values = {"company": COMPANY, "grade": grade, "employment_type": category,
	          "status": "Active", "default_shift": SHIFT, "relieving_date": relieving,
	          "holiday_list": HOLIDAYS}
	if not name:
		name = _insert(dict({"doctype": "Employee", "first_name": first, "last_name": "L067",
		                     "gender": _gender(), "date_of_birth": "1990-01-01",
		                     "date_of_joining": add_days(START, -200),
		                     "create_user_permission": 0}, **values)).name
	else:
		frappe.db.set_value("Employee", name, values)
	if not frappe.db.exists("Salary Structure Assignment", {"employee": name, "docstatus": 1}):
		_insert({"doctype": "Salary Structure Assignment", "employee": name,
		         "salary_structure": STRUCTURE, "company": COMPANY, "currency": "INR",
		         "from_date": add_days(START, -150), "base": BASE}, submit=True)
	return name


def setUpModule():
	ensure_fiscal_years(START, END, nowdate())
	frappe.set_user("Administrator")
	if not frappe.db.exists("Holiday List", HOLIDAYS):
		_insert({"doctype": "Holiday List", "holiday_list_name": HOLIDAYS,
		         "from_date": add_days(START, -400), "to_date": add_days(END, 400)})
	if not frappe.db.exists("Company", COMPANY):
		_insert({"doctype": "Company", "company_name": COMPANY, "abbr": ABBR,
		         "default_currency": "INR", "country": "India"})
	frappe.db.set_value("Company", COMPANY, "default_holiday_list", HOLIDAYS)
	# This hrms reads holidays from a submitted Holiday List Assignment only.
	if not frappe.db.exists("Holiday List Assignment", {"assigned_to": COMPANY, "docstatus": 1}):
		_insert({"doctype": "Holiday List Assignment", "applicable_for": "Company",
		         "assigned_to": COMPANY, "holiday_list": HOLIDAYS,
		         "from_date": add_days(START, -390)}, submit=True)
	if not frappe.db.exists("Shift Type", SHIFT):
		_insert({"doctype": "Shift Type", "name": SHIFT,
		         "start_time": "10:00:00", "end_time": "18:00:00"})
	for g in (JUNIOR, SENIOR):
		if not frappe.db.exists("Employee Grade", g):
			_insert({"doctype": "Employee Grade", "__newname": g})
	if not frappe.db.exists("Employment Type", CONTRACT):
		_insert({"doctype": "Employment Type", "employee_type_name": CONTRACT})

	# DTC's shape: Red and Green at a fixed 0, not by payment days.
	_component(payroll_slip.RED_COMPONENT, "RV", "Deduction")
	_component(payroll_slip.GREEN_COMPONENT, "GV", "Earning")
	_component(BASIC, "L067B", "Earning", by_payment_days=1)
	_component(INCENTIVE, "L067I", "Earning")
	_component(ARREAR_WHOLE, "L067A", "Earning", by_payment_days=0)
	_component(ARREAR_SCALED, "L067AS", "Earning", by_payment_days=1)

	if not frappe.db.exists("Salary Structure", STRUCTURE):
		_insert({"doctype": "Salary Structure", "name": STRUCTURE, "company": COMPANY,
		         "payroll_frequency": "Monthly", "currency": "INR", "is_active": "Yes",
		         "earnings": [
		             {"salary_component": BASIC, "amount_based_on_formula": 1,
		              "formula": "base", "depends_on_payment_days": 1},
		             {"salary_component": payroll_slip.GREEN_COMPONENT, "amount": 0},
		             {"salary_component": INCENTIVE, "amount": 0}],
		         "deductions": [
		             {"salary_component": payroll_slip.RED_COMPONENT, "amount": 0}]},
		        submit=True)

	if not frappe.db.get_value("Alvoraa Payroll Rule Set", {"company": COMPANY}):
		_insert({
			"doctype": "Alvoraa Payroll Rule Set", "company": COMPANY, "enabled": 1,
			"grace_minutes": 6, "free_reds_per_month": 2, "special_day_multiplier": 2,
			"leave_threshold_days": 15, "accrual_month_days": 30,
			"grade_field": "grade", "category_field": "employment_type",
			"slabs": [
				{"percent_from": 0, "percent_to": 50, "quarters_off": 2, "raises_red": 1},
				{"percent_from": 50, "percent_to": 90, "quarters_off": 1, "raises_red": 0},
				{"percent_from": 90, "percent_to": 100, "quarters_off": 0, "raises_red": 0}],
			"mark_rates": [{"grade": JUNIOR, "amount_per_mark": 100},
			               {"grade": SENIOR, "amount_per_mark": 200}],
			"categories": [{"category": CONTRACT, "earns_leave_credits": 0,
			                "earns_marks": 0, "doubles_deduction": 0}],
		})
	frappe.db.commit()


def _rule_set():
	return frappe.db.get_value("Alvoraa Payroll Rule Set", {"company": COMPANY})


def _switch(on):
	frappe.db.set_value("Alvoraa Payroll Rule Set", _rule_set(), "enabled", 1 if on else 0)
	frappe.clear_cache(doctype="Alvoraa Payroll Rule Set")


def _wipe(*employees):
	"""Slips, engine and hand lines, attendance and punches for these people."""
	for emp in employees:
		for table in ("Salary Slip", "Additional Salary", "Attendance", "Employee Checkin"):
			frappe.db.delete(table, {"employee": emp})
	frappe.db.delete("Comment", {"reference_doctype": "Salary Slip",
	                             "content": ("like", "%red and green lines%")})


def _summary(red=0.0, green=0.0, paid_days=None):
	return MonthSummary(paid_days=DAYS if paid_days is None else paid_days,
	                    red_deduction=red, green_earning=green)


def _slip(emp, summary=None):
	doc = frappe.get_doc({"doctype": "Salary Slip", "employee": emp, "company": COMPANY,
	                      "start_date": START, "end_date": END, "posting_date": END,
	                      "payroll_frequency": "Monthly", "currency": "INR"})
	doc.flags.ignore_permissions = True
	if summary is None:
		doc.insert()
	else:
		with patch.object(payroll_slip, "month_summary", return_value=summary):
			doc.insert()
	return doc


def _resave(doc, summary):
	doc.reload()
	doc.flags.ignore_permissions = True
	with patch.object(payroll_slip, "month_summary", return_value=summary):
		doc.save()
	return doc


def _line(doc, component):
	rows = [r for r in doc.earnings + doc.deductions if r.salary_component == component]
	return flt(rows[0].amount, 2) if rows else None


def _engine(emp, component, docstatus=None):
	f = {"employee": emp, "salary_component": component,
	     "ref_doctype": payroll_slip.ENGINE_REF}
	if docstatus is not None:
		f["docstatus"] = docstatus
	return frappe.get_all("Additional Salary", filters=f,
	                      fields=["name", "amount", "docstatus", "amended_from", "payroll_date"],
	                      order_by="creation asc")


def _work(emp, red_days=0, normal_days=None):
	"""Real attendance and punches: `red_days` days at 3 hours of an 8-hour
	shift (37.5%, a red), then ordinary full days."""
	normal_days = DAYS - red_days if normal_days is None else normal_days
	for i in range(red_days + normal_days):
		day = add_days(START, i)
		out = "13:00:00" if i < red_days else "18:00:00"
		_insert({"doctype": "Attendance", "employee": emp, "company": COMPANY,
		         "attendance_date": day, "status": "Present", "shift": SHIFT}, submit=True)
		for t in ("10:00:00", out):
			_insert({"doctype": "Employee Checkin", "employee": emp,
			         "time": "%s %s" % (day, t), "shift": SHIFT})


class SlipCase(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		_switch(True)
		self.junior = _employee("Jaya", grade=JUNIOR)
		self.senior = _employee("Sena", grade=SENIOR)
		self.contract = _employee("Chandu", grade=JUNIOR, category=CONTRACT)
		self.everyone = (self.junior, self.senior, self.contract)
		_wipe(*self.everyone)

	def tearDown(self):
		frappe.set_user("Administrator")
		_wipe(*self.everyone)
		_switch(True)
		frappe.db.commit()


class TestTheMoneyReachesTheSlip(SlipCase):
	"""T1, T2, T3, T4, T11: real attendance, real slip, the report beside it."""

	def _report_row(self, emp):
		_cols, rows, _msg = report.execute({"company": COMPANY, "from_date": str(START),
		                                     "to_date": str(END), "employee": emp})[:3]
		return [r for r in rows if r["employee"] == emp][0]

	def test_a_juniors_reds_after_the_free_two_reach_the_slip_and_match_the_report(self):
		_work(self.junior, red_days=5)
		slip = _slip(self.junior)
		row = self._report_row(self.junior)
		self.assertEqual(row["red_deduction"], 300)                 # (5 - 2) x 100
		self.assertEqual(_line(slip, payroll_slip.RED_COMPONENT), 300)
		self.assertEqual(flt(slip.payment_days, 2), row["paid_days"])
		self.assertAlmostEqual(_line(slip, BASIC), row["basic"], 0)
		self.assertAlmostEqual(flt(slip.net_pay, 2), flt(slip.gross_pay - 300, 2), 2)
		# Credits are inside paid days; there is no separate encashment line.
		self.assertFalse([r for r in slip.earnings if r.salary_component == "Leave Encashment"])

	def test_a_senior_pays_two_hundred_a_red(self):
		_work(self.senior, red_days=3)
		slip = _slip(self.senior)
		self.assertEqual(_line(slip, payroll_slip.RED_COMPONENT), 200)  # (3 - 2) x 200

	def test_two_reds_are_free_so_no_line_and_no_record(self):
		_work(self.junior, red_days=2)
		slip = _slip(self.junior)
		self.assertIsNone(_line(slip, payroll_slip.RED_COMPONENT))
		self.assertEqual(_engine(self.junior, payroll_slip.RED_COMPONENT), [])

	def test_contract_staff_carry_no_marks_whatever_their_attendance(self):
		_work(self.contract, red_days=4)
		slip = _slip(self.contract)
		self.assertIsNone(_line(slip, payroll_slip.RED_COMPONENT))
		self.assertEqual(_engine(self.contract, payroll_slip.RED_COMPONENT), [])


class TestReplacedNeverAdded(SlipCase):
	"""T1 (green), T5, T6, T7, T17."""

	def test_red_and_green_lines_and_one_record_each(self):
		slip = _slip(self.junior, _summary(red=300, green=200))
		self.assertEqual(_line(slip, payroll_slip.RED_COMPONENT), 300)
		self.assertEqual(_line(slip, payroll_slip.GREEN_COMPONENT), 200)
		red = _engine(self.junior, payroll_slip.RED_COMPONENT)
		self.assertEqual(len(red), 1)
		self.assertEqual(red[0].docstatus, 1)
		self.assertEqual(getdate(red[0].payroll_date), END)

	def test_saving_twice_writes_nothing_new(self):
		slip = _slip(self.junior, _summary(red=300, green=200))
		net = slip.net_pay
		_resave(slip, _summary(red=300, green=200))
		self.assertEqual(len(_engine(self.junior, payroll_slip.RED_COMPONENT)), 1)
		self.assertEqual(len(_engine(self.junior, payroll_slip.GREEN_COMPONENT)), 1)
		self.assertEqual(_engine(self.junior, payroll_slip.RED_COMPONENT, docstatus=2), [])
		self.assertEqual(slip.net_pay, net)

	def test_a_changed_figure_cancels_the_old_record_and_amends_it(self):
		slip = _slip(self.junior, _summary(red=300))
		first = _engine(self.junior, payroll_slip.RED_COMPONENT)[0].name
		_resave(slip, _summary(red=200))
		rows = _engine(self.junior, payroll_slip.RED_COMPONENT)
		self.assertEqual([r.docstatus for r in rows], [2, 1])
		self.assertEqual(rows[1].amended_from, first)
		self.assertEqual(rows[1].amount, 200)
		self.assertEqual(_line(slip, payroll_slip.RED_COMPONENT), 200)

	def test_falling_to_nothing_cancels_the_record_and_the_line_goes(self):
		slip = _slip(self.junior, _summary(red=300))
		_resave(slip, _summary(red=0))
		self.assertEqual([r.docstatus for r in _engine(self.junior, payroll_slip.RED_COMPONENT)], [2])
		self.assertIsNone(_line(slip, payroll_slip.RED_COMPONENT))

	def test_a_slip_made_again_reuses_the_record(self):
		"""Cancelling a Payroll Entry deletes its draft slips; the next run
		must not stack a second red on the first."""
		slip = _slip(self.junior, _summary(red=300))
		frappe.delete_doc("Salary Slip", slip.name, force=True, ignore_permissions=True)
		again = _slip(self.junior, _summary(red=300))
		rows = _engine(self.junior, payroll_slip.RED_COMPONENT)
		self.assertEqual([r.docstatus for r in rows], [1])
		self.assertEqual(_line(again, payroll_slip.RED_COMPONENT), 300)


class TestWhatTheEngineLeavesAlone(SlipCase):
	"""T8, T9, T13."""

	def test_a_line_hr_typed_by_hand_is_untouched(self):
		hand = _insert({"doctype": "Additional Salary", "employee": self.junior,
		                "company": COMPANY, "currency": "INR",
		                "salary_component": INCENTIVE, "amount": 500,
		                "payroll_date": END, "overwrite_salary_structure_amount": 1},
		               submit=True)
		slip = _slip(self.junior, _summary(red=300))
		_resave(slip, _summary(red=0))
		self.assertEqual(frappe.db.get_value("Additional Salary", hand.name, "docstatus"), 1)
		self.assertEqual(_line(slip, INCENTIVE), 500)

	def test_nothing_is_written_while_the_rule_set_is_off(self):
		_switch(False)
		_slip(self.junior, _summary(red=300))
		self.assertEqual(_engine(self.junior, payroll_slip.RED_COMPONENT), [])

	def test_a_paid_slip_and_its_lines_are_never_changed(self):
		slip = _slip(self.junior, _summary(red=300))
		slip.flags.ignore_permissions = True
		slip.submit()
		record = _engine(self.junior, payroll_slip.RED_COMPONENT)[0].name
		with self.assertRaises(frappe.LinkExistsError):
			doc = frappe.get_doc("Additional Salary", record)
			doc.flags.ignore_permissions = True
			doc.cancel()
		with patch.object(payroll_slip, "month_summary", return_value=_summary(red=900)):
			payroll_slip.on_salary_slip_validate(frappe.get_doc("Salary Slip", slip.name))
		self.assertEqual([r.amount for r in _engine(self.junior, payroll_slip.RED_COMPONENT)], [300])
		slip.reload()
		slip.flags.ignore_permissions = True
		slip.cancel()


class TestAFailureIsAllOrNothing(SlipCase):
	"""T10."""

	def test_a_failure_half_way_leaves_no_half_written_lines(self):
		real = payroll_slip._set_additional_salary

		def red_then_fail(slip, component, *a, **kw):
			if component == payroll_slip.GREEN_COMPONENT:
				frappe.throw("forced failure for the test")
			return real(slip, component, *a, **kw)

		with patch.object(payroll_slip, "_set_additional_salary", side_effect=red_then_fail):
			slip = _slip(self.junior, _summary(red=300, green=200, paid_days=20))
		frappe.local.message_log = []
		self.assertEqual(_engine(self.junior, payroll_slip.RED_COMPONENT), [],
		                 "the red written before the failure must be undone")
		self.assertIsNone(_line(slip, payroll_slip.RED_COMPONENT))
		self.assertEqual(flt(slip.payment_days), 20, "paid days still reach the slip")
		self.assertTrue(frappe.db.exists("Comment", {
			"reference_doctype": "Salary Slip", "reference_name": slip.name,
			"content": ("like", "%red and green lines%")}))
		log = frappe.get_all("Error Log", filters={"method": ("like", "%" + slip.name + "%")},
		                     fields=["method", "error"], order_by="creation desc", limit=1)
		self.assertTrue(log, "the failure must reach the Error Log, named by the slip")
		for word in ("Jaya", "L067 Junior", "31000"):
			self.assertNotIn(word, log[0].method)


class TestTheRestOfTheSlip(SlipCase):
	"""T12, T14, T16 (Arrear), T15 (Why?)."""

	def test_year_to_date_follows_the_engines_net_pay(self):
		slip = _slip(self.junior, _summary(red=300, green=200, paid_days=20))
		self.assertEqual(flt(slip.year_to_date, 2), flt(slip.net_pay, 2))
		self.assertEqual(flt(slip.gross_year_to_date, 2), flt(slip.gross_pay, 2))
		self.assertEqual(flt(slip.month_to_date, 2), flt(slip.net_pay, 2))

	def test_the_held_days_note_reaches_a_brand_new_slip(self):
		"""During validate a new slip is not in the database, so a comment on
		it was refused and the note was lost. It is now posted after the save."""
		summary = _summary(paid_days=20)
		summary.days_held = 1
		slip = _slip(self.junior, summary)
		self.assertTrue(frappe.db.exists("Comment", {
			"reference_doctype": "Salary Slip", "reference_name": slip.name,
			"content": ("like", "%held for a missing check-out%")}))
		frappe.db.delete("Comment", {"reference_name": slip.name})

	def test_a_leavers_line_is_dated_on_the_relieving_date(self):
		leaver = _employee("Lata", grade=JUNIOR, relieving=add_days(END, -5))
		try:
			_wipe(leaver)
			_slip(leaver, _summary(red=300, paid_days=20))
			rows = _engine(leaver, payroll_slip.RED_COMPONENT)
			self.assertEqual(len(rows), 1)
			self.assertEqual(getdate(rows[0].payroll_date), getdate(add_days(END, -5)))
		finally:
			_wipe(leaver)
			frappe.db.set_value("Employee", leaver, "relieving_date", None)

	def test_an_arrear_stays_whole_only_when_it_does_not_depend_on_payment_days(self):
		"""Why DTC's Arrear component must have Depends on Payment Days off: a
		released held day typed as an Arrear would otherwise be scaled by paid
		days over days in the month."""
		for comp in (ARREAR_WHOLE, ARREAR_SCALED):
			_insert({"doctype": "Additional Salary", "employee": self.junior, "company": COMPANY,
			         "currency": "INR", "salary_component": comp, "amount": 1000,
			         "payroll_date": END}, submit=True)
		slip = _slip(self.junior, _summary(paid_days=DAYS / 2.0))
		self.assertEqual(_line(slip, ARREAR_WHOLE), 1000)
		self.assertNotEqual(_line(slip, ARREAR_SCALED), 1000)

	def test_the_why_sheet_never_calls_an_engine_line_hand_entered(self):
		user = "jaya@l067.test"
		if not frappe.db.exists("User", user):
			_insert({"doctype": "User", "email": user, "first_name": "Jaya",
			         "send_welcome_email": 0, "roles": [{"role": "Employee"}]})
		frappe.db.set_value("Employee", self.junior, "user_id", user)
		_slip(self.junior, _summary(red=300))
		record = _engine(self.junior, payroll_slip.RED_COMPONENT)[0].name
		frappe.local.conf["features"] = list(PAYROLL_ON)
		frappe.set_user(user)
		try:
			self.assertEqual(pay_api.get_deduction_explanation(record), {"from_attendance": True})
		finally:
			frappe.set_user("Administrator")
			frappe.local.conf.pop("features", None)
			frappe.db.set_value("Employee", self.junior, "user_id", None)


class TestTheWiringStaysInPlace(FrappeTestCase):
	"""Pins: a bad merge that drops the wiring fails here."""

	def test_the_slip_hook_is_registered(self):
		self.assertIn("alvoraa_portal.payroll_slip.on_salary_slip_validate",
		              frappe.get_hooks("doc_events").get("Salary Slip", {}).get("validate", []))
		self.assertIn("alvoraa_portal.payroll_slip.post_slip_notes",
		              frappe.get_hooks("doc_events").get("Salary Slip", {}).get("on_update", []))

	def test_the_engine_owns_red_and_green_and_nothing_hr_types(self):
		owned = [c for c, _f in payroll_slip.ENGINE_LINES]
		self.assertEqual(owned[:2], ["Red Value", "Green Value"])
		for c in ("Incentive", "Advance Deduction", "Other Deduction", "Arrear"):
			self.assertNotIn(c, owned)
		for _c, figure in payroll_slip.ENGINE_LINES:
			self.assertTrue(hasattr(MonthSummary(), figure), figure)
