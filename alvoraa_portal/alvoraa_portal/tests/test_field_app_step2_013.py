"""Slice 013, step 2: the organisation's switches, and who may see a phone.

Every test here names the thing it keeps alive:

  * **US-3** - the three settings on HR Settings: they install with safe
    defaults, HR Manager changes them and the change is recorded, HR User and
    an Employee cannot, turning the app off or dropping a designation needs a
    reason on every door, and a read that fails treats the app as off.
  * **APP_OFF_FOR_FIELD / NOT_FIELD_ROLE** - the two codes step 1 declared and
    nothing raised. An app phone is refused with them, a web phone is not, and
    restoring the setting restores the phone with no new code.
  * **C-11c** - an HR user limited to one company sees only that company's
    phones, by list, by has_permission and by check_permission. Before this
    step they saw every company's. Remove the two hook lines from hooks.py and
    the two-company test fails.
"""

import json
import secrets
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now

from alvoraa_goals.tests.utils import ensure_company, ensure_gender
from alvoraa_portal import field_app_errors as errors
from alvoraa_portal import field_app_notice as notice
from alvoraa_portal import field_app_settings as fas
from alvoraa_portal import field_checkin as fc
from alvoraa_portal import subscription as sub
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_field_device import (
	alvoraa_field_device as device_rules,
)
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_notice_acknowledgement.alvoraa_notice_acknowledgement import (
	record_acknowledgement,
)
from alvoraa_portal.tests.leave_fixtures import ensure_user
from alvoraa_portal.tests.test_field_app_step1_013 import FieldAppCase, _bin, _new_phone
from alvoraa_portal.tests.test_portal_security_010 import _second_company

TAG = "S013b"
DRIVER = "Zqx Driver 013"
CLERK = "Zqx Store Associate 013"


# ── fixtures ─────────────────────────────────────────────────────────────────

def _designation(name):
	if not frappe.db.exists("Designation", name):
		frappe.get_doc({"doctype": "Designation", "designation_name": name}).insert(
			ignore_permissions=True)
	return name


def _employee(first, company, designation=None, user=None):
	name = frappe.db.get_value("Employee", {"first_name": first, "last_name": TAG}, "name")
	doc = frappe.get_doc("Employee", name) if name else frappe.get_doc({
		"doctype": "Employee", "first_name": first, "last_name": TAG,
		"gender": ensure_gender(), "date_of_birth": "1990-01-01",
		"date_of_joining": "2025-01-01",
	})
	doc.company = company
	doc.status = "Active"
	doc.designation = designation
	doc.user_id = user
	doc.create_user_permission = 0
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	if user:
		frappe.db.delete("User Permission", {"user": user})
		frappe.clear_cache(user=user)
	frappe.db.commit()
	return doc.name


def _user(local, roles):
	user = ensure_user(f"s013b.{local}@example.com", roles=roles)
	frappe.db.set_value("User", user, "module_profile", None, update_modified=False)
	frappe.db.delete("Block Module", {"parent": user, "parenttype": "User"})
	frappe.db.delete("User Permission", {"user": user})
	frappe.clear_cache(user=user)
	frappe.db.commit()
	return user


def _company_permission(user, company):
	up = frappe.get_doc({"doctype": "User Permission", "user": user, "allow": "Company",
	                     "for_value": company, "apply_to_all_doctypes": 1})
	up.insert(ignore_permissions=True)
	frappe.clear_cache(user=user)
	frappe.db.commit()
	return up.name


