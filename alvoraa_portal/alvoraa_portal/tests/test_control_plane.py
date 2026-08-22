"""The tenant admin console must exist ONLY on the control plane.

A tenant site is an ordinary Frappe site, and its own administrators legitimately
hold System Manager there. So a role check alone is not a boundary: it let a
tenant admin open the console that lists, suspends and reconfigures EVERY tenant
on the bench.

Verified live on demo.alvoraa.co before the fix - HTTP 200, rendering
"Create New Tenant".
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import tenant_api


class TestControlPlaneIsolation(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._saved = frappe.conf.get("alvoraa_control_plane")

	def tearDown(self):
		if self._saved is None:
			frappe.conf.pop("alvoraa_control_plane", None)
		else:
			frappe.conf["alvoraa_control_plane"] = self._saved
		frappe.set_user("Administrator")

	def test_tenant_api_refuses_when_not_control_plane(self):
		"""Even Administrator must not manage tenants from a tenant site."""
		frappe.conf.pop("alvoraa_control_plane", None)
		with self.assertRaises(frappe.PermissionError):
			tenant_api.list_tenants()

	def test_tenant_api_allows_on_control_plane(self):
		frappe.conf["alvoraa_control_plane"] = 1
		tenant_api.list_tenants()   # must not raise

	def test_is_control_plane_reports_the_flag(self):
		frappe.conf.pop("alvoraa_control_plane", None)
		self.assertFalse(tenant_api.is_control_plane())
		frappe.conf["alvoraa_control_plane"] = 1
		self.assertTrue(tenant_api.is_control_plane())

	def test_admin_page_is_hidden_on_a_tenant_site(self):
		"""The PAGE guard, not just the API. This is the gap that was live:
		the API refused, but the console still rendered."""
		from alvoraa_portal.www import alvoraa_admin

		frappe.conf.pop("alvoraa_control_plane", None)
		ctx = frappe._dict()
		with self.assertRaises(frappe.DoesNotExistError):
			alvoraa_admin.get_context(ctx)
