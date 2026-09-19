"""How far somebody may see on the org chart.

An ordinary employee gets a window around their own seat. HR, leadership and
anybody with people reporting to them may roam.

The reason for the limit is not tidiness. An organisation chart is commercially
sensitive - it names every manager, every team size and every gap - and it is the
first thing that walks out of the door with a leaver. Two levels up and two down
answers the questions an employee actually has.

**Every test here calls the API, not the JavaScript.** A limit enforced in the
page is a suggestion: the endpoint is whitelisted, and anybody who can open the
portal can call it with whatever root they like.
"""

import frappe

from hrms.alvoraa_org_structure import api, settings
from hrms.alvoraa_org_structure.tests.test_org_structure import OrgCase


class ReachCase(OrgCase):
	def setUp(self):
		super().setUp()
		self._saved = {k: frappe.db.get_default(k) for k in settings.DEFAULTS}
		self._user = frappe.session.user
		self._forget()

	def tearDown(self):
		frappe.set_user(self._user)
		for k, v in self._saved.items():
			frappe.db.set_default(k, v if v is not None else "")
		self._forget()
		super().tearDown()

	def _forget(self):
		"""Drop the per-request "does this person manage anybody" cache.

		It is keyed on the user's email, and these tests reuse the same email
		for a fresh Employee each time - so without this, one test's answer
		would be handed to the next and the failure would look like a bug in
		the rule rather than in the test.
		"""
		frappe.local._alvoraa_leads = {}

	def _ladder(self):
		"""Owner > Head > Manager > Supervisor > Assistant, one person each."""
		names = ["Owner", "Head", "Manager", "Supervisor", "Assistant"]
		seats, parent = {}, None
		for n in names:
			seats[n] = self.pos(n, parent=parent)
			parent = seats[n].name
		people = {}
		for n in names:
			people[n] = self.person(n + "Person")
			self.assign(people[n], seats[n].name, weight=100)
		return seats, people

	def _become(self, employee):
		email = f"{employee}.reach@example.com".lower()
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "Reach",
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		frappe.db.set_value("Employee", employee, "user_id", email)
		frappe.set_user(email)
		self._forget()
		return email


class TestAnOrdinaryEmployeeIsBounded(ReachCase):
	def setUp(self):
		super().setUp()
		# Nobody roams by role, and having reports does not open it either -
		# otherwise everybody in the ladder above would be unlimited.
		frappe.db.set_default("alvoraa_org_full_reach_roles", "")
		frappe.db.set_default("alvoraa_org_managers_see_all", 0)

	def test_two_levels_up_is_allowed(self):
		seats, people = self._ladder()
		self._become(people["Assistant"])
		self.assertTrue(api._within_reach(seats["Manager"].name, frappe.utils.nowdate()))

	def test_three_levels_up_is_not(self):
		seats, people = self._ladder()
		self._become(people["Assistant"])
		self.assertFalse(api._within_reach(seats["Head"].name, frappe.utils.nowdate()))

	def test_asking_for_it_anyway_is_refused_not_silently_empty(self):
		"""An employee should be told, not left staring at a blank box wondering
		whether the page is broken."""
		seats, people = self._ladder()
		self._become(people["Assistant"])
		with self.assertRaises(frappe.PermissionError):
			api.subtree(root=seats["Owner"].name)

	def test_the_breadcrumb_stops_at_the_same_ceiling(self):
		"""A breadcrumb that names the chief executive to everybody is the org
		chart leaking one row at a time."""
		seats, people = self._ladder()
		self._become(people["Assistant"])
		chain = api.chain_to_top()
		self.assertLessEqual(len(chain), 3)          # two up, plus themselves
		self.assertNotIn(seats["Owner"].name, [c["id"] for c in chain])

	def test_the_window_is_a_setting(self):
		seats, people = self._ladder()
		self._become(people["Assistant"])
		frappe.db.set_default("alvoraa_org_reach_up", 4)
		self.assertTrue(api._within_reach(seats["Owner"].name, frappe.utils.nowdate()))

	def test_their_own_seat_is_always_visible(self):
		seats, people = self._ladder()
		self._become(people["Assistant"])
		self.assertTrue(api._within_reach(seats["Assistant"].name, frappe.utils.nowdate()))


class TestWhoMayRoam(ReachCase):
	def test_hr_may_see_everything(self):
		seats, people = self._ladder()
		email = self._become(people["Assistant"])
		frappe.set_user("Administrator")
		doc = frappe.get_doc("User", email)
		doc.append("roles", {"role": "HR Manager"})
		doc.save(ignore_permissions=True)
		frappe.set_user(email)
		self.assertTrue(api.reach()["unlimited"])
		self.assertTrue(api._within_reach(seats["Owner"].name, frappe.utils.nowdate()))

	def test_anybody_with_people_under_them_may_roam(self):
		"""A manager who cannot see past their own team cannot plan around the
		one next door."""
		frappe.db.set_default("alvoraa_org_full_reach_roles", "")
		seats, people = self._ladder()
		self._become(people["Manager"])          # has Supervisor beneath
		out = api.reach()
		self.assertTrue(out["unlimited"])
		self.assertEqual(out["why"], "manager")

	def test_an_organisation_may_bound_managers_too(self):
		frappe.db.set_default("alvoraa_org_full_reach_roles", "")
		frappe.db.set_default("alvoraa_org_managers_see_all", 0)
		seats, people = self._ladder()
		self._become(people["Manager"])
		self.assertFalse(api.reach()["unlimited"])

	def test_turning_the_setting_back_on_takes_effect_at_once(self):
		"""reach() caches the expensive lookup but re-reads its settings every
		time. If it cached the whole verdict this would still say bounded."""
		frappe.db.set_default("alvoraa_org_full_reach_roles", "")
		frappe.db.set_default("alvoraa_org_managers_see_all", 0)
		seats, people = self._ladder()
		self._become(people["Manager"])
		self.assertFalse(api.reach()["unlimited"])
		frappe.db.set_default("alvoraa_org_managers_see_all", 1)
		self.assertTrue(api.reach()["unlimited"])

	def test_somebody_at_the_bottom_is_not_a_manager(self):
		frappe.db.set_default("alvoraa_org_full_reach_roles", "")
		seats, people = self._ladder()
		self._become(people["Assistant"])
		self.assertFalse(api.reach()["unlimited"])

	def test_the_roles_that_roam_are_a_setting(self):
		seats, people = self._ladder()
		email = self._become(people["Assistant"])
		frappe.set_user("Administrator")
		doc = frappe.get_doc("User", email)
		doc.append("roles", {"role": "Employee"})
		doc.save(ignore_permissions=True)
		frappe.db.set_default("alvoraa_org_full_reach_roles", "Employee")
		frappe.db.set_default("alvoraa_org_managers_see_all", 0)
		frappe.set_user(email)
		self.assertTrue(api.reach()["unlimited"])


class TestDepthIsCappedForTheBounded(ReachCase):
	def test_a_bounded_viewer_cannot_ask_for_the_whole_tree_at_once(self):
		"""Asking for depth 20 must not return twenty levels just because the
		caller said so."""
		frappe.db.set_default("alvoraa_org_full_reach_roles", "")
		frappe.db.set_default("alvoraa_org_managers_see_all", 0)
		seats, people = self._ladder()
		self._become(people["Owner"])
		tree = api.subtree(depth=20)

		def deepest(node, d=1):
			kids = node.get("children") or []
			return max([deepest(k, d + 1) for k in kids], default=d)

		self.assertLessEqual(deepest(tree), 3)       # own level plus two down
