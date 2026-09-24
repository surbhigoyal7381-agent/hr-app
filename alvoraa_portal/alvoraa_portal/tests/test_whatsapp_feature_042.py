"""Slice 042 - Frappe WhatsApp (shridarpatil/frappe_whatsapp) sold as `whatsapp`.

The same shape as test_crm_feature_040, minus the wizard guard: this app seeds
nothing on install, so provisioning may install it directly.

Every test is database-free. The ones that read deploy/ files skip when the
checkout is not present (the bench container mounts only the app folders).

Fail-without-fix: remove the registry entry and `Frappe Whatsapp` stays in the
blocked modules for every tenant, which is exactly what would hide the app the
day it is sold.
"""
import inspect
import os
import re
import unittest
from unittest.mock import patch

from alvoraa_portal import subscription as sub
from alvoraa_portal import tenant_api as api

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
	os.path.dirname(os.path.abspath(__file__)))))

BASE = ["hrms", "portal", "leaves", "attendance", "expenses", "hr_setup"]
THEIRS = ["Frappe Whatsapp"]
PIN = "08bc1f6af2e3"


class _Result:
	def __init__(self, returncode=0, stdout="", stderr=""):
		self.returncode = returncode
		self.stdout = stdout
		self.stderr = stderr


# ── The registry ─────────────────────────────────────────────────────────────

class TestTheFeatureIsSellable(unittest.TestCase):
	def test_it_exists_in_the_erpnext_catalogue_not_the_hr_one(self):
		self.assertIn("whatsapp", sub.ERPNEXT_FEATURES)
		self.assertNotIn("whatsapp", sub.FEATURES,
			"FEATURES is the HR product and `enterprise` is defined as all of it")

	def test_it_is_labelled_whatsapp(self):
		self.assertEqual(sub.ERPNEXT_FEATURES["whatsapp"]["label"], "WhatsApp")

	def test_it_declares_its_app_so_it_installs_only_where_sold(self):
		self.assertEqual(sub.ERPNEXT_FEATURES["whatsapp"]["app"], "frappe_whatsapp")

	def test_it_claims_its_one_module(self):
		self.assertEqual(sub.ERPNEXT_FEATURES["whatsapp"]["module_defs"], THEIRS)

	def test_it_has_no_roles_of_its_own(self):
		"""Every doctype in the app is System Manager only. A `roles` list here
		would withhold roles from tenants that never bought it."""
		self.assertFalse(sub.ERPNEXT_FEATURES["whatsapp"].get("roles"))

	def test_it_needs_no_erpnext_module(self):
		self.assertFalse(sub.ERPNEXT_FEATURES["whatsapp"].get("requires"))
		self.assertFalse(sub.unmet_requirements([*BASE, "whatsapp"]),
			"nothing is refused when WhatsApp is ticked on an HR-only tenant")

	def test_it_is_in_no_standard_plan(self):
		"""Unselected for every existing tenant: nothing ticks it on its own."""
		for plan, keys in sub.PLANS.items():
			self.assertNotIn("whatsapp", keys, plan)

	def test_it_is_neither_required_nor_default_on(self):
		spec = sub.ERPNEXT_FEATURES["whatsapp"]
		self.assertFalse(spec.get("required"))
		self.assertNotIn("whatsapp", sub.DEFAULT_ON)

	def test_the_console_catalogue_offers_it_once(self):
		cat = sub.get_plan_catalogue()
		ids = [f["id"] for f in cat["features"]]
		self.assertEqual(ids.count("whatsapp"), 1)
		row = next(f for f in cat["features"] if f["id"] == "whatsapp")
		self.assertTrue(row["erpnext"])
		self.assertFalse(row["required"])


class TestEnterpriseIsStillTheWholeHrProduct(unittest.TestCase):
	def test_enterprise_equals_everything_default_on(self):
		self.assertEqual(set(sub.plan_features("enterprise")), set(sub.DEFAULT_ON))

	def test_custom_equals_enterprise_on_the_hr_side(self):
		self.assertEqual(set(sub.plan_features("custom")), set(sub.plan_features("enterprise")))


