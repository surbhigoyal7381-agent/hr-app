"""Where the Alvoraa brand images live, and the one rule for using them.

THE BUG THIS EXISTS TO CLOSE
----------------------------
A tenant's logo had been uploaded as a PRIVATE file, and Website Settings pointed
at it:

    banner_image = /private/files/381140.jpg
    favicon      = /private/files/381140.jpg

A browser fetching `/private/files/...` does not carry Frappe's file permission
check the way an API call does, so it comes back refused and the page draws the
broken-image icon. The logo was never missing. It was unreadable.

Two more faults sat behind it. No Alvoraa image shipped in any app at all, so
there was nothing to fall back to. And the portal's own brand tile painted its
letter in `var(--surface)` on a `var(--surface)` background - the same token - so
the fallback everybody assumed was there had been an empty square the whole time.

THE FIX IS AN APP ASSET, NOT A SITE FILE
----------------------------------------
These three images ship inside this app, under `public/images/`, and Frappe serves
that directory at `/assets/alvoraa_portal/images/`. In production and on dev, nginx
serves it straight off disk with `expires 30d; Cache-Control: public, immutable`
(deploy/nginx.conf). That means:

  * no upload, on any tenant, ever
  * no `docker cp`, no file to copy when a tenant is created
  * no permission check to fail, because an app asset is public by design
  * one file to replace when the artwork changes - see scripts/make_brand_assets.py

A NEW FILE NEEDS A BUILD, AND THAT IS ALREADY HANDLED
-----------------------------------------------------
`sites/assets/<app>` is not a live view of the app directory. `bench build` links
it, and deploy/Dockerfile then runs scripts/materialise_assets.sh to turn the link
into real files, because the nginx container has no /apps to follow a link into.
So on dev and production a new image arrives with the new container image and
needs nothing else - `migrate` has no part in it. On a local bench, whose
sites volume holds a baked copy, `bench build --app alvoraa_portal` is needed once.

THE RULE, ONE SENTENCE
----------------------
A tenant's own logo if it has one, otherwise the Alvoraa mark, and never a broken
image.

The tenant's own logo already has a home: `site_config.json` -> `tenant_logo_url`,
written at provisioning by tenant_api.py and read by tenant_context.get_branding().
Nothing here overrides it. `apply_site_branding()` below only fills a slot that is
empty or unreadable, and the table in `_verdict()` is where that judgement lives.
"""

import frappe

# ── The assets. These names are the contract; make_brand_assets.py keeps them ──
ASSET_DIR = "/assets/alvoraa_portal/images/"

MARK = ASSET_DIR + "alvoraa-mark.png"        # the monogram, 128px, transparent
LOGO = ASSET_DIR + "alvoraa-logo.png"        # the full lockup, 320px, transparent
FAVICON = ASSET_DIR + "alvoraa-favicon.png"  # 32px, on white


# ── Which stored values we are willing to write, and with what ───────────────
#
# Navbar Settings.app_logo rather than the `app_logo_url` hook, and this is not a
# style preference. Frappe resolves that hook like this
# (frappe/core/doctype/navbar_settings/navbar_settings.py):
#
#     logos = frappe.get_hooks("app_logo_url")
#     app_logo = logos[0]
#     if len(logos) == 2:
#         app_logo = logos[1]
#
# frappe, erpnext and hrms all declare it already, so len(logos) is 3 and the
# winner is logos[0] - the Frappe FRAMEWORK logo. A fourth declaration changes
# nothing. That is why a tenant nobody configured by hand shows a Frappe logo in
# the desk today. The only mechanisms that actually decide it are the two stored
# values, and get_app_logo() prefers them in this order:
#
#     Website Settings.app_logo -> Navbar Settings.app_logo -> hooks
#
# We write the second, the lowest rung, so a tenant can still override us from
# either the Website Settings form or the Navbar Settings form.
#
# WHY banner_image AND splash_image POINT AT THE MARK, NOT THE LOCKUP
#
# They should use LOGO - they are the two places with room to read a wordmark.
# They use MARK for now because the master artwork is a PLACEHOLDER whose
# wordmark reads ALVORAA, and the chosen spelling is ALVORA. The monogram has no
# lettering in it, so it is correct either way; the lockup is visibly wrong.
#
# Showing a customer the wrong spelling of our own name is worse than showing
# them nothing, so nothing that carries type is displayed until the real artwork
# lands. `alvoraa-logo.png` is built and ready, and this is the one-line change:
# put LOGO back in these two rows. Nothing else moves.
SLOTS = (
    # (doctype, fieldname, what we put there if the slot is free)
    ("Website Settings", "favicon", FAVICON),
    ("Website Settings", "app_logo", MARK),
    ("Website Settings", "banner_image", MARK),   # LOGO once the wordmark is right
    ("Website Settings", "splash_image", MARK),   # LOGO once the wordmark is right
    ("Navbar Settings", "app_logo", MARK),
)

