"""Every number equals the thing it claims to count (slice 035, takeover review).

Surbhi, 23 Sep 2026: "there should be hundred percent accuracy in calculations
and numbers." Commits 1-3 made each figure right on its own. These tests take
the next step and check the figures against EACH OTHER, because a number that is
right by itself can still be a lie on the screen:

  * a chip that counts 1 goal sitting on top of a list of 2
  * "Due in 30 Days: 3" opening a list with 1 row in it
  * a cycle banner naming one quarter while the numbers under it count another
  * one manager, two screens, two different "average progress" for one person
  * a leave card where taken + left does not add up to the total
  * a balance of -2 shown as 0

Each test below fails on the code as it was inherited.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from alvoraa_portal import goals_api, hr_api
from alvoraa_portal.tests.leave_fixtures import (
	ensure_employee,
	ensure_employee_with_leave,
	ensure_leave_type,
	ensure_user,
	link_user_to_employee,
)
from alvoraa_portal.tests.test_goal_cycle_035 import GoalCycleCase

WORKER_USER = "match.worker035@example.com"
BOSS_USER = "match.boss035@example.com"
YEAR = 2952   # this module's own year, clear of test_goal_cycle_035's 2951
SECOND_COMPANY = "Numbers035 Other Co"


def ensure_second_company(not_this_one):
	"""A company that is NOT the employee's, made once and committed.

	Inserting a Company commits (ERPNext builds its chart of accounts), which
	would end a test's transaction and leave its fixtures behind, so this is
	never called inside a test. Any existing other company will do - which one
	ensure_company() happened to pick must not decide whether this test passes.
	"""
	other = frappe.db.get_value("Company", {"name": ["!=", not_this_one]}, "name")
	if other:
		return other
	first = not_this_one
	doc = frappe.get_doc({
			"doctype": "Company", "company_name": SECOND_COMPANY,
		"default_currency": frappe.db.get_value("Company", first, "default_currency"),
		"country": frappe.db.get_value("Company", first, "country"),
	})
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


class NumbersCase(GoalCycleCase):
	"""GoalCycleCase with this module's own cycle years, so the two modules can
	run in the same suite without one's records answering the other's query."""

	def cycle(self, quarter, status):
		start = f"{YEAR}-{3 * quarter - 2:02d}-01"
		end = {1: f"{YEAR}-03-31", 2: f"{YEAR}-06-30",
		       3: f"{YEAR}-09-30", 4: f"{YEAR}-12-31"}[quarter]
		doc = frappe.get_doc({
			"doctype": "Appraisal Cycle", "cycle_name": f"N035 Q{quarter} {YEAR}",
			"company": self.company, "start_date": start, "end_date": end,
			"status": "In Progress",
		})
		doc.insert(ignore_permissions=True)
		if status != "In Progress":
			frappe.db.set_value("Appraisal Cycle", doc.name, "status", status,
			                    update_modified=False)
		return doc.name


# ══════════════════════════════════════════════════════════════════════════
# Goals: the chips, the banner and the list must describe one set of goals
# ══════════════════════════════════════════════════════════════════════════

class TestTheChipsMatchTheList(NumbersCase):
	"""get_portal_context's numbers against get_my_goals' rows, on one screen."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.other_company = ensure_second_company(cls.company)
		link_user_to_employee(cls.worker, ensure_user(WORKER_USER, roles=("Employee",)))
		frappe.db.commit()

	def setUp(self):
		super().setUp()
		self.q1 = self.cycle(1, "Completed")
		self.q2 = self.cycle(2, "In Progress")
		frappe.set_user("Administrator")

	def _context_and_list(self):
		frappe.set_user(WORKER_USER)
		try:
			return goals_api.get_portal_context(), goals_api.get_my_goals()
		finally:
			frappe.set_user("Administrator")

	def test_active_goals_chip_equals_the_rows_in_the_list(self):
		"""A finished quarter's goal left Active made the chip and the list disagree."""
		self.goal(self.worker, self.q1, 100, status="Active")
		self.goal(self.worker, self.q2, 40, status="Active")

		ctx, rows = self._context_and_list()
		self.assertEqual(ctx["dashboard"]["active"], len([g for g in rows if g["status"] == "Active"]))
		self.assertEqual(ctx["dashboard"]["total"], len(rows))
		# And the number is this quarter's one goal, not both.
		self.assertEqual(ctx["dashboard"]["total"], 1)

	def test_avg_progress_chip_equals_the_average_of_the_rows_shown(self):
		self.goal(self.worker, self.q1, 100)
		self.goal(self.worker, self.q2, 40)

		ctx, rows = self._context_and_list()
		shown = [g for g in rows if g["status"] != "Cancelled"]
		self.assertEqual(
			ctx["dashboard"]["avg_progress"],
			round(sum(float(g["progress_pct"] or 0) for g in shown) / len(shown), 1),
		)
		self.assertEqual(ctx["dashboard"]["avg_progress"], 40)

	def test_due_in_30_days_chip_equals_the_list_it_opens(self):
		"""The count had no lower bound, so goals already overdue were "due"."""
		overdue = self.goal(self.worker, self.q2, 10)
		frappe.db.set_value("Individual Goal", overdue, "end_date", add_days(today(), -5),
		                    update_modified=False)
		soon = self.goal(self.worker, self.q2, 20)
		frappe.db.set_value("Individual Goal", soon, "end_date", add_days(today(), 10),
		                    update_modified=False)

		ctx, rows = self._context_and_list()
		# The list the chip opens: Active, ending between today and today + 30.
		in_the_list = [
			g for g in rows
			if g["status"] == "Active" and g["end_date"]
			and str(today()) <= g["end_date"] <= str(add_days(today(), 30))
		]
		self.assertEqual(ctx["dashboard"]["upcoming_deadlines"], len(in_the_list))
		self.assertEqual(ctx["dashboard"]["upcoming_deadlines"], 1)

	def test_a_goal_with_no_cycle_stays_on_its_owners_screen(self):
		"""Filtering to "this cycle" must not take away a goal that names none.

		PP Jewellers has one such goal today. It belongs to no quarter, so no
		quarter of it has ended - it is still live work, and hiding it would
		make the screen wrong in the other direction.
		"""
		self.goal(self.worker, self.q1, 100, status="Active")     # last quarter: gone
		self.goal(self.worker, self.q2, 40, status="Active")      # this quarter
		undated = self.goal(self.worker, self.q2, 60, status="Active")
		frappe.db.set_value("Individual Goal", undated, "appraisal_cycle", None,
		                    update_modified=False)

		ctx, rows = self._context_and_list()
		self.assertIn(undated, [g["name"] for g in rows])
		self.assertEqual(len(rows), 2)
		self.assertEqual(ctx["dashboard"]["total"], len(rows))
		self.assertEqual(ctx["dashboard"]["avg_progress"], 50)   # 40 and 60, not 100

	def test_the_banner_names_the_cycle_the_chips_count(self):
		"""The banner was site-wide; the chips were per company."""
		# A newer cycle in ANOTHER company. The site-wide banner picked this one
		# while the chips counted the employee's own company's cycle, so the
		# screen named one quarter and counted another.
		other_cycle = frappe.get_doc({
			"doctype": "Appraisal Cycle", "cycle_name": "N035 Other Newer",
			"company": self.other_company,
			"start_date": "2999-01-01", "end_date": "2999-03-31",
			"status": "In Progress",
		})
		other_cycle.insert(ignore_permissions=True)

		self.goal(self.worker, self.q2, 40)
		ctx, _rows = self._context_and_list()
		self.assertIsNotNone(ctx["cycle"])
		self.assertEqual(ctx["cycle"]["name"], goals_api.current_cycle_name(self.company))
		self.assertEqual(ctx["cycle"]["name"], ctx["dashboard"]["cycle"])
		self.assertNotEqual(ctx["cycle"]["name"], other_cycle.name)


