"""Deleting what a joiner sent, on counsel's rules, once a day.

Slice 078, step 6. 078-PRIV-6, and counsel's answer of 29 October 2026 with
Surbhi's four defaults of 31 October.

## The rules, and which clock each one runs on

| Case | Rule | Setting, default |
|---|---|---|
| They became an employee | the details are already their personnel record, so the copy is redundant. Erased on the next run | — |
| They did not join (Cancelled or Expired) | **not erased the moment HR gives up on them** - counsel reversed that, because the employer has its own candidate record-keeping duties. A window from when the invite closed | `alvoraa_joiner_not_hired_days`, **180**, range 180-365 |
| Nobody ever actioned it | erased anyway, from when it arrived, **whatever state it is in** - because the 18 September 2026 policy prohibits indefinite retention in so many words | `alvoraa_joiner_backstop_days`, **90** |
| Before that happens | HR is **told**, so the backstop is a safety net rather than a surprise | `alvoraa_joiner_warn_days`, **75** |

Every number is a setting because **our customers are the Data Controllers and
we are a Data Processor**: our job is the tools and the settings, not the
periods. The defaults are Surbhi's, recorded with her name and date in
`03-implementation-notes.md`, and they are the Processor supplying a sensible
starting point rather than the Controller having chosen.

## Three things this deliberately does

* **Real deletion.** The fields are cleared and the uploaded files are deleted,
  bytes included. Counsel's September policy prohibits indefinite soft
  deletion, so there is no "deleted" flag anywhere and no value of any setting
  means "keep for ever".
* **Legal hold wins.** A flagged row is skipped however old it is. Deleting
  something somebody has asked you to preserve is worse than keeping it too
  long. HR's own Purge is the one exception, because there the erasure is the
  obligation.
* **It says what it did.** A count to the log, so "are these actually being
  deleted" has an answer that is not "look in the files folder and guess".
  Counts only - never a name, never a field, never a file.
"""

import frappe
import hrms.alvoraa_org_structure.settings as org_settings
from frappe import _
from frappe.utils import add_to_date, cint, now

from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission.alvoraa_joiner_submission import (
	erase,
)

DOCTYPE = "Alvoraa Joiner Submission"
BATCH = 500


def _days(key, fallback):
	try:
		value = cint(org_settings.get(key))
	except Exception:
		value = 0
	return value if value > 0 else fallback


def run_daily():
	"""The one scheduled job in this slice. Nothing else here goes on a queue.

	Safe to run twice: `erase` skips a row it has already erased, and the
	warning is recorded on the row so a second run does not send it again.
	"""
	if not frappe.db.exists("DocType", DOCTYPE):
		return {"skipped": "pre-onboarding is not installed on this site"}

	out = {
		"hired": _erase_the_redundant_copies(),
		"not_hired": _erase_the_ones_who_did_not_join(),
		"backstop": _erase_the_untouched(),
		"warned": _warn_hr_before_the_backstop(),
	}
	if any(out.values()):
		frappe.logger("alvoraa").info(f"joiner retention: {out}")
	return out


def _todo(filters):
	filters = dict(filters)
	filters["erased_on"] = ("is", "not set")
	filters["legal_hold"] = 0
	return frappe.get_all(DOCTYPE, filters=filters, pluck="name",
	                      limit_page_length=BATCH, ignore_permissions=True)


def _erase_the_redundant_copies():
	"""They joined, so the details are already their Employee record."""
	done = 0
	for name in _todo({"status": "Made an employee"}):
		if erase(name, why="They became an employee, so the copy was redundant"):
			done += 1
	return done


def _erase_the_ones_who_did_not_join():
	"""Counsel's window, from when the invite CLOSED rather than from when it
	arrived - the employer's candidate record-keeping runs from the decision.

	From `closed_on`, NOT from `modified`. `modified` moves on any later edit,
	so ticking legal hold and unticking it again would restart the clock. A row
	with no `closed_on` is one the controller never stamped, so the backstop
	below catches it instead of this leaving it for ever.
	"""
	days = _days("alvoraa_joiner_not_hired_days", 180)
	cutoff = add_to_date(now(), days=-days)
	done = 0
	for name in _todo({"status": ("in", ("Cancelled", "Expired")),
	                   "closed_on": ("<", cutoff)}):
		if erase(name, why=f"They did not join, and the {days}-day window has passed"):
			done += 1
	return done


