"""ALV-440: the morning check tells HR, sees a half-dead feed, and is quiet on an off day.

The faults these prove, all three found on PRODUCTION (dtc.alvoraa.co) on
23 Nov 2026 while the Pitampura feed in ALV-439 was dead:

  * **D5 found it and told nobody.** Four findings for DTC Pitampura were Open
    from 16 to 23 Nov with no mail and no bell - the module had no notification
    code at all. `tell_hr_about` is the fix, and only for findings that are NEW.
  * **D5's 95% bar let five of nine outage days through.** Pitampura measured
    92.7, 92.2, 94.1, 94.2 and 94.2% absent on the days it missed. D20 judges a
    branch against its own normal for that weekday instead, so it caught the
    outage from 13 Nov rather than the 16th when replayed against real data.
  * **D5 flagged a correct day.** DTC Ambala 9 Nov (50 of 50 absent, 0 punched)
    was its weekly off. A false alarm beside the real ones is how the real ones
    stop being read.

One trap is worth its own test: at DTC the holiday list "Ambala Monday off" is
assigned to 1 employee of 63. A rule that skipped a day because SOME list held
it would let one mis-assigned record silence a whole branch's alarm for ever,
so `_holiday_branch_days` needs a majority - `test_a_minority_holiday_list_does_not_silence_a_branch`.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from alvoraa_portal import data_review as dr
from alvoraa_portal.tests import leader_fixtures_012 as fx
from alvoraa_portal.tests.test_data_review_012 import SETTINGS_MODULE, environment
from alvoraa_portal.tests.test_morning_checks_012 import AS_OF, no_commits

def _a_midweek_day():
	"""A Wednesday inside the 35-day window, with three earlier Wednesdays also
	inside it to make a baseline from.

	It must be a WEEKDAY, and that is not fussiness. These tests first used
	`today() - 8`, which fell on a Sunday, and the fixture company's holiday list
	marks Sundays as a weekly off - so once part C started reading holidays from
	Holiday List Assignment the way the product does, every branch-day was
	correctly skipped and three tests went quiet. Worth knowing: on a real tenant
	whose company list carries the weekly off, Sundays are now skipped
	everywhere, which is right and was not true before.
	"""
	d = getdate(add_days(today(), -5))
	while d.weekday() != 2:                   # Wednesday
		d = getdate(add_days(d, -1))
	return d


DAY = _a_midweek_day()
BACK = [getdate(add_days(DAY, -7 * w)) for w in (1, 2, 3)]
# A second Wednesday, for the one test that assigns a holiday list to the whole
# COMPANY. Records in this module do not roll back between tests - the fixtures
# write straight to the table - so a company-level assignment covering DAY
# silently made every later test's branch look shut, and three of them went
# quiet for the wrong reason. It gets its own day and clears up after itself.
OTHER_DAY = getdate(add_days(DAY, -7))
OTHER_BACK = [getdate(add_days(OTHER_DAY, -7 * w)) for w in (1, 2, 3)]


def setUpModule():
	fx.setup_module_fixtures()


class FeedCase(FrappeTestCase):
	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user(self.caller)

	# ── building a branch's week ──────────────────────────────────────────────

	def people(self, branch, n, company=fx.KAVYA):
		return [fx.employee(f"PF{i}", company, branch, fast=True) for i in range(n)]

	def punched_on(self, people, branch, days, how_many=None):
		"""Check-ins for the first `how_many` people on each of these days."""
		for day in days:
			for emp in people[:how_many if how_many is not None else len(people)]:
				fx.checkin(emp, branch, f"{getdate(day)} 09:30:00")

	def marked_on(self, people, branch, day, absent=0, company=fx.KAVYA):
		for i, emp in enumerate(people):
			fx.attendance(emp, company, branch, day, "Absent" if i < absent else "Present")

	def hr_manager(self, local, company=fx.KAVYA):
		"""A company-wide HR Manager. They need an Employee record: `hr_scope`
		fails closed, so a user with no company has no scope and is told nothing
		- which is correct, and worth saying in a helper rather than per test."""
		email = fx.user(local, ["HR Manager"])
		fx.employee(local, company, None, user_id=email)
		return email

	def feed(self, company=fx.KAVYA, minimum=5, as_of=AS_OF):
		return dr._punch_feed(company, minimum, as_of,
		                      holidays=dr._holiday_branch_days(
		                          company, add_days(as_of, -120), as_of))

	def feed_for(self, branch, **kw):
		return [f for f in self.feed(**kw).values() if f["alvoraa_branch"] == branch]

	def doubtful_for(self, branch, company=fx.KAVYA, minimum=5, as_of=AS_OF, holidays=None):
		"""D5's findings for one branch. Scoped on purpose: every test in this
		module shares one company, so a company-wide count reads the branches
		the other tests built as well."""
		if holidays is None:
			holidays = dr._holiday_branch_days(company, add_days(as_of, -120), as_of)
		return [f for f in dr._doubtful_days(company, minimum, as_of, holidays=holidays).values()
		        if f["alvoraa_branch"] == branch]


class TestTheFeedStopping(FeedCase):
	def test_a_branch_that_stops_punching_is_found(self):
		"""The rule ALV-439 needed: normal on this weekday, then nothing."""
		b = fx.branch("FeedDead")
		crew = self.people(b, 10)
		self.punched_on(crew, b, BACK)            # ten people, three Wednesdays running
		self.marked_on(crew, b, DAY, absent=10)   # then the day itself, nobody punched
		found = self.feed_for(b)
		self.assertEqual(len(found), 1)
		self.assertEqual(found[0]["rule"], "D20")
		self.assertEqual(found[0]["item_type"], "Punch feed")
		self.assertEqual(found[0]["checked_in_count"], 0)
		self.assertEqual(found[0]["people_count"], 10)      # what normal is
		self.assertEqual(getdate(found[0]["check_date"]), DAY)

	def test_a_day_d5_cannot_see_is_still_caught(self):
		"""The five Pitampura days that measured 92-94% absent against a 95% bar.

		Twelve people expected, eleven absent = 91.7%, so D5 says nothing. One
		of twelve punching where twelve normally do is 8% of normal, so D20 does.
		"""
		b = fx.branch("FeedNinetyTwo")
		crew = self.people(b, 12)
		self.punched_on(crew, b, BACK)
		self.marked_on(crew, b, DAY, absent=11)
		self.punched_on(crew, b, [DAY], how_many=1)

		self.assertEqual(self.doubtful_for(b), [],
		                 "a 91.7% day is under D5's bar - that is the point of this test")
		found = self.feed_for(b)
		self.assertEqual(len(found), 1)
		self.assertEqual(found[0]["checked_in_count"], 1)

	def test_it_clears_once_the_branch_punches_again(self):
		"""apply_findings marks a finding that stops firing Cleared, never deletes it."""
		b = fx.branch("FeedBack")
		crew = self.people(b, 10)
		self.punched_on(crew, b, BACK)
		self.marked_on(crew, b, DAY, absent=10)
		rules = ("D20",)
		with no_commits():
			dr.apply_findings(dr.existing_items(fx.KAVYA, AS_OF, rules=rules),
			                  dr.company_findings(fx.KAVYA, 5, AS_OF, rules=rules),
			                  allow_create=True)
		name = dr.item_name("D20", fx.KAVYA, b, DAY)
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Open")

		self.punched_on(crew, b, [DAY])           # the device is fixed, the day back-filled
		with no_commits():
			dr.apply_findings(dr.existing_items(fx.KAVYA, AS_OF, rules=rules),
			                  dr.company_findings(fx.KAVYA, 5, AS_OF, rules=rules),
			                  allow_create=True)
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Cleared")

	def test_a_drop_that_is_not_steep_enough_says_nothing(self):
		"""FEED_DROP_PCT is a floor, not a hint: 40% of normal is still normal."""
		b = fx.branch("FeedHalf")
		crew = self.people(b, 10)
		self.punched_on(crew, b, BACK)
		self.marked_on(crew, b, DAY, absent=6)
		self.punched_on(crew, b, [DAY], how_many=4)        # 40% of 10
		self.assertEqual(self.feed_for(b), [])

		b2 = fx.branch("FeedJustUnder")
		crew2 = self.people(b2, 10)
		self.punched_on(crew2, b2, BACK)
		self.marked_on(crew2, b2, DAY, absent=7)
		self.punched_on(crew2, b2, [DAY], how_many=3)      # 30% of 10
		self.assertEqual(len(self.feed_for(b2)), 1)


class TestTheWeeklyOff(FeedCase):
	"""The Ambala fault: a branch shut on this weekday must not be an alarm."""

	def test_a_branch_shut_every_same_weekday_is_never_judged(self):
		"""No same-weekday ever punched, so there is no normal and no finding.

		This is what makes the rule right without any holiday list - which
		matters, because at DTC the Monday list reaches 1 employee of 63.
		"""
		b = fx.branch("FeedMondayOff")
		crew = self.people(b, 10)
		# Busy on the days in between, shut on every same weekday as DAY.
		self.punched_on(crew, b, [add_days(d, 2) for d in BACK])
		self.marked_on(crew, b, DAY, absent=10)
		self.assertEqual(self.feed_for(b), [])

	def test_too_little_history_says_nothing(self):
		"""FEED_MIN_SAMPLES: a new branch is not judged before it has a normal."""
		b = fx.branch("FeedNew")
		crew = self.people(b, 10)
		self.punched_on(crew, b, BACK[:2])        # only two same-weekdays
		self.marked_on(crew, b, DAY, absent=10)
		self.assertEqual(self.feed_for(b), [])

	def test_a_branch_quieter_than_the_minimum_group_is_not_judged(self):
		"""PRIV-10: a finding never describes a group too small to be anonymous."""
		b = fx.branch("FeedTiny")
		crew = self.people(b, 4)
		self.punched_on(crew, b, BACK)
		self.marked_on(crew, b, DAY, absent=4)
		self.assertEqual(self.feed_for(b), [])

		big = fx.branch("FeedBigEnough")
		crew2 = self.people(big, 20)
		self.punched_on(crew2, big, BACK)
		self.marked_on(crew2, big, DAY, absent=20)
		self.assertEqual(len(self.feed_for(big)), 1)
		# ...and the tenant's own larger minimum wins over the constant.
		self.assertEqual(self.feed_for(big, minimum=25), [])


class TestHolidays(FeedCase):
	"""Part C: a festival the whole branch shares is not a fault.

	**These tests assign a holiday list the way the product does** - a submitted
	Holiday List Assignment - and never by writing `Employee.holiday_list`. An
	earlier version of them wrote that column, which nothing has maintained since
	hrms v16; they passed, and the code they covered was blind on every real
	tenant. On DTC the column said 1 of 63 Ambala people were on the Monday-off
	list while the assignments said 62 were.
	"""

	def assign(self, who, holiday_list, applicable_for="Employee", since=None):
		"""A submitted Holiday List Assignment - what
		hrms.utils.holiday_list.get_assigned_holiday_list actually reads.

		`applicable_for` is the doctype of `assigned_to`, which is a Dynamic
		Link: "Employee" or "Company"."""
		doc = frappe.get_doc({
			"doctype": "Holiday List Assignment", "applicable_for": applicable_for,
			"assigned_to": who, "holiday_list": holiday_list,
			"from_date": getdate(since or add_days(today(), -120)),
		})
		doc.insert(ignore_permissions=True)
		doc.submit()
		return doc.name

	def holiday_list(self, name, days):
		doc = frappe.get_doc({
			"doctype": "Holiday List", "holiday_list_name": fx.unique(name),
			"from_date": add_days(today(), -200), "to_date": add_days(today(), 200),
			"holidays": [{"holiday_date": getdate(d), "description": "shut"} for d in days],
		})
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_a_shared_holiday_is_not_a_dead_feed(self):
		b = fx.branch("FeedFestival")
		crew = self.people(b, 10)
		self.punched_on(crew, b, BACK)
		self.marked_on(crew, b, DAY, absent=10)
		shut = self.holiday_list("Festival", [DAY])
		for emp in crew:
			self.assign(emp, shut)
		self.assertEqual(self.feed_for(b), [])

	def test_a_shared_holiday_is_not_a_doubtful_day_either(self):
		"""The same skip on D5, which is what flagged Ambala's 9 Nov."""
		b = fx.branch("FeedFestD5")
		crew = self.people(b, 10)
		self.marked_on(crew, b, DAY, absent=10)
		self.assertEqual(len(self.doubtful_for(b)), 1)

		shut = self.holiday_list("FestD5", [DAY])
		for emp in crew:
			self.assign(emp, shut)
		self.assertEqual(self.doubtful_for(b), [])

	def test_a_minority_holiday_list_does_not_silence_a_branch(self):
		"""The DTC trap: "Ambala Monday off" is on 1 employee of 63.

		One mis-assigned record must not be able to switch off a whole branch's
		alarm, so the day counts as the branch's holiday only above half.
		"""
		b = fx.branch("FeedOneAssigned")
		crew = self.people(b, 10)
		self.punched_on(crew, b, BACK)
		self.marked_on(crew, b, DAY, absent=10)
		shut = self.holiday_list("MinorityOff", [DAY])
		self.assign(crew[0], shut)
		self.assertEqual(len(self.feed_for(b)), 1,
		                 "one employee's holiday list must not silence ten people's branch")

	def test_the_legacy_employee_column_is_ignored(self):
		"""The DTC fault itself. `Employee.holiday_list` is the pre-v16 column and
		nothing maintains it; a branch must NOT be silenced by it alone."""
		b = fx.branch("FeedStaleColumn")
		crew = self.people(b, 10)
		self.punched_on(crew, b, BACK)
		self.marked_on(crew, b, DAY, absent=10)
		shut = self.holiday_list("StaleOff", [DAY])
		for emp in crew:
			frappe.db.set_value("Employee", emp, "holiday_list", shut, update_modified=False)
		self.assertEqual(len(self.feed_for(b)), 1,
		                 "the stale column must not decide whether a branch is shut")

	def test_a_company_wide_assignment_counts(self):
		"""get_holiday_list_for_employee falls back to the company's assignment,
		so this must too - otherwise a tenant that assigns at company level only
		(which DTC does, from 1 Apr 2026) gets no holiday skip at all.

		On its own day, and it deletes its assignment afterwards: a company-level
		one reaches every branch in the company, including the ones other tests
		in this module built.
		"""
		b = fx.branch("FeedCoWide")
		crew = self.people(b, 10)
		self.punched_on(crew, b, OTHER_BACK)
		self.marked_on(crew, b, OTHER_DAY, absent=10)
		shut = self.holiday_list("CoWideOff", [OTHER_DAY])
		hla = self.assign(fx.KAVYA, shut, applicable_for="Company")
		try:
			found = [f for f in self.feed(as_of=AS_OF).values()
			         if f["alvoraa_branch"] == b and getdate(f["check_date"]) == OTHER_DAY]
			self.assertEqual(found, [],
			                 "a company-level holiday assignment applies to its branches")
		finally:
			frappe.db.delete("Holiday List Assignment", {"name": hla})


