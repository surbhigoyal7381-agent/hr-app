"""Declining an attendance correction must be checked like approving it.

**What went wrong.** `decide()` had two halves guarded differently. Approving
calls `doc.submit()`, and Frappe's own permission check runs inside it, so the
User Permissions that fence a reviewer to their own people were applied.
Declining calls `doc.db_set()`, which checks nothing at all - and `get_doc`
above it makes no read check either. `not_yours_yet()` is asked on both paths
but only ever answers about timing and ownership, never about scope.

So anybody holding the submit permission could name any other employee's
draft, decline it, and read the employee's free-text reason back out of the
return value. Across companies and branches. Approving was never exposed. The
asymmetry was the fault.

**The fix is not a new rule.** `doc.check_permission("submit")` asks Frappe the
same question `submit()` asks, one step earlier, so decline inherits exactly
the scope approve already had. Nothing here tests a rule of our own; these
tests prove the framework is being asked.

A note on what this does NOT cover. A reviewer with no User Permission at all
is entitled to the whole site, and these tests say so rather than pretending
otherwise - that is a configuration choice, not a defect, and ALV-259 covers
the separate question of what the team page shows them.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction as ac
# Reused rather than rebuilt: the company, the Holiday List Assignment an
# Attendance Request insists on, and the one-time field install. The suite
# next door already owns all three, and a second copy would be a second
# thing to keep right.
from alvoraa_portal.tests.test_attendance_correction import (_company,
                                                             _holiday_list,
                                                             setUpModule)

REQUEST = "Attendance Request"


class DeclineScopeCase(FrappeTestCase):
	"""One reviewer fenced to a single employee, and a stranger beside them."""

	# Per test, never committed - the same reason `test_team_scope_259` gives:
	# a committed fixture survives Frappe's rollback and the next run dies on
	# "User ... is already assigned to Employee ...".
	_slot = 0

	def setUp(self):
		frappe.set_user("Administrator")
		DeclineScopeCase._slot += 1
		tag = DeclineScopeCase._slot
		self.company = _company()
		_holiday_list(self.company)

		self.mine = self._employee("Dsmine%d" % tag)
		self.stranger = self._employee("Dsstranger%d" % tag)

		# The reviewer: HR User, so `_may_review` lets them in, plus one
		# Employee User Permission naming `self.mine` and applying to
		# Attendance Request. That is the shape Frappe HR's own Employee Self
		# Service install writes, and the shape dev carries today.
		self.reviewer = self._login("Dsreviewer%d" % tag, roles=("HR User",))
		self._permit(self.reviewer, "Employee", self.mine, REQUEST)

	def tearDown(self):
		frappe.set_user("Administrator")

	# ── fixtures ────────────────────────────────────────────────────────────

	def _login(self, first, roles=()):
		email = "%s.ds@example.com" % first.lower()
		if not frappe.db.exists("User", email):
			u = frappe.get_doc({"doctype": "User", "email": email,
			                    "first_name": first,
			                    "send_welcome_email": 0}).insert(ignore_permissions=True)
			for r in roles:
				u.add_roles(r)
		return email

	def _employee(self, first):
		return frappe.get_doc({
			"doctype": "Employee", "first_name": first, "company": self.company,
			"date_of_birth": "1970-01-01", "date_of_joining": "2000-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active"}).insert(ignore_permissions=True).name

	def _permit(self, user, allow, value, applicable_for=None):
		doc = {"doctype": "User Permission", "user": user, "allow": allow,
		       "for_value": value}
		if applicable_for:
			doc["applicable_for"] = applicable_for
			doc["apply_to_all_doctypes"] = 0
		else:
			doc["apply_to_all_doctypes"] = 1
		frappe.get_doc(doc).insert(ignore_permissions=True)

	def _request(self, employee):
		"""A draft correction raised BY the employee, so the raiser is not the
		reviewer - `not_yours_yet` refuses whoever raised it, and that refusal
		would mask the one being tested here."""
		day = add_days(nowdate(), -3)
		doc = frappe.get_doc({"doctype": REQUEST, "employee": employee,
		                      "from_date": day, "to_date": day,
		                      "reason": "Forgot to Punch In",
		                      "explanation": "I was at the Sector 18 gate by 9, the reader did not beep"})
		doc.insert(ignore_permissions=True)
		return doc.name

	def _decline(self, name):
		frappe.set_user(self.reviewer)
		try:
			return ac.decide(name, approve=0, note="Not this time")
		finally:
			frappe.set_user("Administrator")

	# ── the fault ───────────────────────────────────────────────────────────

	def test_they_cannot_decline_a_stranger(self):
		"""The whole ticket. Before the fix this returned the document."""
		name = self._request(self.stranger)
		# **First prove they are a reviewer at all.** `_may_review` throws the
		# same PermissionError two lines earlier in `decide`, so a reviewer who
		# silently lost their role would make this test green while proving
		# nothing. This pins which refusal is being tested.
		frappe.set_user(self.reviewer)
		try:
			self.assertTrue(ac._may_review())
		finally:
			frappe.set_user("Administrator")
		with self.assertRaises(frappe.PermissionError):
			self._decline(name)

	def test_the_stranger_is_left_untouched(self):
		"""Not merely refused - nothing written. `db_set` wrote three fields
		before the check existed, so a refusal that still stamped the record
		would be no fix at all."""
		name = self._request(self.stranger)
		with self.assertRaises(frappe.PermissionError):
			self._decline(name)
		row = frappe.db.get_value(REQUEST, name,
		                          ["alvoraa_review_status", "alvoraa_reviewed_by",
		                           "alvoraa_review_note"], as_dict=True)
		self.assertNotEqual(row.alvoraa_review_status, "Declined")
		self.assertIsNone(row.alvoraa_reviewed_by)
		self.assertIsNone(row.alvoraa_review_note)

	def test_the_reason_does_not_come_back_in_the_refusal(self):
		"""The employee's own words were readable out of the return value. The
		refusal must carry nothing of the document.

		**Asserted against `frappe.flags.error_message`, not `str(exc)`.** A
		first version read `str(exc)`, and Frappe's `raise_no_permission_to`
		raises `frappe.PermissionError` with NO arguments - so `str(exc)` is
		always the empty string and both assertions passed whatever the code
		did. The sentence goes into `frappe.flags.error_message`, which is what
		reaches the client, so that is what has to be checked.
		"""
		name = self._request(self.stranger)
		frappe.flags.error_message = None
		with self.assertRaises(frappe.PermissionError):
			self._decline(name)
		carried = frappe.flags.error_message or ""
		self.assertNotIn("Sector 18 gate", carried)
		self.assertNotIn("the reader did not beep", carried)
		# And nothing of the employee either - the refusal names the doctype and
		# the request, which the caller already typed, and stops there.
		self.assertNotIn(self.stranger, carried)

	# ── and the half that already worked ───────────────────────────────────

	def test_approving_a_stranger_was_already_refused(self):
		"""Proves the asymmetry this fix closes, rather than assuming it:
		approve went through `submit()`, which ran this check all along."""
		name = self._request(self.stranger)
		frappe.set_user(self.reviewer)
		try:
			with self.assertRaises(frappe.PermissionError):
				ac.decide(name, approve=1)
		finally:
			frappe.set_user("Administrator")

	# ── and the person they really do look after ───────────────────────────

	def test_they_can_still_decline_their_own_person(self):
		"""The fix must not cost the reviewer the work they are there to do."""
		name = self._request(self.mine)
		out = self._decline(name)
		self.assertEqual(out["state"], "declined")
		self.assertEqual(
			frappe.db.get_value(REQUEST, name, "alvoraa_reviewed_by"), self.reviewer)

	def test_a_note_is_still_required(self):
		"""The check runs before the note check, so a missing note must still
		be the thing the reviewer is told about - not a permission error."""
		name = self._request(self.mine)
		frappe.set_user(self.reviewer)
		try:
			with self.assertRaises(frappe.ValidationError):
				ac.decide(name, approve=0, note="   ")
		finally:
			frappe.set_user("Administrator")

	def test_an_unfenced_reviewer_is_unchanged(self):
		"""Nobody loses anything they had. A reviewer with no User Permission
		is entitled to the whole site, and the new line asks Frappe, so it
		answers yes - which is what every HR login on dev, dtc, grace and aahr
		gets today (Surbhi, 31 Oct 2026: none hold such a permission)."""
		free = self._login("Dsfree%d" % DeclineScopeCase._slot, roles=("HR User",))
		name = self._request(self.stranger)
		frappe.set_user(free)
		try:
			out = ac.decide(name, approve=0, note="Fine by me")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(out["state"], "declined")

	# ── the half Frappe cannot answer (ALV-269 F1) ──────────────────────────
	#
	# Everything above turns on the tenant having a User Permission. None of our
	# tenants do, so on dev, dtc, grace and aahr the checks above never refuse
	# anybody - which is why the first version of this fix closed the asymmetry
	# between approve and decline without closing the exposure. These tests are
	# about the entitlement the HR QUEUE is already narrowed by: the company on
	# the reviewer's own Employee record.

	def _hr_with_a_company(self, tag):
		"""An HR reviewer the ordinary way: a login, an Employee record, no
		User Permission that reaches Attendance Request. `permitted_companies`
		answers from their Employee record, exactly as it does in production."""
		email = self._login("Dsco%d" % tag, roles=("HR User",))
		frappe.get_doc({
			"doctype": "Employee", "first_name": "Dsco%d" % tag,
			"company": self.company, "user_id": email,
			"date_of_birth": "1970-01-01", "date_of_joining": "2000-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active"}).insert(ignore_permissions=True)
		# **Frappe HR adds an Employee User Permission for a linked login**, and it
		# applies to Attendance Request - so Frappe would fence this reviewer to
		# their own record and refuse them at the FIRST check, before the company
		# question these tests are about. That fence is real and desirable; it is
		# simply not what is under test here. Removing it models the login ERPNext
		# never gave one to - a user linked by a script or a direct write, which
		# the 076 C notes record as existing on real tenants.
		for up in frappe.get_all("User Permission", filters={"user": email},
		                         pluck="name"):
			frappe.delete_doc("User Permission", up, ignore_permissions=True,
			                  force=True)
		frappe.clear_cache(user=email)
		return email

	def _other_company_employee(self, tag):
		name = "ALV269 Other Co %d" % tag
		if not frappe.db.exists("Company", name):
			frappe.get_doc({"doctype": "Company", "company_name": name,
			                "default_currency": "INR", "country": "India",
			                "abbr": "A269X%d" % tag}).insert(ignore_permissions=True)
		_holiday_list(name)
		return frappe.get_doc({
			"doctype": "Employee", "first_name": "Dsother%d" % tag,
			"company": name, "date_of_birth": "1970-01-01",
			"date_of_joining": "2000-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active"}).insert(ignore_permissions=True).name

	def test_hr_cannot_decline_another_companys_employee(self):
		"""THE REAL EXPOSURE. Frappe says yes - no User Permission stops this
		login - so only our own entitlement refuses it."""
		tag = DeclineScopeCase._slot
		hr = self._hr_with_a_company(tag)
		outs = self._other_company_employee(tag)
		name = self._request(outs)
		frappe.set_user(hr)
		try:
			with self.assertRaises(frappe.PermissionError):
				ac.decide(name, approve=0, note="No")
		finally:
			frappe.set_user("Administrator")
		self.assertNotEqual(
			frappe.db.get_value(REQUEST, name, "alvoraa_review_status"), "Declined")

	def test_hr_can_still_decline_inside_their_own_company(self):
		"""The same reviewer, their own company. Nothing is taken away."""
		tag = DeclineScopeCase._slot
		hr = self._hr_with_a_company(tag)
		name = self._request(self.stranger)
		frappe.set_user(hr)
		try:
			out = ac.decide(name, approve=0, note="Not this time")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(out["state"], "declined")

	# ── and the reviewer is told, and it is written down (ALV-269 F2) ───────

	def test_the_refusal_is_a_sentence_not_a_blank_error(self):
		"""`check_permission` raises PermissionError with no message, and nothing
		on the client reads the field Frappe puts the sentence into - the reviewer
		saw "Something went wrong at the office". The message must reach them."""
		tag = DeclineScopeCase._slot
		hr = self._hr_with_a_company(tag)
		name = self._request(self._other_company_employee(tag))
		frappe.clear_messages()
		frappe.set_user(hr)
		try:
			with self.assertRaises(frappe.PermissionError):
				ac.decide(name, approve=0, note="No")
		finally:
			frappe.set_user("Administrator")
		said = " ".join(m.get("message", "") for m in frappe.message_log)
		self.assertIn("outside the companies and branches", said)
		# And it still gives nothing of the employee away.
		self.assertNotIn("Sector 18 gate", said)

	def test_the_refusal_is_written_down(self):
		"""SEC-17: one structured line per refusal, so misuse can be found
		later. The refusal that catches this probe used to leave no trace."""
		# Patched by NAME, not through `from hrms.alvoraa_hr_core import access`.
		# That import form is the one `check_app_integrity` rejects, and
		# `run-tests` does not catch it - the tests passed and the check failed.
		tag = DeclineScopeCase._slot
		hr = self._hr_with_a_company(tag)
		name = self._request(self._other_company_employee(tag))
		frappe.set_user(hr)
		try:
			with patch("hrms.alvoraa_hr_core.access.log_refusal") as logged:
				with self.assertRaises(frappe.PermissionError):
					ac.decide(name, approve=0, note="No")
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(logged.called, "the refusal was not logged")
		args = logged.call_args[0]
		self.assertEqual(args[0], "SEC-17")
		self.assertEqual(args[1], "attendance_correction.decide")
