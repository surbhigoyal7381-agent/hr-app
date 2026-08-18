import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.exceptions import ValidationError


def make_test_vendor(active=True):
    """Create a minimal Vendor for testing."""
    vendor = frappe.new_doc("Vendor")
    vendor.vendor_name = f"Test Vendor {frappe.utils.random_string(5)}"
    vendor.company_name = "Test Company"
    vendor.email = f"test_{frappe.utils.random_string(5)}@example.com"
    vendor.phone = "9999999999"
    vendor.account_status = "Active" if active else "Inactive"
    vendor.insert(ignore_permissions=True)
    return vendor


def make_test_order(vendor_name, items=None):
    """Create a minimal Vendor Order for testing."""
    order = frappe.new_doc("Vendor Order")
    order.vendor = vendor_name
    order.order_date = frappe.utils.today()
    order.delivery_address = "123 Test Street, Test City"
    order.delivery_slot = "Tomorrow"
    order.order_status = "Draft"

    if items is None:
        items = [{"sku": "TEST-SKU-001", "quantity": 2, "unit_price": 50}]

    for item in items:
        order.append("items", item)

    return order


class TestVendorOrderTotalCalculation(FrappeTestCase):
    def test_order_total_calculation(self):
        """Create order doc with 2 items, validate, assert total_amount = sum of line_totals."""
        vendor = make_test_vendor()
        order = make_test_order(
            vendor.name,
            items=[
                {"sku": "SKU-A", "quantity": 3, "unit_price": 100},
                {"sku": "SKU-B", "quantity": 2, "unit_price": 75},
            ],
        )
        order.insert(ignore_permissions=True)

        # After insert, validate is called
        self.assertAlmostEqual(order.total_amount, 3 * 100 + 2 * 75)
        self.assertAlmostEqual(order.items[0].line_total, 300)
        self.assertAlmostEqual(order.items[1].line_total, 150)

    def tearDown(self):
        frappe.db.rollback()


class TestVendorOrderStatusTransition(FrappeTestCase):
    def test_invalid_status_transition(self):
        """Draft → Delivered should raise ValidationError via VALID_TRANSITIONS check."""
        from alvoraa_portal.controllers.vendor_order import change_order_status, VALID_TRANSITIONS

        vendor = make_test_vendor()
        order = make_test_order(vendor.name)
        order.insert(ignore_permissions=True)
        order.submit()

        # Draft is now Under Review after submit; test invalid transition
        with self.assertRaises(frappe.ValidationError):
            change_order_status(order.name, "Delivered")

    def test_valid_status_transition(self):
        """Draft → Under Review should succeed (happens on submit)."""
        vendor = make_test_vendor()
        order = make_test_order(vendor.name)
        order.insert(ignore_permissions=True)
        order.submit()

        # After submit, status should be Under Review
        updated = frappe.get_doc("Vendor Order", order.name)
        self.assertEqual(updated.order_status, "Under Review")

    def tearDown(self):
        frappe.db.rollback()


class TestVendorInactiveCannotOrder(FrappeTestCase):
    def test_vendor_inactive_cannot_order(self):
        """Vendor with account_status=Inactive should not be able to insert order (validate raises)."""
        vendor = make_test_vendor(active=False)
        order = make_test_order(vendor.name)

        with self.assertRaises(frappe.ValidationError):
            order.insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()
