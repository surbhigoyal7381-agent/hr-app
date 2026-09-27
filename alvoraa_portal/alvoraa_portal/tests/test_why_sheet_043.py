"""Slice 043 AC-27 to AC-31 and AC-57 to AC-61: the Why? sheet tells the truth.

This is the most sensitive thing in Wave 3. It is the first place in this
product where an employee is told that a decision about their pay was made by a
machine, and the whole value of it is that what it says is true.

**AC-58 is the one that matters most, and it is easy to write backwards.** The
spec's revision 1 promised the employee "fix the day first - the rule follows
the attendance record". It does not: `late_rules._process_week` skips any
Attendance Deduction with `docstatus == 1`, in the weekly run and in HR's
catch-up. So the test here is driven from a correction approved AFTER the
deduction was submitted, and asserts on the DOCUMENTS - the deduction's
docstatus, its leave ledger entry, its additional salary - not on the screen.
Written the other way round it passes and proves the opposite.

**AC-61.** Showing a person a decision about them must create no new record
about them. Asserted as a write count around a full call, not as a promise.

**This slice's own company and people**, tagged S043W.
"""

import ast
import io
import os

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

import alvoraa_portal
from alvoraa_portal import hr_api, pay_api

TAG = "S043W"
COMPANY = "S043W Why Company"
ABBR = "S43W"
SHIFT = "S043W Shift"
RULE = "S043W Rule"
RULE_TWO = "S043W Second Rule"
COMPONENT = "S043W Loss Of Pay"
LEAVE_TYPE = "S043W Casual Leave"
HOLIDAYS = "S043W Holidays"

PAYROLL_ON = ("portal", "leaves", "attendance", "expenses", "payroll")
PAYROLL_OFF = ("portal", "leaves", "attendance", "expenses")


def _features(names):
	frappe.local.conf["features"] = list(names)


def _clear_features():
	frappe.local.conf.pop("features", None)


def _ensure(doctype, name, **values):
	if name and frappe.db.exists(doctype, name):
		return frappe.get_doc(doctype, name)
	doc = frappe.get_doc({"doctype": doctype, **values})
	if name:
		doc.name = name
		doc.set("__newname", name)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_mandatory=True)
	return doc


def _user(local):
	email = "s043w.%s@example.com" % local
	if not frappe.db.exists("User", email):
		doc = frappe.get_doc({"doctype": "User", "email": email,
		                      "first_name": local.title(),
		                      "send_welcome_email": 0,
		                      "roles": [{"role": "Employee"}]})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
	frappe.db.set_value("User", email, "module_profile", None,
	                    update_modified=False)
	frappe.db.delete("Block Module", {"parent": email, "parenttype": "User"})
	frappe.clear_cache(user=email)
	return email


def _employee(first, company, login, holidays):
	name = frappe.db.get_value("Employee", {"first_name": first,
	                                        "last_name": TAG}, "name")
	doc = frappe.get_doc("Employee", name) if name else frappe.get_doc({
		"doctype": "Employee", "first_name": first, "last_name": TAG,
		"date_of_birth": "1990-01-01",
		"gender": frappe.get_all("Gender", pluck="name", limit=1)[0]})
	doc.company = company
	doc.date_of_joining = "2024-01-01"
	doc.status = "Active"
	doc.user_id = login
	doc.holiday_list = holidays
	doc.create_user_permission = 0
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


