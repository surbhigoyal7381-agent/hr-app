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
def _bench_path():
    """Where this bench actually lives.

    This used to be hardcoded to "/home/frappe/frappe-bench", which is true in
    our container and false everywhere else - CI runs at /home/runner. The jobs
    file was then written to a path that did not exist, and because _write_jobs
    swallowed the error, provisioning appeared to work while recording nothing.
    """
    try:
        from frappe.utils import get_bench_path

        return get_bench_path()
    except Exception:
        return "/home/frappe/frappe-bench"


BENCH_PATH  = _bench_path()
SITES_DIR   = f"{BENCH_PATH}/sites"
JOBS_FILE   = f"{SITES_DIR}/kinexus_provision_jobs.json"

# Directories inside sites/ that are NOT Frappe sites
_NOT_SITES = {"apps", "assets", "common_site_config.json", "currentsite.txt"}

# ── Guards against a half-deployed bench ───────────────────────────────────
#
# On 2026-08-23 a deploy replaced the web container but left the long-queue
# worker on the previous image. create_tenant sent an argument the old
# _run_provision did not accept, so the job died with a TypeError before it ran
# a single line - and because only the job itself ever writes status, the
# console showed "Queued" with an empty log for an hour.
#
# The guards below need nothing set per environment. They ship in the image and
# behave identically on dev, test and production.

# Bump ONLY when _run_provision's arguments change. The number travels with the
# job, so a worker on an older image can say exactly what is wrong instead of
# raising TypeError. This is deliberately NOT the app version: an unrelated
# release must not invalidate jobs that are already queued.
PROVISION_CONTRACT = 2

# A job that has not moved in this long is not queued, it is abandoned. Without
# this, one dead job blocks its subdomain for ever and the only cure is editing
# JSON on the server by hand.
#
# 30 minutes is chosen to sit ABOVE the RQ timeout on the job itself (1200s =
# 20 minutes), so a run that is genuinely still working can never be declared
# stale. Raise the job timeout and this must move with it.
STALE_AFTER_MINUTES = 30

# Anything matching these is stripped before a traceback reaches the jobs file.
# Provisioning passes generated passwords as job arguments, and RQ puts the
# arguments into the traceback.
_SECRET_HINT = ("password", "passwd", "secret", "token", "api_key", "api_secret")


def _redact(text):
    """Blank out anything password-shaped in a traceback before storing it."""
    if not text:
        return ""
    out = []
    for line in str(text).splitlines():
        low = line.lower()
        out.append("    <redacted - contained a secret>"
                   if any(h in low for h in _SECRET_HINT) else line)
    return "\n".join(out)


def _long_worker_alive():
    """Is anything actually listening on the long queue right now?

    Asks Redis what is running rather than trusting configuration, so it is
    correct in every environment without being told about any of them.
    """
    try:
        from frappe.utils.background_jobs import get_queue, get_workers

        return bool(get_workers(get_queue("long")))
    except Exception:
        # Never block provisioning because the check itself broke.
        frappe.log_error(title="tenant_api: long-worker check failed",
                         message=frappe.get_traceback())
        return True


def _is_stale(job):
    """True when a job claims to be running but has not moved for a long time."""
    if job.get("status") not in ("Queued", "Provisioning"):
        return False
    started = job.get("started_at")
    if not started:
        return False
    try:
        from frappe.utils import time_diff_in_seconds

        return time_diff_in_seconds(now_datetime(), started) > STALE_AFTER_MINUTES * 60
    except Exception:
        return False


def _effective_status(job):
    """The status to SHOW: a stalled job must not keep claiming to be queued."""
    return "Stalled" if _is_stale(job) else job.get("status")


def _update_job(pjob_id, **fields):
    """Merge fields into one job record.

    Re-reads immediately before writing. Both the web process and the worker
    write this file, so building the new contents from a copy read earlier would
    drop whatever the other one wrote in between.
    """
    jobs = _read_jobs()
    if pjob_id not in jobs:
        return
    jobs[pjob_id].update(fields)
    _write_jobs(jobs)


