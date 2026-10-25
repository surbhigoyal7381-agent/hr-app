---
slice: 070-readable-on-phone (YouTrack ALV-217)
artifact: 05-review
author: hrms-technofunctional-reviewer
date: 2026-10-25
reviewed: origin/dev...HEAD (f5b2a1ef) - code 3402386a, bebbca79, 24702e57; tests f5b2a1ef
status: advice. Surbhi decides whether the slice moves to dev.
---

# 070 · Senior architect review

## 1 · Verdict: **SHIP WITH FIXES**

Reason: the slice delivers the brief and matches the prototype, but two places can still
cause a double write after the new 15-second message. That is exactly the risk the brief
named ("Try again must not create a second leave application").

**What I ran and what I did not:**

- **Proven (ran, 25 Oct):** `node alvoraa_portal/tests/portal_phone_070_test.js` - 87 passed, 0 failed.
  `node scripts/run_dom_tests.js` - 14 run, 0 failed. `python scripts/check_app_integrity.py` - 821 checks, OK.
  `git fetch origin dev` - nothing new; no merge commits in the range.
- **Proven (read):** Frappe v16.33.1 `website/js/website.js` in container `hrlocal-070`.
  jQuery's `.always` runs before `statusCode[200]`, and `error` is never called. So the
  new `api()` design rests on true facts.
- **Not checked by me:** a real browser, the phone sizes, the visual match with the prototype,
  and the Python suite. I rely on 04's Chrome runs for those. I compared the built wording
  with the prototype file by text search only.

## 2 · Blockers

None.

## 3 · Majors

### M1 · P2 · A leave Try again while the first send is still running can file two leave requests

- **Where:** `portal.js` `lsSend`, the `send()` / check path (about lines 6318-6342);
  server `hr_api.py:2475-2503` (`apply_leave`: insert, then commit, with no lock).
- **Scenario:** the server is slow (month end, a lock). The send takes 20 s.
  → At 15 s the phone shows "It may have gone through" and **Try again** is live.
  → At 16 s the worker taps it. The check reads `get_leave_summary`. The first request has
  not committed yet, so nothing is found. → The phone sends `apply_leave` again.
  → Frappe HR's overlap check in the second request reads only committed rows. It cannot see
  the first insert, which is still open. → **Two Open Leave Applications for the same days.**
- **Why it is wrong:** SEC-1 and the brief's risk line say this must never happen. The test
  engineer's proof (04, gap 4) is one after the other: the first send had already saved. The
  "both still running" case was not tested.
- **Label:** Inferred from the code. Not reproduced. It needs a send slower than 15 s.
- **Smallest fix:** keep the timed-out request (`e.late`). While it has not finished, Try
  again only checks. If the check finds nothing, say "Still no answer from the office" and
  do **not** send. Send again only after that request has failed. This is about 5 lines in `lsSend`.

### M2 · P2 · OPS-S3 is only partly met: about 20 other writes now unlock their button at 15 s

- **Where:** `gpFetch` write callers that 070 did not guard. Examples:
  `assign_person` (`portal.js` around 2003-2028: `btn.disabled = false` in the `catch`),
  `data_review_confirm` (around 8626: `go.disabled = false`), plus `post_job`, `save_position`,
  `create_goal` / `update_goal`, `submit_goal_update`, `set_goal_progress`,
  `save_self_assessment`, `approve_goal_update`, `create_checkin`, `set_org_setting`
  and `submit_upward_feedback`.
- **Scenario:** an HR manager assigns a person to a position, and the server takes 16 s.
  → Before 070, the button stayed off until the answer came. → Now `gpFetch` rejects at 15 s
  with "We could not reach the office." The `catch` turns the button back on. → She taps again
  while the first call is still running. → Two assignments, or two goals.
- **Why it is wrong:** the approved strategy made OPS-S3 binding: "a time-out never re-enables
  a write button for a blind resend". The words also say "could not reach" when the call
  probably did reach the office. 070 creates this path: before 15 s, nothing failed.
