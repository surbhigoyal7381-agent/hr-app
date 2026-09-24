---
slice: 044-scale-fixtures
artifact: 04-test-report
author: hrms-test-automation-engineer
date: 2026-09-24
status: measured LOCALLY only. Not pushed, not merged into dev, no server, no tenant
branch: slice/044-scale-fixtures, cut from slice/042-redesign-wave2
bench: own container hrlocal-044, own redis hrlocal-044-redis, own sites test044,
       test044s and test044f. hrlocal-bench not used
---

# Wave 2's untested numbers, measured

## Said first

**1. Query count is flat in headcount. That part of the design holds, and it is
proved, not asserted.** Every landing call takes the **same number of queries
for 20 people as for 981**, for every one of the five personas. There is no
query inside a loop anywhere on the Home or Inbox path. This was the property
Wave 1 moved a budget to protect (W1D-23), and it is real.

**2. Three query budgets in Wave 2's section 13 are wrong, and `get_home`'s is
wrong by half.** Measured, warm, steady state, at 981 people:

| Budget | Written | Measured | Verdict |
|---|---|---|---|
| `get_home` ≤ 20 queries | 20 | **30–31**, every persona | **fails by 50 %** |
| `get_nav_counts` ≤ 15 (Wave 1 moved it to 20) | 15 / 20 | **23** for store HR and company HR | **fails** |
| `get_inbox` ≤ 25 queries | 25 | **26–28** for HR personas | **fails** |

They fail at **20 people too, by exactly the same amount**. These are not scale
failures; the budgets were written without anyone counting.

**3. Wall time is NOT flat, even though the query count is.** The System
Manager's bell goes from **31 ms to 159 ms** (p50) between a 20-person tenant
and a 981-person one, and their Inbox from **60 ms to 230 ms**. The cause is
visible in the SQL: every scope is a list of every employee's id pulled into
Python and shipped back as an `IN (...)` of 981 parameters. Still inside the
500 ms budget at 981 — **the 500 ms p95 budget passes everywhere** — but it is
growing roughly linearly, so it is the number to watch, not the query count.

**4. No P0. Nothing leaked, nothing crashed, nothing was slow enough to hurt a
user today.** The 16.4-second bell has not come back: `_pending_approvals_scope`
is reused for its *scope* and never for its loop, and the measurement says so.

**5. What I could not check.** AC-31's 300 ms skeleton paint and AC-40's 2.5 s
"Home usable" are **browser** numbers. There is no headless-browser timing rig
in this repo and I did not build one, so both are **not run** and stay
untested. See "Not automated" below.

---

## 1. The fixtures, and what they cost

Two shapes, each on **its own site**, because a tenant here is a site, not a
company inside one. `permitted_companies()` hands a System Manager *every
company on the site*, so a 20-person tenant measured on a site that also held
981 people would not be a 20-person tenant at all.

| | LARGE | SMALL |
|---|---|---|
| Site | `test044` | `test044s` |
| People | **981** | **20** |
| Companies / stores | 4 / 16 | 1 / 1 |
| Manager tree | head → store manager → team lead → staff, 4 levels | manager → lead → staff |
| Open leave requests | 59, spread over 64 real approver logins | 3 |
| Attendance rows | 2,488 | 397 |
| Pending attendance corrections | 40 | 3 |
| Individual Goals / pending updates | 240 / 60 | 12 / 4 |
| Published policies nobody has accepted | 3 | 3 |
| Logins | 69 | 5 |

Headcount is **981, not 1,000** — the tree comes out at 980 plus one left over
from an early smoke test. Two per cent short of the round number; I have not
padded it to make a nicer headline.

### How long they take

| | Measured | Label |
|---|---|---|
| SMALL, from an empty site | **59 s** | **Ran it** — one clean build, timed by the fixture itself |
| LARGE, from an empty site | **≈ 26 min** | **Inference** from measured parts, see below |
| Either, when already built | **one query** (5.5 s through `bench execute`, almost all of it Frappe starting up) | **Ran it** |
| A site to put one on (`bench new-site` + 4 apps) | **≈ 12 min** | **Ran it**, three times |

