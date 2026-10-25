"""Slice 066, steps 8-11: the legal limit, the slip line, the review flag and
the private review note. PROVISIONAL - waiting for Surbhi's answer on how the
cap works (24 Oct 2026: "after 3 marks it stops for everyone"), which may
replace the 3%-of-wages stop and the 4th-mark flag these tests pin.

Answered the same day: at most 3 marks per person per month for everyone, the
flag at the 3rd, and the 3% check kept as a backstop. These tests pin that.

Uses the world and helpers of test_grooming_066 (same people, same fixture).
"""

import json
import os
from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.utils import add_days

import alvoraa_portal.attendance_correction as ac
import alvoraa_portal.grooming as grooming
import alvoraa_portal.payroll_slip as payroll_slip
from alvoraa_portal.payroll_month import MonthSummary, summarise_month
from alvoraa_portal.tests import test_grooming_066 as world
from alvoraa_portal.tests.test_grooming_066 import (
	COMPANY, DAY2, M_END, M_START, NOTE, P, PLAIN, TODAY, YESTERDAY, _bells, _list, _mark,
	_raw_mark, _rest_mark, as_user, user,
)

setUpModule = world.setUpModule
tearDownModule = world.tearDownModule


class Case(world.Case):
	def setUp(self):
		frappe.db.delete(grooming.REVIEW, {"employee": ("in", list(P.values()))})
		frappe.db.delete("Comment", {"reference_doctype": grooming.REVIEW})
		super().setUp()

	def tearDown(self):
		frappe.db.delete(grooming.REVIEW, {"employee": ("in", list(P.values()))})
		super().tearDown()


# ── US-10, SEC-10: the 3-mark stop, and the 3% backstop behind it ─────────────

class TestLegalLimit(Case):
	def test_three_marks_a_month_is_the_most_for_everyone(self):
		if TODAY.day < 4:
			self.skipTest("too early in the month")
		# Kiran: Junior Rs 100, Basic 15,000 (3% = 450). Three marks fit the law;
		# the 3-mark rule stops the 4th.
		third = [_raw_mark(P["Kiran"], add_days(M_START, i)) for i in range(3)][-1]
		with as_user("Ravi"):
			v = grooming.may_mark(P["Kiran"], TODAY)
		self.assertEqual((v.code, v.message), (
			"R12", "Kiran has had 3 grooming reds this month, the most allowed. HR has been told and "
			       "will talk to Kiran. If it carries on, you can raise it with HR."))
		self.assertNotIn("₹", v.message)
		self.refused(_rest_mark, "Ravi", "Kiran", told_in_person=1)
		with as_user("Ritika"):
			self.assertEqual(grooming.may_mark(P["Kiran"], TODAY).message,
			                 "Kiran has had 3 grooming reds this month, the most allowed, so no "
			                 "more can be marked.")
			self.refused(_rest_mark, "Ritika", "Kiran", told_in_person=1)
		frappe.db.set_value(grooming.MARK, third, "docstatus", 2)
		with as_user("Ravi"):
			self.assertTrue(grooming.may_mark(P["Kiran"], TODAY).ok)

	def test_the_three_percent_backstop_stops_a_senior_earlier(self):
		if YESTERDAY < M_START:
			self.skipTest("first day of the month")
		# Rahul: Senior Rs 200, Basic 18,000 (3% = 540): a 3rd mark would be 600.
		_raw_mark(P["Rahul"], YESTERDAY)
		_raw_mark(P["Rahul"], DAY2 if DAY2 >= M_START else YESTERDAY)
		with as_user("Ravi"):
			v = grooming.may_mark(P["Rahul"], TODAY)
		if DAY2 < M_START:
			self.skipTest("too early in the month")
		self.assertEqual(v.message, "Rahul has reached the most grooming reds the law allows this "
		                            "month, so this one cannot be marked. HR has been told and will "
		                            "talk to Rahul. If it carries on, you can raise it with HR.")
		with as_user("Ritika"):
			self.assertTrue(grooming.may_mark(P["Rahul"], TODAY).message.endswith(
				"(limit ₹540 = 3% of Basic ₹18,000)"))

	def test_ac49_no_salary_assignment_means_no_mark(self):
		with as_user("Ravi"):
			self.assertEqual(grooming.may_mark(P["Nobase"], TODAY).code, "R12")


# ── US-11, SEC-9, SEC-10: the slip ───────────────────────────────────────────

