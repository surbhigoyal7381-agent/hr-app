"""One pricing tier.

Seven at launch, and more can be added by a person rather than a release - which
is the point. A plan is a headcount band, a monthly fee, and the list of
features that fee includes.

Two things are checked here that only bite later if they are not:

  A feature a plan promises must exist. Otherwise a tenant is sold something
  `update_tenant` can never switch on, and the failure surfaces as an empty
  screen weeks after the contract was signed.

  Two public plans cannot cover the same headcount. The band is what picks a
  plan for a tenant of a given size, so an overlap means the same customer has
  two correct prices and the bill depends on which row was read first. Private
  plans are exempt: they are chosen by name for one client, never matched.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from frappe.utils import cint, flt

from alvoraa_portal.subscription import feature_spec

# band_to of 0 means open-ended. Comparing against a large number keeps the
# overlap test one expression instead of four cases.
OPEN_ENDED = 10 ** 9


class AlvoraaPlan(Document):
	def validate(self):
		self._normalise()
		self._check_band()
		self._check_price()
		self._check_features()
		self._check_no_overlap()
		if self.is_private and not self.built_for:
			frappe.throw(_("A private plan needs the customer it was built for, so a "
			               "one-off deal can be traced back to who agreed it."))
		if not self.is_private:
			self.built_for = None

	def _normalise(self):
		"""Turn empty number fields into zero before anything compares them.

		A blank Int or Currency reaches the controller as None, not 0 - Frappe
		only fills a default when the field declares one. Comparing None with a
		number raises a TypeError, which reaches the user as an internal server
		error with no idea which field was left empty.
		"""
		self.band_from = cint(self.band_from)
		self.band_to = cint(self.band_to)
		self.included_employees = cint(self.included_employees)
		self.platform_fee = flt(self.platform_fee)
		self.annual_fee = flt(self.annual_fee)
		self.additional_pepm = flt(self.additional_pepm)

	def _check_band(self):
		if self.band_from < 1:
			frappe.throw(_("The band has to start at one employee or more."))
		if self.band_to and self.band_to < self.band_from:
			frappe.throw(_("The band ends ({0}) before it starts ({1}).")
			             .format(self.band_to, self.band_from))
		if self.included_employees < 0:
			frappe.throw(_("Included employees cannot be negative."))

	def _check_price(self):
		if self.is_quote_only:
			# Negotiated. Storing a fee here would let an invoice run pick up a
			# number nobody ever quoted.
			self.platform_fee = 0
			self.annual_fee = 0
			return
		if not self.platform_fee:
			frappe.throw(_("A plan needs a monthly fee, or must be marked quote only."))
		if self.annual_fee and self.annual_fee > self.platform_fee * 12:
			frappe.throw(_("The annual fee is more than paying monthly for a year. "
			               "Paying up front is meant to be the cheaper way."))

	def _check_features(self):
		seen = set()
		for row in self.features:
			key = (row.feature_key or "").strip()
			row.feature_key = key
			spec = feature_spec(key)
			if not spec:
				frappe.throw(
					_("Row {0}: {1} is not a feature this product has, so a tenant on "
					  "this plan could never be given it.")
					.format(row.idx, frappe.bold(key)))
			if key in seen:
				frappe.throw(_("Row {0}: {1} is listed twice.")
				             .format(row.idx, frappe.bold(key)))
			seen.add(key)
			row.feature_label = spec.get("label") or key

	def _check_no_overlap(self):
		if self.is_private or not self.is_active:
			return
		mine_to = self.band_to or OPEN_ENDED
		others = frappe.get_all(
			"Alvoraa Plan",
			filters={"name": ("!=", self.name), "is_active": 1, "is_private": 0},
			fields=["name", "band_from", "band_to"])
		for other in others:
			other_to = other.band_to or OPEN_ENDED
			if self.band_from <= other_to and other.band_from <= mine_to:
				frappe.throw(
					_("This band overlaps {0} ({1} to {2}). A tenant of that size would "
					  "match two plans, and there would be no right answer for which "
					  "price applies.")
					.format(frappe.bold(other.name), other.band_from,
					        other.band_to or _("above")),
					title=_("Overlapping bands"))
