"""Slice 013, step 5: the HR desk. What HR sees on the Employee record, and
the two things HR can do to a phone or a code from there.

Every test here names the thing it keeps alive:

  * **US-16 / AC-109** - the section's data (E12) is for HR only, and only
    for an employee that HR user may read. An Employee-role user, a guest and
    an HR user limited to another company are refused. **Fail-without-fix
    recipe:** delete the `if not has_permission(...)` two lines in
    `field_app_desk.hr_who_may_act` and `test_013_ac109_..._limited_to_another_
    company_is_refused` fails, as do step 3's AC-43 and the AC-52 cancel test
    below, because the role check alone lets a store HR user read and cancel
    for every company. (Proven on the bench 2026-09-20: 3 of the 4 fail. The
    AC-111 block test still holds, because E11 saves through Frappe's own
    write permission and the company hook - the second gate.)
  * **US-16 / AC-103** - one state word per situation, worked out on the
    server: not joined, code waiting, joined, not agreed, blocked, not a
    field worker, app switched off, plan without field check-in, left.
  * **AC-107 / PRIV-9** - nothing in the answer is a secret, a hash, a code
    or a coordinate; the only time on a phone row is its last saved punch.
  * **US-7 / AC-51, AC-52** - E10 cancels a waiting code with who and when,
    retires its hash, and is safe to call twice.
  * **US-17 / AC-110 to AC-113** - E11 needs a reason, blocks Active, Pending
    and not-yet-agreed phones, retires the secret, never offers an unblock.
  * **US-18 / AC-114, AC-115** - the phone list shows what a rollout needs
    and no "last seen"; an HR user limited to one company sees one company.
  * **Section 6** - E10 and E11 are 30 an hour per HR user, keyed on a hash.
"""

import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now

from alvoraa_goals.tests.utils import ensure_company
from alvoraa_portal import field_app_desk as desk
from alvoraa_portal import field_app_device as device_api
from alvoraa_portal import field_app_join as join
from alvoraa_portal import field_app_notice as notice
from alvoraa_portal import field_checkin as fc
from alvoraa_portal import hooks
from alvoraa_portal import subscription as sub
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_app_invite.alvoraa_app_invite import INVITE
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_notice_acknowledgement.alvoraa_notice_acknowledgement import (
	record_acknowledgement,
)
from alvoraa_portal.tests.test_field_app_step1_013 import _bin, _new_phone
from alvoraa_portal.tests.test_field_app_step2_013 import (
	_company_permission,
	_employee,
	_user,
)
from alvoraa_portal.tests.test_field_app_step3_013 import (
	JoinCase,
	_clear_codes,
	_code_of,
	_FakeRequest,
)
from alvoraa_portal.tests.test_portal_security_010 import _second_company

SECTION_KEYS = {"me", "employee", "app", "state", "can_invite", "waiting_code", "phone",
                "phones", "codes", "block_reasons", "checkin_url", "server_time"}


