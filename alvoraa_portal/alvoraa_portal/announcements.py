"""Slice 076, Part B: sending a notice to the people a sender looks after.

Who may send: whoever holds the role "Notice Sender". The organisation gives it
and takes it away in Users (D8 simplified). HR Managers got it once, at install.

Whom they reach: `access.notice_audience_conditions(sender)`, then only Active
people with an enabled login, never the sender themself. Every scope question
here names the sender. **The scheduled send runs as Administrator, who would
reach everybody, so nothing in this file asks about "the current user" once it
is past the endpoint's own check** (SEC-4).

How it goes out: one Notification Log row per person, type "Alert". "Alert" is
in Frappe's `notification_skip_email_types`, so the row never emails anyone by
itself (SEC-17). An email copy goes only when the sender ticked it and email is
active for this tenant, checked at create and again at send.

Once: the send reads the notice with a row lock first, moves it Scheduled ->
Sending -> Sent, commits after every 200 rows and skips anyone who already has
a row, so a second run or a resume never gives a person two copies (SEC-7).

Logs carry notice ids and counts, never the text, a name or an email (SEC-21).
"""

import html
import json
import time

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_datetime, now_datetime, today

from alvoraa_portal.alvoraa_portal.doctype.announcement.announcement import CREATE_FLAG
from hrms.alvoraa_hr_core.access import notice_audience_conditions, refuse

ROLE = "Notice Sender"
DOCTYPE = "Announcement"
PORTAL = "/hrms-employee"

MAX_CHARS = 300          # after trimming (decision 9: fixed in code)
CONFIRM_ABOVE = 25       # more people than this needs `confirmed` (D2)
PER_DAY = 5              # notices per sender per calendar day, cancelled ones too (D2)
SEND_IN_REQUEST = 25     # "Now" to this many or fewer is written before the reply (Surbhi, 28 Oct)
CHUNK = 200              # rows per commit
REPEAT_SECONDS = 120     # the same text again this soon returns the first notice
STALE_MINUTES = 10       # a "Sending" notice untouched this long is resumed
MAX_STALLS = 3           # resumes with nothing written before it is Failed
PER_TICK = 2             # notices one scheduler tick hands to workers

# What the page sends -> what the record stores.
KINDS = {"everyone": "Everyone in my scope", "company": "Company",
         "branch": "Branch", "people": "Chosen people"}


# ── who is asking ────────────────────────────────────────────────────────────

def _has_left(user):
	"""True when the user has Employee records and none of them is Active."""
	states = frappe.get_all("Employee", filters={"user_id": user}, pluck="status")
	return bool(states) and "Active" not in states


