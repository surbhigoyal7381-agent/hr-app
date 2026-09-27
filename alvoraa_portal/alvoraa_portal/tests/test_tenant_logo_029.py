"""Slice 029 - a tenant's uploaded logo must reach the tenant's own site.

The admin console uploads the logo to the CONTROL PLANE's public files and
hands provisioning a relative `/files/<name>` path. Frappe keeps public files
per site, so the tenant never had the file and every tenant page showed a
broken image - while the console's own tenant list rendered the same path
against the control plane and looked fine. `_stage_tenant_logo` copies the
file across before the path is stored, and refuses to store a path whose
source does not exist.

These tests need NO database and NO site. They use plain `unittest.TestCase`,
point `SITES_DIR` at a temporary folder, and replace `_bench_run` the way
`test_provision_guards.py` does, so they can run with the bench's Python
alone:

    env/bin/python -m unittest alvoraa_portal.tests.test_tenant_logo_029
"""

import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import frappe

from alvoraa_portal import tenant_api as api

CONTROL = "control.test"
TENANT = "acme.test"
LOGO = "AllAboutHR1.png"


class _Result:
	"""What `_bench_run` returns: only `returncode`, `stdout` and `stderr` are read."""

	def __init__(self, returncode=0, stdout="", stderr=""):
		self.returncode = returncode
		self.stdout = stdout
		self.stderr = stderr


class _LogoFixture(unittest.TestCase):
	"""A temporary sites/ folder with a control site that holds the upload."""

	def setUp(self):
		self._tmp = tempfile.TemporaryDirectory()
		self.sites = self._tmp.name
		self.src_dir = os.path.join(self.sites, CONTROL, "public", "files")
		self.dst_dir = os.path.join(self.sites, TENANT, "public", "files")
		os.makedirs(self.src_dir)
		os.makedirs(os.path.join(self.sites, TENANT))
		self._sites_patch = patch.object(api, "SITES_DIR", self.sites)
		self._sites_patch.start()
		# The helper reads frappe.local.site for the control site when the
		# caller does not pass one; set it without needing frappe.init().
		self._had_site = hasattr(frappe.local, "site")
		self._old_site = getattr(frappe.local, "site", None)
		frappe.local.site = CONTROL

	def tearDown(self):
		self._sites_patch.stop()
		if self._had_site:
			frappe.local.site = self._old_site
		elif hasattr(frappe.local, "site"):
			del frappe.local.site
		self._tmp.cleanup()

	def put_upload(self, name=LOGO, content=b"png-bytes"):
		with open(os.path.join(self.src_dir, name), "wb") as f:
			f.write(content)

	def tenant_copy(self, name=LOGO):
		return os.path.join(self.dst_dir, name)


