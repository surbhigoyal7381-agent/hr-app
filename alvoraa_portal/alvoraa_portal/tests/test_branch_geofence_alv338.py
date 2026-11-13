"""ALV-338: a phone or portal punch must be made near the person's own branch.

The client keeps phone punches as the fallback for a machine that cannot read a
finger (mehndi), but only from inside the store. Field workers may punch from
anywhere. Machine punches, punches loaded from another system and punches HR adds
are never measured - Frappe HR's own rule measures every punch, and at DTC that
refused every machine punch on 26 Oct 2026 (ALV-231).
"""

import frappe
import frappe.client
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import branch_geofence as bg
from alvoraa_portal import field_checkin as fc
from alvoraa_portal import hr_api
from alvoraa_portal.field_app_settings import CHILD, F_DESIGNATIONS, SETTINGS

SHIFT = "CI Test Shift"
BRANCH = "ALV338 Test Branch"
FIELD_ROLE = "ALV338 Field Rep"
STORE_ROLE = "ALV338 Store Staff"
PIN = (28.6519, 77.1906)
NEAR = (28.6525, 77.1910)    # about 75 m from the pin
FAR = (28.7000, 77.1500)     # about 6.6 km from the pin

_ORIGINAL_TRACKING = None


def setUpModule():
	global _ORIGINAL_TRACKING
	_ORIGINAL_TRACKING = frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking")
	bg.after_migrate()
	frappe.clear_cache(doctype="Branch")
	for d in (FIELD_ROLE, STORE_ROLE):
		if not frappe.db.exists("Designation", d):
			frappe.get_doc({"doctype": "Designation", "designation_name": d}).insert(ignore_permissions=True)
	if not frappe.db.exists("Branch", BRANCH):
		frappe.get_doc({"doctype": "Branch", "branch": BRANCH}).insert(ignore_permissions=True)
	if not frappe.db.exists("Shift Type", SHIFT):
		frappe.get_doc({"doctype": "Shift Type", "name": SHIFT,
		                "start_time": "09:00:00", "end_time": "18:00:00"}).insert(ignore_permissions=True)
	frappe.db.commit()


def tearDownModule():
	frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", _ORIGINAL_TRACKING or 0)
	frappe.db.delete(CHILD, {"parent": SETTINGS, "designation": FIELD_ROLE})
	frappe.db.commit()
	frappe.clear_cache(doctype="HR Settings")


class Case(FrappeTestCase):
	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		self.tracking(True)
		self.branch(radius=200)
		self.field_list(False)

	def tearDown(self):
		frappe.set_user("Administrator")
		self.tracking(False)
		self.field_list(False)
		frappe.db.commit()
		frappe.set_user(self.caller)

	# ── set-up helpers ──────────────────────────────────────────────────────
	def tracking(self, on):
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 1 if on else 0)
		frappe.clear_cache(doctype="HR Settings")

	def branch(self, radius, pin=PIN):
		frappe.db.set_value("Branch", BRANCH, {bg.F_LAT: pin[0] if pin else 0,
		                                       bg.F_LNG: pin[1] if pin else 0, bg.F_RADIUS: radius})

	def field_list(self, on):
		frappe.db.delete(CHILD, {"parent": SETTINGS, "designation": FIELD_ROLE})
		if on:
			frappe.get_doc({"doctype": CHILD, "parent": SETTINGS, "parenttype": SETTINGS,
			                "parentfield": F_DESIGNATIONS, "designation": FIELD_ROLE,
			                "idx": 99}).db_insert()

	def person(self, first, designation=STORE_ROLE):
		"""Reused across runs: do_checkin commits, so whatever it made outlives the
		test's rollback."""
		email = "%s.alv338@example.com" % first.lower()
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		emp = frappe.db.get_value("Employee", {"user_id": email, "status": "Active"})
		if not emp:
			emp = frappe.get_doc({
				"doctype": "Employee", "first_name": first,
				"company": frappe.db.get_value("Company", {}, "name"),
				"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
				"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
				"status": "Active", "user_id": email, "default_shift": SHIFT,
			}).insert(ignore_permissions=True).name
		frappe.db.set_value("Employee", emp, {"branch": BRANCH, "designation": designation})
		frappe.db.commit()
		return emp, email

	def portal(self, email, where, log_type="IN"):
		frappe.set_user(email)
		try:
			return hr_api.do_checkin(log_type, latitude=where[0], longitude=where[1])
		finally:
			frappe.set_user("Administrator")

	def other_source(self, emp, device_id, where):
		"""A machine punch, a loaded one, or one HR adds: straight to the record."""
		return frappe.get_doc({
			"doctype": "Employee Checkin", "employee": emp, "time": frappe.utils.now(),
			"device_id": device_id, "latitude": where[0], "longitude": where[1],
		}).insert(ignore_permissions=True)


