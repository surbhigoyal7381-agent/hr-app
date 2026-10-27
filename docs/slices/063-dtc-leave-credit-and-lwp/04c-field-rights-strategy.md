---
slice: 063-dtc-leave-credit-and-lwp (SEC-17), ALV-215
artifact: 04c-field-rights-strategy (impact analysis and build strategy)
author: hrms-fullstack-engineer
date: 2026-10-24
status: PROPOSAL - waiting for Surbhi's approval. No code written, nothing committed, nothing pushed, no site changed.
inputs: 01g-employee-field-rights.md; 01c revision 4 / 4b (SEC-17); Surbhi's decisions of 24 Oct 2026 (below); code at origin/dev 6aaf9ffd; installed Frappe 16.33.1 in hrlocal-bench; read-only SQL on 33 local site databases in hrlocal-mariadb (counts and settings only, no names)
---

# Who may change which Employee field - build strategy (ALV-215)

## The answer first

**Build it in three steps. Only step A blocks the DTC switch-on.**

| Step | What | Rung | Blocks switch-on? |
|---|---|---|---|
| **A** | Lock the job, pay and approver fields (level 2) and the bank fields (level 1) at every tenant, and stop anyone changing these fields on their own record | Configuration applied by code on every migrate, plus one small check (rung 2-3, and rung 4 for the check) | **Yes** |
| **B** | Close the bank-number leak in `get_employee_field_property` | A 3-line check (rung 4) | No. Separate ticket, same release |
| **C** | A second person for bank-account changes | A small check on two doctypes (rung 4) | No. **Waits for decision D1**, because the tool it needs is switched off by the plan at PPJ |

**Bad news, three items:**

1. **There is no local copy of DTC or Grace.** I surveyed all 33 local databases. "DTC Demo" is a demo with none of DTC's `dtc_*` fields. So I could not check DTC or Grace. A read-only query on those sites is still needed before release (section 7, step 1).
2. **Payroll User IS in use at PPJ.** 6 enabled people hold it, and all 6 are also HR User. At PPJ, Payroll User can change bank details (level 1). So today 6 of PPJ's 13 HR Users do see and change bank details. This contradicts "HR User may not see bank details (as PPJ)". **Decision D2.**
3. **Employee Promotion is switched off by the plan at PPJ.** The plan gate leaves only a System Manager row on it. Employee Promotion belongs to the "tenure" feature (Business plan). So the bank "second person" route cannot run at PPJ as things stand. **Decision D1.** This is why step C is held.

## Surbhi's decisions (24 Oct 2026), as I apply them

| # | Her decision | Where it lands |
|---|---|---|
| Q1 | Second person for bank-account changes at every client with 2+ HR people. Job and pay fields: no second person unless a client asks | Step C (bank). Level 2 is single-person, with history |
| Q2 | HR User may not see or change bank details (as PPJ) | Step A: the 13 PPJ level-1 fields copied to every tenant. HR User gets no level-1 row |
| Q3 | A manager may not propose changes; they ask HR | Nothing built. Managers are employees |
| Q4 | Approve R4: no edits to your own Employee record, HR included | Step A: one `validate` check on Employee |
| Q5 | No Payroll User at any tenant unless I find one | **Found one: PPJ, 6 people.** D2 |
| Q6 | "Employee Promotion" is an acceptable name on screen | Step C |
| - | Applies to every tenant | Step A runs on every site, on every migrate and every new install |

---

## 1 · The exact field list

### 1.1 The 13 the request names

