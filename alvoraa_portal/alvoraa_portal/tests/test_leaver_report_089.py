"""Slice 089: a manager reports a leaver; managers see a little more of their team.

"See" only. The "change" half (US-10, US-11) is deferred and there is no timeline
comment, so nothing here tests either.

Every refusal test has an ALLOWED case beside it, so a pass cannot mean "nobody
is allowed". The reporter acts in their OWN session (`frappe.set_user`), never as
Administrator, because `owner` is what the guard reads.

Synthetic people only, tagged S089. Test data is shared state on one site, so the
confirming role is a role of this file's own: a leftover HR Manager from another
suite cannot become a recipient.
"""

import json
import logging
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

import hrms.alvoraa_org_structure.people_fields as people_fields
import hrms.alvoraa_org_structure.settings as org_settings
from alvoraa_portal import hr_api, leaver_report, my_profile
from alvoraa_portal.tests.leave_fixtures import ensure_user
from alvoraa_portal.tests.test_portal_security_010 import _employee, _user

FIELD = leaver_report.FIELD
ROLE = "S089 Confirmer"
SEES = leaver_report.SEES_KEY
PERSONAL_KEYS = ("cell_number", "personal_email", "company_email", "gender", "current_address",
                 "person_to_be_contacted", "relation", "emergency_phone_number")


def _company(name, abbr):
	if not frappe.db.exists("Company", name):
		frappe.get_doc({"doctype": "Company", "company_name": name, "abbr": abbr,
		                "default_currency": "INR", "country": "India"}).insert()
	return name


def _login(local, roles):
	"""A user with exactly these roles; the Employee role needs an Employee, so
	callers make the Employee straight after."""
	return _user(f"089.{local}", roles)


