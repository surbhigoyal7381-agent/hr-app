"""ALV-328: the break per day, and the reason for a day, on the two screens.

The break shown must be the break the pay rules counted (spec §5, AC-13), it
reaches only people who may read the punches behind it (SEC-3), and it never
appears on a group view (PRIV-1).

EVERY PERSON AND PUNCH HERE IS MADE UP. No real attendance is in this file, and
none may be added.
"""

import json
from datetime import datetime
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import attendance_analytics as aa
from alvoraa_portal import attendance_correction as ac
from alvoraa_portal.field_app_access import WHOLE_LINE_SETTING
from alvoraa_portal.payroll_rules import minutes_on_break, punch_minutes
from alvoraa_portal.payroll_rules_apply import breaks_by_day

COMPANY = "ALV328 Break Co"
SHIFT = "ALV328 10-19"
YEAR, MONTH = 2025, 3
ALLOWANCE = 40

# (day of the month, punches). Shift 10:00-19:00, shift hours only, 40 allowed.
DAYS = {
	3: "09:58 13:00 13:40 19:05",             # AC-1: 40, nothing over
	4: "09:58 13:00 13:40 16:10 16:25 19:05",  # AC-7: 55, 15 over
	5: "09:58 13:00 19:05",                    # AC-11: a punch is missing
	6: "09:58 09:59 13:00 13:40 19:05",        # AC-12: a repeat scan folds
	7: "09:00 09:20 09:45 13:00 13:30 19:02",  # AC-14: 30 inside the shift
	10: "08:00 08:20 08:50 19:02",             # AC-15: the only gap is before the shift
	11: "09:58 19:05",                         # AC-3: two punches, no break
	13: "09:58 13:00 13:40 19:05",             # AC-17a: plus a 00:30 punch on the 14th
}

SLABS = [
	{"percent_from": 0, "percent_to": 50, "quarters_off": 2, "raises_red": 0},
	{"percent_from": 50, "percent_to": 90, "quarters_off": 1, "raises_red": 0},
	{"percent_from": 90, "percent_to": 98.9, "quarters_off": 0, "raises_red": 1},
	{"percent_from": 98.9, "percent_to": 100, "quarters_off": 0, "raises_red": 0},
]


def date(n):
	return "%04d-%02d-%02d" % (YEAR, MONTH, n)


def _gender():
	return frappe.db.get_value("Gender", {}, "name") or frappe.get_doc(
		{"doctype": "Gender", "gender": "Other"}).insert(ignore_permissions=True).name


def setUpModule():
	frappe.set_user("Administrator")
	if not frappe.db.exists("Company", COMPANY):
		frappe.get_doc({"doctype": "Company", "company_name": COMPANY, "abbr": "A328",
		                "default_currency": "INR", "country": "India"}).insert(ignore_permissions=True)
	if not frappe.db.exists("Shift Type", SHIFT):
		frappe.get_doc({"doctype": "Shift Type", "name": SHIFT, "start_time": "10:00:00",
		                "end_time": "19:00:00"}).insert(ignore_permissions=True)
	existing = frappe.db.get_value("Alvoraa Payroll Rule Set", {"company": COMPANY}, "name")
	if existing:
		frappe.delete_doc("Alvoraa Payroll Rule Set", existing, force=True, ignore_permissions=True)
	rs = frappe.get_doc({
		"doctype": "Alvoraa Payroll Rule Set", "company": COMPANY, "enabled": 1,
		"grace_minutes": 6, "free_reds_per_month": 2, "special_day_multiplier": 2,
		"leave_threshold_days": 15, "accrual_month_days": 30,
		"count_shift_hours_only": 1, "break_allowance_minutes": ALLOWANCE,
		"slabs": SLABS, "mark_rates": [{"grade": "Junior", "amount_per_mark": 100}],
	})
	rs.flags.ignore_permissions = True
	rs.insert()
	frappe.db.set_single_value("HR Settings", WHOLE_LINE_SETTING, 0)
	frappe.db.commit()


