"""Slice 034, Wave 1: one honest number for what is waiting on this person.

The frame draws a bell, an Inbox menu entry and (for some personas) an Inbox
button on the bottom bar. All three show the same total, and that total is this
module's whole job. **Counts only.** The Inbox *list* - the rows a person can
act on - is Wave 2 (spec section 12), and this file is deliberately written so
that Wave 2 extends it rather than replaces it.

Section 5 of the spec sets the six parts and one rule above all others:

    **Count only what the portal can act on today.**

Expense claims to approve and salary advances are not counted, because the
portal has no screen on which to approve one. A number that sends somebody
looking for a button that does not exist is worse than no number.

Three rules govern this module, each with a test that fails if it is broken.

**A count must equal the list it links to (AC-51).** Not "about equal". Every
part below is counted with the *same definition* the screen uses, and where a
screen is capped the count is not - it is the true total, and the screen says
"showing the first 50 of 60" rather than quietly showing fewer. Where a
definition lives somewhere else, this module calls that code rather than
copying it, so the two cannot drift apart. The one place that could not be
reused is named in `_attendance_fixes`, with the reason.

**Nobody gets an error instead of a count (AC-63).** A platform operator with
no Employee record, and a leaver whose login still works, get their own empty
parts and a total of zero. Today's helpers throw "No Employee record found";
the frame would then show the page-error state to somebody who has done nothing
wrong.

**No `ignore_permissions`, and no module-level state that changes at run time**
(SEC-6 / AC-71, SEC-15 / AC-70). Every constant here is a tuple. One worker
serves several sites.

Guest is refused, and the refusal is the decorator plus an explicit line, the
same belt-and-braces as `frame_api.get_frame` (SEC-2). Every function here is
live on production from the release that carries it, whatever page calls it, so
the Guest, wrong-persona and scope tests ship in the same commit.
"""

import frappe
from frappe import _
from frappe.utils import get_build_version

# The parts, in the order the Inbox page lists them. Section 5's table, and the
# routes are section 4's. A tuple of tuples: nothing here is appended to at run
# time (SEC-15).
#
# `my_requests` is the one route that is not a single screen in section 5 - it
# says "the screen each came from", which is per item and is the Wave 2 Inbox
# list's job. Wave 1 sends it to `#time`, where all three kinds (leave,
# attendance fixes and shift changes) are listed today. Named here rather than
# left to be discovered.
PARTS = (
	("leave_approvals", "#team"),
	("goal_updates", "#growth"),
	("attendance_fixes", "#time/fix"),
	("shift_requests", "#time/shift"),
	("policies", "#company/policies"),
	("my_requests", "#time"),
)

# Which parts add up to "approvals waiting". AC-20's total is
# approvals + policies + my own open requests, so the three groups are named
# rather than left as an arithmetic accident in one line.
APPROVAL_PARTS = ("leave_approvals", "goal_updates", "attendance_fixes", "shift_requests")

# The attendance corrections screen reads at most this many rows
# (`attendance_correction.to_review`'s default). The COUNT is not capped - see
# `_attendance_fixes` - but the screen needs to know the cap so it can say
# "showing the first 50 of 60" (section 5, security note N3).
CORRECTIONS_CAP = 50



def _has_doctype(name):
	"""Is this doctype on the site, asked once per site per release?

	Three parts of this call are guarded by "does this doctype exist" - KPI,
	Shift Request and Policy Document - because a bench without the goals app
	or the policy library must not throw. Asked directly that is three database
	queries on a call whose whole job is to be cheap, and the answer changes
	only at a migration, which clears this cache.

	The build version is in the key (review finding F8, 2026-09-24). A migration
	clears the cache and so does a deploy, so the normal path was already safe -
	but the path that skips both is one this project uses: copying a file onto a
	running container changes nothing for up to a day. With the version in the
	key, a new build cannot read the last build's answer. If the goals app is
	installed on a live tenant and nothing clears the cache, the Inbox would
	otherwise count KPI approvals as zero until tomorrow.
	"""
	key = "inbox_api:doctype:%s:%s" % (get_build_version(), name)
	seen = frappe.cache().get_value(key)
	if seen is None:
		seen = 1 if frappe.db.exists("DocType", name) else 0
		frappe.cache().set_value(key, seen, expires_in_sec=24 * 60 * 60)
	return bool(seen)


