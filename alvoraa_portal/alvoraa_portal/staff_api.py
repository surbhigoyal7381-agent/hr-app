"""Slice 034, W1D-21 / SEC-16: a plain searchable staff list for HR.

Until now one flag, `plan_org_structure`, gated two different things - the org
chart (positions, vacancies, seats: the paid layer) and the plain People screen.
An HR person on a tenant that had not bought the org-structure layer therefore
had no way to look a colleague up at all.

Surbhi's decision of 23 September 2026 splits them. The org chart stays behind
`plan_org_structure`. This screen gets its own switch, `staff_list`, which is an
`opt_in` key in the same registry and reaches the page as `plan_staff_list`
through the loop `hr_api.get_available_features` already runs. No new call, no
second mechanism, no bundle: it is off everywhere until a tenant is ticked.
The reasoning, and the warning not to "fix" it by adding it to PLANS, is written
beside the key in `subscription.py`.

**This is not a new source of data.** Everything it returns is already in
today's org-chart people search for the same caller, with the same fields. What
is new is that it can be sold - or given away - separately.

Three rules, each with a test that fails if it is broken:

**The switch is checked HERE, on the server (SEC-16, abuse case A14).** Not
drawing a menu entry is not a permission. An HR user on a tenant without the
feature who calls this function by hand is refused, and the refusal is written
to the security log with no personal content in it.

**The scope is the shared one (SEC-16, SEC-4).** `permitted_employee_filters()`
is `permitted_employees()` in the shape a query wants, so a store's HR person
gets their store and a company's HR person gets their companies - the same
answer every other screen in this slice gives. A caller who is entitled to
nobody is refused outright rather than handed an empty list, and the helper can
never return an empty filter dict, which in Frappe would mean everybody.

**The payload is PRIV-2's five keys and Active people only.** No phone, no
email, no employee number, no branch, no manager. A leaver does not appear.

There is no `ignore_permissions` in this file, and no module-level state that
changes at run time (SEC-6, SEC-15). Every constant below is a tuple or a
number.
"""

import frappe
from frappe import _
from frappe.utils import cint

# The feature key in `subscription.FEATURES`. Named once, here, so the endpoint
# and its tests cannot drift apart from the registry.
FEATURE = "staff_list"

# PRIV-2's set, exactly. `employee` is a link key and is never displayed; the
# rest is what a person needs to recognise a colleague. Adding a field here is a
# visibility change and needs its own decision.
ROW_FIELDS = (
	"name as employee",
	"employee_name as name",
	"designation as title",
	"department",
	"image",
)

# The keys each row actually leaves with, after the aliases above. Kept beside
# them so the test can assert the payload rather than the query.
ROW_KEYS = ("employee", "name", "title", "department", "image")

# The same caps as people search (PRIV-3): the screen asks for 12, the server
# never returns more than 50 however large a number is sent.
DEFAULT_LIMIT = 12
MAX_LIMIT = 50

# A search term shorter than this matches most of a company, so it is not a
# search. An empty term is allowed on purpose - that is the plain list.
MIN_TERM = 2


def _escape_like(term):
	"""Make `%` and `_` mean themselves (PRIV-3).

	Without this, a single `%` returns everybody the caller may see in one call,
	and `a_b` quietly matches `axb`. The backslash goes first, or escaping the
	wildcards would then be escaped itself.
	"""
	return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _refuse():
	"""The frame's one no-permission sentence, and a log line with no names.

	`access.refuse` logs through `log_refusal` and then throws, so a refusal can
	be found later without anyone's name, search term or department being in the
	log (PRIV-5).

	The wording is section 6's, and it is deliberately the SAME sentence whether
	the tenant has not been given the feature or the caller is not HR. A plain
	employee must not be able to tell those two apart - the first is a fact about
	what the company bought, and the second is a fact about a colleague's role.

	`subscription.requires_feature` is the decorator this would otherwise use.
	It is not used here for one reason: it does not log the refusal, and abuse
	case A14 is specifically about somebody calling this endpoint by hand on a
	tenant that does not have it. The entitlement read itself is still
	`has_feature()` - the same function the decorator calls - so there is no
	second definition of "does this tenant have it".
	"""
	from hrms.alvoraa_hr_core.access import refuse

	refuse(
		_("This page is not part of your access. Ask HR if you think it should be."),
		rule="staff_list",
		endpoint="staff_api.get_staff_list",
		doctype="Employee",
	)


# POST only (PRIV-5). The search term is somebody's colleague's name, and a web
# server writes every URL it serves into an access log. In a POST body it is not
# in that log. It also means an old bookmark or a link in a chat cannot carry a
# search someone else then repeats.
@frappe.whitelist(methods=["POST"])
def get_staff_list(q=None, start=0, limit=DEFAULT_LIMIT):
	"""The people this HR person looks after: name, job title, department, photo.

	Guest is refused by `frappe.whitelist()` without `allow_guest`, and again by
	the line below, so adding `allow_guest` later would still not open it.

	Returns the rows, the TRUE total, and the caps that were applied. The total
	is a number and holds nothing personal (PRIV-4). It is what lets the screen
	say "showing the first 50 of 412" instead of quietly showing fewer than
	there are - on a thousand-person tenant a silent cap is how somebody
	concludes a colleague has left.

	Two queries, whatever the tenant's size.
	"""
	import hrms.alvoraa_hr_core.access as access

	from alvoraa_portal.subscription import has_feature

	if frappe.session.user == "Guest":
		_refuse()

	# The switch, on the server. A tenant that has not been given this feature
	# gets a refusal, not a hidden button (SEC-16, A14).
	if not has_feature(FEATURE):
		_refuse()

	# The scope, from the one shared definition. A caller who is entitled to
	# nobody - a plain employee, a plain manager, a vendor login - is refused
	# here rather than handed an empty list, so the screen never looks like a
	# company with no people in it.
	filters = access.permitted_employee_filters()
	if filters == access.NO_EMPLOYEES:
		_refuse()

	# Active only. `permitted_employee_filters` returns every status on purpose
	# (a leaver's history still belongs to the store that had them), so the
	# caller adds this itself - and this caller is a staff list, which must not
	# list leavers (PRIV-2).
	filters["status"] = "Active"

	# str() first: a JSON body can send a list or a number where a string is
	# expected, and this must answer with a refusal or an empty result, never a
	# 500 that says what went wrong inside.
	term = str(q or "").strip()
	if term:
		if len(term) < MIN_TERM:
			return {"rows": [], "total": 0, "start": 0, "limit": DEFAULT_LIMIT}
		filters["employee_name"] = ["like", f"%{_escape_like(term)}%"]

	limit = min(max(cint(limit) or DEFAULT_LIMIT, 1), MAX_LIMIT)
	start = max(cint(start), 0)

	rows = frappe.get_all(
		"Employee",
		filters=filters,
		fields=list(ROW_FIELDS),
		# The id breaks ties. Without it two people with the same name can make
		# the same row appear on two pages and another row never appear at all.
		order_by="employee_name asc, name asc",
		# `offset`/`limit`, not `start`/`limit_start`: the older names are
		# deprecated for removal in Frappe v17 and warn on every call.
		offset=start,
		limit=limit,
	)
	return {
		# Built key by key rather than passed through, so a field added to the
		# query above cannot reach a browser without somebody editing ROW_KEYS.
		"rows": [{key: row.get(key) for key in ROW_KEYS} for row in rows],
		"total": frappe.db.count("Employee", filters=filters),
		"start": start,
		"limit": limit,
	}