The large figure is a composite and I will not dress it up as a single run. Its
parts, each measured on `test044`:

| Step | Measured |
|---|---|
| 4 companies, 16 branches, holiday assignments | 1.3–2.4 s |
| 69 logins | ~2 s |
| 980 employees | 601 in 13.0 min → **46/min → ≈ 21 min** |
| 980 Leave Allocations + 59 applications | ≈ 2.5 min, at the small build's measured rate |
| 2,488 Attendance rows | **105 s** |
| 40 corrections, 240 goals, 60 updates, 3 policies | ≈ 8 s |

### How to reuse them without rebuilding

1. **Do nothing.** The sites are the artifact. `build()` checks one default key
   and returns. Nothing needs rebuilding between runs or between slices.
2. **To hand one to somebody else, or to reset:**
   `bench --site test044 backup --with-files`, then `bench restore` on a new
   site. That is minutes, not half an hour.
3. **To build a fresh one:** one site config setting is needed first, because
   Frappe throttles user creation to sixty an hour and the large shape makes
   sixty-nine logins:
   `bench --site <site> set-config -p throttle_user_limit 5000`.
   The staff list is an **opt-in** feature and is off by default, so a site that
   should measure it needs `staff_list` added to the site's `features`.

### How the records were made

Through the ORM with validation left on, which cost time and earned it back
five times. Each of these is something a fixture that wrote rows in their final
shape would have sailed straight past, leaving a wrong answer looking right:

| What the app refused | What it means |
|---|---|
| `rebuild_tree()` takes one argument in this Frappe, not two | — |
| Frappe HR reads a **submitted Holiday List Assignment**, not the Company's `default_holiday_list`, and throws without one | A tenant configured the "obvious" way has no working leave at all |
| A leave approver is a **User**; a manager tree with no logins gives a tenant one approver | A fixture without this measures one approval queue and calls it a spread |
| Frappe throttles user creation to sixty an hour | Any bulk onboarding hits this |
| Attendance Request refuses a day whose attendance already says what the request would say | Corrections now land outside the attendance window |

Two deliberate bends, both the normal Frappe way of doing the same thing:
`ignore_update_nsm` during the bulk employee load with one `rebuild_tree` at the
end, and holiday lists assigned per **company** rather than per employee.

Everyone in both fixtures is invented. No real name, no real identifier,
nothing copied from any tenant.

---

## 2. The measurements

**Method.** `alvoraa_portal.tests.measure_044.run`. Per persona, per call: three
warm-up calls, then **20 measured calls with nothing written in between**.
Queries counted by wrapping `frappe.db.sql`, which every read goes through
including the query builder. Payload measured as JSON bytes. p95 is nearest
rank over the 20 — the second worst, not an interpolation that hides it.

This is the method Wave 2's first attempt got wrong: it inserted rows between
two readings, and inserting clears caches, so it compared a warm call with a
cold one and read the difference as an N+1.

**Ran it**, twice on the large site and once on the small, one at a time, on my
own container against my own sites. `docker ps` and `pgrep -af run-tests`
checked first; `hrlocal-bench` was never used.

### Queries — 20 people against 981

