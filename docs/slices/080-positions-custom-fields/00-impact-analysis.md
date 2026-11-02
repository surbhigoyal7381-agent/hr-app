# Slice 080 — "Alternative number" on Employee

Strategy approved by Surbhi, 2 November 2026. This file records the impact
check and the one place where the approved mechanism does not work.

## What she decided

| Thing | Her decision |
|---|---|
| Field | A new field on `Employee`, labelled exactly **Alternative number** |
| Help text | "A number colleagues may use to reach this person. Everyone in the company can see it." |
| Who fills it | HR. The employee cannot. |
| Positions page | Tickable, shipping **off** |
| Staff directory | Beside work email |

Out of scope, and not stubbed: letting an Administrator tick arbitrary custom
fields onto these pages.

## Rung on the cost ladder

**Rung 3, customisation — a Custom Field, created by the app's existing
`after_migrate` / `after_install` field-creation pattern.**

* Rung 1 (already there) rejected: ERPNext's `Employee` has 109 fields and none
  of them is a work or alternative number. Verified in
  `apps/erpnext/erpnext/setup/doctype/employee/employee.json` on the bench:
  the only phone fields are `cell_number` (label "Mobile", personal) and
  `emergency_phone_number` (somebody else's number). `people_fields.py:40-42`
  and `staff_api.py:69-74` already said so.
* Rung 2 (configuration) rejected: a Custom Field added by hand per site is
  exactly what we must not do — the field has to exist on every tenant,
  including a fresh one, or the Positions tick and the directory column read a
  column that is not there.
* Rung 4 (new code) rejected beyond the 30-line field-definition module: the
  reader, the setter and the tick dialog are all generic already.
* Rung 5 (new DocType) and rung 6 (new app) are not in question.

## Where the approved strategy is wrong, and what I did instead

**The approved strategy says "an idempotent patch in `patches/v1_0/` registered
in `patches.txt`". A patch cannot do this job.** Frappe marks every patch as
already done on a fresh install, so the patch would never run on a new tenant
and the field would not exist there. `employee_field_rights.py:17-21` records
this exact lesson in its own docstring ("A patch never runs on a new install …
so new tenants would ship open").

The mechanism that does work is already in this app, used by
`payroll_fields.py`, `branch_scope.py`, `attendance_correction.py` and five
others: one module with the field definition and an `after_migrate()`, wired
into **both** `after_migrate` and `after_install` in `hooks.py`.
`create_custom_fields` is idempotent, so it is safe on every run.

**So there is no patch in this slice.** Adding one as well would be a third
path to the same field that does nothing the hooks do not already do. This is a
mechanism change, not a change to anything Surbhi decided. Flagged for her.

## The fieldname

`alvoraa_alternative_number`.

* The `alvoraa_` prefix is this app's convention for every custom field it
  creates (`alvoraa_branch`, `alvoraa_held`, `alvoraa_photo_48`), and it
  guarantees no collision with anything Frappe, ERPNext, Frappe HR or the India
  regional pack creates.
* Checked, not assumed: `grep` for `alternative`/`alternate` across
  `erpnext/setup/doctype/employee`, `hrms/regional` and `india_compliance`
  returns nothing, and the whole repository has no such name either.

## The permission level: 2, not 1

Read from `employee_field_rights.py`, not from the names.

* **Level 1** = bank, statutory IDs, salary. `apply()` gives level 1 to
  **HR Manager only**, read *and* write, and deletes every other role's level-1
  row. A level-1 field is **invisible to colleagues** — which would break
  "everyone in the company can see it".
* **Level 2** = job, pay settings, approvers, identity. `apply()` gives **read
  at level 2 to every role that already reads `Employee`**, and **write only to
  HR User, HR Manager and System Manager**. That is exactly "HR fills it in,
  the employee cannot, everyone can see it".

So the fieldname goes on `LEVEL_2`. Without that one line,
`lock_new_custom_field` (`employee_field_rights.py:217-230`) assigns level 0 —
readable by all and **writable by the employee** — which is the wrong half of
her decision.

Both paths are covered and both are tested:

| Path | Mechanism |
|---|---|
| Fresh install, and every migrate | `lock_fields()` inside `apply()` |
| Custom Field inserted at run time | `lock_new_custom_field` `after_insert` hook |

## Functional impact

**Cross-module.** `hrms` (`people_fields.POSITIONS_PROFILE_FIELDS`) and
`alvoraa_portal` (`employee_field_rights`, `staff_api`, the two JS bundles).
Nothing in `alvoraa_goals`, `erpnext` or upstream `hrms` is touched.

**Grep of every caller of everything changed:**

| Changed | Callers |
|---|---|
| `POSITIONS_PROFILE_FIELDS` | `LIST_KEYS` then `allowed()`/`off_list()`; `people_settings.get_people_settings` (`profile_choices`); `settings.py` setter; 4 test modules |
| `staff_api.ROW_FIELDS` / `ROW_KEYS` | `get_staff_list` only, plus 3 test modules |
| `employee_field_rights.LEVEL_2` | `lock_fields()`, `lock_new_custom_field`, `apply()`, `test_employee_field_rights_alv215` |
| `MPF_FIELDS` (portal.js) | the profile drawer and `ocsWord()` — the settings tick list reads the same list on purpose |
| `personRow` (next-frame.js) | the directory list only |

`positions_profile.get_positions_profile` needs no change: it reads
`ticked_fields()` and the new name is not a link field, so it is not in
`LINKED`.

**Personas.**

| Persona | Before | After |
|---|---|---|
| CXO | — | Can read it on every company; cannot write it unless they hold HR User / HR Manager / System Manager |
| HR Manager | — | Fills it in, for people in their scope. Cannot change it **on their own record** — `refuse_own_locked_change` already covers every high-permlevel field, so this one is covered without a new rule |
| Employee | — | Reads a colleague's, if the tenant ticks it (Positions) or has the directory on. **Cannot write their own** — level 2 refuses it, and `MY_PROFILE_WRITE_FIELDS` is untouched |

**HRMS domain.** None. No leave, attendance, payroll, appraisal or org-structure
behaviour reads this field. It is not on any pay rule set's `*_field` setting,
so `rule_set_fields()` does not pick it up.

**What deliberately does NOT change in `people_fields.py`:**
`MY_PROFILE_WRITE_FIELDS`, the three joiner keys (079 AC-104 binds them to My
Profile by identity, so widening My Profile would reach the pre-onboarding form
for free) and `NEVER`. Asserted as a test, because it is the regression that
would matter.

## Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | One more column on two queries that already select 6 and 10 columns. No new query, no new round trip. The directory still runs two queries whatever the tenant size |
| Security | neutral | The limit lives in Frappe's own field-permission layer (permlevel 2, Property Setter), not in portal code. No `ignore_permissions`, no new whitelisted endpoint, no raw SQL, so the bypass count in `test_portal_security_010` does not move |
| Reliability | neutral | `create_custom_fields` is idempotent and guarded on the DocType existing. A missing value renders as nothing, on both surfaces |
| Scalability | neutral | No per-person read added. Both surfaces batch as before |
| Maintainability | neutral | One 30-line module in the house pattern; two stale comments corrected so the next reader is not told the decision is still open |
| Data integrity | neutral | New nullable column. No migration of existing data, nothing to backfill |
| Compliance / privacy | **widens visibility, on purpose, inside the rule already set** | This is a new personal value shown to colleagues. It is allowed because Surbhi's decision of 24 Sep 2026 (`staff_api.py:66-68`) put **work contact** in the directory, and a number the company hands out is the same class. It ships **off** on Positions. It is **not** added to `NEVER` (it is meant to be visible) and **not** added to `MY_PROFILE_WRITE_FIELDS` (the employee does not own it) |

### Data doors run

The field is a field, not a record, so the doors that matter are the field ones.

| Door | Result |
|---|---|
| `/api/resource/Employee` GET / list | Readable by any role that reads Employee — intended |
| `/api/resource/Employee` PUT as plain staff | **Refused at level 2.** Frappe puts the old value back; proved by test |
| `frappe.client.set_value` as plain staff | Same level check, same refusal |
| Report view / CSV export | Readable, writable only by HR — the same level check |
| Data Import with this column, as HR User | Allowed (HR User writes level 2) — correct, and `refuse_import_of_locked_columns` already names any column they may not write |
| Own record, as HR | `refuse_own_locked_change` refuses it, with no new code |
| `get_employee_field_property` | Level checked already |
| Positions profile endpoint | Intersected twice — allow-list at the setter and again at the reader |
| Staff directory endpoint | Tenant switch, then scope, then caps — all unchanged |

**Bypasses added: zero.**

## Help text — where it actually fits

Her wording goes in the Custom Field's `description`, which Frappe renders as
help text under the input on the Employee form — the screen HR types into, which
is the only screen where anybody fills it in, and the right moment to be told
"everyone in the company can see it".

**It does not fit the Positions tick dialog.** That dialog's rows are a bold
label with a hint slot that only exists on a "must fill in" row
(`portal.js:7434-7447`); a Positions row has no hint. Adding one would be a new
mechanism for one sentence, so I have not. Flagged for Surbhi.

## Parallel-work check

| File | Who else | Plan |
|---|---|---|
| `hrms/alvoraa_org_structure/people_fields.py` | 078/079 landed on dev today (`b202a37d`); nobody else open in it | Branched from `origin/dev` at `b202a37d`; fetch again before commit |
| `alvoraa_portal/employee_field_rights.py` | hot file (ALV-215) | One line added to `LEVEL_2`, nothing reordered |
| `alvoraa_portal/hooks.py` | hot file | Two lines appended at the documented points |
| `alvoraa_portal/staff_api.py` | shared API file | Two tuples, one stale comment |
| `public/js/ess/portal.js`, `next-frame.js` | large shared bundles | One line each, no reflow |
| The five test modules with exact-tuple pins | — | Updated in place, kept as exact equality |

Worktree `.claude/worktrees/080-alt-number`, branch `slice/080-alt-number`, off
`origin/dev`. The shared checkout is not touched.
