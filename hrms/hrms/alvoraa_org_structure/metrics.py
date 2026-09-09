"""What is wrong with the shape of this organisation.

An org chart that only draws boxes tells you what the company looks like. These
are the numbers that tell you what to do about it.

Everything here is DERIVED on read. Nothing is stored, because a stored count of
vacancies drifts the first time somebody resigns on a Friday, and a dashboard
that is confidently wrong is worse than no dashboard.

Every flag says what it is, why it matters and what somebody would do about it.
A dashboard of red dots with no explanation gets ignored by the second week.
"""

import frappe
from frappe import _
from frappe.utils import date_diff, flt, nowdate

from hrms.alvoraa_org_structure import settings


def _positions(as_at):
	return frappe.get_all(
		"Alvoraa Position",
		filters={"status": ("!=", "Closed")},
		fields=["name", "position_title", "seats", "status", "is_key_position",
		        "reports_to_position", "department", "company", "modified"])


def _assignments(as_at):
	rows = frappe.get_all(
		"Alvoraa Position Assignment",
		filters={"from_date": ("<=", as_at)},
		fields=["employee", "employee_name", "position", "weight",
		        "assignment_type", "from_date", "to_date"])
	return [r for r in rows if not r.to_date or str(r.to_date) >= str(as_at)]


@frappe.whitelist()
def org_health(as_at=None):
	"""The headline numbers, and every position behind each one."""
	frappe.only_for(["HR Manager", "HR User", "System Manager"])
	as_at = as_at or nowdate()

	positions = _positions(as_at)
	assignments = _assignments(as_at)
	by_position, by_person = {}, {}
	for a in assignments:
		by_position.setdefault(a.position, []).append(a)
		by_person.setdefault(a.employee, []).append(a)

	children = {}
	for p in positions:
		if p.reports_to_position:
			children.setdefault(p.reports_to_position, []).append(p)

	flags = []
	flags += _vacancies(positions, by_position, as_at)
	flags += _over_capacity(by_person)
	flags += _long_cover(assignments, as_at)
	flags += _span_of_control(positions, children)
	flags += _contradictions(positions, by_position)

	kinds = {}
	for f in flags:
		kinds.setdefault(f["kind"], {"kind": f["kind"], "label": f["label"],
		                             "why": f["why"], "severity": f["severity"],
		                             "items": []})["items"].append(f)
	for k in kinds.values():
		k["count"] = len(k["items"])

	active = {p.name for p in positions if p.status == "Active"}
	filled = sum(flt(a.weight) for a in assignments
	             if a.position in active) / 100.0
	# The headline has to count vacancies the same way the list beneath it
	# does, or the two halves of one screen disagree in front of somebody
	# making a headcount decision. When the organisation says a covered seat
	# is still vacant, that applies here too.
	counts_as_filled = (
		sum(flt(a.weight) for a in assignments if a.position in active
		    and (a.assignment_type or "Permanent") == "Permanent") / 100.0
		if settings.get("alvoraa_cover_vacancy_stays_open") else filled)
	budgeted = sum(flt(p.seats) for p in positions if p.status == "Active")

	return {
		"as_at": as_at,
		"headline": {
			"positions": len(positions),
			"seats_budgeted": round(budgeted, 1),
			"seats_filled": round(filled, 1),
			# The number an executive opens this for.
			"seats_vacant": round(max(0.0, budgeted - counts_as_filled), 1),
			"people_over_capacity": len([f for f in flags
			                             if f["kind"] == "over_capacity"]),
			"positions_flagged": len({f["position"] for f in flags if f.get("position")}),
			"flags": len(flags),
		},
		# Worst first. A dashboard sorted by name makes the one urgent thing as
		# easy to miss as if it were not there.
		"by_kind": sorted(kinds.values(),
		                  key=lambda k: (-_RANK.get(k["severity"], 0), -k["count"])),
	}


_RANK = {"high": 3, "medium": 2, "low": 1}


def _flag(kind, label, why, severity, **rest):
	return {"kind": kind, "label": label, "why": why, "severity": severity, **rest}


# ── the flags ────────────────────────────────────────────────────────────────

def _vacancies(positions, by_position, as_at):
	out = []
	for p in positions:
		if p.status != "Active":
			continue
		held = by_position.get(p.name, [])
		permanent = sum(flt(a.weight) for a in held
		                if (a.assignment_type or "Permanent") == "Permanent") / 100.0
		open_seats = flt(p.seats) - permanent
		if open_seats < 0.5:
			continue
		covered = any((a.assignment_type or "Permanent") != "Permanent" for a in held)
		# A key position standing empty is a different problem from a spare
		# cashier's chair, and it should not be buried in the same list.
		if p.is_key_position:
			out.append(_flag(
				"key_vacant", "Key position empty",
				"A seat somebody decided was critical has nobody permanently in "
				"it. This is the one to fill first.",
				"high", position=p.name, title=p.position_title,
				open=round(open_seats, 1), covered=covered,
				department=p.department))
		else:
			out.append(_flag(
				"vacant", "Vacant seat",
				"Budgeted and unfilled. Cover does not close it, because once "
				"somebody is standing in the urgency drops and the requisition "
				"quietly stalls.",
				"medium", position=p.name, title=p.position_title,
				open=round(open_seats, 1), covered=covered,
				department=p.department))
	return out


