"""Slice 013, step 6: housekeeping and proof. The daily clean-up, the daily
counts, the threshold alert, "what does the app hold about me?", the busy
depot, the privacy scan, migration twice, and rollback by the switch.

Every test here names the thing it keeps alive:

  * **US-21 / AC-126 to AC-130** - the daily job marks codes that ran out and
    retires their hash; runs twice with no change; counts a live secret on a
    stopped record and raises the technical alert; deletes codes that never set
    up a phone twelve months after they ended, permanently, and keeps Used
    codes; saves 500 rows a commit on the default queue. **Fail-without-fix
    recipe:** empty the body of `field_app_housekeeping.expire_codes` (return
    0) and `test_013_ac126_...` fails on "a code that ran out kept a live hash"
    - the code's status stays Waiting and its hash stays live. (E1 refuses an
    expired code by time even without the job - the step-3 check - so what the
    job adds is OPS-52: no live hash on a dead code, and the Ran out status HR
    sees.)
  * **US-22 / AC-131 to AC-134** - each outcome moves its counter by one; the
    day's row holds no name, ID, phone model, code or secret; rows older than
    13 months go; nobody writes a row by hand.
  * **US-19 / AC-120, AC-121** - N5: the threshold crossing sends one desk-bell
    alert to the tenant's HR Managers, once an hour, with the number and no
    code. **Fail-without-fix recipe:** delete the two lines in
    `field_app_housekeeping.record_outcome` that call `_bad_code_seen()` and
    `test_013_ac120_...` fails on "no N5 alert".
  * **US-28 / AC-153 (server half)** - the signed-in employee gets their own
    phones, codes, acknowledgements and punches; nothing secret; no way to
    name anyone else; ten calls an hour.
  * **US-25 / AC-140, AC-141** - 400 phones behind one address are 400 callers
    on E4 and E5; no per-IP limit sits on any device endpoint but the web
    page's registration; Redis limit keys hold the hash, never the secret.
  * **US-26 / AC-146, AC-147** - every refusal and a forced crash on every
    guest endpoint leave no code, secret, photo, position or name in the
    Error Log, Version rows, Notification Log, Redis or the response.
  * **US-29 / AC-157** - the three installers run twice and leave exactly one
    of each field.
  * **US-30 / AC-160, AC-161** - the switch off stops app phones and waiting
    codes with `APP_OFF_FOR_FIELD`; a web phone keeps working; the switch on
    restores the same phones with no new code.
  * **Section 6** - the whole rate-limit table, per endpoint, pinned.
"""

import json
import secrets
from typing import ClassVar
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, add_to_date, now, today

from alvoraa_portal import field_app_desk as desk
from alvoraa_portal import field_app_device as device_api
from alvoraa_portal import field_app_errors as errors
from alvoraa_portal import field_app_housekeeping as hk
from alvoraa_portal import field_app_join as join
from alvoraa_portal import field_app_notice as notice
from alvoraa_portal import field_app_records as records
from alvoraa_portal import field_app_settings as fas
from alvoraa_portal import field_checkin as fc
from alvoraa_portal import hooks
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_app_invite.alvoraa_app_invite import (
	INVITE,
	SERVER_FLAG,
)
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_field_app_daily_count.alvoraa_field_app_daily_count import (
	DAILY_COUNT,
)
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_notice_acknowledgement.alvoraa_notice_acknowledgement import (
	ACKNOWLEDGEMENT,
	record_acknowledgement,
)
from alvoraa_portal.tests.test_field_app_step1_013 import EMP_EMAIL, NAME_MARKER, _bin, _new_phone
from alvoraa_portal.tests.test_field_app_step2_013 import _employee, _user
from alvoraa_portal.tests.test_field_app_step3_013 import JoinCase, _clear_codes, _code_of, _FakeRequest
from alvoraa_portal.tests.test_field_app_step4_013 import JPEG_1PX, DailyCase

PHOTO_MARKER = "ZQXPHOTO013STEP6"
LAT_MARKER = "12.3456789"
LON_MARKER = "76.5432101"
LABEL_MARKER = "Zqxphone Model Six"

COUNTER_PREFIXES = ("alvoraa_fa", "rl:alvoraa_portal.field_")


def _clear_counters():
	for prefix in COUNTER_PREFIXES:
		frappe.cache.delete_keys(prefix)


def _keys(prefix):
	return [k.decode() if isinstance(k, bytes) else str(k) for k in frappe.cache.get_keys(prefix)]


def _seed_invite(employee, status, **values):
	"""A code record straight into the table (no controller): the shape the
	job has to clean up, including shapes the controller would never write."""
	doc = frappe.get_doc({
		"doctype": INVITE, "employee": employee, "status": status, "lifetime_hours": 1,
		"expires_at": values.pop("expires_at", add_to_date(now(), hours=-2)),
		"token_hash": values.pop("token_hash", fc._hash(secrets.token_urlsafe(32))),
		**values,
	})
	doc.flags[SERVER_FLAG] = True
	doc.db_insert()
	return doc.name


