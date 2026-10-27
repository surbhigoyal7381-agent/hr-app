---
slice: 063-dtc-leave-credit-and-lwp (SEC-17), ALV-215
artifact: 06b-security-verification (Employee field rights)
author: hrms-security-privacy-engineer
date: 2026-10-26
code verified: branch slice/063-field-rights, worktree .claude/worktrees/063-field-rights. Started on a9bbc98f; the branch moved to 5b8a9e12 (review fixes B1-B3) while I worked. Every path that commit changed was run again on 5b8a9e12. Verdicts below are for 5b8a9e12.
requirements: 01c revision 4 / 4b (SEC-17); 01g-employee-field-rights.md; 04c-field-rights-strategy.md (both in worktree 067-pay-slip-marks); 05-implementation-notes-field-rights.md
environment: my own throwaway site testfr_sec in container hrlocal-063fr (fresh install: erpnext, hrms, alvoraa_portal, alvoraa_goals; fake people only). Read-only SQL on the local PPJ copy (ppj.localhost). No server, no dev or production site touched.
---

# Employee field rights (ALV-215) - security verification

**I wrote SEC-17 (01c) and 01g myself, so part of this review checks my own requirement (lesson 6).**
The verdicts on the code are checked against running behaviour, not against my own text. But
whether the requirement is the right shape needs a second person. Please ask the architect
reviewer to read §3 (the matrix) with that in mind.

## The answer first

**The write side holds on every door I tried. No blocker for the push to dev.**
An employee cannot change any job, pay, approver or identity field on their own record. That
holds over desk, REST v1 and v2, `frappe.client.set_value`, `client.save`, bulk update and import.
An HR User cannot change bank, PAN, ESI, PF or CTC. Nobody, HR included, can change their own
locked fields: not by a direct save, a Promotion, or a Transfer. That is true on 5b8a9e12. On
a9bbc98f a Transfer about yourself got through (see F-0 below).

**Bad news: "only an HR Manager can see bank, PAN and CTC" is not true yet.** Five read paths
still show them to people below HR Manager. One of them reaches **managers**, not only HR:

| # | Who | Path | What they see | Status |
|---|---|---|---|---|
| F-1 | HR User, a plain manager (reports' records), System Manager | The **form history** (Version rows in `getdoc`'s `docinfo.versions`) | Old and new bank account number, PAN and CTC each time HR changes them | **Verified by running it** |
| F-2 | HR User | **Employee Promotion `current_ctc`** (fetched from `employee.ctc` at level 0) | A colleague's CTC | **Verified by running it** |
| F-3 | HR User | **Employee Promotion detail rows** (`current` / `new`) | The new bank number in a bank change an HR Manager drafted | **Verified by running it** |
| F-4 | HR User | **Salary Slip `bank_account_no`** | Bank number, copied onto every slip | Verified in code (`salary_slip.py:2299-2304`); I made no slips |
| F-5 | HR User | **ESI Deductions / Provident Fund Deductions reports** | ESI number and PF account, read with raw `frappe.qb` that skips field levels | Verified in code (`esi_deductions.py:96`, `provident_fund_deductions.py:85`). HR User can run both (HTTP 200). I made no slips, so no rows came back |

**None of these is new.** Before this branch, bank, PAN and CTC sat at level 0 on every tenant
except PPJ, so everyone with Employee access read them straight off the form. The branch makes
things much better. **So these do not block the push to dev.** But each one must be fixed, or
accepted in writing, before anyone tells a client "only HR Manager sees bank details". F-1 is a
live exposure on every tenant today, including production, and needs its own ticket now
(escalation in §8).

**DTC switch-on (063 leave rules, 066 grooming):** nothing in the code blocks it. Three release
checks block it. I could not run them, because they need read-only access to DTC (§7).

---

## 1 · Threat model, for this change