class TestOneManagerTwoScreensOneNumber(NumbersCase):
	"""get_team_goals and get_team_scorecard are both open to the same manager."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		link_user_to_employee(cls.boss, ensure_user(BOSS_USER, roles=("Employee",)))
		frappe.db.commit()

	def setUp(self):
		super().setUp()
		self.q2 = self.cycle(2, "In Progress")
		frappe.set_user("Administrator")

	def _both(self):
		frappe.set_user(BOSS_USER)
		try:
			team_goals = goals_api.get_team_goals()
			scorecard = hr_api.get_team_scorecard()
		finally:
			frappe.set_user("Administrator")
		row = [r for r in team_goals if r["employee_id"] == self.worker][0]
		member = [m for m in scorecard["members"] if m["name"] == self.worker][0]
		return row, member

	def test_a_finished_goal_is_not_0_on_one_screen_and_100_on_the_other(self):
		"""The team list averaged Active goals only; the scorecard averaged all of them."""
		self.goal(self.worker, self.q2, 100, status="Completed")
		self.goal(self.worker, self.q2, 40, status="Active")

		row, member = self._both()
		self.assertEqual(row["avg_progress"], member["goals_avg"])
		self.assertEqual(row["total_goals"], member["goals_total"])
		self.assertEqual(row["avg_progress"], 70)

	def test_a_cancelled_goal_is_in_neither_the_count_nor_the_average(self):
		"""The scorecard counted a cancelled goal in "total" but left it out of "avg"."""
		self.goal(self.worker, self.q2, 0, status="Cancelled")
		self.goal(self.worker, self.q2, 60, status="Active")

		row, member = self._both()
		self.assertEqual(member["goals_total"], 1)
		self.assertEqual(member["goals_avg"], 60)
		self.assertEqual(row["total_goals"], member["goals_total"])
		self.assertEqual(row["avg_progress"], member["goals_avg"])


# ══════════════════════════════════════════════════════════════════════════
# Leave: the card must add up, and a real negative must not be dressed as 0
# ══════════════════════════════════════════════════════════════════════════

LEAVE_TYPE_EXPIRY = "Alvoraa Match Expiry 035"
LEAVE_TYPE_NEG = "Alvoraa Match Negative 035"
LEAVE_USER = "match.leave035@example.com"
NEG_BOSS_USER = "match.negboss035@example.com"   # its own user: sharing BOSS_USER
                                                # re-pointed that login at this
                                                # class's manager instead


class TestTheLeaveCardAddsUp(FrappeTestCase):
	"""total = taken + expired + left. Nothing on PP Jewellers expires today; a
	tenant that carries leave forward will, and then the card must still be
	checkable by the person reading it."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		ensure_leave_type(LEAVE_TYPE_EXPIRY)
		cls.worker = ensure_employee_with_leave("Match035", LEAVE_TYPE_EXPIRY, days=8,
		                                        last_name="Expiry")
		link_user_to_employee(cls.worker, ensure_user(LEAVE_USER, roles=("Employee",)))
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _expire_by_hand(self, days):
		"""An allocation expired by hand, the way Frappe HR's own expiry writes it."""
		alloc = frappe.get_all("Leave Allocation",
		                       filters={"employee": self.worker, "leave_type": LEAVE_TYPE_EXPIRY,
		                                "docstatus": 1},
		                       fields=["name", "from_date", "to_date"], limit=1)[0]
		doc = frappe.get_doc({
			"doctype": "Leave Ledger Entry", "employee": self.worker,
			"leave_type": LEAVE_TYPE_EXPIRY, "transaction_type": "Leave Allocation",
			"transaction_name": alloc.name, "leaves": -days, "is_expired": 1,
			"is_carry_forward": 0,
			# to_date must be strictly INSIDE the allocation period:
			# get_manually_expired_leaves reads `to_date < end_date`.
			"from_date": alloc.from_date, "to_date": add_days(alloc.to_date, -1),
			"company": frappe.db.get_value("Employee", self.worker, "company"),
		})
		doc.flags.ignore_links = True
		doc.flags.ignore_permissions = True
		doc.submit()

	def test_total_equals_taken_plus_expired_plus_left(self):
		self._expire_by_hand(2)
		frappe.set_user(LEAVE_USER)
		row = [b for b in hr_api.get_leave_summary()["balances"]
		       if b["leave_type"] == LEAVE_TYPE_EXPIRY][0]
		self.assertEqual(row["expired"], 2)
		self.assertEqual(row["taken"] + row["expired"] + row["balance"], row["total"])

	def test_home_reports_the_same_expired_days(self):
		self._expire_by_hand(2)
		frappe.set_user(LEAVE_USER)
		row = [b for b in hr_api.get_employee_dashboard()["leave_balances"]
		       if b["leave_type"] == LEAVE_TYPE_EXPIRY][0]
		self.assertEqual(row["taken"] + row["expired"] + row["balance"], row["total"])

	def test_the_page_shows_expired_days_on_the_ring(self):
		"""A figure the server sends and the page drops is still a card that does
		not add up."""
		import os

		import alvoraa_portal

		path = os.path.join(os.path.dirname(alvoraa_portal.__file__), "www", "hrms-employee.html")
		with open(path, encoding="utf-8") as f:
			page = f.read()
		self.assertIn("b.expired", page)
		# The figure must be rendered next to "N / M used" on the ring itself,
		# not merely present somewhere in a 20,000-line page.
		at = page.index("' used'")
		self.assertIn("b.expired", page[at:at + 400])


