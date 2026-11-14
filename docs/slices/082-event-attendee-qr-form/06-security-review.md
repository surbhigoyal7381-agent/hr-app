---
slice: 082-event-attendee-qr-form
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-11-14
code: worktree .claude/worktrees/082-event-form, git diff 0b0cff7b..43da6e4b (4 commits, last 43da6e4b "fix round 1")
inputs: 01c, 02-functional-spec.md, 03-implementation-notes.md, 04-test-report.md
status: review only. No source edited, nothing run on any bench, nothing pushed.
youtrack: ALV-339
---

# 082 · Event attendee QR form · Security review

I recommend. Surbhi decides. I am not a lawyer.

**Same-author note (lesson 6).** I wrote 01c, so I am checking the code against my own
requirements. The code is someone else's, so that part is fine. But nobody has checked
whether *my requirements* were the right ones. I ask the techno-functional reviewer to
read 01c §6-§7 with that question in mind.

## 0. The answer first

- **No High and no P0 finding.** No cross-tenant path, no permission bypass, and no
  attendee data in a log, as far as I could read.
- **One Major (P2): erasure is complete only if the Sales Manager ticks "delete linked".**
  If they do not, the lead's notes, tasks and call logs stay behind with their text, and
  no longer point to the lead. The setup guide tells them their details are "removed with
  it", which is then untrue. Fix: one line in the guide, or accept it in writing (F-1).
- **Fix round 1 has not been re-tested in any report.** The two fixes (D1 erasure, D2
  limiter expiry) read correctly in the code, but 04 was written before them. The two
  failing tests must be run again and seen to pass before dev (F-2).
