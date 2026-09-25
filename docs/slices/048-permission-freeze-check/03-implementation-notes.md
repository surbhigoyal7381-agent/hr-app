# Slice 048 · ALV-127 detection — implementation notes

Local only. Nothing pushed, nothing merged into `dev`, no server, no tenant, no
`docker cp`. Built and tested in its own container `hrlocal-048` on its own site
`test048`; `hrlocal-bench` was never used.

---

## The finding that changed the slice

**The 5 `Custom DocPerm` rows on production's `Attendance Request` are our own install,
not a tenant's administrator.**

A site built from scratch on 2026-09-25 — `bench new-site` plus erpnext, hrms,
alvoraa_goals and alvoraa_portal, never opened by a human — already had:

| Doctype | Custom rows | Standard rows |
|---|---|---|
| `Attendance Request` | **5** | 4 |
| `Attendance` | 5 | 4 |
| `Leave Application` | 9 | 8 |
| `Employee Performance Feedback` | **0** | 4 |

That is production's shape exactly, including the zero. Four of the five rows on
`Attendance Request` were copies carrying their original 2018 creation date; the fifth
was an `Employee Self Service` row created during the install.

The chain, read in the installed source:

```
hrms/setup.py:637   get_user_types_data()    lists Attendance Request, Leave Application …
hrms/setup.py:693   create_user_type()       saves the "Employee Self Service" User Type
frappe/core/doctype/user_type/user_type.py:161   add_permission(doctype, role, 0)
                                             -> setup_custom_perms:686 -> copy_perms:733
```

So **three of the four watched doctypes are born frozen on every site we run.** Nothing
was misconfigured by anyone at `dtc.alvoraa.co`.

This mattered for the design. A check that reports "frozen" on every healthy site is a
check people stop reading, which is how the original fault would have gone unnoticed a
second time. So the check separates *frozen the way every site is* from *frozen because
somebody changed something*.

---

## What was built, file by file

| File | Mechanism | Why |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/permission_health.py` (new) | **build** — a plain module function | Nothing in Frappe reports this. It sits beside `health.py`, which already does the "pull a signal off a tenant" job, and beside `module_access.py`, the one place we write `Custom DocPerm`. |
| `alvoraa_portal/alvoraa_portal/tests/test_permission_health_048.py` (new) | build | 16 tests, each breaking something before asking the check. |
| `hrms/hrms/alvoraa_hr_core/tests/test_attendance_request_access_048.py` (new) | **extend** — reuses slice 047's `FeedbackFixtures047` | The tenant shape already exists there: two stores, HR limited to one, employees under different managers. Building a second one would have been duplication. |
| `docs/runbooks/permission-freeze-check.md` (new) | configure | How to run it and how to read the four states. |
| `DEPLOYMENT_RUNBOOK.md` §8 (edited, one bullet) | configure | Where someone already looks after a deploy. |

**Deliberately not whitelisted.** A report of the permission surface should not gain a
web endpoint because it would be convenient. It runs as
`bench --site <site> execute alvoraa_portal.permission_health.check_permission_freeze`.

**Deliberately not preventive.** A guard would fight the tenant's own Role Permissions
Manager, which is a legitimate Frappe feature used correctly.

### The four states

| Status | Meaning |
|---|---|
| `ok` | No custom rows. Still follows Frappe HR. |
| `frozen_at_install` | Custom rows, but exactly the standard set plus `Employee Self Service`. What every healthy site looks like. |
| `frozen` | A role was granted or lost beyond the install. Nobody has lost read. |
| `broken` | `Employee` or `HR Manager` has no read row at permlevel 0, **or** a watched doctype is not installed. |

An `if_owner` row does not count as the role having read — it is narrower, and counting
it would let a real loss pass as healthy. There is a test for that.

---

## The acceptance list

| What ALV-127 asked for | How it is satisfied |
|---|---|
| A health check listing watched doctypes in custom-permission mode | `check_permission_freeze()`; four states, per-doctype findings |
| Flag where the `Employee` or `HR Manager` row has disappeared | `REQUIRED_ROLES`; status `broken`; `missing_required_roles` names them |
| At least those four doctypes | `WATCHED_DOCTYPES`, pinned by `test_the_four_doctypes_the_ticket_named_are_all_watched` |
| A named constant with a one-line reason per entry | `WATCHED_DOCTYPES` is `{doctype: reason}`; a test asserts every reason is non-empty and longer than a shrug |
| An unknown doctype is an error, not a silent skip | `_examine` returns `broken` with "not installed"; proved by a test that patches in a made-up doctype |
| Read-only and safe against a live tenant | Two `SELECT`s and one `frappe.db.exists` per doctype. `test_the_check_writes_nothing` snapshots every permission row and compares after a run |
| One test: employee reads own Attendance Request, HR in scope reads it | `test_an_ordinary_employee_can_read_their_own_attendance_request`, `test_hr_in_scope_can_read_it` |
| Run against the tenant shape, not a bare site | Both run on `FeedbackFixtures047` — two stores, Branch User Permissions, real reporting lines |
| One line in the runbook | `DEPLOYMENT_RUNBOOK.md` §8, plus `docs/runbooks/permission-freeze-check.md` |
| Prove the check bites | Below |

---

## Proving it bites

Done twice: once by hand outside the test suite, once inside it.

**By hand, on `test048`.** Baseline read and saved: 5 rows on `Attendance Request` —
`Employee`, `Employee Self Service`, `HR Manager`, `HR User`, `System Manager`. Then
`add_permission("Attendance Request", "ALV127 Manual Supervisor", 0)` and the `Employee`
row deleted. The check then said:

```
BROKEN - a role that people need has lost read on a watched doctype.
[BROKEN] Attendance Request (5 custom / 4 standard rows)
    - Employee has NO read row at permlevel 0. People holding that role cannot open
      any Attendance Request record at all.
