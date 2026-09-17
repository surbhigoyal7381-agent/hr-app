---
slice: 012-leadership-view
artifact: 03-implementation-notes
scope: push 1 only (US-1 to US-10)
author: hrms-fullstack-engineer
date: 2026-09-15
status: built on the local instance; fix round 1 applied after the test report; NOT pushed
branch: slice/012-leadership-view in .claude/worktrees/012-leadership-view
---

# 012 · Leadership view — push 1 implementation notes

## The short answer

**Bad news first.**

1. **No timing run on synthetic 400 / 1,000-person sites (strategy commit 10, OPS-53, OPS-64)
   was done.** The bench was shared with slice 010 all day. A lighter timing script exists
   (see "Timing") but has not been run.
2. **The portal page was traced by reading the code, not in a browser.** 360 px, 200% zoom
   and keyboard checks through the confirm dialog are still to do.
3. **The Data to review menu badge only appears after HR opens HR Analytics or Data to review
   in that visit** (AC-31 wants it on the menu from page load). A load-time count would need
   one more call per HR page load; I did not add an endpoint the strategy did not name.
4. **The whole `alvoraa_portal` suite has not been run after all 012 commits.** Every 012
   module and the existing modules that pin what I touched pass (section 8). The whole-suite
   run is the test engineer's next step.

Everything else in the approved strategy is built. Nothing was pushed, nothing deployed,
no `docker cp`. `bench migrate` ran twice on `test_site` only.

---

## 1 · Base branch — why local `dev`, not `origin/dev`

`origin/dev` had nothing new (c27fb56). Local `dev` held slice 010 group D's unpushed
commits. I branched from **local `dev` (4bb3d8d)** because:

- the bench runs the main checkout's `dev`, and `merge --ff-only` needs my branch on top of it;
- D-15 already says push 1 reaches `origin/dev` only after group D, so the two cannot be
  separated at push time anyway;
- basing on `origin/dev` would only have forced the same rebase an hour later, with group D's
  `hr_api.py` changes as a likely conflict.

I rebased twice as `dev` moved (010 D phase 2 notes; 010 D phase 3 commits 285858a…926369e).
Both rebases were clean.

## 2 · Commits

On `slice/012-leadership-view`. "In dev" means already fast-forwarded into local `dev` for a bench run.

