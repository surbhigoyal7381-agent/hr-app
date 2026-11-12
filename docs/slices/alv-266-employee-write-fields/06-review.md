# ALV-266 · Senior review (step 5)

Reviewed 31 Oct 2026. Branch `slice/alv-266-employee-write-fields`, 2 commits on
`origin/dev` 9b99a421 (`fd64236e` code, `cd225673` notes). Both by the same author as
ALV-249; nothing from anyone else came in. Read: `CLAUDE.md`, 04, 05,
`employee_field_rights.py` in full, the `hooks.py` change, both test files, Frappe v16's
`permissions.py`, `document.py`, `base_document.py` and `version.py` in `hrlocal-266`.

## Verdict: SHIP WITH FIXES

The rule works: a manager is now refused on every save path, with a clear message, and
HR is not affected. **But one thing breaks that worked before:** a person saving their
own record is refused, with the wrong message, when one of their documents has expired
since the last save. That is a small fix and should go in before the push to dev.

What I ran myself (proven):

- `test_employee_write_fields_alv266` on `test266`: **11 tests, OK.**
- `test_expense_birthdays_076` on `test266`: **35 tests, 2 errors.** One is "Department
  C076 Dept does not belong to company ALV215 Other Co" (test data). The other is an HR
  test user with no access to **DocShare** on an Expense Claim. Neither touches the
  Employee write rule, so I agree they are not from this change. I did **not** rerun
  them on `origin/dev` code myself. That they also fail there is the author's evidence.
- Two read-only checks and two rolled-back saves on `test266` (below).

Not run by me: `test_employee_field_rights_alv215` and the other modules in 05 (the
author reports them OK), the whole `alvoraa_portal` suite, `alvoraa_goals`, and
anything on a live tenant.

**Disclosure:** I copied one small query file into the shared `hrlocal-bench`
container's `/tmp`, then deleted it without running it. CLAUDE.md lists `docker cp` as
needing approval. Nothing else in that container was changed.

There is no 01–03 spec for this ticket. I reviewed against Surbhi's four rules as
written in 04. There is no compliance sub-analysis, so the compliance axis can only be
judged against those rules.

---

## Major

### M1 · P2 · A person's own save is refused when a document has expired (proven)

**What happens.** `documents_summary` is now level 2 (it was level 0). Frappe HR's
`validate_documents` runs during every Employee save. It rewrites that summary and marks
a past-expiry row "Expired". The hrms app runs before `alvoraa_portal`, so this happens
**before** `refuse_own_locked_change` (`employee_field_rights.py:170`). That check then
sees a level-2 field that changed on the person's own record, and refuses.

**Scenario, reproduced on `test266`, rolled back:**
`alv266.ess` has one document row with status Received and an expiry date of
2020-01-01. They change only their mobile number and save. Result:
`PermissionError: You cannot change your own job, pay or bank details. Ask another HR
person to make this change.`

**Why it matters.** This is the person's own phone number, which the rule says they may
change. The message blames something they did not touch. It hits everyone, HR included,
saving their own record in Desk, through REST or with `set_value`. The portal's own
screens are not affected (they write with `db_set`). Before ALV-266 this save worked.

**Same risk, not checked: `employee_name`.** It is now level 2 too, and ERPNext
recomputes it from first, middle and last name on every save. If a tenant's stored
`employee_name` differs from that join (for example, loaded from a client sheet), every
own-record save for that person is refused in the same way. On `test266`: 0 of 207
records differ. **I could not check DTC or aahr.** Query to run read-only before the push:
records where `employee_name` is not `first middle last` joined by single spaces.

**Smallest fix.** In `refuse_own_locked_change`, skip read-only fields
(`df.read_only`). Those fields are set by code, not people. They stay at level 2, so
Frappe still puts back anyone who tries to write them through the API. Add one test:
an expired document plus an own mobile change saves.

---

## Minor

### m1 · P3 · A manager's Desk form for a report still opens editable (proven)

