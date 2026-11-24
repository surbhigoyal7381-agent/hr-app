---
slice: 090-leadership-hr-analytics
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-11-24
tier: 1
read_at: worktree .claude/worktrees/090-leadership-hr-analytics, branch slice/090-leadership-hr-analytics, commit 8c4763e0 (diff 0a181d05..8c4763e0, 26 files)
also_read: 01c (whole), 02 §5.4-5.8, §10 US-6..US-11 and US-15, decisions sections; 03 (whole); 07 §4 and §5 (part)
not_read: the two uncommitted files in the worktree (scripts/run_dom_tests.js, people_trends_090_gaps_dom_test.js); they are DOM tests only
---

# 090 · People trends: security review

**I recommend. You decide.** I changed no source file, ran no test and committed nothing. Labels: **proven** (I read the line, or ran a read-only command), **inferred**, **not checked**.

**Conflict of interest (lesson 6).** The same agent role wrote `01c` and now checks the code against it. Where `01c` itself was wrong I say so (SEC-6 below). **Please have the technofunctional reviewer read findings F1 and F2 a second time**, because they are about my own rule.

## Verdict

**Not ready for dev yet. Two P1 findings. No P0 (stop-the-line) finding.** Both fixes are small.

- **F1 (Major, P1).** You can subtract the attendance and leave figures to get a group the rule never checked: attendance rows tagged with a blank branch, or with a branch no current employee holds, plus rows for people the rule does not count. This depends on data I could not see.
- **F2 (Major, P1).** The attendance and leave series per bucket are sent even when a bucket fails. Only the people chart is held back. That breaks AC-50 and AC-90.

**Counts:** SEC: 9 met, 1 partial, 0 not met. PRIV: 8 met, 5 partial, 0 not met. Decisions: 4 met. SQ-1: met in code, partly tested.

The scope resolver does **not** have the ALV-359 hole (proven, details under SEC-1). I found no cross-company leak in the code.

---

## 1 · What I checked

| Check | How | Label |
|---|---|---|
| `people_trends.py`, all 865 lines | Read | proven |
| `org_figures.condition`, `employee_condition`, `Scope`, `open_doubtful_counts`, `data_up_to`, `_OPEN_DOUBTFUL` | Read | proven |
| `subscription.requires_feature` | Read, lines 848-891 | proven |
| `hrms/.../access.py` `security_logger` (29-68), `permitted_branches` (263-280) | Read | proven |
| `branch_scope.py`: how `alvoraa_branch` is filled | Read, lines 1-80. It is copied from Employee.branch at save. It keeps the old branch when a person moves ("deliberate, 2026-09-14") | proven |
| `people-trends.js` (escaping, storage), the template and nav diffs, `hooks.py` diff | Read | proven |
| The tests: `test_people_trends_090.py` (parts), `_http_090.py` (all), `_property_090.py` (all) | Read. **Not run**: the full suite was running in `alv090-bench` | proven that they exist; pass or fail not checked by me |
| Installed Frappe in `alv090-bench` (commit 988e54f): `auth.py` 81-97 (CSRF), `app.py` 308 (headers), `user_permission.py` 102-140 (cache, child companies); ERPNext `company.py` 34 | Read-only `sed`/`grep` through `docker exec`. No bench, DB or redis command | proven |
| `ignore_permissions` lines, `alvoraa_portal/alvoraa_portal/*.py` outside tests | `git grep` at 0a181d05 and 8c4763e0: **362 and 362** | proven |
| Any tenant's data (blank `alvoraa_branch` rows, Inactive staff with attendance, leave types on DTC's On Leave rows) | — | **not checked**. Needs a read-only count on a dev copy of DTC and Grace |

---

## 2 · Findings (ranked)

### F1 · Major · P1 · Attendance and leave figures can be subtracted to get a group the rule never checked

**Where.** `people_trends.py` 450-479 (`_attendance_bins`), 545-559 (`_pending`), 759-787 (attendance and leave use the people verdict). For a branch filter, rows are matched on `a.alvoraa_branch` (line 456). For the company total, every row of the company is counted (line 453). The rule's siblings come from **Employee** values of **counted** people only (lines 326, 705: Active, or Left with a relieving date).

**The gap.** Company total minus every shown sibling should leave only the hidden siblings, which part C proves pass together. For attendance and leave it also leaves:
1. rows whose `alvoraa_branch` is blank, or names a branch that no current Employee holds (a closed store, or a store everyone moved out of: `branch_scope.py` keeps the old tag on purpose);
2. rows of people the rule does not count (Inactive, Suspended, Left with no relieving date, no joining date), when their department, type or branch is not a counted sibling. The test `test_empty_cut_is_no_match` builds exactly this: a branch of 6 Inactive people answers "no match", but their attendance still sits in the company total.

Nobody checks how many people are behind that remainder.

**Scenario.** A company head of one company opens 3 months with no filter. They read Leave days and the leave series. Then they open each branch in turn. Say every branch passes, so none is hidden. Three people moved from "Kiosk" to "Civil Lines" in October, and "Kiosk" now has no employee. Company leave days minus the sum of the branches = **the On Leave days of those three people**, week by week. That is a figure about 3 people, below the minimum of 5. The same works for Pending (Leave Application `alvoraa_branch`) and for "days left out".