class DeskCase(JoinCase):
	"""The step-3 fixture - a listed field worker, the app on, one HR maker -
	plus the desk calls.

	The maker gets a Company User Permission for the employee's company here:
	E11 saves the phone record through Frappe's own write permission and the
	company scoping hook (C-11c), and an HR Manager with no company and no
	employee record is scoped to nothing (step 2, pinned). A real HR user
	always has one or the other."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.company = frappe.db.get_value("Employee", cls.employee, "company")
		cls.maker_perm = _company_permission(cls.maker, cls.company)
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		frappe.delete_doc("User Permission", cls.maker_perm, force=True, ignore_permissions=True)
		frappe.db.commit()
		super().tearDownClass()

	def call(self, endpoint, args):
		frappe.local.response = frappe._dict()
		frappe.clear_messages()
		frappe.local.form_dict = frappe._dict(
			args, cmd=f"{endpoint.__module__}.{endpoint.__name__}")
		out = endpoint(**args)
		frappe.db.commit()
		return out

	def desk(self, endpoint, args, user=None):
		"""Call a desk endpoint as this user. Our own refusals (the plan, the
		limit) come back as None with the code in the response; Frappe's own
		PermissionError and ValidationError raise, as they do on the desk."""
		frappe.set_user(user or self.maker)
		try:
			frappe.local.response = frappe._dict()
			frappe.clear_messages()
			frappe.local.form_dict = frappe._dict(
				args, cmd=f"{endpoint.__module__}.{endpoint.__name__}")
			out = endpoint(**args)
			frappe.db.commit()
			return out
		finally:
			frappe.set_user("Guest")

	def section(self, employee=None, user=None):
		return self.desk(desk.employee_app_section, {"employee": employee or self.employee}, user)

	def cancel(self, invite, user=None):
		return self.desk(join.cancel_code, {"invite": invite}, user)

	def block(self, device, reason="Phone lost or stolen", user=None):
		args = {"device": device}
		if reason is not None:
			args["reason"] = reason
		return self.desk(device_api.block_phone, args, user)

	def app_phone(self, agreed=1):
		"""Join with a fresh code, the way a real app phone exists."""
		out = self.make()
		if agreed:
			answer = self.joined(_code_of(out))
		else:
			answer = self.joined(_code_of(out), agreed=0, notice_version=None)
		self.assertIn("token", answer or {}, self.words())
		return answer["token"], out

	def phone_by_token(self, token):
		fields = ["name", "status", "token_hash", "retired_token_hash", "block_reason",
		          "status_changed_on", "status_changed_by", "status_change_source"]
		row = frappe.db.get_value(fc.DEVICE, {"token_hash": fc._hash(token)}, fields, as_dict=True)
		if not row:
			row = frappe.db.get_value(fc.DEVICE, {"retired_token_hash": fc._hash(token)}, fields,
			                          as_dict=True)
		return row

	def status(self, token):
		frappe.local.response = frappe._dict()
		frappe.clear_messages()
		frappe.local.form_dict = frappe._dict({"token": token},
		                                      cmd="alvoraa_portal.field_checkin.field_status")
		return fc.field_status(token=token)


# ── US-16 · who may see the section ─────────────────────────────────────────

class TheSectionIsForHrWhoMayReadThePerson(DeskCase):

	def test_013_ac102_an_hr_manager_gets_the_section_with_every_key(self):
		out = self.section()
		self.assertEqual(set(out), SECTION_KEYS)
		self.assertEqual(out["me"], self.maker)
		self.assertEqual(out["employee"]["name"], self.employee)
		self.assertEqual(out["employee"]["designation"], self.driver)
		self.assertTrue(out["app"]["enabled"])
		self.assertTrue(out["app"]["listed"])
		self.assertEqual(out["app"]["lifetime_hours"], 24)
		# Only lifetimes up to the organisation's setting are offered (AC-46, D6).
		self.assertEqual([lt["hours"] for lt in out["app"]["lifetimes"]], [1, 4, 12, 24])
		self.assertEqual(out["block_reasons"], list(desk.BLOCK_REASONS))
		self.assertEqual(out["state"], "no_phone")
		self.assertTrue(out["can_invite"])
		self.assertTrue(out["checkin_url"].endswith("/checkin"))

	def test_013_ac109_an_employee_and_a_guest_are_refused(self):
		for user in (self.employee_user, "Guest"):
			with self.subTest(user=user):
				with self.assertRaises(frappe.PermissionError):
					self.section(user=user)
				frappe.db.rollback()

	def test_013_ac109_an_hr_user_limited_to_another_company_is_refused(self):
		"""Fail-without-fix: remove the `has_permission` check in
		`field_app_desk.hr_who_may_act` and this passes the role check and
		hands a store HR user another company's employee."""
		frappe.set_user("Administrator")
		company_b = _second_company()
		company_a = ensure_company()
		emp_b = _employee("DeskBeta", company_b, designation=self.driver)
		limited = _user("desk.limited", ["HR User"])
		perm = _company_permission(limited, company_a)
		try:
			with self.assertRaises(frappe.PermissionError):
				self.section(employee=emp_b, user=limited)
			frappe.db.rollback()
			# The same user may see an employee of their own company.
			emp_a = _employee("DeskAlpha", company_a, designation=self.driver)
			out = self.section(employee=emp_a, user=limited)
			self.assertEqual(out["employee"]["name"], emp_a)
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User Permission", perm, force=True, ignore_permissions=True)
			frappe.db.commit()

	def test_013_ac103_a_plan_without_field_checkin_answers_feature_off_and_nothing_else(self):
		frappe.conf["features"] = [f for f in sub.FEATURES if f != "field_checkin"]
		try:
			self.assertIsNone(self.section())
			self.assertEqual(self.answer()[:2], (403, "FEATURE_OFF"))
		finally:
			frappe.conf["features"] = list(sub.FEATURES)

	def test_013_ac107_nothing_secret_and_nothing_that_watches_people_is_in_the_answer(self):
		token, made = self.app_phone()
		waiting = self.make()
		code = _code_of(waiting)
		out = self.section()
		text = json.dumps(out)
		for forbidden in (token, fc._hash(token), code, fc._hash(code), "latitude", "longitude",
		                  "token_hash", "last_opened", "online"):
			self.assertNotIn(forbidden, text, forbidden[:12])
		# The only time on a phone row is its last saved PUNCH; an open moves nothing.
		before = out["phones"][0]["last_seen"]
		self.status(token)
		self.assertEqual(self.section()["phones"][0]["last_seen"], before)
		self.assertEqual(before, "")


