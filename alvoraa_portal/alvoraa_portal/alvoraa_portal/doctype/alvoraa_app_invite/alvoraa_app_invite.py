# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""One joining code: who it was made for, how long it works, and what became of it.

The code itself is never in this table. HR sees it once, drawn as a QR in their
browser; the row keeps only its SHA-256 hash while the code is waiting, and moves
that hash aside the moment the code is used, cancelled or runs out - so a dead
code can still be recognised and told "already used at 9:01" instead of "not
recognised", but a leaked table never holds a live hash for a dead code.

The rules live here and not on a form because there is no form: nobody makes,
edits or deletes one of these by hand. Every row is written by server code -
HR's "make a code", the phone's check / "this is not me" / join, the leaver hook
and the daily clean-up - and the same rules hold whichever door a person tries:
desk, list bulk edit, Data Import, `frappe.client.set_value` or the REST API,
because all of them end up in `validate`.

  * Only the server inserts a row, and every row starts Waiting.
  * `employee`, `lifetime_hours` and `expires_at` never change.
  * Only the server moves the status, and only out of Waiting. Used, Cancelled
    and Ran out are final.
  * Leaving Waiting retires the hash in the same save.
  * Only the server deletes a row (the retention job, step 6).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now

# The same flag the phone record uses. Set on the document before saving when
# SERVER code is the author.
SERVER_FLAG = "alvoraa_server_write"

WAITING = "Waiting"
FINAL = ("Used", "Cancelled", "Ran out")

FROZEN_AFTER_INSERT = ("employee", "lifetime_hours", "expires_at")

CANCEL_REASONS = ("By HR", "This is not me (on a phone)", "Newer code made", "Employee left")


class AlvoraaAppInvite(Document):
	def validate(self):
		if self.is_new():
			self._only_the_server_writes_these()
			if self.status != WAITING:
				frappe.throw(_("A new code always starts as Waiting."), frappe.ValidationError)
			return

		before = self.get_doc_before_save()
		if before is None:
			# Frappe could not read the row it is about to overwrite. Fail closed.
			frappe.throw(_("This code record could not be checked. Please try again."),
			             frappe.ValidationError)

		for field in FROZEN_AFTER_INSERT:
			if self._changed(before, field):
				frappe.throw(
					_("{0} cannot be changed once a code is made.").format(
						_(self.meta.get_label(field))),
					frappe.ValidationError)

		if self._changed(before, "token_hash") or self._changed(before, "retired_token_hash"):
			if not self._by_the_server():
				frappe.throw(_("A code's hash cannot be changed by hand."), frappe.PermissionError)

		if before.status != self.status:
			self._only_the_server_writes_these()
			if before.status in FINAL:
				frappe.throw(_("A code that is {0} cannot change again. Make a new code.").format(
					_(before.status)), frappe.ValidationError)
			if self.status == "Cancelled" and self.cancel_reason not in CANCEL_REASONS:
				frappe.throw(_("A cancelled code has to say how it was cancelled."),
				             frappe.ValidationError)
		elif not self._by_the_server():
			# Nothing a person may change on one of these. The fields are all
			# read-only on the form; this holds for the doors that have no form.
			frappe.throw(_("A code record is written by the server, not by hand."),
			             frappe.PermissionError)

	def before_save(self):
		if self.status != WAITING and self.token_hash:
			# OPS-52: no live hash on a dead code. Kept aside so the code can still
			# be recognised (the same shape as the phone's retired_token_hash).
			self.retired_token_hash = self.token_hash
			self.token_hash = None
		if self.status == "Cancelled" and not self.cancelled_at:
			self.cancelled_at = now()

	def on_trash(self):
		if self._by_the_server():
			return
		frappe.throw(
			_("A code record cannot be deleted. It is the record of who let a phone in."),
			frappe.PermissionError)

	# ── pieces ───────────────────────────────────────────────────────────────

	def _by_the_server(self):
		return bool(self.flags.get(SERVER_FLAG))

	def _only_the_server_writes_these(self):
		if self._by_the_server():
			return
		frappe.throw(
			_("A code is made from the employee's record with \"Invite to the app\", "
			  "not by hand."),
			frappe.PermissionError)

	def _changed(self, before, field):
		# As text, for the reason written in the phone record's controller: the
		# form sends a Datetime back as a string while the row holds a datetime.
		return str(self.get(field) or "") != str(before.get(field) or "")


# ── helpers server code shares ───────────────────────────────────────────────
#
# Here rather than in field_app_join.py because the leaver hook in
# field_checkin.py needs one of them, and field_app_join imports field_checkin.

INVITE = "Alvoraa App Invite"


def cancel_invite(name, reason, cancelled_by=None):
	"""Cancel one code through the document, so every rule above runs.

	`cancelled_by` is the HR user for a desk cancel, and None for a phone, the
	leaver hook or the system - an empty field is the honest answer there.
	"""
	doc = frappe.get_doc(INVITE, name)
	if doc.status != WAITING:
		return doc
	doc.status = "Cancelled"
	doc.cancel_reason = reason
	doc.cancelled_by = cancelled_by
	doc.cancelled_at = now()
	doc.flags[SERVER_FLAG] = True
	doc.save(ignore_permissions=True)
	return doc
