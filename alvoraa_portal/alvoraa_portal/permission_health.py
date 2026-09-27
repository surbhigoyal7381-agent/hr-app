"""ALV-127: telling a tenant that a doctype's permissions have stopped moving.

WHAT GOES WRONG, IN ONE PARAGRAPH

Frappe keeps two sets of permission rows. `DocPerm` holds the standard ones that
ship with Frappe HR and arrive with every `bench migrate`. `Custom DocPerm` holds
a tenant's own. From `frappe/permissions.py` in the installed 16.33.1:

    doctypes_with_custom_perms = get_doctypes_with_custom_docperms()
    for p in perms:
        if p.parent not in doctypes_with_custom_perms:
            custom_perms.append(p)          # else the STANDARD rows are ignored

So the moment ONE `Custom DocPerm` row exists for a doctype, that doctype's
standard rows are ignored for ever after. The doctype is frozen.

THREE WAYS IN, AND HOW BADLY EACH ONE BITES

1. THE FREEZE - the common one, and the quiet one. A tenant grants a role in the
   Desk's Role Permissions Manager. That calls `add_permission` ->
   `setup_custom_perms` -> `copy_perms`, which COPIES EVERY STANDARD ROW INTO
   Custom DocPerm FIRST. Nobody loses access that day. But from that day the
   doctype no longer tracks Frappe HR. An upstream permission fix - including a
   security fix - never reaches that tenant, and nothing says so.
   Measured read-only on production on 2026-09-25: `dtc.alvoraa.co` already has
   5 Custom DocPerm rows on `Attendance Request`. Already frozen. Nobody has
   noticed, because nothing is broken yet.

2. THE DELETE. Inside the same manager, removing a row - or "Reset to default",
   which deletes every custom row - does change who can see what, with no
   warning and no log.

3. THE DIRECT INSERT. A single `Custom DocPerm` written by code, a fixture or a
   patch puts the doctype into custom mode holding ONLY that row. Everybody else
   loses access in one statement. `module_access._keep_exempt_row` guards itself
   against exactly this shape.

WHY THIS FILE DETECTS RATHER THAN PREVENTS

A guard would have to fight the tenant's own administration screen. That is the
wrong trade: the Role Permissions Manager is a documented, legitimate Frappe
feature, and a customer using it correctly should not be blocked. So we watch
instead, and we say plainly what changed.

IT IS SAFE TO RUN ON A LIVE TENANT. Every statement here is a read. Nothing is
inserted, updated, deleted or cached. It does not read any employee's data - only
role names and permission flags - so there is nothing personal to leak into its
output or into a log.

HOW TO RUN IT

    bench --site <site> execute alvoraa_portal.permission_health.check_permission_freeze

Run it after ANY permission change made in the Desk. See
`docs/runbooks/permission-freeze-check.md`.
"""

import json

import frappe
from frappe.utils import now_datetime

SENTINEL = "ALVORAA_PERMISSION_FREEZE_JSON "

# The doctypes the employee portal cannot work without, each with the reason it
# is on this list. The reason is here, not in a wiki, because the next person to
# add a row needs to know what earns a place on it: the portal reads or writes
# the doctype on a path an ordinary employee or an HR manager uses every day.
#
# Adding a doctype here is cheap and safe - the check is read-only. Leaving one
# off is what costs, so err towards adding.
WATCHED_DOCTYPES = {
	"Attendance Request": "The attendance corrections queue. Employees raise them, HR decides them.",
	"Leave Application": "Every leave request an employee files and every approval a manager makes.",
	"Attendance": "The daily attendance record the portal's calendar and month view read.",
	"Employee Performance Feedback": "Feedback written about and by a person; the portal's feedback history.",
}

# Roles that OUR OWN INSTALL adds, so finding them is not evidence a tenant did
# anything.
#
# This was measured, not assumed. A site built from scratch on 2026-09-25 -
# `bench new-site` plus erpnext, hrms, alvoraa_goals and alvoraa_portal, never
# opened by a human - already had 5 custom rows on Attendance Request, 5 on
# Attendance and 9 on Leave Application. Four of the five were copies of the
# standard rows, carrying their original 2018 creation date. The fifth was a new
# `Employee Self Service` row created during the install.
#
# The chain, read in the installed source:
#     hrms/setup.py:637 get_user_types_data()   lists Attendance Request,
#         Leave Application and others for the Employee Self Service user type
#     hrms/setup.py:693 create_user_type()      saves the User Type
#     frappe/core/doctype/user_type/user_type.py:161  add_permission(doctype, role, 0)
#         -> setup_custom_perms -> copy_perms
#
# So THREE OF THE FOUR WATCHED DOCTYPES ARE BORN FROZEN ON EVERY SITE WE BUILD.
# The 5 rows found on `dtc.alvoraa.co` on 2026-09-25 are that install, not a
# tenant's administrator. `Employee Performance Feedback` has 0 rows because it
# is not on Frappe HR's ESS list - which is exactly what production showed.
#
# That is why the check separates the two. A freeze that matches the install is
# normal and needs no one's attention; a freeze that goes beyond it means
# somebody changed something, and that is worth a look.
INSTALL_ADDED_ROLES = frozenset({"Employee Self Service"})

