"""Slice 086, test stage: the cases the build's own suite did not name.

Each test is named after the acceptance criterion or SEC/PRIV item it proves. Fixtures are the build suite's
(`HeldTeamCase`); nothing here is committed to the database, so each test rolls back on its own.
"""

import os
import threading
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.utils import add_days

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal import held_day, held_team, punch_fix
from alvoraa_portal.tests import test_held_day_085 as hd
from alvoraa_portal.tests.test_held_team_086 import (
	ATT, CHECKIN, NOT_YOURS, REQUEST, HeldTeamCase)


def setUpModule():
	hd.setUpModule()
	punch_fix.after_migrate()
	frappe.clear_cache()


class ProofCase(HeldTeamCase):

	# SEC-1 / US-8: who may call at all -------------------------------------------------------------
	def test_a_colleague_a_stranger_and_a_guest_get_nothing_from_either_call(self):
		"""A colleague (Employee record, no team), a login with no Employee record, and a Guest."""
		self.hold(self.a)
		colleague_login = self.h._login("coll", ("Employee",))
		self.h._employee("Coll", colleague_login)
		stranger_login = self.h._login("nobody", ("Employee",))
		fake = [self.row(self.a)]
		out = self.send(fake, user=colleague_login)
		self.assertEqual(out["results"][0]["sentence"], NOT_YOURS)
		self.assertEqual(self.requests(self.a), [])
		self.refused(lambda: self.send(fake, user=stranger_login), "cannot send held days")
		self.refused(lambda: self.send(fake, user="Guest"), "cannot send held days")
		for who in (colleague_login, stranger_login, "Guest"):
			self.assertEqual(self.listed(user=who)["rows"], [], who)
			self.assertTrue(self.listed(user=who)["nobody"], who)

	# AC-19: the edge of the cap -------------------------------------------------------------------
	def test_fifty_rows_are_answered_one_by_one_and_fifty_one_file_nothing(self):
		self.hold(self.a)
		fifty = [self.row("HR-EMP-9%04d" % i) for i in range(50)]
		out = self.send(fifty)
		self.assertEqual((len(out["results"]), out["sent"], out["not_sent"]), (50, 0, 50))
		real_first = [self.row(self.a)] + [self.row("HR-EMP-9%04d" % i) for i in range(50)]
		self.refused(lambda: self.send(real_first), "50 at most")
		self.assertEqual(self.requests(self.a), [])      # the real first row was not filed: all or nothing

	# SEC-4 / AC-35: the limiter counts only on a real request, so give it one ----------------------
	def test_the_thirty_first_send_in_an_hour_is_refused(self):
		fake = [self.row("HR-EMP-90000")]
		request = SimpleNamespace(method="POST")
		key = "held086.proof.%s" % frappe.generate_hash(length=8)
		frappe.set_user(self.boss_email)
		frappe.local.request = request
		frappe.form_dict.cmd = key                      # the limiter's counter is named after the call
		try:
			for _ in range(30):
				held_team.send_held(rows=fake)
			with self.assertRaises(frappe.ValidationError) as cm:
				held_team.send_held(rows=fake)
		finally:
			frappe.local.request = None
			frappe.form_dict.pop("cmd", None)
			frappe.set_user("Administrator")
			for k in frappe.cache.get_keys("rl:%s" % key):
				frappe.cache.delete_value(k)
		self.assertIn("Too many", str(cm.exception))

	# AC-2: a cancelled request frees the day -------------------------------------------------------
	def test_a_cancelled_request_brings_the_day_back(self):
		self.hold(self.a)
		self.send([self.row(self.a)])
		self.assertEqual(self.listed()["rows"], [])
		name = self.requests(self.a)[0].name
		frappe.db.set_value(REQUEST, name, "docstatus", 2)
		self.assertEqual([r["employee"] for r in self.listed()["rows"]], [self.a])

	# AC-8, AC-9 ---------------------------------------------------------------------------------
	def test_a_left_manager_sees_no_list_and_the_hold_switch_shows_in_the_answer(self):
		self.hold(self.a)
		self.assertTrue(self.listed()["hold_on"])
		frappe.db.set_value("Company", self.h.company, held_day.SWITCH, 0)
		frappe.clear_cache()
		self.assertFalse(self.listed()["hold_on"])
		frappe.db.set_value("Employee", self.boss, "status", "Left")
		self.assertEqual(self.listed()["rows"], [])

	# AC-10 ---------------------------------------------------------------------------------------
	def test_the_list_writes_nothing_to_the_cache(self):
		self.hold(self.a)
		self.listed()
		before = set(frappe.cache.get_keys("*"))
		self.listed()
		self.listed(day="all")
		self.assertEqual(set(frappe.cache.get_keys("*")) - before, set())

	# AC-56: no login, or a disabled login, is filed like everyone else ----------------------------
	def test_a_report_with_no_login_or_a_disabled_login_is_filed_like_everyone(self):
		off = self.h._login("off", ("Employee",))
		frappe.db.set_value("User", off, "enabled", 0)
		frappe.db.set_value("Employee", self.b, "user_id", off)
		self.assertFalse(frappe.db.get_value("Employee", self.a, "user_id"))
		for e in (self.a, self.b):
			self.hold(e)
		out = self.send([self.row(self.a), self.row(self.b)])
		self.assertEqual((out["sent"], out["not_sent"]), (2, 0), out)

	# AC-37 / SEC-8: from the request alone ---------------------------------------------------------
	def test_the_request_alone_says_who_filed_for_whom_in_which_batch_and_who_decided(self):
		self.hold(self.a)
		self.hold(self.b)
		self.send([self.row(self.a, reason="Saw him go at 18:30"), self.row(self.b)])
		name = self.requests(self.a)[0].name
		frappe.set_user(self.hr)
		try:
			ac.decide(name, 1, "Seen", punch_fix.seen_token(frappe.get_doc(REQUEST, name)))
		finally:
			frappe.set_user("Administrator")
		doc = frappe.get_doc(REQUEST, name)
		boss_name = frappe.db.get_value("Employee", self.boss, "employee_name")
		self.assertEqual(doc.owner, self.boss_email)                       # who filed
		self.assertTrue(doc.creation)                                      # and when
		self.assertIn("(%s), their reporting manager" % self.boss, doc.explanation)   # as whose manager
		self.assertIn(boss_name, doc.explanation)
		self.assertIn("One of 2 days sent together.", doc.explanation)     # in which batch
		self.assertEqual((doc.alvoraa_missing_log, doc.alvoraa_missing_time.seconds), ("OUT", 18 * 3600 + 30 * 60))
		self.assertTrue(doc.alvoraa_reviewed_by and doc.alvoraa_reviewed_on and doc.alvoraa_review_note == "Seen")

	# AC-63 / PRIV-2: a marker in the reason is stored in the request and nowhere else -------------
	def test_a_marker_in_the_reason_appears_only_in_the_request(self):
		marker = "MARKER" + frappe.generate_hash(length=10)
		self.hold(self.a)
		self.hold(self.b)
		real = ac.raise_for_report

		def second_blows_up(*args, **kwargs):
			if kwargs.get("employee") == self.b:
				raise RuntimeError("boom " + kwargs.get("explanation", ""))
			return real(*args, **kwargs)
		with patch.object(ac, "raise_for_report", second_blows_up):
			out = self.send([self.row(self.a, reason=marker), self.row(self.b, reason=marker)])
		self.assertEqual((out["sent"], out["not_sent"]), (1, 1))
		self.assertNotIn(marker, str(out))
		self.assertEqual(len(frappe.get_all(REQUEST, filters={"explanation": ("like", "%" + marker + "%")})), 1)
		for dt, field in (("Error Log", "error"), ("Error Log", "method"), ("Email Queue", "message"),
		                  ("Notification Log", "subject"), ("Notification Log", "email_content"),
		                  ("Comment", "content"), ("Activity Log", "subject")):
			self.assertEqual(frappe.db.count(dt, {field: ("like", "%" + marker + "%")}), 0, (dt, field))
		logs = {frappe.get_site_path("logs"), os.path.join(frappe.utils.get_bench_path(), "logs")}
		for folder in logs:
			if not os.path.isdir(folder):
				continue
			for fname in os.listdir(folder):
				path = os.path.join(folder, fname)
				if fname.endswith(".log") and os.path.isfile(path):
					with open(path, errors="ignore") as fh:
						self.assertNotIn(marker, fh.read(), path)



