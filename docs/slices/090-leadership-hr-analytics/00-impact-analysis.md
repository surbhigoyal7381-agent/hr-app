---
slice: 090-leadership-hr-analytics
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-11-23
status: proposal, waiting for Surbhi's approval (change-process step 3). No code written, no command run that changes anything.
tier: 1 (who sees which scope, small-group hiding, aggregates over people)
read_at: worktree /Users/mac/hr-app/.claude/worktrees/090-leadership-hr-analytics, branch slice/090-leadership-hr-analytics, HEAD 9a140875 (docs only, on top of 412d5361)
---

# 090 · People trends: impact analysis and strategy

Labels: **proven** (I read it or ran it this session), **inferred**, **not checked**.

## 0 · Where the branch stands (parallel-work check)

- `git fetch origin dev` done. Branch is **1 commit ahead, 3 behind** origin/dev (proven: `rev-list --left-right --count`).
- The 3 incoming commits are all ALV-436 (`bcb8a6f8`, `f6d91de4`, `0a181d05`). They touch four files: `punch_fix.py`, `register_notice.py` and their two tests. **None is a file I will change.** Nothing to resolve. I rebase before I start and again before I stage anything.
- Slices 088 and 089 are active (worktrees `088-register-notice-and-forms`, `089-manager-profile-edits` exist). In the last 7 days origin/dev changed `portal.js`, `frame.html`, `hrms-employee.html` and `hooks.py` in **48 commits** (proven: `git log`). Those are the four hot files I must touch. **Rule I will follow:** my edits to them are one-to-three-line additions at the end of a list, written last, right after a fresh rebase.
- The work board `.claude/work-in-progress.md` has no row for 085-089 and its newest row is 19 Nov (proven). It is stale. Surbhi: is anyone besides the 088/089 sessions in `hooks.py`, `portal.js`, `frame.html` or `hrms-employee.html`? I will add a row for 090 once you approve.

| File I will change | Hot? | Who else is in it | Plan |
|---|---|---|---|
| `alvoraa_portal/alvoraa_portal/hooks.py` | Yes | 088/089 sessions (inferred, recent commits) | Sequence: add 2 lines at the end of `after_migrate` and `after_install`, after a fresh rebase |
| `alvoraa_portal/alvoraa_portal/public/js/ess/portal.js` (26,758 lines) | Yes | same | 2 to 3 lines only (panel dispatch, nav flag). All real code goes in a new file |
| `alvoraa_portal/alvoraa_portal/templates/includes/ess/frame.html` | Yes | same | One new `nav-item` block, own id |
| `alvoraa_portal/alvoraa_portal/www/hrms-employee.html` | Yes | same | Two lines: one `ess_part("people-trends")`, one `<script>` tag |
| New files (`people_trends.py`, `people-trends.html`, `people-trends.js`, tests) | No | nobody | Own prefix `pt` |

