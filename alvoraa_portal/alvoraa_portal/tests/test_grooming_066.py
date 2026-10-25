"""Slice 066: the grooming red mark - every SEC and PRIV item, and the stories.

One class per story, so a merge that drops a feature fails a test that names
it. The world is the spec's fixture (section 11), built once, every name
ending G066. Marks are made through the real doors - the portal endpoint and
`frappe.client` (what /api/resource calls) - as the named user. Where a test
needs marks on days the rules would no longer allow (yesterday's manager mark,
two marks on one date), they are written straight to the table and the test
says so.

Logins carry NO User Permission rows: that is DTC's shape, and the one that
would leak if the record's own read gate were missing (SEC-4 e).
"""

import json
import os
import re
from contextlib import contextmanager
from unittest.mock import patch

import frappe
import frappe.client
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, get_first_day, get_last_day, getdate, nowdate

import alvoraa_portal.grooming as grooming
import alvoraa_portal.payroll_slip as payroll_slip
import alvoraa_portal.attendance_correction as ac
from alvoraa_portal.tests.utils import ensure_fiscal_years

COMPANY, OTHER, OFF, PLAIN = "G066 Co", "G066 Other Co", "G066 Off Co", "G066 Plain Co"
HOLIDAYS = "G066 Holidays"
NORTH, SOUTH = "G066 North", "G066 South"
JUNIOR, SENIOR, ZERO = "G066 Junior", "G066 Senior", "G066 Zero"
CONTRACT = "G066 Contract"
STRUCTURE = "G066 Structure"
BASIC = "G066 Basic"
DOMAIN = "g066.test"
NOTE = "Talked about the uniform rule. Full uniform from the start of the shift."

TODAY = getdate(nowdate())
YESTERDAY = add_days(TODAY, -1)
DAY2 = add_days(TODAY, -2)
M_START, M_END = getdate(get_first_day(TODAY)), getdate(get_last_day(TODAY))
P = {}   # first name -> employee id


def user(first):
	return "%s@%s" % (first.lower(), DOMAIN)


def _insert(d, submit=False):
	doc = frappe.get_doc(d)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc


def _gender():
	return frappe.db.get_value("Gender", {}, "name") or _insert(
		{"doctype": "Gender", "gender": "Other"}).name


def _ensure_user(email, roles, first, employee=None):
	if frappe.db.exists("User", email):
		u = frappe.get_doc("User", email)
	else:
		u = _insert({"doctype": "User", "email": email, "first_name": first,
		             "send_welcome_email": 0, "enabled": 1})
	if employee:
		frappe.db.set_value("Employee", employee, "user_id", email)
	u.enabled = 1
	u.set("roles", [])
	for r in roles:
		u.append("roles", {"role": r})
	u.flags.ignore_permissions = True
	u.save(ignore_permissions=True)
	frappe.db.delete("User Permission", {"user": email})
	return email


def _employee(first, company=COMPANY, grade=JUNIOR, category=None, reports_to=None,
              branch=NORTH, status="Active", roles=None, base=12000):
	name = frappe.db.get_value("Employee", {"first_name": first, "last_name": "G066"}, "name")
	values = {"company": company, "grade": grade, "employment_type": category,
	          "reports_to": reports_to, "branch": branch, "status": "Active",
	          "holiday_list": HOLIDAYS}
	if not name:
		name = _insert(dict({"doctype": "Employee", "first_name": first, "last_name": "G066",
		                     "gender": _gender(), "date_of_birth": "1990-01-01",
		                     "date_of_joining": add_days(TODAY, -300),
		                     "create_user_permission": 0}, **values)).name
	else:
		frappe.db.set_value("Employee", name, values)
	if roles is not None:
		_ensure_user(user(first), roles, first, employee=name)
	else:
		frappe.db.set_value("Employee", name, "user_id", None)
	if base and company in (COMPANY, OFF, PLAIN) and not frappe.db.exists(
			"Salary Structure Assignment", {"employee": name, "docstatus": 1}):
		_insert({"doctype": "Salary Structure Assignment", "employee": name,
		         "salary_structure": STRUCTURE + " " + company, "company": company,
		         "currency": "INR", "from_date": add_days(TODAY, -200), "base": base}, submit=True)
	# Status last: a Left employee keeps their login, which is the case SEC-1 (l, m) tests.
	frappe.db.set_value("Employee", name, "status", status)
	P[first] = name
	return name


def _component(name, abbr, kind, by_days=0):
	if not frappe.db.exists("Salary Component", name):
		_insert({"doctype": "Salary Component", "salary_component": name,
		         "salary_component_abbr": abbr, "type": kind, "depends_on_payment_days": by_days,
		         "remove_if_zero_valued": 1, "is_tax_applicable": 0})


def _punch(emp, day, at="00:30:00"):
	_insert({"doctype": "Employee Checkin", "employee": emp, "time": "%s %s" % (day, at),
	         "log_type": "IN", "latitude": 28.65, "longitude": 77.19, "skip_auto_attendance": 1})


