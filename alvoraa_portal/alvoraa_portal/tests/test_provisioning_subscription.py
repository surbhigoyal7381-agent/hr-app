"""Creating a tenant must record what was sold, at the moment it was sold.

Two ideas wore the same word for a while. The provisioning "plan" is a FEATURE
BUNDLE - starter, business, enterprise - derived from which boxes were ticked.
The billing plan is a HEADCOUNT BAND with a fee. They share three names and mean
opposite things: a tenant provisioned on the "enterprise" bundle with twenty
staff belongs on the "Starter" price band.

Worse, they were not connected at all. Every tenant created was born with no
subscription - invisible to billing until somebody adopted it by hand, which
nobody would remember to do.

These tests hold the join together, and hold the two rules that make it safe to
put on a live control plane:

  Without a priced plan, provisioning behaves exactly as it always did.
  With one, the subscription exists from the moment somebody agreed to it -
  even if the site never comes up.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import pricing
from alvoraa_portal import tenant_api as api

SITE = "acme.alvoraa.co"
CUSTOMER = "Provisioning Test Customer"


def _clear():
	for dt in ("Alvoraa Subscription", "Alvoraa Plan", "Alvoraa Operations Pack",
	           "Alvoraa Module Price"):
		for name in frappe.get_all(dt, pluck="name"):
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
	settings = frappe.get_single("Alvoraa Pricing Settings")
	settings.seeded = None
	settings.pack_cap_per_user = 0
	settings.save(ignore_permissions=True)
	frappe.db.commit()


class ProvisioningCase(FrappeTestCase):
	def setUp(self):
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf["alvoraa_control_plane"] = 1
		_clear()
		pricing.seed()
		for name in (CUSTOMER, "Another Customer"):
			if not frappe.db.exists("Customer", name):
				frappe.get_doc({"doctype": "Customer", "customer_name": name}
				               ).insert(ignore_permissions=True)

	def tearDown(self):
		_clear()
		if self._plane is None:
			frappe.conf.pop("alvoraa_control_plane", None)
		else:
			frappe.conf["alvoraa_control_plane"] = self._plane

	def made(self, **kw):
		"""The subscription half of create_tenant, without provisioning a site."""
		kw.setdefault("modules", ["portal", "leaves", "attendance", "expenses",
		                          "hr_setup", "tenure", "tax_benefits"])
		kw.setdefault("packs", None)
		return api._create_subscription(
			SITE, kw.pop("alvoraa_plan", "Starter"), kw.pop("customer", CUSTOMER),
			kw.pop("modules"), kw.pop("packs"),
			kw.pop("implementation_fee", 0), kw.pop("billing_frequency", "Monthly"))


class TestNothingChangesWithoutAPricedPlan(ProvisioningCase):
	"""The rule that makes this safe to deploy on a live control plane."""

	def test_no_plan_means_no_subscription_and_no_error(self):
		self.assertIsNone(self.made(alvoraa_plan=None))
		self.assertEqual(frappe.db.count("Alvoraa Subscription"), 0)

	def test_an_unknown_plan_is_refused_before_anything_is_written(self):
		with self.assertRaises(frappe.ValidationError):
			self.made(alvoraa_plan="Nonexistent Band")
		self.assertEqual(frappe.db.count("Alvoraa Subscription"), 0)


class TestWhatGetsRecorded(ProvisioningCase):
	def test_the_subscription_is_created_with_the_priced_plan(self):
		out = self.made(alvoraa_plan="Business")
		doc = frappe.get_doc("Alvoraa Subscription", SITE)
		self.assertEqual(out["plan"], "Business")
		self.assertEqual(doc.plan, "Business")
		self.assertEqual(doc.customer, CUSTOMER)

	def test_it_starts_as_a_trial(self):
		"""Nothing has been provisioned yet, let alone used."""
		self.made()
		self.assertEqual(frappe.db.get_value("Alvoraa Subscription", SITE, "status"),
		                 "Trial")

	def test_features_beyond_the_fee_become_addons(self):
		"""The operator ticks features. They should not also have to know which
		side of the platform fee each one falls on."""
		out = self.made(modules=["portal", "leaves", "attendance", "expenses",
		                         "hr_setup", "payroll", "recruitment"])
		doc = frappe.get_doc("Alvoraa Subscription", SITE)
		keys = sorted(r.feature_key for r in doc.addons)
		self.assertEqual(keys, ["payroll", "recruitment"])
		self.assertEqual(out["addons"], 2)

	def test_features_inside_the_fee_are_not_charged_twice(self):
		self.made(modules=["portal", "leaves", "attendance", "expenses", "hr_setup"])
		doc = frappe.get_doc("Alvoraa Subscription", SITE)
		self.assertEqual(doc.addons, [])

	def test_a_module_that_cannot_be_sold_is_left_off(self):
		"""Coming Soon carries an intended price so it can be shown. Putting it on
		a contract would charge for something no tenant can be given."""
		self.made(modules=["portal", "leaves", "attendance", "expenses",
		                   "hr_setup", "lms"])
		doc = frappe.get_doc("Alvoraa Subscription", SITE)
		self.assertEqual([r.feature_key for r in doc.addons], [])

	def test_the_rate_is_taken_from_the_price_list_at_signing(self):
		self.made(modules=["portal", "leaves", "attendance", "expenses",
		                   "hr_setup", "payroll"])
		doc = frappe.get_doc("Alvoraa Subscription", SITE)
		self.assertEqual(doc.addons[0].agreed_rate, 25)

	def test_packs_and_a_setup_fee_are_carried_across(self):
		out = self.made(packs=[{"pack": "Finance", "named_users": 2}],
		                implementation_fee=25000)
		doc = frappe.get_doc("Alvoraa Subscription", SITE)
		self.assertEqual(out["packs"], 1)
		self.assertEqual(doc.implementation_fee, 25000)

	def test_it_can_be_invoiced_the_month_it_starts(self):
		"""The whole point. Before this, a new tenant was invisible to billing
		until somebody adopted it by hand."""
		self.made(alvoraa_plan="Business")
		from alvoraa_portal import subscriptions

		out = subscriptions.list_subscriptions()
		self.assertEqual(out["billable"], 1)
		self.assertNotIn(SITE, out["unadopted"])


class TestPrivatePlans(ProvisioningCase):
	def _private(self, built_for):
		frappe.get_doc({
			"doctype": "Alvoraa Plan", "plan_name": "Acme Deal", "band_from": 1,
			"band_to": 60, "platform_fee": 1500, "is_private": 1,
			"built_for": built_for,
			"features": [{"feature_key": "leaves"}]}).insert(ignore_permissions=True)

	def test_a_private_plan_is_offered_only_to_its_own_customer(self):
		"""What stops a one-off discount agreed with one client quietly becoming
		an option on every future deal."""
		self._private(CUSTOMER)
		mine = [p["name"] for p in api.get_provisioning_plans(CUSTOMER)["plans"]]
		theirs = [p["name"] for p in api.get_provisioning_plans("Another Customer")["plans"]]
		nobody = [p["name"] for p in api.get_provisioning_plans()["plans"]]
		self.assertIn("Acme Deal", mine)
		self.assertNotIn("Acme Deal", theirs)
		self.assertNotIn("Acme Deal", nobody)

	def test_public_plans_are_always_offered(self):
		out = api.get_provisioning_plans()
		names = [p["name"] for p in out["plans"]]
		self.assertIn("Starter", names)
		self.assertIn("Enterprise", names)
		self.assertTrue(out["billing_ready"])

	def test_a_retired_plan_is_not_offered(self):
		frappe.db.set_value("Alvoraa Plan", "Growth", "is_active", 0)
		self.assertNotIn("Growth",
		                 [p["name"] for p in api.get_provisioning_plans()["plans"]])

	def test_each_plan_says_what_it_includes(self):
		"""So the console can tick the right boxes and show which extras cost more."""
		starter = [p for p in api.get_provisioning_plans()["plans"]
		           if p["name"] == "Starter"][0]
		self.assertIn("leaves", starter["features"])
		self.assertNotIn("payroll", starter["features"])


class TestThePlanLabel(FrappeTestCase):
	"""Every tenant ever provisioned came out "custom", including full Enterprise.

	create_tenant prepends a legacy `hrms` marker to every module list. It is not
	a feature and appears in no plan, so the comparison against PLANS was always
	one member short of matching. The label had been wrong long enough that
	nobody questioned it - it surfaced only when a demo needed the console to say
	"Enterprise" in front of a customer.

	update_tenant had a second copy of the same comparison with the same bug,
	which is what a second copy is for. There is one function now.
	"""

	def test_a_full_enterprise_tick_is_called_enterprise(self):
		from alvoraa_portal.subscription import FEATURES

		everything = ["hrms"] + [k for k, v in FEATURES.items() if not v.get("opt_in")]
		self.assertEqual(api._plan_label(everything), "enterprise")

	def test_the_starter_five_are_called_starter(self):
		from alvoraa_portal.subscription import PLANS

		self.assertEqual(api._plan_label(["hrms"] + list(PLANS["starter"])), "starter")

	def test_it_works_without_the_legacy_marker_too(self):
		from alvoraa_portal.subscription import PLANS

		self.assertEqual(api._plan_label(list(PLANS["business"])), "business")

	def test_an_opt_in_extra_does_not_change_the_bundle(self):
		"""An Enterprise tenant with the late-coming rule switched on is still
		Enterprise. Opt-in features are extras, not a different plan."""
		from alvoraa_portal.subscription import FEATURES, OPT_IN

		base = ["hrms"] + [k for k, v in FEATURES.items() if not v.get("opt_in")]
		if OPT_IN:
			self.assertEqual(api._plan_label(base + [OPT_IN[0]]), "enterprise")

	def test_a_genuinely_odd_selection_is_still_custom(self):
		self.assertEqual(api._plan_label(["hrms", "portal", "payroll"]), "custom")

	def test_nothing_at_all_is_custom_not_a_crash(self):
		self.assertEqual(api._plan_label(None), "custom")
		self.assertEqual(api._plan_label([]), "custom")
