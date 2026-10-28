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
from frappe.query_builder.functions import Count

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
		# Re-opening a closed opening that already names the seat is a new
		# start to hiring too, so the hold applies; SEC-8 does not (review R-1).
		if new and before and before.status != "Open" and doc.status == "Open":
			_refuse_if_on_hold(new, frappe.db.get_value(register.POSITION, new, "seats"))
		return

	seat = frappe.db.get_value(register.POSITION, new, ["company", "branch", "seats"], as_dict=True)
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

	_refuse_if_on_hold(new, seat.seats)


def _refuse_if_on_hold(position, seats):
	"""Slice 065, option A: no opening starts on a seat held for an
	improvement period - from `post_job`, the desk form or REST alike. Plan
	readers only: a refusal to anyone else would tell them a plan exists. An
	opening with no seat link is not checked (a stated limit)."""
	import hrms.alvoraa_org_structure.plans as plans

	if plans.is_reader() and plans.hiring_on_hold(position, seats):
		frappe.throw(_("Hiring for this seat is on hold until the improvement period ends and HR "
		               "records the outcome."))


# ── a hire placed in their seat on the day they join (US-18, SEC-6/7/9/10) ──
#
# Employee `after_insert`. Frappe HR already links opening -> applicant ->
# offer -> employee; nothing linked the employee to the seat, so a seat that
# was advertised stayed "Nobody in this seat" after the person joined until
# somebody remembered to put them in it.
#
# IT NEVER GETS IN THE WAY OF SAVING THE EMPLOYEE. Every condition is checked
# first; when one fails nothing is written and the person who saved is told
# why. The write itself runs inside a savepoint with messages muted, so a
# refusal from the assignment's own rules rolls back to nothing and its red
# message does not reach the save. Nothing raises out of this function.
#
# It writes NOTHING on the Employee: not reports_to, leave_approver or
# expense_approver (SEC-9). A Permanent assignment moves no approvals.


def place_hire(doc, method=None):
	"""Employee after_insert: put a new hire in the seat their opening fills."""
	try:
		opening = _opening_for(doc)
		if not opening:
			return
		_place(doc, opening)
		_close_if_filled(doc, opening)
	except Exception as e:
		# Ids and the code location only, never a name or the error's own text,
		# which can carry one (PRIV-3).
		frappe.log_error(
			title="Hire not placed in a seat",
			message=f"Employee {doc.name}: {_where(e)}",
		)


def _where(e):
	"""The exception's class and the line it came from - enough to find the
	fault, with nothing personal in it."""
	import traceback

	last = traceback.extract_tb(e.__traceback__)[-1] if e.__traceback__ else None
	return (
		f"{type(e).__name__} at {last.filename.rsplit('/', 1)[-1]}:{last.lineno}"
		if last
		else type(e).__name__
	)


def _opening_for(doc):
	"""The opening this hire came from, when it is linked to a seat - or None,
	silently, for every employee who did not come through a linked opening."""
	if doc.status != "Active" or not doc.get("job_applicant") or not doc.date_of_joining:
		return None
	if not frappe.get_meta(JOB_OPENING).has_field(LINK):
		return None
	name = frappe.db.get_value("Job Applicant", doc.job_applicant, "job_title")
	if not name:
		return None
	opening = frappe.db.get_value(
		JOB_OPENING, name, ["name", LINK, "company", "vacancies", "status"], as_dict=True
	)
	return opening if opening and opening.get(LINK) else None


