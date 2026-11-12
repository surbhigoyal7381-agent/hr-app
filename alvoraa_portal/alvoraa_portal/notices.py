"""Slice 076, Part A: the one answer to "what notices have I not read?".

The Notices card on Home, the number on the bell and the "See all" sheet all
read this one function, so the card's "N unread" and the bell cannot disagree.
Nothing else in the portal counts notices.

A notice is a grooming alert (a Notification Log row about a grooming mark or
review) or, from Part B, an announcement a Notice Sender sent. Announcements come
first ("Pinned") with who sent them; their text is stored HTML-escaped for the
desk (SEC-9), so it is unescaped here and the page escapes it again on the way in.

**Own rows only.** The query names the caller as `for_user` and Frappe's own
permission condition for Notification Log says the same, so a colleague's row
cannot come back whatever the client sends. A row is shown only while its reader
may still read the document it is about (`grooming._readable`, the same gate the
old bell used).

**Fixed fields only.** A row carries its name, the sentence, the link, the time
and whether it is read. Nothing else leaves the server.

**Bounded.** One read of at most `READ_CAP` rows, then the grooming gate (a flat
handful of queries). The cost does not grow with headcount: it is this person's
own rows.

Marking ONE notice read is Frappe's own `mark_as_read(docname)`, which only ever
changes a row where `for_user` is the caller. There is no wrapper to get wrong.
Marking them ALL read is `mark_all_seen` below, which is a wrapper, and the two
filter terms in it are the whole of its security - see its docstring.
"""

import html

import frappe
from frappe import _
from frappe.utils import add_days, cint, now_datetime

from alvoraa_portal import grooming
from alvoraa_portal.field_app_limits import SELF_KEY, _limited

# The kinds of document a notice may be about.
ANNOUNCEMENT = "Announcement"
NOTICE_DOCTYPES = (grooming.MARK, grooming.REVIEW, ANNOUNCEMENT)

CARD_ROWS = 5        # what the Home card shows (design 4.2)
READ_CAP = 100       # the most rows one call reads
SEE_ALL_DAYS = 30    # read notices stay in "See all" this long