class SettingsCase(FrappeTestCase):
	"""Remembers the tenant's field-app settings and puts them back afterwards."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.driver = _designation(DRIVER)
		cls.clerk = _designation(CLERK)
		cls.hr_manager = _user("hrm", ["HR Manager"])
		cls.hr_user = _user("hru", ["HR User"])
		cls.employee_user = _user("emp", ["Employee"])
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")
		self.started = now()
		self._saved = {
			f: frappe.db.get_single_value(fas.SETTINGS, f, cache=False)
			for f in (fas.F_ENABLED, fas.F_LIFETIME, fas.F_REASON)
		}
		self._saved_rows = fas.settings()["designations"]
		frappe.local.response = frappe._dict()
		frappe.clear_messages()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		for f, v in self._saved.items():
			frappe.db.set_single_value(fas.SETTINGS, f, v, update_modified=False)
		self._write_rows(self._saved_rows)
		# The Version rows these tests wrote on HR Settings are not a tenant's
		# history; take them away again.
		frappe.db.delete("Version", {"ref_doctype": fas.SETTINGS,
		                             "creation": [">=", self.started]})
		frappe.clear_document_cache(fas.SETTINGS, fas.SETTINGS)
		frappe.db.commit()
		frappe.local.form_dict = frappe._dict()
		frappe.local.response = frappe._dict()
		frappe.clear_messages()

	@staticmethod
	def _write_rows(designations):
		frappe.db.delete(fas.CHILD, {"parent": fas.SETTINGS, "parentfield": fas.F_DESIGNATIONS})
		for i, d in enumerate(designations, start=1):
			frappe.get_doc({"doctype": fas.CHILD, "parent": fas.SETTINGS,
			                "parenttype": fas.SETTINGS, "parentfield": fas.F_DESIGNATIONS,
			                "designation": d, "idx": i}).db_insert()

	# ── helpers ──────────────────────────────────────────────────────────────

	def put(self, enabled=None, lifetime=None, designations=None, reason=None, user=None,
	        version=True):
		"""Save HR Settings the way the desk and REST do: through the document."""
		frappe.set_user(user or "Administrator")
		try:
			doc = frappe.get_doc(fas.SETTINGS)
			if enabled is not None:
				doc.set(fas.F_ENABLED, enabled)
			if lifetime is not None:
				doc.set(fas.F_LIFETIME, lifetime)
			if designations is not None:
				doc.set(fas.F_DESIGNATIONS, [])
				for d in designations:
					doc.append(fas.F_DESIGNATIONS, {"designation": d})
			doc.set(fas.F_REASON, reason)
			doc.save(ignore_version=not version)
			frappe.db.commit()
			return doc
		finally:
			frappe.set_user("Administrator")

	def versions(self):
		rows = frappe.get_all("Version", filters={"ref_doctype": fas.SETTINGS,
		                                          "creation": [">=", self.started]},
		                      fields=["owner", "data"], order_by="creation desc")
		return [(r.owner, json.loads(r.data)) for r in rows]

	def stored(self, field):
		return frappe.db.get_single_value(fas.SETTINGS, field, cache=False)


# ── US-3 · install ───────────────────────────────────────────────────────────

class TheSettingsInstallSafely(SettingsCase):

	def test_013_ac14_a_site_that_never_stored_a_value_gets_the_defaults(self):
		"""On, 1 day, nobody. And every other HR Settings value stays as it was."""
		def others():
			# `Singles` is a table, not a DocType, so get_all cannot read it.
			return frappe.db.sql(
				"select field, value from tabSingles where doctype=%s and field not in %s "
				"order by field", (fas.SETTINGS, fas.TRACKED_FIELDS))

		others_before = others()
		frappe.db.delete("Singles", {"doctype": fas.SETTINGS,
		                             "field": ["in", [fas.F_ENABLED, fas.F_LIFETIME]]})
		self._write_rows([])
		frappe.db.commit()

		self.assertTrue(fas.after_migrate())
		self.assertTrue(fas.after_migrate(), "the installer is not safe to run twice")

		current = fas.settings()
		self.assertEqual(current, {"enabled": True, "designations": [], "lifetime": "1 day",
		                           "lifetime_hours": 24, "readable": True})
		self.assertEqual(others_before, others(), "the installer touched another setting")

	def test_013_ac14_a_value_the_tenant_saved_is_never_overwritten(self):
		self.put(enabled=0, lifetime="3 days", reason="Pausing the pilot")
		self.assertTrue(fas.after_migrate())
		self.assertEqual(fas.settings()["enabled"], False)
		self.assertEqual(fas.settings()["lifetime"], "3 days")

	def test_013_the_fields_are_on_hr_settings(self):
		meta = frappe.get_meta(fas.SETTINGS)
		for f in (fas.F_DESIGNATIONS, fas.F_ENABLED, fas.F_LIFETIME, fas.F_REASON, fas.F_INFO):
			self.assertTrue(meta.has_field(f), f)
		self.assertEqual(meta.get_field(fas.F_DESIGNATIONS).options, fas.CHILD)
		self.assertEqual(sorted(fas.LIFETIME_HOURS), sorted(
			meta.get_field(fas.F_LIFETIME).options.split("\n")))
		self.assertEqual(max(fas.LIFETIME_HOURS.values()), 7 * 24,
		                 "the user's decision: at most 7 days")
		self.assertEqual(fas.LIFETIME_HOURS[fas.DEFAULT_LIFETIME], 24,
		                 "the user's decision: 24 hours by default")
		self.assertTrue(frappe.get_meta(fas.CHILD).istable)

	def test_013_both_validate_hooks_are_registered_and_one_save_passes_both(self):
		"""alvoraa_goals validates its own fields on the same Single."""
		hooks = frappe.get_hooks("doc_events").get(fas.SETTINGS, {}).get("validate", [])
		self.assertIn("alvoraa_portal.field_app_settings.validate_hr_settings", hooks)
		if "alvoraa_goals" in frappe.get_installed_apps():
			self.assertIn("alvoraa_goals.review_items.validate_hr_settings", hooks)
		self.put(lifetime="4 hours")
		self.assertEqual(self.stored(fas.F_LIFETIME), "4 hours")


# ── US-3 · who changes them, and how ─────────────────────────────────────────

class WhoMayChangeThem(SettingsCase):

	def test_013_ac15_hr_manager_saves_and_the_change_is_recorded(self):
		self.put(lifetime="1 day")
		self.put(lifetime="3 days", user=self.hr_manager)
		self.assertEqual(self.stored(fas.F_LIFETIME), "3 days")
		owner, data = self.versions()[0]
		self.assertEqual(owner, self.hr_manager)
		self.assertIn([fas.F_LIFETIME, "1 day", "3 days"], data.get("changed", []))

	def test_013_ac16_hr_user_and_employee_cannot_save_these_fields(self):
		before = self.stored(fas.F_LIFETIME)
		for user in (self.hr_user, self.employee_user):
			with self.subTest(user=user):
				self.assertFalse(frappe.has_permission(fas.SETTINGS, "write", user=user))
				with self.assertRaises(frappe.PermissionError):
					self.put(lifetime="7 days", user=user)
				frappe.db.rollback()
				self.assertEqual(self.stored(fas.F_LIFETIME), before)

	def test_013_ac17_turning_the_app_off_needs_a_reason_on_every_door(self):
		self.put(enabled=1)
		with self.assertRaises(frappe.ValidationError) as caught:
			self.put(enabled=0)
		self.assertIn("Choose a reason", str(caught.exception))
		frappe.db.rollback()

		from frappe.client import set_value
		with self.assertRaises(frappe.ValidationError):
			set_value(fas.SETTINGS, fas.SETTINGS, fas.F_ENABLED, 0)
		frappe.db.rollback()
		self.assertEqual(fas.settings()["enabled"], True, "a refused save changed the switch")

	def test_013_ac18_removing_a_designation_needs_a_reason(self):
		self.put(designations=[self.driver])
		# adding needs no reason
		self.put(designations=[self.driver, self.clerk])
		self.assertEqual(sorted(fas.settings()["designations"]), sorted([self.driver, self.clerk]))

		with self.assertRaises(frappe.ValidationError):
			self.put(designations=[self.clerk])
		frappe.db.rollback()
		self.assertEqual(sorted(fas.settings()["designations"]), sorted([self.driver, self.clerk]))

		self.put(designations=[self.clerk], reason="Other")
		self.assertEqual(fas.settings()["designations"], [self.clerk])

	def test_013_ac19_the_reason_is_kept_in_the_history_and_emptied_afterwards(self):
		self.put(enabled=1)
		doc = self.put(enabled=0, reason="Pausing the pilot", user=self.hr_manager)
		self.assertIsNone(doc.get(fas.F_REASON), "the returned document still held the reason")
		self.assertFalse(self.stored(fas.F_REASON), "the reason was not emptied after the save")
		self.assertEqual(fas.settings()["enabled"], False)
		owner, data = self.versions()[0]
		self.assertEqual(owner, self.hr_manager)
		changed = {f: (o, n) for f, o, n in data.get("changed", [])}
		self.assertEqual(changed.get(fas.F_REASON, (None, None))[1], "Pausing the pilot")
		self.assertIn(fas.F_ENABLED, changed)

	def test_013_ac20_a_lifetime_outside_the_six_options_is_refused(self):
		before = self.stored(fas.F_LIFETIME)
		from frappe.client import set_value
		for bad in ("90 days", "2 days", "0", "forever"):
			with self.subTest(bad=bad):
				with self.assertRaises(frappe.ValidationError):
					set_value(fas.SETTINGS, fas.SETTINGS, fas.F_LIFETIME, bad)
				frappe.db.rollback()
		self.assertEqual(self.stored(fas.F_LIFETIME), before)

	def test_013_a_reason_outside_the_list_is_refused(self):
		"""The history is readable by every Employee-role user, so it can never
		hold free text."""
		with self.assertRaises(frappe.ValidationError):
			self.put(enabled=0, reason="Because Suresh was rude")
		frappe.db.rollback()


# ── US-3 · what the settings decide ──────────────────────────────────────────

class WhoIsAFieldWorker(SettingsCase):

	def refusal(self, designation):
		try:
			fas.refuse_unless_eligible(designation)
		except errors.FieldAppRefusal as e:
			return e.alvoraa_code, e.alvoraa_values
		return None

	def test_013_ac21_only_a_listed_designation_is_a_field_worker(self):
		self.put(enabled=1, designations=[self.driver])
		self.assertIsNone(self.refusal(self.driver))
		self.assertEqual(self.refusal(self.clerk), ("NOT_FIELD_ROLE", {"designation": self.clerk}))
		self.assertEqual(self.refusal(None), ("NOT_FIELD_ROLE", {"designation": ""}))

	def test_013_ac21_an_empty_list_means_nobody(self):
		self.put(enabled=1, designations=[])
		self.assertEqual(self.refusal(self.driver)[0], "NOT_FIELD_ROLE")

	def test_013_ac21_when_the_settings_cannot_be_read_nobody_is_eligible(self):
		"""Fail closed: a broken read is "off", never "on"."""
		self.put(enabled=1, designations=[self.driver])
		with mock.patch.object(frappe.db, "get_single_value", side_effect=Exception("db down")):
			current = fas.settings()
			self.assertEqual((current["enabled"], current["designations"], current["readable"]),
			                 (False, [], False))
			self.assertEqual(self.refusal(self.driver)[0], "APP_OFF_FOR_FIELD")

	def test_013_the_switch_is_asked_before_the_list(self):
		"""A switched-off tenant answers the same for everybody, so it never
		says who is on the list."""
		self.put(designations=[self.driver])
		self.put(enabled=0, reason="Other")
		self.assertEqual(self.refusal(self.driver)[0], "APP_OFF_FOR_FIELD")
		self.assertEqual(self.refusal(self.clerk)[0], "APP_OFF_FOR_FIELD")

	def test_013_ac22_a_change_is_read_on_the_very_next_call(self):
		"""No cache anywhere in the read path. The cross-process proof was step
		1's; this pins that nobody adds a cache later."""
		self.put(enabled=1, designations=[self.driver])
		self.assertTrue(fas.settings()["enabled"])
		self.put(enabled=0, reason="Pausing the pilot")
		self.assertFalse(fas.settings()["enabled"])
		self.put(enabled=1)
		self.assertTrue(fas.settings()["enabled"])
		self.put(lifetime="7 days")
		self.assertEqual(fas.settings()["lifetime_hours"], 168)


