"""Slice 042, Wave 2: the count equals the list, and the scope is a value.

Wave 1 proved the six counts. This file proves the thing Wave 2 adds: that the
number and the list come from **one filter expression**, and that a part whose
scope is missing or empty cannot exist.

Six of these checks are easy to write so that they prove nothing, and the spec's
handoff note names each one. What is done about it here:

* **AC-8 enumerates the parts from `parts()` itself**, never from a list typed
  into this file, so a seventh part added later with no matching row fails here
  rather than shipping untested.
* **AC-8's "never `{}`" half asserts on the RETURN VALUE**, not on the rows. An
  unscoped query that happened to return nothing looks identical from the
  outside, and that is the fail-open shape.
* **AC-11 puts the declined and withdrawn rows INSIDE the first 50** by creation
  date. Outside them the cap hides the bug.
* **AC-17 drives every drawn row through its own action AND an undrawn document
  through it expecting a refusal.** The second half is the one that matters.
* **AC-37 asserts zero scoped queries**, not just an empty list.
* Every equality assertion is guarded by a line proving the fixture is not
  empty. Two of Wave 1's assertions were written so they could never fail, and
  that is a finding, not a pass.

Synthetic people only, all tagged S042, in this slice's own company.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction, inbox_api
from alvoraa_portal.tests import fixtures_042 as fx

# Every table a part is allowed to read only when the caller has an Active
# Employee record. AC-37 asserts none of these is touched otherwise.
SCOPED_TABLES = (
	"tabLeave Application",
	"tabAttendance Request",
	"tabShift Request",
	"tabPolicy Document",
	"tabPolicy Acknowledgement",
	"tabKPI",
	"tabIndividual Goal",
)


class _Recorder:
	"""Every SQL statement run inside the block, as text.

	`frappe.db.sql` is the one door every read goes through, including the query
	builder's `.run()`. Wrapping it is how "did this query run at all" becomes a
	thing a test can assert instead of a thing a reviewer squints at.
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

	def touched(self, tables):
		return sorted({t for t in tables
		               if any(t in s for s in self.statements)})


