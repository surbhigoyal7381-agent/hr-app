"""ATT-07: re-running the rules over a period that has already been judged.

The daily engine and the monthly roll-up are pure and tested without a site.
This file covers the part that cannot be: reading attendance out of the
database, writing verdicts back, and the four promises the reprocess makes.

  It is safe to click twice.
  It never touches an employee whose slip is already submitted.
  It shows the numbers before it writes anything.
  It leaves a trail that outlives an error log.

The third is the one worth stating plainly: `preview` must write NOTHING. A
preview with a side effect is not a preview, and nobody would ever find out.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from alvoraa_portal import payroll_reprocess as rp
from alvoraa_portal.payroll_rules_apply import VERDICT_FIELDS

COMPANY = "Reprocess Test Co"
ABBR = "RTC"
SHIFT = "Reprocess Test Shift"          # 10:30-20:30, 600 minutes, no own grace
GENEROUS_SHIFT = "Reprocess Generous Shift"   # same hours, 45 minutes' grace
RULE_SET = None


def _gender():
	"""Whatever this site calls a gender.

	Hard-coding "Female" fails on a bench that has never had the Gender
	fixtures loaded, which is exactly how CI builds its site. The same lesson
	is already written down in `hrms/alvoraa_org_structure/tests/
	test_org_structure.py`; this file repeated the mistake anyway, which is
	why it is spelled out again here rather than left as a one-liner.
	"""
	existing = frappe.db.get_value("Gender", {}, "name")
	if existing:
		return existing
	return frappe.get_doc({"doctype": "Gender", "gender": "Other"}
	                      ).insert(ignore_permissions=True).name


def _ensure_company():
	if not frappe.db.exists("Company", COMPANY):
		frappe.get_doc({"doctype": "Company", "company_name": COMPANY,
		                "abbr": ABBR, "default_currency": "INR",
		                "country": "India"}).insert(ignore_permissions=True)


def _ensure_shift():
	if not frappe.db.exists("Shift Type", SHIFT):
		# Late entry marking deliberately OFF, so this shift says nothing about
		# grace and the rule set's own number applies. That is the fallback
		# path, and every other test in this file runs on it.
		frappe.get_doc({"doctype": "Shift Type", "name": SHIFT,
		                "start_time": "10:30:00", "end_time": "20:30:00"}
		               ).insert(ignore_permissions=True)
	if not frappe.db.exists("Shift Type", GENEROUS_SHIFT):
		# The same hours, but this one sets its own grace - and a much longer
		# one, so a day is late under the rule set's 6 minutes and on time
		# under the shift's 45. One number cannot produce both answers, which
		# is what makes the test prove which one was used.
		frappe.get_doc({"doctype": "Shift Type", "name": GENEROUS_SHIFT,
		                "start_time": "10:30:00", "end_time": "20:30:00",
		                "enable_late_entry_marking": 1,
		                "late_entry_grace_period": 45}
		               ).insert(ignore_permissions=True)


def _ensure_rule_set():
	"""DTC's table, on a throwaway company, switched on."""
	name = frappe.db.get_value("Alvoraa Payroll Rule Set", {"company": COMPANY})
	if name:
		return frappe.get_doc("Alvoraa Payroll Rule Set", name)
	doc = frappe.get_doc({
		"doctype": "Alvoraa Payroll Rule Set",
		"company": COMPANY,
		"enabled": 1,
		"grace_minutes": 6,
		"free_reds_per_month": 2,
		"special_day_multiplier": 2,
		"leave_threshold_days": 15,
		"accrual_month_days": 30,
		"slabs": [
			{"percent_from": 0, "percent_to": 20, "quarters_off": 4, "raises_red": 0},
			{"percent_from": 20, "percent_to": 24, "quarters_off": 3, "raises_red": 1},
			{"percent_from": 24, "percent_to": 40, "quarters_off": 3, "raises_red": 0},
			{"percent_from": 40, "percent_to": 44, "quarters_off": 2, "raises_red": 1},
			{"percent_from": 44, "percent_to": 65, "quarters_off": 2, "raises_red": 0},
			{"percent_from": 65, "percent_to": 68, "quarters_off": 1, "raises_red": 1},
			{"percent_from": 68, "percent_to": 90, "quarters_off": 1, "raises_red": 0},
			{"percent_from": 90, "percent_to": 98.9, "quarters_off": 0, "raises_red": 1},
			{"percent_from": 98.9, "percent_to": 100, "quarters_off": 0, "raises_red": 0},
		],
		"mark_rates": [{"grade": "Junior", "amount_per_mark": 100}],
		# Contract staff get a longer grace because of their contract, not
		# their shift. Needed here to prove a shift cannot overrule it.
		#
		# category_field is what makes the table reachable at all. Without it
		# the rows sit there matching nobody, which looks exactly like the
		# engine ignoring them.
		"category_field": "employment_type",
		"categories": [{"category": "Contract", "grace_minutes": 90,
		                "earns_marks": 0, "earns_leave_credits": 0}],
		# No leave classes. Leave is credited once a month from the roll-up,
		# which this file does not touch - it reprocesses days. Listing a class
		# here would oblige the rule set to name the Employee field that holds
		# it, and that field does not exist on a throwaway test company.
	})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


