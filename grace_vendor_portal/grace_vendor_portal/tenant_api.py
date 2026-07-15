"""
Kinexus HRMS – Tenant Provisioning API
Manages Frappe sites (one per tenant) on this bench.

All endpoints require System Manager role.
Provisioning runs as a Frappe background job (queue=long) so the API
returns immediately with a job_id; the client polls get_provision_status().
"""

import frappe
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
PLAN_MODULES = {
    "starter":    ["hrms"],
    "business":   ["hrms", "vendor_portal", "goals"],
    "enterprise": ["hrms", "vendor_portal", "goals", "analytics"],
}


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

        tenants.append({
            "site_name":     site_name,
            "tenant_name":   cfg.get("tenant_name", site_name),
            "plan":          cfg.get("subscription_plan", "—"),
            "status":        status,
            "primary_color": cfg.get("primary_color", "#1a7f5a"),
            "logo_url":      cfg.get("tenant_logo_url", ""),
            "host_name":     cfg.get("host_name", f"http://{site_name}"),
            "modules":       cfg.get("modules_enabled", []),
            "support_email": cfg.get("support_email", ""),
        })

    # Sort: provisioning first, then alphabetical
    tenants.sort(key=lambda t: (0 if t["status"] in ("Queued","Provisioning") else 1,
                                t["tenant_name"].lower()))
    return tenants


@frappe.whitelist()
def create_tenant(subdomain, tenant_name, plan="starter",
                  primary_color="#1a7f5a", logo_url="", support_email=""):
    """Validate inputs, enqueue provisioning. Returns {job_id, site_name, admin_password}."""
    _require_admin()

    subdomain = subdomain.strip().lower()
    base_domain = os.environ.get("BASE_DOMAIN", "localhost")
    site_name = f"{subdomain}.{base_domain}"

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

    if plan not in PLAN_MODULES:
        frappe.throw(f"Invalid plan '{plan}'. Choose: starter, business, enterprise.")

    # ── Create job record ──────────────────────────────────────────────────
    admin_password = _generate_password()
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
        "grace_vendor_portal.tenant_api._run_provision",
        queue="long",
        timeout=1200,
        # deduplicate=False so two jobs can coexist
        job_id_suffix=job_id,
        # kwargs forwarded to the function:
        pjob_id=job_id,
        site_name=site_name,
        tenant_name=tenant_name,
        plan=plan,
        primary_color=primary_color,
        logo_url=logo_url,
        support_email=support_email,
        admin_password=admin_password,
        base_domain=base_domain,
        db_root_password=os.environ.get("DB_ROOT_PASSWORD", "123"),
    )

    return {
        "job_id":         job_id,
        "site_name":      site_name,
        "host_name":      f"http://{site_name}",
        "admin_password": admin_password,
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
    """Return all provisioning jobs, newest first."""
    _require_admin()
    jobs = _read_jobs()
    return sorted(jobs.values(), key=lambda j: j.get("started_at", ""), reverse=True)


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

def _run_provision(pjob_id, site_name, tenant_name, plan, primary_color,
                   logo_url, support_email, admin_password, base_domain, db_root_password):
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
            ["bash", "/workspace/provision_tenant.sh", subdomain, tenant_name, plan],
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


# ══════════════════════════════════════════════════════════════════════════
# Private helpers
# ══════════════════════════════════════════════════════════════════════════

def _require_admin():
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted.", frappe.PermissionError)
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw("Tenant management requires System Manager role.", frappe.PermissionError)


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


def _generate_password(length=16):
    alphabet = string.ascii_letters + string.digits + "!@#$"
    return "".join(secrets.choice(alphabet) for _ in range(length))
