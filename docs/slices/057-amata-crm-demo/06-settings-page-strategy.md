# Slice 057 - Settings page for CRM intake and the founders' summary

Written 2 Oct 2026. Impact analysis and strategy only. No code written, nothing edited, no containers started.
Status: waiting for Surbhi's approval (step 3 of the change process).

## 1. What she asked for

A page in the desk, so she does not need `bench` for: (1) AI email intake on/off + mailbox; (2) WhatsApp intake on/off + forwarder list (number -> user); (3) founders' summary recipients + template; (4) switching any of them off. Plus, if cheap, the summary send time as a saved field.

## 2. Ladder: which rung, and why not a cheaper one

| Rung | Verdict |
|---|---|
| Already there | No. Email Account has a tick for the mailbox, but the master switch, forwarders and summary live only in site config. |
| Configuration (HR Settings custom fields, as field app settings do) | Rejected. HR Settings is for HR rules. This is CRM, and it needs a table (forwarders). A table on HR Settings is a clumsy fit. |
| New code only (a whitelisted API + no storage) | Rejected. Needs somewhere to keep the values. |
| **One new Single DocType + one child table** | **Chosen.** Smallest thing that holds a list and gives a form, a save button, a Version history and permissions for free. |
| Several DocTypes, a custom page, a Vue screen | Rejected. Nothing she asked for needs them. |

**DocType: `Alvoraa CRM Intake Settings`** (Single, `track_changes`), plus child `Alvoraa CRM Forwarder` (Phone number, User). Same pattern as the existing Single `Alvoraa Pricing Settings` / `Alvoraa Leader View Settings`.

Fields:
- Email: `email_intake` (Check), `mailbox` (Link Email Account), `daily_cap` (Int, default 200, ceiling 500 stays in code), `lead_owner` (Link User, optional; today `ai_lead_intake_owner`).
- WhatsApp: `whatsapp_intake` (Check), `forwarders` (table).
- Summary: `summary_on` (Check), `summary_whatsapp` (Small Text, one number per line), `summary_email` (Small Text, one address per line), `summary_template` (Data), `summary_hour` (Int 0-23, default 9).
- Read-only status lines, filled on load: "AI key set: yes/no", "Meta app secret set: yes/no", "Feature ticked: yes/no". These answer Part 10 of the guide without a server.

No separate "enabled" master tick: the old site-config `ai_lead_intake_enabled` was one shared flag. It becomes "email on OR WhatsApp on". Each switch means exactly what its label says.

## 3. What happens on Save (the old `switch_on` / `switch_on_whatsapp` logic, moved)

`validate` + `on_update` call the existing helpers in `ai_leads/setup.py` (`ensure_fields`, `ensure_status`, `ensure_view`, `ensure_service_user`, the mailbox rules in `guards.problems`, the "WhatsApp" lead source). They already run twice safely. Changes to `setup.py`: `switch_on`, `switch_on_whatsapp`, `switch_off` and every `update_site_config` call are deleted; the helpers stay. Refusals reuse today's messages (mailbox breaks a rule, number without country code, user disabled). Switching a tick off just saves; the next sweep sees it. Turning email off also clears the mailbox's intake tick (so the sweep skips it) - that is the old `switch_off` made precise.

## 4. Secrets: what stays server-only

| Secret | Where | Why |
|---|---|---|
| AI API key (`ai_lead_intake_api_key`) and model name | **Stay in site config, set by us.** | It is Alvoraa's key, shared across tenants and billed to us (her 043 decision). A tenant admin typing it into a form is a leak and a cost risk. The page only shows "set / not set". |
| Meta app secret | **Stay on the WhatsApp Account form**, in the existing `alvoraa_app_secret` Password field. | Yes, that is the right home. It is per Meta app, sits next to that account's token and verify token, is stored encrypted, and the signature check already reads it there. Moving it to the settings page would give two homes for Meta values. The page only shows "set / not set". |
| Gmail app password | Stays on the Email Account form. | Unchanged. |

Nothing secret is ever read into the settings doc, so it can never appear in its Version history.

## 5. Who can open it

