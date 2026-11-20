"""Slice 085 (ALV-392), Release 2: Held days.

A day with an odd number of punches is written as Held, is unpaid, and ends by
a late machine punch or an HR approval. Every test that proves a refusal has a
control beside it that proves the same act works for the person who may do it.
"""

import json
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal import held_day
from alvoraa_portal.tests.test_attendance_correction import (_holiday_list,
                                                             setUpModule as _ac_setup)

REQUEST = "Attendance Request"
SHIFT = "ALV085 Shift"
COMPANY = "ALV085 Company"
OTHER = "ALV085 Other Company"


def backfill_script_path():
	"""Where the backfill script is. CI copies only the apps into the bench, so the
	repo's scripts/ folder is in GITHUB_WORKSPACE there; locally it sits four folders
	above this file. A missing file fails the test: it never skips."""
	repo = os.environ.get("GITHUB_WORKSPACE") or os.path.abspath(
		os.path.join(os.path.dirname(__file__), *[".."] * 4))
	path = os.path.join(repo, "scripts", "alv392_held_backfill_grace.py")
	assert os.path.exists(path), "the backfill script is not at " + path
	return path


def setUpModule():
	_ac_setup()
	held_day.after_migrate()
	frappe.clear_cache()


def _make_company(name, abbr):
	from alvoraa_portal.tests.fixtures_043 import ensure_company
	return ensure_company(name, abbr)


