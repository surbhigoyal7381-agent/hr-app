---
slice: 087-attendance-follows-punches
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-11-21
reviewed: git diff bad23ce0..94f22878 (branch slice/087-attendance-follows-punches)
risk tier: 1
status: recommendations only. Surbhi decides; I approve nothing.
---

# 087 · Security review

**I wrote 01c, the requirements this review checks against (lesson 6).** I can say whether
the code meets them. I cannot judge whether they were the right requirements. A second
reader should check that part.

**What I read.** I read the code at commit `94f22878`, copied out with `git show` (scratch
copy, not the live worktree). **While I was reviewing, another session moved this worktree.**
HEAD is now `e469b0e7` ("HR can undo a disputed approved change", which adds
`punch_fix.undo_change`), and `punch_fix.py`, `portal.js` and `test_punch_fix_087.py` have
edits that are not committed. **None of that is reviewed here.** `undo_change` is a new write
endpoint that edits punches, so it needs its own review.

**What I ran.** I ran no tests. The engineer's bench is in use, and the rule is one agent per
worktree. I ran one read-only check: `frappe/utils/logger.py` inside the `alv358-bench`
container (line 12, see F2).

## 0 · Bad news first

1. **Blocker, P1 (blocks the release).** Changing the `employee` field on a draft request
   gets past two controls. Every check that decides who may file the request, and whether it
   needs the employee's Confirm, runs only when the request is first created. Details in F1.
   This is **verified in code, not run**.
2. **Major, P2.** The rule says "an Administrator change to a marked punch is logged". In
   practice that log line goes nowhere. The same is true of every `punch_fix` log line (F2).
3. There is **no P0**. Nothing here leaks across tenants, no secret or statutory ID reaches a
   log, and no personal data reaches a model. The branch has not been pushed.

## 1 · SEC and PRIV, met or not

All file:line references are at `94f22878`. `pf` = `alvoraa_portal/alvoraa_portal/punch_fix.py`,
`ac` = `attendance_correction.py`, `T` = `tests/test_punch_fix_087.py`.

