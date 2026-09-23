"""Slice 025 — the Alvoraa logo, for every tenant, and never a broken image.

The reported fault was a broken-image icon on the portal. Behind it were three
separate faults:

  1. the logo was a PRIVATE file - `/private/files/381140.jpg` in Website
     Settings - and a browser cannot read one, so it rendered as broken;
  2. no Alvoraa image shipped in any app, so there was nothing to fall back to;
  3. the portal's brand tile painted its letter in `var(--surface)` on a
     `var(--surface)` ground - the same token - so the fallback everybody assumed
     was there had been an invisible letter on an empty square all along.

These tests exist so a bad merge cannot take any of the three fixes back out, and
so nobody later "simplifies" the repair into one that overwrites a paying
customer's own logo.

The one that matters most is `test_the_patch_leaves_a_deliberate_logo_alone`. A
patch that runs once across every live customer and sets a logo unconditionally
would delete their branding. That test is the thing standing between this code
and that outcome.
"""

import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import brand
from alvoraa_portal.tenant_context import get_branding


# Built from __file__ rather than frappe.get_app_path(), which scrubs its
# arguments and so turns "hrms-employee.html" into "hrms_employee.html".
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PUBLIC = os.path.join(APP_ROOT, "public", "images")
WWW = os.path.join(APP_ROOT, "www")

# Every asset brand.py promises, and the URL each must be served at.
EXPECTED = {
    "alvoraa-mark.png": brand.MARK,
    "alvoraa-logo.png": brand.LOGO,
    "alvoraa-favicon.png": brand.FAVICON,
}


class BrandAssetCase(FrappeTestCase):
    """The files exist, at the paths the pages reference."""

    def test_the_alvoraa_mark_resolves_for_a_fresh_site(self):
        """The asset is in the app, so it needs no per-tenant upload.

        Deliberately a filesystem check and not an HTTP one. `/assets/<app>/...`
        is served by nginx straight off `sites/assets`, which is populated by
        `bench build`; a fresh CI site has run `install-app` and nothing else. So
        the thing that is true on every site, with no build and no web server, is
        that the file is inside the app at the path the URL maps to. If that
        holds, the URL holds wherever assets are built - and if it does not, no
        amount of building will help.
        """
        for name, url in EXPECTED.items():
            path = os.path.join(APP_PUBLIC, name)
            self.assertTrue(
                os.path.isfile(path),
                f"{name} is missing from alvoraa_portal/public/images - "
                f"{url} would 404 on every tenant",
            )
            self.assertEqual(
                url,
                f"/assets/alvoraa_portal/images/{name}",
                "the URL in brand.py and the file on disk have drifted apart",
            )
            self.assertGreater(os.path.getsize(path), 200, f"{name} looks empty")

    def test_the_brand_assets_stay_small_enough_for_a_phone(self):
        """nfr-budget.md section 2: employee surfaces, 3G, p95 2.5 s.

        A 1600x1600 JPEG master was the starting point; shipping it would have
        been 84 KB for a 32-pixel tile. The ceiling here is deliberately loose -
        it is a guard against somebody dropping the master straight in, not a
        pixel-level style rule.
        """
        total = sum(os.path.getsize(os.path.join(APP_PUBLIC, n)) for n in EXPECTED)
        self.assertLess(
            total, 40 * 1024,
            f"brand assets total {total} bytes. Re-run scripts/make_brand_assets.py "
            f"rather than committing a master-sized image",
        )

    def test_the_master_artwork_is_not_served(self):
        """The master is version-controlled but must never be a public asset.

        One artwork file to replace is the point of the design; serving it as
        well would mean a browser fetching 84 KB to draw 32 pixels.
        """
        served = os.listdir(APP_PUBLIC)
        self.assertNotIn("alvoraa-logo-master.jpg", served)
        for name in served:
            self.assertTrue(
                name in EXPECTED or name.startswith("."),
                f"{name} is in public/images but brand.py does not know about it",
            )


