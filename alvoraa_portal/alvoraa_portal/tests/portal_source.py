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
# Slice 034 Wave 1. There are TWO portal pages now, not one: the live page and
# the preview page that carries the new frame until the swap. Every file under
# templates/includes/ess/ and public/*/ess/ must be reached by ONE of them - so
# the orphan check below asks both, and a file belonging to neither still fails
# loudly. Without this, adding the frame to the preview page would have made the
# live page's guard call every new file an orphan, and the honest fix would have
# looked like loosening the guard.
PREVIEW_PAGE = os.path.join(WWW, "hrms-employee-next.html")
ESS_DIR = os.path.join(APP_ROOT, "templates", "includes", "ess")

# OPS-31. The frame's styles and the portal script are no longer Jinja includes.
# They are ordinary static files under public/, pulled in by <link> and <script
# src>. A check that only expanded include tags would now be reading a page with
# no CSS and no JavaScript in it - the exact silent failure this helper exists to
# stop - so the asset tags are expanded too, back into <style> and <script>
# blocks, which is what every caller already knows how to read.
ASSET_DIRS = (
	os.path.join(APP_ROOT, "public", "css", "ess"),
	os.path.join(APP_ROOT, "public", "js", "ess"),
)

# Only our own include files are expanded. design_system.html and brand_color.html
# are shared with five other pages and were never part of this page's source.
ESS_PREFIX = "templates/includes/ess/"
INCLUDE_RE = re.compile(rb'\{%\s*include\s+"(templates/includes/ess/[^"]+)"\s*%\}')

# <link rel="stylesheet" href="/assets/alvoraa_portal/css/ess/frame.css?v=123">
LINK_RE = re.compile(
	rb'<link[^>]*href="/assets/alvoraa_portal/(css/ess/[^"?]+)(?:\?[^"]*)?"[^>]*>')
# <script src="/assets/alvoraa_portal/js/ess/portal.js?v=123" defer></script>
SCRIPT_RE = re.compile(
	rb'<script[^>]*src="/assets/alvoraa_portal/(js/ess/[^"?]+)(?:\?[^"]*)?"[^>]*>\s*</script>')

# {{ ess_part("home") }} pastes a piece of the page's markup that holds no Jinja
# and is therefore never compiled (see alvoraa_portal/ess_parts.py). It is how
# the page is split by area without spending Frappe's 32 template cache slots.
PART_RE = re.compile(rb'\{\{\s*ess_part\(\s*"([a-z0-9-]+)"\s*\)\s*\}\}')
PARTS_DIR = os.path.join(ESS_DIR, "parts")

MAX_DEPTH = 5

# Written with chr() rather than escape sequences, because this file is edited
# by scripts often enough that a mangled backslash has already cost an hour.
CR_ONLY = chr(13)
LF_ONLY = chr(10)
CRLF = CR_ONLY + LF_ONLY


class PortalSourceError(RuntimeError):
	"""The page and its include files no longer agree. Never pass quietly."""


def ess_parts_on_disk(parts_dir=PARTS_DIR):
	"""Every markup part that exists, by name."""
	if not os.path.isdir(parts_dir):
		return set()
	return {n[:-5] for n in os.listdir(parts_dir) if n.endswith(".html")}


def expand_parts(raw, used, parts_dir=PARTS_DIR):
	"""Paste each markup part where its tag sits, exactly as the server does.

	ess_part() returns the file's bytes unchanged and Jinja keeps the newline
	after the tag, so replacing 'tag + newline' with 'bytes + newline' is what
	the page really becomes.
	"""

	def swap(m):
		name = m.group(1).decode("utf-8")
		path = os.path.join(parts_dir, name + ".html")
		if not os.path.exists(path):
			raise PortalSourceError("the page asks for part %s, which does not exist" % name)
		used.add(name)
		with open(path, "rb") as fh:
			return fh.read()

	return PART_RE.sub(swap, raw)


def ess_assets_on_disk(dirs=ASSET_DIRS):
	"""Every static frame file that exists, as app-relative public/ paths."""
	found = set()
	for d in dirs:
		if not os.path.isdir(d):
			continue
		for base, _dirs, names in os.walk(d):
			for n in names:
				full = os.path.join(base, n)
				rel = os.path.relpath(full, os.path.join(APP_ROOT, "public"))
				found.add(rel.replace(os.sep, "/"))
	return found


def expand_assets(raw, used, app_root=APP_ROOT):
	"""Paste each static frame file back where its tag sits.

	A stylesheet comes back inside <style>, a script inside <script>, so callers
	that scan for CSS rules or for JavaScript keep finding both where they were.
	"""

	def swap(m, tag):
		rel = m.group(1).decode("utf-8")
		path = os.path.join(app_root, "public", *rel.split("/"))
		if not os.path.exists(path):
			raise PortalSourceError("the page loads %s, which does not exist" % rel)
		used.add(rel)
		with open(path, "rb") as fh:
			body = fh.read()
		nl = b"\r\n"
		return b"<" + tag + b">" + nl + body + nl + b"</" + tag + b">"

	out = LINK_RE.sub(lambda m: swap(m, b"style"), raw)
	return SCRIPT_RE.sub(lambda m: swap(m, b"script"), out)


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


