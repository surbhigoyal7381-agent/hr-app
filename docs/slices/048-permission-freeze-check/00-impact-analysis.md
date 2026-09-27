# Slice 048 · Permission freeze detection (ALV-127) — impact analysis and strategy

**In one line:** a doctype whose permissions have been customised stops tracking Frappe
HR for ever, and nothing tells anyone. This slice adds a read-only check that says so, a
test on the tenant shape that proves the access it protects, and one line in the runbook.

**Not in scope, deliberately:** any preventive guard. Blocking the Role Permissions
Manager means fighting the tenant's own administration screen, which is a legitimate
Frappe feature used correctly. Detection is the right trade, and it is what ALV-127's
correcting comment asks for.

---

## 1. What is actually true (verified, not remembered)

Read in the installed Frappe **16.33.1** (`frappe/permissions.py`, read from the bench
image in a throwaway `docker run --rm`):

| Line | Fact |
|---|---|
| `get_doctypes_with_custom_docperms:586` | any `Custom DocPerm` row puts the whole doctype into custom mode |
| `add_permission:693` → `setup_custom_perms:686` → `copy_perms:733` | the Desk's grant **copies every standard row in first** |
| `reset_perms:741` | "Reset to default" **deletes every custom row** |

So ALV-127's original description was wrong: the Desk route does **not** strip anyone.
The three real risks are the freeze (silent, permanent), the delete (silent, immediate),
and a lone `Custom DocPerm` written by code (silent, total).

Live, read-only on production 2026-09-25: `dtc.alvoraa.co` has **5 custom rows on
`Attendance Request`** — already frozen. `Employee Performance Feedback` has 0.

## 2. Functional impact

**Cross-module.** Nothing is changed in any existing module. The new file only reads
`Custom DocPerm` and `DocPerm`. `alvoraa_portal/module_access.py` is the one place that
writes `Custom DocPerm`; it is **read but not edited**, so its `_keep_exempt_row` guard is
untouched. `hrms`, `erpnext`, `alvoraa_goals` are unchanged.

**Callers.** No existing function's signature changes, so there is nothing to grep for.
The new entry points are `check_permission_freeze` and module-private helpers, called by
the new tests and by `bench execute`. Deliberately **not whitelisted**: a report of the
permission surface is exactly the kind of thing that should not gain a web endpoint just
because it would be convenient.

**Personas.**

| Persona | What changes |
|---|---|
| CXO | Nothing in the product. An operator can now tell them whether their tenant's permissions still track upstream. |
| HR Manager | Nothing in the product. If their queue ever empties, the check names the cause in one command instead of a day of guessing. |
| Employee | Nothing at all. No screen, no field, no new data. |

**HRMS domain.** Attendance corrections, leave, attendance and feedback are the four
watched doctypes, chosen because the portal cannot work without them.

## 3. Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | Two queries in total (`Custom DocPerm`, `DocPerm`), both `parent in (...)` over a four-name list, both on an indexed column. Not on any request path — it is a `bench execute`. |
| Security | **improves** | It is the only thing that notices a role losing read on a doctype the portal depends on. It grants nothing, widens nothing, and has no endpoint. |
| Reliability | improves | Refuses to report health when it read nothing, rather than printing a reassuring OK. |
| Scalability | neutral | Cost is fixed by the length of the watched list, not by headcount, months or transactions. |
| Maintainability | improves | One named constant with a written reason per entry; an unknown doctype is an error, not a silent skip. |
| Data integrity | neutral | Reads only. A test asserts every permission row is byte-for-byte identical after a run. |
| Compliance / privacy | improves | Reads role names and permission flags only — no employee record, no name, no identifier — so neither its output nor its log line can carry personal data. It makes an access-rights control observable, which the baseline asks for. |

## 4. Parallel-work check

**Files I will change**

| File | New or edited | Hot file? |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/permission_health.py` | new | no |
| `alvoraa_portal/alvoraa_portal/tests/test_permission_health_048.py` | new | no |
| `hrms/hrms/alvoraa_hr_core/tests/test_attendance_request_access_048.py` | new | no |
| `docs/runbooks/permission-freeze-check.md` | new | no |
| `DEPLOYMENT_RUNBOOK.md` | **edited** — one bullet appended to §8 | shared, but append-only |
| `docs/slices/048-permission-freeze-check/` | new | no |

`module_access.py` and `health.py` are **read only** — neither is edited, so the hot-file
rule for `module_access.py` does not bite.

**Who else is in them.** `git fetch origin` at the start brought in five commits, all
slice 047 (ALV-117): `79b53d1`, `8b27274`, `ccff073`, `2b190dc`, `42f89c4`, touching
`hrms/hrms/alvoraa_hr_core/feedback_access.py`, `hrms/hrms/hooks.py`,
`hrms/hrms/hr/doctype/appraisal/appraisal.py`, two 047 test files and the 047 docs.
`origin/dev` is now at `42f89c4`; this branch starts there. **No overlap with any file
above.** The work board shows no other slice in `permission_health.py`,
`DEPLOYMENT_RUNBOOK.md` or the `alvoraa_hr_core` tests folder. No other developer was
reported in these files.

**The plan where there is overlap.** The only shared file is `DEPLOYMENT_RUNBOOK.md`, and
the change is a single appended bullet in §8 — sequence and split are both unnecessary;
a conflict there resolves by keeping both bullets.

**Pins.** `test_the_four_doctypes_the_ticket_named_are_all_watched` fails CI if a merge
drops one of the four from the list.
`test_an_ordinary_employee_can_read_their_own_attendance_request` and
`test_hr_in_scope_can_read_it` fail if the access itself is ever taken away.

## 5. Strategy

Three pieces, exactly as ALV-127's correcting comment specifies.

1. **`alvoraa_portal/alvoraa_portal/permission_health.py`** — `check_permission_freeze()`.
   Read-only. Named constant `WATCHED_DOCTYPES` with a one-line reason per entry;
   `REQUIRED_ROLES = ("Employee", "HR Manager")`. Status per doctype: `ok` (standard
   rows still in force), `frozen` (custom rows exist, nobody has lost read), `broken` (a
   required role has no read row at permlevel 0, or the doctype is not installed). An
   `if_owner` row does not count as read, because it is narrower than the role having
   read and counting it would let a real loss pass as healthy. It prints what it read
   and raises if that is nothing.

2. **Tests.** `test_permission_health_048.py` breaks the doctype and watches the check go
   red, for each of the three routes. `test_attendance_request_access_048.py` runs on
   slice 047's tenant fixture — two stores, HR limited to one of them — and asserts an
   ordinary employee reads their own correction and HR in scope reads it, then breaks it
   once to prove those assertions can fail.

3. **The runbook line** — in `DEPLOYMENT_RUNBOOK.md` §8 and its own short runbook at
   `docs/runbooks/permission-freeze-check.md`.

**Risk, and what is done about it.** A test that puts a doctype into custom mode can
strip roles for the rest of the run. Every break goes in through `add_permission` (which
copies first) and comes out through `reset_perms`, and the **doctype** cache is cleared
each time — the exact line whose absence cost a day on ALV-117.

**Trade-off accepted.** The freeze is reported, not fixed. Un-freezing a doctype means
deleting a tenant's own permission rows, which is a decision about their configuration,
not ours to take from a health check.
