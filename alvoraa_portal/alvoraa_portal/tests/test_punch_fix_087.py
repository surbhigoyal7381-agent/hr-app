"""Slice 087: attendance follows the punches.

HR approves a punch fix on the review card; the approval adds one real punch, sets
the ticked ones aside, judges the day from the real punches and writes it. Every
test that proves a refusal has a control beside it that proves the same act works
for the person who may do it. Fixtures are borrowed from the 085 held-day tests:
shift 09:00-18:00, absent under 4 h, half day under 7 h.
"""

import json
import os
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_datetime, nowdate

from alvoraa_portal import attendance_correction as ac
import hrms.alvoraa_hr_core.access as access
from alvoraa_portal import held_day, punch_fix
from alvoraa_portal.tests import test_held_day_085 as hd

REQUEST = "Attendance Request"
CHECKIN = "Employee Checkin"
PKG = os.path.dirname(os.path.dirname(__file__))


def setUpModule():
	hd.setUpModule()
	punch_fix.after_migrate()
	frappe.clear_cache()


def security_lines_from_a_fresh_process(fn):
	"""Run `fn` and return the lines written to the "security" logger, with that logger set back to Frappe's
	own default (ERROR) first. Frappe caches the logger, so once anything in the process has raised it the
	level stays raised; a test that asks `access.security_logger()` itself would raise it too and could not
	tell a code path that never raises it (ALV-391: every such line was thrown away) from one that does."""
	import logging
	seen = []

	class Catch(logging.Handler):
		def emit(self, record):
			seen.append(record.getMessage())

	lg = frappe.logger("security")
	level, handler = lg.level, Catch()
	lg.setLevel(logging.ERROR)
	lg.addHandler(handler)
	try:
		fn()
	finally:
		lg.removeHandler(handler)
		lg.setLevel(level)
	return seen


class PunchFixCase(FrappeTestCase):
	def setUp(self):
		self.h = hd.HeldDayCase("test_held_is_a_status_and_the_fields_exist")
		self.h.setUp()
		h = self.h
		# ALV-430. **This suite tests the compliant workflow, so its company has
		# to choose it.** Asking the employee to confirm a change somebody else
		# made for them is now a per-company setting and it is OFF by default
		# (Surbhi, 22 Nov 2026): a tenant that never asked for it gets the
		# simple workflow. Without this line 23 tests below fail with
		# `0 != 1` on `alvoraa_needs_confirm` - not because the behaviour broke,
		# but because the company opted out of it. Restored after each test so
		# no other suite inherits the choice.
		self._confirm_was = frappe.db.get_value("Company", h.company,
		                                        punch_fix.CONFIRM_SWITCH)
		self.addCleanup(self._put_the_confirm_switch_back, h.company)
		frappe.db.set_value("Company", h.company, punch_fix.CONFIRM_SWITCH, 1,
		                    update_modified=False)
		frappe.clear_cache()
		self.emp, self.hr, self.day = h.worker, h.hr, h.day
		self.emp_user = h._login("emp", ())
		# Linking the login is what gives it the employee role (ERPNext's own hook), so this is
		# a save and not a bare set_value.
		worker = frappe.get_doc("Employee", self.emp)
		worker.user_id, worker.create_user_permission = self.emp_user, 0
		worker.save(ignore_permissions=True)
		# DTC's setting: the day's hours are the sum of each in/out pair, so a break is taken off.
		frappe.db.set_value("Shift Type", hd.SHIFT, "working_hours_calculation_based_on",
		                    "Every Valid Check-in and Check-out")
		frappe.clear_document_cache("Shift Type", hd.SHIFT)
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	# ── fixtures ────────────────────────────────────────────────────────
	def day_of(self, times, employee=None, **extra):
		"""A submitted Attendance with these punches, as ('HH:MM', 'IN'|'OUT'[, device])."""
		employee = employee or self.emp
		names = []
		for t in times:
			doc = frappe.get_doc({"doctype": CHECKIN, "employee": employee, "log_type": t[1],
			                      "time": "%s %s:00" % (self.day, t[0]), "device_id": t[2] if len(t) > 2 else None})
			names.append(doc.insert(ignore_permissions=True).name)
		att = self.h._attendance(employee, **extra)
		att.submit()
		return att.name, names

	def held_three(self):
		return self.day_of([("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")])

	def fix(self, time=None, aside=None, by="Administrator", employee=None, note=None, day=None):
		frappe.set_user(by)
		try:
			doc = frappe.get_doc({"doctype": REQUEST, "employee": employee or self.emp,
			                      "from_date": day or self.day, "to_date": day or self.day,
			                      "reason": "Forgot to Punch In", "explanation": note,
			                      "alvoraa_missing_time": time, "alvoraa_set_aside": ", ".join(aside or []) or None,
			                      "alvoraa_review_status": "Waiting"})
			doc.insert(ignore_permissions=True)
			return doc.name
		finally:
			frappe.set_user("Administrator")

	def confirm_as_employee(self, name):
		"""What the employee's Confirm leaves on the request (the real endpoint is tested in `Confirm`)."""
		frappe.db.set_value(REQUEST, name, {"alvoraa_confirmed_by": "Administrator",
		                                    "alvoraa_confirmed_on": frappe.utils.now_datetime()})

	def decide(self, name, approve=1, by=None, note=None, seen="auto", confirmed=True):
		# V5: approval never waits for the employee's Confirm, so nothing is confirmed first.
		if seen == "auto":
			seen = punch_fix.seen_token(frappe.get_doc(REQUEST, name))
		frappe.set_user(by or self.hr)
		try:
			return ac.decide(name, approve, note, seen)
		finally:
			frappe.set_user("Administrator")

	def row(self, att):
		return frappe.db.get_value("Attendance", att, ["status", "working_hours", "attendance_request",
		                                               "alvoraa_release_how", "alvoraa_release_by"], as_dict=True)

	def added(self, req):
		return frappe.get_all(CHECKIN, filters={punch_fix.ADDED: req}, fields=["*"])

	def refused(self, fn, *needles):
		with self.assertRaises((frappe.ValidationError, frappe.PermissionError)) as cm:
			fn()
		text = str(cm.exception)
		for n in needles:
			self.assertIn(n, text)
		return text


	def _put_the_confirm_switch_back(self, company):
		"""ALV-430. Leave the company exactly as this suite found it, so a
		later suite sharing the fixture is not silently switched on."""
		frappe.db.set_value("Company", company, punch_fix.CONFIRM_SWITCH,
		                    self._confirm_was, update_modified=False)
		frappe.clear_cache()


class Install(PunchFixCase):
	def test_the_nineteen_fields_exist(self):
		"""Eighteen until ALV-430 added the per-company confirm switch on
		`Company`. **Renamed with the number**: a test called "eighteen" that
		asserts nineteen is a sentence that lies to the next reader, and the
		name is what they see first."""
		for dt, fields in punch_fix.FIELDS.items():
			for f in fields:
				self.assertTrue(frappe.db.exists("Custom Field", {"dt": dt, "fieldname": f["fieldname"]}), f["fieldname"])
		self.assertEqual(sum(len(v) for v in punch_fix.FIELDS.values()), 19)

	def test_after_migrate_runs_twice_and_is_wired_to_install_too(self):
		self.assertTrue(punch_fix.after_migrate() and punch_fix.after_migrate())
		hooks = frappe.get_hooks("after_install") + frappe.get_hooks("after_migrate")
		self.assertEqual(hooks.count("alvoraa_portal.punch_fix.after_migrate"), 2)

	def test_the_subclass_is_the_only_override_of_attendance_request(self):
		self.assertEqual(frappe.get_hooks("override_doctype_class")["Attendance Request"],
		                 ["alvoraa_portal.overrides.attendance_request.AlvoraAttendanceRequest"])

	def test_no_ignore_permissions_and_no_cache_in_the_new_module(self):
		src = open(os.path.join(PKG, "punch_fix.py")).read()
		self.assertNotIn("ignore_permissions", src)
		self.assertNotIn("frappe.cache", src)
		self.assertNotIn("allow_guest", src)

	def test_the_patch_marks_old_held_requests_and_runs_twice(self):
		from alvoraa_portal.patches.v1_0 import punch_fix_marks_085_requests_as_held_day as patch_mod
		att, _n = self.held_three()
		req = self.fix("12:40")
		frappe.db.set_value(REQUEST, req, {"alvoraa_for_held_day": 0, "alvoraa_missing_log": "IN"})
		patch_mod.execute()
		patch_mod.execute()
		self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_for_held_day"), 1)


class Kind(PunchFixCase):
	"""AC-2: Arrival, Leaving, Back in after a break, Out for a break."""

	def kind(self, times, at, aside=()):
		att, names = self.day_of(times)
		picked = [names[i] for i in aside]
		log, label, _when = punch_fix.derive(self.emp, self.day, at, picked)
		return log, label

	def test_the_six_rows_of_the_table(self):
		three = [("10:30", "IN"), ("14:00", "OUT"), ("19:30", "OUT")]
		self.assertEqual(self.kind(three, "14:40"), ("IN", "Back in after a break"))

	def test_arrival_before_two_punches(self):
		self.assertEqual(self.kind([("11:15", "IN"), ("19:30", "OUT")], "10:30"), ("IN", "Arrival"))

	def test_arrival_still_when_the_first_is_set_aside(self):
		# 11:15 set aside leaves only 19:30: the added 10:30 comes before it, so it is an arrival.
		self.assertEqual(self.kind([("11:15", "IN"), ("19:30", "OUT")], "10:30", aside=(0,))[1], "Arrival")

	def test_leaving_after_the_last(self):
		self.assertEqual(self.kind([("10:30", "IN")], "19:30"), ("OUT", "Leaving"))

	def test_out_for_a_break_after_the_first_of_three(self):
		three = [("10:30", "IN"), ("14:00", "OUT"), ("19:30", "OUT")]
		self.assertEqual(self.kind(three, "12:00"), ("OUT", "Out for a break"))

	def test_a_single_punch_before_it(self):
		self.assertEqual(self.kind([("19:30", "OUT")], "10:00"), ("IN", "Arrival"))

	def test_the_server_derives_it_and_ignores_the_one_sent(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		frappe.db.set_value(REQUEST, req, "alvoraa_missing_log", "OUT")  # a forged value
		doc = frappe.get_doc(REQUEST, req)
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.alvoraa_missing_log, "IN")


