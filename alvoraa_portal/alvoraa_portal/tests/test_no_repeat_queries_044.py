"""Slice 044 R1 and R4: Home must not ask the same question twice, and a scope
must not be shipped to the database as a list of names.

Slice 044 measured Wave 2's landing calls on a 981-person tenant and found two
things the query count alone could never have shown.

**R1 - the same question, four or five times in one call.** `get_home` asked
the database for the caller's holiday-list assignment twice, their company
twice, their direct reports two or three times, and for an HR caller the whole
permitted-employee list twice. Same statement, same parameters, same call.
Nothing inside `get_home` writes, so nothing could have changed between them.
`test_get_home_asks_no_question_twice` fails on the old code with four to five
exact repeats and passes on the new one with none.

**R4 - a scope as 981 parameters.** `goals_api._pending_approvals_scope` read
every permitted employee id into Python and each reader shipped the whole list
back inside an `IN (...)`. One statement, so the query count stayed flat and
nothing looked wrong - but the statement grew with the company, and it was the
widest slope in the measurement. `test_the_scope_is_not_shipped_back_as_a_list`
grows the team from four people to thirty and asserts the SQL the Inbox sends
does not grow with it.

**The memo is the other half of R1, and it is a permission rule.**
`call_cache` remembers an answer for the next line of the same function and
throws it away in a `finally`. Four tests here exist only to prove it cannot
outlive the call: one after a normal return, one after an exception, one that
asserts a second `get_home` costs exactly what the first did, and one that
proves nothing is memoised at all outside a call.

A scope remembered across requests would mean an HR person removed from a
company at 10:00 kept seeing it, which is why this is tested rather than
described.
"""

import json
from collections import Counter

import frappe

from alvoraa_portal import call_cache, home_api, inbox_api
from alvoraa_portal.tests.test_scale_flatness_044 import (
	GROWN_TEAM,
	SMALL_TEAM,
	_Flatness,
)


class _ParamSpy:
	"""Every statement run inside the block, WITH its parameters.

	The parameters are the point. Slice 044's first count called three
	`tabDocType` existence checks "repeats" because the SQL text matched; they
	ask about three different doctypes and are three different questions. A
	repeat is the same statement with the same values, and nothing else.
	"""

	def __init__(self):
		self.seen = []

	def __enter__(self):
		self._real = frappe.db.sql

		def spy(query, values=(), *args, **kwargs):
			self.seen.append((" ".join(str(query).split()),
			                  json.dumps(values, default=str, sort_keys=True)))
			return self._real(query, values, *args, **kwargs)

		frappe.db.sql = spy
		return self

	def __exit__(self, *exc):
		frappe.db.sql = self._real
		return False

	def repeats(self):
		return {k: n for k, n in Counter(self.seen).items() if n > 1}

	def report(self):
		return "\n".join(
			"  x%d  %s\n        params=%s" % (n, q[:160], v[:120])
			for (q, v), n in sorted(self.repeats().items(), key=lambda kv: -kv[1]))


class TestHomeAsksEachQuestionOnce(_Flatness):
	"""044 R1 / D2. Measured, not read."""

	def setUp(self):
		super().setUp()
		self._hire(SMALL_TEAM)

	def tearDown(self):
		frappe.set_user("Administrator")
		self._fire()
		super().tearDown()

	def _repeats_for(self, login):
		frappe.set_user(login)
		frappe.local.request_ip = "127.0.0.1"
		for _ in range(3):        # warm, so a cache miss is not read as a repeat
			home_api.get_home()
		with _ParamSpy() as spy:
			home_api.get_home()
		frappe.set_user("Administrator")
		return spy

	def test_get_home_asks_no_question_twice(self):
		"""The assertion 044 R1 exists for, for all three personas."""
		for login in (self.emp_login, self.mgr_login, self.hr_login):
			spy = self._repeats_for(login)
			self.assertEqual(
				spy.repeats(), {},
				"get_home asked the same question more than once for %s:\n%s"
				% (login, spy.report()))

	def test_the_spy_can_see_a_repeat_when_there_is_one(self):
		"""The guard's guard. An assertion that finds nothing is worthless
		unless it would have found something."""
		frappe.set_user(self.mgr_login)
		with _ParamSpy() as spy:
			for _ in range(2):
				frappe.get_all("Employee",
				               filters={"reports_to": self.mgr, "status": "Active"},
				               pluck="name")
		frappe.set_user("Administrator")
		self.assertTrue(spy.repeats(),
		                "the spy did not notice the same query run twice")


