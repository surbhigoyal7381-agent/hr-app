"""Reviewing your own attendance, and asking HR to fix a day that is wrong.

The engine underneath is Frappe HR's Attendance Request, which already creates
and overwrites Attendance rows on approval. Nothing here re-implements that. What
is tested is the part we own: that the reasons on offer can actually be saved,
that a person only ever sees and disputes their OWN days, and that the state
reported back to them is the true one.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction as ac

SHIFT = "AC Test Shift"          # 09:00-18:00, nine hours


HOLIDAYS = "AC Test Holidays"


def setUpModule():
	"""The reasons and the review fields have to be on the site before any of
	this can pass.

	They arrive through after_install and after_migrate in production. A test
	run should not depend on which of those a particular site happened to go
	through - CI builds its site with `bench install-app` and nothing else, and
	before this line existed the whole file failed on "Unknown column
	alvoraa_review_status". Both calls run by themselves and cost nothing when
	the fields are already there.
	"""
	ac.after_migrate()
	frappe.clear_cache(doctype=ac.REQUEST)


def _company():
	return frappe.db.get_value("Company", {}, "name")


def _holiday_list(company):
	"""Attendance Request asks whether each day is a holiday before it marks it.

	Without one, Frappe HR throws "No Holiday List was found for Employee", so
	a test employee needs the same setup a real one does. In v16 that is a
	**Holiday List Assignment** - the `holiday_list` field on Employee is no
	longer what gets read, which is why setting it alone changed nothing.
	"""
	if not frappe.db.exists("Holiday List", HOLIDAYS):
		frappe.get_doc({
			"doctype": "Holiday List", "holiday_list_name": HOLIDAYS,
			"from_date": add_days(nowdate(), -2000), "to_date": add_days(nowdate(), 400),
			"holidays": [{"holiday_date": nowdate(), "description": "A day off"}],
		}).insert(ignore_permissions=True)

	# One assignment for the whole company covers every test employee, so this
	# does not have to be repeated per person.
	if not frappe.db.exists("Holiday List Assignment",
	                        {"assigned_to": company, "holiday_list": HOLIDAYS,
	                         "docstatus": 1}):
		frappe.get_doc({
			"doctype": "Holiday List Assignment", "holiday_list": HOLIDAYS,
			"applicable_for": "Company", "assigned_to": company,
			"from_date": add_days(nowdate(), -2000),
		}).insert(ignore_permissions=True).submit()
	return HOLIDAYS


class TheReasonsWeOffer(FrappeTestCase):
	def test_every_reason_the_portal_offers_can_be_saved(self):
		"""The bug this slice starts from.

		The portal's dropdown was hardcoded and had drifted from the field, so
		four of its six reasons threw on save. The list must come FROM the field,
		which is the only version of it that cannot drift.
		"""
		allowed = set(frappe.get_meta(ac.REQUEST)
		              .get_field("reason").options.split("\n"))
		for r in ac.reasons():
			self.assertIn(r["value"], allowed,
			              "the portal offers %r, which the field will refuse" % r["value"])

	def test_forgetting_to_punch_is_one_of_them(self):
		"""The case that prompted this work. If it is not on the list, the
		employee picks something untrue instead."""
		values = " ".join(r["value"] for r in ac.reasons()).lower()
		self.assertIn("punch", values)

	def test_a_reason_carries_the_status_it_will_produce(self):
		"""A person is agreeing to what the day will become, so it has to be on
		screen before they agree to it - not a surprise after HR approves."""
		for r in ac.reasons():
			self.assertIn(r["becomes"], ("Present", "Work From Home", "Half Day"))

	def test_widening_the_list_keeps_what_was_already_there(self):
		"""An organisation may have added reasons of their own. Replacing the
		list would invalidate every request that used one."""
		before = set(frappe.get_meta(ac.REQUEST).get_field("reason").options.split("\n"))
		ac.install_reasons()
		frappe.clear_cache(doctype=ac.REQUEST)
		after = set(frappe.get_meta(ac.REQUEST).get_field("reason").options.split("\n"))
		self.assertTrue(before <= after)

	def test_frappe_hrs_own_two_reasons_keep_their_exact_spelling(self):
		"""The controller reads `reason == "Work From Home"` to decide the
		status. Renaming it would silently mark those days Present."""
		values = {r["value"] for r in ac.reasons()}
		self.assertIn("Work From Home", values)
		self.assertIn("On Duty", values)


class TheFieldsReachEverySite(FrappeTestCase):
	"""How the columns get onto a site, which CI caught us getting wrong.

	The hook was wired to after_migrate only. A site is BUILT with
	`bench install-app`, which never runs a migrate, so a brand new tenant had
	no review columns and every correction died on "Unknown column
	alvoraa_review_status". Not a CI quirk - CI just happened to be the first
	fresh site anyone made.
	"""

	def test_it_is_wired_to_a_fresh_install_not_only_to_migrate(self):
		want = "alvoraa_portal.attendance_correction.after_migrate"
		self.assertIn(want, frappe.get_hooks("after_install", app_name="alvoraa_portal") or [],
		              "a fresh tenant would have no review columns")
		self.assertIn(want, frappe.get_hooks("after_migrate", app_name="alvoraa_portal") or [],
		              "an existing tenant would never receive them")

	def test_the_columns_actually_exist(self):
		"""The field being on the meta is not the same as the column being in
		the table, and it is the column that the write hits."""
		ac.after_migrate()
		columns = frappe.db.get_table_columns(ac.REQUEST)
		for field in ("alvoraa_review_status", "alvoraa_review_note",
		              "alvoraa_reviewed_by", "alvoraa_reviewed_on"):
			self.assertIn(field, columns)

	def test_running_it_twice_changes_nothing(self):
		"""It runs on every migrate for the life of the product."""
		ac.after_migrate()
		before = frappe.get_meta(ac.REQUEST).get_field("reason").options
		ac.after_migrate()
		frappe.clear_cache(doctype=ac.REQUEST)
		self.assertEqual(before, frappe.get_meta(ac.REQUEST).get_field("reason").options)

	def test_it_declines_quietly_when_frappe_hr_is_not_there_yet(self):
		"""Install order is not ours to choose. Failing here would fail the
		whole app install rather than wait for the next migrate."""
		real = frappe.db.exists
		frappe.db.exists = lambda dt, name=None, *a, **k: (
			None if (dt == "DocType" and name == ac.REQUEST) else real(dt, name, *a, **k))
		try:
			self.assertFalse(ac.after_migrate())
		finally:
			frappe.db.exists = real


class CorrectionCase(FrappeTestCase):
	# Same reason as the analytics tests: Frappe rolls a test back but does not
	# roll back the naming counter, so two tests can be handed the same employee
	# id. A window each keeps one test's attendance out of the next one's month.
	_slot = 0

	def setUp(self):
		self.company = _company()
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		CorrectionCase._slot += 1
		self.offset = 400 + CorrectionCase._slot * 40
		if not frappe.db.exists("Shift Type", SHIFT):
			frappe.get_doc({"doctype": "Shift Type", "name": SHIFT,
			                "start_time": "09:00:00", "end_time": "18:00:00"}
			               ).insert(ignore_permissions=True)
		self.holidays = _holiday_list(self.company)

	def tearDown(self):
		frappe.set_user(self.caller)

	def d(self, i=0):
		"""A day inside this test's own window."""
		return add_days(nowdate(), -(self.offset + i))

	def ym(self, i=0):
		day = frappe.utils.getdate(self.d(i))
		return day.year, day.month

	def person(self, first, roles=()):
		email = "%s.ac@example.com" % first.lower()
		if not frappe.db.exists("User", email):
			u = frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
			                    "send_welcome_email": 0}).insert(ignore_permissions=True)
			for r in roles:
				u.add_roles(r)
		e = frappe.get_doc({
			"doctype": "Employee", "first_name": first, "company": self.company,
			"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "default_shift": SHIFT, "user_id": email,
			"holiday_list": self.holidays,
		}).insert(ignore_permissions=True)
		# Frappe HR matches the day's existing Attendance row BY SHIFT when it
		# applies a correction. With no Shift Assignment the request carries no
		# shift, the match misses, and it tries to insert a second row for the
		# same day - DuplicateAttendanceError. Real employees have one.
		frappe.get_doc({
			"doctype": "Shift Assignment", "employee": e.name, "shift_type": SHIFT,
			"company": self.company, "start_date": add_days(nowdate(), -2000),
			"end_date": add_days(nowdate(), 400),
		}).insert(ignore_permissions=True).submit()
		return e.name, email

	def day(self, employee, date, hours, status="Present", in_time=None, out_time=None):
		a = frappe.get_doc({
			"doctype": "Attendance", "employee": employee, "attendance_date": date,
			"status": status, "working_hours": hours, "shift": SHIFT,
			"in_time": in_time, "out_time": out_time,
			"company": self.company}).insert(ignore_permissions=True)
		a.submit()
		return a.name

	def punch(self, employee, when, log_type, attendance=None, where=None):
		# The attendance link is set AFTER the insert. Employee Checkin refuses
		# a time on a row that already carries one ("please cancel the
		# attendance before modifying time"), and the real auto-attendance job
		# writes them in this order for the same reason.
		# Coordinates supplied so these tests do not depend on whether the site
		# happens to have geolocation tracking on. They are about punches, not
		# about where somebody was, and a global setting should not decide
		# whether they can run.
		c = frappe.get_doc({
			"doctype": "Employee Checkin", "employee": employee, "time": when,
			"log_type": log_type, "device_id": where,
			"latitude": 28.6519, "longitude": 77.1906,
			"skip_auto_attendance": 1}).insert(ignore_permissions=True)
		if attendance:
			frappe.db.set_value("Employee Checkin", c.name, "attendance", attendance,
			                    update_modified=False)
		return c.name

	def my_day(self, email, i):
		y, m = self.ym(i)
		return [d for d in ac.month(y, m)["days"] if d["date"] == self.d(i)][0]


