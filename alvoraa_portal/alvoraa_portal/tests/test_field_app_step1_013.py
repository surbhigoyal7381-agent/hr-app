"""Slice 013, step 1: the phone's state, the phone record's rules, and the codes.

Every test here names the thing it keeps alive. Step 1 closes holes that are
open in production-shaped code today - HR can re-point a phone at another
employee, switch a blocked one back on, and delete the record - so a bad merge
that dropped any of it would be worse than not having built it.

Four groups:

  * **US-1** - only an Active phone punches. Everything else gets its own code
    and writes no `Employee Checkin` row. A Pending phone and a secret nobody
    holds must be indistinguishable.
  * **US-2** - the phone record cannot be forged, re-pointed, unblocked or
    deleted, through any of the five doors into that table.
  * **US-4** - the code table is the contract an old app build relies on.
  * **US-23** - a leaver's phone actually stops, with its secret retired. This
    one is a bug fix: the hook used to write straight to the table and skip
    every rule above.
"""

import json
import secrets
from typing import ClassVar

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now

from alvoraa_portal import field_app_errors as errors
from alvoraa_portal import field_app_notice as notice
from alvoraa_portal import field_checkin as fc
from alvoraa_portal import subscription as sub
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_field_device import (
	alvoraa_field_device as device_rules,
)

EMP_EMAIL = "zqx.fieldapp013@example.com"
NAME_MARKER = "Zqxthirteen"


def _company():
	return frappe.db.get_value("Company", {}, "name")


def _new_phone(employee, status="Active", token=None, **extra):
	"""A phone record the way server code makes one."""
	token = token or secrets.token_urlsafe(32)
	doc = frappe.get_doc({
		"doctype": fc.DEVICE,
		"employee": employee,
		"status": status,
		"join_method": "Web check-in page",
		"token_hash": fc._hash(token),
		**extra,
	})
	doc.flags[device_rules.SERVER_FLAG] = True
	doc.insert(ignore_permissions=True)
	return doc, token


def _bin(doctype, name):
	frappe.delete_doc(doctype, name, force=True, ignore_permissions=True,
	                  ignore_on_trash=True)


