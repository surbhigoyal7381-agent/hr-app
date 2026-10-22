"""066: Approve and Decline are offered only to somebody who may decide TODAY.

DTC, 22 Oct 2026. An HR user pressed Approve on an attendance correction a
manager had raised for their own report the day before. `decide` refused it
with a 403 - "This is still with <manager> until <date>" - because HR waits two
working days for the employee's own manager (045 AC-81). The refusal was right.
Offering the button was not.

So every row that offers the buttons carries `can_decide` and `not_yet`, worked
out by `not_yours_yet` - the same function `decide` asks. The screen draws
whatever the server says and holds no copy of the rule.

Personas from 045: Sandeep manages Rahul and holds only Employee; Priya is HR
and nobody's manager; Kamal is HR Manager and manages Kamal-both.
"""

import frappe
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal.tests.test_decided_as_045 import _Corrections, may_review_granted


class TestTheRowSaysWhatDecideWillSay(_Corrections):
	def _row(self, name):
		"""The row the Attendance page draws, as the caller sees it."""
		with may_review_granted():
			rows = [r for r in ac.to_review(limit=500) if r["name"] == name]
		self.assertEqual(len(rows), 1, "the request is not in this caller's queue")
		return rows[0]

	def test_hr_inside_the_wait_gets_no_buttons_and_the_same_sentence(self):
		"""The DTC case: raised today for somebody whose manager has a login."""
		doc = self._request(self.rahul)
		self.as_user(self.priya_user)
		row = self._row(doc.name)
		self.assertIs(row["can_decide"], False)
		self.assertIn("still with", row["not_yet"])
		with may_review_granted(), self.assertRaises(frappe.PermissionError) as caught:
			ac.decide(doc.name, 1)
		# One sentence, two places: the row says exactly what pressing would.
		self.assertEqual(row["not_yet"], str(caught.exception))

	def test_hr_after_the_wait_gets_the_buttons(self):
		doc = self._request(self.rahul, raised_on=f"{add_days(nowdate(), -12)} 09:00:00")
		self.as_user(self.priya_user)
		row = self._row(doc.name)
		self.assertIs(row["can_decide"], True)
		self.assertIsNone(row["not_yet"])

	def test_the_manager_gets_the_buttons_at_once(self):
		"""Kamal decides as Manager, so the HR wait is not his."""
		doc = self._request(self.kamal_both)
		self.as_user(self.kamal_user)
		row = self._row(doc.name)
		self.assertIs(row["can_decide"], True)

	def test_nobody_to_wait_for_means_hr_gets_the_buttons(self):
		doc = self._request(self.covered_only[0])
		self.as_user(self.priya_user)
		self.assertIs(self._row(doc.name)["can_decide"], True)

	def test_somebody_without_the_right_to_decide_gets_no_queue_at_all(self):
		"""Sandeep holds only Employee. He never sees a row to press."""
		self._request(self.rahul)
		self.as_user(self.sandeep_user)
		with self.assertRaises(frappe.PermissionError):
			ac.to_review()

	def test_the_inbox_rows_carry_the_same_flag(self):
		from alvoraa_portal import inbox_api

		doc = self._request(self.rahul)
		self.as_user(self.priya_user)
		with may_review_granted():
			part, _hr = inbox_api._part_attendance_fixes(inbox_api._Who(self.priya_user))
			rows = [r for r in part.rows(None) if r["name"] == doc.name]
		self.assertEqual(len(rows), 1)
		self.assertIs(rows[0]["can_decide"], False)
		self.assertIn("still with", rows[0]["not_yet"])
		# Only the two new keys were added; nothing about the person leaked.
		self.assertNotIn("employee", rows[0])
		self.assertNotIn("creation", rows[0])


class TestWhoeverRaisedItDoesNotDecideIt(_Corrections):
	"""Kamal holds HR Manager and manages Kamal-both. Before this he could
	raise a correction for her and approve it himself."""

	_row = TestTheRowSaysWhatDecideWillSay._row

	def _raised_by(self, employee, user, **kw):
		doc = self._request(employee, **kw)
		frappe.db.set_value(ac.REQUEST, doc.name, "owner", user, update_modified=False)
		frappe.db.commit()
		return frappe.get_doc(ac.REQUEST, doc.name)

	def test_the_raiser_gets_no_buttons_and_is_refused(self):
		doc = self._raised_by(self.kamal_both, self.kamal_user)
		self.as_user(self.kamal_user)
		row = self._row(doc.name)
		self.assertIs(row["can_decide"], False)
		self.assertEqual(row["not_yet"], "You raised this request, so someone else decides it.")
		self.assertNotIn("owner", row, "the raiser's login is not sent to the screen")
		with may_review_granted(), self.assertRaises(frappe.PermissionError) as caught:
			ac.decide(doc.name, 1)
		self.assertEqual(row["not_yet"], str(caught.exception))
		frappe.set_user("Administrator")
		self.assertEqual(0, frappe.db.get_value(ac.REQUEST, doc.name, "docstatus"),
		                 "a refused decision still went through")

	def test_somebody_else_may_decide_what_the_raiser_raised(self):
		"""The rule binds the raiser only. Priya is HR and did not raise it."""
		doc = self._raised_by(self.covered_only[0], self.kamal_user)
		self.as_user(self.priya_user)
		self.assertIs(self._row(doc.name)["can_decide"], True)
