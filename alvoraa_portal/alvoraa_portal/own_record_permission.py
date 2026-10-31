"""Every staff login is limited to its own Employee record (ALV-249, ALV-261).

WHY. ERPNext gives the Employee role read on every Employee row and expects each
login to carry one User Permission on its own Employee record, "all document
types". ERPNext's controller only makes that row when the Employee is saved with
`create_user_permission` ticked; our account script links logins with
`frappe.db.set_value`, so no login at DTC had one. Every staff login could list
every employee's date of birth, phone and address, and every expense claim.

THE RULE. The row exists when the login is enabled, is the `user_id` of an
Employee, and holds no excluded role. Otherwise it does not. Only rows of this
exact shape are ever written or removed: allow Employee, `for_value` = that
login's own Employee, all document types. A narrow row (manager_scope.py) or a
row on somebody else's record is never touched.

EXCLUDED ROLES. Every role that reads Employee in this site's own permissions,
except Employee and Employee Self Service, plus System Manager and Administrator
by name. By name because a site may give System Manager no read row on
Employee at all (found on the test site, 31 Oct 2026): computing it from the
permissions alone would have put the row on System Managers. A row restricts;
it never grants (ALV-226: three HR Managers were cut off by one).

A LEAVER loses the row because ERPNext disables the login of any employee who is
not Active (employee.py, validate_for_enabled_user_id), and a disabled login gets
no row. If somebody re-enables that login by hand, the row comes back: an enabled
login without it would see every record, so status is deliberately not checked.

A MANAGER sees their own record and everyone below them: Employee is a tree,
and Frappe extends an own-record row to the tree unless "hide descendants" is
set. That is ERPNext's standard behaviour, chosen on 31 Oct 2026 (D-2).

WHY A BYPASS. Only System Manager may write User Permission, and these run
when HR saves an Employee or a User. The two writes below are the only ones.

OWNER. A row made at sign-in shows "Guest" as its owner: Frappe runs on_login
before the session exists. A row made by a save shows the person who saved.
"""

import hashlib
import json
import os

import frappe
from frappe.utils import get_datetime

ALLOW = "Employee"
SELF_SERVICE = {"Employee", "Employee Self Service"}
ALWAYS_EXCLUDED = {"System Manager", "Administrator"}
# Roles that are expected on a staff login; any other one is listed in the dry run.
EXPECTED = SELF_SERVICE | {"Leave Approver", "Expense Approver", "All", "Guest", "Desk User"}


def excluded_roles():
	"""Roles whose holders never get the row."""
	readers = {p.role for p in frappe.get_meta(ALLOW).permissions
	           if p.read and not p.permlevel and not p.if_owner}
	return (readers - SELF_SERVICE) | ALWAYS_EXCLUDED


def _due(user, excluded):
	if user in ("Administrator", "Guest"):
		return False
	if not frappe.db.get_value("User", user, "enabled"):
		return False
	return not (set(frappe.get_roles(user)) & excluded)


def _rows(user, employee):
	return frappe.get_all("User Permission", filters={
		"user": user, "allow": ALLOW, "for_value": employee,
		"apply_to_all_doctypes": 1}, pluck="name")


def _delete(names):
	for name in names:
		frappe.delete_doc("User Permission", name, force=True, ignore_permissions=True)


def _remove(user, employee):
	_delete(_rows(user, employee))


def sync(user, employee, excluded=None):
	"""Make the one row for this login and its own Employee right. Safe to run twice.

	Returns "added", "removed" or None.
	"""
	excluded = excluded_roles() if excluded is None else excluded
	have = _rows(user, employee)
	if _due(user, excluded):
		if have:
			return None
		frappe.get_doc({"doctype": "User Permission", "user": user, "allow": ALLOW,
		                "for_value": employee, "apply_to_all_doctypes": 1}
		               ).insert(ignore_permissions=True)
		return "added"
	if have:
		_remove(user, employee)
		return "removed"
	return None


