---
slice: 085-held-odd-punch-days (ALV-392)
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-11-20
risk tier: 1
code reviewed: `git diff 101fd29b..208de542`, worktree .claude/worktrees/085-held-odd-punch-days, branch slice/085-held-odd-punch-days
status: recommendation only. Surbhi decides. Nothing pushed.
---

# 085 · Security review

**Conflict of interest, said first.** I wrote `01c` (the requirements I am now checking). Lesson 6 applies. The technofunctional reviewer should check SEC-2 and SEC-5 on their own, without reading my verdict first.

## 0 · Verdict

**Not ready. One P1, two P2s. No P0.**

1. **P1. An HR person can still add a back-dated punch to their own record, so their own one-punch day is never held** (SEC-2 / AC-46, partly met). See F1.
2. **P2. The Administrator login counts as "the machine".** Any punch filed while logged in as Administrator (Desk, a bench script, a data load) releases a held day and records it as "Machine punch". See F2. Verified by running.
3. **P2. An ordinary request that covers more than one day turns a Held day into a full Present day.** It skips the missing-time rule and leaves no release record. See F3.
4. **Rebase warning (must hold before any push).** `origin/dev` has moved on. Slice 084 sets its own `validate` hook on Attendance Request, and so does 085. Slice 084's employee filing window may also refuse a held-day request. ALV-391 (the fix that makes refusals actually reach `security.log`) is on dev but not under this branch. See §5.

Everything else in `01c` is met in code, and the slice's tests pass on `alv085-bench2` (from `04-test-report.md`; I did not re-run the suites).

## 1 · What I checked, and how

- **Verified in code:** every file and line named below, at HEAD 208de542.
- **Verified by running:** on `alv085-bench2`, site `test_site`, as Administrator, read-only `bench execute` calls. `files_as_machine("Administrator")` returned **true**. `is_machine_account("Administrator")` did **not** return true. Role `Biometric Sync` exists on that site. The product code on bench2 (mounted at 487867d0) is the same as HEAD: `git diff --stat 487867d0 208de542` over the app folders and `scripts/` (tests excluded) is empty.
- **Verified by reading installed files in `alv085-bench2`:** Frappe `permissions.py:546-547` gives Administrator every Role on the site. `company.json` and `attendance.json` both have `track_changes: 1`.
- **Not run:** I did not run any suite, break test or write on any site. The bench belongs to the engineer, and two sessions on one site break each other's runs. F1 and F3 are read from the code. A demonstration needs my own bench.
- **Real data shape:** not checked on any tenant. To see these controls working, a site needs: a company with the switch on, at least one Held row, a sync account (sync role and no Employee record), two companies, a branch-scoped HR login, and a draft slip. `04` says the test fixtures build all of these.

## 2 · Requirements

