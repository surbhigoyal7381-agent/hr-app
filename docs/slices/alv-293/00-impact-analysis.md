# ALV-293 — impact analysis and strategy

**A User Permission row restricts; it never grants.** `manager_scope.py` writes narrow
rows for any line manager, with no role check. A person who is both a line manager and
an HR Manager therefore gets rows that cap their HR-wide sight at their own direct
reports. Measured on production 3 Nov 2026: `HR-EMP-00413` (HR Manager + HR User) sees
796 of 18,903 Attendance rows — 4%.

Direction approved by Surbhi 3 Nov 2026: a person who is both keeps full HR sight.
Skipping the row costs them nothing, because HR already sees everyone.

**The analysis did not change the approved direction.** It is the right shape.

---

## 1. The cost ladder

| Rung | Verdict |
|---|---|
| 1. Already there | No. Frappe has no "never restrict this role" setting. |
| 2. Configuration | No. The rows are written by our code on every Employee save; no setting stops that. |
| 3. Customisation | No. A Server Script cannot stop a Python hook writing a row. |
| **4. New code** | **Yes — a role check at the one write seam, reusing the list that already exists.** |
| 5. New DocType | No. |
| 6. New app | No. |

Rung 4, three lines of behaviour and one import. No new list, no new setting, no flag.

## 2. The seam — `grant()`, not only `sync_for_manager()`

The ticket suggests `sync_for_manager`. That is not enough. Two call paths write rows:

| Path | Calls |
|---|---|
| `after_migrate` → `sync_for_manager` → `grant` | every deploy |
| `on_employee_update` (Employee `on_update` hook) → **`grant` directly** | every reporting-line or status change |

Guarding only `sync_for_manager` would leave the second path open: a reporting-line save
would still write a row for an HR Manager. **The guard goes in `grant()`** — the single
function every write passes through. One check, both paths.

`sync_for_manager` additionally gets the removal (section 4).

## 3. One source of truth for the role list

`own_record_permission.excluded_roles()` is reused. No second list.

**No import cycle.** `own_record_permission` imports only `hashlib`, `json`, `os`,
`frappe` and `frappe.utils`. It does not import `manager_scope`. Verified by reading the
file. The import form is `from alvoraa_portal.own_record_permission import excluded_roles`
— `from package.module import name`, which is the form CI accepts; the banned form is
`from package import submodule`.

**What the list is only as good as.** `excluded_roles()` is computed from the roles that
hold a read row on `Employee` in *this site's* permissions, plus System Manager and
Administrator by name. On a site where HR Manager has no read row on Employee, HR Manager
would not be excluded. That is `own_record_permission`'s existing shape and the reason the
ticket asks for one list rather than two. On DTC, HR Manager does read Employee.

## 4. Point 2 — what happens to rows that already exist

**Recommendation: the fixed sync removes them.** `sync_for_manager` computes `should` as
the empty set for a user who holds an excluded role, so every row this module ever wrote
for them lands in `have - should` and goes out through the existing `revoke()` path.

| Option | What it costs |
|---|---|
| **Remove (recommended)** | DTC's 84 rows clear on the next `bench migrate`, with no one-off script. `HR-EMP-00413` goes back to seeing all 18,903 Attendance rows. The ticket's measured fault is actually fixed, not just prevented for the next person. |
| Stop adding only | The code is correct from here on, but `HR-EMP-00413` still sees 4% of attendance until somebody runs a separate clean-up. A fix that leaves the reported case broken is the wrong shape. |

**Two consequences to say out loud.**

1. `revoke()` deletes rows by `(user, for_value, applicable_for in SCOPED_DOCTYPES)`. It
   cannot tell our row from a narrow row somebody made by hand on one of those four
   doctypes. So if any of the **43 stray self-rows on `HR-EMP-00412`** happen to be
   Attendance, Employee Checkin, Attendance Request or Leave Application, the sync will
   remove those too. Removing a restricting row only widens HR's own access, which is
   exactly the approved decision — but it means this change touches up to 4 rows it did
   not write. The other ~39, and the five Location Managers' rows, are untouched: their
   holders do not hold an excluded role, or the rows are on other doctypes.
2. Removal fires on `after_migrate`, which runs on every deploy. It is not instant. **A
   line manager promoted to HR Manager keeps their narrow rows until the next deploy**,
   because there is no `manager_scope` hook on User. Adding one would be a hook on a
   shared doctype for a case the ticket did not raise — written down, not built.

To drop to "stop adding only", revert one line in `sync_for_manager`.

## 5. Functional impact

**Cross-module reach.** Grepped every mention of `manager_scope` in the repo:

| Caller | Effect |
|---|---|
| `alvoraa_portal/hooks.py:212` `on_employee_update` | now skips the write for an excluded-role manager |
| `alvoraa_portal/hooks.py:579, 647` `after_migrate` | now also removes such rows |
| `attendance_correction.py` (3 comments, lines 32, 2045, 2109) | comments only, no call |
| `request_guard.py:7` | comment only |
| `tests/test_manager_scope.py` | uses `grant`, `revoke`, `sync_for_manager`, `SCOPED_DOCTYPES` |
| `tests/test_employee_field_rights_alv215.py:14` | imports the module |
| `tests/test_grooming_066.py:538` | reads `SCOPED_DOCTYPES` only |
| `tests/test_attendance_correction.py:1269` | comment only |

