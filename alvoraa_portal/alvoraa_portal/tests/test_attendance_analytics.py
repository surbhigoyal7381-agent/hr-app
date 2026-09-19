"""Who may count whom, and whether the numbers mean what they say.

The metrics are arithmetic over data that already exists. The permission model
is new, it is bulk personal data, and the people picker is the part most likely
to leak - it takes a list of names from the browser and returns records. So most
of this file is about the boundary, as the brief's handoff note asked.

Every test calls the endpoint, never the page. A limit written in JavaScript is
a suggestion: the endpoint is whitelisted, and anybody who can open the portal
can call it with any argument they like.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_analytics as aa

SHIFT = "AA Test Shift"          # 09:00-18:00, nine hours


def _company():
	name = frappe.db.get_value("Company", {}, "name")
	if not name:
		name = frappe.get_doc({"doctype": "Company", "company_name": "AA Test Co",
		                       "abbr": "AAT", "default_currency": "INR"}
		                      ).insert(ignore_permissions=True).name
	return name


class AnalyticsCase(FrappeTestCase):
	# Each test gets its own fortnight. Frappe rolls a test back but does not
	# roll back the naming counter, so the next test's employee can be handed
	# the same id as the last one's - and anything that outlived the rollback
	# then looks like it belongs to the new person. Separate windows make that
	# impossible rather than unlikely.
	_slot = 0

	def setUp(self):
		self.company = _company()
		self.user = frappe.session.user
		frappe.set_user("Administrator")
		self._made = []
		AnalyticsCase._slot += 1
		self.offset = 90 + AnalyticsCase._slot * 20
		if not frappe.db.exists("Shift Type", SHIFT):
			frappe.get_doc({"doctype": "Shift Type", "name": SHIFT,
			                "start_time": "09:00:00", "end_time": "18:00:00"}
			               ).insert(ignore_permissions=True)

	def tearDown(self):
		# No deleting and no commit. FrappeTestCase wraps each test in a
		# transaction and rolls it back; committing here defeated that, so a
		# failed run left employees and attendance behind and the next run
		# collided with them ("Attendance is already marked for...").
		frappe.set_user(self.user)

	def person(self, first, reports_to=None):
		e = frappe.get_doc({
			"doctype": "Employee", "first_name": first, "company": self.company,
			"date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "default_shift": SHIFT, "reports_to": reports_to,
		}).insert(ignore_permissions=True)
		self._made.append(("Employee", e.name))
		return e.name

	def d(self, i):
		"""Day `i` inside this test's own window."""
		return add_days(nowdate(), -(self.offset + i))

	def day(self, employee, date, hours, status="Present"):
		a = frappe.get_doc({
			"doctype": "Attendance", "employee": employee, "attendance_date": date,
			"status": status, "working_hours": hours, "shift": SHIFT,
			"company": self.company,
		}).insert(ignore_permissions=True)
		a.submit()
		self._made.append(("Attendance", a.name))
		return a.name

	def summary(self, **kw):
		"""Always scoped to the people this test made.

		The organisation view means every active employee on the site, and a
		shared test site is full of other modules' fixtures. Without naming our
		own, a test asserting "no attendance" is really asserting something
		about somebody else's data.
		"""
		kw.setdefault("date_from", self.d(19))
		kw.setdefault("date_to", self.d(0))
		kw.setdefault("people", [n for dt, n in self._made if dt == "Employee"])
		return aa.summary(**kw)


class TestShortIsAboutHowOften(AnalyticsCase):
	def test_a_full_day_is_not_short(self):
		p = self.person("AAFull")
		self.day(p, self.d(3), 9.0)
		row = self.summary(view="organisation")["rows"][0]
		self.assertEqual(row["short_days"], 0)

	def test_inside_the_tolerance_is_not_short(self):
		"""Twenty minutes under a nine-hour shift is not an event."""
		p = self.person("AANear")
		self.day(p, self.d(3), 8.7)      # 18 minutes under
		self.assertEqual(self.summary(view="organisation")["rows"][0]["short_days"], 0)

	def test_past_the_tolerance_is_short(self):
		p = self.person("AAShort")
		self.day(p, self.d(3), 7.0)      # two hours under
		row = self.summary(view="organisation")["rows"][0]
		self.assertEqual(row["short_days"], 1)
		self.assertAlmostEqual(row["hours_short"], 1.5, places=1)   # past the 30 min

	def test_the_headline_is_a_rate_not_a_count(self):
		"""Somebody present 4 days and short once is not the same as somebody
		present 40 days and short once, and a count cannot tell them apart."""
		often = self.person("AAOften")
		rare = self.person("AARare")
		for i in range(1, 5):
			self.day(often, self.d(i), 7.0)
		for i in range(1, 5):
			self.day(rare, self.d(i), 9.0)
		self.day(rare, self.d(6), 7.0)

		rows = {r["employee"]: r for r in self.summary(view="organisation")["rows"]}
		self.assertEqual(rows[often]["short_rate"], 100.0)
		self.assertEqual(rows[rare]["short_rate"], 20.0)
		# And the worst is first, so nobody has to sort a list to find them.
		self.assertEqual(self.summary(view="organisation")["rows"][0]["employee"], often)

	def test_a_run_of_short_days_is_counted(self):
		"""A run of five is a life event; five scattered days are a habit."""
		p = self.person("AARun")
		for i in (2, 3, 4, 8):
			self.day(p, self.d(i), 7.0)
		self.assertEqual(self.summary(view="organisation")["rows"][0]["longest_run"], 3)

	def test_somebody_with_no_shift_is_not_judged(self):
		"""There is nothing to be short of, so inventing a shortfall would
		invent a problem."""
		p = self.person("AANoShift")
		frappe.db.set_value("Employee", p, "default_shift", None)
		a = frappe.get_doc({"doctype": "Attendance", "employee": p,
		                    "attendance_date": self.d(3),
		                    "status": "Present", "working_hours": 2.0,
		                    "company": self.company}).insert(ignore_permissions=True)
		a.submit()
		self._made.append(("Attendance", a.name))
		self.assertEqual(self.summary(view="organisation")["rows"][0]["short_days"], 0)


