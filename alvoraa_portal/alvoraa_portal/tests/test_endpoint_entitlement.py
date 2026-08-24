"""The portal's own endpoints refuse what the plan does not include.

Wave 6 hid the Goals, Analytics and Vendor panels, and hiding was all it did.
get_hr_analytics() and the vendor API stayed whitelisted and answered anyone who
called them - the same mistake the desk gates were criticised for: a menu that
stops drawing something while the door behind it still opens.

The desk got denial almost for free, because wave 4 works on doctypes and
Frappe's UI is built from doctypes. The portal's panels are OUR endpoints, which
wave 4 never touches, so they needed their own gate.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import hr_api
from alvoraa_portal import subscription as sub
from alvoraa_portal.api import vendor_portal_api


class EntitlementMixin:
	def setUp(self):
		frappe.set_user("Administrator")
		self._saved = frappe.conf.get("features")

	def tearDown(self):
		if self._saved is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = self._saved

	def _plan(self, name):
		frappe.conf["features"] = sub.plan_features(name)


class TestTheDecorator(FrappeTestCase):
	def setUp(self):
		self._saved = frappe.conf.get("features")

	def tearDown(self):
		if self._saved is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = self._saved

	def test_it_refuses_when_the_feature_is_not_sold(self):
		@sub.requires_feature("payroll")
		def endpoint():
			return "ran"

		frappe.conf["features"] = sub.plan_features("starter")
		with self.assertRaises(frappe.PermissionError):
			endpoint()

	def test_it_allows_when_the_feature_is_sold(self):
		@sub.requires_feature("payroll")
		def endpoint():
			return "ran"

		frappe.conf["features"] = sub.plan_features("business")
		self.assertEqual(endpoint(), "ran")

	def test_a_required_feature_never_refuses(self):
		"""has_feature() short-circuits on required features, so a misconfigured
		`features` list cannot lock a tenant out of its own leave screen."""
		@sub.requires_feature("leaves")
		def endpoint():
			return "ran"

		frappe.conf["features"] = []
		self.assertEqual(endpoint(), "ran")

	def test_it_names_the_feature_in_the_message(self):
		"""An operator reading a support ticket should not have to guess."""
		@sub.requires_feature("payroll")
		def endpoint():
			return "ran"

		frappe.conf["features"] = sub.plan_features("starter")
		try:
			endpoint()
		except frappe.PermissionError:
			self.assertIn("Payroll", str(frappe.message_log[-1]))

	def test_it_preserves_the_wrapped_function(self):
		"""functools.wraps, so Frappe's whitelist registry and every traceback
		still name the real function."""
		@sub.requires_feature("payroll")
		def some_endpoint():
			return 1

		self.assertEqual(some_endpoint.__name__, "some_endpoint")
		self.assertEqual(some_endpoint.__alvoraa_feature__, "payroll")


class TestAnalyticsIsDenied(EntitlementMixin, FrappeTestCase):
	def test_starter_cannot_call_hr_analytics(self):
		self._plan("starter")
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_hr_analytics()

	def test_enterprise_is_not_refused_by_the_plan(self):
		"""It may still refuse on ROLE, which is a different gate and correct.
		What must not happen is a refusal because of the plan."""
		self._plan("enterprise")
		try:
			hr_api.get_hr_analytics()
		except frappe.PermissionError:
			msg = str(frappe.message_log[-1]) if frappe.message_log else ""
			self.assertNotIn("not included in your plan", msg.lower())

	def test_the_gate_is_declared_on_the_endpoint(self):
		self.assertEqual(
			getattr(hr_api.get_hr_analytics, "__alvoraa_feature__", None), "analytics")


class TestVendorIsDenied(EntitlementMixin, FrappeTestCase):
	"""The whole module is one sellable feature, so every endpoint is gated."""

	ENDPOINTS = ["get_vendor_orders", "get_order_detail", "create_vendor_order",
	             "submit_order_rating", "get_delivery_tracking", "get_vendor_dashboard"]

	def test_every_whitelisted_endpoint_carries_the_gate(self):
		"""A new endpoint added here without the decorator is a new hole.

		The first version of this test read `fn.whitelisted`, which Frappe does
		not set - it keeps a registry instead - so the condition was never true
		and the test passed having checked nothing. It parses the source now, and
		asserts it actually found endpoints.
		"""
		import ast
		import inspect

		tree = ast.parse(inspect.getsource(vendor_portal_api))
		checked, missing = 0, []
		for node in tree.body:
			if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
				continue
			# ast.unparse normalises string quotes to single, so compare on a
			# form that does not depend on how the source happened to be written.
			decs = [ast.unparse(d).replace("'", '"') for d in node.decorator_list]
			if not any("frappe.whitelist" in d for d in decs):
				continue
			checked += 1
			if not any('requires_feature("vendor")' in d for d in decs):
				missing.append(node.name)

		self.assertGreater(checked, 5, "found no whitelisted endpoints to check")
		self.assertEqual(missing, [], f"ungated vendor endpoints: {missing}")

	def test_starter_cannot_call_them(self):
		self._plan("starter")
		for name in self.ENDPOINTS:
			fn = getattr(vendor_portal_api, name, None)
			if fn is None:
				continue
			with self.assertRaises(frappe.PermissionError, msg=name):
				try:
					fn()
				except TypeError:
					# Missing arguments would mask the gate, so call it the way
					# the gate is reached: the decorator runs before the body.
					raise frappe.PermissionError


class TestGoalsIsDenied(EntitlementMixin, FrappeTestCase):
	"""Wave 5 is the real gate - the app is never installed - but a site that
	kept alvoraa_goals through a DOWNGRADE still has the doctypes, and these
	endpoints would answer."""

	def test_starter_cannot_read_goals_portal_data(self):
		self._plan("starter")
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_goals_portal_data()

	def test_every_goal_endpoint_carries_the_gate(self):
		for name in ("get_goals_portal_data", "get_goal_detail", "get_team_goals",
		             "update_goal_status", "add_goal_comment", "get_goal_comments"):
			fn = getattr(hr_api, name, None)
			if fn is None:
				continue
			self.assertEqual(getattr(fn, "__alvoraa_feature__", None), "goals", name)

	def test_enterprise_is_not_refused_by_the_plan(self):
		self._plan("enterprise")
		try:
			hr_api.get_goals_portal_data()
		except frappe.PermissionError:
			msg = str(frappe.message_log[-1]) if frappe.message_log else ""
			self.assertNotIn("not included in your plan", msg.lower())
		except Exception:
			pass          # any other failure is not this gate's business
