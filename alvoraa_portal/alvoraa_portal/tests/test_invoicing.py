"""The last step, and the one with legal weight.

Everything before this produced numbers on a screen. This produces a document
that goes to a customer, posts to a ledger, and - on the control plane, where
india_compliance is installed - can be transmitted to the government.

So the tests are about the ways that goes wrong:

  billing the same month twice because somebody re-ran the job
  billing our own demo site
  billing from a count that failed, or was never taken
  an annual fee landing on a monthly invoice
  an invoice submitted by a machine instead of read by a person
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import invoicing, pricing, usage


def _clear():
	for name in frappe.get_all("Sales Invoice",
	                           filters={"customer": ("like", "Invoice Test%")},
	                           pluck="name"):
		doc = frappe.get_doc("Sales Invoice", name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc("Sales Invoice", name, force=True, ignore_permissions=True)
	for dt in ("Alvoraa Usage Record", "Alvoraa Subscription", "Alvoraa Plan",
	           "Alvoraa Operations Pack", "Alvoraa Module Price"):
		for name in frappe.get_all(dt, pluck="name"):
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
	settings = frappe.get_single("Alvoraa Pricing Settings")
	settings.seeded = None
	settings.pack_cap_per_user = 0
	settings.save(ignore_permissions=True)
	frappe.db.commit()


class InvoiceCase(FrappeTestCase):
	SITE = "sharma.alvoraa.co"
	PERIOD = "2026-08"
	CUSTOMER = "Invoice Test Customer"

	def setUp(self):
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf["alvoraa_control_plane"] = 1
		_clear()
		pricing.seed()
		if not frappe.db.exists("Customer", self.CUSTOMER):
			frappe.get_doc({"doctype": "Customer", "customer_name": self.CUSTOMER}
			               ).insert(ignore_permissions=True)

	def tearDown(self):
		_clear()
		if self._plane is None:
			frappe.conf.pop("alvoraa_control_plane", None)
		else:
			frappe.conf["alvoraa_control_plane"] = self._plane

	def sub(self, **kw):
		return frappe.get_doc({
			"doctype": "Alvoraa Subscription", "site_name": self.SITE,
			"status": "Active", "customer": self.CUSTOMER, "plan": "Business",
			"started_on": "2026-01-15", **kw}).insert(ignore_permissions=True)

	def counted(self, heads=52):
		usage._write_record(self.SITE, self.PERIOD, {
			"employees": {"total": heads + 250,
			              "by_status": {"Active": heads, "Left": 250},
			              "active_by_employment_type": {"Full-time": heads}},
			"users_by_module": {},
		}, None)

	def ready(self, **kw):
		self.sub(**kw)
		self.counted()


class TestItOnlyEverDrafts(InvoiceCase):
	def test_the_invoice_is_left_as_a_draft(self):
		"""Submitting posts to the ledger and can transmit an e-invoice to the
		government. Not a decision for a job running at two in the morning."""
		self.ready()
		out = invoicing.raise_invoices(self.PERIOD, dry_run=False)
		name = out["drafted"][0]["draft"]
		self.assertEqual(frappe.db.get_value("Sales Invoice", name, "docstatus"), 0)

	def test_a_dry_run_creates_nothing(self):
		self.ready()
		out = invoicing.raise_invoices(self.PERIOD, dry_run=True)
		self.assertTrue(out["dry_run"])
		self.assertIsNone(out["drafted"][0]["draft"])
		self.assertEqual(frappe.db.count("Sales Invoice",
		                                 {"customer": self.CUSTOMER}), 0)

	def test_a_dry_run_still_says_what_it_would_charge(self):
		self.ready()
		out = invoicing.raise_invoices(self.PERIOD, dry_run=True)
		self.assertEqual(out["drafted"][0]["amount"], 4999)


class TestNobodyIsBilledTwice(InvoiceCase):
	def test_running_the_job_again_skips_a_month_already_invoiced(self):
		"""The single worst failure this module could have."""
		self.ready()
		first = invoicing.raise_invoices(self.PERIOD, dry_run=False)
		again = invoicing.raise_invoices(self.PERIOD, dry_run=False)
		self.assertEqual(len(first["drafted"]), 1)
		self.assertEqual(again["drafted"], [])
		self.assertIn("already invoiced", again["skipped"][0]["why"])
		self.assertEqual(frappe.db.count("Sales Invoice",
		                                 {"customer": self.CUSTOMER}), 1)

	def test_the_link_is_kept_on_the_count_that_produced_it(self):
		self.ready()
		out = invoicing.raise_invoices(self.PERIOD, dry_run=False)
		self.assertEqual(
			frappe.db.get_value("Alvoraa Usage Record", f"{self.SITE} {self.PERIOD}",
			                    "sales_invoice"),
			out["drafted"][0]["draft"])

	def test_a_cancelled_invoice_may_be_raised_again(self):
		"""Cancelling one is exactly how you ask for a new one."""
		self.ready()
		name = invoicing.raise_invoices(self.PERIOD, dry_run=False)["drafted"][0]["draft"]
		doc = frappe.get_doc("Sales Invoice", name)
		doc.submit()
		doc.cancel()
		again = invoicing.raise_invoices(self.PERIOD, dry_run=False)
		self.assertEqual(len(again["drafted"]), 1)


class TestWhoIsSkipped(InvoiceCase):
	def test_our_own_tenants_are_never_invoiced(self):
		self.ready(status="Internal", customer=None)
		out = invoicing.raise_invoices(self.PERIOD, dry_run=False)
		self.assertEqual(out["drafted"], [])
		self.assertIn("ours", out["skipped"][0]["why"])

	def test_a_cancelled_subscription_is_not_invoiced(self):
		self.ready(status="Cancelled")
		self.assertEqual(
			invoicing.raise_invoices(self.PERIOD, dry_run=False)["drafted"], [])

	def test_a_month_never_counted_is_not_invoiced(self):
		"""Better a late invoice than one built on a number nobody measured."""
		self.sub()
		out = invoicing.raise_invoices(self.PERIOD, dry_run=False)
		self.assertEqual(out["drafted"], [])
		self.assertIn("no usage count", out["skipped"][0]["why"])

	def test_a_failed_count_is_not_invoiced(self):
		self.sub()
		usage._write_record(self.SITE, self.PERIOD, None, "site was down")
		out = invoicing.raise_invoices(self.PERIOD, dry_run=False)
		self.assertEqual(out["drafted"], [])
		self.assertIn("failed", out["skipped"][0]["why"])

	def test_a_zero_bill_raises_nothing(self):
		"""An invoice for nothing still costs somebody the time to read it."""
		self.sub(plan="Enterprise Custom")     # quote only, so no fee
		self.counted()
		self.assertEqual(
			invoicing.raise_invoices(self.PERIOD, dry_run=False)["drafted"], [])


class TestWhatIsOnIt(InvoiceCase):
	def _invoice(self, **kw):
		self.ready(**kw)
		out = invoicing.raise_invoices(self.PERIOD, dry_run=False)
		return frappe.get_doc("Sales Invoice", out["drafted"][0]["draft"])

	def test_each_charge_is_its_own_line(self):
		doc = self._invoice(addons=[{"feature_key": "payroll"}],
		                    packs=[{"pack": "Finance", "named_users": 3}])
		self.assertEqual(len(doc.items), 3)
		self.assertEqual(doc.total, 4999 + 52 * 25 + 3 * 300)

	def test_a_line_says_what_it_is_in_english(self):
		doc = self._invoice(addons=[{"feature_key": "payroll"}])
		payroll = [i for i in doc.items if "Payroll" in i.description][0]
		self.assertIn("52 employees", payroll.description)

	def test_an_annual_fee_never_lands_on_a_monthly_invoice(self):
		"""It belongs to the year it covers. On a month it is twelve times wrong."""
		doc = self._invoice(billing_frequency="Annual",
		                    addons=[{"feature_key": "payroll"}])
		self.assertEqual(doc.total, 52 * 25)
		self.assertTrue(all("platform fee" not in i.description for i in doc.items))

	def test_the_headcount_is_written_on_the_invoice(self):
		"""The number a customer will ring about, answered on the document."""
		doc = self._invoice()
		self.assertIn("Billable employees counted at month end: 52", doc.remarks)

	def test_it_is_dated_at_the_end_of_the_month_it_covers(self):
		doc = self._invoice()
		self.assertEqual(str(doc.posting_date), "2026-08-31")

	def test_the_items_are_services_not_stock(self):
		"""A subscription line must never look to ERPNext like something that
		moves in and out of a warehouse."""
		self._invoice()
		for key in ("platform", "module", "packs"):
			code = invoicing.ITEMS[key][0]
			if frappe.db.exists("Item", code):
				self.assertEqual(
					frappe.db.get_value("Item", code, "is_stock_item"), 0, code)


class TestTheMonthlyPicture(InvoiceCase):
	def test_it_separates_raised_from_waiting(self):
		self.ready()
		invoicing.raise_invoices(self.PERIOD, dry_run=False)
		out = invoicing.invoice_run_summary(self.PERIOD)
		self.assertEqual(out["raised"][0]["state"], "draft")
		self.assertEqual(out["drafted_value"], 4999)
		self.assertEqual(out["waiting"], [])

	def test_it_names_what_is_holding_a_bill_up(self):
		self.sub()      # counted nothing
		out = invoicing.invoice_run_summary(self.PERIOD)
		self.assertFalse(out["waiting"][0]["ready"])
		self.assertIn("no usage count", out["waiting"][0]["why"])

	def test_a_tenant_ready_to_bill_is_marked_ready(self):
		self.ready()
		out = invoicing.invoice_run_summary(self.PERIOD)
		self.assertTrue(out["waiting"][0]["ready"])
		self.assertEqual(out["ready_to_raise"], 1)


class TestControlPlaneOnly(FrappeTestCase):
	def setUp(self):
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf.pop("alvoraa_control_plane", None)

	def tearDown(self):
		if self._plane is not None:
			frappe.conf["alvoraa_control_plane"] = self._plane

	def test_invoicing_is_refused_on_a_tenant(self):
		with self.assertRaises(frappe.ValidationError):
			invoicing.raise_invoices()

	def test_the_summary_is_refused_on_a_tenant(self):
		with self.assertRaises(frappe.ValidationError):
			invoicing.invoice_run_summary()


class TestBillingNeverWidensTenantAccess(FrappeTestCase):
	"""A Link field on a billing record must not grant tenants read on its target.

	This is a regression test for something nobody wrote and nobody intended.

	Our billing doctypes live in the Alvoraa Portal module, which every tenant
	buys. linked_dependencies() derives what a tenant may read from what the
	SOLD modules link to. So the day Alvoraa Usage Record gained a Link to
	Sales Invoice, Sales Invoice stopped being blocked - on every tenant, at
	once, because a field was added to a billing record.

	No plan changed. No rule changed. A customer on Starter could have read
	invoices. The suite caught it; without this test the next Link on a billing
	doctype does the same thing again, silently, to whatever it points at.
	"""

	def test_sales_invoice_is_not_granted_by_our_link_to_it(self):
		from alvoraa_portal import subscription as sub

		starter = sub.plan_features("starter")
		self.assertNotIn("Sales Invoice", sub.linked_dependencies(starter))

	def test_every_billing_doctype_is_named_as_control_plane_only(self):
		"""The list is what does the work, so an unnamed one is a hole."""
		from alvoraa_portal import subscription as sub

		ours = frappe.get_all("DocType",
		                      filters={"module": "Alvoraa Portal",
		                               "name": ("like", "Alvoraa %")},
		                      pluck="name")
		missing = [d for d in ours if d not in sub.CONTROL_PLANE_DOCTYPES]
		self.assertEqual(missing, [],
		                 "control-plane doctypes not excluded from tenant access "
		                 "derivation: " + ", ".join(missing))
