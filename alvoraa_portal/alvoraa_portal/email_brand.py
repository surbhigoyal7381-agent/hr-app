"""ALV-174: Frappe/ERPNext branding removed from outgoing email.

Two things a recipient sees, from two different Frappe mechanisms:

    THE FOOTER LINE ("Sent via ERPNext")
    ERPNext declares a hook, `default_mail_footer` (erpnext/hooks.py), and
    Frappe's own footer template prints every app's value for that hook on
    EVERY outgoing email (frappe/email/email_body.py:get_footer,
    templates/emails/email_footer.html), unless
    `System Settings.disable_standard_email_footer` is on. That switch is the
    only way to remove ERPNext's line - `frappe.get_hooks()` APPENDS every
    installed app's value into one list (frappe/__init__.py:append_hook), so
    an `alvoraa_portal` hook of the same name would not replace ERPNext's, it
    would print BOTH. `System Settings.email_footer_address` is a separate,
    independent field - it renders in its own <div> regardless of the switch
    above - so that is where OUR line goes.

    THE HEADER LOGO
    `get_brand_logo()` (frappe/email/email_body.py:707) prefers the sending
    Email Account's own `brand_logo` field over `Website Settings.app_logo`.
    We use the Email Account field on purpose and leave `Website
    Settings.app_logo` exactly as `brand.py` (ALV-149) already set it: the
    desk navbar reads that SAME field (frappe/core/doctype/navbar_settings/
    navbar_settings.py:get_app_logo()), already holds the small Alvora mark,
    and a 320px lockup there would resize the desk navbar's logo along with
    the email header. Per Email Account keeps the two independent.
    `brand_logo` must be an ABSOLUTE url - a relative one resolves fine on
    a page in a browser but has no base to resolve against in a mail client,
    so it fails to load there. `frappe.utils.get_url()` gives each tenant's
    own domain, so the logo in an email is served from the tenant's own site.

Applied per site - the control plane included, same as brand.py and
brand_text.py - from `after_install` (new tenant) and a patch (existing one).
Safe to run twice. Never fails an install or a migrate over a footer.

Surbhi's decisions, 28 Sep 2026 (ALV-174): footer = the tenant's own name
(from `tenant_context.get_branding()`, already how the portal names a tenant
everywhere else) plus "Powered by AllAboutHR" on its own line; header logo =
the full ALVORA lockup (`brand.LOGO`), not the small mark.

WHAT THIS DOES NOT DO
----------------------
It does not change which Email Account sends, or add a Reply-To. The control
plane's own outgoing account is Brevo-backed (see the "Email sending via
Brevo" note) and its SMTP/sending configuration is untouched here - only the
two email-only fields above. A Reply-To of support@alvoraa.co on the control
plane's sending account is a real option (`add_reply_to_header` +
`reply_to_addresses` on Email Account) but it is a live mail-config change,
not a footer or a logo, so it is proposed in the implementation notes for
Surbhi to apply by hand rather than written by this patch.
"""

import frappe

from alvoraa_portal import brand, tenant_context

FOOTER_LINE = "Powered by AllAboutHR"


def _footer_text():
	tenant_name = tenant_context.get_branding()["tenant_name"]
	return f"{tenant_name}\n{FOOTER_LINE}"


def _footer_is_ours(value):
	"""Empty, or a footer this module wrote before (whatever the tenant name
	was at the time - a rename should not turn "leave alone" against us)."""
	if not value or not str(value).strip():
		return True
	lines = str(value).splitlines()
	return bool(lines) and lines[-1].strip() == FOOTER_LINE


def _logo_url():
	return frappe.utils.get_url() + brand.LOGO


def _logo_is_ours(value):
	"""Empty, or one of our own asset paths (any host - a rename or a domain
	change should still count as "ours" so a re-run picks it up)."""
	if not value or not str(value).strip():
		return True
	value = str(value).strip()
	return value.endswith(brand.MARK) or value.endswith(brand.LOGO)