- **SEC-5 was replaced by your decision R1 = A** (300 saves a minute per event, no
  per-address limit in our code, nginx's 120 a minute per address in front). The code
  matches R1 = A. The risk that comes with it (AB2: three addresses can keep one event
  refused for as long as they keep sending) needs your name and a date in §6.
- **Still needs dev or a browser:** XSS in CRM's own lead page and list view; the load
  test (OPS-32 / AC-28); the Guest-row count on real tenants (AC-67). All three need your
  word to run.
- **Counsel questions C-1 to C-6 stay open.** The setup guide's notice already promises
  "6 months" (C-3). That wording must not reach a real attendee until counsel answers.

**Counts:** SEC: 8 Verified, 2 Partial (SEC-5 by design change, SEC-9 browser half).
PRIV: 3 Verified, 3 Partial (PRIV-1, PRIV-5, PRIV-2 seatbelt gaps are Minor).

## 1. Threat model check (01c §1), against what was built

| Question | Still true? |
|---|---|
| Who wants it | Yes. The only new door is one guest POST. No guest read door was added. |
| Blast radius | Unchanged. One tenant's lead list if a read door opens; tests found none. |
| What is new | One public write per event form, bounded at 300 a minute (was 1,000 an hour in 01c). |
| How we find out | Better than 01c expected: an hourly alert counts refusals per form and nginx 503s (`scripts/check_event_refusals.sh`, `worker-health.yml`). Only live after `main`. |

**Real data shape (lesson 1).** No tenant has a published CRM event form today. Every
control here is observable only when (a) a form is published, (b) leads arrive, (c) a
lead is deleted through CRM. Until then "0 refusals" and "0 copies left" mean nothing.

## 2. SEC and PRIV, one by one

Labels: **Code** = I read the line. **Run** = a test in 04 or 03 ran it and I read the
result. **Inf** = inference.

| Item | Status | Mechanism (file:line) | Proof |
|---|---|---|---|
| **SEC-1** writes only the form's fields | **Verified** | `event_form.py:223-230`: any key not in the form's own rows → `INVALID_REQUEST`, nothing saved. `Event form` set from the server's form (`:228`). `NEVER` list `:84`; read-only and hidden fields refuse the form (`:168-171`) | Code; Run `test_082_ac52_…` |
| **SEC-2** nothing read back | **Verified** | Success returns `{"saved": 1}` only (`:245`). Refusals carry a code; `FIELD_INVALID` carries only the question's label (`field_app_errors.py` CODES, `event_form.py:259-264`). CRM validation errors become a plain `SERVER_ERROR` (`:234-244`) | Code; Run `test_082_ac53_…` |
| **SEC-3** one counted bypass | **Verified** | Single `insert(ignore_permissions=True)` at `event_form.py:233`; ceiling `event_form.py: 1`, `www/event_form.py: 0` (`test_portal_security_010.py` +6 lines). No Guest DocPerm added. Second bypass `_erase_copies` (`frappe.db.delete`, `:364-367`, `:390-394`) takes no user input and is declared in the module docstring | Code; Run security suite 45+5 OK, `test_082_ac55_…` (Guest `/api/resource` and `get_list` → 403) |
| **SEC-4** only a clean, published form opens; same answer for closed and unknown | **Verified** | `form_state` `event_form.py:108-164` (allow-list `ALLOWED` `:77`, module `FCRM` + `CRM Lead` + not login-only `:124-127`, required fields `:156-159`, published last `:163`), `_row_problem` `:167-177`. Runs on GET (`www/event_form.py:35`) and POST (`event_form.py:218`). Guest gets the closed card, which returns before any title is set (`www/event_form.py:41-44`); POST answers `FORM_CLOSED` 404 for missing, draft and unsafe alike (`event_form.py:219-221`) | Code; Run `WhatOpens`, HTTP byte compare of unknown vs unpublished (03 §2, AC-19/20). Not every banned type tried (04: P3) |
| **SEC-5** limits | **Partial — by your decision R1 = A** | `event_form.py:210` `_limited(EVENT_KEY, "route", limit=300, window=60)`; no address limit in our code; nginx `deploy/nginx.conf:292-293` and `:507-508` (`kinexus_api`, 120/min per address, burst 30). Expiry fix `_keep_expiry` `field_app_limits.py` (+`:133-142`), called in `finally`; acts only when a key has no expiry, so the 31 other limits are unchanged | Code; Run 305 real sends → 300 saved then 429s (03 §2). D2 test failed in 04 **before** the fix; not re-run since (F-2). Load test not run |
| **SEC-6** no Guest row on User, Employee, CRM Lead | **Verified** (code); real-tenant count outstanding | `event_form.py:329-345`, hook `hooks.py:449-451` (`Custom DocPerm` validate). Stricter than 01c: refuses *any* Guest right on those three, not only read/select. Standard `DocPerm` not hooked (developer-mode only; accepted simplification in 03 §8) | Run `test_082_ac65_…` incl. CRM's `grant_guest_link_access("User")`, Role Permission Manager, an existing row changed to Guest; **switch-off proof: fails without the hook** (04 §4); `test_082_ac66_…` Guest link search on User → nothing. `check_guest_rows.sh` built, not run on any real tenant |
| **SEC-7** organiser box decided on the server | **Verified** | `www/event_form.py:37` (role check), `:41-44`, `:57-66`; box and QR only rendered when `organiser`; CSRF token only for signed-in users (`:40`); `no_cache` + `Cache-Control: no-store` (`:20-28`) | Code; Run AC-31, AC-35, AC-10 |
| **SEC-8** stays in its own site | **Verified** | Address from `frappe.utils.get_url()` (`www/event_form.py:58`); no site/host parameter read anywhere in the diff | Code; Run AC-33 (`?site=`/`?host=` ignored) |
| **SEC-9** guest text cannot run in staff screens | **Partial** | Our page: every value escaped (`event-form.html` uses `|e` throughout; script data via `tojson` `:165-186`; messages built with `textContent` `:206`, `:237-239`). Server: length caps `event_form.py:317-318`; editor types not in `ALLOWED`. Frappe also strips HTML on save (03 §8) | Code (our page); Run AC-56 server side. **CRM's own lead page and list view: NOT RUN** — needs a browser on dev |
| **SEC-10** CRM Lead read doors | **Verified** (Inf: not a freshly made site) | CRM's own role permissions and row rule; nothing of ours | Run 04 §3.4: Guest, Employee-only, HR Manager, no-role login, unassigned Sales User get nothing; assigned Sales User gets exactly L1, including export; switch-off proof of CRM's row rule. Export writes an Access Log row (W2 closed). CI will repeat on a fresh site |
| **PRIV-1** seven fields by default | **Partial** (document control) | `setup-guide.md` step 4 lists seven questions, no upload/age/address | A document; no test. Acceptable, as 01c planned |
| **PRIV-2** sensitive questions refused | **Verified**, with Minor gaps (F-4) | Regex `event_form.py:92-95`, applied to label, row label, field label and fieldname `:174-176`; System Manager-only field creation is Frappe's default | Run AC-23, AC-38; AC-42 (Sales Manager cannot create a Custom Field → 403) |
| **PRIV-3** consent proves what was shown | **Verified** | Consent required on the server `event_form.py:271`, `:281-282`; a tick that did not arrive is 0, form default ignored `:274-280`; page never draws a default (`www/event_form.py:_field`); form refuses to open without both consents and a notice `:150-154`; `set_only_once` on the consent field `:65-66`; Web Form track changes on | Run AC-57, AC-23, AC-51 (old notice text in Web Form's Version) |
| **PRIV-4** withdrawal as easy as consent | **Verified** | CRM Lead track changes; guide §5 "Stop sending me news" | Run AC-46 (Version row: who, 1 → 0; lead leaves the News OK view) |
| **PRIV-5** erasure removes the person | **Partial** (F-1, F-2) | Lead: `after_lead_delete` `event_form.py:348-367` (Deleted Document, Version, Comment, at `before_commit` so Frappe's own Deleted Document row is caught). Notes, tasks, call logs: `forget_unlinked_record` `:370-394`, hooks `hooks.py:466-470`. Retention view deferred by you (14 Nov); manual delete by filter in the guide | Run before fix: lead's own copies erased, switch-off proof (04 §4). CRM-way test with notes and tasks **failed** in 04 (D1); fix in 43da6e4b, **not re-run in any report** |
| **PRIV-6** no personal data out through page or logs | **Verified** | Crash path logs only route hash + error type (`event_form.py:237-241`), messages cleared; refusal log `route=<16 hex>` only (`:201`); limiter keys hashed; values in POST body only (whitelist `methods=["POST"]` `:207`); no other host in the page | Run AC-58 (forced crash: Error Log row has no value), AC-68, AC-27, AC-30, AC-9, AC-59 (0 jobs carry an answer) |

### The specific checks you asked for

| Check | Result |
|---|---|
| Guest save and its single `ignore_permissions` | **Verified** — `event_form.py:233`, after the open check (`:218-221`) and the key check (`:225-226`), under the limit (`:210`) |
| Custom DocPerm hook | **Verified** — `event_form.py:332-345`, `hooks.py:449-451` |
| Form-open refusals (types, FCRM, required, sensitive labels) | **Verified** — `event_form.py:77`, `:124-127`, `:156-159`, `:92-95` |
| Error Log holds no answers | **Verified** for the insert path (`:232-244`, AC-58). See worry W1 for errors raised *outside* that `try` |
| Rate limit 300 / 60 s and the expiry fix | **Verified in code**; expiry fix not yet re-tested (F-2) |
| Erasure hooks (lead, FCRM Note, CRM Task, CRM Call Log) | **Verified in code**; complete only with "delete linked" (F-1); D1 test not re-run (F-2) |
| XSS on the guest page | **Verified** (code read, see SEC-9) |
| XSS in CRM's screens | **Not verified** — needs a browser on dev (04 §8 item 2) |
| CSRF on the guest save | **Verified for our side**: the page sends `X-Frappe-CSRF-Token` for signed-in users (`www/event_form.py:40`, `event-form.html:260`). A guest has no session to forge. **Inference**: Frappe checks the token for every signed-in POST, so a forged post from another site as a signed-in Sales Manager is refused; I could not re-read the installed Frappe source (no container) |
| Closed and unknown links answer the same | **Verified** — code above, plus the HTTP byte compare (03 §2) |

## 3. Findings

| # | Rank | Level | Finding |
|---|---|---|---|
| F-1 | **Major** | P2 | **Erasure leaves notes, tasks and call logs when "delete linked" is not ticked.** *A Sales Manager, in CRM's lead list, deletes an attendee's lead after a "delete my details" request without ticking "delete linked documents". CRM unlinks the lead's FCRM Note, CRM Task and CRM Call Log rows and keeps them (04 §6, Inference from `crm/api/doc.py` 780-800, not run).* Our hook rightly leaves records that still exist (`event_form.py:391-392`). The text the staff wrote about that person stays, now unfindable by lead. The guide says "Its history copies are removed with it" (`setup-guide.md:148`) and does not mention the tick (`:135-137`). **Smallest fix:** two guide lines — "tick *delete linked documents*" in both places — and soften `:148`. Otherwise accept in writing. **Temporary debt** until fixed. |
| F-2 | **Major** | P1 for the release | **Fix round 1 is not proven by a test run in any report.** 04 failed D1 and D2; 43da6e4b changed `event_form.py`, `field_app_limits.py` and `hooks.py`, but its only test change is a hook pin. Code reads right; I could not run it. **Needed:** run `test_event_form_082` (both `test_082_priv5_erasing_an_event_lead_the_crm_way…` and `test_082_ac25_a_window_that_ends…`) plus `test_field_app_*` (the limiter is shared by 31 endpoints), and record the result. |
| F-3 | Minor | P3 | **The limiter's `finally` now calls Redis even when the call failed.** `_keep_expiry` (`field_app_limits.py`, in `finally`) runs `ttl` and maybe `expire`. If Redis errors there, that error replaces the real refusal or result on all 31 limited endpoints. Low chance (Redis down means the limiter failed first anyway). Note only. |
| F-4 | Minor | P4 | **Sensitive-word list misses common spellings.** `event_form.py:92-95`: "account no" does not match "Account number" or fieldname `account_no`; "religion" does not match "religious". "Bank account number" is caught by "bank". It is a seatbelt (01c accepted it as dodgeable); add `account.?n(o|umber)` and `religio` if anyone touches the file. |
| F-5 | Minor | P4 | A form may list `converted`, `alvoraa_ai_needs_review` or `facebook_lead_id` (allowed type, not read-only), and a guest could then set them (04 §6). Needs an organiser to add them. Adding them to `NEVER` (`:84`) is one line. |

No Blocker. Nothing downgraded from fail-closed to warn: refusals refuse the whole save
(`:225-226`), and the open check fails closed on unknown types (`:172`).

**Unneeded surface (review of the opposite failure):** none found. No cache, no copy of
personal data, no new export, no list or edit view on our page (AC-70). The one public
route (`/event-form/<route>`) and one guest POST are what the spec asked for.

## 4. Worries (not findings)

- **W1. Errors outside the guarded insert.** Only `insert` is inside `try` (`:232`). If
  something else raises an unexpected error — for example Redis failing inside the limiter
  while `values` is a local — Frappe's own handler takes over. I do not know whether
  Frappe 16.35 then writes a traceback *with local variables* to Error Log. Check on dev:
  stop Redis briefly on a test site, post once, read the newest Error Log row.
- **W2. A bot on many addresses, or a hostile web page making visitors' browsers post,**
  can write up to 300 junk leads a minute per event, and three addresses can keep the
  event refused. This is R1 = A as decided; the hourly alert is the detection.
- **W3. CRM's assignment rule may email lead details per attendee** (OPS-11, 03 §5). The
  guide warns about "Lead type"; the tenant's own assignment rules are unknown until a
  tenant is named.
- **W4.** CRM's stock `/crm-form/<route>` and Frappe's `/<route>` Web Form page still exist
  beside ours (01c W3). SEC-6 covers the worst of it.

## 5. Compliance check

| Obligation | Source, date | This slice |
|---|---|---|
| Notice before collection, EN + Eighth Schedule language | DPDP s.5; baseline verified 24 Aug 2026 (**82 days — stale on 22 Nov 2026**) | Guide template EN + HI; form will not open without a notice. Hindi needs the native reviewer (O-8) |
| Consent free, specific, unticked, withdrawable | DPDP s.6; 24 Aug 2026 | Met in code (PRIV-3, PRIV-4) |
| Erasure when purpose served | DPDP s.8(7); counsel 18 Sep 2026 "no soft-delete for ever" | Partial (F-1, F-2); period open (C-3) |
| Children | DPDP s.9, Rule 10 (13 May 2027, secondary sources, checked 13 Nov 2026) | Guide forbids under-18 events; notice says 18+. **C-1 open** |
| Processor contract | DPDP s.8(2) — **not re-verified** | **C-2 open**; no live event without a signed agreement |
| Breach readiness | CERT-In 6 h; baseline 24 Aug 2026 | No new control. A public write door is now in scope of the ALV-249 runbook |

Counsel questions **C-1 to C-6 stay open** (C-6: does a lead converted to a Deal leave the
event rule — spec E-13). I have not decided any of them. The guide's notice text promises
"6 months" today; my 01c default was "nothing shown to attendees until confirmed".

## 6. Residual risk

| Risk | Label | Owner | Accepted on |
|---|---|---|---|
| A public write door for as long as QR codes are printed | Intentional trade-off | Surbhi | **Not yet accepted** |
| R1 = A: up to ~18,000 junk leads an hour per event, and an event can be kept refused by three addresses | Intentional trade-off (R1 decided 13 Nov 2026) | Surbhi | **Decision made; risk not yet signed** |
| F-1: erasure incomplete without "delete linked" | Temporary debt — removed by two guide lines | Surbhi / engineer | Not yet accepted |
| Manual erasure may not be done on time (due-for-deletion view deferred 14 Nov) | Temporary debt — removed by counsel's number plus a measured need | Surbhi / organiser | Deferral by Surbhi 14 Nov 2026; risk not signed |
| Sensitive-word refusal can be dodged | Acceptable simplification | Surbhi | Not yet accepted |
| Backups keep erased leads until they age out | Intentional trade-off, stated in the notice (C-3) | Surbhi + counsel | Not yet accepted |

## 7. What I could not verify, and what I would need

- **Fix round 1 by running it** — a free bench (`hrlocal-qr082`); I was told not to start containers.
- **XSS in CRM's lead page and list view** — a browser on dev with a lead holding `<img src=x onerror=alert(1)>`.
- **Load test OPS-32 / AC-28** — dev, with your word.
- **Guest-row count on real tenants (AC-67)** — a named CRM tenant and your word.
- **CRM's delete order** (F-1) and **Frappe's CSRF and 500-logging paths** (W1) — the installed CRM v1.84.0 and Frappe 16.35 source in a running container.
- **A freshly made site** — CI will build one on push (OPS-36).

## Subtract pass

Removed from this review: a full re-listing of every AC (04 has it); a finding on the
`ignore_permissions` docstring mention (the ceiling suite passes, so it is not counted);
a worry about ToDo rows after delete (Frappe's default description holds only the lead's
ID, not personal data); a JSON-nesting crash case (the data would be the attacker's own).

---

## Follow-up · 14 Nov 2026 · fix round 2 (`git diff 43da6e4b..5059e179`)

Reading and git only. I ran no test and started no container.

**Verdict: no new finding. F-1 and F-5 are closed. F-3 and F-4 are closed except one small gap.
PRIV-5 is now met through "Delete N items", once a green test run of 5059e179 is recorded.**

| Check | Result |
|---|---|
| New hook `clear_lead_notices` (`event_form.py` +374-389, `hooks.py` +446-447, CRM Lead `on_trash`) | Read below |
| No privilege escalation | **Verified in code (the hook), Inference (Frappe's order).** `on_trash` only runs inside a delete of that lead. It takes no input from the request and has no whitelisted entry point. In Frappe's `delete_doc`, the delete-permission check comes before `on_trash` (my reading of standard Frappe; I could not re-read 16.35 because no container is running). So the hook only runs for someone who could already delete the lead, or for server code that chose to skip permissions. The guest save never deletes. It removes rows the deleting user could not write, but only rows that point at the lead they are deleting. |
| Touches only event leads' notices | **Verified.** It returns early when there is no `custom_event_form` (+385-386). It deletes only `CRM Notification` rows whose `reference_doctype/reference_name` or `notification_type_doctype/notification_type_doc` equal **this** lead (+387-388). Plain CRM leads keep Frappe's normal behaviour. |
| Rolls back with a failed delete | **Inference, sound.** `frappe.db.delete` runs in the same transaction as the delete, with no commit in the hook. A failure later on (for example a link check on some other doctype) rolls the request back, notices included. Not tested. One gap: in CRM's background bulk delete, I could not check whether the job keeps going after one document fails. |
| PRIV-5 via "Delete N items" | **Met in code. Not yet proven on 5059e179.** Lead copies (`after_lead_delete`); notes, tasks, call logs and now notices (`forget_unlinked_record`, CRM Notification added at `hooks.py` +473-474, field switch at +401); notices that block the delete (`clear_lead_notices`). New tests: an assigned lead deleted **as a Sales Manager**, and a call-log erasure. 04's re-test (51/51) covers 43da6e4b only. **No run of 5059e179 is recorded** in 03 or 04. "Unlink & Delete" still leaves the person's text behind on purpose. That rests on the guide (both places now name the right button) and stays the P3 / counsel point C-3 in 04. |
| F-1 (guide) | **Closed.** `setup-guide.md` 135-140 and 151-154 name "Delete N items", warn against "Unlink & Delete", and no longer over-promise. |
| F-2 (fix round 1 run) | **Closed** for 43da6e4b (04 re-test: 51/51, both fixes fail when switched off). It **reopens for 5059e179**: one run of `test_event_form_082` and `test_field_app_*` is needed before dev. |
| F-3 (Redis in the limiter's `finally`) | **Closed.** `_keep_expiry` is now wrapped in try/except (`field_app_limits.py` +139-146), the same pattern as `_seconds_left`. |
| F-4 (word list) | **Mostly closed.** "account number" and "religious" were added, with a test. A fieldname `account_no` still slips through, because the underscore does not match "account no". Seatbelt only, P4. |
| F-5 (`converted`, `facebook_lead_id`) | **Closed.** Both are in `NEVER` (+85-88), so a form holding either refuses to open, with a test. |

**What is left:** record a green run of 5059e179 (P1 gate). The browser XSS check in CRM screens, the load test and the real-tenant Guest-row count are unchanged from §7. Counsel questions C-1 to C-6 are still open.