class _WaveTwo(FrappeTestCase):
	"""This slice's own company, stores and people. Nothing shared."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fx.ensure_company()
		fx.ensure_branches()

		cls.rahul_login = fx.user("rahul", ("Employee",))
		cls.sandeep_login = fx.user("sandeep", ("Employee",))
		cls.priya_login = fx.user("priya", ("HR User", "Employee"))
		cls.kamal_login = fx.user("kamal", ("HR Manager", "Employee"))
		# Asha: a login with no Employee record at all (persona rule 6).
		cls.asha_login = fx.user("asha", ("System Manager",))

		cls.sandeep = fx.employee("Sandeep", branch=fx.STORE_A, login=cls.sandeep_login,
		                          designation="S042 Floor Manager")
		cls.rahul = fx.employee("Rahul", branch=fx.STORE_A, reports_to=cls.sandeep,
		                        login=cls.rahul_login)
		cls.priya = fx.employee("Priya", branch=fx.STORE_A, login=cls.priya_login)
		cls.kamal = fx.employee("Kamal", branch=None, login=cls.kamal_login)
		cls.in_b = fx.employee("InStoreB", branch=fx.STORE_B, reports_to=cls.kamal)
		# Four more under Sandeep, so his team is five people and can be taken
		# back below the minimum group size by moving one.
		cls.peers = [fx.employee("Peer%d" % i, branch=fx.STORE_A, reports_to=cls.sandeep)
		             for i in range(1, 5)]
		# A leaver whose login still works (SEC-14).
		cls.leaver_login = fx.user("leaver", ("Employee",))
		cls.leaver = fx.employee("Leaver", branch=fx.STORE_A, login=cls.leaver_login,
		                         status="Left")

		everyone = [cls.sandeep, cls.rahul, cls.priya, cls.kamal, cls.in_b,
		            cls.leaver] + cls.peers
		fx.holiday_list(everyone)
		attendance_correction.after_migrate()
		frappe.clear_cache(doctype=attendance_correction.REQUEST)
		frappe.db.commit()

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self._clear()
		fx.store_permission(self.priya_login, fx.STORE_A)

	def tearDown(self):
		frappe.set_user("Administrator")
		self._clear()
		fx.drop_store_permission(self.priya_login)
		super().tearDown()

	def _clear(self):
		frappe.db.delete(attendance_correction.REQUEST, {"explanation": "S042 fixture"})
		frappe.db.commit()

	def _as(self, login):
		frappe.set_user(login)
		frappe.clear_cache(user=login)

	def _correction(self, employee, day, status=None, docstatus=0):
		doc = frappe.get_doc({
			"doctype": attendance_correction.REQUEST,
			"employee": employee,
			"from_date": day,
			"to_date": day,
			"reason": "On Duty",
			"explanation": "S042 fixture",
		})
		doc.insert(ignore_permissions=True)
		if status is not None:
			doc.db_set("alvoraa_review_status", status, update_modified=False)
		if docstatus:
			doc.db_set("docstatus", docstatus, update_modified=False)
		return doc.name

	def _part(self, built, key):
		for p in built:
			if p.key == key:
				return p
		raise AssertionError("no part called %s" % key)


# ── AC-8: one filter, two uses ───────────────────────────────────────────────


class TestTheCountEqualsTheList(_WaveTwo):
	"""042 AC-8. The parts are enumerated from `parts()`, never typed here."""

	def _personas(self):
		return (self.rahul_login, self.sandeep_login, self.priya_login,
		        self.kamal_login, self.asha_login)

	def test_every_part_of_every_persona_counts_what_it_lists(self):
		# Make sure there is something to count. An all-zero fixture would let
		# this test pass while proving nothing.
		self._correction(self.rahul, add_days(nowdate(), -3))
		self._correction(self.in_b, add_days(nowdate(), -4))
		frappe.db.commit()

		seen_any = 0
		for login in self._personas():
			self._as(login)
			built, _hr = inbox_api.parts()
			self.assertEqual(len(built), len(inbox_api.PARTS))
			for part in built:
				count = part.count()
				rows = part.rows(limit=None)
				self.assertEqual(
					count, len(rows),
					"%s: part %r counted %d and listed %d"
					% (login, part.key, count, len(rows)))
				seen_any += count
		frappe.set_user("Administrator")
		self.assertGreater(
			seen_any, 0,
			"the fixture produced nothing to count, so this test proved nothing")

	def test_a_part_without_a_scope_cannot_be_built(self):
		"""SEC-3. The scope is data, not a comment, and it is checked on
		construction - so a part added later with no scope is a failure here
		rather than a runtime default meaning 'everybody'."""
		for bad in ("", "   ", None, 0):
			with self.assertRaises(inbox_api.PartDefinitionError):
				inbox_api.Part("x", "#x", bad, {"name": "y"},
				               lambda f: 0, lambda f, n: [])

	def test_a_part_with_an_empty_filter_dict_cannot_be_built(self):
		"""SEC-4. In Frappe `{}` means every record."""
		with self.assertRaises(inbox_api.PartDefinitionError):
			inbox_api.Part("x", "#x", "a scope", {}, lambda f: 0, lambda f, n: [])
		# ...and the good case really does build, so the test above can fail.
		inbox_api.Part("x", "#x", "a scope", {"name": "y"},
		               lambda f: 0, lambda f, n: [])

	def test_every_part_carries_a_non_empty_scope_for_every_persona(self):
		for login in self._personas():
			self._as(login)
			built, _hr = inbox_api.parts()
			for part in built:
				self.assertTrue(part.scope and part.scope.strip(),
				                "part %r has no scope for %s" % (part.key, login))
		frappe.set_user("Administrator")

	def test_no_filter_helper_ever_returns_an_empty_dict(self):
		"""SEC-4, asserted on the RETURN VALUE and not on the rows.

		A plain employee, a manager, an HR user and a caller with no Employee
		record. An unscoped query that happened to return nothing looks
		identical from the outside; this looks at the filter itself.
		"""
		for login in self._personas():
			self._as(login)
			built, _hr = inbox_api.parts()
			for part in built:
				filters = part.filters
				if isinstance(filters, dict):
					self.assertTrue(
						filters,
						"part %r handed %s an empty filter dict, which in Frappe "
						"means every record" % (part.key, login))
		frappe.set_user("Administrator")

	def test_no_rows_really_matches_nothing(self):
		"""The sentinel is only fail-closed if it actually matches nothing."""
		self._correction(self.rahul, add_days(nowdate(), -3))
		frappe.db.commit()
		found = frappe.get_all(attendance_correction.REQUEST,
		                       filters=inbox_api.no_rows(), pluck="name")
		self.assertEqual(found, [])
		# The same query without the sentinel finds the row, so the assertion
		# above can fail.
		self.assertTrue(frappe.get_all(attendance_correction.REQUEST,
		                               filters={"explanation": "S042 fixture"},
		                               pluck="name"))


# ── AC-37: a caller with no Employee record is refused, not filtered ─────────


class TestACallerWithNoEmployeeRecord(_WaveTwo):

	def test_asha_gets_zeroes_and_no_scoped_query_runs_at_all(self):
		"""042 AC-37, strengthened. The result is empty AND the query did not run.

		A refusal must be an explicit early return, never a filter that was
		skipped because there was no employee to filter on.
		"""
		self._as(self.asha_login)
		# Warm the doctype-exists cache first, so what is measured is the parts
		# and not the site probe.
		inbox_api.parts()
		with _Recorder() as rec:
			built, _hr = inbox_api.parts()
			for part in built:
				self.assertEqual(part.count(), 0)
				self.assertEqual(part.rows(limit=None), [])
		touched = rec.touched(SCOPED_TABLES)
		frappe.set_user("Administrator")
		self.assertEqual(
			touched, [],
			"a caller with no Employee record made these scoped queries: %s"
			% (touched,))
		# The recorder works: the same block as a real employee DOES touch them.
		self._as(self.rahul_login)
		with _Recorder() as rec2:
			built, _hr = inbox_api.parts()
			for part in built:
				part.count()
		frappe.set_user("Administrator")
		self.assertTrue(
			rec2.touched(SCOPED_TABLES),
			"the recorder saw no scoped query even for a real employee, so the "
			"assertion above could never have failed")

	def test_asha_gets_all_clear_rather_than_an_error(self):
		self._as(self.asha_login)
		counts = inbox_api.get_nav_counts()
		box = inbox_api.get_inbox()
		frappe.set_user("Administrator")
		self.assertEqual(counts["total"], 0)
		self.assertEqual(box["total"], 0)
		self.assertFalse(box["has_employee"])
		self.assertTrue(all(p["count"] == 0 and not p["rows"] for p in box["parts"]))

	def test_a_leaver_with_a_live_login_gets_zeroes(self):
		self._as(self.leaver_login)
		box = inbox_api.get_inbox()
		frappe.set_user("Administrator")
		self.assertEqual(box["total"], 0)


# ── AC-9: counted once, never twice ──────────────────────────────────────────


class TestNobodyIsCountedTwice(_WaveTwo):

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Leave Application", {"employee": self.rahul})
		frappe.db.commit()
		super().tearDown()

	def _own_leave(self):
		"""Rahul's own open leave, with Rahul as his own leave approver."""
		from alvoraa_portal.tests.leave_fixtures import ensure_leave_type

		leave_type = ensure_leave_type("S042 Casual")
		doc = frappe.get_doc({
			"doctype": "Leave Application",
			"employee": self.rahul,
			"leave_type": leave_type,
			"from_date": add_days(nowdate(), 10),
			"to_date": add_days(nowdate(), 10),
			"leave_approver": self.rahul_login,
			"status": "Open",
		})
		doc.flags.ignore_permissions = True
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		frappe.db.commit()
		return doc.name

	def test_my_own_leave_is_mine_and_not_an_approval(self):
		"""042 AC-9. A person who is their own approver is counted ONCE."""
		name = self._own_leave()
		self.assertTrue(name)
		self._as(self.rahul_login)
		built, _hr = inbox_api.parts()
		approvals = self._part(built, "leave_approvals")
		mine = self._part(built, "my_requests")
		frappe.set_user("Administrator")
		self.assertEqual(approvals.count(), 0)
		self.assertGreaterEqual(mine.count(), 1)
		self.assertIn(name, [r["name"] for r in mine.rows(limit=None)])

	def test_my_own_correction_is_not_in_my_own_queue(self):
		"""042 AC-25, on the corrections path."""
		mine = self._correction(self.priya, add_days(nowdate(), -3))
		frappe.db.commit()
		self._as(self.priya_login)
		built, _hr = inbox_api.parts()
		queue = self._part(built, "attendance_fixes")
		names = [r["name"] for r in queue.rows(limit=None)]
		my_part = self._part(built, "my_requests")
		my_names = [r["name"] for r in my_part.rows(limit=None)]
		frappe.set_user("Administrator")
		self.assertNotIn(mine, names)
		self.assertIn(mine, my_names)