class TheMonthYouSee(CorrectionCase):
	def test_it_is_your_own_month_and_nobody_elses(self):
		"""The whole screen is one person's personal data. The endpoint is
		whitelisted, so the employee it is about can never come from the caller."""
		mine, my_email = self.person("ACMine")
		theirs, _e = self.person("ACTheirs")
		self.day(mine, self.d(3), 9.0)
		self.day(theirs, self.d(3), 9.0)

		frappe.set_user(my_email)
		y, m = self.ym(3)
		out = ac.month(y, m)
		self.assertEqual(out["employee"], mine)
		self.assertEqual(len([d for d in out["days"] if d["attendance"]]), 1)

	def test_a_day_says_what_is_actually_wrong_with_it(self):
		"""A red mark you cannot explain is not reviewable. The old calendar
		fetched these fields and drew none of them."""
		p, email = self.person("ACDetail")
		self.day(p, self.d(3), 6.5)
		frappe.set_user(email)
		day = self.my_day(email, 3)
		self.assertEqual(day["status"], "Present")
		self.assertEqual(day["expected_hours"], 9.0)
		self.assertEqual(day["hours"], 6.5)
		self.assertGreater(day["short_by"], 0)

	def test_a_weekend_is_not_an_absence(self):
		"""Every day with no record is not a missing day. Marking them absent
		would put a red mark on every weekend and on today before you leave."""
		p, email = self.person("ACQuiet")
		frappe.set_user(email)
		y, m = self.ym()
		out = ac.month(y, m)
		self.assertEqual(out["totals"]["absent"], 0)
		self.assertTrue(all(d["state"] != "absent" for d in out["days"]))

	def test_a_day_with_no_shift_is_not_short(self):
		"""There is nothing to be short of, so a shortfall would be invented."""
		p, email = self.person("ACNoShift")
		frappe.db.set_value("Employee", p, "default_shift", None)
		a = frappe.get_doc({"doctype": "Attendance", "employee": p,
		                    "attendance_date": self.d(3), "status": "Present",
		                    "working_hours": 2.0, "company": self.company}
		                   ).insert(ignore_permissions=True)
		a.submit()
		frappe.set_user(email)
		self.assertEqual(self.my_day(email, 3)["short_by"], 0.0)

	def test_somebody_with_no_employee_record_is_told_so(self):
		email = "acnobody@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "ACNo",
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		frappe.set_user(email)
		with self.assertRaises(frappe.PermissionError):
			ac.month()

	def test_a_month_that_is_not_a_month_is_refused(self):
		p, email = self.person("ACBadMonth")
		frappe.set_user(email)
		with self.assertRaises(frappe.ValidationError):
			ac.month(2026, 13)


