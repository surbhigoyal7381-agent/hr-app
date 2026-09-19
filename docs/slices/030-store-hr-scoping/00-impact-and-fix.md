# Slice 030 — a store's HR person sees only their store, everywhere

**Status:** built and tested on the local bench (throwaway container `hrlocal-030`,
`test_site`). On branch `slice/030-store-hr-scoping`, from local `dev` 886c8c4.
Not in local `dev`, not pushed. The user sequences merges.

## 1. The bug (diagnosis)

On ppj.dev, Arjun Sodhi — Store HR & Admin Executive, roles HR User + Payroll
User, with a **Branch User Permission** for "PPJ Chandigarh Sector 17" inside PPJ's
single company — is correctly limited to his 72 employees everywhere (Employee
list, salary slips, attendance organisation view, Data to review) **except three
places that handed him all 403**:

| # | Reader | Why it leaked |
|---|---|---|
| 1 | `alvoraa_portal.performance_api.hr_list_appraisals` → `_hr_cycle_reviews` | scoped by company only |
| 2 | `alvoraa_portal.performance_api.get_calibration_matrix` | reads through `_hr_cycle_reviews` (company only), and shipped every plotted person's `gender` to the browser |
| 3 | `Cumulative KPI Readings Check` script report (`alvoraa_goals`) | `permitted_companies()` only: 125 rows, 98 outside his store |

A plain manager (Vinod Bedi, no HR role) is correctly refused all three. The role
checks were right; these readers never learned about branches.

**Root cause.** `hrms.alvoraa_hr_core.access.permitted_companies()` knows companies
and nothing smaller. Slice 011 added branch scoping (Branch User Permission,
`alvoraa_branch` on 11 record types) but only the attendance screens honoured it,
through a private helper `attendance_analytics._linked_branches()`. Two definitions
of "who may this HR person see" existed; the performance and report readers used
neither.

## 2. What changed

One shared definition, and every reader points at it.

| File | Change | Mechanism |
|---|---|---|
| `hrms/hrms/alvoraa_hr_core/access.py` | NEW `permitted_branches(user)` — the user's Branch User Permissions (all-doctype or Employee), sorted, or `None`. NEW `permitted_employees(user)` — a set of Employee names: System Manager / Administrator → everyone; HR with no Branch permission → everyone in `permitted_companies()`; HR with one → those companies **and** those branches (an empty branch is outside — fails closed, DEF-6); no HR role → empty set. Every status, so a leaver's records still belong to their store. | extend (shared helper, appended) |
| `alvoraa_portal/alvoraa_portal/attendance_analytics.py` | `_linked_branches()` is now a two-line wrapper around `access.permitted_branches()`. Its three callers (`_population`, `filter_options`, `_in_organisation`) are untouched, so the attendance behaviour did not move — `test_branch_scope` and `test_attendance_scope_012` pass unchanged. | extend |
| `alvoraa_portal/alvoraa_portal/performance_api.py` | `_hr_cycle_reviews`: the company clause in `or_filters` becomes `["employee", "in", sorted(permitted_employees()) or [""]]`. The caller's own line and own review still come through the second clause. This fixes readers 1 and 2 at once. `get_calibration_matrix`: `gender` removed from the Employee read, from every row and from `filter_options` (`genders` key gone). The Employee read takes its names from the scoped appraisal list, so it cannot reach outside it. | extend |
| `alvoraa_goals/.../report/cumulative_kpi_readings_check/cumulative_kpi_readings_check.py` | `execute` passes `permitted_employees()`; `_rows(employees, cycle, company)` filters KPIs to those names. The report's Company filter only narrows the set; it never widens it. | extend |
| `alvoraa_portal/alvoraa_portal/www/hrms-employee.html` | The Gender filter chip removed from both screens that consume the matrix (calibration `cal-f-gender`, performance dashboard `pd-f-gender`): the two `<select>` groups and their JS lines (fill, read, filter, active-count, reset). Nothing else on the page touched. | build (removal) |
| `alvoraa_portal/alvoraa_portal/tests/test_store_hr_scoping_030.py` | NEW pinned tests (14). | test |
| `alvoraa_portal/alvoraa_portal/tests/test_org_setting_scope_030.py` + `hr_api.py` | Decision 4, own final commit — see §6. | extend |

