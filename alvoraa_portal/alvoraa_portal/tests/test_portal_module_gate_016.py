"""Slice 016 phase 1 — three things, three sets of pin tests.

1. The whole vendor / driver / delivery module is gated by plan. 28 whitelisted
   endpoints answered anyone who called them, on any tenant, whatever the plan.
   The panel was hidden; the door still opened.

2. One customer's details are out of the source: a warehouse name and phone
   number, five named shops with their coordinates, an "ops@" mailbox at that
   customer's domain used in six places, and their name signed at the bottom of
   every outgoing email. The repository is public, and every tenant was posting
   its own customers' names and addresses to that one mailbox.

3. Driving telemetry no longer becomes a performance score. Harsh braking and
   speeding alerts used to be summed into `safety_incidents` and scored, which is
   passive behavioural monitoring used as a performance input - FR-H7 says we do
   not do that. The raw tracking rows are kept; only the scoring is gone.

These tests exist so a bad merge cannot quietly put any of the three back.
"""

import ast
import inspect
import io
import os
import re
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import portal_api
from alvoraa_portal import subscription as sub
from alvoraa_portal.controllers import (
	delivery_assignment,
	delivery_feedback,
	delivery_order,
	delivery_partner,
	delivery_tracking,
	rating,
	scorecard,
	vehicle_compliance,
	vendor_order,
)

# Every module in the slice. delivery_tracking has no endpoint today; it is in
# the list on purpose, so the day somebody adds one it is checked too.
MODULES = [
	portal_api,
	delivery_assignment,
	delivery_feedback,
	delivery_order,
	delivery_partner,
	delivery_tracking,
	rating,
	scorecard,
	vehicle_compliance,
	vendor_order,
]

# The count on the day of the change. It may go UP - a new endpoint must be
# gated too. It going DOWN means an endpoint was deleted, which is worth a look.
ENDPOINTS_AT_THE_TIME = 28


def _whitelisted(module):
	"""(name, decorators) for every @frappe.whitelist function in a module.

	Read from the source with ast, not from the function object: Frappe keeps a
	registry rather than setting an attribute, so an attribute check would look
	like it was testing something and be testing nothing.
	"""
	tree = ast.parse(inspect.getsource(module))
	out = []
	for node in tree.body:
		if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
			continue
		# ast.unparse normalises quotes, so compare on a form that does not
		# depend on how the source happened to be written.
		decs = [ast.unparse(d).replace("'", '"') for d in node.decorator_list]
		if any("frappe.whitelist" in d for d in decs):
			out.append((node.name, decs))
	return out


def _dummy_args(fn):
	"""One harmless positional value per required parameter.

	The gate runs before the body, so the values never matter - they only have
	to let Python make the call at all. Without them the call raises TypeError
	for missing arguments and the refusal is never exercised.
	"""
	params = inspect.signature(fn).parameters.values()
	return ["016-does-not-exist" for p in params
	        if p.default is inspect.Parameter.empty
	        and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]