# The two roles whose disappearance means the portal is broken for real people.
# `Employee` is every logged-in member of staff. `HR Manager` is the person who
# runs the queue. If either loses read on a watched doctype, somebody's day has
# stopped working and nobody has been told.
REQUIRED_ROLES = ("Employee", "HR Manager")

# Frappe evaluates document-level access at permlevel 0. Higher permlevels guard
# individual fields, which is a different question from "can this person open the
# record at all", so the row test below is deliberately fixed at 0.
DOCUMENT_PERMLEVEL = 0

# Four states, worst last. `expected` exists so the check is not red on every
# healthy site - a check that is always red is a check nobody reads.
_OK = "ok"
_EXPECTED = "frozen_at_install"
_FROZEN = "frozen"
_BROKEN = "broken"


def check_permission_freeze(as_json=False, print_report=True):
	"""Report which watched doctypes have stopped tracking Frappe HR's permissions.

	Reads only. Returns a dict, and prints a report a human can act on.

	Raises if it managed to read nothing. A check that says "OK" having looked at
	no rows is indistinguishable from a clean result, and that has fooled this
	programme before. So the count of what was read is part of the answer.
	"""
	watched = sorted(WATCHED_DOCTYPES)
	# Checked before the queries, not after: an empty `in (...)` filter is a SQL
	# error, and an empty watch list is a bug worth naming in plain words rather
	# than a database message.
	if not watched:
		frappe.throw(
			"Permission freeze check examined no doctypes. WATCHED_DOCTYPES is empty, "
			"so this check proves nothing."
		)

	custom_by_doctype = _rows("Custom DocPerm", watched)
	standard_by_doctype = _rows("DocPerm", watched)

	findings = []
	for doctype in watched:
		findings.append(
			_examine(
				doctype,
				custom_by_doctype.get(doctype, []),
				standard_by_doctype.get(doctype, []),
			)
		)

	read_counts = {
		"doctypes_examined": len(findings),
		"custom_docperm_rows_read": sum(len(v) for v in custom_by_doctype.values()),
		"standard_docperm_rows_read": sum(len(v) for v in standard_by_doctype.values()),
	}
	_assert_it_actually_read_something(read_counts)

	result = {
		"site": frappe.local.site,
		"checked_at": str(now_datetime()),
		"read": read_counts,
		"worst": _worst(findings),
		"findings": findings,
	}
	# `bench execute` is the normal caller and a human reads its output, so the
	# report prints by default. Tests turn it off - fifteen copies of it buries
	# the one line that says which test failed.
	if print_report:
		print(_report(result))
		print(SENTINEL + json.dumps(result, default=str))
	return json.dumps(result, default=str) if as_json else result


def _rows(doctype, watched):
	"""All permission rows for the watched doctypes, grouped by doctype.

	One query per table for the whole list, not one per doctype - the list will
	grow and a per-doctype loop would grow with it.
	"""
	out = {}
	rows = frappe.get_all(
		doctype,
		filters={"parent": ["in", watched]},
		fields=["parent", "role", "permlevel", "if_owner", "read", "write", "create", "delete"],
		limit_page_length=0,
	)
	for row in rows:
		out.setdefault(row.parent, []).append(row)
	return out


