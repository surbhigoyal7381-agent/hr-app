---
slice: 066-grooming-red-mark
artifact: 06-review-retention (senior architect review, change-process step 5, for the grooming erase job)
author: hrms-technofunctional-reviewer
date: 2026-10-26
reviewed: branch slice/066-retention, tip 4edebe09, 8 commits on origin/dev 52fc3451
  (origin/dev re-fetched 26 Oct: still 52fc3451, so nothing new to absorb)
inputs: 04b-retention-job-strategy.md (dev-integration-2026-10-22 worktree),
  05-implementation-notes-retention.md, the diff, Frappe v16.33.1 source in hrlocal-066r
ran on: my own throwaway site test066r_rev (database _066rev, a copy of _066groom) in
  hrlocal-066r. Not test066r, not test066r_sec, nothing shared, nothing on any server.
---

# 066 retention: review of the grooming erase job

## 1 · Verdict

**SHIP WITH FIXES - ready to present for a push to dev with the switch OFF. It is not
ready to be switched on anywhere, and must not be until counsel answers in writing.**
No Blocker. Four Minor faults are proven or traced. None of them can do harm while the
switch is off, and two of them should be fixed before the first real erase.

`SHIP WITH FIXES` here is not permission to deploy. Surbhi decides.

What is **proven** (I ran it): the 18 retention tests pass on my own site; the integrity
check passes; six break-it probes below, with their output. What is **inferred**: anything
about production timing, the production database version and the real scheduler. What is
**not checked**: production's MariaDB settings, whether telemetry is on, and how often
Left Employee rows are re-saved on the live tenants (which decides whether D-1 ever lets
anyone through).

**Release gate, not a code fault.** Counsel's written answer on Q-1 (the fines register
at 6 months) and D-3 (a hold for open disputes) is still missing. The code honours that:
nothing is erased unless `grooming_erase_enabled` is 1 in the site config. Shipping the
code is fine; switching it on is not.

## 2 · Blockers

None.

## 3 · Majors

None.

## 4 · Minors (P3 - ship, tracked, fix before the switch goes on)

### m-1 · The "re-check under the lock" reads old data. A rehire during the run is not seen. (Proven)

`grooming.py` `_erase_person`: the row lock is taken with `get_value(..., for_update=True)`,
but the re-check is a plain `frappe.get_all("Employee", filters=_due_filters(...))`.
MariaDB runs at REPEATABLE READ (local: 10.8.8, `tx_isolation` REPEATABLE-READ), so a
plain read sees the snapshot from the start of the job, not the row just locked.

- *State:* person is Left and due. The job starts (its first read fixes the snapshot).
  Another session sets the person Active, clears the relieving date and commits.
- *What happens:* `_erase_person` locks the row, re-checks against the old snapshot, still
  sees "Left", and erases.
- *Proof (probe P2):* `_erase_person` returned `[1, 0]` and the mark was gone, while the
  database row already read `status = Active`.
- *Why it is wrong:* the strategy and the notes say "every change to the Employee is
  obeyed". It is not, for a change made while the job runs. The test
  `test_the_lock_recheck_spares_a_person_rehired_after_the_list_was_made` is sequential
  (one connection), so it cannot catch this.
- *Real-world chance:* small. The run lasts seconds to two minutes, just after midnight.
  The marks lost are from an employment that ended more than 6 months earlier.
- *Smallest fix:* make the re-check itself a locking read:
  `frappe.get_all("Employee", filters=_due_filters(today, [employee]), pluck="name", for_update=True)`
  and drop the separate `get_value` line. [Inferred: `get_all` accepts `for_update` in
  v16; check when fixing.] A two-connection test like probe P2 would pin it.

### m-2 · A person who fails half way loses the history of the marks that were rolled back. (Proven)

`_erase_one` calls `frappe.delete_doc`. Frappe's `delete_doc` (delete_doc.py, the
`frappe.enqueue(... delete_dynamic_links, enqueue_after_commit=True)` call) puts a clean-up
job on the "after commit" list. A rollback **to a savepoint** does not clear that list
(database.py `rollback`: only a full rollback calls `after_commit.reset()`).

- *State:* one person, two marks. Mark A erases; mark B fails (any error).
- *What happens:* the savepoint brings A back. But the queued clean-up for A stays. When
  the job commits, the worker deletes A's Version rows, Notification Log (the bells),
  Comments, ToDo, DocShare and Document Follow - while A itself still exists.
