"""Hiring meets the seat chart (slice 064).

A Job Opening can carry a link to the seat it is filling (`alvoraa_position`,
installed by alvoraa_portal.org_job_link). Once a hire from that opening is
put in the seat by itself, that link decides WHO SITS WHERE - and a seat with
seats under it gives its holder the manager's view of the Organisation page.
So the link carries the same authority as putting somebody in a seat by hand.

THE GUARD (SEC-8). Frappe does not enforce a field's `read_only` on the
server, so the API could always set this link. Whenever it is set to a new
seat - desk, REST, data import or `post_job` - the server checks the person
may place people in that seat: Write on Alvoraa Position, the seat inside
their companies and branches, and the seat in the opening's own company.
A save that leaves the link as it was (closing the opening, editing the
description, Frappe HR's nightly close-by-date) is not checked. Clearing the
link is not checked either: it cannot place anybody.
"""

import frappe
from frappe import _

import hrms.alvoraa_org_structure.register as register

JOB_OPENING = register.JOB_OPENING
LINK = register.POSITION_LINK


def guard_seat_link(doc, method=None):
	"""Job Opening `validate`: only somebody who may place people in a seat
	may point an opening at it (SEC-8)."""
	if not doc.meta.has_field(LINK):
		return
	new = doc.get(LINK) or None
	before = doc.get_doc_before_save()
	old = (before.get(LINK) or None) if before else None
	if not new or new == old:
		return

	seat = frappe.db.get_value(register.POSITION, new, ["company", "branch"], as_dict=True)
	if not seat:
		return  # Frappe's own link check refuses a seat that does not exist
	companies, branches = register._scope()
	if (
		not register.may_edit()
		or seat.company not in companies
		or (branches is not None and (seat.branch or "") not in branches)
		or (doc.company and seat.company != doc.company)
	):
		from hrms.alvoraa_hr_core.access import refuse

		refuse(
			_(
				"You cannot link this job opening to that seat. Only someone who may "
				"place people in that seat can link an opening to it."
			),
			"SEC-8",
			"hiring.guard_seat_link",
			JOB_OPENING,
			doc.name,
		)
