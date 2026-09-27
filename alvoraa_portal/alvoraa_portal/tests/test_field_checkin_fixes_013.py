"""Field app check-in fixes, found on a real phone on 26 Sep 2026 and approved
on 27 Sep 2026. Every test names the thing it keeps alive:

  * **Where the punch was** - `field_checkin`'s answer carries `location`:
    the workplace, its radius, the distance (rounded), `within` and the
    accuracy used. `within` is True/False only when there is a radius above 0;
    with no workplace or a radius of 0 it is None, so the app never says "At
    <workplace>" for someone 13 km away. Never the workplace's coordinates.
  * **Outside the radius** is still refused, with the distance.
  * **The photo time** - a `captured_at` that carries its UTC offset (the app
    sends "+05:30" from 0.2.1) is moved into the site's time zone. Before, the
    app sent UTC with no mark and it was stored 5 h 30 min early. The "more
    than a day off is dropped" rule still holds.
"""

import datetime
from zoneinfo import ZoneInfo

import frappe
from frappe.utils import add_days, get_system_timezone, now_datetime, nowdate

from alvoraa_portal import field_checkin as fc
from alvoraa_portal.tests.test_field_app_step1_013 import _bin
from alvoraa_portal.tests.test_field_app_step4_013 import SHIFT, DailyCase

# The workplace, and two places near it: about 10 m north and about 380 m north.
DEPOT = "Zqx Depot Fixes 013"
DEPOT_LAT, DEPOT_LON = 28.6519, 77.1906
NEAR = {"latitude": "28.6520", "longitude": "77.1906"}
FAR = {"latitude": "28.6553", "longitude": "77.1906"}

LOCATION_KEYS = {"workplace", "radius_m", "distance_m", "within", "accuracy_m"}

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


class NoWorkplace(DailyCase):
	"""An employee with no Shift Location: the punch is allowed anywhere."""

	def test_fix0927_no_workplace_says_location_recorded_with_the_accuracy(self):
		token = self.app_phone()
		out = self.punch(token, accuracy="14")
		self.assertEqual((out or {}).get("status"), "ok", self.words())
		self.assertEqual(out["location"], {"workplace": None, "radius_m": None,
		                                   "distance_m": None, "within": None,
		                                   "accuracy_m": 14})


