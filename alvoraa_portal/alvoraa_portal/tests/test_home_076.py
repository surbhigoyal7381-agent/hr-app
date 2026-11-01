"""Slice 076, Part A: Home loses Activity, gains Pending and a decline reason.

Pin tests, named so a bad merge that drops the feature fails by name:

  test_activity_endpoint_is_gone
  test_every_part_row_is_the_old_keys_plus_waiting_since
  test_a_decline_reason_is_saved_and_only_its_owner_reads_it
  test_the_reason_is_validated_and_escaped
  test_the_approval_rules_are_unchanged_by_the_reason

The notices half is in test_notices_076 (it needs the grooming world).
"""

import os
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal import hr_api, inbox_api
from alvoraa_portal.tests.test_decided_as_045 import _Corrections
from alvoraa_portal.tests.leave_fixtures import (
	WEEK_MON,
	WEEK_TUE,
	ensure_employee_with_leave,
	ensure_leave_type,
	ensure_user,
	link_user_to_employee as _link_user_to_employee,
	reset_leave_applications,
)


def link_user_to_employee(employee, email):
	"""Link, then hand the Employee role back if the link cost the user it.

	A new user saved before any Employee points at it loses the Employee role
	(ERPNext validate_employee_role), so on a fresh site such as CI every call
	the test made as that user was refused. A site that already had the user
	from an earlier run passed, which is how this got through (CI, 28 Oct).
	"""
	_link_user_to_employee(employee, email)
	user = frappe.get_doc("User", email)
	if not any(r.role == "Employee" for r in user.roles):
		user.append("roles", {"role": "Employee"})
		user.flags.ignore_permissions = True
		user.save(ignore_permissions=True)

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The key lists as slice 042 left them. Slice 076 adds exactly one key to each.
OLD_KEYS = {
	"leave_approvals": {"name", "employee_name", "from_date", "to_date", "leave_type",
	                    "total_days", "context", "action", "half_day", "lwp_in_play",
	                    "lwp_limit", "special_day", "chain_top"},
	"goal_updates": {"name", "kind", "employee_name", "subject", "logged_on", "value", "action"},
	"attendance_fixes": {"name", "employee_name", "from_date", "to_date", "reason", "context",
	                     "action", "can_decide"},
	"shift_requests": {"name", "employee_name", "from_date", "to_date", "shift_type", "action"},
	"policies": {"name", "title", "version", "action"},
	"my_requests": {"name", "kind", "title", "from_date", "to_date", "state", "says", "note",
	                "can_withdraw", "action"},
}


class TestPartKeys(unittest.TestCase):
	def test_every_part_row_is_the_old_keys_plus_waiting_since(self):
		for key, old in OLD_KEYS.items():
			with self.subTest(part=key):
				extra = {"waiting_since"} | ({"document"} if key == "goal_updates" else set())
				self.assertEqual(set(inbox_api.row_keys(key)), old | extra)

	def test_the_part_list_did_not_change(self):
		# Part C adds exactly one part, expense_approvals, after leave (on purpose).
		want = list(OLD_KEYS)
		want.insert(1, "expense_approvals")
		self.assertEqual([k for k, _r in inbox_api.PARTS], want)


class TestActivityIsGone(unittest.TestCase):
	def test_activity_endpoint_is_gone(self):
		self.assertFalse(hasattr(hr_api, "get_portal_activity"))
		with self.assertRaises(AttributeError):
			frappe.get_attr("alvoraa_portal.hr_api.get_portal_activity")

	def test_nothing_in_the_app_still_asks_for_it(self):
		bad = []
		for root, _dirs, files in os.walk(APP):
			if "tests" in root.split(os.sep) or "node_modules" in root:
				continue
			for f in files:
				if not f.endswith((".py", ".js", ".html")):
					continue
				text = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
				for word in ("get_portal_activity", "homeActivity", "renderActivityFeed"):
					if word in text:
						bad.append("%s: %s" % (f, word))
		self.assertEqual(bad, [])

	def test_the_home_page_has_no_activity_card_and_no_side_column(self):
		page = open(os.path.join(APP, "templates", "includes", "ess", "parts", "home.html"),
		            encoding="utf-8").read()
		self.assertNotIn("home-activity-card", page)
		self.assertNotIn("home-body-grid", page)
		css = open(os.path.join(APP, "public", "css", "ess", "panels.css"), encoding="utf-8").read()
		self.assertNotIn("1fr 300px", css)