# ── US-16 · the states ──────────────────────────────────────────────────────

class TheStateMachine(DeskCase):

	def test_013_ac103_code_waiting(self):
		made = self.make(hours=4)
		out = self.section()
		self.assertEqual(out["state"], "code_waiting")
		self.assertEqual(out["waiting_code"]["name"], made["invite"])
		self.assertEqual(out["waiting_code"]["made_by"], self.maker)
		self.assertEqual(out["waiting_code"]["lifetime_hours"], 4)
		self.assertEqual(out["waiting_code"]["outcome"], "waiting")
		self.assertTrue(out["can_invite"])
		self.assertEqual(len(out["codes"]), 1)

	def test_013_ac103_ac104_ac105_joined(self):
		token, made = self.app_phone()
		out = self.section()
		self.assertEqual(out["state"], "joined")
		phone = out["phone"]
		self.assertEqual(phone["status"], "Active")
		self.assertEqual(phone["status_word"], "Active")
		self.assertEqual(phone["device_label"], "Redmi 12")
		self.assertEqual(phone["join_method"], "App QR code")
		self.assertEqual(phone["invite"], made["invite"])
		# AC-104: the script says "you" or the maker's name from these two.
		self.assertEqual(phone["invite_made_by"], self.maker)
		self.assertEqual(out["me"], self.maker)
		self.assertTrue(phone["can_block"])
		self.assertFalse(phone["not_field_worker"])
		self.assertEqual(out["waiting_code"], None)
		self.assertEqual(out["codes"][0]["outcome"], "used")
		self.assertEqual(out["codes"][0]["used_device_label"], "Redmi 12")

	def test_013_not_agreed(self):
		token, _ = self.app_phone(agreed=0)
		out = self.section()
		self.assertEqual(out["state"], "not_agreed")
		self.assertEqual(out["phone"]["status_word"], "Not agreed yet")
		self.assertTrue(out["phone"]["can_block"])
		self.assertTrue(out["can_invite"])

	def test_013_ac103_ac112_blocked_and_no_way_back(self):
		token, _ = self.app_phone()
		name = self.phone_by_token(token).name
		self.block(name, "Has a new phone")
		out = self.section()
		self.assertEqual(out["state"], "blocked")
		self.assertEqual(out["phone"]["name"], name)
		self.assertEqual(out["phone"]["block_reason"], "Has a new phone")
		self.assertEqual(out["phone"]["status_changed_by"], self.maker)
		self.assertTrue(out["can_invite"])
		# AC-112: nothing in the answer offers a way back for a blocked phone.
		self.assertFalse(out["phone"]["can_block"])
		self.assertNotIn("unblock", json.dumps(out).lower())

	def test_013_ac103_app_off_shows_the_phone_as_stopped(self):
		token, _ = self.app_phone()
		self.configure(0, [self.driver], self.driver)
		out = self.section()
		self.assertEqual(out["state"], "app_off")
		self.assertFalse(out["can_invite"])
		self.assertEqual(out["phones"][0]["status_word"], "Stopped")
		self.assertTrue(out["phones"][0]["stopped"])
		# Restored: no new code needed, the same phone is Active again.
		self.configure(1, [self.driver], self.driver)
		out = self.section()
		self.assertEqual(out["state"], "joined")
		self.assertEqual(out["phones"][0]["status_word"], "Active")

	def test_013_ac103_ac106_not_a_field_worker(self):
		# A web-page phone from before the rule keeps working and is flagged.
		frappe.set_user("Administrator")
		_new_phone(self.employee, "Active", join_method="Web check-in page")
		frappe.db.commit()
		self.configure(1, [self.driver], self.clerk)
		out = self.section()
		self.assertEqual(out["state"], "not_field")
		self.assertFalse(out["can_invite"])
		self.assertTrue(out["phones"][0]["not_field_worker"])
		self.assertEqual(out["phones"][0]["status_word"], "Active")

	def test_013_web_page_phone_waiting_for_hr(self):
		frappe.set_user("Administrator")
		_new_phone(self.employee, "Pending", join_method="Web check-in page")
		frappe.db.commit()
		out = self.section()
		self.assertEqual(out["state"], "web_pending")
		self.assertEqual(out["phone"]["status_word"], "Waiting for HR")
		self.assertTrue(out["phone"]["can_block"])

	def test_013_an_employee_who_left(self):
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.employee, "status", "Left", update_modified=False)
		frappe.db.commit()
		try:
			out = self.section()
			self.assertEqual(out["state"], "not_active")
			self.assertFalse(out["can_invite"])
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", self.employee, "status", "Active", update_modified=False)
			frappe.db.commit()

	def test_013_ac108_every_outcome_a_code_can_have(self):
		# newer code made
		first = self.make()
		second = self.make()
		# cancelled by HR
		self.cancel(second["invite"])
		# this is not me
		third = self.make()
		self.call(join.refuse_code, {"code": _code_of(third)})
		# used
		token, fifth = self.app_phone()
		# ran out (the daily job is step 6; until it runs the section says so itself)
		fourth = self.make()
		frappe.set_user("Administrator")
		frappe.db.set_value(INVITE, fourth["invite"], "expires_at", add_to_date(now(), hours=-1),
		                    update_modified=False)
		frappe.db.commit()
		frappe.set_user("Guest")
		out = self.section()
		by_name = {c["name"]: c["outcome"] for c in out["codes"]}
		self.assertEqual(by_name[first["invite"]], "newer_code")
		self.assertEqual(by_name[second["invite"]], "cancelled_by_hr")
		self.assertEqual(by_name[third["invite"]], "not_me")
		self.assertEqual(by_name[fourth["invite"]], "ran_out")
		self.assertEqual(by_name[fifth["invite"]], "used")
		# A code that ran out is not "waiting", so the phone is what counts.
		self.assertEqual(out["state"], "joined")
		self.assertEqual(out["waiting_code"], None)
		# Newest first.
		self.assertEqual(out["codes"][0]["name"], fourth["invite"])


