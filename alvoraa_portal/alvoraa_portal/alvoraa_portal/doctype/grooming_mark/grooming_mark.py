# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""One grooming red: this person, this day, this reason, marked by this person.

Every door - the portal, the desk, REST, an import - comes through here, so the
rules live here and in `alvoraa_portal.grooming` and nowhere else.

  made        validate runs `may_mark` (SEC-1, SEC-3, SEC-6, SEC-7, SEC-10, R13);
              `marked_as` is set from it and anything sent is ignored
  asked       the subject sets `asked_on`, once
  kept        HR in scope sets `kept_by` and `kept_on` after an ask
  removed     a cancel, never a delete (PRIV-3): the marker's own same-day
              undo, or HR in scope with a fixed reason

A submitted slip that covers the day closes all of it (SEC-9). Nothing here
uses ignore_permissions.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate

from hrms.alvoraa_hr_core.access import is_own_record, refuse
import alvoraa_portal.grooming as grooming

AFTER_SUBMIT = ("asked_on", "kept_by", "kept_on", "removal_reason", "raised_on", "raised_by",
                "raised_reason")


class GroomingMark(Document):
	def validate(self):
		# Two markers at the same moment (the manager today, HR on a past day)
		# would both count 2 live marks and both pass the 3-mark stop. Locking
		# the person's Employee row makes the second wait; may_mark(locking=True)
		# then counts the marks with a locking read, which sees the first one's
		# committed mark (security M1 and its second look: a plain read used the
		# transaction's older snapshot and let a 4th through).
		frappe.db.get_value("Employee", self.employee, "name", for_update=True)
		if self.reason not in grooming.REASONS:
			refuse(_("Choose one of the reasons on the list."), "SEC-11", "Grooming Mark save",
			       self.doctype, self.name)
		# "Other" carries a short typed reason; every fixed reason carries none.
		self.other_reason = (grooming.clean_other(self.other_reason)
		                     if self.reason == grooming.OTHER else None)
		verdict = grooming.may_mark(self.employee, self.mark_date,
		                            told_in_person=self.told_in_person or 0, exclude=self.name,
		                            locking=True)
		if not verdict.ok:
			refuse(verdict.message, verdict.code, "Grooming Mark save", self.doctype, self.name)
		self.marked_as = verdict.capacity
		# A new mark carries none of the after-submit facts, whatever was sent.
		for field in AFTER_SUBMIT:
			self.set(field, None)

	def on_submit(self):
		raised = grooming.raised_by(self)
		grooming.notify_marked(self, raised)
		if raised:
			grooming.notify_flag(self, raised)

	def before_update_after_submit(self):
		old = self.get_doc_before_save()
		changed = {f for f in AFTER_SUBMIT if (old.get(f) or None) != (self.get(f) or None)}
		where = "Grooming Mark update"
		if not changed:
			# An empty save has no purpose here, and Frappe's REST save returns the
			# whole record and stamps modified_by (security verification B1).
			refuse(_("Nothing on this grooming red can be changed that way."), "SEC-4", where,
			       self.doctype, self.name)
		if "removal_reason" in changed:
			refuse(_("A grooming red's removal reason is set only when it is removed."),
			       "SEC-5", where, self.doctype, self.name)
		self._refuse_if_closed(where)
		if changed == {"asked_on"}:
			if not is_own_record(self.employee):
				refuse(_("Only the person who was marked can ask HR to look at it."),
				       "US-8", where, self.doctype, self.name)
			if old.asked_on:
				refuse(_("You have already asked HR to look at this."), "US-8", where,
				       self.doctype, self.name)
			self.asked_on = now_datetime()
			self._action_taken = "asked"
			return
		if changed <= {"kept_by", "kept_on"}:
			if is_own_record(self.employee) or self.employee not in grooming.hr_scope(
					frappe.session.user, [self.employee]):
				refuse(_("Only HR can keep a grooming red after the person asked."), "US-8", where,
				       self.doctype, self.name)
			if not old.asked_on or old.kept_on:
				refuse(_("There is no question from the person waiting on this grooming red."),
				       "US-8", where, self.doctype, self.name)
			self.kept_by = frappe.session.user
			self.kept_on = now_datetime()
			self._action_taken = "kept"
			return
		if changed <= set(grooming.RAISE_FIELDS):
			if not self.flags.get(grooming.RAISE_FLAG):
				refuse(_("Use \u201cRaise it with HR\u201d to raise this."), "RAISE5", where,
				       self.doctype, self.name)
			# "Raise it with HR": the subject's current manager, on the mark that
			# reached this month's limit, once a month, one fixed reason. It adds
			# no fine and changes nothing else on the mark.
			v = grooming.may_raise(self.employee)
			if not v.ok or v.mark != self.name:
				refuse(v.message or _("This grooming red is not the one to raise."), v.code or "RAISE4",
				       where, self.doctype, self.name)
			if self.raised_reason not in grooming.RAISE_REASONS:
				frappe.throw(_("Choose a reason first."))
			self.raised_by = frappe.session.user
			self.raised_on = now_datetime()
			self._action_taken = "raised"
			return
		refuse(_("That change is not allowed on a grooming red."), "SEC-5", where,
		       self.doctype, self.name)

	def on_update_after_submit(self):
		action = getattr(self, "_action_taken", None)
		if action == "asked":
			grooming.notify_asked(self)
		elif action == "kept":
			grooming.notify_kept(self)
		elif action == "raised":
			grooming.notify_raised(self)

	def before_cancel(self):
		"""SEC-5: the marker's own same-day undo, or HR in scope until the slip."""
		where = "Grooming Mark cancel"
		user = frappe.session.user
		if is_own_record(self.employee):
			refuse(_("You cannot remove a grooming red on yourself."), "SEC-5", where,
			       self.doctype, self.name)
		self._refuse_if_closed(where)
		if (self.owner == user and self.marked_as == "Manager"
				and getdate(self.mark_date) == getdate(nowdate())):
			self.removal_reason = grooming.UNDO_REASON
			return
		if self.employee not in grooming.hr_scope(user, [self.employee]):
			refuse(_("Only HR can remove this grooming red."), "SEC-5", where,
			       self.doctype, self.name)
		if self.removal_reason not in grooming.REMOVAL_REASONS:
			refuse(_("Choose why you are removing it."), "PRIV-3", where, self.doctype, self.name)

	def on_cancel(self):
		grooming.notify_removed(self)

	def _refuse_if_closed(self, where):
		slip = frappe.get_all("Salary Slip", filters={
			"employee": self.employee, "docstatus": 1,
			"start_date": ("<=", self.mark_date), "end_date": (">=", self.mark_date)},
			fields=["start_date"], limit_page_length=1)
		if slip:
			month = grooming._month_name(slip[0].start_date)
			refuse(_("The pay slip for {0} is submitted, so grooming reds for {0} are closed. "
			         "They cannot be added or removed now.").format(month), "R11", where,
			       self.doctype, self.name)