# ── Access ───────────────────────────────────────────────────────────────────

class TestModuleAccess(unittest.TestCase):
	def _present(self):
		return set(THEIRS) | {"FCRM", "HR", "Payroll", "Selling", "CRM", "Core", "Desk", "Setup"}

	def test_its_module_is_blocked_when_not_sold(self):
		blocked = set(sub.blocked_module_defs(BASE, existing=self._present()))
		self.assertIn("Frappe Whatsapp", blocked)

	def test_buying_it_unblocks_exactly_its_module(self):
		sold = set(sub.blocked_module_defs([*BASE, "whatsapp"], existing=self._present()))
		self.assertNotIn("Frappe Whatsapp", sold)
		unsold = set(sub.blocked_module_defs(BASE, existing=self._present()))
		self.assertEqual(unsold - sold, set(THEIRS),
			"the feature frees its own module and nothing else")

	def test_it_does_not_open_the_crm(self):
		sold = set(sub.blocked_module_defs([*BASE, "whatsapp"], existing=self._present()))
		self.assertIn("FCRM", sold, "WhatsApp alone must not unlock Frappe CRM")

	def test_hr_staff_see_it_too_when_sold(self):
		rows = [type("Row", (), {"name": m})() for m in sorted(self._present())]
		with patch.object(sub.frappe, "get_all", return_value=rows):
			blocked = set(sub.blocked_module_defs_for_hr([*BASE, "whatsapp"]))
		self.assertNotIn("Frappe Whatsapp", blocked)


# ── Provisioning ─────────────────────────────────────────────────────────────

class TestProvisioningScriptInstallsItWhenSold(unittest.TestCase):
	"""No setup-wizard hook in this app, so the script may install it directly,
	the way it installs india_compliance."""

	def setUp(self):
		self.path = os.path.join(REPO, "deploy", "provision_tenant.sh")
		if not os.path.exists(self.path):
			self.skipTest("provision_tenant.sh not in this checkout")
		self.script = open(self.path, encoding="utf-8").read()

	def test_it_is_installed_inside_the_feature_check(self):
		m = re.search(r'if has_feature whatsapp; then(.*?)\nfi', self.script, re.S)
		self.assertIsNotNone(m, "has_feature whatsapp block missing")
		self.assertIn('install-app frappe_whatsapp', m.group(1))

	def test_it_is_not_installed_unconditionally(self):
		lines = [ln for ln in self.script.splitlines()
		         if re.match(r'^\s*bench\b.*install-app frappe_whatsapp', ln)]
		self.assertEqual(len(lines), 1)
		self.assertTrue(lines[0].startswith("    "), "must sit inside the if block")


class TestPlanChangeInstallsIt(unittest.TestCase):
	def test_the_job_accepts_the_flag_and_defaults_off(self):
		sig = inspect.signature(api._run_install_modules)
		self.assertIn("install_whatsapp", sig.parameters)
		self.assertIs(sig.parameters["install_whatsapp"].default, False)

	def test_update_tenant_queues_it_when_ticked_and_absent(self):
		src = inspect.getsource(api.update_tenant)
		self.assertIn('"whatsapp" in modules and "frappe_whatsapp" not in installed', src)
		self.assertIn("install_whatsapp=needs_whatsapp", src)

	def _job(self, install_whatsapp=True, fail=False):
		jobs = {"j1": {"job_id": "j1", "status": "Provisioning", "log": ""}}
		seen = []

		def fake(cmd, timeout=30, env=None):
			seen.append(cmd)
			if "install-app frappe_whatsapp" in cmd and fail:
				return _Result(1, "", "boom")
			return _Result(0, "ok")
		with patch.object(api, "_bench_run", side_effect=fake), \
				patch.object(api, "_read_jobs", side_effect=lambda: jobs), \
				patch.object(api, "_write_jobs", side_effect=lambda j: jobs.update(j)), \
				patch.object(api, "now_datetime", return_value="2026-09-24 12:00:00"):
			api._run_install_modules("j1", "acme.alvoraa.co", install_whatsapp=install_whatsapp)
		return jobs["j1"], [c for c in seen if "install-app frappe_whatsapp" in c]

	def test_installs_without_any_wizard_check(self):
		job, installs = self._job()
		self.assertEqual(job["status"], "Done")
		self.assertEqual(len(installs), 1)
		self.assertNotIn("is_setup_complete", " ".join(installs))

	def test_a_failed_install_fails_the_job_visibly(self):
		job, installs = self._job(fail=True)
		self.assertEqual(job["status"], "Failed")
		self.assertIn("frappe_whatsapp install failed", job["log"])

	def test_not_ticked_means_not_touched(self):
		job, installs = self._job(install_whatsapp=False)
		self.assertEqual(job["status"], "Done")
		self.assertEqual(installs, [])


