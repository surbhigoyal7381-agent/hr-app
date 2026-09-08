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
from frappe.utils import flt, nowdate
from frappe.utils.nestedset import NestedSet

from hrms.alvoraa_org_structure import settings


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
	def _current_assignments(self, on=None):
		"""Who is in this seat now - including anybody whose cover ends later.

		"Current" means NOT YET ENDED, not "never ends". Filtering on an empty
		end date alone excluded every temporary assignment, because cover always
		has one - so an acting store in-charge filled nothing and the seat they
		were covering read as completely vacant.

		`is not set` rather than `in ("", None)` for the empty case: an empty Date
		is NULL, and Frappe's query builder will not turn an `in` list containing
		None into `IS NULL`. That one matched nothing at all.
		"""
		on = on or nowdate()
		rows = frappe.get_all(
			"Alvoraa Position Assignment",
			filters={"position": self.name, "from_date": ("<=", on)},
			fields=["employee", "weight", "to_date", "assignment_type"])
		return [r for r in rows if not r.to_date or str(r.to_date) >= str(on)]

	def filled_weight(self):
		"""How much of this position is occupied, in whole people.

		Two people at 50 each fill one seat, not two. Counted in weights for
		exactly that reason.
		"""
		return sum(flt(a.weight) for a in self._current_assignments()) / 100.0

	def vacancy(self, for_recruitment=False):
		"""Seats minus the people in them.

		Worked out on read, never stored. A stored count drifts the first time
		somebody resigns on a Friday, and a chart that calls a filled seat empty
		is worse than no chart at all.

		`for_recruitment` is the number that should drive hiring, and it is
		deliberately different. Once somebody is covering a seat the urgency
		drops, the requisition quietly stalls, and a three-month gap becomes a
		year - so by default a covered seat still counts as fully open to
		recruitment even though the chart shows it partly filled.

		Whether that holds is the organisation's setting, because a company that
		is happy for an acting manager to run a store for two quarters should not
		be nagged about it.
		"""
		if self.status != "Active":
			return 0.0
		if for_recruitment and settings.get("alvoraa_cover_vacancy_stays_open"):
			# Cover does not count towards filling it. Permanent does.
			permanent = sum(flt(a.weight) for a in self._current_assignments()
			                if (a.assignment_type or "Permanent") == "Permanent") / 100.0
			return max(0.0, flt(self.seats) - permanent)
		return max(0.0, flt(self.seats) - self.filled_weight())