# ── US-3 · what the screen is told ───────────────────────────────────────────

class WhatTheScreenShows(SettingsCase):

	def info(self, designations=None, user="Administrator"):
		frappe.set_user(user)
		try:
			self._features = frappe.conf.get("features")
			frappe.conf["features"] = list(sub.FEATURES)
			return fas.settings_info(json.dumps(designations) if designations is not None else None)
		finally:
			if self._features is None:
				frappe.conf.pop("features", None)
			else:
				frappe.conf["features"] = self._features
			frappe.set_user("Administrator")

	def test_013_ac23_the_retention_line_is_the_notice_s_own(self):
		self.assertEqual(self.info()["retention_line"], notice.retention_line())
		self.assertIn("Check-in photos are kept", notice.retention_line(45))
		self.assertIn("45 days", notice.retention_line(45))
		self.assertIn("until your organisation removes them", notice.retention_line(0))

	def test_013_ac24_the_history_lists_our_changes_newest_first_with_the_reason(self):
		self.put(enabled=1, lifetime="1 day", designations=[])
		self.put(lifetime="3 days", user=self.hr_manager)
		self.put(designations=[self.driver], user=self.hr_manager)
		self.put(enabled=0, reason="Pausing the pilot", user=self.hr_manager)

		info = self.info()
		self.assertEqual(info["history_note"], "HR cannot change this list.")
		history = [h for h in info["history"] if h["when"] >= self.started]
		self.assertGreaterEqual(len(history), 3)
		self.assertEqual(history[0]["reason"], "Pausing the pilot")
		self.assertIn("Field workers can use the app: on → off", history[0]["lines"])
		self.assertIn(f"Field worker designations: added {self.driver}", history[1]["lines"])
		self.assertIn("App codes work for: 1 day → 3 days", history[2]["lines"])
		for h in history:
			self.assertTrue(h["who"])
		self.assertLessEqual(len(info["history"]), fas.HISTORY_LIMIT)

	def test_013_ac25_the_employee_count_matches_the_database(self):
		emp = _employee("Countme", ensure_company(), designation=self.driver)
		try:
			expected = frappe.db.count("Employee", {"status": "Active", "designation": self.driver})
			info = self.info([self.driver])
			self.assertEqual(info["employees_with_designations"], expected)
			self.assertEqual(info["per_designation"][self.driver]["employees"], expected)
			self.assertEqual(self.info([])["employees_with_designations"], 0)
		finally:
			frappe.db.set_value("Employee", emp, "designation", None, update_modified=False)

	def test_013_ac17_the_counts_are_the_database_counts_and_only_app_phones_count(self):
		emp = _employee("Phoney", ensure_company(), designation=self.driver)
		phones = []
		try:
			app, _t = _new_phone(emp, "Active")
			frappe.db.set_value(fc.DEVICE, app.name, "join_method", "App QR code",
			                    update_modified=False)
			web, _t = _new_phone(emp, "Active")
			phones = [app.name, web.name]
			frappe.db.commit()
			info = self.info([self.driver])
			self.assertEqual(info["active_app_phones"],
			                 frappe.db.count(fc.DEVICE, {"status": "Active",
			                                             "join_method": "App QR code"}))
			self.assertEqual(info["per_designation"][self.driver]["phones"], 1,
			                 "a web phone was counted as one the switch will stop")
			self.assertEqual(info["waiting_codes"], 0)
		finally:
			for p in phones:
				_bin(fc.DEVICE, p)
			frappe.db.set_value("Employee", emp, "designation", None, update_modified=False)
			frappe.db.commit()

	def test_013_the_screen_data_is_hr_s_only_and_carries_no_names(self):
		with self.assertRaises(frappe.PermissionError):
			self.info(user=self.employee_user)
		body = json.dumps(self.info(user=self.hr_user))
		for leak in ("employee_name", "token", "@example.com"):
			self.assertNotIn(leak, body)
		for bad in ("not json", json.dumps("x"), json.dumps(["a"] * 201), json.dumps([1])):
			with self.subTest(bad=bad):
				with self.assertRaises(frappe.ValidationError):
					self.info(bad)

	def test_013_the_screen_data_is_behind_the_plan_gate(self):
		chain, f = [], fas.settings_info
		while f is not None:
			chain.append(f)
			f = getattr(f, "__wrapped__", None)
		self.assertTrue(any(getattr(x, "__alvoraa_feature__", None) == "field_checkin"
		                    for x in chain))


