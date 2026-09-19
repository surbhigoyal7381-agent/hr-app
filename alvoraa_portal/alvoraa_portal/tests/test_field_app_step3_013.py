"""Slice 013, step 3: the join. HR makes a code, the phone checks it, reads the
notice, ticks "I have read this and I understand.", and is Active.

Every test here names the thing it keeps alive:

  * **US-5** - HR makes one code per person at a time; the code is never
    stored; nobody but the server creates, changes or deletes a code record.
  * **US-8 / US-9** - a code's lifecycle: expired, used, cancelled, each with
    its own code; "this is not me" cancels it and HR is told.
  * **US-10 / US-11** - E3 is one locked save. Two joins on one code on two
    database connections: exactly one wins. A failure halfway writes nothing.
    A new phone replaces the old app phone; another person's secret on the
    same phone removes their record and HR is told.
  * **US-14** - acknowledgement rows are a history nobody rewrites.
  * **US-20** - the /enrol page reads nothing and sends nothing.
  * **US-23** - a leaver's waiting codes are cancelled.
  * **C-11c** - an HR user limited to one company sees only that company's
    codes and acknowledgements.
  * **C-3** - "I no longer agree" parks the phone; nothing is erased.

The collision test is the pin on the lock order. Take `for_update` off the
employee and code reads in field_app_join.py and it fails.
"""

import json
import secrets
import threading
import time
from typing import ClassVar
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, get_datetime, now

from alvoraa_goals.tests.utils import ensure_company
from alvoraa_portal import field_app_alerts as alerts
from alvoraa_portal import field_app_errors as errors
from alvoraa_portal import field_app_join as join
from alvoraa_portal import field_app_notice as notice
from alvoraa_portal import field_app_settings as fas
from alvoraa_portal import field_checkin as fc
from alvoraa_portal import subscription as sub
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_app_invite.alvoraa_app_invite import (
	INVITE,
	SERVER_FLAG,
)
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_notice_acknowledgement.alvoraa_notice_acknowledgement import (
	ACKNOWLEDGEMENT,
	record_acknowledgement,
)
from alvoraa_portal.tests.test_field_app_step1_013 import FieldAppCase, _bin, _new_phone
from alvoraa_portal.tests.test_field_app_step2_013 import (
	SettingsCase,
	_company_permission,
	_designation,
	_employee,
	_user,
)
from alvoraa_portal.tests.test_portal_security_010 import _second_company

DRIVER = "Zqx Driver 013"
CLERK = "Zqx Store Associate 013"
OLD_VERSION = "2026-01-01"    # a version no phone has ever been shown


def _clear_codes(employee):
	for name in frappe.get_all(ACKNOWLEDGEMENT, {"employee": employee}, pluck="name"):
		_bin(ACKNOWLEDGEMENT, name)
	for name in frappe.get_all(INVITE, {"employee": employee}, pluck="name"):
		_bin(INVITE, name)


def _code_of(answer):
	return answer["link"].split("#t=", 1)[1]