def _require_sender(endpoint):
	"""The caller, if they may send. Refused otherwise, on the server (SEC-1)."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	if ROLE not in frappe.get_roles(user):
		refuse(_("You do not have the Notice Sender access. Ask HR if you need it."),
		       "076-SEC-1", endpoint, DOCTYPE)
	if _has_left(user):
		refuse(_("You cannot send notices after leaving."), "076-T12", endpoint, DOCTYPE)
	return user


def _sender_problem(sender):
	"""Why this sender may no longer send, in plain words, or None (SEC-5)."""
	if not frappe.db.get_value("User", sender, "enabled"):
		return _("The sender's login is switched off.")
	if ROLE not in frappe.get_roles(sender):
		return _("The sender no longer has the Notice Sender access.")
	if _has_left(sender):
		return _("The sender has left the organisation.")
	return None


# ── whom they reach ──────────────────────────────────────────────────────────

def _people(sender, extra=None, limit=None):
	"""Active people with an enabled login inside the sender's scope, not the
	sender. Conditions stay a list, so `extra` can only narrow (SEC-3)."""
	conditions = notice_audience_conditions(sender) + [["status", "=", "Active"], ["user_id", "is", "set"]]
	rows = frappe.get_all("Employee", filters=conditions + (extra or []),
	                      fields=["name", "employee_name", "user_id", "company", "branch"],
	                      order_by="employee_name asc", limit=limit or 0)
	users = list({r.user_id for r in rows if r.user_id != sender})
	enabled = set(frappe.get_all("User", filters={"name": ["in", users], "enabled": 1},
	                             pluck="name")) if users else set()
	return [r for r in rows if r.user_id in enabled]


def _everyone_label(sender):
	return _("Everyone I can see") if (sender == "Administrator" or "System Manager" in frappe.get_roles(sender)) \
		else _("Everyone I look after")


def _targets(people):
	"""The companies and branches a sender may choose, with counts. Companies
	only when the scope has more than one (design 6, as drawn)."""
	companies, branches, homes = {}, {}, {}
	for p in people:
		companies[p.company] = companies.get(p.company, 0) + 1
		if p.branch:
			branches[p.branch] = branches.get(p.branch, 0) + 1
			homes.setdefault(p.branch, set()).add(p.company)
	out = []
	many = len(companies) > 1
	if many:
		out += [{"kind": "company", "value": c, "label": c, "n": n} for c, n in sorted(companies.items())]
	# "Noida unit (Alvora Retail)" when the sender sees more than one company (as drawn).
	out += [{"kind": "branch", "value": b, "n": n,
	         "label": "{0} ({1})".format(b, ", ".join(sorted(homes[b]))) if many else b}
	        for b, n in sorted(branches.items())]
	return out


def _chosen_ids(people):
	if isinstance(people, str):
		try:
			people = json.loads(people) if people.strip() else []
		except ValueError:
			frappe.throw(_("Tick at least one person."))
	if not isinstance(people, (list, tuple)):
		frappe.throw(_("Tick at least one person."))
	return sorted({str(p) for p in people if p})


def _resolve(sender, kind, company=None, branch=None, ids=None, at_send=False):
	"""The people this notice reaches, worked out as the sender.

	At create a choice outside the scope is refused, not narrowed (SEC-2, SEC-3).
	At send the audience is worked out again, so a leaver is skipped and a joiner
	included (AC-26); a company or branch the sender no longer reaches stops it."""
	everyone = _people(sender)
	if kind == "Everyone in my scope":
		return everyone
	if kind in ("Company", "Branch"):
		field, value = ("company", company) if kind == "Company" else ("branch", branch)
		if not value:
			frappe.throw(_("Choose a branch or company."))
		chosen = [p for p in everyone if p.get(field) == value]
		if not chosen and not at_send:
			refuse(_("You cannot send to that branch or company. Choose one from the list."),
			       "076-SEC-2", "create_notice", DOCTYPE)
		return chosen
	ids = ids or []
	if not ids:
		frappe.throw(_("Tick at least one person."))
	wanted = set(ids)
	chosen = [p for p in everyone if p.name in wanted]
	outside = len(wanted) - len(chosen)
	if outside and not at_send:
		refuse(_("{0} of the people you chose cannot get this notice. They may have left, have no login, "
		         "or be outside the people you look after. Choose again.").format(outside),
		       "076-SEC-3", "create_notice", DOCTYPE)
	return chosen


def _users(people):
	"""One row per login, even when a login sits on two Employee records."""
	return sorted({p.user_id for p in people})


def email_is_active():
	"""Is email switched on for this tenant? (D4, SEC-17)

	Off when the site or the bench mutes email (`mute_emails`, how DTC and every
	production site is held quiet today), or when nothing could send it: no
	enabled outgoing Email Account and no mail server in the config. Those are
	the same places Frappe itself looks."""
	if frappe.are_emails_muted():
		return False
	return bool(frappe.db.exists("Email Account", {"enable_outgoing": 1}) or frappe.conf.get("mail_server"))


def _sent_today(sender, for_update=False):
	return frappe.db.get_values(DOCTYPE, {"owner": sender, "creation": [">=", today()]},
	                            ["name", "message", "creation", "status"], as_dict=True,
	                            for_update=for_update)


def _sender_label(sender):
	emp = frappe.db.get_value("Employee", {"user_id": sender, "status": "Active"},
	                          ["employee_name", "designation"], as_dict=True)
	if emp and emp.employee_name:
		return ", ".join(x for x in (emp.employee_name, emp.designation) if x)
	return frappe.utils.get_fullname(sender)


# ── the endpoints ────────────────────────────────────────────────────────────

@frappe.whitelist()
def notice_reach():
	"""What Compose offers this sender: counts only, no names (AC-22, AC-45)."""
	user = _require_sender("notice_reach")
	people = _people(user)
	return {
		"everyone": {"label": _everyone_label(user), "n": len(_users(people))},
		"targets": _targets(people),
		"email_active": email_is_active(),
		"sent_today": len(_sent_today(user)),
		"per_day": PER_DAY,
		"confirm_above": CONFIRM_ABOVE,
		"max_chars": MAX_CHARS,
	}


@frappe.whitelist()
def search_notice_people(q=None):
	"""In-scope Active people with a login whose name matches: id and name, at
	most 20 (AC-22)."""
	user = _require_sender("search_notice_people")
	q = str(q or "").strip()[:60]
	extra = [["employee_name", "like", "%" + q + "%"]] if q else []
	return [{"id": p.name, "name": p.employee_name} for p in _people(user, extra, limit=60)[:20]]


@frappe.whitelist(methods=["POST"])
def create_notice(message=None, audience_kind=None, company=None, branch=None, people=None,
                  when="now", send_at=None, email=0, confirmed=0):
	"""Write one notice, after every check the page also makes (SEC-1, 2, 3, 7, 8, 17).

	"Now" to 200 people or fewer is sent before this returns. "Now" to more, or
	"Later", is Scheduled and goes out from the scheduler as the sender."""
	user = _require_sender("create_notice")

	message = str(message or "").strip()
	if not message:
		frappe.throw(_("Write a message first."))
	if len(message) > MAX_CHARS:
		frappe.throw(_("A notice can be at most 300 characters."))
	# Stored HTML-escaped, so no desk view (print, report) can run it (SEC-9).
	# The limit above is on what the person typed; readers unescape it.
	message = html.escape(message)
	kind = KINDS.get(str(audience_kind or ""))
	if not kind:
		frappe.throw(_("Choose who it goes to."))
	ids = _chosen_ids(people) if kind == "Chosen people" else []

	later = when == "later"
	if later:
		if not send_at:
			frappe.throw(_("Choose a date and a time."))
		try:
			at = get_datetime(send_at)
		except Exception:
			frappe.throw(_("Choose a date and a time."))
		if not at or at <= now_datetime():
			frappe.throw(_("Choose a time that has not passed yet."))
	else:
		at = now_datetime()

	email = cint(email)
	if email and not email_is_active():
		frappe.throw(_("Email is switched off for your organisation, so a notice cannot go by email."))

	# One sender at a time: lock the sender's own User row, then read today's
	# notices with a locking read, which sees what a parallel request just
	# committed (a plain read could see an older snapshot, slice 021).
	frappe.db.get_value("User", user, "name", for_update=True)
	todays = _sent_today(user, for_update=True)

	soon = add_to_date(now_datetime(), seconds=-REPEAT_SECONDS)
	for t in todays:
		if t.message == message and get_datetime(t.creation) >= soon:
			# A double tap, or a retry after a lost answer: the first one stands.
			return _answer(frappe.get_doc(DOCTYPE, t.name), len(todays), repeat=True)
	if len(todays) >= PER_DAY:
		frappe.throw(_("You have sent 5 notices today. That is the limit for one day. You can send again tomorrow."))

	reach = len(_users(_resolve(user, kind, company, branch, ids)))
	if not reach:
		frappe.throw(_("No one is in your scope. Ask HR."))
	if reach > CONFIRM_ABOVE and not cint(confirmed):
		frappe.throw(_("This goes to {0} people. Confirm before sending.").format(reach))

	doc = frappe.get_doc({
		"doctype": DOCTYPE,
		"message": message,
		"audience_kind": kind,
		"audience_company": company if kind == "Company" else None,
		"audience_branch": branch if kind == "Branch" else None,
		"audience_people": json.dumps(ids) if ids else None,
		"sender_label": _sender_label(user),
		"send_at": at,
		"status": "Scheduled",
		"email_requested": email,
	})
	frappe.flags[CREATE_FLAG] = True
	try:
		doc.insert()
	finally:
		frappe.flags.pop(CREATE_FLAG, None)

	if not later and reach <= SEND_IN_REQUEST:
		# Kept even if the send below stops: then the scheduler resumes it.
		frappe.db.commit()
		send_one(doc.name)
		doc.reload()
	elif not later:
		_enqueue(doc.name, after_commit=True)
	return _answer(doc, len(todays) + 1, people_count=reach)


def _answer(doc, sent_today, repeat=False, people_count=None):
	return {"name": doc.name, "status": doc.status, "reached": cint(doc.reached),
	        "people": people_count if people_count is not None else cint(doc.reached),
	        "later": doc.status == "Scheduled" and get_datetime(doc.send_at) > now_datetime(),
	        "sent_today": sent_today, "repeat": 1 if repeat else 0}


@frappe.whitelist(methods=["POST"])
def cancel_notice(name=None):
	"""The owner cancels their own Scheduled notice (SEC-11, AC-36 to AC-38).

	The locked read comes first, so a cancel and the send job cannot both win."""
	user = _require_sender("cancel_notice")
	name = str(name or "")
	if not name or not frappe.db.exists(DOCTYPE, name):
		frappe.throw(_("That notice was not found."), frappe.DoesNotExistError)
	doc = frappe.get_doc(DOCTYPE, name, for_update=True)
	if doc.owner != user:
		refuse(_("You can cancel only notices you sent."), "076-SEC-11", "cancel_notice", DOCTYPE, name)
	if doc.status != "Scheduled":
		frappe.throw(_("This notice is already being sent or was sent, so it cannot be cancelled."))
	doc.status = "Cancelled"
	doc.save(ignore_version=False)    # the Version row is who cancelled it, and when (PRIV-3)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def my_sent_notices():
	"""The sender's own notices, newest first, at most 20, with counts only:
	never who received or read them (PRIV-4, AC-39, AC-40)."""
	user = _require_sender("my_sent_notices")
	rows = frappe.get_all(DOCTYPE, filters={"owner": user},
	                      fields=["name", "message", "audience_kind", "audience_company", "audience_branch",
	                              "audience_people", "send_at", "status", "status_reason", "email_note",
	                              "creation"],
	                      order_by="creation desc", limit=20)
	counts = {}
	if rows:
		# Other people's rows, read as two numbers per notice and nothing else.
		for c in frappe.get_all("Notification Log",
		                        filters={"document_type": DOCTYPE, "document_name": ["in", [r.name for r in rows]]},
		                        fields=["document_name", {"COUNT": "name", "as": "n"}, {"SUM": "read", "as": "r"}],
		                        group_by="document_name"):
			counts[c.document_name] = (cint(c.n), cint(c.r))
	everyone = _everyone_label(user)
	out = []
	for r in rows:
		if r.audience_kind == "Company":
			label = r.audience_company
		elif r.audience_kind == "Branch":
			label = r.audience_branch
		elif r.audience_kind == "Chosen people":
			label = _("Chosen people ({0})").format(len(json.loads(r.audience_people or "[]")))
		else:
			label = everyone
		reached, read = counts.get(r.name, (0, 0))
		out.append({"name": r.name, "message": html.unescape(r.message or ""), "audience_label": label,
		            "scheduled_for": str(r.send_at), "status": r.status,
		            "reason": r.status_reason or r.email_note or "",
		            "reached": reached, "read": read, "created": str(r.creation)})
	return out


@frappe.whitelist()
def notice_sender_holders():
	"""Who holds Notice Sender, for HR (PRIV-8, as the prototype draws it -
	Surbhi, 28 Oct 2026, over AC-107's "names only"): full name, job title, and
	who last changed that person's Notice Sender access and when. No email, no
	user id. "Last changed" is Frappe's own User history (Version), so it is
	empty for anyone who got the role without a saved change."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	if not {"HR Manager", "System Manager"} & set(frappe.get_roles(user)):
		refuse(_("Only HR can see who may send notices."), "076-PRIV-8", "notice_sender_holders")
	holders = frappe.get_all("Has Role", filters={"role": ROLE, "parenttype": "User"}, pluck="parent")
	holders = [h for h in holders if h not in ("Administrator", "Guest")]
	if not holders:
		return []
	users = frappe.get_all("User", filters={"name": ["in", holders], "enabled": 1}, fields=["name", "full_name"])
	if not users:
		return []
	ids = [u.name for u in users]
	titles = dict(frappe.get_all("Employee", filters={"user_id": ["in", ids], "status": "Active"},
	                             fields=["user_id", "designation"], as_list=True))
	changed = {}
	for v in frappe.get_all("Version", filters={"ref_doctype": "User", "docname": ["in", ids],
	                                             "data": ["like", "%" + ROLE + "%"]},
	                        fields=["docname", "owner", "creation"], order_by="creation desc"):
		changed.setdefault(v.docname, v)
	names = dict(frappe.get_all("User", filters={"name": ["in", list({v.owner for v in changed.values()})]},
	                            fields=["name", "full_name"], as_list=True)) if changed else {}
	out = []
	for u in users:
		v = changed.get(u.name)
		out.append({"name": u.full_name, "title": titles.get(u.name) or "",
		            "changed_by": names.get(v.owner) or "" if v else "",
		            "changed_on": str(v.creation)[:10] if v else ""})
	return sorted(out, key=lambda x: x["name"] or "")


# ── the send ─────────────────────────────────────────────────────────────────

def _enqueue(name, after_commit=False):
	frappe.enqueue("alvoraa_portal.announcements.send_one", queue="long", job_id="announcement-" + name,
	               deduplicate=True, enqueue_after_commit=after_commit, name=name)


def send_due_announcements():
	"""Scheduler, every tick: hand at most two due notices to the long queue.
	It writes no rows itself (AC-31). A "Sending" notice nobody has touched for
	10 minutes is due again: its worker stopped part way (AC-32)."""
	now = now_datetime()
	due = frappe.get_all(DOCTYPE, filters={"status": "Scheduled", "send_at": ["<=", now]},
	                     order_by="send_at asc", limit=PER_TICK, pluck="name")
	if len(due) < PER_TICK:
		due += frappe.get_all(DOCTYPE, filters={"status": "Sending",
		                                        "modified": ["<", add_to_date(now, minutes=-STALE_MINUTES)]},
		                      order_by="modified asc", limit=PER_TICK - len(due), pluck="name")
	for name in due:
		_enqueue(name)


def _write_rows(doc, users):
	"""One Notification Log row per person. Writing other people's rows is the
	one thing here that needs `ignore_permissions` (spec 5.5).

	The message is already HTML-escaped (the desk draws `subject` as HTML,
	SEC-9). `link` sends a desk bell click to the portal: a recipient may not
	open the Announcement record itself."""
	for u in users:
		frappe.get_doc({"doctype": "Notification Log", "type": "Alert", "document_type": DOCTYPE,
		                "document_name": doc.name, "from_user": doc.owner, "for_user": u, "link": PORTAL,
		                "subject": doc.message, "email_content": doc.message}).insert(ignore_permissions=True)


def _email(doc, users):
	emails = frappe.get_all("User", filters={"name": ["in", users]}, pluck="email")
	if not emails:
		return
	frappe.sendmail(recipients=emails,
	                subject=_("A notice from {0}").format(doc.sender_label.split(",")[0]),
	                message="<p>" + doc.message + "</p>",    # stored escaped
	                reference_doctype=DOCTYPE, reference_name=doc.name, add_unsubscribe_link=0)


def _count_rows(name):
	return frappe.db.count("Notification Log", {"document_type": DOCTYPE, "document_name": name})


def send_one(name):
	"""Send one notice, once, as its sender (US-4, US-5).

	A thin wrapper on purpose (SEC-21). If the send stops on an unexpected
	error, Frappe would log the traceback with every local value in it - the
	notice text and up to 200 logins. Here the only local is the notice id: the
	error is logged as the id and the error's class name, nothing else, and the
	notice is left as it was. A Scheduled one goes on the next tick; a Sending
	one resumes after 10 minutes, and three stalls end in Failed."""
	try:
		_send(name)
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(title="Notice send stopped",
		                 message="{0}: {1}".format(name, type(e).__name__),
		                 reference_doctype=DOCTYPE, reference_name=name)
		frappe.db.commit()


def _send(name):
	"""The send itself. The row lock is the first read, so two workers - or a
	worker and a cancel - cannot both act on it. Moving it to Sending and
	committing releases the lock and tells any later tick to leave it alone for
	10 minutes."""
	started = time.monotonic()
	doc = frappe.get_doc(DOCTYPE, name, for_update=True)
	now = now_datetime()
	if doc.status == "Scheduled":
		if get_datetime(doc.send_at) > now:
			return
		stalled = 0
	elif doc.status == "Sending":
		if get_datetime(doc.modified) > add_to_date(now, minutes=-STALE_MINUTES):
			return                                   # another worker is on it
		if cint(doc.stalled) >= MAX_STALLS:
			reached = _count_rows(name)
			doc.db_set({"status": "Failed", "reached": reached,
			            "status_reason": _("It stopped part way {0} times. {1} people got it.").format(MAX_STALLS, reached)})
			frappe.log_error(title="Notice send failed",
			                 message="{0}: stopped {1} times, {2} rows written".format(name, MAX_STALLS, reached),
			                 reference_doctype=DOCTYPE, reference_name=name)
			frappe.db.commit()
			_log(name, "failed", reached, started)
			return
		stalled = cint(doc.stalled) + 1
	else:
		return

	sender = doc.owner
	problem = _sender_problem(sender)
	people = []
	if not problem:
		ids = json.loads(doc.audience_people or "[]")
		people = _resolve(sender, doc.audience_kind, doc.audience_company, doc.audience_branch, ids, at_send=True)
		if not people:
			problem = _("No one the sender may reach is in this audience now.")
	if problem:
		doc.db_set({"status": "Not sent", "status_reason": problem})
		frappe.db.commit()
		_log(name, "not sent", 0, started)
		return

	doc.db_set({"status": "Sending", "stalled": stalled})
	frappe.db.commit()

	email_on = cint(doc.email_requested) and email_is_active()
	users = _users(people)
	reached = 0
	for i in range(0, len(users), CHUNK):
		chunk = users[i:i + CHUNK]
		have = set(frappe.get_all("Notification Log", filters={
			"document_type": DOCTYPE, "document_name": name, "for_user": ["in", chunk]}, pluck="for_user"))
		new = [u for u in chunk if u not in have]
		_write_rows(doc, new)
		if email_on and new:
			_email(doc, new)
		reached = _count_rows(name)
		doc.db_set({"reached": reached, "stalled": 0})
		frappe.db.commit()

	note = None
	if cint(doc.email_requested):
		note = _("Emailed") if email_on else _("email not sent: email is off")
	doc.db_set({"status": "Sent", "sent_at": now_datetime(), "reached": _count_rows(name), "email_note": note})
	frappe.db.commit()
	_log(name, "sent", doc.reached, started)


def _log(name, outcome, reached, started):
	"""One line per send: which notice, what happened, how many, how long."""
	frappe.logger("notices").info(json.dumps({"notice": name, "outcome": outcome, "reached": reached,
	                                          "seconds": round(time.monotonic() - started, 2)}))


# ── install ──────────────────────────────────────────────────────────────────

def make_role():
	"""The role, with no desk access of its own: giving it to an employee must
	not turn them into a desk user. Frappe makes the role WITH desk access when it
	first meets it in the Announcement permissions, so this runs after that on a
	new site (after_install) and before it on a live one (the patch)."""
	if frappe.db.exists("Role", ROLE):
		frappe.db.set_value("Role", ROLE, "desk_access", 0)
	else:
		frappe.get_doc({"doctype": "Role", "role_name": ROLE, "desk_access": 0}).insert()
