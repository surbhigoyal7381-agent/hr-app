"""The assembled portal pages must open and close the same tags (042 F1).

Why this exists
---------------
Slice 042 removed the "this week" presence card from the portal Home page. The
commit deleted the card's opening `<div>` and its two inner ones and left the
card's CLOSING `</div>` behind - one extra tag, on line 51 of
`templates/includes/ess/parts/home.html`.

A browser does not error on that. It silently re-parents everything after it.
`home-left-col` closed 25 lines early, so "My Goals" and "Team Goals" fell out
of the left column and the ENTIRE right-hand column - approvals and holidays -
fell out of the two-column grid. The page still rendered. It was simply laid
out wrong, on the live Home screen of every tenant, in go-live week.

Nothing in this repository could see it:

  * `check_app_integrity.py` reads Python imports.
  * `check_design_system.py` counts colours and fonts.
  * `check_undefined_js.js` and `check_portal_handlers.js` read JavaScript.
  * The jsdom tests under `run_dom_tests.js` drive the PREVIEW page
    (`hrms-employee-next.html`), not `hrms-employee.html`.

A layout fault that no test can see is worse than the fault. This check closes
that gap. Text only: no bench, no database, no site, no browser.

The two layers, and why both
----------------------------
**1. The assembled page must balance.** Each file under `ess/parts/` is a
FRAGMENT, and some are deliberately partial: `drawers.html` ends with
`</div><!-- /emp-app -->`, closing a container the frame opened. So "every file
balances" is the wrong rule and would have to be loosened until it caught
nothing. The right rule is the one that matches the failure: the page the
server really sends, with its includes, assets and markup parts expanded,
must balance - and must never close more than it has opened.

That is exactly what `alvoraa_portal/tests/portal_source.py` already builds, so
this check reads the page the same way every other check does. Its own guards
mean a page that lost its include tags fails rather than passing on a shell.

**2. Each fragment's net depth is pinned.** The assembled check says the page is
broken; it does not say which of twenty files broke it, because the line number
is a line in the assembled document. So each fragment's net tag depth is also
recorded here as an exact number. Change a fragment's balance and the check
names the file, the old number and the new one. Pinned with an equality, not a
"less than", so a fragment can neither gain nor silently lose a tag.

Jinja
-----
A tag opened inside `{% if %}` and closed inside `{% else %}` would look
unbalanced. No tracked file does that today, and the pin makes an attempt
visible rather than silently tolerated. Jinja statements and expressions are
stripped before the walk, so `{{ "</div>" }}` cannot confuse it.
"""
import argparse
import importlib.util
import io
import os
import re
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "alvoraa_portal", "alvoraa_portal")
PARTS_DIR = os.path.join(APP, "templates", "includes", "ess", "parts")


# Loaded by path, the way check_design_system.py does it: this script runs from
# the repository root, where the app is not importable.
def _portal_source():
	helper = os.path.join(APP, "tests", "portal_source.py")
	spec = importlib.util.spec_from_file_location("_tag_balance_portal_source", helper)
	mod = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(mod)
	return mod


# HTML elements that never carry a closing tag.
VOID = {
	"area", "base", "br", "col", "embed", "hr", "img", "input", "keygen",
	"link", "meta", "param", "source", "track", "wbr",
}

COMMENT = re.compile(r"<!--.*?-->", re.S)
JINJA = re.compile(r"\{%.*?%\}|\{\{.*?\}\}|\{#.*?#\}", re.S)
RAW_BODY = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.S | re.I)
TAG = re.compile(
	r"<\s*(/?)\s*([A-Za-z][A-Za-z0-9:-]*)"
	r"((?:[^>\"']|\"[^\"]*\"|'[^']*')*?)(/?)\s*>", re.S)

# Each fragment's net tag depth: opens minus closes. A partial fragment is
# allowed - it just has to stay the partial fragment it was.
#
# These numbers were read off the tree, not chosen. The three non-zero ones
# close containers the frame opens:
#   appraisals.html -1   ends  </div><!-- /main-content -->
#   drawers.html    -2   ends  </div><!-- /flex column --> and </div><!-- /emp-app -->
# home.html is 0 and was 0 on Wave 1. It went to -1 in Wave 2 and Wave 3, which
# is the bug this file is named after.
PINNED_DEPTH = {
	"appraisals.html": -1,
	"attendance.html": 0,
	"data-review.html": 0,
	"drawers.html": -2,
	"growth.html": 0,
	"home.html": 0,
	"next-home.html": 0,
	"next-inbox.html": 0,
	"org-settings.html": 0,
	"pay.html": 0,
	"policies.html": 0,
	"request-modals.html": 0,
	"requests.html": 0,
	"team.html": 0,
}