# ── US-7 · cancel a waiting code ────────────────────────────────────────────

class CancelAWaitingCode(DeskCase):

	def test_013_ac51_cancelled_by_hr_with_who_and_when_and_the_hash_retired(self):
		made = self.make()
		code = _code_of(made)
		self.assertEqual(self.cancel(made["invite"]), {})
		row = self.invite(made["invite"])
		self.assertEqual(row.status, "Cancelled")
		self.assertEqual(row.cancel_reason, "By HR")
		self.assertEqual(row.cancelled_by, self.maker)
		self.assertTrue(row.cancelled_at)
		self.assertFalse(row.token_hash)
		self.assertEqual(row.retired_token_hash, fc._hash(code))
		# E1 with that code now says so, with no name.
		self.assertIsNone(self.check(code))
		self.assertEqual(self.answer()[:2], (410, "QR_CANCELLED"))
		self.assertEqual(self.section()["codes"][0]["outcome"], "cancelled_by_hr")

	def test_013_ac52_an_hr_user_without_permission_on_the_employee_is_refused(self):
		frappe.set_user("Administrator")
		company_b = _second_company()
		company_a = ensure_company()
		emp_b = _employee("CancelBeta", company_b, designation=self.driver)
		limited = _user("cancel.limited", ["HR User"])
		perm = _company_permission(limited, company_a)
		made = self.make(employee=emp_b, user="Administrator")
		try:
			for user in (limited, self.employee_user, "Guest"):
				with self.subTest(user=user):
					with self.assertRaises(frappe.PermissionError):
						self.cancel(made["invite"], user=user)
					frappe.db.rollback()
			self.assertEqual(self.invite(made["invite"]).status, "Waiting")
			# A code that does not exist gets the same sentence, not "not found".
			with self.assertRaises(frappe.PermissionError):
				self.cancel("no-such-code")
		finally:
			frappe.set_user("Administrator")
			_clear_codes(emp_b)
			frappe.delete_doc("User Permission", perm, force=True, ignore_permissions=True)
			frappe.db.commit()

	def test_013_cancelling_twice_or_cancelling_a_used_code_changes_nothing(self):
		made = self.make()
		self.cancel(made["invite"])
		first = self.invite(made["invite"])
		self.assertEqual(self.cancel(made["invite"]), {})
		self.assertEqual(self.invite(made["invite"]).cancelled_at, first.cancelled_at)

		token, used = self.app_phone()
		self.assertEqual(self.cancel(used["invite"]), {})
		self.assertEqual(self.invite(used["invite"]).status, "Used")
		self.assertEqual(self.phone_by_token(token).status, "Active")


