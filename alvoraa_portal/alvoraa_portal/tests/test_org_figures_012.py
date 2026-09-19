"""Slice 012 push 1 · one calculation for attendance, leave and people (US-2, US-3).

AC-6 to AC-10, AC-16, AC-30, OPS-6, OPS-63. The numbers in the spec are scaled
down by ten where a test needs hundreds of rows; the percentages are the spec's.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from alvoraa_portal import org_figures as of
from alvoraa_portal.tests import leader_fixtures_012 as fx

SEP = "2026-09-"


def setUpModule():
	fx.setup_module_fixtures()


def day(n):
	return getdate(f"{SEP}{n:02d}")


class FiguresCase(FrappeTestCase):
	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user(self.caller)

	def staff(self, n, company, branch, prefix="Staff"):
		return [fx.employee(f"{prefix}{i}", company, branch) for i in range(n)]


class TestTheAttendanceFormula(FiguresCase):
	def test_present_wfh_and_half_days_over_everyone_expected(self):
		"""AC-6 scaled: Present 70, WFH 2, Half Day 1, Absent 3, On Leave 4 -> 95.4%."""
		lakeside = fx.branch("Lakeside")
		people = self.staff(8, fx.KAVYA, lakeside)
		statuses = ["Present"] * 70 + ["Work From Home"] * 2 + ["Half Day"] + ["Absent"] * 3 + ["On Leave"] * 4
		for i, status in enumerate(statuses):
			fx.attendance(people[i % 8], fx.KAVYA, lakeside, day(1 + i // 8), status)
		scope = of.Scope((fx.KAVYA,), (lakeside,))
		f = of.attendance_figures(scope, day(1), day(13))
		self.assertEqual((f["present"], f["wfh"], f["half"], f["absent"], f["on_leave"]), (70, 2, 1, 3, 4))
		self.assertEqual(f["rate"], 95.4)
		self.assertEqual(f["people"], 8)

	def test_only_the_submitted_record_counts_once(self):
		"""AC-7: a draft, a cancelled record and its amended, resubmitted copy."""
		b = fx.branch("Amended")
		p = self.staff(1, fx.KAVYA, b)[0]
		fx.attendance(p, fx.KAVYA, b, day(2), "Absent", docstatus=0)
		fx.attendance(p, fx.KAVYA, b, day(2), "Absent", docstatus=2)
		fx.attendance(p, fx.KAVYA, b, day(2), "Present", docstatus=1)
		f = of.attendance_figures(of.Scope((fx.KAVYA,), (b,)), day(1), day(13))
		self.assertEqual((f["present"], f["absent"], f["rate"]), (1, 0, 100.0))

	def test_late_arrivals_and_short_days(self):
		"""AC-8: 9-hour shift, 30 minutes tolerance."""
		b = fx.branch("Short")
		a, b2, c = self.staff(3, fx.KAVYA, b)
		fx.attendance(a, fx.KAVYA, b, day(3), "Present", hours=8.0, late=1)
		fx.attendance(b2, fx.KAVYA, b, day(3), "Present", hours=8.6)
		frappe.db.set_value("Employee", c, "default_shift", None)
		fx.attendance(c, fx.KAVYA, b, day(3), "Present", hours=2.0, shift=None)
		with patch.object(of, "_tolerance", return_value=30):
			f = of.attendance_figures(of.Scope((fx.KAVYA,), (b,)), day(1), day(13))
		self.assertEqual((f["late"], f["short"]), (1, 1))

	def test_no_attendance_means_no_figure(self):
		"""AC-30: "No figures yet", never 0%."""
		b = fx.branch("Empty")
		scope = of.Scope((fx.KAVYA,), (b,))
		self.assertIsNone(of.attendance_figures(scope, day(1), day(13))["rate"])
		self.assertIsNone(of.period(scope))

	def test_the_period_is_the_month_of_the_last_day_with_data(self):
		"""D-13 / AC-10."""
		b = fx.branch("Period")
		p = self.staff(1, fx.KAVYA, b)[0]
		fx.attendance(p, fx.KAVYA, b, day(9))
		fx.attendance(p, fx.KAVYA, b, "2026-08-31")
		self.assertEqual(of.period(of.Scope((fx.KAVYA,), (b,))), (day(1), day(9)))

	def test_a_branch_is_always_matched_with_its_company(self):
		"""V6 / AC-42: another company's rows under the same branch name never count."""
		shared = fx.branch("SharedName")
		mine = self.staff(1, fx.KAVYA, shared, "Mine")[0]
		theirs = self.staff(1, fx.OTHER, shared, "Theirs")[0]
		fx.attendance(mine, fx.KAVYA, shared, day(4), "Present")
		fx.attendance(theirs, fx.OTHER, shared, day(4), "Absent")
		f = of.attendance_figures(of.Scope((fx.KAVYA,), (shared,)), day(1), day(13))
		self.assertEqual((f["present"], f["absent"]), (1, 0))


