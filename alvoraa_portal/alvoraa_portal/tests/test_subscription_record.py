"""A subscription must refuse the contracts that produce a wrong invoice.

Every test here is a real bill going out wrong, or a customer being sold
something they can never open:

  a module charged twice - once inside the plan, once as an add-on
  a module sold before it exists
  half a dependency, so the app installs and every screen is then denied
  a pack without the pack it needs
  a private discount handed to a second customer
  an invoice with nobody to send it to

None of them fail loudly on the day. They fail on an invoice, or in a support
call from somebody who paid for a blank screen.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import pricing, subscriptions


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


def _a_customer(name="Subscription Test Customer"):
	if not frappe.db.exists("Customer", name):
		frappe.get_doc({"doctype": "Customer", "customer_name": name}
		               ).insert(ignore_permissions=True)
	return name


class SubscriptionCase(FrappeTestCase):
	def setUp(self):
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf["alvoraa_control_plane"] = 1
		_clear()
		pricing.seed()
		self.customer = _a_customer()

	def tearDown(self):
		_clear()
		if self._plane is None:
			frappe.conf.pop("alvoraa_control_plane", None)
		else:
			frappe.conf["alvoraa_control_plane"] = self._plane

	def sub(self, site="acme.alvoraa.co", **kw):
		doc = frappe.get_doc({
			"doctype": "Alvoraa Subscription", "site_name": site,
			"status": "Active", "customer": self.customer, "plan": "Starter", **kw})
		doc.insert(ignore_permissions=True)
		return doc


class TestWhoIsBilled(SubscriptionCase):
	def test_a_billable_subscription_needs_a_customer(self):
		with self.assertRaises(frappe.ValidationError):
			self.sub(customer=None)

	def test_an_internal_one_does_not(self):
		"""Inventing a Customer for our own demo puts it in every receivables report."""
		doc = self.sub(site="demo.alvoraa.co", status="Internal", customer=None)
		self.assertFalse(doc.customer)
		self.assertFalse(doc.is_billable)

	def test_internal_is_priced_but_never_invoiced(self):
		doc = self.sub(site="allabouthr.dev.alvoraa.co", status="Internal",
		               customer=None, plan="Starter")
		self.assertEqual(doc.plan, "Starter")   # a real plan, on purpose
		self.assertFalse(doc.is_billable)       # and never a bill

	def test_an_active_subscription_needs_a_plan(self):
		with self.assertRaises(frappe.ValidationError):
			self.sub(plan=None)

	def test_a_trial_may_not_have_one_yet(self):
		self.sub(status="Trial", plan=None)     # no raise

	def test_one_subscription_per_site(self):
		self.sub()
		with self.assertRaises(Exception):
			self.sub()


class TestAddons(SubscriptionCase):
	def test_a_module_in_the_plan_cannot_also_be_an_addon(self):
		"""Charging twice for one thing."""
		with self.assertRaises(frappe.ValidationError):
			self.sub(addons=[{"feature_key": "leaves", "agreed_rate": 10}])

	def test_a_coming_soon_module_cannot_be_sold(self):
		with self.assertRaises(frappe.ValidationError):
			self.sub(addons=[{"feature_key": "lms", "agreed_rate": 25}])

	def test_an_unpriced_module_cannot_be_sold(self):
		frappe.db.set_value("Alvoraa Module Price", "vendor", "rate", 0)
		frappe.get_doc("Alvoraa Module Price", "vendor").save(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self.sub(addons=[{"feature_key": "vendor", "agreed_rate": 0}])

	def test_a_module_not_in_the_price_list_cannot_be_sold(self):
		with self.assertRaises(frappe.ValidationError):
			self.sub(addons=[{"feature_key": "telepathy", "agreed_rate": 10}])

	def test_the_same_addon_cannot_be_listed_twice(self):
		with self.assertRaises(frappe.ValidationError):
			self.sub(addons=[{"feature_key": "payroll", "agreed_rate": 25},
			                 {"feature_key": "payroll", "agreed_rate": 25}])

	def test_the_rate_is_taken_from_the_list_when_not_given(self):
		doc = self.sub(addons=[{"feature_key": "payroll"}])
		self.assertEqual(doc.addons[0].agreed_rate, 25)
		self.assertEqual(doc.addons[0].basis, "PEPM")

	def test_the_agreed_rate_survives_the_list_moving(self):
		"""The whole reason the rate is stored rather than looked up."""
		doc = self.sub(addons=[{"feature_key": "payroll", "agreed_rate": 18}])
		frappe.db.set_value("Alvoraa Module Price", "payroll", "rate", 40)
		doc.reload()
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.addon_rate("payroll"), 18)


class TestPacks(SubscriptionCase):
	def test_trade_without_finance_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.sub(packs=[{"pack": "Trade", "named_users": 2}])

	def test_trade_with_finance_is_fine(self):
		doc = self.sub(packs=[{"pack": "Finance", "named_users": 2},
		                      {"pack": "Trade", "named_users": 2}])
		self.assertEqual(len(doc.packs), 2)

	def test_a_pack_needs_at_least_one_named_user(self):
		with self.assertRaises(frappe.ValidationError):
			self.sub(packs=[{"pack": "Finance", "named_users": 0}])

	def test_the_pack_rate_is_taken_from_the_pack(self):
		# Finance and Trade together, because Finance alone is currently
		# unsellable - see TestTheSelectionHoldsTogether below.
		doc = self.sub(packs=[{"pack": "Finance", "named_users": 3},
		                      {"pack": "Trade", "named_users": 1}])
		self.assertEqual(doc.packs[0].agreed_rate, 300)

	def test_a_pack_cannot_be_listed_twice(self):
		with self.assertRaises(frappe.ValidationError):
			self.sub(packs=[{"pack": "Finance", "named_users": 1},
			                {"pack": "Finance", "named_users": 2}])


class TestTheSelectionHoldsTogether(SubscriptionCase):
	def test_indian_compliance_without_its_erpnext_modules_is_refused(self):
		"""The Finance pack carries all four together, so build the broken case
		by hand - which is exactly what a salesperson would do."""
		frappe.get_doc("Alvoraa Module Price", "india_compliance"
		               ).db_set("is_sellable", 1)
		with self.assertRaises(frappe.ValidationError):
			self.sub(addons=[{"feature_key": "india_compliance", "agreed_rate": 100}])

	def test_the_finance_pack_cannot_currently_be_sold_on_its_own(self):
		"""A finding, not a rule we chose - and it needs a decision.

		Finance carries india_compliance, which declares it requires
		erp_accounts, erp_selling AND erp_buying. Selling and Buying live in the
		Trade pack, so buying Finance alone is refused: a customer who wants
		bookkeeping and GST filing is told to buy a wholesale pack as well, and
		the real price of invoicing is Rs 550 a user rather than Rs 300.

		The requirement looks stricter than the facts. Its own comment says
		every india_compliance doctype hangs off Sales Invoice, Purchase Invoice
		or the Accounts module - and BOTH invoices live in the Accounts module,
		verified on the running bench. Sales Order and Purchase Order are what
		live in Selling and Buying, and nothing about filing a return needs them.

		Two ways out, and it is a commercial decision rather than a technical
		one: narrow the requirement to erp_accounts, or move india_compliance
		into the Trade pack and let Finance be plain bookkeeping. This test
		pins the CURRENT behaviour so the change is deliberate when it comes.
		"""
		with self.assertRaises(frappe.ValidationError):
			self.sub(packs=[{"pack": "Finance", "named_users": 1}])

	def test_finance_and_trade_together_satisfy_it(self):
		doc = self.sub(packs=[{"pack": "Finance", "named_users": 1},
		                      {"pack": "Trade", "named_users": 1}])
		self.assertIn("india_compliance", doc.selected_features())
		self.assertIn("erp_accounts", doc.selected_features())


class TestPrivatePlans(SubscriptionCase):
	def test_a_private_plan_cannot_be_given_to_another_customer(self):
		other = _a_customer("Another Customer")
		frappe.get_doc({
			"doctype": "Alvoraa Plan", "plan_name": "Acme Deal", "band_from": 1,
			"band_to": 50, "platform_fee": 999, "is_private": 1,
			"built_for": other,
			"features": [{"feature_key": "leaves"}]}).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self.sub(plan="Acme Deal")

	def test_the_customer_it_was_built_for_may_have_it(self):
		frappe.get_doc({
			"doctype": "Alvoraa Plan", "plan_name": "Acme Deal", "band_from": 1,
			"band_to": 50, "platform_fee": 999, "is_private": 1,
			"built_for": self.customer,
			"features": [{"feature_key": "leaves"}]}).insert(ignore_permissions=True)
		self.sub(plan="Acme Deal")   # no raise


class TestReading(SubscriptionCase):
	def test_the_list_separates_ours_from_theirs(self):
		self.sub(site="acme.alvoraa.co")
		self.sub(site="demo.alvoraa.co", status="Internal", customer=None)
		out = subscriptions.list_subscriptions()
		self.assertEqual(out["billable"], 1)
		self.assertEqual(out["internal"], 1)

	def test_reading_one_resolves_its_features(self):
		self.sub(addons=[{"feature_key": "payroll"}])
		out = subscriptions.get_subscription("acme.alvoraa.co")
		self.assertIn("payroll", out["features"])
		self.assertIn("leaves", out["features"])      # from the plan
		self.assertEqual(out["addons"][0]["agreed_rate"], 25)

	def test_reading_a_site_with_no_subscription_returns_nothing(self):
		self.assertIsNone(subscriptions.get_subscription("nobody.alvoraa.co"))


class TestAdoption(SubscriptionCase):
	def test_a_dry_run_creates_nothing(self):
		out = subscriptions.adopt_existing_tenants(dry_run=True)
		self.assertTrue(out["dry_run"])
		self.assertEqual(out["created"], [])
		self.assertEqual(frappe.db.count("Alvoraa Subscription"), 0)

	def test_our_own_sites_are_marked_internal(self):
		for site in ("demo.alvoraa.co", "test_site", "allabouthr.dev.alvoraa.co"):
			self.assertIn(site, subscriptions.OUR_OWN_SITES)

	def test_a_site_with_no_headcount_gets_no_plan_and_says_why(self):
		"""Better visibly unfinished than finished and billing the wrong amount."""
		row = subscriptions._proposed("acme.alvoraa.co",
		                              {"modules": ["payroll"], "plan": "enterprise"}, None)
		self.assertIsNone(row["plan"])
		self.assertTrue(any("headcount" in w for w in row["needs_a_human"]))

	def test_the_old_plan_name_is_never_carried_across(self):
		"""The old names were feature bundles; the new ones are headcount bands.
		A twenty-person tenant on the old 'enterprise' belongs in Starter."""
		row = subscriptions._proposed("acme.alvoraa.co",
		                              {"modules": [], "plan": "enterprise"}, 20)
		self.assertEqual(row["plan"], "Starter")
		self.assertEqual(row["old_plan_name"], "enterprise")

	def test_modules_beyond_the_plan_become_addons(self):
		row = subscriptions._proposed("acme.alvoraa.co",
		                              {"modules": ["leaves", "payroll"], "plan": "starter"}, 20)
		keys = [a["feature_key"] for a in row["addons"]]
		self.assertIn("payroll", keys)
		self.assertNotIn("leaves", keys)     # already in the fee
		self.assertEqual(row["addons"][0]["agreed_rate"], 25)

	def test_a_module_that_cannot_be_sold_is_flagged_not_billed(self):
		row = subscriptions._proposed("acme.alvoraa.co",
		                              {"modules": ["lms"], "plan": "starter"}, 20)
		self.assertEqual(row["addons"], [])
		self.assertTrue(any("lms" in w for w in row["needs_a_human"]))


class TestControlPlaneOnly(FrappeTestCase):
	def setUp(self):
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf.pop("alvoraa_control_plane", None)

	def tearDown(self):
		if self._plane is not None:
			frappe.conf["alvoraa_control_plane"] = self._plane

	def test_listing_is_refused_on_a_tenant(self):
		with self.assertRaises(frappe.ValidationError):
			subscriptions.list_subscriptions()

	def test_adopting_is_refused_on_a_tenant(self):
		with self.assertRaises(frappe.ValidationError):
			subscriptions.adopt_existing_tenants()
