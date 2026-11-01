"""Deleting what a joiner sent, on counsel's rules, once a day.

Slice 078, step 6. 078-PRIV-6, and counsel's answer of 29 October 2026 with
Surbhi's four defaults of 31 October.

## The rules, and which clock each one runs on

| Case | Rule | Setting, default |
|---|---|---|
| **Their identity documents** | **A second clock, and counsel's ruling 4 is why it exists.** A photograph of an identity card goes much sooner than a candidate record: 30 to 60 days against 180 to 365. It deletes the `File` rows only, bytes included, and leaves every typed field alone - **including on a row nobody ever actioned**, counted from when it arrived, or an ignored submission would keep an identity document until the 90-day backstop took the whole row | `alvoraa_joiner_document_days`, **30**, range 30-60 |
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
	LIVE,
	TERMINAL,
	delete_the_documents,
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
		# Counsel's SECOND clock (ruling 4), and it runs FIRST among the
		# erasures so that a row crossing both clocks on the same night loses
		# its documents under the rule that names them. It keeps its OWN
		# count, because without one "did the documents actually go" has no
		# answer (AC-89).
		"documents": _delete_the_documents_sooner(),
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


def _delete_the_documents_sooner():
	"""Counsel's ruling 4: a photograph of an identity card goes much sooner than
	the record it was sent with.

	**It deletes the `File` rows only, bytes included. The typed fields are not
	touched.** 30 to 60 days against 180 to 365 - one setting could not say both,
	which is why `alvoraa_joiner_document_days` exists at all.

	Two reads, not one, because the clock starts in two different places and both
	are deliberate:

	  * a **closed** row counts from `closed_on`, never from `modified`, for the
	    reason already learned and written on the field itself - ticking legal
	    hold and unticking it again would restart the clock;
	  * a row **nobody ever actioned** counts from `creation`, whatever state it
	    is in. Without that half, an ignored submission would keep an identity
	    document until the 90-day backstop took the whole row - against counsel's
	    30 to 60 (AC-87).

	Legal hold wins, as it does for the record clock. HR is told AT the deletion
	rather than before it (OQ-6): a pre-warning needs a second setting and a
	second stamp field, and HR already has legal hold and a visible row.

	No stamp field is needed to stop it running twice. The second run finds no
	files, deletes nothing, and says nothing.
	"""
	days = _days("alvoraa_joiner_document_days", 30)
	cutoff = add_to_date(now(), days=-days)
	done = 0
	for filters in ({"status": ("in", TERMINAL), "closed_on": ("<", cutoff)},
	                {"status": ("in", LIVE), "creation": ("<", cutoff)}):
		for name in _todo(filters):
			deleted = delete_the_documents(name)
			if not deleted:
				continue
			done += deleted
			_tell_hr_the_documents_went(name, deleted, days)
	if done:
		frappe.db.commit()
	return done


def _tell_hr_the_documents_went(name, deleted, days):
	"""M16, through the `Notification Log` the job already uses.

	It names the REFERENCE and the count, never the person, never the type and
	never the file. An email would be a copy we cannot erase.
	"""
	invited_by = frappe.db.get_value(DOCTYPE, name, "invited_by")
	if not invited_by:
		return
	_tell(invited_by, name,
	      _("Identity documents on a joiner invite were deleted"),
	      _("The {0} identity document(s) on invite {1} were deleted after {2} "
	        "days, which is how long your organisation keeps a photograph of an "
	        "identity card. Ask again if you still need them. The rest of the "
	        "invite is untouched.").format(cint(deleted), name, days),
	      f"Could not say the documents on {name} had gone")


def _tell(user, reference, subject, body, if_it_fails):
	"""One `Notification Log` row, and **the one bypass this module needs for
	both of its messages.**

	Nobody holds `create` on `Notification Log` - Frappe writes its own the same
	way - and this runs from the scheduler, with no session at all. Funnelled
	into one function rather than two so that the bypass is counted once and
	argued once (079-SEC-7).

	It names the REFERENCE, never the person. Whoever opens the row can see the
	name; a notification does not need to carry it. And it is a notification
	rather than an email, because an email is a copy we cannot erase.
	"""
	try:
		frappe.get_doc({
			"doctype": "Notification Log",
			"for_user": user,
			"type": "Alert",
			"document_type": DOCTYPE,
			"document_name": reference,
			"subject": subject,
			"email_content": body,
		}).insert(ignore_permissions=True)
		return True
	except Exception:
		frappe.log_error(if_it_fails, "Joiner retention")
		return False


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
		if not _tell(row.invited_by, row.name,
		             _("A joiner's details will be deleted in {0} days")
		             .format(stop - warn),
		             _("Nobody has turned invite {0} into a staff record. It is "
		               "deleted {1} days after it arrived, which is how we keep "
		               "nothing indefinitely. Open it to act on it, or tick legal "
		               "hold if it must be kept.").format(row.name, stop),
		             f"Could not warn about {row.name}"):
			continue
		frappe.db.set_value(DOCTYPE, row.name, "warned_on", now(),
		                    update_modified=False)
		sent += 1
	if sent:
		frappe.db.commit()
	return sent


def expire_the_dead_sign_ins():
	"""Move a sign-in past its date to `Expired`, which closes the account.

	The status change is what does the work: the controller's `on_update`
	disables the account, strips its role, clears its sessions and destroys its
	credential, in the same transaction (079-SEC-5). **So this is no longer
	cosmetic.** Under the bearer link it only changed what HR SAW, because the
	framework already refused an expired key.

	**Both live states, not only `Invited`.** Decision 4a means a joiner who has
	already sent their form still has a working sign-in, so a `Submitted` row
	reaching its date has an account to close too. Under 078 this read `Invited`
	only, because sending burned the link.
	"""
	rows = frappe.get_all(DOCTYPE,
	                      filters={"status": ("in", LIVE),
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
			done += 1
		except Exception:
			frappe.log_error(f"Could not expire {name}", "Joiner retention")
	if done:
		frappe.db.commit()
		frappe.logger("alvoraa").info(f"joiner sign-ins expired: {done}")
	return done


def daily():
	"""What `hooks.py` names. Expire first, then erase, so a sign-in that died
	today is in the right state before the clocks are read."""
	return {"expired": expire_the_dead_sign_ins(), **run_daily()}


# ── OPS-28: the one invariant worth watching ────────────────────────────────

@frappe.whitelist()
def joiner_counts(days=7):
	"""Sign-ins made, submissions received, and the one invariant HR glances at.

	**The alert is the invariant: submissions must never exceed links issued.**
	More submissions than sign-ins means one credential is being used by
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