def _over_capacity(by_person):
	cap = flt(settings.get("alvoraa_cover_max_load"))
	out = []
	for employee, rows in by_person.items():
		load = sum(flt(r.weight) for r in rows)
		if cap and load <= cap:
			continue
		if not cap and load <= 100:
			continue
		out.append(_flag(
			"over_capacity", "Carrying more than one job",
			"Their own role plus what they are covering. Allowed, and worth "
			"watching - somebody at this level for three weeks is covering, and "
			"somebody there for seven months is being taken advantage of.",
			"high" if load >= 150 else "medium",
			employee=employee, name=rows[0].employee_name,
			load=round(load), cap=round(cap),
			positions=[{"position": r.position, "weight": flt(r.weight),
			            "cover": (r.assignment_type or "Permanent") != "Permanent"}
			           for r in rows]))
	return out


def _long_cover(assignments, as_at):
	limit = int(settings.get("alvoraa_cover_max_days"))
	out = []
	for a in assignments:
		if (a.assignment_type or "Permanent") == "Permanent":
			continue
		days = date_diff(as_at, a.from_date) if a.from_date else 0
		if days < limit:
			continue
		out.append(_flag(
			"long_cover", "Cover that has become permanent by neglect",
			"Nobody decided this. It was meant to be temporary and nobody "
			"revisited it. Make it permanent, or re-advertise.",
			"high" if days > limit * 2 else "medium",
			position=a.position, employee=a.employee, name=a.employee_name,
			days=days, over_by=days - limit, ends=a.to_date or "open-ended"))
	return out


def _span_of_control(positions, children):
	wide = int(settings.get("alvoraa_org_span_wide"))
	narrow = int(settings.get("alvoraa_org_span_narrow"))
	out = []
	for p in positions:
		kids = children.get(p.name, [])
		if len(kids) >= wide:
			out.append(_flag(
				"span_wide", "Too many people reporting in",
				"Past about this many, a manager cannot give anybody real "
				"attention - one-to-ones stop, and appraisals become a form to "
				"fill in. Usually the sign that a layer is missing.",
				"medium", position=p.name, title=p.position_title,
				reports=len(kids)))
		elif len(kids) == narrow and narrow:
			out.append(_flag(
				"span_narrow", "A layer of one",
				"One person managing one person is usually a title rather than "
				"a job. Sometimes it is a deliberate deputy; usually it is a "
				"layer nobody removed.",
				"low", position=p.name, title=p.position_title,
				reports=len(kids)))
	return out


def _contradictions(positions, by_position):
	"""Things that cannot all be true at once, and mean somebody has stopped
	maintaining the register."""
	out = []
	for p in positions:
		held = by_position.get(p.name, [])
		filled = sum(flt(a.weight) for a in held) / 100.0

		if p.status == "Frozen" and held:
			out.append(_flag(
				"frozen_but_filled", "Frozen, with somebody in it",
				"A hiring pause on a seat that is occupied. Either the freeze is "
				"stale or the assignment is.",
				"medium", position=p.name, title=p.position_title,
				people=len(held)))

		if flt(p.seats) and filled > flt(p.seats) + 0.01:
			out.append(_flag(
				"over_filled", "More people than seats",
				"The register says this seat holds fewer people than are in it. "
				"Headcount and cost from here are both wrong.",
				"high", position=p.name, title=p.position_title,
				seats=flt(p.seats), filled=round(filled, 2)))

		if not p.reports_to_position and p.name not in {q.reports_to_position
		                                                for q in positions}:
			# A seat with nothing above and nothing below is not part of the
			# organisation - it is a box somebody drew and forgot.
			if not any(q.reports_to_position == p.name for q in positions):
				out.append(_flag(
					"orphan", "Attached to nothing",
					"No seat above it and none below. Either it belongs "
					"somewhere and nobody said where, or it should be closed.",
					"low", position=p.name, title=p.position_title))
	return out


@frappe.whitelist()
def flagged_positions(kind=None, as_at=None):
	"""One flag type in full, for somebody who clicked a headline number."""
	frappe.only_for(["HR Manager", "HR User", "System Manager"])
	out = org_health(as_at)
	if not kind:
		return out
	for group in out["by_kind"]:
		if group["kind"] == kind:
			return group
	return {"kind": kind, "count": 0, "items": []}
