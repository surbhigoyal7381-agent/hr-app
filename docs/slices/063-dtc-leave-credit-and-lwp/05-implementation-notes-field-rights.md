---
slice: 063-dtc-leave-credit-and-lwp (SEC-17), ALV-215
artifact: 05-implementation-notes-field-rights
author: hrms-fullstack-engineer
date: 2026-10-25
status: BUILT LOCALLY - steps A and B. Step C held (D1). Nothing pushed, no server touched, no production or dev data read or changed.
branch: slice/063-field-rights in .claude/worktrees/063-field-rights (from origin/dev 6aaf9ffd)
tested on: own containers hrlocal-063fr + hrlocal-063fr-redis, site testfr (fresh install, CI-shaped). No tenant data.
inputs: 01g-employee-field-rights.md, 04c-field-rights-strategy.md (in worktree 067-pay-slip-marks), 01c revision 4/4b SEC-17; Surbhi's decisions D1-D5, Q1-Q6, R4 (25 Oct 2026, via the lead)
---

# Who may change which Employee field - what was built (ALV-215)

## The answer first

**Steps A and B are built and tested on my own local site. Step C (second person for bank
changes) is not built - it waits for the product manager to specify opening Employee
Promotion to every plan (D1).**

| What | Where | Rung |
|---|---|---|
| Lock 22 job/pay/approver/identity fields at level 2, 13 bank/ID/salary fields at level 1, plus every Employee field a pay rule set names | `employee_field_rights.apply()` on every migrate and every install | 2-3 applied by code (Property Setters, Custom DocPerm rows) |
| Level-2 rows: every Employee reader reads; HR User, HR Manager, System Manager write (where they already write at level 0) | same | same |
| Level 1: HR Manager only. Every other role's level-1 row is removed (D2: PPJ's Payroll Users lose bank access; D3: System Manager too) | same | same |
| A rule set that names a field locks it when saved | `AlvoraaPayrollRuleSet.on_update` -> `lock_fields()` | 4 (one method) |
| R4: nobody, HR included, changes a locked field on their own record | Employee `validate` -> `refuse_own_locked_change` | 4 |
| Loud import: an Employee import with a column the importer cannot change is refused with a message | Data Import `validate` -> `refuse_import_of_locked_columns` | 4 |
| DTC's three fields the rule set does not name (`dtc_pay_type`, `dtc_employee_category`, `dtc_agency`) | patch `dtc_pay_fields_level_2`, a no-op on any site without them | 2-3 by patch |
| Step B: the field picker leak | `override_whitelisted_methods` -> our `get_employee_field_property`, which checks the level and calls upstream unchanged (D4) | 4 |

Cheaper rungs rejected, as in 04c section 3: a fixture would overwrite tenants' own
permission rows; a patch alone never runs on a new install; Customize Form by hand drifts.
No setting can say "not on your own record", and no setting makes Frappe say *why* it
dropped an imported value.

## Differences from 04c, and why

| # | 04c said | Built | Why |
|---|---|---|---|
| 1 | "Nothing removed" from level 1 | Every level-1 row that is not HR Manager is **removed** | Surbhi's D2 and D3 ("HR Manager only"). **This includes PPJ's System Manager level-1 row**, not only Payroll User. A CXO who holds System Manager but not HR Manager no longer sees bank, PAN, ESI, PF or CTC on the Employee form. Say if System Manager should keep it - one line |
| 2 | DTC-only fields by three hand-made Property Setters on the day | A **patch** that does the same, no-op elsewhere | The lead's instruction for this build. It puts three DTC field names into product code, which 04c had avoided. It still needs DTC to migrate, i.e. a release |
| 3 | `on_update` on the rule set calls `apply()` | It calls `lock_fields()` only | `add_permission` saves its row with the caller's own permissions, so an HR Manager saving a rule set would be refused if rows were ever missing. Rows are migrate's job; the rule-set save only locks fields |
| 4 | Step B in the hrms fork (B1) | Override in our app (B2) | Surbhi's D4. It wraps upstream (check, then call it), so it is not a copy that can drift |
| 5 | Data Import "silently ignored" was an accepted trade-off | Made loud | The lead's instruction. Refused at the Data Import save, before anything is imported |
| 6 | Survey: System Manager gets level-2 write | Same, but only where System Manager already writes Employee at level 0 | On a fresh site System Manager has no Employee row at all, so nothing is added for it |

## Acceptance - rule by rule

