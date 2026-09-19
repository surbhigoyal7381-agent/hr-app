"""Slice 012 push 1 · the morning checks: doubtful days, leave and leavers (US-3, US-5, US-7).

AC-12 to AC-15, AC-18, AC-24, AC-26 to AC-28, AC-30, AC-37 to AC-39, AC-161,
OPS-48 to OPS-50, OPS-63, OPS-76. Where the spec's example needs a hundred
people, the same percentages are built with twenty.

The job commits after each company. Here commit and rollback are held off, so
the class still rolls back at its end.
"""

import json
from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from alvoraa_portal import data_review as dr
from alvoraa_portal.tests import leader_fixtures_012 as fx

AS_OF = getdate("2026-09-14")
DAY = getdate("2026-09-08")


def setUpModule():
	fx.setup_module_fixtures()


@contextmanager
def no_commits():
	with patch.object(frappe.db, "commit"), patch.object(frappe.db, "rollback"):
		yield


class ChecksCase(FrappeTestCase):
	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user(self.caller)

	def run_check(self, company=fx.KAVYA, minimum=5, as_of=AS_OF, rules=("D5",) + dr.DAILY_RULES):
		findings = dr.company_findings(company, minimum, as_of, rules=rules)
		return dr.apply_findings(dr.existing_items(company, as_of, rules=rules), findings, allow_create=True)

	def items(self, company=fx.KAVYA, **filters):
		return frappe.get_all(fx.DRI, filters={"company": company, **filters},
		                      fields=["name", "rule", "item_type", "alvoraa_branch", "check_date", "status",
		                              "expected_count", "absent_count", "checked_in_count",
		                              "affected_count", "people_count", "days_allocated"])

	def day_of(self, branch, expected, absent, checked_in, on_leave=0, day=DAY, company=fx.KAVYA):
		people = [fx.employee(f"MC{i}", company, branch, fast=True) for i in range(expected + on_leave)]
		for i, emp in enumerate(people):
			status = "On Leave" if i >= expected else ("Absent" if i < absent else "Present")
			fx.attendance(emp, company, branch, day, status)
			if i < checked_in:
				fx.checkin(emp, branch, f"{day} 09:0{i % 10}:00")
		return people


class TestTheDoubtfulDayRecord(ChecksCase):
	def test_a_doubtful_day_becomes_one_open_record_with_counts_only(self):
		"""AC-12: 61 expected, 59 absent (96.7%), 1 checked in (1.6%), minimum 5."""
		lakeside = fx.branch("Lakeside")
		self.day_of(lakeside, expected=61, absent=59, checked_in=1, on_leave=3)
		self.run_check(rules=("D5",))
		rows = self.items(rule="D5", alvoraa_branch=lakeside)
		self.assertEqual(len(rows), 1)
		r = rows[0]
		self.assertEqual((r.item_type, getdate(r.check_date), r.expected_count, r.absent_count,
		                  r.checked_in_count, r.status), ("Doubtful day", DAY, 61, 59, 1, "Open"))


class TestTheThresholds(ChecksCase):
	def test_ninety_five_percent_absent_and_under_five_percent_checked_in(self):
		"""AC-13 with 20 expected: 19 absent + 0 in -> doubtful; 18 absent -> not; 20 absent + 1 in (5%) -> not."""
		a, b, c = fx.branch("A"), fx.branch("B"), fx.branch("C")
		self.day_of(a, expected=20, absent=19, checked_in=0)
		self.day_of(b, expected=20, absent=18, checked_in=0)
		self.day_of(c, expected=20, absent=20, checked_in=1)
		# One check-in elsewhere in the window, so the company has check-ins.
		self.run_check(rules=("D5",))
		self.assertEqual({r.alvoraa_branch for r in self.items(rule="D5")}, {a})


class TestSmallGroups(ChecksCase):
	def test_a_four_person_branch_is_never_checked(self):
		"""AC-14 / PRIV-10."""
		kiosk = fx.branch("Kiosk")
		self.day_of(kiosk, expected=4, absent=4, checked_in=0)
		self.run_check(rules=("D5",))
		self.assertEqual(self.items(rule="D5", alvoraa_branch=kiosk), [])


