"""Who may read and who may edit a policy.

A policy is readable when any of its read rules matches the user. HR Managers,
department heads and System Managers read everything. Writing is for the owner
department's head, anyone a write rule names, HR Managers and System Managers.

The same rules are expressed twice: as SQL for list queries (Frappe's
permission_query_conditions) and in Python for one document (has_permission),
so the list and the form never disagree.
"""

import frappe
from frappe.utils import cint

HR_ROLES = {"HR Manager", "HR User"}


def profile(user=None):
	"""What the rules need to know about a user, worked out once per request."""
	user = user or frappe.session.user
	cache = getattr(frappe.local, "policy_profiles", None)
	if cache is None:
		cache = frappe.local.policy_profiles = {}
	if user in cache:
		return cache[user]

	roles = set(frappe.get_roles(user))
	emp = frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		["name", "department", "designation", "branch"],
		as_dict=True,
	) or frappe._dict()
	heads = set()
	if emp.name and frappe.get_meta("Department").has_field("department_head"):
		heads = set(frappe.get_all("Department", filters={"department_head": emp.name}, pluck="name"))
	p = frappe._dict(
		user=user,
		roles=roles,
		employee=emp.name,
		department=emp.department,
		designation=emp.designation,
		branch=emp.branch,
		is_admin=user == "Administrator" or "System Manager" in roles,
		is_hr=bool(roles & HR_ROLES),
		is_hr_manager="HR Manager" in roles,
		is_manager=bool(emp.name and frappe.db.exists("Employee", {"reports_to": emp.name, "status": "Active"})),
		heads=heads,
	)
	p.is_leader = bool(heads) or "Alvoraa CXO" in roles
	p.sees_all = p.is_admin or p.is_hr_manager or p.is_leader
	cache[user] = p
	return p


# ── One rule, one user ──────────────────────────────────────────────────────
def rule_matches(rule, p, owner_department=None):
	t = rule.get("access_type")
	if t == "All Employees":
		return bool(p.employee)
	if t == "Reporting Managers":
		return p.is_manager
	if t == "HR Only":
		return p.is_hr
	if t == "Department Only":
		wanted = rule.get("department") or owner_department
		return bool(p.department) and p.department == wanted
	if t == "Top Leadership":
		return p.is_leader
	if t == "Role":
		return rule.get("role") in p.roles
	if t == "User":
		return rule.get("user") == p.user
	if t == "Designation":
		return bool(p.designation) and rule.get("designation") == p.designation
	if t == "Branch":
		return bool(p.branch) and rule.get("branch") == p.branch
	return False


def can_read(doc, user=None):
	p = profile(user)
	if p.sees_all or can_write(doc, user):
		return True
	if doc.get("status") != "Published":
		return False
	return any(rule_matches(r, p, doc.get("owner_department")) for r in (doc.get("read_access") or []))


def can_write(doc, user=None):
	p = profile(user)
	if p.is_admin or p.is_hr_manager:
		return True
	if doc.get("owner") == p.user and doc.get("__islocal"):
		return True
	dept = doc.get("owner_department")
	if dept and dept in p.heads:
		return True
	if not dept and p.heads:
		return True  # a new policy with no department yet, by a department head
	return any(rule_matches(r, p, dept) for r in (doc.get("write_access") or []))


# ── Frappe hooks ────────────────────────────────────────────────────────────
def has_permission(doc, ptype="read", user=None):
	"""Policy Document has_permission: narrow what the role permissions allow."""
	if ptype in ("read", "print", "email", "report", "export", "share", "select"):
		return can_read(doc, user)
	return can_write(doc, user)


def _rule_sql(p, parentfield, alias="pol"):
	"""SQL that is true when a rule row under `parentfield` matches the user."""
	esc = frappe.db.escape
	yes, no = "1=1", "1=0"
	clauses = [
		f"(r.access_type='All Employees' and {yes if p.employee else no})",
		f"(r.access_type='Reporting Managers' and {yes if p.is_manager else no})",
		f"(r.access_type='HR Only' and {yes if p.is_hr else no})",
		f"(r.access_type='Top Leadership' and {yes if p.is_leader else no})",
		f"(r.access_type='User' and r.user={esc(p.user)})",
	]
	if p.roles:
		clauses.append(f"(r.access_type='Role' and r.role in ({', '.join(esc(x) for x in sorted(p.roles))}))")
	if p.department:
		clauses.append(
			f"(r.access_type='Department Only' and (r.department={esc(p.department)} "
			f"or ((r.department is null or r.department='') and {alias}.owner_department={esc(p.department)})))"
		)
	if p.designation:
		clauses.append(f"(r.access_type='Designation' and r.designation={esc(p.designation)})")
	if p.branch:
		clauses.append(f"(r.access_type='Branch' and r.branch={esc(p.branch)})")
	return (
		f"exists(select 1 from `tabPolicy Access Rule` r where r.parent={alias}.name "
		f"and r.parenttype='Policy Document' and r.parentfield={esc(parentfield)} and ({' or '.join(clauses)}))"
	)


def permission_query_conditions(user=None):
	"""Policy Document list filter for the current user."""
	p = profile(user)
	if p.sees_all:
		return ""
	esc = frappe.db.escape
	readable = f"(`tabPolicy Document`.status='Published' and {_rule_sql(p, 'read_access', '`tabPolicy Document`')})"
	writable = [f"`tabPolicy Document`.owner={esc(p.user)}", _rule_sql(p, "write_access", "`tabPolicy Document`")]
	if p.heads:
		writable.append(f"`tabPolicy Document`.owner_department in ({', '.join(esc(h) for h in sorted(p.heads))})")
	return f"({readable} or {' or '.join(writable)})"


def acknowledgement_query_conditions(user=None):
	"""Employees see their own acknowledgements; HR sees all."""
	p = profile(user)
	if p.is_admin or p.is_hr:
		return ""
	if not p.employee:
		return "1=0"
	return f"`tabPolicy Acknowledgement`.employee={frappe.db.escape(p.employee)}"


def readable_policy_names(user=None, status="Published"):
	"""Names the user may read, through the same query the list uses."""
	filters = {"status": status} if status else {}
	return frappe.get_list("Policy Document", filters=filters, pluck="name", user=user, limit=0)


def cint_flag(v):
	return cint(v)
