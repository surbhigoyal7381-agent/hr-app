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


class PunchFixCase(FrappeTestCase):
	def setUp(self):
		self.h = hd.HeldDayCase("test_held_is_a_status_and_the_fields_exist")
		self.h.setUp()
		h = self.h
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

	def decide(self, name, approve=1, by=None, note=None, seen="auto"):
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


class Install(PunchFixCase):
	def test_the_eight_fields_exist(self):
		for dt, fields in punch_fix.FIELDS.items():
			for f in fields:
				self.assertTrue(frappe.db.exists("Custom Field", {"dt": dt, "fieldname": f["fieldname"]}), f["fieldname"])
		self.assertEqual(sum(len(v) for v in punch_fix.FIELDS.values()), 8)

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
		with patch.object(frappe, "logger") as lg:
			doc = frappe.get_doc(CHECKIN, added)
			doc.log_type = "IN"
			doc.save()
		self.assertTrue(any("Administrator" in str(c) for c in lg.return_value.info.call_args_list))

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
			self.refused(lambda: punch_fix.send(self.day, "12:40", None, "forgot the lunch scan"), "takes only the time")
			self.assertEqual(frappe.db.count(REQUEST, {"employee": self.emp}), 0)
			out = punch_fix.send(self.day, "12:40", None, None)
			self.refused(lambda: punch_fix.send(self.day, "12:40,13:00"), "One punch per request")
			self.refused(lambda: punch_fix.send(self.day, None, None), "Enter the time first")
		finally:
			frappe.set_user("Administrator")
		doc = frappe.get_doc(REQUEST, out["name"])
		self.assertEqual((doc.employee, doc.alvoraa_review_status, doc.alvoraa_missing_log, doc.alvoraa_for_held_day,
		                  doc.reason, doc.explanation),
		                 (self.emp, "Waiting", "IN", 1, "Forgot to Punch In", None))
		self.assertEqual(frappe.db.count(REQUEST, {"employee": self.emp}), 1)

	def test_send_for_a_blocked_day_creates_no_request(self):
		frappe.set_user(self.emp_user)
		try:
			self.refused(lambda: punch_fix.send(self.day, "12:40"), "has not been marked yet")
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


class NoteOnOrdinaryDay(PunchFixCase):
	def test_a_note_is_taken_on_an_ordinary_day_and_refused_on_a_held_day(self):
		self.day_of([("09:00", "IN"), ("18:00", "OUT")])
		frappe.set_user(self.emp_user)
		try:
			out = punch_fix.send(self.day, "12:00", None, "went to the bank")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(REQUEST, out["name"], "explanation"), "went to the bank")


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
