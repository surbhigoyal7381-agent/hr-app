"""Slice 012 push 1 · HR's Data to review page and its confirmations (US-4, US-6).

AC-19, AC-21 to AC-24, AC-29, AC-31 to AC-34, AC-36, SEC-7, SEC-13, SEC-14,
OPS-40, OPS-49, OPS-63. The records come from a real run of the morning check
over a synthetic tenant, dated relative to today, so the page is tested against
what the job actually writes.
"""

import inspect
from contextlib import ExitStack
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, add_to_date, get_first_day, getdate, now_datetime, today

from alvoraa_portal import data_review as dr
from alvoraa_portal.tests import leader_fixtures_012 as fx

SETTINGS_MODULE = "alvoraa_portal.alvoraa_portal.doctype.alvoraa_leader_view_settings.alvoraa_leader_view_settings"


def setUpModule():
	fx.setup_module_fixtures()


def _leave_year_start():
	return getdate(add_months(get_first_day(today()), -5))


def environment():
	"""Plan includes analytics, a fixed leave year five months old, minimum 5, no commits."""
	stack = ExitStack()
	stack.enter_context(patch("alvoraa_portal.subscription.has_feature", return_value=True))
	stack.enter_context(patch("alvoraa_portal.hr_api._leave_year_start", return_value=_leave_year_start()))
	stack.enter_context(patch(f"{SETTINGS_MODULE}.min_group_size", return_value=5))
	stack.enter_context(patch.object(frappe.db, "commit"))
	stack.enter_context(patch.object(frappe.db, "rollback"))
	return stack


def _clear_limit(user):
	bucket = now_datetime().strftime("%Y%m%d%H")
	for endpoint in ("data_review_confirm", "data_review_items"):
		frappe.cache.delete_value(f"alvoraa:limit:data_review.{endpoint}:{user}:{bucket}")