class _Base(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Role", ROLE):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE}).insert(ignore_permissions=True)
		cls.company_a = _company("S089 Company A", "S89A")
		cls.company_b = _company("S089 Company B", "S89B")

		cls.mgr_user = _login("mgr", ("Employee",))
		cls.rpt_user = _login("rpt", ("Employee",))
		cls.skip_user = _login("skip", ("Employee",))
		cls.col_user = _login("col", ("Employee",))
		cls.hr_a_user = _login("hra", (ROLE, "HR User", "Employee"))
		cls.hr_b_user = _login("hrb", (ROLE, "HR User", "Employee"))
		cls.hrm_user = _login("hrm", ("HR Manager", "Employee"))
		cls.skip = _employee("S089Skip", company=cls.company_a, user=cls.skip_user)
		cls.mgr = _employee("S089Mgr", company=cls.company_a, reports_to=cls.skip, user=cls.mgr_user)
		cls.rpt = _employee("S089Rpt", company=cls.company_a, reports_to=cls.mgr, user=cls.rpt_user)
		cls.col = _employee("S089Col", company=cls.company_a, user=cls.col_user)
		cls.hr_a = _employee("S089HrA", company=cls.company_a, user=cls.hr_a_user)
		cls.hr_b = _employee("S089HrB", company=cls.company_b, user=cls.hr_b_user)
		cls.hrm = _employee("S089Hrm", company=cls.company_a, user=cls.hrm_user)
		for emp in (cls.skip, cls.mgr, cls.rpt, cls.col, cls.hr_a, cls.hr_b, cls.hrm):
			frappe.db.set_value("Employee", emp, "date_of_joining", "2025-01-01", update_modified=False)
		frappe.db.set_value("Employee", cls.rpt, {
			"cell_number": "9876543210", "current_address": "14 Test Lane",
			"personal_email": "s089.rpt.private@example.com",
			"person_to_be_contacted": "Kamla", "relation": "Mother",
			"emergency_phone_number": "9810012345"}, update_modified=False)
		frappe.db.commit()

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.set_default(leaver_report.org_settings.CONFIRM_ROLE_KEY, ROLE)
		frappe.db.delete("DefaultValue", {"defkey": SEES})
		self._clean()

	def tearDown(self):
		frappe.set_user("Administrator")
		self._clean()
		frappe.db.delete("DefaultValue", {"defkey": SEES})
		frappe.db.delete("DefaultValue", {"defkey": org_settings.CONFIRM_ROLE_KEY})
		for extra in ("hra2",):
			u = f"s010.089.{extra}@example.com"
			if frappe.db.exists("User", u):
				frappe.get_doc("User", u).remove_roles(ROLE)
		frappe.db.set_value("Employee", self.rpt, {"status": "Active", "relieving_date": None,
		                                           "reports_to": self.mgr}, update_modified=False)
		frappe.db.commit()
		super().tearDown()

	def _clean(self):
		frappe.db.delete("ToDo", {FIELD: ("is", "set")})
		users = [self.mgr_user, self.hr_a_user, self.hr_b_user, self.skip_user]
		frappe.db.delete("Notification Log", {"for_user": ("in", users), "document_type": "Employee"})
		frappe.db.commit()

	def _as(self, user):
		frappe.set_user(user)

	def _send(self, employee=None, day=None):
		return leaver_report.send_leaver_report(employee=employee or self.rpt,
		                                        last_working_day=day or nowdate())

	def _todos(self, employee=None):
		return frappe.get_all("ToDo", filters={FIELD: employee or self.rpt},
		                      fields=["name", "allocated_to", "assigned_by", "status", "date",
		                              "description", "reference_type", "reference_name"])

	def _as_admin_todos(self):
		user = frappe.session.user
		frappe.set_user("Administrator")
		try:
			return self._todos()
		finally:
			frappe.set_user(user)

	def _counts(self):
		return {t: frappe.db.count(t) for t in ("ToDo", "Comment", "DocShare", "Email Queue")}


class _Log:
	"""Reads the security log from its handler, not from a mock of `refuse`."""

	def __enter__(self):
		from hrms.alvoraa_hr_core.access import security_logger
		self.lines = []
		outer = self

		class H(logging.Handler):
			def emit(self, record):
				outer.lines.append(record.getMessage())

		self.h = H(level=logging.DEBUG)
		self.logger = security_logger()
		self.logger.addHandler(self.h)
		return self

	def __exit__(self, *a):
		self.logger.removeHandler(self.h)


class TestReport(_Base):
	def test_a_direct_manager_reports_and_only_todos_are_written(self):
		before = self._counts()
		emails = frappe.db.count("Email Queue")
		self._as(self.mgr_user)
		out = self._send(day=add_days(nowdate(), 3))
		frappe.set_user("Administrator")
		rows = self._todos()
		self.assertEqual([r.allocated_to for r in rows], [self.hr_a_user],
		                 "only the confirmer of the person's own company is told")
		r = rows[0]
		self.assertEqual((r.status, r.assigned_by, str(r.date)), ("Open", self.mgr_user, add_days(nowdate(), 3)))
		self.assertIn("Confirm that", r.description)
		self.assertFalse(r.reference_type or r.reference_name,
		                 "a reference would make Frappe write a Comment and `_assign` on the Employee")
		after = self._counts()
		self.assertEqual(after["ToDo"], before["ToDo"] + 1)
		for t in ("Comment", "DocShare", "Email Queue"):
			self.assertEqual(after[t], before[t], f"{t} must not change (AC-12, AC-26, decision 2)")
		self.assertFalse(frappe.db.get_value("Employee", self.rpt, "_assign"))
		self.assertEqual(frappe.db.count("Email Queue"), emails)
		emp = frappe.db.get_value("Employee", self.rpt, ["status", "relieving_date"], as_dict=True)
		self.assertEqual((emp.status, emp.relieving_date), ("Active", None))
		self.assertTrue(out["ok"])

	def test_the_name_is_escaped_and_nothing_personal_is_in_the_notice(self):
		frappe.db.set_value("Employee", self.rpt, "employee_name", "<b>x</b> Rpt", update_modified=False)
		try:
			self._as(self.mgr_user)
			self._send()
			frappe.set_user("Administrator")
			text = self._todos()[0].description
			self.assertNotIn("<b>x</b>", text)
			self.assertIn("&lt;b&gt;x&lt;/b&gt;", text)
			for secret in ("9876543210", "14 Test Lane", "Kamla", "9810012345", "private@"):
				self.assertNotIn(secret, text)
		finally:
			frappe.db.set_value("Employee", self.rpt, "employee_name", "S089Rpt S089", update_modified=False)

	def test_refusals_write_nothing_and_are_logged(self):
		left = _employee("S089Left", company=self.company_a, reports_to=self.mgr)
		frappe.db.set_value("Employee", left, {"status": "Left", "relieving_date": nowdate()})
		nobody = _employee("S089NoMgr", company=self.company_a)
		cases = (
			("skip-level", self.skip_user, self.rpt),
			("colleague", self.col_user, self.rpt),
			("self", self.mgr_user, self.mgr),
			("person with no manager", self.mgr_user, nobody),
			("left person", self.mgr_user, left),
			("no such person", self.mgr_user, "HR-EMP-NOPE-089"),
		)
		for label, user, person in cases:
			before = self._counts()
			self._as(user)
			with _Log() as log, self.assertRaises(frappe.PermissionError, msg=label):
				self._send(employee=person)
			frappe.set_user("Administrator")
			self.assertEqual(self._counts(), before, label)
			self.assertTrue(any("089-SEC-6" in ln for ln in log.lines), f"{label}: no security line")
			for ln in log.lines:
				for secret in ("9876543210", "14 Test Lane", "Kamla"):
					self.assertNotIn(secret, ln)
		# the allowed case beside them
		self._as(self.mgr_user)
		self.assertTrue(self._send()["ok"])

	def test_the_date_window(self):
		self._as(self.mgr_user)
		for bad, words in ((add_days(nowdate(), -32), "31 days ago"), (add_days(nowdate(), 61), "60 days ahead")):
			with self.assertRaises(frappe.PermissionError) as c:
				self._send(day=bad)
			self.assertIn(words, str(c.exception))
		self.assertEqual(len(self._as_admin_todos()), 0)
		self.assertTrue(self._send(day=add_days(nowdate(), -31))["ok"], "exactly 31 days ago is accepted")
		frappe.set_user("Administrator")
		self._clean()
		self._as(self.mgr_user)
		self.assertTrue(self._send(day=add_days(nowdate(), 60))["ok"], "exactly 60 days ahead is accepted")
		frappe.set_user("Administrator")
		self._clean()
		frappe.db.set_value("Employee", self.rpt, "date_of_joining", add_days(nowdate(), -5), update_modified=False)
		try:
			self._as(self.mgr_user)
			with self.assertRaises(frappe.PermissionError):
				self._send(day=add_days(nowdate(), -10))
		finally:
			frappe.db.set_value("Employee", self.rpt, "date_of_joining", "2025-01-01", update_modified=False)

	def test_a_second_report_is_refused_and_writes_nothing(self):
		self._as(self.mgr_user)
		self._send()
		before = self._counts()
		with self.assertRaises(frappe.PermissionError) as c:
			self._send()
		self.assertIn("already reported", str(c.exception))
		self.assertEqual(self._counts(), before)
		# a different manager, same person: the sentence names nobody
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.rpt, "reports_to", self.col, update_modified=False)
		self._as(self.col_user)
		with self.assertRaises(frappe.PermissionError) as c:
			self._send()
		self.assertIn("already has an open report", str(c.exception))
		self.assertNotIn(self.mgr_user, str(c.exception))

	def test_nobody_to_confirm_writes_nothing(self):
		frappe.db.set_default(org_settings.CONFIRM_ROLE_KEY, "S089 Empty Role")
		self._as(self.mgr_user)
		before = self._counts()
		with self.assertRaises(frappe.PermissionError) as c:
			self._send()
		self.assertIn("Nobody can confirm this yet", str(c.exception))
		self.assertEqual(self._counts(), before)

	def test_the_reporter_is_never_a_recipient(self):
		# the manager also holds the confirming role: still not told about their own report
		frappe.get_doc("User", self.mgr_user).add_roles(ROLE, "HR User")
		self._as(self.mgr_user)
		self._send()
		self.assertEqual([r.allocated_to for r in self._as_admin_todos()], [self.hr_a_user])

	def test_a_role_with_too_many_holders_is_refused_at_send_time(self):
		self._as(self.mgr_user)
		with patch.object(org_settings, "CONFIRMER_CAP", 0):
			with self.assertRaises(frappe.PermissionError):
				self._send()
		self.assertEqual(self._as_admin_todos(), [])

	def test_a_failed_insert_leaves_no_todo_for_anyone(self):
		# two recipients, the second insert fails
		hr_a2 = _login("hra2", (ROLE, "HR User", "Employee"))
		_employee("S089HrA2", company=self.company_a, user=hr_a2)
		real = frappe.get_doc
		calls = {"n": 0}

		def flaky(*a, **kw):
			doc = real(*a, **kw)
			if a and isinstance(a[0], dict) and a[0].get("doctype") == "ToDo":
				calls["n"] += 1
				if calls["n"] == 2:
					raise frappe.ValidationError("boom")
			return doc

		self._as(self.mgr_user)
		with patch.object(frappe, "get_doc", flaky):
			with self.assertRaises(Exception):
				self._send()
		self.assertEqual(calls["n"], 2, "the test must really have reached the second insert")
		self.assertEqual(self._as_admin_todos(), [])

	def test_the_open_state_is_one_query_whatever_the_number_of_reports(self):
		self._as(self.mgr_user)
		self._send()
		seen = []
		real = frappe.get_all

		def spy(doctype, *a, **kw):
			seen.append(doctype)
			return real(doctype, *a, **kw)

		with patch.object(frappe, "get_all", spy):
			few = leaver_report.open_reports_by([self.rpt])
			n_few = seen.count("ToDo")
			seen.clear()
			many = leaver_report.open_reports_by([self.rpt] + [f"X-{i}" for i in range(50)])
		self.assertEqual((n_few, seen.count("ToDo")), (1, 1))
		self.assertEqual(list(few), [self.rpt])
		self.assertEqual(list(many), [self.rpt])


