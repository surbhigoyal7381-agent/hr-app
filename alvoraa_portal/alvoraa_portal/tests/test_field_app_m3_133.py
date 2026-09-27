"""Field app Material 3 redesign, the server's part (ALV-133, 01d §8). Every
test names the thing it keeps alive:

  * **E-1 · the company's colour** - `brand_colour` is in the password sign-in
    answer, the code join's answer and `field_status`. It is always a plain
    "#rrggbb": whatever else is typed into site config never reaches the
    phone, because the app builds its whole palette from it.
  * **E-3 · the check-in rule** - `field_status` says "radius" or "anywhere".
    A radius of 0 is Frappe HR's "no limit", so it is "anywhere".
  * **E-4 · a stable key per notice part** - so the app can put the right
    picture beside each part whatever language the heading is in. Adding the
    key changes no word and no version.
  * **E-5 · HR sees a withdrawal** - after "Stop agreeing" the Employee
    form's section says "not agreed", names the employee as the one who
    changed it, and the phone record's timeline says so in words.
"""

from unittest import mock

import frappe
from frappe.utils import add_days, nowdate

from alvoraa_portal import field_app_join as join
from alvoraa_portal import field_app_notice as notice
from alvoraa_portal import field_app_pwa as pwa
from alvoraa_portal import field_checkin as fc
from alvoraa_portal.tenant_context import DEFAULTS
from alvoraa_portal.tests.test_field_app_password_signin_128 import PasswordCase
from alvoraa_portal.tests.test_field_app_step1_013 import _bin
from alvoraa_portal.tests.test_field_app_step3_013 import _code_of
from alvoraa_portal.tests.test_field_app_step4_013 import SHIFT, DailyCase
from alvoraa_portal.tests.test_field_app_step5_013 import DeskCase

HEX = r"^#[0-9a-f]{6}$"
DEPOT = "Zqx Depot M3 133"


# ── E-1 · the company's colour ───────────────────────────────────────────────

class BrandColourIsAlwaysAPlainHexColour(DailyCase):

	def test_133_e1_status_and_join_carry_the_brand_colour(self):
		with mock.patch.dict(frappe.conf, {"primary_color": "#1A6FA3"}):
			out = self.make()
			answer = self.joined(_code_of(out))
			self.assertEqual(answer.get("brand_colour"), "#1a6fa3", self.words())
			status = self.status(answer["token"])
			self.assertEqual(status.get("brand_colour"), "#1a6fa3", self.words())

	def test_133_e1_black_short_hex_is_widened(self):
		"""PP Jewellers' real setting is black. The app turns it into greys."""
		with mock.patch.dict(frappe.conf, {"primary_color": "#000"}):
			self.assertEqual(pwa.brand_colour(), "#000000")

	def test_133_e1_anything_that_is_not_a_hex_colour_gives_the_default(self):
		for bad in ("red", "#12345g", "#1234", "url(javascript:alert(1))", "#fff;x:y",
		            "", None, 123, "#1a6fa3 !important"):
			with self.subTest(bad=bad), mock.patch.dict(frappe.conf, {"primary_color": bad}):
				self.assertEqual(pwa.brand_colour(), DEFAULTS["primary_color"].lower())
				self.assertRegex(pwa.brand_colour(), HEX)


class SignInCarriesTheBrandColour(PasswordCase):

	def test_133_e1_the_password_sign_in_answer_has_the_colour_and_keyed_rows(self):
		with mock.patch.dict(frappe.conf, {"primary_color": "#5B4B8A"}):
			answer = self.sign_in()
		self.assertTrue(answer and answer.get("token"), self.words())
		self.assertEqual(answer["brand_colour"], "#5b4b8a")
		self.assertEqual([r["key"] for r in answer["notice"]["rows"]],
		                 ["record", "not_record", "why", "who", "how_long", "rights"])


# ── E-3 · the check-in rule ──────────────────────────────────────────────────