class ReviewCase(FrappeTestCase):
	"""Kavya: Lakeside (doubtful 3 days, two leavers with no date), Station Road
	(doubtful 1 day), leave that looks unrecorded, nobody left in a year."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.env = environment()
		cls.env.__enter__()
		cls.lakeside, cls.station = fx.branch("Lakeside"), fx.branch("Station")
		cls.up_to = getdate(add_days(today(), -2))
		cls.days = [add_days(cls.up_to, -2), add_days(cls.up_to, -1), cls.up_to]
		cls.worked = add_days(cls.up_to, -3)

		cls.lake = [fx.employee(f"DRLake{i}", fx.KAVYA, cls.lakeside, fast=True) for i in range(10)]
		cls.stat = [fx.employee(f"DRStat{i}", fx.KAVYA, cls.station, fast=True) for i in range(10)]
		for emp in cls.lake:
			fx.attendance(emp, fx.KAVYA, cls.lakeside, cls.worked, "Present")
			for d in cls.days:
				fx.attendance(emp, fx.KAVYA, cls.lakeside, d, "Absent")
		for emp in cls.stat:
			fx.attendance(emp, fx.KAVYA, cls.station, cls.worked, "Present")
			fx.attendance(emp, fx.KAVYA, cls.station, cls.days[0], "Absent")
		ys = _leave_year_start()
		for emp in cls.lake + cls.stat:
			fx.allocation(emp, fx.KAVYA, None, ys, add_days(add_months(ys, 12), -1), 15)
		fx.application(cls.lake[0], fx.KAVYA, cls.lakeside, add_days(ys, 10), 1)
		cls.leavers = [fx.employee(f"DRGone{i}", fx.KAVYA, cls.lakeside, status="Left", fast=True)
		               for i in range(2)]

		dr.run_morning_checks([fx.KAVYA])

		cls.priya = fx.user("drpriya", ["HR Manager"])
		fx.permission(cls.priya, "Company", fx.KAVYA)
		cls.lake_hr = fx.user("drlakehr", ["HR User"])
		fx.employee("DRLakeHR", fx.KAVYA, cls.lakeside, user_id=cls.lake_hr)
		fx.permission(cls.lake_hr, "Branch", cls.lakeside)
		cls.station_hr = fx.user("drstationhr", ["HR User"])
		fx.employee("DRStationHR", fx.KAVYA, cls.station, user_id=cls.station_hr)
		fx.permission(cls.station_hr, "Branch", cls.station)
		for u in (cls.priya, cls.lake_hr, cls.station_hr):
			_clear_limit(u)

	@classmethod
	def tearDownClass(cls):
		cls.env.__exit__(None, None, None)
		super().tearDownClass()

	def setUp(self):
		self.caller = frappe.session.user

	def tearDown(self):
		frappe.set_user(self.caller)

	def item(self, rule, branch=None, check_date=None):
		filters = {"company": fx.KAVYA, "rule": rule, "alvoraa_branch": branch or ("is", "not set")}
		if check_date:
			filters["check_date"] = check_date
		return frappe.db.get_value(fx.DRI, filters, "name")

	def lake_days(self):
		return [self.item("D5", self.lakeside, d) for d in self.days]

	def as_user(self, user, fn, *args, **kwargs):
		frappe.set_user(user)
		try:
			return fn(*args, **kwargs)
		finally:
			frappe.set_user("Administrator")


class TestTheJobMadeTheRecords(ReviewCase):
	def test_the_fixture_has_the_expected_open_records(self):
		self.assertTrue(all(self.lake_days()))
		self.assertTrue(self.item("D5", self.station, self.days[0]))
		self.assertTrue(self.item("D6"))
		self.assertTrue(self.item("D18-1", self.lakeside))
		self.assertTrue(self.item("D18-2"))


class TestConfirmAbsence(ReviewCase):
	def test_hr_confirms_the_absence_was_real(self):
		"""AC-19: status, who, when, the figure before and after, one Version row each."""
		names = self.lake_days()
		versions = frappe.db.count("Version", {"ref_doctype": fx.DRI})
		out = self.as_user(self.priya, dr.data_review_confirm, items=names, action="absence_real")
		self.assertEqual(out, {"ok": True, "confirmed": 3})
		for name in names:
			d = frappe.get_doc(fx.DRI, name)
			self.assertEqual((d.status, d.confirmation, d.confirmed_by), ("Confirmed", "Absence was real", self.priya))
			self.assertIsNotNone(d.confirmed_on)
			if all(getdate(x).month == self.up_to.month for x in [self.worked, *self.days]):
				# 20 present; Station's day still left out; Lakeside's 30 absences counted again.
				self.assertEqual((d.figure_without, d.figure_with), (100.0, 40.0))
		self.assertEqual(frappe.db.count("Version", {"ref_doctype": fx.DRI}), versions + 3)


class TestTwoHrPeopleAtOnce(ReviewCase):
	def test_a_second_confirmation_of_the_same_day_is_refused(self):
		"""AC-24: the second of two HR people changes nothing."""
		name = self.item("D5", self.station, self.days[0])
		self.as_user(self.priya, dr.data_review_confirm, items=[name], action="absence_real")
		with self.assertRaises(frappe.ValidationError):
			self.as_user(self.station_hr, dr.data_review_confirm, items=[name], action="absence_real")
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "confirmed_by"), self.priya)

	def test_rows_are_locked_while_they_are_checked(self):
		"""AC-24: the lock is what stops two simultaneous confirmations both succeeding."""
		self.assertIn("for_update=True", inspect.getsource(dr.data_review_confirm))


class TestConfirmFigures(ReviewCase):
	def test_hr_confirms_leave_used_is_right(self):
		"""AC-21."""
		name = self.item("D6")
		self.as_user(self.priya, dr.data_review_confirm, items=[name], action="figure_right")
		d = frappe.get_doc(fx.DRI, name)
		self.assertEqual((d.status, d.confirmation), ("Confirmed", "Figure is right"))
		self.assertEqual(d.figure_with, 0.3)          # 1 day of 300 allocated

	def test_nobody_left_in_a_year_can_be_confirmed(self):
		"""BA-Q1 / D-2: rule D18-2 has the button."""
		name = self.item("D18-2")
		self.as_user(self.priya, dr.data_review_confirm, items=[name], action="figure_right")
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Confirmed")

	def test_left_with_no_leaving_date_cannot_be_confirmed(self):
		"""AC-22 / D-2: a missing date is always a gap."""
		name = self.item("D18-1", self.lakeside)
		with self.assertRaises(frappe.PermissionError):
			self.as_user(self.priya, dr.data_review_confirm, items=[name], action="figure_right")
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Open")

	def test_the_action_must_match_the_record(self):
		with self.assertRaises(frappe.PermissionError):
			self.as_user(self.priya, dr.data_review_confirm, items=[self.item("D6")], action="absence_real")


class TestStoreHrConfirms(ReviewCase):
	def test_store_hr_cannot_confirm_another_store_or_a_company_record(self):
		"""AC-23: 403, nothing changes, one security line with the rule and nothing else."""
		station_day = self.item("D5", self.station, self.days[0])
		for name, action in ((station_day, "absence_real"), (self.item("D6"), "figure_right"),
		                     (self.item("D18-2"), "figure_right")):
			with patch("hrms.alvoraa_hr_core.access.log_refusal") as logged:
				with self.assertRaises(frappe.PermissionError):
					self.as_user(self.lake_hr, dr.data_review_confirm, items=[name], action=action)
			self.assertEqual(logged.call_count, 1)
			self.assertEqual(logged.call_args.args[0], "SEC-13")
			self.assertNotIn(self.station, repr(logged.call_args))
			self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Open")

	def test_one_bad_record_refuses_the_whole_request(self):
		names = self.lake_days() + [self.item("D5", self.station, self.days[0])]
		with self.assertRaises(frappe.PermissionError):
			self.as_user(self.lake_hr, dr.data_review_confirm, items=names, action="absence_real")
		self.assertEqual({frappe.db.get_value(fx.DRI, n, "status") for n in names}, {"Open"})

	def test_store_hr_confirms_their_own_store(self):
		self.as_user(self.lake_hr, dr.data_review_confirm, items=self.lake_days(), action="absence_real")
		self.assertEqual({frappe.db.get_value(fx.DRI, n, "status") for n in self.lake_days()}, {"Confirmed"})

	def test_an_unknown_record_gets_the_same_refusal(self):
		with self.assertRaises(frappe.PermissionError):
			self.as_user(self.lake_hr, dr.data_review_confirm, items=["DRI-doesnotexist"], action="absence_real")


class TestThePage(ReviewCase):
	def test_central_hr_sees_every_kind_with_counts_and_no_people(self):
		"""AC-31, AC-36."""
		out = self.as_user(self.priya, dr.data_review_items)
		kinds = sorted(c["kind"] for c in out["cards"])
		self.assertEqual(kinds, ["doubtful", "doubtful", "leave", "leavers", "leavers"])
		self.assertEqual(out["open_count"], 7)
		lake_card = [c for c in out["cards"] if c["kind"] == "doubtful" and self.lakeside in c["branches"]][0]
		self.assertEqual(lake_card["dates"], [str(d) for d in self.days])
		self.assertEqual(lake_card["absent_pct"], [100.0, 100.0])
		leavers = {c["rule"]: c for c in out["cards"] if c["kind"] == "leavers"}
		self.assertEqual((leavers["D18-1"]["people"], leavers["D18-1"]["can_confirm"]), (2, False))
		self.assertTrue(leavers["D18-2"]["can_confirm"])

		text = frappe.as_json(out)
		for emp in self.lake + self.stat + self.leavers:
			self.assertNotIn(emp, text)
			self.assertNotIn(frappe.db.get_value("Employee", emp, "employee_name"), text)

	def test_store_hr_sees_only_their_store(self):
		"""AC-32: no other store, no company-wide record, a count to match."""
		out = self.as_user(self.lake_hr, dr.data_review_items)
		self.assertEqual(out["scope"], "branch")
		self.assertFalse(out["whole_company"])
		self.assertEqual(out["open_count"], 4)       # three doubtful days and the leavers
		self.assertEqual({c["kind"] for c in out["cards"]}, {"doubtful", "leavers"})
		self.assertTrue(all(self.station not in frappe.as_json(c) for c in out["cards"]))

	def test_people_who_are_not_hr_are_refused(self):
		"""AC-32 / SEC-7."""
		if not frappe.db.exists("Role", "Leadership"):
			frappe.get_doc({"doctype": "Role", "role_name": "Leadership"}).insert(ignore_permissions=True)
		for user in (fx.user("dremployee", ["Employee"]), fx.user("drleader", ["Leadership"]), "Guest"):
			with self.assertRaises(frappe.PermissionError):
				self.as_user(user, dr.data_review_items)
			with self.assertRaises(frappe.PermissionError):
				self.as_user(user, dr.data_review_confirm, items=self.lake_days(), action="absence_real")

	def test_endpoint_hygiene(self):
		"""SEC-7: POST only, plan-gated, not cached by the browser."""
		for fn in (dr.data_review_items, dr.data_review_confirm):
			self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func.get(fn), ["POST"])
			self.assertEqual(getattr(fn, "__alvoraa_feature__", None), "analytics")
		frappe.local.response_headers = frappe.local.response_headers.__class__()
		self.as_user(self.priya, dr.data_review_items)
		self.assertEqual(frappe.local.response_headers.get("Cache-Control"), "no-store")

	def test_last_checked_and_the_stale_line(self):
		"""AC-33: stale after 26 hours, or when it never ran."""
		for stamp, stale in ((add_to_date(now_datetime(), hours=-1), False),
		                     (add_to_date(now_datetime(), hours=-27), True), (None, True)):
			frappe.db.set_single_value(dr.SETTINGS, "last_checks_run_on", stamp)
			out = self.as_user(self.priya, dr.data_review_items)
			self.assertEqual(out["stale"], stale, stamp)

	def test_hr_that_is_not_linked_gets_the_message(self):
		self.assertEqual(self.as_user(fx.user("drunlinked", ["HR Manager"]), dr.data_review_items),
		                 {"not_linked": True})


class TestFixingTheDataClearsTheRecord(ReviewCase):
	def test_leaving_dates_clear_leavers_when_store_hr_opens_the_page(self):
		"""AC-29 / OPS-49: without waiting for 06:30."""
		name = self.item("D18-1", self.lakeside)
		for emp in self.leavers:
			frappe.db.set_value("Employee", emp, "relieving_date", add_days(today(), -30))
		out = self.as_user(self.lake_hr, dr.data_review_items)
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Cleared")
		self.assertFalse([c for c in out["cards"] if c["kind"] == "leavers"])

	def test_the_page_never_re_opens_a_cleared_record(self):
		"""DEF-5 (2026-09-16), decision D-5: the page clears records, it never brings
		one back. The morning run re-opens a finding that fires again.
		"""
		name = self.item("D18-1", self.lakeside)
		for emp in self.leavers:
			frappe.db.set_value("Employee", emp, "relieving_date", add_days(today(), -30))
		self.as_user(self.lake_hr, dr.data_review_items)
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Cleared")

		# The gap comes back: the page leaves the record Cleared, the job re-opens it.
		for emp in self.leavers:
			frappe.db.set_value("Employee", emp, "relieving_date", None)
		self.as_user(self.lake_hr, dr.data_review_items)
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Cleared")
		dr.run_morning_checks([fx.KAVYA])
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Open")

	def test_the_page_never_creates_a_record(self):
		"""D-5: a new finding waits for the morning."""
		third = fx.branch("NewLeavers")
		fx.employee("DRNewGone", fx.KAVYA, third, status="Left", fast=True)
		self.as_user(self.priya, dr.data_review_items)
		self.assertFalse(self.item("D18-1", third))


class TestNothingToReview(ReviewCase):
	def test_a_store_with_no_open_records_gets_an_empty_list(self):
		"""AC-34."""
		quiet = fx.branch("Quiet")
		quiet_hr = fx.user("drquiethr", ["HR User"])
		fx.employee("DRQuietHR", fx.KAVYA, quiet, user_id=quiet_hr)
		fx.permission(quiet_hr, "Branch", quiet)
		out = self.as_user(quiet_hr, dr.data_review_items)
		self.assertEqual((out["open_count"], out["cards"]), (0, []))


class TestReadLimit(ReviewCase):
	"""M1 (code review, 2026-09-16): opening the page re-checks leave and leavers and
	saves what changed, so it writes as well as reads. It must not be callable in a
	loop. OPS-40's read half: 120 an hour per user, counted per user, not per address.
	"""

	def test_the_page_can_be_opened_only_so_often_per_user(self):
		_clear_limit(self.priya)
		_clear_limit(self.lake_hr)
		with patch.object(dr, "READS_PER_HOUR", 2):
			self.as_user(self.priya, dr.data_review_items)
			self.as_user(self.priya, dr.data_review_items)
			with self.assertRaises(frappe.exceptions.TooManyRequestsError):
				self.as_user(self.priya, dr.data_review_items)
			# A colleague on the same office Wi-Fi is not affected.
			self.assertFalse(self.as_user(self.lake_hr, dr.data_review_items)["not_linked"])
		_clear_limit(self.priya)

	def test_the_limit_is_generous_enough_for_a_working_day(self):
		self.assertGreaterEqual(dr.READS_PER_HOUR, 60)


class TestConfirmLimit(ReviewCase):
	def test_thirty_confirmations_an_hour_per_user(self):
		"""OPS-40: counted per user, so a colleague on the same Wi-Fi is not affected."""
		name = self.item("D5", self.station, self.days[0])
		with patch.object(dr, "CONFIRMS_PER_HOUR", 1):
			with self.assertRaises(frappe.PermissionError):         # the first call counts
				self.as_user(self.lake_hr, dr.data_review_confirm, items=[name], action="absence_real")
			with self.assertRaises(frappe.exceptions.TooManyRequestsError):
				self.as_user(self.lake_hr, dr.data_review_confirm, items=[name], action="absence_real")
			self.as_user(self.station_hr, dr.data_review_confirm, items=[name], action="absence_real")
		self.assertEqual(frappe.db.get_value(fx.DRI, name, "status"), "Confirmed")


class TestPageQueryCount(FrappeTestCase):
	"""OPS-63: opening the page costs the same at 10 and 100 people, 2 and 8 branches."""

	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user(self.caller)

	def count(self, people, branches):
		names = [fx.branch("DRQC") for _ in range(branches)]
		hr = fx.user(f"drqc{people}x{branches}", ["HR Manager"])
		fx.permission(hr, "Company", fx.OTHER)
		for i in range(people):
			b = names[i % branches]
			emp = fx.employee(f"DRQC{i}", fx.OTHER, b, fast=True)
			fx.attendance(emp, fx.OTHER, b, add_days(today(), -3), "Present")
		frappe.set_user(hr)
		try:
			with environment():
				dr.data_review_items()
				with fx.QueryCounter() as q:
					dr.data_review_items()
		finally:
			frappe.set_user("Administrator")
		return q.count

	def test_counts_are_fixed(self):
		counts = {k: self.count(*k) for k in ((10, 2), (100, 2), (10, 8), (100, 8))}
		self.assertEqual(len(set(counts.values())), 1, counts)
