---
slice: 063-dtc-leave-credit-and-lwp (SEC-17), ALV-215 - steps A and B
artifact: 06-review (senior architect review of the field-rights build)
author: hrms-technofunctional-reviewer
date: 2026-10-26
reviewed: slice/063-field-rights, tip a9bbc98f, 10 commits on origin/dev 52fc3451 (origin/dev has not moved since)
ran on: my own throwaway site testfr_rev in container hrlocal-063fr (fresh install: erpnext, hrms, alvoraa_portal, alvoraa_goals). No tenant data. Sites testfr and testfr_sec not touched.
---

# Review - who may change which Employee field (ALV-215)

## 1 · Verdict

**BLOCK - three small fixes, then a quick re-review of those lines only.** The design is right
and most of it works when tried (proven below). But two of Surbhi's own decisions are not fully
met, and the new tests fail on a fresh site the first time they run, which is how CI runs them.

What blocks, in one line each:

1. **The tests fail on a fresh site** (2 errors on the first run, OK on the second). CI would go red.
2. **Two Promotion/Transfer paths still drop locked values silently** - the thing Surbhi said must be refused.
3. **A new tenant is not locked for five Indian statutory and bank fields** until the next deploy.

None of these leaks data across companies. None changes stored values on existing tenants
except the silent drop in item 2.

**What I ran and what I did not** (stated first, as the rules ask):

| Ran | Result |
|---|---|
| Fresh site install, then read the Employee permission rows | Locked from the start: 9 rows, 30 permlevel Property Setters (proven) |
| Engineer's test module, run 1 (fresh site) | **16 tests, 2 errors** (PermissionError on Employee write) |
| Same module, run 2 | 16 OK |
| My own attack scripts, as each persona, through the desk save path (`savedocs`), `frappe.client.set_value`, `frappe.client.get/get_value/get_list` and the real method dispatcher | Results in section 4 |
| `scripts/check_app_integrity.py` | OK, 832 checks |

**Not run:** the full suite; `bench migrate` (I called `apply()` directly instead - it is the
function migrate calls); a payroll run or a leave policy assignment as an HR User; anything on a
DTC-shaped site (no local copy has the `dtc_*` fields); india_compliance installed (production
has it, CI does not).

---

## 2 · Blockers

### B1 · The new tests fail on a fresh site - P1

- **Proven.** Run 1 on my fresh site: `Ran 16 tests ... FAILED (errors=2)`, both
  `frappe.exceptions.PermissionError` on Employee `write`. Run 2 on the same site: 16 OK.
- **Why.** `test_employee_field_rights_alv215.py:82` creates the ESS user *before* its Employee
  (line 85). ERPNext then strips the role. I reproduced the message on my site:
  *"User ...: Removed Employee Self Service role as there is no mapped employee."*
  On run 2 the Employee already exists, so the role sticks.
- **Scenario.** CI on a new site -> the two Employee Self Service tests
  (`..._employee_cannot_change_own_...` and `..._employee_still_changes_own_phone`) error ->
  CI is red. Worse, the most important rule (R1, employees cannot edit their own pay fields)
  has never been proven on a fresh-site run.
- **Smallest fix.** In `setUpClass`, create each Employee first, then add the roles (or call
  `add_roles` again after `_employee`). Then run the module once on a brand-new site.

### B2 · Two Promotion/Transfer paths still drop locked values silently - P1

Surbhi's decision: a Promotion/Transfer that touches a field the submitter cannot change is
**refused with a message, not silently put back**. The new hook
(`employee_field_rights.py:173`, `before_submit` only) misses two paths. Both **proven** on my site:

1. **Transfer with "Create New Employee Id", submitted by an HR User.** Frappe HR copies the
   Employee and inserts the copy as the HR User (`employee_transfer.py:50-66`). Frappe blanks
   every level-1 field the HR User cannot write on insert. Result on my site:
   old record `bank_ac_no BANK-111, ctc 50000, status Left`;
   **new record `bank_ac_no None, ctc 0.0`**. The old record is marked Left, so the person's
   live record has no bank account and no CTC, and nobody is told.