# ── AC-11: the count is the truth, the list is capped ────────────────────────


class TestTheCapSaysSo(_WaveTwo):

	def test_above_the_cap_the_count_is_the_true_total(self):
		"""042 AC-11. The declined and withdrawn rows sit INSIDE the first 50
		by creation date - outside them the cap would hide the bug."""
		# A day each: Frappe HR refuses two Attendance Requests for one person
		# over the same period, so "many waiting" has to be many days.
		def day(n):
			return add_days(nowdate(), -20 - n)

		# Two that must not be counted, created FIRST so they sit INSIDE the
		# first 50 by creation date. Outside them the cap hides the bug.
		self._correction(self.in_b, day(0), status="Declined")
		self._correction(self.in_b, day(1), status="Withdrawn")
		for i in range(inbox_api.CORRECTIONS_CAP + 1):
			self._correction(self.in_b, day(i + 2))
		frappe.db.commit()

		self._as(self.kamal_login)
		box = inbox_api.get_inbox()
		frappe.set_user("Administrator")
		part = [p for p in box["parts"] if p["key"] == "attendance_fixes"][0]
		self.assertEqual(part["count"], inbox_api.CORRECTIONS_CAP + 1,
		                 "a count that ignored the state filter would read 53")
		self.assertEqual(part["shown"], inbox_api.CORRECTIONS_CAP)
		self.assertTrue(part["capped"])


