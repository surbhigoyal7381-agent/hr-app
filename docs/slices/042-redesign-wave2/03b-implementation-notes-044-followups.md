---
slice: 042-redesign-wave2
artifact: 03b-implementation-notes (slice 044's recommendations R1, R4, D6, R2, R3)
author: hrms-fullstack-engineer
date: 2026-09-24
status: built and measured LOCALLY only. Not pushed, not merged into dev, no server, no tenant
branch: slice/042-redesign-wave2, fast-forwarded onto slice/044-scale-fixtures
bench: own container hrlocal-042s, mounting slice 044's sites volume. hrlocal-bench not used
---

# Acting on slice 044's measurements

A separate file from `03-implementation-notes.md` on purpose: that one is Wave 2's own
record of what it built, and `slice/043-redesign-wave3` sits on top of this branch. A new
file cannot conflict with either.

## Said first

**1. `get_home` drops from 30–31 queries to 26–28, and every duplicate is gone.** Not
"eight duplicates" — **four or five**, and that difference matters. Slice 044 counted
statements whose SQL text matched; three of the eight were `tabDocType` existence checks
for three *different* doctypes, which are three different questions and not repeats. The
ones that really were repeats, measured with their parameters:

| Repeated with the same parameters | Times, before |
|---|---|
| the caller's Holiday List Assignment | 2 |
| their company (read inside that lookup) | 2 |
| the company's Holiday List Assignment | 2 |
| their direct reports | 2 (a manager: 3) |
| for an HR caller, the whole permitted-employee list | 2 |

**2. R4 is the one that was worth doing, and it is a wall-clock fix, not a count fix.**
The System Manager's bell at 981 people goes **118.6 ms → 56.9 ms** (p50) and their Inbox
**188.4 ms → 109.6 ms**. The slope between a 20-person tenant and a 981-person one drops
from **×3.9 to ×2.4** on the bell and **×5.3 to ×3.1** on the Inbox.

**3. The `_presence_counts` cap is gone, and the card is faster as well as honest.**
At 1,001 people it used to count the first thousand and draw the answer as if it were the
whole tenant. No error, no warning.

**4. Flatness holds, and it is now the gate.** Every call takes **exactly the same number
of queries on a 20-person site as on a 981-person one**, for all five personas, before
and after. The counts are recorded as a note.

**5. What got worse.** One query more for a plain employee on `get_nav_counts` and
`get_inbox` (12 → 13 each), and a browser-side number I could not measure at all. Both
are in §6.

---

## 1. What changed, file by file

| File | Mechanism | Why this one |
|---|---|---|
| **NEW** `alvoraa_portal/call_cache.py` | build | A memo that lives for one call. Opened at the top of `get_home`, thrown away in a `finally` whether the call returns or raises. **With no call open it does not memoise at all**, which is what makes it safe to put inside a shared helper |
| `alvoraa_portal/home_api.py` | extend | The memo's lifecycle; `_reports` and `_hr_scope` asked once; the holiday lookup through `call_cache.holiday_list_for`; `_peers` folded into a new `_scope_filters`; `_presence_counts` rewritten as two aggregates |
| `alvoraa_portal/hr_api.py` | extend | One hunk: `_own_upcoming_holidays` takes the holiday list from `call_cache.holiday_list_for` instead of calling ERPNext directly. Line ~336 — clear of slice 043's hunks, which all start at line 1598 |
| `alvoraa_portal/goals_api.py` | extend | **NEW** `_pending_approvals_scope_query` is the definition now, and it is a subquery. `_pending_approvals_scope` runs it rather than repeating its rule. `get_pending_approvals_count` takes the subquery |
| `alvoraa_portal/inbox_api.py` | extend | `_part_goal_updates` holds the subquery in its one filter expression instead of a list of names |
| `tests/test_frame_endpoint_registry_034.py` | extend | Re-counted, and **it now watches two calls it never watched** — see §4 |
| **NEW** `tests/test_no_repeat_queries_044.py` | build | Eleven tests. Four fail on this morning's code |
| `docs/.../02-functional-spec.md`, `07-devops-inputs.md`, `.claude/context/nfr-budget.md` | — | R2 and R3: the measured numbers, and flatness as the gate |

### R1 — the memo, and why it is not a cache

Wave 1's **W1D-23** says in writing that memoising `permitted_companies` is *not* the
answer, because a memo that outlives a request hands a background job a stale scope — an
HR person removed from a company at 10:00 would keep seeing it. **That still stands, and
this does not break it.**

`call_cache` keeps an answer for the next line of the same function. No key outlives the
call, nothing reaches redis or the session, and the teardown is in a `finally`. Within
one `get_home` there is no staleness window at all, because nothing inside `get_home`
writes. Four tests exist only to hold that line: after a normal return, after an
exception, between two consecutive calls, and outside a call — where `once()` must run
the function every time.

I did **not** memoise the three `tabDocType` existence checks. They ask about three
different doctypes, so a per-call memo saves nothing; `inbox_api._has_doctype` already
caches that answer *across* requests, keyed by build version, and adopting it in
`home_api` would take `get_home` three queries lower. That is a cross-request memo and
the instruction for this piece of work was request-scope only, so **it is left as a
recommendation, not done** (§7 R-a).

### R4 — a subquery, not a cap

The choice was "push the scope into the query, or cap it". **I pushed it.** A cap makes
the number wrong instead of slow, and a silently wrong number is the defect this project
keeps finding — `_presence_counts` in the same slice is the proof.

```
employee IN (SELECT name FROM tabEmployee WHERE status='Active'
             AND name<>'…' AND (company IN (…) OR reports_to='…'))
```

`frappe.qb.get_query("Employee", fields=["name"], filters=…, or_filters=…)` builds it —
verified in the installed source at `apps/frappe/frappe/database/query.py:215` and
`query_builder/utils.py:62`, and the SQL it emits was read before it was used, not
assumed. The values are inlined as literals, so there are no bound parameters at all
where there used to be 981.

The rule is unchanged. One difference, deliberate: `name != emp_id` now applies to the
direct-reports half as well as the company half. Nobody reports to themselves, so it
removes nobody it did not already remove.
`test_the_subquery_scope_matches_the_list_scope_exactly` writes slice 042's rule out
again in Python and checks the two agree on the fixture, for a manager, an HR caller and
a plain employee.

**A latent fail-open, found by writing the test.** The old helper handed a caller with
`emp_id = None` and `is_hr = True` **every active person in the site's companies** — 36
of them on the test fixture. No caller reaches it that way today (`_require_employee()`
and `available = bool(who.employee)` both guard it), so nothing leaked. It failed open,
and it now returns `name IN ()`, which matches nothing.

### D6 — the team card

Two problems in one line: `_presence_counts(names[:LIST_CAP * 20], date_)` counted up to
a thousand people, and `_suppress(counts, len(names))` applied the minimum-group rule to
the real size. Above a thousand the two came from different populations.

The group is a condition on Employee now, built from `permitted_employee_filters()` — the
shared scope helper, not a rule of its own. One statement counts the group; one counts
today's Attendance by status; "still to come" is the subtraction, clamped at zero.

**Which way round the second statement runs, measured rather than reasoned:**

| Shape | System Manager, 981 people | Company HR, 245 people |
|---|---|---|
| drive off Attendance's date index (**shipped**) | **12.0 ms** | **13.9 ms** |
| `LEFT JOIN` out from Employee (my first attempt) | 51.9 ms | 16.5 ms |
| the old name list | 52.9 ms | 25.2 ms |

The first version I wrote was the `LEFT JOIN`, and it was the slowest statement on Home.
It is in its own commit so the change is readable; I am not presenting the second attempt
as the first.

Two statements, which is what the old name-list shape also took, so the card costs what
it always cost and is now right at any headcount.

---

## 2. The measurements

**Method.** Slice 044's own harness, unedited: `measure_044.run`, three warm-up calls
then 20 measured with nothing written in between, queries counted by wrapping
`frappe.db.sql`. Same two sites, reused, not rebuilt. Baseline taken on this branch
before any edit, so the before and after are the same rig.

### Queries — the numbers that are exact and reproducible

| Call | Persona | Before | After | 20 people = 981 people? |
|---|---|---|---|---|
| `get_frame` | employee / manager | 3 | 3 | yes |
| `get_frame` | store HR / company HR / System Manager | 5 | 5 | yes |
| `get_nav_counts` | employee | 12 | **13** | yes |
| `get_nav_counts` | manager | 14 | **13** | yes |
| `get_nav_counts` | store HR / company HR | 23 | **21** | yes |
| `get_nav_counts` | System Manager | 18 | **16** | yes |
| `get_home` | employee | 30 | **26** | yes |
| `get_home` | manager | 31 | **27** | yes |
| `get_home` | store HR / company HR | 30 | **27** | yes |
| `get_home` | System Manager | 31 | **28** | yes |
| `get_inbox` | employee | 12 | **13** | yes |
| `get_inbox` | manager | 21 / 18 | **20 / 17** | yes |
| `get_inbox` | store HR | 28 / 26 | **26 / 24** | yes |
| `get_inbox` | company HR | 28 | **26** | yes |
| `get_inbox` | System Manager | 25 / 22 | **23 / 20** | yes |
| `get_staff_list` | HR personas | 2 | 2 | yes |
| `get_team_scorecard` | manager | 10 | 10 | yes |

Where two numbers are given they are the 20-person site and the 981-person site. The
difference is not headcount: a part with a count of zero skips its rows query, and which
parts are empty differs between the two fixtures. It moves the wrong way for an N+1,
which is the direction that matters.

### Wall time — the slopes R4 was about

p50 in milliseconds, best of two runs after, one run before.

| Persona | Call | 20 people | 981 people | Slope before | Slope after |
|---|---|---|---|---|---|
| System Manager | `get_nav_counts` | 30.6 → 23.5 | **118.6 → 56.9** | ×3.9 | **×2.4** |
| System Manager | `get_inbox` | 35.3 → 35.6 | **188.4 → 109.6** | ×5.3 | **×3.1** |
| System Manager | `get_home` | 32.0 → 35.0 | 76.6 → 51.8 | ×2.4 | ×1.5 |
| company HR | `get_inbox` | 42.1 → 42.7 | 93.7 → 66.7 | ×2.2 | ×1.6 |
| company HR | `get_nav_counts` | 34.8 → 32.8 | 64.4 → 52.5 | ×1.9 | ×1.6 |
| company HR | `get_home` | 36.3 → 34.7 | 68.8 → 54.3 | ×1.9 | ×1.6 |
| store HR | `get_inbox` | 44.5 → 36.1 | 85.5 → 43.3 | ×1.9 | ×1.2 |
| store HR | `get_home` | 37.6 → 29.3 | 65.6 → 48.9 | ×1.7 | ×1.7 |
| employee | `get_home` | 35.2 → 33.9 | 67.3 → 50.2 | ×1.9 | ×1.5 |
| employee | `get_nav_counts` | 17.1 → 20.7 | 25.4 → 22.9 | ×1.5 | ×1.1 |

**An honest warning about every wall-clock number above.** This machine runs eight other
slice containers and other sessions were testing while I measured. `get_frame` is
untouched by this work and its p50 moved by up to ×2.6 between runs, which puts a floor
under how much of any single reading to believe. The numbers I would defend are the query
counts (exact, identical across runs and across both sites), the SQL-time profiles below,
and the *direction and size* of the big slopes — a 118.6 ms bell becoming 56.9 ms is
larger than the noise; a 3 ms move is not.

### Where the time went — `profile`, which times each statement

| Call, persona, 981 people | SQL time before | SQL time after |
|---|---|---|
| `get_nav_counts`, System Manager | 67.5 ms, 18 statements | **25.0 ms, 16 statements** |
| `get_home`, plain employee | 32.0 ms, 30 statements | 26 statements |
| `get_home`, company HR | — | 34.0 ms, 26 statements |

The two statements slice 044 named as the cause — `COUNT(*) … WHERE employee IN (981
parameters)` at 11.8 ms and 11.1 ms — are gone from the profile entirely. The
subquery form of the same count costs **1.1 ms**.

### Payload — unchanged, and nowhere near budget

`get_nav_counts` 638 B against ≤ 1 KB, `get_home` 1,470 B against ≤ 30 KB, `get_inbox`
18,351 B against ≤ 60 KB. Identical to slice 044's figures: nothing in this work changed
what is sent.

---

## 3. The budgets, moved (R2) and demoted (R3)

Following **W1D-23**'s precedent: accept the measured number, write it down, and say why
in one line.

| Budget | Was | Measured before | Measured after | Now reads | The one-line reason |
|---|---|---|---|---|---|
| `get_home` queries | ≤ 20 | 30–31 | **26–28** | **28**, flat | Wrong by half the day it was written, and wrong at twenty people too — never a scale failure |
| `get_nav_counts` queries | ≤ 15 (042), ≤ 20 (W1D-23) | 23 | **21** | **21**, flat | Same: both numbers were guesses, and both failed identically at twenty people |
| `get_inbox` queries | ≤ 25 | 26–28 | **24–26** | **26**, flat | Same |
| `get_frame` queries | ≤ 15 | 3–5 | 3–5 | **5**, flat | Measured for the first time. Generous, not wrong |
| p95, all three | ≤ 500 ms | ≤ 276 ms | **≤ 215 ms** | unchanged | It passes everywhere and always did |

Written into `02-functional-spec.md` AC-15 and §13, `07-devops-inputs.md` §4's endpoint
table and its measurement plan, and `.claude/context/nfr-budget.md`'s "queries per
request" row — which also gains a row saying a scope belongs in the query, not in an
`IN (...)`.

**R3 is done in those same edits:** every row now says *flat in headcount — that is the
gate*, with the count as a recorded note so drift stays visible. A change that moves a
count by one and keeps both properties is fine; a change that keeps the count and breaks
flatness is not.

**One number I did not move, because it is not mine to move.** Wave 1's own
`docs/slices/034-redesign-wave1/02-functional-spec.md` AC-24 and §13 still read ≤ 20 for
an HR caller. `slice/034-redesign-wave1` is a different branch that has to reach `dev`
before this one, and editing another slice's spec from here would conflict on the way in.
**It needs the same edit — 21, measured — and that is a decision for you, not a change I
should make quietly.**

---

## 4. The seven dimensions, against the code I actually wrote

| Dimension | Verdict | One line |
|---|---|---|
| **Performance** | **improves** | Four to five duplicate statements gone from `get_home`; the System Manager's bell 118.6 → 56.9 ms and Inbox 188.4 → 109.6 ms at 981 people; `get_nav_counts` SQL time 67.5 → 25.0 ms. One query more for a plain employee on two calls (§6) |
| **Scalability** | **improves** | The widest slope in slice 044's measurement, ×5.3, is now ×3.1, and the scope that caused it no longer grows with the tenant at all. The team card's thousand-name cap is gone |
| **Security** | **improves** | A latent fail-open in `_pending_approvals_scope` now fails closed. The bypass registry watches `frappe.qb.get_query` and `frappe.qb.from_` for the first time, which makes four query-builder reads in the Inbox *declared* rather than merely unseen. No `ignore_permissions` added; every scope still comes from the shared helpers |
| **Reliability** | **neutral to improves** | The memo's teardown is in a `finally`, with a test that raises inside `get_home` and asserts nothing was left open. "Still to come" is clamped at zero rather than able to draw a negative. No new external call, no new job |
| **Maintainability** | **improves, with one honest cost** | `_pending_approvals_scope` and its query are one definition in two shapes, so they cannot drift — the pattern `permitted_employees` / `permitted_employee_filters` already uses. `_peers` is gone, folded into one `_scope_filters`. **The cost:** the Inbox part's filter expression now carries a query-builder object, which is less obvious to read than a list of names, and `_filter_list` in `home_api` translates a Frappe filter dict into conditions — a small piece of machinery that did not exist |
| **Data integrity** | **improves** | The team card's numbers and the group size the suppression rule is applied to now come from the same statement, so they cannot describe different populations. Nothing is cached beyond one call, so no stale read is possible |
| **Compliance / privacy** | **neutral** | No new field, no new row, no widened visibility. The presence counts are still three integers with the status collapsed inside the SQL, so a leave *type* cannot reach a caller. Nothing new is logged; no log line gained a name, an id or a reason. `get_home`'s key set is unchanged and its test still holds it |

**Multi-tenancy.** Every query I touched scopes through `permitted_companies()`,
`permitted_employee_filters()` or `reports_to`, and none of them is memoised past the
call. The subquery carries the company condition *inside* the SQL, which is if anything
harder to bypass than a list assembled in Python.

**Accessibility, i18n, upgrade-safety.** Untouched. No user-facing string changed, no
template changed, nothing in `apps/frappe`, `apps/erpnext` or `apps/hrms` upstream was
edited — the one `hrms` file is `alvoraa_hr_core`, which is ours, and it was only read.

---

## 5. Tests, and what was actually run

**One `bench run-tests` at a time**, on my own container against site `test044f`.
`pgrep -af run-tests` and `docker ps` checked first; `hrlocal-bench` never used.

| Module | Result |
|---|---|
| **NEW** `test_no_repeat_queries_044` | **11 ran, OK** (127 s) |
| `test_scale_flatness_044` (044's guard, unedited) | **11 ran, OK** (307 s) |
| `test_home_api_042` | **23 ran, OK** |
| `test_inbox_parts_042` | **24 ran, OK** |
| `test_inbox_counts_034` | **17 ran, OK**, plus its 2 doctype-cache tests **OK** |
| `test_frame_endpoint_registry_034` | **8 ran, OK** — after the declaration was corrected; it went red first, which is the test doing its job |
| `test_staff_list_034` | **22 ran, OK** |
| `test_frame_api_034` | **33 ran, OK** |
| `test_home_holidays_035` | **8 ran, OK** |
| `test_numbers_match_035` | **6 + 7 ran, OK** |
| `test_ess_parts_034` | **8 ran, OK** |
| `test_panel_source_042` | **7 ran, OK** |
| `test_week_presence_retired_042` | **2 ran, OK** |
| `test_evidence_and_updates` | **8 ran, OK** |
| `test_team_scope_034` | **19 ran, OK** |
| `python scripts/check_app_integrity.py` | **638 checks, OK** — before every commit |

### Each fix has a test that fails without it — run, not assumed

The four changed source files were put back to this morning's state, `call_cache` replaced
by a no-op stand-in so the imports still resolved, and the new module run again:

| Test | Failure on the old code |
|---|---|
| `test_get_home_asks_no_question_twice` | `x2` on the Holiday List Assignment |
| `test_no_list_cap_is_applied_to_the_presence_numbers` | `0 != 30` — the card counted none of the manager's thirty reports |
| `test_the_scope_is_not_shipped_back_as_a_list` | 30 bound parameters in the SQL where there should be none |
| `test_nobody_is_in_scope_for_a_caller_with_no_employee_record` | a list of 36 employees where it should be empty |

`FAILED (failures=4)`. The other seven are guards on the guards, and one of them — the
spy shown a real repeat — is the reason a green run of the first test means something.

---

## 6. What got worse, and what I could not measure

| # | What | Label |
|---|---|---|
| W1 | **A plain employee's `get_nav_counts` and `get_inbox` each take one query more** — 12 → 13. The old code read the caller's direct reports (one query), found none, and short-circuited the goal-updates part with `no_rows()`, so it ran no counting query at all. The new code has no list to look at, so the two counting queries run against a subquery that returns nothing. Measured cost: **1.1 ms** of SQL, against the 1 query and ~0.4 ms the old path spent building the list. Restoring the short-circuit would cost a manager and an HR caller a query each instead, so it is a choice between personas, not a free fix | **intentional trade-off** |
| W2 | **`get_home` is one query above what R1 alone would have given** (27 not 26 for a manager), because the honest team card takes two statements instead of one. It buys 40 ms off the System Manager's Home | **intentional trade-off** |
| W3 | **AC-31 (skeleton ≤ 300 ms) and AC-40 (Home usable ≤ 2.5 s) are still not run.** Browser numbers, no timing rig. Slice 044 said the same. Wave 1's `scripts/browser_check_frame.js` is where they belong | **acceptable simplification** — out of scope by instruction |
| W4 | **Wall-clock p95 before-and-after is not trustworthy on this machine** (§2). Several p95 readings moved *up* on calls this work does not touch | **acceptable simplification** — the query counts and SQL profiles carry the claim instead |

## 7. Recommendations, not done

| # | Recommendation | Why it is not in this commit |
|---|---|---|
| R-a | **Adopt `inbox_api._has_doctype` in `home_api`** and `get_home` drops three more queries, to 23–25. It is an existing, reviewed mechanism with the build version in its key and its own two tests | It memoises *across* requests, and the instruction for this work was request-scope only. Your call |
| R-b | **`_goals`' team summary counts the goals of the first `LIST_CAP` people only** — `names[:LIST_CAP]`, so above fifty people in scope the number on an HR caller's Home is quietly wrong. Same defect class as D6, in the same function I was in, and the fix is the same subquery | It changes a number the screen already shows, which needs your word. **Report it as a real defect, P2** |
| R-c | **`goals_api.get_pending_approvals` still walks one employee at a time** — the 16.4-second bell's own code. It now takes its scope from the subquery, so the two definitions cannot drift, but the loop is untouched | Not on a landing path, not measured in slice 044, and rewriting it is its own piece of work (ALV-113) |
| R-d | **Move Wave 1's AC-24 to 21** in `docs/slices/034-redesign-wave1/` | Another slice's spec on another branch (§3) |
| R-e | **A tenant above a thousand people has still never been measured.** D6's cap is gone, but nothing above 981 has been run | Slice 044's own gap. The fixture is 26 minutes; a bigger one is longer |

## 8. What else moved while I worked

| | |
|---|---|
| Incoming commits | **Five**, all from `slice/044-scale-fixtures`, brought in deliberately: `6856dbe` the two fixtures and the measurement harness, `da1e3b3` the flatness guard, `cdf2956` what leaving validation on found, `8464308` the profiler and the policy fixtures, `e847feb` the test report. I read the diff: three new test files and one document, **no application source at all** |
| How | **Rebase**, not cherry-pick. `slice/044-scale-fixtures` was cut from this branch and is a strict descendant of it, so `git rebase slice/044-scale-fixtures` was a fast-forward — my four commits sit on top of 044's five, and the history is linear |
| Conflicts | **None.** Slice 044 touched no file this work touches |
| Slice 043 | `slice/043-redesign-wave3` sits on top of this branch and **must rebase.** Its `hr_api.py` hunks all start at line 1598; my one `hr_api.py` hunk is at line ~336, so the rebase should be clean. Checked with `git diff 032c9c8 slice/043-redesign-wave3 -- hr_api.py` before I edited the file |
| Shared resources | Own container `hrlocal-042s`. It mounts slice 044's **sites volume** `hrlocal-044-sites` so the two fixtures are reused rather than rebuilt, and shares `hrlocal-044-redis`; slice 044 is finished and `hrlocal-044` was never run while mine was. `hrlocal-bench`, `test_site` and the main checkout were never written to. One `GRANT` was added on the shared local MariaDB so my container's address could reach the three site databases — additive, local, and it changed nothing for slice 044 |

## 9. Commits on this branch

| | |
|---|---|
| `75dde73` | R1 and D6's first form — the memo, and the team card counting everybody |
| `363cba5` | R4 — the approval scope stays in the database |
| `c4b77c2` | the eleven tests, four of which fail without the fixes |
| `9dc2849` | D6 turned round — the card drives off the date, not off the people |
| this file | R2 and R3 — the budgets moved and demoted |

**None of this authorises a deploy.** Nothing is pushed, nothing is merged into `dev`, no
server and no tenant were touched.
