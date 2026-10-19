"""A manager may act for the people who report to them, and for nobody else.

THE PROBLEM THIS SOLVES. Frappe HR gives every login a User Permission tying
it to its own Employee record, so a document naming anybody else is refused.
That rule is right - it is what stops an ordinary employee touching a
colleague's attendance - and it knows nothing about reporting lines. It
therefore refuses the one thing a manager is entitled to do: raise a correction
for somebody on their team.

THE WRONG FIX, which was written first and caught by a test. Calling
`insert(ignore_permissions=True)` after checking the reporting line in our own
code. It works, and it moves the permission decision out of the data and into a
line of Python nobody can audit. `NoQuietBypass.test_this_module_never_ignores_
permissions` exists precisely to stop that spreading, and it did its job.

THE FIX. Say it in the permission system instead: one User Permission per
manager, per report, per doctype. Frappe then allows the request natively,
because the manager genuinely IS permitted. HR can list who may act for whom;
an auditor can read it without reading code; and it disappears when the
reporting line does.

SCOPED TO FOUR DOCTYPES, NEVER "all document types". That distinction is the
whole safety of this. A blanket permission would scope the manager to their
reports EVERYWHERE - and the `Employee` role can read Salary Slip, so a
blanket grant would hand every manager their team's payslips as a side effect
of a correction workflow. Each permission here names one doctype and reaches
no further.

`Employee` IS DELIBERATELY NOT ON THE LIST. A manager needs a report's name,
branch and shift to read the screen, and those already arrive through
`attendance_correction.team_days`, which decides permission explicitly and
returns only those fields. Granting `Employee` would additionally expose date
of birth and everything else on the record, to solve a problem that is already
solved.
"""

import frappe

# What a manager must reach to review a day and ask for it to be fixed.
# Deliberately short. Adding to it is a decision about what a manager may see,
# not a convenience - see the module docstring on what is left out and why.
SCOPED_DOCTYPES = (
	"Attendance",            # the day itself
	"Employee Checkin",      # the punches behind it
	"Attendance Request",    # raising the correction
	"Leave Application",     # raising and approving leave
)

ALLOW = "Employee"


def _user_of(employee):
	return frappe.db.get_value("Employee", employee, "user_id")


def grant(manager_employee, report_employee):
	"""Let one manager act for one report, on the four doctypes above.

	Runs by itself: a permission that already exists is left alone, so this can
	be called on every save of an Employee without piling up duplicates.
	"""
	user = _user_of(manager_employee)
	if not user or not report_employee:
		return 0
	made = 0
	for dt in SCOPED_DOCTYPES:
		if frappe.db.exists("User Permission", {
				"user": user, "allow": ALLOW, "for_value": report_employee,
				"applicable_for": dt}):
			continue
		doc = frappe.get_doc({
			"doctype": "User Permission",
			"user": user,
			"allow": ALLOW,
			"for_value": report_employee,
			# NOT apply_to_all_doctypes. See the module docstring: a blanket
			# grant would reach Salary Slip.
			"apply_to_all_doctypes": 0,
			"applicable_for": dt,
		})
		doc.flags.ignore_permissions = True
		doc.insert()
		made += 1
	return made


def revoke(manager_employee, report_employee):
	"""Take it back when somebody stops reporting to them.

	Only the permissions this module creates: `applicable_for` is always set
	here, so a blanket permission somebody made by hand is never deleted by a
	reporting-line change.
	"""
	user = _user_of(manager_employee)
	if not user or not report_employee:
		return 0
	gone = 0
	for name in frappe.get_all("User Permission", filters={
			"user": user, "allow": ALLOW, "for_value": report_employee,
			"applicable_for": ("in", SCOPED_DOCTYPES)}, pluck="name"):
		frappe.delete_doc("User Permission", name, force=True,
		                  ignore_permissions=True)
		gone += 1
	return gone


def sync_for_manager(manager_employee):
	"""Make the permissions match who reports to this manager right now.

	Grants what is missing and removes what no longer belongs. This is what
	makes a reporting-line change self-correcting rather than something
	somebody has to remember.

	DIRECT REPORTS ONLY, not the whole tree. A manager two levels up reviews
	their own reports, who review theirs. Granting the whole subtree would give
	a regional head every punch in the region, which is a different decision
	from the one taken here.
	"""
	user = _user_of(manager_employee)
	if not user:
		return {"granted": 0, "revoked": 0}

	should = set(frappe.get_all("Employee",
	                            filters={"reports_to": manager_employee,
	                                     "status": "Active"},
	                            pluck="name", limit_page_length=0))
	have = set(frappe.get_all("User Permission",
	                          filters={"user": user, "allow": ALLOW,
	                                   "applicable_for": ("in", SCOPED_DOCTYPES)},
	                          pluck="for_value", limit_page_length=0))

	granted = sum(grant(manager_employee, e) for e in (should - have))
	revoked = sum(revoke(manager_employee, e) for e in (have - should))
	return {"granted": granted, "revoked": revoked}


def on_employee_update(doc, method=None):
	"""Keep both managers in step when somebody's reporting line moves.

	The OLD manager loses them and the NEW one gains them, in the same save, so
	there is never a moment where a reporting line and its permissions
	disagree. Frappe hands us the previous values in `doc.get_doc_before_save`.
	"""
	before = doc.get_doc_before_save()
	old = before.reports_to if before else None
	new = doc.reports_to

	if old == new and (not before or before.status == doc.status):
		return
	if old and old != new:
		revoke(old, doc.name)
	if new:
		if doc.status == "Active":
			grant(new, doc.name)
		else:
			# Left the company, or suspended: the line may still read the same
			# but there is nothing for a manager to act on.
			revoke(new, doc.name)


def after_migrate():
	"""Bring every manager's permissions in line with the reporting lines.

	The hook above keeps things right from here on; this is for the lines that
	already existed when the feature arrived, and for any that drifted because
	somebody edited `reports_to` with a direct database write.

	Quiet by design. A permission sync must never be the thing that fails a
	migrate.
	"""
	try:
		managers = {m for m in frappe.get_all(
			"Employee", filters={"reports_to": ("is", "set"), "status": "Active"},
			pluck="reports_to", limit_page_length=0) if m}
		total = {"granted": 0, "revoked": 0}
		for m in managers:
			out = sync_for_manager(m)
			total["granted"] += out["granted"]
			total["revoked"] += out["revoked"]
		if total["granted"] or total["revoked"]:
			frappe.db.commit()
			print("  manager scope: %d granted, %d revoked across %d manager(s)"
			      % (total["granted"], total["revoked"], len(managers)))
	except Exception:
		frappe.log_error(title="manager_scope: could not sync manager permissions")
