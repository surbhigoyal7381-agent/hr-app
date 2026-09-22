# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""One day's numbers for the field attendance app (slice 013, US-22).

Counts only. The row says how many codes were made and used, how many punches
were saved and refused, how many phones started the app - never who. There is
no name, no employee ID, no phone model, no code and no secret in any field,
and a test reads every row it writes to prove it (AC-131).

Written by the daily clean-up job (`field_app_housekeeping.daily`) and by
nothing else. HR reads it. Nobody creates, edits or deletes one by hand: the
doctype gives no role create, write or delete, and the rules below hold for the
doors that have no form. Rows older than 13 months are removed by the same job
(AC-134).
"""

import frappe
from frappe import _
from frappe.model.document import Document

# The same flag the phone, code and acknowledgement records use: set on the
# document before saving when SERVER code is the author.
SERVER_FLAG = "alvoraa_server_write"

DAILY_COUNT = "Alvoraa Field App Daily Count"


class AlvoraaFieldAppDailyCount(Document):
	def validate(self):
		if not self.flags.get(SERVER_FLAG):
			frappe.throw(
				_("The daily counts are written by the clean-up job, not by hand."),
				frappe.PermissionError)

	def on_trash(self):
		if self.flags.get(SERVER_FLAG):
			return
		frappe.throw(
			_("The daily counts are removed by the clean-up job after 13 months, not by hand."),
			frappe.PermissionError)
