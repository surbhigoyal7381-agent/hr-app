"""Slice 013, step 4: daily use. The app opens, the person punches, the person
removes their phone.

Every test here names the thing it keeps alive:

  * **US-12** - E4 answers an app phone with the keys section 6 lists and no
    workplace coordinates; it writes nothing; a switched-off app, a changed
    notice, a leaver and a phone that has not agreed each get their own code.
    The web check-in page's answer keeps its `work_location` block (AC-35).
  * **US-13** - E5 saves one `Employee Checkin` with the accuracy, the phone,
    the fake-location flag and a private photo; a vague fix (worse than 50 m),
    a missing fix, a punch outside the radius and a second punch inside the
    window are refused with their own codes and write nothing. **The duplicate
    guard has a fail-without-fix recipe**: delete the `_refuse_duplicate(device,
    log_type)` call in `field_checkin` and `test_013_ac86_a_second_punch_inside_
    the_window_is_refused` fails, because both punches then save. (Taking only
    the `time` filter out does NOT make it fail - the guard then refuses on any
    earlier punch of the same kind, which is stricter, not weaker.)
  * **Minimum radius** - a Shift Location cannot be saved with a radius under
    100 m; 0 still means "no radius".
  * **US-15** - E6 removes the phone, retires its secret, erases nothing, and
    a stopped phone is answered with its own code.
  * **Section 6 limits** - 60, 30 and 5 an hour per phone, keyed on the hash.
"""

import json
import time

import frappe
from frappe.utils import add_days, nowdate

from alvoraa_portal import field_app_device as device_api
from alvoraa_portal import field_app_errors as errors
from alvoraa_portal import field_app_join as join
from alvoraa_portal import field_app_notice as notice
from alvoraa_portal import field_checkin as fc
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_field_device import (
	alvoraa_field_device as device_rules,
)
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_notice_acknowledgement.alvoraa_notice_acknowledgement import (
	ACKNOWLEDGEMENT,
)
from alvoraa_portal.tests.test_field_app_step1_013 import _bin, _new_phone
from alvoraa_portal.tests.test_field_app_step3_013 import (
	OLD_VERSION,
	JoinCase,
	_code_of,
	_FakeRequest,
)

# A 1x1 JPEG. The server checks the JPEG magic bytes and the size, not the picture.
JPEG_1PX = ("data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEB"
            "AgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/yQALCAABAAEBAREA/8wABgAQ"
            "EAX/2gAIAQEAAD8A0s8g/9k=")

# The depot, and two places near it: about 380 m north (outside a 100 m
# radius) and about 10 m north (inside it).
DEPOT_LAT, DEPOT_LON = 28.6519, 77.1906
FAR = {"latitude": "28.6553", "longitude": "77.1906"}
NEAR = {"latitude": "28.6520", "longitude": "77.1906"}

SHIFT = "Zqx Field Day 013"
DEPOT = "Zqx Depot 013"

E4_KEYS = {"employee", "employee_name", "first_name", "designation", "company",
           "checked_in", "todays_checkins", "server_time", "workplace",
           "min_version", "notice_version", "joined_on"}


