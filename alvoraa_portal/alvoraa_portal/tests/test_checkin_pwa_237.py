"""ALV-237 - the check-in page installs on a phone's home screen.

The page had a manifest, a service worker, an icon and the Apple tags from the
day it shipped, and it was never once installable. The manifest was returned as
a dict, so Frappe wrapped it the way it wraps every whitelisted answer:

    {"type": "json", "message": {"name": ..., "start_url": ..., ...}}

A browser reading a manifest unwraps nothing. It saw an object with no name, no
start_url and no icons, decided the page was not installable, and said nothing
at all - to the driver, and to us. Nothing failed. There was simply never an
install prompt, from 13 Sep 2026 until this was fixed on 29 Oct.

Slice 062 had already hit the identical wall on the employee portal and fixed
it properly. So the checks that matter here are not "does the manifest have the
right fields" - it always did. They are:

  * the answer is the JSON itself, with nothing wrapped round it, and
  * nothing in this function touches `frappe.local.response` again.

The rest guard a phone that ALREADY has the page on its home screen. Its icon
points at a URL, and its scope is matched against a path. Move either and that
phone's app breaks, with no way to tell its owner.
"""

import inspect
import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import field_app_pwa as pwa

MANIFEST_URL = "/api/method/alvoraa_portal.field_checkin.manifest"
ICON_URL = "/api/method/alvoraa_portal.field_checkin.app_icon"
WORKER_URL = "/api/method/alvoraa_portal.field_checkin.service_worker"

PAGE = os.path.join(
	os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "www", "field-checkin.html"
)


def _manifest():
	"""The manifest exactly as a phone receives it - parsed from the body, never
	read off whatever dict the function builds inside itself. Reading the dict
	is what let the bug live: every field was correct in there."""
	return json.loads(pwa.manifest().get_data(as_text=True))


class _ConfCase(FrappeTestCase):
	"""Lets a test pretend to be a differently branded customer, and put it back.

	`frappe.conf` is process-wide, so a test that changed it and walked away
	would brand every later test in the same run. The teardown restores the
	exact before-state, including "the key was not there at all".
	"""

	KEYS = ("primary_color", "tenant_name")

	def setUp(self):
		self._before = {k: frappe.conf.get(k, KeyError) for k in self.KEYS}

	def tearDown(self):
		for k, v in self._before.items():
			if v is KeyError:
				frappe.conf.pop(k, None)
			else:
				frappe.conf[k] = v

	def as_tenant(self, **kwargs):
		for k, v in kwargs.items():
			frappe.conf[k] = v


class TheWrapperIsGoneCase(FrappeTestCase):
	"""The bug itself. Every one of these would have failed before ALV-237."""

	def test_the_manifest_is_served_unwrapped_as_a_browser_reads_it(self):
		body = json.loads(pwa.manifest().get_data(as_text=True))

		self.assertNotIn("message", body, "Frappe's wrapper is back")
		self.assertNotIn("type", body, "Frappe's wrapper is back")
		self.assertIn("name", body)
		self.assertIn("start_url", body)
		self.assertIn("icons", body)

	def test_nothing_in_it_touches_the_frappe_response_again(self):
		"""The exact line that caused this: it set `frappe.local.response.type`
		and returned a dict. A tidy-up that puts that back brings the whole bug
		back, and every field check above would still pass."""
		source = inspect.getsource(pwa.manifest)

		self.assertNotIn("frappe.local.response", source)

	def test_it_is_served_as_a_manifest_and_not_as_a_download(self):
		self.assertIn("json", pwa.manifest().mimetype)

	def test_it_answers_200(self):
		self.assertEqual(pwa.manifest().status_code, 200)


class TheCacheHeaderCase(FrappeTestCase):
	"""Chrome asks for the manifest again on in-scope navigations, so a day in
	the phone's own cache is worth having. It must not be worth having in
	anybody else's."""

	def test_the_manifest_is_cached_in_the_phone_and_nowhere_shared(self):
		"""`private`, deliberately - NOT the `public` the portal manifest uses.

		That one is byte-identical for every customer. This one carries the
		customer's own name, and a shared proxy keyed on the path alone would
		hand one customer's name to the next.
		"""
		cache = pwa.manifest().headers.get("Cache-Control", "")

		self.assertIn("private", cache)
		self.assertNotIn("public", cache)
		self.assertIn("max-age", cache)


