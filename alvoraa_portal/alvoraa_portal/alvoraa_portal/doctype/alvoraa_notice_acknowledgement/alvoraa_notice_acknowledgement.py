# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""One line of history: this person read this version of the notice, then, there.

Insert-only. A row is never edited and never deleted by a person, because the
whole point of it is to answer, a year later, "which words did Suresh read on
which phone, and when" - and a history that can be rewritten answers nothing.
Each new reading is a NEW row (PRIV-3): reading version 2 leaves the version-1
row exactly as it was.

Only server code writes one - the app's join and "read it again" calls, the web
check-in page's registration, and a backfill. Only server code (the retention
job, step 6) deletes one. Nobody has create, write or delete on the doctype, and
these rules hold for the doors that have no form.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now

# The same flag the phone record and the code record use.
SERVER_FLAG = "alvoraa_server_write"

ACKNOWLEDGEMENT = "Alvoraa Notice Acknowledgement"

CHANNELS = ("App", "Web check-in page", "Backfill")


class AlvoraaNoticeAcknowledgement(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw(
				_("A notice acknowledgement is a record of what happened. It cannot be "
				  "changed."),
				frappe.PermissionError)
		if not self.flags.get(SERVER_FLAG):
			frappe.throw(
				_("A notice acknowledgement is written when somebody reads the notice, "
				  "not by hand."),
				frappe.PermissionError)
		if self.channel not in CHANNELS:
			frappe.throw(_("Unknown channel."), frappe.ValidationError)

	def on_trash(self):
		if self.flags.get(SERVER_FLAG):
			return
		frappe.throw(
			_("A notice acknowledgement cannot be deleted. It is the record of what "
			  "the employee was told."),
			frappe.PermissionError)


def record_acknowledgement(employee, version, channel, device=None, language="en",
                           app_version=None):
	"""Write one row, as the server. Returns the new document."""
	doc = frappe.get_doc({
		"doctype": ACKNOWLEDGEMENT,
		"employee": employee,
		"device": device,
		"notice_version": version,
		"acknowledged_at": now(),
		"language": language,
		"channel": channel,
		"app_version": (app_version or "")[:20] or None,
	})
	doc.flags[SERVER_FLAG] = True
	doc.insert(ignore_permissions=True)
	return doc


def latest_version_for(device):
	"""The notice version this phone last acknowledged, or None."""
	rows = frappe.get_all(
		ACKNOWLEDGEMENT,
		filters={"device": device},
		fields=["notice_version"],
		order_by="acknowledged_at desc, creation desc",
		limit=1,
	)
	return rows[0].notice_version if rows else None