# ── US-17 · block a phone ───────────────────────────────────────────────────

class BlockAPhone(DeskCase):

	def test_013_ac110_no_reason_or_a_reason_off_the_list_is_refused(self):
		token, _ = self.app_phone()
		name = self.phone_by_token(token).name
		for reason in (None, "", "Because", "phone lost or stolen"):
			with self.subTest(reason=reason):
				with self.assertRaises(frappe.ValidationError) as caught:
					self.block(name, reason)
				self.assertIn("Choose a reason", str(caught.exception))
				frappe.db.rollback()
		self.assertEqual(self.phone_by_token(token).status, "Active")

	def test_013_ac111_blocked_with_the_reason_who_and_when_and_the_secret_retired(self):
		token, _ = self.app_phone()
		name = self.phone_by_token(token).name
		self.assertEqual(self.block(name, "Phone lost or stolen"), {})
		row = self.phone_by_token(token)
		self.assertEqual(row.status, "Blocked")
		self.assertEqual(row.block_reason, "Phone lost or stolen")
		self.assertEqual(row.status_changed_by, self.maker)
		self.assertEqual(row.status_change_source, "HR")
		self.assertTrue(row.status_changed_on)
		self.assertFalse(row.token_hash)
		self.assertEqual(row.retired_token_hash, fc._hash(token))
		# The phone's next open: blocked, no reason, no values (PRIV-13).
		self.assertIsNone(self.status(token))
		status, code, values = self.answer()
		self.assertEqual((status, code), (403, "DEVICE_BLOCKED"))
		self.assertEqual(values, {})
		self.assertNotIn("lost", self.words().lower())

	def test_013_ac113_a_pending_web_page_phone_is_blocked_the_same_way(self):
		frappe.set_user("Administrator")
		doc, token = _new_phone(self.employee, "Pending", join_method="Web check-in page")
		frappe.db.commit()
		self.block(doc.name, "Someone else was using it")
		row = self.phone_by_token(token)
		self.assertEqual((row.status, row.block_reason, row.status_change_source),
		                 ("Blocked", "Someone else was using it", "HR"))
		self.assertEqual(row.retired_token_hash, fc._hash(token))

	def test_013_a_phone_that_never_agreed_can_still_be_blocked(self):
		token, _ = self.app_phone(agreed=0)
		name = self.phone_by_token(token).name
		self.assertEqual(self.phone_by_token(token).status, "Consent not given")
		self.block(name, "Phone lost or stolen")
		row = self.phone_by_token(token)
		self.assertEqual((row.status, row.status_change_source, row.status_changed_by),
		                 ("Blocked", "HR", self.maker))
		self.assertFalse(row.token_hash)

	def test_013_ac112_blocking_twice_keeps_the_first_reason_and_a_stopped_phone_is_refused(self):
		token, _ = self.app_phone()
		name = self.phone_by_token(token).name
		self.block(name, "Phone lost or stolen")
		first = self.phone_by_token(token)
		self.assertEqual(self.block(name, "Other"), {})
		again = self.phone_by_token(token)
		self.assertEqual(again.block_reason, "Phone lost or stolen")
		self.assertEqual(again.status_changed_on, first.status_changed_on)

		# A removed phone holds no live secret; there is nothing to block.
		token2, _ = self.app_phone()
		name2 = self.phone_by_token(token2).name
		self.call(device_api.remove_my_phone, {"token": token2})
		self.assertEqual(self.phone_by_token(token2).status, "Removed")
		with self.assertRaises(frappe.ValidationError) as caught:
			self.block(name2, "Other")
		self.assertIn("already stopped", str(caught.exception))
		frappe.db.rollback()

	def test_013_ac111_an_hr_user_without_permission_on_the_employee_is_refused(self):
		frappe.set_user("Administrator")
		company_b = _second_company()
		company_a = ensure_company()
		emp_b = _employee("BlockBeta", company_b, designation=self.driver)
		doc, token = _new_phone(emp_b, "Active", join_method="Web check-in page")
		limited = _user("block.limited", ["HR User"])
		perm = _company_permission(limited, company_a)
		frappe.db.commit()
		try:
			for user in (limited, self.employee_user, "Guest"):
				with self.subTest(user=user):
					with self.assertRaises(frappe.PermissionError):
						self.block(doc.name, "Other", user=user)
					frappe.db.rollback()
			self.assertEqual(self.phone_by_token(token).status, "Active")
			with self.assertRaises(frappe.PermissionError):
				self.block("no-such-phone", "Other")
		finally:
			frappe.set_user("Administrator")
			_bin(fc.DEVICE, doc.name)
			frappe.delete_doc("User Permission", perm, force=True, ignore_permissions=True)
			frappe.db.commit()