**Not changed, on purpose:** `_require_hr`, `set_org_setting`'s allow-list (slice 012
G2), `permitted_companies()` itself, and the other performance endpoints that still
scope by company: `_assert_hr_rule`, `_stand_in_subjects`, `approve_kpi_update`,
`list_appraisals`, `get_team_appraisal`, `attach_ongoing_to_cycle`, `get_cycle_items`,
`search_employees`, `_require_hr_for`. They are outside this brief (the three named
readers). They are the obvious next candidates for `permitted_employees()`; each needs
its own look because several mix the HR path with the manager path. Listed here so
nobody has to rediscover them.

### The three decisions

- **Decision 2.** A store-level HR role sees only its own store's calibration.
  Company-wide calibration is for an HR Manager with company-wide permission. There
  is no special case in the code: the same set of names drives the list and the matrix.
- **Decision 3 — the gender chip.** The matrix sent each plotted person's gender so
  the browser could filter rows by it. A filter on a per-person value cannot work
  without the per-person value, and counts alone would not let anyone filter, so the
  chip is **dropped** on both screens rather than kept as a decoration. The
  organisation dashboard's gender bar chart (a different endpoint, counts only) is
  untouched. Nothing per-person about gender leaves the server from the matrix now.
- **Decision 4** (own commit, §6): a store's HR Manager cannot write organisation-wide
  settings.

## 3. The real numbers

