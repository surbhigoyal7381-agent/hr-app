"""Slice 090 · three acceptance criteria no earlier test named (found at the final run).

AC-123 half-day rows add nothing to Leave days. AC-84 leave days carry a comparison with
the window before. AC-60 the same request gives the same answer, whatever came before.
"""

from alvoraa_portal.tests import leader_fixtures_012 as fx
from alvoraa_portal.tests.test_people_trends_090 import TrendsBase, ago, call, person, setUpModule, tearDownModule  # noqa: F401  (the module builds the tenant)


class TestFinalRunGaps(TrendsBase):
	def _six(self, name):
		b = fx.branch(name)
		return b, person(fx.KAVYA, b, "S090 " + name, None, n=6)

	def test_a_half_day_row_adds_nothing_to_leave_days(self):  # AC-123
		b, emps = self._six("Half")
		for e in emps:
			for d in range(1, 5):
				fx.attendance(e, fx.KAVYA, b, ago(d), "Present")
		before = call(self.lead_retail, period=30, branch=b)
		self.assertEqual(before["leave"]["days"], 0)
		for e in emps:
			fx.attendance(e, fx.KAVYA, b, ago(6), "Half Day")
		after = call(self.lead_retail, period=30, branch=b)
		self.assertEqual(after["leave"]["days"], 0, "half days are not leave days")
		self.assertGreater(after["attendance"]["absent_pct"], before["attendance"]["absent_pct"],
			"but they still count in the absence rate")

	def test_leave_days_carry_a_comparison_with_the_window_before(self):  # AC-84
		b, emps = self._six("Prev")
		fx.attendance(emps[0], fx.KAVYA, b, ago(2), "On Leave")
		for d in (31, 32, 33):  # inside the 30-day window before a 30-day window
			fx.attendance(emps[1], fx.KAVYA, b, ago(d), "On Leave")
		out = call(self.lead_retail, period=30, branch=b)
		self.assertEqual(out["leave"]["days"], 1)
		self.assertEqual(out["leave"]["before"]["days"], 3)

	def test_the_same_request_gives_the_same_answer(self):  # AC-60
		first = call(self.lead_retail, period=90)
		call(self.lead_other, period=30)
		call(self.lead_retail, period=365, branch=self.my)
		self.assertEqual(call(self.lead_retail, period=90), first)
