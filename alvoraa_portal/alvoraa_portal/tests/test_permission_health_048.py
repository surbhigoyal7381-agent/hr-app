"""ALV-127: prove the permission freeze check actually bites.

A health check that cannot go red is worse than no health check, because it
reads as reassurance. So every test here BREAKS something first and then asks
the check what it thinks, rather than only confirming a clean site looks clean.

TWO TRAPS THIS PROGRAMME HAS ALREADY PAID FOR, AND WHAT IS DONE ABOUT THEM

1. Never hand-insert a lone `Custom DocPerm` to set up a test. One row puts the
   doctype into custom mode with ONLY that row, which strips every other role
   site-wide for the rest of the run. A fixture did this once and nearly took
   HR Manager away everywhere. Everything below goes through
   `frappe.permissions.add_permission`, which copies the standard rows in first
   - the same route the Desk's own Role Permissions Manager takes.

2. Clear the DOCTYPE cache in teardown, not just the user cache. A previous
   teardown removed the row and cleared the wrong cache, so the process still
   believed the row was there. Tests run alphabetically: the two before it
   passed, the five after it failed, and the cause read as leftover site state
   for a day. `_restore` below clears the doctype cache by name.
"""

import unittest
from unittest.mock import patch

import frappe
from frappe.permissions import add_permission, reset_perms
from frappe.tests import IntegrationTestCase

from alvoraa_portal import permission_health as ph

# The doctype the tests break. Attendance Request is the one the live finding
# was about, and it is a watched doctype, so breaking it exercises the real path
# rather than a stand-in.
SUBJECT = "Attendance Request"

# A role that is not in REQUIRED_ROLES, so granting it is a pure "tenant adds a
# role" action and nothing else. Created by the fixture so the test does not
# depend on a role another slice happens to have made.
GRANTED_ROLE = "ALV127 Shift Supervisor"

# Everything that makes a permission row what it is. Used to snapshot the site's
# starting state and put it back byte for byte.
PERM_FIELDS = [
	"role",
	"permlevel",
	"if_owner",
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
	"select",
]


