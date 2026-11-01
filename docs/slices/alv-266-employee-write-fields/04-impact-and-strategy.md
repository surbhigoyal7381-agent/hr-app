# ALV-266 · Impact and strategy: who may change an Employee record

Written 31 Oct 2026, reworked the same day for Surbhi's new rule. Branch
`slice/alv-266-employee-write-fields`, worktree `.claude/worktrees/alv-266`, rebased on
`origin/dev` 9b99a421 (ALV-249 landed). Local only.

The first version (Option 2: personal fields HR-only) is replaced. Surbhi's rule, given
31 Oct 2026:

1. Nobody but HR changes **anything** on another person's Employee record.
2. A person changes only their **own** personal details, on their own record.
3. HR (HR User, HR Manager, System Manager) changes any record and any field.
4. Specific fields can be granted to managers for their reports, through a small list
   that is empty by default.

Her answers to the first round: D-1 yes (HR may change their own personal details);
D-2 covered by the rule; D-3 quiet put-back only on a person's own record, a refusal
with a message on anyone else's; D-4 accepted (staff ask HR for HR-owned fields).

---

## Bad news first

1. **Staff can no longer change their own HR-owned fields in Desk or the API.** For
   example contract end, notice days, company email, employee number, exit interview
   answers, the birthday-hide tick in Desk. These are put back quietly, as ALV-215 does.
   The portal's own screens keep working (they write with `db_update`/`db_set`, which
   skip field checks): birthday hide, document upload.
2. **Every Employee field not on the self-edit list becomes HR-only, including custom
   fields added later.** That is the safe default, but a tenant field that staff were
   meant to fill themselves would need adding to the list. On `test266` the custom
   fields it newly locks are: `alvoraa_hide_birthday`, `documents_summary`,
   `employee_documents`, `health_insurance_no`, `health_insurance_provider`,
   `job_applicant`. None is written by staff through a form.
3. **A manager's Desk form for a report still opens editable, but Save is refused**
   with the "Ask HR" message (review m1). The Desk form asks Frappe for its rights
   without saying "write", and the check answers that "yes". Nothing is saved; the cost
   is one wasted edit. Making the form truly read-only would need a form script.
4. **HR cannot change their own HR-owned fields either** (the ALV-215 own-record rule
   now covers the newly locked ones, e.g. their own notice days). Another HR person
   must. Their own personal details stay editable (D-1).
5. **A person without Employee Self Service still cannot edit even their own record.**
   That is not new: the plain Employee role has no write on Employee at all. Surbhi's
   rule says a manager edits their own record "like anyone else"; for staff without ESS
   (I do not know how many at DTC) that would need the Employee role to get write at level 0. I did
   **not** do it, because it is a role change on every tenant and it would also make the
   Positions page show its "Set manager" column to them (`register.py:464` asks only
   "may this login write Employee?"). Decision D-6.
6. **DTC numbers (count by the coordinator, read-only):** 429 enabled logins hold
   Employee Self Service, 4 of them also HR. 7 of them are managers with reports - they
   are the people who could change a report's record until this ships.

## 1. Who can change what

| Who | Own record: self-edit fields | Own record: everything else | Someone else's record |
|---|---|---|---|
| Staff (Employee Self Service) | Yes | Quietly put back | Refused: "Only HR can change another person's employee record. Ask HR to make this change." |
| Staff without Employee Self Service | No (no write at all, as today) | No | Refused (Frappe's own "no permission") |
| Manager, for a report | as staff | as staff | Refused, unless the field is on `MANAGER_EDITABLE` (empty) |
| HR User / HR Manager / System Manager | Yes | Refused, ALV-215 rule (job, pay, employment dates) | Yes, everything (bank and pay: HR Manager only, as before) |

Also (round 3, after the security review): only HR renames or merges an Employee ID,
and Employee Self Service can no longer share an Employee record, so a manager cannot
open a report's record to anyone by sharing or assigning it.

## 2. The self-edit list (for Surbhi to confirm)

`SELF_EDITABLE`, in `employee_field_rights.py`:

| Field(s) | Why the person may change it |
|---|---|
| `cell_number`, `personal_email` | Their own phone and private email |
| `prefered_contact_email`, `prefered_email` | Which of their addresses mail goes to (the second is filled from the first) |
| `unsubscribed` | Their own mail preference |
| `current_address`, `current_accommodation_type`, `permanent_address`, `permanent_accommodation_type` | Where they live |
| `person_to_be_contacted`, `emergency_phone_number`, `relation` | Their emergency contact - they know it best |
| `passport_number`, `date_of_issue`, `valid_upto`, `place_of_issue` | Their own passport; changes on renewal |
| `marital_status`, `blood_group`, `health_details`, `family_background`, `bio` | Personal facts only they can keep current |
| `image`, `salutation` | Photo and title |
| `education`, `external_work_history` | Their own CV |

**HR-only (deliberately not on the list):** `company_email` (issued by the company),
exit interview (`reason_for_leaving`, `feedback`, `new_workplace`, `held_on`), contract,
confirmation, notice, retirement, resignation and encashment dates, `employee_number`,
`internal_work_history`, `create_user_permission`, plus every job, pay and bank field
already locked by ALV-215.

## 3. Design

Two pieces, both in the existing ALV-215 file `alvoraa_portal/employee_field_rights.py`:

- **Field levels (rule 2).** `lock_fields()` now puts every value field that is not on
  `SELF_EDITABLE` at level 2 (HR writes, everyone reads), instead of a named list. A
  new custom field is locked the same way when it is created. The level-2 permission
  rows already exist. This is the 075 mechanism, unchanged in shape.
- **Someone else's record (rules 1, 3, 4).** One `has_permission` hook on Employee.
  For a write by anyone who is not HR, on a record that is not their own, it compares
  the document with the saved copy. Changes outside `MANAGER_EDITABLE`: refused with
  the message above. No changes (a plain "may this login write it?" check):
  no, unless the list grants something. The Desk form itself still opens editable. Frappe asks this hook **before** it quietly resets locked
  fields, so a change to a report's `reports_to` is refused, not silently undone.
  It returns `True` in every allowed case (Frappe v16 reads anything else as "no").
- **`MANAGER_EDITABLE`** is a constant, empty. Rung: a constant is cheaper than a
  setting and Surbhi asked for "changeable without touching other code". It only works
  for fields on the self-edit list; an HR-owned field would also need a permission row.

**Ladder.** Configuration (Property Setters, through the existing function) plus one
hook. Why not configuration alone:

- A Role Permission row cannot say "not on someone else's record". `if_owner` means
  "the person who created the record", which for an Employee is HR, not the employee.
- **The own-record User Permission with "Hide Descendants" ticked** would stop a
  manager reaching their reports at all - read as well as write. That is a setting, not
  code, but it is untested here and it would very likely break what managers rely on
  reading through that same row: team goals and KPIs, the team pages, approvals that
  look up the report's Employee. ALV-249 chose the tree on purpose (Surbhi's D-2). The
  code rule keeps every read and blocks only writes, so nothing a manager sees changes.

