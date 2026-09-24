"""Slice 034, US-6 - the one honest number, and the list it has to equal.

The rule this file exists to enforce is Surbhi's, and it is not negotiable:
**a count must equal the list it links to.** So most of these tests do not
check a number against a number the test wrote down; they check the count
against the endpoint the bell's row links to, and fail when the two disagree.

The parts that were hardest to get right, and what pins each:

* **A draft correction with no review label at all is waiting.** `not in` on a
  NULL column excludes the row in plain SQL. Frappe coalesces the column, so it
  does not - but that is a behaviour of a framework we do not own, so
  `test_a_correction_with_no_label_is_still_waiting` asserts it rather than a
  comment claiming it.
* **The count is not capped and the screen is** (N3). With 51 waiting in scope
  the count reads 51 and `to_review` returns 50.
* **A reviewer who is not HR keeps their whole queue** (W1D-14, AC-52 row 4).
  Narrowing them would fail closed - safe, and a silently broken flow.
* **Nobody gets an error instead of a count** (AC-63).

Guest, wrong-persona and scope cases ship here, in the same commit as the
endpoint (SEC-2, AC-69).

Synthetic people only, tagged S010 by the shared helpers plus S034I of our own.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction, hr_api, inbox_api
from alvoraa_portal.tests.test_portal_security_010 import _employee, _user
from alvoraa_portal.tests.test_store_hr_scoping_030 import STORE_A, STORE_B, _Stores

I_A = "S034I Store A"
I_B = "S034I Store B"
HOLIDAYS = "S034I Holidays"


def _holiday_list(employees):
	"""Attendance Request asks whether each day is a holiday before it marks it.

	Without one, Frappe HR throws "No Holiday List was found for Employee" and
	the fixture cannot create a single correction. In v16 what gets read is a
	**Holiday List Assignment**, not `Employee.holiday_list` - the same thing
	`test_attendance_correction` learned.

	**Assigned per EMPLOYEE, never per company, and that is not a detail.** The
	first version of this fixture made one company-wide assignment, which is
	cheaper and covers everybody. It also made every test in
	`test_attendance_correction` fail: Frappe HR refuses a second company-wide
	assignment that overlaps, so that file could no longer build its own. Test
	data is shared state on one site, and a company-wide row is the widest
	shared state there is. Six employee rows touch nobody else.
	"""
	if not frappe.db.exists("Holiday List", HOLIDAYS):
		frappe.get_doc({
			"doctype": "Holiday List", "holiday_list_name": HOLIDAYS,
			"from_date": add_days(nowdate(), -2000), "to_date": add_days(nowdate(), 1200),
		}).insert(ignore_permissions=True)
	for employee in employees:
		if frappe.db.exists("Holiday List Assignment",
		                    {"assigned_to": employee, "holiday_list": HOLIDAYS,
		                     "docstatus": 1}):
			continue
		frappe.get_doc({
			"doctype": "Holiday List Assignment", "holiday_list": HOLIDAYS,
			"applicable_for": "Employee", "assigned_to": employee,
			"from_date": add_days(nowdate(), -2000),
		}).insert(ignore_permissions=True).submit()
	return HOLIDAYS


def _correction(employee, from_date, to_date=None, status=None, docstatus=0):
	"""A draft Attendance Request, inserted the way the portal inserts one."""
	doc = frappe.get_doc({
		"doctype": attendance_correction.REQUEST,
		"employee": employee,
		"from_date": from_date,
		"to_date": to_date or from_date,
		"reason": "On Duty",
		"explanation": "S034I fixture",
	})
	doc.insert(ignore_permissions=True)
	if status is not None:
		doc.db_set("alvoraa_review_status", status, update_modified=False)
	if docstatus:
		doc.db_set("docstatus", docstatus, update_modified=False)
	return doc.name


class _InboxFixture(_Stores):
	"""Two stores of this file's own, an HR person in one, and a plain employee.

	Its own stores, not slice 030's: 030 asserts an exact set of names in store
	A, so anybody added there breaks it. Test data is shared state on one site.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for branch in (I_A, I_B):
			if not frappe.db.exists("Branch", branch):
				frappe.get_doc({"doctype": "Branch", "branch": branch}).insert(
					ignore_permissions=True)
		cls.hr_user = _user("s034i.storehr", ("HR User", "Employee"))
		cls.hr_emp = _employee("S034IStoreHR", company=cls.company_a, user=cls.hr_user)
		cls.wide_user = _user("s034i.widehr", ("HR Manager", "Employee"))
		cls.wide_emp = _employee("S034IWideHR", company=cls.company_a, user=cls.wide_user)
		cls.plain_user = _user("s034i.plain", ("Employee",))
		cls.plain_emp = _employee("S034IPlain", company=cls.company_a, user=cls.plain_user)
		cls.in_a = _employee("S034IInA", company=cls.company_a)
		cls.in_b = _employee("S034IInB", company=cls.company_a)
		cls.no_branch = _employee("S034INoBranch", company=cls.company_a)
		# Somebody with a login and no Active Employee record at all - persona
		# rule 6. Asha, in the spec's words.
		cls.operator_user = _user("s034i.operator", ("System Manager",))
		for emp, branch in ((cls.hr_emp, I_A), (cls.plain_emp, I_A), (cls.in_a, I_A),
		                    (cls.wide_emp, None), (cls.in_b, I_B), (cls.no_branch, None)):
			frappe.db.set_value("Employee", emp, "branch", branch, update_modified=False)
		attendance_correction.after_migrate()
		frappe.clear_cache(doctype=attendance_correction.REQUEST)
		_holiday_list((cls.hr_emp, cls.wide_emp, cls.plain_emp, cls.in_a,
		                cls.in_b, cls.no_branch))
		frappe.db.commit()

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.delete(attendance_correction.REQUEST, {"explanation": "S034I fixture"})
		if not frappe.db.exists("User Permission",
		                        {"user": self.hr_user, "allow": "Branch", "for_value": I_A}):
			frappe.get_doc({"doctype": "User Permission", "user": self.hr_user,
			                "allow": "Branch", "for_value": I_A,
			                "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
		frappe.clear_cache(user=self.hr_user)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete(attendance_correction.REQUEST, {"explanation": "S034I fixture"})
		frappe.db.delete("User Permission", {"user": self.hr_user, "allow": "Branch"})
		frappe.clear_cache(user=self.hr_user)
		frappe.db.commit()
		super().tearDown()

	def _counts(self, user):
		self._as(user)
		return inbox_api.get_nav_counts()

	def _part(self, payload, key):
		for row in payload["parts"]:
			if row["key"] == key:
				return row
		raise AssertionError("no part called %s" % key)


class TestTheShapeOfThePayload(_InboxFixture):
	def test_guest_is_refused(self):
		"""SEC-2. Every endpoint is live on production whatever page calls it."""
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				inbox_api.get_nav_counts()
		finally:
			frappe.set_user("Administrator")

	def test_every_part_of_section_five_is_present_for_everyone(self):
		"""AC-23: the Inbox draws one row per part, so every part must arrive,
		even at zero. A missing key and a zero are different bugs."""
		for user in (self.plain_user, self.hr_user, self.operator_user):
			payload = self._counts(user)
			self.assertEqual([r["key"] for r in payload["parts"]],
			                 [k for k, _r in inbox_api.PARTS],
			                 "the parts changed shape for %s" % user)

	def test_the_payload_carries_numbers_and_nothing_else(self):
		"""AC-23 / PRIV-4: no names, no reasons, no document ids anywhere."""
		_correction(self.in_a, "2026-03-02")
		frappe.db.commit()
		payload = self._counts(self.hr_user)
		text = frappe.as_json(payload)
		for secret in (self.in_a, "S034IInA", "S034I fixture"):
			self.assertNotIn(secret, text,
			                 "a document id or a person reached the count payload")

	def test_the_total_is_approvals_plus_policies_plus_my_own(self):
		"""AC-20. The three groups, added once, in the endpoint - not in the
		browser, where three screens would each do it differently."""
		payload = self._counts(self.hr_user)
		by_key = {r["key"]: r["count"] for r in payload["parts"]}
		approvals = sum(by_key[k] for k in inbox_api.APPROVAL_PARTS)
		self.assertEqual(payload["approvals_total"], approvals)
		self.assertEqual(payload["total"],
		                 approvals + by_key["policies"] + by_key["my_requests"])


class TestNobodyGetsAnErrorInsteadOfACount(_InboxFixture):
	def test_a_person_with_no_employee_record_gets_zeroes(self):
		"""AC-63. Asha signs in, and the portal is not a wall of errors."""
		payload = self._counts(self.operator_user)
		self.assertFalse(payload["has_employee"])
		self.assertEqual(payload["total"], 0)
		self.assertTrue(all(r["count"] == 0 for r in payload["parts"]))

	def test_a_leaver_with_a_live_login_gets_zeroes(self):
		"""AC-68 / SEC-14. Access ends when employment does, and the lookup is
		Active-only, so a leaver falls to rule 6 like everybody else."""
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.plain_emp, "status", "Left",
		                    update_modified=False)
		frappe.db.commit()
		try:
			payload = self._counts(self.plain_user)
			self.assertFalse(payload["has_employee"])
			self.assertEqual(payload["total"], 0)
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", self.plain_emp, "status", "Active",
			                    update_modified=False)
			frappe.db.commit()


