"""Slice 063, Housekeeping: leave earned from days present (the days-present table).

The table lives on the rule set (Alvoraa Leave Credit Row). These tests pin
SEC-18 (who the table reaches), SEC-19 (a wrong table cannot be saved), SEC-20
(the credit is reported, never paid), the card and Apply facts, and the Q-S2
scope check on behalf (AC-17, AC-18, AC-124..AC-138, AC-140..AC-144).

The numbers for every row edge of both month lengths are pure tests in
test_payroll_month.py (TestLeaveFromDaysPresent). Here the site proves the parts
that need a database: the save checks, the real month summary, a real Salary
Slip, and the endpoints.
"""

import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, getdate, nowdate

from alvoraa_portal import hr_api, leave_rules, payroll_slip
from alvoraa_portal.payroll_month import MonthSummary
from alvoraa_portal.tests import leave_063_fixtures as fx
from alvoraa_portal.tests.test_leave_063_rules import LWP, Rules063Case

BASIC, STRUCTURE = "L063H Basic", "L063H Structure"
START = getdate(get_first_day(add_months(nowdate(), -1)))
END = getdate(get_last_day(START))

# Present days in the last full month, chosen so the answer is the same in a 28, 30
# or 31 day month: 14 -> 2, 20 -> 3, 26 -> 4 (the rows differ by one day, not at these).
DAYS_BY_PERSON = {"gita": 14, "geeta": 26, "hari": 26, "pooja": 26, "sushila": 26}


def _insert(d, submit=False):
	doc = frappe.get_doc(d)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc


def _component(name, abbr, kind, by_payment_days=0):
	if not frappe.db.exists("Salary Component", name):
		_insert({"doctype": "Salary Component", "salary_component": name,
		         "salary_component_abbr": abbr, "type": kind,
		         "depends_on_payment_days": by_payment_days,
		         "remove_if_zero_valued": 1, "is_tax_applicable": 0})
	frappe.db.set_value("Salary Component", name, "depends_on_payment_days", by_payment_days)


def _work(emp, days, month_start=START, company=fx.COMPANY):
	"""`days` full worked days from the first of the month, with real punches."""
	for i in range(days):
		day = add_days(month_start, i)
		_insert({"doctype": "Attendance", "employee": emp, "company": company,
		         "attendance_date": day, "status": "Present", "shift": fx.SHIFT}, submit=True)
		for t in ("10:30:00", "20:30:00"):
			_insert({"doctype": "Employee Checkin", "employee": emp,
			         "time": "%s %s" % (day, t), "shift": fx.SHIFT})


def _wipe(*employees):
	for emp in employees:
		for table in ("Salary Slip", "Additional Salary", "Attendance", "Employee Checkin"):
			frappe.db.delete(table, {"employee": emp})


def _wipe_since(emp, day):
	"""This person's attendance and punches from `day` on (the endpoints commit, so a
	rollback alone leaves them behind)."""
	for table, field in (("Attendance", "attendance_date"), ("Employee Checkin", "time")):
		names = frappe.get_all(table, filters={"employee": emp, field: [">=", day]}, pluck="name")
		if names:
			frappe.db.delete(table, {"name": ["in", names]})
	frappe.db.commit()


def setUpModule():
	global P
	P = fx.ensure_world()
	P["gita"] = fx.ensure_employee("Gita", grade="L063-A", category="L063 Contract",
	                               branch="L063 North", reports_to=P["sunil"],
	                               approver=fx.user("Sunil"), designation=fx.HK)
	for name in (payroll_slip.RED_COMPONENT, payroll_slip.GREEN_COMPONENT):
		_component(name, name[:2].upper() + "H", "Deduction" if name.startswith("Red") else "Earning")
	_component(BASIC, "L063HB", "Earning", by_payment_days=1)
	if not frappe.db.exists("Salary Structure", STRUCTURE):
		_insert({"doctype": "Salary Structure", "name": STRUCTURE, "company": fx.COMPANY,
		         "payroll_frequency": "Monthly", "currency": "INR", "is_active": "Yes",
		         "earnings": [{"salary_component": BASIC, "amount_based_on_formula": 1,
		                       "formula": "base", "depends_on_payment_days": 1},
		                      {"salary_component": payroll_slip.GREEN_COMPONENT, "amount": 0}],
		         "deductions": [{"salary_component": payroll_slip.RED_COMPONENT, "amount": 0}]},
		        submit=True)
	for who in DAYS_BY_PERSON:
		emp = P[who]
		_wipe(emp)
		frappe.db.delete("Salary Structure Assignment", {"employee": emp})
		_insert({"doctype": "Salary Structure Assignment", "employee": emp,
		         "salary_structure": STRUCTURE, "company": fx.COMPANY, "currency": "INR",
		         "from_date": add_days(START, -150), "base": 12000}, submit=True)
		_work(emp, DAYS_BY_PERSON[who])
	frappe.db.commit()


