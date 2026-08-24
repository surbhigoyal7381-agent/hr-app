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
    blocked_doctypes,
    blocked_module_defs,
    blocked_module_defs_for_hr,
    enabled_features,
    sold_and_unsold_workspaces,
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

    # Workspaces, which module blocking cannot reach. Frappe HR keeps Leaves,
    # Expenses, Recruitment, Tenure and the rest inside one `HR` module, so a
    # tenant on Starter was still shown Recruitment and Payroll in the desk
    # sidebar even with module blocking applied.
    try:
        sync_workspaces(feats)
    except Exception:
        frappe.log_error(title="module_access: workspace sync failed",
                         message=frappe.get_traceback())

    # And the desk sidebar, which neither of the above reaches.
    try:
        sync_module_sidebars(feats)
    except Exception:
        frappe.log_error(title="module_access: module sidebar sync failed",
                         message=frappe.get_traceback())

    # Wave 4. The only one of these that actually DENIES anything; everything
    # above it just stops drawing menus.
    try:
        perms = sync_permissions(feats)
    except Exception:
        perms = {"error": True}
        frappe.log_error(title="module_access: permission sync failed",
                         message=frappe.get_traceback())

    # The desk's own menu gets a way back to the portal.
    try:
        sync_navbar_item()
    except Exception:
        frappe.log_error(title="module_access: navbar item failed",
                         message=frappe.get_traceback())

    res = apply_to_users()
    counts = {
        n: frappe.db.count("Block Module", {"parent": n, "parenttype": "Module Profile"})
        for n in (PROFILE_NAME, HR_PROFILE_NAME)
    }
    ws = get_hidden_workspaces()
    msg = (f"denied: {perms.get('total_recorded', '?')} doctypes | "
           f"employees: {counts[PROFILE_NAME]} hidden | HR: {counts[HR_PROFILE_NAME]} hidden "
           f"| workspaces hidden: {len(ws['hidden'])} visible: {len(ws['visible'])} "
           f"| applied to {res['applied']} users, {res['admins_exempt']} admins exempt")
    print(msg)          # bench execute prints this back to the operator
    return {"blocked": counts, "workspaces": get_hidden_workspaces(), **res}


# Frappe stamps the sidebars it ships with `standard = 1`. Ours are placeholders,
# so they carry 0 - which is also how sync_module_sidebars knows what it may
# remove again when a plan is upgraded.
SIDEBAR_PLACEHOLDER_ICON = "lock"


# ── Wave 4: denial, not hiding ───────────────────────────────────────────────
#
# Three levers were built before this one - block_modules, Workspace.is_hidden,
# and empty Workspace Sidebars - and a tenant still showed Payroll, Recruitment
# and CRM. Every sidebar item type except `workspace` is decided by PERMISSIONS
# (frappe/desk/desk_views.py), so hiding can never finish the job, and each new
# menu Frappe adds is another hole.
#
# Withholding roles does not work either: the unwanted access rides on roles the
# tenant must keep. HR Manager has read on Payroll and CRM by ERPNext default,
# and every user alive holds `All`.
#
# So we override the PERMISSIONS. From frappe/permissions.py:
#
#     doctypes_with_custom_perms = get_doctypes_with_custom_docperms()
#     for p in perms:
#         if p.parent not in doctypes_with_custom_perms:
#             custom_perms.append(p)
#
# Once ANY Custom DocPerm row exists for a doctype, its standard permissions are
# ignored entirely. That is the lever and the danger in one sentence.

# Roles that keep access to everything. Read from ADMIN_ROLES so there is one
# definition of "exempt" in this module, not two that can drift.
# Administrator is not listed because Frappe bypasses permission checks for it
# outright - adding it here would imply a guarantee we do not control.
def _exempt_roles():
    return set(ADMIN_ROLES)


