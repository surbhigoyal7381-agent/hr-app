"""Slice 012 push 1 · morning-check edges the first tests did not reach (test engineer).

- D5 at exactly the minimum group, and the job reading the stored minimum (PRIV-10, SEC-22)
- people with no branch are never checked for doubtful days (decision D-12)
- leavers with no branch become a company-wide record that store HR never sees (deviation 4)
- a leave or "nobody left" confirmation lasts one leave year (decision D-3)
- a whole second run writes nothing, for every rule (AC-18, OPS-48)
- neither the page re-check nor the job undoes an HR confirmation (AC-24)
- a doubtful day older than the 35-day window can still clear (AC-18) - DEFECT, expected failure
- after migrate: indexes, then settings, then the queued check; a queue failure never stops migrate (OPS-72)
- the slow-call log line has no company, branch or figure (OPS-56, OPS-57)
- both new doctypes keep change history (OPS-58)
"""

import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from alvoraa_portal import data_review as dr
from alvoraa_portal import org_figures as of
from alvoraa_portal.tests import leader_fixtures_012 as fx
from alvoraa_portal.tests.test_data_review_012 import SETTINGS_MODULE, _clear_limit, environment
from alvoraa_portal.tests.test_morning_checks_012 import AS_OF, DAY, no_commits

YEAR_1 = getdate("2025-04-01")
YEAR_2 = getdate("2026-04-01")


def setUpModule():
	fx.setup_module_fixtures()


def _fiscal_april(date_=None, company=None):
	d = getdate(date_ or today())
	return getdate(f"{d.year if d.month >= 4 else d.year - 1}-04-01")


class EdgeCase(FrappeTestCase):
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
		                      fields=["name", "rule", "alvoraa_branch", "check_date", "status", "modified"])

	def day_of(self, branch, expected, absent, day=DAY, company=fx.KAVYA):
		people = [fx.employee(f"EDG{i}", company, branch, fast=True) for i in range(expected)]
		for i, emp in enumerate(people):
			fx.attendance(emp, company, branch, day, "Absent" if i < absent else "Present")
		return people


class TestTheMinimumGroupItself(EdgeCase):
	def test_a_group_of_exactly_the_minimum_is_checked(self):
		"""PRIV-10 boundary: expected == minimum is checked; one fewer is not."""
		five, four = fx.branch("Five"), fx.branch("Four")
		self.day_of(five, 5, 5)
		self.day_of(four, 4, 4)
		self.run_check(minimum=5, rules=("D5",))
		self.assertEqual(len(self.items(rule="D5", alvoraa_branch=five)), 1)
		self.assertEqual(self.items(rule="D5", alvoraa_branch=four), [])

	def test_the_job_uses_the_stored_minimum(self):
		"""SEC-10 / SEC-22: the job reads the settings doctype, not a constant."""
		eight = fx.branch("Eight")
		self.day_of(eight, 8, 8)
		with no_commits(), patch("alvoraa_portal.subscription.has_feature", return_value=True), \
		     patch("alvoraa_portal.hr_api._leave_year_start", return_value=YEAR_2):
			with patch(f"{SETTINGS_MODULE}.min_group_size", return_value=10):
				dr.run_morning_checks([fx.KAVYA])
			self.assertEqual(self.items(rule="D5", alvoraa_branch=eight), [])
			with patch(f"{SETTINGS_MODULE}.min_group_size", return_value=8):
				dr.run_morning_checks([fx.KAVYA])
			self.assertEqual(len(self.items(rule="D5", alvoraa_branch=eight)), 1)


class TestNoBranchPeopleAreNotChecked(EdgeCase):
	def test_people_with_no_branch_never_make_a_doubtful_day(self):
		"""Decision D-12."""
		self.day_of(None, 8, 8)
		findings = dr.company_findings(fx.KAVYA, 5, AS_OF, rules=("D5",))
		self.assertEqual([f for f in findings.values() if not f["alvoraa_branch"]], [])


