"""The link from a job opening back to the seat it is advertising.

One field. Without it a job opening created from the Positions screen is just
another opening, and the chart cannot say "this empty seat is being recruited
for" - which is the difference between a hole somebody is dealing with and a
hole nobody has noticed.

INSTALLED FROM THIS APP, not from hrms, although the doctype is Frappe HR's.
That is the same path `attendance_correction` already takes for its fields on
Attendance Request: a custom field here rather than an edit there, so a `bench
update` of Frappe HR stays safe and the change survives it.

The writer guards on the field existing (`register.post_job`), so a site that
installs this app before Frappe HR, or has not migrated yet, creates openings
without the link rather than failing. The link is how the chart reads better,
never how the opening gets made.
"""

import frappe

JOB_OPENING = "Job Opening"


def after_migrate():
	"""Wired to after_migrate AND after_install, for the reason this app has
	learned twice: a site built with `bench install-app` never runs a migrate,
	so a brand new tenant would be missing the field in exactly the same way.

	Guarded on the doctype existing, because install order is not ours to
	choose - a site that installs this app before Frappe HR gets nothing here
	and picks it up on the next migrate.
	"""
	if not frappe.db.exists("DocType", JOB_OPENING):
		return False

	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	# Editable since slice 064, so an opening made by hand can be linked too.
	# Who may SET it is the server's rule, not this flag: Frappe does not
	# enforce read_only on the server, so the guard is a validate hook
	# (hrms.alvoraa_org_structure.hiring.guard_seat_link, SEC-8).
	create_custom_fields({JOB_OPENING: [
		{"fieldname": "alvoraa_position", "fieldtype": "Link",
		 "options": "Alvoraa Position", "label": "Position",
		 "insert_after": "designation", "read_only": 0,
		 "description": "The seat on the organisation chart this opening is "
		                "filling. Only someone who may place people in that "
		                "seat can set it."},
	]})

	# Who linked an opening to a seat, and when (PRIV-3): Job Opening keeps no
	# change history of its own. Configuration, not code - one Property Setter,
	# made once.
	if not frappe.db.exists("Property Setter", {"doc_type": JOB_OPENING,
	                                            "property": "track_changes"}):
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter

		make_property_setter(JOB_OPENING, None, "track_changes", "1", "Check", for_doctype=True)
	return True