# ── the two codes nothing raised before ──────────────────────────────────────

class AnAppPhoneObeysTheSettings(FieldAppCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.driver = _designation(DRIVER)
		cls.clerk = _designation(CLERK)
		cls._saved = {f: frappe.db.get_single_value(fas.SETTINGS, f, cache=False)
		              for f in (fas.F_ENABLED, fas.F_LIFETIME)}
		cls._saved_rows = fas.settings()["designations"]
		cls._saved_designation = frappe.db.get_value("Employee", cls.employee, "designation")
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for f, v in cls._saved.items():
			frappe.db.set_single_value(fas.SETTINGS, f, v, update_modified=False)
		SettingsCase._write_rows(cls._saved_rows)
		frappe.db.set_value("Employee", cls.employee, "designation", cls._saved_designation,
		                    update_modified=False)
		frappe.db.commit()
		super().tearDownClass()

	def configure(self, enabled, designations, employee_designation):
		frappe.set_user("Administrator")
		frappe.db.set_single_value(fas.SETTINGS, fas.F_ENABLED, enabled, update_modified=False)
		SettingsCase._write_rows(designations)
		frappe.db.set_value("Employee", self.employee, "designation", employee_designation,
		                    update_modified=False)
		frappe.db.commit()
		frappe.set_user("Guest")

	def app_phone(self):
		"""An Active app phone, the way one exists in production: with a reading
		of the current notice. Since step 4 an app phone whose latest reading is
		not the current version is refused NOTICE_CHANGED at E4 and E5 (AC-80),
		so a phone made here without one would be testing that rule, not the
		switch."""
		phone, token = _new_phone(self.employee, "Active")
		frappe.db.set_value(fc.DEVICE, phone.name, "join_method", "App QR code",
		                    update_modified=False)
		record_acknowledgement(self.employee, notice.CURRENT_VERSION, "App", device=phone.name)
		frappe.db.commit()
		return phone, token

	def test_013_app_off_for_field_is_raised_at_e4_and_e5_and_writes_nothing(self):
		phone, token = self.app_phone()
		self.configure(0, [self.driver], self.driver)
		before = self.checkin_count()

		self.call(fc.field_status, {"token": token})
		self.assertEqual(self.answer(), (403, "APP_OFF_FOR_FIELD", {}))
		self.assertIn("not switched on for field staff", self.words())

		self.call(fc.field_checkin, self.punch_args(token))
		self.assertEqual(self.answer()[:2], (403, "APP_OFF_FOR_FIELD"))
		self.assertEqual(self.checkin_count(), before, "a refused phone wrote a punch")

	def test_013_not_field_role_carries_the_designation_and_nothing_else(self):
		phone, token = self.app_phone()
		self.configure(1, [self.driver], self.clerk)
		before = self.checkin_count()

		self.call(fc.field_checkin, self.punch_args(token))
		self.assertEqual(self.answer(), (403, "NOT_FIELD_ROLE", {"designation": self.clerk}))
		self.assertEqual(self.checkin_count(), before)
		body = json.dumps(dict(frappe.local.response))
		self.assertNotIn(self.driver, body, "the allowed list leaked to the phone")

		self.call(fc.field_status, {"token": token})
		self.assertEqual(self.answer()[:2], (403, "NOT_FIELD_ROLE"))

	def test_013_ac78_restoring_the_setting_restores_the_phone_with_no_new_code(self):
		phone, token = self.app_phone()
		row_before = frappe.db.get_value(fc.DEVICE, phone.name,
		                                 ["status", "modified", "token_hash"], as_dict=True)

		self.configure(0, [self.driver], self.driver)
		self.call(fc.field_status, {"token": token})
		self.assertEqual(self.answer()[1], "APP_OFF_FOR_FIELD")

		self.configure(1, [self.driver], self.driver)
		out = self.call(fc.field_status, {"token": token})
		self.assertEqual((out or {}).get("employee"), self.employee, self.words())

		row_after = frappe.db.get_value(fc.DEVICE, phone.name,
		                                ["status", "modified", "token_hash"], as_dict=True)
		self.assertEqual(row_before, row_after, "the refusal changed the phone row")

	def test_013_a_web_phone_keeps_working_while_the_app_is_off(self):
		"""Section 3.5: the settings are about the app. The web check-in page is
		how everybody else still marks attendance."""
		_, token = _new_phone(self.employee, "Active")    # join_method: web
		self.configure(0, [], self.clerk)
		before = self.checkin_count()
		out = self.call(fc.field_checkin, self.punch_args(token))
		self.assertEqual((out or {}).get("status"), "ok", self.words())
		self.assertEqual(self.checkin_count(), before + 1)

	def test_013_an_eligible_app_phone_still_punches(self):
		"""The control case."""
		_, token = self.app_phone()
		self.configure(1, [self.driver], self.driver)
		before = self.checkin_count()
		out = self.call(fc.field_checkin, self.punch_args(token))
		self.assertEqual((out or {}).get("status"), "ok", self.words())
		self.assertEqual(self.checkin_count(), before + 1)


# ── C-11c · who may see a phone ──────────────────────────────────────────────

class AnHrUserSeesOnlyTheirCompanysPhones(FrappeTestCase):
	"""Pinned to the exact arrangement the step-1 probe used: two companies, an
	HR User and an HR Manager each limited to the second one by a Company User
	Permission, one Active phone in each company. Before this step both users
	listed both phones."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.company_b = _second_company()
		cls.company_a = ensure_company()
		cls.emp_a = _employee("Alpha", cls.company_a)
		cls.emp_b = _employee("Beta", cls.company_b)
		cls.hr_user = _user("scope.hru", ["HR User"])
		cls.hr_manager = _user("scope.hrm", ["HR Manager"])
		cls.hr_nowhere = _user("scope.nowhere", ["HR User"])
		cls.sysman = _user("scope.sm", ["System Manager"])
		cls.perms = [_company_permission(cls.hr_user, cls.company_b),
		             _company_permission(cls.hr_manager, cls.company_b)]
		cls.phone_a, _t = _new_phone(cls.emp_a, "Active")
		cls.phone_b, _t = _new_phone(cls.emp_b, "Active")
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for p in (cls.phone_a, cls.phone_b):
			_bin(fc.DEVICE, p.name)
		for up in cls.perms:
			frappe.delete_doc("User Permission", up, force=True, ignore_permissions=True)
		frappe.db.commit()
		super().tearDownClass()

	def tearDown(self):
		frappe.set_user("Administrator")

	def listed_by(self, user):
		frappe.set_user(user)
		return set(frappe.get_list(fc.DEVICE, pluck="name",
		                           filters={"name": ["in", [self.phone_a.name, self.phone_b.name]]}))

	def test_013_ac149_a_company_limited_hr_user_and_hr_manager_see_one_company(self):
		for user in (self.hr_user, self.hr_manager):
			with self.subTest(user=user):
				self.assertEqual(self.listed_by(user), {self.phone_b.name},
				                 "the other company's phone was listed")

				a = frappe.get_doc(fc.DEVICE, self.phone_a.name)
				b = frappe.get_doc(fc.DEVICE, self.phone_b.name)
				self.assertFalse(frappe.has_permission(fc.DEVICE, "read", doc=a, user=user))
				self.assertTrue(frappe.has_permission(fc.DEVICE, "read", doc=b, user=user))

				frappe.set_user(user)
				with self.assertRaises(frappe.PermissionError):
					frappe.get_doc(fc.DEVICE, self.phone_a.name).check_permission("read")
				frappe.get_doc(fc.DEVICE, self.phone_b.name).check_permission("read")

	def test_013_a_system_manager_sees_every_company(self):
		self.assertEqual(self.listed_by(self.sysman), {self.phone_a.name, self.phone_b.name})
		for p in (self.phone_a, self.phone_b):
			self.assertTrue(frappe.has_permission(
				fc.DEVICE, "read", doc=frappe.get_doc(fc.DEVICE, p.name), user=self.sysman))

	def test_013_hr_with_no_company_and_no_employee_record_sees_nothing(self):
		"""Fails closed, the way every HR endpoint in the product already does."""
		self.assertEqual(self.listed_by(self.hr_nowhere), set())
		self.assertFalse(frappe.has_permission(
			fc.DEVICE, "read", doc=frappe.get_doc(fc.DEVICE, self.phone_b.name),
			user=self.hr_nowhere))

	def test_013_the_two_hooks_are_registered(self):
		"""So a bad merge that drops the hooks.py lines fails here, by name."""
		self.assertIn("alvoraa_portal.field_app_access.device_query_conditions",
		              frappe.get_hooks("permission_query_conditions").get(fc.DEVICE, []))
		self.assertIn("alvoraa_portal.field_app_access.device_has_permission",
		              frappe.get_hooks("has_permission").get(fc.DEVICE, []))


# ── the codes table did not move ─────────────────────────────────────────────

class TheTwoCodesAreStillInTheTable(FrappeTestCase):

	def test_013_the_two_codes_keep_their_status_and_values(self):
		self.assertEqual(errors.CODES["APP_OFF_FOR_FIELD"], (403, ()))
		self.assertEqual(errors.CODES["NOT_FIELD_ROLE"], (403, ("designation",)))

	def test_013_the_child_table_is_classified_as_tenant_side(self):
		self.assertIn(fas.CHILD, sub.TENANT_DOCTYPES)

	def test_013_a_random_secret_is_still_not_a_phone(self):
		"""Nothing in step 2 may have widened what a secret nobody holds gets."""
		frappe.set_user("Guest")
		try:
			frappe.local.response = frappe._dict()
			frappe.clear_messages()
			frappe.local.form_dict = frappe._dict(token=secrets.token_urlsafe(32),
			                                      cmd="alvoraa_portal.field_checkin.field_status")
			features = frappe.conf.get("features")
			frappe.conf["features"] = list(sub.FEATURES)
			try:
				fc.field_status(token=frappe.local.form_dict.token)
			finally:
				if features is None:
					frappe.conf.pop("features", None)
				else:
					frappe.conf["features"] = features
			self.assertEqual(frappe.local.response.get("code"), "DEVICE_PENDING")
		finally:
			frappe.set_user("Administrator")
			frappe.local.form_dict = frappe._dict()
			frappe.local.response = frappe._dict()
			frappe.clear_messages()
