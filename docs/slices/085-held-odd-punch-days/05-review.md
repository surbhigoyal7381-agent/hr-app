---
slice: 085-held-odd-punch-days (ALV-392)
artifact: 05-review (step 5, senior architect review)
author: hrms-technofunctional-reviewer
date: 2026-11-20
read: worktree /Users/mac/hr-app/.claude/worktrees/085-held-odd-punch-days, branch slice/085-held-odd-punch-days. Diff 101fd29b..208de542 (the brief's range). HEAD moved to f36129a3 while I read; that commit is the DevOps agent's 07 §5 and touches only 07-devops-inputs.md.
ran on: container alv085-bench2, site test_site. It mounts .claude/worktrees/085-fix-tmp at 1abc9fd7, and that tree's app folders match 208de542 exactly (`git diff --stat` came back empty).
status: advice only. Surbhi decides whether this ships.
---

# 085 review: BLOCK

**Verdict: BLOCK. A held day is paid again the moment its salary slip is submitted. The slice's main promise, "Held is not paid", only holds on draft slips.**

I ran this myself. I did not take it from the handoff (details in B-1). Every other finding below is P2 or lower, apart from the rebase (B-2), which the DevOps agent also found.

## 1 · Blockers

### B-1 (P1, Blocker) · Submitting a slip pays the held days again. Proven by a run.

- **The setup:** one employee at a company with no pay rule set. Two Held days in October. `consider_unmarked_attendance_as` = Present.
- **What happens:**
  - The draft slip says 29 payment days.
  - Saving the draft again still says 29.
  - **After `slip.submit()`, the slip says 31 payment days, net pay 30,000.00 and absent days 0.** I ran this in-process on alv085-bench2 / test_site and rolled it back. The script is `/private/tmp/claude-501/-Users-mac-hr-app/6c11a767-ce60-411e-be29-4d558086e1b8/scratchpad/submit_probe.py`.
- **Why it happens:**
  - Frappe's `_submit` sets `docstatus = 1` and then runs `validate` (`frappe/model/document.py`, `run_before_save_methods`, read in the container).
  - The stock `SalarySlip.validate` works out the payment days again from scratch (`salary_slip.py:230-234`). That count does not know about Held (`:824`).
  - Our hook then returns straight away, because of `if doc.docstatus != 0` (`held_day.py:458`).
  - So every slip that goes through Payroll Entry, or is submitted by hand, pays every Held day. The Salary Register reads the submitted slip's `payment_days` and `absent_days` (`salary_register.py:50`), so it shows those days as paid too.
- **Why no test caught it:**
  - The real-slip tests only ever look at **draft** slips.
  - The AC-18 test marks a slip final with `set_value("docstatus", 1)`, so `validate` never runs.
  - No test in this slice could ever have shown this fault.
- **Where it came from:** the impact analysis designed it this way. It says the hook "returns at once for a submitted slip" (`00-impact-analysis.md:69`), and it marks data integrity as "improves".
- **The smallest fix:**
  - Skip only cancelled slips (`docstatus == 2`), so the hook also runs during the submit's `validate`. `validate` does not run on cancel or on update-after-submit, so a slip that is already final is still never touched.
  - Add one test that calls a real `slip.submit()` and checks that payment days are still 2 lower.
  - Change the AC-18 test to use a real submit as well.

### B-2 (P1) · The branch no longer merges with `dev`. Proven.

- I ran `git fetch` and then `git merge-tree HEAD origin/dev`. `origin/dev` is now at 15c716f6, 12 commits past the base. All 12 are by `surbhigoyal7381-agent`: slice 084, ALV-391, ALV-353 and an agent-docs commit.
- There are conflicts in `hooks.py`, `hr_api.py` and `portal.js`. This matches 07 §5 (OPS-30).
- One conflict changes behaviour. 084 adds an Attendance Request `validate` called `refuse_own_day_outside_window`, and 085 adds `validate_missing_time` to the same hook. **AC-69 says a held day must be exempt from 084's window. Nothing in 085 does that yet, because 084 was not on the base.** After the rebase, an employee's request for an old held day will be refused unless the 084 check skips requests that carry `alvoraa_missing_time`.
- The fix: rebase, add that one exemption with a test, then re-run the 085 and 084 modules.

## 2 · Majors

### M-1 (P2) · The R1/R2 split does not stand alone yet. Proven from the commit list.

- Release 1 is commits `d0f775c6` and `43b12bd0`.
- Release 1's own-punch line broke `test_punch_rights_alv332`. The fix for that test is `1f83c44f`, which comes after all the R2 commits.
- So shipping Release 1 on its own ships a red test.
- The fix: move `1f83c44f` straight after `43b12bd0` during the rebase.

### M-2 (P2) · HR logins with no company lose the correction screens on every tenant. Release precondition, not counted.

- `_scope_conditions` now returns "match nothing" for an HR role with no company and no branch (`attendance_correction.py:330-335`).
- The engineer says so (03 §0.5), and the runbook asks for a count per tenant.
- That count has not been taken for dev, DTC, Grace, aahr or PPJ (**not checked** by anyone).
- Until it is taken and fixed, Release 1 can lock real HR users out of approving attendance on the day it lands.

### M-3 (P2) · Held days on a weekly off or holiday can be charged twice as hard as stock charges them. Inferred from code, not run.

- `held_dates` finds holidays only from `Employee.holiday_list` (`held_day.py:487-492`).
- Stock finds them from the **Holiday List Assignment** for the employee, then for the company (`hrms/utils/holiday_list.py:96-116`). That is the pattern DTC and Grace use.
- **The scenario:**
  - An employee has an empty or stale `Employee.holiday_list` and an assigned list.
  - They punch once on a Sunday, and the day is Held.
  - Stock has already left Sunday out of the working days.
  - Our hook takes one more day off.
- The fix: call the stock `get_holiday_list_for_employee`.

### M-4 (P2, provisional; needs an answer) · The monthly limit also refuses HR, while its own message tells the employee to "ask HR".

- `enforce_monthly_limit` runs on every insert. It checks only the employee's own roles and designation, never who is filing (`held_day.py:206-239`).
- So HR, filing a fourth ordinary request for that employee, gets "You have used your 3 requests this month... For another day, ask HR." That is a dead end.
- **The question:** did Grace's script let HR file beyond the limit? If yes, this is P2 and needs an exemption for HR who file. If no, it is P3 and only the wording needs to change.

### M-5 (P2) · About 16 screen ACs have no proof at all, and the screens were never opened.

The test report §5 says so. Here is what I found by reading the code against the prototype:

- **Not built:** the prototype's line "This replaces the old hidden rule of 3 requests a month." The parity table marked it "Same".
- **Built, although the gate cut it:** the second "Sent to HR" tag (`portal.js`, `ac-tag wait`).
- **Not met:** AC-30 asks for two things that are missing. One is the "Your time is saved on this phone" wording. The other is a timeout path that checks the server first. Today the toast shows only the server's message.
- **Wrong promise on the Save button:** it says "N days will be held". But switching the hold on only holds days marked **after** that. Past days are held only by the Grace November backfill. At any other company, or in any later month, that sentence is false.
- The fix: a human walks the screens at 360 px before release, or Surbhi accepts the gap in writing.

## 3 · Minors (P3)

- **N1. The backfill's dry run prints one total.** The kill criterion (AC-63) needs 86 one-punch days that were Absent and 80 days that were Present. Print the count by previous status.
- **N1 (cont.). The backfill's audit comment** does not record a run id or the person who ran it. The session is set to Administrator. AC-59 asks for both.
- **N2. A multi-day or ordinary request that covers a Held day** goes down stock's path to Present (`note_held_day` returns early). The release fields are never written, so the employee's sheet cannot say how the day was released. PRIV-3 is only partly met.
- **N3. Queries inside loops.**
  - `to_review` calls `preview()` for each row, about 6 queries each, up to 50 rows.
  - `month()` adds one query for each held or released day.
  - Both are bounded, but neither is flat as headcount grows. Not measured against the 500 ms budget.
- **N4. `guard_company_settings` checks the exempt list on every Company save.** If one of those roles is later deleted, nobody can save the Company, accounts included.
- **N5. The AC-62 test patches the function it is meant to prove.** It cannot fail for the right reason (test report §3).
- **Nit.** An HR person who cancels their own attendance sees "You cannot decide your own request" (that is the wording of `refuse_own_decision`).

## 4 · AC verification (grouped; "test" means a test I read, not one I re-ran unless stated)

| AC | Verdict | Evidence |
|---|---|---|
| 1, 2 | met / operator step | Property Setter in `held_day.after_migrate`, wired to both hook lists |
| 3, 4 | **partial: drafts only** | `test_held_slip_085` real drafts; **fails on submit (B-1, I ran it)** |
| 5 | partial | reader table 03 §6; Salary Register wrong after B-1; Employee CTC Break Up reads the salary structure, not attendance (not a reader); `leave_rules.py` not checked |
| 6 | partial | `held_dates` in payslip payload; wording follows Q4 |
| 7 | met | HLD plus a ninth colour; sheet test |
| 8 | partial | list JS chip, never seen in a browser |
| 9, 10, 11, 13 | met | held_gaps and held_day tests; the hold runs at first `validate`, so the row is written once |
| 12 | met in code, no test | skips when `leave_application` is set (`held_day.py:261`) |
| 14, 15 | met | stock `get_attendance` thresholds; three-time fixture |
| 16, 17 | met / partial | real draft re-priced; error path tested on the machine path only |
| 18 | met for the release; the slip side is broken by B-1 | test uses `set_value` docstatus |
| 19 | partial | decline path unchanged |
| 20, 21, 23 | met / partial | `files_as_machine` break-tested by the tester; flag check on the punch itself |
| 22 | not tested | |
| 24-31 | partial / none | code read only; AC-28 payload tested; AC-30 not met |
| 32, 33 | partial / met | |
| 34, 35 | met for the computed line | button text not tested |
| 37-39 | partial | Save text promise wrong (M-5) |
| 40, 41, 43 | met | tests; HR-filer question M-4 |
| 42 | partial | Sales Executive's odd day still Held is not asserted |
| 44 | partial | operator step |
| 45-51, 53 | met | doors tests (16) |
| 52, 54 | operator step / not tested | |
| 55-57 | partial | 1 new `ignore_permissions`, 0 `allow_guest` (I grepped the diff); 010 ceilings 32/45 run |
| 58-63 | met on a test site | 86/80 not run on Grace data; N1 |
| 64-67 | written, not run | runbook |
| 68 | met in code | manager window skipped for held |
| 69 | **not met after rebase** | B-2 |

## 5 · NFRs and the seven dimensions

| Dimension | Impact analysis said | What the code shows |
|---|---|---|
| Performance | neutral | Hooks: neutral (one cached Company read; 1-2 queries per machine punch; 3 per slip save). HR queue and month view add looped queries (N3). Not measured |
| Security | improves | Agree. Own-day, raiser and fail-open scope doors closed. One justified `ignore_permissions`. Parameterised raw SQL in `held_count`. Lockout risk M-2 |
| Reliability | neutral | Agree for punches (wrapped, savepoints). Slip refresh in its own try |
| Scalability | neutral | Agree for hooks; N3 grows with queue size. Backfill is N+1 per row, acceptable for a one-off |
| Maintainability | slightly worse | Agree. Plus one vendored hrms edit (D-3, approved) and a fourth Company `validate` |
| Data integrity | improves | **Disagree: worse until B-1 is fixed.** A submitted slip disagrees with its own Held rows. M-3 can over-deduct |
| Compliance / privacy | improves | Partly. Logs carry ids only. PRIV-3 gap (N2). The wage-law risk is Surbhi's accepted R1 |

## 5b · Compliance (spec §13)

| Obligation | Mechanism | Test | State |
|---|---|---|---|
| Accuracy of pay (DPDP accuracy, wage records) | `deduct_held_days` | draft-only tests | **not discharged** (B-1) |
| Person sees state and how it was released (PRIV-3) | three release fields, day sheet | AC-15, AC-20 | partial (N2, screens unwalked) |
| Time only, no reason collected (PRIV-2) | `_held_request_fields`, form | AC-28 payload | discharged; no log-body assertion |
| No new reader (PRIV-1) | scope unchanged, integer count | partial | partial |
| Safeguards: own-day and raiser doors (SEC-2, 3) | `attendance_doors.py` | 16 tests | discharged |
| Backfill undo and audit (SEC-7) | undo file, Comment | end-to-end on a test site | partial (N1) |

## 6 · What to delete

Nothing big. The slice stays on rungs 2 and 4, with no new DocType, no new app and no new dependency.

- **Delete:** the second "Sent to HR" tag. The gate cut it, and the sentence in the sheet already says the same thing.
- **Keep:** `alvoraa_release_on`. `modified` is not a safe stand-in, because every later write changes it.

## 7 · What was done well

- `files_as_machine` decides by who filed the punch, never by `device_id`. It also leaves `is_machine_account` alone, because the geofence code reads that function.
- The release uses the Shift Type's own `get_attendance`, and the HR card's preview calls the same function. So the card cannot promise something the approval does not do.
- The backfill is careful: Grace only, dry run first, the undo list on disk before any change, it stops if the count has changed, and it skips final slips.

## 8 · Confidence

- **Proven:**
  - B-1, by my own run.
  - B-2, by my own fetch and merge-tree.
  - The `ignore_permissions` and `allow_guest` counts, by grep.
  - Frappe's submit flow, which I read in the container.
- **Inferred:** M-1, M-3, M-4, N2 and N3, from reading the code.
- **Not checked:**
  - Any screen in a browser.
  - Grace's Payroll Settings: `payroll_based_on`, and the Shift Type thresholds. If both thresholds are 0, every release becomes Present whatever time is sent.
  - The per-tenant count of HR logins with no company.
  - `leave_rules.py`.
  - The full suite. I re-ran no suite. I relied on 04 and 04b for those counts, and did not repeat them.

**Subtract pass:** I removed three draft findings. Each one turned out to be handled already:
- the repeat-scan hours, because `punch_dedupe` flags repeat scans as `skip_auto_attendance`;
- the Company write right, because stock gives HR Manager write on Company;
- the Employee CTC Break Up report, because it does not read attendance.

---

# Re-review, 20 Nov 2026: SHIP WITH FIXES

**Verdict: SHIP WITH FIXES. Both blockers are closed, and I proved B-1 myself. What is left is three counts nobody has taken on the live tenants. Each one decides whether real HR users or real punches are refused on release day. None of them needs code.**

**Where I looked:** this worktree, branch `slice/085-held-odd-punch-days` at 148cb639. `15c716f6` is an ancestor (proven with `git merge-base --is-ancestor`). I read the fix diff `f95d6faf..148cb639` and the scoping code in full, plus `03` §14-16. The test engineer was running suites on alv085-bench2 (test_held_day_085, then test_attendance_correction). My first probe there hit a lock wait, so I ran the probe on **alv085-bench** instead. That container mounts this worktree at 148cb639 and has its own database (`_0d985145…`, not bench2's `_310633…`). The probe rolls back in `finally`.

## Findings from round one

| Finding | State | Evidence |
|---|---|---|
| B-1 submit pays Held days | **Closed. Proven.** | Probe on alv085-bench: draft 29.0, re-saved 29.0, **after a real `submit()`: 29.0 payment days, net 28,064.52, absent 2.0**. Before the fix the same script gave 31 / 30,000 / 0. `held_day.py:489` now skips only `docstatus == 2`. The test `SubmitKeepsTheHold` does a real submit and could fail. |
| B-2 rebase and AC-69 | **Closed.** Code read, not run by me | `hooks.py`: Attendance Request `validate` is now one list, and `validate_missing_time` runs before 084's window. `attendance_correction.py:1597` returns early on a missing time. A time on a day that is not Held is refused first, so the exemption cannot be abused. |
| M-1 R1/R2 split | **Closed by decision.** | There is one release now, so commit order no longer matters. |
| M-2 HR with no company | **Open, P2. Not checked.** | It is wider now: see S-1 below. |
| M-3 holidays | **Closed.** Code read | `_holidays` makes the same two calls as stock `SalarySlip.get_holidays_for_employee` (`salary_slip.py:748-749`, read in the container), with the same default date (today). |
| M-4 HR and the monthly limit | **Closed by decision.** Test read | `_filed_by_hr` decides by the filer, at insert and when counting. The test covers the employee, HR and a manager on behalf, with controls. |
| M-5 screens | **Partly closed.** | The tag is gone, the AC-30 lost-answer path is built, and the count promise is gone. The 63 DOM tests were not re-run by me. **The screens have still not been opened at 360 px.** That still needs a human walk, or Surbhi's acceptance in writing. |

`scripts/check_app_integrity.py` at HEAD: **984 checks, OK** (I ran it; 03 says 978 because that run came before the last commits).

## The new scoping, and release-day risk

- **S-1 (P2). The R4/R5 scope switches on for every tenant on release day, whatever the hold switch says. The runbook's pre-push count misses one group.**
  - The runbook counts HR logins with *neither* a Company User Permission *nor* an Employee record.
  - It does not count the other group: an HR login, or a CXO without System Manager, whose Employee record is at company A, who has no Company rows, and who approves today for company B. `permitted_companies` (`access.py:254-258`) gives that login A only.
  - After release, that login cannot approve B's requests or attendance (R5). It also cannot add, change or delete B's punches (R4).
  - **Fix:** before the push, on each tenant, list every HR-role login, its `permitted_companies`, and the companies whose requests it decided in the last 60 days. Every gap needs a Company row first.
  - A CXO who holds System Manager sees every company and is not affected (proven by test and by `access.py:247`).
- **S-2 (P3, inferred from code). R5 also gates leave approval.**
  - When a Leave Application is approved, stock code inserts and submits an Attendance in the approver's session (`leave_application.py:373-374`).
  - So `refuse_outside_company` runs on that submit, and a leave approval with no permitted company fails with "you cannot approve this".
  - That fits "every door", but leave was never named, and no test covers it.
  - **Fix:** add this to the runbook note. The S-1 count covers the same people.
- **S-3 (P2, not checked). Sync accounts.**
  - DTC's `biometric.sync@` has held only Biometric Sync since 10:41 today (ALV-386). Grace's still holds HR roles.
  - Both still count as the machine (`files_as_machine` needs the Has Role row, which a role profile writes).
  - With no Company rows they stay unscoped, so all 10 machines keep posting.
  - **But** `_machine_may_file` reads *every* Company User Permission row, whatever its `applicable_for`. If either account already has even one Company row, every punch for any other company is refused, and the sync tool stops that machine's batch.
  - **Fix:** run a read-only count of Company User Permission rows for both sync accounts before the push. Expect 0, or a full list of companies.
- **Holiday list on the Shift Type: I agree with the engineer.**
  - Stock `get_holidays_for_employee` does not read `Shift Type.holiday_list`.
  - The hook's job is to remove exactly the days the slip counts as working days. If it also read the shift's list, a Held day on a shift-only holiday would cost nothing, while a Present day on the same date is paid as a working day.
  - Where a shift list disagrees with the employee's list (the Ambala Monday case), the fault is in attendance (ALV-354), not in pay.
- **F1 and F2 regressions:**
  - Phone and portal punches insert with `ignore_permissions` (`field_checkin.py:691`, `hr_api.py:1856`), so HR punching their own day is not affected.
  - The sync tool uses stock `add_log_based_on_employee_field` (`doc.insert()` with no flag), so R2 really does apply to it.
- **P3.**
  - The save message "This replaces the old hidden rule of 3 requests a month… the old script is switched off in the same release" shows at every company. It is only true at Grace.
- **P4, delete.**
  - `held_day.held_count` is a whitelisted endpoint that no screen calls now. Delete it and its test.

## Not checked

- Any live-tenant count (S-1, S-3).
- Any suite re-run by me. The test engineer's runs were still going.
- The screens in a browser.
- Grace's Shift Type thresholds.

**Subtract pass:** I dropped a draft point that the AC-69 exemption could be abused. `validate_missing_time` runs first and refuses a time on a day that is not Held.

# Round 3, 20 Nov 2026: SHIP WITH FIXES

**Verdict: SHIP WITH FIXES. The code fixes hold, and I found no code blocker. What is left is runbook text: one pre-push check (S-1) has no query, and one (OPS-35) tells the operator to add rows with no way to know which companies. All the live-tenant counts are still unrun.**

**Where I looked:** this worktree, branch `slice/085-held-odd-punch-days` at d1300bc3, level with `origin/dev` (fetched; nothing incoming). I read the diff `3b488799..HEAD`, `03` §17, `08` §7, `ci.yml` and the stock leave code. alv085-bench2 mounts `085-fix-tmp` at 8bd77bf9, the same code as HEAD (HEAD only adds notes). **I re-ran one suite:** Redis db 2 emptied, then `test_company_scope_085` gave **20 tests, OK** (matches §17). I re-ran nothing else.

## Round 2 findings

| Finding | State | Evidence |
|---|---|---|
| S-2 leave approval | **Closed: the premise was wrong.** Proven by reading the code | `leave_application.py:371` sets `flags.ignore_validate`. `document.py` `run_before_save_methods` returns before `before_submit`. So R5 never sees a new leave Attendance. |
| S-3 rows that apply | **Closed.** Proven by reading the code and a run | `field_app_access.py` `_machine_may_file` counts only rows for all doctypes or for Employee Checkin. The S-3 test passed in my run. |
| P3 wording | **Closed.** Read | `portal.js:23826` no longer claims a script was switched off. |
| P4 `held_count` | **Closed.** Read | Endpoint and its assertions deleted. The settings-save refusal is kept. |

## New findings

- **R3-1 (P2). Runbook §7 cannot be run as written.**
  - S-1 is prose with no query. Use `alvoraa_reviewed_by` on submitted Attendance Requests, and the approver on approved Leave Applications from the last 60 days, joined to `Employee.company`. Compare that with each login's Company rows.
  - OPS-35 says "Add the row" and "Expect at least 1 row". It gives no way to find which companies a machine punches for. §17 says that no rows is an accepted trade-off. If someone adds a row narrower than the real set, punches are refused and the sync batch stops.
  - **Fix:** before any row is added, run a count of `Employee.company` over the last 30 days of `tabEmployee Checkin` where `owner` is the account. Also state plainly that adding rows is optional and is a separate, approved write.
- **R3-2 (P3). S-2 is still described wrongly in two places.** These are `attendance_doors.py:52-53` (the docstring) and the S-1 line in runbook §7. Both say a leave approval meets R5.
  - There is one real narrow case, and it is new in this round. When a leave covers a holiday that already has a submitted Attendance, stock code cancels that Attendance with no `ignore_validate` (`leave_application.py:333-335`). Its `before_cancel` now runs R5.
  - Effect: only an HR approver outside the company's scope is refused, which means the S-1 group. This is inferred from the code; I did not run it.
- **R3-3 (P3). OPS-36 misses HR logins whose Employee record is not Active.** `permitted_companies` reads only Active records (`access.py:259`). Such a login passes the query, then gets no companies after release. **Fix:** add `and e.status = 'Active'`.
- **Nit.** The test comment "locally it sits four folders above this file" is true only because bench2 mounts `scripts/` at the bench root.

## The questions asked

- **CI backfill path: correct, inferred, not proven in CI.**
  - The test job's `actions/checkout@v4` has no `path:` (`ci.yml:391-393`), so the repo root is `$GITHUB_WORKSPACE`.
  - `scripts/alv392_held_backfill_grace.py` is in that root.
  - The same job already runs `$GITHUB_WORKSPACE/scripts/...` (`ci.yml:481, 541, 550`).
  - `bench run-parallel-tests` inherits the step's environment, and the job does not run inside a `container:`.
- **`access.py`: safe.** Proven by reading the code and grep.
  - `checked_user` is optional, and the default is the old behaviour.
  - There are 3 non-test callers. `refuse()` and `leave_rules.py:216` are unchanged. Only `field_app_access.py:270` passes a user.
  - The log key set is unchanged. Nothing changes for any tenant, or for what CXO, HR or Employee can see or do.
  - The only effect: in R2 and R4 lines, `user` is now the login being checked, which is normally the session user anyway.
- **Biometric sync on release day (DTC 8 machines, Grace 2): no regression while the accounts have no Company rows.** Proven by reading the code.
  - `_machine_may_file` returns True when it finds no rows.
  - Grace's account still holds HR roles and passes on `is_hr`. DTC's account reaches the ALV-302 create branch as before.
  - Cost: one or two extra small reads per punch (the own-record lookup for an HR-role account).
  - The row counts themselves are **not checked**.
- **HR approvals.** R5 now also covers cancelling and amending Attendance, and cancelling and amending Attendance Requests.
  - Only HR-role logins without System Manager, acting outside their permitted companies, are refused. That is the same S-1 group as before.
  - Managers (no HR role), Administrator and System Manager are not affected (`attendance_doors.py:59-62`).

## Not checked

- Any live-tenant count (§7 is all unrun).
- CI itself.
- Any suite other than `test_company_scope_085`.
- The screens in a browser.

**Subtract pass:** I removed a draft point about the monthly limit refusing a manager's edit of a draft. Declining uses `db_set`, and an HR editor returns early, so I could not write a real failure scenario.
