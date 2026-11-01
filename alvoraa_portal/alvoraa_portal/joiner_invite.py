"""The joiner's sign-in: who makes one, what it can reach, and how it ends.

Slice 079. HR's side of pre-onboarding. US-1, US-2, US-14, US-15, US-22.

## What replaced what, and why this file got smaller

Slice 078 handed the joiner a **bearer link**: a token in a URL fragment, stored
in clear in Frappe's own `Web Form Request`, against an unpublished `Web Form`
record that existed only so the request row had something to point at. Counsel's
advice of 31 October and Surbhi's decision of 1 November replaced it with a
**restricted login**, because a login identifies the person rather than trusting
whoever holds a URL.

So all of this is **gone**, not replaced: the token, the fragment handling, the
`Web Form` anchor, `_web_form()`, `_drop_request()`, the clear-text key and
078-SEC-19's recorded deviation about it. **The public write surface of this
product goes from one page and three guest endpoints to zero of each.** That is
the largest subtraction in the slice and it is what pays for the gate in
`auth.py`.

## The account is a door we are deliberately not opening (079-SEC-1)

| Clause | Why |
|---|---|
| **`Website User`**, never a System User | Frappe sends a System User to the desk and refuses a Website User at `/app` by construction, and **`usage.py` counts enabled System Users as seats** - so a System User joiner would be a billable seat, which decision 1 exists to avoid |
| **One role**, `desk_access = 0`, **in no doctype's permission rows anywhere** | `announcements.make_role` already carries the warning this obeys: Frappe creates a role *with* desk access the first time it meets it in a permission JSON. The joiner's own row is reached by server code bound to their session, never by their own permissions |
| **An opaque, non-routable login id** | Frappe's guest-allowed `reset_password` then has no mailbox to mail; the login page stops being an oracle for whether a real person's address exists; and a future staff login on their real email cannot collide with a leftover joiner account |
| **`send_welcome_email = 0`** | Frappe's welcome mail carries a password link, and that does not belong in a stranger's inbox by accident |
| **No `Employee` row** | No seat, no headcount, no org chart - and no `Attendance`, which is the trap this project has already paid for once at DTC |

**The number the joiner types is `User.mobile_no`**, which Frappe resolves
through `System Settings.allow_login_using_mobile_number`
(`frappe/core/doctype/user/user.py:831-843`, read 1 Nov 2026 on v16.33.1). That
setting is **site-wide**: turning it on lets every employee at that tenant sign
in with their mobile number too. Surbhi accepted that with the side effect named
(decision 6b), and **we do not patch it** - `make_sign_in` refuses a mobile login
id while it is off and says which setting to change.

## The credential

Three words and two numbers, from `secrets`, generated here and returned **once**.
It is never stored in clear, never logged, and there is no endpoint to read it
back. If it is lost, HR cancels and makes a new one, which leaves a cleaner trail
than a reissue (OQ-10).

**Why words and not a hash.** It is typed once, from a text message, on a cracked
screen, and sometimes read down a telephone or off a printed slip - which is the
whole reason the design chose a password over a set-password link, because a link
cannot be dictated. Every string on the sign-in page promises that format, so a
random hash would make the page lie. The trade is entropy: 96 words cubed times
100 is about 88 million, against Frappe's 10-attempt lockout and a seven-day
life. **That trade is `01b` ⚠ D3 and it is the security engineer's to confirm.**
"""

import secrets

import frappe
import hrms.alvoraa_org_structure.settings as org_settings
from frappe import _
from frappe.utils import add_to_date, cint, cstr, now

from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission.alvoraa_joiner_submission import (
	JOINER_FIELDS,
	erase,
)
from alvoraa_portal.field_app_limits import HR_KEY, _limited

DOCTYPE = "Alvoraa Joiner Submission"
HR_ROLES = ("HR Manager", "System Manager")
ENDPOINT = "joiner_invite"

# The one role. It appears in NO doctype's permission rows, anywhere, in any app
# - which `test_joiner_079` asserts statically, because Frappe creates a role
# WITH desk access the first time it meets it in a permission JSON.
JOINER_ROLE = "Alvoraa Joiner"

# A reserved TLD (RFC 2606), so nothing can ever be delivered to it. The
# requirement is "not routable", not this exact string.
LOGIN_DOMAIN = "joiner.invalid"

