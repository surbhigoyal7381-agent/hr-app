"""The plan definition is a pricing decision, so it gets tested like one.

Before subscription.py it lived in three places - twice in tenant_api and once in
the admin page's JavaScript. These tests exist to stop the ladder drifting again.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import subscription as sub


class TestPlanLadder(FrappeTestCase):
	def test_each_plan_contains_the_one_below_it(self):
		"""A customer must never lose a feature by paying more."""
		starter = set(sub.plan_features("starter"))
		business = set(sub.plan_features("business"))
		enterprise = set(sub.plan_features("enterprise"))
		self.assertTrue(starter < business, "business must be a superset of starter")
		self.assertTrue(business < enterprise, "enterprise must be a superset of business")

	def test_starter_is_self_service_only(self):
		f = sub.plan_features("starter")
		for yes in ("portal", "leaves", "attendance", "expenses"):
			self.assertIn(yes, f)
		for no in ("payroll", "recruitment", "goals", "performance", "vendor"):
			self.assertNotIn(no, f, "%s must not be on starter" % no)

	def test_recruitment_and_payroll_are_business(self):
		f = sub.plan_features("business")
		self.assertIn("recruitment", f)
		self.assertIn("payroll", f)
		self.assertNotIn("goals", f)

	def test_enterprise_has_everything_we_sell(self):
		self.assertEqual(set(sub.plan_features("enterprise")), set(sub.FEATURES))

	def test_custom_has_every_hr_feature_too(self):
		"""Custom is Enterprise PLUS ERPNext, not a different HR product."""
		self.assertEqual(set(sub.plan_features("custom")), set(sub.plan_features("enterprise")))

	def test_unknown_plan_grants_everything(self):
		"""Tenants provisioned before this existed must not lose access."""
		self.assertEqual(set(sub.plan_features("nonsense")), set(sub.FEATURES))
		self.assertEqual(set(sub.plan_features(None)), set(sub.FEATURES))


class TestEntitlement(FrappeTestCase):
	def test_a_site_with_no_config_gets_everything(self):
		"""A missing key must never lock a tenant out."""
		self.assertEqual(set(sub.enabled_features({})), set(sub.FEATURES))

	def test_features_list_wins_when_present(self):
		feats = sub.enabled_features({"features": ["portal", "leaves", "payroll"]})
		self.assertIn("payroll", feats)
		self.assertNotIn("goals", feats)

	def test_required_features_are_added_back(self):
		"""Even a config that omits them keeps Core HR working."""
		feats = sub.enabled_features({"features": ["payroll"]})
		for r in sub.REQUIRED:
			self.assertIn(r, feats, "%s is required and must survive any config" % r)

	def test_plan_is_used_when_no_explicit_feature_list(self):
		feats = sub.enabled_features({"subscription_plan": "starter"})
		self.assertNotIn("payroll", feats)

	def test_has_feature_never_denies_a_required_one(self):
		self.assertTrue(sub.has_feature("leaves", {"features": []}))
		self.assertFalse(sub.has_feature("payroll", {"features": []}))


class TestGating(FrappeTestCase):
	def test_erpnext_is_always_blocked_in_the_desk(self):
		blocked = sub.blocked_module_defs(sub.plan_features("enterprise"))
		for m in ("Accounts", "Manufacturing", "Stock", "Selling"):
			self.assertIn(m, blocked, "%s must be hidden unless Custom re-enables it" % m)

	def test_payroll_module_is_blocked_on_starter(self):
		self.assertIn("Payroll", sub.blocked_module_defs(sub.plan_features("starter")))
		self.assertNotIn("Payroll", sub.blocked_module_defs(sub.plan_features("business")))

	def test_recruitment_is_gated_by_role_not_module(self):
		"""Job Opening, Job Applicant and Interview live in the HR module, so
		blocking a module would take Core HR with it."""
		self.assertEqual(sub.FEATURES["recruitment"].get("module_defs"), None)
		self.assertIn("Interviewer", sub.withheld_roles(sub.plan_features("starter")))
		self.assertNotIn("Interviewer", sub.withheld_roles(sub.plan_features("business")))

	def test_goals_app_only_installed_when_sold(self):
		self.assertNotIn("alvoraa_goals", sub.required_apps(sub.plan_features("starter")))
		self.assertIn("alvoraa_goals", sub.required_apps(sub.plan_features("enterprise")))

	def test_the_portal_app_is_always_required(self):
		self.assertIn("alvoraa_portal", sub.required_apps(sub.plan_features("starter")))

	def test_erpnext_lists_do_not_overlap(self):
		"""A module is either sellable or plumbing - never counted twice."""
		self.assertEqual(set(sub.ERPNEXT_SELLABLE) & set(sub.ERPNEXT_INFRASTRUCTURE), set())


class TestPerTenantSelection(FrappeTestCase):
	"""The control-plane admin ticks modules per tenant, across both groups.

	Plans are presets, not cages: whatever ends up ticked is what the tenant gets,
	and the plan NAME is derived from the selection.
	"""

	def test_erpnext_modules_are_selectable_alongside_hr_features(self):
		cat = sub.get_plan_catalogue()
		groups = {g["key"]: g for g in cat["groups"]}
		self.assertEqual(len(groups["alvoraa_hr"]["features"]), len(sub.FEATURES))
		self.assertEqual(len(groups["erpnext"]["features"]), len(sub.ERPNEXT_SELLABLE))
		# one flat catalogue too, so the admin can render a single grid
		self.assertEqual(len(cat["features"]), len(sub.FEATURES) + len(sub.ERPNEXT_SELLABLE))

	def test_unticked_erpnext_modules_are_hidden(self):
		blocked = sub.blocked_module_defs(sub.plan_features("enterprise"))
		for m in sub.ERPNEXT_SELLABLE:
			self.assertIn(m, blocked, "%s should be hidden when not selected" % m)

	def test_ticked_erpnext_modules_are_visible(self):
		selection = sub.plan_features("enterprise") + ["erp_accounts", "erp_projects"]
		blocked = sub.blocked_module_defs(selection)
		self.assertNotIn("Accounts", blocked)
		self.assertNotIn("Projects", blocked)
		self.assertIn("Stock", blocked, "modules not ticked stay hidden")

	def test_erp_ids_are_stable_and_readable(self):
		self.assertEqual(sub.erp_feature_id("Quality Management"), "erp_quality_management")
		self.assertEqual(sub.erp_feature_id("Stock"), "erp_stock")

	def test_infrastructure_is_hidden_whatever_is_ticked(self):
		"""Setup, Regional and friends are plumbing Frappe HR needs - never sold,
		never shown, even to a tenant that bought every sellable module."""
		everything = sub.plan_features("enterprise") + list(sub.ERPNEXT_FEATURES)
		blocked = sub.blocked_module_defs(everything)
		for m in sub.ERPNEXT_INFRASTRUCTURE:
			self.assertIn(m, blocked, "%s is plumbing and must stay hidden" % m)

	def test_a_starter_tenant_can_still_be_given_one_erp_module(self):
		"""The admin is not forced up a plan tier to add a single module."""
		selection = sub.plan_features("starter") + ["erp_accounts"]
		blocked = sub.blocked_module_defs(selection)
		self.assertNotIn("Accounts", blocked)
		self.assertIn("Payroll", blocked, "starter still does not include payroll")


class TestPlanValidation(FrappeTestCase):
	"""A custom selection must be accepted, not rejected.

	tenant_api validated the DERIVED plan against its own stale constant, which
	listed only starter/business/enterprise. Any tick set that did not exactly
	match a preset produced "custom" and was refused - which is precisely the
	case the Custom plan exists for.
	"""

	def test_custom_is_a_known_plan(self):
		self.assertIn("custom", sub.PLANS)

	def test_every_derivable_plan_name_is_valid(self):
		"""Whatever the derivation can produce, validation must accept."""
		for name in ("starter", "business", "enterprise", "custom"):
			self.assertIn(name, sub.PLANS, "%s can be derived but would be rejected" % name)

	def test_tenant_api_validates_against_the_registry(self):
		"""Not against a copy of it."""
		from alvoraa_portal import tenant_api
		self.assertIs(tenant_api.PLANS, sub.PLANS)
		self.assertFalse(hasattr(tenant_api, "PLAN_MODULES"),
		                 "the stale fourth copy of the plan definition is back")


class TestWorkspaceGating(FrappeTestCase):
	"""Module blocking cannot gate Frappe HR's workspaces.

	Leaves, Expenses, HR Setup, Recruitment, Tenure, Performance and
	Shift & Attendance ALL live in one module called `HR`; Payroll and
	Tax & Benefits share `Payroll`. So blocking a module hides the features a
	tenant bought alongside the ones it did not.
	"""

	def test_a_starter_site_hides_what_it_did_not_buy(self):
		show, hide = sub.sold_and_unsold_workspaces(sub.plan_features("starter"))
		self.assertIn("Recruitment", hide, "Starter does not include Recruitment")
		self.assertIn("Payroll", hide, "Starter does not include Payroll")
		self.assertIn("Tenure", hide)
		self.assertIn("Leaves", show, "Leaves is required on every plan")
		self.assertIn("Expenses", show)
		self.assertIn("HR Setup", show)

	def test_business_reveals_payroll_and_recruitment(self):
		show, hide = sub.sold_and_unsold_workspaces(sub.plan_features("business"))
		self.assertIn("Payroll", show)
		self.assertIn("Recruitment", show)
		self.assertIn("Tax & Benefits", show)

	def test_enterprise_hides_nothing_of_ours(self):
		show, hide = sub.sold_and_unsold_workspaces(sub.plan_features("enterprise"))
		self.assertEqual(hide, [], "Enterprise includes every Alvoraa HR feature")

	def test_the_two_lists_never_overlap(self):
		"""A workspace in both lists would flip on every sync, depending on
		which loop ran last."""
		for plan in sub.PLANS:
			show, hide = sub.sold_and_unsold_workspaces(sub.plan_features(plan))
			self.assertFalse(set(show) & set(hide), plan)

	def test_required_features_are_always_shown(self):
		"""Even given an empty feature list - which a downgrade can produce."""
		show, hide = sub.sold_and_unsold_workspaces([])
		for ws in ("Leaves", "Shift & Attendance", "Expenses", "HR Setup"):
			self.assertIn(ws, show, ws)
			self.assertNotIn(ws, hide, ws)

	def test_every_declared_workspace_is_accounted_for(self):
		"""The `workspaces` field sat in the registry unused for weeks while the
		desk showed Recruitment and Payroll to tenants that had not bought them.
		If a feature declares one, some plan must place it."""
		declared = {w for spec in sub.FEATURES.values()
		            for w in (spec.get("workspaces") or [])}
		show, hide = sub.sold_and_unsold_workspaces(sub.plan_features("starter"))
		self.assertEqual(declared, set(show) | set(hide))
