"""Slice 087, step 4: the proofs the first test file left out.

AC-81 (Frappe's own attendance job, both orders), AC-43 (a time outside the shift
window), AC-35 (50 cards timed), and the controls that had no break-test: own-day
locks, scope, exactly once, preview equals result, the engine check, ALV-410.
Each control's break-test is in 04-test-report.md.
Fixtures are the 085/087 ones (`PunchFixCase`), plus one change: the day's original
punches are LINKED to the Attendance, the way Frappe's job leaves them. The first
file's `day_of` leaves them unlinked, which no real day has.
"""

import json
import time as clock
from unittest.mock import patch

import frappe
from frappe.utils import add_days, now_datetime

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal import payroll_rules_apply, punch_fix
from alvoraa_portal.payroll_rules_apply import _punches
from alvoraa_portal.tests import test_held_day_085 as hd
from alvoraa_portal.tests import test_punch_fix_087 as base

REQUEST, CHECKIN = base.REQUEST, base.CHECKIN


def setUpModule():
	base.setUpModule()


class Proof(base.PunchFixCase):
	def linked_day(self, times):
		"""A day as Frappe's job leaves it: the punches carry the Attendance's name."""
		att, names = self.day_of(times)
		for n in names:
			frappe.db.set_value(CHECKIN, n, "attendance", att)
		return att, names

	def job_ready(self):
		frappe.db.set_value("Shift Type", hd.SHIFT, {"process_attendance_after": add_days(self.day, -2),
		                                             "last_sync_of_checkin": now_datetime()})
		frappe.clear_document_cache("Shift Type", hd.SHIFT)

	def run_job(self):
		frappe.get_doc("Shift Type", hd.SHIFT).process_auto_attendance()

	def rows_for_day(self):
		return frappe.db.count("Attendance", {"employee": self.emp, "attendance_date": self.day,
		                                      "docstatus": ("<", 2)})

	def assert_one_day_four_punches(self, att, req):
		"""One Attendance row, and the row, the day sheet, the engine and the counter agree on 4."""
		self.assertEqual(self.rows_for_day(), 1)
		added = self.added(req)[0]
		self.assertEqual((added.attendance, added.skip_auto_attendance), (att, 0))
		self.assertEqual(frappe.db.count("Comment", {"reference_doctype": CHECKIN, "reference_name": added.name}), 0)
		self.assertEqual(len(punch_fix.counted(self.emp, self.day)), 4)
		self.assertEqual(_punches(self.emp, self.day)[2], 4)
		frappe.set_user(self.emp_user)
		try:
			sheet = punch_fix.day_sheet(self.day)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(sum(1 for p in sheet["punches"] if p["counted"]), 4)
		self.assertEqual((self.row(att).status, round(self.row(att).working_hours, 2)), ("Present", 8.33))

	# ── AC-81 (SEC-7, OPS-R6) ───────────────────────────────────────────

	def test_ac81_approval_then_frappes_attendance_job(self):
		att, names = self.linked_day([("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")])
		self.job_ready()
		errors = frappe.db.count("Error Log")
		req = self.fix("12:40")
		self.decide(req)
		self.run_job()
		self.assert_one_day_four_punches(att, req)
		self.assertEqual(frappe.db.count("Error Log"), errors)

	def test_ac81_frappes_attendance_job_then_approval(self):
		att, names = self.linked_day([("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")])
		self.job_ready()
		errors = frappe.db.count("Error Log")
		req = self.fix("12:40")
		self.run_job()
		self.assertEqual(self.rows_for_day(), 1)  # the job found nothing unlinked and made nothing
		self.decide(req)
		self.assert_one_day_four_punches(att, req)
		self.assertEqual(frappe.db.count("Error Log"), errors)

	def test_ac81_the_link_is_what_keeps_the_job_off_the_added_punch(self):
		"""The hazard itself, to show the two tests above can fail: with the link line left
		out, the job finds an unlinked punch on a marked day and marks it SKIPPED, so it stops
		counting and the day goes back to Held."""
		att, names = self.linked_day([("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")])
		self.job_ready()
		req = self.fix("12:40")
		real = frappe.db.set_value

		def no_link(dt, dn=None, field=None, val=None, *a, **k):
			if dt == CHECKIN and field == "attendance":
				return None
			return real(dt, dn, field, val, *a, **k)

		with patch.object(frappe.db, "set_value", no_link):
			self.decide(req)
		self.assertFalse(self.added(req)[0].attendance)
		self.run_job()
		self.assertEqual(self.added(req)[0].skip_auto_attendance, 1)

	# ── AC-43 ───────────────────────────────────────────────────────────

	def test_ac43_a_time_outside_the_shift_window_is_refused_in_words_and_writes_nothing(self):
		att, names = self.day_of([("09:00", "IN")])
		req = self.fix("23:30")
		frappe.db.savepoint("t087_43")
		self.refused(lambda: self.decide(req), "23:30 is outside the shift's punch window. Check the time.")
		frappe.db.rollback(save_point="t087_43")  # what the framework does with a failed request
		self.assertEqual(len(self.added(req)), 0)
		self.assertEqual(frappe.db.get_value(REQUEST, req, "docstatus"), 0)
		self.assertEqual((self.row(att).status, self.row(att).attendance_request), ("Held", None))  # one punch is a Held day; unchanged

	# ── AC-48: the first file's "still odd" test cannot fail, this one can ──

	def test_ac48_a_result_that_is_still_odd_stays_held_and_the_hours_are_written(self):
		att, names = self.held_three()
		req = self.fix("13:00", aside=[names[1]])  # 3 punches - 1 set aside + 1 added = 3, still odd
		self.decide(req)
		row = self.row(att)
		self.assertEqual(row.status, "Held")
		self.assertEqual(len(punch_fix.counted(self.emp, self.day)), 3)
		self.assertEqual(round(row.working_hours, 2), 4.0)  # 09:00 to 13:00; the 18:00 stays unpaired

	# ── own-day locks, scope, exactly once, preview, engine ─────────────

	def test_exactly_once_a_stale_second_approval_adds_no_second_punch(self):
		"""The second line of defence: even if `decide`'s own check were passed (two
		approvers holding the same draft), the apply step refuses a punch next to the first."""
		att, names = self.held_three()
		req = self.fix("12:40")
		stale = frappe.get_doc(REQUEST, req)
		self.decide(req)
		self.assertEqual(len(self.added(req)), 1)
		frappe.set_user(self.hr)
		try:
			with self.assertRaises(frappe.ValidationError):
				punch_fix.apply(stale)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(len(self.added(req)), 1)

	def test_the_approval_refuses_when_the_day_does_not_come_out_as_the_card_showed(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		real, calls = punch_fix.outcome, []

		def skewed(*a, **k):
			out = real(*a, **k)
			calls.append(1)
			return dict(out, hours=out["hours"] + 1) if len(calls) == 1 else out

		frappe.db.savepoint("t087_pv")
		with patch.object(punch_fix, "outcome", skewed):
			self.refused(lambda: self.decide(req), "did not come out as the review card showed")
		frappe.db.rollback(save_point="t087_pv")
		self.assertEqual(len(self.added(req)), 0)
		self.assertEqual(self.row(att).status, "Held")

	def test_the_approval_refuses_when_the_pay_engine_would_still_hold_the_day(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		frappe.db.savepoint("t087_eg")
		with patch.object(payroll_rules_apply, "evaluate_attendance", return_value=frappe._dict(held=True)):
			self.refused(lambda: self.decide(req), "pay engine would still hold this day")
		frappe.db.rollback(save_point="t087_eg")
		self.assertEqual((len(self.added(req)), self.row(att).status), (0, "Held"))
		# control: an engine that agrees lets it through
		with patch.object(payroll_rules_apply, "evaluate_attendance", return_value=frappe._dict(held=False)):
			self.decide(req)
		self.assertEqual(self.row(att).status, "Present")

	def test_an_hr_person_and_a_manager_outside_scope_see_nothing_and_decide_nothing(self):
		att, names = self.held_three()
		req = self.fix("12:40")
		doc = frappe.get_doc(REQUEST, req)
		other_hr = self.h._login("hrx", ("HR Manager",))
		self.h._employee("HrX", other_hr, company=self.h.other_company)
		mgr = self.h._login("mgrx", ())
		self.h._employee("MgrX", mgr)
		# control: HR of the employee's own company sees the card
		frappe.set_user(self.hr)
		try:
			self.assertIn(req, [r["name"] for r in ac.to_review(limit=500)])
		finally:
			frappe.set_user("Administrator")
		# HR of another company: not in the queue, cannot decline, cannot approve
		frappe.set_user(other_hr)
		try:
			self.assertNotIn(req, [r["name"] for r in ac.to_review(limit=500)])
		finally:
			frappe.set_user("Administrator")
		self.refused(lambda: self.decide(req, approve=0, by=other_hr, note="no"))
		self.refused(lambda: self.decide(req, by=other_hr))
		# a manager with no HR role: the queue is not theirs to open, and nothing is decided
		frappe.set_user(mgr)
		try:
			with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
				ac.to_review(limit=500)
		finally:
			frappe.set_user("Administrator")
		self.refused(lambda: self.decide(req, by=mgr))
		self.assertEqual((frappe.db.get_value(REQUEST, req, ["docstatus", "alvoraa_review_status"]),
		                  len(self.added(req))), ((0, "Waiting"), 0))

	# ── what the screens send (the server end of the payload) ───────────

	def test_send_takes_exactly_what_the_screen_sends(self):
		"""portal.js `acPfSend` posts date, time, set_aside (a JSON string, "[]" when empty)
		and note ("" when empty); decide posts name, approve (1 or 0), note, seen."""
		att, names = self.held_three()
		frappe.set_user(self.emp_user)
		try:
			add_only = punch_fix.send(date=self.day, time="12:40", set_aside="[]", note="")
		finally:
			frappe.set_user("Administrator")
		doc = frappe.get_doc(REQUEST, add_only["name"])
		self.assertEqual((str(doc.alvoraa_missing_time)[:5], doc.alvoraa_set_aside, doc.explanation), ("12:40", None, None))
		frappe.delete_doc(REQUEST, doc.name, force=1, ignore_permissions=True)
		frappe.set_user(self.emp_user)
		try:
			aside_only = punch_fix.send(date=self.day, time="", set_aside=json.dumps([names[1]]), note="")
		finally:
			frappe.set_user("Administrator")
		doc = frappe.get_doc(REQUEST, aside_only["name"])
		self.assertEqual((doc.alvoraa_missing_time, doc.alvoraa_set_aside), (None, names[1]))
		# HR's side: approve as an int with the token, and the decide result carries the real status
		out = self.decide(doc.name)
		self.assertIn(out["day_status"], ("Present", "Half Day", "Absent", "Held"))

	# ── AC-35 (nfr-budget core view) ────────────────────────────────────

	def test_ac35_fifty_pending_punch_fixes_come_back_in_one_request_inside_the_budget(self):
		staff = [self.h._employee("Staff%d" % i) for i in range(10)]
		made = []
		for emp in staff:
			for back in range(5):
				day = add_days(self.day, -back)
				for hhmm, lt in (("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")):
					frappe.get_doc({"doctype": CHECKIN, "employee": emp, "log_type": lt,
					                "time": "%s %s:00" % (day, hhmm)}).insert(ignore_permissions=True)
				att = frappe.get_doc({"doctype": "Attendance", "employee": emp, "company": self.h.company,
				                      "attendance_date": day, "status": "Present", "shift": hd.SHIFT,
				                      "in_time": "%s 09:00:00" % day})
				att.insert(ignore_permissions=True)
				att.submit()
				made.append(self.fix("12:40", employee=emp, day=day))
		self.assertEqual(len(made), 50)
		queries = []
		db_class = type(frappe.local.db)
		real_sql = db_class.sql

		def counting(db, *a, **k):
			queries.append(1)
			return real_sql(db, *a, **k)

		timings, counts = [], []
		frappe.set_user(self.hr)
		try:
			for _i in range(5):
				del queries[:]
				start = clock.perf_counter()
				with patch.object(db_class, "sql", counting):
					rows = [r for r in ac.to_review(limit=500) if r["name"] in set(made)]
				timings.append(clock.perf_counter() - start)
				counts.append(len(queries))
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(len(rows), 50)
		self.assertTrue(all(r["card"].get("after") for r in rows))
		print("AC-35 MEASURED: 50 cards, seconds per call %s, queries per call %s"
		      % ([round(t, 2) for t in timings], counts))
		self.assertLessEqual(max(timings), 1.5, timings)
