"""Slice 076, Part C: expense claims decided from Home, and the birthdays card.

Pin tests, named so a bad merge that drops the feature fails by name:

  test_only_the_named_approver_decides
  test_nobody_decides_their_own_claim_on_any_door
  test_a_claim_with_no_approver_is_refused
  test_birthday_reply_has_no_year
  test_switch_off_returns_nothing_and_reads_nobody

The data matters (01c lesson 1): every expense test uses a claim filed through
the portal WITH an approver, because "0 rows" proves nothing.
"""

import inspect
import re
from datetime import date

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from alvoraa_goals.tests.utils import ensure_company, ensure_employee
from alvoraa_portal import home_people, hr_api, inbox_api
from alvoraa_portal.patches.v1_0 import expense_claim_approver_backfill
from alvoraa_portal.tests.leave_fixtures import ensure_user
from alvoraa_portal.tests.measure_044 import _Spy
from alvoraa_portal.tests.test_expense_and_scoping import ensure_expense_type
from alvoraa_portal.tests.test_home_076 import link_user_to_employee
from alvoraa_portal.tests.utils import ensure_fiscal_years

EXPENSE_KEYS = {"name", "employee_name", "expense_type", "expense_date", "amount", "note",
                "waiting_since", "action"}


def _person(first, user=None, roles=("Employee",), last="C076"):
	emp = ensure_employee(first, last)
	frappe.db.set_value("Employee", emp, {"status": "Active", "expense_approver": None,
	                                      "department": None, "branch": None,
	                                      home_people.HIDE: 0})
	if user:
		ensure_user(user, roles=roles)
		link_user_to_employee(emp, user)
	return emp


def _expense_part(user):
	frappe.set_user(user)
	got = {p["key"]: p for p in inbox_api.get_inbox()["parts"]}["expense_approvals"]
	frappe.set_user("Administrator")
	return got


def _gl(name):
	return frappe.db.count("GL Entry", {"voucher_type": "Expense Claim", "voucher_no": name,
	                                    "is_cancelled": 0})


