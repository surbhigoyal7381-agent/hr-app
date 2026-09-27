"""Slice 034, US-7 / US-14 / US-15 - what people search may find, and for whom.

Three changes, each with its own reason:

**A store's HR person searches their store, plus their own reporting line**
(SEC-3, AC-26). Before this they searched their whole company, which is the
same leak W1D-20 closed on the Team screen - closed there and left open here
would be worse than either, because search is the faster way to find a name.
An employee with no branch is head office, and head office is outside every
store (DEF-6).

**A leaver finds nobody** (SEC-14, AC-68). The search path now looks up the
caller's ACTIVE Employee record. A manager who has left, whose login is still
enabled and whose reports have not moved, kept finding his whole team by name.

**`%` and `_` mean themselves** (PRIV-3, AC-57). A single `%` used to return
everybody the caller may see, in one call, from two keystrokes.

The payload is pinned at PRIV-2's five keys (AC-56), Active people only.

Synthetic people only, tagged by the shared helpers plus S034S of our own.
"""

import frappe

# `import x.y.z as name`, not `from x.y import z`. The integrity check rejects
# the second form - it is the shape that silently shadows a package attribute -
# and `run-tests` does not catch it, so it would fail in CI instead.
import hrms.alvoraa_org_structure.api as org

from alvoraa_portal.tests.test_portal_security_010 import _employee, _user
from alvoraa_portal.tests.test_store_hr_scoping_030 import _Stores

S_A = "S034S Store A"
S_B = "S034S Store B"

# One term that matches every person this file creates and nobody else's.
TERM = "Searchable"


