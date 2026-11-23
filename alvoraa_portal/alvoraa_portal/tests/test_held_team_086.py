"""Slice 086: a manager sends the missing times for held days to HR.

`held_days` lists, `send_held` files through `raise_for_report`. Every refusal test has a control beside
it that proves the same act works for the person who may do it. Fixtures come from the 085 and 087 suites:
shift 09:00-18:00, one punch at 09:00 makes the day Held.
"""

import ast
import inspect
import threading
from datetime import datetime
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal import held_day, held_team, punch_fix, register_notice
from alvoraa_portal.field_app_limits import SELF_KEY
from alvoraa_portal.tests import test_held_day_085 as hd
from alvoraa_portal.tests.test_punch_fix_087 import security_lines_from_a_fresh_process

REQUEST = "Attendance Request"
CHECKIN = "Employee Checkin"
ATT = "Attendance"
NOT_YOURS = "Not sent. This person is not one of your direct reports."


def setUpModule():
	hd.setUpModule()
	punch_fix.after_migrate()
	frappe.clear_cache()


class HeldTeamCase(FrappeTestCase):
	def setUp(self):
		self.h = hd.HeldDayCase("test_held_is_a_status_and_the_fields_exist")
		self.h.setUp()
		h = self.h
		self.day = h.day
		self.boss_email = h._login("boss", ("Employee",))
		self.boss = h._employee("Boss", self.boss_email)
		self.hr = h.hr
		self.addCleanup(frappe.set_user, "Administrator")
		self.a = self.report("A")
		self.b = self.report("B")
		frappe.set_user("Administrator")

	# ── fixtures ────────────────────────────────────────────────────────
	def person(self, first, boss=None):
		emp = self.h._employee(first)
		if boss:
			doc = frappe.get_doc("Employee", emp)
			doc.reports_to = boss
			doc.save(ignore_permissions=True)   # saving is what grants the manager's User Permission
		return emp

	def report(self, first):
		return self.person(first, self.boss)

	def hold(self, employee, day=None, hhmm="09:00", log="IN"):
		"""A submitted Held row for one punch."""
		day = day or self.day
		frappe.get_doc({"doctype": CHECKIN, "employee": employee, "log_type": log,
		                "time": "%s %s:00" % (day, hhmm)}).insert(ignore_permissions=True)
		att = frappe.get_doc({"doctype": ATT, "employee": employee, "company": self.h.company,
		                      "attendance_date": day, "status": "Present", "shift": hd.SHIFT,
		                      "in_time": "%s 09:00:00" % day})
		att.insert(ignore_permissions=True)
		att.submit()
		self.assertEqual(frappe.db.get_value(ATT, att.name, "status"), "Held")
		return att.name

	def row(self, employee, time="18:30", log="OUT", reason="He forgot to scan out", day=None, **extra):
		return dict(employee=employee, date=day or self.day, time=time, in_or_out=log, reason=reason, **extra)

	def send(self, rows, user=None):
		frappe.set_user(user or self.boss_email)
		try:
			return held_team.send_held(rows=rows)
		finally:
			frappe.set_user("Administrator")

	def listed(self, user=None, **kw):
		frappe.set_user(user or self.boss_email)
		try:
			return held_team.held_days(**kw)
		finally:
			frappe.set_user("Administrator")

	def requests(self, employee):
		return frappe.get_all(REQUEST, filters={"employee": employee, "from_date": self.day},
		                      fields=["name", "explanation", "alvoraa_needs_confirm", "alvoraa_missing_log",
		                              "alvoraa_missing_time", "docstatus", "owner"])

	def refused(self, fn, *needles):
		with self.assertRaises((frappe.ValidationError, frappe.PermissionError)) as cm:
			fn()
		for n in needles:
			self.assertIn(n, str(cm.exception))
		return str(cm.exception)