class TestExpenseFromPending(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		ensure_fiscal_years()
		company = ensure_company()
		cls.etype = ensure_expense_type(company=company)
		frappe.db.set_single_value("HR Settings", "prevent_self_expense_approval", 0)
		approver = ("Employee", "Expense Approver")
		cls.m = "c076.mgr@example.com"
		cls.m_emp = _person("C076Mgr", cls.m, approver)
		cls.x = "c076.x@example.com"
		_person("C076X", cls.x, approver)
		cls.hr = "c076.hr@example.com"
		_person("C076Hr", cls.hr, ("Employee", "HR Manager"))
		cls.a = "c076.a@example.com"
		cls.a_emp = _person("C076A", cls.a)
		cls.b = "c076.b@example.com"
		cls.b_emp = _person("C076B", cls.b)
		cls.n = "c076.n@example.com"
		cls.n_emp = _person("C076N", cls.n)
		cls.s = "c076.s@example.com"
		cls.s_emp = _person("C076S", cls.s, approver)
		cls.p = "c076.p@example.com"
		_person("C076P", cls.p)                       # an approver without the role
		cls.c = "c076.c@example.com"
		cls.c_emp = _person("C076C", cls.c)
		cls.l = "c076.l@example.com"
		cls.l_emp = _person("C076L", cls.l, approver)  # an approver who has left
		cls.e = "c076.e@example.com"
		cls.e_emp = _person("C076E", cls.e)
		cls.d = "c076.d@example.com"
		cls.d_emp = _person("C076D", cls.d)
		for emp in (cls.a_emp, cls.b_emp):
			frappe.db.set_value("Employee", emp, "expense_approver", cls.m)
		frappe.db.set_value("Employee", cls.s_emp, "expense_approver", cls.s)
		frappe.db.set_value("Employee", cls.c_emp, "expense_approver", cls.p)
		# Frappe HR gives a named approver the role on their next User save; a
		# Department approver may never get it. Take it away directly.
		frappe.db.delete("Has Role", {"parent": cls.p, "role": "Expense Approver"})
		frappe.clear_cache(user=cls.p)
		frappe.db.set_value("Employee", cls.e_emp, "expense_approver", cls.l)
		# The Department route: no approver on the Employee, one on the Department.
		dept = frappe.db.get_value("Department", {"department_name": "C076 Dept", "company": company})
		if not dept:
			dept = frappe.get_doc({"doctype": "Department", "department_name": "C076 Dept",
			                       "company": company}).insert(ignore_permissions=True).name
		d = frappe.get_doc("Department", dept)
		d.set("expense_approvers", [{"approver": cls.m}])
		d.save(ignore_permissions=True)
		frappe.db.set_value("Employee", cls.d_emp, "department", dept)
		# Filing commits, so drafts from an earlier run would fill the queue.
		mine = [cls.a_emp, cls.b_emp, cls.s_emp, cls.c_emp, cls.e_emp, cls.d_emp]
		for name in frappe.get_all("Expense Claim", filters={"employee": ["in", mine], "docstatus": 0},
		                           pluck="name"):
			frappe.delete_doc("Expense Claim", name, force=1, ignore_permissions=True)
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _file(self, user, amount=2300, note="Taxi to the supplier visit"):
		frappe.set_user(user)
		name = hr_api.apply_expense_claim(expense_type=self.etype, expense_date=today(),
		                                  amount=amount, description=note)["name"]
		frappe.set_user("Administrator")
		return name

	def _decide(self, user, name, action, reason=None):
		frappe.set_user(user)
		try:
			return hr_api.decide_expense(name, action, reason)
		finally:
			frappe.set_user("Administrator")

	# ── filing ─────────────────────────────────────────────────────────────
	def test_filing_sets_the_approver(self):
		claim = frappe.get_doc("Expense Claim", self._file(self.a))
		self.assertEqual(claim.expense_approver, self.m)
		self.assertTrue(frappe.has_permission("Expense Claim", "submit", claim, user=self.m))

	def test_the_department_approver_is_used_when_the_employee_has_none(self):
		self.assertEqual(frappe.db.get_value("Expense Claim", self._file(self.d), "expense_approver"), self.m)

	def test_an_approver_without_the_role_gets_a_share(self):
		name = self._file(self.c)
		self.assertTrue(frappe.db.exists("DocShare", {"share_doctype": "Expense Claim", "share_name": name,
		                                              "user": self.p, "submit": 1}))

	def test_a_claim_with_no_approver_is_refused(self):
		before = frappe.db.count("Expense Claim", {"employee": self.n_emp})
		frappe.set_user(self.n)
		with self.assertRaises(frappe.ValidationError) as ctx:
			hr_api.apply_expense_claim(expense_type=self.etype, expense_date=today(), amount=10)
		frappe.set_user("Administrator")
		self.assertIn("Ask HR to set your approver.", str(ctx.exception))
		self.assertEqual(frappe.db.count("Expense Claim", {"employee": self.n_emp}), before)

	# ── the Pending part ───────────────────────────────────────────────────
	def test_the_approver_sees_the_claim_with_exactly_the_agreed_keys(self):
		name = self._file(self.a, 860, "Printer paper")
		part = _expense_part(self.m)
		self.assertEqual(part["count"], len(part["rows"]))
		row = [r for r in part["rows"] if r["name"] == name][0]
		self.assertEqual(set(row), EXPENSE_KEYS)
		self.assertEqual((row["amount"], row["expense_type"], row["note"], row["action"]),
		                 (860, self.etype, "Printer paper", "expense"))
		self.assertEqual(row["expense_date"], today())
		self.assertTrue(row["waiting_since"])
		self.assertIn("expense_approvals", inbox_api.APPROVAL_PARTS)

	def test_nobody_else_sees_it(self):
		self._file(self.a)
		for user in (self.x, self.hr, self.a, self.b):
			with self.subTest(user=user):
				part = _expense_part(user)
				self.assertEqual((part["count"], part["rows"]), (0, []))

	def test_a_caller_with_no_active_employee_gets_no_rows(self):
		who = inbox_api._Who("Administrator")
		part = inbox_api._part_expense_approvals(who)
		self.assertEqual(part.filters, inbox_api.no_rows())
		self.assertFalse(part.available)
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			inbox_api.get_inbox()

	def test_the_count_and_the_total_add_up(self):
		self._file(self.a)
		self._file(self.b)
		frappe.set_user(self.m)
		counts = inbox_api.get_nav_counts()
		frappe.set_user("Administrator")
		by_key = {p["key"]: p["count"] for p in counts["parts"]}
		self.assertGreaterEqual(by_key["expense_approvals"], 2)
		self.assertEqual(counts["approvals_total"], sum(by_key[k] for k in inbox_api.APPROVAL_PARTS))

	# ── deciding ───────────────────────────────────────────────────────────
	def test_only_the_named_approver_decides(self):
		name = self._file(self.a)
		for user in (self.x, self.hr, self.b):
			with self.subTest(user=user):
				with self.assertRaises(frappe.PermissionError):
					self._decide(user, name, "approve")
		claim = frappe.get_doc("Expense Claim", name)
		self.assertEqual((claim.docstatus, claim.approval_status), (0, "Draft"))
		with self.assertRaises(frappe.PermissionError):
			self._decide(self.m, "HR-EXP-NO-SUCH-CLAIM", "approve")
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			hr_api.decide_expense(name, "approve")

	def test_an_approver_who_has_left_is_refused(self):
		name = self._file(self.e)
		frappe.db.set_value("Employee", self.l_emp, "status", "Left")
		try:
			with self.assertRaises(frappe.PermissionError):
				self._decide(self.l, name, "approve")
		finally:
			frappe.db.set_value("Employee", self.l_emp, "status", "Active")
			frappe.db.commit()

	def test_an_approver_without_the_role_is_told_what_to_ask_for(self):
		name = self._file(self.c)
		with self.assertRaises(frappe.PermissionError) as ctx:
			self._decide(self.p, name, "approve")
		self.assertIn("Expense Approver", str(ctx.exception))
		self.assertEqual(frappe.db.get_value("Expense Claim", name, "docstatus"), 0)

	def test_approve_posts_once_and_a_second_tap_is_already_decided(self):
		name = self._file(self.a)
		got = self._decide(self.m, name, "approve")
		self.assertEqual(got, {"name": name, "approval_status": "Approved"})
		claim = frappe.get_doc("Expense Claim", name)
		self.assertEqual((claim.docstatus, claim.approval_status), (1, "Approved"))
		posted = _gl(name)
		self.assertGreaterEqual(posted, 2)
		for action in ("approve", "decline"):
			with self.assertRaises(frappe.ValidationError) as ctx:
				self._decide(self.m, name, action, "late")
			self.assertIn("already been decided", str(ctx.exception))
		self.assertEqual(_gl(name), posted)
		self.assertNotIn(name, [r["name"] for r in _expense_part(self.m)["rows"]])

	def test_decline_needs_a_reason_stores_it_as_text_and_posts_nothing(self):
		name = self._file(self.a)
		for bad in (None, "   ", "x" * 141):
			with self.subTest(reason=bad):
				with self.assertRaises(frappe.ValidationError):
					self._decide(self.m, name, "decline", bad)
		self.assertEqual(frappe.db.get_value("Expense Claim", name, "docstatus"), 0)
		self._decide(self.m, name, "decline", "  <b>x</b> no receipt  ")
		claim = frappe.get_doc("Expense Claim", name)
		self.assertEqual((claim.docstatus, claim.approval_status), (1, "Rejected"))
		self.assertEqual(claim.alvoraa_decline_reason, "&lt;b&gt;x&lt;/b&gt; no receipt")
		self.assertFalse(claim.remark)            # the claim's title is not touched (AC-94)
		self.assertEqual(_gl(name), 0)
		self.assertEqual(claim.total_sanctioned_amount, 0)

	def test_the_claimant_reads_their_own_reason_and_nobody_elses(self):
		name = self._file(self.a)
		self._decide(self.m, name, "decline", "<b>x</b>")
		frappe.set_user(self.a)
		mine = {c["name"]: c for c in hr_api.get_expense_claims()["claims"]}
		frappe.set_user(self.b)
		theirs = hr_api.get_expense_claims()["claims"]
		frappe.set_user("Administrator")
		self.assertEqual(mine[name]["decline_reason"], "<b>x</b>")
		self.assertNotIn("alvoraa_decline_reason", mine[name])
		self.assertNotIn(name, [c["name"] for c in theirs])
		self.assertFalse([c for c in theirs if c.get("decline_reason") == "<b>x</b>"])

	def test_nobody_decides_their_own_claim_on_any_door(self):
		self.assertEqual(frappe.db.get_single_value("HR Settings", "prevent_self_expense_approval"), 0)
		# Filing refuses S (own approver), so the claim is filed with M and HR
		# points it at S in Desk - the shape a self-approval would need.
		frappe.db.set_value("Employee", self.s_emp, "expense_approver", self.m)
		try:
			name = self._file(self.s)
		finally:
			frappe.db.set_value("Employee", self.s_emp, "expense_approver", self.s)
		frappe.db.set_value("Expense Claim", name, "expense_approver", self.s)
		frappe.db.commit()
		with self.assertRaises(frappe.PermissionError):
			self._decide(self.s, name, "approve")
		self.assertNotIn(name, [r["name"] for r in _expense_part(self.s)["rows"]])
		frappe.set_user(self.s)
		try:
			doc = frappe.get_doc("Expense Claim", name)
			doc.approval_status = "Approved"
			with self.assertRaises(frappe.PermissionError):
				doc.submit()                      # the doc API
			from frappe.client import submit
			doc = frappe.get_doc("Expense Claim", name).as_dict()
			doc["approval_status"] = "Approved"
			with self.assertRaises(frappe.PermissionError):
				submit(doc)                       # the REST door
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Expense Claim", name, "docstatus"), 0)

	def test_a_claimant_who_is_their_own_approver_is_refused_at_filing(self):
		before = frappe.db.count("Expense Claim", {"employee": self.s_emp})
		frappe.set_user(self.s)
		with self.assertRaises(frappe.ValidationError) as ctx:
			hr_api.apply_expense_claim(expense_type=self.etype, expense_date=today(), amount=10)
		frappe.set_user("Administrator")
		self.assertIn("Ask HR to set your approver.", str(ctx.exception))
		self.assertEqual(frappe.db.count("Expense Claim", {"employee": self.s_emp}), before)

	def test_the_claimant_cannot_choose_their_approver_but_hr_can(self):
		name = self._file(self.a)
		from frappe.client import set_value
		frappe.set_user(self.a)
		try:
			with self.assertRaises(frappe.PermissionError):
				set_value("Expense Claim", name, "expense_approver", self.x)       # the REST door
			doc = frappe.get_doc({"doctype": "Expense Claim", "employee": self.a_emp,
			                      "expense_approver": self.x, "expenses": []})
			with self.assertRaises(frappe.PermissionError):
				hr_api.keep_claim_approver(doc)                                      # a new claim naming a friend
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Expense Claim", name, "expense_approver"), self.m)
		frappe.set_user(self.hr)
		try:
			set_value("Expense Claim", name, "expense_approver", self.x)           # HR may
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Expense Claim", name, "expense_approver"), self.x)

	def test_the_hook_is_registered(self):
		self.assertEqual(frappe.get_hooks("doc_events")["Expense Claim"]["validate"],
		                 ["alvoraa_portal.hr_api.keep_claim_approver"])
		self.assertIn("hrms.alvoraa_hr_core.access.refuse_own_submit",
		              frappe.get_hooks("doc_events")["Expense Claim"]["before_submit"])

	def test_decide_expense_has_no_permission_shortcuts(self):
		src = inspect.getsource(hr_api.decide_expense)
		code = "\n".join(line for line in src.splitlines() if not line.strip().startswith("#"))
		body = code.split('"""')[2]               # after the docstring
		for word in ("ignore_permissions", "db_set", "frappe.db.sql", "set_value"):
			self.assertNotIn(word, body)

	# ── the backfill ───────────────────────────────────────────────────────
	def test_backfill_sets_open_claims_and_a_second_run_changes_nothing(self):
		name = self._file(self.a)
		frappe.db.set_value("Expense Claim", name, "expense_approver", None)
		frappe.db.commit()
		expense_claim_approver_backfill.execute()
		self.assertEqual(frappe.db.get_value("Expense Claim", name, "expense_approver"), self.m)
		modified = frappe.db.get_value("Expense Claim", name, "modified")
		expense_claim_approver_backfill.execute()
		self.assertEqual(frappe.db.get_value("Expense Claim", name, "modified"), modified)

	def test_backfill_never_makes_the_claimant_their_own_approver(self):
		frappe.db.set_value("Employee", self.s_emp, "expense_approver", self.m)
		try:
			name = self._file(self.s)
		finally:
			frappe.db.set_value("Employee", self.s_emp, "expense_approver", self.s)
		frappe.db.set_value("Expense Claim", name, "expense_approver", None)
		frappe.db.commit()
		expense_claim_approver_backfill.execute()
		self.assertFalse(frappe.db.get_value("Expense Claim", name, "expense_approver"))


class TestBirthdays(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		now = getdate(today())
		cls.now = now
		for b in ("C076 North", "C076 South"):
			if not frappe.db.exists("Branch", b):
				frappe.get_doc({"doctype": "Branch", "branch": b}).insert(ignore_permissions=True)
		other = 1 if now.month != 1 else 2
		yday = 1 if now.day != 1 else 2

		def born(day, month=None, year=1990):
			return date(year, month or now.month, day)

		def make(first, branch="C076 North", dob=None, doj=None, user=None, status="Active", login=True):
			user = user or ("c076.bd.%s@example.com" % first.lower() if login else None)
			emp = _person(first, user, last="Bday076")
			if not login:
				frappe.db.set_value("Employee", emp, "user_id", None)
			frappe.db.set_value("Employee", emp, {
				"branch": branch, "status": status,
				"date_of_birth": dob or date(1990, other, 15),
				"date_of_joining": doj or date(now.year - 2, other, 15)})
			return emp

		cls.viewer = "c076.view@example.com"
		cls.v_emp = make("Viewer", user=cls.viewer)
		cls.today_b = make("TodayBirthday", dob=born(now.day))
		cls.earlier_b = make("EarlierBirthday", dob=born(yday)) if now.day != yday else None
		cls.anniv = make("FiveYears", doj=born(now.day, year=now.year - 5))
		cls.new_joiner = make("JoinedThisYear", doj=born(now.day, year=now.year))
		cls.south = make("SouthBirthday", branch="C076 South", dob=born(now.day))
		cls.nobranch = make("NoBranch", branch=None, dob=born(now.day))
		cls.leaver = make("LeftBirthday", dob=born(now.day), status="Left")
		cls.hidden = make("HiddenBirthday", dob=born(now.day))
		frappe.db.set_value("Employee", cls.hidden, home_people.HIDE, 1)
		cls.nologin = make("NoLogin", dob=born(now.day), login=False)
		cls.sm = "c076.bsm@example.com"
		make("BdaySm", user=cls.sm)
		ensure_user(cls.sm, roles=("Employee", "System Manager"))
		link_user_to_employee(frappe.db.get_value("Employee", {"user_id": cls.sm}), cls.sm)
		cls.extra = [make("Extra%d" % i, dob=born(now.day)) for i in range(4)]
		cls.lost = "c076.lost@example.com"
		make("NoBranchViewer", branch=None, user=cls.lost)
		cls.hr = "c076.bhr@example.com"
		make("BdayHr", user=cls.hr)
		ensure_user(cls.hr, roles=("Employee", "HR Manager"))
		link_user_to_employee(frappe.db.get_value("Employee", {"user_id": cls.hr}), cls.hr)
		cls.hr_user = "c076.bhruser@example.com"
		make("BdayHrUser", user=cls.hr_user)
		ensure_user(cls.hr_user, roles=("Employee", "HR User"))
		link_user_to_employee(frappe.db.get_value("Employee", {"user_id": cls.hr_user}), cls.hr_user)
		cls.dates = {str(v) for v in frappe.get_all(
			"Employee", filters={"last_name": "Bday076"}, pluck="date_of_birth")} | {str(v) for v in frappe.get_all(
			"Employee", filters={"last_name": "Bday076"}, pluck="date_of_joining")}
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("HR Settings", home_people.SWITCH, 1)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		frappe.db.set_single_value("HR Settings", home_people.SWITCH, 0)
		frappe.db.commit()

	def _as(self, user, see_all=1):
		frappe.set_user(user)
		try:
			return home_people.birthdays_this_month(see_all=see_all)
		finally:
			frappe.set_user("Administrator")

	def _names(self, got):
		return [(r["name"], r["kind"]) for r in got["rows"]]

	def test_the_switch_ships_off(self):
		meta = frappe.get_meta("HR Settings").get_field(home_people.SWITCH)
		self.assertEqual(str(meta.default), "0")

	def test_switch_off_returns_nothing_and_reads_nobody(self):
		frappe.db.set_single_value("HR Settings", home_people.SWITCH, 0)
		frappe.set_user(self.viewer)
		with _Spy() as spy:
			got = home_people.birthdays_this_month(see_all=1)
		frappe.set_user("Administrator")
		self.assertEqual(got, {"on": 0})
		self.assertFalse([q for q in spy.statements if "tabEmployee" in q])

	def test_birthday_reply_has_no_year(self):
		got = self._as(self.viewer)
		self.assertTrue(got["rows"])
		for row in got["rows"]:
			want = {"name", "kind", "day", "month"} | ({"years"} if row["kind"] == "anniversary" else set())
			self.assertEqual(set(row), want)
			for value in row.values():
				self.assertFalse(re.search(r"\b(19|20)\d\d\b", str(value)))
				self.assertNotIn(str(value), self.dates)
		self.assertFalse(re.search(r"(19|20)\d\d-\d\d-\d\d", frappe.as_json(got)))

	def test_own_branch_active_and_not_hidden_only(self):
		names = [n for n, _k in self._names(self._as(self.viewer))]
		self.assertIn("TodayBirthday Bday076", names)
		self.assertIn("FiveYears Bday076", names)
		for out in ("SouthBirthday", "NoBranch", "LeftBirthday", "HiddenBirthday", "JoinedThisYear", "NoLogin"):
			self.assertNotIn(out + " Bday076", names)

	def test_years_today_first_and_the_card_cap(self):
		got = self._as(self.viewer)
		five = [r for r in got["rows"] if r["name"] == "FiveYears Bday076"][0]
		self.assertEqual((five["kind"], five["years"], five["day"], five["month"]),
		                 ("anniversary", 5, self.now.day, self.now.month))
		days = [r["day"] for r in got["rows"]]
		upcoming = [d for d in days if d >= self.now.day]
		self.assertEqual(days[:len(upcoming)], sorted(upcoming))
		card = self._as(self.viewer, see_all=0)
		self.assertEqual(len(card["rows"]), min(5, got["total"]))
		self.assertEqual(card["total"], got["total"])
		self.assertGreater(got["total"], 5)

	def test_29_february_shows_on_the_28th_in_a_short_year(self):
		self.assertEqual(home_people._day(2, 29, 2027), 28)
		self.assertEqual(home_people._day(2, 29, 2028), 29)

	def test_no_branch_or_no_employee_sees_nobody(self):
		self.assertEqual(self._as(self.lost)["rows"], [])
		self.assertEqual(self._as("Administrator")["rows"], [])
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			home_people.birthdays_this_month()

	def test_a_person_who_leaves_disappears(self):
		frappe.db.set_value("Employee", self.today_b, "status", "Left")
		names = [n for n, _k in self._names(self._as(self.viewer))]
		self.assertNotIn("TodayBirthday Bday076", names)

	def test_the_tick_changes_only_my_own_record(self):
		self.assertEqual(list(inspect.signature(home_people.set_birthday_hide).parameters), ["value"])
		frappe.set_user(self.viewer)
		home_people.set_birthday_hide(1)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Employee", self.v_emp, home_people.HIDE), 1)
		self.assertEqual(frappe.db.get_value("Employee", self.today_b, home_people.HIDE), 0)
		self.assertEqual(self._as(self.viewer)["hidden"], 1)
		self.assertTrue(frappe.db.exists("Comment", {"reference_doctype": "Employee", "reference_name": self.v_emp,
		                                             "content": "Hid their birthday on Home", "owner": self.viewer}))
		# Hidden from a colleague in the same branch, even with a birthday today.
		frappe.db.set_value("Employee", self.v_emp, "date_of_birth", date(1990, self.now.month, self.now.day))
		self.assertNotIn("Viewer Bday076", [n for n, _k in self._names(self._as(self.hr))])
		frappe.db.set_value("Employee", self.v_emp, home_people.HIDE, 0)
		self.assertIn("Viewer Bday076", [n for n, _k in self._names(self._as(self.hr))])

	def test_hr_cannot_change_someone_elses_tick(self):
		frappe.set_user(self.hr)
		try:
			doc = frappe.get_doc("Employee", self.today_b)
			doc.set(home_people.HIDE, 1)
			doc.save()
		except frappe.ValidationError:
			pass
		from frappe.client import set_value
		try:
			set_value("Employee", self.today_b, home_people.HIDE, 1)
		except frappe.ValidationError:
			pass
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Employee", self.today_b, home_people.HIDE), 0)

	def test_only_a_system_manager_changes_the_switch_and_history_says_who(self):
		for user in (self.viewer, self.hr_user, self.hr):
			with self.subTest(user=user):
				frappe.set_user(user)
				with self.assertRaises(frappe.PermissionError):
					home_people.set_birthdays_switch(0)
				with self.assertRaises(frappe.PermissionError):
					home_people.birthdays_switch_state()
				frappe.set_user("Administrator")
		frappe.set_user(self.sm)
		got = home_people.set_birthdays_switch(0)
		frappe.set_user("Administrator")
		self.assertEqual(got["on"], 0)
		self.assertEqual(got["changed_by"], frappe.db.get_value("User", self.sm, "full_name"))
		self.assertEqual(got["changed_on"], today())
		self.assertEqual(got["people"], frappe.db.count("Employee", {"status": "Active"}))
		self.assertEqual(set(got), {"on", "people", "changed_by", "changed_on"})

	def test_a_colleague_cannot_read_the_dates_through_frappe(self):
		"""AC-120. What stops it is ERPNext's own Employee User Permission, made
		when a login is linked on the Employee form; the fixture links with a
		direct write, so it adds the same row real data has."""
		from frappe.permissions import add_user_permission

		if not frappe.db.exists("User Permission", {"user": self.viewer, "allow": "Employee"}):
			add_user_permission("Employee", self.v_emp, self.viewer)
		frappe.set_user(self.viewer)
		try:
			rows = frappe.get_list("Employee", filters={"name": self.today_b},
			                       fields=["name", "date_of_birth", "date_of_joining"])
		except frappe.PermissionError:
			rows = []
		frappe.set_user("Administrator")
		self.assertFalse([r for r in rows if r.get("date_of_birth") or r.get("date_of_joining")])
