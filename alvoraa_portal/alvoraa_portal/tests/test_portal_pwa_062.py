"""Slice 062 - the employee portal installs on a phone's home screen.

Three small things make that true, and each one is easy to lose in a merge
without anybody noticing, because the portal keeps working perfectly in a
browser when they are gone. Nothing fails; the phone just quietly stops
offering to install. So every check here names the thing it keeps alive.

  * **The page** carries the manifest link, the Apple icon and the worker
    registration. Lose any of them and no phone offers to install.
  * **The manifest** says Alvora, at /hrms-employee, standalone, with the three
    icons Chrome documents.
  * **The worker** caches nothing and is scoped to /hrms-employee.

Two of these are guards against a well-meaning tidy-up rather than against a
bug, and they are the ones that matter most:

  * `test_the_worker_caches_nothing` - decision 2 (25 Oct). A caching worker is
    a bug you cannot deploy a fix for, because the stale worker serves the
    stale fix.
  * `test_the_icon_ignores_the_tenants_own_logo` - decision 4 (27 Oct). The
    rest of the portal follows "the tenant's logo if it has one, otherwise the
    Alvora mark". The home-screen icon deliberately does not. Somebody will one
    day see that as an inconsistency and "fix" it. This stops them.
"""

import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import field_app_pwa as pwa
from alvoraa_portal.tests import portal_source

MANIFEST_URL = "/api/method/alvoraa_portal.field_app_pwa.portal_manifest"
ICON_URL = "/api/method/alvoraa_portal.field_app_pwa.portal_app_icon"
WORKER_URL = "/api/method/alvoraa_portal.field_app_pwa.portal_service_worker"


def _icon_bytes(size=192):
    """Call the endpoint the way Frappe does and take what it put on the response."""
    pwa.portal_app_icon(size)
    return frappe.local.response.filecontent


def _manifest():
    """The manifest exactly as a browser receives it - parsed from the body, not
    read off the dict the function happens to build inside itself."""
    return json.loads(pwa.portal_manifest().get_data(as_text=True))


class _ConfCase(FrappeTestCase):
    """Lets a test pretend to be a differently branded tenant, and put it back.

    `frappe.conf` is process-wide. A test that changed it and left would brand
    every later test in the same run, so the teardown restores the exact
    before-state, including "the key was absent".
    """

    KEYS = ("primary_color", "tenant_name", "tenant_logo_url")

    def setUp(self):
        self._before = {k: (k in frappe.conf, frappe.conf.get(k)) for k in self.KEYS}
        pwa._mark_mask.cache_clear()

    def tearDown(self):
        for key, (had, was) in self._before.items():
            if had:
                frappe.conf[key] = was
            else:
                frappe.conf.pop(key, None)
        pwa._mark_mask.cache_clear()

    def _as_tenant(self, **conf):
        frappe.conf.update(conf)


class PortalPageCase(FrappeTestCase):
    """The page itself. Without these tags there is nothing to install."""

    def setUp(self):
        self.page = portal_source.read_page()

    def test_the_page_links_the_portal_manifest(self):
        """No manifest, no install prompt - on any phone, ever."""
        self.assertIn('<link rel="manifest" href="%s"' % MANIFEST_URL, self.page)

    def test_the_page_carries_an_apple_touch_icon(self):
        """iPhone has no install prompt. Add to Home Screen uses this tag, and
        without it the home screen gets a screenshot of the page."""
        self.assertIn('rel="apple-touch-icon"', self.page)
        self.assertIn(ICON_URL, self.page)

    def test_the_page_registers_the_worker_at_the_portal_scope(self):
        """Chrome will not offer to install a page with no service worker.

        The scope is checked here and not only on the server, because the
        browser asks for a scope and the header permits one: if the two ever
        disagree the registration fails silently.
        """
        self.assertIn("serviceWorker", self.page)
        self.assertIn(WORKER_URL, self.page)
        self.assertIn("scope: '/hrms-employee'", self.page)

    def test_the_home_screen_name_is_alvora_not_the_tenant(self):
        """Decision 5 (27 Oct). The iPhone label is a constant, like the
        manifest's name. A tenant name here would contradict the manifest and
        give the same phone two different labels."""
        self.assertIn('name="apple-mobile-web-app-title" content="Alvora"', self.page)

    def test_the_page_does_not_claim_a_translucent_status_bar(self):
        """frame.css pins the navbar at top:0 with no safe-area inset, so a
        translucent status bar would drop the iPhone clock on top of the
        header. The check-in page can have one; this page cannot."""
        # Matched as a tag, not as a word: the page comment above the PWA tags
        # explains why the tag is absent, and naming it there is not setting it.
        self.assertNotIn('name="apple-mobile-web-app-status-bar-style"', self.page)