| Rule | How it is met | Test (all in `tests/test_employee_field_rights_alv215.py`) |
|---|---|---|
| R1 employee cannot change job, pay, approver, pay-rule fields | Level 2; Frappe puts the old value back before any hook runs | `test_alv215_employee_cannot_change_own_job_pay_or_approver_fields` (also: the old manager keeps their User Permission - manager_scope sees no change) |
| R1 self-service still works | Phone etc. stay at level 0 | `test_alv215_employee_still_changes_own_phone` |
| HR User edits a colleague, history kept | Level-2 write row; Version row | `test_alv215_hr_user_changes_a_colleague_and_history_says_so` |
| R2 bank/ID/salary HR Manager only, and hidden from HR User | Level 1 | `test_alv215_only_hr_manager_changes_or_sees_bank_details` |
| R4 nobody edits their own locked fields | Employee validate | `test_alv215_hr_cannot_change_own_locked_fields`, `test_alv215_hr_cannot_promote_themselves`, `test_alv215_another_hr_person_changes_it` |
| Migrate sets levels and rows; safe twice | `apply()` | `test_alv215_apply_sets_levels_and_rows_and_runs_twice_for_nothing` |
| Never lowers a field; D2 removes other level-1 rows | `apply()` | `test_alv215_apply_never_lowers_a_field_and_drops_other_level_1_rows` |
| A site with no custom rows loses nobody | `add_permission` copies standard rows first | `test_alv215_apply_on_a_site_with_no_custom_rows_keeps_every_role` |
| New install starts locked | `after_install` | Seen directly: the fresh `testfr` install ended with the level-1 and level-2 rows in place before any test ran |
| Rule-set field locked on save, by an HR Manager | `on_update` | `test_alv215_a_field_a_rule_set_names_is_locked_on_save` |
| DTC patch locks its three, no-op elsewhere | patch | `test_alv215_dtc_patch_locks_its_three_fields_and_is_a_no_op_elsewhere` |
| Step B no bank number through the picker | override | `test_alv215_field_picker_does_not_leak_bank_number` (also pins the hook) |
| Loud import | Data Import validate | `test_alv215_import_with_a_locked_column_is_refused_loudly` (also pins the hook) |

Not covered by an automated test: an employee changing their own **company** over the API.
It is refused outright by the Company User Permission ERPNext gives every employee login,
before our rules matter. Noted in the test.

### Guards broken on purpose - each made its test fail

| Break | Test | Result |
|---|---|---|
| R4 check never refuses | own locked fields; promote themselves | both FAILED |
| Step B check skipped | field picker | FAILED |
| Import check never refuses | import | FAILED |
| D2 removal skipped | never lowers / drops level 1 | FAILED |
| "Never lower" removed | same | FAILED |
| Level-2 write rows not granted | site with no custom rows | FAILED |
| Rule-set `on_update` does nothing | rule set | FAILED |
| `lock_fields` locks nothing (Property Setters deleted first) | R1 employee test | FAILED |
| DTC patch does nothing | DTC patch | FAILED (`0 != 2`) |

Each break was made in my worktree only and restored from my commit afterwards; the site
was put back by running the real `apply()`.

## The risks the lead named

| Risk | What happens now |
|---|---|
| HR User imports bank/PAN/ESI/PF columns | **Refused, with a message** naming the columns: "Remove them from the file, or ask an HR Manager to run this import." Data Import is System Manager only as shipped, so this bites a System Manager without HR Manager, or a tenant that granted Data Import |
| One-person HR team cannot change its own locked fields | **Supported path:** log in as Administrator (who has no Employee record, so R4 never applies), or a second HR person. A System Manager who is also an employee is bound by R4 like everyone. Intentional trade-off (R4) |
| Portal self-service edits | No portal screen writes Employee. A REST write by an employee to a locked field is put back silently (R1, as 01g). Phone, email, address, emergency contact still save |
| Positions chart and manager_scope | manager_scope: test passes (12); a self-edit of `reports_to` is put back before `on_update`, so the real manager keeps access (asserted in the R1 test). Positions: reads Employee only; its tests run below |
| Hooks that write these fields | Position cover writes `leave_approver`/`expense_approver` with `frappe.db.set_value` - skips levels and R4, no Version row (existing debt, 01g). `employee_documents` writes its own child rows with `db_insert`. Employee Promotion's submit saves the Employee as the submitter: works for HR on someone else, refused for yourself (tested). **New consequence:** an HR User submitting a Promotion with a revised CTC has the CTC silently put back (CTC is level 1) |

## NFR - before vs after, against the code written

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | Employee save: no query unless a level 1/2 field changed, then one `get_value`. New records: returns at once. Migrate: two reads, writes only what is missing. Data Import save: the file is parsed once more |
| Security | improves | Self-edit of job, pay, approver, identity and rule-set fields closed on desk, REST and import; HR cannot edit their own (closes the own-company path to another company); picker leak closed |
| Reliability | neutral | If level-2 rows were missing, HR edits would be put back silently; `apply()` heals that every migrate and a test proves it on a site with no custom rows |
| Scalability | neutral | Nothing grows with headcount |
| Maintainability | improves | One file, two field lists, one rule set read. R4 reads levels, no second list |
| Data integrity | improves | Pay inputs change only through HR, with Version history. No value is migrated |
| Compliance / privacy | improves | Bank, PAN, ESI, PF, CTC leave HR User's (and System Manager's) view. Refusal logs carry user, doctype and document name only |

