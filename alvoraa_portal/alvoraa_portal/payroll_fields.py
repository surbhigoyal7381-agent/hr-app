"""The columns the pay-rule engine writes its verdict into.

WHY THIS FILE EXISTS. The engine was written and the tests were written, but
nothing ever created the fields, so every write failed with "Unknown column".
It did not show up in day-to-day use because both hooks return early on a
company with no rule set - and until DTC's rule set exists, that is every
company. The first thing the rule set would have done is break attendance
submission for the whole tenant.

Wired to BOTH after_migrate and after_install, for the reason attendance
correction learned the hard way: a site is built with `bench install-app`,
which never runs a migrate, so a brand new tenant would be missing them in
exactly the same way.

THESE ARE ON Attendance, NOT ON A TABLE OF OUR OWN. The verdict belongs to the
day it judges. Keeping it on the Attendance row is what makes a reprocess safe
to run twice: the second run overwrites the same eleven values instead of
adding a second adjustment on top of the first.

ALL BUT TWO ARE READ-ONLY, AND ONLY THOSE TWO ARE `allow_on_submit` (ALV-477).
The two that a person may set are the held-day confirmation (ATT-06) - somebody
has to stand behind the time an employee left when the machine has no record of
it. The rest are the engine's alone. `read_only` is not enforced by the server,
but a change to a submitted row that is not `allow_on_submit` is refused by
Frappe on every document route (Desk, REST, `frappe.client`). `db.set_value`,
`db_set`, Server Scripts, raw SQL and `ignore_validate_update_after_submit`
bypass that by design, and an import was not driven. The engine does not
need the flag: it writes with `frappe.db.set_value`, which is not a document
save. The flag is written as an explicit 0 rather than left out, because
`create_custom_fields` merges what is given over what a site already has, so a
missing key would leave an existing tenant on 1.
"""

import frappe

ATTENDANCE = "Attendance"

# Everything the engine works out about one day. Int rather than Float for the
# quarters because a quarter-day is the smallest unit DTC deduct; there is no
# such thing as half of one.
VERDICT = [
	{"fieldname": "alvoraa_rules_section", "fieldtype": "Section Break",
	 "label": "Pay Rules", "insert_after": "early_exit", "collapsible": 1,
	 "description": "Worked out by the pay-rule engine. Only companies with a "
	                "rule set switched on have anything here."},

	# ── the held day, and the only two fields a person may set ───────────────
	{"fieldname": "alvoraa_held", "fieldtype": "Check", "label": "Held",
	 "insert_after": "alvoraa_rules_section", "read_only": 1,
	 "allow_on_submit": 0, "in_list_view": 0,
	 "description": "An odd number of punches: the employee checked in and "
	                "never checked out. The day is neither paid nor penalised "
	                "until somebody confirms when they left."},
	{"fieldname": "alvoraa_held_confirmed", "fieldtype": "Check",
	 "label": "Out Time Confirmed", "insert_after": "alvoraa_held",
	 "allow_on_submit": 1,
	 # ALV-351: also on a missing-punch day the engine has not judged (rule set
	 # saved but off) - payroll_rules_apply.attendance_onload sets the flag.
	 "depends_on": "eval:doc.alvoraa_held || (doc.__onload && doc.__onload.alvoraa_missing_punch)",
	 "description": "Tick this only when you are standing behind the time "
	                "below. Until it is ticked the day stays held."},
	{"fieldname": "alvoraa_confirmed_out_time", "fieldtype": "Time",
	 "label": "Confirmed Out Time", "insert_after": "alvoraa_held_confirmed",
	 "allow_on_submit": 1,
	 # ALV-351: also on a missing-punch day the engine has not judged (rule set
	 # saved but off) - payroll_rules_apply.attendance_onload sets the flag.
	 "depends_on": "eval:doc.alvoraa_held || (doc.__onload && doc.__onload.alvoraa_missing_punch)",
	 "mandatory_depends_on": "eval:doc.alvoraa_held_confirmed",
	 "description": "The time the employee actually left, as confirmed by "
	                "their manager."},

	# ── what the day came to ─────────────────────────────────────────────────
	{"fieldname": "alvoraa_attendance_percent", "fieldtype": "Percent",
	 "label": "Attendance", "insert_after": "alvoraa_confirmed_out_time",
	 "read_only": 1, "allow_on_submit": 0,
	 "description": "Minutes present as a share of the shift. The slab table "
	                "turns this into quarters."},
	{"fieldname": "alvoraa_slab_quarters", "fieldtype": "Int",
	 "label": "Quarters Off (Slab)", "insert_after": "alvoraa_attendance_percent",
	 "read_only": 1, "allow_on_submit": 0,
	 "description": "From the slab table, for time missed."},
	{"fieldname": "alvoraa_extra_quarters", "fieldtype": "Int",
	 "label": "Quarters Off (Extra)", "insert_after": "alvoraa_slab_quarters",
	 "read_only": 1, "allow_on_submit": 0,
	 "description": "Added by a rule outside the slab table, such as arriving "
	                "inside the late window."},

	{"fieldname": "alvoraa_rules_column", "fieldtype": "Column Break",
	 "insert_after": "alvoraa_extra_quarters"},

	{"fieldname": "alvoraa_reds", "fieldtype": "Int", "label": "Red Marks",
	 "insert_after": "alvoraa_rules_column", "read_only": 1,
	 "allow_on_submit": 0,
	 "description": "Counted for the month, where the first two are free."},
	{"fieldname": "alvoraa_greens", "fieldtype": "Int", "label": "Green Marks",
	 "insert_after": "alvoraa_reds", "read_only": 1, "allow_on_submit": 0,
	 "description": "Only for employees eligible on this date."},
	{"fieldname": "alvoraa_late_arrival", "fieldtype": "Check",
	 "label": "Late Arrival", "insert_after": "alvoraa_greens",
	 "read_only": 1, "allow_on_submit": 0},
	{"fieldname": "alvoraa_early_departure", "fieldtype": "Check",
	 "label": "Early Departure", "insert_after": "alvoraa_late_arrival",
	 "read_only": 1, "allow_on_submit": 0},
	{"fieldname": "alvoraa_special_day_doubled", "fieldtype": "Check",
	 "label": "Special Day (Doubled)",
	 "insert_after": "alvoraa_early_departure", "read_only": 1,
	 "allow_on_submit": 0,
	 "description": "A listed special day, so the day counts twice."},

	# ── the audit trail, which is the point of showing any of this ───────────
	{"fieldname": "alvoraa_rules_why", "fieldtype": "Small Text",
	 "label": "Why", "insert_after": "alvoraa_special_day_doubled",
	 "read_only": 1, "allow_on_submit": 0,
	 "description": "In plain words, every rule that fired on this day. This "
	                "is what an employee is shown when they ask."},
	{"fieldname": "alvoraa_evaluated_on", "fieldtype": "Datetime",
	 "label": "Judged On", "insert_after": "alvoraa_rules_why",
	 "read_only": 1, "allow_on_submit": 0,
	 "description": "Blank means the engine has not looked at this day yet."},
]


def after_migrate():
	"""Guarded on the doctype existing, because install order is not ours.

	A site that installs this app before Frappe HR gets nothing here and picks
	it up on the next migrate, rather than failing the install.
	"""
	if not frappe.db.exists("DocType", ATTENDANCE):
		return False

	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({ATTENDANCE: VERDICT})
	return True
