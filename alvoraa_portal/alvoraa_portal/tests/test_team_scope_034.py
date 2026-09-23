"""Slice 034, SEC-13 / AC-72 / W1D-20 - the Team screen follows the HR scope.

What was there before: `get_manager_dashboard` added every Active employee in
the tenant whose `reports_to` was empty to anyone holding HR Manager or HR User,
with `ignore_permissions=True` and no company or branch filter at all. A store's
HR person in Ludhiana got head office and every other store's unassigned people
on their own team screen.

It is replaced, not filtered: an HR caller's Team screen is now
`access.permitted_employee_filters()` - their companies, narrowed to their
branches - plus their own direct reports, capped, with the true total beside it.

Every row of AC-72's table is here, and so are the three things that would be a
regression if the rebuild dropped them: leavers stay out, the caller stays out,
and a direct report outside the caller's HR scope stays in.

Synthetic people only, tagged S030 (the shared two-store fixture) and S034.
"""

import frappe

from alvoraa_portal import hr_api
from alvoraa_portal.tests.test_portal_security_010 import _employee, _user
from alvoraa_portal.tests.test_store_hr_scoping_030 import STORE_A, STORE_B, _Stores


ST_A = "S034 Store A"
ST_B = "S034 Store B"


class _TeamFixture(_Stores):
	"""Two stores of this slice's own, and everybody this AC needs in them.

	Deliberately NOT slice 030's stores. Its first test asserts that a store HR
	person sees exactly three named people, so anybody added to its store A
	breaks it - which is what happened on the first run of this file. Test data
	is shared state on one site, and an exact-equality assertion next door is
	the cheapest way to find that out.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for branch in (ST_A, ST_B):
			if not frappe.db.exists("Branch", branch):
				frappe.get_doc({"doctype": "Branch", "branch": branch}).insert(
					ignore_permissions=True)
		# The store's HR person, with one direct report inside their store and
		# one outside it.
		cls.s_hr_user = _user("s034.storehr", ("HR User", "Employee"))
		cls.s_hr = _employee("S034StoreHR", company=cls.company_a, user=cls.s_hr_user)
		cls.in_a = _employee("S034InA", company=cls.company_a)
		cls.report_a = _employee("S034ReportA", company=cls.company_a)
		# A direct report OUTSIDE their HR scope. They manage this person, so
		# this person must stay on their team screen whatever the scope says.
		cls.report_b = _employee("S034ReportB", company=cls.company_a)
		cls.in_b = _employee("S034InB", company=cls.company_a)
		# Head office: no branch at all, so outside every store (DEF-6).
		cls.no_branch = _employee("S034NoBranch", company=cls.company_a)
		# A leaver in store A. permitted_employee_filters returns every status
		# on purpose, so if "Active" ever falls off the Team query this appears.
		cls.leaver_a = _employee("S034LeaverA", company=cls.company_a)
		# A second store HR person who manages nobody at all. Before W1D-20
		# this person had no team screen.
		cls.lonely_user = _user("s034.lonelyhr", ("HR User", "Employee"))
		cls.lonely_hr = _employee("S034LonelyHR", company=cls.company_a,
		                          user=cls.lonely_user)
		for emp, branch in ((cls.s_hr, ST_A), (cls.in_a, ST_A), (cls.report_a, ST_A),
		                    (cls.leaver_a, ST_A), (cls.lonely_hr, ST_A),
		                    (cls.report_b, ST_B), (cls.in_b, ST_B),
		                    (cls.no_branch, None)):
			frappe.db.set_value("Employee", emp, "branch", branch, update_modified=False)
		for emp in (cls.report_a, cls.report_b):
			frappe.db.set_value("Employee", emp, "reports_to", cls.s_hr,
			                    update_modified=False)
		frappe.db.set_value("Employee", cls.leaver_a, "status", "Left",
		                    update_modified=False)
		# Nobody in store A has a manager except the two reports, so the "used
		# to be added to everybody's screen" case is real without touching any
		# other slice's fixture.
		frappe.db.commit()

	def setUp(self):
		super().setUp()
		for user in (self.s_hr_user, self.lonely_user):
			if not frappe.db.exists("User Permission",
			                        {"user": user, "allow": "Branch", "for_value": ST_A}):
				frappe.get_doc({"doctype": "User Permission", "user": user,
				                "allow": "Branch", "for_value": ST_A,
				                "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
			frappe.clear_cache(user=user)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		for user in (self.s_hr_user, self.lonely_user):
			frappe.db.delete("User Permission", {"user": user, "allow": "Branch"})
			frappe.clear_cache(user=user)
		frappe.db.commit()
		super().tearDown()

	def _team(self, user):
		self._as(user)
		d = hr_api.get_manager_dashboard()
		self.assertFalse(d.get("no_employee"), "the caller has no Employee record")
		return d, {row["name"] for row in d["team"]}


class TestTheTeamScreenFollowsTheHrScope(_TeamFixture):
	def test_store_hr_sees_their_store_and_nowhere_else(self):
		"""AC-72 row 1. This is the leak the slice exists to close."""
		d, names = self._team(self.s_hr_user)
		self.assertTrue({self.in_a, self.report_a} <= names,
		                "store A's own people are missing")
		self.assertNotIn(self.no_branch, names,
		                 "the head-office employee with no branch is on a store's screen")
		self.assertTrue(d["is_hr_scope"])

	def test_the_unassigned_employee_outside_the_store_is_gone(self):
		"""The exact row the deleted block used to add: an Active employee with
		no manager, in another branch, in the same tenant."""
		_d, names = self._team(self.s_hr_user)
		self.assertNotIn(self.no_branch, names)
		self.assertNotIn(self.in_b, names)

	def test_a_store_hr_person_who_manages_nobody_still_has_a_screen(self):
		"""AC-72 row 2, and the whole point of W1D-20. Before this they had an
		empty screen; a test that only checked for absences would have passed."""
		d, names = self._team(self.lonely_user)
		self.assertTrue(names, "the screen is empty - this is what W1D-20 gives back")
		self.assertTrue({self.in_a, self.s_hr, self.report_a} <= names)
		self.assertNotIn(self.no_branch, names)
		self.assertGreaterEqual(d["team_total"], 3)

	def test_a_leaver_never_appears(self):
		"""AC-72 row 5. permitted_employee_filters returns every status on
		purpose, so "Active" must survive on this query or the screen gets WIDER."""
		for user in (self.s_hr_user, self.hr_user):
			_d, names = self._team(user)
			self.assertNotIn(self.leaver_a, names, user)

	def test_the_caller_is_never_on_their_own_screen(self):
		for user in (self.s_hr_user, self.hr_user, self.lonely_user):
			d, names = self._team(user)
			self.assertNotIn(d["manager"]["name"], names, user)

	def test_a_direct_report_outside_the_hr_scope_is_still_on_the_screen(self):
		"""They manage this person. Losing them would be a new regression, not
		a fix - the point of SEC-13 is to stop showing people who are nothing to
		do with the caller, not to hide the caller's own team."""
		_d, names = self._team(self.s_hr_user)
		self.assertIn(self.report_b, names,
		              "their own direct report in another store has gone missing")

	def test_a_manager_who_is_not_hr_is_untouched(self):
		"""AC-72 row 4. The deleted block never ran for them, so nothing here
		may change: their own direct reports, and no unassigned people."""
		self._as(self.manager_user)
		d = hr_api.get_manager_dashboard()
		names = {row["name"] for row in d["team"]}
		expected = set(frappe.get_all(
			"Employee",
			filters={"reports_to": d["manager"]["name"], "status": "Active"},
			pluck="name"))
		self.assertEqual(names, expected)
		self.assertFalse(d["is_hr_scope"])
		self.assertFalse(d["team_capped"])
		self.assertEqual(d["team_total"], len(expected))

	def test_company_wide_hr_gets_their_companies(self):
		"""AC-72 row 3. The cap is lifted for this one, because the test site
		carries a hundred other people and the fixture's four are not in the
		first fifty by name - which is the cap doing its job, not a fault."""
		real = hr_api.TEAM_LIST_CAP
		hr_api.TEAM_LIST_CAP = 1000
		try:
			d, names = self._team(self.hr_user)
		finally:
			hr_api.TEAM_LIST_CAP = real
		self.assertTrue({self.in_a, self.in_b, self.no_branch, self.report_a} <= names)
		self.assertTrue(d["is_hr_scope"])
		self.assertFalse(d["team_capped"])
		self.assertEqual(d["team_total"], len(names))


	def test_the_true_total_is_shown_when_the_list_is_capped(self):
		"""Surbhi's standing rule: a count must equal the list it sits beside,
		and a capped list must say so. The cap is lowered here rather than
		creating fifty people, so the arithmetic is what is being tested."""
		real = hr_api.TEAM_LIST_CAP
		hr_api.TEAM_LIST_CAP = 2
		try:
			d, names = self._team(self.s_hr_user)
			self.assertEqual(len(names), 2, "the cap was not applied")
			self.assertTrue(d["team_capped"])
			self.assertEqual(d["team_size"], 2)
			self.assertEqual(d["team_cap"], 2)
			self.assertGreater(d["team_total"], 2,
			                   "the true total is not bigger than the capped list")
		finally:
			hr_api.TEAM_LIST_CAP = real

	def test_an_uncapped_list_reports_its_own_length(self):
		d, names = self._team(self.s_hr_user)
		self.assertFalse(d["team_capped"])
		self.assertEqual(d["team_total"], len(names))
		self.assertEqual(d["team_size"], len(names))

	def test_the_total_counts_the_same_people_the_list_would_hold(self):
		"""Uncap it and the total must be exactly what comes back."""
		real = hr_api.TEAM_LIST_CAP
		hr_api.TEAM_LIST_CAP = 2
		try:
			capped, _ = self._team(self.s_hr_user)
		finally:
			hr_api.TEAM_LIST_CAP = real
		full, names = self._team(self.s_hr_user)
		self.assertEqual(capped["team_total"], full["team_total"])
		self.assertEqual(full["team_total"], len(names))


	def test_no_employees_with_no_manager_query_survives_on_the_team_screen(self):
		"""AC-72's static check. The block is deleted, not left behind a
		condition - a narrowed version of the same query would still answer
		"who has no manager" rather than "who may I see".

		Checked against get_manager_dashboard, not the whole module, and the
		reason is worth writing down rather than leaving as a quiet choice:
		get_portal_context has a second "is anybody unassigned" count, used to
		decide the is_manager FLAG. It is a boolean, not a list of people, and
		the spec says in as many words that get_portal_context is not changed by
		this slice (SEC-12). It is pinned below so it cannot grow into a list."""
		import inspect

		src = inspect.getsource(hr_api.get_manager_dashboard)
		for token in ('"reports_to": ("is", "not set")',
		              '"reports_to": ["is", "not set"]',
		              "'reports_to': ('is', 'not set')"):
			self.assertNotIn(token, src, "the orphan query is still on the Team screen")

	def test_the_only_other_unassigned_query_is_still_a_count(self):
		"""The one in get_portal_context. If it ever starts returning people
		instead of a number, this fails and somebody has to think about it."""
		import inspect

		src = inspect.getsource(hr_api.get_portal_context)
		self.assertIn('"reports_to": ("is", "not set")', src,
		              "it moved or changed shape - re-read this test")
		self.assertIn("frappe.db.count(", src)
		self.assertNotIn("frappe.get_all(", src.split('"reports_to": ("is", "not set")')[0][-400:],
		                 "it is no longer a count")

	def test_the_scoped_query_asks_the_database_for_a_bounded_list(self):
		"""Found by breaking the code on purpose: taking `limit` off the query
		turned NO test red, because the Python truncation below it still cut the
		list to fifty. The screen looked right while the database was handing
		back a thousand rows - the exact cost the cap exists to avoid. So the
		limit is asserted where it matters, on the query itself."""
		seen = []
		real_get_all = frappe.get_all

		def spy(doctype, *args, **kwargs):
			if doctype == "Employee" and isinstance(kwargs.get("filters"), list):
				seen.append(kwargs.get("limit"))
			return real_get_all(doctype, *args, **kwargs)

		frappe.get_all = spy
		try:
			self._team(self.s_hr_user)
		finally:
			frappe.get_all = real_get_all
		self.assertTrue(seen, "the scoped Employee query did not run")
		self.assertEqual(seen[0], hr_api.TEAM_LIST_CAP,
		                 "the scoped Employee query is unbounded - the cap is "
		                 "only being applied after the rows have been fetched")

	def test_the_team_query_is_built_on_the_shared_scope_helper(self):
		"""One definition of who HR may see (SEC-4). A private copy of the rule
		here is how the three readers in slice 030 drifted apart."""
		import inspect

		src = inspect.getsource(hr_api.get_manager_dashboard)
		self.assertIn("permitted_employee_filters(user)", src)
		self.assertIn('["status", "=", "Active"]', src)