class WhySheetFixture(FrappeTestCase):
	"""One submitted deduction with a real Additional Salary behind it."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure("Company", COMPANY, company_name=COMPANY,
		                      abbr=ABBR, default_currency="INR",
		                      country="India").name
		cls.shift = _ensure("Shift Type", SHIFT, shift_type=SHIFT,
		                    start_time="09:30:00", end_time="18:30:00").name
		cls.component = _ensure("Salary Component", COMPONENT,
		                        salary_component=COMPONENT,
		                        salary_component_abbr="S43WLP",
		                        type="Deduction").name
		_ensure("Leave Type", LEAVE_TYPE, leave_type_name=LEAVE_TYPE)
		holidays = _ensure("Holiday List", HOLIDAYS,
		                   holiday_list_name=HOLIDAYS, from_date="2026-01-01",
		                   to_date="2026-12-31").name

		cls.rahul_login = _user("rahul")
		cls.other_login = _user("other")
		cls.rahul = _employee("Rahul", cls.company, cls.rahul_login, holidays)
		cls.other = _employee("Other", cls.company, cls.other_login, holidays)

		cls.rule = _ensure(
			"Attendance Deduction Rule", RULE, rule_name=RULE,
			company=cls.company, shift_type=cls.shift, enabled=1,
			week_start_day="Monday", late_threshold_minutes=60,
			count_early_exit=0, free_violations_per_week=1,
			deduction_per_violation_days=0.25, round_up_from_days=0.75,
			round_up_to_days=1.0, deduct_from_leave_first=0,
			lwp_salary_component=cls.component,
			notify_employee=0, notify_manager=0).name

		# A SECOND rule with different numbers. AC-57 asserts each element
		# against two fixtures, so no sentence can be a hard-coded one.
		cls.rule_two = _ensure(
			"Attendance Deduction Rule", RULE_TWO, rule_name=RULE_TWO,
			company=cls.company, shift_type=cls.shift, enabled=0,
			week_start_day="Sunday", late_threshold_minutes=45,
			count_early_exit=0, free_violations_per_week=2,
			deduction_per_violation_days=0.5, round_up_from_days=0.9,
			round_up_to_days=1.0, deduct_from_leave_first=0,
			lwp_salary_component=cls.component,
			notify_employee=0, notify_manager=0).name

		# Rahul must be COVERED by the rule, or `_process_week` iterates nobody
		# and AC-58's document test can never fail. It could not, until this
		# was added - found by disabling the skip and watching nothing go red.
		for employee in (cls.rahul, cls.other):
			if not frappe.db.exists("Shift Assignment",
			                        {"employee": employee,
			                         "shift_type": cls.shift, "docstatus": 1}):
				sa = frappe.get_doc({
					"doctype": "Shift Assignment", "employee": employee,
					"shift_type": cls.shift, "company": cls.company,
					"start_date": "2026-01-01", "status": "Active"})
				sa.flags.ignore_permissions = True
				sa.insert(ignore_permissions=True)
				sa.submit()

		cls.mine, cls.my_extra = cls._deduction(cls.rahul, cls.rule,
		                                        "2026-08-17", "2026-08-23")
		cls.theirs, cls.their_extra = cls._deduction(
			cls.other, cls.rule, "2026-08-17", "2026-08-23")
		cls.second, cls.second_extra = cls._deduction(
			cls.rahul, cls.rule_two, "2026-07-20", "2026-07-26")
		frappe.db.commit()

	@classmethod
	def _deduction(cls, employee, rule, start, end):
		"""A SUBMITTED deduction plus the Additional Salary that carries it.

		The Additional Salary is made here rather than by `on_submit`, because
		valuing a loss of pay needs a Salary Structure Assignment and this file
		is about the explanation, not about the valuation.
		"""
		existing = frappe.db.get_value(
			"Attendance Deduction",
			{"employee": employee, "week_start": start, "rule": rule}, "name")
		if existing:
			extra = frappe.db.get_value(
				"Additional Salary",
				{"ref_doctype": "Attendance Deduction", "ref_docname": existing},
				"name")
			return existing, extra
		doc = frappe.get_doc({
			"doctype": "Attendance Deduction",
			"employee": employee,
			"employee_name": frappe.db.get_value("Employee", employee,
			                                     "employee_name"),
			"company": cls.company,
			"rule": rule,
			"week_start": start,
			"week_end": end,
			"violations": [
				{"attendance_date": "2026-08-18", "actual_time": "10:47:00",
				 "minutes": 77, "violation_type": "Late Arrival"},
				{"attendance_date": "2026-08-19", "actual_time": "10:35:00",
				 "minutes": 65, "violation_type": "Late Arrival"},
				{"attendance_date": "2026-08-20", "actual_time": "10:40:00",
				 "minutes": 70, "violation_type": "Late Arrival"},
				{"attendance_date": "2026-08-21", "actual_time": "11:00:00",
				 "minutes": 90, "violation_type": "Late Arrival"},
			],
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_mandatory=True)
		doc.db_set("docstatus", 1, update_modified=False)

		extra = frappe.get_doc({
			"doctype": "Additional Salary", "employee": employee,
			"company": cls.company, "salary_component": cls.component,
			"amount": 548.39, "payroll_date": end, "currency": "INR",
			"ref_doctype": "Attendance Deduction", "ref_docname": doc.name,
			"overwrite_salary_structure_amount": 0})
		extra.flags.ignore_permissions = True
		extra.flags.ignore_validate = True
		extra.insert(ignore_permissions=True, ignore_mandatory=True)
		extra.db_set("docstatus", 1, update_modified=False)
		return doc.name, extra.name

	def setUp(self):
		frappe.set_user(self.rahul_login)
		_features(PAYROLL_ON)

	def tearDown(self):
		_clear_features()
		frappe.set_user("Administrator")


class TestTheFixtureIsReal(WhySheetFixture):
	"""Every assertion below is worthless if these are not true."""

	def test_the_deduction_is_submitted(self):
		self.assertEqual(
			frappe.db.get_value("Attendance Deduction", self.mine, "docstatus"), 1)

	def test_the_additional_salary_points_back_at_it(self):
		row = frappe.db.get_value("Additional Salary", self.my_extra,
		                          ["ref_doctype", "ref_docname"], as_dict=True)
		self.assertEqual(row.ref_doctype, "Attendance Deduction")
		self.assertEqual(row.ref_docname, self.mine)

	def test_the_two_rules_genuinely_differ(self):
		one = frappe.get_doc("Attendance Deduction Rule", self.rule)
		two = frappe.get_doc("Attendance Deduction Rule", self.rule_two)
		self.assertNotEqual(one.free_violations_per_week,
		                    two.free_violations_per_week)
		self.assertNotEqual(one.deduction_per_violation_days,
		                    two.deduction_per_violation_days)


class TestWhoMayCallIt(WhySheetFixture):
	"""AC-28, AC-31, AC-42's three cases."""

	def test_guest_is_refused(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			frappe.is_whitelisted(pay_api.get_deduction_explanation)

	def test_a_caller_with_no_employee_record_is_refused(self):
		frappe.set_user(_user("asha"))
		with self.assertRaises(frappe.PermissionError):
			pay_api.get_deduction_explanation(self.my_extra)

	def test_somebody_elses_deduction_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			pay_api.get_deduction_explanation(self.their_extra)

	def test_my_own_is_not(self):
		out = pay_api.get_deduction_explanation(self.my_extra)
		self.assertEqual(out["deduction"], self.mine)

	def test_all_four_refusal_causes_give_one_sentence(self):
		"""AC-31, including the Why? endpoint. Asserted together."""
		def message(*args):
			try:
				pay_api.get_deduction_explanation(*args)
			except frappe.PermissionError as exc:
				return str(exc)
			self.fail("it did not refuse")

		somebody_elses = message(self.their_extra)
		frappe.set_user(_user("asha"))
		no_employee = message(self.my_extra)
		frappe.set_user(self.rahul_login)
		_features(PAYROLL_OFF)
		never_bought = message(self.my_extra)
		does_not_exist = message("HR-ADS-NOPE-0001")

		self.assertEqual(
			[somebody_elses, no_employee, never_bought, does_not_exist],
			[hr_api.PAYSLIP_UNAVAILABLE] * 4,
			"a refusal that varies lets a caller walk names (AC-31)")

	def test_a_tenant_without_payroll_cannot_reach_it(self):
		_features(PAYROLL_OFF)
		with self.assertRaises(frappe.PermissionError):
			pay_api.get_deduction_explanation(self.my_extra)


class TestTheNumbersAreReadNotRecomputed(WhySheetFixture):
	"""AC-27."""

	def test_the_payload_keys_are_the_fixed_list(self):
		out = pay_api.get_deduction_explanation(self.my_extra)
		self.assertEqual(sorted(out.keys()), sorted(pay_api.WHY_KEYS))

	def test_the_violations_are_the_stored_ones_with_the_free_one_marked(self):
		out = pay_api.get_deduction_explanation(self.my_extra)
		self.assertEqual(len(out["violations"]), 4)
		self.assertEqual(sum(1 for v in out["violations"] if not v["counted"]), 1)
		self.assertEqual(out["counted_violations"], 3)

	def test_the_violation_rows_carry_no_document_ids(self):
		out = pay_api.get_deduction_explanation(self.my_extra)
		for row in out["violations"]:
			self.assertEqual(sorted(row.keys()),
			                 sorted(pay_api.VIOLATION_FIELDS))

	def test_editing_the_rule_today_does_not_move_a_stored_figure(self):
		"""The reason AC-27 says read, not recompute. A person must never be
		shown a number that was never applied to them."""
		before = pay_api.get_deduction_explanation(self.my_extra)
		frappe.db.set_value("Attendance Deduction Rule", self.rule,
		                    "deduction_per_violation_days", 0.5)
		frappe.clear_cache(doctype="Attendance Deduction Rule")
		try:
			after = pay_api.get_deduction_explanation(self.my_extra)
			self.assertEqual(before["deduction_days"], after["deduction_days"])
			self.assertEqual(before["computed_days"], after["computed_days"])
		finally:
			frappe.db.set_value("Attendance Deduction Rule", self.rule,
			                    "deduction_per_violation_days", 0.25)
			frappe.clear_cache(doctype="Attendance Deduction Rule")

	def test_the_stored_explanation_text_never_leaves(self):
		"""It is technical, and it is the same string that goes in the email."""
		out = frappe.as_json(pay_api.get_deduction_explanation(self.my_extra))
		stored = frappe.db.get_value("Attendance Deduction", self.mine,
		                             "explanation")
		if stored:
			self.assertNotIn(stored, out)


class TestItSaysItWasAutomatic(WhySheetFixture):
	"""AC-57, against TWO rule fixtures so no sentence can be hard-coded."""

	def test_it_says_nobody_looked_at_the_week(self):
		for extra in (self.my_extra, self.second_extra):
			out = pay_api.get_deduction_explanation(extra)
			self.assertIn("automatically", out["how_it_was_decided"])
			self.assertIn("Nobody looked at your week by hand",
			              out["how_it_was_decided"])

	def test_it_names_the_rule_that_decided_it_and_the_rule_moves(self):
		first = pay_api.get_deduction_explanation(self.my_extra)
		second = pay_api.get_deduction_explanation(self.second_extra)
		self.assertIn(RULE, first["how_it_was_decided"])
		self.assertIn(RULE_TWO, second["how_it_was_decided"])
		self.assertNotEqual(first["how_it_was_decided"],
		                    second["how_it_was_decided"])

	def test_it_says_when(self):
		out = pay_api.get_deduction_explanation(self.my_extra)
		self.assertTrue(out["decided_on"])
		self.assertIn("2026", out["how_it_was_decided"])

	def test_the_free_allowance_comes_from_the_record_not_the_copy(self):
		self.assertEqual(
			pay_api.get_deduction_explanation(self.my_extra)["free_per_week"], 1)
		self.assertEqual(
			pay_api.get_deduction_explanation(self.second_extra)["free_per_week"], 2)

	def test_it_says_where_the_days_came_from(self):
		out = pay_api.get_deduction_explanation(self.my_extra)
		self.assertIn("taken_from_leave", out)
		self.assertIn("lwp_days", out)

	def test_all_seven_blocks_are_present_and_none_is_blank(self):
		for extra in (self.my_extra, self.second_extra):
			out = pay_api.get_deduction_explanation(extra)
			for key in ("how_it_was_decided", "if_a_day_is_wrong",
			            "what_a_correction_does_not_do", "getting_it_put_back",
			            "who_to_go_to"):
				self.assertTrue(out[key].strip(), "%s is blank" % key)


class TestTheRemedyIsTheRemedyThatExists(WhySheetFixture):
	"""AC-58 (PRIV-8, ALV-115).

	Driven from a correction approved AFTER the deduction was submitted, and
	asserted on the DOCUMENTS. Written the other way round it passes and proves
	the opposite.
	"""

	def test_the_rule_actually_covers_this_employee(self):
		"""The guard that was missing.

		`covered_employees` keeps only employees with an Active Shift
		Assignment for the rule's shift type. Without one, `_process_week`
		iterates nobody, and the test below passes whatever the skip does -
		which is how it stood until the skip was deliberately disabled and
		nothing went red.
		"""
		from hrms.alvoraa_late_rules.late_rules import covered_employees
		rule = frappe.get_doc("Attendance Deduction Rule", self.rule)
		self.assertIn(self.rahul,
		              [e.name for e in covered_employees(rule)])

	def test_a_later_run_skips_a_submitted_deduction(self):
		"""(a) The fact the wording has to agree with.

		A correction approved in September changes the Attendance record. The
		next run of the rule - weekly or HR's catch-up - sees a submitted
		deduction for that week and skips it, so the deduction, the leave
		ledger entry and the additional salary are all untouched.
		"""
		from hrms.alvoraa_late_rules.late_rules import process_week

		before = frappe.db.get_value(
			"Attendance Deduction", self.mine,
			["docstatus", "deduction_days", "additional_salary"], as_dict=True)
		extra_before = frappe.db.get_value("Additional Salary", self.my_extra,
		                                   ["amount", "docstatus"], as_dict=True)

		# The correction lands: the late arrival on 18 August was wrong.
		att = frappe.get_doc({
			"doctype": "Attendance", "employee": self.rahul,
			"attendance_date": "2026-08-18", "status": "Present",
			"company": self.company, "shift": self.shift,
			"in_time": "2026-08-18 09:28:00", "out_time": "2026-08-18 18:35:00"})
		att.flags.ignore_permissions = True
		att.flags.ignore_validate = True
		att.insert(ignore_permissions=True, ignore_mandatory=True)
		att.db_set("docstatus", 1, update_modified=False)
		frappe.db.commit()

		rule = frappe.get_doc("Attendance Deduction Rule", self.rule)
		result = process_week(rule, "2026-08-17")

		after = frappe.db.get_value(
			"Attendance Deduction", self.mine,
			["docstatus", "deduction_days", "additional_salary"], as_dict=True)
		extra_after = frappe.db.get_value("Additional Salary", self.my_extra,
		                                  ["amount", "docstatus"], as_dict=True)

		self.assertEqual(after.docstatus, 1)
		self.assertEqual(after, before,
		                 "the deduction moved after a later run - the screen's "
		                 "remedy wording would then be wrong the other way")
		self.assertEqual(extra_after, extra_before)
		self.assertEqual(result["created"], 0)

	def test_the_wording_agrees_with_that(self):
		"""(b)"""
		out = pay_api.get_deduction_explanation(self.my_extra)
		self.assertIn("does not undo this deduction",
		              out["what_a_correction_does_not_do"])
		self.assertIn("does not work it out again",
		              out["what_a_correction_does_not_do"])

	def test_it_says_a_correction_still_helps_later_weeks(self):
		out = pay_api.get_deduction_explanation(self.my_extra)
		self.assertIn("counts for the weeks after it", out["if_a_day_is_wrong"])

	def test_the_route_back_names_the_payslip_deadline(self):
		out = pay_api.get_deduction_explanation(self.my_extra)
		self.assertIn("before that month's payslip is finalised",
		              out["getting_it_put_back"])


class TestTheFalseSentenceCannotComeBack(FrappeTestCase):
	"""AC-58(c). A static check over everything Wave 3 ships to the browser."""

	FALSE = ("the rule follows the attendance record",
	         "fix the day first")

	def _shipped_files(self):
		root = os.path.dirname(os.path.abspath(alvoraa_portal.__file__))
		found = []
		for folder in ("", "public/js/ess", "public/css/ess",
		               "templates/includes/ess",
		               "templates/includes/ess/parts"):
			base = os.path.join(root, folder) if folder else root
			if not os.path.isdir(base):
				continue
			for name in sorted(os.listdir(base)):
				if name.endswith((".py", ".js", ".html")):
					found.append(os.path.join(base, name))
		return found

	def test_there_are_files_to_check(self):
		self.assertTrue(self._shipped_files())

	def test_the_false_remedy_is_nowhere(self):
		"""Strings INCLUDED, and that is the whole point.

		The first version of this check stripped string literals out of Python
		before searching - borrowed from the `ignore_permissions` check, where
		prose is the false positive. Here it made the check useless: the
		wording IS a string literal, so putting the false sentence back into
		`pay_api` left it green. It was caught by deliberately putting the
		sentence back and watching only ONE assertion go red.

		So: comments are stripped (a comment ships to nobody), strings are
		kept, and `pay_api` is written so it never quotes the false sentence -
		not even to say it is false.
		"""
		for path in self._shipped_files():
			text = _without_comments(path)
			for phrase in self.FALSE:
				self.assertNotIn(
					phrase, text.lower(),
					"%s ships the remedy that does not exist (AC-58c). "
					"A submitted deduction is skipped by every later run."
					% os.path.basename(path))

	def test_the_check_reads_strings_and_not_just_code(self):
		"""The hole the first version had, pinned."""
		import tempfile
		with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
		                                 encoding="utf-8") as handle:
			handle.write('X = "fix the day first"' + chr(10))
			temp = handle.name
		try:
			self.assertIn("fix the day first", _without_comments(temp))
		finally:
			os.unlink(temp)

	def test_this_check_can_actually_fail(self):
		self.assertIn("the rule follows the attendance record",
		              "if a day here is wrong, fix the day first - "
		              "the rule follows the attendance record")


