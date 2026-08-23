"""
Kinexus HRMS – Tenant Provisioning API
Manages Frappe sites (one per tenant) on this bench.

All endpoints require System Manager role.
Provisioning runs as a Frappe background job (queue=long) so the API
returns immediately with a job_id; the client polls get_provision_status().
"""

import frappe

from alvoraa_portal.subscription import PLANS
import os
import json
import re
import uuid
import subprocess
import secrets
import string

from frappe.utils import now_datetime

# ── Paths ──────────────────────────────────────────────────────────────────
BENCH_PATH  = "/home/frappe/frappe-bench"
SITES_DIR   = f"{BENCH_PATH}/sites"
JOBS_FILE   = f"{SITES_DIR}/kinexus_provision_jobs.json"

# Directories inside sites/ that are NOT Frappe sites
_NOT_SITES = {"apps", "assets", "common_site_config.json", "currentsite.txt"}

# Plans → enabled module list
# PLAN_MODULES used to live here - a FOURTH copy of the plan definition, with a
# module list matching neither the admin page nor subscription.py. The single
# definition is alvoraa_portal/subscription.py.


# ══════════════════════════════════════════════════════════════════════════
# Public API – all require System Manager
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def list_tenants():
    """Return all Frappe sites on this bench with their tenant config."""
    _require_admin()
    jobs = _read_jobs()

    # Build a map of site_name → provisioning job (latest)
    provisioning_sites = {}
    for job in jobs.values():
        sn = job.get("site_name", "")
        if job.get("status") in ("Queued", "Provisioning"):
            provisioning_sites[sn] = job

    tenants = []
    for site_name in _all_site_names():
        cfg = _read_site_config(site_name)

        if site_name in provisioning_sites:
            status = provisioning_sites[site_name]["status"]
        elif cfg.get("maintenance_mode"):
            status = "Suspended"
        elif cfg.get("tenant_name") or cfg.get("subscription_plan"):
            status = "Active"
        else:
            status = "Active"   # non-tenant Frappe site (e.g. hrms.localhost)

        raw_modules = cfg.get("modules_enabled", [])
        if isinstance(raw_modules, str):
            try:
                raw_modules = json.loads(raw_modules)
            except Exception:
                raw_modules = []

        tenants.append({
            "site_name":     site_name,
            "tenant_name":   cfg.get("tenant_name", site_name),
            "plan":          cfg.get("subscription_plan", "—"),
            "status":        status,
            "primary_color": cfg.get("primary_color", "#1a7f5a"),
            "logo_url":      cfg.get("tenant_logo_url", ""),
            "host_name":     cfg.get("host_name", f"http://{site_name}"),
            "modules":       raw_modules,
            "support_email": cfg.get("support_email", ""),
        })

    # Sort: provisioning first, then alphabetical
    tenants.sort(key=lambda t: (0 if t["status"] in ("Queued","Provisioning") else 1,
                                t["tenant_name"].lower()))
    return tenants