class JoinCase(FieldAppCase):
	"""The step-1 employee as a listed field worker, the app on, one HR maker."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.driver = _designation(DRIVER)
		cls.clerk = _designation(CLERK)
		cls.maker = _user("join.maker", ["HR Manager"])
		cls.hrm2 = _user("join.hrm2", ["HR Manager"])
		cls.employee_user = _user("join.emp", ["Employee"])
		cls._saved = {f: frappe.db.get_single_value(fas.SETTINGS, f, cache=False)
		              for f in (fas.F_ENABLED, fas.F_LIFETIME)}
		cls._saved_rows = fas.settings()["designations"]
		cls._saved_designation = frappe.db.get_value("Employee", cls.employee, "designation")
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		_clear_codes(cls.employee)
		for f, v in cls._saved.items():
			frappe.db.set_single_value(fas.SETTINGS, f, v, update_modified=False)
		SettingsCase._write_rows(cls._saved_rows)
		frappe.db.set_value("Employee", cls.employee, "designation", cls._saved_designation,
		                    update_modified=False)
		frappe.db.commit()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		_clear_codes(self.employee)
		self.configure(1, [self.driver], self.driver, "1 day")
		self.started = now()
		frappe.set_user("Guest")

	def configure(self, enabled, designations, employee_designation, lifetime="1 day"):
		frappe.set_user("Administrator")
		frappe.db.set_single_value(fas.SETTINGS, fas.F_ENABLED, enabled, update_modified=False)
		frappe.db.set_single_value(fas.SETTINGS, fas.F_LIFETIME, lifetime, update_modified=False)
		SettingsCase._write_rows(designations)
		frappe.db.set_value("Employee", self.employee, "designation", employee_designation,
		                    update_modified=False)
		frappe.db.commit()
		frappe.set_user("Guest")

	# ── calling the endpoints the way the app and the desk do ────────────────

	def call(self, endpoint, args):
		frappe.local.response = frappe._dict()
		frappe.clear_messages()
		frappe.local.form_dict = frappe._dict(
			args, cmd=f"alvoraa_portal.field_app_join.{endpoint.__name__}")
		out = endpoint(**args)
		# What Frappe's request handler does after a successful call. In a test
		# run the alerts are written at once, inside the open transaction; the
		# next refusal's rollback would otherwise take them away (the first run
		# lost N2 that way).
		frappe.db.commit()
		return out

	def make(self, employee=None, hours=None, user=None):
		"""E7, as the HR maker. Returns the answer; the code is in the link."""
		frappe.set_user(user or self.maker)
		try:
			args = {"employee": employee or self.employee}
			if hours is not None:
				args["lifetime_hours"] = hours
			return self.call(join.make_code, args)
		finally:
			frappe.set_user("Guest")

	def check(self, code, token=None):
		args = {"code": code}
		if token:
			args["token"] = token
		return self.call(join.check_code, args)

	def join_args(self, code, **overrides):
		args = {"code": code, "notice_version": notice.CURRENT_VERSION,
		        "device_label": "Redmi 12", "platform": "android"}
		args.update(overrides)
		return args

	def joined(self, code, **overrides):
		return self.call(join.join_with_code, self.join_args(code, **overrides))

	def invite(self, name):
		return frappe.db.get_value(
			INVITE, name,
			["name", "employee", "status", "lifetime_hours", "expires_at", "token_hash",
			 "retired_token_hash", "used_at", "used_device", "cancel_reason", "cancelled_by",
			 "cancelled_at", "owner"], as_dict=True)

	def app_phones(self, employee=None):
		return frappe.get_all(fc.DEVICE, filters={"employee": employee or self.employee,
		                                          "join_method": "App QR code"},
		                      fields=["name", "status", "token_hash", "invite"])

	def acks(self, employee=None):
		return frappe.get_all(ACKNOWLEDGEMENT, filters={"employee": employee or self.employee},
		                      fields=["name", "device", "notice_version", "channel", "language",
		                              "acknowledged_at"], order_by="creation asc")

	def notifications(self):
		return frappe.get_all("Notification Log",
		                      filters={"creation": [">=", self.started], "type": "Alert"},
		                      fields=["for_user", "subject", "email_content", "document_name"])


# ── US-5 · HR makes a code ───────────────────────────────────────────────────

class HrMakesACode(JoinCase):

	def test_013_ac38_one_waiting_code_with_the_right_fields_and_a_strong_link(self):
		before = now()
		out = self.make(hours=24)
		code = _code_of(out)
		self.assertGreaterEqual(len(code), 43)
		self.assertTrue(out["link"].startswith("http"))
		self.assertIn("/enrol#t=", out["link"])
		self.assertEqual(out["lifetime_hours"], 24)

		row = self.invite(out["invite"])
		self.assertEqual((row.status, row.employee, row.owner, row.lifetime_hours),
		                 ("Waiting", self.employee, self.maker, 24))
		self.assertEqual(row.token_hash, fc._hash(code))
		self.assertFalse(row.retired_token_hash)
		expires = get_datetime(row.expires_at)
		self.assertGreaterEqual(expires, get_datetime(add_to_date(before, hours=24, minutes=-2)))
		self.assertLessEqual(expires, get_datetime(add_to_date(now(), hours=24, minutes=2)))

	def test_013_ac39_the_code_is_nowhere_but_the_answer(self):
		out = self.make()
		code = _code_of(out)
		self.assertEqual(frappe.db.count(INVITE, {"token_hash": code}), 0)
		for doctype, field in (("Version", "data"), ("Comment", "content"),
		                       ("Notification Log", "email_content"), ("Notification Log", "subject"),
		                       ("Error Log", "error")):
			with self.subTest(doctype=doctype, field=field):
				self.assertEqual(frappe.db.count(doctype, {field: ["like", f"%{code}%"]}), 0)
		# and the row holds only the hash
		row = frappe.db.get_value(INVITE, out["invite"], "*", as_dict=True)
		self.assertNotIn(code, json.dumps(row, default=str))

	def test_013_ac40_a_lifetime_above_the_setting_or_off_the_list_is_refused(self):
		self.configure(1, [self.driver], self.driver, "1 day")
		for bad in (72, "720", "0.5", "abc", 25):
			with self.subTest(bad=bad):
				with self.assertRaises(frappe.ValidationError) as caught:
					self.make(hours=bad)
				self.assertIn("up to your organisation's setting of 1 day", str(caught.exception))
				frappe.db.rollback()
		self.assertEqual(frappe.db.count(INVITE, {"employee": self.employee}), 0)
		# the setting itself, and shorter, are fine; empty means the setting
		self.assertEqual(self.make(hours=24)["lifetime_hours"], 24)
		self.assertEqual(self.make(hours=4)["lifetime_hours"], 4)
		self.assertEqual(self.make()["lifetime_hours"], 24)

	def test_013_ac41_a_newer_code_cancels_the_waiting_one_and_retires_its_hash(self):
		first = self.make()
		second = self.make()
		old = self.invite(first["invite"])
		self.assertEqual((old.status, old.cancel_reason, old.cancelled_by),
		                 ("Cancelled", "Newer code made", self.maker))
		self.assertFalse(old.token_hash, "a cancelled code kept a live hash")
		self.assertEqual(old.retired_token_hash, fc._hash(_code_of(first)))
		self.assertTrue(old.cancelled_at)
		self.assertEqual(frappe.db.count(INVITE, {"employee": self.employee, "status": "Waiting"}), 1)
		self.assertEqual(self.invite(second["invite"]).status, "Waiting")

	def test_013_ac42_not_a_field_worker_app_off_plan_off_or_not_active_makes_no_row(self):
		cases = {
			"NOT_FIELD_ROLE": lambda: self.configure(1, [self.driver], self.clerk),
			"APP_OFF_FOR_FIELD": lambda: self.configure(0, [self.driver], self.driver),
		}
		for code, arrange in cases.items():
			with self.subTest(code=code):
				arrange()
				with self.assertRaises(errors.FieldAppRefusal) as caught:
					self.make()
				self.assertEqual(caught.exception.alvoraa_code, code)
				frappe.db.rollback()
		self.configure(1, [self.driver], self.driver)

		frappe.conf["features"] = [f for f in sub.FEATURES if f != "field_checkin"]
		with self.assertRaises(errors.FieldAppRefusal) as caught:
			self.make()
		self.assertEqual(caught.exception.alvoraa_code, "FEATURE_OFF")
		frappe.conf["features"] = list(sub.FEATURES)
		frappe.db.rollback()

		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.employee, "status", "Left", update_modified=False)
		frappe.db.commit()
		try:
			with self.assertRaises(frappe.ValidationError) as caught:
				self.make()
			self.assertIn("Only active employees can be invited", str(caught.exception))
			frappe.db.rollback()
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", self.employee, "status", "Active", update_modified=False)
			frappe.db.commit()
		self.assertEqual(frappe.db.count(INVITE, {"employee": self.employee}), 0)

	def test_013_ac43_only_hr_who_can_read_the_employee_may_make_a_code(self):
		frappe.set_user("Administrator")
		company_b = _second_company()
		company_a = ensure_company()
		emp_b = _employee("JoinBeta", company_b, designation=self.driver)
		limited = _user("join.limited", ["HR User"])
		perm = _company_permission(limited, company_a)
		try:
			for user, employee in ((limited, emp_b), (self.employee_user, self.employee),
			                       ("Guest", self.employee)):
				with self.subTest(user=user):
					with self.assertRaises(frappe.PermissionError):
						self.make(employee=employee, user=user)
					frappe.db.rollback()
			self.assertEqual(frappe.db.count(INVITE, {"employee": ["in", [emp_b, self.employee]]}), 0)
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User Permission", perm, force=True, ignore_permissions=True)
			_clear_codes(emp_b)
			frappe.db.commit()

	def test_013_ac45_nobody_but_the_server_creates_changes_or_deletes_a_code(self):
		meta = frappe.get_meta(INVITE)
		self.assertTrue(meta.permissions, "no role can even read a code record")
		for perm in meta.permissions:
			self.assertTrue(perm.get("read"))
			for action in ("create", "write", "delete", "email", "print", "share", "export", "import"):
				self.assertFalse(perm.get(action), f"{perm.role} can {action} a code record")
		self.assertEqual(frappe.db.count("Print Format", {"doc_type": INVITE}), 0)

		# and the controller, for Administrator and for a script
		frappe.set_user("Administrator")
		doc = frappe.get_doc({"doctype": INVITE, "employee": self.employee, "status": "Waiting",
		                      "lifetime_hours": 1, "expires_at": add_to_date(now(), hours=1),
		                      "token_hash": "x" * 64})
		with self.assertRaises(frappe.PermissionError):
			doc.insert(ignore_permissions=True)
		frappe.db.rollback()

		out = self.make()
		frappe.set_user("Administrator")
		doc = frappe.get_doc(INVITE, out["invite"])
		doc.status = "Used"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)
		frappe.db.rollback()
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc(INVITE, out["invite"], force=True, ignore_permissions=True)
		frappe.db.rollback()
		self.assertEqual(self.invite(out["invite"]).status, "Waiting")

	def test_013_the_waiting_count_on_the_settings_tab_is_real(self):
		self.assertEqual(fas._waiting_codes(),
		                 frappe.db.count(INVITE, {"status": "Waiting", "expires_at": [">", now()]}))
		before = fas._waiting_codes()
		self.make()
		self.assertEqual(fas._waiting_codes(), before + 1)


# ── US-8 · the app checks a code without using it ────────────────────────────

class ThePhoneChecksACode(JoinCase):

	def test_013_ac53_the_answer_is_the_least_and_the_code_is_still_waiting(self):
		out = self.make()
		code = _code_of(out)
		for _ in range(2):
			answer = self.check(code)
		self.assertEqual(sorted(answer), sorted(["first_name", "surname_initial", "designation",
		                                         "company", "brand_colour", "notice", "min_version"]))
		self.assertEqual(answer["first_name"], "Zqxthirteen")
		self.assertEqual(answer["designation"], self.driver)
		self.assertEqual(answer["notice"]["version"], notice.CURRENT_VERSION)
		self.assertEqual(answer["notice"]["agree"], "I have read this and I understand.")
		self.assertEqual(len(answer["notice"]["rows"]), 6)
		body = json.dumps(answer, default=str)
		for leak in (self.employee, "employee_name", "@example.com", "date_of_birth", "cell_number"):
			self.assertNotIn(leak, body)
		self.assertEqual(self.invite(out["invite"]).status, "Waiting")

	def test_013_ac54_dead_codes_get_their_own_code_and_no_name(self):
		expired = self.make()
		frappe.set_user("Administrator")
		frappe.db.set_value(INVITE, expired["invite"], "expires_at",
		                    add_to_date(now(), seconds=-1), update_modified=False)
		frappe.db.commit()
		frappe.set_user("Guest")
		self.check(_code_of(expired))
		status, code, values = self.answer()
		self.assertEqual((status, code), (410, "QR_EXPIRED"))
		self.assertIn("expired_at", values)

		used = self.make()
		self.joined(_code_of(used))
		self.check(_code_of(used))
		status, code, values = self.answer()
		self.assertEqual((status, code), (410, "QR_USED"))
		self.assertTrue(values.get("used_at"))

		cancelled = self.make()
		self.make()    # cancels the one above
		self.check(_code_of(cancelled))
		self.assertEqual(self.answer(), (410, "QR_CANCELLED", {}))

		self.check(secrets.token_urlsafe(32))
		self.assertEqual(self.answer(), (404, "QR_NOT_RECOGNISED", {}))
		self.check("short")
		self.assertEqual(self.answer()[:2], (404, "QR_NOT_RECOGNISED"))

		for dead in (expired, used, cancelled):
			self.check(_code_of(dead))
			body = json.dumps(dict(frappe.local.response), default=str) + self.words()
			for leak in ("Zqxthirteen", "Redmi", self.employee):
				self.assertNotIn(leak, body, "a dead code's answer named somebody")

	def test_013_ac55_an_ineligible_code_names_nobody(self):
		out = self.make()
		code = _code_of(out)
		self.configure(1, [self.driver], self.clerk)
		self.check(code)
		self.assertEqual(self.answer(), (403, "NOT_FIELD_ROLE", {"designation": self.clerk}))
		self.configure(0, [self.driver], self.driver)
		self.check(code)
		self.assertEqual(self.answer(), (403, "APP_OFF_FOR_FIELD", {}))
		body = json.dumps(dict(frappe.local.response), default=str)
		for leak in ("first_name", "Zqxthirteen", self.employee):
			self.assertNotIn(leak, body)
		self.assertEqual(self.invite(out["invite"]).status, "Waiting")

	def test_013_ac56_no_last_name_means_an_empty_initial(self):
		self.assertFalse(frappe.db.get_value("Employee", self.employee, "last_name"))
		self.assertEqual(self.check(_code_of(self.make()))["surname_initial"], "")

	def test_013_ac58_a_code_past_its_time_is_expired_before_the_job_runs(self):
		out = self.make()
		frappe.set_user("Administrator")
		frappe.db.set_value(INVITE, out["invite"], "expires_at", add_to_date(now(), seconds=-1),
		                    update_modified=False)
		frappe.db.commit()
		frappe.set_user("Guest")
		self.check(_code_of(out))
		self.assertEqual(self.answer()[:2], (410, "QR_EXPIRED"))
		self.joined(_code_of(out))
		self.assertEqual(self.answer()[:2], (410, "QR_EXPIRED"))
		self.assertEqual(self.app_phones(), [])

	def test_013_ac60_a_waiting_code_for_a_leaver_is_cancelled_at_the_check(self):
		out = self.make()
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.employee, "status", "Left", update_modified=False)
		frappe.db.commit()
		frappe.set_user("Guest")
		try:
			self.check(_code_of(out))
			self.assertEqual(self.answer()[:2], (410, "QR_CANCELLED"))
			row = self.invite(out["invite"])
			self.assertEqual((row.status, row.cancel_reason), ("Cancelled", "Employee left"))
			self.assertFalse(row.token_hash)
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", self.employee, "status", "Active", update_modified=False)
			frappe.db.commit()


# ── US-9 · this is not me ────────────────────────────────────────────────────

class ThisIsNotMe(JoinCase):

	def test_013_ac61_the_code_is_cancelled_and_hr_is_told(self):
		out = self.make()
		self.assertEqual(self.call(join.refuse_code, {"code": _code_of(out)}), {})
		row = self.invite(out["invite"])
		self.assertEqual((row.status, row.cancel_reason, row.cancelled_by),
		                 ("Cancelled", "This is not me (on a phone)", None))
		self.assertTrue(row.cancelled_at)
		self.assertFalse(row.token_hash)
		self.check(_code_of(out))
		self.assertEqual(self.answer()[:2], (410, "QR_CANCELLED"))

		sent = [n for n in self.notifications() if n.document_name == out["invite"]]
		self.assertIn(self.maker, {n.for_user for n in sent})
		self.assertTrue(any("refused on a phone" in n.subject for n in sent))

	def test_013_ac62_a_dead_code_changes_nothing_and_sends_nothing(self):
		out = self.make()
		self.joined(_code_of(out))
		before = self.invite(out["invite"])
		count = len(self.notifications())
		self.call(join.refuse_code, {"code": _code_of(out)})
		self.assertEqual(self.answer()[:2], (410, "QR_USED"))
		self.assertEqual(self.invite(out["invite"]), before)
		self.assertEqual(len(self.notifications()), count)
		self.call(join.refuse_code, {"code": secrets.token_urlsafe(32)})
		self.assertEqual(self.answer()[:2], (404, "QR_NOT_RECOGNISED"))


# ── US-10 · agree and finish ─────────────────────────────────────────────────

class AgreeAndFinish(JoinCase):

	def test_013_ac64_one_save_makes_the_phone_uses_the_code_and_records_the_reading(self):
		out = self.make()
		answer = self.joined(_code_of(out))
		self.assertTrue(answer and answer.get("token"), self.words())
		self.assertGreaterEqual(len(answer["token"]), 43)
		self.assertEqual(sorted(answer), sorted(["token", "status", "first_name", "company",
		                                         "workplace", "todays_checkins"]))
		self.assertEqual(answer["status"], "active")
		self.assertEqual(answer["first_name"], "Zqxthirteen")
		self.assertEqual(answer["todays_checkins"], [])
		if answer["workplace"]:
			self.assertEqual(sorted(answer["workplace"]), ["name", "radius_m"])

		phones = self.app_phones()
		self.assertEqual(len(phones), 1)
		phone = frappe.get_doc(fc.DEVICE, phones[0].name)
		self.assertEqual((phone.status, phone.join_method, phone.invite, phone.device_label,
		                  phone.platform, phone.activated_by),
		                 ("Active", "App QR code", out["invite"], "Redmi 12", "android", self.maker))
		self.assertEqual(phone.token_hash, fc._hash(answer["token"]))
		self.assertFalse(phone.consent_given_on, "new code wrote the old consent field")

		row = self.invite(out["invite"])
		self.assertEqual((row.status, row.used_device), ("Used", phone.name))
		self.assertTrue(row.used_at)
		self.assertFalse(row.token_hash)
		self.assertEqual(row.retired_token_hash, fc._hash(_code_of(out)))

		acks = self.acks()
		self.assertEqual(len(acks), 1)
		self.assertEqual((acks[0].device, acks[0].notice_version, acks[0].channel, acks[0].language),
		                 (phone.name, notice.CURRENT_VERSION, "App", "en"))

		# the phone works at once - no Pending, no HR click
		out2 = self.call(fc.field_status, {"token": answer["token"]})
		self.assertEqual((out2 or {}).get("employee"), self.employee, self.words())

	def test_013_ac65_two_joins_on_one_code_exactly_one_wins(self):
		"""Two database connections, one code. The second caller queues on the
		employee row, re-reads the code after the lock and is told it is used.
		Without the locks both proceed and this fails."""
		out = self.make()
		code = _code_of(out)
		frappe.db.commit()
		results = _two_at_once(join.join_with_code, self.join_args(code),
		                       join.join_with_code, self.join_args(code, device_label="Other"))
		wins = [r for r in results if r.get("out") and r["out"].get("token")]
		losses = [r for r in results if not (r.get("out") and r["out"].get("token"))]
		self.assertEqual(len(wins), 1, results)
		self.assertEqual(len(losses), 1, results)
		self.assertEqual((losses[0]["response"].get("http_status_code"),
		                  losses[0]["response"].get("code")), (410, "QR_USED"), results)
		self.assertEqual(len(self.app_phones()), 1)
		self.assertEqual(self.invite(out["invite"]).status, "Used")

	def test_013_ac66_a_failure_halfway_writes_nothing(self):
		out = self.make()
		with mock.patch.object(join, "record_acknowledgement", side_effect=RuntimeError("boom")):
			self.joined(_code_of(out))
		self.assertEqual(self.answer()[:2], (500, "SERVER_ERROR"))
		self.assertEqual(self.app_phones(), [])
		self.assertEqual(self.acks(), [])
		row = self.invite(out["invite"])
		self.assertEqual(row.status, "Waiting")
		self.assertEqual(row.token_hash, fc._hash(_code_of(out)))
		# and the code still works afterwards
		self.assertTrue(self.joined(_code_of(out)).get("token"), self.words())

	def test_013_ac67_a_stale_notice_version_is_refused_with_the_new_rows(self):
		out = self.make()
		self.joined(_code_of(out), notice_version=OLD_VERSION)
		status, code, values = self.answer()
		self.assertEqual((status, code), (409, "NOTICE_CHANGED"))
		self.assertEqual(values["version"], notice.CURRENT_VERSION)
		self.assertEqual(len(values["rows"]), 6)
		self.assertIn("retention_days", values)
		self.assertEqual(self.app_phones(), [])
		self.assertEqual(self.invite(out["invite"]).status, "Waiting")

	def test_013_ac68_anything_that_changed_since_the_check_refuses_and_writes_nothing(self):
		out = self.make()
		code = _code_of(out)
		self.check(code)

		self.configure(0, [self.driver], self.driver)
		self.joined(code)
		self.assertEqual(self.answer()[1], "APP_OFF_FOR_FIELD")

		self.configure(1, [self.driver], self.clerk)
		self.joined(code)
		self.assertEqual(self.answer()[1], "NOT_FIELD_ROLE")
		self.configure(1, [self.driver], self.driver)

		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.employee, "status", "Left", update_modified=False)
		frappe.db.commit()
		frappe.set_user("Guest")
		try:
			self.joined(code)
			self.assertEqual(self.answer()[:2], (403, "EMPLOYEE_NOT_ACTIVE"))
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", self.employee, "status", "Active", update_modified=False)
			frappe.db.commit()
			frappe.set_user("Guest")

		self.assertEqual(self.app_phones(), [])
		self.assertEqual(self.invite(out["invite"]).status, "Waiting")

	def test_013_ac69_extra_fields_are_not_stored(self):
		out = self.make()
		frappe.local.form_dict = frappe._dict(cmd="alvoraa_portal.field_app_join.join_with_code")
		answer = frappe.call(join.join_with_code, imei="IMEI-CANARY-1", android_id="ANDROID-CANARY",
		                     serial="SERIAL-CANARY", **self.join_args(_code_of(out)))
		self.assertTrue(answer.get("token"), self.words())
		phone = frappe.db.get_value(fc.DEVICE, self.app_phones()[0].name, "*", as_dict=True)
		ack = frappe.db.get_value(ACKNOWLEDGEMENT, self.acks()[0].name, "*", as_dict=True)
		for canary in ("IMEI-CANARY-1", "ANDROID-CANARY", "SERIAL-CANARY"):
			self.assertNotIn(canary, json.dumps(phone, default=str))
			self.assertNotIn(canary, json.dumps(ack, default=str))
			self.assertEqual(frappe.db.count("Version", {"data": ["like", f"%{canary}%"]}), 0)
			self.assertEqual(frappe.db.count("Error Log", {"error": ["like", f"%{canary}%"]}), 0)

	def test_013_ac70_a_join_and_a_new_code_at_the_same_moment_do_not_deadlock(self):
		out = self.make()
		frappe.db.commit()
		results = _two_at_once(join.join_with_code, self.join_args(_code_of(out)),
		                       join.make_code, {"employee": self.employee}, second_user=self.maker)
		for r in results:
			self.assertNotIn("exc", r, results)
			self.assertLess(r["response"].get("http_status_code") or 200, 500, results)
		self.assertLessEqual(frappe.db.count(INVITE, {"employee": self.employee, "status": "Waiting"}), 1)
		self.assertLessEqual(frappe.db.count(fc.DEVICE, {"employee": self.employee, "status": "Active",
		                                                 "join_method": "App QR code"}), 1)

	def test_013_not_now_links_the_phone_without_agreeing_and_e9_finishes_it(self):
		"""The user's 2026-09-17 decision: "Not now" still uses the code; the
		phone is parked, cannot punch, and agreeing later needs no new code."""
		out = self.make()
		answer = self.joined(_code_of(out), agreed=0, notice_version=None)
		self.assertEqual(answer.get("status"), "not_agreed", self.words())
		phone = self.app_phones()[0]
		self.assertEqual(phone.status, "Consent not given")
		self.assertEqual(self.acks(), [], "a refusal was recorded as a reading")
		self.assertEqual(self.invite(out["invite"]).status, "Used")

		self.call(fc.field_checkin, self.punch_args(answer["token"]))
		self.assertEqual(self.answer()[:2], (403, "CONSENT_REQUIRED"))

		self.assertEqual(self.call(join.acknowledge_notice,
		                           {"token": answer["token"], "notice_version": notice.CURRENT_VERSION}), {})
		self.assertEqual(frappe.db.get_value(fc.DEVICE, phone.name, "status"), "Active")
		self.assertEqual(len(self.acks()), 1)
		self.assertEqual(frappe.db.get_value(fc.DEVICE, phone.name, "status_change_source"),
		                 "The employee")


# ── US-11 · one working app phone per person ─────────────────────────────────

class OneAppPhonePerPerson(JoinCase):

	def test_013_ac72_a_new_phone_replaces_the_old_app_phone_in_the_same_save(self):
		a = self.joined(_code_of(self.make()))
		phone_a = self.app_phones()[0].name
		b = self.joined(_code_of(self.make()))
		phones = {p.name: p for p in self.app_phones()}
		self.assertEqual(len(phones), 2)
		old = frappe.get_doc(fc.DEVICE, phone_a)
		new = next(p for p in phones.values() if p.name != phone_a)
		self.assertEqual((old.status, old.replaced_by, old.status_change_source),
		                 ("Replaced", new.name, "System"))
		self.assertTrue(old.status_changed_on)
		self.assertFalse(old.token_hash)
		self.assertEqual(old.retired_token_hash, fc._hash(a["token"]))
		self.assertEqual(new.status, "Active")

		self.call(fc.field_status, {"token": a["token"]})
		status, code, values = self.answer()
		self.assertEqual((status, code), (403, "DEVICE_REPLACED"))
		self.assertTrue(values.get("replaced_at"))
		self.assertEqual((self.call(fc.field_status, {"token": b["token"]}) or {}).get("employee"),
		                 self.employee)

	def test_013_ac73_a_web_page_phone_is_not_replaced(self):
		web, web_token = _new_phone(self.employee, "Active")
		frappe.db.commit()
		self.joined(_code_of(self.make()))
		self.assertEqual(frappe.db.get_value(fc.DEVICE, web.name, "status"), "Active")
		self.assertEqual((self.call(fc.field_status, {"token": web_token}) or {}).get("employee"),
		                 self.employee)

	def test_013_ac74_another_persons_secret_on_the_phone_removes_their_record_and_tells_hr(self):
		frappe.set_user("Administrator")
		other = _employee("JoinOther", ensure_company(), designation=self.driver)
		frappe.db.commit()
		frappe.set_user("Guest")
		try:
			theirs = self.joined(_code_of(self.make(employee=other)))
			their_phone = self.app_phones(other)[0].name
			mine = self.joined(_code_of(self.make()), token=theirs["token"])
			self.assertTrue(mine.get("token"), self.words())

			old = frappe.get_doc(fc.DEVICE, their_phone)
			self.assertEqual((old.status, old.status_change_source), ("Removed", "System"))
			self.assertFalse(old.token_hash)
			self.assertEqual(self.app_phones()[0].status, "Active")

			sent = [n for n in self.notifications() if "two employees" in n.subject]
			self.assertTrue(sent, "the one-phone-two-people alert was not queued")
			self.assertIn(self.hrm2, {n.for_user for n in sent})
			for n in sent:
				for leak in (theirs["token"], mine["token"], fc._hash(theirs["token"])):
					self.assertNotIn(leak, n.subject + n.email_content)
		finally:
			frappe.set_user("Administrator")
			for p in frappe.get_all(fc.DEVICE, {"employee": other}, pluck="name"):
				_bin(fc.DEVICE, p)
			_clear_codes(other)
			frappe.db.commit()

	def test_013_ac75_my_own_secret_again_is_a_replacement_with_no_alert(self):
		first = self.joined(_code_of(self.make()))
		count = len([n for n in self.notifications() if "two employees" in n.subject])
		second = self.joined(_code_of(self.make()), token=first["token"])
		self.assertTrue(second.get("token"), self.words())
		statuses = sorted(p.status for p in self.app_phones())
		self.assertEqual(statuses, ["Active", "Replaced"])
		self.assertEqual(len([n for n in self.notifications() if "two employees" in n.subject]), count)


# ── US-14 · the notice, and who read which version ───────────────────────────

class WhoReadWhichWords(JoinCase):

	def test_013_ac94_a_new_reading_is_a_new_row_and_a_stale_one_is_refused(self):
		answer = self.joined(_code_of(self.make()))
		phone = self.app_phones()[0].name
		frappe.set_user("Administrator")
		old_row = record_acknowledgement(self.employee, OLD_VERSION, "App", device=phone)
		frappe.db.commit()
		frappe.set_user("Guest")

		self.call(join.acknowledge_notice, {"token": answer["token"], "notice_version": OLD_VERSION})
		self.assertEqual(self.answer()[:2], (409, "NOTICE_CHANGED"))

		self.assertEqual(self.call(join.acknowledge_notice,
		                           {"token": answer["token"], "notice_version": notice.CURRENT_VERSION}), {})
		rows = self.acks()
		self.assertEqual([r.notice_version for r in rows],
		                 [notice.CURRENT_VERSION, OLD_VERSION, notice.CURRENT_VERSION])
		self.assertEqual(frappe.db.get_value(ACKNOWLEDGEMENT, old_row.name, "notice_version"),
		                 OLD_VERSION, "the old row was rewritten")
		# reading the same version twice in a row does not pile up rows
		self.call(join.acknowledge_notice, {"token": answer["token"], "notice_version": notice.CURRENT_VERSION})
		self.assertEqual(len(self.acks()), 3)

	def test_013_ac95_the_web_page_registration_writes_one_row(self):
		before = len(self.acks())
		out = self.call(fc.register_device, {"employee_id": self.employee, "device_label": "web",
		                                     "platform": "web", "consent": 1,
		                                     "consent_version": fc.CONSENT_VERSION})
		self.assertTrue(out.get("token"))
		rows = self.acks()
		self.assertEqual(len(rows), before + 1)
		self.assertEqual((rows[-1].channel, rows[-1].notice_version),
		                 ("Web check-in page", fc.CONSENT_VERSION))

	def test_013_ac98_hr_reads_acknowledgements_and_never_writes_or_deletes_one(self):
		self.joined(_code_of(self.make()))
		name = self.acks()[0].name
		meta = frappe.get_meta(ACKNOWLEDGEMENT)
		for perm in meta.permissions:
			self.assertTrue(perm.get("read"))
			for action in ("create", "write", "delete", "email", "print", "share", "export"):
				self.assertFalse(perm.get(action), f"{perm.role} can {action} an acknowledgement")

		# The maker has no company of their own, so C-11c (step 2) shows them
		# nothing; for this check they are limited to the employee's company.
		company = frappe.db.get_value("Employee", self.employee, "company")
		perm = _company_permission(self.maker, company)
		try:
			frappe.set_user(self.maker)
			self.assertTrue(frappe.has_permission(ACKNOWLEDGEMENT, "read", doc=name))
			self.assertFalse(frappe.has_permission(ACKNOWLEDGEMENT, "write", doc=name))
			self.assertFalse(frappe.has_permission(ACKNOWLEDGEMENT, "delete", doc=name))
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User Permission", perm, force=True, ignore_permissions=True)
			frappe.clear_cache(user=self.maker)
			frappe.db.commit()

		# and the controller, for Administrator and for a script
		frappe.set_user("Administrator")
		doc = frappe.get_doc(ACKNOWLEDGEMENT, name)
		doc.notice_version = OLD_VERSION
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)
		frappe.db.rollback()
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc(ACKNOWLEDGEMENT, name, force=True, ignore_permissions=True)
		frappe.db.rollback()
		doc = frappe.get_doc({"doctype": ACKNOWLEDGEMENT, "employee": self.employee,
		                      "notice_version": OLD_VERSION, "acknowledged_at": now(),
		                      "language": "en", "channel": "App"})
		with self.assertRaises(frappe.PermissionError):
			doc.insert(ignore_permissions=True)
		frappe.db.rollback()
		self.assertEqual(frappe.db.get_value(ACKNOWLEDGEMENT, name, "notice_version"),
		                 notice.CURRENT_VERSION)


# ── C-3 · "I no longer agree" ────────────────────────────────────────────────

class WithdrawingAgreement(JoinCase):

	def test_013_c3_withdrawing_parks_the_phone_refuses_punches_and_erases_nothing(self):
		answer = self.joined(_code_of(self.make()))
		phone = self.app_phones()[0].name
		self.assertEqual((self.call(fc.field_checkin, self.punch_args(answer["token"])) or {}).get("status"),
		                 "ok", self.words())
		punches = self.checkin_count()
		acks = len(self.acks())
		hash_before = frappe.db.get_value(fc.DEVICE, phone, "token_hash")

		self.assertEqual(self.call(join.withdraw_agreement, {"token": answer["token"]}), {})
		row = frappe.db.get_value(fc.DEVICE, phone, ["status", "status_change_source", "token_hash",
		                                             "status_changed_on"], as_dict=True)
		self.assertEqual((row.status, row.status_change_source), ("Consent not given", "The employee"))
		self.assertEqual(row.token_hash, hash_before, "the secret was retired; the phone must keep it")
		self.assertTrue(row.status_changed_on)

		self.call(fc.field_checkin, self.punch_args(answer["token"], log_type="OUT"))
		self.assertEqual(self.answer()[:2], (403, "CONSENT_REQUIRED"))
		self.call(fc.field_status, {"token": answer["token"]})
		self.assertEqual(self.answer()[:2], (403, "CONSENT_REQUIRED"))

		# nothing erased
		self.assertEqual(self.checkin_count(), punches)
		self.assertEqual(len(self.acks()), acks)
		self.assertTrue(frappe.db.exists(fc.DEVICE, phone))

		# withdrawing twice is harmless; agreeing again restores the phone with no new code
		self.assertEqual(self.call(join.withdraw_agreement, {"token": answer["token"]}), {})
		self.assertEqual(self.call(join.acknowledge_notice,
		                           {"token": answer["token"], "notice_version": notice.CURRENT_VERSION}), {})
		self.assertEqual(frappe.db.get_value(fc.DEVICE, phone, "status"), "Active")
		self.assertEqual((self.call(fc.field_checkin, self.punch_args(answer["token"], log_type="OUT")) or {}).get("status"),
		                 "ok", self.words())

	def test_013_the_notice_endpoints_refuse_a_stopped_phone_like_everything_else(self):
		answer = self.joined(_code_of(self.make()))
		phone = frappe.get_doc(fc.DEVICE, self.app_phones()[0].name)
		frappe.set_user("Administrator")
		phone.status = "Blocked"
		phone.block_reason = "Phone lost or stolen"
		phone.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.set_user("Guest")
		for endpoint, args in ((join.acknowledge_notice, {"token": answer["token"],
		                                                   "notice_version": notice.CURRENT_VERSION}),
		                       (join.withdraw_agreement, {"token": answer["token"]})):
			with self.subTest(endpoint=endpoint.__name__):
				self.call(endpoint, args)
				self.assertEqual(self.answer(), (403, "DEVICE_BLOCKED", {}))


# ── US-19 · HR is told ───────────────────────────────────────────────────────

class HrIsTold(JoinCase):

	def test_013_ac116_the_maker_is_told_when_the_code_is_used(self):
		out = self.make()
		answer = self.joined(_code_of(out))
		sent = [n for n in self.notifications() if n.document_name == out["invite"]
		        and "joined the Alvoraa app" in n.subject]
		self.assertEqual({n.for_user for n in sent}, {self.maker})
		body = sent[0].subject + sent[0].email_content
		self.assertIn("Redmi 12", body)
		for leak in (_code_of(out), answer["token"], fc._hash(_code_of(out)), fc._hash(answer["token"])):
			self.assertNotIn(leak, body)

	def test_013_ac117_this_is_not_me_reaches_hr_who_can_read_the_employee_and_nobody_else(self):
		frappe.set_user("Administrator")
		far = _user("join.hrm.far", ["HR Manager"])
		perm = _company_permission(far, _second_company())
		frappe.db.commit()
		frappe.set_user("Guest")
		try:
			out = self.make()
			self.call(join.refuse_code, {"code": _code_of(out)})
			sent = {n.for_user for n in self.notifications()
			        if n.document_name == out["invite"] and "refused on a phone" in n.subject}
			self.assertIn(self.maker, sent)
			self.assertIn(self.hrm2, sent)
			self.assertNotIn(far, sent, "an HR Manager limited to another company was told")
			self.assertNotIn(self.employee_user, sent)
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User Permission", perm, force=True, ignore_permissions=True)
			frappe.db.commit()

	def test_013_ac118_a_used_code_scanned_from_another_phone_alerts_once_an_hour(self):
		out = self.make()
		answer = self.joined(_code_of(out))
		subject_part = "was scanned again"

		# the phone that used it, scanning again: no alert
		self.check(_code_of(out), token=answer["token"])
		self.assertEqual([n for n in self.notifications() if subject_part in n.subject], [])

		self.check(_code_of(out))
		sent = [n for n in self.notifications() if subject_part in n.subject]
		self.assertLessEqual({self.maker, self.hrm2}, {n.for_user for n in sent})
		self.check(_code_of(out))
		self.assertEqual(len([n for n in self.notifications() if subject_part in n.subject]), len(sent))

	def test_013_ac122_a_failed_alert_does_not_undo_the_join(self):
		out = self.make()
		with mock.patch("frappe.enqueue", side_effect=RuntimeError("redis down")):
			answer = self.joined(_code_of(out))
		self.assertTrue(answer.get("token"), self.words())
		self.assertEqual(self.invite(out["invite"]).status, "Used")
		self.assertEqual(len(self.app_phones()), 1)


# ── US-23 · a leaver's waiting code stops ────────────────────────────────────

class ALeaversCodeStops(JoinCase):

	def test_013_ac135_leaving_cancels_the_waiting_code_before_the_phones(self):
		out = self.make()
		phone, _t = _new_phone(self.employee, "Active")
		frappe.db.commit()
		frappe.set_user("Administrator")
		emp = frappe.get_doc("Employee", self.employee)
		emp.status = "Left"
		emp.relieving_date = now()
		emp.save(ignore_permissions=True)
		frappe.db.commit()
		try:
			row = self.invite(out["invite"])
			self.assertEqual((row.status, row.cancel_reason, row.cancelled_by),
			                 ("Cancelled", "Employee left", None))
			self.assertFalse(row.token_hash)
			self.assertEqual(frappe.db.get_value(fc.DEVICE, phone.name, "status"), "Blocked")
			# and the code answers as cancelled ever after, including after a rehire
			emp = frappe.get_doc("Employee", self.employee)
			emp.status = "Active"
			emp.relieving_date = None
			emp.save(ignore_permissions=True)
			frappe.db.commit()
			frappe.set_user("Guest")
			self.check(_code_of(out))
			self.assertEqual(self.answer()[:2], (410, "QR_CANCELLED"))
		finally:
			frappe.set_user("Administrator")
			emp = frappe.get_doc("Employee", self.employee)
			if emp.status != "Active":
				emp.status = "Active"
				emp.relieving_date = None
				emp.save(ignore_permissions=True)
			frappe.db.commit()


# ── rate limits keyed on the hash ────────────────────────────────────────────

class _FakeRequest:
	method = "POST"
	host = "test_site"
	scheme = "http"
	url = "http://test_site/api/method/x"
	headers: ClassVar[dict] = {}


class TheLimitsAreKeyedOnTheHash(JoinCase):
	"""Frappe's limiter only runs when there is a request. A fake one is enough
	for it to count, and to show what it writes into Redis."""

	PREFIX = "rl:alvoraa_portal.field_app_join"

	def setUp(self):
		super().setUp()
		frappe.cache.delete_keys(self.PREFIX)
		frappe.local.request = _FakeRequest()
		frappe.local.request_ip = "127.0.0.1"

	def tearDown(self):
		frappe.local.request = None
		frappe.cache.delete_keys(self.PREFIX)
		super().tearDown()

	def test_013_ac59_the_21st_check_in_an_hour_is_too_many_and_redis_holds_only_the_hash(self):
		out = self.make()
		code = _code_of(out)
		for _ in range(20):
			self.check(code)
			self.assertEqual(self.answer()[0], None, self.words())
		self.check(code)
		status, got, values = self.answer()
		self.assertEqual((status, got), (429, "TOO_MANY_TRIES"))
		self.assertIn("retry_after_s", values or {})

		keys = [k.decode() if isinstance(k, bytes) else str(k)
		        for k in frappe.cache.get_keys(self.PREFIX)]
		self.assertTrue(keys, "no rate-limit key was written")
		for key in keys:
			self.assertNotIn(code, key, "the code itself was written into a Redis key")
		self.assertTrue(any(fc._hash(code) in k for k in keys))
		self.assertNotIn(join.CODE_KEY, frappe.form_dict)

	def test_013_ac63_the_6th_this_is_not_me_and_the_6th_join_in_an_hour_are_too_many(self):
		for endpoint, args in ((join.refuse_code, {"code": secrets.token_urlsafe(32)}),
		                       (join.join_with_code, self.join_args(secrets.token_urlsafe(32)))):
			with self.subTest(endpoint=endpoint.__name__):
				for _ in range(5):
					self.call(endpoint, dict(args))
					self.assertEqual(self.answer()[1], "QR_NOT_RECOGNISED")
				self.call(endpoint, dict(args))
				self.assertEqual(self.answer()[:2], (429, "TOO_MANY_TRIES"))

	def test_013_ac44_the_31st_code_by_one_hr_user_in_an_hour_is_too_many(self):
		for _ in range(30):
			self.make()
		with self.assertRaises(errors.FieldAppRefusal) as caught:
			self.make()
		self.assertEqual(caught.exception.alvoraa_code, "TOO_MANY_TRIES")
		self.assertGreater(caught.exception.alvoraa_values.get("retry_after_s", 0), 0)
		frappe.db.rollback()
		keys = [k.decode() if isinstance(k, bytes) else str(k)
		        for k in frappe.cache.get_keys(self.PREFIX)]
		for key in keys:
			self.assertNotIn(self.maker, key, "an HR user's email was written into a Redis key")


# ── C-11c · who may see a code or an acknowledgement ─────────────────────────

class AnHrUserSeesOnlyTheirCompanysCodes(FrappeTestCase):
	"""The same two-company arrangement step 2 pinned for the phone record."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.company_b = _second_company()
		cls.company_a = ensure_company()
		cls.emp_a = _employee("CodeAlpha", cls.company_a)
		cls.emp_b = _employee("CodeBeta", cls.company_b)
		cls.hr_user = _user("codes.hru", ["HR User"])
		cls.hr_manager = _user("codes.hrm", ["HR Manager"])
		cls.sysman = _user("codes.sm", ["System Manager"])
		cls.perms = [_company_permission(cls.hr_user, cls.company_b),
		             _company_permission(cls.hr_manager, cls.company_b)]
		cls.rows = {}
		for emp in (cls.emp_a, cls.emp_b):
			inv = frappe.get_doc({"doctype": INVITE, "employee": emp, "status": "Waiting",
			                      "lifetime_hours": 1, "expires_at": add_to_date(now(), hours=1),
			                      "token_hash": fc._hash(secrets.token_urlsafe(32))})
			inv.flags[SERVER_FLAG] = True
			inv.insert(ignore_permissions=True)
			ack = record_acknowledgement(emp, notice.CURRENT_VERSION, "App")
			cls.rows[emp] = {INVITE: inv.name, ACKNOWLEDGEMENT: ack.name}
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for emp in (cls.emp_a, cls.emp_b):
			_clear_codes(emp)
		for up in cls.perms:
			frappe.delete_doc("User Permission", up, force=True, ignore_permissions=True)
		frappe.db.commit()
		super().tearDownClass()

	def tearDown(self):
		frappe.set_user("Administrator")

	def listed_by(self, user, doctype):
		frappe.set_user(user)
		names = [self.rows[self.emp_a][doctype], self.rows[self.emp_b][doctype]]
		return set(frappe.get_list(doctype, pluck="name", filters={"name": ["in", names]}))

	def test_013_ac149_a_company_limited_hr_user_sees_one_companys_codes_and_readings(self):
		for doctype in (INVITE, ACKNOWLEDGEMENT):
			for user in (self.hr_user, self.hr_manager):
				with self.subTest(doctype=doctype, user=user):
					self.assertEqual(self.listed_by(user, doctype), {self.rows[self.emp_b][doctype]})
					a = frappe.get_doc(doctype, self.rows[self.emp_a][doctype])
					b = frappe.get_doc(doctype, self.rows[self.emp_b][doctype])
					self.assertFalse(frappe.has_permission(doctype, "read", doc=a, user=user))
					self.assertTrue(frappe.has_permission(doctype, "read", doc=b, user=user))
					frappe.set_user(user)
					with self.assertRaises(frappe.PermissionError):
						frappe.get_doc(doctype, a.name).check_permission("read")

	def test_013_a_system_manager_sees_every_company(self):
		for doctype in (INVITE, ACKNOWLEDGEMENT):
			self.assertEqual(self.listed_by(self.sysman, doctype),
			                 {self.rows[self.emp_a][doctype], self.rows[self.emp_b][doctype]})

	def test_013_the_four_hooks_are_registered(self):
		for doctype, fn in ((INVITE, "invite"), (ACKNOWLEDGEMENT, "acknowledgement")):
			self.assertIn(f"alvoraa_portal.field_app_access.{fn}_query_conditions",
			              frappe.get_hooks("permission_query_conditions").get(doctype, []))
			self.assertIn(f"alvoraa_portal.field_app_access.{fn}_has_permission",
			              frappe.get_hooks("has_permission").get(doctype, []))

	def test_013_both_doctypes_are_classified_as_tenant_side(self):
		self.assertIn(INVITE, sub.TENANT_DOCTYPES)
		self.assertIn(ACKNOWLEDGEMENT, sub.TENANT_DOCTYPES)


