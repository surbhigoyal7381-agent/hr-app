"""The joiner's page: public, hardened, and it never reads the token.

Slice 078, step 6, 078-SEC-15. Copied from `www/enrol.py`, which already got
all of this right for the field app's joining code - deliberately, rather than
reinvented.

Public, because the person opening it **has no login**: that is the whole point
of the feature. Which makes it the most attacked surface this product has, so
it is built to give an attacker nothing:

* **It reads NOTHING about any invite.** The token is in the URL fragment,
  which a browser never sends to a server, and this page never looks at it. The
  page's own JavaScript posts it in a request body to the endpoints in
  `joiner_public.py`, which is where the token check provably runs.
* **Only the tenant's name and colour** go into the HTML, both of which are
  already public on its login page. No employee name, no count, no email
  address, nothing else about the tenant.
* `no_cache`, `no_header`, `no_sidebar`, `X-Robots-Tag: noindex, nofollow` as a
  header **and** a meta tag, `Cache-Control: no-store`, `referrer:
  no-referrer`.
* **No external host for any asset.** Its CSS and JavaScript are inline, which
  is OPS-44's requirement and not a style choice: `check_portal_assets_gate.py`
  reads only `hrms-employee.html`, so a 404 on a file this page needed would
  give a dead form with nothing in any log - on the one page used by people who
  cannot ring our helpdesk.
* It falls through to nginx's `location /`, which deliberately does **not**
  gzip HTML. That is the BREACH rule and it is right for a page carrying a
  token, so the page must stay out of the compressed-HTML list.
"""

import frappe

from alvoraa_portal.tenant_context import get_branding

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.no_header = 1
	context.no_sidebar = 1
	context.update(get_branding())
	# Slice 078: whether the feature is on at all. Used only to draw the "this
	# link has run out" screen without a round trip - the ENDPOINTS refuse
	# regardless, and they give the same answer whether the feature is off or
	# the token is wrong, so this leaks nothing a stranger could use.
	try:
		from alvoraa_portal.joiner_invite import form_is_on

		context.joiner_on = 1 if form_is_on() else 0
	except Exception:
		context.joiner_on = 0
	try:
		frappe.local.response_headers["X-Robots-Tag"] = "noindex, nofollow"
		frappe.local.response_headers["Cache-Control"] = "no-store"
		frappe.local.response_headers["Referrer-Policy"] = "no-referrer"
	except Exception:
		pass
	return context