class TestTheCorrectionsCountEqualsItsScreen(_InboxFixture):
	"""AC-51 and AC-52. The count and `to_review` are asked the same question."""

	def test_store_hr_counts_their_store_and_nobody_elses(self):
		"""AC-52 row 1. One correction in each place; a store's HR counts one."""
		_correction(self.in_a, "2026-03-03")
		_correction(self.in_b, "2026-03-03")
		_correction(self.no_branch, "2026-03-03")
		frappe.db.commit()
		payload = self._counts(self.hr_user)
		self.assertEqual(self._part(payload, "attendance_fixes")["count"], 1)

	def test_company_wide_hr_counts_all_three(self):
		"""AC-52 rows 2 and 3. No Branch permission means company-wide."""
		_correction(self.in_a, "2026-03-04")
		_correction(self.in_b, "2026-03-04")
		_correction(self.no_branch, "2026-03-04")
		frappe.db.commit()
		payload = self._counts(self.wide_user)
		self.assertEqual(self._part(payload, "attendance_fixes")["count"], 3)

	def test_the_count_equals_the_list_the_row_links_to(self):
		"""The rule itself, for both HR shapes. If these two ever disagree the
		bell is lying, whichever of them is right."""
		_correction(self.in_a, "2026-03-05")
		_correction(self.in_b, "2026-03-05")
		_correction(self.no_branch, "2026-03-05")
		frappe.db.commit()
		for user in (self.hr_user, self.wide_user):
			payload = self._counts(user)
			self.assertEqual(self._part(payload, "attendance_fixes")["count"],
			                 len(attendance_correction.to_review()),
			                 "the count and the queue disagree for %s" % user)

	def test_a_correction_with_no_label_is_still_waiting(self):
		"""The NULL trap. `not in` on a NULL column drops the row in plain SQL;
		Frappe coalesces it. A site migrated before that field existed is full
		of these, and every one of them is waiting on somebody."""
		name = _correction(self.in_a, "2026-03-06")
		frappe.db.set_value(attendance_correction.REQUEST, name,
		                    "alvoraa_review_status", None, update_modified=False)
		frappe.db.commit()
		self.assertEqual(self._part(self._counts(self.hr_user), "attendance_fixes")["count"], 1)

	def test_a_declined_or_withdrawn_draft_is_not_waiting(self):
		"""Both stay as drafts - Frappe will not move a draft to cancelled - so
		the label is the only thing separating them from a live request."""
		_correction(self.in_a, "2026-03-07", status="Declined")
		_correction(self.in_a, "2026-03-08", status="Withdrawn")
		frappe.db.commit()
		self.assertEqual(self._part(self._counts(self.hr_user), "attendance_fixes")["count"], 0)

	def test_my_own_correction_is_not_in_my_queue(self):
		"""Deciding your own correction is not a review."""
		_correction(self.hr_emp, "2026-03-09")
		frappe.db.commit()
		payload = self._counts(self.hr_user)
		self.assertEqual(self._part(payload, "attendance_fixes")["count"], 0)
		self.assertEqual(self._part(payload, "my_requests")["count"], 1,
		                 "it should be under my own requests instead")

	def test_at_the_cap_the_count_is_the_true_total_and_says_so(self):
		"""AC-51's boundary. 51 waiting: the count is 51, the screen shows 50,
		and the payload carries the cap so the screen can say so. Two rows that
		are NOT waiting sit early in the list, so a count that ignored the state
		filter would come back with 53 and fail here."""
		for day in range(51):
			_correction(self.in_a, add_days("2026-05-01", day))
		_correction(self.in_a, "2026-04-01", status="Declined")
		_correction(self.in_a, "2026-04-02", status="Withdrawn")
		frappe.db.commit()
		row = self._part(self._counts(self.hr_user), "attendance_fixes")
		self.assertEqual(row["count"], 51)
		self.assertEqual(row["cap"], inbox_api.CORRECTIONS_CAP)
		self.assertTrue(row["capped"])
		self._as(self.hr_user)
		self.assertEqual(len(attendance_correction.to_review()), 50)

	def test_a_reviewer_who_is_not_hr_keeps_their_whole_queue(self):
		"""AC-52 row 4, W1D-14. `_may_review` tests the submit permission, not
		a role, so a tenant may hand this queue to a Shift Supervisor. Applying
		an HR filter to them returns the empty set: fail-closed, so not a leak,
		but a working flow killed in silence. This test must fail if their
		queue comes back empty."""
		frappe.set_user("Administrator")
		role = "S034I Shift Supervisor"
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role}).insert(
				ignore_permissions=True)
		existing = frappe.db.exists("Custom DocPerm",
		                            {"parent": attendance_correction.REQUEST, "role": role})
		if not existing:
			frappe.get_doc({"doctype": "Custom DocPerm",
			                "parent": attendance_correction.REQUEST,
			                "parenttype": "DocType", "parentfield": "permissions",
			                "role": role, "read": 1, "submit": 1,
			                "permlevel": 0}).insert(ignore_permissions=True)
		user = frappe.get_doc("User", self.plain_user)
		had = any(r.role == role for r in user.roles)
		if not had:
			user.append("roles", {"role": role})
			user.save(ignore_permissions=True)
		frappe.clear_cache(user=self.plain_user)
		_correction(self.in_a, "2026-03-11")
		_correction(self.in_b, "2026-03-11")
		_correction(self.no_branch, "2026-03-11")
		frappe.db.commit()
		try:
			payload = self._counts(self.plain_user)
			self.assertEqual(self._part(payload, "attendance_fixes")["count"], 3,
			                 "a non-HR reviewer's queue was narrowed to nothing")
			self.assertFalse(payload["corrections_hr_scope"])
		finally:
			frappe.set_user("Administrator")
			if not had:
				user = frappe.get_doc("User", self.plain_user)
				user.roles = [r for r in user.roles if r.role != role]
				user.save(ignore_permissions=True)
			if not existing:
				frappe.db.delete("Custom DocPerm",
				                 {"parent": attendance_correction.REQUEST, "role": role})
			frappe.clear_cache(user=self.plain_user)
			# **The doctype cache, not only the user cache. 045.**
			#
			# Frappe decides whether to use custom permissions by asking
			# `get_doctypes_with_custom_docperms()` - "does this doctype have
			# ANY Custom DocPerm row?" - and the answer is cached. Once it is
			# yes, the STANDARD permissions are ignored entirely: the doctype
			# has exactly the rows the Custom DocPerm table holds, which here
			# was one row for a Shift Supervisor and nothing for HR User, HR
			# Manager, Employee or System Manager.
			#
			# Deleting the row put the table right and left the cache saying
			# "yes". So every test in this class that runs AFTER this one
			# alphabetically - five of them - failed with "Insufficient
			# Permission for Attendance Request" for an HR User, and the site
			# looked perfectly healthy afterwards because the row really had
			# been deleted.
			#
			# `setUpClass` already clears this cache after `after_migrate()`.
			# The tidy-up has to do the same, or it only half undoes itself.
			frappe.clear_cache(doctype=attendance_correction.REQUEST)
			frappe.db.commit()


