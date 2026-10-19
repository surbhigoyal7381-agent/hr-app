"""What the home banner tells somebody about the day they are standing in.

Surbhi, 17 Oct 2026: "show, according to their alloted shift whether the
employee is eligible for green pay / red pay for that day, what is their half
day according to their shift timing".

Every figure is a clock time against THEIR shift. The tests are mostly about
the cases where a wrong answer would cost somebody money or mislead them into
staying late for nothing.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from alvoraa_portal.day_marks import marks_today

COMPANY = "Day Marks Test Co"
SHIFT = "DM 10:30-8:30"
DAY = "2026-10-20"


def setUpModule():
	if not frappe.db.exists("Company", COMPANY):
		frappe.get_doc({"doctype": "Company", "company_name": COMPANY,
		                "abbr": "DMTC", "default_currency": "INR",
		                "country": "India"}).insert(ignore_permissions=True)
	# DTC-shaped: a ten-hour shift, half day at 4.5 hours worked, absent below
	# 2 - so the times these tests assert are the ones a DTC employee sees.
	if not frappe.db.exists("Shift Type", SHIFT):
		frappe.get_doc({"doctype": "Shift Type", "name": SHIFT,
		                "start_time": "10:30:00", "end_time": "20:30:00",
		                "working_hours_threshold_for_half_day": 4.5,
		                "working_hours_threshold_for_absent": 2.0}
		               ).insert(ignore_permissions=True)
	# The rule set is REPLACED, not merely created when absent. A test site
	# outlives a run, so an "only if missing" fixture quietly keeps the
	# figures from whenever it was first written - which is how the slab
	# table below went in and never took effect.
	existing = frappe.db.get_value("Alvoraa Payroll Rule Set",
	                               {"company": COMPANY}, "name")
	if existing:
		frappe.delete_doc("Alvoraa Payroll Rule Set", existing, force=True,
		                  ignore_permissions=True)
	doc = frappe.get_doc({
		"doctype": "Alvoraa Payroll Rule Set", "company": COMPANY,
		"enabled": 0, "grace_minutes": 6, "free_reds_per_month": 2,
		"special_day_multiplier": 2, "leave_threshold_days": 15,
		"accrual_month_days": 30,
		"late_window_from": "11:00:00", "late_window_to": "11:30:00",
		"late_window_extra_quarters": 1,
		"green_eligibility_field": "dtc_green_eligibility",
		# DTC's real table, all twelve bands. A placeholder single band would
		# let the ladder tests pass while proving nothing about the merge.
		"slabs": [
			{"percent_from": 0, "percent_to": 20, "quarters_off": 4, "raises_red": 0},
			{"percent_from": 20, "percent_to": 24, "quarters_off": 3, "raises_red": 1},
			{"percent_from": 24, "percent_to": 25, "quarters_off": 3, "raises_red": 0},
			{"percent_from": 25, "percent_to": 40, "quarters_off": 3, "raises_red": 0},
			{"percent_from": 40, "percent_to": 44, "quarters_off": 2, "raises_red": 1},
			{"percent_from": 44, "percent_to": 50, "quarters_off": 2, "raises_red": 0},
			{"percent_from": 50, "percent_to": 65, "quarters_off": 2, "raises_red": 0},
			{"percent_from": 65, "percent_to": 68, "quarters_off": 1, "raises_red": 1},
			{"percent_from": 68, "percent_to": 75, "quarters_off": 1, "raises_red": 0},
			{"percent_from": 75, "percent_to": 90, "quarters_off": 1, "raises_red": 0},
			{"percent_from": 90, "percent_to": 98.9, "quarters_off": 0, "raises_red": 1},
			{"percent_from": 98.9, "percent_to": 100, "quarters_off": 0, "raises_red": 0},
		],
		"mark_rates": [{"grade": "Junior", "amount_per_mark": 100}],
	})
	doc.flags.ignore_permissions = True
	doc.insert()
	frappe.db.commit()


class MarksCase(FrappeTestCase):
	_n = 0

	def setUp(self):
		MarksCase._n += 1
		self.emp = self._employee()
		self.row = {"company": COMPANY}

	def _employee(self, green=None, green_from="2026-01-01", green_to=None):
		doc = frappe.get_doc({
			"doctype": "Employee", "first_name": "DM%d" % MarksCase._n,
			"company": COMPANY, "date_of_birth": "1990-01-01",
			"date_of_joining": "2024-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "default_shift": SHIFT,
		})
		doc.flags.ignore_permissions = True
		doc.insert()
		if green:
			self._grant(doc.name, green, green_from, green_to)
		return doc.name

	def _grant(self, employee, eligibility, from_date, to_date=None):
		"""A dated green grant, which is where DTC actually hold this.

		Not an Employee field: eligibility is dated so that re-running October
		in December applies October's rules. See `test_green_eligibility`.
		"""
		g = frappe.get_doc({
			"doctype": "Alvoraa Green Eligibility", "employee": employee,
			"from_date": from_date, "to_date": to_date,
			"eligibility": eligibility, "reason": "day marks test"})
		g.flags.ignore_permissions = True
		g.insert()
		return g.name

	def shift(self, name=SHIFT, start="10:30:00", end="20:30:00"):
		return {"name": name, "start": start, "end": end}

	def at(self, *times):
		return [{"time": "%s %s" % (DAY, t), "log_type": ""} for t in times]

	def marks(self, punches=(), shift=None, employee=None):
		return marks_today(employee or self.emp, self.row,
		                   shift or self.shift(), list(punches), DAY)


class TheTimesEverybodyGets(MarksCase):
	"""Half day and the late cutoff are Shift Type settings, so they hold on a
	tenant with no payroll rules at all."""

	def test_on_time_is_the_shift_start_plus_its_grace(self):
		self.assertEqual(self.marks()["on_time_until"], "10:36")

	def test_half_day_is_measured_from_when_they_actually_arrived(self):
		"""Somebody who came in late reaches their half-day mark later. Fixing
		it to the shift start would tell a 10:28 arrival and an 11:40 arrival
		the same time, and one of them would be wrong by over an hour."""
		self.assertEqual(self.marks(self.at("10:28:00"))["half_day_before"], "14:58")
		self.assertEqual(self.marks(self.at("11:40:00"))["half_day_before"], "16:10")

	def test_with_no_punch_yet_it_measures_from_the_shift_start(self):
		"""Before anybody arrives there is no better anchor, and a blank is
		less use than the shift's own answer."""
		self.assertEqual(self.marks()["half_day_before"], "15:00")

	def test_the_absent_line_is_shown_too(self):
		self.assertEqual(self.marks(self.at("10:28:00"))["absent_before"], "12:28")

	def test_somebody_with_no_shift_is_told_nothing(self):
		"""No shift means no shift length to measure against, which is the same
		answer the engine gives."""
		self.assertIsNone(marks_today(self.emp, self.row, None, [], DAY))


