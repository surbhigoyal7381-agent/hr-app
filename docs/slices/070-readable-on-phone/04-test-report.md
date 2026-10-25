---
slice: 070-readable-on-phone (YouTrack ALV-217)
artifact: 04-test-report
author: hrms-test-automation-engineer
date: 2026-10-25
code tested: slice/070-readable-on-phone at 4c9dd95e (rebased on origin/dev f207e82c; nothing new on origin/dev at 15:50)
status: LOCAL only. No push, no deploy command, no migrate, no docker cp.
---

# 070 · Test report

## Verdict: **Pass with known defects** (no P0, no P1)

- Every AC that can be tested before release has a passing test or a real-browser check.
- **I could not check on local PPJ:** a real leave send, and the Leave page with data. Local
  `ppj.localhost` is behind dev's schema: `apply_leave` and `get_leave_summary` fail there with
  "Table tabAlvoraa Payroll Rule Set doesn't exist". So the lost-answer database check ran
  against the **real server code on the test070 site** (own database), driven from the real
  page (see "Gap 4" below). Not a 070 fault.
- Still open for release: AC-62 (dev check), AC-63 (07 §5 rollback tag), AC-64 (real Android
  phone at "Largest" font) — human or release steps.
- Surbhi's decisions of 25 Oct (late answer replaces the message once; the five undrawn screens
  accepted as built) are what I tested against.

## Where it ran, and who else was there

- Code: the worktree, served by the engineer's own container `hrlocal-070` (mounts this
  worktree). Python runs on site `test070` (own DB `_070phone`, own Redis `hrlocal-070-redis`).
  `test070`'s schema is a copy of `test_site`. `hrlocal-bench` and `test_site` were not used.
  No other run was active in `hrlocal-070` (`pgrep` empty before each run).
- Browser: **Chrome** (the installed one, through Playwright `channel:'chrome'`) against
  `http://127.0.0.1:8070` = `ppj.localhost` on `hrlocal-070`. The Claude-in-Chrome extension
  did not answer (same as the engineer saw), so I used Playwright instead.
- Logins: local demo users Rahul Kumar (PPJ-0058, employee), Sakshi Verma (PPJ-0048, his
  manager, 13 reports), Kamal Gupta (HR Manager). Synthetic `alvoraa.staff@example.com` on
  `test070` for the database check. Nothing real, nothing from production.
- Incoming work: `git fetch` at start and at commit — nothing new on `origin/dev`.
  Another session's uncommitted edits in this worktree (`.claude/context/product-context.md`,
  `ux-learnings.md`, `docs/product/design-benchmark/`) were not staged.
- Clean-up: the one synthetic Leave Application on `test070` was deleted; PPJ-0058 still has
  exactly its 3 leave rows (no write reached `ppj.localhost`).

## Commands run (all today, all read)

| Command | Result |
|---|---|
| `python scripts/check_app_integrity.py` | 821 checks, OK |
| `node scripts/run_dom_tests.js` | **14 run, 0 failed** (phone 070: 87 passed, 0 failed) |
| `node scripts/check_attendance_strip.js` | every case draws cleanly |
| `bench --site test070 run-tests --app alvoraa_portal --module …test_portal_split_034` | Ran 12, OK |
| `… --module …test_panel_source_042` | Ran 7, OK |
| `… --module …test_leave_permissions` (with my 2 new tests) | Ran 12, OK (run twice) |
| Same 2 new tests with the guard switched off in-process (stdin script) | **2 of 2 fail** — proven |
| Playwright + Chrome scripts (in the scratchpad, not committed) | numbers below |

**Not run:** the full `alvoraa_portal` suite (already run once on this branch by the engineer:
batch 1 16 OK; batch 2 962 run, 1 failure `test_email_logo_175` — fails alone too, test_site's
own logo setting; 20 skipped. Batch 3 was stopped part-way). Told not to repeat it.

## New tests (committed)

`alvoraa_portal/alvoraa_portal/tests/test_leave_permissions.py`, 2 tests:

- `test_sec3_ac48_staff_check_with_another_id_reads_only_their_own_leave` — AC-48 says "the
  existing server test still passes", but **no existing test covered a non-HR caller passing
  someone else's `employee_id` to `get_leave_summary`**. Now one does. Fails when the server
  honours the id for anyone.
- `test_sec1_ac39_a_resent_leave_for_the_same_days_is_refused_one_record_stays` — the server
  backstop behind the phone's check. Fails when Frappe HR's overlap check is switched off.

## The four gaps the engineer left

1. **Chrome after the rebase, 390 / 360 / 1440, light.** Home, Attendance (Oct 2026, weekly
   off Thursday), Leave page, Finances (3 tabs), Apply leave pop-up. At 390 and 360: smallest
   text **12 px**, **0** controls under 44 × 44, every field 16 px and ≥ 44 px (textarea ≥ 88),
   **no sideways scroll** (`scrollWidth` = width), no ISO / dd/mm/yyyy / "Sept" / leading-zero
   dates. Side by side with prototype v1 screenshots: same layout and words (colours differ
   only by tenant brand, as the prototype notes). 1440: tokens 11/12/13/15, 8-column table
   with strip, top bar names each page.