class TheCheckInRule(DailyCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
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
				"latitude": 28.6519, "longitude": 77.1906, "checkin_radius": 200,
			}).insert(ignore_permissions=True).name
		cls.assignment = None
		cls._tracking = frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking")
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		cls._clear_phones()
		cls._drop_assignment()
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", cls._tracking or 0)
		frappe.clear_cache(doctype="HR Settings")
		frappe.db.commit()
		super().tearDownClass()

	@classmethod
	def _drop_assignment(cls):
		if cls.assignment:
			try:
				cls.assignment.reload()
				cls.assignment.cancel()
				_bin("Shift Assignment", cls.assignment.name)
			except Exception:
				pass
			cls.assignment = None

	def assign(self):
		frappe.set_user("Administrator")
		type(self).assignment = frappe.get_doc({
			"doctype": "Shift Assignment", "employee": self.employee, "shift_type": SHIFT,
			"company": frappe.db.get_value("Employee", self.employee, "company"),
			"shift_location": self.depot, "start_date": add_days(nowdate(), -30),
		}).insert(ignore_permissions=True)
		self.assignment.submit()
		frappe.db.commit()
		frappe.set_user("Guest")

	def radius(self, metres, tracking=1):
		"""The radius, and whether HR Settings lets Frappe HR check it."""
		frappe.db.set_value("Shift Location", self.depot, "checkin_radius", metres,
		                    update_modified=False)
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", tracking)
		frappe.clear_cache(doctype="HR Settings")
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		self._drop_assignment()
		frappe.db.commit()
		super().tearDown()

	def test_133_e3_no_workplace_is_anywhere(self):
		out = self.status(self.app_phone())
		self.assertIsNone(out["workplace"], self.words())
		self.assertEqual(out["check_in_rule"], "anywhere")

	def test_133_e3_a_radius_is_radius_and_0_is_anywhere(self):
		self.assign()
		token = self.app_phone()
		self.radius(200)
		out = self.status(token)
		self.assertEqual((out["workplace"]["name"], out["check_in_rule"]), (DEPOT, "radius"),
		                 self.words())
		self.radius(0)
		out = self.status(token)
		self.assertEqual((out["workplace"]["name"], out["check_in_rule"]), (DEPOT, "anywhere"))
		self.radius(200)

	def test_133_e3_tracking_off_is_anywhere_even_with_a_radius(self):
		"""Review P2: with location tracking off, Frappe HR checks no radius, so
		the rule must be "anywhere" - never "radius" beside radius_m 0."""
		self.assign()
		token = self.app_phone()
		self.radius(200, tracking=0)
		out = self.status(token)
		self.assertEqual(out["workplace"], {"name": DEPOT, "radius_m": 0}, self.words())
		self.assertEqual(out["check_in_rule"], "anywhere")
		self.radius(200, tracking=1)
		self.assertEqual(self.status(token)["check_in_rule"], "radius")


# ── E-4 · a stable key per notice part ───────────────────────────────────────

class NoticePartsHaveStableKeys(DailyCase):

	KEYS = ["record", "not_record", "why", "who", "how_long", "rights"]

	def test_133_e4_every_version_has_the_six_keys_in_order(self):
		for version in notice.NOTICE:
			with self.subTest(version=version):
				self.assertEqual([r["key"] for r in notice.rows_for(version)], self.KEYS)

	def test_133_e4_the_key_changes_no_word_and_no_version(self):
		"""The words stay exactly as the step-1 pin holds them; the version is
		the one people agreed to on 22 Sep."""
		self.assertEqual(notice.CURRENT_VERSION, "2026-09-22")
		rows = notice.rows_for(retention_days=90)
		for (heading, body), row in zip(notice.NOTICE[notice.CURRENT_VERSION]["rows"], rows):
			self.assertEqual(row["heading"], heading)
			if body is not None:
				self.assertEqual(row["body"], body)
			self.assertEqual(sorted(row), ["body", "heading", "key"])

	def test_133_e4_a_changed_notice_refusal_carries_the_keys(self):
		token = self.app_phone()
		self.call(join.acknowledge_notice, {"token": token, "notice_version": "old"})
		status, code, values = self.answer()
		self.assertEqual(code, "NOTICE_CHANGED", self.words())
		self.assertEqual([r["key"] for r in values["rows"]], self.KEYS)


# ── E-5 · HR sees a withdrawal ───────────────────────────────────────────────

class HrSeesAWithdrawal(DeskCase):

	def test_133_e5_the_section_and_the_timeline_show_the_employee_stopped_agreeing(self):
		answer = self.joined(_code_of(self.make()))
		phone = self.app_phones()[0].name
		self.assertEqual(self.section()["state"], "joined")

		self.assertEqual(self.call(join.withdraw_agreement, {"token": answer["token"]}), {})

		section = self.section()
		self.assertEqual(section["state"], "not_agreed")
		row = next(p for p in section["phones"] if p["name"] == phone)
		self.assertEqual(row["status_change_source"], "The employee")
		self.assertTrue(row["status_changed_on"])

		frappe.set_user("Administrator")
		notes = frappe.get_all("Comment", filters={"reference_doctype": fc.DEVICE,
		                                           "reference_name": phone,
		                                           "comment_type": "Info"},
		                       pluck="content")
		frappe.set_user("Guest")
		self.assertIn("The employee stopped agreeing to the notice in the app.", notes,
		              "the phone's timeline does not say the employee stopped agreeing")

		# Withdrawing twice writes one line, not two (the second call changes nothing).
		self.call(join.withdraw_agreement, {"token": answer["token"]})
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count("Comment", {"reference_doctype": fc.DEVICE,
		                                             "reference_name": phone,
		                                             "comment_type": "Info"}), len(notes))
		frappe.set_user("Guest")