class TestLeaversWithNoBranch(EdgeCase):
	"""Deviation 4: Left, no leaving date, no branch -> one company-wide D18-1 record."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.env = environment()
		cls.env.__enter__()
		cls.store = fx.branch("NBStore")
		fx.attendance(fx.employee("NBAtt", fx.KAVYA, cls.store, fast=True), fx.KAVYA, cls.store,
		              add_days(today(), -3))
		for i in range(2):
			fx.employee(f"NBGone{i}", fx.KAVYA, None, status="Left", fast=True)
		dr.run_morning_checks([fx.KAVYA])
		cls.central = fx.user("nbcentral", ["HR User"])
		fx.permission(cls.central, "Company", fx.KAVYA)
		cls.store_hr = fx.user("nbstorehr", ["HR User"])
		fx.employee("NBStoreHR", fx.KAVYA, cls.store, user_id=cls.store_hr)
		fx.permission(cls.store_hr, "Branch", cls.store)
		for u in (cls.central, cls.store_hr):
			_clear_limit(u)

	@classmethod
	def tearDownClass(cls):
		cls.env.__exit__(None, None, None)
		super().tearDownClass()

	def as_user(self, user, fn, *args, **kwargs):
		frappe.set_user(user)
		try:
			return fn(*args, **kwargs)
		finally:
			frappe.set_user("Administrator")

	def record(self):
		return frappe.db.get_value(fx.DRI, {"company": fx.KAVYA, "rule": "D18-1",
		                                    "alvoraa_branch": ("is", "not set")}, ["name", "affected_count"],
		                           as_dict=True)

	def test_one_company_wide_record_that_cannot_be_confirmed(self):
		r = self.record()
		self.assertTrue(r)
		self.assertGreaterEqual(r.affected_count, 2)
		out = self.as_user(self.central, dr.data_review_items)
		card = [c for c in out["cards"] if c["kind"] == "leavers" and c["rule"] == "D18-1" and not c["branch"]]
		self.assertEqual(len(card), 1)
		self.assertFalse(card[0]["can_confirm"])
		with self.assertRaises(frappe.PermissionError):
			self.as_user(self.central, dr.data_review_confirm, items=[r.name], action="figure_right")

	def test_store_hr_never_sees_it(self):
		out = self.as_user(self.store_hr, dr.data_review_items)
		self.assertNotIn(self.record().name, frappe.as_json(out))


class TestAConfirmationLastsOneLeaveYear(EdgeCase):
	def test_leave_and_nobody_left_are_asked_again_next_leave_year(self):
		"""Decision D-3: the record is keyed on the leave year, so a new year asks again."""
		b = fx.branch("Year")
		people = [fx.employee(f"YR{i}", fx.OTHER, b, fast=True) for i in range(3)]
		fx.attendance(people[0], fx.OTHER, b, DAY)
		for emp in people:
			fx.allocation(emp, fx.OTHER, b, "2025-04-01", "2027-03-31", 1000)
		rules = ("D6", "D18-2")
		with patch("alvoraa_portal.hr_api._leave_year_start", side_effect=_fiscal_april):
			self.run_check(company=fx.OTHER, as_of=getdate("2025-09-14"), rules=rules)
			first = {r.rule: r for r in self.items(company=fx.OTHER, check_date=YEAR_1) if r.rule in rules}
			self.assertEqual(set(first), set(rules))
			for r in first.values():
				frappe.db.set_value(fx.DRI, r.name, {"status": "Confirmed", "confirmation": "Figure is right",
				                                     "confirmed_by": "Administrator"})

			self.run_check(company=fx.OTHER, as_of=AS_OF, rules=rules)
			second = {r.rule: r for r in self.items(company=fx.OTHER, check_date=YEAR_2) if r.rule in rules}
		self.assertEqual({k: v.status for k, v in second.items()}, {"D6": "Open", "D18-2": "Open"})
		for rule in rules:
			self.assertNotEqual(first[rule].name, second[rule].name)
			self.assertEqual(frappe.db.get_value(fx.DRI, first[rule].name, "status"), "Confirmed")


class TestAWholeSecondRunWritesNothing(EdgeCase):
	def test_every_rule_second_run(self):
		"""AC-18 / OPS-48 for D5, D6, D18-1 and D18-2 together, through the job itself."""
		b = fx.branch("Whole")
		people = self.day_of(b, 6, 6, company=fx.OTHER)
		for emp in people:
			fx.allocation(emp, fx.OTHER, b, "2026-04-01", "2027-03-31", 100)
		fx.employee("WholeGone", fx.OTHER, b, status="Left", fast=True)
		with no_commits(), patch("alvoraa_portal.subscription.has_feature", return_value=True), \
		     patch("alvoraa_portal.hr_api._leave_year_start", return_value=YEAR_2), \
		     patch(f"{SETTINGS_MODULE}.min_group_size", return_value=5), \
		     patch.object(dr, "today", return_value=str(AS_OF)):
			dr.run_morning_checks([fx.OTHER])
			before = {r.name: (r.status, r.modified) for r in self.items(company=fx.OTHER)}
			self.assertEqual({r.rule for r in self.items(company=fx.OTHER, status="Open")},
			                 {"D5", "D6", "D18-1", "D18-2"})
			versions = frappe.db.count("Version", {"ref_doctype": fx.DRI})
			dr.run_morning_checks([fx.OTHER])
		self.assertEqual({r.name: (r.status, r.modified) for r in self.items(company=fx.OTHER)}, before)
		self.assertEqual(frappe.db.count("Version", {"ref_doctype": fx.DRI}), versions)


class TestConfirmationsSurviveFixedData(EdgeCase):
	"""AC-24: once HR confirmed, neither the page re-check nor the job changes it,
	even when the rule stops firing."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.env = environment()
		cls.env.__enter__()
		from alvoraa_portal.tests.test_data_review_012 import _leave_year_start

		cls.ys = _leave_year_start()
		cls.b = fx.branch("Survive")
		cls.people = [fx.employee(f"SV{i}", fx.KAVYA, cls.b, fast=True) for i in range(3)]
		fx.attendance(cls.people[0], fx.KAVYA, cls.b, add_days(today(), -3))
		for emp in cls.people:
			fx.allocation(emp, fx.KAVYA, cls.b, cls.ys, add_days(cls.ys, 364), 100)
		dr.run_morning_checks([fx.KAVYA])
		cls.priya = fx.user("svpriya", ["HR Manager"])
		fx.permission(cls.priya, "Company", fx.KAVYA)
		_clear_limit(cls.priya)

	@classmethod
	def tearDownClass(cls):
		cls.env.__exit__(None, None, None)
		super().tearDownClass()

	def test_page_recheck_and_job_leave_confirmations_alone(self):
		names = [frappe.db.get_value(fx.DRI, {"company": fx.KAVYA, "rule": rule,
		                                      "alvoraa_branch": ("is", "not set")}, "name")
		         for rule in ("D6", "D18-2")]
		self.assertTrue(all(names))
		frappe.set_user(self.priya)
		try:
			dr.data_review_confirm(items=names, action="figure_right")
		finally:
			frappe.set_user("Administrator")

		# The data is fixed afterwards: plenty of leave, and a proper leaver.
		fx.application(self.people[1], fx.KAVYA, self.b, add_days(self.ys, 20), 250)
		fx.employee("SVLeft", fx.KAVYA, self.b, status="Left", relieving=add_days(today(), -30), fast=True)
		self.assertEqual(dr.company_findings(fx.KAVYA, 5, getdate(today()), rules=("D6", "D18-2")), {})

		frappe.set_user(self.priya)
		try:
			dr.data_review_items()
		finally:
			frappe.set_user("Administrator")
		dr.run_morning_checks([fx.KAVYA])
		for name in names:
			self.assertEqual(frappe.db.get_value(fx.DRI, name, ["status", "confirmed_by"]),
			                 ("Confirmed", self.priya))


