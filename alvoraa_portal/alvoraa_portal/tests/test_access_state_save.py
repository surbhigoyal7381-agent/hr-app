"""Writing the access-state record must survive a stale cached copy.

This is the fault that broke 43 tests across four suites at once, and it would
have broken real work the same way.

`frappe.get_single` returns a CACHED document. `release_permissions` reads the
state, spends a while deleting permission rows, then saves - and by then
anything else that touched the record has moved the row on. Frappe compares the
timestamps, sees the copy in hand is older, and refuses:

    TimestampMismatchError: ... has been modified after you have opened it

In a test run it looked like noise. In use it is worse than that: it fires
exactly when two permission changes land close together, which is what happens
when an administrator bulk-updates users or a scheduled sync overlaps an admin
action. The write is lost and the operation reports failure, on the record that
says which doctypes we restricted.

The guard itself is right and stays. What changed is that we now save the
current copy, so it watches for a real concurrent write rather than for our own
cache.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import module_access as ma


class TestAccessStateSurvivesAStaleCopy(FrappeTestCase):
	def setUp(self):
		self._before = ma._recorded_restrictions()
		self._snapshot = ma._load("permission_snapshot")

	def tearDown(self):
		# BOTH halves. Restoring only the restrictions left a snapshot behind
		# that failed test_state_is_cleared_after_release in another suite -
		# which is the same class of bug this file exists to fix, made by the
		# test for it.
		ma._save(restricted=self._before, snapshot=self._snapshot)
		frappe.db.commit()

	def test_saving_after_the_row_moved_on_does_not_raise(self):
		"""The exact sequence from the failure: read, row changes, write."""
		ma._save(restricted={"Leave Type"})
		frappe.db.commit()

		# Hold a cached copy, the way release_permissions does across its work.
		stale = frappe.get_single(ma.STATE_DOCTYPE)
		self.assertIsNotNone(stale.modified)

		# Something else writes the row - another sync, a hook, the next test.
		frappe.db.set_single_value(ma.STATE_DOCTYPE, "last_synced", frappe.utils.now())
		frappe.db.commit()

		# Before the fix this raised TimestampMismatchError.
		ma._save(restricted={"Leave Type", "Shift Type"})
		frappe.db.commit()
		self.assertEqual(ma._recorded_restrictions(), {"Leave Type", "Shift Type"})

	def test_two_saves_in_a_row_both_land(self):
		"""The commonest shape of the bug: one request saving twice."""
		ma._save(restricted={"Leave Type"})
		ma._save(restricted={"Leave Type", "Holiday List"})
		frappe.db.commit()
		self.assertEqual(ma._recorded_restrictions(), {"Leave Type", "Holiday List"})

	def test_the_snapshot_is_not_lost_when_only_restrictions_are_written(self):
		"""Reloading must not quietly drop the half of the record we did not set."""
		ma._save(restricted={"Leave Type"}, snapshot={"Leave Type": [{"role": "HR Manager"}]})
		frappe.db.commit()
		ma._save(restricted={"Leave Type", "Shift Type"})
		frappe.db.commit()
		self.assertIn("Leave Type", ma._load("permission_snapshot"))