1. **Who wants it, and what is the cheapest way?** An employee with a portal login raising their
   own leave class or grade with one REST call. An HR person changing their own pay fields or
   company. A manager or HR User reading bank and PAN numbers they have no need for.
2. **Blast radius.** Writes: one record each time, but repeatable by every employee with a login.
   The own-company path is cross-company. Reads: every employee whose bank details were ever
   changed.
3. **What does this make possible that was impossible before?** Nothing new is collected or shown.
   It only takes rights away. The one new surface is a whitelisted override of the field picker,
   and it only adds a check.
4. **How would we find out?** A refusal by our own checks is logged (`access.py:28-48`: user,
   doctype, name, rule; no values). **A silent reset by Frappe is not logged.** An employee who
   tries to raise their own leave class over REST gets HTTP 200 and leaves no trace (F-9).

## 2 · Every rule: met, partly or not met

Tests are in `alvoraa_portal/alvoraa_portal/tests/test_employee_field_rights_alv215.py`. On my
site, on 5b8a9e12: **19 tests, OK** (`bench --site testfr_sec run-tests --module ...`).

| Rule | Verdict | Mechanism (file:line) | Test that proves it | Also checked by running it |
|---|---|---|---|---|
| **SEC-17 (a)-(b)** Employee cannot change `designation`, `dtc_leave_class`, `employment_type`, `leave_approver` over REST | **Met** | Field levels set in `employee_field_rights.py:107-122` (`lock_fields`); Frappe resets them in `document.py:1021-1033` before any hook | `test_alv215_employee_cannot_change_own_job_pay_or_approver_fields` (line 118) | Yes - 6 doors, table §4 |
| **SEC-17 (c)** Own phone still saves | **Met** | `cell_number` stays at level 0 | `test_alv215_employee_still_changes_own_phone` (132) | Yes, on all 6 doors |
| **SEC-17 (d)** HR User changes a colleague; a Version row names them | **Met** | Level-2 write rows, `apply()` lines 79-87 | `test_alv215_hr_user_changes_a_colleague_and_history_says_so` (136) | Yes |
| **SEC-17 field list** (01g: 12 at DTC, plus `reports_to`, `company`) | **Met in code, unproven at DTC** | 22 standard fields (`LEVEL_2`, line 38); rule-set fields (`rule_set_fields`, 125); 3 DTC fields by patch `dtc_pay_fields_level_2.py` | `test_alv215_a_field_a_rule_set_names_is_locked_on_save` (245); `test_alv215_dtc_patch_...` (291) | Yes: rule set locked `dtc_leave_class` / `dtc_grade` at 2; the patch moved my `dtc_agency` from 0 to 2 |
| **SEC-17 release check** - read-only query on DTC before switch-on | **Not done** | - | - | Needs DTC access (§7) |
| **R1** level 2 written only by HR | **Met** | `LEVEL_2_WRITERS`, line 55 | `test_alv215_apply_sets_levels_and_rows_...` (183) | Yes |
| **R2 write** - only HR Manager changes bank, PAN, ESI, PF, CTC | **Met** | Level 1, HR Manager row only, `apply()` 89-101 | `test_alv215_only_hr_manager_changes_or_sees_bank_details` (146) | Yes: HR User's change reset on all 6 doors; HR Manager's saved |
| **R2 read** - nobody below HR Manager sees them | **Partly met** | Form, API, list, report builder, export, print, search, group-by, filters and the field picker all hide them | Same test (checks `frappe.client.get` only) | Yes. **But F-1 to F-5 still show them** |
| **R3** a second person for bank changes | **Not built** (held for D1, as agreed) | - | - | - |
| **R4** nobody changes their own locked fields, HR included | **Met on 5b8a9e12** | `refuse_own_locked_change` (140-157), Employee `validate`; `refuse_locked_promotion_fields` own-record check (191) | `test_alv215_hr_cannot_change_own_locked_fields` (156), `..._promote_themselves` (167) | Yes: HR User and HR Manager refused on all 6 doors, and on Promotion and Transfer about themselves. **No test for a self-Transfer with a new ID (F-0)** |
| **Step B** - field picker no longer returns bank numbers | **Met** | `get_employee_field_property` (234-250) + `override_whitelisted_methods` (`hooks.py:582`) | `test_alv215_field_picker_does_not_leak_bank_number` (263) | Yes, over HTTP: 403 for ESS, HR User and System Manager; value for HR Manager |
| **Loud import** | **Met** | `refuse_import_of_locked_columns` (160-179), Data Import `validate` | `test_alv215_import_with_a_locked_column_is_refused_loudly` (276) - calls the function directly | Yes, through a real Data Import save by a System Manager + HR User: refused, names "PAN Number" |
| **Promotion / Transfer refused loudly** (5b in 05 notes, B2) | **Met** | `refuse_locked_promotion_fields` (182-215), `before_submit` and `before_cancel` (`hooks.py:188-195`) | lines 319, 330, 338, 359 | Yes: HR User bank / CTC Promotion refused; HR User Transfer with a new ID refused, naming bank, CTC, ESI, PAN |
| **New tenant starts locked** | **Met** | `after_install` (`hooks.py:575`); `lock_new_custom_field` for fields made later (217) | `test_alv215_indian_fields_created_after_install_are_locked_at_once` (390) | Yes: my fresh site had level-1 and level-2 rows and levels before I touched it |
| **Migrate function safe twice** | **Met** | `apply()` writes only what is missing | `test_alv215_apply_sets_levels_and_rows_and_runs_twice_for_nothing` (183) | Yes, also on a PPJ-shaped site (§5) |
| 01g T9 - Promotion field picker still offers level-2 fields | **Met (code only)** | The picker filters hidden, read-only and some types, not levels (`hrms/hr/employee_property_update.js:82-88`) | None | No |

