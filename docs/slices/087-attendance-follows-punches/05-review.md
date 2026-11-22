---
slice: 087-attendance-follows-punches
artifact: 05-review (step 5, senior architect review)
reviewed: branch slice/087-attendance-follows-punches at 94f22878, diff bad23ce0..94f22878 (48 files, +9,603 / -114), worktree /Users/mac/hr-app/.claude/worktrees/087-attendance-follows-punches
ran on: container alv358-bench, site test_site, apps mounted from worktree alv358-daily-workings at 94f22878 (checked: same SHA, clean)
reviewer: hrms-technofunctional-reviewer, 21 Nov 2026
---

# 087 review

## 1. Verdict

**BLOCK.** A manager or HR person can change what a request does after it is filed, and the "needs the employee's Confirm" flag is never worked out again, so a cut can be approved and paid with no confirmation. That is counsel's DTC condition (ALV-419), and it is broken on a path I ran.

This is advice. Surbhi decides.

**Read these first:**

1. **The worktree moved while I reviewed it.** Three commits landed on this branch after 94f22878: `802ca499` (07 §5), `e469b0e7` (Surbhi's "Undo this change" decision) and `ecf33389` ("HR can undo a disputed approved change, code and tests, not yet run"). I reviewed 94f22878, as briefed. **I did not review `ecf33389`.** It looks aimed at B2 and B3 below, but it has never been run.
2. **Another session was running `test_punch_fix_087` on test_site at the same time** (started 14:46 IST). I started the same module at 14:51, saw the clash, and stopped my run before it reported. **So I have not re-run the 108-test figure in 03 §18. It is unverified by me.** My first probe also locked the test Company row for a few seconds. **That session's run may show one "Lock wait timeout".** That would be caused by me, not by the code.
3. **The 04 test report is out of date.** It covers round 2 (code 694f0b91). It covers none of ALV-418, ALV-419, SEC-7, the manager-additions rule or V5: Confirm, disputes, the before-payroll list and the slip refusal. All the evidence for those is the engineer's own (03 §11 to §18).

## 2. Blockers

### B1 · P1 · The Confirm rule is decided only when a request is created. An edit changes what it does, and nobody is asked

- **Where:** `punch_fix.py:314` (the SEC-4 rule, `if doc.is_new() and ...`) and `punch_fix.py:340-351` (`needs_confirm` is set only when `before is None`). On an edit, `punch_fix.py:356-357` puts `alvoraa_needs_confirm` back to what was stored.
- **Who can edit:** the Employee role has write on Attendance Request (`attendance_request.json`, Employee row, `write: 1`, no owner limit). `manager_scope.py:52-104` gives every manager one User Permission per report, scoped to Attendance Request. HR User and HR Manager have write. **No `has_permission` hook covers Attendance Request** (`hooks.py:638`).
- **Scenario A (I ran it):**
  - A manager files a time-only request for a Held day. It is saved with `needs_confirm = 0`.
  - The manager then saves the same draft with `alvoraa_set_aside` = a machine punch.
  - The save goes through and `needs_confirm` stays 0.
  - HR approves. The punch is set aside.
  - `refuse_slip_while_unconfirmed` does not refuse the slip, before or after approval.
  - Probe output (test_site, code 94f22878): `A needs_confirm at insert: 0` / `A edit as manager: SAVED; set_aside= EMP-CKIN-11-2026-004100 needs_confirm= 0` / `A slip refused before approval: False` / `A approved; aside punch marked: True slip refused after approval: False`.
  - The probe saved with `ignore_permissions=True` as the manager. So it proves that `validate` lets the edit through. The permission half rests on reading the two files above.
- **Scenario B (code read, probe blocked by the lock):** an HR person opens the employee's **own** waiting request in the Desk, changes the time and adds a set-aside. `needs_confirm` stays 0, because the request's owner is the employee. On the employee's day sheet it still reads as their own request, so no Confirm block shows (`day_sheet`: `filed_for = r.owner != session user`).
- **Why it is wrong:** counsel's condition, which Surbhi accepted: HR-filed changes, and any cut or set-aside, need the employee's confirmation before pay is locked. AC-113 says "a manager cannot set a punch aside in 087 (the document refuses it)". That is true on insert only. The project's own SEC-7 test (`test_a_confirm_is_cleared_when_the_filer_changes_what_the_request_says`) saves a set-aside into an HR-filed request in an edit, and it is accepted. **Priority rung 2: a legal obligation.**
- **Smallest fix:** in `validate`, on an edit where a `CONFIRMED_CONTENT` field changed and the session user is neither the employee's login nor Administrator:
  - apply the SEC-4 rule again (no set-aside by anyone but the employee);
  - set `alvoraa_needs_confirm = 1` and clear `confirmed_by/on`.
  - Add one test for each of the two scenarios, and watch each one fail before the fix.

### B2 · P1 · After approval, "Not right" with the employee's own time adds a second punch and does not replace HR's

- **Where:** `punch_fix.py:847-849` → `_replacement` (`punch_fix.py:873-895`). The new request carries only `alvoraa_missing_time`. It sets nothing aside, and `derive(..., [])` counts HR's approved punch.
- **Scenario (code read; my probe of it was stopped by the lock):**
  - The day has 09:00, 12:00 and 18:00. HR's 12:40 is approved, so there are 4 punches and the day is Present.
  - The employee says "Not right, it was 12:50".
  - HR approves that request. The day now has 09:00, 12:00, 12:40, 12:50 and 18:00: five punches, an odd count. So it goes back to Held, or the hours come out wrong.
- **Why it is wrong:** v5 promises "Your own time replaces the one that was sent" (prototype `toast_nr2`, and the build's own toast at `portal.js:6756`). The day would carry both times.
- **Status:** the spec added after my base (AC-124, "so the day never carries both times") and `ecf33389` address this. That code is **not run and not reviewed**. The branch at 94f22878 cannot ship with this path.

### B3 · P1 · At 94f22878 a disputed approved change holds the employee's salary slip, and nobody can release it in 087

- **Where:** `_unconfirmed_filters` (`punch_fix.py:689-697`) counts a disputed request. `day_sheet` turns Confirm off once it is disputed (`can_confirm` needs `confirm_state == "not_yet"`, `punch_fix.py:501`). `withdraw_filed` refuses an approved change (D-2). `record_register_signature` throws. So nothing in 087 lifts the hold.
- **Effect:** Payroll Entry skips that slip without stopping. `payroll_entry.py:1687-1690` catches the `ValidationError` for each slip and lists it as unsubmitted. So one employee goes unpaid through the portal that month (Grace uses Salary Slips).
- **Status:** the spec called this "Open (for Surbhi)". She decided at 14:51 (`e469b0e7`: HR undo), and the code is `ecf33389`, not run. Same point as B2: 94f22878 does not carry the fix.

## 3. Majors

### M1 · P2 · The filing window blocks "Not right" on an older approved change, and then the employee has no way out

- `refuse_own_day_outside_window` (`attendance_correction.py`, slice 087 hunk) exempts only `alvoraa_for_held_day`. The replacement for an approved change is on a day that is no longer Held, so it gets 0 and the window applies.
- The monthly limit exempts `alvoraa_replaces` (`held_day.py:206`). The window does not.
- A time is required when one was sent (`punch_fix.py:842-843`), so the employee cannot fall back to a dispute.
- **Scenario:** the window is 5 working days. HR's addition for the 3rd is approved, and the employee looks at it on the 20th. "Not right" with a time is refused with the window sentence, and the savepoint rolls back. All they can do is Confirm something wrong, or leave the slip held.
- Code read, not run.
- **Fix:** exempt `alvoraa_replaces` in the window, the same way as in the limit.

### M2 · P2 · The "deploy before migrate" trap the impact analysis named is only partly handled

- 00 §4.4 says the new columns are guarded. Two readers are not:
  - `held_day.enforce_monthly_limit` filters on `alvoraa_for_held_day` and `alvoraa_replaces` (`held_day.py:229`) with no `has_column`.
  - `punch_fix.card_context` reads `alvoraa_fix_added_request` and `alvoraa_fix_aside_request` with no `columns_ready()`. `to_review` calls it for every waiting request that carries a time, and 085's held requests carry one.
- **Scenario:** the new image is up and the migrate has not reached a site yet (5 Nov: hours, on DTC). At a company with a monthly limit, every employee's own request fails with "Unknown column". HR's review queue fails the same way while any 085 held request is waiting. The "old preview" fallback in `to_review` exists for exactly this case, but it is never reached.
- **Fix:** guard both readers with `columns_ready()`.
- Code read, not run.

### M3 · P2 · Nothing tests the slip refusal against a real Salary Slip

- `test_the_salary_slip_is_refused_while_...` calls `refuse_slip_while_unconfirmed(SimpleNamespace(...))` directly. The wiring test only checks that the hook string is in `frappe.get_hooks`.
- No test submits a real Salary Slip, or runs a Payroll Entry, with an unconfirmed change.
- I read that Payroll Entry calls `submit()` per slip and catches the refusal. So the gate is reached, but HR sees only "unsubmitted", not the sentence. **Inferred, not run.**
- I found no write of `docstatus` on Salary Slip in `alvoraa_portal` or the vendored `hrms`. So I see no bypass.
- **Fix:** one test that submits a real draft slip, and one through `submit_salary_slips_for_employees`.

## 4. Minors (P3, ship tracked) and nits

- **m1 · `withdraw_filed` has no own-record lock** (`punch_fix.py:785-796`). An HR person can withdraw a pending change filed about themselves. `decide` refuses that (`refuse_own_decision`). It is a decline by another name. The risk is low, because HR can only file additions.
- **m2 · Scope read into Python** (`before_payroll`, `punch_fix.py:775-778`): the scoped Employee names are read, then sent back as `IN (...)`. nfr-budget §2 says the scope stays in the database. There is also one query per set-aside name and per employee in `unconfirmed_changes`. Both are bounded (100 / 20 / 1000).
- **m3 · Silent caps.** The slip refusal reads 20 changes at most but says "{n} changes are not confirmed" with n ≤ 20. The before-payroll list stops at 100. Say "first 20".
- **m4 · Parity with v5 (needs her yes, or build as drawn):** `own_t` "You sent your own time, {0} · Waiting for HR" is not built (the build shows v4's "This replaces the 12:40 that HR sent"). `cf_truth_ma` carries the approval date, and the build does not. "The button tries the slip" is not built (declared in 01b).
- **m5 · Arrear path.** An HR-filed change on a Held day that is already on a final slip is paid as an arrear next month. It never holds a slip, because its day is outside the next slip's period. So it is paid with no confirmation. Inferred. Needs Surbhi's rule.
- **m6 · Test name claims more than it tests:** `test_the_draft_slip_is_refreshed_and_a_failure_does_not_undo_the_approval` never makes the refresh fail.
- **m7 · One open request per day is not locked.** `validate_request_overlap` reads without a lock, so two sends at the same moment could both be saved. The client's send guard makes this unlikely.
- **m8 · Process.** Two agents worked in this worktree and on one test site at once, against usage-discipline §6. The branch is also 2 commits behind `origin/dev` (`b0048ee7`, `b3844e58`: `auth.py` and the joiner sign-out files). They do not overlap with this slice. A rebase is needed before any push.

## 5. Acceptance criteria (the ones I walked; not all 125)

| AC | Result | Evidence |
|---|---|---|
| AC-44 / no new `ignore_permissions` | met | Counted 0 added lines in all 15 changed non-test `.py` files (proven, per-file grep) |
| AC-61 one door: Desk, REST, import | met | `before_submit` needs `flags.punch_fix_decided`. A client cannot send `flags`: Frappe drops it (`base_document.py` RESERVED_KEYWORDS line 1601, `update()` line 292; `api/v1.py:54`; `client.py:313`). Proven by reading Frappe in alv358-bench |
| AC-60/62 seen token | met | `decide` works the token out again after `for_update` (`attendance_correction.py`, decide hunk) |
| AC-64 / ALV-411 POST only | met for new writes | `send`, `confirm`, `withdraw_filed` are POST. `day_sheet` and `before_payroll` are reads (GET), which is acceptable |
| ALV-412 / company and branch scope | met where read | `before_submit` and `withdraw_filed` use `employee_in_scope`. `before_payroll` uses `_scope_conditions` (fails closed for an HR login with no scope, `attendance_correction.py:335`). The report "Punch fixes this month" scopes by company only, so branch HR sees counts for the whole company (counts only, no names) |
| AC-80 exactly once | met (read) | `decide` and `confirm` both lock the request row (`for_update`). `apply` locks the day row |
| AC-101/102 reason on every request | met (read) | `send`, the `raise_correction` held path and `raise_for_report` all refuse a blank reason |
| AC-113 manager additions decided on the server | **partial** | Right at insert (session, `_filed_by_hr`). Not worked out again on edit: **B1** |
| AC-114 SEC-7 clear on edit | met as written | `punch_fix.py:361-362`. It clears a Confirm already given. It does not cover an edit that turns a no-confirm request into a cut (B1) |
| AC-115 approval never waits | met | No `refuse_unconfirmed` in the hooks |
| AC-116 Not right before or after approval | **partial** | Before approval: right, one savepoint. After approval with a time: **B2**. Old day: **M1** |
| AC-117 Withdraw pending only, HR in scope | met (m1 aside) | `punch_fix.py:789-793` |
| AC-118 before-payroll list in scope | met | as above |
| AC-119 slip refused while unconfirmed | met in the function, **not proven end to end** | M3. Disputed changes: **B3** |
| AC-120 Workings column | met | `salary_components_and_workings.py` hunk |
| AC-121 printed-reason hint | met | 3 places in `portal.js`, one line in `hi.csv`. Whether Frappe loads `hi.csv` for the portal: not checked |
| Seam `record_register_signature` | met | Throws "Recording a signed register is not available yet." (`punch_fix.py:799-804`) |

## 6. NFR and the seven dimensions

| Dimension | Impact analysis said | What I found |
|---|---|---|
| Performance | neutral; 50 cards ≤ 1.5 s | The engineer measured 222 queries and 0.14 s. Not re-measured by me. `before_payroll` scope IN-list (m2) |
| Security | improves | Mostly true: one door, three own-day locks, no new bypass. **Degraded on one point: the Confirm flag can be got round by an edit (B1)** |
| Reliability | improves, with the migrate trap handled | **Trap only partly handled (M2).** One transaction plus a fail-closed engine check: true by reading |
| Scalability | neutral | true. Slip gate: one small query per slip at submit |
| Maintainability | degrades slightly | true. `punch_fix.py` is 1,021 lines and grew again in `ecf33389`. 088 guard code is already spread over 5 functions (see §8) |
| Data integrity | improves | **Not on the after-approval replacement path (B2)** |
| Compliance / privacy | improves | Logs carry ids only (read: `confirm`, `apply`, `guard_marks`). **ALV-419 partial (B1)** |

## 7. Compliance

| Obligation | Mechanism | Test | Result |
|---|---|---|---|
| ALV-418 reason on every request | refusals in `send`, `raise_correction`, `raise_for_report` | `ReasonOnEveryRequest` (3), break-tested per 03 §11 | discharged (not re-run by me) |
| ALV-419 confirmation before pay is locked | `needs_confirm` at insert, slip `before_submit`, Workings column | V5 tests (direct function calls) | **partial**: the edit path (B1), disputes (B3), no real slip test (M3), arrear path (m5) |
| An HR-added punch is shown as such (wage record) | `alvoraa_fix_added_request`, punch `owner` = approver, "Added by HR" | `test_the_added_punch_belongs_to_the_approver_not_administrator` | discharged |
| Audit, before and after | `alvoraa_fix_before/after`; set-aside who and when | Approval tests | discharged |
| Nothing deleted | `guard_marks` on validate and on_trash | `Marks` tests, break-tested | discharged |
| Counsel's approval for main | release gate Q1 | none | open, by design |

## 8. What to delete

- **`_signed_field()` and its five reads of 088's field** (`day_sheet`, `card_context`, `card`, `_unconfirmed_filters`, `_own_the_confirm_fields`). Surbhi approved one seam, `record_register_signature`. These reads are code for a field that does not exist yet ("we will need it later"), and each one calls `get_meta`. 088 can add them with its field. Removing them changes nothing today.
- **`held_day.validate_missing_time`** is now kept only for a site that has not migrated (`held_day.py:242-247`). It is a compatibility shim. Optional: delete it once M2 is guarded properly.
- I found nothing else that could go: no new DocType, app, queue or cache.

## 9. What was done well

- The one door cannot be forged. The approval flag lives in `doc.flags`, which Frappe strips from every client body, so the Desk, REST and imports really are refused.
- The punch is inserted as the approver with no permission bypass. That makes `checkin_has_permission` a real third own-day lock, not a comment.
- The preview and the approval share one function (`outcome`), and the approval fails closed if the read-back differs.
- The subclass is small. It changes three stock methods for punch fixes only and calls `super()` for everything else.
- Each break test is recorded with the failure it produced (03 §6, §11, §17, §18).

## 10. Confidence

- **Proven:** B1 scenario A (probe output above). The Frappe `flags` stripping. The per-file `ignore_permissions` count. Payroll Entry's per-slip catch. The bench running 94f22878.
- **Inferred from code:** B1 scenario B, B2, B3, M1, M2, m1 to m7. My probe of B and B2 hit a lock timeout from the other session's run. A follow-up probe is queued for when that run ends, and its result is in the hand-off message, not here.
- **Not checked:** the 108-test figure (not re-run, site busy). Screens in a browser. `ecf33389` and the two doc commits. Any tenant's Custom DocPerm. Whether DTC or Grace has a monthly limit or a filing window set (this decides how often M1 and M2 bite).

### Must-know questions

1. **B1.** Should an edit by anyone but the employee always ask for the employee's Confirm again, or should such edits be refused? Either one closes B1. I am ranking it as a Blocker until the edit path is closed.
2. **m5.** Does an HR-filed change paid as an arrear need the employee's confirmation first? I am ranking it P3 until Surbhi says.

**Subtract pass:** I removed three findings I could not trace to a failure: a "flags" bypass (Frappe strips it), a Payroll Entry batch abort (each slip is caught), and a held_day 085 condition I thought was broken (the arrear path is 085's own). Nothing else removed.

---

## Re-review, fix round 1 (68b4a544, 21 Nov 2026)

**Verdict: SHIP WITH FIXES.** All three blockers are closed in the code. One small gap is left from M2: a single unguarded read before the migrate. It is a one-line fix and should land before dev.

**How I checked.** I read `git diff 94f22878..68b4a544` in the 087 worktree, at HEAD 68b4a544. I ran no code; the coordinator asked me to keep off alv358-bench. The test figures come from the coordinator's file, `/private/tmp/claude-501/-Users-mac-hr-app/67b461e9-84fe-425b-b761-79423d0b7215/scratchpad/087-fixround1-tests.txt`:
- `test_punch_fix_087`: 127 OK.
- `test_held_day_085`: 6 failures. `test_held_gaps_085`: 3 failures.
- Every other module listed: OK.

The file gives counts only, with no test names. **So I could not confirm that the 9 failures are the known backfill ones.** That figure is not checked.

### My findings, one by one

| Finding | Status | Evidence |
|---|---|---|
| **B1**: the Confirm rule skipped on an edit | **Closed, as Surbhi worded it** | `punch_fix.py:366-373` works the flag out again on every save. An edit by anyone but the employee or Administrator that adds a set-aside sets `needs_confirm = 1` and clears any Confirm. Tests: `test_b1_a_managers_time_only_filing_then_a_set_aside_edit_holds_the_slip` (my scenario A). Moving a request to another employee is now refused for everyone (`punch_fix.py:309-313`). **Left over, P3, for Surbhi:** an HR edit that only moves the *time* on the employee's own request still needs no Confirm. Her decision says "adds a cut or set-aside", and `test_b1_..._or_a_time_only_edit_does_not_ask_again` locks that in. Moving an In time later is a cut in hours. She should say whether that counts |
| **B2**: the replacement after approval left both times | **Closed** | `apply` (`punch_fix.py:1000-1007`) takes the original change back first, through `_reverse`, before the replacement is judged. The card leaves out the original's added punch (`punch_fix.py:663-666`). Test: `test_approving_the_employees_own_time_reverses_the_change_it_replaces` (counted times 09:00, 12:00, 12:50, 18:00; nothing deleted) |
| **B3**: a disputed change held the slip for ever | **Closed** | `undo_change` (`punch_fix.py:850-881`): POST only, HR in scope, not on their own day, a reason required, disputed approved changes only, once only. It re-judges the day, the engine must agree, and the slip is freed (`_unconfirmed_filters` skips undone requests, `punch_fix.py:711`). Seven `Undo` tests |
| **M1**: the filing window blocked "Not right" | **Closed** | `attendance_correction.py:1624` exempts `alvoraa_replaces`. Test `test_m1_not_right_is_outside_the_filing_window` |
| **M2**: new columns read before the migrate | **Partial** | The monthly limit is guarded (`held_day.py:231-235`), and so is the request read in `card_context`. **Still open:** the Employee Checkin read in `card_context` asks for `alvoraa_fix_added_request` and `alvoraa_fix_aside_request` with no guard (`punch_fix.py:591`). `to_review` calls it for every waiting request that carries a time (`attendance_correction.py:1949`). The new test patches `has_column` for Attendance Request columns only, so it could never have shown this. **Fix:** return `{}` at the top of `card_context` when `not columns_ready()`. `to_review` then falls back to 085's `held_preview` |
| **M3**: no real Salary Slip test | **Closed** | `test_held_slip_085.SlipRefusedWhileUnconfirmed.test_a_real_submit_is_refused_then_allowed` makes a real `slip.submit()`: refused, then allowed once confirmed. Payroll Entry is still checked by reading only (`payroll_entry.py:1687-1690`) |
| **Delete**: `_signed_field` | **Closed** | Removed with all its reads. Only the `record_register_signature` docstring still names 088's field, which is correct |
| m1 `withdraw_filed` had no own-day lock | **Closed** | `refuse_own_decision` added (`punch_fix.py:821`) |

### New things the fixes brought in

- **n1 · P3 · The arrears rule holds every later slip, not only the one that carries the arrears.** `refuse_slip_while_unconfirmed` (`punch_fix.py:761-764`) also counts approved, unconfirmed changes on any earlier day that is on a final slip. So the hold lasts until the employee confirms, slip after slip. Surbhi's words were "the next salary slip that carries the arrears". It is safe, because it errs toward holding, but it is wider than she said. A test calls the function on a SimpleNamespace, not on a real slip.
- **n2 · P3 · Undoing a change on a day that was Held leaves the old release record behind.** `undo_change` writes the status through `_write_day`, but `alvoraa_release_how/by/on` still say "HR decision". The 085 box on the day sheet can then still say "Held, now Present. Pay restored." after the undo.
- **n3 · P4 · A replacement stores the wrong In/Out until it is approved.** `_replacement` works the kind out while HR's punch still counts (`derive(..., [])`), so `alvoraa_missing_log` and `reason` may read Out where approval will write In. `apply` works it out again correctly. Only the stored label and the "says" line are wrong until then.
- **n4 · P3 · Two more scope lists are read into Python and sent back as `IN (...)`:** in the report (`access.permitted_employees()`) and in `before_payroll`. nfr-budget §2. Both are bounded by one tenant's headcount.
- **Logging:** the punch-fix lines now go to `security_logger().warning`, which is the ALV-391 fix. The lines I read carry ids only.

### What is still needed before dev

1. Guard `card_context` (M2, one line), with a test that also patches the Employee Checkin columns.
2. Surbhi's word on n1 and on the B1 time-only edit. Neither blocks a push to dev.