class Step6Case(DailyCase):
	"""The step-4 fixture (a listed field worker, the app on, one HR maker) plus
	a clean set of counters and daily-count rows for every test."""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		_clear_counters()
		frappe.db.delete(DAILY_COUNT, {"on_date": [">=", add_days(today(), -2)]})
		frappe.db.commit()
		frappe.set_user("Guest")

	def tearDown(self):
		frappe.local.request = None
		frappe.set_user("Administrator")
		_clear_counters()
		frappe.db.delete(DAILY_COUNT, {"on_date": [">=", add_days(today(), -2)]})
		frappe.db.commit()
		super().tearDown()

	def with_request(self, version=None):
		req = _FakeRequest()
		req.headers = {errors.VERSION_HEADER: version} if version else {}
		frappe.local.request = req
		frappe.local.request_ip = "203.0.113.9"

	def check(self, code, token=None):
		args = {"code": code}
		if token:
			args["token"] = token
		return self.call(join.check_code, args)


# ── US-21 · the daily clean-up ───────────────────────────────────────────────

class TheDailyCleanUp(Step6Case):

	def test_013_ac126_waiting_codes_past_their_lifetime_become_ran_out_with_the_hash_retired(self):
		out = self.make()
		code = _code_of(out)
		frappe.set_user("Administrator")
		frappe.db.set_value(INVITE, out["invite"], "expires_at", add_to_date(now(), hours=-1),
		                    update_modified=False)
		frappe.db.commit()

		result = hk.daily()
		self.assertFalse(result["failed"])
		self.assertEqual(result["codes_expired"], 1)
		row = self.invite(out["invite"])
		self.assertEqual(row.status, "Ran out")
		self.assertFalse(row.token_hash, "a code that ran out kept a live hash")
		self.assertEqual(row.retired_token_hash, fc._hash(code))
		# E1 still recognises it, and says so with its own code.
		frappe.set_user("Guest")
		self.assertIsNone(self.check(code))
		self.assertEqual(self.answer()[:2], (410, "QR_EXPIRED"))

	def test_013_ac127_running_the_job_twice_changes_nothing_and_logs_counts_only(self):
		out = self.make()
		frappe.set_user("Administrator")
		frappe.db.set_value(INVITE, out["invite"], "expires_at", add_to_date(now(), hours=-1),
		                    update_modified=False)
		frappe.db.commit()
		first = hk.daily()
		before = frappe.db.get_value(INVITE, out["invite"], ["status", "modified", "retired_token_hash"],
		                             as_dict=True)
		with mock.patch.object(frappe, "logger") as logger:
			second = hk.daily()
		after = frappe.db.get_value(INVITE, out["invite"], ["status", "modified", "retired_token_hash"],
		                            as_dict=True)
		self.assertEqual(before, after)
		self.assertEqual(first["codes_expired"], 1)
		self.assertEqual((second["codes_expired"], second["codes_deleted"], second["failed"]),
		                 (0, 0, False))
		# The log line: the job's name and numbers, nothing else.
		line = logger.return_value.info.call_args[0][0]
		self.assertTrue(line.startswith("field app clean-up: {"))
		for marker in (self.employee, NAME_MARKER, out["invite"]):
			self.assertNotIn(marker, line)

	def test_013_ac128_a_live_hash_on_a_stopped_record_is_counted_and_alerted(self):
		frappe.set_user("Administrator")
		started = now()
		# A cancelled code that somehow kept its hash, and a blocked phone likewise:
		# shapes the controllers never write, seeded straight into the tables.
		bad_code = _seed_invite(self.employee, "Cancelled", cancel_reason="By HR")
		phone, _token = _new_phone(self.employee, status="Active")
		frappe.db.set_value(fc.DEVICE, phone.name, "status", "Blocked", update_modified=False)
		frappe.db.commit()
		try:
			self.assertEqual(hk.live_hashes_on_stopped_records(), 2)
			result = hk.daily()
			self.assertEqual(result["live_hashes"], 2)
			alerts = frappe.get_all("Error Log", filters={"creation": [">=", started]},
			                        fields=["method", "error"])
			titles = [a.method for a in alerts if (a.method or "").startswith("Field app clean-up")]
			self.assertEqual(titles, ["Field app clean-up: 2 live secret(s) on stopped records"] * 2,
			                 "one alert per run, by title, with the count")
			for a in alerts:
				self.assertNotIn(NAME_MARKER, (a.error or "") + (a.method or ""))
			# and it lands on today's count row
			row = frappe.db.get_value(DAILY_COUNT, {"on_date": today()}, "live_hashes_found")
			self.assertEqual(row, 2)
		finally:
			frappe.set_user("Administrator")
			_bin(INVITE, bad_code)
			frappe.db.commit()

	def test_013_ac129_old_cancelled_and_ran_out_codes_go_permanently_and_used_codes_stay(self):
		frappe.set_user("Administrator")
		long_ago = add_to_date(now(), months=-13)
		recent = add_to_date(now(), months=-11)
		old_cancelled = _seed_invite(self.employee, "Cancelled", cancel_reason="By HR",
		                             cancelled_at=long_ago, token_hash=None,
		                             retired_token_hash="a" * 64)
		old_ran_out = _seed_invite(self.employee, "Ran out", expires_at=long_ago, token_hash=None,
		                           retired_token_hash="b" * 64)
		young_cancelled = _seed_invite(self.employee, "Cancelled", cancel_reason="By HR",
		                               cancelled_at=recent, token_hash=None,
		                               retired_token_hash="c" * 64)
		frappe.db.commit()
		frappe.set_user("Guest")
		# A Used code older than the cut-off, made the real way: it let a phone in.
		token = self.app_phone()
		used = frappe.db.get_value(fc.DEVICE, {"token_hash": fc._hash(token)}, "invite")
		frappe.set_user("Administrator")
		frappe.db.set_value(INVITE, used, {"used_at": long_ago, "expires_at": long_ago},
		                    update_modified=False)
		frappe.db.commit()

		result = hk.daily()
		self.assertEqual(result["codes_deleted"], 2, result)
		self.assertFalse(frappe.db.exists(INVITE, old_cancelled))
		self.assertFalse(frappe.db.exists(INVITE, old_ran_out))
		self.assertTrue(frappe.db.exists(INVITE, young_cancelled))
		self.assertEqual(frappe.db.get_value(INVITE, used, "status"), "Used")
		# Permanently: no copy of the row survives in Deleted Document.
		for name in (old_cancelled, old_ran_out):
			self.assertEqual(frappe.db.count("Deleted Document",
			                                 {"deleted_doctype": INVITE, "deleted_name": name}), 0)
		# and twice is the same
		self.assertEqual(hk.daily()["codes_deleted"], 0)

	def test_013_ac130_the_job_batches_five_hundred_a_commit_on_the_default_queue(self):
		self.assertEqual(hk.BATCH, 500)
		self.assertIn("alvoraa_portal.field_app_housekeeping.daily", hooks.scheduler_events["daily"])
		self.assertIn("alvoraa_portal.field_app_photos.purge_old_checkin_photos",
		              hooks.scheduler_events["daily"], "the photo purge must keep its own entry")
		job = frappe.new_doc("Scheduled Job Type")
		job.frequency = "Daily"
		self.assertEqual(job.get_queue_name(), "default")

		# More than two batches, seeded straight into the table, all expired.
		frappe.set_user("Administrator")
		names = [_seed_invite(self.employee, "Waiting") for _ in range(hk.BATCH * 2 + 100)]
		frappe.db.commit()
		try:
			with mock.patch.object(frappe.db, "commit", wraps=frappe.db.commit) as commit:
				expired = hk.expire_codes()
			self.assertEqual(expired, len(names))
			self.assertGreaterEqual(commit.call_count, 3, "one commit per batch of 500")
			self.assertEqual(frappe.db.count(INVITE, {"name": ["in", names], "status": "Ran out"}),
			                 len(names))
			self.assertEqual(frappe.db.count(INVITE, {"name": ["in", names],
			                                          "token_hash": ["is", "set"]}), 0)
		finally:
			frappe.set_user("Administrator")
			frappe.db.delete(INVITE, {"name": ["in", names]})
			frappe.db.commit()

	def test_013_a_failure_inside_the_job_is_a_titled_alert_with_no_values(self):
		started = now()
		with mock.patch.object(hk, "expire_codes", side_effect=RuntimeError("boom " + NAME_MARKER)):
			result = hk.daily()
		self.assertTrue(result["failed"])
		rows = frappe.get_all("Error Log", filters={"creation": [">=", started], "method": hk.JOB_FAILED_TITLE},
		                      fields=["error"])
		self.assertEqual(len(rows), 1)
		self.assertIn("RuntimeError", rows[0].error)
		self.assertNotIn(NAME_MARKER, rows[0].error)


