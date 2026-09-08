"""Who sits in a seat, and how much of them.

A head of operations who also runs quality. A founder still holding finance. In
a company of a hundred this is not an edge case, it is most of the senior team.

Forbidding it was the wrong answer, because the situation is true whether the
software admits it or not - and a chart that cannot show it is a chart people
stop trusting. Weights let it be shown without headcount lying: Operations 70,
Quality 30, and the company still totals what it totals.

**The number is a WEIGHT, not time.** "Time allocation" sounds like a claim
about hours, and the moment it does, somebody wants it reconciled against a
timesheet and somebody else argues they spent forty per cent on Quality last
week. Nobody has that data and nobody should be asked to defend it. A weight is
a management judgement about where a person mostly sits. It divides headcount
and it divides cost. It is not a timesheet and must never be presented as one.

This deliberately does NOT touch `Employee.reports_to`. That field routes
performance reviews - `pms_cycle.py` sets each review's primary_manager from it -
so deriving it from the position hierarchy would reassign live appraisals as a
side effect of somebody tidying an org chart, and nobody would connect the two.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

# A three-way split is 34/33/33, so exact equality would refuse a perfectly
# sensible arrangement. One hundredth of a person is the tolerance; letting 99.5
# pass as "about right" is how a headcount total quietly stops adding up.
TOLERANCE = 0.01


class AlvoraaPositionAssignment(Document):
	def validate(self):
		self._check_weight()
		self._check_dates()
		self._check_not_before_they_join()
		self._check_position_is_open()
		self._check_cover_is_temporary()
		self._check_person_adds_up()
		self._check_one_primary()

	def on_update(self):
		self._check_position_not_overfilled()

	# ── rules ────────────────────────────────────────────────────────────
	def _check_weight(self):
		if flt(self.weight) <= 0:
			frappe.throw(_("A weight of zero means they are not in this position. "
			               "Remove the row instead, or set an end date."))
		if flt(self.weight) > 100:
			frappe.throw(_("A weight cannot be more than 100 - a person is one person."))

	@property
	def is_cover(self):
		"""Acting, Interim and Additional Charge are cover carried ON TOP of the
		person's own job. Permanent is the job itself."""
		return self.assignment_type and self.assignment_type != "Permanent"

	def _check_dates(self):
		if self.from_date and self.to_date and str(self.to_date) < str(self.from_date):
			frappe.throw(_("This assignment ends before it starts."))

	def _check_not_before_they_join(self):
		"""A new joiner is put in a seat weeks before they arrive - the seat is
		created, the offer is signed, the chart is planned. They must not appear
		as though they are in it until the day they actually start.

		Enforced against the Employee's own joining date rather than trusted from
		the form, because the form is where somebody types the planned date and
		then the start slips a fortnight.
		"""
		joins = frappe.db.get_value("Employee", self.employee, "date_of_joining")
		if joins and self.from_date and str(self.from_date) < str(joins):
			frappe.throw(
				_("{0} joins on {1}. An assignment cannot start before that - "
				  "they would show in the seat on a day they do not work here.")
				.format(frappe.bold(self.employee_name or self.employee), joins))

	def _check_cover_is_temporary(self):
		"""Cover that never ends is not cover. Warned, not refused: an interim
		arrangement genuinely can be open-ended while a search runs, and refusing
		it would send somebody to record it as permanent, which is worse."""
		if self.is_cover and not self.to_date:
			frappe.msgprint(
				_("{0} cover with no end date. If it is not temporary, it is a "
				  "permanent assignment - and if it is, say when it ends.")
				.format(self.assignment_type),
				indicator="orange", alert=True)

	def _check_position_is_open(self):
		status = frappe.db.get_value("Alvoraa Position", self.position, "status")
		if status == "Closed" and not self.to_date:
			frappe.throw(
				_("{0} is closed. Reopen it, or pick another position.")
				.format(frappe.bold(self.position)))

	def _current_rows_for_person(self):
		rows = frappe.get_all(
			"Alvoraa Position Assignment",
			filters={"employee": self.employee, "name": ("!=", self.name or ""),
			         "to_date": ("is", "not set")},
			fields=["name", "position", "weight", "is_primary", "assignment_type"])
		for r in rows:
			r["is_cover"] = bool(r.assignment_type and r.assignment_type != "Permanent")
		return rows

	def _check_person_adds_up(self):
		"""A person's PERMANENT weights total 100. Cover is counted separately.

		The distinction matters and it is not bookkeeping. A store in-charge who
		covers a second store still does their own job in full - the cover is
		extra duty, not a reallocation. Squeezing it into the same 100 would
		force somebody to pretend they had reduced their real role, and the
		chart would then understate what the first store actually has.

		So cover is allowed to push the total past 100, and the person is FLAGGED
		rather than refused. Somebody carrying 130% is a real risk worth seeing,
		not a data-entry error worth blocking.
		"""
		if self.to_date:
			return                      # a closed assignment is history, not a claim
		rows = self._current_rows_for_person()
		permanent = sum(flt(r.weight) for r in rows if not r.get("is_cover"))
		cover = sum(flt(r.weight) for r in rows if r.get("is_cover"))

		if not self.is_cover:
			total = flt(self.weight) + permanent
			if total > 100 + TOLERANCE:
				held = ", ".join(f"{r.position} {flt(r.weight):g}%"
				                 for r in rows if not r.get("is_cover"))
				frappe.throw(
					_("{0} would be at {1}% of their own job. A person is one "
					  "person. Already holding: {2}. If this is temporary cover, "
					  "set the type instead.")
					.format(frappe.bold(self.employee_name or self.employee),
					        f"{total:g}", held or _("nothing else")),
					title=_("Weights add up to more than one person"))
			return

		load = flt(self.weight) + permanent + cover
		if load > 100 + TOLERANCE:
			frappe.msgprint(
				_("{0} will be carrying {1}% once this cover starts - their own "
				  "role plus what they are standing in for. That is allowed, and "
				  "worth knowing.")
				.format(frappe.bold(self.employee_name or self.employee), f"{load:g}"),
				indicator="orange", alert=True)

	def _check_one_primary(self):
		"""Exactly one primary per person - it decides where they appear by
		default and which line the rest of the product follows.

		Cover is never primary. Somebody standing in for a fortnight should not
		become the person whose appraisal and approvals route through the seat
		they are covering.
		"""
		# Cover first. Checking `to_date` before this skipped the rule for every
		# temporary assignment - and temporary assignments are the only ones that
		# have a to_date, so the rule never ran at all.
		if self.is_cover:
			self.is_primary = 0
			return
		if self.to_date:
			return
		others = [r for r in self._current_rows_for_person() if not r.get("is_cover")]
		if not others:
			self.is_primary = 1         # their only position is the primary one
			return
		if self.is_primary:
			for row in others:
				if row.is_primary:
					frappe.db.set_value("Alvoraa Position Assignment", row.name,
					                    "is_primary", 0, update_modified=False)
		elif not any(r.is_primary for r in others):
			frappe.throw(_("Somebody has to be primary. Mark one of this person's "
			               "positions as their main one."))

	def _check_position_not_overfilled(self):
		pos = frappe.get_doc("Alvoraa Position", self.position)
		if flt(pos.seats) and pos.filled_weight() > flt(pos.seats) + TOLERANCE:
			frappe.throw(
				_("{0} has {1} seat(s) and would be filled {2} times over.")
				.format(frappe.bold(self.position), flt(pos.seats),
				        round(pos.filled_weight(), 2)),
				title=_("Position is over-filled"))