class TestSlip(Case):
	def test_ac50_capped_figure_and_the_why(self):
		from alvoraa_portal.payroll_rules import DayVerdict
		days = [DayVerdict() for _ in range(30)]          # 30 ordinary days, each paid in full
		s = summarise_month(days, basic=10000, month_days=30, grooming_days=4, mark_rate=100,
		                    earns_leave_credits=False)
		self.assertEqual((s.grooming_deduction, s.grooming_capped), (300.0, True))
		self.assertIn("4 grooming reds at ₹100, capped at ₹300 by the legal limit.", s.notes)
		s = summarise_month(days, basic=12000, month_days=30, grooming_days=3, mark_rate=100,
		                    earns_leave_credits=False)
		self.assertEqual((s.grooming_deduction, s.grooming_capped), (300.0, False))
		self.assertIn("3 grooming reds at ₹100.", s.notes)
		self.assertAlmostEqual(s.net, s.gross - 300)
		s = summarise_month(days, basic=12000, month_days=30, grooming_days=3, mark_rate=100,
		                    earns_marks=False, earns_leave_credits=False)
		self.assertEqual(s.grooming_deduction, 0)

	def test_ac53_sec2c_distinct_days_and_no_charge_on_a_full_day_leave(self):
		if DAY2 < M_START:
			self.skipTest("too early in the month")
		_raw_mark(P["Kiran"], DAY2)
		_raw_mark(P["Kiran"], DAY2, owner_first="Ritika", marked_as="HR")     # same date twice
		_raw_mark(P["Kiran"], YESTERDAY)
		frappe.get_doc({"doctype": "Attendance", "employee": P["Kiran"], "company": COMPANY,
		                "attendance_date": YESTERDAY, "status": "On Leave", "docstatus": 1,
		                "name": frappe.generate_hash(length=10)}).db_insert()
		s = payroll_slip.month_summary(P["Kiran"], COMPANY, M_START, M_END)
		self.assertEqual(s.grooming_days, 1)

	def test_ac53_a_contract_person_with_marks_is_charged_nothing(self):
		_raw_mark(P["Geeta"], TODAY)
		s = payroll_slip.month_summary(P["Geeta"], COMPANY, M_START, M_END)
		self.assertEqual(s.grooming_deduction, 0)

	def test_ac50_ac51_one_engine_line_replaced_never_added(self):
		self.assertEqual(payroll_slip.ENGINE_LINES[-1], ("Grooming Red Value", "grooming_deduction"))
		self.assertEqual([c for c, _f in payroll_slip.ENGINE_LINES[:2]],
		                 [payroll_slip.RED_COMPONENT, payroll_slip.GREEN_COMPONENT])

		def slip(amount, doc=None):
			summary = MonthSummary(paid_days=30, grooming_deduction=amount)
			with patch.object(payroll_slip, "month_summary", return_value=summary):
				if doc is None:
					doc = frappe.get_doc({"doctype": "Salary Slip", "employee": P["Kiran"],
					                      "company": COMPANY, "start_date": M_START,
					                      "end_date": M_END, "posting_date": M_END,
					                      "payroll_frequency": "Monthly", "currency": "INR"})
					doc.flags.ignore_permissions = True
					doc.insert()
				else:
					doc.reload()
					doc.flags.ignore_permissions = True
					doc.save()
			return doc

		def lines(docstatus=None):
			f = {"employee": P["Kiran"], "salary_component": "Grooming Red Value"}
			if docstatus is not None:
				f["docstatus"] = docstatus
			return frappe.get_all("Additional Salary", filters=f, fields=["amount", "docstatus",
			                                                              "amended_from"],
			                      order_by="creation asc")

		doc = slip(300)
		self.assertEqual([r.amount for r in doc.deductions
		                  if r.salary_component == "Grooming Red Value"], [300])
		slip(300, doc)
		self.assertEqual(len(lines(1)), 1)
		slip(400, doc)
		rows = lines()
		self.assertEqual([r.docstatus for r in rows], [2, 1])
		self.assertTrue(rows[1].amended_from)

		# AC-52: the submit check re-prices and refuses a stale slip.
		doc.reload()
		with patch.object(payroll_slip, "month_summary",
		                  return_value=MonthSummary(grooming_deduction=500)):
			self.assertRaises(frappe.ValidationError, payroll_slip.check_grooming_before_submit, doc)
		with patch.object(payroll_slip, "month_summary",
		                  return_value=MonthSummary(grooming_deduction=400)):
			payroll_slip.check_grooming_before_submit(doc)

	def test_ac52_the_submit_check_does_nothing_without_a_rule_set(self):
		doc = frappe._dict(company=PLAIN, employee=P["Pia"], start_date=M_START, end_date=M_END,
		                   deductions=[])
		with patch.object(payroll_slip, "month_summary") as priced:
			payroll_slip.check_grooming_before_submit(doc)
		priced.assert_not_called()

	def test_ac54_the_workings_report_has_the_two_columns(self):
		from alvoraa_portal.alvoraa_portal.report.salary_components_and_workings import (
			salary_components_and_workings as report)
		_raw_mark(P["Kiran"], TODAY)
		cols, rows = report.execute({"company": COMPANY, "from_date": str(M_START),
		                             "to_date": str(M_END), "employee": P["Kiran"]})[:2]
		keys = [c["fieldname"] for c in cols]
		self.assertEqual(keys[keys.index("red_deduction") + 1:keys.index("red_deduction") + 3],
		                 ["grooming_days", "grooming_deduction"])
		row = [r for r in rows if r["employee"] == P["Kiran"]]
		if row:
			self.assertEqual(row[0]["grooming_days"], 1)


# ── US-14: the review flag ───────────────────────────────────────────────────