def tearDownModule():
	for who in DAYS_BY_PERSON:
		_wipe(P[who])
		frappe.db.delete("Salary Structure Assignment", {"employee": P[who]})
	frappe.db.commit()
	fx.leave_world(P.values())


def _rule_set_doc():
	return frappe.get_doc("Alvoraa Payroll Rule Set",
	                      frappe.db.get_value("Alvoraa Payroll Rule Set", {"company": fx.COMPANY}))


def _summary(emp):
	return payroll_slip.month_summary(emp, fx.COMPANY, START, END)


class TestTheRowsAreChecked(FrappeTestCase):
	"""SEC-19 / AC-130, AC-131: a typo here goes to a third party's figures, so the
	save refuses a wrong table and names the rows."""

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		frappe.clear_cache(doctype="Alvoraa Payroll Rule Set")

	def _refuses(self, rows, message):
		rs = _rule_set_doc()
		rs.set("leave_credit_rows", rows)
		with self.assertRaisesRegex(frappe.ValidationError, message):
			rs.validate()

	def _rows(self, change):
		"""DTC's ten rows with one row changed: change = {row index: {field: value}}."""
		rows = fx.credit_rows()
		for i, edit in change.items():
			rows[i].update(edit)
		return rows

	def test_dtcs_ten_rows_save(self):
		rs = _rule_set_doc()
		rs.set("leave_credit_rows", fx.credit_rows())
		rs.validate()

	def test_an_empty_table_saves(self):
		rs = _rule_set_doc()
		rs.set("leave_credit_rows", [])
		rs.validate()

	def test_a_row_that_runs_backwards_is_refused(self):
		self._refuses(self._rows({1: {"days_from": 12, "days_to": 6}}), "starts at 12 days but ends at 6")

	def test_a_table_that_does_not_start_at_zero_is_refused(self):
		self._refuses(self._rows({0: {"days_from": 1}}), "first row starts at 1 days, not 0")

	def test_a_gap_is_refused_and_named(self):
		self._refuses(self._rows({1: {"days_from": 7}}), "nothing covers 6 to 6 days, between rows 1 and 2")

	def test_an_overlap_is_refused_and_named(self):
		self._refuses(self._rows({1: {"days_from": 5}}), "rows 1 and 2 overlap")

	def test_a_last_row_that_stops_short_is_refused_for_each_month_length(self):
		self._refuses(self._rows({4: {"days_to": 30}}), "last row ends at 30 days, not 31")
		self._refuses(self._rows({9: {"days_to": 28}}), "last row ends at 28 days, not 29")

	def test_negative_leave_is_refused(self):
		self._refuses(self._rows({0: {"credits": -1}}), "cannot be negative")

	def test_more_days_present_cannot_earn_less(self):
		self._refuses(self._rows({3: {"credits": 1}}), "More days present cannot earn less")

	def test_another_designation_is_checked_on_its_own(self):
		rows = fx.credit_rows() + fx.credit_rows(fx.PANTRY)
		rs = _rule_set_doc()
		rs.set("leave_credit_rows", rows)
		rs.validate()
		rows[10]["days_from"] = 3          # the second set's first row no longer starts at 0
		self._refuses(rows, fx.PANTRY)

	def test_hr_reads_the_table_but_cannot_change_it(self):
		"""AC-131."""
		rs = _rule_set_doc()
		self.assertTrue(frappe.has_permission("Alvoraa Payroll Rule Set", "read", rs, fx.user("Ritika")))
		self.assertFalse(frappe.has_permission("Alvoraa Payroll Rule Set", "write", rs, fx.user("Ritika")))
		self.assertEqual(frappe.get_meta("Alvoraa Leave Credit Row").permissions, [])

	def test_a_row_change_shows_in_the_version_row(self):
		"""AC-131 / SEC-19: the old and new row are kept for the check."""
		rs = _rule_set_doc()
		rs.leave_credit_rows[1].credits = 2     # 6-12 earns 2 now; still never falls
		rs.flags.ignore_permissions = True
		rs.save(ignore_version=False)    # tests skip the Version row unless asked
		version = frappe.get_all("Version", filters={"ref_doctype": "Alvoraa Payroll Rule Set",
		                                             "docname": rs.name},
		                         fields=["data"], order_by="creation desc", limit=1)[0]
		self.assertIn("leave_credit_rows", version.data)