class _SearchFixture(_Stores):
	"""Two stores of this file's own, and one person in each place.

	Its own stores, for the reason stretch 5 learned the hard way: slice 030
	asserts an exact set of names in ITS store A, so anybody added there breaks
	it. Test data is shared state on one site.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for branch in (S_A, S_B):
			if not frappe.db.exists("Branch", branch):
				frappe.get_doc({"doctype": "Branch", "branch": branch}).insert(
					ignore_permissions=True)
		cls.store_hr_user = _user("s034s.storehr", ("HR User", "Employee"))
		cls.store_hr = _employee("SearchableStoreHR", company=cls.company_a,
		                         user=cls.store_hr_user)
		cls.wide_hr_user = _user("s034s.widehr", ("HR Manager", "Employee"))
		cls.wide_hr = _employee("SearchableWideHR", company=cls.company_a,
		                        user=cls.wide_hr_user)
		cls.in_a = _employee("SearchableInA", company=cls.company_a)
		cls.in_b = _employee("SearchableInB", company=cls.company_a)
		# Head office: no branch at all, so outside every store.
		cls.head_office = _employee("SearchableHeadOffice", company=cls.company_a)
		# A direct report of the store's HR person, sitting in the OTHER store.
		# They manage this person, so they must keep finding them.
		cls.report_in_b = _employee("SearchableReportInB", company=cls.company_a,
		                            reports_to=cls.store_hr)
		# A plain manager and his one report, for the leaver case.
		cls.mgr_user = _user("s034s.mgr", ("Employee",))
		cls.mgr = _employee("SearchableManager", company=cls.company_a, user=cls.mgr_user)
		cls.mgr_report = _employee("SearchableUnderManager", company=cls.company_a,
		                           reports_to=cls.mgr)
		# Somebody with a wildcard in their name, so an escaped search can still
		# find a real match rather than only proving it finds nothing.
		cls.odd = _employee("Searchable_Odd", company=cls.company_a)
		for emp, branch in ((cls.store_hr, S_A), (cls.in_a, S_A), (cls.wide_hr, None),
		                    (cls.in_b, S_B), (cls.report_in_b, S_B),
		                    (cls.head_office, None), (cls.mgr, S_A),
		                    (cls.mgr_report, S_A), (cls.odd, S_A)):
			frappe.db.set_value("Employee", emp, "branch", branch, update_modified=False)
		frappe.db.commit()

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		if not frappe.db.exists("User Permission",
		                        {"user": self.store_hr_user, "allow": "Branch",
		                         "for_value": S_A}):
			frappe.get_doc({"doctype": "User Permission", "user": self.store_hr_user,
			                "allow": "Branch", "for_value": S_A,
			                "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
		frappe.clear_cache(user=self.store_hr_user)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete("User Permission",
		                 {"user": self.store_hr_user, "allow": "Branch"})
		frappe.clear_cache(user=self.store_hr_user)
		frappe.db.commit()
		super().tearDown()

	def _find(self, user, term=TERM, limit=50):
		self._as(user)
		return {row["employee"] for row in org.search_people(term, limit=limit)}


class TestWhoEachPersonaFinds(_SearchFixture):
	def test_store_hr_finds_their_store_and_their_own_line(self):
		"""AC-26. The store, plus anybody who reports to them wherever they sit.

		Both halves matter. Without the store they would find only their own
		reports, which is useless to an HR person who manages nobody; without
		their own line an HR person for one store who manages somebody in
		another would lose them.
		"""
		found = self._find(self.store_hr_user)
		self.assertIn(self.in_a, found, "their own store is missing")
		self.assertIn(self.report_in_b, found,
		              "their own direct report, outside the store, was dropped")
		self.assertNotIn(self.head_office, found,
		                 "head office - an employee with no branch - is in a store's search")
		self.assertNotIn(self.in_b, found, "another store's person is findable")

	def test_company_wide_hr_finds_the_head_office_person(self):
		"""AC-26's other half. Somebody must be able to find that person, and
		it is the HR user who holds no Branch permission."""
		found = self._find(self.wide_hr_user)
		self.assertIn(self.head_office, found)
		self.assertIn(self.in_b, found)

	def test_a_manager_finds_their_line_and_nobody_else(self):
		"""Unchanged behaviour, asserted so the rewrite cannot have moved it."""
		found = self._find(self.mgr_user)
		self.assertIn(self.mgr_report, found)
		self.assertIn(self.mgr, found, "a person must find themselves")
		self.assertNotIn(self.in_b, found)
		self.assertNotIn(self.head_office, found)

	def test_a_leaver_with_a_live_login_finds_nobody(self):
		"""AC-68 / SEC-14. Access ends when employment does."""
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.mgr, "status", "Left", update_modified=False)
		frappe.db.commit()
		try:
			self.assertEqual(self._find(self.mgr_user), set(),
			                 "a leaver still finds his team by name")
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", self.mgr, "status", "Active",
			                    update_modified=False)
			frappe.db.commit()


class TestTheTermIsNotAWildcard(_SearchFixture):
	def test_a_bare_percent_finds_nobody(self):
		"""PRIV-3 / AC-57. Two keystrokes used to return the caller's whole
		scope, which is a directory export dressed as a search."""
		self.assertEqual(self._find(self.wide_hr_user, "%%"), set())

	def test_an_underscore_matches_an_underscore(self):
		"""`a_b` must not quietly match `axb`. The fixture has a person with a
		real underscore in their name, so this proves the escaping still finds
		a true match rather than only proving it finds nothing."""
		found = self._find(self.wide_hr_user, "Searchable_")
		self.assertIn(self.odd, found)
		self.assertNotIn(self.in_a, found,
		                 "the underscore behaved as a single-character wildcard")

	def test_one_letter_is_not_a_search(self):
		self.assertEqual(self._find(self.wide_hr_user, "S"), set())


class TestThePayload(_SearchFixture):
	def test_the_keys_are_exactly_the_five(self):
		"""AC-56 / PRIV-2. Adding a field here is a visibility change."""
		self._as(self.wide_hr_user)
		rows = org.search_people(TERM, limit=5)
		self.assertTrue(rows)
		for row in rows:
			self.assertEqual(set(row.keys()),
			                 {"employee", "name", "title", "department", "image"})

	def test_only_active_people_are_returned(self):
		"""A leaver is not a colleague to look up."""
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.in_a, "status", "Inactive",
		                    update_modified=False)
		frappe.db.commit()
		try:
			self.assertNotIn(self.in_a, self._find(self.wide_hr_user))
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", self.in_a, "status", "Active",
			                    update_modified=False)
			frappe.db.commit()

	def test_a_large_limit_is_capped(self):
		"""AC-28. The screen asks for 12; the server decides the ceiling."""
		self._as(self.wide_hr_user)
		self.assertLessEqual(len(org.search_people(TERM, limit=500)), org.MAX_RESULTS)

	def test_it_is_a_post_endpoint_and_guest_may_not_call_it(self):
		"""PRIV-5 and SEC-2. A name does not belong in a URL, a proxy log or a
		browser history; and every endpoint is live on production whatever page
		calls it. `whitelisted` and `guest_methods` are sets of the functions
		themselves, and the allowed methods are a dict keyed by the same
		function (frappe/__init__.py:423-426, read on the bench)."""
		self.assertIn(org.search_people, frappe.whitelisted)
		self.assertNotIn(org.search_people, frappe.guest_methods)
		self.assertEqual(
			frappe.allowed_http_methods_for_whitelisted_func[org.search_people],
			["POST"])
