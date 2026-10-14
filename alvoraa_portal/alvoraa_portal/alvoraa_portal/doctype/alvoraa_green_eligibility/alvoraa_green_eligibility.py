"""Who may earn a green mark, and between which dates.

Green eligibility is not a property of a person, it is a property of a person
AT A TIME. DTC widen it in festive seasons and narrow it afterwards, so a single
field on Employee answers the wrong question: it says what is true today, and
loses what was true in October.

That matters because of ATT-07. Re-running October in December must use
October's eligibility. With a single field it would use December's, and a
reprocess would silently invent or destroy green marks in a month that had
already been paid.

So this follows Frappe HR's own shape for an attribute that changes over time -
Shift Assignment, Salary Structure Assignment - a dated row per employee.

OVERLAPS ARE ALLOWED, AND THE LATEST START WINS. DTC keep a standing,
open-ended grant per employee and widen it for a festive season. Banning
overlaps would make granting Diwali three edits per person - end the standing
period, add the season, start a new standing period - for two hundred and
fifty people. "The most recent decision applies" is how anybody reads it, and
it is unambiguous because two grants cannot share a start date: the record is
named after the employee and that date.

Rows are created in bulk through Data Import for a festive window, or one at a
time for an individual. There is no tool screen, because Data Import already is
one.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

# Open-ended periods are stored with a NULL to_date. Comparing against a date
# far in the future keeps the overlap test one expression instead of four cases.
FOREVER = "9999-12-31"


class AlvoraaGreenEligibility(Document):
	def validate(self):
		self._check_dates()
		self._warn_if_it_shadows_another()

	def _check_dates(self):
		if self.to_date and getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(
				_("This period ends on {0} but starts on {1}.")
				.format(self.to_date, self.from_date))

		if not self.to_date and self.eligibility != "None":
			# Not refused - an open-ended grant is legitimate for permanent
			# staff. But a festive window left open is how a temporary rule
			# becomes a permanent cost, so it is said out loud at save.
			frappe.msgprint(
				_("This grant has no end date, so it runs until somebody ends it. "
				  "If it is for a season, set the last day now."),
				title=_("No end date"), indicator="orange", alert=True)

	def _warn_if_it_shadows_another(self):
		"""Not a refusal - a note, so nobody is surprised later.

		A grant starting later than an existing one takes precedence over it
		for the days they share. That is the intended behaviour for a festive
		window, and a mistake if somebody meant to replace the old row.
		"""
		mine_to = self.to_date or FOREVER
		for other in frappe.get_all(
				"Alvoraa Green Eligibility",
				filters={"employee": self.employee, "name": ("!=", self.name or "")},
				fields=["name", "from_date", "to_date", "eligibility"]):
			other_to = other.to_date or FOREVER
			overlaps = (getdate(self.from_date) <= getdate(other_to)
			            and getdate(other.from_date) <= getdate(mine_to))
			if not overlaps:
				continue
			if getdate(self.from_date) > getdate(other.from_date):
				frappe.msgprint(
					_("This overrides {0} ({1}) for the days they share, because it "
					  "starts later.")
					.format(frappe.bold(other.name), other.eligibility),
					indicator="blue", alert=True)
			elif getdate(self.from_date) < getdate(other.from_date):
				frappe.msgprint(
					_("{0} ({1}) starts later than this one, so it will win on the "
					  "days they share.")
					.format(frappe.bold(other.name), other.eligibility),
					indicator="orange", alert=True)


def eligibility_on(employee, date, fallback=""):
	"""What this employee could earn on this date.

	Used by the engine one day at a time only where a period has not been
	preloaded; the payroll run loads the whole window once instead.

	Falls back to whatever the caller passes - in practice the old Employee
	field - so a tenant that has not created any dated rows yet keeps working
	exactly as it did.
	"""
	row = frappe.db.sql("""
		SELECT eligibility FROM `tabAlvoraa Green Eligibility`
		WHERE employee = %s AND from_date <= %s
		  AND (to_date IS NULL OR to_date >= %s)
		ORDER BY from_date DESC LIMIT 1""", (employee, date, date))
	return row[0][0] if row else fallback


@frappe.whitelist()
def grant_window(employees, from_date, to_date, eligibility, reason=None):
	"""Give the same window to many employees at once.

	A festive season is "most of the permanent employees", which is two hundred
	rows nobody will create by hand. Data Import can do it from a spreadsheet;
	this does it from a list.

	An employee who already has a grant starting on the SAME DAY is skipped and
	named - that would be a straight rewrite of an existing decision. An
	earlier standing grant is left alone and simply overridden for the season,
	which is the point.
	"""
	frappe.has_permission("Alvoraa Green Eligibility", "create", throw=True)
	if isinstance(employees, str):
		import json
		employees = json.loads(employees)

	created, skipped = [], []
	for employee in employees:
		doc = frappe.get_doc({
			"doctype": "Alvoraa Green Eligibility",
			"employee": employee,
			"from_date": from_date,
			"to_date": to_date or None,
			"eligibility": eligibility,
			"reason": reason,
		})
		try:
			doc.insert()
			created.append(doc.name)
		except frappe.ValidationError as e:
			skipped.append({"employee": employee, "why": str(e)})

	frappe.db.commit()
	return {"created": len(created), "skipped": skipped}