class TestTheBoundary(AnalyticsCase):
	def _become(self, employee):
		email = "%s.aa@example.com" % employee.lower()
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "AA",
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
			self._made.append(("User", email))
		frappe.db.set_value("Employee", employee, "user_id", email)
		frappe.set_user(email)
		return email

	def test_an_employee_cannot_ask_for_the_organisation(self):
		p = self.person("AAPlain")
		self._become(p)
		with self.assertRaises(frappe.PermissionError):
			aa.summary(view="organisation")

	def test_somebody_with_no_team_cannot_ask_for_one(self):
		p = self.person("AALoner")
		self._become(p)
		with self.assertRaises(frappe.PermissionError):
			aa.summary(view="team")

	def test_a_manager_gets_their_own_team(self):
		boss = self.person("AABoss")
		self.person("AAReport1", reports_to=boss)
		self.person("AAReport2", reports_to=boss)
		self._become(boss)
		self.assertEqual(aa.summary(view="team", date_from=self.d(19), date_to=self.d(0))["people"], 2)

	def test_deep_reaches_the_whole_line(self):
		boss = self.person("AAHead")
		mid = self.person("AAMid", reports_to=boss)
		self.person("AAJunior", reports_to=mid)
		self._become(boss)
		shallow = aa.summary(view="team", depth="direct",
		                     date_from=self.d(19), date_to=self.d(0))
		deep = aa.summary(view="team", depth="all",
		                  date_from=self.d(19), date_to=self.d(0))
		self.assertEqual(shallow["people"], 1)
		self.assertEqual(deep["people"], 2)

	def test_naming_somebody_elses_report_refuses_the_whole_request(self):
		"""Not a quiet subset. A silent trim teaches nobody where the boundary
		is and hides a permission bug for months."""
		boss = self.person("AAMgrA")
		mine = self.person("AAMine", reports_to=boss)
		other_boss = self.person("AAMgrB")
		theirs = self.person("AATheirs", reports_to=other_boss)
		self._become(boss)
		with self.assertRaises(frappe.PermissionError):
			aa.summary(view="team", people=[mine, theirs])

	def test_a_person_outside_the_line_cannot_be_opened(self):
		boss = self.person("AAMgrC")
		self.person("AAOwn", reports_to=boss)
		stranger = self.person("AAStranger")
		self._become(boss)
		with self.assertRaises(frappe.PermissionError):
			aa.person(stranger)

	def test_everybody_can_open_themselves(self):
		p = self.person("AASelf")
		self.day(p, self.d(3), 7.0)
		self._become(p)
		out = aa.person(p, date_from=self.d(19), date_to=self.d(0))
		self.assertEqual(out["employee"], p)
		self.assertTrue(any(d["short_by"] > 0 for d in out["days"]))


class TestPersonOrRota(AnalyticsCase):
	def test_one_bad_weekday_across_a_group_is_called_out(self):
		"""The most useful thing this screen does. A day that runs high across a
		whole group is a rota, not a group of people who all chose to leave."""
		people = [self.person("AAW%d" % i) for i in range(6)]
		# Six Mondays back, everybody short; other days fine.
		mondays, others = [], []
		for i in range(0, 20):
			day = self.d(i)
			(mondays if frappe.utils.getdate(day).weekday() == 0 else others).append(day)
		for p in people:
			for day in mondays[:3]:
				self.day(p, day, 6.0)
			for day in others[:6]:
				self.day(p, day, 9.0)

		v = self.summary(view="organisation")["weekday"]["verdict"]
		# Every other day here is clean, so the "worse than typical" comparison
		# has nothing to divide by. That must still be called out - it is the
		# clearest rota signal of all, not the weakest.
		self.assertIsNotNone(v, "a day this far out of line should be named")
		self.assertEqual(v["day"], "Monday")
		self.assertIn("rota", v["message"])

	def test_an_even_spread_says_nothing(self):
		"""Crying wolf on ordinary variation is how a screen gets ignored."""
		people = [self.person("AAE%d" % i) for i in range(4)]
		for p in people:
			for i in range(1, 15):
				self.day(p, self.d(i), 9.0 if i % 5 else 7.0)
		self.assertIsNone(self.summary(view="organisation")["weekday"]["verdict"])


class TestItSurvivesAThinTenant(AnalyticsCase):
	def test_no_attendance_at_all(self):
		self.person("AAEmpty")
		out = self.summary(view="organisation")
		self.assertEqual(out["headline"]["days_present"], 0)
		self.assertEqual(out["headline"]["short_rate"], 0.0)

	def test_the_views_a_person_gets_are_reported(self):
		out = aa.views()
		self.assertIn("mine", out)
		self.assertIn("team", out)
		self.assertIn("organisation", out)
		self.assertTrue(out["tolerance_mins"] > 0)
