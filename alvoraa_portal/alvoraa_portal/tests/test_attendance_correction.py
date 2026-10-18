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

	def recent(self):
		"""The newest day that is not a day off, so inside the filing window.

		Picked, not assumed. Frappe HR refuses an Attendance Request that
		covers only holidays, and the shared list has a day off on the day it
		was built - so "yesterday" is not always a day a request can exist for.
		The newest non-holiday day is inside any window of one working day or
		more, which is every setting but the tightest.
		"""
		off = {str(frappe.utils.getdate(d)) for d in frappe.get_all(
			"Holiday",
			filters={"parent": self.holidays, "parenttype": "Holiday List",
			         "holiday_date": ["between", [add_days(nowdate(), -12), nowdate()]]},
			pluck="holiday_date")}
		for i in range(12):
			day = add_days(nowdate(), -i)
			if str(frappe.utils.getdate(day)) not in off:
				return day
		return nowdate()

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
			# Covers THIS test's own window. A fixed -2000 was fine until
			# enough classes existed to push `offset` past it, and then the
			# day fell outside the assignment, the request carried no shift,
			# the match missed and a SECOND attendance row was inserted -
			# surfacing as DuplicateAttendanceError on an unrelated test.
			"company": self.company,
			"start_date": add_days(nowdate(), -(self.offset + 200)),
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

	def test_hr_reviewing_somebody_offers_no_request_button(self):
		"""HR DECIDES corrections, so HR is not offered the button that asks
		for one. A reviewer who could also raise one would be deciding their
		own request, which `decide` refuses - the button would be a dead end
		dressed up as an action.

		Changed on 17 Oct 2026 only in what it claims: this used to be the
		rule for everybody who was not the employee. A direct manager now gets
		the button (see `AManagerRaisingItForSomebodyElse`); HR still does
		not.
		"""
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


class WhoMayAskFromSomebodyElsesMonth(CorrectionCase):
	"""`can_request` is what puts the button on a day, so it has to agree with
	`raise_for_report` exactly.

	Surbhi, 15 Oct 2026: "let's get the manager request the changes and the HR
	to confirm or reject it." Surbhi, 17 Oct 2026: "direct reports only." The
	flag used to be `is_self` alone, so the manager's route existed in the
	endpoint with no way to reach it from the day it is about.

	A flag that said yes where the endpoint says no would show a button that
	refuses when pressed, so each case below checks BOTH.
	"""

	def setUp(self):
		super().setUp()
		tag = CorrectionCase._slot
		self.boss, self.boss_email = self.person("Cqboss%d" % tag, roles=("Employee",))
		self.report, self.report_email = self.person("Cqrep%d" % tag, roles=("Employee",))
		self.deep, _ = self.person("Cqdeep%d" % tag, roles=("Employee",))
		# Saved rather than set_value: saving is what fires the hook that
		# grants the manager's User Permission in production, and the document
		# check inside `raise_for_report` depends on it.
		for who, boss in ((self.report, self.boss), (self.deep, self.report)):
			e = frappe.get_doc("Employee", who)
			e.reports_to = boss
			e.save(ignore_permissions=True)

	def as_boss(self, fn):
		frappe.set_user(self.boss_email)
		try:
			return fn()
		finally:
			frappe.set_user("Administrator")

	def test_a_direct_report_gets_the_button(self):
		y, m = self.ym(1)
		out = self.as_boss(lambda: ac.month(year=y, month=m, employee=self.report))
		self.assertTrue(out["can_request"],
		                "a manager must be able to ask from the day itself")

	def test_and_the_button_works(self):
		"""The flag is only honest if the endpoint behind it says yes too.

		Yesterday, not this test's own window 400-odd days back: the manager's
		path has a filing window now (SEC-9a), and this test is about who may
		ask, not about how far back they may ask.
		"""
		req = self.as_boss(
			lambda: ac.raise_for_report(self.report, self.recent(),
			                            reason="On Duty"))
		self.assertEqual(frappe.db.get_value("Attendance Request", req["name"],
		                                     "employee"), self.report)

	def test_a_skip_level_month_opens_but_offers_nothing(self):
		"""Reading reaches the whole line; asking stops at the direct reports.
		So the month still opens - taking that away would remove a screen
		managers use - and it opens read-only."""
		y, m = self.ym(1)
		out = self.as_boss(lambda: ac.month(year=y, month=m, employee=self.deep))
		self.assertEqual(out["employee"], self.deep, "reading must still work")
		self.assertFalse(out["can_request"], "acting stops at the direct reports")

	def test_and_the_endpoint_agrees_about_the_skip_level(self):
		with self.assertRaises(frappe.PermissionError):
			self.as_boss(
				lambda: ac.raise_for_report(self.deep, self.d(1), reason="On Duty"))



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