# Words for the credential: short, unambiguous when read aloud, no homophones,
# nothing that could be misheard down a phone line, and no word that spells
# anything unfortunate next to another. 96 of them.
_WORDS = (
	"amber", "anchor", "apple", "arrow", "basket", "bridge", "bucket", "button",
	"cactus", "candle", "canvas", "carpet", "castle", "cherry", "cloud", "cobra",
	"copper", "cotton", "cricket", "crystal", "dolphin", "dragon", "eagle",
	"engine", "falcon", "feather", "forest", "garden", "ginger", "glacier",
	"granite", "guitar", "hammer", "harbour", "helmet", "honey", "island",
	"jacket", "jasmine", "jungle", "kettle", "ladder", "lantern", "lemon",
	"lotus", "magnet", "mango", "maple", "marble", "meadow", "melon", "mirror",
	"monsoon", "mustard", "nutmeg", "olive", "orbit", "orchid", "otter",
	"palace", "pepper", "pigeon", "pillar", "pocket", "pumpkin", "rabbit",
	"ribbon", "river", "rocket", "saddle", "saffron", "sandal", "shadow",
	"silver", "socket", "sparrow", "spinach", "statue", "summit", "sunset",
	"tailor", "temple", "thunder", "ticket", "tiger", "timber", "tulip",
	"tunnel", "turtle", "valley", "velvet", "violet", "walnut", "willow",
	"window", "yellow", "zebra",
)


# ── the switch, and the one gate left on it ─────────────────────────────────

def form_is_on():
	"""Is pre-onboarding switched on at this tenant? **Off unless ticked.**"""
	try:
		return bool(cint(org_settings.get("alvoraa_joiner_form_on")))
	except Exception:
		return False


def require_form_on():
	if not form_is_on():
		frappe.throw(
			_("Asking new joiners for their details before day one is switched "
			  "off. A System Manager turns it on in Organisation Settings."),
			frappe.ValidationError)


def _require_hr():
	if frappe.session.user in ("Guest", ""):
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	if not set(HR_ROLES) & set(frappe.get_roles()):
		from hrms.alvoraa_hr_core.access import refuse

		refuse(_("Only HR can invite a joiner."), "079-SEC-1",
		       f"{ENDPOINT}.make_sign_in")


# ── the employer's own values, which have to be there first (US-2) ──────────

def what_the_employer_has_not_set():
	"""The values a joiner has to be told before they hand anything over.

	Read **raw**, not through `org_settings.get()`, and that is the point: our
	default is the Processor's suggestion, not the Fiduciary's decision. A clock
	nobody chose is exactly the number 078-PRIV-7 existed to refuse, and counsel
	(ruling 1) put the choice with the employer.

	Returns a list of (label, key) still missing, in the order HR's screen draws
	them. Empty means HR may invite.

	**Four rows, where `01b` §6.3 and AC-11 name three.** The notice text is the
	fourth, because 079-PRIV-3 makes it a hard precondition - no text, no form -
	and listing it beside the other three puts all four on the one screen that
	can fix them, rather than letting HR make a sign-in that then refuses to
	open. Recorded as a departure in `03-implementation-notes.md`.
	"""
	missing = []
	for label, key in (
		(_("how long you keep the details of somebody who does not join"),
		 "alvoraa_joiner_not_hired_days"),
		(_("how long you keep a photograph of an identity card"),
		 "alvoraa_joiner_document_days"),
		(_("what you tell a joiner before the first question"),
		 "alvoraa_joiner_notice_text"),
	):
		if not cstr(frappe.db.get_default(key) or "").strip():
			missing.append({"what": label, "key": key})
	if not hr_contact():
		missing.append({
			"what": _("a phone number or email a joiner can reach you on"),
			"key": "alvoraa_hr_contact_phone",
		})
	return missing


def hr_contact():
	"""A REAL way to reach a person, from the tenant's own settings.

	Never ours. The joiner's business is with the employer, and counsel was
	explicit that the rights footer carries the employer's details.
	"""
	out = {}
	for key, field in (("phone", "alvoraa_hr_contact_phone"),
	                   ("email", "alvoraa_hr_contact_email")):
		try:
			value = frappe.db.get_default(field)
		except Exception:
			value = None
		if value:
			out[key] = cstr(value)
	if not out.get("email"):
		# The company's own email, if the tenant set one. Still the employer's,
		# never ours.
		try:
			company = frappe.db.get_default("company")
			if company:
				email = frappe.db.get_value("Company", company, "email")
				if email:
					out["email"] = cstr(email)
		except Exception:
			pass
	return out


# ── the role, made once ─────────────────────────────────────────────────────

