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

**The scope is the shared one for an HR caller (SEC-16, SEC-4).**
`permitted_employee_filters()` is `permitted_employees()` in the shape a query
wants, so a store's HR person gets their store and a company's HR person gets
their companies - the same answer every other screen in this slice gives.

**045 adds a second scope, for everybody else.** Surbhi opened the directory to
employees on 24 September 2026. A caller with no HR entitlement now gets
`_own_scope_filters()` instead of a refusal - **their own company**, and the
width is one named constant, `DIRECTORY_SCOPE_FOR_EMPLOYEES`. Neither helper can
ever return an empty filter dict, which in Frappe would mean everybody, and a
caller neither of them can place is still refused outright rather than handed an
empty list.

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
	# 045, Surbhi's decision of 24 September 2026: the staff directory is for
	# employees too, and **work contact is in**. Her reason: *"the companies
	# have NDAs"*.
	#
	# **`company_email` and nothing else.** It is the one genuinely
	# work-shaped contact field ERPNext's Employee has. There is **no work
	# phone or extension field at all** - `cell_number` is labelled "Mobile"
	# and is personal, `personal_email` says what it is, and
	# `emergency_phone_number` is somebody else's number entirely. Adding a
	# work-phone field is a decision for Surbhi, not a thing to slip in here.
	#
	# **And the NDA point, because it is the part that is easy to get
	# backwards:** an NDA binds the employee who LOOKS. It is not the same as
	# the employer's own duty to the person whose data it is. A colleague
	# promising not to share a home address does not make collecting and
	# showing it proportionate. Keeping this to work contact is what makes the
	# wider audience safe.
	"company_email as work_email",
)

# The keys each row actually leaves with, after the aliases above. Kept beside
# them so the test can assert the payload rather than the query.
ROW_KEYS = ("employee", "name", "title", "department", "image", "work_email")

# The same caps as people search (PRIV-3): the screen asks for 12, the server
# never returns more than 50 however large a number is sent.
DEFAULT_LIMIT = 12
MAX_LIMIT = 50

# A search term shorter than this matches most of a company, so it is not a
# search. An empty term is allowed on purpose - that is the plain list.
MIN_TERM = 2


# ── who may open the directory at all ────────────────────────────────────────
#
# **045, Surbhi's decision of 24 September 2026: employees get the directory.**
# Her decision had two halves. The field half (work email, no phone) shipped in
# `59d0c0d`. This is the audience half.
#
# **The SCOPE of a plain employee's directory is the engineer's call, not
# hers** - she said "employees get it", she did not say how wide. So it is
# behind ONE constant, and changing that one line reverses the decision:
#
#   DIRECTORY_SCOPE_FOR_EMPLOYEES = "own_company"   <- today: their own company
#   DIRECTORY_SCOPE_FOR_EMPLOYEES = "own_branch"    <- their own store only
#
# **Both are implemented below**, because a constant that selects between one
# real branch and a branch nobody wrote is not a switch, it is a comment. The
# line to change is the assignment on the next line and nothing else.
#
# **Why "own_company" is the recommendation.** A directory whose point is "find
# and contact a colleague" is not much use if it stops at your own shop floor,
# and the fields on it are already limited to what is safe to show widely -
# name, job title, department, photo and WORK email. There is no phone number
# of any kind, because the data model has no work phone field
# (`cell_number` is labelled "Mobile" and is personal).
#
# **What this does NOT change.** The tenant switch still gates the screen
# (`has_feature`), the refusal is still the same sentence whichever the cause,
# and an HR caller still gets their HR scope, which is narrower than a company
# for a store's HR person and wider for a multi-company one. This adds a floor
# for people who had none; it does not widen anybody who already had a scope.
DIRECTORY_SCOPE_FOR_EMPLOYEES = "own_company"

# The Employee field the scope is built from, per option. Named here so the
# constant above cannot select a shape that no query knows how to build.
#
# **A tuple of pairs, not a dict, and that is a rule rather than a style.** A
# module-level dict can be mutated by one request and read by the next - a
# worker serves several sites - so `test_frame_endpoint_registry_034` bans
# every module-level dict, list and set in this file. The first version of this
# was a dict and the guard caught it on the full-suite run. The pairs are
# turned into a lookup inside the function, where the copy is per call.
_SCOPE_FIELDS = (("own_company", "company"), ("own_branch", "branch"))


def _own_scope_filters(user=None):
	"""The directory scope for a caller with **no HR entitlement**.

	Returns a filter dict, or `NO_EMPLOYEES` - **never an empty dict**, which in
	Frappe means everybody (SEC-4, 045 AC-84). The three ways this can fail all
	fail the same way: no Employee record, no company (or no branch) on it, and
	an unknown value in the constant above.

	The caller is not excluded from their own directory. A staff list that hides
	you from yourself is a bug people report.
	"""
	# `import ... as access`, not `from ... import NO_EMPLOYEES`. The repo's
	# integrity check resolves a `from hrms...` import against the functions and
	# classes defined there and cannot see a module-level constant, so the
	# from-import form fails the check even though the name exists. Every other
	# caller in this app uses the module form; this one does too.
	import hrms.alvoraa_hr_core.access as access

	field = dict(_SCOPE_FIELDS).get(DIRECTORY_SCOPE_FOR_EMPLOYEES)
	if not field:
		# Fail closed on a constant somebody has edited to a value no query
		# knows. The alternative - falling back to "own_company" - would hide
		# the typo and ship the wider scope.
		return dict(access.NO_EMPLOYEES)
	emp = frappe.db.get_value(
		"Employee", {"user_id": user or frappe.session.user, "status": "Active"},
		["name", field], as_dict=True)
	if not emp or not emp.get(field):
		return dict(access.NO_EMPLOYEES)
	return {field: emp.get(field)}


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
	the tenant has not been given the feature, the caller cannot be placed in any
	scope, or Guest asked. A caller must not be able to tell those apart - the
	first is a fact about what the company bought, and the rest are facts about
	the caller's own record that a refusal has no business confirming.

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

	# The scope, from the one shared definition. An HR caller gets their HR
	# scope - their companies, narrowed to their branches for a store's HR
	# person - exactly as before.
	filters = access.permitted_employee_filters()
	if filters == access.NO_EMPLOYEES:
		# **045: a caller with no HR entitlement is no longer refused outright.**
		# Until today this line was the end of the road for a plain employee,
		# and the directory was HR-only. Surbhi opened it to employees; the
		# width is `DIRECTORY_SCOPE_FOR_EMPLOYEES`, one constant, above.
		#
		# This is still fail-closed: `_own_scope_filters` returns NO_EMPLOYEES
		# for anybody it cannot place - no Employee record, no company on it -
		# and that is refused below, with the same sentence as every other
		# cause.
		filters = _own_scope_filters()
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