| Call | Persona | 20 | 981 | Flat? |
|---|---|---|---|---|
| `get_frame` | employee | 3 | 3 | yes |
| `get_frame` | manager | 3 | 3 | yes |
| `get_frame` | store HR / company HR / System Manager | 5 | 5 | yes |
| `get_nav_counts` | employee | 12 | 12 | yes |
| `get_nav_counts` | manager | 14 | 14 | yes |
| `get_nav_counts` | store HR | 23 | 23 | yes |
| `get_nav_counts` | company HR | 23 | 23 | yes |
| `get_nav_counts` | System Manager | 18 | 18 | yes |
| `get_home` | employee | 30 | 30 | yes |
| `get_home` | manager | 31 | 31 | yes |
| `get_home` | store HR / company HR | 30 | 30 | yes |
| `get_home` | System Manager | 31 | 31 | yes |
| `get_inbox` | employee | 12 | 12 | yes |
| `get_inbox` | manager | 21 | 18 | yes (fewer, see note) |
| `get_inbox` | store HR | 28 | 26 | yes (fewer) |
| `get_inbox` | company HR | 28 | 28 | yes |
| `get_inbox` | System Manager | 25 | 22 | yes (fewer) |
| `get_staff_list` | HR personas | 2 | 2 | yes |
| `get_staff_list` | employee / manager | refused | refused | correct |
| `get_team_scorecard` | manager | 10 | 10 | yes |
| `get_team_scorecard` | everyone else | 2 | 2 | yes |

*The note.* `get_inbox` takes a **few fewer** queries on the big tenant for
three personas. That is not headcount: a part with a count of zero skips its
rows query, and which parts are empty differs between the two fixtures. It
moves the wrong way for an N+1, which is the direction that matters.

### Wall time and payload, at 981 people

**Ran it.** p50 / p95 in milliseconds over 20 warm calls; bytes is the JSON
payload.

| Persona | Call | p50 | p95 | bytes |
|---|---|---|---|---|
| employee | `get_frame` | 20.9 | 27.8 | 1,297 |
| employee | `get_nav_counts` | 65.3 | 102.8 | 634 |
| employee | `get_home` | 92.8 | 150.4 | 1,443 |
| employee | `get_inbox` | 47.4 | 59.3 | 1,283 |
| employee | `get_team_scorecard` | 15.0 | 25.9 | 15 |
| manager | `get_frame` | 13.6 | 18.9 | 1,299 |
| manager | `get_nav_counts` | 45.7 | 54.1 | 637 |
| manager | `get_home` | 60.9 | **88.2** | 1,448 |
| manager | `get_inbox` | 61.5 | 83.1 | 5,104 |
| manager | `get_team_scorecard` | 27.9 | 34.9 | 5,191 |
| store HR | `get_frame` | 13.9 | 23.6 | 1,364 |
| store HR | `get_nav_counts` | 96.9 | 191.4 | 636 |
| store HR | `get_home` | 61.5 | 74.9 | 1,463 |
| store HR | `get_inbox` | 107.0 | 149.3 | 10,775 |
| store HR | `get_staff_list` | 5.3 | 7.7 | 1,523 |
| company HR | `get_frame` | 14.2 | 16.7 | 1,368 |
| company HR | `get_nav_counts` | 102.5 | 165.2 | 638 |
| company HR | `get_home` | 85.3 | 166.2 | 1,470 |
| company HR | `get_inbox` | 112.9 | 170.2 | 18,351 |
| company HR | `get_staff_list` | 6.1 | 7.3 | 1,488 |
| System Manager | `get_frame` | 12.2 | 13.9 | 1,356 |
| System Manager | `get_nav_counts` | 158.6 | **246.5** | 638 |
| System Manager | `get_home` | 106.1 | 162.8 | 1,470 |
| System Manager | `get_inbox` | **230.0** | **275.9** | 18,351 |
| System Manager | `get_staff_list` | 5.6 | 7.6 | 1,485 |

### The same, at 20 people — the comparison that matters

| Persona | Call | p50 (20) | p50 (981) | Growth |
|---|---|---|---|---|
| employee | `get_nav_counts` | 31.2 | 65.3 | ×2.1 |
| employee | `get_home` | 48.0 | 92.8 | ×1.9 |
| manager | `get_home` | 45.1 | 60.9 | ×1.4 |
| store HR | `get_nav_counts` | 48.6 | 96.9 | ×2.0 |
| store HR | `get_inbox` | 78.0 | 107.0 | ×1.4 |
| company HR | `get_nav_counts` | 60.9 | 102.5 | ×1.7 |
| company HR | `get_inbox` | 56.8 | 112.9 | ×2.0 |
| System Manager | `get_nav_counts` | 31.2 | **158.6** | **×5.1** |
| System Manager | `get_inbox` | 59.7 | **230.0** | **×3.9** |
| System Manager | `get_home` | 47.6 | 106.1 | ×2.2 |