class TestNobodyIsNamedAndItSaysSo(WhySheetFixture):
	"""AC-60 (PRIV-7). D-7's fail-closed default.

	`Attendance Deduction Rule` has no owner field - asserted here, so the day
	somebody adds one this test tells them to revisit the wording.
	"""

	def test_the_rule_really_has_no_owner_field(self):
		meta = frappe.get_meta("Attendance Deduction Rule")
		self.assertFalse(
			meta.has_field("accountable_person"),
			"an owner field exists now - D-7 is answered, so take the fallback "
			"wording out and name the person (AC-60)")

	def test_the_payload_says_nobody_is_named(self):
		out = pay_api.get_deduction_explanation(self.my_extra)
		self.assertFalse(out["accountable_named"])

	def test_the_contact_line_is_not_blank(self):
		out = pay_api.get_deduction_explanation(self.my_extra)
		self.assertTrue(out["who_to_go_to"].strip())

	def test_it_says_plainly_that_no_individual_is_named(self):
		out = pay_api.get_deduction_explanation(self.my_extra)
		self.assertIn("no individual is named on this rule yet",
		              out["who_to_go_to"])

	def test_nothing_in_the_sheet_claims_a_human_reviewed_the_case(self):
		out = pay_api.get_deduction_explanation(self.my_extra)
		text = " ".join(str(v) for v in out.values()).lower()
		for claim in ("reviewed by", "was reviewed", "checked by",
		              "approved by hr", "a manager approved"):
			self.assertNotIn(claim, text,
			                 "the sheet implies human review of this week")