class DailyCase(JoinCase):
	"""An eligible field worker with an app phone that joined through E3."""

	def call(self, endpoint, args):
		frappe.local.response = frappe._dict()
		frappe.clear_messages()
		frappe.local.form_dict = frappe._dict(
			args, cmd=f"{endpoint.__module__}.{endpoint.__name__}")
		out = endpoint(**args)
		frappe.db.commit()
		return out

	def app_phone(self, agreed=1):
		"""Join with a fresh code; the device secret the app would keep."""
		out = self.make()
		if agreed:
			answer = self.joined(_code_of(out))
		else:
			answer = self.joined(_code_of(out), agreed=0, notice_version=None)
		self.assertIn("token", answer or {}, self.words())
		return answer["token"]

	def status(self, token):
		return self.call(fc.field_status, {"token": token})

	def punch(self, token, **overrides):
		args = {"token": token, "log_type": "IN",
		        "latitude": "12.9", "longitude": "77.6", "accuracy": "8"}
		args.update(overrides)
		return self.call(fc.field_checkin, args)

	def remove(self, token):
		return self.call(device_api.remove_my_phone, {"token": token})

	def phone_of(self, token):
		fields = ["name", "status", "token_hash", "retired_token_hash", "last_seen",
		          "checkin_count", "modified", "app_version", "status_changed_on",
		          "status_change_source", "status_changed_by", "join_method"]
		row = frappe.db.get_value(fc.DEVICE, {"token_hash": fc._hash(token)}, fields,
		                          as_dict=True)
		if not row:
			row = frappe.db.get_value(fc.DEVICE, {"retired_token_hash": fc._hash(token)},
			                          fields, as_dict=True)
		return row

	def rows(self):
		return frappe.get_all(
			"Employee Checkin", filters={"employee": self.employee},
			fields=["name", "log_type", "time", "device_id", "latitude", "longitude",
			        "alvoraa_gps_accuracy", "alvoraa_field_device", "alvoraa_mock_location",
			        "alvoraa_checkin_photo"],
			order_by="time asc")

	def leave(self):
		"""The employee is Left, and the leaver hook has NOT run (AC-83)."""
		frappe.db.set_value("Employee", self.employee, "status", "Left", update_modified=False)
		frappe.db.commit()

	def rejoin(self):
		frappe.db.set_value("Employee", self.employee, "status", "Active", update_modified=False)
		frappe.db.commit()


# ── US-12 · the start screen ─────────────────────────────────────────────────