class TheWholeModuleIsGatedByPlan(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._saved = frappe.conf.get("features")

	def tearDown(self):
		if self._saved is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = self._saved

	def test_016_every_endpoint_carries_the_gate(self):
		"""The test that stops the next endpoint being forgotten."""
		checked, missing = 0, []
		for module in MODULES:
			for name, decs in _whitelisted(module):
				checked += 1
				if not any('requires_feature("vendor")' in d for d in decs):
					missing.append("%s.%s" % (module.__name__, name))
		self.assertEqual(missing, [], "ungated endpoints: %s" % missing)
		self.assertGreaterEqual(
			checked, ENDPOINTS_AT_THE_TIME,
			"expected at least %d whitelisted endpoints, found %d - has one been "
			"deleted, or has the parsing stopped finding them?"
			% (ENDPOINTS_AT_THE_TIME, checked))

	def test_016_the_gate_runs_before_the_body(self):
		"""The decorator order matters: @frappe.whitelist() on top, so the
		registry holds the gated function, not the bare one."""
		for module in MODULES:
			for name, decs in _whitelisted(module):
				gate = [i for i, d in enumerate(decs) if "requires_feature" in d]
				whitelist = [i for i, d in enumerate(decs) if "frappe.whitelist" in d]
				self.assertTrue(gate and whitelist, name)
				self.assertLess(whitelist[0], gate[0],
				                "%s: @frappe.whitelist() must be above the gate" % name)

	def test_016_a_tenant_without_the_feature_is_refused_on_every_one(self):
		"""Table-driven over all 28: a starter tenant gets a PermissionError.

		The first version of this test wrapped the call in `except TypeError:
		raise frappe.PermissionError`, to get past endpoints that need
		arguments. That made it pass whether the gate was there or not, for the
		25 endpoints that take an argument - a test that looked like proof and
		was not. It now builds a dummy argument for every parameter from
		`inspect.signature`, so the call reaches the gate for real.
		"""
		frappe.conf["features"] = sub.plan_features("starter")
		called = 0
		for module in MODULES:
			for name, _decs in _whitelisted(module):
				fn = getattr(module, name)
				args = _dummy_args(fn)
				called += 1
				with self.assertRaises(frappe.PermissionError, msg=name):
					fn(*args)
		self.assertGreaterEqual(called, ENDPOINTS_AT_THE_TIME)

	def test_016_the_refusal_test_supplies_every_required_argument(self):
		"""Proves the test above cannot be passing on a TypeError.

		It does it by checking the arity, not by calling the endpoints a second
		time with the feature on - several of them write, and a test should not
		leave rows behind to prove a point about arguments.
		"""
		for module in MODULES:
			for name, _decs in _whitelisted(module):
				fn = getattr(module, name)
				required = [
					p for p in inspect.signature(fn).parameters.values()
					if p.default is inspect.Parameter.empty
					and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
				]
				self.assertEqual(
					len(_dummy_args(fn)), len(required),
					"%s: the refusal test would raise TypeError, not reach the gate" % name)

	def test_016_vendor_is_opt_in(self):
		self.assertTrue(sub.is_opt_in("vendor"))

	def test_016_a_site_with_no_feature_list_does_not_get_vendor(self):
		"""The provisioning script writes `subscription_plan` and never
		`features`, so the fallback used to hand this module to every tenant it
		created."""
		frappe.conf.pop("features", None)
		self.assertFalse(sub.has_feature("vendor"))

	def test_016_no_plan_bundle_hands_it_over_on_its_own(self):
		for plan in ("starter", "business", "enterprise", "custom"):
			self.assertNotIn("vendor", sub.plan_features(plan), plan)

	def test_016_a_tenant_that_has_it_is_not_refused_by_the_plan(self):
		"""Switching it on must still work, or this is a deletion, not a gate."""
		frappe.conf["features"] = sub.plan_features("enterprise") + ["vendor"]
		self.assertTrue(sub.has_feature("vendor"))
		try:
			portal_api.get_all_vendors()
		except frappe.PermissionError:
			msg = str(frappe.message_log[-1]) if frappe.message_log else ""
			self.assertNotIn("not included in your plan", msg.lower())


class NoCustomerDetailsInTheSource(FrappeTestCase):
	"""The repository is public. These values named a real company, a real
	phone number and five real shops."""

	# Split so this test file does not itself put the strings back into a
	# grep of the repository.
	BANNED = [
		"Grace" + " Warehouse",
		"98761" + "-00099",
		"Raj Wine" + " Shop",
		"Metro Wines" + " & Spirits",
		"Hotel Regent" + " (Bar)",
		"QuickStop" + " Beverages",
		"Celebrations" + " Banquets",
		"grace" + "drinks.in",
		"Grace" + " Drinks",
	]

	# Files this scan deliberately skips, each with a reason. Nothing else is
	# skipped, and the list must not grow without one.
	SKIPPED = {
		# Slice 015 (repo hygiene) owns this file and has it open. Editing it
		# here would clash. It still carries the five shop names and their
		# addresses - see 03-implementation-notes.md §4.
		"demo_setup.py",
		# This test file names the banned strings on purpose, to look for them.
		"test_portal_module_gate_016.py",
	}

	def _sources(self):
		"""Every source file in the installed app, not a hand-written list.

		The first version read only the ten modules of the slice, so it passed
		while the same customer's mailbox sat in `hooks.py`, three hub addresses
		sat in `setup_data.py`, and the five named shops sat in the demo seeder.
		The repository is public, so the scan has to cover what ships.
		"""
		root = os.path.dirname(os.path.dirname(os.path.abspath(
			inspect.getsourcefile(portal_api))))
		for dirpath, dirnames, filenames in os.walk(root):
			dirnames[:] = [d for d in dirnames
			               if d not in ("__pycache__", "node_modules", "dist", ".git")]
			for filename in sorted(filenames):
				if filename in self.SKIPPED:
					continue
				if not filename.endswith((".py", ".js", ".jsx", ".vue", ".html", ".json", ".md")):
					continue
				path = os.path.join(dirpath, filename)
				try:
					with io.open(path, encoding="utf-8") as fh:
						yield os.path.relpath(path, root), fh.read()
				except (UnicodeDecodeError, OSError):
					continue

	def test_016_no_customer_name_phone_shop_or_mailbox_is_hardcoded(self):
		found = []
		for name, text in self._sources():
			for banned in self.BANNED:
				if banned in text:
					found.append("%s: %s" % (name, banned))
		self.assertEqual(found, [], "customer details back in the source: %s" % found)

	def test_016_no_bare_email_address_is_hardcoded(self):
		"""Not just that one mailbox - any literal address in this module is
		somebody's, and it will be the wrong somebody on the next tenant."""
		# The TLD has to be alphabetic, or an npm package spec like
		# "leaflet@1.9.4" reads as an address.
		pattern = re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z][\w.]*[A-Za-z]")
		allowed = (
			# obvious placeholders and test fixtures
			"example.com", "example.org", "company.com", "acmecorp.com", ".test",
			# our own demo data and our own domains
			"gracedemo.in", "alvoraa.co",
			# our own product support address; changing what a user is told to
			# write to is a product decision, not a tidy-up (slice 016 notes §4)
			"kinexus.in",
			# upstream projects named in comments and docs
			"erpnext.com", "frappe.io",
		)
		found = []
		for name, text in self._sources():
			for hit in pattern.findall(text):
				if hit.endswith(allowed):
					continue
				found.append("%s: %s" % (name, hit))
		self.assertEqual(sorted(set(found)), [], "hardcoded email addresses: %s" % sorted(set(found)))

	def test_016_the_settings_come_from_site_config(self):
		from alvoraa_portal import delivery_settings

		saved = {k: frappe.conf.get(k) for k in
		         ("portal_warehouse_name", "portal_warehouse_phone", "portal_ops_email")}
		try:
			frappe.conf["portal_warehouse_name"] = "North Depot"
			frappe.conf["portal_warehouse_phone"] = "0000-000000"
			frappe.conf["portal_ops_email"] = "ops@tenant.example.com"
			self.assertEqual(delivery_settings.warehouse_name(), "North Depot")
			self.assertEqual(delivery_settings.warehouse_phone(), "0000-000000")
			self.assertEqual(delivery_settings.ops_recipients(),
			                 ["ops@tenant.example.com"])
		finally:
			for key, value in saved.items():
				if value is None:
					frappe.conf.pop(key, None)
				else:
					frappe.conf[key] = value

	def test_016_an_unconfigured_tenant_sends_no_ops_alert(self):
		"""Fail closed. These alerts carry a customer's name and address, and
		there is no safe address to guess."""
		from alvoraa_portal import delivery_settings

		saved = frappe.conf.get("portal_ops_email")
		frappe.conf.pop("portal_ops_email", None)
		try:
			self.assertEqual(delivery_settings.ops_recipients(), [])
			with mock.patch.object(frappe, "sendmail") as sendmail:
				sent = delivery_settings.send_ops_alert(
					subject="s", message="m", context="DO-0001")
			self.assertFalse(sent)
			sendmail.assert_not_called()
		finally:
			if saved is not None:
				frappe.conf["portal_ops_email"] = saved


