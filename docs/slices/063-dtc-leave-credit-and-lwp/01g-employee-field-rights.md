---
slice: 063-dtc-leave-credit-and-lwp (SEC-17), ALV-215
artifact: 01g-employee-field-rights
author: hrms-security-privacy-engineer
date: 2026-10-24
status: recommendation - nothing built, nothing changed on any site
inputs: 01c revision 4 / 4b (SEC-17); code in worktree dev-integration-2026-10-24 (eb33129b) and 067-pay-slip-marks; installed Frappe 16.33.1 and hrms 17.0.0-dev in the local container hrlocal-bench; read-only SQL on the local copy ppj.localhost
---

# Who may change which Employee field - for every tenant

*I wrote SEC-17 in 01c. This file extends my own requirement, so somebody else should check it at
review (lesson 6).*

## The short answer

**Yes, Frappe HR can do "one person changes, another approves" - but only partly, and only with
two small settings changes and one small check.** The cheapest safe plan is:

1. **Lock the fields** with Frappe's field permission levels ("permlevel" - a number on each field;
   a role can only change a field if it holds write at that number). Configuration only, no code.
2. **Where a second person must approve,** use the HRMS document that already exists for this:
   **Employee Promotion**. One person drafts the change, an HR Manager submits it, and submitting
   writes the new value onto the Employee. No new doctype.
3. **Nobody changes these fields on their own Employee record**, HR included. This needs one small
   check (new code, a few lines), because no setting can say "not on your own record".

Frappe's **Workflow** is *not* the answer here. Details in §2.

---

## 1 · The facts today

### 1.1 Employees can edit their own Employee record

| Fact | Label |
|---|---|
| Frappe HR's "Employee Self Service" role gets **read and write on Employee**, limited to their own record by a User Permission | Verified in code: `hrms/setup.py` ~line 646 (`"Employee": ["read", "write"]`) |
| On the local PPJ copy: Employee Self Service holds read + write at level 0 on Employee; 402 users have the role. The plain "Employee" role is read-only | Verified by running it (read-only SQL, `ppj.localhost`, 24 Oct 2026) |
| At DTC: all 10 portal logins hold the role, 7 are not HR | From 01c rev 4 (read-only check on DTC, 24 Oct 2026). Not re-checked today |
| No portal screen in our code writes to Employee. The only door is the REST API (`PUT /api/resource/Employee/<own id>`) | Inference: searched `alvoraa_portal`, `alvoraa_goals`, `hrms/hrms/alvoraa_*` for Employee saves and `set_value` calls. Found none from the portal |

### 1.2 The eight fields in 01c, checked again

01c revision 4 named eight: `designation`, `employment_type`, `dtc_leave_class`, `dtc_grade`,
`dtc_pay_type`, `dtc_employee_category`, `leave_approver`, `reports_to`.

**Bad news: the eight are not the full list, even for DTC.** The pay engine reads Employee fields
that the rule set *names*, and the rule set names more than these:

| Rule-set setting | DTC field it names | Read by | In 01c's eight? |
|---|---|---|---|
| `leave_class_field` | `dtc_leave_class` | `leave_rules.py:477`, `payroll_rules_apply.py:185` | yes |
| `category_field` | `employment_type` | `leave_rules.py:477`, `payroll_rules_apply.py:186, 237` | yes |
| `grade_field` | `dtc_grade` | rule set rates | yes |
| `double_deduction_field` | `dtc_double_deduction` | `payroll_rules_apply.py:182, 219` | **no** |
| `green_eligibility_field` | `dtc_green_eligibility` | `payroll_rules_apply.py:183, 219` | **no** |
| `late_window_employee_field` | `dtc_11am_quarter_deduction` | `payroll_rules_apply.py:181, 219` | **no** |

(Verified in code, worktree 067: the rule set's field descriptions in
`alvoraa_payroll_rule_set.json` name the DTC fields; the engine lines above read them.)

- `dtc_pay_type` and `dtc_employee_category`: **I could not find any code that reads them.** They stay
  on the list because 01c found them on DTC and they describe pay. I would need the DTC site's
  Custom Field list to say more.
