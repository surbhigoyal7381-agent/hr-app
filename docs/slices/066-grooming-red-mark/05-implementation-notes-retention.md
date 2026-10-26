---
slice: 066-grooming-red-mark
artifact: 05-implementation-notes-retention (the grooming erase job)
author: hrms-fullstack-engineer
date: 2026-10-25
branch: slice/066-retention in .claude/worktrees/066-retention, from origin/dev f207e82c
status: BUILT LOCALLY. Not pushed. Not merged into dev. Nothing run on any server.
strategy: 04b-retention-job-strategy.md (written in .claude/worktrees/dev-integration-2026-10-22,
  untracked there; not copied into this branch)
---

# 066 retention: the grooming erase job

## 0 · The answer first

**The job is built, tested and committed locally, and it is OFF.** It erases nothing on
any site until that site's config says `grooming_erase_enabled: 1`. Counsel has still to
confirm Q-1 (the register of fines erased at 6 months) and D-3 (a hold for open disputes)
in writing. Do not switch it on before that.

**One real fault was found while testing, and is fixed.** Frappe reads a blank relieving
date as 0001-01-01. My first filter (`relieving_date < 6 months ago`) therefore treated a
Left person with no relieving date as long overdue, and would have erased their records at
once. The rule now also needs `relieving_date is set`, and a test pins it.

## 1 · How to switch it on, and back off

Per site, on the site's own `site_config.json` (never in `common_site_config.json`, which
would switch on every site on that bench):

| Want | Command |
|---|---|
| See what it would do (any time, switch on or off; erases nothing) | `bench --site <site> execute alvoraa_portal.grooming.erase_due` (a dry run unless told otherwise in so many words) |
| A real run by hand (only with the switch on) | `bench --site <site> execute alvoraa_portal.grooming.erase_due --kwargs "{'dry_run': 0}"` |
| One deliberate catch-up run of more than 25 people | `bench --site <site> set-config -p grooming_erase_max_people <n>`, then set it back with `0` (0 or missing means 25) |
| Switch on | `bench --site <site> set-config -p grooming_erase_enabled 1` |
| Switch off | `bench --site <site> set-config -p grooming_erase_enabled 0` |
| Is it on? | `bench --site <site> execute alvoraa_portal.grooming.erase_switched_on` |
| Run the self-check by hand | `bench --site <site> execute alvoraa_portal.grooming.erase_self_check` |

The switch is read fresh by every scheduled job, so no restart is needed. With it off the
daily run (`erase_daily`) returns `{"switched_on": 0}` before any query, and a real run by
hand (`dry_run` 0) does the same. Order on any site, when Surbhi says so:
backup, dry run, read the ids with HR, switch on, read the Error Log after the next day.

**Why a site-config key and not a Scheduled Job Type left disabled.** A Scheduled Job Type
is created by `bench migrate` from `hooks.py`, enabled. Shipping it disabled would need a
patch that runs after the job sync, and anyone re-enabling the row in the desk would switch
it on without a trace in git. The site-config key is the repo's existing pattern
(`ai_lead_intake_enabled`), defaults to off when absent, and needs no schema. This is the
one setting the 04b strategy said it would not add; Surbhi asked for it on 25 Oct.

## 2 · What was built, file by file

Rung 4 (new code), as the strategy approved. No DocType, no field, no screen.

| File | Change | Why this mechanism |
|---|---|---|
| `alvoraa_portal/grooming.py` | New section at the end: `erase_switched_on`, `_due_filters` (the rule, once), `_due`, `_draft_slip`, `_erase_one`, `_erase_person`, `erase_daily` (the hook), `erase_due` (dry run unless told otherwise), `_erase_run`, `_record`, `_transferred`, `_left_without_date`, `erase_self_check`. `add_days` import | The module that holds every grooming rule. Slice 065's erase shape, copied not imported (two uses) |
| `grooming_mark.py`, `grooming_review.py` | `no_feed_on_delete = True` and `on_trash` refusing any delete without the erase flag | The two lines per controller the strategy named |
| `hooks.py` | One line appended to `scheduler_events["daily"]` | Frappe's scheduler |
| `tests/test_grooming_erase_066.py` | 25 tests (18, then 7 for the review fixes) | Pins every guard |

