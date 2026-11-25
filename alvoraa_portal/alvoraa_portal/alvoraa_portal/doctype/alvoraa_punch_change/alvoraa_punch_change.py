# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""The record of one manual punch change (slice 088c).

Append-only, for the same reason the change notice is: it is the evidence behind what the
employee was told. It is created only by `alvoraa_portal.punch_change.write_log`, under the
module's flag, never by a client and never by hand in the Desk. Nobody edits it and nobody
deletes it, including Administrator. Retention is a separate, dated ticket (5 years maximum,
Surbhi, 25 Nov 2026); nothing here deletes."""

import frappe
from frappe import _
from frappe.model.document import Document

import hrms.alvoraa_hr_core.access as access

#: Set by `punch_change.write_log` around its own insert. A browser cannot send a flag.
FLAG = "in_punch_change"


class AlvoraaPunchChange(Document):
	def validate(self):
		if frappe.flags.get(FLAG) or frappe.flags.in_install or frappe.flags.in_migrate:
			return
		access.refuse(_("A punch change record is written by the system when a punch is changed. "
		                "It cannot be created or edited by hand."),
		              "088c-SEC-1", "Alvoraa Punch Change validate", self.doctype, self.name)

	def on_trash(self):
		if frappe.flags.in_install or frappe.flags.in_migrate:
			return
		access.refuse(_("A punch change record is evidence of what the employee was told, so it "
		                "cannot be deleted."),
		              "088c-SEC-1", "Alvoraa Punch Change on_trash", self.doctype, self.name)