# ── AC-15: the query count, and the N+1 it caught ───────────────────────────


class TestTheQueryCountIsBounded(_WaveTwo):
	"""042 AC-15. Not the 1,000-employee measurement the spec asks for - that
	fixture does not exist yet and the notes say so. What this DOES prove is the
	shape that makes the measurement fail: **a query inside a loop.**

	It earned its place immediately. The context line on a leave approval row
	was asked for one row at a time, which is fifty queries at the list cap and
	breaks the budget of twenty-five for the whole call. This test is what found
	it; `_leave_contexts` now reads the whole page in one query.
	"""

	BUDGET = 25

	def tearDown(self):
		frappe.set_user("Administrator")
		# Only ever this slice's own people. A delete with a loose filter here is
		# another file's fixture gone, and that has cost this slice time before.
		mine = list(self.peers) + [self.rahul, self.in_b]
		frappe.db.delete("Leave Application", {"employee": ["in", mine]})
		frappe.db.commit()
		super().tearDown()

	def _leave(self, employee, day):
		from alvoraa_portal.tests.leave_fixtures import ensure_leave_type

		doc = frappe.get_doc({
			"doctype": "Leave Application",
			"employee": employee,
			"leave_type": ensure_leave_type("S042 Casual"),
			"from_date": day,
			"to_date": day,
			"leave_approver": self.sandeep_login,
			"status": "Open",
		})
		doc.flags.ignore_permissions = True
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		return doc.name

	def test_more_rows_do_not_mean_more_queries(self):
		"""The assertion that catches an N+1 without needing a big fixture:
		the query count must not GROW with the number of rows."""
		day = add_days(nowdate(), 20)
		self._leave(self.peers[0], day)
		frappe.db.commit()
		self._as(self.sandeep_login)
		inbox_api.get_inbox()                     # warm the caches
		with _Recorder() as one_row:
			inbox_api.get_inbox()
		frappe.set_user("Administrator")

		for peer in self.peers[1:]:
			self._leave(peer, day)
		self._leave(self.rahul, day)
		frappe.db.commit()
		self._as(self.sandeep_login)
		# Warm again, and this line is the whole method. Inserting documents
		# clears caches, so measuring straight after the inserts compares a warm
		# call with a cold one and reads the difference as an N+1. The first
		# version of this test did exactly that and reported 14 against 17 while
		# the real steady-state answer is 14 against 14. Both measurements are
		# now taken in the same state, which is the only way the comparison
		# means anything.
		inbox_api.get_inbox()
		with _Recorder() as many_rows:
			box = inbox_api.get_inbox()
		frappe.set_user("Administrator")

		drawn = [p for p in box["parts"] if p["key"] == "leave_approvals"][0]
		self.assertGreaterEqual(
			drawn["shown"], 4,
			"only %d rows were drawn, so going from one row to many proved "
			"nothing" % drawn["shown"])
		self.assertLessEqual(
			len(many_rows.statements), len(one_row.statements) + 1,
			"the query count grew from %d to %d when the rows went from 1 to %d "
			"- that is a query inside a loop"
			% (len(one_row.statements), len(many_rows.statements), drawn["shown"]))

	def test_get_inbox_stays_inside_its_budget(self):
		day = add_days(nowdate(), 21)
		for peer in self.peers:
			self._leave(peer, day)
		self._correction(self.in_b, add_days(nowdate(), -11))
		frappe.db.commit()
		self._as(self.sandeep_login)
		inbox_api.get_inbox()                     # warm the caches
		with _Recorder() as rec:
			inbox_api.get_inbox()
		frappe.set_user("Administrator")
		self.assertLessEqual(
			len(rec.statements), self.BUDGET,
			"get_inbox ran %d queries; the budget is %d"
			% (len(rec.statements), self.BUDGET))