def plan():
	"""What email_brand would change on this site. Reads only.

	Rows of {"setting", "current", "proposed", "action"}; action is "change"
	or "leave".
	"""
	rows = []

	disable = frappe.db.get_single_value(
		"System Settings", "disable_standard_email_footer", cache=False)
	if not frappe.utils.cint(disable):
		rows.append({"setting": "System Settings.disable_standard_email_footer",
		             "current": "0", "proposed": "1", "action": "change"})

	footer = frappe.db.get_single_value(
		"System Settings", "email_footer_address", cache=False) or ""
	wanted_footer = _footer_text()
	if footer != wanted_footer:
		if _footer_is_ours(footer):
			rows.append({"setting": "System Settings.email_footer_address",
			             "current": footer or "(not set)", "proposed": wanted_footer,
			             "action": "change"})
		else:
			rows.append({"setting": "System Settings.email_footer_address",
			             "current": footer, "proposed": footer, "action": "leave"})

	wanted_logo = _logo_url()
	for acc in frappe.get_all("Email Account", filters={"enable_outgoing": 1},
	                          fields=["name", "brand_logo"], order_by="name"):
		current = acc.brand_logo or ""
		key = f"Email Account.brand_logo ({acc.name})"
		if current == wanted_logo:
			continue
		if _logo_is_ours(current):
			rows.append({"setting": key, "current": current or "(not set)",
			             "proposed": wanted_logo, "action": "change"})
		else:
			rows.append({"setting": key, "current": current, "proposed": current,
			             "action": "leave"})

	return rows


def apply():
	"""Make the changes plan() lists. Safe to run twice. Never raises.

	Returns {"changed": [...], "left_alone": [...], "failed": [...]} - setting
	names and the old/new values only, never personal data.
	"""
	result = {"changed": [], "left_alone": [], "failed": []}
	for row in plan():
		if row["action"] == "leave":
			result["left_alone"].append(row["setting"])
			continue
		try:
			_change(row)
			result["changed"].append(f'{row["setting"]}: {row["current"]!r} -> {row["proposed"]!r}')
		except Exception:
			frappe.log_error(title="email_brand: could not change a setting",
			                 message=f'{row["setting"]}\n{frappe.get_traceback()}')
			result["failed"].append(row["setting"])

	if result["changed"]:
		frappe.clear_cache()

	frappe.logger("alvoraa.brand").info(
		{"operation": "email_brand.apply", "site": frappe.local.site, **result})
	return result


def _save_system_setting(fieldname, value):
	"""frappe.db.set_single_value writes tabSingles only. get_footer() reads
	these two fields through frappe.db.get_default() instead
	(frappe/email/email_body.py:get_footer) - a SEPARATE table (tabDefaultValue)
	that only System Settings' own `on_update` -> `set_defaults()` keeps in
	sync: one `frappe.db.set_default()` call per changed field. A raw
	`db.set_single_value` skips that step: the value looks changed everywhere
	the settings FORM reads it, and the ERPNext footer keeps showing anyway,
	because get_footer() never sees the change. Found by actually rendering
	the footer, not by reading the Python -
	see test_alv174_the_footer_never_says_sent_via_erpnext.

	Not `frappe.get_single("System Settings").save()` either: that runs the
	WHOLE document's validation, including mandatory fields (`language`,
	`time_zone`) this module never touches - and `after_install` runs BEFORE
	the setup wizard has ever run, when a brand new tenant's System Settings
	has neither set yet (confirmed by actually running this against a fresh
	site: MandatoryError, not a guess). `brand_text.py`'s own fields
	(`Website Settings`/`System Settings.app_name`) don't need this - Frappe
	reads those back through `get_system_settings()`/`get_website_settings()`,
	which go straight to the cached document, not through `get_default()` -
	but `email_footer_address` and `disable_standard_email_footer` specifically
	do, so only these two need the second write. Write both tables directly
	for the ONE field being changed, exactly what `set_defaults()` does per
	field, without the rest of the document's validation along for the ride."""
	frappe.db.set_single_value("System Settings", fieldname, value)
	frappe.db.set_default(fieldname, value)


def _change(row):
	setting = row["setting"]
	if setting == "System Settings.disable_standard_email_footer":
		_save_system_setting("disable_standard_email_footer", 1)
	elif setting == "System Settings.email_footer_address":
		_save_system_setting("email_footer_address", row["proposed"])
	elif setting.startswith("Email Account.brand_logo ("):
		name = setting[len("Email Account.brand_logo ("):-1]
		frappe.db.set_value("Email Account", name, "brand_logo", row["proposed"],
		                    update_modified=False)
	else:
		raise ValueError(f"email_brand: unknown setting {setting!r}")


def report():
	"""Print plan() for `bench --site <site> execute alvoraa_portal.email_brand.report`."""
	rows = plan()
	print(f"site: {frappe.local.site}")
	if not rows:
		print("  nothing to change")
		return
	for row in rows:
		print(f'  {row["action"]}: {row["setting"]}: {row["current"]!r} -> {row["proposed"]!r}')


def after_install():
	"""Hook entry point. Never fails an install over a footer or a logo."""
	try:
		result = apply()
		print(f"email_brand: {len(result['changed'])} setting(s) changed, "
		      f"{len(result['left_alone'])} left to the tenant")
	except Exception:
		frappe.log_error(title="email_brand: could not set site branding",
		                 message=frappe.get_traceback())
