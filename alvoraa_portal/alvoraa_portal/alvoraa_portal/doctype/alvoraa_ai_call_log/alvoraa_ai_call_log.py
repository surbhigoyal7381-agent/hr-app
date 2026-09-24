# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""What the AI lead intake did with each email (slice 043, SEC-17).

Content-free on purpose: no subject, no body, no model answer, no key. The outcome,
a short reason, the model, the prompt version, the confidence and the token counts
are enough to audit a decision and to count cost. The `communication` field is
unique, which is what makes the sweep safe to run twice (OPS-4).

Written by the sweep and by nothing else: System Manager may read, nobody may
create, edit or delete one by hand.
"""

import frappe
from frappe import _
from frappe.model.document import Document

SERVER_FLAG = "alvoraa_server_write"


class AlvoraaAICallLog(Document):
	def validate(self):
		if not self.flags.get(SERVER_FLAG):
			frappe.throw(_("The AI call log is written by the lead intake, not by hand."),
				frappe.PermissionError)

	def on_trash(self):
		if self.flags.get(SERVER_FLAG):
			return
		frappe.throw(_("The AI call log is not deleted by hand."), frappe.PermissionError)
