"""ALV-128: signing in to the field app with a work email and password.

The user's decisions (25 Sep 2026), each pinned by a test below so a bad merge
that drops one fails CI:

  * **Anyone with a login.** An active employee whose record names a login
    signs in with its email and password - no designation list, no code from
    HR. The phone then uses the same token endpoints as a code-joined phone:
    the punch with photo and GPS, the 50 m rule, the notice.
  * **Frappe checks the password.** Wrong password and unknown email get one
    answer (no staff directory). Frappe's lockout applies. Two-factor sign-in,
    when on, asks for the one-time code, and a wrong code is refused.
  * **The password lands nowhere.** Not in form_dict after the request, not in
    the Error Log, not in the answer, not in Redis - not even beside the
    two-factor one-time id, where Frappe's own website keeps it.
  * **HR keeps both doors.** Two switches on HR Settings, one per way in; at
    least one stays on. Turning a way off stops NEW joins that way only;
    phones that already joined keep working (the user's decision, 26 Sep
    2026). The designation list still binds code phones only.
  * **A phone stops when its login does.** Disabling the User, changing its
    password (SEC-26) or unlinking it from the employee record (SEC-28) blocks
    the phones it signed in - through a hook and, where a hook can be skipped,
    on the phone's next call.
  * **One app phone per person.** A new sign-in replaces the old phone,
    whichever way the old one joined, and emails the person (SEC-27).

Review fixes, 26 Sep 2026: the two-factor second step takes its user from a
site-prefixed marker only (P1 - Frappe's own keys are shared by every tenant on
the bench); the per-account limit counts the login Frappe finds (SEC-29); a
sign-in writes an Activity Log row (SEC-31); Frappe's per-network lock is not
called an account lock.

**Fail-without-fix recipes:** make `_refuse_sign_in_failed` say something
different for an unknown email and `test_128_an_unknown_email_and_a_wrong_password_get_one_answer`
fails. Put the real password back into `form_dict["pwd"]` in
`_start_second_step` and `test_128_two_factor_...` fails on the cached value,
which must be the empty string. Take `JOIN_PASSWORD` out of `APP_JOIN_METHODS`
and `test_128_a_new_sign_in_replaces_the_old_phone` fails: the first password
phone is no longer replaced, so the person has two live app phones.
"""

import json
from unittest import mock

import pyotp

import frappe
from frappe.utils import now
from frappe.utils.password import update_password

from alvoraa_goals.tests.utils import ensure_company, ensure_gender
from alvoraa_portal import field_app_desk as desk
from alvoraa_portal import field_app_errors as errors
from alvoraa_portal import field_app_join as join
from alvoraa_portal import field_app_limits as limits
from alvoraa_portal import field_app_notice as notice
from alvoraa_portal import field_app_settings as fas
from alvoraa_portal import field_checkin as fc
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_field_device.alvoraa_field_device import (
	APP_JOIN_METHODS,
	JOIN_PASSWORD,
	JOIN_QR,
)
from alvoraa_portal.tests.test_field_app_step1_013 import _company
from alvoraa_portal.tests.test_field_app_step3_013 import _code_of, _FakeRequest
from alvoraa_portal.tests.test_field_app_step4_013 import JPEG_1PX, DailyCase
from alvoraa_portal.tests.test_field_app_step6_013 import _clear_counters, _keys, _limit_of

PW_EMAIL = "zqx.pw128@example.com"
OTHER_EMAIL = "zqx.pw128.nobody@example.com"          # has a login, no employee record
UNKNOWN_EMAIL = "zqx.pw128.unknown@example.com"       # no login at all
PASSWORD = "Zqx-Pw128-Right!horse"
WRONG = "Zqx-Pw128-Wrong!horse"
FIRST_NAME = "Zqxpwone"
ROLE_2FA = "Zqx Two Factor 128"
IP = "203.0.113.128"
OTHER_IPS = ("203.0.113.1", "203.0.113.2", "203.0.113.3", "203.0.113.4")   # test addresses only

_SYSTEM_FIELDS = ("allow_consecutive_login_attempts", "allow_login_after_fail",
                  "enable_two_factor_auth", "two_factor_method", "disable_user_pass_login")


class _Request(_FakeRequest):
	path = "/api/method/alvoraa_portal.field_app_join.sign_in_with_password"
	referrer = None


def _login(email, roles=("Employee",)):
	"""A login with a known password, enabled."""
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": FIRST_NAME,
		                "send_welcome_email": 0,
		                "roles": [{"role": r} for r in roles]}).insert(ignore_permissions=True)
	frappe.db.set_value("User", email, "enabled", 1, update_modified=False)
	update_password(email, PASSWORD)
	return email


def _forget_trackers(*keys):
	for key in keys:
		frappe.cache.hdel("login_failed_count", key)
		frappe.cache.hdel("login_failed_time", key)


