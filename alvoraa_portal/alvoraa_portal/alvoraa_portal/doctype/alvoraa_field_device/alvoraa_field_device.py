# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""The record of one phone: who it belongs to, and whether it still works.

**Why the rules are here and not on the form.** A phone record decides whether a
punch is believed. If HR could point a record at somebody else, or switch a
blocked phone back on, then "who marked Suresh present on 3 March" has no honest
answer, and an attendance deduction cannot be defended in a grievance.

A form is only one of five doors into this table. The others are list bulk edit,
Data Import, `frappe.client.set_value` and the REST API. Every one of them ends
up in `validate`, so that is where the rules live - hiding a button would leave
four doors open.

The rules, in plain words:

  * Nobody creates a phone record by hand. One appears because the server made
    it: the web check-in page's registration, or an app join with HR's code.
  * A phone's employee never changes. Nor does its secret, its retired secret,
    how it joined, which code let it in, or when it was registered.
  * A person may move a phone Pending -> Active (web phones only), Pending ->
    Blocked or Active -> Blocked, and must say why for a block. Nothing else.
  * Replaced and Removed are set by server code, never by a person.
  * Blocked, Replaced and Removed are final. Getting the app back needs a new
    code. There is no unblock, for anybody, including a System Manager.
  * "Signed out" (ALV-128, 26 Sep 2026) is a password phone whose login's
    password changed. It is not a block: its secret is retired like a stopped
    phone's, and the only way out is "Replaced", when the person signs in again.
  * Whenever a phone stops or is signed out, its secret's hash moves into
    `retired_token_hash` in the same save. The old secret then gets its own refusal instead of a 200,
    and "why did this phone stop" is still answerable a year later.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now

# Set this flag on the document before saving when SERVER code is the author -
# registration, an app join, a replacement, the employee removing their own
# phone, the leaver hook. It is a flag on the document and not a role, because
# the server acts as whoever is logged in and a role check would let a person
# with that role do the same thing by hand.
SERVER_FLAG = "alvoraa_server_write"

# How a phone arrived. The two APP ways are the ones the organisation's app
# settings govern; a web check-in page phone is not touched by them (ALV-128
# added the second app way: email and password, for anyone with a login).
JOIN_WEB = "Web check-in page"
JOIN_QR = "App QR code"
JOIN_PASSWORD = "App password sign-in"
APP_JOIN_METHODS = (JOIN_QR, JOIN_PASSWORD)

# States a person may put a phone into, from the state it is in now.
ALLOWED_BY_A_PERSON = {
	("Pending", "Active"),
	("Pending", "Blocked"),
	("Active", "Blocked"),
}

# Once a phone is in one of these it never comes out. Not by HR, not by a
# System Manager, not by an import.
FINAL = ("Blocked", "Replaced", "Removed")

# A password phone whose login's password changed (ALV-128). Not final - a new
# sign-in on any phone moves it to Replaced - but it holds no live secret.
SIGNED_OUT = "Signed out"

# Every state in which the phone holds no live secret.
NO_LIVE_SECRET = (*FINAL, SIGNED_OUT)

# Only the server puts a phone into these.
SERVER_ONLY = ("Replaced", "Removed", "Consent not given", SIGNED_OUT)

# Never editable after the record exists. The two hash fields are the exception
# the server needs when it retires a secret, and only then.
FROZEN_AFTER_INSERT = (
	"employee", "join_method", "invite", "registered_on", "password_stamp",
)
FROZEN_UNLESS_SERVER = ("token_hash", "retired_token_hash")