def _role():
	"""The one role, with the desk shut. **Read here, created by the patch.**

	`announcements.make_role` does the same thing for notice holders and carries
	the warning this obeys in its own comment: **Frappe creates a role with desk
	access the first time it meets the name in a doctype's permission rows.** So
	this name must never appear in a permission JSON - a static test asserts it.

	It is not created here, and that is 079-SEC-7: making it needed a bypass on
	a request path, and a role is a schema-shaped object that belongs in a patch
	(`patches/v1_0/joiner_sign_in_replaces_the_link.py`) rather than in HR's
	button. A missing role is a site that has not been migrated, and it says so
	in words rather than quietly making one.
	"""
	if not frappe.db.exists("Role", JOINER_ROLE):
		frappe.throw(
			_("This site has not finished setting up pre-onboarding. Ask your "
			  "system administrator to run the update, and try again."),
			frappe.ValidationError)
	return JOINER_ROLE


def _new_credential():
	"""Three words and two numbers. From `secrets`, on the server, never chosen
	by HR and never reused (079-SEC-2, and J4 - which is ALV-242 again).

	**Three words, not two.** `01b` §4.2's copy says "three words and two
	numbers" and then gives `tiger-lamp-74`, which is two. The copy is right and
	the example was wrong: two words and two digits is 96² × 100 ≈ 920,000,
	which a 10-tries-a-minute lockout exhausts inside the credential's own
	seven-day life. Three words is ≈ 88 million. Our worked example everywhere
	is therefore `tiger-lamp-maple-74`, and the change is recorded in
	`03-implementation-notes.md`.
	"""
	return "%s-%s-%s-%02d" % (
		secrets.choice(_WORDS), secrets.choice(_WORDS), secrets.choice(_WORDS),
		secrets.randbelow(100),
	)


def _login_id():
	"""An opaque, non-routable address. Nothing HR typed is in it."""
	return f"joiner-{frappe.generate_hash(length=18)}@{LOGIN_DOMAIN}"


def _looks_like_a_number(value):
	"""Is what HR typed a telephone number rather than an email address?

	Deliberately crude: it decides which refusal to show, not who gets in.
	"""
	return "@" not in cstr(value)


def _already_a_login(typed):
	"""Does that number or email already belong to ANY `User`?

	AC-9, and it is ALV-242's lesson: one credential per person, never a batch.
	It covers a member of staff's real login, a re-hire's old account and
	another joiner's, because all three resolve through the same two columns
	Frappe searches (`User.name` and `User.mobile_no`).
	"""
	typed = cstr(typed).strip()
	if not typed:
		return False
	# `ignore_permissions` because the guard has to see rows the caller may not:
	# Frappe ships `User` read to System Manager, so an HR Manager's own query
	# would be narrowed to their own row and the duplicate check would pass
	# silently every time. It returns a boolean and never a name.
	return bool(frappe.get_all("User", or_filters=[
		{"name": typed}, {"email": typed}, {"mobile_no": typed},
	], pluck="name", limit_page_length=1, ignore_permissions=True))


