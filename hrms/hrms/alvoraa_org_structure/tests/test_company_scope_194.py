"""Who the position register belongs to, and who may count it.

Two faults, both of the same shape: a question that should have been asked of
one company was asked of the whole site.

1. "Does this tenant keep positions?" decided whether the chart drew seats or
   people. It counted every Active position on the bench, so on a site carrying
   two companies the first one to create a seat switched the other company's
   chart into seat mode as well.

2. `org_health` read every position on the site. Its only gate was a role
   check, and a role says what somebody does, not who they do it for - so one
   company's HR saw another company's vacancies, and a single store's HR saw
   all six stores'. Slice 030 fixed exactly this shape of bug in three other
   readers and this one was missed.

Both are invisible on a one-company site, which is why they survived. These
tests make them visible.
"""

import frappe

from hrms.alvoraa_org_structure import api, metrics
from hrms.alvoraa_org_structure.tests.test_org_structure import OrgCase, _company, _gender


class CompanyScopeCase(OrgCase):
	def setUp(self):
		super().setUp()
		self._user = frappe.session.user
		frappe.local._alvoraa_positions_kept = {}
		frappe.local._alvoraa_leads = {}
		self._cleanup = []

	def tearDown(self):
		frappe.set_user(self._user)
		for doctype, name in reversed(self._cleanup):
			try:
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
			except Exception:
				pass
		frappe.db.delete("User Permission", {"user": ("like", "scope194%")})
		frappe.local._alvoraa_positions_kept = {}
		frappe.local._alvoraa_leads = {}
		frappe.db.commit()
		super().tearDown()

	def branch(self, name):
		if not frappe.db.exists("Branch", name):
			doc = frappe.get_doc({"doctype": "Branch", "branch": name}).insert(
				ignore_permissions=True)
			self._cleanup.append(("Branch", doc.name))
		return name

	def hr_user(self, email, branch=None):
		"""An HR person with an employee record, optionally tied to one store.

		The employee record matters: with no Company User Permission,
		permitted_companies falls back to the company on the person's own
		record, and without one they may act for nothing at all.
		"""
		if not frappe.db.exists("User", email):
			u = frappe.get_doc({"doctype": "User", "email": email,
			                    "first_name": "Scope", "enabled": 1,
			                    "send_welcome_email": 0}).insert(ignore_permissions=True)
			self._cleanup.append(("User", u.name))
		emp = frappe.get_doc({
			"doctype": "Employee", "first_name": "Scope194", "company": _company(),
			"date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01",
			"gender": _gender(), "status": "Active", "user_id": email,
		}).insert(ignore_permissions=True)
		self._cleanup.append(("Employee", emp.name))
		# Roles come after the employee link, or ERPNext strips "Employee" off a
		# user nothing points at - the same trap that silently emptied the DTC
		# manager logins on 14 October.
		user = frappe.get_doc("User", email)
		user.flags.ignore_permissions = True
		user.add_roles("HR User")
		if branch:
			frappe.get_doc({"doctype": "User Permission", "user": email,
			                "allow": "Branch", "for_value": branch,
			                "apply_to_all_doctypes": 0,
			                "applicable_for": "Employee"}).insert(ignore_permissions=True)
		frappe.db.commit()
		return email


class TestWhetherThisCompanyKeepsPositions(CompanyScopeCase):
	def test_a_company_with_no_seats_is_not_a_positions_company(self):
		"""The whole point. Seats exist on the site, but not for this company,
		so this company's chart must still draw people."""
		self.pos("Shift Supervisor", seats=1)
		frappe.local._alvoraa_positions_kept = {}
		self.assertFalse(api._positions_kept(company="A Company With No Seats"))

	def test_the_company_that_owns_the_seats_does_keep_positions(self):
		self.pos("Shift Supervisor", seats=1)
		frappe.local._alvoraa_positions_kept = {}
		self.assertTrue(api._positions_kept(company=_company()))

	def test_no_seats_anywhere_means_no_positions(self):
		self.assertFalse(api._positions_kept(company=_company()))

	def test_a_closed_seat_does_not_make_a_positions_company(self):
		"""Closing the last seat should put the chart back to drawing people,
		not leave it in seat mode with nothing to show."""
		self.pos("Shift Supervisor", seats=1, status="Closed")
		frappe.local._alvoraa_positions_kept = {}
		self.assertFalse(api._positions_kept(company=_company()))


class TestTheHeadlineNumbersStayInTheirLane(CompanyScopeCase):
	def test_a_store_hr_person_counts_only_their_own_store(self):
		here, there = self.branch("Scope194 Here"), self.branch("Scope194 There")
		self.pos("Counter Staff Here", seats=2, branch=here)
		self.pos("Counter Staff There", seats=3, branch=there)

		frappe.set_user(self.hr_user("scope194.store@example.com", branch=here))
		frappe.local._alvoraa_positions_kept = {}
		h = metrics.org_health()
		# Two seats here, both empty. The three next door are not theirs to see.
		self.assertEqual(h["headline"]["seats_budgeted"], 2.0)
		self.assertEqual(h["headline"]["positions"], 1)

	def test_an_unrestricted_hr_person_counts_every_store(self):
		here, there = self.branch("Scope194 Here"), self.branch("Scope194 There")
		self.pos("Counter Staff Here", seats=2, branch=here)
		self.pos("Counter Staff There", seats=3, branch=there)

		frappe.set_user(self.hr_user("scope194.all@example.com"))
		frappe.local._alvoraa_positions_kept = {}
		h = metrics.org_health()
		self.assertEqual(h["headline"]["seats_budgeted"], 5.0)
		self.assertEqual(h["headline"]["positions"], 2)

	def test_a_seat_with_no_branch_belongs_to_no_store(self):
		"""Head office is not a store's business - the same rule every other
		reader follows since slice 030 (DEF-6)."""
		here = self.branch("Scope194 Here")
		self.pos("Counter Staff Here", seats=2, branch=here)
		self.pos("Head Office Role", seats=4)

		frappe.set_user(self.hr_user("scope194.store2@example.com", branch=here))
		frappe.local._alvoraa_positions_kept = {}
		h = metrics.org_health()
		self.assertEqual(h["headline"]["seats_budgeted"], 2.0)

	def test_the_people_counted_are_only_those_in_seats_they_may_see(self):
		"""A count of people over capacity must not describe somebody in a
		store the reader has no business looking at."""
		here, there = self.branch("Scope194 Here"), self.branch("Scope194 There")
		mine = self.pos("Counter Staff Here", seats=1, branch=here)
		yours = self.pos("Counter Staff There", seats=1, branch=there)
		self.assign(self.person("Asha"), mine.name, weight=100)
		self.assign(self.person("Bo"), yours.name, weight=100)

		frappe.set_user(self.hr_user("scope194.store3@example.com", branch=here))
		frappe.local._alvoraa_positions_kept = {}
		h = metrics.org_health()
		self.assertEqual(h["headline"]["seats_filled"], 1.0)