## 3 · The rule as built

Due on a run when, all at once:

- Employee `status` is `Left`;
- `relieving_date` is set and earlier than the same day 6 months before today (so on the
  date 6 months on, the records are kept; the run after it erases them);
- the Employee row was last edited more than 30 days ago (**D-1**);
- the person has at least one mark or review.

The same filter runs again under a row lock on the Employee just before the erase, so a
rehire or a date change between the list and the erase is obeyed. A person with a **draft**
Salary Slip is skipped and shows in the self-check after 2 days. Section 13 has what the
review changed (fresh locking read, per-person commit, the 25-person stop, transfers).

**D-2** as approved: a rehire on a new Employee record does not touch the old record's
marks; they go 6 months after the old record's relieving date. **D-5** accepted: the
workings report shows 0 reds for erased months. **D-6**: the alerts are read by Surbhi.

[ASSUMPTION] D-1 read as "erase only when both are true: 6 months past the relieving date,
and no edit to the Employee in 30 days". It can only delay an erase.

## 4 · What is erased, and what stays

Erased per record, in one transaction: Event Participants rows first, `docstatus` set to 2
on a mark (Frappe deletes no submitted record; a cancel would run the mark's rules and tell
the person), `frappe.delete_doc(..., delete_permanently=True, flags={ERASE_FLAG: True})`, then
`delete_dynamic_links` at once (Version, Comment, ToDo, DocShare, View Log, Document Follow,
Notification Log, Email Unsubscribe). Tag Link, global search, files go inside `delete_doc`.
No Deleted Document copy, no "Deleted" comment.

Stays: submitted Salary Slips, their "Grooming Red Value" row, the Additional Salary
records, slip comments by the engine. Proven by a test.

## 5 · Acceptance criteria (strategy section 9) and the tests

| # | Strategy test | Test |
|---|---|---|
| 1 | Every trace gone | `test_a_due_leavers_marks_reviews_and_every_trace_are_gone` (run with `frappe.enqueue` stubbed, as with no worker) |
| 2 | Boundary | `test_the_boundary_is_the_day_after_six_months` (skips itself on a day with no exact 6-month date, e.g. 31 March) |
| 3 | Active / Inactive / Suspended kept | `test_anyone_not_left_is_kept_whatever_the_date` |
| 4 | Left with no date | `test_a_person_past_due_and_a_leaver_without_a_date_raise_one_alert` |
| 5 | Rehire on the same record / lock re-check | `test_the_lock_recheck_spares_a_person_rehired_after_the_list_was_made` |
| 6 | D-1 | `test_d1_an_employee_edited_in_the_last_30_days_waits` |
| 7 | Grooming switched off: still erases | `test_it_still_erases_with_grooming_switched_off` |
| 8 | Dry run | `test_the_dry_run_erases_nothing_and_counts_what_the_real_run_erases` |
| 9 | Run twice | `test_a_second_run_does_nothing_and_raises_nothing` |
| 10 | Slip, row, Additional Salary stay | `test_the_slip_its_grooming_line_and_the_additional_salary_stay` |
| 11 | Draft slip | `test_a_draft_slip_holds_the_person_and_is_counted` |
| 12 | One failure | `test_one_record_that_will_not_erase_stops_nobody_else_and_logs_an_id_only` |
| 13 | No desk delete | `test_the_administrator_cannot_delete_a_mark_or_a_review_from_the_desk` |
| 14 | Other people / D-2 | `test_d2_a_rehire_on_a_new_record_and_other_people_keep_their_marks` |
| 15 | Hook line | `test_the_daily_hook_line_exists` |
| new | Ships off | `test_it_ships_off_and_the_daily_run_then_erases_nothing` |
| new | Self-check on a soft copy / clean site | `test_a_deleted_document_copy_raises_the_alert`, `test_a_clean_site_raises_nothing` |