@frappe.whitelist()
def create_tenant(subdomain, tenant_name, plan="starter",
                  hr_email="", admin_email="",
                  company_name="", company_abbr="", country="India",
                  currency="INR", timezone="Asia/Kolkata", fy_start_date="",
                  primary_color="#1a7f5a", logo_url="", support_email="", modules=None):
    """Validate inputs, enqueue provisioning. Returns {job_id, site_name, admin_password}."""
    _require_admin()

    subdomain = subdomain.strip().lower()
    base_domain = os.environ.get("BASE_DOMAIN", "localhost")
    site_name = f"{subdomain}.{base_domain}"

    # Normalise modules — accept list or JSON string from JS
    if modules is None:
        modules = ["hrms"]
    elif isinstance(modules, str):
        try:
            modules = json.loads(modules)
        except Exception:
            modules = [m.strip() for m in modules.split(",") if m.strip()]
    if "hrms" not in modules:
        modules = ["hrms"] + [m for m in modules if m != "hrms"]
    # Derive the plan label from the modules. This intentionally OVERWRITES the
    # `plan` argument: modules are the source of truth, so a caller cannot send a
    # label that contradicts what was actually provisioned.
    # Plan is derived from the feature set, using the ONE definition in
    # subscription.py. It used to be redefined here and again in update_tenant,
    # with a third copy in the admin page's JavaScript.
    mset = set(modules)
    plan = next((p for p, feats in PLANS.items() if set(feats) == mset), "custom")

    # ── Validation ────────────────────────────────────────────────────────
    if not re.match(r'^[a-z0-9][a-z0-9\-]{1,30}[a-z0-9]$', subdomain):
        frappe.throw("Subdomain must be 3–32 chars: lowercase letters, numbers, hyphens only. "
                     "Must start and end with a letter or number.")

    if os.path.isdir(f"{SITES_DIR}/{site_name}"):
        frappe.throw(f"A tenant with subdomain '{subdomain}' already exists.")

    # Check not already being provisioned
    jobs = _read_jobs()
    for job in jobs.values():
        if job.get("site_name") == site_name and job.get("status") in ("Queued","Provisioning"):
            frappe.throw(f"'{site_name}' is already being provisioned (job {job['job_id']}).")

    # `plan` is DERIVED from the ticked modules a few lines above, so it can only
    # be one of the registry's names. The old check rejected "custom" outright,
    # which made any selection that did not exactly match a preset impossible -
    # exactly what the Custom plan is for.
    if plan not in PLANS:
        frappe.throw(f"Invalid plan '{plan}'. Known plans: {', '.join(PLANS)}.")

    # ── Create job record ──────────────────────────────────────────────────
    admin_password = _generate_password()

    # Two real logins per tenant. Left blank, they are derived from the
    # subdomain so provisioning never depends on the operator remembering.
    hr_email = (hr_email or f"hr@{subdomain}.{base_domain}").strip().lower()
    admin_email = (admin_email or f"admin@{subdomain}.{base_domain}").strip().lower()
    hr_password = _generate_password()
    user_admin_password = _generate_password()
    job_id = uuid.uuid4().hex[:12]

    jobs[job_id] = {
        "job_id":          job_id,
        "site_name":       site_name,
        "tenant_name":     tenant_name,
        "plan":            plan,
        "status":          "Queued",
        "started_at":      str(now_datetime()),
        "finished_at":     None,
        "admin_password":  admin_password,
        "log":             "",
        "host_name":       f"http://{site_name}",
    }
    _write_jobs(jobs)

    # ── Enqueue background job ─────────────────────────────────────────────
    frappe.enqueue(
        "alvoraa_portal.tenant_api._run_provision",
        queue="long",
        timeout=1200,
        job_name=f"provision_{job_id}",
        # kwargs forwarded to the function:
        pjob_id=job_id,
        site_name=site_name,
        tenant_name=tenant_name,
        plan=plan,
        modules=",".join(modules),
        primary_color=primary_color,
        logo_url=logo_url,
        support_email=support_email,
        admin_password=admin_password,
        base_domain=base_domain,
        hr_email=hr_email,
        admin_email=admin_email,
        hr_password=hr_password,
        user_admin_password=user_admin_password,
        company_name=company_name or tenant_name,
        company_abbr=company_abbr,
        country=country,
        currency=currency,
        timezone=timezone,
        fy_start_date=fy_start_date,
        # No fallback. A default here does not make provisioning work - it makes
        # it fail with "Access denied for user 'root'" several steps later, after
        # the job has been queued and the operator has been told it started.
        # Better to refuse immediately and say why.
        db_root_password=_require_db_root_password(),
    )

    return {
        "job_id":         job_id,
        "site_name":      site_name,
        # Provisioning takes minutes and runs in a background worker. The console
        # shows this so the operator can close the dialog and come back, rather
        # than watching a spinner.
        "started_at":     str(now_datetime()),
        "estimated_minutes": 8,
        "host_name":      f"http://{site_name}",
        "admin_password": admin_password,
        # Shown once on the provisioning screen. Not stored anywhere afterwards.
        "users": [
            {"role": "HR Manager",     "email": hr_email,    "password": hr_password},
            {"role": "System Manager", "email": admin_email, "password": user_admin_password},
        ],
    }