| # | Hash | What | In local dev? |
|---|---|---|---|
| 1 | ed8732f | Eight indexes: Property Setter + `add_index` for the six one-column ones, `add_index` for the two two-column ones; hook lines after `branch_scope` | yes |
| 2 | 1d75c28 | G2: `get/set_org_setting` allow-list (`kra_link_mandatory`, "0"/"1"); Q6 org-roles guard | yes |
| 3 | bdc50c0 | G3: `person()` scoped to self / line / org population, 12-month cap; `filter_options()` via `get_list` | yes |
| 3a | b89cdfb | G3 tests fix (class-level rollback; ERPNext's automatic Employee user permission) | yes |
| 4 | c692ea9 | Doctypes `Alvoraa Data Review Item` and `Alvoraa Leader View Settings` with controllers | yes |
| 5 | 85f0073 | `org_figures.py`: scope, attendance, leave, people, data up to; fixtures | yes |
| 5a | e6bae5c | Settings: System Manager `create` (first Single save is an insert); fixtures stop committing | yes |
| 5b | 3c33d56 | Settings set-up writes a whole record so the first change keeps a Version row | yes |
| 6 | 21a2518 | G1: `get_hr_analytics` on the shared calculation, "not linked"; counter table (OPS-75) | yes |
| 7 | 0fa5952 | Morning checks: cron → enqueue on `long`; D5, D6, D18-1, D18-2; failure log; stamp; enqueue after migrate (OPS-72) | yes |
| 8 | bf79aad | `data_review_items`, `data_review_confirm` | yes |
| 9 | 96f3ef9 | Portal page: Data to review panel, HR Analytics lines | yes |
| 9a | 3e2f1e0 | A failed page re-check logs and still shows the list | yes |
| 9b | 15a2dae | Page pin test: match the dialog across lines | yes |
| 10 | — | Synthetic-site timings | **not done** (see Short answer 1) |

## 3 · What was built, file by file

| File | Mechanism | Why this one |
|---|---|---|
| `alvoraa_portal/data_review.py` (new) | Extend: indexes installer, morning job, two whitelisted endpoints | One module for the Data to review feature, as the strategy said |
| `alvoraa_portal/org_figures.py` (new) | Extend: grouped, parameterised SQL | One definition for HR Analytics now and the leader view in push 2 |
| `doctype/alvoraa_data_review_item` (new) | Build: doctype, name = hash of the finding's key | A finding the business names; needs `company` and branch so User Permissions apply |
| `doctype/alvoraa_leader_view_settings` (new) | Build: Single, `track_changes` | D-1 / BA-Q10: System Manager-only setting without touching HR Settings' permissions |
| `hr_api.py` | Extend: `get_hr_analytics`, `get/set_org_setting` only | G1, G2. No signature changed |
| `attendance_analytics.py` | Extend: `_org_roles`, `person`, `filter_options`, new `_org_read`, `_in_organisation` | G3, Q6. `_population` untouched (D-6) |
| `hooks.py` | Configure: `"cron"` key at the end of `scheduler_events`; one line at the end of `after_migrate` and `after_install` | Hot-file rule: added at the end, with comments |
| `www/hrms-employee.html` | Extend: own block, `dr` prefix; one nav item, one `switchPanel` line, two `applyPlanNav` lines, `renderAnalyticsData` additions | Hot-file rule. Org Settings not touched |
| `tests/test_portal_security_010.py` | `CEILINGS`: `hr_api.py` 77 → 75; five new files at 0 | OPS-75. Inserted after the `hr_api.py` line, not at the end, to avoid 010 D's planned end-of-table line |
| `tests/*_012.py`, `tests/leader_fixtures_012.py` (new) | Tests | Pin tests named per feature |

## 4 · Deviations from the strategy, and why

| # | Strategy said | Built | Why |
|---|---|---|---|
| 1 | `org_figures` has a `group_by` enum (`branch`, `department`, `month`) | Not built | Push 1 has no caller for it. Push 2 adds it with its first use (no abstraction before its use) |
| 2 | Settings value "created as 5" | Set-up writes a **whole** Single record (name, timestamps, 5) without the controller | Found in testing: a Single with no stored name is saved through `insert`, which keeps **no Version row** — the first real change would have gone unrecorded (SEC-10) |
| 3 | System Manager read + write on settings | read + write + **create** | Same cause: the first save of a Single needs `create`. Still System Manager only |
| 4 | D18-1 per branch | Also a **company-wide D18-1** record for Left people **with no branch** | Otherwise that gap is invisible. Location HR do not see it (company-wide) |
| 5 | Checks run for every company | A company with **no submitted attendance at all** gets no records | AC-30: a new tenant says "No figures yet", not "Needs review". Without this, D18-2 would fire on every new tenant |
| 6 | AC-32 "company-wide items show no confirm action" for store HR | Store HR **do not see company-wide records at all** | Strategy 6.6: an explicit branch filter; a company-wide record carries company-wide counts (fail closed). The AC's two halves conflict; I followed the approved strategy |
| 7 | Doubtful cards "one card per set of dates" | One card per company and identical date set, naming the branches | Same idea; on ppj six branches × 7–9 Sep become one card |
| 8 | Slow-call log with query count (OPS-56) | Endpoint, scope kind, branch count, duration; **no query count** | Counting queries in production needs a wrapper around every query; not worth it for a log line |
| 9 | AC-19 "Kavya's `ldr:` cache keys are gone" | Nothing cleared | Push 1 has no cache (strategy 6.11). Push 2 adds the delete |
| 10 | `run_morning_checks()` | `run_morning_checks(companies=None)` | Lets tests and a support person run one company; the scheduled job passes nothing |
| 11 | AC-11 pin in `hrms/.../test_attendance_score.py` | In `alvoraa_portal/tests/test_org_figures_012.py` | OPS-74: CI does not run the hrms fork's tests |

## 5 · The seven non-functional dimensions, against the code written

| Dimension | Before push 1 | After (as built) | Verdict |
|---|---|---|---|
| **Performance** | HR Analytics: ~12 tenant-wide queries, two name lists read without limits | Fixed query count per endpoint (tests at 10/100 people, 2/8 branches). HR Analytics ≈ 15 queries + 2 for leave. Eight indexes. Data to review: re-check (5 queries per company in scope) + list + 3 figure queries. **Not measured at 1,000 people** | Improves (unmeasured) |
| **Security** | G1, G2, G3 open | Closed. New endpoints POST-only, plan-gated, HR-only, `no-store`, per-user limit. No new `ignore_permissions` (counter proves it for new files). All SQL parameterised; a quote in a branch name is tested | Improves |
| **Reliability** | — | Job writes only on change, never touches Confirmed, commits per company, logs type-only failures, stamp only on full success; page re-check failure does not break the page. New dependency: `worker-long` | Improves, one new moving part |
| **Scalability** | Tenant-wide queries | Queries grow with companies in scope (1–2), not people or branches. Job reads 35 days through the two-column indexes | Improves |
| **Maintainability** | Three attendance formulas | Two (Attendance Insights keeps its own, BA-Q4). +2 modules, +2 doctypes, +1 job, ~19.5 KB page block | Neutral |
| **Data integrity** | Leave used ÷ every allocation ever; device-failure days counted as absence | Leave year per company; doubtful days left out while Open; confirmations locked (`for_update`) and immutable; one record per finding by primary key | Improves |
| **Compliance / privacy** | Store HR saw every store's names, gender, joining dates; any HR could re-grant named leave data | Scoped; review records hold counts only; refusals logged with rule id only; settings and confirmations keep who/when/before/after | Improves |

**What gets worse for someone:** HR numbers change with no switch; HR with no company link loses
HR Analytics figures; store HR can no longer open other stores' people; HR can no longer write
tolerance, photo-retention or org-roles keys through the portal API.

## 6 · How each in-scope SEC, PRIV and OPS item is met in code

| Item | Where | Test |
|---|---|---|
| SEC-7 | `data_review._require_hr`, `@frappe.whitelist(methods=["POST"])`, `@requires_feature("analytics")`, `response_headers["Cache-Control"]="no-store"` | `test_data_review_012.TestThePage.test_endpoint_hygiene`, `test_people_who_are_not_hr_are_refused` (pass) |
| SEC-8 | No `ignore_permissions` in new/changed code; `%(x)s` parameters only | `test_portal_security_010` CEILINGS; `test_hr_analytics_scope_012.test_a_branch_name_with_a_quote_is_just_a_value` |
| SEC-10 | `AlvoraaLeaderViewSettings.validate` / `on_change`; `min_group_size()` → 10 when broken | `test_leader_settings_012` (14 pass) |
| SEC-12 | Minimum only in the Single; allow-list refuses other keys | `test_the_minimum_is_not_a_frappe_default`; G2 tests |
| SEC-13 | Record carries company + branch; `get_list` + explicit branch filter; confirm checks scope + `has_permission(write)` + kind + status, all-or-nothing, row lock; controller refuses every hand edit | `test_data_review_item_012` (10 pass); `test_data_review_012` (pass) |
| SEC-14 | `access.refuse` / `log_refusal` with rule id; no key, value or branch name | G2, G3 tests (pass); SEC-13 test (pass) |
| SEC-15 | Error Log message is JSON `{company, stage, error type}`; generic page messages | `test_morning_checks_012.test_a_failure_is_logged_without_figures…` (pass) |
| SEC-16 | `get_hr_analytics` on `hr_scope`, `get_list` name lists, leave year | `test_hr_analytics_scope_012` (pass) |
| SEC-17 | `person()` / `_in_organisation` / `filter_options` via `_org_read` | `test_attendance_scope_012` (8 pass) |
| SEC-18 | `ALLOWED_ORG_SETTINGS` | `test_org_settings_allowlist_012` (10 pass) |
| SEC-19 | `NEVER_ORG_ROLES` incl. `All`, `Guest`, `Desk User` (D-11); security log line with role names | same module (pass) |
| SEC-22 | D5 `having expected >= minimum`; counts only | `test_morning_checks_012.TestSmallGroups` (pass) |
| PRIV-10 | Same as SEC-22 | same |
| PRIV-13 | `org_figures.PURPOSE`; `attendance_score.py` untouched | `TestAppraisalScoresDoNotMove` (2 pass) |
| PRIV-14 | Declared in the doctype description; no purge | Doctype description (no automated test) |
| PRIV-1 (HR page) | Response holds counts, dates, company/branch names only | `test_central_hr_sees_every_kind_with_counts_and_no_people` (pass) |
| OPS-1, OPS-6 | `org_figures` grouped SQL; `_analyse` not reused | figures tests (pass) |
| OPS-5, 20, 52, 70, 71 | `data_review.add_indexes` | `test_leader_indexes_012` (5 pass, incl. re-sync survival) |
| OPS-7, OPS-63 | Query-count tests for figures (pass), HR Analytics, job, Data to review (pass) | — |
| OPS-9, OPS-48 | cron → `enqueue(queue="long", timeout=900, job_id="leader-data-checks", deduplicate=True)` | `test_the_cron_entry_only_queues_the_job_once` (pass) |
| OPS-21, OPS-22 | D5 per branch per day; company with no check-ins → absent alone | `TestNoCheckInsAtAll` (pass) |
| OPS-40 | `_within_hourly_limit`, 30/hour per user, key expires in 1 h, Redis trouble never blocks | `TestConfirmLimit` (pass) |
| OPS-49 | `recheck()` on page open, clears only (D-5) | `TestFixingTheDataClearsTheRecord` (pass) |
| OPS-50 | Stamp via `set_single_value` (no Version); stale > 26 h; fixed Error Log title | settings stamp test (pass); job tests (pass) |
| OPS-56, 57 | `org_figures.log_if_slow` (no figures or names) | none automated |
| OPS-58 | `track_changes` on both doctypes; saves use `ignore_version=False` so tests see Version rows | settings + item tests (pass) |
| OPS-72 | `data_review.after_migrate` queues the check last, after indexes | hook-order test (pass) |
| OPS-75 | CEILINGS table | runs with `test_portal_security_010` (pass) |
| OPS-76 | `frappe.get_attr(JOB_METHOD)` asserted | job test (pass) |
| OPS-82 | ~19.5 KB added before compression (measured with `git diff`) | — |
| OPS-53, OPS-64 | **Not done** | — |

## 7 · What else moved while I worked

| When | Came in | Files | Conflict? |
|---|---|---|---|
| First rebase | c2fc8fc (010 D phase 2 notes) | one `docs/` file | No |
| Second rebase | f22a45e … 926369e (010 D phase 3, 7 commits) | `hr_api.py` (scorecard functions), `goals_api.py`, `performance_api.py`, `alvoraa_goals/*`, `kpi.json`, `appraisal.json`, their tests, `demo/` | No. I checked 0d30808's added lines in `hr_api.py` are still present (`_hr_target_employee` calls) and the counter is still 75 |
| Third rebase | 5100f83, 9c6d97b, 474d8f3 (010 D phase 3 tests and notes) | `test_portal_security_010.py` CEILINGS, `review_items.py`, their tests | **Yes, one conflict** in the CEILINGS table. Kept both: their `performance_api.py` 64 and `review_backfill.py` 0; my `hr_api.py` 75 and five new files at 0. Proved by grep, then ran the whole `test_portal_security_010` module: 50 tests OK. Real counts: `performance_api.py` 64, `hr_api.py` 75 |

Other sessions' uncommitted edits in the main checkout (`.claude/*`, `CLAUDE.md`, `backlog/…`,
`alvoraa_position.py`, deleted `OBJECTIVES_KPI_REQUIREMENTS.md`) were left alone. None is mine.