class TestReviewFlag(Case):
	def _flag(self, first, subject):
		with as_user(first):
			return ac.month(TODAY.year, TODAY.month, P[subject]).get("grooming", {}).get("review")

	def test_ac55_y1_a_senior_on_18000_is_flagged_at_the_mark_that_reaches_the_limit(self):
		if YESTERDAY < M_START:
			self.skipTest("first day of the month")
		_raw_mark(P["Rahul"], YESTERDAY)
		self.assertEqual(self._flag("Ritika", "Rahul"), [])
		name = _mark("Ravi", "Rahul")                    # the 2nd: 3 x 200 > 540
		review = self._flag("Ritika", "Rahul")[0]
		self.assertEqual((review["state"], review["why"], review["limit"], review["base"]),
		                 ("pending", "limit", "₹540", "₹18,000"))
		for first in ("Rahul", "Ravi"):
			self.assertEqual(self._flag(first, "Rahul")[0]["state"], "pending")
		self.assertNotIn("base", self._flag("Rahul", "Rahul")[0])
		self.assertNotIn("limit", self._flag("Ravi", "Rahul")[0])
		self.assertIsNone(self._flag("Sunil", "Rahul"))
		bells = _bells(name)
		self.assertIn("You have reached this month's legal limit for grooming reds, so HR will "
		              "talk to you about it.", [b for b in bells if b.for_user == user("Rahul")][0].subject)
		hr = [b.subject for b in bells if b.for_user == user("Hari")]
		self.assertEqual(hr, ["Grooming review pending for Rahul G066: the legal limit for grooming "
		                      "reds in %s is reached." % grooming._month_name(TODAY)])

	def test_ac55_ac56_a_junior_on_15000_is_flagged_at_the_third_and_removal_lowers_it(self):
		if TODAY.day < 4:
			self.skipTest("too early in the month")
		days = [add_days(M_START, i) for i in range(3)]
		names = [_raw_mark(P["Kiran"], d, at="%s 10:0%d:00" % (d, i)) for i, d in enumerate(days)]
		with as_user("Ritika"):
			fl = grooming.flag_for(P["Kiran"], M_START, 100, 15000)
		self.assertEqual((fl.state, fl.why, fl.count), ("pending", "max", 3))
		frappe.db.set_value(grooming.MARK, names[-1], "docstatus", 2)
		self.assertIsNone(grooming.flag_for(P["Kiran"], M_START, 100, 15000))

	def test_ac60_once_cleared_it_never_returns_that_month(self):
		if TODAY.day < 5:
			self.skipTest("too early in the month")
		for i in range(3):
			_raw_mark(P["Kiran"], add_days(M_START, i), at="%s 10:0%d:00" % (add_days(M_START, i), i))
		with as_user("Ritika"):
			grooming.record_review(P["Kiran"], str(M_START), NOTE)
		_raw_mark(P["Kiran"], add_days(M_START, 3))    # a 4th, written straight to the table
		self.assertEqual(grooming.flag_for(P["Kiran"], M_START, 100, 15000).state, "cleared")

	def test_ac58_the_word_integrity_is_nowhere_in_the_slice(self):
		root = os.path.dirname(grooming.__file__)
		files = [grooming.__file__,
		         os.path.join(root, "alvoraa_portal", "doctype", "grooming_mark", "grooming_mark.py"),
		         os.path.join(root, "alvoraa_portal", "doctype", "grooming_review", "grooming_review.py")]
		for f in files:
			self.assertNotIn("integrity", open(f, encoding="utf-8").read().lower(), f)
		js = open(os.path.join(root, "public", "js", "ess", "portal.js"), encoding="utf-8").read()
		block = js[js.index("/* ── Slice 066: the grooming red"):js.index("/* ── The team's days, worst first")]
		self.assertNotIn("integrity", block.lower())


# ── US-15, D5, D6: the private review note ───────────────────────────────────

class TestReviewNote(Case):
	def setUp(self):
		super().setUp()
		if YESTERDAY < M_START:
			self.skipTest("first day of the month")
		_raw_mark(P["Rahul"], YESTERDAY)
		_raw_mark(P["Rahul"], TODAY, at="%s 11:00:00" % TODAY)

	def test_ac61_ac62_hr_records_it_and_the_flag_clears_for_everyone_marks_unchanged(self):
		with as_user("Ritika"):
			grooming.record_review(P["Rahul"], str(M_START), NOTE)
		r = TestReviewFlag._flag(self, "Rahul", "Rahul")[0]
		self.assertEqual(r["state"], "cleared")
		self.assertNotIn("note", r)                           # "Action agreed on {date}" only
		self.assertEqual(r["on"], grooming._day(TODAY))
		r = TestReviewFlag._flag(self, "Ravi", "Rahul")[0]    # the direct manager reads it (v2)
		self.assertEqual((r["state"], r["note"], r["by"]), ("cleared", NOTE, "Ritika G066"))
		r = TestReviewFlag._flag(self, "Ritika", "Rahul")[0]
		self.assertEqual(r["note"], NOTE)
		self.assertEqual(frappe.db.count(grooming.MARK, {"employee": P["Rahul"], "docstatus": 1}), 2)

	def test_ac64_the_note_reaches_nobody_but_hr_and_the_direct_manager(self):
		with as_user("Ritika"):
			name = grooming.record_review(P["Rahul"], str(M_START), NOTE)["name"]
		from frappe.desk.form.load import getdoc
		for first in ("Rahul", "Om", "Olga", "Neha", "Sunil", "Deepa"):
			with self.subTest(first=first), as_user(first):
				self.assertEqual(_list(grooming.REVIEW), [])
				self.assertRaises(frappe.PermissionError, frappe.client.get, grooming.REVIEW, name)
				frappe.local.response = frappe._dict()
				try:
					getdoc("Employee", P["Rahul"])
				except frappe.PermissionError:
					pass
				self.assertNotIn("uniform rule", json.dumps(frappe.local.response, default=str, ensure_ascii=False))
		for first in ("Ritika", "Ravi"):
			with as_user(first):
				self.assertEqual(frappe.get_list(grooming.REVIEW, pluck="name"), [name])
				self.assertEqual(frappe.client.get(grooming.REVIEW, name)["review_note"], NOTE)
		with as_user("Ravi"):                                  # read only, never write
			self.refused(frappe.client.set_value, grooming.REVIEW, name, "review_note", "x")

	def test_ac63_it_cannot_be_changed_or_deleted_or_commented(self):
		with as_user("Ritika"):
			name = grooming.record_review(P["Rahul"], str(M_START), NOTE)["name"]
			self.refused(frappe.client.set_value, grooming.REVIEW, name, "review_note", "changed")
			self.refused(frappe.client.delete, grooming.REVIEW, name)
		self.refused(frappe.get_doc(grooming.REVIEW, name).add_comment, "Comment", "x")
		self.assertEqual(frappe.db.get_value(grooming.REVIEW, name, "review_note"), NOTE)
		self.assertEqual(frappe.db.count("Version", {"ref_doctype": grooming.REVIEW}), 0)

	def test_ac65_who_may_not_record_and_when(self):
		for first in ("Ravi", "Om", "Rahul", "Olga"):
			with self.subTest(first=first), as_user(first):
				self.refused(grooming.record_review, P["Rahul"], str(M_START), NOTE)
		with as_user("Ritika"):
			self.refused(grooming.record_review, P["Rahul"], str(M_START), "   ")
			self.refused(grooming.record_review, P["Kiran"], str(M_START), NOTE)   # no flag