class TestAnOldDoubtfulDay(EdgeCase):
	def test_fixing_a_day_older_than_the_window_still_clears_it(self):
		"""DEF-2, fixed 2026-09-16. AC-18 has no time limit.

		A doubtful day HR fixes more than 35 days later used to stay Open for ever:
		on HR's list and in the "N figures need review" count. The check now looks
		again at the days of records that are still Open, however old they are.
		"""
		b = fx.branch("Old")
		old = add_days(AS_OF, -40)
		people = self.day_of(b, 6, 6, day=old)
		self.run_check(as_of=add_days(old, 1), rules=("D5",))
		rows = self.items(rule="D5", alvoraa_branch=b)
		self.assertEqual(len(rows), 1)
		frappe.db.sql("update `tabAttendance` set status='Present' where employee in %s", (tuple(people),))
		self.run_check(rules=("D5",))
		self.assertEqual(frappe.db.get_value(fx.DRI, rows[0].name, "status"), "Cleared")


class TestAfterMigrate(FrappeTestCase):
	def test_indexes_then_settings_then_the_queued_check(self):
		"""OPS-72: the first check runs at deploy, after the indexes it reads through."""
		calls = []
		with patch.object(dr, "add_indexes", side_effect=lambda: calls.append("indexes")), \
		     patch.object(dr, "_ensure_settings", side_effect=lambda: calls.append("settings")), \
		     patch.object(dr, "enqueue_morning_checks", side_effect=lambda: calls.append("queue")):
			dr.after_migrate()
		self.assertEqual(calls, ["indexes", "settings", "queue"])

	def test_install_never_queues_a_check(self):
		with patch.object(dr, "add_indexes"), patch.object(dr, "_ensure_settings"), \
		     patch.object(dr, "enqueue_morning_checks") as queue:
			dr.after_install()
		queue.assert_not_called()

	def test_a_queue_failure_is_logged_and_migrate_carries_on(self):
		with patch.object(dr, "add_indexes"), patch.object(dr, "_ensure_settings"), \
		     patch.object(dr, "enqueue_morning_checks", side_effect=ConnectionError("redis down")), \
		     patch("frappe.log_error") as log_error:
			dr.after_migrate()
		log_error.assert_called_once()
		self.assertEqual(log_error.call_args.kwargs["title"], dr.FAILED_TITLE)
		self.assertNotIn("redis down", log_error.call_args.kwargs["message"])


