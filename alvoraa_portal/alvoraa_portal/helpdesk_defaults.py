"""Safe privacy defaults for Frappe Helpdesk, applied once per site (slice 166/167).

Checked against the app's own source at the pinned tag (v1.30.1, cloned and
read directly, not recalled) before writing this:

  - `HD Settings.allow_anyone_to_create_tickets` is the ONE switch that opens
    the customer portal to unauthenticated ticket creation. Its controller
    (`hd_settings.py` `on_update`) calls `set_guest_ticket_creation_permission`/
    `remove_guest_ticket_creation_permission` (`hd_ticket.py`), which is what
    actually grants or removes the Guest role's read/write/create permission
    on HD Ticket - HD Ticket carries NO Guest row in its own DocType JSON, so
    a site where this has never been turned on has no guest access to tickets
    at all. Default is already "0" (off) - this file writes it explicitly
    anyway, the same reasoning as LMS's `disable_signup`: a future change to
    the app's own default must not silently reopen it here without this
    file's own test noticing.
  - No separate self-sign-up flag exists in this app - it has none of its own;
    a site's normal `Website Settings.disable_signup` governs Frappe's own
    account sign-up the same way it always has, unrelated to Helpdesk.
  - `HD Article Category.allow_guest_to_view` is a DocType-level default (baked
    into the schema, not a per-tenant Settings field), making the knowledge
    base public by design - the product's own intended behaviour for
    documentation articles, not a Settings switch we can or should flip here.
    Left alone. If a tenant ever puts non-public content in an HD Article,
    that is a decision for the business analyst to scope, not a default to
    silently override in code.

Applied ONCE per site, the same way and for the same reason as
alvoraa_portal.lms_defaults - see that module's docstring for the full
"never flips a value back" rule. Called by provision_tenant.sh right after
`bench install-app helpdesk`, and by tenant_api._run_install_modules the same
way for an existing tenant that ticks the feature later.
"""

import frappe

SENTINEL = "alvoraa_helpdesk_privacy_applied"

SAFE_VALUES = {
	"allow_anyone_to_create_tickets": 0,
}


def apply_safe_defaults():
	"""Idempotent. A no-op unless Helpdesk is installed on this site and the
	one-time write has never run here. Safe to call by hand."""
	if not frappe.db.exists("DocType", "HD Settings"):
		return  # helpdesk is not installed on this site
	if frappe.db.get_default(SENTINEL):
		return  # already applied once - never touched again, on purpose

	doc = frappe.get_single("HD Settings")
	for field, value in SAFE_VALUES.items():
		doc.set(field, value)
	doc.save(ignore_permissions=True)

	frappe.db.set_default(SENTINEL, "1")
	frappe.db.commit()


def after_migrate():
	"""Runs on every `bench migrate`, on every site. See module docstring for
	why this is safe to run repeatedly and forever."""
	apply_safe_defaults()