# ── US-22 · the daily counts ─────────────────────────────────────────────────

class TheDailyCounts(Step6Case):

	def test_013_ac132_each_outcome_moves_its_counter_by_exactly_one(self):
		self.with_request("1.2.3")
		token = self.app_phone()
		self.status(token)                                       # E4 ok
		self.punch(token, accuracy="20", photo=JPEG_1PX)         # E5 ok
		self.punch(token, log_type="OUT", accuracy="900")        # E5 GPS_NOT_EXACT
		self.check("x" * 43)                                     # E1 QR_NOT_RECOGNISED
		self.remove(token)                                       # E6 ok
		self.with_request("0.0.1")
		self.status(token)                                       # APP_TOO_OLD

		counters = hk.counters_for(today())
		self.assertEqual(counters["field_status"]["ok"]["1.2.3"], 1)
		self.assertEqual(counters["field_checkin"]["ok"]["1.2.3"], 1)
		self.assertEqual(counters["field_checkin"]["GPS_NOT_EXACT"]["1.2.3"], 1)
		self.assertEqual(counters["check_code"]["QR_NOT_RECOGNISED"]["1.2.3"], 1)
		self.assertEqual(counters["remove_my_phone"]["ok"]["1.2.3"], 1)
		self.assertEqual(counters["field_status"]["APP_TOO_OLD"]["0.0.1"], 1)

		frappe.set_user("Administrator")
		hk.write_daily_counts(day=today())
		row = hk_row(today())
		self.assertEqual((row.app_starts, row.punches_saved, row.punches_refused,
		                  row.code_checks_refused, row.phones_removed, row.app_too_old),
		                 (1, 1, 1, 1, 1, 1))
		# The code columns come from the code table, so they count every
		# employee's codes made today - other modules may have left some.
		self.assertEqual(row.codes_made, frappe.db.count(INVITE, {"creation": [">=", today()]}))
		self.assertEqual(row.codes_used, frappe.db.count(INVITE, {"used_at": [">=", today()]}))
		self.assertGreaterEqual(row.codes_used, 1)
		self.assertEqual(json.loads(row.detail)["field_checkin"]["ok"]["1.2.3"], 1)

	def test_013_ac131_the_row_holds_no_name_id_model_code_or_secret(self):
		self.with_request("1.2.3")
		out = self.make()
		code = _code_of(out)
		answer = self.joined(code, device_label=LABEL_MARKER)
		token = answer["token"]
		self.punch(token, accuracy="20")
		frappe.set_user("Administrator")
		hk.write_daily_counts(day=today())
		row = json.dumps(hk_row(today()).as_dict(), default=str)
		for marker in (self.employee, NAME_MARKER, LABEL_MARKER, code, token, fc._hash(token),
		               fc._hash(code)):
			self.assertNotIn(marker, row)
		# and the counter keys themselves
		for key in _keys("alvoraa_fa"):
			for marker in (self.employee, NAME_MARKER, code, token):
				self.assertNotIn(marker, key)

	def test_013_a_bad_version_header_is_counted_as_bad_not_copied_into_the_row(self):
		self.with_request("1.2.3")
		token = self.app_phone()
		self.with_request("evil:header:value")
		self.status(token)   # APP_TOO_OLD, unparseable
		counters = hk.counters_for(today())
		self.assertEqual(counters["field_status"]["APP_TOO_OLD"], {"bad": 1})

	def test_013_ac134_rows_older_than_thirteen_months_go(self):
		frappe.set_user("Administrator")
		old = hk._upsert_count_row(add_months(today(), -14), {"punches_saved": 3})
		kept = hk._upsert_count_row(add_months(today(), -12), {"punches_saved": 4})
		try:
			self.assertEqual(hk.purge_old_counts(), 1)
			self.assertFalse(frappe.db.exists(DAILY_COUNT, old))
			self.assertTrue(frappe.db.exists(DAILY_COUNT, kept))
		finally:
			frappe.db.delete(DAILY_COUNT, {"name": ["in", [old, kept]]})
			frappe.db.commit()

	def test_013_nobody_writes_a_count_row_by_hand(self):
		meta = frappe.get_meta(DAILY_COUNT)
		for perm in meta.permissions:
			self.assertTrue(perm.get("read"))
			for action in ("create", "write", "delete", "email", "print", "share", "import"):
				self.assertFalse(perm.get(action), f"{perm.role} can {action} a count row")
		frappe.set_user("Administrator")
		doc = frappe.get_doc({"doctype": DAILY_COUNT, "on_date": add_days(today(), -400)})
		with self.assertRaises(frappe.PermissionError):
			doc.insert(ignore_permissions=True)
		frappe.db.rollback()
		name = hk._upsert_count_row(add_days(today(), -400), {})
		try:
			with self.assertRaises(frappe.PermissionError):
				frappe.delete_doc(DAILY_COUNT, name, ignore_permissions=True)
			frappe.db.rollback()
		finally:
			frappe.db.delete(DAILY_COUNT, {"name": name})
			frappe.db.commit()

	def test_013_counting_never_changes_an_answer_when_redis_is_unhappy(self):
		token = self.app_phone()
		with mock.patch.object(hk, "_bump", side_effect=RuntimeError("redis is away")):
			out = self.status(token)
		self.assertTrue(out and out.get("employee") == self.employee, self.words())


