"""The few pricing numbers that belong to nothing in particular.

Only the operations pack cap lives here so far. It is a price, so by the same
rule as every other price it is a row a person can edit, not a constant in the
code.

The cap is a ceiling on what one named user can cost across every pack they
hold: hold Finance alone and pay its rate, hold all five and pay the cap rather
than the sum.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class AlvoraaPricingSettings(Document):
	def validate(self):
		if self.pack_cap_per_user and self.pack_cap_per_user < 0:
			frappe.throw(_("The cap cannot be negative."))
		self._check_cap_is_above_every_pack()

	def _check_cap_is_above_every_pack(self):
		"""A cap below a single pack's rate would discount that pack on its own.

		The cap exists to stop the total running away when someone buys
		everything. Set it under the dearest pack and it quietly becomes the
		price of that pack instead - a discount nobody decided to give.
		"""
		if not self.pack_cap_per_user:
			return  # zero means no cap, which is a valid choice
		dearest = frappe.get_all("Alvoraa Operations Pack", filters={"is_active": 1},
		                         fields=["name", "rate_per_user"],
		                         order_by="rate_per_user desc", limit=1)
		if dearest and dearest[0].rate_per_user > self.pack_cap_per_user:
			frappe.throw(
				_("The cap ({0}) is below the {1} pack on its own ({2}). That would "
				  "quietly discount a single pack, which is not what a cap is for.")
				.format(self.pack_cap_per_user, frappe.bold(dearest[0].name),
				        dearest[0].rate_per_user),
				title=_("Cap is too low"))
