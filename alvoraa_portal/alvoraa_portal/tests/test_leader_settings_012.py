"""Slice 012 push 1 · the minimum group setting obeys its rules on every path (SEC-10, SEC-12).

Push 1 creates the settings record without its screen: the morning check reads
the minimum, and the "last checked" stamp lives here. The rules are in the
controller, so the desk, REST and set_value obey them as the screen will.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint

from alvoraa_portal.alvoraa_portal.doctype.alvoraa_leader_view_settings import (
	alvoraa_leader_view_settings as lvs,
)

DOCTYPE = lvs.DOCTYPE


def _user(first, *roles):
	email = f"{first.lower()}.s012set@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
		                "send_welcome_email": 0}).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(*roles)
	return email


class SettingsCase(FrappeTestCase):
	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		frappe.db.set_single_value(DOCTYPE, "min_group_size", 5, update_modified=False)
		frappe.db.set_single_value(DOCTYPE, "change_reason", None, update_modified=False)
		frappe.clear_document_cache(DOCTYPE, DOCTYPE)
		self.sm = _user("VikramSet", "System Manager")
		self.hrm = _user("PriyaSet", "HR Manager")

	def tearDown(self):
		frappe.set_user(self.caller)

	def stored(self):
		return cint(frappe.db.get_single_value(DOCTYPE, "min_group_size", cache=False))

	def save_as(self, user, value, reason=None):
		frappe.set_user(user)
		try:
			doc = frappe.get_doc(DOCTYPE)
			doc.min_group_size = value
			doc.change_reason = reason
			doc.save(ignore_version=False)
			return doc
		finally:
			frappe.set_user("Administrator")


class TestOnlySystemManagerSaves(SettingsCase):
	def test_hr_manager_is_refused_in_the_desk(self):
		with self.assertRaises(frappe.PermissionError):
			self.save_as(self.hrm, 3, "testing")
		self.assertEqual(self.stored(), 5)

	def test_hr_manager_is_refused_through_set_value(self):
		frappe.set_user(self.hrm)
		with self.assertRaises(frappe.PermissionError):
			frappe.client.set_value(DOCTYPE, DOCTYPE, {"min_group_size": 3, "change_reason": "x"})
		frappe.set_user("Administrator")
		self.assertEqual(self.stored(), 5)

	def test_hr_manager_is_refused_through_rest_save(self):
		frappe.set_user(self.hrm)
		doc = frappe.get_doc(DOCTYPE).as_dict()
		doc.update({"min_group_size": 3, "change_reason": "x"})
		with self.assertRaises(frappe.PermissionError):
			frappe.client.save(doc)
		frappe.set_user("Administrator")
		self.assertEqual(self.stored(), 5)

	def test_hr_manager_can_read_it(self):
		frappe.set_user(self.hrm)
		self.assertTrue(frappe.has_permission(DOCTYPE, "read"))
		self.assertFalse(frappe.has_permission(DOCTYPE, "write"))


class TestTheRules(SettingsCase):
	def test_a_change_needs_a_reason(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_as(self.sm, 6)
		self.assertEqual(self.stored(), 5)

	def test_two_and_eleven_are_refused(self):
		for value in (2, 11):
			with self.assertRaises(frappe.ValidationError):
				self.save_as(self.sm, value, "testing the range")
		self.assertEqual(self.stored(), 5)

	def test_a_save_without_a_change_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_as(self.sm, 5, "no change")

	def test_a_change_is_kept_with_its_reason_and_the_reason_is_then_cleared(self):
		before = frappe.db.count("Version", {"ref_doctype": DOCTYPE})
		self.save_as(self.sm, 7, "Stores merged into larger teams")
		self.assertEqual(self.stored(), 7)
		versions = frappe.get_all("Version", filters={"ref_doctype": DOCTYPE},
		                          fields=["data", "owner"], order_by="creation desc")
		self.assertEqual(len(versions), before + 1)
		data = frappe.parse_json(versions[0].data)
		changed = {row[0]: row[1:] for row in data.get("changed", [])}
		self.assertEqual([cint(v) for v in changed["min_group_size"]], [5, 7])
		self.assertEqual(changed["change_reason"][1], "Stores merged into larger teams")
		self.assertEqual(versions[0].owner, self.sm)
		# Cleared after the history row, so the next change cannot reuse it.
		self.assertFalse(frappe.db.get_single_value(DOCTYPE, "change_reason", cache=False))


class TestReadingTheMinimum(SettingsCase):
	def test_a_stored_value_in_range_is_used(self):
		self.assertEqual(lvs.min_group_size(), 5)

	def test_a_broken_value_reads_as_ten(self):
		"""Q7: a console-set 1 must not share tiny groups."""
		for broken in (1, 0, 42, "abc"):
			frappe.db.set_single_value(DOCTYPE, "min_group_size", broken, update_modified=False)
			self.assertEqual(lvs.min_group_size(), 10, broken)

	def test_set_up_stores_five_once_and_never_overwrites(self):
		frappe.db.sql("delete from `tabSingles` where doctype=%s and field='min_group_size'", DOCTYPE)
		lvs.ensure_default()
		self.assertEqual(self.stored(), 5)
		frappe.db.set_single_value(DOCTYPE, "min_group_size", 8, update_modified=False)
		lvs.ensure_default()
		self.assertEqual(self.stored(), 8)

	def test_the_minimum_is_not_a_frappe_default(self):
		"""SEC-12: never in tabDefaultValue, so set_org_setting can never reach it."""
		self.assertFalse(frappe.db.sql(
			"select 1 from `tabDefaultValue` where defkey like %s", "%min_group%"))

	def test_the_last_checked_stamp_adds_no_history(self):
		"""OPS-50: written every morning without a Version row."""
		before = frappe.db.count("Version", {"ref_doctype": DOCTYPE})
		frappe.db.set_single_value(DOCTYPE, "last_checks_run_on", frappe.utils.now_datetime())
		self.assertEqual(frappe.db.count("Version", {"ref_doctype": DOCTYPE}), before)