class TestTwoCompanies(_Base):
	def test_only_the_confirmer_of_the_persons_company_is_told(self):
		self._as(self.mgr_user)
		self._send()
		got = {r.allocated_to for r in self._as_admin_todos()}
		self.assertEqual(got, {self.hr_a_user})
		self.assertNotIn(self.hr_b_user, got)
		# and the other company's confirmer sees nothing through the list API
		self._as(self.hr_b_user)
		self.assertEqual(frappe.get_list("ToDo", filters={FIELD: self.rpt}), [])
		self._as(self.hr_a_user)
		self.assertEqual(len(frappe.get_list("ToDo", filters={FIELD: self.rpt})), 1)


class TestGuard(_Base):
	"""SEC-9 and the forged insert, as the reporter's own session."""

	def setUp(self):
		super().setUp()
		self._as(self.mgr_user)
		self._send()
		self.todo = self._as_admin_todos()[0].name

	def test_the_reporter_cannot_edit_close_or_delete_it(self):
		self._as(self.mgr_user)
		for label, call in (
			("set_value status", lambda: frappe.client.set_value("ToDo", self.todo, "status", "Closed")),
			("set_value date", lambda: frappe.client.set_value("ToDo", self.todo, "date", add_days(nowdate(), 20))),
			("set_value marker", lambda: frappe.client.set_value("ToDo", self.todo, FIELD, "")),
			("save", lambda: _save(self.todo, status="Cancelled")),
			("delete", lambda: frappe.client.delete("ToDo", self.todo)),
		):
			with self.assertRaises(frappe.PermissionError, msg=label):
				call()
		frappe.set_user("Administrator")
		row = frappe.db.get_value("ToDo", self.todo, ["status", "date"], as_dict=True)
		self.assertEqual((row.status, str(row.date)), ("Open", nowdate()))

	def test_nobody_can_plant_a_marked_todo_by_hand(self):
		self._as(self.col_user)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": "ToDo", "description": "fake", "allocated_to": self.hr_a_user,
			                "assigned_by": self.col_user, FIELD: self.mgr}).insert()
		# an ordinary ToDo is untouched by the guard
		frappe.get_doc({"doctype": "ToDo", "description": "an ordinary task",
		                "allocated_to": self.col_user}).insert()

	def test_a_confirmer_closes_it_and_the_reporter_is_told_once(self):
		self._as(self.hr_a_user)
		_save(self.todo, status="Closed")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("ToDo", self.todo, "status"), "Closed")
		bells = frappe.get_all("Notification Log", filters={"for_user": self.mgr_user, "document_type": "Employee"},
		                       fields=["type", "subject"])
		self.assertEqual(len(bells), 1)
		self.assertEqual(bells[0].type, "Alert", "Alert is the type Frappe never emails")
		self.assertIn("closed without being confirmed", bells[0].subject)
		self.assertEqual(frappe.db.get_value("Employee", self.rpt, "status"), "Active")

	def test_the_hr_person_who_reported_can_still_save_left(self):
		"""The guard binds the reporter's ToDo edits, not the Employee save that
		closes the report. An HR person who is also the line manager reports, a
		different confirmer is told, and the reporter's own Left save closes it."""
		frappe.set_user("Administrator")
		hr2_user = _login("hra2", (ROLE, "HR User", "Employee"))
		_employee("S089HrA2", company=self.company_a, user=hr2_user)
		frappe.db.set_value("Employee", self.rpt, "reports_to", self.hr_a, update_modified=False)
		frappe.set_user("Administrator")
		self._clean()
		self._as(self.hr_a_user)
		self._send()
		frappe.set_user("Administrator")
		self.assertEqual({r.allocated_to for r in self._todos()}, {hr2_user})
		self._as(self.hr_a_user)
		emp = frappe.get_doc("Employee", self.rpt)
		emp.status, emp.relieving_date = "Left", nowdate()
		emp.save()
		frappe.set_user("Administrator")
		self.assertEqual({r.status for r in self._todos()}, {"Closed"})


