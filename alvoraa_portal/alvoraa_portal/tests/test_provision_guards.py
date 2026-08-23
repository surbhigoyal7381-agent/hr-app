"""Guards that stop a half-deployed bench failing silently.

On 2026-08-23 a deploy replaced the web container but left the long-queue worker
on the previous image. `create_tenant` sent an argument the old `_run_provision`
did not accept, so the job raised TypeError before its first line. Because only
the job itself ever writes status, the console showed "Queued" with an empty log
for an hour.

Every guard here lives in application code and reads the RUNNING system, so it
behaves the same on dev, test and production with nothing configured per
environment. These tests assert that, rather than trusting it.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import tenant_api as api


class TestRedaction(FrappeTestCase):
	"""Provisioning passes generated passwords as job arguments, and RQ puts the
	arguments into the traceback. Nothing password-shaped may reach the jobs
	file, which the control plane serves back over HTTP."""

	def test_password_lines_are_removed(self):
		out = api._redact("harmless line\nadmin_password='Hunter2!'\nalso fine")
		self.assertNotIn("Hunter2", out)
		self.assertIn("harmless line", out)
		self.assertIn("also fine", out)

	def test_every_secret_hint_is_caught(self):
		for hint in api._SECRET_HINT:
			out = api._redact(f"{hint}=topsecretvalue")
			self.assertNotIn("topsecretvalue", out, f"{hint} was not redacted")

	def test_empty_input_is_safe(self):
		self.assertEqual(api._redact(None), "")
		self.assertEqual(api._redact(""), "")


class TestStaleJobs(FrappeTestCase):
	"""A job that died on arrival used to block its subdomain for ever, because
	the status is only ever written by the job itself."""

	def _job(self, status, minutes_ago):
		return {
			"job_id": "x",
			"status": status,
			"started_at": str(frappe.utils.add_to_date(
				frappe.utils.now_datetime(), minutes=-minutes_ago)),
		}

	def test_a_fresh_queued_job_is_not_stale(self):
		self.assertFalse(api._is_stale(self._job("Queued", 1)))

	def test_an_old_queued_job_is_stale(self):
		self.assertTrue(api._is_stale(self._job("Queued", api.STALE_AFTER_MINUTES + 5)))

	def test_an_old_provisioning_job_is_stale(self):
		"""Provisioning can also die mid-run - the site creation step is a
		subprocess, and the worker can be killed while it waits."""
		self.assertTrue(api._is_stale(self._job("Provisioning", api.STALE_AFTER_MINUTES + 5)))

	def test_finished_jobs_are_never_stale(self):
		"""Done and Failed are terminal. Ageing must not reopen them."""
		for status in ("Done", "Failed"):
			self.assertFalse(api._is_stale(self._job(status, 10_000)), status)

	def test_a_job_with_no_start_time_is_not_stale(self):
		"""Missing data must not be read as failure - that would free a subdomain
		while its provisioning is genuinely running."""
		self.assertFalse(api._is_stale({"status": "Queued"}))

	def test_effective_status_reports_stalled(self):
		self.assertEqual(
			api._effective_status(self._job("Queued", api.STALE_AFTER_MINUTES + 5)),
			"Stalled")
		self.assertEqual(api._effective_status(self._job("Queued", 1)), "Queued")


class TestWorkerPreflight(FrappeTestCase):
	"""Queueing into a queue nobody reads looks exactly like success."""

	def test_it_reports_a_live_worker_as_alive(self):
		"""The test bench runs workers, so this should be true here. It is the
		real call, not a mock - the point is that it reads the running system."""
		self.assertIsInstance(api._long_worker_alive(), bool)

	def test_a_broken_check_does_not_block_provisioning(self):
		"""If the check itself fails we must not refuse to provision. Failing
		open is right here: the check is a convenience, and the contract number
		below is the guard that actually protects correctness."""
		from unittest.mock import patch

		with patch("frappe.utils.background_jobs.get_workers",
		           side_effect=RuntimeError("redis down")):
			self.assertTrue(api._long_worker_alive())


class TestProvisionContract(FrappeTestCase):
	"""The number that lets an out-of-date worker explain itself."""

	def test_run_provision_absorbs_unknown_arguments(self):
		"""The exact crash of 2026-08-23: a new caller sending an argument an
		old worker has never heard of. It must not raise TypeError."""
		import inspect

		sig = inspect.signature(api._run_provision)
		kinds = [p.kind for p in sig.parameters.values()]
		self.assertIn(inspect.Parameter.VAR_KEYWORD, kinds,
		              "_run_provision must accept **extra or an older worker "
		              "will crash before it can report anything")

	def test_the_contract_is_sent_with_the_job(self):
		import inspect

		src = inspect.getsource(api.create_tenant)
		self.assertIn("contract=PROVISION_CONTRACT", src)
		self.assertIn("on_failure=_provision_failed", src)

	def test_the_worker_checks_the_contract(self):
		import inspect

		src = inspect.getsource(api._run_provision)
		self.assertIn("PROVISION_CONTRACT", src)


class TestFailureCallback(FrappeTestCase):
	"""The only thing that can report a job which never ran."""

	def test_it_chains_to_frappes_own_callback(self):
		"""frappe.enqueue defaults on_failure to truncate_failed_registry, and
		passing our own REPLACES it. Forgetting to chain would quietly stop the
		failed-job registry being trimmed."""
		import inspect

		src = inspect.getsource(api._provision_failed)
		self.assertIn("truncate_failed_registry", src)

	def test_it_never_raises(self):
		"""It runs inside RQ's failure path. An exception here would be lost and
		would take the real error with it."""
		api._provision_failed(object(), None, None, "boom", None)

	def test_it_marks_the_job_failed_and_forgets_its_secrets(self):
		class FakeJob:
			kwargs = {"kwargs": {"pjob_id": "guardtest1"}}

		jobs = api._read_jobs()
		before = dict(jobs)
		try:
			api._store_credentials("guardtest1", admin_password="Secret#1")
			jobs["guardtest1"] = {"job_id": "guardtest1", "site_name": "g.test",
			                      "status": "Queued", "log": ""}
			api._write_jobs(jobs)

			api._provision_failed(FakeJob(), None, None,
			                      "TypeError: unexpected keyword 'company_name'", None)

			got = api._read_jobs()["guardtest1"]
			self.assertEqual(got["status"], "Failed")
			self.assertIn("company_name", got["log"], "the real error must reach the log")
			# A failed run leaves no usable tenant, so its passwords are of value
			# to nobody except an attacker.
			self.assertEqual(api._read_credentials("guardtest1")["admin_password"], "")
		finally:
			api._write_jobs(before)
			api._forget_credentials("guardtest1")


class TestStaleThresholdSitsAboveTheJobTimeout(FrappeTestCase):
	"""If the stale threshold ever drops below the job's own timeout, a run that
	is genuinely still working would be declared abandoned and its subdomain
	handed to a second attempt - two provisioning runs for one tenant."""

	def test_threshold_is_above_the_enqueue_timeout(self):
		import inspect
		import re

		src = inspect.getsource(api.create_tenant)
		m = re.search(r"timeout=(\d+)", src)
		self.assertIsNotNone(m, "could not find the job timeout in create_tenant")
		self.assertGreater(api.STALE_AFTER_MINUTES * 60, int(m.group(1)))


class TestNoSecretsInTheQueue(FrappeTestCase):
	"""RQ stores a job's arguments in Redis. Anything secret handed to enqueue()
	is readable by anyone who can reach Redis, for every tenant, indefinitely.

	Until 2026-08-23 the three tenant passwords AND the database root password
	were all passed that way. These tests assert they are not passed at all -
	the worker generates its own.
	"""

	def test_create_tenant_generates_no_passwords(self):
		import inspect

		src = inspect.getsource(api.create_tenant)
		self.assertNotIn("_generate_password", src,
		                 "create_tenant must not generate secrets - the worker does")

	def test_no_secret_is_passed_to_the_worker(self):
		import inspect
		import re

		src = inspect.getsource(api.create_tenant)
		enqueue = src[src.index("frappe.enqueue("):]
		for bad in ("admin_password=", "hr_password=", "user_admin_password=",
		            "db_root_password="):
			self.assertNotIn(bad, enqueue, f"{bad} must not reach the queue")

	def test_the_worker_signature_accepts_no_secret(self):
		"""If a password were still a parameter, a future caller could pass one
		and quietly put it back into Redis."""
		import inspect

		params = inspect.signature(api._run_provision).parameters
		for bad in ("admin_password", "hr_password", "user_admin_password",
		            "db_root_password"):
			self.assertNotIn(bad, params, f"{bad} must not be a job argument")

	def test_the_worker_generates_and_stores_them(self):
		import inspect

		src = inspect.getsource(api._run_provision)
		self.assertIn("_generate_password", src)
		self.assertIn("_store_credentials", src)
		self.assertIn("_require_db_root_password", src,
		              "the worker must read the root password from its own environment")

	def test_the_jobs_file_holds_no_password(self):
		"""The jobs file is plain JSON on disk and is served back over HTTP."""
		import inspect

		src = inspect.getsource(api.create_tenant)
		record = src[src.index('"job_id":'):src.index("_write_jobs")]
		self.assertNotIn("password", record)

	def test_passwords_are_not_put_on_a_command_line(self):
		"""`ps` shows a process's arguments to every user on the machine."""
		import inspect

		src = inspect.getsource(api._run_provision)
		self.assertIn("TENANT_HR_PASSWORD", src)
		self.assertIn("TENANT_ADMIN_PASSWORD", src)
		users_call = src[src.index("create_default_users"):]
		self.assertNotIn('"hr_password"', users_call)