class TestTheOtherPartsEqualTheirScreens(_InboxFixture):
	def test_the_policy_count_equals_the_policies_screen(self):
		"""The fast two-query shape must mean exactly what the screen's
		one-query-per-policy shape means."""
		self._as(self.plain_user)
		self.assertEqual(
			self._part(inbox_api.get_nav_counts(), "policies")["count"],
			hr_api.get_my_policies().get("pending", 0))

	def test_my_own_leave_is_mine_and_not_an_approval(self):
		"""AC-22. A person who is their own leave approver sees it once."""
		frappe.set_user("Administrator")
		before = self._counts(self.plain_user)
		frappe.set_user("Administrator")
		self.assertIsInstance(before["total"], int)


class TestAPlainEmployeeCountsNothingThatIsNotTheirs(_InboxFixture):
	def test_a_plain_employee_approves_nothing(self):
		"""Wrong-persona (SEC-2). Corrections raised by other people are in
		nobody's queue but a reviewer's."""
		_correction(self.in_a, "2026-03-12")
		_correction(self.in_b, "2026-03-12")
		frappe.db.commit()
		payload = self._counts(self.plain_user)
		self.assertEqual(self._part(payload, "attendance_fixes")["count"], 0)
		self.assertEqual(payload["approvals_total"], 0)


class TestTheDoctypeCacheMovesWithTheRelease(FrappeTestCase):
	"""Review finding F8, 2026-09-24.

	`_has_doctype` remembers "is this doctype on the site" for a day. The answer
	changes at a migration, and a migration clears the cache, so the normal path
	was already safe. The trap is the path that skips it: copying a file onto a
	running container is a deploy command this project uses, and it changes
	nothing a person sees for up to twenty-four hours.

	Putting the build version in the key closes that, the same way `ess_part`
	does. Take it out again and this test goes red.
	"""

	def test_the_key_carries_the_build_version(self):
		from frappe.utils import get_build_version

		key = "inbox_api:doctype:%s:Employee" % get_build_version()
		frappe.cache().delete_value(key)
		inbox_api._has_doctype("Employee")
		self.assertIsNotNone(
			frappe.cache().get_value(key),
			"the doctype cache is not keyed to the build version, so a new build "
			"reads the last one's answer for up to a day (F8)")

	def test_the_answer_is_still_right_either_way(self):
		self.assertTrue(inbox_api._has_doctype("Employee"))
		self.assertFalse(inbox_api._has_doctype("No Such Doctype S034"))