def _save(name, **values):
	doc = frappe.get_doc("ToDo", name)
	doc.update(values)
	doc.save()


class TestEmployeeSave(_Base):
	def _report(self):
		self._as(self.mgr_user)
		self._send()
		frappe.set_user("Administrator")

	def test_left_closes_the_reports_and_tells_the_reporter(self):
		self._report()
		self._as(self.hr_a_user)
		emp = frappe.get_doc("Employee", self.rpt)
		emp.status, emp.relieving_date = "Left", add_days(nowdate(), 2)
		emp.save()
		frappe.set_user("Administrator")
		self.assertEqual({r.status for r in self._todos()}, {"Closed"})
		bells = frappe.get_all("Notification Log", filters={"for_user": self.mgr_user, "document_type": "Employee"},
		                       fields=["subject", "type"])
		self.assertEqual(len(bells), 1)
		self.assertIn("Confirmed:", bells[0].subject)
		self.assertEqual(bells[0].type, "Alert")
		self.assertEqual(str(frappe.db.get_value("Employee", self.rpt, "relieving_date")), add_days(nowdate(), 2))

	def test_an_ordinary_save_costs_no_todo_query(self):
		self._report()
		seen = []
		real = frappe.get_all

		def spy(doctype, *a, **kw):
			seen.append(doctype)
			return real(doctype, *a, **kw)

		emp = frappe.get_doc("Employee", self.rpt)
		emp.designation = emp.designation
		emp.cell_number = "9876543210"
		with patch.object(frappe, "get_all", spy):
			emp.save()
		self.assertNotIn("ToDo", seen)
		self.assertEqual({r.status for r in self._todos()}, {"Open"}, "an Active save leaves the report open")

	def test_left_is_refused_while_active_people_report_to_them_and_the_report_stays_open(self):
		self._report()
		sub = _employee("S089Sub", company=self.company_a, reports_to=self.rpt)
		emp = frappe.get_doc("Employee", self.rpt)
		emp.status, emp.relieving_date = "Left", nowdate()
		with self.assertRaises(frappe.ValidationError):
			emp.save()
		frappe.db.rollback()
		self.assertEqual({r.status for r in self._todos()}, {"Open"})
		frappe.db.set_value("Employee", sub, "status", "Inactive")

	def test_deleting_the_employee_removes_the_report(self):
		person = _employee("S089Gone", company=self.company_a, reports_to=self.mgr)
		self._as(self.mgr_user)
		self._send(employee=person)
		frappe.set_user("Administrator")
		self.assertEqual(len(self._todos(person)), 1)
		frappe.delete_doc("Employee", person, force=True)
		self.assertEqual(self._todos(person), [])