class APhoneThatAlreadyHasItCase(FrappeTestCase):
	"""Nothing here is new behaviour. Every check is a pin: a phone with the app
	on its home screen keeps working only while these stay exactly as they were
	before ALV-237 touched the function."""

	def test_it_still_starts_and_scopes_at_checkin(self):
		m = _manifest()

		self.assertEqual(m["start_url"], "/checkin")
		self.assertEqual(m["scope"], "/checkin")

	def test_the_icons_keep_their_own_addresses(self):
		"""The check-in app's icon endpoint, not the portal's. The two draw
		different pictures - a tick here, the Alvora mark there."""
		m = _manifest()

		self.assertTrue(all("field_checkin.app_icon" in i["src"] for i in m["icons"]))

	def test_it_offers_the_three_icons_chrome_documents(self):
		sizes = {(i["sizes"], i["purpose"]) for i in _manifest()["icons"]}

		self.assertIn(("192x192", "any"), sizes)
		self.assertIn(("512x512", "any"), sizes)
		self.assertIn(("512x512", "maskable"), sizes)

	def test_it_opens_standalone_and_upright(self):
		"""A camera page held in one hand. The portal deliberately does not pin
		an orientation; this one must."""
		m = _manifest()

		self.assertEqual(m["display"], "standalone")
		self.assertEqual(m["orientation"], "portrait")

	def test_a_driver_who_is_not_signed_in_can_still_fetch_it(self):
		"""The page is opened before any device is registered, by somebody with
		no session at all. A manifest behind a login is a manifest Chrome
		cannot read."""
		self.assertIn(pwa.manifest, frappe.whitelisted)
		self.assertIn(pwa.manifest, frappe.guest_methods)


class ItIsTheCustomersOwnAppCase(_ConfCase):
	"""Unlike the portal's, this manifest is branded per customer. Decision 5
	(27 Oct) fixed the portal's name to "Alvora"; it was never applied here and
	must not be - a driver is handed this page as their employer's attendance
	app, not as ours."""

	def test_the_name_is_the_customers(self):
		self.as_tenant(tenant_name="Minda Corp")

		self.assertEqual(_manifest()["name"], "Minda Corp")

	def test_the_short_name_fits_a_home_screen_label(self):
		self.as_tenant(tenant_name="A Very Long Manufacturing Company Limited")

		self.assertLessEqual(len(_manifest()["short_name"]), 12)

	def test_the_theme_colour_follows_the_customers_brand(self):
		self.as_tenant(primary_color="#1B7F5A")
		first = _manifest()["theme_color"]

		self.as_tenant(primary_color="#B3261E")
		second = _manifest()["theme_color"]

		self.assertNotEqual(first, second)

	def test_a_colour_that_is_not_a_colour_does_not_break_the_manifest(self):
		"""Site config is edited by hand. The install must not depend on it
		being right."""
		self.as_tenant(primary_color="purple-ish")

		self.assertRegex(_manifest()["theme_color"], r"^#[0-9a-f]{6}$")


class ThePageStillAsksForItCase(FrappeTestCase):
	"""Three tags and one registration. The page works perfectly in a browser
	with all four gone, and no phone ever offers to install it - which is how
	this went unnoticed for six weeks."""

	def setUp(self):
		with open(PAGE, encoding="utf-8") as f:
			self.page = f.read()

	def test_the_page_links_the_manifest_at_the_address_phones_know(self):
		self.assertIn('<link rel="manifest" href="%s"' % MANIFEST_URL, self.page)

	def test_the_page_carries_an_apple_touch_icon(self):
		"""iPhone has no install prompt and does not read the manifest for Add
		to Home Screen. Without this tag the home screen gets a screenshot."""
		self.assertIn('rel="apple-touch-icon"', self.page)
		self.assertIn(ICON_URL, self.page)

	def test_the_page_registers_the_worker_at_the_checkin_scope(self):
		"""Chrome will not offer to install a page with no service worker. The
		scope the browser asks for and the scope the header permits have to
		agree, or the registration fails silently."""
		self.assertIn(WORKER_URL, self.page)
		self.assertIn('scope: "/checkin"', self.page)

	def test_the_worker_is_served_as_javascript_and_scoped_wide_enough(self):
		r = pwa.service_worker()

		self.assertIn("javascript", r.mimetype)
		self.assertTrue(r.headers.get("Service-Worker-Allowed"))