class TheShapeOfADay(CorrectionCase):
	"""The part taken from what competitors do well: a strip of the day rather
	than one total. A missing second punch is invisible in a total and obvious
	in a strip, and it is the commonest reason a correction is needed."""

	def test_the_punches_come_back_in_order(self):
		p, email = self.person("ACPunches")
		att = self.day(p, self.d(3), 7.5)
		self.punch(p, self.d(3) + " 13:50:00", "IN", att, "Gate 2")
		self.punch(p, self.d(3) + " 09:32:00", "IN", att, "Gate 1")
		self.punch(p, self.d(3) + " 13:04:00", "OUT", att, "Gate 1")
		frappe.set_user(email)
		marks = self.my_day(email, 3)["punches"]
		self.assertEqual([m["at"] for m in marks], ["09:32", "13:04", "13:50"])
		self.assertEqual(marks[0]["where"], "Gate 1")

	def test_an_odd_number_of_punches_is_called_out(self):
		"""Two INs and one OUT means one never registered."""
		p, email = self.person("ACOdd")
		att = self.day(p, self.d(3), 4.0)
		self.punch(p, self.d(3) + " 09:00:00", "IN", att)
		self.punch(p, self.d(3) + " 13:00:00", "OUT", att)
		self.punch(p, self.d(3) + " 13:45:00", "IN", att)
		frappe.set_user(email)
		self.assertTrue(self.my_day(email, 3)["missing_punch"])

	def test_a_clean_pair_is_not_called_out(self):
		"""Crying wolf on a normal day is how a flag stops being read."""
		p, email = self.person("ACEven")
		att = self.day(p, self.d(3), 9.0)
		self.punch(p, self.d(3) + " 09:00:00", "IN", att)
		self.punch(p, self.d(3) + " 18:00:00", "OUT", att)
		frappe.set_user(email)
		self.assertFalse(self.my_day(email, 3)["missing_punch"])

	def test_an_in_with_no_out_is_called_out_even_with_no_punch_rows(self):
		"""Not every tenant runs Employee Checkin. The attendance row alone
		still shows the commonest case, so the screen must not need punches."""
		p, email = self.person("ACNoDevice")
		self.day(p, self.d(3), 3.0, in_time=self.d(3) + " 09:00:00")
		frappe.set_user(email)
		day = self.my_day(email, 3)
		self.assertEqual(day["punches"], [])
		self.assertTrue(day["missing_punch"])

	def test_late_is_measured_not_just_flagged(self):
		"""Frappe's late_entry is a yes/no. "Late" without "by how much" is the
		kind of number that starts an unfair conversation."""
		p, email = self.person("ACLate")
		self.day(p, self.d(3), 8.0, in_time=self.d(3) + " 09:47:00")
		frappe.set_user(email)
		day = self.my_day(email, 3)
		self.assertEqual(day["late_by_mins"], 47)
		self.assertEqual(day["shift_starts"], "09:00")
		self.assertEqual(day["shift_ends"], "18:00")

	def test_arriving_on_time_is_zero_not_a_small_negative(self):
		p, email = self.person("ACOnTime")
		self.day(p, self.d(3), 9.0, in_time=self.d(3) + " 08:52:00")
		frappe.set_user(email)
		self.assertEqual(self.my_day(email, 3)["late_by_mins"], 0)

	def test_the_month_counts_what_the_list_leads_with(self):
		p, email = self.person("ACTotals")
		self.day(p, self.d(3), 6.0, in_time=self.d(3) + " 09:30:00")
		frappe.set_user(email)
		y, m = self.ym(3)
		totals = ac.month(y, m)["totals"]
		self.assertEqual(totals["late_days"], 1)
		self.assertEqual(totals["short_days"], 1)
		self.assertEqual(totals["hours_worked"], 6.0)


