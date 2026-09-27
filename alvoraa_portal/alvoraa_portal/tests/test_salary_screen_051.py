"""Slice 051: the year-so-far figures the salary screen reads off the payslip.

**Read, never added up.** Frappe HR's payroll run works `year_to_date` and
`gross_year_to_date` out against the payroll period and stores them on the slip.
Summing the slips the screen happens to list gives a different number for a
mid-year joiner, for anyone whose slips do not start in April, and for anyone
whose list is capped - and it would be the portal's number rather than payroll's,
which is the one a Form 16 will agree with.

So the test that matters is not "is there a figure": it is "is it the one on the
document, even when the document disagrees with the arithmetic". The fixture
below deliberately stores a year-to-date that is NOT the sum of the slips, and
asserts the payload returns the stored figure.

The screen side - both pay figures, the Why? control, the year line appearing
only when payroll worked one out - is driven in a real DOM by
`alvoraa_portal/tests/portal_salary_test.js`, because a check that read
`portal.js` for a string would pass while the line sat in a branch that never
runs.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import hr_api
from alvoraa_portal.tests import fixtures_043 as fx

# Chosen so it can only have come from the document. It is not the sum of the
# two slips, not either slip's net, and not a round number.
STORED_YTD = 482350.37
STORED_GROSS_YTD = 560000.11


def _payroll_on():
	frappe.local.conf["features"] = ["portal", "leaves", "attendance",
	                                 "expenses", "payroll"]


def _payroll_clear():
	frappe.local.conf.pop("features", None)


class TestTheYearSoFarIsReadNotComputed(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fx.ensure_company()
		fx.ensure_branches()
		cls.login = fx.user("ytd051", ["Employee"])
		cls.emp = fx.employee("Ytd051", branch=fx.STORE_A, login=cls.login)

		# Two slips, so "the sum of the list" is a real rival answer.
		cls.older = fx.salary_slip(cls.emp)
		cls.newer = fx.salary_slip(
			cls.emp,
			start=frappe.utils.add_days(frappe.utils.nowdate(), -30),
			end=frappe.utils.nowdate())

		for name, net in ((cls.older, 40000), (cls.newer, 48234.61)):
			frappe.db.set_value("Salary Slip", name, {
				"net_pay": net,
				"rounded_total": round(net),
				"gross_pay": net + 3765.39,
			}, update_modified=False)

		# Only the NEWEST slip carries the year figures, which is how payroll
		# writes them: each slip holds the year up to its own end date.
		frappe.db.set_value("Salary Slip", cls.newer, {
			"year_to_date": STORED_YTD,
			"gross_year_to_date": STORED_GROSS_YTD,
		}, update_modified=False)
		frappe.db.commit()

	def setUp(self):
		frappe.set_user(self.login)
		_payroll_on()

	def tearDown(self):
		_payroll_clear()
		frappe.set_user("Administrator")

	def test_the_fixture_really_disagrees_with_the_arithmetic(self):
		"""Otherwise the assertion below passes for the wrong reason."""
		total = sum(frappe.db.get_value("Salary Slip", n, "net_pay")
		            for n in (self.older, self.newer))
		self.assertNotAlmostEqual(
			total, STORED_YTD, places=2,
			msg="the fixture's slips add up to the stored year figure, so this "
			    "file cannot tell reading from summing")

	def test_the_payload_carries_the_stored_year_figures(self):
		payload = hr_api.get_payslip(self.newer)
		self.assertAlmostEqual(payload["year_to_date"], STORED_YTD, places=2)
		self.assertAlmostEqual(payload["gross_year_to_date"],
		                       STORED_GROSS_YTD, places=2)

	def test_it_is_the_document_s_figure_and_not_the_sum_of_the_list(self):
		payload = hr_api.get_payslip(self.newer)
		total = sum(frappe.db.get_value("Salary Slip", n, "net_pay")
		            for n in (self.older, self.newer))
		self.assertNotAlmostEqual(
			payload["year_to_date"], total, places=2,
			msg="the screen is adding the slips up rather than reading the "
			    "figure payroll stored")

	def test_a_slip_with_no_year_figures_returns_zero_not_a_guess(self):
		"""An older slip payroll never wrote a year figure on.

		Zero is the honest answer, and the screen draws no year line for it. A
		figure worked out here would be the portal inventing one.
		"""
		payload = hr_api.get_payslip(self.older)
		self.assertEqual(payload["year_to_date"], 0)
		self.assertEqual(payload["gross_year_to_date"], 0)

	def test_both_pay_figures_reach_the_screen(self):
		"""The rounded total AND the exact net, on the same payload.

		555 of 800 PP Jewellers slips print a net that is not the amount paid.
		The screen shows both; it can only do that if both are sent.
		"""
		payload = hr_api.get_payslip(self.newer)
		self.assertAlmostEqual(payload["net_pay"], 48234.61, places=2)
		self.assertEqual(payload["rounded_total"], 48235)
		self.assertNotEqual(payload["net_pay"], payload["rounded_total"])