class PasswordCase(DailyCase):
	"""The step-4 fixture, with its own employee whose record names a login."""

	@classmethod
	def _employee(cls):
		_login(PW_EMAIL)
		existing = frappe.db.get_value("Employee", {"user_id": PW_EMAIL})
		if existing:
			frappe.db.set_value("Employee", existing, "status", "Active", update_modified=False)
			return existing
		# A bare site has no company and no gender; make them rather than hope
		# another module ran first (the 24 Sep CI lesson, ALV-126).
		return frappe.get_doc({
			"doctype": "Employee", "first_name": FIRST_NAME, "company": _company() or ensure_company(),
			"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
			"gender": ensure_gender(),
			"status": "Active", "user_id": PW_EMAIL, "create_user_permission": 0,
		}).insert(ignore_permissions=True).name

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		_login(OTHER_EMAIL)
		cls._saved_routes = {f: frappe.db.get_single_value(fas.SETTINGS, f, cache=False)
		                     for f in (fas.F_CODE_JOIN, fas.F_PASSWORD)}
		cls._saved_system = {f: frappe.db.get_single_value("System Settings", f)
		                     for f in _SYSTEM_FIELDS}
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for f, v in cls._saved_routes.items():
			frappe.db.set_single_value(fas.SETTINGS, f, v, update_modified=False)
		for f, v in cls._saved_system.items():
			frappe.db.set_single_value("System Settings", f, v, update_modified=False)
		frappe.db.set_value("User", PW_EMAIL, "enabled", 1, update_modified=False)
		frappe.db.set_value("Employee", cls.employee, "user_id", PW_EMAIL, update_modified=False)
		frappe.db.commit()
		frappe.clear_cache()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.routes(code=1, password=1)
		frappe.db.set_single_value("System Settings", "allow_consecutive_login_attempts", 0,
		                           update_modified=False)
		frappe.db.set_single_value("System Settings", "enable_two_factor_auth", 0,
		                           update_modified=False)
		frappe.db.set_single_value("System Settings", "disable_user_pass_login", 0,
		                           update_modified=False)
		_login(PW_EMAIL)
		frappe.db.set_value("Employee", self.employee, {"status": "Active", "user_id": PW_EMAIL},
		                    update_modified=False)
		frappe.db.commit()
		frappe.clear_cache()
		_clear_counters()
		_forget_trackers(PW_EMAIL, OTHER_EMAIL, UNKNOWN_EMAIL, IP, *OTHER_IPS)
		self.with_request()
		self.started = now()
		frappe.set_user("Guest")

	def tearDown(self):
		frappe.local.request = None
		frappe.set_user("Administrator")
		_clear_counters()
		_forget_trackers(PW_EMAIL, OTHER_EMAIL, UNKNOWN_EMAIL, IP, *OTHER_IPS)
		frappe.local.request_ip = IP
		super().tearDown()

	# ── helpers ──────────────────────────────────────────────────────────────

	def with_request(self):
		req = _Request()
		req.headers = {}
		frappe.local.request = req
		frappe.local.request_ip = IP

	def routes(self, code=1, password=1):
		user = frappe.session.user
		frappe.set_user("Administrator")
		frappe.db.set_single_value(fas.SETTINGS, fas.F_CODE_JOIN, code, update_modified=False)
		frappe.db.set_single_value(fas.SETTINGS, fas.F_PASSWORD, password, update_modified=False)
		frappe.db.commit()
		frappe.set_user(user)

	def sign_in(self, email=PW_EMAIL, password=PASSWORD, **overrides):
		args = {"email": email, "password": password, "device_label": "Redmi 12",
		        "platform": "android", "agreed": 0}
		args.update(overrides)
		return self.call(join.sign_in_with_password, args)

	def signed_in(self, **overrides):
		"""Sign in and agree, as the app does: sign in, then acknowledge the notice."""
		out = self.sign_in(**overrides)
		self.assertIn("token", out or {}, f"{self.answer()} {self.words()}")
		self.call(join.acknowledge_notice, {"token": out["token"],
		                                    "notice_version": notice.CURRENT_VERSION})
		self.assertEqual(self.phone_of(out["token"]).status, "Active", self.words())
		return out["token"]

	def confirm(self, tmp_id, otp, **overrides):
		args = {"tmp_id": tmp_id, "otp": otp, "device_label": "Redmi 12", "platform": "android",
		        "agreed": 1, "notice_version": notice.CURRENT_VERSION}
		args.update(overrides)
		return self.call(join.confirm_sign_in_code, args)

	def phones(self):
		return frappe.get_all(fc.DEVICE, filters={"employee": self.employee},
		                      fields=["name", "status", "join_method", "replaced_by",
		                              "activated_by", "block_reason"],
		                      order_by="creation asc")

	def set_designation(self, designation):
		frappe.db.set_value("Employee", self.employee, "designation", designation,
		                    update_modified=False)
		frappe.db.commit()


# ── the good path: sign in, agree, punch ─────────────────────────────────────

