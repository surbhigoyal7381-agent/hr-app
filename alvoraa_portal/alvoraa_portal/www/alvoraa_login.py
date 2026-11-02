import frappe

from alvoraa_portal.tenant_context import get_branding

no_cache = 1


def get_context(context):
    # Already logged in → send to the right portal immediately
    if frappe.session.user != "Guest":
        from alvoraa_portal.auth import JOINER_ROLE, JOINING_PAGE, _portal_home_for
        roles = set(frappe.get_roles(frappe.session.user))
        desk_roles = {"System Manager", "HR Manager", "HR User", "Administrator",
                      "Accounts Manager", "Accounts User"}
        if JOINER_ROLE in roles:
            # Slice 079. This door answered before `home_page_for` existed and
            # never learnt about it, so a signed-in joiner reloading the sign-in
            # page was sent to _portal_home_for() - the staff portal. The gate in
            # `auth.lock_to_the_joining_page` would turn that into a redirect
            # loop through a refusal screen; answering here is the honest fix.
            frappe.local.flags.redirect_location = JOINING_PAGE
        elif desk_roles.intersection(roles):
            frappe.local.flags.redirect_location = "/app"
        else:
            frappe.local.flags.redirect_location = _portal_home_for(frappe.session.user)
        raise frappe.Redirect

    context.no_cache   = 1
    context.no_header  = 1
    context.no_sidebar = 1
    # Branding server side, so brand_color.html paints the tenant's colour
    # before first paint. It used to arrive from get_tenant_config() after the
    # page had already drawn, so everybody saw a flash of the default purple
    # and then the real brand - on the sign-in page, which is the first thing
    # a customer's staff ever see.
    context.update(get_branding())
    # Set by JavaScript from the tenant config; a hardcoded brand here
    # flashed the wrong name before that ran.
    context.title      = "Sign In"
    _the_joiner_state(context)


def _the_joiner_state(context):
    """Slice 079, US-3. The same page, speaking to somebody who has never been
    here.

    **Not a second login page.** One page, one set of fields, one error pattern,
    one place to fix a bug. The state is chosen by a hint in the address HR
    sends - `?for=joining` - and with no hint the ordinary page appears and the
    same credentials still work, so nothing breaks if the hint is lost.

    Three things are read from the server rather than guessed, and all three were
    open questions in the design:

    * **The lockout numbers** (⚠ D4b, OQ-8). Frappe's own are 10 consecutive
      attempts and a 60-second lock - **not the "30 minutes" the design wrote**.
      The copy is generated from the settings, so the countdown says what will
      actually happen. Read, not guessed, because a joiner told the wrong number
      rings to say the system is broken.
    * **The employer's own phone number**, so "I cannot sign in" ends at a human
      rather than at a `mailto:` or at our helpdesk. *This does put a tenant's HR
      telephone number on a page a visitor can open, which is a small new
      disclosure, and it is in the implementation notes for the security
      reviewer.* The page already shows the tenant's name and logo.
    * **Whether sign-in by mobile number is on**, which decides whether the
      username label can honestly say "the phone number or email".
    """
    from frappe.utils import cint

    context.joiner = frappe.form_dict.get("for") == "joining"
    if not context.joiner:
        return
    settings = frappe.get_cached_doc("System Settings")
    context.lock_tries = cint(settings.allow_consecutive_login_attempts)
    context.lock_seconds = cint(settings.allow_login_after_fail)
    context.mobile_login = bool(cint(settings.allow_login_using_mobile_number))
    try:
        context.hr_phone = frappe.db.get_default("alvoraa_hr_contact_phone") or ""
        context.hr_email = frappe.db.get_default("alvoraa_hr_contact_email") or ""
    except Exception:
        context.hr_phone = context.hr_email = ""