class TheStartScreen(DailyCase):

	def test_013_ac76_an_app_phone_gets_the_listed_keys_and_no_coordinates(self):
		token = self.app_phone()
		out = self.status(token)
		self.assertIsNotNone(out, self.words())
		self.assertEqual(set(out), E4_KEYS)
		self.assertNotIn("work_location", out)
		body = json.dumps(out, default=str)
		self.assertNotIn("latitude", body)
		self.assertNotIn("longitude", body)
		self.assertLessEqual(len(body), 4096)
		self.assertTrue(out["first_name"])
		self.assertTrue(out["employee_name"].startswith(out["first_name"]))
		self.assertEqual(out["designation"], self.driver)
		self.assertTrue(out["company"])
		self.assertEqual(out["notice_version"], notice.CURRENT_VERSION)
		self.assertEqual(out["min_version"], errors.MIN_APP_VERSION)
		self.assertTrue(out["joined_on"])
		self.assertFalse(out["checked_in"])
		self.assertEqual(out["todays_checkins"], [])
		if out["workplace"]:
			self.assertEqual(sorted(out["workplace"]), ["name", "radius_m"])

	def test_013_ac35_a_web_phone_still_gets_its_work_location_block(self):
		"""The web check-in page reads `work_location` today; the new keys are
		added beside it, nothing is taken away."""
		_, token = _new_phone(self.employee, "Active")
		frappe.db.commit()
		out = self.status(token)
		self.assertIsNotNone(out, self.words())
		self.assertIn("work_location", out)
		self.assertTrue(E4_KEYS <= set(out))
		if out["work_location"]:
			self.assertEqual(sorted(out["work_location"]),
			                 ["latitude", "longitude", "name", "radius"])

	def test_013_ac77_opening_the_app_five_times_moves_nothing_on_the_phone(self):
		token = self.app_phone()
		before = self.phone_of(token)
		for _ in range(5):
			self.assertIsNotNone(self.status(token), self.words())
		after = self.phone_of(token)
		for field in ("last_seen", "checkin_count", "modified", "app_version"):
			self.assertEqual(after[field], before[field], field)

	def test_013_ac78_ac91_the_switch_stops_e4_and_e5_and_restoring_it_needs_no_code(self):
		token = self.app_phone()
		versions = frappe.db.count("Version", {"ref_doctype": fc.DEVICE,
		                                       "docname": self.phone_of(token).name})
		self.configure(0, [self.driver], self.driver)
		self.status(token)
		self.assertEqual(self.answer()[:2], (403, "APP_OFF_FOR_FIELD"))
		self.punch(token)
		self.assertEqual(self.answer()[:2], (403, "APP_OFF_FOR_FIELD"))
		self.assertEqual(self.rows(), [])

		self.configure(1, [self.clerk], self.driver)
		self.status(token)
		status, code, values = self.answer()
		self.assertEqual((status, code), (403, "NOT_FIELD_ROLE"))
		self.assertEqual(values.get("designation"), self.driver)

		self.configure(1, [self.driver], self.driver)
		self.assertIsNotNone(self.status(token), self.words())
		self.assertEqual(self.punch(token)["status"], "ok")
		self.assertEqual(frappe.db.count("Version", {"ref_doctype": fc.DEVICE,
		                                             "docname": self.phone_of(token).name}),
		                 versions)

	def test_013_ac80_a_changed_notice_stops_e4_and_e5_until_it_is_read_again(self):
		token = self.app_phone()
		name = self.phone_of(token).name
		for ack in frappe.get_all(ACKNOWLEDGEMENT, {"device": name}, pluck="name"):
			# The phone's reading is of an older version. Written straight to the
			# row: the record is insert-only by design and this is history, not
			# a change anybody made.
			frappe.db.set_value(ACKNOWLEDGEMENT, ack, "notice_version", OLD_VERSION,
			                    update_modified=False)
		frappe.db.commit()

		self.status(token)
		status, code, values = self.answer()
		self.assertEqual((status, code), (409, "NOTICE_CHANGED"))
		self.assertEqual(set(values), {"version", "rows", "retention_days", "what_changed"})
		self.assertEqual(values["version"], notice.CURRENT_VERSION)
		self.assertEqual(len(values["rows"]), 6)

		self.punch(token)
		self.assertEqual(self.answer()[:2], (409, "NOTICE_CHANGED"))
		self.assertEqual(self.rows(), [])

		self.call(join.acknowledge_notice, {"token": token,
		                                    "notice_version": notice.CURRENT_VERSION})
		self.assertIsNone(self.answer()[0], self.words())
		self.assertIsNotNone(self.status(token), self.words())
		self.assertEqual(self.punch(token)["status"], "ok")

	def test_013_ac96_a_web_phone_is_never_asked_about_the_notice_again(self):
		_, token = _new_phone(self.employee, "Active")
		frappe.db.commit()
		self.assertEqual(frappe.db.count(ACKNOWLEDGEMENT, {"employee": self.employee}), 0)
		self.assertIsNotNone(self.status(token), self.words())

	def test_013_ac83_a_leaver_whose_phone_is_not_yet_blocked_is_refused(self):
		token = self.app_phone()
		self.leave()
		try:
			self.status(token)
			self.assertEqual(self.answer()[:2], (403, "EMPLOYEE_NOT_ACTIVE"))
			self.punch(token)
			self.assertEqual(self.answer()[:2], (403, "EMPLOYEE_NOT_ACTIVE"))
			self.assertEqual(self.rows(), [])
		finally:
			self.rejoin()

	def test_013_consent_not_given_phone_is_refused_at_e4_and_e5(self):
		token = self.app_phone(agreed=0)
		self.status(token)
		status, code, values = self.answer()
		self.assertEqual((status, code), (403, "CONSENT_REQUIRED"))
		self.assertEqual(values.get("version"), notice.CURRENT_VERSION)
		self.punch(token)
		self.assertEqual(self.answer()[:2], (403, "CONSENT_REQUIRED"))
		self.assertEqual(self.rows(), [])


# ── US-13 · the punch ────────────────────────────────────────────────────────