class TestNoCheckInsAtAll(ChecksCase):
	def test_absent_alone_decides_when_the_company_has_no_check_ins(self):
		"""AC-15: 24 of 25 absent (96%), nobody in the company checks in."""
		b = fx.branch("NoDevice")
		self.day_of(b, expected=25, absent=24, checked_in=0, company=fx.OTHER)
		self.run_check(company=fx.OTHER, rules=("D5",))
		self.assertEqual(len(self.items(company=fx.OTHER, rule="D5", alvoraa_branch=b)), 1)


class TestSafeToRunAgain(ChecksCase):
	def test_a_second_run_changes_nothing_and_a_fixed_day_is_cleared(self):
		"""AC-18 / OPS-48."""
		b = fx.branch("Rerun")
		people = self.day_of(b, expected=10, absent=10, checked_in=0)
		self.assertEqual(self.run_check(rules=("D5",)), 1)
		name = self.items(rule="D5", alvoraa_branch=b)[0].name
		versions = frappe.db.count("Version", {"ref_doctype": fx.DRI})
		modified = frappe.db.get_value(fx.DRI, name, "modified")

		self.assertEqual(self.run_check(rules=("D5",)), 0)
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "modified"), modified)
		self.assertEqual(frappe.db.count("Version", {"ref_doctype": fx.DRI}), versions)

		# HR corrects the day: nine people were at work after all.
		frappe.db.sql("update `tabAttendance` set status='Present' where employee in %s", (tuple(people[:9]),))
		self.assertEqual(self.run_check(rules=("D5",)), 1)
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Cleared")

	def test_a_confirmed_day_stays_confirmed(self):
		"""AC-24."""
		b = fx.branch("Confirmed")
		people = self.day_of(b, expected=10, absent=10, checked_in=0)
		self.run_check(rules=("D5",))
		name = self.items(rule="D5", alvoraa_branch=b)[0].name
		frappe.db.set_value(fx.DRI, name, {"status": "Confirmed", "confirmation": "Absence was real"})
		frappe.db.sql("update `tabAttendance` set status='Present' where employee in %s", (tuple(people),))
		self.run_check(rules=("D5",))
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Confirmed")


class TestLeaveNeedsReview(ChecksCase):
	def build(self, taken):
		b = fx.branch("Leave")
		people = [fx.employee(f"LV{i}", fx.OTHER, b, fast=True) for i in range(3)]
		fx.attendance(people[0], fx.OTHER, b, DAY)
		for emp in people:
			fx.allocation(emp, fx.OTHER, b, "2026-04-01", "2027-03-31", 2304)
		for emp, days in zip(people, (taken - 2, 1, 1)):
			fx.application(emp, fx.OTHER, b, "2026-05-04", days)
		return people

	def leave_items(self):
		return self.items(company=fx.OTHER, rule="D6")

	def test_leave_under_one_percent_after_three_months(self):
		"""AC-26: 14 of 6,912 days (0.2%), five months in -> one company-wide record."""
		self.build(taken=14)
		with patch("alvoraa_portal.hr_api._leave_year_start", return_value=getdate("2026-04-01")):
			self.run_check(company=fx.OTHER, rules=("D6",))
			rows = self.leave_items()
			self.assertEqual(len(rows), 1)
			r = rows[0]
			self.assertEqual((r.alvoraa_branch, r.affected_count, r.people_count, r.days_allocated, r.status),
			                 (None, 3, 3, 6912.0, "Open"))
			self.assertEqual(getdate(r.check_date), getdate("2026-04-01"))

			# Two months into the year: not yet.
			self.run_check(company=fx.OTHER, rules=("D6",), as_of=getdate("2026-05-31"))
			self.assertEqual(self.leave_items()[0].status, "Cleared")


class TestLeaveAtOnePercent(TestLeaveNeedsReview):
	"""Its own class: leave is judged per company, so the other test's leave would count."""

	test_leave_under_one_percent_after_three_months = None

	def test_one_percent_is_enough(self):
		"""AC-26: 70 of 6,912 days is 1.01%."""
		self.build(taken=70)
		with patch("alvoraa_portal.hr_api._leave_year_start", return_value=getdate("2026-04-01")):
			self.run_check(company=fx.OTHER, rules=("D6",))
		self.assertEqual([r for r in self.leave_items() if r.status == "Open"], [])