class TestDoubtfulDaysAreLeftOut(FiguresCase):
	"""Alone in its class: it reads the whole company, and a class shares one transaction."""

	def test_open_doubtful_days_leave_out_that_branch_only(self):
		"""AC-16: Lakeside's rows on 8-10 Sep out; Station Road's rows on those dates still count."""
		lakeside, station = fx.branch("Lakeside"), fx.branch("Station")
		lake = self.staff(2, fx.KAVYA, lakeside, "Lake")
		stat = self.staff(2, fx.KAVYA, station, "Stat")
		for d in (7, 8, 9, 10):
			for p in lake:
				fx.attendance(p, fx.KAVYA, lakeside, day(d), "Present" if d == 7 else "Absent")
			for p in stat:
				fx.attendance(p, fx.KAVYA, station, day(d), "Present")
		for d in (8, 9, 10):
			fx.review_item(fx.KAVYA, lakeside, check_date=day(d), expected_count=2, absent_count=2)
		# A cleared day and a confirmed day count again.
		fx.review_item(fx.KAVYA, station, check_date=day(8), status="Cleared")

		company = of.attendance_figures(of.Scope((fx.KAVYA,), None), day(1), day(13))
		self.assertEqual((company["present"], company["absent"]), (2 + 8, 0))
		lake_only = of.attendance_figures(of.Scope((fx.KAVYA,), (lakeside,)), day(1), day(13))
		self.assertEqual((lake_only["present"], lake_only["absent"], lake_only["rate"]), (2, 0, 100.0))
		both = of.attendance_figures(of.Scope((fx.KAVYA,), (lakeside, station)), day(1), day(13))
		self.assertEqual((both["present"], both["absent"]), (10, 0))

		# The figure "with those days" adds them back, from one grouped query.
		left_out = of.open_doubtful_counts(of.Scope((fx.KAVYA,), (lakeside,)), day(1), day(13))
		self.assertEqual(len(left_out), 3)
		self.assertEqual(of.rate_with(lake_only, left_out.values()), 25.0)


class TestConfirmedDoubtfulDays(FiguresCase):
	def test_a_confirmed_absence_counts_again(self):
		b = fx.branch("Confirmed")
		p = self.staff(1, fx.KAVYA, b)[0]
		fx.attendance(p, fx.KAVYA, b, day(8), "Absent")
		fx.attendance(p, fx.KAVYA, b, day(7), "Present")
		fx.review_item(fx.KAVYA, b, check_date=day(8), status="Confirmed")
		f = of.attendance_figures(of.Scope((fx.KAVYA,), (b,)), day(1), day(13))
		self.assertEqual((f["present"], f["absent"], f["rate"]), (1, 1, 50.0))