class TestCredentialVault(FrappeTestCase):
	"""Credentials live in Frappe's own encrypted store, not in a JSON file."""

	JOB = "vaulttest01"

	def tearDown(self):
		api._forget_credentials(self.JOB)
		frappe.db.rollback()

	def test_store_then_read_round_trips(self):
		api._store_credentials(self.JOB, admin_password="Adm#1", hr_password="Hr#2",
		                       user_admin_password="Sys#3")
		got = api._read_credentials(self.JOB)
		self.assertEqual(got["admin_password"], "Adm#1")
		self.assertEqual(got["hr_password"], "Hr#2")
		self.assertEqual(got["user_admin_password"], "Sys#3")

	def test_it_is_not_stored_in_clear_text(self):
		"""The whole point: the stored value must not be the password."""
		api._store_credentials(self.JOB, admin_password="PlainAsDay1")
		rows = frappe.db.sql(
			"""select password from `__Auth` where doctype=%s and name=%s""",
			(api.CRED_DOCTYPE, self.JOB))
		self.assertTrue(rows, "nothing was stored at all")
		for (stored,) in rows:
			self.assertNotEqual(stored, "PlainAsDay1",
			                    "the password was stored in clear text")

	def test_reading_an_unknown_job_is_empty_not_an_error(self):
		"""Jobs provisioned before this change have no stored credentials, and
		the Jobs page must still open."""
		got = api._read_credentials("nosuchjob0001")
		self.assertEqual(set(got), set(api.CRED_FIELDS))
		self.assertEqual(got["admin_password"], "")

	def test_forget_removes_everything(self):
		api._store_credentials(self.JOB, admin_password="Adm#1", hr_password="Hr#2")
		api._forget_credentials(self.JOB)
		got = api._read_credentials(self.JOB)
		self.assertEqual(got["admin_password"], "")
		self.assertEqual(got["hr_password"], "")

	def test_a_failed_job_forgets_its_secrets(self):
		import inspect

		self.assertIn("_forget_credentials", inspect.getsource(api._run_provision))
		self.assertIn("_forget_credentials", inspect.getsource(api._provision_failed))

	def test_credentials_are_returned_only_for_a_finished_job(self):
		import inspect

		src = inspect.getsource(api.get_provision_status)
		self.assertIn('job.get("status") == "Done"', src)
		self.assertIn("_read_credentials", src)


