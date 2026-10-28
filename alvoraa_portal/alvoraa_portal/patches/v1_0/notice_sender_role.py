"""Slice 076 (US-1, SEC-6, decision Q8): the "Notice Sender" role.

Made with no desk access, and given ONCE to the people who hold HR Manager at
the moment this runs. After that the organisation owns it: it gives and removes
the role in Users, and this never gives it to anyone again - running it a
second time changes nobody, and a person HR took it from does not get it back.

Runs before the Announcement DocType is synced (no [post_model_sync] section in
this app's patches.txt), so the role exists before Frappe could make it with
desk access. Rollback: none needed; the role does nothing without the code.
"""

import frappe

from alvoraa_portal.announcements import ROLE, make_role


def execute():
	existed = frappe.db.exists("Role", ROLE)
	make_role()
	if existed:
		return
	holders = frappe.get_all("Has Role", filters={"role": "HR Manager", "parenttype": "User"}, pluck="parent")
	for name in sorted(set(holders) - {"Administrator", "Guest"}):
		if not frappe.db.get_value("User", name, "enabled"):
			continue
		frappe.get_doc("User", name).add_roles(ROLE)
