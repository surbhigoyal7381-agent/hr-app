# Kinexus HRMS — Deployment Architecture

**Audience:** DevOps / Platform Engineering
**Goal:** Deploy this application to the cloud for the first time — on any provider — with CI/CD and three environments.

> ## Start here: this application has never been deployed
>
> It runs on developer laptops via Docker Compose. There is **no production server, no staging, no CI/CD, no tenants, and no data to migrate.** This is a greenfield deployment.
>
> That is good news: there is nothing to preserve, no cutover to plan, and no legacy to work around. The earlier Oracle-specific deploy scripts have been **deleted** from this repo because they were never used and would have misled you (they are recoverable from git history if ever needed).
>
> Everything in this document describes what to **build**, not what to fix.

---

## 1. What this application is

Kinexus HRMS is a **multi-tenant HR, performance-management and vendor/logistics platform** built on the [Frappe Framework](https://frappeframework.com). It is not a standalone web app — it is a set of Frappe *apps* installed into a Frappe *bench*, and it inherits Frappe's entire runtime model: process layout, database conventions, background workers, asset pipeline, and site-per-tenant isolation.

**If you have not deployed Frappe before, read §4 before sizing anything.** Its process model is the single most important thing to get right and it is not a typical 12-factor app.

### Functional surface

| Area | Delivered by | Notes |
|---|---|---|
| Core HR — employee, leave, attendance, onboarding, payroll | `hrms` | Frappe HR fork with Grace Group customisations |
| Performance management — appraisals, calibration, check-ins, upward feedback, talent flags | `hrms/hrms/pms` + `hrms/hrms/performance_management` | 37 doctypes. **Never run before** — see §11 |
| Cascaded goals & KPIs with evidence-based progress | `alvoraa_goals` | 21 doctypes, row-level scoping, hourly recalculation |
| Vendor portal, order tracking, delivery/driver management | `alvoraa_portal` | 22 doctypes, scheduled scorecards |
| Appraisal/KPI APIs and branded tenant portals | `alvoraa_portal` | `performance_api.py` (157 KB), server-rendered pages under `www/` |
| Tenant provisioning control plane | `alvoraa_portal/tenant_api.py` | Creates Frappe sites via background jobs; System Manager only |
| Employee PWA + Roster SPA | `hrms/frontend`, `hrms/roster` | Vue 3 + frappe-ui, built at image-build time |

---

## 2. Technology stack

| Layer | Technology | Version | Where pinned |
|---|---|---|---|
| Framework | Frappe Framework | `>=17.0.0-dev,<18.0.0` | `hrms/pyproject.toml` |
| ERP base | ERPNext | `>=17.0.0-dev,<18.0.0` | same |
| Language | Python | `>=3.10` | `hrms/pyproject.toml` |
| Asset build | Node.js 20 + Yarn | — | `hrms/package.json` |
| Database | MariaDB 10.6+ (10.8 recommended) | utf8mb4 / utf8mb4_unicode_ci | §5.1 |
| Cache / queue / pub-sub | Redis 6+ | — | §5.2 |
| WSGI | gunicorn | bundled | `deploy/Dockerfile` |
| Realtime | Node Socket.IO | bundled | port 9000 |
| Job queue | python-rq on Redis | bundled | queues: `short`, `default`, `long` |
| Reverse proxy | Nginx 1.2x | — | `deploy/nginx.conf` |
| PDF rendering | wkhtmltopdf 0.12.x (patched Qt) | required for payslips | in base image |

**No third-party runtime services.** The custom apps declare only `frappe` as a dependency and make no calls to S3, SMS, push, or LLM APIs. Email goes through Frappe's built-in Email Account doctype, configured per tenant **in the database** — not via environment variables. The only mandatory egress is your SMTP relay; package registries are needed at build time only.

---

## 3. Repository layout

Single mono-repo, ~2,020 tracked files, 67 MB.

```
hr-app/
├── hrms/                       # Frappe HR fork (1,755 files)
│   ├── hrms/                   #   hr, payroll, pms, performance_management, grace_group
│   ├── frontend/               #   Vue 3 employee PWA
│   ├── roster/                 #   Vue 3 roster SPA
│   ├── frappe-ui/              #   ⚠️ GIT SUBMODULE → github.com/frappe/frappe-ui
│   └── docker/                 #   local dev stack (keep — this is what developers use)
├── alvoraa_goals/                # custom app — goals, KPIs, appraisal extensions
├── alvoraa_portal/        # custom app — vendor, delivery, portals, tenant API
├── deploy/                     # ← everything needed to deploy
│   ├── Dockerfile              #   the application image
│   ├── compose/                #   test/prod stack
│   ├── envs/                   #   per-environment variable templates
│   ├── nginx.conf              #   multi-tenant reverse proxy
│   └── provision_tenant.sh     #   creates a new tenant site
└── .github/workflows/          # CI/CD
```

⚠️ **`hrms/frappe-ui` is a git submodule.** Every clone — CI, image build, local — must use `--recurse-submodules` or the PWA build fails.

⚠️ **`hrms/` is a fork committed into this repo, not a submodule.** Any build that runs `bench get-app hrms` fetches *upstream* Frappe HR and silently discards every customisation here. `deploy/Dockerfile` copies it from the repo instead. Do not "simplify" this back to `get-app`.

---

## 4. Runtime process model — read before sizing

A Frappe bench is **five distinct process types**. In a correct deployment they are separate containers running the *same image* with different commands.

| Process | Command | Port | Scaling | Notes |
|---|---|---|---|---|
| **web** | `gunicorn … frappe.app:application` | 8000 | Horizontal | `(2 × cores) + 1` workers, ~250–400 MB RSS each |
| **socketio** | `node apps/frappe/socketio.js` | 9000 | Horizontal | needs sticky sessions or a Redis adapter |
| **scheduler** | `bench schedule` | — | **EXACTLY ONE, cluster-wide** | see below |
| **worker** | `bench worker --queue …` | — | Horizontal, per queue | |
| **nginx** | — | 80/443 | Horizontal, or replaced by the cloud LB | |

All web, socketio and worker processes need **read/write access to the same `sites/` directory** (§5.3).

### 🔴 The scheduler is a singleton

`bench schedule` enqueues every cron-driven job. Two schedulers **double-fire every job**:

| Frequency | Jobs | Consequence of double-firing |
|---|---|---|
| every ~4 min | `update_delivery_tracking` | duplicate tracking rows |
| hourly | `recalculate_all_progress`, `calculate_driver_ratings` | double-counted KPI progress |
| daily | `send_progress_reminders`, `send_arrival_notifications`, `check_compliance_alerts`, `check_cascade_alignment` | **duplicate emails to real employees and vendors** |
| monthly | `generate_monthly_scorecards` | duplicate scorecards |

Plus all stock Frappe/ERPNext/HRMS jobs (backups, email queue, leave accrual, salary slips).

**Enforcement:** Kubernetes `Deployment` with `replicas: 1` and `strategy.type: Recreate`, or ECS `desiredCount: 1` with `maximumPercent: 100`. **Never place the scheduler in an autoscaling group.**

`recalculate_all_progress` iterates every goal across every tenant — its cost grows linearly with tenant count. Budget one `long`-queue worker per ~20 tenants and monitor queue depth.

---

## 5. Data architecture

### 5.1 MariaDB

**One database per site (per tenant).** 50 tenants = 50 databases on one instance, each with its own DB user.

Mandatory server settings — Frappe will fail to install or corrupt data without them:

```ini
character-set-server            = utf8mb4
collation-server                = utf8mb4_unicode_ci
skip-character-set-client-handshake
skip-innodb-read-only-compressed     # required on MariaDB 10.6+
innodb_file_per_table           = 1
max_connections                 = 500
```

#### Managed-database caveat

`bench new-site` connects **as a DB root-level user** to `CREATE DATABASE`, `CREATE USER` and `GRANT`. Managed services do not give you real `root`:

| Service | Verdict | Notes |
|---|---|---|
| **AWS RDS for MariaDB** | ✅ Recommended on AWS | Master user lacks `SUPER` but has `CREATE USER` + `GRANT OPTION`. Settings go in a **custom Parameter Group** — they cannot be set at runtime. |
| **Azure Database for MySQL Flexible Server** | ⚠️ | MariaDB flavour is retired. MySQL 8 compatibility with Frappe v17 is unvalidated here. |
| **GCP Cloud SQL / OCI MySQL HeatWave** | ⚠️ | MySQL only, same caveat. |
| **Self-hosted MariaDB 10.8** | ✅ Fully tested path | You own backups, failover, patching. |

**Recommendation:** RDS MariaDB on AWS; self-hosted MariaDB 10.8 (VM or StatefulSet) anywhere else.

### 5.2 Redis — three roles, two instances

Frappe uses Redis for three things. The eviction policy differs, so run **two** instances:

| Role | Policy | Persistence | If wrong |
|---|---|---|---|
| Cache | `allkeys-lru` | none | — |
| **Queue (RQ)** | **`noeviction`** | **AOF required** | Silent loss of queued jobs: notifications, tenant provisioning, scorecards |
| SocketIO pub/sub | `allkeys-lru` | none | — |

Cache + socketio can share one instance. The queue gets its own with `noeviction` and persistence.

### 5.3 Filesystem — the stateful part

```
frappe-bench/sites/
├── common_site_config.json          # DB host, redis hosts        ← SECRET
├── assets/                          # built JS/CSS — baked into the image
├── kinexus_provision_jobs.json      # tenant provisioning state    ← flat file, see §19
└── <tenant>.kinexus.in/
    ├── site_config.json             # encryption_key, db creds     ← SECRET + CRITICAL
    ├── public/files/                # photos, documents
    ├── private/files/               # payslips, contracts, IDs     ← PII
    └── private/backups/
```

#### 🔴 `site_config.json` holds the `encryption_key`

Frappe encrypts stored passwords (email accounts, API keys) with a **per-site** key that lives in this file, not in the database. **A database restore without the matching `site_config.json` produces a site whose stored secrets cannot be decrypted.** Always back them up together.

#### Shared storage

A file uploaded by a request on web replica A must be readable by a PDF job on worker C.

| Option | How | Trade-off |
|---|---|---|
| **Shared network filesystem** (recommended) | EFS / Azure Files / Filestore / OCI File Storage mounted at `…/frappe-bench/sites` | Zero code change. NFS latency hurts `assets/` — which is why assets are baked into the image. |
| **Single node + block volume** | EBS / managed disk | Fine for `dev` and `test`. No horizontal scaling or HA. |
| S3-backed attachments | `frappe-s3-attachment` | Reduces NFS bulk but `site_config.json` still needs local storage. Extra app to vet. |

---

## 6. Multi-tenancy

**One Frappe site = one tenant = one database = one `sites/<host>/` directory.**

```
Browser → https://acme.kinexus.in
   │  DNS: *.kinexus.in → LB
   ▼
[ Load balancer ]  ── MUST preserve the Host header
   ▼
[ Frappe web ]  reads Host → sites/acme.kinexus.in/site_config.json → that tenant's DB
```

**Requirements this places on your ingress — all four are mandatory:**

1. **The `Host` header must survive end-to-end.** An LB that rewrites it breaks tenant resolution for *every* tenant at once. This is the #1 cause of failed first Frappe deployments.
2. **Wildcard DNS** `*.kinexus.in → LB`.
3. **Wildcard TLS** `*.kinexus.in` + apex. Requires **DNS-01** validation — HTTP-01 cannot issue wildcards.
4. **`X-Forwarded-Proto: https`** set and trusted, or every generated URL comes out as `http://`.

**Tenant lifecycle:** `deploy/provision_tenant.sh <subdomain> "Name" <plan>` creates the site and installs `erpnext → hrms → alvoraa_portal → alvoraa_goals` (order matters — `alvoraa_goals` requires `hrms`, `alvoraa_portal` requires `erpnext`).

Plans map to a `modules_enabled` list: `starter` = HR only; `business` adds vendor portal + goals; **`enterprise` enables everything**.

> Provisioning is **not idempotent**, takes 3–10 minutes, runs as an RQ `long` job, and shells out to `bench` — so it needs a writable bench and elevated DB credentials. Run it on a dedicated worker with that credential rather than granting it to the whole web tier (§17).

---

## 7. Network & ports

| From | To | Port | Notes |
|---|---|---|---|
| Internet | LB | 80, 443 | 80 → 301 → 443 |
| LB | web | 8000 | health: `GET /api/method/ping` → `{"message":"pong"}` |
| LB | socketio | 9000 | path `/socket.io`, WS upgrade headers, idle timeout ≥ 120 s |
| app | MariaDB | 3306 | private subnet |
| app | Redis | 6379 | private subnet |
| worker | SMTP relay | 587 | outbound only |
| build agents | ghcr.io, PyPI, npm, github.com | 443 | build-time only |

**Body size** `50m` — document uploads; match this on the cloud LB.
**Timeout** ≥ 120 s — payroll runs and bulk appraisal operations are slow synchronous requests. A lower LB idle timeout produces spurious 504s.

---

## 8. Sizing

| Environment | Web | Worker | Scheduler | SocketIO | DB | Redis |
|---|---|---|---|---|---|---|
| **dev** | 1 × (2 vCPU / 4 GB), all-in-one | shared | shared | shared | container, 20 GB | container |
| **test** | 1 × (2 vCPU / 4 GB) | 1 × (2 vCPU / 4 GB) | 1 × (0.5 / 1 GB) | 1 × (0.5 / 1 GB) | 2 vCPU / 8 GB, 50 GB | 1 GB |
| **prod, ≤25 tenants** | 2 × (2 vCPU / 4 GB) | 2 × (2 vCPU / 4 GB) | **1** × (0.5 / 1 GB) | 2 × (0.5 / 1 GB) | 4 vCPU / 16 GB, 200 GB, Multi-AZ | 2 × 2 GB |
| **prod, ≤100 tenants** | 4 × (4 vCPU / 8 GB) | 4 × (4 vCPU / 8 GB) + 1 dedicated `long` | **1** | 2 | 8 vCPU / 32 GB, 500 GB + replica | 2 × 4 GB |

**Architecture:** build multi-arch (`linux/amd64,linux/arm64`) so the target cloud stays an open choice. Arm instances (Graviton, Ampere, Oracle A1) are materially cheaper for this workload.

**Cold start:** a bench built from scratch takes 25–35 minutes. This is why everything is baked into an image — a pre-built image starts in seconds.

---

## 9. Cloud service mapping

| Need | AWS | Azure | GCP | OCI | Self-hosted |
|---|---|---|---|---|---|
| Containers | ECS Fargate / EKS | Container Apps / AKS | GKE¹ | OKE | Compose / k3s |
| Database | **RDS MariaDB** | MySQL Flexible² | Cloud SQL² | MySQL HeatWave² | MariaDB 10.8 |
| Redis cache | ElastiCache | Azure Cache | Memorystore | OCI Cache | Redis 7 |
| Redis queue (`noeviction` + AOF) | ElastiCache, separate | separate | separate | separate | Redis 7 |
| Shared files | EFS | Azure Files (NFS) | Filestore | File Storage | NFS |
| Ingress + wildcard TLS | ALB + ACM | App Gateway + Key Vault | GCLB + managed cert | LB + cert | Nginx + cert-manager |
| Registry | ECR | ACR | Artifact Registry | OCIR | GHCR / Harbor |
| Secrets | Secrets Manager | Key Vault | Secret Manager | Vault | SOPS + age |
| Backups | S3 + Glacier lifecycle | Blob cool tier | GCS Nearline | Object Storage | MinIO |
| Logs / metrics | CloudWatch | Monitor | Cloud Logging | Logging | Loki + Prometheus |

¹ Cloud Run is a poor fit for the scheduler and workers (no always-on singleton, request-scoped CPU).
² Not MariaDB — validate Frappe v17 against MySQL 8 first, or self-host.

**Recommendation:** target **Kubernetes** — the workload maps to five Deployments + one RWX PVC + one Ingress, and the same manifests run everywhere. If that is too heavy for the team, **Docker Compose on 1–3 VMs with managed DB and Redis** keeps most of the portability at a fraction of the operational cost. The shipped `deploy/compose/` stack is the Compose path.

---

## 10. Target architecture

```
                          ┌──────────────────────────┐
   *.kinexus.in ─DNS──▶   │  Cloud LB  (wildcard TLS) │
                          └────────────┬─────────────┘
                     ┌─────────────────┼─────────────────┐
                     ▼                 ▼                 ▼
              ┌────────────┐    ┌────────────┐    ┌─────────────┐
              │  web × N   │    │socketio × 2│    │ nginx        │
              │  gunicorn  │    │   :9000    │    │ (or cloud LB)│
              │   :8000    │    └─────┬──────┘    └─────────────┘
              └─────┬──────┘          │
      ┌─────────────┼─────────────────┼──────────────┐
      ▼             ▼                 ▼              ▼
┌──────────┐  ┌──────────┐    ┌──────────────┐  ┌──────────────┐
│worker × N│  │scheduler │    │ Redis queue  │  │ Redis cache  │
│    RQ    │  │  × 1 🔴  │    │ noeviction   │  │ allkeys-lru  │
└────┬─────┘  └────┬─────┘    │ + AOF        │  └──────────────┘
     └──────┬──────┘          └──────────────┘
            ▼
   ┌──────────────────┐        ┌────────────────────────────┐
   │  MariaDB         │        │  Shared RWX volume          │
   │  Multi-AZ        │        │  …/frappe-bench/sites       │
   │  1 DB per tenant │        │  (EFS / Azure Files / …)    │
   └────────┬─────────┘        └────────────────────────────┘
            │                  ┌────────────────────────────┐
            └── nightly ─────▶ │ Object storage (cross-region)│
                               └────────────────────────────┘
```

### The image

**One image, five roles.** Built by [`deploy/Dockerfile`](deploy/Dockerfile) from the repo root:

```dockerfile
FROM frappe/bench:latest
RUN bench init --frappe-branch ${FRAPPE_BRANCH} frappe-bench
RUN bench get-app --branch ${ERPNEXT_BRANCH} erpnext

# All three first-party apps copied from THIS commit — never re-downloaded
COPY --chown=frappe:frappe hrms                 apps/hrms
COPY --chown=frappe:frappe alvoraa_goals          apps/alvoraa_goals
COPY --chown=frappe:frappe alvoraa_portal  apps/alvoraa_portal

RUN ./env/bin/pip install -e apps/hrms -e apps/alvoraa_goals -e apps/alvoraa_portal \
 && bench build --production          # bakes sites/assets + PWA + roster
```

| Role | Command |
|---|---|
| web | `gunicorn --bind 0.0.0.0:8000 --workers 4 --threads 2 --worker-class gthread --timeout 120 frappe.app:application` |
| socketio | `node apps/frappe/socketio.js` |
| scheduler | `bench schedule` — **1 replica** |
| worker | `bench worker --queue default,short` |
| worker | `bench worker --queue long` |

Configuration is injected at container start by the `configurator` service in [`deploy/compose/docker-compose.app.yml`](deploy/compose/docker-compose.app.yml) — never baked in.

---

## 11. 🔴 Everything is enabled — including a module that has never run

Per the product decision, **all modules ship enabled in production**, and tenants are provisioned on the `enterprise` plan.

That includes `hrms/hrms/pms` + `hrms/hrms/performance_management`: **37 doctypes and 137 files that have never executed against any database.** Verified: the current local container has no `pms/` directory and `SELECT COUNT(*) FROM tabDocType WHERE name LIKE 'PMS%'` returns `0`. Until now, `bench get-app hrms` downloaded stock Frappe HR and this code was never loaded. `deploy/Dockerfile` changes that.

**What this means for you:**

- The first `bench install-app hrms` **creates 37 new tables** and activates untested permission handlers, document hooks and web routes (`/pms-employee`, `/pms-manager`, `/pms-calibration`, `/pms-steering`).
- CI covers this: [`ci.yml`](.github/workflows/ci.yml) installs `hrms` on a fresh site and asserts the Performance Management doctypes are created. **If that job fails, the module has a defect — do not deploy past it.**
- Deploy to `dev`, then `test`, and exercise the PMS screens **before** the first `main` deploy. This is exactly what the three environments are for.
- Note there are effectively **two performance systems**: the live one built on `Appraisal` + `KPI` + `Individual Goal` (in `alvoraa_portal/performance_api.py`), and this PMS module. They are independent. Enabling both is the stated intent — just be aware users will see two routes to similar functionality.

---

## 12. Environments and branches

Three long-lived branches, one per environment. **Deployment is driven by the branch**, so promoting code means merging it forward.

```
feature/*  ──PR──▶  dev  ──PR──▶  test  ──PR──▶  main
                     │             │              │
                     ▼             ▼              ▼
                    dev           test        PRODUCTION
                  (auto)        (auto)      (approval required)
```

| | **dev** | **test** | **production** |
|---|---|---|---|
| **Branch** | `dev` | `test` | `main` |
| **Deploys** | automatically on push | automatically on push | **manual approval** |
| **Purpose** | integration of feature work | UAT, migration rehearsal, PMS validation | live tenants |
| **Domain** | `*.dev.kinexus.in` | `*.test.kinexus.in` | `*.kinexus.in` |
| **Image tag** | `dev-<sha>` | `test-<sha>` | `prod-<sha>` |
| **Env file** | `deploy/envs/dev.env` | `deploy/envs/test.env` | `deploy/envs/production.env` |
| **Database** | container or small managed | managed, single-AZ | managed, Multi-AZ + replica |
| **Redis** | 1 instance | 1 instance | 2 (cache / queue) |
| **Files** | local volume | single volume | shared RWX |
| **`developer_mode`** | `1` | `0` | `0` |
| **Tenants** | 1 synthetic | 2–3 synthetic | real |
| **Plan** | `enterprise` | `enterprise` | `enterprise` |
| **TLS** | Let's Encrypt | Let's Encrypt | wildcard + HSTS |
| **Outbound email** | 🔴 `MUTE_EMAILS=1` | 🔴 mail-catcher (Mailpit) | real SMTP relay |
| **Backups** | none | daily, 7-day | pre-deploy + daily, 35-day, cross-region |
| **Approval** | none | none | **required reviewer** |

### 🔴 Two non-negotiable environment rules

1. **`MUTE_EMAILS=1` in dev and test.** This app sends progress reminders, arrival notifications and compliance alerts on a daily scheduler tick. A non-prod environment holding a copy of real data **will email real employees and vendors within hours**. Set this before the first data load, not after.
2. **`test` mirrors production *topology*, not scale.** Same process split, same managed services, smaller instances. A staging environment running a different process model does not de-risk anything.

### Branch protection

| Branch | Rules |
|---|---|
| `dev` | PR required; status checks `lint`, `test-python`, `test-frontend` |
| `test` | PR required; same checks; **only merges from `dev`** |
| `main` | PR required; same checks; **only merges from `test`**; ≥1 approving review; no force-push; linear history |

---

## 13. CI/CD

Three workflows in `.github/workflows/`:

| Workflow | Trigger | Does |
|---|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | PR into or push to `dev`/`test`/`main` | ruff, semgrep, `bench run-tests` for both grace apps against real MariaDB + Redis service containers, PMS doctype creation check, PWA + roster builds. **Never deploys.** |
| [`build-image.yml`](.github/workflows/build-image.yml) | push to `dev`/`test`/`main` | multi-arch build → GHCR as `<env>-<sha>`, then Trivy scan → Security tab |
| [`deploy.yml`](.github/workflows/deploy.yml) | after a successful build, per branch | pre-deploy backup, maintenance mode, `bench --site all migrate`, health wait, smoke test, rollback instructions on failure |

**CI runtime note:** a cold `bench init` is 15–25 minutes. `ci.yml` caches the bench keyed on `pyproject.toml` + the requirements files, so steady-state runs are far shorter. Do not remove that cache without accepting the cost — CI being slow is the usual reason teams stop running it.

### Required GitHub configuration — do this before the first push

**Environments** (Settings → Environments): create `dev`, `test`, `production`.

| Environment | Protection rules |
|---|---|
| `dev` | none |
| `test` | none |
| `production` | **Required reviewers ≥ 1**; deployment branch rule: `main` only |

**Secrets, per environment:**

| Secret | Notes |
|---|---|
| `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` | Compose host. For Kubernetes, use `KUBE_CONFIG` and swap the SSH steps |
| `BACKUP_BUCKET` | object storage for offsite backups (test + production) |

**Variables, per environment:** `BASE_DOMAIN`, `SMOKE_SITE` (e.g. `demo.kinexus.in`).

Application secrets (`DB_ROOT_PASSWORD`, `ADMIN_PASSWORD`, SMTP) belong in the **cloud secret store** and are rendered into `deploy/envs/<env>.env` on the host — not held in GitHub. Templates: `deploy/envs/*.env.example`.

> ⚠️ `.github/` has never been committed. **The first `git push` of these workflows activates all of them at once.** Create the Environments, secrets and variables above *first*, or the first push triggers a deploy against nothing and fails loudly.

### Migration and release

`bench migrate` runs **per site** and is not transactional across the fleet:

```bash
bench --site all set-maintenance-mode on
bench --site all backup --with-files        # the rollback point
bench --site all migrate                    # ~30-120 s per site, serialised
bench --site all clear-cache
bench --site all set-maintenance-mode off
```

- A schema-changing release needs a **maintenance window proportional to tenant count** (100 tenants × 60 s ≈ 100 min). Batch across workers, or accept staggered per-tenant migration if the release is backward-compatible.
- **Rolling restarts are safe only for code-only releases.** Gate on whether `patches.txt` changed.
- **Always rehearse migrations in `test` first.** That is the environment's main job.

### Rollback

| Situation | Action | RTO |
|---|---|---|
| Bad code, no migration | Actions → Deploy → Run workflow → previous `image_tag`, `run_migrations: false` | < 2 min |
| Migration already ran | Redeploy previous tag **and** restore the pre-deploy backup per site. Frappe patches are not reversible. | 10–30 min/site |
| Migration failed mid-fleet | Sites are independent — restore only the failed ones | per-site |

Keep the last 5 image tags; never garbage-collect the tag currently on production.

---

## 14. First deployment — recommended order

| # | Step |
|---|---|
| 1 | Choose cloud + orchestrator (§9) and provision: VPC, private subnets, MariaDB, 2 × Redis, shared file storage, registry, secret store |
| 2 | Create the GitHub Environments, secrets and variables (§13) |
| 3 | Create the `dev` and `test` branches from `main` and set branch protection (§12) |
| 4 | Commit `.github/` and push to `dev` → first CI run and first image build |
| 5 | Stand up the **dev** environment; run `provision_tenant.sh demo "Demo" enterprise`; verify login and portals |
| 6 | **Exercise the PMS module in dev** (§11). Fix anything broken before promoting |
| 7 | Merge `dev` → `test`; stand up **test** with prod-like topology; run UAT and a migration rehearsal |
| 8 | Wildcard DNS + wildcard TLS for `*.kinexus.in`; verify the Host header survives the LB (§6) |
| 9 | Set up backups to object storage — and **perform a restore drill** before go-live (§17) |
| 10 | Merge `test` → `main`; approve the production deploy; provision real tenants |
| 11 | Add monitoring, log shipping and alerting (§16) |
| 12 | Restrict DB root to the provisioning worker; move all secrets to the cloud secret store (§15) |

Steps 1–10 are the minimum before real payroll data goes through this system.

---

## 15. Secrets

| Secret | Where it lives | Notes |
|---|---|---|
| `DB_ROOT_PASSWORD` | cloud secret store → provisioning worker only | Creates databases and users. **Do not give it to the web tier.** The app tier should hold a least-privilege user with DML on existing site DBs |
| `ADMIN_PASSWORD` | secret store | rotate after first login |
| Per-site `encryption_key` | `sites/<site>/site_config.json` | Frappe requires it there. Back up **encrypted**, never log it |
| Per-site DB password | same file | same |
| SMTP credentials | Frappe `Email Account` doctype, encrypted at rest | per tenant |
| `DEPLOY_SSH_KEY` | GitHub environment secret | prefer OIDC → cloud IAM role instead of a long-lived key |

`deploy/envs/*.env` is gitignored; only `*.env.example` is committed. Never log `site_config.json` — it appears in `bench` debug output, so scrub it in the log pipeline.

---

## 16. Observability

| Check | Endpoint / method | Healthy |
|---|---|---|
| Web liveness | `GET /api/method/ping` | `200 {"message":"pong"}` |
| SocketIO | `GET /socket.io/?EIO=4&transport=polling` | `200` |
| Scheduler | Scheduled Job Log freshness, or `bench --site <s> doctor` | last run < 2× interval |
| Workers | Redis `LLEN rq:queue:default` | < 100 and not growing |

Ship `web.log`, `worker.log`, `worker.error.log`, `scheduler.log`, `frappe.log` and Nginx logs. In containers, log to stdout and let the platform collect.

**Alerts specific to this application:**

- `long` queue depth growing → `recalculate_all_progress` is falling behind; tenant count has outgrown worker capacity
- A scheduled job has not fired in 2× its interval → **the scheduler singleton is dead**
- MariaDB connections > 80 % of `max_connections` → the classic multi-tenant Frappe failure
- Nginx 429s from the `kinexus_login` zone (5/min/IP) → credential stuffing, *or* a legitimate office behind one NAT being throttled. Consider raising it or keying on `$http_x_forwarded_for`
- `sites/` volume > 75 % → `private/backups/` accumulating

---

## 17. Backup & DR

**Targets:** RPO ≤ 1 hour, RTO ≤ 4 hours.

**A database dump alone is not a restorable backup.** Capture all five:

1. `<site>-database.sql.gz`
2. `<site>-files.tar`
3. `<site>-private-files.tar` (payslips, contracts — PII)
4. **`site_config.json`** — the `encryption_key`
5. `common_site_config.json`

`bench --site all backup --with-files` produces 1–3; the deploy workflow tars 4–5 separately.

| What | Frequency | Retention | Where |
|---|---|---|---|
| Managed DB snapshot / PITR | continuous | 35 days | provider, cross-region |
| `bench backup --with-files` | daily 02:00 UTC + pre-deploy | 30 days | object storage, cross-region, versioned, SSE |
| Config bundle | on change | 90 days | encrypted bucket / secret store |

**Restore drill — run before go-live, then quarterly, into `test`:**

```bash
bench new-site <site> --mariadb-root-password "$DB_ROOT" --admin-password "$ADMIN" --no-mariadb-socket
bench --site <site> restore <db>.sql.gz \
      --with-public-files <files>.tar --with-private-files <private>.tar \
      --mariadb-root-password "$DB_ROOT"
cp <backup>/site_config.json sites/<site>/site_config.json   # restores encryption_key
bench --site <site> set-config mute_emails 1                 # BEFORE the scheduler ticks
bench --site <site> migrate
```

Tenants are independent, so recovery can be prioritised per tenant by SLA. Agree that order with the business in advance.

---

## 18. Security

Already implemented in [`deploy/nginx.conf`](deploy/nginx.conf): `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, login rate limiting (5/min/IP), API rate limiting (120/min/IP), 50 MB body cap.

| Control | Action |
|---|---|
| TLS | Wildcard cert, TLS 1.2+, HSTS `max-age=31536000; includeSubDomains`, 80→443 |
| Network | DB and Redis in private subnets; security groups allow the app tier only |
| DB least privilege | App tier DML-only; root confined to provisioning |
| `developer_mode` | `0` in test and production |
| `server_script_enabled` | `0` — Server Scripts are arbitrary Python execution from the UI |
| Image scanning | Trivy in `build-image.yml`; escalate HIGH/CRITICAL to blocking once the baseline is clean |
| SAST | semgrep rules in `hrms/semgrep/`, wired into `ci.yml` |
| Dependency scanning | Dependabot for `pyproject.toml`, `package.json`, base image |
| **Tenant isolation** | `test_permissions.py` in both grace apps is **blocking in CI**. Row-level scoping (`permission_query_conditions`) is the only thing stopping employees reading each other's goals, KPIs and appraisals |
| Audit logging | Frappe Activity Log + LB access logs → SIEM |

**Data protection:** this system holds salary data, payslips, ID documents, appraisal ratings and upward feedback — likely GDPR / DPDP scope. Note that Frappe's `encryption_key` protects *stored credentials*, **not** employee PII columns, which are plaintext in the database. Encryption at rest (DB, object storage, file volume) is therefore required, not optional.

---

## 19. Open decisions

| # | Decision | Recommendation |
|---|---|---|
| 1 | Cloud + orchestrator | Kubernetes for portability; Compose on VMs if the team is small |
| 2 | MariaDB managed vs self-hosted | RDS MariaDB on AWS; self-hosted MariaDB 10.8 elsewhere |
| 3 | **Frappe version** | The repo tracks `17.0.0-dev`. **Running a pre-release framework in production is a real risk.** Decide: pin to the last stable release, or accept develop-branch churn. Then replace `FRAPPE_BRANCH=develop` with a commit SHA in `deploy/Dockerfile` and `ci.yml` |
| 4 | Expected tenant count at 12 months | Drives DB sizing, worker count, and migration window tolerance |
| 5 | Migration window | Determines whether schema releases can happen in business hours |
| 6 | `kinexus_provision_jobs.json` | A flat file. Convert to a doctype before scaling the web tier past one replica, or pin the control-plane endpoints to a single replica |
| 7 | CPU architecture | Multi-arch is built either way; pick instance families to match |

---

## Appendix — quick reference

```bash
# Local development (unchanged)
cd hrms/docker && docker compose up -d
docker compose logs -f frappe          # first run ~25-35 min
# → http://hrms.localhost

# Build the image locally
docker buildx build --platform linux/arm64 -f deploy/Dockerfile -t kinexus:local .

# Bring up an environment
cd deploy/compose
echo "KINEXUS_IMAGE=ghcr.io/<org>/hr-app:dev-abc1234" > .image.env
docker compose -f docker-compose.app.yml --env-file ../envs/dev.env --env-file .image.env up -d

# Provision a tenant with everything enabled
docker compose -f docker-compose.app.yml exec backend \
  bash /workspace/provision_tenant.sh acme "Acme Corp" enterprise

# Migrate every tenant
docker compose -f docker-compose.app.yml exec backend bench --site all migrate

# Health
curl -H "Host: acme.kinexus.in" https://kinexus.in/api/method/ping
```

| Path | Role |
|---|---|
| `deploy/Dockerfile` | Application image — all five apps, assets baked |
| `deploy/compose/docker-compose.app.yml` | test/prod stack, split process roles |
| `deploy/envs/{dev,test,production}.env.example` | Per-environment variable templates |
| `deploy/nginx.conf` | Multi-tenant reverse proxy |
| `deploy/provision_tenant.sh` | Creates a tenant site and installs all apps |
| `hrms/docker/` | Local development stack |
| `.github/workflows/{ci,build-image,deploy}.yml` | CI/CD |
