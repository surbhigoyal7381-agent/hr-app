---
slice: 066-grooming-red-mark
artifact: 06b-security-verification-retention (security and privacy check of the grooming erase job)
author: hrms-security-privacy-engineer
date: 2026-10-26
code: branch slice/066-retention, tip 4edebe09, compared with origin/dev 52fc3451
inputs: 04b-retention-job-strategy.md and 01c-security-privacy-requirements.md (in
  .claude/worktrees/dev-integration-2026-10-22); 05-implementation-notes-retention.md (this branch);
  Frappe v16.33.1 source in container hrlocal-066r
where I ran things: my own throwaway site test066r_sec (database _066sec, a copy of _066ret) in
  container hrlocal-066r. Local only. I did not touch test066r, test066r_rev, any server or dev.
code changed: none
---

# 066 retention: security and privacy verification of the grooming erase job

## 0 · The answer first

**No blocker for the push to dev.** The job ships off. With the switch off, the only live
changes are good ones: nobody, not even Administrator, can delete a grooming record by hand
any more, so no full copy can land in Deleted Document.

**Do not switch the job on yet.** One item blocks it for certain, and three more should be
fixed or accepted in writing first:

| # | What | Level |
|---|---|---|
| 1 | Counsel's written answer on the register of fines (Q-1) and on a hold for open disputes (D-3) is still missing. Erasing is irreversible | **P1 - blocks switch-on** |
| 2 | Nobody would notice a run that erased the wrong people. The job's counts go nowhere: the scheduler throws away the return value | P2 - fix or accept in writing before switch-on |
| 3 | A mistyped dry run is a real erase. `dry_run='true'` or `'yes'` reads as 0 | P2 - fix or accept in writing before switch-on |
| 4 | Six smaller gaps (section 4, Minor) | P3 |

**One thing I need to say about myself.** This agent role wrote 01c, including PRIV-3 and
PRIV-4 on retention. The erase design is the engineer's (04b), so I am not checking my own
design here. But PRIV-4 said "this slice adds no delete" and the job now replaces it. Somebody
other than me should confirm that PRIV-4 is superseded by Surbhi's 25 Oct decision and 04b.
(The brief named "PRIV-3 (retention)". Retention is PRIV-4. PRIV-3 is "a removed mark is
cancelled, never deleted". After the erase, that stays true for 6 months after leaving, then
the whole record goes.)

## 1 · Threat model in four lines

1. **Who wants this, cheapest way?** Nobody wants to steal an erase. The risk is the other
   way: an erase that hits the wrong person, or one that leaves a readable copy behind.
   The cheapest wrong erase is a wrong date on an Employee record.
2. **Blast radius of one mistake.** Up to 50 people a day, for ever, on one site. It cannot
   be undone; a backup restore is erased again the next day.
3. **What is newly possible?** A daily job that deletes rows with no Deleted Document copy,
   and a database write that sets a submitted mark to cancelled without its cancel rules.
4. **How would we find out?** About failures: an Error Log title, pulled by the control
   plane health page. About a wrong erase: **we would not**. See finding M-1.

## 2 · Every check asked for, with the evidence

Labels: **Code** = I read the file and line. **Run** = I ran it on test066r_sec and read the
output. **Test** = an automated test pins it.

### 2.1 No readable copy left anywhere

