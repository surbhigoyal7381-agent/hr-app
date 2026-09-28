"""Slice 166/167 - Frappe LMS (frappe/lms) sold as `lms`.

Same shape as test_crm_feature_040 and test_whatsapp_feature_042, minus the
wizard guard (LMS seeds nothing on install, so provisioning may install it
directly, straight after its Payments dependency).

Every test is database-free except TestLmsDefaults, which mocks frappe rather
than touching a real site. The ones that read deploy/ files skip when the
checkout is not present (the bench container mounts only the app folders).

Fail-without-fix: remove the registry entry and LMS stays in the blocked
modules for every tenant, which is exactly what would hide the app the day it
is sold. Remove lms_defaults and a newly-sold tenant's course catalogue and
public sign-up ship open on day one.
"""
import inspect
import os
import re
import unittest
from unittest.mock import MagicMock, patch

from alvoraa_portal import lms_defaults
from alvoraa_portal import subscription as sub
from alvoraa_portal import tenant_api as api

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
	os.path.dirname(os.path.abspath(__file__)))))

BASE = ["hrms", "portal", "leaves", "attendance", "expenses", "hr_setup"]
THEIRS = ["LMS", "Job"]
LMS_COMMIT = "87168fc7"
PAYMENTS_COMMIT = "cca07d9f"


class _Result:
	def __init__(self, returncode=0, stdout="", stderr=""):
		self.returncode = returncode
		self.stdout = stdout
		self.stderr = stderr


# ── The registry ─────────────────────────────────────────────────────────────

class TestTheFeatureIsSellable(unittest.TestCase):
	def test_it_exists_in_the_erpnext_catalogue_not_the_hr_one(self):
		self.assertIn("lms", sub.ERPNEXT_FEATURES)
		self.assertNotIn("lms", sub.FEATURES,
			"FEATURES is the HR product and `enterprise` is defined as all of it")

	def test_it_is_labelled_in_plain_words(self):
		self.assertEqual(sub.ERPNEXT_FEATURES["lms"]["label"], "Learning & Certification")

	def test_it_declares_its_app_so_it_installs_only_where_sold(self):
		self.assertEqual(sub.ERPNEXT_FEATURES["lms"]["app"], "lms")

	def test_it_claims_its_one_module(self):
		self.assertEqual(sub.ERPNEXT_FEATURES["lms"]["module_defs"], THEIRS)

	def test_it_has_no_roles_of_its_own(self):
		self.assertFalse(sub.ERPNEXT_FEATURES["lms"].get("roles"))

	def test_it_requires_hr_setup(self):
		"""hr_setup is required on every plan, so this never actually blocks a
		real tenant - it exists so a bare custom plan cannot tick LMS with no
		HR underneath it (internal-training-only decision, 28 Sep 2026)."""
		self.assertEqual(sub.ERPNEXT_FEATURES["lms"]["requires"], ["hr_setup"])
		self.assertTrue(sub.FEATURES["hr_setup"].get("required"))
		self.assertFalse(sub.unmet_requirements([*BASE, "lms"]),
			"hr_setup is on every plan, so ticking lms never leaves it unmet")

	def test_it_is_in_no_standard_plan(self):
		for plan, keys in sub.PLANS.items():
			self.assertNotIn("lms", keys, plan)

	def test_it_is_neither_required_nor_default_on(self):
		spec = sub.ERPNEXT_FEATURES["lms"]
		self.assertFalse(spec.get("required"))
		self.assertNotIn("lms", sub.DEFAULT_ON)

	def test_the_console_catalogue_offers_it_once(self):
		cat = sub.get_plan_catalogue()
		ids = [f["id"] for f in cat["features"]]
		self.assertEqual(ids.count("lms"), 1)
		row = next(f for f in cat["features"] if f["id"] == "lms")
		self.assertTrue(row["erpnext"])
		self.assertFalse(row["required"])


class TestEnterpriseIsStillTheWholeHrProduct(unittest.TestCase):
	def test_enterprise_equals_everything_default_on(self):
		self.assertEqual(set(sub.plan_features("enterprise")), set(sub.DEFAULT_ON))
		self.assertNotIn("lms", sub.plan_features("enterprise"))


# ── Access ───────────────────────────────────────────────────────────────────

class TestModuleAccess(unittest.TestCase):
	def _present(self):
		return set(THEIRS) | {"FCRM", "HR", "Payroll", "Selling", "CRM", "Core", "Desk", "Setup"}

	def test_its_module_is_blocked_when_not_sold(self):
		blocked = set(sub.blocked_module_defs(BASE, existing=self._present()))
		self.assertIn("LMS", blocked)

	def test_buying_it_unblocks_exactly_its_module(self):
		sold = set(sub.blocked_module_defs([*BASE, "lms"], existing=self._present()))
		self.assertNotIn("LMS", sold)
		unsold = set(sub.blocked_module_defs(BASE, existing=self._present()))
		self.assertEqual(unsold - sold, set(THEIRS),
			"the feature frees its own module and nothing else")

	def test_hr_staff_see_it_too_when_sold(self):
		rows = [type("Row", (), {"name": m})() for m in sorted(self._present())]
		with patch.object(sub.frappe, "get_all", return_value=rows):
			blocked = set(sub.blocked_module_defs_for_hr([*BASE, "lms"]))
		self.assertNotIn("LMS", blocked)