def _zero():
	"""Every part at zero. What a person with no Employee record gets (AC-63)."""
	return {key: 0 for key, _route in PARTS}


def _my_employee(user):
	"""The caller's own ACTIVE Employee record id, or None.

	The same "who am I" question `frame_api._me` asks, and the same answer, so
	the bell and the menu cannot describe two different people. None is a real
	answer here, not a failure: a platform operator never had an Employee
	record, and a leaver's is no longer Active (SEC-14).
	"""
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def _leave_approvals(user):
	"""Leave applications waiting on this person as the named approver.

	The same filter `hr_api.get_manager_dashboard` uses for the list it shows,
	minus the fields - a count needs no names. Anybody can be named as a leave
	approver, so there is no role test here and there should not be one.
	"""
	return frappe.db.count(
		"Leave Application",
		{"leave_approver": user, "status": "Open", "docstatus": 0},
	)


def _goal_updates():
	"""KPI and goal progress updates this caller may approve.

	`goals_api.get_pending_approvals_count` is called rather than copied: it
	already holds `_pending_approvals_scope`, which is the definition of who a
	manager or an HR person may approve for, and PRIV-4 forbids the boot path
	from calling the heavy `get_pending_approvals` instead.

	It throws for a caller with no Employee record, which is correct for the
	screen and wrong for a count (AC-63), so that one case is turned into zero
	here. Nothing else is caught: a real fault must reach the caller as the
	card-error state, not be quietly rendered as "nothing waiting".
	"""
	if not _has_doctype("KPI"):
		return 0
	from alvoraa_portal.goals_api import get_pending_approvals_count

	try:
		return int((get_pending_approvals_count() or {}).get("total") or 0)
	except frappe.PermissionError:
		# `_require_employee` raises this when the caller has no Employee
		# record. Rule 6's personas have nobody to approve for by definition.
		return 0


def _attendance_fixes(user, employee):
	"""Attendance corrections waiting for this caller to decide.

	Two things make this the most delicate count in the file.

	**Who may see it is not a role.** `attendance_correction._may_review` tests
	the submit permission on Attendance Request, so a tenant can hand this queue
	to a Shift Supervisor. That function is called, not re-implemented (W1D-14,
	AC-52's fourth row).

	**The scope differs by caller, on purpose.** For an HR caller the queue is
	`permitted_employees()` minus themselves (W1D-05), so a store's HR person
	counts their store. For a reviewer who is not HR the scope is exactly what
	they see today - no narrowing at all - because applying an HR filter to
	somebody who holds no HR entitlement returns the empty set and kills a
	working flow silently (W1D-14).

	**The count is not capped, and the screen is.** `to_review` reads 50 rows.
	This counts every waiting row in the caller's scope, so the bell can say 60
	while the screen shows 50 and says so. A count that stopped at 50 could not
	be added into AC-20's single honest total.

	Returns (count, is_hr_scope) - the second so the Inbox page knows which
	sentence to draw when the count is above the cap.
	"""
	from alvoraa_portal.attendance_correction import REQUEST, _may_review, review_queue_filters

	if not _may_review():
		return 0, False

	# The queue's own filters, not a copy of them. `to_review` builds its list
	# from this exact dict; the only difference here is that no cap is applied,
	# so the number is the true total (section 5, N3).
	filters, is_hr_scope = review_queue_filters(user)

	# `get_list`, not `get_all`: the caller's own permissions apply, exactly as
	# they do on the screen. A tenant that has scoped Attendance Request by
	# department gets that scoping in the count too.
	rows = frappe.get_list(REQUEST, filters=filters, pluck="name", limit_page_length=0)
	return len(rows), is_hr_scope


def _shift_requests(user):
	"""Shift changes waiting on this person as the named approver."""
	if not _has_doctype("Shift Request"):
		return 0
	return frappe.db.count("Shift Request", {"approver": user, "docstatus": 0})