**Flatness holds in queries and does not hold in time.** Fifty times the people
costs between 1.4× and 5.1× the wall clock. Everything still lands inside the
500 ms budget at 981 people, and none of this is urgent — but on this slope a
5,000-person tenant puts the System Manager's bell near 800 ms, which is over
budget, and nobody would see it coming from the query count alone.

### Where the time actually goes

**Ran it** — `measure_044.profile`, which times each statement.

`get_nav_counts`, System Manager, 981 people: 18 statements, 67.5 ms in SQL.
The three slowest are all the same shape:

```
13.8 ms  SELECT name FROM tabEmployee WHERE status=%s AND name<>%s
         AND company IN (...4...) ORDER BY creation DESC
11.8 ms  SELECT COUNT(*) FROM `tabGoal Progress Update` JOIN `tabIndividual Goal`
         ... WHERE `tabIndividual Goal`.employee IN (981 parameters)
11.1 ms  SELECT COUNT(*) FROM `tabKPI Progress Log` JOIN tabKPI
         ... WHERE tabKPI.employee IN (981 parameters)
```

`goals_api._pending_approvals_scope` pulls **every** employee id into Python and
every reader ships the whole list back as `IN (...)`. It is one query, which is
why the count is flat — and it is a query whose cost grows with the company,
which is why the clock is not. There is no cap on that list.

`get_home`, plain employee, 981 people: **30 statements, 32.0 ms in SQL** — and
**eight of the thirty are repeats of a query already run in the same call**:

| Repeated query | Times |
|---|---|
| `tabHoliday List Assignment` for the same employee, same date | **4** |
| `tabDocType WHERE name=...` (the "does this doctype exist" check) | **3** |
| `tabEmployee WHERE reports_to=... AND status='Active'` | **2** |
| `tabEmployee WHERE name=... SELECT company` | **2** |

Cheap queries, but they are most of the distance between 30 and the budget of
20.

### Total page payload and render time

| | 20 people | 981 people | Budget |
|---|---|---|---|
| Home = `get_frame` + `get_nav_counts` + `get_home`, company HR | 3,465 B | **3,476 B** | no page budget written |
| `get_nav_counts` alone | 634 B | **638 B** | ≤ 1 KB — **passes** |
| `get_home` alone | 1,463 B | **1,470 B** | ≤ 30 KB — **passes, by 20×** |
| `get_inbox` alone, worst persona | 2,787 B | **18,351 B** | ≤ 60 KB — **passes** |
| Server time for one Home load (sum of the three p95s), System Manager | 110 ms | **423 ms** | — |
| Skeleton painted | — | **not run** | ≤ 300 ms |
| Home usable | — | **not run** | ≤ 2.5 s p95 |

Payload is flat and nowhere near its budgets. The `get_inbox` growth is rows,
not headcount: 18 KB is fifty drawn rows, and fifty is the cap.

---

## 3. Budget by budget

