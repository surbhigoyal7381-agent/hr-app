"""068: Approve and Decline are offered only to somebody who may decide TODAY.

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
		"""Raised today for somebody whose manager can decide (Kamal holds HR
		Manager), so HR waits two working days."""
		doc = self._request(self.kamal_both)
		self.as_user(self.priya_user)
		row = self._row(doc.name)
		self.assertIs(row["can_decide"], False)
		self.assertIn("still with", row["not_yet"])
		with may_review_granted(), self.assertRaises(frappe.PermissionError) as caught:
			ac.decide(doc.name, 1)
		# One sentence, two places: the row says exactly what pressing would.
		self.assertEqual(row["not_yet"], str(caught.exception))

	def test_hr_after_the_wait_gets_the_buttons(self):
		doc = self._request(self.kamal_both, raised_on=f"{add_days(nowdate(), -12)} 09:00:00")
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

	def test_a_manager_who_cannot_decide_is_not_waited_for(self):
		"""Surbhi, 23 Oct 2026. The DTC case: Sandeep holds only Employee, so
		he can never decide, and HR decides Rahul's request today."""
		self.assertFalse(frappe.has_permission(ac.REQUEST, "submit", user=self.sandeep_user))
		doc = self._request(self.rahul)
		self.as_user(self.priya_user)
		row = self._row(doc.name)
		self.assertIs(row["can_decide"], True)
		self.assertIsNone(row["not_yet"])

	def _inbox(self):
		"""The Inbox part as the bell and the Inbox see it: (count, row names)."""
		from alvoraa_portal import inbox_api

		with may_review_granted():
			part, _hr = inbox_api._part_attendance_fixes(
				inbox_api._Who(frappe.session.user))
			rows = part.rows(None)
			return part.count(), [r["name"] for r in rows], rows

	def test_the_bell_counts_only_what_can_be_pressed(self):
		"""Surbhi, 23 Oct 2026: the count matches the buttons. A correction
		still with a manager who can decide is listed on the Attendance page
		with its sentence, but not counted or listed in the Inbox."""
		waiting = self._request(self.kamal_both)
		ready = self._request(self.covered_only[0])
		self.as_user(self.priya_user)
		count, names, rows = self._inbox()
		self.assertNotIn(waiting.name, names)
		self.assertIn(ready.name, names)
		self.assertEqual(count, len(names), "the count and the list disagree")
		self.assertTrue(all(r["can_decide"] for r in rows))
		# Only the flag was added; nothing about the person leaked.
		for r in rows:
			self.assertNotIn("employee", r)
			self.assertNotIn("owner", r)
		# The Attendance page still shows it, saying whose it is.
		self.assertIn("still with", self._row(waiting.name)["not_yet"])

	def test_once_it_is_hrs_it_is_counted(self):
		doc = self._request(self.kamal_both,
		                    raised_on=f"{add_days(nowdate(), -12)} 09:00:00")
		self.as_user(self.priya_user)
		count, names, _rows = self._inbox()
		self.assertIn(doc.name, names)
		self.assertEqual(count, len(names))


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

	def test_the_raiser_is_not_counted_it(self):
		doc = self._raised_by(self.kamal_both, self.kamal_user)
		self.as_user(self.kamal_user)
		count, names, _rows = TestTheRowSaysWhatDecideWillSay._inbox(self)
		self.assertNotIn(doc.name, names)
		self.assertEqual(count, len(names))

	def test_somebody_else_may_decide_what_the_raiser_raised(self):
		"""The rule binds the raiser only. Priya is HR and did not raise it."""
		doc = self._raised_by(self.covered_only[0], self.kamal_user)
		self.as_user(self.priya_user)
		self.assertIs(self._row(doc.name)["can_decide"], True)


class TestAManagersOwnRaiseIsNotWaitedOn(_Corrections):
	"""Fix A. Surbhi, 22 Oct 2026, amending 045 AC-81: when the employee's
	own manager raised the correction, HR decides at once."""

	_row = TestTheRowSaysWhatDecideWillSay._row
	_raised_by = TestWhoeverRaisedItDoesNotDecideIt._raised_by

	def test_hr_may_decide_a_managers_raise_straight_away(self):
		"""Kamal can decide, but he raised it for Kamal-both himself, and the
		raiser never decides - so HR does, today."""
		doc = self._raised_by(self.kamal_both, self.kamal_user)
		self.as_user(self.priya_user)
		row = self._row(doc.name)
		self.assertIs(row["can_decide"], True)
		self.assertIsNone(row["not_yet"])
		with may_review_granted():
			ac.decide(doc.name, 1)
		frappe.set_user("Administrator")
		stored = frappe.db.get_value(ac.REQUEST, doc.name,
		                             ["docstatus", "alvoraa_decided_as"], as_dict=True)
		self.assertEqual(1, stored.docstatus)
		self.assertEqual("HR", stored.alvoraa_decided_as)

	def test_a_raise_by_somebody_else_still_waits_for_a_manager_who_can_decide(self):
		"""Kamal can decide; the request was raised by somebody else (here the
		fixture's Administrator), so HR still waits for him."""
		doc = self._request(self.kamal_both)
		self.as_user(self.priya_user)
		row = self._row(doc.name)
		self.assertIs(row["can_decide"], False)
		self.assertIn("still with", row["not_yet"])
