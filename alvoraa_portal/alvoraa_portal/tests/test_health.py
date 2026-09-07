"""Knowing a customer is broken before they ring.

Two things these tests hold to.

**No tracebacks leave a tenant.** A Frappe traceback carries whatever was in
memory when it broke - an employee's name, a salary, an email address. Moving
that onto a machine the customer's employees never agreed to is a DPDP problem,
and it would make the control plane the most sensitive database we own for the
sake of a diagnostic convenience. Titles and counts only.

**Silence is not health.** A tenant that cannot be reached, or that was never
checked, must look worse than a healthy one - not the same. That is the failure
mode this whole file exists to prevent, and it is the easy one to get wrong.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime, nowdate

from alvoraa_portal import health


def _clear():
	for name in frappe.get_all("Alvoraa Tenant Health", pluck="name"):
		frappe.delete_doc("Alvoraa Tenant Health", name, force=True,
		                  ignore_permissions=True)
	frappe.db.commit()


class HealthCase(FrappeTestCase):
	SITE = "sharma.alvoraa.co"

	def setUp(self):
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf["alvoraa_control_plane"] = 1
		_clear()

	def tearDown(self):
		_clear()
		if self._plane is None:
			frappe.conf.pop("alvoraa_control_plane", None)
		else:
			frappe.conf["alvoraa_control_plane"] = self._plane

	def payload(self, errors_24h=0, errors_7d=0, distinct=0, top=None,
	            enabled=True, hours_ago=1):
		last = (str(add_to_date(now_datetime(), hours=-hours_ago))
		        if hours_ago is not None else None)
		return {
			"site": self.SITE,
			"errors": {"last_24h": errors_24h, "last_7d": errors_7d,
			           "distinct": distinct, "top": top or []},
			"scheduler": {"enabled": enabled, "last_job": last},
		}

	def row(self):
		return health.health_summary()["tenants"][0]


class TestNoPersonalDataTravels(FrappeTestCase):
	"""The line that must not move."""

	def test_the_collector_never_reads_a_traceback(self):
		"""`error` is the traceback field on Error Log. `method` is the title."""
		import inspect

		source = inspect.getsource(health._error_counts)
		self.assertIn('"method"', source)
		self.assertNotIn('"error"', source)

	def test_only_titles_and_counts_are_stored(self):
		fields = {f.fieldname for f in
		          frappe.get_meta("Alvoraa Tenant Error").fields}
		self.assertEqual(fields, {"title", "count", "last_seen"})

	def test_a_title_is_capped_so_a_traceback_cannot_ride_along_in_one(self):
		"""If a title ever carried a whole stack, this is what stops it."""
		import inspect

		self.assertIn("[:140]", inspect.getsource(health._error_counts))


class TestWhatIsRecorded(HealthCase):
	def test_a_quiet_tenant_needs_no_attention(self):
		health._write(self.SITE, self.payload(), None)
		row = self.row()
		self.assertTrue(row["ok"])
		self.assertFalse(row["needs_attention"])

	def test_a_noisy_tenant_is_flagged(self):
		health._write(self.SITE, self.payload(errors_24h=200), None)
		row = self.row()
		self.assertTrue(row["noisy"])
		self.assertTrue(row["needs_attention"])

	def test_the_top_errors_come_back_with_the_row(self):
		health._write(self.SITE, self.payload(
			errors_24h=30, distinct=2,
			top=[{"title": "ZeroDivisionError", "count": 28,
			      "last_seen": str(now_datetime())},
			     {"title": "Salary Slip: could not submit", "count": 2,
			      "last_seen": str(now_datetime())}]), None)
		titles = [e["title"] for e in self.row()["top_errors"]]
		self.assertEqual(titles[0], "ZeroDivisionError")

	def test_one_error_many_times_is_told_apart_from_many_errors(self):
		"""A bug and a site falling over need different reactions, so the count
		alone is not enough."""
		health._write(self.SITE, self.payload(errors_24h=500, distinct=1), None)
		self.assertEqual(self.row()["distinct_kinds"], 1)

	def test_checking_twice_in_a_day_updates_one_row(self):
		health._write(self.SITE, self.payload(errors_24h=3), None)
		health._write(self.SITE, self.payload(errors_24h=9), None)
		self.assertEqual(frappe.db.count("Alvoraa Tenant Health",
		                                 {"site_name": self.SITE}), 1)
		self.assertEqual(self.row()["errors_24h"], 9)


class TestBackgroundWork(HealthCase):
	def test_a_scheduler_switched_off_needs_attention(self):
		"""Nothing runs by itself: no payroll, no leave allocation, no
		reminders. It fails silently and looks normal from the front."""
		health._write(self.SITE, self.payload(enabled=False), None)
		row = self.row()
		self.assertFalse(row["scheduler_enabled"])
		self.assertTrue(row["needs_attention"])

	def test_a_scheduler_switched_on_but_stalled_needs_attention_too(self):
		"""The same failure wearing a disguise. The flag says yes and nothing
		has run since Tuesday."""
		health._write(self.SITE, self.payload(enabled=True, hours_ago=30), None)
		row = self.row()
		self.assertTrue(row["scheduler_enabled"])
		self.assertTrue(row["stalled"])
		self.assertTrue(row["needs_attention"])

	def test_a_recent_job_is_not_stalled(self):
		health._write(self.SITE, self.payload(enabled=True, hours_ago=1), None)
		self.assertFalse(self.row()["stalled"])


class TestSilenceIsNotHealth(HealthCase):
	def test_a_site_that_did_not_answer_gets_a_row_saying_so(self):
		health._write(self.SITE, None, "site did not respond")
		row = self.row()
		self.assertFalse(row["ok"])
		self.assertTrue(row["needs_attention"])
		self.assertEqual(row["error"], "site did not respond")

	def test_the_worst_tenant_is_first(self):
		"""A list sorted by name makes the one broken tenant as easy to miss as
		if it were not there."""
		health._write("quiet.alvoraa.co", self.payload(), None)
		health._write("loud.alvoraa.co", self.payload(errors_24h=400), None)
		health._write("dead.alvoraa.co", None, "no answer")
		sites = [r["site_name"] for r in health.health_summary()["tenants"]]
		self.assertEqual(sites[-1], "quiet.alvoraa.co")
		self.assertIn(sites[0], ("dead.alvoraa.co", "loud.alvoraa.co"))

	def test_a_failed_check_can_simply_be_re_run(self):
		health._write(self.SITE, None, "no answer")
		health._write(self.SITE, self.payload(), None)
		self.assertTrue(self.row()["ok"])
		self.assertIsNone(self.row()["error"])

	def test_yesterdays_row_is_not_todays(self):
		health._write(self.SITE, self.payload(errors_24h=5), None)
		self.assertEqual(len(health.health_summary(nowdate())["tenants"]), 1)
		self.assertEqual(health.health_summary("1999-01-01")["tenants"], [])


class TestControlPlaneOnly(FrappeTestCase):
	def setUp(self):
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf.pop("alvoraa_control_plane", None)

	def tearDown(self):
		if self._plane is not None:
			frappe.conf["alvoraa_control_plane"] = self._plane

	def test_collecting_is_refused_on_a_tenant(self):
		with self.assertRaises(frappe.ValidationError):
			health.collect()

	def test_the_summary_is_refused_on_a_tenant(self):
		with self.assertRaises(frappe.ValidationError):
			health.health_summary()

	def test_the_daily_job_is_silent_on_a_tenant(self):
		self.assertIsNone(health.collect_scheduled())

	def test_checking_still_works_on_a_tenant(self):
		"""That is the half that runs there."""
		out = health.check_here()
		self.assertIn("errors", out)
		self.assertIn("scheduler", out)
		self.assertIsInstance(out["errors"]["last_24h"], int)

	def test_what_it_reports_carries_no_traceback(self):
		import json

		blob = json.dumps(health.check_here(), default=str)
		self.assertNotIn("Traceback", blob)
		self.assertNotIn('File "', blob)