class TestStageTenantLogo(_LogoFixture):
	"""The helper on its own."""

	def test_relative_path_with_source_present_is_copied_and_kept_relative(self):
		self.put_upload(content=b"real-logo")
		url, warn = api._stage_tenant_logo(TENANT, f"/files/{LOGO}")
		self.assertEqual(url, f"/files/{LOGO}")
		self.assertEqual(warn, "")
		self.assertTrue(os.path.isfile(self.tenant_copy()))
		with open(self.tenant_copy(), "rb") as f:
			self.assertEqual(f.read(), b"real-logo")

	def test_source_missing_is_not_stored_and_warns(self):
		url, warn = api._stage_tenant_logo(TENANT, f"/files/{LOGO}")
		self.assertEqual(url, "")
		self.assertIn("[WARN]", warn)
		self.assertIn(LOGO, warn)
		self.assertFalse(os.path.exists(self.tenant_copy()))

	def test_absolute_url_is_left_alone_and_nothing_is_copied(self):
		# The second address was ".svg" until 2026-09-19, when the user dropped
		# SVG as a logo format. The point of this test is that an absolute URL
		# passes through untouched whatever the case of the scheme, so only the
		# file type changed - the assertions are the same ones 029 wrote.
		for url_in in ("https://cdn.example.com/logo.png", "HTTP://cdn.example.com/x.webp"):
			url, warn = api._stage_tenant_logo(TENANT, url_in)
			self.assertEqual(url, url_in)
			self.assertEqual(warn, "")
		self.assertFalse(os.path.exists(self.dst_dir))

	def test_empty_value_does_nothing(self):
		self.assertEqual(api._stage_tenant_logo(TENANT, ""), ("", ""))
		self.assertEqual(api._stage_tenant_logo(TENANT, None), ("", ""))
		self.assertEqual(api._stage_tenant_logo(TENANT, "   "), ("", ""))

	def test_control_site_can_be_passed_explicitly(self):
		self.put_upload()
		url, warn = api._stage_tenant_logo(TENANT, f"/files/{LOGO}", control_site=CONTROL)
		self.assertEqual(url, f"/files/{LOGO}")
		self.assertTrue(os.path.isfile(self.tenant_copy()))

	def test_unknown_control_site_refuses_rather_than_guessing(self):
		self.put_upload()
		# Delete it for this one test only. tearDown restores whatever was there
		# before setUp, so do NOT touch _had_site: setting it False here told the
		# clean-up there was nothing to put back, and every module that ran after
		# this one in a full suite inherited a frappe.local with no site - 21
		# AttributeErrors in test_usage, which sorts next. (2026-09-20)
		del frappe.local.site
		url, warn = api._stage_tenant_logo(TENANT, f"/files/{LOGO}")
		self.assertEqual(url, "")
		self.assertIn("[WARN]", warn)
		self.assertFalse(os.path.exists(self.tenant_copy()))

	def test_never_follows_a_dotdot_or_absolute_source(self):
		"""A crafted value must not make the copy read outside public/files."""
		# Something real one level up, to prove it is not reached.
		secret = os.path.join(self.sites, CONTROL, "site_config.json")
		with open(secret, "w") as f:
			f.write('{"db_password": "nope"}')
		self.put_upload()
		bad = [
			"/files/../site_config.json",
			"/files/../../control.test/site_config.json",
			"/files/sub/../" + LOGO,
			"/files//etc/passwd",
			"/files/.hidden.png",
			"/files/" + os.sep + LOGO,
			"/etc/passwd",
			"files/" + LOGO,
			"/private/files/" + LOGO,
			"C:/anything/" + LOGO,
			"/files/a\\b.png",
		]
		for value in bad:
			url, warn = api._stage_tenant_logo(TENANT, value)
			self.assertEqual(url, "", value)
			self.assertIn("[WARN]", warn, value)
		self.assertFalse(os.path.exists(self.dst_dir))
		self.assertFalse(os.path.exists(os.path.join(self.sites, TENANT, "site_config.json")))

	def test_copy_is_idempotent(self):
		"""Provisioning can be retried; the second copy must not fail."""
		self.put_upload()
		api._stage_tenant_logo(TENANT, f"/files/{LOGO}")
		url, warn = api._stage_tenant_logo(TENANT, f"/files/{LOGO}")
		self.assertEqual((url, warn), (f"/files/{LOGO}", ""))


def _logo_config_calls(bench_run):
	"""The `set-config tenant_logo_url ...` commands a mocked `_bench_run` saw."""
	return [c.args[0] for c in bench_run.call_args_list
	        if "set-config tenant_logo_url" in c.args[0]]


