"""ALV-117 finding F1: get_feedback_history leaked aggregates past the row filter.

`hrms.hr.doctype.appraisal.appraisal.get_feedback_history` is whitelisted and
takes an employee id and an appraisal id. Its list of feedback is filtered by
the row condition added for ALV-117, but the six `frappe.db.count` calls and
the `frappe.db.get_value("Appraisal", ...)` underneath it are not - neither
goes through permissions. So an unrelated employee could still read how many
one-star reviews a colleague had, and that colleague's average feedback score.

The fix is one `frappe.has_permission("Appraisal", "read", ...)` gate. It adds
no new rule of its own: `Appraisal` already has both a row filter and a
has_permission hook of its own, registered by `alvoraa_goals.permissions`, and
the plain Employee role holds no permission on Appraisal at all. So the gate
says exactly "you may read this appraisal's feedback summary if you may read
the appraisal", which is what the desk form that calls it already requires.

That is what this module measures: the function now succeeds exactly when
Appraisal read succeeds, and refuses otherwise.

Lives in its own module so the gate and its proof can be reverted together.
"""

import frappe

from hrms.hr.doctype.appraisal.appraisal import get_feedback_history

from .test_feedback_access_047 import PEOPLE, FeedbackFixtures047, _email


class TestFeedbackHistoryGate047(FeedbackFixtures047):
	def test_an_unrelated_employee_cannot_read_the_rating_distribution(self):
		frappe.set_user(_email("unrel"))
		try:
			with self.assertRaises(frappe.PermissionError):
				get_feedback_history(self.emp["subj"], self.appraisal["subj"])
		finally:
			frappe.set_user("Administrator")

	def test_the_subject_cannot_reach_it_either_because_appraisal_is_hrs(self):
		"""Not a regression: the Employee role has never held any permission on
		Appraisal, so the portal reads appraisals through its own endpoints and
		never through this one."""
		frappe.set_user(_email("subj"))
		try:
			with self.assertRaises(frappe.PermissionError):
				get_feedback_history(self.emp["subj"], self.appraisal["subj"])
		finally:
			frappe.set_user("Administrator")

	def test_the_gate_adds_no_rule_of_its_own(self):
		"""For every persona: the call works exactly when Appraisal read works.

		Written this way rather than with a fixed expected list because the
		Appraisal rule belongs to alvoraa_goals, not to this slice. If they
		change it, this test follows them instead of going red for no reason.
		"""
		appraisal = self.appraisal["subj"]
		for key in PEOPLE:
			with self.subTest(person=key):
				user = _email(key)
				allowed = bool(frappe.has_permission("Appraisal", "read", doc=appraisal, user=user))
				frappe.set_user(user)
				try:
					if allowed:
						data = get_feedback_history(self.emp["subj"], appraisal)
						self.assertEqual(len(data.reviews_per_rating), 5)
					else:
						with self.assertRaises(frappe.PermissionError):
							get_feedback_history(self.emp["subj"], appraisal)
				finally:
					frappe.set_user("Administrator")

	def test_the_history_itself_is_still_returned_for_a_permitted_caller(self):
		data = get_feedback_history(self.emp["subj"], self.appraisal["subj"])
		names = {row["name"] for row in data.feedback_history}
		self.assertIn(self.fb["submitted"], names)
		self.assertEqual(len(data.reviews_per_rating), 5)
