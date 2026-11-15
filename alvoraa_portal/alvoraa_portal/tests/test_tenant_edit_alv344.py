"""ALV-344 - changing a big tenant's modules timed out, and the app was never installed.

`update_tenant` ran `module_access.sync_site` inside the request under a 30 s
limit. On a 407-user tenant it takes about 153 s, so the request failed with a
500 after the plan was written and before the app install was queued. Now the
request never runs the sync: it is queued, and when apps are installed the
install job runs it after the installs.

No database and no site, the same shape as test_console_edit_logo_031:
`_bench_run` and `frappe.enqueue` are replaced.

    env/bin/python -m unittest alvoraa_portal.tests.test_tenant_edit_alv344
"""

import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import frappe

from alvoraa_portal import tenant_api as api
from alvoraa_portal.tests.test_console_edit_logo_031 import _Result, _throw_without_a_site

TENANT = "acme.test"
SYNC = "module_access.sync_site"


class _Fixture(unittest.TestCase):
	def setUp(self):
		self._tmp = tempfile.TemporaryDirectory()
		os.makedirs(os.path.join(self._tmp.name, TENANT))
		for p in (patch.object(api, "SITES_DIR", self._tmp.name),
		          patch.object(api, "_require_admin"),
		          patch.object(api, "_read_site_config", return_value={}),
		          patch.object(api, "_read_jobs", return_value={}),
		          patch.object(api, "_write_jobs")):
			p.start()
			self.addCleanup(p.stop)
		_throw_without_a_site(self)
		self.addCleanup(self._tmp.cleanup)

	def save(self, modules, installed):
		"""Press Save in Edit Tenant. Returns (result, bench commands, enqueue calls)."""
		with patch.object(api, "_bench_run", return_value=_Result()) as bench, \
				patch.object(api, "_get_installed_apps", return_value=installed), \
				patch.object(frappe, "enqueue") as enqueue:
			out = api.update_tenant(TENANT, tenant_name="Acme", modules=modules)
		return out, [c.args[0] for c in bench.call_args_list], enqueue.call_args_list


class TestTheSaveNeverWaitsForTheSync(_Fixture):

	def test_adding_crm_queues_the_install_with_the_sync_and_never_syncs_inline(self):
		out, cmds, queued = self.save(["crm"], installed=["frappe", "hrms"])
		self.assertFalse([c for c in cmds if SYNC in c], "no sync inside the request")
		self.assertEqual(out["status"], "installing")
		self.assertEqual(len(queued), 1)
		self.assertEqual(queued[0].args[0], "alvoraa_portal.tenant_api._run_install_modules")
		self.assertTrue(queued[0].kwargs["install_crm"])
		self.assertTrue(queued[0].kwargs["sync_access"], "the install job rebuilds the menus after")

	def test_a_change_with_nothing_to_install_queues_the_sync_alone(self):
		out, cmds, queued = self.save(["crm"], installed=["frappe", "hrms", "crm"])
		self.assertFalse([c for c in cmds if SYNC in c])
		self.assertEqual(out["status"], "ok")
		self.assertEqual([q.args[0] for q in queued], ["alvoraa_portal.tenant_api._sync_access"])

	def test_a_save_without_modules_queues_nothing(self):
		with patch.object(api, "_bench_run", return_value=_Result()), \
				patch.object(frappe, "enqueue") as enqueue:
			api.update_tenant(TENANT, tenant_name="Acme")
		self.assertEqual(enqueue.call_args_list, [])


class TestTheBackgroundSync(_Fixture):

	def test_a_slow_sync_is_logged_not_raised(self):
		with patch.object(api, "_bench_run", side_effect=subprocess.TimeoutExpired("bench", 900)), \
				patch.object(frappe, "log_error") as log:
			line = api._sync_access(TENANT)
		self.assertIn("NOT updated", line)
		self.assertTrue(log.called)

	def test_it_gets_far_more_than_thirty_seconds(self):
		with patch.object(api, "_bench_run", return_value=_Result()) as bench:
			line = api._sync_access(TENANT)
		self.assertIn("Menus updated", line)
		self.assertGreaterEqual(bench.call_args.kwargs["timeout"], 600)

	def test_the_install_job_syncs_after_the_install_even_when_it_fails(self):
		order = []

		def run(cmd, *a, **kw):
			order.append(cmd)
			return _Result(returncode=1 if "install-app telephony" in cmd else 0)

		with patch.object(api, "_bench_run", side_effect=run), \
				patch.object(frappe, "log_error"):
			api._run_install_modules("j1", TENANT, install_helpdesk=True, sync_access=True)
		installs = [i for i, c in enumerate(order) if "install-app" in c]
		syncs = [i for i, c in enumerate(order) if SYNC in c]
		self.assertEqual(len(syncs), 1)
		self.assertGreater(syncs[0], installs[-1])


class TestThePageSaysWhatHappened(unittest.TestCase):

	def test_an_empty_server_error_still_gets_words(self):
		page = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
		                    "www", "alvoraa-admin.html")
		with open(page, encoding="utf-8") as f:
			self.assertIn("The server stopped with error", f.read())


if __name__ == "__main__":
	unittest.main()
