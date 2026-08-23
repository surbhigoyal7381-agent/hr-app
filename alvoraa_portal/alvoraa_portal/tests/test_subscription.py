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
