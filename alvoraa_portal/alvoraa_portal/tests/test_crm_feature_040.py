"""Slice 040 - Frappe CRM is in the image, sellable, and installed only after the wizard.

The app is `frappe/crm`, pinned to tag v1.84.0: the standalone CRM (leads, deals,
email, telephony), not ERPNext's classic Lead/Opportunity module.

Three facts about our own code drive every test here, all read from source on
2026-09-23:

  * Access control denies by default. A module no feature claims is blocked for
    every user but the tenant admin, and the CRM's own page check
    (crm.api.check_app_permission) refuses anyone whose blocked modules include
    `FCRM`. So without a registry entry the CRM is dark for everybody on the day
    it is installed - even on a tenant that bought it.
  * The CRM's `setup_wizard_complete` hook (crm.demo.api.create_demo_data)
    seeds three fake @example.com System Users with Sales roles and fake leads,
    on any site where the app is present when the wizard finishes. Sargam's
    wizard is already complete; a NEW tenant's is not until tenant_api runs
    complete_company_setup - which happens AFTER provision_tenant.sh. So the
    install has to come after that step, on both install paths.
  * `enterprise` is defined as every Alvoraa HR feature, and a test enforces it.
    A non-HR feature therefore lives in ERPNEXT_FEATURES, as india_compliance does.

These tests need NO database and NO site: plain unittest.TestCase, `_bench_run`
replaced the way test_provision_guards.py and test_tenant_logo_029.py do it.
They also run under `bench run-tests`.

Fail-without-fix: delete the `crm` entry from ERPNEXT_FEATURES and
TestModuleAccess.test_buying_it_unblocks_exactly_its_two_modules fails with
FCRM still blocked - which is the lockout the entry exists to prevent.
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

# A Starter-shaped selection, as the india_compliance tests use it.
BASE = ["hrms", "portal", "leaves", "attendance", "expenses", "hr_setup"]
THEIRS = ["FCRM", "Lead Syncing"]


class _Result:
	"""What `_bench_run` returns: only `returncode`, `stdout` and `stderr` are read."""

	def __init__(self, returncode=0, stdout="", stderr=""):
		self.returncode = returncode
		self.stdout = stdout
		self.stderr = stderr


# ── The registry ─────────────────────────────────────────────────────────────

class TestTheFeatureIsSellable(unittest.TestCase):
	def test_it_exists_in_the_erpnext_catalogue_not_the_hr_one(self):
		self.assertIn("crm", sub.ERPNEXT_FEATURES)
		self.assertNotIn("crm", sub.FEATURES,
			"FEATURES is the HR product, and `enterprise` is defined as all of it")

	def test_it_is_labelled_frappe_crm(self):
		spec = sub.feature_spec("crm")
		self.assertEqual(spec["label"], "Frappe CRM")
		self.assertEqual(spec["desc"], "Leads, deals, tenders, email — the standalone CRM")
		self.assertTrue(spec.get("erpnext"), "rendered in the ERPNext group of the console")

	def test_it_declares_its_app_so_it_installs_only_where_sold(self):
		"""`app` is what required_apps() and both install paths key off."""
		self.assertEqual(sub.feature_spec("crm")["app"], "crm")
		self.assertIn("crm", sub.required_apps([*BASE, "crm"]))
		self.assertNotIn("crm", sub.required_apps(BASE))

	def test_it_claims_both_of_its_modules(self):
		"""39 doctypes live in FCRM and 5 in Lead Syncing. A module the registry
		does not name is denied by default."""
		self.assertEqual(set(sub.feature_spec("crm")["module_defs"]), set(THEIRS))

	def test_it_has_no_roles_of_its_own(self):
		"""It reuses ERPNext's Sales User and Sales Manager. Withholding those
		from tenants without the CRM would break ERPNext Selling for them - the
		real gate for this app is "not installed"."""
		self.assertFalse(sub.feature_spec("crm").get("roles"))
		for feats in (BASE, [*BASE, "crm"], [*BASE, "erp_selling"]):
			withheld = sub.withheld_roles(feats)
			self.assertNotIn("Sales User", withheld, feats)
			self.assertNotIn("Sales Manager", withheld, feats)

	def test_it_needs_no_erpnext_module(self):
		"""Unlike india_compliance it stands alone: its ERPNext link is a
		per-tenant setting, off by default."""
		self.assertIsNone(sub.requirement_error([*BASE, "crm"]))
		self.assertNotIn("crm", sub.unmet_requirements([*BASE, "crm"]))

	def test_it_is_in_no_standard_plan(self):
		"""Like every ERPNext-side feature it is ticked per tenant, which makes
		that tenant `custom`. No bundle hands it out."""
		for plan, feats in sub.PLANS.items():
			self.assertNotIn("crm", feats, f"plan {plan}")
		for plan in ("starter", "business", "enterprise", "custom"):
			self.assertNotIn("crm", sub.plan_features(plan), plan)

	def test_it_is_neither_required_nor_default_on(self):
		self.assertNotIn("crm", sub.REQUIRED)
		self.assertNotIn("crm", sub.DEFAULT_ON)
		self.assertNotIn("crm", sub.enabled_features({}),
			"a site with no config must not get the CRM by fallback")

	def test_a_tenant_that_names_it_has_it(self):
		self.assertTrue(sub.has_feature("crm", {"features": [*BASE, "crm"]}))
		self.assertFalse(sub.has_feature("crm", {"features": BASE}))

	def test_the_price_list_learns_about_it(self):
		"""sync_registry adds a row for every sellable key, so the CRM shows in
		the console as built-and-unpriced - the state that gets noticed."""
		from alvoraa_portal import pricing
		self.assertIn("crm", pricing._sellable_registry_keys())


class TestTheClassicOneIsRelabelled(unittest.TestCase):
	def test_erp_crm_says_which_crm_it_is(self):
		self.assertEqual(sub.ERPNEXT_FEATURES["erp_crm"]["label"], "CRM (classic ERPNext)")

	def test_the_key_did_not_change(self):
		"""Tenants already hold `erp_crm` in their features list. Renaming the
		key would lock them out of what they bought."""
		self.assertIn("erp_crm", sub.ERPNEXT_FEATURES)
		self.assertEqual(sub.ERPNEXT_FEATURES["erp_crm"]["module_defs"], ["CRM"])
		self.assertEqual(sub.erp_feature_id("CRM"), "erp_crm")

	def test_the_two_labels_cannot_be_confused_in_the_console(self):
		labels = {f["id"]: f["label"] for f in sub.get_plan_catalogue()["features"]}
		self.assertEqual(labels["crm"], "Frappe CRM")
		self.assertEqual(labels["erp_crm"], "CRM (classic ERPNext)")
		self.assertNotEqual(labels["crm"], labels["erp_crm"])


class TestEnterpriseIsStillTheWholeHrProduct(unittest.TestCase):
	"""The invariant the placement protects. Extended, not weakened."""

	def test_enterprise_equals_everything_default_on(self):
		self.assertEqual(set(sub.plan_features("enterprise")), set(sub.DEFAULT_ON))

	def test_custom_equals_enterprise_on_the_hr_side(self):
		self.assertEqual(set(sub.plan_features("custom")), set(sub.plan_features("enterprise")))

	def test_the_catalogue_offers_every_feature_once(self):
		cat = sub.get_plan_catalogue()
		ids = [f["id"] for f in cat["features"]]
		self.assertEqual(len(ids), len(set(ids)))
		self.assertEqual(set(ids), set(sub.FEATURES) | set(sub.ERPNEXT_FEATURES))
		erp_ids = {f["id"] for f in cat["features"] if f["erpnext"]}
		self.assertIn("crm", erp_ids)
		self.assertIn("india_compliance", erp_ids)


# ── Module access: what the desk and the CRM's own page check see ───────────

class TestModuleAccess(unittest.TestCase):
	"""`existing` is injected, as the india_compliance tests do, so the rule is
	stated regardless of whether this bench has the CRM installed."""

	def _present(self):
		"""A site that HAS the app, whatever this bench looks like."""
		return set(THEIRS) | {"HR", "Payroll", "Selling", "CRM", "Core", "Desk", "Setup"}

	def test_its_modules_are_blocked_when_not_sold(self):
		blocked = set(sub.blocked_module_defs(BASE, existing=self._present()))
		for m in THEIRS:
			self.assertIn(m, blocked, m)

	def test_buying_it_unblocks_exactly_its_two_modules(self):
		"""This is the lockout test. Remove the registry entry and FCRM stays
		blocked here - which is what crm.api.check_app_permission refuses on."""
		sold = set(sub.blocked_module_defs([*BASE, "crm"], existing=self._present()))
		for m in THEIRS:
			self.assertNotIn(m, sold, f"{m} must be allowed once the CRM is bought")
		unsold = set(sub.blocked_module_defs(BASE, existing=self._present()))
		self.assertEqual(unsold - sold, set(THEIRS),
			"the feature frees its own two modules and nothing else")

	def test_hr_staff_see_it_too_when_sold(self):
		"""The HR variant of the profile blocks the same list minus the desk shell.

		blocked_module_defs_for_hr has no `existing` parameter, so the Module Def
		read is replaced here to keep the test database-free."""
		rows = [type("Row", (), {"name": m})() for m in sorted(self._present())]
		with patch.object(sub.frappe, "get_all", return_value=rows):
			blocked = set(sub.blocked_module_defs_for_hr([*BASE, "crm"]))
		for m in THEIRS:
			self.assertNotIn(m, blocked, m)
		for m in sub.DESK_SHELL:
			self.assertNotIn(m, blocked, "HR staff keep the desk shell")

	def test_the_classic_module_is_separate(self):
		"""Buying Frappe CRM does not open ERPNext's CRM module, and the other
		way round. Two products, two ticks."""
		with_new = set(sub.blocked_module_defs([*BASE, "crm"], existing=self._present()))
		self.assertIn("CRM", with_new)
		with_old = set(sub.blocked_module_defs([*BASE, "erp_crm"], existing=self._present()))
		self.assertIn("FCRM", with_old)
		self.assertNotIn("CRM", with_old)

	def test_wave_4_denies_its_doctypes_until_sold(self):
		"""The real gate: Custom DocPerm deny rows for the CRM doctypes on a
		tenant that has the app but did not buy it, and none once it did."""
		existing = [("CRM Lead", "FCRM"), ("CRM Deal", "FCRM"),
		            ("CRM Lead Sync Source", "Lead Syncing"),
		            ("Lead", "CRM"), ("Leave Application", "HR")]
		module_apps = {"FCRM": "crm", "Lead Syncing": "crm", "CRM": "erpnext", "HR": "hrms"}
		kw = dict(existing=existing, links=[], module_apps=module_apps, workspace_links=[])
		unsold = set(sub.blocked_doctypes(BASE, **kw))
		for d in ("CRM Lead", "CRM Deal", "CRM Lead Sync Source"):
			self.assertIn(d, unsold, d)
		sold = set(sub.blocked_doctypes([*BASE, "crm"], **kw))
		for d in ("CRM Lead", "CRM Deal", "CRM Lead Sync Source"):
			self.assertNotIn(d, sold, d)
		self.assertIn("Lead", sold, "ERPNext's classic Lead is a different purchase")
		self.assertNotIn("Leave Application", sold)


# ── Both install paths wait for the wizard ──────────────────────────────────

class TestProvisioningScriptDoesNotInstallIt(unittest.TestCase):
	"""provision_tenant.sh runs BEFORE tenant_api completes the wizard, so it
	must never be the thing that installs the CRM."""

	def setUp(self):
		self.path = os.path.join(REPO, "deploy", "provision_tenant.sh")
		if not os.path.exists(self.path):
			self.skipTest("provision_tenant.sh not in this checkout")
		self.script = open(self.path, encoding="utf-8").read()

	def test_no_install_command_for_crm(self):
		commands = [ln for ln in self.script.splitlines()
		            if re.match(r'^\s*bench\b.*install-app crm', ln)]
		self.assertEqual(commands, [], "the script must not run install-app crm")

	def test_it_still_knows_the_feature_and_says_what_happens(self):
		"""A manual run prints where the install really happens, instead of
		silently skipping a sold feature."""
		self.assertIn("has_feature crm", self.script)
		self.assertIn("AFTER the setup wizard", self.script)


class TestNewTenantInstallsItAfterTheWizard(unittest.TestCase):
	def test_the_install_comes_after_company_setup_in_the_worker(self):
		src = inspect.getsource(api._run_provision)
		wizard = src.index("tenant_setup.complete_company_setup")
		crm = src.index("_install_crm_after_wizard")
		self.assertGreater(crm, wizard, "the CRM install must follow the wizard")
		# ...and before the plan is applied, so sync_site sees the FCRM Module Def
		# and can leave it unblocked.
		self.assertLess(crm, src.index("module_access.sync_site"))

	def test_it_is_installed_only_when_sold(self):
		src = inspect.getsource(api._run_provision)
		block = src[src.index("_install_crm_after_wizard") - 200:src.index("_install_crm_after_wizard")]
		self.assertIn('"crm" in', block)


class TestTheGuardItself(unittest.TestCase):
	"""_install_crm_after_wizard asks the SITE whether its wizard finished, and
	installs only on a clear yes."""

	def _run(self, wizard_stdout, wizard_rc=0, install_rc=0):
		def fake(cmd, timeout=30, env=None):
			if "frappe.is_setup_complete" in cmd:
				return _Result(wizard_rc, wizard_stdout)
			if "install-app crm" in cmd:
				return _Result(install_rc, "Installing crm...\nInstalled")
			return _Result()
		with patch.object(api, "_bench_run", side_effect=fake) as bench_run:
			ok, msg = api._install_crm_after_wizard("acme.alvoraa.co")
		installs = [c.args[0] for c in bench_run.call_args_list if "install-app crm" in c.args[0]]
		return ok, msg, installs

	def test_wizard_complete_installs(self):
		"""`bench execute` prints its return value as JSON - `true`, lower case.
		Checked on the bench; the first draft of the guard looked for `True` and
		would have refused every install for ever."""
		ok, msg, installs = self._run("true\n")
		self.assertTrue(ok)
		self.assertEqual(len(installs), 1)
		self.assertIn("--site acme.alvoraa.co install-app crm", installs[0])

	def test_the_python_spelling_is_accepted_too(self):
		ok, msg, installs = self._run("Some warning line first\nTrue\n")
		self.assertTrue(ok)
		self.assertEqual(len(installs), 1)

	def test_wizard_incomplete_does_not_install(self):
		ok, msg, installs = self._run("false\n")
		self.assertFalse(ok)
		self.assertEqual(installs, [])
		self.assertIn("NOT installed", msg)
		self.assertIn("install-app crm", msg, "the message says what to run later")

	def test_a_failed_check_counts_as_incomplete(self):
		"""Fail closed: an unreadable answer must not become an install."""
		for stdout, rc in (("", 0), ("true", 1), ("Traceback ...\nnull", 0), ("true\nfalse", 0)):
			ok, msg, installs = self._run(stdout, wizard_rc=rc)
			self.assertFalse(ok, (stdout, rc))
			self.assertEqual(installs, [], (stdout, rc))

	def test_a_failed_install_is_reported_with_both_streams(self):
		def fake(cmd, timeout=30, env=None):
			if "frappe.is_setup_complete" in cmd:
				return _Result(0, "true")
			return _Result(1, "stdout says why", "stderr says why")
		with patch.object(api, "_bench_run", side_effect=fake):
			ok, msg = api._install_crm_after_wizard("acme.alvoraa.co")
		self.assertFalse(ok)
		self.assertIn("stdout says why", msg)
		self.assertIn("stderr says why", msg)


class TestPlanChangeInstallsItThroughTheSameGuard(unittest.TestCase):
	"""update_tenant queues _run_install_modules for a newly ticked CRM; the job
	must go through the wizard guard like a new tenant does."""

	def test_the_job_accepts_the_flag_and_defaults_off(self):
		sig = inspect.signature(api._run_install_modules)
		self.assertIn("install_crm", sig.parameters)
		self.assertIs(sig.parameters["install_crm"].default, False)

	def test_update_tenant_queues_it_when_ticked_and_absent(self):
		src = inspect.getsource(api.update_tenant)
		self.assertIn('"crm" in modules and "crm" not in installed', src)
		self.assertIn("install_crm=needs_crm", src)

	def _job(self, wizard_stdout, install_crm=True):
		jobs = {"j1": {"job_id": "j1", "status": "Provisioning", "log": ""}}
		seen = []

		def fake(cmd, timeout=30, env=None):
			seen.append(cmd)
			if "frappe.is_setup_complete" in cmd:
				return _Result(0, wizard_stdout)
			return _Result(0, "ok")
		with patch.object(api, "_bench_run", side_effect=fake), \
				patch.object(api, "_read_jobs", side_effect=lambda: jobs), \
				patch.object(api, "_write_jobs", side_effect=lambda j: jobs.update(j)), \
				patch.object(api, "now_datetime", return_value="2026-09-23 12:00:00"):
			api._run_install_modules("j1", "acme.alvoraa.co", install_crm=install_crm)
		return jobs["j1"], [c for c in seen if "install-app crm" in c]

	def test_installs_when_the_wizard_is_done(self):
		job, installs = self._job("true")
		self.assertEqual(job["status"], "Done")
		self.assertEqual(len(installs), 1)

	def test_refuses_and_fails_the_job_when_the_wizard_is_not_done(self):
		"""A ticked feature with no app behind it must be visible as a failure,
		not a quiet Done."""
		job, installs = self._job("false")
		self.assertEqual(job["status"], "Failed")
		self.assertEqual(installs, [])
		self.assertIn("NOT installed", job["log"])

	def test_not_ticked_means_not_touched(self):
		job, installs = self._job("true", install_crm=False)
		self.assertEqual(job["status"], "Done")
		self.assertEqual(installs, [])


# ── The image ────────────────────────────────────────────────────────────────

class TestTheImageCarriesItPinned(unittest.TestCase):
	def setUp(self):
		self.dockerfile = os.path.join(REPO, "deploy", "Dockerfile")
		self.workflow = os.path.join(REPO, ".github", "workflows", "build-image.yml")
		if not os.path.exists(self.dockerfile):
			self.skipTest("deploy/Dockerfile not in this checkout")
		self.df = open(self.dockerfile, encoding="utf-8").read()

	def test_the_app_is_fetched_by_tag_from_a_build_arg(self):
		self.assertIn("ARG CRM_TAG=v1.84.0", self.df)
		self.assertIn('bench get-app --branch "${CRM_TAG}" https://github.com/frappe/crm', self.df)

	def test_it_comes_after_erpnext_and_before_the_first_party_apps(self):
		self.assertLess(self.df.index("get-app --branch \"${ERPNEXT_BRANCH}\""),
		                self.df.index("github.com/frappe/crm"))
		self.assertLess(self.df.index("github.com/frappe/crm"),
		                self.df.index("COPY --chown=frappe:frappe hrms"))

	def test_apps_txt_lists_it(self):
		m = re.search(r"printf '([^']*)' > sites/apps.txt", self.df)
		self.assertIsNotNone(m)
		self.assertIn("crm", m.group(1).split("\\n"))

	def test_its_assets_are_built_in_the_image(self):
		"""Baked in, one app at a time, so a failure names the app - and no
		`bench build` on a live container, which would recreate symlinks nginx
		cannot follow."""
		self.assertIn("RUN bench build --production --app crm", self.df)

	def test_ci_passes_the_same_pin(self):
		if not os.path.exists(self.workflow):
			self.skipTest("build-image.yml not in this checkout")
		self.assertIn("CRM_TAG=v1.84.0", open(self.workflow, encoding="utf-8").read())