class Raising(PunchFixCase):
	def test_a_time_is_accepted_on_an_ordinary_day_and_stamps_it_not_held(self):
		att, _n = self.day_of([("09:00", "IN"), ("18:00", "OUT")])
		req = self.fix("12:00")
		self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_for_held_day"), 0)

	def test_held_day_request_is_stamped_held_by_the_server_whatever_the_client_says(self):
		att, _n = self.held_three()
		doc = frappe.get_doc({"doctype": REQUEST, "employee": self.emp, "from_date": self.day, "to_date": self.day,
		                      "reason": "Forgot to Punch In", "alvoraa_missing_time": "12:40",
		                      "alvoraa_for_held_day": 0, "alvoraa_review_status": "Waiting"})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.alvoraa_for_held_day, 1)
		ordinary = self.h._employee("Ord")
		self.day_of([("09:00", "IN"), ("18:00", "OUT")], employee=ordinary)
		doc2 = frappe.get_doc({"doctype": REQUEST, "employee": ordinary, "from_date": self.day, "to_date": self.day,
		                       "reason": "Forgot to Punch In", "alvoraa_missing_time": "12:00",
		                       "alvoraa_for_held_day": 1, "alvoraa_review_status": "Waiting"})
		doc2.insert(ignore_permissions=True)
		self.assertEqual(doc2.alvoraa_for_held_day, 0)

	def test_a_punch_within_two_minutes_of_a_counted_one_is_refused_both_ways(self):
		att, _n = self.held_three()
		for t in ("12:01", "11:59", "12:02"):
			self.refused(lambda t=t: self.fix(t), "within 2 minutes")
		self.fix("12:03")  # control: three minutes is a different punch

	def test_a_set_aside_punch_does_not_anchor_the_repeat_check(self):
		att, names = self.held_three()
		self.fix("12:01", aside=[names[1]])  # 12:00 is being set aside, so 12:01 is not a repeat

	def test_a_set_aside_that_leaves_no_punch_is_refused(self):
		att, names = self.day_of([("09:00", "IN")])
		self.refused(lambda: self.fix(aside=[names[0]]), "no punches")

	def test_set_aside_names_must_be_this_employees_on_this_day_and_still_counting(self):
		att, names = self.held_three()
		other = self.h._employee("Other")
		foreign = frappe.get_doc({"doctype": CHECKIN, "employee": other, "log_type": "IN",
		                          "time": "%s 10:00:00" % self.day}).insert(ignore_permissions=True).name
		self.refused(lambda: self.fix("12:40", aside=[foreign]), "not on this day")
		tomorrow = frappe.get_doc({"doctype": CHECKIN, "employee": self.emp, "log_type": "IN",
		                           "time": "%s 10:00:00" % add_days(self.day, 1)}).insert(ignore_permissions=True).name
		self.refused(lambda: self.fix("12:40", aside=[tomorrow]), "not on this day")
		frappe.db.set_value(CHECKIN, names[0], "skip_auto_attendance", 1)
		self.refused(lambda: self.fix("12:40", aside=[names[0]]), "does not count already")
		self.fix("12:40", aside=[names[2]])  # control

	def test_a_final_slip_blocks_a_fix_on_a_day_that_was_not_held_and_creates_nothing(self):
		self.day_of([("09:00", "IN"), ("18:00", "OUT")])
		with patch.object(held_day, "is_in_final_slip", return_value=True):
			self.refused(lambda: self.fix("12:00"), "salary slip that is already final")
		self.assertEqual(frappe.db.count(REQUEST, {"employee": self.emp}), 0)

	def test_a_held_day_on_a_final_slip_can_still_be_asked_about(self):
		self.held_three()
		with patch.object(held_day, "is_in_final_slip", return_value=True):
			self.fix("12:40")  # control: 085's arrear path stays open

	def test_a_day_with_no_attendance_row_is_not_fixable(self):
		self.refused(lambda: self.fix("12:40"), "has not been marked yet")

	def test_a_hand_marked_day_is_not_fixable_and_an_auto_marked_one_is(self):
		# made by hand: no in_time, a named user's row, no request, no leave
		self.day_of([("09:00", "IN"), ("18:00", "OUT")], in_time=False)
		frappe.db.set_value("Attendance", {"employee": self.emp, "attendance_date": self.day}, "owner", self.hr)
		self.refused(lambda: self.fix("12:00"), "marked this day by hand")
		# control: the scheduler's own row (Administrator, in_time set) is fixable
		frappe.db.set_value("Attendance", {"employee": self.emp, "attendance_date": self.day},
		                    {"owner": "Administrator", "in_time": "%s 09:00:00" % self.day})
		self.fix("12:00")

	def test_approved_leave_blocks_without_naming_the_leave_type(self):
		self.held_three()
		with patch.object(punch_fix, "day_state", return_value="leave"):
			text = self.refused(lambda: self.fix("12:40"), "approved leave")
		self.assertNotIn("Casual", text)

	def test_one_waiting_request_per_day_but_declined_and_approved_fixes_do_not_block(self):
		att, names = self.held_three()
		first = self.fix("12:40")
		self.refused(lambda: self.fix("12:50"), "HR has not decided")
		self.decide(first, approve=0, note="Wrong time")
		second = self.fix("12:40")  # a Declined draft no longer blocks (AC-16)
		self.assertNotEqual(first, second)
		self.decide(second)
		self.fix("17:00")  # an Approved punch fix no longer blocks (AC-17)

	def test_an_ordinary_declined_request_still_blocks_an_ordinary_one(self):
		self.day_of([("09:00", "IN"), ("18:00", "OUT")], status="Absent")
		mk = lambda: frappe.get_doc({"doctype": REQUEST, "employee": self.emp, "from_date": self.day,
		                             "to_date": self.day, "reason": "Other", "explanation": "x",
		                             "alvoraa_review_status": "Waiting"}).insert(ignore_permissions=True)
		first = mk()
		frappe.db.set_value(REQUEST, first.name, "alvoraa_review_status", "Declined")
		with self.assertRaises(frappe.ValidationError):
			mk()

	def test_a_manager_can_send_for_a_held_day_but_not_an_ordinary_day_or_a_set_aside(self):
		mgr = self.h._login("mgr", ())
		self.h._employee("Mgr", mgr)
		att, names = self.held_three()
		self.refused(lambda: self.fix("12:40", by=mgr, aside=[names[1]]), "Only the employee")
		ord_emp = self.h._employee("Ord2")
		self.day_of([("09:00", "IN"), ("18:00", "OUT")], employee=ord_emp)
		self.refused(lambda: self.fix("12:00", by=mgr, employee=ord_emp), "Only the employee")
		self.fix("12:40", by=mgr)  # control: a Held day with a time is 085's route and still works


class Limits(PunchFixCase):
	def own_fix(self, day, held=False):
		self.h.day = self.day = day
		self.day_of([("09:00", "IN")] if held else [("09:00", "IN"), ("18:00", "OUT")])
		frappe.set_user(self.emp_user)
		try:
			return frappe.get_doc({"doctype": REQUEST, "employee": self.emp, "from_date": day, "to_date": day,
			                       "reason": "Forgot to Punch In", "alvoraa_missing_time": "12:00",
			                       "alvoraa_review_status": "Waiting"}).insert()
		finally:
			frappe.set_user("Administrator")

	def test_the_monthly_limit_counts_ordinary_day_fixes_and_not_held_day_ones(self):
		self.h.set_switch(1, limit=3)
		for i in (1, 2, 3):
			self.own_fix(add_days(nowdate(), -i))
		with self.assertRaises(frappe.ValidationError) as cm:
			self.own_fix(add_days(nowdate(), -4))
		self.assertIn("requests this month", str(cm.exception))
		# a Held day is accepted at any count
		held = self.own_fix(add_days(nowdate(), -6), held=True)
		self.assertEqual(held.alvoraa_for_held_day, 1)

