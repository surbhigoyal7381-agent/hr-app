"""Leave left comes from Frappe HR's leave ledger (slice 035, commit 1).

The portal used to work leave out as "allocated minus approved Leave
Applications". That missed the days the late-coming rule takes, which reach the
ledger as "Attendance Deduction" entries. On PP Jewellers 97 people were shown
76 days of Casual Leave they did not have, while the apply form's preview, the
leave check and the late rule itself all read the ledger and said less.

Decision Q-e (14 Sep 2026): leave left is the ledger's figure, late-rule days
included. Every screen that shows a balance is checked here, with the late rule
having taken 3 of 8 days, so any one of them going back to its own sum fails.

The manager in these tests is the reporting manager but NOT the named leave
approver. Frappe HR's get_leave_details would refuse that manager; the portal
must not.
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from alvoraa_portal import hr_api
from alvoraa_portal.tests.leave_fixtures import (
	ensure_employee,
	ensure_employee_with_leave,
	ensure_leave_type,
	ensure_user,
	link_user_to_employee,
)

LEAVE_TYPE = "Alvoraa Ledger 035"
ALLOCATED = 8
LATE_RULE_TOOK = 3
WORKER_USER = "ledger.worker035@example.com"
BOSS_USER = "ledger.boss035@example.com"


def _late_rule_takes(employee, leave_type, days):
	"""A ledger entry exactly like the one AttendanceDeduction.consume_leave writes.

	The transaction it points at is not created: the ledger is what every balance
	reads, and building a whole week of late arrivals to get one row would make
	this a test of the late rule instead of the screens.
	"""
	doc = frappe.get_doc({
		"doctype": "Leave Ledger Entry",
		"employee": employee,
		"leave_type": leave_type,
		"transaction_type": "Attendance Deduction",
		"transaction_name": "ALV-035-LATE-RULE",
		"leaves": -days,
		"from_date": today(),
		"to_date": today(),
		"company": frappe.db.get_value("Employee", employee, "company"),
	})
	doc.flags.ignore_links = True
	doc.flags.ignore_permissions = True
	doc.submit()


def _row(rows, leave_type=LEAVE_TYPE):
	found = [r for r in rows if r["leave_type"] == leave_type]
	assert found, f"{leave_type} missing from {rows}"
	return found[0]


class TestLeaveLeftFromTheLedger(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		ensure_leave_type(LEAVE_TYPE)
		cls.worker = ensure_employee_with_leave("Ledger035", LEAVE_TYPE, days=ALLOCATED,
		                                        last_name="Worker")
		cls.boss = ensure_employee("Ledger035", "Boss")
		link_user_to_employee(cls.worker, ensure_user(WORKER_USER, roles=("Employee",)))
		link_user_to_employee(cls.boss, ensure_user(BOSS_USER, roles=("Employee",)))
		# The reporting manager, deliberately NOT the named leave approver.
		frappe.db.set_value("Employee", cls.worker, {"reports_to": cls.boss, "leave_approver": None})
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")
		_late_rule_takes(self.worker, LEAVE_TYPE, LATE_RULE_TOOK)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	# ── every screen that shows a balance ──────────────────────────────────

	def test_home_takes_off_the_days_the_late_rule_took(self):
		frappe.set_user(WORKER_USER)
		row = _row(hr_api.get_employee_dashboard()["leave_balances"])
		self.assertEqual(row["balance"], ALLOCATED - LATE_RULE_TOOK)
		self.assertEqual(row["total"], ALLOCATED)
		self.assertEqual(row["taken"], LATE_RULE_TOOK)

	def test_leave_screen_agrees_with_the_apply_preview(self):
		"""The drop-down and the preview on one form must say the same number."""
		frappe.set_user(WORKER_USER)
		row = _row(hr_api.get_leave_summary()["balances"])
		preview = hr_api.preview_leave_request(LEAVE_TYPE, today(), today())
		self.assertEqual(row["balance"], ALLOCATED - LATE_RULE_TOOK)
		self.assertEqual(row["balance"], preview["balance"])
		self.assertEqual(row["taken"], LATE_RULE_TOOK)

	def test_hr_acting_for_someone_sees_the_ledger(self):
		row = _row(hr_api.get_leave_summary(employee_id=self.worker)["balances"])
		self.assertEqual(row["balance"], ALLOCATED - LATE_RULE_TOOK)

	def test_manager_scorecard_sees_the_ledger_without_being_the_leave_approver(self):
		frappe.set_user(BOSS_USER)
		row = _row(hr_api.get_employee_scorecard(self.worker)["leave_balances"])
		self.assertEqual(row["balance"], ALLOCATED - LATE_RULE_TOOK)
		self.assertEqual(row["allocated"], ALLOCATED)
		self.assertEqual(row["taken"], LATE_RULE_TOOK)

	def test_manager_detail_sees_the_ledger_without_being_the_leave_approver(self):
		frappe.set_user(BOSS_USER)
		row = _row(hr_api.get_employee_detail_for_manager(self.worker)["leave_balances"])
		self.assertEqual(row["balance"], ALLOCATED - LATE_RULE_TOOK)

	# ── the helper is Frappe HR's figure, not a fifth opinion ───────────────

	def test_helper_equals_frappe_hr_balance(self):
		from hrms.hr.doctype.leave_application.leave_application import (
			get_leave_balance_on,
			get_leave_details,
		)

		row = _row(hr_api._ledger_leave_balances(self.worker, today()))
		frappe_hr = get_leave_balance_on(self.worker, LEAVE_TYPE, today(),
		                                 consider_all_leaves_in_the_allocation_period=True)
		details = get_leave_details(self.worker, today())["leave_allocation"][LEAVE_TYPE]
		self.assertEqual(row["balance"], frappe_hr)
		self.assertEqual(row["balance"], details["remaining_leaves"])
		self.assertEqual(row["taken"], details["leaves_taken"])
		self.assertEqual(row["total"], details["total_leaves"])

	def test_late_rule_days_reach_frappe_hr_at_all(self):
		"""Guards the 4-line local edit in hrms get_leaves_for_period.

		Frappe HR counts "Attendance Deduction" entries only because of that edit.
		If an upstream update drops it, every balance - Frappe's and ours - would
		ignore late-rule days again, and this is the test that notices.
		"""
		from hrms.hr.doctype.leave_application.leave_application import get_leaves_for_period

		alloc = frappe.get_all("Leave Allocation", filters={"employee": self.worker,
		                       "leave_type": LEAVE_TYPE, "docstatus": 1},
		                       fields=["from_date", "to_date"], limit=1)[0]
		self.assertEqual(get_leaves_for_period(self.worker, LEAVE_TYPE, alloc.from_date,
		                                       alloc.to_date), -LATE_RULE_TOOK)

	def test_query_count_is_bounded(self):
		"""One leave type costs a fixed handful of queries, not one per ledger row."""
		count = {"n": 0}
		real_sql = frappe.db.sql

		def counting(*args, **kwargs):
			count["n"] += 1
			return real_sql(*args, **kwargs)

		frappe.db.sql = counting
		try:
			hr_api._ledger_leave_balances(self.worker, today())
		finally:
			frappe.db.sql = real_sql
		self.assertLessEqual(count["n"], 12, f"{count['n']} queries for one leave type")


class TestHomeLeaveCardReadsTheServersKey(FrappeTestCase):
	"""The Home card read `total_leaves`; the server has always sent `total`.

	So "of 8" never showed, and a fully used type (balance 0) was hidden. With
	the ledger fix Rahul's Casual Leave becomes 0, so without this the fix would
	have made his leave vanish from Home instead of reading "0 of 8".
	"""

	def test_the_card_reads_total(self):
		import os

		import alvoraa_portal

		path = os.path.join(os.path.dirname(alvoraa_portal.__file__), "www", "hrms-employee.html")
		with open(path, encoding="utf-8") as f:
			page = f.read()
		body = re.search(r"function loadHomeLeave\(balances\) \{(.*?)\n\}", page, re.S)
		self.assertTrue(body, "loadHomeLeave not found - update this test if it moved")
		self.assertNotIn("total_leaves", body.group(1))
		self.assertIn("b.total", body.group(1))