- *Proof (probe P4):* after the rollback, A existed with 1 Version row and the after-commit
  list still held `delete_dynamic_links(Grooming Mark, A)`. Running what the worker would
  run left A with 0 Version rows.
- *Why it is wrong:* the person's records are "atomic per person" for the marks, but not
  for their history. If the failure repeats every day (for example a record that will not
  delete), the marks stay with their audit trail gone. Low harm: these records are already
  past their retention date.
- *Smallest fix (also fixes m-4):* commit after each person who erased cleanly, and on a
  failure do a full `frappe.db.rollback()` (which clears the after-commit list) instead of
  a savepoint rollback. This is the usual Frappe pattern for a scheduled job.

### m-3 · People held by a draft slip, or who keep failing, use up the cap of 50 for ever. (Proven)

`_due(today, limit=ERASE_BATCH)` takes the 50 oldest due people **before** the draft-slip
skip and before any failure. `_erase_run` then skips or fails them and stops.

- *State:* the oldest due person has a draft Salary Slip. Cap set to 1 for the probe.
- *What happens (probe P3):* the run returned `people: 0`; the next person, who was due
  and had no draft slip, kept their mark.
- *At the real cap:* every held or failing person takes one of the 50 places every day.
  With 50 of them, nobody else is ever erased. The self-check would raise "people past
  due" daily, so it is visible, not silent.
- *Smallest fix:* walk the full due list and stop after 50 people **erased**, or leave the
  draft-slip people out of the query.

### m-4 · A big first run can pass the 300-second queue limit, with no clear end state. (Measured locally, extrapolated)

A daily job runs on the `default` queue, 300 seconds (scheduled_job_type.py
`get_queue_name`; background_jobs.py default timeout 300).

- *Measured (probe P5):* 50 people with about 40 marks each (1,961 marks, each with a
  Version row) took **119 seconds** on the local Docker bench. About 60 ms a mark. The
  strategy's estimate ("about 2,500 queries, a few seconds" for a 240-record leaver) is
  too low: 240 records is about 14 seconds a person here.