class Approval(PunchFixCase):
	def test_case_b_adds_one_punch_and_the_day_is_judged_from_real_punches(self):
		att, names = self.held_three()
		req = self.fix("12:40", note="forgot")
		self.assertEqual(self.row(att).status, "Held")
		self.decide(req)
		added = self.added(req)
		self.assertEqual(len(added), 1)
		p = added[0]
		self.assertEqual((p.owner, p.log_type, p.attendance, p.skip_auto_attendance, p.device_id),
		                 (self.hr, "IN", att, 0, None))
		self.assertEqual(str(p.time)[11:16], "12:40")
		self.assertTrue(p.shift)
		row = self.row(att)
		# 09:00-12:00 + 12:40-18:00 = 3h + 5h20m
		self.assertEqual((row.status, round(row.working_hours, 2)), ("Present", 8.33))
		self.assertEqual((row.alvoraa_release_how, row.alvoraa_release_by, row.attendance_request),
		                 ("HR decision", self.hr, req))
		doc = frappe.get_doc(REQUEST, req)
		self.assertEqual(doc.docstatus, 1)
		before, after = json.loads(doc.alvoraa_fix_before), json.loads(doc.alvoraa_fix_after)
		self.assertEqual((before["status"], before["punches"]), ("Held", ["09:00", "12:00", "18:00"]))
		self.assertEqual((after["status"], after["punches"]), ("Present", ["09:00", "12:00", "12:40", "18:00"]))
		self.assertNotIn("forgot", doc.alvoraa_fix_before + doc.alvoraa_fix_after)

	def test_case_a_sets_the_wrong_punch_aside_and_it_stays_on_record(self):
		att, names = self.day_of([("11:15", "IN"), ("19:30", "OUT", "M1")])
		frappe.db.set_value("Attendance", att, {"status": "Present"})
		req = self.fix("09:30", aside=[names[0]])
		out = self.decide(req)
		self.assertEqual(self.row(att).status, "Present")
		self.assertEqual(round(self.row(att).working_hours, 2), 10.0)  # 09:30 to 19:30
		aside = frappe.db.get_value(CHECKIN, names[0], [punch_fix.ASIDE, punch_fix.ASIDE_BY, "skip_auto_attendance"],
		                            as_dict=True)
		self.assertEqual((aside[punch_fix.ASIDE], aside[punch_fix.ASIDE_BY], aside.skip_auto_attendance),
		                 (req, self.hr, 1))
		self.assertTrue(frappe.db.exists(CHECKIN, names[0]))  # kept
		self.assertEqual(len(punch_fix.counted(self.emp, self.day)), 2)
		from alvoraa_portal.payroll_rules_apply import _punches
		self.assertEqual(_punches(self.emp, self.day)[2], 2)  # the engine reads one list
		# An ordinary day: no "Held, now X" release box (it was never held)
		self.assertFalse(self.row(att).alvoraa_release_how)
		self.assertIn("name", out)
		# The approver and the time are on the punch itself (ASIDE_BY, ASIDE_ON). A Version row
		# is NOT asserted: on test_site the save made none (see the implementation notes).
		self.assertTrue(frappe.db.get_value(CHECKIN, names[0], punch_fix.ASIDE_ON))

	def test_a_set_aside_leaves_a_version_row_naming_the_approver(self):
		"""AC-38. Frappe skips Version rows while `frappe.in_test` is true (document.py `_save`:
		`ignore_version = frappe.in_test`), so this switches it off for the approval only."""
		att, names = self.held_three()
		req = self.fix("12:40", aside=[names[1]])
		with patch.object(frappe, "in_test", False):
			self.decide(req)
		versions = frappe.get_all("Version", filters={"ref_doctype": CHECKIN, "docname": names[1]},
		                          fields=["owner"])
		self.assertEqual([v.owner for v in versions], [self.hr])

	def test_only_the_ticked_punches_change(self):
		att, names = self.held_three()
		before = {n: frappe.db.get_value(CHECKIN, n, ["skip_auto_attendance", "time", "log_type"], as_dict=True)
		          for n in names}
		req = self.fix("12:40", aside=[names[1]])
		self.decide(req)
		for n in (names[0], names[2]):
			self.assertEqual(frappe.db.get_value(CHECKIN, n, ["skip_auto_attendance", "time", "log_type"],
			                                     as_dict=True), before[n])

	def test_a_result_below_the_absent_threshold_is_absent(self):
		att, names = self.day_of([("09:00", "IN")])
		req = self.fix("10:00")
		self.decide(req)
		self.assertEqual(self.row(att).status, "Absent")

	def test_an_added_punch_never_triggers_the_machine_release_or_a_second_release(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		before = frappe.db.count("Error Log")
		with patch("frappe.enqueue") as enq:
			self.decide(req)
		self.assertFalse([c for c in enq.call_args_list if "refresh_slip_job" in str(c)])
		self.assertEqual(frappe.db.count("Error Log"), before)
		self.assertEqual(self.row(att).alvoraa_release_how, "HR decision")

	def test_the_preview_and_the_approval_come_from_one_function(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		row = frappe._dict(frappe.db.get_value("Attendance", att, ["*"], as_dict=True))
		with patch.object(punch_fix, "outcome", wraps=punch_fix.outcome) as spy:
			frappe.set_user(self.hr)
			try:
				card = punch_fix.card(frappe.get_doc(REQUEST, req).as_dict())
			finally:
				frappe.set_user("Administrator")
			self.assertTrue(spy.called)
			calls = spy.call_count
			self.decide(req)
			self.assertGreater(spy.call_count, calls)
		self.assertEqual(card["after"]["status"], self.row(att).status)
		self.assertEqual(card["after"]["hours"], round(self.row(att).working_hours, 2))

	def test_a_failure_after_the_insert_leaves_nothing_behind(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		frappe.db.savepoint("t087")
		with patch.object(punch_fix, "_snapshot", side_effect=[json.dumps({}), RuntimeError("boom")]):
			with self.assertRaises(RuntimeError):
				self.decide(req)
		frappe.db.rollback(save_point="t087")  # what the framework does with a failed request
		self.assertEqual(len(self.added(req)), 0)
		self.assertEqual(self.row(att).status, "Held")
		self.assertEqual(frappe.db.get_value(REQUEST, req, "docstatus"), 0)

	def test_the_draft_slip_is_refreshed_and_a_failure_does_not_undo_the_approval(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		with patch.object(held_day, "refresh_draft_slip", side_effect=lambda e, d: "refreshed") as r:
			self.decide(req)
		r.assert_called_once()
		self.assertEqual(self.row(att).status, "Present")

	def test_a_final_slip_blocks_the_approval_of_a_day_that_was_not_held_and_changes_nothing(self):
		att, names = self.day_of([("09:00", "IN"), ("18:00", "OUT")])
		req = self.fix("12:00")
		with patch.object(held_day, "is_in_final_slip", return_value=True):
			self.refused(lambda: self.decide(req), "already final")
		self.assertEqual(len(self.added(req)), 0)
		self.assertEqual(frappe.db.get_value("Attendance", att, "status"), "Present")

	def test_a_held_day_on_a_final_slip_is_approved_the_slip_is_not_touched_and_hr_is_told(self):
		"""085's arrear path (Surbhi, 21 Nov): approved, the slip never touched, flagged for the sheet."""
		att, names = self.held_three()
		req = self.fix("12:40")
		with patch.object(held_day, "is_in_final_slip", return_value=True), \
				patch.object(frappe, "get_doc", wraps=frappe.get_doc) as gd:
			out = self.decide(req)
		self.assertTrue(out["slip_final"])
		self.assertEqual(out["day_status"], "Present")
		self.assertEqual(self.row(att).alvoraa_release_how, "HR decision")
		self.assertFalse([c for c in gd.call_args_list if c.args and c.args[0] == "Salary Slip"])

	def test_a_leaver_cannot_be_approved(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		frappe.db.set_value("Employee", self.emp, "status", "Left")
		self.refused(lambda: self.decide(req), "has left")
		self.assertEqual(len(self.added(req)), 0)

	def test_decide_twice_adds_one_punch(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		seen = punch_fix.seen_token(frappe.get_doc(REQUEST, req))
		self.decide(req, seen=seen)
		self.refused(lambda: self.decide(req, seen=seen), "already been decided")
		self.assertEqual(len(self.added(req)), 1)

	def test_the_auto_attendance_job_after_the_approval_makes_no_second_row_and_takes_no_punch(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		self.decide(req)
		added = self.added(req)[0]
		self.assertEqual(added.attendance, att)  # linked in the same transaction, so the job skips it
		self.assertEqual(frappe.db.count("Attendance", {"employee": self.emp, "attendance_date": self.day,
		                                                "docstatus": ("<", 2)}), 1)

	def test_a_declined_fix_changes_nothing_and_needs_a_reason_and_no_token(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		self.refused(lambda: self.decide(req, approve=0, note="", seen=None), "say why")
		self.decide(req, approve=0, note="That time is wrong", seen=None)
		self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_review_status"), "Declined")
		self.assertEqual(len(self.added(req)), 0)
		self.assertEqual(self.row(att).status, "Held")

	def test_cancelling_an_approved_fix_is_refused(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		self.decide(req)
		frappe.set_user("Administrator")
		self.refused(lambda: frappe.get_doc(REQUEST, req).cancel(), "Raise a new request")
		self.assertEqual(len(self.added(req)), 1)

	def test_rollback_is_a_new_request_that_sets_the_added_punch_aside(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		self.decide(req)
		added = self.added(req)[0].name
		again = self.fix(aside=[added])
		self.decide(again)
		self.assertTrue(frappe.db.exists(CHECKIN, added))  # never deleted
		self.assertEqual(frappe.db.get_value(CHECKIN, added, punch_fix.ASIDE), again)
		self.assertEqual(self.row(att).status, "Held")  # back to the three, odd again

	def test_a_missing_shift_on_the_day_is_refused_with_the_085_words(self):
		att, names = self.held_three()
		frappe.db.set_value("Attendance", att, "shift", None)
		req = self.fix("12:40")
		self.refused(lambda: self.decide(req), "no shift")


class OneDoor(PunchFixCase):
	def test_desk_submit_is_refused_and_the_control_works_through_decide(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		frappe.set_user(self.hr)
		try:
			self.refused(lambda: frappe.get_doc(REQUEST, req).submit(), "review card")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(REQUEST, req, "docstatus"), 0)
		self.decide(req)

	def test_decide_without_the_token_or_with_a_stale_one_is_refused(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		self.refused(lambda: self.decide(req, seen=None), "changed after you opened it")
		old = punch_fix.seen_token(frappe.get_doc(REQUEST, req))
		# a machine punch arrives after the card was opened
		frappe.get_doc({"doctype": CHECKIN, "employee": self.emp, "log_type": "IN",
		                "time": "%s 15:00:00" % self.day}).insert(ignore_permissions=True)
		self.refused(lambda: self.decide(req, seen=old), "changed after you opened it")
		self.assertEqual(len(self.added(req)), 0)

	def test_an_edit_of_the_draft_after_the_card_was_opened_makes_the_token_stale(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		old = punch_fix.seen_token(frappe.get_doc(REQUEST, req))
		frappe.db.set_value(REQUEST, req, "alvoraa_missing_time", "13:00")  # changes `modified`
		self.refused(lambda: self.decide(req, seen=old), "changed after you opened it")

	def test_an_ordinary_request_still_decides_without_a_token(self):
		self.day_of([("09:00", "IN"), ("18:00", "OUT")], status="Absent")
		doc = frappe.get_doc({"doctype": REQUEST, "employee": self.emp, "from_date": self.day,
		                      "to_date": self.day, "reason": "Other", "explanation": "x",
		                      "alvoraa_review_status": "Waiting"}).insert(ignore_permissions=True)
		frappe.set_user(self.hr)
		try:
			ac.decide(doc.name, 0, "No")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(REQUEST, doc.name, "alvoraa_review_status"), "Declined")

	def test_send_is_post_only(self):
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func.get(punch_fix.send), ["POST"])


class WhoMayDecide(PunchFixCase):
	def test_hr_cannot_approve_their_own_day_at_decide_before_submit_or_the_punch_insert(self):
		hr_emp = frappe.db.get_value("Employee", {"user_id": self.hr}, "name")
		att, names = self.day_of([("09:00", "IN")], employee=hr_emp)
		req = self.fix("18:00", employee=hr_emp, by="Administrator")
		self.refused(lambda: self.decide(req, by=self.hr), "own request")
		# second lock: the insert as that user is refused by the checkin permission rule
		from alvoraa_portal.field_app_access import checkin_has_permission
		frappe.set_user(self.hr)
		try:
			probe = frappe.get_doc({"doctype": CHECKIN, "employee": hr_emp, "log_type": "OUT",
			                        "time": "%s 18:00:00" % self.day})
			self.assertFalse(checkin_has_permission(probe, ptype="create", user=self.hr))
		finally:
			frappe.set_user("Administrator")
		# control: another HR person in the same company decides it
		self.decide(req, by=self.h.hr2)

	def test_the_punch_insert_is_a_lock_of_its_own_when_the_other_two_are_switched_off(self):
		"""Own day, third lock (SEC-3): with `refuse_own_decision` (decide and the submit hook)
		doing nothing, the insert as the approver is still refused by the checkin permission rule."""
		hr_emp = frappe.db.get_value("Employee", {"user_id": self.hr}, "name")
		att, names = self.day_of([("09:00", "IN")], employee=hr_emp)
		req = self.fix("18:00", employee=hr_emp)
		with patch.object(access, "refuse_own_decision", lambda *a, **k: None):
			with self.assertRaises(frappe.PermissionError):
				self.decide(req, by=self.hr)
		self.assertEqual(len(self.added(req)), 0)

	def test_the_raiser_cannot_decide(self):
		att, names = self.held_three()
		req = self.fix("12:40", by=self.hr)  # HR raised it for the employee (085 route, a Held day)
		self.refused(lambda: self.decide(req, by=self.hr))
		self.decide(req, by=self.h.hr2)

	def test_a_login_with_the_submit_right_but_no_hr_role_is_refused(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		sup = self.h._login("sup", ())
		self.h._employee("Sup", sup)
		self.refused(lambda: self.decide(req, by=sup))
		with patch.object(frappe, "get_roles", return_value=["Employee"]):
			with self.assertRaises(frappe.PermissionError):
				doc = frappe.get_doc(REQUEST, req)
				doc.flags.punch_fix_decided = True
				punch_fix.before_submit(doc)

	def test_hr_of_another_company_is_refused(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		other_hr = self.h._login("hrother", ("HR Manager",))
		self.h._employee("HrO", other_hr, company=self.h.other_company)
		self.refused(lambda: self.decide(req, by=other_hr))
		self.assertEqual(len(self.added(req)), 0)

	def test_an_hr_login_with_no_company_and_no_branch_decides_nothing(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		nobody = self.h._login("hrnone", ("HR Manager",))  # no Employee record at all
		self.refused(lambda: self.decide(req, by=nobody))

	def test_the_added_punch_belongs_to_the_approver_not_administrator(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		self.decide(req, by=self.h.hr2)
		self.assertEqual(self.added(req)[0].owner, self.h.hr2)


class Marks(PunchFixCase):
	def approved(self):
		att, names = self.held_three()
		req = self.fix("12:40", aside=[names[1]])
		self.decide(req)
		return att, names, req, self.added(req)[0].name

	def test_marks_cannot_be_written_outside_an_approval(self):
		att, names = self.held_three()
		real = self.fix("12:40")
		frappe.set_user(self.hr)
		try:
			doc = frappe.get_doc(CHECKIN, names[0])
			doc.update({punch_fix.ASIDE: real, "skip_auto_attendance": 1})
			self.refused(lambda: doc.save(), "cannot be changed")
			self.refused(lambda: frappe.get_doc({"doctype": CHECKIN, "employee": self.emp, "log_type": "IN",
			                                     "time": "%s 15:00:00" % self.day,
			                                     punch_fix.ADDED: real}).insert(), "cannot be changed")
		finally:
			frappe.set_user("Administrator")

	def test_a_marked_punch_cannot_be_edited_cleared_or_deleted_even_by_a_system_manager(self):
		att, names, req, added = self.approved()
		sm = self.h._login("sm", ("System Manager",))
		for user in (self.hr, sm):
			frappe.set_user(user)
			try:
				doc = frappe.get_doc(CHECKIN, names[1])
				doc.skip_auto_attendance = 0  # clearing the flag on a set-aside punch
				self.refused(lambda: doc.save(), "cannot be changed")
				doc = frappe.get_doc(CHECKIN, added)
				doc.log_type = "IN"  # the approval stored OUT (12:00 is set aside, so 12:40 follows one punch)
				self.refused(lambda: doc.save(), "cannot be changed")
				self.refused(lambda: frappe.delete_doc(CHECKIN, added), "cannot be changed")
			finally:
				frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists(CHECKIN, added))

	def test_administrator_may_and_it_is_logged(self):
		att, names, req, added = self.approved()
		frappe.set_user("Administrator")
		import logging
		seen = []

		class Catch(logging.Handler):
			def emit(self, record):
				seen.append(record.getMessage())

		lg, handler = access.security_logger(), Catch()
		lg.addHandler(handler)
		try:
			doc = frappe.get_doc(CHECKIN, added)
			doc.log_type = "IN"
			doc.save()
		finally:
			lg.removeHandler(handler)
		self.assertTrue(any("Administrator" in m for m in seen), seen)  # really written, not just called

	def test_an_unmarked_punch_edits_as_before(self):
		att, names = self.held_three()
		frappe.set_user(self.hr)
		try:
			doc = frappe.get_doc(CHECKIN, names[0])
			doc.log_type = "OUT"
			doc.save()
		finally:
			frappe.set_user("Administrator")


class Engine(PunchFixCase):
	def test_punches_skip_a_set_aside_punch_and_nothing_else(self):
		from alvoraa_portal.payroll_rules_apply import _punches
		att, names = self.held_three()
		self.assertEqual(_punches(self.emp, self.day)[2], 3)
		frappe.db.set_value(CHECKIN, names[1], punch_fix.ASIDE, "X")
		self.assertEqual(_punches(self.emp, self.day)[2], 2)
		# a repeat scan (skip_auto_attendance only) is still counted as it is today
		frappe.db.set_value(CHECKIN, names[1], punch_fix.ASIDE, None)
		frappe.db.set_value(CHECKIN, names[1], "skip_auto_attendance", 1)
		self.assertEqual(_punches(self.emp, self.day)[2], 3)

	def test_without_the_column_the_reader_is_unchanged(self):
		from alvoraa_portal.payroll_rules_apply import _punches
		att, names = self.held_three()
		frappe.db.set_value(CHECKIN, names[1], punch_fix.ASIDE, "X")
		with patch.object(frappe.db, "has_column", return_value=False):
			self.assertEqual(_punches(self.emp, self.day)[2], 3)

	def test_alv410_an_approved_fix_is_no_longer_held_by_the_engine(self):
		from alvoraa_portal.payroll_rules_apply import judge, prepare, rule_set_for
		company = self.h.company
		rs = frappe.get_doc({"doctype": "Alvoraa Payroll Rule Set", "company": company, "enabled": 1,
		                     "grace_minutes": 6, "free_reds_per_month": 2, "special_day_multiplier": 2,
		                     "leave_threshold_days": 15, "accrual_month_days": 30,
		                     "slabs": [{"percent_from": 0, "percent_to": 50, "quarters_off": 2, "raises_red": 0},
		                               {"percent_from": 50, "percent_to": 90, "quarters_off": 1, "raises_red": 0},
		                               {"percent_from": 90, "percent_to": 98.9, "quarters_off": 0, "raises_red": 1},
		                               {"percent_from": 98.9, "percent_to": 100, "quarters_off": 0, "raises_red": 0}],
		                     "mark_rates": [{"grade": "Junior", "amount_per_mark": 100}]})
		rs.flags.ignore_permissions = True
		rs.insert()
		frappe.clear_document_cache("Alvoraa Payroll Rule Set", rs.name)
		att, names = self.held_three()
		a = frappe.db.get_value("Attendance", att, ["name", "employee", "attendance_date", "status", "shift", "company"],
		                        as_dict=True)
		ctx = prepare(rule_set_for(company), a.attendance_date, a.attendance_date)
		self.assertTrue(judge(a, ctx).held)  # control: three punches are held today
		req = self.fix("12:40")
		self.decide(req)
		a = frappe.db.get_value("Attendance", att, ["name", "employee", "attendance_date", "status", "shift",
		                                            "company"], as_dict=True)
		self.assertFalse(judge(a, ctx).held)
		self.assertEqual(frappe.db.get_value("Attendance", att, "alvoraa_held"), 0)

	def test_alv410_the_typed_time_is_not_counted_twice(self):
		att, names = self.day_of([("09:00", "IN")])
		req = self.fix("18:00")
		self.decide(req)
		self.assertEqual(round(self.row(att).working_hours, 2), 9.0)
		src = open(os.path.join(PKG, "punch_fix.py")).read()
		self.assertNotIn("release_by_hr", src)
		self.assertNotIn("def release_by_hr", open(os.path.join(PKG, "held_day.py")).read())


class Screens(PunchFixCase):
	def test_to_review_gives_the_card_and_no_photo_or_location_key(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		frappe.set_user(self.hr)
		try:
			rows = [r for r in ac.to_review() if r["name"] == req]
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(len(rows), 1)
		row = rows[0]
		self.assertTrue(row["punch_fix"])
		card = row["card"]
		self.assertEqual((card["now"]["status"], card["after"]["status"], card["kind"]),
		                 ("Held", "Present", "Back in after a break"))
		self.assertTrue(card["seen"] and not card["blocked"])
		flat = json.dumps(row, default=str).lower()
		for bad in ("photo", "latitude", "longitude"):
			self.assertNotIn(bad, flat)
		self.assertNotIn("alvoraa_set_aside", row)

	def test_a_manager_sees_the_row_but_cannot_decide_it(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		doc = frappe._dict(frappe.get_doc(REQUEST, req).as_dict())
		mgr = self.h._login("mgr2", ())
		self.assertEqual(ac.not_yours_yet(doc, "Manager", mgr), "Only HR decides a punch fix.")
		self.assertIsNone(ac.not_yours_yet(doc, "HR", self.hr))

	def test_send_creates_one_waiting_request_for_the_callers_own_record(self):
		att, names = self.held_three()
		frappe.set_user(self.emp_user)
		try:
			self.refused(lambda: punch_fix.send(self.day, "12:40", None, None), "A reason is needed")
			self.refused(lambda: punch_fix.send(self.day, "12:40", None, "   "), "A reason is needed")
			self.assertEqual(frappe.db.count(REQUEST, {"employee": self.emp}), 0)
			out = punch_fix.send(self.day, "12:40", None, "forgot the lunch scan")
			self.refused(lambda: punch_fix.send(self.day, "12:40,13:00"), "One punch per request")
			self.refused(lambda: punch_fix.send(self.day, None, None), "Enter the time first")
		finally:
			frappe.set_user("Administrator")
		doc = frappe.get_doc(REQUEST, out["name"])
		self.assertEqual((doc.employee, doc.alvoraa_review_status, doc.alvoraa_missing_log, doc.alvoraa_for_held_day,
		                  doc.reason, doc.explanation),
		                 (self.emp, "Waiting", "IN", 1, "Forgot to Punch In", "forgot the lunch scan"))
		self.assertEqual(frappe.db.count(REQUEST, {"employee": self.emp}), 1)

	def test_send_for_a_blocked_day_creates_no_request(self):
		frappe.set_user(self.emp_user)
		try:
			self.refused(lambda: punch_fix.send(self.day, "12:40", None, "forgot"), "has not been marked yet")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count(REQUEST, {"employee": self.emp}), 0)

	def test_a_note_is_in_no_refusal_and_no_log_line(self):
		att, names = self.held_three()
		marker = "ZZMARKER087"
		req = self.fix("12:40", note=marker)
		with patch.object(punch_fix, "_snapshot", side_effect=RuntimeError("boom")):
			with self.assertRaises(RuntimeError):
				self.decide(req)
		self.assertEqual(frappe.db.count("Error Log", {"error": ("like", "%" + marker + "%")}), 0)

	def test_the_report_counts_this_months_punch_fixes_by_company_and_state(self):
		from alvoraa_portal.alvoraa_portal.report.punch_fixes_this_month import punch_fixes_this_month as rpt

		def mine():
			rows = rpt.execute()[1]
			hit = [r for r in rows if r["company"] == self.h.company]
			return hit[0] if hit else {"approved": 0, "waiting": 0, "declined": 0, "withdrawn": 0}

		att, names = self.held_three()
		before = mine()
		a = self.fix("12:40")
		self.decide(a)
		self.fix("17:00")  # waiting
		frappe.set_user("Administrator")
		after = mine()
		self.assertEqual((after["approved"] - before["approved"], after["waiting"] - before["waiting"]), (1, 1))
		self.assertTrue(frappe.db.exists("Report", "Punch fixes this month"))


class DaySheet(PunchFixCase):
	def sheet(self, date=None):
		frappe.set_user(self.emp_user)
		try:
			return punch_fix.day_sheet(date or self.day)
		finally:
			frappe.set_user("Administrator")

	def test_the_sheet_gives_punches_with_marks_and_the_shift_and_no_photo_or_location(self):
		att, names = self.day_of([("09:00", "IN"), ("12:00", "OUT", "M1"), ("18:00", "OUT")])
		out = self.sheet()
		self.assertIsNone(out["blocked"])
		self.assertEqual((out["shift"]["start"], out["shift"]["end"], out["shift"]["expected"]), ("09:00", "18:00", 9.0))
		self.assertEqual([(p["time"], p["counted"]) for p in out["punches"]],
		                 [("09:00", True), ("12:00", True), ("18:00", True)])
		self.assertEqual(out["punches"][1]["source"], "Machine")
		flat = json.dumps(out, default=str).lower()
		for bad in ("photo", "latitude", "longitude"):
			self.assertNotIn(bad, flat)

	def test_the_sheet_says_why_a_day_cannot_be_fixed_and_shows_the_request_state(self):
		self.day_of([("09:00", "IN"), ("18:00", "OUT")])
		req = self.fix("12:00", note="forgot")
		out = self.sheet()
		self.assertEqual((out["request"]["state"], out["request"]["time"], out["request"]["note"]),
		                 ("waiting", "12:00", "forgot"))
		with patch.object(held_day, "is_in_final_slip", return_value=True):
			out = self.sheet()
		self.assertEqual(out["blocked"], "slip")
		self.assertIn("already final", out["blocked_text"])

	def test_an_approved_fix_shows_added_and_set_aside_marks_to_the_employee(self):
		att, names = self.held_three()
		req = self.fix("12:40", aside=[names[1]])
		self.decide(req, note="ok")
		out = self.sheet()
		self.assertEqual(out["request"]["state"], "approved")
		marks = {p["time"]: (p["added"], p["aside"], p["counted"]) for p in out["punches"]}
		self.assertEqual(marks["12:40"], (True, False, True))
		self.assertEqual(marks["12:00"], (False, True, False))

	def test_the_sheet_is_for_the_callers_own_record_only(self):
		other = self.h._employee("Peer")
		self.day_of([("09:00", "IN"), ("18:00", "OUT")], employee=other)
		self.assertEqual(self.sheet().get("punches"), None)  # the caller's own day has no row

	def test_the_card_carries_the_after_times_the_shift_and_the_machine_note(self):
		att, names = self.day_of([("11:15", "IN"), ("19:30", "OUT", "M1")])
		req = self.fix("09:30", aside=[names[1]])
		frappe.set_user(self.hr)
		try:
			card = punch_fix.card(frappe.get_doc(REQUEST, req).as_dict())
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(card["sets_aside_machine"])
		self.assertEqual(card["now"]["shift"]["start"], "09:00")
		# AC-27: the set-aside 19:30 stays on the If-approved side, flagged so the screen strikes it through
		self.assertEqual([(p["time"], p["added"], bool(p.get("aside"))) for p in card["after"]["punches"]],
		                 [("09:30", True, False), ("11:15", False, False), ("19:30", False, True)])
		self.assertEqual([p["time"] for p in card["now"]["punches"] if p["ticked"]], ["19:30"])


class ReasonOnEveryRequest(PunchFixCase):
	"""ALV-418 (counsel, 21 Nov): a reason on every request, a Held day too. Reverses PRIV-2."""

	def test_send_needs_a_reason_on_an_ordinary_day_and_on_a_held_day(self):
		self.day_of([("09:00", "IN"), ("18:00", "OUT")])
		frappe.set_user(self.emp_user)
		try:
			self.refused(lambda: punch_fix.send(self.day, "12:00", None, ""), "A reason is needed")
			out = punch_fix.send(self.day, "12:00", None, "went to the bank")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(REQUEST, out["name"], "explanation"), "went to the bank")

	def test_a_held_day_takes_a_reason_through_the_085_form_and_refuses_none(self):
		self.held_three()
		frappe.set_user(self.emp_user)
		try:
			self.refused(lambda: ac.raise_correction(self.day, missing_time="12:40", missing_log="IN"), "A reason is needed")
			out = ac.raise_correction(self.day, explanation="Ran out for lunch", missing_time="12:40", missing_log="IN")
		finally:
			frappe.set_user("Administrator")
		doc = frappe.get_doc(REQUEST, out["name"])
		self.assertEqual((doc.explanation, doc.reason), ("Ran out for lunch", "Forgot to Punch In"))  # the auto-picked reason holds no text

	def test_somebody_filing_for_the_employee_needs_a_reason_on_a_held_day(self):
		"""`raise_for_report` is the door for a manager and for HR; HR is used here because the
		manager's insert right needs a User Permission this fixture does not make. Slice 086 (ALV-425): HR
		may file only for a direct report, so the HR person is made this employee's manager first."""
		self.held_three()
		boss = frappe.get_doc("Employee", self.emp)
		boss.reports_to = self.h.hr_emp
		boss.save(ignore_permissions=True)
		frappe.set_user(self.hr)
		try:
			with patch.object(ac, "manager_on_behalf_on", return_value=True):
				self.refused(lambda: ac.raise_for_report(self.emp, self.day, missing_time="12:40", missing_log="IN"), "A reason is needed")
				out = ac.raise_for_report(self.emp, self.day, explanation="He told me", missing_time="12:40", missing_log="IN")
		finally:
			frappe.set_user("Administrator")
		self.assertIn("He told me", frappe.db.get_value(REQUEST, out["name"], "explanation"))
		self.assertEqual(frappe.db.get_value(REQUEST, out["name"], "alvoraa_needs_confirm"), 1)

	def test_a_reason_that_would_empty_itself_is_refused_not_stored(self):
		"""ALV-436. The fault: Frappe cleans every Small Text on save and removes anything
		shaped like a tag, so `<machine down>` was stored as nothing at all - AFTER the "a
		reason is needed" refusal above had already passed. A mandatory reason silently
		emptying itself is the worst shape this bug could take, because the reason is the
		evidence counsel cleared DTC and Grace on.

		Asserted from both sides, the habit this file keeps: the brackets are refused AND an
		ordinary reason is stored exactly as typed. A test that only proves the refusal
		passes just as well on code that refuses everything."""
		self.day_of([("09:00", "IN"), ("18:00", "OUT")])
		frappe.set_user(self.emp_user)
		try:
			self.refused(lambda: punch_fix.send(self.day, "12:00", None, "<machine down>"),
			             "without < and >")
			self.refused(lambda: punch_fix.send(self.day, "12:00", None, "Punch missed <not my fault>"),
			             "without < and >")
			out = punch_fix.send(self.day, "12:00", None, "machine 9 > 8 was down & I told HR")
		finally:
			frappe.set_user("Administrator")
		# The control: what a person types is what payroll reads, character for character.
		self.assertEqual(frappe.db.get_value(REQUEST, out["name"], "explanation"),
		                 "machine 9 > 8 was down & I told HR")

	def test_nothing_was_written_by_the_refused_attempt(self):
		"""ALV-436, the half that matters to an auditor: a refusal must leave no row behind."""
		self.day_of([("09:00", "IN"), ("18:00", "OUT")])
		before = frappe.db.count(REQUEST)
		frappe.set_user(self.emp_user)
		try:
			self.refused(lambda: punch_fix.send(self.day, "12:00", None, "<machine down>"),
			             "without < and >")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count(REQUEST), before,
		                 "a request was stored for a reason that was refused")


class Confirm(PunchFixCase):
	"""ALV-419: a request somebody else filed for the employee waits for their Confirm."""

	def filed_by_hr(self):
		att, names = self.held_three()
		return att, self.fix("12:40", by=self.hr, note="HR typed it")

	def test_a_request_filed_by_hr_or_a_manager_needs_confirm_and_one_the_employee_files_does_not(self):
		att, names = self.held_three()
		frappe.set_user(self.emp_user)
		try:
			own = punch_fix.send(self.day, "17:00", None, "my own")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(REQUEST, own["name"], "alvoraa_needs_confirm"), 0)
		frappe.db.set_value(REQUEST, own["name"], "alvoraa_review_status", "Withdrawn")  # one open request per day
		req = self.fix("12:40", by=self.hr, note="HR typed it")
		self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_needs_confirm"), 1)
		# Administrator is the one exception
		frappe.db.set_value(REQUEST, req, "alvoraa_review_status", "Withdrawn")
		self.assertEqual(frappe.db.get_value(REQUEST, self.fix("12:40"), "alvoraa_needs_confirm"), 0)

	def test_a_managers_addition_goes_straight_to_hr_and_an_hr_filing_still_waits(self):
		"""Counsel, 21 Nov (manager additions)."""
		mgr = self.h._login("mgradd", ())
		self.h._employee("Mgradd", mgr)
		att, names = self.held_three()
		added = self.fix("12:40", by=mgr, note="He told me")
		self.assertEqual(frappe.db.get_value(REQUEST, added, "alvoraa_needs_confirm"), 0)
		self.decide(added, by=self.hr, confirmed=False)  # no Confirm asked for, and none needed
		self.assertEqual(len(self.added(added)), 1)
		# a manager cannot set a punch aside at all (validate refuses it)
		self.refused(lambda: self.fix(aside=[names[1]], by=mgr), "Only the employee")
		# HR filing the same still waits
		att2, names2 = self.held_three_on(add_days(self.day, -1))
		waiting = self.fix("12:40", by=self.hr, note="HR typed it")
		self.assertEqual(frappe.db.get_value(REQUEST, waiting, "alvoraa_needs_confirm"), 1)

	def held_three_on(self, day):
		self.h.day = self.day = day
		return self.day_of([("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")])

	def test_approval_never_waits_for_the_employee_and_confirm_can_come_after(self):
		att, req = self.filed_by_hr()
		self.decide(req, by=self.h.hr2)  # V5: no Confirm needed to approve
		self.assertEqual(len(self.added(req)), 1)
		self.assertEqual(self.row(att).status, "Present")
		self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_needs_confirm"), 1)  # unconfirmed: pay not locked yet
		frappe.set_user(self.emp_user)
		try:
			punch_fix.confirm(req, 1)  # after approval
		finally:
			frappe.set_user("Administrator")
		row = frappe.db.get_value(REQUEST, req, ["alvoraa_confirmed_by", "alvoraa_confirmed_on", "docstatus"], as_dict=True)
		self.assertEqual((row.alvoraa_confirmed_by, bool(row.alvoraa_confirmed_on), row.docstatus), (self.emp_user, True, 1))

	def not_right(self, req, reason="I was back by 12:50", time="12:50"):
		frappe.set_user(self.emp_user)
		try:
			return punch_fix.confirm(req, 0, reason, time)
		finally:
			frappe.set_user("Administrator")

	def test_not_right_declines_it_and_files_the_employees_own_time_in_its_place(self):
		att, req = self.filed_by_hr()
		out = self.not_right(req)
		row = frappe.db.get_value(REQUEST, req, ["alvoraa_review_status", "alvoraa_review_note", "alvoraa_reviewed_by"], as_dict=True)
		self.assertEqual((row.alvoraa_review_status, row.alvoraa_review_note, row.alvoraa_reviewed_by),
		                 ("Declined", "I was back by 12:50", self.emp_user))
		new = frappe.get_doc(REQUEST, out["replacement"])
		self.assertEqual((new.employee, new.alvoraa_review_status, str(new.alvoraa_missing_time)[:5], new.alvoraa_replaces,
		                  new.alvoraa_needs_confirm, new.explanation, new.owner),
		                 (self.emp, "Waiting", "12:50", req, 0, "I was back by 12:50", self.emp_user))
		self.assertEqual(self.row(att).status, "Held")

	def test_the_time_is_required_when_one_was_sent_and_must_differ_and_fit(self):
		att, req = self.filed_by_hr()
		frappe.set_user(self.emp_user)
		try:
			self.refused(lambda: punch_fix.confirm(req, 0, "wrong", ""), "Enter the time first")
			self.refused(lambda: punch_fix.confirm(req, 0, "wrong", "12:40"), "time that was sent")
			self.refused(lambda: punch_fix.confirm(req, 0, "wrong", "12:01"), "within 2 minutes")
			self.refused(lambda: punch_fix.confirm(req, 0, " ", "12:50"), "Say what is not right")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_review_status"), "Waiting")  # every refusal left it alone
		self.assertEqual(frappe.db.count(REQUEST, {"alvoraa_replaces": req}), 0)

	def test_a_filed_set_aside_has_no_time_and_not_right_just_declines(self):
		att, names = self.held_three()
		# Today only Administrator can file a set-aside for somebody (validate refuses it from HR and managers), so the
		# Confirm flag is set by hand to reach the screen's "set-aside, no time" branch.
		req = self.fix(aside=[names[1]], note="wrong scan")
		frappe.db.set_value(REQUEST, req, "alvoraa_needs_confirm", 1)
		out = self.not_right(req, "that scan was right", "")
		self.assertIsNone(out["replacement"])
		self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_review_status"), "Declined")

	def test_decline_and_replacement_are_one_transaction(self):
		att, req = self.filed_by_hr()
		frappe.db.savepoint("t087nr")
		with patch.object(punch_fix, "_replacement", side_effect=RuntimeError("boom")):
			with self.assertRaises(RuntimeError):
				self.not_right(req)
		self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_review_status"), "Waiting")  # the decline was undone
		frappe.db.rollback(save_point="t087nr")

	def test_the_replacement_does_not_count_against_the_monthly_limit_and_the_link_is_the_servers(self):
		# An ORDINARY day: a request for a Held day is outside the limit anyway, so only here does the exemption matter.
		# Today only Administrator files a time for somebody on an ordinary day, so the Confirm flag is set by hand.
		first_day = self.day
		self.day_of([("09:00", "IN"), ("18:00", "OUT")])
		req = self.fix("12:00")
		frappe.db.set_value(REQUEST, req, "alvoraa_needs_confirm", 1)
		self.h.set_switch(1, limit=1)
		self.h.day = self.day = add_days(first_day, -1)
		self.day_of([("09:00", "IN"), ("18:00", "OUT")])
		frappe.set_user(self.emp_user)
		try:
			punch_fix.send(self.day, "12:00", None, "my own")  # uses the limit of 1
		finally:
			frappe.set_user("Administrator")
		self.h.day = self.day = add_days(first_day, -2)
		self.day_of([("09:00", "IN"), ("18:00", "OUT")])
		frappe.set_user(self.emp_user)
		try:
			with self.assertRaises(frappe.ValidationError) as cm:  # control: a second counted request is refused
				punch_fix.send(self.day, "13:30", None, "a second one")
			self.assertIn("requests this month", str(cm.exception))
		finally:
			frappe.set_user("Administrator")
		self.day = self.h.day = first_day
		frappe.db.set_value(REQUEST, req, "alvoraa_review_status", "Waiting")
		out = self.not_right(req, "I was back by 12:50", "12:50")  # the replacement is allowed with the limit used up
		self.assertTrue(out["replacement"])
		fake = frappe.new_doc(REQUEST)
		fake.update({"employee": self.emp, "alvoraa_replaces": req})
		punch_fix._own_the_confirm_fields(fake, None)  # a client value is dropped
		self.assertIsNone(fake.alvoraa_replaces)

	def test_the_day_sheet_and_the_card_carry_what_the_v4_screens_say(self):
		att, req = self.filed_by_hr()
		frappe.set_user(self.emp_user)
		try:
			sheet = punch_fix.day_sheet(self.day)["request"]
		finally:
			frappe.set_user("Administrator")
		self.assertEqual((sheet["item"]["kind"], sheet["item"]["time"], sheet["item"]["label"], sheet["filer_reason"], sheet["filed_by"]),
		                 ("add", "12:40", "Back in after a break", "HR typed it", "HR"))
		self.assertIsNone(sheet["filed_by_name"])  # the employee is not told which HR person (decision 7)
		frappe.set_user(self.hr)
		try:
			card = punch_fix.card(frappe.get_doc(REQUEST, req).as_dict())
		finally:
			frappe.set_user("Administrator")
		self.assertEqual((card["filed"]["by"], bool(card["filed"]["name"]), card["filed"]["reason"]), ("HR", True, "HR typed it"))
		out = self.not_right(req)
		frappe.set_user(self.emp_user)
		try:
			after = punch_fix.day_sheet(self.day)["request"]
		finally:
			frappe.set_user("Administrator")
		self.assertEqual((after["name"], after["replaces"]["time"], after["replaces"]["filed_by"]), (out["replacement"], "12:40", "HR"))
		frappe.set_user(self.hr)
		try:
			card2 = punch_fix.card(frappe.get_doc(REQUEST, out["replacement"]).as_dict())
		finally:
			frappe.set_user("Administrator")
		self.assertEqual((card2["replaces"]["time"], card2["replaces"]["by"], card2["awaiting_confirm"]), ("12:40", "HR", False))

	def test_the_declined_request_reads_as_the_employees_own_words(self):
		att, req = self.filed_by_hr()
		self.not_right(req, "I was not there")
		frappe.set_user(self.emp_user)
		try:
			# the replacement is newest; look at the old one through the same field the sheet uses
			rows = frappe.get_all(REQUEST, filters={"name": req}, fields=["alvoraa_reviewed_by"])
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(rows[0].alvoraa_reviewed_by, self.emp_user)

	def test_home_lists_a_request_waiting_for_the_employee_and_stops_after_the_answer(self):
		att, req = self.filed_by_hr()
		rows = punch_fix.home_rows(self.emp)
		self.assertEqual([(r["name"], r["filed_by"], r["punch_fix"]) for r in rows], [(req, "HR", True)])
		self.confirm_as_employee(req)
		self.assertEqual(punch_fix.home_rows(self.emp), [])

	def test_only_the_employee_can_confirm_and_not_twice_and_not_their_own_request(self):
		att, req = self.filed_by_hr()
		other = self.h._login("peer", ())
		self.h._employee("Peer2", other)
		frappe.set_user(other)
		try:
			self.refused(lambda: punch_fix.confirm(req, 1), "not about you")
		finally:
			frappe.set_user("Administrator")
		self.refused_as(self.hr, lambda: punch_fix.confirm(req, 1))  # HR cannot confirm for them
		frappe.set_user(self.emp_user)
		try:
			punch_fix.confirm(req, 1)
			self.refused(lambda: punch_fix.confirm(req, 1), "already confirmed")
			frappe.db.set_value(REQUEST, req, "alvoraa_review_status", "Withdrawn")  # one open request per day
			own = punch_fix.send(self.day, "17:00", None, "mine")
			self.refused(lambda: punch_fix.confirm(own["name"], 1), "nothing to confirm")
		finally:
			frappe.set_user("Administrator")

	def refused_as(self, user, fn):
		frappe.set_user(user)
		try:
			with self.assertRaises((frappe.ValidationError, frappe.PermissionError)):
				fn()
		finally:
			frappe.set_user("Administrator")

	def test_a_client_cannot_write_the_confirm_fields(self):
		att, req = self.filed_by_hr()
		doc = frappe.get_doc(REQUEST, req)
		doc.alvoraa_confirmed_by, doc.alvoraa_confirmed_on, doc.alvoraa_needs_confirm = self.hr, frappe.utils.now_datetime(), 0
		doc.save(ignore_permissions=True)
		row = frappe.db.get_value(REQUEST, req, ["alvoraa_needs_confirm", "alvoraa_confirmed_by", "alvoraa_confirmed_on"], as_dict=True)
		self.assertEqual((row.alvoraa_needs_confirm, row.alvoraa_confirmed_by, row.alvoraa_confirmed_on), (1, None, None))

	def test_a_confirm_is_cleared_when_the_filer_changes_what_the_request_says(self):
		"""SEC-7 (from 086's review): confirm, then the filer edits the time, the reason or the set-aside:
		the request is no longer confirmed, so the approval is refused until the employee confirms again."""
		att, names = self.held_three()
		for field, value in (("alvoraa_missing_time", "12:45:00"), ("explanation", "I typed it wrong"),
		                     ("alvoraa_set_aside", None)):
			req = self.fix("12:40", by=self.hr, note="HR typed it")
			frappe.set_user(self.emp_user)
			try:
				punch_fix.confirm(req, 1)
			finally:
				frappe.set_user("Administrator")
			self.assertTrue(frappe.db.get_value(REQUEST, req, "alvoraa_confirmed_on"))
			doc = frappe.get_doc(REQUEST, req)
			if field == "alvoraa_set_aside":
				doc.alvoraa_set_aside = names[1]
			else:
				doc.set(field, value)
			frappe.set_user(self.hr)  # the filer, saving as themselves
			try:
				doc.save(ignore_permissions=True)
			finally:
				frappe.set_user("Administrator")
			row = frappe.db.get_value(REQUEST, req, ["alvoraa_confirmed_by", "alvoraa_confirmed_on", "alvoraa_needs_confirm"], as_dict=True)
			self.assertEqual((row.alvoraa_confirmed_by, row.alvoraa_confirmed_on, row.alvoraa_needs_confirm), (None, None, 1), field)
			self.assertIn(req, [x["name"] for x in punch_fix.unconfirmed_changes([self.emp])])  # unconfirmed again
			frappe.db.set_value(REQUEST, req, "alvoraa_review_status", "Withdrawn")  # one open request per day

	def test_saving_the_request_again_without_a_change_keeps_the_confirm(self):
		att, req = self.filed_by_hr()
		frappe.set_user(self.emp_user)
		try:
			punch_fix.confirm(req, 1)
		finally:
			frappe.set_user("Administrator")
		frappe.get_doc(REQUEST, req).save(ignore_permissions=True)
		self.assertTrue(frappe.db.get_value(REQUEST, req, "alvoraa_confirmed_on"))

	def test_the_card_and_the_day_sheet_say_the_request_is_waiting_for_the_employee(self):
		att, req = self.filed_by_hr()
		frappe.set_user(self.hr)
		try:
			card = punch_fix.card(frappe.get_doc(REQUEST, req).as_dict())
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(card["awaiting_confirm"])
		frappe.set_user(self.emp_user)
		try:
			sheet = punch_fix.day_sheet(self.day)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual((sheet["request"]["needs_confirm"], sheet["request"]["filed_by"]), (True, "HR"))
		self.confirm_as_employee(req)
		frappe.set_user(self.emp_user)
		try:
			self.assertEqual(punch_fix.day_sheet(self.day)["request"]["confirm_state"], "confirmed")
		finally:
			frappe.set_user("Administrator")

	def test_confirm_is_post_only_and_the_module_still_has_no_permission_bypass(self):
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func.get(punch_fix.confirm), ["POST"])
		self.assertNotIn("ignore_permissions", open(os.path.join(PKG, "punch_fix.py")).read())


class V5(PunchFixCase):
	"""V5 (Surbhi, 21 Nov): approval never waits; the employee can confirm or say Not right before or after
	approval; HR's list before payroll; the salary slip refuses while an HR-filed or cut change is unconfirmed."""

	def filed(self, by=None, note="HR typed it"):
		att, names = self.held_three()
		return att, names, self.fix("12:40", by=by or self.hr, note=note)

	def not_right(self, req, reason="I was back by 12:50", time="12:50"):
		frappe.set_user(self.emp_user)
		try:
			return punch_fix.confirm(req, 0, reason, time)
		finally:
			frappe.set_user("Administrator")

	def test_after_approval_not_right_with_a_time_is_a_new_request_and_the_day_stays_as_approved(self):
		att, names, req = self.filed()
		self.decide(req, by=self.h.hr2)
		self.refused(lambda: self.not_right(req, "wrong", ""), "Enter the time first")
		out = self.not_right(req)
		new = frappe.get_doc(REQUEST, out["replacement"])
		self.assertEqual((new.docstatus, new.alvoraa_review_status, new.alvoraa_replaces, new.alvoraa_needs_confirm, new.owner),
		                 (0, "Waiting", req, 0, self.emp_user))
		self.assertEqual(frappe.db.get_value(REQUEST, req, "docstatus"), 1)  # the approved one is untouched
		self.assertEqual((self.row(att).status, len(self.added(req))), ("Present", 1))  # the day stays as approved

	def test_after_approval_not_right_for_a_cut_is_a_dispute_that_reaches_hr_and_changes_no_day(self):
		att, names = self.held_three()
		req = self.fix(aside=[names[1]], note="wrong scan")  # only Administrator can file a cut for somebody
		frappe.db.set_value(REQUEST, req, {"alvoraa_needs_confirm": 1})
		self.decide(req, by=self.h.hr2)
		status = self.row(att).status
		out = self.not_right(req, "That scan was mine", "")
		self.assertTrue(out["disputed"])
		row = frappe.db.get_value(REQUEST, req, ["alvoraa_disputed_by", "alvoraa_dispute_reason", "docstatus"], as_dict=True)
		self.assertEqual((row.alvoraa_disputed_by, row.alvoraa_dispute_reason, row.docstatus), (self.emp_user, "That scan was mine", 1))
		self.assertEqual(self.row(att).status, status)
		self.assertEqual([x["disputed"] for x in punch_fix.unconfirmed_changes([self.emp])], [True])  # it still holds the slip

	def test_a_managers_addition_needs_no_confirm_but_the_employee_can_still_say_not_right(self):
		mgr = self.h._login("mgrv5", ())
		self.h._employee("Mgrv5", mgr)
		att, names = self.held_three()
		req = self.fix("12:40", by=mgr, note="He told me")
		frappe.set_user(self.emp_user)
		try:
			self.refused(lambda: punch_fix.confirm(req, 1), "nothing to confirm")
			sheet = punch_fix.day_sheet(self.day)["request"]
		finally:
			frappe.set_user("Administrator")
		self.assertEqual((sheet["needs_confirm"], sheet["can_confirm"], sheet["can_not_right"]), (False, False, True))
		out = self.not_right(req)
		self.assertTrue(out["replacement"])

	def test_withdraw_is_for_a_pending_change_only_and_only_by_hr_in_scope(self):
		att, names, req = self.filed()
		other_hr = self.h._login("hrout", ("HR Manager",))
		self.h._employee("Hrout", other_hr, company=self.h.other_company)
		frappe.set_user(other_hr)
		try:
			self.refused(lambda: punch_fix.withdraw_filed(req), "outside the people")
		finally:
			frappe.set_user("Administrator")
		frappe.set_user(self.h.hr2)
		try:
			punch_fix.withdraw_filed(req)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_review_status"), "Withdrawn")
		self.assertEqual(punch_fix.unconfirmed_changes([self.emp]), [])  # a withdrawn change no longer holds the slip
		att2, names2 = self.held_three_on(add_days(self.day, -1))
		approved = self.fix("12:40", by=self.hr, note="HR typed it")
		self.decide(approved, by=self.h.hr2)
		frappe.set_user(self.h.hr2)
		try:
			self.refused(lambda: punch_fix.withdraw_filed(approved), "still waiting for HR")  # D-2
		finally:
			frappe.set_user("Administrator")

	def held_three_on(self, day):
		self.h.day = self.day = day
		return self.day_of([("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")])

	def test_the_list_before_payroll_names_unconfirmed_changes_for_hr_in_scope_only(self):
		att, names, req = self.filed()
		frappe.set_user(self.h.hr2)
		try:
			out = punch_fix.before_payroll(str(self.day))
		finally:
			frappe.set_user("Administrator")
		# test_site also holds the committed browser fixtures of earlier rounds, so look for this request only
		self.assertEqual([(r["name"], r["what"], r["filed_by"], r["can_withdraw"]) for r in out["rows"] if r["name"] == req],
		                 [(req, "added 12:40", "HR", True)])
		other_hr = self.h._login("hrout2", ("HR Manager",))
		self.h._employee("Hrout2", other_hr, company=self.h.other_company)
		frappe.set_user(other_hr)
		try:
			self.assertEqual(punch_fix.before_payroll(str(self.day))["rows"], [])
		finally:
			frappe.set_user("Administrator")
		self.refused(lambda: self._as(self.emp_user, lambda: punch_fix.before_payroll(str(self.day))), "Only HR")

	def _as(self, user, fn):
		frappe.set_user(user)
		try:
			return fn()
		finally:
			frappe.set_user("Administrator")

	def slip(self):
		from types import SimpleNamespace
		first = frappe.utils.get_first_day(self.day)
		return SimpleNamespace(docstatus=0, employee=self.emp, employee_name="Ravi Sample", start_date=first,
		                       end_date=frappe.utils.get_last_day(first))

	def test_the_salary_slip_is_refused_while_an_hr_filed_change_is_unconfirmed_and_names_it(self):
		att, names, req = self.filed()
		with self.assertRaises(frappe.ValidationError) as cm:
			punch_fix.refuse_slip_while_unconfirmed(self.slip())
		text = str(cm.exception)
		for needle in ("cannot be submitted", "1 change is not confirmed", "added 12:40", "(HR)", "confirm in the app"):
			self.assertIn(needle, text)
		self.decide(req, by=self.h.hr2)  # approval does not lift it
		with self.assertRaises(frappe.ValidationError):
			punch_fix.refuse_slip_while_unconfirmed(self.slip())
		self.confirm_as_employee(req)  # confirmed: lifted
		punch_fix.refuse_slip_while_unconfirmed(self.slip())

	def test_the_slip_is_not_held_by_a_withdrawn_change_a_managers_addition_or_the_employees_own_request(self):
		mgr = self.h._login("mgrslip", ())
		self.h._employee("Mgrslip", mgr)
		att, names = self.held_three()
		manager_add = self.fix("12:40", by=mgr, note="He told me")
		punch_fix.refuse_slip_while_unconfirmed(self.slip())  # a manager's addition never holds the slip
		self.decide(manager_add, by=self.hr)
		att2, names2 = self.held_three_on(add_days(self.day, -1))
		hr_filed = self.fix("12:40", by=self.hr, note="HR typed it")
		with self.assertRaises(frappe.ValidationError):
			punch_fix.refuse_slip_while_unconfirmed(self.slip())
		frappe.db.set_value(REQUEST, hr_filed, "alvoraa_review_status", "Withdrawn")
		punch_fix.refuse_slip_while_unconfirmed(self.slip())

	def test_the_slip_check_is_wired_to_the_slip_submit_and_the_workings_report_gets_the_flag(self):
		hooks = frappe.get_hooks("doc_events")["Salary Slip"]["before_submit"]
		self.assertIn("alvoraa_portal.punch_fix.refuse_slip_while_unconfirmed", hooks)
		att, names, req = self.filed()
		first = frappe.utils.get_first_day(self.day)
		text = punch_fix.unconfirmed_text_by_employee([self.emp], first, frappe.utils.get_last_day(first))
		self.assertIn("added 12:40", text[self.emp])
		from alvoraa_portal.alvoraa_portal.report.salary_components_and_workings import salary_components_and_workings as rpt
		self.assertIn("unconfirmed", [c["fieldname"] for c in rpt._columns()])

	def test_the_register_seam_refuses_a_notice_that_does_not_exist(self):
		"""Slice 088 part 1 implemented this seam, so it no longer says "not available yet".

		What 087 needs to keep proving is that the seam is WIRED and is not a no-op: handed a
		notice that does not exist it refuses, rather than quietly marking the days as signed
		for a page nobody ever printed. The marking itself is proved in
		`test_register_notice_088`, which owns the notice record."""
		self.refused(lambda: punch_fix.record_register_signature(["HR-ARQ-X"], "NOTICE-X"),
		             "does not exist")

	def test_the_printed_reason_hint_is_on_every_reason_box_and_has_a_hindi_line(self):
		js = open(os.path.join(PKG, "public/js/ess/portal.js")).read()
		hint = "This reason is printed on the employee's monthly notice."
		self.assertGreaterEqual(js.count(hint), 3)  # the send bar, Not right, the 085 held form
		self.assertIn(hint, open(os.path.join(PKG, "translations/hi.csv")).read())


class ReviewFixRound1(PunchFixCase):
	"""05-review.md B1, M1, M2 and Surbhi's arrears decision (21 Nov)."""

	def test_b1_a_managers_time_only_filing_then_a_set_aside_edit_holds_the_slip(self):
		mgr = self.h._login("mgrb1", ())
		self.h._employee("Mgrb1", mgr)
		att, names = self.held_three()
		req = self.fix("12:40", by=mgr, note="He told me")
		self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_needs_confirm"), 0)
		frappe.set_user("Administrator")  # a person other than the employee edits it to cut a punch
		frappe.set_user(self.hr)
		try:
			doc = frappe.get_doc(REQUEST, req)
			doc.alvoraa_set_aside = names[1]
			doc.save(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		row = frappe.db.get_value(REQUEST, req, ["alvoraa_needs_confirm", "alvoraa_confirmed_on"], as_dict=True)
		self.assertEqual((row.alvoraa_needs_confirm, row.alvoraa_confirmed_on), (1, None))
		self.decide(req, by=self.h.hr2)
		first = frappe.utils.get_first_day(self.day)
		from types import SimpleNamespace
		slip = SimpleNamespace(docstatus=0, employee=self.emp, employee_name="Ravi Sample", start_date=first,
		                       end_date=frappe.utils.get_last_day(first))
		with self.assertRaises(frappe.ValidationError):
			punch_fix.refuse_slip_while_unconfirmed(slip)  # the slip is held

	def test_b1_an_edit_by_the_employee_or_a_time_only_edit_does_not_ask_again(self):
		att, names = self.held_three()
		req = self.fix("12:40", by=self.emp_user, note="my own")
		frappe.set_user(self.emp_user)
		try:
			doc = frappe.get_doc(REQUEST, req)
			doc.explanation = "my own, edited"
			doc.save()
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_needs_confirm"), 0)

	def test_a_change_for_a_day_on_a_final_slip_holds_only_the_slip_that_carries_the_arrears(self):
		"""Surbhi, 21 Nov: an HR change paid as an arrear holds the slip that carries it, and no other."""
		att, names = self.held_three()
		req = self.fix("12:40", by=self.hr, note="HR typed it")
		self.decide(req, by=self.h.hr2)
		nxt = frappe.utils.add_months(frappe.utils.get_first_day(self.day), 1)
		later = frappe.utils.add_months(nxt, 1)
		frappe.db.set_value(REQUEST, req, "alvoraa_reviewed_on", "%s 10:00:00" % add_days(nxt, 2))  # approved in nxt
		from types import SimpleNamespace

		def slip(start):
			return SimpleNamespace(docstatus=0, employee=self.emp, employee_name="Ravi Sample", start_date=start,
			                       end_date=frappe.utils.get_last_day(start))
		with patch.object(held_day, "is_in_final_slip", return_value=False):
			punch_fix.refuse_slip_while_unconfirmed(slip(nxt))  # the day is not on a final slip: nothing to hold
		with patch.object(held_day, "is_in_final_slip", return_value=True):
			self.refused(lambda: punch_fix.refuse_slip_while_unconfirmed(slip(nxt)), "cannot be submitted")
			punch_fix.refuse_slip_while_unconfirmed(slip(later))  # a later slip does not carry it
			self.confirm_as_employee(req)
			punch_fix.refuse_slip_while_unconfirmed(slip(nxt))

	def test_m1_not_right_is_outside_the_filing_window(self):
		att, names = self.held_three()
		doc = frappe.get_doc({"doctype": REQUEST, "employee": self.emp, "from_date": self.day, "to_date": self.day,
		                      "reason": "Forgot to Punch In", "alvoraa_missing_time": "12:50"})
		doc.alvoraa_replaces = "x"
		frappe.set_user(self.emp_user)
		try:
			with patch.object(ac, "employee_filing_window_days", return_value=1):
				ac.refuse_own_day_outside_window(doc)  # a replacement is exempt: nothing is raised
				with patch.object(ac, "own_day_state", return_value="old") as st:
					ac.refuse_own_day_outside_window(doc)
					st.assert_not_called()  # exempt before the window is looked at
				doc.alvoraa_replaces = None  # without the link the window is asked
				with patch.object(ac, "own_day_state", return_value="open") as st:
					ac.refuse_own_day_outside_window(doc)
					st.assert_called_once()
		finally:
			frappe.set_user("Administrator")

	def test_m2_the_limit_and_the_card_work_before_the_columns_exist(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		real = frappe.db.has_column

		def has(doctype, col):
			if doctype == REQUEST and col in ("alvoraa_for_held_day", "alvoraa_replaces", "alvoraa_needs_confirm",
			                                 "alvoraa_confirmed_on", "alvoraa_undone_on"):
				return False
			return real(doctype, col)
		doc = frappe.get_doc(REQUEST, req)
		with patch.object(frappe.db, "has_column", side_effect=has):  # the columns really read as missing
			self.assertFalse(punch_fix.columns_ready())
			held_day.enforce_monthly_limit(doc)  # does not read a missing column
			self.assertEqual(punch_fix.card_context([dict(frappe.get_doc(REQUEST, req).as_dict(), punch_fix=True)]), {})
			frappe.set_user(self.h.hr2)
			try:
				ac.to_review()  # the review list does not fail on an unknown column
			finally:
				frappe.set_user("Administrator")

	def test_an_ordinary_request_cannot_be_moved_to_another_employee_either(self):
		other = self.h._employee("Moved2")
		doc = frappe.get_doc({"doctype": REQUEST, "employee": self.emp, "from_date": self.day, "to_date": self.day,
		                      "reason": "Work From Home", "explanation": "home"}).insert(ignore_permissions=True)
		self.assertFalse(punch_fix.is_punch_fix(doc))
		doc.employee = other
		self.refused(lambda: doc.save(ignore_permissions=True), "another employee")

	def test_undo_on_a_held_day_clears_the_old_hr_decision_fields(self):
		att, names = self.held_three()
		req = self.fix("12:40", by=self.hr, note="HR typed it")
		self.decide(req, by=self.h.hr2)
		self.assertEqual(self.row(att).alvoraa_release_how, "HR decision")
		frappe.db.set_value(REQUEST, req, {"alvoraa_disputed_by": self.emp_user,
		                                   "alvoraa_disputed_on": frappe.utils.now_datetime(), "alvoraa_dispute_reason": "no"})
		frappe.set_user(self.h.hr2)
		try:
			punch_fix.undo_change(req, "the employee is right")
		finally:
			frappe.set_user("Administrator")
		row = frappe.db.get_value("Attendance", att, ["status", "alvoraa_release_how", "alvoraa_release_by", "alvoraa_release_on"], as_dict=True)
		self.assertEqual((row.status, row.alvoraa_release_how, row.alvoraa_release_by, row.alvoraa_release_on),
		                 ("Held", None, None, None))

	def test_a_replacement_stores_the_in_out_it_will_have_once_hrs_punch_is_gone(self):
		att, names = self.held_three()
		req = self.fix("12:40", by=self.hr, note="HR typed it")
		self.decide(req, by=self.h.hr2)
		frappe.set_user(self.emp_user)
		try:
			out = punch_fix.confirm(req, 0, "I was back by 12:50", "12:50")
		finally:
			frappe.set_user("Administrator")
		added = [p.name for p in self.added(req)]
		expected = punch_fix.derive(self.emp, self.day, "12:50:00", added)[0]
		self.assertEqual(frappe.db.get_value(REQUEST, out["replacement"], "alvoraa_missing_log"), expected)
		self.assertNotEqual(expected, punch_fix.derive(self.emp, self.day, "12:50:00", [])[0])  # HR's punch would flip it
		self.decide(out["replacement"], by=self.h.hr2)
		stored = frappe.get_all(CHECKIN, filters={punch_fix.ADDED: out["replacement"]}, fields=["log_type"])
		self.assertEqual(stored[0].log_type, expected)  # and approval agrees with what was stored

	def test_pending_surbhi_the_hr_time_edit_switch(self):
		"""Behind one switch: off keeps today's behaviour, on re-asks the employee."""
		att, names = self.held_three()
		req = self.fix("12:40", by=self.emp_user, note="my own")
		for switch, expect in ((False, 0), (True, 1)):
			frappe.db.set_value(REQUEST, req, {"alvoraa_needs_confirm": 0, "alvoraa_missing_time": "12:40:00"})
			frappe.set_user(self.hr)
			try:
				with patch.object(punch_fix, "HR_TIME_EDIT_REASKS_CONFIRM", switch):
					doc = frappe.get_doc(REQUEST, req)
					doc.alvoraa_missing_time = "12:30:00"
					doc.save(ignore_permissions=True)
			finally:
				frappe.set_user("Administrator")
			self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_needs_confirm"), expect)


class SecurityReview(PunchFixCase):
	"""Fixes from the 087 security review: F1 (employee cannot be moved), SEC-6 logging, minor scope rules."""

	def other_worker(self):
		return self.h._employee("Moved")

	def move(self, req, to, by="Administrator"):
		frappe.set_user(by)
		try:
			doc = frappe.get_doc(REQUEST, req)
			doc.employee = to
			doc.save(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")

	def test_a_confirmed_request_cannot_be_moved_to_another_employee(self):
		att, names = self.held_three()
		req = self.fix(aside=[names[1]], note="wrong scan")
		frappe.db.set_value(REQUEST, req, "alvoraa_needs_confirm", 1)
		self.confirm_as_employee(req)
		y = self.other_worker()
		self.refused(lambda: self.move(req, y), "another employee")
		self.assertEqual(frappe.db.get_value(REQUEST, req, "employee"), self.emp)

	def test_an_hr_own_day_fix_cannot_be_moved_to_someone_elses_day(self):
		hr_emp = frappe.db.get_value("Employee", {"user_id": self.hr}, "name")
		att, names = self.day_of([("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")], employee=hr_emp)
		req = self.fix("12:40", employee=hr_emp, by=self.hr)
		self.refused(lambda: self.move(req, self.emp, by=self.hr), "another employee")

	def test_employee_is_part_of_what_a_confirm_vouches_for(self):
		self.assertIn("employee", punch_fix.CONFIRMED_CONTENT)

	def test_the_punch_fix_log_lines_are_really_written_to_the_security_log(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		seen = security_lines_from_a_fresh_process(lambda: self.decide(req))
		self.assertTrue(any("punch_fix approved request=%s" % req in m for m in seen), seen)

	def test_withdraw_is_post_only_and_refused_on_the_hr_persons_own_day(self):
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func.get(punch_fix.withdraw_filed), ["POST"])
		hr_emp = frappe.db.get_value("Employee", {"user_id": self.hr}, "name")
		att, names = self.day_of([("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")], employee=hr_emp)
		req = self.fix(aside=[names[1]], employee=hr_emp, note="wrong scan")
		frappe.db.set_value(REQUEST, req, "alvoraa_needs_confirm", 1)
		frappe.set_user(self.hr)
		try:
			self.refused(lambda: punch_fix.withdraw_filed(req), "cannot decide your own")
		finally:
			frappe.set_user("Administrator")

	def branch_hr(self):
		"""An HR login limited to branch A, and a worker who sits in branch B."""
		for b in ("A87A", "A87B"):
			if not frappe.db.exists("Branch", b):
				frappe.get_doc({"doctype": "Branch", "branch": b}).insert(ignore_permissions=True)
		frappe.db.set_value("Employee", self.emp, "branch", "A87B")
		frappe.get_doc({"doctype": "User Permission", "user": self.h.hr2, "allow": "Branch", "for_value": "A87A",
		                "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
		frappe.clear_cache(user=self.h.hr2)
		return self.h.hr2

	def test_withdraw_and_the_before_payroll_list_respect_the_branch(self):
		att, names = self.held_three()
		req = self.fix(aside=[names[1]], note="wrong scan")
		frappe.db.set_value(REQUEST, req, "alvoraa_needs_confirm", 1)
		hr = self.branch_hr()
		frappe.set_user(hr)
		try:
			self.refused(lambda: punch_fix.withdraw_filed(req), "outside the people")
			rows = punch_fix.before_payroll(str(self.day))
			self.assertNotIn(req, [r["name"] for r in rows["rows"]])
		finally:
			frappe.set_user("Administrator")

	def test_the_report_counts_only_the_callers_branch(self):
		from alvoraa_portal.alvoraa_portal.report.punch_fixes_this_month import punch_fixes_this_month as rpt
		att, names = self.held_three()
		self.fix("12:40")
		hr = self.branch_hr()
		frappe.set_user(hr)
		try:
			cols, rows = rpt.execute()
			self.assertEqual(rows, [])
		finally:
			frappe.set_user("Administrator")


class Undo(PunchFixCase):
	"""HR's "Undo this change" on an approved change the employee disputed (Surbhi, 21 Nov)."""

	def undo(self, req, reason="The employee is right", by=None):
		frappe.set_user(by or self.h.hr2)
		try:
			return punch_fix.undo_change(req, reason)
		finally:
			frappe.set_user("Administrator")

	def disputed_cut(self):
		"""A cut (only Administrator files one for somebody), approved, then disputed by the employee."""
		att, names = self.held_three()
		req = self.fix(aside=[names[1]], note="wrong scan")
		frappe.db.set_value(REQUEST, req, "alvoraa_needs_confirm", 1)
		self.decide(req, by=self.h.hr2)
		frappe.set_user(self.emp_user)
		try:
			punch_fix.confirm(req, 0, "That scan was mine", "")
		finally:
			frappe.set_user("Administrator")
		return att, names, req

	def test_undoing_a_disputed_cut_makes_the_punch_count_again_and_frees_the_slip(self):
		att, names, req = self.disputed_cut()
		self.assertEqual(len(punch_fix.counted(self.emp, self.day)), 2)  # the cut is in force
		self.assertEqual(len(punch_fix.unconfirmed_changes([self.emp])), 1)  # and holds the slip
		self.undo(req, "The scan was the employee's own")
		self.assertEqual(len(punch_fix.counted(self.emp, self.day)), 3)  # the set-aside punch counts again
		self.assertTrue(frappe.db.exists(CHECKIN, names[1]))  # nothing deleted
		self.assertFalse(frappe.db.get_value(CHECKIN, names[1], punch_fix.ASIDE))
		row = frappe.db.get_value(REQUEST, req, ["alvoraa_undone_by", "alvoraa_undone_on", "alvoraa_undone_reason", "docstatus"], as_dict=True)
		self.assertEqual((row.alvoraa_undone_by, bool(row.alvoraa_undone_on), row.alvoraa_undone_reason, row.docstatus),
		                 (self.h.hr2, True, "The scan was the employee's own", 1))
		self.assertEqual(punch_fix.unconfirmed_changes([self.emp]), [])  # no longer holds the slip
		self.assertEqual(self.row(att).status, "Held")  # three punches again: judged from the real punches

	def test_undoing_an_added_punch_marks_it_not_counted_with_an_aside_link_and_deletes_nothing(self):
		att, names = self.held_three()
		req = self.fix("12:40", by=self.hr, note="HR typed it")
		self.decide(req, by=self.h.hr2)
		self.assertEqual(self.row(att).status, "Present")
		frappe.db.set_value(REQUEST, req, {"alvoraa_disputed_by": self.emp_user, "alvoraa_disputed_on": frappe.utils.now_datetime(),
		                                   "alvoraa_dispute_reason": "I was not back"})
		self.undo(req)
		added = self.added(req)[0]
		self.assertEqual((added[punch_fix.ASIDE], added.skip_auto_attendance, added.get(punch_fix.ADDED)), (req, 1, req))
		self.assertEqual(len(punch_fix.counted(self.emp, self.day)), 3)
		self.assertEqual(self.row(att).status, "Held")

	def test_undo_needs_a_reason_a_disputed_approved_change_hr_in_scope_not_their_own_day_and_only_once(self):
		att, names, req = self.disputed_cut()
		self.refused(lambda: self.undo(req, "  "), "Say why")
		self.refused(lambda: self.undo(req, "x", by=self.emp_user), "outside the people")
		other_hr = self.h._login("hrundo", ("HR Manager",))
		self.h._employee("Hrundo", other_hr, company=self.h.other_company)
		self.refused(lambda: self.undo(req, "x", by=other_hr), "outside the people")
		self.undo(req)
		self.refused(lambda: self.undo(req), "only once")
		# not disputed: refused
		att2, names2 = self.held_three_on(add_days(self.day, -1))
		plain = self.fix("12:40", by=self.hr, note="HR typed it")
		self.decide(plain, by=self.h.hr2)
		self.refused(lambda: self.undo(plain), "disputed")

	def held_three_on(self, day):
		self.h.day = self.day = day
		return self.day_of([("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")])

	def test_the_undo_log_line_is_really_written_to_the_security_log(self):
		att, names, req = self.disputed_cut()
		seen = security_lines_from_a_fresh_process(lambda: self.undo(req))
		self.assertTrue(any("punch_fix undone request=%s" % req in m for m in seen), seen)

	def test_hr_cannot_undo_a_change_on_their_own_day(self):
		hr_emp = frappe.db.get_value("Employee", {"user_id": self.hr}, "name")
		att, names = self.day_of([("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")], employee=hr_emp)
		req = self.fix(aside=[names[1]], employee=hr_emp, note="wrong scan")
		frappe.db.set_value(REQUEST, req, {"alvoraa_needs_confirm": 1, "alvoraa_disputed_on": frappe.utils.now_datetime()})
		frappe.db.set_value(REQUEST, req, "docstatus", 1)  # approved by somebody else, as the state under test
		self.refused(lambda: self.undo(req, "x", by=self.hr), "own request")

	def test_approving_the_employees_own_time_reverses_the_change_it_replaces(self):
		"""Review B2: after approval, "Not right" with the employee's own time must not leave HR's punch counting."""
		att, names = self.held_three()
		req = self.fix("12:40", by=self.hr, note="HR typed it")
		self.decide(req, by=self.h.hr2)
		frappe.set_user(self.emp_user)
		try:
			out = punch_fix.confirm(req, 0, "I was back by 12:50", "12:50")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(len(punch_fix.counted(self.emp, self.day)), 4)  # HR's 12:40 still counts until HR decides
		self.decide(out["replacement"], by=self.h.hr2)
		times = sorted(str(p.time)[11:16] for p in punch_fix.counted(self.emp, self.day))
		self.assertEqual(times, ["09:00", "12:00", "12:50", "18:00"])  # HR's 12:40 is not counted next to theirs
		self.assertTrue(frappe.db.get_value(REQUEST, req, "alvoraa_undone_on"))
		self.assertEqual(punch_fix.unconfirmed_changes([self.emp]), [])
		old = self.added(req)[0]
		self.assertEqual((old.skip_auto_attendance, old[punch_fix.ASIDE]), (1, req))
		self.assertTrue(frappe.db.exists(CHECKIN, old.name))  # nothing deleted

	def test_the_before_payroll_row_offers_undo_only_on_a_disputed_approved_change(self):
		att, names, req = self.disputed_cut()
		rows = [r for r in self._as(self.h.hr2, lambda: punch_fix.before_payroll(str(self.day)))["rows"] if r["name"] == req]
		self.assertEqual((rows[0]["disputed"], rows[0]["can_undo"], rows[0]["can_withdraw"]), (True, True, False))
		att2, names2 = self.held_three_on(add_days(self.day, -1))
		plain = self.fix("12:40", by=self.hr, note="HR typed it")
		self.decide(plain, by=self.h.hr2)
		row = [r for r in self._as(self.h.hr2, lambda: punch_fix.before_payroll(str(self.day)))["rows"] if r["name"] == plain][0]
		self.assertEqual((row["can_undo"], row["can_withdraw"]), (False, False))

	def _as(self, user, fn):
		frappe.set_user(user)
		try:
			return fn()
		finally:
			frappe.set_user("Administrator")

	def test_undo_is_post_only(self):
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func.get(punch_fix.undo_change), ["POST"])


class NightShift(PunchFixCase):
	"""ALV-402's rule in 087's reads: a punch counts on its `shift_start` day. DTC's case: two
	daytime punches and a 00:00 departure on the next calendar date."""

	def night_day(self):
		names = []
		for when, lt, start in (("%s 09:00:00" % self.day, "IN", self.day), ("%s 12:00:00" % self.day, "OUT", self.day),
		                        ("%s 00:00:00" % add_days(self.day, 1), "OUT", self.day)):
			doc = frappe.get_doc({"doctype": CHECKIN, "employee": self.emp, "log_type": lt, "time": when})
			doc.insert(ignore_permissions=True)
			# Set after insert, as test_midnight_punch_alv402 does: Frappe's own shift match depends on the site.
			frappe.db.set_value(CHECKIN, doc.name, {"shift_start": "%s 09:00:00" % start, "offshift": 0},
			                    update_modified=False)
			names.append(doc.name)
		att = self.h._attendance(self.emp)
		att.submit()
		return att.name, names

	def test_the_card_the_preview_and_the_engine_count_the_00_00_departure_on_its_shift_day(self):
		from alvoraa_portal.payroll_rules_apply import _punches
		att, names = self.night_day()
		self.assertEqual(self.row(att).status, "Held")  # 3 punches by the shift day, as the engine reads them
		self.assertEqual(_punches(self.emp, self.day)[2], 3)
		self.assertEqual(len(punch_fix.counted(self.emp, self.day)), 3)
		self.assertEqual(len(punch_fix.day_punches(self.emp, self.day)), 3)
		self.assertEqual(len(punch_fix.day_punches(self.emp, add_days(self.day, 1))), 0)  # not the next day's
		row = frappe._dict(frappe.db.get_value("Attendance", att, ["*"], as_dict=True))
		status, hours, late, early, first, last = held_day.worked_out(row)
		self.assertEqual(str(last), "%s 00:00:00" % add_days(self.day, 1))  # the 00:00 punch is the out time
		req = self.fix("12:40")
		frappe.set_user(self.hr)
		try:
			card = punch_fix.card(frappe.get_doc(REQUEST, req).as_dict())
		finally:
			frappe.set_user("Administrator")
		self.assertEqual([p["time"] for p in card["now"]["punches"]], ["09:00", "12:00", "00:00"])
		self.assertEqual([p["m"] for p in card["now"]["punches"]], [540, 720, 1440])  # after midnight runs on
		self.decide(req)
		row = self.row(att)
		self.assertEqual((row.status, round(row.working_hours, 2)), (card["after"]["status"], card["after"]["hours"]))
		self.assertEqual(card["after"]["status"], "Present")

	def test_a_day_punch_for_the_next_day_is_not_taken_into_this_days_card(self):
		att, names = self.night_day()
		doc = frappe.get_doc({"doctype": CHECKIN, "employee": self.emp, "log_type": "IN",
		                      "time": "%s 11:00:00" % add_days(self.day, 1)})
		doc.insert(ignore_permissions=True)
		frappe.db.set_value(CHECKIN, doc.name, {"shift_start": "%s 11:00:00" % add_days(self.day, 1), "offshift": 0},
		                    update_modified=False)
		self.assertEqual(len(punch_fix.day_punches(self.emp, self.day)), 3)