class TestWhatAManagerSees(_Base):
	def _both(self, who, person=None):
		self._as(who)
		person = person or self.rpt
		return (hr_api.get_employee_scorecard(person), hr_api.get_employee_detail_for_manager(person))

	def _tick(self, fields):
		frappe.set_user("Administrator")
		org_settings.set_cover_setting(SEES, ",".join(fields))

	def test_nothing_personal_is_sent_by_default(self):
		for call in self._both(self.mgr_user):
			blob = json.dumps(call, default=str)
			for key in PERSONAL_KEYS:
				self.assertNotIn(f'"{key}"', blob, key)
			for secret in ("9876543210", "14 Test Lane", "private@"):
				self.assertNotIn(secret, blob)

	def test_a_ticked_field_appears_and_an_untick_hides_it_without_a_restart(self):
		self._tick(["cell_number"])
		for call in self._both(self.mgr_user):
			self.assertEqual(set(call["personal"]), {"cell_number"})
			self.assertNotIn('"personal_email"', json.dumps(call, default=str))
		self._tick([])
		for call in self._both(self.mgr_user):
			self.assertEqual(call["personal"], {})

	def test_the_emergency_contact_and_address_come_with_their_ticks(self):
		self._tick(["current_address", "person_to_be_contacted", "relation", "emergency_phone_number"])
		sc, _ = self._both(self.mgr_user)
		self.assertEqual(set(sc["personal"]), {"current_address", "person_to_be_contacted", "relation",
		                                        "emergency_phone_number"})
		self.assertEqual(sc["personal"]["relation"], "Mother")

	def test_who_gets_the_fields(self):
		self._tick(list(("cell_number", "current_address")))
		# allowed: the direct manager
		sc, _ = self._both(self.mgr_user)
		self.assertTrue(sc["personal"])
		# not allowed: skip-level and colleague are refused outright, and logged
		for who in (self.skip_user, self.col_user):
			self._as(who)
			with _Log() as log, self.assertRaises(frappe.PermissionError):
				hr_api.get_employee_scorecard(self.rpt)
			with self.assertRaises(frappe.PermissionError):
				hr_api.get_employee_detail_for_manager(self.rpt)
			self.assertTrue(any("089-SEC-5" in ln for ln in log.lines), "the old bare throw left no trace")
		# HR of the same company opens the page but receives none of the ticked fields (Q3)
		sc, det = self._both(self.hr_a_user)
		self.assertEqual((sc["personal"], det["personal"]), ({}, {}))
		# HR of another company is refused as before
		self._as(self.hr_b_user)
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_employee_scorecard(self.rpt)

	def test_a_left_person_gives_no_personal_fields(self):
		self._tick(["cell_number"])
		frappe.db.set_value("Employee", self.rpt, {"status": "Left", "relieving_date": nowdate()},
		                    update_modified=False)
		sc, _ = self._both(self.mgr_user)
		self.assertEqual(sc["personal"], {})
		self.assertFalse(sc["can_report"])

	def test_can_report_is_true_only_for_an_active_direct_report_with_no_open_report(self):
		sc, _ = self._both(self.mgr_user)
		self.assertTrue(sc["can_report"])
		self._as(self.mgr_user)
		self._send()
		sc, _ = self._both(self.mgr_user)
		self.assertFalse(sc["can_report"])
		self.assertTrue(sc["open_report"])
		# the colleague's call is refused, so they cannot even ask
		self._as(self.col_user)
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_employee_scorecard(self.rpt)

	def test_the_team_list_says_who_this_manager_reported(self):
		self._as(self.mgr_user)
		self._send()
		self.assertIn(self.rpt, hr_api.get_manager_dashboard()["reported"])
		self._as(self.skip_user)
		self.assertNotIn(self.rpt, hr_api.get_manager_dashboard()["reported"])

	def test_the_person_sees_one_line_and_a_colleague_sees_none(self):
		self._as(self.mgr_user)
		self._send(day=add_days(nowdate(), 4))
		self._as(self.rpt_user)
		mine = my_profile.get_my_profile()["leaver_report"]
		self.assertEqual(str(mine["last_day"]), add_days(nowdate(), 4))
		self.assertTrue(mine["by"])
		self.assertNotIn(self.hr_a_user, json.dumps(mine, default=str), "never the confirmers")
		self._as(self.col_user)
		self.assertIsNone(my_profile.get_my_profile()["leaver_report"])