class TestTellingHR(FeedCase):
	"""Part A: the fault that made the other two worth fixing."""

	@staticmethod
	def mails(mock):
		"""(users, subject, body) of every queued Notification Log call."""
		return [(kw["users"], kw["doc"]["subject"], kw["doc"]["email_content"])
		        for _a, kw in mock.call_args_list]

	def a_dead_feed(self, prefix="Tell"):
		b = fx.branch(prefix)
		crew = self.people(b, 10)
		self.punched_on(crew, b, BACK)
		self.marked_on(crew, b, DAY, absent=10)
		return b, crew

	def run_job(self, rules=("D20",), created=None):
		created = [] if created is None else created
		with no_commits():
			dr.apply_findings(dr.existing_items(fx.KAVYA, AS_OF, rules=rules),
			                  dr.company_findings(fx.KAVYA, 5, AS_OF, rules=rules),
			                  allow_create=True, created=created)
		return created

	def test_a_new_finding_mails_every_hr_manager(self):
		b, _crew = self.a_dead_feed("TellNew")
		boss = self.hr_manager("Hrm440")
		created = self.run_job()
		self.assertTrue(created)
		with patch.object(dr, "_queue") as q:
			dr.tell_hr_about(created)
		addressed = [call.args[0] for call in q.call_args_list]
		self.assertIn(boss, addressed)
		subject = [call.args[1] for call in q.call_args_list if call.args[0] == boss][0]
		self.assertIn(b, subject, "the branch whose feed died leads the subject")
		self.assertIn("punches", subject)

	def test_only_new_findings_are_mailed(self):
		"""No daily "all clear": a mail that always arrives is filtered, and then
		so is the one that mattered."""
		self.a_dead_feed("TellAgain")
		first = self.run_job()
		self.assertTrue(first)
		second = self.run_job()
		self.assertEqual(second, [], "a second run creates nothing, so there is nothing to say")

	def test_the_mail_never_names_a_person(self):
		"""SEC-13 / AC-36: counts, dates and place names only."""
		b, crew = self.a_dead_feed("TellQuiet")
		self.hr_manager("Hrm440b")
		created = self.run_job()
		with patch.object(dr, "_queue") as q:
			dr.tell_hr_about(created)
		bodies = " ".join(call.args[2] for call in q.call_args_list)
		subjects = " ".join(call.args[1] for call in q.call_args_list)
		self.assertTrue(q.call_args_list, "somebody must have been mailed for this to prove anything")
		for emp in crew:
			name = frappe.db.get_value("Employee", emp, "employee_name")
			self.assertNotIn(emp, bodies + subjects)
			self.assertNotIn(name, bodies + subjects)
		self.assertIn(b, bodies)

	def test_a_mail_that_cannot_be_sent_never_undoes_the_findings(self):
		"""It runs after the commit; the findings must stand (as AC-122 does for joins)."""
		self.a_dead_feed("TellBroken")
		self.hr_manager("Hrm440d")   # somebody has to be mailed for this to prove anything
		created = self.run_job()
		name = created[0]
		with patch.object(dr, "_queue", side_effect=RuntimeError("redis is down")), \
		     patch.object(frappe, "log_error") as logged:
			dr.tell_hr_about(created)          # must not raise
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Open")
		self.assertTrue(logged.called)
		# Every call, not just the last: the only recipient failing logs the error
		# AND then "nobody to tell", which is the behaviour we want.
		said = str(logged.call_args_list)
		self.assertIn("RuntimeError", said)
		self.assertIn("nobody to tell", said)
		self.assertNotIn("redis is down", said, "the type only - a traceback's values hold counts")

	def test_the_job_tells_hr_at_the_end(self):
		"""Wiring: run_morning_checks must actually call it, after its commits."""
		self.a_dead_feed("TellWired")
		self.hr_manager("Hrm440c")
		with no_commits(), patch("alvoraa_portal.subscription.has_feature", return_value=True), \
		     patch(f"{SETTINGS_MODULE}.min_group_size", return_value=5), \
		     patch.object(dr, "tell_hr_about") as told:
			dr.run_morning_checks([fx.KAVYA])
		self.assertTrue(told.called, "a finding nobody is told about is not an alarm")
		self.assertTrue(told.call_args[0][0], "and it must be told which findings are new")


