"""A seat in the organisation, which exists whether or not anybody is in it.

That is the whole distinction. A person-based chart draws people, so a vacancy
is an absence - nothing renders, and nobody notices the hole until somebody asks
why the South region has no numbers. Once a box is a seat, five things become
expressible that otherwise cannot be: an empty seat, two people in one seat
during a handover, a seat that starts next April, a seat with a budget, and a
successor named for the seat rather than for the person.

A nested set, the same shape Department already uses, so "everyone under this
position" stays one indexed read rather than a recursive walk.
"""

import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import NestedSet


class AlvoraaPosition(NestedSet):
	nsm_parent_field = "reports_to_position"

	def validate(self):
		self._check_not_its_own_ancestor()
		self._check_seats()
		self._check_dates()

	def on_update(self):
		super().on_update()
		self.validate_recursion()

	def on_trash(self):
		# A position with people in it must not vanish - the chart would hold an
		# employee attached to nothing.
		held = self._current_assignments()
		if held:
			frappe.throw(
				_("{0} still has {1} person(s) in it. Move them first.")
				.format(frappe.bold(self.name), len(held)))
		super().on_trash()

	# ── rules ────────────────────────────────────────────────────────────
	def _check_not_its_own_ancestor(self):
		if self.reports_to_position == self.name:
			frappe.throw(_("A position cannot report to itself."))

	def validate_recursion(self):
		"""Walk up the chain. A loop makes every subtree count run for ever."""
		seen, at = {self.name}, self.reports_to_position
		while at:
			if at in seen:
				frappe.throw(
					_("{0} would make the reporting line loop back on itself.")
					.format(frappe.bold(self.reports_to_position)),
					title=_("Circular reporting line"))
			seen.add(at)
			at = frappe.db.get_value("Alvoraa Position", at, "reports_to_position")

	def _check_seats(self):
		if flt(self.seats) < 0:
			frappe.throw(_("Seats cannot be negative."))
		# Reducing seats below what is already filled would make the position
		# over-full the moment it is saved, and the chart would say so for ever.
		filled = self.filled_weight()
		if flt(self.seats) and filled > flt(self.seats):
			frappe.throw(
				_("{0} already holds {1} of a person. It cannot be reduced to "
				  "{2} seat(s) while they are in it.")
				.format(frappe.bold(self.name), filled, flt(self.seats)))

	def _check_dates(self):
		if self.effective_from and self.effective_to and \
				str(self.effective_to) < str(self.effective_from):
			frappe.throw(_("The position ends before it starts."))

	# ── derived, never stored ────────────────────────────────────────────
	def _current_assignments(self):
		# `is not set`, not `in ("", None)`: an empty Date is stored as NULL, and
		# Frappe's query builder does not turn an `in` list containing None into
		# `IS NULL`. That filter silently matched nothing, so every seat looked
		# empty however many people were in it - and every vacancy was wrong.
		return frappe.get_all(
			"Alvoraa Position Assignment",
			filters={"position": self.name, "to_date": ("is", "not set")},
			fields=["employee", "weight"])

	def filled_weight(self):
		"""How much of this position is occupied, in whole people.

		Two people at 50 each fill one seat, not two. Counted in weights for
		exactly that reason.
		"""
		return sum(flt(a.weight) for a in self._current_assignments()) / 100.0

	def vacancy(self):
		"""Seats minus the people in them.

		Worked out on read, never stored. A stored count drifts the first time
		somebody resigns on a Friday, and a chart that calls a filled seat empty
		is worse than no chart at all.
		"""
		if self.status != "Active":
			return 0.0
		return max(0.0, flt(self.seats) - self.filled_weight())
