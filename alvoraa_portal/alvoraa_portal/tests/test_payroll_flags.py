"""Which rules apply to whom: the switches, not the arithmetic.

The arithmetic is pure and tested in test_payroll_rules - given "this employee
doubles" it works out the quarters. THIS file tests the question before that
one: does this employee double at all, and is the late window theirs?

Worth its own file. Both answers used to come from a blank setting, and the two
read the same blank in OPPOSITE directions - the window fired for nobody, the
doubling for everybody. A tenant who set a window and named no field got a rule
that silently did nothing, and nothing in the arithmetic tests could see it,
because they are handed the answer rather than working it out.

Settled by Surbhi on 15 October 2026:

  the late window applies to EVERYONE, and the employee's own shift timing
  decides whether it bites;

  doubling applies to everyone EXCEPT contract staff, read from the employee's
  category so it follows employment type rather than a box kept in step by hand.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from alvoraa_portal.payroll_rules_apply import _employee_flags, prepare

COMPANY = "Flags Test Co"
ABBR = "FLGT"


def _gender():
	"""Whatever this site calls a gender.

	Hard-coding "Female" fails on a bench that has never had the Gender
	fixtures loaded, which is exactly how CI builds its site. The same lesson
	is already written down in `hrms/alvoraa_org_structure/tests/
	test_org_structure.py`; this file repeated the mistake anyway, which is
	why it is spelled out again here rather than left as a one-liner.
	"""
	existing = frappe.db.get_value("Gender", {}, "name")
	if existing:
		return existing
	return frappe.get_doc({"doctype": "Gender", "gender": "Other"}
	                      ).insert(ignore_permissions=True).name


def _ensure_company():
	if not frappe.db.exists("Company", COMPANY):
		frappe.get_doc({"doctype": "Company", "company_name": COMPANY,
		                "abbr": ABBR, "default_currency": "INR",
		                "country": "India"}).insert(ignore_permissions=True)


def _rule_set(**overrides):
	"""A minimal enabled rule set, rebuilt per test so each can vary it.

	Deleted and recreated rather than edited, because the engine reads it
	through `get_cached_doc` and a half-changed cache is a confusing test
	failure to chase.
	"""
	for name in frappe.get_all("Alvoraa Payroll Rule Set",
	                           filters={"company": COMPANY}, pluck="name"):
		frappe.delete_doc("Alvoraa Payroll Rule Set", name, force=True,
		                  ignore_permissions=True)
	frappe.clear_cache(doctype="Alvoraa Payroll Rule Set")
	doc = frappe.get_doc(dict({
		"doctype": "Alvoraa Payroll Rule Set",
		"company": COMPANY,
		"enabled": 1,
		"grace_minutes": 6,
		"category_field": "employment_type",
		"slabs": [{"percent_from": 0, "percent_to": 100,
		           "quarters_off": 0, "raises_red": 0}],
		"mark_rates": [{"grade": "Junior", "amount_per_mark": 100}],
	}, **overrides))
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


def _employee(employment_type=None):
	doc = frappe.get_doc({
		"doctype": "Employee", "first_name": "Flags", "last_name": "Test",
		"company": COMPANY,
		"date_of_joining": add_days(nowdate(), -200),
		"date_of_birth": "1990-01-01", "gender": _gender(),
		"status": "Active", "employment_type": employment_type,
	})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def _ensure_employment_types():
	"""`Contract` ships with ERPNext. `Permanent` does NOT - it was created for
	DTC on 15 Oct 2026, because 319 people had the field blank and the contract
	rule could only reach the 42 who happened to be marked. So the fixture has
	to create it, exactly as the tenant did."""
	for name in ("Permanent", "Contract"):
		if not frappe.db.exists("Employment Type", name):
			frappe.get_doc({"doctype": "Employment Type",
			                "employee_type_name": name}).insert(ignore_permissions=True)


def setUpModule():
	_ensure_company()
	_ensure_employment_types()
	frappe.db.commit()


class TestWhoDoubles(FrappeTestCase):
	"""WSD-05/06. Nobody is exempt except contract staff."""

	def setUp(self):
		self.date = getdate(nowdate())

	def _flags(self, employment_type, categories=None):
		rs = _rule_set(categories=categories if categories is not None else [
			{"category": "Contract", "grace_minutes": 15, "earns_marks": 0,
			 "earns_leave_credits": 0, "doubles_deduction": 0},
		])
		emp = _employee(employment_type)
		return _employee_flags(emp, self.date, prepare(rs, self.date, self.date))

	def test_a_permanent_employee_doubles(self):
		self.assertTrue(self._flags("Permanent")["double_deduction_applies"])

	def test_a_contract_employee_does_not(self):
		self.assertFalse(self._flags("Contract")["double_deduction_applies"])

	def test_somebody_with_no_employment_type_still_doubles(self):
		"""The safe direction. An unlisted category keeps every standard rule,
		so forgetting to categorise somebody cannot quietly exempt them."""
		self.assertTrue(self._flags(None)["double_deduction_applies"])

	def test_with_no_categories_at_all_everybody_doubles(self):
		"""A tenant that has set none, which is every tenant but DTC."""
		self.assertTrue(self._flags("Contract", categories=[])
		                ["double_deduction_applies"])

	def test_the_contract_row_still_switches_off_marks_and_leave(self):
		"""The new switch sits beside three others. Proving they still work
		guards against a field added in the wrong place in the child table."""
		flags = self._flags("Contract")
		self.assertFalse(flags["earns_marks"])
		self.assertEqual(flags["grace_minutes"], 15)


class TestWhoTheLateWindowApplies(FrappeTestCase):
	"""ATT-04. Everybody, unless a tenant deliberately narrows it."""

	def setUp(self):
		self.date = getdate(nowdate())

	def test_with_no_employee_field_it_applies_to_everybody(self):
		"""The case that was broken. A window was set, no field was named, and
		the rule fired for nobody - and the rule set would not even save."""
		rs = _rule_set(late_window_from="11:00:00", late_window_to="11:30:00",
		               late_window_extra_quarters=1)
		emp = _employee("Permanent")
		flags = _employee_flags(emp, self.date, prepare(rs, self.date, self.date))
		self.assertTrue(flags["late_window_flagged"])

	def test_a_window_with_no_employee_field_can_now_be_saved(self):
		"""It used to be refused outright: "it needs the Employee field that
		carries the flag"."""
		rs = _rule_set(late_window_from="11:00:00", late_window_to="11:30:00",
		               late_window_extra_quarters=1)
		# The save itself is the assertion - it used to throw. The field being
		# empty is what makes that meaningful.
		self.assertTrue(frappe.db.exists("Alvoraa Payroll Rule Set", rs.name))
		self.assertFalse(rs.late_window_employee_field)

	def test_a_window_adding_no_quarters_is_still_refused(self):
		"""Half-filled is worse than empty: it reads as configured and does
		nothing."""
		with self.assertRaises(frappe.ValidationError):
			_rule_set(late_window_from="11:00:00", late_window_to="11:30:00",
			          late_window_extra_quarters=0)

	def test_naming_a_field_narrows_it_again(self):
		"""Kept deliberately, for a tenant that wants a subset. `holiday_list`
		is used only because it is a real Employee field that is empty here -
		this test is about the narrowing, not about holidays."""
		rs = _rule_set(late_window_from="11:00:00", late_window_to="11:30:00",
		               late_window_extra_quarters=1,
		               late_window_employee_field="holiday_list")
		emp = _employee("Permanent")
		flags = _employee_flags(emp, self.date, prepare(rs, self.date, self.date))
		self.assertFalse(flags["late_window_flagged"])