# ── Provisioning ─────────────────────────────────────────────────────────────

class TestProvisioningScriptInstallsItWhenSold(unittest.TestCase):
	"""No setup-wizard hook in this app, so the script may install it - and its
	Payments dependency - directly, the way it installs india_compliance."""

	def setUp(self):
		self.path = os.path.join(REPO, "deploy", "provision_tenant.sh")
		if not os.path.exists(self.path):
			self.skipTest("provision_tenant.sh not in this checkout")
		self.script = open(self.path, encoding="utf-8").read()

	def test_it_is_installed_inside_the_feature_check(self):
		m = re.search(r'if has_feature lms; then(.*?)\nfi', self.script, re.S)
		self.assertIsNotNone(m, "has_feature lms block missing")
		self.assertIn("install-app payments", m.group(1))
		self.assertIn("install-app lms", m.group(1))
		self.assertIn("lms_defaults.apply_safe_defaults", m.group(1))

	def test_it_is_not_installed_unconditionally(self):
		lines = [ln for ln in self.script.splitlines()
		         if re.match(r'^\s*bench\b.*install-app lms\b', ln)]
		self.assertEqual(len(lines), 1)
		self.assertTrue(lines[0].startswith("    "), "must sit inside the if block")

	def test_payments_installs_before_lms(self):
		m = re.search(r'if has_feature lms; then(.*?)\nfi', self.script, re.S)
		body = m.group(1)
		self.assertLess(body.index("install-app payments"), body.index("install-app lms"))

	def test_defaults_are_applied_after_the_install(self):
		m = re.search(r'if has_feature lms; then(.*?)\nfi', self.script, re.S)
		body = m.group(1)
		self.assertLess(body.index("install-app lms"), body.index("lms_defaults"))


class TestPlanChangeInstallsIt(unittest.TestCase):
	def test_the_job_accepts_the_flag_and_defaults_off(self):
		sig = inspect.signature(api._run_install_modules)
		self.assertIn("install_lms", sig.parameters)
		self.assertIs(sig.parameters["install_lms"].default, False)

	def test_update_tenant_queues_it_when_ticked_and_absent(self):
		src = inspect.getsource(api.update_tenant)
		self.assertIn('"lms" in modules and "lms" not in installed', src)
		self.assertIn("install_lms=needs_lms", src)

	def _job(self, install_lms=True, fail_at=None):
		jobs = {"j1": {"job_id": "j1", "status": "Provisioning", "log": ""}}
		seen = []

		def fake(cmd, timeout=30, env=None):
			seen.append(cmd)
			if fail_at and fail_at in cmd:
				return _Result(1, "", "boom")
			return _Result(0, "ok")
		with patch.object(api, "_bench_run", side_effect=fake), \
				patch.object(api, "_read_jobs", side_effect=lambda: jobs), \
				patch.object(api, "_write_jobs", side_effect=lambda j: jobs.update(j)), \
				patch.object(api, "now_datetime", return_value="2026-09-28 12:00:00"):
			api._run_install_modules("j1", "acme.alvoraa.co", install_lms=install_lms)
		return jobs["j1"], seen

	def test_installs_payments_then_lms_then_applies_defaults(self):
		job, cmds = self._job()
		self.assertEqual(job["status"], "Done")
		lms_cmds = [c for c in cmds if "lms" in c]
		self.assertTrue(any("install-app payments" in c for c in cmds))
		self.assertTrue(any("install-app lms" in c for c in lms_cmds))
		self.assertTrue(any("lms_defaults.apply_safe_defaults" in c for c in lms_cmds))
		# payments before lms before defaults
		i_pay = next(i for i, c in enumerate(cmds) if "install-app payments" in c)
		i_lms = next(i for i, c in enumerate(cmds) if "install-app lms" in c)
		i_def = next(i for i, c in enumerate(cmds) if "lms_defaults.apply_safe_defaults" in c)
		self.assertLess(i_pay, i_lms)
		self.assertLess(i_lms, i_def)

	def test_a_failed_payments_install_fails_the_job_and_skips_lms(self):
		job, cmds = self._job(fail_at="install-app payments")
		self.assertEqual(job["status"], "Failed")
		self.assertIn("payments install failed", job["log"])
		self.assertFalse(any("install-app lms" in c for c in cmds))

	def test_a_failed_lms_install_fails_the_job_visibly(self):
		job, cmds = self._job(fail_at="install-app lms")
		self.assertEqual(job["status"], "Failed")
		self.assertIn("lms install failed", job["log"])

	def test_not_ticked_means_not_touched(self):
		job, cmds = self._job(install_lms=False)
		self.assertEqual(job["status"], "Done")
		self.assertFalse(any("lms" in c for c in cmds))


