import frappe
import unittest
from frappe.tests.utils import FrappeTestCase


class TestPermissions(FrappeTestCase):

    def test_employee_cannot_edit_target(self):
        # Employee role should not have general write permission on Individual Goal
        # (only if_owner-scoped write is allowed)
        meta = frappe.get_meta("Individual Goal")
        permissions = meta.get("permissions", [])
        employee_perms = [p for p in permissions if p.role == "Employee"]
        for perm in employee_perms:
            if not perm.if_owner:
                self.assertEqual(
                    perm.get("write"), 0,
                    "Employee role should not have write permission on Individual Goal without if_owner"
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