class TestCreatePath(_LogoFixture):
	"""`_run_provision` - the background job behind create_tenant - end to end,
	with every subprocess and every store replaced, exactly as the guard tests
	do. Nothing here needs a bench."""

	def _run(self, logo_url):
		jobs = {"job1": {"job_id": "job1", "status": "Queued", "log": ""}}
		with patch.object(api, "_bench_run", return_value=_Result()) as bench_run, \
				patch.object(api, "subprocess") as sp, \
				patch.object(api, "_read_jobs", side_effect=lambda: jobs), \
				patch.object(api, "_write_jobs", side_effect=lambda j: jobs.update(j)), \
				patch.object(api, "_store_credentials"), \
				patch.object(api, "_forget_credentials"), \
				patch.object(api, "_require_db_root_password", return_value="x"), \
				patch.object(api, "now_datetime", return_value=datetime(2026, 9, 19, 12, 0)):
			# now_datetime() reads System Settings, which needs a database.
			sp.run.return_value = _Result(0, "provisioned", "")
			sp.TimeoutExpired = Exception
			api._run_provision(
				"job1", TENANT, "Acme", "starter", "hrms",
				"#1a7f5a", logo_url, "help@acme.test", "test",
				hr_email="hr@acme.test", admin_email="admin@acme.test",
			)
		return jobs["job1"], _logo_config_calls(bench_run)

	def test_relative_logo_is_copied_then_written_to_site_config(self):
		self.put_upload()
		job, calls = self._run(f"/files/{LOGO}")
		self.assertEqual(job["status"], "Done", job["log"])
		self.assertTrue(os.path.isfile(self.tenant_copy()))
		self.assertEqual(len(calls), 1)
		self.assertIn(f"--site {TENANT} set-config tenant_logo_url", calls[0])
		self.assertIn(f"/files/{LOGO}", calls[0])
		self.assertNotIn("[WARN] Logo", job["log"])

	def test_missing_source_is_not_written_and_the_job_log_says_so(self):
		job, calls = self._run(f"/files/{LOGO}")
		self.assertEqual(job["status"], "Done", job["log"])
		self.assertEqual(calls, [])
		self.assertIn("[WARN] Logo not applied", job["log"])
		self.assertIn(LOGO, job["log"])

	def test_absolute_url_is_written_untouched(self):
		job, calls = self._run("https://cdn.example.com/acme.png")
		self.assertEqual(len(calls), 1)
		self.assertIn("https://cdn.example.com/acme.png", calls[0])
		self.assertFalse(os.path.exists(self.dst_dir))

	def test_no_logo_writes_nothing(self):
		job, calls = self._run("")
		self.assertEqual(job["status"], "Done", job["log"])
		self.assertEqual(calls, [])


class TestUpdatePath(_LogoFixture):
	"""`update_tenant` with a logo behaves the same as provisioning."""

	def _run(self, logo_url):
		with patch.object(api, "_bench_run", return_value=_Result()) as bench_run, \
				patch.object(api, "_require_admin"):
			out = api.update_tenant(TENANT, tenant_name="Acme", logo_url=logo_url)
		return out, _logo_config_calls(bench_run)

	def test_relative_logo_is_copied_then_written(self):
		self.put_upload()
		out, calls = self._run(f"/files/{LOGO}")
		self.assertEqual(out["status"], "ok")
		self.assertTrue(os.path.isfile(self.tenant_copy()))
		self.assertEqual(len(calls), 1)
		self.assertIn(f"/files/{LOGO}", calls[0])
		self.assertNotIn("[WARN]", out["message"])

	def test_missing_source_is_not_written_and_the_message_says_so(self):
		out, calls = self._run(f"/files/{LOGO}")
		self.assertEqual(out["status"], "ok")
		self.assertEqual(calls, [])
		self.assertIn("[WARN] Logo not applied", out["message"])

	def test_absolute_url_is_written_untouched(self):
		out, calls = self._run("https://cdn.example.com/acme.png")
		self.assertEqual(len(calls), 1)
		self.assertIn("https://cdn.example.com/acme.png", calls[0])

	def test_no_logo_argument_changes_nothing(self):
		"""An edit that is not about the logo must stay a no-op.

		Slice 031 gave the edit modal a logo control, so it CAN send one now.
		What must not change: an edit that does not mention the logo leaves it
		alone.
		"""
		with patch.object(api, "_bench_run", return_value=_Result()) as bench_run, \
				patch.object(api, "_require_admin"):
			out = api.update_tenant(TENANT, tenant_name="Acme")
		self.assertEqual(out["status"], "ok")
		self.assertEqual(_logo_config_calls(bench_run), [])
		self.assertNotIn("[WARN]", out["message"])