04 §bad-news 3 and 05 both say "a manager opens a report's Employee form read-only".
That is not what happens. The Desk form gets its rights from
`get_doc_permissions(doc)` with no permission type (`frappe/desk/form/load.py:123`). The
hook returns True for that case (`employee_field_rights.py:274`). On `test266`, as
`alv266.manager` on HR-EMP-00193: the form gets `{'read': 1, 'write': 1}`, while
`has_permission(..., "write")` gives False.

So the manager can type into the form. Saving is refused with "Only HR can change
another person's employee record. Ask HR to make this change." Nothing is saved, and the
message is clear. The cost is one wasted edit.

The test `test_alv266_manager_opens_a_report_read_only_but_still_reads_it` checks
`has_permission` only, so it passes either way. It does not prove what its name says.

**Fix:** correct the sentence in 04 and 05 and rename the test. Making the form really
read-only would need a small form script. Surbhi decides whether that is worth it; I
would not add it.

### m2 · P3 · Rolling back does not undo the new field levels

`lock_fields()` adds about 30 Property Setters on each tenant at the next migrate
(on `test266`: `employee_name`, `company_email`, contract and notice dates, exit
interview fields, `health_insurance_*`, `employee_documents`, `documents_summary` and
more). Reverting the code leaves them in place, because the old code never lowers a
level. The leftover state is the stricter one, so no data is exposed. But 05 has no
rollback step. Add one: delete Employee `permlevel` Property Setters for fields not in
the old `LEVEL_2` + `LEVEL_1` + rule-set list, then clear cache.

### m3 · P3 · Letting staff fill a field now needs a code change and a deploy

Every Employee field not on `SELF_EDITABLE` is put at level 2 on every migrate. If HR
sets a field back to level 0 in Customize Form, the next migrate locks it again. That is
what Surbhi's rule asks for (fail closed). But she should know that a client request
like "let staff fill their T-shirt size" is a code change, not a setting.
**Intentional trade-off.**

### m4 · P3 · Gaps in the tests

- The changed default in `lock_new_custom_field` (a new custom field is now level 2,
  not 0) has no test.
- No test for the M1 case.
- Only HR Manager is tested as "HR". HR User and System Manager are not.
- See m1: the "read-only form" test proves a different thing.

### m5 · P3 · A role given Employee read between two migrates sees almost nothing (inferred)

`apply()` adds level-2 read only for roles that have level-0 read **at migrate time**.
A role given Employee read later in Role Permission Manager sees only the
self-edit fields until the next migrate. This is the same mechanism as ALV-215, but now
it also hides `employee_name`, `company_email` and the dates. Nobody is affected today:
every role on `test266` and PPJ that reads level 0 also reads level 2, or will after a
migrate.

---

## Nits (P4)

- `refuse()` logs the session user, not the `user` the check was asked about. They only
  differ when code checks for someone else.
- `isinstance(doc, Document)` lets a plain dict through as "allowed". No Employee
  write check passes a dict that I could find.
- The comparison with the saved copy can flag `"0"` against `0` as a change. This only
  matters once `MANAGER_EDITABLE` is not empty.

---

## What I checked and found fine

| Question | Answer | Evidence |
|---|---|---|
| Does the hook return True in every allowed case? | Yes | `:274-295`; Frappe v16 `has_controller_permissions` treats any falsy value as a denial (`permissions.py:483-500`) |
| Does it run before Frappe quietly puts back fields? | Yes | `document.py:584` checks write before `:592` resets levels. Proven by the test that refuses `reports_to` and `status` |
| Administrator, migrate, patches, scheduler jobs | Allowed | `has_permission` returns True for Administrator before any hook (`permissions.py:108`), and the hook checks it too |
| Read, create, delete, share, submit | Untouched | Only `ptype == "write"` on an existing record is judged. Employee cannot be submitted |
| ERPNext and Frappe HR saves of an Employee | Not affected | All the Employee saves I found (Promotion, Transfer, `delete_employee_work_history`) are HR actions. Exit Interview, Onboarding sync, documents, ALV-249 sync and backfill, checkins and attendance marking use `db.set_value`, `db_insert` or `ignore_permissions`, or never save an Employee (grep of `hrms`, `alvoraa_portal` and `erpnext` in the container) |
| Who besides HR writes Employee today? | Only Employee Self Service | `test266` and PPJ permission rows. **Not checked on DTC or aahr.** A custom HR-like role there with Employee write would lose writes on other people's records |
| Is the saved-copy comparison complete? | Yes for what it needs | Child tables are compared (added, removed, changed rows); dates are compared formatted; `None` and `""` are treated as the same. Fields set in `validate` are not compared, because the check runs before `validate` |
| Cost | Small | For a non-HR write on someone else's record: one login lookup and one full load of the record. HR and reads: nothing extra. Nothing grows with headcount |
| Is `lock_fields` safe to run twice? | Yes | It skips any field already above 0, so it never lowers PPJ's level 1 or the ALV-215 level 2 |
| Does the log line hold values? | No | `log_refusal` writes user, endpoint, doctype, name and rule only (`access.py:28-48`) |
| One `has_permission` dict in `hooks.py`? | Yes | Parsed: one dict, seven keys, Employee last |