# ── AC-12 and PRIV-4: the counts payload carries numbers ─────────────────────


class TestTheCountsPayloadIsNumbers(_WaveTwo):

	def test_no_names_no_reasons_no_document_ids(self):
		self._correction(self.in_b, add_days(nowdate(), -3))
		frappe.db.commit()
		self._as(self.kamal_login)
		payload = inbox_api.get_nav_counts()
		frappe.set_user("Administrator")
		blob = frappe.as_json(payload)
		self.assertNotIn(fx.TAG, blob, "a person's name reached the counts payload")
		self.assertNotIn("On Duty", blob, "a reason reached the counts payload")
		for part in payload["parts"]:
			self.assertEqual(sorted(part.keys()),
			                 ["cap", "capped", "count", "key", "route"])

	def test_a_row_only_ever_carries_the_fixed_key_list(self):
		"""Every row of every part, for every persona, against ROW_KEYS."""
		self._correction(self.in_b, add_days(nowdate(), -3))
		frappe.db.commit()
		seen = 0
		for login in (self.rahul_login, self.sandeep_login, self.priya_login,
		              self.kamal_login):
			self._as(login)
			built, _hr = inbox_api.parts()
			for part in built:
				for row in part.rows(limit=None):
					seen += 1
					self.assertEqual(sorted(row.keys()),
					                 sorted(inbox_api.row_keys(part.key)),
					                 "part %r sent an unexpected key set" % part.key)
		frappe.set_user("Administrator")
		self.assertGreater(seen, 0, "no row was checked, so this proved nothing")


# ── AC-17: the list and the action share one scope ───────────────────────────


class TestADrawnRowIsActionableAndAnUndrawnOneIsNot(_WaveTwo):

	def test_every_drawn_correction_can_be_decided_by_the_person_who_sees_it(self):
		"""042 AC-17 (a). A row that is drawn never returns a refusal."""
		self._correction(self.in_b, add_days(nowdate(), -5))
		frappe.db.commit()
		self._as(self.kamal_login)
		built, _hr = inbox_api.parts()
		rows = self._part(built, "attendance_fixes").rows(limit=None)
		self.assertTrue(rows, "no correction was drawn, so this proved nothing")
		for row in rows:
			attendance_correction.decide(row["name"], approve=0, note="S042 test")
		frappe.set_user("Administrator")

	def test_a_correction_that_is_not_drawn_is_refused_when_called_by_hand(self):
		"""042 AC-17 (b) - the half that matters.

		Rahul sees no corrections queue at all. Calling `decide` by hand with a
		real document name must be refused, and nothing may be written.
		"""
		name = self._correction(self.in_b, add_days(nowdate(), -6))
		frappe.db.commit()
		before = frappe.db.get_value(attendance_correction.REQUEST, name,
		                             ["docstatus", "alvoraa_review_status"])
		self._as(self.rahul_login)
		built, _hr = inbox_api.parts()
		self.assertEqual(self._part(built, "attendance_fixes").rows(limit=None), [])
		with self.assertRaises(frappe.PermissionError):
			attendance_correction.decide(name, approve=1)
		frappe.set_user("Administrator")
		after = frappe.db.get_value(attendance_correction.REQUEST, name,
		                            ["docstatus", "alvoraa_review_status"])
		self.assertEqual(before, after, "a refused call still wrote to the document")