class TestTheSlowCallLine(FrappeTestCase):
	def test_no_company_branch_or_figure_in_the_line(self):
		"""OPS-56 / OPS-57."""
		scope = of.Scope(("S012 Secret Company",), ("S012 Secret Branch", "S012 Other Branch"))
		with patch("frappe.logger") as logger, patch("time.monotonic", return_value=100.0):
			of.log_if_slow("get_hr_analytics", scope, started=97.5, items=3, name="Priya Raman")
		line = logger.return_value.info.call_args.args[0]
		data = json.loads(line)
		self.assertEqual((data["endpoint"], data["scope"], data["branches"], data["duration_ms"]),
		                 ("get_hr_analytics", "branch", 2, 2500))
		for secret in ("Secret", "Priya"):
			self.assertNotIn(secret, line)

	def test_a_fast_call_writes_nothing(self):
		with patch("frappe.logger") as logger, patch("time.monotonic", return_value=100.0):
			of.log_if_slow("get_hr_analytics", of.Scope(("X",), None), started=99.5)
		logger.assert_not_called()


class TestChangeHistoryIsKept(FrappeTestCase):
	def test_both_doctypes_track_changes(self):
		"""OPS-58 / SEC-13 / SEC-10."""
		for doctype in (dr.DOCTYPE, dr.SETTINGS):
			self.assertEqual(frappe.get_meta(doctype).track_changes, 1, doctype)

	def test_nobody_may_delete_a_review_record(self):
		"""Spec 3c: the job creates, nobody deletes."""
		perms = frappe.get_meta(dr.DOCTYPE).permissions
		self.assertFalse([p.role for p in perms if p.delete or p.create])