2. **Dark theme in a real browser** (Chrome `prefers-color-scheme: dark`, 390): same numbers as
   light. Failure box: amber edge `rgb(224,169,74)` on `rgb(34,30,27)`, heading
   `rgb(240,237,232)` — readable. Chips readable.
3. **Team View / approvals as a manager.** Sakshi (13 reports): Team View **loaded with real
   data** at 390 and 1440, all phone floors met, no failure. HR Manager Kamal: Team View and
   Home got a real **403** from `get_manager_dashboard` / `get_employee_dashboard` (this local
   login seems to have no reach there) — the box and Frappe's own permission pop-up show.
   **Unproven:** an approval tapped from Team View with a pending request (Sakshi has none
   pending locally), and the HR holidays card with data.
4. **Lost leave answer → exactly one Leave Application.** Real page (Rahul's session, 390),
   real Chrome; the two server calls (`apply_leave`, `get_leave_summary`) were routed to the
   **real `hr_api` functions on `test070`** as a synthetic employee:
   - Send → server saved `HR-LAP-2026-00164` (Open) → answer held → at **15.1 s**: "No answer
     from the office. It may have gone through." / "Tap Try again. We check first, so it is
     never sent twice." Button "Try again", focus on it, `role=alert`, values kept.
   - Try again → "Checking…" (disabled) → check found it → toast "Leave application submitted."
     **once**, **0** new `apply_leave` calls. Database: **1 row**.
   - Held answer then delivered late → still **one** toast (AC-33).
   - Forced miss (check returns nothing) → the phone resent → server refused with
     `OverlapError` → database still **1 row**.
   - Offline send: **0** requests, "We could not reach the office. Nothing was sent."

## Other real-browser results

| Check | Result |
|---|---|
| AC-18 / AC-21: attendance read held 18 s | box at **15.0 s**; data replaced it at **18.5 s**, no tap |
| AC-22: offline, open Home, Attendance, Leave, Finances, Team, both request panels (manager and HR) | every panel shows a box; **0** "Loading…" 16 s later |
| AC-23: leave types fail | "We could not load the leave types." + Try again; typed reason kept; Try again loads the list |
| AC-11 / AC-12 in Chrome, Los Angeles and Kolkata | both: "6 Nov 2026", "1 Sep 2026", "" for empty, "Friday, 6 Nov 2026" |
| AC-13 leave cards | "6 Nov 2026", "6 Nov – 7 Nov 2026", "30 Dec 2026 – 2 Jan 2027" |
| AC-14 | "1 Aug 2026 – 31 Aug 2026" |
| AC-53 | tapping a day block opens "What went wrong?" for that day |
| AC-57 (today 25 Oct) | "No more holidays in October."; › "9 Nov Diwali next day (store closed for stock-take)"; All year lists nothing before today |
| AC-50 | after a failed send and reload: form empty; nothing in local/session storage or URL |
| AC-6 at 390 | login, driver, vendor pages: `--fs-base` 13 px, `frame.css` not loaded; check-in keeps its own 17 px (file unchanged) |
| AC-59 | no shadowed element at the right edge on 5 desktop panels |

## Page weight (measured from the committed files, gzip level 5 = nginx)

`portal.js` +22.0 KB raw / **+7.5 KB gzipped**; `frame.css` +4.4 KB / **+1.4 KB**; templates
+0.2 KB. **About 9 KB more over the wire** (engineer: ~8.7 KB; estimate was 1–3 KB). The
portal script is now 256 KB gzipped. Inference: about 0.1–0.2 s more on a 3G first visit,
once per release. P3 — inside the 2.5 s budget as far as this adds, but 3× the estimate.

## Traceability

| Item | Proof | Result |
|---|---|---|
| AC-1 – AC-4 | Chrome 390/360, 4 screens + pop-up, light and dark | Pass |
| AC-5 | Chrome 1440 tokens 11/12/13/15 | Pass |
| AC-6 | Chrome 390 other pages + no diff to `design_system.html` | Pass |
| AC-7 | header controls ≥ 44 in the tap scan; drawn 36 seen in screenshots | Pass |
| AC-8, AC-9 | Chrome (1 Oct "Weekly off", 2 Oct "Gandhi Jayanti", no "Holiday") + jsdom (HTML name as text) | Pass |
| AC-10 | code read + jsdom draw only; no DTC-like holiday list in the browser | Pass (not seen in a browser) |
| AC-11 – AC-16 | Chrome (2 time zones, cards, payslips, date words, text scan) + jsdom | Pass |
| AC-17 – AC-24 | Chrome (offline, 15 s, 5xx, late answer, sweep, leave types) + jsdom (AC-20, AC-24 timers) | Pass |
| AC-25 – AC-31, AC-33, AC-34, AC-37 | jsdom (all) + Chrome for AC-26, 27, 28, 33, 37 | Pass |
| AC-32 | jsdom; server refusal proven by the new Python test. In Chrome my bridge answered at 15 s, so the refusal arrived after the time limit — not a clean browser proof | Pass (jsdom + Python) |
| AC-35 | jsdom | Pass |
| AC-36 | code read: reopening clears the form (Chrome AC-50 shows it empty); "Leave page lists it" not seen — that page fails on local PPJ | Partly proven |
| AC-38 – AC-40 | jsdom (double tap, 3 lost answers → 1 send) + **Chrome + real DB: 1 row** + new Python test | Pass |
| AC-41 – AC-44 | jsdom only | Pass (client). **One Expense Claim / one advance in a real DB: not proven** |
| AC-45 – AC-47 | jsdom (5xx, traceback, 417 text, no Frappe pop-up) | Pass |
| AC-48 | jsdom (no `employee_id` from staff) + **new Python test** | Pass — proven |
| AC-49, AC-51, AC-65 | diff grep: no `@frappe.whitelist`, no new `console.*` / `log_error` in product code, new words through `drT()` | Pass |
| AC-50 | Chrome reload + diff grep | Pass |
| AC-52 – AC-54 | Chrome (31 blocks, ≥ 52 px, named buttons, no strip; desktop table) + jsdom (line 2 words) | Pass. Line 2 with real punches not seen — Rahul has no October punches locally |
| AC-55 – AC-57 | Chrome | Pass |
| AC-58, AC-59 | Chrome 1440 | Pass |
| AC-60 | `test_portal_split_034`, `test_panel_source_042` | Pass |
| AC-61, AC-63 (diff part) | diff: 9 files, no nginx, font, image, patch, DocType JSON | Pass |
| AC-62, AC-63 (07 §5 tag), AC-64 | release / human steps | **Not run** |
| SEC-1 | Chrome + real DB 1 row; Python backstop test | Pass — proven |
| SEC-2 | jsdom (no resend control, one send) | Pass (client); DB count not proven |
| SEC-3 | new Python test + jsdom | Pass — proven |
| SEC-4 | jsdom (traceback never shown) + Chrome 5xx box on the Leave page | Pass |
| SEC-5 | jsdom + Python overlap refusal | Pass |
| PRIV-1 | Chrome reload + diff grep | Pass |
| PRIV-2 | diff grep | Pass |
| OPS-R1 | 034 / 042 tests | Pass |
| OPS-R2 | diff | Pass |
| OPS-R3 / OPS-R4 | jsdom (nothing retried; no expense/advance resend) | Pass |
| OPS-R5 | new Python test | Pass — proven |
| OPS-R6, OPS-R7 | release steps | Not run |
| OPS-R8 | decision for Surbhi (count 499s) | Not a test |
| OPS-S1 | diff | Pass |
| OPS-S2 | gates above all green; R-48 in `portal_leave_063_test.js` goes through the `fetch` stub | Pass |
| OPS-S3 | jsdom ("a timed-out write never unlocks its button") | Pass |
| OPS-S4 | jsdom 16 s stubs; engineer's timings (all < 0.3 s); Team View read for Sakshi answered fast | Pass. Not re-timed by me |
| OPS-S5 | 066's grooming lines kept (engineer); strip check clean | Pass |

## Defects and observations

| # | Level | What | Where / how to see it |
|---|---|---|---|
| D1 | P3 | Leave page failure box is squeezed into a narrow column (~150 px) inside the Leave Balance card on a phone, so the words wrap every 2–3 words. Undrawn screen, accepted as built, but it reads badly | `/hrms-employee` → Leave, at 390, when `get_leave_summary` fails (always on local PPJ today) |
| D2 | P3 | Page weight +9 KB gzipped vs a 1–3 KB estimate | see above |
| O1 | P4 | A refused panel load (403) shows Frappe's pop-up **and** "Something went wrong at the office … tell HR" in the box. Known trade-off in 03 | Kamal (HR) → Team View on local PPJ |
| O2 | P4 | On local PPJ, Home opens with Frappe's "DocType Alvoraa Payroll Rule Set not found" pop-up — local schema, not 070 | any login, local only |

## Human checklist (not automated)

- AC-64: a real Android phone, font size "Largest": Home, Attendance, Apply leave — no sideways
  scroll, no clipped button label.
- On dev after the push (with Surbhi's yes): AC-62 `?v=` changes and the phone `@media` block is
  served; a real leave send and an approval from Team View with a pending request; the HR
  holidays card with data; one expense claim with a dropped answer → one claim in the list.
- AC-63 / OPS-R7: 07 §5 names the previous tag and confirms it exists.

## Subtract pass

Removed from my plan: a Playwright test committed to the repo (a second browser framework —
the jsdom suite already pins the logic; the browser scripts stay in the scratchpad as evidence
only); a separate Python test file (the two tests sit in the existing leave permission class
and reuse its fixtures); a third Python test for three lost answers (jsdom already proves one
send, and the server test proves the backstop).
