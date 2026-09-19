"""The page behind HR's joining code: "open the app" (slice 013, US-20).

Public, like the field check-in page, because the person opening it has no
login. It reads NOTHING from the database about codes - the code is in the
URL fragment, which never reaches the server, and the page never looks at it
(SEC-2). Only the tenant's name and colour, from site config, go into it.
"""

import frappe

from alvoraa_portal.tenant_context import get_branding

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.no_header = 1
	context.no_sidebar = 1
	context.update(get_branding())
	# Search engines stay away, by header as well as by meta tag (AC-123).
	# `frappe.local.response_headers` is what Frappe copies onto every response
	# (frappe/app.py, `response.headers.update(frappe.local.response_headers)`).
	try:
		frappe.local.response_headers["X-Robots-Tag"] = "noindex, nofollow"
		frappe.local.response_headers["Cache-Control"] = "no-store"
	except Exception:
		pass
	return context
