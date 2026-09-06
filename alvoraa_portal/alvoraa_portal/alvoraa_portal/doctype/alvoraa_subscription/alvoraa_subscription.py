"""What one tenant has bought, and what they agreed to pay for it.

The bridge between a site on disk and a Customer in ERPNext. A tenant has no
record of its own - `list_tenants()` walks the sites folder and reads
site_config.json - so this is the first thing in the system that can be linked
to, reported on, or invoiced.

The agreed rate is stored on the row rather than read from the price list each
month. It costs one column, and it is the only way to honour a price after the
list moves. It also gives per-customer pricing for nothing: sell payroll at
Rs 25 generally and Rs 18 to one client, and their subscription keeps Rs 18.

What this refuses, and why each one is a bill that would otherwise be wrong:

  Selling something that is not sellable. A Coming Soon module carries an
  intended price so it can be shown; putting it on a subscription would charge
  for something no tenant can be given.

  Charging twice for one thing. If the plan already includes a module, an
  add-on row for it is a second charge for the same feature.

  Selling half a dependency. india_compliance without ERPNext Accounts installs
  an app whose every screen is then denied by our own access control. The same
  check that guards tenant creation guards the subscription.

  A pack without the pack it needs. Trade requires Finance. Sold apart, the
  customer opens Trade and finds it empty.

  An invoice with nobody to send it to. A live subscription needs a Customer;
  an internal one is ours and never leaves the building.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from alvoraa_portal.subscription import feature_spec, requirement_error

# Ours. Priced exactly like a customer so the pricing screens get exercised
# against a live site, but never invoiced and never counted as revenue.
INTERNAL = "Internal"


class AlvoraaSubscription(Document):
	def validate(self):
		self.site_name = (self.site_name or "").strip()
		self._check_party()
		self._check_plan()
		self._check_addons()
		self._check_packs()
		self._check_dependencies_are_whole()

	# ── who is being billed ──────────────────────────────────────────────
	def _check_party(self):
		if self.status == INTERNAL:
			# Deliberately allowed to have no customer. Requiring one would mean
			# inventing an ERPNext Customer for our own demo site, which then
			# shows up in every receivables report we ever run.
			return
		if not self.customer:
			frappe.throw(
				_("A subscription that gets invoiced needs a customer. Mark it "
				  "{0} if this tenant is ours.").format(frappe.bold(_(INTERNAL))))

	def _check_plan(self):
		if not self.plan and self.status not in (INTERNAL, "Trial"):
			frappe.throw(_("An active subscription needs a plan. Without one there "
			               "is no platform fee and no included features, so the "
			               "invoice would be built from nothing."))
		if self.plan and frappe.db.get_value("Alvoraa Plan", self.plan, "is_private"):
			built_for = frappe.db.get_value("Alvoraa Plan", self.plan, "built_for")
			if built_for and self.customer and built_for != self.customer:
				frappe.throw(
					_("{0} is a private plan built for {1}. It cannot be given to "
					  "another customer - that is how a one-off discount quietly "
					  "becomes everybody's price.")
					.format(frappe.bold(self.plan), frappe.bold(built_for)))

	# ── what they bought on top ──────────────────────────────────────────
	def _plan_features(self):
		if not self.plan:
			return set()
		return set(frappe.get_all("Alvoraa Plan Feature",
		                          filters={"parent": self.plan}, pluck="feature_key"))

	def _check_addons(self):
		included = self._plan_features()
		seen = set()
		for row in self.addons:
			key = (row.feature_key or "").strip()
			row.feature_key = key
			price = self._module_price(key, row.idx)

			if key in seen:
				frappe.throw(_("Row {0}: {1} is listed twice.")
				             .format(row.idx, frappe.bold(key)))
			seen.add(key)

			if key in included:
				frappe.throw(
					_("Row {0}: {1} is already included in the {2} plan. Charging "
					  "for it again bills the customer twice for one thing.")
					.format(row.idx, frappe.bold(price.module_label or key),
					        frappe.bold(self.plan)))

			if not price.is_sellable:
				frappe.throw(
					_("Row {0}: {1} cannot be sold yet - it is marked {2} in the "
					  "price list, or it has no rate. A subscription may only "
					  "carry things a tenant can actually be given.")
					.format(row.idx, frappe.bold(price.module_label or key),
					        frappe.bold(price.status)))

			row.module_label = price.module_label
			row.basis = price.basis
			if row.agreed_rate is None:
				# First time this row is added, take today's list price. After
				# that it is theirs, whatever the list does next.
				row.agreed_rate = price.rate
			if flt(row.agreed_rate) < 0:
				frappe.throw(_("Row {0}: a rate cannot be negative.").format(row.idx))

	def _module_price(self, key, idx):
		if not key or not frappe.db.exists("Alvoraa Module Price", key):
			frappe.throw(
				_("Row {0}: {1} is not in the price list. Nothing can be sold "
				  "before somebody prices it.").format(idx, frappe.bold(key or "?")))
		return frappe.db.get_value(
			"Alvoraa Module Price", key,
			["module_label", "basis", "rate", "is_sellable", "status"], as_dict=True)

	def _check_packs(self):
		held = set()
		for row in self.packs:
			if row.pack in held:
				frappe.throw(_("Row {0}: {1} is listed twice.")
				             .format(row.idx, frappe.bold(row.pack)))
			held.add(row.pack)
			if cint(row.named_users) < 1:
				frappe.throw(
					_("Row {0}: {1} needs at least one named user. A pack nobody "
					  "can open is a charge for nothing.")
					.format(row.idx, frappe.bold(row.pack)))
			if row.agreed_rate is None:
				row.agreed_rate = frappe.db.get_value(
					"Alvoraa Operations Pack", row.pack, "rate_per_user")

		# Trade needs Finance. Checked against the whole selection rather than
		# row by row, because the customer may have added them in any order.
		for pack in sorted(held):
			needs = frappe.db.get_value("Alvoraa Operations Pack", pack, "requires_pack")
			if needs and needs not in held:
				frappe.throw(
					_("{0} needs the {1} pack. Sold on its own it opens onto "
					  "screens that are not there.")
					.format(frappe.bold(pack), frappe.bold(needs)),
					title=_("Missing pack"))

	# ── the whole selection has to hold together ─────────────────────────
	def selected_features(self):
		"""Every feature key this subscription grants, from all three sources."""
		keys = self._plan_features()
		keys |= {row.feature_key for row in self.addons}
		for row in self.packs:
			keys |= set(frappe.get_all("Alvoraa Pack Feature",
			                           filters={"parent": row.pack}, pluck="feature_key"))
		return keys

	def _check_dependencies_are_whole(self):
		"""The same guard that protects tenant creation, applied to the contract.

		Catching it here matters more than catching it at provisioning: by then
		somebody has signed for it.
		"""
		problem = requirement_error(self.selected_features())
		if problem:
			frappe.throw(problem, title=_("Incomplete selection"))

	# ── read by the estimate and the invoice run ─────────────────────────
	@property
	def is_billable(self):
		"""Internal tenants are priced like anyone else and invoiced like nobody."""
		return self.status in ("Trial", "Active", "Suspended")

	def addon_rate(self, feature_key):
		for row in self.addons:
			if row.feature_key == feature_key:
				return flt(row.agreed_rate)
		return None

	def label_for(self, feature_key):
		return feature_spec(feature_key).get("label") or feature_key