class WhetherAGreenIsStillOnTheTable(MarksCase):
	"""Who may earn what is the ENGINE's answer, asked through
	`green_eligibility_on`. These tests exist because working it out a second
	time beside the banner got every one of the four rules wrong."""

	def test_nobody_set_up_either_way_can_still_earn_a_morning_green(self):
		"""THE BUG THIS CLASS WAS WRITTEN FOR. A blank eligibility earns a
		morning green and not a night one - that is what the engine pays. The
		first version of the banner told these people they could earn nothing,
		so anyone who read it would stop coming in early for a mark they were
		in fact being paid."""
		out = self.marks(self.at("08:15:00"))["green"]
		self.assertTrue(out["eligible"])
		self.assertTrue(out["morning"]["earned"])
		self.assertIsNone(out["night"], "a blank earns no night green")

	def test_somebody_barred_from_both_is_told_so_plainly(self):
		emp = self._employee(green="None")
		out = self.marks(employee=emp)["green"]
		self.assertFalse(out["eligible"])

	def test_a_festive_grant_beats_the_standing_one_for_today(self):
		"""DTC widen eligibility for a season on top of a standing grant, and
		the later start wins. A banner reading the standing row would tell
		somebody there is no night green to earn on a day there is."""
		emp = self._employee(green="None")
		self._grant(emp, "Both", "2026-10-15", "2026-11-15")
		out = self.marks(self.at("10:28:00"), employee=emp)["green"]
		self.assertTrue(out["eligible"])
		self.assertIsNotNone(out["night"])

	def test_a_grant_that_has_not_started_does_not_count_today(self):
		emp = self._employee(green="None")
		self._grant(emp, "Both", "2026-12-01")
		self.assertFalse(self.marks(employee=emp)["green"]["eligible"])

	def test_a_morning_green_needs_two_hours_early(self):
		emp = self._employee(green="Both")
		out = self.marks(self.at("08:15:00"), employee=emp)["green"]
		self.assertEqual(out["morning"]["by"], "08:30")
		self.assertTrue(out["morning"]["earned"])

	def test_arriving_after_the_morning_cutoff_does_not_earn_it(self):
		emp = self._employee(green="Both")
		out = self.marks(self.at("08:45:00"), employee=emp)["green"]
		self.assertFalse(out["morning"]["earned"])

	def test_once_they_are_in_the_morning_mark_is_settled(self):
		"""Telling somebody already at their desk that it is "still possible"
		is a lie they could act on."""
		emp = self._employee(green="Both")
		out = self.marks(self.at("08:45:00"), employee=emp)["green"]
		self.assertFalse(out["morning"]["still_possible"])

	def test_before_anybody_arrives_the_morning_mark_is_still_possible(self):
		emp = self._employee(green="Both")
		out = self.marks(employee=emp)["green"]
		self.assertTrue(out["morning"]["still_possible"])

	def test_a_night_green_needs_an_hour_past_the_end(self):
		emp = self._employee(green="Both")
		out = self.marks(self.at("10:28:00"), employee=emp)["green"]
		self.assertEqual(out["night"]["after"], "21:30")
		self.assertTrue(out["night"]["still_possible"])

	def test_a_night_green_is_settled_once_they_have_gone(self):
		emp = self._employee(green="Both")
		out = self.marks(self.at("10:28:00", "21:45:00"), employee=emp)["green"]
		self.assertTrue(out["night"]["earned"])
		self.assertFalse(out["night"]["still_possible"])

	def test_leaving_before_the_line_does_not_earn_the_night_mark(self):
		emp = self._employee(green="Both")
		out = self.marks(self.at("10:28:00", "20:40:00"), employee=emp)["green"]
		self.assertFalse(out["night"]["earned"])

	def test_morning_only_staff_are_not_told_about_a_night_mark(self):
		"""Night greens are for flagged staff. Offering one to somebody who
		cannot earn it would keep them at work for nothing."""
		emp = self._employee(green="Morning Green")
		out = self.marks(self.at("10:28:00"), employee=emp)["green"]
		self.assertIsNone(out["night"])
		self.assertIsNotNone(out["morning"])


