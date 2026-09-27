"""Goal percentages are about one review cycle (slice 035, commit 3).

The goal averages took every goal a person ever had. At PP Jewellers that blended
a finished Q1 (goals averaging 97%) with the live Q2 (71%): 210 of 213 people
showed a figure 13 points high on average, up to 50 - on the comparison chart
managers look at while they rate. The appraisal's own goal score was always per
cycle, by weight; these tests keep the screens in step with it.

Decisions (22 Sep 2026): the current cycle is In Progress, else the newest not
Completed, per company (Q-G1); weighted when goals carry weights, plain when not
(Q-G2).

Nothing here is committed. Every record is made inside the test's transaction and
rolled back, including pushing the company's existing cycles into the past so
"current" means the cycles made here.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_goals.tests.utils import ensure_company
from alvoraa_portal import goals_api, hr_api, performance_api
from alvoraa_portal.tests.leave_fixtures import ensure_employee, ensure_user, link_user_to_employee

YEAR = 2951   # far from any other test's cycles and appraisals
BOSS_USER = "goal.boss035@example.com"
WORKER_USER = "goal.worker035@example.com"


class GoalCycleCase(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.company = ensure_company()
		cls.boss = ensure_employee("Goal035", "Boss")
		cls.worker = ensure_employee("Goal035", "Worker")
		link_user_to_employee(cls.boss, ensure_user(BOSS_USER, roles=("Employee",)))
		link_user_to_employee(cls.worker, ensure_user(WORKER_USER, roles=("Employee",)))
		frappe.db.set_value("Employee", cls.worker, {"reports_to": cls.boss, "company": cls.company})
		frappe.db.set_value("Employee", cls.boss, "company", cls.company)
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")
		self._plan = patch("alvoraa_portal.subscription.has_feature", return_value=True)
		self._plan.start()
		# Other tests' cycles for this company become old and Completed - inside
		# this transaction only, so the rollback puts them back.
		frappe.db.set_value("Appraisal Cycle", {"company": self.company},
		                    {"status": "Completed", "start_date": "1901-01-01", "end_date": "1901-03-31"},
		                    update_modified=False)
		for goal in frappe.get_all("Individual Goal", {"employee": ["in", [self.boss, self.worker]]},
		                           pluck="name"):
			frappe.db.set_value("Individual Goal", goal, "docstatus", 2, update_modified=False)

	def tearDown(self):
		self._plan.stop()
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def cycle(self, quarter, status):
		start = f"{YEAR}-{3 * quarter - 2:02d}-01"
		end = {1: f"{YEAR}-03-31", 2: f"{YEAR}-06-30", 3: f"{YEAR}-09-30", 4: f"{YEAR}-12-31"}[quarter]
		doc = frappe.get_doc({
			"doctype": "Appraisal Cycle", "cycle_name": f"G035 Q{quarter} {YEAR}",
			"company": self.company, "start_date": start, "end_date": end,
			"status": "In Progress",
		})
		doc.insert(ignore_permissions=True)
		if status != "In Progress":
			frappe.db.set_value("Appraisal Cycle", doc.name, "status", status, update_modified=False)
		return doc.name

	def goal(self, employee, cycle, pct, weightage=0, status="Active"):
		start, end = frappe.db.get_value("Appraisal Cycle", cycle, ["start_date", "end_date"])
		doc = frappe.get_doc({
			"doctype": "Individual Goal", "employee": employee,
			"goal_name": f"G035 {cycle} {pct}% {frappe.generate_hash(length=5)}",
			"appraisal_cycle": cycle, "target_value": 100, "progress_mode": "Cumulative",
			"start_date": start, "end_date": end, "weightage": weightage,
		})
		doc.insert(ignore_permissions=True)
		frappe.db.set_value("Individual Goal", doc.name, {"progress_pct": pct, "status": status},
		                    update_modified=False)
		return doc.name


class TestWhichCycleIsCurrent(GoalCycleCase):

	def test_in_progress_wins(self):
		self.cycle(1, "Completed")
		q2 = self.cycle(2, "In Progress")
		self.cycle(3, "Not Started")
		self.assertEqual(goals_api.current_cycle_name(self.company), q2)

	def test_else_the_newest_not_completed(self):
		self.cycle(1, "Completed")
		q3 = self.cycle(3, "Not Started")
		self.assertEqual(goals_api.current_cycle_name(self.company), q3)

	def test_between_cycles_the_newest_rather_than_all_of_them(self):
		self.cycle(1, "Completed")
		q2 = self.cycle(2, "Completed")
		self.assertEqual(goals_api.current_cycle_name(self.company), q2)

	def test_a_company_with_no_cycle_has_none(self):
		self.assertIsNone(goals_api.current_cycle_name("G035 No Such Company"))
		self.assertIsNone(goals_api.current_cycle_name(None))


class TestGoalAveragesAreOneCycle(GoalCycleCase):

	def setUp(self):
		super().setUp()
		self.q1 = self.cycle(1, "Completed")
		self.q2 = self.cycle(2, "In Progress")

	def test_employee_avg_progress_is_this_cycle(self):
		self.goal(self.worker, self.q1, 100, status="Completed")
		self.goal(self.worker, self.q2, 40)
		stats = goals_api._dashboard_stats(self.worker)
		self.assertEqual(stats["avg_progress"], 40.0)
		self.assertEqual(stats["total"], 1)

	def test_team_comparison_chart_is_this_cycle(self):
		self.goal(self.worker, self.q1, 100, status="Completed")
		self.goal(self.worker, self.q2, 40)
		frappe.set_user(BOSS_USER)
		member = next(m for m in hr_api.get_team_scorecard()["members"] if m["name"] == self.worker)
		self.assertEqual(member["goals_avg"], 40)
		self.assertEqual(member["goals_total"], 1)

	def test_team_goals_drop_a_q1_goal_still_marked_active(self):
		self.goal(self.worker, self.q1, 90)          # left Active after Q1 closed
		self.goal(self.worker, self.q2, 40)
		frappe.set_user(BOSS_USER)
		row = next(r for r in goals_api.get_team_goals() if r["employee_id"] == self.worker)
		self.assertEqual(row["avg_progress"], 40.0)
		self.assertEqual(row["total_goals"], 1)

	def test_weighted_when_goals_carry_weights(self):
		self.goal(self.worker, self.q2, 100, weightage=75)
		self.goal(self.worker, self.q2, 0, weightage=25)
		self.assertEqual(goals_api._dashboard_stats(self.worker)["avg_progress"], 75.0)

	def test_plain_average_when_no_goal_carries_a_weight(self):
		self.goal(self.worker, self.q2, 100)
		self.goal(self.worker, self.q2, 0)
		self.assertEqual(goals_api._dashboard_stats(self.worker)["avg_progress"], 50.0)

	def test_cancelled_goals_do_not_pull_the_average_down(self):
		self.goal(self.worker, self.q2, 80)
		self.goal(self.worker, self.q2, 0, status="Cancelled")
		self.assertEqual(goals_api._dashboard_stats(self.worker)["avg_progress"], 80.0)

	def test_scorecard_lists_this_cycles_goals_first(self):
		this_cycle = self.goal(self.worker, self.q2, 40)
		self.goal(self.worker, self.q1, 100, status="Completed")   # created later
		frappe.set_user(BOSS_USER)
		goals = hr_api.get_employee_scorecard(self.worker)["goals"]
		self.assertEqual(goals[0]["name"], this_cycle)
		self.assertNotIn("appraisal_cycle", goals[0], "no new field in the payload")


class TestTeamReviewsWithoutACycle(GoalCycleCase):
	"""With no cycle chosen, the newest review - not whichever the database returned last."""

	def test_newest_review_wins(self):
		q1 = self.cycle(1, "In Progress")
		q2 = self.cycle(2, "In Progress")
		old = frappe.get_doc({"doctype": "Appraisal", "employee": self.worker,
		                      "appraisal_cycle": q1, "company": self.company}).insert(ignore_permissions=True)
		new = frappe.get_doc({"doctype": "Appraisal", "employee": self.worker,
		                      "appraisal_cycle": q2, "company": self.company}).insert(ignore_permissions=True)
		# Q1's review made first, as in life. Frappe's default order is newest
		# created first, so an unordered read hands the OLD review back last,
		# and "last one wins" picked it.
		frappe.db.set_value("Appraisal", old.name, "creation", "2000-01-01 00:00:00", update_modified=False)
		frappe.db.set_value("Appraisal Cycle", {"name": ["in", [q1, q2]]}, "status", "Completed",
		                    update_modified=False)
		frappe.set_user(BOSS_USER)
		row = next(t for t in performance_api.get_team_reviews()["team"] if t["employee"] == self.worker)
		self.assertEqual(row["appraisal"], new.name)