class BrandRuleCase(FrappeTestCase):
    """The rule: the tenant's logo wins; the Alvoraa mark fills the gap."""

    def setUp(self):
        self._had = "tenant_logo_url" in frappe.conf
        self._was = frappe.conf.get("tenant_logo_url")

    def tearDown(self):
        if self._had:
            frappe.conf["tenant_logo_url"] = self._was
        else:
            frappe.conf.pop("tenant_logo_url", None)

    def test_a_tenant_with_its_own_logo_keeps_it(self):
        """This is the line between "our product" and "their company".

        A tenant's logo lives in site_config.json as `tenant_logo_url`, written at
        provisioning. Branding the product must never write over it.
        """
        frappe.conf["tenant_logo_url"] = "/files/pp-jewellers-logo.png"
        b = get_branding()
        self.assertEqual(b["brand_mark_url"], "/files/pp-jewellers-logo.png")
        self.assertEqual(b["brand_logo_url"], "/files/pp-jewellers-logo.png")
        self.assertNotEqual(b["brand_mark_url"], brand.MARK)

    def test_a_tenant_with_no_logo_gets_the_alvoraa_mark(self):
        frappe.conf.pop("tenant_logo_url", None)
        b = get_branding()
        self.assertEqual(b["brand_mark_url"], brand.MARK)
        self.assertEqual(b["brand_logo_url"], brand.LOGO)

    def test_the_tenants_own_setting_is_still_readable(self):
        """Callers must still be able to ask "did this tenant set a logo?"."""
        frappe.conf.pop("tenant_logo_url", None)
        self.assertEqual(get_branding()["tenant_logo_url"], "")


class BrandRepairCase(FrappeTestCase):
    """The patch: repair the unreadable, never touch a decision."""

    SLOTS = [(d, f) for d, f, _ in brand.SLOTS]

    def setUp(self):
        self._saved = {
            (d, f): frappe.db.get_single_value(d, f, cache=False)
            for d, f in self.SLOTS
        }

    def tearDown(self):
        for (d, f), v in self._saved.items():
            frappe.db.set_single_value(d, f, v)
        frappe.db.commit()

    def test_the_patch_repairs_a_private_file_path(self):
        """The reported bug, as a test.

        `/private/files/...` in a page is unreadable to a browser however the
        file's permissions are set, so there is no version of this value that
        works and it is always safe to replace.
        """
        frappe.db.set_single_value("Website Settings", "favicon",
                                   "/private/files/381140.jpg")
        result = brand.apply_site_branding()
        self.assertEqual(
            frappe.db.get_single_value("Website Settings", "favicon", cache=False),
            brand.FAVICON,
        )
        self.assertEqual(result["changed"].get("Website Settings.favicon"), "broken")

    def test_the_patch_leaves_a_deliberate_logo_alone(self):
        """The test that stops this patch destroying a customer's branding.

        A public `/files/...` path renders perfectly well. Somebody chose it. It
        stays, and so does an external URL.
        """
        for value in ("/files/their-own-logo.png",
                      "https://cdn.example.com/logo.svg"):
            with self.subTest(value=value):
                frappe.db.set_single_value("Website Settings", "app_logo", value)
                result = brand.apply_site_branding()
                self.assertEqual(
                    frappe.db.get_single_value("Website Settings", "app_logo",
                                               cache=False),
                    value,
                    "the patch overwrote a logo the tenant had chosen",
                )
                self.assertNotIn("Website Settings.app_logo", result["changed"])
                self.assertIn("Website Settings.app_logo", result["left_alone"])

    def test_an_empty_slot_is_filled(self):
        frappe.db.set_single_value("Navbar Settings", "app_logo", None)
        brand.apply_site_branding()
        self.assertEqual(
            frappe.db.get_single_value("Navbar Settings", "app_logo", cache=False),
            brand.MARK,
        )

    def test_the_desk_logo_cannot_be_left_to_the_hook(self):
        """Why `Navbar Settings.app_logo` is written at all.

        Frappe resolves the `app_logo_url` hook as `logos[0]`, and only picks
        `logos[1]` when there are exactly two. frappe, erpnext and hrms all
        declare it, so the winner is frappe's OWN framework logo and a fourth
        declaration would change nothing. If that ever stops being true this test
        fails and somebody gets to delete code - which is the good outcome.
        """
        logos = frappe.get_hooks("app_logo_url")
        self.assertGreater(
            len(logos), 2,
            "only two apps declare app_logo_url now - the hook may work again; "
            "re-read navbar_settings.get_app_logo() before trusting it",
        )
        self.assertIn(("Navbar Settings", "app_logo"), self.SLOTS)

    def test_running_it_twice_changes_nothing_the_second_time(self):
        brand.apply_site_branding()
        again = brand.apply_site_branding()
        self.assertEqual(
            again["changed"], {},
            "apply_site_branding is not safe to run twice",
        )


