"""Paste one piece of the employee portal's markup into the page.

Slice 034, OPS-31 follow-on. The page wants to be split into one file per area,
so that two sessions working on two different panels do not meet in one file.
A Jinja `{% include %}` cannot give that: Frappe compiles at most 32 templates
per worker (`frappe/utils/jinja.py`, `cache_size=32`) and this page's chain
already uses about 25 of them. Measured on a real server, splitting the markup
into twelve include files costs +33 %; the budget is 10 %.

A part is not a template. It holds no Jinja at all - that is checked here and
pinned by a test - so there is nothing to compile, nothing to cache and no cache
slot taken. It is read and pasted in, and the number of parts stops mattering.

The pieces that DO need Jinja - the tenant's name and brand mark - stay in an
ordinary include file. This helper is for the rest.

Rules it keeps, because a Jinja global is reachable from any template:

  * the name is matched against the files that exist, and may hold nothing but
    lower-case letters, digits and hyphens. No path, no traversal, no extension.
  * a part holding a Jinja tag is refused rather than rendered, so nobody can
    write `{{ ... }}` in one and quietly get a literal on the screen.
  * the answer is cached per site, keyed by the build version, so a release
    invalidates it and a worker does not read the files on every request.
"""

import os
import re

import frappe
from frappe.utils import get_build_version

PARTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "templates", "includes", "ess", "parts")

NAME_RE = re.compile(r"^[a-z0-9-]+$")
JINJA_TOKENS = ("{{", "{%", "{#")


class EssPartError(frappe.ValidationError):
	pass


def ess_part(name):
	"""Return one markup part, ready to paste into the page."""
	from markupsafe import Markup

	if not isinstance(name, str) or not NAME_RE.match(name):
		frappe.throw(frappe._("Unknown page part."), EssPartError)

	key = "ess_part:%s:%s" % (get_build_version(), name)
	body = frappe.cache().get_value(key)
	if body is None:
		body = _read(name)
		frappe.cache().set_value(key, body, expires_in_sec=24 * 60 * 60)
	return Markup(body)


def _read(name):
	path = os.path.join(PARTS_DIR, name + ".html")
	if not os.path.isfile(path):
		frappe.throw(frappe._("Unknown page part."), EssPartError)
	with open(path, encoding="utf-8") as fh:
		body = fh.read()
	for token in JINJA_TOKENS:
		if token in body:
			frappe.throw(
				frappe._("A page part may not contain template tags."), EssPartError)
	return body


def parts_on_disk():
	"""Every part that exists. Used by the tests and the shared expanders."""
	if not os.path.isdir(PARTS_DIR):
		return set()
	return {n[:-5] for n in os.listdir(PARTS_DIR) if n.endswith(".html")}