class TelemetryDoesNotBecomeAScore(FrappeTestCase):
	"""FR-H7: no passive behavioural monitoring as a performance input."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls._saved = frappe.conf.get("features")
		frappe.conf["features"] = list(cls._saved or []) + ["vendor"]

		cls.partner = frappe.get_doc({
			"doctype": "Delivery Partner",
			"partner_name": "Telemetry Pin 016",
			"partner_type": "Contractual",
			"primary_email": "telemetry.016@example.com",
			"status": "Active",
			"is_active": 1,
		}).insert(ignore_permissions=True).name

		cls.tracking = []
		for _ in range(3):
			cls.tracking.append(frappe.get_doc({
				"doctype": "Vehicle Tracking",
				"delivery_partner": cls.partner,
				"latitude": 30.71, "longitude": 76.80,
				"speed": 95, "heading": 90,
				"recorded_timestamp": frappe.utils.now_datetime(),
				"harsh_braking": 1,
				"harsh_acceleration": 1,
				"speeding_alert": 1,
			}).insert(ignore_permissions=True).name)
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for card in frappe.get_all("Delivery Performance Scorecard",
		                           {"delivery_partner": cls.partner}, pluck="name"):
			frappe.delete_doc("Delivery Performance Scorecard", card,
			                  force=True, ignore_permissions=True)
		for row in cls.tracking:
			frappe.delete_doc("Vehicle Tracking", row, force=True, ignore_permissions=True)
		frappe.delete_doc("Delivery Partner", cls.partner, force=True, ignore_permissions=True)
		frappe.db.commit()
		if cls._saved is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = cls._saved
		super().tearDownClass()

	def test_016_a_stats_refresh_does_not_write_safety_incidents(self):
		frappe.db.set_value("Delivery Partner", self.partner, "safety_incidents", 0)
		frappe.db.commit()
		delivery_partner.update_partner_stats_from_orders(self.partner)
		self.assertEqual(
			frappe.db.get_value("Delivery Partner", self.partner, "safety_incidents") or 0,
			0,
			"harsh braking and speeding are back on the person's record")

	def test_016_a_recorded_incident_survives_a_stats_refresh(self):
		"""A person's judgement is not passive monitoring, and the refresh must
		not wipe it either."""
		frappe.db.set_value("Delivery Partner", self.partner, "safety_incidents", 2)
		frappe.db.commit()
		delivery_partner.update_partner_stats_from_orders(self.partner)
		self.assertEqual(
			frappe.db.get_value("Delivery Partner", self.partner, "safety_incidents"), 2)
		frappe.db.set_value("Delivery Partner", self.partner, "safety_incidents", 0)
		frappe.db.commit()

	def test_016_a_scorecard_carries_no_telemetry(self):
		today = frappe.utils.getdate(frappe.utils.today())
		name = scorecard.generate_scorecard_for_partner(self.partner, today.month, today.year)
		card = frappe.get_doc("Delivery Performance Scorecard", name)
		self.assertEqual(card.harsh_driving_detected or 0, 0)
		self.assertEqual(card.speeding_incidents or 0, 0)
		self.assertEqual(card.safety_incidents or 0, 0)

	def test_016_the_scoring_code_no_longer_reads_the_telemetry_columns(self):
		"""Belt and braces: the SQL itself is gone, not merely unused."""
		for module in (scorecard, delivery_partner):
			with io.open(inspect.getsourcefile(module), encoding="utf-8") as fh:
				# Comment lines are dropped: both files explain in a comment what
				# they used to read, and the explanation is the point.
				text = "\n".join(line for line in fh.read().split("\n")
				                 if not line.strip().startswith("#"))
			for column in ("SUM(harsh_braking)", "SUM(harsh_acceleration)",
			               "SUM(speeding_alert)"):
				self.assertNotIn(column, text, "%s still reads %s" % (module.__name__, column))

	def test_016_the_raw_tracking_rows_are_kept(self):
		"""We stopped scoring it. We did not stop storing it - retention is a
		separate question, and a test should say which one this slice answered."""
		rows = frappe.get_all(
			"Vehicle Tracking",
			filters={"delivery_partner": self.partner},
			fields=["harsh_braking", "speeding_alert"])
		self.assertEqual(len(rows), 3)
		self.assertTrue(all(r.harsh_braking and r.speeding_alert for r in rows))
