import frappe
from frappe.tests.utils import FrappeTestCase


def make_delivered_order_and_vendor():
    """Helper: create a vendor and a delivered order."""
    vendor = frappe.new_doc("Vendor")
    vendor.vendor_name = f"Rating Vendor {frappe.utils.random_string(5)}"
    vendor.company_name = "Rating Co"
    vendor.email = f"rating_{frappe.utils.random_string(5)}@example.com"
    vendor.phone = "8888888888"
    vendor.account_status = "Active"
    vendor.insert(ignore_permissions=True)

    order = frappe.new_doc("Vendor Order")
    order.vendor = vendor.name
    order.order_date = frappe.utils.today()
    order.delivery_address = "456 Rating Road"
    order.delivery_slot = "Tomorrow"
    order.order_status = "Delivered"  # Set directly for test
    order.append("items", {"sku": "TEST-SKU", "quantity": 1, "unit_price": 100})
    # Bypass validate to set Delivered status directly
    order.flags.ignore_validate = True
    order.insert(ignore_permissions=True)
    # Force set status to Delivered
    frappe.db.set_value("Vendor Order", order.name, "order_status", "Delivered")

    return vendor, order


class TestRatingValidationRange(FrappeTestCase):
    def test_rating_validation_range(self):
        """Rating outside 1-5 should raise ValidationError."""
        vendor, order = make_delivered_order_and_vendor()

        rating = frappe.new_doc("Order Rating")
        rating.vendor_order = order.name
        rating.vendor = vendor.name
        rating.rating_date = frappe.utils.now_datetime()
        rating.order_quality_rating = 6  # Invalid
        rating.delivery_timeliness_rating = 3
        rating.driver_professionalism_rating = 3

        with self.assertRaises(frappe.ValidationError):
            rating.insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()


class TestRatingOnlyAfterDelivery(FrappeTestCase):
    def test_rating_only_after_delivery(self):
        """Rating on non-Delivered order should raise ValidationError."""
        vendor = frappe.new_doc("Vendor")
        vendor.vendor_name = f"Vendor {frappe.utils.random_string(5)}"
        vendor.company_name = "Test Co"
        vendor.email = f"t_{frappe.utils.random_string(5)}@example.com"
        vendor.phone = "7777777777"
        vendor.account_status = "Active"
        vendor.insert(ignore_permissions=True)

        order = frappe.new_doc("Vendor Order")
        order.vendor = vendor.name
        order.order_date = frappe.utils.today()
        order.delivery_address = "Test"
        order.delivery_slot = "Tomorrow"
        order.append("items", {"sku": "SKU", "quantity": 1, "unit_price": 10})
        order.insert(ignore_permissions=True)
        # status is Draft

        rating = frappe.new_doc("Order Rating")
        rating.vendor_order = order.name
        rating.vendor = vendor.name
        rating.rating_date = frappe.utils.now_datetime()
        rating.order_quality_rating = 4
        rating.delivery_timeliness_rating = 4
        rating.driver_professionalism_rating = 4

        with self.assertRaises(frappe.ValidationError):
            rating.insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()


class TestNoDuplicateRating(FrappeTestCase):
    def test_no_duplicate_rating(self):
        """Second rating for same order should raise ValidationError."""
        vendor, order = make_delivered_order_and_vendor()

        # First rating
        rating1 = frappe.new_doc("Order Rating")
        rating1.vendor_order = order.name
        rating1.vendor = vendor.name
        rating1.rating_date = frappe.utils.now_datetime()
        rating1.order_quality_rating = 4
        rating1.delivery_timeliness_rating = 4
        rating1.driver_professionalism_rating = 4
        rating1.insert(ignore_permissions=True)

        # Second rating should fail
        rating2 = frappe.new_doc("Order Rating")
        rating2.vendor_order = order.name
        rating2.vendor = vendor.name
        rating2.rating_date = frappe.utils.now_datetime()
        rating2.order_quality_rating = 3
        rating2.delivery_timeliness_rating = 3
        rating2.driver_professionalism_rating = 3

        with self.assertRaises(frappe.ValidationError):
            rating2.insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()


class TestAverageCalculation(FrappeTestCase):
    def test_average_calculation(self):
        """avg of (4, 5, 3) = 4.0."""
        vendor, order = make_delivered_order_and_vendor()

        rating = frappe.new_doc("Order Rating")
        rating.vendor_order = order.name
        rating.vendor = vendor.name
        rating.rating_date = frappe.utils.now_datetime()
        rating.order_quality_rating = 4
        rating.delivery_timeliness_rating = 5
        rating.driver_professionalism_rating = 3
        rating.insert(ignore_permissions=True)

        self.assertAlmostEqual(rating.average_rating, 4.0)

    def tearDown(self):
        frappe.db.rollback()
