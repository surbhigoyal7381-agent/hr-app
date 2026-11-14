"""ALV-337: a repeat scan stops costing a day, and every shift plays by one rule.

Two faults, one slice, because they are the same fault seen twice: a punch that
Frappe cannot use disappears in silence, and the day then holds an arrival with
no departure, scores 0.0 hours and is marked Absent. Paid days come from that
status, so both faults reach base salary.

  * a DTC reader stores one scan up to nine times within seconds. Alternating
    entries then read the second scan as a departure five seconds after the
    arrival. 984 of November's 9,072 punches were repeats; 139 days were Absent
    on exactly 0.0 recorded hours.
  * a punch past the shift window gets no shift and is never looked at again.
    86 November punches landed there, 74 of them within half an hour of the
    cut-off.

`test_the_marking_job_now_calls_the_day_present` is the one that proves the
money. The rest pin the mechanism and the boundaries.

Fail-without-fix recipe:
  * drop the `before_insert` line for punch_dedupe in hooks.py: the flag tests
    and the marking test fail;
  * compare against the raw previous punch instead of the last KEPT one (drop
    `"skip_auto_attendance": 0` from the lookup, or the `continue` in
    `repeat_scans`): the two `drifting_chain` tests fail.
    `test_nine_scans_in_a_row_collapse_to_one` does NOT - checked by breaking
    it. Nine reads a second apart are all inside two minutes of the first, so
    both ways of measuring fold them alike. Only a chain that drifts tells them
    apart, and the wrong one swallows a whole day into a single punch;
  * drop the employee from the lookup: `test_another_persons_punch...` fails;
  * make the window exclusive at its far end (`>` rather than `>=`):
    `test_exactly_the_window_is_still_one_punch` fails;
  * let `apply` write `enable_auto_attendance` or `process_attendance_after`:
    `test_it_never_touches_the_switch_or_the_start_date` fails - and October's
    repair would refuse to run on the live site;
  * drop the 24-hour ceiling check from shift_standard:
    `test_a_shift_too_long_for_the_window_is_reported_not_broken` fails with
    Frappe's own refusal, half way through a run.

`test_both_before_insert_handlers_are_wired_in_order` passes with no fix at all.
It is here because ALV-302 already owned that event with a single string, and
replacing rather than appending would have silently dropped the handler that
keeps a machine's sent time.
"""

import os

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_time, getdate

from alvoraa_goals.tests.utils import ensure_company
from alvoraa_portal.payroll_rules import DUPLICATE_PUNCH_MINUTES, collapse_duplicate_punches
from alvoraa_portal.punch_dedupe import (earlier_kept_punch, flag_existing, preview_existing,
                                         repeat_scans, unflag_existing)
from alvoraa_portal.shift_standard import NEVER_TOUCHED, STANDARD, apply, preview, undo
from alvoraa_portal.tests.test_field_app_step2_013 import _employee

CHECKIN = "Employee Checkin"
SHIFT = "ALV337 Shift"
LONG_SHIFT = "ALV337 Twenty Hour Shift"
DRIFTED = "ALV337 Drifted Shift"
# A fixed past weekday, so the test does not depend on the day it runs.
DAY = "2026-03-02"


def _punch(employee, at, **extra):
	"""One punch, through the ORM, so every hook on the doctype runs."""
	doc = frappe.get_doc({"doctype": CHECKIN, "employee": employee,
	                      "time": "{0} {1}".format(DAY, at), **extra})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc


def _skipped(name):
	return bool(frappe.db.get_value(CHECKIN, name, "skip_auto_attendance"))


def _shift(name, start="09:00:00", end="18:00:00", **extra):
	"""A shift carrying DTC's settings, not Frappe's defaults."""
	fields = {
		"determine_check_in_and_check_out": "Alternating entries as IN and OUT during the same shift",
		"working_hours_calculation_based_on": "Every Valid Check-in and Check-out",
		"working_hours_threshold_for_absent": 2.0,
		"working_hours_threshold_for_half_day": 4.5,
		"begin_check_in_before_shift_start_time": 180,
		"allow_check_out_after_shift_end_time": 180,
	}
	fields.update(extra)
	existing = frappe.db.exists("Shift Type", name)
	doc = (frappe.get_doc("Shift Type", name) if existing
	       else frappe.get_doc({"doctype": "Shift Type", "name": name}))
	doc.start_time, doc.end_time = start, end
	for field, value in fields.items():
		doc.set(field, value)
	doc.flags.ignore_permissions = True
	if existing:
		doc.save(ignore_permissions=True)
	else:
		doc.insert(ignore_permissions=True)
	return doc.name