class PermissionFreezeCheck048(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		if not frappe.db.exists("Role", GRANTED_ROLE):
			role = frappe.get_doc({"doctype": "Role", "role_name": GRANTED_ROLE, "desk_access": 1})
			role.flags.ignore_permissions = True
			role.insert(ignore_permissions=True)
			frappe.db.commit()
		# What this site looked like before any test touched it. Restoring to
		# `reset_perms` alone is NOT enough: that deletes the install's own
		# Employee Self Service row too, so every later test - here and in every
		# other module in the run - would measure a site the install never
		# produced. Tests run alphabetically, which is how that kind of damage
		# gets blamed on the wrong module.
		cls.baseline = frappe.get_all(
			"Custom DocPerm",
			filters={"parent": SUBJECT},
			fields=PERM_FIELDS,
			limit_page_length=0,
		)
		assert cls.baseline, (
			f"{SUBJECT} has no custom rows on this site, so these tests would restore "
			"it to a state the install never produced. Check the site was built with hrms."
		)

	def setUp(self):
		frappe.set_user("Administrator")
		self._restore()

	def tearDown(self):
		self._restore()

	def _restore(self):
		"""Put SUBJECT back exactly as the install left it.

		`reset_perms` is Frappe's own undo - it deletes every Custom DocPerm row
		for the doctype - and then the rows captured in setUpClass go back in, so
		the site ends where it started rather than one row short.

		The doctype cache clear is the load-bearing line. Clearing the USER cache
		instead is the mistake that cost this programme a day on ALV-117: the rows
		were gone and the process still believed they were there.
		"""
		reset_perms(SUBJECT)
		for row in self.baseline:
			doc = frappe.get_doc(
				{
					"doctype": "Custom DocPerm",
					"parent": SUBJECT,
					"parenttype": "DocType",
					"parentfield": "permissions",
					**row,
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
		frappe.db.commit()
		frappe.clear_cache(doctype=SUBJECT)
		frappe.local.role_permissions = {}

	def _freeze(self):
		"""Do what a tenant does in the Desk: grant one role, the supported way."""
		add_permission(SUBJECT, GRANTED_ROLE, 0)
		frappe.db.commit()
		frappe.clear_cache(doctype=SUBJECT)

	def _finding(self, result, doctype=SUBJECT):
		return next(f for f in result["findings"] if f["doctype"] == doctype)

	# ── the clean site ──────────────────────────────────────────────────────

	def test_a_site_nobody_has_touched_is_already_frozen_and_the_check_says_why(self):
		"""Measured, and it surprised us: a fresh site is NOT clean.

		`bench new-site` plus erpnext, hrms, alvoraa_goals and alvoraa_portal,
		never opened by a human, already has custom rows on Attendance,
		Attendance Request and Leave Application - because Frappe HR's Employee
		Self Service user type calls add_permission on them. The 5 rows found on
		production's Attendance Request are that, not a tenant's administrator.

		So the check must say "expected", not "red". A check that is red on every
		healthy site is a check nobody reads.
		"""
		result = ph.check_permission_freeze(print_report=False)
		self.assertEqual(result["worst"], "frozen_at_install")
		for finding in result["findings"]:
			self.assertIn(finding["status"], ("ok", "frozen_at_install"), finding)
			self.assertEqual(finding["missing_required_roles"], [], finding)
			self.assertEqual(finding["roles_lost_against_standard"], [], finding)
			self.assertEqual(finding["roles_added_beyond_install"], [], finding)

	def test_the_install_really_is_what_froze_attendance_request(self):
		"""Pin the diagnosis, so a future Frappe HR change to it is visible here."""
		finding = self._finding(ph.check_permission_freeze(print_report=False))
		self.assertEqual(finding["status"], "frozen_at_install")
		self.assertEqual(finding["roles_added_against_standard"], ["Employee Self Service"])

	def test_employee_performance_feedback_is_the_one_that_is_still_standard(self):
		"""It is not on Frappe HR's ESS list - which is what production showed too."""
		finding = self._finding(ph.check_permission_freeze(print_report=False), "Employee Performance Feedback")
		self.assertEqual(finding["status"], "ok")
		self.assertEqual(finding["custom_rows"], 0)

	def test_it_says_what_it_read_and_refuses_to_pass_on_nothing(self):
		"""An OK that read nothing is the failure mode this guards against."""
		result = ph.check_permission_freeze(print_report=False)
		read = result["read"]
		self.assertEqual(read["doctypes_examined"], len(ph.WATCHED_DOCTYPES))
		self.assertGreater(read["standard_docperm_rows_read"], 0)

		with patch.dict(ph.WATCHED_DOCTYPES, {}, clear=True):
			with self.assertRaises(frappe.ValidationError) as caught:
				ph.check_permission_freeze(print_report=False)
		self.assertIn("examined no doctypes", str(caught.exception))

	# ── the freeze ──────────────────────────────────────────────────────────

	def test_granting_a_role_the_documented_way_shows_up_as_frozen(self):
		"""Nobody has lost access - but the doctype has stopped tracking upstream."""
		before = self._finding(ph.check_permission_freeze(print_report=False))
		self.assertEqual(before["status"], "frozen_at_install")

		self._freeze()

		after = self._finding(ph.check_permission_freeze(print_report=False))
		self.assertEqual(after["status"], "frozen")
		self.assertGreater(
			after["custom_rows"], 1, "add_permission should have copied the standard rows in"
		)
		self.assertEqual(after["missing_required_roles"], [])
		self.assertEqual(after["roles_lost_against_standard"], [])
		self.assertEqual(after["roles_added_beyond_install"], [GRANTED_ROLE])
		self.assertIn("upstream", " ".join(after["problems"]).lower())

	def test_add_permission_really_does_copy_first_so_nobody_loses_read(self):
		"""The correction at the heart of ALV-127, asserted rather than assumed.

		If a future Frappe version stops copying, this fails here rather than on
		a customer's site.
		"""
		self._freeze()
		for role in ph.REQUIRED_ROLES:
			self.assertTrue(
				frappe.db.exists("Custom DocPerm", {"parent": SUBJECT, "role": role, "read": 1}),
				f"{role} lost its read row when one unrelated role was granted",
			)

	# ── the delete ──────────────────────────────────────────────────────────

	def test_deleting_the_employee_row_turns_the_check_red(self):
		self._freeze()
		self._delete_row("Employee")

		finding = self._finding(ph.check_permission_freeze(print_report=False))
		self.assertEqual(finding["status"], "broken")
		self.assertEqual(finding["missing_required_roles"], ["Employee"])
		self.assertIn("cannot open", " ".join(finding["problems"]))
		self.assertIn("Employee", finding["action"])

	def test_deleting_the_hr_manager_row_turns_the_check_red(self):
		self._freeze()
		self._delete_row("HR Manager")

		finding = self._finding(ph.check_permission_freeze(print_report=False))
		self.assertEqual(finding["status"], "broken")
		self.assertEqual(finding["missing_required_roles"], ["HR Manager"])

	def test_a_role_lost_that_is_not_required_is_still_reported(self):
		"""HR User is not in REQUIRED_ROLES, but losing it is still a change."""
		self._freeze()
		self._delete_row("HR User")

		finding = self._finding(ph.check_permission_freeze(print_report=False))
		self.assertEqual(finding["status"], "frozen")
		self.assertIn("HR User", finding["roles_lost_against_standard"])

	def test_reset_to_default_leaves_no_trace_and_the_check_says_so(self):
		"""The Desk's "Reset to default" button is `reset_perms` underneath."""
		self._freeze()
		self.assertEqual(self._finding(ph.check_permission_freeze(print_report=False))["status"], "frozen")

		reset_perms(SUBJECT)
		frappe.db.commit()
		frappe.clear_cache(doctype=SUBJECT)

		# Back to "ok" - not "frozen_at_install" - because Reset to default deletes
		# the install's own Employee Self Service row along with everything else.
		# The tenant has silently undone part of the install, and the check shows
		# the doctype standing on its standard rows again.
		self.assertEqual(self._finding(ph.check_permission_freeze(print_report=False))["status"], "ok")

	# ── the narrow row that looks like access and is not ─────────────────────

	def test_an_if_owner_row_does_not_count_as_the_role_having_read(self):
		"""`if_owner` grants read only on records the user created.

		If that counted, a real loss of access would report healthy.
		"""
		self._freeze()
		row = frappe.db.get_value(
			"Custom DocPerm", {"parent": SUBJECT, "role": "Employee", "permlevel": 0}, "name"
		)
		frappe.db.set_value("Custom DocPerm", row, "if_owner", 1)
		frappe.db.commit()
		frappe.clear_cache(doctype=SUBJECT)

		finding = self._finding(ph.check_permission_freeze(print_report=False))
		self.assertEqual(finding["status"], "broken")
		self.assertIn("Employee", finding["missing_required_roles"])

	# ── the list itself ─────────────────────────────────────────────────────

	def test_a_doctype_on_the_list_that_is_not_installed_is_an_error_not_a_skip(self):
		with patch.dict(ph.WATCHED_DOCTYPES, {"ALV127 No Such Doctype": "made up on purpose"}):
			result = ph.check_permission_freeze(print_report=False)
		finding = self._finding(result, "ALV127 No Such Doctype")
		self.assertEqual(finding["status"], "broken")
		self.assertEqual(result["worst"], "broken")
		self.assertIn("not installed", " ".join(finding["problems"]))

	def test_the_printed_report_names_the_doctype_the_status_and_what_to_do(self):
		"""The report is what a human reads at two in the morning."""
		self._freeze()
		self._delete_row("Employee")
		text = ph._report(ph.check_permission_freeze(print_report=False))
		self.assertIn("BROKEN", text)
		self.assertIn(SUBJECT, text)
		self.assertIn("cannot open", text)
		self.assertIn("Role Permissions Manager", text)
		self.assertIn("standard permission rows", text)

	def test_every_watched_doctype_has_a_reason_written_next_to_it(self):
		"""The reason is what tells the next person what earns a place on the list."""
		for doctype, reason in ph.WATCHED_DOCTYPES.items():
			self.assertTrue(reason.strip(), f"{doctype} has no reason")
			self.assertGreater(len(reason), 20, f"{doctype}'s reason says nothing useful")

	def test_the_four_doctypes_the_ticket_named_are_all_watched(self):
		"""A pin: a merge that drops one of these must fail CI, not a customer."""
		for doctype in (
			"Attendance Request",
			"Leave Application",
			"Attendance",
			"Employee Performance Feedback",
		):
			self.assertIn(doctype, ph.WATCHED_DOCTYPES)

	# ── it must be safe to point at a live tenant ───────────────────────────

	def test_the_check_writes_nothing(self):
		"""Every permission row is byte-for-byte the same after a run."""
		self._freeze()
		before = self._snapshot()
		ph.check_permission_freeze(print_report=False)
		self.assertEqual(self._snapshot(), before)

	def _snapshot(self):
		return sorted(
			(r.parent, r.role, r.permlevel, r.if_owner, r.read, r.write)
			for table in ("Custom DocPerm", "DocPerm")
			for r in frappe.get_all(
				table,
				filters={"parent": ["in", sorted(ph.WATCHED_DOCTYPES)]},
				fields=["parent", "role", "permlevel", "if_owner", "read", "write"],
				limit_page_length=0,
			)
		)

	def _delete_row(self, role):
		"""Remove one role's row, the way the Desk's delete button does."""
		for name in frappe.get_all(
			"Custom DocPerm", filters={"parent": SUBJECT, "role": role}, pluck="name"
		):
			frappe.delete_doc("Custom DocPerm", name, ignore_permissions=True, force=True)
		frappe.db.commit()
		frappe.clear_cache(doctype=SUBJECT)


if __name__ == "__main__":
	unittest.main()