**What must exist for this to happen:** attendance or leave rows in the last 2 years that are tagged with a blank or orphan branch, or that belong to uncounted people. **Not checked** on any tenant. DTC and Grace have 0 leavers without a relieving date (02, production measure, 23 Nov). The other two cases are unknown.

**Why Major and not Blocker.** The mechanism is proven in the code. The data that would make it fire is not checked, and nothing is live.

**Smallest fix (engineer and analyst to choose; changes the AC-76/AC-83 "equals `attendance_figures`" check, so it is your call):**
- (a) For leaders, match attendance, leave and pending rows by the **Employee's current** company, branch, department and type, **only for counted employees**. Department and type already use the Employee join (line 458). Then the rows split exactly along the siblings the rule checks. Or
- (b) keep `alvoraa_branch`, but include the blank tag and every tag seen in the rows as siblings in the rule, and count uncounted employees in the populations.

(a) is less code. In both cases, add one test: company minus all shown branches, with one orphan-tagged row present.

### F2 · Major · P1 · Attendance and leave series are sent when a bucket fails

**Where.** Lines 737-740 hold back only the people chart when `bin_rule` fails. Lines 770-772 (`attendance.series`) and 782-783 (`leave.series`) are always sent.

**Scenario.** A branch has 5 people. One leaves on day 1 of the last week. The branch passes all nine stretches (5 were on the roll in stretch 0-7). On the 1-week chip, days 2 to 7 have 4 people, so `bin_rule` fails and the people chart says "Not shared". But the response still carries the absent % and the On Leave count **for each of those days, for 4 people**. Decision 1 in 03 says the same people stand behind attendance and the people figures. So the same bucket rule must cover all three series.

**Breaks:** PRIV-4 ("each chart series is sent whole or not at all"), AC-50 and AC-90. **No test covers the failing-bucket case for any series** (grep: the only chart test asserts `shared: True`, line 302-309).

**Fix:** when `bin_rule` fails, remove `attendance.series` and `leave.series` as well, keeping the window totals. One condition, plus one test that makes a bucket fail.

### F3 · Minor · P3 · The named leave types can change between periods

**Where.** `_leave_types` lines 531-537. When "Other" fails, the named type with the **fewest days in the current period** moves into Other. So the named list can differ from period to period. AC-86 says the list is the same on all five periods.

**Scenario.** 1 week names Earned and moves Sick into Other; 1 year names Sick and moves Earned. I could not build a subtraction that isolates a group under 5 from this, because per-type figures are not sent per bucket. But the stated guarantee does not hold. **Fix:** order the fold by a value that does not depend on the period (for example, people over 365 days, then name).

### F4 · Minor · P3 · `window.records_start` is one person's joining date

