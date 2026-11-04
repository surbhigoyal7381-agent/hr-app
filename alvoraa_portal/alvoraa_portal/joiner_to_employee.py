"""HR turning a joiner's own words into their personnel record (slice 082).

Two actions, and both of them are deliberately small.

**The prefill reads. It never writes.** It hands HR the six details and the name
the person typed, and HR's own Save on a form they are looking at is the only
thing that creates an `Employee`. There is no endpoint here that creates one.

**No date of any kind is in the payload (082-SEC-1).** Not the joining date, not
the date of birth, not a default and not a null placeholder. `date_of_joining`
is `reqd: 1` on `Employee` (read in `erpnext/.../employee.json`), so Frappe's own
mandatory check refuses a save without one, and the date HR types is the date HR
chose. The reason is a logged DTC fault, not a theory: a back-dated joining date
makes Frappe mark the person Absent for every day since, and deleting those rows
does not help.

**The field map lives in one place and is inverted here at runtime** -
`COLUMN_FOR_TICK` in the controller, which is also what HR's ticks are named
after. A second copy of that map, in this file or in the browser, would be two
lists that drift.

## What is deliberately NOT here

* **The document move.** The files the joiner uploaded stay on the invite. Moving
  them onto `Employee` puts an identity document behind the parent `Employee`'s
  read permission, which is a disclosure question nobody has counted yet
  (082-PRIV-1) and a retention question counsel has not answered in writing
  (082-PRIV-2). Out of scope on Surbhi's word, 4 November 2026.
* **Any `ignore_permissions`.** 082-SEC-3. Both endpoints run with the caller's
  own rights and refuse loudly when those rights are not enough.
* **An undo.** *Made an employee* is terminal (`_refuse_a_revival`), which is why
  the link step names the person before it writes anything.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission.alvoraa_joiner_submission import (
	COLUMN_FOR_TICK,
)
from alvoraa_portal.field_app_limits import HR_KEY, _limited

DOCTYPE = "Alvoraa Joiner Submission"
EMPLOYEE = "Employee"

# The only state a submission can be turned into an employee from. The
# controller's `_follow_the_employee` would also accept `Invited`; this is
# narrower on purpose, because an `Invited` row holds nothing to copy.
READY = "Submitted"


def _the_submission(submission: str | None, ptype: str) -> Document:
	"""One joiner's row, with the caller's own rights checked on THAT row.

	`check_permission` goes through `frappe.permissions.has_permission` with the
	document, so a User Permission narrowing the caller applies. A role check
	alone would not.
	"""
	if not submission or not isinstance(submission, str):
		frappe.throw(_("No joiner record was named."), frappe.ValidationError)
	if not frappe.db.exists(DOCTYPE, submission):
		# The same answer for a row that never existed and one the caller may
		# not see is not needed here: holding read on this doctype is HR-only
		# already, and a wrong reference is a typing mistake HR must be told
		# about.
		frappe.throw(_("There is no joiner record called {0}.").format(submission),
		             frappe.DoesNotExistError)
	doc = frappe.get_doc(DOCTYPE, submission)
	doc.check_permission(ptype)
	return doc


def _must_be_ready(state, name: str) -> None:
	"""Refuse every state this cannot be done from, naming the state.

	`state` carries `erased_on`, `employee` and `status`. The read-only prefill
	passes the loaded document; **the link passes three values read from the
	database under a row lock**, so a second HR user pressing at the same moment
	is refused rather than overwriting, and an erase landing in the same instant
	cannot be worked on as if it had not happened.
	"""
	if state.erased_on:
		frappe.throw(
			_("The details on {0} were erased, so there is nothing to copy. "
			  "Ask the person again.").format(name),
			frappe.ValidationError)
	if state.employee:
		frappe.throw(
			_("{0} is already the employee record for this person. A joiner "
			  "record can only be linked once.").format(state.employee),
			frappe.ValidationError)
	if state.status != READY:
		frappe.throw(
			_("This invite is {0}. Only an invite the person has sent back can "
			  "be made into an employee record.").format(_(state.status)),
			frappe.ValidationError)


@frappe.whitelist(methods=["POST"])
@_limited(HR_KEY, "user", limit=30)
def details_for_a_new_employee(submission: str | None = None) -> dict[str, str | None]:
	"""The seven values that go on a new, unsaved `Employee` form. Nothing else.

	**POST, so the rate limit is real.** `field_app_limits._limited` runs
	Frappe's own limiter with `methods=["POST"]`, so a GET would skip it
	entirely. The call is still read-only: it inserts nothing and saves nothing.

	**Two doors before a single field is returned (082-SEC-2):** `create` on
	`Employee`, because somebody who cannot make an employee record has no
	reason to read a candidate's address; and `read` on **this** submission row,
	with the document passed so User Permissions apply.

	The returned keys are exactly `COLUMN_FOR_TICK`'s keys plus `first_name`.
	Seven, always, even where the joiner left one blank - a key that appears
	and disappears would make the browser's behaviour depend on the data.
	"""
	# `create` first: it needs no row, so a caller with no business here is
	# refused before anybody's details are read off the disk.
	frappe.has_permission(EMPLOYEE, "create", throw=True)
	doc = _the_submission(submission, "read")
	_must_be_ready(doc, doc.name)

	# `full_name` goes whole into `first_name`, exactly as Frappe HR's own
	# `make_employee` maps `employee_name` (`employee_onboarding.py:110`). We do
	# not split a name in code: splitting a name is a guess, and HR can split it
	# on the form in front of them.
	out: dict[str, str | None] = {"first_name": doc.get("full_name")}
	for employee_column, our_column in COLUMN_FOR_TICK.items():
		out[employee_column] = doc.get(our_column)
	return out


@frappe.whitelist(methods=["POST"])
@_limited(HR_KEY, "user", limit=30)
def link_the_employee(submission: str | None = None,
                      employee: str | None = None) -> dict[str, object]:
	"""Record which `Employee` this joiner became. **The step that did not exist.**

	`Alvoraa Joiner Submission.employee` is `read_only: 1` and nothing in the
	product wrote it, so *Made an employee* was unreachable. Writing it here is
	what moves the status on (`_follow_the_employee`) and closes the joiner's
	sign-in (`_close_the_sign_in`, 079-SEC-5), both in the controller, both in
	this one transaction.

	**Why an endpoint rather than making the field editable.** A plain editable
	Link loses the one guard that matters: HR is shown the name of the person
	they are about to merge into before anything is written (082-SEC-6). Linking
	the wrong Employee is the worst outcome in this slice and it cannot be
	undone - *Made an employee* is terminal.

	**The link is re-read from the database under a row lock** (`for_update`),
	not taken from the form the browser loaded. Two HR users pressing at the
	same moment would both have seen it empty; the second one blocks here, reads
	what the first wrote, and is refused by name.

	**This function commits nothing of its own**, so a failure before or during
	the save leaves the row exactly as it was - no link, no status change - and
	the status therefore never becomes *Made an employee*, so the nightly erase
	never picks the row up. That is FR-ORDER, safe by construction.

	**Said exactly, because the easy version of this sentence is wrong:** the
	step is not one uncommitted transaction end to end. The existing
	`end_the_sign_in` (079) calls `frappe.db.commit()` inside `on_update`. But it
	runs AFTER the row's own update is written, and nothing here runs after it -
	so the link, the status and the closed sign-in always land together.

	**It moves no file.** See the module docstring.
	"""
	if not employee or not isinstance(employee, str):
		frappe.throw(_("Pick the employee record this person became."),
		             frappe.ValidationError)
	doc = _the_submission(submission, "write")

	if not frappe.db.exists(EMPLOYEE, employee):
		frappe.throw(_("There is no employee record called {0}.").format(employee),
		             frappe.DoesNotExistError)
	person = frappe.get_doc(EMPLOYEE, employee)
	# Write, not read: this is the record the joiner's details have just been
	# saved onto, and the caller is claiming it. An HR login narrowed to another
	# company by a User Permission is refused here.
	person.check_permission("write")

	# One query, a row lock, and all three conditions read fresh - not taken
	# from the form the browser loaded minutes ago.
	_must_be_ready(frappe.db.get_value(DOCTYPE, doc.name,
	                                   ["employee", "status", "erased_on"],
	                                   as_dict=True, for_update=True), doc.name)

	# Counted BEFORE the save, because the save closes the sign-in and stamps
	# the row, and the counts are what HR is told.
	details = sum(1 for column in COLUMN_FOR_TICK.values() if doc.get(column))
	documents = frappe.db.count("File", {"attached_to_doctype": DOCTYPE,
	                                     "attached_to_name": doc.name})

	doc.employee = employee
	doc.save()

	# A reference, a count and an outcome. Never a name, never a field value,
	# never a file name.
	frappe.logger("alvoraa").info(
		f"joiner linked to an employee: {doc.name} by {frappe.session.user}, "
		f"{details} detail(s), {documents} document(s) left on the invite")

	return {
		"employee": employee,
		# HR asked for this person by name on the confirmation; echoing it back
		# is how they can see the link landed on the one they named.
		"employee_name": person.employee_name,
		"details": details,
		"documents_left_behind": documents,
	}
