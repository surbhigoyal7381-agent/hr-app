# ALV-266 · Implementation notes

Built 31 Oct 2026, reworked the same day for Surbhi's rule (04). Branch
`slice/alv-266-employee-write-fields`, worktree `.claude/worktrees/alv-266`, rebased on
`origin/dev` 9b99a421. **Local only. Not pushed. Not merged into local `dev`. Dev and
production untouched. No SSH.**

---

## Round 3: security fixes Surbhi approved (06-security.md), 1 Nov 2026

### Bad news first

- **D6 cannot be built with the 075 level mechanism.** Frappe decides who may read a
  field level from the login's **roles only**, never from whose record it is
  (`Document.get_permlevel_access` and `Meta.get_masked_fields` both read roles and
  cache per login, not per record). So a level cannot say "HR, or the person
  themselves". Nothing was built for D6. The choices are below; Surbhi decides.
- **Not fixed here, by instruction:** ALV-272 (refusal log lines are never written -
  the security logger drops WARNING) and ALV-273 (anyone who can read a record can
  attach a file to it). Follow-ups.
- `test_alv266_only_hr_renames_an_employee` fails without the fix on its first line
  (the hook is not registered), before it reaches the rename itself. The rename
  behaviour is proven by the same test once the hook is there.

### What changed

| Finding | Fix | Test (fails without the fix?) |
|---|---|---|
| Blocker 1: the other person's values in the Error Log | The comparison is in its own function, `changed_fieldnames`, which returns names only. When the check refuses, no frame left on the stack holds an old value | `test_alv266_a_refused_bulk_edit_logs_no_value_of_the_report` - a real bulk edit, then no Error Log row holds the report's real mobile |
| Blocker 2: staff could rename their own Employee ID | `refuse_rename_unless_hr` on Employee `before_rename`: only HR User, HR Manager, System Manager and Administrator. Merging goes the same way | `test_alv266_only_hr_renames_an_employee`: own rename, a manager renaming a report, and a merge are refused; HR Manager renames. Failed without the fix |
| Major 3: ESS could share (and so assign) a report's record to anyone | `apply()` takes Share off Employee Self Service on Employee (level 0). Assigning a record to someone who cannot read it needs Share, so it is refused too | `test_alv266_staff_cannot_share_or_assign_a_report_open`: share refused, assignment refused, the other person still cannot read it. Failed without the fix |

### D6: the choices (nothing built)

Goal: passport, health details, family background and blood group readable by HR and
the person only, not by their manager, and not in a manager's CSV export.

| Option | What it does | Cost | What is lost |
|---|---|---|---|
| A. Put the fields at a new level that only HR roles read | Managers can no longer read or export them anywhere | ~10 lines in `apply()`/`lock_fields()` | **The person can no longer see or edit their own passport, health, family or blood group** in Desk or the /hrms phone app (its Profile shows blood group). Contradicts the self-edit list |
| B. Blank those fields when the reader is neither HR nor the person, in the Employee document class (`override_doctype_class`) | Covers the form, `frappe.client.get`, the /hrms profile, every single-record read | ~25 lines, plus a class override on Employee that hrms plans to restore itself ("step B" in `hrms/hooks.py`) - a clash risk | **Does not cover list and report reads** (`reportview.get` with those columns): Frappe applies field reads there by role only. Needs C as well, and a list-column check |
| C. Take the Export right off Employee Self Service on Employee | Stops the CSV export for every ESS holder | 1 line in `apply()`, same as Share | Staff lose Employee export; nobody uses it for their own one record |

Recommended: **C now** (cheap, closes the export), and decide between A and B. A is
the only one that closes every read path, at the cost of the person's own view.

### Statements on an Employee save (budget check, `test266`, warm)

| Save | Before (`origin/dev` code) | After |
|---|---|---|
| ESS person changes own mobile | 680 | 641 (same work; the difference is noise) |
| Manager with ESS changes a report's mobile | 424, and it saved | 40, refused before any write |

The new check costs the own save one lookup of the record's login. The big number is
the existing save path (Frappe, ERPNext, Frappe HR and our hooks), not this change.

### Error Log check (blocker 1)