# ── US-20 · the /enrol page ──────────────────────────────────────────────────

class TheEnrolPageUsesNothing(FrappeTestCase):

	def page(self):
		import os

		import alvoraa_portal
		path = os.path.join(os.path.dirname(alvoraa_portal.__file__), "www", "enrol.html")
		with open(path, encoding="utf-8") as f:
			return f.read()

	def test_013_ac123_the_words_the_noindex_and_the_fragment_removal(self):
		page = self.page()
		self.assertIn("Open the Alvoraa app to use this code", page)
		self.assertIn("This code sets up the Alvoraa attendance app.", page)
		self.assertIn('name="robots" content="noindex', page)
		self.assertIn("history.replaceState", page)
		self.assertIn("window.location.pathname", page)
		self.assertNotIn("location.hash", page)

	def test_013_ac125_nothing_is_loaded_from_any_other_host(self):
		import re
		page = self.page()
		self.assertEqual(re.findall(r"https?://", page), [])
		self.assertEqual(re.findall(r"<(script|link|img)[^>]*\s(src|href)=", page), [])

	def test_013_ac124_the_page_reads_no_code_record_and_sets_the_header(self):
		from alvoraa_portal.www import enrol
		frappe.local.response_headers = frappe._dict()
		with mock.patch.object(frappe.db, "sql", side_effect=AssertionError("the page read the database")):
			context = enrol.get_context(frappe._dict())
		self.assertEqual(frappe.local.response_headers.get("X-Robots-Tag"), "noindex, nofollow")
		self.assertTrue(context.get("tenant_name"))
		self.assertNotIn("Alvoraa App Invite", open(enrol.__file__, encoding="utf-8").read())