class RaisingOne(CorrectionCase):
	def test_forgetting_to_punch_in_goes_through(self):
		"""The exact case this slice exists for, end to end. Before it, the
		nearest reason on the portal was one the field refused."""
		p, email = self.person("ACPunch")
		self.day(p, self.d(3), 0.0, status="Absent")
		frappe.set_user(email)
		out = ac.raise_correction(self.d(3), reason="Forgot to Punch In",
		                          explanation="Badge would not read.")
		self.assertEqual(out["state"], "waiting")
		self.assertEqual(out["says"], "Waiting for HR")

	def test_a_reason_the_field_would_refuse_is_refused_here_first(self):
		"""With a clear message, rather than Frappe's "should be one of"."""
		p, email = self.person("ACBadReason")
		frappe.set_user(email)
		with self.assertRaises(frappe.ValidationError):
			ac.raise_correction(self.d(3), reason="Because I Say So")

	def test_other_has_to_be_explained(self):
		"""An unexplained "Other" gives HR nothing to decide on, so it would
		bounce back anyway - better to say so while the person is still typing."""
		p, email = self.person("ACOther")
		frappe.set_user(email)
		with self.assertRaises(frappe.ValidationError):
			ac.raise_correction(self.d(3), reason="Other", explanation="   ")

	def test_you_cannot_raise_one_for_tomorrow(self):
		p, email = self.person("ACFuture")
		frappe.set_user(email)
		with self.assertRaises(frappe.ValidationError):
			ac.raise_correction(add_days(nowdate(), 3), reason="On Duty")

	def test_it_is_raised_against_you_whatever_is_sent(self):
		"""The endpoint takes no employee argument at all. This pins that down,
		because adding one later would let anybody rewrite anybody's attendance."""
		p, email = self.person("ACSelfOnly")
		frappe.set_user(email)
		out = ac.raise_correction(self.d(3), reason="On Duty")
		self.assertEqual(frappe.db.get_value(ac.REQUEST, out["name"], "employee"), p)

	def test_the_day_shows_the_request_raised_against_it(self):
		"""So nobody raises the same day twice, and so they can see where the
		first one got to without leaving the calendar."""
		p, email = self.person("ACLinked")
		self.day(p, self.d(3), 0.0, status="Absent")
		frappe.set_user(email)
		ac.raise_correction(self.d(3), reason="Marked Absent by Mistake")
		day = self.my_day(email, 3)
		self.assertIsNotNone(day["request"])
		self.assertEqual(day["request"]["state"], "waiting")


