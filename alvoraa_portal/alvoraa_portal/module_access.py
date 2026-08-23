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

from alvoraa_portal.subscription import (
    blocked_module_defs,
    blocked_module_defs_for_hr,
    enabled_features,
)

PROFILE_NAME = "Alvoraa Plan"          # employees: the product, nothing else
HR_PROFILE_NAME = "Alvoraa Plan (HR)"  # HR staff: the same, plus the desk shell

# Anyone expected to WORK in the desk. They keep Core and Desk so /app/hr is
# usable, but still lose everything the plan does not include.
HR_ROLES = {"HR Manager", "HR User"}

# The tenant's own Administrator is left alone. If a profile is ever built wrong,
# support still needs a way in — locking every account out of the desk at once is
# not a failure mode worth risking for a cosmetic gate.
NEVER_TOUCH = {"Administrator", "Guest"}

# Tenant administrators keep the full module list. They are the people who set up
# integrations, email accounts and print formats, and those live in the very
# framework modules this profile hides from everyone else.
#
# Note what this means: a tenant admin still sees Payroll in the desk even on a
# plan without it. Hiding was never the boundary - roles are (wave 4) - so the
# trade is deliberate: usability for admins, and the real gate elsewhere.
ADMIN_ROLES = {"System Manager"}


def _is_tenant_admin(user):
    return bool(ADMIN_ROLES & set(frappe.get_roles(user)))


def _is_hr(user):
    return bool(HR_ROLES & set(frappe.get_roles(user)))


def _profile_for(user):
    """Which profile a user should carry, or None if they are exempt."""
    if user in NEVER_TOUCH or _is_tenant_admin(user):
        return None
    return HR_PROFILE_NAME if _is_hr(user) else PROFILE_NAME


def sync_module_profile(features=None, name=PROFILE_NAME, blocked=None):
    """Create or update one Module Profile. Returns its name."""
    features = features if features is not None else enabled_features()
    if blocked is None:
        blocked = blocked_module_defs(features)

    # Only block modules that actually exist here. A site without alvoraa_goals
    # installed has no such Module Def, and Frappe rejects the link.
    existing = {m.name for m in frappe.get_all("Module Def", fields=["name"])}
    blocked = [m for m in blocked if m in existing]

    if frappe.db.exists("Module Profile", name):
        doc = frappe.get_doc("Module Profile", name)
        doc.set("block_modules", [])
    else:
        doc = frappe.get_doc({
            "doctype": "Module Profile",
            "module_profile_name": name,
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

    changed = skipped = 0
    for name in users:
        if name in NEVER_TOUCH:
            continue
        want = _profile_for(name)
        if want is None:
            # Tenant admin: keep the full module list, and clear any profile
            # applied before they became one, or an old block list lingers.
            if frappe.db.get_value("User", name, "module_profile"):
                u = frappe.get_doc("User", name)
                u.module_profile = None
                u.set("block_modules", [])
                u.flags.ignore_permissions = True
                u.save(ignore_permissions=True)
            skipped += 1
            continue
        try:
            user = frappe.get_doc("User", name)
            # Always save, even if the profile name is unchanged: its CONTENTS
            # may have changed, and Frappe only copies them on save.
            user.module_profile = want
            user.flags.ignore_permissions = True
            user.save(ignore_permissions=True)
            changed += 1
        except Exception:
            frappe.log_error(
                title="module_access: could not apply profile",
                message=frappe.get_traceback(),
            )
    frappe.db.commit()
    return {"applied": changed, "admins_exempt": skipped}


def sync_site(features=None):
    """Build the profile from this site's config and apply it to every user.

    Refuses to run on the control plane. That site is not a tenant - it is where
    tenants are provisioned from, and its administrators need the full module
    list to do that. Applying a tenant plan there would hide the tooling they
    work with.
    """
    if frappe.conf.get("alvoraa_control_plane"):
        msg = "Refusing to run on the control plane - it is not a tenant."
        print(msg)
        return {"skipped": True, "reason": msg}

    feats = features if features is not None else enabled_features()

    # Two profiles: employees lose the desk shell, HR staff keep it so /app/hr
    # is usable. Both lose everything the plan does not include.
    sync_module_profile(feats, PROFILE_NAME)
    sync_module_profile(feats, HR_PROFILE_NAME, blocked_module_defs_for_hr(feats))

    res = apply_to_users()
    counts = {
        n: frappe.db.count("Block Module", {"parent": n, "parenttype": "Module Profile"})
        for n in (PROFILE_NAME, HR_PROFILE_NAME)
    }
    msg = (f"employees: {counts[PROFILE_NAME]} hidden | HR: {counts[HR_PROFILE_NAME]} hidden "
           f"| applied to {res['applied']} users, {res['admins_exempt']} admins exempt")
    print(msg)          # bench execute prints this back to the operator
    return {"blocked": counts, **res}


@frappe.whitelist()
def get_hidden_modules():
    """What this site currently hides. For the admin console and for support."""
    out = {}
    for name in (PROFILE_NAME, HR_PROFILE_NAME):
        if frappe.db.exists("Module Profile", name):
            doc = frappe.get_doc("Module Profile", name)
            out[name] = sorted(d.module for d in doc.block_modules)
        else:
            out[name] = None
    return {"profiles": out, "blocked": out.get(PROFILE_NAME) or []}


def apply_on_user_insert(doc, method=None):
    """Give a NEW user the site's Module Profile.

    Without this, module hiding would apply only to whoever existed when the
    plan was last synced. Every employee added afterwards - which is most of
    them, over a tenant's life - would see the full module list. The gate would
    quietly decay from the day it was switched on.

    Tenant admins are left alone, as everywhere else.
    """
    if doc.name in NEVER_TOUCH:
        return
    want = _profile_for(doc.name)
    if not want or not frappe.db.exists("Module Profile", want):
        return
    # Set it directly: this runs inside the user's own insert, so saving the
    # document again here would recurse.
    frappe.db.set_value("User", doc.name, "module_profile", want,
                        update_modified=False)
    for m in frappe.get_all("Block Module",
                            filters={"parent": want, "parenttype": "Module Profile"},
                            fields=["module"]):
        frappe.get_doc({
            "doctype": "Block Module", "parent": doc.name, "parenttype": "User",
            "parentfield": "block_modules", "module": m.module,
        }).db_insert()


def apply_on_role_change(doc, method=None):
    """Re-evaluate a user when their roles change.

    Promoting someone to System Manager should give them the full module list;
    demoting them should take it away again. Without this, the exemption is
    decided once and never revisited.
    """
    user = getattr(doc, "parent", None)
    if not user or user in NEVER_TOUCH:
        return
    if not frappe.db.exists("Module Profile", PROFILE_NAME):
        return
    try:
        # Roles decide which profile applies, so a change here can move someone
        # between employee, HR and exempt.
        apply_to_users([user])
    except Exception:
        frappe.log_error(title="module_access: role change re-apply failed",
                         message=frappe.get_traceback())
