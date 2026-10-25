---
slice: 070-readable-on-phone (YouTrack ALV-217)
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-10-25
status: built and tested LOCALLY. Not pushed. No deploy command run.
base: slice/070-readable-on-phone on origin/dev 6aaf9ffd (fetched again 25 Oct: nothing new came in)
---

# 070 · Implementation notes

## Read this first

- **Built as approved: E1 (refusals at the top of the form), E2 (AC-22's list), plus DevOps
  OPS-S2, S3, S4.** Client side only. No server file, DocType, patch, setting, font, image,
  route or new file requested by the page.
- **Two things for Surbhi to confirm (I did not decide them):**
  1. **A late answer after the 15 s message.** The approval note says "a late answer after a
     time-out is ignored". The spec (AC-21, AC-33), the design (D10) and the approved prototype
     (P36) say the late answer still counts, once. I built the spec: a late page load paints
     over the box; a late leave, expense or advance send shows its normal success once. What
     OPS-S3 really guards is met: **no** time-out ever unlocks a write button for a blind resend.
  2. **Undrawn screens** (parity table rows not in the prototype) — listed under "Parity" below.
- **The local copy of PPJ is behind dev's database.** `get_leave_summary` and
  `get_manager_dashboard` fail there with "DocType Alvoraa Payroll Rule Set not found".
  So the Leave page on `ppj.localhost` showed the new 5xx box (a real test of AC-19), and I
  drove the Apply for Leave pop-up with a stub for that one read. Not a 070 fault.
- **Size: M, top end.** ~580 lines added in `portal.js` (estimate was ~430). The extra is the
  OPS-S3 guard on 23 write callbacks and comments.

## What I built, file by file

| File | What | Rung / why |
|---|---|---|
| `public/js/ess/portal.js` — shared helpers (own commit) | `api()`: no signal → error at once, nothing sent; 15 s → error once, request not cancelled; real failures finally reach the error branch (website `frappe.call` never calls `error`). `callKind`, `callWords`, `relay`. `gpFetch`/`gpSend`: same offline and 15 s rules; a time-out carries `.late`; an nginx HTML page is a 5xx, not a crash. `gpErr`: never shows `exc` or status text (SEC-4); a 5xx's own text is not shown either. `mayHaveGone`/`sayMayHaveGone` + a guard at the top of 23 write callbacks (OPS-S3) | New code: no setting for any of this |
| `portal.js` — screens | `failBox` (one box for every AC-22 load), leave send states `lsSend` for both leave forms, expense and advance sends, `fmtDate` from ISO parts, `dateInWords`, `refreshDateWords`, `localToday`, `acRow` (Weekly off, plain holiday name, phone two-line block), `acPlain`, Home (`homeActivity`, `homeDashboard`, hidden empty Activity, past holidays hidden), `switchPanel` (top bar page name) | New code |
| `public/css/ess/frame.css` | `.fail`, `.send-fail`, `.date-words`; G8 fix (closed drawers lose their shadow); one `@media (max-width:768px)` block with 01b §5 sizes and the phone day blocks | CSS only; `design_system.html` untouched (AC-6) |
| `parts/home.html` | "Hey there," and the clock date removed; Activity card gets an id | Template |
| `parts/request-modals.html` | Date-in-words lines; Half Day row is one label; send message areas | Template |
| `parts/requests.html` | Date-in-words lines on the attendance request; advance send message area | Template |
| `tests/portal_phone_070_test.js` (new), `scripts/run_dom_tests.js` | The pin test: 87 checks | Test |
| `tests/portal_leave_063_test.js` | R-48 moved to the `fetch` stub (OPS-S2); date helpers built like the page | Test |
| `scripts/check_attendance_strip.js` | Knows acRow's new helpers | Script |

**Not touched:** `panels.css`, `hr_api.py`, `time_api.py`, `attendance_correction.py`,
`design_system.html`, `deploy/`, any DocType, `next-*`.

## Acceptance criteria

| AC | Status | How proven |
|---|---|---|
| AC-1 – AC-4 | Met | Browser, 390 and 360 px: smallest text 12 px, 0 controls under 44 px, every field 16 px / ≥ 44 px, no sideways scroll — Home, Attendance, Leave, Finances (3 tabs), Attendance request, Advance, Shift request, Apply leave pop-up, Expense pop-up, slide-out menu |
| AC-5 | Met | Desktop 1440: tokens 11/12/13/15 |
| AC-6 | Met | No diff to `design_system.html`; only `hrms-employee.html` loads `frame.css` |
| AC-7 | Met | Header boxes 44 × 44, drawn 36 (prototype's own technique) |
| AC-8 – AC-10 | Met | Browser (Rahul, Oct 2026: 1 Oct "Weekly off", 2 Oct "Gandhi Jayanti") + jsdom |
| AC-11 – AC-16 | Met | jsdom (fmtDate, dateInWords); browser scan of each screen for ISO, dd/mm/yyyy, "Sept", leading zero: one hit found and fixed (late-coming week dates) |
| AC-17 – AC-21 | Met | Browser: offline box in < 1 s; "Still could not…"; held answer → box at 15.0 s, data at 18.5 s with no tap; 5xx box on the Leave page |
| AC-22 | Met for the AC-22 list | Boxes on Home (Activity, holidays), Attendance, Leave page, Finances (3 tabs), request histories, shift/encashment/expense/leave-type selects, Team View. Others: 15 s limit with their existing text (E2) |
| AC-23 | Met | "We could not load the leave types." under the select |
| AC-24 | Met | No timer calls `api()`/`gpFetch` after a failure (jsdom checks counts after 16 s) |
| AC-25 – AC-37 | Met | Browser: no-signal (nothing sent), lost answer at 15.0 s, Checking… found it, one send, late answer success once. jsdom for each AC |
| AC-38 – AC-40 | Met | jsdom: double tap → 1 send; three lost answers → 1 record |
| AC-41 – AC-44 | Met | jsdom |
| AC-45 – AC-47 | Met | jsdom + browser: a 500 shows no Frappe pop-up and no server text; a 403 still shows "Not permitted" as before |
| AC-48 – AC-51 | Met | Check sends `employee_id` only for HR on-behalf (jsdom); signature unchanged; no storage API, no new `console.*` |
| AC-52 – AC-54 | Met | Browser: two-line blocks 60 px, named buttons, tap opens "What went wrong?", desktop table unchanged |
| AC-55 – AC-57 | Met | Browser: no greeting line, no clock date, empty Activity hidden, "No more holidays in October." |
| AC-58 | Met | Browser 1440: Attendance, Leave, My Finances, Team View, Home |
| AC-59 | Met | Cause found: closed drawers off the right edge kept a 32 px shadow. Removed while closed |
| AC-60 – AC-61 | Met | No new file; existing `?v=` links |
| AC-62 – AC-63 | Release step | DevOps §5 |
| AC-64 | Not run | Needs a real Android phone at "Largest" — human check |
| AC-65 | Met | New strings through `drT()` |

## Parity with prototype v1

Built as drawn: P2–P4, P6–P25, P27–P36. P1, P5 prototype-only. P26 unchanged (server preview).

**Not drawn — built from the spec's words, for Surbhi to confirm:**
1. P38 advance: the button shows "Sending…" instead of today's full-screen loading overlay.
2. Leave page failure: one box at the top; the list under it goes blank instead of a second box.
3. Expense types, shift types and encashment types: the generic box under the select
   ("We could not reach the office."). Only the leave-type heading was decided.
4. Home check-in status keeps today's "Could not load status" line (no box in the hero card).
5. Writes outside the three forms (approvals, cancel, check-in, notes, goals, policies, shift /
   attendance / encashment requests): after a lost answer, a toast with the D2 words and the
   button stays off (OPS-S3).

## Non-functional dimensions — against the code written

| Dimension | Before → after | Verdict |
|---|---|---|
| Performance | No new request on a normal path; one indexed read only on Try again after a lost leave answer. Measured: JS +22.0 KB raw / +7.3 KB gzipped, CSS +4.4 KB raw / +1.4 KB gzipped — about 8.7 KB more over the wire, more than the 1–3 KB estimated (comments are a large part of the JS). No new file request. On a 3G phone that is roughly 0.2 s more on a first visit, once per release (the files are cached) | degrades slightly (page weight) |
| Security | Tracebacks and 5xx text no longer reach the screen (SEC-4); server message markup goes to an inert `<template>`, not a live element; holiday names parsed by `DOMParser` (inert) | improves |
| Reliability | Every call ends by 15 s; 61 error branches that never ran now run; a lost leave answer cannot become a second request | improves |
| Scalability | No automatic retry anywhere. OPS-S4 timings on `ppj.localhost` (≈370 staff): `get_hr_analytics` 0.18 s, `get_team_scorecard` 0.05 s, `hr_document_compliance` 0.29 s, `get_all_active_employees` 0.02 s, `get_manager_dashboard` failed at 0.07 s (local schema, see above). All far under 15 s | neutral |
| Maintainability | +~580 lines in a 17,650-line file; one failure helper, one send flow for both leave forms. Some callers outside AC-22 now show a toast **and** Frappe's pop-up on a refusal | neutral |
| Data integrity | No duplicate leave; no resend control after a lost expense/advance answer; timed-out writes stay locked | improves |
| Compliance / privacy | Typed reason in page memory only; no storage, URL or log use | improves (slightly) |

## Commands run and results

| Command | Result |
|---|---|
| `git fetch origin dev` (start) | Nothing new |
| `git fetch origin dev` (before commit) | **32 commits came in: slice 066 grooming (20, incl. `a9af0501` correction-test fix) and slice 069 wall chart (12).** Read; no obfuscated code. Rebased: `portal.js` merged by itself (066's `gmReview`/`gmTile`/`gmTag`/`gmBox` lines all present, grooming chip shows inside the phone day block); `check_attendance_strip.js` and `run_dom_tests.js` conflicted — kept both sides (066's `gm*` list + 070's helpers; 069's and 070's tests, count 14) |
| `python scripts/check_app_integrity.py` | 821 checks, OK (after rebase) |
| `node scripts/run_dom_tests.js` (after rebase) | 14 run, 14 pass after one test-wait fix in the 070 test (`24702e57`): click 8, notes 12, correction 37, leave 063 103, tree 19, redesign 74, positions 168 checks, wall chart 183 checks, phone 070 87, next-* suites all pass |
| `node scripts/check_attendance_strip.js` | every case draws cleanly |
| `bench --site test070 run-tests --app alvoraa_portal` (own container, own Redis, own DB copied from test_site; run on the pre-rebase tree) | **Batch 1: 16 tests, OK. Batch 2: 962 tests, 1 failure, 20 skipped.** Batch 3 stopped part-way on the coordinator's word (it had passed `test_attendance_correction` … `test_positions_064` with no failure line) |
| The 1 failure, alone: `--module alvoraa_portal.tests.test_email_logo_175` | Ran 11, 1 failure — fails alone too. **Not 070:** `Website Settings.app_logo` is `/files/their-own-brand.png` in the shared `test_site` database itself (left by some other test; nothing in this repo writes that name), and 070 changes no Python, email template or setting |
| OPS-S4 timings, `ppj.localhost`, best of 3, as an HR manager with 15 reports | `get_hr_analytics` 0.18 s, `get_team_scorecard` 0.05 s, `hr_document_compliance` 0.29 s, `get_all_active_employees` 0.02 s, `get_manager_dashboard` failed at 0.07 s (local schema behind) |
| Browser (Chrome, iframe at 390 / 360 / 1440 on the local copy) | As in the AC table. **Not repeated after the rebase:** Chrome stopped answering while the test run loaded the same container |

## Known gaps and shortcuts

- **Temporary debt:** the Team View and the HR holidays card were not opened in a browser as a
  manager or HR (the local manager data needs the newer schema). Covered by code reading and the
  shared helper. Removed by a browser pass on dev.
- **Temporary debt:** the browser pass was done before the rebase onto 066/069, and the dark
  theme (P4) was checked from the CSS tokens only. Removed by one browser pass after the rebase.
- **Acceptable simplification:** `todayISO()` elsewhere is UTC; only the new holiday filter uses
  the phone's own date (`localToday`). Not changed elsewhere (not this slice's).
- **Intentional trade-off:** a refusal on a call outside the three forms shows Frappe's pop-up
  and, where the caller had one, its own "Failed…" toast too.
- **Existing flaky tests, not 070's:** `portal_correction_test.js` "an incomplete request was
  sent" fails about 1 run in 6 on the untouched base code too (measured); `portal_leave_063_test.js`
  R-35/R-36 depend on a 300 ms timer inside a 400 ms wait.
- **Written down, not done (scope):** four more date boxes have no words line (`le-date`,
  `sr-from/to`, `tn-*`, `tv-from/to`, `pos-p-until`); 01c W1 (branch scope in
  `get_leave_summary`) wants a ticket.

## Subtract pass

Removed: a second message helper for the leave form (it now uses `sendSay`); a tautological test
line; a plan for per-panel failure helpers. Kept the per-call `<template>` sink — without it the
5xx pop-up (AC-47) cannot be stopped.

## Decisions — Surbhi, 25 Oct 2026 ("1 keep, 2 accept")

1. **Late answer after the 15 s message: keep as built.** It replaces the message once, as the approved prototype shows; no time-out ever unlocks a write button (OPS-S3). This supersedes "a late answer is ignored" in the strategy-approval note of 00-impact-analysis.md.
2. **The five undrawn screens above: accepted as built.**