def _reached_by(path):
	"""Every include file, asset and part one page pulls in. No guards."""
	with open(path, "rb") as fh:
		raw = fh.read()
	used, assets, parts = set(), set(), set()
	out = expand_bytes(raw, used)
	out = expand_assets(out, assets)
	expand_parts(out, parts)
	return used, assets, parts


def preview_reach():
	"""What the preview page reaches. Empty when the page is not there yet."""
	if not os.path.exists(PREVIEW_PAGE):
		return set(), set(), set()
	return _reached_by(PREVIEW_PAGE)


def page_bytes(path=PORTAL_PAGE, check=True):
	"""The page with its includes expanded, as raw bytes (CRLF, BOM and all)."""
	with open(path, "rb") as fh:
		raw = fh.read()
	used = set()
	out = expand_bytes(raw, used)
	assets = set()
	out = expand_assets(out, assets)
	parts = set()
	out = expand_parts(out, parts)
	if check and os.path.abspath(path) == os.path.abspath(PORTAL_PAGE):
		_assert_nothing_went_quiet(used, assets, parts)
	return out


def preview_bytes():
	"""The preview page with its include, stylesheet and script expanded.

	The same treatment the live page gets, so a check can read the new frame's
	markup, styles and script as one document. It has its own guard: the frame
	include and both asset files must be reached, or the preview page has been
	emptied and every check reading it would be reading a shell.
	"""
	with open(PREVIEW_PAGE, "rb") as fh:
		raw = fh.read()
	used, assets, parts = set(), set(), set()
	# Slice 042: the preview page's frame pastes markup parts in too - Home's
	# and the Inbox's skeletons. Without expanding them this helper hands every
	# check a page with an unexpanded ess_part() tag in it as text.
	out = expand_parts(expand_assets(expand_bytes(raw, used), assets), parts)
	if not parts:
		raise PortalSourceError(
			"hrms-employee-next.html asks for no markup parts - the skeletons "
			"are gone, or this helper is reading the wrong file.")
	if not used:
		raise PortalSourceError(
			"hrms-employee-next.html includes no ess file - the frame markup is "
			"gone, or this helper is reading the wrong file.")
	if not assets:
		raise PortalSourceError(
			"hrms-employee-next.html loads no /assets/alvoraa_portal frame files "
			"- the preview page has no styles and no script.")
	return out


def _universal(text):
	"""CRLF and CR both become LF, the way open() in text mode does."""
	return text.replace(CRLF, LF_ONLY).replace(CR_ONLY, LF_ONLY)


def read_preview():
	"""The expanded preview page as text, with universal newlines."""
	return _universal(preview_bytes().decode("utf-8"))


def _assert_nothing_went_quiet(used, assets=None, parts=None):
	if parts is not None:
		if not parts:
			raise PortalSourceError(
				"hrms-employee.html asks for no markup parts. Either the page "
				"lost its ess_part() tags or this helper is reading the wrong "
				"file - either way every check calling it is reading a page with "
				"almost no markup in it.")
		# Slice 042: TWO pages ask for parts now. A part the PREVIEW page pastes
		# in - Home's and the Inbox's skeletons - is not an orphan just because
		# the live page does not ask for it. Exactly the allowance the asset
		# check below already makes.
		stranded = ess_parts_on_disk() - parts - preview_reach()[2]
		if stranded:
			raise PortalSourceError(
				"these markup parts exist but the page never asks for them, so "
				"their contents are checked by nobody: " + ", ".join(sorted(stranded)))
	if assets is not None:
		if not assets:
			raise PortalSourceError(
				"hrms-employee.html loads no /assets/alvoraa_portal frame files. "
				"Either the page lost its <link> and <script src> tags or this "
				"helper is reading the wrong file - either way every check calling "
				"it would now be reading a page with no styles and no script.")
		stranded = ess_assets_on_disk() - assets - preview_reach()[1]
		if stranded:
			raise PortalSourceError(
				"these frame asset files exist but the page never loads them, so "
				"their contents are checked by nobody: " + ", ".join(sorted(stranded)))
	if not used:
		raise PortalSourceError(
			"hrms-employee.html has no ess include tags. Either the page was "
			"flattened or this helper is reading the wrong file - either way "
			"every check calling it would now be checking a shell."
		)
	on_disk = {f for f in ess_files_on_disk() if "/parts/" not in f}
	orphans = on_disk - used - preview_reach()[0]
	if orphans:
		raise PortalSourceError(
			"these include files exist but nothing includes them, so their "
			"contents are checked by nobody: " + ", ".join(sorted(orphans))
		)


def read_page(path=PORTAL_PAGE, encoding="utf-8", errors="strict"):
	"""The expanded page as text, with universal newlines, like open() gives."""
	text = page_bytes(path).decode(encoding, errors)
	return text.replace("\r\n", "\n").replace("\r", "\n")
