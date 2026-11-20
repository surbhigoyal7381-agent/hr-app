"""Slice 087 (AC-100, OPS-R10): how many punch fixes were sent this month, by
company and by where each one stands. A punch fix is a request with a missing
time OR punches to set aside; Report Builder filters are all "and", so this is a
small Script Report. Only the companies the caller looks after are counted."""

import frappe
from frappe import _
from frappe.utils import get_first_day, get_last_day, nowdate

import hrms.alvoraa_hr_core.access as access

STATES = ("Waiting", "Approved", "Declined", "Withdrawn")


def state_of(row):
	if row.docstatus == 1:
		return "Approved"
	return row.alvoraa_review_status if row.alvoraa_review_status in ("Declined", "Withdrawn") else "Waiting"


def execute(filters=None):
	columns = [{"label": _("Company"), "fieldname": "company", "fieldtype": "Link",
	            "options": "Company", "width": 220}] + [
		{"label": _(s), "fieldname": s.lower(), "fieldtype": "Int", "width": 110} for s in STATES]
	companies = access.permitted_companies()
	if not companies:
		return columns, []
	rows = frappe.get_all(
		"Attendance Request",
		filters={"company": ("in", companies), "docstatus": ("<", 2),
		         "creation": ("between", [get_first_day(nowdate()), f"{get_last_day(nowdate())} 23:59:59"])},
		fields=["company", "docstatus", "alvoraa_review_status", "alvoraa_missing_time", "alvoraa_set_aside"])
	counts = {}
	for r in rows:
		if r.alvoraa_missing_time in (None, "") and not (r.alvoraa_set_aside or "").strip():
			continue
		by_state = counts.setdefault(r.company, dict.fromkeys((s.lower() for s in STATES), 0))
		by_state[state_of(r).lower()] += 1
	return columns, [{"company": c, **v} for c, v in sorted(counts.items())]
