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

Marking a notice read is Frappe's own `mark_as_read(docname)`, which only ever
changes a row where `for_user` is the caller. There is no wrapper to get wrong.
"""

import html

import frappe
from frappe import _
from frappe.utils import add_days, cint, now_datetime

from alvoraa_portal import grooming

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

	# An announcement row is the person's own copy: nothing more to gate.
	alerts = [r for r in rows if r.document_type != ANNOUNCEMENT]
	allowed = grooming._readable(user, alerts) if alerts else set()
	shown = [r for r in rows if r.document_type == ANNOUNCEMENT
	         or (r.document_type, r.document_name) in allowed]
	# Pinned first, then newest first (the sort keeps creation order inside each).
	shown.sort(key=lambda r: r.document_type != ANNOUNCEMENT)
	unread = [r for r in shown if not r.read]

	chosen = (sorted(shown, key=lambda r: bool(r.read)) if see_all else unread[:CARD_ROWS])
	# Grooming links open the day only while grooming is on (as the old bell did).
	on = grooming.is_on() if any(r.document_type != ANNOUNCEMENT for r in chosen) else False
	sent = [r.document_name for r in chosen if r.document_type == ANNOUNCEMENT]
	senders = dict(frappe.get_all(ANNOUNCEMENT, filters={"name": ["in", sent]},
	                              fields=["name", "sender_label"], as_list=True)) if sent else {}
	return {
		"unread": len(unread),
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
