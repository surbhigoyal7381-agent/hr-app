"""Leave is counted against the company's FINANCIAL year, not the calendar year.

Every caller used frappe.utils.get_year_start(), which returns 1 January. On a
company running April-March that is wrong by three months, and it is wrong
silently - the number simply comes out too low or too high.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal.hr_api import _leave_year_start
from alvoraa_goals.tests.utils import ensure_company


class TestLeaveYearStart(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.company = ensure_company()
		# Both years, every time. Creating one per test made the result depend on
		# execution order: a year left behind (or rolled back) by a sibling test
		# changed which one get_fiscal_year matched.
		self._fy("TEST-2025-2026", "2025-04-01", "2026-03-31")
		self._fy("TEST-2026-2027", "2026-04-01", "2027-03-31")

	def tearDown(self):
		frappe.db.rollback()

	def _fy(self, name, start, end):
		if frappe.db.exists("Fiscal Year", name):
			return name
		doc = frappe.get_doc({
			"doctype": "Fiscal Year",
			"year": name,
			"year_start_date": start,
			"year_end_date": end,
			# This version's controller reads self.auto_created; without it the
			# insert dies with AttributeError.
			"auto_created": 0,
			# get_fiscal_year only matches ACTIVE years - "not in any active
			# Fiscal Year" is the error when this is left to chance.
			"disabled": 0,
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		# Commit: get_fiscal_year runs its own query, and the tests roll back
		# after each case, so an uncommitted fixture is not reliably visible.
		frappe.db.commit()
		return doc.name

	def test_uses_the_fiscal_year_when_one_exists(self):
		"""April-March company: a date in August belongs to the year that began 1 April."""
		got = _leave_year_start("2026-08-22", self.company)
		self.assertEqual(str(got), "2026-04-01",
		                 "August should count from 1 April, not 1 January")

	def test_falls_back_to_the_calendar_year_when_no_year_covers_the_date(self):
		"""dev and demo have no Fiscal Year records at all, so get_fiscal_year()
		raises FiscalYearError. Without the fallback every leave screen breaks.

		A date no Fiscal Year covers reproduces that, which a made-up company name
		does NOT: these years carry no company links, so they match every company.
		"""
		got = _leave_year_start("2019-06-15", self.company)
		self.assertEqual(str(got), "2019-01-01")

	def test_a_date_before_the_fiscal_year_start_belongs_to_the_previous_one(self):
		got = _leave_year_start("2026-02-10", self.company)
		self.assertEqual(str(got), "2025-04-01",
		                 "February is still the fiscal year that began the previous April")
