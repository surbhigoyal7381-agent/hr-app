"""What one sellable module costs.

The price list is rows, not constants. That was the requirement the whole
pricing design followed from: a rate has to be changeable by a person on a
Tuesday, without a deploy.

The one thing this doctype refuses to allow is a price for something that does
not exist. `feature_key` is checked against the feature registry in
subscription.py, which is the same list `update_tenant` switches modules on
from. If the registry does not know a key, nothing can ever grant it - so a
sellable price for it would be a promise the product cannot keep.

Coming Soon and Service rows are the deliberate exception. A roadmap item is
worth listing with an intended price, and a service like a custom report is
delivered by a human rather than a switch. Neither is in the registry, and
neither can be sold: `is_sellable` stays 0, so anything reading this list for
"what can I put on a subscription" skips them.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from alvoraa_portal.subscription import feature_spec


class AlvoraaModulePrice(Document):
	def validate(self):
		self.feature_key = (self.feature_key or "").strip()
		spec = feature_spec(self.feature_key)
		self.in_registry = 1 if spec else 0

		if not spec and self.status == "Built":
			frappe.throw(
				_("{0} is not a feature this product has. Built modules must exist in "
				  "the registry; use Coming Soon for something planned, or Service for "
				  "work a person delivers by hand.").format(frappe.bold(self.feature_key)),
				title=_("Unknown feature"),
			)

		if spec and not self.module_label:
			self.module_label = spec.get("label") or self.feature_key
		if not self.module_label:
			self.module_label = self.feature_key

		if self.rate and self.rate < 0:
			frappe.throw(_("A rate cannot be negative."))

		# Computed, never typed. A module with no price cannot be sold, however
		# finished it is; a module the registry does not know cannot be sold at
		# all. Both conditions have to hold.
		self.is_sellable = 1 if (spec and self.status == "Built" and self.rate) else 0
