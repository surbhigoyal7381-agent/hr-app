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
CURRENT_VERSION = "2026-09-13"

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
}


def rows_for(version=None, retention_days=None):
	"""The notice's lines, with the retention line filled in for this tenant."""
	entry = NOTICE.get(version or CURRENT_VERSION)
	if not entry:
		return []
	days = photo_retention_days() if retention_days is None else retention_days
	out = []
	for heading, body in entry["rows"]:
		if body is None:
			body = (_("Check-in photos are kept for {0} days, then deleted.").format(days)
			        if days else
			        _("Check-in photos are kept until your organisation removes them."))
		out.append({"heading": _(heading), "body": body})
	return out


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