class BreakHelpers(FrappeTestCase):
	"""The pure rules both the engine and the screens use (AC-16, AC-17)."""

	def test_alv328_seconds_are_dropped_before_counting(self):
		times = [datetime(2025, 3, 3, 10, 0), datetime(2025, 3, 3, 13, 0, 59),
		         datetime(2025, 3, 3, 13, 40, 0), datetime(2025, 3, 3, 19, 0)]
		distinct = punch_minutes(times)
		self.assertEqual(distinct, [600, 780, 820, 1140])
		self.assertEqual(minutes_on_break([(780, 820)], 600, 1140), 40)

	def test_alv328_a_repeat_scan_is_one_punch(self):
		times = [datetime(2025, 3, 3, 9, 58), datetime(2025, 3, 3, 9, 59)]
		self.assertEqual(len(punch_minutes(times)), 1)


class BreakCase(FrappeTestCase):
	_n = 0

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		BreakCase._n += 1
		tag = "%s%d" % (cls.__name__[:6], BreakCase._n)
		cls.arjun, cls.arjun_mail = cls.person("Arj" + tag)
		cls.kavita, cls.kavita_mail = cls.person("Kav" + tag, reports_to=cls.arjun)
		cls.rohan, cls.rohan_mail = cls.person("Roh" + tag, reports_to=cls.kavita)
		cls.priya, cls.priya_mail = cls.person("Pri" + tag)
		cls.meena, cls.meena_mail = cls.person("Mee" + tag, roles=("HR Manager",))
		names = {n: [cls.punch(cls.rohan, "%s %s:00" % (date(n), t)) for t in p.split()]
		         for n, p in DAYS.items()}
		# AC-17a: a punch after midnight, linked to the 13th's Attendance below,
		# as Frappe's own attendance job links a night shift's punches.
		names[13].append(cls.punch(cls.rohan, "%s 00:30:00" % date(14)))
		cls.att = {n: cls.day(cls.rohan, date(n)) for n in DAYS}
		for c in names[13]:
			frappe.db.set_value("Employee Checkin", c, "attendance", cls.att[13],
			                    update_modified=False)

	@classmethod
	def person(cls, first, reports_to=None, roles=()):
		email = "%s.alv328@example.com" % first.lower()
		if not frappe.db.exists("User", email):
			u = frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
			                    "send_welcome_email": 0}).insert(ignore_permissions=True)
			u.add_roles("Employee", *roles)
		e = frappe.get_doc({
			"doctype": "Employee", "first_name": first, "company": COMPANY,
			"date_of_birth": "1980-01-01", "date_of_joining": "2000-01-01",
			"gender": _gender(),
			"status": "Active", "default_shift": SHIFT, "user_id": email,
			"reports_to": reports_to}).insert(ignore_permissions=True)
		return e.name, email

	@classmethod
	def punch(cls, employee, when):
		return frappe.get_doc({
			"doctype": "Employee Checkin", "employee": employee, "time": when,
			"latitude": 28.6, "longitude": 77.2, "skip_auto_attendance": 1,
		}).insert(ignore_permissions=True).name

	@classmethod
	def day(cls, employee, on, status="Present"):
		a = frappe.get_doc({"doctype": "Attendance", "employee": employee, "attendance_date": on,
		                    "status": status, "shift": SHIFT, "company": COMPANY})
		a.insert(ignore_permissions=True)
		a.submit()
		return a.name

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("HR Settings", WHOLE_LINE_SETTING, 0)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("HR Settings", WHOLE_LINE_SETTING, 0)

	def month_as(self, email, employee=None):
		frappe.set_user(email)
		try:
			return ac.month(YEAR, MONTH, employee)
		finally:
			frappe.set_user("Administrator")

	def person_as(self, email, employee):
		frappe.set_user(email)
		try:
			return aa.person(employee, date(1), date(31))
		finally:
			frappe.set_user("Administrator")

	@staticmethod
	def by_date(out):
		return {d["date"]: d for d in out["days"]}

	@staticmethod
	def breaks(out):
		return {d["date"]: {k: v for k, v in d.items() if k.startswith("break_")}
		        for d in out["days"] if any(k.startswith("break_") for k in d)}