class PortalManifestCase(_ConfCase):
    """What the manifest promises the phone."""

    def test_the_manifest_is_served_unwrapped_as_a_browser_reads_it(self):
        """Found over HTTP, not by reading the code.

        Setting `frappe.local.response.type = "json"` and returning a dict - the
        obvious way, and the way the check-in manifest above does it - makes
        Frappe send `{"type": "json", "message": {...}}`. A browser reading a
        manifest unwraps nothing. It would see an object with no name, no
        start_url and no icons, and quietly decline to offer the install: no
        error, no warning, just no install button, forever.
        """
        body = json.loads(pwa.portal_manifest().get_data(as_text=True))
        self.assertNotIn("message", body)
        self.assertEqual(body["name"], "Alvora")
        self.assertIn("json", pwa.portal_manifest().mimetype)

    def test_the_manifest_starts_and_scopes_at_the_portal(self):
        m = _manifest()
        self.assertEqual(m["start_url"], "/hrms-employee")
        self.assertEqual(m["scope"], "/hrms-employee")
        self.assertEqual(m["display"], "standalone")

    def test_the_manifest_offers_the_three_icons_chrome_documents(self):
        """192 any, 512 any, 512 maskable. Chrome needs a 192 and a 512 to
        offer installation at all, and Android crops anything not marked
        maskable into a white box."""
        icons = _manifest()["icons"]
        self.assertEqual(
            {(i["sizes"], i["purpose"]) for i in icons},
            {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")},
        )
        for i in icons:
            self.assertEqual(i["type"], "image/png")
            self.assertTrue(i["src"].startswith(ICON_URL))

    def test_the_name_is_always_alvora_never_the_tenants(self):
        """Decision 5 (27 Oct). A factory worker's home screen says Alvora.

        This was chosen, not missed - the icon says which product this is - so
        a later change that reads tenant_name here is a reversal of a decision
        and must be made deliberately, not by tidying.
        """
        self._as_tenant(tenant_name="Delhi Transport Corporation")
        m = _manifest()
        self.assertEqual(m["name"], "Alvora")
        self.assertEqual(m["short_name"], "Alvora")
        self.assertNotIn("Delhi", json.dumps(m))

    def test_the_theme_colour_follows_the_tenant(self):
        """The one thing that IS per tenant. The manifest's theme colour is
        what Android paints the title bar of the installed app."""
        self._as_tenant(primary_color="#0A7A4B")
        green = _manifest()["theme_color"]
        self._as_tenant(primary_color="#5B4B8A")
        purple = _manifest()["theme_color"]
        self.assertNotEqual(green, purple)


class PortalIconCase(_ConfCase):
    """The icon: always the Alvora mark, always on the tenant's colour."""

    def _image(self, size=192):
        from io import BytesIO

        from PIL import Image

        return Image.open(BytesIO(_icon_bytes(size)))

    def test_the_icon_ignores_the_tenants_own_logo(self):
        """Decision 4 (27 Oct), and the whole reason this file exists.

        tenant_context.get_branding() sets brand_mark_url to "the tenant's own
        logo if it has one". The home-screen icon does NOT follow that rule, on
        purpose. Same colour, same bytes, logo or no logo.
        """
        self._as_tenant(primary_color="#5B4B8A", tenant_logo_url="")
        plain = _icon_bytes(192)
        pwa._mark_mask.cache_clear()
        self._as_tenant(primary_color="#5B4B8A",
                        tenant_logo_url="/files/a-customers-own-logo.png")
        self.assertEqual(plain, _icon_bytes(192))

    def test_the_icon_is_drawn_on_the_tenants_colour(self):
        """The colour is the only per-tenant thing left, so it must actually
        reach the icon."""
        self._as_tenant(primary_color="#0A7A4B")
        green = self._image().getpixel((0, 0))
        pwa._mark_mask.cache_clear()
        self._as_tenant(primary_color="#5B4B8A")
        self.assertNotEqual(green, self._image().getpixel((0, 0)))

    def test_a_maskable_icon_is_filled_to_every_edge(self):
        """Android crops a maskable icon to the launcher's shape. A transparent
        or light corner shows as a notch, so the ground must reach all four."""
        img = self._image(192)
        self.assertEqual(img.mode, "RGB")  # no alpha channel at all
        corners = {img.getpixel(p) for p in ((0, 0), (191, 0), (0, 191), (191, 191))}
        self.assertEqual(len(corners), 1)

    def test_the_mark_stays_inside_the_circle_android_will_not_crop(self):
        """Android promises only the middle 80 % by diameter. Anything of the
        mark outside that circle can be sliced off by a launcher."""
        size = 192
        img = self._image(size).convert("L")
        ground = img.getpixel((0, 0))
        centre = (size - 1) / 2
        safe = (size * 0.80 / 2) ** 2
        outside = [
            (x, y)
            for y in range(size)
            for x in range(size)
            if (x - centre) ** 2 + (y - centre) ** 2 > safe
            and abs(img.getpixel((x, y)) - ground) > 24
        ]
        self.assertEqual(outside, [], "the mark is drawn outside the safe circle")

    def test_the_icon_survives_a_tenant_colour_that_is_not_a_colour(self):
        """Branding comes from site config, which a platform operator types by
        hand. A bad value must give the default icon, never a 500 - a phone
        with a broken icon cannot be installed at all.
        """
        self._as_tenant(primary_color="not a colour")
        self.assertTrue(_icon_bytes(192))

    def test_white_on_the_ground_passes_contrast_even_for_a_pale_brand(self):
        """The mark is painted white, so a tenant whose brand is pale yellow
        would lose it entirely if the ground were only a fixed shade darker.
        _darker() keeps darkening until white passes WCAG AA; this proves the
        icon uses that and not the raw brand colour."""
        self._as_tenant(primary_color="#FFF9C4")
        r, g, b = self._image(192).getpixel((0, 0))

        def channel(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

        lum = 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
        self.assertGreaterEqual(1.05 / (lum + 0.05), 4.5)

    def test_the_mark_comes_from_the_master_artwork(self):
        """One artwork file to replace is the point of the brand design. If the
        icon ever stops reading it, a logo change would miss the home screen."""
        self.assertTrue(os.path.exists(pwa._MARK_SOURCE))
        self.assertTrue(pwa._MARK_SOURCE.endswith("alvoraa-logo-master.jpg"))


class PortalWorkerCase(FrappeTestCase):
    """The worker: it must do nothing, and it must do nothing widely."""

    def test_the_worker_caches_nothing(self):
        """Decision 2 (25 Oct), and the single most important line here.

        The portal page carries the signed-in user and the CSRF token, so it
        must never enter a shared store. And a caching worker is a bug you
        cannot deploy a fix for: the stale worker serves the stale fix. Before
        anyone adds caching, the build version must be inside the worker body
        and a kill switch must exist.
        """
        body = pwa._PORTAL_SERVICE_WORKER
        for forbidden in ("caches", "cache.put", "respondWith", "CacheStorage"):
            self.assertNotIn(forbidden, body)

    def test_the_worker_is_scoped_to_the_portal_and_not_the_whole_site(self):
        """Decision 3 (25 Oct). The check-in worker is allowed "/" only because
        it does nothing at all. Copying that here would hand this worker
        /checkin, the login page and the entire desk."""
        headers = pwa.portal_service_worker().headers
        self.assertEqual(headers["Service-Worker-Allowed"], "/hrms-employee")

    def test_the_portal_scope_does_not_cover_the_other_doors(self):
        """A worker controls a page when the page's path starts with its scope.
        These three must stay outside it."""
        for path in ("/checkin", "/alvoraa-login", "/app", "/"):
            self.assertFalse(path.startswith(pwa._PORTAL_SCOPE), path)

    def test_the_worker_is_served_as_javascript_and_never_cached(self):
        """A browser refuses to register a worker not served as JavaScript, and
        a worker frozen by a cache header is a month-long outage waiting."""
        r = pwa.portal_service_worker()
        self.assertIn("javascript", r.mimetype)
        self.assertEqual(r.headers["Cache-Control"], "no-cache, no-store, must-revalidate")


class CheckinAppUntouchedCase(FrappeTestCase):
    """Slice 062 adds a second app. It must not disturb the first one.

    A check-in page already installed on a driver's phone keeps working only if
    its three URLs and its manifest keep saying exactly what they said before.
    """

    def test_the_checkin_manifest_still_points_at_checkin(self):
        # Read from the body, not from a returned dict: ALV-237 changed the
        # check-in manifest to answer the way this one always has.
        m = json.loads(pwa.manifest().get_data(as_text=True))
        self.assertEqual(m["start_url"], "/checkin")
        self.assertEqual(m["scope"], "/checkin")
        self.assertTrue(
            all("field_checkin.app_icon" in i["src"] for i in m["icons"]),
            "the check-in manifest must keep its own icon URL",
        )

    def test_the_checkin_endpoints_keep_their_old_addresses(self):
        """They are reached at alvoraa_portal.field_checkin.*, not at this
        module's name, because that is the address on phones in the field."""
        from alvoraa_portal import field_checkin

        self.assertIs(field_checkin.manifest, pwa.manifest)
        self.assertIs(field_checkin.app_icon, pwa.app_icon)
        self.assertIs(field_checkin.service_worker, pwa.service_worker)
