---
slice: 090-leadership-hr-analytics
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-11-24
status: built and tested on the LOCAL stack only. Not pushed. No deploy command run. No dev or production server touched.
tier: 1
built_on: worktree .claude/worktrees/090-leadership-hr-analytics, branch slice/090-leadership-hr-analytics, based on origin/dev 0a181d05 (origin/dev was 0 commits ahead of my base when I finished: nothing came in)
---

# 090 · People trends: implementation notes

Labels: **proven** (a test or command run this session), **inferred**, **not checked**.

## 1 · What I built, file by file

| File | Mechanism | Why |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/people_trends.py` (new) | **Build.** Two POST endpoints (`get_people_trends`, `save_people_trends_period`), `leader_scope()`, `make_role()`, window and bin maths, people / early-leaver / attendance / leave figures, the hiding rule as class `Rule` (parts A to D), the headline sentence | Nothing existing had the leader scope, the windows or the hiding rule |
| `alvoraa_portal/alvoraa_portal/hooks.py` | **Configure.** `make_role` added last in `after_migrate` and in `after_install` | Role made on every migrate and on a new tenant. No `patches.txt` line (a migrate hook runs every time) |
| `.../templates/includes/ess/parts/people-trends.html` (new) + 1 line in `www/hrms-employee.html` | **Extend** the portal's `ess_part` pattern | Panel shell and styles (portal tokens only) |
| `.../public/js/ess/people-trends.js` (new) + 1 `<script defer>` line in `hrms-employee.html` | **Build**, prefix `pt` | Draws the answer. Keeps `portal.js` almost untouched |
| `.../templates/includes/ess/frame.html` | **Extend** | One sidebar item "People trends" |
| `.../templates/includes/ess/parts/drawers.html` | **Extend** | One phone bottom-bar item "Trends" (found in `drawers.html`, not `frame.html`: closes risk R6) |
| `.../public/js/ess/portal.js` | **Extend**, 4 small edits | panel loader line in `switchPanel`; `window._roles.leadership` from the context's `roles`; nav shows for Leadership; the Management heading shows for Leadership |
| `.github/workflows/deploy.yml` | **Extend** (OPS-29) | `people-trends.js` added to "Portal assets must be served". The automatic Deploy runs `main`'s copy of this file, so the new line gates production only after the release that carries it |
| `scripts/check_tag_balance.py`, `scripts/run_dom_tests.js` | **Extend** | Pin the new part's depth (0); list the new DOM test and move the expected count 28 to 29 |
| Tests (new): `tests/test_people_trends_090.py` (48), `tests/test_people_trends_http_090.py` (5), `tests/test_people_trends_property_090.py` (2), `alvoraa_portal/tests/people_trends_090_dom_test.js` (17 checks) | | |

**Not changed (proven by `git diff --stat`):** `org_figures.py`, `access.py`, `hr_api.py`, `attendance_analytics.py`, nginx, any DocType JSON, `patches.txt`, the old HR Analytics panel. I import `condition`, `rate`, `COUNTED`, `data_up_to`, `open_doubtful_counts`, `employee_condition` and `_OPEN_DOUBTFUL` from `org_figures` (one definition of "left out" and of the rate).

## 2 · Decisions that changed the plan while building

1. **R1 (the 730-day attendance scan) missed its pass mark.** Surbhi chose option 1 on 24 Nov: group populations come from Employee, not a two-year Attendance scan. The per-period Attendance query stays, capped at window plus comparison window. No cache. So **attendance is shown exactly when the people figures are shown** (the same people stand behind both). Leave types still use the people who took each type (one query over 365 days of On Leave rows only).
2. **A login that holds an HR role and Leadership is refused in v1** (BQ-2: HR off). AC-7 says "scope equals `hr_scope()`"; that waits for US-19.
3. **`HR_ROLES` is copied, not imported.** `scripts/check_app_integrity.py` reads only functions and classes from `access.py`, so importing the constant fails the gate. The copy has a comment pointing at the source.
4. **One log line per call, refusals included.** A refusal writes my one line (outcome `refused`, rule id) and does not also call `log_refusal`, so the file holds one line per call (AC-16, AC-19).

## 3 · Local timing, and the check that is still owed (OPS-23, OPS-28)

Stack: my own `alv090-*` containers on an Intel Mac. Seed: 600 invented staff, 438,000 Attendance rows over 730 days (more than DTC's real ~1 year), production indexes. Scripts: `~/hrlocal-data/slice090/step0/` plus `/private/tmp/.../scratchpad/full090.py`. **This stack is about 8x slower per row than the production-class figure in the older notes** (the existing HR Analytics 30-day figure took 0.18 to 0.25 s for 18.6k rows here, against 29 ms for 26k rows recorded earlier). That 8x is a measured calibration of this stack, not a claim about production.

Whole endpoint, warm, one at a time (statements the module sent: 6, plus 3 to 4 inside `org_figures`):

| Chip | Server time here | Response size |
|---|---|---|
| 1 week | 1.6 s | 2.3 KB |
| 1 month | 1.1 s | 2.2 KB |
| 3 months | 2.0 s | 2.8 KB |
| 6 months | 4.1 s | 2.3 KB |
| 1 year | 6.9 s | 2.7 KB |

Five 1-year calls at once: about 12 s each on this stack. Employee populations: 11 ms.

**Still owed:** the 6-month and 1-year timing on the DTC-size dev copy, on a throttled 3G profile (OPS-23, AC-115), by Surbhi's word for a dev tenant. If 6 months or 1 year miss 3 s there, it comes back to Surbhi as a decision. No cache was added and none is proposed. **Not checked:** MariaDB version and buffer pool on production; gunicorn worker count; five concurrent calls on production-class hardware.

## 4 · Acceptance criteria: how each is met, and the ones I could not meet

Proven = a named test passes now. Break-tested = I broke the code, watched that test fail for the right reason, and restored it (committed first).

| AC | Status |
|---|---|
| AC-1 to 6, 121 (scope, role, hook twice) | proven (`TestScopeAndRefusals`). AC-6 break-tested: removing the narrowed-branch check failed `test_scope_table` |
| AC-4 (no figure query for "not set up") | proven (`_people` patched to raise) |
| AC-7 | **not met as written**: HR + Leadership is refused in v1 (decision 2) |
| AC-8, 9 | proven (`test_the_role_adds_no_rows_anywhere`, `test_leadership_is_still_refused_the_organisation_attendance_view`) |
| AC-10 | proven (own record Left, then refused). Removing the role / permission paths are covered by the scope table, not a second walk |
| AC-11 to 15, 19, 20 | proven over real HTTP in the WSGI app (`test_people_trends_http_090.py`). The CSRF test needs the token saved the way a live request saves it, because Frappe skips saving it under test (found, commented in the test); without that, the test passed on a missing check |
| AC-16, 65 (one line per refusal) | proven, line read from the file |
| AC-17, 18 | proven |
| AC-21 | no `ignore_permissions` in the module (0 occurrences, asserted). SQL takes values as parameters; a quote in a branch name is refused. Baseline command for the whole app: `git grep -n ignore_permissions -- 'alvoraa_portal/alvoraa_portal/*.py' ':!*/tests/*'` gives 362 lines at this commit |
| AC-22, 117 | proven by a source check (no `frappe.cache`, no `scheduler_events`); no DocType, field, patch, queue, nginx edit in the diff |
| AC-23, 24 | proven (no file method; nothing in `alvoraa_goals` imports the module) |
| AC-25 to 31 | chips and one request per tap: DOM test. Dwell save 2 s and last answer wins: written in `people-trends.js`, **dwell and out-of-order not covered by a test** |
| AC-26, 27, 28 | AC-26 and clipped window proven; AC-27's exact sentence text and "6 months, 2 x 180 > 313" not separately tested |
| AC-29, 30 | proven server side (save, reopen, per user, bad value refused) |
| AC-32 to 37 | proven (company figures, identity for every chip and cut, edges, future relieving date). The old-card comparison in AC-37 not run |
| AC-38 (no success/danger colour) | not met by test; the panel uses no such class (inferred from the CSS) |
| AC-40 to 44, 53 | proven (shown cells, four-stretch hiding, whole company only, one chip never has a finished cohort). The production counts (21, 297, 163, 46) are not fixed cases; the generated tenants and Kavya/Other cover the rule |
| AC-45 to 52, 54, 55, 57, 58, 59, 60 | proven (`TestTheGroupRule`, the property test). AC-45 and AC-48 break-tested in part; AC-60 determinism is by construction (sorted, ties by name) and not a separate test |
| AC-61 | proven (same statement count at 3 and 30 branches, at most 30) |
| AC-62 (PRIV-13 property) | proven over 300 generated tenants at minimums 3, 5 and 10. **Break-tested twice:** (1) a `Mutant` rule with part C's "together they pass" removed is caught inside the suite; (2) I deleted `while len(hidden) < 2 or not together()` from the real rule and `test_the_real_rule_holds_at_every_minimum` failed. A real finding on the way: when every sibling is hidden and the parent itself fails, the union fails but nothing is shown to subtract from; the property now says so |
| AC-72 to 75 | bins and chart totals proven. `role="img"`, the text label, the table fold and 12 px text are written; DOM test checks the label is present, not the 12 px |
| AC-76, 77, 79, 82, 83 | proven against `org_figures.attendance_figures` (same rate and same `on_leave`, drafts and an Open doubtful day left out). A real bug found by the window-edge test: `to_days` offset was off by one day |
| AC-85, 86, 87, 122 | proven for the fold, "not named under a filter", and "a type taken by one person is never named". AC-87 (headline never names "Other") not separately tested; the code skips an unnamed top type |
| AC-88 | proven (count only) |
| AC-91, 92 | partly proven (headline text for the fixture). The "clause left out when withheld" is covered by the DOM test for tiles, not by a headline test |
| AC-93, 94 | proven (alphabetical; hidden companies and their list entries) |
| AC-95 to 100 | DOM test covers error with PT-LOAD, refused filter, not set up, not shared, why sheet and Escape. **Not tested:** the 300 ms skeleton timing, the offline line, "No people" |
| AC-101 | not built (HR); AC-102, 103 proven |
| AC-104 | proven by diff (no nginx, no route); page pins test |
| AC-105 | the nav shows by role in `portal.js`; the portal context cache is cleared on a User save (read in `hr_api.py`). **Not run in a browser**, so the hour-long wait question stays unanswered |
| AC-106 | **not checked**: no browser at 360 px, 200% text or target-size measure was run. The CSS sets 44 px targets and `--fs-md` form fields |
| AC-107 | partly: radiogroup, labels, focus return for chips, sheet focus and Escape are in the DOM test. **Not tested:** screen-reader live region wording by a reader |
| AC-108 | proven in the DOM test for `localStorage` and `sessionStorage`; cookies not checked |
| AC-109 | the two-year sentence is in the sheet (DOM-tested); "How counted" wording is mine, based on 01b |
| AC-110 | proven by diff: `hr_api.py` is untouched |
| AC-111, 112, 113 | proven for names, ids and the key allowlist; SQL text is checked for the banned tables and fields |
| AC-114 | proven (adding 400 people to one branch changed the payload by under 10%) |
| AC-115 | **owed** (section 3) |
| AC-116 | the slow-call line is coded (`Call.log` warns above 2 s); **not tested** |
| AC-118 | proven (HR refused). AC-119, 120 (US-19) **not built**, by decision |

## 5 · The seven dimensions, re-assessed against the code I wrote

| Dimension | Before (proposal) | After (the code) | Why |
|---|---|---|---|
| Performance | neutral with a watch item | **neutral for existing screens; slower-than-budget on this stack for 6 months and 1 year** | Fixed statement count (6 in the module, about 10 with the shared helpers, ceiling 30 proven). Attendance reads window plus comparison: 1.1 to 6.9 s here (section 3). The 3 s budget is not proven on a DTC-size copy yet |
| Security | improves | **improves** | Server-side scope worked out on every call, fail closed, POST plus CSRF plus role plus plan, filters refused not trimmed, no new `ignore_permissions`, one log line per call from a proven sink. Residual: `get_user_permissions` is Frappe's own cached read, cleared when a User Permission changes |
| Reliability | neutral | **neutral** | Read only. Generic PT-LOAD message; the Error Log gets the exception type only (tested). A User Permission read that fails would give "not set up" or an error, never figures |
| Scalability | neutral, one watch item | **neutral, same watch item** | Employee rows grouped by non-identifying columns (grow with distinct combinations); Attendance is the cost that grows with months and headcount. No job, queue or cache was added |
| Maintainability | neutral | **neutral to slightly worse** | One 865-line module (including long docstrings) and one 311-line script. A second definition of "leader scope" (as planned). One copied constant (`HR_ROLES`) and one imported private name (`_OPEN_DOUBTFUL`) |
| Data integrity | neutral | **neutral** | No cache, so no stale figure. END fixed once per call. Known limits: a rehire counts as a leaver plus a joiner; a person who moved branch sits under the old branch in attendance and the new in people figures |
| Compliance / privacy | improves, residual risk | **improves, residual risk unchanged** | Totals only, minimum read fresh on every call, hidden means not sent, property-tested. One honest weakening: attendance rides on the people populations rather than its own (decision 1), so it is no stricter than the people family. R1 to R10 in 01c are not accepted; counsel questions CQ1 to CQ3 are open |

## 6 · NFR notes

- **Statements per call:** 6 in the module plus `data_up_to` (1 per company), `open_doubtful_counts` (1), the minimum (1): about 10. The 3 vs 30 branch test shows the count is the same.
- **Indexes added:** none. **Background jobs:** none. **Cache:** none. **Schema:** none.
- **Permission enforcement points:** the whitelist decorator (POST), `requires_feature("analytics")`, `_caller()` (role, HR refusal, own Employee status), `leader_scope()`, filter checks against the Employee rows already in scope.
- **Sensitive fields touched:** `leave_type` on Attendance, read only for part D. Never read: `reason_for_leaving`, Leave Application `description`, Salary Slip, Employee Checkin (asserted on the source text).
- **Logs:** `{event, at, user, role, period, ms, outcome, statements, rule}`. No figure, company, branch or filter value (read back from the file in the HTTP test).
- **Role:** `make_role()` sets `desk_access = 0`. The 012 tests create the role with Desk access on; my tests call `make_role()` first. Dev and production hold no Leadership role and no holders (read by Surbhi, recorded in 07), so the hook takes Desk from no one. **Test order:** my files pass alone; run after the 012 files they still pass (the 012 tests insert the role only when missing, and mine fix it), but I did not run all 012 files before mine in one process: **not checked**.
- **Data used in tests:** invented employees (`last_name = P090`), removed at module end. Test users take no password in the unit tests; the HTTP test sets a generated one.

## 7 · Commands run and what they said

| Command | Result |
|---|---|
| `bench --site test_site run-tests --module ...test_people_trends_090` | 48 tests OK |
| `... test_people_trends_http_090` | 5 tests OK |
| `... test_people_trends_property_090` | 2 tests OK (87 s) |
| `node alvoraa_portal/tests/people_trends_090_dom_test.js` | 17 checks OK; two break tests failed for the right reasons |
| `python3 scripts/check_app_integrity.py` | OK (it first failed: the `HR_ROLES` import, fixed) |
| `check_portal_assets_gate.py` (and `--self-test`), `check_tag_balance.py`, `check_brand_spelling.py`, `check_api_paths.py --max 0`, `check_no_demo_passwords.py`, `check_undefined_js.js`, `check_portal_handlers.js` | all OK |
| `node scripts/run_dom_tests.js` | 29 run, 1 failed: `portal_leave_063_test.js` "R-88: should not show <15>". **Fails the same on a detached checkout of origin/dev** (proven), so it is not mine; it looks date-dependent |
| `check_design_system.py` | one failure, **pre-existing on origin/dev**: `999px` in `panels.css` (`.myp-need`, another slice) makes 4 radii against a limit of 3. My part adds no radius value of its own (uses `var(--r)`, `var(--r-sm)`, `var(--r-full)`), after I removed one `16px` of my own |
| `check_scope_traps.py` | the host's Python cannot parse `employee_ctc_break_up.py` (f-string), so the script reports a fail on that file; my files are not named. **Not run on a Python that can parse it** |

## 8 · What else moved while I worked

I fetched `origin/dev` at the start, before the hot-file edits and at the end: **0 commits ahead of my base each time after the first rebase** (the first fetch brought in three ALV-436 commits that touch `punch_fix.py`, `register_notice.py` and their tests, none of which I touch). The 086 worktree has uncommitted edits in `portal.js` (per the coordinator); I never touched that folder. My four `portal.js` edits are small; a conflict there on rebase means keeping both sides.

## 9 · Known gaps and shortcuts

| Gap | Label |
|---|---|
| 6-month and 1-year timing on the DTC-size dev copy, and 3G timing | **temporary debt**, owed (OPS-23). Removed by that run |
| US-19 (HR) not built; HR + Leadership refused | **intentional trade-off** (BQ-2) |
| Attendance population = people on the roll, not people with attendance rows | **intentional trade-off** (decision 1) |
| No browser check at 360 px / 200% text / real target sizes (AC-106), no screen-reader pass | **temporary debt**. Removed by a manual browser check before dev |
| 300 ms skeleton, offline line, "No people", dwell save and out-of-order answers not covered by a test | **temporary debt** (small) |
| Test order against the 012 files in one process not run | **temporary debt** |
| `_OPEN_DOUBTFUL` imported by its underscore name; `HR_ROLES` copied | **acceptable simplification** |
| `check_design_system.py` and `check_scope_traps.py` do not pass locally | **Corrected in fix round 1:** the design-system failure was mine (two `border-radius:4px` in `people-trends.js`); it now passes. `check_scope_traps.py` still not run (see section 10) |
| Part B for chart bins uses the people on the roll in each bin | **acceptable simplification** of "a bucket's own population" |
| Dates in the panel use the browser's locale, the server sentence is English | **acceptable simplification** (English only in v1) |

**Subtract pass (my own output):** I removed an attendance-population query, a second hiding rule for attendance, and a `Rule` argument for an attendance own-record key after the R1 decision; I did not remove anything else. Nothing was left that the requirement does not need except the PRIV-7 one-line guard, which is the requirement.

## 10 · Fix round 1 (24 Nov 2026): what changed after the three reviews

Built on worktree `.claude/worktrees/090-leadership-hr-analytics`, branch `slice/090-leadership-hr-analytics`, rebased onto `origin/dev` 640cd1f5. Each fix has a test; each was break-tested (the fix undone, the test watched failing for its own reason, the fix put back after a commit). Labels: proven / inferred / not checked.

| # | Finding | What I did | Break test (proven) |
|---|---|---|---|
| 1 | B1 / F2 hidden bucket still sent series | `_build`: `series_ok = chart["shared"]`. When the bin rule fails, `attendance.series` and `leave.series` are not sent (keys absent). The Attendance and Leave cards say "Not shared". Also removed `chart.total` (never read) | `test_a_failing_bucket_sends_no_series_at_all` failed with `series_ok = True` |
| 2 | F1 subtraction leak | Attendance, leave days and pending now join Employee and count only people the rule counts (`COUNTED_SQL` = `_counted` in SQL), cut by the Employee's company, branch, department and type, not the row's branch tag. Total and checked set are now the same set. Chosen because the Employee join already existed for department and type, and it is the one change that closes all three kinds. Rows are added up per person first and the Employee joined after, so the join runs per person, not per row | Three tests, one per row kind (blank tag, tag nobody holds, Inactive staff): company figures equal the sum over the shown branches. Undoing the "counted people" part failed the Inactive test; cutting the branch by the row tag failed the other two |
| 3 | M2 guard (Surbhi, 24 Nov) | `_attendance_bins` also returns how many people stand behind each bucket. If any bucket (or the comparison window, or a company on the By company card) has 1 to 4 people with rows, attendance is `{"shared": False, "reason": "few_attending"}` and no number or series is sent. Recorded in 02 under "Decisions after review". Whole-or-nothing was chosen so the window figure minus the shown buckets cannot give one bucket away. **This hides more than "a bucket" literally: one thin day hides the whole Attendance card for that chip.** Say if you want a softer rule | `test_attendance_is_shown_only_when_five_people_have_rows` failed with the guard off |
| 4 | B2 website `frappe.call` | `people-trends.js` uses `fetch("/api/method/...")`, POST, `X-Frappe-CSRF-Token`, real status codes: 403 gives the PT-SCOPE page at once, any other status or a dropped connection gives PT-LOAD at once (no 15 s wait). The DOM fakes now return real status codes; the fake throws if `frappe.call` is used | Old file put back: DOM test threw "frappe.call used". `status 403` mapping broken: two checks failed |
| 5 | design system "4 radii" | `var(--r-sm)` in place of `4px` | `check_design_system.py`: OK |
| 6 | M3 / F3 | Types are sorted and folded by the 365-day total, so the named list is the same on every chip. The headline names a type only if its days are more than Other's | Two tests; each failed with the old line back |
| 7 | m1 nav | `ptShow` needs `roles.leadership && !roles.is_hr` | A source-pin test failed with the old line back (a pin, not a browser check) |
| 8 | deletions | `after_migrate = make_role` alias, `scope.branches_only`, `scope.several_companies`, `chart.total`, the dead `labels` line in the Attendance card | `check_app_integrity.py` OK; no test read them (grep) |
| 9 | F4 `records_start` | **Not changed.** In a clipped window it equals the window start (AC-27 draws it), and the sentence "your records start on {date}" is in the approved prototype; changing it needs Surbhi's yes (prototype parity). Written in 02 as open | none |

Also: the test engineer's gap DOM test is committed with this round. It found a real fault, which I fixed: table text at 11 px (`--fs-xs`) in the panel CSS, now `--fs-sm` (AC-74). `test_the_log_line_is_in_the_file_and_holds_no_figure` was flaky (it looked for the digits "43" anywhere in the line, including the time stamp; it failed 1 run in 3). It now checks values.

**Seven dimensions after this round.** Performance: **degraded, measured** (see below). Security / privacy: **improves** (B1, F1, M2 closed on the server; page now uses the `/api/` path with CSRF). Reliability: **improves** (a refusal and a failure now reach the page at once). Scalability: neutral. Maintainability: neutral to slightly better (dead keys removed; one SQL constant duplicated from `_counted`, pinned by the three subtraction tests). Data integrity: **improves** (total and checked set are one set). Compliance: improves; R11 and the attendance guard are now Surbhi decisions, not yet written as risk acceptances.

**Speed, measured on my 8x-slow stack (inferred only for production):** heaviest call, 1 year, one company, 438,000 attendance rows: before this round 5.0 s, with a per-row Employee join 10.0 to 11.2 s, with the join after per-person addition **6.3 to 7.2 s** (+25 to 40 percent). Dividing by the stack's 8x figure gives about 0.8 to 0.9 s (inferred). 90 days: 1.35 s before, 2.55 s with the per-row join; not re-measured after the last change. Statement count is unchanged (6 in `_build`). The multi-company path and the DTC-size copy are still **not measured** (OPS-23 stays owed).

**What came in with the rebase:** 23 commits, all slice 086 by the same account (manager Held view): `held_team.py` (new), `attendance_correction.py`, `punch_fix.py`, `field_app_limits.py`, `hooks.py` (2 lines: an `on_trash` hook), `portal.js` (about 425 lines added, none in my hunks), `panels.css`, `check_portal_trays.js`, `run_dom_tests.js`, 086 tests and docs. I read the code diff for hidden code (no `eval`, no encoded text, no long lines). The only conflict was `EXPECTED_BROWSER_TESTS` in `scripts/run_dom_tests.js` (both sides 28 to 29); it is now **31** (28 on the base + 086 + my two files) and the runner reports 31 run, 0 not run, 1 failed. The one failure is `portal_leave_063_test.js` "R-88", which failed the same on a detached `origin/dev` before the rebase (proven then, date-dependent); not mine.

**Commands, after the rebase:** `test_people_trends_090` 57 + 2 (two batches) OK; `test_people_trends_http_090` 1 + 5 OK (6 repeat runs after the flake fix); `test_people_trends_property_090` 2 OK; `people_trends_090_dom_test.js` 22 checks ok; `people_trends_090_gaps_dom_test.js` 16 ok. Gates OK: integrity (1036 checks), design system, tag balance, assets gate (and self-test), brand spelling, api_paths, undefined_js, portal_handlers, no_demo_passwords. **Not run:** the full suite (told to wait), `check_scope_traps.py`, a browser at 360 px, 086's own tests against my branch, the 012-then-090 order.

**Known gaps added:** the property test (`test_people_trends_property_090.py`) still covers only the people family; the three F1 cases are plain subtraction tests, not generated ones (**temporary debt**). The M2 guard counts people per bucket for one filter at a time; no test for the By company card's guard (**temporary debt**).

## 11 · Fix round 2 (24 Nov 2026): the last round

Built on worktree `.claude/worktrees/090-leadership-hr-analytics`, branch `slice/090-leadership-hr-analytics`, rebased onto `origin/dev` a269ce00. Labels: proven / inferred / not checked. Each fix has a test, and each was break-tested (the fix undone, the test watched failing, the fix put back after a commit).

| # | Finding | What I did | Break test (proven) |
|---|---|---|---|
| 1 | G1 (security P1): "All companies" minus each company could leave a mover's rows unchecked | `_rows_of_counted_people` now also needs the row's company to be the person's Employee company (`x.company = e.company`; `l.company = e.company` for Pending). The attendance and leave queries group by the row's company too, so the match is per row company. Applies to attendance, leave days, leave types and pending | `test_all_companies_is_the_sum_of_the_companies_for_a_person_who_moved` failed with the line removed |
| 2 | N1 / G2: the attendance check counted the leader | `_attendance_bins` takes the caller's Employee name and subtracts it from the count of people (also on the By company card) | `test_the_guard_leaves_the_caller_out` failed with the subtraction removed |
| 3 | Softer guard (Surbhi, 24 Nov) | A bucket with 1 to 4 people loses only its own point (`series[i]` is `None`, `attendance.hidden` lists the index). The window figure stays when at least one bucket has 5 or more. The whole card is withheld only when no bucket has 5 (`few_attending`). A comparison with 1 to 4 people loses only its `before` figure. The page shows "Not shared" for the hidden point in the table and says why under the chart | `test_a_thin_bucket_loses_only_its_own_point` and (next row) |
| 3b | Can the hidden bucket be got back as window minus shown buckets? | **Yes for exactly one hidden bucket** (the window percent, less the shown bucket percents, weighted by roughly known expected days, gives that bucket). So with exactly one hidden bucket the window figure is hidden too (`window_hidden`, the tile says "Not shared"; no number, no headline clause). **Leave days are not affected:** leave figures follow decision 1 (about everyone on the roll, R11), so the leave series is sent for every bucket the people rule passes. **Residual, not closed:** with two or more hidden buckets, the window figure less the shown buckets gives a rough pooled estimate of the hidden ones (needs expected days, which are not sent). This is R15; I judged it weaker than the single-bucket case and kept Surbhi's rule for it. Your call if you want it hidden whenever any bucket is hidden. | `test_one_hidden_bucket_also_hides_the_window_figure` failed with the carve-out removed |
| 4 | Absence % counts people expected at work | The person count is people with at least one Present, Work From Home, Half Day or Absent row in the bucket. A person on leave all bucket does not count | `test_absence_counts_only_people_expected_at_work` failed with every row counted |
| 5 | Records start: month and year only | The response sends the first of the month for `records_start`; a clipped window starts on the first of that month too, and `days` is counted from it. People figures are the same (nobody joined earlier in the scope). The page says "Records start in Mar 2026." AC-27 and its test changed | `test_records_start_is_a_month_never_a_day` failed with the day sent; the DOM check failed with the old sentence |
| 6 | F5 admin line, AC-10 | Written in 02 section 13 (rollout, where the admin steps live; there is no separate admin guide in the repo, checked by grep of `docs/`). AC-10 now says removing only the Branch permission widens a branch head to the whole company | none (words) |
| 7a | `check_portal_trays.js` inventory | Added `#pt-sheet-scrim` (dialog, opened by script) and `#pt-sheet` (a bottom sheet placed by script) | `--static` failed with both missing (before the edit: 2 problems), 0 now |
| 7b | `test_portal_split_034` expected set | Added `js/ess/people-trends.js` | failed with the line removed |
| 7c | `test_browser_call_args_045` | Taught the scanner a fourth call shape, `post(CONST, {...})`, so both People trends endpoints are read (and `period` is checked against `save_people_trends_period`). Nothing was weakened. Floor raised 201 to 203 (235 sites read now, counted in the container) | `test_no_endpoint_is_named_but_never_read` failed with the shape removed |
| 8 | Decisions recorded | 02, "Decisions after review (24 Nov 2026)": softer guard, expected people, records start, G1. F4 is closed | none |

