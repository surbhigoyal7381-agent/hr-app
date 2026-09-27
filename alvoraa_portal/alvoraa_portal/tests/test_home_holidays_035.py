"""Home's holiday card shows the employee's own holidays (slice 035, commit 2).

Home used to read every holiday list on the site. At PP Jewellers 363 store staff
were told Diwali, Dussehra, Guru Nanak Jayanti and Christmas were holidays -
Head Office's, not theirs. It also stopped at 31 December, hiding January to
March of an April-March list.

The card now finds the list the way payroll does. In this Frappe HR version that
is Holiday List Assignment only: the Employee form's holiday_list field and the
company default are not read by pay or leave at all. So the fixtures here set the
Employee field to a DIFFERENT list on purpose - the card must ignore it, exactly
as the salary slip does, and must never show a calendar payroll ignores.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from alvoraa_portal import hr_api
from alvoraa_portal.tests.leave_fixtures import (
	assign_holiday_list,
	ensure_employee,
	ensure_user,
	link_user_to_employee,
)

STORE = "HH035 Store Holidays"
HEAD_OFFICE = "HH035 Head Office Holidays"
WORKER_USER = "holiday.worker035@example.com"
LOOKUP = "erpnext.setup.doctype.employee.employee.get_holiday_list_for_employee"


def _dates(rows):
	return {str(getdate(r["holiday_date"])) for r in rows}


def _holiday_list(name, named, weekly_offs=()):
	"""A list from 2026-01-01 (what assign_holiday_list assigns from) to past next March.

	Kept, not recreated: an assignment points at it. Its holidays are rewritten
	every run, because they are dated from today and yesterday's run left its own.
	"""
	rows = ([{"holiday_date": d, "description": f"{name} {d}"} for d in named]
	        + [{"holiday_date": d, "description": "Weekly off", "weekly_off": 1} for d in weekly_offs])
	end = add_days(today(), 400)
	if frappe.db.exists("Holiday List", name):
		doc = frappe.get_doc("Holiday List", name)
		doc.to_date = max(getdate(doc.to_date), getdate(end))
		doc.set("holidays", rows)
		doc.save(ignore_permissions=True)
		return doc.name
	doc = frappe.get_doc({
		"doctype": "Holiday List",
		"holiday_list_name": name,
		"from_date": "2026-01-01",
		"to_date": end,
		"holidays": rows,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


class TestHomeHolidaysAreTheEmployeesOwn(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		t = getdate(today())
		cls.own = str(add_days(t, 3))
		cls.own_weekly_off = str(add_days(t, 4))
		cls.head_office_only = str(add_days(t, 5))
		# 26 January after the coming 31 December: inside an April-March list.
		cls.next_january = f"{t.year + 1}-01-26"

		store = _holiday_list(STORE, [cls.own, cls.next_january], [cls.own_weekly_off])
		head_office = _holiday_list(HEAD_OFFICE, [cls.head_office_only])

		cls.worker = ensure_employee("Holiday035", "Worker")
		link_user_to_employee(cls.worker, ensure_user(WORKER_USER, roles=("Employee",)))
		assign_holiday_list(cls.worker, store)
		# The old field points somewhere else. Payroll ignores it; so must Home.
		frappe.db.set_value("Employee", cls.worker, "holiday_list", head_office)
		frappe.db.commit()

	def setUp(self):
		frappe.set_user(WORKER_USER)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_another_lists_holidays_never_appear(self):
		d = hr_api.get_employee_dashboard()
		self.assertIn(self.own, _dates(d["holidays"]))
		self.assertNotIn(self.head_office_only, _dates(d["holidays"]),
		                 "Head Office's holiday shown to a store employee")
		self.assertIsNone(d["holiday_note"])

	def test_weekly_offs_are_not_listed_as_holidays(self):
		d = hr_api.get_employee_dashboard()
		self.assertNotIn(self.own_weekly_off, _dates(d["holidays"]))

	def test_the_card_runs_to_the_end_of_the_list_not_31_december(self):
		d = hr_api.get_employee_dashboard()
		self.assertIn(self.next_january, _dates(d["holidays"]))

	def test_no_list_says_so_in_plain_words(self):
		with patch(LOOKUP, return_value=None):
			d = hr_api.get_employee_dashboard()
		self.assertEqual(d["holidays"], [])
		self.assertEqual(d["holiday_note"],
		                 "No holiday list is assigned to you yet. Ask HR to set one up.")


class TestHomeCardShowsTheNote(FrappeTestCase):
	"""The page passes the server's note to the card, and the card shows it."""

	def test_the_page_passes_and_shows_the_note(self):
		import os
		import re

		from alvoraa_portal.tests import portal_source

		# Follows the page's Jinja includes (slice 034 US-10, AC-37). These three
		# slice 035 checks read the page too; without this they would look at a
		# short shell and pass while proving nothing.
		page = portal_source.read_page(encoding="utf-8")
		self.assertIn("renderHolidays(data.holidays || [], data.holiday_note)", page)
		body = re.search(r"function renderHolidays\(holidays, note\) \{(.*?)\n\}", page, re.S)
		self.assertTrue(body, "renderHolidays(holidays, note) not found - update this test if it moved")
		self.assertIn("esc(note)", body.group(1), "the note must be shown, escaped")


class TestHomeUsesTheLookupPayrollUses(FrappeTestCase):
	"""The pin: the card and the salary slip resolve holidays through ONE function.

	If anyone points the card back at Employee.holiday_list, or at any lookup of
	its own, the screen could again show holidays payroll does not honour. On
	aahr.alvoraa.co that is 4 of 5 employees today.
	"""

	def test_salary_slip_and_home_share_the_lookup(self):
		import importlib

		erpnext_employee = importlib.import_module("erpnext.setup.doctype.employee.employee")
		salary_slip = importlib.import_module("hrms.payroll.doctype.salary_slip.salary_slip")
		self.assertIs(salary_slip.get_holiday_list_for_employee,
		              erpnext_employee.get_holiday_list_for_employee)

	def test_home_asks_that_lookup_and_nothing_else(self):
		frappe.set_user("Administrator")
		emp = ensure_employee("Holiday035", "Worker")
		asked = []

		def lookup(employee, raise_exception=True, as_on=None):
			asked.append(employee)
			return HEAD_OFFICE

		try:
			with patch(LOOKUP, side_effect=lookup):
				rows, note = hr_api._own_upcoming_holidays(emp, today())
		finally:
			frappe.db.rollback()
		self.assertEqual(asked, [emp])
		self.assertIsNone(note)
		# Whatever the lookup answers is what the card shows - here Head Office's.
		self.assertTrue(all(r["description"].startswith(HEAD_OFFICE) for r in rows), rows)

	def test_the_employee_field_alone_gives_no_holidays(self):
		"""An Employee holiday_list with no assignment: payroll finds nothing, so Home does too."""
		frappe.set_user("Administrator")
		emp = ensure_employee("Holiday035", "Unassigned")
		frappe.db.set_value("Employee", emp, "holiday_list", HEAD_OFFICE)
		try:
			from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

			payroll_sees = get_holiday_list_for_employee(emp, raise_exception=False)
			rows, note = hr_api._own_upcoming_holidays(emp, today())
			if payroll_sees:
				self.skipTest("the site's company carries a holiday assignment, so "
				              "every employee has a list; the no-list case is covered by the mock")
			self.assertEqual(rows, [])
			self.assertTrue(note)
		finally:
			frappe.db.rollback()