No signature changes. `grant`, `revoke`, `sync_for_manager`, `on_employee_update`,
`after_migrate`, `SCOPED_DOCTYPES` all keep their names and arguments. Nothing outside
`alvoraa_portal` calls this module; `hrms`, `erpnext`, `alvoraa_goals` and
`alvox_compensation` do not reference it.

**Existing tests that must keep passing.** `test_manager_scope.py` builds its managers
with `add_roles("Employee")` only, so none of them holds an excluded role and every
current assertion still holds. Checked by reading the fixture.

**Persona impact.**

| Persona | Before | After |
|---|---|---|
| CXO | holds System Manager, so already excluded by name from the own-record row, but **not** from `manager_scope` — a CXO with direct reports gets narrow rows today. | No rows. Full sight. |
| HR Manager who also manages people | capped at their direct reports on Attendance, Employee Checkin, Attendance Request, Leave Application | full HR sight on all four |
| HR Manager who manages nobody | unaffected | unaffected |
| Line manager with no HR role | narrow rows, acts for their reports | unchanged — this is the feature, and `test_manager_scope` pins it |
| Employee | no rows from this module | unchanged |

**HRMS domain impact.** Attendance, Employee Checkin, Attendance Request and Leave
Application reads and the attendance-correction approval flow. Payroll, appraisals and
org structure are untouched — those doctypes are not in `SCOPED_DOCTYPES`.

## 6. The seven non-functional dimensions

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | `excluded_roles()` reads `frappe.get_meta("Employee")`, which is cached; `frappe.get_roles(user)` is cached per request. No new database query on the Employee-save path. `after_migrate` gains one cached role lookup per manager. |
| Security | **improves** | Removes an accidental restriction; adds no widening that was not already the role's own permission. No new bypass. The two existing `ignore_permissions` writes in the module are unchanged in count. |
| Reliability | neutral | `grant` already returned 0 for a manager with no login; the new check is the same shape. `after_migrate` keeps its try/except. |
| Scalability | neutral | One extra cached lookup per manager in a loop that already does two queries per manager. |
| Maintainability | **improves** | One list of "who must never be restricted" instead of one list and one silent omission. |
| Data integrity | **improves** | The row set stops disagreeing with the role set. |
| Compliance / privacy | neutral | No change to who may read whose data beyond restoring HR's own role rights. No personal data logged — nothing new is logged at all. |

## 7. Parallel-work check

- **Files I will change:** `alvoraa_portal/alvoraa_portal/manager_scope.py` (not a hot
  file), `alvoraa_portal/alvoraa_portal/tests/test_manager_scope.py` (not a hot file).
  **Not** `hooks.py`, **not** `own_record_permission.py`, **not** `patches.txt`, no
  DocType JSON.
- **Who else is in them:** nobody. `git log --since="14 days ago"` on both files plus
  `own_record_permission.py` returns no commits. No work-board row mentions
  `manager_scope` or `own_record`. Incoming on `origin/dev` since the main checkout's
  `dev` (5aa654d2): `62e9f521`, `fc89205e`, `742ffe45`, `d1b31221` (ALV-291 attendance
  one-off fix), `5dbbf3ab`, `dcf74d58` (ALV-292 joiner role), `b7841327` (ALV-286 tray
  link) — none touches these two files. My worktree is branched from `b7841327`.
- **Plan:** no overlap, so no sequencing needed.
- **The pin test:** `test_manager_scope.WhatAManagerIsGranted` already pins the feature
  I am narrowing — a plain line manager must still get all four rows. My new tests pin
  the fix itself.

## 8. Race conditions, edge cases, state transitions

**Races.** Two Employee saves at once could each pass the exists-check and insert a
duplicate row — that is today's behaviour and this change neither causes nor cures it. A
role change racing a save is covered above: the stray row survives to the next deploy.

**Edge cases.** Manager with no login (already returns 0). Manager who is Administrator
(holds every role, so excluded — correct). Manager with no reports (nothing granted,
unchanged). A manager whose login is disabled but holds an excluded role (skipped, which
is also the safe answer). A site whose HR Manager has no Employee read row (not excluded
— stated in section 3).

**State transitions.** `reports_to` set, changed, cleared; status Active → Left /
Inactive / Suspended. `grant` becomes a no-op for an excluded-role manager on all of
them; `revoke` still runs, and removing a restricting row can only widen, never narrow.
So moving a report away from an HR-manager boss still clears the rows.

## 9. The test that fails on the pattern

Three tests in `test_manager_scope.py`, all of which fail against the current code:

1. `grant` writes nothing for a manager holding an excluded role.
2. `on_employee_update` — a real Employee save with `reports_to` pointing at such a
   manager — writes nothing.
3. **The pattern test:** after a sync, no user holding an excluded role carries any
   narrow Employee User Permission on a scoped doctype. Stated over the whole table,
   not over the two production rows.

Plus one that proves the removal: pre-existing rows on such a manager are cleared by the
next `sync_for_manager`.

## 10. What this change does not do

- No clean-up of the 43 stray self-rows on `HR-EMP-00412` (out of scope; still latent
  until the tenant holds payroll data).
- No review of the five Location Managers' 283–483 rows each.
- Nothing on production.
- No `manager_scope` hook on User, so a promotion is cleaned at the next deploy.
