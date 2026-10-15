"""Green eligibility is dated, because DTC change it with the seasons.

The resolution itself - given an employee and a day, which grant applies - is
pure, so it is tested here without a site. The database side - which grant wins
on a shared day, the one-grant-per-start-date rule, and the bulk grant - needs a
bench and lives in the integration class below.

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


class TestGreenEligibilityRecords(FrappeTestCase):
	"""Needs a site: the overlap refusal and the bulk grant."""

	def setUp(self):
		self.emp = None

	def _employee(self):
		"""One fresh employee per test, deliberately not shared.

		A grant is named after the employee and its start date, so two tests
		that use the same person and the same date collide on the record name
		- and the failure then looks like the rule under test rather than the
		fixture. It cost an hour to see that once; a new person each time
		costs one insert.
		"""
		if self.emp:
			return self.emp
		company = frappe.db.get_value("Company", {}, "name")
		doc = frappe.get_doc({
			"doctype": "Employee", "first_name": "Green", "last_name": "Test",
			"company": company, "date_of_joining": "2026-01-01",
			"date_of_birth": "1990-01-01", "gender": _gender(), "status": "Active",
		})
		doc.flags.ignore_permissions = True
		doc.insert()
		self.emp = doc.name
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

	def test_two_periods_that_overlap_are_allowed_and_the_later_start_wins(self):
		"""The first design refused an overlap. That was wrong for the way DTC
		actually work: they keep one standing grant per person and widen it for
		a festive season, so refusing would make Diwali three edits each for
		two hundred and fifty people.

		A day covered twice is still unambiguous, because two grants cannot
		share a start date - the record is named after the employee and that
		day - so "the later start applies" always picks exactly one."""
		from alvoraa_portal.alvoraa_portal.doctype \
			.alvoraa_green_eligibility.alvoraa_green_eligibility \
			import eligibility_on
		emp = self._employee()
		self._grant("2026-10-01", "2026-10-31", "None")
		self._grant("2026-10-15", "2026-11-15", "Both")

		# inside the season, the season applies
		self.assertEqual(eligibility_on(emp, "2026-10-20"), "Both")
		# before it, the standing grant still does
		self.assertEqual(eligibility_on(emp, "2026-10-05"), "None")
		# after both, nothing is granted and the caller's fallback is used
		self.assertEqual(eligibility_on(emp, "2026-12-01", "fell back"),
		                 "fell back")

	def test_two_grants_cannot_share_a_start_date(self):
		"""What makes the rule above unambiguous. It is enforced by the record
		name, so it holds for Data Import and the API as well as the form."""
		self._grant("2026-10-01", "2026-10-31", "None")
		with self.assertRaises(frappe.DuplicateEntryError):
			self._grant("2026-10-01", "2026-11-15", "Both")

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

	def test_a_bulk_grant_skips_a_same_day_rewrite_and_names_who(self):
		"""Overwriting a decision somebody already made is not a side effect a
		bulk action gets to have. The same start date means a straight rewrite,
		so it is skipped and reported rather than applied quietly.

		This used to fail open. The collision raises DuplicateEntryError, which
		is not a ValidationError, so the catch missed it: the whole run died on
		the first such employee, with nobody listed as skipped."""
		from alvoraa_portal.alvoraa_portal.doctype \
			.alvoraa_green_eligibility.alvoraa_green_eligibility \
			import grant_window
		emp = self._employee()
		self._grant("2026-08-01", "2026-08-31", "None")
		out = grant_window([emp], "2026-08-01", "2026-09-15", "Both", "Diwali")
		self.assertEqual(out["created"], 0)
		self.assertEqual(len(out["skipped"]), 1)
		self.assertEqual(out["skipped"][0]["employee"], emp)

	def test_a_bulk_grant_adds_a_season_over_a_standing_grant(self):
		"""The case it exists for. A later start is not a rewrite, so it is
		created and simply wins on the days the two share."""
		from alvoraa_portal.alvoraa_portal.doctype \
			.alvoraa_green_eligibility.alvoraa_green_eligibility \
			import eligibility_on, grant_window
		emp = self._employee()
		self._grant("2026-08-01", None, "None")
		out = grant_window([emp], "2026-08-15", "2026-09-15", "Both", "Diwali")
		self.assertEqual(out["created"], 1)
		self.assertEqual(out["skipped"], [])
		self.assertEqual(eligibility_on(emp, "2026-08-20"), "Both")
		self.assertEqual(eligibility_on(emp, "2026-08-10"), "None")
		self.assertEqual(eligibility_on(emp, "2026-10-01"), "None")


if __name__ == "__main__":
	unittest.main(verbosity=2)
