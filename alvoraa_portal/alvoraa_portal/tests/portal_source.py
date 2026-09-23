"""Read hrms-employee.html the way the server does: with its includes expanded.

Slice 034 US-10 (AC-36, AC-37, OPS-6). The page used to be one 18,000-line file
that every check opened directly. It is now a short page that pulls in about two
dozen Jinja include files. A check that keeps opening the page alone would still
pass -- while reading a 52-line shell and checking almost nothing. That is worse
than no check, so every check now comes through here.

Two guards make silence impossible:

  * at least one include tag must be expanded, and
  * every file under templates/includes/ess/ must be reached by the expansion.

So deleting the tags from the page, or leaving an include file behind that
nothing pulls in, fails loudly instead of quietly checking less.

The helper is deliberately importable two ways, because Python tests run inside
the bench (where the app is importable) and the CI scripts in scripts/ run from
the repository root (where it is not). The scripts load this file by path.
"""

import os
import re

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WWW = os.path.join(APP_ROOT, "www")
PORTAL_PAGE = os.path.join(WWW, "hrms-employee.html")
ESS_DIR = os.path.join(APP_ROOT, "templates", "includes", "ess")

# Only our own include files are expanded. design_system.html and brand_color.html
# are shared with five other pages and were never part of this page's source.
ESS_PREFIX = "templates/includes/ess/"
INCLUDE_RE = re.compile(rb'\{%\s*include\s+"(templates/includes/ess/[^"]+)"\s*%\}')

MAX_DEPTH = 5


class PortalSourceError(RuntimeError):
	"""The page and its include files no longer agree. Never pass quietly."""


def ess_files_on_disk(ess_dir=ESS_DIR):
	"""Every include file that exists, as app-relative Jinja paths."""
	found = set()
	for base, _dirs, names in os.walk(ess_dir):
		for n in names:
			full = os.path.join(base, n)
			rel = os.path.relpath(full, APP_ROOT).replace(os.sep, "/")
			found.add(rel)
	return found


def expand_bytes(raw, used, app_root=APP_ROOT, _depth=0):
	"""Paste every ess include file where its tag sits, exactly as Jinja does.

	Jinja drops one trailing newline from each template and keeps the newline
	that follows the tag, so replacing 'tag + newline' with the file's bytes
	reproduces the server's output byte for byte. `used` collects the files that
	were actually pulled in, so the caller can prove none was left behind.
	"""
	if _depth > MAX_DEPTH:
		raise PortalSourceError("include files are nested more than %d deep" % MAX_DEPTH)

	def swap(m):
		rel = m.group(1).decode("utf-8")
		path = os.path.join(app_root, *rel.split("/"))
		if not os.path.exists(path):
			raise PortalSourceError("the page includes %s, which does not exist" % rel)
		used.add(rel)
		with open(path, "rb") as fh:
			body = fh.read()
		return expand_bytes(body, used, app_root, _depth + 1)

	# The tag sits alone on its line, so take that line's newline with it.
	out = re.sub(INCLUDE_RE.pattern + rb"\r?\n", swap, raw)
	# A tag sharing its line with other markup still works, just without one.
	return INCLUDE_RE.sub(swap, out)


def page_bytes(path=PORTAL_PAGE, check=True):
	"""The page with its includes expanded, as raw bytes (CRLF, BOM and all)."""
	with open(path, "rb") as fh:
		raw = fh.read()
	used = set()
	out = expand_bytes(raw, used)
	if check and os.path.abspath(path) == os.path.abspath(PORTAL_PAGE):
		_assert_nothing_went_quiet(used)
	return out


def _assert_nothing_went_quiet(used):
	if not used:
		raise PortalSourceError(
			"hrms-employee.html has no ess include tags. Either the page was "
			"flattened or this helper is reading the wrong file - either way "
			"every check calling it would now be checking a shell."
		)
	on_disk = ess_files_on_disk()
	orphans = on_disk - used
	if orphans:
		raise PortalSourceError(
			"these include files exist but nothing includes them, so their "
			"contents are checked by nobody: " + ", ".join(sorted(orphans))
		)


def read_page(path=PORTAL_PAGE, encoding="utf-8", errors="strict"):
	"""The expanded page as text, with universal newlines, like open() gives."""
	text = page_bytes(path).decode(encoding, errors)
	return text.replace("\r\n", "\n").replace("\r", "\n")