PRIVATE_PREFIX = "/private/files/"


def _verdict(value):
    """Should we write this slot? Returns "empty", "broken", "ours" or None.

    None means LEAVE IT ALONE. That is the important branch: a customer who
    uploaded their own public logo keeps it, and so does one who pointed the
    field at a URL of their own.

        empty   nobody ever chose anything          -> write ours
        broken  a /private/files/ path              -> write ours; a browser can
                                                       never render this one
        ours    already one of our asset paths      -> rewrite, so a renamed
                                                       asset is picked up
        None    anything else - /files/..., http:// -> a deliberate choice
    """
    if not value or not str(value).strip() or value == "attach_files:":
        return "empty"
    value = str(value).strip()
    if value.startswith(PRIVATE_PREFIX):
        return "broken"
    if value.startswith(ASSET_DIR):
        return "ours"
    return None


def apply_site_branding():
    """Point this site's brand slots at the Alvoraa assets, where they are free.

    Safe to run twice: the second run finds every slot already "ours" and writes
    the same values back. Returns a summary for the caller to print or log.

    Called from `after_install` - so every new tenant and every CI site gets it
    with no manual step - and from the patch that repairs sites already live.
    Deliberately NOT in `after_migrate`: baseline.py sets out why. A decision a
    tenant starts with is applied once, or it stops being a default and becomes
    a setting they cannot keep.
    """
    changed = {}
    left_alone = {}

    for doctype, field, want in SLOTS:
        if not frappe.db.exists("DocType", doctype):
            continue
        # cache=False on purpose. get_single_value memoises per request, and the
        # patch runs after a migrate that has already read these; a stale read
        # here would be the difference between repairing a tenant and not.
        current = frappe.db.get_single_value(doctype, field, cache=False)
        verdict = _verdict(current)
        key = f"{doctype}.{field}"
        if verdict is None:
            left_alone[key] = "set by the tenant"
            continue
        if verdict == "ours" and current == want:
            continue
        frappe.db.set_single_value(doctype, field, want)
        changed[key] = verdict

    if changed:
        # Website Settings is cached, and Guest holds its own copy. Without this
        # the old favicon keeps being served until something else clears it.
        # This is what Frappe's own WebsiteSettings.on_update does.
        from frappe.website.utils import clear_website_cache

        frappe.clear_cache()
        clear_website_cache()

    # Names of fields and the reason, never a file name or any personal data.
    frappe.logger("alvoraa.brand").info(
        {
            "operation": "apply_site_branding",
            "site": frappe.local.site,
            "changed": changed,
            "left_alone": left_alone,
        }
    )
    return {"changed": changed, "left_alone": left_alone}


def after_install():
    """Hook entry point. Never fails an install over a logo."""
    try:
        result = apply_site_branding()
        print(f"brand: {len(result['changed'])} slot(s) set, "
              f"{len(result['left_alone'])} left to the tenant")
    except Exception:
        # A tenant that exists with the wrong logo beats a tenant that failed to
        # install. Same reasoning as tenant_api.py's [WARN] on the baseline step.
        frappe.log_error(title="brand: could not set site branding",
                         message=frappe.get_traceback())
