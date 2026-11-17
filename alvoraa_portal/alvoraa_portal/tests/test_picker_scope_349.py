"""The attendance picker offers only the people the month view will open.

**What went wrong (ALV-349).** On grace.alvoraa.co, a group HR person with no
User Permissions was scoped to the company on their own Employee record. The
month view (`_subject` -> `_refuse_outside_scope`) refused everybody outside
it, but the picker beside it (`whose_months_i_can_open`) asked only "is this
person active?". It offered 106 people and the page refused 72 of them.

**The fix.** Both now read one rule, `_scope_conditions`. These tests prove
the picker narrows the way the month view refuses, and that every person the
picker offers can be opened.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal.tests.fixtures_043 import ensure_company

HOME = "ALV349 Home Company"
OTHER = "ALV349 Other Company"
STORE_A = "ALV349 Store A"
STORE_B = "ALV349 Store B"


class PickerScopeCase(FrappeTestCase):
	"""One reviewer, colleagues in their company and branch, strangers outside."""

	# Per test, never committed, for the reason `test_decline_scope` gives.
	_slot = 0

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		# A fresh site that skipped the setup wizard has no Gender rows.
		if not frappe.db.exists("Gender", "Male"):
			frappe.get_doc({"doctype": "Gender", "gender": "Male"}).insert(
				ignore_permissions=True)
		ensure_company(HOME, "A349H")
		ensure_company(OTHER, "A349O")
		for b in (STORE_A, STORE_B):
			if not frappe.db.exists("Branch", b):
				frappe.get_doc({"doctype": "Branch", "branch": b}).insert(
					ignore_permissions=True)

	def setUp(self):
		frappe.set_user("Administrator")
		PickerScopeCase._slot += 1
		self.tag = "Pks%d" % PickerScopeCase._slot
		self.reviewer = self._login("rev")
		self.reviewer_emp = self._employee("Rev", HOME, STORE_A, user=self.reviewer)
		self.home_a = self._employee("Homea", HOME, STORE_A)
		self.home_b = self._employee("Homeb", HOME, STORE_B)
		self.home_none = self._employee("Homenone", HOME, None)
		self.other = self._employee("Other", OTHER, STORE_A)

	def tearDown(self):
		frappe.set_user("Administrator")

	# ── fixtures ────────────────────────────────────────────────────────────

	def _login(self, local):
		email = "%s.%s.a349@example.com" % (self.tag.lower(), local)
		u = frappe.get_doc({"doctype": "User", "email": email,
		                    "first_name": self.tag + local,
		                    "send_welcome_email": 0}).insert(ignore_permissions=True)
		u.add_roles("HR User")
		return email

	def _employee(self, first, company, branch, user=None):
		doc = {"doctype": "Employee", "first_name": self.tag + first,
		       "company": company, "date_of_birth": "1970-01-01",
		       "date_of_joining": "2000-01-01", "status": "Active",
		       "gender": frappe.db.get_value("Gender", {}, "name") or "Male"}
		if branch:
			doc["branch"] = branch
		if user:
			doc["user_id"] = user
			# Otherwise Frappe HR writes Employee and Company User Permissions
			# for the login, and the "no permissions" case is never tested.
			doc["create_user_permission"] = 0
		return frappe.get_doc(doc).insert(ignore_permissions=True).name

	def _permit(self, allow, value):
		frappe.get_doc({"doctype": "User Permission", "user": self.reviewer,
		                "allow": allow, "for_value": value,
		                "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)

	def _offered(self, user=None):
		frappe.set_user(user or self.reviewer)
		try:
			return {r["name"] for r in ac.whose_months_i_can_open(search=self.tag, limit=500)}
		finally:
			frappe.set_user("Administrator")

	def _all_open(self, names, user=None):
		"""Every person the picker offered opens without a refusal."""
		frappe.set_user(user or self.reviewer)
		try:
			for name in names:
				ac._subject(name)
		finally:
			frappe.set_user("Administrator")

	def _refused(self, name):
		frappe.set_user(self.reviewer)
		try:
			with self.assertRaises(frappe.PermissionError):
				ac._subject(name)
		finally:
			frappe.set_user("Administrator")

	# ── the tests ───────────────────────────────────────────────────────────

	def test_hr_with_no_permissions_is_offered_only_their_own_company(self):
		"""The whole ticket: Prasad before his access was set."""
		self.assertFalse(frappe.get_all("User Permission", {"user": self.reviewer}))
		frappe.set_user(self.reviewer)
		try:
			self.assertTrue(ac._may_review())  # prove which branch is tested
		finally:
			frappe.set_user("Administrator")
		offered = self._offered()
		self.assertIn(self.home_a, offered)
		self.assertIn(self.home_none, offered)
		self.assertNotIn(self.other, offered)
		self._all_open(offered)
		self._refused(self.other)

	def test_hr_given_both_companies_is_offered_both(self):
		"""Prasad after his access was set: four companies, all offered."""
		self._permit("Company", HOME)
		self._permit("Company", OTHER)
		offered = self._offered()
		self.assertIn(self.home_a, offered)
		self.assertIn(self.other, offered)
		self._all_open(offered)

	def test_store_hr_is_offered_only_their_branch(self):
		"""A store's HR person: no head-office staff, no other store."""
		self._permit("Branch", STORE_A)
		offered = self._offered()
		self.assertIn(self.home_a, offered)
		self.assertNotIn(self.home_b, offered)
		self.assertNotIn(self.home_none, offered)
		self.assertNotIn(self.other, offered)
		self._all_open(offered)
		self._refused(self.home_b)
		self._refused(self.home_none)

	def test_a_search_cannot_reach_outside_the_scope(self):
		"""Typing a stranger's ID gets nothing, not the stranger."""
		frappe.set_user(self.reviewer)
		try:
			self.assertEqual(ac.whose_months_i_can_open(search=self.other), [])
		finally:
			frappe.set_user("Administrator")

	def test_administrator_is_still_offered_everybody(self):
		offered = self._offered("Administrator")
		for name in (self.home_a, self.home_b, self.home_none, self.other):
			self.assertIn(name, offered)