# Where the record of our own work lives.
#
# A Single doctype, not site config: this is DATA - up to a few hundred
# permission rows - and it must survive in a database backup, because it is the
# only record of how to put a tenant's permissions back.
STATE_DOCTYPE = "Alvoraa Access State"


def _state():
    return frappe.get_single(STATE_DOCTYPE)


def _load(field):
    import json as _json

    raw = (_state().get(field) or "").strip()
    try:
        return _json.loads(raw) if raw else ({} if field == "permission_snapshot" else [])
    except Exception:
        frappe.log_error(title=f"module_access: unreadable {field}", message=raw[:2000])
        return {} if field == "permission_snapshot" else []


def _save(restricted=None, snapshot=None):
    import json as _json

    doc = _state()
    if restricted is not None:
        doc.restricted_doctypes = _json.dumps(sorted(restricted))
    if snapshot is not None:
        doc.permission_snapshot = _json.dumps(snapshot)
    doc.last_synced = frappe.utils.now()
    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)


def _recorded_restrictions():
    return set(_load("restricted_doctypes"))


# Permission rows that already existed before we touched a doctype.
#
# Frappe's reset_perms() restores the STANDARD permissions, which is exactly
# right for a doctype nobody had customised. But 40 of the 450 doctypes a Starter
# tenant blocks already carry Custom DocPerm rows - hrms/setup.py writes them at
# install - and for those, reset_perms would restore something DIFFERENT from
# what was there. So we keep the originals and put them back verbatim.
#
# 172 rows on a real site. Small enough to store exactly, which is the only
# honest way to promise a reversal.
_SNAPSHOT_FIELDS = ("role", "permlevel", "read", "write", "create", "delete",
                    "submit", "cancel", "amend", "report", "export", "import",
                    "share", "print", "email", "select", "if_owner")


def _snapshot_existing(doctype):
    rows = frappe.get_all("Custom DocPerm", filters={"parent": doctype},
                          fields=list(_SNAPSHOT_FIELDS))
    return [dict(r) for r in rows]


def _keep_exempt_row(doctype, exempt):
    """Leave at least one Custom DocPerm row on a restricted doctype.

    THIS IS LOAD-BEARING. Frappe decides whether to use custom permissions like
    this:

        doctypes_with_custom_perms = get_doctypes_with_custom_docperms()   # rows exist?
        for p in perms:
            if p.parent not in doctypes_with_custom_perms:
                custom_perms.append(p)                                    # else STANDARD

    So a doctype with ZERO custom rows silently falls back to its standard
    permissions - and "delete every role we do not exempt" produces exactly that
    whenever none of the exempt roles was in the original list. Measured: after
    restricting Salary Slip that way, an HR Manager could still read it.

    Keeping one row for an exempt role holds the doctype in custom-permission
    mode, which is what denies everybody else.
    """
    if frappe.db.exists("Custom DocPerm", {"parent": doctype}):
        return

    for role in sorted(exempt):
        std = frappe.get_all("DocPerm", filters={"parent": doctype, "role": role},
                             fields=list(_SNAPSHOT_FIELDS), limit=1)
        row = dict(std[0]) if std else {
            "role": role, "permlevel": 0,
            "read": 1, "write": 1, "create": 1, "delete": 1,
            "report": 1, "export": 1, "share": 1, "print": 1, "email": 1,
        }
        row["role"] = role
        doc = frappe.get_doc({"doctype": "Custom DocPerm", "parent": doctype,
                              "parenttype": "DocType", "parentfield": "permissions",
                              **row})
        # db_insert, for the same reason as _restore_snapshot: doc.insert()
        # queues a background job per row, and 450 doctypes overload the queue.
        doc.name = frappe.generate_hash(length=10)
        doc.db_insert()


