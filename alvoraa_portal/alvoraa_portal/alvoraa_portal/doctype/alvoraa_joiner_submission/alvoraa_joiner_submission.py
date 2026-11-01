"""A person who has told us about themselves and is not yet an employee.

Slice 078, step 6. The controller holds three rules and nothing else; the token,
the public page and the erase job live in their own modules.

**It never becomes an Employee by itself (078-SEC-12).** There is no code path
anywhere that creates an `Employee` from one of these. HR creates the personnel
record by hand, in Desk, and sets the joining date themselves - because a
back-dated joining date makes Frappe mark the person Absent for every day since
and deleting those rows does not help. That is a logged DTC fault, not a
theory.

**Every move out of Invited or Submitted is terminal.** A link cannot be
revived, which `Alvoraa App Invite` already established for the field app.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now

LIVE = ("Invited", "Submitted")
TERMINAL = ("Made an employee", "Expired", "Cancelled")

# What the joiner is asked for - 078-PRIV-9's closed allow-list, the seven the
# design promises and not one more.
#
# **No bank account, no salary, no CTC and no statutory identifier as a typed
# field.** Where an identity number is genuinely needed it arrives as one of the
# ticked document types - a file under HR's existing verification flow rather
# than a searchable column on a table a stranger can write to.
JOINER_FIELDS = (
	"full_name",
	"mobile",
	"personal_email",
	"current_address",
	"emergency_contact_name",
	"emergency_relation",
	"emergency_phone",
)

# Slice 079. The six details HR ticks are named after `Employee`'s own columns -
# `people_fields.MY_PROFILE_WRITE_FIELDS`, the same six an employee may correct
# about themselves, by identity so a third list cannot appear and drift. This
# doctype's columns were named differently in 078, so the map is fixed here, in
# one place, and tested.
#
# `full_name` is deliberately NOT in it: it is HR's own entry at invite,
# pre-filled on the form, correctable by the joiner, and never made compulsory
# by a tick (AC-104).
COLUMN_FOR_TICK = {
	"cell_number": "mobile",
	"personal_email": "personal_email",
	"current_address": "current_address",
	"person_to_be_contacted": "emergency_contact_name",
	"relation": "emergency_relation",
	"emergency_phone_number": "emergency_phone",
}


class AlvoraaJoinerSubmission(Document):
	def validate(self):
		self._refuse_a_revival()
		self._follow_the_employee()
		self._stamp_the_closing()

	def on_update(self):
		self._close_the_sign_in()

	def _close_the_sign_in(self):
		"""Slice 079, 079-SEC-5. **The one place all the endings meet.**

		Four of the five ways a joiner's access ends are a move into a terminal
		state - cancelled, expired, hired, and turned down (which HR records as
		a cancellation with that reason). Putting the closing here rather than
		at four call sites means no caller can forget it, and it happens in the
		same transaction as the status change.

		**The fifth ending is not here, and that is decision 4a:** pressing Send
		ends the FORM, not the sign-in. Somebody who finds their PAN card the
		next evening should not have to ring HR, so the account lives until its
		expiry date or until HR ends it.
		"""
		if self.status not in TERMINAL or not self.get("user"):
			return
		before = self.get_doc_before_save()
		if before and before.status == self.status:
			return
		from alvoraa_portal.joiner_invite import end_the_sign_in

		end_the_sign_in(self, why=self.status)

	def _stamp_the_closing(self):
		"""When it stopped being live, recorded ONCE.

		The not-hired retention window runs from this and not from `modified`,
		because `modified` moves on any later edit - so ticking legal hold and
		unticking it again would restart a 180-day clock. Found by a test that
		aged a row and watched it survive.
		"""
		if self.status in TERMINAL and not self.closed_on:
			self.closed_on = now()

	def _refuse_a_revival(self):
		before = self.get_doc_before_save()
		if not before:
			return
		if before.status in TERMINAL and self.status != before.status:
			frappe.throw(
				_("This invite is already {0} and cannot be changed back.").format(
					_(before.status)),
				frappe.ValidationError)

	def _follow_the_employee(self):
		"""HR linking the personnel record is what moves it on.

		Declarative on purpose: there is no "turn this into an employee" button
		to press by accident, and no endpoint that could be called with somebody
		else's id. HR makes the Employee, opens this row, picks it, and saves.
		"""
		if self.employee and self.status in ("Invited", "Submitted"):
			self.status = "Made an employee"


def strip_personal_fields(doc):
	"""Clear every field the joiner typed, in place. Does not save.

	Shared by the erase job and by HR's Purge so there is one list, and so
	neither can forget a field the other remembers.
	"""
	for field in JOINER_FIELDS:
		doc.set(field, None)
	doc.set("bring_on_day_one", None)
	# HR's own entry, and still this person's telephone number or email - so it
	# goes with everything else. It is not in `JOINER_FIELDS` because the joiner
	# is never asked for it and it is never one of HR's ticks.
	doc.set("login_id", None)


def erase(name, why, force=False):
	"""Real deletion of what the joiner sent. Not a flag, not a soft delete.

	Counsel's 18 September 2026 policy prohibits indefinite soft deletion, so
	this clears the fields and **deletes the uploaded files, bytes included** -
	a parent that keeps its `File` rows is the obvious way to get this wrong,
	and those files are identity documents.

	**What survives is a shell with no personal data in it**: the status, who
	issued the link, the dates, and the Employee link where there is one. That
	is what answers "who invited somebody on 3 November" a year later, which
	§15 of the spec promises, and it holds nothing about the person. Said out
	loud because it is a judgement: counsel said there is no reason to hold the
	data, and this holds none of it.

	**Legal hold wins**, however old the row is, unless the caller is HR acting
	on a person's own request (`force`), which is the one case where erasing is
	the obligation rather than the risk.

	Returns True when something was erased.
	"""
	doc = frappe.get_doc("Alvoraa Joiner Submission", name)
	if doc.legal_hold and not force:
		return False
	if doc.erased_on:
		return False

	deleted = delete_the_documents(name)
	account = _delete_the_sign_in(doc)

	strip_personal_fields(doc)
	doc.erased_on = now()
	doc.erased_why = why
	# `ignore_permissions` is passed to `save` below; setting the flag as well
	# was a second copy of the same decision.
	doc.flags.ignore_validate_update_after_submit = True
	# Slice 079, 079-PRIV-2. **Without this the erasure is theatre.** The doctype
	# carries `track_changes: 1`, so a save that clears a field writes the OLD
	# value into `tabVersion` - the mobile number, the home address and the
	# emergency contact we have just told somebody we deleted. See `_sweep_the_history`.
	doc.flags.ignore_version = True
	doc.save(ignore_permissions=True)
	_sweep_the_history(name)
	frappe.db.commit()

	# A count and a reason. Never a name, never a number, never a file.
	frappe.logger("alvoraa").info(
		f"joiner submission erased: {name}, {deleted} file(s), "
		f"sign-in gone: {account}, reason {why}")
	return True


def delete_the_documents(name):
	"""Every uploaded file on one row, bytes included. Returns the count.

	Shared by `erase` and by the **document clock**, which deletes the files and
	nothing else (counsel's ruling 4 - an identity document goes much sooner
	than a candidate record). One function, so the two cannot drift apart and
	one of them quietly stop deleting the bytes.
	"""
	deleted = 0
	for file_name in frappe.get_all("File", filters={
		"attached_to_doctype": "Alvoraa Joiner Submission",
		"attached_to_name": name,
	}, pluck="name", ignore_permissions=True):
		try:
			frappe.delete_doc("File", file_name, force=True, ignore_permissions=True,
			                  delete_permanently=True)
			deleted += 1
		except Exception:
			# Say which row, never what was in it.
			frappe.log_error(f"Could not delete a joiner file on {name}",
			                 "Joiner retention")
	return deleted


def _sweep_the_history(name):
	"""Delete every `Version` row for this submission (079-PRIV-2 clause 3).

	**This is the clause that made both retention clocks real.** The joiner's own
	submit and this erase both pass `ignore_version`, so no new history row
	carries their values - but HR's own edits DO write history, deliberately
	(AC-96: §14 of the spec promises that "who changed this row, and to what" is
	answerable a year later), and an HR edit to the mobile number puts the
	mobile number in `tabVersion`.

	So the sweep is not belt and braces on the `ignore_version` flags. It is the
	only thing that reaches what HR's editing wrote. An audit trail of *who
	issued and closed an invite* survives in the row's own shell - `status`,
	`invited_by`, the dates, `erased_on`, `erased_why` - and holds nothing about
	the person.
	"""
	try:
		frappe.db.delete("Version", {
			"ref_doctype": "Alvoraa Joiner Submission", "docname": name,
		})
	except Exception:
		frappe.log_error(f"Could not clear the history on {name}",
		                 "Joiner retention")


def _delete_the_sign_in(doc):
	"""The joiner's `User` row, gone (079-PRIV-2 clause 4).

	`delete_permanently=True` so Frappe's own `Deleted Document` does not keep a
	JSON copy of their name - which would make the erasure a move rather than a
	deletion.

	**If a linked row makes the delete impossible, the fallback is explicit**:
	strip the name, strip the roles, disable, and record on the row that the
	account could not go. Never leave a named user row behind silently.
	"""
	name = doc.get("user")
	if not name or not frappe.db.exists("User", name):
		return "none"
	try:
		frappe.delete_doc("User", name, force=True, ignore_permissions=True,
		                  delete_permanently=True)
		doc.set("user", None)
		return "deleted"
	except Exception:
		try:
			frappe.db.set_value("User", name, {
				"enabled": 0, "first_name": "Erased", "full_name": "Erased",
				"mobile_no": None, "phone": None,
			}, update_modified=False)
			frappe.db.delete("Has Role", {"parent": name, "parenttype": "User"})
		except Exception:
			pass
		frappe.log_error(
			f"The sign-in on {doc.name} could not be deleted, so it was stripped "
			f"and disabled instead", "Joiner retention")
		return "stripped"
