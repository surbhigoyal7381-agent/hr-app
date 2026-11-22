"""A punch just after midnight belongs to the shift it ends (ALV-402).

DTC, 6-7 Nov 2026: Samiron Mondol (shift 11:00-20:30) punched 10:55, 15:04 and
15:22 on the 6th, left at 00:00:42 on the 7th, and on the 7th punched 16:42 and
21:42. Read by calendar date, both days had three punches and both were held,
with no green on either. Frappe had matched the 00:00 punch to the 6th's shift
(`shift_start` on the 6th) wherever its window reached; the engine ignored it.

The rule now: a punch counts on the date of its `shift_start`; a punch with no
shift keeps its calendar date, exactly as before.
"""

from datetime import datetime

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from alvoraa_portal.payroll_rules import evaluate_day, punch_minutes
from alvoraa_portal.payroll_rules_apply import _punches
from alvoraa_portal.tests.test_payroll_flags import _employee, setUpModule  # noqa: F401


class PunchMinutesRunPastMidnight(FrappeTestCase):
	def test_a_punch_on_the_next_date_runs_past_1440(self):
		day = getdate("2026-11-06")
		times = [datetime(2026, 11, 6, 10, 55), datetime(2026, 11, 7, 0, 0, 42)]
		self.assertEqual(punch_minutes(times, day=day), [655, 1440])

	def test_without_a_day_it_reads_the_clock_as_before(self):
		self.assertEqual(punch_minutes([datetime(2026, 11, 7, 0, 0, 42)]), [0])


class PunchesFollowTheShiftDay(FrappeTestCase):
	def _punch(self, emp, when, shift_start=None):
		doc = frappe.get_doc({"doctype": "Employee Checkin", "employee": emp,
		                      "time": when, "log_type": ""})
		doc.insert(ignore_permissions=True)
		# Set after insert: Frappe's own shift match depends on the site's shifts.
		frappe.db.set_value("Employee Checkin", doc.name, "shift_start", shift_start,
		                    update_modified=False)

	def setUp(self):
		self.emp = _employee("Permanent")
		self.d1 = getdate(add_days(nowdate(), -12))
		self.d2 = add_days(self.d1, 1)

	def test_samiron_s_two_days(self):
		s1, s2 = "{0} 11:00:00".format(self.d1), "{0} 11:00:00".format(self.d2)
		for t in ("10:55:59", "15:04:19", "15:22:52"):
			self._punch(self.emp, "{0} {1}".format(self.d1, t), s1)
		self._punch(self.emp, "{0} 00:00:42".format(self.d2), s1)
		for t in ("16:42:18", "21:42:38"):
			self._punch(self.emp, "{0} {1}".format(self.d2, t), s2)

		self.assertEqual(_punches(self.emp, self.d1), (655, 1440, 4, [(904, 922)]))
		self.assertEqual(_punches(self.emp, self.d2), (1002, 1302, 2, []))

	def test_a_punch_with_no_shift_keeps_its_calendar_date(self):
		self._punch(self.emp, "{0} 10:55:00".format(self.d1), None)
		self._punch(self.emp, "{0} 00:00:42".format(self.d2), None)
		self.assertEqual(_punches(self.emp, self.d1)[2], 1)
		self.assertEqual(_punches(self.emp, self.d2)[:3], (0, 0, 1))


class TheNightIsJudgedWhole(FrappeTestCase):
	def test_leaving_after_midnight_earns_the_night_green(self):
		v = evaluate_day(shift_start=660, shift_end=1230, first_in=655, last_out=1440,
		                 punch_count=4, slabs=[_Slab()], night_green_eligible=True,
		                 shift_hours_only=True, break_allowance_minutes=40,
		                 break_gaps=[(904, 922)])
		self.assertFalse(v.held)
		self.assertEqual(v.greens, 1)


class _Slab:
	percent_from, percent_to = 0, 100

	def __getattr__(self, name):
		return 0


class ScreensPutThePunchOnTheSameDay(FrappeTestCase):
	"""The home screen and the attendance pages group a punch by `shift_day`,
	the same rule the engine uses, so a screen never shows the 00:00 departure
	as the first punch of the next morning."""

	def test_shift_day_follows_the_shift_and_falls_back_to_the_calendar(self):
		from alvoraa_portal.payroll_rules_apply import shift_day
		self.assertEqual(shift_day(frappe._dict(time="2026-11-07 00:00:42",
		                                        shift_start="2026-11-06 11:00:00")), "2026-11-06")
		self.assertEqual(shift_day(frappe._dict(time="2026-11-07 00:00:42", shift_start=None)),
		                 "2026-11-07")

	def test_the_home_screen_leaves_last_night_s_departure_out_of_today(self):
		from alvoraa_portal.home_api import _punches_today
		emp = _employee("Permanent")
		d1 = getdate(add_days(nowdate(), -12))
		d2 = add_days(d1, 1)
		PunchesFollowTheShiftDay._punch(self, emp, "{0} 00:00:42".format(d2), "{0} 11:00:00".format(d1))
		PunchesFollowTheShiftDay._punch(self, emp, "{0} 10:58:00".format(d2), "{0} 11:00:00".format(d2))
		self.assertEqual([r["time"][11:16] for r in _punches_today(emp, d2)], ["10:58"])