2. **Cancel of a Promotion with a revised CTC, by an HR User**, after an HR Manager submitted it.
   `on_cancel` sets `ctc = current_ctc` and saves as the HR User (`employee_promotion.py:58-64`);
   Frappe puts the value back. Result: **Promotion cancelled (docstatus 2), CTC still 2000.**

- **Smallest fix (a few lines in the same function, no new file).**
  (a) Also register `refuse_locked_promotion_fields` as `before_cancel` on both doctypes
  (for a cancel, `revised_ctc` means `ctc` is written back).
  (b) For a Transfer with `create_new_employee_id`, also count every level-1/level-2 field that
  holds a value on the Employee being copied. Add one test for each path.

### B3 · A new tenant starts with PAN, ESI, PF, IFSC and MICR open - P2 (ranked here because it breaks a stated claim)

- **Proven.** On my fresh site, `apply()` ran at install (Property Setters at 03:16:03). Frappe HR
  created `pan_number`, `esi_number`, `provident_fund_account`, `ifsc_code`, `micr_code` as Custom
  Fields when the first Indian Company was made (03:16:58, `hrms/regional/india/setup.py`). They
  stayed at level 0. Then:
  - an Employee Self Service user **changed their own PAN and ESI number** (desk save and
    `client.set_value`);
  - an HR User **read a colleague's PAN** through `frappe.client.get` and `get_list`.
- **Why it matters.** `deploy/provision_tenant.sh` installs the apps first; the company is made
  later in the setup wizard. So every new client tenant is in this state until the next deploy
  runs `migrate` (proven: a later `apply()` moves all five to level 1). The notes say "a new
  tenant starts locked" - true for the standard fields, not for these five.
- **Not a regression** for existing tenants: their next migrate locks them. It is the new-tenant
  promise that is not met.
- **Smallest fix.** Call `employee_field_rights.apply` once more after the company exists - for
  example from this app's `setup_wizard_complete` hook, or as one line at the end of tenant
  setup. Add a test that creates an Indian company after `apply()` and checks the five levels.

---

## 3 · Minors

| # | Finding | Label | Rank |
|---|---|---|---|
| m1 | **The bank number is still on every Salary Slip.** `salary_slip.py:2299-2304` copies `bank_ac_no` into the slip's `bank_account_no`, a level-0 field. HR User, Payroll User and the employee read it there. So "HR User may not see bank details" holds on the Employee record only. Outside this slice; write it down for the security engineer | Inferred from code, not run | P3 |
| m2 | **What `apply()` removes is not recorded.** It deletes every non-HR-Manager level-1 row (`employee_field_rights.py:97-100`). Rollback relies on the D5 release query output being saved first. Make "save the query output" a must-do step in the release checklist | Proven by reading | P3 |
| m3 | **A field a rule set names stays locked for good.** If a rule set names `cell_number` by mistake, employees lose their phone edit (proven: level 2 after save). A rule set naming a field that does not exist saves with no warning (proven). Acceptable; mention it to whoever sets up rule sets | Proven | P3 |
| m4 | The Promotion field picker still lists bank fields to an HR User; choosing one shows "You do not have access to this field." Correct, a little rough | Proven via the dispatcher | P4 |
| m5 | Three DTC field names now live in product code (the patch). The lead asked for it; 04c had avoided it | Acceptable simplification | P4 |

---

## 4 · Trying to break it - what happened

All on testfr_rev, as real users, unless marked otherwise.