class PortalRenderCase(FrappeTestCase):
    """The rendered page: a real mark, a real fallback, no private path."""

    PAGE = os.path.join(WWW, "hrms-employee.html")
    LOGIN = os.path.join(WWW, "alvoraa-login.html")

    def _read(self, path):
        """The portal page arrives with its Jinja includes expanded (US-10, AC-37)."""
        from alvoraa_portal.tests import portal_source

        if os.path.abspath(path) == os.path.abspath(portal_source.PORTAL_PAGE):
            return portal_source.read_page(encoding="utf-8")
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def test_the_portal_never_renders_a_broken_image(self):
        """Three things have to be true of the sidebar brand tile at once."""
        html = self._read(self.PAGE)
        tile = re.search(r'<div class="sidebar-brand-logo">(.*?)</div>', html)
        self.assertIsNotNone(tile, "the sidebar brand tile has moved or been renamed")
        block = tile.group(1)

        # 1. it draws the resolved mark, not a hard-coded path and not a site file
        self.assertIn("brand_mark_url", block)
        self.assertNotIn("/private/files/", block)
        self.assertNotIn("/files/", block)
        #
        # Scoped to the tile, NOT to the whole page, and that is deliberate. The
        # page legitimately contains the string "/private/files/" in
        # `_safeFileUrl`, which is slice 010's allowlist for goal evidence links
        # (SEC-11): it draws a link ONLY when the URL starts with our own private
        # files prefix, and nothing otherwise. A file-wide assertion here would
        # fail on that correct security code, and the first version of this test
        # did exactly that. What this slice cares about is that the BRAND tile
        # never points at a site file, because a browser cannot read one.

        # 2. the tenant's initial is still there underneath, as the last resort
        self.assertIn("tenant_name[0] | upper", block)

        # 3. a failed image takes itself out of the way so the letter shows
        self.assertIn("onerror", block)

    def test_the_brand_tile_letter_is_no_longer_invisible(self):
        """Fault 3: background and colour were the same custom property.

        Worth its own test because it is a bug in its own right, it was silent,
        and a careless merge of the CSS block would bring it straight back.
        """
        html = self._read(self.PAGE)
        rule = re.search(r"\.sidebar-brand-logo\{(.*?)\}", html, re.S)
        self.assertIsNotNone(rule, "the .sidebar-brand-logo rule has moved")
        # Strip CSS comments first. The rule carries a comment quoting the old
        # broken declaration so nobody reintroduces it, and without this the
        # regex below reads that comment as the live value. The first version of
        # this test did exactly that and failed on correct code.
        body = re.sub(r"/\*.*?\*/", "", rule.group(1), flags=re.S)
        bg = re.search(r"background:\s*var\((--[a-z0-9-]+)\)", body)
        fg = re.search(r"color:\s*var\((--[a-z0-9-]+)\)", body)
        self.assertIsNotNone(bg)
        self.assertIsNotNone(fg)
        self.assertNotEqual(
            bg.group(1), fg.group(1),
            "the brand tile paints its letter in the same token as its own "
            "background again - the letter is invisible",
        )

    def test_the_login_page_brands_itself_before_first_paint(self):
        """The sign-in page is the first screen a customer's staff ever see.

        The mark used to arrive from JavaScript after the page had drawn. It is
        rendered server side now, and the placeholder SVG stays behind it.
        """
        html = self._read(self.LOGIN)
        self.assertIn("brand_mark_url", html)
        self.assertIn("kx-logo-mark.has-mark", html)
        self.assertIn("kx-logo-svg", html, "the last-resort SVG has been deleted")

    def test_every_branded_page_gets_the_resolved_urls(self):
        """get_branding() is the one door, so every page walks through it."""
        for page in ("hrms_employee", "alvoraa_login", "goals_portal",
                     "vendor_portal", "driver_portal"):
            path = os.path.join(WWW, page + ".py")
            with self.subTest(page=page):
                self.assertIn("get_branding", self._read(path))