class TestPendingReport(Case):
	def test_y4_the_pending_report_and_the_inbox(self):
		if YESTERDAY < M_START:
			self.skipTest("first day of the month")
		_raw_mark(P["Rahul"], YESTERDAY)
		asked = _mark("Ravi", "Rahul")
		with as_user("Rahul"):
			grooming.ask(asked)
		from alvoraa_portal.alvoraa_portal.report.grooming_review_pending import (
			grooming_review_pending as pending)
		self.assertEqual(frappe.db.get_value("Report", "Grooming Review Pending", "report_type"),
		                 "Script Report")
		with as_user("Ritika"):
			_cols, rows, _msg = pending.execute({"month": str(M_START)})
			self.assertEqual([(r["employee"], r["why"]) for r in rows],
			                 [(P["Rahul"], "Legal limit reached")])
		for first in ("Ravi", "Olga"):
			with as_user(first):
				self.assertEqual(pending.execute({"month": str(M_START)})[1], [])


# ── Raise it with HR (brief, Decisions 24 Oct 2026 (3), option A) ────────────

class TestRaiseWithHR(Case):
	def _at_limit(self, subject="Kiran", owner="Ravi", n=3):
		if TODAY.day < n + 1:
			self.skipTest("too early in the month")
		return [_raw_mark(P[subject], add_days(M_START, i), owner_first=owner,
		                  marked_as="HR" if owner == "Ritika" else "Manager",
		                  at="%s 10:0%d:00" % (add_days(M_START, i), i)) for i in range(n)]

	def _raise(self, first, subject, reason="Not in uniform"):
		with as_user(first):
			return grooming.raise_with_hr(P[subject], reason)["name"]

	def test_the_manager_raises_once_on_the_mark_that_reached_the_limit(self):
		names = self._at_limit()
		self.refused(self._raise, "Ravi", "Kiran", "Other")          # fixed reasons only
		self.assertEqual(self._raise("Ravi", "Kiran"), names[-1])
		doc = frappe.get_doc(grooming.MARK, names[-1])
		self.assertEqual((doc.raised_by, doc.raised_reason, doc.docstatus),
		                 (user("Ravi"), "Not in uniform", 1))
		self.assertTrue(doc.raised_on)
		self.refused(self._raise, "Ravi", "Kiran")                    # one a month
		fl = grooming.flag_for(P["Kiran"], M_START, 100, 15000)
		self.assertEqual((fl.state, fl.why), ("pending", "raised"))
		hr = [b.subject for b in _bells(names[-1]) if b.for_user == user("Hari")]
		self.assertEqual(hr, ["Grooming review pending for Kiran G066: Ravi G066, the manager, raised it with HR on "
		                      "%s." % grooming._day(TODAY)])

	def test_nobody_else_raises_and_nothing_before_the_limit(self):
		self._at_limit(n=2)                                           # Junior on 15,000: not yet
		self.refused(self._raise, "Ravi", "Kiran")
		_raw_mark(P["Kiran"], add_days(M_START, 2))
		for first in ("Neha", "Sunil", "Ritika", "Deepa"):
			with self.subTest(first=first):
				self.refused(self._raise, first, "Kiran")

	def test_the_employee_is_told_who_raised_it_and_that_it_adds_no_fine(self):
		if YESTERDAY < M_START or DAY2 < M_START:
			self.skipTest("too early in the month")
		_raw_mark(P["Rahul"], DAY2)
		name = _raw_mark(P["Rahul"], YESTERDAY)                      # Senior on 18,000: the limit
		self._raise("Ravi", "Rahul")
		mine = [b.subject for b in _bells(name) if b.for_user == user("Rahul")]
		self.assertEqual(mine, ["Ravi G066, your manager, has asked HR to talk to you about "
		                        "grooming. This adds no fine."])

	def test_the_manager_can_raise_on_hrs_mark_but_still_cannot_read_it(self):
		names = self._at_limit(owner="Ritika")
		self._raise("Ravi", "Kiran")
		with as_user("Ravi"):
			self.assertRaises(frappe.PermissionError, frappe.client.get, grooming.MARK, names[-1])
			self.refused(frappe.client.set_value, grooming.MARK, names[-1], "asked_on", str(TODAY))
			self.refused(frappe.client.cancel, grooming.MARK, names[-1])

	def test_hr_records_the_talk_and_still_nobody_adds_a_fourth(self):
		self._at_limit()
		with as_user("Ritika"):
			grooming.record_review(P["Kiran"], str(M_START), NOTE)
		self.assertEqual(grooming.flag_for(P["Kiran"], M_START, 100, 15000).state, "cleared")
		self._raise("Ravi", "Kiran")
		self.assertEqual(grooming.flag_for(P["Kiran"], M_START, 100, 15000).why, "raised")
		with as_user("Ritika"):
			_cols, rows, _m = __import__(
				"alvoraa_portal.alvoraa_portal.report.grooming_review_pending.grooming_review_pending",
				fromlist=["execute"]).execute({"month": str(M_START)})
			self.assertEqual([r["employee"] for r in rows], [P["Kiran"]])
			grooming.record_review(P["Kiran"], str(M_START), NOTE)
			self.assertEqual(grooming.may_mark(P["Kiran"], TODAY).code, "R12")
		self.assertEqual(grooming.flag_for(P["Kiran"], M_START, 100, 15000).state, "cleared")
		self.assertEqual(frappe.db.count(grooming.REVIEW, {"employee": P["Kiran"]}), 2)

	def test_the_today_card_offers_the_raise_then_says_when(self):
		self._at_limit()
		with as_user("Ravi"):
			row = [r for r in grooming.today()["rows"] if r["employee"] == P["Kiran"]][0]
		self.assertEqual((row["why_code"], row["raise"]), ("R12", {"can": True}))
		self._raise("Ravi", "Kiran")
		with as_user("Ravi"):
			row = [r for r in grooming.today()["rows"] if r["employee"] == P["Kiran"]][0]
		self.assertEqual(row["raise"]["raised_on"], grooming._day(TODAY))
		self.assertNotIn("\u20b9", json.dumps(row, ensure_ascii=False))