def on_employee_update(doc, method=None):
	"""Employee on_update: a login linked, unlinked or swapped."""
	before = doc.get_doc_before_save()
	if before and before.user_id and before.user_id != doc.user_id:
		_remove(before.user_id, doc.name)
	if doc.user_id:
		sync(doc.user_id, doc.name)


def sync_user(user):
	"""Every Employee this login is linked to. The account script calls this after
	it links logins with frappe.db.set_value, which runs no hook (D-3)."""
	excluded = excluded_roles()
	for employee in frappe.get_all("Employee", filters={"user_id": user}, pluck="name"):
		sync(user, employee, excluded)


def on_user_update(doc, method=None):
	"""User on_update: roles changed (a promotion to HR), or the login disabled."""
	sync_user(doc.name)


def on_login(login_manager):
	"""on_login: catches every login linked by a direct database write, and every
	role whose Employee read was changed in Role Permission Manager since the
	login's last save, before the session is handed back.

	Never blocks a sign-in. On any error the person gets in without the row (the
	state before this change), and one short Error Log line says so: a hash of the
	login and the error's type, no name, no email, no traceback."""
	try:
		sync_user(login_manager.user)
	except Exception as e:
		user = str(getattr(login_manager, "user", ""))
		frappe.log_error(title="ALV-249 own-record sync skipped at sign-in",
		                 message="login sha1:%s error %s" % (
		                     hashlib.sha1(user.encode()).hexdigest()[:12], type(e).__name__))


# ── The one-off run on a live tenant (ALV-249 step 3). Never run by migrate. ──

def _linked():
	return frappe.get_all("Employee", filters={"user_id": ("is", "set")},
	                      fields=["name", "user_id", "lft", "rgt"], limit_page_length=0)


def _own_rows(linked):
	own = {(e.user_id, e.name) for e in linked}
	rows = frappe.get_all("User Permission", filters={"allow": ALLOW, "apply_to_all_doctypes": 1},
	                      fields=["name", "user", "for_value", "creation"], limit_page_length=0)
	return [r for r in rows if (r.user, r.for_value) in own]


def _counts_as(user):
	"""What this login can list now, through Frappe's own permission layer."""
	frappe.set_user(user)
	try:
		return {"employee": len(frappe.get_list(ALLOW, limit_page_length=0)),
		        "employee_ref_todo": len(frappe.get_list(ALLOW, limit_page_length=0, reference_doctype="ToDo")),
		        "claims": len(frappe.get_list("Expense Claim", limit_page_length=0))}
	finally:
		frappe.set_user("Administrator")


def _expected(employee):
	"""1 + everyone below them, and the claims of those people plus claims shared with them."""
	tree = frappe.get_all(ALLOW, filters={"lft": (">=", employee.lft), "rgt": ("<=", employee.rgt)},
	                      pluck="name", limit_page_length=0)
	claims = set(frappe.get_all("Expense Claim", filters={"employee": ("in", tree)}, pluck="name",
	                            limit_page_length=0))
	claims |= set(frappe.get_all("DocShare", filters={"share_doctype": "Expense Claim", "user": employee.user_id,
	                                                   "read": 1}, pluck="share_name"))
	return {"employee": len(tree), "employee_ref_todo": len(tree), "claims": len(claims)}


def _before_file():
	return frappe.get_site_path("alv249_rows_before.json")


def save_existing_rows(deployed_at):
	"""Run once per tenant, right after the deploy: save the own-record rows that
	existed before the deploy, so rollback() can leave exactly those.

	deployed_at: the deploy time from the deploy log, in the site's time zone.
	Rows created after it were made by this change (sign-in, saves, run_once).
	Why a time and not a list taken at once: sign-ins start the moment the code is
	live, and a User Permission has no spare field to mark ours with."""
	if frappe.session.user != "Administrator":
		frappe.throw("Run as Administrator.", frappe.PermissionError)
	cutoff = get_datetime(deployed_at)
	names = sorted(r.name for r in _own_rows(_linked()) if r.creation < cutoff)
	deployed_at = str(cutoff)
	with open(_before_file(), "w") as f:
		json.dump({"deployed_at": deployed_at, "names": names}, f)
	print("saved", len(names), "rows that existed before", deployed_at, "to", _before_file())
	return len(names)


