"""ALV-434: an approval that cannot happen says why, in words the approver can act on.

At Grace (18 Oct - 22 Nov 2026) an active Workflow on Attendance Request refused
every portal approval ("Workflow State transition not allowed from Draft to
Approved"), and HR saw nothing useful. These tests pin the two sentences now
given instead, and that a request is left untouched when either is said.
"""

from unittest.mock import patch

import frappe
from frappe.model.document import Document

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal.tests.test_attendance_correction import CorrectionCase

WF = "ALV-434 Test Workflow"


class AnApprovalThatCannotHappenSaysWhy(CorrectionCase):

	def _request(self, first):
		# A name of its own per run: a re-run on the same site must not meet the
		# last run's user, which is already linked to an employee.
		p, email = self.person(first + frappe.generate_hash(length=5))
		self.day(p, self.d(3), 0.0, status="Absent")
		frappe.set_user(email)
		req = ac.raise_correction(self.d(3), reason="Marked Absent by Mistake",
		                          explanation="Forgot to punch.")
		frappe.set_user("Administrator")
		return p, req["name"]

	def test_an_organisation_workflow_is_named_and_nothing_changes(self):
		"""Pretended, not created: inserting a real Workflow adds a column to the
		table, and MariaDB commits on that, so a real one would outlive the test
		(it did, on 22 Nov 2026). The check reads Frappe's own lookup, so that is
		what is stood in for."""
		p, name = self._request("ACWorkflow")
		with patch("frappe.model.workflow.get_workflow_name", return_value=WF):
			with self.assertRaises(frappe.ValidationError) as caught:
				ac.decide(name, approve=1, note="")
		said = str(caught.exception)
		self.assertIn("own approval steps", said)
		self.assertIn(WF, said)
		self.assertIn("Nothing was changed", said)
		self.assertEqual(frappe.db.get_value(ac.REQUEST, name, "docstatus"), 0)

	def test_without_a_workflow_approval_still_works(self):
		p, name = self._request("ACNoWorkflow")
		ac.decide(name, approve=1, note="Checked.")
		self.assertEqual(frappe.db.get_value(ac.REQUEST, name, "docstatus"), 1)

	def test_a_wordless_permission_refusal_gets_a_sentence(self):
		p, name = self._request("ACWordless")

		def refuse(doc, *a, **k):
			raise frappe.PermissionError

		frappe.clear_messages()
		with patch.object(Document, "submit", refuse):
			with self.assertRaises(frappe.PermissionError) as caught:
				ac.decide(name, approve=1, note="")
		said = str(caught.exception)
		self.assertIn("You are not allowed to approve this request", said)
		self.assertIn("Ask an HR Manager of", said)

	def test_a_refusal_that_already_has_words_keeps_them(self):
		p, name = self._request("ACWorded")

		def refuse(doc, *a, **k):
			frappe.throw("Grace says no on Sundays.", frappe.PermissionError)

		frappe.clear_messages()
		with patch.object(Document, "submit", refuse):
			with self.assertRaises(frappe.PermissionError) as caught:
				ac.decide(name, approve=1, note="")
		self.assertIn("Grace says no on Sundays.", str(caught.exception))
		self.assertNotIn("You are not allowed", str(caught.exception))