# ── The image ────────────────────────────────────────────────────────────────

class TestTheImageCarriesItPinned(unittest.TestCase):
	def setUp(self):
		self.dockerfile = os.path.join(REPO, "deploy", "Dockerfile")
		if not os.path.exists(self.dockerfile):
			self.skipTest("deploy/Dockerfile not in this checkout")
		self.df = open(self.dockerfile, encoding="utf-8").read()

	def test_lms_is_pinned_to_a_commit_from_a_build_arg(self):
		self.assertIn(f"ARG LMS_COMMIT={LMS_COMMIT}", self.df)
		self.assertIn("github.com/frappe/lms", self.df)
		self.assertIn('git -C apps/lms checkout --quiet "${LMS_COMMIT}"', self.df)

	def test_payments_is_pinned_to_a_commit_from_a_build_arg(self):
		self.assertIn(f"ARG PAYMENTS_COMMIT={PAYMENTS_COMMIT}", self.df)
		self.assertIn("github.com/frappe/payments", self.df)
		self.assertIn('git -C apps/payments checkout --quiet "${PAYMENTS_COMMIT}"', self.df)

	def test_payments_comes_before_lms(self):
		pay = self.df.index("bench get-app --branch version-16 https://github.com/frappe/payments")
		lms = self.df.index("bench get-app --branch version-16 https://github.com/frappe/lms")
		self.assertLess(pay, lms)
		self.assertLess(lms, self.df.index("COPY --chown=frappe:frappe hrms"))

	def test_apps_txt_lists_both(self):
		m = re.search(r"printf '([^']*)' > sites/apps.txt", self.df)
		self.assertIsNotNone(m)
		names = m.group(1).split("\\n")
		self.assertIn("payments", names)
		self.assertIn("lms", names)
		self.assertLess(names.index("payments"), names.index("lms"))

	def test_its_assets_are_built_in_the_image_with_the_yarn_cache_mount(self):
		self.assertIn(
			'RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 '
			'bench build --production --app lms', self.df)

	def test_no_git_submodule_update_for_frappe_ui(self):
		"""P1 from the DevOps first look: both apps vendor an empty frappe-ui
		submodule that neither app's Vite build reads (proven on a throwaway
		build, 01e-test-build-results.md). No fix should ever be added here."""
		self.assertNotIn("git submodule update", self.df)


# ── Privacy defaults ─────────────────────────────────────────────────────────

class TestLmsDefaults(unittest.TestCase):
	"""Database-free: mocks frappe rather than touching a real site."""

	def _run(self, lms_installed=True, already_applied=False):
		saved = {}

		def fake_exists(kind, name=None):
			if kind == "DocType" and name == "LMS Settings":
				return lms_installed
			return False

		doc = MagicMock()
		with patch.object(lms_defaults.frappe, "db") as fake_db, \
				patch.object(lms_defaults.frappe, "get_single", return_value=doc) as fake_single:
			fake_db.exists.side_effect = fake_exists
			fake_db.get_default.return_value = "1" if already_applied else None
			fake_db.set_default.side_effect = lambda k, v: saved.update({k: v})
			lms_defaults.apply_safe_defaults()
		return doc, fake_db, fake_single, saved

	def test_not_installed_is_a_no_op(self):
		doc, fake_db, fake_single, saved = self._run(lms_installed=False)
		fake_single.assert_not_called()

	def test_already_applied_is_a_no_op(self):
		doc, fake_db, fake_single, saved = self._run(already_applied=True)
		fake_single.assert_not_called()

	def test_first_run_writes_the_safe_values_and_the_sentinel(self):
		doc, fake_db, fake_single, saved = self._run()
		doc.set.assert_any_call("allow_guest_access", 0)
		doc.set.assert_any_call("disable_signup", 1)
		doc.set.assert_any_call("allow_job_posting", 0)
		doc.save.assert_called_once_with(ignore_permissions=True)
		self.assertEqual(saved.get(lms_defaults.SENTINEL), "1")

	def test_the_after_migrate_hook_is_registered(self):
		hooks_path = os.path.join(REPO, "alvoraa_portal", "alvoraa_portal", "hooks.py")
		if not os.path.exists(hooks_path):
			self.skipTest("hooks.py not in this checkout")
		src = open(hooks_path, encoding="utf-8").read()
		self.assertIn("alvoraa_portal.lms_defaults.after_migrate", src)