- `dtc_agency` (rev. 4b) decides **which agency is sent a person's days** (PRIV-7). It belongs on the
  list too.
- Other standard fields the code reads that also move pay or access: `holiday_list`,
  `date_of_joining`, `relieving_date`, `default_shift`, `attendance_device_id`, `status`, `company`,
  `user_id` (Verified in code: counted in `alvoraa_portal` and `hrms/hrms/alvoraa_*`).

### 1.3 What a self-edit does today (concrete scenarios)

All are **Inference** from the permissions and the code. I did not make the writes. Each test in §4
must be written first and seen to fail on today's permissions.

- **An employee hides from their own manager.** An employee with Employee Self Service sends one REST
  call setting their own `reports_to` to a colleague. The hook
  `alvoraa_portal.manager_scope.on_employee_update` (`hooks.py:168-171`, `manager_scope.py:137-152`)
  then **removes their real manager's access to them and gives it to the colleague**, in the same save.
- **An employee picks who approves their leave** by setting `leave_approver`.
  `refuse_own_submit` stops self-approval, but not a friend's approval.
- **An employee raises their own leave credit** (`dtc_leave_class` B to A), or switches off their own
  double deduction or 11 am deduction. Live the moment DTC's rule set is switched on.
- **An employee moves their own punches** by changing `attendance_device_id`.

### 1.4 What one tenant already does

**On the local PPJ copy, 13 bank and pay fields are already locked at level 1** (`bank_ac_no`,
`bank_name`, `iban`, `ifsc_code`, `micr_code`, `ctc`, `salary_mode`, `salary_currency`,
`pan_number`, `esi_number`, `provident_fund_account`, `payroll_cost_center`,
`employee_advance_account`). Level 1 write: HR Manager, Payroll User, System Manager. **HR User has
no level-1 access there.** Set by Administrator on 14 Sep 2026; I could not find which script did it.
(Verified by running it, local copy only.)

**This matters for the design:** if we put the job fields on level 1 too and gave HR User write at
level 1, HR User would gain write on PPJ's bank fields. So the job fields need **their own level,
level 2**.

**Unknown:** the state on DTC (other than the eight), Grace, production PPJ and the other tenants. I
had no access and did not probe production. A read-only query on each site is needed before the
change (§5).

---

## 2 · What Frappe v16 and Frappe HR really offer

| Tool | What it does | Field-level? | Second person? | Verdict |
|---|---|---|---|---|
| **Field permission level** | A role without write at a field's level cannot change it. Frappe quietly puts the old value back on desk, REST and Data Import alike | yes | no | **Use it.** Verified in code: `document.py:1021-1033` (`validate_higher_perm_levels`, runs on insert and save), `base_document.py:1484-1525`, `data_import/importer.py:289, 309` (import saves with permissions on) |
| **Version history** (`track_changes`) | Every save records who, when, old and new value | yes | after the fact | **Already on.** Employee `track_changes` = 1 in the standard doctype (Verified in code) |
| **Workflow** | States and role-based buttons on a whole document | **no**, whole document | weakly | **Do not use on Employee.** It would route every phone-number change and every import through states. And its "no self-approval" setting is **skipped by a direct submit**: `has_approval_access` is only called from `apply_workflow` (`workflow.py:137, 298`), while a plain submit runs `validate_workflow` and `set_workflow_state_on_action` (`workflow.py:243-292, 440-454`), which check neither who made it nor the transition role. Default for "Allow Self Approval" is **on** (`workflow_transition.json`). Inference from code, not run |
| **Allow on Submit** | Lets a field change after a document is submitted | n/a | no | **Not relevant.** Employee is not a submitted document |
| **Employee Promotion** | Submittable. A child table lists field, current value, new value. On submit it **writes the new values onto the Employee** and saves; on cancel it puts the old ones back | **any** Employee field that is not hidden or read-only (incl. our custom fields) | **yes, if HR User loses "submit"** | **Use it for two-person changes.** Verified in code: `employee_promotion.py:48-64`, `hr/utils.py:87-124`, field picker `hr/employee_property_update.js:48-96`. Out of the box HR User **and** HR Manager can create **and** submit (`employee_promotion.json` permissions), so it is one-person until we change that |
| **Employee Transfer** | Same mechanism for company / department / branch moves; can create a new Employee in the new company | yes | same as above | Use for moves. Verified in code: `employee_transfer.py:46-93` |
| **Salary Structure Assignment** | The real pay figure. Submittable, history kept | n/a | HR User can create **and** submit today | Already the right shape. Remove HR User "submit" if pay needs two people (verified: `salary_structure_assignment.json`) |
| **Leave Policy Assignment** | Leave entitlement. Submittable | n/a | HR User can submit today | Same choice as above |
| **Employee Grade** | A master record (default salary structure). Not submittable. HR User can write | n/a | no | Leave as it is; a grade *change on a person* goes through the `grade` field below |