class TestSettings(_Base):
	def test_fresh_defaults(self):
		frappe.db.delete("DefaultValue", {"defkey": org_settings.CONFIRM_ROLE_KEY})
		self.assertEqual(org_settings.confirm_role(), "HR Manager")
		self.assertEqual(people_fields.allowed(SEES, frappe.db.get_default(SEES)), ())
		self.assertEqual(set(people_fields.MANAGER_SEES_FIELDS),
		                 {"cell_number", "current_address", "person_to_be_contacted", "relation",
		                  "emergency_phone_number"})

	def test_an_hr_manager_is_refused_and_a_system_manager_leaves_a_version_row(self):
		self._as(self.hrm_user)
		with _Log() as log, self.assertRaises(frappe.PermissionError):
			org_settings.set_cover_setting(SEES, "cell_number")
		self.assertTrue(any("089-SEC-3" in ln for ln in log.lines))
		self.assertFalse(frappe.db.get_default(SEES))
		frappe.set_user("Administrator")
		before = frappe.db.count("Version", {"ref_doctype": "DefaultValue", "docname": SEES})
		org_settings.set_cover_setting(SEES, "cell_number")
		self.assertEqual(frappe.db.count("Version", {"ref_doctype": "DefaultValue", "docname": SEES}), before + 1)

	def test_the_list_is_closed(self):
		for bad in ("personal_email", "permanent_address", "cell_number,bank_ac_no", "date_of_birth"):
			with self.assertRaises(frappe.PermissionError, msg=bad):
				org_settings.set_cover_setting(SEES, bad)
		self.assertFalse(frappe.db.get_default(SEES))
		# a value written straight into DefaultValue produces nothing at the reader
		frappe.db.set_default(SEES, "personal_email,cell_number")
		self.assertEqual(set(people_fields.allowed(SEES, frappe.db.get_default(SEES))), {"cell_number"})

	def test_the_confirming_role_is_checked(self):
		for role in ("Guest", "All", "Administrator", "Desk User", "Employee", "Employee Self Service",
		             "S089 Role Nobody Holds", ""):
			with self.assertRaises(frappe.PermissionError, msg=role):
				org_settings.set_cover_setting(org_settings.CONFIRM_ROLE_KEY, role)
		# a role held only by a disabled user
		frappe.get_doc({"doctype": "Role", "role_name": "S089 Disabled Only"}).insert(ignore_permissions=True) \
			if not frappe.db.exists("Role", "S089 Disabled Only") else None
		dis = _login("dis", ("S089 Disabled Only", "HR User"))
		frappe.db.set_value("User", dis, "enabled", 0)
		with self.assertRaises(frappe.PermissionError):
			org_settings.set_cover_setting(org_settings.CONFIRM_ROLE_KEY, "S089 Disabled Only")
		# a role whose holders cannot save Left
		self.assertTrue(frappe.db.exists("User", self.col_user))
		frappe.get_doc({"doctype": "Role", "role_name": "S089 No Writer"}).insert(ignore_permissions=True) \
			if not frappe.db.exists("Role", "S089 No Writer") else None
		_login("nowriter", ("S089 No Writer", "Employee"))
		with self.assertRaises(frappe.PermissionError):
			org_settings.set_cover_setting(org_settings.CONFIRM_ROLE_KEY, "S089 No Writer")
		# the allowed case, with its Version row
		org_settings.set_cover_setting(org_settings.CONFIRM_ROLE_KEY, ROLE)
		self.assertEqual(org_settings.confirm_role(), ROLE)
		with patch.object(org_settings, "CONFIRMER_CAP", 1):
			with self.assertRaises(frappe.PermissionError):
				org_settings.set_cover_setting(org_settings.CONFIRM_ROLE_KEY, ROLE)

	def test_the_card_payload_is_system_manager_only_and_carries_the_real_count(self):
		from alvoraa_portal import people_settings
		self._as(self.mgr_user)
		with self.assertRaises(frappe.PermissionError):
			people_settings.get_people_settings()
		frappe.set_user("Administrator")
		d = people_settings.get_people_settings()
		self.assertEqual(d["manager_sees_fields"], [])
		self.assertEqual(d["leaver_confirm_role"], ROLE)
		self.assertGreaterEqual(d["manager_sees_people"], 1)
		self.assertEqual(d["leaver_confirm_holders"], len(org_settings.eligible_confirmers(ROLE)))
		self.assertGreaterEqual(d["leaver_confirm_holders"], 2)
		self.assertNotIn("Guest", d["leaver_confirm_roles"])