def hk_row(day):
	name = frappe.db.get_value(DAILY_COUNT, {"on_date": day}, "name")
	return frappe.get_doc(DAILY_COUNT, name)


# ── US-19 · N5, the threshold alert ─────────────────────────────────────────

class TheThresholdAlert(Step6Case):

	def test_013_ac120_ac121_the_crossing_sends_one_alert_an_hour_to_hr_managers_with_no_code(self):
		codes = ["y" * 43, "z" * 43]
		from frappe.utils import get_datetime
		fixed = get_datetime("2026-01-01 10:30:00")   # one clock hour, whatever the wall clock says
		with mock.patch.object(hk, "BAD_CODE_ALERT_THRESHOLD", 3), \
				mock.patch.object(hk, "now_datetime", return_value=fixed):
			for i in range(3):
				self.check(codes[i % 2])
			self.assertEqual(self.notifications(), [], "under the threshold, nothing")
			self.check(codes[0])                      # the 4th: the crossing
			rows = self.notifications()
			self.assertTrue(rows, "no N5 alert")
			self.assertEqual({r.subject for r in rows}, {"Many app codes that do not work were tried"})
			# Every enabled HR Manager on the site - the two of this fixture among
			# them - and never the employee.
			self.assertLessEqual({self.maker, self.hrm2}, {r.for_user for r in rows})
			self.assertNotIn(self.employee_user, {r.for_user for r in rows})
			for r in rows:
				self.assertIn("4 app codes that do not work were tried in the last hour", r.email_content)
				for bad in (codes[0], codes[1], "203.0.113", self.employee, NAME_MARKER):
					self.assertNotIn(bad, r.subject + r.email_content)
			self.check(codes[1])                      # the 5th: nothing more
			self.check(codes[0])
			self.assertEqual(len(self.notifications()), len(rows), "at most one an hour")

	def test_013_the_alert_module_itself_keeps_to_one_an_hour(self):
		frappe.set_user("Administrator")
		from alvoraa_portal import field_app_alerts as alerts
		alerts.too_many_bad_codes(51)
		frappe.db.commit()
		first = self.notifications()
		alerts.too_many_bad_codes(80)
		frappe.db.commit()
		self.assertGreaterEqual(len(first), 2, "one row per HR Manager")
		self.assertEqual(len(self.notifications()), len(first), "the second call, in the hour, sends nothing")
		self.assertTrue(all("51 app codes" in r.email_content for r in first))