## 6 · Every guard broken on purpose

Each guard was taken out, the module run, and the file put back (script in my scratchpad,
not committed). **All 18 were caught.**

| Guard removed | Test that failed |
|---|---|
| `no_feed_on_delete` on the mark | every-trace test and 8 others (the erase fails on the "Deleted" comment) |
| `on_trash` refusal, mark | desk-delete test |
| `on_trash` refusal, review | desk-delete test |
| `docstatus` set to 2 | every-trace test and others |
| `delete_dynamic_links` in the same transaction | every-trace test (run with no worker) |
| Event Participants deleted first | every-trace test |
| `relieving_date is set` | left-without-a-date test |
| D-1 30-day wait | D-1 test |
| `<` made `<=` (boundary) | boundary test |
| `status = Left` | Active / Inactive / Suspended test |
| re-check under the lock | lock re-check test |
| draft-slip skip | draft-slip test |
| the erase switch | ships-off test |
| per-person savepoint | one-failure test |
| self-check after a real run | left-without-a-date test |
| Deleted Document count in the self-check | soft-copy test |
| dry run erases nothing | dry-run, draft-slip, D-1 and other tests |
| the daily hook line | hook test |

## 7 · Commands run and what they said

All in my own containers `hrlocal-066r` + `hrlocal-066r-redis`, volume
`hrlocal-066r-sites`, site `test066r` (database `_066ret`, a copy of `_066groom`).
`hrlocal-bench` and every other container untouched. No migrate, no clear-cache, no build.

| Command | Result |
|---|---|
| `run-tests --module alvoraa_portal.tests.test_grooming_erase_066` | 18 tests, OK |
| `run-tests --module ...test_grooming_066` | 64 + 1 tests, OK |
| `run-tests --module ...test_grooming_cap_066` | 42 tests, OK. **First run had 1 failure**: a stray Version row on Grooming Review left by my own guard-breaking run, which I stopped part-way. The row was mine (`data` "{}", written by my test helper). I deleted it and re-ran: OK. Not a code fault, but it shows a killed run of the new module leaves rows the 066 tests count |
| `run-tests --module ...test_pay_slip_marks_067` | 18 + 2 tests, OK |
| `python scripts/check_app_integrity.py` | 822 checks, OK |
| `ruff check` on the five changed files | All checks passed |
| `bench set-config --help` | confirms `-p` exists, so the switch commands in section 1 are real |

Not run: the full alvoraa_portal suite, `test_payroll_*`, `test_salary_report`,
`test_portal_security_010`. The change adds no endpoint, no permission and no payroll code,
so I judged the modules above enough; the full suite belongs to the run before a dev push.

## 8 · Non-functional dimensions, against the code written

| Dimension | Before → after | Verdict |
|---|---|---|
| Performance | No request path changes. Off: one config read a day. On: 3 queries to find people, about 30 per record, at most 50 people a run | neutral |
| Security | The Administrator desk delete that kept a full copy is closed. No endpoint added; nothing whitelisted. The `docstatus` write is reachable only from the scheduler and `bench execute` | improves |
| Reliability | Savepoint per person, lock re-check, draft-slip skip, outer catch with a title only, self-check. The irreversible step is behind the switch and the dry run | improves |
| Scalability | Grows with leavers; capped at 50 people a run | neutral |
| Maintainability | ~150 lines in the module that owns the rules; the rule is one function used by the job, the re-check and the self-check | neutral |
| Data integrity | Payroll records untouched; no orphan bell, Version or comment; workings report shows 0 reds for erased months (D-5) | neutral |
| Compliance / privacy | Meets "employment + 6 months, then erased, no soft delete" once switched on. Logs carry an employee id or counts, never a name or the "Other" text | improves |

## 9 · What else moved while I worked

`origin/dev` was at f207e82c when I branched. At the end it was at 57d1a157: nine ALV-217
commits (slice 070, phone readability) came in - portal.js, frame.css, the portal parts,
the 070 docs and two scripts. None touches `grooming*.py`, `hooks.py` or
my test. I have not rebased; the branch still sits on f207e82c. Rebase before it goes to
dev, then run the four modules again. The work board row is under `066-retention`.

