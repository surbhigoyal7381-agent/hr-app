# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""The record of one printed change notice (slice 088, spec section 7.1).

This controller exists to say no. The record is evidence: it says a page was released to
an HR person, which changed days were on it, and what the employee answered. Evidence
that anybody can type, retype or quietly delete is not evidence, so:

- it is created only by `register_notice.open_notices`, never by a client and never by
  hand in the Desk (SEC-5);
- it is never deleted, by any role, including System Manager;
- what was printed (`printed_by`, `printed_at`, `changes`) can never be edited;
- once the employee has answered - outcome Signed or Not right - the answer and its
  photos are closed too, so a second HR person cannot rewrite it.

The one door left open is 01c Q1, Surbhi's default: a System Manager may replace a
photo that came out unreadable. `track_changes` is on, so the Version record names them.
"""

import frappe
from frappe import _
from frappe.model.document import Document

import hrms.alvoraa_hr_core.access as access

#: Set by `register_notice.open_notices` and `register_notice.record` around their own
#: writes. A browser cannot send a flag, which is the whole point of using one.
FLAG = "in_register_notice"

#: Never editable, whatever the outcome: what was printed.
PRINT_OWNED = ("employee", "month", "printed_by", "printed_at", "page_count", "changes")

#: Editable only while the employee has not answered yet.
ANSWER_OWNED = ("outcome", "recorded_by", "recorded_on", "dispute_reason", "pages")

ANSWERED = ("Signed", "Not right")


def _under_the_module():
	return bool(frappe.flags.get(FLAG))


class AlvoraaRegisterNotice(Document):
	def validate(self):
		if _under_the_module() or frappe.flags.in_install or frappe.flags.in_migrate:
			return
		if self.is_new():
			access.refuse(_("A change notice is created by printing it, not by hand."),
			              "088-SEC-5", "Alvoraa Register Notice insert",
			              self.doctype, self.name)
		before = self.get_doc_before_save()
		if not before:
			return
		for field in PRINT_OWNED:
			if self._moved(before, field):
				access.refuse(_("What was printed cannot be changed. Print the notice again instead."),
				              "088-SEC-5", "Alvoraa Register Notice " + field,
				              self.doctype, self.name)
		if before.outcome in ANSWERED:
			for field in ANSWER_OWNED:
				if field == "pages" and "System Manager" in frappe.get_roles():
					# 01c Q1, Surbhi's default: an unreadable photo may be replaced.
					# track_changes records who did it.
					continue
				if self._moved(before, field):
					access.refuse(_("This notice has already been answered, so it cannot be changed."),
					              "088-SEC-5", "Alvoraa Register Notice " + field,
					              self.doctype, self.name)

	def _moved(self, before, field):
		meta = self.meta.get_field(field)
		if meta and meta.fieldtype == "Table":
			mine = [tuple(str(row.get(f) or "") for f in sorted(row.as_dict().keys())
			              if f not in ("name", "modified", "creation", "idx", "modified_by", "owner"))
			        for row in (self.get(field) or [])]
			theirs = [tuple(str(row.get(f) or "") for f in sorted(row.as_dict().keys())
			                if f not in ("name", "modified", "creation", "idx", "modified_by", "owner"))
			          for row in (before.get(field) or [])]
			return mine != theirs
		return str(self.get(field) or "") != str(before.get(field) or "")

	def on_trash(self):
		"""Nobody deletes a notice. Not HR, not a System Manager, not Administrator.

		This is deliberate and it is not symmetry with the rest of the app: the notice is
		what proves the employee was shown their changed days before pay was locked. If it
		can go, the proof can go. Retention is a separate question and still open with
		counsel (PRIV-4): nothing here decides it, and nothing here deletes."""
		if frappe.flags.in_install or frappe.flags.in_migrate:
			return
		access.refuse(_("A change notice is a record of what the employee was shown, so it "
		                "cannot be deleted."),
		              "088-SEC-5", "Alvoraa Register Notice on_trash", self.doctype, self.name)
