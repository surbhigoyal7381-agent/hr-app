"""Slice 076 (US-1, SEC-6): the "Notice Sender" role, with no desk access.

**Nobody is given it.** Sending notices stays off at every tenant until counsel
gives a number for how long notices and read marks are kept (Q1, Surbhi's
working default, 28 Oct 2026). The role is the switch: with no holder, nobody
sees "Send a notice" and every send endpoint refuses. A System Manager turns it
on for a tenant by ticking the role on chosen people in Users, which Frappe
records in the User's history. This replaces design Q8 ("HR Managers get it at
install") until then.

It saves no User, so it can never remove the Employee role from an HR Manager
login that has no Employee record (ERPNext's validate_employee_role does that
on every User save).

Runs before the Announcement DocType is synced (no [post_model_sync] section in
this app's patches.txt), so the role exists before Frappe could make it with
desk access. Safe to run twice. Rollback: none needed; the role does nothing
without the code.
"""

from alvoraa_portal.announcements import make_role


def execute():
	make_role()