class SigningIn(PasswordCase):

	def test_128_a_good_sign_in_sets_up_a_password_phone_that_punches_with_photo_and_gps(self):
		out = self.sign_in()
		self.assertIsNotNone(out, self.words())
		self.assertEqual(out["status"], "not_agreed")
		self.assertEqual(out["first_name"], FIRST_NAME)
		self.assertGreaterEqual(len(out["token"]), 43)
		# The app shows the notice from this answer, with no second call.
		self.assertEqual(out["notice"]["version"], notice.CURRENT_VERSION)
		self.assertTrue(out["notice"]["rows"])

		phone = self.phone_of(out["token"])
		self.assertEqual(phone.status, "Consent not given")
		self.assertEqual(phone.join_method, JOIN_PASSWORD)
		self.assertEqual(frappe.db.get_value(fc.DEVICE, phone.name, "activated_by"), PW_EMAIL)
		# Not agreed yet: no punch.
		self.assertIsNone(self.punch(out["token"]))
		self.assertEqual(self.answer()[1], "CONSENT_REQUIRED")

		self.call(join.acknowledge_notice, {"token": out["token"],
		                                    "notice_version": notice.CURRENT_VERSION})
		self.assertEqual(self.phone_of(out["token"]).status, "Active")

		status = self.status(out["token"])
		self.assertIsNotNone(status, self.words())
		self.assertFalse(status["checked_in"])
		self.assertNotIn("work_location", status, "an app phone never gets the workplace position")

		# The 50 m rule is the same for a password phone.
		self.assertIsNone(self.punch(out["token"], accuracy="80"))
		self.assertEqual(self.answer()[1], "GPS_NOT_EXACT")
		self.assertIsNone(self.punch(out["token"], accuracy=None))
		self.assertEqual(self.answer()[1], "LOCATION_MISSING")

		done = self.punch(out["token"], accuracy="20", photo=JPEG_1PX)
		self.assertIsNotNone(done, self.words())
		self.assertEqual(done["status"], "ok")
		row = self.rows()[-1]
		self.assertEqual(row.alvoraa_field_device, phone.name)
		self.assertEqual(row.device_id, "alvoraa-field-app")
		self.assertTrue(row.alvoraa_checkin_photo)

	def test_128_agreeing_in_the_same_call_makes_the_phone_active_at_once(self):
		out = self.sign_in(agreed=1, notice_version=notice.CURRENT_VERSION)
		self.assertEqual(out["status"], "active")
		self.assertEqual(self.phone_of(out["token"]).status, "Active")
		self.assertIsNotNone(self.status(out["token"]), self.words())

	def test_128_agreeing_to_an_old_notice_is_refused(self):
		self.assertIsNone(self.sign_in(agreed=1, notice_version="1999-01-01"))
		self.assertEqual(self.answer()[:2], (409, "NOTICE_CHANGED"))
		self.assertEqual(self.phones(), [])

	def test_128_no_web_session_is_made(self):
		before = frappe.db.sql("select count(*) from tabSessions where user=%s", PW_EMAIL)[0][0]
		self.assertIsNotNone(self.sign_in(), self.words())
		after = frappe.db.sql("select count(*) from tabSessions where user=%s", PW_EMAIL)[0][0]
		self.assertEqual(before, after)
		self.assertEqual(frappe.session.user, "Guest")

	def test_128_a_new_sign_in_replaces_the_old_phone(self):
		first = self.signed_in()
		second = self.signed_in()
		old = self.phone_of(first)
		self.assertEqual(old.status, "Replaced")
		self.assertEqual(frappe.db.get_value(fc.DEVICE, old.name, "replaced_by"),
		                 self.phone_of(second).name)
		self.assertIsNone(self.status(first))
		self.assertEqual(self.answer()[1], "DEVICE_REPLACED")
		self.assertIsNotNone(self.status(second), self.words())
		live = [p for p in self.phones() if p.status in ("Active", "Consent not given")]
		self.assertEqual(len(live), 1)

	def emails_about(self, phone_name):
		return frappe.get_all("Email Queue", filters={"reference_doctype": fc.DEVICE,
		                                              "reference_name": phone_name},
		                      fields=["name", "message"])

	def test_128_sec27_a_sign_in_that_replaces_a_phone_emails_the_person(self):
		first = self.signed_in()
		first_phone = self.phone_of(first).name
		self.assertEqual(self.emails_about(first_phone), [], "no email for a first-ever phone")
		second = self.signed_in()
		phone = self.phone_of(second).name
		mails = self.emails_about(phone)
		self.assertEqual(len(mails), 1)
		recipients = frappe.get_all("Email Queue Recipient", filters={"parent": mails[0].name},
		                            pluck="recipient")
		self.assertEqual(recipients, [PW_EMAIL])
		# The queued message is MIME, wrapped at 76 characters; unwrap it to read.
		body = mails[0].message.replace("=\r\n", "")
		self.assertIn("Subject: A new phone signed in to the Alvoraa app as you", body)
		self.assertIn("If this was not you, tell HR and change your password", body)
		# ...and it is on the new phone's timeline.
		notes = frappe.get_all("Comment", filters={"reference_doctype": fc.DEVICE,
		                                           "reference_name": phone, "comment_type": "Info"},
		                       pluck="content")
		self.assertTrue(any(first_phone in n and "emailed" in n for n in notes), notes)

	def test_128_sec27_no_outgoing_email_account_never_fails_the_sign_in(self):
		"""Round-two P2: a tenant with no outgoing Email Account makes sendmail
		raise at once. The sign-in must still succeed."""
		from frappe.email.doctype.email_account.email_account import EmailAccount

		first = self.signed_in()

		def no_account(*args, **kwargs):
			raise frappe.OutgoingEmailError("Please setup default outgoing Email Account")

		with mock.patch.object(EmailAccount, "find_outgoing", side_effect=no_account):
			out = self.sign_in()
		self.assertIsNotNone(out, f"{self.answer()} {self.words()}")
		self.assertIn("token", out)
		self.assertNotIn("outgoing Email Account", self.words())
		phone = self.phone_of(out["token"])
		self.assertEqual(phone.status, "Consent not given")
		self.assertEqual(self.phone_of(first).status, "Replaced")
		self.assertEqual(self.emails_about(phone.name), [])
		# The timeline says the email could not be sent; the log names the phone only.
		notes = frappe.get_all("Comment", filters={"reference_doctype": fc.DEVICE,
		                                           "reference_name": phone.name}, pluck="content")
		self.assertTrue(any("could not be sent" in n for n in notes), notes)
		logs = frappe.get_all("Error Log", filters={"creation": [">=", self.started],
		                                            "method": "Field app sign-in email"},
		                      fields=["error"])
		self.assertTrue(logs)
		self.assertIn(phone.name, logs[0].error)
		self.assertNotIn(PW_EMAIL, logs[0].error)
		self.assertNotIn(PASSWORD, logs[0].error)
		# The app goes on as normal: agree, and the phone is Active.
		self.call(join.acknowledge_notice, {"token": out["token"],
		                                    "notice_version": notice.CURRENT_VERSION})
		self.assertEqual(self.phone_of(out["token"]).status, "Active")

	def test_128_sec27_the_email_goes_to_the_users_email_field(self):
		self.signed_in()
		with mock.patch.object(frappe.db, "get_value", wraps=frappe.db.get_value) as spy:
			second = self.signed_in()
		self.assertTrue(any(c.args[:3] == ("User", PW_EMAIL, "email") for c in spy.call_args_list))
		mails = self.emails_about(self.phone_of(second).name)
		self.assertEqual(len(mails), 1)

	def test_128_sec31_each_sign_in_writes_an_activity_log_row(self):
		self.signed_in(device_label="Zqx Model 128")
		rows = frappe.get_all("Activity Log",
		                      filters={"user": PW_EMAIL, "creation": [">=", self.started],
		                               "operation": "Login", "status": "Success"},
		                      fields=["subject", "ip_address"])
		self.assertEqual(len(rows), 1, rows)
		self.assertIn("Phone app sign-in", rows[0].subject)
		self.assertIn("Zqx Model 128", rows[0].subject)
		self.assertEqual(rows[0].ip_address, IP)
		self.assertEqual(frappe.session.user, "Guest", "still no session")


# ── Frappe checks the password ───────────────────────────────────────────────