# ── making one (US-1) ───────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
@_limited(HR_KEY, "user", limit=30)
def make_sign_in(submission=None):
	"""One sign-in for one person HR has already written down.

	HR types the joiner's name and the number or email they already reached them
	on, saves the row, and presses this. The password comes back **once** and is
	stored nowhere readable: Frappe's own password store is the only copy.
	"""
	_require_hr()
	require_form_on()

	missing = what_the_employer_has_not_set()
	if missing:
		# **The block lands on the person who can fix it.** The alternative was a
		# joiner-facing "we do not know how long they keep this" screen, shown to
		# the only person who cannot do anything about it.
		frappe.throw(
			_("You cannot invite anybody yet. A joiner has to be told these "
			  "things before they hand anything over, and they come from your "
			  "settings, not from us: {0}. A System Manager sets them in "
			  "Organisation Settings.")
			.format(", ".join(m["what"] for m in missing)),
			frappe.ValidationError)

	doc = frappe.get_doc(DOCTYPE, submission)
	if doc.status != "Invited":
		frappe.throw(_("This invite is already {0}.").format(_(doc.status)),
		             frappe.ValidationError)
	if doc.user:
		frappe.throw(
			_("This person already has a sign-in. Cancel it and make a new one "
			  "if they have lost their password."), frappe.ValidationError)
	if not cstr(doc.full_name or "").strip():
		frappe.throw(_("Give the joiner's name."), frappe.ValidationError)

	# **HR's own entry, in its own field, and NOT in the joiner's `mobile`
	# column.** Reading `doc.mobile` here was a real defect, found by the 078
	# suite being re-keyed: `cell_number` maps to `mobile`, so HR typing the
	# number before pressing this button answered *"has this joiner sent us
	# anything yet?"* on every row - which let an empty form be sent, and made
	# marking the mobile number compulsory do nothing at all.
	typed = cstr(doc.login_id or "").strip()
	if not typed:
		frappe.throw(
			_("Give the mobile number or the email you reached this person on, "
			  "in “Signs in with”. It is what they type to sign in."),
			frappe.ValidationError)

	if _already_a_login(typed):
		frappe.throw(
			_("That number or email already belongs to a sign-in here. Use the "
			  "other one - a mobile number if you typed an email, or an email if "
			  "you typed a number. Two people can never share one sign-in."),
			frappe.ValidationError)

	if _looks_like_a_number(typed) and not cint(
			frappe.get_system_settings("allow_login_using_mobile_number")):
		# **Not patched from here.** It is site-wide: turning it on lets every
		# employee at this tenant sign in with their mobile number as well.
		# Surbhi accepted that side effect by name, so a System Manager turns it
		# on deliberately.
		frappe.throw(
			_("Signing in with a mobile number is switched off at this "
			  "organisation. A System Manager turns on “Allow Login using "
			  "Mobile Number” in System Settings - which also lets every "
			  "employee here sign in with their mobile number. Or use the "
			  "joiner's email address instead."), frappe.ValidationError)

	days = max(1, cint(org_settings.get("alvoraa_joiner_link_days")) or 7)
	expires = add_to_date(now(), days=days)
	password = _new_credential()

	user = frappe.get_doc({
		"doctype": "User",
		"email": _login_id(),
		# Their name, so HR's own user list is readable. No email, no
		# photograph, no address: the joiner's personal email stays a field on
		# the submission, where erasure already reaches it.
		"first_name": cstr(doc.full_name).strip()[:140],
		"mobile_no": typed if _looks_like_a_number(typed) else None,
		"user_type": "Website User",
		"enabled": 1,
		"send_welcome_email": 0,
		"new_password": password,
		"roles": [{"role": _role()}],
	})
	# The one bypass here, and the permission system genuinely cannot do it: an
	# HR Manager holds no `create` on `User` - Frappe ships that to System
	# Manager - and the whole point of decision 1 is that HR, not an
	# administrator, invites a joiner. It runs after `_require_hr()`, after the
	# employer's own values are checked, and after the duplicate guard.
	user.insert(ignore_permissions=True)

	doc.db_set("user", user.name, update_modified=False)
	doc.db_set("expires_on", expires, update_modified=False)
	frappe.db.commit()

	# The row and who made it. **Never the credential**, and never the name.
	frappe.logger("alvoraa").info(
		f"joiner sign-in made: {doc.name} by {frappe.session.user} at {now()}, "
		f"{days} day access")

	return {
		"submission": doc.name,
		# The ONE time these come back. There is no endpoint that reads them
		# again, and the password is in no log line, no Version row and no field.
		"username": typed,
		"password": password,
		"expires_on": str(expires),
		"access_days": days,
		"address": f"{frappe.utils.get_url()}/joining",
		"contact": hr_contact(),
	}


@frappe.whitelist(methods=["POST"])
@_limited(HR_KEY, "user", limit=30)
def cancel_invite(submission=None, reason=None):
	"""Take a sign-in back. Terminal, like every other move out of Invited.

	The account itself is ended by the controller, in the same transaction as
	the status change - see `alvoraa_joiner_submission.on_update`, which is the
	one place all five endings meet.
	"""
	_require_hr()
	doc = frappe.get_doc(DOCTYPE, submission)
	if doc.status not in ("Invited", "Submitted"):
		frappe.throw(_("This invite is already {0}.").format(_(doc.status)),
		             frappe.ValidationError)
	doc.status = "Cancelled"
	doc.cancel_reason = reason or "By HR"
	doc.save()
	frappe.db.commit()
	frappe.logger("alvoraa").info(
		f"joiner invite cancelled: {doc.name} by {frappe.session.user} at {now()}")
	return {"status": doc.status}


# ── the five endings, in one place (US-14, 079-SEC-5) ──────────────────────