**System Manager only.** Reason: the page decides what third-party text leaves for the AI provider and who receives pipeline numbers outside the CRM. That is an owner/admin decision, not a sales one. Sales Manager can be added later by adding one permission row (an easy change). Her call. Server side, the doc's own permissions enforce it; no whitelisted endpoint is added, so there is no new open door.

**Gating by `crm_ai_intake`:** the form opens on any tenant that has the app. `validate` refuses to save either AI tick unless `has_feature("crm_ai_intake")` (same message as today) and CRM / frappe_whatsapp are installed. The summary tick needs CRM only (as today). Runtime code still checks `has_feature` on every path, so a tenant that loses the feature stops at once even if the tick stays.

## 6. Reading the values at run time (no shims)

`intake.enabled()`, `daily_cap()`, `whatsapp.forwarders()`, the service-user and owner reads, and `crm_summary.send_daily` read the Single through `frappe.get_cached_doc`. Frappe clears that cache on save, so a change is live on the next request. **They no longer read `frappe.conf` for these values - no fallback.** The `conf=` test parameters become a settings object/dict. Left in site config on purpose: API key, model, `ai_lead_intake_ignore`, research flags (not asked for).

Cost: one cached read per sweep or message. The sweep runs every 5 minutes and the mailbox pull every minute; both stay "return before any query" on an off site (the cached doc read is memory, not a query once warm).

## 7. Summary send time (her open decision 1) - cheap, so included

Replace cron `0 9 * * *` in hooks.py with `0 * * * *`. `send_daily` returns unless `summary_on` and the current site hour equals `summary_hour`. The cron fires once per hour, so it sends once a day with no "last sent" field. The hook text never changes, so a deploy no longer resets the time. Cost: 24 tiny runs a day that exit immediately. Caveat: the scheduler ticks every 3-4 minutes, so a run lands in the right hour but not on the exact minute (fine for "about 9"). A "Send now" button is left out: the Scheduled Job Type Execute route already exists (guide Part 8.3).

## 8. Migration - how sargam.dev's email intake keeps working

One patch in `patches.txt` (runs on `bench migrate` before `after_migrate`):
- If site config has `ai_lead_intake_enabled`: set `email_intake` = on, `mailbox` = the Email Account whose intake tick is set, copy `ai_lead_intake_daily_cap`, `ai_lead_intake_owner`.
- If it has `ai_lead_whatsapp_forwarders`: set `whatsapp_intake` = on and copy each pair to the table.
- If it has `crm_founder_summary`: copy whatsapp, email, template; `summary_on` = on; hour 9.
- Sites with none of these: the patch does nothing. Writes the Single directly with `ignore_permissions`; idempotent (skips if the doc already has `modified` set by a person).
- The old keys are left in the file, unread. Removing them needs a check of `update_site_config`'s delete support in the installed Frappe; I have not verified that, so I will not promise it.

**What I could not check:** I did not look at what dev, sargam.dev or Amata currently hold in site config (no server or container access in this task). Before the deploy I will read each tenant's `show-config` keys (not the key's value) so we know the patch will find something to copy. A site that had intake on but whose patch did not run would stop silently. Hence the check, and a test (below).

## 9. Where she finds it

Desk URL: `/app/alvoraa-crm-intake-settings` (Single, so it opens straight to the form). Search bar: "Alvoraa CRM Intake Settings". The existing `Alvoraa CRM Step Task` has no workspace link either (found by search), so I add **no** workspace shortcut: that would touch the shared workspace fixtures, a hot file. If she wants a link on the CRM or Alvoraa desk workspace, say so (~0.5 h and a clash check).

## 10. Impact, by persona and module