class ThePasswordCheck(PasswordCase):

	def test_128_an_unknown_email_and_a_wrong_password_get_one_answer(self):
		self.assertIsNone(self.sign_in(password=WRONG))
		wrong = (self.answer(), self.words())
		self.assertIsNone(self.sign_in(email=UNKNOWN_EMAIL))
		unknown = (self.answer(), self.words())
		self.assertEqual(wrong, unknown)
		self.assertEqual(wrong[0][:2], (401, "SIGN_IN_FAILED"))
		self.assertEqual(wrong[0][2], {})
		# Frappe's own differing words never reach the phone.
		self.assertNotIn("message", frappe.local.response)
		self.assertEqual(self.phones(), [])

	def test_128_a_disabled_login_gets_the_same_answer_too(self):
		frappe.set_user("Administrator")
		frappe.db.set_value("User", PW_EMAIL, "enabled", 0, update_modified=False)
		frappe.db.commit()
		frappe.set_user("Guest")
		self.assertIsNone(self.sign_in())
		self.assertEqual(self.answer()[:2], (401, "SIGN_IN_FAILED"))

	def lockout_on(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("System Settings", "allow_consecutive_login_attempts", 2,
		                           update_modified=False)
		frappe.db.set_single_value("System Settings", "allow_login_after_fail", 120,
		                           update_modified=False)
		frappe.db.commit()
		frappe.clear_cache()
		frappe.set_user("Guest")

	def test_128_frappe_lockout_of_the_account_is_respected(self):
		self.lockout_on()
		# Three wrong tries from three networks: the ACCOUNT's lock, not a network's.
		for ip in OTHER_IPS[:3]:
			frappe.local.request_ip = ip
			self.assertIsNone(self.sign_in(password=WRONG))
		# The right password now, from a fourth network: still locked, as on the website.
		frappe.local.request_ip = OTHER_IPS[3]
		self.assertIsNone(self.sign_in())
		self.assertEqual(self.answer()[:2], (429, "ACCOUNT_LOCKED"))
		self.assertEqual(self.answer()[2], {"retry_after_s": 120})
		self.assertIn("Your account is locked", self.words())
		self.assertEqual(self.phones(), [])

	def test_128_a_locked_network_is_not_called_a_locked_account(self):
		self.lockout_on()
		# Three failures from one address, each for a different unknown email:
		# Frappe locks the address; this account never failed at all.
		for i in range(3):
			self.assertIsNone(self.sign_in(email=f"zqx.pw128.stranger{i}@example.com", password=WRONG))
		self.assertIsNone(self.sign_in())
		self.assertEqual(self.answer()[:2], (429, "NETWORK_LOCKED"))
		self.assertIn("Too many sign-in attempts from this network", self.words())
		self.assertNotIn("account", self.words().lower())

	def test_128_an_expired_password_is_sent_to_the_website(self):
		with mock.patch("frappe.auth.LoginManager.force_user_to_reset_password", return_value=True):
			self.assertIsNone(self.sign_in())
		self.assertEqual(self.answer()[:2], (403, "PASSWORD_EXPIRED"))
		self.assertEqual(self.phones(), [])

	def test_128_the_sites_own_no_password_setting_is_obeyed(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("System Settings", "disable_user_pass_login", 1,
		                           update_modified=False)
		frappe.db.commit()
		frappe.clear_cache()
		frappe.set_user("Guest")
		self.assertIsNone(self.sign_in())
		self.assertEqual(self.answer()[:2], (403, "PASSWORD_SIGNIN_OFF"))

	def test_128_a_login_with_no_employee_record_is_refused_clearly(self):
		self.assertIsNone(self.sign_in(email=OTHER_EMAIL))
		self.assertEqual(self.answer()[:2], (403, "NO_EMPLOYEE_RECORD"))
		self.assertIn("link your employee record", self.words())

	def test_128_an_employee_who_is_not_active_is_refused(self):
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.employee, "status", "Left", update_modified=False)
		frappe.db.commit()
		frappe.set_user("Guest")
		self.assertIsNone(self.sign_in())
		self.assertEqual(self.answer()[:2], (403, "EMPLOYEE_NOT_ACTIVE"))
		self.assertEqual(self.phones(), [])


# ── two-factor sign-in ───────────────────────────────────────────────────────

class TwoFactor(PasswordCase):

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		if not frappe.db.exists("Role", ROLE_2FA):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_2FA, "desk_access": 0,
			                "two_factor_auth": 1}).insert(ignore_permissions=True)
		frappe.db.set_value("Role", ROLE_2FA, "two_factor_auth", 1, update_modified=False)
		frappe.get_doc("User", PW_EMAIL).add_roles(ROLE_2FA)
		frappe.db.set_single_value("System Settings", "enable_two_factor_auth", 1,
		                           update_modified=False)
		frappe.db.set_single_value("System Settings", "two_factor_method", "Email",
		                           update_modified=False)
		frappe.db.commit()
		frappe.clear_cache()
		frappe.set_user("Guest")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.get_doc("User", PW_EMAIL).remove_roles(ROLE_2FA)
		frappe.db.commit()
		super().tearDown()

	def _code_for(self, tmp_id):
		secret = frappe.safe_decode(frappe.cache.get(tmp_id + "_otp_secret"))
		token = frappe.safe_decode(frappe.cache.get(tmp_id + "_token"))
		return pyotp.HOTP(secret).at(int(token))

	def test_128_two_factor_asks_for_the_code_and_refuses_a_wrong_one(self):
		with mock.patch("frappe.twofactor.send_token_via_email", return_value=True):
			first = self.sign_in()
		self.assertEqual(first["status"], "otp_required", self.words())
		self.assertNotIn("token", first)
		self.assertEqual(first["method"], "Email")
		tmp_id = first["tmp_id"]
		self.assertTrue(tmp_id)
		self.assertEqual(self.phones(), [], "no phone before the code")
		# Frappe's website caches the password beside the id. We hand it an empty string.
		self.assertEqual(frappe.safe_decode(frappe.cache.get(tmp_id + "_pwd")), "")
		self.assertNotIn(PASSWORD, json.dumps(frappe.local.response, default=str))

		right = self._code_for(tmp_id)
		wrong = "000000" if right != "000000" else "111111"
		self.assertIsNone(self.confirm(tmp_id, wrong))
		self.assertEqual(self.answer()[:2], (401, "OTP_WRONG"))
		self.assertEqual(self.phones(), [])

		out = self.confirm(tmp_id, right)
		self.assertIsNotNone(out, self.words())
		self.assertEqual(out["status"], "active")
		phone = self.phone_of(out["token"])
		self.assertEqual((phone.status, phone.join_method), ("Active", JOIN_PASSWORD))

		# The id works once.
		self.assertIsNone(self.confirm(tmp_id, right))
		self.assertEqual(self.answer()[:2], (410, "OTP_EXPIRED"))

	def test_128_an_unknown_one_time_id_is_told_to_sign_in_again(self):
		self.assertIsNone(self.confirm("zqxnotanid", "123456"))
		self.assertEqual(self.answer()[:2], (410, "OTP_EXPIRED"))

	def test_128_p1_an_id_frappe_wrote_without_our_marker_is_refused(self):
		"""Frappe's own keys have no site prefix. An id whose `_usr` and secret
		exist - written by another tenant, or by the website's own login - but
		that this site never marked, opens nothing."""
		tmp_id = "zqxp1raw"
		secret = pyotp.random_base32()
		frappe.cache.set(tmp_id + "_usr", PW_EMAIL, 180)
		frappe.cache.set(tmp_id + "_otp_secret", secret, 180)
		try:
			self.assertIsNone(self.confirm(tmp_id, pyotp.TOTP(secret).now()))
			self.assertEqual(self.answer()[:2], (410, "OTP_EXPIRED"))
			self.assertEqual(self.phones(), [])
		finally:
			frappe.cache.delete(tmp_id + "_usr", tmp_id + "_otp_secret")

	def test_128_p1_a_marker_written_for_another_site_is_refused(self):
		import pickle

		tmp_id = "zqxp1oth"
		secret = pyotp.random_base32()
		other = f"_zqx_other_site_db|{join._MARKER_KEY.format(tmp_id)}".encode()
		frappe.cache.set(other, pickle.dumps(PW_EMAIL), 180)
		frappe.cache.set(tmp_id + "_usr", PW_EMAIL, 180)
		frappe.cache.set(tmp_id + "_otp_secret", secret, 180)
		try:
			self.assertIsNone(self.confirm(tmp_id, pyotp.TOTP(secret).now()))
			self.assertEqual(self.answer()[:2], (410, "OTP_EXPIRED"))
			self.assertEqual(self.phones(), [])
		finally:
			frappe.cache.delete(other, tmp_id + "_usr", tmp_id + "_otp_secret")

	def test_128_p1_the_marker_is_this_sites_and_goes_with_success(self):
		with mock.patch("frappe.twofactor.send_token_via_email", return_value=True):
			tmp_id = self.sign_in()["tmp_id"]
		key = frappe.cache.make_key(join._MARKER_KEY.format(tmp_id))
		self.assertTrue(key.startswith(f"{frappe.local.conf.db_name}|".encode()))
		# Raw reads: `key` is already the full, prefixed name.
		self.assertIsNotNone(frappe.cache.get(key))
		self.assertIsNotNone(self.confirm(tmp_id, self._code_for(tmp_id)), self.words())
		self.assertIsNone(frappe.cache.get(key), "the marker must go once used")

	def test_128_a_login_disabled_between_the_two_steps_is_refused(self):
		with mock.patch("frappe.twofactor.send_token_via_email", return_value=True):
			tmp_id = self.sign_in()["tmp_id"]
		right = self._code_for(tmp_id)
		frappe.set_user("Administrator")
		frappe.db.set_value("User", PW_EMAIL, "enabled", 0, update_modified=False)
		frappe.db.commit()
		frappe.set_user("Guest")
		self.assertIsNone(self.confirm(tmp_id, right))
		self.assertEqual(self.answer()[:2], (401, "SIGN_IN_FAILED"))
		self.assertEqual(self.phones(), [])


