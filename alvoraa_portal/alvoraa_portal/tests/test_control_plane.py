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


class TestPortalHidesTenantAdminOnTenants(FrappeTestCase):
	"""The portal's "Tenant Admin" link is for Alvoraa operators, not customers.

	It used to appear for any System Manager, which on a provisioned tenant means
	that tenant's OWN administrator. They were shown a link to /alvoraa-admin -
	a page that then refused them. A door advertised to people who cannot open
	it, pointing at tooling that is not theirs.
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		self._saved = frappe.conf.get("alvoraa_control_plane")
		self._clear_context_cache()

	def tearDown(self):
		if self._saved is None:
			frappe.conf.pop("alvoraa_control_plane", None)
		else:
			frappe.conf["alvoraa_control_plane"] = self._saved
		self._clear_context_cache()
		frappe.db.rollback()

	def _clear_context_cache(self):
		"""The portal context is cached for an hour under `portal_ctx_<user>`.

		Without clearing the exact key, a test that flips the flag reads the
		PREVIOUS test's answer and passes or fails for the wrong reason - which
		is what happened the first time this was written.
		"""
		frappe.cache().delete_value(f"portal_ctx_{frappe.session.user}")

	def _ctx(self):
		from alvoraa_portal import hr_api

		self._clear_context_cache()
		return hr_api.get_portal_context()

	def test_a_tenant_site_reports_false(self):
		frappe.conf.pop("alvoraa_control_plane", None)
		self.assertFalse(self._ctx().get("is_control_plane"),
		                 "a tenant must not advertise the tenant-admin console")

	def test_the_control_plane_reports_true(self):
		frappe.conf["alvoraa_control_plane"] = 1
		self.assertTrue(self._ctx().get("is_control_plane"))

	def test_the_flag_is_independent_of_being_a_system_manager(self):
		"""Both conditions are needed. Being an admin on a tenant is not enough,
		and the flag alone must not reveal the link to an ordinary employee."""
		frappe.conf.pop("alvoraa_control_plane", None)
		ctx = self._ctx()
		self.assertTrue(ctx.get("is_system_manager"), "Administrator should be one")
		self.assertFalse(ctx.get("is_control_plane"))