class TestShowingItWritesNothing(WhySheetFixture):
	"""AC-61 (PRIV-10). A write count around a full call."""

	def _counts(self):
		return {
			doctype: frappe.db.count(doctype)
			for doctype in ("Attendance Deduction", "Additional Salary",
			                "Leave Ledger Entry", "Access Log", "Activity Log",
			                "Version", "Comment")
			if frappe.db.exists("DocType", doctype)
		}

	def test_no_row_of_any_kind_appears(self):
		before = self._counts()
		pay_api.get_deduction_explanation(self.my_extra)
		pay_api.get_deduction_explanation(self.my_extra)
		self.assertEqual(self._counts(), before,
		                 "showing a person a decision about them created a new "
		                 "record about them (AC-61)")

	def test_the_deduction_itself_is_not_touched(self):
		before = frappe.db.get_value("Attendance Deduction", self.mine,
		                             "modified")
		pay_api.get_deduction_explanation(self.my_extra)
		self.assertEqual(
			frappe.db.get_value("Attendance Deduction", self.mine, "modified"),
			before)

	def test_the_module_has_no_write_call_at_all(self):
		"""Static, because a write can hide behind a branch a test never takes."""
		code = _code_only(os.path.join(
			os.path.dirname(os.path.abspath(alvoraa_portal.__file__)),
			"pay_api.py"))
		for banned in ("db_set", "insert", "save", "db_insert", "db_update",
		               "set_value", "delete", "submit", "ignore_permissions"):
			self.assertNotIn(banned, code,
			                 "pay_api.py contains `%s` - it is a read path "
			                 "(AC-61, AC-43)" % banned)


