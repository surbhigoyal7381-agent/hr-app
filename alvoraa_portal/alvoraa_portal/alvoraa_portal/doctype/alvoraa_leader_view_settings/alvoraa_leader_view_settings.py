"""The leader view's privacy rule: the smallest group whose figures are shared (SEC-10).

Rules live in this controller, so the portal, the desk, REST and data import all
obey them:

- only a System Manager saves (the DocType permission says so too);
- the number is a whole number from 3 to 10;
- a change needs a reason in the same save, and the reason is cleared after the
  change history row is written, so an old reason is never recorded again;
- a save that does not change the number is refused.

Push 1 of slice 012 uses the number for the doubtful-day check and stores the
"last checked" stamp here. The portal screen for changing it comes in push 2.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

DOCTYPE = "Alvoraa Leader View Settings"
LOWEST, HIGHEST, DEFAULT = 3, 10, 5


class AlvoraaLeaderViewSettings(Document):
	def validate(self):
		if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
			from hrms.alvoraa_hr_core.access import refuse

			refuse(_("Only a System Manager can change the leader view privacy rule."),
			       "SEC-10", "Alvoraa Leader View Settings save", DOCTYPE, DOCTYPE)

		# Frappe has already turned the Int field into a whole number; text reads as 0.
		self.min_group_size = cint(self.min_group_size)
		if not LOWEST <= self.min_group_size <= HIGHEST:
			frappe.throw(_("Choose a number from 3 to 10."))

		before = self.get_doc_before_save()
		saved = cint(before.min_group_size) if before else None
		if saved == self.min_group_size:
			frappe.throw(_("Choose a different number first. The saved value is already {0}.")
			             .format(saved))
		if not (self.change_reason or "").strip():
			frappe.throw(_("Add a short reason. It is kept with the change."))

	def on_change(self):
		# Runs after the change history row is written, so the reason is recorded
		# with this change and then gone before the next one.
		if self.change_reason:
			frappe.db.set_single_value(DOCTYPE, "change_reason", None, update_modified=False)


def min_group_size():
	"""The stored minimum. Anything missing or outside 3-10 reads as 10, the strictest.

	A value set from a console can be anything. A support ticket costs less than
	sharing a small group's figures (Q7).
	"""
	raw = frappe.db.get_single_value(DOCTYPE, "min_group_size", cache=False)
	value = cint(raw) if str(raw if raw is not None else "").strip().lstrip("-").isdigit() else None
	if value is None or not LOWEST <= value <= HIGHEST:
		frappe.log_error(title="Leader view minimum group is not usable",
		                 message="The stored value is missing or outside 3 to 10, so 10 is used.")
		return HIGHEST
	return value


def ensure_default():
	"""Store 5 on a site that has never had a value. Never overwrites a stored one.

	Written straight to the settings row: this is the set-up, not a change a
	person made, and a broken stored value must stay visible (it reads as 10).
	"""
	stored = frappe.db.sql("select 1 from `tabSingles` where doctype=%s and field=%s",
	                       (DOCTYPE, "min_group_size"))
	if not stored:
		frappe.db.set_single_value(DOCTYPE, "min_group_size", DEFAULT, update_modified=False)
