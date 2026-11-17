"""The joiner's page: behind their own sign-in, and it still reads no row.

Slice 079, 079-SEC-3. It was `www/joiner.py` and `/joiner` until this slice;
the address is `/joining` now, which is what the design draws and what HR's
message prints. The rename was free exactly once - the feature ships off at
every tenant, so no link anywhere points at the old address - and it will never
be free again.

**What changed, and what deliberately did not.**

* **A session is required.** Guest gets our own sign-in page in its joiner
  state, the way `hrms_employee.py` already redirects. The token is gone, and
  with it the URL fragment, the `replaceState` dance and the clear-text key.
* **It still reads nothing about any invite.** Every fact on the screen comes
  from `joiner_public.open_invite`, which is where the session check provably
  runs. This page knows the tenant's name and colour, both of which are already
  public on its login page, and nothing else.
* **Every 078-SEC-15 header stays.** It carries one person's identity documents,
  so it must not be cached, indexed or referred from: `no-store`,
  `noindex, nofollow` as a header **and** a meta tag, `no-referrer`, and
  inline-only assets.
* **Those headers are no longer set inside a silent `except Exception: pass`** -
  finding F5 of the 078 review, and it matters more now that the page is
  authenticated. The one case where the headers genuinely cannot be set is a
  render with no HTTP request behind it (a unit test, or a Jinja render from the
  console), and that case is named rather than swallowed. Any other failure
  escapes, which is the point.
* **No external host for any asset.** Its CSS and JavaScript are inline, which
  is OPS-44's requirement and not a style choice: `check_portal_assets_gate.py`
  reads only `hrms-employee.html`, so a 404 on a file this page needed would
  give a dead form with nothing in any log - on the one page used by people who
  cannot ring our helpdesk.
* It falls through to nginx's `location /`, which deliberately does **not** gzip
  HTML. That was the BREACH rule for a page carrying a token; it is still right
  for a page carrying a session and personal data, so the page stays out of the
  compressed-HTML list.
"""

import frappe
from frappe.sessions import get_csrf_token

from alvoraa_portal.tenant_context import get_branding

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		# The sign-in page in its joiner state. `for=joining` only chooses the
		# wording - the same credentials work on the ordinary page, so nothing
		# breaks if the hint is lost.
		frappe.local.flags.redirect_location = "/alvoraa-login?for=joining"
		raise frappe.Redirect

	# ALV-343. **Without this the page has no CSRF protection at all**, and
	# putting a token in the markup only made it LOOK protected.
	#
	# `validate_csrf_token` (`frappe/auth.py:87`) reads
	# `or not (saved_token := frappe.session.data.csrf_token)` and **returns
	# early when the session has no token** - the POST is then accepted whatever
	# header it carries. A token is only ever minted by `get_csrf_token()`, and
	# a joiner is pinned to this one page by `auth.lock_to_the_joining_page`, so
	# nothing else was ever going to mint one for them.
	#
	# That also explains who saw "Invalid Request": only somebody whose session
	# ALREADY had a token - HR or an admin opening the link from a Desk or ESS
	# session. A plain joiner was never refused, because the check never ran.
	#
	# `hrms_employee.py:21`, `hrms_employee_next.py:72` and `event_form.py:39`
	# all do exactly this, for exactly this reason. An existing token is reused,
	# never replaced, so other open tabs keep working.
	get_csrf_token()

	context.no_cache = 1
	context.no_header = 1
	context.no_sidebar = 1
	context.update(get_branding())
	# Set by `auth._GoToTheJoiningPage` when a joiner asked for an address that
	# is not theirs. The page then draws the refusal the design asks for -
	# "This sign-in only opens your joining form", one button that works, code
	# JOIN-ONEPAGE - rather than silently showing the form as though nothing had
	# happened. It names no page, no menu and no count.
	context.one_page = bool(frappe.form_dict.get("one-page")
	                        or frappe.form_dict.get("one_page"))
	_harden()
	return context


def _harden():
	headers = getattr(frappe.local, "response_headers", None)
	if headers is None:
		# No HTTP request behind this render at all - a unit test, or a Jinja
		# render from the console. There is nothing to harden and nothing has
		# gone wrong. Every OTHER failure now escapes, which is the whole reason
		# this is not a bare `except Exception: pass` any more (078 review, F5).
		return
	headers["X-Robots-Tag"] = "noindex, nofollow"
	headers["Cache-Control"] = "no-store"
	headers["Referrer-Policy"] = "no-referrer"