class WhatItSaysBack(CorrectionCase):
	def test_waiting_never_reads_as_draft(self):
		"""An employee cannot submit these, so every request they raise sits at
		docstatus 0 until HR acts. Calling that "Draft" told them they had not
		finished it."""
		p, email = self.person("ACWait")
		frappe.set_user(email)
		out = ac.raise_correction(self.d(3), reason="On Duty")
		self.assertEqual(out["state"], "waiting")
		self.assertNotIn("draft", out["says"].lower())

	def test_approving_from_the_desk_still_updates_what_the_employee_sees(self):
		"""HR will not always use the portal. If the Desk leaves the label at
		"Waiting", the employee is told the opposite of the truth."""
		p, email = self.person("ACDesk")
		self.day(p, self.d(3), 0.0, status="Absent")
		frappe.set_user(email)
		req = ac.raise_correction(self.d(3), reason="Marked Absent by Mistake")

		frappe.set_user("Administrator")
		frappe.get_doc(ac.REQUEST, req["name"]).submit()

		frappe.set_user(email)
		mine = [r for r in ac.my_requests() if r["name"] == req["name"]][0]
		self.assertEqual(mine["state"], "approved")

	def test_approving_actually_corrects_the_day(self):
		"""The point of the whole screen. Frappe HR's own controller does this -
		the test is that we hand off to it rather than writing attendance."""
		p, email = self.person("ACFixed")
		self.day(p, self.d(3), 0.0, status="Absent")
		frappe.set_user(email)
		req = ac.raise_correction(self.d(3), reason="Marked Absent by Mistake")

		frappe.set_user("Administrator")
		ac.decide(req["name"], approve=1, note="Checked the gate log.")

		self.assertEqual(
			frappe.db.get_value("Attendance",
			                    {"employee": p, "attendance_date": self.d(3),
			                     "docstatus": 1}, "status"),
			"Present")

	def test_a_declined_request_does_not_look_like_a_waiting_one(self):
		"""They were the same badge before this. A person chasing HR about a
		request that was already turned down is the failure that caused."""
		p, email = self.person("ACDeclined")
		frappe.set_user(email)
		req = ac.raise_correction(self.d(3), reason="On Duty")

		frappe.set_user("Administrator")
		ac.decide(req["name"], approve=0, note="No client visit was booked that day.")

		frappe.set_user(email)
		mine = [r for r in ac.my_requests() if r["name"] == req["name"]][0]
		self.assertEqual(mine["state"], "declined")
		self.assertIn("client visit", mine["note"])

	def test_declining_without_a_reason_is_refused(self):
		"""A bare "no" tells the employee nothing about what to do next."""
		p, email = self.person("ACNoReason")
		frappe.set_user(email)
		req = ac.raise_correction(self.d(3), reason="On Duty")
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			ac.decide(req["name"], approve=0, note="  ")

	def test_withdrawing_is_not_the_same_as_being_declined(self):
		"""Flattening the two would tell somebody they were turned down when
		they simply changed their mind."""
		p, email = self.person("ACWithdraw")
		frappe.set_user(email)
		req = ac.raise_correction(self.d(3), reason="On Duty")
		out = ac.withdraw(req["name"])
		self.assertEqual(out["state"], "withdrawn")

	def test_you_cannot_withdraw_somebody_elses(self):
		p, email = self.person("ACOwner")
		other, other_email = self.person("ACNotOwner")
		frappe.set_user(email)
		req = ac.raise_correction(self.d(3), reason="On Duty")
		frappe.set_user(other_email)
		with self.assertRaises(frappe.PermissionError):
			ac.withdraw(req["name"])


