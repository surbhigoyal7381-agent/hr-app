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
| See what it would do (any time, switch on or off; erases nothing) | `bench --site <site> execute alvoraa_portal.grooming.erase_due --kwargs "{'dry_run': 1}"` |
| Switch on | `bench --site <site> set-config -p grooming_erase_enabled 1` |
| Switch off | `bench --site <site> set-config -p grooming_erase_enabled 0` |
| Is it on? | `bench --site <site> execute alvoraa_portal.grooming.erase_switched_on` |
| Run the self-check by hand | `bench --site <site> execute alvoraa_portal.grooming.erase_self_check` |

The switch is read fresh by every scheduled job, so no restart is needed. With it off the
daily run returns `{"switched_on": 0}` before any query, and a real run by hand
(`erase_due` without `dry_run`) does the same. Order on any site, when Surbhi says so:
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
| `alvoraa_portal/grooming.py` | New section at the end: `erase_switched_on`, `_due_filters` (the rule, once), `_due`, `_draft_slip`, `_erase_one`, `_erase_person`, `erase_due` (daily + dry run), `_erase_run`, `_left_without_date`, `erase_self_check`. `add_days` import | The module that holds every grooming rule. Slice 065's erase shape, copied not imported (two uses) |
| `grooming_mark.py`, `grooming_review.py` | `no_feed_on_delete = True` and `on_trash` refusing any delete without the erase flag | The two lines per controller the strategy named |
| `hooks.py` | One line appended to `scheduler_events["daily"]` | Frappe's scheduler |
| `tests/test_grooming_erase_066.py` | 18 tests | Pins every guard |

## 3 · The rule as built

Due on a run when, all at once:

- Employee `status` is `Left`;
- `relieving_date` is set and earlier than the same day 6 months before today (so on the
  date 6 months on, the records are kept; the run after it erases them);
- the Employee row was last edited more than 30 days ago (**D-1**);
- the person has at least one mark or review.

The same filter runs again under a row lock on the Employee just before the erase, so a
rehire or a date change between the list and the erase is obeyed. A person with a **draft**
Salary Slip is skipped and shows in the self-check after 2 days. At most 50 people a run.

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