# ── the password lands nowhere ───────────────────────────────────────────────

class ThePasswordLandsNowhere(PasswordCase):

	def scan(self):
		places = [("form_dict", json.dumps(frappe.form_dict, default=str)),
		          ("the response", json.dumps(frappe.local.response, default=str)),
		          ("the message log", json.dumps(frappe.local.message_log, default=str)),
		          ("Redis limit keys", " ".join(_keys("rl:")))]
		for row in frappe.get_all("Error Log", filters={"creation": [">=", self.started]},
		                          fields=["name", "method", "error", "metadata"]):
			places.append((f"Error Log {row.name}",
			               " ".join(str(row.get(f) or "") for f in ("method", "error", "metadata"))))
		for row in frappe.get_all("Activity Log", filters={"creation": [">=", self.started]},
		                          fields=["name", "subject", "content"]):
			places.append((f"Activity Log {row.name}", f"{row.subject} {row.content}"))
		from frappe.utils.error import get_error_metadata
		places.append(("Frappe's error metadata", str(get_error_metadata())))
		for where, text in places:
			self.assertNotIn(PASSWORD, text, f"the password leaked into {where}")
			self.assertNotIn(WRONG, text, f"a wrong password leaked into {where}")

	def test_128_after_every_kind_of_request_the_password_is_gone(self):
		for kwargs in ({}, {"password": WRONG}, {"email": UNKNOWN_EMAIL, "password": WRONG},
		               {"email": OTHER_EMAIL}):
			with self.subTest(**kwargs):
				self.sign_in(**kwargs)
				for field in ("password", "pwd", "email", "otp", "token"):
					self.assertNotIn(field, frappe.form_dict)
				self.scan()
		# The limiters' keys hold a hash of the account, never the address.
		self.assertFalse([k for k in _keys("rl:") + _keys("alvoraa_fa") if PW_EMAIL in k])

	def test_128_a_crash_logs_a_place_and_no_password(self):
		with mock.patch.object(join, "_set_up_phone", side_effect=RuntimeError("boom " + PASSWORD)):
			self.assertIsNone(self.sign_in())
		self.assertEqual(self.answer()[:2], (500, "SERVER_ERROR"))
		rows = frappe.get_all("Error Log", filters={"creation": [">=", self.started]},
		                      fields=["error"])
		self.assertTrue(any("endpoint: sign_in_with_password" in (r.error or "") for r in rows))
		self.scan()


# ── HR's two switches, and who each binds ────────────────────────────────────