After a refused bulk edit, the newest "Bulk action failed" row on `test266` holds
`data = {'cell_number': '9777777266'}` (the caller's own typed value), `doc = Employee
(HR-EMP-00193)` and `changed = {'cell_number'}` - names only. The report's real mobile
is not in it.

### Test runs, round 3 (own container `hrlocal-266`, one module at a time)

Copied site `test266`:

| Module | Result |
|---|---|
| `test_employee_write_fields_alv266` | 19, OK |
| `test_employee_field_rights_alv215` | 20, OK |
| `test_own_record_permission_alv249` | 26 + 1, OK |
| `test_request_guard_alv249` | 5 + 3, OK |
| `test_unseated_071` | 12, **1 failure: `test_statement_count_is_a_fixed_handful`, 43 statements against a budget of 40.** This is the same failure dev CI shows on `origin/dev` (being fixed on another branch). The counted calls run as an HR user, for which the new check returns at once with no query. I did not re-run it on `origin/dev` code to prove that |
| `test_expense_birthdays_076` | 35, **2 errors, the same two as on `origin/dev` code** (round 1 notes) |
| `test_expense_and_scoping` | 8, OK |
| `test_inbox_counts_034` | 17 + 2, OK |
| `test_directory_contact_045` | 17, OK |
| `test_permission_health_048` | 16, OK |
| `test_personas_012` | 17, OK |
| `test_portal_security_010` | 45 + 5, OK |
| `test_positions_064` | 17, OK (21 minutes) |

Fresh site `fresh266` (made with `bench new-site` in my container, apps erpnext, hrms,
alvoraa_goals, alvoraa_portal): 

| Module | Result |
|---|---|
| `test_employee_write_fields_alv266` | 19, OK |
| `test_employee_field_rights_alv215` | 20, OK |
| `test_own_record_permission_alv249` | 26 + 1, OK |
| `test_request_guard_alv249` | 5 + 3, OK |
| `test_expense_and_scoping` | 8, OK |
| `test_expense_birthdays_076` | 35, **1 error: `..._but_hr_can` (PermissionError)** - the same failure dev CI shows on `origin/dev`, being fixed on another branch. The second error seen on the copied site does not happen on a fresh site (it came from the copied data) |
| `test_unseated_071` | 12, **1 failure: 43 statements against 40** - the same as dev CI |

So on a fresh site this branch shows exactly the two failures `origin/dev` already
has, and no new one.

Scripts: `check_app_integrity.py` 873 checks OK (shadowing part skipped);
`check_scope_traps.py` OK.

### Follow-ups (not in this branch)

- **ALV-272** - the security logger drops WARNING, so no refusal anywhere is recorded.
- **ALV-273** - `frappe.client.attach_file` needs only read: a manager can attach a file
  to a report's record.

## Round 2: review fixes (06-review.md, 06-security.md), 31 Oct 2026

### Bad news first

- **The security review found two blockers and three majors. I fixed one blocker (my
  own code put data in a log). The rest are open and need Surbhi's decision**:
  - *Blocker 2:* a person with Employee Self Service can **rename their own Employee
    ID** (Frappe's rename, `allow_rename` is on). **Fixed in round 3.**
  - *Major 3:* ESS holds the **Share** right on Employee, so a manager can share a
    report's whole record (passport, health) with anyone, or "everyone"; assigning does
    the same. Not new. **Fixed in round 3.**
  - *Major 4:* refusal log lines are **never written** (WARNING level is dropped).
    Affects every `refuse()` in the product, not only this one.
  - *Major 5:* anyone who can read a record can attach a file to it. Standard Frappe.
- **Review M1 was real and worse than one case:** a person's own save was refused
  ("You cannot change your own job, pay or bank details") whenever code rewrote a
  locked read-only field during the save - an expired document, or a full name that
  differs from first + middle + last. Proven on `test266` before the fix: both tests
  failed with that message. Fixed.

### What changed

| Finding | Fix |
|---|---|
| Review M1 | `refuse_own_locked_change` skips read-only fields and tables. They stay at level 2, so Frappe still puts back an API write by staff. No job, pay or bank field is read-only or a table |
| Security blocker 1 (other person's values in the Error Log) | The hook deletes its comparison before refusing, so a logged traceback holds field names only. Test: a refused bulk edit, then no Error Log row contains the report's real mobile |
| Review m1 | Wording in 04/05 corrected: the form opens editable, Save is refused. Test renamed. No form script added |
| Review m2 | Rollback step added below |
| Review m4 | Tests added: new custom field is level 2; HR User and System Manager change a report; the M1 cases (expired document, rebuilt full name, a work-history row) |

### Rollback

Reverting the code is not enough: `lock_fields()` leaves about 30 Employee fields at
level 2 (stricter, so nothing is exposed). To undo fully, on each site, as
Administrator: delete the Employee `permlevel` Property Setters for every field that is
**not** in the ALV-215 `LEVEL_2` or `LEVEL_1` lists or named by a pay rule set; then
`bench --site <site> clear-cache`. Needs Surbhi's approval like any data change.

---

## Bad news first (round 1)

- **Staff without Employee Self Service still cannot edit their own record** (no write
  for the plain Employee role, as today). Surbhi's rule says a manager edits their own
  record like anyone else; for a login without ESS that needs a role change I did not
  make (04, D-6). There is a test that pins today's behaviour so the choice is visible.
- **Staff lose Desk edits of their own HR-owned fields** (contract and notice dates,
  company email, exit interview, the birthday-hide tick in Desk). The portal's own
  birthday-hide and document-upload still work - they write directly.
- **Every future Employee field is HR-only unless added to `SELF_EDITABLE`.**
- **A manager's Desk form for a report still opens editable**; Save is refused with the "Ask HR" message. Nothing is saved (review m1).
- **My first try at the hook had a bug the tests caught:** Frappe's diff returns
  nothing at all when nothing changed, and my code assumed it returned an empty result.
  Opening a report's form as a manager would have crashed. Fixed, and the test that
  found it (`..._manager_opens_a_report_read_only...`) stays.
- **The first version of this slice (Option 2) is replaced**, not added to. Personal
  fields are back at level 0. The ALV-215 test I had reversed is back as it was.

## Who can change what

| Who | Own record: self-edit fields | Own record: everything else | Someone else's record |
|---|---|---|---|
| Staff / manager with Employee Self Service | Yes | Quietly put back | Refused: "Only HR can change another person's employee record. Ask HR to make this change." |
| Staff / manager without it | No (as today, D-6) | No | Refused (Frappe's "no permission") |
| HR User / HR Manager / System Manager | Yes | Refused on own job/pay/dates (ALV-215 rule) | Yes, everything (bank and pay: HR Manager only, as before) |

Self-edit list (`SELF_EDITABLE`), for Surbhi to confirm: mobile, personal email,
preferred email choice, unsubscribe tick, current and permanent address (and rented /
owned), emergency contact name, phone and relation, passport number and dates and
place, marital status, blood group, health details, family background, bio, photo,
salutation, education, past work history. Reasons, one line each, in 04 §2.

## What was built

| File | What | Rung |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/employee_field_rights.py` | `SELF_EDITABLE` and `MANAGER_EDITABLE` (empty). `lock_fields()` puts every value field not on the list at level 2. `lock_new_custom_field()` does the same for a field created later. New `employee_has_permission` hook. `refuse_own_locked_change` back to its ALV-215 form | Configuration through the existing 075 function, plus one hook |
| `alvoraa_portal/alvoraa_portal/hooks.py` | One line at the end of `has_permission`: `"Employee": ...employee_has_permission` | - |
| `tests/test_employee_write_fields_alv266.py` | 11 tests, below | - |
| `tests/test_employee_field_rights_alv215.py` | No net change (the reversal from the first version is undone) | - |

**How the hook works.** Frappe asks it on every permission check for an Employee.
It says yes to everything except "write" by someone who is not HR on a record that is
not their own. For that, it compares the document with the saved copy:
- changes outside `MANAGER_EDITABLE` → refused with the message, and a line in the
  security log (who, which record, rule ALV-266; never a value) - **but the security
  review found that log line is never written** (Frappe keeps that logger at ERROR,
  ours writes WARNING). Not new; affects every `refuse()` in the product;
- no changes (a plain "may this login write it?" check) → no, unless the list grants a
  field. The Desk form does not ask that way, so it still opens editable; Save is refused.

It runs **before** Frappe quietly resets locked fields, so a change to a report's
`reports_to` or `status` is refused, not silently undone. Every allowed case returns
`True`; Frappe v16 reads anything else as "no".

**Why a code rule and not a setting.** See 04 §3. In short: no role permission can say
"not someone else's record", and ticking "Hide Descendants" on the ALV-249 own-record
row would cut managers off from *reading* their reports too - untested, and likely to
break team goals, KPIs and the manager screens.

## Requirements and their tests

| Requirement | Test | Without the change (`origin/dev` code) |
|---|---|---|
| Manager **with** ESS: report's mobile, passport, address, contract end, notice days, reports_to, status, photo, department - refused on Desk save, REST PUT, `set_value`, `save`; values unchanged | `test_alv266_manager_with_ess_is_refused_on_a_report_on_every_path` (36 cases) | Failed, 32 of 32 cases (department added after) |
| Manager **without** ESS: same | `test_alv266_manager_without_ess_is_refused_on_a_report_on_every_path` | Passed (no write role) - pin |
| The refusal says what to do | `test_alv266_refusal_says_what_to_do` | Failed |
| Manager may not write a report (permission check), still reads the mobile | `test_alv266_manager_may_not_write_a_report_but_still_reads_it` (renamed after review m1) | Failed |
| A manager edits own mobile and address; own department, notice days, reports_to put back | `test_alv266_a_manager_edits_own_personal_details_but_not_own_hr_fields` | Added after the "without" run; own HR fields were level 0 then, so it would fail |
| Without ESS, a manager cannot edit even their own record (today's behaviour, D-6) | `test_alv266_without_ess_a_manager_cannot_edit_even_own_record_today` | Passes - pin |
| Person edits own mobile and passport | `test_alv266_person_edits_own_mobile_and_passport` | Passed - pin |
| Person's own contract end and notice days put back | `test_alv266_person_cannot_change_own_contract_end_or_notice` | Failed |
| Levels follow the list | `test_alv266_levels_follow_the_self_editable_list` | Failed |
| HR changes anything on a report | `test_alv266_hr_changes_anything_on_a_report` | Passed - pin |
| One granted field, and only that one | `test_alv266_a_granted_field_and_only_that_field` | Failed |
| *Round 2:* own save with an expired document (review M1) | `test_alv266_own_save_with_an_expired_document_still_saves` | Failed with "You cannot change your own job, pay or bank details" before the fix |
| *Round 2:* own save when the full name is rebuilt (review M1) | `test_alv266_own_save_when_the_full_name_is_rebuilt_still_saves` | Failed, same message, before the fix |
| *Round 2:* own save with a work-history row | `test_alv266_own_save_with_a_work_history_row_still_saves` | Passed before the fix too - pin |
| *Round 2:* a new custom field is HR-only (review m4) | `test_alv266_a_new_custom_field_is_hr_only` | - |
| *Round 2:* HR User changes a report; our rule lets System Manager through (review m4) | `test_alv266_hr_user_and_system_manager_change_a_report` | - |
| *Round 2:* a refused bulk edit logs no value of the report (security blocker 1) | `test_alv266_a_refused_bulk_edit_logs_no_value_of_the_report` | - |

**System Manager note:** on `test266` the System Manager role has **no** Employee
rights at all (the site's own permission rows leave it out), so its test checks our
rule, not a full save. Whether System Manager may edit Employees is each tenant's own
setting.

"Without the change": `employee_field_rights.py` and `hooks.py` put back to `origin/dev`,
every Employee level Property Setter on `test266` deleted (the old `apply()` re-made the
ALV-215 ones), cache cleared. Result: 9 tests, 35 failures and 2 errors.

## Non-functional, against the code as written

| Dimension | Before → after | Note |
|---|---|---|
| Performance | neutral | Non-HR write check: one lookup of the record's login; one read of the saved record only for someone else's record. Reads and HR: nothing extra |
| Security | improves | Manager writes on reports refused on every save path, before any quiet reset |
| Reliability | neutral | `ignore_permissions`, `db_set`, `db_update` and `db.set_value` never reach the hook, so ERPNext's Employee hooks, the ALV-249 sync, birthday hide and document upload are unaffected (their tests pass) |
| Scalability | neutral | Nothing grows with headcount |
| Maintainability | improves slightly | One list says what staff may edit |
| Data integrity | improves | Employment data changed by HR only, with Version history |
| Compliance / privacy | improves | Refusals logged with no values; no new data shown anywhere |

## Test runs (own container `hrlocal-266`, site `test266`, one module at a time)

Code at the final commit, ALV-249 included (it is on `origin/dev` now):

| Module | Result |
|---|---|
| `test_employee_write_fields_alv266` (new) | 11, OK |
| `test_employee_field_rights_alv215` | 20, OK |
| `test_own_record_permission_alv249` | 26 + 1, OK |
| `test_request_guard_alv249` | 5 + 3, OK |
| `test_positions_064` (asks "may this login write Employee?") | 17, OK (20 minutes - it makes 200 people) |
| `test_personas_012` | 17, OK |
| `test_permission_health_048` | 16, OK |
| `test_portal_security_010` | 45 + 5, OK |
| `test_expense_birthdays_076` | 35, **2 errors - the same 2 on `origin/dev` code** on this site (a department that belongs to another company in the copied data, and a share removal). Not caused by this change |
| `hrms ... test_employee_documents` | **Could not run**: the hrms test start-up stops on an overlapping fiscal year in the copied data (the known hrms bootstrap issue). Document upload writes the row directly and never reaches the new hook |

Scripts: `check_app_integrity.py` - 872 checks, OK (doctype-shadowing part skipped, no
bench path). `check_scope_traps.py` - OK.

Not run: the whole `alvoraa_portal` suite; `alvoraa_goals`.

## What else moved

Rebased onto `origin/dev` 9b99a421: 8 ALV-249 commits came in (5452084c .. 9b99a421):
`hooks.py`, `own_record_permission.py`, `request_guard.py`, their tests,
`test_inbox_counts_034.py`, `test_portal_security_010.py`, their slice documents. No
conflict. My `hooks.py` line is in `has_permission`, which ALV-249 did not touch; their
lines (`on_login`, `before_request`, two `doc_events`) are intact.

DTC counts from the coordinator (read-only): 429 enabled logins hold Employee Self
Service, 4 also HR, 7 are managers with reports.

## Environment

Container `hrlocal-266` (image `dev-3830ed3`, apps mounted from this worktree), redis
`hrlocal-266-redis`, volume `hrlocal-266-sites`, site `test266`, database `_266fields`
(read-only dump of `test249`'s database). Nothing else written. Stop:
`docker stop hrlocal-266 hrlocal-266-redis`. Remove: `docker rm -f hrlocal-266
hrlocal-266-redis; docker volume rm hrlocal-266-sites`, then drop database and user
`_266fields`.

## Gaps and shortcuts

- **Quiet put-back on a person's own record** - intentional trade-off, Surbhi's D-3.
- **`MANAGER_EDITABLE` only works for self-edit fields** - acceptable simplification; an
  HR-owned field would also need a permission row. Said in the code comment.
- **Staff without ESS cannot edit their own details** - open decision D-6.
- **Data Import by non-HR** is not possible today (no import right), so the hook was not
  tested through it.
- **Not run:** the whole `alvoraa_portal` suite, and `alvoraa_goals` (team goals read
  Employee; the hook changes no read).

## Decisions for Surbhi

1. Confirm the self-edit list (04 §2).
2. Confirm that any future Employee field is HR-only unless added to the list.
3. `MANAGER_EDITABLE` stays empty? Recommended yes.
4. **D-6:** staff without Employee Self Service - give the Employee role write on their
   own details (one line, plus a fix to the Positions "Set manager" check), or keep
   using ESS per tenant as today? Recommended: keep using ESS.
5. Security blocker 2 and major 3: approved by Surbhi and fixed in round 3.
6. **D6:** choose A or B for passport, health, family and blood group, and say yes or
   no to C (no Export for staff). See round 3.
7. ALV-272 (log level) and ALV-273 (attach a file) are follow-ups.
