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

from alvoraa_portal import hr_api, inbox_api
from alvoraa_portal.tests.leave_fixtures import (
	WEEK_MON,
	WEEK_TUE,
	ensure_employee_with_leave,
	ensure_leave_type,
	ensure_user,
	link_user_to_employee,
	reset_leave_applications,
)

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
				self.assertEqual(set(inbox_api.row_keys(key)), old | {"waiting_since"})

	def test_the_part_list_did_not_change(self):
		self.assertEqual([k for k, _r in inbox_api.PARTS], list(OLD_KEYS))


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