class TestAHandEnteredDeduction(WhySheetFixture):
	"""AC-29."""

	def test_a_line_with_nothing_behind_it_says_so(self):
		extra = frappe.get_doc({
			"doctype": "Additional Salary", "employee": self.rahul,
			"company": self.company, "salary_component": self.component,
			"amount": 100, "payroll_date": "2026-08-23", "currency": "INR",
			"overwrite_salary_structure_amount": 0})
		extra.flags.ignore_permissions = True
		extra.flags.ignore_validate = True
		extra.insert(ignore_permissions=True, ignore_mandatory=True)
		# Submitted, because a draft Additional Salary never reached a payslip
		# and so can never be the line somebody is asking about.
		extra.db_set("docstatus", 1, update_modified=False)
		frappe.db.commit()
		self.assertEqual(pay_api.get_deduction_explanation(extra.name),
		                 {"hand_entered": True})

	def test_somebody_elses_hand_entered_line_is_refused_not_answered(self):
		"""AC-28. It must not answer "hand entered" about a line that is not
		theirs: that is an answer about somebody else's document, and it tells
		the caller the id is real. The refusal is the same sentence a line that
		does not exist gives.

		The first version of this file asserted the opposite and went red, which
		is how the conflict between AC-28 and a uniform "hand entered" answer
		was found."""
		extra = frappe.get_doc({
			"doctype": "Additional Salary", "employee": self.other,
			"company": self.company, "salary_component": self.component,
			"amount": 100, "payroll_date": "2026-08-23", "currency": "INR",
			"overwrite_salary_structure_amount": 0})
		extra.flags.ignore_permissions = True
		extra.flags.ignore_validate = True
		extra.insert(ignore_permissions=True, ignore_mandatory=True)
		extra.db_set("docstatus", 1, update_modified=False)
		frappe.db.commit()
		try:
			pay_api.get_deduction_explanation(extra.name)
		except frappe.PermissionError as exc:
			self.assertEqual(str(exc), hr_api.PAYSLIP_UNAVAILABLE)
		else:
			self.fail("somebody else's line was answered, not refused")