class TestWhoIsTold(FeedCase):
	"""The rule that broke. It had no test, which is why it broke.

	The first version filtered each recipient's findings with
	`frappe.has_permission(DOCTYPE, "read", doc=<name>, user=...)`. That answers
	True for every branch and every company here, because a tenant's Branch User
	Permission rows carry `applicable_for = "Employee"` and Frappe keeps a row
	only when `applicable_for` is empty or equals the doctype under test - so the
	allowed list comes back empty and the check is skipped entirely. A store HR
	Manager would have been told another branch's and another company's counts.
	"""

	def dead_branch(self, prefix, company=fx.KAVYA):
		b = fx.branch(prefix)
		crew = self.people(b, 10, company=company)
		self.punched_on(crew, b, BACK)
		for i, emp in enumerate(crew):
			fx.attendance(emp, company, b, DAY, "Absent")
		return b

	def store_hr(self, local, branch, company=fx.KAVYA):
		"""An HR Manager restricted to one branch, the way a tenant really does it:
		a User Permission on Branch with applicable_for = "Employee"."""
		email = fx.user(local, ["HR Manager"])
		fx.employee(local, company, branch, user_id=email)
		fx.permission(email, "Company", company, applicable_for="Employee")
		fx.permission(email, "Branch", branch, applicable_for="Employee")
		return email

	def words_sent_to(self, user, created):
		with patch.object(dr, "_queue") as q:
			dr.tell_hr_about(created)
		for call in q.call_args_list:
			if call.args[0] == frappe.db.get_value("User", user, "email"):
				return call.args[1] + " " + call.args[2]
		return None

	def test_branch_hr_is_never_told_another_branch(self):
		mine = self.dead_branch("ToldMine")
		theirs = self.dead_branch("ToldTheirs")
		boss = self.store_hr("Store440", mine)
		created = []
		rules = ("D20",)
		with no_commits():
			dr.apply_findings(dr.existing_items(fx.KAVYA, AS_OF, rules=rules),
			                  dr.company_findings(fx.KAVYA, 5, AS_OF, rules=rules),
			                  allow_create=True, created=created)
		said = self.words_sent_to(boss, created)
		self.assertIsNotNone(said, "branch HR must still be told about their own branch")
		self.assertIn(mine, said)
		self.assertNotIn(theirs, said, "another branch's counts must never reach branch HR")

	def test_branch_hr_is_never_told_another_company(self):
		mine = self.dead_branch("ToldCoMine")
		elsewhere = self.dead_branch("ToldCoOther", company=fx.OTHER)
		boss = self.store_hr("StoreCo440", mine)
		created = []
		for company in (fx.KAVYA, fx.OTHER):
			rules = ("D20",)
			with no_commits():
				dr.apply_findings(dr.existing_items(company, AS_OF, rules=rules),
				                  dr.company_findings(company, 5, AS_OF, rules=rules),
				                  allow_create=True, created=created)
		said = self.words_sent_to(boss, created)
		self.assertIsNotNone(said)
		self.assertNotIn(elsewhere, said, "another company's counts must never reach branch HR")
		self.assertNotIn(fx.OTHER, said)

	def test_branch_hr_is_never_told_a_company_wide_finding(self):
		"""A finding with no branch is company-wide. Frappe's own User Permissions
		let a record with an EMPTY link field through, which is why the page draws
		this line explicitly - and so must the mail."""
		mine = self.dead_branch("ToldWide")
		boss = self.store_hr("StoreWide440", mine)
		wide = fx.review_item(fx.KAVYA, None, rule="D18-2", item_type="Leavers")
		said = self.words_sent_to(boss, [wide])
		self.assertIsNone(said, "location HR is never told a company-wide figure")

	def test_an_unrestricted_hr_manager_is_told_everything(self):
		"""The other half: scoping must not silence company-wide HR."""
		a = self.dead_branch("WideA")
		b = self.dead_branch("WideB")
		boss = self.hr_manager("Wide440")
		created = []
		rules = ("D20",)
		with no_commits():
			dr.apply_findings(dr.existing_items(fx.KAVYA, AS_OF, rules=rules),
			                  dr.company_findings(fx.KAVYA, 5, AS_OF, rules=rules),
			                  allow_create=True, created=created)
		said = self.words_sent_to(boss, created)
		self.assertIsNotNone(said)
		self.assertIn(a, said)
		self.assertIn(b, said)

	def test_one_bad_recipient_does_not_silence_the_others(self):
		"""The guard is inside the loop. Outside it, one failure skipped every
		later HR Manager and returned as though it had worked."""
		self.dead_branch("BadFirst")
		for n in ("Bad440a", "Bad440b", "Bad440c"):
			self.hr_manager(n)
		created = []
		rules = ("D20",)
		with no_commits():
			dr.apply_findings(dr.existing_items(fx.KAVYA, AS_OF, rules=rules),
			                  dr.company_findings(fx.KAVYA, 5, AS_OF, rules=rules),
			                  allow_create=True, created=created)
		calls = {"n": 0}

		def flaky(email, subject, body, name):
			calls["n"] += 1
			if calls["n"] == 1:
				raise RuntimeError("this one is broken")

		with patch.object(dr, "_queue", side_effect=flaky), patch.object(frappe, "log_error"):
			dr.tell_hr_about(created)
		self.assertGreater(calls["n"], 1, "the recipients after the broken one must still be tried")

	def test_nothing_sent_is_logged(self):
		"""A silent nought is the failure mode that let ALV-439 run for a week."""
		self.dead_branch("NoOne")
		created = []
		rules = ("D20",)
		with no_commits():
			dr.apply_findings(dr.existing_items(fx.KAVYA, AS_OF, rules=rules),
			                  dr.company_findings(fx.KAVYA, 5, AS_OF, rules=rules),
			                  allow_create=True, created=created)
		self.assertTrue(created)
		with patch.object(dr, "_hr_managers", return_value=[]), \
		     patch.object(frappe, "log_error") as logged:
			dr.tell_hr_about(created)
		self.assertTrue(logged.called, "nothing went out and nothing said so")
		self.assertIn("nobody to tell", str(logged.call_args))