| Where a copy could live | Result | Evidence |
|---|---|---|
| Deleted Document | **None.** `delete_permanently=True` skips `add_to_deleted_document` | Code: grooming.py:1558; frappe/model/delete_doc.py `if not delete_permanently: add_to_deleted_document(doc)`. Run: 0 rows after a real run. Test: `test_a_due_leavers_marks_reviews_and_every_trace_are_gone` |
| "Deleted" feed Comment | **Never written** (`no_feed_on_delete = True`) | Code: grooming_mark.py:34, grooming_review.py:32. Test: same test checks for `comment_type` "Deleted" |
| Version, Comment, ToDo, DocShare, View Log, Document Follow, Notification Log, Email Unsubscribe | **Deleted in the same transaction** by `delete_dynamic_links` | Code: grooming.py:1560; frappe delete_doc.py `delete_dynamic_links` lists exactly these. Test: the every-trace test, with `frappe.enqueue` stubbed as on a server with no worker (Version, Comment, Notification Log, ToDo, DocShare, Tag Link, Event Participants) |
| Event Participants | Deleted first | Code: grooming.py:1552. Test: every-trace test |
| File, Tag Link, global search | Inside `delete_doc` (`remove_all`, `delete_tags_for_document`, `delete_for_document`); files and tags are refused on these records anyway | Code: frappe delete_doc.py; grooming.py:611-624 (`refuse_side_record`). **Not in the test's list** (see m-5) |
| Communication, Activity Log | Frappe only clears the link, it does not delete the row. No grooming code writes either | Code: frappe delete_doc.py `clear_references`; no `sendmail`/Communication in grooming.py |
| **Email Queue** | **Not erased.** A grooming bell also goes out as email if the user's email notifications are on. The employee's mail carries the marker's name, the date, the fixed reason and the amount (never the "Other" text). Frappe clears Email Queue after 30 days by default, long before any erase | Code: grooming.py:852-858, 898-918; frappe notification_log.py `send_notification_email`; frappe hooks.py `default_log_clearing_doctypes` "Email Queue": 30. **Unknown:** the Log Settings on dev and production; I could not check them |
| Error Log, erase failure | **Employee id only**, no name, no reason, no text. `log_error` with a message attaches no traceback | Code: grooming.py:1630; frappe/utils/error.py:61-67. Test: `test_one_record_that_will_not_erase_stops_nobody_else_and_logs_an_id_only` |
| Error Log, whole job failed | Fixed title and fixed sentence, no traceback | Code: grooming.py:1590-1599 |
| Error Log, self-check | Counts only | Code: grooming.py:1665. Run: `{"left without a relieving date": 1}`. Test: `test_a_person_past_due_and_a_leaver_without_a_date_raise_one_alert` checks no id |
| Error Log, old "Grooming notice not sent for {mark}" | Mark name plus a traceback. Existing code, not new. Frappe's default clears Error Log after **14 days** (04b says 30) | Code: grooming.py:860-861; frappe hooks.py "Error Log": 14 |
| Scheduled Job Log | Nothing from the job. Frappe discards the return value | Code: frappe scheduled_job_type.py:143-161 |
| The audit line | None by design (D-4). The "Other" text audit line is ids only and ALV-212 drops it on dev and production anyway | Code: grooming.py `audit_other_text` |
| Background job arguments | Doctype and record name only, short Redis lifetime | Code: frappe delete_doc.py enqueue of `delete_dynamic_links` |
| Sentry | Only if telemetry is on and a Sentry address is set. Then the erase failure title and "Employee id" go out | Code: frappe/utils/sentry.py:100-130. **Unknown** on dev and production |
| Backups, MariaDB binary logs, delivered email in mailboxes | **Out of scope, listed.** They hold copies until they rotate out. Counsel Q-3, Q-4 | - |

### 2.2 Who can run the job, the dry run, and the switch