# ── US-28 · what does the app hold about me? ────────────────────────────────

class WhatTheAppHoldsAboutMe(Step6Case):

	KEYS: ClassVar[set] = {"employee", "row_limit", "phones", "codes", "acknowledgements",
	                       "notice_words", "punches", "totals", "how_to_get_more"}

	def mine(self, user=None):
		"""As the employee's own sign-in (the step-1 fixture links EMP_EMAIL to
		the employee record), or as whoever `user` names."""
		frappe.set_user(user or EMP_EMAIL)
		try:
			frappe.local.response = frappe._dict()
			frappe.clear_messages()
			frappe.local.form_dict = frappe._dict(cmd="alvoraa_portal.field_app_records.my_field_app_records")
			return records.my_field_app_records()
		finally:
			frappe.set_user("Guest")

	def test_013_ac153_the_employee_sees_their_own_phones_codes_readings_and_punches(self):
		out = self.make()
		code = _code_of(out)
		token = self.joined(code, device_label=LABEL_MARKER)["token"]
		self.punch(token, accuracy="20", latitude=LAT_MARKER, longitude=LON_MARKER)

		mine = self.mine()
		self.assertEqual(set(mine), self.KEYS)
		self.assertEqual(mine["employee"], self.employee)
		self.assertEqual(len(mine["phones"]), 1)
		self.assertEqual(mine["phones"][0]["device_label"], LABEL_MARKER)
		self.assertEqual(mine["phones"][0]["status"], "Active")
		self.assertEqual([c["outcome"] for c in mine["codes"]], ["used"])
		self.assertEqual([a["notice_version"] for a in mine["acknowledgements"]], [notice.CURRENT_VERSION])
		self.assertIn(notice.CURRENT_VERSION, mine["notice_words"])
		self.assertEqual(len(mine["punches"]), 1)
		self.assertEqual(str(mine["punches"][0]["latitude"])[:7], LAT_MARKER[:7])
		self.assertEqual(mine["totals"], {"phones": 1, "codes": 1, "acknowledgements": 1, "punches": 1})

		text = json.dumps(mine, default=str)
		for secret in (code, token, fc._hash(code), fc._hash(token), "token_hash", "block_reason"):
			self.assertNotIn(secret, text)
		# never the workplace's coordinates, never the photo itself
		self.assertNotIn("workplace", text)
		self.assertNotIn("alvoraa_checkin_photo", text)

	def test_013_ac153_nobody_else_and_no_way_to_name_anyone_else(self):
		with self.assertRaises(frappe.PermissionError):
			self.mine("Guest")
		frappe.db.rollback()
		with self.assertRaises(frappe.PermissionError):
			self.mine(self.maker)     # an HR Manager with no employee record of their own
		frappe.db.rollback()
		with self.assertRaises(TypeError):
			frappe.set_user(EMP_EMAIL)
			records.my_field_app_records(employee=self.employee)
		frappe.set_user("Guest")
		frappe.db.rollback()

	def test_013_the_block_reason_never_reaches_the_person(self):
		token = self.app_phone()
		phone = frappe.db.get_value(fc.DEVICE, {"token_hash": fc._hash(token)}, "name")
		# Blocked from the desk, as Administrator (the fixture's HR maker holds
		# no company permission here; step 5 tests the HR path itself).
		frappe.set_user("Administrator")
		frappe.local.form_dict = frappe._dict(device=phone, reason="Someone else was using it",
		                                      cmd="alvoraa_portal.field_app_device.block_phone")
		device_api.block_phone(device=phone, reason="Someone else was using it")
		frappe.db.commit()
		mine = self.mine()
		self.assertEqual(mine["phones"][0]["status"], "Blocked")
		self.assertNotIn("Someone else", json.dumps(mine, default=str))

	def test_013_the_eleventh_call_in_an_hour_is_too_many(self):
		self.with_request()
		for _ in range(10):
			self.assertIsNotNone(self.mine(), self.words())
		self.assertIsNone(self.mine())
		self.assertEqual(self.answer()[:2], (429, "TOO_MANY_TRIES"))

	def test_013_it_is_a_post_only_gated_limited_call(self):
		self.assertIn("alvoraa_portal.field_app_records.my_field_app_records",
		              [f"{fn.__module__}.{fn.__name__}" for fn in frappe.whitelisted])
		self.assertNotIn(records.my_field_app_records, frappe.guest_methods)
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[records.my_field_app_records],
		                 ["POST"])
		self.assertEqual(_limit_of(records.my_field_app_records), ("self_user_key", "user", 10))