class TestWhoTheTableReaches(FrappeTestCase):
	"""SEC-18 / AC-122..AC-127, AC-132, on the real month summary."""

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_a_contract_table_person_earns_from_days_present(self):
		for who, earned in (("gita", 2), ("geeta", 4)):
			s = _summary(P[who])
			self.assertTrue(s.credit_table, who)
			self.assertEqual(s.leave_credits_earned, earned, who)

	def test_a_class_with_no_leave_earns_nothing(self):
		"""AC-124 (SEC-18b): Sushila, 26 days present."""
		s = _summary(P["sushila"])
		self.assertFalse(s.credit_table)
		self.assertEqual(s.leave_credits_earned, 0)

	def test_a_permanent_person_keeps_the_office_rule(self):
		"""AC-125 (SEC-18a): Hari has the table's designation but earns office leave:
		4 given and in paid days."""
		s = _summary(P["hari"])
		self.assertFalse(s.credit_table)
		self.assertEqual(s.leave_credits_earned, 4)
		self.assertEqual(s.paid_days, 30)

	def test_another_designation_gets_nothing(self):
		"""AC-125 (SEC-18c): Pooja, Contract, other designation."""
		self.assertEqual(_summary(P["pooja"]).leave_credits_earned, 0)

	def test_with_the_rows_deleted_the_table_stops_applying(self):
		"""AC-125 (SEC-18d), and the rollback: delete the rows and the switch is off."""
		rs = _rule_set_doc()
		rs.set("leave_credit_rows", [])
		s = payroll_slip.month_summary(P["geeta"], fx.COMPANY, START, END, rule_set=rs)
		self.assertFalse(s.credit_table)
		self.assertEqual(s.leave_credits_earned, 0)

	def test_a_table_person_earns_no_marks(self):
		"""AC-127 (SEC-18g): Contract earns no red or green."""
		s = _summary(P["geeta"])
		self.assertEqual((s.reds, s.greens), (0, 0))

	def test_the_designation_on_the_day_decides(self):
		"""AC-132 (W4): changed to another designation, the whole month reads it."""
		frappe.db.set_value("Employee", P["geeta"], "designation", fx.PANTRY)
		try:
			self.assertEqual(_summary(P["geeta"]).leave_credits_earned, 0)
		finally:
			frappe.db.set_value("Employee", P["geeta"], "designation", fx.HK)

	def test_the_why_note_reads_the_designation_from_the_row(self):
		"""AC-129: the desk report row, and the engine's own words."""
		from alvoraa_portal.alvoraa_portal.report.salary_components_and_workings import (
			salary_components_and_workings as report,
		)

		_cols, rows, _msg = report.execute({"company": fx.COMPANY, "from_date": str(START),
		                                    "to_date": str(END), "employee": P["gita"]})[:3]
		row = [r for r in rows if r["employee"] == P["gita"]][0]
		self.assertEqual((row["leave_earned"], row["leave_encashed"]), (2, 0))
		self.assertIn("%s table: 14 days present in a %d-day month gives 2. Reported to the "
		              "agency; not paid by DTC." % (fx.HK, (END - START).days + 1), row["why"])


