"""Slice 087 (AC-92): requests sent before this slice that carry a missing In/Out
were all for a Held day (085 allowed a time on no other day), so they are marked
`alvoraa_for_held_day = 1`. The monthly limit and the filing window read that
flag now, and without it those requests would start to count.

Safe to run twice: it only touches rows still at 0. No patch over Attendance or
Employee Checkin. Batched, so a tenant with many requests holds no long lock.
"""

import frappe


def execute():
	# Patches run before `after_migrate`, which is what makes the fields.
	from alvoraa_portal import held_day, punch_fix

	held_day.after_migrate()
	punch_fix.after_migrate()
	while True:
		names = frappe.get_all("Attendance Request",
		                       filters={"alvoraa_missing_log": ("is", "set"), "alvoraa_for_held_day": 0},
		                       pluck="name", limit_page_length=500)
		if not names:
			break
		frappe.db.set_value("Attendance Request", {"name": ("in", names)}, "alvoraa_for_held_day", 1,
		                    update_modified=False)
		frappe.db.commit()