class APhonePunchIsMeasuredAgainstTheBranch(Case):
	def test_far_from_the_branch_is_refused_and_says_how_far(self):
		emp, email = self.person("GeoFar")
		with self.assertRaises(frappe.ValidationError) as caught:
			self.portal(email, FAR)
		said = str(caught.exception)
		self.assertIn(BRANCH, said)
		self.assertIn("200 m", said)
		self.assertRegex(said, r"about \d{4} m")

	def test_inside_the_store_is_accepted(self):
		"""The mehndi case: the machine cannot read the finger, the phone works."""
		emp, email = self.person("GeoNear")
		out = self.portal(email, NEAR)
		self.assertEqual(out["status"], "ok")

	def test_the_refusal_is_frappe_hrs_own_kind(self):
		"""So the field app's existing handling rewrites it like Frappe HR's."""
		from hrms.hr.doctype.employee_checkin.employee_checkin import CheckinRadiusExceededError

		emp, email = self.person("GeoKind")
		with self.assertRaises(CheckinRadiusExceededError):
			self.portal(email, FAR)

	def test_filing_your_own_punch_through_the_api_is_measured_too(self):
		"""The review's finding: the device name is the sender's choice. A staff
		login calling Frappe's API (or Frappe HR's own phone app) with no device
		name must not skip the rule."""
		emp, email = self.person("GeoApi")
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.ValidationError):
				frappe.client.insert({"doctype": "Employee Checkin", "employee": emp,
				                      "log_type": "IN", "latitude": FAR[0], "longitude": FAR[1]})
		finally:
			frappe.set_user("Administrator")

	def test_the_field_app_source_is_measured_too(self):
		emp, _email = self.person("GeoApp")
		with self.assertRaises(frappe.ValidationError):
			self.other_source(emp, "alvoraa-field-app", FAR)


class EverythingElseIsNeverMeasured(Case):
	def test_a_machine_punch_far_from_the_branch_is_saved(self):
		"""Staff punch at another store's machine: Pitampura on the Delhi machine."""
		emp, _email = self.person("GeoMachine")
		self.assertTrue(self.other_source(emp, "DTCDEV1", FAR).name)

	def test_the_machine_account_is_never_measured_whatever_device_it_names(self):
		"""Never refuse a machine punch (ALV-231), even with a mis-set device name."""
		from unittest import mock

		emp, _email = self.person("GeoSync")
		with mock.patch("alvoraa_portal.field_app_access.is_machine_account", return_value=True):
			self.assertTrue(self.other_source(emp, "web-portal", FAR).name)

	def test_a_punch_loaded_with_no_real_location_is_saved(self):
		"""Loads from another system put a position close to 0, 0 on the punch. (An
		exact 0, 0 is refused by Frappe HR itself while tracking is on, before
		this rule is reached - not this change's doing.)"""
		emp, _email = self.person("GeoLoaded")
		self.assertTrue(self.other_source(emp, "1027", (0.0001, 0.0001)).name)

	def test_a_punch_hr_adds_with_no_device_is_saved(self):
		emp, _email = self.person("GeoHR")
		self.assertTrue(self.other_source(emp, None, FAR).name)


class WhoMayPunchFromAnywhere(Case):
	def test_a_field_worker_may(self):
		emp, email = self.person("GeoField", designation=FIELD_ROLE)
		self.field_list(True)
		self.assertEqual(self.portal(email, FAR)["status"], "ok")

	def test_the_same_role_off_the_list_may_not(self):
		emp, email = self.person("GeoFieldOff", designation=FIELD_ROLE)
		with self.assertRaises(frappe.ValidationError):
			self.portal(email, FAR)