# ── The image and the proxy ──────────────────────────────────────────────────

class TestTheImageCarriesItPinned(unittest.TestCase):
	def setUp(self):
		self.dockerfile = os.path.join(REPO, "deploy", "Dockerfile")
		self.workflow = os.path.join(REPO, ".github", "workflows", "build-image.yml")
		if not os.path.exists(self.dockerfile):
			self.skipTest("deploy/Dockerfile not in this checkout")
		self.df = open(self.dockerfile, encoding="utf-8").read()

	def test_the_app_is_pinned_to_a_commit_from_a_build_arg(self):
		"""By commit, not tag: multi-account exists only on master."""
		self.assertIn(f"ARG WHATSAPP_COMMIT={PIN}", self.df)
		self.assertIn("github.com/shridarpatil/frappe_whatsapp", self.df)
		self.assertIn('git -C apps/frappe_whatsapp checkout --quiet "${WHATSAPP_COMMIT}"', self.df)

	def test_it_comes_after_the_crm_and_before_the_first_party_apps(self):
		crm = self.df.index("bench get-app --branch \"${CRM_TAG}\"")
		wa = self.df.index("bench get-app --branch master https://github.com/shridarpatil/frappe_whatsapp")
		self.assertLess(crm, wa)
		self.assertLess(wa, self.df.index("COPY --chown=frappe:frappe hrms"))

	def test_apps_txt_lists_it(self):
		m = re.search(r"printf '([^']*)' > sites/apps.txt", self.df)
		self.assertIsNotNone(m)
		self.assertIn("frappe_whatsapp", m.group(1).split("\\n"))

	def test_its_assets_are_built_in_the_image(self):
		"""It has app_include_js, so the desk needs its bundle."""
		self.assertIn("RUN bench build --production --app frappe_whatsapp", self.df)

	def test_ci_passes_the_same_pin(self):
		if not os.path.exists(self.workflow):
			self.skipTest("build-image.yml not in this checkout")
		self.assertIn(f"WHATSAPP_COMMIT={PIN}", open(self.workflow, encoding="utf-8").read())


class TestTheWebhookIsRateLimited(unittest.TestCase):
	"""SEC-1: the app's webhook is public and unsigned, so nginx limits it."""

	def setUp(self):
		self.path = os.path.join(REPO, "deploy", "nginx.conf")
		if not os.path.exists(self.path):
			self.skipTest("deploy/nginx.conf not in this checkout")
		self.conf = open(self.path, encoding="utf-8").read()

	def test_a_zone_exists(self):
		self.assertRegex(self.conf, r"limit_req_zone \$binary_remote_addr zone=alvoraa_webhook:10m rate=\d+r/m;")

	def test_both_server_blocks_limit_the_webhook_path(self):
		blocks = re.findall(
			r"location ~ \^/api/method/frappe_whatsapp\\\.utils\\\.webhook\\\.webhook\$ \{(.*?)\n    \}",
			self.conf, re.S)
		self.assertEqual(len(blocks), 2, "one per server block (production and dev)")
		for b in blocks:
			self.assertIn("limit_req zone=alvoraa_webhook", b)
			self.assertIn("client_max_body_size 1m", b)
			self.assertIn("proxy_pass          http://frappe_http", b)
			self.assertIn("X-Content-Type-Options", b, "headers repeated per location (OPS-45)")
