"""Slice 166/167 - Frappe Helpdesk (frappe/helpdesk) sold as `helpdesk`.

Same shape as test_lms_feature_166 - no setup-wizard hook, so provisioning may
install it, and its Telephony dependency, directly.

Every test is database-free except TestHelpdeskDefaults, which mocks frappe
rather than touching a real site. The ones that read deploy/ files skip when
the checkout is not present.

Fail-without-fix: remove the registry entry and Helpdesk stays in the blocked
modules for every tenant. Remove helpdesk_defaults and a newly-sold tenant's
customer portal ships with `allow_anyone_to_create_tickets` unverified.
"""
import inspect
import os
import re
import unittest
from unittest.mock import MagicMock, patch

from alvoraa_portal import helpdesk_defaults
from alvoraa_portal import subscription as sub
from alvoraa_portal import tenant_api as api

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
	os.path.dirname(os.path.abspath(__file__)))))

BASE = ["hrms", "portal", "leaves", "attendance", "expenses", "hr_setup"]
THEIRS = ["Helpdesk"]
HELPDESK_TAG = "v1.30.1"
TELEPHONY_COMMIT = "039cf39f"


class _Result:
	def __init__(self, returncode=0, stdout="", stderr=""):
		self.returncode = returncode
		self.stdout = stdout
		self.stderr = stderr


# ── The registry ─────────────────────────────────────────────────────────────

class TestTheFeatureIsSellable(unittest.TestCase):
	def test_it_exists_in_the_erpnext_catalogue_not_the_hr_one(self):
		self.assertIn("helpdesk", sub.ERPNEXT_FEATURES)
		self.assertNotIn("helpdesk", sub.FEATURES,
			"FEATURES is the HR product and `enterprise` is defined as all of it")

	def test_it_is_labelled_in_plain_words(self):
		self.assertEqual(sub.ERPNEXT_FEATURES["helpdesk"]["label"], "Customer Helpdesk")

	def test_it_declares_its_app_so_it_installs_only_where_sold(self):
		self.assertEqual(sub.ERPNEXT_FEATURES["helpdesk"]["app"], "helpdesk")

	def test_it_claims_its_one_module(self):
		self.assertEqual(sub.ERPNEXT_FEATURES["helpdesk"]["module_defs"], THEIRS)

	def test_it_has_no_roles_of_its_own(self):
		"""Helpdesk defines its own Agent/Agent Manager roles inside the app
		rather than reusing an ERPNext one, so there is nothing shared to
		withhold from a tenant that never bought it."""
		self.assertFalse(sub.ERPNEXT_FEATURES["helpdesk"].get("roles"))

	def test_it_needs_no_erpnext_module(self):
		"""A resold support desk, not an internal HR tool - works on an HR-only
		tenant the same way WhatsApp does."""
		self.assertFalse(sub.ERPNEXT_FEATURES["helpdesk"].get("requires"))
		self.assertFalse(sub.unmet_requirements([*BASE, "helpdesk"]))

	def test_it_is_in_no_standard_plan(self):
		for plan, keys in sub.PLANS.items():
			self.assertNotIn("helpdesk", keys, plan)

	def test_it_is_neither_required_nor_default_on(self):
		spec = sub.ERPNEXT_FEATURES["helpdesk"]
		self.assertFalse(spec.get("required"))
		self.assertNotIn("helpdesk", sub.DEFAULT_ON)

	def test_the_console_catalogue_offers_it_once(self):
		cat = sub.get_plan_catalogue()
		ids = [f["id"] for f in cat["features"]]
		self.assertEqual(ids.count("helpdesk"), 1)
		row = next(f for f in cat["features"] if f["id"] == "helpdesk")
		self.assertTrue(row["erpnext"])
		self.assertFalse(row["required"])


class TestEnterpriseIsStillTheWholeHrProduct(unittest.TestCase):
	def test_enterprise_equals_everything_default_on(self):
		self.assertEqual(set(sub.plan_features("enterprise")), set(sub.DEFAULT_ON))
		self.assertNotIn("helpdesk", sub.plan_features("enterprise"))


# ── Access ───────────────────────────────────────────────────────────────────