class TestANegativeBalanceIsShownAsNegative(FrappeTestCase):
	"""max(balance, 0) told an employee two days in debt that they had none
	left. The leave gate reads the ledger and would have said otherwise."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		ensure_leave_type(LEAVE_TYPE_NEG, allow_negative=1)
		cls.worker = ensure_employee_with_leave("Match035", LEAVE_TYPE_NEG, days=2,
		                                        last_name="Negative")
		cls.boss = ensure_employee("Match035", "NegBoss")
		link_user_to_employee(cls.boss, ensure_user(NEG_BOSS_USER, roles=("Employee",)))
		# The reporting manager, deliberately NOT the named leave approver.
		frappe.db.set_value("Employee", cls.worker,
		                    {"reports_to": cls.boss, "leave_approver": None})
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")
		# The late-coming rule takes 4 days against an allocation of 2.
		doc = frappe.get_doc({
			"doctype": "Leave Ledger Entry", "employee": self.worker,
			"leave_type": LEAVE_TYPE_NEG, "transaction_type": "Attendance Deduction",
			"transaction_name": "ALV-035-MATCH-NEG", "leaves": -4,
			"from_date": today(), "to_date": today(),
			"company": frappe.db.get_value("Employee", self.worker, "company"),
		})
		doc.flags.ignore_links = True
		doc.flags.ignore_permissions = True
		doc.submit()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _row(self, rows):
		return [b for b in rows if b["leave_type"] == LEAVE_TYPE_NEG][0]

	def test_the_helper_says_minus_two(self):
		self.assertEqual(self._row(hr_api._ledger_leave_balances(self.worker, today()))["balance"], -2)

	def test_the_ledger_agrees(self):
		from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

		self.assertEqual(
			get_leave_balance_on(self.worker, LEAVE_TYPE_NEG, today(),
			                     consider_all_leaves_in_the_allocation_period=True),
			-2,
		)

	def test_every_screen_says_minus_two_not_zero(self):
		with patch("alvoraa_portal.subscription.has_feature", return_value=True):
			self.assertEqual(self._row(hr_api.get_leave_summary(employee_id=self.worker)["balances"])
			                 ["balance"], -2)
			frappe.set_user(NEG_BOSS_USER)
			self.assertEqual(self._row(hr_api.get_employee_scorecard(self.worker)["leave_balances"])
			                 ["balance"], -2)
			self.assertEqual(self._row(hr_api.get_employee_detail_for_manager(self.worker)
			                           ["leave_balances"])["balance"], -2)