class AManagersWholeTeamOnOnePage(CorrectionCase):
	"""Surbhi, 17 Oct 2026: "we would need one page with filter for all the
	reporting persons first", and "only attendance facts".

	Before this, a manager could open ONE report's month if they knew to look -
	there was no screen that showed the team at once, and nothing surfaced the
	days somebody has to act on.
	"""

	def setUp(self):
		super().setUp()
		tag = CorrectionCase._slot
		self.boss, self.boss_email = self.person("Tdboss%d" % tag, roles=("Employee",))
		self.a, self.a_email = self.person("Tdone%d" % tag, roles=("Employee",))
		self.b, self.b_email = self.person("Tdtwo%d" % tag)
		self.outsider, _ = self.person("Tdout%d" % tag)
		for who in (self.a, self.b):
			frappe.db.set_value("Employee", who, "reports_to", self.boss)

	def team(self, **kw):
		frappe.set_user(self.boss_email)
		try:
			return ac.team_days(from_date=self.d(5), to_date=self.d(0), **kw)
		finally:
			frappe.set_user("Administrator")

	def test_the_page_opens_on_the_direct_reports_not_the_whole_line(self):
		"""Surbhi, 17 Oct 2026: "direct reports only". The page opens on the
		people a manager can actually DO something about, because acting stops
		at the direct reports - offering a skip-level day with a button that
		then refuses would be worse than not offering it."""
		below, _ = self.person("Tddeep%d" % CorrectionCase._slot)
		frappe.db.set_value("Employee", below, "reports_to", self.a)
		self.day(below, self.d(1), 9)
		self.day(self.a, self.d(1), 9)
		seen = {r["employee"] for r in self.team()["rows"]}
		self.assertIn(self.a, seen)
		self.assertNotIn(below, seen, "a grandchild is not a direct report")

	def test_the_whole_line_is_there_when_it_is_asked_for(self):
		"""The same choice Attendance Insights already offers, so a manager can
		still see what they are accountable for."""
		below, _ = self.person("Tdwide%d" % CorrectionCase._slot)
		frappe.db.set_value("Employee", below, "reports_to", self.a)
		self.day(below, self.d(1), 9)
		seen = {r["employee"] for r in self.team(depth="all")["rows"]}
		self.assertIn(below, seen)

	def test_a_page_says_how_many_there_were_altogether(self):
		"""Without a total, somebody reaching the end of page one cannot tell
		whether they are finished."""
		for i in range(1, 5):
			self.day(self.a, self.d(i), 9)
		out = self.team(page_length=2)
		self.assertEqual(len(out["rows"]), 2)
		self.assertGreaterEqual(out["total"], 4)
		self.assertEqual(out["page_length"], 2)

	def test_the_second_page_carries_on_where_the_first_stopped(self):
		for i in range(1, 5):
			self.day(self.a, self.d(i), 9)
		first = self.team(page_length=2)
		second = self.team(page_length=2, start=2)
		self.assertEqual(second["start"], 2)
		keys = lambda o: {(r["employee"], r["date"]) for r in o["rows"]}
		self.assertFalse(keys(first) & keys(second), "a page must not repeat rows")

	def test_the_counts_are_for_the_whole_period_not_the_page(self):
		"""A chip reading "4 need a look" has to mean four altogether. Counting
		only the page would tell a manager they were done at the end of page
		one."""
		for i in range(1, 5):
			day = self.d(i)
			self.day(self.a, day, 0, status="Absent", in_time=day + " 09:04:00")
			self.punch(self.a, day + " 09:04:00", "IN")
		out = self.team(page_length=1)
		self.assertEqual(len(out["rows"]), 1)
		self.assertGreaterEqual(out["counts"].get("no_clock_out", 0), 4)

	def test_a_page_cannot_be_asked_to_exceed_the_safety_net(self):
		self.day(self.a, self.d(1), 9)
		self.assertLessEqual(self.team(page_length=99999, limit=5)["page_length"], 5)

	def test_narrowing_by_branch_empties_the_person_filter_too(self):
		"""The picker and the rows must agree. A branch filter that left every
		colleague in the picker would read as a broken page."""
		self.day(self.a, self.d(1), 9)
		out = self.team(branch="No Such Branch")
		self.assertEqual(out["rows"], [])
		self.assertEqual(out["people"], [])

	def test_a_manager_sees_both_reports_and_not_the_outsider(self):
		self.day(self.a, self.d(1), 9, in_time=self.d(1) + " 09:00:00",
		         out_time=self.d(1) + " 18:00:00")
		self.day(self.b, self.d(1), 9, in_time=self.d(1) + " 09:00:00",
		         out_time=self.d(1) + " 18:00:00")
		self.day(self.outsider, self.d(1), 9)
		out = self.team()
		seen = {r["employee"] for r in out["rows"]}
		self.assertIn(self.a, seen)
		self.assertIn(self.b, seen)
		self.assertNotIn(self.outsider, seen,
		                 "a manager must not see somebody outside their line")

	def test_the_people_filter_lists_only_the_team(self):
		out = self.team()
		ids = {p["name"] for p in out["people"]}
		self.assertEqual(ids, {self.a, self.b})

	def test_one_punch_reads_as_no_clock_out_not_as_a_short_day(self):
		"""ATT-06. A day with one punch is unfinished, not short - and it is
		the commonest thing a manager is asked about."""
		day = self.d(2)
		self.day(self.a, day, 0, status="Absent", in_time=day + " 09:04:00")
		self.punch(self.a, day + " 09:04:00", "IN")
		row = [r for r in self.team()["rows"] if r["employee"] == self.a][0]
		self.assertEqual(row["flag"], "no_clock_out")
		self.assertEqual(row["punches"], 1)

	def test_absent_with_punches_is_told_apart_from_absent(self):
		"""Two people marked Absent, one of whom badged in twice. They need
		opposite answers, and on the attendance row alone they look alike."""
		day = self.d(3)
		self.day(self.a, day, 0, status="Absent")
		self.day(self.b, day, 0, status="Absent")
		self.punch(self.b, day + " 09:02:00", "IN")
		self.punch(self.b, day + " 18:05:00", "OUT")
		rows = {r["employee"]: r for r in self.team()["rows"] if r["date"] == day}
		self.assertEqual(rows[self.a]["flag"], "absent")
		self.assertEqual(rows[self.b]["flag"], "absent_but_punched")

	def test_the_days_needing_a_look_come_first(self):
		"""The ordering IS the value of the page. A manager should meet the
		days somebody must act on, not scroll to them."""
		self.day(self.a, self.d(1), 9, in_time=self.d(1) + " 09:00:00",
		         out_time=self.d(1) + " 18:00:00")
		bad = self.d(2)
		self.day(self.b, bad, 0, status="Absent", in_time=bad + " 09:04:00")
		self.punch(self.b, bad + " 09:04:00", "IN")
		flags = [r["flag"] for r in self.team()["rows"]]
		self.assertEqual(flags[0], "no_clock_out",
		                 "the unfinished day must be at the top")

	def test_it_can_be_narrowed_to_one_person(self):
		self.day(self.a, self.d(1), 9)
		self.day(self.b, self.d(1), 9)
		out = self.team(employee=self.a)
		self.assertEqual({r["employee"] for r in out["rows"]}, {self.a})

	def test_narrowing_to_somebody_outside_the_team_is_refused(self):
		"""Naming an employee must not be a way around the reporting line."""
		frappe.set_user(self.boss_email)
		try:
			with self.assertRaises(frappe.PermissionError):
				ac.team_days(from_date=self.d(5), to_date=self.d(0),
				             employee=self.outsider)
		finally:
			frappe.set_user("Administrator")

	def test_it_carries_no_pay_figures(self):
		"""Surbhi, 17 Oct 2026: "only attendance facts". A manager confirming
		what happened on a Tuesday does not need their team's pay, and this
		screen must not become a way to see it."""
		self.day(self.a, self.d(1), 9)
		row = self.team()["rows"][0]
		for money in ("quarters", "quarter_days", "paid_days", "basic", "gross",
		              "net", "green_pay", "red_deduction", "greens", "reds",
		              "daily_rate", "base"):
			self.assertNotIn(money, row, "%s is pay, not an attendance fact" % money)

	def test_somebody_who_manages_nobody_gets_an_empty_page_that_says_so(self):
		frappe.set_user(self.a_email)
		try:
			out = ac.team_days(from_date=self.d(5), to_date=self.d(0))
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(out["rows"], [])
		self.assertTrue(out.get("nobody"))

	def test_a_period_longer_than_three_months_is_refused(self):
		frappe.set_user(self.boss_email)
		try:
			with self.assertRaises(frappe.ValidationError):
				ac.team_days(from_date=add_days(nowdate(), -200), to_date=nowdate())
		finally:
			frappe.set_user("Administrator")