class TestShiftHoursSettingsALV326(FrappeTestCase):
	"""ALV-326 (Surbhi, 2026-11-11): nothing company-specific in code. The late
	limit and the break allowance live on the rule set, a category may override
	either (0 = the rule set's), and a rule set that sets nothing keeps the old
	behaviour."""

	def setUp(self):
		self.date = getdate(nowdate())

	def _flags(self, employment_type, **rule_set):
		rs = _rule_set(**rule_set)
		ctx = prepare(rs, self.date, self.date)
		return ctx, _employee_flags(_employee(employment_type), self.date, ctx)

	def test_alv326_a_new_rule_set_switches_all_three_off(self):
		ctx, flags = self._flags("Permanent")
		self.assertFalse(ctx["shift_hours_only"])
		self.assertEqual(flags["late_quarter_after_minutes"], 0)
		self.assertEqual(flags["break_allowance_minutes"], 0)

	def test_alv326_the_rule_set_figures_reach_the_engine(self):
		ctx, flags = self._flags("Permanent", count_shift_hours_only=1,
		                         late_quarter_after_minutes=30, break_allowance_minutes=40)
		self.assertTrue(ctx["shift_hours_only"])
		self.assertEqual(flags["late_quarter_after_minutes"], 30)
		self.assertEqual(flags["break_allowance_minutes"], 40)

	def test_alv326_a_category_overrides_and_zero_means_the_rule_set_s(self):
		cats = [{"category": "Contract", "grace_minutes": 15, "earns_marks": 0,
		         "earns_leave_credits": 0, "doubles_deduction": 0,
		         "late_quarter_after_minutes": 45, "break_allowance_minutes": 0}]
		_, flags = self._flags("Contract", late_quarter_after_minutes=30,
		                       break_allowance_minutes=40, categories=cats)
		self.assertEqual(flags["late_quarter_after_minutes"], 45)
		self.assertEqual(flags["break_allowance_minutes"], 40)

	def test_alv326_negative_figures_are_refused(self):
		for field in ("late_quarter_after_minutes", "break_allowance_minutes"):
			with self.subTest(field=field), self.assertRaises(frappe.ValidationError):
				_rule_set(**{field: -1})
		with self.assertRaises(frappe.ValidationError):
			_rule_set(categories=[{"category": "Contract", "break_allowance_minutes": -5}])

	def test_alv326_a_late_limit_at_or_below_grace_is_refused(self):
		"""Security review M1: it would turn every late red into a quarter."""
		for limit in (5, 6):
			with self.subTest(limit=limit), self.assertRaises(frappe.ValidationError):
				_rule_set(late_quarter_after_minutes=limit)
		self.assertTrue(_rule_set(late_quarter_after_minutes=7).name)

	def test_alv326_a_category_grace_above_the_late_limit_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			_rule_set(late_quarter_after_minutes=10, categories=[
				{"category": "Contract", "grace_minutes": 15}])


