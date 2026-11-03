# ALV-293 — implementation notes

**Local only.** Nothing pushed, nothing on `dev`, nothing on `main`, nothing run against
production. Branch `slice/alv-293-manager-scope-hr` in `.claude/worktrees/alv-293`, from
`origin/dev` `b7841327`.

---

## 1. What changed, file by file

### `alvoraa_portal/alvoraa_portal/manager_scope.py` — new code (rung 4)

| Change | Mechanism | Why |
|---|---|---|
| `from alvoraa_portal.own_record_permission import excluded_roles` | reuse | One list of "who must never be restricted". A second list would drift. |
| `never_restrict(user)` — one predicate, four lines | new code | `set(frappe.get_roles(user)) & excluded_roles()`. Both are cached, so no new query. |
| Guard at the top of `grant()` | new code | **The one write seam.** `after_migrate` reaches it through `sync_for_manager`; the Employee `on_update` hook calls it directly. A guard only in `sync_for_manager` would leave the daily save path open. |
| `should = set()` in `sync_for_manager` for such a manager | reuse of the existing `revoke` path | Makes the rows a tenant already carries go out on the next `bench migrate`, with no one-off patch. |
| Type hints on `grant`, `sync_for_manager` and the new helper | — | Only functions this fix changes. `_user_of` and `revoke` were deliberately left alone (section 9). |
| Docstring paragraph naming ALV-293 and the measured number | — | The module's existing style: every rule says why it exists. |

No other file changed. **Not** `hooks.py`, **not** `own_record_permission.py`, **not**
`patches.txt`, no DocType JSON, no new dependency, no flag, no new DocType.

### `alvoraa_portal/alvoraa_portal/tests/test_manager_scope.py` — five new tests

One new class, `AnHrManagerIsNeverRestricted`, plus two small helpers
(`_an_excluded_role()`, `ScopeCase.promote`). The existing classes are untouched.

| Test | The door it holds shut |
|---|---|
| `test_the_role_is_really_one_the_site_refuses_to_restrict` | guards the guard — if the chosen role were not excluded, the rest would rest on an unstated assumption |
| `test_granting_writes_nothing` | `grant()` directly |
| `test_a_reporting_line_save_writes_nothing` | the Employee `on_update` hook — a real `e.save()`, which is the path a real HR team walks every day |
| `test_sync_grants_nothing_and_clears_what_is_already_there` | the `after_migrate` repair, with four pre-planted rows standing in for a tenant on the old code |
| `test_no_login_that_must_not_be_restricted_carries_a_narrow_row` | **the pattern** — read over the whole `User Permission` table after the repair, not over the two production logins |

`_an_excluded_role()` asks `own_record_permission.excluded_roles()` which role to use
rather than naming one, so the test asks the same question the code asks. It prefers
`HR Manager`, then `HR User`, then `System Manager` (which is in that set by name on
every site, so there is always an answer), and raises if none exists — the test can
never pass by picking a role the site does not actually protect.

## 2. Acceptance criteria

| Required | How it is satisfied |
|---|---|
| 1. Skip the row for a user holding an excluded role | guard in `grant()`, so both write paths are covered |
| 1. Reuse `excluded_roles()`, no second list | imported; **no cycle** — `own_record_permission` imports only `hashlib`, `json`, `os`, `frappe`, `frappe.utils`, never `manager_scope` |
| 2. Decide and state what happens to existing rows | section 3: **remove**, built, with its consequences named |
| 3. A test that fails on the pattern | the five tests above; measured failing before the change and passing after (section 5) |
| Approved product decision: a person who is both keeps full HR sight | they get no row at all, and rows they already hold are removed |

Nothing in the required scope was left unsatisfied.

## 3. Point 2 — the recommendation, and what it costs

**Recommendation, and what is built: the fixed sync removes the stray rows.**
`sync_for_manager` treats such a manager as having no reports, so every row this module
ever wrote for them falls into `have - should` and leaves through the existing `revoke()`
call.

**Why not "stop adding only".** Without removal, the code is correct from here on but
`HR-EMP-00413` still sees 796 of 18,903 attendance records until somebody runs a separate
clean-up. A fix that leaves the reported case broken is the wrong shape. With removal,
DTC heals on the next `bench migrate` and no one-off script is needed.

