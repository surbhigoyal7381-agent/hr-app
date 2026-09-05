"""Waves 5 and 6 - the app that is never installed, and the portal's own panels.

Wave 5 is the only REAL denial in the whole scheme. Hiding a module, hiding a
workspace and denying a permission all act on something that exists. An app that
was never installed has no doctypes at all, so there is nothing to reach by any
URL, role or API call.

Wave 6 is the opposite end: the portal is the interface most staff actually use,
and it ignored the plan entirely. subscription.has_feature() had existed since
wave 1 and nothing called it.
"""

import io
import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import hr_api
from alvoraa_portal import subscription as sub


def _script():
	"""provision_tenant.sh, wherever this bench keeps it."""
	import alvoraa_portal

	repo = os.path.dirname(os.path.dirname(os.path.dirname(
		os.path.abspath(alvoraa_portal.__file__))))
	for cand in (os.path.join(repo, "deploy", "provision_tenant.sh"),
	             "/workspace/provision_tenant.sh"):
		if os.path.exists(cand):
			return io.open(cand, encoding="utf-8").read()
	return None


class TestWave5ConditionalInstall(FrappeTestCase):
	"""alvoraa_goals is installed only when Goals was sold."""

	def setUp(self):
		self.src = _script()
		if self.src is None:
			self.skipTest("provision_tenant.sh is not on this bench")

	def test_goals_is_installed_conditionally(self):
		m = re.search(r"if has_feature goals; then(.*?)fi", self.src, re.S)
		self.assertIsNotNone(m, "alvoraa_goals must be behind a feature check")
		self.assertIn("install-app alvoraa_goals", m.group(1))

	def test_erpnext_and_hrms_are_never_conditional(self):
		"""Frappe HR links to Bank Account, Journal Entry, Supplier, Project and
		Delivery Trip. Removing ERPNext breaks payroll and expenses on EVERY
		plan, so it is installed always and gated by visibility instead."""
		for app in ("erpnext", "hrms", "alvoraa_portal"):
			line = f'bench --site "$SITE_NAME" install-app {app}'
			self.assertIn(line, self.src)
			after = self.src[self.src.index(line):]
			self.assertNotIn("has_feature", after[:len(line)])

	def test_the_registry_agrees_that_goals_is_an_app(self):
		self.assertEqual(sub.FEATURES["goals"].get("app"), "alvoraa_goals")

	def test_required_apps_matches_what_the_script_does(self):
		"""If these disagree, the script installs something the registry says is
		not sold, or misses something it says is."""
		self.assertNotIn("alvoraa_goals", sub.required_apps(sub.plan_features("starter")))
		self.assertIn("alvoraa_goals", sub.required_apps(sub.plan_features("enterprise")))

	def test_a_manual_run_still_installs_everything(self):
		"""has_feature() returns true when no feature list was passed, so running
		the script by hand behaves as it always did."""
		self.assertIn('[ -z "$FEATURES" ] && return 0', self.src)

	def test_the_plan_to_modules_case_statement_is_gone(self):
		"""It was a FIFTH copy of the plan definition, agreeing with none of the
		other four. modules_enabled is derived from what was sold now."""
		self.assertNotIn('MODULES=\'["hrms","vendor_portal","goals"]\'', self.src)
		self.assertIn("$FEATURES", self.src)

	def test_a_downgrade_must_not_uninstall(self):
		"""bench uninstall-app DROPS TABLES. A downgrade hides; it never deletes
		a customer's data."""
		self.assertNotIn("uninstall-app", self.src)


class TestWave6PortalEntitlement(FrappeTestCase):
	"""The portal now knows what the tenant bought."""

	def setUp(self):
		frappe.set_user("Administrator")
		self._saved = frappe.conf.get("features")
		try:
			frappe.cache().delete_value("portal_features_global")
		except Exception:
			pass

	def tearDown(self):
		if self._saved is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = self._saved
		try:
			frappe.cache().delete_value("portal_features_global")
		except Exception:
			pass

	def _features(self, plan):
		frappe.conf["features"] = sub.plan_features(plan)
		try:
			frappe.cache().delete_value("portal_features_global")
		except Exception:
			pass
		return hr_api.get_available_features()

	def test_it_reports_entitlement_for_every_feature(self):
		f = self._features("starter")
		for key in sub.FEATURES:
			self.assertIn(f"plan_{key}", f, f"{key} has no entitlement flag")

	def test_starter_is_not_entitled_to_analytics_or_goals(self):
		f = self._features("starter")
		self.assertFalse(f["plan_analytics"])
		self.assertFalse(f["plan_goals"])
		self.assertFalse(f["plan_payroll"])

	def test_enterprise_is_entitled_to_everything(self):
		f = self._features("enterprise")
		for key in sub.FEATURES:
			self.assertTrue(f[f"plan_{key}"], key)

	def test_required_features_are_always_entitled(self):
		f = self._features("starter")
		for key in sub.REQUIRED:
			self.assertTrue(f[f"plan_{key}"], key)

	def test_goals_needs_the_app_AND_the_plan(self):
		"""A site that keeps alvoraa_goals after a downgrade must stop showing
		the panel. The server ANDs the two rather than trusting either alone."""
		self.assertFalse(self._features("starter")["goals"])

	def test_entitlement_failure_never_blacks_out_the_portal(self):
		"""The desk gates are the boundary. This only decides what to draw, so a
		failure here must not leave someone staring at an empty app."""
		from unittest.mock import patch

		with patch("alvoraa_portal.subscription.has_feature",
		           side_effect=RuntimeError("boom")):
			f = hr_api.get_available_features()
		self.assertIsInstance(f, dict)
		self.assertIn("shift_request", f, "the rest of the payload must survive")


class TestWave6IsWiredIntoTheUi(FrappeTestCase):
	"""The payload is useless if the page ignores it."""

	def setUp(self):
		import alvoraa_portal

		page = os.path.join(os.path.dirname(os.path.abspath(alvoraa_portal.__file__)),
		                    "www", "hrms-employee.html")
		if not os.path.exists(page):
			self.skipTest("portal page not found on this bench")
		self.html = io.open(page, encoding="utf-8-sig").read()

	def test_analytics_needs_role_and_plan(self):
		"""It used to be `ctx.is_hr` alone, so every tenant got the panel."""
		self.assertIn("plan_analytics", self.html)
		self.assertIn("ctx.is_hr && anaSold", self.html)

	def test_an_unknown_flag_does_not_hide_the_panel(self):
		"""Absent is not the same as false. An older cached payload with no
		entitlement key must not black out Analytics for an HR user."""
		self.assertIn("_f.plan_analytics !== false", self.html)