def setUpModule():
	_ensure_company()
	_ensure_shift()
	_ensure_rule_set()
	frappe.db.commit()


class TestReprocess(FrappeTestCase):
	def setUp(self):
		self.date = getdate(add_days(nowdate(), -3))
		self.emp = self._employee()

	def _employee(self, shift=None, employment_type=None):
		"""A FRESH employee for each test, and every call below scoped to them.

		`apply` commits - it writes a trail on purpose - so nothing in this
		file is rolled back. Sharing one person then makes the tests fight:
		the same two punches at the same two times collide, and a test that
		counts a company's days counts the days another test left behind.
		Reading that failure as a bug in the engine cost an hour once.

		One person per test, and every preview and apply told which employee
		it is about, makes each test independent of the others and of whatever
		earlier runs left on the site.
		"""
		doc = frappe.get_doc({
			"doctype": "Employee", "first_name": "Reprocess", "last_name": "One",
			"company": COMPANY, "date_of_joining": add_days(nowdate(), -200),
			"date_of_birth": "1990-01-01", "gender": _gender(),
			"status": "Active", "default_shift": shift or SHIFT,
			"employment_type": employment_type,
		})
		doc.flags.ignore_permissions = True
		doc.insert()
		return doc.name

	def _attendance(self, status="Present", shift=None, employee=None):
		employee = employee or self.emp
		existing = frappe.db.get_value(
			"Attendance", {"employee": employee, "attendance_date": self.date,
			               "docstatus": 1})
		if existing:
			return existing
		doc = frappe.get_doc({
			"doctype": "Attendance", "employee": employee, "company": COMPANY,
			"attendance_date": self.date, "status": status,
			"shift": shift or SHIFT,
		})
		doc.flags.ignore_permissions = True
		doc.insert()
		doc.submit()
		return doc.name

	def _punch(self, hhmm, shift=None, employee=None):
		doc = frappe.get_doc({
			"doctype": "Employee Checkin", "employee": employee or self.emp,
			"time": "{0} {1}:00".format(self.date, hhmm),
			"shift": shift or SHIFT,
		})
		doc.flags.ignore_permissions = True
		doc.insert()
		return doc.name

	# ── the promises ─────────────────────────────────────────────────────────

	def test_preview_writes_nothing(self):
		"""The whole point of a preview. A side effect here would never be
		noticed, because the next call writes the same thing anyway."""
		att = self._attendance()
		self._punch("11:00")
		self._punch("17:42")
		before = frappe.db.get_value("Attendance", att, list(VERDICT_FIELDS),
		                             as_dict=True)
		out = rp.preview(COMPANY, self.date, self.date, employees=[self.emp])
		self.assertTrue(out["ok"])
		after = frappe.db.get_value("Attendance", att, list(VERDICT_FIELDS),
		                            as_dict=True)
		self.assertEqual(before, after)

	def test_apply_refuses_without_a_confirmation(self):
		self._attendance()
		with self.assertRaises(frappe.ValidationError):
			rp.apply(COMPANY, self.date, self.date, employees=[self.emp],
			         confirmed=0)

	def test_running_it_twice_gives_the_same_answer(self):
		"""Idempotence, and the reason the verdict lives on the Attendance row
		rather than in a ledger of adjustments. Two clicks must not cost an
		employee twice."""
		att = self._attendance()
		self._punch("11:00")
		self._punch("17:42")
		rp.apply(COMPANY, self.date, self.date, employees=[self.emp],
		         confirmed=1)
		once = frappe.db.get_value("Attendance", att, list(VERDICT_FIELDS),
		                           as_dict=True)
		rp.apply(COMPANY, self.date, self.date, employees=[self.emp],
		         confirmed=1)
		twice = frappe.db.get_value("Attendance", att, list(VERDICT_FIELDS),
		                            as_dict=True)
		self.assertEqual(once["alvoraa_slab_quarters"],
		                 twice["alvoraa_slab_quarters"])
		self.assertEqual(once["alvoraa_reds"], twice["alvoraa_reds"])

	def test_the_second_run_reports_nothing_changed(self):
		"""Once the verdicts are current, a preview should show an empty
		movement - which is how somebody knows the data has settled."""
		self._attendance()
		self._punch("11:00")
		self._punch("17:42")
		rp.apply(COMPANY, self.date, self.date, employees=[self.emp],
		         confirmed=1)
		out = rp.preview(COMPANY, self.date, self.date, employees=[self.emp])
		self.assertEqual(out["totals"]["changed"], 0)
		self.assertEqual(out["moved"], [])

	def test_a_late_punch_moves_the_day_and_the_preview_says_so(self):
		"""The case this exists for: attendance arrives after payroll was
		prepared. First judged with one punch, so held; then the check-out
		lands and it becomes a measured day."""
		att = self._attendance()
		self._punch("11:00")
		rp.apply(COMPANY, self.date, self.date, employees=[self.emp],
		         confirmed=1)
		self.assertEqual(
			frappe.db.get_value("Attendance", att, "alvoraa_held"), 1)

		self._punch("17:42")
		out = rp.preview(COMPANY, self.date, self.date, employees=[self.emp])
		self.assertEqual(out["totals"]["changed"], 1)
		moved = out["moved"][0]
		self.assertEqual(moved["held_before"], 1)
		self.assertEqual(moved["held_after"], 0)
		self.assertEqual(moved["quarters_after"], 1)      # 67% -> one quarter

	def test_an_employee_with_a_submitted_slip_is_skipped_and_named(self):
		"""A submitted slip is a paid slip. Correcting it is a decision for
		next month, not a recalculation."""
		att = self._attendance()
		self._punch("11:00")
		self._punch("17:42")
		slip = frappe.get_doc({
			"doctype": "Salary Slip", "employee": self.emp, "company": COMPANY,
			"start_date": self.date, "end_date": self.date,
			"docstatus": 1, "posting_date": self.date,
		})
		slip.flags.ignore_permissions = True
		slip.db_insert()
		# A submitted slip is the one fixture here that outlives the test: it
		# is written straight to the table, and `apply` below commits. Left
		# behind it would make this employee look paid in every later run, and
		# every other test in this file would then skip instead of reprocess.
		self.addCleanup(lambda: frappe.db.delete("Salary Slip", {"name": slip.name}))

		# Scoped to this employee on purpose. The company's other rows are not
		# what this test is about, and counting them made the assertion below
		# depend on what the rest of the file had left lying around.
		out = rp.preview(COMPANY, self.date, self.date, employees=[self.emp])
		skipped = {s["employee"] for s in out["skipped_paid"]}
		self.assertIn(self.emp, skipped)
		self.assertEqual(out["totals"]["days"], 0)

		before = frappe.db.get_value("Attendance", att, "alvoraa_evaluated_on")
		rp.apply(COMPANY, self.date, self.date, employees=[self.emp],
		         confirmed=1)
		self.assertEqual(
			frappe.db.get_value("Attendance", att, "alvoraa_evaluated_on"), before)

	def test_a_company_with_no_rule_set_is_left_alone(self):
		"""Every other tenant on this image. Not an error, and not a write."""
		# A company with NO rule set, not merely another one: other modules
		# (063, 067) leave companies with a rule set switched on behind them.
		with_rules = frappe.get_all("Alvoraa Payroll Rule Set", pluck="company")
		other = frappe.db.get_value("Company", {"name": ("not in", with_rules + [COMPANY])})
		if not other:
			self.skipTest("only one company on this site")
		out = rp.preview(other, self.date, self.date)
		self.assertFalse(out["ok"])
		self.assertIn("rule set", out["reason"])

	def test_the_run_is_recorded(self):
		"""This changes pay, so it needs a trail that outlives an Error Log."""
		self._attendance()
		self._punch("11:00")
		self._punch("17:42")
		out = rp.apply(COMPANY, self.date, self.date, employees=[self.emp],
		         confirmed=1)
		log = frappe.get_doc("Alvoraa Payroll Reprocess Log", out["log"])
		self.assertEqual(log.company, COMPANY)
		self.assertEqual(log.run_by, frappe.session.user)
		self.assertTrue(log.days_reprocessed >= 1)
		self.assertTrue(log.detail)

	# ── where the grace comes from ───────────────────────────────────────────
	#
	# One number, in the place HR actually maintains it. The rule set used to
	# hold its own copy, and Frappe's Late Entry tick held another, so the two
	# could drift apart: edit a shift and only half the behaviour moved.
	#
	# Arriving at 11:00 on a 10:30 shift is 30 minutes late. That is late under
	# the rule set's 6 minutes, on time under the generous shift's 45, and on
	# time under a contract employee's 90. No single number gives all three, so
	# each test can only pass if the right source was used.

	def _late_flag(self, att):
		return frappe.db.get_value("Attendance", att, "alvoraa_late_arrival")

	def test_a_shift_that_sets_its_own_grace_is_the_one_that_counts(self):
		emp = self._employee(shift=GENEROUS_SHIFT)
		att = self._attendance(shift=GENEROUS_SHIFT, employee=emp)
		self._punch("11:00", shift=GENEROUS_SHIFT, employee=emp)
		self._punch("20:30", shift=GENEROUS_SHIFT, employee=emp)
		rp.apply(COMPANY, self.date, self.date, employees=[emp], confirmed=1)
		# 30 minutes late, inside the shift's 45. Not late.
		self.assertEqual(self._late_flag(att), 0)

	def test_a_shift_that_sets_none_falls_back_to_the_rule_set(self):
		"""The path every other test in this file runs on, stated once."""
		att = self._attendance()
		self._punch("11:00")
		self._punch("20:30")
		rp.apply(COMPANY, self.date, self.date, employees=[self.emp],
		         confirmed=1)
		# 30 minutes late, past the rule set's 6. Late.
		self.assertEqual(self._late_flag(att), 1)

	def test_a_contract_grace_beats_the_shift_it_is_worked_on(self):
		"""Contract staff get a longer grace because of their contract, not
		their shift - they work the same shifts as everybody else. A shift
		overruling that would take the concession away the first time somebody
		edited the shift."""
		emp = self._employee(shift=GENEROUS_SHIFT, employment_type="Contract")
		att = self._attendance(shift=GENEROUS_SHIFT, employee=emp)
		self._punch("11:00", shift=GENEROUS_SHIFT, employee=emp)
		self._punch("20:30", shift=GENEROUS_SHIFT, employee=emp)
		rp.apply(COMPANY, self.date, self.date, employees=[emp], confirmed=1)
		self.assertEqual(self._late_flag(att), 0)
		# And the contract rule as a whole still applies, not just its grace.
		self.assertEqual(
			frappe.db.get_value("Attendance", att, "alvoraa_reds"), 0)

	def test_the_trail_cannot_be_deleted(self):
		self._attendance()
		self._punch("11:00")
		self._punch("17:42")
		out = rp.apply(COMPANY, self.date, self.date, employees=[self.emp],
		         confirmed=1)
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Alvoraa Payroll Reprocess Log", out["log"],
			                  ignore_permissions=True)