class HeldDayCase(FrappeTestCase):
	_slot = 0

	def setUp(self):
		frappe.set_user("Administrator")
		HeldDayCase._slot += 1
		# Unique per run: the backfill script commits, and a committed fixture
		# survives Frappe's rollback.
		self.tag = "Hd%s%d" % (frappe.generate_hash(length=4), HeldDayCase._slot)
		self.company = _make_company(COMPANY, "A85C")
		self.other_company = _make_company(OTHER, "A85O")
		_holiday_list(self.company)
		_holiday_list(self.other_company)
		if not frappe.db.exists("Shift Type", SHIFT):
			frappe.get_doc({"doctype": "Shift Type", "name": SHIFT, "start_time": "09:00:00",
			                "end_time": "18:00:00", "working_hours_threshold_for_absent": 4,
			                "working_hours_threshold_for_half_day": 7,
			                "enable_auto_attendance": 1}).insert(ignore_permissions=True)
		self.set_switch(1)
		self.worker = self._employee("Worker")
		self.day = add_days(nowdate(), -5)
		self.hr = self._login("hr", ("HR Manager",))
		self.hr_emp = self._employee("Hr", self.hr)
		self.hr2 = self._login("hr2", ("HR Manager",))
		self._employee("Hrtwo", self.hr2)

	def tearDown(self):
		frappe.set_user("Administrator")

	# ── fixtures ────────────────────────────────────────────────────────

	def set_switch(self, on, limit=0, roles="", company=None):
		company = company or self.company
		frappe.db.set_value("Company", company, {held_day.SWITCH: on, held_day.LIMIT: limit,
		                                         held_day.EXEMPT: roles})
		frappe.clear_cache(doctype="Company")

	def _login(self, local, roles):
		email = "%s.%s.hd085@example.com" % (self.tag.lower(), local)
		u = frappe.get_doc({"doctype": "User", "email": email, "first_name": self.tag + local,
		                    "send_welcome_email": 0}).insert(ignore_permissions=True)
		for r in roles:
			u.add_roles(r)
		return email

	def _employee(self, first, user=None, company=None):
		doc = {"doctype": "Employee", "first_name": self.tag + first, "company": company or self.company,
		       "date_of_birth": "1970-01-01", "date_of_joining": "2000-01-01",
		       "gender": frappe.db.get_value("Gender", {}, "name") or "Male", "status": "Active",
		       "default_shift": SHIFT}
		if user:
			doc["user_id"] = user
			doc["create_user_permission"] = 0
		return frappe.get_doc(doc).insert(ignore_permissions=True).name

	def _punch(self, employee, hhmm, day=None, log_type=None, user=None):
		doc = frappe.get_doc({"doctype": "Employee Checkin", "employee": employee,
		                      "time": "%s %s:00" % (day or self.day, hhmm), "log_type": log_type or "IN"})
		if user:
			frappe.set_user(user)
		try:
			return doc.insert(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")

	def _attendance(self, employee, status="Present", in_time=True, **extra):
		doc = frappe.get_doc({"doctype": "Attendance", "employee": employee, "company": self.company,
		                      "attendance_date": self.day, "status": status, "shift": SHIFT,
		                      "in_time": ("%s 09:00:00" % self.day) if in_time else None, **extra})
		doc.insert(ignore_permissions=True)
		return doc

	def _held(self, employee=None):
		"""A submitted Held row for one punch at 09:00."""
		employee = employee or self.worker
		self._punch(employee, "09:00")
		att = self._attendance(employee)
		att.submit()
		return att

	def _request(self, employee, hhmm="18:30", log="OUT", by="Administrator"):
		frappe.set_user(by)
		try:
			doc = frappe.get_doc({"doctype": REQUEST, "employee": employee, "from_date": self.day,
			                      "to_date": self.day, "reason": "Forgot to Punch Out",
			                      "alvoraa_missing_time": hhmm, "alvoraa_missing_log": log,
			                      "alvoraa_review_status": "Waiting"})
			doc.insert(ignore_permissions=True)
			return doc.name
		finally:
			frappe.set_user("Administrator")

	def _approve(self, name, by):
		frappe.set_user(by)
		try:
			frappe.get_doc(REQUEST, name).submit()
		finally:
			frappe.set_user("Administrator")

	# ── US-1: Held exists ───────────────────────────────────────────────

	def test_held_is_a_status_and_the_fields_exist(self):
		options = (frappe.get_meta("Attendance").get_field("status").options or "").split("\n")
		self.assertIn("Held", options)
		for dt, fields in held_day.FIELDS.items():
			for f in fields:
				self.assertTrue(frappe.db.exists("Custom Field", {"dt": dt, "fieldname": f["fieldname"]}),
				                f["fieldname"])

	# ── US-3: the hold ─────────────────────────────────────────────────

	def test_one_punch_is_held_at_a_company_with_the_switch_on(self):
		self._punch(self.worker, "09:00")
		self.assertEqual(self._attendance(self.worker).status, "Held")

	def test_three_punches_are_held_and_two_are_not(self):
		for t in ("09:00", "13:00", "14:00"):
			self._punch(self.worker, t)
		self.assertEqual(self._attendance(self.worker).status, "Held")
		other = self._employee("Two")
		self._punch(other, "09:00")
		self._punch(other, "18:00", log_type="OUT")
		self.assertEqual(self._attendance(other).status, "Present")

	def test_switch_off_marks_as_before(self):
		self.set_switch(0)
		self._punch(self.worker, "09:00")
		self.assertEqual(self._attendance(self.worker).status, "Present")

	def test_a_request_made_row_and_a_row_with_no_in_time_are_never_held(self):
		self._punch(self.worker, "09:00")
		self.assertEqual(self._attendance(self.worker, in_time=False).status, "Present")

	def test_a_repeat_scan_does_not_make_two_punches_one_held_day_even(self):
		self._punch(self.worker, "09:00")
		self._punch(self.worker, "09:01")  # folded into the first by punch_dedupe
		self.assertEqual(self._attendance(self.worker).status, "Held")

	# ── US-4: release by HR ────────────────────────────────────────────

	def test_hr_approval_releases_by_the_shifts_own_thresholds(self):
		for hhmm, expected in (("18:30", "Present"), ("14:00", "Half Day"), ("11:00", "Absent")):
			emp = self._employee("Rel" + hhmm.replace(":", ""))
			self._punch(emp, "09:00")
			att = self._attendance(emp)
			att.submit()
			self._approve(self._request(emp, hhmm), self.hr)
			row = frappe.db.get_value("Attendance", att.name,
			                          ["status", "alvoraa_release_how", "alvoraa_release_by",
			                           "alvoraa_release_on"], as_dict=True)
			self.assertEqual(row.status, expected, hhmm)
			self.assertEqual((row.alvoraa_release_how, row.alvoraa_release_by), ("HR decision", self.hr))
			self.assertTrue(row.alvoraa_release_on)

	def test_a_held_day_with_no_shift_is_refused_in_one_sentence(self):
		att = self._held()
		frappe.db.set_value("Attendance", att.name, "shift", None)
		name = self._request(self.worker)
		with self.assertRaises(frappe.ValidationError) as cm:
			self._approve(name, self.hr)
		self.assertIn("no shift", str(cm.exception))
		self.assertEqual(frappe.db.get_value("Attendance", att.name, "status"), "Held")

	def test_a_time_for_a_day_that_is_not_held_is_refused(self):
		self._punch(self.worker, "09:00")
		self._punch(self.worker, "18:00", log_type="OUT")
		self._attendance(self.worker).submit()
		with self.assertRaises(frappe.ValidationError):
			self._request(self.worker)

	def test_the_request_for_a_held_day_needs_a_time(self):
		self._held()
		frappe.set_user("Administrator")
		doc = frappe.get_doc({"doctype": REQUEST, "employee": self.worker, "from_date": self.day,
		                      "to_date": self.day, "reason": "Forgot to Punch Out",
		                      "alvoraa_review_status": "Waiting"}).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self._approve(doc.name, self.hr)

	def test_the_hr_card_previews_what_approval_will_do(self):
		self._held()
		self.assertEqual(held_day.preview(self.worker, self.day, "11:00", "OUT")["status"], "Absent")
		self.assertEqual(held_day.preview(self.worker, self.day, "18:30", "OUT")["status"], "Present")

	# ── US-5: a late machine punch ─────────────────────────────────────

	def _machine(self):
		if not frappe.db.exists("Role", "Biometric Sync"):
			frappe.get_doc({"doctype": "Role", "role_name": "Biometric Sync"}).insert(ignore_permissions=True)
		email = "%s.machine.hd085@example.com" % self.tag.lower()
		u = frappe.get_doc({"doctype": "User", "email": email, "first_name": "Machine" + self.tag,
		                    "send_welcome_email": 0, "roles": [{"role": "Biometric Sync"}]}
		                   ).insert(ignore_permissions=True)
		return u.name

	def test_a_late_machine_punch_releases_the_day(self):
		att = self._held()
		machine = self._machine()
		with patch("frappe.enqueue") as enq:
			punch = self._punch(self.worker, "18:30", log_type="OUT", user=machine)
		row = frappe.db.get_value("Attendance", att.name, ["status", "alvoraa_release_how",
		                                                   "alvoraa_release_by"], as_dict=True)
		self.assertEqual(row.status, "Present")
		self.assertEqual((row.alvoraa_release_how, row.alvoraa_release_by), ("Machine punch", punch.name))
		# The slip refresh is queued after commit, with ids only.
		kwargs = enq.call_args.kwargs
		self.assertTrue(kwargs["enqueue_after_commit"])
		self.assertEqual(set(kwargs) - {"enqueue_after_commit", "queue"}, {"employee", "date"})

	def test_a_punch_by_anyone_but_the_machine_account_leaves_the_day_held(self):
		att = self._held()
		self._punch(self.worker, "18:30", log_type="OUT", user=self.hr)  # an HR-added punch
		self.assertEqual(frappe.db.get_value("Attendance", att.name, "status"), "Held")
		self._punch(self.worker, "18:40", log_type="OUT")  # a staff/admin login with a device id
		self.assertEqual(frappe.db.get_value("Attendance", att.name, "status"), "Held")

	def test_a_fault_in_the_release_never_fails_the_punch(self):
		self._held()
		machine = self._machine()
		with patch("alvoraa_portal.held_day.worked_out", side_effect=RuntimeError("boom")):
			punch = self._punch(self.worker, "18:30", log_type="OUT", user=machine)
		self.assertTrue(frappe.db.exists("Employee Checkin", punch.name))

	# ── the slip ───────────────────────────────────────────────────────

	def test_held_days_are_taken_off_the_payment_days(self):
		self._held()
		doc = SimpleNamespace(docstatus=0, employee=self.worker, company=self.company,
		                      start_date=add_days(self.day, -3), end_date=add_days(self.day, 3),
		                      payment_days=30.0, absent_days=0.0, calls=[])
		for name in ("calculate_net_pay", "compute_year_to_date", "compute_month_to_date",
		             "compute_component_wise_year_to_date"):
			setattr(doc, name, lambda n=name: doc.calls.append(n))
		held_day.deduct_held_days(doc)
		self.assertEqual((doc.payment_days, doc.absent_days), (29.0, 1.0))
		self.assertIn("calculate_net_pay", doc.calls)
		doc.docstatus = 2  # a cancelled slip is never touched
		held_day.deduct_held_days(doc)
		self.assertEqual(doc.payment_days, 29.0)

	def test_the_slip_hook_is_wired_after_the_engines(self):
		hooks = frappe.get_hooks("doc_events")["Salary Slip"]["validate"]
		self.assertLess(hooks.index("alvoraa_portal.payroll_slip.on_salary_slip_validate"),
		                hooks.index("alvoraa_portal.held_day.deduct_held_days"))

	def test_a_submitted_slip_is_not_refreshed_and_says_so(self):
		with patch("alvoraa_portal.held_day.is_in_final_slip", return_value=True):
			self.assertEqual(held_day.refresh_draft_slip(self.worker, self.day), "final")

	# ── review fix round 1 ─────────────────────────────────────────────

	def test_f2_administrator_is_not_the_machine_and_does_not_release_a_day(self):
		from alvoraa_portal.field_app_access import files_as_machine
		self.assertFalse(files_as_machine("Administrator"))
		att = self._held()
		self._punch(self.worker, "18:30", log_type="OUT")  # filed as Administrator
		self.assertEqual(frappe.db.get_value("Attendance", att.name, "status"), "Held")
		# control: a real sync account still releases a held day (another person: this
		# one now has two punches, so one more would make it odd again)
		other = self._employee("Fm2")
		att2 = self._held(other)
		with patch("frappe.enqueue"):
			self._punch(other, "18:40", log_type="OUT", user=self._machine())
		self.assertEqual(frappe.db.get_value("Attendance", att2.name, "status"), "Present")

	def test_f3_a_multi_day_request_cannot_turn_a_held_day_into_present(self):
		att = self._held()
		frappe.set_user("Administrator")
		doc = frappe.get_doc({"doctype": REQUEST, "employee": self.worker,
		                      "from_date": add_days(self.day, -1), "to_date": self.day,
		                      "reason": "On Duty", "alvoraa_review_status": "Waiting"
		                      }).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError) as cm:
			self._approve(doc.name, self.hr)
		self.assertIn("covers a held day", str(cm.exception))
		self.assertEqual(frappe.db.get_value("Attendance", att.name, "status"), "Held")
		# control: the same two days with no held day in them are approved as before
		other = self._employee("Plain")
		clean = frappe.get_doc({"doctype": REQUEST, "employee": other,
		                        "from_date": add_days(self.day, -1), "to_date": self.day,
		                        "reason": "On Duty", "alvoraa_review_status": "Waiting"
		                        }).insert(ignore_permissions=True)
		self._approve(clean.name, self.hr)
		self.assertEqual(frappe.db.get_value(REQUEST, clean.name, "docstatus"), 1)

	def test_m3_a_held_day_on_the_assigned_lists_holiday_costs_no_second_day(self):
		"""The employee's own field is empty and a Holiday List Assignment holds the
		list: the slip leaves that day out already, so the hook must too."""
		self._held()
		frappe.db.set_value("Employee", self.worker, "holiday_list", None)
		listname = "ALV085 M3 holidays"
		if not frappe.db.exists("Holiday List", listname):
			frappe.get_doc({"doctype": "Holiday List", "holiday_list_name": listname,
			                "from_date": add_days(self.day, -400), "to_date": add_days(self.day, 400),
			                "holidays": [{"holiday_date": self.day, "description": "M3"}]}
			               ).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Holiday List Assignment", "applicable_for": "Employee",
		                "assigned_to": self.worker, "holiday_list": listname,
		                "from_date": add_days(self.day, -300)}).insert(ignore_permissions=True).submit()
		self.assertEqual(held_day.held_dates(self.worker, add_days(self.day, -3), add_days(self.day, 3)), [])
		# control: with no assignment on that date the day does cost
		other = self._employee("M3b")
		self._punch(other, "09:00")
		self._attendance(other).submit()
		self.assertEqual(len(held_day.held_dates(other, add_days(self.day, -3), add_days(self.day, 3))), 1)

	def test_ac69_084s_own_day_window_does_not_refuse_a_held_day_request(self):
		user = self._login("emp084", ("Employee",))
		emp = self._employee("Emp084", user)
		self._punch(emp, "09:00")
		self._attendance(emp).submit()
		saved = frappe.db.get_default(ac.EMPLOYEE_FILING_WINDOW_KEY)
		frappe.db.set_default(ac.EMPLOYEE_FILING_WINDOW_KEY, "0")  # today only
		try:
			frappe.set_user(user)
			try:
				frappe.get_doc({"doctype": REQUEST, "employee": emp, "from_date": self.day,
				                "to_date": self.day, "reason": "Forgot to Punch Out",
				                "alvoraa_missing_time": "18:30", "alvoraa_missing_log": "OUT",
				                "alvoraa_review_status": "Waiting"}).insert()
				# control: an ordinary request for the same old day IS refused by 084
				with self.assertRaises(frappe.ValidationError):
					frappe.get_doc({"doctype": REQUEST, "employee": emp, "from_date": self.day,
					                "to_date": self.day, "reason": "On Duty",
					                "alvoraa_review_status": "Waiting"}).insert()
			finally:
				frappe.set_user("Administrator")
		finally:
			frappe.db.set_default(ac.EMPLOYEE_FILING_WINDOW_KEY, saved or "")

	def test_the_hold_switch_defaults_to_off_for_every_company(self):
		"""One release (decision 1): nothing is held anywhere until the switch is ticked."""
		self.assertEqual(frappe.db.get_value("Custom Field", {"dt": "Company", "fieldname": held_day.SWITCH},
		                                     "default"), "0")
		# No company is created here: a new Company would stay on the shared site and
		# change which company other modules pick first.
		self.set_switch(0, company=self.other_company)
		frappe.db.sql("update `tabCompany` set `%s` = default(`%s`) where name = %%s" % (held_day.SWITCH, held_day.SWITCH),
		              self.other_company)
		frappe.clear_cache(doctype="Company")
		self.assertFalse(held_day._switch_on(self.other_company))

	def test_both_attendance_request_validate_hooks_are_kept(self):
		hooks = frappe.get_hooks("doc_events")["Attendance Request"]["validate"]
		for h in ("alvoraa_portal.held_day.validate_missing_time",
		          "alvoraa_portal.attendance_correction.refuse_own_day_outside_window"):
			self.assertIn(h, hooks)

	# ── US-14 / SEC-6: who may change the settings ─────────────────────

	def _as_save(self, user, company=None, **values):
		frappe.set_user(user)
		try:
			doc = frappe.get_doc("Company", company or self.company)
			doc.update(values)
			doc.save(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")

	def test_only_an_hr_manager_of_the_company_may_change_the_settings(self):
		hr_user = self._login("hru", ("HR User",))
		self._employee("Hru", hr_user)
		accounts = self._login("acc", ("Accounts Manager",))
		other_hr = self._login("ohr", ("HR Manager",))
		self._employee("Ohr", other_hr, company=self.other_company)
		for user in (hr_user, accounts, other_hr):
			with self.assertRaises(frappe.PermissionError):
				self._as_save(user, **{held_day.LIMIT: 5})
		self._as_save(self.hr, **{held_day.LIMIT: 5})
		self.assertEqual(frappe.db.get_value("Company", self.company, held_day.LIMIT), 5)
		self._as_save("Administrator", **{held_day.LIMIT: 6})

	def test_an_unknown_exempt_role_is_refused_with_its_name(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			self._as_save("Administrator", **{held_day.EXEMPT: "Sales Executive, No Such Role"})
		self.assertIn("No Such Role", str(cm.exception))

	def test_saving_settings_is_refused_outside_the_callers_companies(self):
		frappe.set_user(self.hr)
		try:
			with self.assertRaises(frappe.PermissionError):
				held_day.save_settings(self.other_company, 1, 3, "")
		finally:
			frappe.set_user("Administrator")

	# ── US-10: the monthly limit ───────────────────────────────────────

	def _login_of(self, employee):
		"""The employee's own login, made once. The limit counts the employee's own
		requests, so these are filed as that login, not as Administrator (who is
		treated as HR and never counted)."""
		user = frappe.db.get_value("Employee", employee, "user_id")
		if not user:
			user = self._login("own" + frappe.generate_hash(length=5), ("Employee",))
			frappe.db.set_value("Employee", employee, "user_id", user)
		return user

	def _ordinary_request(self, employee, day, by=None):
		frappe.set_user(by or self._login_of(employee))
		try:
			return frappe.get_doc({"doctype": REQUEST, "employee": employee, "from_date": day,
			                       "to_date": day, "reason": "Marked Absent by Mistake",
			                       "alvoraa_review_status": "Waiting"}).insert(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")

	def test_r_hr_filed_requests_are_never_refused_and_never_counted(self):
		"""Decision 2: HR filing for an employee is outside the limit. The employee's own
		requests and a manager's on-behalf ones count."""
		self.set_switch(1, limit=2)
		first = add_days(frappe.utils.get_first_day(add_days(nowdate(), -40)), 3)
		self._ordinary_request(self.worker, first)
		self._ordinary_request(self.worker, add_days(first, 1))
		with self.assertRaises(frappe.ValidationError):  # the employee is at the limit
			self._ordinary_request(self.worker, add_days(first, 2))
		for n in range(3):  # HR files three more: none refused
			self._ordinary_request(self.worker, add_days(first, 2 + n), by=self.hr)
		# and the HR ones did not count: a manager on behalf (no HR role) is the 3rd that counts
		mgr = self._login("mgr", ("Employee",))
		with self.assertRaises(frappe.ValidationError):
			self._ordinary_request(self.worker, add_days(first, 6), by=mgr)
		# control: another employee with only HR-filed requests so far still has both own slots
		other = self._employee("Hrfiled")
		for n in range(3):
			self._ordinary_request(other, add_days(first, n), by=self.hr)
		self._ordinary_request(other, add_days(first, 4))
		self._ordinary_request(other, add_days(first, 5))
		with self.assertRaises(frappe.ValidationError):
			self._ordinary_request(other, add_days(first, 6))

	def test_f4_a_held_day_draft_edited_into_an_ordinary_request_is_counted(self):
		"""The held-day draft carries a time, so it is outside the limit when made. Edited
		into an ordinary request, it is counted at the next save, not only at insert."""
		self.set_switch(1, limit=1)
		user = self._login_of(self.worker)
		self._held()
		name = self._request(self.worker, by=user)  # a draft with a time: not counted
		near = add_days(self.day, 1)
		if getdate(near).month != getdate(self.day).month:
			near = add_days(self.day, -1)
		self._ordinary_request(self.worker, near)  # the one allowed request this month
		frappe.set_user(user)
		try:
			doc = frappe.get_doc(REQUEST, name)
			doc.alvoraa_missing_time = None
			doc.alvoraa_missing_log = None
			with self.assertRaises(frappe.ValidationError) as cm:
				doc.save(ignore_permissions=True)
			self.assertIn("Held days do not count", str(cm.exception))
		finally:
			frappe.set_user("Administrator")

	def test_the_fourth_ordinary_request_is_refused_and_a_held_one_is_not(self):
		self.set_switch(1, limit=3)
		first = frappe.utils.get_first_day(add_days(nowdate(), -40))
		first = add_days(first, 3)
		month_days = [first, add_days(first, 1), add_days(first, 2)]
		for d in month_days:
			self._ordinary_request(self.worker, d)
		with self.assertRaises(frappe.ValidationError) as cm:
			self._ordinary_request(self.worker, add_days(first, 3))
		self.assertIn("Held days do not count", str(cm.exception))
		self._held()  # the held day's request carries a time, so it is accepted at any count
		self._request(self.worker)

	def test_an_exempt_role_and_limit_zero_are_never_refused(self):
		user = self._login("sales", ("Employee",))
		emp = self._employee("Sales", user)
		self.set_switch(1, limit=1, roles="Employee")
		first = add_days(frappe.utils.get_first_day(add_days(nowdate(), -40)), 3)
		self._ordinary_request(emp, first)
		self._ordinary_request(emp, add_days(first, 1))
		self.set_switch(1, limit=0)
		self._ordinary_request(self.worker, first)
		self._ordinary_request(self.worker, add_days(first, 1))

	def test_ac44_the_limit_counts_the_way_graces_script_did(self):
		"""Grace's script: same from_date month, docstatus != 2, not Rejected,
		self excluded, three allowed, "Sales Executive" exempt by designation.
		A cancelled and a declined request do not count; a held-day request does
		not count; a designation named in the exempt list is never refused."""
		self.set_switch(1, limit=3)
		first = add_days(frappe.utils.get_first_day(add_days(nowdate(), -40)), 3)
		counted = [self._ordinary_request(self.worker, add_days(first, i)) for i in range(2)]
		cancelled = self._ordinary_request(self.worker, add_days(first, 2))
		frappe.db.set_value(REQUEST, cancelled.name, "docstatus", 2)
		declined = self._ordinary_request(self.worker, add_days(first, 3))
		frappe.db.set_value(REQUEST, declined.name, "alvoraa_review_status", "Declined")
		self._ordinary_request(self.worker, add_days(first, 4))  # the third that counts
		with self.assertRaises(frappe.ValidationError):
			self._ordinary_request(self.worker, add_days(first, 5))
		# a request in the NEXT month is a different month
		self._ordinary_request(self.worker, add_days(frappe.utils.get_last_day(first), 2))
		# designation exemption, as Grace's script had it
		if not frappe.db.exists("Designation", "Sales Executive"):
			frappe.get_doc({"doctype": "Designation", "designation_name": "Sales Executive"}
			               ).insert(ignore_permissions=True)
		sales = self._employee("Salesexec")
		frappe.db.set_value("Employee", sales, "designation", "Sales Executive")
		self.set_switch(1, limit=3, roles="Sales Executive")
		for i in range(5):
			self._ordinary_request(sales, add_days(first, i))

	# ── the month sheet (US-6) ─────────────────────────────────────────

	def test_the_month_names_the_held_day_and_sends_no_reason(self):
		self._held()
		frappe.set_user(self.hr_emp and frappe.db.get_value("Employee", self.worker, "user_id") or "Administrator")
		year, month = int(self.day[:4]), int(self.day[5:7])
		with patch.object(ac, "_me", return_value=frappe.get_doc("Employee", self.worker)):
			data = ac.month(year, month, self.worker)
		day = [d for d in data["days"] if d["date"] == self.day][0]
		self.assertTrue(day["held"])
		self.assertEqual(day["state"], "held")
		self.assertFalse(day["missing_punch"])
		self.assertEqual(data["totals"]["held"], 1)
		self.assertTrue(data["hold_on"])

	def test_a_held_request_sent_from_the_portal_carries_only_the_time(self):
		self._held()
		user = frappe.db.get_value("Employee", self.worker, "user_id")
		self.assertIsNone(user)  # the worker has no login: raise through the manager path instead
		frappe.set_user(self.hr)
		try:
			with patch.object(ac, "_subject", return_value=(
					frappe.get_doc("Employee", self.worker), False)), \
					patch.object(ac, "manager_on_behalf_on", return_value=True), \
					patch.object(ac, "_may_review", return_value=True):
				out = ac.raise_for_report(employee=self.worker, from_date=self.day,
				                          missing_time="18:30", missing_log="OUT")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(out["missing_time"], "18:30")
		# No free text: the only words on the request are the system's own stamp.
		self.assertEqual(frappe.db.get_value(REQUEST, out["name"], "explanation"),
		                 "Raised by %s on behalf of the employee." % frappe.db.get_value(
			                 "Employee", self.hr_emp, "employee_name"))
		self.assertEqual(out["reason"], "Forgot to Punch Out")

	# ── the vendored Monthly Attendance Sheet (D-3) ────────────────────

	def test_the_monthly_attendance_sheet_opens_with_a_held_row(self):
		import importlib
		sheet = importlib.import_module("hrms.hr.report.monthly_attendance_sheet.monthly_attendance_sheet")
		self._held()
		self.assertEqual(sheet.status_map["Held"], "HLD")
		self.assertGreaterEqual(len(sheet.get_message().split("border-left")) - 1, len(sheet.status_map))
		from frappe.utils import getdate
		filters = {"filter_based_on": "Month", "month": getdate(self.day).month,
		           "year": getdate(self.day).year, "company": self.company, "employee": self.worker}
		columns, data, *_rest = sheet.execute(filters)
		self.assertTrue(data)

	# ── Release 2 is wired where the spec says ─────────────────────────

	def test_the_hooks_are_wired(self):
		events = frappe.get_hooks("doc_events")
		self.assertIn("alvoraa_portal.held_day.hold_odd_punch_day", events["Attendance"]["validate"])
		self.assertIn("alvoraa_portal.held_day.release_on_machine_punch", events["Employee Checkin"]["after_insert"])
		self.assertIn("alvoraa_portal.held_day.release_by_hr", events["Attendance Request"]["on_submit"])
		self.assertIn("alvoraa_portal.held_day.guard_company_settings", events["Company"]["validate"])
		self.assertIn("public/js/attendance_list_held.js", frappe.get_hooks("doctype_list_js")["Attendance"])
		after = frappe.get_hooks("after_install") + frappe.get_hooks("after_migrate")
		self.assertEqual(after.count("alvoraa_portal.held_day.after_migrate"), 2)


	# ── who counts as a machine (P1, SEC-5) ──

	def test_files_as_machine_for_every_real_account_shape_and_for_no_human(self):
		from alvoraa_portal.field_app_access import files_as_machine
		if not frappe.db.exists("Role", "Biometric Sync"):
			frappe.get_doc({"doctype": "Role", "role_name": "Biometric Sync"}).insert(ignore_permissions=True)
		for name, roles, expected in (
				("sync", ("Biometric Sync",), True),
				("synchru", ("Biometric Sync", "HR User"), True),
				("synchrm", ("Biometric Sync", "HR Manager"), True),
				("hruser", ("HR User",), False),
				("hrmgr", ("HR Manager", "HR User"), False),
				("sysmgr", ("System Manager",), False)):
			self.assertEqual(files_as_machine(self._login(name, roles)), expected, name)
		# The role on a person who has an Employee record is not a machine.
		person = self._login("syncperson", ("Biometric Sync", "HR User"))
		self._employee("Syncperson", person)
		self.assertFalse(files_as_machine(person))

	def test_a_human_hr_user_without_the_sync_role_cannot_release_with_a_punch(self):
		att = self._held()
		for n, roles in enumerate((("HR User",), ("HR Manager", "HR User"))):
			user = self._login("human%d" % n, roles)  # no Employee record, as an admin login
			self._punch(self.worker, "18:%d" % (30 + n * 5), log_type="OUT", user=user)
			self.assertEqual(frappe.db.get_value("Attendance", att.name, "status"), "Held", roles)

	def _backfill_module(self):
		import importlib.util
		path = backfill_script_path()
		spec = importlib.util.spec_from_file_location("held_backfill_e2e", path)
		mod = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(mod)
		return mod

	def _marked_before_switch(self, hhmm="09:00"):
		self.day = "2026-11-10"
		self.set_switch(0)
		emp = self._employee("Bf" + frappe.generate_hash(length=3))
		self._punch(emp, hhmm)
		att = self._attendance(emp)
		att.submit()
		self.set_switch(1)
		return att.name

	def test_backfill_end_to_end_dry_run_then_apply_then_undo(self):
		"""AC-58, 62, 63 through run(), the same path the command line takes."""
		mod = self._backfill_module()
		att = self._marked_before_switch()
		undo_file = tempfile.mktemp(suffix=".jsonl")
		kw = {"_in_test_site": frappe.local.site}
		try:
			with patch.object(frappe.db, "commit"):
				# AC-63: no real run without a dry run
				with self.assertRaises(SystemExit) as cm:
					mod.run(frappe.local.site, undo_file, apply=True, **kw)
				self.assertIn("dry run first", str(cm.exception))
				self.assertEqual(frappe.db.get_value("Attendance", att, "status"), "Present")
				dry = mod.run(frappe.local.site, undo_file, **kw)
				self.assertGreaterEqual(dry["count"], 1)
				self.assertEqual(frappe.db.get_value("Attendance", att, "status"), "Present")  # dry run changes nothing
				# AC-63: the count moved after the dry run, so the real run stops
				self._marked_before_switch("09:05")
				with self.assertRaises(SystemExit) as cm:
					mod.run(frappe.local.site, undo_file, apply=True, **kw)
				self.assertIn("Run the dry run again", str(cm.exception))
				self.assertEqual(frappe.db.get_value("Attendance", att, "status"), "Present")
				# dry run again, then the real run
				import contextlib
				import io
				out = io.StringIO()
				with contextlib.redirect_stdout(out):
					again = mod.run(frappe.local.site, undo_file, **kw)
				# AC-63: the printed split, one punch against three or more, and the old status
				self.assertRegex(out.getvalue(), r"one punch: \d+, three or more punches: \d+\. "
				                 r"Was Absent: \d+, Present: \d+, Half Day: \d+\.")
				out = io.StringIO()
				with contextlib.redirect_stdout(out):
					done = mod.run(frappe.local.site, undo_file, apply=True, operator="Test Operator", **kw)
				self.assertEqual(done["count"], again["count"])
				self.assertEqual(frappe.db.get_value("Attendance", att, "status"), "Held")
				# AC-59: the audit Comment names the run and the person
				run_id = out.getvalue().split("Run id ")[1].split(",")[0]
				self.assertEqual(len(run_id), 8)
				note = frappe.db.get_value("Comment", {"reference_doctype": "Attendance",
				                                      "reference_name": att, "comment_type": "Info"}, "content")
				self.assertIn(run_id, note)
				self.assertIn("Test Operator", note)
				# AC-58: every changed id is in the undo list
				with open(undo_file) as f:
					listed = [json.loads(x)["name"] for x in f if x.strip()]
				self.assertIn(att, listed)
				self.assertEqual(len(listed), done["count"])
				# harmless to re-run: nothing left, and the stale dry-run count stops it
				with self.assertRaises(SystemExit):
					mod.run(frappe.local.site, undo_file, apply=True, **kw)
				mod.run(frappe.local.site, undo_file, undo=True, **kw)
				self.assertEqual(frappe.db.get_value("Attendance", att, "status"), "Present")
		finally:
			for f in (undo_file, undo_file + ".dryrun"):
				if os.path.exists(f):
					os.unlink(f)

	def test_a_day_in_a_submitted_slip_is_not_held_by_the_backfill(self):
		mod = self._backfill_module()
		att = self._marked_before_switch()
		with patch("alvoraa_portal.held_day.is_in_final_slip", return_value=True):
			self.assertNotIn(att, [r.name for r in mod.candidates(frappe, [self.company])])

	def test_the_test_hook_still_refuses_every_other_site(self):
		mod = self._backfill_module()
		for site in ("dtc.alvoraa.co", "ppj.dev.alvoraa.co", "aahr.alvoraa.co"):
			with self.assertRaises(SystemExit) as cm:
				mod.run(site, "/tmp/x.jsonl", _in_test_site=frappe.local.site)
			self.assertIn("grace.alvoraa.co", str(cm.exception))

	# ── the backfill's own work: candidates, hold, harmless re-run, undo ──

	def test_hold_then_rerun_finds_nothing_then_undo_restores(self):
		import importlib.util
		path = backfill_script_path()
		spec = importlib.util.spec_from_file_location("held_backfill_run", path)
		mod = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(mod)
		self.day = "2026-11-10"
		self.set_switch(0)
		self._punch(self.worker, "09:00")
		att = self._attendance(self.worker)
		att.submit()
		self.assertEqual(att.status, "Present")  # marked while the switch was off
		self.set_switch(1)
		rows = mod.candidates(frappe, [self.company])
		self.assertIn(att.name, [r.name for r in rows if r.name == att.name])
		undo_file = tempfile.mktemp(suffix=".jsonl")
		try:
			with patch.object(frappe.db, "commit"):
				mod.hold(frappe, [r for r in rows if r.name == att.name], undo_file)
			self.assertEqual(frappe.db.get_value("Attendance", att.name, "status"), "Held")
			self.assertNotIn(att.name, [r.name for r in mod.candidates(frappe, [self.company])])
			with patch.object(frappe.db, "commit"):
				mod.undo_run(frappe, undo_file)
			self.assertEqual(frappe.db.get_value("Attendance", att.name, "status"), "Present")
		finally:
			if os.path.exists(undo_file):
				os.unlink(undo_file)


class BackfillScript(FrappeTestCase):
	"""scripts/alv392_held_backfill_grace.py: refuses everything but Grace."""

	def _load(self):
		import importlib.util
		path = backfill_script_path()
		spec = importlib.util.spec_from_file_location("held_backfill", path)
		mod = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(mod)
		return mod

	def test_it_refuses_any_other_site_and_a_repo_undo_file(self):
		mod = self._load()
		for argv in (["x", "--site", "test_site", "--undo-file", "/tmp/u.jsonl"],
		             ["x", "--site", "dtc.alvoraa.co", "--undo-file", "/tmp/u.jsonl"]):
			with patch("sys.argv", argv), self.assertRaises(SystemExit) as cm:
				mod.main()
			self.assertIn("grace.alvoraa.co", str(cm.exception))
		with patch("sys.argv", ["x", "--site", mod.SITE, "--undo-file", os.path.join(
				os.path.dirname(mod.__file__), "undo.jsonl")]), self.assertRaises(SystemExit) as cm:
			mod.main()
		self.assertIn("outside the repository", str(cm.exception))

	def test_undo_puts_back_only_rows_that_are_still_held(self):
		mod = self._load()
		with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
			f.write(json.dumps({"name": "NO-SUCH-ROW", "status": "Present", "half_day_status": None}) + "\n")
		try:
			with patch.object(frappe.db, "get_value", return_value="Present"), \
					patch.object(frappe.db, "set_value") as setv, patch.object(frappe.db, "commit"):
				mod.undo_run(frappe, f.name)
			setv.assert_not_called()  # already released by a human: left alone
		finally:
			os.unlink(f.name)
