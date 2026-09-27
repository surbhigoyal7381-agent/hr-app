---
slice: 043-ai-email-leads
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-09-24
status: analysis only — waiting for the user's approval of the strategy; no code, no branch, no bench run
scope: slice one only (D-7 as amended)
inputs: [CLAUDE.md §2, change-process.md, parallel-work.md, 02-functional-spec.md rev 2, 01c (SEC-1…26, PRIV-1…12), 01-product-brief.md, 01b-ux-design.md incl. the 24 Sep feedback, 07-devops-inputs.md §1–3, subscription.py, module_access.py, hooks.py, field_app_settings.py, delivery_settings.py, the `claude-api` skill (found this time), Frappe 16.35.0 and CRM 1.84.0 source read inside `alvoraa-app:local-042`]
---

# 043 — slice one: impact analysis and build strategy

**Bad news first.**

1. **The local bench cannot run this slice's site tests.** `hrlocal-bench` runs Frappe 16.33.1 with no `crm` app (checked `apps.txt` today). Every test that needs `CRM Lead` or `FCRM Settings` must run in a throwaway container from the image `alvoraa-app:local-042` (Frappe 16.35.0, CRM 1.84.0, Python 3.14.2), the way slice 040 used `hrlocal-040`. That container needs the `anthropic` package installed into its env before the tests run; the image itself has neither `anthropic` nor `httpx` today.
2. **The image must be rebuilt for dev** (new Python dependency). That is the slice-040 build path: ~40 minutes of CI, a whole-image change for every tenant. The dependency is pinned exactly (OPS-5).
3. **The design asks for per-field confidence (01b §12 item 3).** The spec's schema, and `01c`'s SEC-1 as amended, fix eighteen keys and say "nothing else". Adding a confidence per field is a change to SEC-1. I will **not** add it without a decision; the page shows one confidence per lead plus the phone's source phrase, which is what the spec and `01c` agreed. **Decision needed** (open question 4).

## 0 · Start-of-work check (parallel-work §1)

- `git fetch origin`: **nothing incoming** on `origin/dev`. Local `dev` is one commit ahead (`98f0b7f`, user-creation throttle, slice 044 — not mine, unpushed).
- Main checkout holds other sessions' uncommitted work: `mobile/field-app/android/**` (staged and deleted files), `.claude/context/ux-learnings.md`, untracked `docs/sargam_metals/`, `docs/slices/013…step6.md`, `docs/slices/042-whatsapp-app/`, and this slice's own docs. **None of it is in files I would change.** I will not touch it.
- Work board: 045-redesign-wave4 is building in its own container `hrlocal-045` (shared redis + DB with 044: "no other run while mine runs"). Nineteen other worktrees exist; none claims `subscription.py`, `hooks.py`, `Email Account`, `User` hooks or a `crm` area. `slice/042-whatsapp-app` (sibling add-on) sits at `8718f27` = `origin/dev`, so it holds no unmerged code yet — but its `00` plans a `whatsapp` entry in `subscription.py` and a `hooks.py` change. **Overlap plan below.**
- The `claude-api` skill **exists in this session** (the analyst and security engineer could not find it). Its house rules were checked against SEC-1…6; one conflict is recorded in §4.

## 1 · Functional impact

### Cross-module