class WhetherARedIsInPlay(MarksCase):
	def test_arriving_inside_the_grace_is_not_late(self):
		out = self.marks(self.at("10:34:00"))["red"]
		self.assertFalse(out["late"])

	def test_arriving_past_the_grace_is_late_and_says_by_how_much(self):
		out = self.marks(self.at("10:50:00"))["red"]
		self.assertTrue(out["late"])
		self.assertEqual(out["late_by_minutes"], 14)

	def test_the_late_window_is_shown_to_somebody_it_can_bite(self):
		out = self.marks(self.at("10:28:00"))["red"]
		self.assertEqual(out["late_window"], {"from": "11:00", "to": "11:30"})

	def test_arriving_inside_the_window_is_flagged(self):
		out = self.marks(self.at("11:12:00"))["red"]
		self.assertTrue(out["in_late_window"])

	def test_a_shift_starting_inside_the_window_is_never_charged_for_it(self):
		"""The window is a clock time, not an offset. Arriving at 11:00 on an
		11:00 shift is punctual, and the engine refuses to charge it - so this
		must not warn about it either."""
		late = {"name": "DM 11:00", "start": "11:00:00", "end": "20:30:00"}
		if not frappe.db.exists("Shift Type", "DM 11:00"):
			frappe.get_doc({"doctype": "Shift Type", "name": "DM 11:00",
			                "start_time": "11:00:00", "end_time": "20:30:00"}
			               ).insert(ignore_permissions=True)
		out = self.marks(self.at("11:10:00"), shift=late)["red"]
		self.assertIsNone(out["late_window"])
		self.assertFalse(out["in_late_window"])

	def test_it_says_how_many_reds_are_free(self):
		self.assertEqual(self.marks()["red"]["free_per_month"], 2)


class ATenantWithoutTheseRules(MarksCase):
	"""Green and red marks are a rule-set idea. A company without one gets the
	shift's own times and no pretending otherwise."""

	def setUp(self):
		super().setUp()
		self.row = {"company": self._bare_company()}

	def _bare_company(self):
		with_rules = set(frappe.get_all("Alvoraa Payroll Rule Set", pluck="company"))
		for c in frappe.get_all("Company", pluck="name"):
			if c not in with_rules:
				return c
		return None

	def test_no_rule_set_means_no_green_and_no_red(self):
		if not self.row["company"]:
			self.skipTest("every company on this site has a rule set")
		out = self.marks(self.at("10:28:00"))
		self.assertIsNone(out["green"])
		self.assertIsNone(out["red"])

	def test_but_the_half_day_time_is_still_there(self):
		if not self.row["company"]:
			self.skipTest("every company on this site has a rule set")
		self.assertEqual(self.marks(self.at("10:28:00"))["half_day_before"], "14:58")


