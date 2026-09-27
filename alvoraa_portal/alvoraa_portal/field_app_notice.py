"""The words of the setup notice, versioned, as data.

**Why this file exists.** The notice a person reads before their face and
position start being recorded is the most important text in this product. Until
now its words lived in one place - the HTML of the web check-in page - and the
version was a bare string in another. The phone app, the desk and the web page
would each have grown their own copy, and three copies of a legal notice drift.

So the words are data here, one entry per version, and every screen renders from
this. Changing what a person is asked to agree to is then a **new version**: one
block of data and a version bump, not an edit scattered across three files.

Two rules, and a test holds each of them:

1. **A published version's text is never edited.** If the words change, add a
   version. Somebody who agreed on Monday agreed to Monday's words, and a record
   that names a version whose text has since been rewritten answers nothing.
2. **The current version's exact words are pinned by a test.** That is what
   stops a quiet change to what people agree to. It is deliberately a pin on the
   words rather than a ban on particular vocabulary: which words are right is a
   question for the user and for counsel, and a test that bans a word would fight
   that decision instead of protecting it.

The retention line is NOT in here. It quotes the tenant's own setting, which the
tenant may change without a new notice version, so it is filled in at request
time from `photo_retention_days()`. The words are versioned; the number is
today's truth.
"""

from frappe import _

from alvoraa_portal.field_app_photos import photo_retention_days

# The version shown today. It is a date, because "which words did they see" is
# always a question about a moment.
#
# ALV-43 (2026-09-22): the app now records the phone's model name at setup
# (AC-220), and the old version's "What we record" row never said so. D19's
# review named this before any pilot user agreed to the old words - see
# 01b-ux-design.md's "Read this first" §2 and Decision D19. This is a NEW
# version, not an edit of the old one (the rule below): "2026-09-13" is
# unchanged and stays in NOTICE forever.
CURRENT_VERSION = "2026-09-22"

# version -> the notice. `rows` are (heading, body); a body of None means the
# line is filled in at request time (the retention line). `agree` is the exact
# words beside the tick box.
NOTICE = {
	"2026-09-13": {
		"title": "Before you start",
		"rows": [
			("What we record",
			 "A photo of you, where you are, and the time — only when you press "
			 "Check In or Check Out."),
			("What we do not record",
			 "Nothing between punches. You are not tracked while you work."),
			("Why",
			 "To mark your attendance, and to confirm you were at your workplace."),
			("Who can see it",
			 "HR and your manager. Not your colleagues."),
			("How long", None),
			("Your rights",
			 "Ask HR to see what was recorded about you, or to correct it."),
		],
		"agree": "I have read this and I understand.",
		"what_changed": "",
	},
	# ALV-43 / D19: the only change from "2026-09-13" is the added sentence in
	# "What we record", naming the phone's model name (PRIV-2). Every other
	# row is byte-for-byte the same as before - this is not a rewrite, it is
	# one disclosure that was missing.
	"2026-09-22": {
		"title": "Before you start",
		"rows": [
			("What we record",
			 "A photo of you, where you are, and the time — only when you press "
			 "Check In or Check Out. When you set up: this phone's model name."),
			("What we do not record",
			 "Nothing between punches. You are not tracked while you work."),
			("Why",
			 "To mark your attendance, and to confirm you were at your workplace."),
			("Who can see it",
			 "HR and your manager. Not your colleagues."),
			("How long", None),
			("Your rights",
			 "Ask HR to see what was recorded about you, or to correct it."),
		],
		"agree": "I have read this and I understand.",
		"what_changed": "We now tell you that we record this phone's model name when you set up.",
	},
}


# A stable name for each part of the notice, so the phone app can put the
# right picture beside it whatever language the heading is shown in (ALV-133,
# E-4). Keyed on the English heading as written in NOTICE, before translation.
# This is not part of the words: adding or reading a key changes nothing a
# person agrees to, so it needs no new version. Every heading of every version
# must have one; a test holds that.
ROW_KEYS = {
	"What we record": "record",
	"What we do not record": "not_record",
	"Why": "why",
	"Who can see it": "who",
	"How long": "how_long",
	"Your rights": "rights",
}


def rows_for(version=None, retention_days=None):
	"""The notice's lines, with the retention line filled in for this tenant.

	Each line is {"key", "heading", "body"}; `key` is the stable name above."""
	entry = NOTICE.get(version or CURRENT_VERSION)
	if not entry:
		return []
	days = photo_retention_days() if retention_days is None else retention_days
	out = []
	for heading, body in entry["rows"]:
		if body is None:
			body = retention_line(days)
		out.append({"key": ROW_KEYS.get(heading, ""), "heading": _(heading), "body": body})
	return out


def retention_line(retention_days=None):
	"""The one line that is not versioned: how long this tenant keeps photos.

	Shared by the notice and by the HR Settings screen (AC-23), so the person
	reading the notice and the HR manager reading the settings are told the same
	thing in the same words.
	"""
	days = photo_retention_days() if retention_days is None else retention_days
	if days:
		return _("Check-in photos are kept for {0} days, then deleted.").format(days)
	return _("Check-in photos are kept until your organisation removes them.")


def agree_wording(version=None):
	"""The exact words beside the tick box, for the version asked for."""
	entry = NOTICE.get(version or CURRENT_VERSION)
	return entry["agree"] if entry else ""


def what_changed(version=None):
	entry = NOTICE.get(version or CURRENT_VERSION)
	return entry["what_changed"] if entry else ""


def facts(version=None):
	"""Everything a screen needs to draw the notice, in one call."""
	days = photo_retention_days()
	version = version or CURRENT_VERSION
	return {
		"version": version,
		"retention_days": days,
		"rows": rows_for(version, days),
		"agree": agree_wording(version),
		"what_changed": what_changed(version),
	}
