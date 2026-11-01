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


class AlvoraaJoinerSubmission(Document):
	def validate(self):
		self._refuse_a_revival()
		self._follow_the_employee()
		self._stamp_the_closing()

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

	strip_personal_fields(doc)
	doc.erased_on = now()
	doc.erased_why = why
	doc.flags.ignore_permissions = True
	doc.flags.ignore_validate_update_after_submit = True
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	# A count and a reason. Never a name, never a number, never a file.
	frappe.logger("alvoraa").info(
		f"joiner submission erased: {name}, {deleted} file(s), reason {why}")
	return True