class TestModuleAccess(unittest.TestCase):
	def _present(self):
		return set(THEIRS) | {"FCRM", "HR", "Payroll", "Selling", "CRM", "Core", "Desk", "Setup"}

	def test_its_module_is_blocked_when_not_sold(self):
		blocked = set(sub.blocked_module_defs(BASE, existing=self._present()))
		self.assertIn("Helpdesk", blocked)

	def test_buying_it_unblocks_exactly_its_module(self):
		sold = set(sub.blocked_module_defs([*BASE, "helpdesk"], existing=self._present()))
		self.assertNotIn("Helpdesk", sold)
		unsold = set(sub.blocked_module_defs(BASE, existing=self._present()))
		self.assertEqual(unsold - sold, set(THEIRS),
			"the feature frees its own module and nothing else")

	def test_it_does_not_open_the_crm(self):
		sold = set(sub.blocked_module_defs([*BASE, "helpdesk"], existing=self._present()))
		self.assertIn("FCRM", sold, "Helpdesk alone must not unlock Frappe CRM")

	def test_hr_staff_see_it_too_when_sold(self):
		rows = [type("Row", (), {"name": m})() for m in sorted(self._present())]
		with patch.object(sub.frappe, "get_all", return_value=rows):
			blocked = set(sub.blocked_module_defs_for_hr([*BASE, "helpdesk"]))
		self.assertNotIn("Helpdesk", blocked)


# ── Provisioning ─────────────────────────────────────────────────────────────

class TestProvisioningScriptInstallsItWhenSold(unittest.TestCase):
	def setUp(self):
		self.path = os.path.join(REPO, "deploy", "provision_tenant.sh")
		if not os.path.exists(self.path):
			self.skipTest("provision_tenant.sh not in this checkout")
		self.script = open(self.path, encoding="utf-8").read()

	def test_it_is_installed_inside_the_feature_check(self):
		m = re.search(r'if has_feature helpdesk; then(.*?)\nfi', self.script, re.S)
		self.assertIsNotNone(m, "has_feature helpdesk block missing")
		self.assertIn("install-app telephony", m.group(1))
		self.assertIn("install-app helpdesk", m.group(1))
		self.assertIn("helpdesk_defaults.apply_safe_defaults", m.group(1))

	def test_it_is_not_installed_unconditionally(self):
		lines = [ln for ln in self.script.splitlines()
		         if re.match(r'^\s*bench\b.*install-app helpdesk\b', ln)]
		self.assertEqual(len(lines), 1)
		self.assertTrue(lines[0].startswith("    "), "must sit inside the if block")

	def test_telephony_installs_before_helpdesk(self):
		m = re.search(r'if has_feature helpdesk; then(.*?)\nfi', self.script, re.S)
		body = m.group(1)
		self.assertLess(body.index("install-app telephony"), body.index("install-app helpdesk"))

	def test_defaults_are_applied_after_the_install(self):
		m = re.search(r'if has_feature helpdesk; then(.*?)\nfi', self.script, re.S)
		body = m.group(1)
		self.assertLess(body.index("install-app helpdesk"), body.index("helpdesk_defaults"))


class TestPlanChangeInstallsIt(unittest.TestCase):
	def test_the_job_accepts_the_flag_and_defaults_off(self):
		sig = inspect.signature(api._run_install_modules)
		self.assertIn("install_helpdesk", sig.parameters)
		self.assertIs(sig.parameters["install_helpdesk"].default, False)

	def test_update_tenant_queues_it_when_ticked_and_absent(self):
		src = inspect.getsource(api.update_tenant)
		self.assertIn('"helpdesk" in modules and "helpdesk" not in installed', src)
		self.assertIn("install_helpdesk=needs_helpdesk", src)

	def _job(self, install_helpdesk=True, fail_at=None):
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
			api._run_install_modules("j1", "acme.alvoraa.co", install_helpdesk=install_helpdesk)
		return jobs["j1"], seen

	def test_installs_telephony_then_helpdesk_then_applies_defaults(self):
		job, cmds = self._job()
		self.assertEqual(job["status"], "Done")
		self.assertTrue(any("install-app telephony" in c for c in cmds))
		self.assertTrue(any("install-app helpdesk" in c for c in cmds))
		self.assertTrue(any("helpdesk_defaults.apply_safe_defaults" in c for c in cmds))
		i_tel = next(i for i, c in enumerate(cmds) if "install-app telephony" in c)
		i_hd = next(i for i, c in enumerate(cmds) if "install-app helpdesk" in c)
		i_def = next(i for i, c in enumerate(cmds) if "helpdesk_defaults.apply_safe_defaults" in c)
		self.assertLess(i_tel, i_hd)
		self.assertLess(i_hd, i_def)

	def test_a_failed_telephony_install_fails_the_job_and_skips_helpdesk(self):
		job, cmds = self._job(fail_at="install-app telephony")
		self.assertEqual(job["status"], "Failed")
		self.assertIn("telephony install failed", job["log"])
		self.assertFalse(any("install-app helpdesk" in c for c in cmds))

	def test_a_failed_helpdesk_install_fails_the_job_visibly(self):
		job, cmds = self._job(fail_at="install-app helpdesk")
		self.assertEqual(job["status"], "Failed")
		self.assertIn("helpdesk install failed", job["log"])

	def test_not_ticked_means_not_touched(self):
		job, cmds = self._job(install_helpdesk=False)
		self.assertEqual(job["status"], "Done")
		self.assertFalse(any("helpdesk" in c for c in cmds))