| App | Touched | How, and the callers I grepped |
|---|---|---|
| `alvoraa_portal` | **Home of all new code.** `subscription.py`: one new `ERPNEXT_FEATURES` entry; one-line fix in `requires_feature` (it reads the label from `FEATURES` only, line 693, so an ERPNext-side feature's refusal would say `crm_ai_intake is not included…` instead of its label — AC-4's exact text needs `feature_spec(name)`). `requires_feature` has **55 callers** (grep, excluding tests); the change alters only the message text for ERPNext-side keys, never the decision. `ERPNEXT_FEATURES` is read by `pricing.py`, `module_access.py` (`sync_site`) and four test modules; a new entry with no `app` and no `module_defs` changes nothing for them (`sync_site` blocks only module defs an entry names). `hooks.py`: three `doc_events` entries added at the end, one cron line, one daily-long line, one `after_migrate`/`after_install` line each. | 
| `crm` (v1.84.0, sold as `crm`, on Sargam dev only) | Target, **read and extended, never edited.** Custom fields on `CRM Lead` and `FCRM Settings`; one `CRM Lead Status`; a section appended to the tenant's `CRM Fields Layout` "CRM Lead-Side Panel" record (§3). Its `Communication.after_insert → crm.utils.on_communication_insert → create_lead_from_incoming_email` (`crm/utils/__init__.py` 195–235, 256) stays; V-1 refuses the flag on intake mailboxes so it never fires there. Its row rules (`crm.permissions.org_hierarchy`, hooks 135–145) apply unchanged because the queue reads through `frappe.get_list`. |
| `frappe` | Read-only use of `Email Account` (pull, `imap_folder.append_to`, `default_incoming`), `Communication`, `User Email`, `Notification Log`, `Version`. Custom field + `validate` hook on `Email Account`; `validate` hook on `User`. **Never** `frappe.email.receive`, never `get_password` (SEC-13). |
| `erpnext` | No. Reuses roles Sales User / Sales Manager as the CRM does. |
| `hrms`, `alvoraa_goals`, `alvox_compensation` | **No.** |

**HRMS domain impact: none.** Leaves, attendance, payroll, appraisals, goals, compensation, org structure are untouched. The only HR-shaped code is a refusal: an HR-looking mailbox or an HR-role user's mailbox can never be ticked (SEC-8, V-5/V-6).

### Personas