class PunchDedupe(FrappeTestCase):
	"""One punch per scan, whatever the reader sends."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		company = ensure_company()
		_shift(SHIFT)
		cls.worker = _employee("Alv337 Worker", company)
		cls.mate = _employee("Alv337 Mate", company)
		# default_shift, never a Shift Assignment: an assignment would make the
		# marking job ALSO mark every assigned day with no punches as Absent,
		# which would bury this test's one day under hundreds of rows.
		frappe.db.set_value("Employee", cls.worker, "default_shift", SHIFT)
		frappe.db.set_value("Employee", cls.mate, "default_shift", SHIFT)
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")
		self._clear()

	def tearDown(self):
		frappe.set_user("Administrator")
		self._clear()
		frappe.db.commit()

	def _clear(self):
		people = [self.worker, self.mate]
		frappe.db.delete("Attendance", {"employee": ("in", people)})
		frappe.db.delete(CHECKIN, {"employee": ("in", people)})

	# ── the mechanism ───────────────────────────────────────────────────────

	def test_a_repeat_scan_is_flagged_and_the_first_is_not(self):
		first = _punch(self.worker, "09:00:00")
		again = _punch(self.worker, "09:00:05")
		self.assertFalse(_skipped(first.name), "the first scan must still count")
		self.assertTrue(_skipped(again.name), "a scan five seconds later is the same punch")

	def test_nine_scans_in_a_row_collapse_to_one(self):
		names = [_punch(self.worker, "09:00:0{0}".format(n)).name for n in range(9)]
		kept = [n for n in names if not _skipped(n)]
		self.assertEqual(len(kept), 1, "nine scans of one arrival are one punch")
		self.assertEqual(kept[0], names[0], "the first scan is the one that counts")

	def test_a_drifting_chain_does_not_swallow_a_real_punch(self):
		"""The gap is measured from the last KEPT punch, not the raw previous row.

		A burst of scans cannot show this: nine reads a second apart are all
		inside two minutes of the first, so either way of measuring folds them
		the same. A DRIFTING chain can. 09:00:00, 09:01:30, 09:03:00 - each 90
		seconds after the one before, but the third is three minutes from the
		first. Measured from the last kept punch the third is a real punch, and
		the day has an arrival and a departure. Measured from whatever row came
		last, the chain swallows itself, the day is left with one punch and no
		departure, and we have rebuilt the fault we set out to fix.

		Written after breaking the fix proved the burst test did NOT catch this.
		"""
		first = _punch(self.worker, "09:00:00")
		middle = _punch(self.worker, "09:01:30")
		last = _punch(self.worker, "09:03:00")
		self.assertFalse(_skipped(first.name), "the arrival counts")
		self.assertTrue(_skipped(middle.name), "90 seconds on is the same punch")
		self.assertFalse(_skipped(last.name),
		                 "three minutes from the arrival is a real punch, not a repeat")

	def test_a_gap_wider_than_the_window_is_two_punches(self):
		first = _punch(self.worker, "09:00:00")
		later = _punch(self.worker, "09:03:00")
		self.assertFalse(_skipped(first.name))
		self.assertFalse(_skipped(later.name), "three minutes apart is two real punches")

	def test_exactly_the_window_is_still_one_punch(self):
		"""`collapse_duplicate_punches` folds a gap of exactly the window, with `<=`.

		The door must agree with it, or the same day reads one way in the pay
		engine and another way in Frappe's marking.
		"""
		self.assertEqual(DUPLICATE_PUNCH_MINUTES, 2, "this test is written for a 2-minute rule")
		first = _punch(self.worker, "09:00:00")
		edge = _punch(self.worker, "09:02:00")
		self.assertFalse(_skipped(first.name))
		self.assertTrue(_skipped(edge.name))

	def test_another_persons_punch_is_not_a_duplicate(self):
		mine = _punch(self.worker, "09:00:00")
		theirs = _punch(self.mate, "09:00:00")
		self.assertFalse(_skipped(mine.name))
		self.assertFalse(_skipped(theirs.name), "two people at one reader are two punches")

	def test_a_flagged_punch_is_not_an_anchor(self):
		"""A punch marking ignores cannot make the next one a duplicate.

		ALV-302 flags a machine punch with an impossible date. If that row
		counted as an anchor, the real punch that followed it would be thrown
		away too - the fault this slice exists to stop, in reverse.
		"""
		filed = _punch(self.worker, "09:00:00", skip_auto_attendance=1)
		real = _punch(self.worker, "09:00:05")
		self.assertTrue(_skipped(filed.name), "it was filed on the way in")
		self.assertFalse(_skipped(real.name), "so the punch after it is the first that counts")

	def test_the_lookup_reports_nothing_when_the_day_is_empty(self):
		self.assertIsNone(earlier_kept_punch(self.worker, "{0} 09:00:00".format(DAY)))

	# ── what it is all for ──────────────────────────────────────────────────

	def test_the_marking_job_now_calls_the_day_present(self):
		"""The money test. A double read used to turn a full day into Absent.

		09:00:00, 09:00:05 and 18:00:00. Alternating entries pair the first two
		as an arrival and a departure five seconds apart, leave 18:00 unpaired,
		and score the day at 0.0 hours - under the 2-hour threshold, so Absent,
		so an unpaid day. With the repeat flagged on the way in, the pair is
		09:00 to 18:00 and the day is a full nine hours.
		"""
		_punch(self.worker, "09:00:00")
		_punch(self.worker, "09:00:05")
		_punch(self.worker, "18:00:00")
		frappe.db.commit()

		shift = frappe.get_doc("Shift Type", SHIFT)
		shift.enable_auto_attendance = 1
		shift.process_attendance_after = "2026-03-01"
		shift.last_sync_of_checkin = "2026-03-03 23:59:59"
		shift.flags.ignore_permissions = True
		shift.save(ignore_permissions=True)
		shift.process_auto_attendance()
		frappe.db.commit()

		row = frappe.db.get_value("Attendance",
		                          {"employee": self.worker, "attendance_date": getdate(DAY)},
		                          ["status", "working_hours"], as_dict=True)
		self.assertIsNotNone(row, "the day should have been marked")
		self.assertEqual(row.status, "Present",
		                 "a nine-hour day with one double read is a present day")
		self.assertAlmostEqual(row.working_hours, 9.0, places=1)

	def test_both_before_insert_handlers_are_wired_in_order(self):
		"""ALV-302 owned this event first, as a single string.

		Replacing it rather than appending would have dropped the handler that
		keeps a machine's sent time - with no error, and no test to catch it.
		"""
		wired = frappe.get_hooks("doc_events")[CHECKIN]["before_insert"]
		machine = "alvoraa_portal.field_app_access.check_machine_punch"
		dedupe = "alvoraa_portal.punch_dedupe.skip_repeat_scan"
		self.assertIn(machine, wired, "ALV-302's handler must survive")
		self.assertIn(dedupe, wired)
		self.assertLess(wired.index(machine), wired.index(dedupe),
		                "ALV-302 files an impossible date first, so it is never an anchor")


class TheShiftStandard(FrappeTestCase):
	"""Every shift plays by one rule, and the two October fields stay untouched."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		ensure_company()

	def setUp(self):
		frappe.set_user("Administrator")
		# Drifted from the standard: wrong hours method, hour thresholds that
		# would call a one-punch day Absent (Surbhi's rule of 13 Nov says it is
		# present but incomplete), and a three-hour window.
		_shift(DRIFTED,
		       working_hours_calculation_based_on="Every Valid Check-in and Check-out",
		       working_hours_threshold_for_absent=2.0,
		       working_hours_threshold_for_half_day=4.5,
		       begin_check_in_before_shift_start_time=180,
		       allow_check_out_after_shift_end_time=180)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		path = frappe.get_site_path("alv337_shift_standard_before.json")
		if os.path.exists(path):
			# apply() reaches EVERY shift on the test site, not only DRIFTED. Put
			# them all back, or other suites' shifts keep this standard's values.
			undo()
		if os.path.exists(path):
			os.remove(path)
		frappe.db.delete("Shift Type", {"name": ("in", (DRIFTED, LONG_SHIFT))})
		frappe.db.commit()

	def _read(self, name, fields=None):
		return frappe.db.get_value("Shift Type", name, fields or list(STANDARD), as_dict=True)

	def test_preview_changes_nothing(self):
		before = self._read(DRIFTED)
		result = preview()
		after = self._read(DRIFTED)
		self.assertEqual(before, after, "preview is read-only")
		self.assertGreaterEqual(result["changing"], 1)

	def test_apply_brings_a_drifted_shift_to_the_standard(self):
		apply()
		row = self._read(DRIFTED)
		for field, want in STANDARD.items():
			have = row[field]
			if isinstance(want, float):
				self.assertAlmostEqual(float(have), want, places=2, msg=field)
			else:
				self.assertEqual(have if not isinstance(want, int) else int(have), want, field)

	def test_undo_puts_the_old_values_back(self):
		before = self._read(DRIFTED)
		apply()
		self.assertNotEqual(self._read(DRIFTED), before, "apply should have changed it")
		undo()
		self.assertEqual(self._read(DRIFTED), before, "undo should restore every field")

	def test_it_never_touches_the_switch_or_the_start_date(self):
		"""The most important test here.

		October's repair (ALV-291) switches the paused shifts back on itself and
		refuses to run while any of them is on. If this module moved either
		field, October would either refuse or be re-processed for everybody on
		that shift.
		"""
		frappe.db.set_value("Shift Type", DRIFTED, {
			"enable_auto_attendance": 1, "process_attendance_after": "2026-10-01"})
		frappe.db.commit()
		apply()
		row = self._read(DRIFTED, ["enable_auto_attendance", "process_attendance_after",
		                           "start_time", "end_time"])
		self.assertEqual(int(row.enable_auto_attendance), 1, "the switch is October's, not ours")
		self.assertEqual(getdate(row.process_attendance_after), getdate("2026-10-01"))
		self.assertEqual(get_time(row.start_time), get_time("09:00:00"))
		self.assertEqual(get_time(row.end_time), get_time("18:00:00"))
		for field in ("enable_auto_attendance", "process_attendance_after"):
			self.assertIn(field, NEVER_TOUCHED)
			self.assertNotIn(field, STANDARD)

	def test_a_shift_too_long_for_the_window_is_reported_not_broken(self):
		"""Frappe caps a shift's length plus both windows at 24 hours.

		A twenty-hour shift cannot take four hours either side. It must be
		reported and left alone, not thrown half way through a run with the
		earlier shifts already written and the later ones not.
		"""
		_shift(LONG_SHIFT, start="04:00:00", end="00:00:00",
		       begin_check_in_before_shift_start_time=30,
		       allow_check_out_after_shift_end_time=30)
		frappe.db.commit()
		result = preview()
		self.assertGreaterEqual(result["refused"], 1, "the long shift should be refused")
		apply()
		row = self._read(LONG_SHIFT, ["begin_check_in_before_shift_start_time",
		                              "allow_check_out_after_shift_end_time"])
		self.assertEqual(int(row.begin_check_in_before_shift_start_time), 30,
		                 "left exactly as it was")
		self.assertEqual(int(row.allow_check_out_after_shift_end_time), 30)

	def test_the_standard_never_calls_a_punched_day_absent_or_half(self):
		"""Pinned. Surbhi's rule, 13 Nov 2026: a day with at least one punch is
		present but incomplete, held for the missing time - never Absent or Half
		Day from hours. Any threshold above 0 would mark a one-punch day (0.0 h)
		Absent again and cut paid days the pay engine is holding."""
		self.assertEqual(STANDARD["working_hours_threshold_for_absent"], 0)
		self.assertEqual(STANDARD["working_hours_threshold_for_half_day"], 0)

	def test_the_standard_sets_four_hours_either_side(self):
		"""Pinned, because three hours is what orphaned 86 November punches.

		Four, not five: five hours either side of a shift ending at 10 PM reaches
		3 AM, and the day somebody holds two assignments a punch could be claimed
		by the wrong shift.
		"""
		self.assertEqual(STANDARD["begin_check_in_before_shift_start_time"], 240)
		self.assertEqual(STANDARD["allow_check_out_after_shift_end_time"], 240)
		self.assertEqual(STANDARD["working_hours_calculation_based_on"],
		                 "First Check-in and Last Check-out")