- *Inferred:* 50 people averaging more than about 100 records each passes 300 seconds.
  The whole run commits only at the end. RQ raises a timeout inside the job, which the
  per-person `except Exception` would catch and log as an "Employee X" failure; RQ then
  kills the job about 60 seconds later. Nothing is committed, and the next day starts with
  the same 50 people. [Inferred from RQ's behaviour, not run.]
- *Real-world chance at DTC:* low for at least a year. Marks are capped at 3 a month and
  grooming is not on yet, so early leavers will have few records.
- *Smallest fix:* the per-person commit in m-2. Then a timeout keeps the work done so far.

### m-5 · An old slip cancelled and amended after the erase silently drops the fine. (Traced, not run)

`payroll_slip.py` `on_salary_slip_validate` → `month_summary` counts live marks →
`_set_additional_salary`.

- *State:* a leaver's marks were erased. Later HR cancels and amends one of their old
  submitted slips (say, to correct the full-and-final), with grooming switched on.
- *What happens:* the amended draft is priced again from the marks, finds 0 reds, cancels
  the engine's Additional Salary for grooming and drops the line. The slip-submit check
  then compares 0 with 0 and passes.
- *Why it matters:* a corrected slip refunds a fine that was properly deducted, with no
  note. D-5 accepted "0 reds" in the workings **report**; this is a **slip**.
- *Owner:* Surbhi (rule). Options: (a) accept, written next to D-5; (b) the engine leaves an
  engine Additional Salary alone for a month when the person's marks have been erased.
  I recommend (a) for now - it needs an unusual action on a person who left 6 months ago.
  Ranked P3 until she says.

### m-6 · A company transfer with a new Employee ID starts the erase clock. (Traced; a question)

hrms `employee_transfer.py` `on_submit`, when "Create New Employee ID" is ticked: the old
record gets `relieving_date = transfer_date` and `status = Left`.

- *What happens:* 6 months and 30 days after the transfer, the marks on the old record are
  erased, although the person still works for the group.
- *Why it may be wrong:* counsel's rule is "end of employment + 6 months". A transfer is not
  the end of employment. D-2 covered a **rehire** on a new record, not a transfer.
- *Question for Surbhi (should know):* is a company transfer with a new ID the end of
  employment for this rule? If yes, nothing to do. If no, the smallest change is to skip a
  record that has a submitted Employee Transfer with `new_employee_id` set. Ranked P3
  meanwhile; it changes nothing while the switch is off.

## 5 · Nits

- In an overlapping second run (only possible if someone runs `erase_due` by hand during
  the daily run), the second run reads the first run's deleted marks from its snapshot and
  counts them again. Nothing is harmed; the counts are wrong. m-1's fix covers most of it.
- The test file's `_wipe` deletes **every** Deleted Document row for these doctypes and
  every Error Log with the two alert titles. Right on a test site; it would destroy a real
  alert if anyone ran this module on a tenant. One comment line in the file would say so.

## 6 · Break-it list from the brief, one by one

| Attack | Result | Label |
|---|---|---|
| Blank relieving date (Frappe reads 0001-01-01) | Guard holds. Probe P1: Left with no date is not due, is listed by `_left_without_date`, and a real run kept its mark. Test `test_a_person_past_due_and_a_leaver_without_a_date_raise_one_alert` also covers it | Proven |
| Left person re-activated, or date moved, before the run | Kept (re-check). Tests for Active/Inactive/Suspended, D-1 | Proven |
| Same, **during** the run | Erased - m-1 | Proven |
| Rejoin on the same record | Kept while Active; clock restarts at the next relieving date | Proven by test |
| Rejoin on a new record (D-2) | Old record's marks go; new record's stay. Test d2 | Proven |
| Company transfer with a new ID | Clock starts at the transfer - m-6 | Traced |
| Draft slip | Person skipped and counted; but uses a cap place - m-3 | Proven |
| Submitted slip | Slip, its grooming row and the Additional Salary stay (test). The submit check only runs on drafts, and drafts block the erase. Later amend - m-5 | Proven / traced |
| 30-day wait (D-1) | Holds; `modified` compared to midnight 30 days back. It trusts `modified`: `db_set` and `save` update it; a raw `set_value(..., update_modified=False)` would bypass it (none found in our code for this field) | Proven by test; inferred |
| Timezone at the edge | `nowdate()` uses the site time zone (Asia/Kolkata on my site). `add_months` on the 29th-31st rounds to the month end, which only ever delays. The boundary test skips itself on days with no exact 6-month date, so it cannot fail on those days | Inferred |
| Grooming switched OFF | Still erases (test) - it never calls `is_on()` | Proven |
| Erase switch OFF | Daily run returns `{"switched_on": 0}` before any query (test) | Proven |
| Dry run erases nothing | Works with the switch off; counts match the real run (test) | Proven |
| Self-check | Raises one titled Error Log with counts only (tests). It cannot see D-1 holding people for ever, because it uses the same rule (noted by the engineer) | Proven |
| Administrator desk delete | Refused by `on_trash`; no Deleted Document (test). List-view bulk delete goes through the same `delete_doc` | Proven / inferred |
| Frappe's "Deleted" comment | Not written: `no_feed_on_delete` is read by `insert_feed` (delete_doc.py 553-560) | Proven |
| Version, comment, file, notice rows | Deleted in the same transaction (test with the worker stubbed). Communication and Activity Log rows would be **unlinked, not deleted** by Frappe - none exist for these doctypes (no email permission on either) | Proven / inferred |
| Emails already sent | Email Queue rows carry the notice text with no reference to the mark; cleared by Log Settings. Unchanged by this diff (Q-3) | Inferred |
| Permission of the job | Not whitelisted. No `ignore_permissions` added in app code (the 2 in the diff are in the test file). Runs as Administrator | Proven by grep |
| 500 people due at once | 50 a day: 10 days. The self-check raises "people past due" every day until the queue drains. Timing - m-4 | Proven (P5: 61 people due; 50 erased; 11 left for the next run) |
| Crash half way | Marks: atomic per person (savepoint). History: not - m-2. Whole run killed: nothing committed | Proven / inferred |
| Hot files | `hooks.py` gets one line at the end of `daily`. origin/dev has not moved since 52fc3451. All 8 commits are the engineer's, no merge commits | Proven |

## 7 · Acceptance criteria (strategy section 9)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Every trace gone | Met | test passes; P4 shows the gap only on failure (m-2) |
| 2 | Boundary | Met | test (runs today, 26 Oct) |
| 3 | Not Left: kept | Met | test |
| 4 | Left, no date: kept, counted, alert | Met | test + probe P1 |
| 5 | Rehire / lock re-check | Partial | sequential case met; concurrent case fails (m-1) |
| 6 | D-1 | Met | test |
| 7 | Grooming off: still erases | Met | test |
| 8 | Dry run | Met | test |
| 9 | Run twice | Met | test (sequential) |
| 10 | Slip, row, Additional Salary stay | Met | test |
| 11 | Draft slip skipped and counted | Met | test; cap side effect m-3 |
| 12 | One failure stops nobody; id-only log | Met | test; history side effect m-2 |
| 13 | No desk delete, no copy | Met | test |
| 14 | Other people untouched | Met | test |
| 15 | Hook line | Met | test |
| - | Ships off | Met | test |

## 8 · Non-functional

| Dimension | Strategy said | What the code does | Finding |
|---|---|---|---|
| Performance | neutral; "a few seconds" | Off: one config read a day. On: about 60 ms a record, measured | Neutral for requests. Estimate too low - m-4 |
| Security | improves | Closes the Administrator delete that kept a full copy. No endpoint | Agree |
| Reliability | improves | Savepoint per person; outer catch; self-check | Mostly. m-2, m-4 |
| Scalability | neutral, capped | Cap of 50 people, not records | m-3, m-4 |
| Maintainability | neutral | Rule in one function, used three times | Agree |
| Data integrity | neutral | Payroll records stay | m-5 on an amended slip |
| Compliance / privacy | improves | Hard delete, no copy, id-only logs | Agree, once switched on and counsel agrees |

## 9 · Compliance

| Obligation | Mechanism | Test | Status |
|---|---|---|---|
| Erased at employment + 6 months | `_due_filters`, daily hook | boundary, every-trace tests | **Partial** - built, but OFF until counsel; m-6 asks what "end of employment" means for a transfer |
| No soft delete, no Deleted Document copy | `delete_permanently=True`, `on_trash` refusal, self-check count | desk-delete, soft-copy tests | Discharged |
| No "Deleted" comment naming the record | `no_feed_on_delete` | every-trace test | Discharged |
| No side records left | `delete_dynamic_links` in the transaction, Event Participants first | every-trace test | Discharged; gap on failure (m-2) |
| No personal data in logs | Fixed titles; id or counts only | one-failure test, self-check test | Discharged. [Not checked: if telemetry is on, Frappe's `capture_exception` sends the traceback message to Sentry; the message is the id only] |
| Payroll records kept | Erase touches only the two doctypes | slip test | Discharged |
| Hold for open disputes (D-3) | None | None | **Not discharged** - waiting on counsel |

## 10 · What to delete

Nothing. Each part earns its place: the switch and dry run were asked for, the cap bounds
the run, the self-check is the only proof of the outcome. The site-config switch is the
one setting the strategy said it would not add; Surbhi asked for it on 25 Oct, and it is
one `if` to remove once counsel answers.

## 11 · What was done well

- **The rule lives in one function** (`_due_filters`) used by the job, the re-check and the
  self-check, so they cannot drift apart.
- **`on_trash` closes a real gap that existed before this slice**: the Administrator could
  delete a mark and Frappe kept a full copy for ever.
- **`delete_dynamic_links` is called in the same transaction** instead of trusting Frappe's
  queued job, and the test stubs the queue to prove it - a test that fails if the worker is
  down, which is what production looks like at times.
- **Every guard was broken on purpose** and a test went red each time. That is the
  "tests test what they claim" lesson applied properly.
- **The blank-date fault was found by the engineer's own test**, before review.

## 12 · Commands I ran

| Command | Result |
|---|---|
| `bench --site test066r_rev run-tests --app alvoraa_portal --module alvoraa_portal.tests.test_grooming_erase_066` | `Ran 18 tests in 252.754s` `OK` |
| `python scripts/check_app_integrity.py` (in the 066-retention worktree) | `823 checks` `OK - all consistent` (doctype-shadowing check skipped: no bench path) |
| Probes P1-P5, one Python script on test066r_rev, each rolled back | Output quoted in m-1 to m-4 and section 6 |
| MariaDB: `select version(), @@global.tx_isolation` | `10.8.8-MariaDB`, `REPEATABLE-READ` |

Not run: the wider payroll and 066 modules (the engineer ran them after the rebase; the
diff does not touch their code), anything on dev or production.

## 13 · Confidence

- **High** on m-1, m-2, m-3: each was run and the output is above.
- **Medium** on m-4: the 119-second figure is real, but it is a Windows Docker bench; the
  production machine may be faster. What happens at the timeout is inferred from RQ.
- **Medium** on m-5 and m-6: traced through the code, not run.
- **Not checked:** production's MariaDB version and isolation (MariaDB 11.8+ with
  snapshot isolation would turn m-1 into a failed run instead of a wrong erase); whether
  telemetry is on; how often Left Employee rows are re-saved on dtc/aahr (decides whether
  D-1 ever lets anyone through).

## 14 · Open questions

| Kind | Question | Owner | Meanwhile |
|---|---|---|---|
| Must know (for switch-on, not for the push) | Counsel's written answer on Q-1 and D-3 | Surbhi / counsel | Switch stays off everywhere |
| Should know | Is a company transfer with a new Employee ID the end of employment? (m-6) | Surbhi | P3 |
| Should know | Accept that an amended old slip drops an erased fine? (m-5) | Surbhi | P3 |
| Nice to know | Owner for m-1 to m-4 fixes before switch-on | `hrms-fullstack-engineer` | Tracked |

## 15 · Subtract pass on this review

Removed: a finding on `_with_records()` loading every employee with a mark (fine at our
size, no failure I could state); a finding on Sentry (moved to "not checked", it is
Frappe-wide, not this diff); a note on the dry run's extra counts (they were in the
approved strategy).

