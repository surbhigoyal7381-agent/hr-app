# ALV-266 · Implementation notes

Built 31 Oct 2026, reworked the same day for Surbhi's rule (04). Branch
`slice/alv-266-employee-write-fields`, worktree `.claude/worktrees/alv-266`, rebased on
`origin/dev` 9b99a421. **Local only. Not pushed. Not merged into local `dev`. Dev and
production untouched. No SSH.**

---

## Bad news first

- **Staff without Employee Self Service still cannot edit their own record** (no write
  for the plain Employee role, as today). Surbhi's rule says a manager edits their own
  record like anyone else; for a login without ESS that needs a role change I did not
  make (04, D-6). There is a test that pins today's behaviour so the choice is visible.
- **Staff lose Desk edits of their own HR-owned fields** (contract and notice dates,
  company email, exit interview, the birthday-hide tick in Desk). The portal's own
  birthday-hide and document-upload still work - they write directly.
- **Every future Employee field is HR-only unless added to `SELF_EDITABLE`.**
- **A manager opens a report's Employee form read-only.**
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
  security log (who, which record, rule ALV-266; never a value);
- no changes (the form asking whether to open editable) → read-only, unless the list
  grants a field.

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
| Manager opens a report read-only, still reads the mobile | `test_alv266_manager_opens_a_report_read_only_but_still_reads_it` | Failed |
| A manager edits own mobile and address; own department, notice days, reports_to put back | `test_alv266_a_manager_edits_own_personal_details_but_not_own_hr_fields` | Added after the "without" run; own HR fields were level 0 then, so it would fail |
| Without ESS, a manager cannot edit even their own record (today's behaviour, D-6) | `test_alv266_without_ess_a_manager_cannot_edit_even_own_record_today` | Passes - pin |
| Person edits own mobile and passport | `test_alv266_person_edits_own_mobile_and_passport` | Passed - pin |
| Person's own contract end and notice days put back | `test_alv266_person_cannot_change_own_contract_end_or_notice` | Failed |
| Levels follow the list | `test_alv266_levels_follow_the_self_editable_list` | Failed |
| HR changes anything on a report | `test_alv266_hr_changes_anything_on_a_report` | Passed - pin |
| One granted field, and only that one | `test_alv266_a_granted_field_and_only_that_field` | Failed |

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