Bench: throwaway container `hrlocal-030` mounting this worktree, against the shared
`test_site` (carrying slice 013's step-3 schema, inert here). One run at a time; no
other session's container was running (`docker ps` checked).

| Module | Result |
|---|---|
| `test_store_hr_scoping_030` (new) | 14 tests OK (84 s) |
| `test_store_hr_scoping_030` **without the branch intersection** | **4 failures** — exactly the four store-HR tests (helper set, review list, matrix, report); the refusals and the see-everything tests still passed. Intersection restored, 14 OK again. |
| `test_branch_scope` | 11 OK |
| `test_attendance_scope_012` | 13 OK (62 s) |
| `test_personas_012` | 17 OK (68 s); re-run after decision 4: 17 OK |
| `test_review_outside_010d` | 28 OK (213 s) |
| `test_review_render_027` | 15 OK, 2 skipped + 1 OK |
| `test_review_copies_010d` | 34 run, **1 error, not mine**: `test_sec28_bad_values...` loads the whole HR Settings document and hits `ModuleNotFoundError: alvoraa_portal...alvoraa_field_worker_designation` — slice 013's child doctype, whose field `test_site` carries (commit 49918da, 013 branch only) but whose code is not on `dev`. Fails the same way on any branch without 013. The other 33 OK. |
| `test_review_line_hr_010d` | 9 OK + 1 OK |
| `test_calibration_note_010d` | 9 OK |
| `test_review_fixround2_010d` | 12 OK + 3 OK |
| `test_review_fixround_010d` (holds the report's existing test) | 33 OK + 6 OK (274 s) — includes `test_rr_the_report_lists_cumulative_kpis...`, the report's existing test |
| `test_org_setting_scope_030` (decision 4, new) | 5 OK (8 s). Also re-run after the edit: `test_org_settings_allowlist_012` 10 OK, `test_leader_settings_012` 14 OK, `test_late_minutes_017` 4 OK + 25 OK |

Static: `ruff` on every changed Python file — no new findings (`performance_api.py`
had 84 pre-existing style findings, now 83: one `E701` one-liner about gender went).
Both new test modules are ruff-clean.

## 4. The seven dimensions, against the code as written

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | One extra query per call (`permitted_employees`: one `Employee` read). The Appraisal / KPI filter is now an `IN` list of names on an indexed column instead of a company `IN`. Designed for a tenant of ~5,000 employees: a 5,000-name list is ~100 KB of SQL, far inside MariaDB's packet limit. The matrix lost one field. |
| Security | **improves** | Tighter: a store's HR person can no longer list, plot or report on people outside their store from these three readers. Nothing got looser: System Manager / Administrator unchanged (everyone); company-wide HR unchanged (their companies); no HR role → empty set, and the role checks in front (`_require_hr`, the report's role test) are unchanged. The manager path in `_hr_cycle_reviews` (own line, own review) is unchanged. |
| Reliability | neutral | Fails closed in every branch: no companies → empty; a Branch permission with nobody in it → empty; an employee with no branch → outside. |
| Scalability | neutral | Bounded: one read of the tenant's employees, then indexed `IN` filters. No per-row queries added. |
| Maintainability | **improves** | One definition of "who may this HR person see" (`permitted_branches` + `permitted_employees`) in the place every app can import; `_linked_branches` is a wrapper, not a second truth. |
| Data integrity | neutral | Read-only change; nothing written differently. |
| Compliance / privacy | **improves** | Minimisation: a per-person sensitive attribute (`gender`) no longer leaves the server from the matrix. Access rights: row scope now matches the organisation's own Branch User Permission on all three paths. Refusals go through `access.refuse` with no personal content. |

**Persona check.** CXO (System Manager): unchanged, sees every company and store.
HR Manager with company-wide permission: unchanged. Store HR (Branch User Permission):
now sees only their store in the review list, the matrix and the report — the same
72 people as everywhere else on ppj. Employee / plain manager: still refused all three.

**HRMS domain.** Appraisals (list + calibration) and KPIs (report). Attendance
unchanged by proof. Leaves, payroll, org structure untouched.

## 5. Parallel-work check

- Fetched `origin/dev` at the start: no incoming commits (local `dev` is ahead of it).
  The slice number moved from 028 to 030 on the coordinator's word (028 was taken); the
  028 worktree and branch were removed before anything was written in them.
- Local `dev` moved to 5ae87c5 (slice 029, `tenant_api.py` only) during the build:
  none of my files, no rebase needed.
- Files held: listed on the work board row for 030. `performance_api.py` is a hot file;
  my edit is inside `_hr_cycle_reviews` and `get_calibration_matrix` only. Slice 027's
  changes to the same two functions (row-building) were already in the base I branched
  from, so I scoped the code that ships. `hrms-employee.html`: only the two gender
  filter selects and their JS lines. `hooks.py`, `patches.txt`, DocType JSON: untouched.
- Bench claimed on the board before the first run, cleared after the last; container
  removed.

## 6. Decision 4 — own final commit, droppable

`hr_api.set_org_setting` guarded with `_require_hr()` (HR Manager or System Manager)
and then wrote `frappe.db.set_default(key, value)` tenant-wide. A store's HR Manager
could change a setting for every store.

**Change:** a small guard `_refuse_store_hr(endpoint)` in `hr_api.py`, called by
`set_org_setting` right after `_require_hr()` and before the allow-list check. It uses
`access.permitted_branches()` — the same Branch User Permission read
`permitted_employees` uses — so "limited to a store" has one definition. System
Manager returns early (unchanged). `get_org_setting` is not guarded. The allow-list
logic (slice 012 G2) is untouched. Refusals log rule `030-D4` through `access.refuse`.

**Pinned** in `test_org_setting_scope_030.py` (5 tests): store HR Manager refused,
logged once, value unchanged; store HR Manager may still read; company-wide HR Manager
and System Manager still write; a System Manager with a Branch permission is
unchanged; an HR User is still refused as before.

If the user does not confirm decision 4, drop the last commit on the branch; nothing
else depends on it.

## 7. Known gaps and shortcuts, honestly

- The other company-scoped performance endpoints listed in §2 are not touched. A store
  HR person may still reach beyond their store through some of them (for example
  `search_employees`, `attach_ongoing_to_cycle`). Outside this brief; named so it is a
  decision, not a surprise.
- `permitted_employees` returns every name for System Manager and for company-wide HR,
  and the readers pass that list into an `IN` filter. Correct and bounded, but for a
  very large tenant a filter-shaped helper would be leaner. Not needed at Alvoraa's
  target sizes.
- Browser trace of the two screens without the gender chip was done by reading the
  page code, not in a browser: the removed lines are self-contained (fill, read,
  filter, count, reset) and nothing else references the two ids or `opts.genders`. The
  pin test asserts that statically.
- `attendance_analytics` keeps its own company rule (`me.company`) while
  `permitted_employees` uses `permitted_companies()` (Company User Permissions first,
  own record second). They agree for every real user on ppj; they could differ for an
  HR person whose Company permission is not the company on their own record. Left as
  is: the brief was to share the branch definition without moving the attendance
  behaviour, and the existing tests prove it did not move.