def _erase_the_untouched():
	"""The backstop. From when it ARRIVED, whatever state it is in.

	This is the one that makes "nothing is kept indefinitely" true: a submission
	nobody ever actioned would otherwise sit for ever, and no setting here has a
	value that means never.
	"""
	days = _days("alvoraa_joiner_backstop_days", 90)
	cutoff = add_to_date(now(), days=-days)
	done = 0
	for name in _todo({"creation": ("<", cutoff)}):
		if erase(name, why=f"Nobody actioned it within {days} days"):
			done += 1
	return done


def _warn_hr_before_the_backstop():
	"""Tell whoever issued the link, once, before the backstop takes it.

	Uses Frappe's own `Notification Log`, which is what the bell in the portal
	already reads - not a new mechanism and not an email, because an email
	naming a joiner is one more place a non-employee's data travels.

	It names the REFERENCE, never the person. Whoever opens the row can see the
	name; a notification does not need to carry it.
	"""
	warn = _days("alvoraa_joiner_warn_days", 75)
	stop = _days("alvoraa_joiner_backstop_days", 90)
	if warn >= stop:
		# Mis-set. The setter refuses this, so it can only arrive by a direct
		# write - and a warning after the deletion is not a warning.
		return 0
	cutoff = add_to_date(now(), days=-warn)
	rows = frappe.get_all(
		DOCTYPE,
		filters={"status": ("in", ("Invited", "Submitted")),
		         "creation": ("<", cutoff),
		         "erased_on": ("is", "not set"),
		         "warned_on": ("is", "not set")},
		fields=["name", "invited_by"], limit_page_length=BATCH,
		ignore_permissions=True)
	sent = 0
	for row in rows:
		try:
			frappe.get_doc({
				"doctype": "Notification Log",
				"for_user": row.invited_by,
				"type": "Alert",
				"document_type": DOCTYPE,
				"document_name": row.name,
				"subject": _("A joiner's details will be deleted in {0} days")
				.format(stop - warn),
				"email_content": _(
					"Nobody has turned invite {0} into a staff record. It is "
					"deleted {1} days after it arrived, which is how we keep "
					"nothing indefinitely. Open it to act on it, or tick legal "
					"hold if it must be kept.").format(row.name, stop),
			}).insert(ignore_permissions=True)
			frappe.db.set_value(DOCTYPE, row.name, "warned_on", now(),
			                    update_modified=False)
			sent += 1
		except Exception:
			frappe.log_error(f"Could not warn about {row.name}",
			                 "Joiner retention")
	if sent:
		frappe.db.commit()
	return sent


def expire_the_dead_links():
	"""Move a link past its date to `Expired`, and destroy the key's row.

	The framework already refuses an expired key, so this changes nothing about
	safety - it changes what HR SEES, so a list of "Invited" is a list of links
	that still work. And it is what gets the clear-text key deleted rather than
	left in `Web Form Request` until somebody notices.
	"""
	from alvoraa_portal import joiner_invite

	rows = frappe.get_all(DOCTYPE,
	                      filters={"status": "Invited",
	                               "expires_on": ("<", now())},
	                      pluck="name", limit_page_length=BATCH,
	                      ignore_permissions=True)
	done = 0
	for name in rows:
		try:
			doc = frappe.get_doc(DOCTYPE, name)
			doc.status = "Expired"
			doc.flags.ignore_permissions = True
			doc.save(ignore_permissions=True)
			joiner_invite._drop_request(doc)
			done += 1
		except Exception:
			frappe.log_error(f"Could not expire {name}", "Joiner retention")
	if done:
		frappe.db.commit()
		frappe.logger("alvoraa").info(f"joiner links expired: {done}")
	return done


def daily():
	"""What `hooks.py` names. Expire first, then erase, so a link that died
	today is in the right state before the clocks are read."""
	return {"expired": expire_the_dead_links(), **run_daily()}


# ── OPS-28: the one invariant worth watching ────────────────────────────────

@frappe.whitelist()
def joiner_counts(days=7):
	"""Links issued, submissions received, and refusals - for HR to glance at.

	**The alert is the invariant: submissions must never exceed links issued.**
	More submissions than links means one forwarded link is being used by
	several people, which is visible here before HR notices records for people
	they never invited. No new tool: two numbers we already have.
	"""
	from alvoraa_portal.joiner_invite import HR_ROLES

	if not set(HR_ROLES) & set(frappe.get_roles()):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	since = add_to_date(now(), days=-max(1, cint(days)))
	issued = frappe.db.count(DOCTYPE, {"creation": (">", since)})
	sent = frappe.db.count(DOCTYPE, {"submitted_at": (">", since)})
	return {
		"days": cint(days),
		"links_issued": issued,
		"submissions": sent,
		# True is the normal state. False is the thing to look at.
		"invariant_holds": sent <= issued,
	}