class PunchesAlreadyStored(FrappeTestCase):
	"""The in-between step, and the order that makes it necessary.

	ALV-291's `cancel_wrong` clears the skip flag on every punch it frees, on
	purpose, so the marking job can use them. So a November re-mark would
	reproduce the same wrong Absents unless the repeats are flagged again
	between the cancel and the marking. These tests pin that step.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		company = ensure_company()
		_shift(SHIFT)
		cls.worker = _employee("Alv337 Stored", company)
		frappe.db.set_value("Employee", cls.worker, "default_shift", SHIFT)
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")
		self._clear()
		# The state a day is in straight after ALV-291's cancel step: the
		# punches are back, loose, and every skip flag has been cleared.
		for at in ("09:00:00", "09:00:05", "09:00:09", "18:00:00"):
			_punch(self.worker, at)
		frappe.db.sql("""update `tabEmployee Checkin` set skip_auto_attendance = 0
		                 where employee = %s""", self.worker)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		self._clear()
		path = frappe.get_site_path("alv337_flagged_punches.json")
		if os.path.exists(path):
			os.remove(path)
		frappe.db.commit()

	def _clear(self):
		frappe.db.delete("Attendance", {"employee": self.worker})
		frappe.db.delete(CHECKIN, {"employee": self.worker})

	def _flags(self):
		return dict(frappe.db.sql("""select time, skip_auto_attendance
		                             from `tabEmployee Checkin` where employee = %s
		                             order by time""", self.worker))

	def test_preview_finds_the_repeats_and_writes_nothing(self):
		before = self._flags()
		result = preview_existing("2026-03-01", "2026-03-31")
		self.assertEqual(result["repeats"], 2, "09:00:05 and 09:00:09 repeat 09:00:00")
		self.assertEqual(self._flags(), before, "preview is read-only")

	def test_flagging_leaves_the_real_punches_alone(self):
		flag_existing("2026-03-01", "2026-03-31")
		kept = [t for t, flag in self._flags().items() if not flag]
		self.assertEqual(len(kept), 2, "one arrival and one departure survive")

	def test_flag_then_unflag_round_trips(self):
		before = self._flags()
		flag_existing("2026-03-01", "2026-03-31")
		self.assertNotEqual(self._flags(), before, "flagging should have changed something")
		unflag_existing()
		self.assertEqual(self._flags(), before, "unflag puts every punch back")

	def test_a_range_that_misses_the_day_touches_nothing(self):
		"""There is no default range, so October can never be reached by accident."""
		before = self._flags()
		flag_existing("2026-04-01", "2026-04-30")
		self.assertEqual(self._flags(), before)

	def test_marking_after_the_flagging_calls_the_day_present(self):
		"""The whole point of the in-between step, end to end.

		Without `flag_existing` the day re-marks as Absent on 0.0 hours, exactly
		as it did before any of this - because the cancel step handed the
		marking job its duplicates back.
		"""
		flag_existing("2026-03-01", "2026-03-31")
		shift = frappe.get_doc("Shift Type", SHIFT)
		shift.enable_auto_attendance = 1
		shift.process_attendance_after = "2026-03-01"
		shift.last_sync_of_checkin = "2026-03-03 23:59:59"
		shift.flags.ignore_permissions = True
		shift.save(ignore_permissions=True)
		shift.process_auto_attendance()
		frappe.db.commit()
		row = frappe.db.get_value("Attendance",
		                          {"employee": self.worker, "attendance_date": getdate(DAY)},
		                          ["status", "working_hours"], as_dict=True)
		self.assertIsNotNone(row, "the day should have been marked")
		self.assertEqual(row.status, "Present")
		self.assertAlmostEqual(row.working_hours, 9.0, places=1)


class TheRuleIsOneRule(FrappeTestCase):
	"""The door, the back-fill and the pay engine must fold the same punches.

	No database. If these three ever disagree, one day reads two ways and a
	disputed payslip cannot be answered.
	"""

	def test_repeat_scans_agrees_with_the_pay_engines_helper(self):
		at = ["09:00:00", "09:00:05", "09:00:09", "09:03:00", "18:00:00"]
		stamps = ["{0} {1}".format(DAY, t) for t in at]
		mine = repeat_scans(stamps)
		kept_by_me = [t for i, t in enumerate(at) if i not in mine]

		minutes = [int(t[:2]) * 60 + int(t[3:5]) for t in at]
		kept_by_engine = collapse_duplicate_punches(minutes)

		self.assertEqual(len(kept_by_me), len(kept_by_engine),
		                 "the two must keep the same number of punches")
		self.assertEqual(kept_by_me, ["09:00:00", "09:03:00", "18:00:00"])

	def test_nothing_in_gives_nothing_out(self):
		self.assertEqual(repeat_scans([]), [])

	def test_a_drifting_chain_keeps_its_real_punches(self):
		"""The batch helper has to measure from the last KEPT punch too.

		Same case as the door's own drifting-chain test. If these two ever
		disagree, flagging stored punches would fold a day one way and the hook
		would fold the next day's another way.
		"""
		at = ["09:00:00", "09:01:30", "09:03:00"]
		stamps = ["{0} {1}".format(DAY, t) for t in at]
		self.assertEqual(repeat_scans(stamps), [1],
		                 "only the middle read repeats; 09:03 stands on its own")

	def test_a_double_read_across_midnight_is_one_punch(self):
		"""Whole date-times, not minutes from midnight.

		The pay engine's helper is handed one day at a time, so it never sees
		this pair; here it would look 1,439 minutes apart and survive.
		"""
		self.assertEqual(repeat_scans(["2026-03-02 23:59:50", "2026-03-03 00:00:20"]), [1])