class TestAskedHoldsTheSlip(Case):
	def _slip(self):
		return frappe._dict(company=COMPANY, employee=P["Rahul"], employee_name="Rahul G066",
		                    start_date=M_START, end_date=M_END, deductions=[])

	def test_an_open_ask_holds_the_slip_and_a_raise_does_not(self):
		name = _mark("Ravi", "Rahul")
		with as_user("Rahul"):
			grooming.ask(name)
		with patch.object(payroll_slip, "month_summary", return_value=MonthSummary()):
			with self.assertRaises(frappe.ValidationError) as caught:
				payroll_slip.check_grooming_before_submit(self._slip())
			self.assertIn("Rahul asked HR to look at the grooming red on", str(caught.exception))
			with as_user("Ritika"):
				grooming.keep(name)
			payroll_slip.check_grooming_before_submit(self._slip())


class TestSecurityVerificationCap(Case):
	def test_m1_the_slip_never_charges_more_than_three_days(self):
		if TODAY.day < 5:
			self.skipTest("too early in the month")
		for i in range(4):                              # a race left four on the table
			_raw_mark(P["Kiran"], add_days(M_START, i))
		self.assertEqual(payroll_slip.month_summary(P["Kiran"], COMPANY, M_START, M_END)
		                 .grooming_days, grooming.MONTH_MAX)

	def test_b1_a_raise_sent_straight_through_rest_is_refused(self):
		if TODAY.day < 4:
			self.skipTest("too early in the month")
		names = [_raw_mark(P["Kiran"], add_days(M_START, i), owner_first="Ritika", marked_as="HR",
		                   at="%s 10:0%d:00" % (add_days(M_START, i), i)) for i in range(3)]
		with as_user("Ravi"):
			self.refused(frappe.client.set_value, grooming.MARK, names[-1],
			             {"raised_reason": "Not in uniform"})
			self.refused(frappe.client.set_value, grooming.MARK, names[-1], {})
		self.assertFalse(frappe.db.get_value(grooming.MARK, names[-1], "raised_on"))
		self.assertEqual(frappe.db.get_value(grooming.MARK, names[-1], "modified_by"), user("Ritika"))
		with as_user("Ravi"):                           # the endpoint still works, and says only the name
			self.assertEqual(grooming.raise_with_hr(P["Kiran"], "Not in uniform"), {"name": names[-1]})


# ── Architect review, 25 Oct 2026 (06-review): M-1, M-2, m-1, m-6 ───────────