class TestTheMemoDiesWithTheCall(_Flatness):
	"""044 R1, the half that is a permission rule and not a performance one."""

	def tearDown(self):
		frappe.set_user("Administrator")
		call_cache.close_cache()
		self._fire()
		super().tearDown()

	def test_nothing_is_open_after_a_normal_return(self):
		frappe.set_user(self.emp_login)
		home_api.get_home()
		frappe.set_user("Administrator")
		self.assertFalse(call_cache.is_open())

	def test_nothing_is_open_after_the_call_raises(self):
		"""A memo left open by an exception would be read by the next call in
		the same worker - which is the stale-scope bug, arriving by accident."""
		real = home_api._me

		def boom(_user):
			raise RuntimeError("S044 deliberate failure")

		frappe.set_user(self.emp_login)
		home_api._me = boom
		try:
			with self.assertRaises(RuntimeError):
				home_api.get_home()
		finally:
			home_api._me = real
			frappe.set_user("Administrator")
		self.assertFalse(call_cache.is_open(),
		                 "the memo survived an exception inside get_home")

	def test_a_second_call_costs_exactly_what_the_first_did(self):
		"""Nothing is remembered between two calls. If the memo were a cache the
		second reading would be cheaper, and every flatness measurement in this
		slice would be measuring the cache rather than the code."""
		self._hire(SMALL_TEAM)
		frappe.set_user(self.mgr_login)
		frappe.local.request_ip = "127.0.0.1"
		for _ in range(3):
			home_api.get_home()
		with _ParamSpy() as first:
			home_api.get_home()
		with _ParamSpy() as second:
			home_api.get_home()
		frappe.set_user("Administrator")
		self.assertEqual(len(first.seen), len(second.seen),
		                 "the second get_home ran %d statements against the "
		                 "first's %d - something outlived the call"
		                 % (len(second.seen), len(first.seen)))

	def test_outside_a_call_there_is_no_memo_at_all(self):
		"""`hr_api._own_upcoming_holidays` is shared. With no call open it must
		behave exactly as it did before, so every other caller is untouched."""
		self.assertFalse(call_cache.is_open())
		calls = []
		self.assertEqual(call_cache.once("k", lambda: calls.append(1) or 1), 1)
		self.assertEqual(call_cache.once("k", lambda: calls.append(2) or 2), 2)
		self.assertEqual(len(calls), 2, "something memoised outside a call")


class TestTheTeamCardCountsEverybody(_Flatness):
	"""044 D6. The cap that quietly stopped counting at a thousand people."""

	def setUp(self):
		super().setUp()
		self._cap = home_api.LIST_CAP

	def tearDown(self):
		frappe.set_user("Administrator")
		home_api.LIST_CAP = self._cap
		self._fire()
		super().tearDown()

	def test_no_list_cap_is_applied_to_the_presence_numbers(self):
		"""The old card counted `names[:LIST_CAP * 20]` and then applied the
		minimum-group rule to `len(names)`, so above a thousand people it drew
		the first thousand's numbers as if they were the tenant's.

		A 1,001-person fixture takes half an hour to build, so the cap is made
		to bite instead: with `LIST_CAP` at zero the old code counted nobody and
		the new code, which does not read the constant at all, still counts
		everybody. Same defect, one second instead of half an hour.
		"""
		team = self._hire(GROWN_TEAM)
		self.assertGreater(team, 10, "nobody was hired, so this proves nothing")
		home_api.LIST_CAP = 0
		frappe.set_user(self.mgr_login)
		frappe.local.request_ip = "127.0.0.1"
		card = home_api.get_home()["team_today"]
		frappe.set_user("Administrator")
		self.assertEqual(card["basis"], "team")
		counted = sum(card[k] or 0 for k in ("in", "away", "due"))
		self.assertEqual(
			counted, team,
			"the team card counted %d of the manager's %d reports"
			% (counted, team))