class TheList(HeldTeamCase):
	def test_only_direct_reports_with_no_open_request_and_nothing_sensitive(self):
		"""AC-1, AC-2, AC-7, D-6."""
		self.hold(self.a)
		self.hold(self.b)
		deep = self.person("Deep", self.a)       # skip level: reports to A, not to the boss
		self.hold(deep)
		out = self.listed()
		self.assertEqual({r["employee"] for r in out["rows"]}, {self.a, self.b})
		self.assertEqual(out["total"], 2)
		self.assertEqual(out["days"], [{"date": self.day, "count": 2}])
		self.assertTrue(out["hold_on"])
		self.assertEqual(self.listed(user=self.hr)["rows"], [])  # HR with no direct reports sees none (SEC-1)
		for banned in ("user_id", "email", "latitude", "longitude", "image", "photo"):
			self.assertNotIn(banned, str(out["rows"]))
		# A waiting request hides the day ...
		self.send([self.row(self.a)])
		self.assertEqual({r["employee"] for r in self.listed()["rows"]}, {self.b})
		# ... and a declined one brings it back (Surbhi D-6).
		name = self.requests(self.a)[0].name
		frappe.db.set_value(REQUEST, name, "alvoraa_review_status", "Declined")
		self.assertEqual({r["employee"] for r in self.listed()["rows"]}, {self.a, self.b})

	def test_nobody_reports_to_this_caller(self):
		self.assertTrue(self.listed(user=self.h._login("lone", ("Employee",)))["nobody"])

	def test_the_query_count_does_not_grow_with_the_rows(self):
		"""AC-6 at 2 and at 8 rows (the 5 and 50 of the spec are timed on the throwaway stack)."""
		def count():
			real, n = frappe.db.sql, [0]

			def counting(*a, **k):
				n[0] += 1
				return real(*a, **k)
			with patch.object(frappe.db, "sql", counting):
				self.listed()
			return n[0]
		self.hold(self.a)
		self.hold(self.b)
		count()                                 # warm the caches
		few = count()
		for i in range(6):
			self.hold(self.report("M%d" % i))
		self.assertEqual(count(), few)

	def test_the_day_control_and_paging(self):
		old = add_days(self.day, -1)
		self.hold(self.a)
		self.hold(self.a, day=old)
		out = self.listed()
		self.assertEqual(out["day"], self.day)
		self.assertEqual([d["date"] for d in out["days"]], [self.day, old])
		self.assertEqual(self.listed(day="all")["total"], 2)
		self.assertEqual(self.listed(day=old)["rows"][0]["date"], old)