class TestTheCreditIsNeverPaid(FrappeTestCase):
	"""SEC-20 (a-e) / AC-128, AC-129. Reporting only, the slip must not move."""

	def _clean(self):
		for who in DAYS_BY_PERSON:
			for table in ("Salary Slip", "Additional Salary"):
				frappe.db.delete(table, {"employee": P[who]})
		frappe.db.commit()

	def setUp(self):
		self._clean()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		self._clean()

	def _slip(self, emp):
		doc = frappe.get_doc({"doctype": "Salary Slip", "employee": emp, "company": fx.COMPANY,
		                      "start_date": START, "end_date": END, "posting_date": END,
		                      "payroll_frequency": "Monthly", "currency": "INR"})
		doc.flags.ignore_permissions = True
		doc.insert()
		return doc

	def test_paid_days_are_the_days_worked_alone_and_nothing_is_added(self):
		slip = self._slip(P["geeta"])
		self.assertEqual(flt(slip.payment_days, 2), 26.0, "no +4")
		self.assertFalse(frappe.get_all("Additional Salary", filters={"employee": P["geeta"]}))
		self.assertFalse([r for r in slip.earnings + slip.deductions
		                  if "Leave" in (r.salary_component or "")])

	def test_the_slip_is_the_same_with_the_rows_deleted(self):
		first = self._slip(P["geeta"])
		with_rows = flt(first.payment_days, 2)
		frappe.delete_doc("Salary Slip", first.name, force=True, ignore_permissions=True)
		rs = _rule_set_doc()
		rs.set("leave_credit_rows", [])
		with patch.object(payroll_slip, "rule_set_for", return_value=rs):
			without = flt(self._slip(P["geeta"]).payment_days, 2)
		self.assertEqual(without, with_rows)

	def test_office_staff_on_the_same_days_still_get_their_credit(self):
		"""SEC-20 (e): Hari, 26 days present, 26 + 4."""
		self.assertEqual(flt(self._slip(P["hari"]).payment_days, 2), 30.0)

	def test_encashed_is_zero_and_used_is_real(self):
		s = _summary(P["geeta"])
		self.assertEqual(s.leave_encashed, 0)
		self.assertEqual(flt(s.paid_days, 2), 26.0)