class TheTwoWaysIn(PasswordCase):

	def test_128_the_password_switch_off_stops_new_sign_ins_only(self):
		"""The user's decision, 26 Sep 2026: a phone that already signed in keeps
		working; HR stops one phone with the block action."""
		token = self.signed_in()
		self.routes(code=1, password=0)
		self.assertIsNone(self.sign_in())
		self.assertEqual(self.answer()[:2], (403, "PASSWORD_SIGNIN_OFF"))
		self.assertIsNotNone(self.status(token), self.words())
		self.assertIsNotNone(self.punch(token, accuracy="15"), self.words())

	def test_128_the_master_switch_stops_both_ways(self):
		token = self.signed_in()
		self.configure(0, [self.driver], self.driver)
		self.assertIsNone(self.sign_in())
		self.assertEqual(self.answer()[1], "APP_OFF_FOR_FIELD")
		self.assertIsNone(self.status(token))
		self.assertEqual(self.answer()[1], "APP_OFF_FOR_FIELD")

	def test_128_the_code_switch_off_stops_new_codes_and_joins_only(self):
		qr_token = self.app_phone()
		code = _code_of(self.make())               # made while codes were on
		self.routes(code=0, password=1)
		# The phone that already joined keeps working.
		self.assertIsNotNone(self.status(qr_token), self.words())
		# A waiting code cannot be used to join now...
		self.assertIsNone(self.check(code))
		self.assertEqual(self.answer()[:2], (403, "JOIN_CODE_OFF"))
		self.assertIsNone(self.joined(code))
		self.assertEqual(self.answer()[:2], (403, "JOIN_CODE_OFF"))
		# ...and HR cannot make one, in HR's own words (the user's answer 4).
		self.assertIsNone(self.make())
		self.assertEqual(self.answer()[:2], (403, "JOIN_CODE_OFF"))
		self.assertIn("Joining codes are switched off in HR Settings.", self.words())
		# Signing in with a password still works.
		token = self.signed_in()
		self.assertIsNotNone(self.status(token), self.words())

	def test_128_the_designation_list_binds_code_phones_only(self):
		qr_token = self.app_phone()
		self.set_designation(self.clerk)             # not on the list
		self.assertIsNone(self.status(qr_token))
		self.assertEqual(self.answer()[:2], (403, "NOT_FIELD_ROLE"))

		token = self.signed_in()
		self.assertIsNotNone(self.status(token), self.words())
		self.assertIsNotNone(self.punch(token, accuracy="15"), self.words())
		# ...and the password phone replaced the code phone: one app phone each.
		qr_phone = self.phone_of(qr_token)
		self.assertEqual(qr_phone.status, "Replaced")
		self.assertEqual(frappe.db.get_value(fc.DEVICE, qr_phone.name, "replaced_by"),
		                 self.phone_of(token).name)

	def test_128_a_code_join_replaces_a_password_phone_too(self):
		token = self.signed_in()
		qr_token = self.app_phone()
		self.assertEqual(self.phone_of(token).status, "Replaced")
		self.assertEqual(self.phone_of(qr_token).join_method, JOIN_QR)

	def test_128_hr_settings_refuses_both_ways_off(self):
		frappe.set_user("Administrator")
		doc = frappe.get_single(fas.SETTINGS)
		doc.set(fas.F_CODE_JOIN, 0)
		doc.set(fas.F_PASSWORD, 0)
		doc.set(fas.F_REASON, fas.CHANGE_REASONS[0])
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.save()
		self.assertIn("at least one way", str(caught.exception))
		frappe.db.rollback()

	def test_128_turning_one_way_off_needs_a_reason_and_is_kept_in_the_history(self):
		frappe.set_user("Administrator")
		doc = frappe.get_single(fas.SETTINGS)
		doc.set(fas.F_PASSWORD, 0)
		with self.assertRaises(frappe.ValidationError):
			doc.save()
		frappe.db.rollback()
		doc = frappe.get_single(fas.SETTINGS)
		doc.set(fas.F_PASSWORD, 0)
		doc.set(fas.F_REASON, fas.CHANGE_REASONS[0])
		# Frappe writes no Version row in a test unless asked (step 2 does the same).
		doc.save(ignore_version=False)
		frappe.db.commit()
		try:
			self.assertEqual(frappe.db.get_single_value(fas.SETTINGS, fas.F_PASSWORD, cache=False), 0)
			newest = fas._history()[:1]
			self.assertTrue(newest, "no history row")
			self.assertIn(f"{fas.LABELS[fas.F_PASSWORD]}: on → off", newest[0]["lines"])
			self.assertEqual(newest[0]["reason"], fas.CHANGE_REASONS[0])
		finally:
			# Not a tenant's history; take it away again.
			frappe.db.delete("Version", {"ref_doctype": fas.SETTINGS, "creation": [">=", self.started]})
			frappe.db.commit()

	def test_128_the_installer_seeds_both_ways_on_and_never_turns_one_back_on(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Singles", {"doctype": fas.SETTINGS, "field": fas.F_PASSWORD})
		frappe.db.set_single_value(fas.SETTINGS, fas.F_CODE_JOIN, 0, update_modified=False)
		self.assertTrue(fas.after_migrate())
		self.assertEqual(frappe.db.get_single_value(fas.SETTINGS, fas.F_PASSWORD, cache=False), 1)
		self.assertEqual(frappe.db.get_single_value(fas.SETTINGS, fas.F_CODE_JOIN, cache=False), 0)
		for field in (fas.F_CODE_JOIN, fas.F_PASSWORD):
			self.assertEqual(frappe.db.count("Custom Field", {"dt": fas.SETTINGS, "fieldname": field}), 1)
		frappe.db.commit()

	def test_128_before_the_migrate_code_phones_keep_working_and_password_sign_in_waits(self):
		"""The minutes between a deploy and its migrate: neither switch is stored."""
		qr_token = self.app_phone()
		frappe.set_user("Administrator")
		frappe.db.delete("Singles", {"doctype": fas.SETTINGS,
		                             "field": ["in", [fas.F_CODE_JOIN, fas.F_PASSWORD]]})
		frappe.db.commit()
		frappe.set_user("Guest")
		current = fas.settings()
		self.assertTrue(current["readable"])
		self.assertTrue(current["enabled"], "the whole app must not read as off")
		self.assertEqual((current["code_join"], current["password_signin"]), (True, False))
		self.assertIsNotNone(self.status(qr_token), self.words())
		self.assertIsNone(self.sign_in())
		self.assertEqual(self.answer()[1], "PASSWORD_SIGNIN_OFF")

	def test_128_the_desk_calls_a_signed_in_person_joined_even_off_the_list(self):
		self.set_designation(self.clerk)
		self.signed_in()
		frappe.set_user("Administrator")
		frappe.local.form_dict = frappe._dict(employee=self.employee)
		out = desk.employee_app_section(employee=self.employee)
		self.assertEqual(out["state"], "joined")
		self.assertEqual(out["phones"][0]["join_method"], JOIN_PASSWORD)
		self.assertFalse(out["phones"][0]["stopped"])


# ── a phone stops when its login does ────────────────────────────────────────

class ADisabledLoginStopsItsPhone(PasswordCase):

	def test_128_disabling_the_user_blocks_the_password_phone(self):
		token = self.signed_in()
		frappe.set_user("Administrator")
		user = frappe.get_doc("User", PW_EMAIL)
		user.enabled = 0
		user.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.set_user("Guest")
		phone = frappe.db.get_value(fc.DEVICE, self.phone_of(token).name,
		                            ["status", "block_reason", "token_hash"], as_dict=True)
		self.assertEqual((phone.status, phone.block_reason), ("Blocked", "Login disabled"))
		self.assertFalse(phone.token_hash, "the secret is retired in the same save")
		self.assertIsNone(self.status(token))
		self.assertEqual(self.answer()[:2], (403, "DEVICE_BLOCKED"))

	def test_128_a_disable_that_skipped_the_hook_still_stops_the_phone(self):
		token = self.signed_in()
		frappe.set_user("Administrator")
		frappe.db.set_value("User", PW_EMAIL, "enabled", 0, update_modified=False)
		frappe.db.commit()
		frappe.set_user("Guest")
		self.assertIsNone(self.status(token))
		self.assertEqual(self.answer()[:2], (403, "DEVICE_BLOCKED"))
		self.assertIsNone(self.punch(token))
		self.assertEqual(self.answer()[1], "DEVICE_BLOCKED")

	def test_128_a_code_phone_is_not_touched_by_the_login(self):
		qr_token = self.app_phone()
		frappe.set_user("Administrator")
		user = frappe.get_doc("User", PW_EMAIL)
		user.enabled = 0
		user.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.set_user("Guest")
		self.assertEqual(self.phone_of(qr_token).status, "Active")
		self.assertIsNotNone(self.status(qr_token), self.words())

	# ── SEC-26 · a changed password ──────────────────────────────────────────

	def blocked_as(self, token, reason):
		phone = frappe.db.get_value(fc.DEVICE, self.phone_of(token).name,
		                            ["status", "block_reason", "token_hash"], as_dict=True)
		self.assertEqual((phone.status, phone.block_reason), ("Blocked", reason))
		self.assertFalse(phone.token_hash, "the secret is retired in the same save")
		self.assertIsNone(self.punch(token))
		self.assertEqual(self.answer()[:2], (403, "DEVICE_BLOCKED"))

	def test_128_sec26_a_new_password_set_on_the_user_form_blocks_the_phone(self):
		token = self.signed_in()
		frappe.set_user("Administrator")
		user = frappe.get_doc("User", PW_EMAIL)
		user.new_password = "Zqx-Pw128-Newer!horse-" + "9"
		user.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.set_user("Guest")
		self.blocked_as(token, "Password changed")

	def test_128_sec26_a_forgot_password_reset_blocks_the_phone(self):
		from alvoraa_portal import field_app_device as device_api

		token = self.signed_in()
		frappe.set_user("Administrator")
		link = frappe.get_doc("User", PW_EMAIL)._reset_password(send_email=False)
		key = link.split("key=", 1)[1].split("&", 1)[0]
		frappe.db.commit()
		frappe.set_user("Guest")
		# The website's /update-password page, through the override in hooks.py.
		self.assertEqual(frappe.get_hooks("override_whitelisted_methods")
		                 .get("frappe.core.doctype.user.user.update_password"),
		                 ["alvoraa_portal.field_app_device.update_password"])
		frappe.local.response = frappe._dict()
		with mock.patch.object(frappe.local, "login_manager", mock.MagicMock(), create=True):
			device_api.update_password(new_password="Zqx-Pw128-Reset!horse-" + "7", key=key)
		frappe.db.commit()
		frappe.set_user("Guest")
		self.blocked_as(token, "Password changed")

	def test_128_sec26_our_own_tenant_setup_reset_blocks_the_phone(self):
		"""Round-two P3: tenant_setup resets an existing login's password with
		frappe.utils.password.update_password, which no hook sees."""
		from alvoraa_portal import tenant_setup

		token = self.signed_in()
		frappe.set_user("Administrator")
		tenant_setup._make_user(PW_EMAIL, FIRST_NAME, "Zqx-Pw128-Setup!horse-" + "5", ["Employee"])
		frappe.db.commit()
		frappe.set_user("Guest")
		self.blocked_as(token, "Password changed")

	def test_128_sec26_a_used_or_wrong_reset_key_blocks_nothing(self):
		from alvoraa_portal import field_app_device as device_api

		token = self.signed_in()
		frappe.local.response = frappe._dict()
		with mock.patch.object(frappe.local, "login_manager", mock.MagicMock(), create=True):
			device_api.update_password(new_password="Zqx-Pw128-Reset!horse-" + "7", key="zqx-no-such-key")
		self.assertEqual(frappe.local.response.get("http_status_code"), 410)
		self.assertEqual(self.phone_of(token).status, "Active")

	# ── SEC-28 · an unlinked login ───────────────────────────────────────────

	def test_128_sec28_changing_the_employees_login_blocks_the_phone(self):
		token = self.signed_in()
		frappe.set_user("Administrator")
		emp = frappe.get_doc("Employee", self.employee)
		emp.user_id = OTHER_EMAIL
		emp.create_user_permission = 0
		emp.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.set_user("Guest")
		self.blocked_as(token, "Login unlinked")

	def test_128_sec28_an_unlink_that_skipped_the_hook_is_still_refused(self):
		token = self.signed_in()
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.employee, "user_id", None, update_modified=False)
		frappe.db.commit()
		frappe.set_user("Guest")
		self.assertIsNone(self.punch(token))
		self.assertEqual(self.answer()[:2], (403, "LOGIN_UNLINKED"))
		self.assertIsNone(self.status(token))
		self.assertEqual(self.answer()[:2], (403, "LOGIN_UNLINKED"))

	def test_128_sec28_saving_the_employee_without_changing_the_login_blocks_nothing(self):
		token = self.signed_in()
		frappe.set_user("Administrator")
		emp = frappe.get_doc("Employee", self.employee)
		emp.create_user_permission = 0
		emp.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.set_user("Guest")
		self.assertEqual(self.phone_of(token).status, "Active")