Also: `test_people_trends_final_090.py` (the test engineer's file) failed when run alone (`no attribute lead_retail`: it did not import the module's tenant set-up). I added the two imports. It passes alone now.

**Commands, after the rebase onto a269ce00 (all on my worktree in `alv090-bench`, run after the test engineer's run had ended):**

| Command | Result |
|---|---|
| `test_people_trends_090` | 62 + 2 (two batches) OK |
| `test_people_trends_http_090`, `test_people_trends_final_090`, `test_people_trends_property_090` | 5 OK, 3 OK, 2 OK |
| `test_portal_split_034`, `test_browser_call_args_045` | 12 OK, 6 OK |
| `people_trends_090_dom_test.js`, `people_trends_090_gaps_dom_test.js` | all ok (two new checks in the first) |
| `node scripts/run_dom_tests.js` | 31 run, 0 not run, 0 failed (the R-88 date failure is gone with 80dc5cbf) |
| Gates | integrity (1038 checks), design system, tag balance, assets gate, brand spelling, api_paths, undefined_js, portal_handlers, no_demo_passwords, `check_portal_trays.js --static` (35 of 35): all OK |
| **Not run** | `check_scope_traps.py` (the host Python cannot parse one file, as in round 0), the full suite (the orchestrator's), a real 360 px screen, a real browser |

**Rebase intake:** 7 commits came in, none in my files: ALV-440 (4 commits: `data_review.py` +674 lines, `hooks.py` +8, `portal.js` +22, the DocType JSON, `test_punch_feed_alv440.py`), `a269ce00` (a read-gate fix), 091's product brief (docs only), `14a9d115` (a grooming test), `80dc5cbf` (the leave card date fix). I read the diffs of the code files: no `eval`, `atob`, `Function(`, `base64`, `fromCharCode` or `\x` escapes. I did not review ALV-440's logic.

**Timing, one call, my stack (600 staff, 438,000 Attendance rows, 8x slower than production class: calibration from section 3), `_build`, 6 statements:** 6 months 4.0 to 4.2 s (round 0: 4.1 s); 1 year 6.7 to 7.0 s (round 1: 6.3 to 7.2 s). So this round added nothing measurable. Dividing by 8 gives about 0.5 and 0.85 s (inferred). Five at once and the DTC-size dev copy: **not re-measured** (OPS-23 stays owed).

**Seven dimensions, this round:** Performance neutral (measured). Security / privacy improves (G1 closed, the leader left out, the hidden bucket not recoverable for the single case). Reliability neutral. Scalability neutral. Maintainability neutral (one more argument on one helper, one more scanner shape). Data integrity improves (a row counts only for the person's own company). Compliance improves; R13 now has its admin line; R15 is the residual above.

**Known gaps:** the property test still covers only the people family (temporary debt); the By company card's guard has no test of its own (temporary debt); N2 (an expired session shows "not available to you"), N3 (a thin company's absent % on By company shows nothing, not "Not shared"), N4 (a sentence in 02 that branch history moves with the person), m2, m4 and the missing `@requires_feature` on `save_people_trends_period` were not in this round and stay open. G3 is closed by Surbhi's expected-people decision. R-numbers still need Surbhi's written acceptance.


## 12 · Fix round 3 (24 Nov 2026): H1 and N5

Built on 5eeef770, commit 703fee29 (code and tests). `origin/dev` is at a269ce00; I did not rebase.

| Item | What I did | Files |
|---|---|---|
| H1 | If any bin has 1 to 4 people expected at work, the attendance block sends no `series`. It keeps `absent_pct` (window) and `before`. `window_hidden` and `hidden` are gone from the response and the page. The page already says "The chart by period is not shared" when there is no series | `people_trends.py`, `people-trends.js` |
| N5 | On By company, if any shared company is thin, every shared company's `absent_pct` is `None`. The all-companies figure stays | `people_trends.py` (`_by_company`) |
| Decision | Recorded in 02 "Decisions after review" as Surbhi, 24 Nov 2026 | `02-functional-spec.md` |

**Can a hidden bucket still be got back across views?** I checked the bin layouts in `_bin_lengths` (read, proven).
- **Exact overlaps:** the 7-day window is the 30-day view's last bin; the 90-day window is the 180-day view's last three bins, and its "before" is the first three; the 180-day view's six bins are the 365-day view's last six. With no points on a thin view, the other view gives only what the window figure already says. Proven for 7d/30d by the new test (the 30-day last point equals the 7-day window figure, and no 7-day point is sent). 90/180/365: proven by reading the layouts, not by a test.
- **Not exact (still open, R3):** 30-day bins (8,8,7,7) and 90-day weeks (7s) do not line up (one-day sliver); 90-day weeks and 180-day months differ by three days; 365-day months (31 and 30) differ from 180-day months by a few days. A hidden bin could be estimated roughly, not exactly, from those. This is residual risk R3, unchanged. I did not close it.
- R17 is gone: with no points on a thin view, there is nothing to subtract from the window figure inside one view.

**Tests (new, all break-tested):** `test_a_thin_bucket_sends_no_points_for_the_whole_view` (replaces the softer-guard test), `test_no_hidden_day_can_be_got_back_from_two_views_together` (7d and 30d together), `test_by_company_sends_no_absent_percent_when_one_company_is_thin`. I replaced `test_one_hidden_bucket_also_hides_the_window_figure` (the rule it pinned is gone) and changed the DOM check for a thin bar. Break-test: I put back the per-bin points and the per-company hiding; `test_people_trends_090` showed 3 failures (I did not read their names; inferred these three), then I restored the file (git status clean).

**Run:** `test_people_trends_090` 63 OK (+2), `_http_090` 1+5 OK, `_final_090` 3 OK, `_property_090` 2 OK, `test_portal_split_034` 12 OK, `test_browser_call_args_045` 6 OK (all in `alv090-bench`, `test_site`). `run_dom_tests.js`: 31 run, 0 failed. Gates OK: integrity, design system, api_paths, brand spelling, no demo passwords, assets gate, portal handlers, trays static (35 of 35), tag balance, undefined JS. **Not run:** full suite, `check_scope_traps.py`, a real browser. The property test still covers only people figures (temporary debt).

## 13 · Fix round 4 (24 Nov 2026): attendance follows the people rule, all five or none

Built on f1d863e9 (security notes committed first as 457e4902); code and tests in b28a77b2. `origin/dev` is at a269ce00, which is my merge base: **nothing came in, no rebase.**

**What changed (`people_trends.py`)**
- New `_attendance_rule`: one query gives, per person, the set of buckets they were expected at work in (a bit mask built with `bit_or`), grouped by company, branch, department and type. It feeds the same `Rule` class the people figures use, so parts A to D (next-smallest subtraction, company and dimension siblings) apply with no new code. The leader is left out in the SQL.
- New `_attendance_buckets`: every bucket of all five periods plus each period's "before" window. Same list for every view, so the verdict is the same on every period.
- `_build`: attendance is shown only if `att_rule.verdict(company, dim, value, several)` is None, then it sends window, series and before. `_by_company`: a company's absent % shows only if its verdict is None.
- **Removed (subtract pass):** `_bucket_state`, the `people` column and `own` argument of `_attendance_bins`, the thin-bucket and "exactly one hidden" code in `_build`, the `_thin` flag in `_by_company`, `series_ok`/`attending_ok` for attendance. Leave still uses `chart["shared"]` for its series (unchanged).

**Tests (all break-tested: undo, named test fails, restore)**
| Test | Break made | Result |
|---|---|---|
| `test_one_thin_day_hides_attendance_on_all_five_periods` (thin day: Not shared on 7, 30, 90, 180, 365; fifth person added: all five shown) | attendance always shown | fails by name |
| `test_a_bucket_of_another_period_hides_the_short_views_too` (H2) | buckets of the 7-day period only | fails by name |
| `test_all_companies_minus_one_company_cannot_rebuild_a_thin_one` (H3) | company verdict ignores "several companies" | fails by name |
| `test_by_company_sends_no_absent_percent_when_one_company_is_thin` | by-company check removed | fails by name |
| `test_no_hidden_day_can_be_got_back_from_two_views_together` (H1), caller-left-out and expected-at-work tests | attendance always shown | fail by name |
| Property test on attendance units (PRIV-13), 300 seeds, minimum 3, 5, 10 | part C removed (`Mutant`) | the property catches it |
Reworded: `test_a_failing_bucket_sends_no_series_at_all` (attendance no longer follows the people chart; leave still does).

**Run (alv090-bench, test_site):** `test_people_trends_090` 65 + 2 OK, `_property_090` 4 OK, `_final_090` 3, `_http_090` 1 + 5, `test_portal_split_034` 12, `test_browser_call_args_045` 6, all OK. `run_dom_tests.js` 31 run, 0 failed; both 090 DOM tests ok. Gates OK: api_paths, integrity, design system, portal handlers, trays static, undefined JS, no demo passwords, tag balance, brand spelling, assets gate, `check_scope_traps.py` (on the bench Python). **Not run:** the full suite, ruff (not installed here), a real browser.

**Timing, once, 600 staff and 438,000 attendance rows, warm, this stack:** 1 week 9.2 s, 1 month 8.0 s, 3 months 8.5 s, **6 months 9.9 s (was 4.1)**, **1 year 12.3 s (was 6.9)**. 7 statements each. **This is a real cost of "all five or none":** every call now reads two years of attendance, so the short views slow down most. It misses the 3 s budget here, and it also did before for 6 months and 1 year. No cache added. A cache of the pass test per company and day would fix it; it needs your word.

**Inferred, not proven:** a person has no attendance rows before their joining date, so a view clipped to the records start has the same people as the global bucket. **Known gap (R3, unchanged):** buckets of different periods that do not line up exactly (for example 30-day and 90-day bins) can still give a rough estimate of a day, but every bucket and every window is now 5 or more people, so no exact small group can be rebuilt.