class TestArchitectReviewFixes(Case):
	def test_m2_one_raise_a_month_even_after_the_mark_it_was_on_is_removed(self):
		if TODAY.day < 5:
			self.skipTest("too early in the month")
		names = [_raw_mark(P["Kiran"], add_days(M_START, i), at="%s 10:0%d:00" % (add_days(M_START, i), i))
		         for i in range(3)]
		with as_user("Ravi"):
			self.assertEqual(grooming.raise_with_hr(P["Kiran"], "Not in uniform"), {"name": names[-1]})
		frappe.db.set_value(grooming.MARK, names[-1], "docstatus", 2)   # HR removed it
		_raw_mark(P["Kiran"], add_days(M_START, 3), at="%s 10:09:00" % add_days(M_START, 3))
		with as_user("Ravi"):
			self.assertEqual(grooming.may_raise(P["Kiran"]).code, "RAISE2")
			self.refused(grooming.raise_with_hr, P["Kiran"], "Not in uniform")

	def test_m1_pending_report_says_why_in_the_right_words(self):
		if TODAY.day < 4:
			self.skipTest("too early in the month")
		from alvoraa_portal.alvoraa_portal.report.grooming_review_pending import (
			grooming_review_pending as pending)
		for i in range(3):
			_raw_mark(P["Kiran"], add_days(M_START, i), at="%s 10:0%d:00" % (add_days(M_START, i), i))
		with as_user("Ritika"):
			self.assertEqual([r["why"] for r in pending.execute({"month": str(M_START)})[1]],
			                 ["3 grooming reds, the most allowed"])
			grooming.record_review(P["Kiran"], str(M_START), NOTE)
		with as_user("Ravi"):
			grooming.raise_with_hr(P["Kiran"], "Not in uniform")
		with as_user("Ritika"):
			self.assertEqual([r["why"] for r in pending.execute({"month": str(M_START)})[1]],
			                 ["Raised again by Ravi G066"])

	def test_m6_the_today_card_is_flat_with_people_at_the_limit(self):
		if TODAY.day < 4:
			self.skipTest("too early in the month")

		def count():
			n = [0]
			real = frappe.db.sql

			def wrap(*a, **k):
				n[0] += 1
				return real(*a, **k)
			with as_user("Ravi"), patch.object(frappe.db, "sql", wrap):
				grooming.today()
			return n[0]
		for i in range(3):
			_raw_mark(P["Kiran"], add_days(M_START, i), at="%s 10:0%d:00" % (add_days(M_START, i), i))
		count()
		one = count()
		for who in ("Aman", "Pooja"):
			for i in range(3):
				_raw_mark(P[who], add_days(M_START, i), at="%s 11:0%d:00" % (add_days(M_START, i), i))
		count()
		self.assertEqual(count(), one)
		with as_user("Ravi"):
			rows = {r["employee"]: r for r in grooming.today()["rows"]}
		self.assertEqual(rows[P["Aman"]]["raise"], {"can": True})

	def test_m1_a_scaled_grooming_line_does_not_hold_the_slip_for_ever(self):
		"""Architect review M-1. With "depends on payment days" on, Frappe HR
		scales the engine's line on a slip with unpaid days. The submit check
		compares the engine's record with the marks, so a scaled line passes and
		a real change still refuses."""
		frappe.db.set_value("Salary Component", payroll_slip.GROOMING_COMPONENT,
		                    "depends_on_payment_days", 1)
		try:
			summary = MonthSummary(paid_days=15, grooming_deduction=300)
			with patch.object(payroll_slip, "month_summary", return_value=summary):
				doc = frappe.get_doc({"doctype": "Salary Slip", "employee": P["Kiran"],
				                      "company": COMPANY, "start_date": M_START, "end_date": M_END,
				                      "posting_date": M_END, "payroll_frequency": "Monthly",
				                      "currency": "INR"})
				doc.flags.ignore_permissions = True
				doc.insert()
				row = [r.amount for r in doc.deductions
				       if r.salary_component == payroll_slip.GROOMING_COMPONENT]
				self.assertTrue(row and row[0] < 300, row)        # Frappe scaled it
				payroll_slip.check_grooming_before_submit(doc)     # and it is not refused
			with patch.object(payroll_slip, "month_summary",
			                  return_value=MonthSummary(paid_days=15, grooming_deduction=400)):
				self.assertRaises(frappe.ValidationError,
				                  payroll_slip.check_grooming_before_submit, doc)
		finally:
			frappe.db.set_value("Salary Component", payroll_slip.GROOMING_COMPONENT,
			                    "depends_on_payment_days", 0)