**Where.** Lines 692 and 701. Every response, including "Not shared", carries the earliest joining date in the company (or in a branch head's branches). The page shows it as "your records start on {date}" (JS line 115). PRIV-1 says no person's date of joining. In most companies this is the first employee's date, and a leader may know who that is. **Fix:** send it only when the window is clipped. In that case it is the window start anyway, as AC-27 designed.

### F5 · Minor · P3 · Removing a branch head's Branch permission widens them to the whole company

**Where.** `leader_scope` lines 127-134. Under BQ-1, a branch head is Company plus Branch. If someone deletes the Branch row, the person becomes a company head on the next call. **`01c` SEC-6 was wrong to expect "not set up" here**, given BQ-1. That was my error. **Fix:** no code change. Add one line to the admin guidance: "to end a leader's access, remove the role or the Company permission, never only the Branch one."

### F6 · Minor · P4 · Small gaps in the log line

The plan refusal (`requires_feature`, before the body runs) and an empty tenant (`no_people`, line 669-670, which returns before the filter checks) write no `people_trends` line. Neither returns a figure. `save_people_trends_period` has no plan check. It writes only the user's own period.

### F7 · Minor · P4 · Data-quality count by subtraction across companies

`_data_quality` (860-865) shows N ≥ 5 at "All companies" and at each chosen company. All minus Company A can give Company B's count of 1-4 leavers with no relieving date. This is the same kind of count that Q3 dropped the under-5 rule for, and it is low in sensitivity. Note only.

---

## 3 · SEC requirements

| ID | Status | Mechanism and evidence |
|---|---|---|
| SEC-1 One resolver, fail closed | **Met** | `_caller` 137-162 and `leader_scope` 112-134. Guest (144), not Leadership (150), HR + Leadership refused (152-153, BQ-2). A Company permission counts only if `applicable_for` is empty or Employee (124-127). **A narrowed Branch row returns "not set up" (131-132), so the ALV-359 / R6 hole in `permitted_branches()` (`access.py` 278-279, unchanged) is not copied.** "Not set up" returns before any figure query (631-633). Tests: `test_scope_table`, `test_not_set_up_runs_no_figure_query`, `test_who_is_refused`. Proven in code; tests not run by me |
| SEC-2 Filters refused, never trimmed | **Met** | Lines 673-685: two filters → PT-FILTERS; company outside scope → PT-SCOPE; dimension value must be held by a person of the chosen company inside scope; period one of five (613-619). Unknown parameters are dropped by Frappe's signature filter (`test_extra_parameters_have_no_effect`). F6 notes the empty-tenant order |
| SEC-3 Lists from inside scope | **Met** | `_filter_lists` 821-838 builds lists from `_people` rows, which are scoped by `employee_condition` (209). Companies are limited to `scope.companies` (835-836). Test `test_lists_hold_only_the_scope` |
| SEC-4 Endpoint hygiene | **Met** | `@frappe.whitelist(methods=["POST"])` and `@requires_feature("analytics")` (622-623, the same order as `hr_api.py` 819-820). `Cache-Control: private, no-store` is set through `frappe.local.response_headers` (606-610), which Frappe merges into **every** response, errors included (`app.py` 308, proven). CSRF over real HTTP: `test_a_post_without_the_token_is_refused_and_with_it_is_served`. **Framework limit (proven, `auth.py` 87):** the check is skipped when a session has no saved token. The page saves one; an API-only session would not. Low impact here: the endpoint reads, and the only write is the user's own period |
| SEC-5 Leadership role, no permissions | **Met** | `make_role` 55-64 sets `desk_access = 0`, runs last in `after_migrate` and `after_install`. Tests: no DocPerm or Custom DocPerm rows; `test_the_role_adds_no_rows_anywhere` (5 DocTypes); `test_leadership_is_still_refused_the_organisation_attendance_view`. 07 OPS-30: 0 holders on 10 sites, so nobody loses Desk access |
| SEC-6 Access ends on the next request | **Partial** | Met: scope is worked out every call, no cache (only Frappe's `user_permissions` cache, cleared when a permission changes); a leader whose linked Employee records are all non-Active is refused (159-160, status checked, lesson 3); test `test_a_leader_whose_own_record_is_left_is_refused`. **Not met as `01c` wrote it:** removing the Branch permission widens to the company (F5). That is my requirement's fault, not the code's |
| SEC-7 Parameterised SQL, no new `ignore_permissions` | **Met** | Every f-string slot is a constant or a parameter name: `where` from `condition()`, `join`, `e.{dim}` where dim comes from a fixed tuple (673-674), `_interval` names. 0 `ignore_permissions` in the module; app count 362 → 362 (proven by `git grep`). Test `test_a_branch_name_with_a_quote_is_just_refused` |
| SEC-8 Narrowed Branch row (R6) | **Met, by keeping HR off** | HR roles are refused (152-153), so no HR user reaches the page. For leaders, fail closed (131-132). The R6 fix in `permitted_branches()` itself is still open (ALV-359), and HR Analytics still uses it. That is outside this slice |
| SEC-9 One line per call, in a sink that writes | **Met** | `Call.log` 86-101 writes through `security_logger()`, which raises the "security" logger to INFO (`access.py` 62-67, the ALV-391 fix, present on this branch). Fields: event, at, user, role, period, ms, outcome, statements, rule. No figure, company, branch or filter value. Over HTTP the line is **read back from the file**, not from a patched logger (`test_the_log_line_is_in_the_file_and_holds_no_figure`, `test_a_refusal_writes_exactly_one_line`). An error gives the generic PT-LOAD message, and the Error Log holds only the exception type (641; `test_forced_exception_gives_the_generic_message`). Gaps: F6. **Not checked:** that the level holds in the production image (the test proves it on the test site) |
| SEC-10 No cache | **Met** | No `frappe.cache` in the module (grep, proven). No scheduler job |

## 4 · PRIV requirements

| ID | Status | Mechanism and evidence |
|---|---|---|
| PRIV-1 Totals only | **Partial** | `_people` (203-220) groups by non-identifying columns and returns counts only. The SQL never names `reason_for_leaving` or `description` (grep, proven; `test_no_reason_or_pay_columns_in_the_sql`). Key allowlist and name/id scan: `test_totals_only`. JS escapes all server text (`h()`, `option()`). **F4:** `records_start` is one person's joining date |
| PRIV-2 Population per figure; caller not counted | **Met** | People: on the roll in each stretch (`_people_units` 242-249). Early leavers: joiners per cohort stretch (252-260). Leave types: people who took the type (509-525). The caller's own record is taken out of every pass test (`minus` 285-286, 714-716, 748-752; `own_key` 790). Attendance uses the people population: **your decision 1, 24 Nov** (03 §2). `min_group_size()` is read every call (664). Tests: `test_callers_own_record_is_left_out_of_the_pass_test`, `test_minimum_is_read_every_call` |
| PRIV-3 Hidden means not sent | **Met** for whole cuts | `not_shared` returns only window, filters and scope (729-730). The headline uses only figures that were sent (573-601). Test `test_hidden_means_not_sent` (keys absent). Bucket-level series: see PRIV-4 |
| PRIV-4 Time rule | **Partial** | Nine stretches (45) match every window and comparison edge (I checked all five periods by hand). Clipping to `records_start` is safe, because nobody joined before it. People chart buckets get their own check (737-740). **F2:** the attendance and leave series skip it. The failing-bucket case is not tested |
| PRIV-5 One filter, one company | **Met** | 675-681; "All companies" has no lists below company (826-827) and no types (788). Tests `test_refused_filters`, `test_all_companies_has_no_sub_company_figures` |
| PRIV-6 Siblings, blank included | **Partial** | `Rule.hidden` 314-342: blank (None) is a sibling (326); keep hiding the next-smallest until ≥2 are hidden and they pass together (337-340); companies under "All companies" (322-324). Ordering uses headcount at END (`_sizes`), as 02 §5.6 says. Tests: `test_branches_part_b_and_c`, `test_employment_type_and_department_siblings`, `test_a_small_company_hides_the_next_smallest_too`, and the property test. **F1:** for attendance and leave, the siblings do not cover every row |
| PRIV-7 Shown figures do not rebuild a hidden one | **Met** | The people family is shown whole or not at all. `share_left=False` guards the function (391-404; `test_leaving_unshared_leaves_nothing_derived`) |
| PRIV-8 Leave types only at the top | **Partial** | Types are sent only with no filter, for one company or a branch head's set (788-790). A type is named only if its people pass in 5 stretches; Other must pass, else total only (531-542). Tests `test_leave_types_fold_small_ones_into_other`, `test_types_are_named_only_at_the_top`. **F3:** the named list depends on the period |
| PRIV-9 Count-under-5 rule removed | **Met** | No such rule in the code (Q3) |
| PRIV-10 Data-quality line | **Met** for leaders | Only with no filter, and only N ≥ minimum (860-865); `test_data_quality_line_only_at_the_top_and_only_five_or_more`. HR link: not built (HR off). F7 note |
| PRIV-11 No export, ranking or named lists | **Met** | Two whitelisted methods, neither returns a file. Lists and By company are sorted by name (829, 844). A sort parameter has no effect (`test_extra_parameters_have_no_effect`) |
| PRIV-12 Purpose limitation | **Met** | `test_goals_and_appraisals_do_not_import_it`; my grep found no importer in `alvoraa_goals` or `hrms` |
| PRIV-13 Property test | **Partial** | 300 generated tenants at minimums 3, 5 and 10; the `Mutant` break test is in the suite (property file 41-95). The engineer says they deleted part C's loop and watched the test fail (03 §4; not seen by me). **It covers only sibling unions for the people family.** It does not cover window, comparison or bucket differences (asked for by AC-62), or the attendance and leave families. With those, it would have caught F1 and F2 |

## 5 · Decisions and SQ-1

| Item | Status | Evidence |
|---|---|---|
| Q1 one filter, inside one company | **Met** | 675-681 |
| Q2 leave types only with no filter | **Met** | 788 |
| Q3 count-under-5 dropped | **Met** | No such rule |
| Q4 HR held off until ALV-359 | **Met** | 152-153; `test_who_is_refused` covers `hr` and `hr_lead` |
| SQ-1 early leavers: 4 cohort stretches 7-30, 30-90, 90-180, 180-365 | **Met** | `COHORT_STRETCHES` 47; `_cohort_units` 252-260; the check runs on the company match (752-753) |
| SQ-1 whole company only | **Met** | 743: a company is chosen, no filter, **and not a branch head** (`scope.branches is None`). This is stricter than 01c and correct |
| SQ-1 1-week period: "Too early to tell" | **Met by construction** | Window start = END−6 and cutoff = END−7, so every cohort is 0 (409-424). The engineer's note says it is tested (AC-40-44) |
| SQ-1 closed cohorts only | **Met** | 417-420: joiners past the cutoff go to `inside`, not into the cohort |
| SQ-1 fixed production cases (21, 297, 163, 46 show; 1, 4, 1, 3 hide) | **Partial** | Not written as fixed tests (03 §4 says so). Fixture cases cover the rule. Add the two as cases: cheap |

---

## 6 · Trying to break the differencing rule

| Attack | Result |
|---|---|
| Company minus the shown branches, departments or types (people) | **Holds.** Part C plus the property test |
| "All companies" minus a company | **Holds.** Companies are siblings (322) |
| Period minus period; window minus comparison | **Holds** for people: every difference is a union of whole stretches, and each passes |
| Clipped window minus a shorter window | **Holds.** Nobody is on the roll before `records_start` |
| Company minus branches, **for attendance and leave** | **Breaks** when orphan-tagged or uncounted rows exist: **F1** |
| Bucket series of a cut whose bucket fails | **Breaks** for attendance and leave: **F2** |
| Parent chart minus shown siblings' charts, per bucket | Not checked by the code at bucket level. Only matters if the hidden group shrinks inside a stretch. Worry W1 |
| Leave types across periods | The guarantee is weaker than stated (F3). I found no exact extraction |
| Early leavers across "within" cells | Lower limits only, each over ≥5 joiners (R10, as designed) |
| Same-named branch in two companies | **Holds.** Company is always in the condition, and a filter needs a chosen company (680-685) |
| Post another company, branch or department | **Refused and logged** (PT-SCOPE; HTTP test reads the line from the file) |

## 7 · Worries (not findings)

- **W1.** Part C is not checked at bucket level. Parent chart minus the shown siblings' charts gives the hidden union per bucket. A bucket inside a stretch can hold fewer people than the stretch. The leak needs turnover inside the hidden group within one stretch. It is close to 01c R3.
- **W2.** A Company permission on a **group** company also covers its child companies. Frappe adds descendants unless `hide_descendants` is set (`user_permission.py` 136-139; ERPNext `Company(NestedSet)`). This is Frappe's normal meaning, but whoever sets up a leader should know it.
- **W3.** Whether DTC's On Leave rows carry a leave type is still not checked. If they do not, nothing leaks; the split is just empty.

## 8 · What must exist for the controls to be seen working (lesson 1)

- Part C fires only where a branch, department or type has 1-4 people. Most live companies will show some "Not shared".
- Early leavers show at DTC and Grace Drinks, and hide at Grace Sales and Grace Enterprises (01c SQ-1 table, your production counts).
- F1 fires only if orphan-tagged or uncounted attendance rows exist. **One read-only count per tenant answers it:** On Leave and counted Attendance rows in the last 730 days whose `alvoraa_branch` is blank or not held by any Employee of the company, and rows of employees whose status is not Active and not Left-with-a-date. Counts only, no names. Your word is needed to run it on a dev copy.

## 9 · Residual risk

**None of these is accepted yet.** An accepted risk needs a name and a date.

| # | Risk | Size | Kind | Proposed owner | Accepted on |
|---|---|---|---|---|---|
| R1-R5, R7, R10 | As in 01c §11 and SQ-1 (range inference, daily visits, bucket crossings, what the leader already knows, pooling, no detection inside scope, early-leaver lower limits) | Low to medium | Intentional trade-off / acceptable simplification | Surbhi | — |
| R6 | `permitted_branches()` still ignores narrowed Branch rows for **HR Analytics** (ALV-359). Not reachable through People trends | Medium, possibly live elsewhere | **Dangerous debt, carried; escalated on ALV-359** | Surbhi (live check), engineer (fix) | — |
| R8 | Logs: about 2 MB, held in France | Medium | Temporary debt | Founder | — |
| R11 (new) | Attendance population = the people on the roll, not people with attendance rows (your decision 1, 24 Nov) | Low once F1 is fixed | Intentional trade-off | Surbhi | **Decided 24 Nov; not yet written as a risk acceptance** |
| R12 (new) | CSRF is skipped for a session with no saved token (`frappe/auth.py` 87) | Low here (read-only endpoint) | Acceptable simplification (framework) | Surbhi | — |
| R13 (new) | Removing only the Branch permission widens a branch head (F5) | Low, if the admin note exists | Acceptable simplification | Surbhi | — |

**Counsel questions still open** (01c CQ1-CQ3): legitimate use under s.7(i), naming health-related leave types, and the notice line. None blocks the build. **Baseline:** the CERT-In entry was last checked 24 Aug (92 days ago) and is stale. This review does not rely on it beyond R8.

## 10 · Before dev (in order)

1. Fix F2 and F1 (or decide F1 after the read-only count), and add their tests. Extend the property test to attendance and leave if you choose F1 option (b).
2. F3 and F4: one line each. They can ride with step 1.
3. The DevOps P1-A design-system failure and the rebase onto 086 (07 §5) are separate from this review.
4. Name an owner and a date for each line in section 9.

## Subtract pass

Removed from my draft: a finding that `requires_feature` sits below the whitelist (it matches the three other analytics endpoints and runs before the body, so it is not a finding); a worry about the `few` and `subtraction` reasons revealing size (designed, UX-1b); a finding on `inside` counts for unfinished cohorts (it equals Joined, which may be shown). Kept: seven findings, three worries.

---

# Re-review round 1 (24 Nov 2026)

**Read at:** worktree `.claude/worktrees/090-leadership-hr-analytics`, branch `slice/090-leadership-hr-analytics`, commit **cb3677e3**, rebased on `origin/dev` 640cd1f5. I read the fix diff 8c4763e0..cb3677e3 for `people_trends.py`, `people-trends.js`, the template and the new tests; 03 §10; 02 "Decisions after review". I did not re-read the whole slice (usage rule §5).
**Not done:** I ran no test (the full suite is running in `alv090-bench`). The only commands in the container were read-only `sed`/`grep` of installed Frappe. I changed no source and committed nothing. Same conflict of interest as above: I wrote 01c.

## Verdict

**Not ready for dev yet: one new P1 (G1), small fix. No P0 (stop-the-line) finding.**
F1 is fixed inside one company. F2 is fixed. B2 holds. But the F1 fix stops one level too low: **"All companies" minus each company can still leave a group the rule never checked** (G1). F5's admin line was not written.

## What the fixes did

| Item | Result | Evidence | Label |
|---|---|---|---|
| F1 | **Fixed inside a company.** Rows are now cut by the Employee's branch, department and type, only for counted people (`_rows_of_counted_people` 453-471, `COUNTED_SQL` 449, which matches `_counted` 221-227). The row tag only narrows to the company. Pending uses the same helper (580-585) | Read. Three tests (blank tag, tag nobody holds, Inactive staff) assert company = sum of branches | proven in code; tests not run by me |
| F2 | **Fixed.** `series_ok = chart["shared"]` (802); `attendance.series` and `leave.series` are left out when it is false (811-812, 820-821). Window totals stay | `test_a_failing_bucket_sends_no_series_at_all` | proven in code; test not run by me |
| F3 | **Fixed.** Named types sorted by the 365-day total, so the list is the same on every chip | `test_named_leave_types_are_the_same_on_every_chip` | proven in code |
| F4 | **Not changed, by choice.** Needs Surbhi's yes, because the prototype draws the sentence (02, open) | — | proven (unchanged) |
| F5 | **Not done.** No admin-guide line anywhere (`grep` of `docs/` and the app). AC-10 in 02 (line 330) still says "remove the Branch permission → not set up", which the code does not do | grep, read | proven |
| B2 | **Holds.** `fetch("/api/method/…")`, POST, `X-Frappe-CSRF-Token` from `frappe.csrf_token` (JS 231-239). The host page asks for a token (`hrms_employee.py` 21). Frappe parses a JSON body (`frappe/app.py` 365, installed copy). 403 → PT-SCOPE; any other status, bad JSON or a dropped connection → PT-LOAD; the 15 s timer stays. Unknown args are still dropped by the server | Read; DOM tests use fakes with real status codes | proven in code. **Not checked:** a real browser; the HTTP test posts form data, not JSON |
| M2 guard | **Built as decided.** `_attendance_bins` now counts people per bucket (482); attendance is withheld whole if any bucket, or the comparison window, has 1-4 people with rows (803); the By company card does the same per company (891) | `test_attendance_is_shown_only_when_five_people_have_rows` | proven in code. By company guard: no test (03 §10 says so) |
| `ignore_permissions` | 362 at 640cd1f5 and 362 at cb3677e3 (app, outside tests); 0 in `people_trends.py` | `git grep` | proven |

## New findings

### G1 · Major · P1 · "All companies" minus each company leaves a group the rule never checked

**Where.** `_rows_of_counted_people` 464-465. The row is matched on **its own** company (`a.company` / `l.company` in the scope), and the person on **their Employee** company. These are checked separately, never against each other.
**Scenario.** A leader over Grace Drinks and Grace Sales. Three people moved from Sales to Drinks last month (Employee Transfer without a new Employee ID, so `Employee.company` changes and old rows keep "Grace Sales"). On "All companies" their old Sales leave rows count (row company in scope, Employee company in scope). On "Grace Drinks" they do not (row company is Sales). On "Grace Sales" they do not (Employee company is Drinks). **All-companies leave days minus Drinks minus Sales = those 3 people's leave days.** The same works for Pending, and roughly for absent %.
**What must exist:** attendance or leave rows in the last 2 years whose company differs from the person's Employee company, and a leader with two or more companies. **Not checked** on any tenant.
**Why P1:** it is the same leak as F1, one level up, and the fix is small.
**Fix (engineer's choice):** also group the inner query by the row's company and add `x.company = e.company` (and `l.company = e.company` in `_pending`). Then a mover's old-company rows are left out everywhere. Add one test: All = sum of companies, with one moved person. The property test still covers only the people family (03 §10, temporary debt). That is why this got through.

### G2 · Minor · P2 · The M2 guard counts the caller

**Where.** `count(*) as people` (482) and `_attending_ok` (503-506) count every person with rows, the leader included. Every other check takes the caller out (PRIV-2, `minus`).
**Scenario.** A branch head is on the roll of their own branch. A week has 5 people with rows: the head and 4 others. Attendance is shown. The head knows their own days, so the absent % is in effect about 4 people.
**Fix:** leave the caller's employee out of the count (the own record is already known in `_build`). One line and one test.

### G3 · Minor · P2 · On Leave rows count as "attending", but absent % ignores them

**Where.** The guard counts anyone with a row (482). Absent % uses only Present, WFH, Half Day and Absent (`org_figures.rate` 129-134).
**Scenario.** A day with 5 people with rows, 4 of them On Leave. The guard passes. The absent % for that day is about 1 person. The leave series on the same chart says 4 were on leave.
**This matches Surbhi's words** ("at least 5 people have attendance rows"), so it is her call, not a defect. The cheaper, stricter version counts people with at least one non-leave row.

## Trying to break the differencing again

| Attack | Result |
|---|---|
| Company minus every shown branch, department or type (attendance, leave, pending) | **Holds** (F1 fix; three tests) |
| Blank tag, orphan tag, Inactive staff | **Holds**: left out of total and cuts alike |
| All companies minus each company | **Breaks for movers between companies: G1** |
| Window total minus the shown buckets | **Holds**: series are sent only when every bucket passes (F2), and attendance is whole-or-nothing (M2) |
| Chip minus chip (for example 30 days minus 7 days) | **Holds** as before. Every bucket of the longer chip has 5 or more people. A single day can only be got by visiting on two days in a row, which is R2 |
| Company attendance minus the branches it shows, when one branch is hidden by M2 | **Only a rough estimate.** The M2 guard is not sibling-aware, but only percentages are sent. The days behind them are not. Worry W4 |
| Caller's own days taken out of a 5-person bucket | **Breaks slightly: G2** |
| Leave types across chips | **Holds** now (F3) |

**W4 (worry, not a finding).** Company absent % minus the branches' absent % can give a rough figure for a branch that M2 hid. You would need the expected days, which are not sent. You could guess them from headcount × working days.

## SEC and PRIV, re-marked

| ID | Before | Now | Why |
|---|---|---|---|
| SEC-1 | Met | **Met** | Unchanged |
| SEC-2 | Met | **Met** | Unchanged |
| SEC-3 | Met | **Met** | Unchanged |
| SEC-4 | Met | **Met** | B2 fixed: `/api/method`, POST, token header; status codes kept. R12 still applies |
| SEC-5 | Met | **Met** | Only the `after_migrate` alias was removed; `make_role` still runs from hooks (03 §10 item 8; integrity check per engineer, not run by me) |
| SEC-6 | Partial | **Partial** | F5 line not written; AC-10's text is still wrong |
| SEC-7 | Met | **Met** | New SQL slots are constants (`COUNTED_SQL`, `e.{dim}` from a fixed tuple) or parameters. 362 → 362 |
| SEC-8 | Met | **Met** | Unchanged |
| SEC-9 | Met | **Met** | Flaky log test now checks values (engineer; not run by me) |
| SEC-10 | Met | **Met** | Still no cache |
| PRIV-1 | Partial | **Partial** | F4 open, waiting for Surbhi |
| PRIV-2 | Met | **Partial** | G2: the new M2 count includes the caller |
| PRIV-3 | Met | **Met** | Unchanged |
| PRIV-4 | Partial | **Met** | F2 fixed and tested |
| PRIV-5 | Met | **Met** | Unchanged |
| PRIV-6 | Partial | **Partial** | F1 fixed inside a company; G1 across companies |
| PRIV-7 | Met | **Met** | Unchanged |
| PRIV-8 | Partial | **Met** | F3 fixed |
| PRIV-9 to PRIV-12 | Met | **Met** | Unchanged |
| PRIV-13 | Partial | **Partial** | Still the people family only; the F1 cases are hand-written tests, not generated ones |

**Counts:** SEC 9 met, 1 partial, 0 not met. PRIV 9 met, 4 partial, 0 not met (before: 8 and 5).

## Before dev

1. Fix G1 with its test. Fix G2 (one line). Surbhi decides G3.
2. Write the F5 line in the admin guide, and correct AC-10 in 02.
3. One read-only count per tenant on a dev copy, with Surbhi's word: rows whose company differs from the person's Employee company (G1). Counts only, no names.

## Residual risks needing a name and a date

None is accepted yet. Each is one sentence Surbhi can accept or reject. Proposed owner: Surbhi, unless stated.

1. **R1.** A leader can narrow a figure to a range, not an exact number, by combining different filters.
2. **R2.** A leader who visits every day can see how each day changed.
3. **R3.** Short stretches where week and month buckets overlap are not checked on their own.
4. **R4.** A leader can combine the page with what they already know (who was missing from the floor), and no counting rule can stop that.
5. **R5.** Two leaders who pool their screens, or one who looks before and after the minimum changes, can learn more than either view shows.
6. **R6.** HR Analytics still treats a store HR person with a narrowed Branch permission as company-wide (ALV-359). People trends cannot be reached this way. **Dangerous debt, escalated**; owners: Surbhi (live check) and the engineer (fix).
7. **R7.** We cannot detect a leader misusing figures inside their own scope.
8. **R8.** The security log is about 2 MB and held in France, not India. Owner: founder.
9. **R10.** Early-leaver figures can show a lower limit for a small group, as designed.
10. **R11.** Leave figures are about everyone on the roll, not only people with attendance rows (Surbhi's decision 1, 24 Nov; not yet written as an acceptance).
11. **R12.** A session with no saved CSRF token skips Frappe's CSRF check (`frappe/auth.py` 87). Low risk here, because the endpoint only reads.
12. **R13.** Removing only a branch head's Branch permission widens them to the whole company, until the admin line (F5) tells admins not to do that.
13. **R14 (new).** "Your records start on {date}" shows the company's earliest joining date (F4), as the prototype draws it.
14. **R15 (new).** A branch hidden by the M2 guard can be roughly estimated from the company and sibling percentages (W4).
15. **R16 (new, only if Surbhi keeps G3 as built).** Absent % can be about fewer than 5 people when most people with rows were on leave.

**Baseline:** the CERT-In entry is still stale (last checked 24 Aug). This round relies on it only for R8.

## Subtract pass (round 1)

Removed from my draft: a finding that the JS sends no token when `frappe.csrf_token` is "None" (the server then refuses, or R12 applies, so the page fails safe); a note on the `scope_company` key that both helpers write (same value, proven); a worry about "days left out" (one company-level figure, the same on every view, so there is nothing to subtract).

# Final check round 2 (24 Nov 2026)

**Read at:** worktree `.claude/worktrees/090-leadership-hr-analytics`, branch `slice/090-leadership-hr-analytics`, commit **5eeef770** (on `origin/dev` a269ce00). I read the diff e0fe98ad..5eeef770 of `people_trends.py` and `people-trends.js`, the six new tests, 03 §11, and 02 "Decisions after review" and §13. **Not done:** I ran no test and nothing in `alv090-*`. I changed no source and committed nothing. Same conflict of interest as before: I wrote 01c.

## Verdict

**Not ready for dev: one new P1 (H1), caused by the softer guard. No P0.** Everything asked for in round 1 is fixed.

## What round 2 fixed (all proven in code; tests read, not run by me)

| Item | Result |
|---|---|
| G1 | **Fixed.** A row counts only when its company is the person's Employee company (`_rows_of_counted_people`, `{row_company} = e.company`). Attendance and leave queries group by `a.company`; Pending uses `l.company`. Test: `test_all_companies_is_the_sum_of_the_companies_for_a_person_who_moved` |
| G2 | **Fixed.** The caller is taken out of the per-bucket count (`own_emp` in `_attendance_bins`), also on By company. Test: `test_the_guard_leaves_the_caller_out` |
| Expected people | **Built as decided.** Only people with a Present, WFH, Half Day or Absent row count (`expected > 0`). Test: `test_absence_counts_only_people_expected_at_work` |
| Softer guard | **Built as decided**, with the one-hidden carve-out (`window_hidden`). The headline skips a hidden figure (`_headline` checks `absent_pct is not None`). `change()` shows nothing when the figure is hidden |
| Records start | **Fixed.** `get_first_day` for `records_start` and a clipped start. Test plus a DOM check |
| F5 | **Written** in 02 §13. AC-10 now matches the code |

## New finding

### H1 · Major · P1 · Another period button gives back the point the softer guard hid

**Where.** `_bin_lengths` (line 176): the 30-day view's last bucket is the last 7 days. The 7-day view's buckets are those same 7 days, one by one. The 90-day view's window is exactly the 180-day view's last three buckets. Its comparison window is exactly the first three.
**Scenario.** A branch head opens the 7-day view of their store. Sunday had 3 people at work, so Sunday is hidden and so is the window figure. The other six days show. They press 30 days. Its last point is the absent % for the same 7 days, and it is shown, because 7 days pooled has more than 5 people. Sunday = (that point × all expected days − the six daily points × their days) ÷ Sunday's days. A branch head knows the roster, so they know the days. Rounding to one decimal gives an error of about ±4 points. Each of 3 people is worth about 33 points, so the result says exactly how many of the 3 were absent. **Labels:** the bucket layout is proven in code. That the 30-day point is shown is inferred. The arithmetic was not run.
**The same thing in a bigger form:** in the 180-day view one hidden month among the first three comes back from the 90-day view's "before" figure, less the two months shown.
**Round 1 did not have this.** It held back the whole card on a thin chip, so no fine points sat next to a coarse one.
**Neither option in 03 §11 closes it.** Hiding the window figure does not help, because the 30-day point carries that figure anyway.

**Recommendation for Surbhi (one choice):** if any bucket on a view is thin, send **no chart points** on that view. **Keep** the window figure and the "before" figure (each covers 5 or more people). The 7-day Sunday case then has nothing to subtract from. The `window_hidden` carve-out is no longer needed, and R17 below goes away. The change is small: drop the series when `thin` is not empty, then add one test that the 7-day and 30-day views together give no hidden point. This goes against her words "a thin bucket hides only its own point". So it is her decision, not mine.

## Trying to break it (round 2)

| Attack | Result |
|---|---|
| All companies minus each company, with a person who moved | **Holds** (G1) |
| Window minus shown buckets, exactly one hidden | **Holds inside one view.** **Breaks across views: H1** |
| Two or more hidden buckets, inside one view | **Not rough when the hidden buckets are one quiet stretch.** The same 1-4 people sit behind each one, so the pooled figure is about them. It is as exact as the one-bucket case (R17) |
| Two or more hidden, across views | **Breaks**: H1 brings one back, and then the window figure gives the rest |
| Branch hidden, company point minus the sibling branches' points | **Rough**, because you need every sibling's daily expected days. Same as W4 (R15) |
| All companies minus companies, one company's By-company % hidden | **Rough**, same kind as R15 |
| Comparison window thin | **Holds**: `before` is dropped (`cmp_state`) |

## SEC and PRIV, final

SEC-6 is now **met** (F5 line, AC-10). PRIV-1 is **met** (F4). PRIV-2 is **met** (G2). PRIV-6 is **met** (G1). PRIV-7 ("shown figures must not rebuild a hidden one") is now **partial** (H1). PRIV-13 is still **partial**: the property test covers only the people figures. That is why H1 got through.

**Counts:** SEC: 10 met, 0 partial, 0 not met. PRIV: 11 met, 2 partial (PRIV-7, PRIV-13), 0 not met.

## Final residual risks (none accepted yet; each needs a name and a date)

Owner is Surbhi unless stated.

1. **R1.** A leader can narrow a figure down to a range by combining filters.
2. **R2.** A leader who visits every day can see how each day changed.
3. **R3.** Week and month buckets in different views overlap without lining up, and the slivers between them are not checked.
4. **R4.** A leader can combine the page with what they already know, and no counting rule can stop that.
5. **R5.** Two leaders who pool their screens can learn more than either one sees.
6. **R6.** HR Analytics still treats a store HR person with a narrowed Branch permission as company-wide (ALV-359). This page cannot be reached that way. **Dangerous debt, escalated.** Owners: Surbhi (live check), engineer (fix).
7. **R7.** We cannot detect a leader misusing figures inside their own scope.
8. **R8.** The security log is about 2 MB and held in France. Owner: founder.
9. **R10.** Early-leaver figures can show a lower limit for a small group, as designed.
10. **R11.** Leave figures cover everyone on the roll, not only people expected at work (your decision, 24 Nov).
11. **R12.** A session with no saved CSRF token skips Frappe's CSRF check. Low risk, because the page only reads.
12. **R13.** Removing only a branch head's Branch permission widens them to the whole company. The admin line now warns about this.
13. **R15.** A branch's hidden point can be roughly estimated from the company point less its sibling branches.
14. **R17 (only if you keep the build as it is).** With two or more hidden buckets in one quiet stretch, the window figure gives those few people's absent % about as exactly as one hidden bucket would.
15. **Temporary debt.** The property test covers only the people figures, and the By-company guard has no test of its own. Owner: test engineer.

R14 (F4) and R16 (G3) are closed by your 24 Nov decisions. **Baseline:** the CERT-In entry is still stale (24 Aug). Only R8 relies on it.

## Subtract pass (round 2)

I removed a note on the `change()` text when the window is hidden (it returns nothing, proven) and a worry about `records_start` (the people figures are unchanged, per the engineer and my reading of `_build`). I also dropped the sibling case under the softer guard as a new finding, because it is R15 again.