**Three consequences to weigh, plainly.**

1. **It can remove up to four rows it did not write.** `revoke()` matches on
   `(user, for_value, applicable_for in SCOPED_DOCTYPES)`. It cannot tell our row from a
   narrow row made by hand on one of those four doctypes. So if any of the 43 stray
   self-rows on `HR-EMP-00412` is Attendance, Employee Checkin, Attendance Request or
   Leave Application, this sync will remove it too. Removing a restricting row only
   widens HR's own role rights, which is exactly the approved decision — but it is a row
   we did not create, and you should know before it runs. The other ~39, and the five
   Location Managers' rows, are untouched.
2. **It is not instant.** Removal fires on `after_migrate`, which runs on every deploy. A
   line manager promoted to HR Manager keeps their narrow rows until the next deploy,
   because there is no `manager_scope` hook on User. Adding one would be a hook on a
   shared doctype for a case this ticket did not raise — written down, not built.
3. **To drop to "stop adding only"**, revert one line in `sync_for_manager` (the
   `should = set() if ...` expression). The guard in `grant()` stays either way.

## 4. The seven dimensions, against the code actually written

| Dimension | Before to after | One line |
|---|---|---|
| Performance | **neutral** | `never_restrict` adds no query: `frappe.get_roles` is cached per request and `frappe.get_meta("Employee")` inside `excluded_roles()` is cached too. `grant()` already read `user_id` before doing anything. |
| Security | **improves** | An accidental restriction on HR is removed. No new `ignore_permissions`, no new bypass, no raw SQL, no new whitelisted endpoint. The two existing bypass writes in the module are unchanged in count, so the CI ceiling in `test_portal_security_010` does not move — and that suite passed. |
| Reliability | **neutral** | The new guard returns 0, the same shape as the existing "no login" guard. `after_migrate` keeps its try/except, so a sync failure still cannot fail a migrate. |
| Scalability | **neutral** | One cached role lookup per manager inside a loop that already runs two queries per manager. |
| Maintainability | **improves** | One answer to "who must never be restricted" instead of one answer and one silent omission. |
| Data integrity | **improves** | The permission rows stop disagreeing with the role grid, and heal themselves on the next migrate. |
| Compliance / privacy | **neutral** | No widening beyond restoring a role's own rights. Nothing new is logged, so no personal data can reach a log. |

## 5. Tests — every batch

**`bench run-tests --app alvoraa_portal` prints a summary per batch.** It printed three.
The run was killed by its own 2-hour cap part-way through the third, so that batch's
numbers are partial and I ran the permission modules it had not reached separately.

| Run | Result |
|---|---|
| `--app alvoraa_portal` **batch 1** | **Ran 48 tests in 100.7s — OK** |
| `--app alvoraa_portal` **batch 2** | **Ran 1119 tests in 4010.7s — FAILED (failures=2, errors=1, skipped=19)** |
| `--app alvoraa_portal` **batch 3** | **incomplete** — 2869 tests planned, about 950 run (it had reached `test_grooming_erase_066`) when the 2-hour `timeout` killed it. 2120 passes recorded across all three batches, and no failure beyond the three below. |
| `--app alvoraa_goals` | **Ran 18 tests in 5.1s — OK (skipped=2)** |
| `--module ...test_manager_scope`, fix **reverted** | **Ran 17 tests — FAILED (failures=4, errors=1)** |
| `--module ...test_manager_scope`, fix in place | **Ran 17 tests in 127.1s — OK** |
| the same module after the subtract pass | **Ran 17 tests in 124.4s — OK** |

**The three failures are not mine.** I re-ran each module against `origin/dev`'s own
`manager_scope.py`, with only my tests added, and each failed in the same place:

| Module | Baseline on unmodified code | Why it is not mine |
|---|---|---|
| `test_expense_birthdays_076` | Ran 35, FAILED (errors=1) | Expense Claim is not in `SCOPED_DOCTYPES`, and the insert uses `ignore_permissions=True` anyway |
| `test_alv291_attendance_fix.test_the_runbook_end_to_end` | Ran 4, FAILED (failures=1) | ALV-291's own test, which landed on `dev` today; it runs as Administrator |
| `test_email_logo_175` | Ran 11, FAILED (failures=1, skipped=1) | it found `their-own-brand.png` — another test left a tenant logo on this long-lived `test_site` |

