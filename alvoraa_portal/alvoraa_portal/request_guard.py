"""No HTTP request may ask Frappe to skip permissions (ALV-249, security review doors 1 and 2).

Frappe's list API (`frappe.desk.reportview.get`, `get_list`, `get_count`, export)
removes a caller's `ignore_permissions`, but not `ignore_user_permissions`. Link
search (`search_widget`, `search_link`) and ERPNext's `employee_query` take
`ignore_user_permissions` as an argument. Sent by a staff login, that one word
skips every User Permission row, so the own-record row, manager_scope's rows and
DTC's narrow rows stop counting: every employee, claim, attendance and salary
assignment comes back. A few whitelisted ERPNext and Frappe HR functions also take
`ignore_permissions` from the caller (make_salary_slip, get_party_details,
make_sales_invoice, create_dunning, make_timesheet).

So both words are dropped from every request's arguments before Frappe routes it:
every path, including a website page's POST to "/" with `cmd`, because they all
read the same `frappe.local.form_dict`. Server code that passes either word in a
Python call is untouched; this only sees what came over HTTP.

Cost: Frappe's own Desk link field sends `ignore_user_permissions` for a link
marked "Ignore User Permissions". With it dropped, a login that holds User
Permissions sees only its permitted records in that picker. That includes an HR
person who holds ERPNext's Company row (made when their Employee is saved with
"Create User Permission" ticked): on a tenant with more than one company, such a
picker shows them only their own company. With one company, as at DTC, nothing
changes. System Managers hold no rows.
"""

import frappe

DROP = ("ignore_user_permissions", "ignore_permissions")


def drop_permission_skips():
	"""before_request: remove the two words from the request's arguments."""
	form = getattr(frappe.local, "form_dict", None)
	if form:
		for key in DROP:
			form.pop(key, None)