class AlvoraaFieldDevice(Document):
	# ── the rules ────────────────────────────────────────────────────────────

	def validate(self):
		if not self.registered_on:
			self.registered_on = now()

		if self.is_new():
			self._only_the_server_creates_these()
			return

		before = self.get_doc_before_save()
		if before is None:
			# Frappe could not read the row it is about to overwrite. Fail closed:
			# we cannot tell what is changing, so nothing may change.
			frappe.throw(_("This phone record could not be checked. Please try again."),
			             frappe.ValidationError)

		self._frozen_fields_stay_frozen(before)
		self._status_moves_are_legal(before)

	def before_save(self):
		before = self.get_doc_before_save()
		if before is not None and before.status != self.status:
			self._record_the_change()
			if self.status in NO_LIVE_SECRET:
				self._retire_the_secret()

	def on_update(self):
		"""Record who turned a device on.

		HR activating a second phone for somebody is the one moment in this
		feature where a human decision matters, so it is worth being able to
		answer "who allowed this" six months later.
		"""
		if self.has_value_changed("status") and self.status == "Active":
			if not self.activated_by:
				self.db_set("activated_by", frappe.session.user, update_modified=False)

	def on_trash(self):
		"""A phone record is never deleted.

		The permission change takes `delete` away from every role, which covers
		HR and a System Manager. Administrator is not limited by Frappe
		permissions, and neither is a script, so the rule is also written here.
		The row is the only evidence of which phone sent a punch; deleting it
		orphans every `Employee Checkin` that points at it.
		"""
		frappe.throw(
			_("A phone record cannot be deleted. Block it instead - the record of "
			  "which phone sent each check-in has to stay."),
			frappe.PermissionError)

	# ── the pieces ───────────────────────────────────────────────────────────

	def _by_the_server(self):
		return bool(self.flags.get(SERVER_FLAG))

	def _only_the_server_creates_these(self):
		if self._by_the_server():
			return
		frappe.throw(
			_("A phone record is made when somebody sets up the app, not by hand. "
			  "Invite the employee to the app instead."),
			frappe.PermissionError)

	def _changed(self, before, field):
		"""Did this field really change?

		Compared as text, which is what Frappe's own `validate_set_only_once`
		does, and for the same reason: a form sends a Datetime back as the string
		"2026-09-18 12:00:00" while the row holds a `datetime` object. Comparing
		the two directly says "changed" on every ordinary save, which would have
		refused every save of this record rather than only the forbidden ones.
		"""
		return str(self.get(field) or "") != str(before.get(field) or "")

	def _frozen_fields_stay_frozen(self, before):
		for field in FROZEN_AFTER_INSERT:
			if not self.meta.has_field(field):
				continue
			if self._changed(before, field):
				frappe.throw(
					_("{0} cannot be changed once the phone is set up.").format(
						_(self.meta.get_label(field))),
					frappe.ValidationError)

		if self._by_the_server():
			return
		for field in FROZEN_UNLESS_SERVER:
			if not self.meta.has_field(field):
				continue
			if self._changed(before, field):
				frappe.throw(
					_("A phone's secret cannot be changed by hand."),
					frappe.PermissionError)

	def _status_moves_are_legal(self, before):
		old, new = before.status, self.status
		if old == new:
			return

		if old in FINAL:
			frappe.throw(
				_("A blocked phone cannot be switched back on. Make a new code "
				  "instead."),
				frappe.ValidationError)

		if old == SIGNED_OUT and new != "Replaced":
			# A signed-out phone has no live secret. Nothing - not HR, not the
			# server - may switch it back on; a new sign-in replaces it.
			frappe.throw(
				_("A signed-out phone cannot be switched back on. The person signs in "
				  "again instead."),
				frappe.ValidationError)

		if self._by_the_server():
			# The server's own moves: replace, remove, the leaver hook, and the
			# notice gate. They still cannot resurrect a final state, because the
			# check above runs first for everybody.
			self._a_block_says_why(new)
			return

		if new in SERVER_ONLY:
			frappe.throw(
				_("Only the app can put a phone into that state."),
				frappe.ValidationError)

		if (old, new) not in ALLOWED_BY_A_PERSON:
			frappe.throw(
				_("A phone cannot be moved from {0} to {1}.").format(_(old), _(new)),
				frappe.ValidationError)

		if (old, new) == ("Pending", "Active") and self.join_method in APP_JOIN_METHODS:
			# A phone that joined with HR's code was already approved by the
			# person who made the code; one that signed in was approved by the
			# person's own password. Nobody approves it a second time, and
			# nobody uses this door to switch on a phone the app parked.
			frappe.throw(
				_("A phone that joined through the app is switched on by the app, not "
				  "from here."),
				frappe.ValidationError)

		self._a_block_says_why(new)

	def _a_block_says_why(self, new):
		if new == "Blocked" and not self.block_reason:
			frappe.throw(_("Choose a reason. It is kept in the record."),
			             frappe.ValidationError)

	def _record_the_change(self):
		"""Who moved this phone, when, and from which desk.

		`modified` moves whenever anything is saved, so it cannot answer "when
		did this phone stop". These three fields can.
		"""
		self.status_changed_on = now()
		user = frappe.session.user
		source = self.flags.get("alvoraa_change_source")
		if not source:
			source = "System" if user in ("Guest", None) else "HR"
		self.status_change_source = source
		# A change made by the employee on their own phone, or by a scheduled
		# job, has no desk user to name. Leaving it empty is the honest answer.
		self.status_changed_by = user if source == "HR" else None

	def _retire_the_secret(self):
		"""Move the live secret's hash aside, in the same save as the status.

		Two things at once, and both matter. The live hash is emptied, so the
		phone's next call finds no record and is refused. The old hash is kept,
		so that call can still be recognised as THIS phone and answered with its
		own reason rather than "not set up" - and so a question six months later
		about which phone punched still has an answer.
		"""
		if self.token_hash:
			self.retired_token_hash = self.token_hash
			self.token_hash = None