| Door | Result | Evidence |
|---|---|---|
| HTTP `/api/method/alvoraa_portal.grooming.erase_due` (and `_erase_run`, `_erase_person`, `erase_self_check`, `erase_switched_on`) | **Refused: none is whitelisted** | Run: `frappe.is_whitelisted` raised PermissionError for all five |
| The switch `grooming_erase_enabled` | Only by editing site config on the server (`bench set-config`). No code in our apps writes it | Code: grep shows only grooming.py reads it; `update_site_config` is used only by ai_leads/setup.py for its own keys |
| System Manager "Execute" on the Scheduled Job Type | Runs the real job, which obeys the switch. Harmless while off | Code: frappe scheduled_job_type.py:194-196 (`only_for("System Manager")`) |
| System Manager disables the Scheduled Job Type | The job and its self-check stop, silently (see m-3) | Code: self-check runs inside the job, grooming.py:1636 |
| Dry run | `bench execute` only, so only someone with shell on the server. Returns counts and employee **ids**, printed to that terminal, never logged. No names, no marker, no reason, no text | Code: grooming.py:1600-1615. Run: keys are `employees, left_without_date, marks, notices, people, reviews, skipped_draft_slip, switched_on, versions`. Test: dry-run test |
| Dry run with the switch off | Works, erases nothing | Test: `test_d1_...` and `test_a_draft_slip_...` call it with the switch off |

**Trap (P2, M-2):** a hand run with a mistyped flag is a real run. See section 3.

### 2.3 Every other way to delete a mark or a review

All tried on test066r_sec as Administrator unless said otherwise.

| Path | Result | Evidence |
|---|---|---|
| Desk delete / `frappe.delete_doc` | Refused (ValidationError), record stays, 0 Deleted Document | Run. Test: `test_the_administrator_cannot_delete_a_mark_or_a_review_from_the_desk` |
| REST `DELETE /api/resource/...` (= `frappe.client.delete`) | Refused for Administrator (on_trash), for an HR Manager and for a System Manager without HR (PermissionError: no role has Delete) | Run. **Not in the tests** (m-5). HTTP layer itself not exercised; same function |
| Bulk delete from the list (`delete_items` / `delete_bulk`) | Record stays, for Administrator, HR Manager and System Manager | Run. Not in the tests |
| `delete_doc(..., delete_permanently=True)` or `force=1` without the flag | Refused | Run |
| Deleting the Employee (would orphan the marks) | Refused: LinkExistsError, even when the only link is a **cancelled** mark or a review. Frappe v16 counts every linked row on delete | Run; code frappe delete_doc.py:356-381 |
| ERPNext "delete company transactions" | Not touched: neither doctype has a company field | Code: grooming_mark.json, grooming_review.json |
| `ignore_on_trash=True` | Used only by `bench uninstall-app` | Code: grep of frappe, erpnext, hrms, our apps |
| A Server Script calling `frappe.delete_doc(..., flags={"grooming_erase": True})` | **Would work.** `delete_doc` is exposed to Server Scripts. Only the Script Manager role can write one, held by Administrator alone (ARCHITECTURE.md:597). No soft copy is left, but the rule is skipped | Code: frappe/utils/safe_exec.py:29, 544. Residual risk R-3 |

### 2.4 Can it erase the WRONG person?

Each case run against the real rule with a dry run, then a real run (switch patched on).

| Case | Due? | Evidence |
|---|---|---|
| Left, relieving date blank | **No** - Frappe writes `relieving_date<>''`, which is false for NULL | Run: the SQL is `status='Left' AND relieving_date<>'' AND IFNULL(relieving_date,'0001-01-01')<'2026-04-26' AND modified<'2026-09-26'`. Test: self-check test |
| Left, date 6 months + 1 day, Employee edited today (D-1) | No | Run. Test: `test_d1_...` |
| Left, date in the future | No | Run |
| Active / Inactive / Suspended with an old date (rehire on the same record) | No | Run. Test: `test_anyone_not_left_...` |
| Exactly 6 months | No (kept on the day) | Run. Test: boundary test (ran today; it skips itself on a day like 31 March) |
| Rehired between the list and the erase | No - re-checked under the Employee row lock | Code: grooming.py:1567-1569. Test: lock re-check test (calls the function directly; no real race) |
| Same name, different person | No - everything is by Employee id | Code: grooming.py:1572-1573 |
| Another person, other company | Untouched | Test: `test_d2_...` |
| Date moved earlier by a desk save | Waits 30 days (D-1) | Run |
| **Date moved earlier with `update_modified=False`** (console, script, raw import) | **Due at once - D-1 bypassed** | Run. Needs code or console access. Worry W-1 |
| **Employee Transfer "create new employee id"** | The old record is set Left with relieving date = transfer date. **6 months later the marks are erased while the person still works in the group** | Code: hrms/hr/doctype/employee_transfer/employee_transfer.py:66-67. Question QS-1 |