def setUpModule():
	ensure_fiscal_years(add_months(TODAY, -2), add_months(TODAY, 2), TODAY)
	frappe.set_user("Administrator")
	if not frappe.db.exists("Holiday List", HOLIDAYS):
		_insert({"doctype": "Holiday List", "holiday_list_name": HOLIDAYS,
		         "from_date": add_days(TODAY, -400), "to_date": add_days(TODAY, 400)})
	for b in (NORTH, SOUTH):
		if not frappe.db.exists("Branch", b):
			_insert({"doctype": "Branch", "branch": b})
	for g in (JUNIOR, SENIOR, ZERO):
		if not frappe.db.exists("Employee Grade", g):
			_insert({"doctype": "Employee Grade", "__newname": g})
	if not frappe.db.exists("Employment Type", CONTRACT):
		_insert({"doctype": "Employment Type", "employee_type_name": CONTRACT})
	_component(payroll_slip.RED_COMPONENT, "RV", "Deduction")
	_component(payroll_slip.GREEN_COMPONENT, "GV", "Earning")
	_component("Grooming Red Value", "GRV", "Deduction")
	_component(BASIC, "G066B", "Earning", by_days=1)
	for company, abbr in ((COMPANY, "G066C"), (OTHER, "G066T"), (OFF, "G066F"), (PLAIN, "G066P")):
		if not frappe.db.exists("Company", company):
			_insert({"doctype": "Company", "company_name": company, "abbr": abbr,
			         "default_currency": "INR", "country": "India"})
		frappe.db.set_value("Company", company, "default_holiday_list", HOLIDAYS)
		# This hrms reads holidays from a submitted Holiday List Assignment only.
		if not frappe.db.exists("Holiday List Assignment", {"assigned_to": company, "docstatus": 1}):
			_insert({"doctype": "Holiday List Assignment", "applicable_for": "Company",
			         "assigned_to": company, "holiday_list": HOLIDAYS,
			         "from_date": add_days(TODAY, -390)}, submit=True)
		if not frappe.db.exists("Salary Structure", STRUCTURE + " " + company):
			_insert({"doctype": "Salary Structure", "name": STRUCTURE + " " + company,
			         "company": company, "payroll_frequency": "Monthly", "currency": "INR",
			         "is_active": "Yes",
			         "earnings": [{"salary_component": BASIC, "amount_based_on_formula": 1,
			                       "formula": "base", "depends_on_payment_days": 1}],
			         "deductions": [{"salary_component": payroll_slip.RED_COMPONENT, "amount": 0}]},
			        submit=True)
	for company, enabled in ((COMPANY, 1), (OTHER, 1), (OFF, 0)):
		name = frappe.db.get_value("Alvoraa Payroll Rule Set", {"company": company})
		if not name:
			_insert({"doctype": "Alvoraa Payroll Rule Set", "company": company, "enabled": enabled,
			         "grace_minutes": 6, "free_reds_per_month": 2, "special_day_multiplier": 2,
			         "leave_threshold_days": 15, "accrual_month_days": 30,
			         "grade_field": "grade", "category_field": "employment_type",
			         "slabs": [{"percent_from": 0, "percent_to": 100, "quarters_off": 0,
			                    "raises_red": 0}],
			         "mark_rates": [{"grade": JUNIOR, "amount_per_mark": 100},
			                        {"grade": SENIOR, "amount_per_mark": 200},
			                        {"grade": ZERO, "amount_per_mark": 0}],
			         "categories": [{"category": CONTRACT, "earns_leave_credits": 0,
			                         "earns_marks": 0, "doubles_deduction": 0}]})
		else:
			frappe.db.set_value("Alvoraa Payroll Rule Set", name, "enabled", enabled)
	frappe.clear_cache(doctype="Alvoraa Payroll Rule Set")

	E = ["Employee"]
	_employee("Sunil", grade=SENIOR, roles=E, base=30000)
	_employee("Ravi", grade=SENIOR, reports_to=P["Sunil"], roles=E, base=30000)
	_employee("Rahul", grade=SENIOR, reports_to=P["Ravi"], roles=E, base=18000)
	_employee("Aman", reports_to=P["Ravi"], base=12000)
	_employee("Kiran", reports_to=P["Ravi"], base=15000)
	_employee("Geeta", category=CONTRACT, reports_to=P["Ravi"])
	_employee("Asha", reports_to=P["Ravi"])
	_employee("Mohan", grade=None, reports_to=P["Ravi"])
	_employee("Zara", grade=ZERO, reports_to=P["Ravi"])
	_employee("Pooja", reports_to=P["Ravi"])
	_employee("Deepa", reports_to=P["Ravi"], roles=E)
	_employee("Nobase", reports_to=P["Ravi"], base=0)
	_employee("Omkar", company=OFF, reports_to=P["Ravi"])
	_employee("Pia", company=PLAIN, reports_to=P["Ravi"])
	_employee("Leaver", reports_to=P["Ravi"], status="Left")
	_employee("Neha", reports_to=P["Sunil"], roles=E)
	_employee("Vikas", reports_to=P["Neha"])
	_employee("Ritika", grade=SENIOR, roles=["HR Manager", "Employee"], base=40000)
	_employee("Hari", grade=SENIOR, roles=["HR User", "Employee"], base=40000)
	_employee("Anil", branch=SOUTH, roles=["HR User", "Employee"])
	_employee("Lalit", roles=["HR User", "Employee"], status="Left")
	_employee("Lena", roles=E, status="Left")
	_employee("Tara", reports_to=P["Lena"])
	_ensure_user(user("Om"), ["System Manager"], "Om")
	_ensure_user(user("Olga"), ["HR User"], "Olga")
	if not frappe.db.exists("User Permission", {"user": user("Olga"), "allow": "Company"}):
		_insert({"doctype": "User Permission", "user": user("Olga"), "allow": "Company",
		         "for_value": OTHER, "apply_to_all_doctypes": 1})
	if not frappe.db.exists("User Permission", {"user": user("Anil"), "allow": "Branch"}):
		_insert({"doctype": "User Permission", "user": user("Anil"), "allow": "Branch",
		         "for_value": SOUTH, "apply_to_all_doctypes": 1})

	people = [P[x] for x in ("Rahul", "Aman", "Kiran", "Geeta", "Mohan", "Zara", "Pooja", "Deepa",
	                         "Nobase", "Omkar", "Pia", "Leaver", "Vikas", "Tara")]
	frappe.db.delete("Employee Checkin", {"employee": ("in", people)})
	for emp in people:
		_punch(emp, TODAY)
	for emp in (P["Rahul"], P["Aman"], P["Kiran"], P["Pooja"]):
		if YESTERDAY >= M_START:
			_punch(emp, YESTERDAY)
		if DAY2 >= M_START:
			_punch(emp, DAY2)
	frappe.db.commit()


def tearDownModule():
	frappe.set_user("Administrator")
	_wipe()
	frappe.db.commit()


def _people():
	return [v for v in P.values()]


def _wipe():
	people = _people()
	frappe.db.delete(grooming.MARK, {"employee": ("in", people)})
	frappe.db.delete("Notification Log", {"document_type": ("in", [grooming.MARK, grooming.REVIEW])})
	frappe.db.delete("Salary Slip", {"employee": ("in", people)})
	frappe.db.delete("Additional Salary", {"employee": ("in", people)})
	frappe.db.delete("Attendance", {"employee": ("in", people)})
	frappe.db.delete("Leave Application", {"employee": ("in", people)})
	frappe.db.delete("Comment", {"reference_doctype": grooming.MARK})
	frappe.db.delete("ToDo", {"reference_type": grooming.MARK})
	frappe.db.delete("DocShare", {"share_doctype": grooming.MARK})


@contextmanager
def as_user(first):
	frappe.set_user(user(first))
	try:
		yield
	finally:
		frappe.set_user("Administrator")


def _raw_mark(emp, day, owner_first="Ravi", marked_as="Manager", docstatus=1, at=None, **extra):
	"""Straight to the table: a mark the rules would refuse to make now."""
	doc = frappe.get_doc(dict({"doctype": grooming.MARK, "employee": emp, "mark_date": day,
	                           "reason": "Not in uniform", "marked_as": marked_as,
	                           "employee_name": frappe.db.get_value("Employee", emp, "employee_name")},
	                          **extra))
	doc.name = frappe.generate_hash(length=10)
	doc.owner = doc.modified_by = user(owner_first)
	doc.creation = doc.modified = at or "%s 10:%02d:00" % (day, len(frappe.get_all(grooming.MARK)) % 60)
	doc.docstatus = docstatus
	doc.db_insert()
	return doc.name


