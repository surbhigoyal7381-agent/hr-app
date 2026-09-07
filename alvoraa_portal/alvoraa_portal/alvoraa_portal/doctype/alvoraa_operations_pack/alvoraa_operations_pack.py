"""A group of ERPNext modules sold together, priced per named user.

Two rules this enforces that the price list alone could not:

  A module belongs to at most one pack. Two packs claiming Accounts would make
  the same user billable twice for the same thing, and there would be no
  correct answer to which rate applied.

  The pack chain cannot loop. Trade requires Finance, Manufacturing requires
  Trade. A cycle would make "what else must they buy" run forever, and it is
  far easier to create one by accident than to notice it afterwards.

The pack owns the list of what is in it. `Alvoraa Module Price.pack` is written
from here on every save rather than typed, so the two can never disagree about
which pack a module belongs to.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from alvoraa_portal.subscription import feature_spec


class AlvoraaOperationsPack(Document):
	def validate(self):
		self._check_features()
		self._check_no_cycle()

	def on_update(self):
		self._stamp_module_prices()

	def on_trash(self):
		# Leave the price rows behind, but stop them pointing at a pack that is
		# gone - a link that resolves to nothing is worse than no link.
		for name in self._rows_pointing_here():
			frappe.db.set_value("Alvoraa Module Price", name, "pack", None,
			                    update_modified=False)

	def _check_features(self):
		seen = set()
		for row in self.features:
			key = (row.feature_key or "").strip()
			row.feature_key = key
			spec = feature_spec(key)
			if not spec:
				frappe.throw(
					_("Row {0}: {1} is not a feature this product has.")
					.format(row.idx, frappe.bold(key)))
			if not spec.get("erpnext"):
				frappe.throw(
					_("Row {0}: {1} is an Alvoraa HR feature, not an ERPNext module. "
					  "Operations packs carry ERPNext only; HR features are sold per "
					  "employee, not per named user.")
					.format(row.idx, frappe.bold(spec.get("label") or key)))
			if key in seen:
				frappe.throw(_("Row {0}: {1} is listed twice.")
				             .format(row.idx, frappe.bold(key)))
			seen.add(key)
			row.feature_label = spec.get("label") or key

			owner = frappe.db.get_value("Alvoraa Module Price", key, "pack")
			if owner and owner != self.name:
				frappe.throw(
					_("{0} is already in the {1} pack. A module belongs to one pack, or "
					  "a user holding both would be charged twice for it.")
					.format(frappe.bold(spec.get("label") or key), frappe.bold(owner)))

	def _check_no_cycle(self):
		seen, at = {self.name}, self.requires_pack
		while at:
			if at in seen:
				frappe.throw(
					_("{0} would make the pack requirements loop back on themselves.")
					.format(frappe.bold(self.requires_pack)),
					title=_("Circular requirement"))
			seen.add(at)
			at = frappe.db.get_value("Alvoraa Operations Pack", at, "requires_pack")

	def _rows_pointing_here(self):
		return frappe.get_all("Alvoraa Module Price", filters={"pack": self.name},
		                      pluck="name")

	def _stamp_module_prices(self):
		"""Make the price rows agree with this pack's contents."""
		mine = {row.feature_key for row in self.features}
		for name in self._rows_pointing_here():
			if name not in mine:
				frappe.db.set_value("Alvoraa Module Price", name, "pack", None,
				                    update_modified=False)
		for key in mine:
			if frappe.db.exists("Alvoraa Module Price", key):
				frappe.db.set_value("Alvoraa Module Price", key, "pack", self.name,
				                    update_modified=False)