### 2.5 Irreversibility guards

| Guard | Result | Evidence |
|---|---|---|
| Ships off | Yes. Off: returns `{"switched_on": 0}` before any query | Code: grooming.py:1590-1592. Test: `test_it_ships_off_...` |
| Dry run erases nothing, counts match the real run | Yes | Test: dry-run test |
| Cap of 50 people a run | In the query (grooming.py:1621, `limit=ERASE_BATCH`). **No test pins it** (m-5). People held by a draft slip still use up places (m-2) | Code |
| One person all-or-nothing | Yes for the records: a savepoint per person | Test: one-failure test. **But see m-1:** Frappe's after-commit clean-up still runs for rolled-back records |
| Alert on failure | Error Log titles "Grooming erase failed" and "Grooming erase self-check failed"; health.py pulls Error Log titles to the control plane | Code: health.py:68-92. But only the **top 8** titles by count are sent (`TOP_N = 8`, health.py:50) and Frappe clears Error Log after 14 days (m-4) |
| Alert on a runaway or wrong run | **None** (M-1) | - |

### 2.6 No new `ignore_permissions`

Ceiling unchanged: **425** non-test uses on origin/dev and on the branch (git grep over the
three apps, test files left out). The two new uses are in the test file's fixtures only. The
job runs as Administrator, so it needs none. There is no CI gate that counts this; noted in
section 6.

### 2.7 The slip and the Additional Salary stay, the mark goes

- **Stays (Test: `test_the_slip_its_grooming_line_and_the_additional_salary_stay`):** the
  submitted slip, its "Grooming Red Value" amount, the engine's Additional Salary (amount,
  component, date and a pointer to the rule set - no reason, no dates of marks;
  payroll_slip.py:205-219), and the slip note "N grooming reds at Rs X"
  (payroll_month.py:231-234).
- **Privacy:** what stays is that a deduction of X happened for N reds in that month. No reason,
  no day, no marker, no text. That is the wage record. Whether the register of fines must keep
  more, and for longer, is exactly counsel's Q-1. I do not know the law here and I have not
  stated a period.
- **Consistency:** after the erase the workings report shows 0 reds next to a slip that took
  money (D-5, accepted). A grievance about that deduction after the erase cannot be answered
  from the system: that is D-3.
- **Worry W-2:** if a slip for an erased month is ever reprocessed (a new draft after the
  erase), the engine would re-price it with 0 reds and replace the Additional Salary. That
  favours the employee and needs a payroll re-run of a month over 6 months old, so I rate it
  a worry, not a finding.

## 3 · Findings

None is P0. None blocks the push to dev.

### Major

**M-1 · A wrong or runaway erase is invisible. (P2 before switch-on.)**
*Actor:* the daily job. *State:* switched on; 40 Employee rows set to Left with relieving dates
a year ago by a bad import (or a transfer batch, QS-1), more than 30 days ago. *Path:*
grooming.py:1618-1637. *Result:* 40 people's marks and reviews are erased in one night. The job
returns `{"people": 40, ...}`, and Frappe throws that away (scheduled_job_type.py:156). No Error
Log, because nothing failed. The self-check looks for records that should be gone, never for
records that went too fast. Nobody learns of it.
*Smallest fix:* when a real run erases at least one person, write one Error Log with a fixed
title and **counts only** (people, marks, reviews), no ids. That is not a record about any
person, so it does not reopen D-4, and the health page already pulls it. Or Surbhi accepts in
writing that the weekly dry run by hand is the control.