class HRsSide(CorrectionCase):
	def test_an_employee_cannot_open_the_review_queue(self):
		"""It is every colleague's personal data. The page hides the panel, but
		the endpoint is whitelisted and the page is only a suggestion."""
		p, email = self.person("ACPlain")
		frappe.set_user(email)
		with self.assertRaises(frappe.PermissionError):
			ac.to_review()

	def test_an_employee_cannot_approve_their_own(self):
		"""The one that matters most: approving writes the attendance."""
		p, email = self.person("ACSelfApprove")
		frappe.set_user(email)
		req = ac.raise_correction(self.d(3), reason="On Duty")
		with self.assertRaises(frappe.PermissionError):
			ac.decide(req["name"], approve=1)

	def test_hr_sees_what_is_waiting(self):
		p, email = self.person("ACQueued")
		frappe.set_user(email)
		req = ac.raise_correction(self.d(3), reason="On Duty")
		frappe.set_user("Administrator")
		self.assertIn(req["name"], [r["name"] for r in ac.to_review(limit=200)])

	def test_a_decided_one_leaves_the_queue(self):
		"""Otherwise the queue only ever grows and stops being read."""
		p, email = self.person("ACLeaves")
		frappe.set_user(email)
		req = ac.raise_correction(self.d(3), reason="On Duty")
		frappe.set_user("Administrator")
		ac.decide(req["name"], approve=0, note="Not supported by the roster.")
		self.assertNotIn(req["name"], [r["name"] for r in ac.to_review(limit=200)])

	def test_the_same_one_cannot_be_decided_twice(self):
		p, email = self.person("ACTwice")
		frappe.set_user(email)
		req = ac.raise_correction(self.d(3), reason="On Duty")
		frappe.set_user("Administrator")
		ac.decide(req["name"], approve=0, note="Declined once.")
		with self.assertRaises(frappe.ValidationError):
			ac.decide(req["name"], approve=1, note="And again.")