@frappe.whitelist()
def notices_feed(see_all=0):
	"""The caller's notices.

	`see_all=0`: the unread ones, newest first, at most `CARD_ROWS` (the card).
	`see_all=1`: the last 30 days, unread first (the sheet, and the bell).

	`unread` is the true count of unread notices the caller may still read.
	`any` is whether they have ever had one in the window, so an empty card can
	say "You are up to date" or "No notices". `can_send` is whether the caller
	holds Notice Sender, so the card shows "Send a notice" (the endpoints check
	again, AC-51).

	Slice 083 (AC-24 to AC-27): `unread` used to be counted from `shown`, which
	came from a read already cut off at `READ_CAP`. A person with 150 unread
	notices was told 100, the bell said "99+", and clearing every notice the
	screen offered left the bell at 99+ - the one failure the bell exists to
	prevent. It is now counted on its own, uncapped, and `capped` says when the
	LIST was cut so the page can say so in words.

	Two extra statements, and they are split by kind on purpose (OPS-13):

	  * an announcement row is the person's own copy, so a plain `COUNT` is
	    exact and needs no gate;
	  * a grooming row is only readable while its mark or review still is, so
	    its rows are folded into the SINGLE `_readable` call this function
	    already makes. A second `_readable` call would break the <= 14
	    statement ceiling, and a plain `COUNT(*)` would count notices about
	    marks the reader may no longer see (AC-26).
	"""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	see_all = cint(see_all)

	rows = frappe.get_list(
		"Notification Log",
		filters={"for_user": user, "document_type": ["in", list(NOTICE_DOCTYPES)]},
		# Unread stays whatever its age; read ones stay for 30 days.
		or_filters=[["read", "=", 0], ["creation", ">=", add_days(now_datetime(), -SEE_ALL_DAYS)]],
		fields=["name", "subject", "link", "creation", "read", "document_type", "document_name"],
		order_by="creation desc", limit_page_length=READ_CAP)

	# Every unread grooming notice, however old and however many - this is the
	# read the capped one above cannot stand in for. Three fields, no subject,
	# so a long backlog costs rows and not bytes. `for_user` is named here as
	# well as being pinned by Frappe's own condition: it is the term that makes
	# this the caller's own count and nothing else (SEC-1).
	open_alerts = frappe.get_list(
		"Notification Log",
		filters={"for_user": user, "read": 0,
		         "document_type": ["in", [grooming.MARK, grooming.REVIEW]]},
		fields=["name", "document_type", "document_name"], limit_page_length=0)

	# An announcement row is the person's own copy: nothing more to gate.
	alerts = [r for r in rows if r.document_type != ANNOUNCEMENT]
	# ONE gate call for both sets. `_readable` asks a fixed number of queries
	# whatever the row count - longer IN lists, not more queries - and it keys
	# on (doctype, name), so the overlap between the two sets costs nothing.
	gate = alerts + open_alerts
	allowed = grooming._readable(user, gate) if gate else set()
	shown = [r for r in rows if r.document_type == ANNOUNCEMENT
	         or (r.document_type, r.document_name) in allowed]
	# Pinned first, then newest first (the sort keeps creation order inside each).
	shown.sort(key=lambda r: r.document_type != ANNOUNCEMENT)
	unread = [r for r in shown if not r.read]

	unread_total = (
		frappe.db.count("Notification Log",
		                {"for_user": user, "document_type": ANNOUNCEMENT, "read": 0})
		+ sum(1 for r in open_alerts
		      if (r.document_type, r.document_name) in allowed))

	chosen = (sorted(shown, key=lambda r: bool(r.read)) if see_all else unread[:CARD_ROWS])
	# Grooming links open the day only while grooming is on (as the old bell did).
	on = grooming.is_on() if any(r.document_type != ANNOUNCEMENT for r in chosen) else False
	sent = [r.document_name for r in chosen if r.document_type == ANNOUNCEMENT]
	senders = dict(frappe.get_all(ANNOUNCEMENT, filters={"name": ["in", sent]},
	                              fields=["name", "sender_label"], as_list=True)) if sent else {}
	return {
		"unread": unread_total,
		# The LIST was cut, not the count. `get_inbox` already returns `cap`,
		# `shown` and `capped` per part for exactly this reason, so this is the
		# same honesty on the sibling endpoint, not a new idea.
		"capped": len(rows) >= READ_CAP,
		"any": bool(shown),
		"can_send": 1 if "Notice Sender" in frappe.get_roles(user) else 0,
		"items": [{
			"name": r.name,
			"kind": "announcement" if r.document_type == ANNOUNCEMENT else "alert",
			"from": senders.get(r.document_name) if r.document_type == ANNOUNCEMENT else None,
			"text": html.unescape(r.subject or "") if r.document_type == ANNOUNCEMENT else r.subject,
			"link": r.link if on and str(r.link or "").startswith("/hrms-employee?grooming=") else None,
			"when": str(r.creation),
			"read": 1 if r.read else 0,
		} for r in chosen],
	}


@frappe.whitelist(methods=["POST"])
@_limited(SELF_KEY, "user", limit=30)
def mark_all_seen():
	"""Mark every unread notice of the caller's own three kinds as read.

	Slice 083, US-9. Moved here from `grooming.my_notices_seen`, which had no
	live caller and cleared two of the three kinds from the wrong module. One
	name, one place, and `NOTICE_DOCTYPES` stays single-sourced - the filter
	IS the constant the feed above reads, so the two can never drift apart.

	**The two filter terms are the whole of the security here, and Frappe
	checks neither.** `frappe.db.set_value` with a dict filter issues one
	direct `UPDATE` through the query builder: no permission condition, no
	`has_permission` call, nothing. So:

	  * `for_user` is what stops this clearing every colleague's notices. A
	    wrong write here is silent and unlogged and nobody would report it,
	    which is why it has an assertion of its own (AC-32).
	  * `document_type` is what stops it clearing the caller's own Desk
	    notifications that this page never showed. DTC carries 902 unread
	    `Employee` rows and PPJ's heaviest user 406 (AC-31).

	Frappe's own `mark_all_as_read` filters on `for_user` ALONE, so it would
	clear rows this page has never shown. That is why this is not a call to it.

	It takes no arguments at all, so there is no doctype, field, user or filter
	a browser can post. One set-based statement, not a loop: 86 unread notices
	cost one `UPDATE`, not 86. `update_modified=False` keeps it to that one
	statement - the named cost is that nothing records WHEN a bulk clear
	happened, accepted in the spec (section 14) because no decision turns on it.

	Safe to run twice: it sets `read = 1` where `read = 0`, so a retry, a second
	tap or a second handset matches nothing and writes nothing.
	"""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	frappe.db.set_value(
		"Notification Log",
		{"for_user": user, "read": 0,
		 "document_type": ["in", list(NOTICE_DOCTYPES)]},
		"read", 1, update_modified=False)
	return {"ok": 1}