def _provision_failed(job, connection, type, value, traceback):
    """RQ failure callback - the only thing that reports a job that never ran.

    Registered with frappe.enqueue(on_failure=...). It fires even when the
    ARGUMENTS are rejected, which is the case an in-function try/except can
    never catch: _run_provision had not started, so it could not report on
    itself. Without this the console shows "Queued" for ever.
    """
    try:
        outer = job.kwargs or {}
        pjob_id = (outer.get("kwargs") or {}).get("pjob_id") or outer.get("pjob_id")
        if not pjob_id:
            return
        prev = (_read_jobs().get(pjob_id) or {}).get("log") or ""
        _forget_credentials(pjob_id)   # never keep a secret for a failed job
        _update_job(
            pjob_id,
            status="Failed",
            finished_at=str(now_datetime()),
            log=prev + "\n[" + str(now_datetime()) + "] The job failed before it "
                "could report on itself:\n" + _redact(value) + "\n",
        )
    except Exception:
        frappe.log_error(title="tenant_api: failure callback broke",
                         message=frappe.get_traceback())
    finally:
        # frappe.enqueue defaults on_failure to truncate_failed_registry, and
        # passing our own REPLACES it. Call it so the registry keeps being trimmed.
        try:
            from frappe.utils.background_jobs import truncate_failed_registry

            truncate_failed_registry(job, connection, type, value, traceback)
        except Exception:
            pass

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
        # _effective_status, not the stored one: a job that died on arrival is
        # still recorded as "Queued" and would otherwise claim the row for ever.
        if _effective_status(job) in ("Queued", "Provisioning"):
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
    """Validate inputs, enqueue provisioning.

    Returns {job_id, site_name, started_at, ...} and NO credentials: they do not
    exist yet. The worker generates them, and get_provision_status returns them
    once the job reports Done.
    """
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
        if job.get("site_name") != site_name:
            continue
        # A job that died on arrival used to block its subdomain for ever: the
        # status is only ever written by the job itself, so one that never ran
        # stayed "Queued" and the only cure was editing JSON on the server.
        if job.get("status") in ("Queued", "Provisioning") and not _is_stale(job):
            frappe.throw(f"'{site_name}' is already being provisioned (job {job['job_id']}).")

    # ── Pre-flight: can this possibly work? ───────────────────────────────
    # Checked here so the operator is told immediately, rather than several
    # minutes later inside `bench new-site`. The VALUE is deliberately not sent
    # to the worker: it reads the same variable from its own environment, which
    # keeps the database root password out of Redis.
    _require_db_root_password()


    # Queueing into a queue nobody reads looks exactly like success. The job sits
    # in Redis, the console says "Queued", and no error appears anywhere.
    if not _long_worker_alive():
        frappe.throw(
            "No background worker is running for the 'long' queue, so provisioning "
            "cannot start. Start the long worker on this bench and try again."
        )

    # `plan` is DERIVED from the ticked modules a few lines above, so it can only
    # be one of the registry's names. The old check rejected "custom" outright,
    # which made any selection that did not exactly match a preset impossible -
    # exactly what the Custom plan is for.
    if plan not in PLANS:
        frappe.throw(f"Invalid plan '{plan}'. Known plans: {', '.join(PLANS)}.")

    # ── Create job record ──────────────────────────────────────────────────
    #
    # No password is generated here, and none is passed to the worker. RQ stores
    # a job's arguments in Redis, so anything secret handed to enqueue() is
    # readable by anyone who can reach Redis - for every tenant, indefinitely.
    # The worker generates its own and puts them straight into Frappe's
    # encrypted store; see _store_credentials.
    #
    # Two real logins per tenant. Left blank, they are derived from the
    # subdomain so provisioning never depends on the operator remembering.
    hr_email = (hr_email or f"hr@{subdomain}.{base_domain}").strip().lower()
    admin_email = (admin_email or f"admin@{subdomain}.{base_domain}").strip().lower()
    job_id = uuid.uuid4().hex[:12]

    jobs[job_id] = {
        "job_id":          job_id,
        "site_name":       site_name,
        "tenant_name":     tenant_name,
        "plan":            plan,
        "status":          "Queued",
        "started_at":      str(now_datetime()),
        "finished_at":     None,
        # Not secret, and needed to label the credentials when the job finishes.
        "hr_email":        hr_email,
        "admin_email":     admin_email,
        "log":             "",
        "host_name":       f"http://{site_name}",
    }
    _write_jobs(jobs)

    # ── Enqueue background job ─────────────────────────────────────────────
    #
    # The job record above exists ONLY so the worker has somewhere to report.
    # It is not a tenant: a tenant is a real site directory with a config, and
    # list_tenants reads those, so nothing appears as a tenant until the site is
    # genuinely built.
    #
    # If the enqueue is refused, that record would otherwise sit at "Queued"
    # for ever, blocking its own subdomain. So a refusal marks it Failed
    # immediately and re-raises: nothing is left claiming to be in progress.
    try:
        frappe.enqueue(
            "alvoraa_portal.tenant_api._run_provision",
            queue="long",
            timeout=1200,
            job_name=f"provision_{job_id}",
            # Fires even when the ARGUMENTS are rejected - the one failure an
            # in-function try/except cannot catch, because the function never ran.
            on_failure=_provision_failed,
            # Travels with the job so a worker on an older image can say so.
            contract=PROVISION_CONTRACT,
            # kwargs forwarded to the function:
            pjob_id=job_id,
            site_name=site_name,
            tenant_name=tenant_name,
            plan=plan,
            modules=",".join(modules),
            primary_color=primary_color,
            logo_url=logo_url,
            support_email=support_email,
            base_domain=base_domain,
            hr_email=hr_email,
            admin_email=admin_email,
            company_name=company_name or tenant_name,
            company_abbr=company_abbr,
            country=country,
            currency=currency,
            timezone=timezone,
            fy_start_date=fy_start_date,
        )
    except Exception:
        _update_job(
            job_id,
            status="Failed",
            finished_at=str(now_datetime()),
            log="Could not queue the provisioning job:\n"
                + _redact(frappe.get_traceback()),
        )
        raise

    return {
        "job_id":         job_id,
        "site_name":      site_name,
        # Provisioning takes minutes and runs in a background worker. The console
        # shows this so the operator can close the dialog and come back, rather
        # than watching a spinner.
        "started_at":     str(now_datetime()),
        "estimated_minutes": 8,
        "host_name":      f"http://{site_name}",
        # No credentials here: they do not exist yet. The worker generates them
        # and get_provision_status hands them back once the job reports Done.
        "hr_email":       hr_email,
        "admin_email":    admin_email,
    }


