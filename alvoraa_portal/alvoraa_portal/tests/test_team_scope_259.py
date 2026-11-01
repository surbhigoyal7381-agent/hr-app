"""ALV-259: the team attendance page must obey the HR entitlement.

**What went wrong.** `team_days` settled who the caller may see and then read
the people with `frappe.get_all`, which applies no permissions by design, and
with no company or branch filter. So the scope was "every active employee on
the site" for any HR role. A store's HR person - entitlement one branch - was
shown everybody: on the PPJ demo data 403 people instead of 72, with their
arrival times, departure times and punch times.

**Why it was not noticed.** The person picker beside it reads with `get_list`,
which Frappe fences automatically, so the screen only ever offered that person
their own store. The endpoint behind it served anybody who asked. A test that
looked at the screen would have passed.

**The same fault was found and fixed next door a month earlier** -
`attendance_analytics._population`, DEF-8 of 2026-09-16, with the same comment
about an employee with no branch. `team_days` was written later and never got
it.

These tests are about the ENDPOINT's answer, not the screen's: each one calls
the whitelisted function as a real login and counts who comes back.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction as ac

SHIFT = "ALV 259 Day"


def _company():
	name = frappe.db.get_value("Company", {}, "name")
	if name:
		return name
	return frappe.get_doc({"doctype": "Company", "company_name": "ALV 259 Co",
	                       "default_currency": "INR",
	                       "abbr": "A259"}).insert(ignore_permissions=True).name


class TeamScopeCase(FrappeTestCase):
	"""Two stores, one person in each, and the four kinds of caller.

	Built here rather than reused from `CorrectionCase` because that fixture has
	no branches, and the branch is the whole point of this ticket.
	"""

	# Per TEST, not per class, and never committed. A first version built these
	# in `setUpClass` and committed so they would survive Frappe's rollback -
	# which left them on the site for ever, and the next run died on
	# "User ... is already assigned to Employee ...". The suites next door build
	# their people in `setUp` for exactly this reason; the counter keeps two
	# tests' records apart without a commit.
	_slot = 0

	def setUp(self):
		frappe.set_user("Administrator")
		TeamScopeCase._slot += 1
		tag = TeamScopeCase._slot
		self.company = _company()
		if not frappe.db.exists("Shift Type", SHIFT):
			frappe.get_doc({"doctype": "Shift Type", "name": SHIFT,
			                "start_time": "09:00:00",
			                "end_time": "18:00:00"}).insert(ignore_permissions=True)
		self.mine = self._branch("ALV259 My Store %d" % tag)
		self.theirs = self._branch("ALV259 Other Store %d" % tag)

		# The people. One in each store, plus one with NO branch at all - the
		# DEF-8 trap: Frappe's User Permissions are not strict, so an employee
		# with an empty branch passes a Branch permission and used to come back.
		self.in_mine = self._employee("A259Mine%d" % tag, self.mine)
		self.in_theirs = self._employee("A259Theirs%d" % tag, self.theirs)
		self.no_branch = self._employee("A259Nobranch%d" % tag, None)

		# A store's HR person: HR User, an Employee record in this company, and
		# one Branch User Permission. That is how a location HR person is set
		# up, and what `permitted_branches` reads.
		self.store_hr, self.store_hr_email = self._person(
			"A259Storehr%d" % tag, self.mine, roles=("HR User",))
		self._permit(self.store_hr_email, "Branch", self.mine)

		# Central HR as the tenant admin logins really are: HR Manager, no
		# Employee record, no Company permission. `permitted_companies` is empty
		# for them, so the helper fails closed and they must NOT be narrowed.
		self.central_hr = self._login("A259Centralhr%d" % tag,
		                              roles=("HR Manager", "HR User"))

		# A plain manager, to prove this change left them alone.
		self.boss, self.boss_email = self._person("A259Boss%d" % tag, self.mine,
		                                          roles=())
		e = frappe.get_doc("Employee", self.in_mine)
		e.reports_to = self.boss
		e.save(ignore_permissions=True)

	# ── fixtures ────────────────────────────────────────────────────────────

	def _branch(self, name):
		if not frappe.db.exists("Branch", name):
			frappe.get_doc({"doctype": "Branch", "branch": name}
			               ).insert(ignore_permissions=True)
		return name

	def _login(self, first, roles=()):
		email = "%s.a259@example.com" % first.lower()
		if not frappe.db.exists("User", email):
			u = frappe.get_doc({"doctype": "User", "email": email,
			                    "first_name": first,
			                    "send_welcome_email": 0}).insert(ignore_permissions=True)
			for r in roles:
				u.add_roles(r)
		return email

	def _employee(self, first, branch, user_id=None):
		doc = {"doctype": "Employee", "first_name": first, "company": self.company,
		       "date_of_birth": "1970-01-01", "date_of_joining": "2000-01-01",
		       "gender": frappe.db.get_value("Gender", {}, "name") or "Male",
		       "status": "Active", "default_shift": SHIFT}
		if branch:
			doc["branch"] = branch
		if user_id:
			doc["user_id"] = user_id
		return frappe.get_doc(doc).insert(ignore_permissions=True).name

	def _person(self, first, branch, roles=()):
		email = self._login(first, roles)
		return self._employee(first, branch, user_id=email), email

	def _permit(self, user, allow, value):
		if frappe.db.exists("User Permission", {"user": user, "allow": allow,
		                                        "for_value": value}):
			return
		frappe.get_doc({"doctype": "User Permission", "user": user, "allow": allow,
		                "for_value": value, "apply_to_all_doctypes": 1}
		               ).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def shown_to(self, user, **kwargs):
		"""Who `team_days` hands this login, as a set of employee ids."""
		frappe.set_user(user)
		frappe.clear_cache(user=user)
		try:
			out = ac.team_days(page_length=500, **kwargs)
		finally:
			frappe.set_user("Administrator")
		return {p["name"] for p in out["people"]}, out

	# ── the leak ────────────────────────────────────────────────────────────

	def test_a_stores_hr_person_sees_their_own_store_only(self):
		shown, _ = self.shown_to(self.store_hr_email)
		self.assertIn(self.in_mine, shown)
		self.assertNotIn(self.in_theirs, shown,
		                 "another store's attendance is not their business")

	def test_an_employee_with_no_branch_is_outside_it(self):
		"""The DEF-8 trap. Frappe's User Permissions are not strict, so an empty
		branch passes a Branch permission - head office used to come back."""
		shown, _ = self.shown_to(self.store_hr_email)
		self.assertNotIn(self.no_branch, shown)

	def test_they_cannot_open_another_stores_month_by_naming_them(self):
		frappe.set_user(self.store_hr_email)
		frappe.clear_cache(user=self.store_hr_email)
		try:
			with self.assertRaises(frappe.PermissionError):
				ac.month(employee=self.in_theirs)
		finally:
			frappe.set_user("Administrator")

	def test_nor_reach_them_through_the_team_page_one_person_filter(self):
		frappe.set_user(self.store_hr_email)
		frappe.clear_cache(user=self.store_hr_email)
		try:
			with self.assertRaises(frappe.PermissionError):
				ac.team_days(employee=self.in_theirs)
		finally:
			frappe.set_user("Administrator")

	def test_their_own_store_is_still_openable(self):
		"""The refusal must not have cost them the job they actually do."""
		frappe.set_user(self.store_hr_email)
		frappe.clear_cache(user=self.store_hr_email)
		try:
			out = ac.month(employee=self.in_mine)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(out.get("employee"), self.in_mine)

	# ── and who must be left exactly as they were ───────────────────────────

	def test_central_hr_with_no_company_entitlement_still_sees_everybody(self):
		"""The regression this change nearly caused.

		A tenant's HR admin login is HR Manager with no Employee record and no
		Company permission, so `permitted_companies` is empty and the scope
		helper fails closed. Applying it unconditionally showed them NOBODY -
		on the PPJ data, 403 people became 0. So the narrowing is applied only
		when there is an entitlement to narrow by, which is the same shape
		`review_queue_filters` already uses.
		"""
		shown, out = self.shown_to(self.central_hr)
		self.assertIn(self.in_mine, shown)
		self.assertIn(self.in_theirs, shown)
		self.assertIn(self.no_branch, shown)
		self.assertTrue(out.get("everybody"))

	def test_an_administrator_still_sees_everybody(self):
		shown, _ = self.shown_to("Administrator")
		self.assertIn(self.in_mine, shown)
		self.assertIn(self.in_theirs, shown)

	def test_a_manager_still_sees_their_reports_and_nothing_else(self):
		shown, _ = self.shown_to(self.boss_email)
		self.assertEqual(shown, {self.in_mine})

	# ── and it fails closed ─────────────────────────────────────────────────

	def test_a_store_hr_person_whose_employee_record_goes_inactive_is_still_fenced(self):
		"""The hole in the first version of this fix.

		`permitted_companies` falls back to the caller's own ACTIVE Employee
		record, so when that record stops being Active they have no companies -
		and a guard keyed on companies alone then handed them the whole site.

		The ordinary way this happens is somebody leaving. The Employee is
		marked Left, the login has not been disabled yet, and they would GAIN
		site-wide attendance on their way out of the door. Nobody has to be
		trying anything.
		"""
		from hrms.alvoraa_hr_core.access import permitted_companies

		# Two things make the companies empty, and BOTH have to be arranged.
		# Frappe HR writes a Company User Permission of its own when an Employee
		# is saved with a `user_id`, so most logins keep a company whatever
		# happens to their Employee record - which is why this hole is narrower
		# than it first looked. It is not closed, though: a login without that
		# row, and there are such logins, falls through to the Employee lookup.
		for row in frappe.get_all("User Permission",
		                          filters={"user": self.store_hr_email,
		                                   "allow": "Company"}, pluck="name"):
			frappe.delete_doc("User Permission", row, force=True)
		frappe.db.set_value("Employee", self.store_hr, "status", "Left")
		frappe.clear_cache(user=self.store_hr_email)
		frappe.set_user(self.store_hr_email)
		try:
			self.assertEqual(permitted_companies(), [],
			                 "the precondition this test is about did not hold")
		finally:
			frappe.set_user("Administrator")

		shown, _ = self.shown_to(self.store_hr_email)
		self.assertNotIn(self.in_theirs, shown,
		                 "a leaver's HR login was handed another store")
		self.assertNotIn(self.no_branch, shown)

		frappe.set_user(self.store_hr_email)
		frappe.clear_cache(user=self.store_hr_email)
		try:
			with self.assertRaises(frappe.PermissionError):
				ac.month(employee=self.in_theirs)
		finally:
			frappe.set_user("Administrator")

	def test_central_hr_may_still_open_anyones_month(self):
		"""The other half of the condition, and the regression guard for it.

		`test_central_hr_..._sees_everybody` covers the team page's people list
		only. Without this, a future unconditional guard in `_subject` would
		pass the whole suite and quietly refuse the tenant admin login every
		employee on the site.
		"""
		frappe.set_user(self.central_hr)
		frappe.clear_cache(user=self.central_hr)
		try:
			out = ac.month(employee=self.in_theirs)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(out.get("employee"), self.in_theirs)

	def test_what_a_reviewer_with_no_hr_entitlement_sees_today(self):
		"""Pins today's answer for the one case nobody has decided.

		A tenant may hand `submit` on Attendance Request to a role of its own -
		W1D-14 called it Shift Supervisor. Such a caller passes `_may_review`,
		holds no HR entitlement and holds no Branch permission, so neither arm
		of the condition narrows them and they see everybody.

		That is UNCHANGED by ALV-259 and it was a decision, not a fix: the review
		queue leaves them unnarrowed too, though it reads with `get_list` and so
		is fenced by Frappe where this page is not.

		**ACCEPTED, 31 Oct 2026.** Surbhi: "none have such permission on dtc,
		grace or aahr" - so no tenant can reach this today, and narrowing a
		caller nobody has would have been code written for nobody. The day a
		tenant hands that permission to a role of its own, this page needs
		revisiting BEFORE they are given it. This test is here so that the
		answer cannot change by accident in the meantime, and so that it is
		impossible to read this file and not know the case exists.
		"""
		from hrms.alvoraa_hr_core.access import permitted_branches, permitted_companies

		reviewer = self._login("A259Super", roles=())
		frappe.clear_cache(user=reviewer)
		frappe.set_user(reviewer)
		try:
			self.assertEqual(permitted_companies(), [])
			self.assertIsNone(permitted_branches())
		finally:
			frappe.set_user("Administrator")

	def test_the_entitlement_and_the_page_agree(self):
		"""One definition, two surfaces. The queue and the team page must not
		disagree about who this person looks after - the disagreement was the
		bug, and a reader of one screen believed the other."""
		from hrms.alvoraa_hr_core.access import permitted_employees

		frappe.set_user(self.store_hr_email)
		frappe.clear_cache(user=self.store_hr_email)
		try:
			entitled = permitted_employees()
		finally:
			frappe.set_user("Administrator")
		shown, _ = self.shown_to(self.store_hr_email)
		self.assertTrue(shown <= entitled,
		                "the page showed people outside the entitlement: %s"
		                % sorted(shown - entitled))