def _policies(employee):
	"""Policies this person may read and has not acknowledged for its version.

	The same answer `hr_api.get_my_policies()["pending"]` gives, in two queries
	instead of one per policy. The definition is
	`policy_document.acknowledgement_status`: a policy needs acknowledging when
	it is set to be acknowledged on joining or on a new version, and it is done
	when there is an acknowledgement for the policy AND its current version.
	`test_inbox_counts_034` asserts this number equals `get_my_policies`'s, so
	the faster shape cannot quietly mean something else.
	"""
	if not employee or not _has_doctype("Policy Document"):
		return 0
	# `get_list`, so this is what the caller may READ - the same set
	# `readable_policy_names` returns, through the same permission path.
	policies = frappe.get_list(
		"Policy Document",
		filters={"status": "Published"},
		fields=["name", "current_version", "acknowledge_on_joining", "acknowledge_on_new_version"],
		limit_page_length=0,
	)
	needed = [
		(p.name, int(p.current_version or 0))
		for p in policies
		if p.acknowledge_on_joining or p.acknowledge_on_new_version
	]
	if not needed:
		return 0
	done = {
		(a.policy_document, int(a.version or 0))
		for a in frappe.get_all(
			"Policy Acknowledgement",
			filters={"employee": employee, "policy_document": ["in", [n for n, _v in needed]]},
			fields=["policy_document", "version"],
			limit_page_length=0,
		)
	}
	return sum(1 for pair in needed if pair not in done)


def _my_requests(employee):
	"""This person's own requests that are still waiting on somebody else.

	Leave, attendance corrections and shift changes. AC-22: a person who is
	their own leave approver sees their request here and NOT under approvals -
	which is why this is counted from the employee and the approvals are
	counted from the approver, and why the Inbox page shows them as separate
	rows.
	"""
	if not employee:
		return 0
	total = frappe.db.count(
		"Leave Application", {"employee": employee, "status": "Open", "docstatus": 0}
	)
	# `DONE_STATES` is imported rather than retyped, so "still waiting" has one
	# definition in the codebase.
	from alvoraa_portal.attendance_correction import DONE_STATES, REQUEST

	total += frappe.db.count(
		REQUEST,
		{
			"employee": employee,
			"docstatus": 0,
			"alvoraa_review_status": ["not in", list(DONE_STATES)],
		},
	)
	if _has_doctype("Shift Request"):
		total += frappe.db.count("Shift Request", {"employee": employee, "docstatus": 0})
	return total


@frappe.whitelist()
def get_nav_counts():
	"""The second and last start-up call (US-6, AC-7, AC-20, AC-24).

	Returns counts and nothing else - no names, no reasons, no document ids
	(AC-23, PRIV-4). A number tells somebody to go and look; the screen they go
	to is where the permission checks that matter live.

	Guest is refused by `frappe.whitelist()` without `allow_guest`. The explicit
	line below is what still refuses if somebody ever adds it.
	"""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)

	employee = _my_employee(user)
	counts = _zero()
	corrections_hr_scope = False

	if employee:
		counts["leave_approvals"] = _leave_approvals(user)
		counts["goal_updates"] = _goal_updates()
		counts["attendance_fixes"], corrections_hr_scope = _attendance_fixes(user, employee)
		counts["shift_requests"] = _shift_requests(user)
		counts["policies"] = _policies(employee)
		counts["my_requests"] = _my_requests(employee)
	# Rule 6 - no Active Employee record - keeps every part at zero. Not an
	# error, and not an empty payload either: the Inbox page draws "All clear"
	# from the same shape everybody else gets (AC-63).

	approvals = sum(counts[key] for key in APPROVAL_PARTS)
	total = approvals + counts["policies"] + counts["my_requests"]

	return {
		"total": total,
		"approvals_total": approvals,
		"has_employee": bool(employee),
		"parts": [
			{
				"key": key,
				"count": counts[key],
				"route": route,
				# The screen this row links to shows at most `cap` rows. None
				# where the screen shows everything. The Inbox page uses it to
				# say "showing the first 50 of 60" instead of showing 50 and
				# calling it the whole list (section 5, N3).
				"cap": CORRECTIONS_CAP if key == "attendance_fixes" else None,
				"capped": bool(key == "attendance_fixes" and counts[key] > CORRECTIONS_CAP),
			}
			for key, route in PARTS
		],
		# The Inbox page's wording for a capped corrections list differs for an
		# HR caller and a non-HR reviewer, because their scopes differ (W1D-14).
		"corrections_hr_scope": corrections_hr_scope,
	}