class AManagerRaisingItForSomebodyElse(CorrectionCase):
	"""Surbhi, 15 Oct 2026: "let's get the manager request the changes and the
	HR to confirm or reject it."
	"""

	def setUp(self):
		super().setUp()
		tag = CorrectionCase._slot
		self.boss, self.boss_email = self.person("Rfboss%d" % tag, roles=("Employee",))
		self.report, self.report_email = self.person("Rfrep%d" % tag, roles=("Employee",))
		self.outsider, _ = self.person("Rfout%d" % tag)
		# The reporting line, and the permission that goes with it. Saving the
		# employee is what fires the hook in production; set_value alone would
		# leave the line without its permission, which is a state the product
		# never reaches.
		e = frappe.get_doc("Employee", self.report)
		e.reports_to = self.boss
		e.save(ignore_permissions=True)

	def test_a_skip_level_report_is_refused_and_told_whose_job_it_is(self):
		"""Surbhi, 17 Oct 2026: "direct reports only."

		This also closes a real gap rather than only narrowing a rule.
		`manager_scope` grants the Frappe permission for DIRECT reports only, so
		before this a request for somebody further down passed our own check and
		then failed on the document's permission check - a confusing refusal,
		and only ever for skip-level reports, which is the case nobody tries by
		hand. The refusal now happens here, in words that say what to do.
		"""
		below, _ = self.person("Rfdeep%d" % CorrectionCase._slot)
		e = frappe.get_doc("Employee", below)
		e.reports_to = self.report
		e.save(ignore_permissions=True)

		frappe.set_user(self.boss_email)
		try:
			with self.assertRaises(frappe.PermissionError) as caught:
				ac.raise_for_report(below, self.d(1), reason="On Duty")
		finally:
			frappe.set_user("Administrator")
		self.assertIn("report directly", str(caught.exception))

	def test_reading_a_skip_level_month_still_works(self):
		"""Narrowing who a manager may ACT for must not take away a screen they
		already use. Reading the whole line is a different question, and
		`_subject` still answers yes to it."""
		below, _ = self.person("Rfread%d" % CorrectionCase._slot)
		e = frappe.get_doc("Employee", below)
		e.reports_to = self.report
		e.save(ignore_permissions=True)

		frappe.set_user(self.boss_email)
		try:
			y, m = self.ym(1)
			out = ac.month(year=y, month=m, employee=below)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(out["employee"], below)

	def test_a_manager_can_raise_one_for_a_report(self):
		# Yesterday: the manager's path is bounded by the filing window
		# (SEC-9a), which has its own class below.
		frappe.set_user(self.boss_email)
		try:
			out = ac.raise_for_report(self.report, self.recent(),
			                          reason="On Duty")
		finally:
			frappe.set_user("Administrator")
		doc = frappe.get_doc("Attendance Request", out["name"])
		self.assertEqual(doc.employee, self.report)
		self.assertEqual(doc.alvoraa_review_status, "Waiting")

	def test_it_records_who_vouched_for_the_day(self):
		"""HR should read a request that says a manager is standing behind it,
		not one that appears to have come from the employee."""
		frappe.set_user(self.boss_email)
		try:
			out = ac.raise_for_report(self.report, self.recent(),
			                          reason="On Duty")
		finally:
			frappe.set_user("Administrator")
		doc = frappe.get_doc("Attendance Request", out["name"])
		self.assertIn("Raised by", doc.explanation or "")

	def test_raising_one_for_somebody_who_does_not_report_to_you_is_refused(self):
		"""THE WHOLE GUARD. `raise_correction` refuses to take an employee from
		the request at all, because a field naming somebody else would let
		anyone rewrite anyone's attendance. Here the name is CHECKED."""
		frappe.set_user(self.boss_email)
		try:
			with self.assertRaises(frappe.PermissionError):
				ac.raise_for_report(self.outsider, self.d(1), reason="On Duty")
		finally:
			frappe.set_user("Administrator")

	def test_naming_yourself_goes_through_the_ordinary_path(self):
		"""Their own day keeps its own rules, and is not stamped as raised on
		somebody's behalf."""
		frappe.set_user(self.report_email)
		try:
			out = ac.raise_for_report(self.report, self.d(1), reason="On Duty")
		finally:
			frappe.set_user("Administrator")
		doc = frappe.get_doc("Attendance Request", out["name"])
		self.assertEqual(doc.employee, self.report)
		self.assertNotIn("Raised by", doc.explanation or "")

	def test_a_day_that_has_not_happened_is_refused(self):
		frappe.set_user(self.boss_email)
		try:
			with self.assertRaises(frappe.ValidationError):
				ac.raise_for_report(self.report, add_days(nowdate(), 3),
				                    reason="On Duty")
		finally:
			frappe.set_user("Administrator")

	def test_a_reason_the_field_would_refuse_is_caught_here_first(self):
		frappe.set_user(self.boss_email)
		try:
			with self.assertRaises(frappe.ValidationError):
				ac.raise_for_report(self.report, self.d(1), reason="Made Up")
		finally:
			frappe.set_user("Administrator")