def _without_comments(path):
	"""The file with comments removed and STRINGS KEPT.

	For the false-remedy check, where the sentence is a string literal.
	"""
	import tokenize
	if not path.endswith(".py"):
		return io.open(path, encoding="utf-8", errors="ignore").read()
	kept = []
	with io.open(path, "rb") as handle:
		for tok in tokenize.tokenize(handle.readline):
			if tok.type == tokenize.COMMENT:
				continue
			kept.append(tok.string)
	return " ".join(kept)


def _code_only(path):
	"""The file with every comment and every string literal removed."""
	import tokenize
	kept = []
	with io.open(path, "rb") as handle:
		for tok in tokenize.tokenize(handle.readline):
			if tok.type in (tokenize.COMMENT, tokenize.STRING):
				continue
			kept.append(tok.string)
	return " ".join(kept)


class TestThePayslipLineCarriesTheLink(WhySheetFixture):
	"""AC-26."""

	def test_the_helper_only_adds_the_key_where_there_is_a_link(self):
		source = io.open(os.path.join(
			os.path.dirname(os.path.abspath(alvoraa_portal.__file__)),
			"hr_api.py"), encoding="utf-8").read()
		tree = ast.parse(source)
		found = any(
			isinstance(n, ast.FunctionDef) and n.name == "lines"
			for n in ast.walk(tree))
		self.assertTrue(found, "get_payslip's `lines` helper is gone")
		self.assertIn('line["additional_salary"] = r.additional_salary', source)
