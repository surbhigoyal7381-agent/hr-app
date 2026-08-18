import frappe
import unittest
from frappe.tests.utils import FrappeTestCase


class TestPermissions(FrappeTestCase):

    def test_row_level_scoping_is_wired(self):
        # Write access for Employees is NOT restricted by the doctype's `if_owner` flag.
        # It is enforced in Python by has_employee_permission, which allows write only
        # when the current user raised the record. This test guards the wiring: if the
        # hooks are ever dropped, every Employee silently gains write on every goal.
        for hook, expected in (
            ("permission_query_conditions", "alvoraa_goals.permissions.individual_goal_query"),
            ("has_permission", "alvoraa_goals.permissions.has_employee_permission"),
        ):
            handlers = frappe.get_hooks(hook, {}).get("Individual Goal") or []
            if isinstance(handlers, str):
                handlers = [handlers]
            self.assertIn(
                expected, handlers,
                f"{hook} for Individual Goal must be handled by {expected}; "
                "without it doctype-level write=1 is unscoped",
            )

    def test_permission_hook_denies_unknown_user(self):
        # Deny by default: a user with no employee record manages nobody, so the hook
        # must refuse rather than fall through to the doctype's write=1.
        from alvoraa_goals.permissions import has_employee_permission

        doc = frappe._dict({"employee": "EMP-NONEXISTENT", "owner": "someone.else@example.com"})
        self.assertFalse(
            has_employee_permission(doc, "write", "nobody@example.com"),
            "A user with no manageable employees must not get write access",
        )

    def test_employee_can_read_own_goal(self):
        # Employee role should have read permission on Individual Goal
        meta = frappe.get_meta("Individual Goal")
        permissions = meta.get("permissions", [])
        employee_perms = [p for p in permissions if p.role == "Employee"]
        self.assertTrue(len(employee_perms) > 0, "Employee permissions should exist on Individual Goal")
        has_read = any(p.get("read") for p in employee_perms)
        self.assertTrue(has_read, "Employee role should have read permission on Individual Goal")

    def test_hr_manager_can_write(self):
        # HR Manager should have write permission on Individual Goal
        meta = frappe.get_meta("Individual Goal")
        permissions = meta.get("permissions", [])
        hr_manager_perms = [p for p in permissions if p.role == "HR Manager"]
        self.assertTrue(len(hr_manager_perms) > 0, "HR Manager permissions should exist on Individual Goal")
        has_write = any(p.get("write") for p in hr_manager_perms)
        self.assertTrue(has_write, "HR Manager role should have write permission on Individual Goal")

    def test_goal_cascade_employee_read_only(self):
        # Employee should have read permission but NOT write permission on Goal Cascade
        meta = frappe.get_meta("Goal Cascade")
        permissions = meta.get("permissions", [])
        employee_perms = [p for p in permissions if p.role == "Employee"]
        self.assertTrue(len(employee_perms) > 0, "Employee permissions should exist for Goal Cascade")
        has_read = any(p.get("read") for p in employee_perms)
        self.assertTrue(has_read, "Employee role should have read permission on Goal Cascade")
        has_write = any(p.get("write") for p in employee_perms)
        self.assertFalse(has_write, "Employee role should not have write permission on Goal Cascade")