class TestTheApprovalScopeStaysInTheDatabase(_Flatness):
	"""044 R4 / D5."""

	def tearDown(self):
		frappe.set_user("Administrator")
		self._fire()
		super().tearDown()

	def _old_rule(self, emp_id, is_hr):
		"""The rule as slice 042 wrote it, in Python, so the new query has
		something independent to agree with."""
		if is_hr:
			from hrms.alvoraa_hr_core.access import permitted_companies

			return sorted(set(frappe.get_all(
				"Employee",
				filters={"status": "Active", "name": ["!=", emp_id],
				         "company": ["in", permitted_companies() or [""]]},
				pluck="name")) | set(frappe.get_all(
					"Employee",
					filters={"reports_to": emp_id, "status": "Active"},
					pluck="name") if emp_id else []))
		return sorted(frappe.get_all(
			"Employee", filters={"reports_to": emp_id, "status": "Active"},
			pluck="name"))

	def test_the_subquery_scope_matches_the_list_scope_exactly(self):
		"""The push-down changed where the rule runs, not what it decides."""
		from alvoraa_portal.goals_api import _pending_approvals_scope

		self._hire(GROWN_TEAM)
		for login, emp, is_hr in ((self.mgr_login, self.mgr, False),
		                          (self.hr_login, self.hr, True),
		                          (self.emp_login, self.emp, False)):
			frappe.set_user(login)
			got = sorted(_pending_approvals_scope(emp, is_hr))
			want = self._old_rule(emp, is_hr)
			frappe.set_user("Administrator")
			self.assertEqual(got, want,
			                 "%s: the subquery and the old list disagree about "
			                 "who may be approved for" % login)

	def test_nobody_is_in_scope_for_a_caller_with_no_employee_record(self):
		"""Fail closed. `name IN ()` matches nothing; an empty condition would
		match everything (SEC-4)."""
		from alvoraa_portal.goals_api import _pending_approvals_scope

		self.assertEqual(_pending_approvals_scope(None, True), [])
		self.assertEqual(_pending_approvals_scope(None, False), [])

	def test_the_caller_is_never_in_their_own_approval_scope(self):
		"""042 AC-25."""
		from alvoraa_portal.goals_api import _pending_approvals_scope

		self._hire(GROWN_TEAM)
		frappe.set_user(self.hr_login)
		scope = _pending_approvals_scope(self.hr, True)
		frappe.set_user("Administrator")
		self.assertTrue(scope, "the HR scope is empty, so this proves nothing")
		self.assertNotIn(self.hr, scope)

	def test_the_scope_is_not_shipped_back_as_a_list(self):
		"""**The R4 assertion.** The SQL the Inbox sends must be the same for
		four people as for thirty.

		The old code put one bound value per permitted employee into every
		`IN (...)`, so the statement grew with the company even though the
		number of statements did not. This measures the statement.
		"""
		self._fire()
		small_team = self._hire(SMALL_TEAM)
		small = self._scope_sql(self.hr_login)

		grown_team = self._hire(GROWN_TEAM)
		self.assertGreater(grown_team, small_team + 10,
		                   "the team went from %d to %d, so growing it proved "
		                   "nothing" % (small_team, grown_team))
		grown = self._scope_sql(self.hr_login)

		self.assertEqual(
			grown, small,
			"the goal-updates part sent %d characters of SQL for %d people and "
			"%d for %d - the scope is travelling to the database as data"
			% (len(small), small_team, len(grown), grown_team))

	def _scope_sql(self, login):
		"""The goal-updates part's counting SQL, as text, warm."""
		frappe.set_user(login)
		frappe.local.request_ip = "127.0.0.1"
		for _ in range(3):
			inbox_api.get_nav_counts()
		with _ParamSpy() as spy:
			built, _hr = inbox_api.parts()
			part = [p for p in built if p.key == "goal_updates"][0]
			part.count()
		frappe.set_user("Administrator")
		sql = [q for q, _v in spy.seen
		       if "tabIndividual Goal" in q or "tabKPI" in q]
		self.assertTrue(sql, "the goal-updates part ran no query at all")
		return "\n".join(sorted(sql))
