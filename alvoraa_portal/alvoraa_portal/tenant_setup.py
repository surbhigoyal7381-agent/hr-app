"""First-run setup that happens ON a newly provisioned tenant site.

Called by the provisioning job:

    bench --site acme.alvoraa.co execute \\
        alvoraa_portal.tenant_setup.create_default_users --kwargs '{...}'

A fresh Frappe site has exactly one login: `Administrator`. That account is
shared, unattributable, and the wrong thing to hand a customer. Every tenant
therefore starts with two real accounts:

    HR      HR Manager      lands in Frappe HR, sees "Switch to HR Core"
    Admin   System Manager  lands in the desk,  sees "Switch to Admin"

Both are created with a generated password, returned once to the provisioning
screen, and flagged to force a change on first login.

Neither lands on the employee portal: `alvoraa_login` already sends anyone with a
desk role to /app. They reach the portal, if they want it, through "Switch to
Employee Portal" in the desk's top-right menu.
"""

import frappe


def _make_user(email, first_name, password, roles):
    """Create the user if absent, then set roles and password. Idempotent."""
    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
    else:
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            # Never mail a new tenant's staff during provisioning. The password
            # goes back to the operator on screen instead.
            "send_welcome_email": 0,
            "enabled": 1,
            "user_type": "System User",
        })
        user.flags.ignore_permissions = True
        user.insert(ignore_permissions=True)

    existing = {r.role for r in user.roles}
    for role in roles:
        if role not in existing and frappe.db.exists("Role", role):
            user.append("roles", {"role": role})

    user.flags.ignore_permissions = True
    user.save(ignore_permissions=True)

    if password:
        from frappe.utils.password import update_password

        update_password(email, password)
        # Make them choose their own on first login. The generated one is shown
        # on a provisioning screen and may be written down or pasted around.
        frappe.db.set_value("User", email, "reset_password_key", None)

    return user.name


def create_default_users(hr_email=None, admin_email=None,
                         hr_password=None, admin_password=None,
                         tenant_name=None):
    """Create the tenant's HR and Admin accounts. Returns what was created.

    Safe to run twice: existing users are updated rather than duplicated, which
    matters because provisioning can be retried after a partial failure.
    """
    created = {}

    if hr_email:
        created["hr"] = _make_user(
            hr_email,
            f"{tenant_name} HR" if tenant_name else "HR",
            hr_password,
            # NOT "Employee": Frappe HR grants that role from the Employee
            # record, and strips it again on save when there is none. These are
            # administrative logins, not staff - if this person is also an
            # employee, creating their Employee record adds the role properly.
            ["HR Manager", "HR User"],
        )

    if admin_email:
        created["admin"] = _make_user(
            admin_email,
            f"{tenant_name} Admin" if tenant_name else "Administrator",
            admin_password,
            ["System Manager"],
        )

    frappe.db.commit()

    # Module access follows roles, so apply it AFTER the roles are set - the HR
    # user needs the HR profile (which keeps the desk shell) and the admin needs
    # no profile at all.
    try:
        from alvoraa_portal.module_access import apply_to_users

        apply_to_users([u for u in created.values()])
    except Exception:
        frappe.log_error(title="tenant_setup: module access for default users",
                         message=frappe.get_traceback())

    print("created: " + ", ".join(f"{k}={v}" for k, v in created.items()))
    return created