## 3 · Trying to break each guard

### 3.1 Writes - who, which door, what happened (my site, over real HTTP)

Each attempt sent `designation`, `employment_type`, `reports_to`, `leave_approver`,
`dtc_leave_class`, `dtc_grade`, `attendance_device_id`, `bank_ac_no`, `ctc` and `pan_number`
together. Doors: REST v1 `PUT`, REST v2 `PATCH`, `frappe.client.set_value`, desk `savedocs`,
`frappe.client.save`, bulk update.

| Who | On | Result on all 6 doors |
|---|---|---|
| Employee Self Service | own record | HTTP 200, **no locked field changed** (silent reset). Real manager kept their User Permission. `company`, `status`, `user_id`, `first_name`, `date_of_joining` tried separately: all unchanged (`company` refused by the Company User Permission) |
| HR User | colleague | Job, pay-setting and approver fields changed (as intended). **Bank, CTC, PAN unchanged** |
| HR User | own record | **Refused**: "You cannot change your own job, pay or bank details..." Own phone still saves |
| HR Manager | own record | **Refused**, same message. Own phone still saves |
| HR Manager | colleague | All fields changed, bank, PAN and CTC included (as intended) |
| System Manager without HR Manager | colleague | Refused: no Employee write row at all on a fresh site |

Also run in-process: own `user_id` unlinking, own `reports_to`, own `company` through
`frappe.client.set_value` - all refused. Setting a colleague's `user_id` to yourself - refused by
ERPNext's duplicate-user check.

### 3.2 Reads of bank, PAN and CTC

