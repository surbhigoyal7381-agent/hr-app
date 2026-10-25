"""The second process of test_grooming_cap_066's race test (security M1).

Run with `bench --site <site> execute alvoraa_portal.tests.grooming_race_066.mark_as`.
It reads first - as the portal does before a save - so its transaction's
snapshot is fixed before the other process commits, then tries to mark.
"""

import frappe

import alvoraa_portal.grooming as grooming


def mark_as(user, employee, date, told=1):
	frappe.set_user(user)
	frappe.db.count(grooming.MARK, {"employee": employee})   # the snapshot starts here
	print("READY", flush=True)
	try:
		grooming.mark(employee, "No name badge", told_in_person=told, date=date)
		frappe.db.commit()
		print("RESULT saved", flush=True)
	except Exception as e:
		frappe.db.rollback()
		print("RESULT refused", type(e).__name__, flush=True)