# ── the limits and the wrapping ──────────────────────────────────────────────

class TheLimits(PasswordCase):

	def test_128_the_eleventh_try_for_one_account_in_an_hour_is_too_many(self):
		for _ in range(10):
			self.assertIsNone(self.sign_in(password=WRONG))
			self.assertEqual(self.answer()[1], "SIGN_IN_FAILED")
		self.assertIsNone(self.sign_in())
		self.assertEqual(self.answer()[:2], (429, "TOO_MANY_TRIES"))
		# Another account from the same address is its own bucket.
		self.assertIsNone(self.sign_in(email=OTHER_EMAIL))
		self.assertEqual(self.answer()[1], "NO_EMPLOYEE_RECORD")

	def test_128_sec29_spellings_of_one_account_share_one_count(self):
		from frappe.core.doctype.user.user import User

		local, domain = PW_EMAIL.split("@")
		spellings = [PW_EMAIL.upper(), f" {PW_EMAIL} ", f"{local}@exämple.com",
		             f"{local.replace('pw', 'pŵ')}@{domain}", PW_EMAIL.title()]
		# The database finds the same login for every spelling - that is the gap.
		for s in spellings:
			found = User.find_by_credentials(s.strip(), "", validate_password=False)
			self.assertEqual(found and found["name"], PW_EMAIL, s)
		for i in range(10):
			self.assertIsNone(self.sign_in(email=spellings[i % len(spellings)], password=WRONG))
			self.assertEqual(self.answer()[1], "SIGN_IN_FAILED", spellings[i % len(spellings)])
		self.assertIsNone(self.sign_in())
		self.assertEqual(self.answer()[:2], (429, "TOO_MANY_TRIES"))
		# The count's key holds a hash, never the address.
		self.assertFalse([k for k in _keys("alvoraa_fa") if local in k])

	def test_128_the_address_limit_counts_every_email(self):
		# Read the limit off each endpoint, then prove it bites with a small one.
		# 500 an hour: the user's decision of 26 Sep 2026 (a depot's first day).
		for endpoint in (join.sign_in_with_password, join.confirm_sign_in_code):
			chain, fn = [], endpoint
			while fn is not None:
				chain.append(getattr(fn, "__alvoraa_address_limit__", None))
				fn = getattr(fn, "__wrapped__", None)
			self.assertIn((500, limits.WINDOW_SECONDS), chain, endpoint.__name__)

		@limits._limited_by_address(limit=2)
		def probe():
			return "ok"

		frappe.local.form_dict = frappe._dict(cmd="alvoraa_portal.field_app_join.zqx_probe_128")
		self.assertEqual(probe(), "ok")
		self.assertEqual(probe(), "ok")
		with self.assertRaises(errors.FieldAppRefusal) as caught:
			probe()
		self.assertEqual(caught.exception.alvoraa_code, "TOO_MANY_TRIES")

	def test_128_both_endpoints_are_post_only_guest_private_gated_and_limited(self):
		# The per-account limit is counted inside, on the login Frappe finds (SEC-29).
		self.assertIsNone(_limit_of(join.sign_in_with_password))
		self.assertEqual(join.ACCOUNT_LIMIT, 10)
		self.assertEqual(_limit_of(join.confirm_sign_in_code), ("signin_otp_key", "tmp_id", 5))
		for fn in (join.sign_in_with_password, join.confirm_sign_in_code):
			with self.subTest(endpoint=fn.__name__):
				self.assertIn(fn, frappe.guest_methods)
				self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[fn], ["POST"])
				chain, f = [], fn
				while f is not None:
					chain.append(f)
					f = getattr(f, "__wrapped__", None)
				private = [i for i, x in enumerate(chain) if hasattr(x, "__alvoraa_private_request__")]
				gate = [i for i, x in enumerate(chain) if hasattr(x, "__alvoraa_feature__")]
				self.assertTrue(private and gate)
				self.assertLess(private[-1], gate[-1], "the wrapper sits above the plan gate")
				fields = chain[private[-1]].__alvoraa_private_request__
				for field in ("email", "password", "otp", "tmp_id", "token"):
					self.assertIn(field, fields)

	def test_128_the_new_codes_are_in_the_table_and_the_old_ones_did_not_move(self):
		for code in ("SIGN_IN_FAILED", "ACCOUNT_LOCKED", "PASSWORD_EXPIRED", "SIGN_IN_NOT_ALLOWED",
		             "OTP_WRONG", "OTP_EXPIRED", "NO_EMPLOYEE_RECORD", "PASSWORD_SIGNIN_OFF",
		             "JOIN_CODE_OFF", "NETWORK_LOCKED", "LOGIN_UNLINKED"):
			self.assertIn(code, errors.CODES)
		self.assertEqual(errors.CODES["SIGN_IN_FAILED"], (401, ()))
		self.assertEqual(errors.CODES["QR_USED"], (410, ("used_at",)))
		self.assertEqual(set(APP_JOIN_METHODS), {JOIN_QR, JOIN_PASSWORD})
		options = frappe.get_meta(fc.DEVICE).get_field("join_method").options.split("\n")
		self.assertIn(JOIN_PASSWORD, options)

	def test_128_the_plan_gate_still_applies(self):
		frappe.conf["features"] = [f for f in frappe.conf["features"] if f != "field_checkin"]
		self.assertIsNone(self.sign_in())
		self.assertEqual(self.answer()[:2], (403, "FEATURE_OFF"))
