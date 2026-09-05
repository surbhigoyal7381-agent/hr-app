"""Approving somebody's work is the manager's job, not a permission's.

Two flaws of the same shape as the leave-approval bug, found by auditing every
action endpoint in the portal after that one was reported:

    approve_goal_update   the UI drew buttons for ANY manager, while the backend
                          required the goal owner's OWN manager
    approve_evidence      anyone who could WRITE the goal could sign off its
                          evidence - a colleague could validate work they had no
                          part in supervising, and the audit trail would name
                          them as though they had
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_goals.controllers import evidence
from alvoraa_portal import goals_api


class TestEvidenceValidationIsTheManagersJob(FrappeTestCase):
	def test_write_permission_alone_is_no_longer_enough(self):
		"""If this string comes back, so has the bug."""
		import inspect

		src = inspect.getsource(evidence.approve_evidence)
		self.assertNotIn('has_permission("Individual Goal", "write", goal_name)', src)
		self.assertIn("_assert_can_validate", src)

	def test_reject_uses_the_same_rule_as_approve(self):
		"""Half a gate is no gate: rejecting evidence is as consequential as
		approving it."""
		import inspect

		self.assertIn("_assert_can_validate",
		              inspect.getsource(evidence.reject_evidence))

	def test_the_rule_is_manager_or_hr(self):
		import inspect

		src = inspect.getsource(evidence.can_validate_evidence)
		self.assertIn("reports_to", src)
		self.assertIn("HR Manager", src)

	def test_write_permission_is_still_required_on_top(self):
		"""Being the manager does not help if the goal is out of reach for
		another reason - a plan that does not include Goals, for instance."""
		import inspect

		self.assertIn("has_permission", inspect.getsource(evidence.can_validate_evidence))

	def test_a_missing_manager_says_so_plainly(self):
		"""The likely real case. A bare 'Not permitted' sends HR looking in the
		wrong place."""
		import inspect

		self.assertIn("No manager is set", inspect.getsource(evidence._assert_can_validate))


class TestGoalUpdateButtonsMatchTheBackend(FrappeTestCase):
	def test_the_log_reports_whether_this_user_may_action(self):
		import inspect

		self.assertIn("can_action", inspect.getsource(goals_api.get_goal_update_log))

	def test_the_flag_uses_the_same_rule_the_action_enforces(self):
		"""One rule, two callers. The previous version had the UI ask 'am I a
		manager' while the backend asked 'am I THIS person's manager'."""
		import inspect

		log = inspect.getsource(goals_api.get_goal_update_log)
		act = inspect.getsource(goals_api.approve_goal_update)
		for src in (log, act):
			self.assertIn("reports_to", src)
			self.assertIn("_is_hr()", src)

	def test_seeing_the_log_is_not_the_same_as_actioning_it(self):
		"""An employee reads their own updates and must not be able to approve
		them, so the read check and the action check cannot be the same test."""
		import inspect

		src = inspect.getsource(goals_api.get_goal_update_log)
		self.assertIn("goal.employee == emp_id", src)   # may READ
		self.assertIn("can_action = bool(", src)        # may ACT - narrower