```

Restored by `reset_perms` plus re-inserting the five captured rows. Verified: 5 rows
back, same five roles, and the check returned to `EXPECTED`.

**Inside the suite**, `test_losing_the_employee_row_really_does_take_the_queue_away`
grants a role the Desk way (access survives — the copy works), then deletes the
`Employee` row and asserts three things at once: `has_permission` goes false,
`get_list` **refuses** (measured — it raises `PermissionError` rather than returning an
empty list), and the health check reports `broken`. Then it restores and asserts the
restore worked in the same test, rather than leaving the next module to discover it.

---

## Test results, real numbers

All in `hrlocal-048` against `test048`, one run at a time.

| Command | Result |
|---|---|
| `bench --site test048 run-tests --module alvoraa_portal.tests.test_permission_health_048` | **16 tests, OK** (22.6 s) |
| `bench --site test048 run-tests --module hrms.alvoraa_hr_core.tests.test_attendance_request_access_048` | **5 tests, OK** (6.1 s) |
| `bench --site test048 run-tests --module hrms.alvoraa_hr_core.tests.test_feedback_access_047` | **27 tests, OK** (6.6 s) — slice 047 unharmed |
| `bench --site test048 run-tests --module hrms.alvoraa_hr_core.tests.test_feedback_history_gate_047` | **4 tests, OK** (3.3 s) |
| `python scripts/check_app_integrity.py` | 635 checks, "OK - all consistent" |
| `python -m ruff check` on all three new files | "All checks passed!" |
| `python -m py_compile` on all three | clean |

Two failures on the way, both real and both fixed:

1. `Attendance Request` will not save without a Holiday List. In this Frappe HR version
   the link is a **submitted `Holiday List Assignment`**, not a `holiday_list` field —
   `hrms/utils/holiday_list.py:119` reads that doctype with `docstatus == 1`. The first
   fix set the old field and changed nothing at all.
2. `get_list` **raises** rather than returning `[]` when the role has no read row. The
   test now asserts the refusal, which is the stronger claim.

### Against a clean site

`EXPECTED` — three doctypes `frozen_at_install`, `Employee Performance Feedback` `ok`,
"Read 4 doctypes, 20 standard permission rows and 19 custom permission rows."

---

## The seven dimensions, against the code actually written

| Dimension | Before → after | One line |
|---|---|---|
| Performance | neutral | Two `SELECT`s plus four `exists` per run, on indexed `parent`. Not on any request path. |
| Security | **improves** | The only thing that notices a required role losing read. Grants nothing, no endpoint, no whitelist. |
| Reliability | **improves** | Raises rather than reporting OK on an empty read. Every teardown restores the install's own rows. |
| Scalability | neutral | Cost fixed by the length of the watched list, not by headcount or months. |
| Maintainability | **improves** | One constant with a written reason each; an unknown doctype is an error; the install's contribution is named with file and line so the next Frappe HR change to it is visible. |
| Data integrity | neutral | Reads only, proved by `test_the_check_writes_nothing`. |
| Compliance / privacy | **improves** | Reads role names and permission flags only — no employee record, name or identifier — so neither the report nor a log line can carry personal data. Makes an access-rights control observable. |

## NFR notes

- **Query count:** 2 list queries + 4 `frappe.db.exists` per run. Fixed, not per-employee.
- **Indexes:** none added. `Custom DocPerm.parent` and `DocPerm.parent` are already indexed.
- **Background jobs:** none.
- **Permission enforcement:** the check enforces nothing; it observes. It uses
  `frappe.get_all`, which ignores permissions, and is only reachable from a bench shell.
- **Sensitive fields touched:** none. Role names and permission flags only.
- **Fallback:** none needed — it is read-only and has no external call.

## What else moved while I worked

`git fetch origin` at the start brought five commits into `origin/dev`, all slice 047
(ALV-117): `79b53d1`, `8b27274`, `ccff073`, `2b190dc`, `42f89c4`. Files:
`hrms/hrms/alvoraa_hr_core/feedback_access.py`, `hrms/hrms/hooks.py`,
`hrms/hrms/hr/doctype/appraisal/appraisal.py`, two 047 test files, 047 docs. This branch
starts at `42f89c4`. **No overlap with anything changed here, so no conflict arose and
nothing had to be proved surviving.** The 047 suites were run anyway (27 + 4, both OK)
because this slice reuses their fixture.

Other sessions' uncommitted work in the main checkout (`ux-learnings.md`, the
`mobile/field-app/` tree, `docs/sargam_metals/`, the 013 step-6 notes) was not touched —
all work was done in this worktree. `hrlocal-bench` was not used; slices 042 and 045 have
their own containers running and were not disturbed.

---

## Known gaps and shortcuts

- **The freeze is reported, not fixed** — *intentional trade-off*. Un-freezing means
  deleting a tenant's own permission rows; that is a decision about their configuration,
  not one a health check should take.
- **Three doctypes are frozen on every site and nothing re-applies upstream changes** —
  *dangerous debt, escalating it here rather than noting it.* Frappe HR's own installer
  guarantees that a future upstream permission fix to `Attendance Request`, `Attendance`
  or `Leave Application` will never reach any site we run, including production. This
  check makes it visible; it does not close it. Closing it needs a decision: either a
  migrate-time reconciliation of custom rows against standard, or a documented manual
  review on each Frappe HR upgrade. **That is an architecture decision and it is the
  user's to take.**
- **The check is manual** — *acceptable simplification*. It is a `bench execute`, not a
  scheduled job feeding the control plane. `health.py` already has the pattern for
  pulling a tenant signal up daily; wiring this into it is the obvious next step and was
  not in scope.
- **`WATCHED_DOCTYPES` is four entries** — *acceptable simplification*. Those are what
  the ticket named. `Expense Claim`, `Employee Advance`, `Shift Request` and
  `Timesheet` are all on Frappe HR's ESS list too and are therefore frozen as well;
  adding them is cheap, and the constant says so.
- **Only permlevel 0 is examined** — *intentional trade-off*. Higher permlevels guard
  individual fields, which is a different question from "can this person open the record
  at all". A field-level freeze would not be caught.
- **Not tested on a tenant with real data volume** — *acceptable simplification*. The
  cost does not vary with data; it varies with the length of the watched list.
