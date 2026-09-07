"""The price list has to refuse the mistakes that produce a wrong invoice.

Every test here is a bill that would otherwise go out wrong, or a promise the
product could not keep:

  a plan promising a feature the product does not have
  two public plans covering the same headcount, so a tenant has two prices
  a module priced twice, in two packs, for the same user
  a pack requirement chain that loops
  a cap set below a single pack, quietly discounting it
  a price list a tenant administrator can read out of their own desk

None of these fail loudly on their own. They fail on an invoice, weeks later,
in front of a customer.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import pricing


def _clear():
	for dt in ("Alvoraa Plan", "Alvoraa Operations Pack", "Alvoraa Module Price"):
		for name in frappe.get_all(dt, pluck="name"):
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
	settings = frappe.get_single("Alvoraa Pricing Settings")
	settings.seeded = None
	settings.pack_cap_per_user = 0
	settings.save(ignore_permissions=True)
	frappe.db.commit()


class PricingCase(FrappeTestCase):
	"""Every test runs as if on the control plane; the guard is tested by itself."""

	def setUp(self):
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf["alvoraa_control_plane"] = 1
		_clear()

	def tearDown(self):
		_clear()
		if self._plane is None:
			frappe.conf.pop("alvoraa_control_plane", None)
		else:
			frappe.conf["alvoraa_control_plane"] = self._plane

	# helpers ────────────────────────────────────────────────────────────────
	def plan(self, name, low, high, fee=1000, **kw):
		doc = frappe.get_doc({
			"doctype": "Alvoraa Plan", "plan_name": name,
			"band_from": low, "band_to": high, "platform_fee": fee,
			"features": [{"feature_key": "leaves"}], **kw})
		doc.insert(ignore_permissions=True)
		return doc

	def price(self, key, **kw):
		doc = frappe.get_doc({"doctype": "Alvoraa Module Price", "feature_key": key,
		                      **kw})
		doc.insert(ignore_permissions=True)
		return doc

	def pack(self, name, features, rate=100, **kw):
		doc = frappe.get_doc({
			"doctype": "Alvoraa Operations Pack", "pack_name": name,
			"rate_per_user": rate,
			"features": [{"feature_key": k} for k in features], **kw})
		doc.insert(ignore_permissions=True)
		return doc


class TestSeed(PricingCase):
	def test_seed_creates_the_agreed_model(self):
		out = pricing.seed()
		self.assertTrue(out["seeded"])
		self.assertEqual(len(frappe.get_all("Alvoraa Plan")), len(pricing.PLANS))
		self.assertEqual(len(frappe.get_all("Alvoraa Operations Pack")), len(pricing.PACKS))
		self.assertEqual(
			frappe.db.get_single_value("Alvoraa Pricing Settings", "pack_cap_per_user"),
			pricing.PACK_CAP_PER_USER)

	def test_seed_does_not_run_twice(self):
		pricing.seed()
		frappe.db.set_value("Alvoraa Plan", "Starter", "platform_fee", 1)
		out = pricing.seed()
		self.assertFalse(out["seeded"])
		# The edited price survived, which is the whole point of the stamp.
		self.assertEqual(frappe.db.get_value("Alvoraa Plan", "Starter", "platform_fee"), 1)

	def test_seeded_bands_do_not_overlap(self):
		"""The model itself has to pass the rule the doctype enforces."""
		pricing.seed()
		rows = frappe.get_all("Alvoraa Plan", filters={"is_private": 0},
		                      fields=["band_from", "band_to"], order_by="band_from asc")
		for earlier, later in zip(rows, rows[1:]):
			self.assertLess(earlier.band_to, later.band_from)

	def test_payroll_is_priced_and_not_in_the_fee(self):
		pricing.seed()
		self.assertNotIn("payroll", pricing.PLATFORM_FEATURES)
		self.assertEqual(frappe.db.get_value("Alvoraa Module Price", "payroll", "rate"), 25)
		self.assertTrue(frappe.db.get_value("Alvoraa Module Price", "payroll", "is_sellable"))

	def test_every_seeded_pack_module_is_a_real_erpnext_feature(self):
		pricing.seed()
		for pack in frappe.get_all("Alvoraa Operations Pack", pluck="name"):
			for row in frappe.get_doc("Alvoraa Operations Pack", pack).features:
				spec = pricing.feature_spec(row.feature_key)
				self.assertTrue(spec.get("erpnext"), f"{row.feature_key} in {pack}")


class TestPlan(PricingCase):
	def test_a_plan_cannot_promise_a_feature_that_does_not_exist(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({
				"doctype": "Alvoraa Plan", "plan_name": "Bad", "band_from": 1,
				"band_to": 10, "platform_fee": 999,
				"features": [{"feature_key": "telepathy"}]}).insert(ignore_permissions=True)

	def test_two_public_plans_cannot_cover_the_same_headcount(self):
		self.plan("A", 1, 50)
		with self.assertRaises(frappe.ValidationError):
			self.plan("B", 40, 90)

	def test_a_private_plan_may_overlap(self):
		"""It is chosen by name, never matched by size, so it cannot collide."""
		self.plan("A", 1, 50)
		customer = _a_customer()
		self.plan("Special", 1, 50, is_private=1, built_for=customer)  # no raise

	def test_a_private_plan_needs_the_customer_it_was_built_for(self):
		with self.assertRaises(frappe.ValidationError):
			self.plan("Special", 1, 50, is_private=1)

	def test_a_plan_needs_a_price_unless_it_is_quote_only(self):
		with self.assertRaises(frappe.ValidationError):
			self.plan("Free", 1, 50, fee=0)
		doc = self.plan("Custom", 1, 50, fee=0, is_quote_only=1)
		self.assertEqual(doc.platform_fee, 0)

	def test_annual_cannot_cost_more_than_paying_monthly(self):
		with self.assertRaises(frappe.ValidationError):
			self.plan("A", 1, 50, fee=1000, annual_fee=99999)

	def test_the_band_cannot_end_before_it_starts(self):
		with self.assertRaises(frappe.ValidationError):
			self.plan("A", 50, 10)

	def test_headcount_picks_the_right_plan(self):
		self.plan("Small", 1, 25)
		self.plan("Big", 26, 0)          # open-ended
		self.assertEqual(pricing.plan_for_headcount(10), "Small")
		self.assertEqual(pricing.plan_for_headcount(25), "Small")
		self.assertEqual(pricing.plan_for_headcount(26), "Big")
		self.assertEqual(pricing.plan_for_headcount(9999), "Big")

	def test_headcount_never_picks_a_private_plan(self):
		self.plan("Small", 1, 25)
		self.plan("Deal", 1, 25, is_private=1, built_for=_a_customer())
		self.assertEqual(pricing.plan_for_headcount(10), "Small")


class TestModulePrice(PricingCase):
	def test_a_built_module_must_exist_in_the_registry(self):
		with self.assertRaises(frappe.ValidationError):
			self.price("telepathy", status="Built", rate=10)

	def test_a_roadmap_item_may_be_listed_but_never_sold(self):
		doc = self.price("telepathy", status="Coming Soon", rate=10)
		self.assertFalse(doc.is_sellable)
		self.assertFalse(doc.in_registry)

	def test_a_built_module_with_no_rate_is_not_sellable(self):
		self.assertFalse(self.price("payroll", status="Built").is_sellable)

	def test_a_priced_built_module_is_sellable(self):
		self.assertTrue(self.price("payroll", status="Built", rate=25).is_sellable)

	def test_the_label_comes_from_the_registry(self):
		self.assertEqual(self.price("payroll", rate=25).module_label, "Payroll")


class TestOperationsPack(PricingCase):
	def test_a_pack_cannot_carry_an_hr_feature(self):
		"""HR is charged per employee. A pack is charged per named user."""
		with self.assertRaises(frappe.ValidationError):
			self.pack("Wrong", ["payroll"])

	def test_a_module_cannot_belong_to_two_packs(self):
		self.price("erp_accounts", rate=0)
		self.pack("Finance", ["erp_accounts"])
		with self.assertRaises(frappe.ValidationError):
			self.pack("Also Finance", ["erp_accounts"])

	def test_the_requirement_chain_cannot_loop(self):
		a = self.pack("A", ["erp_accounts"])
		b = self.pack("B", ["erp_selling"], requires_pack="A")
		a.requires_pack = b.name
		with self.assertRaises(frappe.ValidationError):
			a.save(ignore_permissions=True)

	def test_the_pack_stamps_itself_onto_its_price_rows(self):
		self.price("erp_accounts", rate=0)
		self.price("erp_selling", rate=0)
		pack = self.pack("Finance", ["erp_accounts"])
		self.assertEqual(
			frappe.db.get_value("Alvoraa Module Price", "erp_accounts", "pack"), "Finance")

		# set(), not assignment: a plain list of dicts never becomes child
		# documents, and the next save fails deep inside Frappe.
		pack.set("features", [{"feature_key": "erp_selling"}])
		pack.save(ignore_permissions=True)
		# The module it no longer carries stops claiming it does.
		self.assertFalse(
			frappe.db.get_value("Alvoraa Module Price", "erp_accounts", "pack"))
		self.assertEqual(
			frappe.db.get_value("Alvoraa Module Price", "erp_selling", "pack"), "Finance")

	def test_deleting_a_pack_leaves_no_dangling_link(self):
		self.price("erp_accounts", rate=0)
		self.pack("Finance", ["erp_accounts"])
		frappe.delete_doc("Alvoraa Operations Pack", "Finance", force=True,
		                  ignore_permissions=True)
		self.assertFalse(
			frappe.db.get_value("Alvoraa Module Price", "erp_accounts", "pack"))


class TestCap(PricingCase):
	def _set_cap(self, value):
		settings = frappe.get_single("Alvoraa Pricing Settings")
		settings.pack_cap_per_user = value
		settings.save(ignore_permissions=True)

	def test_the_cap_cannot_sit_below_a_single_pack(self):
		self.pack("Finance", ["erp_accounts"], rate=300)
		with self.assertRaises(frappe.ValidationError):
			self._set_cap(200)

	def test_one_pack_costs_its_own_rate(self):
		self.pack("Finance", ["erp_accounts"], rate=300)
		self._set_cap(799)
		self.assertEqual(pricing.pack_total_per_user(["Finance"]), 300)

	def test_holding_everything_costs_the_cap_not_the_sum(self):
		self.pack("Finance", ["erp_accounts"], rate=300)
		self.pack("Trade", ["erp_selling"], rate=250, requires_pack="Finance")
		self.pack("CRM", ["erp_crm"], rate=200)
		self.pack("Projects", ["erp_projects"], rate=200)
		self.pack("Manufacturing", ["erp_manufacturing"], rate=250)
		self._set_cap(799)
		self.assertEqual(
			pricing.pack_total_per_user(
				["Finance", "Trade", "CRM", "Projects", "Manufacturing"]), 799)

	def test_no_cap_means_the_sum(self):
		self.pack("Finance", ["erp_accounts"], rate=300)
		self.pack("Trade", ["erp_selling"], rate=250)
		self._set_cap(0)
		self.assertEqual(pricing.pack_total_per_user(["Finance", "Trade"]), 550)

	def test_no_packs_costs_nothing(self):
		self.assertEqual(pricing.pack_total_per_user([]), 0)


class TestRegistrySync(PricingCase):
	def test_a_feature_with_no_price_row_gets_one_unpriced(self):
		added = pricing.sync_registry()["added"]
		self.assertGreater(added, 0)
		row = frappe.get_doc("Alvoraa Module Price", "recruitment")
		self.assertFalse(row.rate)
		self.assertFalse(row.is_sellable)   # listed, visibly unpriced, unsellable

	def test_syncing_twice_adds_nothing_the_second_time(self):
		pricing.sync_registry()
		self.assertEqual(pricing.sync_registry()["added"], 0)

	def test_a_platform_feature_never_gets_its_own_price(self):
		"""The fee already pays for it, so an unpriced row would nag for ever."""
		pricing.sync_registry()
		for key in pricing.PLATFORM_FEATURES:
			self.assertFalse(frappe.db.exists("Alvoraa Module Price", key), key)

	def test_the_catalogue_names_what_is_built_but_unpriced(self):
		pricing.sync_registry()
		self.assertIn("recruitment", pricing.get_price_catalogue()["unpriced"])


class TestControlPlaneOnly(FrappeTestCase):
	"""On a tenant the price list must stay empty and unreadable.

	The doctypes install everywhere, because they ship with the app. A tenant
	administrator is System Manager on their own site, so doctype permissions
	alone would not keep our prices from them. This guard is what does.
	"""

	def setUp(self):
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf.pop("alvoraa_control_plane", None)

	def tearDown(self):
		if self._plane is not None:
			frappe.conf["alvoraa_control_plane"] = self._plane

	def test_reading_the_catalogue_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			pricing.get_price_catalogue()

	def test_seeding_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			pricing.seed()

	def test_syncing_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			pricing.sync_registry()


def _a_customer():
	name = "Pricing Test Customer"
	if not frappe.db.exists("Customer", name):
		frappe.get_doc({"doctype": "Customer", "customer_name": name}
		               ).insert(ignore_permissions=True)
	return name