class TestLeaveDeclineReason(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.lt = ensure_leave_type("Alvoraa Casual")
		cls.mgr_user = ensure_user("h076.mgr@example.com", roles=("Employee",))
		cls.mgr_emp = ensure_employee_with_leave("H076Mgr", cls.lt, days=10, last_name="Boss")
		link_user_to_employee(cls.mgr_emp, cls.mgr_user)
		cls.a_user = ensure_user("h076.a@example.com", roles=("Employee",))
		cls.a_emp = ensure_employee_with_leave("H076A", cls.lt, days=10, last_name="Staff")
		link_user_to_employee(cls.a_emp, cls.a_user)
		cls.b_user = ensure_user("h076.b@example.com", roles=("Employee",))
		cls.b_emp = ensure_employee_with_leave("H076B", cls.lt, days=10, last_name="Staff")
		link_user_to_employee(cls.b_emp, cls.b_user)
		cls.x_user = ensure_user("h076.x@example.com", roles=("Employee",))
		cls.x_emp = ensure_employee_with_leave("H076X", cls.lt, days=10, last_name="Other")
		link_user_to_employee(cls.x_emp, cls.x_user)
		# The manager is the named leave approver on the record, as real data has
		# it; Frappe HR checks that when the leave is decided.
		for emp in (cls.a_emp, cls.b_emp):
			frappe.db.set_value("Employee", emp, "leave_approver", cls.mgr_user)
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")
		for emp in (self.mgr_emp, self.a_emp, self.b_emp, self.x_emp):
			reset_leave_applications(emp)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _open_leave(self, emp, day=WEEK_MON):
		la = frappe.get_doc({
			"doctype": "Leave Application", "employee": emp, "leave_type": self.lt,
			"from_date": day, "to_date": day, "status": "Open",
			"leave_approver": self.mgr_user,
			"company": frappe.db.get_value("Employee", emp, "company"),
		})
		la.insert(ignore_permissions=True)
		return la.name

	def test_a_decline_reason_is_saved_and_only_its_owner_reads_it(self):
		la = self._open_leave(self.a_emp)
		frappe.set_user(self.mgr_user)
		out = hr_api.action_leave(la, "reject", reason="Two people are away that week.")
		self.assertEqual(out["status"], "Rejected")

		# The employee reads it on their own Rejected row.
		frappe.set_user(self.a_user)
		rows = hr_api.get_leave_summary()["applications"]
		mine = [r for r in rows if r["name"] == la]
		self.assertEqual(len(mine), 1)
		self.assertEqual(mine[0]["decline_reason"], "Two people are away that week.")

		# A colleague never sees it, and a stranger asking for A's record gets
		# their own.
		frappe.set_user(self.b_user)
		summary = hr_api.get_leave_summary(employee_id=self.a_emp)
		self.assertEqual(summary["employee"]["name"], self.b_emp)
		self.assertNotIn(la, [r["name"] for r in summary["applications"]])
		self.assertNotIn("Two people", frappe.as_json(summary))

	def test_a_decline_without_a_reason_behaves_as_before(self):
		la = self._open_leave(self.a_emp)
		frappe.set_user(self.mgr_user)
		out = hr_api.action_leave(la, "reject")
		self.assertEqual(out["status"], "Rejected")
		frappe.set_user(self.a_user)
		mine = [r for r in hr_api.get_leave_summary()["applications"] if r["name"] == la][0]
		self.assertIsNone(mine["decline_reason"])
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count("Comment", {
			"reference_doctype": "Leave Application", "reference_name": la,
			"subject": hr_api.DECLINE_REASON_SUBJECT}), 0)

	def test_the_reason_is_validated_and_escaped(self):
		la = self._open_leave(self.a_emp)
		frappe.set_user(self.mgr_user)
		for bad in ("", "   ", "x" * 141):
			with self.subTest(reason=len(bad)):
				with self.assertRaises(frappe.ValidationError):
					hr_api.action_leave(la, "reject", reason=bad)
		with self.assertRaises(frappe.ValidationError):
			hr_api.action_leave(la, "approve", reason="Fine")
		self.assertEqual(frappe.db.get_value("Leave Application", la, "docstatus"), 0,
		                 "a refused call must decide nothing")
		hr_api.action_leave(la, "reject", reason="<img src=x onerror=alert(1)>")
		frappe.set_user("Administrator")
		stored = frappe.db.get_value("Comment", {
			"reference_name": la, "subject": hr_api.DECLINE_REASON_SUBJECT}, "content")
		self.assertNotIn("<img", stored, "Desk draws a comment as HTML; it must be escaped")
		frappe.set_user(self.a_user)
		mine = [r for r in hr_api.get_leave_summary()["applications"] if r["name"] == la][0]
		self.assertEqual(mine["decline_reason"], "<img src=x onerror=alert(1)>",
		                 "the screen gets the words back; the screen escapes them")

	def test_an_ordinary_note_on_the_leave_is_not_shown_as_the_reason(self):
		la = self._open_leave(self.a_emp)
		frappe.set_user(self.mgr_user)
		hr_api.action_leave(la, "reject")
		frappe.set_user("Administrator")
		frappe.get_doc("Leave Application", la).add_comment("Comment", "HR note: call him first.")
		frappe.set_user(self.a_user)
		mine = [r for r in hr_api.get_leave_summary()["applications"] if r["name"] == la][0]
		self.assertIsNone(mine["decline_reason"])

	def test_the_approval_rules_are_unchanged_by_the_reason(self):
		la = self._open_leave(self.a_emp)
		# Not the approver: refused, and no comment is written.
		frappe.set_user(self.x_user)
		with self.assertRaises(frappe.PermissionError):
			hr_api.action_leave(la, "reject", reason="Not mine to decline")
		# The claimant: refused.
		frappe.set_user(self.a_user)
		with self.assertRaises(frappe.PermissionError):
			hr_api.action_leave(la, "reject", reason="I decline myself")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Leave Application", la, "docstatus"), 0)
		self.assertEqual(frappe.db.count("Comment", {
			"reference_name": la, "subject": hr_api.DECLINE_REASON_SUBJECT}), 0)

	def test_an_approval_still_works_with_two_arguments(self):
		la = self._open_leave(self.b_emp, WEEK_TUE)
		frappe.set_user(self.mgr_user)
		self.assertEqual(hr_api.action_leave(la, "approve")["status"], "Approved")

	def test_the_approvers_inbox_row_carries_when_it_was_filed(self):
		la = self._open_leave(self.a_emp)
		frappe.set_user(self.mgr_user)
		part = [p for p in inbox_api.get_inbox()["parts"] if p["key"] == "leave_approvals"][0]
		row = [r for r in part["rows"] if r["name"] == la][0]
		self.assertTrue(row["waiting_since"])
		self.assertEqual(set(row), set(inbox_api.row_keys("leave_approvals")))

	def test_the_count_is_still_the_sum_of_the_parts(self):
		self._open_leave(self.a_emp)
		frappe.set_user(self.mgr_user)
		nav = inbox_api.get_nav_counts()
		inbox = inbox_api.get_inbox()
		self.assertEqual(nav["total"], sum(p["count"] for p in nav["parts"]))
		self.assertEqual(inbox["total"], nav["total"])
		self.assertEqual([p["count"] for p in inbox["parts"]], [p["count"] for p in nav["parts"]])