---

## Re-review, 26 Oct 2026 (tip d9414eb2, on origin/dev 52fc3451)

### Verdict

**SHIP - provisional. Ready to present for a push to dev with the switch OFF. Not ready to
switch on until counsel answers and Surbhi decides r-1 below.** `SHIP` is not permission to
deploy; Surbhi decides.

**I could not run the tests.** I could not make my own throwaway site in hrlocal-066r: the
`sites` folder is owned by root, and `bench new-site` needs the MariaDB root password, which
I was not allowed to read. I did not use test066r or test066r_sec. So every "proven" below is
proven by reading the code (and Frappe's own source in the container), not by a run. The
engineer reports retention 25 OK, grooming 64+1, cap 42, 067 18+2, payroll 9/29/12/76, all
OK, on test066r (section 13 of the notes) - **not reproduced by me**.

What I did run: `python scripts/check_app_integrity.py` -> `823 checks`, `OK - all
consistent` (doctype-shadowing check skipped, no bench path); `py_compile` of grooming.py and
the test file -> OK; the dry-run parser on 21 inputs (table below). origin/dev re-fetched: one
new commit, 479ad441 (module_access.py and three tests), touches none of this slice's files.

### Each earlier finding, tried to break

| Finding | Fixed? | Evidence |
|---|---|---|
| Sec M-2: mistyped dry run erases | **Fixed** (proven by read + parser run) | `_real()` grooming.py:1608-1611. Dry for `'true'`, `'True'`, `'yes'`, `1`, `'1'`, `None`, `''`, `[]`, `{}`, `'dry'`, `'o'`, `0.0`. Real only for `0`, `'0'`, `' 0 '`, `False`, `'false'`, `'no'` (any case). No argument -> default `1` -> dry. A mistyped key (`dryrun=0`) raises TypeError: `erase_due` takes only `dry_run`, so nothing runs. The hook is `erase_daily` (hooks.py:413), which calls `erase_due(dry_run=0)`, and that returns `{"switched_on": 0}` unless `grooming_erase_enabled` is 1 (grooming.py:1628-1630). Neither function is whitelisted |
| Sec M-1: a runaway erase is invisible | **Fixed** (proven by read) | `_record()` writes one Error Log titled "Grooming erase run": mode, considered, held, erased, failed, marks, reviews, and `stopped` (numbers only). No id, no name, no marker text. The message is given, so Frappe stores it instead of a traceback. More than 25 due (after held people are removed) erases nobody and records why (1668-1671); `grooming_erase_max_people` raises it (1527; missing, 0 or negative means 25). Test `test_m1_every_run_is_recorded_in_counts_only` asserts the exact count dict and that neither the id nor the "Other" text appears |
| Review m-1: re-check read an old snapshot | **Fixed** (proven by read of Frappe source) | The re-check is now `get_value(..., _due_filters(...), for_update=True)` (1592). With a list filter Frappe builds the query with `for_update` (database.py `get_values`, the list-filter branch), so it is a locking read and sees the latest committed row. The run also commits before the loop and after each person, so each person starts a fresh snapshot. The test opens a second connection, rehires after the job's snapshot, and expects `None` - it would fail on a plain read |
| Review m-2 / sec m-1: rollback lost Version and bell rows | **Fixed** (proven by read) | Full `frappe.db.rollback()` per failed person (1681). Frappe's `rollback()` without a savepoint calls `after_commit.reset()` (database.py:1201-1203), and `frappe.enqueue(..., enqueue_after_commit=True)` puts the clean-up on that list (background_jobs.py:205-206). `delete_dynamic_links` runs inside the person's transaction, so its deletes roll back too. Test `test_m4_...` reproduces the server's queued clean-up and expects 1 Version and 1 bell per mark - it fails if a savepoint is used |
| Review m-4: one long uncommitted run | **Fixed** | Commit per person (1677). A timeout now keeps the people already done. The 25-person stop roughly halves the measured 119 s worst case [Inferred] |
| Review m-3 / sec m-2: held people use up the cap | **Fixed** | Draft-slip people are removed before the count (1665); the old `limit=50` is gone. Test `test_m3_...` (cap 1, one held, one free -> free erased, not stopped) |
| Review m-6: transfer to a new ID starts the clock | **Fixed as recommended, with a new gap - r-1** | `_transferred()` (1535-1542) excludes a record that is the `employee` of a submitted Employee Transfer with `new_employee_id` set. Field names match hrms employee_transfer.py:28-33, 46-67. Test `test_m6_...` |
| Blank relieving date (0001-01-01) | **Still holds** | `["relieving_date", "is", "set"]` in `_due_filters` (1553); `_left_without_date` still counted and alerted |
| Switch OFF by default | **Holds in the repo** | `grooming_erase_enabled` appears only in code, comments and the test's `patch.dict`. No site config, fixture, patch or deploy file sets it. **Not checked:** the site_config.json of dev, dtc, aahr or production (no access) |
| No new `ignore_permissions` | **Holds** | The only two in the diff are in the test file's company and employee set-up |
| Nothing else regressed | **Inferred** | Since the first review the diff touches only the erase section of grooming.py (hunks from line 1500 on), one hook line, the test file and the notes. Grooming, cap, 067 and payroll code is unchanged. Not run by me |

### New findings

**r-1 · P3, decide before switch-on · A transferred person's old-ID marks are kept for ever,
and nothing reports them.** (Proven by read)
- *State:* A works under ID E1. A company transfer with "Create New Employee ID" makes E2 and
  sets E1 Left. Later A leaves for good from E2.
- *What happens:* E2's marks are erased 6 months after E2's relieving date. E1's marks are
  never erased, because `_transferred` always excludes E1. The self-check uses the same rule,
  so "people past due" never counts E1. Nobody sees it.
- *Why it matters:* counsel's rule is end of employment + 6 months, then erased. This keeps
  them past that, silently. The engineer wrote this down (notes section 13), so it is not
  hidden, but it has no owner and no alert.
- *Smallest fix (once Surbhi decides):* treat E1 as due when its `new_employee_id` record is
  due; or at least have the self-check count "kept because transferred" so it is seen.
  Owner: Surbhi for the rule, `hrms-fullstack-engineer` for the code.

**r-2 · P4 · The draft-slip check is no longer inside the person's lock.** (Proven by read)
It moved from `_erase_person` to the list step (1665). A draft slip made for a due person in
the seconds between the list and their erase is not seen, and that slip is then priced
without the marks. It needs HR to start a slip for someone who left over 6 months ago, just
after midnight, inside a run of under a minute. Backlog; one line moves it back if wanted.

**r-3 · P4 · "Every run is recorded" means "every run that found somebody".** (Proven by read)
`_record` writes nothing when nobody is due (1604). Fine for noise. But a missing record
cannot tell "nobody due" from "the job did not run" - the same blind spot as security m-3.
Write it next to m-3; no code needed now.

**Test gap · P4.** `test_m2_...` does not try `[]`, `{}` or a mistyped key. I proved those by
reading and by the parser run above. Optional to add.

### Subtract pass on this re-review

Removed: a worry about a File attachment's disk copy being deleted before a rollback (no
Attach field on either doctype, and I could not state a likely case); a note that the old
`erase_due` Scheduled Job Type on local sites would now run as a harmless dry run (local
only, never reached dev).

### What to delete

Nothing. `erase_daily` is one line and is what lets the safe default exist.

### Confidence

- **High** on M-2, M-1, the 25-person stop, held people and the transfer rule: short code,
  read in full.
- **Medium-high** on the lock and the rollback: I read Frappe's own source for both, and the
  engineer's tests target each, but I did not see them pass.
- **Not checked:** a test run on my own site (needs the MariaDB root password, or someone to
  make the site for me); the live sites' config files.