class ThePunch(DailyCase):

	def test_013_ac84_one_punch_with_everything_on_it(self):
		token = self.app_phone()
		request = _FakeRequest()
		request.headers = {errors.VERSION_HEADER: "1.0.3"}
		frappe.local.request = request
		frappe.local.request_ip = "127.0.0.1"
		frappe.cache.delete_keys("rl:alvoraa_portal.field_checkin")
		try:
			out = self.punch(token, accuracy="20", photo=JPEG_1PX, mock_location=0)
		finally:
			frappe.local.request = None
			frappe.cache.delete_keys("rl:alvoraa_portal.field_checkin")
		self.assertEqual((out or {}).get("status"), "ok", self.words())
		self.assertEqual(set(out) >= {"log_type", "time", "todays_checkins", "employee_name"}, True)

		rows = self.rows()
		self.assertEqual(len(rows), 1)
		row = rows[0]
		phone = self.phone_of(token)
		self.assertEqual(row.device_id, "alvoraa-field-app")
		self.assertEqual(row.log_type, "IN")
		self.assertAlmostEqual(row.latitude, 12.9, places=4)
		self.assertAlmostEqual(row.longitude, 77.6, places=4)
		self.assertEqual(row.alvoraa_gps_accuracy, 20.0)
		self.assertEqual(row.alvoraa_field_device, phone.name)
		self.assertEqual(row.alvoraa_mock_location, 0)
		self.assertTrue(row.alvoraa_checkin_photo, "the photo was not attached")
		f = frappe.db.get_value("File", {"attached_to_doctype": "Employee Checkin",
		                                 "attached_to_name": row.name},
		                        ["is_private", "file_url"], as_dict=True)
		self.assertTrue(f)
		self.assertEqual(f.is_private, 1)
		self.assertIn("/private/", f.file_url)

		self.assertEqual(phone.checkin_count, 1)
		self.assertTrue(phone.last_seen)
		self.assertEqual(phone.app_version, "1.0.3")

		self.assertEqual([r["name"] for r in out["todays_checkins"]], [row.name])
		self.assertEqual(str(out["time"]), str(row.time))

	def test_013_ac85_the_fake_location_flag_is_kept_on_the_punch(self):
		token = self.app_phone()
		self.assertEqual(self.punch(token, mock_location=1)["status"], "ok")
		time.sleep(1.1)
		self.assertEqual(self.punch(token, log_type="OUT", mock_location="true")["status"], "ok")
		rows = self.rows()
		self.assertEqual([r.alvoraa_mock_location for r in rows], [1, 1])

	def test_013_ac86_no_location_and_no_accuracy_are_refused_on_an_app_phone(self):
		token = self.app_phone()
		self.punch(token, latitude=None)
		self.assertEqual(self.answer()[:2], (422, "LOCATION_MISSING"))
		self.punch(token, accuracy=None)
		self.assertEqual(self.answer()[:2], (422, "LOCATION_MISSING"))
		self.assertEqual(self.rows(), [])

	def test_013_ac35_a_web_phone_may_still_punch_without_an_accuracy(self):
		_, token = _new_phone(self.employee, "Active")
		frappe.db.commit()
		self.assertEqual(self.punch(token, accuracy=None)["status"], "ok")

	def test_013_ac86_a_fix_worse_than_50_m_is_refused_and_50_m_is_allowed(self):
		token = self.app_phone()
		self.punch(token, accuracy="60")
		status, code, values = self.answer()
		self.assertEqual((status, code), (422, "GPS_NOT_EXACT"))
		self.assertEqual(values, {"accuracy_m": 60, "limit_m": 50})
		self.assertEqual(self.rows(), [])
		self.assertEqual(self.punch(token, accuracy="50")["status"], "ok")

	def test_013_ac86_a_second_punch_inside_the_window_is_refused(self):
		"""Fail-without-fix: delete the `_refuse_duplicate(...)` call in the
		punch and both punches save, so the second answer is "ok" and this
		fails. Proven on 2026-09-19: rows 000054 and 000055 both saved."""
		token = self.app_phone()
		first = self.punch(token)
		self.assertEqual(first["status"], "ok")
		time.sleep(1.1)   # not the same second: that is Frappe HR's own refusal
		second = self.punch(token)
		status, code, values = self.answer()
		self.assertIsNone(second)
		self.assertEqual((status, code), (409, "ALREADY_RECORDED"))
		self.assertEqual(str(values.get("time")), str(first["time"]))
		self.assertEqual(len(self.rows()), 1)
		# A different kind of punch inside the window is not a duplicate.
		self.assertEqual(self.punch(token, log_type="OUT")["status"], "ok")
		self.assertEqual(len(self.rows()), 2)

	def test_013_ac35_the_web_page_answer_keeps_its_keys(self):
		_, token = _new_phone(self.employee, "Active")
		frappe.db.commit()
		out = self.punch(token)
		self.assertTrue({"status", "log_type", "time", "name", "employee_name"} <= set(out))


# ── the radius ───────────────────────────────────────────────────────────────