def _restore_snapshot(doctype, rows):
    """Put back exactly what was there, without going through the document layer.

    doc.insert() on a permission row fires validation and hooks, and Frappe
    queues a background job for each one. Across a few hundred doctypes that
    reaches the queue limit and the whole release dies half-done:

        QueueOverloaded: Too many queued background jobs (550)

    Measured, on the first attempt at this. These rows are a restore of values we
    read from this same table minutes earlier, so there is nothing to validate.
    """
    for row in rows:
        doc = frappe.get_doc({"doctype": "Custom DocPerm", "parent": doctype,
                              "parenttype": "DocType", "parentfield": "permissions",
                              **row})
        doc.name = frappe.generate_hash(length=10)
        doc.db_insert()


def release_permissions(doctypes=None):
    """Give back access to doctypes we previously restricted.

    Built and tested BEFORE the restriction it undoes. A change that can stop a
    customer working should not ship until putting it back is proven.

    Deleting every Custom DocPerm row for a doctype puts Frappe back on the
    standard ones, so a doctype nobody had customised is restored exactly by
    doing nothing more. The 40 that WERE customised get their original rows
    written back from the snapshot.

    Only doctypes WE recorded are released. A Custom DocPerm somebody else made
    is not ours to delete.
    """
    ours = _recorded_restrictions()
    snapshot = _load("permission_snapshot")
    targets = ours if doctypes is None else (set(doctypes) & ours)

    released = []
    for dt in sorted(targets):
        if not frappe.db.exists("DocType", dt):
            continue
        try:
            # NOT frappe.permissions.reset_perms: it deletes each row as a
            # document, which queues a background job apiece and overloads the
            # queue long before 450 doctypes are done. A direct delete of the
            # same rows has the same effect on permissions - Frappe reads this
            # table, not a cache - without the per-row machinery.
            frappe.db.delete("Custom DocPerm", {"parent": dt})
            if dt in snapshot:
                # It had custom permissions before us. Standard rows are NOT what
                # was there, so put back exactly what we found.
                _restore_snapshot(dt, snapshot.pop(dt))
            released.append(dt)
        except Exception:
            frappe.log_error(title=f"module_access: could not release {dt}",
                             message=frappe.get_traceback())

    if released:
        _save(restricted=ours - set(released), snapshot=snapshot)
        frappe.db.commit()
        # Once, at the end. Clearing per doctype would be hundreds of round trips
        # for the same result.
        frappe.clear_cache()
    return {"released": released, "still_restricted": sorted(ours - set(released))}


def sync_permissions(features=None, limit=None, only=None):
    """Deny access to the doctypes this site did not buy. Wave 4.

    For every doctype in a blocked module, copy its standard permissions into
    Custom DocPerm and keep only the exempt roles. Frappe then ignores the
    standard rows entirely, so the doctype disappears from the API, the list
    view, the sidebar and the search bar at the same time - which is the point.
    Hiding only ever reached one of those at a time.

    Runs BOTH ways on every call. A doctype that is no longer blocked - because
    the plan was upgraded - is released before anything new is restricted, so a
    plan change is never one-way.

    Nothing here is hardcoded. The doctype list is derived from the modules the
    registry blocks, which are derived from the features the site bought. A
    doctype added by a future ERPNext release is covered the day it appears.
    """
    feats = features if features is not None else enabled_features()
    should_block = set(blocked_doctypes(feats))
    # `only` narrows the run to named doctypes. Useful for repairing one doctype
    # on a live tenant without re-walking 450, and it keeps the test suite from
    # taking eight minutes to prove things about six of them.
    if only is not None:
        should_block &= set(only)
    exempt = _exempt_roles()
    already = _recorded_restrictions()

    # Upgrades first: release before restricting, so a doctype that moved from
    # blocked to sold is never left denied by the same run that should free it.
    released = release_permissions(already - should_block)["released"]

    to_restrict = sorted(should_block - _recorded_restrictions())
    if limit:
        to_restrict = to_restrict[:limit]

    snapshot = _load("permission_snapshot")
    restricted, failed = [], []

    for dt in to_restrict:
        try:
            # setup_custom_perms returns True when it copied the standard rows,
            # and False when custom rows were already there. The False case is
            # the one that matters: 40 of the 450 doctypes a Starter tenant
            # blocks already carry customisations from hrms/setup.py - Salary
            # Slip among them - and skipping those would leave exactly the
            # doctypes the plan is meant to deny wide open.
            #
            # So we take them too, having first recorded what was there. The
            # snapshot is what makes the reversal a promise rather than a hope.
            if frappe.db.exists("Custom DocPerm", {"parent": dt}):
                if dt not in snapshot:
                    snapshot[dt] = _snapshot_existing(dt)

            # Deliberately NOT frappe.permissions.setup_custom_perms: it copies
            # the standard rows through the document layer, queueing a job per
            # row. We only ever KEEP the exempt roles, so copying everything and
            # deleting most of it was wasted work as well as a queue flood.
            frappe.db.delete("Custom DocPerm", {"parent": dt})
            # Without this the doctype can end up with no custom rows at all,
            # which puts its STANDARD permissions back and undoes the denial.
            _keep_exempt_row(dt, exempt)
            restricted.append(dt)
        except Exception:
            frappe.log_error(title=f"module_access: could not restrict {dt}",
                             message=frappe.get_traceback())
            failed.append(dt)

    if restricted:
        _save(restricted=_recorded_restrictions() | set(restricted), snapshot=snapshot)

    frappe.db.commit()
    frappe.clear_cache()
    return {"restricted": len(restricted), "released": len(released),
            "failed": len(failed), "snapshotted": len(snapshot),
            "total_recorded": len(_recorded_restrictions())}