# ── US-25 · the busy depot ───────────────────────────────────────────────────

def _limit_of(fn):
	"""(field, source, limit) of the innermost limiter on this endpoint, or None."""
	found = None
	while fn is not None:
		if hasattr(fn, "__alvoraa_limit__"):
			found = fn.__alvoraa_limit__[:3]
		fn = getattr(fn, "__wrapped__", None)
	return found


def _has_frappe_ip_limiter(fn):
	"""Frappe's own `rate_limit` in the chain (the per-IP one), as opposed to ours."""
	from frappe.rate_limiter import rate_limit

	while fn is not None:
		code = getattr(fn, "__code__", None)
		if code is not None and code.co_filename == rate_limit.__code__.co_filename \
				and not hasattr(fn, "__alvoraa_limit__"):
			return True
		fn = getattr(fn, "__wrapped__", None)
	return False


class TheBusyDepot(Step6Case):

	# Section 6, and register_device (slice 014). (field, source, limit an hour)
	TABLE: ClassVar[dict] = {
		join.check_code: ("code_hash_key", "code", 20),
		join.refuse_code: ("code_hash_key", "code", 5),
		join.join_with_code: ("code_hash_key", "code", 5),
		join.acknowledge_notice: ("phone_hash_key", "token", 5),
		join.withdraw_agreement: ("phone_hash_key", "token", 5),
		fc.field_status: ("phone_hash_key", "token", 60),
		fc.field_checkin: ("phone_hash_key", "token", 30),
		device_api.remove_my_phone: ("phone_hash_key", "token", 5),
		join.make_code: ("hr_user_key", "user", 30),
		join.cancel_code: ("hr_user_key", "user", 30),
		device_api.block_phone: ("hr_user_key", "user", 30),
		records.my_field_app_records: ("self_user_key", "user", 10),
		desk.employee_app_section: None,
		fas.settings_info: None,
	}

	def test_013_every_endpoint_carries_the_limit_the_spec_gives_it(self):
		for fn, expected in self.TABLE.items():
			with self.subTest(endpoint=fn.__name__):
				self.assertEqual(_limit_of(fn), expected)
				self.assertFalse(_has_frappe_ip_limiter(fn),
				                 f"{fn.__name__} carries a per-IP limit; a depot shares one address")
		# The one per-IP limit that stays: the web page's registration (slice 014),
		# where the address is the only thing an attacker guessing employee IDs
		# cannot vary. Its own test pins it; here it is only named as the exception.
		self.assertTrue(_has_frappe_ip_limiter(fc.register_device))
		self.assertIsNone(_limit_of(fc.register_device))

	def test_013_ac140_four_hundred_phones_behind_one_address_are_not_refused(self):
		frappe.set_user("Administrator")
		tokens = []
		for _ in range(400):
			phone, token = _new_phone(self.employee, status="Active", join_method="App QR code")
			record_acknowledgement(self.employee, notice.CURRENT_VERSION, "App", device=phone.name)
			tokens.append(token)
		frappe.db.commit()
		frappe.set_user("Guest")
		self.with_request()
		statuses = set()
		for token in tokens:
			out = self.status(token)
			statuses.add(self.answer()[0] if out is None else 200)
			self.punch(token, accuracy="900")          # refused for GPS, never for the address
			statuses.add(self.answer()[0])
		self.assertEqual(statuses, {200, 422}, "a 429 here means a per-IP limit is back")

	def test_013_ac141_redis_limit_keys_hold_the_hash_never_the_secret(self):
		self.with_request()
		token = self.app_phone()
		self.status(token)
		keys = _keys("rl:")
		self.assertTrue(keys)
		for key in keys:
			self.assertNotIn(token, key)
		self.assertTrue(any(fc._hash(token) in k for k in keys))


# ── US-26 · nothing personal reaches a log ──────────────────────────────────

