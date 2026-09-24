# Slice 042 — Frappe WhatsApp in the core suite, sold as a feature, first on Sargam

Status: **impact analysis and strategy, for the user's approval. No code yet.** (24 Sep 2026)

App: https://github.com/shridarpatil/frappe_whatsapp — MIT licence, 479 stars, maintained
(last push 4 Aug 2026). Meta's WhatsApp Cloud API directly; no third party in between.

## 1. What the app is

| Fact | Detail | Source |
|---|---|---|
| Frappe versions | `frappe >= 14, <= 17.0.0-dev`; master already handles v16 (`frappe.db.after_commit`) | pyproject, utils |
| Branches / tags | `master` (default), `version-15`, `frappe-15-compat`, `multi_acc`. Newest tag **v1.0.11 (25 Nov 2025)**. Master is **62 commits ahead**, and multi-account (WhatsApp Account doctype) exists **only on master**. | GitHub |
| Pin | By commit: **08bc1f6** (4 Aug 2026, master head). No tag carries multi-account. | GitHub |
| Python deps | `python-magic` only; libmagic is already in our image | pyproject; checked in the image |
| Modules | one: `Frappe Whatsapp` | modules.txt |
| Doctypes | 15: WhatsApp Account (token, phone id, business id, app id, verify token), Settings (single: default in/out account), Templates, Message, Notification (+Log), Bulk Message, Recipient (+List), Flow (+Screen, Field), Button, Profiles, Message Fields | repo |
| Roles | Creates none. Every doctype is **System Manager only** — the tenant's own admin configures it | doctype JSON |
| Install hooks | None (no after_install, no setup-wizard hook, no fixtures). Two patches, both about the multi-account migration | hooks.py, patches.txt |
| Assets | `app_include_js` on every desk page → needs `bench build --app frappe_whatsapp` in the image | hooks.py |
| Scheduler | `all` (every few minutes): notifications + scheduled bulk messages; hourly/daily/weekly/monthly variants | hooks.py |
| Public endpoints | `frappe_whatsapp.utils.webhook.webhook` (Meta's webhook, `allow_guest`) and `...api.flow_endpoint.handle_flow_request` (Flows, `allow_guest`, HMAC-signed) | repo |

## 2. Functional impact

- **Cross-module**: none on alvoraa_goals, grace_compensation, hrms or erpnext code. The app hooks
  `doc_events["*"]` on 13 events for *every* doctype — but only to look up whether a WhatsApp
  Notification exists for that doctype/event. With none configured, nothing is sent.
- **Personas**: CXO / HR Manager see nothing unless the tenant has the feature; Employees never see
  it (System Manager doctypes). The tenant admin configures accounts, templates and notifications
  in the desk. Later slices can add "send my payslip / leave approval on WhatsApp".
- **HRMS domain**: no change to leaves, attendance, payroll, appraisals or org structure.
- **Provisioning**: unlike the CRM, no setup-wizard hook, so it can be installed **in
  `provision_tenant.sh` directly when sold**, like india_compliance. Existing tenants get it through
  Edit Tenant → tick → save, the same path the CRM uses.

## 3. Non-functional impact

| Dimension | Effect | Note |
|---|---|---|
| Performance | **Slightly worse on sites where installed**: `get_notifications_map()` runs one `SELECT` on `WhatsApp Notification` on *every* document event (not cached). Small table, ~1 ms — but 13 events × every save. The `all` scheduler job runs every few minutes per installed site. **Neutral** everywhere else: hooks load only for installed apps. | Contained by install-when-sold. An upstream cache is a later contribution, not this slice |
| Security | **New public surface**: the webhook accepts **unsigned** POSTs from anyone (no X-Hub-Signature check; the Flows endpoint does check HMAC) and writes every payload into WhatsApp Notification Log. Forged inbound messages match on `phone_number_id`, which is guessable only if leaked. Token stored as a Password field (encrypted at rest). | Requirements: (SEC-1) nginx rate limit on the webhook path, same style as the device zone; (SEC-2) the endpoint is inert until a WhatsApp Account exists, so on a tenant without one the risk is log spam only; (SEC-3) never put Meta credentials in site_config or docs |
| Reliability | Sends happen after commit (v16-safe). Outbound to graph.facebook.com fails softly into the log. | Meta temporary tokens last 24 h; use a System User permanent token |
| Scalability | Per-tenant accounts; multi-company via multiple accounts. Bulk messaging is rate-limited by Meta, not us. | Fine |
| Maintainability | Pinned by commit, bumped on purpose in one place (Dockerfile ARG), same as CRM_TAG. | Master-only features mean we track master, not releases |
| Data integrity | Own tables only; uninstall drops them (messages, templates). Downgrade = remove the feature, never uninstall. | Same rule as CRM |
| Compliance / privacy | **New PII**: phone numbers and message content of employees/customers, plus conversation logs. DPDP: purpose limitation and retention need a line in the compliance notes before a paying tenant uses it. Meta processes the messages (transfer outside India). | Counsel note before selling; the demo tenant holds fictional data |

## 4. Strategy (for approval)

1. **Image** — `deploy/Dockerfile`: `ARG WHATSAPP_COMMIT=08bc1f6`, `bench get-app` then checkout that commit, add to `apps.txt`, `bench build --production --app frappe_whatsapp`. `build-image.yml` passes the arg. Yarn cache mount as before. Expected image growth: tens of MB.
2. **Feature** — `subscription.py`: `ERPNEXT_FEATURES["whatsapp"]` = label "WhatsApp", `app: "frappe_whatsapp"`, `module_defs: ["Frappe Whatsapp"]`, no roles, no requires, **in no plan bundle** → unselected for every existing tenant, custom when ticked. Same catalogue placement and reason as the CRM.
3. **Provisioning** — `provision_tenant.sh`: `has_feature whatsapp` → `install-app frappe_whatsapp` (no wizard dependency). `tenant_api.update_tenant`: `needs_whatsapp` → install through `_run_install_modules`, the CRM path generalised to "any feature that names an `app`".
4. **Tests** — `tests/test_whatsapp_feature_042.py` mirroring the CRM tests (feature shape, no roles, enterprise invariant holds, provisioning installs only when sold, module unblocked when sold). Full alvoraa_portal suite on the local bench.
5. **nginx** — SEC-1 rate limit on the webhook path, in the same commit (both server blocks; the `nginx -t` gate covers it).
6. **Local proof** — image build; a throwaway site with the app installed; the tests.
7. **Dev** — push on your word. **Trap**: the automatic deploy still runs main's workflow, which lacks the assets/apps.txt refresh (ALV-112), so either a hand deploy from dev again, or main gets the workflow first.
8. **Sargam** — on your word: backup, `install-app frappe_whatsapp`, tick the feature, `sync_site`, then a WhatsApp Account **with credentials you provide** (Meta app: permanent token, phone number ID, business account ID, app ID, a verify token you choose) and the webhook URL `https://sargam.dev.alvoraa.co/api/method/frappe_whatsapp.utils.webhook.webhook` registered in Meta. Without credentials the demo can show templates and notification rules but cannot send. Meta's free test number sends to up to five verified numbers — enough for a demo.

**Out of scope**: patching the app (webhook signature check, notification-map cache) — logged as follow-ups; a priced pack for it; employee-facing WhatsApp features.

**Rollback**: remove the feature from the site (hidden, refused) → uninstall on the demo tenant only → revert the Dockerfile lines only after every site has uninstalled.

**Effort**: about half a day to local proof; the on-server steps minutes each, plus whatever Meta setup takes on your side.
