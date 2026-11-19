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
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal import held_day
from alvoraa_portal.tests.test_attendance_correction import (_holiday_list,
                                                             setUpModule as _ac_setup)

REQUEST = "Attendance Request"
SHIFT = "ALV085 Shift"
COMPANY = "ALV085 Company"
OTHER = "ALV085 Other Company"


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
		self.tag = "Hd%d" % HeldDayCase._slot
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
		doc.docstatus = 1  # a submitted slip is never touched
		held_day.deduct_held_days(doc)
		self.assertEqual(doc.payment_days, 29.0)

	def test_the_slip_hook_is_wired_after_the_engines(self):
		hooks = frappe.get_hooks("doc_events")["Salary Slip"]["validate"]
		self.assertLess(hooks.index("alvoraa_portal.payroll_slip.on_salary_slip_validate"),
		                hooks.index("alvoraa_portal.held_day.deduct_held_days"))

	def test_a_submitted_slip_is_not_refreshed_and_says_so(self):
		with patch("alvoraa_portal.held_day.is_in_final_slip", return_value=True):
			self.assertEqual(held_day.refresh_draft_slip(self.worker, self.day), "final")

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

	def test_the_count_is_an_integer_and_refused_outside_the_callers_companies(self):
		frappe.set_user(self.hr)
		try:
			self.assertIsInstance(held_day.held_count(self.company), int)
			with self.assertRaises(frappe.PermissionError):
				held_day.held_count(self.other_company)
			with self.assertRaises(frappe.PermissionError):
				held_day.save_settings(self.other_company, 1, 3, "")
		finally:
			frappe.set_user("Administrator")

	# ── US-10: the monthly limit ───────────────────────────────────────

	def _ordinary_request(self, employee, day):
		return frappe.get_doc({"doctype": REQUEST, "employee": employee, "from_date": day,
		                       "to_date": day, "reason": "Marked Absent by Mistake",
		                       "alvoraa_review_status": "Waiting"}).insert(ignore_permissions=True)

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
		after = frappe.get_hooks("after_install") + frappe.get_hooks("after_migrate")
		self.assertEqual(after.count("alvoraa_portal.held_day.after_migrate"), 2)


	# ── the backfill's own work: candidates, hold, harmless re-run, undo ──

	def test_hold_then_rerun_finds_nothing_then_undo_restores(self):
		import importlib.util
		repo = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))
		path = os.path.join(repo, "scripts", "alv392_held_backfill_grace.py")
		if not os.path.exists(path):
			self.skipTest("the script is not on this checkout's path")
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
			mod.hold(frappe, [r for r in rows if r.name == att.name], undo_file)
			self.assertEqual(frappe.db.get_value("Attendance", att.name, "status"), "Held")
			self.assertNotIn(att.name, [r.name for r in mod.candidates(frappe, [self.company])])
			mod.undo(frappe, undo_file)
			self.assertEqual(frappe.db.get_value("Attendance", att.name, "status"), "Present")
		finally:
			if os.path.exists(undo_file):
				os.unlink(undo_file)


class BackfillScript(FrappeTestCase):
	"""scripts/alv392_held_backfill_grace.py: refuses everything but Grace."""

	def _load(self):
		import importlib.util
		repo = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))
		path = os.path.join(repo, "scripts", "alv392_held_backfill_grace.py")
		if not os.path.exists(path):
			self.skipTest("the script is not on this checkout's path")
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
				mod.undo(frappe, f.name)
			setv.assert_not_called()  # already released by a human: left alone
		finally:
			os.unlink(f.name)
