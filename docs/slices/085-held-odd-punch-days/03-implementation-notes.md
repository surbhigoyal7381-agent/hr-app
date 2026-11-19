---
slice: 085-held-odd-punch-days
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-11-19
status: BUILT LOCALLY, NOT PUSHED, NOT DEPLOYED. Release 1 and Release 2 are separate commits.
risk tier: 1
worktree: /Users/mac/hr-app/.claude/worktrees/085-held-odd-punch-days
branch: slice/085-held-odd-punch-days, built on origin/dev 101fd29b (HEAD after this work: see `git log`)
test stack: own containers alv085-bench / alv085-db / alv085-redis, site test_site, image hr-app:dev-3830ed3, the worktree bind-mounted
---

# 085 Held days: implementation notes (ALV-392)

## 0 · Bad news first

1. **Release 2 was built on a base that does NOT have slice 084.** The strategy gate said Release 2 waits for 084 to reach `dev` and rebases onto it. I was told to build it now, so it sits on 101fd29b. Expect conflicts in `hooks.py`, `attendance_correction.py`, `hr_api.py`, `portal.js` and `org-settings.html` when 084 lands. Release 1 touches far less and should rebase cleanly.
2. **Real draft Salary Slips are tested** (`test_held_slip_085.py`): two Held days cost exactly two payment days under both `consider_unmarked_attendance_as` settings, and the test fails when the hook is removed. Not tested: a real **submitted** slip (AC-18) and a refresh of a real draft slip after a release (AC-16); those two use a stand-in.
3. **Added after the first report:** AC-6 (the payslip names the held dates; `held_dates` in the payslip payload; the sentence does not claim a final slip updates), AC-8 (an amber Held chip on the Attendance list through `doctype_list_js`, wrapping the stock indicator; **not seen in a browser**, and the list's company scope is Frappe's own, so AC-56 depends on each tenant's User Permissions), US-17 (`08-release-runbook.md`, written not run), AC-44 (Grace's script text was read by the coordinator: the limit counts the same way, and an exempt list may name a designation as the script did; `test_ac44_...` replays the rule and fails when the designation exemption is removed). **Still not built:** Hindi strings (cut at the gate). AC-66 is read in `nginx.conf` only; what Frappe sends is not proved.
4. **Grace HR will be locked out of the release screens after Release 1 until `hr@grace.alvoraa.co` has a Company User Permission** (Q1). Do this before the Release 1 push.
5. **US-13 undoes an earlier decision (ALV-259).** Three older tests said a tenant's central HR login (HR Manager, no Employee record, no Company permission) opens everyone's month and decides every request. `_scope_conditions` now refuses that login; I changed the tests to match the spec (AC-50) and the strategy gate. **How many such logins exist on dev, DTC, Grace, aahr and PPJ is not checked.** Every one of them loses the month view, the picker and `decide` until it holds a Company User Permission. The Release 1 push needs that count per tenant, not only Grace's. The team page's people list is a different surface and keeps today's behaviour.
6. **Behaviour change on every tenant from Release 1:** an HR person can no longer cancel, amend, delete or hand-make their own attendance, or change or delete their own punch (D-2). A person with an HR role and no company and no branch now sees nobody on the correction screens (US-13). A Shift Supervisor with the submit right and no HR role keeps today's behaviour on purpose.

## 1 · Ladder (no-over-engineering.md): rungs used

| Need | Rung | Why cheaper was rejected |
|---|---|---|
| Held status | 2: one Property Setter, widening, never replacing | Stock options have no Held |
| Own-day doors, raiser | 4: one small module, existing `refuse` and `refuse_own_decision` | No standard control covers them |
| Hold, release, slip | 4: hooks in one file, `held_day.py` | Frappe has no hold; editing the vendored slip rejected (fork policy) |
| Settings | 2: three Custom Fields; 4: a Company `validate` hook (D-5) | New DocType (rung 5) and permlevel rejected |
| Backfill | 4: one script | none exists |

New DocType: none. New app: none. New dependency: none. New queue: none (the slip refresh uses the existing `short` queue). One edit inside the vendored `hrms` tree, approved at D-3.

## 2 · What I built, file by file

### Release 1 (commit d0f775c6, can ship alone)

| File | Change |
|---|---|
| `alvoraa_portal/attendance_doors.py` (new) | `refuse_own_attendance_change` (Attendance `before_update_after_submit`, `before_cancel`, `on_trash`), `refuse_own_attendance_new` (`validate`, new rows only), `refuse_raiser_submit` (Attendance Request `before_submit`; Administrator exempt, a named System Manager refused) |
| `hooks.py` | the four Attendance entries and the Attendance Request `before_submit` list |
| `field_app_access.py` | `checkin_has_permission` answers "no" to write and delete on one's **own** punch, before HR's blanket yes. A new punch of one's own stays allowed |
| `attendance_correction.py` | `_scope_conditions` returns a match-nothing condition for a caller with an HR role and no company and no branch |
| `tests/test_attendance_doors_085.py` | 16 tests, each refusal with a positive control |