class FieldAppCase(FrappeTestCase):
	"""One Active employee, and a clean request for each test."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.employee = cls._employee()
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		cls._clear_phones()
		frappe.db.commit()
		super().tearDownClass()

	@classmethod
	def _clear_phones(cls):
		# The readings first: they link the phones (the doctype arrived in step 3,
		# and step 2's fixture writes one since step 4).
		if frappe.db.exists("DocType", "Alvoraa Notice Acknowledgement"):
			for name in frappe.get_all("Alvoraa Notice Acknowledgement",
			                           {"employee": cls.employee}, pluck="name"):
				_bin("Alvoraa Notice Acknowledgement", name)
		for name in frappe.get_all("Employee Checkin", {"employee": cls.employee},
		                           pluck="name"):
			for f in frappe.get_all("File", {"attached_to_doctype": "Employee Checkin",
			                                 "attached_to_name": name}, pluck="name"):
				_bin("File", f)
			_bin("Employee Checkin", name)
		for name in frappe.get_all(fc.DEVICE, {"employee": cls.employee}, pluck="name"):
			_bin(fc.DEVICE, name)

	@classmethod
	def _employee(cls):
		existing = frappe.db.get_value("Employee", {"user_id": EMP_EMAIL, "status": "Active"})
		if existing:
			return existing
		if not frappe.db.exists("User", EMP_EMAIL):
			frappe.get_doc({"doctype": "User", "email": EMP_EMAIL,
			                "first_name": NAME_MARKER,
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		return frappe.get_doc({
			"doctype": "Employee", "first_name": NAME_MARKER, "company": _company(),
			"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "user_id": EMP_EMAIL,
		}).insert(ignore_permissions=True).name

	def setUp(self):
		frappe.set_user("Administrator")
		self._clear_phones()
		frappe.db.commit()
		frappe.set_user("Guest")
		self._features = frappe.conf.get("features")
		frappe.conf["features"] = list(sub.FEATURES)
		frappe.local.response = frappe._dict()
		frappe.clear_messages()

	def tearDown(self):
		if self._features is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = self._features
		frappe.local.form_dict = frappe._dict()
		frappe.local.response = frappe._dict()
		frappe.clear_messages()
		frappe.set_user("Administrator")

	# ── helpers ──────────────────────────────────────────────────────────────

	def call(self, endpoint, args):
		frappe.local.response = frappe._dict()
		frappe.clear_messages()
		frappe.local.form_dict = frappe._dict(
			args, cmd=f"alvoraa_portal.field_checkin.{endpoint.__name__}")
		return endpoint(**args)

	def answer(self):
		"""The refusal as the app would read it: status, code, values."""
		r = frappe.local.response
		return (r.get("http_status_code"), r.get("code"), r.get("values"))

	def words(self):
		return " ".join(m.get("message", "") if isinstance(m, dict) else str(m)
		                for m in frappe.local.message_log)

	def punch_args(self, token, **overrides):
		args = {"token": token, "log_type": "IN",
		        "latitude": "12.9", "longitude": "77.6", "accuracy": "8"}
		args.update(overrides)
		return args

	def checkin_count(self):
		return frappe.db.count("Employee Checkin", {"employee": self.employee})


# ── US-1 · only an Active phone punches ──────────────────────────────────────

class OnlyAnActivePhonePunches(FieldAppCase):

	def test_013_ac1_pending_phone_and_unknown_secret_are_indistinguishable(self):
		"""AC-1. If these two answers differ, this endpoint becomes a way to ask
		"does this employee exist" one call after registration refused to."""
		_, pending_token = _new_phone(self.employee, "Pending")
		unknown_token = secrets.token_urlsafe(32)
		before = self.checkin_count()

		self.call(fc.field_status, {"token": pending_token})
		pending = (dict(frappe.local.response), self.words())

		self.call(fc.field_status, {"token": unknown_token})
		unknown = (dict(frappe.local.response), self.words())

		self.assertEqual(pending[0], unknown[0], "the bodies differ")
		self.assertEqual(pending[1], unknown[1], "the sentences differ")
		# Two empty sentences are also "the same". The first run passed this
		# way while the web page's sentence was missing altogether, so the pin
		# now insists the sentence is there.
		self.assertIn("waiting for HR", pending[1], "the refusal carried no sentence")
		self.assertEqual(pending[0].get("http_status_code"), 401)
		self.assertEqual(pending[0].get("code"), "DEVICE_PENDING")

		self.call(fc.field_checkin, self.punch_args(pending_token))
		self.assertEqual(self.answer()[:2], (401, "DEVICE_PENDING"))
		self.assertEqual(self.checkin_count(), before, "a Pending phone wrote a punch")

	def test_013_ac2_every_stopped_state_has_its_own_code_and_writes_nothing(self):
		"""AC-2. And a blocked phone is never told why."""
		before = self.checkin_count()
		expected = {
			"Blocked": (403, "DEVICE_BLOCKED", ()),
			"Replaced": (403, "DEVICE_REPLACED", ("replaced_at",)),
			"Removed": (403, "DEVICE_REMOVED", ("removed_at",)),
			"Consent not given": (403, "CONSENT_REQUIRED", ("version",)),
		}
		for status, (http, code, value_names) in expected.items():
			with self.subTest(status=status):
				phone, token = _new_phone(self.employee, "Active")
				phone.status = status
				if status == "Blocked":
					phone.block_reason = "Someone else was using it"
				phone.flags[device_rules.SERVER_FLAG] = True
				phone.save(ignore_permissions=True)
				frappe.db.commit()

				self.call(fc.field_checkin, self.punch_args(token))
				status_code, got_code, values = self.answer()
				self.assertEqual((status_code, got_code), (http, code))
				self.assertEqual(sorted(values or {}), sorted(value_names))
				self.assertEqual(self.checkin_count(), before)

				body = json.dumps(dict(frappe.local.response)) + self.words()
				for leak in ("Someone else was using it", "block_reason", "reason"):
					self.assertNotIn(leak, body,
					                 f"{status}: the block reason reached the phone")
				_bin(fc.DEVICE, phone.name)

	def test_013_ac3_a_missing_or_short_secret_is_not_set_up(self):
		for token in (None, "", "short"):
			with self.subTest(token=token):
				self.call(fc.field_status, {"token": token})
				self.assertEqual(self.answer()[:2], (401, "NOT_SET_UP"))

	def test_013_ac4_no_status_may_be_added_without_a_refusal_for_it(self):
		"""AC-4. Reads the Select options off the doctype and fails if somebody
		adds a state the refusal table has never heard of. A new state that
		silently fell through to "allowed" would let a stopped phone punch."""
		options = [o.strip() for o in
		           frappe.get_meta(fc.DEVICE).get_field("status").options.split("\n")
		           if o.strip()]
		self.assertIn("Active", options)
		for status in options:
			if status in ("Active", "Pending"):
				continue    # Active is the allowed one; Pending has its own answer
			self.assertIn(status, fc._REFUSAL_FOR_STATUS,
			              f"status {status!r} has no named refusal")
			code = fc._REFUSAL_FOR_STATUS[status][0]
			self.assertIn(code, errors.CODES, f"{status!r} refuses with an unknown code")

	def test_013_ac5_stopping_a_phone_retires_its_secret_in_the_same_save(self):
		for status in ("Blocked", "Replaced", "Removed"):
			with self.subTest(status=status):
				phone, token = _new_phone(self.employee, "Active")
				live = phone.token_hash
				phone.status = status
				if status == "Blocked":
					phone.block_reason = "Phone lost or stolen"
				phone.flags[device_rules.SERVER_FLAG] = True
				phone.save(ignore_permissions=True)

				after = frappe.db.get_value(
					fc.DEVICE, phone.name,
					["token_hash", "retired_token_hash", "status_changed_on"],
					as_dict=True)
				self.assertFalse(after.token_hash, "the live secret was not emptied")
				self.assertEqual(after.retired_token_hash, live)
				self.assertTrue(after.status_changed_on)

				# the old secret still gets its own code, never a 200
				self.call(fc.field_status, {"token": token})
				self.assertGreaterEqual(self.answer()[0], 400)
				self.assertNotEqual(self.answer()[1], "NOT_SET_UP")
				_bin(fc.DEVICE, phone.name)

	def test_013_ac6_an_active_phone_still_punches(self):
		"""The control case. If this ever fails, everything above is meaningless
		because nobody can mark attendance at all."""
		_, token = _new_phone(self.employee, "Active")
		before = self.checkin_count()
		out = self.call(fc.field_checkin, self.punch_args(token))
		self.assertEqual((out or {}).get("status"), "ok",
		                 f"an Active phone was refused: {self.words()}")
		self.assertEqual(self.checkin_count(), before + 1)


# ── US-2 · the phone record's own rules ──────────────────────────────────────

class ThePhoneRecordCannotBeForged(FieldAppCase):

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

	def test_013_ac7_a_stopped_phone_is_never_switched_back_on(self):
		"""AC-7, through the document and through frappe.client.set_value, which
		is the door a list bulk edit and a REST PUT both come in by."""
		for status in ("Blocked", "Replaced", "Removed"):
			for target in ("Active", "Pending"):
				with self.subTest(status=status, target=target):
					phone, _t = _new_phone(self.employee, "Active")
					phone.status = status
					if status == "Blocked":
						phone.block_reason = "Other"
					phone.flags[device_rules.SERVER_FLAG] = True
					phone.save(ignore_permissions=True)
					frappe.db.commit()
					before = frappe.db.get_value(
						fc.DEVICE, phone.name, ["status", "modified", "token_hash"],
						as_dict=True)

					doc = frappe.get_doc(fc.DEVICE, phone.name)
					doc.status = target
					with self.assertRaises(frappe.ValidationError):
						doc.save(ignore_permissions=True)
					frappe.db.rollback()

					from frappe.client import set_value
					with self.assertRaises(Exception):
						set_value(fc.DEVICE, phone.name, "status", target)
					frappe.db.rollback()

					after = frappe.db.get_value(
						fc.DEVICE, phone.name, ["status", "modified", "token_hash"],
						as_dict=True)
					self.assertEqual(after, before, "a refused save still changed the row")
					_bin(fc.DEVICE, phone.name)

	def test_013_ac8_hr_cannot_create_or_delete_a_phone_record(self):
		"""AC-8. Checked as a permission, because that is what stops the desk
		form, the list view, Data Import and REST in one place."""
		meta = frappe.get_meta(fc.DEVICE)
		for perm in meta.permissions:
			self.assertFalse(perm.get("create"), f"{perm.role} can create a phone record")
			self.assertFalse(perm.get("delete"), f"{perm.role} can delete a phone record")
			# C-7 (user decision, 2026-09-19): a phone record says who carries
			# which phone. Nobody emails, prints or shares one.
			for action in ("email", "print", "share"):
				self.assertFalse(perm.get(action),
				                 f"{perm.role} can {action} a phone record")

		# and the controller says so too, for Administrator and for a script
		doc = frappe.get_doc({"doctype": fc.DEVICE, "employee": self.employee,
		                      "status": "Pending", "token_hash": "x" * 64})
		with self.assertRaises(frappe.PermissionError):
			doc.insert(ignore_permissions=True)
		frappe.db.rollback()

		phone, _t = _new_phone(self.employee, "Active")
		frappe.db.commit()
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc(fc.DEVICE, phone.name, force=True, ignore_permissions=True)
		frappe.db.rollback()
		self.assertTrue(frappe.db.exists(fc.DEVICE, phone.name))
		_bin(fc.DEVICE, phone.name)

	def test_013_ac9_and_ac13_the_frozen_fields_are_frozen(self):
		other = frappe.db.get_value(
			"Employee", {"status": "Active", "name": ["!=", self.employee]}, "name")
		phone, _t = _new_phone(self.employee, "Active")
		frappe.db.commit()

		changes = {
			"join_method": "App QR code",
			"registered_on": "2020-01-01 00:00:00",
			"token_hash": "y" * 64,
			"retired_token_hash": "z" * 64,
		}
		if other:
			changes["employee"] = other

		for field, value in changes.items():
			with self.subTest(field=field):
				doc = frappe.get_doc(fc.DEVICE, phone.name)
				doc.set(field, value)
				with self.assertRaises((frappe.ValidationError, frappe.PermissionError)):
					doc.save(ignore_permissions=True)
				frappe.db.rollback()
		_bin(fc.DEVICE, phone.name)

	def test_013_ac10_hr_switches_on_a_waiting_web_phone(self):
		phone, _t = _new_phone(self.employee, "Pending")
		doc = frappe.get_doc(fc.DEVICE, phone.name)
		doc.status = "Active"
		doc.save(ignore_permissions=True)

		row = frappe.db.get_value(
			fc.DEVICE, phone.name,
			["status", "activated_by", "status_changed_on", "status_changed_by",
			 "status_change_source"], as_dict=True)
		self.assertEqual(row.status, "Active")
		self.assertEqual(row.activated_by, frappe.session.user)
		self.assertEqual(row.status_changed_by, frappe.session.user)
		self.assertEqual(row.status_change_source, "HR")
		self.assertTrue(row.status_changed_on)
		_bin(fc.DEVICE, phone.name)

	def test_013_ac11_a_block_has_to_say_why(self):
		phone, _t = _new_phone(self.employee, "Active")
		frappe.db.commit()  # the rollback below must not take the phone with it
		doc = frappe.get_doc(fc.DEVICE, phone.name)
		doc.status = "Blocked"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)
		frappe.db.rollback()

		doc = frappe.get_doc(fc.DEVICE, phone.name)
		doc.status = "Blocked"
		doc.block_reason = "Has a new phone"
		doc.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value(fc.DEVICE, phone.name, "status"), "Blocked")
		_bin(fc.DEVICE, phone.name)

	def test_013_ac12_a_person_cannot_set_replaced_removed_or_go_back_to_pending(self):
		for target in ("Replaced", "Removed", "Consent not given", "Pending"):
			with self.subTest(target=target):
				phone, _t = _new_phone(self.employee, "Active")
				doc = frappe.get_doc(fc.DEVICE, phone.name)
				doc.status = target
				with self.assertRaises(frappe.ValidationError):
					doc.save(ignore_permissions=True)
				frappe.db.rollback()
				_bin(fc.DEVICE, phone.name)

	def test_013_a_code_phone_is_not_switched_on_from_the_desk(self):
		"""A phone that joined with HR's code was already approved by whoever made
		the code. Nobody approves it twice, and nobody uses this door to switch on
		a phone the app parked."""
		phone, _t = _new_phone(self.employee, "Pending")
		frappe.db.set_value(fc.DEVICE, phone.name, "join_method", "App QR code",
		                    update_modified=False)
		doc = frappe.get_doc(fc.DEVICE, phone.name)
		doc.status = "Active"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)
		frappe.db.rollback()
		_bin(fc.DEVICE, phone.name)


# ── US-23 · a leaver's phone actually stops ──────────────────────────────────

class ALeaversPhoneStops(FieldAppCase):
	"""The point of US-23. `block_devices_for_leaver` used to write straight to
	the table with `update_modified=False`, which skips `validate` and
	`on_update` - so every rule above fired for every phone except a leaver's.

	This test leaves an employee for real, through the Employee document and its
	own hook, and then asks whether the secret was retired. On the old code it
	fails."""

	def test_013_ac135_leaving_stops_every_phone_and_retires_its_secret(self):
		frappe.set_user("Administrator")
		active, active_token = _new_phone(self.employee, "Active")
		pending, pending_token = _new_phone(self.employee, "Pending")
		live_hashes = {active.name: active.token_hash, pending.name: pending.token_hash}
		frappe.db.commit()

		emp = frappe.get_doc("Employee", self.employee)
		emp.status = "Left"
		emp.relieving_date = now()
		emp.save(ignore_permissions=True)
		frappe.db.commit()

		try:
			for name, live in live_hashes.items():
				row = frappe.db.get_value(
					fc.DEVICE, name,
					["status", "block_reason", "token_hash", "retired_token_hash",
					 "status_changed_on", "status_changed_by"], as_dict=True)
				self.assertEqual(row.status, "Blocked", f"{name} was not blocked")
				self.assertEqual(row.block_reason, "Left the company")
				self.assertFalse(row.token_hash, f"{name} kept a live secret")
				self.assertEqual(row.retired_token_hash, live,
				                 f"{name}: the old secret was not kept")
				self.assertTrue(row.status_changed_on)
				self.assertEqual(row.status_changed_by, "Administrator")

			# and neither secret opens anything any more
			frappe.set_user("Guest")
			for token in (active_token, pending_token):
				self.call(fc.field_status, {"token": token})
				self.assertEqual(self.answer()[:2], (403, "DEVICE_BLOCKED"))
		finally:
			frappe.set_user("Administrator")
			emp = frappe.get_doc("Employee", self.employee)
			emp.status = "Active"
			emp.relieving_date = None
			emp.save(ignore_permissions=True)
			frappe.db.commit()

	def test_013_ac136_a_rehire_does_not_re_arm_the_old_phone(self):
		frappe.set_user("Administrator")
		phone, token = _new_phone(self.employee, "Active")
		frappe.db.commit()

		emp = frappe.get_doc("Employee", self.employee)
		emp.status = "Left"
		emp.relieving_date = now()
		emp.save(ignore_permissions=True)
		emp = frappe.get_doc("Employee", self.employee)
		emp.status = "Active"
		emp.relieving_date = None
		emp.save(ignore_permissions=True)
		frappe.db.commit()

		self.assertEqual(frappe.db.get_value(fc.DEVICE, phone.name, "status"), "Blocked")
		frappe.set_user("Guest")
		self.call(fc.field_status, {"token": token})
		self.assertEqual(self.answer()[:2], (403, "DEVICE_BLOCKED"))


# ── US-4 · the contract an old app build relies on ───────────────────────────

class TheCodeTableIsTheContract(FrappeTestCase):

	# The table as 02-functional-spec.md §7.1 froze it. This copy is the pin: if
	# a code's status or its value names move, an app already in somebody's
	# pocket shows the wrong screen, so the change has to be deliberate enough to
	# edit this list too.
	FROZEN: ClassVar[dict] = {
		"QR_NOT_RECOGNISED": (404, ()),
		"QR_EXPIRED": (410, ("expired_at",)),
		"QR_USED": (410, ("used_at",)),
		"QR_CANCELLED": (410, ()),
		"APP_OFF_FOR_FIELD": (403, ()),
		"NOT_FIELD_ROLE": (403, ("designation",)),
		"FEATURE_OFF": (403, ()),
		"NOTICE_CHANGED": (409, ("version", "rows", "retention_days", "what_changed")),
		"CONSENT_REQUIRED": (403, ("version",)),
		"APP_TOO_OLD": (426, ("min_version",)),
		"NOT_SET_UP": (401, ()),
		"DEVICE_PENDING": (401, ()),
		"DEVICE_BLOCKED": (403, ()),
		"DEVICE_REPLACED": (403, ("replaced_at",)),
		"DEVICE_REMOVED": (403, ("removed_at",)),
		"EMPLOYEE_NOT_ACTIVE": (403, ()),
		"LOCATION_MISSING": (422, ()),
		"GPS_NOT_EXACT": (422, ("accuracy_m", "limit_m")),
		"OUTSIDE_WORKPLACE": (422, ("distance_m", "site", "radius_m")),
		"ALREADY_RECORDED": (409, ("time",)),
		"INVALID_REQUEST": (400, ()),
		"TOO_MANY_TRIES": (429, ("retry_after_s",)),
		"SERVER_ERROR": (500, ()),
	}

	def test_013_ac26_no_code_changes_its_status_or_its_values(self):
		for code, (status, values) in self.FROZEN.items():
			with self.subTest(code=code):
				self.assertIn(code, errors.CODES, f"{code} was removed")
				self.assertEqual(errors.CODES[code], (status, tuple(values)))

	def test_013_a_code_is_never_removed(self):
		"""Codes are only ever added, for the life of a supported app version."""
		self.assertEqual(set(self.FROZEN) - set(errors.CODES), set(),
		                 "a code the app relies on was removed")

	def test_013_a_refusal_carries_only_the_values_its_code_declared(self):
		with self.assertRaises(errors.FieldAppRefusal) as caught:
			errors.refuse("DEVICE_BLOCKED", "stopped",
			              reason="Phone lost or stolen", replaced_at="2026-01-01")
		self.assertEqual(caught.exception.alvoraa_values, {},
		                 "a value the code never declared was about to be sent")

	def test_013_ac29_the_app_version_header(self):
		cases = {
			"1.0.0": None,           # exactly the minimum: allowed
			"1.10.0": None,          # newer than 1.9.0, which a string compare gets wrong
			"0.9.9": "APP_TOO_OLD",
			"abc": "APP_TOO_OLD",
			"1.2": "APP_TOO_OLD",
			"a" * 25: "APP_TOO_OLD",
		}
		self.assertEqual(errors.MIN_APP_VERSION, "1.0.0")
		for sent, expected in cases.items():
			with self.subTest(sent=sent):
				self.assertEqual(
					errors.parse_version(sent) is not None
					and errors.parse_version(sent) >= errors.parse_version(
						errors.MIN_APP_VERSION),
					expected is None)

	def test_013_the_plan_gate_still_marks_itself(self):
		"""The entitlement tests walk every endpoint looking for this attribute.
		A gate nobody can see is a gate nobody can check."""
		for fn in (fc.field_checkin, fc.field_status, fc.register_device):
			chain, f = [], fn
			while f is not None:
				chain.append(f)
				f = getattr(f, "__wrapped__", None)
			self.assertTrue(any(getattr(x, "__alvoraa_feature__", None) == "field_checkin"
			                    for x in chain), fn.__name__)

	def test_013_subscription_requires_feature_was_not_touched(self):
		"""28 vendor endpoints and the goals, analytics and payroll endpoints
		share this decorator, and slice 016 has only just settled them."""
		import inspect
		source = inspect.getsource(sub.requires_feature)
		self.assertIn("is not included in your plan", source)
		self.assertNotIn("FEATURE_OFF", source)


# ── the notice's words, pinned ───────────────────────────────────────────────

class TheNoticeSaysWhatItSaid(FrappeTestCase):
	"""A pin on the exact words of the current version, not a ban on particular
	vocabulary. Which words are right is the user's decision and counsel's; this
	test only stops them changing quietly."""

	VERSION = "2026-09-13"

	ROWS: ClassVar[list] = [
		("What we record",
		 "A photo of you, where you are, and the time — only when you press "
		 "Check In or Check Out."),
		("What we do not record",
		 "Nothing between punches. You are not tracked while you work."),
		("Why",
		 "To mark your attendance, and to confirm you were at your workplace."),
		("Who can see it",
		 "HR and your manager. Not your colleagues."),
		("How long", None),
		("Your rights",
		 "Ask HR to see what was recorded about you, or to correct it."),
	]

	AGREE = "I have read this and I understand."

	def test_013_the_current_notice_reads_exactly_this(self):
		self.assertEqual(notice.CURRENT_VERSION, self.VERSION)
		self.assertEqual(notice.NOTICE[self.VERSION]["rows"], self.ROWS)
		self.assertEqual(notice.agree_wording(), self.AGREE)

	def test_013_a_published_version_is_never_edited(self):
		"""If the words change, add a version. Somebody who agreed on Monday
		agreed to Monday's words, and a record naming a version whose text has
		been rewritten answers nothing."""
		self.assertIn(self.VERSION, notice.NOTICE)

	def test_013_the_web_page_and_the_store_say_the_same_thing(self):
		"""Step 1 leaves the web page exactly as it was (AC-35), so for now the
		page holds its own copy of these words. This test stops the two drifting
		before step 3 makes the page read the store."""
		import os

		import alvoraa_portal
		path = os.path.join(os.path.dirname(alvoraa_portal.__file__), "www",
		                    "field-checkin.html")
		with open(path, encoding="utf-8") as f:
			page = f.read()

		for heading, body in self.ROWS:
			self.assertIn(heading, page, f"the page lost the heading {heading!r}")
			if body:
				self.assertIn(body, page, f"the page and the store differ on {heading!r}")
		self.assertIn(self.AGREE, page)

	def test_013_the_retention_line_is_not_versioned(self):
		"""It quotes the tenant's own setting, which the tenant may change
		without a new notice version."""
		rows = notice.rows_for(retention_days=45)
		self.assertIn("45 days", rows[4]["body"])
		forever = notice.rows_for(retention_days=0)
		self.assertIn("until your organisation removes them", forever[4]["body"])


# ── the split did not move anything ──────────────────────────────────────────

class EveryOldImportPathStillResolves(FrappeTestCase):
	"""`hooks.py`, the web page and the browser all call these at
	`alvoraa_portal.field_checkin.<name>`. A path in a hook or a browser URL is a
	promise, so the split re-exports every one of them."""

	NAMES = (
		"purge_old_checkin_photos", "photo_retention_days", "_setting",
		"checkin_query_conditions", "checkin_has_permission", "log_photo_view",
		"app_icon", "manifest", "service_worker",
		"after_migrate", "block_devices_for_leaver", "notice_facts",
		"MAX_PHOTO_BYTES", "JPEG_MAGIC", "CONSENT_VERSION", "DEVICE",
	)

	def test_013_the_names_hooks_py_uses_are_still_there(self):
		for name in self.NAMES:
			self.assertTrue(hasattr(fc, name), f"{name} disappeared in the split")

	def test_013_every_hook_path_in_hooks_py_resolves(self):
		import os
		import re

		import alvoraa_portal
		path = os.path.join(os.path.dirname(alvoraa_portal.__file__), "hooks.py")
		with open(path, encoding="utf-8") as f:
			text = f.read()
		paths = set(re.findall(r"alvoraa_portal\.field_(?:checkin|app_\w+?)\.\w+", text))
		self.assertTrue(paths, "no field check-in hook paths found at all")
		for dotted in sorted(paths):
			with self.subTest(dotted=dotted):
				self.assertTrue(callable(frappe.get_attr(dotted)), dotted)

	def test_013_the_three_guest_endpoints_are_still_whitelisted(self):
		for fn in (fc.app_icon, fc.manifest, fc.service_worker,
		           fc.field_checkin, fc.field_status, fc.register_device):
			self.assertIn(fn, frappe.whitelisted, fn.__name__)
			self.assertIn(fn, frappe.guest_methods, fn.__name__)