| Path | ESS (own) | HR User | System Manager (no HR Manager) | HR Manager |
|---|---|---|---|---|
| `GET /api/resource/Employee/<id>` | hidden | hidden | hidden | shown |
| Desk form (`getdoc`) - the document | hidden | hidden | hidden | shown |
| Desk form - **history (`docinfo.versions`)** | own only | **shown (F-1)** | **shown (F-1)** | shown |
| `frappe.client.get_value` / `get_list`, `/api/resource?fields=` | dropped | dropped | dropped | shown |
| Report builder (`reportview.get`), list view columns | dropped | dropped | dropped | shown |
| Export (`export_query` CSV) | dropped | dropped | dropped | shown |
| Filter by `bank_ac_no` (a yes/no oracle) | 403 | 403 | 403 | allowed |
| Sidebar group-by on `bank_ac_no` | 403 | 403 | 403 | shown |
| Link search (`search_link`) | nothing | nothing | nothing | nothing |
| Print view | hidden | hidden | hidden | - |
| Field picker (override) | 403 | 403 | 403 | shown |
| `Version` list | 403 | 403 | **shown** | 403 |
| Employee Promotion `current_ctc` | - | **shown (F-2)** | - | - |

Link titles use `employee_name`, which is not a locked field. Nothing to leak there.

## 4 · Findings

| ID | Rank | Urgency | Finding |
|---|---|---|---|
| F-0 | - | closed | **On a9bbc98f, an HR person could move themselves to another company and change their own leave class through a Transfer.** I ran it there: HR User, Transfer about themselves, "create new employee ID", new company SecCo Two, `dtc_leave_class` B to A, submitted. A new Active Employee in SecCo Two appeared, linked to their login, class A. `permitted_companies` went from `[SecCo One]` to `[SecCo Two]`. R4 missed it because the new record is an insert (`refuse_own_locked_change` returns on `is_new()`, line 146) and the old one is changed by `db_set`. **5b8a9e12 closes it** at line 191: I ran it again and it was refused. **Still open: no test pins it.** `test_alv215_hr_cannot_promote_themselves` still passes without line 191, because Employee `validate` catches a Promotion. Only line 191 stops an **HR Manager** (who holds every level) doing a self-Transfer with a new ID. **Add one test: HR Manager, Transfer about themselves, new ID → PermissionError, no new Employee.** P2 |
| F-1 | **Major** | **Live, pre-existing - escalate (§8). Not caused by this branch** | **Form history shows bank, PAN and CTC to people below HR Manager.** *An HR User, or a manager opening a direct report's Employee form, calls `frappe.desk.form.load.getdoc`. The reply's `docinfo.versions` carries the last 10 Version rows with old and new values for every changed field.* `frappe/desk/form/load.py:241-250` (`get_versions`) reads them with `frappe.get_all`, with no field-level check. The desk timeline shows them too: `version_timeline_content_builder.js` has no level check. Shown by running it: as manager `sec.boss` (Employee role only) I received `['bank_ac_no', 'BANK-ess', 'BANK-ESS-NEW']` and the PAN pair for their report. As HR User I received the bank, PAN and CTC pairs for a colleague. Before this branch these fields were readable outright on every tenant but PPJ, so the branch narrows the exposure. It does not close it |
| F-2 | Major | P2 - fix before claiming R2, or accept in writing | **Employee Promotion shows a colleague's CTC to HR User.** `current_ctc` is `fetch_from: employee.ctc` at level 0 (`employee_promotion.json`). The server fills it on insert, ignoring levels. Shown by running it: HR User inserts a Promotion for a colleague and reads `current_ctc = 50000`. Fix: put `current_ctc` and `revised_ctc` at level 1 on Employee Promotion, using the same mechanism |
| F-3 | Minor now, **Major when step C is built** | P3 | **A bank change drafted as a Promotion stores the bank numbers in a document HR User can read.** Promotion detail rows (`current`, `new`) are level-0 Data fields. HR Manager drafts `bank_ac_no` → `NEWBANK-1`. HR User opens the Promotion and reads it (shown by running it). Step C plans to route every bank change this way, so step C's design must keep these rows from HR User |
| F-4 | Major | P2, pre-existing | **Salary Slip copies the bank number, and HR User reads Salary Slips.** `salary_slip.py:2299-2304` copies `bank_name` and `bank_ac_no` into `bank_account_no` at level 0. HR User has read on Salary Slip. Code only - I made no slips |
| F-5 | Major | P2, pre-existing | **ESI and PF deduction reports read ESI numbers and PF accounts with raw queries.** `esi_deductions.py:96`, `provident_fund_deductions.py:85` use `frappe.qb`, which skips field levels. HR User can run both (HTTP 200 on my site). Rows not shown because I had no slips. The ECS report uses `frappe.get_list`, which drops level-1 columns (Inference from the read probes) |
| F-6 | Minor | P2 - a release check, not code | **The DTC patch runs once. A DTC field made after it stays open.** `dtc_pay_fields_level_2.py` locks `dtc_pay_type`, `dtc_employee_category` and `dtc_agency` only if they exist when the release migrate runs. `dtc_agency` came in rev. 4b, and **I could not check that it exists at DTC**. `lock_new_custom_field` (217) does not cover these three: they are in neither list and not named by the rule set. Release check: all three exist at DTC before the release, or lock any late one by hand |
| F-7 | Minor | P3 | **`apply()` stops the whole migrate if an Employee permission row names a role the site no longer has.** I built a PPJ-shaped site without the "Recruitment User" role. `add_permission` raised `LinkValidationError: Could not find Row #0: Role: Recruitment User` (`employee_field_rights.py:81`), and `apply()` runs inside `after_migrate`. Rare: Frappe normally refuses to delete a role that is still used. The D5 query should list the roles on each tenant's Employee rows, so we know before the release |
| F-8 | Minor | P4 | **One new `ignore_permissions`** in product code: `employee_field_rights.py:100` (`frappe.delete_doc("Custom DocPerm", ..., ignore_permissions=True)`). It only runs at migrate or install, as Administrator, who skips permission checks anyway, so the flag is not needed and can go. **I found no CI gate that counts `ignore_permissions`** (searched `.github/` and `scripts/`). That gate is mine to build. Not this slice's debt |
| F-9 | Minor | P3, intentional | **An employee's attempt to change a locked field leaves no trace.** Frappe resets the value and answers HTTP 200. No Version row and no log, so attempts cannot be found. Acceptable for now (no new log pipeline without an obligation). Write it down as known |
| F-10 | Minor | P4 | **The DTC patch test fails on any site that already has `dtc_agency`** (`test_...dtc_patch...`, line 292, asserts no Property Setter first). I saw it fail on my site while my seeded `dtc_agency` field was there. Once I removed it: 19 OK. It would fail on a DTC copy |

