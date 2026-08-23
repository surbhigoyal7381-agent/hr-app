"""Wave 2 — hide the modules a tenant did not buy.

Runs ON a tenant site, not on the control plane:

    bench --site acme.alvoraa.co execute alvoraa_portal.module_access.sync_site

It builds one Module Profile from that site's own selection and points every user
at it. Frappe copies the profile's blocked modules into `User.block_modules` in
`validate_allowed_modules()` — but only when the user is SAVED, so a plan change
means re-saving the affected users. `apply_to_users()` does that.

WHAT THIS DOES NOT DO, and it matters:

    This HIDES modules from the desk. It does not DENY anything. A hidden
    Payroll module still answers /api/resource/Salary Slip if the user's role
    permits it. Roles are the boundary — that is wave 4.

Shipping this alone would make the product look correctly gated while it is not.
"""

import frappe

from alvoraa_portal.subscription import blocked_module_defs, enabled_features

PROFILE_NAME = "Alvoraa Plan"

# The tenant's own Administrator is left alone. If a profile is ever built wrong,
# support still needs a way in — locking every account out of the desk at once is
# not a failure mode worth risking for a cosmetic gate.
NEVER_TOUCH = {"Administrator", "Guest"}


def sync_module_profile(features=None):
    """Create or update this site's Module Profile. Returns its name."""
    features = features if features is not None else enabled_features()
    blocked = blocked_module_defs(features)

    # Only block modules that actually exist here. A site without alvoraa_goals
    # installed has no such Module Def, and Frappe rejects the link.
    existing = {m.name for m in frappe.get_all("Module Def", fields=["name"])}
    blocked = [m for m in blocked if m in existing]

    if frappe.db.exists("Module Profile", PROFILE_NAME):
        doc = frappe.get_doc("Module Profile", PROFILE_NAME)
        doc.set("block_modules", [])
    else:
        doc = frappe.get_doc({
            "doctype": "Module Profile",
            "module_profile_name": PROFILE_NAME,
        })

    for m in blocked:
        doc.append("block_modules", {"module": m})

    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True) if not doc.is_new() else doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.name


def apply_to_users(users=None):
    """Point users at the profile and save, so Frappe copies the blocks across.

    Saving is the point: Frappe only copies `block_modules` during validate, so a
    profile that changed after a user was last saved has no effect on them until
    they are saved again.
    """
    if users is None:
        users = [
            u.name
            for u in frappe.get_all("User", filters={"enabled": 1}, fields=["name"])
            if u.name not in NEVER_TOUCH
        ]

    changed = 0
    for name in users:
        if name in NEVER_TOUCH:
            continue
        try:
            user = frappe.get_doc("User", name)
            if user.module_profile == PROFILE_NAME:
                # Re-save anyway: the profile's contents may have changed.
                pass
            user.module_profile = PROFILE_NAME
            user.flags.ignore_permissions = True
            user.save(ignore_permissions=True)
            changed += 1
        except Exception:
            frappe.log_error(
                title="module_access: could not apply profile",
                message=frappe.get_traceback(),
            )
    frappe.db.commit()
    return changed


def sync_site(features=None):
    """Build the profile from this site's config and apply it to every user."""
    profile = sync_module_profile(features)
    count = apply_to_users()
    blocked = frappe.db.count("Block Module", {"parent": profile, "parenttype": "Module Profile"})
    msg = f"{profile}: {blocked} modules hidden, applied to {count} users"
    print(msg)          # bench execute prints this back to the operator
    return {"profile": profile, "blocked": blocked, "users": count}


@frappe.whitelist()
def get_hidden_modules():
    """What this site currently hides. For the admin console and for support."""
    if not frappe.db.exists("Module Profile", PROFILE_NAME):
        return {"profile": None, "blocked": []}
    doc = frappe.get_doc("Module Profile", PROFILE_NAME)
    return {"profile": PROFILE_NAME, "blocked": sorted(d.module for d in doc.block_modules)}