- **Who meets it:** HR and managers. Positions, Goals and Data review are not frontline screens.
- **Label:** Proven by reading those `catch` blocks. Not run.
- **Smallest fix:** add the same one-line guard used on the 23 `api()` writes
  (`if (mayHaveGone(e)) { sayMayHaveGone(); return; }`) to these `catch` blocks. If Surbhi
  does not want that scope, she should accept the risk in writing.

## 4 · Minors

- **m1 · P3 · The OPS-S3 test does not test the real code.** `portal_phone_070_test.js:325-328`
  writes its own error handler and then checks that handler. Delete all 23 real guards and
  this test still passes. Fix: send one real write, for example `submitShiftRequest` or
  `actionLeave`, through a 16 s stub. (Proven by reading.)
- **m2 · P3 · After a lost answer, the 20 `api()` writes explain it only in a 3-second toast.**
  `toast()` removes itself after 3000 ms. After that the button stays dead, with no words.
  On **Check In**, the main daily action, the button stays off until the page is reloaded.
  Keeping it locked is right (DTC counts punches, so a second punch would flip IN/OUT).
  But two sentences in 3 s is too short for the phone user this slice is for. Surbhi accepted
  this screen as built (undrawn screen 5). I flag only the 3 s. A cheap fix: keep `err`
  toasts on screen longer.
- **m3 · P3 · D1 (from 04):** on a phone, the Leave page failure box is squeezed to about 150 px.
  Accepted as built, but it reads badly on the page most likely to fail today.
- **m4 · P3 · Page weight:** about 9 KB more gzipped against an estimate of 1-3 KB. Much of it
  is comments. There is no KB budget in `nfr-budget.md`, and the 2.5 s 3G budget is not at
  risk (+0.1-0.2 s on a first visit only). Inferred, not measured on a phone.
- **Nits (P4):** in `api()`, a late HTTP-200 answer that carries `exc` after a time-out calls
  the error callback a second time. `callback` does not check `failed` (rare: Frappe sends
  `exc` with 4xx/5xx). The comment "markup in a `<template>` is inert" says too much: jQuery
  first reads the markup into a live-document `div`. This is not new exposure, because
  `relay()` shows the same text in `msgprint`. `startClock` still writes to the deleted `#live-date`.

## 5 · AC verification

| ACs | Status | Evidence |
|---|---|---|
| AC-1 – AC-7 (phone sizes, desktop unchanged, shared design system untouched) | Met | 04 Chrome 390/360/1440, light and dark. I read the `frame.css` diff: one `@media` block, and `design_system.html` is not in the diff (proven) |
| AC-8 – AC-10 (Weekly off, holiday names) | Met; AC-10 not seen in a browser | jsdom + Chrome (04) |
| AC-11 – AC-16 (one date format) | Met | `fmtDate` is built from the ISO parts (read). 04 checked two time zones |
| AC-17 – AC-24 (every load ends) | Met | Ran: 87/87. Read: `failBox`, no automatic retry |
| AC-25 – AC-31, AC-33 – AC-37 (leave send states) | Met, **except the race in M1** | jsdom + Chrome + one row in the real DB (04). AC-36 partly proven (04) |
| AC-32 (refusal at the top of the form) | Met | jsdom + Python overlap test |
| AC-38 – AC-40 (one send) | **Partial** | Proven for a double tap and for sends one after another. Not for a send still running (M1) |
| AC-41 – AC-44 (expense, advance) | Met (client) | Read: no resend control after a lost answer. One record in the real DB: **not proven** |
| AC-45 – AC-47 (no traceback, no 5xx text) | Met | Read: `gpErr` drops `exc` and the status text. `api()` does not relay messages on a 5xx |
| AC-48 – AC-51 | Met | New Python test, proven to fail when the guard is off (04) |
| AC-52 – AC-59 | Met | Chrome (04). Line 2 with real punches not seen |
| AC-60, AC-61, AC-65 | Met | Diff: no new file, font, image or nginx change. New words go through `drT()` |
| AC-62 – AC-64 | Not run | Release steps and a real Android phone |