class ReviewingSomebodyElse(CorrectionCase):
	"""HR and managers use this screen to look at a named person, so the whole
	thing becomes a record of one colleague's daily movements. That makes the
	boundary the most important part of it."""

	def test_an_employee_cannot_open_a_colleagues_month(self):
		p, email = self.person("ACNosy")
		other, _e = self.person("ACPrivate")
		self.day(other, self.d(3), 9.0)
		frappe.set_user(email)
		with self.assertRaises(frappe.PermissionError):
			ac.month(employee=other)

	def test_it_refuses_rather_than_quietly_showing_your_own(self):
		"""A silent fallback would leave somebody believing they had checked a
		colleague's record when they had checked their own."""
		p, email = self.person("ACFallback")
		other, _e = self.person("ACNotMine")
		frappe.set_user(email)
		with self.assertRaises(frappe.PermissionError):
			ac.month(employee=other)

	def test_a_manager_can_open_their_own_report(self):
		boss, boss_email = self.person("ACBoss")
		report, _e = self.person("ACReport")
		frappe.db.set_value("Employee", report, "reports_to", boss)
		self.day(report, self.d(3), 7.0)
		frappe.set_user(boss_email)
		out = ac.month(*self.ym(3), employee=report)
		self.assertEqual(out["employee"], report)
		self.assertFalse(out["is_self"])

	def test_a_manager_reaches_the_whole_line_not_just_direct_reports(self):
		boss, boss_email = self.person("ACHead")
		mid, _e = self.person("ACMid")
		junior, _e2 = self.person("ACJunior")
		frappe.db.set_value("Employee", mid, "reports_to", boss)
		frappe.db.set_value("Employee", junior, "reports_to", mid)
		frappe.set_user(boss_email)
		self.assertEqual(ac.month(*self.ym(3), employee=junior)["employee"], junior)

	def test_a_manager_cannot_open_somebody_outside_their_line(self):
		boss, boss_email = self.person("ACMgrA")
		stranger, _e = self.person("ACStranger")
		frappe.set_user(boss_email)
		with self.assertRaises(frappe.PermissionError):
			ac.month(employee=stranger)

	def test_hr_can_open_anybody_even_with_no_employee_record_of_their_own(self):
		"""Administrator is not on the payroll, and neither is most HR staff at
		a bigger company. Demanding an employee record before they may open
		anybody refused the screen to the people it is mostly built for."""
		p, _e = self.person("ACAnybody")
		self.day(p, self.d(3), 9.0)
		frappe.set_user("Administrator")
		self.assertEqual(ac.month(*self.ym(3), employee=p)["employee"], p)

	def test_reviewing_somebody_else_offers_no_request_button(self):
		"""Raising a correction in another person's name would put words in
		their mouth. HR fixes the record directly instead."""
		p, _e = self.person("ACNoButton")
		frappe.set_user("Administrator")
		out = ac.month(*self.ym(3), employee=p)
		self.assertFalse(out["can_request"])

	def test_your_own_month_still_offers_it(self):
		p, email = self.person("ACOwnButton")
		frappe.set_user(email)
		self.assertTrue(ac.month(*self.ym(3))["can_request"])

	def test_the_picker_is_empty_for_somebody_who_reviews_nobody(self):
		"""Otherwise it is a staff directory handed to every employee."""
		p, email = self.person("ACNoTeam")
		frappe.set_user(email)
		self.assertEqual(ac.whose_months_i_can_open(), [])

	def test_the_picker_gives_a_manager_their_own_line(self):
		boss, boss_email = self.person("ACPickBoss")
		report, _e = self.person("ACPickReport")
		outsider, _e2 = self.person("ACPickOutsider")
		frappe.db.set_value("Employee", report, "reports_to", boss)
		frappe.set_user(boss_email)
		names = [r["name"] for r in ac.whose_months_i_can_open(limit=500)]
		self.assertIn(report, names)
		self.assertNotIn(outsider, names)


class NoQuietBypass(CorrectionCase):
	def test_this_module_never_ignores_permissions(self):
		"""The security review asked for this to stop spreading. Every read here
		is a get_list under the caller's own permissions AND narrowed to the
		employee it is about; every write goes through the document's own check.

		A source check rather than a behaviour test on purpose - the point is
		that the NEXT person to edit this file has to make the same decision
		deliberately, instead of copying the line in from a neighbouring module.
		"""
		import ast
		import inspect

		# Docstrings are blanked first. This module's own opening paragraph
		# explains that it never ignores permissions, and a plain substring
		# search accused it of doing exactly that.
		tree = ast.parse(inspect.getsource(ac))
		for node in ast.walk(tree):
			if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
				first = node.body[0] if node.body else None
				if (isinstance(first, ast.Expr)
						and isinstance(first.value, ast.Constant)
						and isinstance(first.value.value, str)):
					first.value.value = ""
		self.assertNotIn("ignore_permissions", ast.unparse(tree))