def _examine(doctype, custom_rows, standard_rows):
	# Every finding carries the same keys whatever its status, so a caller never
	# has to test for a missing one.
	finding = {
		"doctype": doctype,
		"why_watched": WATCHED_DOCTYPES[doctype],
		"custom_rows": len(custom_rows),
		"standard_rows": len(standard_rows),
		"missing_required_roles": [],
		"roles_lost_against_standard": [],
		"roles_added_against_standard": [],
		"roles_added_beyond_install": [],
	}

	# An unknown doctype is an ERROR, never a quiet skip. If somebody renames a
	# doctype, or an app stops being installed, the portal breaks and this check
	# must not answer "all clear" because it found nothing to look at.
	if not frappe.db.exists("DocType", doctype):
		finding["status"] = _BROKEN
		finding["problems"] = [
			f"{doctype} is not installed on this site, so the portal paths that use it cannot work."
		]
		finding["action"] = "Find out which app stopped being installed. Do not edit permissions."
		return finding

	if not custom_rows:
		finding["status"] = _OK
		finding["problems"] = []
		finding["action"] = "Nothing to do. This doctype still follows Frappe HR's own permissions."
		return finding

	# Custom rows exist, so this doctype is frozen: Frappe now ignores every
	# standard row on it, today and after every future migrate.
	missing_required = [
		role for role in REQUIRED_ROLES if not _has_document_read(custom_rows, role)
	]
	lost_since_standard = sorted(
		{
			row.role
			for row in standard_rows
			if _is_document_read(row) and not _has_document_read(custom_rows, row.role)
		}
		- set(missing_required)
	)

	# Roles that have a row here and no standard row - somebody granted them.
	added_since_standard = sorted(
		{row.role for row in custom_rows} - {row.role for row in standard_rows}
	)
	beyond_install = sorted(set(added_since_standard) - INSTALL_ADDED_ROLES)

	problems = [
		"Frozen. Custom permissions are in force, so Frappe HR's standard rows are "
		"ignored here - now and after every future upgrade. Any upstream permission "
		"fix will not reach this site until somebody applies it by hand."
	]
	for role in missing_required:
		problems.append(
			f"{role} has NO read row at permlevel {DOCUMENT_PERMLEVEL}. "
			f"People holding that role cannot open any {doctype} record at all."
		)
	if lost_since_standard:
		problems.append(
			"These roles read this doctype in Frappe HR's standard rows but have no "
			"read row here: " + ", ".join(lost_since_standard) + "."
		)
	if beyond_install:
		problems.append(
			"Somebody granted roles this doctype does not ship with: "
			+ ", ".join(beyond_install)
			+ ". That is allowed, and worth knowing about."
		)

	finding["missing_required_roles"] = missing_required
	finding["roles_lost_against_standard"] = lost_since_standard
	finding["roles_added_against_standard"] = added_since_standard
	finding["roles_added_beyond_install"] = beyond_install

	if missing_required:
		finding["status"] = _BROKEN
		finding["problems"] = problems
		finding["action"] = (
			f"Put the missing role back. In the Desk open Role Permissions Manager for "
			f"{doctype}, add a row for each of: {', '.join(missing_required)}, with Read ticked."
		)
	elif lost_since_standard or beyond_install:
		finding["status"] = _FROZEN
		finding["problems"] = problems
		finding["action"] = (
			"Check the change was intended, then record it. This doctype no longer "
			"tracks Frappe HR, so re-check it by hand whenever Frappe HR changes its "
			"permissions upstream."
		)
	else:
		# Frozen, but only in the way every site we build is frozen.
		finding["status"] = _EXPECTED
		finding["problems"] = [
			"Frozen, but by our own install, not by anybody here. Frappe HR's Employee "
			"Self Service user type calls add_permission on this doctype, which copies "
			"the standard rows in. Every site we build looks like this. Nobody has lost "
			"anything, and no tenant has changed anything."
		]
		finding["action"] = (
			"Nothing to do. Worth remembering that upstream permission changes to this "
			"doctype will not arrive by themselves on any of our sites."
		)
	return finding


def _is_document_read(row):
	return bool(row.read) and int(row.permlevel or 0) == DOCUMENT_PERMLEVEL


def _has_document_read(rows, role):
	"""Does this role get read on the whole doctype, not only its own records?

	`if_owner` rows are deliberately not counted. A row with `if_owner` set grants
	read only on documents the user created, which is a narrower thing than the
	role having read. Counting it would let a real loss of access pass as healthy.
	"""
	return any(
		row.role == role and _is_document_read(row) and not row.if_owner for row in rows
	)


def _worst(findings):
	statuses = {f["status"] for f in findings}
	for status in (_BROKEN, _FROZEN, _EXPECTED):
		if status in statuses:
			return status
	return _OK


def _assert_it_actually_read_something(read_counts):
	"""Refuse to report health when nothing was read.

	A check that prints OK having read nothing looks exactly like a clean site.
	This has cost this programme real time, so the failure is loud.
	"""
	if not read_counts["doctypes_examined"]:
		frappe.throw(
			"Permission freeze check examined no doctypes. WATCHED_DOCTYPES is empty, "
			"so this check proves nothing."
		)
	if not read_counts["standard_docperm_rows_read"]:
		frappe.throw(
			"Permission freeze check read 0 standard DocPerm rows across "
			f"{read_counts['doctypes_examined']} doctypes. That is not a healthy site, it "
			"is a check that cannot see the table it needs. Do not read its result as OK."
		)


def _report(result):
	headline = {
		_OK: "OK - every watched doctype still follows Frappe HR's own permissions.",
		_EXPECTED: (
			"EXPECTED - the only freeze found is the one our own install creates. "
			"Nobody here has changed anything."
		),
		_FROZEN: "CHANGED - a watched doctype's permissions have been altered beyond the install.",
		_BROKEN: "BROKEN - a role that people need has lost read on a watched doctype.",
	}[result["worst"]]

	read = result["read"]
	lines = [
		"",
		f"Permission freeze check - {result['site']} - {result['checked_at']}",
		headline,
		(
			f"Read {read['doctypes_examined']} doctypes, "
			f"{read['standard_docperm_rows_read']} standard permission rows and "
			f"{read['custom_docperm_rows_read']} custom permission rows."
		),
		"",
	]
	for finding in result["findings"]:
		lines.append(
			f"[{finding['status'].upper()}] {finding['doctype']} "
			f"({finding['custom_rows']} custom / {finding['standard_rows']} standard rows)"
		)
		lines.append(f"    Watched because: {finding['why_watched']}")
		for problem in finding["problems"]:
			lines.append(f"    - {problem}")
		lines.append(f"    Next: {finding['action']}")
		lines.append("")
	return "\n".join(lines)