class TestTwoMarkersAtOnce(Case):
	"""Security M1, second look (25 Oct 2026): a REAL race between two
	processes. This process makes the 3rd mark and keeps its transaction open;
	a second bench process reads (fixing its snapshot), then tries a 4th and
	waits on the person's row lock. When this one commits, the second must see
	the 3rd mark and be refused - not save a 4th from its old snapshot."""

	def test_m1_the_second_of_two_simultaneous_marks_sees_the_first_and_stops(self):
		import subprocess
		import time
		if TODAY.day < 4 or YESTERDAY in (M_START, add_days(M_START, 1)):
			self.skipTest("needs two earlier days and yesterday in this month")
		for i in range(2):
			_raw_mark(P["Kiran"], add_days(M_START, i))
		frappe.db.commit()                              # 2 live marks, seen by everyone
		with as_user("Ritika"):                         # A: the 3rd, transaction left open
			grooming.mark(P["Kiran"], "Not in uniform", told_in_person=1, date=str(YESTERDAY))
		args = json.dumps({"user": user("Ravi"), "employee": P["Kiran"], "date": str(TODAY)})
		b = subprocess.Popen(
			["bench", "--site", frappe.local.site, "execute",
			 "alvoraa_portal.tests.grooming_race_066.mark_as", "--kwargs", args],
			cwd=frappe.utils.get_bench_path(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
			text=True)
		lines = []
		try:
			for line in b.stdout:                       # wait until B has its snapshot
				lines.append(line)
				if "READY" in line:
					break
			time.sleep(3)                               # B is now waiting on the lock
			frappe.db.commit()                          # A commits the 3rd mark
			out, _err = b.communicate(timeout=180)
		finally:
			if b.poll() is None:
				b.kill()
		said = "".join(lines) + (out or "")
		self.assertIn("RESULT refused", said, said[-600:])
		live = frappe.db.sql("""select count(distinct mark_date) from `tabGrooming Mark`
			where employee=%s and docstatus=1 and mark_date between %s and %s""",
			(P["Kiran"], M_START, M_END))[0][0]
		self.assertEqual(live, 3)


class TestActionAgreedNotice(Case):
	def test_the_person_and_their_manager_are_told_the_date_never_the_note(self):
		if YESTERDAY < M_START:
			self.skipTest("first day of the month")
		_raw_mark(P["Rahul"], YESTERDAY)
		_raw_mark(P["Rahul"], TODAY, at="%s 11:00:00" % TODAY)
		with as_user("Ritika"):
			name = grooming.record_review(P["Rahul"], str(M_START), NOTE)["name"]
		bells = frappe.get_all("Notification Log", filters={"document_type": grooming.REVIEW,
		                                                    "document_name": name},
		                       fields=["for_user", "subject", "link"])
		day = grooming._day(frappe.db.get_value(grooming.REVIEW, name, "creation"))
		said = {b.for_user: b.subject for b in bells}
		self.assertEqual(said, {
			user("Rahul"): "HR recorded a grooming review with you. Action agreed on %s." % day,
			user("Ravi"): "HR recorded the grooming review for Rahul G066. Action agreed on %s." % day})
		self.assertNotIn("uniform rule", json.dumps(bells))
		for first in ("Rahul", "Ravi"):
			with as_user(first):
				self.assertEqual(len(grooming.my_notices()["items"]), 1)
		frappe.db.set_value("Employee", P["Rahul"], "reports_to", P["Neha"])
		try:
			with as_user("Ravi"):                       # no longer the manager: the notice goes
				self.assertEqual(grooming.my_notices()["items"], [])
		finally:
			frappe.db.set_value("Employee", P["Rahul"], "reports_to", P["Ravi"])


class TestPrototypeV3Limit(Case):
	"""v3 Z8, Z11, Z16 on the server's side."""

	def _kiran_at_three(self):
		if TODAY.day < 4:
			self.skipTest("too early in the month")
		for i in range(3):
			_raw_mark(P["Kiran"], add_days(M_START, i), at="%s 10:0%d:00" % (add_days(M_START, i), i))

	def _row(self):
		with as_user("Ravi"):
			return [r for r in grooming.today()["rows"] if r["employee"] == P["Kiran"]][0]

	def test_z8_after_the_raise_the_row_says_the_stop_alone(self):
		self._kiran_at_three()
		row = self._row()
		self.assertEqual(row["why_not"], "Kiran has had 3 grooming reds this month, the most allowed. "
		                                 "HR has been told and will talk to Kiran. If it carries on, you "
		                                 "can raise it with HR.")
		self.assertEqual((row["raise"], row["has_login"]), ({"can": True}, False))
		with as_user("Ravi"):
			grooming.raise_with_hr(P["Kiran"], "Not in uniform")
		row = self._row()
		self.assertEqual(row["why_not"], "Kiran has had 3 grooming reds this month, the most allowed.")
		self.assertEqual(row["raise"]["raised_on"], grooming._day(TODAY))

	def test_z16_the_review_says_whether_the_manager_can_still_raise_it(self):
		self._kiran_at_three()
		with as_user("Ritika"):
			grooming.record_review(P["Kiran"], str(M_START), NOTE)
			first = ac.month(TODAY.year, TODAY.month, P["Kiran"])["grooming"]["review"][-1]
		self.assertEqual((first["state"], first["after_raise"]), ("cleared", False))
		with as_user("Ravi"):
			grooming.raise_with_hr(P["Kiran"], "Not in uniform")
		with as_user("Ritika"):
			grooming.record_review(P["Kiran"], str(M_START), NOTE)
			second = ac.month(TODAY.year, TODAY.month, P["Kiran"])["grooming"]["review"][-1]
		self.assertEqual((second["state"], second["after_raise"]), ("cleared", True))


# ── Grooming's own switch (pre-push review P-1; Surbhi, 25 Oct 2026, option 2) ─

@contextmanager
def grooming_off(missing=False):
	"""Grooming switched off: the component disabled, or not there at all."""
	frappe.local.request_cache.clear()
	try:
		if missing:
			with patch.object(grooming, "COMPONENT", "No Such Component G066"):
				yield
		else:
			frappe.db.set_value("Salary Component", grooming.COMPONENT, "disabled", 1)
			yield
	finally:
		frappe.db.set_value("Salary Component", grooming.COMPONENT, "disabled", 0)
		frappe.local.request_cache.clear()


class TestGroomingSwitch(Case):
	def test_on_only_while_the_component_exists_and_is_enabled(self):
		self.assertTrue(grooming.is_on())
		# The company's payroll rule set stays enabled throughout: it never
		# switches grooming on by itself.
		self.assertTrue(payroll_slip.rule_set_for(COMPANY))
		with grooming_off():
			self.assertFalse(grooming.is_on())
		with grooming_off(missing=True):
			self.assertFalse(grooming.is_on())
		self.assertTrue(grooming.is_on())

	def test_the_switch_is_read_once_per_request(self):
		self.assertTrue(grooming.is_on())
		frappe.db.set_value("Salary Component", grooming.COMPONENT, "disabled", 1)
		try:
			self.assertTrue(grooming.is_on())             # the same request: no second read
			frappe.local.request_cache.clear()            # the next request reads it again
			self.assertFalse(grooming.is_on())
		finally:
			frappe.db.set_value("Salary Component", grooming.COMPONENT, "disabled", 0)
			frappe.local.request_cache.clear()

	def test_off_no_screens_no_marks_no_payload_keys(self):
		_raw_mark(P["Rahul"], TODAY)
		for missing in (False, True):
			with grooming_off(missing):
				with as_user("Ravi"):
					self.assertEqual(grooming.today(), {"show": False})
					self.assertEqual(grooming.may_mark(P["Aman"], TODAY).code, "R1")
				self.refused(_mark, "Ravi", "Aman", told=1)
				self.refused(_rest_mark, "Ritika", "Aman", told_in_person=1)
				with as_user("Rahul"):
					self.assertNotIn("grooming", ac.month(TODAY.year, TODAY.month))
				with as_user("Ritika"):
					self.assertNotIn("grooming", ac.month(TODAY.year, TODAY.month, P["Rahul"]))
		self.assertEqual(frappe.db.count(grooming.MARK, {"employee": P["Aman"]}), 0)

	def test_off_old_marks_are_kept_readable_and_frozen_with_no_notices(self):
		asked = _mark("Ravi", "Rahul")
		with as_user("Rahul"):
			grooming.ask(asked)
		other = _raw_mark(P["Kiran"], TODAY)
		bells = len(_bells())
		with grooming_off():
			with as_user("Rahul"):
				frappe.get_doc(grooming.MARK, asked).check_permission("read")
			with as_user("Ritika"):
				self.assertIn(asked, _list(grooming.MARK))
			with as_user("Ritika"):
				self.refused(grooming.keep, asked)
				self.refused(grooming.remove, other, grooming.REMOVAL_REASONS[1])
				self.refused(grooming.record_review, P["Kiran"], str(M_START), NOTE)
			with as_user("Ravi"):
				self.refused(grooming.undo, asked)
				self.assertEqual(grooming.may_raise(P["Kiran"]).code, "R1")
		self.assertEqual(frappe.db.count(grooming.MARK, {"name": ("in", [asked, other]),
		                                                 "docstatus": 1}), 2)
		self.assertEqual(len(_bells()), bells)

	def test_off_no_slip_line_no_flag_and_an_open_ask_holds_no_slip(self):
		if TODAY.day < 4:
			self.skipTest("too early in the month")
		for i in range(3):
			_raw_mark(P["Kiran"], add_days(M_START, i))
		name = _mark("Ravi", "Rahul")
		with as_user("Rahul"):
			grooming.ask(name)
		slip = frappe._dict(company=COMPANY, employee=P["Rahul"], employee_name="Rahul G066",
		                    start_date=M_START, end_date=M_END, deductions=[])
		with grooming_off():
			self.assertEqual(payroll_slip.month_summary(P["Kiran"], COMPANY, M_START, M_END)
			                 .grooming_days, 0)
			payroll_slip.check_grooming_before_submit(slip)        # not held
			self.assertEqual(grooming.pending_reviews(user("Ritika"), M_START), [])
		self.assertEqual(payroll_slip.month_summary(P["Kiran"], COMPANY, M_START, M_END)
		                 .grooming_days, 3)
		self.assertRaises(frappe.ValidationError, payroll_slip.check_grooming_before_submit, slip)

	def test_s1_a_slip_saved_while_on_is_not_submitted_with_its_fine_while_off(self):
		"""Switch review S-1: nobody can contest a fine while grooming is off, so
		a draft still carrying the engine's grooming line is refused until it
		is saved again, and the re-save drops the line."""
		with patch.object(payroll_slip, "month_summary",
		                  return_value=MonthSummary(paid_days=30, grooming_deduction=300)):
			doc = frappe.get_doc({"doctype": "Salary Slip", "employee": P["Kiran"],
			                      "company": COMPANY, "start_date": M_START, "end_date": M_END,
			                      "posting_date": M_END, "payroll_frequency": "Monthly",
			                      "currency": "INR"})
			doc.flags.ignore_permissions = True
			doc.insert()
		grv = [r for r in doc.deductions if r.salary_component == payroll_slip.GROOMING_COMPONENT]
		self.assertTrue(grv and grv[0].additional_salary, grv)
		with grooming_off():
			with self.assertRaises(frappe.ValidationError) as caught:
				payroll_slip.check_grooming_before_submit(doc)
			self.assertIn("Save this slip again to drop the grooming line", str(caught.exception))
			doc.save()
			self.assertEqual([r for r in doc.deductions
			                  if r.salary_component == payroll_slip.GROOMING_COMPONENT], [])
			payroll_slip.check_grooming_before_submit(doc)            # now it goes through

	def test_s2_s3_off_says_so_in_the_report_and_old_notices_open_nothing(self):
		from alvoraa_portal.alvoraa_portal.report.grooming_review_pending import (
			grooming_review_pending as report,
		)
		_mark("Ravi", "Rahul")
		with as_user("Rahul"):
			self.assertTrue(grooming.my_notices()["items"][0]["link"])
		with as_user("Ritika"):
			self.assertEqual(report.execute({"month": str(M_START)})[2],
			                 "No grooming review is pending.")
		with grooming_off():
			with as_user("Rahul"):
				items = grooming.my_notices()["items"]
			self.assertTrue(items)                                    # still readable
			self.assertEqual([i["link"] for i in items], [None] * len(items))
			with as_user("Ritika"):
				self.assertEqual(report.execute({"month": str(M_START)})[2],
				                 "Grooming reds are switched off.")