# ── US-18 · the phone list ──────────────────────────────────────────────────

class ThePhoneListIsShapedForRollouts(FrappeTestCase):

	def _json(self):
		root = os.path.dirname(fc.__file__)
		path = os.path.join(root, "alvoraa_portal", "doctype", "alvoraa_field_device",
		                    "alvoraa_field_device.json")
		with open(path, encoding="utf-8") as f:
			return json.load(f)

	def test_013_ac114_the_columns_are_who_which_how_when_and_status_and_never_last_seen(self):
		fields = {f["fieldname"]: f for f in self._json()["fields"]}
		listed = {name for name, f in fields.items() if f.get("in_list_view")}
		self.assertEqual(listed, {"employee", "employee_name", "status", "device_label",
		                          "join_method", "registered_on"})
		self.assertEqual(fields["registered_on"]["label"], "Joined")
		for never in ("last_seen", "checkin_count", "token_hash", "retired_token_hash"):
			self.assertFalse(fields[never].get("in_list_view"), never)

	def test_013_ac114_the_list_script_is_wired_and_has_no_last_seen(self):
		self.assertEqual(hooks.doctype_list_js.get("Alvoraa Field Device"),
		                 "public/js/alvoraa_field_device_list.js")
		root = os.path.dirname(fc.__file__)
		path = os.path.join(root, "public", "js", "alvoraa_field_device_list.js")
		with open(path, encoding="utf-8") as f:
			script = f.read()
		self.assertIn('frappe.listview_settings["Alvoraa Field Device"]', script)
		self.assertIn("registered_on", script)
		for never in ("last_seen", "checkin_count"):
			self.assertNotIn(never, script, never)

	def test_013_ac115_an_hr_user_limited_to_one_company_lists_one_companys_phones(self):
		frappe.set_user("Administrator")
		company_b = _second_company()
		company_a = ensure_company()
		emp_a = _employee("ListAlpha", company_a)
		emp_b = _employee("ListBeta", company_b)
		a, _ = _new_phone(emp_a, "Active")
		b, _ = _new_phone(emp_b, "Active")
		limited = _user("list.limited", ["HR User"])
		perm = _company_permission(limited, company_b)
		frappe.db.commit()
		try:
			frappe.set_user(limited)
			seen = set(frappe.get_list(fc.DEVICE, pluck="name", filters={"name": ["in", [a.name, b.name]]}))
			self.assertEqual(seen, {b.name})
		finally:
			frappe.set_user("Administrator")
			_bin(fc.DEVICE, a.name)
			_bin(fc.DEVICE, b.name)
			frappe.delete_doc("User Permission", perm, force=True, ignore_permissions=True)
			frappe.db.commit()


# ── section 6 · the limits, and the contract ────────────────────────────────

class TheDeskLimitsArePerHrUser(DeskCase):
	"""Frappe's limiter only runs when there is a request; a fake one is enough."""

	PREFIXES = ("rl:alvoraa_portal.field_app_join", "rl:alvoraa_portal.field_app_device")

	def setUp(self):
		super().setUp()
		for p in self.PREFIXES:
			frappe.cache.delete_keys(p)
		frappe.local.request = _FakeRequest()
		frappe.local.request_ip = "127.0.0.1"

	def tearDown(self):
		frappe.local.request = None
		for p in self.PREFIXES:
			frappe.cache.delete_keys(p)
		super().tearDown()

	def test_013_the_31st_cancel_and_the_31st_block_in_an_hour_are_too_many(self):
		for endpoint, args in ((join.cancel_code, {"invite": "no-such-code"}),
		                       (device_api.block_phone, {"device": "no-such-phone", "reason": "Other"})):
			with self.subTest(endpoint=endpoint.__name__):
				for _ in range(30):
					with self.assertRaises(frappe.PermissionError):
						self.desk(endpoint, dict(args))
					frappe.db.rollback()
				self.assertIsNone(self.desk(endpoint, dict(args)))
				status, code, values = self.answer()
				self.assertEqual((status, code), (429, "TOO_MANY_TRIES"))
				self.assertGreater((values or {}).get("retry_after_s", 0), 0)
		keys = []
		for p in self.PREFIXES:
			keys += [k.decode() if isinstance(k, bytes) else str(k) for k in frappe.cache.get_keys(p)]
		self.assertTrue(keys)
		for key in keys:
			self.assertNotIn(self.maker, key, "an HR user's email was written into a Redis key")