| Attack | Result | Label |
|---|---|---|
| Employee edits own designation, reports_to, ctc, bank, status, device id (desk save) | All unchanged; phone saved | Proven |
| Employee `client.set_value` own leave_approver | Unchanged | Proven |
| Employee REST `PUT` | Same `doc.save()` path as the desk save | Inferred |
| Employee edits own PAN / ESI | **Changed** on a new tenant (B3) | Proven |
| Portal self-service | No portal code writes Employee (grep of alvoraa_portal, alvoraa_goals, hrms `alvoraa_*`) | Inferred |
| HR User / HR Manager edits own phone (desk save) | Saved - no false refusal from the R4 check | Proven |
| HR Manager edits own ctc or bank | Refused with the message | Proven |
| HR User edits own reports_to | Refused | Proven |
| HR User saves own record with company unchanged | Saved | Proven |
| HR User changes own company | Refused (engineer's test) | Proven by test |
| HR Manager edits a colleague's reports_to and designation | Saved | Proven |
| HR User edits colleague's bank | Put back silently (as designed for the form, where the field is hidden) | Proven |
| HR User reads bank via picker (real dispatcher) | Refused; designation returned; HR Manager gets the bank number | Proven |
| HR User reads bank via `client.get_value` / `get_list` | Field stripped by Frappe | Proven |
| Cross-company HR | Not run. Frappe's User Permission check on the `company` link applies | Not checked |
| Rule set naming a field not in the list | Locked at level 2 on save | Proven |
| `apply()` twice | No change on the second run | Proven |
| Re-save of User Type "Employee Self Service" | No rows removed or added | Proven |
| Positions seat assignment / cover | Writes approvers with `frappe.db.set_value`, so skips levels and R4 (existing debt, already in 01g) | Proven by reading |
| Leave policy assignment, attendance, payroll, field app hooks | None writes a locked Employee field; they read with `frappe.db` | Inferred by grep; not run as HR User |
| Promotion/Transfer about yourself | Refused (engineer's test) | Proven by test |
| Transfer with new employee id; Promotion cancel | **Silent drop** (B2) | Proven |

**An existing tenant with customised permissions** - proven on my site with Payroll User
(level 0 and 1), System Manager (level 0 write and level 1 write) and a custom role writing at
level 0:

- **Removed:** Payroll User level 1 (read, write); System Manager level 1 (read, write).
  Only rows with "if owner" off are touched.
- **Added:** level-2 read for Payroll User and the custom role; level-2 read+write for System
  Manager (because it writes at level 0). HR Manager level 1 and HR User/HR Manager level 2
  where missing.
- **Effect to tell the tenant:** a custom HR role that writes Employee can no longer change
  job fields (its edits are put back silently). Already listed by the engineer as intentional.

---

## 5 · AC verification (Surbhi's decisions)

| Decision | Status | Evidence |
|---|---|---|
| 22 job/pay/approver/identity fields HR-only; every reader still reads | Met | Rows after install; desk tests above |
| Every field a pay rule set names is HR-only | Met | Engineer's test; my rule-set check |
| 13 bank/ID/salary fields HR Manager only; Payroll User and System Manager level-1 rows removed | **Partial** | Met on existing tenants (proven). New tenants: 5 of the 13 open until next migrate (B3) |
| R4: nobody changes these on their own record, HR included; Promotion/Transfer about yourself refused | Met | Proven for HR User and HR Manager; test for Promotion |
| Promotion/Transfer with a locked field by an HR User refused with a clear message | **Partial** | Submit path met (test). Transfer copy and cancel paths drop silently (B2) |
| Import with a column the importer cannot change refused loudly | Met | Test calls the hook and pins its wiring. A full import job was not run |
| Rule set save locks its fields | Met | Test, and my check |
| Patch locks DTC's three, does nothing elsewhere | Met on a CI site | Test. Not checked on a DTC-shaped site |
| Step B: picker checks the field level, then calls Frappe HR unchanged | Met | Proven via the real dispatcher |
| Step C held | Met | No step C code in the diff |

## 6 · NFR and migration

| Dimension | 04c / notes said | What I found |
|---|---|---|
| Performance | neutral | Agree. R4 check reads cached meta; one `get_value` only when a locked field changed. Data Import save parses the file once more (and fetches a Google Sheet again, if used) - small |
| Security | improves | Agree for existing tenants. New tenants: B3 |
| Reliability | neutral | **Worse than claimed in two paths** (B2: silent drop). Otherwise agree |
| Scalability | neutral | Agree - nothing grows with headcount |
| Maintainability | improves | Agree. One file, one hook block per doctype, no duplicate dict keys in `hooks.py` (checked) |
| Data integrity | improves | Partial - B2 loses bank/CTC on a transferred record |
| Compliance / privacy | improves | Agree on Employee. Salary Slip still carries the bank number (m1) |

**Migration and upgrade safety:**

| Question | Answer | Label |
|---|---|---|
| Runs on every migrate? | Yes, `after_migrate` | Proven by reading hooks |
| Runs on a new install? | Yes, `after_install`; rows present after my install | Proven |
| Safe to run twice? | Yes | Proven |
| Survives image rebuilds? | Yes. Settings are in the database; code in the app | Proven by reading |
| Sites-volume asset trap? | Does not apply: no JS, CSS or built file in the diff | Proven (diff has none) |
| Hot file `hooks.py` | Lines added only; no second `"Employee"`, `"Data Import"`, `"Employee Promotion"`, `"Employee Transfer"` or `override_whitelisted_methods` key; 066's lines intact | Proven by grep |
| Incoming work | 10 commits, all by this build, linear on origin/dev 52fc3451, no merge commits | Proven |

## 6b · Compliance (SEC-17 and the decisions)

| Obligation | Mechanism | Test | Status |
|---|---|---|---|
| SEC-17: pay-setting fields HR-only on every door | Field levels + `apply()` | R1 tests | **Partial** - tests error on a fresh site (B1) |
| Need-to-know on bank/ID (Q2/D2/D3) | Level 1, HR Manager only | R2 test | **Partial** - new tenants (B3); Salary Slip (m1, outside slice) |
| No self-decision (R4) | `refuse_own_locked_change` | R4 tests | Discharged |
| Audit of HR edits | Employee `track_changes` | Version-row test | Discharged |
| Refusal logs carry no personal data | `refuse()` logs user, doctype, name | Read | Discharged |

## 7 · What to delete

**Nothing.** Each piece maps to a decision. I looked at the Data Import check (Data Import is
System Manager only as shipped, so it bites rarely) - kept, because Surbhi asked for it.

## 8 · What was done well

- **The R4 check reads the field levels instead of a second field list.** Any field locked later is covered for free.
- **Rule-set fields are locked on save**, so the next client's pay field needs no code change.
- **`apply()` only writes what is missing** and was proven twice-safe; it heals a reset in Role Permission Manager at the next migrate.
- **Step B wraps the Frappe HR function** (check, then call it) instead of copying it.
- **Every guard was broken once on purpose** to prove its test can fail.

## 9 · Confidence

- **High** on the field levels, rows, R4 and step B - tried as real users through the real save and dispatch paths.
- **Medium** on the hooks of other modules (leave, attendance, payroll, field app): grep plus the engineer's runs; I did not run a payroll or leave assignment as an HR User.
- **Not checked:** DTC, Grace or PPJ shapes (no local copy); india_compliance installed; a full `bench migrate`; the full suite.

## Subtract pass

Removed from this review: a note on `update_permission_property` ignoring "if owner" (no site
has such a row - no failure scenario); a performance note on `rule_set_fields` (one small query
on save); a finding on custom HR roles losing job-field writes (the engineer already lists it).

---

## Re-review - fixes B1 to B3 (26 Oct 2026)

**Verdict: SHIP - all three blockers are really fixed; I tried to break each one and could not.**
SHIP means ready to ask Surbhi about the push to dev. It is not permission to push.

**What I reviewed.** Tip 66f0ee01 on origin/dev 52fc3451 (origin/dev has not moved). The code
fix is 5b8a9e12; b6c324ba adds one test; 66f0ee01 is docs. All commits by this build, linear, no
merge commits. Code read in full: `employee_field_rights.py`, the hooks block, the new tests,
and upstream `employee_transfer.py`, `employee_promotion.py`, `update_employee_work_history`.

**Where I ran it.** Two new throwaway sites in `hrlocal-063fr`, local only:
`testfr_rev2` (erpnext, hrms, alvoraa_portal, alvoraa_goals) and `testfr_rev2b` (same apps, no
company ever made by me). No other site touched. Both sites are still there; drop them when done.

### The three blockers

| # | Check | Result | Label |
|---|---|---|---|
| B1 | Test module, fresh site `testfr_rev2`, run 1 / run 2 | `Ran 20 tests ... OK` / `Ran 20 tests ... OK` | Proven |
| B1 | Same on `testfr_rev2b` (no company before run 1, as CI) | `Ran 20 tests ... OK` / `Ran 20 tests ... OK` | Proven |
| B3 | Fresh site, before any company: the five fields do not exist. Made the first Indian company, then read the levels | PAN, ESI, PF, IFSC, MICR all **level 1** at once; five Property Setters written by `lock_new_custom_field` | Proven |
| B2 | 22 attack cases as real HR User / HR Manager users, below | All refused before any write, or allowed where they should be | Proven |

**B2 - trying to break it** (my script, on `testfr_rev2`):

| Attack | What happened |
|---|---|
| HR User submits a Promotion with a revised CTC | Refused; CTC unchanged; Promotion still draft |
| HR Manager submits it, HR User cancels | Refused (twice: first by Frappe's cancel right, then with that right bypassed, by the new hook). Promotion still submitted, CTC still the new figure. No "cancelled but applied" |
| HR Manager cancels | CTC put back |
| HR User amends the cancelled Promotion and submits with a CTC | Refused; no amended record kept |
| HR Manager amends and submits | Goes through |
| HR User submits a Promotion with a bank row | Refused |
| HR User submits a Transfer with "Create New Employee Id" (record has bank, CTC, PAN) - same company, and to another company | Refused, naming the three fields. Employee count unchanged; old record still Active with its bank number |
| HR Manager does the same Transfer | New record keeps bank, CTC and PAN; old one Left |
| HR User submits / cancels an in-place Transfer with a bank row | Refused both ways; HR Manager submit and cancel work and the bank number comes back |
| HR Manager and HR User: self-Transfer with new ID to another company; self-Transfer in place to another company | All four refused; no new record, company unchanged, login not moved |
| HR Manager self-Promotion; HR User cancels their own Promotion | Both refused |

Employee Separation writes no Employee field (read `employee_separation.py` and the boarding
controller), so it needs no guard. **Proven by reading.**

### Nothing went backwards

| Earlier guard | Result | Label |
|---|---|---|
| Employee changes own designation, CTC, bank, status, PAN, manager, company (desk save) | All unchanged | Proven |
| Same through `client.set_value` (CTC, PAN, leave approver, bank) and `client.save` | Unchanged | Proven |
| Employee changes own phone | Saved | Proven |
| REST `PUT` | Same `doc.save()` path. Security ran it over real HTTP on 5b8a9e12 (06b); I did not | Inferred |
| HR User own manager; HR Manager own CTC | Refused | Proven |
| HR Manager own phone | Saved | Proven |
| HR User writes a colleague's bank | Not written | Proven |
| HR User reads bank, PAN, CTC with `get_value` / `get_list` | Stripped | Proven |
| Level 1 rows | HR Manager only | Proven |
| Employee import with a bank column | HR User: refused with a message naming the column. HR Manager: accepted | Proven |
| Rule set names a field, it locks | Engineer's test, green on both fresh sites | Proven by test |
| `apply()` twice | No row or Property Setter added or changed (9 rows, 36 setters) | Proven |
| `hooks.py` | No duplicate keys (parsed it); only additions | Proven |
| `ignore_permissions` | Product code still has only the one at `employee_field_rights.py:100` (F-8). New ones are in tests only | Proven |
| `scripts/check_app_integrity.py` | `OK - all consistent`, 836 checks | Proven |

F-0 from 06b is now pinned: the HR User in `test_alv215_hr_cannot_move_themselves_to_another_company_by_transfer`
has no bank or CTC, so only line 191 can refuse it. **Inferred** from my run, where the same
employee shape had empty level-1 fields.

### New, small

| # | Finding | Rank |
|---|---|---|
| n1 | Cancelling a new-ID Transfer (after its new record is deleted) is refused for an HR User whenever the old record has bank or CTC, though cancel only writes status, relieving date and company (`employee_field_rights.py:201-206`). Safe direction; an HR Manager can do it. Proven by reading, not run | P4 |
| n2 | The message reads "Bank A/C No.." - the label already ends in a full stop | P4 |

The earlier minors (m1-m5) and the security findings F-1 to F-10 are unchanged and still
open where they were.

**Not checked:** india_compliance installed on the site; a full `bench migrate`; the full suite;
any DTC, Grace or PPJ copy.

**Subtract pass:** removed a note on the database "commit ignored" warning seen while creating a
company - it comes from setup code outside this change.