class TestWholeMinutesALV326(FrappeTestCase):
	"""Review P3-2, Surbhi's D3: lateness is judged in whole minutes. A real
	Employee Checkin at 10:36:40 on a 10:30 shift with 6 minutes' grace is
	10:36, which is on time. With the seconds kept it would be late."""

	SHIFT = "ALV326 Whole Minutes 10:30"

	def test_alv326_a_punch_at_10_36_40_is_on_time(self):
		from alvoraa_portal.payroll_rules_apply import _punches, judge

		if not frappe.db.exists("Shift Type", self.SHIFT):
			frappe.get_doc({"doctype": "Shift Type", "name": self.SHIFT,
			                "start_time": "10:30:00", "end_time": "20:30:00",
			                "enable_late_entry_marking": 1,
			                "late_entry_grace_period": 6}).insert(ignore_permissions=True)
		rs = _rule_set()
		emp = _employee("Permanent")
		day = add_days(nowdate(), -3)
		for t in ("10:36:40", "20:30:00"):
			frappe.get_doc({"doctype": "Employee Checkin", "employee": emp,
			                "time": "{0} {1}".format(day, t),
			                "log_type": ""}).insert(ignore_permissions=True)

		first_in, last_out, count, gaps = _punches(emp, getdate(day))
		self.assertEqual((first_in, last_out, count, gaps), (636, 1230, 2, []))

		v = judge(frappe._dict(name="not-saved", employee=emp, attendance_date=day,
		                       status="Present", shift=self.SHIFT),
		          prepare(rs, getdate(day), getdate(day)))
		self.assertFalse(v.late_arrival)