**Two limits you must know before choosing two-person approval:**

1. **The approver can always edit directly.** Employee Promotion saves the Employee as the person
   who submits it, so the approver must hold write on the field (Verified in code:
   `employee_promotion.py:55` calls `employee.save()` with permissions on). So "two people" binds
   the person who drafts, not the HR Manager. The HR Manager's direct edits are only recorded in
   Version history.
2. **The approver field-picker hides read-only fields.** So lock fields with a permission level,
   **never with "Read Only"**, or they disappear from Employee Promotion
   (`employee_property_update.js:84-88`).

---

## 3 · The recommended matrix (every tenant)

**Ladder:** rung 2-3 (Property Setters and Custom DocPerm rows) for rules R1-R3. Rung 4 (a few lines,
reusing `refuse_own_decision`) only for R4, because no setting can say "not on your own record".
No Workflow, no new doctype.

### 3.1 Three groups of fields

| Level | Fields | Employee / manager | HR User | HR Manager | Second person? | How |
|---|---|---|---|---|---|---|
| **0 - the employee's own details** | `cell_number`, `personal_email`, `current_address`, `permanent_address`, `person_to_be_contacted`, `emergency_phone_number`, `relation`, `blood_group`, `marital_status` | **edit own** | edit | edit | no | As today |
| **2 - job, pay settings, approvers, identity** (new level) | Standard: `designation`, `department`, `branch`, `grade`, `employment_type`, `reports_to`, `leave_approver`, `expense_approver`, `shift_request_approver`, `holiday_list`, `default_shift`, `attendance_device_id`, `date_of_joining`, `relieving_date`, `status`, `company`, `user_id`, `first_name`, `middle_name`, `last_name`, `gender`, `date_of_birth`. **Plus every Employee field an enabled pay rule set names** - at DTC: `dtc_leave_class`, `dtc_grade`, `dtc_double_deduction`, `dtc_green_eligibility`, `dtc_11am_quarter_deduction`, and also `dtc_pay_type`, `dtc_employee_category`, `dtc_agency` | read own | **edit** | **edit** | **no by default**; yes where the tenant asks (option B) | Permission level 2 |
| **1 - bank, statutory IDs, salary** (PPJ already does this) | The 13 fields in §1.4 | no access (as PPJ today) | **no access** | **edit** | **recommended** for bank account changes | Permission level 1, HR Manager (and Payroll User where the tenant uses it) |

**Managers get nothing extra.** A manager is an employee; they ask HR. Fail-closed until you say
otherwise (Q3).

**Read at level 2:** every role that reads Employee at level 0 also gets read at level 2, so no
screen loses the job title. The portal reads with `frappe.db.get_value`, which ignores levels, so
portal pages are unaffected (Inference from the readers I grepped).

### 3.2 The rules

- **R1 - Employees cannot change level-2 fields.** Level 2 rows: HR User, HR Manager, System
  Manager write; all other Employee readers read only.
- **R2 - Only HR Manager (and Payroll User where used) can change level-1 fields.** Keep PPJ's
  setting; copy it to tenants that lack it.
- **R3 - Option B, per tenant: two people for level-2 changes.** Take level-2 write away from HR User,
  take "submit" on Employee Promotion and Employee Transfer away from HR User. HR User drafts an
  Employee Promotion; an HR Manager submits it. Recommended for bank changes (level 1) at every
  tenant with two or more HR people; for level 2 only where the client asks.