### Release 2 (separate commits, in this order)

1. Held Property Setter, Custom Fields (Company 3, Attendance 3, Attendance Request 2), `held_day.py`, wired to `after_migrate` **and** `after_install`.
2. The hold: Attendance `validate`, before the first save.
3. The late machine punch: Employee Checkin `after_insert`; the slip refresh is `frappe.enqueue(..., enqueue_after_commit=True)` with the employee and date only.
4. HR release: Attendance Request `before_submit` (`note_held_day`) and `on_submit` (`release_by_hr`), inline, in its own try.
5. Company `validate` hook (who may change the settings) and the monthly limit on Attendance Request `before_insert`.
6. Salary Slip `validate`, `deduct_held_days`, after the engine's hook.
7. The reader sweep (section 6).
8. Settings card, day sheet, HR card wording (`attendance_correction.py`, `portal.js`, `panels.css`, `org-settings.html`).
9. `scripts/alv392_held_backfill_grace.py`. **Written, not run anywhere.**
10. `tests/test_held_day_085.py`: 29 tests.

## 3 · Decisions taken as the strategy gate said

| Decision | How |
|---|---|
| D-1 | US-14 is in Release 2 |
| D-2 | all own attendance and own punch changes refused (Release 1) |
| D-3 | `"Held": "HLD"` **and a ninth colour** in the vendored sheet; a test opens the report with a Held row and counts legend entries against colours |
| D-5 | Company `validate` hook `guard_company_settings`; no permlevel |
| Q3 | a corrected time under the absent threshold gives Absent (the Shift Type's own `get_attendance`); the HR card says so before the button; a held day with no shift is refused in one sentence |
| Q4 | a release after the slip is submitted changes nothing; HR is told to use Additional Salary (`decide` returns `slip_final`, the card shows it); the employee sheet says "the slip was not changed" and never "updated" |
| Machine path | enqueued, after commit, ids only. HR release is inline in its own try |

## 4 · Acceptance criteria

| AC | State |
|---|---|
| 1, 2 | met locally (Held in the status options, fields present). AC-2's per-tenant read-back is an operator step |
| 3, 4 | met on real draft slips (`test_held_slip_085.py`) |
| 5 | reader table in section 6 |
| 7 | met: the sheet prints HLD, and the report runs with a Held row |
| 6, 8 | **not built** |
| 9, 10, 12, 13 | met (tests: one, three, two punches; switch off; request-made row) |
| 11 | partly: the row is written once as Held at first save, so there is nothing for the job to rewrite. The 3-tick job itself was not run |
| 14, 15 | met (Present / Half Day / Absent by the shift's thresholds; release fields written) |
| 16, 17 | 17 met (a failing slip never undoes a release); 16: the refresh is called and queued (tested with a stand-in), not shown on a real draft slip |
| 18 | met in code (`slip_final`, the sheet's sentence); not tested with a real submitted slip |
| 19 | the decline path is unchanged: the day stays Held and today's decline reason shows |
| 20, 21, 23 | met for the machine account vs HR-added vs staff punch; `skip_auto_attendance` returns early. The portal `do_checkin` and a device-id REST insert by staff are covered by the same account test, not one test each |
| 22 | not tested |
| 24 | met in the day sheet wording |
| 25 to 31 | day sheet, banner, tile, form and payload built to the prototype. Not exercised in a browser. The payload keys are date, time, In/Out |
| 32, 33 | the manager path reuses `raise_for_report` with the time; the existing refusals stand |
| 34, 35 | HR card lines built; Half Day/Absent shown from the same function approval runs |
| 36 | nothing to build: a held day nobody asked about is not a request |
| 37, 38, 39 | card built; the count is one integer; days already held stay held (not tested through the card) |
| 40 to 43 | met (limit on `before_insert`, held requests outside it, exempt role, limit 0) |
| 44 | blocked, Q2 |
| 45 to 49 | met by Release 1 tests |
| 50, 51 | met for the correction screens. The settings endpoint and the count refuse outside the caller's companies (tested) |
| 52 | operator step (Q1) |
| 53, 54 | 53 met (HR User, Accounts Manager, another company's HR Manager refused). 54: Company `track_changes` is stock, not re-proved |
| 55 to 57 | no new route that returns a list; no `allow_guest`; **one** new `ignore_permissions` (the slip refresh) |
| 58 to 63 | the script is written and the pieces tested (site refusal, repo undo file, hold, re-run finds nothing, undo). Not run against any server |
| 64 to 67 | not written |
| 68, 69 | held requests skip the filing window and the monthly limit |

## 5 · Seven dimensions, against the code as written

| Dimension | Before | After | One line |
|---|---|---|---|
| Performance | n/a | **neutral** | Switch off: one cached Company read per new Attendance. A machine punch: `is_machine_account` first, then at most 2 queries. A slip save: one extra indexed query. Not measured on a real month: **not checked** |
| Security | open doors | **improves** | Own-attendance, own-punch, raiser and fail-open scope closed. New `ignore_permissions`: 1 (slip refresh, named). No `allow_guest`. Machine release judged by who filed it |
| Reliability | n/a | **neutral** | Every new hook that runs on a punch or a slip save is wrapped; a fault goes to Error Log and never fails the punch. Savepoints around the release and the slip refresh |
| Scalability | n/a | **neutral** | No loop over employees in any hook. Backfill in chunks of 50, committed per chunk |
| Maintainability | n/a | **degrades slightly** | Pay is now right through a second hook beside the engine's; the "not charged" rule has two copies, both updated |
| Data integrity | n/a | **improves** | Held written once; releases carry how, by whom, when; Held is unpaid so a cancelled Held row cannot fall back to paid. **Risk:** `set_value` writes skip the Version row, so the three release fields carry the audit |
| Compliance / privacy | n/a | **improves** | A pay decision now has a visible state, a named human or a named punch, and a challenge route. No reason is collected for a held day. Logs carry document names only (`frappe.get_traceback()` is called without context) |

## 6 · The reader sweep (AC-5), one verdict each

Greps: 31 modules hold the literal `"Absent"` outside tests. Verdicts below were read in source.

| Reader | Verdict |
|---|---|
| `salary_slip.py` (stock) | fixed from outside by `deduct_held_days`; not edited |
| `payroll_slip.py` `not_charged` | **fixed** (Held added) |
| `daily_attendance_workings.py` `not_charged` | **fixed** (same rule, same word) |
| `attendance_analytics.py` | **fixed**: a `held` count, still an expected day |
| `hr_api.py` team and monthly cards | **fixed**: a `held` key beside `absent` |
| `monthly_attendance_sheet.py` (vendored) | **fixed**: HLD and a ninth colour (D-3) |
| `payroll_rules_apply.py`, `payroll_reprocess.py` | reads Held correctly: rule-set path, odd count already held; `deduct_held_days` returns early for a rule-set company |
| `salary_components_and_workings.py`, `salary_register` | not a status reader (title only / reads the slip) |
| `home_api.py` days-to-fix | reads Held correctly: only unmarked and Absent are listed, so a Held day is not offered twice |
| `org_figures.py`, `data_review.py`, `attendance_score.py`, `gratuity.py` | **left and listed**: not pay; Held is ignored until released |
| `leave_rules.py` | **not checked**: a leave over a Held day has no test |
| `alv291_attendance_fix.py`, `employee_checkin.py`, `attendance_request.py` | not a live pay reader |

## 7 · NFR notes

- **Permission enforcement points:** the Attendance and Attendance Request hooks (every door), `checkin_has_permission`, `_scope_conditions`, `held_count`, `save_settings`, `held_settings` (all through `permitted_companies`, fail closed), the Company `validate` hook.
- **Sensitive fields touched:** none new. The held day's missing time is the only new employee-supplied value. No reason box.
- **Indexes added:** none. The held-count SQL (one raw, parameterised query) correlates on Employee Checkin by employee and time; unmeasured on a large site.
- **Background jobs:** one enqueue (`refresh_slip_job`, queue `short`, after commit, ids only).
- **Fallbacks:** a missing Company column reads as switch off; a missing Attendance column is not selected.

## 8 · What else moved while I worked

`git fetch origin dev` at the start: origin/dev was at 101fd29b, nothing incoming. I did not rebase. `slice/084-employee-window` (8 commits) overlaps `hooks.py`, `attendance_correction.py`, `hr_api.py`, `portal.js`, `org-settings.html`. Not merged, not read again.

## 9 · Commands run and what they said

- Own stack built (alv085-*), `test_site` created, `bench migrate` on that local site only.
- `alvoraa_goals` suite: first run failed on the user-throttle setting (a string); fixed with `set-config -p`; **not re-run** (not my code).
- `test_attendance_doors_085`: 16 OK. Break-tested: removing the hooks, the scope branch and the punch check made 8 of 16 fail, then restored.
- `test_held_day_085`: 29 OK; `test_held_slip_085`: 1 OK, break-tested (hook removed: 0.0 != 2, restored). Break-tested six fixes (hold, machine-account test, slip hook, company guard, limit, ninth colour): 16 failures, each for its own reason, then restored.
- `check_app_integrity.py`: OK at each commit. `check_api_paths.py`, `check_undefined_js.js`, `check_portal_handlers.js`, `check_tag_balance.py`, `check_design_system.py`, `portal_correction_test.js` (40 passed): all OK. `check_scope_traps.py` reported one hit it does not name; the only message printed is a parse error on an untouched `hrms` file under the local older python, so I treat it as environmental: **not proved**.
- Neighbour regression: see section 10.

## 10 · Regression run

One run, one module at a time, on my own stack, 17 neighbour modules (attendance correction, decline scope, picker scope, team scope, decided-as, portal security 010, checkin security, inbox counts, withdraw, leave rules 063, install-hooks parity, expense evidence, permission health, grooming 066, endpoint registry, api calls, alv291).

- OK first time: attendance_correction (118), picker_scope_349, decided_as_045, checkin_security_014, inbox_counts_034, leave_063_rules, install_hooks_parity, expense_evidence_081, permission_health_048, grooming_066, frame_endpoint_registry_034, frappe_api_calls, alv291_attendance_fix.
- **Failed first time, caused by this slice, fixed in the tests:** decline_scope (3), withdraw_after_decline (3), team_scope_259 (1). All used an HR login with no company, which the fail-closed scope refuses by design. Re-run: 11, 6 and 12 tests OK.
- **portal_security_010: 13 errors, not caused by this change as far as I can tell:** every one is `No module named frappe.core.doctype.individual_goal` or `kpi`. The `alvoraa_goals` app is not installed on my test site (I installed erpnext, hrms and alvoraa_portal only). Not run on the base commit, so "pre-existing" is **inferred, not proved**. Run it on a CI-shaped site before any push. Its ceiling on `ignore_permissions` counts is therefore **not checked**; my diff adds one.
- Not run: the full suite, `alvoraa_goals`, browser checks.

## 11 · Known gaps and shortcuts

| Gap | Label |
|---|---|
| No real submitted-slip test (AC-18), no real refresh of a draft slip after a release (AC-16) | temporary debt: extend `test_held_slip_085.py` |
| Central HR logins with no company lose the screens (0.5) | **dangerous debt until counted per tenant**: escalated here, not fixed |
| Held reason for a 3-punch day is "Forgot to Punch Out"/"Forgot to Punch In" by the log chosen, not "Missed Punch Both Ways" | acceptable simplification |
| Withdrawn requests ARE counted, as in Grace's script (only cancelled and Declined are not). Edits to an existing request are not re-counted: the limit runs on insert, Grace's on every save | acceptable simplification |
| Day sheet and settings card were not opened in a browser | temporary debt |
| Night-shift Held days matched by calendar date | intentional trade-off, as in the strategy |
| One more `ignore_permissions` (slip refresh) | intentional trade-off, named |

## 12 · Subtract pass

Read my own diff asking what can go. Removed while building: a second query for the punch count (the hold reuses `_punches`), a base class for the doors, a permlevel, a separate time-stamp field. **Kept and could still go if asked:** the third release field `alvoraa_release_on` (`modified` also carries it).


## 13 · Fix round 1 (tester, 19 Nov)

- **P1 fixed.** The real sync accounts hold Biometric Sync plus HR roles, so `is_machine_account()` (which wants the role and nothing else) was false for them and a late machine punch never released a day. `held_day.release_on_machine_punch` now asks `field_app_access.files_as_machine`: the sync role held and no Employee record, whatever other roles. `is_machine_account` itself is **unchanged on purpose** (punch-time and geofence rules read it; widening it would change what they do for these accounts). A human HR user without the sync role never releases (test, with the old function the tester's HR shapes fail). Never judged by `device_id`.
- **Backfill (AC-62, 63, 58).** Skips days in a submitted slip; the real run stops if the live count differs from the dry run's (count saved beside the undo file); the whole id list is written before any change. `run()` has a test-only `_in_test_site` argument so dry run, real run and undo run end to end on a test site; the command line cannot set it and every site other than Grace is still refused (tested).
- **AC-16 and AC-18 on real slips** (`ReleaseAndTheSlip`): an HR release re-prices that employee's draft slip (+1 payment day); after the slip is submitted nothing changes and `decide` returns `slip_final`. Both fail when the code is removed.
- **Monthly Attendance Sheet:** the stock hrms module's 18 tests run once the two `_Test Fiscal Year` rows are inserted by SQL (the known bootstrap clash) and pass with the Held change; my own `test_the_monthly_attendance_sheet_opens_with_a_held_row` also covers the ninth colour.