The request says "12 at DTC plus `reports_to` and `company`". 01g's 12 already include
`reports_to` (01c's eight, plus three rule-set fields, plus `dtc_agency`). Adding `company`
makes **13**:

| # | Field | Why it matters | At which tenants |
|---|---|---|---|
| 1 | `designation` | Picks the Housekeeping credit table (SEC-18) | All |
| 2 | `employment_type` | The rule set's `category_field` at DTC | All |
| 3 | `reports_to` | Moves manager permissions in the same save (`manager_scope.on_employee_update`) | All |
| 4 | `leave_approver` | Picks who approves leave | All |
| 5 | `company` | `permitted_companies` falls back to the HR person's own company (`access.py`). Cross-company | All |
| 6 | `dtc_leave_class` | `leave_class_field` - leave credit | DTC only |
| 7 | `dtc_grade` | `grade_field` - rates | DTC only |
| 8 | `dtc_double_deduction` | `double_deduction_field` | DTC only |
| 9 | `dtc_green_eligibility` | `green_eligibility_field` | DTC only |
| 10 | `dtc_11am_quarter_deduction` | `late_window_employee_field` | DTC only |
| 11 | `dtc_pay_type` | Describes pay. No code reads it (01g) | DTC only |
| 12 | `dtc_employee_category` | Describes pay. No code reads it (01g) | DTC only |
| 13 | `dtc_agency` | Decides which agency gets a person's days (PRIV-7) | DTC only |

### 1.2 The rest of level 2 - from 01g §3.1, which Surbhi agreed

`department`, `branch`, `grade`, `expense_approver`, `shift_request_approver`, `holiday_list`,
`default_shift`, `attendance_device_id`, `date_of_joining`, `relieving_date`, `status`,
`user_id`, `first_name`, `middle_name`, `last_name`, `gender`, `date_of_birth` (17 fields).

**Level 2 rule:** HR User and HR Manager write. Every role that reads Employee at level 0 also
reads at level 2, so no screen loses a field. Employee Self Service gets **read only**.

### 1.3 Level 1 - PPJ's 13, copied to every tenant (Q2)

`bank_ac_no`, `bank_name`, `iban`, `ifsc_code`, `micr_code`, `ctc`, `salary_mode`,
`salary_currency`, `pan_number`, `esi_number`, `provident_fund_account`, `payroll_cost_center`,
`employee_advance_account`.

**Level 1 rule:** HR Manager reads and writes. Nobody else gets a new row. Rows that already
exist (PPJ's Payroll User and System Manager) are left alone.

**Check this consequence (D3):** "as PPJ" also takes PAN, ESI, PF, CTC, salary mode and the two
accounts away from HR User at every other tenant - not only bank details. At DTC, if an HR User
enters PAN or ESI numbers for new joiners today, that moves to the HR Manager. The other way is
to lock only the five bank fields at level 1 and put the other eight on level 2. I recommend
**keeping it as approved (all 13)**, because it is one rule everywhere and it is what PPJ
already runs.

### 1.4 How the list reaches a tenant's own custom fields

- The **standard** fields (1.1 rows 1-5, 1.2, 1.3) are a fixed list in the code. A field the
  site does not have is skipped (`meta.has_field`).
- **Fields named by a pay rule set** (rows 6-10 at DTC) are read from every
  `Alvoraa Payroll Rule Set` (`*_field` settings) and locked at level 2. This runs on migrate
  **and** when a rule set is saved. So the next client's custom pay field is locked the moment
  their rule set names it - no list to remember, no CI scan that cannot see tenant data.
- **The three DTC-only fields the rule set does not name** (`dtc_pay_type`,
  `dtc_employee_category`, `dtc_agency`) get a one-time data change on DTC: three Property
  Setters at level 2, the same thing Customize Form would write. **This keeps a tenant's field
  names out of the product code.** It is a production data change, so it needs Surbhi's word
  on the day (section 7, step 6).

---

## 2 · Impact analysis

### 2.1 Cross-module and callers

| Area | Effect | Evidence |
|---|---|---|
| `alvoraa_portal` - portal self-service | **No change.** No portal screen or endpoint writes Employee. Portal reads use `frappe.db.get_value` / `get_all`, which ignore levels | Grep of `alvoraa_portal`, `alvoraa_goals`, `hrms/hrms/alvoraa_*` for Employee `set_value`, `save`, `insert`, and of all JS for `resource/Employee` and `client.set_value` on Employee: none from the portal. The Frappe HR phone app has no profile edit |
| `alvoraa_portal.manager_scope.on_employee_update` | Unchanged for HR edits. For a self-edit, Frappe resets `reports_to` **before** `on_update` runs, so the hook sees no change and the real manager keeps access | Frappe `document.py:592` runs `validate_higher_perm_levels` before `run_before_save_methods` |
| Positions chart (`alvoraa_org_structure/api.py`) | **No change.** It only reads Employee (`get_all`, `db.get_value`). It never reconciles `reports_to` | `api.py:406-410` "Never reconciled automatically" |
| Position cover (`alvoraa_position_assignment.py:292, 314`) | Keeps working: writes `leave_approver` / `expense_approver` with `frappe.db.set_value`, which skips levels and the new check. Existing audit gap (no Version row), already noted in 01g | Read the code |
| `module_access` (plan gate) | Does not restrict Employee. Snapshots keep `permlevel`, so level-2 rows survive a plan change | `module_access.py:363` |
| User Type sync (Frappe HR, every migrate) | Only rewrites level-0 rows for its role, and deletes rows only on doctypes **not** in its list. Employee is in the list, so the level-2 read row for Employee Self Service survives | Frappe `user_type.py:135-155` |
| `permission_health` (ALV-127) | Employee is already in custom-permission mode at every tenant (4 rows on most sites, 9 at PPJ). Adding rows does not change that | Local survey |
| Data Import | HR User import of level-2 fields works. **HR User import of level-1 columns (bank, PAN, ESI, PF, CTC) is silently ignored** - Frappe resets them without an error | Frappe `validate_higher_perm_levels` runs on every save, import included |
| Employee Promotion / Transfer | Keep working for HR User and HR Manager on level-2 fields. A promotion **about yourself** is refused by the new Employee check, because the submit saves your own record | `employee_promotion.py:55` saves the Employee as the submitter |
| `hrms` Employee events | Our `validate` runs alongside `validate_onboarding_process` and `validate_documents`. Neither touches these fields | `hrms/hooks.py:250` |
| `alvoraa_goals`, `alvox_compensation`, `erpnext` | No change. Nothing there writes these fields as a user | Grep |
| Scripts run as Administrator (DTC sheet loads) | No change. Frappe skips level checks for Administrator, and Administrator has no Employee record | `document.py:1025-1028` |

Functions I will change or call, and their callers:

- `refuse` and `is_own_record` (`hrms/alvoraa_hr_core/access.py`) - **called, not changed.**
- `AlvoraaPayrollRuleSet.on_update` - new one-line method. The rule set has no `on_update` today.
- `hrms.hr.utils.get_employee_field_property` (step B) - one caller:
  `hrms/hr/employee_property_update.js:133` (the Promotion and Transfer field picker).
- Frappe `add_permission`, `update_permission_property`, `make_property_setter` - **verified in
  the installed 16.33.1** (`permissions.py:659, 693`; `property_setter.py:74`).
  `add_permission` copies the standard rows first if a doctype has no custom rows
  (`setup_custom_perms`), so nobody loses access on a site with zero custom rows.

### 2.2 Personas

| Persona | What changes |
|---|---|
| **CXO** (System Manager) | Nothing for other people's records. Cannot change their own job, pay or bank fields (R4). At most tenants System Manager has no Employee row at all today - unchanged |
| **HR Manager** | Same as today for everyone else. Cannot change their own record's locked fields: another HR person does it. Step C: a bank change needs a second HR Manager |
| **HR User** | Job, pay-setting and approver fields: same as today. **Loses read and write on the 13 level-1 fields at every tenant except PPJ** (already so there). Cannot change their own locked fields |
| **Employee** (and manager) | Can no longer change job, pay, approver or identity fields on their own record. Phone, email, address, emergency contact, blood group, marital status: still editable. Sees the same fields as before |

### 2.3 HRMS domain

Leaves (`leave_approver`, `holiday_list`, leave class), attendance (`attendance_device_id`,
`default_shift`, `holiday_list`), payroll (rule-set fields, bank, PAN, ESI, PF, CTC), org
structure (`reports_to`, `department`, `designation`, `company`), appraisals (`reports_to`
routes reviews). **No values change anywhere. Only who may change them.**

### 2.4 Local survey - read-only, 24 Oct 2026, 33 databases

| Finding | Count |
|---|---|
| Sites with Employee fields above level 0 | 1 (PPJ copy: 13 at level 1) |
| Sites with any Employee field at level 2 | **0** - so level 2 is free everywhere I could see |
| Sites with Custom DocPerm rows on Employee | 31 of 33 (4 rows on most; 9 at PPJ; 14 on three test sites) |
| Sites with an enabled Payroll User | 1 (PPJ: 6 people, all also HR User) |
| PPJ HR people | 4 HR Manager, 13 HR User, 1 System Manager, 402 Employee Self Service |
| PPJ Employee Promotion | Blocked by the plan (only a System Manager row). 0 promotions, 0 transfers |
| Local copies of DTC or Grace | **None** |

---

## 3 · Strategy

### 3.1 Ladder

| Rung | Used for | Why the cheaper rung was rejected |
|---|---|---|
| 1 · Already there | Frappe field permission levels; Version history (`track_changes` = 1); Employee Promotion | - |
| 2-3 · Configuration | Property Setters (`permlevel`) and Custom DocPerm rows | - |
| 4 · New code | (a) one function that applies the configuration on every site; (b) one `validate` check (R4); (c) step B's 3 lines; (d) step C | (a) a fixture, a patch or Customize Form cannot do it safely at every tenant - see 3.2. (b) no setting can say "not on your own record". (c) the endpoint ignores levels by design. (d) Frappe can make a second person draft, but never stop an HR Manager editing directly |
| 5-6 · New doctype or app | **Not used.** No Workflow (01g §2: whole-document, and its self-approval rule is skipped by a direct submit) | - |

### 3.2 How it reaches existing tenants - patch vs fixture vs Customize Form

| Mechanism | Existing tenants | New tenants | Survives upgrades and image rebuilds | Verdict |
|---|---|---|---|---|
| **Customize Form by hand** | One by one | Missed | Yes - Property Setters live in the database | **Rejected.** Manual, drifts, nobody remembers the next tenant |
| **Patch** (`patches.txt`) | Once, at migrate | **Never runs.** A fresh install marks every patch as done without running it (Frappe `installer.py:358`, `set_all_patches_as_completed`) | Yes | **Rejected** on its own - new tenants would ship open |
| **Fixture** (Property Setter / Custom DocPerm in `hooks.fixtures`) | Every migrate | Yes | Yes | **Rejected.** A Custom DocPerm fixture imports whole rows by name and would replace a tenant's own rows (PPJ's Payroll User, the plan gate's rows) - the "direct insert" danger `permission_health.py` describes. A Property Setter fixture would fail or leave orphans on sites without the field |
| **Idempotent `after_migrate` + `after_install` function** | Every migrate | Yes (`after_install`) | Yes - the setting is in the database; the code is in the image; every deploy runs migrate, which re-applies it | **Chosen.** It is this repo's existing pattern (`payroll_fields`, `field_app_desk`, `manager_scope`). It also heals drift: if someone resets Employee permissions in Role Permission Manager, the next migrate puts the floor back |

**The sites volume trap does not bite here.** That trap is about `sites/assets` files being
hidden by the volume. This change has **no JavaScript, CSS or asset**. The setting lives in the
database, and the code lives in the app folder inside the image.

**What the function does, on every migrate (safe to run twice):**

1. If Employee does not exist, stop.
2. For each field in the level-2 list and the rule-set-named fields: if the site has the field
   and its level is **0**, write a Property Setter `permlevel = 2`. **Never lower a field that
   is already above 0** (PPJ's 13 stay at 1).
3. For each field in the level-1 list: if the site has it and its level is 0, write
   `permlevel = 1`.
4. Level-2 rows: for every role that has a **level-0** row on Employee, add a level-2 row if
   missing - read for all, write only for HR User, HR Manager and System Manager when that role
   already writes at level 0. (Frappe will not accept a level-2 row for a role without a
   level-0 row - `doctype.py:1880` - so rows are only added where they mean something.)
5. Level-1 row: HR Manager read + write, if missing. Nothing else added, nothing removed.
6. Clear the Employee cache only if something changed.

Two batched reads (existing Property Setters, existing Custom DocPerm rows), then only the
writes that are missing. On an already-applied site it writes nothing.

### 3.3 R4 - nobody changes these fields on their own record

One `validate` handler on Employee (new file `alvoraa_portal/employee_field_rights.py`, the same
file as the function above):

- If the record is new, stop.
- List the fields above level 0 whose value changed (`doc.meta.get_high_permlevel_fields()` and
  `doc.has_value_changed()`, both verified in 16.33.1). If none, stop - **no query**.
- If the record's stored `user_id` is the caller (`is_own_record`), refuse with the existing
  `refuse()` (logs user, doctype and name only - no personal data):
  *"You cannot change your own job, pay or bank details. Ask another HR person to make this
  change."*

It reads the level from the field itself, so it covers every locked field - including the next
tenant's - with no second list. It also covers Employee Promotion and Transfer about yourself,
because their submit saves your own record. **So no extra hooks on those two doctypes.**

Because Frappe resets an Employee Self Service user's attempt **before** `validate`, this check
never fires for an ordinary employee - they are simply ignored (R1). It fires for HR, who hold
the levels.

### 3.4 Step B - the bank-number leak (separate ticket)

**Proposed ticket (ALV, bug, P2):** *"Field picker on Promotion and Transfer returns any Employee
field, including bank account numbers, to anyone who can open that Employee."*

`hrms.hr.utils.get_employee_field_property` opens the Employee with a document check, then
returns any field, ignoring levels. After the fix: if the caller has no read at that field's
level (`doc.has_permlevel_access_to(fieldname, df=field, permission_type="read")`, verified in
16.33.1, `document.py:1056`), refuse with *"You do not have access to this field."*

**Two ways to build it - Surbhi chooses (D4):**

| Option | Change | Cost |
|---|---|---|
| **B1 (recommended)** | 3 lines in our hrms fork's `hr/utils.py` | Our fork has been edited in this file before (8965ef55). A future upstream merge could drop it - a pin test catches that. The agent rules treat any edit to Frappe HR's own source as your call, so I am asking |
| B2 | `override_whitelisted_methods` in `alvoraa_portal/hooks.py`, pointing to our own copy of the function | Leaves the fork untouched, but adds a copy that can drift from upstream and one more line in a hot file |

It matters more after step A: step A hides bank fields from HR User on forms, and this call is
the way round that.

### 3.5 Step C - a second person for bank changes (held for D1)

**Why it needs code:** Employee Promotion can make one person draft and another submit, but an
HR Manager holds level-1 write and can always edit the Employee directly. Only a check can stop
that.

The design, when D1 is answered:

- Employee `validate` (the same handler): if a **bank** field (`bank_ac_no`, `bank_name`,
  `ifsc_code`, `iban`, `micr_code`) changed on an existing record, and the site has **2 or more**
  people who can change bank details, refuse unless the save comes from a submitted Employee
  Promotion. Message: *"Bank details change through an Employee Promotion that a second HR
  Manager submits."*
- Employee Promotion `before_submit` and `before_cancel`: if it changes a bank field, refuse
  when the submitter is the person who drafted it; otherwise mark this request as an approved
  bank change for that one Employee.
- A new joiner's first bank details are not a "change" and stay single-person.
- At a tenant with one person who can change bank details: single-person, Version history only
  (an intentional trade-off: there is nobody to be the second person).

**Costs to accept:** bulk bank updates by Data Import are refused at 2+-person tenants - one
Promotion per person, or a script run as Administrator.

**D1 - the blocker:** Employee Promotion is in the "tenure" feature (Business plan). At PPJ the
plan has switched it off. Choices:

| Option | Effect |
|---|---|
| C1 | Let Employee Promotion through the plan gate for every plan. It is a control here, not a sold feature. **A plan change, so it goes to the product manager first** |
| C2 | Use Employee Transfer instead (not blocked at PPJ). Works, but the screen says "Transfer" for a bank change |
| C3 | Turn step C on only where the plan includes "tenure". Starter tenants keep single-person bank changes with history |

My recommendation: **C1**, routed through `hrms-product-manager`. Until then, step C waits and
bank changes stay HR-Manager-only with Version history (step A).

---

## 4 · Files I will change, and the parallel-work check

| File | Change | Who else is in it | Plan |
|---|---|---|---|
| NEW `alvoraa_portal/alvoraa_portal/employee_field_rights.py` | `apply()` and the R4 check (step C adds to it) | Nobody | - |
| `alvoraa_portal/alvoraa_portal/hooks.py` (**hot file**) | `"validate"` on Employee; one line each in `after_migrate` and `after_install` (step C: two lines for Employee Promotion) | 063-dtc-leave, 067, alv-211 have lines here; several unpushed slices on the work board | Add lines only, at the end of each list. Fetch and rebase just before commit. Check their lines survive |
| `alvoraa_payroll_rule_set.py` | New `on_update` that calls `apply()` | 059 / 063 / 067 built on this doctype | One new method, no existing line touched. Rebase before commit |
| NEW `alvoraa_portal/alvoraa_portal/tests/test_employee_field_rights_alv215.py` | Tests below | Nobody | - |
| Step B: `hrms/hrms/hr/utils.py` (or `hooks.py` if B2) + its test | 3 lines | Nobody recently | Separate commit, separate ticket |

**What came in:** origin/dev is 8 commits ahead of this worktree (6aaf9ffd: Positions chart,
attendance correction decisions, full-width portal). I read the file list. None of them touch
Employee permissions, `hooks.py`, `access.py` or the rule set. The build will be in its own
worktree `.claude/worktrees/215-field-rights` on `slice/215-field-rights` from `origin/dev`.

---

## 5 · Tests - one per rule, each written first and seen to fail

All in `alvoraa_portal`, run on `test_site`. Test names carry `alv215` so a bad merge that drops
the feature fails CI. Each guard is broken on purpose once to prove its test can fail.

| # | Rule | Test |
|---|---|---|
| T1 | R1 | Employee Self Service user with a User Permission on their own record sends `PUT /api/resource/Employee/<own>` changing `designation`, `reports_to`, `leave_approver`, `employment_type`, `company`, `attendance_device_id` and one rule-set-named field → every stored value unchanged, **and the old manager still holds their User Permission** |
| T2 | R1 | The same user changes their own `cell_number` → saved (self-service still works) |
| T3 | R1 | HR User changes another employee's `designation` → saved; a Version row names the user, the old and the new value |
| T4 | R2 | HR User changes another employee's `bank_ac_no` → unchanged; HR Manager → saved. HR User GET of that Employee does not return `bank_ac_no` |
| T5 | R4 | HR User changes `company` on their **own** record → refused with the message; their own `cell_number` → saved. HR Manager submits an Employee Promotion about themselves → refused |
| T6 | migration | On a site with Employee custom rows **and** on one with none: after `apply()`, every listed field is at the right level; HR User and HR Manager write at level 2; every level-0 reader reads at level 2; no level-0 row lost. Run `apply()` again → nothing written. A field already at level 1 stays at 1 |
| T7 | rule set | Save a rule set naming a custom Employee field → that field is at level 2 |
| T8 | step B | HR User calls `get_employee_field_property(<emp>, "bank_ac_no")` → refused; `designation` → value returned; HR Manager `bank_ac_no` → value returned |
| T9 | step C (only if built) | HR Manager A drafts a bank change, A submits → refused; B submits → applied; A edits `bank_ac_no` directly → refused; with only one HR Manager → direct edit saved |

Then a rehearsal of `apply()` on the local PPJ copy (shared bench - book it on the work board):
the 13 level-1 fields untouched, Payroll User's rows untouched, 17 + 5 fields at level 2.

Removed from 01g's list on purpose: a separate Data Import test (import goes through the same
save, T1-T4 cover it) and a CI scan of "enabled rule sets" (CI has no tenant rule sets; T7 and
the rule-set hook replace it).

---

## 6 · NFR - before and after

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **neutral** | Employee save: no extra query unless a locked field changed, then one `get_value`. Migrate: two reads, writes only on first run |
| Security | **improves** | Closes self-edit of pay, approver and company fields on desk, REST and import; closes the own-record company path to another company; step B closes the bank-number leak |
| Reliability | **neutral, one risk** | If level-2 rows were missing, HR edits would be silently undone. Guarded by T6 and the release query. Step A adds no failure path to a normal save |
| Scalability | **neutral** | Nothing grows with headcount |
| Maintainability | **improves slightly** | One file, one rule list, re-applied every migrate. The R4 check reads levels, so it needs no second list |
| Data integrity | **improves** | Pay inputs change only through HR, recorded in Version history. No values migrated |
| Compliance / privacy | **improves** | Bank, PAN and ESI numbers leave HR User's view at every tenant (need-to-know). Logs carry user and document name only |

---

## 7 · Release order - before the leave and grooming switch-on

| # | Step | Who says go |
|---|---|---|
| 1 | Read-only query on **DTC, Grace and PPJ production**: which Employee fields are above level 0; which Employee Custom DocPerm rows exist; how many people hold HR Manager and Payroll User. **Stop if any site already uses level 2** | Surbhi (production read) |
| 2 | Build step A (+ B if D4 answered) locally; tests; rehearsal on the PPJ copy | Surbhi approves this strategy |
| 3 | Review, security review | - |
| 4 | Push to dev → migrate applies it at every dev tenant → check one dev tenant by the release query | Surbhi: "push to dev" |
| 5 | Push to main → production migrate applies it at every tenant | Surbhi: "push to main" |
| 6 | DTC data change: three Property Setters (`dtc_pay_type`, `dtc_employee_category`, `dtc_agency`) at level 2. Written rollback alongside | Surbhi, on the day |
| 7 | Release query on DTC: all 13 fields of 1.1 at level 2, the 13 of 1.3 at level 1, the rows present | - |
| 8 | **Only then** switch on DTC's leave rule set (063) and the grooming rule (066) | Surbhi |
| 9 | Step C after D1 | Surbhi |

---

## 8 · Rollback

**No Employee values change, so rollback loses no data.**

1. Revert the commit first - otherwise the next migrate puts everything back.
2. Delete what step A created: Property Setters on Employee with `property = "permlevel"` and
   `value = "2"`; level-1 Property Setters for the 13 fields **created after the release time**
   (PPJ's own, dated 14 Sep 2026, stay); Employee Custom DocPerm rows at level 2; the HR Manager
   level-1 row where it was created after the release time.
3. Clear the Employee cache - needs Surbhi's approval (`bench clear-cache` is on the approval
   list).

The exact script goes in the implementation notes, and is run only on her word.

---

## 9 · Risks and debts

| Item | Label |
|---|---|
| A site already using level 2 for something else | **Dangerous if skipped** - release step 1 checks it |
| HR User import of bank / PAN / ESI / PF columns silently ignored | Intentional trade-off (Q2). HR Manager does these |
| A one-person HR team cannot change their own job or bank fields | Intentional trade-off (R4). Administrator, or a second person |
| HR Manager can still change bank details alone until step C | Temporary debt - step C removes it, after D1 |
| Payroll User at PPJ still sees bank details | Open until D2 |
| Position cover writes approvers with no Version row and outside R4 | Existing debt, separate ticket (01g) |
| An HR User could set a colleague's `user_id` to their own login | Acceptable simplification - recorded in Version history, HR-only field |

---

## 10 · What Surbhi must decide

| # | Question | My default |
|---|---|---|
| **Approve** | This strategy: step A now, step B with it, step C after D1 | - |
| **D1** | Step C's tool is switched off by the plan at PPJ: C1 (let Employee Promotion through every plan, via the product manager), C2 (use Employee Transfer), or C3 (only where the plan has it) | C1 |
| **D2** | PPJ's 6 Payroll Users (all HR Users) can see and change bank details today. Keep, or remove? | Keep - someone set it deliberately on 14 Sep; my code never removes rows |
| **D3** | Level 1 = all 13 PPJ fields (approved), or only the 5 bank fields? | All 13, as approved |
| **D4** | Step B in our hrms fork (B1) or by override (B2)? | B1 |
| **D5** | Read-only query on DTC, Grace and PPJ production before release (step 1) | Yes |

---

## Subtract pass

Removed on this pass:

- **The `refuse_own_submit` hooks on Employee Promotion and Transfer** that 01g proposed - the
  Employee check already refuses a promotion about yourself, because its submit saves your own
  record.
- **A second field list in the R4 check** - it reads the field levels instead.
- **A code guard for "a site already uses level 2"** - the release query answers it once; no
  local site uses level 2.
- **A CI scan of enabled rule sets (01g T8)** - CI has no tenant rule sets; locking on rule-set
  save does the job where it matters.
- **A separate Data Import test** - same save path as T1-T4.
- **Hard-coded DTC field names in the product** - three Property Setters on DTC instead.
- **Fixtures and a patch** - one migrate function does both jobs.
- **Step C from this release** - it does not block the switch-on and its tool is blocked by
  the plan at PPJ.

Considered and kept: the name, gender and birth-date fields on level 2. They cost nothing extra
(same mechanism, same list) and Surbhi agreed them.