- **R4 - Nobody changes level-1 or level-2 fields on their own Employee record**, HR included. A
  small `validate` check on Employee that calls the existing `refuse_own_decision`
  (`hrms/alvoraa_hr_core/access.py`) when one of these fields changes and the record is the
  editor's own; and add `refuse_own_submit` as `before_submit` on Employee Promotion and Employee
  Transfer (the same one-line hook Leave Application uses, `hooks.py:138, 268`), so nobody approves
  a change about themselves.

  *Why it is worth the code:* `permitted_companies` falls back to **the company on the HR person's
  own Employee record** when they have no Company User Permission (`access.py`,
  `permitted_companies`). So an HR User with no Company permission who edits their own `company`
  would act as HR for another company. That is cross-company - the top of the scale. **Inference
  from code, not run.** R4 stops it.

### 3.3 What changes for existing tenants

| Who / what | Effect | Breaks? |
|---|---|---|
| Employees (ESS) at every tenant | Can no longer change job, pay or approver fields over REST. Phone, email, address still work | No portal screen breaks (Inference) |
| HR User, R1 only | No change in daily work | No |
| HR User, if R3 (option B) is chosen | **Cannot set job fields on a new joiner.** Frappe sets them to blank on insert for a user without the level (Verified in code, `base_document.py:1504-1506`). HR Manager must complete new joiners, or HR User drafts a Promotion. Data Import of these fields by HR User is **silently ignored** (`importer.py:309`) | **Yes** - the main cost of option B |
| Payroll User | Read only at level 2. Payroll runs read through the database layer | No (Inference) |
| Recruitment User and other readers | Read at level 2 is added, so forms look the same | No |
| Position Assignment cover (`alvoraa_position_assignment.py:292, 314`) | Writes `leave_approver` with `frappe.db.set_value`, which skips levels, so it keeps working. **It also writes no Version row** - an existing audit gap | No |
| Employee Promotion / Transfer | Keep working; the person who submits needs write at the level | No, if the rows are right |
| Module access snapshots (`module_access.py:363`) | Store `permlevel`, so level-2 rows survive a plan change | No (Inference) |
| User Type sync (Frappe `user_type.py:157-158`) | Only touches level-0 rows, so level-2 rows survive | No (Inference) |
| **Any tenant where a Custom DocPerm row exists on Employee** (all of them, because of the User Type) | Frappe uses only the custom rows. **If the level-2 rows are missing for HR User, every HR User edit of these fields is silently undone** | **Yes, if the migration is wrong** - the test in §4 T7 guards it |
| DTC | 8 + 3 + `dtc_agency` fields locked. Check first whether DTC already uses level 1 or 2 for something | Unknown |
| PPJ | Level 1 stays as it is; level 2 is new | No |
| Grace and others | Unknown. Run the read-only query in §5 first | Unknown |

---

## 4 · One test per rule

Write each test first and watch it fail on today's permissions.

| # | Rule | Test |
|---|---|---|
| T1 | R1 | A user with only Employee Self Service and a User Permission on their own Employee sends `PUT /api/resource/Employee/<own id>` with `designation`, `reports_to`, `leave_approver`, `employment_type`, `company`, `attendance_device_id` and one rule-set-named field changed → every stored value unchanged, and the old manager still holds their User Permission |
| T2 | R1 | The same user changes their own `cell_number` → saved |
| T3 | R1 | An HR User changes another employee's `designation` → saved; one Version row names the user, old and new value |
| T4 | R2 | An HR User sends a change to `bank_ac_no` → unchanged; an HR Manager → saved |
| T5 | R3 (only where chosen) | HR User creates an Employee Promotion changing `dtc_leave_class` → draft saves; HR User submit → refused; HR Manager submit → the Employee shows the new value; cancel → the old value is back |
| T6 | R4 | An HR User changes `company` (and a rule-set field) on **their own** Employee → refused with a message. An HR Manager submits an Employee Promotion about themselves → refused |
| T7 | migration | On a site where Employee has Custom DocPerm rows: after the patch, every level-2 field has `permlevel` 2, and HR User, HR Manager and System Manager hold write at level 2, and every level-0 reader holds read at level 2 |
| T8 | all tenants | For every **enabled** pay rule set, each Employee field it names (`*_field`) is at level 1 or 2. This is the check that catches the next tenant's custom field nobody told us about |
| T9 | picker | Employee Promotion's field list still offers the level-2 fields (none were made read-only) |

