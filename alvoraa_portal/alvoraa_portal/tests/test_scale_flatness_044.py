"""Slice 044: the portal's landing calls must not get more expensive as the
company hires.

**What this file is for.** Wave 1 moved `get_nav_counts`'s budget from 15
queries to 20 rather than pretend, and said in writing why that was the right
call: *the property the budget exists to protect is that the call is flat in
headcount.* A magic number is a proxy. Flatness is the thing. So this file
asserts the thing.

**The shape, borrowed from Wave 2 and kept.** Measure, grow the data, measure
again in the same state, and assert the count did not grow - with a guard that
refuses to pass unless the data really did grow. Wave 2's version grew the
number of *rows*; this one grows the number of *people*, which is the axis the
16.4-second bell blew up on.

**Two traps this file is built around, both already paid for:**

1. *Steady state.* Wave 2's first measurement reported 14 against 17 and the
   method was wrong, not the code: it inserted between the two readings, and
   inserting clears caches, so it compared a warm call with a cold one. Every
   measurement here is taken after three warm-up calls of the same call as the
   same user, with nothing written in between.
2. *A guard that can fail.* An assertion that a count did not grow passes
   perfectly on an empty fixture. Every test here first asserts that the team
   or the scope actually got bigger, and says by how much when it does not.

Runs on any site in about a minute. It does **not** need the 1,000-person
fixture: a query inside a loop shows up at thirty people just as clearly, and a
regression guard nobody can afford to run is not a guard.

Synthetic people only, tagged S044F, in this file's own company.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import frame_api, home_api, inbox_api, staff_api

TAG = "S044F"
COMPANY = "S044F Flatness Company"
BRANCH = "S044F Store"

SMALL_TEAM = 4        # people under the manager to start with
GROWN_TEAM = 30       # and after the company hires


class _Spy:
	"""Every SQL statement run inside the block.

	`frappe.db.sql` is the one door every read goes through, the query builder's
	`.run()` included, so wrapping it turns "how many queries" into something a
	test can assert rather than something a reviewer squints at.
	"""

	def __init__(self):
		self.statements = []

	def __enter__(self):
		self._real = frappe.db.sql

		def spy(query, *args, **kwargs):
			self.statements.append(str(query))
			return self._real(query, *args, **kwargs)

		frappe.db.sql = spy
		return self

	def __exit__(self, *exc):
		frappe.db.sql = self._real
		return False


class _Flatness(FrappeTestCase):
	"""One manager, one HR person, one plain employee, and a team that grows."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from alvoraa_goals.tests.utils import (
			_ensure_erpnext_company_prerequisites,
			ensure_gender,
		)

		cls._gender = ensure_gender()
		if not frappe.db.exists("Company", COMPANY):
			_ensure_erpnext_company_prerequisites()
			doc = frappe.get_doc({
				"doctype": "Company", "company_name": COMPANY, "abbr": "S44F",
				"default_currency": "INR", "country": "India",
			})
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
		if not frappe.db.exists("Branch", BRANCH):
			frappe.get_doc({"doctype": "Branch", "branch": BRANCH}).insert(
				ignore_permissions=True)

		cls.mgr_login = cls._user("mgr", ("Employee",))
		cls.emp_login = cls._user("emp", ("Employee",))
		cls.hr_login = cls._user("hr", ("HR Manager", "Employee"))

		cls.mgr = cls._employee("Mgr", login=cls.mgr_login)
		cls.emp = cls._employee("Emp", login=cls.emp_login, reports_to=cls.mgr)
		cls.hr = cls._employee("Hr", login=cls.hr_login)
		# HR is scoped to this company only, so growing it grows their scope and
		# nothing else on the site does.
		if not frappe.db.exists("User Permission",
		                        {"user": cls.hr_login, "allow": "Company",
		                         "for_value": COMPANY}):
			frappe.get_doc({"doctype": "User Permission", "user": cls.hr_login,
			                "allow": "Company", "for_value": COMPANY,
			                "apply_to_all_doctypes": 1}).insert(
				ignore_permissions=True)
		frappe.clear_cache(user=cls.hr_login)
		frappe.db.commit()

	@classmethod
	def _user(cls, local, roles):
		email = "s044f.%s@example.com" % local
		if not frappe.db.exists("User", email):
			doc = frappe.get_doc({"doctype": "User", "email": email,
			                      "first_name": local.title(), "last_name": TAG,
			                      "send_welcome_email": 0, "enabled": 1})
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
		doc = frappe.get_doc("User", email)
		have = {r.role for r in doc.roles}
		for role in roles:
			if role not in have:
				doc.append("roles", {"role": role})
		doc.flags.ignore_permissions = True
		doc.save(ignore_permissions=True)
		frappe.db.set_value("User", email, "module_profile", None,
		                    update_modified=False)
		frappe.db.delete("Block Module", {"parent": email, "parenttype": "User"})
		frappe.clear_cache(user=email)
		return email

	@classmethod
	def _employee(cls, first, login=None, reports_to=None):
		existing = frappe.db.get_value(
			"Employee", {"first_name": first, "last_name": TAG}, "name")
		if existing:
			return existing
		doc = frappe.get_doc({
			"doctype": "Employee", "first_name": first, "last_name": TAG,
			"gender": cls._gender, "date_of_birth": "1992-06-15",
			"date_of_joining": "2023-04-01", "status": "Active",
			"company": COMPANY, "branch": BRANCH, "reports_to": reports_to,
			"user_id": login, "create_user_permission": 0,
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		if login:
			frappe.db.delete("User Permission", {"user": login})
			frappe.clear_cache(user=login)
		return doc.name

	# ── growing the company ──────────────────────────────────────────────

	@classmethod
	def _hire(cls, upto):
		"""Make the manager's team `upto` people, through the ORM."""
		from frappe.utils.nestedset import rebuild_tree

		have = frappe.get_all("Employee",
		                      filters={"reports_to": cls.mgr, "status": "Active"},
		                      pluck="name")
		frappe.local.flags.ignore_update_nsm = True
		try:
			for i in range(len(have), upto):
				cls._employee("Hire%03d" % i, reports_to=cls.mgr)
			frappe.db.commit()
		finally:
			frappe.local.flags.ignore_update_nsm = False
		rebuild_tree("Employee")
		frappe.db.commit()
		return frappe.db.count("Employee",
		                       {"reports_to": cls.mgr, "status": "Active"})

	@classmethod
	def _fire(cls):
		"""Back to the small team. Removes only this file's hires."""
		names = frappe.get_all(
			"Employee",
			filters={"last_name": TAG, "first_name": ["like", "Hire%"]},
			pluck="name")
		for name in names:
			frappe.delete_doc("Employee", name, force=True,
			                  ignore_permissions=True, delete_permanently=True)
		frappe.db.commit()

	# ── measuring ────────────────────────────────────────────────────────

	def _as(self, login):
		frappe.set_user(login)
		frappe.local.request_ip = "127.0.0.1"

	def _measure(self, login, thunk, warm=3):
		"""Warm, then measure. Nothing is written between the warm-up and the
		reading, which is the whole method."""
		self._as(login)
		payload = None
		for _ in range(warm):
			payload = thunk()
		with _Spy() as spy:
			payload = thunk()
		frappe.set_user("Administrator")
		return len(spy.statements), payload

	def _flat(self, login, thunk, name, allow=0):
		"""The assertion this file exists for.

		Measure at four people, hire to thirty, measure again, and fail if the
		query count grew. The guard comes first: if the team did not really
		grow, the comparison proved nothing and the test says so.
		"""
		self._fire()
		small_team = self._hire(SMALL_TEAM)
		small, _payload = self._measure(login, thunk)

		grown_team = self._hire(GROWN_TEAM)
		self.assertGreater(
			grown_team, small_team + 10,
			"the team went from %d to %d, so growing it proved nothing"
			% (small_team, grown_team))
		grown, payload = self._measure(login, thunk)

		self.assertLessEqual(
			grown, small + allow,
			"%s took %d queries for a team of %d and %d for a team of %d - "
			"that is a query that grows with headcount, which is what the "
			"16.4-second bell was"
			% (name, small, small_team, grown, grown_team))
		return small, grown, payload


class TestTheLandingCallsAreFlatInHeadcount(_Flatness):
	"""Five calls, three personas, one property: hiring must not cost queries."""

	def tearDown(self):
		frappe.set_user("Administrator")
		self._fire()
		super().tearDown()

	def test_get_nav_counts_is_flat_for_a_manager(self):
		self._flat(self.mgr_login, inbox_api.get_nav_counts,
		           "get_nav_counts (manager)")

	def test_get_nav_counts_is_flat_for_hr(self):
		"""The one that matters most: HR's scope IS the headcount."""
		self._flat(self.hr_login, inbox_api.get_nav_counts,
		           "get_nav_counts (HR)")

	def test_get_home_is_flat_for_a_manager(self):
		"""Home's team card reads the manager's reports, so it grows with them."""
		_small, _grown, payload = self._flat(
			self.mgr_login, home_api.get_home, "get_home (manager)")
		self.assertEqual(
			payload["team_today"]["basis"], "team",
			"the manager's Home did not draw a team card, so the comparison "
			"was not about a team at all")

	def test_get_home_is_flat_for_hr(self):
		_small, _grown, payload = self._flat(
			self.hr_login, home_api.get_home, "get_home (HR)")
		self.assertEqual(
			payload["team_today"]["basis"], "hr",
			"HR's Home did not draw the HR-scoped card")

	def test_get_home_is_flat_for_a_plain_employee(self):
		"""A plain employee's peer card is their manager's other reports, so it
		grows with the team even though they manage nobody."""
		_small, _grown, payload = self._flat(
			self.emp_login, home_api.get_home, "get_home (employee)")
		self.assertEqual(
			payload["team_today"]["basis"], "peers",
			"the employee's Home did not draw a peer card")

	def test_get_inbox_is_flat_for_hr(self):
		self._flat(self.hr_login, inbox_api.get_inbox, "get_inbox (HR)")

	def test_get_frame_is_flat_for_hr(self):
		self._flat(self.hr_login, frame_api.get_frame, "get_frame (HR)")

	def test_get_staff_list_is_flat_for_hr(self):
		"""The staff list is paged, so a bigger company must cost the same."""
		_small, _grown, payload = self._flat(
			self.hr_login, staff_api.get_staff_list, "get_staff_list (HR)")
		self.assertGreaterEqual(
			payload.get("total") or 0, GROWN_TEAM,
			"the staff list did not see the new people, so nothing was proved")


class TestTheGuardCanFail(_Flatness):
	"""The guard that stops this file passing on an empty fixture.

	An assertion that a number did not grow is free to pass when nothing grew.
	These two prove the machinery here would notice.
	"""

	def tearDown(self):
		frappe.set_user("Administrator")
		self._fire()
		super().tearDown()

	def test_a_team_that_does_not_grow_fails_the_guard(self):
		"""Hiring nobody must be caught, not read as flatness."""
		self._fire()
		small_team = self._hire(SMALL_TEAM)
		grown_team = self._hire(SMALL_TEAM)
		with self.assertRaises(AssertionError) as caught:
			self.assertGreater(
				grown_team, small_team + 10,
				"the team went from %d to %d, so growing it proved nothing"
				% (small_team, grown_team))
		self.assertIn("proved nothing", str(caught.exception))

	def test_a_call_that_walks_the_team_one_by_one_is_caught(self):
		"""The failure mode, written out as code and proved to be caught.

		This is the 16.4-second bell in three lines: a query per person. If
		`_flat` could not see it, every other test in this file would be
		decoration.
		"""
		def walks_the_team():
			names = frappe.get_all(
				"Employee",
				filters={"reports_to": self.mgr, "status": "Active"},
				pluck="name")
			return [frappe.db.get_value("Employee", n, "employee_name")
			        for n in names]

		with self.assertRaises(AssertionError) as caught:
			self._flat(self.mgr_login, walks_the_team, "a deliberate N+1")
		self.assertIn("grows with headcount", str(caught.exception))


class TestTheBellIsNotBackToWalkingPeople(_Flatness):
	"""AC-16, from the other side.

	`goals_api.get_pending_approvals` walks one employee at a time and took 16.4
	seconds for an HR caller. Wave 2's Inbox reuses that helper's **scope** and
	must never reuse its loop. This asserts the loop is not there by measuring
	it, not by reading the code.
	"""

	def tearDown(self):
		frappe.set_user("Administrator")
		self._fire()
		super().tearDown()

	def test_the_goal_updates_part_does_not_query_per_person(self):
		from alvoraa_portal.inbox_api import parts

		def goal_part_count():
			built, _scope = parts()
			for part in built:
				if part.key == "goal_updates":
					return part.count()
			raise AssertionError("no goal_updates part")

		small, grown, _payload = self._flat(
			self.hr_login, goal_part_count, "the goal-updates part (HR)")
		# Said out loud in the failure message above; this line is here so the
		# numbers reach the report even on a pass.
		self.assertLessEqual(grown, small)