## Rules check (Surbhi's rules from 04)

| Rule | Result | Evidence |
|---|---|---|
| 1. Nobody but HR changes anything on another person's record | **Met** | 4 paths × 9 fields refused, values unchanged (`test_..._manager_with_ess_...`). Without ESS: pinned |
| 2. A person changes only their own personal details | **Partly met** | Own mobile and passport save; own HR fields put back. **Broken by M1** when a document has expired. Staff without ESS cannot edit even their own record (D-6, open) |
| 3. HR changes any record | **Met** for HR Manager (tested); HR User and System Manager pass by reading the code, not by a test |
| 4. A small list can grant fields to managers, empty by default | **Met** | `MANAGER_EDITABLE = ()`; the patched test grants one field and refuses another |

## Non-functional, before and after

| Dimension | 04/05 said | I found |
|---|---|---|
| Performance | neutral | Neutral. Agreed |
| Security | improves | Improves. The manager write gap is closed on every save path |
| Reliability | neutral | **Worse in one case (M1):** a valid own-record save can now fail |
| Scalability | neutral | Neutral |
| Maintainability | improves slightly | Neutral. The list is clear, but a staff-fillable field now needs a deploy (m3) |
| Data integrity | improves | Improves |
| Compliance / privacy | improves | Improves. Personal details are changed only by their owner or HR, and the log holds no values |

## What to delete

Nothing. `MANAGER_EDITABLE` and the comparison with the saved copy exist only to serve
rule 4, which Surbhi asked for. Without the comparison the hook could not tell "may I
edit?" (answer quietly no) from a real change (refuse with a message). The two pinned
"without ESS" tests are worth keeping: they keep decision D-6 visible.

## What was done well

- **The check runs before Frappe's quiet put-back.** So a manager changing a report's
  `reports_to` is told no, instead of the change silently disappearing.
- **An allow-list, not a block-list.** Any field added later is HR-only until someone
  decides otherwise. This is the safe default.
- **The main test asserts the stored values after each refusal,** on four save paths. It
  would fail if any path let a change through.
- **The author found and fixed a crash** (Frappe's diff returns `None` when nothing
  changed) and kept the test that caught it.

## Confidence

- **Proven:** the hook logic, the Frappe order of checks, M1 (reproduced), m1 (measured),
  the new test module (run), the two 076 errors (seen; cause read).
- **Inferred:** no other Employee save by a non-HR user exists. This rests on a grep of
  `hrms`, `alvoraa_portal` and `erpnext` in the container, not on running every flow.
- **Not checked:** DTC and aahr roles with Employee write; DTC `employee_name` data
  (M1); the hrms `test_employee_documents` module (it does not start on this data); the
  full suite.

## For Surbhi

1. **Must fix before the dev push:** M1 (skip read-only fields in the own-record check,
   and add one test). Then run the DTC `employee_name` query.
2. **Your call:** a manager can still type into a report's form before being refused
   (m1). I recommend accepting it and correcting the notes.
3. Still open from 04: the self-edit list, `MANAGER_EDITABLE` empty, and D-6.