- CXO / HR Manager: no change. Sales Manager: nothing to see (System Manager only). System Manager: the page replaces five server commands.
- Modules: only `alvoraa_portal` (ai_leads, crm_summary, hooks, patches). No change to grace/alvoraa_goals/compensation, hrms, erpnext, crm or frappe_whatsapp. Callers of the changed functions (grepped): `intake.py` lines 62, 84, 108, 331, 387, 421; `research.py` 251, 257; `whatsapp.py` 47, 49, 76, 91, 132; 16 test references to the three old config keys.
- Parallel work: another engineer is editing `ai_leads/whatsapp.py` and the step-task code (review M1/M2) and running the full suite **right now**. This slice edits `whatsapp.py`, `intake.py` and `hooks.py`. **Wait until M1/M2 land and the suite is green, then rebase**; do not start before. `hooks.py` and `patches.txt` are hot files: add one line each, nothing else.

## 11. Seven dimensions

| Dimension | Verdict | Note |
|---|---|---|
| Performance | neutral | One cached doc read; summary cron 24 exits a day. |
| Security | improves | Server-side perms; nothing secret on the page; no new endpoint. Risk: a wrong forwarder list sends third parties' text to AI; hence System Manager only and Version history. |
| Reliability | improves, one risk | Bench typos gone. Risk: the migrate patch missing a tenant (see section 8). Cron minute drift noted. |
| Scalability | neutral | Per-site doc. |
| Maintainability | improves | Two config homes become one; three `setup` entry points deleted. |
| Data integrity | neutral | Cache clears on save; the doc is the only source. |
| Compliance / privacy | improves | Every change has who/when/before/after (Version). Forwarder numbers are personal data: shown only to System Manager, never logged. |

Other NFRs: errors say what to do (reuse today's); every label and message wrapped for translation; fields have labels and help text; form works on a phone (standard desk form).

## 12. Tests (each named to the feature)

1. Saving with email on + a good mailbox ticks the mailbox and `intake.enabled()` is true; saving off stops the sweep with no model call.
2. Mailbox that breaks a rule (HR, default) is refused with the reason.
3. Bad number (no country code) and disabled user refused.
4. WhatsApp: listed number is processed, unlisted ignored, off = ignored; reads the doc, not site config (put a value in `frappe.conf` and prove it is ignored).
5. Saving an AI tick without `crm_ai_intake` is refused; summary tick works without it.
6. Non-System-Manager (Sales Manager, Sales User) cannot read or write the doc.
7. Summary: only sends in `summary_hour`; recipients parsed one per line; blank = off.
8. Patch: site-config values land in the doc; run twice, same result; empty site does nothing.
9. Pin test that fails if the cron entry or the permission row is dropped in a merge.
10. Existing 043/057 tests moved from `conf=` to the new reads; whole suite once at the end.

## 13. Effort and Monday

| Part | Hours |
|---|---|
| DocType + child + permissions + status lines | 1.5 |
| Save logic from `setup.py`, delete bench entry points | 1.5 |
| Switch readers in intake/research/whatsapp/summary | 1.5 |
| Summary hour + cron change | 0.5 |
| Migration patch | 1 |
| Tests (new + convert 16 references) | 2.5 |
| Guide rewrite (Parts 5, 7, 8, 9) + review fixes + subtract pass | 1.5 |
| **Total** | **about 10 h** |

**Fits before Monday's demo?** Technically yes, if it starts only after M1/M2 land and the suite is green, and the whole slice goes through local, review and dev with no surprises. It is tight and it touches the code the demo depends on (intake and WhatsApp readers). **My recommendation: do not ship it before Monday.** Run the demo with the bench commands, which are proven, and build this right after. The one cheap exception worth doing now is nothing: even the send-time field needs the same reader change. Her call.

## 14. Decisions for Surbhi

1. Approve this approach (one Single DocType + one child table)?
2. System Manager only, or also Sales Manager?
3. Before Monday or after? (I recommend after.)
4. Daily at a chosen hour (this design), or weekly? Still open from section 8 of `03`.
5. Do you want a workspace link, knowing it touches a shared file?

## 15. Subtract pass

Removed while writing: a master "enabled" tick (two ticks say it better); a config fallback and a shim (migration patch instead); a "Send now" button (Scheduled Job Type has it); the API key and app secret as form fields; a workspace shortcut; a "last sent" date field; a child table for summary recipients (a line-per-entry text box is enough for a handful of founders); a separate per-forwarder "enabled" tick (delete the row).