**Pins so a bad merge cannot drop my lines:** a test that reads `hooks.py` and asserts both hook entries exist; a test that renders `/hrms-employee` and asserts the panel and nav item exist (the repo's `portal_source.py` / jsdom harness already fails on a missing `ess_part` line, proven by the comment at `hrms-employee.html` line 59-61).

## 1 · What I read this session (proven) and what I did not

Read: the whole spec, 01c sections 7-8 and the SQ-1 section, 07 sections 3 and the §2 payload notes, `org_figures.py` (whole), `access.py` (lines 20-100 and 235-330), `alvoraa_leader_view_settings.py`, `hr_api.py` lines 316-396 and 815-960, `hooks.py` after_migrate/after_install lists, `announcements.make_role`, `ess_parts.py` usage, `portal.js` around the panel dispatch and nav flags, `frame.html` nav items, `www/hrms_employee.py`. Installed Frappe on the bench image: v16.33.1; `frappe.defaults.set_user_default(key, value, user)` and `get_user_default(key, user)` exist (read from `apps/frappe/frappe/defaults.py`).

**Not checked:** any production or dev tenant; the Employee JSON (erpnext app); the phone bottom bar's file (I did not find "bottom" in `frame.html`, so P2 "Trends" in the bottom bar needs a look when I build the shell); MariaDB's query plans for my new queries (first build step measures them).

## 2 · EQ-3, the `[UNVERIFIED]` items, answered

| Item | Answer | Label |
|---|---|---|
| Does Attendance "On Leave" carry `leave_type`? | **Local data only, never production:** in three local databases (the Docker MariaDB `hrlocal-mariadb`) every submitted On Leave row has a type: 5 of 5, 1 of 1, 1 of 1. That is 7 rows, one type each. Tiny sample, demo data. **DTC's rows: not checked and I may not check.** The design already copes: no type means "Other", never named (AC-122) | proven (local, 7 rows); DTC not checked |
| Role-creation pattern | `announcements.make_role` (line 570): if the Role exists, `set_value desk_access 0`; else insert with `desk_access 0`. It is listed in **both** `after_migrate` and `after_install` lists in `hooks.py` (new tenants never run a migrate patch: the comment at the `after_install` list says so). I copy it | proven |
| **A role named "Leadership" already exists locally** | Two local databases already hold Role `Leadership`, created 18 Sep 2026, `desk_access = 1`, zero DocPerm, zero Custom DocPerm, no user holds it. Tests `test_data_review_012.py` 246 and `test_personas_012.py` 71 insert it with Frappe's default (desk access on). So my hook must set `desk_access = 0` on an existing role, not only create it. **Not checked: whether dev or production already has it, and who holds it.** Setting `desk_access 0` on a role someone holds could change what they can open. Surbhi: may I ask for a read-only count of holders on dev and production before release? | proven (local); production not checked |
| Saved-period call | `frappe.defaults.set_user_default("alvoraa_people_trends_period", value)` and `get_user_default(...)`. No new field, no DocType. Beware: `get_user_default` reads Frappe's defaults cache; a save clears it (read `set_default`, line 149) | proven (signatures); behaviour inferred |
| `attendance_analytics.summary(view="organisation")` | Name is right: `def summary(view="mine", ...)` at line 385, `@frappe.whitelist()`. `NEVER_ORG_ROLES` at line 81 already lists "Leadership" | proven |
| Translation pattern | Server: `frappe._()` as in the leader settings controller. Browser: the portal's `drT(text, args)` helper at `portal.js` 15676 (`window.__` plus `{0}` fill). The new JS file gets its own copy of the 4-line pattern, no import (portal.js is one file, not modules) | proven |
| Does `track_changes` log User Permission? | Not checked. It is a report line, not a build line | not checked |
| Who else calls `permitted_branches()` | See section 3: 13 call lines in 9 non-test files | proven (grep) |
| Does the cached `portal_ctx_<user>` go stale for a new leader? | `invalidate_portal_context_cache` (`hr_api.py` 168) clears it when an Employee or a **User** record is saved (read `hr_api.py` 168-191; the comment there says role edits go through the User form), and `hooks.py` 312, 335, 388 wire it. So the "up to an hour" in AC-105 is probably too gloomy: giving the role through the User form clears the cache. A role added by raw SQL would not. I will test it, not assume it | inferred; test written in build |

## 3 · Cross-module reach and callers

**Rung on the ladder: new code in the existing `alvoraa_portal` app** (one module, one panel), plus one Role made by a hook, plus User Permissions that a person sets. Rejected cheaper rungs: Desk number cards and the Employee Exits report cannot hide small groups and have no phone view; Insights is a second permission model and a new app (OPS-1). No new DocType, field, index, scheduled job, queue, cache, patch or nginx line.

**What I will change, and every caller I grepped (counts are non-test unless said):**

| Thing | Change | Callers (grep, `git grep` in this worktree) | Verdict |
|---|---|---|---|
| `org_figures.py` (all functions: `hr_scope`, `attendance_figures`, `people_figures`, `employee_condition`, `condition`, `data_up_to`, `open_doubtful_counts`, `rate`, `rate_with`, `log_if_slow`, `leave_figures`) | **None. Zero edits.** I import `condition`, `rate`, `COUNTED`, `data_up_to`, `open_doubtful_counts` and the doubtful-day SQL fragment, and write new grouped queries in my module | `hr_scope`: 4 call sites (`hr_api.py` 842, `data_review.py` 68, 572, 676); `attendance_figures`: 2 (`hr_api.py` 894, `data_review.py` 554); `people_figures`: 1; `leave_figures`: 4; `rate_with`: 2; `log_if_slow`: 3; 5 + 12 + 4 + 5 + 1 + 2 test references | Deviates from the spec's word "extend" on purpose: a new function beside the old one, not a signature change. Cost: my module imports one underscore name (`_OPEN_DOUBTFUL`), because one definition of "left out" is the point (AC-76, AC-77). If the reviewer dislikes importing a private name, the fix is a one-word rename in `org_figures.py` and its single internal use, as its own commit |
| `get_hr_analytics` (`hr_api.py` 821) | **None** (AC-110) | 30 references in py, js, html, tests | untouched |
| `get_portal_context` (`hr_api.py` 316) | **None.** It already returns the full `roles` list; the browser tests for "Leadership" in it | n/a | untouched |
| `access.permitted_companies` | **None** | 45 call lines in 19 non-test files, across `alvoraa_portal`, `alvoraa_goals`, `hrms`; 34 test references | Leadership is not an HR role, so it returns `[]` for them (proven, `access.py` 251-252). I write `leader_scope()` in my module instead. Touching this helper would reach goals and performance code |
| `access.permitted_branches` (R6 / ALV-359) | **None in v1** | **13 call lines in 9 non-test files** (`attendance_analytics`, `attendance_correction` x4, `frame_api` x4, `hr_api`, `inbox_api` x2, `org_structure/api`, `metrics`, `register`, `access.py` x2); 5 test references | Not changed. See BQ-2 below |
| `Alvoraa Leader View Settings` (`min_group_size()`) | **None** (read only, fresh on every call) | 1 non-test caller (`data_review.py` 217); the DocType is also listed in `subscription.py` 579 | untouched |
| `security_logger()` (`access.py` 29) | **None** (reused for the one line per call) | 7+ call sites (ALV-391) | untouched |
| `hooks.py` | +2 lines (the role hook, in `after_migrate` and `after_install`) | n/a | additive |

**Cross-module:** `hrms` (read only for Employee, Attendance, Leave Application, Company, Branch, Department, User Permission, Payroll Settings); `erpnext` (same, read only); `alvoraa_goals`, `alvox_compensation`, `grace_compensation`: **not touched**, and an import test (AC-24) fails the build if `alvoraa_goals` ever imports `people_trends`. `alvoraa_portal` tenant/control-plane split: the endpoint sits on tenant sites under `requires_feature("analytics")`; it reads one tenant's database and cannot reach another's (proven by construction: no cross-site call exists; the tenant plan check is the existing decorator).

**BQ-2 (HR on the page).** Two ways to meet SEC-8, and I recommend neither be done in this slice's first release:
1. *Fix the shared helper* (`permitted_branches()` and `hr_scope()`). Reaches 13 + 4 call sites, changes what store HR sees on attendance corrections, inbox, org structure and registers. That is a Tier 1 change to many screens, and it belongs to ALV-359 with its own tests.
2. *A guard inside my module only:* for an HR caller, read every Branch permission whatever it applies to, and use that set. About four lines, no shared change, strictly safer than the old card, meets AC-119.
**My recommendation:** build Leadership only; US-19 last; if you want HR early, take option 2, and leave ALV-359 to fix the shared helper. Your decision.

## 4 · Personas and HRMS domains

| Persona | What changes | Evidence |
|---|---|---|
| **CXO / Leadership** | New page "People trends". Sees totals for their linked company or branches. One company: no "By company" block. Two or more: alphabetical block, no ranking. No scope: "not set up" page, no figure query run | spec section 9 |
| **HR Manager / HR User** | Nothing in v1 (AC-118: refused, nav hidden). After BQ-2: the same page for their scope, plus the "no relieving date" Desk link | US-19 |
| **Employee, line manager, frontline** | Nothing on screen, no endpoint. Their rows sit inside totals that pass the group rule. A line manager who is also a leader gets only this page from the role (the role has zero DocPerm rows) | AC-8 |
| **System Manager with no HR role and no Leadership** | Refused (as `get_hr_analytics` 826 does today) | AC-16 |

HRMS domains: org structure (headcount, joiners, leavers), attendance, leave (read from Attendance On Leave rows). **Not** payroll, appraisals, goals, compensation, learning. Matches payroll at DTC and Grace because both use `payroll_based_on = Attendance` (production measure, 23 Nov, run by Surbhi).

## 5 · Verdict on the seven non-functional dimensions (against the proposal; I re-assess against the code at step 5)

| Dimension | Verdict | Why (one line) |
|---|---|---|
| **Performance** | **Neutral to existing screens; a new load on one path.** Risk named in section 8 (R1) | Fixed query count (about 14, ceiling 30), response size bounded by branches not headcount. The 730-day attendance read is the one to measure first |
| **Security** | **Improves** (a new door, closed by default) | Scope worked out server-side on every call, fail closed, POST+CSRF+role+plan, refused filters never trimmed, no new `ignore_permissions`, SQL parameterised |
| **Reliability** | **Neutral** | Read-only; the only write is one user default. Timeout, offline and error states are drawn. No job, no queue, nothing to retry |
| **Scalability** | **Neutral, with one watch item** | Employee rows grouped to non-identifying combinations (grows with distinct combinations, not response size). Attendance read is the cost that grows with months and headcount (R1) |
| **Maintainability** | **Neutral** | One new module, one new JS file, no edits to the shared calculation. Cost: a second definition of "branch scope for a leader", and one imported private name |
| **Data integrity** | **Neutral** | No cache, so no stale figure. END fixed once per call. Known limits stated in "How counted" (rehire counted as leaver plus joiner; person who moved branch sits under old branch in attendance) |
| **Compliance / privacy** | **Improves with residual risk** (R1-R10 in 01c, none yet accepted) | Totals only, minimum read fresh, hidden means not sent, a property test over generated tenants. Surbhi owns R10 "proposed, not accepted". Counsel questions CQ1-CQ3 do not block the build |

## 6 · How each SEC, PRIV and OPS item will be met

**SEC**

| Item | Mechanism (file) | Proved by |
|---|---|---|
| SEC-1 one scope resolver, fail closed | `leader_scope(user)` in `people_trends.py`; HR roles keep `of.hr_scope()` (never a union). Leadership: Company and Branch User Permissions with `applicable_for` empty or Employee; Branch counts only with its company | table-driven test over all fixture users; "not set up" runs no figure query (statement-count assertion) |
| SEC-2 filters refused, not trimmed | `_check_filters()`: one of branch / department / type, each tested against the Employee rows already inside scope; any miss raises PermissionError and logs the rule id only | AB-1..3 as real HTTP calls, log read from the file |
| SEC-3 lists from scope | Filter lists built from the same grouped Employee rows | scan of a response for the other company's names |
| SEC-4 endpoint hygiene | `@frappe.whitelist(methods=["POST"])`, `@requires_feature("analytics")` above it, role check first, `Cache-Control: private, no-store` via `frappe.local.response_headers.set` (same call as `hr_api.py` 839) | real-HTTP test: GET, Guest, no CSRF, header |
| SEC-5 role with no permissions | `make_role()`; no DocPerm/Custom DocPerm rows | row counts before and after; `summary(view="organisation")` refuses Leadership |
| SEC-6 access ends next request | Scope and the caller's own Employee status read on every call; nothing cached | load, mark Left, refused; restore; remove permission |
| SEC-7 SQL | Values only as parameters; table and column names constants; the pre-existing `ignore_permissions` count recorded with the same grep before and after. **Note:** 01c quotes 392; my `git grep` of non-test `.py` lines in this worktree gives 632 (and 2,013 with tests). The two greps count different things. I will record my own command and its number as the baseline and compare like with like | quote-in-branch-name test; reviewer reads every new statement |
| SEC-8 narrowed Branch permission | HR off in v1 (above) | AC-118 |
| SEC-9 one log line, in a sink that is written | `security_logger().info(json)` (ALV-391 fixed the level); fields: endpoint, user, role class, period, duration_ms, outcome. No figure, name, company or filter value | test reads the **file**, not a patched logger |
| SEC-10 no cache | None. The saved period is a user default, not a cache | test: no cache write |

**PRIV**

| Item | Mechanism | Proved by |
|---|---|---|
| PRIV-1 totals only | Allowlist of response keys; queries never select name, employee id, `description`, `reason_for_leaving`; the grouped Employee query selects only company, branch, department, type, status and the two dates, grouped, with `count(*)` | key-allowlist test; name and id scan of every fixture response; static check of SQL text; SQL capture shows no Salary Slip or Checkin read |
| PRIV-2 populations, caller left out | `_pass()`: population 0 or at least `min_group_size()`, caller's own Active record taken out of the test only | department of 5 including caller hidden at 5; stored 1 or 12 reads as 10 |
| PRIV-3 hidden means not sent | Hiding happens in `people_trends.py` before the dict is returned; key absent, `shared: false`, reason `few` or `subtraction`; the headline sentence is built on the server from sent figures only | recursive scan of every response |
| PRIV-4 decide once over time | Part B over the nine stretches, whole series or none | New Kiosk fixture (3 to 12) hidden on all chips |
| PRIV-5 one filter at a time | Refused if two; "All companies" carries no sub-company figures | AC-63, 64 |
| PRIV-6 siblings, blank included | Part C: hide next-smallest until hidden ones together pass; ties by name | AC-55..60 |
| PRIV-7 shown must not rebuild hidden | one-line guard in the builder, function-level test | AC-51 |
| PRIV-8 leave types at the top only | Part D | AC-85..87, 122 |
| PRIV-9 | Parity note only, no code | n/a |
| PRIV-10 data-quality line | Count at top of scope only; Desk link grants nothing | AC-101..103 |
| PRIV-11 no export, ranking, named lists | No file method, no sort parameter; lists sorted by name on the server | AC-17, 23 |
| PRIV-12 purpose | Import test: nothing in `alvoraa_goals` or appraisal code imports the module | AC-24 |
| PRIV-13 property test | One test over generated tenants and every fixture user; it must fail when part C's "together they pass" is removed (break it, watch it fail, restore it; I commit first) | `04-test-report.md` |

**OPS** (all 27 accepted; grouped)

| Items | How |
|---|---|
| OPS-1, 2, 6 | No Insights; no Employee Checkin or Salary Slip read (SQL capture test) |
| OPS-3, 12, 18, 19, 21 | Scope in SQL; POST only under `/api/method`, never a `cmd` on `/`; CSRF token carried by the page (`hrms_employee.py` calls `get_csrf_token()`); refusals logged in the proven sink. The panel calls through the portal's existing `gpFetch`, which already retries once with a fresh token |
| OPS-4 | Minimum read fresh each call |
| OPS-5, 15, 17, 25, 27 | No cache, no job, no queue, no schema, no patch, no new app. The diff test (AC-117) checks it |
| OPS-7, 9, 10 | Leave from Attendance On Leave rows; one row per day so no day-splitting; types folded by part D |
| OPS-8, 13, 14, 24 | Bins counted back from END; one call per period change; fixed statement count tested at 3 vs 30 branches and 20 vs 2,000 people; response within 10% in size |
| OPS-11 | Hidden = absent |
| OPS-16, 22, 23 | Timing line per call (warning above 2 s); 3G timing on a dev copy at DTC size, seeded not copied, by Surbhi's word |
| OPS-19 route | Settled in the spec: a panel inside `/hrms-employee`, so **no nginx edit** |
| OPS-20 | No new rate rule; the saved period is sent after a 2-second dwell (client side) |
| OPS-26 | No secrets, no outbound call |

## 7 · Proposed approach, file by file

Rung: **new code** in the existing app. Everything below is on the local instance only. I will build my own stack (own containers and site, like `alv089-*`) because the shared `hrlocal-bench` mounts the stale main checkout (memory: shared bench cannot test a branch). That needs an hour and no one's approval beyond this one; tell me if you would rather I did not.

| File | Mechanism | Why |
|---|---|---|
| **NEW** `alvoraa_portal/alvoraa_portal/people_trends.py` | Build. Endpoint `get_people_trends(period, company=None, branch=None, department=None, employment_type=None)`, endpoint `save_people_trends_period(period)`, `leader_scope()`, window maths, people and early-leaver counts, attendance and leave grouped queries, parts A-D, headline builder, `make_role()` | No existing code has the leader scope, the windows or the hiding rules. One file; split only if it passes about 900 lines |
| `alvoraa_portal/alvoraa_portal/hooks.py` | Configure: 2 lines | Role created on migrate and on a new tenant. No `patches.txt` line: `after_migrate` runs on every migrate, so a patch adds nothing |
| **NEW** `.../templates/includes/ess/parts/people-trends.html` + 1 line in `www/hrms-employee.html` | Extend: the portal's own `ess_part` pattern | Panel, skeleton, banners, chips, sheet, tables. Phone-first |
| **NEW** `.../public/js/ess/people-trends.js` + 1 `<script defer>` line in `hrms-employee.html` | Build, prefix `pt` | Keeps 26,758-line `portal.js` almost untouched. If the 3G test says the extra file costs too much, it becomes lazy-loaded on first open (decide on the number, not now) |
| `.../templates/includes/ess/frame.html` | Extend: one nav item "People trends" (Company group) and, once I find the file, "Trends" in the phone bottom bar (P2, **not yet located**) | Parity P1, P2 |
| `.../public/js/ess/portal.js` | Extend: about 3 lines: `switchPanel` loads the panel (near line 4859), the nav shows for `ctx.roles` containing "Leadership" (near line 13459), and `applyPlanNav` respects `plan_analytics` (near 13530) | The portal's own wiring, nothing else |
| **NEW** tests: `tests/test_people_trends_090.py`, `tests/test_people_trends_http_090.py` (real HTTP, log file), `tests/test_people_trends_property_090.py`, `tests/people_trends_090_dom_test.js` (jsdom, same style as `event_form_082_dom_test.js`) | Reuse the fixtures in `leader_fixtures_012.py`; own record names with a `pt090` prefix | Every AC has an oracle; the hook, route and panel are pinned |

**Not changed:** `org_figures.py`, `access.py`, `hr_api.py`, `deploy/nginx.conf`, any DocType JSON, `patches.txt`, fixtures, the old HR Analytics panel.

**Query plan per call (about 14, ceiling 30, same at 3 or 30 branches):** the minimum setting (1), the caller's role and Employee status (2), User Permissions (1, framework), grouped Employee rows (1), the caller's own Employee row (1), attendance per bin (1), attendance distinct people per stretch (1), On Leave by type and stretch (1), `data_up_to` (one per company, 1 to 2), Open doubtful count (1), pending Leave Applications (1), saved period (1). Everything else is Python on those results.

## 8 · Build order, thin slice first, and the cut line

Nothing is pushed or shown to anyone until US-6 and US-7 and their property test exist; a figure must never ship without its rule.

| Step | Stories | What you can see when it is done |
|---|---|---|
| 0 | none (spike, half a day) | Seed a local site to DTC size (about 600 staff, a year of attendance, **seeded, never copied**) and time the two attendance queries. **Go or stop** before anything else is built (R1) |
| 1 | US-1, US-2 | Role, scope, "not set up", endpoint, POST/CSRF/plan/header, log line, generic error. Returns only a period echo |
| 2 | US-3, US-4, US-16 (thin) | One period chip, headcount, joined, left, net, attrition, in a real panel on a phone-width screen. First end-to-end path for one role |
| 3 | US-6, US-7, US-8 | The group rule, siblings and one-at-a-time filters, with the property test (and its break test) |
| 4 | US-5, US-9, US-12 | Early leavers (whole company only, four stretches), the chart and its table, the headline sentence |
| 5 | US-14, US-13, US-15 | All states, By company, data-quality line |
| 6 | US-10, US-11 | Attendance and leave |
| 7 | US-17, US-18 | Totals-only scans, budgets, 3G timing on the dev copy (needs Surbhi's word for a dev tenant) |
| 8 | US-19 | HR, only if BQ-2 says so |

**Cut line if time runs short** (the brief's order): drop **US-19** first (it is gated anyway), then **US-11 leave**, then **US-10 attendance**, then **US-15**, **US-13**, and last **US-8 filters**. The floor that must ship together: US-1, 2, 3, 4, 5, 6, 7, 9, 12, 14, 16, 17, 18 = 50 of the 66 points. The 16 points above the floor are US-8, 10, 11, 13, 15, 19. Without filters, part C shrinks to the companies under "All companies".

## 9 · Risks and what I want decided

| # | Risk or question | My recommendation |
|---|---|---|
| R1 | **Performance.** Part B needs distinct people per stretch over 730 days, so every call reads about two years of Attendance (DTC about 220,000 rows a year, an estimate not a count). The 3 s budget could be missed on a cold call, and "no cache, no job" (OPS-17) forbids the usual fixes | Step 0 measures it. If it misses, come back to you as a decision (a time-only cache per OPS-5, or reading Employee-based populations for attendance). I will not add either quietly |
| R2 | A Role "Leadership" already exists locally with desk access on, and may exist on dev and production | Hook sets `desk_access 0`. Read-only holder count on dev and production before release |
| R3 | Four hot files, 48 commits in 7 days, two live sessions | Hot-file edits last, one line each, rebase first, pin tests |
| R4 | My `git grep` counts 632 `ignore_permissions` lines where 01c says 392 | Record my own command and number as the baseline |
| R5 | BQ-2 undecided | HR off; US-19 last; option 2 if you want HR early |
| R6 | The phone bottom bar is not located; the spec labels P2 `[UNVERIFIED]` | Find it in step 2; if it lives in a file another session is changing, ask you before editing |
| R7 | Brief timing: 66 points is large for one slice | The cut line in section 8 |
| R8 | The spec's AC-105 hour-long wait may not exist (the cache is cleared when the User record is saved) | Write the test; change the AC wording if it is true |
| R9 | Residual R1-R10 (01c) not accepted; CQ1-CQ3 with counsel | Surbhi owns them; none blocks the build |

## 10 · Subtract pass

Removed from my own first idea: a separate `people_trends_rules.py`; a `patches.txt` line and an `after_install`-only hook split; a new `get_portal_context` flag; a snapshot job for the 730-day read (not allowed, and not measured); an `org_figures.py` rename and refactor; the shared `permitted_branches()` fix; a second saved-period store. **Kept though thin:** the PRIV-7 one-line guard.

## 11 · Waiting for you

Approve, adjust or redirect. Specifically: **(1)** go ahead on the file plan in section 7; **(2)** BQ-2: HR off in v1 (my default) or option 2; **(3)** may I build my own local stack; **(4)** read-only count of Leadership role holders on dev and production; **(5)** is anyone else in the four hot files. Deploy is a separate decision, later.

---

## Strategy decision

**Approved — Surbhi, 23 Nov 2026 ("go with your recommendations"):** the file plan plus the deploy.yml "Portal assets must be served" edit (OPS-29); HR off in v1 (BQ-2); the engineer builds its own local stack; R1 pass mark = attendance part under 1.5 s cold at DTC size, with five concurrent calls (OPS-28); OPS-28 to OPS-33 accepted. This approves local implementation only — not commit to dev, push or deploy.

### R1 decision after step 0 — Surbhi, 24 Nov 2026 ("go with your recommendations")

Option 1: group populations come from Employee (date_of_joining, relieving_date, status), not from a 2-year Attendance scan (measured 0.011 s vs 6.4-10.1 s on the 8x-slow local stack). The per-period Attendance query stays, capped at the window plus its comparison window. The 6-month and 1-year timing is confirmed on the DTC-size dev copy (OPS-23) before release. No cache; a cache comes back to Surbhi only if that test still misses.
