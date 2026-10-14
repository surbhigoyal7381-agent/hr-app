"""Green eligibility is dated, because DTC change it with the seasons.

The resolution itself - given an employee and a day, which grant applies - is
pure, so it is tested here without a site. The database side (overlap refusal,
bulk grant) needs a bench and lives in the integration class below.

WHY THIS EXISTS AT ALL. Eligibility used to be one field on Employee. That
field says what is true today and forgets what was true in October. Re-running
October in December would then apply December's rules to a month already paid -
inventing green marks that nobody earned, or removing ones that were. A dated
row per employee is Frappe HR's own shape for this, the same as Shift
Assignment and Salary Structure Assignment.
"""

import unittest
from datetime import date

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal.payroll_rules_apply import _green_on

D = date


def ctx(windows):
	return {"green_windows": windows}


class TestResolvingAGrantByDate(unittest.TestCase):
	"""Pure. No site needed."""

	DIWALI = (D(2026, 10, 15), D(2026, 11, 15), "both")
	NORMAL = (D(2026, 1, 1), None, "none")

	def setUp(self):
		self.ctx = ctx({"EMP-1": [self.NORMAL, self.DIWALI]})

	def test_a_day_inside_the_festive_window_gets_the_festive_grant(self):
		self.assertEqual(_green_on("EMP-1", D(2026, 10, 20), self.ctx), "both")

	def test_the_first_and_last_day_of_a_window_are_inside_it(self):
		"""Boundaries, because a season that starts a day late is a complaint."""
		self.assertEqual(_green_on("EMP-1", D(2026, 10, 15), self.ctx), "both")
		self.assertEqual(_green_on("EMP-1", D(2026, 11, 15), self.ctx), "both")

	def test_the_day_before_and_after_fall_back_to_the_standing_grant(self):
		self.assertEqual(_green_on("EMP-1", D(2026, 10, 14), self.ctx), "none")
		self.assertEqual(_green_on("EMP-1", D(2026, 11, 16), self.ctx), "none")

	def test_an_open_ended_grant_covers_every_later_day(self):
		self.assertEqual(_green_on("EMP-1", D(2030, 6, 1), self.ctx), "none")

	def test_the_later_start_wins_where_two_grants_overlap(self):
		"""The rule that makes a festive season one row instead of three.

		A standing open-ended grant plus a dated Diwali window: inside the
		window the window wins, outside it the standing grant does."""
		self.assertEqual(_green_on("EMP-1", D(2026, 10, 20), self.ctx), "both")
		self.assertEqual(_green_on("EMP-1", D(2026, 12, 1), self.ctx), "none")

	def test_the_order_rows_arrive_in_makes_no_difference(self):
		"""The bug this test was written for. Scanning for the first match let
		an open-ended standing grant swallow every later window, so Diwali
		would have done nothing at all."""
		forwards = ctx({"E": [self.NORMAL, self.DIWALI]})
		backwards = ctx({"E": [self.DIWALI, self.NORMAL]})
		for c in (forwards, backwards):
			self.assertEqual(_green_on("E", D(2026, 10, 20), c), "both")
			self.assertEqual(_green_on("E", D(2026, 10, 1), c), "none")

	def test_a_day_before_any_grant_resolves_to_nothing(self):
		"""The caller then falls back to the Employee field, which is how a
		tenant with no dated rows keeps working unchanged."""
		self.assertEqual(_green_on("EMP-1", D(2025, 6, 1), self.ctx), "")

	def test_an_employee_with_no_grants_resolves_to_nothing(self):
		self.assertEqual(_green_on("EMP-NONE", D(2026, 10, 20), self.ctx), "")

	def test_october_is_still_october_when_rerun_in_december(self):
		"""The whole reason the field was not enough.

		Diwali widened eligibility from 15 October. A day on 10 October was not
		covered then and must not become covered just because a reprocess runs
		later."""
		self.assertEqual(_green_on("EMP-1", D(2026, 10, 10), self.ctx), "none")
		self.assertEqual(_green_on("EMP-1", D(2026, 10, 20), self.ctx), "both")

	def test_night_only_and_morning_only_are_kept_apart(self):
		c = ctx({"E": [(D(2026, 1, 1), None, "night green")]})
		self.assertEqual(_green_on("E", D(2026, 5, 5), c), "night green")


class TestGreenEligibilityRecords(FrappeTestCase):
	"""Needs a site: the overlap refusal and the bulk grant."""

	EMP = None

	def _employee(self):
		if TestGreenEligibilityRecords.EMP:
			return TestGreenEligibilityRecords.EMP
		company = frappe.db.get_value("Company", {}, "name")
		doc = frappe.get_doc({
			"doctype": "Employee", "first_name": "Green", "last_name": "Test",
			"company": company, "date_of_joining": "2026-01-01",
			"date_of_birth": "1990-01-01", "gender": "Female", "status": "Active",
		})
		doc.flags.ignore_permissions = True
		doc.insert()
		TestGreenEligibilityRecords.EMP = doc.name
		return doc.name

	def _grant(self, from_date, to_date, eligibility="Both"):
		doc = frappe.get_doc({
			"doctype": "Alvoraa Green Eligibility",
			"employee": self._employee(),
			"from_date": from_date, "to_date": to_date,
			"eligibility": eligibility, "reason": "test",
		})
		doc.flags.ignore_permissions = True
		doc.insert()
		return doc

	def test_two_periods_that_overlap_are_refused(self):
		"""A day covered twice has two answers, and which applies would depend
		on the order the rows were read in."""
		self._grant("2026-10-01", "2026-10-31")
		with self.assertRaises(frappe.ValidationError):
			self._grant("2026-10-15", "2026-11-15")

	def test_periods_that_touch_are_allowed(self):
		self._grant("2026-01-01", "2026-01-31")
		self._grant("2026-02-01", "2026-02-28")

	def test_an_open_ended_period_does_not_block_a_later_window(self):
		"""It would have, under the first design. That was the bug."""
		self._grant("2026-03-01", None, "None")
		self._grant("2027-01-01", "2027-01-31", "Both")

	def test_a_period_cannot_end_before_it_starts(self):
		with self.assertRaises(frappe.ValidationError):
			self._grant("2026-06-30", "2026-06-01")

	def test_a_bulk_grant_skips_rather_than_rewrites(self):
		"""Changing somebody's existing grant is a decision, not a side effect
		of a bulk action."""
		from alvoraa_portal.alvoraa_portal.doctype.alvoraa_green_eligibility \
			.alvoraa_green_eligibility import grant_window
		emp = self._employee()
		self._grant("2026-08-01", "2026-08-31")
		out = grant_window([emp], "2026-08-15", "2026-09-15", "Both", "Diwali")
		self.assertEqual(out["created"], 0)
		self.assertEqual(len(out["skipped"]), 1)
		self.assertEqual(out["skipped"][0]["employee"], emp)


if __name__ == "__main__":
	unittest.main(verbosity=2)