class NothingPersonalReachesALog(Step6Case):

	def setUp(self):
		super().setUp()
		self.started = now()

	def scan(self, *markers, alert_ok=()):
		"""Every place a value could have landed since the test started.
		`alert_ok` are the markers an HR alert is allowed to carry (a name, a
		phone model - section 10), checked everywhere but the Notification Log."""
		places = []
		for row in frappe.get_all("Error Log", filters={"creation": [">=", self.started]},
		                          fields=["name", "method", "error", "metadata"]):
			places.append((f"Error Log {row.name}", " ".join(str(row.get(f) or "") for f in ("method", "error", "metadata"))))
		for row in frappe.get_all("Version", filters={"creation": [">=", self.started]},
		                          fields=["name", "data"]):
			places.append((f"Version {row.name}", row.data or ""))
		for row in frappe.get_all("Notification Log", filters={"creation": [">=", self.started]},
		                          fields=["name", "subject", "email_content"]):
			places.append((f"Notification Log {row.name}", (row.subject or "") + (row.email_content or "")))
		places.append(("Redis keys", " ".join(_keys("rl:") + _keys("alvoraa_fa"))))
		places.append(("the response", json.dumps(frappe.local.response, default=str)))
		places.append(("the message log", json.dumps(frappe.local.message_log, default=str)))
		from frappe.utils.error import get_error_metadata
		places.append(("Frappe's error metadata", str(get_error_metadata())))
		for where, text in places:
			for marker in markers:
				if where.startswith("Notification Log") and marker in alert_ok:
					continue
				self.assertNotIn(marker, text, f"{marker!r} leaked into {where}")

	def test_013_ac147_every_refusal_path_leaves_no_code_secret_photo_position_or_name(self):
		self.with_request("1.2.3")
		code = _code_of(self.make())
		token = self.joined(code, device_label=LABEL_MARKER)["token"]
		dead_code = "Q" * 43
		dead_token = "T" * 43
		photo = "data:image/jpeg;base64," + PHOTO_MARKER
		refusals = [
			(join.check_code, {"code": dead_code, "token": dead_token}),
			(join.refuse_code, {"code": dead_code}),
			# A live code with an old notice version: NOTICE_CHANGED, whose
			# values carry the notice's rows - words, never a value of ours.
			(join.join_with_code, self.join_args(code, notice_version="1999-01-01",
			                                     device_label=LABEL_MARKER)),
			(join.acknowledge_notice, {"token": dead_token, "notice_version": "x"}),
			(join.withdraw_agreement, {"token": dead_token}),
			(fc.field_status, {"token": dead_token}),
			(fc.field_checkin, {"token": token, "log_type": "IN", "latitude": LAT_MARKER,
			                    "longitude": LON_MARKER, "accuracy": "900", "photo": photo}),
			(device_api.remove_my_phone, {"token": dead_token}),
		]
		for endpoint, args in refusals:
			with self.subTest(endpoint=endpoint.__name__):
				self.assertIsNone(self.call(endpoint, args))
				self.assertLess(self.answer()[0], 500, self.words())
				# The employee's name is allowed in an N2 alert to HR - it is the
				# whole point of that alert (AC-117) - so it is scanned separately.
				self.scan(code, dead_code, token, dead_token, PHOTO_MARKER, LAT_MARKER, LON_MARKER,
				          LABEL_MARKER, alert_ok=(LABEL_MARKER,))
		for row in frappe.get_all("Error Log", filters={"creation": [">=", self.started]},
		                          fields=["error", "metadata"]):
			self.assertNotIn(NAME_MARKER, (row.error or "") + (row.metadata or ""))

	def test_013_ac146_a_forced_crash_on_every_guest_endpoint_logs_a_place_and_nothing_else(self):
		self.with_request("1.2.3")
		code = _code_of(self.make())
		token = self.app_phone()
		photo = "data:image/jpeg;base64," + PHOTO_MARKER
		crashes = [
			(join.check_code, {"code": code}, join, "_live_invite"),
			(join.refuse_code, {"code": code}, join, "_live_invite"),
			(join.join_with_code, self.join_args(code, device_label=LABEL_MARKER), join, "_invite_by_code"),
			(join.acknowledge_notice, {"token": token, "notice_version": notice.CURRENT_VERSION},
			 join, "latest_version_for"),
			(join.withdraw_agreement, {"token": token}, join, "_phone_locked"),
			(fc.field_status, {"token": token}, fc, "_shift_location_for"),
			(fc.field_checkin, {"token": token, "log_type": "IN", "latitude": LAT_MARKER,
			                    "longitude": LON_MARKER, "accuracy": "8", "photo": photo},
			 fc, "_refuse_duplicate"),
			(device_api.remove_my_phone, {"token": token}, device_api, "_phone_locked"),
		]
		for endpoint, args, module, inner in crashes:
			with self.subTest(endpoint=endpoint.__name__):
				with mock.patch.object(module, inner, side_effect=RuntimeError("boom " + NAME_MARKER + code)):
					out = self.call(endpoint, args)
				self.assertIsNone(out)
				self.assertEqual(self.answer()[:2], (500, "SERVER_ERROR"))
				rows = [r for r in frappe.get_all("Error Log", filters={"creation": [">=", self.started]},
				                                  fields=["method", "error"], order_by="creation asc")
				        if (r.method or "").startswith(fc._SERVER_ERROR_TITLE)]
				self.assertTrue(rows, "the crash should be logged, as a place")
				self.assertIn("RuntimeError", rows[-1].error)
				self.assertIn(f"endpoint: {endpoint.__name__}", rows[-1].error)
				# The code's hash is allowed in the Version row the join wrote
				# (the retired hash IS the record); the code itself never is.
				self.scan(code, token, PHOTO_MARKER, LAT_MARKER, LON_MARKER, LABEL_MARKER, NAME_MARKER,
				          alert_ok=(LABEL_MARKER, NAME_MARKER))

	def test_013_every_guest_endpoint_is_wrapped_above_its_gate(self):
		for fn in (join.check_code, join.refuse_code, join.join_with_code, join.acknowledge_notice,
		           join.withdraw_agreement, fc.field_status, fc.field_checkin, fc.register_device,
		           device_api.remove_my_phone):
			with self.subTest(endpoint=fn.__name__):
				chain, f = [], fn
				while f is not None:
					chain.append(f)
					f = getattr(f, "__wrapped__", None)
				private = [i for i, f in enumerate(chain) if hasattr(f, "__alvoraa_private_request__")]
				gate = [i for i, f in enumerate(chain) if hasattr(f, "__alvoraa_feature__")]
				self.assertTrue(private and gate, fn.__name__)
				self.assertLess(private[-1], gate[-1], fn.__name__)
				self.assertIn(fn, frappe.guest_methods)