# ── The image ────────────────────────────────────────────────────────────────

class TestTheImageCarriesItPinned(unittest.TestCase):
	def setUp(self):
		self.dockerfile = os.path.join(REPO, "deploy", "Dockerfile")
		if not os.path.exists(self.dockerfile):
			self.skipTest("deploy/Dockerfile not in this checkout")
		self.df = open(self.dockerfile, encoding="utf-8").read()

	def test_helpdesk_is_pinned_to_the_release_tag(self):
		"""By tag, not commit - unlike telephony, it has a real release history."""
		self.assertIn(f"ARG HELPDESK_TAG={HELPDESK_TAG}", self.df)
		self.assertIn('bench get-app --branch "${HELPDESK_TAG}" https://github.com/frappe/helpdesk', self.df)

	def test_telephony_is_pinned_to_a_commit_from_a_build_arg(self):
		"""By commit, not branch - it has never had a tagged release."""
		self.assertIn(f"ARG TELEPHONY_COMMIT={TELEPHONY_COMMIT}", self.df)
		self.assertIn("github.com/frappe/telephony", self.df)
		self.assertIn('git -C apps/telephony checkout --quiet "${TELEPHONY_COMMIT}"', self.df)

	def test_telephony_comes_before_helpdesk(self):
		tel = self.df.index("bench get-app --branch develop https://github.com/frappe/telephony")
		hd = self.df.index('bench get-app --branch "${HELPDESK_TAG}" https://github.com/frappe/helpdesk')
		self.assertLess(tel, hd)
		self.assertLess(hd, self.df.index("COPY --chown=frappe:frappe hrms"))

	def test_apps_txt_lists_both(self):
		m = re.search(r"printf '([^']*)' > sites/apps.txt", self.df)
		self.assertIsNotNone(m)
		names = m.group(1).split("\\n")
		self.assertIn("telephony", names)
		self.assertIn("helpdesk", names)
		self.assertLess(names.index("telephony"), names.index("helpdesk"))

	def test_its_assets_are_built_in_the_image_with_the_yarn_cache_mount(self):
		self.assertIn(
			'RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 '
			'bench build --production --app helpdesk', self.df)


# ── Privacy defaults ─────────────────────────────────────────────────────────

class TestHelpdeskDefaults(unittest.TestCase):
	"""Database-free: mocks frappe rather than touching a real site."""

	def _run(self, helpdesk_installed=True, already_applied=False):
		saved = {}

		def fake_exists(kind, name=None):
			if kind == "DocType" and name == "HD Settings":
				return helpdesk_installed
			return False

		doc = MagicMock()
		fake_db = MagicMock()
		with patch.object(helpdesk_defaults.frappe, "db", new=fake_db), \
				patch.object(helpdesk_defaults.frappe, "get_single", return_value=doc) as fake_single:
			fake_db.exists.side_effect = fake_exists
			fake_db.get_default.return_value = "1" if already_applied else None
			fake_db.set_default.side_effect = lambda k, v: saved.update({k: v})
			helpdesk_defaults.apply_safe_defaults()
		return doc, fake_db, fake_single, saved

	def test_not_installed_is_a_no_op(self):
		doc, fake_db, fake_single, saved = self._run(helpdesk_installed=False)
		fake_single.assert_not_called()

	def test_already_applied_is_a_no_op(self):
		doc, fake_db, fake_single, saved = self._run(already_applied=True)
		fake_single.assert_not_called()

	def test_first_run_writes_the_safe_value_and_the_sentinel(self):
		doc, fake_db, fake_single, saved = self._run()
		doc.set.assert_any_call("allow_anyone_to_create_tickets", 0)
		doc.save.assert_called_once_with(ignore_permissions=True)
		self.assertEqual(saved.get(helpdesk_defaults.SENTINEL), "1")

	def test_the_after_migrate_hook_is_registered(self):
		hooks_path = os.path.join(REPO, "alvoraa_portal", "alvoraa_portal", "hooks.py")
		if not os.path.exists(hooks_path):
			self.skipTest("hooks.py not in this checkout")
		src = open(hooks_path, encoding="utf-8").read()
		self.assertIn("alvoraa_portal.helpdesk_defaults.after_migrate", src)