@frappe.whitelist()
def get_provision_status(job_id):
    """Poll a single provisioning job."""
    _require_admin()
    jobs = _read_jobs()
    job = jobs.get(job_id)
    if not job:
        frappe.throw(f"Job '{job_id}' not found.")
    return job


@frappe.whitelist()
def list_provision_jobs():
    """Return all provisioning jobs, newest first, with secrets redacted.

    The initial admin password is returned exactly twice: by create_tenant, and
    by get_provision_status for the job the caller is actively polling. A bulk
    listing has no reason to hand back every tenant's credentials, so strip it.
    """
    _require_admin()
    jobs = _read_jobs()
    redacted = []
    for job in jobs.values():
        job = dict(job)
        job["admin_password"] = ""
        job["admin_password_redacted"] = True
        redacted.append(job)
    return sorted(redacted, key=lambda j: j.get("started_at", ""), reverse=True)


@frappe.whitelist()
def suspend_tenant(site_name, suspend=1):
    """Put a site in maintenance mode (suspend=1) or bring it back (suspend=0)."""
    _require_admin()
    _validate_site_name(site_name)
    if not os.path.isdir(f"{SITES_DIR}/{site_name}"):
        frappe.throw(f"Site '{site_name}' not found.")

    flag = "on" if frappe.parse_json(suspend) else "off"
    result = _bench_run(f"--site {site_name} set-maintenance-mode {flag}")
    if result.returncode != 0:
        frappe.throw("Failed to change maintenance mode: " + result.stderr)

    new_status = "Suspended" if flag == "on" else "Active"
    return {"status": new_status, "site_name": site_name}


@frappe.whitelist()
def update_tenant(site_name, tenant_name="", plan="", modules=None,
                  primary_color="", support_email=""):
    """Update an existing tenant's config; queues a background app-install if new modules need it."""
    _require_admin()
    _validate_site_name(site_name)

    if not os.path.isdir(f"{SITES_DIR}/{site_name}"):
        frappe.throw(f"Site '{site_name}' not found.")

    # Normalize modules list
    if modules is not None:
        if isinstance(modules, str):
            try:
                modules = json.loads(modules)
            except Exception:
                modules = [m.strip() for m in modules.split(",") if m.strip()]
        if "hrms" not in modules:
            modules = ["hrms"] + [m for m in modules if m != "hrms"]

    # Derive plan label from module set
    from alvoraa_portal.subscription import PLANS

    if modules is not None:
        mset = set(modules)
        plan = next((p for p, feats in PLANS.items() if set(feats) == mset), "custom")

    # Update scalar site_config values
    for key, val in [
        ("tenant_name",      tenant_name),
        ("subscription_plan", plan),
        ("primary_color",    primary_color),
        ("support_email",    support_email),
    ]:
        if val:
            r = _bench_run(f'--site {site_name} set-config {key} "{val}"')
            if r.returncode != 0:
                frappe.throw(f"Failed to update {key}: {r.stderr}")

    # Update modules_enabled list
    if modules is not None:
        _MOD_MAP = {
            "hrms":        "hrms",
            "payroll":     "Payroll",
            "recruitment": "Recruitment",
            "vendor":      "Vendor Portal",
            "goals":       "Goals",
            "analytics":   "Analytics",
        }
        modules_enabled = [_MOD_MAP.get(m, m) for m in modules]

        # `features` is the authoritative value: the raw selection ids the
        # registry understands (portal, payroll, erp_accounts...).
        # `modules_enabled` keeps human labels for display and older callers.
        # Writing only labels meant subscription.enabled_features() could not
        # read the selection back.
        r = _bench_run(f"--site {site_name} set-config -p features '{json.dumps(list(modules))}'")
        if r.returncode != 0:
            frappe.throw(f"Failed to update features: {r.stderr}")
        # -p makes bench evaluate the value as a Python object. Without it the
        # JSON is stored as a STRING, so site_config holds
        #   "modules_enabled": "[\"hrms\", \"Payroll\", ...]"
        # instead of a list. Anything doing len() or iterating over it then reads
        # characters, not module names.
        r = _bench_run(f"--site {site_name} set-config -p modules_enabled '{json.dumps(modules_enabled)}'")
        if r.returncode != 0:
            frappe.throw(f"Failed to update modules: {r.stderr}")

    _bench_run(f"--site {site_name} clear-cache")

    # Rebuild the Module Profile so the desk shows only what was bought, and
    # re-save its users: Frappe copies block_modules on SAVE, so a profile that
    # changed afterwards does nothing until the users are saved again.
    if modules is not None:
        r = _bench_run(f"--site {site_name} execute alvoraa_portal.module_access.sync_site")
        if r.returncode != 0:
            # Not fatal: the plan is recorded, the desk just still shows too much.
            frappe.log_error(
                title=f"module_access sync failed for {site_name}",
                message=r.stderr,
            )

    # Queue background install for any newly-added apps not yet on the site
    if modules is not None:
        installed = _get_installed_apps(site_name)
        needs_vendor = "vendor" in modules and "alvoraa_portal" not in installed
        needs_goals  = "goals"  in modules and "alvoraa_goals"          not in installed

        if needs_vendor or needs_goals:
            job_id = uuid.uuid4().hex[:12]
            cfg = _read_site_config(site_name)
            jobs = _read_jobs()
            jobs[job_id] = {
                "job_id":         job_id,
                "site_name":      site_name,
                "tenant_name":    cfg.get("tenant_name", site_name),
                "plan":           plan or cfg.get("subscription_plan", "custom"),
                "status":         "Provisioning",
                "started_at":     str(now_datetime()),
                "finished_at":    None,
                "admin_password": "",
                "log":            f"[{now_datetime()}] Installing additional module apps…\n",
                "host_name":      cfg.get("host_name", f"http://{site_name}"),
            }
            _write_jobs(jobs)
            frappe.enqueue(
                "alvoraa_portal.tenant_api._run_install_modules",
                queue="long",
                timeout=600,
                job_name=f"install_modules_{job_id}",
                pjob_id=job_id,
                site_name=site_name,
                install_vendor=needs_vendor,
                install_goals=needs_goals,
            )
            return {
                "status": "installing",
                "job_id": job_id,
                "message": "Configuration saved. Installing new module apps in the background.",
            }

    return {"status": "ok", "message": "Tenant configuration updated."}