def _blank_out(text, pattern):
	"""Replace every match with the same number of newlines, so reported line
	numbers stay true to the text as written."""
	return pattern.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def strip(text):
	text = _blank_out(text, COMMENT)
	text = _blank_out(text, RAW_BODY)
	return _blank_out(text, JINJA)


def walk(text):
	"""Walk one document's tags.

	Returns (net_depth, problems). `net_depth` is opens minus closes, so a
	deliberately partial fragment reports a negative number rather than an
	error. `problems` holds only things that are wrong however the document is
	used: a close that does not match the open above it.
	"""
	text = strip(text)
	depth, floor, problems, stack = 0, 0, [], []

	for match in TAG.finditer(text):
		closing, name, _attrs, self_closing = match.groups()
		name = name.lower()
		if name in VOID or self_closing:
			continue
		line = text.count("\n", 0, match.start()) + 1

		if not closing:
			depth += 1
			stack.append((name, line))
			continue

		depth -= 1
		floor = min(floor, depth)
		if stack:
			open_name, open_line = stack.pop()
			if open_name != name:
				problems.append(
					"line %d: </%s> does not match <%s> opened on line %d"
					% (line, name, open_name, open_line))
	return depth, floor, problems, stack


def context(text, line, span=3):
	"""A few lines around a line number, for a human to find the place."""
	lines = text.splitlines()
	lo, hi = max(0, line - span - 1), min(len(lines), line + span)
	return "\n".join("    %5d | %s" % (n + 1, lines[n]) for n in range(lo, hi))


def check_assembled(source):
	"""The real rule: the page the server sends must balance."""
	failures = []
	pages = [("hrms-employee.html", source.read_page),
			 ("hrms-employee-next.html", source.read_preview)]

	for name, reader in pages:
		try:
			text = reader()
		except Exception as exc:  # PortalSourceError, or a file that moved
			failures.append((name, ["the page could not be assembled: %s" % exc], ""))
			continue

		depth, floor, problems, unclosed = walk(text)
		notes = list(problems)
		if depth != 0:
			notes.append(
				"the assembled page ends at depth %+d - it %s %d tag(s)"
				% (depth,
				   "closes" if depth < 0 else "leaves open",
				   abs(depth)))
		if floor < 0:
			notes.append(
				"at its worst the page had closed %d more tag(s) than it had "
				"opened, so everything after that point is re-parented" % -floor)
		for open_name, open_line in unclosed[:5]:
			notes.append("<%s> opened at assembled line %d is never closed"
						 % (open_name, open_line))
		if notes:
			hint = ""
			if unclosed:
				hint = context(strip(text), unclosed[0][1])
			failures.append((name, notes, hint))
	return failures


def check_pins(parts_dir=PARTS_DIR, pinned=PINNED_DEPTH):
	"""Attribution: each fragment stays the shape it was recorded as."""
	if not os.path.isdir(parts_dir):
		return ["the markup parts folder is missing: %s" % parts_dir]

	on_disk = sorted(n for n in os.listdir(parts_dir) if n.endswith(".html"))
	if not on_disk:
		return ["the markup parts folder holds no .html file - this check "
				"would otherwise print OK having read nothing"]

	notes = []
	for name in on_disk:
		text = io.open(os.path.join(parts_dir, name), encoding="utf-8",
					   errors="ignore").read()
		depth, _floor, problems, _unclosed = walk(text)
		for problem in problems:
			notes.append("parts/%s: %s" % (name, problem))
		if name not in pinned:
			notes.append(
				"parts/%s is new and has no pinned depth. It measures %+d. Add "
				"it to PINNED_DEPTH in this script, with a line saying why if "
				"it is not 0." % (name, depth))
		elif depth != pinned[name]:
			notes.append(
				"parts/%s now nets %+d tag(s); it was pinned at %+d. %s"
				% (name, depth, pinned[name],
				   "It closes one more than it opens - the 042 shape."
				   if depth < pinned[name] else
				   "It opens one more than it closes."))
	for name in sorted(set(pinned) - set(on_disk)):
		notes.append("parts/%s is pinned here but no longer exists - remove "
					 "its pin, deliberately." % name)
	return notes


