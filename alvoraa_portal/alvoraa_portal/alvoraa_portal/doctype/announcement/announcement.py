# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""A notice a Notice Sender sent or scheduled (slice 076, Part B).

Made only by `announcements.create_notice`, which checks the role, the scope,
the limits and the time. A record posted straight to the REST API would skip
all of that, so `before_insert` refuses anything that did not come through it.

After that, the sender may change one thing: Scheduled to Cancelled. Text,
audience and time are fixed - changing them means cancel and send a new one
(spec section 6). The send job moves the status on with `db_set`, which does
not come through here. Track Changes keeps a Version row for every save, so a
cancel says who and when (PRIV-3).
"""

import frappe
from frappe import _
from frappe.model.document import Document

# Set only for the length of one create_notice call, on this request.
CREATE_FLAG = "alvoraa_create_notice"


class Announcement(Document):
	def before_insert(self):
		if not frappe.flags.get(CREATE_FLAG):
			frappe.throw(_("Send a notice from Home, under Notices."), frappe.PermissionError)

	def validate(self):
		self.message = (self.message or "").strip()
		if not self.message:
			frappe.throw(_("Write a message first."))
		if len(self.message) > 300:
			frappe.throw(_("A notice can be at most 300 characters."))
		if self.is_new():
			return
		before = self.get_doc_before_save()
		changed = [df.fieldname for df in self.meta.fields
		           if df.fieldname != "status" and self.get(df.fieldname) != before.get(df.fieldname)]
		if changed:
			frappe.throw(_("A notice cannot be changed. Cancel it and send a new one."))
		if self.status != before.status and not (before.status == "Scheduled" and self.status == "Cancelled"):
			frappe.throw(_("Only a scheduled notice can be cancelled."))