class TheContract(DeskCase):

	def test_013_the_desk_endpoints_are_whitelisted_for_sessions_wrapped_and_gated(self):
		for fn in (desk.employee_app_section, join.make_code, join.cancel_code,
		           device_api.block_phone):
			with self.subTest(endpoint=fn.__name__):
				chain, f = [], fn
				while f is not None:
					chain.append(f)
					f = getattr(f, "__wrapped__", None)
				wrapper = [i for i, x in enumerate(chain) if hasattr(x, "__alvoraa_desk_request__")]
				gate = [i for i, x in enumerate(chain) if hasattr(x, "__alvoraa_feature__")]
				self.assertTrue(wrapper and gate, "not wrapped and gated")
				self.assertLess(wrapper[-1], gate[-1], "the wrapper must sit above the gate")
				self.assertIn(fn, frappe.whitelisted)
				self.assertNotIn(fn, frappe.guest_methods)

	def test_013_the_block_reasons_are_the_phone_records_own_list(self):
		options = frappe.get_meta(fc.DEVICE).get_field("block_reason").options
		self.assertEqual(tuple(o for o in options.split("\n") if o), desk.BLOCK_REASONS)
		self.assertEqual(desk.BLOCKABLE, ("Active", "Pending", "Consent not given"))

	def test_013_the_employee_form_gets_its_section_and_the_scripts_are_wired(self):
		self.assertEqual(hooks.doctype_js.get("Employee"),
		                 ["public/js/alvoraa_qr.js", "public/js/employee_field_app.js"])
		self.assertIn("alvoraa_portal.field_app_desk.after_migrate", hooks.after_migrate)
		self.assertIn("alvoraa_portal.field_app_desk.after_migrate", hooks.after_install)
		root = os.path.dirname(fc.__file__)
		for rel in hooks.doctype_js["Employee"]:
			self.assertTrue(os.path.exists(os.path.join(root, rel)), rel)
		with open(os.path.join(root, "public", "js", "employee_field_app.js"), encoding="utf-8") as f:
			script = f.read()
		# AC-47: the QR is drawn in the browser; no "Copy link" (user decision).
		self.assertIn("AlvoraaQR.svg(", script)
		self.assertNotIn("Copy link", script)
		self.assertIn("silent: true", script)

		frappe.set_user("Administrator")
		self.assertTrue(desk.after_migrate())
		self.assertTrue(desk.after_migrate())     # safe twice
		for fieldname, insert_after in ((desk.F_SECTION, "holiday_list"),
		                                (desk.F_HTML, desk.F_SECTION)):
			row = frappe.db.get_value("Custom Field", {"dt": "Employee", "fieldname": fieldname},
			                          ["fieldtype", "insert_after"], as_dict=True)
			self.assertTrue(row, fieldname)
			self.assertEqual(row.insert_after, insert_after)
		self.assertEqual(frappe.db.get_value("Custom Field", {"dt": "Employee", "fieldname": desk.F_HTML},
		                                     "fieldtype"), "HTML")
		frappe.db.commit()

	def test_013_a_reading_is_not_required_for_the_section_to_answer(self):
		# A phone made straight into the table (a web phone) still shows.
		frappe.set_user("Administrator")
		doc, token = _new_phone(self.employee, "Active", join_method="Web check-in page")
		record_acknowledgement(self.employee, notice.CURRENT_VERSION, "Web check-in page",
		                       device=doc.name)
		frappe.db.commit()
		out = self.section()
		self.assertEqual(out["state"], "joined")
		self.assertEqual(out["phone"]["join_method"], "Web check-in page")