**Because batch 3 was cut short, I ran the ten modules that own this surface on their
own, with the fix in place. All ten passed:**

| Module | Result |
|---|---|
| `test_own_record_permission_alv249` | Ran 32 — OK; second batch Ran 1 — OK |
| `test_portal_security_010` (holds the bypass ceiling) | Ran 45 — OK; second batch Ran 5 — OK |
| `test_leave_permissions` | Ran 12 — OK |
| `test_leave_endpoint_access_173` | Ran 9 — OK |
| `test_leave_privacy_045` | Ran 11 — OK |
| `test_team_scope_259` | Ran 12 — OK |
| `test_team_scope_034` | Ran 19 — OK |
| `test_employee_field_rights_alv215` | Ran 20 — OK |
| `test_grooming_066` | Ran 64 — OK; second batch Ran 1 — OK |
| `test_access_control` | Ran 34 — OK |

`test_attendance_correction` — the suite that uses `manager_scope`'s grants most heavily
— ran inside batch 2 and passed.

**One finding worth your attention.** The pattern test, run against the **unmodified**
code, named ten logins on `test_site` that already carried a narrow row while holding an
excluded role: `mshr1/2/3@example.com` (mine), plus `s010.d.line.top`,
`s010.d.team.hrboss`, `s010.s034.storehr`, `s010.s034s.storehr`, `s010.s045.crossboss`,
`s042.kamal` and `s045.kamal`. With the fix, the repair cleared all of them inside the
test's own transaction and the test passed. So the fault was not only at DTC — our own
test fixtures have been producing it, and nothing was looking.

## 6. Permission and privacy notes

- **Permission enforcement point:** Frappe's own `User Permission` layer. This change
  removes rows; it writes no new kind of row and adds no portal-side check. The limit on
  a plain line manager is unchanged and still enforced by Frappe, not by our portal.
- **Bypasses: unchanged, none added.** `grant()` keeps `doc.flags.ignore_permissions =
  True` and `revoke()` keeps `ignore_permissions=True` on the delete, both pre-existing
  and both necessary because only a System Manager may write `User Permission`.
- **Sensitive fields touched:** none directly. Indirectly, the four scoped doctypes
  (Attendance, Employee Checkin, Attendance Request, Leave Application) become fully
  visible again to a login whose HR role already grants that read. Salary Slip, Expense
  Claim and the rest of `SCOPED_DOCTYPES`' deliberate omissions are unaffected.
- **Logging:** nothing new is logged. No name, email, employee ID or role list is written
  anywhere by this change.

## 7. What else moved while I worked

`git fetch origin` at the start. The main checkout's `dev` sat at `5aa654d2`; `origin/dev`
was at `b7841327`. Seven commits had come in that the main checkout did not have:

| Commit | What |
|---|---|
| `62e9f521`, `fc89205e`, `742ffe45`, `d1b31221` | ALV-291 — a one-time, preview-first fix for DTC's October attendance |
| `516e24bd`, `5dbbf3ab` | 079 — masked Aadhaar card wording and QR digits |
| `dcf74d58` | ALV-292 — the joiner role must reach a site built from scratch |
| `b7841327` | ALV-286 — a named way back to the tray |

**None of them touches `manager_scope.py`, `own_record_permission.py` or
`test_manager_scope.py`.** `git log --since="14 days ago"` on all three files returns no
commits at all. My worktree is branched from `b7841327`, so there was nothing to rebase
and **no conflict arose** — nothing of anyone's could be lost.

The main checkout holds a large set of other sessions' uncommitted edits (about 30 files
under `.claude/` and `alvoraa_portal/`). **I touched none of them, staged nothing by
`-A`, and merged nothing into local `dev`.** That is also why the tests ran in a
throwaway container mounted on my own worktree rather than on `hrlocal-bench`, which
reads the shared main checkout.

A work-board row was added claiming the worktree and the container, and removed at the
end; the container and its site were left in place for you, since the run was cut short.