This notes file sits in the main checkout's **untracked** `docs/slices/012-leadership-view/`
folder and is not committed: committing the folder on my branch would make `merge --ff-only`
refuse (the same untracked-file block slice 010 hit).

## 8 · Commands run and real results

| Command | Result |
|---|---|
| `git fetch`, `git log dev..origin/dev` | nothing new on origin/dev all session |
| `bench --site test_site migrate` (×2, test_site only) | completed; after_migrate hooks ran |
| `run-tests --module test_leader_indexes_012` | 5 tests OK |
| `run-tests --module test_org_settings_allowlist_012` | 10 tests OK |
| `run-tests --module test_attendance_scope_012` | first run 1 fail + 7 errors (test fixtures: class-level rollback; ERPNext Employee user permission); after fix 8 OK |
| `run-tests --module test_attendance_analytics` / `test_branch_scope` / `test_portal_call_paths` / `test_attendance_correction` | 17 / 11 / 7 / 42 OK (after commits 1–3) |
| `run-tests --module test_leader_settings_012` | first run 4 errors (missing `create`), then 1 fail (no Version on first save); after both fixes 14 OK |
| `run-tests --module test_data_review_item_012` | 10 OK |
| `run-tests --module test_org_figures_012` | first run 1 fail (test shared a company across a class); after fix 18 OK (60 s) |
| `python scripts/check_design_system.py` | OK — the visual system holds |
| `python scripts/check_api_paths.py --max 2` | OK (2 known, unchanged) |
| `python scripts/check_app_integrity.py` | first FAIL (`async function` handlers not seen as global); after fix OK, 558 checks |
| `node scripts/check_undefined_js.js hrms-employee.html` | none |
| `node scripts/check_portal_handlers.js` | all reachable and callable |
| `bench version` | not recorded (the command errored inside the container); Frappe 16.33.1 / ERPNext 16.34.2 / HRMS 17.0.0-dev per the impact analysis (OPS-77 still to record properly) |