## 5a · NFRs, before and after

| Dimension | Impact analysis said | Code shows | Finding |
|---|---|---|---|
| Performance | neutral (4-6 KB raw) | +26 KB raw, about 9 KB gzipped. No new request on a normal path | Slightly worse (m4). The analysis missed this, and 03/04 say so honestly |
| Security | improves | `exc` and 5xx text no longer shown. No new endpoint or argument | Agreed |
| Reliability | improves | 61 error branches run for the first time; every call ends | Agreed, **but** the new time-out opens two double-write paths (M1, M2) |
| Scalability | neutral | No automatic retry | Agreed |
| Maintainability | neutral | +580 lines in a 17,650-line file; one `failBox`, one `lsSend` | Agreed |
| Data integrity | improves | Sends one after another: yes. Sends still running: no | **Claimed "improves"; it is partly worse for ~20 gpFetch writes (M2)** |
| Compliance / privacy | improves slightly | No storage, URL or log use | Agreed |

## 5b · Compliance (SEC / PRIV / OPS)

| Item | Mechanism | Test | Result |
|---|---|---|---|
| SEC-1 no duplicate leave | Check before resend + Frappe HR overlap check | jsdom, Chrome, Python backstop | **Partial** (M1) |
| SEC-2 expense/advance not resent | Close only, no resend | jsdom | Discharged (client); one record in DB not proven |
| SEC-3 `employee_id` only for HR on-behalf | `LP.subject` | New Python test | Discharged |
| SEC-4 no traceback | `gpErr`, 5xx not relayed | jsdom | Discharged |
| SEC-5 refusals never resent | `kind === "refused"` path | jsdom | Discharged |
| PRIV-1 / PRIV-2 | Page memory only; no new logging | Diff grep, Chrome reload | Discharged |
| OPS-R1 – R5 | No new file; no retry | 034/042 tests, jsdom, Python | Discharged |
| OPS-S2, S4, S5 | Stub moved; 16 s tests; 066 lines kept | Ran: pass | Discharged |
| **OPS-S3** time-out never unlocks a write | Guard on 23 `api()` writes + 3 forms | jsdom, but hollow (m1) | **Partial** (M2, m1) |
| OPS-R6 – R8, AC-62 – 64 | Release steps | - | Not run |

## 6 · What to delete

- The dead `#live-date` lines in `startClock`. The element no longer exists.
- Long comment blocks in `portal.js`. They are about half of the +7.5 KB gzipped. Optional.
- Nothing structural: no new DocType, setting, flag, file or dependency was added. The rung
  ("new code, client side only") is right, and every cheaper rung was rightly rejected.

## 7 · What was done well

- One fix in `api()` turns on 61 error branches that never ran. The cheapest possible route.
- The leave check reuses `get_leave_summary` unchanged. No new endpoint, and no new reader of anyone's data.
- `gpErr` stops showing tracebacks to HR (SEC-4) and keeps real server refusals.
- The test engineer's two Python tests were run with the guard switched off and failed. That proves they test something.
- 03 and 04 report the page-weight miss and the local-schema gaps openly.

## 8 · Confidence

- **High** on M1 and M2 as code paths (read end to end). **Medium** on how often they happen
  in real use: both need a write slower than 15 s.
- **Not checked by me:** the browser, the visual match with the prototype, Python tests,
  production timings. The four unproven items in 04 still stand: an approval from Team View
  with a request pending, the HR holidays card with data, a real Android phone at "Largest",
  and one Expense Claim / Advance in a real DB after a lost answer.

## Subtract pass

Removed from this review: a finding about stale leave previews racing (it existed before 070);
a finding about a session expiry showing "Something went wrong" (it existed before 070); a
finding on the inert-template wording raised above P4 (no new exposure).

---

# Round 2 — fixes 92fc3a35 (+ notes 5a477d0f), diff f5b2a1ef..HEAD

## Verdict: **SHIP** (ready to present for the dev-push decision; not permission to push)

Both Majors are closed. What is left is P3 or P4, and none of it can cause a double save today.