No P0 introduced by this branch. F-1 is a P0-*type* exposure (a statutory ID reaching people with
no right to it). It is already live everywhere and is **reduced** by this branch, which is why it
does not stop the push. It should not wait for the next slice.

## 5 · What `apply()` changes on a tenant with its own permissions

I copied the exact Employee permission rows and the 13 level-1 Property Setters from the local
PPJ copy (read-only SQL) onto my site, ran `apply()`, compared, then rolled back:

| | Rows |
|---|---|
| **Removed** | `Payroll User` level 1 (read, write); `System Manager` level 1 (read, write) |
| **Added** | level 2 read: `Employee`, `Employee Self Service`, `Payroll User`, `Recruitment User`. Level 2 read + write: `HR User`, `HR Manager` |
| **Changed** | none. No level-0 row touched. PPJ's 13 level-1 fields stayed at 1 |
| **Second run** | nothing written (rows and Property Setters the same) |

It never lowers a field's level, and never changes a level-0 row. It does **remove** every
level-1 row that is not HR Manager's (D2/D3), including rows a tenant made on purpose. It skips
`if_owner` rows: a role whose only Employee access is "if owner" gets no level-2 read, so it sees
those fields blank. That fails closed, and no local site has such a row.

### Which roles lose what, per tenant

| Tenant | What I know | Who loses access |
|---|---|---|
| **PPJ** (local copy, read-only SQL, 26 Oct) | 9 Employee rows; 13 fields already level 1; 5 HR Manager, 14 HR User, 6 Payroll User, 2 System Manager; 409 ESS | **6 Payroll Users** (none hold HR Manager) lose read and write on bank, PAN, ESI, PF, CTC, salary mode, currency and the two accounts. **System Manager's level-1 row goes, but changes nothing in practice:** System Manager has no level-0 Employee row there, so it could not open an Employee anyway. 409 ESS users lose write on 22 job/identity fields; they keep phone, email, address and emergency contact |
| **DTC, Grace, aahr, demo, alvoraa.co** | **No local copy. I did not query them** | By code: bank, PAN, ESI, PF, CTC and the rest of the 13 move from level 0 to HR Manager only. **HR Users, managers and employees** (own record) stop seeing them on the form; HR Users stop changing them; ESS users lose write on the 22 fields plus every rule-set field. A System Manager or CXO without HR Manager loses whatever level-0 Employee access gave them to these 13 fields. At DTC also the 3 patched fields and the rule-set fields. Any custom HR-like role gets level-2 read only |

