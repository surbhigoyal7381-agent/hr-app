"""ALV-351 (Surbhi, 17 Nov 2026): a day with an odd number of punches is held.

The engine cases sit in test_payroll_rules.py. These are the ones the review
found missing: punches that fold to three, a marked-Absent day, contract staff,
a special day, and the month summary actually handing HR's confirmation to the
engine (without it a confirmed day stayed held on the report and the slip).
No site is needed: the month summary's one database read is replaced.
"""

import unittest
from unittest.mock import patch

from alvoraa_portal.payroll_rules import break_gaps, collapse_duplicate_punches, evaluate_day
from alvoraa_portal.tests.test_payroll_rules import DTC_SLABS, hm


def day(punches, **extra):
	p = collapse_duplicate_punches(punches)
	args = dict(shift_start=hm(10, 30), shift_end=hm(20, 30),
	            first_in=p[0] if p else None, last_out=p[-1] if p else None,
	            punch_count=len(p), grace_minutes=6, slabs=DTC_SLABS,
	            special_day_multiplier=2, night_green_eligible=True,
	            break_gaps=break_gaps(p))
	args.update(extra)
	return evaluate_day(**args)


class OddCountIsHeld(unittest.TestCase):
	def test_alv351_a_repeat_scan_is_merged_before_counting(self):
		"""10:30 and 10:31 are one arrival, so 10:30 10:31 20:30 is a finished
		two-punch day - not held."""
		v = day([hm(10, 30), hm(10, 31), hm(20, 30)])
		self.assertFalse(v.held)
		self.assertEqual(v.attendance_percent, 100.0)

	def test_alv351_punches_that_fold_to_three_are_held(self):
		v = day([hm(10, 30), hm(10, 31), hm(14, 0), hm(20, 30)])
		self.assertTrue(v.held)

	def test_alv351_the_invented_odd_day_is_held_not_just_uncharged(self):
		"""The shift-hours table expects (0, 0, 0) for this day. The old code
		gave that too, so here it is pinned as HELD."""
		v = day([hm(8, 30), hm(12, 30), hm(18, 30)], shift_start=hm(8, 30),
		        shift_end=hm(18, 30))
		self.assertTrue(v.held)

	def test_alv351_marked_absent_with_three_punches_is_held(self):
		v = day([hm(10, 30), hm(14, 0), hm(20, 30)], marked_absent=True)
		self.assertTrue(v.held)
		self.assertFalse(v.absent)

	def test_alv351_contract_staff_are_held_and_released_without_marks(self):
		held = day([hm(10, 30), hm(14, 0), hm(20, 30)], earns_marks=False)
		self.assertTrue(held.held)
		done = day([hm(10, 50), hm(14, 0), hm(22, 0)], earns_marks=False,
		           confirmed_out=hm(17, 0))
		self.assertFalse(done.held)
		self.assertEqual((done.reds, done.greens), (0, 0))
		self.assertGreater(done.total_quarters, 0)

	def test_alv351_a_held_special_day_doubles_nothing(self):
		v = day([hm(10, 30), hm(14, 0), hm(20, 30)], is_special_day=True,
		        double_deduction_applies=True)
		self.assertTrue(v.held)
		self.assertEqual(v.total_quarters, 0)

	def test_alv351_a_confirmed_special_day_doubles_as_usual(self):
		odd = day([hm(10, 30), hm(14, 0), hm(21, 0)], is_special_day=True,
		          double_deduction_applies=True, confirmed_out=hm(17, 0))
		two = day([hm(10, 30), hm(17, 0)], is_special_day=True,
		          double_deduction_applies=True)
		self.assertEqual(odd.total_quarters, two.total_quarters)
		self.assertGreater(odd.total_quarters, 0)


class HalfDays(unittest.TestCase):
	"""Surbhi, 17 Nov 2026: hold a half day only when no half-day leave is
	behind it. Frappe HR marks an approved half-day leave as status "Half Day"
	with the leave linked; a "Half Day" with no leave is a short day."""

	def test_alv351_a_half_day_leave_with_three_punches_is_measured_not_held(self):
		v = day([hm(10, 30), hm(13, 0), hm(15, 30)], half_day_leave=True)
		self.assertFalse(v.held)
		self.assertTrue(v.half_leave)

	def test_alv351_a_half_day_with_no_leave_and_three_punches_is_held(self):
		v = day([hm(10, 30), hm(13, 0), hm(15, 30)], half_day_leave=False)
		self.assertTrue(v.held)


class Doc(dict):
	"""Just enough of an Attendance document for the onload hook."""
	__getattr__ = dict.get

	def set_onload(self, key, value):
		self.setdefault("__onload", {})[key] = value


class FormShowsTheConfirmFields(unittest.TestCase):
	"""Choice A: HR sees the confirm fields on a missing-punch day even while
	the rule set is switched off."""

	def run_onload(self, doc, has_rule_set=True, count=3):
		import alvoraa_portal.payroll_rules_apply as apply
		with patch.object(apply.frappe.db, "exists", return_value=has_rule_set), \
				patch.object(apply, "_punches", return_value=(None, None, count, [])):
			apply.attendance_onload(doc)
		return (doc.get("__onload") or {}).get("alvoraa_missing_punch")

	def present(self, **kw):
		d = Doc(docstatus=1, status="Present", company="Co", employee="E",
		        attendance_date="2026-11-01")
		d.update(kw)
		return d

	def test_alv351_an_odd_day_with_a_rule_set_shows_them(self):
		self.assertEqual(self.run_onload(self.present()), 1)
		self.assertEqual(self.run_onload(self.present(), count=1), 1)

	def test_alv351_an_even_day_does_not(self):
		self.assertIsNone(self.run_onload(self.present(), count=2))

	def test_alv351_a_company_with_no_rule_set_does_not(self):
		self.assertIsNone(self.run_onload(self.present(), has_rule_set=False))

	def test_alv351_leave_and_half_day_leave_do_not(self):
		self.assertIsNone(self.run_onload(self.present(status="On Leave")))
		self.assertIsNone(self.run_onload(
			self.present(status="Half Day", leave_application="HR-LAP-1")))
		self.assertEqual(self.run_onload(self.present(status="Half Day")), 1)

	def test_alv351_a_draft_does_not(self):
		self.assertIsNone(self.run_onload(self.present(docstatus=0)))


class MonthSummaryReadsTheConfirmation(unittest.TestCase):
	def test_alv351_the_month_summary_asks_for_both_confirm_fields(self):
		"""The report, the slip and the leave card all go through month_summary.
		If it does not read these two fields, judge() never sees HR's time."""
		import alvoraa_portal.payroll_slip as slip

		asked = {}

		def fake_get_all(doctype, **kw):
			if doctype == "Attendance":
				asked["fields"] = kw.get("fields") or []
			return []

		with patch.object(slip, "rule_set_for", return_value=object()), \
				patch.object(slip, "prepare", return_value={}), \
				patch.object(slip.frappe, "get_all", side_effect=fake_get_all):
			try:
				slip.month_summary("EMP-X", "Co", "2026-11-01", "2026-11-30")
			except Exception:
				pass  # only the Attendance read is under test here
		self.assertIn("alvoraa_held_confirmed", asked.get("fields", []))
		self.assertIn("alvoraa_confirmed_out_time", asked.get("fields", []))