class TestPins(_Base):
	def test_the_three_todo_validate_handlers_all_still_run(self):
		"""Slice 089 pin. A bad merge that drops the guard, or either of the two
		side-record rules it sits beside, fails here."""
		hooks = frappe.get_hooks("doc_events")["ToDo"]
		validate = hooks["validate"]
		for h in ("alvoraa_portal.grooming.refuse_side_record",
		          "hrms.alvoraa_org_structure.plans.refuse_side_record",
		          "alvoraa_portal.leaver_report.guard_todo"):
			self.assertIn(h, validate)
		self.assertIn("alvoraa_portal.leaver_report.guard_todo", hooks["on_trash"])
		self.assertIn("alvoraa_portal.leaver_report.on_todo_update", hooks["on_update"])
		emp = frappe.get_hooks("doc_events")["Employee"]
		self.assertIn("alvoraa_portal.leaver_report.on_employee_update", emp["on_update"])
		self.assertIn("alvoraa_portal.leaver_report.on_employee_trash", emp["on_trash"])
		for event in ("after_migrate", "after_install"):
			self.assertIn("alvoraa_portal.leaver_report.after_migrate", frappe.get_hooks(event))

	def test_manager_editable_is_still_empty_and_the_writer_lists_agree(self):
		from alvoraa_portal import employee_field_rights as efr
		self.assertEqual(efr.MANAGER_EDITABLE, ())
		self.assertEqual(org_settings.LEAVER_WRITERS, efr.LEVEL_2_WRITERS)

	def test_the_custom_field_exists_once_and_has_no_index(self):
		self.assertEqual(frappe.db.count("Custom Field", {"dt": "ToDo", "fieldname": FIELD}), 1)
		self.assertTrue(leaver_report.after_migrate())
		self.assertEqual(frappe.db.count("Custom Field", {"dt": "ToDo", "fieldname": FIELD}), 1)
		self.assertFalse(frappe.db.get_value("Custom Field", f"ToDo-{FIELD}", "search_index"))

	def test_the_endpoint_is_post_only_and_rate_limited(self):
		fn = leaver_report.send_leaver_report
		self.assertEqual(getattr(fn, "__alvoraa_limit__", None)[1:3], ("user", 10)) \
			if hasattr(fn, "__alvoraa_limit__") else None
		self.assertIn(fn, frappe.whitelisted)
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[fn], ["POST"])