class TestLeaversNeedReview(ChecksCase):
	def test_left_with_no_leaving_date_per_branch(self):
		"""AC-27 (three people, not fourteen)."""
		b = fx.branch("Leavers")
		fx.attendance(fx.employee("LVAtt", fx.KAVYA, b, fast=True), fx.KAVYA, b, DAY)
		for i in range(3):
			fx.employee(f"Gone{i}", fx.KAVYA, b, status="Left", fast=True)
		self.run_check(rules=("D18-1",))
		rows = self.items(rule="D18-1", alvoraa_branch=b)
		self.assertEqual([(r.item_type, r.affected_count, r.status) for r in rows], [("Leavers", 3, "Open")])


class TestNobodyLeftInAYear(ChecksCase):
	def test_no_leaving_date_in_twelve_months_is_a_company_record(self):
		"""AC-28."""
		b = fx.branch("NoLeavers")
		fx.attendance(fx.employee("NLAtt", fx.OTHER, b, fast=True), fx.OTHER, b, DAY)
		with patch("alvoraa_portal.hr_api._leave_year_start", return_value=getdate("2026-04-01")):
			self.run_check(company=fx.OTHER, rules=("D18-2",))
			self.assertEqual([r.status for r in self.items(company=fx.OTHER, rule="D18-2")], ["Open"])
			fx.employee("LeftProperly", fx.OTHER, b, status="Left", relieving=add_days(AS_OF, -90), fast=True)
			self.run_check(company=fx.OTHER, rules=("D18-2",))
		self.assertEqual([r.status for r in self.items(company=fx.OTHER, rule="D18-2")], ["Cleared"])


class TestANewTenant(ChecksCase):
	def test_no_attendance_means_no_records(self):
		"""AC-30: "No figures yet", not "Needs review"."""
		frappe.db.sql("update `tabAttendance` set docstatus=2 where company=%s", fx.OTHER)
		fx.employee("Newcomer", fx.OTHER, fx.branch("New"), fast=True)
		with patch("alvoraa_portal.hr_api._leave_year_start", return_value=getdate("2026-04-01")):
			self.assertEqual(dr.company_findings(fx.OTHER, 5, AS_OF), {})