Permission enforcement points: Frappe `validate_higher_perm_levels` (every save, insert,
import); `refuse_own_locked_change` (Employee validate); `refuse_import_of_locked_columns`
(Data Import validate); our `get_employee_field_property`. Sensitive fields touched: the 13
level-1 fields - only who may read/write them, never their values. Nothing personal is logged.

## Files

| File | Change |
|---|---|
| NEW `alvoraa_portal/alvoraa_portal/employee_field_rights.py` | `apply`, `lock_fields`, `rule_set_fields`, `refuse_own_locked_change`, `refuse_import_of_locked_columns`, `get_employee_field_property` |
| `alvoraa_portal/alvoraa_portal/hooks.py` | Employee `validate`; Data Import `validate`; one line at the end of `after_migrate` and `after_install`; `override_whitelisted_methods` (new block) |
| `alvoraa_payroll_rule_set.py` | new `on_update` (calls `lock_fields`) |
| NEW `patches/v1_0/dtc_pay_fields_level_2.py` + one line at the end of `patches.txt` | DTC-only fields |
| NEW `tests/test_employee_field_rights_alv215.py` | 14 tests |

## What else moved while I worked

origin/dev moved from 6aaf9ffd by 12 commits of slice 069 (wall-chart print: `portal.js`,
`panels.css`, `positions.html`, scripts, docs). None touch my files. Rebased on it before
handing off (see commands).

## Commands run and what they said

All on my own site `testfr` in container `hrlocal-063fr` (image dev-3830ed3, Frappe 16.33.1,
worktree apps mounted). Fresh install as CI does it: erpnext, hrms, alvoraa_portal, alvoraa_goals.

| Run | Result |
|---|---|
| After the install, before any test: Employee Custom DocPerm rows | Level 2 read for Employee and Employee Self Service; level 2 read+write for HR User and HR Manager; level 1 read+write for HR Manager only. So a new tenant starts locked |
| `test_employee_field_rights_alv215` | 14 tests OK (after the subtract pass, again OK) |
| Guards broken on purpose | 10 breaks, 10 failing tests (table above) |
| Affected modules, one at a time | `test_manager_scope` 12 OK; `test_positions_064` 17 OK (1,459 s - it builds ~400 employees); `test_payroll_flags` 9 OK; `test_leave_063_rules` 38 OK; `test_permission_health_048` 16 OK; `test_personas_012` 17 OK; hrms `alvoraa_org_structure.test_org_structure` 33 OK; `test_cover_policy` 25 OK |
| `scripts/check_app_integrity.py` | OK - 806 checks |
| **Full suite, once, after rebasing on origin/dev af0b7cdf** | `alvoraa_goals`: 18 OK (2 skipped). `alvoraa_portal`: three batches - 30 OK; 962 OK (19 skipped); 2,168 OK (40 skipped). No failure, no error |

Not run: the hrms per-doctype CI job (`hrms_test_site`); `bench migrate` (on the approval list
- the after_install path was observed instead, and `apply()` is the same function).

## Release notes for later (not done - each needs Surbhi's word)

1. D5: read-only query on DTC, Grace and PPJ production first (fields above level 0; Employee
   Custom DocPerm rows; HR Manager and Payroll User counts). **Stop if a site already uses
   level 1 for anything other than the 13, or level 2 at all** - `apply()` would remove other
   roles' level-1 rows and add level-2 readers.
2. Push to dev, migrate runs `apply()` and the DTC patch (no-op on dev tenants without the
   fields). Check one dev tenant by the same query.
3. Rollback: revert the commits first (or the next migrate re-applies), then delete Property
   Setters on Employee with `property = "permlevel"` created after the release time (PPJ's own
   of 14 Sep stay), Employee Custom DocPerm rows at level 2, the HR Manager level-1 row where
   created after the release, and re-add PPJ's removed Payroll User / System Manager level-1 rows
   from the D5 query's output. Clear the cache (on the approval list).

## Known gaps

| Item | Label |
|---|---|
| Step C (second person for bank changes) | Temporary debt - waits for D1 |
| HR Manager can change a colleague's bank details alone, with Version history | Temporary debt - step C |
| Position cover writes approvers with no Version row and outside R4 | Existing debt, separate ticket (01g) |
| An HR User could set a colleague's `user_id` to their own login. Afterwards R4 treats that record as theirs and refuses their edits to it, but the `user_id` change itself is one person's, recorded only in Version history | Acceptable simplification (as 04c) |
| A tenant's custom HR role (not HR User / HR Manager / System Manager) that writes Employee gets level-2 **read** only | Intentional - fail closed. Say so to any tenant with such a role |
| HR User Promotion with revised CTC: CTC silently put back | Intentional trade-off (D3); HR Manager submits those |
| DTC field names in product code (patch) | Acceptable simplification, lead's instruction |

## Subtract pass

Removed on this pass: an `after_migrate` wrapper that only called `apply()` (hooks now call
`apply` directly); a second cache clear in `apply()`; an `on_rule_set_update` doc_event (a
method on our own doctype does it); a copy of the upstream picker function (the override
checks, then calls upstream). Considered and kept: deriving the rule-set settings from the
`*_field` names rather than a second list of six.
