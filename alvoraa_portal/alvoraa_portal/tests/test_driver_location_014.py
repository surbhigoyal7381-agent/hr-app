"""Slice 014: only the assigned driver may post a location for a delivery.

`portal_api.update_driver_location` inserted a Vehicle Tracking row with
ignore_permissions and checked nothing about the caller. Any logged-in user
could write a position, speed and heading for any Delivery Order - a fake trail
for someone else's delivery, or a false speeding alert against a driver.

The rule now: the caller must be the Delivery Partner (matched by
`primary_email`, the same rule get_portal_context uses to recognise a driver)
assigned to that order. Every other case is the same PermissionError and
writes nothing.
"""

from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import portal_api

DRIVER_A = "driver.a.014@example.com"
DRIVER_B = "driver.b.014@example.com"
NOT_A_DRIVER = "not.a.driver.014@example.com"


def _user(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0],
		                "send_welcome_email": 0}).insert(ignore_permissions=True)


def _partner(email):
	existing = frappe.db.get_value("Delivery Partner", {"primary_email": email}, "name")
	if existing:
		return existing
	return frappe.get_doc({
		"doctype": "Delivery Partner", "partner_name": email.split("@")[0],
		"partner_type": "Contractual", "primary_email": email, "status": "Active",
	}).insert(ignore_permissions=True).name


def _order(partner=None):
	# Delivery Order's before_save geocodes the address over the internet
	# (Nominatim). Tests must not make outside calls.
	with mock.patch("alvoraa_portal.controllers.delivery_order._geocode_address"):
		return _insert_order(partner)


def _insert_order(partner):
	return frappe.get_doc({
		"doctype": "Delivery Order", "delivery_date": frappe.utils.today(),
		"customer_name": "CI Customer 014", "delivery_address": "CI address",
		"assigned_to_partner": partner, "current_status": "In Transit" if partner else "Pending",
	}).insert(ignore_permissions=True).name


class OnlyTheAssignedDriverPosts(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		# Slice 016 gated the whole vendor and driver module by plan, and
		# test_site is on the starter feature list. These tests are about WHO may
		# post, not about the plan, so the feature is switched on for them.
		cls._saved_features = frappe.conf.get("features")
		frappe.conf["features"] = list(cls._saved_features or []) + ["vendor"]
		for email in (DRIVER_A, DRIVER_B, NOT_A_DRIVER):
			_user(email)
		cls.partner_a = _partner(DRIVER_A)
		cls.partner_b = _partner(DRIVER_B)
		cls.order_a = _order(cls.partner_a)
		cls.unassigned = _order(None)
		# The endpoint commits; commit fixtures too so the cleanup below owns them.
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for order in (cls.order_a, cls.unassigned):
			for row in frappe.get_all("Vehicle Tracking", {"delivery_order": order}, pluck="name"):
				frappe.delete_doc("Vehicle Tracking", row, force=True, ignore_permissions=True)
			frappe.delete_doc("Delivery Order", order, force=True, ignore_permissions=True)
		for partner in (cls.partner_a, cls.partner_b):
			frappe.delete_doc("Delivery Partner", partner, force=True, ignore_permissions=True)
		frappe.db.commit()
		if cls._saved_features is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = cls._saved_features
		super().tearDownClass()

	def tearDown(self):
		frappe.set_user("Administrator")

	def rows(self, order):
		return frappe.db.count("Vehicle Tracking", {"delivery_order": order})

	def post_as(self, user, order):
		frappe.set_user(user)
		return portal_api.update_driver_location(order, "30.7101", "76.8012", speed=20, heading=90)

	def test_014_driver_location_assigned_driver_can_post(self):
		"""The real driver keeps working: the portal's GPS post is accepted."""
		before = self.rows(self.order_a)
		self.assertEqual(self.post_as(DRIVER_A, self.order_a), "ok")
		self.assertEqual(self.rows(self.order_a), before + 1)
		row = frappe.get_all("Vehicle Tracking", {"delivery_order": self.order_a},
		                     ["delivery_partner", "latitude"], order_by="creation desc", limit=1)[0]
		self.assertEqual(row.delivery_partner, self.partner_a)

	def test_014_driver_location_other_driver_refused(self):
		before = self.rows(self.order_a)
		with self.assertRaises(frappe.PermissionError):
			self.post_as(DRIVER_B, self.order_a)
		self.assertEqual(self.rows(self.order_a), before)

	def test_014_driver_location_non_driver_refused(self):
		"""A logged-in user with no Delivery Partner - including an admin - may
		not post a driver's position."""
		for user in (NOT_A_DRIVER, "Administrator"):
			before = self.rows(self.order_a)
			with self.assertRaises(frappe.PermissionError, msg=user):
				self.post_as(user, self.order_a)
			self.assertEqual(self.rows(self.order_a), before, user)

	def test_014_driver_location_unassigned_or_missing_order_refused(self):
		"""Same refusal for an order with nobody assigned and for one that does
		not exist, so the answer does not reveal which orders exist."""
		messages = []
		for order in (self.unassigned, "DO-DOES-NOT-EXIST-014"):
			frappe.clear_messages()
			with self.assertRaises(frappe.PermissionError):
				self.post_as(DRIVER_A, order)
			last = frappe.local.message_log[-1] if frappe.local.message_log else {}
			# The words only: each queued message also carries a random id.
			messages.append(last.get("message") if isinstance(last, dict) else last)
		self.assertEqual(self.rows(self.unassigned), 0)
		self.assertTrue(messages[0])
		self.assertEqual(messages[0], messages[1])

	def test_014_driver_location_guest_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self.post_as("Guest", self.order_a)