# ── AC-23 / AC-24: a store HR person's queue is their store's ────────────────


class TestStoreHrSeesTheirStore(_WaveTwo):

	def test_priya_counts_her_store_and_nobody_elses(self):
		mine = self._correction(self.rahul, add_days(nowdate(), -7))
		theirs = self._correction(self.in_b, add_days(nowdate(), -7))
		frappe.db.commit()
		self._as(self.priya_login)
		built, _hr = inbox_api.parts()
		part = self._part(built, "attendance_fixes")
		names = [r["name"] for r in part.rows(limit=None)]
		frappe.set_user("Administrator")
		self.assertIn(mine, names, "her own store's correction is missing")
		self.assertNotIn(theirs, names, "head office's correction reached her store")
		self.assertEqual(part.count(), len(names))

	def test_company_wide_hr_sees_both_stores(self):
		mine = self._correction(self.rahul, add_days(nowdate(), -8))
		theirs = self._correction(self.in_b, add_days(nowdate(), -8))
		frappe.db.commit()
		self._as(self.kamal_login)
		built, _hr = inbox_api.parts()
		names = [r["name"] for r in self._part(built, "attendance_fixes").rows(limit=None)]
		frappe.set_user("Administrator")
		self.assertIn(mine, names)
		self.assertIn(theirs, names)


# ── AC-41 / SEC-2: who may call get_inbox ────────────────────────────────────


class TestWhoMayCallTheInbox(_WaveTwo):

	def test_guest_is_refused(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				inbox_api.get_inbox()
		finally:
			frappe.set_user("Administrator")

	def test_a_plain_employee_gets_an_inbox_with_no_approvals_in_it(self):
		"""The wrong-persona case. Rahul approves nothing, and is told so with
		an empty list rather than a refusal."""
		self._correction(self.in_b, add_days(nowdate(), -9))
		frappe.db.commit()
		self._as(self.rahul_login)
		box = inbox_api.get_inbox()
		frappe.set_user("Administrator")
		self.assertEqual(box["approvals_total"], 0)
		for part in box["parts"]:
			if part["key"] in inbox_api.APPROVAL_PARTS:
				self.assertEqual(part["rows"], [])

	def test_my_requests_is_my_own_employee_and_nobody_elses(self):
		"""042 AC-20."""
		mine = self._correction(self.rahul, add_days(nowdate(), -10))
		theirs = self._correction(self.in_b, add_days(nowdate(), -10))
		frappe.db.commit()
		self._as(self.rahul_login)
		built, _hr = inbox_api.parts()
		names = [r["name"] for r in self._part(built, "my_requests").rows(limit=None)]
		frappe.set_user("Administrator")
		self.assertIn(mine, names)
		self.assertNotIn(theirs, names)


# ── AC-38: the parts are computed once, and get_home carries no counts ───────


class TestTheCountIsComputedOnce(_WaveTwo):

	def test_get_nav_counts_and_get_inbox_both_read_the_same_helper(self):
		"""The structural half of AC-38: neither call writes a filter of its own.

		Read from the source rather than claimed: `frappe.db.count`,
		`frappe.get_all` and `frappe.get_list` may appear inside a part builder,
		never inside `get_nav_counts` or `get_inbox`.
		"""
		import ast
		import inspect

		source = inspect.getsource(inbox_api)
		tree = ast.parse(source)
		for node in ast.walk(tree):
			if not isinstance(node, ast.FunctionDef):
				continue
			if node.name not in ("get_nav_counts", "get_inbox"):
				continue
			for inner in ast.walk(node):
				if isinstance(inner, ast.Attribute) and inner.attr in (
					"count", "get_all", "get_list", "sql",
				):
					owner = getattr(inner.value, "id", None) or getattr(
						getattr(inner.value, "value", None), "id", None)
					self.assertNotEqual(
						owner, "frappe",
						"%s queries the database directly - every number must "
						"come out of parts()" % node.name)