@frappe.whitelist()
def get_tenant_stats(site_name):
    """Return live stats from a tenant site (user count, last backup, etc.)."""
    _require_admin()
    _validate_site_name(site_name)

    stats = {"site_name": site_name, "users": 0, "last_backup": None}
    try:
        r = _bench_run(
            f"--site {site_name} execute frappe.db.count "
            "--args '[\"User\"]' --kwargs '{\"filters\": {\"enabled\": 1}}'",
            timeout=10
        )
        if r.returncode == 0:
            lines = r.stdout.strip().splitlines()
            stats["users"] = int(lines[-1]) if lines else 0
    except Exception:
        pass

    return stats


# ══════════════════════════════════════════════════════════════════════════
# Background job (called by Frappe worker, not directly by API)
# ══════════════════════════════════════════════════════════════════════════

def _run_provision(pjob_id, site_name, tenant_name, plan, modules,
                   primary_color, logo_url, support_email, admin_password,
                   base_domain, db_root_password,
                   hr_email=None, admin_email=None,
                   hr_password=None, user_admin_password=None,
                   company_name=None, company_abbr=None, country="India",
                   currency="INR", timezone="Asia/Kolkata", fy_start_date=None):
    """
    Runs in a Frappe long-queue worker.
    Calls provision_tenant.sh and writes status back to JOBS_FILE.
    """
    def _update(status, log_append="", finished=False):
        jobs = _read_jobs()
        if pjob_id in jobs:
            jobs[pjob_id]["status"] = status
            if log_append:
                jobs[pjob_id]["log"] = (jobs[pjob_id].get("log") or "") + log_append
            if finished:
                jobs[pjob_id]["finished_at"] = str(now_datetime())
                if status != "Done":
                    jobs[pjob_id]["admin_password"] = ""  # wipe on failure
        _write_jobs(jobs)

    _update("Provisioning", f"[{now_datetime()}] Starting provisioning for {site_name}…\n")

    subdomain = site_name.split(".")[0]
    env = {
        **os.environ,
        "BASE_DOMAIN":     base_domain,
        "ADMIN_PASSWORD":  admin_password,
        "DB_ROOT_PASSWORD": db_root_password,
        "PRIMARY_COLOR":   primary_color,
        "SUPPORT_EMAIL":   support_email or "support@kinexus.in",
    }

    try:
        result = subprocess.run(
            ["bash", "/workspace/provision_tenant.sh", subdomain, tenant_name, plan, modules],
            capture_output=True,
            text=True,
            cwd=BENCH_PATH,
            env=env,
            timeout=900,
        )

        log = result.stdout
        if result.stderr:
            log += f"\n--- stderr ---\n{result.stderr}"

        if result.returncode == 0:
            # Write extra config that provision_tenant.sh doesn't cover
            # Finish ERPNext's setup wizard here, or the tenant's first
            # Administrator login is met with "Setup your organization". We
            # already know the company name; the rest has sane defaults.
            import json as _sj
            _setup = {
                "company_name": company_name or tenant_name,
                "company_abbr": company_abbr or "",
                "country": country, "currency": currency, "timezone": timezone,
                "fy_start_date": fy_start_date or "",
                "email": admin_email,
            }
            rs = _bench_run(
                f"--site {site_name} execute alvoraa_portal.tenant_setup.complete_company_setup "
                f"--kwargs '{_sj.dumps(_setup)}'",
                timeout=600,
            )
            if rs.returncode != 0:
                log += "\n[WARN] company setup did not complete: " + (rs.stderr or "")
            # Every tenant starts with two real logins. A fresh Frappe site has
            # only `Administrator`, which is shared and unattributable - not
            # something to hand a customer.
            import json as _json
            _users = {
                "hr_email": hr_email, "admin_email": admin_email,
                "hr_password": hr_password, "admin_password": user_admin_password,
                "tenant_name": tenant_name,
            }
            ru = _bench_run(
                f"--site {site_name} execute alvoraa_portal.tenant_setup.create_default_users "
                f"--kwargs '{_json.dumps(_users)}'"
            )
            if ru.returncode != 0:
                log += "\n[WARN] default users not created: " + (ru.stderr or "")

            if logo_url:
                _bench_run(f"--site {site_name} set-config tenant_logo_url \"{logo_url}\"")

            # Update host_name in jobs file
            jobs = _read_jobs()
            if pjob_id in jobs:
                jobs[pjob_id]["host_name"] = f"http://{site_name}"
            _write_jobs(jobs)

            _update("Done", log + f"\n[{now_datetime()}] ✅ Provisioning complete.\n", finished=True)
        else:
            _update("Failed", log + f"\n[{now_datetime()}] ❌ Script exited with code {result.returncode}.\n", finished=True)

    except subprocess.TimeoutExpired:
        _update("Failed", f"\n[{now_datetime()}] ❌ Timed out after 15 minutes.\n", finished=True)
    except Exception as exc:
        _update("Failed", f"\n[{now_datetime()}] ❌ Exception: {exc}\n", finished=True)