@frappe.whitelist()
def get_provision_status(job_id):
    """Poll a single provisioning job."""
    _require_admin()
    jobs = _read_jobs()
    job = jobs.get(job_id)
    if not job:
        frappe.throw(f"Job '{job_id}' not found.")
    job = dict(job)

    # Credentials live in Frappe's encrypted store, not in the jobs file. They
    # are handed back only for a job that actually produced a tenant.
    if job.get("status") == "Done":
        creds = _read_credentials(job_id)
        job["admin_password"] = creds.get("admin_password", "")
        job["users"] = [
            {"role": "HR Manager", "email": job.get("hr_email", ""),
             "password": creds.get("hr_password", "")},
            {"role": "System Manager", "email": job.get("admin_email", ""),
             "password": creds.get("user_admin_password", "")},
        ]
    else:
        job["admin_password"] = ""
        job["users"] = []

    if _is_stale(job):
        job["status"] = "Stalled"
        job["log"] = (job.get("log") or "") + (
            f"[{now_datetime()}] No progress for over {STALE_AFTER_MINUTES} minutes. "
            f"The worker that should run this is probably not running. "
            f"This subdomain is free to try again.\n"
        )
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
        job["status"] = _effective_status(job)
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
                   primary_color, logo_url, support_email,
                   base_domain,
                   hr_email=None, admin_email=None,
                   company_name=None, company_abbr=None, country="India",
                   currency="INR", timezone="Asia/Kolkata", fy_start_date=None,
                   contract=None, **extra):
    """
    Runs in a Frappe long-queue worker.
    Calls provision_tenant.sh and writes status back to JOBS_FILE.

    `**extra` is deliberate. A deploy can leave this worker on an older image
    than the web process that queued the job, and an unknown keyword used to
    raise TypeError before the first line ran - which no handler here could
    report. Unknown arguments are now absorbed, and the mismatch is reported
    below in words instead.
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
                    # A failed run leaves no usable tenant, so its passwords are
                    # of value to nobody except an attacker.
                    _forget_credentials(pjob_id)
        _write_jobs(jobs)

    # The web process stamps the contract it was built against. A lower number
    # here means this worker is running older code than the site that queued the
    # job, and provisioning would silently skip whatever the new arguments carry.
    if contract is not None and int(contract) > PROVISION_CONTRACT:
        _update(
            "Failed",
            f"[{now_datetime()}] This job was created by a newer build "
            f"(contract {contract}) than the worker running it "
            f"(contract {PROVISION_CONTRACT}).\n"
            f"The worker is on an older image than the web process. Redeploy the "
            f"whole stack - including the long-queue worker - and create the "
            f"tenant again. No site was created.\n",
            finished=True,
        )
        return

    if extra:
        _update("Queued", f"[{now_datetime()}] Ignoring unknown arguments from a "
                          f"newer build: {', '.join(sorted(extra))}\n")

    _update("Provisioning", f"[{now_datetime()}] Starting provisioning for {site_name}…\n")

    # Secrets are generated HERE, in the worker, and never travel through the
    # queue. They go straight into Frappe's encrypted store, and reach the
    # operator through get_provision_status once the job is Done.
    admin_password      = _generate_password()
    hr_password         = _generate_password()
    user_admin_password = _generate_password()
    _store_credentials(pjob_id,
                       admin_password=admin_password,
                       hr_password=hr_password,
                       user_admin_password=user_admin_password)

    # Read from this worker's own environment rather than accepting it as a job
    # argument, which would put the database root password into Redis.
    db_root_password = _require_db_root_password()

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
            # Emails and the tenant name are not secret, so they can go on the
            # command line. The two passwords MUST NOT: `ps` shows a process's
            # arguments to every user on the box, and shells record them in
            # history. They travel in the environment instead, which the kernel
            # exposes only to the process owner.
            _users = {
                "hr_email": hr_email, "admin_email": admin_email,
                "tenant_name": tenant_name,
            }
            ru = _bench_run(
                f"--site {site_name} execute alvoraa_portal.tenant_setup.create_default_users "
                f"--kwargs '{_json.dumps(_users)}'",
                env={**env,
                     "TENANT_HR_PASSWORD": hr_password,
                     "TENANT_ADMIN_PASSWORD": user_admin_password},
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
    """Persist the job records, or fail loudly.

    This used to log and carry on. A write that fails silently is the same bug
    as a job that dies without reporting: provisioning looks fine and records
    nothing, so the console shows a status that was never updated. If this file
    cannot be written, that is worth stopping for.
    """
    try:
        with open(JOBS_FILE, "w") as f:
            json.dump(jobs, f, indent=2, default=str)
    except Exception as e:
        frappe.log_error(str(e), "Alvoraa: could not write jobs file")
        raise


def _bench_run(cmd, timeout=30, env=None):
    """Run a bench command.

    `env` exists so secrets can be handed to a subprocess WITHOUT putting them
    on the command line. Arguments are world-readable through `ps` and land in
    shell history; an environment block is readable only by the process owner.
    """
    return subprocess.run(
        f"bench {cmd}",
        shell=True,
        capture_output=True,
        text=True,
        cwd=BENCH_PATH,
        timeout=timeout,
        env=env,
    )


# ── Credential storage ─────────────────────────────────────────────────────
#
# Provisioning produces three logins the operator must be given once. Where
# those live matters, because until 2026-08-23 they lived in three bad places
# at the same time:
#
#   1. As background-job arguments, which RQ stores in Redis. Anyone who could
#      reach Redis could read every tenant's initial passwords.
#   2. In plain text in the jobs JSON file on disk.
#   3. On a command line - `bench ... --kwargs '{"hr_password": ...}'` - which
#      `ps` shows to every user on the box.
#
# They now live in Frappe's own encrypted store (the `__Auth` table, encrypted
# with the site's encryption_key), keyed on the job. That is the mechanism the
# framework already uses for every other secret it holds, so it inherits the
# same key management and the same backup and restore behaviour.
CRED_DOCTYPE = "Alvoraa Provision Job"

# The three logins a tenant is born with.
CRED_FIELDS = ("admin_password", "hr_password", "user_admin_password")


def _store_credentials(pjob_id, **passwords):
    """Encrypt and store the credentials for one provisioning job."""
    from frappe.utils.password import set_encrypted_password

    for field, pwd in passwords.items():
        if pwd:
            set_encrypted_password(CRED_DOCTYPE, pjob_id, pwd, field)
    frappe.db.commit()


def _read_credentials(pjob_id):
    """Decrypt the credentials for one job. Missing ones come back empty.

    Never raises: a job provisioned before this change, or one whose secrets
    have been cleared, must still be viewable.
    """
    from frappe.utils.password import get_decrypted_password

    out = {}
    for field in CRED_FIELDS:
        try:
            out[field] = get_decrypted_password(
                CRED_DOCTYPE, pjob_id, field, raise_exception=False) or ""
        except Exception:
            out[field] = ""
    return out


def _forget_credentials(pjob_id):
    """Drop every stored secret for a job. Used when provisioning fails.

    A failed run leaves no usable tenant, so its passwords are of no value to
    anyone except an attacker.
    """
    try:
        from frappe.utils.password import delete_all_passwords_for

        delete_all_passwords_for(CRED_DOCTYPE, pjob_id)
        frappe.db.commit()
    except Exception:
        frappe.log_error(title="tenant_api: could not clear job credentials",
                         message=frappe.get_traceback())


def _generate_password(length=18):
    # Alphanumeric only — avoids shell/SQL quoting issues when passed via env vars
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