class TestItActuallyEmails(FeedCase):
	"""A Notification Log of type "Alert" never emails anybody: "Alert" is in
	Frappe's `notification_skip_email_types`, so the gate returns False before it
	reads the person's own settings. One commit of this module believed otherwise
	and would have shipped an alarm that reached only HR Managers who open Desk.
	"""

	def test_a_real_email_goes_out_when_email_is_on(self):
		with patch("alvoraa_portal.announcements.email_is_active", return_value=True), \
		     patch.object(frappe, "sendmail") as mail, patch.object(frappe, "enqueue"):
			dr._queue("someone@example.com", "subject", "<p>body</p>", "DRI-x")
		self.assertTrue(mail.called, "the bell alone never emails - Alert is skipped by Frappe")
		self.assertEqual(mail.call_args.kwargs["recipients"], ["someone@example.com"])

	def test_no_email_when_the_tenant_has_email_off(self):
		"""Every production site is muted today, so the bell is all there is."""
		with patch("alvoraa_portal.announcements.email_is_active", return_value=False), \
		     patch.object(frappe, "sendmail") as mail, patch.object(frappe, "enqueue") as bell:
			dr._queue("someone@example.com", "subject", "<p>body</p>", "DRI-x")
		self.assertFalse(mail.called)
		self.assertTrue(bell.called, "the desk bell still goes")


class TestTheRecordsStayPrivate(FeedCase):
	def test_a_punch_feed_finding_holds_no_employee(self):
		b = fx.branch("FeedPriv")
		crew = self.people(b, 10)
		self.punched_on(crew, b, BACK)
		self.marked_on(crew, b, DAY, absent=10)
		found = self.feed_for(b)
		self.assertEqual(len(found), 1)
		values = " ".join(str(v) for v in found[0].values())
		for emp in crew:
			self.assertNotIn(emp, values)