After slice 010 freed the bench (commits rebased, fast-forwarded into local `dev` at 15a2dae):

| Command | Result |
|---|---|
| `run-tests --module test_hr_analytics_scope_012` | 10 tests OK |
| `run-tests --module test_data_review_page_012` | first 1 fail (my regex did not cross lines); after 15a2dae 4 OK |
| `run-tests --module test_morning_checks_012` | 17 OK |
| `run-tests --module test_data_review_012` | 23 OK |
| `run-tests --module test_portal_security_010` | 50 OK (counter table with both slices' lines) |
| `run-tests --module test_endpoint_entitlement` | 13 OK |
| Re-run after commits 6–9: `test_org_figures_012` / `test_leader_indexes_012` / `test_data_review_item_012` / `test_leader_settings_012` / `test_attendance_scope_012` / `test_org_settings_allowlist_012` / `test_portal_call_paths` | 18 / 5 / 10 / 14 / 8 / 10 / 7 OK |

**Not run:** the whole `alvoraa_portal` and `alvoraa_goals` suites after all 012 commits, the
hrms `alvoraa_hr_core` tests, and the timing script.

## 9 · Timing

Not measured. A script for a quick measurement inside one rolled-back transaction on
`test_site` (1,000 employees, ~300 days of attendance, check-ins; p50/p95 of
`get_hr_analytics` and `data_review_items`; the job for one company; `EXPLAIN` on the main
queries) is ready in my scratchpad (`time_012.py`, fed to `bench console`). It is not the
OPS-64 synthetic-site run; that still needs the bench and your word to create sites.

## 10 · Known gaps and shortcuts

1. Whole-suite run not done (test engineer).
2. Badge only after HR opens Analytics or Data to review (above).
3. Page not traced in a browser; 360 px / 200% zoom / keyboard not checked.
4. "Keep them left out" and "Keep 'Needs review'" send nothing (AC-20 is true by construction; no server test).
5. Real concurrency of two confirmations is proven only by the row lock in code, not by two threads.
6. D-6 (Attendance Insights for HR with no Employee record sees all companies) left as recorded.
7. Draft copy used for: not linked (BA-Q5), empty state and success toast (BA-Q12), the D18-2 confirm dialog, the "no branch" leavers line. UX designer to confirm.
8. The `System Manager` without an HR role still sees both HR menu items (old `is_hr` mismatch) and gets a refusal message on open.
9. A doubtful day outside the "data up to" month shows the dialog without a "drop to about" figure.
10. Page `drT()` uses Frappe's `__` only if the page has it; today it does not, so strings are English.
11. Test fixtures left a few `S012 …` Branch rows and one test Employee on `test_site` from the first (buggy) fixture run. Harmless, unique names.

## 11 · For the test engineer

- Worktree `.claude/worktrees/012-leadership-view`, branch `slice/012-leadership-view`. Work there.
- `test_site` needs a migrate for the two doctypes — already done at commit 5b; commits 6–9 add no schema.
- Frappe 16 rolls back **per class**, not per test. Tests that read a whole company live alone in a class. Use `leader_fixtures_012` helpers; `fx.user()` does not commit (the shared `ensure_user` does).
- ERPNext adds an "Employee = self" User Permission when a login is linked unless `create_user_permission = 0`; test HR users need it off.
- Saves ask for Version rows explicitly (`ignore_version=False`), because Frappe skips them in tests.
- The morning job commits per company; tests patch `frappe.db.commit` and `rollback`.
- Frappe fills an empty Link field from the caller's own User Permission, so an Employee
  inserted while logged in as store HR is given that store's branch. Build no-branch
  fixtures as Administrator (this cost me one red test in fix round 1).
- `data_review_confirm` counts calls per user per hour in Redis; `_clear_limit` in the test resets it.
- Please run the whole `alvoraa_portal` suite once commits 6–9 are in `dev`, and the timing script / OPS-64 when the bench allows.

---

## 12 · Fix round 1 (2026-09-16) — after the test report

Seven defects from `04-test-report.md`. Your decisions of 2026-09-16: DEF-6 option (a),
DEF-7 index yes. DEF-4 is a spec defect and no code changed for it.

| Defect | Commit | What changed |
|---|---|---|
| DEF-1 | 18e9f7a | The two new doctypes are named in `TENANT_DOCTYPES` in `subscription.py`. **Why that list:** both hold the tenant's own data - findings about its own figures, and its own privacy rule - read and written inside the tenant by its HR and System Manager. `CONTROL_PLANE_DOCTYPES` is our billing and provisioning plumbing, and is the list the tenant access derivation *skips*; putting them there would have quietly taken them out of that derivation. `test_invoicing.test_every_billing_doctype_is_named_as_control_plane_only` now passes |
| DEF-2 | 4de5423 | `existing_items` also loads doubtful-day records that are still Open from before the 35-day window, and the check looks at those exact days again in one extra grouped query. A day HR fixes late now clears. The test engineer's expected failure is a passing test |
| DEF-5 | 4de5423 | `apply_findings` leaves a Cleared record alone when it is called from the page (`allow_create` False). Decision D-5 holds: the page clears, the morning run re-opens |
| DEF-6 | 502bddf, a6e38db | `person()` and `filter_options()` limit a location HR user to their linked branches, so an employee with no branch is outside their scope - the same rule HR Analytics applies (D-8). Frappe's strict user permissions were **not** switched on. New pin tests in `test_attendance_scope_012` |
| DEF-7 | 4de5423 (index), 0f1a3ea (tests), bc65d50 (query), 5aad1ae (the joins and the distinct count) | A ninth index, Attendance (`company`, `attendance_date`), added the agreed way. **The index alone was not enough:** on a tenant with one company every Attendance row is that company's, so `MAX(attendance_date)` still read the whole table. "Data up to" now reads the newest row per company with `ORDER BY ... LIMIT 1`, which uses the index |
| DEF-3 | 3a8850a | The badge count comes back with the portal context the page already loads, so it is on the menu from the first paint |
| DEF-4 | — | Spec defect in AC-32 (store HR and company-wide records). No behaviour changed; for the analyst |

### What DEF-3 costs

No extra HTTP call: the count rides on `get_portal_context`, which every portal page load
already makes. Per HR page load it adds **one permission-checked read** of the review
records (plus `permitted_companies` and the user's permissions, both already cached in
that request), and only when the plan includes analytics. Everyone who is not HR gets the
context untouched, at zero cost. It is added **around** that response's one-hour cache,
not inside it, so a confirmation shows on the next page load rather than up to an hour
later; the cached body itself is unchanged.

### Timing after the DEF-7 work

Measured the way the test engineer measured: `test_site`, 1,000 people, 257,000 attendance
rows, 120,941 check-ins, seeded and **rolled back**, warm calls, 30 runs each. This run was
**quiet**: no other bench run before it or after it (checked with `pgrep` both times). An
earlier pair of runs was spoilt by an overlapping slice 010 run and is not reported here.

Warm p95, 1,000 people. Budget: 500 ms for a whitelisted call (`nfr-budget.md` §2), and
`07` §3 H allows `get_hr_analytics` up to 1 s at 2,000.

| Call | Before, same script and seed (the old "data up to") | After |
|---|---|---|
| `get_hr_analytics`, whole company | 2,404 ms | **359 ms** |
| `data_review_items`, whole company | 1,665 ms | **409 ms** |
| `get_hr_analytics`, one branch | 273 ms | **50 ms** |
| `data_review_items`, one branch | 281 ms | **41 ms** |

Both columns come from the same script and the same seed, minutes apart, so they compare
fairly with each other. They are **not** comparable with the test report's own numbers
(761 ms and 536 ms for the same two calls): that was a different run on the same laptop, and
the spread between runs here is large - which is exactly why OPS-64's separate sites still matter.

**Verdict: inside the budget at 1,000 people, on a quiet bench.** Three things did it, in
order of size:

1. **The attendance query now asks only for what the screen shows.** It joined Employee and
   Shift Type and counted distinct people, for late arrivals, short days and group size -
   none of which HR Analytics or Data to review shows. Measured on its own over a month of a
   whole company: 158 ms with them, 72 ms without the joins, 23 ms without the distinct
   count as well. The leader view keeps the full version, because push 2's small-group rule
   needs the people count.
2. **"Data up to" reads the newest row through the index** instead of `MAX()` over the scope
   (`EXPLAIN`: type `ALL`, whole table, 236,612 rows → type `range` on
   `company_attendance_date_index`, no sort).
3. **The index itself**, Attendance (`company`, `attendance_date`), which makes 2 possible
   and speeds the job's "has this company any attendance" read.

Caveats, said plainly: this is a laptop running `bench serve` (one process) with three other
Frappe stacks in Docker, so these are numbers for comparing against the budget, not a
production forecast. 2,000 employees was not run, and OPS-64's separate synthetic sites and
the index-migrate timing (AC-5) are still open before `main`.

### Deviations added in this round

| # | What | Why |
|---|---|---|
| 12 | `data_up_to` sends one query per company instead of one for the scope | The index cannot help `MAX()` when one company owns the table. Query count still does not grow with people or branches; it grows with companies, as leave already did |
| 15 | `attendance_figures` gained a `detail` flag, and HR Analytics and Data to review pass `detail=False` | The budget. Both screens showed none of the three figures the joins and the distinct count were for. The leader view keeps the default |
| 16 | A scope of one company or one branch is written as `=`, not `in (one value)` | MariaDB only uses the first column of a two-column index for an `IN` list |
| 13 | DEF-6 was applied to `filter_options()` as well as `person()` | The same leak, the same rule: a store's HR person would otherwise still see no-branch colleagues' departments and managers |
| 14 | The badge count is on `get_portal_context`, not a new endpoint | AC-31 wants it at page load; the strategy named no endpoint for it, and this adds no call |

### Tests run in this round (test_site, one at a time)

| Module | Result |
|---|---|
| `test_invoicing` | the DEF-1 test passes; the 11 pre-existing "more than one company" failures the test engineer classified are unchanged |
| `test_leader_indexes_012` | 6 OK |
| `test_morning_checks_edges_012` | 16 OK — including the DEF-2 test, now a passing test, not an expected failure |
| `test_morning_checks_012` | 17 OK |
| `test_data_review_012` | 24 OK (one new DEF-5 test) |
| `test_data_review_page_012` | 5 OK (one new DEF-3 test) |
| `test_attendance_scope_012` | 9 OK (one new DEF-6 test), after fixing my own fixture |

Re-run once slice 010 freed the bench, after the last two performance commits (bc65d50,
5aad1ae), one module at a time: `test_org_figures_012` 18 OK, `test_hr_analytics_scope_012`
10 OK, `test_data_review_012` 24 OK, `test_morning_checks_012` 17 OK,
`test_morning_checks_edges_012` 16 OK, `test_data_review_page_012` 5 OK,
`test_attendance_scope_012` 9 OK. **Everything from fix round 1 is in local `dev`.**

### Still not done after this round

1. The whole-suite run (the test engineer's next step).
2. OPS-64's separate 400 / 1,000 / 2,000-person sites, 2,000 itself, and the index-migrate
   timing (AC-5). The quiet 1,000-person run is done and inside budget (above).
3. Browser checks: 360 px, 200% zoom, keyboard through the confirm dialog, desk links.
4. `_population` (the Attendance Insights organisation list, decision D-6) still lets a
   location HR user count no-branch colleagues. DEF-6 fixed the two calls that show a
   person's days and the filter lists; changing `_population` would break slice 011's
   pinned test, so it stays a recorded decision for you.
5. Draft copy still waiting on the UX designer (BA-Q5, BA-Q12, the D18-2 dialog).

---

## 13 · Fix round 2 (2026-09-16) — DEF-8

**DEF-8:** the Attendance Insights organisation list (`_population`, view "organisation")
read Employee with no branch filter. Frappe's User Permissions are not strict on this site,
so an employee with an **empty** branch passed a Branch permission: a store's HR person got
head-office colleagues with their names, days present and absent, late and short days and
their **leave types** — more than `person()` ever showed, and `person()` had just been made
to refuse those same people (DEF-6). Two screens, two rules.

**Commit c78efcd.** `_population` now uses the same `_linked_branches()` helper: a caller
with Branch permissions sees those branches, and an employee with no branch is outside them.
Asking for a branch outside the caller's own is refused with one `SEC-17` security line
rather than quietly returning nothing. Frappe's strict user permissions were **not** switched
on site-wide.

### Slice 011's decision is untouched — checked, not assumed

`_linked_branches()` returns `None` for anyone with no Branch permission, and the code only
narrows when it returns a list. I read slice 011's three pinned tests before changing
anything:

| Pinned test | Caller | Effect |
|---|---|---|
| `test_central_hr_sees_every_store_in_the_portal_view` | `hr_user("BSPortalCentral")` — no Branch permission | untouched |
| `test_system_manager_alone_still_sees_every_store_in_the_portal_view` | System Manager, no Branch permission | untouched |
| `test_store_hr_sees_only_their_store_in_the_portal_view` | store HR with a Branch permission; both employees in the test **have** branches | same assertions, still pass |

`test_branch_scope` ran green (11 OK) after the change, so this is measured, not argued.

### Tests run (test_site, one at a time, bench claimed)

| Module | Result |
|---|---|
| `test_attendance_scope_012` | 13 OK — 9 from before plus 4 new DEF-8 tests |
| `test_branch_scope` (slice 011's pins) | 11 OK |
| `test_attendance_analytics` | 17 OK |
| `test_personas_012` (test engineer's) | 17 OK |
| `test_org_settings_allowlist_012` | 10 OK |
| `test_attendance_correction` (imports the same module) | 51 OK (42 + 9) |

The new tests name DEF-8: store HR see their own store and neither another store nor anyone
without a branch; asking for another branch is refused and logged; central HR and System
Manager still see everyone, people with no branch included.

---

## 14 · Fix round 3 (2026-09-16) — after the three reviews

Three fixes the user approved. The other review findings are recorded, not fixed here.

| # | Commit | What changed |
|---|---|---|
| M1 (code review, Major) | acbcaa5 | Opening Data to review had **no limit**, although it writes: it re-checks leave and leavers for the caller's scope and saves what changed, so a loop of calls would write documents and change-history rows as fast as it could ask. Confirming was already 30 an hour per user; reading is now **120 an hour per user** through the same helper. Generous on purpose - normal use is a handful of opens - and counted per user, so a busy office behind one address cannot lock itself out. This is OPS-40's read half |
| F3 (security, Minor) | 0fd66bd | `get_hr_analytics` no longer selects **gender** for the ten newest joiners. Checked first that nothing reads it: the page's table renders name, role, team and joining date, and `recent_employees` has no other consumer in the repo. The gender ratio card is untouched - it counts people, it does not name them |
| F4 (security, Minor) | 0fd66bd | The same answer carries names, roles and joining dates, so it must not sit in a browser or proxy cache |

### F4: what I did, and why

**Both halves: POST only, and `Cache-Control: no-store`.**

- **POST only** (`@frappe.whitelist(methods=["POST"])`, as the two Data to review calls already
  are). Safe for every caller: the portal asks through `frappe.call`, which posts, and the
  tests call the Python function directly. A GET is what a browser or proxy would cache, and
  what a link or a history entry could repeat, so closing it is the stronger half.
- **`no-store` on the response**, because POST answers can still be stored by an intermediary
  that was told nothing, and because the header says the intent plainly to the next reader.

Doing only one would have left a gap: the header alone still allows a cacheable GET, and
POST alone relies on every proxy behaving.

### Tests run (test_site, one at a time, bench claimed, `pgrep` checked)

| Module | Result |
|---|---|
| `test_data_review_012` | 26 OK (25 + 1) — includes the new read-limit tests |
| `test_hr_analytics_scope_012` | 12 OK (7 + 5) — includes the new F3 and F4 tests |
| `test_personas_012` | 17 OK |
| `test_data_review_page_012` | 5 OK |
| `test_endpoint_entitlement` | 13 OK |
| `test_portal_call_paths` | 7 OK |
| `test_morning_checks_edges_012` | 16 OK |
| `test_portal_csrf` | 4 OK |
| `test_portal_security_010` | 50 OK |

One red on the way: my own F3 test matched the word "gender" in the comment I had written
beside the field list. It now reads the field list itself (commit 2db1d71).

### Recorded, deliberately not fixed in this round

F1 (`set_cover_setting`, the org-chart settings door) and F2 (review-item counts through desk
or REST) are before-`main` items; m1, m2, m3, m8, m9 and m10 from the code review, and the
AC-32 spec fix, are for the analyst and later rounds. None of them is a two-line change I
would slip in beside these.