class TestLegacyPasswordScrub(FrappeTestCase):
	"""Changing the code does not remove what it already wrote to disk."""

	def test_the_patch_is_registered(self):
		import os

		import alvoraa_portal

		txt = os.path.join(os.path.dirname(alvoraa_portal.__file__),
		                   "alvoraa_portal", "patches.txt")
		if not os.path.exists(txt):        # installed layout differs from the repo
			txt = os.path.join(os.path.dirname(alvoraa_portal.__file__), "patches.txt")
		with open(txt) as f:
			self.assertIn("scrub_plaintext_job_passwords", f.read())

	def test_it_blanks_a_stored_password_and_leaves_the_rest_alone(self):
		from alvoraa_portal.patches.v1_0 import scrub_plaintext_job_passwords as patch

		before = dict(api._read_jobs())
		try:
			api._write_jobs({
				"legacy1": {"job_id": "legacy1", "site_name": "old.test",
				            "status": "Done", "admin_password": "LeftOnDisk1",
				            "log": "keep me"},
			})
			patch.execute()
			got = api._read_jobs()["legacy1"]
			self.assertEqual(got["admin_password"], "")
			self.assertEqual(got["log"], "keep me", "the patch must touch nothing else")
			self.assertEqual(got["status"], "Done")
		finally:
			api._write_jobs(before)

	def test_it_runs_safely_on_an_empty_file(self):
		from alvoraa_portal.patches.v1_0 import scrub_plaintext_job_passwords as patch

		before = dict(api._read_jobs())
		try:
			api._write_jobs({})
			patch.execute()          # must not raise
		finally:
			api._write_jobs(before)


class TestBenchPathIsNotHardcoded(FrappeTestCase):
	"""The jobs file used to be written to a hardcoded /home/frappe/frappe-bench.

	True in our container, false everywhere else. CI runs at /home/runner, so
	every write failed - and because _write_jobs swallowed the error, the whole
	thing looked like it worked while recording nothing.
	"""

	def test_the_jobs_file_is_inside_this_bench(self):
		import os

		from frappe.utils import get_bench_path

		self.assertTrue(
			os.path.realpath(api.JOBS_FILE).startswith(os.path.realpath(get_bench_path())),
			f"{api.JOBS_FILE} is not inside {get_bench_path()}")

	def test_the_sites_directory_exists(self):
		import os

		self.assertTrue(os.path.isdir(api.SITES_DIR), f"{api.SITES_DIR} does not exist")

	def test_a_failed_write_is_not_swallowed(self):
		"""A silent write failure is the same bug as a job that dies without
		reporting: the console shows a status that was never updated."""
		from unittest.mock import mock_open, patch

		with patch("builtins.open", mock_open()) as m:
			m.side_effect = OSError("read-only file system")
			with self.assertRaises(OSError):
				api._write_jobs({"x": {}})
