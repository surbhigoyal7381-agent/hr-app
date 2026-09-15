"""Slice 012 push 1 · the eight indexes exist, and survive Frappe re-syncing the tables.

US-1 (AC-1, AC-2), OPS-52, OPS-70, OPS-71. The survival test is the one that
matters: CI builds its site with `install-app` and never re-syncs Employee, so a
single-column index Frappe silently drops would pass every other check.

These tests change the schema, which commits. They create no records.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import branch_scope, data_review


def setUpModule():
	branch_scope.after_migrate()
	data_review.add_indexes()


def _first_columns(doctype):
	"""{index name: [columns in order]} for the doctype's table."""
	out = {}
	for row in frappe.db.sql(f"SHOW INDEX FROM `tab{doctype}`", as_dict=True):
		out.setdefault(row.Key_name, []).append((row.Seq_in_index, row.Column_name))
	return {k: [c for _s, c in sorted(v)] for k, v in out.items()}


class TestTheEightIndexes(FrappeTestCase):
	def assertAllEight(self):
		for doctype, field in data_review.SINGLE_COLUMN_INDEXES:
			self.assertIsNotNone(
				frappe.db.get_column_index(f"tab{doctype}", field),
				f"{doctype}.{field} has no one-column index",
			)
		for doctype, fields in data_review.TWO_COLUMN_INDEXES:
			self.assertIn(list(fields), list(_first_columns(doctype).values()),
			              f"{doctype} has no index on {fields}")

	def assertMarked(self):
		for doctype, field in data_review.SINGLE_COLUMN_INDEXES:
			self.assertEqual(
				frappe.db.get_value("Property Setter",
				                    {"doc_type": doctype, "field_name": field, "property": "search_index"},
				                    "value"),
				"1", f"{doctype}.{field} is not marked indexed")

	def test_install_creates_all_eight_indexes(self):
		"""AC-1."""
		self.assertAllEight()
		self.assertMarked()

	def test_running_again_adds_and_changes_nothing(self):
		"""AC-2."""
		before = {dt: _first_columns(dt) for dt in ("Employee", "Employee Checkin", "Attendance")}
		setters = frappe.db.count("Property Setter", {"property": "search_index"})
		data_review.after_install()
		after = {dt: _first_columns(dt) for dt in ("Employee", "Employee Checkin", "Attendance")}
		self.assertEqual(before, after)
		self.assertEqual(frappe.db.count("Property Setter", {"property": "search_index"}), setters)

	def test_the_indexes_survive_frappe_resyncing_the_tables(self):
		"""OPS-71. A Custom Field save or an ERPNext update re-syncs Employee; an
		unmarked one-column index is dropped then. This is the tripwire for a
		future Frappe changing those rules."""
		for dt in ("Employee", "Employee Checkin", "Attendance"):
			frappe.clear_cache(doctype=dt)
			frappe.db.updatedb(dt)
		self.assertAllEight()
		self.assertMarked()

	def test_the_hook_marks_fields_during_migrate_too(self):
		"""OPS-71: `add_index` does not mark a field while in_migrate is set; ours must."""
		saved = frappe.flags.in_migrate
		frappe.flags.in_migrate = True
		try:
			data_review.add_indexes()
		finally:
			frappe.flags.in_migrate = saved
		self.assertAllEight()
		self.assertMarked()

	def test_the_hook_lists_run_after_the_branch_column_installer(self):
		"""OPS-72: two indexes need alvoraa_branch, which branch_scope creates."""
		from alvoraa_portal import hooks

		for name, ours in (("after_migrate", "alvoraa_portal.data_review.after_migrate"),
		                   ("after_install", "alvoraa_portal.data_review.after_install")):
			entries = getattr(hooks, name)
			self.assertIn(ours, entries)
			self.assertGreater(entries.index(ours),
			                   entries.index("alvoraa_portal.branch_scope.after_migrate"), name)