**Ran (25 Oct):** `node scripts/run_dom_tests.js` — 14 run, 0 failed (phone 070: 93 passed).
`check_app_integrity.py` — OK. `git fetch origin dev` — nothing new. **Not run by me:**
Chrome and the bench tests. The notes say they were run; I did not repeat them.

## What closed

| Round 1 item | Status | Evidence |
|---|---|---|
| M1 leave double send | **Closed** | `lsSend`: a time-out sets `LS.inFlight`. While it is set, Try again checks and then says "Still no answer". It never sends (`portal.js` around 6340-6348). It resends only after the first request fails. Test: held 17 s, Try again at 15.3 s, then exactly 1 `apply_leave` (proven, ran) |
| M2 gpFetch saves unlock at 15 s | **Closed for every save today** | See the verb check below |
| m1 hollow OPS-S3 test | Closed | The test now taps the real attendance-request button (the notes say 7 checks fail without the guards; I did not repeat that) |
| m2 3-second toast | Closed | `sayMayHaveGone(r, button)` adds a lasting `role=alert` line beside the locked button. Check In passes its own button |
| D1 squeezed box | Closed (CSS read; Chrome per notes) | `.leave-rings > .fail{grid-column:1 / -1}` |
| Security: stale person picked for the check | Closed | The check uses `args.on_behalf_of`, the id actually sent. A new search clears `LP.subject` |
| "Inert" comment, dead `#live-date` | Closed | Read |

## The M2 change (writes skip the 15 s stop): judged

- **Is the verb list complete today? Yes, proven.** I extracted every method name `gpFetch`
  is called with in `portal.js`: literal names and the wrappers `pf`, `acApi`, `aiApi`, `GM`,
  plus the two variable names in `actionProgressApproval` and the grooming `call`. I tested
  each one against `WRITE_CALL`. Every save is matched, all 21 literal names and all 51 `pf`
  saves. Every read starts with get/list/search/my/… and is not matched.
- **One false match (P3):** `to_review` is in the list, but `attendance_correction.to_review`
  is a read (`frappe.get_list`, no write; read at `attendance_correction.py:1451`). So the
  reviewer queue on Attendance has lost its 15 s end again. Fix: drop `to_review` from the regex.
- **Signal drop during an exempt save (Inferred, not run).** No signal *before* the tap still
  fails at once with nothing sent. A connection that breaks mid-request makes `fetch` reject,
  and the caller shows its old error, as before 070. A connection that goes silent, with no
  packets and no reset, can leave `fetch` waiting for minutes. The button stays on
  "Saving…" with no words. That is exactly the behaviour before 070, so nothing got worse. It
  differs from the approved E2 ("every other call ends at 15 s") in the safe direction.
  Surbhi should note it. **P3.**
- **A future save with a verb not on the list (P3).** It would end at 15 s and could unlock
  its button again: the M2 bug, back without anyone seeing it. Nothing tests for it. The
  smallest structural fix is to **flip the default**: list the read verbs (get, list, search,
  my, …) and treat every other name as a write. A missed name would then only wait, as
  before 070. It could never save twice. That is a one-line regex change, with no extra test needed.
  If the team keeps the current shape, add one jsdom check that fails when a `gpFetch` name
  outside a read prefix is not matched.
- **Two mechanisms for one rule (P4, accepted trade-off):** `api()` saves use 23 guards in each
  callback; `gpFetch` saves use the name rule. The notes say so. It is fine for now.

## Small leftovers (P4, backlog)

- If someone closes and reopens the leave form while a timed-out send is still running,
  `lsReset` clears `inFlight`, so a fresh send can still race the old one. This needs a
  15 s+ send and a deliberate re-entry of the same dates.
- `api()` finds the tapped button through `window.event`. After an `await` (for example
  `uploadMyDocument`) there is no event, so it falls back to the toast. That is safe; it is just less helpful.

## Subtract pass (round 2)

Removed from this section: a note on the `pf` read list (all correct) and a note on Firefox
`window.event` support (supported since FF 66; no finding).