# ── US-29 · migration twice ─────────────────────────────────────────────────

class MigrationRunsTwice(FrappeTestCase):

	def test_013_ac157_the_installers_run_twice_and_leave_one_of_each_field(self):
		frappe.set_user("Administrator")
		before = {f: frappe.db.get_single_value(fas.SETTINGS, f, cache=False)
		          for f in (fas.F_ENABLED, fas.F_LIFETIME)}
		for _ in range(2):
			self.assertTrue(fc.after_migrate())
			self.assertTrue(fas.after_migrate())
			self.assertTrue(desk.after_migrate())
		frappe.db.commit()
		expected = {
			"Employee Checkin": ["alvoraa_checkin_photo", "alvoraa_gps_accuracy", "alvoraa_checkin_offline",
			                     "alvoraa_captured_at", "alvoraa_mock_location", "alvoraa_legal_hold",
			                     "alvoraa_field_device"],
			"HR Settings": [fas.F_TAB, fas.F_SECTION, fas.F_DESIGNATIONS, fas.F_SWITCH_SECTION,
			                fas.F_ENABLED, fas.F_LIFETIME, fas.F_REASON, fas.F_INFO_SECTION, fas.F_INFO],
			"Employee": [desk.F_SECTION, desk.F_HTML],
		}
		for doctype, fields in expected.items():
			for field in fields:
				with self.subTest(doctype=doctype, field=field):
					self.assertEqual(frappe.db.count("Custom Field", {"dt": doctype, "fieldname": field}), 1)
		after = {f: frappe.db.get_single_value(fas.SETTINGS, f, cache=False)
		         for f in (fas.F_ENABLED, fas.F_LIFETIME)}
		self.assertEqual(before, after, "a value the tenant saved was overwritten")
		for doctype in (INVITE, ACKNOWLEDGEMENT, DAILY_COUNT, fc.DEVICE):
			self.assertTrue(frappe.db.exists("DocType", doctype))


# ── US-30 · rollback by the switch ──────────────────────────────────────────

class RollbackByTheSwitch(Step6Case):

	def test_013_ac161_off_stops_app_phones_and_waiting_codes_web_phones_carry_on_and_on_restores(self):
		token = self.app_phone()
		waiting = _code_of(self.make())
		frappe.set_user("Administrator")
		web, web_token = _new_phone(self.employee, status="Active")
		frappe.db.commit()
		frappe.set_user("Guest")

		self.configure(0, [self.driver], self.driver)
		for endpoint, args in ((fc.field_status, {"token": token}),
		                       (fc.field_checkin, self.punch_args(token)),
		                       (join.check_code, {"code": waiting})):
			with self.subTest(endpoint=endpoint.__name__):
				self.assertIsNone(self.call(endpoint, args))
				self.assertEqual(self.answer()[:2], (403, "APP_OFF_FOR_FIELD"))
		self.assertIsNotNone(self.status(web_token), self.words())
		self.assertEqual((self.punch(web_token) or {}).get("status"), "ok", self.words())

		self.configure(1, [self.driver], self.driver)
		self.assertIsNotNone(self.status(token), self.words())
		self.assertEqual((self.punch(token, log_type="OUT") or {}).get("status"), "ok", self.words())
		self.assertIsNotNone(self.check(waiting), self.words())
		self.assertEqual(frappe.db.count(fc.DEVICE, {"employee": self.employee, "status": "Active",
		                                             "join_method": "App QR code"}), 1,
		                 "the same phone, no new code")

	def test_013_ac160_an_empty_designation_list_refuses_every_invite(self):
		self.configure(1, [], self.driver)
		self.assertIsNone(self.make())
		self.assertEqual(self.answer()[1], "NOT_FIELD_ROLE")
		frappe.db.rollback()
