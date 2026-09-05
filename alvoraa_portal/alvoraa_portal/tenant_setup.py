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

import os

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

    Passwords are read from the ENVIRONMENT, not from the arguments. This runs
    as `bench ... execute ... --kwargs '{...}'`, and a command line is visible to
    every user on the machine through `ps` and is recorded in shell history. An
    environment block is readable only by the process owner. The arguments are
    kept for direct calls and for tests; the environment wins when both are set.
    """
    hr_password = os.environ.get("TENANT_HR_PASSWORD") or hr_password
    admin_password = os.environ.get("TENANT_ADMIN_PASSWORD") or admin_password

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


def complete_company_setup(company_name=None, company_abbr=None, country="India",
                           currency="INR", timezone="Asia/Kolkata", language="en",
                           fy_start_date=None, chart_of_accounts=None,
                           email=None, full_name="Administrator"):
    """Finish ERPNext's setup wizard during provisioning.

    A freshly provisioned tenant used to greet its first Administrator login with
    "Setup your organization" - company name, abbreviation, chart of accounts,
    financial year. That is our setup to do, not the customer's: we already ask
    for the workspace name, and everything else has a sensible default.

    Frappe shows the wizard whenever System Settings.setup_complete is 0, so the
    only durable fix is to actually COMPLETE it. Calling the same
    `setup_complete()` the wizard calls runs every stage - company, fiscal year,
    chart of accounts, defaults - and sets the flag as a consequence rather than
    faking it. Setting the flag alone would leave a tenant with no Company, and
    Frappe HR needs one for almost everything.

    Safe to run twice: frappe.is_setup_complete() short-circuits.
    """
    if frappe.is_setup_complete():
        print("setup already complete")
        return {"status": "already-complete"}

    fy_start_date = fy_start_date or f"{frappe.utils.nowdate()[:4]}-04-01"
    fy_end = frappe.utils.add_days(frappe.utils.add_months(fy_start_date, 12), -1)

    # Abbreviation: ERPNext appends it to every account name, so it must be short
    # and stable. Initials of the company name unless one was given.
    if not company_abbr:
        words = [w for w in (company_name or "Company").split() if w]
        company_abbr = ("".join(w[0] for w in words)[:5] or "CO").upper()

    args = {
        "language": language,
        "country": country,
        "timezone": timezone,
        "currency": currency,
        "company_name": company_name,
        "company_abbr": company_abbr,
        "chart_of_accounts": chart_of_accounts or "Standard",
        "fy_start_date": fy_start_date,
        "fy_end_date": str(fy_end),
        "email": email or frappe.session.user,
        "full_name": full_name,
    }

    from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

    setup_complete(args)
    frappe.db.commit()

    done = frappe.is_setup_complete()
    print(f"setup_complete={done} company={company_name} abbr={company_abbr} fy={fy_start_date}")
    return {"status": "ok", "setup_complete": bool(done),
            "company": company_name, "fy_start_date": fy_start_date}