**M-2 · A mistyped dry run erases for real. (P2 before switch-on.)**
*Actor:* the operator on the server. *State:* switch on. *Path:* `bench --site <site> execute
alvoraa_portal.grooming.erase_due --kwargs "{'dry_run': 'true'}"`, grooming.py:1590.
*Result:* `cint('true')` is 0 (Run: `cint` of "true", "True", "yes", "dry" all give 0), so this is
a real run. Same for forgetting `--kwargs`. Fail-open on the one irreversible action.
*Smallest fix:* give the dry run its own function name (for example `erase_dry_run()`) so the
real run is never one typo away. Or accept it in writing.

### Minor

**m-1 · A rolled-back person still loses their Version and bell rows. (P3.)**
`frappe.delete_doc` queues its own `delete_dynamic_links` to run after commit
(frappe delete_doc.py:200-209). A rollback to a savepoint does not cancel that queue
(frappe/database/database.py:1196-1200 resets the queue only on a full rollback).
*Run:* one person, two marks, the second forced to fail. After the run both marks are back,
2 Version rows; once the after-commit jobs run, 1 Version row is left. So a mark that was
**not** erased loses its history (who removed it, PRIV-3) and its bells. Only people already
due are affected, and the next run erases the rest. The test suite cannot see it: under
`run-tests` Frappe runs the job at once, inside the savepoint. *Fix:* note the length of
`frappe.db.after_commit` before each person and cut it back after a rollback; or accept.

**m-2 · Draft-slip holders use up the cap. (P3.)** `_due(limit=50)` (grooming.py:1621) picks
the 50 oldest due people, including those a draft slip will skip. 50 such people would stop
everyone else for ever. The self-check would alert after 2 days, so it is seen. Unlikely.

**m-3 · The self-check stops when the job stops. (P3.)** It runs only inside a real run
(grooming.py:1636). A disabled Scheduled Job Type, a stopped scheduler, or the switch turned
off after go-live means no "past due" alert at all. health.py reports the scheduler as a
whole, not this job.

**m-4 · The alert can be crowded out or aged out. (P3.)** health.py sends the top 8 titles by
count; a noisy tenant pushes a once-a-day title off the list. Frappe clears Error Log after
14 days by default (04b says about 30). D-6 names Surbhi as the reader; she should look at the
tenant's own Error Log list by title, not only the top-8 summary.

**m-5 · Guards that have no test. (P3.)** Verified by me by running, but nothing stops them
decaying: REST/`frappe.client.delete` and bulk delete; Employee delete refused; the cap of 50;
File, View Log and Document Follow missing from the test's `TRACES` list.

**m-6 · Test clean-up deletes real evidence if run on a shared site. (P4.)** `_wipe()`
(test_grooming_erase_066.py:137-138) deletes every Deleted Document row for these doctypes and
every Error Log with the two titles. Fine on a test site; never run it on dev.

### Worries (not findings: I cannot yet write a concrete wrong outcome)

- **W-1** D-1 is bypassed by any write with `update_modified=False` (Run: proven). Only code or
  console can do that. One existing hrms write uses it on Employee, for `documents_summary`
  only (employee_documents.py:153). If a future script fixes relieving dates that way, D-1 is
  gone.
- **W-2** Re-pricing an erased month (section 2.7).
- **W-3** If something re-saves every Employee monthly, nobody is ever erased, and the
  self-check (same rule) would not notice. The engineer found no such job; neither did I.

## 4 · Real data shape: what must exist to see the job work

- **Production (DTC):** grooming is off, no mark exists. The first real erase can come no
  earlier than about 6 months after grooming is switched on. Until then "0 erased" proves
  nothing.