class TheDayLock(HeldTeamCase):
	"""OPS-56 / M-6, the part the build's own suite could not prove (its notes: "the day lock has no test of
	its own"). While a send has filed a day and not yet committed, a second connection that wants to write
	that day's Attendance row must wait. Without the locking read on the day, it would not."""

	def setUp(self):
		super().setUp()
		self.hold(self.a)
		frappe.db.commit()
		self.addCleanup(self.remove_what_was_committed)

	def remove_what_was_committed(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		people = [self.a, self.b, self.boss]
		for dt in (REQUEST, CHECKIN, ATT):
			frappe.db.delete(dt, {"employee": ("in", people)})
		frappe.db.delete("User Permission", {"for_value": ("in", people)})
		frappe.db.delete("Employee", {"name": ("in", people)})
		frappe.db.commit()

	def test_a_second_connection_waits_for_a_day_the_send_has_filed_but_not_committed(self):
		site, path = frappe.local.site, frappe.local.sites_path
		boss_email, row = self.boss_email, self.row(self.a)
		att_name = frappe.db.get_value(ATT, {"employee": self.a, "attendance_date": self.day}, "name")
		filed, release, done = threading.Event(), threading.Event(), threading.Event()
		seen, real = {}, ac.raise_for_report

		def pausing(*args, **kwargs):
			result = real(*args, **kwargs)
			filed.set()                              # filed; every lock still held; not committed
			release.wait(30)
			return result

		def connect():
			frappe.init(site=site, sites_path=path)
			frappe.connect()

		def sender():
			try:
				connect()
				frappe.set_user(boss_email)
				seen["send"] = held_team.send_held(rows=[row])
				frappe.db.commit()
			except Exception as e:
				seen["send"] = repr(e)
				frappe.db.rollback()
			finally:
				frappe.destroy()

		def writer():
			try:
				connect()
				frappe.set_user("Administrator")
				frappe.db.sql("update `tabAttendance` set modified = modified where name = %s", att_name)
				seen["wrote_after_release"] = release.is_set()
				frappe.db.commit()
			except Exception as e:
				seen["write"] = repr(e)
				frappe.db.rollback()
			finally:
				done.set()
				frappe.destroy()

		with patch.object(ac, "raise_for_report", pausing):
			one = threading.Thread(target=sender)
			one.start()
			self.assertTrue(filed.wait(60), "the send never filed")
			two = threading.Thread(target=writer)
			two.start()
			self.assertFalse(done.wait(3), "the second connection was not made to wait for the locked day")
			release.set()
			one.join(60)
			two.join(60)
		frappe.db.rollback()
		self.assertEqual(seen["send"]["sent"], 1, seen)
		self.assertTrue(seen.get("wrote_after_release"), seen)