class TheManagersFilingWindow(CorrectionCase):
	"""SEC-9a: a manager files for a recent day, and an old one goes to HR.

	Surbhi, 15 Oct 2026: "let's keep it a customizable window default to 48
	hrs. else HR will do the manual adjustments themselves in case of some
	genuine case." Settled the same day as two whole WORKING days, per tenant.

	Every day used here is counted from today on purpose. The rest of this file
	works in a window 400-odd days back so two tests cannot collide on the same
	attendance row, and the window is exactly the rule that cares what today is.
	"""

	def setUp(self):
		super().setUp()
		tag = CorrectionCase._slot
		self.boss, self.boss_email = self.person("Fwboss%d" % tag, roles=("Employee",))
		self.report, self.report_email = self.person("Fwrep%d" % tag, roles=("Employee",))
		e = frappe.get_doc("Employee", self.report)
		e.reports_to = self.boss
		e.save(ignore_permissions=True)
		self._saved_window = frappe.db.get_default(ac.MANAGER_FILING_WINDOW_KEY)
		# The shared holiday list carries a day off on the day it was built,
		# which moves with the calendar and would make the arithmetic below
		# depend on which day the suite happens to run. Cleared for this test
		# only - Frappe rolls it back - so each case puts its own days off in.
		frappe.db.delete("Holiday", {"parent": self.holidays,
		                             "holiday_date": [">=", add_days(nowdate(), -40)]})

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_default(ac.MANAGER_FILING_WINDOW_KEY, self._saved_window or "")
		super().tearDown()

	def window(self, days):
		frappe.db.set_default(ac.MANAGER_FILING_WINDOW_KEY, str(days))

	def back(self, i):
		return add_days(nowdate(), -i)

	def file_for(self, date, employee=None):
		frappe.set_user(self.boss_email)
		try:
			return ac.raise_for_report(employee or self.report, date, reason="On Duty")
		finally:
			frappe.set_user("Administrator")

	def day_off(self, date, weekly_off=0):
		"""Make one day a non-working day on this employee's own holiday list."""
		hl = frappe.get_doc("Holiday List", self.holidays)
		hl.append("holidays", {"holiday_date": date, "description": "Closed",
		                       "weekly_off": weekly_off})
		hl.save(ignore_permissions=True)

	def test_nothing_stored_means_two_working_days(self):
		frappe.db.set_default(ac.MANAGER_FILING_WINDOW_KEY, "")
		self.assertEqual(ac.manager_filing_window_days(), 2)

	def test_a_stored_zero_is_not_read_as_unset(self):
		"""The trap next door: `get_default(KEY) or DEFAULT` would turn the
		tightest setting a tenant can choose into the default one."""
		self.window(0)
		self.assertEqual(ac.manager_filing_window_days(), 0)

	def test_a_day_inside_the_window_goes_through(self):
		out = self.file_for(self.back(1))
		self.assertEqual(frappe.db.get_value("Attendance Request", out["name"],
		                                     "employee"), self.report)

	def test_a_day_outside_the_window_is_refused_and_sent_to_hr(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			self.file_for(self.back(20))
		self.assertIn("ask HR", str(caught.exception))

	def test_the_refusal_carries_the_configured_number(self):
		"""Not a hardcoded two, or the message stops being true the day a
		tenant changes the setting."""
		self.window(5)
		with self.assertRaises(frappe.ValidationError) as caught:
			self.file_for(self.back(20))
		said = str(caught.exception)
		self.assertIn("5 working days", said)
		self.assertNotIn("2 working days", said)

	def test_a_holiday_in_the_range_pushes_the_reach_further_back(self):
		"""The count is working days, so a day the store was shut does not use
		the window up. If this ever stops being true the range was built the
		wrong way round and the refusal is lying about how it counted."""
		with self.assertRaises(frappe.ValidationError):
			self.file_for(self.back(3))          # two working days reach day -2
		self.day_off(self.back(1))
		self.file_for(self.back(3))              # now day -1 is skipped, so -3 counts

	def test_a_weekly_off_counts_the_same_way(self):
		"""Frappe keeps the weekly offs as rows on the same holiday list, so
		there is no Monday-to-Friday assumption anywhere in the count."""
		self.day_off(self.back(1), weekly_off=1)
		self.file_for(self.back(3))

	def test_zero_means_today_only(self):
		self.window(0)
		self.file_for(nowdate())
		with self.assertRaises(frappe.ValidationError) as caught:
			self.file_for(self.back(1))
		self.assertIn("today", str(caught.exception))

	def test_an_employees_own_old_day_is_not_touched_by_the_window(self):
		"""The window bounds a MANAGER filing for somebody else. Narrowing what
		a person may ask about their own attendance was never asked for."""
		frappe.set_user(self.report_email)
		try:
			out = ac.raise_correction(self.d(1), reason="On Duty")
			through_the_other_door = ac.raise_for_report(self.report, self.d(2),
			                                            reason="On Duty")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Attendance Request", out["name"],
		                                     "employee"), self.report)
		self.assertEqual(frappe.db.get_value("Attendance Request",
		                                     through_the_other_door["name"],
		                                     "employee"), self.report)

	def test_hr_is_never_bounded_by_it(self):
		"""HR's manual route is the way out when a day is too old, so the
		window must not reach it. HR files on the desk, which is the document,
		and the window lives in the manager's endpoint."""
		self.window(1)
		doc = frappe.get_doc({
			"doctype": ac.REQUEST, "employee": self.report,
			"company": self.company, "from_date": self.d(1), "to_date": self.d(1),
			"reason": "On Duty", "alvoraa_review_status": "Waiting",
		}).insert(ignore_permissions=True)
		self.assertEqual(doc.employee, self.report)

	def test_the_setting_refuses_a_value_outside_its_range(self):
		"""The endpoint HR saves it through holds the same range the server
		counts with.

		`frappe.db.commit` is stubbed out for this one test. `set_org_setting`
		commits, which would take this test's own employees and users out of
		the rollback and leave them on the site for the next run to trip over -
		which is exactly what happened the first time this was run.
		"""
		from unittest.mock import patch

		from alvoraa_portal import hr_api

		hr = self.person("Fwhr%d" % CorrectionCase._slot, roles=("HR Manager",))[1]
		frappe.set_user(hr)
		try:
			with patch("frappe.db.commit"):
				self.assertEqual(
					hr_api.set_org_setting(ac.MANAGER_FILING_WINDOW_KEY, "3"),
					{"ok": True})
				self.assertEqual(
					hr_api.get_org_setting(ac.MANAGER_FILING_WINDOW_KEY), "3")
				for bad in ("31", "-1", "2.5", "two", "999", ""):
					with self.assertRaises(frappe.PermissionError, msg=bad):
						hr_api.set_org_setting(ac.MANAGER_FILING_WINDOW_KEY, bad)
				self.assertEqual(
					frappe.db.get_default(ac.MANAGER_FILING_WINDOW_KEY), "3")
		finally:
			frappe.set_user("Administrator")