class WithAWorkplace(DailyCase):
	"""One workplace, assigned through a Shift Assignment, as Frappe HR reads it."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls._tracking = frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking")
		if not frappe.db.exists("Shift Type", SHIFT):
			frappe.get_doc({"doctype": "Shift Type", "name": SHIFT,
			                "start_time": "00:00:00", "end_time": "23:59:00",
			                "begin_check_in_before_shift_start_time": 0,
			                "allow_check_out_after_shift_end_time": 0}
			               ).insert(ignore_permissions=True)
		cls.depot = frappe.db.get_value("Shift Location", {"location_name": DEPOT})
		if not cls.depot:
			cls.depot = frappe.get_doc({
				"doctype": "Shift Location", "location_name": DEPOT,
				"latitude": DEPOT_LAT, "longitude": DEPOT_LON, "checkin_radius": 200,
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

	def radius(self, metres, tracking=1):
		"""Set straight on the row: the minimum-radius hook runs on a save, and
		0 is allowed anyway."""
		user = frappe.session.user
		frappe.set_user("Administrator")
		frappe.db.set_value("Shift Location", self.depot, "checkin_radius", metres,
		                    update_modified=False)
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", tracking)
		frappe.clear_cache(doctype="HR Settings")
		frappe.db.commit()
		frappe.set_user(user)

	def test_fix0927_inside_the_radius_is_at_the_workplace(self):
		self.radius(200)
		token = self.app_phone()
		out = self.punch(token, accuracy="14", **NEAR)
		self.assertEqual((out or {}).get("status"), "ok", self.words())
		loc = out["location"]
		self.assertEqual(set(loc), LOCATION_KEYS)
		self.assertEqual(loc["workplace"], DEPOT)
		self.assertEqual(loc["radius_m"], 200)
		self.assertIs(loc["within"], True)
		self.assertIsInstance(loc["distance_m"], int)
		self.assertTrue(0 <= loc["distance_m"] <= 20, loc)
		self.assertEqual(loc["accuracy_m"], 14)

	def test_fix0927_outside_the_radius_is_refused_with_the_distance(self):
		self.radius(200)
		token = self.app_phone()
		self.punch(token, **FAR)
		status, code, values = self.answer()
		self.assertEqual((status, code), (422, "OUTSIDE_WORKPLACE"), self.words())
		self.assertEqual(values.get("site"), DEPOT)
		self.assertEqual(values.get("radius_m"), 200)
		self.assertTrue(250 <= values.get("distance_m", 0) <= 500, values)
		self.assertEqual(self.rows(), [])

	def test_fix0927_radius_0_means_allowed_anywhere_and_still_says_how_far(self):
		"""The case seen on 26 Sep: radius 0, 13 km away, allowed - and the app
		said "At <workplace>". Now `within` is None and the distance is sent."""
		self.radius(0)
		token = self.app_phone()
		out = self.punch(token, accuracy="14", **FAR)
		self.assertEqual((out or {}).get("status"), "ok", self.words())
		loc = out["location"]
		self.assertEqual(loc["workplace"], DEPOT)
		self.assertEqual(loc["radius_m"], 0)
		self.assertIsNone(loc["within"])
		self.assertTrue(250 <= loc["distance_m"] <= 500, loc)
		self.assertEqual(loc["accuracy_m"], 14)

	def test_fix0927_a_radius_not_enforced_is_from_anywhere_never_at(self):
		"""Tracking off: Frappe HR does not enforce the radius, so the punch is
		saved, the phone is told the radius is 0 (from anywhere), and it still
		says how far away the person was - never "at" the workplace."""
		self.radius(200, tracking=0)
		token = self.app_phone()
		out = self.punch(token, **FAR)
		self.assertEqual((out or {}).get("status"), "ok", self.words())
		self.assertEqual(out["location"]["radius_m"], 0)
		self.assertIsNone(out["location"]["within"])
		self.assertTrue(250 <= out["location"]["distance_m"] <= 500)

	def test_fix0927_status_says_from_anywhere_when_tracking_is_off(self):
		"""The rule line on welcome and home: a radius nobody checks is shown as 0."""
		self.radius(200, tracking=0)
		token = self.app_phone()
		self.assertEqual(self.status(token)["workplace"], {"name": DEPOT, "radius_m": 0})
		self.radius(200, tracking=1)
		self.assertEqual(self.status(token)["workplace"], {"name": DEPOT, "radius_m": 200})

	def test_fix0927_the_answer_never_carries_the_workplace_coordinates(self):
		self.radius(200)
		token = self.app_phone()
		out = self.punch(token, **NEAR)
		text = frappe.as_json(out)
		self.assertNotIn(str(DEPOT_LON), text)
		self.assertNotIn("latitude", text)
		self.assertNotIn("longitude", text)

	def test_fix0927_status_names_the_workplace_and_radius_0_as_0(self):
		"""The rule line on welcome and home reads this; 0 means "from anywhere"."""
		self.radius(0)
		token = self.app_phone()
		out = self.status(token)
		self.assertEqual(out["workplace"], {"name": DEPOT, "radius_m": 0})


class ThePhotoTime(DailyCase):
	"""`captured_at` with an offset lands in the site's time zone."""

	def site_now(self):
		return now_datetime().replace(microsecond=0)

	def as_phone_in_india(self, site_local):
		"""The same moment written the way a phone in India sends it from 0.2.1."""
		aware = site_local.replace(tzinfo=ZoneInfo(get_system_timezone()))
		return aware.astimezone(IST).isoformat(timespec="seconds")

	def test_fix0927_a_plus_0530_phone_time_is_moved_into_site_time(self):
		site_local = self.site_now()
		sent = self.as_phone_in_india(site_local)
		self.assertTrue(sent.endswith("+05:30"), sent)
		got = fc._validated_captured_at(sent)
		self.assertIsNotNone(got)
		self.assertIsNone(got.tzinfo)
		self.assertEqual(got, site_local)

	def test_fix0927_utc_marked_z_is_moved_too(self):
		site_local = self.site_now()
		aware = site_local.replace(tzinfo=ZoneInfo(get_system_timezone()))
		sent = aware.astimezone(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
		self.assertEqual(fc._validated_captured_at(sent), site_local)

	def test_fix0927_a_plus_0530_time_is_stored_on_the_punch_in_site_time(self):
		site_local = self.site_now()
		token = self.app_phone()
		out = self.punch(token, captured_at=self.as_phone_in_india(site_local))
		self.assertEqual((out or {}).get("status"), "ok", self.words())
		stored = frappe.db.get_value("Employee Checkin", out["name"], "alvoraa_captured_at")
		self.assertEqual(stored, site_local)

	def test_fix0927_more_than_a_day_off_is_still_dropped(self):
		sent = self.as_phone_in_india(self.site_now() - datetime.timedelta(days=2))
		self.assertIsNone(fc._validated_captured_at(sent))
		sent = self.as_phone_in_india(self.site_now() + datetime.timedelta(hours=25))
		self.assertIsNone(fc._validated_captured_at(sent))

	def test_fix0927_a_time_with_no_offset_is_read_as_site_time_as_before(self):
		site_local = self.site_now()
		self.assertEqual(fc._validated_captured_at(site_local.strftime("%Y-%m-%d %H:%M:%S")),
		                 site_local)

	def test_fix0927_an_old_app_time_with_no_offset_is_read_as_utc(self):
		"""Builds before 0.2.1 sent UTC with no offset: read as UTC, not site time."""
		site_local = self.site_now()
		aware = site_local.replace(tzinfo=ZoneInfo(get_system_timezone()))
		bare_utc = aware.astimezone(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
		self.assertEqual(fc._validated_captured_at(bare_utc, "0.2.0"), site_local)
		self.assertEqual(fc._validated_captured_at(bare_utc, "0.1.0"), site_local)

	def test_fix0927_new_app_and_web_page_bare_times_stay_site_time(self):
		site_local = self.site_now()
		bare = site_local.strftime("%Y-%m-%d %H:%M:%S")
		self.assertEqual(fc._validated_captured_at(bare, "0.2.1"), site_local)
		self.assertEqual(fc._validated_captured_at(bare, None), site_local)       # the web page
		self.assertEqual(fc._validated_captured_at(bare, "not-a-version"), site_local)

	def test_fix0927_nonsense_is_dropped_not_an_error(self):
		for sent in ("not a time", "2026-13-45T99:00:00+05:30", "", None):
			with self.subTest(sent=sent):
				self.assertIsNone(fc._validated_captured_at(sent))