| Req | State | How it is met (file:line) | Proof |
|---|---|---|---|
| SEC-1 Held unpaid; paid once released; final slip untouched | **Met, with one gap (F3)** | `held_day.py:452-471` (slip validate takes Held days off payment days); `:425-449` (re-saves that one employee's draft slip); `:335-337` and `attendance_correction.py:1890-1892` (tells HR when the slip is final). Readers: `attendance_analytics.py`, `payroll_slip.py` (`not_charged` now includes Held) | `test_held_slip_085` AC-3/4/16/18; **break-proven** by the test engineer. AC-5: not every reader has a test |
| SEC-2 nobody releases their own Held day, on any door | **Partial (F1)** | `attendance_doors.py:19-29`, wired in `hooks.py:169-178` to validate (new rows), before_update_after_submit, before_cancel and on_trash. These use `refuse_own_decision`, which applies to every role (`access.py:64-77`). Own punch write and delete refused at `field_app_access.py:278-281`. **An own punch *create* with any time is still allowed for HR** | `test_attendance_doors_085` (16 OK). No break test by anyone (`04` §3) |
| SEC-3 the raiser does not decide | **Met** | `attendance_doors.py:32-44` on Attendance Request before_submit (`hooks.py:205-209`). Covers Desk, REST and import | `test_raiser_cannot_submit_but_a_colleague_can`, `test_a_named_system_manager_raiser_is_refused_too`. Not break-proven |
| SEC-4 release and settings scoped, fail closed | **Met on the named paths** | `attendance_correction.py:330-335`: an HR login with no company and no branch now gets "nobody". `decide` asks it at `:1852`. `held_day.py:163-165` and `:187-189` check `permitted_companies` (`access.py:193-215`, fails closed). **A Desk or REST submit is scoped only by the tenant's User Permissions.** This was true before 085 (R5) | `test_hr_login_with_no_company_and_no_branch_sees_nobody`, `test_the_count_is_an_integer_and_refused_outside_the_callers_companies` |
| SEC-5 only a machine punch releases by itself | **Partial (F2)** | `held_day.py:386-416`: after_insert only, judged by who filed the punch (`files_as_machine`, `field_app_access.py:59-74`), never by `device_id`. Skips `skip_auto_attendance`. Recount after edit or delete never runs. **Administrator passes the test** | `test_held_p1_machine_accounts_085` (3), **break-proven**. F2 verified by running |
| SEC-6 settings are HR Manager's, in scope, on every door | **Met** | `held_day.py:102-141`, Company validate (`hooks.py:419-423`), so the Desk form, REST `PUT` and `save_settings` all meet it. Change history: Company `track_changes: 1` (stock), so `doc.save()` writes a Version row. Limit on every door: `held_day.py:206-239` (before_insert). Exempt roles skip only the limit, never the hold (`:226`) | `test_only_an_hr_manager_of_the_company_may_change_the_settings` (HR User, Accounts Manager, other-company HR Manager). It calls the save directly, not REST. AC-54 (Version row) has no test. Minor F5 |
| SEC-7 backfill: dry run first, narrow, undoable, attributable | **Met, minor gaps** | `scripts/alv392_held_backfill_grace.py`: site lock `:57-58` (the test-only parameter cannot be set from the command line, `:106-113`); November only `:29`; dry-run default and count match `:85-97`; undo list written and fsynced before any change `:116-123`; undo file refused inside the repo `:59-62`; Comment per row `:130-131`; ids and counts only in the output. **Gaps:** the Comment is written as Administrator, so it does not say which person ran it, and there is no run id. Rows skipped because they sit in a final slip are dropped without being listed (`:47-49`) | `test_the_test_hook_still_refuses_every_other_site`, backfill end-to-end tests. AC-62 is not break-proven (`04` §3) |
| PRIV-1 no new reader, no wider view | **Met** | 0 `allow_guest` in the diff (counted). 3 new whitelisted endpoints, all scoped (`held_day.py:144,158,182`). `held_count` returns only a whole number. New fields go only into readers that were already scoped (`month`, `to_review`, the scorecards, `_payslip_payload` after its ownership check). **One new `ignore_permissions` in product code**, `held_day.py:439`. It is justified (the machine account holds no Salary Slip right), but it goes against the wording of AC-57 (F6) | AC-55/56 partial; AC-57 untested (`04`) |
| PRIV-2 time only; nothing personal in logs | **Met in code; the logging part only works after rebase** | The form sends date, time and In/Out only (`attendance_correction.py:1210-1227`). Refusals go through `refuse` → `log_refusal`: user id, document name, rule (`access.py:28-48`). Error Log titles carry checkin or slip ids (`held_day.py:415, 447`). **At this base, `security.log` drops these lines (ALV-391).** The fix is on dev (a627e0a5, 15c716f6), not under this branch | AC-28 payload test. No test reads a captured log line |
| PRIV-3 the person sees the state and how it ended; the record lasts | **Partial (F3)** | `attendance_correction.py:974-995` (`_held_flags`); release fields `held_day.py:47-56`, written at `:340-352` | AC-15, AC-20 fields. The screens are not proven (`04` §5) |

## 3 · Findings

**F1 · Major · P1 · SEC-2 / AC-46 partly met.**
- **Who and how:** an HR User or HR Manager who has an Employee record. Their day has one IN punch, and auto-attendance has not marked it yet. In the Desk (or `POST /api/resource/Employee Checkin`) they add an OUT punch on their **own** record at a time they pick, say 18:30.
- **Why it works:** `checkin_has_permission` refuses only `write` and `delete` on one's own punch (`field_app_access.py:280`), then gives HR a blanket yes (`:282`). HR holds write on `time` at permlevel 1 (`employee_checkin.json`, stock rows; tenant Custom DocPerm not checked). The phone geofence never measures punches HR adds.
- **What happens:** the day is marked Present with hours they chose. It is never Held, and no second person sees it. AC-46 allows only an ordinary new punch "now". The test `test_hr_can_still_make_a_new_punch_of_their_own` uses 09:00 today, so it also accepts any time.
- **Smallest fix:** for one's own record, a non-machine create is allowed only near the current time, or `time` is forced to now. One condition in the same hook. The test must use a past time and expect a refusal.
- **Evidence:** read in code. Not run.

**F2 · Major · P2 · SEC-5, a human can pass as the machine.**
- **Who and how:** anyone working as Administrator who files an Employee Checkin: the Desk logged in as Administrator, a `bench` script, or a data load of missing punches. Memory notes record punches loaded by script before ("173 punches saved to load").
- **Why it works:** Frappe gives Administrator every role (`permissions.py:546-547`), and Administrator has no Employee record. So `files_as_machine` returns true (`field_app_access.py:72-74`). Verified by running.
- **What happens:** the held day is released through `held_day.py:393-408`, recorded as "Machine punch", at a time a person chose.
- **Not an escalation:** Administrator can already change any row. The harm is a pay decision with no human named on it, made by accident during repairs.
- **Smallest fix:** `files_as_machine` returns False for Administrator, matching `is_machine_account`. Add one test.

**F3 · Major · P2 · SEC-1 / PRIV-3, a release door outside the design.**
- **Who and how:** an employee whose 12 Nov is Held sends an ordinary request for 11 to 12 Nov, with no missing time. HR approves it.
- **Why it works:** `note_held_day` looks for a held row only when the request covers one day (`held_day.py:358`), so it does not stop this. Stock then sets the Held row to Present (`attendance_request.py:165-170`).
- **What happens:** the day becomes a full Present day. Its hours are not worked out from the shift, and no "released by" fields are written. The employee's sheet does not show how the day ended. A second person did approve it, so this is not a self-release. The only trace is the stock Comment "Changed the status from Held to Present".
- **Smallest fix:** in `note_held_day`, refuse any request whose dates cover a Held day unless it is that day's own held-day request.

**F4 · Minor · P3.** An employee can get round the monthly limit through REST:
1. They insert a draft held-day request. It carries a time, so the limit is skipped (`held_day.py:213-214`).
2. They edit the draft to an ordinary request. `validate_missing_time` returns early when there is no time (`:244`), and the limit runs only on `before_insert`.

HR still decides every request, so pay is not affected. Slice 084 moved its own check to `validate` for this same reason.

**F5 · Minor · P3.** The SEC-6 test calls the save directly, not REST `PUT /api/resource/Company`. The hook covers both doors, but only one has a test. AC-54 (the Version row) has no test.

**F6 · Minor · P3 · gate gap (mine).** `test_sec16_ignore_permissions_does_not_grow` loops only over the files in `CEILINGS` (`test_portal_security_010.py:1024`). The new `held_day.py:439` is therefore invisible to the gate, and so is any new file. Add a `held_day.py` ceiling of 1 now. Separately, I will make the gate fail on any file that is not listed.

**F7 · Minor · P4.** `_viewer` looks only for an **Active** Employee (`field_app_access.py:204`). A leaver who still has an HR login skips the own-punch refusal. ERPNext does not disable a leaver's login (lesson 3). Only the punches from their last days are exposed.

**Worries (I cannot yet write the full scenario):**
- If HR cancels an approved held-day request, stock cancels the released row (`attendance_request.py:145-152`). The day then has no row at all. With `consider_unmarked_attendance_as = Present`, it is paid, and it is not Held again.
- If an HR user runs "Mark Attendance" on a Shift Type from the Desk as themselves, their own new row meets `refuse_own_attendance_new`. I did not check whether that stops the whole batch.

## 4 · The questions in the brief, answered

| Question | Answer | Label |
|---|---|---|
| HR releases directly | Only through an Attendance Request submit (portal `decide` or Desk/REST) that carries the time. Own request refused (`refuse_own_submit`), own raise refused (`refuse_raiser_submit`). Exceptions: F3, and HR's Desk cancel-and-amend of a **colleague's** Held row, which is allowed by design and recorded in its Version history | Verified in code |
| Employee's own request | Can send the time; can never decide it | Verified in code; tested |
| Reporting manager's request | Can send for a direct report (`raise_for_report`); cannot decide what they raised | Verified in code; tested |
| Machine account | Sync role and no Employee record, judged by who filed the punch, never `device_id`. **A human can pass as it by working as Administrator (F2)**, or by holding the sync key or password (R2) | Verified by running (F2) |
| D-2 nobody edits own attendance or punches, HR included | Attendance: met on every door. Punches: change and delete met; **back-dated create open (F1)** | Verified in code |
| Company and tenant scope of lists and reports | Portal paths fail closed. The Desk list, Desk submit and the Monthly Attendance Sheet rely on the tenant's User Permissions, as before 085. Each site is one tenant; no cross-site path was added | Verified in code; tenant rows not checked |
| Backfill can only run on the intended site | Yes: `--site` must equal `grace.alvoraa.co` (`:57`), and November is fixed. **Not checked:** that Grace's production site has exactly that name. If it does not, the script refuses (fails closed) | Verified in code; tested |
| Logs | Ids and user logins only; no names, no statutory ids. They reach the file only after the rebase onto ALV-391 | Verified in code |
| The switch and who changes it | HR Manager of that company, System Manager, Administrator, on every door. HR User and Accounts Manager are refused. Every change gets a Version row (stock `track_changes`) | Verified in code; tested (one door) |

## 5 · Before any push to dev (rebase conditions)

1. After rebasing onto `origin/dev`, Attendance Request `validate` must be a **list holding both** `held_day.validate_missing_time` (085) and `attendance_correction.refuse_own_day_outside_window` (084). Keeping only one side of the conflict silently drops a control.
2. Decide with Surbhi whether 084's **employee** window may refuse a held-day request. 085 exempts held days only from the manager window (`attendance_correction.py:2317-2320`). If 084 refuses an old held day, that day stays unpaid with no way out, which works against PRIV-3. Owner: `hrms-business-analyst`.
3. After the rebase, check that one 085 refusal actually writes a line to `logs/security.log` (ALV-391). Read the file; do not just assert the call.

## 6 · Obligations

| Obligation | Last verified | Effect here |
|---|---|---|
| DPDP 2023 + Rules 2025 (safeguards, accuracy, grievance) | baseline, 24 Aug 2026. **Goes stale on 22 Nov 2026**; I did not re-verify it today | F1 and F3 touch accuracy; PRIV-3 is the grievance path |
| Code on Wages 2019, holding a day's pay | not read; see `01c` §7 | R1 |

## 7 · Residual risk, each needing a named person

| # | Risk | Owner to accept | Accepted? | Label |
|---|---|---|---|---|
| R1 | The wage-law basis for holding a day's pay rests on Surbhi's decision, not counsel's written view | Surbhi | Recorded in `01c` as her decision of 19 Nov 2026 (Brief gate). I have not seen it in her own words | intentional trade-off |
| R2 | Anyone with a sync account's key or password can file punches for anyone and release held days. The real sync accounts also hold HR roles | Surbhi | **No** | temporary debt; removed by key rotation and an IP allow-list (own ticket) |
| R4 | Any HR role can write another company's punches by name (pre-existing, `01c`) | Surbhi; fix by `hrms-fullstack-engineer` | **No.** Not checked whether it is ticketed | dangerous if left untracked |
| R5 | A Desk or REST submit of a held-day request is scoped only by tenant User Permissions, not by `_scope_conditions` (pre-existing) | Surbhi | **No** | temporary debt |
| F2, F3 | If not fixed before release | Surbhi, in writing, with a date | **No** | temporary debt |

## 8 · What I could not check

- Tenant Custom DocPerm on Employee Checkin, Attendance and Company (F1 assumes the stock rows). Needs read-only site access.
- The exact name of Grace's production site.
- Whether F1 and F3 behave as I read them when run. Needs my own bench, not the engineer's.
- Whether ALV-391 writes lines on production.

## 9 · Subtract pass

Removed from this review:
- a finding on the company-wide `held_count` shown to branch HR (it is one number with no names);
- a finding on traceback text in the Error Log (only System Managers can read it);
- the backfill not re-pricing draft slips (a pay question for the technofunctional reviewer, not a security one).

No new gate, tool or requirement is proposed beyond F6's one ceiling line.

---

# Re-review, 20 Nov 2026 (fix round 2)

**Code read:** `git diff 15c716f6..148cb639`, worktree `.claude/worktrees/085-held-odd-punch-days`, HEAD 148cb639 (clean). **Run on:** container `alv085-bench` (it mounts this worktree), site `test_site`. Read-only Python with `frappe.init`, every write rolled back, nothing committed. I did not run any suite. **Conflict of interest, again:** I wrote `01c`. A second reader should check the P1 below.

## R.0 · Verdict

**Not ready. One new P1. No P0.**

**P1 (dangerous debt, escalate now). The punch write check looks at the punch as it will be saved, not as it is stored.** The `employee` field on Employee Checkin can be edited (stock `employee_checkin.json`: no `set_only_once`, no `read_only`; no Property Setter in the repo). Frappe checks `write` on the changed document (`frappe/model/document.py:584`, `check_permission("write", "save")` after `doc.update(data)` in `api/v1.py:57-58`). So `checkin_has_permission` (`field_app_access.py:315` and `:326-331`) judges the new employee. Two results:
- **R4 is not closed for write.** *An HR User whose only company is G066 Co opens punch EMP-CKIN-11-2026-000001 (ALV085 Company) by name, sets `employee` to a G066 Co person and saves.* `checkin_has_permission(..., "write")` and `frappe.has_permission` both returned **True** (verified by running, as `anil@g066.test`). Unchanged, the same punch returned False. The other company's employee loses a punch, which can turn their day Held or cost pay. Reads are not narrowed, so the punch can be found.
- **SEC-2 is open again for one move.** An HR person with an Employee record can move one of their OWN punches to a colleague. Before marking, a three-punch day (it would be Held) becomes a two-punch Present day. **Inference** from the same mechanism. There was no HR user with their own punches on `test_site`, so I could not run it.
- **Smallest fix:** in the same hook, for `write`, run the own-record test and the company test on **both** the stored employee (`frappe.db.get_value("Employee Checkin", doc.name, "employee")`) and the new one. A test must move a punch across, each way, and expect a refusal. The other option is `set_only_once` by Property Setter, which is configuration. It is the cheaper fix, but it also stops HR putting a punch right when it was filed against the wrong person, so that is a product call (`hrms-business-analyst`).

## R.1 · The fix items

| Item | State | Mechanism (file:line) | Proof |
|---|---|---|---|
| F1 HR cannot insert own punch | **Closed** for create | `field_app_access.py:321-322`: HR holding an Employee record, own employee, `create`, refused | `test_f1_...` (notes §14, break-proven per the engineer). Verified in code. The F7 leaver gap remains (`_viewer` looks for Active only, `:207`) |
| F2 Administrator is not the machine | **Closed** | `field_app_access.py:74-77`: Administrator returns False, and a real `Has Role` row for `Biometric Sync` is required | `test_f2_...`. Verified in code |
| F3 multi-day request covering a Held day | **Closed** | `held_day.py:384-389` refuses a request without a time whose dates cover a submitted Held row. A request with a time already needs a one-day Held row (`:376-380`) | `test_f3_...`. Verified in code |
| R2 sync account limited to its Company rows | **Partial** | `field_app_access.py:274-285`, **create only**. No rows means unscoped (`:281-282`) | `test_a_scoped_sync_account_...`. **Verified by running:** a temporary row made `create` for another company False, and an `R2` line was written |
| R4 HR create/write/delete within permitted_companies | **Not met for write** (P1 above). Create and delete met | `field_app_access.py:288-296`, `:326-331` | Create was refused for another company, and so was write of the punch as stored. **Both verified by running, with R4 lines written** |
| R5 approve/submit company-scoped on every door | **Met for submit**. Cancel and update-after-submit are not scoped (as the engineer says) | `attendance_doors.py:46-67`, on `before_submit` for Attendance (`hooks.py:170`) and Attendance Request (`:216`). Company is read from the Employee record, not the document | `test_company_scope_085` R5 tests. **Verified by running:** PermissionError, and an `R5` line written for `anil@g066.test` |

**The refusals reach `security.log`: verified by running.** `logs/security.log` and `sites/test_site/logs/security.log` went from 0 to 889 bytes: two R4 lines, one R5 line, one R2 line, as JSON with ids only. **One flaw (Minor, P4):** `log_refusal` records `frappe.session.user`, not the `user` that `checkin_has_permission` was asked about. My R4 and R2 lines say `Administrator`. On a real REST or Desk call the two are the same (inference). The 085 tests still patch `security_logger`, so no test reads the file.

## R.2 · Every SEC and PRIV item now

| Req | State | Change since the first review |
|---|---|---|
| SEC-1 | **Met** | F3 closed. B-1 (a submitted slip keeps the hold) is the reviewer's item; I did not re-check it |
| SEC-2 | **Partial** | F1 closed. The own-punch **move** (P1) is new. **Minor P3:** Attendance `before_submit` has no own-record check (`hooks.py:170`). An HR person can edit and submit a **draft** Attendance of their own that someone else created. This needs a second person to make the draft, and `hold_odd_punch_day` still runs at validate. Doors checked: Attendance insert, save, submit, update-after-submit, cancel and delete; Attendance Request submit; Employee Checkin create, write and delete. Desk, REST and import all meet the same hooks |
| SEC-3 | **Met** | unchanged |
| SEC-4 | **Met for portal and submit** | R5 now covers Desk and REST submit. Cancel is still scoped only by Frappe User Permissions. Those apply here, because both doctypes carry `company`, but only for HR logins that have Company rows. HR logins that fall back to their Employee company get no Frappe scoping on cancel |
| SEC-5 | **Met** | F2 closed |
| SEC-6 | **Met** | unchanged. F5 is still open (Minor) |
| SEC-7 | **Met** | The run id and the operator are now in every row's Comment (`scripts/alv392_held_backfill_grace.py:114-117, 151`). The `--operator` value is typed by whoever runs it, not checked |
| PRIV-1 | **Met** | The F6 ceiling for `held_day.py` is still not in `test_portal_security_010.py` (that one is mine) |
| PRIV-2 | **Met** | Logging verified by running (above) |
| PRIV-3 | **Met** | F3 closed |

Still open from the first review: F4 (the limit is still `before_insert`, `hooks.py:224`), F5, F6, F7. All Minor.

## R.3 · R2 with no rows: my judgement

- **Failing open here is acceptable only as a named, dated trade-off.** Refusing a sync account that has no rows would stop punches on every tenant at release, as on 2 Nov (ALV-302). That is an outage, not a leak, and the slice adds no new exposure. The account could already file for anyone before 085.
- **What R2 does not do, said plainly:**
  1. On a tenant with one company, the rows change nothing.
  2. The real sync accounts hold HR roles (notes §13). For them, write and delete skip the R4 check (`:327` runs before `:330`) and fall through to HR's yes (`:332-333`). Anyone with the key can still change or delete any punch in any company.
  3. The key itself is the exposure. Key rotation and an IP allow-list remain the real fix (own ticket, not checked whether it exists).
- **The operator step must be:** per tenant, before the push, list the logins holding `Biometric Sync` and count each one's Company User Permission rows. Add one row per company the account serves, with `apply_to_all_doctypes` **off**. Read the rows back and write the counts in the release record. Then prove the refusal on **dev**, not production: a punch for another company, then read `security.log` for the `R2` line. On a single-company tenant, write "R2 adds nothing here" in the release record. Runbook line 79 asks for a test punch but does not say where, and does not ask for the counts.

## R.4 · Worries (no full scenario yet)

- R5 raises PermissionError, and stock `mark_attendance_and_link_log` catches only ValidationError (`employee_checkin.py:280`). An HR login that presses "Mark Attendance" on a Shift Type used by two companies may stop partway. The same applies to approving a leave for someone outside the login's companies. That is a question of the service staying up, not a leak.
- Cancelling an approved held-day request still removes the released row (first review). With R5 not on cancel, an HR login can do this for another company (it works where SEC-4 says it does).

## R.5 · Residual risk, needing Surbhi's named acceptance with a date

| # | Risk | Label | Accepted? |
|---|---|---|---|
| P1 | Punch write judged on the new employee: cross-company move (R4) and own-punch move (SEC-2) | **dangerous debt, fix before release** | No. I recommend fixing, not accepting |
| R2a | A sync account with no Company rows stays unscoped until the operator adds them | intentional trade-off | No |
| R2b | Sync accounts holding HR roles may write and delete any punch in any company; the key is the exposure | temporary debt (key rotation and allow-list ticket) | No |
| R5a | Cancel and update-after-submit of Attendance and Attendance Request are not company-scoped for HR logins without Company rows | temporary debt. The fix is two hook lines that reuse `refuse_outside_company` | No |
| R1 | Wage-law basis for holding pay | intentional trade-off (her 19 Nov decision) | As before |

## R.6 · Not checked

- The P1 own-punch move, by running (there is no such user on `test_site`).
- Tenant Custom DocPerm and Property Setters on Employee Checkin.
- Whether the key-rotation ticket exists.
- Production `security.log`.

**Subtract pass:** I dropped a finding that the R4 log line's `name` is empty on a create (true, harmless) and a note on the `held_count` endpoint nobody uses (not a security matter). No new gate or requirement is proposed.

---

# Round 3, 20 Nov 2026 (fix round 3)

**Code read:** `git diff 3b488799..HEAD` (HEAD d1300bc3; code in ce0e69b3, 57cb44b4, 8bd77bf9), worktree `.claude/worktrees/085-held-odd-punch-days`. Frappe source read in `alv085-bench2` (frappe 988e54f). **I ran no test this round**; the counts and break proofs are the engineer's (notes §17). **Conflict of interest, again:** I wrote `01c`.

## 3.0 · Verdict

**Ready from the security side. No P0, no P1.** Four items still need Surbhi's named, dated acceptance (3.3). Two stale sentences should be corrected before the push (P4).

## 3.1 · The open items

| Item | State | Mechanism (verified in code) |
|---|---|---|
| P1 punch move, R4 and SEC-2 | **Closed** | `field_app_access.py:319-322` builds the set {new employee, stored employee} for write and delete. The own-record refusal (`:329`) and the company loop (`:341-346`) both run over that set. Tests `PunchMovedAcrossCompanies` (both directions, own punch out, colleague's punch in, a real `save()` refused and the stored value unchanged) |
| R5 cancel and update-after-submit | **Closed** | `hooks.py`: Attendance `before_cancel` and `before_update_after_submit` lists, Attendance Request `before_cancel` and `before_update_after_submit`, all reuse `refuse_outside_company` |
| R2 write and delete | **Closed for accounts with rows** | `:341-344` runs the sync-account check for create, write and delete, before HR's yes. No rows is still unscoped (`:285-286`), by design |
| S-3 | **Closed** | `:283-284`: only rows with `apply_to_all_doctypes = 1` or `applicable_for = Employee Checkin` count, as Frappe applies them |
| Log user field | **Closed** | `access.py:71, 84`: `user` is the login asked about when one is passed, else the session user. Key set unchanged. Caveat (P4): when the two differ, the asker is not recorded. Nothing in this slice asks on another user's behalf |
| SEC-2 P3 own-submit | **Closed** | Attendance `before_submit` now runs `refuse_own_attendance_change` first. `is_own_record` reads `Employee.user_id` with no status filter |
| F4 | **Closed** | `enforce_monthly_limit` on `validate`; skips `docstatus` ≠ 0; excludes itself on edit (`held_day.py:204, 230-231`) |
| F5, F6 | **Closed** | API-door test; ceiling `held_day.py: 1` in `test_portal_security_010.py:752` |
| F7 | **Closed** | `:325`: an HR login's own record is looked up whatever its status |
| `held_count` | **Removed**. No caller left in Python, JS or HTML (grep) | one fewer whitelisted endpoint |

## 3.2 · The three judgements asked for

- **Leave approval and R5 — the engineer is right.** Verified in code: `leave_application.py:372` sets `flags.ignore_validate`, and `frappe/model/document.py:1407-1408` then returns before any `before_submit` hook. The existing-attendance path uses `db_set` (`:351`) and leave cancel uses `frappe.db.set_value(..., "docstatus", 2)` (`:384`): no hooks at all. So R5 and SEC-2 never see leave-made attendance. Leave approval is scoped only by Frappe User Permissions on Leave Application, so **an HR login with no Company rows (falling back to its Employee company) can approve leave in any company.** This was true before 085; the slice does not widen it. Two sentences now say the opposite and should be fixed (P4): the `refuse_outside_company` docstring ("A leave approval ... meets this too (S-2)", `attendance_doors.py:52-53`) and runbook 08 §7 S-1 ("refused (R4, R5, and a leave approval, S-2)").
- **`access.py` change: safe for every tenant.** A new keyword argument with a default; the old behaviour is unchanged when it is not passed. Repo-wide grep: three callers, only `field_app_access.py:270` passes it. No schema, no config, no key change.
- **CI key guard: no real credential found.** I scanned every added line in `acc89592..2d9f979c` (40 commits, 5,782 lines) for known key shapes (AWS, GitHub, Slack, Google, OpenAI-style, private keys, JWTs), for key/token/secret/password followed by a value, and for long mixed-case strings. Nothing. The two candidates are not secrets. 01c:235 is two public law-firm URLs. 05-review:25 is a local temp path; its UUID is a Claude Code session folder name, not a token. **Not checked:** which line gitleaks actually matched. The redacted log still prints RuleID, File, Line and Commit. Read those before adding any allow-list entry, and allow that one fingerprint only (`.gitleaksignore`), never a path or a rule.

## 3.3 · Residual risk, needing Surbhi's named acceptance with a date

| # | Risk | Label | Accepted? |
|---|---|---|---|
| R2a | A sync account with no Company rows stays unscoped until the operator adds them (runbook OPS-35) | intentional trade-off | No |
| R2b | Sync accounts hold HR roles; anyone with the key can change or delete any punch in a company the account serves, and in every company when it has no rows | temporary debt; removed by key rotation and an IP allow-list (ticket not checked) | No |
| S-2 | Leave approval and leave cancel are not company-scoped for HR logins without Company rows (stock code skips the hooks) | temporary debt, older than 085. The cheapest fix is one hook line: `refuse_outside_company` on Leave Application `before_submit` and `before_cancel`. That is a scope call for `hrms-business-analyst` | No |
| R1 | Wage-law basis for holding pay | intentional trade-off (her 19 Nov decision) | As before |

## 3.4 · Not checked

Test runs (none by me this round); the gitleaks rule and line; tenant Custom DocPerm and Property Setters on Employee Checkin; production `security.log`; whether the key-rotation ticket exists.

**Subtract pass:** I dropped a note that `permitted_companies` counts Company rows for any doctype while R2 now counts only the applicable ones. It is older than this round and changes no result here. I also dropped a rehire edge case (an Active and a Left record for one login). No new requirement or gate is proposed.