def _place(doc, opening):
	who = doc.employee_name or doc.name
	seat = frappe.db.get_value(
		register.POSITION,
		opening.get(LINK),
		["name", "position_title", "branch", "company", "status", "seats"],
		as_dict=True,
	)
	if not seat:
		return
	where = seat.position_title + (" · " + seat.branch if seat.branch else "")
	joins = str(doc.date_of_joining)

	if frappe.db.exists("Employee", {"job_applicant": doc.job_applicant, "name": ("!=", doc.name)}):
		return _say(
			_(
				"Another employee was already created from this applicant, so {0} was not put in a seat."
			).format(who)
		)
	if seat.status == "Closed":
		return _say(
			_("{0} was hired for {1}, but that seat is closed. Put {0} in a seat from Positions.").format(
				who, where
			)
		)
	if seat.company != doc.company or (opening.company and opening.company != seat.company):
		return _say(
			_(
				"{0} was hired for {1}, which belongs to another company, so they were not put in it. "
				"Check the job opening's seat."
			).format(who, seat.position_title)
		)
	today = frappe.utils.nowdate()
	ends = frappe.get_all(register.ASSIGNMENT, filters={"employee": doc.name}, pluck="to_date")
	if any(not end or str(end) >= today for end in ends):
		return _say(
			_("{0} already holds a seat, so they were not put in {1}. Check Positions.").format(who, where)
		)

	# Room on the joining date, counted the way the chart counts it. A seat
	# full today but free by the joining date is fine - a replacement who
	# starts after the leaver goes (AC-66). For a joining date already past,
	# today must have room too, because the seat is filled from then on.
	position = frappe.get_doc(register.POSITION, seat.name)
	for day in [joins] + ([today] if joins <= today else []):
		held = position._current_assignments(day)
		if sum(frappe.utils.flt(a.weight) for a in held) / 100.0 + 1 > frappe.utils.flt(seat.seats) + 0.01:
			ends = [a.to_date for a in held]
			until = ""
			if ends and all(ends):
				until = " " + _("until {0}").format(frappe.utils.formatdate(min(ends), "d MMM"))
			return _say(
				_(
					"{0} was hired for {1}, but that seat is full{2}. Put {0} in from Positions when it frees up."
				).format(who, where, until)
			)

	a = frappe.new_doc(register.ASSIGNMENT)
	a.update(
		{
			"position": seat.name,
			"employee": doc.name,
			"weight": 100,
			"assignment_type": "Permanent",
			"from_date": joins,
			"delegate_authority": 0,
			# A fixed sentence with the opening's id only. NOT the applicant: a
			# Job Applicant is named by its email address, which is personal
			# data. The Employee record already links the applicant.
			# The page reads the first words to say "hired for this seat";
			# `owner` says who saved the Employee.
			"reason": f"{register.PLACED} {opening.name}",
		}
	)
	point = "pos_hire_" + frappe.generate_hash(length=10)
	muted = frappe.flags.mute_messages
	frappe.db.savepoint(point)
	try:
		frappe.flags.mute_messages = True
		# THE ONE BYPASS (SEC-7). The person saving the Employee may have no
		# right to create assignments - at DTC an HR User does not. What they
		# are allowed to do is hire from an opening somebody with that right
		# linked to this seat (hiring.guard_seat_link). Permissions only:
		# every rule on the assignment still runs.
		a.insert(ignore_permissions=True)
	except Exception as e:
		frappe.flags.mute_messages = muted
		frappe.db.rollback(save_point=point)
		frappe.log_error(
			title="Hire not placed in a seat",
			message=f"Employee {doc.name}, seat {seat.name}, opening {opening.name}: {_where(e)}",
		)
		return _say(
			_("{0} is saved, but could not be put in {1}. Put {0} in from Positions.").format(who, where)
		)
	frappe.flags.mute_messages = muted
	frappe.db.release_savepoint(point)
	_say(
		_("{0} is now in the seat {1} from {2}.").format(
			who, where, frappe.utils.formatdate(joins, "d MMM yyyy")
		),
		"green",
	)


def _close_if_filled(doc, opening):
	"""Close the opening once the employees made from its applicants reach its
	places (D6, SEC-10). As the user, with no bypass: if they may not edit it,
	it stays open and they are told. Blank or 0 places never closes."""
	places = frappe.utils.cint(opening.vacancies)
	if places < 1 or opening.status != "Open":
		return
	emp = frappe.qb.DocType("Employee")
	app = frappe.qb.DocType("Job Applicant")
	hired = (
		frappe.qb.from_(emp)
		.join(app)
		.on(app.name == emp.job_applicant)
		.select(Count(emp.name))
		.where(app.job_title == opening.name)
	).run()[0][0]
	if hired < places:
		return
	point = "pos_close_" + frappe.generate_hash(length=10)
	muted = frappe.flags.mute_messages
	frappe.db.savepoint(point)
	try:
		frappe.flags.mute_messages = True
		jo = frappe.get_doc(JOB_OPENING, opening.name)
		jo.status = "Closed"
		jo.save()
	except Exception:
		frappe.flags.mute_messages = muted
		frappe.db.rollback(save_point=point)
		return _say(
			_(
				"Job Opening {0} has all {1} places filled, but you cannot close it. Ask someone who "
				"can edit job openings to close it, so it leaves the careers page."
			).format(opening.name, places)
		)
	frappe.flags.mute_messages = muted
	frappe.db.release_savepoint(point)
	_say(
		_("Job Opening {0} is now closed: its {1} place(s) are filled. It is off the careers page.").format(
			opening.name, places
		),
		"green",
	)


def _say(message, indicator="orange"):
	"""A message to the person who saved the Employee, and nobody else."""
	frappe.msgprint(message, indicator=indicator, alert=False)