def _mark(first, subject, reason="Not in uniform", told=0, day=None, other=None):
	with as_user(first):
		return grooming.mark(P[subject], reason, told_in_person=told,
		                     date=str(day) if day else None, other_reason=other)["name"]


def _rest_mark(first, subject, day=None, **extra):
	"""What POST /api/resource/Grooming Mark then frappe.client.submit do."""
	with as_user(first):
		doc = frappe.client.insert(dict({"doctype": grooming.MARK, "employee": P[subject],
		                                 "mark_date": str(day or TODAY), "reason": "No name badge"},
		                                **extra))
		return frappe.client.submit(doc)


def _list(doctype):
	"""What a reader may list. No DocPerm read at all is a refusal in Frappe,
	and for these tests it means the same thing as an empty list."""
	try:
		return frappe.get_list(doctype, pluck="name")
	except frappe.PermissionError:
		return []


def _bells(name=None):
	f = {"document_type": grooming.MARK}
	if name:
		f["document_name"] = name
	return frappe.get_all("Notification Log", filters=f, fields=["for_user", "subject"],
	                      order_by="creation asc")


class Case(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		_wipe()

	def tearDown(self):
		frappe.set_user("Administrator")
		_wipe()
		frappe.db.commit()

	def refused(self, fn, *args, **kwargs):
		"""The call is refused, and whatever it half did is undone - but only
		back to just before it, so the marks this test made stay."""
		frappe.db.savepoint("g066_refused")
		with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
			fn(*args, **kwargs)
		frappe.db.rollback(save_point="g066_refused")


# ── US-2, US-9, SEC-1, SEC-2, SEC-3, SEC-6, SEC-7, R13 ───────────────────────

class TestManagerMarksToday(Case):
	def test_ac10_a_direct_report_today_is_marked_as_manager(self):
		name = _mark("Ravi", "Rahul")
		doc = frappe.get_doc(grooming.MARK, name)
		self.assertEqual((doc.employee, getdate(doc.mark_date), doc.reason, doc.marked_as,
		                  doc.docstatus, doc.owner),
		                 (P["Rahul"], TODAY, "Not in uniform", "Manager", 1, user("Ravi")))

	def test_ac10b_a_sent_capacity_is_ignored(self):
		doc = _rest_mark("Ravi", "Rahul", marked_as="HR")
		self.assertEqual(frappe.db.get_value(grooming.MARK, doc["name"], "marked_as"), "Manager")

	def test_ac10a_sec2_one_live_mark_a_day_and_mark_again_after_removal(self):
		first = _mark("Ravi", "Rahul")
		self.refused(_mark, "Ritika", "Rahul")
		self.assertEqual(frappe.db.count(grooming.MARK, {"employee": P["Rahul"], "docstatus": 1}), 1)
		with as_user("Ravi"):
			grooming.undo(first)
		_mark("Ravi", "Rahul")
		self.assertEqual(frappe.db.count(grooming.MARK, {"employee": P["Rahul"], "docstatus": 1}), 1)

	def test_ac13_r13_no_login_needs_the_told_tick_on_every_door(self):
		self.refused(_mark, "Ravi", "Aman", told=0)
		self.refused(_rest_mark, "Ravi", "Aman", told_in_person=0)
		name = _mark("Ravi", "Aman", told=1)
		self.assertEqual(frappe.db.get_value(grooming.MARK, name, "told_in_person"), 1)

	def test_d3_hr_also_ticks_for_a_person_with_no_login(self):
		if YESTERDAY < M_START:
			self.skipTest("first day of the month")
		self.refused(_mark, "Ritika", "Aman", day=YESTERDAY, told=0)
		self.assertTrue(_mark("Ritika", "Aman", day=YESTERDAY, told=1))

	def test_ac46_sec1_who_may_not_mark(self):
		for marker, subject in (("Sunil", "Rahul"),      # skip-level
		                        ("Neha", "Rahul"),       # another team
		                        ("Deepa", "Rahul"),      # colleague
		                        ("Om", "Rahul"),         # System Manager alone
		                        ("Olga", "Rahul"),       # HR, company excludes him
		                        ("Anil", "Rahul"),       # HR, branch excludes him
		                        ("Lalit", "Rahul"),      # HR linked to a Left employee
		                        ("Lena", "Tara")):       # manager whose own record is Left
			with self.subTest(marker=marker):
				self.refused(_mark, marker, subject)
				self.refused(_rest_mark, marker, subject)
		self.assertEqual(frappe.db.count(grooming.MARK, {"employee": ("in", _people())}), 0)

	def test_ac45_nobody_marks_themselves(self):
		self.refused(_mark, "Ravi", "Ravi")
		self.refused(_mark, "Ritika", "Ritika")
		with as_user("Ritika"):
			v = grooming.may_mark(P["Ritika"], TODAY)
		self.assertEqual(v.code, "R2")

	def test_ac39_ac41_contract_blank_grade_and_zero_rate_are_refused(self):
		for subject, code in (("Geeta", "R4"), ("Mohan", "R5"), ("Zara", "R5")):
			with self.subTest(subject=subject):
				with as_user("Ravi"):
					self.assertEqual(grooming.may_mark(P[subject], TODAY).code, code)
				self.refused(_rest_mark, "Ravi", subject)
		with as_user("Ritika"):
			v = grooming.may_mark(P["Mohan"], TODAY)
		self.assertIn("Set Mohan's grade on Mohan's employee record first.", v.message)

	def test_ac42_no_punch_and_a_left_subject_are_refused(self):
		with as_user("Ravi"):
			self.assertEqual(grooming.may_mark(P["Asha"], TODAY).code, "R8")
		with as_user("Ritika"):
			self.assertEqual(grooming.may_mark(P["Leaver"], TODAY).code, "R3")

	def test_ac43_a_full_day_leave_is_refused_and_hr_sees_the_type(self):
		frappe.get_doc({"doctype": "Attendance", "employee": P["Kiran"], "company": COMPANY,
		                "attendance_date": TODAY, "status": "On Leave", "leave_type": "Paid Leave",
		                "docstatus": 1, "name": frappe.generate_hash(length=10)}).db_insert()
		with as_user("Ritika"):
			v = grooming.may_mark(P["Kiran"], TODAY)
		self.assertEqual((v.code, v.message),
		                 ("R9", "Kiran was on leave all day (Paid Leave), so there is nothing to mark."))

	def test_sec3_the_day_rules_for_each_capacity(self):
		with as_user("Ravi"):
			self.assertEqual(grooming.may_mark(P["Rahul"], YESTERDAY).code, "R7")
			self.assertEqual(grooming.may_mark(P["Rahul"], add_days(TODAY, 1)).code, "R7")
		with as_user("Ritika"):
			self.assertEqual(grooming.may_mark(P["Rahul"], add_days(TODAY, 1)).code, "R7")
			self.assertEqual(grooming.may_mark(P["Rahul"], add_days(M_START, -1)).code, "R7")
			if YESTERDAY >= M_START:
				self.assertTrue(grooming.may_mark(P["Rahul"], YESTERDAY).ok)
		self.refused(_rest_mark, "Ritika", "Rahul", day=add_days(M_START, -1))

	def test_ac46_a_draft_from_yesterday_cannot_be_submitted_today(self):
		if YESTERDAY < M_START:
			self.skipTest("first day of the month")
		name = _raw_mark(P["Rahul"], YESTERDAY, docstatus=0)
		with as_user("Ravi"):
			self.refused(frappe.client.submit, frappe.get_doc(grooming.MARK, name).as_dict())

	def test_sec6_rule_set_off_or_absent_refuses_on_every_door(self):
		for subject in ("Omkar", "Pia"):            # disabled draft rule set; none at all
			with self.subTest(subject=subject):
				with as_user("Ravi"):
					self.assertEqual(grooming.may_mark(P[subject], TODAY).code, "R1")
				self.refused(_mark, "Ravi", subject)
				self.refused(_rest_mark, "Ravi", subject)

	def test_ac46_a_manager_whose_report_moved_today_is_refused(self):
		frappe.db.set_value("Employee", P["Rahul"], "reports_to", P["Neha"])
		try:
			with as_user("Ravi"):
				v = grooming.may_mark(P["Rahul"], TODAY)
			self.assertEqual(v.message, "Only Rahul's current manager or HR can mark Rahul.")
		finally:
			frappe.db.set_value("Employee", P["Rahul"], "reports_to", P["Ravi"])

	def test_sec11_reasons_are_the_fixed_clothing_only_list(self):
		field = frappe.get_meta(grooming.MARK).get_field("reason")
		self.assertEqual(tuple(o for o in field.options.split("\n") if o), grooming.REASONS)
		self.refused(_rest_mark, "Ravi", "Rahul", reason="Beard not trimmed")
		banned = ("hair", "beard", "turban", "hijab", "burqa", "veil", "tilak", "bindi", "sindoor",
		          "kara", "skin", "weight", "jewel", "caste", "religion", "unclean")
		for r in grooming.REASONS:
			self.assertFalse([w for w in banned if w in r.lower()], r)


# ── "Other": the marker's own short reason (Surbhi, 24 Oct 2026) ─────────────

class TestOtherReason(Case):
	def test_other_needs_a_short_clothing_reason_and_is_kept_on_the_mark(self):
		self.refused(_mark, "Ravi", "Rahul", reason="Other", other="  ")
		self.refused(_mark, "Ravi", "Rahul", reason="Other", other="x" * 101)
		for words in ("He looks sick today", "Family trouble", "Religion", "Wearing a hijab",
		              "Pregnant, no belt"):
			with self.subTest(words=words):
				self.refused(_mark, "Ravi", "Rahul", reason="Other", other=words)
		name = _mark("Ravi", "Rahul", reason="Other", other="  Torn   shirt sleeve ")
		self.assertEqual(frappe.db.get_value(grooming.MARK, name, ["reason", "other_reason"]),
		                 ("Other", "Torn shirt sleeve"))
		self.assertEqual(frappe.get_meta(grooming.MARK).get_field("other_reason").length, 100)

	def test_a_fixed_reason_carries_no_text(self):
		name = _mark("Ravi", "Rahul", other="sneaked in")
		self.assertIsNone(frappe.db.get_value(grooming.MARK, name, "other_reason"))

	def test_the_text_never_reaches_a_notice_but_readers_of_the_mark_see_it(self):
		name = _mark("Ravi", "Rahul", reason="Other", other="Torn shirt sleeve")
		self.assertTrue(_bells(name))
		for b in _bells(name):
			self.assertNotIn("Torn", b.subject)
			self.assertIn(": Other.", b.subject)
		with as_user("Rahul"):
			g = ac.month(TODAY.year, TODAY.month, P["Rahul"])["grooming"]
		self.assertEqual(g["days"][str(TODAY)]["mark"]["reason"], "Other: Torn shirt sleeve")
		with as_user("Neha"):
			self.assertRaises(frappe.PermissionError, frappe.client.get, grooming.MARK, name)

	def test_it_cannot_be_changed_after_the_mark_is_made(self):
		name = _mark("Ravi", "Rahul", reason="Other", other="Torn shirt sleeve")
		with as_user("Ritika"):
			self.refused(frappe.client.set_value, grooming.MARK, name, "other_reason", "changed")
		self.assertEqual(frappe.db.get_value(grooming.MARK, name, "other_reason"), "Torn shirt sleeve")


# ── US-12, SEC-4: one read gate ──────────────────────────────────────────────

class TestReadGate(Case):
	def setUp(self):
		super().setUp()
		self.today = _mark("Ravi", "Rahul")
		self.by_hr = (_raw_mark(P["Rahul"], YESTERDAY, owner_first="Ritika", marked_as="HR")
		              if YESTERDAY >= M_START else None)

	def _seen(self, first):
		with as_user(first):
			return set(_list(grooming.MARK)), None

	def test_ac68_each_actor_reads_exactly_their_rows(self):
		everything = {self.today} | ({self.by_hr} if self.by_hr else set())
		self.assertEqual(self._seen("Rahul")[0], everything)          # subject
		self.assertEqual(self._seen("Ritika")[0], everything)         # HR in scope
		self.assertEqual(self._seen("Ravi")[0], {self.today})         # own mark, today
		for first in ("Neha", "Sunil", "Deepa", "Om", "Olga", "Anil", "Lalit"):
			with self.subTest(first=first):
				self.assertEqual(self._seen(first)[0], set())
				with as_user(first):
					self.assertRaises(frappe.PermissionError, frappe.client.get,
					                  grooming.MARK, self.today)

	def test_ac70_hrs_mark_yesterday_is_not_readable_by_the_manager(self):
		if not self.by_hr:
			self.skipTest("first day of the month")
		with as_user("Ravi"):
			self.assertRaises(frappe.PermissionError, frappe.client.get, grooming.MARK, self.by_hr)

	def test_ac69_no_user_permission_rows_reads_nothing_but_its_own(self):
		self.assertFalse(frappe.db.exists("User Permission", {"user": user("Deepa")}))
		mine = _mark("Ravi", "Deepa")
		self.assertEqual(self._seen("Deepa")[0], {mine})

	def test_sec4_link_search_follows_the_gate(self):
		from frappe.desk.search import search_link
		with as_user("Neha"):
			self.assertEqual(search_link(grooming.MARK, ""), [])

	def test_ac70_the_docperms_are_exactly_the_matrix(self):
		perms = {p.role: {k for k in ("read", "write", "create", "submit", "cancel", "delete",
		                              "amend", "report", "export", "share", "email", "print",
		                              "import") if p.get(k)}
		         for p in frappe.get_meta(grooming.MARK).permissions}
		base = {"read", "write", "create", "submit", "cancel"}
		self.assertEqual(perms, {"Employee": base, "HR User": base | {"report"},
		                         "HR Manager": base | {"report", "export"}})

	def test_ac72_not_in_manager_scope(self):
		from alvoraa_portal import manager_scope
		self.assertNotIn(grooming.MARK, manager_scope.SCOPED_DOCTYPES)

	def test_sec4g_a_skip_level_month_has_no_grooming_key(self):
		with as_user("Sunil"):
			d = ac.month(TODAY.year, TODAY.month, P["Rahul"])
		self.assertNotIn("grooming", d)


# ── US-3, US-5, SEC-5, PRIV-3: removal ───────────────────────────────────────

class TestRemoval(Case):
	def test_ac20_the_manager_undoes_their_own_mark_today(self):
		name = _mark("Ravi", "Rahul")
		with as_user("Ravi"):
			grooming.undo(name)
		doc = frappe.get_doc(grooming.MARK, name)
		self.assertEqual((doc.docstatus, doc.removal_reason, doc.modified_by),
		                 (2, "Marked by mistake", user("Ravi")))
		self.assertEqual([b.subject for b in _bells(name)][-1],
		                 "Ravi G066, your manager, removed the grooming red Ravi marked for you "
		                 "today (%s). Nothing will come off your pay for it." % grooming._day(TODAY))

	def test_ac21_undo_for_a_person_with_no_login_tells_nobody(self):
		name = _mark("Ravi", "Aman", told=1)
		with as_user("Ravi"):
			grooming.undo(name)
		self.assertEqual(_bells(name), [])

	def test_ac22_ac22a_the_undo_closes_at_midnight_and_never_reaches_hrs_marks(self):
		if YESTERDAY < M_START:
			self.skipTest("first day of the month")
		old = _raw_mark(P["Rahul"], YESTERDAY)
		with as_user("Ravi"):
			self.refused(grooming.undo, old)
			self.refused(frappe.client.cancel, grooming.MARK, old)
		hr = _mark("Ritika", "Kiran", told=1)
		with as_user("Ravi"):
			self.refused(grooming.undo, hr)
		self.assertEqual(frappe.db.get_value(grooming.MARK, old, "docstatus"), 1)

	def test_ac28_hr_removes_with_a_reason_and_nothing_is_deleted(self):
		name = _mark("Ravi", "Rahul")
		before = frappe.db.count("Deleted Document")
		self.refused(grooming.remove, name, "Because")
		# Frappe writes no Version row in tests unless told to (document.py:
		# ignore_version = frappe.in_test). Off here, so the trail is proven.
		with as_user("Ritika"), patch.object(frappe, "in_test", False):
			grooming.remove(name, "Marked by mistake")
		doc = frappe.get_doc(grooming.MARK, name)
		self.assertEqual((doc.docstatus, doc.removal_reason), (2, "Marked by mistake"))
		self.assertTrue(frappe.db.exists("Version", {"ref_doctype": grooming.MARK, "docname": name}))
		self.assertEqual(frappe.db.count("Deleted Document"), before)
		self.assertEqual(_bells(name)[-1].subject,
		                 "Ritika G066 (HR) removed the grooming red on %s: Marked by mistake. Nothing "
		                 "will come off your pay for it." % grooming._day(TODAY))

	def test_sec5_who_may_not_remove(self):
		name = _mark("Ravi", "Rahul")
		with as_user("Rahul"):
			self.refused(frappe.client.cancel, grooming.MARK, name)       # the subject
		for first in ("Olga", "Anil", "Neha"):
			with as_user(first):
				self.refused(grooming.remove, name, "Marked by mistake")
		with as_user("Ritika"):
			self.refused(frappe.client.cancel, grooming.MARK, name)       # HR, no reason
			self.refused(frappe.client.delete, grooming.MARK, name)       # nobody deletes
		self.assertEqual(frappe.db.get_value(grooming.MARK, name, "docstatus"), 1)

	def test_ac44_a_submitted_slip_closes_the_month(self):
		name = _mark("Ravi", "Pooja", told=1)
		frappe.get_doc({"doctype": "Salary Slip", "employee": P["Pooja"], "company": COMPANY,
		                "start_date": M_START, "end_date": M_END, "posting_date": M_END,
		                "docstatus": 1, "name": frappe.generate_hash(length=10)}).db_insert()
		with as_user("Ritika"):
			self.refused(grooming.remove, name, "Marked by mistake")
			self.assertEqual(grooming.may_mark(P["Pooja"], YESTERDAY if YESTERDAY >= M_START
			                                   else TODAY).code, "R11")
		with as_user("Ravi"):
			self.refused(grooming.undo, name)


# ── US-8: ask HR, keep ───────────────────────────────────────────────────────

class TestAskAndKeep(Case):
	def test_ac35_ac37_the_subject_asks_once_and_hr_is_told_without_the_reason(self):
		name = _mark("Ravi", "Rahul")
		with as_user("Rahul"):
			grooming.ask(name)
			self.refused(grooming.ask, name)
		self.assertTrue(frappe.db.get_value(grooming.MARK, name, "asked_on"))
		asked = [b for b in _bells(name) if b.for_user in (user("Ritika"), user("Hari"))]
		self.assertEqual({b.for_user for b in asked}, {user("Ritika"), user("Hari")})
		self.assertEqual(asked[0].subject, "Rahul G066 asked HR to look at a grooming red on %s."
		                 % grooming._day(TODAY))
		self.assertNotIn("uniform", asked[0].subject.lower())
		self.assertFalse(frappe.db.exists("Attendance Request", {"employee": P["Rahul"]}))

	def test_ac38_nobody_else_writes_asked_on(self):
		name = _mark("Ravi", "Rahul")
		for first in ("Ravi", "Neha"):
			with as_user(first):
				self.refused(grooming.ask, name)
				self.refused(frappe.client.set_value, grooming.MARK, name, "asked_on", "2026-01-01")

	def test_ac36_hr_keeps_it_after_an_ask_and_the_person_is_told(self):
		name = _mark("Ravi", "Rahul")
		with as_user("Ritika"):
			self.refused(grooming.keep, name)                 # nothing asked yet
		with as_user("Rahul"):
			grooming.ask(name)
		with as_user("Ritika"):
			grooming.keep(name)
		doc = frappe.get_doc(grooming.MARK, name)
		self.assertEqual((doc.docstatus, doc.kept_by), (1, user("Ritika")))
		self.assertEqual(_bells(name)[-1].subject,
		                 "Ritika G066 (HR) checked the grooming red on %s and kept it. ₹200 still "
		                 "comes off your %s pay." % (grooming._day(TODAY), grooming._month_name(TODAY)))
		with as_user("Ritika"):
			self.refused(grooming.keep, name)                 # already answered


# ── US-7, PRIV-2, PRIV-7: notices ───────────────────────────────────────────

class TestNotices(Case):
	def test_ac33_one_bell_to_the_subject_only_with_the_fixed_words(self):
		name = _mark("Ravi", "Rahul")
		bells = _bells(name)
		self.assertEqual([b.for_user for b in bells], [user("Rahul")])
		self.assertEqual(bells[0].subject,
		                 "Ravi G066, your manager, marked a grooming red for you today (%s): Not in "
		                 "uniform. It takes ₹200 off your %s pay. If you think it is wrong, open the "
		                 "day and tap “Ask HR to look at this”."
		                 % (grooming._day(TODAY), grooming._month_name(TODAY)))

	def test_ac34_a_bell_opens_the_day_own_month_for_the_person_theirs_for_hr(self):
		name = _mark("Ravi", "Rahul")
		link = frappe.get_all("Notification Log", filters={"document_name": name}, pluck="link")
		self.assertEqual(link, ["/hrms-employee?grooming=%s" % TODAY])
		with as_user("Rahul"):
			grooming.ask(name)
		hr = frappe.get_all("Notification Log", filters={"document_name": name,
		                                                 "for_user": user("Ritika")}, pluck="link")
		self.assertEqual(hr, ["/hrms-employee?grooming=%s&who=%s" % (TODAY, P["Rahul"])])

	def test_ac33a_a_disabled_login_gets_nothing(self):
		frappe.db.set_value("User", user("Rahul"), "enabled", 0)
		try:
			name = _mark("Ravi", "Rahul", told=1)       # a disabled login is no login
			self.assertEqual(_bells(name), [])
		finally:
			frappe.db.set_value("User", user("Rahul"), "enabled", 1)

	def test_priv7_a_failed_notice_keeps_the_mark_and_logs_no_name(self):
		frappe.db.delete("Error Log", {"method": ("like", "Grooming notice%")})
		with patch("frappe.desk.doctype.notification_log.notification_log.make_notification_logs",
		           side_effect=RuntimeError("boom")):
			name = _mark("Ravi", "Rahul")
		self.assertEqual(frappe.db.get_value(grooming.MARK, name, "docstatus"), 1)
		logs = frappe.get_all("Error Log", filters={"method": ("like", "Grooming notice%")},
		                      fields=["method", "error"])
		self.assertTrue(logs)
		text = json.dumps(logs, ensure_ascii=False)
		self.assertIn(name, text)
		for word in ("Rahul", "Ravi", "uniform"):
			self.assertNotIn(word, text)

	def test_priv7_a_refusal_logs_ids_and_rule_only(self):
		lines = []
		with patch("hrms.alvoraa_hr_core.access.frappe.logger") as logger:
			logger.return_value.warning.side_effect = lines.append
			self.refused(_mark, "Neha", "Rahul")
		self.assertTrue(lines)
		for word in ("Rahul", "uniform"):
			self.assertNotIn(word, " ".join(lines))


# ── US-13, SEC-8, PRIV-1 ─────────────────────────────────────────────────────

class TestNoFreeText(Case):
	def test_ac76_no_comment_on_a_mark_and_other_comments_still_save(self):
		name = _mark("Ravi", "Rahul")
		doc = frappe.get_doc(grooming.MARK, name)
		self.refused(doc.add_comment, "Comment", "his beard")
		self.assertEqual(frappe.db.count("Comment", {"reference_doctype": grooming.MARK}), 0)
		c = frappe.get_doc("Employee", P["Rahul"]).add_comment("Comment", "G066 an ordinary comment")
		self.assertTrue(frappe.db.exists("Comment", c.name))
		frappe.db.delete("Comment", {"name": c.name})

	def test_ac77_no_share_and_no_assign_to_someone_who_cannot_read(self):
		from frappe.desk.form import assign_to
		import frappe.share
		name = _mark("Ravi", "Rahul")
		with as_user("Ritika"):
			self.refused(frappe.share.add, grooming.MARK, name, user("Neha"), read=1)
			self.refused(assign_to.add, {"assign_to": [user("Neha")], "doctype": grooming.MARK,
			                             "name": name})
		self.assertEqual(frappe.db.count("DocShare", {"share_doctype": grooming.MARK,
		                                              "share_name": name}), 0)
		self.assertEqual(frappe.db.count("ToDo", {"reference_type": grooming.MARK,
		                                          "reference_name": name}), 0)

	def test_ac79_least_fields_a_random_name_and_a_locked_reason(self):
		meta = frappe.get_meta(grooming.MARK)
		self.assertEqual({f.fieldname for f in meta.fields if f.fieldtype != "Column Break"},
		                 {"employee", "employee_name", "mark_date", "reason", "other_reason", "marked_as",
		                  "told_in_person", "asked_on", "kept_by", "kept_on", "removal_reason",
		                  "raised_on", "raised_by", "raised_reason"})
		self.assertEqual((meta.autoname, meta.allow_import, meta.allow_rename, meta.track_views,
		                  meta.track_changes, meta.is_submittable), ("hash", 0, 0, 0, 1, 1))
		self.assertFalse([f for f in meta.fields if f.in_global_search])
		name = _mark("Ravi", "Rahul")
		for part in (P["Rahul"], "rahul", str(TODAY), TODAY.strftime("%Y%m%d")):
			self.assertNotIn(part.lower(), name.lower())
		with as_user("Ritika"):
			self.refused(frappe.client.set_value, grooming.MARK, name, "reason", "No name badge")
		self.assertEqual(frappe.db.get_value(grooming.MARK, name, "reason"), "Not in uniform")


# ── US-1: the Today card ─────────────────────────────────────────────────────

class TestTodayCard(Case):
	def test_ac2_direct_reports_who_punched_today_sorted_with_my_count(self):
		_mark("Ravi", "Rahul")
		_mark("Ritika", "Kiran", told=1)
		with as_user("Ravi"):
			d = grooming.today()
		names = [r["employee_name"] for r in d["rows"]]
		self.assertEqual(names, sorted(names))
		self.assertNotIn("Asha G066", names)
		self.assertIn("Asha G066", d["not_in"])
		self.assertNotIn("Leaver G066", names)
		self.assertEqual(d["count"], 1)                        # mine only
		row = {r["employee_name"]: r for r in d["rows"]}
		self.assertTrue(row["Rahul G066"]["mark"]["mine"])
		self.assertEqual((row["Kiran G066"]["mark"]["by"], row["Kiran G066"]["mark"]["marked_as"]),
		                 ("Ritika G066", "HR"))
		self.assertEqual(row["Geeta G066"]["why_not"], "Contract staff are not given grooming reds.")
		self.assertNotIn("₹", json.dumps(d, ensure_ascii=False))               # never money to a manager

	def test_sec1n_the_screens_flag_equals_may_mark_for_every_row(self):
		with as_user("Ravi"):
			d = grooming.today()
			for r in d["rows"]:
				if "mark" in r:
					continue
				with self.subTest(r["employee_name"]):
					self.assertEqual(r["can_mark"], bool(grooming.may_mark(r["employee"], TODAY).ok))

	def test_ac6_ac2a_no_card_with_nobody_or_with_the_rule_set_off(self):
		with as_user("Rahul"):
			self.assertEqual(grooming.today(), {"show": False})
		with as_user("Lena"):
			self.assertEqual(grooming.today(), {"show": False})

	def test_the_card_is_flat_in_queries(self):
		def count():
			n = [0]
			real = frappe.db.sql

			def wrap(*a, **k):
				n[0] += 1
				return real(*a, **k)
			with as_user("Ravi"), patch.object(frappe.db, "sql", wrap):
				grooming.today()
			return n[0]
		count()
		small = count()
		extra = [_employee("Extra%d" % i, reports_to=P["Ravi"]) for i in range(5)]
		for e in extra:
			_punch(e, TODAY)
		try:
			count()                       # new records clear caches; warm them again
			self.assertEqual(count(), small)
		finally:
			frappe.db.delete("Employee Checkin", {"employee": ("in", extra)})
			frappe.db.set_value("Employee", {"name": ("in", extra)}, "reports_to", None)


# ── US-6, US-4: the month ────────────────────────────────────────────────────

class TestMonth(Case):
	def _month(self, first, subject):
		with as_user(first):
			return ac.month(TODAY.year, TODAY.month, P[subject])

	def test_ac30_the_manager_sees_his_mark_and_no_money(self):
		_mark("Ravi", "Rahul")
		if YESTERDAY >= M_START:
			_raw_mark(P["Rahul"], YESTERDAY, owner_first="Ritika", marked_as="HR")
		g = self._month("Ravi", "Rahul")["grooming"]
		self.assertEqual(list(g["days"]), [str(TODAY)])
		self.assertTrue(g["days"][str(TODAY)]["mark"]["can_undo"])
		self.assertNotIn("₹", json.dumps(g, ensure_ascii=False))
		self.assertNotIn("rate_words", g)

	def test_ac31_ac32_the_employee_sees_who_why_and_what_it_costs(self):
		_mark("Ravi", "Rahul")
		g = self._month("Rahul", "Rahul")["grooming"]
		m = g["days"][str(TODAY)]["mark"]
		self.assertEqual((m["by"], m["reason"], m["can_ask"]), ("Ravi G066", "Not in uniform", True))
		self.assertEqual((g["rate_words"], g["grade"]), ("₹200", SENIOR))
		self.assertEqual((g["tile"]["n"], g["tile"]["amount"]), (1, "₹200"))

	def test_ac40_contract_staff_get_no_key(self):
		_ensure_user(user("Geeta"), ["Employee"], "Geeta", employee=P["Geeta"])
		try:
			self.assertNotIn("grooming", self._month("Geeta", "Geeta"))
		finally:
			frappe.db.set_value("Employee", P["Geeta"], "user_id", None)

	def test_ac23_hr_gets_a_button_where_may_mark_says_yes_and_its_sentence_where_not(self):
		g = self._month("Ritika", "Asha")["grooming"]
		self.assertEqual(g["days"][str(TODAY)]["why_code"], "R8")
		g = self._month("Ritika", "Rahul")["grooming"]
		self.assertTrue(g["days"][str(TODAY)]["can_mark"])
		self.assertEqual(g["viewer"], "hr")


# ── US-16, PRIV-6, the Inbox ─────────────────────────────────────────────────

class TestHRViews(Case):
	def test_ac66_ac67_the_saved_views_and_who_may_export(self):
		for name in ("Marks per marker per month", "Asked to look at not yet answered",
		             "People with grooming reds this month"):
			self.assertEqual(frappe.db.get_value("Report", name, ["ref_doctype", "report_type"]),
			                 (grooming.MARK, "Report Builder"))
		with as_user("Ritika"):
			self.assertTrue(frappe.has_permission(grooming.MARK, "export"))
		with as_user("Hari"):
			self.assertFalse(frappe.has_permission(grooming.MARK, "export"))

	def test_priv6_a_branch_hr_sees_only_its_branch(self):
		_mark("Ravi", "Rahul")
		with as_user("Anil"):
			self.assertEqual(_list(grooming.MARK), [])

# ── SEC-12, PRIV-5: the purpose fence ────────────────────────────────────────

ALLOWED = re.compile(r"(^|/)(grooming\.py|payroll_slip\.py|hooks\.py|tests/.*|"
                     r"alvoraa_portal/doctype/grooming_(mark|review)/.*|"
                     r"alvoraa_portal/report/(grooming_review_pending|marks_per_marker_per_month|"
                     r"asked_to_look_at_not_yet_answered|people_with_grooming_reds_this_month)/.*)$")


class TestPurposeFence(FrappeTestCase):
	def test_ac73_the_record_is_named_only_where_it_belongs(self):
		import alvoraa_goals
		import hrms
		roots = [os.path.dirname(os.path.dirname(grooming.__file__)),
		         os.path.dirname(os.path.dirname(alvoraa_goals.__file__)),
		         os.path.dirname(os.path.dirname(hrms.__file__))]
		found = []
		for root in roots:
			for d, _dirs, files in os.walk(root):
				if "node_modules" in d or "/." in d:
					continue
				for f in files:
					if not f.endswith((".py", ".js")):
						continue
					path = os.path.join(d, f)
					try:
						text = open(path, encoding="utf-8", errors="ignore").read()
					except OSError:
						continue
					if "Grooming Mark" in text or "Grooming Review" in text:
						found.append(path.replace(os.sep, "/"))
		strays = [p for p in found if not ALLOWED.search(p.split("/alvoraa_portal/", 1)[-1]
		                                                if "/alvoraa_portal/" in p else p)]
		self.assertEqual(strays, [])
		self.assertTrue(found)


# ── Security verification, 25 Oct 2026 (06b): B1, B2, B3, M2 ────────────────

class TestSecurityVerificationFixes(Case):
	def test_b1_an_empty_save_neither_reads_nor_stamps_a_mark(self):
		if YESTERDAY < M_START:
			self.skipTest("first day of the month")
		hr_mark = _raw_mark(P["Rahul"], YESTERDAY, owner_first="Ritika", marked_as="HR",
		                    reason="Other", other_reason="PROBE-TEXT")
		before = frappe.db.get_value(grooming.MARK, hr_mark, "modified_by")
		with as_user("Ravi"):                           # manager; may not read yesterday's HR mark
			self.refused(frappe.client.set_value, grooming.MARK, hr_mark, {})
			self.refused(frappe.client.save, frappe.get_doc(grooming.MARK, hr_mark).as_dict())
		self.assertEqual(frappe.db.get_value(grooming.MARK, hr_mark, "modified_by"), before)
		own = _mark("Ravi", "Rahul")
		with as_user("Rahul"):                          # even a reader: an empty save is refused
			self.refused(frappe.client.set_value, grooming.MARK, own, {})

	def test_b2_no_file_and_no_tag_on_a_mark(self):
		from frappe.desk.doctype.tag.tag import add_tag
		name = _mark("Ravi", "Rahul")
		for first in ("Ravi", "Ritika"):
			frappe.db.savepoint("g066_tag")             # add_tag makes the site-wide Tag first
			with self.subTest(first=first), as_user(first):
				with self.assertRaises(frappe.PermissionError) as caught:
					add_tag("probe beard", grooming.MARK, name)
				self.assertIn("tagged", str(caught.exception))
			frappe.db.rollback(save_point="g066_tag")
		frappe.db.savepoint("g066_file")
		with as_user("Ritika"):
			with self.assertRaises(frappe.PermissionError) as caught:
				frappe.get_doc({"doctype": "File", "file_name": "g066-probe.txt", "content": "x",
				                "is_private": 1, "attached_to_doctype": grooming.MARK,
				                "attached_to_name": name}).insert()
			self.assertIn("files attached", str(caught.exception))
		frappe.db.rollback(save_point="g066_file")
		self.assertEqual(frappe.db.count("File", {"attached_to_doctype": grooming.MARK}), 0)
		self.assertEqual(frappe.db.count("Tag Link", {"document_type": grooming.MARK}), 0)

	def test_m4_one_list_refuses_sensitive_information_and_allows_grooming_words(self):
		"""Architect review M-4: refuse religion, caste, health, family, gender and
		the like; allow clothing and grooming words. One list for the fixed
		reasons and the typed ones."""
		for r in grooming.REASONS:                      # the same list pins the fixed reasons
			self.assertFalse(grooming.about_the_person(r), r)
		for words in ("Turban untidy", "Hijab not in company colour", "Sikh kara showing",
		              "Religious thread on wrist", "Caste mark", "Sick looking",
		              "Medical boot on one foot", "Pregnant, no belt", "Wife called",
		              "Gender", "Disabled, wrong shoes", "Fasting so tired"):
			with self.subTest(refused=words):
				self.refused(_mark, "Ravi", "Rahul", reason="Other", other=words)
		for words in ("Beard not trimmed", "Hair too long", "Dirty shirt",
		              "Jewellery not allowed", "Head covering wrong colour", "Torn shirt sleeve",
		              "Paint stains on trousers", "Face mask missing", "Shirt not tucked in"):
			with self.subTest(allowed=words):
				self.assertFalse(grooming.about_the_person(words), words)
		self.assertTrue(_mark("Ravi", "Rahul", reason="Other", other="Beard not trimmed"))

	def test_m2_the_raise_sheet_asks_for_a_reason_not_why_it_is_removed(self):
		"""Architect review m-2. Read from the screen code: only the remove sheet
		asks "why"; the mark and raise sheets say "Choose a reason first."."""
		js = open(os.path.join(os.path.dirname(grooming.__file__), "public", "js", "ess",
		                       "portal.js"), encoding="utf-8").read()
		self.assertIn('s.error = s.kind === "remove" ? "Choose why you are removing it." : '
		              '"Choose a reason first.";', js)

	def test_m2_a_marker_who_has_left_reads_nothing(self):
		name = _mark("Ravi", "Rahul")
		frappe.db.set_value("Employee", P["Ravi"], "status", "Left")
		try:
			with as_user("Ravi"):
				self.assertEqual(_list(grooming.MARK), [])
				self.assertRaises(frappe.PermissionError, frappe.client.get, grooming.MARK, name)
		finally:
			frappe.db.set_value("Employee", P["Ravi"], "status", "Active")


# ── The live portal's bell (Surbhi, 24-25 Oct 2026) ──────────────────────────

class TestLivePortalBell(Case):
	def test_the_person_sees_fixed_words_never_the_other_text_and_a_link_to_the_day(self):
		name = _mark("Ravi", "Rahul", reason="Other", other="Torn shirt sleeve")
		with as_user("Rahul"):
			d = grooming.my_notices()
			self.assertEqual(d["unread"], 1)
			self.assertEqual(d["items"][0]["link"], "/hrms-employee?grooming=%s" % TODAY)
			self.assertIn(": Other.", d["items"][0]["text"])
			self.assertNotIn("Torn", json.dumps(d, ensure_ascii=False))
			grooming.my_notices_seen()
			self.assertEqual(grooming.my_notices()["unread"], 0)
		with as_user("Ravi"):                           # the marker gets no notice of his own
			self.assertEqual(grooming.my_notices()["items"], [])
		with as_user("Rahul"):
			grooming.ask(name)
		for first, n in (("Ritika", 1), ("Hari", 1), ("Olga", 0), ("Neha", 0)):
			with self.subTest(first=first), as_user(first):
				items = grooming.my_notices()["items"]
				self.assertEqual(len(items), n)
				self.assertNotIn("Torn", json.dumps(items, ensure_ascii=False))

	def test_a_notice_follows_the_mark_s_own_read_rule(self):
		name = _mark("Ravi", "Rahul")
		with as_user("Rahul"):
			grooming.ask(name)
		with as_user("Hari"):
			self.assertEqual(len(grooming.my_notices()["items"]), 1)
		frappe.db.set_value("Employee", P["Hari"], "status", "Left")   # HR who left reads nothing
		try:
			with as_user("Hari"):
				self.assertEqual(grooming.my_notices()["items"], [])
		finally:
			frappe.db.set_value("Employee", P["Hari"], "status", "Active")

	def test_every_other_text_is_audit_logged_by_id_never_by_its_words(self):
		lines = []
		with patch("alvoraa_portal.grooming.frappe.logger") as logger:
			logger.return_value.info.side_effect = lines.append
			fixed = _mark("Ravi", "Rahul")
			self.assertEqual(lines, [])                 # a fixed reason writes no line
		with as_user("Ravi"):
			grooming.undo(fixed)
		with patch("alvoraa_portal.grooming.frappe.logger") as logger:
			logger.return_value.info.side_effect = lines.append
			other = _mark("Ravi", "Rahul", reason="Other", other="Torn shirt sleeve")
		self.assertEqual(len(lines), 1)
		entry = json.loads(lines[0])
		self.assertEqual((entry["event"], entry["name"], entry["user"], entry["length"]),
		                 ("grooming_other_text", other, user("Ravi"), len("Torn shirt sleeve")))
		self.assertNotIn("Torn", lines[0])
		# the words themselves stay on the mark, unchangeable
		with as_user("Ritika"):
			self.refused(frappe.client.set_value, grooming.MARK, other, "other_reason", "x")

