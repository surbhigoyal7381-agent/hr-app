---
slice: 070-readable-on-phone (ALV-217)
artifact: 06-security-review.md
author: hrms-security-privacy-engineer
date: 2026-10-25
reviewed: origin/dev...HEAD at f5b2a1ef (6 commits; portal.js, frame.css, 3 templates, 1 Python test file, 2 JS test files, scripts)
inputs: 01c, 03-implementation-notes.md, 04-test-report.md, installed Frappe 16.33.1 and jQuery 3.7.0 source in container hrlocal-070s
---

# 070 · Security review

**Conflict of interest, said first:** I wrote the requirements in 01c. I did not write the code.
The techno-functional reviewer should check that 01c asked for the right things, not only that
the code meets them.

## Verdict: **Pass. No Blocker, no Major.** Two Minor findings, one note.

No P0. No P1. No server code changed: the only `.py` change is two new tests. No new
`@frappe.whitelist`, no new `ignore_permissions`, no new route, no new stored copy of anything.

## Requirements

| ID | Status | Mechanism in the diff | Proof |
|---|---|---|---|
| SEC-1 | **Met** | `lsSend` (portal.js:6282-6341): `LS.busy` locks the button while Sending… / Checking…; after a lost answer `LS.maybeSent` forces a read of `get_leave_summary` before any resend (6327-6340). A late answer counts once (`live()`, `LS.done`). | Chrome + real `hr_api` on test070: lost answer → Try again → **1 row** (04 Gap 4). Server backstop: new `test_sec1_ac39_…` (test_leave_permissions.py:111-120), shown to fail with the guard off. |
| SEC-2 | **Met (client); DB count not proven** | `submitExpenseClaim` (6983-7041) and `submitAdvanceRequest` (7623-7665): after timeout / network / 5xx the submit button is hidden or stays locked; only Close. Offline (nothing sent) is the only Try again. No timer calls `api()` or `gpFetch` again. | jsdom suite (04: AC-41–44). One claim / one advance in a real DB: **not proven** — on the human checklist for dev. |
| SEC-3 | **Met**, one edge (M1) | No change to `hr_api.py`. The check calls `get_leave_summary` with `employee_id` only when `LP.subject` is set (6285, 6329). Non-HR path ignores the id and reads `_get_employee()`, which filters `status: "Active"` (hr_api.py:2309-2312, 299-307 — **Verified in code**). | New `test_sec3_ac48_…` (test_leave_permissions.py:100-110): staff passing another id gets their own record and no applications. jsdom: staff check body is `{}`. |
| SEC-4 | **Met** | `gpErr` (10644-10656) no longer reads `r.exc` or `statusText`; on anything but a refusal it drops even `_server_messages` and uses a fixed sentence (`callWords`, 27-31). `api()` (42-80) relays server messages only on a refusal (`fail`, line 47) or a 200 — never on a 5xx — and diverts Frappe's own pop-up into a detached `<template>` (`error_msg`, line 56). `failBox` and `sendSay` print only fixed, escaped words. No code in portal.js reads `.exc` for display, `.exception`, `_debug_messages`, `statusText` or `responseText` (grep: 0 hits; line 61 only tests `r.exc` for truth). | jsdom: 500 with a traceback in `exc` → no "Traceback", no table name, no 5xx message on the page; 0 Frappe pop-ups on a 5xx (portal_phone_070_test.js:173-181, 279-283). Chrome: 5xx box on the Leave page. |
| SEC-5 | **Met** | A refusal (4xx with a message) clears `maybeSent`, shows the server's words via `pfShowErr` (textContent) and never resends (6299-6305). A refused check during Checking… is treated as "still unknown" and never sends blindly (6339). | jsdom 417 → message unchanged; Python overlap refusal (SEC-1 test). |
| PRIV-1 | **Met** | Typed values stay in the DOM fields. | Diff grep for `localStorage`, `sessionStorage`, `indexedDB`, `history.pushState/replaceState`, `location.hash/search`: **0 new hits** (only old hit is the sidebar pin, portal.js:19381). Chrome: reload after a failed send → empty form, nothing in storage or URL (04 AC-50). |
| PRIV-2 | **Met** | — | Diff grep for `console.`: **0 new hits**. No `log_error` added. |

**What must exist for SEC-1 to be observable:** an Open or Approved Leave Application with the
same type and dates among the person's 10 newest (`get_leave_summary` limit 10, newest first).
A just-saved record is always the newest, so the check can see it.

## Findings

| # | Level | Finding |
|---|---|---|
| M1 | Minor · P3 | **The check can read a different person than the send.** `laSearchEmployee` (portal.js:6059-6060) empties `la-behalf-employee` but leaves `LP.subject` set. *An HR user picks employee A, then starts a new search and submits without picking:* `apply_leave` goes for the HR user, but after a lost answer the check reads A's list. No new data is seen (HR just read A, and the server still scopes A). The harm is to correctness: if A has a leave with the same type and dates, the phone says "submitted" for a send that may not have saved. Otherwise the server's overlap check still stops a duplicate. Fix: take `who` from the same value sent as `on_behalf_of`, or clear `LP.subject` in `laSearchEmployee`. One line. Owner: hrms-fullstack-engineer. |
| M2 | Minor · P4 | **A code comment overclaims.** portal.js:55 says markup written into the `<template>` is inert. Frappe's `process_response` calls `$(error_msg).html(array)`, which jQuery 3.7.0 turns into `append()`, and that parses HTML strings in a div inside the live document (**Verified in installed source**: jquery.js 4732-4760, 6172; website.js 166-167). So it is not inert. **No new exposure**: before 070, Frappe passed the same text to `msgprint`, which also renders it as HTML. Fix the comment so nobody relies on it. |
| N1 | Note | Refusal messages from Frappe still show unchanged, including the overlap message that names the employee ID and Leave Application ID. They name only the caller's own record, or one HR may act for. `pfShowErr` and `toast` use `textContent`, so nothing in them runs. This is the 01c design, not new. |

## Worries (not findings)

- **W1 (from 01c, outside 070, still open):** `get_leave_summary` scopes HR by company only;
  `apply_leave` also scopes by branch. I could not check whether any tenant has branch-limited HR
  users, or whether a YouTrack ticket was raised for it.

## What I could not check

- One Expense Claim / one advance in a real database after a lost answer (SEC-2). Needs the dev
  check on the human list in 04.
- Whether dev or production has `allow_error_traceback` on. It does not change SEC-4 (the code no
  longer reads `exc`), but it decides how much a 5xx carries to the browser console, which Frappe
  itself prints (website.js:173-186, unchanged by 070).

## Residual risk — needs a named person and a date

| Risk | Kind | Needs |
|---|---|---|
| SEC-2 not proven against a real database | Temporary debt — removed by the dev check | Surbhi to accept for local, and to run or delegate the dev check before main |
| N1: raw Frappe refusal text with record IDs stays on screen | Intentional trade-off (01c) | Surbhi's name and date in this table |
| W1: branch scope gap in `get_leave_summary` | Existing, not 070 | Surbhi: raise a YouTrack ticket or accept with a date |
| M1 | Temporary debt — removed by a one-line fix | Fix before push, or Surbhi accepts with a date |

Accepted by: _____ · Date: _____

## Subtract pass

Removed: a re-statement of each AC already in 04; a finding on buttons staying faded after a
lost approval (usability, not security); a finding on the 9 KB page weight (DevOps owns it).
