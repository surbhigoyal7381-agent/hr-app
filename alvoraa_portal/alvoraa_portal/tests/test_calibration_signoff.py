"""Unit tests for save_calibration_signoff and get_calibration_signoff."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal.performance_api import get_calibration_signoff, save_calibration_signoff


def _make_cycle_config(cycle_name):
    """Create a minimal Alvoraa Cycle Config, skipping a real Appraisal Cycle link."""
    frappe.db.sql(
        """INSERT IGNORE INTO `tabAlvoraa Cycle Config`
           (name, appraisal_cycle, page_settings, creation, modified, owner, modified_by, docstatus)
           VALUES (%s, %s, %s, NOW(), NOW(), 'Administrator', 'Administrator', 0)""",
        (cycle_name, cycle_name, "{}"),
    )
    frappe.db.commit()


def _delete_cycle_config(cycle_name):
    frappe.db.sql(
        "DELETE FROM `tabAlvoraa Cycle Config` WHERE name = %s", (cycle_name,)
    )
    frappe.db.commit()


class TestCalibrationSignoff(FrappeTestCase):
    CYCLE = "TEST-SIGNOFF-CYCLE-001"

    def setUp(self):
        frappe.set_user("Administrator")
        _make_cycle_config(self.CYCLE)

    def tearDown(self):
        _delete_cycle_config(self.CYCLE)
        frappe.set_user("Administrator")

    def test_get_returns_none_before_signoff(self):
        result = get_calibration_signoff(self.CYCLE)
        self.assertIsNone(result)

    def test_save_and_get_roundtrip(self):
        summary = "Q2 calibration complete. Top performers confirmed."
        saved = save_calibration_signoff(self.CYCLE, summary)
        self.assertEqual(saved["summary"], summary)
        self.assertEqual(saved["signed_by"], "Administrator")
        self.assertIn("signed_at", saved)

        retrieved = get_calibration_signoff(self.CYCLE)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["summary"], summary)
        self.assertEqual(retrieved["signed_by"], "Administrator")

    def test_overwrite_preserves_other_page_settings(self):
        # Pre-populate page_settings with unrelated data
        existing = json.dumps({"some_other_key": "keep_me"})
        frappe.db.set_value("Alvoraa Cycle Config", self.CYCLE, "page_settings", existing)
        frappe.db.commit()

        save_calibration_signoff(self.CYCLE, "Second sign-off.")

        raw = frappe.db.get_value("Alvoraa Cycle Config", self.CYCLE, "page_settings")
        settings = json.loads(raw)
        self.assertEqual(settings.get("some_other_key"), "keep_me")
        self.assertEqual(settings["calibration_signoff"]["summary"], "Second sign-off.")

    def test_get_returns_none_for_missing_cycle(self):
        result = get_calibration_signoff("NONEXISTENT-CYCLE-XYZ")
        self.assertIsNone(result)

    def test_save_raises_for_missing_cycle(self):
        with self.assertRaises(frappe.exceptions.ValidationError):
            save_calibration_signoff("NONEXISTENT-CYCLE-XYZ", "Should fail.")

    def test_save_raises_without_summary(self):
        with self.assertRaises(frappe.exceptions.ValidationError):
            save_calibration_signoff(self.CYCLE, "")

    def test_save_raises_without_hr_role(self):
        # Create a user with no HR roles
        user_email = "test_no_hr_role@example.com"
        if not frappe.db.exists("User", user_email):
            u = frappe.get_doc({
                "doctype": "User",
                "email": user_email,
                "first_name": "NoHR",
                "send_welcome_email": 0,
                "roles": [{"role": "Guest"}],
            })
            u.insert(ignore_permissions=True)
            frappe.db.commit()

        frappe.set_user(user_email)
        with self.assertRaises(frappe.PermissionError):
            save_calibration_signoff(self.CYCLE, "Should be blocked.")