class BreakOnTheAttendancePage(BreakCase):
	def test_alv328_the_days_the_spec_names(self):
		out = self.month_as(self.rohan_mail)
		days = self.by_date(out)
		self.assertEqual(out["break_allowance_minutes"], ALLOWANCE)
		self.assertEqual({k: days[date(3)].get(k) for k in ("break_state", "break_minutes")},
		                 {"break_state": "measured", "break_minutes": 40})
		self.assertNotIn("break_over", days[date(3)])
		self.assertEqual((days[date(4)]["break_minutes"], days[date(4)]["break_over"]), (55, 15))
		self.assertEqual(days[date(5)]["break_state"], "not_measured")
		self.assertNotIn("break_minutes", days[date(5)])
		self.assertEqual(days[date(6)]["break_minutes"], 40)
		self.assertEqual(days[date(7)]["break_minutes"], 30)
		self.assertEqual(days[date(10)]["break_minutes"], 0)
		for n in (11, 12):
			self.assertFalse([k for k in days[date(n)] if k.startswith("break_")], date(n))

	def test_alv328_a_punch_after_midnight_counts_on_its_own_date(self):
		"""AC-17a: four punches on the 13th by calendar date, though five are linked."""
		days = self.by_date(self.month_as(self.rohan_mail))
		self.assertEqual(len(days[date(13)]["punches"]), 5)
		self.assertEqual(days[date(13)]["break_minutes"], 40)

	def test_alv328_the_break_shown_is_the_break_the_pay_rules_counted(self):
		"""AC-13, the brief's kill criterion: same number as the stored reason."""
		days = self.by_date(self.month_as(self.rohan_mail))
		checked = 0
		for n in DAYS:
			why = days[date(n)].get("rules_why") or ""
			if "Breaks: " in why:
				stored = int(why.split("Breaks: ")[1].split(" minutes")[0])
				self.assertEqual(days[date(n)]["break_minutes"], stored, why)
				checked += 1
			elif "A punch is missing from the middle of the day" in why:
				self.assertEqual(days[date(n)]["break_state"], "not_measured", why)
				checked += 1
			elif days[date(n)].get("break_state") == "measured":
				self.assertEqual(days[date(n)]["break_minutes"], 0, why)
				checked += 1
		self.assertGreaterEqual(checked, 6, "the engine did not judge the fixture days")

	def test_alv328_the_reason_and_when_it_was_worked_out(self):
		days = self.by_date(self.month_as(self.rohan_mail))
		self.assertIn("Breaks: 55 minutes", days[date(4)]["rules_why"])
		self.assertRegex(days[date(4)]["evaluated_on"], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$")
		self.assertNotIn("rules_why", days[date(1)])
		self.assertNotIn("evaluated_on", days[date(1)])

	def test_alv328_no_key_is_sent_empty(self):
		"""AC-48."""
		for d in self.month_as(self.rohan_mail)["days"]:
			for k in ("break_state", "break_minutes", "break_over", "rules_why", "evaluated_on"):
				if k in d:
					self.assertNotIn(d[k], (None, ""), k)

	def test_alv328_no_break_without_a_break_rule(self):
		"""AC-5: an allowance of 0 shows no break at all."""
		name = frappe.db.get_value("Alvoraa Payroll Rule Set", {"company": COMPANY}, "name")
		frappe.db.set_value("Alvoraa Payroll Rule Set", name, "break_allowance_minutes", 0)
		frappe.clear_document_cache("Alvoraa Payroll Rule Set", name)
		try:
			out = self.month_as(self.rohan_mail)
			self.assertEqual(self.breaks(out), {})
			self.assertNotIn("break_allowance_minutes", out)
		finally:
			frappe.db.set_value("Alvoraa Payroll Rule Set", name, "break_allowance_minutes", ALLOWANCE)
			frappe.clear_document_cache("Alvoraa Payroll Rule Set", name)

	def test_alv328_leave_and_night_shifts_get_no_break(self):
		"""AC-4 and the engine's held night shift, through the shared function."""
		times = {date(3): [datetime(2025, 3, 3, h, m) for h, m in ((10, 0), (13, 0), (13, 40), (19, 0))]}
		self.assertEqual(breaks_by_day(self.rohan, COMPANY, {date(3): ("On Leave", SHIFT)}, times), (0, {}))
		self.assertEqual(breaks_by_day(self.rohan, COMPANY, {date(3): ("Present", "No such shift")}, times), (0, {}))
		self.assertEqual(breaks_by_day(self.rohan, COMPANY, {date(3): ("Present", SHIFT)}, times)[1],
		                 {date(3): {"break_state": "measured", "break_minutes": 40}})


class WhoSeesTheBreak(BreakCase):
	def test_alv328_the_direct_manager_sees_what_the_person_sees(self):
		"""AC-24."""
		own = self.month_as(self.rohan_mail)
		theirs = self.month_as(self.kavita_mail, self.rohan)
		self.assertEqual(self.breaks(theirs), self.breaks(own))
		self.assertEqual(theirs["break_allowance_minutes"], own["break_allowance_minutes"])
		self.assertEqual(self.by_date(theirs)[date(4)]["rules_why"], self.by_date(own)[date(4)]["rules_why"])

	def test_alv328_a_skip_level_manager_gets_no_break_by_default(self):
		"""AC-25, AC-26 (SEC-3): no break worked out from punches they cannot read."""
		out = self.month_as(self.arjun_mail, self.rohan)
		self.assertEqual(self.breaks(out), {})
		self.assertNotIn("break_allowance_minutes", out)
		self.assertIn("rules_why", self.by_date(out)[date(4)], "the reason still shows (Q-B)")
		self.assertFalse([d for d in self.person_as(self.arjun_mail, self.rohan)["days"]
		                  if any(k.startswith("break_") for k in d)])

	def test_alv328_with_the_switch_on_the_skip_level_manager_sees_it(self):
		"""AC-30, AC-34."""
		frappe.db.set_single_value("HR Settings", WHOLE_LINE_SETTING, 1)
		self.assertEqual(self.breaks(self.month_as(self.arjun_mail, self.rohan)),
		                 self.breaks(self.month_as(self.rohan_mail)))
		frappe.db.set_single_value("HR Settings", WHOLE_LINE_SETTING, 0)
		self.assertEqual(self.breaks(self.month_as(self.arjun_mail, self.rohan)), {})

	def test_alv328_a_colleague_is_refused_and_gets_nothing(self):
		"""AC-41."""
		for call in (lambda: self.month_as(self.priya_mail, self.rohan),
		             lambda: self.person_as(self.priya_mail, self.rohan)):
			with self.assertRaises(frappe.PermissionError):
				call()

	def test_alv328_frappe_doors_keep_a_colleague_out_of_the_reason(self):
		"""AC-42 (SEC-4): the list (REST and report view use it), get_value and get."""
		import frappe.client

		def doors():
			frappe.set_user(self.priya_mail)
			try:
				listed = frappe.get_list("Attendance", filters={"employee": self.rohan},
				                         fields=["name", "alvoraa_rules_why"], limit_page_length=0)
				try:
					one = frappe.client.get_value("Attendance", "alvoraa_rules_why",
					                              {"name": self.att[4]})
				except frappe.PermissionError:
					one = None
				try:
					frappe.client.get("Attendance", self.att[4])
					opened = True
				except frappe.PermissionError:
					opened = False
				return listed, one, opened
			finally:
				frappe.set_user("Administrator")

		listed, one, opened = doors()
		self.assertEqual(listed, [])
		self.assertFalse(one, "get_value must return nothing of a colleague's")
		self.assertFalse(opened)
		# Negative control: without Priya's own-record row the list opens, so the
		# check above can fail. The row is put back afterwards.
		from alvoraa_portal.own_record_permission import sync_user

		frappe.db.delete("User Permission", {"user": self.priya_mail, "allow": "Employee"})
		frappe.clear_cache(user=self.priya_mail)
		try:
			self.assertTrue(doors()[0], "the negative control did not open the list")
		finally:
			sync_user(self.priya_mail)
			frappe.clear_cache(user=self.priya_mail)

	def test_alv328_hr_sees_the_same_break_on_insights_and_no_reason(self):
		"""AC-37, AC-38."""
		days = {d["date"]: d for d in self.person_as(self.meena_mail, self.rohan)["days"]}
		own = self.breaks(self.month_as(self.rohan_mail))
		got = {k: {x: v for x, v in d.items() if x.startswith("break_")}
		       for k, d in days.items() if any(x.startswith("break_") for x in d)}
		self.assertEqual(got, own)
		for d in days.values():
			self.assertNotIn("rules_why", d)
			self.assertNotIn("evaluated_on", d)

	def test_alv328_no_break_on_any_group_view(self):
		"""AC-40 (PRIV-1)."""
		frappe.set_user(self.kavita_mail)
		try:
			blobs = [aa.summary(view, depth, date(1), date(31))
			         for view in ("mine", "team") for depth in ("direct", "deep")]
			blobs.append(ac.team_days(date(1), date(31)))
		finally:
			frappe.set_user("Administrator")
		frappe.set_user(self.meena_mail)
		try:
			blobs.append(aa.summary("organisation", "direct", date(1), date(31)))
			blobs.append(aa.filter_options())
		finally:
			frappe.set_user("Administrator")
		for blob in blobs:
			self.assertNotIn('"break', json.dumps(blob, default=str))


class QueryCounts(BreakCase):
	"""AC-46, AC-47 (OPS-1, OPS-3): the count does not grow with punches or days."""

	def counted(self, call):
		with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
			call()
		checkin = [str(c.args[0]) for c in sql.call_args_list
		           if "tabEmployee Checkin" in str(c.args[0] if c.args else "")]
		self.checkin_sql = checkin
		return sql.call_count, len(checkin)

	def test_alv328_month_costs_the_same_for_few_or_many_punches(self):
		few, _ = self.person("Few%d" % BreakCase._n, reports_to=None)
		for n in DAYS:
			for t in ("09:58", "19:05"):
				self.punch(few, "%s %s:00" % (date(n), t))
			self.day(few, date(n))
		frappe.set_user(self.meena_mail)
		try:
			ac.month(YEAR, MONTH, self.rohan)    # warm the caches both calls share
			many = self.counted(lambda: ac.month(YEAR, MONTH, self.rohan))
			many_sql = self.checkin_sql
			less = self.counted(lambda: ac.month(YEAR, MONTH, few))
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(many, less)
		# The page's own punch list is the only read this slice relies on; the
		# break adds none. The grooming line, when on, reads punches once more.
		own = [q for q in many_sql if "`attendance`" in q]
		self.assertEqual(len(own), 1, "the break adds no Employee Checkin read")

	def test_alv328_person_costs_the_same_for_one_month_or_twelve(self):
		frappe.set_user(self.meena_mail)
		try:
			aa.person(self.rohan, date(1), date(31))
			short = self.counted(lambda: aa.person(self.rohan, date(1), date(31)))
			long_ = self.counted(lambda: aa.person(self.rohan, "2024-04-01", date(31)))
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(short, long_)
		self.assertEqual(short[1], 1, "exactly one Employee Checkin read")
