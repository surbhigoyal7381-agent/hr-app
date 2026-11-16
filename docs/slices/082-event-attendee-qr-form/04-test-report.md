---
slice: 082-event-attendee-qr-form
artifact: 04-test-report
author: hrms-test-automation-engineer
date: 2026-11-14
branch: slice/082-event-form (worktree .claude/worktrees/082-event-form), test commit 29ffb45b on fcad19b5
site: test082 in container hrlocal-qr082 (the engineer's own stack; nothing shared was used)
status: local only. Nothing pushed, nothing deployed.
---

# 082 · Event attendee QR form · Test report

## Re-test after fix round 1 — 14 Nov 2026 (engineer's commit 43da6e4b)

**New verdict: Pass with known defects.** Both defects are fixed, and the tests prove the fixes.

| Check | Result |
|---|---|
| `run-tests --module alvoraa_portal.tests.test_event_form_082` | **Ran it. 51 of 51 OK** |
| `run-tests --module alvoraa_portal.tests.test_portal_security_010` | **Ran it. 45 OK + 5 OK** |
| D1: hook `forget_unlinked_record` switched off in-process | **Proven.** The CRM-way erasure test fails without it and passes with it |
| D2: `_keep_expiry` switched off in-process | **Proven.** The window test fails without it and passes with it |
| Site left clean (no test notes, copies or leads) | Checked |

How each fix works:
- **D1:** the hook runs when a note, task or call log is unlinked from an event lead. Just before the commit, if that record has been deleted, the hook removes its Deleted Document and Version copies. My test runs CRM's own delete with "delete linked" on, so it goes through the hook.
- **D2:** after every limited call, `_limited` gives an expiry back to any counter that has none. My test makes exactly that counter (no expiry), so it can only pass if the fix runs.

Known defects that are left (none blocks):
- **P3:** CRM's delete with "delete linked" off still keeps the lead's notes and tasks. They are only unlinked, and their text stays. The engineer did this on purpose ("only unlinked is left alone"). Whether a lead's notes must go when the lead goes is Surbhi's call, with counsel (PRIV-5).
- **P3:** CRM Call Log is covered by the hook, but no test creates one. The rule is the same as for notes and tasks, so this rests on **Inference**.
- Everything in §7 is still **NOT RUN**: browser timing, phone width, screen reader and the dev load test.

The sections below are the first run's report, kept as it was.

## 0. The answer first (first run, 14 Nov 2026)

**Verdict: Fail — two defects found.** Both are for the engineer (cap: two fix rounds).

| # | Defect | Severity | Failing test |
|---|---|---|---|
| D1 | **Erasing an event lead the CRM way leaves copies of its notes and tasks.** CRM's delete (`crm.api.doc.delete_bulk_docs`, `delete_linked=1`) removes the lead, its FCRM Note and its CRM Task, but Frappe writes a Deleted Document row for the note and the task. Their text survives. PRIV-5 says erasure removes "CRM activity rows for that lead". `_erase_copies` only clears CRM Lead's own copies | **P1** (an AC-47 / PRIV-5 obligation fails) | `test_082_priv5_erasing_an_event_lead_the_crm_way_also_erases_its_notes_and_tasks` — `['CRM Task', 'FCRM Note'] != []` |
| D2 | **A form can get stuck "too busy" for good.** Frappe's limiter reads the counter, then adds one. If the 60-second key expires between the two, the add makes a key with **no expiry**. That form is then counted for ever: after 300 more saves, every attendee gets "Many people are sending…". Frappe core code, but the 60 s window (decided in R1) makes the boundary come 60 times more often than slice 013's one-hour window | **P2** (fix, or accept in writing) | `test_082_ac25_a_window_that_ends_during_a_save_still_ends` — `ttl -1 not greater than 0` |

- **No P0.** Every persona and every door held. No cross-tenant or permission leak was found.
- **SEC-10 / R3 is decided by a test:** an assigned Sales User reads exactly their own event lead and nothing of the other two, through every door including export. R3 does not need a permission change.
- **AC-62's open question:** an export **does** write an Access Log row (2 exports, 2 rows). R6 is not opened.

## 1. Commands run (all on test082, one run at a time)

Bench claimed: `docker exec hrlocal-qr082 pgrep -af run-tests` was empty before every run; the container is the engineer's own, so no other session uses it.

| Command | Result |
|---|---|
| `bench --site test082 run-tests --module alvoraa_portal.tests.test_event_form_082` (final) | **Ran it. 51 tests: 49 pass, 2 fail** (D1, D2). 32 were there before; 19 are new |
| Same module, two runs back to back (leak check) | **Ran it.** Same 49 / 2 both times |
| `bench --site test082 run-tests --module alvoraa_portal.tests.test_portal_security_010` | **Ran it.** 45 OK + 5 OK (two batches) |
| Switch-off proof, in-process, script piped on standard input (no file copied, no repo file edited) | **Proven**, 4 of 4 — see §4 |
| `python scripts/check_app_integrity.py` | OK, 941 checks |
| check_brand_spelling, check_no_demo_passwords, check_scope_traps, check_tracked_keys, check_api_paths | all OK |
| `ruff check` on the test file (ruff 0.15.4) | All checks passed |

**Not run:** the full `alvoraa_portal` suite (the engineer ran it; brief said not to); the jsdom DOM test `event_form_082_dom_test.js` (unchanged, last run by the engineer: 36 OK).

**Site schema:** test082 was built by the engineer in the OPS-23 order (wizard, our apps, then CRM v1.84.0 last) and carries slice/082's schema. It is **not freshly created for this run** — it has had many runs. So the "fresh site" rule of data-doors is met only as **Inference**; CI builds a fresh site and will be the honest check (OPS-36 put CRM in CI).

**Versions (AC-64):** Frappe v16.35.0, CRM v1.84.0, ERPNext v16.36.0, alvoraa_portal at 29ffb45b (hrms mounted from the worktree, no tag).

## 2. How the new tests reach the doors

Requests go through Frappe's own WSGI app in a thread (`frappe.tests.test_api.make_request`), so routing, sign-in, the whitelist and the request guard all run as on a real server. **No port was opened and no browser was used.** Each staff login signs in with an API key made in the test; Guest sends no header.

## 3. Traceability

Pass = passes on the final run. "Existing" = the engineer's test. "New" = added here.

### 3.1 Acceptance criteria

| AC | Test(s) | Result |
|---|---|---|
| AC-1, AC-3, AC-4, AC-9 | existing `test_082_ac1_ac9_…`; DOM test | Pass |
| AC-2 | — | **NOT RUN** (needs a real browser at 360 / 390 px) |
| AC-5, AC-11 | existing `test_082_ac5_…`, `test_082_ac11_…` | Pass |
| AC-6, AC-7, AC-12 – AC-15 | DOM test (engineer) | Pass at engineer's run; not re-run |
| AC-8 | — | **NOT RUN** (3G-throttled timing needs a browser) |
| AC-10 | **new** `test_082_ac10_ac19_ac30_…` — page, closed card and save all carry `no-store` over HTTP | Pass |
| AC-16, AC-19 – AC-23, AC-74, AC-75 | existing `WhatOpens` tests; **new** HTTP check that unknown and draft answer the same status | Pass |
| AC-17, AC-56 (server side) | existing `test_082_ac17_ac56_…`, `test_082_ac56_…` | Pass. The "opened in CRM's lead page" half needs a browser — **NOT RUN** |
| AC-18 | — | Untested control (reading only; Hindi needs the native reviewer) |
| AC-24, AC-25 | existing pin and `test_082_ac25_ac27_…`; **new** `test_082_ac24_ac25_300_saves_a_minute_per_event_whatever_the_address` (one real save counts once, TTL ≤ 60 s, 300th passes, 301st from another address refused, another event not held up) | Pass |
| AC-25 (the window ends) | **new** `test_082_ac25_a_window_that_ends_during_a_save_still_ends` | **FAIL — D2** |
| AC-26, AC-27 | existing | Pass |
| AC-28 | — | **NOT RUN** (OPS-32, dev server, needs Surbhi's word) |
| AC-29 | `git diff` (engineer) | Not re-run |
| AC-30 | **new** — a GET of the save is refused and saves nothing | Pass |
| AC-31 | existing (Sales Manager); **new** `test_082_ac31_…` (System Manager) | Pass |
| AC-32 | DOM test (dialog, Escape, focus) | PNG decode not tested — **gap**, needs a browser |
| AC-33, AC-34, AC-35, AC-36 | existing | Pass |
| AC-37 | **new** `test_082_ac37_…` (8 extras warn, QR stays; 5 extras no warning) | Pass |
| AC-38 | **new** `test_082_ac38_…` (sensitive label named; missing notice wording; no QR) | Pass |
| AC-39 | **new** `test_082_ac39_ac41_…` — drawn after Email, answer lands in its column | Pass. CRM builder's "Add Field" list is UI — **NOT RUN** |
| AC-40 | **new** `test_082_ac40_…` — hidden later closes the form, old answer kept | Pass |
| AC-41 | **new** `test_082_ac39_ac41_…` — exact bilingual option stored, near-miss refused 422 | Pass |
| AC-42 | **new** `test_082_ac42_…` — Sales Manager POST of a Custom Field → 403 | Pass |
| AC-43, AC-44, AC-49 | existing `TheViews` | Pass |
| AC-45, AC-69 | setup guide | Untested control (a document; read by reviewer) |
| AC-46 | **new** `test_082_ac46_…` — Version row: who, 1 → 0; lead leaves the News OK view | Pass |
| AC-47 | existing PRIV-5 pin (now writes a real Version row first); **new** CRM-way erasure with note and task | Existing: Pass. New: **FAIL — D1** |
| AC-48 | existing | Pass |
| AC-50 | existing | Pass |
| AC-51 | **new** `test_082_ac51_…` — old notice text in the Web Form's Version | Pass |
| AC-52, AC-53, AC-57, AC-58, AC-60, AC-68, AC-76 | existing | Pass |
| AC-54 | `test_portal_security_010` | Pass |
| AC-55 | **new** `test_082_ac55_…` — no Guest row on CRM Lead / Web Form in Custom DocPerm or DocPerm; Guest `/api/resource` and `frappe.client.get_list` → 403 | Pass |
| AC-59 | **new** `test_082_ac59_…` — no enqueued job carries an answer (0 jobs per save on this site) | Pass |
| AC-61, AC-62, AC-63 | **new** `test_082_ac61_ac62_ac63_sec10_…` — see §3.4 | Pass |
| AC-64 | this report §1 | Done (with the "not freshly created" caveat) |
| AC-65 | existing (read row; CRM's grant); **new** `test_082_ac65_…` (select row by a System Manager through the API; Role Permission Manager's `add_permission`; an existing row changed to Guest) | Pass |
| AC-66 | **new** `test_082_ac66_…` — Guest link search on User returns no staff email | Pass |
| AC-67 | `scripts/check_guest_rows.sh` (engineer: PASS / FAIL / ERROR) | Not re-run |
| AC-70 | **new** `test_082_ac70_…` — `allow_edit` and `show_list` on: no link, no list | Pass |
| AC-71 | **new** `test_082_ac71_…` | Pass |
| AC-72 | — | Focus outline and labels: DOM test. **TalkBack NOT RUN** (needs a phone) |
| AC-73 | `check_event_refusals.sh --self-test` (engineer, 5/5) | Not re-run |

### 3.2 Security (SEC) and privacy (PRIV)

| Item | Test(s) | Result |
|---|---|---|
| SEC-1 | existing `test_082_ac52_…` | Pass |
| SEC-2 | existing `test_082_ac53_…` | Pass |
| SEC-3 | `test_portal_security_010` ceiling; **new** AC-55 | Pass |
| SEC-4 | existing `WhatOpens`; **new** AC-40 | Pass. Not every banned type is tried (CRM Lead has no Attach, Time, Color field to point at) — **thin, P3** |
| SEC-5 | AC-24 / AC-25 tests | Pass, except **D2** |
| SEC-6 | existing pin; **new** AC-65, AC-66 | Pass |
| SEC-7, SEC-8 | existing AC-35, AC-33 | Pass |
| SEC-9 | existing (stored text cleaned) | Pass server side; browser half **NOT RUN** |
| SEC-10 | **new** doors test | Pass — assigned Sales User sees exactly L1 |
| PRIV-1 | setup guide | Untested control |
| PRIV-2 | existing AC-23; **new** AC-38 | Pass |
| PRIV-3 | existing AC-57, AC-23; **new** AC-51 | Pass |
| PRIV-4 | **new** AC-46 | Pass |
| PRIV-5 | existing pin; **new** CRM-way test | **FAIL — D1** |
| PRIV-6 | existing AC-58, AC-9; **new** AC-59 | Pass |

### 3.3 Operations (OPS)

| OPS | Test or reason | Result |
|---|---|---|
| OPS-1, 19 | limit pin and HTTP limit test | Pass (D2 aside) |
| OPS-2, 3, 4, 25 | not adopted / open in the spec | — |
| OPS-5 | AC-6 (DOM), **new** AC-70 | Pass |
| OPS-6 | **new** AC-71 | Pass |
| OPS-7 | existing AC-33 | Pass |
| OPS-8 | **new** AC-30 | Pass |
| OPS-9, 32 | dev load test | **NOT RUN** (dev server, R2) |
| OPS-10, 12 | AC-5, AC-1 | Pass |
| OPS-11, 24 | **new** AC-59 (0 jobs per save); email count from the engineer's §5 | Pass |
| OPS-13, 17 | existing AC-9 | Pass |
| OPS-14, 30 | existing pin; **new** AC-65; engineer's script | Pass |
| OPS-15 | existing AC-35 | Pass |
| OPS-16, 31 | page speed | **NOT RUN** (browser) |
| OPS-18 | existing AC-5 / AC-11 | Pass |
| OPS-20 | DOM test (429 and 503 map to "Many people…") | Pass at engineer's run |
| OPS-21, 29, 34 | `git diff` (engineer) | Not re-run |
| OPS-22 | **new** AC-10 | Pass |
| OPS-23 | site built in that order by the engineer | Inference (see §1) |
| OPS-26, 28 | existing AC-68, AC-58, AC-27 | Pass |
| OPS-27, 38, 39, 40, 41 | alert script self-test (engineer) | Not re-run; live only after `main` |
| OPS-33 | existing AC-11 | Pass |
| OPS-35, 37 | read-only counts and the hand test on dev | **NOT RUN** (dev server) |
| OPS-36 | CI change (engineer) | Not run here — CI runs on push |
| OPS-42, 43 | comment / FYI | — |

### 3.4 The doors, persona by persona (AC-61 to AC-63)

One form, three event leads (L1 to L3) saved through the real guest path, each with an extra "Shop name" answer. L1 assigned to Sales User S1. Doors tried by each persona: `/api/resource` list, get, put; `frappe.desk.reportview.get`, `get_count`, `export_query` (CSV); `frappe.client.get`, `get_list`, `get_value`; `search_link`; `frappe.share.add`; `assign_to.add`.

| Persona | What they got | Result |
|---|---|---|
| Guest | 403 or nothing on every door; no name, no shop name in any answer | Pass |
| Employee only | same | Pass |
| HR Manager | same | Pass |
| Plain login, no roles | same | Pass |
| Sales User, not assigned | same; count 0 | Pass |
| Sales User, assigned L1 | L1 through list, report view, get_list, export; count 1; L2 refused on get, put, share, assign; L2 never in any answer | Pass |
| Sales Manager, System Manager | export holds all three | Pass |

After all of it, L2's name is unchanged, and no share or open assignment exists on it. Link search on `Event form` (Web Form) was not tried separately; Guest and staff search on CRM Lead itself was.

## 4. Pin tests: do they fail without their fix?

Each fix switched off **in-process** (a script piped into the container's Python; no file copied, no repo file edited), the same test run, then run again with the fix on.

| Fix switched off | Test | Without fix | With fix |
|---|---|---|---|
| `refuse_guest_perm` (Custom DocPerm hook) | `test_082_ac65_…` | FAIL | PASS |
| CRM's row rule for CRM Lead (`get_lead_permission_query_conditions` returns nothing) | `test_082_ac61_ac62_ac63_sec10_…` | FAIL | PASS |
| The limiter's count (`incrby` always 1) | `test_082_ac24_ac25_300_…` | FAIL | PASS |
| `_erase_copies` | existing `test_082_priv5_an_erased_event_lead_leaves_no_copy` | FAIL | PASS |

**4 of 4 proven.** The other new tests (AC-37 to AC-41, AC-46, AC-51, AC-59, AC-70) were not switched off one by one — **Inference** only that they can fail.

## 5. Things I found in the suite itself, and fixed (test code only)

| What | Effect | Fix |
|---|---|---|
| **Frappe writes no Version rows in tests** unless `save(ignore_version=False)` (`document.py:576`) | The existing PRIV-5 pin's "zero Version rows" check passed whatever the code did — a hollow assertion | The pin now saves with `ignore_version=False` and asserts a Version row exists before the delete |
| Test leads that were assigned left **CRM Notification and ToDo rows** behind | A later lead with the same name could not be deleted (`LinkExistsError`); `test_082_ac48` failed once in a batch and passed alone | The shared `tearDownClass` now deletes ToDo, DocShare and CRM Notification rows of the test leads |
| test082 held **3 Guest rows on Web Page** in Custom DocPerm, left by an earlier version of the slice's own test (13 Nov, 17:29–17:33) | Custom rows replace a doctype's standard rows, so Website Manager had lost Web Page access on test082 | Deleted the three rows on test082 (site state only); the current test does not leak — checked |
| 6 stale CRM Notification rows from test leads | as above | Deleted on test082 |

## 6. What the tests showed beyond the ACs

- **Desk delete of an assigned lead is refused** (`LinkExistsError` on its CRM Notification). CRM's own delete clears the notification and works. **Ran it** (script, rolled back). P3: the setup guide already says to use CRM; worth one line saying "delete from CRM, not from Desk".
- **CRM delete with "delete linked" off** keeps the notes and tasks, only unlinked. **Inference** from `crm/api/doc.py` lines 780-800; not run. Part of D1.
- A form can list `converted`, `alvoraa_ai_needs_review` or `facebook_lead_id` (allowed types, not read-only) and a guest could then set them. Only an organiser who adds those questions can open this. P4, note only.

## 7. NOT RUN, and why

| Item | Why |
|---|---|
| AC-8 / OPS-31 page time on 3G | Needs a real browser; downloading one was refused for this session |
| AC-2 at 360 / 390 px | same |
| AC-56 and SEC-9 in CRM's lead page and list | same |
| AC-32 PNG decode | same |
| AC-72 TalkBack | Needs an Android phone |
| AC-28 / OPS-32 load test, OPS-35, OPS-37 | Dev server; needs Surbhi's word |
| Full `alvoraa_portal` suite | Brief: the engineer ran it; not repeated |
| A freshly created site | Not allowed to start containers; CI builds one on push |

## 8. Human checklist

1. One Chrome DevTools pass with the custom throttle from OPS-31, five loads, record bytes and the slowest time.
2. Open a lead holding `<img src=x onerror=alert(1)>` in CRM's lead page and list view; no dialog.
3. Download the PNG, scan it with a phone; it opens this site's own address.
4. One TalkBack pass completing AC-5's task.
5. Hindi lines read by the native reviewer (O-8).

## 9. Parallel work

Fetched `origin/dev` before committing: nothing new since `0b0cff7b`. Only `test_event_form_082.py` changed, committed as `29ffb45b` on `slice/082-event-form`, staged by path. This report sits in the main checkout and is **not staged**.

## 10. Subtract pass

Removed one new test: a real-HTTP request-guard check. It only proved what `test_082_ac52_…` and `test_082_ac60_…` already prove. Moved the ToDo / DocShare clean-up out of one class into the shared tear-down, so it is written once.

## Re-test after fix round 2 (5059e179), 14 Nov 2026

Run by the orchestrating session in hrlocal-qr082 / test082, one module at a time. Container code checked identical to the worktree first.

| Module | Result |
|---|---|
| test_event_form_082 | 53 / 53 OK |
| test_portal_security_010 | 45 + 5 OK |
| test_field_app_step3_013 (shared limiter) | 41 + 9 OK |
| test_field_app_step6_013 (shared limiter) | 1 + 27 OK |

Verdict: **Pass.** Still not run: the browser timing, phone width, screen reader and the dev load test, which wait for dev (user decision C).