## 10 · Gaps and shortcuts

- **Intentional trade-off.** The switch reads `frappe.conf`, which also merges
  `common_site_config.json`. Set it per site only.
- **Temporary debt.** The switch and the dry run exist only until counsel answers Q-1 and
  D-3. If counsel asks for a dispute hold (D-3), that is new work. Removing the switch later
  is one `if` and one test.
- **Acceptable simplification.** D-1 trusts that nothing re-saves leavers' Employee rows
  every month. I found no job that does (grep of `set_value("Employee"` in our apps). If one
  appears, nobody is ever erased, and the self-check would not see it because it uses the
  same rule. The dry run's `people` count on dev is the place to notice.
- **Acceptable simplification.** The dry run lists employee ids in the operator's terminal
  only. They are not logged.
- **Not done.** No full alvoraa_portal suite run (two hours); see section 7 for what ran.
- **Not in scope, noted.** The existing "Grooming notice not sent for {mark}" Error Log keeps
  a traceback; Log Settings clears it after about 30 days (strategy section 3).

## 11 · Subtract pass

Removed: a `this_run_would_erase` count in the dry run (the cap is documented); the plan
to check orphan Version rows in the self-check (the erase deletes them in the same
transaction, and a test proves it). Kept: the switch and the dry run (asked for), the
batch cap, D-1.

## 12 · Rebase, 26 Oct 2026

Rebased onto origin/dev 52fc3451. What came in, 25 commits: slice 071 (In no seat tray,
ALV-228 scope fix: portal.js, positions.html, panels.css, register.py, test_unseated_071.py),
ALV-217 / slice 070 (phone readability: portal.js, frame.css, portal parts,
test_leave_permissions.py), and 52fc3451 (066 grooming network-error message: portal.js and
portal_grooming_066_test.js). None touches my files. No conflicts.

Re-run on test066r in hrlocal-066r after the rebase: test_grooming_erase_066 18 OK;
test_grooming_066 64 + 1 OK; test_grooming_cap_066 42 OK; test_pay_slip_marks_067 18 + 2 OK;
test_payroll_flags 9, test_payroll_month 29, test_payroll_reprocess 12, test_payroll_rules
76, all OK; check_app_integrity 823 checks OK. The job was not switched on anywhere.

## 13 · Review fixes, 26 Oct 2026 (06-review-retention, 06b-security-verification-retention)

Both said SHIP WITH FIXES. Each fix has a test that fails when the fix is taken out.