class TestLeaveUsedThisLeaveYear(FiguresCase):
	def test_this_leave_years_leave_over_allocations_overlapping_it(self):
		"""AC-9: 281 / 1,536 = 18.3%; last year's 1,400 days are not counted."""
		b = fx.branch("Leave")
		a, c = self.staff(2, fx.KAVYA, b, "Leave")
		fx.allocation(a, fx.KAVYA, b, "2026-04-01", "2027-03-31", 1000)
		fx.allocation(c, fx.KAVYA, b, "2026-04-01", "2027-03-31", 536)
		fx.allocation(a, fx.KAVYA, b, "2025-04-01", "2026-03-31", 1400)
		fx.application(a, fx.KAVYA, b, "2026-05-04", 200)
		fx.application(c, fx.KAVYA, b, "2026-08-10", 81)
		fx.application(c, fx.KAVYA, b, "2026-03-10", 40)                      # last leave year
		fx.application(c, fx.KAVYA, b, "2026-08-11", 50, status="Open", docstatus=0)
		fx.application(c, fx.KAVYA, b, "2026-08-12", 30, docstatus=2)          # cancelled

		with patch("alvoraa_portal.hr_api._leave_year_start", return_value=getdate("2026-04-01")):
			f = of.leave_figures(of.Scope((fx.KAVYA,), (b,)), day(13))
		self.assertEqual((f["allocated"], f["taken"]), (1536.0, 281.0))
		self.assertEqual(f["used_pct"], 18.3)
		self.assertEqual(f["requests"], 3)          # two approved and one open; not the cancelled one
		self.assertEqual(f["people"], 2)

	def test_each_company_uses_its_own_leave_year(self):
		b = fx.branch("TwoYears")
		k = self.staff(1, fx.KAVYA, b, "K")[0]
		o = self.staff(1, fx.OTHER, b, "O")[0]
		fx.allocation(k, fx.KAVYA, b, "2026-04-01", "2027-03-31", 100)
		fx.application(k, fx.KAVYA, b, "2026-05-01", 10)
		fx.allocation(o, fx.OTHER, b, "2026-01-01", "2026-12-31", 100)
		fx.application(o, fx.OTHER, b, "2026-02-01", 20)

		starts = {fx.KAVYA: getdate("2026-04-01"), fx.OTHER: getdate("2026-01-01")}
		with patch("alvoraa_portal.hr_api._leave_year_start", side_effect=lambda d, c: starts[c]):
			f = of.leave_figures(of.Scope((fx.KAVYA, fx.OTHER), (b,)), day(13))
		self.assertEqual(f["by_company"][fx.KAVYA]["taken"], 10.0)
		self.assertEqual(f["by_company"][fx.OTHER]["taken"], 20.0)
		self.assertEqual(f["used_pct"], 15.0)


class TestPeople(FiguresCase):
	def test_headcount_is_active_and_joined(self):
		b = fx.branch("People")
		fx.employee("Here", fx.KAVYA, b, joined="2020-01-01")
		fx.employee("Future", fx.KAVYA, b, joined="2026-09-30")
		fx.employee("Gone", fx.KAVYA, b, status="Left", relieving="2026-06-30")
		fx.employee("New", fx.KAVYA, b, joined="2026-09-02")
		f = of.people_figures(of.Scope((fx.KAVYA,), (b,)), day(13), day(1), getdate("2026-09-30"))
		self.assertEqual(f, {"active": 2, "total": 4, "joiners": 2})