# ── the endpoints are wired like the punch ───────────────────────────────────

class TheEndpointsAreWiredLikeThePunch(FrappeTestCase):

	GUEST = ("check_code", "refuse_code", "join_with_code", "acknowledge_notice", "withdraw_agreement")

	def test_013_guest_endpoints_are_post_only_private_and_plan_gated(self):
		for name in (*self.GUEST, "make_code"):
			fn = getattr(join, name)
			with self.subTest(name=name):
				self.assertIn(fn, frappe.whitelisted)
				self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func.get(fn), ["POST"])
				chain, f = [], fn
				while f is not None:
					chain.append(f)
					f = getattr(f, "__wrapped__", None)
				self.assertTrue(any(getattr(x, "__alvoraa_feature__", None) == "field_checkin"
				                    for x in chain), f"{name} is not behind the plan gate")
				if name in self.GUEST:
					self.assertIn(fn, frappe.guest_methods)
					self.assertTrue(any(hasattr(x, "__alvoraa_private_request__") for x in chain),
					                f"{name} is not wrapped by _private_request")
				else:
					self.assertNotIn(fn, frappe.guest_methods)

	def test_013_the_codes_table_did_not_move(self):
		for code in ("QR_NOT_RECOGNISED", "QR_EXPIRED", "QR_USED", "QR_CANCELLED", "NOTICE_CHANGED",
		             "CONSENT_REQUIRED", "EMPLOYEE_NOT_ACTIVE"):
			self.assertIn(code, errors.CODES)
		self.assertEqual(errors.CODES["QR_USED"], (410, ("used_at",)))
		self.assertEqual(errors.CODES["NOTICE_CHANGED"],
		                 (409, ("version", "rows", "retention_days", "what_changed")))


