# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""The review HR records to clear a "Grooming review pending" flag (D5, D6).

Its own record, because nothing else in the product is private enough: a
manager note is an Info comment the desk shows to anyone who can open the
Employee, the subject included (slice 066, strategy bad news 1).

  - HR in scope reads it, and nobody else - not the subject, not the manager,
    not a System Manager without an HR role (its own permission hooks).
  - Insert-only. Nobody has write or delete, so it cannot be changed after it
    is saved; `track_changes` is off so no Version row ever holds the text.
  - Everybody else who sees the flag gets only "Action agreed on {date}",
    read from `creation` - the note is never selected on that path.

Saving it changes no mark and no fine.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_first_day, get_last_day, getdate

from hrms.alvoraa_hr_core.access import is_own_record, refuse
import alvoraa_portal.grooming as grooming


class GroomingReview(Document):
	def validate(self):
		where = "Grooming Review save"
		if not self.is_new():
			refuse(_("A grooming review cannot be changed after it is saved."), "D5", where,
			       self.doctype, self.name)
		if is_own_record(self.employee) or self.employee not in grooming.hr_scope(
				frappe.session.user, [self.employee]):
			refuse(_("Only HR can record a grooming review."), "D5", where, self.doctype, self.name)
		self.review_note = (self.review_note or "").strip()
		if not self.review_note:
			frappe.throw(_("Write what you talked about and the action plan first."))
		self.review_month = getdate(get_first_day(getdate(self.review_month)))
		flag = grooming.flag_for(self.employee, self.review_month, grooming._rate_now(self.employee),
		                         grooming._base(self.employee, get_last_day(self.review_month)))
		if not flag or flag.state != "pending":
			name = frappe.db.get_value("Employee", self.employee, "first_name") or self.employee
			frappe.throw(_("There is no grooming review pending for {0}.").format(name))