| Item | Verdict | Mechanism (verified in code) | Test |
|---|---|---|---|
| SEC-1 one door, on what HR saw | **Met** | `pf:676-677` refuses a submit unless `decide` set the flag. `ac:2045` compares the token (request `modified` + the day's punch ids, `pf:277-286`). The Inbox shows Review, not Approve (`next-inbox.js`). Each punch's source is named (`pf:_source`) | `test_desk_submit_is_refused…` (break-tested, 03 §6), `test_decide_without_the_token_or_with_a_stale_one…`, `test_an_edit_of_the_draft…makes_the_token_stale` |
| SEC-2 POST only | **Met** | New writes are POST only: `send` `pf:389`, `confirm` `pf:807`, `withdraw_filed` `pf:784`. `decide`, `raise_*` and `withdraw` were already POST only (ALV-411). The new GET endpoints only read: `day_sheet` `pf:455`, `before_payroll` `pf:766` | Registry checks for `send` (`T:560`) and `confirm` (`T:1212`). **No test for `withdraw_filed`** (F5) |
| SEC-3 HR in scope, never own day | **Met** | `pf:679-684`: HR role, `employee_in_scope` (company, then branch, fails closed: `access.py:334`), leaver refused through `day_state`. Own-day and raiser hooks stay in place (`hooks.py:250-254`). The punch is inserted as the approver with no permission bypass | `T:565, 582` (the insert is its own lock), `T:593, 599, 611, 619, 625`, `test_a_leaver_cannot_be_approved` |
| SEC-4 own day only, gates count | **Partial** | Set-aside ids are checked on every save and again at approval (`pf:365-378`, `pf:913`). Limit and window key on the server flag (`held_day.py:206`, `ac:1623`). **The rule on who may raise runs only on insert (`pf:314` `doc.is_new()`): F1** | `T:221, 284, 307` (break-tested) |
| SEC-5 unfixable days refused | **Met** | `day_state` runs at raise (`pf:318`), at submit (`pf:684`) and in `apply` (`pf:910-912`). A Held day on a final slip is allowed, by Surbhi's decision of 21 Nov | `T:234-258, 439-459` |
| SEC-6 marks only by approval | **Partial** | `guard_marks` on validate and on trash (`pf:998`, `hooks.py:297-299`). **The Administrator log line goes nowhere: F2** | `T:639, 653` (break-tested). `T:670` replaces the logger with a stand-in and checks only that it was called |
| SEC-7 (01c) exactly once | **Met** | `decide` locks the request (`ac:1976`). `apply` locks the day row (`pf:910`). The added punch is linked inside the same transaction. Cancel is refused (`pf:898`) | `T:466, 474, 492, 419`, proof file AC-81 both orders |
| SEC-7 (086 review, AC-114) a Confirm covers what was seen | **Partial** | `pf:361` clears the Confirm when the content changes. **`CONFIRMED_CONTENT` (`pf:51`) leaves out `employee`: F1** | `T:1153, 1181` (break-tested) |
| SEC-8 pay reads one list | **Met** | Filter in `payroll_rules_apply._punches`. `counting_only` in the month view, analytics, team days and grooming. The Salary Workings figures come from the engine through `month_summary` (Inference) | `T:691` (break-tested), `T:702, 709, 735` |
| PRIV-1 collect only this | **Met** | `send` takes four values. The kind (In or Out) is worked out on the server. No file, photo or location. Counsel (ALV-418) made the reason required | proof `test_send_takes_exactly_what_the_screen_sends`, `T:177` |
| PRIV-2 no new reader | **Met, as amended** | No `photo`, latitude or longitude key in any 087 response. No cache. **No new `ignore_permissions` in source** (diff grep: hits only in tests). Refusals and log lines carry ids only (`pf:836, 862, 971, 1017`). Per Q3 and ALV-418, HR and the manager can read the reason | `T:746, 836, 131`. `T:800` checks Error Log only, not `security.log` |
| PRIV-3 rebuildable a year later | **Met** | `alvoraa_fix_before`/`after` (`pf:968`). Who and when for confirm, dispute and withdraw are kept on the request. A Version row on a set-aside. Attendance Request has `track_changes: 1` (stock json:210), so a Confirm cleared by an edit can still be traced | `T:365` |
| PRIV-4 dry run copies nothing | **Met (script)** | `scripts/087_dry_run.py` prints counts and Attendance names only. **It has not been run on ppj.dev** (03 §6) | none |

**Brief checks:**

- **The employee can confirm only their own request.** `pf:823` checks this. `_me()` returns
  Active employees only. A request the employee filed themselves is refused (`pf:826`).
  Test: `T:1117`.
- **The reason text never reaches a log line or an error message.** Verified in code. The
  refusal sentences are fixed strings.
- **The Salary Slip refusal (`pf:738-753`) names only that slip's own employee**
  (`unconfirmed_changes([doc.employee])`). It gives the day, the time added or set aside, and
  the filer's name and kind. It gives no reason text. In a bulk Payroll Entry the
  ValidationError is caught and the slip goes on the not-submitted list
  (`payroll_entry.py:1689`), so no Error Log row is written.
- **Scope on the new endpoints.** `withdraw_filed` and `before_payroll` use `employee_in_scope`
  and `_scope_conditions`, both company then branch (ALV-412). An HR login with no company and
  no branch gets nobody (`ac:335-336`). The tests cover another company only, not another
  branch (F5).
- **The photo is not built here.** The diff has no upload, attach or photo code.
  `record_register_signature` is not whitelisted and always refuses (`pf:799`).

## 2 · Findings

### F1 · Blocker, P1 · Changing the employee on a draft gets past the raise rule and the Confirm

- **Verified in code, not run.** The `employee` field is editable on a draft (stock json: not
  read-only, not set-only-once). HR roles hold write. Tenant Property Setters not checked.
- **Who and how.** HR User A, in scope for employees X and Y, edits the draft in the Desk or
  through REST.
- **Case 1.** A files a change for X. X presses Confirm. A changes `employee` to Y.
  `_own_the_confirm_fields` puts the stored `alvoraa_confirmed_on` back (`pf:356`). The change
  check at `pf:361` does not cover `employee` (`pf:51`). Result: Y's request reads
  "confirmed", Y never confirmed it, and Y's salary slip is not held.
- **Case 2.** A files a request for A's own day. It is A's own request, so
  `needs_confirm = 0` (`pf:349`). A then changes `employee` to Y, and can edit the set-aside
  ids to Y's punches (`_check_aside` re-checks them against Y and passes). The rule "only the
  employee's own login raises an ordinary-day fix or a set-aside" runs only `if doc.is_new()`
  (`pf:314`). A second HR person, B, approves it. Result: an HR-filed set-aside on Y's day
  that needs no confirmation from Y, ever.
- **What it breaks.** Counsel's condition ALV-419 (HR-filed changes and cuts need the
  employee's confirmation before pay is locked), and SEC-4.
- **What limits it.** It needs one HR insider plus a second HR person to approve. The card
  names the filer, and a Version row records the edit.
- **Smallest fix.** In `punch_fix.validate`, refuse a change of `employee` on a request that
  already exists. Refuse, rather than clear: a request moved to another person is a new
  request. Test: confirm as X, edit the employee to Y, and the save is refused. Break it,
  watch that test fail, then restore it.
- **To demonstrate it I would need** a free bench with test_site and about 10 minutes.

### F2 · Major, P2 · "It is logged" is false for every `punch_fix` log line

- **Where.** `frappe.logger("alvoraa_portal").info(...)` at `pf:836, 862, 971, 991, 1017`.
- **Why it goes nowhere.** Frappe's default level is ERROR off a dev server
  (`frappe/utils/logger.py:12`, read in the `alv358-bench` container). This is the ALV-391
  pattern, which this repo has already paid for once. The approval and confirm events can
  still be rebuilt from database fields, so those lines are a nice-to-have.
- **What it breaks.** SEC-6's Administrator exception ("every such change must be logged")
  is not met. All that remains is a Version row (Employee Checkin `track_changes` not checked
  on any tenant) or a Deleted Document row (Inference).
- **The test cannot catch it.** `T:670` replaces the logger with a stand-in and checks only
  that it was called.
- **Fix.** Use `access.security_logger().warning(...)` at `pf:1017`, with the same ids. Make
  `T:670` read the real handler's output.

### F3 · Minor, P3 · "Punch fixes this month" is scoped by company, not branch

- `punch_fixes_this_month.py:25` uses `permitted_companies()` only. A store's HR person sees
  the counts for the whole company.
- It shows counts only: no names and no times. But it is wider than the ALV-412 rule. The
  fix is to count over `permitted_employee_filters()`.

### F4 · Minor, P3 · `withdraw_filed` has no own-record refusal

- HR person B can withdraw a pending change that another HR person filed about B's own day
  (`pf:785-796`). `decide` refuses the same person (SEC-9).
- The harm is small: it is a pending change, and withdrawing it only removes something not
  yet approved. Adding `access.refuse_own_decision` keeps the rule the same everywhere.

### F5 · Minor, P4 · Test gaps

- No POST-only registry test for `withdraw_filed`.
- No branch-scope (ALV-412) test for `before_payroll` or `withdraw_filed`.
- `T:800` does not search `security.log` for the reason text.

## 3 · Worries (not yet findings)

- **A leaver's final slip can be blocked for good.** `_me()` filters on Active, so a leaver
  cannot confirm. At `94f22878`, HR cannot withdraw an approved change. So an unconfirmed
  HR-filed change blocks the full-and-final slip until slice 088's register exists. This
  fails safe for the control, but it may delay final pay. **That is a question for counsel,
  not for me.**
- **An employee's "Not right" sets the request to Declined but leaves it as a draft.** I did
  not find a before_submit hook that stops a Desk submit of a Declined ordinary request. That
  gap is older than 087, but 087 adds a new way to reach it.
- **POST only does not help if the session has no CSRF token.** `frappe/auth.py:87` skips the
  check when the session has no saved token. I did not check whether the ESS page always
  creates one. SameSite=Lax cookies probably cover a cross-site POST. Not checked.
- **`confirm` lets an employee test whether a request name exists.** A real name gets "not
  about you"; a wrong one gets "does not exist". P4.

## 4 · Compliance verification

| Obligation | State | Source and date |
|---|---|---|
| Counsel, ALV-418: a reason on every request | Met (`pf:408`, `ac:1214-1217`, `ac:2489-2492`) | counsel in writing, 21 Nov 2026, relayed by Surbhi (spec) |
| Counsel, ALV-419: HR-filed changes and cuts confirmed before pay is locked | **Partial: F1** | same |
| DPDP, CERT-In | No new outbound flow, no model, no new collection beyond the reason | baseline, not re-verified today |

## 5 · Residual risk (proposed. Owner: Surbhi. Nothing is accepted until she says so)

| Risk | Kind | What removes it |
|---|---|---|
| F1 | **dangerous debt: escalate now** | the one-line refusal plus a test, before dev |
| F2 | temporary debt | `security_logger` at `pf:1017` |
| Two HR people approve each other's days (A6, from 01c) | intentional trade-off | detection only (§7 of 01c) |
| A leaver's final slip blocked | open question | counsel, then 088 |
| `undo_change` and the uncommitted edits | not reviewed | a re-review of `94f22878..e469b0e7` plus whatever is committed next |

## 6 · Subtract pass

Removed: a restatement of the 01c abuse cases, and a separate "how I read" list (now folded
into the header).