class WhatTheBannerActuallyReceives(MarksCase):
	"""The calculator above is proven; this is the wire to the screen.

	`get_checkin_status` is what the live portal banner asks - NOT `get_home`,
	which feeds the redesign that was dropped. A perfect `marks_today` reaching
	no endpoint is the same bug as the salary report in the wrong folder: every
	test passed and nobody could open it.
	"""

	def setUp(self):
		super().setUp()
		self.caller = frappe.session.user
		self.email = "dmbanner%d@example.com" % MarksCase._n
		if not frappe.db.exists("User", self.email):
			frappe.get_doc({"doctype": "User", "email": self.email,
			                "first_name": "DMBanner", "send_welcome_email": 0}
			               ).insert(ignore_permissions=True).add_roles("Employee")
		frappe.db.set_value("Employee", self.emp, "user_id", self.email)

	def tearDown(self):
		frappe.set_user(self.caller)

	def status(self):
		from alvoraa_portal import hr_api
		frappe.set_user(self.email)
		try:
			return hr_api.get_checkin_status()
		finally:
			frappe.set_user("Administrator")

	def test_the_status_call_carries_the_days_marks(self):
		out = self.status()
		self.assertIn("marks", out)
		self.assertIsNotNone(out["marks"], "the banner would draw nothing")

	def test_they_are_measured_against_the_shift_the_employee_is_on(self):
		m = self.status()["marks"]
		self.assertEqual(m["shift"]["start"], "10:30")
		self.assertEqual(m["on_time_until"], "10:36")
		self.assertEqual(m["half_day_before"], "15:00")

	def test_a_punch_today_moves_the_half_day_line(self):
		"""Proves the endpoint hands its OWN punches to the calculator, rather
		than letting the two read the clock separately and disagree."""
		frappe.get_doc({"doctype": "Employee Checkin", "employee": self.emp,
		                "log_type": "IN", "time": today() + " 10:28:00"}
		               ).insert(ignore_permissions=True)
		m = self.status()["marks"]
		self.assertEqual(m["arrived"], "10:28")
		self.assertEqual(m["half_day_before"], "14:58")

	def test_somebody_with_no_employee_record_is_not_broken_by_it(self):
		from alvoraa_portal import hr_api
		frappe.db.set_value("Employee", self.emp, "user_id", "")
		frappe.set_user(self.email)
		try:
			self.assertTrue(hr_api.get_checkin_status().get("no_employee"))
		finally:
			frappe.set_user("Administrator")


