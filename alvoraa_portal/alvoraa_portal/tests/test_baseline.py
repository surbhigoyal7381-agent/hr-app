"""The settings a new tenant starts with, and the guards around them.

Two things are being protected here, and they pull in opposite directions:

    A new tenant must GET the defaults.
    An existing tenant must KEEP what it has.

The second is the one worth writing tests for, because getting it wrong is
silent. Nothing errors when a deploy quietly reverts a customer's configuration
back to ours - they just find their setting changed one morning and have no way
to know why. That is the failure `fixtures` has by design, and the reason this
module exists.
"""

import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import baseline


class TestWhatShips(FrappeTestCase):
    """The lists are the security boundary. Everything named lands in every
    tenant we create from now on, including customers we have never met."""

    def test_nothing_sweeps_a_whole_doctype(self):
        """The failure this module was redesigned around.

        Capturing "all Custom DocPerm" from a real tenant produced 582 rows, of
        which 264 were written by our own access control and encoded THAT
        TENANT'S PLAN. Every new customer would have been born carrying another
        customer's subscription. Each list must name its members.
        """
        for name in ("PERMISSION_DEFAULTS", "CUSTOMISED_DOCTYPES"):
            value = getattr(baseline, name)
            self.assertIsInstance(value, list)
            for entry in value:
                self.assertIsInstance(entry, str,
                    f"{name} must name doctypes, not describe a query")

    def test_permissions_ship_only_for_named_doctypes(self):
        """A filter-free export is what caused the problem above."""
        import inspect

        src = inspect.getsource(baseline.capture)
        self.assertIn("PERMISSION_DEFAULTS", src)
        self.assertIn("filters=", src)

    def test_letter_head_is_the_first_decision(self):
        """Approved 2026-08-30: HR Manager and System Manager only."""
        self.assertIn("Letter Head", baseline.PERMISSION_DEFAULTS)
        self.assertIn("Letter Head",
            baseline.SELECT_REMOVALS.get("Employee Self Service", []))

    def test_the_letter_head_decision_has_both_halves(self):
        """Permissions alone do not hold. Frappe HR regenerates select rows from
        the User Type, so the removal has to be there too or the restriction
        comes back on the next migration."""
        self.assertTrue(baseline.SELECT_REMOVALS,
            "a permission decision on a select-listed doctype needs the removal too")

    def test_select_removals_subtract_rather_than_replace(self):
        """Shipping the whole User Type would freeze one tenant's copy of a list
        Frappe HR maintains, holding back their future additions."""
        import inspect

        src = inspect.getsource(baseline._apply_select_removals)
        self.assertIn("not in doctypes", src)

    def test_no_customer_data_is_shipped(self):
        shipped = set(baseline.PERMISSION_DEFAULTS) | set(baseline.CUSTOMISED_DOCTYPES)
        leaked = shipped & set(baseline.EXCLUDED)
        # Letter Head is the deliberate, documented split: its PERMISSIONS ship,
        # its content does not.
        leaked.discard("Letter Head")
        self.assertEqual(leaked, set(),
            f"these hold customer data and must never ship: {leaked}")

    def test_letter_head_content_is_still_excluded(self):
        self.assertIn("Letter Head", baseline.EXCLUDED)
        self.assertIn("PERMISSIONS ship", baseline.EXCLUDED["Letter Head"])

    def test_the_excluded_list_says_why(self):
        """A bare list invites someone to add an entry back. A reason does not."""
        for dt, why in baseline.EXCLUDED.items():
            self.assertTrue(why and len(why) > 10, f"{dt} is excluded without a reason")

    def test_capture_refuses_to_run_on_the_control_plane(self):
        import inspect

        self.assertIn("alvoraa_control_plane", inspect.getsource(baseline.capture))


class TestItRunsOnce(FrappeTestCase):
    """The guard that makes defaults overridable rather than enforced."""

    def setUp(self):
        frappe.set_user("Administrator")
        self._saved = baseline._already_applied()

    def tearDown(self):
        frappe.db.rollback()

    def _mark(self, value):
        doc = frappe.get_single(baseline.STATE)
        doc.baseline_applied = value
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)

    def test_a_seeded_site_is_not_seeded_again(self):
        """This is the whole point. A second run would overwrite whatever the
        tenant changed in between."""
        self._mark("1")
        out = baseline.apply()
        self.assertTrue(out.get("skipped"))
        self.assertIn("already applied", out.get("reason", ""))

    def test_the_reason_explains_the_risk(self):
        """An operator reading this in a provisioning log should understand why
        it refused, not just that it did."""
        self._mark("1")
        out = baseline.apply()
        self.assertIn("overwrite", out["reason"].lower())

    def test_force_is_available_for_support(self):
        """Deliberate, per-tenant support work is allowed. It is just never
        something a deploy does on its own."""
        import inspect

        sig = inspect.signature(baseline.apply)
        self.assertIn("force", sig.parameters)
        self.assertIs(sig.parameters["force"].default, False)

    def test_a_site_with_no_captured_baseline_does_nothing(self):
        """Before anyone has captured anything, provisioning must still work."""
        self._mark(None)
        if os.path.isdir(baseline._baseline_dir()):
            self.skipTest("a baseline has been captured on this checkout")
        out = baseline.apply()
        self.assertTrue(out.get("skipped"))


class TestExistingTenantsAreLeftAlone(FrappeTestCase):
    """Decided explicitly on 2026-08-30: live tenants keep their configuration,
    and any change to it is a separate, deliberate act."""

    def test_provisioning_seeds_but_updating_does_not(self):
        """If apply() were wired into update_tenant, then every tenant alive
        today - none of which has been seeded - would be retro-fitted the next
        time anyone edited their plan. That is the opposite of the decision."""
        import inspect

        from alvoraa_portal import tenant_api

        provision = inspect.getsource(tenant_api._run_provision)
        update = inspect.getsource(tenant_api.update_tenant)

        self.assertIn("baseline.apply", provision,
            "a new tenant must be seeded during provisioning")
        self.assertNotIn("baseline.apply", update,
            "seeding on plan update would retro-fit every existing tenant")

    def test_there_is_no_apply_to_all_helper(self):
        """A convenience that seeds every tenant at once is exactly the thing
        that turns one mistake into every customer's mistake."""
        import inspect

        src = inspect.getsource(baseline)
        for banned in ("def apply_all", "def backfill", "for site in"):
            self.assertNotIn(banned, src)


class TestItIsNotAFixture(FrappeTestCase):
    """Frappe re-imports fixtures on every migrate with force=True. If this data
    ever lands in a fixtures/ folder or the fixtures hook, tenant overrides start
    being reverted on deploy and nothing reports it."""

    def test_the_json_is_not_in_a_fixtures_folder(self):
        self.assertTrue(baseline._baseline_dir().endswith("baseline"))
        self.assertNotIn(os.sep + "fixtures", baseline._baseline_dir())

    def test_the_fixtures_hook_does_not_carry_what_we_ship(self):
        """A doctype in both places is the worst of both: we seed it once as an
        overridable default, and the fixtures sync then force-overwrites the
        tenant's version of it on every deploy."""
        hooked = frappe.get_hooks("fixtures") or []
        names = {h if isinstance(h, str) else h.get("doctype") for h in hooked}
        shipped = ({"Custom DocPerm", "Custom Field", "Property Setter", "User Type"}
                   | set(baseline.PERMISSION_DEFAULTS)
                   | set(baseline.CUSTOMISED_DOCTYPES))
        clash = names & shipped
        self.assertEqual(clash, set(),
            f"these would be force-overwritten on every migrate: {clash}")
