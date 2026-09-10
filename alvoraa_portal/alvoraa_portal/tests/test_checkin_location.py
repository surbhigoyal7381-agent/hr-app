"""Checking in when the organisation records where you were.

Frappe HR refuses a check-in with no coordinates whenever
`allow_geolocation_tracking` is on. The portal had never sent any, so the
check-in button simply did not work on any tenant with that switched on - it
failed with "Latitude and longitude values are required for checking in.",
which means nothing to the person reading it.

What is pinned down here is the portal's half: that it asks only where the
employer records it, that the coordinates reach the record, and that the
refusal explains itself.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import hr_api

SHIFT = "CI Test Shift"


_ORIGINAL_TRACKING = None


def setUpModule():
	"""Remember the site's real setting ONCE, for the whole module.

	Capturing it per test looked equivalent and was not: `set_single_value`
	commits, so the first test to switch tracking on made every later setUp
	read 1 as "the original" and restore 1 forever. The setting then leaked out
	of this module and broke test_attendance_correction, which creates check-ins
	of its own.
	"""
	global _ORIGINAL_TRACKING
	_ORIGINAL_TRACKING = frappe.db.get_single_value(
		"HR Settings", "allow_geolocation_tracking")


def tearDownModule():
	frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking",
	                           _ORIGINAL_TRACKING or 0)
	frappe.db.commit()
	frappe.clear_cache(doctype="HR Settings")


def _company():
	return frappe.db.get_value("Company", {}, "name")


class CheckinCase(FrappeTestCase):
	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		self.company = _company()
		if not frappe.db.exists("Shift Type", SHIFT):
			frappe.get_doc({"doctype": "Shift Type", "name": SHIFT,
			                "start_time": "09:00:00", "end_time": "18:00:00"}
			               ).insert(ignore_permissions=True)

	def tearDown(self):
		# Back to off between tests, so no test inherits the last one's setting.
		# The site's real value is put back once, in tearDownModule.
		self.tracking(False)
		frappe.set_user(self.caller)

	def tracking(self, on):
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking",
		                           1 if on else 0)
		frappe.clear_cache(doctype="HR Settings")

	def person(self, first):
		"""Reused if it already exists, rather than created afresh.

		`do_checkin` ends with `frappe.db.commit()`, so everything the test made
		up to that point is committed too and outlives FrappeTestCase's
		rollback. A second run then hit "User ... is already assigned to
		Employee ...". Reusing is honest here - the tests care about the
		check-in, not about who made the employee.
		"""
		email = "%s.ci@example.com" % first.lower()
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
			                "send_welcome_email": 0}).insert(ignore_permissions=True)

		existing = frappe.db.get_value("Employee", {"user_id": email, "status": "Active"})
		if existing:
			return existing, email

		emp = frappe.get_doc({
			"doctype": "Employee", "first_name": first, "company": self.company,
			"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "user_id": email, "default_shift": SHIFT,
		}).insert(ignore_permissions=True)
		return emp.name, email


class WhetherWeAskAtAll(CheckinCase):
	def test_we_do_not_ask_when_the_employer_does_not_record_it(self):
		"""A browser location prompt is an intrusion. Showing it to somebody
		whose employer does not record this would be asking for personal data
		with no reason to want it."""
		self.tracking(False)
		self.assertFalse(hr_api.checkin_needs_location())

	def test_we_ask_when_they_do(self):
		self.tracking(True)
		self.assertTrue(hr_api.checkin_needs_location())

	def test_the_page_is_told_before_the_button_is_pressed(self):
		"""The status call carries it, so the first press already knows whether
		to ask - rather than discovering it from a failure."""
		p, email = self.person("CIFlag")
		self.tracking(True)
		frappe.set_user(email)
		self.assertTrue(hr_api.get_checkin_status()["needs_location"])

		frappe.set_user("Administrator")
		self.tracking(False)
		frappe.set_user(email)
		self.assertFalse(hr_api.get_checkin_status()["needs_location"])


class TheCoordinatesReachTheRecord(CheckinCase):
	def test_a_checkin_with_a_location_keeps_it(self):
		"""The whole point. Recording WHERE is the thing the organisation
		switched on."""
		p, email = self.person("CIWhere")
		self.tracking(True)
		frappe.set_user(email)
		out = hr_api.do_checkin("IN", latitude=28.6519, longitude=77.1906)
		row = frappe.db.get_value("Employee Checkin", out["name"],
		                          ["latitude", "longitude", "device_id"], as_dict=True)
		self.assertAlmostEqual(row.latitude, 28.6519, places=4)
		self.assertAlmostEqual(row.longitude, 77.1906, places=4)
		self.assertEqual(row.device_id, "web-portal")

	def test_it_still_works_where_nothing_is_recorded(self):
		"""Most tenants do not record location, and check-in must not need one."""
		p, email = self.person("CIPlain")
		self.tracking(False)
		frappe.set_user(email)
		out = hr_api.do_checkin("IN")
		self.assertEqual(out["status"], "ok")

	def test_coordinates_are_accepted_as_strings(self):
		"""They arrive over HTTP, so they arrive as text."""
		p, email = self.person("CIStrings")
		self.tracking(True)
		frappe.set_user(email)
		out = hr_api.do_checkin("IN", latitude="28.6519", longitude="77.1906")
		self.assertAlmostEqual(
			frappe.db.get_value("Employee Checkin", out["name"], "latitude"),
			28.6519, places=4)


class TheRefusalExplainsItself(CheckinCase):
	def test_a_missing_location_says_what_to_do(self):
		"""Frappe HR's own words are "Latitude and longitude values are required
		for checking in." Nobody reading that knows they need to press Allow in
		their browser."""
		p, email = self.person("CINoLoc")
		self.tracking(True)
		frappe.set_user(email)
		with self.assertRaises(frappe.ValidationError) as caught:
			hr_api.do_checkin("IN")
		said = str(caught.exception).lower()
		self.assertIn("allow location access", said)
		self.assertNotIn("latitude", said)

	def test_a_bad_log_type_is_still_refused(self):
		p, email = self.person("CIBadType")
		frappe.set_user(email)
		with self.assertRaises(frappe.ValidationError):
			hr_api.do_checkin("SIDEWAYS")


class TheDistanceRuleIsOff(CheckinCase):
	"""Recording where somebody was is not the same as refusing them for it.

	The product decision (2026-09-10) is to record and never block: GPS is
	routinely 100-500m out indoors, so a tight radius refuses people who are
	standing in the shop. Frappe HR reads a radius of zero as "do not police
	this", which is the lever used.
	"""

	def test_a_zero_radius_lets_a_far_away_checkin_through(self):
		p, email = self.person("CIFar")
		self.tracking(True)

		name = frappe.db.get_value("Shift Location", {"location_name": "CI Test Store"})
		if not name:
			name = frappe.get_doc({
				"doctype": "Shift Location", "location_name": "CI Test Store",
				"latitude": 28.6519, "longitude": 77.1906, "checkin_radius": 0,
			}).insert(ignore_permissions=True).name

		if not frappe.db.exists("Shift Assignment",
		                        {"employee": p, "shift_location": name, "docstatus": 1}):
			frappe.get_doc({
				"doctype": "Shift Assignment", "employee": p, "shift_type": SHIFT,
				"company": self.company, "shift_location": name,
				"start_date": frappe.utils.add_days(frappe.utils.nowdate(), -30),
			}).insert(ignore_permissions=True).submit()

		frappe.set_user(email)
		# Mumbai, well over a thousand kilometres from that Delhi store.
		out = hr_api.do_checkin("IN", latitude=19.0760, longitude=72.8777)
		self.assertEqual(out["status"], "ok")