class TestTheQueueDoesNotCostAQueryPerFix(_Corrections):
	"""AC-72. Deciding whether HR may press Approve asked the permission system
	about the employee's manager once per queued fix, and the inbox did it twice
	a call (count, then rows). It is once per manager now, once per call."""

	def test_the_manager_is_asked_about_once_however_many_fixes_are_queued(self):
		from unittest.mock import patch

		real = frappe.has_permission
		asked = []

		def spy(doctype=None, ptype="read", doc=None, user=None, **kw):
			if doctype == ac.REQUEST and ptype == "submit":
				asked.append(user)
			return real(doctype, ptype, doc, user=user, **kw)

		self.as_user(self.priya_user)
		rows = lambda n: [{"employee": e, "creation": "%s 09:00:00" % add_days(nowdate(), -1),
		                   "owner": "someone@example.com"} for e in self.sandeep_reports[:n]]
		with patch.object(frappe, "has_permission", spy):
			ac._with_decide_flag(rows(1), self.priya_user)
			one = len(asked)
			asked.clear()
			many = rows(len(self.sandeep_reports))
			ac._with_decide_flag(many, self.priya_user)
		self.assertGreaterEqual(len(many), 2, "the fixture must have several reports")
		self.assertEqual(one, 1)
		self.assertEqual(len(asked), 1, "one lookup for the manager, not one per fix")
		self.assertTrue(all("can_decide" in r for r in many))