## 8. Commands run

| Command | Result |
|---|---|
| `python scripts/check_app_integrity.py` (before and after the subtract pass) | **905 checks, OK - all consistent**, both times |
| the test runs | section 5 |

## 9. The subtract pass

I read it again asking only what could go. Two things went:

1. **The type hints on `_user_of` and `revoke`.** This fix does not otherwise change those
   two functions, and annotating them would be sweeping code the slice did not ask about.
2. **One line of the docstring paragraph**, trimmed to the rule plus the measured number.

What I considered and kept:

- `never_restrict` as a named helper rather than the expression inlined twice. It is used
  in two places and a test asserts it directly.
- The five new tests. Each closes a different door — `grant`, the hook, the sync, the
  whole-table pattern, and one that proves the chosen role really is excluded.
- `should = set()` rather than an early return in `sync_for_manager`. The early return
  would need its own revoke loop; the empty set reuses the one that already exists.

What is *not* in the change and was never written: no feature flag, no new DocType, no
settings field, no second role list, no data-migration patch, no hook on User, no
background job, no cache, no index, no new dependency.

## 10. Known gaps and shortcuts

| Item | Label | Detail |
|---|---|---|
| Removal waits for the next `bench migrate` | **intentional trade-off** | `after_migrate` is the only caller of `sync_for_manager`, so a promotion leaves the stray rows until the next deploy. A `manager_scope` hook on User would close it, and is a hook on a shared doctype the ticket did not ask for. Your call. |
| The removal can take up to four rows this module did not write | **intentional trade-off** | Section 3, consequence 1. It only ever widens HR's own role rights, but worth knowing before the first migrate on DTC. |
| The exclusion is only as strong as the site's `Employee` read permissions | **acceptable simplification** | `excluded_roles()` is computed from them, plus System Manager and Administrator by name. A site that gave HR Manager no read row on Employee would not get the protection. That is `own_record_permission`'s existing shape, and reusing it was the point. |
| The 43 stray self-rows on `HR-EMP-00412`, across 43 doctypes | **dangerous debt — escalated here, not just noted** | Out of this ticket's scope and untouched on 39 of the 43 doctypes. Latent only because the tenant holds no payroll data. **The first payroll run through the portal leaves an HR Manager able to see exactly one salary slip.** It needs its own decision before payroll goes through the portal. |
| Our own test fixtures have been creating the same fault | **temporary debt** | Seven `s010*`/`s042*`/`s045*` logins on `test_site` carry it. The fix cleans them on any sync, so nothing needs doing — but the pattern was reproducible in our own tests all along. The new pattern test is what now looks. |
| The whole `alvoraa_portal` suite did not finish | **temporary debt** | Section 11. |

With more time I would add the User-level hook so a promotion takes effect at once rather
than at the next deploy, and I would look at why `test_site` carries logins that
reproduce this fault.

## 11. What I did not test

Said plainly, because a shortcut you declare is a decision and one you hide is a defect.

- **The whole `alvoraa_portal` suite did not finish.** Batches 1 and 2 ran in full (1167
  tests). Batch 3 got about 950 of its 2869 tests before the 2-hour cap killed it. I
  covered the gap with the ten permission modules above, but roughly 1900 tests in that
  batch did not run in this session.
- **I did not run the `hrms` or `erpnext` suites.** Neither app references
  `manager_scope`; I grepped for it.
- **I did not test on a freshly created site.** `data-doors.md` asks for that, and
  `test_site` is long-lived — which is exactly how the `test_email_logo_175` failure and
  the seven stray fixture rows arose. A fresh-site run is worth doing before this goes to
  `dev`.
- **I did not run the door list by hand as a live login.** No API call as a plain staff
  login, a manager or an HR Manager; no report view, export, link search, share or
  child-table check. This change only *removes* restricting rows and adds no new read
  path, so the doors it could open are the ones the HR role already holds — but that is
  an argument, not a test.
- **Nothing was run against production, dev, or any real tenant.** No read-only count on
  DTC either: the ticket's counts were taken before I started and I did not repeat them.
- **No JavaScript or screen was traced**, because none changed.
- **I did not verify the removal against DTC-shaped data** — only against four rows
  planted in a test.
