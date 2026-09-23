"""Slice 042, SEC-9 / AC-59: retiring the card is not retiring the endpoint.

**What was there.** `hr_api`'s week-presence endpoint was whitelisted (its
name is assembled below rather than written out, so this file does not trip its
own check). It returned
NAMED rows - `employee_name`, `designation` and `image` - with a per-day
in / away / due / off state for each person, and when the caller had no direct
reports it fell back to their whole **department**, capped at 40. So any
signed-in person could ask it, by hand, for forty colleagues' week of absences.

**What Wave 2 does.** It replaces the card with `home_api._team_today`: three
numbers, no names, a minimum group size, and peers defined as people with the
same manager - no department fallback at all.

**Why this file exists.** Revision 1 of the spec called this an "extend" and
claimed the visibility was narrower. That was true of the CARD and false of the
ENDPOINT: a function nobody draws is still a function anybody can call. Removing
the card and leaving the endpoint would be "a hidden menu is not a permission"
in a different hat.

So two checks, and the second is the one that matters:

  (a) the name appears in **no source file of this app** - not in a call, not in
      a comment, not in a string. The name is deliberately not written in the
      explanatory comments either, so this check can be absolute;
  (b) calling it by hand gets a missing method.

`docs/` is not scanned. The spec and the decision register have to be able to
say what was removed and why.
"""

import os

from frappe.tests.utils import FrappeTestCase

import alvoraa_portal

# Written in pieces so that this file, which is itself scanned, does not carry
# the name it is checking for.
GONE = "get_" + "week_" + "presence"

SUFFIXES = (".py", ".js", ".html", ".css", ".json", ".md")


def _app_root():
	return os.path.dirname(os.path.abspath(alvoraa_portal.__file__))


class TestTheWeekPresenceEndpointIsGone(FrappeTestCase):

	def test_the_name_appears_in_no_source_file(self):
		root = _app_root()
		found = []
		scanned = 0
		for base, dirs, files in os.walk(root):
			dirs[:] = [d for d in dirs
			           if d not in ("__pycache__", "node_modules", ".git")]
			for name in files:
				if not name.endswith(SUFFIXES):
					continue
				path = os.path.join(base, name)
				scanned += 1
				try:
					with open(path, encoding="utf-8", errors="ignore") as fh:
						if GONE in fh.read():
							found.append(os.path.relpath(path, root))
				except OSError:
					continue
		# The walk really did look at this app, so an empty `found` means
		# something. Without this the test passes on a typo in the path.
		self.assertGreater(scanned, 50,
		                   "only %d files were scanned - the walk is wrong, so "
		                   "the check below proved nothing" % scanned)
		self.assertEqual(found, [],
		                 "the retired week-presence endpoint is named in: %s"
		                 % (found,))

	def test_calling_it_by_hand_finds_nothing(self):
		from alvoraa_portal import hr_api

		self.assertFalse(hasattr(hr_api, GONE),
		                 "the endpoint is still importable, so it is still "
		                 "callable over the API")
		# Its private helper went with it - a helper nobody calls is how a
		# deleted feature grows back.
		self.assertFalse(hasattr(hr_api, "_holiday_dates"))