def run_once(dry_run=1, samples=None):
	"""Give every due login its row, with counts before and after. Run as Administrator.

	dry_run=1 writes nothing: it prints the excluded roles, the number due, and every
	login that would get the row while holding a role outside the expected staff
	roles, for a person to read first. dry_run=0 writes, then prints PASS or FAIL
	for every check. Each check compares against a number worked out separately,
	so one dropped login cannot hide behind a total.

	samples: staff logins to check one by one (default: the first three due).
	Returns the number of FAIL lines.
	"""
	if frappe.session.user != "Administrator":
		frappe.throw("Run as Administrator.", frappe.PermissionError)
	dry_run = int(dry_run)
	excluded = excluded_roles()
	linked = _linked()
	due = [e for e in linked if _due(e.user_id, excluded)]
	due_users = {e.user_id for e in due}
	not_due = [e for e in linked if e.user_id not in due_users]
	print("excluded roles:", ", ".join(sorted(excluded)))
	print("logins due a row (N):", len(due))
	for e in due:
		extra = set(frappe.get_roles(e.user_id)) - EXPECTED
		if extra:
			print("  check by hand:", e.user_id, e.name, "also holds", ", ".join(sorted(extra)))
	rows = _own_rows(linked)
	print("BEFORE own-record rows:", len(rows),
	      "| on excluded or disabled logins:", sum(1 for r in rows if r.user not in due_users))

	sample_users = list(samples or [e.user_id for e in due[:3]])
	by_user = {e.user_id: e for e in linked}
	other = sorted({e.user_id for e in not_due if frappe.db.get_value("User", e.user_id, "enabled")})
	before_other = {u: _counts_as(u) for u in other}
	for u in sample_users:
		print("BEFORE", u, _counts_as(u))
	for u in other:
		print("BEFORE (no row)", u, before_other[u])
	print("rollback list:", _before_file() if os.path.exists(_before_file()) else
	      "MISSING - run save_existing_rows(deployed_at=<deploy time>) before the real run")
	if dry_run:
		print("dry run: nothing written")
		return 0

	before_names = {r.name for r in rows}
	removed = sum(sync(e.user_id, e.name, excluded) == "removed" for e in linked)
	print("added", len({r.name for r in _own_rows(linked)} - before_names), "removed", removed)

	fails = 0

	def check(label, ok, detail=""):
		nonlocal fails
		fails += not ok
		print(("PASS " if ok else "FAIL ") + label, detail)

	rows = _own_rows(linked)
	check("rows = N", len(rows) == len(due), f"{len(rows)} vs {len(due)}")
	check("0 rows on excluded or disabled logins", not [r for r in rows if r.user not in due_users])
	missing = sorted(due_users - {r.user for r in rows})
	check("every due login has its row", not missing, ", ".join(missing))
	for u in sample_users:
		got, want = _counts_as(u), _expected(by_user[u])
		check(f"sample {u}", got == want, f"got {got} want {want}")
	for u in other:
		got = _counts_as(u)
		check(f"unchanged {u}", got == before_other[u], f"got {got} before {before_other[u]}")
	return fails


def rollback(force=0):
	"""Remove every own-record row on a linked login except those saved by
	save_existing_rows(): run_once's, the sign-in hook's and the save hooks'.
	Refuses without the saved list; force=1 removes every own-record row (right
	only where there were none before, as at DTC on 31 Oct 2026).
	Revert the code first, or the hooks add rows back on the next save or sign-in."""
	if frappe.session.user != "Administrator":
		frappe.throw("Run as Administrator.", frappe.PermissionError)
	keep = set()
	if os.path.exists(_before_file()):
		with open(_before_file()) as f:
			keep = set(json.load(f)["names"])
	elif not int(force):
		frappe.throw("No list of rows from before the deploy; nothing removed. Run "
		             "save_existing_rows, or pass force=1 if there were none.", frappe.ValidationError)
	gone = [r.name for r in _own_rows(_linked()) if r.name not in keep]
	_delete(gone)
	print("removed", len(gone), "kept", len(keep))
	return len(gone)