class WhenNothingIsMeasured(Case):
	def test_radius_zero_means_no_limit(self):
		emp, email = self.person("GeoZero")
		self.branch(radius=0)
		self.assertEqual(self.portal(email, FAR)["status"], "ok")

	def test_a_branch_with_no_pin_is_not_measured(self):
		emp, email = self.person("GeoNoPin")
		self.branch(radius=200, pin=None)
		self.assertEqual(self.portal(email, FAR)["status"], "ok")

	def test_tracking_off_in_hr_settings_turns_it_all_off(self):
		emp, email = self.person("GeoOff")
		self.tracking(False)
		frappe.set_user(email)
		try:
			self.assertEqual(hr_api.do_checkin("IN", latitude=FAR[0], longitude=FAR[1])["status"], "ok")
		finally:
			frappe.set_user("Administrator")

	def test_somebody_with_no_branch_is_not_measured(self):
		emp, email = self.person("GeoNoBranch")
		frappe.db.set_value("Employee", emp, "branch", None)
		self.assertEqual(self.portal(email, FAR)["status"], "ok")


class FrappeHrsOwnRuleKeepsItsPeople(Case):
	def test_a_shift_assignment_workplace_wins_and_this_rule_steps_aside(self):
		"""Two rules must never disagree about one person. With a Shift Location of
		radius 0 on the assignment, Frappe HR says "no limit" and this rule stays out."""
		emp, email = self.person("GeoAssigned")
		loc = frappe.db.get_value("Shift Location", {"location_name": "ALV338 Assigned"}) or frappe.get_doc({
			"doctype": "Shift Location", "location_name": "ALV338 Assigned",
			"latitude": PIN[0], "longitude": PIN[1], "checkin_radius": 0,
		}).insert(ignore_permissions=True).name
		if not frappe.db.exists("Shift Assignment", {"employee": emp, "shift_location": loc, "docstatus": 1}):
			frappe.get_doc({"doctype": "Shift Assignment", "employee": emp, "shift_type": SHIFT,
			                "company": frappe.db.get_value("Employee", emp, "company"),
			                "start_date": "2020-01-01", "shift_location": loc}).insert(ignore_permissions=True).submit()
		frappe.db.commit()
		self.assertEqual(self.portal(email, FAR)["status"], "ok")
		self.assertEqual(fc._shift_location_for(emp).location_name, "ALV338 Assigned")


class TheFieldAppNamesTheBranch(Case):
	def test_its_workplace_is_the_branch(self):
		emp, _email = self.person("GeoSite")
		site = fc._shift_location_for(emp)
		self.assertEqual(site.location_name, BRANCH)
		self.assertEqual(site.checkin_radius, 200)
		self.assertEqual(fc._check_in_rule(site), "radius")

	def test_for_a_field_worker_it_says_anywhere(self):
		emp, _email = self.person("GeoSiteField", designation=FIELD_ROLE)
		self.field_list(True)
		self.assertIsNone(fc._shift_location_for(emp))
		self.assertEqual(fc._check_in_rule(None), "anywhere")

	def test_its_refusal_message_names_the_branch_and_the_distance(self):
		from hrms.hr.doctype.employee_checkin.employee_checkin import CheckinRadiusExceededError

		emp, _email = self.person("GeoMsg")
		out = fc._geofence_message(CheckinRadiusExceededError("x"), emp, FAR[0], FAR[1])
		self.assertIn(BRANCH, out["message"])
		self.assertEqual(out["values"]["radius_m"], 200)
		self.assertGreater(out["values"]["distance_m"], 5000)
		self.assertNotIn("latitude", out["values"])  # never the branch's position


class TheRadiusFloor(Case):
	def test_a_radius_a_phone_cannot_measure_is_refused_on_save(self):
		doc = frappe.get_doc("Branch", BRANCH)
		doc.set(bg.F_RADIUS, 30)
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	def test_zero_and_a_real_radius_save(self):
		doc = frappe.get_doc("Branch", BRANCH)
		for r in (0, 300):
			doc.set(bg.F_RADIUS, r)
			doc.save(ignore_permissions=True)


class TheFields(Case):
	def test_the_three_branch_fields_exist(self):
		meta = frappe.get_meta("Branch")
		for f in (bg.F_LAT, bg.F_LNG, bg.F_RADIUS):
			self.assertTrue(meta.has_field(f), f)

	def test_running_again_changes_nothing(self):
		before = frappe.db.get_value("Custom Field", {"dt": "Branch", "fieldname": bg.F_RADIUS}, "modified")
		bg.after_migrate()
		after = frappe.db.get_value("Custom Field", {"dt": "Branch", "fieldname": bg.F_RADIUS}, "modified")
		self.assertEqual(before, after)