class TableCase(Rules063Case):
	"""Like the other 063 cases, but it keeps the last month's attendance that
	setUpModule built for the table people (the shared case wipes attendance)."""

	def _clear(self):
		frappe.set_user("Administrator")
		fx.clear_leave(*[v for k, v in P.items() if k not in DAYS_BY_PERSON])
		for name in frappe.get_all("Leave Application", pluck="name",
		                           filters={"employee": ["in", [P[k] for k in DAYS_BY_PERSON]]}):
			frappe.delete_doc("Leave Application", name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def setUp(self):
		self._clear()

	def tearDown(self):
		frappe.db.rollback()
		self._clear()


class TestTheCardForTableStaff(TableCase):
	"""AC-17, AC-18, AC-133..AC-138: list two, with no pay."""

	def _card(self, who="geeta"):
		emp = frappe.db.get_value("Employee", P[who], ["name", "company"], as_dict=True)
		return leave_rules.paid_leaves_card(emp)

	def test_the_keys_are_list_two_exactly(self):
		"""AC-138: nothing more, and the cap keys only when they apply."""
		card = self._card()
		self.assertEqual(set(card), set(leave_rules.CARD_KEYS_TABLE))
		self.assertTrue(card["housekeeping"])
		self.assertEqual(card["cap"], 4)

	def test_no_pay_figure_reaches_the_card(self):
		"""AC-18 / SEC-20 (a): the Basic is 12,000 on her assignment, and nothing
		in the block carries it or any pay name."""
		text = json.dumps(self._card())
		for never in ("to_be_paid_out", "paid_days", "daily_rate", "earning_basic", "gross",
		              "net", "12000", "reds", "greens", "notes"):
			self.assertNotIn(never, text)

	def test_at_the_cap_there_is_no_next_step(self):
		"""AC-135."""
		full = MonthSummary(leave_credits_earned=4.0, days_for_gate=27.0, credit_table=True)
		with patch.object(leave_rules, "table_summary", return_value=full):
			card = self._card()
		self.assertEqual(card["earned"], 4)
		self.assertNotIn("next_at", card)
		self.assertNotIn("days_to_next", card)
		self.assertEqual(set(card), set(leave_rules.CARD_KEYS_TABLE) - {"next_at", "days_to_next"})

	def test_the_next_step_is_the_real_distance(self):
		"""AC-139: 14.5 days present, earned 2, next at 19, 4.5 more."""
		mid = MonthSummary(leave_credits_earned=2.0, days_for_gate=14.5, next_credit_at=19,
		                   credit_table=True)
		with patch.object(leave_rules, "table_summary", return_value=mid):
			card = self._card()
		self.assertEqual((card["attended_so_far"], card["next_at"], card["days_to_next"]), (14.5, 19, 4.5))

	def test_the_rule_box_rows_are_this_months_and_the_other_lengths_starts(self):
		"""AC-133 / AC-136: rule-set facts the page words around."""
		card = self._card()
		self.assertEqual(card["rows"]["this"][0], [6, 12, 1.0] if card["month_length"] == "30-31"
		                 else [5, 11, 1.0])
		other = [6, 13, 19, 26] if card["month_length"] == "28-29" else [5, 12, 18, 25]
		self.assertEqual(card["rows"]["other_starts"], other)

	def test_a_class_with_no_leave_gets_the_class_sentence(self):
		"""AC-137 / X-9: the class is why, not the category."""
		card = self._card("sushila")
		self.assertFalse(card["earns"])
		self.assertEqual(card["class"], "L063-NoLeave")
		self.assertIsNone(card["category"])
		self.assertNotIn("housekeeping", card)

	def test_contract_staff_outside_the_table_keep_the_category_sentence(self):
		card = self._card("pooja")
		self.assertFalse(card["earns"])
		self.assertEqual(card["category"], "L063 Contract")

	def test_an_office_person_with_the_same_designation_gets_list_one(self):
		card = self._card("hari")
		self.assertTrue(set(card) <= set(leave_rules.CARD_KEYS_OFFICE))
		self.assertIn("to_be_paid_out", card)
		self.assertNotIn("housekeeping", card)

	def test_the_card_costs_the_same_queries_for_more_staff(self):
		"""AC-23: one person, one summary, whatever the headcount."""
		def count():
			emp = frappe.db.get_value("Employee", P["geeta"], ["name", "company"], as_dict=True)
			leave_rules.paid_leaves_card(emp)
			with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as spy:
				leave_rules.paid_leaves_card(emp)
			return spy.call_count

		before = count()
		extra = [fx.ensure_employee("TExtra%d" % i, grade="L063-A", category="L063 Contract",
		                            designation=fx.HK) for i in range(5)]
		try:
			after = count()
		finally:
			for e in extra:
				frappe.db.set_value("Employee", e, "status", "Left")
		self.assertEqual(before, after)


class TestApplyFactsForTableStaff(TableCase):
	"""AC-140..AC-144, with the Q-S2 scope check."""

	def _present_this_month(self, who, days):
		"""`days` worked days from the 1st of this month, up to yesterday."""
		first = getdate(get_first_day(nowdate()))
		if (getdate(nowdate()) - first).days < days:
			self.skipTest("too close to the 1st for this case")
		_work(P[who], days, first)

	def tearDown(self):
		super().tearDown()
		_wipe_since(P["geeta"], getdate(get_first_day(nowdate())))

	def _types(self, caller, who):
		frappe.set_user(fx.user(caller))
		try:
			return {t["leave_type"]: t for t in
			        hr_api.get_leave_summary(employee_id=P[who])["types_offered"]}
		finally:
			frappe.set_user("Administrator")

	def test_hr_in_scope_sees_the_days_left_and_no_pay(self):
		"""AC-144 / Q-S2: 6 days present this month earns 1."""
		self._present_this_month("geeta", 6)
		row = self._types("Ritika", "geeta")[fx.PAID]
		self.assertEqual(row["left"], 1)
		self.assertNotIn("to_be_paid_out", json.dumps(row))

	def test_hr_in_another_branch_is_refused(self):
		"""Bad news 3 and F-3: Anil looks after another branch, so Geeta's summary
		is refused outright - no figure, no class name."""
		self._present_this_month("geeta", 6)
		with self.assertRaises(frappe.PermissionError):
			self._types("Anil", "geeta")

	def test_an_agency_worker_with_no_class_is_told_so_not_blamed_on_the_work_type(self):
		"""m-1: Geeta's class cleared. The card must not say 'Contract staff do not
		get Paid Leaves', and the Apply list says no class is set."""
		frappe.db.set_value("Employee", P["geeta"], "grade", None)
		card = leave_rules.paid_leaves_card(frappe.get_doc("Employee", P["geeta"]))
		self.assertFalse(card["earns"])
		self.assertIsNone(card["class"])
		self.assertIsNone(card["category"])
		row = self._types("Ritika", "geeta")[LWP]
		self.assertEqual(row.get("no_class"), 1)
		self.assertNotIn("no_paid_class", row)

	def test_days_used_and_waiting_are_taken_off(self):
		"""R-98: left = earned so far - used - waiting."""
		self._present_this_month("geeta", 13)       # earns 2
		d, = self.need(fx.future_day(1))
		fx.apply_as(fx.user("Ritika"), leave_type=fx.PAID, from_date=d, to_date=d,
		            on_behalf_of=P["geeta"])
		self.assertEqual(self._types("Ritika", "geeta")[fx.PAID]["left"], 1)

	def test_a_class_with_no_leave_is_not_offered_paid_leaves(self):
		"""AC-124 / SEC-2: hidden in the list and refused by the server."""
		types = self._types("Ritika", "sushila")
		self.assertNotIn(fx.PAID, types)
		self.assertEqual(types[LWP]["no_paid_class"], "L063-NoLeave")
		d, = self.need(fx.future_day(1))
		with self.assertRaises(frappe.PermissionError):
			fx.apply_as(fx.user("Ritika"), leave_type=fx.PAID, from_date=d, to_date=d,
			            on_behalf_of=P["sushila"])

	def test_contract_staff_outside_the_table_have_no_class_reason(self):
		self.assertNotIn("no_paid_class", self._types("Ritika", "pooja")[LWP])

	def _preview(self, caller, who, leave_type, d, **kw):
		frappe.set_user(fx.user(caller))
		try:
			return hr_api.preview_leave_request(leave_type, d, d, on_behalf_of=P[who], **kw)
		finally:
			frappe.set_user("Administrator")

	def test_the_preview_for_table_staff_carries_earned_and_next_and_no_special_day(self):
		"""AC-141, AC-143 (R-94): no special-day line for an agency person."""
		self._present_this_month("geeta", 6)
		d, = self.need(fx.future_day(1))
		fx.set_special_day(d)
		pre = self._preview("Ritika", "geeta", fx.PAID, d)
		self.assertEqual((pre["housekeeping"], pre["earned"]), (1, 1))
		self.assertIn(pre["next_at"], (12, 13), "the next row starts at 13 (30-31 days) or 12 (28-29)")
		self.assertNotIn("special_day", pre)
		self.assertEqual(pre["verdict"], "ok")
		office = self._preview("Ritika", "hari", fx.PAID, d)
		self.assertNotIn("housekeeping", office)

	def test_not_enough_is_checked_on_behalf_too(self):
		"""AC-142 / A-1: 1 day earned, 2 asked for."""
		self._present_this_month("geeta", 6)
		d, e = self.need(fx.future_day(1), fx.future_day(2))
		frappe.set_user(fx.user("Ritika"))
		try:
			pre = hr_api.preview_leave_request(fx.PAID, d, e, on_behalf_of=P["geeta"])
		finally:
			frappe.set_user("Administrator")
		self.assertEqual((pre["verdict"], pre["reason_code"]), ("block", "pl_short"))
		self.assertEqual((pre["earned"], pre["pl_left"]), (1, 1))

	def test_a_no_leave_person_asking_for_lwp_is_still_marked_agency_paid(self):
		"""R-93: the words follow the designation, not the class."""
		d, = self.need(fx.future_day(1))
		self.assertEqual(self._preview("Ritika", "sushila", LWP, d)["housekeeping"], 1)

	def test_the_server_does_not_cap_the_filing_at_left(self):
		"""AC-34 is unchanged: the preview blocks, the server does not."""
		d, e = self.need(fx.future_day(1), fx.future_day(2))
		res = fx.apply_as(fx.user("Ritika"), leave_type=fx.PAID, from_date=d, to_date=e,
		                  on_behalf_of=P["geeta"])
		self.assertTrue(res["name"])