class WhatLeavingNowWouldCost(MarksCase):
	"""The ladder: every band boundary as a departure clock time.

	Surbhi, 17 Oct 2026: "Every employee should see what time are their
	quarters, half day, according to the shift timing, compared to their
	current arrival time."

	A 10:30-20:30 shift is 600 minutes, so a band starting at P% becomes a
	clock time at arrival + P% of 600. All the figures below were worked out
	from the real DTC table by hand before the code was written.
	"""

	def rungs(self, *punches):
		out = self.marks(self.at(*punches))["ladder"]
		self.assertIsNotNone(out, "a tenant with a rule set has a ladder")
		return out

	def test_the_twelve_bands_become_five_rungs(self):
		"""68-75% and 75-90% both cost one quarter. Showing them apart is noise
		an employee has to read past, so bands with equal cost are merged."""
		steps = self.rungs("10:28:00")["steps"]
		self.assertEqual([s["quarters"] for s in steps], [0, 1, 2, 3, 4])

	def test_each_rung_is_a_clock_time_from_when_they_arrived(self):
		"""The percentage is span-over-shift, so 90% of 600 minutes is nine
		hours after their own first punch - 19:28 for somebody in at 10:28."""
		steps = self.rungs("10:28:00")["steps"]
		at = {s["quarters"]: s["leave_after"] for s in steps}
		self.assertEqual(at[0], "19:28")   # 90% of 600 = 540m
		self.assertEqual(at[1], "16:58")   # 65% of 600 = 390m
		self.assertEqual(at[2], "14:28")   # 40% of 600 = 240m
		self.assertEqual(at[3], "12:28")   # 20% of 600 = 120m
		self.assertEqual(at[4], "10:28")   # 0%

	def test_arriving_late_moves_every_rung_with_them(self):
		"""THE REASON THIS IS NOT A TABLE OF FIXED TIMES. Somebody in at 11:12
		has to stay 44 minutes later for the same money. A ladder pinned to the
		shift start would tell them the opposite."""
		at = {s["quarters"]: s["leave_after"]
		      for s in self.rungs("11:12:00")["steps"]}
		self.assertEqual(at[0], "20:12")
		self.assertEqual(at[1], "17:42")
		self.assertEqual(at[2], "15:12")

	def test_before_anybody_arrives_it_is_measured_from_the_shift_start(self):
		"""The same anchor the half-day line uses, so the two agree."""
		at = {s["quarters"]: s["leave_after"] for s in self.rungs()["steps"]}
		self.assertEqual(at[2], "14:30")   # 10:30 + 240m

	def test_the_red_window_just_after_a_cliff_is_named(self):
		"""The dangerous minutes are the ones straight after each drop: the
		40-44% band costs two quarters AND a red, so leaving at 14:30 costs
		twice while leaving at 15:00 costs once."""
		steps = {s["quarters"]: s for s in self.rungs("10:28:00")["steps"]}
		self.assertEqual(steps[2]["red_from"], "14:28")
		self.assertEqual(steps[2]["red_to"], "14:52")

	def test_the_top_rung_carries_its_own_red_window(self):
		"""90-98.9% takes no quarters but does raise a red, so a full day's pay
		with a mark against it is reachable - and has to be said."""
		steps = {s["quarters"]: s for s in self.rungs("10:28:00")["steps"]}
		self.assertEqual(steps[0]["red_from"], "19:28")
		self.assertEqual(steps[0]["red_to"], "20:21")

	def test_a_rung_with_no_red_band_says_so_rather_than_guessing(self):
		steps = {s["quarters"]: s for s in self.rungs("10:28:00")["steps"]}
		self.assertIsNone(steps[4]["red_from"], "0-20% raises no red")

	def test_the_late_window_quarter_is_kept_separate(self):
		"""ATT-04 stacks on whatever the band decides and is never doubled.
		Folding it into the rungs would make every rung wrong by one for the
		people it applies to, and right for everybody else."""
		self.assertTrue(self.rungs("11:12:00")["extra_quarter"])
		self.assertFalse(self.rungs("10:28:00")["extra_quarter"])

	def test_it_carries_the_shift_length_it_measured_against(self):
		out = self.rungs("10:28:00")
		self.assertEqual(out["shift_minutes"], 600)
		self.assertEqual(out["anchor"], "10:28")

	def test_the_site_clock_is_sent_not_the_browser_s(self):
		"""The page places "you are here" against this, so a device an hour out
		does not light the wrong rung."""
		out = self.marks(self.at("10:28:00"))
		self.assertRegex(out["now"], r"^\d\d:\d\d$")

	def test_no_money_appears_anywhere_in_the_payload(self):
		"""Quarters are a fraction of a day, never an amount. Putting rupees on
		the home page would turn it into a payslip."""
		import json
		blob = json.dumps(self.marks(self.at("10:28:00")))
		for money in ("amount", "rupee", "mark_rate", "basic", "gross", "net",
		              "deduction", "earning"):
			self.assertNotIn(money, blob.lower(),
			                 "%s is pay, and this screen is not a payslip" % money)


class ATenantWithNoQuarters(MarksCase):
	def setUp(self):
		super().setUp()
		self.row = {"company": self._bare_company()}

	def _bare_company(self):
		with_rules = set(frappe.get_all("Alvoraa Payroll Rule Set", pluck="company"))
		for c in frappe.get_all("Company", pluck="name"):
			if c not in with_rules:
				return c
		return None

	def test_no_rule_set_means_no_ladder_at_all(self):
		"""Quarters are a rule-set idea. An empty ladder, or one invented from
		nothing, would be worse than showing the half-day line alone."""
		if not self.row["company"]:
			self.skipTest("every company on this site has a rule set")
		self.assertIsNone(self.marks(self.at("10:28:00"))["ladder"])

	def test_somebody_with_no_shift_still_gets_nothing(self):
		self.assertIsNone(marks_today(self.emp, self.row, None, [], DAY))