| Persona | What changes |
|---|---|
| Tenant admin (System Manager) | New "AI lead intake" section on FCRM Settings (statement, accept, reviewer, thresholds, ignore list, today's count, turn-off with reason); one tick on Email Account that is refused for unsafe mailboxes; can read the content-free call log. |
| Sales Manager / named reviewer | New desk page `/app/ai-lead-review`; "Needs review" leads; accept / edit-then-accept / reject. |
| Sales User | AI-created leads appear with columns filled and an "AI intake" block on the CRM lead page; can decide only leads assigned to them (01b C4, taken). |
| CXO without a Sales role | **Nothing.** Tested (AC-39–41). |
| HR Manager, Employee | **Nothing, and must not.** Tested (AC-39–41), plus the `User Email` rule (V-6, AC-71–72). |

## 2 · Non-functional impact (seven dimensions)

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **neutral** for every existing screen; the new sweep is bounded: one `get_all` for candidates (indexed on `email_account`, `reference_doctype`, `creation`), then ≤ 12 queries per email (asserted in a test), at most 25 emails a run, one model call in flight per site. Page and list endpoints page at 20. |
| Security | **improves** the CRM's own email intake (the bare-lead hook creates a lead for every stranger today); **adds** a new surface: one outbound call to `api.anthropic.com`, six whitelisted endpoints, all role-checked and `@requires_feature`, no `allow_guest`. `ignore_permissions` used in exactly three places (log insert, Communication reference update, lead insert as the service user) — each commented and counted by a test. |
| Reliability | **degrades slightly by design**: a new external dependency. Contained by 30 s timeout, 3 bounded retries, breaker, idempotency row, a defined end state for every path (§4), and the non-AI fallback (bare "Needs review" after 24 h). Nothing in it can block the request thread or the mail pull. |
| Scalability | **neutral** for HR volume; for mail volume the shared `default,short` worker is the limit (OPS-2/6): a 200-email burst is ~33 min serial. The cap (500/day ceiling, 200 tenant) and the 25-per-run bound keep any one tenant from starving the worker for more than ~4 minutes per sweep. Slice two's backfill goes to `long`. |
| Maintainability | **neutral**: one package `alvoraa_portal/ai_leads/` with small pure modules (skip rules, validators, redaction, prompt, client) that test without a site; the pipeline is the only module that touches the database. No new abstraction beyond that. |
| Data integrity | **improves** where it touches existing data: SEC-7 (never overwrite an existing lead), one transaction per email, idempotency row before the call, `Communication` remains the single truth for the email. Stale-data risk: settings read with `cache=False`; the breaker is a TTL cache key (loss = one early retry, harmless); the daily count is a locked database row (cache loss cannot reset it). |
| Compliance / privacy | **degrades the privacy surface knowingly** (prospect email text leaves the tenant to a US provider, ≤ 30 days) — that is the product decision D-1/D-2, gated by PRIV-1's recorded acceptance and the three switches; **improves** auditability (content-free call log, provenance on the lead, breach query runnable in one group-by). Nothing widens who can see a lead. Logs carry document names only. |

## 3 · The Fields-layout verdict (settled from code)

**Yes — Frappe CRM 1.84 renders custom fields on its Vue lead page, on one condition: the field names must be in the tenant's `CRM Fields Layout` record for `CRM Lead` / `Side Panel`.**

- `crm/crm/fcrm/doctype/crm_fields_layout/crm_fields_layout.py`, `get_sidepanel_sections` (lines 113–147): loads the record `{dt: "CRM Lead", type: "Side Panel"}`, takes `frappe.get_meta(doctype).fields` — which includes Custom Fields — keeps only the fieldnames the layout JSON lists, runs `handle_perm_level_restrictions` (150–159: a permlevel the user cannot read → `hidden`) and `get_field_obj` (177–189: `read_only` → tooltip "This field is read only").
- `crm/frontend/src/pages/Lead.vue` line 486 calls that endpoint and line 197 renders `<SidePanelLayout>`.
- `crm/frontend/src/components/SidePanelLayout.vue` lines 80–105: any `read_only` field whose type is not numeric/Check is drawn as plain text; `Percent` at 235 and `Check` at 116 draw disabled; `Select` 138, `Link` 185, `Datetime` 211, `Small Text` 121–135 all have branches. Lines 609–627 hide an **empty** read-only field (`hide_empty_read_only_fields`, default on) — so a human-made lead shows no AI block at all, which is what we want.
- The CRM writes the default layout at install (`crm/crm/install.py` 196–199) and only rewrites it with `force`. It is **tenant data**, editable by an admin in the CRM's layout editor.

So: our switch-on step appends a section `{"label": "AI intake — filled by an AI model; check before you rely on it", "columns": [{"fields": [alvoraa_ai_intake_state, alvoraa_ai_confidence, alvoraa_ai_reasons, alvoraa_ai_reviewed_by, alvoraa_ai_reviewed_on, alvoraa_ai_source_account, alvoraa_ai_model, alvoraa_ai_prompt_version]}]}` to that record if absent (safe to run twice; a test pins it). The PRIV-8 sentence is the **section label**, which always renders; no HTML field needed. "Open the AI record" for Sales Manager only: `alvoraa_ai_model` and `alvoraa_ai_prompt_version` at `permlevel 1` with a Sales Manager / System Manager read row — `handle_perm_level_restrictions` hides them from a Sales User. The list columns the WOW moment needs: `crm/api/doc.py` `get_fields` (639–650) also reads `get_meta`, so the two fields are choosable as columns (inferred from code, not run). **Design note stays as drawn; the lead-page block does not move to the desk.** Residual risk: an admin who edits the layout can drop the section; the accept endpoint re-asserts it, and the desk form of the lead still shows the fields.

## 4 · Strategy

### 4.1 Feature gating — a new opt-in entry, not part of `crm`

`ERPNEXT_FEATURES["crm_ai_intake"] = {label: "AI lead intake (email)", requires: ["crm"], opt_in: True, erpnext: True}` — no `app`, no `module_defs`, no roles, in no plan bundle. Why not fold it into `crm`: it is separately priced (brief OQ-9), it introduces a sub-processor and a recorded transfer acceptance, and folding it in would switch a US model provider on for every CRM tenant at the next restart. Verified in code that `opt_in` and `requires` work for `ERPNEXT_FEATURES` entries: `feature_spec` (475) covers both registries, `is_opt_in` (461), `plan_features` (536) and `enabled_features` (551–567) go through it, `unmet_requirements` (478) too. Closes the spec's `[ASSUMPTION]`. The desk page lives in module "Alvoraa Portal", which every tenant has; the page's own role list plus `@requires_feature` on every endpoint are the gate.

### 4.2 Where the settings live — custom fields, not a new Single

Custom fields on `FCRM Settings` (tenant-wide) and `Email Account` (per mailbox), prefix `alvoraa_ai_`, exactly as `field_app_settings.py` did on HR Settings (slice 013): the Single already gives System Manager write / Sales Manager write / Sales User read and Version rows; a new Single would need its own permissions, its own history and a second place to look. The API key, platform switch, ceiling, model id and log retention are `frappe.conf` keys, read the way `delivery_settings.py` reads them (fail closed: missing switch = off; missing ceiling = 500; missing model id = refuse to call).

### 4.3 Files and records

| Path | Mechanism | What |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/ai_leads/__init__.py`, `settings.py` | extend | field constants; installers (`after_migrate`, guarded by `"crm" in frappe.get_installed_apps()` for CRM-side fields; Email Account field always); `validate_fcrm_settings` (AC-1, 5, 47, 48, 53, 55; thresholds floor 70; limit ≤ ceiling), `accept_ai_transfer_statement` (AC-54); statement text v1 keyed to the model id (PRIV-3) |
| `ai_leads/eligibility.py` | build | V-1…V-7 as pure functions; `validate_email_account`, `validate_user` (mirror rule); the sweep re-checks at run time (AC-67) |
| `ai_leads/skip_rules.py`, `redact.py`, `validators.py` | build | SEC-9 headers/keywords EN+HI, bounce, calendar, empty; SEC-5 pre-send `[ID REMOVED]` + output-side drop; SEC-4 per-field rules, phone span check, industry/territory resolved against existing rows only |
| `ai_leads/prompt.py` + `prompt_v1.txt` | build | template with the SEC-2 guard sentence verbatim; `PROMPT_VERSION` = SHA-256 of the file; the 18-key JSON schema, `additionalProperties: false`; masked sender; ≤ 6,000 chars of `text_content` after quote stripping |
| `ai_leads/model_client.py` | build | §4.4 |
| `ai_leads/pipeline.py` | build | the 5-minute sweep (§4.5) and the daily stale rule (SEC-26) |
| `ai_leads/review_api.py` | build | `list_review_queue`, `get_review_item`, `decide_review_item(lead, action, note)`, `accept_ai_transfer_statement`, `ai_usage_today` — the spec's names (01b's `accept_intake_lead`/`reject_intake_lead` map onto `decide_review_item`); each `@requires_feature("crm_ai_intake")` above `@frappe.whitelist()`, Guest refused, role checked, reads via `frappe.get_list` |
| `ai_leads/notify.py`, `log.py` | build | `enqueue_create_notification(users, doc, dedupe_on=[...])` (Frappe 16.35 signature verified) — counts and links only; log rows; daily purge on `long` with a receipt row |
| `alvoraa_portal/alvoraa_portal/alvoraa_portal/doctype/alvoraa_ai_call_log/` | build (new DocType) | SEC-17 fields; `communication` Link **unique** (the idempotency key); `attempts` Int; `ids_redacted` Int; perms: System Manager read only; no write/delete for anyone; list view without free text (OPS-8) |
| `.../doctype/alvoraa_ai_usage_day/` | build (new DocType, tiny) | one row per site-day: `day`, `calls`, `stale_leads`; taken with `frappe.db.get_value(..., for_update=True)` (verified `database.py` 527) — the same shape as slice 013's `Alvoraa Field App Daily Count`. SEC-19 asks for a locked DB row, so a cache counter is out |
| `.../alvoraa_portal/page/ai_lead_review/` | build (Frappe Page) | `ai_lead_review.json` (roles System Manager, Sales Manager, Sales User), `.js`, `.html`, `.css` as 01b draws; Frappe loads page JS from the file at runtime (`core/doctype/page/page.py` 143–159) — **no `bench build`** |
| Records at switch-on (idempotent) | configure | `CRM Lead Status` "Needs review" (Open, amber); `CRM Lead Source` "Email" if missing; role `Alvoraa AI Intake` (create on CRM Lead, write on Communication); service user `ai-leads@<site>` (System User, enabled, no password, `send_welcome_email=0`, only that role — cannot log in; the pipeline wraps the insert in `frappe.set_user(...)`/restore so `owner` is honest — OQ-14); the side-panel section (§3) |
| `hooks.py` | extend (hot file, append-only) | `doc_events`: `FCRM Settings.validate`, `Email Account.validate`, `User.validate`; `scheduler_events.cron["*/5 * * * *"]` → `pipeline.enqueue_sweep`; `daily_long` → `log.purge`; `after_migrate`/`after_install` → `settings.after_migrate` |
| `subscription.py` | extend (hot file, add-only) | the entry; `requires_feature` label via `feature_spec` — one line, one new test |
| `setup.py` `install_requires` + `requirements.txt` | configure | `anthropic==<exact 1.x>` `[verify latest at build]`; the Dockerfile's `pip install -e apps/alvoraa_portal` (line 80) picks it up |
| `scripts/check_no_api_keys.py` + one `ci.yml` lint line | build | SEC-22; same shape as `check_no_demo_passwords.py`; `--self-test`. **`ci.yml` is outside a feature slice by the hot-file rule — asking (open question 1).** gitleaks 8.30.1 already runs on new commits (ci.yml 195–219) and has a generic key rule, but SEC-22 wants a repo-wide, self-testing check |

### 4.4 The model call

- **Model:** `claude-haiku-4-5` — D-2's "cheapest hosted class". From the skill's table (cached 2026-06-24): $1 / $5 per MTok, 200K context, structured outputs supported. ≈ 1,500 in + 250 out ≈ $0.0028 ≈ **₹0.23** at ₹84/$ `[verify prices and rate]`. It is **not a Covered Model**, so zero-data-retention is possible if signed (Q-4); the statement text is keyed to the id. **Conflict with the skill:** its house rule is "always `claude-opus-5` unless the user names another" — D-2 is the user naming one; recorded here so nobody "corrects" it. The id lives in site config against a code allowlist `{id → retention statement}`, so switching to Sonnet after the 200-email measurement is a config change plus one allowlist line.
- **Request:** `anthropic.Anthropic(api_key=frappe.conf.get("alvoraa_ai_api_key"), timeout=30.0, max_retries=0)` built **inside** the call function (SEC-14; the skill's own client init shape). `messages.create(model, max_tokens=600, temperature=0, system=<template>, messages=[{"role":"user","content":<delimited email block>}], output_config={"format": {"type": "json_schema", "schema": SCHEMA}})`. No `thinking` (Haiku takes `budget_tokens`; extraction needs none). No `tools`, no `tool_choice`. **No prompt caching in slice one:** Haiku 4.5's minimum cacheable prefix is 4,096 tokens (skill `prompt-caching.md` line 138) and our system prompt is ~1.2K, so a marker would silently do nothing; the PRIV-10 test still asserts no `cache_control` on the user turn.
- **Response:** first `text` block → `json.loads` → schema check (extras rejected, SEC-6) → validators. Usage from `response.usage.input_tokens / output_tokens`, model from `response.model`, request id from the SDK's response request-id attribute `[verify name in 1.x]`.
- **Errors, most specific first:** `AuthenticationError`, `PermissionDeniedError` → breaker open now, ops alert, no retry. `RateLimitError`, `InternalServerError`, `APIConnectionError`, `APITimeoutError` → our own backoff (2 s, 4 s, 8 s + jitter, 3 tries, ≤ 20 s total so the job stays inside its budget); then `error:provider`. `BadRequestError` → `error:request`, no retry, alert (a schema/parameter fault is ours). Five consecutive provider errors → cache key `alvoraa_ai_breaker` TTL 30 min. Every `except` logs a fixed class and the Communication name — never `get_traceback()` of the block that holds the body (SEC-15).

### 4.5 The sweep, in order

1. Cron every 5 min enqueues `sweep` on `default`, `job_name="alvoraa_ai_sweep|<site>"` de-duplicated via `get_jobs` (Frappe's own pull pattern, `email_account.py` 1019–1028), `timeout=300`. **I disagree with OPS-2's 60 s**: the job is one sweep of up to 25 emails, not one email; 60 s would cut it after six. DevOps to comment in §4.
2. Three switches (`frappe.conf.alvoraa_ai_enabled`, `has_feature`, FCRM `alvoraa_ai_enabled` with `cache=False`); any off → return `"disabled:<which>"`, no rows (AC-51).
3. Take today's `Alvoraa AI Usage Day` row `for_update` (creates it if absent). This serialises sweeps per site (AC-24, AC-65).
4. Candidates: received `Communication` rows on ticked accounts, no reference, no call-log row, oldest first, limit 25. Re-check SEC-8 per account; ineligible → `skipped:ineligible_account` + one notice.
5. Per email: **insert the log row first** (`result="in_progress"`, unique `communication`; an `IntegrityError` means another run has it — skip). Skip rules → finalise `skipped:<rule>`. Cap reached → finalise `skipped:cap`, stop calling this run (the row is deleted so the email stays "waiting"). Otherwise redact, build, call. Validate, cap confidence, match by sender email then validated phone, then create / fill-empty / attach-only (SEC-7), link the Communication, set the lead as `ai-leads@<site>`, finalise the row — **one commit per email**; on any exception `rollback`, then write `error:<class>` and commit.
6. `in_progress` rows older than 10 minutes (a killed worker) → `attempts += 1` and retried; after 3, `error:interrupted` and the stale rule takes over. That is the defined end state OPS-4 asked for.
7. Stale rule (SEC-26): emails waiting > 24 h → bare "Needs review" lead, ≤ 200/day from the same locked row.

### 4.6 Rollout, rollback, effort

- **Local:** throwaway container `hrlocal-043` from `alvoraa-app:local-042` with its own site and `pip install anthropic==<pin>` in its env; stub provider (fixed JSON, no network); whole `alvoraa_portal` suite there. `hrlocal-bench` untouched.
- **Dev:** push on the user's word → image rebuild → `bench migrate` (custom fields, two doctypes, page). Then, each for the user to run: `set-config alvoraa_ai_api_key` (typed by her, OPS-10), `alvoraa_ai_enabled true`, `alvoraa_ai_model_id`, add `crm_ai_intake` to Sargam's `features`, `sync_site`; the demo mailbox entered in the Email Account form (D-6); switch on in FCRM Settings; forced runs at ceiling 3 and a forced 429 with the log rows shown (01c §8).
- **Rollback:** FCRM switch off (seconds, tenant) or `alvoraa_ai_enabled false` (platform) stop every call with no deploy — the real rollback (OPS-15). Image rollback is for code defects only; fields, doctypes and the page are inert with the feature absent.
- **Effort (my estimate):** settings + refusals + acceptance 2 d · pipeline, client, validators, redaction, skip rules 3 d · call log, counter, breaker, stale rule 1.5 d · review page + endpoints 2.5 d · installers, fixtures, service user, side-panel section 1 d · tests (§5) 2.5 d · CI gate, notes, review fixes 1 d → **~13.5 engineer-days ≈ 3 weeks**, in line with `07`'s 31 points. Slice one alone, demo mailbox only.

## 5 · How the tests prove the ACs

**Database-free (plain `unittest`, run under `bench run-tests` too, no CRM needed):** `test_ai_leads_registry_043` (AC-49, 50; `requires_feature` label); `test_ai_leads_prompt_043` (AC-43, 44, 56 body shape, 60; the guard sentence; 18 keys, no `tools`, no top-level client — SEC-14); `test_ai_leads_skip_rules_043` (AC-12–14, 61); `test_ai_leads_validators_043` (AC-9–11, 59; SEC-4 table); `test_ai_leads_redact_043` (AC-58; pre-send count); `test_ai_leads_eligibility_043` (AC-68, 69 deny-list edges); `test_ai_leads_source_hygiene_043` (AC-78 greps; AST list of whitelisted functions vs the role table — AC-20's second half; `ignore_permissions` count = 3); `test_check_no_api_keys_043` (AC-74).

**Site tests (`FrappeTestCase`, throwaway container with CRM):** `test_ai_leads_settings_043` (AC-1–5, 47, 48, 53–55); `test_ai_leads_mailbox_refusals_043` (AC-2, 3, 67–73, the `User` mirror); `test_ai_leads_pipeline_043` (AC-6–8, 15–17, 21, 23–25, 42, 62 with the stub); `test_ai_leads_resilience_043` (AC-26–31, 63–65, SEC-26's five cases, two threads on ceiling 1); `test_ai_leads_log_043` (AC-35–38); `test_ai_leads_permissions_043` (AC-20, 36, 39–41 via `/api/resource`); `test_ai_leads_notifications_043` (AC-45, 46); `test_ai_leads_no_leak_043` (AC-64 / SEC-23: marker key and body through 401, 429, 500, timeout, bad JSON; scan Error Log, logger, log rows); `test_ai_leads_layout_043` (the side-panel section, the "Needs review" status, the service user — pins §3).

**Fail-without-fix tests (the pin tests):** delete the `crm_ai_intake` entry → registry test fails; remove the guard sentence → prompt test fails; drop the unique index on `communication` → the two-thread test creates two leads; remove `frappe.set_user` → `owner` test fails; take the section out of the layout installer → layout test fails; put `frappe.get_traceback()` back in the client → the no-leak test fails (AC-75).

**Live (optional, key present, never on a fork PR):** AC-44b injection corpus, marked `skipIf(not key)`.

## 6 · Parallel-work check

| File | Hot? | Who else | Plan |
|---|---|---|---|
| `subscription.py` | yes | 042-whatsapp-app plans a `whatsapp` entry (no commits yet) | **Split**: each adds its own entry at the end of `ERPNEXT_FEATURES`; my `requires_feature` line is a separate commit that says so |
| `hooks.py` | yes | 042 plans hook lines; 045 does not touch it | **Split / append-only**: my entries at the end of each list with a comment; on conflict keep both |
| `setup.py`, `requirements.txt` | no | 042 may add a dependency too | Append; rebase before the push |
| `.github/workflows/ci.yml` | outside a slice | — | **Ask** (open question 1) |
| Everything else | new files under `ai_leads/`, two doctype folders, one page folder, `docs/slices/043-ai-email-leads/` | nobody | — |

Worktree `.claude/worktrees/043-ai-email-leads` on `slice/043-ai-email-leads` from `origin/dev`, created **after** approval; board row added then. Bench: my own container only.

## 7 · Risks and trade-offs

| # | Risk | What I do about it |
|---|---|---|
| 1 | **The CRM lead-page block depends on a per-tenant layout record** an admin can edit | Re-asserted at switch-on; pinned by a test; the desk form is the fallback; residual risk stated in the notes |
| 2 | **First sync bursts the one shared worker** (`bench worker --queue default,short`, compose 272): a mailbox with 250 old mails queues 250 sweeps' worth behind the mail pull | 25 per run, ceiling, and OPS-16's rule: never switch on during a deploy or month-end. Slice two moves backfill to `long` |
| 3 | **The key sits in `site_config.json`, therefore in every backup tarball** (deploy.yml 304–329, OPS-9) | Out of my hands in code; one workspace key per tenant so a leak revokes one; written into the notes and the release checklist |
| 4 | **Anthropic SDK 1.x is `httpx2`-based and the image runs Python 3.14** — a pin that does not resolve breaks the whole image build | Resolve the pin in the throwaway container first; `[verify]` before the push |
| 5 | The `User Email` scoping rule is the only thing keeping intake mail out of an Employee's `Communication` list (`communication.py` 508–528) | V-6 + the mirror rule on `User` + AC-40 run against `/api/resource` with an Employee session |
| 6 | Frappe's `text_content` for HTML-only mail can be empty; a stripped `content` may leak quoted history | E-9: strip tags locally, `EmailReplyParser`, cut at 6,000; AC-56 captures the body |
| 7 | Per-field confidence (01b) vs 18 fixed keys (SEC-1) | Not built; decision below |
| 8 | Two doctypes instead of one (the counter row) | Cheapest correct lock; the repo already has the same shape; no report reads it |

## Open questions (before I build)

1. May this slice add `scripts/check_no_api_keys.py` **and one line to `ci.yml`** (SEC-22), given the hot-file rule that workflows are not part of a feature slice? Recommended: yes, as its own commit.
2. Job budget: one sweep job, `timeout=300`, ≤ 25 emails — or OPS-2's 60 s per job (which would mean one job per email)? Recommended: 300/25; DevOps §4 to confirm.
3. `requires_feature` one-line label fix in `subscription.py` — in this slice, or leave AC-4's wording to my own `frappe.throw` in the validate? Recommended: fix it; it affects `crm` today too.
4. Per-field confidence and source phrase for every field (01b §12 item 3): not in SEC-1's eighteen keys. Build to the spec (one confidence + phone span) — yes/no? Recommended: spec as written for slice one; measure on the 200 emails first.
5. Model id for the first run: `claude-haiku-4-5` per D-2, with `claude-sonnet-5` as the allowlisted alternative? Recommended: yes.

## Assumptions

- `[ASSUMPTION]` The demo mailbox is IMAP with `enable_incoming`, not `default_incoming`, no `append_to` (else V-2/V-4 refuse it — by design).
- `[ASSUMPTION]` `anthropic` 1.x installs on Python 3.14 in the image; `[verify]` in the throwaway container first.
- `[ASSUMPTION]` Prices and the ₹/$ rate as marked `[verify]`; the rate table in code carries a dated comment.
- `[ASSUMPTION]` The ops alert channel is an `Error Log` row with a fixed title (what `check_workers.sh`/`worker-health.yml` can grep), as `01c` and `07` assumed.

**Stopping here for the user's approval of the strategy. No file outside this document has been changed.**


## Amendment, 24 Sep 2026 — no screens in slice one

The user cut slice one to the pipeline (see the spec's "Scope change" section). For the
strategy above this means: drop the desk Page `/app/ai-lead-review`, the CRM Fields Layout
section, the acceptance flow and the settings form; keep the Email Account custom Check
and validate rules, the site-config keys for the switch and the cap, the sweep job, the
model call, the call log, the `alvoraa_ai_*` custom fields on CRM Lead, a "Needs Review"
CRM Lead Status and a saved list filter. Effort about 6 engineer-days. The risk about the
per-tenant layout record disappears with the screen; the other two stand.


## Correction after review, 24 Sep 2026

The reviewer found this analysis claims more than slice one's code does. For the record: there
is **no circuit breaker** yet (a sweep has a 240-second limit and per-email isolation, not a
breaker); the sweep runs on the shared default queue and **can** delay the mail pull by up to
the time limit; there is **no** query-count test and **no** test that counts `ignore_permissions`
uses; the call log **is** content-free after the review fix. The breaker and alerts move to
slice two (ALV-122).