class TestHrScope(FiguresCase):
	def test_store_hr_gets_their_company_and_branch(self):
		b = fx.branch("ScopeStore")
		u = fx.user("scopestore", ["HR User"])
		fx.employee("ScopeStore", fx.KAVYA, b, user_id=u)
		fx.permission(u, "Branch", b)
		self.assertEqual(of.hr_scope(u), of.Scope((fx.KAVYA,), (b,)))

	def test_a_branch_permission_for_another_doctype_does_not_narrow(self):
		b = fx.branch("ScopeOther")
		u = fx.user("scopeother", ["HR User"])
		fx.employee("ScopeOther", fx.KAVYA, b, user_id=u)
		fx.permission(u, "Branch", b, applicable_for="Expense Claim")
		self.assertEqual(of.hr_scope(u), of.Scope((fx.KAVYA,), None))

	def test_hr_with_no_company_and_no_employee_is_not_linked(self):
		"""BA-Q5: fail closed."""
		u = fx.user("scopenobody", ["HR Manager"])
		self.assertTrue(of.hr_scope(u).not_linked)

	def test_company_permissions_decide_the_companies(self):
		u = fx.user("scopecentral", ["HR Manager"])
		fx.permission(u, "Company", fx.KAVYA)
		self.assertEqual(of.hr_scope(u), of.Scope((fx.KAVYA,), None))


class TestQueryCountsDoNotGrow(FiguresCase):
	"""OPS-63 / AC-4: the same number of queries at 10 and 100 people, 2 and 8 branches."""

	def build(self, people, branches):
		names = [fx.branch("QC") for _ in range(branches)]
		for i in range(people):
			b = names[i % branches]
			p = fx.employee(f"QC{i}", fx.KAVYA, b, fast=True)
			fx.attendance(p, fx.KAVYA, b, day(5), "Present" if i % 3 else "Absent")
			fx.allocation(p, fx.KAVYA, b, "2026-04-01", "2027-03-31", 12)
		return of.Scope((fx.KAVYA,), tuple(names))

	def count(self, scope):
		with patch("alvoraa_portal.hr_api._leave_year_start", return_value=getdate("2026-04-01")):
			with fx.QueryCounter() as q:
				of.attendance_figures(scope, day(1), day(13))
				of.open_doubtful_counts(scope, day(1), day(13))
				of.data_up_to(scope)
				of.leave_figures(scope, day(13))
				of.people_figures(scope, day(13))
		return q.count

	def test_counts_are_fixed(self):
		self.count(self.build(1, 1))   # warm Frappe's own caches first
		counts = {(p, b): self.count(self.build(p, b)) for p, b in ((10, 2), (100, 2), (10, 8), (100, 8))}
		self.assertEqual(len(set(counts.values())), 1, counts)
		self.assertLessEqual(next(iter(counts.values())), 8, counts)


class TestAppraisalScoresDoNotMove(FiguresCase):
	"""AC-11, PRIV-13: appraisal attendance keeps its own formula; doubtful days do not touch it.

	In alvoraa_portal/tests on purpose: CI does not run the hrms fork's tests (OPS-74).
	"""

	def test_an_open_doubtful_day_still_counts_in_the_appraisal_numbers(self):
		from hrms.alvoraa_hr_core.attendance_score import numbers_for_many

		b = fx.branch("Appraisal")
		p = fx.employee("Appraised", fx.KAVYA, b, joined="2020-01-01")
		fx.attendance(p, fx.KAVYA, b, day(7), "Present", late=1)
		fx.attendance(p, fx.KAVYA, b, day(8), "Absent")
		fx.attendance(p, fx.KAVYA, b, day(9), "Half Day")
		fx.review_item(fx.KAVYA, b, check_date=day(8))
		n = numbers_for_many([p], day(1), day(13))[p]
		self.assertEqual((n.present_days, n.absent_days, n.late_days), (1.5, 1.5, 1))

	def test_nothing_that_rates_people_imports_the_leader_figures(self):
		import os

		import alvoraa_goals
		import hrms.alvoraa_hr_core.attendance_score as score

		paths = [score.__file__]
		root = os.path.dirname(alvoraa_goals.__file__)
		for folder, _dirs, files in os.walk(root):
			paths += [os.path.join(folder, f) for f in files if f.endswith(".py") and "tests" not in folder]
		for path in paths:
			with open(path, encoding="utf-8-sig") as f:
				text = f.read()
			self.assertNotIn("org_figures", text, path)
			self.assertNotIn("data_review", text, path)