def end_the_sign_in(doc, why):
	"""Close a joiner's account. Four things, in one transaction.

	`enabled = 0`, the role removed, **every session cleared explicitly**, and
	the credential destroyed.

	The sessions are cleared by hand because whether Frappe kills a live session
	the moment `enabled` goes to 0 is **not stated anywhere we could read**, and
	`System Settings.session_expiry` is not touched - it is site-wide and would
	change every member of staff's day.

	The credential is destroyed rather than rotated: there is nothing to rotate
	to, and `__Auth` holding a dead hash is one more copy of a secret.

	**The account is closed, never promoted.** On the day the person is hired
	their staff login is a separate account on their real address: carrying this
	role onto it would lock the new employee out of their own record through the
	very gate in `auth.py`.
	"""
	name = doc.get("user")
	if not name or not frappe.db.exists("User", name):
		return False
	try:
		from frappe.sessions import clear_sessions
		from frappe.utils.password import delete_all_passwords_for

		frappe.db.set_value("User", name, "enabled", 0, update_modified=False)
		frappe.db.delete("Has Role", {"parent": name, "parenttype": "User"})
		clear_sessions(user=name, force=True)
		delete_all_passwords_for("User", name)
		frappe.cache().hdel("user_roles", name)
		frappe.clear_cache(user=name)
		frappe.db.commit()
	except Exception:
		# Worth knowing about: an account we meant to close may still be open.
		# The row, never the person.
		frappe.log_error(f"Could not close the sign-in on {doc.name}",
		                 "Joiner sign-in")
		return False
	frappe.logger("alvoraa").info(
		f"joiner sign-in closed: {doc.name}, reason {why}, at {now()}")
	return True


# ── counsel's two actions for a candidate's own request (US-22) ─────────────

@frappe.whitelist()
def export_submission(submission=None):
	"""Everything held about one joiner, as a file HR can send them.

	Counsel, ruling 8: a candidate who never joined cannot see or export
	anything themselves, so HR has to be able to answer "what do you hold about
	me" in one click, without a developer.

	**Masked by default, and it is not a choice** (counsel 9). It lists the files
	by name and date and does **not** include their bytes: the request is "what
	do you hold", the documents are the person's own and HR can send them
	separately, and putting identity scans into a JSON attachment is a second
	copy nobody asked for. There is no bytes-included export at any permission
	level - `test_joiner_079` asserts that there is none.
	"""
	_require_hr()
	doc = frappe.get_doc(DOCTYPE, submission)
	files = frappe.get_all("File", filters={
		"attached_to_doctype": DOCTYPE, "attached_to_name": doc.name,
	}, fields=["file_name", "creation"], limit_page_length=0, ignore_permissions=True)

	body = {
		"what_this_is": "Everything held about one person who was invited to "
		                "send their details before their first day.",
		"reference": doc.name,
		"status": doc.status,
		"invited_on": str(doc.creation),
		"sent_on": str(doc.submitted_at) if doc.submitted_at else None,
		"erased_on": str(doc.erased_on) if doc.erased_on else None,
		"details": {f: doc.get(f) for f in JOINER_FIELDS},
		"bringing_on_the_first_day": doc.bring_on_day_one or None,
		"files": [{"name": f.file_name, "given_on": str(f.creation)} for f in files],
	}
	frappe.local.response.filename = f"what-we-hold-{doc.name}.json"
	frappe.local.response.filecontent = frappe.as_json(body, indent=2).encode("utf-8")
	frappe.local.response.type = "download"
	log_an_export(doc.name, masked=True)


def log_an_export(submission, masked):
	"""One line per export, and **whether it was masked** (counsel 9).

	A named function with one job, so a fourth export cannot be added without
	one: `test_joiner_079` runs a table test over every export endpoint in these
	modules and asserts exactly one line per call. Never a field value, never a
	file.
	"""
	frappe.logger("alvoraa").info(
		f"joiner submission exported: {submission} by {frappe.session.user} "
		f"at {now()}, masked={bool(masked)}")


@frappe.whitelist(methods=["POST"])
def purge_submission(submission=None):
	"""Erase one joiner's details and files now, on their own request.

	`force=True`: the one case where a legal hold does not stop an erasure,
	because the person has asked and HR has decided. The hold exists to stop a
	CLOCK deleting something somebody wants preserved, not to override a human
	acting on a request.
	"""
	_require_hr()
	doc = frappe.get_doc(DOCTYPE, submission)
	done = erase(doc.name, why="HR purged it on request", force=True)
	frappe.logger("alvoraa").info(
		f"joiner submission purged: {doc.name} by {frappe.session.user} at {now()}")
	return {"erased": bool(done)}