@frappe.whitelist()
def get_restricted_doctypes():
    """What this site currently denies. For the console and for support."""
    return {"count": len(_recorded_restrictions()),
            "doctypes": sorted(_recorded_restrictions()),
            "snapshotted": sorted(_load("permission_snapshot"))}


def sync_module_sidebars(features=None):
    """Silence the desk sidebars for modules this site did not buy.

    Blocking a module hides it from the module LIST, and Frappe honours that. It
    does not reach the sidebar, because frappe.boot builds that from
    `auto_generate_sidebar_from_module()`, which does this:

        for module in frappe.get_all("Module Def", pluck="name"):

    Every module on the site, with no reference to the user's blocked modules.
    That is why a tenant with 31 modules blocked was still handed sidebars for
    Accounts, CRM, Quality and Maintenance.

    The generator has one guard we can use - it only auto-generates when no
    stored sidebar exists for that module:

        if not frappe.db.exists("Workspace Sidebar", {"name": module, "for_user": None}):

    So an EMPTY stored sidebar suppresses it. Frappe then drops the whole thing,
    because boot only shows a sidebar in which at least one real item survived.

    Reversible by design: an upgrade deletes the placeholder and Frappe generates
    the real sidebar again on the next boot.
    """
    if not frappe.db.exists("DocType", "Workspace Sidebar"):
        return {"skipped": "no Workspace Sidebar doctype on this Frappe"}

    feats = features if features is not None else enabled_features()
    blocked = set(blocked_module_defs(feats))
    existing_modules = {m.name for m in frappe.get_all("Module Def", fields=["name"])}
    blocked &= existing_modules

    silenced, restored = [], []

    for module in sorted(blocked):
        if frappe.db.exists("Workspace Sidebar", {"name": module, "for_user": None}):
            continue
        doc = frappe.get_doc({
            "doctype": "Workspace Sidebar",
            "title": module,
            "module": module,
            "standard": 0,
            "header_icon": SIDEBAR_PLACEHOLDER_ICON,
            "items": [],
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        silenced.append(module)

    # An upgrade must undo it, or a plan change is one-way. Only OUR placeholders
    # are removed: a sidebar Frappe ships, or one a customer built, is not ours.
    for row in frappe.get_all("Workspace Sidebar",
                              filters={"standard": 0, "for_user": ["is", "not set"]},
                              fields=["name", "module"]):
        if row.module and row.module not in blocked:
            doc = frappe.get_doc("Workspace Sidebar", row.name)
            if doc.header_icon == SIDEBAR_PLACEHOLDER_ICON and not doc.items:
                frappe.delete_doc("Workspace Sidebar", row.name,
                                  force=True, ignore_permissions=True)
                restored.append(row.module)

    frappe.db.commit()
    frappe.clear_cache()
    return {"silenced": silenced, "restored": restored}


def sync_workspaces(features=None):
    """Hide the desk workspaces this site did not buy, and reveal the ones it did.

    `is_hidden` is Frappe's own flag: a public workspace with it set disappears
    for everyone except a Workspace Manager. That keeps the tenant's own
    administrator able to see everything, which matches how module blocking
    already exempts them.

    Both directions matter. Hiding alone would make every plan change one-way,
    so an upgrade could never restore what a downgrade took away.

    Only touches workspaces the registry names. Anything else on the site -
    ERPNext's, or one the customer built - is left exactly as it is.
    """
    feats = features if features is not None else enabled_features()
    show, hide = sold_and_unsold_workspaces(feats)

    changed = {"hidden": [], "shown": []}
    for names, hidden in ((hide, 1), (show, 0)):
        for name in names:
            if not frappe.db.exists("Workspace", name):
                continue        # not every feature ships a workspace on every site
            if frappe.db.get_value("Workspace", name, "is_hidden") == hidden:
                continue
            # db_set, not save: Workspace.on_update rebuilds sidebar caches and
            # can reject a doc whose content predates a Frappe upgrade. The flag
            # is a single column and nothing else about the workspace changes.
            frappe.db.set_value("Workspace", name, "is_hidden", hidden,
                                update_modified=False)
            changed["hidden" if hidden else "shown"].append(name)

    frappe.db.commit()
    frappe.clear_cache()        # the sidebar is cached per user
    return changed


@frappe.whitelist()
def get_hidden_workspaces():
    """What this site currently hides in the desk sidebar. For support."""
    rows = frappe.get_all("Workspace", filters={"public": 1},
                          fields=["name", "module", "is_hidden"], order_by="name")
    return {"hidden": [r.name for r in rows if r.is_hidden],
            "visible": [r.name for r in rows if not r.is_hidden]}


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


# ── Moving between the portal and the desk ───────────────────────────────────

NAVBAR_LABEL = "Switch to Employee Portal"


def sync_navbar_item():
    """Add "Switch to Employee Portal" to the desk's top-right menu.

    Frappe owns that menu, and it is a real doctype - Navbar Settings, with a
    `settings_dropdown` table. Adding a row is supported; injecting markup into
    someone else's navbar with JavaScript is not, and would break the next time
    they change it.

    Idempotent: called on every sync.
    """
    settings = frappe.get_doc("Navbar Settings")
    for row in settings.settings_dropdown:
        if row.item_label == NAVBAR_LABEL:
            return NAVBAR_LABEL          # already there

    settings.append("settings_dropdown", {
        "item_label": NAVBAR_LABEL,
        "item_type": "Route",
        "route": "/hrms-employee",
        "is_standard": 0,
    })
    settings.flags.ignore_permissions = True
    settings.save(ignore_permissions=True)
    frappe.db.commit()
    return NAVBAR_LABEL


@frappe.whitelist()
def get_switch_target():
    """Where the portal's switch control should send THIS user, and what to call it.

    Returns None when the user has no business in the desk, so the portal can
    hide the control entirely rather than offering a door that leads nowhere.
    """
    user = frappe.session.user
    if user in NEVER_TOUCH:
        return None
    roles = set(frappe.get_roles(user))

    if ADMIN_ROLES & roles:
        return {"label": "Switch to Admin", "url": "/app"}
    if HR_ROLES & roles:
        # /app/hr is Frappe HR's own workspace - leaves, payroll, recruitment.
        return {"label": "Switch to HR Core", "url": "/app/hr"}
    return None