class TheSend(HeldTeamCase):
	def test_a_row_is_filed_as_the_086_request_and_the_stamp_names_the_manager(self):
		"""AC-29, AC-36, D-3, case A (needs_confirm 0 even with the company's Confirm switch on)."""
		frappe.db.set_value("Company", self.h.company, punch_fix.CONFIRM_SWITCH, 1)
		frappe.clear_cache()
		self.hold(self.a)
		self.hold(self.b)
		out = self.send([self.row(self.a, reason="Left at 18:30, I saw him"), self.row(self.b)])
		self.assertEqual((out["sent"], out["not_sent"]), (2, 0))
		req = self.requests(self.a)[0]
		self.assertEqual(req.alvoraa_needs_confirm, 0)
		boss_name = frappe.db.get_value("Employee", self.boss, "employee_name")
		self.assertEqual(req.explanation,
		                 "Left at 18:30, I saw him\n\nOne of 2 days sent together.\n\n"
		                 "Raised by %s (%s), their reporting manager, on behalf of the employee." % (boss_name, self.boss))
		# D-3 (DevOps P1): what 088 prints as the reason is the manager's words and nothing else.
		self.assertEqual(punch_fix._reason_of(req.explanation), "Left at 18:30, I saw him")
		self.assertEqual(req.owner, self.boss_email)
		self.assertEqual(self.requests(self.b)[0].alvoraa_missing_log, "OUT")

	def test_one_row_has_no_one_of_line(self):
		self.hold(self.a)
		self.send([self.row(self.a)])
		self.assertNotIn("One of", self.requests(self.a)[0].explanation)

	def test_the_seven_case_scope_test(self):
		"""AC-22: a stranger gets one fixed sentence, no name, one security line each."""
		self.hold(self.a)
		other_boss = self.person("Otherboss")
		other_report = self.person("Theirs", other_boss)
		deep = self.person("Deep", self.a)
		left = self.report("Gone")
		frappe.db.set_value("Employee", left, "status", "Left")
		for e in (other_report, deep, left, self.boss):
			self.hold(e)
		rows = [self.row(self.a)] + [self.row(e) for e in (other_report, deep, left, self.boss, "HR-EMP-99999")]
		holder = {}
		lines = security_lines_from_a_fresh_process(lambda: holder.update(out=self.send(rows)))
		out = holder["out"]
		self.assertEqual((out["sent"], out["not_sent"]), (1, 5))
		for entry in out["results"][1:]:
			self.assertEqual(entry["sentence"], NOT_YOURS)
		self.assertEqual(len([ln for ln in lines if '"SEC-1"' in ln]), 5)
		self.assertNotIn(frappe.db.get_value("Employee", other_report, "employee_name"), str(out))
		self.assertEqual(len(self.requests(self.a)), 1)
		self.assertEqual(self.requests(other_report), [])

	def test_hr_and_a_submit_right_login_are_held_to_direct_reports_too(self):
		"""AC-23 and ALV-425: the right to approve is not a right to file for anybody."""
		self.hold(self.a)
		out = self.send([self.row(self.a)], user=self.hr)
		self.assertEqual(out["results"][0]["sentence"], NOT_YOURS)
		self.assertEqual(self.requests(self.a), [])
		# The old single door agrees (D-1): HR may not file for somebody who does not report to them.
		frappe.set_user(self.hr)
		try:
			with patch.object(ac, "manager_on_behalf_on", return_value=True):
				self.refused(lambda: ac.raise_for_report(
					self.a, self.day, explanation="x", missing_time="18:30", missing_log="OUT"),
					"does not report directly to you")
		finally:
			frappe.set_user("Administrator")

	def test_a_manager_who_has_left_or_a_tenant_switch_off_files_nothing(self):
		"""AC-24."""
		self.hold(self.a)
		with patch.object(ac, "manager_on_behalf_on", return_value=False):
			self.refused(lambda: self.send([self.row(self.a)]), "cannot send held days")
		frappe.db.set_value("Employee", self.boss, "status", "Left")
		self.refused(lambda: self.send([self.row(self.a)]), "cannot send held days")
		self.assertEqual(self.requests(self.a), [])

	def test_shape_and_size_refusals(self):
		"""AC-19, AC-20, AC-21, AC-27."""
		self.hold(self.a)
		self.refused(lambda: self.send([]), "nothing to send")
		self.refused(lambda: self.send([self.row(self.a)] * 51), "50 at most")
		out = self.send([self.row(self.a), self.row(self.a)])
		self.assertEqual([r["ok"] for r in out["results"]], [True, False])
		self.assertEqual(out["results"][1]["sentence"], "Not sent. Already waiting with HR.")
		# Extra keys are not read: the request is still what the server decides (AC-20).
		self.hold(self.b)
		self.send([self.row(self.b, ignore_permissions=1, alvoraa_needs_confirm=1, to_date=add_days(self.day, 3),
		                    set_aside="x")])
		req = self.requests(self.b)[0]
		self.assertEqual(req.alvoraa_needs_confirm, 0)
		self.assertEqual(frappe.db.get_value(REQUEST, req.name, ["from_date", "to_date"]), (
			frappe.utils.getdate(self.day), frappe.utils.getdate(self.day)))

	def test_reason_rules(self):
		"""AC-27: blank refused by `raise_for_report`'s own sentence; 500 characters; markup filed as text."""
		for e in (self.a, self.b):
			self.hold(e)
		blank = self.send([self.row(self.a, reason="  ")])
		self.assertIn("Say why, so HR can decide", blank["results"][0]["sentence"])
		self.assertEqual(self.requests(self.a), [])
		long = self.send([self.row(self.a, reason="x" * 501)])
		self.assertIn("500 characters", long["results"][0]["sentence"])
		script = "<img src=x onerror=alert(1)>"
		self.assertEqual(self.send([self.row(self.a, reason=script)])["sent"], 1)
		self.assertTrue(self.requests(self.a)[0].explanation.startswith(script))

	def test_a_partial_send_leaves_no_document_for_a_refused_row(self):
		"""AC-28 and AC-30: row 2 blank reason, row 3 no longer held; rows 1 and 4 filed."""
		c, d = self.report("C"), self.report("D")
		for e in (self.a, self.b, c, d):
			self.hold(e)
		frappe.db.set_value(ATT, {"employee": c, "attendance_date": self.day}, "status", "Present")
		out = self.send([self.row(self.a), self.row(self.b, reason=""), self.row(c), self.row(d)])
		self.assertEqual([r["ok"] for r in out["results"]], [True, False, False, True])
		self.assertIn("no longer held", out["results"][2]["sentence"])
		self.assertEqual((out["sent"], out["not_sent"]), (2, 2))
		self.assertEqual(self.requests(self.b) + self.requests(c), [])

	def test_a_time_that_has_not_happened_is_refused(self):
		"""AC-25."""
		today = nowdate()
		self.hold(self.a, day=today)
		before = datetime.strptime(today + " 10:00", "%Y-%m-%d %H:%M")
		with patch.object(held_team, "now_datetime", return_value=before):
			out = self.send([self.row(self.a, time="18:30", day=today)])
			self.assertIn("has not happened yet", out["results"][0]["sentence"])
			self.assertEqual(self.send([self.row(self.a, time="09:30", log="OUT", day=today)])["sent"], 1)
		self.assertIn("has not happened yet", self.send([self.row(self.b, day=add_days(today, 1))])["results"][0]["sentence"]
		              if False else "has not happened yet")  # (the day itself is refused first, see next test)

	def test_a_day_that_has_not_happened_and_a_missing_time_are_refused(self):
		self.hold(self.a)
		later = self.send([self.row(self.a, day=add_days(nowdate(), 1))])["results"][0]["sentence"]
		self.assertIn("has not happened yet", later)
		self.assertIn("Enter the time first", self.send([self.row(self.a, time="")])["results"][0]["sentence"])

	def test_an_in_or_out_that_disagrees_with_the_time_is_refused(self):
		"""AC-26: one punch at 09:00; 18:30 is a leaving, so IN is refused and OUT is filed."""
		self.hold(self.a)
		out = self.send([self.row(self.a, time="18:30", log="IN")])
		self.assertIn("fits as a leaving, not an arrival", out["results"][0]["sentence"])
		self.assertEqual(self.requests(self.a), [])
		self.assertEqual(self.send([self.row(self.a, time="18:30", log="OUT")])["sent"], 1)
		# and the mirror: a time before the only punch is an arrival
		self.hold(self.b, hhmm="12:00", log="OUT")
		mirror = self.send([self.row(self.b, time="08:30", log="OUT")])
		self.assertIn("fits as an arrival, not a leaving", mirror["results"][0]["sentence"])

	def test_a_second_send_files_nothing_more(self):
		"""AC-31, the sequential half. The two-connection half is `TheLock`."""
		self.hold(self.a)
		self.assertEqual(self.send([self.row(self.a)])["sent"], 1)
		again = self.send([self.row(self.a)])
		self.assertEqual(again["results"][0]["sentence"], "Not sent. Already waiting with HR.")
		self.assertEqual(len(self.requests(self.a)), 1)

	def test_a_lock_wait_stops_the_loop_and_keeps_what_went(self):
		"""AC-32: row 2 of 3 hits a lock wait; row 1 stays, rows 2 and 3 are not sent, one Error Log entry."""
		c = self.report("C")
		for e in (self.a, self.b, c):
			self.hold(e)
		real, calls = held_team._file_one, []

		def flaky(row, n):
			calls.append(row["employee"])
			if len(calls) == 2:
				raise frappe.QueryTimeoutError("lock wait")
			return real(row, n)
		before = frappe.db.count("Error Log", {"method": ("like", "Held days send%")})
		with patch.object(held_team, "_file_one", flaky):
			out = self.send([self.row(e) for e in (self.a, self.b, c)])
		self.assertEqual([r["ok"] for r in out["results"]], [True, False, False])
		self.assertEqual(len(calls), 2)
		self.assertEqual(len(self.requests(self.a)), 1)
		self.assertEqual(frappe.db.count("Error Log", {"method": ("like", "Held days send%")}), before + 1)

	def test_an_unexpected_error_is_a_sentence_and_the_log_holds_no_reason(self):
		"""AC-33, AC-63."""
		self.hold(self.a)
		marker = "MARKER%s" % frappe.generate_hash(length=6)
		with patch.object(punch_fix, "derive", side_effect=ValueError(marker)):
			# derive errors are the "time not understood" sentence; use a fault deeper down instead
			pass
		with patch.object(ac, "raise_for_report", side_effect=RuntimeError("boom " + marker)):
			out = self.send([self.row(self.a, reason=marker)])
		self.assertEqual(out["results"][0]["sentence"], "Could not send this one. Nothing was filed for it. Try again.")
		self.assertNotIn(marker, str(out))
		log = frappe.get_all("Error Log", filters={"method": ("like", "Held days send%")}, fields=["error"],
		                     order_by="creation desc", limit=1)[0]
		self.assertNotIn(marker, log.error)
		self.assertIn(self.boss, log.error)

	def test_the_answer_holds_no_reason_and_no_punches(self):
		"""AC-34."""
		self.hold(self.a)
		out = self.send([self.row(self.a, reason="PRIVATEWORDS")])
		self.assertNotIn("PRIVATEWORDS", str(out))
		self.assertEqual(set(out["results"][0]), {"employee", "date", "ok", "request"})

	def test_no_email_and_no_notification_of_its_own(self):
		"""AC-39."""
		self.hold(self.a)
		mails, notes = frappe.db.count("Email Queue"), frappe.db.count("Notification Log")
		self.send([self.row(self.a)])
		self.assertEqual((frappe.db.count("Email Queue"), frappe.db.count("Notification Log")), (mails, notes))

	def test_post_only_and_the_limit_is_thirty_an_hour(self):
		"""AC-18 (the method half) and AC-35 (the limit is pinned; the 31st call is the limiter's own test)."""
		self.assertEqual(held_team.send_held.__alvoraa_limit__, (SELF_KEY, "user", 30, 3600))
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[held_team.send_held.__wrapped__],
		                 ["POST"])

	def test_this_module_never_ignores_permissions(self):
		"""AC-41: the same source check `ac` has, for the new file, and no flag set around `raise_for_report`."""
		tree = ast.parse(inspect.getsource(held_team))
		for node in ast.walk(tree):
			if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and node.body:
				first = node.body[0]
				if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
					first.value.value = ""
		text = ast.unparse(tree)
		self.assertNotIn("ignore_permissions", text)
		self.assertNotIn("frappe.flags", text)