def _get_installed_apps(site_name):
    """Return list of Frappe app names installed on a site."""
    r = _bench_run(f"--site {site_name} list-apps", timeout=15)
    if r.returncode != 0:
        return []
    # `bench list-apps` prints "name version branch", e.g.
    #     alvoraa_portal 0.0.1      UNVERSIONED
    # Keeping the whole line meant `"alvoraa_portal" not in installed` was always
    # True, so every tenant update queued a background install for apps that were
    # already there. Take the first column only.
    apps = []
    for line in r.stdout.strip().splitlines():
        line = line.strip()
        if line:
            apps.append(line.split()[0])
    return apps


def _run_install_modules(pjob_id, site_name, install_vendor=False, install_goals=False):
    """Background job: install additional Frappe apps on an existing site."""
    def _update(status, log_append="", finished=False):
        jobs = _read_jobs()
        if pjob_id in jobs:
            jobs[pjob_id]["status"] = status
            if log_append:
                jobs[pjob_id]["log"] = (jobs[pjob_id].get("log") or "") + log_append
            if finished:
                jobs[pjob_id]["finished_at"] = str(now_datetime())
        _write_jobs(jobs)

    try:
        if install_vendor:
            _update("Provisioning", f"[{now_datetime()}] Installing alvoraa_portal…\n")
            r = _bench_run(f"--site {site_name} install-app alvoraa_portal", timeout=300)
            if r.returncode != 0:
                raise RuntimeError(f"alvoraa_portal install failed:\n{r.stderr}")
            _update("Provisioning", r.stdout + "\n")

        if install_goals:
            _update("Provisioning", f"[{now_datetime()}] Installing alvoraa_goals…\n")
            r = _bench_run(f"--site {site_name} install-app alvoraa_goals", timeout=300)
            if r.returncode != 0:
                raise RuntimeError(f"alvoraa_goals install failed:\n{r.stderr}")
            _update("Provisioning", r.stdout + "\n")

        _bench_run(f"--site {site_name} clear-cache")
        _update("Done", f"[{now_datetime()}] ✅ Module installation complete.\n", finished=True)

    except Exception as exc:
        _update("Failed", f"[{now_datetime()}] ❌ {exc}\n", finished=True)