**The release check (D5) must list, per tenant:** fields already above level 0; Employee Custom
DocPerm rows with their roles; who holds System Manager or Payroll User without HR Manager.
**Stop if any tenant already uses level 1 for other fields, or level 2 at all.**

## 6 · Personal data and DPDP

- **Better:** need-to-know for bank, PAN, ESI, PF and CTC improves on every tenant but PPJ, by a
  lot. Refusal logs carry user, doctype, document name and rule only (`access.py:28-48`). No
  values. No new copy of personal data, no new export, no new public route.
- **Still exposed:** F-1 to F-5.
- **Employees lose sight of their own bank, PAN and CTC on the desk form.** Level 1 is HR Manager
  only, and no "own record" exception exists. They also cannot correct their own name, date of
  birth or gender. Under DPDP (baseline §2, "Accuracy & correction", verified 24 Aug 2026, 63
  days ago, within 90), an employee needs a way to ask for a correction. Today that is "ask HR".
  It is acceptable while the Rules phase in (around May 2027 per the baseline), but it is a
  manual route with no record. **Question for Surbhi (should know):** is "ask HR" enough until
  then?
- I am not a lawyer. Whether showing bank numbers to an HR User breaches the "reasonable security
  safeguards" duty is for counsel. Surbhi's own decision Q2 already says HR User must not see
  them, so the product should meet it either way.

## 7 · What I could not verify, and what I would need

| Item | Why it matters | What I would need |
|---|---|---|
| DTC: do `dtc_pay_type`, `dtc_employee_category`, `dtc_agency` exist, at what level, and which `*_field` values does the rule set hold? | F-6; SEC-17 release check | Read-only query on DTC (D5), with Surbhi's word |
| Grace, aahr, demo, alvoraa.co: current Employee rows and field levels | §5 effect | Same query on each |
| F-4 and F-5 with real rows | Turns "code" into "shown" | Salary Slips on a throwaway site |
| Full portal suite on 5b8a9e12 | I ran only the field-rights module (19 OK) | The engineer's full run |
| Whether any tenant's CXO holds HR Manager | Who loses bank access | The D5 role list |

**What must exist for each control to be visible at DTC (lesson 1):** the rule-set refusals and
resets only show when someone tries. "0 refusals" in the log means nothing. The control is visible
in the **settings**: the release query must show every DTC field at level 2, the 13 at level 1,
and the level-2 rows for HR User and HR Manager.

## 8 · Escalation - F-1 (form history leaks bank and PAN)

- **Decision needed:** fix the history leak now, as its own ticket, or accept it in writing until a
  date.
- **Context:** Frappe sends the last 10 change records with every form, unfiltered. Anyone who can
  open an Employee form sees past bank, PAN and CTC values in the history.
