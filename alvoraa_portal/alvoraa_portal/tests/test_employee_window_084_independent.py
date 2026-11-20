"""Slice 084, independent proof (test engineer), not the engineer's own tests.

Four things the brief says this slice fails on:
  1. the guard binds ALL THREE ways in, and the edit path (AC-9..12, 26)
  2. the blank-value trap in `set_org_setting` (AC-7)
  3. the joining-day rule, both ways (AC-15..17)
  4. blank costs zero statements and changes nothing (AC-21, 60)

Own fixtures: an empty-of-holidays list (so a window of N is exactly N calendar
days, whatever weekday the suite runs on) and NO Shift Assignment, as at DTC.
"""
import uuid
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, formatdate, getdate, nowdate

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal import hr_api

KEY = ac.EMPLOYEE_FILING_WINDOW_KEY
REQ = "Attendance Request"
LIST = "T084 independent no-holiday list"


def _say(d):
	return formatdate(d, "EEE d MMM")


class Independent084(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._commit = patch("frappe.db.commit")  # endpoints commit; keep rollback
		self._commit.start()
		self.company = frappe.db.get_value("Company", {}, "name")
		self.assertTrue(self.company, "the site has no Company")
		self._saved = frappe.db.get_default(KEY)
		if not frappe.db.exists("Holiday List", LIST):
			frappe.get_doc({
				"doctype": "Holiday List", "holiday_list_name": LIST,
				"from_date": add_days(nowdate(), -2000), "to_date": add_days(nowdate(), 400),
				"holidays": [{"holiday_date": add_days(nowdate(), 300), "description": "far"}],
			}).insert(ignore_permissions=True)
		self.emp, self.email = self.person("Emp", ("Employee",))

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_default(KEY, self._saved or "")
		self._commit.stop()

	# ── fixtures ──────────────────────────────────────────────────────
	def person(self, first, roles, joined="2000-01-01"):
		tag = uuid.uuid4().hex[:6]
		email = "t084%s@example.com" % tag
		u = frappe.get_doc({"doctype": "User", "email": email, "first_name": first + tag,
		                    "send_welcome_email": 0}).insert(ignore_permissions=True)
		for r in roles:
			u.add_roles(r)
		e = frappe.get_doc({
			"doctype": "Employee", "first_name": first + tag, "company": self.company,
			"date_of_birth": "1970-01-01", "date_of_joining": joined,
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "user_id": email,
		}).insert(ignore_permissions=True)
		frappe.get_doc({
			"doctype": "Holiday List Assignment", "holiday_list": LIST,
			"applicable_for": "Employee", "assigned_to": e.name,
			"from_date": add_days(nowdate(), -1500),
		}).insert(ignore_permissions=True).submit()
		return e.name, email

	def window(self, v):
		frappe.db.set_default(KEY, "" if v is None else str(v))

	def back(self, n):
		return add_days(nowdate(), -n)

	def joined(self, date, emp=None):
		frappe.db.set_value("Employee", emp or self.emp, "date_of_joining", date)

	def rows(self, emp=None):
		return frappe.db.count(REQ, {"employee": emp or self.emp})

	def doc(self, f, t, emp=None):
		return {"doctype": REQ, "employee": emp or self.emp, "company": self.company,
		        "from_date": f, "to_date": t, "reason": "On Duty",
		        "alvoraa_review_status": "Waiting"}

	def by(self, route, f, t=None, email=None, emp=None):
		t = t or f
		frappe.set_user(email or self.email)
		try:
			if route == "a":
				return ac.raise_correction(f, t, reason="On Duty")
			if route == "b":
				return hr_api.submit_attendance_request(f, t, "On Duty")
			if route == "c":  # the Desk
				return frappe.get_doc(self.doc(f, t, emp)).insert()
			# d: what /api/resource POST calls
			return frappe.client.insert(self.doc(f, t, emp))
		finally:
			frappe.set_user("Administrator")

	ROUTES = ("a", "b", "c", "d")

	def refused(self, route, f, t=None, **kw):
		before = self.rows(kw.get("emp"))
		with self.assertRaises(frappe.ValidationError) as c:
			self.by(route, f, t, **kw)
		self.assertEqual(self.rows(kw.get("emp")), before, "refused, so no row (route %s)" % route)
		return str(c.exception)

	# ══ 1. all three ways in, and the edit path ═══════════════════════
	def test_AC9_to_11_every_way_in_refuses_an_old_day_with_the_right_sentence(self):
		self.window(3)
		for route in self.ROUTES:
			msg = self.refused(route, self.back(8))
			# the right error: our sentence, naming the boundary and HR. A
			# different error thrown first by Frappe HR would fail here.
			self.assertIn("older than your organisation lets you raise yourself", msg, route)
			self.assertIn(_say(self.back(3)), msg, route)
			self.assertIn("tell HR which day it was and why", msg, route)

	def test_the_boundary_day_is_allowed_on_every_way_in_and_the_day_before_is_not(self):
		self.window(3)
		for route in self.ROUTES:
			e, mail = self.person("Edge", ("Employee",))
			self.by(route, self.back(3), emp=e, email=mail)
			self.assertEqual(self.rows(e), 1, route)
			self.refused(route, self.back(4), emp=e, email=mail)

	def test_AC12_editing_a_draft_back_to_an_old_day_is_refused(self):
		"""Employee holds write=1 with no if_owner: create a permitted day, then
		move from_date. Fails if the hook sits on before_insert."""
		self.window(3)
		self.by("c", self.back(1))
		name = frappe.db.get_value(REQ, {"employee": self.emp}, "name")
		for how in ("save", "client_set_value"):
			frappe.set_user(self.email)
			try:
				with self.assertRaises(frappe.ValidationError) as c:
					if how == "save":
						d = frappe.get_doc(REQ, name)
						d.from_date = self.back(20)
						d.save()
					else:
						frappe.client.set_value(REQ, name, "from_date", self.back(20))
			finally:
				frappe.set_user("Administrator")
			self.assertIn("older than your organisation", str(c.exception), how)
			self.assertEqual(str(frappe.db.get_value(REQ, name, "from_date")), self.back(1), how)

	def test_AC12_moving_to_date_back_alone_is_not_a_way_round(self):
		self.window(3)
		# from stays recent; to cannot be before from, so an old `to` needs an old
		# `from`: the only way to cross is a range, refused whole.
		self.by("c", self.back(1), self.back(1))
		name = frappe.db.get_value(REQ, {"employee": self.emp}, "name")
		frappe.set_user(self.email)
		try:
			d = frappe.get_doc(REQ, name)
			d.from_date = self.back(9)
			d.to_date = nowdate()
			with self.assertRaises(frappe.ValidationError):
				d.save()
		finally:
			frappe.set_user("Administrator")

	def test_AC26_an_hr_manager_with_an_employee_record_is_bound_on_their_own_day_only(self):
		self.window(3)
		hr, hr_mail = self.person("Hr", ("Employee", "HR Manager"))
		self.refused("c", self.back(9), emp=hr, email=hr_mail)
		self.refused("d", self.back(9), emp=hr, email=hr_mail)
		# and is free for somebody else's old day (HR route unbound)
		self.by("c", self.back(200), emp=self.emp, email=hr_mail)
		self.assertEqual(self.rows(), 1)

	def test_a_missing_from_date_is_still_an_error_not_a_pass(self):
		self.window(3)
		frappe.set_user(self.email)
		try:
			with self.assertRaises(Exception):
				frappe.get_doc(self.doc(None, nowdate())).insert()
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(self.rows(), 0)

	# ══ 2. the blank-value trap ═══════════════════════════════════════
	def test_AC7_hr_can_clear_the_number_and_the_old_day_then_goes_through(self):
		hr, hr_mail = self.person("Hr", ("Employee", "HR Manager"))
		frappe.set_user(hr_mail)
		try:
			hr_api.set_org_setting(KEY, "3")
			self.assertEqual(frappe.db.get_default(KEY), "3")
			hr_api.set_org_setting(KEY, "")          # must NOT raise PermissionError
		finally:
			frappe.set_user("Administrator")
		self.assertIn(frappe.db.get_default(KEY), ("", None))
		self.assertIsNone(ac.employee_filing_window_days())
		for route in self.ROUTES:
			e, mail = self.person("Clr", ("Employee",))
			self.by(route, self.back(180), emp=e, email=mail)
			self.assertEqual(self.rows(e), 1, route)

	def test_AC2_bad_values_are_refused_and_the_stored_number_stays(self):
		hr, hr_mail = self.person("Hr", ("Employee", "HR Manager"))
		frappe.set_user(hr_mail)
		try:
			hr_api.set_org_setting(KEY, "3")
			for bad in ("31", "-1", "3 ", "abc", "999", "1.5"):
				with self.assertRaises(frappe.PermissionError, msg=bad):
					hr_api.set_org_setting(KEY, bad)
				self.assertEqual(frappe.db.get_default(KEY), "3", bad)
			for ok in ("0", "30"):
				hr_api.set_org_setting(KEY, ok)
				self.assertEqual(frappe.db.get_default(KEY), ok)
		finally:
			frappe.set_user("Administrator")

	def test_the_zero_save_returns_the_server_date_and_other_saves_do_not(self):
		hr, hr_mail = self.person("Hr", ("Employee", "HR Manager"))
		frappe.set_user(hr_mail)
		try:
			self.assertEqual(hr_api.set_org_setting(KEY, "0"), {"ok": True, "today": nowdate()})
			self.assertEqual(hr_api.set_org_setting(KEY, "2"), {"ok": True})
			self.assertEqual(hr_api.set_org_setting(KEY, ""), {"ok": True})
		finally:
			frappe.set_user("Administrator")

	# ══ 3. the joining-day rule, both ways ════════════════════════════
	def test_AC15_to_17_joining_day_alone_is_allowed_however_old_and_nothing_else(self):
		self.window(3)
		J = self.back(40)
		self.joined(J)
		# alone: allowed on every way in (own employee each time)
		for route in self.ROUTES:
			e, mail = self.person("Jn", ("Employee",), joined=J)
			self.by(route, J, emp=e, email=mail)
			self.assertEqual(self.rows(e), 1, route)
		# joining day .. today: refused whole, with the range sentence
		for route in self.ROUTES:
			msg = self.refused(route, J, nowdate())
			self.assertIn("can be asked about on its own", msg, route)
			self.assertIn(_say(J), msg, route)
		# the day after joining (outside the window) is refused, the old sentence
		for route in self.ROUTES:
			msg = self.refused(route, add_days(J, 1))
			self.assertIn("older than your organisation", msg, route)
			self.assertIn("The one exception is your joining day, %s" % _say(J), msg, route)
		# the day BEFORE joining is no exception
		for route in self.ROUTES:
			self.refused(route, add_days(J, -1))

	def test_AC18_a_blank_joining_date_gives_no_exception_and_does_not_crash(self):
		self.window(3)
		frappe.db.set_value("Employee", self.emp, "date_of_joining", None)
		msg = self.refused("c", self.back(40))
		self.assertNotIn("joining", msg)

	def test_joining_day_inside_the_window_needs_no_exception_and_a_range_is_fine(self):
		self.window(3)
		self.joined(self.back(2))
		self.by("c", self.back(2), nowdate())     # a range from the joining day, in-window
		self.assertEqual(self.rows(), 1)

	# ══ 4. blank means zero cost, no change ═══════════════════════════
	def test_AC21_blank_hook_makes_zero_statements(self):
		self.window(None)
		d = frappe.new_doc(REQ)
		d.update(self.doc(self.back(300), self.back(300)))
		frappe.db.get_default(KEY)               # warm any cache
		seen = []
		real = frappe.db.sql
		def spy(*a, **k):
			seen.append(str(a[0])[:80])
			return real(*a, **k)
		with patch.object(frappe.db, "sql", spy):
			ac.refuse_own_day_outside_window(d)
		self.assertEqual(seen, [], "blank: the hook must not read the database at all")

	def test_AC21_unchanged_dates_cost_zero_statements_even_with_a_limit(self):
		self.window(3)
		self.by("c", self.back(1))
		name = frappe.db.get_value(REQ, {"employee": self.emp}, "name")
		d = frappe.get_doc(REQ, name)
		d.explanation = "only the words changed"
		d._doc_before_save = frappe.get_doc(REQ, name)    # as save() sets it
		seen = []
		real = frappe.db.sql
		def spy(*a, **k):
			seen.append(str(a[0])[:80])
			return real(*a, **k)
		with patch.object(frappe.db, "sql", spy):
			ac.refuse_own_day_outside_window(d)
		self.assertEqual(seen, [])

	def test_AC60_blank_changes_nothing_for_anyone_on_any_way_in(self):
		self.window(None)
		hr, hr_mail = self.person("Hr", ("Employee", "HR Manager"))
		for route in self.ROUTES:
			e, mail = self.person("Bl", ("Employee",))
			self.by(route, self.back(365), emp=e, email=mail)
			self.assertEqual(self.rows(e), 1, route)
		self.by("c", self.back(365), emp=hr, email=hr_mail)       # HR's own day too
		self.assertEqual(self.rows(hr), 1)

	def test_a_zero_is_not_blank_today_only(self):
		self.window(0)
		for route in self.ROUTES:
			self.refused(route, self.back(1))
		self.by("c", nowdate())
		self.assertEqual(self.rows(), 1)

	# ══ compliance ════════════════════════════════════════════════════
	def test_PRIV2_PRIV4_PRIV6_a_refusal_logs_nothing_and_names_no_person(self):
		self.window(3)
		name = frappe.db.get_value("Employee", self.emp, "employee_name")
		with patch("hrms.alvoraa_hr_core.access.log_refusal") as lr, \
		     patch("frappe.log_error") as le:
			msgs = [self.refused(r, self.back(30)) for r in self.ROUTES]
		lr.assert_not_called()
		le.assert_not_called()
		for m in msgs:
			self.assertNotIn(self.emp, m)
			self.assertNotIn(name, m)
			self.assertNotIn(self.email, m)
			self.assertNotIn(LIST, m)
			self.assertNotIn(self.company, m)

	def test_PRIV3_a_manager_reading_my_month_gets_no_joining_date_and_no_flags(self):
		self.window(3)
		self.joined(self.back(10))
		boss, boss_mail = self.person("Boss", ("Employee",))
		frappe.db.set_value("Employee", self.emp, "reports_to", boss)
		frappe.set_user(boss_mail)
		try:
			m = ac.month(getdate(nowdate()).year, getdate(nowdate()).month, employee=self.emp)
		finally:
			frappe.set_user("Administrator")
		blob = frappe.as_json(m)
		self.assertNotIn("joined_on", blob)
		self.assertNotIn("own_window", blob)