# ══════════════════════════════════════════════════════════════════════════
# Private helpers
# ══════════════════════════════════════════════════════════════════════════

def _require_admin():
    """Guard every tenant-management endpoint.

    Two independent checks — BOTH must pass:

    1. The request must be served by the control-plane site. Tenant sites are
       ordinary Frappe sites whose own admins legitimately hold System Manager,
       so a role check alone would let any tenant's admin enumerate, suspend,
       reconfigure or read provisioning secrets for EVERY other tenant on the
       bench. The control plane is opted in explicitly via site_config.json:
           "alvoraa_control_plane": 1
       A tenant site never carries that flag, so this API does not exist there.
    2. The caller must hold System Manager on the control-plane site.
    """
    if not frappe.conf.get("alvoraa_control_plane"):
        frappe.throw(
            "Tenant management is not available on this site.",
            frappe.PermissionError,
        )
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted.", frappe.PermissionError)
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw("Tenant management requires System Manager role.", frappe.PermissionError)


@frappe.whitelist()
def is_control_plane():
    """Side-effect-free probe so the admin UI can hide itself on tenant sites."""
    return bool(frappe.conf.get("alvoraa_control_plane"))


def _require_db_root_password():
    """The MariaDB root password, or a clear error.

    Provisioning creates a new site, which means creating a database and a
    database user, which needs root. The value comes from the environment - set
    in deploy/envs/*.env and passed through by docker-compose.app.yml.

    It was previously `os.environ.get("DB_ROOT_PASSWORD", "123")`. The container
    did not have the variable, so every provisioning attempt tried to log in as
    root with the password "123" and failed deep inside `bench new-site`, with a
    MySQL traceback that said nothing about configuration.
    """
    pw = os.environ.get("DB_ROOT_PASSWORD")
    if not pw:
        frappe.throw(
            "DB_ROOT_PASSWORD is not set in this container, so a new site cannot "
            "be created. Add it to deploy/envs/&lt;env&gt;.env and recreate the backend."
        )
    return pw


def _validate_site_name(site_name):
    """Prevent path traversal."""
    if ".." in site_name or "/" in site_name or "\\" in site_name:
        frappe.throw("Invalid site name.")


def _all_site_names():
    try:
        return sorted([
            d for d in os.listdir(SITES_DIR)
            if os.path.isdir(f"{SITES_DIR}/{d}") and d not in _NOT_SITES
        ])
    except Exception:
        return []


def _read_site_config(site_name):
    path = f"{SITES_DIR}/{site_name}/site_config.json"
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def _read_jobs():
    try:
        with open(JOBS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _write_jobs(jobs):
    try:
        with open(JOBS_FILE, "w") as f:
            json.dump(jobs, f, indent=2, default=str)
    except Exception as e:
        frappe.log_error(str(e), "Kinexus: could not write jobs file")


def _bench_run(cmd, timeout=30):
    return subprocess.run(
        f"bench {cmd}",
        shell=True,
        capture_output=True,
        text=True,
        cwd=BENCH_PATH,
        timeout=timeout,
    )


def _generate_password(length=18):
    # Alphanumeric only — avoids shell/SQL quoting issues when passed via env vars
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