def check(repo_root=REPO):
	"""0 when both assembled pages balance and every fragment holds its pin."""
	source = _portal_source()
	assembled = check_assembled(source)
	pins = check_pins()

	if assembled or pins:
		print("FAIL - the portal markup does not balance its tags:")
		for name, notes, hint in assembled:
			print("  %s (assembled)" % name)
			for note in notes:
				print("    %s" % note)
			if hint:
				print(hint)
		for note in pins:
			print("  %s" % note)
		print()
		print("The browser will not error. It re-parents everything after the")
		print("bad tag and lays the page out wrong. See 042 review F1.")
		return 1

	print("tag balance: 2 assembled pages, %d markup fragments" % len(PINNED_DEPTH))
	print("OK - both pages balance and every fragment holds its pinned depth")
	return 0


def self_test():
	"""The positive control: prove this check can FAIL.

	The first case is the real 042 bug, reduced: a removed card whose closing
	`</div>` was left behind. A guard nobody has watched fail is not a guard.
	"""
	walk_cases = [
		("the real 042 bug - a removed card left its closing div",
		 '<div class="grid">\n'
		 '  <div class="left">\n'
		 '    <div class="card">x</div>\n'
		 '    <!-- the card was removed here -->\n'
		 '    </div>\n'
		 '    <div class="goals">y</div>\n'
		 '  </div>\n'
		 '</div>\n', -1),
		("a div that is never closed", '<div><span>x</span>\n', 1),
		("balanced, with void elements and self-closing svg",
		 '<div class="card"><img src="a.png"><br>'
		 '<svg viewBox="0 0 24 24"><circle cx="1" cy="1" r="1"/></svg>'
		 '<input type="text"></div>\n', 0),
		("a stray closing div INSIDE a comment must not count",
		 '<div>\n  <!-- </div> -->\n</div>\n', 0),
		("a '<' inside a script body must not count",
		 '<div>\n<script>if (a < b) { }</script>\n</div>\n', 0),
		("a jinja expression holding a '</div>' must not count",
		 '<div>\n  {{ "</div>" }}\n</div>\n', 0),
		("a deliberately partial fragment reports its negative, not an error",
		 '  <div class="x">y</div>\n</div><!-- /emp-app -->\n', -1),
	]

	failed = 0
	for name, fragment, expected in walk_cases:
		depth, _floor, problems, _unclosed = walk(fragment)
		if depth != expected or problems:
			failed += 1
			print("SELF-TEST FAIL - %s: expected %+d, got %+d %s"
				  % (name, expected, depth, problems))
		else:
			print("  ok  %s" % name)

	# Tags closed in the wrong order must be reported however they net out.
	_d, _f, problems, _u = walk('<div><span>x</div></span>\n')
	if not problems:
		failed += 1
		print("SELF-TEST FAIL - tags closed in the wrong order were not caught")
	else:
		print("  ok  tags closed in the wrong order")

	# The pin layer must name the file when a fragment changes shape.
	root = tempfile.mkdtemp(prefix="tag-balance-self-test-")
	try:
		parts = os.path.join(root, "parts")
		os.makedirs(parts)
		io.open(os.path.join(parts, "home.html"), "w", encoding="utf-8").write(
			'<div class="a"><div class="b">x</div></div>\n  </div>\n')
		notes = check_pins(parts, {"home.html": 0})
		if not notes or not any("home.html" in n for n in notes):
			failed += 1
			print("SELF-TEST FAIL - a fragment that broke its pin was not named")
		else:
			print("  ok  a fragment that breaks its pin is named: %s" % notes[0])

		io.open(os.path.join(parts, "brand-new.html"), "w", encoding="utf-8").write(
			'<div>x</div>\n')
		notes = check_pins(parts, {"home.html": -1})
		if not any("brand-new.html" in n and "no pinned depth" in n for n in notes):
			failed += 1
			print("SELF-TEST FAIL - a new unpinned fragment slipped through")
		else:
			print("  ok  a new fragment with no pin is refused, not ignored")

		empty = os.path.join(root, "empty")
		os.makedirs(empty)
		if not check_pins(empty, {}):
			failed += 1
			print("SELF-TEST FAIL - the pin check passed having read no file")
		else:
			print("  ok  a scan that reads no file fails instead of passing")
	finally:
		shutil.rmtree(root, ignore_errors=True)

	if failed:
		print()
		print("FAIL - %d self-test case(s) wrong. This check cannot be trusted."
			  % failed)
		return 1
	print()
	print("OK - the check catches every broken shape and passes every good one")
	return 0


def main():
	parser = argparse.ArgumentParser(description="portal tag balance")
	parser.add_argument("--self-test", action="store_true",
						help="prove the check can fail, then exit")
	args = parser.parse_args()
	return self_test() if args.self_test else check()


if __name__ == "__main__":
	sys.exit(main())
