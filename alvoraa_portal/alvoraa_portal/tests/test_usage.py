"""The count is what every invoice multiplies by, so it has to be defensible.

Each test here is a bill that would otherwise be wrong, or a month that would
go unbilled without anybody noticing:

  an employee who left still being charged for
  an intern counted when the contract says interns are free
  a failed measurement leaving no row at all, so the tenant is silently missed
  a re-run creating a second row for the same month
  a tenant site able to change what it reports and so lower its own bill

The billable rule is deliberately plain - Active employees, minus the
employment types this customer does not pay for. One filter on the Employee
list. A cleverer rule nobody can check themselves costs more in support calls
than it earns.
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import pricing, usage


def _clear():
	for dt in ("Alvoraa Usage Record", "Alvoraa Subscription", "Alvoraa Plan",
	           "Alvoraa Operations Pack", "Alvoraa Module Price"):
		for name in frappe.get_all(dt, pluck="name"):
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
	settings = frappe.get_single("Alvoraa Pricing Settings")
	settings.seeded = None
	settings.pack_cap_per_user = 0
	settings.save(ignore_permissions=True)
	frappe.db.commit()


class UsageCase(FrappeTestCase):
	SITE = "acme.alvoraa.co"
	PERIOD = "2026-08"

	def setUp(self):
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf["alvoraa_control_plane"] = 1
		_clear()
		pricing.seed()
		self.customer = self._a_customer()
		frappe.get_doc({
			"doctype": "Alvoraa Subscription", "site_name": self.SITE,
			"status": "Active", "customer": self.customer, "plan": "Starter",
		}).insert(ignore_permissions=True)

	def tearDown(self):
		_clear()
		if self._plane is None:
			frappe.conf.pop("alvoraa_control_plane", None)
		else:
			frappe.conf["alvoraa_control_plane"] = self._plane

	def _a_customer(self, name="Usage Test Customer"):
		if not frappe.db.exists("Customer", name):
			frappe.get_doc({"doctype": "Customer", "customer_name": name}
			               ).insert(ignore_permissions=True)
		return name

	def payload(self, by_status=None, by_type=None, modules=None):
		# `is None`, not `or`: an EMPTY dict is a real answer - a site with no
		# employees at all - and `or` would quietly swap it for the default,
		# which is how a test for an empty site ends up asserting against ten
		# imaginary people.
		if by_status is None:
			by_status = {"Active": 10}
		if by_type is None:
			by_type = {"Full-time": 10}
		return {
			"site": self.SITE,
			"employees": {
				"total": sum(by_status.values()),
				"by_status": by_status,
				"active_by_employment_type": by_type,
			},
			"users_by_module": modules or {},
		}


class TestWhoCounts(UsageCase):
	def test_only_active_employees_are_billed(self):
		out = usage._write_record(
			self.SITE, self.PERIOD,
			self.payload(by_status={"Active": 8, "Left": 40, "Inactive": 5},
			             by_type={"Full-time": 8}), None)
		self.assertTrue(out["ok"])
		self.assertEqual(out["billable_employees"], 8)
		self.assertEqual(out["total_employees"], 53)

	def test_forty_leavers_do_not_cost_anything(self):
		"""The commonest way a bill goes wrong: a site that has been running for
		years has far more records than people."""
		out = usage._write_record(
			self.SITE, self.PERIOD,
			self.payload(by_status={"Active": 12, "Left": 300},
			             by_type={"Full-time": 12}), None)
		self.assertEqual(out["billable_employees"], 12)

	def test_an_excluded_employment_type_is_not_billed(self):
		frappe.db.set_value("Alvoraa Subscription", self.SITE,
		                    "excluded_employment_types", "Intern\nContract")
		out = usage._write_record(
			self.SITE, self.PERIOD,
			self.payload(by_status={"Active": 30},
			             by_type={"Full-time": 20, "Intern": 7, "Contract": 3}), None)
		self.assertEqual(out["billable_employees"], 20)

	def test_the_exclusion_is_written_down_with_the_count(self):
		"""An invoice has to be able to show its working."""
		frappe.db.set_value("Alvoraa Subscription", self.SITE,
		                    "excluded_employment_types", "Intern")
		usage._write_record(self.SITE, self.PERIOD,
		                    self.payload(by_status={"Active": 11},
		                                 by_type={"Full-time": 10, "Intern": 1}), None)
		out = usage.get_usage(self.SITE, self.PERIOD)
		self.assertEqual(out["breakdown"]["excluded_employment_types"], ["Intern"])
		self.assertEqual(out["breakdown"]["active_by_employment_type"]["Intern"], 1)

	def test_no_exclusions_means_everybody_active_counts(self):
		out = usage._write_record(
			self.SITE, self.PERIOD,
			self.payload(by_status={"Active": 9},
			             by_type={"Full-time": 6, "Intern": 3}), None)
		self.assertEqual(out["billable_employees"], 9)

	def test_an_empty_site_costs_nothing_and_still_gets_a_row(self):
		out = usage._write_record(self.SITE, self.PERIOD,
		                          self.payload(by_status={}, by_type={}), None)
		self.assertTrue(out["ok"])
		self.assertEqual(out["billable_employees"], 0)


class TestFailureIsRecorded(UsageCase):
	def test_a_failed_measurement_still_writes_a_row(self):
		"""A month with no row looks like a tenant nobody billed. A row saying
		the count failed looks like something to go and fix."""
		out = usage._write_record(self.SITE, self.PERIOD, None, "site was down")
		self.assertFalse(out["ok"])
		self.assertEqual(usage.get_usage(self.SITE, self.PERIOD)["error"], "site was down")

	def test_a_failed_month_can_simply_be_re_run(self):
		usage._write_record(self.SITE, self.PERIOD, None, "site was down")
		usage._write_record(self.SITE, self.PERIOD,
		                    self.payload(by_status={"Active": 5},
		                                 by_type={"Full-time": 5}), None)
		out = usage.get_usage(self.SITE, self.PERIOD)
		self.assertTrue(out["ok"])
		self.assertIsNone(out["error"])
		self.assertEqual(out["billable_employees"], 5)

	def test_running_twice_never_makes_a_second_row(self):
		for _ in range(3):
			usage._write_record(self.SITE, self.PERIOD,
			                    self.payload(), None)
		self.assertEqual(
			frappe.db.count("Alvoraa Usage Record",
			                {"site_name": self.SITE, "period": self.PERIOD}), 1)

	def test_each_month_is_its_own_row(self):
		usage._write_record(self.SITE, "2026-07", self.payload(), None)
		usage._write_record(self.SITE, "2026-08", self.payload(), None)
		self.assertEqual(frappe.db.count("Alvoraa Usage Record",
		                                 {"site_name": self.SITE}), 2)


class TestReadingBenchOutput(UsageCase):
	"""bench prints what it likes around a return value, and that has changed
	between Frappe versions. This line becomes an invoice, so the parse has to
	be immune to all of it."""

	class Result:
		def __init__(self, stdout="", stderr="", returncode=0):
			self.stdout, self.stderr, self.returncode = stdout, stderr, returncode

	def test_the_count_is_found_among_other_output(self):
		payload, problem = usage._read_payload(self.Result(
			stdout="Updating DocTypes...\n"
			       + usage.SENTINEL + '{"employees": {"total": 3}}\n'
			       + "done\n"))
		self.assertIsNone(problem)
		self.assertEqual(payload["employees"]["total"], 3)

	def test_a_broken_line_says_so_rather_than_guessing(self):
		payload, problem = usage._read_payload(
			self.Result(stdout=usage.SENTINEL + "{not json"))
		self.assertIsNone(payload)
		self.assertIn("could not read", problem)

	def test_a_failed_bench_run_reports_its_error(self):
		payload, problem = usage._read_payload(
			self.Result(stderr="site does not exist", returncode=1))
		self.assertIsNone(payload)
		self.assertIn("site does not exist", problem)

	def test_silence_is_not_treated_as_zero(self):
		"""An empty answer read as zero employees is a free month for a tenant
		and nobody would ever notice."""
		payload, problem = usage._read_payload(self.Result(stdout="", returncode=0))
		self.assertIsNone(payload)
		self.assertIn("no count", problem)

	def test_nothing_at_all_is_reported_too(self):
		payload, problem = usage._read_payload(None)
		self.assertIsNone(payload)
		self.assertTrue(problem)


class TestPacks(UsageCase):
	def setUp(self):
		super().setUp()
		doc = frappe.get_doc("Alvoraa Subscription", self.SITE)
		doc.append("packs", {"pack": "Finance", "named_users": 3})
		doc.save(ignore_permissions=True)

	def test_measured_against_agreed(self):
		usage._write_record(self.SITE, self.PERIOD,
		                    self.payload(modules={"Accounts": 5, "Assets": 2}), None)
		row = usage.get_usage(self.SITE, self.PERIOD)["packs"][0]
		self.assertEqual(row["agreed_users"], 3)
		self.assertEqual(row["measured_users"], 5)
		self.assertEqual(row["over_by"], 2)

	def test_one_person_with_two_modules_is_one_named_user(self):
		"""The largest single module, not the sum - or everybody would be
		counted once per screen they can open."""
		usage._write_record(self.SITE, self.PERIOD,
		                    self.payload(modules={"Accounts": 4, "Assets": 4}), None)
		self.assertEqual(
			usage.get_usage(self.SITE, self.PERIOD)["packs"][0]["measured_users"], 4)

	def test_being_under_the_agreed_number_is_not_a_negative(self):
		usage._write_record(self.SITE, self.PERIOD,
		                    self.payload(modules={"Accounts": 1}), None)
		self.assertEqual(
			usage.get_usage(self.SITE, self.PERIOD)["packs"][0]["over_by"], 0)


class TestTheMonthlyPicture(UsageCase):
	def test_a_tenant_with_no_count_is_named(self):
		"""A missing row is exactly what nobody notices."""
		frappe.get_doc({
			"doctype": "Alvoraa Subscription", "site_name": "other.alvoraa.co",
			"status": "Active", "customer": self.customer, "plan": "Starter",
		}).insert(ignore_permissions=True)
		usage._write_record(self.SITE, self.PERIOD, self.payload(), None)
		out = usage.usage_summary(self.PERIOD)
		self.assertIn("other.alvoraa.co", out["not_counted"])
		self.assertNotIn(self.SITE, out["not_counted"])

	def test_the_total_ignores_a_failed_count(self):
		"""Adding a failed month in as zero understates the bill silently."""
		usage._write_record(self.SITE, self.PERIOD,
		                    self.payload(by_status={"Active": 7},
		                                 by_type={"Full-time": 7}), None)
		frappe.get_doc({
			"doctype": "Alvoraa Subscription", "site_name": "other.alvoraa.co",
			"status": "Active", "customer": self.customer, "plan": "Starter",
		}).insert(ignore_permissions=True)
		usage._write_record("other.alvoraa.co", self.PERIOD, None, "down")
		out = usage.usage_summary(self.PERIOD)
		self.assertEqual(out["billable_total"], 7)
		self.assertIn("other.alvoraa.co", out["failed"])

	def test_reading_a_month_that_was_never_counted_returns_nothing(self):
		self.assertIsNone(usage.get_usage(self.SITE, "1999-01"))


class TestControlPlaneOnly(FrappeTestCase):
	"""A tenant must not be able to read - or influence - what it is billed for."""

	def setUp(self):
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf.pop("alvoraa_control_plane", None)

	def tearDown(self):
		if self._plane is not None:
			frappe.conf["alvoraa_control_plane"] = self._plane

	def test_collecting_is_refused_on_a_tenant(self):
		with self.assertRaises(frappe.ValidationError):
			usage.collect()

	def test_reading_the_summary_is_refused_on_a_tenant(self):
		with self.assertRaises(frappe.ValidationError):
			usage.usage_summary()

	def test_the_monthly_job_is_silent_on_a_tenant(self):
		"""It runs on every site we own. Throwing on each of them every month
		fills the error log with the same non-problem until nobody reads it."""
		self.assertIsNone(usage.collect_scheduled())

	def test_measuring_still_works_on_a_tenant(self):
		"""It has to - that is the half that runs there. It counts and prints,
		writes nothing and decides nothing."""
		out = usage.measure_here()
		self.assertIn("employees", out)
		self.assertIn("by_status", out["employees"])
		self.assertIsInstance(out["employees"]["total"], int)

	def test_the_measurement_is_json_a_machine_can_read_back(self):
		payload, problem = usage._read_payload(
			type("R", (), {"stdout": usage.SENTINEL
			                          + json.dumps(usage.measure_here(), default=str),
			               "stderr": "", "returncode": 0})())
		self.assertIsNone(problem)
		self.assertIn("employees", payload)