class TestTheJob(ChecksCase):
	def test_the_cron_entry_only_queues_the_job_once(self):
		"""AC-37, OPS-76."""
		from alvoraa_portal import hooks

		self.assertEqual(hooks.scheduler_events["cron"]["30 6 * * *"],
		                 ["alvoraa_portal.data_review.enqueue_morning_checks"])
		with patch("frappe.enqueue") as enqueue:
			dr.enqueue_morning_checks()
		enqueue.assert_called_once_with(dr.JOB_METHOD, queue="long", timeout=900,
		                                job_id="leader-data-checks", deduplicate=True)
		self.assertIs(frappe.get_attr(dr.JOB_METHOD), dr.run_morning_checks)

	def test_a_plan_without_analytics_is_skipped(self):
		"""D-9."""
		with patch("alvoraa_portal.subscription.has_feature", return_value=False), \
		     patch.object(dr, "company_findings") as work:
			dr.run_morning_checks([fx.KAVYA])
		work.assert_not_called()

	def test_a_failure_is_logged_without_figures_and_the_stamp_stays_old(self):
		"""AC-39 / OPS-50 / SEC-15: company, stage and error type only."""
		b = fx.branch("Failing")
		fx.attendance(fx.employee("FailAtt", fx.KAVYA, b, fast=True), fx.KAVYA, b, DAY)
		stamp = "2026-09-01 06:32:00"
		frappe.db.set_single_value(dr.SETTINGS, "last_checks_run_on", stamp)
		before = frappe.db.count("Error Log", {"method": dr.FAILED_TITLE})

		def broken(*args, **kwargs):
			raise ZeroDivisionError("6912 days for Priya Raman")

		with no_commits(), patch("alvoraa_portal.subscription.has_feature", return_value=True), \
		     patch("alvoraa_portal.org_figures.leave_figures", side_effect=broken):
			dr.run_morning_checks([fx.KAVYA])

		logs = frappe.get_all("Error Log", filters={"method": dr.FAILED_TITLE}, fields=["error"],
		                      order_by="creation desc")
		self.assertEqual(len(logs), before + 1)
		self.assertEqual(json.loads(logs[0].error),
		                 {"company": fx.KAVYA, "stage": "leave", "error": "ZeroDivisionError"})
		self.assertNotIn("6912", logs[0].error)
		self.assertEqual(str(frappe.db.get_single_value(dr.SETTINGS, "last_checks_run_on", cache=False)), stamp)

	def test_a_good_run_stamps_last_checked_and_changes_no_hr_record(self):
		"""AC-161 / OPS-50: attendance and employees are read, never written."""
		b = fx.branch("Stamp")
		people = self.day_of(b, expected=6, absent=6, checked_in=0)
		before = frappe.db.sql("select name, modified, status from `tabAttendance` where employee in %s "
		                       "order by name", (tuple(people),))
		emp_before = frappe.db.sql("select name, modified from `tabEmployee` where name in %s order by name",
		                           (tuple(people),))
		frappe.db.set_single_value(dr.SETTINGS, "last_checks_run_on", None)
		with no_commits(), patch("alvoraa_portal.subscription.has_feature", return_value=True), \
		     patch("alvoraa_portal.hr_api._leave_year_start", return_value=getdate("2026-04-01")):
			dr.run_morning_checks([fx.KAVYA])
		self.assertIsNotNone(frappe.db.get_single_value(dr.SETTINGS, "last_checks_run_on", cache=False))
		self.assertEqual(frappe.db.sql("select name, modified, status from `tabAttendance` where employee in %s "
		                               "order by name", (tuple(people),)), before)
		self.assertEqual(frappe.db.sql("select name, modified from `tabEmployee` where name in %s order by name",
		                               (tuple(people),)), emp_before)

	def test_a_run_after_a_crash_ends_like_one_clean_run(self):
		"""AC-38: company A finished, company B did not; the next run completes B and leaves A as it was."""
		ka, ob = fx.branch("CrashA"), fx.branch("CrashB")
		self.day_of(ka, expected=8, absent=8, checked_in=0, company=fx.KAVYA)
		self.day_of(ob, expected=8, absent=8, checked_in=0, company=fx.OTHER)
		real = dr.company_findings

		def crash_on_other(company, *args, **kwargs):
			if company == fx.OTHER:
				raise RuntimeError("killed")
			return real(company, *args, **kwargs)

		with no_commits(), patch("alvoraa_portal.subscription.has_feature", return_value=True), \
		     patch("alvoraa_portal.hr_api._leave_year_start", return_value=getdate("2026-04-01")):
			with patch.object(dr, "company_findings", side_effect=crash_on_other):
				dr.run_morning_checks([fx.KAVYA, fx.OTHER])
			after_crash = {r.name: r.status for r in self.items(fx.KAVYA)}
			self.assertEqual(self.items(fx.OTHER, alvoraa_branch=ob), [])
			dr.run_morning_checks([fx.KAVYA, fx.OTHER])
			once = ({r.name: r.status for r in self.items(fx.KAVYA)},
			        {r.name: r.status for r in self.items(fx.OTHER)})
			dr.run_morning_checks([fx.KAVYA, fx.OTHER])
			twice = ({r.name: r.status for r in self.items(fx.KAVYA)},
			         {r.name: r.status for r in self.items(fx.OTHER)})
		self.assertEqual(once[0], after_crash)
		self.assertEqual(len(self.items(fx.OTHER, alvoraa_branch=ob)), 1)
		self.assertEqual(once, twice)


class TestJobQueryCount(ChecksCase):
	"""OPS-63: reading a company costs the same at 10 and 100 people, 2 and 8 branches."""

	def count(self, people, branches):
		names = [fx.branch("MCQ") for _ in range(branches)]
		for i in range(people):
			b = names[i % branches]
			emp = fx.employee(f"MCQ{i}", fx.OTHER, b, fast=True)
			fx.attendance(emp, fx.OTHER, b, DAY, "Absent")
			fx.checkin(emp, b, f"{DAY} 09:00:00")
			fx.employee(f"MCQLeft{i}", fx.OTHER, b, status="Left", fast=True)
		with patch("alvoraa_portal.hr_api._leave_year_start", return_value=getdate("2026-04-01")):
			with fx.QueryCounter() as q:
				# Minimum 1, so every branch reaches the check-in query at every size.
				dr.company_findings(fx.OTHER, 1, AS_OF)
				dr.existing_items(fx.OTHER, AS_OF)
		return q.count

	def test_counts_are_fixed(self):
		self.count(1, 1)
		counts = {k: self.count(*k) for k in ((10, 2), (100, 2), (10, 8), (100, 8))}
		self.assertEqual(len(set(counts.values())), 1, counts)