| Finding | Fix | Test |
|---|---|---|
| Security M-2: `dry_run='true'` was a real erase (`cint('true')` is 0) | `erase_due` is a dry run unless `dry_run` is exactly 0 / "0" / false / "false" / "no". Anything else, including nothing at all, a typo, "true" or "yes", is a dry run. The daily hook is a new one-line `erase_daily`, the only real run that needs no flag. A real run still needs the switch on | `test_m2_anything_but_an_explicit_no_is_a_dry_run` |
| Security M-1: a wrong or runaway erase went unseen | Every run that found anybody writes one Error Log titled **"Grooming erase run"** with counts only: mode (dry/real), considered, held_draft_slip, erased, failed, marks, reviews, and `stopped` with the reason. No ids, no names | `test_m1_every_run_is_recorded_in_counts_only` |
| Security M-1: stop a runaway | A real run with more than 25 people due (after draft-slip holds) erases nobody and records `stopped: "N people due, more than the 25 allowed in one run"`. Site config `grooming_erase_max_people` raises it for one deliberate run | `test_m1_more_people_due_than_the_limit_stops_and_says_why` |
| Review m-1: the re-check read an old snapshot | The re-check is now itself the locking read (`get_value(..., for_update=True)` with the rule's filters), which sees the latest committed row | `test_m1_a_rehire_committed_while_the_job_runs_is_seen` (a second database connection rehires the person after the job's snapshot) |
| Review m-2/m-4, security m-1: a failed person lost history; one long uncommitted run | Commit after each person. A failure does a full rollback (which also drops Frappe's queued clean-up of the records it put back), logs the id, commits the log, and moves on | `test_m4_a_person_put_back_keeps_their_history` (Frappe's after-commit clean-up queued as on a server); `test_one_record_that_will_not_erase_...` (the person erased before the failure stays erased) |
| Review m-3, security m-2: held people used up the 50 places | The cap of 50 is gone; the 25-person stop replaces it. Draft-slip people are left out **before** the count, so they never take a place | `test_m3_people_held_by_a_draft_slip_take_no_place` |
| Review m-6, security QS-1: a transfer with a new Employee ID started the clock | A Left record that is the `employee` of a submitted Employee Transfer with `new_employee_id` set is never due. **[ASSUMPTION, Surbhi's call pending]**: the coordinator's recommendation, "a transfer is not the end of employment". Consequence: the old record's marks stay until a rule for them is decided (for example, follow the new record's clock). They are not counted by the self-check | `test_m6_a_transfer_to_a_new_employee_id_starts_no_clock` |
| Review m-5: an old slip cancelled and amended after the erase | **Not changed, written down here.** If HR cancels and amends a submitted slip for a month whose marks were erased, with grooming on, the engine prices the amended draft from the marks, finds 0, cancels its grooming Additional Salary and drops the line. The corrected slip then refunds a fine that was properly deducted, with no note. It needs an unusual action on someone who left over 6 months ago. Surbhi to accept next to D-5, or ask for the engine to leave a month's grooming line alone once its marks are erased | none (traced only) |
| Review nit, security m-6 | One comment line in the test's clean-up: never run this module on a real site | - |

**Why an Error Log row for the run record.** No schema, no new DocType; `health.py` already
pulls Error Log titles to the control plane; it is the place D-6 says Surbhi reads. Costs,
stated plainly: it shows up among errors on the health page (it is not one), and Frappe's Log
Settings clears Error Log after 14 days by default. A run record must be read within two
weeks, or Log Settings raised for Error Log. A new log DocType would keep it longer but adds a
schema, permissions and a migration for one row a day; I did not think that earns it.

**Subtract pass on the fixes.** Removed: the 50-person cap (`ERASE_BATCH`), replaced by the
25-person stop; the draft-slip check inside `_erase_person` (the run now leaves held people
out before it starts; the inner check only repeated it). Kept: `erase_daily` (one line; it is
what lets `erase_due` default to a dry run).

**Not changed, still open from the reviews:** the self-check stops when the job stops
(security m-3); the health page sends only the top 8 titles (m-4); REST and bulk delete have
no test of their own (they reach the same `on_trash`); D-1 trusts `modified` (W-1); Server
Script can call the erase with the flag (R-3). Each needs Surbhi's word, not code.

**Every guard broken on purpose, again (26 Oct).** 24 guards: the 18 from section 6 as they
now stand, plus the strict dry-run parse, the run record, the 25-person stop, held people
taking no place, the per-person commit, the full rollback, the fresh locking read and the
transfer rule. **All 24 caught.** The first try missed the full-rollback guard: marks are
erased newest first, so the "first mark erases, second fails" test was failing on the wrong
mark and nothing had been queued. The test now fails on the second erase call, whichever
mark that is, and catches it.

**Correction to section 7.** The stray Version row that failed `test_ac63` in
test_grooming_cap_066 was not left by stopping my run part-way. It came back on 26 Oct
after a complete guard-breaking run: a broken guard (for example, no `delete_dynamic_links`)
erases a review but leaves its Version row, and my test clean-up looked for traces only by
the names of records that still existed. The clean-up now wipes traces by every name a test
wrote. After deleting the one stray row (mine, `data` "{}"), the cap module passes: 42 OK.

**Runs on test066r after the fixes (26 Oct):** retention 25 OK; grooming 64 + 1 OK; cap 42
OK (after the stray row above); 067 18 + 2 OK; payroll flags 9, month 29, reprocess 12,
rules 76, all OK; integrity 823 checks OK.