- **Conflict:** R2 (Surbhi's Q2) against the audit trail. Turning off history on Employee would
  lose the record that defends HR changes. Not an option.
- **Who is affected:** every employee whose bank, PAN or CTC was ever changed in the desk, on every
  tenant. Readers: HR Users, managers for their reports, System Managers.
- **Options:**
  (a) **Recommended:** a small wrapper on the two whitelisted calls that load a form's history
  (`frappe.desk.form.load.getdoc` and `get_docinfo`), through `override_whitelisted_methods`, the
  same way as step B. It calls Frappe unchanged, then removes changed-field entries the caller
  cannot read at that field's level. It works for every doctype with locked fields, Salary Slip
  included. The engineer should confirm it is possible (`hrms-fullstack-engineer`).
  (b) Accept until a named date, with the client-facing claim limited to "cannot change".
- **Risk if it waits:** every bank-detail change from today adds to what HR Users and managers can
  read.
- **Owner:** Surbhi to decide; `hrms-fullstack-engineer` for (a).

## 9 · Worries (not findings - I cannot yet write "this actor, this path, sees this")

- Position cover (`alvoraa_position_assignment.py:292, 314`) writes `leave_approver` with
  `db.set_value`, outside R4 and with no Version row. Could an HR Manager covering a position that
  includes their own record become their own leave approver? `refuse_own_submit` should still stop
  self-approval. Known debt from 01g. Not traced.
- `company_email` stays at level 0. An employee can set their own to any address, and the staff
  directory shows it as "work email" (`staff_api.py:82`). Misdirected mail is about themselves,
  but another person could read a wrong address as genuine. Not traced further.
- An HR person with **no** linked Employee and no Company User Permission falls back to an empty
  company list in `permitted_companies`. They could create an Employee in any company with their
  own login as `user_id`, which `is_new()` skips. Frappe-level HR User access is already all
  companies in that case, so this is not R4's gap. Not traced.

## 10 · Residual risk

| Risk | Label | Owner | Accepted on |
|---|---|---|---|
| F-1 history shows bank, PAN and CTC below HR Manager | **Dangerous debt - escalate now** (live, pre-existing) | Surbhi | **not accepted** |
| F-2, F-4, F-5 other read paths for CTC, bank, ESI and PF | Temporary debt - removed by level 1 on those fields, or by fixing the report queries | Surbhi | not accepted |
| F-0 no test pins the self-Transfer refusal | Temporary debt - one test removes it | engineer | - |
| F-6 DTC fields that arrive after the patch | Temporary - the D5 release check removes it | Surbhi, on the day | - |
| HR Manager changes a colleague's bank details alone (step C held) | Temporary debt, D1 | Surbhi | 25 Oct 2026 (D1, recorded in 05 notes) |
| Silent resets leave no trace (F-9) | Intentional trade-off | Surbhi | not yet accepted |
| Employees cannot see or correct their own bank or identity on desk | Intentional trade-off (Q2, R1); route is "ask HR" | Surbhi | not yet accepted |

## Notes on the environment

- My site `testfr_sec` is still in `hrlocal-063fr`, with fake people only. Drop it when done
  (`bench drop-site testfr_sec`).
- **One slip to report:** my first local web server answered for the container's default site
  `testfr` (the reviewer's site), not mine. Before I noticed, it received one ping, one
  Administrator login and one failed login for `sec.ess@example.com`. Nothing was written there
  except the session and login-log rows those create. I then pinned the server to `testfr_sec`
  and stopped it at the end. I did not use `testfr_rev`.

## Subtract pass

Removed on this pass: a proposal to add a log for silent resets (no obligation needs it; kept as
a known gap, F-9); a full STRIDE table; a per-field list of all 22 level-2 fields (it is in the
code and in 04c); a recommendation to rework the Data Import test to go through a real save (my
run proved the real path; the direct call is enough as a pin). Kept F-3 as Minor, because it
decides step C's design.