class TestGoalUpdateRowsCarryTheGoalOnlyInScope(FrappeTestCase):
	"""SEC-19. A goal-update row names the goal it belongs to so Home can open it.
	The id comes from the same scope subquery as the row, so a caller sees ids
	only for goals inside their own scope."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from alvoraa_portal.tests.test_portal_security_010 import _second_company
		cls.company_b = _second_company()      # before the people, as that helper asks
		lt = ensure_leave_type("Alvoraa Casual")
		cls.mgr_user = ensure_user("g076.mgr@example.com", roles=("Employee",))
		cls.mgr_emp = ensure_employee_with_leave("G076Mgr", lt, days=1, last_name="Boss")
		link_user_to_employee(cls.mgr_emp, cls.mgr_user)
		cls.other_user = ensure_user("g076.other@example.com", roles=("Employee",))
		cls.other_emp = ensure_employee_with_leave("G076Other", lt, days=1, last_name="Boss")
		link_user_to_employee(cls.other_emp, cls.other_user)
		cls.a_emp = ensure_employee_with_leave("G076A", lt, days=1, last_name="Staff")
		cls.x_emp = ensure_employee_with_leave("G076X", lt, days=1, last_name="Staff")
		cls.a_user = ensure_user("g076.a@example.com", roles=("Employee",))
		link_user_to_employee(cls.a_emp, cls.a_user)
		frappe.db.set_value("Employee", cls.a_emp, "reports_to", cls.mgr_emp)
		frappe.db.set_value("Employee", cls.x_emp, "reports_to", cls.other_emp)
		cls.hr_user = ensure_user("g076.hr@example.com", roles=("HR Manager", "Employee"))
		hr_emp = ensure_employee_with_leave("G076Hr", lt, days=1, last_name="Hr")
		link_user_to_employee(hr_emp, cls.hr_user)
		cls.sm_user = ensure_user("g076.sm@example.com", roles=("System Manager", "Employee"))
		sm_emp = ensure_employee_with_leave("G076Sm", lt, days=1, last_name="Sm")
		link_user_to_employee(sm_emp, cls.sm_user)
		cls.goals = {}
		for key, emp in (("a", cls.a_emp), ("x", cls.x_emp)):
			g = frappe.get_doc({
				"doctype": "Individual Goal", "employee": emp, "goal_name": "G076 goal " + key,
				"target_value": 100, "start_date": add_days(nowdate(), -30),
				"end_date": add_days(nowdate(), 200), "status": "Active"})
			g.flags.ignore_permissions = True
			g.insert(ignore_permissions=True)
			g.append("progress_updates", {"log_date": add_days(nowdate(), -2), "value": 5,
			                              "approval_status": "Pending", "note": "G076"})
			g.flags.ignore_permissions = True
			g.save(ignore_permissions=True)
			cls.goals[key] = g.name
		frappe.db.commit()
		frappe.clear_cache()      # roles were just set; no stale per-user permission cache

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for name in cls.goals.values():
			frappe.delete_doc("Individual Goal", name, force=True, ignore_permissions=True)
		frappe.db.commit()
		super().tearDownClass()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _ids(self, user):
		frappe.set_user(user)
		part = [p for p in inbox_api.get_inbox()["parts"] if p["key"] == "goal_updates"][0]
		return {r["document"] for r in part["rows"] if r["document"] in self.goals.values()}, part

	def test_a_manager_gets_the_goal_of_their_own_report_and_no_other(self):
		ids, part = self._ids(self.mgr_user)
		self.assertEqual(ids, {self.goals["a"]})
		self.assertEqual(set(part["rows"][0]), set(inbox_api.row_keys("goal_updates")))

	def test_a_manager_outside_scope_gets_no_id_and_cannot_open_or_approve(self):
		ids, _p = self._ids(self.other_user)       # manages X, not A
		self.assertNotIn(self.goals["a"], ids)
		frappe.set_user(self.other_user)
		row = frappe.get_doc("Individual Goal", self.goals["a"]).progress_updates[0].name
		from alvoraa_portal import goals_api
		with self.assertRaises(frappe.PermissionError):
			goals_api.approve_goal_update(self.goals["a"], row, "Approved")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.get_doc("Individual Goal", self.goals["a"]).progress_updates[0]
		                 .approval_status, "Pending")

	def test_a_normal_employee_gets_no_goal_ids(self):
		ids, part = self._ids(self.a_user)
		self.assertEqual((ids, part["count"], part["rows"]), (set(), 0, []))

	def test_hr_and_system_manager_get_the_ids_in_their_scope(self):
		for user in (self.hr_user, self.sm_user):
			with self.subTest(user=user):
				ids, _p = self._ids(user)
				self.assertEqual(ids, set(self.goals.values()))

	def test_hr_limited_to_another_company_gets_no_id_and_cannot_approve(self):
		"""A System Manager (the CXO, by Surbhi's answer) sees every company by
		design - `access.permitted_companies` says so - so "outside scope" is a
		person limited to a company that is not these people's: HR on another
		company."""
		user = ensure_user("g076.cxo@example.com", roles=("HR Manager", "Employee"))
		emp = ensure_employee_with_leave("G076Cxo", ensure_leave_type("Alvoraa Casual"),
		                                 days=1, last_name="Cxo")
		link_user_to_employee(emp, user)
		frappe.get_doc({"doctype": "User Permission", "user": user, "allow": "Company",
		                "for_value": self.company_b, "apply_to_all_doctypes": 1}).insert(
			ignore_permissions=True)
		frappe.db.commit()
		frappe.clear_cache()
		self.addCleanup(lambda: (frappe.set_user("Administrator"),
		                         frappe.db.delete("User Permission", {"user": user}),
		                         frappe.db.commit()))
		ids, _p = self._ids(user)
		self.assertEqual(ids, set())
		from alvoraa_portal import goals_api
		row = frappe.get_doc("Individual Goal", self.goals["a"]).progress_updates[0].name
		with self.assertRaises(frappe.PermissionError):
			goals_api.approve_goal_update(self.goals["a"], row, "Approved")

	def test_the_manager_can_approve_the_update_the_row_points_at(self):
		from alvoraa_portal import goals_api
		frappe.set_user(self.mgr_user)
		part = [p for p in inbox_api.get_inbox()["parts"] if p["key"] == "goal_updates"][0]
		row = [r for r in part["rows"] if r["document"] == self.goals["a"]][0]
		goals_api.approve_goal_update(row["document"], row["name"], "Approved")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.get_doc("Individual Goal", self.goals["a"]).progress_updates[0]
		                 .approval_status, "Approved")

	# ── KPI updates opened from Pending (the log says who may approve) ────────

	def _kpi(self):
		k = frappe.get_doc({"doctype": "KPI", "kpi_name": "G076 KPI", "employee": self.a_emp,
							"target_value": 10})
		k.append("progress_log", {"log_date": nowdate(), "value": 1, "approval_status": "Pending"})
		k.insert(ignore_permissions=True)
		frappe.db.commit()
		self.addCleanup(lambda: (frappe.set_user("Administrator"),
								 frappe.delete_doc("KPI", k.name, force=True, ignore_permissions=True),
								 frappe.db.commit()))
		return k.name, k.progress_log[0].name

	def test_kpi_log_tells_the_in_scope_manager_and_hr_they_may_approve(self):
		from alvoraa_portal import performance_api
		kpi, _row = self._kpi()
		for user in (self.mgr_user, self.hr_user):
			frappe.set_user(user)
			self.assertTrue(performance_api.get_kpi_update_log(kpi)[0]["can_action"], user)

	def test_kpi_log_says_no_to_the_employee_themselves(self):
		from alvoraa_portal import performance_api
		kpi, row = self._kpi()
		frappe.set_user(self.a_user)
		self.assertFalse(performance_api.get_kpi_update_log(kpi)[0]["can_action"])
		with self.assertRaises(frappe.PermissionError):
			performance_api.approve_kpi_update(kpi, row, "Approved")

	def test_an_outside_manager_can_neither_read_nor_approve_the_kpi(self):
		from alvoraa_portal import performance_api
		kpi, row = self._kpi()
		frappe.set_user(self.other_user)
		with self.assertRaises(frappe.PermissionError):
			performance_api.get_kpi_update_log(kpi)
		with self.assertRaises(frappe.PermissionError):
			performance_api.approve_kpi_update(kpi, row, "Approved")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.get_doc("KPI", kpi).progress_log[0].approval_status, "Pending")

	def test_the_manager_can_approve_what_the_log_offered(self):
		from alvoraa_portal import performance_api
		kpi, row = self._kpi()
		frappe.set_user(self.mgr_user)
		self.assertTrue(performance_api.get_kpi_update_log(kpi)[0]["can_action"])
		performance_api.approve_kpi_update(kpi, row, "Approved")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.get_doc("KPI", kpi).progress_log[0].approval_status, "Approved")
