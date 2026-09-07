"""The estimate is the invoice before anyone signs it, so the arithmetic has
to be right and the refusals have to be loud.

Two things every test here is really about:

  A number that is wrong by a factor. Counting employee records instead of
  active employees, adding an annual fee onto a monthly bill, charging setup
  every month - none of these look wrong on the screen. They look like an
  invoice.

  A number produced from nothing. A month with no count must yield NO figure,
  not zero. Zero is a free month that looks exactly like a correct bill.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import estimate as est
from alvoraa_portal import pricing, usage


def _clear():
	for dt in ("Alvoraa Usage Record", "Alvoraa Subscription", "Alvoraa Plan",
	           "Alvoraa Operations Pack", "Alvoraa Module Price"):
		for name in frappe.get_all(dt, pluck="name"):
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
	settings = frappe.get_single("Alvoraa Pricing Settings")
	settings.seeded = None
	settings.pack_cap_per_user = 0
	settings.save(ignore_permissions=True)
	frappe.db.commit()


class EstimateCase(FrappeTestCase):
	SITE = "sharma.alvoraa.co"
	PERIOD = "2026-08"

	def setUp(self):
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf["alvoraa_control_plane"] = 1
		_clear()
		pricing.seed()
		if not frappe.db.exists("Customer", "Sharma Textiles"):
			frappe.get_doc({"doctype": "Customer", "customer_name": "Sharma Textiles"}
			               ).insert(ignore_permissions=True)

	def tearDown(self):
		_clear()
		if self._plane is None:
			frappe.conf.pop("alvoraa_control_plane", None)
		else:
			frappe.conf["alvoraa_control_plane"] = self._plane

	def sub(self, **kw):
		doc = frappe.get_doc({
			"doctype": "Alvoraa Subscription", "site_name": self.SITE,
			"status": "Active", "customer": "Sharma Textiles",
			"plan": "Business", "started_on": "2026-01-15", **kw})
		doc.insert(ignore_permissions=True)
		return doc

	def counted(self, heads, packs=None):
		usage._write_record(self.SITE, self.PERIOD, {
			"employees": {"total": heads + 250,
			              "by_status": {"Active": heads, "Left": 250},
			              "active_by_employment_type": {"Full-time": heads}},
			"users_by_module": packs or {},
		}, None)

	def amount(self, out, what):
		for line in out["lines"]:
			if line["what"].startswith(what):
				return line["amount"]
		return None


class TestTheWorkedExample(EstimateCase):
	"""Sharma Textiles: 312 employee records, 52 of them billable."""

	def test_the_whole_bill(self):
		self.sub(addons=[{"feature_key": "payroll"}],
		         packs=[{"pack": "Finance", "named_users": 3}])
		self.counted(52)
		out = est.estimate(self.SITE, self.PERIOD)

		self.assertTrue(out["complete"])
		self.assertEqual(out["billable_employees"], 52)
		self.assertEqual(self.amount(out, "Business platform fee"), 4999)
		self.assertEqual(self.amount(out, "Payroll"), 52 * 25)
		self.assertEqual(self.amount(out, "Operations packs"), 3 * 300)
		self.assertEqual(out["totals"]["due_this_period"], 4999 + 1300 + 900)

	def test_the_leavers_never_reach_the_bill(self):
		"""312 records would land them three bands up and quadruple the bill."""
		self.sub(addons=[{"feature_key": "payroll"}])
		self.counted(52)
		out = est.estimate(self.SITE, self.PERIOD)
		self.assertEqual(self.amount(out, "Payroll"), 1300)
		self.assertNotEqual(self.amount(out, "Payroll"), 312 * 25)


class TestTheIncludedHeadcount(EstimateCase):
	def test_under_the_included_count_costs_only_the_fee(self):
		self.sub(plan="Starter")          # 25 included, 75 extra PEPM
		self.counted(20)
		out = est.estimate(self.SITE, self.PERIOD)
		self.assertEqual(out["totals"]["due_this_period"], 1999)
		self.assertIsNone(self.amount(out, "Additional employees"))

	def test_exactly_the_included_count_costs_only_the_fee(self):
		"""The off-by-one that would charge for one imaginary person."""
		self.sub(plan="Starter")
		self.counted(25)
		self.assertEqual(
			est.estimate(self.SITE, self.PERIOD)["totals"]["due_this_period"], 1999)

	def test_over_the_included_count_charges_only_the_excess(self):
		self.sub(plan="Starter")
		self.counted(30)
		out = est.estimate(self.SITE, self.PERIOD)
		self.assertEqual(self.amount(out, "Additional employees"), 5 * 75)
		self.assertEqual(out["totals"]["due_this_period"], 1999 + 375)


class TestItRefusesToGuess(EstimateCase):
	def test_no_count_produces_no_figure_and_says_why(self):
		"""Zero would be a free month that looks like a correct invoice."""
		self.sub(addons=[{"feature_key": "payroll"}])
		out = est.estimate(self.SITE, self.PERIOD)
		self.assertFalse(out["complete"])
		self.assertIsNone(out["billable_employees"])
		self.assertIsNone(self.amount(out, "Payroll"))
		self.assertTrue(any("no usage count" in w for w in out["why_not"]))

	def test_a_failed_count_is_not_treated_as_zero(self):
		self.sub(addons=[{"feature_key": "payroll"}])
		usage._write_record(self.SITE, self.PERIOD, None, "site was down")
		out = est.estimate(self.SITE, self.PERIOD)
		self.assertFalse(out["complete"])
		self.assertIsNone(self.amount(out, "Payroll"))

	def test_the_platform_fee_still_shows_without_a_count(self):
		"""It does not depend on headcount, so withholding it would hide the
		one number we DO know."""
		self.sub()
		out = est.estimate(self.SITE, self.PERIOD)
		self.assertEqual(self.amount(out, "Business platform fee"), 4999)

	def test_a_quote_only_plan_is_not_invented(self):
		self.sub(plan="Enterprise Custom", status="Active")
		self.counted(2000)
		out = est.estimate(self.SITE, self.PERIOD)
		self.assertFalse(out["complete"])
		self.assertTrue(any("quote only" in w for w in out["why_not"]))

	def test_a_site_with_no_subscription_gives_nothing(self):
		out = est.estimate("nobody.alvoraa.co", self.PERIOD)
		self.assertFalse(out["complete"])
		self.assertEqual(out["totals"]["due_this_period"], 0)


class TestRecurrenceIsKeptApart(EstimateCase):
	def test_an_annual_fee_is_not_added_to_a_monthly_bill(self):
		"""Summing them shows a monthly figure twelve times too big."""
		self.sub(billing_frequency="Annual", addons=[{"feature_key": "payroll"}])
		self.counted(52)
		out = est.estimate(self.SITE, self.PERIOD)
		self.assertEqual(out["totals"]["annual"], 49990)   # ten months' price
		self.assertEqual(out["totals"]["due_this_period"], 1300)

	def test_setup_is_charged_in_its_first_month_only(self):
		self.sub(implementation_fee=25000, started_on="2026-08-03")
		self.counted(52)
		out = est.estimate(self.SITE, self.PERIOD)
		self.assertEqual(self.amount(out, "Implementation"), 25000)
		self.assertEqual(out["totals"]["one-time"], 25000)

	def test_setup_is_never_charged_again(self):
		"""A flag somebody has to clear gets missed, and the customer pays
		setup twice. The start date decides instead."""
		self.sub(implementation_fee=25000, started_on="2026-01-15")
		self.counted(52)
		out = est.estimate(self.SITE, self.PERIOD)
		self.assertIsNone(self.amount(out, "Implementation"))
		self.assertEqual(out["totals"]["one-time"], 0)


class TestPackCap(EstimateCase):
	def _cap(self, value):
		s = frappe.get_single("Alvoraa Pricing Settings")
		s.pack_cap_per_user = value
		s.save(ignore_permissions=True)

	def test_one_pack_is_simply_users_times_rate(self):
		self._cap(799)
		self.sub(packs=[{"pack": "Finance", "named_users": 4}])
		self.counted(52)
		self.assertEqual(self.amount(est.estimate(self.SITE, self.PERIOD),
		                             "Operations packs"), 1200)

	def test_the_cap_applies_per_user_assuming_the_same_people(self):
		"""Finance 5 at 300, Trade 3 at 250, Manufacturing 2 at 250, cap 799.

		    users 1-2  all three   800 -> 799
		    user 3     two         550
		    users 4-5  Finance     300 each
		"""
		self._cap(799)
		self.sub(packs=[{"pack": "Finance", "named_users": 5},
		                {"pack": "Trade", "named_users": 3},
		                {"pack": "Manufacturing", "named_users": 2}])
		self.counted(52)
		self.assertEqual(self.amount(est.estimate(self.SITE, self.PERIOD),
		                             "Operations packs"),
		                 799 + 799 + 550 + 300 + 300)

	def test_without_a_cap_it_is_the_plain_sum(self):
		self._cap(0)
		self.sub(packs=[{"pack": "Finance", "named_users": 5},
		                {"pack": "Trade", "named_users": 3},
		                {"pack": "Manufacturing", "named_users": 2}])
		self.counted(52)
		self.assertEqual(self.amount(est.estimate(self.SITE, self.PERIOD),
		                             "Operations packs"),
		                 5 * 300 + 3 * 250 + 2 * 250)

	def test_no_packs_is_no_line(self):
		self.sub()
		self.counted(52)
		self.assertIsNone(self.amount(est.estimate(self.SITE, self.PERIOD),
		                              "Operations packs"))


class TestOurOwnTenants(EstimateCase):
	def test_internal_is_priced_in_full(self):
		"""allabouthr exists to show what a change costs before a customer sees
		it. A bench that does not compute is not a bench."""
		self.sub(status="Internal", customer=None,
		         addons=[{"feature_key": "payroll"}])
		self.counted(52)
		out = est.estimate(self.SITE, self.PERIOD)
		self.assertTrue(out["complete"])
		self.assertEqual(out["totals"]["due_this_period"], 4999 + 1300)
		self.assertFalse(out["will_be_invoiced"])

	def test_internal_money_is_left_out_of_the_revenue_figure(self):
		self.sub(status="Internal", customer=None)
		self.counted(52)
		out = est.estimate_all(self.PERIOD)
		self.assertEqual(out["invoiceable_total"], 0)
		self.assertEqual(out["ready"], 0)
		self.assertEqual(out["tenants"][0]["due"], 4999)   # still priced

	def test_a_real_customer_does_count_towards_revenue(self):
		self.sub()
		self.counted(52)
		out = est.estimate_all(self.PERIOD)
		self.assertEqual(out["invoiceable_total"], 4999)
		self.assertEqual(out["ready"], 1)

	def test_anything_stopping_a_bill_is_named(self):
		self.sub()
		out = est.estimate_all(self.PERIOD)
		self.assertEqual(out["blocked"][0]["site"], self.SITE)
		self.assertTrue(out["blocked"][0]["why"])


class TestControlPlaneOnly(FrappeTestCase):
	def setUp(self):
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf.pop("alvoraa_control_plane", None)

	def tearDown(self):
		if self._plane is not None:
			frappe.conf["alvoraa_control_plane"] = self._plane

	def test_estimating_is_refused_on_a_tenant(self):
		with self.assertRaises(frappe.ValidationError):
			est.estimate("anything")

	def test_the_revenue_figure_is_refused_on_a_tenant(self):
		with self.assertRaises(frappe.ValidationError):
			est.estimate_all()
