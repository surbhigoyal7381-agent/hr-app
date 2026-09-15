"""Data to review: figures whose data looks wrong, found every morning (slice 012).

Push 1 of the leadership view. Three things live here:

  indexes           the eight indexes every scoped figure filters on
  morning checks    doubtful attendance days, leave that looks unrecorded,
                    leavers with no leaving date
  Data to review    HR's list of those findings, and their confirmations

Nothing here stores a figure. Findings hold counts and dates only - never an
employee, a name or a leave type.
"""

import frappe

DOCTYPE = "Alvoraa Data Review Item"

# More Open items than one scope can have: 25 branches x 35 days, plus a few per company.
MAX_ITEMS = 1000


def item_filters(scope, **extra):
	"""Filters limiting review records to an HR scope.

	The explicit branch filter matters for location HR: Frappe's User Permissions
	let a record with an EMPTY branch through, and a company-wide item carries
	company-wide counts that a store's HR person has no business reading.
	"""
	filters = {"company": ["in", list(scope.companies) or [""]], **extra}
	if scope.branches is not None:
		filters["alvoraa_branch"] = ["in", list(scope.branches) or [""]]
	return filters


def review_summary(scope):
	"""How many figures need review in this scope, and which days look wrong (AC-17, AC-46).

	Read with get_list, so the caller's own permissions apply too.
	"""
	if scope.not_linked:
		return {"open_count": 0, "doubtful_dates": []}
	rows = frappe.get_list(DOCTYPE, filters=item_filters(scope, status="Open"),
	                       fields=["item_type", "check_date"], limit_page_length=MAX_ITEMS)
	dates = sorted({str(r.check_date) for r in rows if r.item_type == "Doubtful day" and r.check_date})
	return {"open_count": len(rows), "doubtful_dates": dates}


# ── indexes (US-1, OPS-52, OPS-70) ───────────────────────────────────────────
#
# One-column indexes need a Property Setter as well as the index. Frappe 16
# drops a single-column index on a standard table whenever it re-syncs that
# table and the field is not marked "indexed" (database/schema.py, the drop
# list). A re-sync happens on an ERPNext update, and also any time somebody
# saves a Custom Field on Employee. `add_index` would mark the field itself,
# but skips that step during migrate and install - exactly where this runs.
# Two-column indexes are never dropped that way, so they need no marker.

SINGLE_COLUMN_INDEXES = (
	("Employee", "company"),
	("Employee", "branch"),
	("Employee", "department"),
	("Employee", "date_of_joining"),
	("Employee", "relieving_date"),
	("Employee Checkin", "time"),
)

TWO_COLUMN_INDEXES = (
	("Employee Checkin", ("alvoraa_branch", "time")),
	("Attendance", ("alvoraa_branch", "attendance_date")),
)


def add_indexes():
	"""Create the eight indexes. Safe to run again: it changes nothing then."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	for doctype, field in SINGLE_COLUMN_INDEXES:
		marked = frappe.db.exists(
			"Property Setter",
			{"doc_type": doctype, "field_name": field, "property": "search_index"},
		)
		# Only when missing: writing it again deletes and re-inserts the row and
		# clears the doctype's cache on every migrate. `is_system_generated` stays
		# True, so "Reset to defaults" in Customize Form leaves it alone.
		if not marked:
			make_property_setter(doctype, field, "search_index", "1", "Check", for_doctype=False)
		frappe.db.add_index(doctype, [field])

	for doctype, fields in TWO_COLUMN_INDEXES:
		# The branch column comes from slice 011's installer, which runs just
		# before this one in the hook lists. Checked anyway, so a site where it
		# is missing still migrates.
		if all(frappe.db.has_column(doctype, f) for f in fields):
			frappe.db.add_index(doctype, list(fields))


def after_install():
	"""A site built with `bench install-app` (CI) never runs after_migrate."""
	add_indexes()
	_ensure_settings()


def after_migrate():
	add_indexes()
	_ensure_settings()


def _ensure_settings():
	from alvoraa_portal.alvoraa_portal.doctype.alvoraa_leader_view_settings.alvoraa_leader_view_settings import (
		ensure_default,
	)

	ensure_default()