**What the hook skips:** server code that saves with `ignore_permissions`, and
`db_set`/`db_update`/`frappe.db.set_value`. Those never reach it. This is how the
portal's birthday-hide and document-upload endpoints, ERPNext's own Employee hooks and
the ALV-249 sync keep working.

## 4. Impact

**Cross-module.** `alvoraa_portal` only (`employee_field_rights.py`, one line in
`hooks.py`). `hrms`, `erpnext`, `alvoraa_goals`: no change. Callers: `lock_fields` -
`apply()`, `alvoraa_payroll_rule_set.py:58`; `refuse_own_locked_change` - `hooks.py`;
`lock_new_custom_field` - `hooks.py`. The new hook is called only by Frappe.

**Personas.**

| Persona | Change |
|---|---|
| CXO (HR Manager / System Manager) | None |
| HR Manager / HR User | None on others. Own HR-owned fields now need another HR person |
| Employee | Own personal details: still editable. Own HR-owned fields: no longer |
| Manager | Can no longer change anything on a report's record |

**HRMS domains.** Leave, attendance, payroll, appraisals: no change. Employee documents:
upload still works (the endpoint writes the row directly).

## 5. Non-functional verdicts

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | For a non-HR write check: one lookup of the record's login, and one read of the saved record only when it is not their own. HR and reads: nothing |
| Security | improves | Closes manager writes on reports on every save path, with a refusal |
| Reliability | neutral | Server code that skips permissions is untouched |
| Scalability | neutral | Nothing grows with headcount |
| Maintainability | improves slightly | One list says what staff may edit; everything else is HR's |
| Data integrity | improves | Employment data changed only by HR, each change in Version history |
| Compliance / privacy | improves | Personal data changed by its owner or HR only; refusals logged without values |

## 6. Parallel-work check

| File | Hot? | Who else |
|---|---|---|
| `employee_field_rights.py` | no | Nobody on the board; ALV-249 did not touch it |
| `hooks.py` | **hot** | ALV-249 landed changes (`on_login`, `before_request`, two `doc_events`). Mine is one new line at the end of `has_permission`; no overlap |
| `tests/test_employee_field_rights_alv215.py` | shared | Untouched in the end (the one test I had reversed is back as it was) |
| `tests/test_employee_write_fields_alv266.py` | no | New |

Incoming on rebase: 8 ALV-249 commits (5452084c .. 9b99a421) - `hooks.py`,
`own_record_permission.py`, `request_guard.py`, their tests, `test_inbox_counts_034.py`,
`test_portal_security_010.py`, and their slice documents. No conflict.

## Decisions for Surbhi

- **Confirm the self-edit list** in §2 (in particular: `marital_status`, `health_details`
  and `passport` stay self-editable; `company_email` is HR's).
- **Confirm that any future Employee field is HR-only unless added to the list.**
- **`MANAGER_EDITABLE` stays empty?** Recommended: yes, until a tenant asks.
- **D-6. Staff without Employee Self Service: should they edit their own personal
  details?** If yes: one line in `apply()` gives the Employee role write at level 0, and
  `register.py:464` must ask for an HR role instead, so the "Set manager" column does
  not appear for them. Recommended: decide per tenant by giving ESS, as today.
- **D6 (round 3): passport, health, family and blood group hidden from managers.**
  Frappe's field levels go by role, not by whose record it is, so "HR or the person"
  cannot be said with them. Options A, B, C are in 05, round 3.
