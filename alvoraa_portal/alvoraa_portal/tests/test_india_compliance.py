"""Indian Compliance is sold, installed on demand, and refuses to stand alone.

The app is `india-compliance` from resilient-tech: GST returns, e-invoicing,
e-way bills, TDS on vendor payments, and the Companies Act audit trail.

Two things about it drive every test here.

It is NOT an HR feature. All 25 of its doctypes hang off Sales Invoice,
Purchase Invoice or the Accounts module, and it declares
required_apps = ["frappe/erpnext"]. On an HR-only tenant there is nothing for
it to act on - so it is installed only where it was bought, the same way
alvoraa_goals is.

And it cannot stand on its own. Ticking it without the ERPNext modules that
provide those documents installs an app whose every screen is then refused by
our own access control. The tenant sees a product they paid for and cannot
open, with nothing in the UI explaining why. So the selection is refused up
front, and deliberately NOT auto-corrected: silently switching on Accounts,
Selling and Buying because a fourth box was ticked would hand over three
modules nobody bought.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import subscription as sub


class TestItIsSellable(FrappeTestCase):
    def test_the_feature_exists(self):
        self.assertIn("india_compliance", sub.ERPNEXT_FEATURES)
        self.assertNotIn("india_compliance", sub.FEATURES,
            "FEATURES is the HR product, and `enterprise` is defined as all of it")

    def test_it_declares_its_app_so_it_installs_on_demand(self):
        """`app` is what provisioning and update_tenant key off. Without it the
        feature would gate the UI while the app was never installed."""
        self.assertEqual(sub.feature_spec("india_compliance")["app"], "india_compliance")

    def test_it_claims_all_four_of_its_modules(self):
        """A module the registry does not name is denied by default - correct for
        an app nobody bought, wrong for one they did."""
        got = set(sub.feature_spec("india_compliance")["module_defs"])
        self.assertEqual(
            got, {"GST India", "Income Tax India", "VAT India", "Audit Trail"})

    def test_it_is_not_in_any_standard_plan(self):
        """It needs ERPNext accounting, which no standard HR plan includes."""
        for plan, feats in sub.PLANS.items():
            self.assertNotIn("india_compliance", feats, f"plan {plan}")

    def test_it_is_not_required(self):
        self.assertNotIn("india_compliance", sub.REQUIRED)


class TestItRefusesToStandAlone(FrappeTestCase):
    BASE = ["hrms", "portal", "leaves", "attendance", "expenses", "hr_setup"]

    def test_ticking_it_alone_is_refused(self):
        unmet = sub.unmet_requirements(self.BASE + ["india_compliance"])
        self.assertIn("india_compliance", unmet)
        self.assertEqual(set(unmet["india_compliance"]),
                         {"erp_accounts", "erp_selling", "erp_buying"})

    def test_the_message_names_what_is_missing(self):
        """An operator reading a refusal should not have to guess which boxes to
        tick. The names are the ones shown in the admin catalogue."""
        msg = sub.requirement_error(self.BASE + ["india_compliance"])
        self.assertIn("Indian Compliance", msg)
        for name in ("Accounts", "Selling", "Buying"):
            self.assertIn(name, msg)

    def test_a_partial_selection_is_still_refused(self):
        """Two of three is not enough, and the message says which one is left."""
        msg = sub.requirement_error(
            self.BASE + ["india_compliance", "erp_accounts", "erp_selling"])
        self.assertIsNotNone(msg)
        self.assertIn("Buying", msg)
        self.assertNotIn("Selling", msg)

    def test_a_complete_selection_passes(self):
        msg = sub.requirement_error(
            self.BASE + ["india_compliance", "erp_accounts", "erp_selling", "erp_buying"])
        self.assertIsNone(msg)

    def test_selections_without_it_are_untouched(self):
        """This gate must not become a tax on every other feature."""
        self.assertIsNone(sub.requirement_error(self.BASE + ["goals", "payroll"]))
        self.assertIsNone(sub.requirement_error([]))
        self.assertIsNone(sub.requirement_error(None))

    def test_nothing_is_auto_enabled(self):
        """The refusal must not quietly become a grant. unmet_requirements only
        REPORTS - if it ever starts returning a corrected selection, a tenant
        gets three ERPNext modules they did not buy."""
        import inspect

        src = inspect.getsource(sub.unmet_requirements)
        for banned in ("selection.append", "chosen.add", "chosen |=", "return chosen"):
            self.assertNotIn(banned, src)


class TestBothInstallPathsAreGated(FrappeTestCase):
    """A tenant can buy it at sign-up or later. Both routes must honour the gate
    and neither may install it unasked."""

    def test_create_tenant_refuses_an_impossible_selection(self):
        import inspect

        from alvoraa_portal import tenant_api

        src = inspect.getsource(tenant_api.create_tenant)
        self.assertIn("requirement_error", src)
        self.assertIn("frappe.throw", src)

    def test_update_tenant_refuses_it_too(self):
        """Editing an existing tenant into an impossible state is worse than
        creating one - the app lands on a live site."""
        import inspect

        from alvoraa_portal import tenant_api

        self.assertIn("requirement_error", inspect.getsource(tenant_api.update_tenant))

    def test_provisioning_installs_it_only_when_sold(self):
        import os

        here = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))))
        path = os.path.join(here, "deploy", "provision_tenant.sh")
        if not os.path.exists(path):
            self.skipTest("provision_tenant.sh not in this checkout")
        script = open(path, encoding="utf-8").read()
        self.assertIn("has_feature india_compliance", script)
        self.assertIn("install-app india_compliance", script)

    def test_the_update_job_can_install_it(self):
        import inspect

        from alvoraa_portal import tenant_api

        sig = inspect.signature(tenant_api._run_install_modules)
        self.assertIn("install_india_compliance", sig.parameters)
        self.assertIs(sig.parameters["install_india_compliance"].default, False)

    def test_audit_trail_is_switched_on_where_it_lands(self):
        """It protects accounting documents, so anyone holding those documents
        should have them protected. Charging for it separately would price a
        legal obligation."""
        import inspect

        from alvoraa_portal import tenant_api

        src = inspect.getsource(tenant_api._run_install_modules)
        self.assertIn("enable_audit_trail", src)


class TestAnUnsoldTenantSeesNothing(FrappeTestCase):
    """Deny-by-default should already cover this, but it is the whole promise of
    the feature gate and is worth asserting rather than assuming.

    `existing` is passed explicitly. blocked_module_defs only blocks modules that
    are actually present on the site, which is right - you cannot deny what is
    not there - but it means a bench without india_compliance installed would
    make these pass by accident, testing nothing. Naming the modules states the
    rule regardless of what this particular bench happens to have.
    """

    BASE = ["hrms", "portal", "leaves", "attendance", "expenses", "hr_setup"]
    THEIRS = ["GST India", "Income Tax India", "VAT India", "Audit Trail"]

    def _present(self):
        """A site that HAS the app installed, whatever this bench looks like."""
        return set(self.THEIRS) | {"Payroll", "Accounts", "Selling", "Buying", "Core", "Desk"}

    def test_its_modules_are_blocked_when_not_sold(self):
        blocked = set(sub.blocked_module_defs(self.BASE, existing=self._present()))
        for m in self.THEIRS:
            self.assertIn(m, blocked, m)

    def test_its_modules_are_allowed_when_sold(self):
        feats = self.BASE + ["india_compliance", "erp_accounts", "erp_selling", "erp_buying"]
        blocked = set(sub.blocked_module_defs(feats, existing=self._present()))
        for m in self.THEIRS:
            self.assertNotIn(m, blocked, m)

    def test_buying_it_does_not_unblock_anything_else(self):
        """The feature grants its own four modules and nothing more."""
        sold = set(sub.blocked_module_defs(
            self.BASE + ["india_compliance", "erp_accounts", "erp_selling", "erp_buying"],
            existing=self._present()))
        unsold = set(sub.blocked_module_defs(self.BASE, existing=self._present()))
        freed = unsold - sold
        self.assertEqual(freed, set(self.THEIRS) | {"Accounts", "Selling", "Buying"})