---

## 5 · Migration, rollback, risks

**Before:** a read-only query on each site: which Employee fields already have a level above 0, and
which Custom DocPerm rows exist on Employee. **Do not apply level 2 on a site that already uses
level 2 for something else** until we have looked.

**Change (per site):**
1. A patch in `alvoraa_portal` sets `permlevel` = 2 on the standard fields by Property Setter, and adds
   the level-2 Custom DocPerm rows. Same patch on every tenant.
2. Custom fields that exist on one site only (the `dtc_*` fields) are a **dev-stage data change** on
   that site: set the Custom Field's `permlevel` to 2. Written rollback alongside.
3. R2: copy PPJ's level-1 setting to tenants that lack it - **only after Q2**.
4. R3 and R4 only after Q1 and Q4.

**No data is changed.** Only who may change it.

**Rollback:** delete the Property Setters and the level-2 Custom DocPerm rows the patch created (they
can be listed by `property = "permlevel"` and `permlevel = 2`), then clear the cache. Values on
Employee are untouched, so rollback loses nothing.

**Risks:**

| Risk | Label |
|---|---|
| Missing level-2 rows on a site → HR edits silently undone | Guarded by T7 and the release check. **Dangerous if skipped** |
| Option B leaves new joiners half-filled when created by HR User | Intentional trade-off, only if chosen |
| HR Manager can still edit alone; only Version history records it | Intentional trade-off. ISO 27001:2022 control 5.3 (segregation of duties) accepts logging and review as a compensating control where a small team cannot separate roles (secondary sources, checked 24 Oct 2026; not an obligation in our baseline) |
| A new client adds a pay field and forgets to lock it | Caught by T8 |
| Position Assignment writes approvers with no Version row | Existing audit gap, separate ticket |

**Separate finding, outside this slice (write it down, do not fix here):**
`hrms.hr.utils.get_employee_field_property` (`hr/utils.py:191-213`) is whitelisted and returns **any**
Employee field to anyone who can read that Employee, **ignoring field levels**. Scenario: on PPJ, an
HR User (no level-1 access) calls it with `fieldname = "bank_ac_no"` for an employee in their scope
and gets the account number. Inference from code, not run. Major (P2). It also means R2 hides bank
fields from HR User in forms but not through this call.

---

## 6 · Questions for Surbhi

**Must know**

- **Q1 - Second person: which fields, which tenants?** My suggestion: bank account changes at every
  tenant with two or more HR people; level-2 fields single-person with history, unless a client asks.
  *Blocks R3.* Default meanwhile: R1 and R2 only.
- **Q2 - May HR User see and change bank details?** PPJ says no today. *Blocks copying R2 to other
  tenants.* Default: no (as PPJ).
- **Q3 - Should a manager be able to propose a change for their team** (for example a new
  designation)? Default: no - they ask HR.
- **Q4 - Approve R4** (no edits to your own record, HR included). It is new code on Employee, a shared
  doctype. *Blocks the cross-company guard.* Default meanwhile: R1 still stops employees; HR remains
  trusted, recorded by Version history.

**Should know**

- **Q5 - Payroll User:** does any tenant use it? If not, level 1 is HR Manager only.
- **Q6 - Is "Employee Promotion" an acceptable name** on the screen for a leave-class change? It is
  the only existing two-person document. Renaming the label is a translation, not a new doctype.

**Still blocks DTC switch-on:** SEC-17 now means R1 with the fuller DTC list in §1.2 (12 fields, not 8).

---

## Subtract pass

Removed on this pass: a Workflow on Employee (rejected, §2); a new "Employee Change Request" doctype
(Employee Promotion already does it); a periodic review report of Version rows (a procedure, not a
control - Version history is already there to read when needed); making `marital_status` and
`image` HR-only (no pay or access effect). Kept R4 because it is the only thing that closes the
cross-company path.
