---
slice: 082-event-attendee-qr-form
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-11-13
status: built locally, not pushed, not deployed
youtrack: ALV-339
branch: slice/082-event-form (worktree .claude/worktrees/082-event-form), base origin/dev c3885fad
---

# 082 · Event attendee QR form · Implementation notes

I recommend. Surbhi decides. Nothing here is on dev or production.

## 0. The answer first

- **Built:** the public page `/event-form/<route>`, the guest save, the organiser box with the QR
  card, the two permission hooks (no Guest row on User/Employee/CRM Lead; erased event leads
  leave no copy), the five CRM Lead fields, the hourly refusal alert (our log **and** nginx
  503s), the Guest-row check script, and Frappe CRM in CI.
- **Tests:** the slice's own module **28 of 28 pass**. Full `alvoraa_portal` suite: see §6.
- **Bad news:** none that blocks. The gaps that are left are listed in §8. The biggest is
  **AC-8 (page speed on a 3G-like connection) is not measured yet** - I measured the server
  time and the bytes, not a throttled phone.
- **No push, no deploy, no command on dev or production.**

## 1. What was built, file by file

| File | What | Rung, and why |
|---|---|---|
| `alvoraa_portal/event_form.py` (new) | `form_state` (the open check), `save` (guest POST), `refuse_guest_perm` (Custom DocPerm validate), `after_lead_delete` + `_erase_copies` (PRIV-5), `ensure_fields` / `on_app_install` | 4, new code. CRM's own page allows 10 saves a minute per address; a hall needs 300 per event |
| `alvoraa_portal/www/event-form.html`, `www/event_form.py` (new) | The phone page, the closed card, the organiser box, the QR card dialog | 4. CRM's page cannot change its layout or its limit (07 §2) |
| `hooks.py` | Route rule; `CRM Lead` `after_delete`; `Custom DocPerm` `validate`; `ensure_fields` in `after_migrate`; `after_app_install` became a two-item list | 4, hooks rather than edits to CRM |
| `field_app_limits.py` | `_limited(..., window=WINDOW_SECONDS)`; `EVENT_KEY` | Smallest change to reuse slice 013's limiter; the 31 existing uses keep 3,600 s |
| `field_app_errors.py` | `FIELD_INVALID` (422, label), `FORM_CLOSED` (404) | Added, never renamed (the table's rule) |
| `tests/test_portal_security_010.py` | CEILINGS: `event_form.py` = 1, `www/event_form.py` = 0 | SEC-3 |
| `tests/test_event_form_082.py` (new) | 28 tests | - |
| `.github/workflows/ci.yml` | CRM v1.84.0 fetched (`--skip-assets`), put in `apps.txt`, installed after our apps; cache key carries the CRM tag; one self-test step for the alert script | OPS-36. **About 12 lines - as small as hoped** |
| `scripts/check_version_pins.py` | CI's `CRM_TAG` must equal the Dockerfile's | Keeps OPS-36's pin honest; 8/8 self-test |
| `.github/workflows/worker-health.yml` | One step: "Event form refusals", `if: always()` | OPS-27 / OPS-38, reuses the hourly runner |
| `scripts/check_event_refusals.sh` (new) | Counts `limit` + `closed` refusals per route hash in the last hour, and nginx 503s on the save call; fails at 30 | AC-73; `--self-test` 5/5 on Git Bash and Linux |
| `scripts/check_guest_rows.sh` (new) | OPS-30: PASS/FAIL on Guest rows for User, Employee, CRM Lead; lists roles that read CRM Lead | AC-67; proven PASS, FAIL (planted row), and "ERROR, not a PASS" on a missing site |

**One change from the strategy:** the fields are made by `after_migrate` (plus
`after_app_install`), not by a patch. That is the pattern slice 057 already uses for its CRM
field, it runs safely every migrate, and it saves an edit to the hot file `patches.txt`.
Same effect on every site.

## 2. Acceptance criteria

| AC | How it is met | Proof |
|---|---|---|
| AC-1, AC-3, AC-4 | Page draws title, intro, rows in order, button label; Select ≤ 6 → radio rows; tel/email/numeric/decimal/date inputs; no Discard | `test_082_ac1_ac9...`; jsdom run |
| AC-2 | 16 px inputs, 48 px rows and Send, 15 px labels, ink #2b2b2b | CSS only. **To run on dev (user decision C, 14 Nov 2026)** |
| AC-5, AC-6, AC-11 | One stamped lead, `lead_owner` empty, status "New"; thank-you names the event, echoes nothing; lead exists when 200 returns; no enqueue | `test_082_ac5...`, jsdom, HTTP run |
| AC-7 | Send disabled while sending; double tap = one request | jsdom |
| AC-8 | Page 19.4 KB (guest), 21.5 KB (manager), one request, no other host; server time median 143 ms | **To run on dev (user decision C, 14 Nov 2026).** Arithmetic only: about 4 round trips of 562.5 ms plus ~0.1 s transfer ≈ 2.4 s, at the edge of the 2.5 s budget |
| AC-9 | No other host, no `<img>`, phone fonts | test + HTTP `grep` (zero hosts) |
| AC-10 | `Cache-Control: no-store` on page and closed card; save answers `no-store,no-cache,...` | HTTP run |
| AC-12 – AC-17 | Every failure keeps the answers; 429 and 503 → "Many people…"; 404 `FORM_CLOSED` hides Send; 422 shows the server's sentence; network/500/30 s → "Not sent" | jsdom (all six cases), tests |
| AC-18 | English wrapped in `_()`; Hindi as in 01b §6.2 | Read; Hindi still needs the native reviewer (O-8) |
| AC-19, AC-20 | One closed card; unknown and unpublished bodies byte-identical; no title | test + HTTP `cmp` |
| AC-21 – AC-23, AC-74, AC-75 | `form_state` rules | `WhatOpens` tests |
| AC-24 – AC-27 | `(event_form_key, route, 300, 60)`; 301st refused 429; key holds the hash; others keep 3,600 s | tests; **real HTTP: 305 sends → 297 saved + 3 earlier = 300, then 8 × 429** |
| AC-28 | OPS-32 on dev | **Not run** - needs your word (R2) |
| AC-29 | No nginx, compose or `server.env` change | `git diff` |
| AC-30 | POST body only; GET of the save → 403 | HTTP run |
| AC-31 – AC-35 | Box only for Sales/System Manager; address from `get_url()`; `?site=`/`?host=` ignored; draft and broken-form boxes have no QR button | tests, jsdom (dialog, Escape, focus) |
| AC-36 – AC-38 | Box texts (Link, other types, sensitive, consent, required) | `test_082_ac34_ac36...` (Link, draft); others by reading |
| AC-39 – AC-41 | CRM's builder offers new fields (fact §1 of 00); page draws them; Select checked exactly | test (Select); builder by source read |
| AC-42 | Frappe default (Sales Manager cannot write Custom Field) | **Not tested here** |
| AC-43 – AC-45, AC-49 | `setup-guide.md` (in the slice folder, committed) gives three saved views as CRM configuration. The fourth, "Event leads – due for deletion", is **deferred by the user, 14 Nov 2026** (good to have, not a must); the guide now says how to delete an event's old leads by filter. The AC-49 test is kept; tests run each view's own filters and sort | `TheViews`: AC-43 (all 1s before 2s; unrated leads sort **first** without "is set" - 01b's EF13 assumption is now a fact), AC-44 (count per form), AC-49 (only old leads without News OK) |
| AC-46, AC-51 | Track changes is on for CRM Lead and Web Form (confirmed) | fact, not a new test |
| AC-47, AC-48, AC-50 | Erasure leaves no Deleted Document / Version / Comment; a plain lead keeps Frappe's copy; consent cannot change | tests |
| AC-52, AC-53, AC-56 – AC-58, AC-76 | Unknown keys → 400; one body; Frappe cleans HTML on save; consent required; crash → 500 with hash + error type only | tests |
| AC-54, AC-55 | CEILINGS row; no Guest DocPerm added | security suite (§6) |
| AC-59 | Insert side effects | §5 |
| AC-60 | `request_guard` drops both words | test |
| AC-61, AC-62 | Sales User sees only assigned; second Sales User none; plain login and Guest refused; manager all | test (doors 1-2 and `has_permission`); export not driven in a test (§8) |
| AC-63, AC-64 | - | test engineer |
| AC-65, AC-66 | Custom DocPerm Guest rows on the three doctypes refused; CRM's `grant_guest_link_access("User")` refused; a Guest row on Web Page still allowed | test |
| AC-67 | `check_guest_rows.sh` | run on test082 (PASS / FAIL / ERROR) |
| AC-68 | One line per refusal: `refused reason=<r> route=<16-hex>` | test |
| AC-69 – AC-72 | Guide; no list/edit view on our page; uploads untouched; labels and focus | AC-72's TalkBack pass not done (§8) |
| AC-73 | Alert script and workflow step | `--self-test` 5/5 |

## 3. Seven dimensions, against the code as written

| Dimension | Before → after | Verdict | Why |
|---|---|---|---|
| Performance | - → save p95 **55 ms** (40 saves, local dev server), page median 143 ms | **Neutral** | Staff paths gain one `if` in CRM Lead `after_delete` and one check on rare Custom DocPerm saves. No cache, no job |
| Security | No public write → one public write door | **Degrades, bounded** | Allow-list of keys, the open check on GET and POST, 300/60 s per event, nginx's address limit, one counted bypass. **Improves** too: the Guest-row hook closes today's staff-name leak on every tenant with CRM |
| Reliability | - | **Improves** for event capture | Synchronous save; every failure keeps the answers; crashes caught and answered in plain words |
| Scalability | - | **Degrades slightly** | Bursts share the web workers; capped at 300 saves a minute per form. OPS-32 is the real measure |
| Maintainability | - | **Degrades slightly** | Reads CRM's Web Form record; `test_082_ac11` fails if CRM renames what we read. One module, no abstraction |
| Data integrity | - | **Neutral** | One insert, one transaction. A lost reply can make a duplicate lead (E-1, accepted) |
| Compliance / privacy | - | **Improves on staff data; new public data with controls** | Consent required on the server, never pre-ticked; refusal and crash logs carry no answers; erasure removes copies |

## 4. NFR notes

- **Queries:** not counted with a spy. Timing: save p95 55 ms, max 60 ms, single process.
- **Indexes:** none added. The saved views filter on `custom_event_form`, which has no index;
  at a few hundred leads per event that is a small scan. Add one only if a view is measured slow.
- **Background jobs:** none. Frappe itself enqueues `delete_dynamic_links` on delete (after commit).
- **Permission enforcement points:** CRM Lead role permissions + CRM's
  `permission_query_conditions` / `has_permission` (unchanged); our Custom DocPerm hook.
- **Bypasses:** (1) the guest insert, counted at 1; (2) `_erase_copies` `frappe.db.delete` after
  a permitted delete; (3) `form_state` reads Web Form config with `frappe.db.get_value` /
  `get_doc` - layout, not personal data, and a guest has no right on Web Form.
- **Sensitive fields:** name, mobile, email, comment. Never logged, never in the URL, never in a
  Redis key, never echoed.

## 5. What a lead insert sets off (OPS-24, on test082 with CRM)

CRM `before_insert` (`enrich_form_submission`, no-op: we do not set `in_web_form`);
`before_validate` (SLA lookup); `validate` (status "New", names); `after_insert` (nothing, no
owner). Frappe's global `on_update`: assignment rules (none on a fresh site; **a tenant's
CRM assignment rule would create a ToDo and may email per lead**), search-index update. Ours:
slice 057's `on_status_change` and `refresh_task_labels` (no-op without `custom_lead_type`).
No job carries attendee values. Email count for 300 leads on a stock site: 0.

## 6. Commands run and what they said

| Command | Result |
|---|---|
| `bench --site test082 run-tests --module alvoraa_portal.tests.test_event_form_082` | **28 tests, OK** |
| `bench --site test082 run-tests --app alvoraa_portal` (second run; Docker Desktop stopped the first) | Three blocks: **71 OK**; **1,293 with 1 error**; **3,121 with 4 errors** (15 and 40 skipped). **None of the 5 errors touches a slice 082 file** - causes below |
| After rebasing on origin/dev `0b0cff7b`: `test_event_form_082`, `test_portal_security_010`, `test_install_hooks_parity`, `test_portal_module_gate_016` | 28 OK; 45 + 5 OK (two batches); 4 OK; 17 OK |

The five errors in the full run, and their causes:

| Test | Error | Cause |
|---|---|---|
| `test_expense_birthdays_076` (department approver) | MismatchError: "Department C076 Dept - S4E2 does not belong to company: S043 Wave Three Company" | Leftover data from other tests on test082; it repeats when run alone. Site state, not code |
| `test_field_app_step2_013` ac21 | "Choose a reason" | HR Settings on test082 still holds a leftover row, "Zqx Driver 013", in Alvoraa Field Worker Designation; removing it needs a reason. Site state; dev CI passes on a fresh site |
| `test_field_app_step2_013` ac24 | "Choose a reason" | Same leftover row |
| `test_grooming_066` z1..z12 | OSError: Cannot allocate memory | Machine load on this laptop during the run |
| `test_grooming_cap_066` m1 | `bench execute` call timed out after 180 s | Machine load |

Before that run, the first full run had caught two faults of mine, both fixed: the field set-up
was in `after_migrate` but not `after_install` (`test_install_hooks_parity`), and a test used a
`.example` email address (`test_portal_module_gate_016`).
| `alvoraa_portal/tests/event_form_082_dom_test.js` on the two fixtures (jsdom 27.1.0), now in `scripts/run_dom_tests.js`, so CI runs it | 36 checks, all OK |
| Real HTTP against `bench serve` in my container | as in §2 |
| `scripts/check_event_refusals.sh --self-test` | 5/5 (Git Bash and Linux) |
| `scripts/check_guest_rows.sh` | PASS; FAIL with a planted row; ERROR (exit 2) on a missing site |
| `scripts/check_version_pins.py` (+ `--self-test`) | OK; 8/8 |
| `scripts/check_app_integrity.py` | OK, 938 checks |
| ruff 0.6.9 on my files | All checks passed |
| check_api_paths, design_system, tag_balance, brand_spelling, no_demo_passwords, preview_flag, scope_traps, tracked_keys, nginx_conf | all OK |

The test site is my own (`test082` in `hrlocal-qr082`, built in CI's order with CRM installed
last). I cleared its cache once from a script so the new route rule loaded. Nothing shared
was touched.

**Refreshing the DOM fixtures.** `tests/fixtures/event_form_082_guest.html` and
`_manager.html` are the page as the server renders it for the test form `s082-pune-dealer-meet`.
`test_082_the_dom_fixtures_carry_todays_script` fails when the page's script changes and they
were not rendered again. To render them: on a test site with CRM, run the `TheSave` set-up
(`make_form()`, `ensure_user(MANAGER, ["Sales Manager"])`), then for Guest and the manager set
`frappe.local.session.data.csrf_token`, build a werkzeug request for `/event-form/<route>`,
call `frappe.website.serve.get_response_content`, blank the `"csrf"` value and save.

## 7. What else moved while I worked

Five commits came into `origin/dev` from other sessions after `c3885fad`: `7faf3043` (one punch
is a present day), `e393f4a7` (joiner invite form can be saved), `ee599d78` (subtract pass),
`f966a986` (after a machine punch the app offers Check out), `0b0cff7b` (geofence test). They
touch attendance_correction, shift_standard, payroll_rules (`label_punches`), field_checkin,
home_api, hr_api, alv291, the joiner submission JSON, tests, and **one comment in hooks.py**
(the Shift Type window comment, 3 h → 4 h). I read the diff. My commit rebased on top with no
conflict; hooks.py keeps both their comment and my five entries. Nothing in the incoming code
touches CRM, Custom DocPerm or the limiter. The shared main checkout still carries another
session's uncommitted edits; untouched.

## 8. Known gaps and shortcuts

| Gap | Label |
|---|---|
| AC-8 slow-3G timing and AC-2 at 360/390 px | **To run on dev (user decision C, 14 Nov 2026)**, with the OPS-32 load test once the user allows it. Locally a browser was not available to this session |
| The DOM test reads rendered fixtures, not the live template | **acceptable simplification** - a Python test fails if the page's script and the fixtures drift apart |
| AC-28 / OPS-32 on dev | waits for your word (R2) |
| AC-42, AC-62 export, AC-63, AC-64 door tests | test engineer, on a site built in the OPS-23 order with the wizard |
| `DocPerm` (standard rows) not hooked, only `Custom DocPerm` | **acceptable simplification** - standard rows change only in developer mode; the OPS-30 script reads both tables |
| A site that installs CRM **before** our app gets the fields at the next migrate, not at once | **acceptable simplification** - provisioning installs CRM after our apps |
| Communications (emails) about an erased lead are unlinked by Frappe, not deleted | **intentional trade-off** - event leads normally have none; delete by hand if one exists |
| Frappe cleans HTML out of the comment on save, so "stored as typed" is not literally true | **intentional trade-off** - safer than the spec asked |
| `desk_request` (named for HR desk endpoints) wraps this guest endpoint | **acceptable simplification** - it does exactly what is needed |

## 9. Parity with prototype-v2

| Prototype item | Built? | Note |
|---|---|---|
| Screen 1 form, 360/390, missing-fields, no signal, too many, closed meanwhile, closed link, thank you | Yes | Font: phone's own (no "Inter" download, OPS-13) - looks slightly different on phones without Inter |
| Thank-you Hindi line | Yes, when the organiser leaves the success message empty | With an organiser message, their own words are shown |
| Screen 2 box Ready, 8 extras, Link field | Yes | |
| Box draft / missing notice / sensitive / required | Yes | P-2, P-3 accepted; "required" box is new (AC-75) |
| QR card dialog, Close, Download PNG | Yes | Drawn on one canvas: the dialog shows the picture the PNG saves. Layout matches 01b §6.4; not pixel-checked |
| Screen 3 views: "Pune Dealer Meet – lowest first", "Events – entries per form", "Nashik … – answers" | Yes, as CRM saved views made from the setup guide, with the prototype's names, filters, sort and columns | P-4 (the "!" chip) accepted. A fourth view ("Event leads – due for deletion") was drafted and then **deferred by the user, 14 Nov 2026** |

## 10. Subtract pass

Removed: the patch (after_migrate does it); the `LAYOUT` filter in the save (layout rows never
reach it); an unused constant in the page controller; a `noqa`. Nothing else could go without
losing an AC.

## 11. User decisions and fix rounds (14 Nov 2026)

**Decisions recorded:**

- **Other public save paths** (`/<route>` and `/crm-form/<route>`, through `web_form.accept`):
  **option A - accepted for go-live as a known gap** (W3 / OPS-43 / review P2 #3). Event teams
  share only the `/event-form/` QR link. No code change.
- **Rate limit 300 saves per 60 s per event** (SEC-5 replaced by R1 = A): **the user accepts the
  trade-off in writing** - up to about 18,000 junk leads an hour per event, and a few addresses
  could keep an event refused.
- "Event leads – due for deletion" saved view: deferred by the user, 14 Nov 2026.
- 360/390 px check and slow-3G timing: to run on dev (user decision C, 14 Nov 2026).

**Fix round 1 (`43da6e4b`):** D1 - notes, tasks and call logs unlinked then deleted by CRM's
"delete linked" leave no Deleted Document / Version copy (`forget_unlinked_record`). D2 - a
limiter key that lost its expiry gets its window back (`_keep_expiry`).

**Fix round 2:**

- CRM Notification added to `forget_unlinked_record` (it names its record in
  `reference_name`). **Found while testing:** a **Sales Manager could not erase an assigned event
  lead at all** - CRM's "delete linked" skips the assignment notice (the manager cannot write
  it), and Frappe then refused the lead because the notice still linked to it; CRM swallowed the
  error. New `clear_lead_notices` (CRM Lead `on_trash`, event leads only) removes the notices
  before Frappe's link check, in the same transaction. The erasure test now assigns the lead and
  deletes as a Sales Manager; a new test covers call logs.
- Setup guide: when deleting, choose CRM's **"Delete N items", not "Unlink & Delete N items"**.
  CRM has no "Delete linked documents" tick box; those are its two real buttons.
- "account number" and "religious" added to the sensitive-label words; `converted` and
  `facebook_lead_id` refuse to open a form. Tests for both.
- `_keep_expiry` wrapped in try/except like `_seconds_left`.