class TheGeofence(DailyCase):
	"""Frappe HR's own radius rule, answered with the distance and no coordinates."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls._tracking = frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking")
		if not frappe.db.exists("Shift Type", SHIFT):
			# A shift that spans the day, so the punch is always inside it.
			# Frappe HR refuses it unless the check-in/out margins are 0: with
			# the default 60 minutes the shift would overlap itself.
			frappe.get_doc({"doctype": "Shift Type", "name": SHIFT,
			                "start_time": "00:00:00", "end_time": "23:59:00",
			                "begin_check_in_before_shift_start_time": 0,
			                "allow_check_out_after_shift_end_time": 0}
			               ).insert(ignore_permissions=True)
		cls.depot = frappe.db.get_value("Shift Location", {"location_name": DEPOT})
		if not cls.depot:
			cls.depot = frappe.get_doc({
				"doctype": "Shift Location", "location_name": DEPOT,
				"latitude": DEPOT_LAT, "longitude": DEPOT_LON, "checkin_radius": 100,
			}).insert(ignore_permissions=True).name
		cls.assignment = frappe.get_doc({
			"doctype": "Shift Assignment", "employee": cls.employee, "shift_type": SHIFT,
			"company": frappe.db.get_value("Employee", cls.employee, "company"),
			"shift_location": cls.depot, "start_date": add_days(nowdate(), -30),
		}).insert(ignore_permissions=True)
		cls.assignment.submit()
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 1)
		frappe.clear_cache(doctype="HR Settings")
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		cls._clear_phones()
		try:
			cls.assignment.reload()
			cls.assignment.cancel()
			_bin("Shift Assignment", cls.assignment.name)
		except Exception:
			pass
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking",
		                           cls._tracking or 0)
		frappe.clear_cache(doctype="HR Settings")
		frappe.db.commit()
		super().tearDownClass()

	def test_013_ac86_outside_the_radius_says_how_far_and_never_where_the_depot_is(self):
		token = self.app_phone()
		self.punch(token, **FAR)
		status, code, values = self.answer()
		self.assertEqual((status, code), (422, "OUTSIDE_WORKPLACE"), self.words())
		self.assertEqual(values.get("site"), DEPOT)
		self.assertEqual(values.get("radius_m"), 100)
		self.assertTrue(250 <= values.get("distance_m", 0) <= 500, values)
		self.assertEqual(set(values), {"distance_m", "site", "radius_m"})
		self.assertEqual(self.rows(), [])
		self.assertIn("You are about", self.words())

	def test_013_inside_the_radius_is_saved(self):
		token = self.app_phone()
		self.assertEqual(self.punch(token, **NEAR)["status"], "ok", self.words())

	def test_013_e4_names_the_workplace_and_its_radius_only(self):
		token = self.app_phone()
		out = self.status(token)
		self.assertEqual(out["workplace"], {"name": DEPOT, "radius_m": 100})


class TheMinimumRadius(DailyCase):

	def _location(self, radius):
		return frappe.get_doc({"doctype": "Shift Location",
		                       "location_name": f"Zqx Radius {radius} 013",
		                       "latitude": DEPOT_LAT, "longitude": DEPOT_LON,
		                       "checkin_radius": radius})

	def test_013_a_radius_under_100_m_cannot_be_saved(self):
		frappe.set_user("Administrator")
		for radius in (1, 50, 99):
			with self.subTest(radius=radius), self.assertRaises(frappe.ValidationError):
				self._location(radius).insert(ignore_permissions=True)
			frappe.db.rollback()

	def test_013_100_m_and_no_radius_are_allowed(self):
		frappe.set_user("Administrator")
		for radius in (100, 0, 2000):
			with self.subTest(radius=radius):
				doc = self._location(radius).insert(ignore_permissions=True)
				self.assertEqual(doc.checkin_radius, radius)
				_bin("Shift Location", doc.name)
		frappe.db.commit()

	def test_013_editing_an_old_location_down_to_30_m_is_refused_too(self):
		frappe.set_user("Administrator")
		doc = self._location(150).insert(ignore_permissions=True)
		try:
			doc.checkin_radius = 30
			with self.assertRaises(frappe.ValidationError):
				doc.save(ignore_permissions=True)
		finally:
			frappe.db.rollback()
			_bin("Shift Location", doc.name)
			frappe.db.commit()


# ── US-15 · remove this phone ────────────────────────────────────────────────

class RemoveMyPhone(DailyCase):

	def test_013_ac99_the_phone_is_removed_its_secret_retired_and_nothing_erased(self):
		token = self.app_phone()
		self.assertEqual(self.punch(token)["status"], "ok")
		acks = frappe.db.count(ACKNOWLEDGEMENT, {"employee": self.employee})
		before = self.phone_of(token)

		self.assertEqual(self.remove(token), {}, self.words())
		after = self.phone_of(token)
		self.assertEqual(after.name, before.name)
		self.assertEqual(after.status, "Removed")
		self.assertEqual(after.status_change_source, "The employee")
		self.assertFalse(after.status_changed_by)
		self.assertTrue(after.status_changed_on)
		self.assertFalse(after.token_hash)
		self.assertEqual(after.retired_token_hash, fc._hash(token))
		# Nothing erased: the reading history and the punch stay.
		self.assertEqual(frappe.db.count(ACKNOWLEDGEMENT, {"employee": self.employee}), acks)
		self.assertEqual(len(self.rows()), 1)
		self.assertEqual(self.rows()[0].alvoraa_field_device, before.name)

		# Twice is harmless, and the app is told what happened, with the time.
		self.remove(token)
		status, code, values = self.answer()
		self.assertEqual((status, code), (403, "DEVICE_REMOVED"))
		self.assertEqual(str(values.get("removed_at")), str(after.status_changed_on))
		self.status(token)
		self.assertEqual(self.answer()[:2], (403, "DEVICE_REMOVED"))
		self.punch(token)
		self.assertEqual(self.answer()[:2], (403, "DEVICE_REMOVED"))
		self.assertEqual(len(self.rows()), 1)

	def test_013_ac100_a_blocked_phone_is_told_so_and_left_alone(self):
		doc, token = _new_phone(self.employee, "Active", join_method="App QR code")
		doc.status = "Blocked"
		doc.block_reason = "Other"
		doc.flags[device_rules.SERVER_FLAG] = True
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		changed = self.phone_of(token).status_changed_on

		self.remove(token)
		status, code, values = self.answer()
		self.assertEqual((status, code), (403, "DEVICE_BLOCKED"))
		self.assertEqual(values, {})
		self.assertNotIn("Other", self.words())
		after = self.phone_of(token)
		self.assertEqual(after.status, "Blocked")
		self.assertEqual(after.status_changed_on, changed)

	def test_013_ac100_a_replaced_phone_is_told_so_and_left_alone(self):
		old = self.app_phone()
		self.app_phone()     # the same person joins on a new phone
		self.assertEqual(self.phone_of(old).status, "Replaced")
		self.remove(old)
		status, code, values = self.answer()
		self.assertEqual((status, code), (403, "DEVICE_REPLACED"))
		self.assertIn("replaced_at", values)
		self.assertEqual(self.phone_of(old).status, "Replaced")

	def test_013_a_phone_that_has_not_agreed_can_still_be_removed(self):
		token = self.app_phone(agreed=0)
		self.assertEqual(self.remove(token), {}, self.words())
		self.assertEqual(self.phone_of(token).status, "Removed")

	def test_013_a_pending_web_phone_and_an_unknown_secret_get_the_same_answer(self):
		_, pending = _new_phone(self.employee, "Pending")
		frappe.db.commit()
		self.remove(pending)
		one = (self.answer(), self.words())
		self.remove("x" * 43)
		two = (self.answer(), self.words())
		self.assertEqual(one, two)
		self.assertEqual(one[0][:2], (401, "DEVICE_PENDING"))
		self.assertEqual(self.phone_of(pending).status, "Pending")


# ── the limits, per phone ────────────────────────────────────────────────────

class TheLimitsArePerPhone(DailyCase):

	PREFIXES = ("rl:alvoraa_portal.field_checkin", "rl:alvoraa_portal.field_app_device")

	def setUp(self):
		super().setUp()
		for prefix in self.PREFIXES:
			frappe.cache.delete_keys(prefix)
		frappe.local.request = _FakeRequest()
		frappe.local.request_ip = "127.0.0.1"

	def tearDown(self):
		frappe.local.request = None
		for prefix in self.PREFIXES:
			frappe.cache.delete_keys(prefix)
		super().tearDown()

	def _keys(self, prefix):
		return [k.decode() if isinstance(k, bytes) else str(k)
		        for k in frappe.cache.get_keys(prefix)]

	def test_013_ac82_the_61st_open_in_an_hour_is_too_many_and_redis_holds_the_hash(self):
		token = self.app_phone()
		for _ in range(60):
			self.assertIsNotNone(self.status(token), self.words())
		self.status(token)
		status, code, values = self.answer()
		self.assertEqual((status, code), (429, "TOO_MANY_TRIES"))
		self.assertGreater(values.get("retry_after_s", 0), 0)
		keys = self._keys(self.PREFIXES[0])
		self.assertTrue(keys)
		for key in keys:
			self.assertNotIn(token, key)
		self.assertTrue(any(fc._hash(token) in k for k in keys))

	def test_013_ac88_the_31st_punch_in_an_hour_is_too_many(self):
		token = self.app_phone()
		for _ in range(30):
			self.punch(token)
			self.assertNotEqual(self.answer()[0], 429)
		self.punch(token)
		self.assertEqual(self.answer()[:2], (429, "TOO_MANY_TRIES"))

	def test_013_ac101_the_6th_remove_in_an_hour_is_too_many(self):
		token = self.app_phone()
		for _ in range(5):
			self.remove(token)
			self.assertNotEqual(self.answer()[0], 429)
		self.remove(token)
		self.assertEqual(self.answer()[:2], (429, "TOO_MANY_TRIES"))

	def test_013_ac140_two_phones_behind_one_address_are_two_callers(self):
		a, b = self.app_phone(), self.app_phone()   # b replaces a; a is refused, still counted
		for _ in range(60):
			self.status(b)
		self.status(b)
		self.assertEqual(self.answer()[:2], (429, "TOO_MANY_TRIES"))
		self.status(a)
		self.assertEqual(self.answer()[:2], (403, "DEVICE_REPLACED"))


# ── the contract ─────────────────────────────────────────────────────────────

class TheContract(DailyCase):

	def test_013_every_code_step_4_sends_is_in_the_table_with_its_values(self):
		expected = {
			"LOCATION_MISSING": (422, ()),
			"GPS_NOT_EXACT": (422, ("accuracy_m", "limit_m")),
			"OUTSIDE_WORKPLACE": (422, ("distance_m", "site", "radius_m")),
			"ALREADY_RECORDED": (409, ("time",)),
			"NOTICE_CHANGED": (409, ("version", "rows", "retention_days", "what_changed")),
			"CONSENT_REQUIRED": (403, ("version",)),
			"EMPLOYEE_NOT_ACTIVE": (403, ()),
			"DEVICE_REMOVED": (403, ("removed_at",)),
			"TOO_MANY_TRIES": (429, ("retry_after_s",)),
		}
		for code, (status, values) in expected.items():
			self.assertEqual(errors.CODES.get(code), (status, values), code)

	def test_013_remove_my_phone_is_wrapped_gated_and_limited(self):
		chain, fn = [], device_api.remove_my_phone
		while fn is not None:
			chain.append(fn)
			fn = getattr(fn, "__wrapped__", None)
		private = [i for i, f in enumerate(chain) if hasattr(f, "__alvoraa_private_request__")]
		gate = [i for i, f in enumerate(chain) if hasattr(f, "__alvoraa_feature__")]
		self.assertTrue(private and gate)
		self.assertLess(private[-1], gate[-1])
		self.assertEqual(chain[private[-1]].__alvoraa_private_request__, ())
		self.assertIn(device_api.remove_my_phone, frappe.guest_methods)

	def test_013_the_accuracy_limit_and_the_minimum_radius_are_what_was_decided(self):
		self.assertEqual(fc.MAX_ACCURACY_METRES, 50.0)
		self.assertEqual(fc.MIN_RADIUS_M, 100)
		self.assertEqual(fc.DUPLICATE_WINDOW_SECONDS, 60)
