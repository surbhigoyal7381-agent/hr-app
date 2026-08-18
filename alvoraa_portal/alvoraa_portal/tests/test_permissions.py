import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch


class TestVendorCannotSeeOtherVendorOrder(FrappeTestCase):
    def test_vendor_cannot_see_other_vendor_order(self):
        """Calling get_order_detail for another vendor's order raises PermissionError."""
        # Create vendor A
        vendor_a = frappe.new_doc("Vendor")
        vendor_a.vendor_name = f"Vendor A {frappe.utils.random_string(4)}"
        vendor_a.company_name = "Company A"
        vendor_a.email = f"a_{frappe.utils.random_string(4)}@example.com"
        vendor_a.phone = "1111111111"
        vendor_a.account_status = "Active"
        vendor_a.insert(ignore_permissions=True)

        # Create vendor B
        vendor_b = frappe.new_doc("Vendor")
        vendor_b.vendor_name = f"Vendor B {frappe.utils.random_string(4)}"
        vendor_b.company_name = "Company B"
        vendor_b.email = f"b_{frappe.utils.random_string(4)}@example.com"
        vendor_b.phone = "2222222222"
        vendor_b.account_status = "Active"
        vendor_b.insert(ignore_permissions=True)

        # Create Frappe User for vendor B
        user_b = frappe.new_doc("User")
        user_b.email = vendor_b.email
        user_b.first_name = "Vendor B"
        user_b.send_welcome_email = 0
        user_b.insert(ignore_permissions=True)

        # Create Vendor User linking user_b to vendor_b
        vu_b = frappe.new_doc("Vendor User")
        vu_b.vendor = vendor_b.name
        vu_b.email = vendor_b.email
        vu_b.frappe_user = user_b.name
        vu_b.insert(ignore_permissions=True)

        # Create order belonging to vendor A
        order_a = frappe.new_doc("Vendor Order")
        order_a.vendor = vendor_a.name
        order_a.order_date = frappe.utils.today()
        order_a.delivery_address = "Vendor A Street"
        order_a.delivery_slot = "Tomorrow"
        order_a.append("items", {"sku": "SKU-A", "quantity": 1, "unit_price": 100})
        order_a.flags.ignore_validate = True
        order_a.insert(ignore_permissions=True)

        # Simulate being logged in as vendor_b's user
        from alvoraa_portal.api.vendor_portal_api import _assert_vendor_owns_order

        with self.assertRaises(frappe.PermissionError):
            _assert_vendor_owns_order(order_a.name, vendor_b.name)

    def tearDown(self):
        frappe.db.rollback()


class TestUnauthenticatedApiCall(FrappeTestCase):
    def test_unauthenticated_api_call(self):
        """Calling get_vendor_dashboard without Vendor User linked raises PermissionError."""
        from alvoraa_portal.api.vendor_portal_api import _get_vendor_id

        # Simulate a user with no linked Vendor User
        with patch.object(frappe, "session") as mock_session:
            mock_session.user = "no-vendor@example.com"
            with patch("frappe.get_value", return_value=None):
                with self.assertRaises(frappe.PermissionError):
                    _get_vendor_id()

    def tearDown(self):
        frappe.db.rollback()