# ── two callers at once ──────────────────────────────────────────────────────

def _two_at_once(fn1, args1, fn2, args2, second_user="Guest"):
	"""Run two endpoint calls on two database connections, the first holding
	its locks for a second so the second really has to wait on them.

	Each thread gets its own `frappe.local`, so its own connection and its own
	transaction - exactly what two phones hitting two workers get. The pause is
	put into `refuse_unless_eligible`, which both E3 and E7 reach only AFTER
	the employee row is locked.
	"""
	site = frappe.local.site
	results = []
	original = fas.refuse_unless_eligible
	first_started = threading.Event()

	def slow(designation):
		first_started.set()
		time.sleep(1.2)
		return original(designation)

	def run(fn, args, user):
		frappe.init(site=site)
		frappe.connect()
		try:
			frappe.set_user(user)
			frappe.conf["features"] = list(sub.FEATURES)
			frappe.local.response = frappe._dict()
			frappe.clear_messages()
			frappe.local.form_dict = frappe._dict(args, cmd=f"alvoraa_portal.field_app_join.{fn.__name__}")
			try:
				out = fn(**args)
				results.append({"out": out, "response": dict(frappe.local.response)})
			except Exception as e:
				results.append({"exc": repr(e), "response": dict(frappe.local.response)})
			frappe.db.commit()
		finally:
			frappe.destroy()

	with mock.patch.object(fas, "refuse_unless_eligible", side_effect=slow):
		t1 = threading.Thread(target=run, args=(fn1, args1, "Guest"))
		t2 = threading.Thread(target=run, args=(fn2, args2, second_user))
		t1.start()
		first_started.wait(10)
		time.sleep(0.2)
		t2.start()
		t1.join(60)
		t2.join(60)
	return results