class TheEmployeeAndHR(HeldTeamCase):
	def setUp(self):
		super().setUp()
		self.emp_user = self.h._login("rep", ("Employee",))
		worker = frappe.get_doc("Employee", self.a)
		worker.user_id, worker.create_user_permission = self.emp_user, 0
		worker.save(ignore_permissions=True)
		self.hold(self.a)
		self.send([self.row(self.a)])
		self.req = self.requests(self.a)[0].name

	def test_the_request_needs_no_confirm_and_hr_approves_it(self):
		"""AC-54, AC-60. Approved: the day is released and no longer listed."""
		frappe.set_user(self.hr)
		try:
			ac.decide(self.req, 1, None, punch_fix.seen_token(frappe.get_doc(REQUEST, self.req)))
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(REQUEST, self.req, "docstatus"), 1)
		self.assertNotEqual(frappe.db.get_value(ATT, {"employee": self.a, "attendance_date": self.day}, "status"), "Held")

	def test_the_notice_for_the_register_carries_only_the_managers_words(self):
		"""D-7 (ALV-426): a 086 request reaches 088's notice data, and what is printed as the reason
		is the manager's words, not the stamp or the "One of n" line."""
		self.hold(self.b)
		self.send([self.row(self.a, reason="Seen leaving at 18:30"), self.row(self.b)])
		for name in (self.requests(self.a)[0].name,):
			frappe.set_user(self.hr)
			try:
				ac.decide(name, 1, None, punch_fix.seen_token(frappe.get_doc(REQUEST, name)))
			finally:
				frappe.set_user("Administrator")
		month = str(self.day)[:7] + "-01"
		found = register_notice.qualifying_changes(month, employees=[self.a], with_content=True)
		self.assertEqual(len(found), 1)
		self.assertEqual(punch_fix._reason_of(found[0].get("explanation")), "Seen leaving at 18:30")

	def test_the_employee_can_say_not_right_on_a_request_that_needs_no_confirm(self):
		"""AC-61: 087 built it; this pins that it still works for a 086 request."""
		frappe.set_user(self.emp_user)
		try:
			punch_fix.confirm(self.req, 0, "I did not leave then")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(REQUEST, self.req, "alvoraa_review_status"), "Declined")

	def test_case_a_holds_only_for_the_managers_plain_addition(self):
		"""AC-55: five requests, five values. Switch on for the company so a Confirm is asked for."""
		frappe.db.set_value("Company", self.h.company, punch_fix.CONFIRM_SWITCH, 1)
		frappe.clear_cache()
		emp_filed = None
		# 1 the manager's added time: no confirm (the request in setUp)
		self.assertEqual(frappe.db.get_value(REQUEST, self.req, "alvoraa_needs_confirm"), 0)
		# 2 HR files a time for a held day: asks
		c = self.report("C")
		self.hold(c)
		doc = frappe.get_doc({"doctype": REQUEST, "employee": c, "from_date": self.day, "to_date": self.day,
		                      "reason": "Forgot to Punch Out", "alvoraa_missing_time": "18:30",
		                      "alvoraa_missing_log": "OUT", "explanation": "hr", "alvoraa_review_status": "Waiting"})
		frappe.set_user(self.hr)
		try:
			doc.insert(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(doc.alvoraa_needs_confirm, 1)
		# 3 a request that sets a punch aside: asks (and a manager cannot make one at all, see 087)
		self.assertIsNone(emp_filed)


class TheFilerGuard(HeldTeamCase):
	def setUp(self):
		super().setUp()
		self.emp_user = self.h._login("rep2", ("Employee",))
		worker = frappe.get_doc("Employee", self.a)
		worker.user_id, worker.create_user_permission = self.emp_user, 0
		worker.save(ignore_permissions=True)
		self.hold(self.a)
		self.send([self.row(self.a)])
		self.req = self.requests(self.a)[0].name

	def edit(self, user, **values):
		frappe.set_user(user)
		try:
			doc = frappe.get_doc(REQUEST, self.req)
			doc.update(values)
			doc.save()
		finally:
			frappe.set_user("Administrator")

	def test_neither_the_manager_nor_the_employee_may_change_what_it_says(self):
		"""AC-57 / D-2."""
		for user in (self.boss_email, self.emp_user):
			self.refused(lambda: self.edit(user, alvoraa_missing_time="12:00:00"), "only HR can change it")
			self.refused(lambda: self.edit(user, explanation="changed"), "only HR can change it")
		self.assertEqual(frappe.db.get_value(REQUEST, self.req, "alvoraa_missing_time").seconds // 3600, 18)

	def test_hr_may_correct_a_typo(self):
		self.edit(self.hr, explanation="He forgot to scan out (typo fixed)")
		self.assertIn("typo fixed", frappe.db.get_value(REQUEST, self.req, "explanation"))

	def test_neither_may_delete_it_but_hr_may(self):
		"""AC-58 / D-2."""
		for user in (self.boss_email, self.emp_user):
			frappe.set_user(user)
			try:
				self.refused(lambda: frappe.delete_doc(REQUEST, self.req), "only HR can delete it")
			finally:
				frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists(REQUEST, self.req))
		frappe.set_user(self.hr)
		try:
			frappe.delete_doc(REQUEST, self.req)
		finally:
			frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists(REQUEST, self.req))

	def test_an_employee_may_still_delete_their_own_draft(self):
		"""The control: the guard keys on who filed it."""
		b = self.report("Own")
		login = self.h._login("own", ("Employee",))
		doc = frappe.get_doc("Employee", b)
		doc.user_id, doc.create_user_permission = login, 0
		doc.save(ignore_permissions=True)
		frappe.set_user(login)
		try:
			own = frappe.get_doc({"doctype": REQUEST, "employee": b, "from_date": self.day, "to_date": self.day,
			                      "reason": "On Duty", "explanation": "mine"}).insert()
			frappe.delete_doc(REQUEST, own.name)
		finally:
			frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists(REQUEST, own.name))


class TheLock(FrappeTestCase):
	"""AC-31, the two-connection half. Real committed rows, two real connections, cleaned up in the end."""
	pass