| # | Budget, from Wave 2 §13 / the ACs | Measured at 981 | Verdict |
|---|---|---|---|
| AC-15 | `get_nav_counts` ≤ **15** queries as company-wide HR at 1,000 employees | **23** | **FAILS** — and fails identically at 20 people |
| W1D-23 | the same budget, moved to **20** | **23** | **FAILS** |
| AC-15 | `get_nav_counts` ≤ 500 ms p95 | 165 ms (company HR), 247 ms (System Manager) | **passes** |
| §13 | `get_inbox` ≤ **25** queries whatever the team size | **26–28** for HR | **FAILS** |
| §13 | `get_inbox` ≤ 500 ms p95 | 276 ms worst | **passes** |
| §13 | `get_home` ≤ **20** queries for a manager with 19 reports | **31** | **FAILS by 50 %** |
| AC-39 | `get_home` ≤ 500 ms p95, manager with 19 reports | **88.2 ms** | **passes** |
| AC-38 | Home makes exactly three calls, counts computed once | three calls measured; `get_home` carries no `counts` key | **passes** (inherited from Wave 2's own test) |
| OPS-W2-7 | `get_nav_counts` ≤ 1 KB | 638 B | **passes** |
| OPS-W2-7 | `get_home` ≤ 30 KB | 1,470 B | **passes** |
| OPS-W2-7 | `get_inbox` ≤ 60 KB at the 50-row cap | 18,351 B | **passes** |
| nfr-budget | whitelisted API p95 ≤ 500 ms | worst 276 ms | **passes** |
| nfr-budget | queries per request bounded, no query in a loop | flat in headcount, proved both ways | **passes** |
| AC-31 | skeleton painted ≤ 300 ms | — | **NOT RUN** |
| AC-40 | Home usable ≤ 2.5 s p95 of 20 loads | — | **NOT RUN** |
| AC-27 | 390 px, 200 % zoom, 12 px floor, 44 px targets | — | **NOT RUN** — not this slice's job, still open from Wave 2 |
| OPS-W2-10 | calls per page against nginx's 120/min/IP | — | **NOT RUN** — see below |

**On OPS-W2-10.** Three calls per Home load is measured. Twenty people in one
store behind one address at the shift bell is 60 requests in a few seconds
against a burst of 30 — that is arithmetic from a measured number, so
**Inference**, not a test. It wants a real rate-limit test against nginx, which
is DevOps' rig, not mine.

---

## 4. Defects found

| # | What | Where | Severity | How to reproduce |
|---|---|---|---|---|
| D1 | **`get_home` takes 30–31 queries against a budget of 20**, every persona, at both sizes | `home_api.get_home` | **P2** | `bench --site test044 execute alvoraa_portal.tests.measure_044.run --kwargs "{'shape':'large'}"` |
| D2 | **Eight of those thirty are the same query run twice or more** in one call: the holiday-list assignment four times, `tabDocType` existence three times, `_reports()` twice, the employee's company twice | `home_api._team_today` calls `_reports()` twice; `_has_doctype` is not memoised; the holiday lookup happens once per reader | **P2** | `...measure_044.profile --kwargs "{'shape':'large','persona':'emp','call':'get_home','top':30}"` |
| D3 | **`get_nav_counts` takes 23 queries for HR** against a budget Wave 1 had already moved once, to 20 | `inbox_api.parts()` | **P2** | as D1 |
| D4 | **`get_inbox` takes 26–28 for HR** against a budget of 25 | `inbox_api.get_inbox` | **P2** | as D1 |
| D5 | **`_pending_approvals_scope` has no cap.** It returns every employee id in the caller's companies and every reader ships the whole list back as `IN (...)`. One query, so the count stays flat, but the clock grows with the company: ×5.1 from 20 to 981 for the System Manager's bell | `goals_api._pending_approvals_scope:1308`, read by `inbox_api._part_goal_updates` | **P2** | `...measure_044.profile --kwargs "{'shape':'large','persona':'sysmgr','call':'get_nav_counts'}"` |
| D6 | `_presence_counts` is capped at `LIST_CAP * 20` = 1,000 names. At 981 the cap has not bitten; at 1,001 an HR caller's presence numbers quietly stop counting everybody | `home_api._team_today` | **P3** | read; not reproduced — no fixture above the cap |
| D7 | The staff list is an **opt-in** feature and is off on a fresh site. Every persona including System Manager is refused until `staff_list` is added to the site's `features` | `subscription.FEATURES["staff_list"]["opt_in"]` | **P4** — correct behaviour, a trap for anyone measuring | first large run: every persona `PermissionError` |

**None of these is a P0 or a P1.** Nothing leaked across a company, no persona
saw anything they should not, no call was slow enough to hurt a user at 981
people. Every one of D1–D4 is a budget that was written without anyone counting
— which is exactly what Wave 2 said about its own section 13.

---

## 5. The regression guard

`alvoraa_portal/tests/test_scale_flatness_044.py` — **11 tests, 304 s, all
pass.**

It asserts the property, not a number: measure at four people, hire to thirty
through the ORM, measure again in the same state, fail if the query count grew.
Three guards stop it passing on nothing:

1. The team must really have grown — it asserts that first, and says by how
   much when it has not.
2. **A deliberate query-per-person is fed to the same machinery and must be
   caught.** `test_a_call_that_walks_the_team_one_by_one_is_caught` writes the
   16.4-second bell in three lines and asserts `_flat` raises with "grows with
   headcount". **Ran it; it passes, which is the proof the other ten tests are
   not decoration.**
3. Hiring nobody is caught rather than read as flatness.

It runs on a bare site with no scale fixture, because a query inside a loop
shows at thirty people as clearly as at a thousand, and a guard nobody can
afford to run is not a guard.

| Test | Covers |
|---|---|
| `test_get_nav_counts_is_flat_for_a_manager` | AC-15, manager scope |
| `test_get_nav_counts_is_flat_for_hr` | AC-15, the scope that IS the headcount |
| `test_get_home_is_flat_for_a_manager` | AC-39 · asserts the team card really drew |
| `test_get_home_is_flat_for_hr` | AC-39 · asserts the HR-scoped card really drew |
| `test_get_home_is_flat_for_a_plain_employee` | AC-55 peer card grows with the team |
| `test_get_inbox_is_flat_for_hr` | §13's "whatever the team size" |
| `test_get_frame_is_flat_for_hr` | Wave 1's frame |
| `test_get_staff_list_is_flat_for_hr` | W1D-21 · skipped where the tenant is not entitled |
| `test_the_goal_updates_part_does_not_query_per_person` | AC-16 — the bell, measured not read |
| `test_a_call_that_walks_the_team_one_by_one_is_caught` | the guard's own guard |
| `test_a_team_that_does_not_grow_fails_the_guard` | the other guard's guard |

---

## 6. What is deliberately not automated

| What | Why | Who, and how often |
|---|---|---|
| **AC-31 skeleton ≤ 300 ms and AC-40 Home usable ≤ 2.5 s** | Browser numbers. There is no headless-timing rig in this repo and building one is a slice of its own | DevOps or a UI slice, before the production release |
| **AC-27 — 390 px, 200 % zoom, 12 px text floor, 44 px targets** | Still open from Wave 2. Needs eyes and a device | A human, once per screen change |
| **OPS-W2-10 — nginx's 120 requests a minute per address** | Needs a real nginx and twenty clients | DevOps, before the production release |
| **Volume at a year's history** — 2,488 Attendance rows, not the ~250,000 a 1,000-person tenant has after a year | Honest gap. Index selectivity at that size is untested. Building it is hours of inserts | Worth one deliberate run before a large tenant goes live |
| **A tenant above 1,000 people** — `_presence_counts`' 1,000-name cap (D6) and the uncapped `IN` list (D5) | No fixture above the cap | Whoever signs off the first tenant over a thousand |

---

## 7. Who else is in these files

**Nobody.** This slice adds three new files and edits no application source at
all. Checked at the start of work: `git status` in the main checkout, the work
board, `git worktree list`, and `git log origin/dev`.

| File | Mine alone |
|---|---|
| `alvoraa_portal/alvoraa_portal/tests/fixtures_scale_044.py` | new |
| `alvoraa_portal/alvoraa_portal/tests/measure_044.py` | new |
| `alvoraa_portal/alvoraa_portal/tests/test_scale_flatness_044.py` | new |
| `docs/slices/044-scale-fixtures/04-test-report.md` | new |

Slice 042 owns `inbox_api.py`, `home_api.py` and the panel files and I have not
touched them. Slice 043 (Wave 3) is in its own worktree. The work board carries
my row.

**No shared resource was used.** Own container `hrlocal-044`, own redis
`hrlocal-044-redis`, own sites. `hrlocal-bench`, `test_site` and the main
checkout were never written to. One test run at a time, checked with
`docker ps` and `pgrep -af run-tests` before each.

---

## 8. Commands run

| Command | Result |
|---|---|
| `docker run` ×2, `bench new-site test044 / test044s / test044f --install-app …` | three sites, ≈ 12 min each |
| `bench --site test044 execute …fixtures_scale_044.build --kwargs "{'shape':'large'}"` | 981 people |
| `bench --site test044s execute …fixtures_scale_044.build --kwargs "{'shape':'small'}"` | 20 people, **59 s from empty** |
| `bench --site test044 execute …measure_044.run --kwargs "{'shape':'large'}"` | the large table above |
| `bench --site test044s execute …measure_044.run --kwargs "{'shape':'small'}"` | the small table above |
| `bench --site test044 execute …measure_044.profile …` ×4 | the statement breakdowns |
| `bench --site test044f run-tests --app alvoraa_portal --module …test_scale_flatness_044` | **11 ran, OK** (304 s) |
| `… --module …test_inbox_parts_042` | **24 ran, OK** |
| `… --module …test_home_api_042` | **23 ran, OK** |
| `… --module …test_inbox_counts_034` | **17 ran, OK**, plus its 2 doctype-cache tests OK |
| `… --module …test_frame_endpoint_registry_034` | **8 ran, OK** |
| `… --module …test_staff_list_034` | **22 ran, OK** |

Wave 1's and Wave 2's own suites were re-run on the same fresh site **after**
this slice's test file had created its people there, to prove the new file
leaks nothing into theirs. One run at a time.
| `python scripts/check_app_integrity.py` | 636 checks, OK — before every commit |

---

## 9. What I recommend

| # | Recommendation | Why |
|---|---|---|
| **R1** | **Fix the eight duplicate queries in `get_home` (D2)** before moving its budget. Memoise the holiday-list lookup and `_has_doctype` per request, and call `_reports()` once in `_team_today` | It is the cheapest 8 of the 10 queries between 30 and 20, and none of it changes behaviour |
| **R2** | **Then move the budgets in writing, with the measured numbers against them** — Wave 1's W1D-23 precedent. My proposal after R1: `get_home` ≤ 24, `get_nav_counts` ≤ 24, `get_inbox` ≤ 30. Re-measure before writing them down | A budget nobody measured is worse than no budget: it reads as proof |
| **R3** | **Replace the query-count budgets with the flatness tests as the gate**, and keep the numbers as a note | The number is a proxy; flatness is the property, and it is now asserted and proved able to fail |
| **R4** | **Put a cap on `_pending_approvals_scope` (D5)** or push the scope into the query as a join on company rather than a list of ids | It is the single biggest slope in the whole measurement, ×5.1, and it is the helper the 16.4-second bell came from |
| **R5** | **Run the browser numbers (AC-31, AC-40) before the production release**, on the rig Wave 1 used (W1D-09) | They are the two budgets that describe what a user feels, and they are the two nobody has measured |
| **R6** | **Keep the three sites.** Back them up rather than rebuild | 26 minutes each time, against a `bench restore` |

---

## Verdict

**Pass with known defects.**

The design holds where it was designed to hold: the landing calls are flat in
headcount, proved at 20 and at 981 people across five personas, with a
regression guard that is proved able to fail. Every response-time and payload
budget passes at 981 people.

Four query-count budgets do not pass — `get_home` by half — and they do not
pass at twenty people either, so they were wrong when they were written rather
than broken by scale. None of them costs a user anything today. R1 and R2 close
them honestly.

**This does not authorise a deploy.** Nothing here is pushed, nothing is
merged, no server and no tenant were touched.