- **Dev:** I did not check dev (not in scope, and I would not run anything there). To see the
  rule fire, a dev tenant needs one Employee with status Left, a relieving date more than 6
  months ago, last edited more than 30 days ago, and at least one mark. Marks are new (Oct
  2026), so dev will very likely show 0 for months too. **The local tests and my runs are the
  only proof today.**

## 5 · Questions

**Must know (block switch-on, not the push to dev):**

- **Q-1 (counsel)** - the register of fines erased at employment + 6 months: confirm in
  writing, naming the register. Blocks switch-on. Meanwhile: switch stays off.
- **D-3 (counsel, Surbhi)** - a hold for an open dispute or claim. Blocks switch-on. Meanwhile:
  switch stays off.

**Should know:**

- **QS-1 (Surbhi)** - an Employee Transfer with a new employee id marks the old record Left.
  Is that the end of employment for this rule? If not, the marks of a person still working in
  the group are erased 6 months after the transfer. My reading: it is like D-2 (a new
  record), so erase is probably right, but it is your call. Default meanwhile: switch off,
  so nothing happens.
- **M-1 and M-2** - fix, or accept in writing with a name and a date.

**Nice to know:** Log Settings on dev and production (Email Queue, Error Log days); whether
telemetry/Sentry is on there.

## 6 · Repo checks run

| Command | Result |
|---|---|
| `run-tests --module alvoraa_portal.tests.test_grooming_erase_066` on **test066r_sec** | **18 tests, OK** (76.8 s; the boundary test ran, it did not skip) |
| My break script on test066r_sec (sections 2.2-2.4) and the after-commit demo (m-1) | Outputs as quoted above. Every row I made is deleted again |
| `python scripts/check_app_integrity.py` | 823 checks, OK |
| `python scripts/check_no_demo_passwords.py` | OK, 41 files |
| `python scripts/check_api_paths.py` | OK |
| `ignore_permissions` count, non-test, origin/dev vs branch | 425 = 425 |

Programme note, not this slice: of the four CI gates in my remit, the `ignore_permissions`
counter does not exist in CI. I counted by hand.

Not run: the full alvoraa_portal suite; anything on dev or production.

## 7 · Residual risk

| # | Risk | Kind | Owner / accepted | Date |
|---|---|---|---|---|
| R-1 | Copies in backups, binary logs and delivered email outlive the erase | Intentional trade-off | Counsel (Q-3, Q-4) - **not yet accepted** | open |
| R-2 | No erase receipt naming people (D-4) | Intentional trade-off | Surbhi (D-4 approved per 05 notes) | 25 Oct 2026 |
| R-3 | Administrator can erase outside the rule through a Server Script | Acceptable simplification (same power as server shell) | **Unnamed - Surbhi to accept** | open |
| R-4 | M-1 wrong erase invisible | Temporary debt (removed by a count-only line) | **Unnamed** | before switch-on |
| R-5 | M-2 mistyped dry run | Temporary debt (removed by a separate function) | **Unnamed** | before switch-on |
| R-6 | Fines register erased before its legal period, if Q-1 says so | **Dangerous debt if switched on before Q-1 - escalate now** | Counsel / Surbhi | before switch-on |

## 8 · What I could not verify

- Log Settings, telemetry and Sentry on dev and production: needs read access to those sites'
  settings.
- The HTTP layer itself for REST DELETE (I called the same Python function; no web server on my
  site).
- Whether any dev tenant has a due leaver with marks.
- The law on the register of fines. I am not a lawyer; that is Q-1.

## 9 · Subtract pass

Removed from my draft: a recommendation to move the self-check into its own scheduled job
(m-3 is enough as a note; it would add a second hook for a gap the switch-on review can
decide); a request for a new CI gate for the `ignore_permissions` counter (programme work,
not this slice, kept as one line); a full table of every Frappe log type (kept only the ones
that can hold grooming data).

My throwaway site test066r_sec (database and user `_066sec`) is still in container
hrlocal-066r. It can be dropped any time; nobody else uses it.
