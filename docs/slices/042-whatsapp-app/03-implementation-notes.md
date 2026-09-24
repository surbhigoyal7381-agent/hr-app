# Slice 042 — implementation notes (local build, 24 Sep 2026)

Branch `slice/042-whatsapp-app` in `.claude/worktrees/042-whatsapp-app`, from `origin/dev`
8718f27. Approved strategy: `00-impact-analysis.md` §4. Ticket ALV-118.

## 1. What changed

| File | Change |
|---|---|
| `deploy/Dockerfile` | `ARG WHATSAPP_COMMIT=08bc1f6af2e3`; `bench get-app --branch master` then `git checkout` of that commit (get-app cannot take a commit; the editable pip install stays valid); `frappe_whatsapp` in `sites/apps.txt` after `crm`; `bench build --production --app frappe_whatsapp` (it has `app_include_js`) |
| `.github/workflows/build-image.yml` | passes `WHATSAPP_COMMIT` |
| `alvoraa_portal/subscription.py` | `ERPNEXT_FEATURES["whatsapp"]`: label "WhatsApp", `app: frappe_whatsapp`, `module_defs: ["Frappe Whatsapp"]`, no roles, no requires, in no plan |
| `deploy/provision_tenant.sh` | `has_feature whatsapp` → `install-app frappe_whatsapp`, inside the block, after the CRM note |
| `alvoraa_portal/tenant_api.py` | `needs_whatsapp` in `update_tenant`; `install_whatsapp` flag on `_run_install_modules`, installed through the same background job, no wizard guard (the app seeds nothing) |
| `deploy/nginx.conf` | zone `alvoraa_webhook` 300 r/m; one location per server block for `frappe_whatsapp.utils.webhook.webhook`, burst 200, 1 MB body, headers repeated (OPS-45) — SEC-1 |
| `tests/test_whatsapp_feature_042.py` | 24 tests, database-free |

Not changed: the app itself (no patches to the webhook or the notification map — follow-ups
in ALV-118), pricing, any HR module.

## 2. Proof

| Check | Result |
|---|---|
| `python -m unittest` 042 + 040 tests, throwaway container | **69 OK** |
| Lockout: image code without the entry → "Frappe Whatsapp" blocked when sold; with the entry → freed | holds |
| `scripts/check_app_integrity.py` | 629 checks, OK |
| `bash -n deploy/provision_tenant.sh` | OK |
| `ruff check` 0.6.9: subscription.py 0, new test 0, tenant_api.py 53 before = 53 after (all pre-existing) | no new findings |
| `nginx -t` on the new config (stand-in certificates) | syntax ok |
| Local image `alvoraa-app:local-042` | builds; **8.38 GB, same as before** (the app is small); yarn cache 12 KB; app pinned at `08bc1f6 (2026-08-04)`; `frappe_whatsapp.js` bundle present; `import frappe_whatsapp, magic` ok |
| Real `install-app frappe_whatsapp` on a fresh site (`testwa042`, Frappe 16.35 / ERPNext 16.36) | installs in under a minute, 15 doctypes, module def `Frappe Whatsapp`; reports 1.0.12 |
| `sync_site` not sold → module blocked (1 row); sold → freed (0 rows), denied doctypes 331 → 322 | holds |
| `get_plan_catalogue` | lists `crm` and `whatsapp` once each |
| Whole `alvoraa_portal` suite on `testwa042` | see §3 |

First local build failed at `materialise_assets.sh` with `set: pipefail: invalid option
name`: the Windows checkout had CRLF in the shell scripts (the committed blobs are LF). Same
trap as slice 040's second attempt. Converted the working copies; the three scripts I did
not otherwise change are NOT staged.

Stale `DocumentLockedError` on the second `sync_site` in the throwaway container: no worker
was running, so the queued save held its lock. Cleared `sites/<site>/locks/*`, started a
worker; not a product fault.

## 3. Whole-suite result

`bench --site testwa042 run-tests --app alvoraa_portal` on the throwaway site built from
`alvoraa-app:local-042` with frappe_whatsapp installed: **1,003 tests, OK, 16 skipped**
(the pre-existing skips), 6,333 s - slow because the same container was also building
seed test sites at the time.

Two earlier runs failed for reasons outside this slice, both recorded: Frappe 16.35's new
user-creation throttle (ALV-119; `throttle_user_limit` must be a number, a quoted value
crashes the comparison on every user insert), and a leftover `features` key from the
access check in section 2. With both removed the suite is clean.

## 4. On-server steps that remain — each on the user's word

1. Push to dev. The automatic deploy runs main's workflow (no ALV-112 refresh), so hand-deploy
   from dev: `gh workflow run Deploy --ref dev -f environment=dev -f image_tag=dev-<sha> -f image_package=alvoraa-app -f run_migrations=true`.
2. Prove: `apps.txt` in the dev volume lists `frappe_whatsapp`; `/assets/frappe_whatsapp/js/frappe_whatsapp.js` is served; nginx gate passed with the new location.
3. Sargam: backup → `install-app frappe_whatsapp` → add `whatsapp` to `features` → `sync_site` →
   WhatsApp Account with **her** Meta credentials (permanent token, phone number ID, business
   account ID, app ID, a verify token she chooses) → register the webhook URL in Meta
   → one template send to a verified test number.
4. Never set credentials in site_config or docs. Never `bench build` on the server.
