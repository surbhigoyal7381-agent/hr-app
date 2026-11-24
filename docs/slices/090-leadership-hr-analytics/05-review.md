---
slice: 090-leadership-hr-analytics
artifact: 05-review
author: hrms-technofunctional-reviewer
date: 2026-11-24
tier: 1
read_at: worktree /Users/mac/hr-app/.claude/worktrees/090-leadership-hr-analytics, branch slice/090-leadership-hr-analytics, HEAD 8c4763e0, diff 0a181d05..8c4763e0
---

# 090 · People trends: senior architect review (step 5)

**Verdict: BLOCK.** Two P1 faults, both small to fix. (1) The server sends day-by-day attendance and leave figures for a group that its own rule calls too small to chart. (2) On the real page, every refusal and every server error is handled wrongly: the user sees a "Not permitted" pop-up, then waits 15 seconds for the wrong message. That second fault comes from a browser test that fakes a callback the real page never calls. Fix both, re-run the slice's own tests, and this becomes SHIP WITH FIXES. **This verdict is advice. You decide.**

**What I could and could not run.** I did not run `bench run-tests`. The test engineer's full suite was running in `alv090-bench`, and I was told not to touch it. So **every Python test count below is the engineer's figure, and I have not checked it.** What I did run myself:

- the DOM test (17 checks, all ok);
- `check_app_integrity.py`, `check_tag_balance.py` and `check_portal_assets_gate.py` (all OK);
- the property test's own `violations()` logic, run against the real `people_trends.py` with stand-in `frappe` modules in my scratchpad. Result: 0 violations at minimums 3, 5 and 10, and 570 for the `Mutant`. That matches the engineer's claim;
- two small proofs of my own, described under B1, M3 and B2.

Read-only `grep`/`sed` in `alv090-bench` only, to read Frappe's `website.js`, `request.js` and `base.html`.

Labels: **proven** (I read it or ran it), **inferred**, **not checked**, `[ASSUMPTION]`.

---

## Blockers (P1, block the release)

### B1 · Day-by-day attendance and leave figures are sent when the rule hides the chart (PRIV-3, PRIV-4, AC-50, AC-81, AC-90): P1

- **Where:** `people_trends.py:737-741` checks `bin_rule` and withholds only `chart`. Lines `770-772` and `782-783` then build `attendance["series"]` and `leave["series"]` with no reference to `bin_rule`. In the page, `people-trends.js:163` and `:180` *draw* those two charts only when `d.chart.shared` is true. So the screen hides them, but the network answer still carries them.
- **Scenario (proven).** I ran the real `Rule`, `_people_units`, `_bins` and `_bin_units` with a stand-in `frappe`. The data:
  - Company "Co" has branches Y (50 people) and Z (40).
  - Branch X has 4 steady people, plus one who left 4 days before END, plus one who joined 3 days before END.

  On the **1 week** chip with filter `branch=X`:
  - `rule.verdict(...)` returns `None`, so the people figures are shown.
  - The day-by-day people counts are `[5, 5, 4, 5, 5, 5, 5]`, so `bin_rule.passes` is `False` and the chart is withheld.
  - But the answer still carries `attendance.series` (absent % per day) and `leave.series` (leave days per day). That includes the day when only **4** people were on the roll.
- **Why it is wrong.**
  - "Hidden means not sent" is the slice's central privacy mechanism.
  - The spec says a series is "sent whole or not at all" (AC-50 for the chart, AC-90 for leave).
  - A leader with DevTools reads a daily absence figure about fewer people than the minimum.
  - No test covers the withheld-chart path. `test_the_chart_is_whole_or_absent` only asserts the *shared* case. The property test checks `Rule.hidden` on its own, not the response (see AC-62 below).
- **Smallest fix.** In `_build`, when `not bin_rule.passes(match)`, leave `series` out of both `attendance` and `leave`, with `series_shared: false`. Make the page say "Not shared" in those two cards instead of drawing nothing (this also closes m3). Add one test with the fixture above: assert the keys are absent.

### B2 · The page calls the endpoint through the website version of `frappe.call`: it posts to "/" (OPS-18), and refusals and errors never reach the page (AC-71, AC-96, AC-97): P1

- **Where:** `people-trends.js:248-262` and `:267`.
- **What the real page loads (proven by reading):**
  - `hrms-employee.html:1` extends `templates/web.html`.
  - Frappe `templates/base.html:102` includes `frappe-web.bundle.js`, which imports `website/js/website.js`.
  - That `frappe.call` (`website.js:69-118`) posts to `url: opts.url || "/"` with `cmd` set to the method.
  - It runs `callback` **only on HTTP 200**. On a 403 it pops `frappe.msgprint("Not permitted")`.
  - It never calls an `error` option. The word does not appear in that function.
  - The portal's own `api()` (`portal.js:31-71`) is written for exactly this contract: it uses `always` and reads `xhr.status`.
- **Scenario (proven in jsdom, with a stand-in shaped like `website.js`; not run in a real browser).** Load the panel, then have the server refuse.
  - Result: posted to `"/"`, one "Not permitted" pop-up, still on the skeleton, no refusal banner, no PT-LOAD banner.
  - After the 15 s timer, the page shows "We could not load People trends … did not get an answer from the server in time … PT-LOAD". That is the wrong message for a refused filter. AC-71 wants "That view is not available to you … PT-SCOPE".
  - A forced error (HTTP 417, PT-LOAD) also waits the full 15 s.
  - If figures were already on screen, a refused filter leaves the old figures up, under a select that now shows the refused value, with "These figures are still for …".
- **Why it is wrong.**
  - **OPS-18 is an accepted P1 requirement:** "Page JS must use `fetch` to the `/api/method` path … never a `cmd` call on `/`". The reason is that a `cmd` on `/` misses path gates and the `/api/` rate-limit zone (ALV-248, ALV-422, and the "website pages post to /" lesson).
  - The impact analysis said the panel would use the portal's `gpFetch`. The built code does not, and no note records the change.
  - **The tests could never have shown it:**
    - The DOM test's fake (`people_trends_090_dom_test.js:35`, `:80-83`) calls `opts.error({status: 403})`, which the real `frappe.call` never does. That makes the PT-LOAD and PT-SCOPE checks green and worthless.
    - The HTTP tests post to `/api/method/...` (`test_people_trends_http_090.py:22`), a route the page does not use.
- **Smallest fix.** Replace the two `frappe.call` uses with `fetch("/api/method/<dotted>", {method: "POST", credentials: "same-origin", headers: {"X-Frappe-CSRF-Token": frappe.csrf_token, "Content-Type": "application/json"}, body: JSON.stringify(args)})`. Then:
  - map 403 to `fail(true)`, any other failure to `fail(false)`, and read `message` on 200;
  - have the DOM test fake `fetch` with real status codes;
  - add one line that asserts the URL starts with `/api/method/`.

  This one change closes OPS-18 and the three ACs. (`gpFetch` sits inside a closure at `portal.js:18004`, so it cannot be called from this file. A dozen lines of `fetch` is cheaper than exposing it.)

---

## Majors (P2: someone accepts in writing, or fix, before release)

### M1 · Speed: the budget is not proven, and two paths were never measured: P2

- **What we have:** the engineer's local figures (8x-slow stack: 1 year 6.9 s, 6 months 4.1 s, 5 concurrent 1-year calls about 12 s each). Dividing by 8 gives about 0.9 s for 1 year and about 1.5 s for 5 concurrent. That is **inferred**, and it sits right at the OPS-28 line of 1.5 s.
- **Why the 8x is shaky:** it comes from one comparison (29 ms for 26k rows, against 0.18-0.25 s for 18.6k rows), so the real factor could be anywhere from about 6x to 12x. At 6x, five concurrent calls miss the mark.
- **Not measured at all:**
  - The **multi-company** path. With "All companies", `_attendance_bins` uses `company in (…)`, which `org_figures.condition`'s own note measured at 10x slower (292 ms against 29 ms). `_by_company` then adds one more attendance query **per company** (`people_trends.py:854`). Grace's leaders would take this path.
  - Why **1 week (1.6 s) is slower than 1 month (1.1 s)**. **Inferred:** `_leave_units` reads 365 days of On Leave rows on every chip (`:789-790`), so every chip pays a fixed cost.
- **What I recommend:** acceptable for testing on dev. **Not acceptable for main until OPS-23 / AC-115 runs on the DTC-size dev copy, with a two-company login added.** No cache. If it misses, it comes back to you, as already agreed.

### M2 · Attendance hides only with the people figures, so attendance can be about fewer people than the minimum: P2 (your decision; ranked provisionally)

- **What changed:** the R1 decision (option 1, 24 Nov) moved attendance onto the people populations: people on the roll (`:759-761`). The spec's population for attendance (5.6) was "distinct people with a counted attendance row".
- **Where the two differ:** a cut where most people on the roll have **no** attendance rows. **Inferred, not checked on DTC data:** at DTC, owners and some third-party-paid staff do not punch, and agency staff with an unknown device id lose punches.
- **Scenario:** a department of 5 on the roll, of whom 2 punch → the page shows a weekly absent % that is about those 2 people → the minimum is not doing its job.
- **Mitigation:** the implementation notes call this "no stricter than the people family". In this case it is weaker.
- **Question (must know):** when you chose option 1, was this case in front of you?
  - If yes: write it as an accepted risk (owner, date), and this drops to P3.
  - If no, the cheapest guard costs no extra query: add `count(distinct a.employee)` to the existing `_attendance_bins` select and leave attendance out when the window's count is between 1 and the minimum minus 1. The trade-off is that this check is per chip, not "decided once over time". The security engineer should say whether that is acceptable.

### M3 · Leave types: the named list changes between chips (AC-86), and the headline can name the wrong "most" (AC-87): P2

- **Proven** by running `_leave_types` with a stand-in `frappe`. Data: Casual and Sick each taken by 5 people, Maternity by 1.
  - The 1-week chip names **Casual** and folds Sick into Other.
  - The 1-year chip names **Sick** and folds Casual into Other.
- **Why:** `people_trends.py:533` sorts by `window_days(…)` of the *current* chip, and `:537` moves the smallest of those into Other. The function's own docstring says "same on every period". AC-86 says "the named list is the same on all five chips".
- **Not proven:** that this actually lets someone work a figure out by subtraction. But it breaks "decide once over time" (PRIV-4).
- **Second fault:** `_headline` (`:598-599`) takes `types[0]`, the largest *named* type, even when "Other" is larger. With 1,000 unnamed days against 105 Sick days, the sentence reads "Sick the most". That is false, and AC-87 says to leave the clause out.
- **Smallest fix:** sort and fold by the 365-day total, so the choice is fixed across chips. In the headline, compare the top named type with the Other row. Add a test for each.

### M4 · Release gates still open (not code defects; listed so none disappears): P2

- Residual risks R1-R10 in 01c are **not accepted**, R10 included (early leavers "E of M" near the minimum).
- Counsel questions CQ1-CQ3 are open. CQ2 asks whether a health- or pregnancy-type leave may be named at 5 or more. Part D still names such a type if 5 people took it.
- Not run: AC-106 (360 px, 200% text, 44 px targets) and AC-107 (screen reader).
- Not run: the 012-then-090 test order in one process.
- **The branch is behind:** `origin/dev` is now `640cd1f5`, 23 commits ahead of the base 0a181d05. All are slice 086 by the same account. They touch `portal.js` (no overlapping hunks), `hooks.py` (a different hunk) and `scripts/run_dom_tests.js`. That last file **will conflict**: both sides moved `EXPECTED_BROWSER_TESTS` from 28 to 29, so it must become 30. The full suite now running in `alv090-bench` is on the tree before the rebase, so it does not include 086.

---

## Minors (P3: ship, tracked)

- **m1 · HR + Leadership sees a nav item that only refuses.**
  - `portal.js` `applyPlanNav` shows the item whenever `roles.leadership` is true. `_caller` (`people_trends.py:152-153`) refuses HR roles with PT-HR-OFF.
  - With B2 unfixed, that person gets a pop-up, then a wrong timeout message.
  - OPS-30 counts 0 holders of the role on every live site today, so nobody meets this yet.
  - Fix: `roles.leadership && !roles.is_hr`.
  - The deviation from AC-7 itself (refuse rather than `hr_scope()`) is **acceptable**. It follows BQ-2 (HR off in v1). Record AC-7 in the spec as deferred to US-19.
- **m2 · "N days left out; HR is checking" ignores the filter.**
  - `people_trends.py:773-774` passes only company and branch scope to `open_doubtful_counts`, never the chosen branch, department or type.
  - So a filtered view shows the whole company's count. Spec 5.4 says "in the cut".
  - The number is not sensitive, but it is wrong.
- **m3 · Charts vanish without a word.** When the people chart is withheld, the attendance and leave charts are not drawn and nothing says why (`people-trends.js:163`, `:180`). Spec 5.6 says the section shows "Not shared". This is part of the B1 fix.
- **m4 · Prototype parity, no recorded yes.**
  - The chart's sub line is cut to "Each week". The prototype says "Each week in {period}. The line adds up joined minus left from the start of the period."
  - The Leave card is stacked, where the prototype has two columns (tile and types beside the chart).
  - Small, but your rule (21 Oct) is "any difference needs her yes".
- **m5 · Query count grows with companies.** `_by_company` runs one query per company. AC-61 is tested only for 3 against 30 branches. Companies are few, so the cost is small, but the "fixed statement count" claim is only true per company.

## Nits (P4, backlog)

- `save_people_trends_period` has no `@requires_feature("analytics")`.
- `.pt-dq` uses `--amber-lt`. That is within the letter of AC-38 (no warning class), not its intent.
- The `Mutant` save and restore of `Rule.passes` does nothing, and `hasattr(pt, "_counted_list")` is always false. Both are in the property test.

---

## AC verification (grouped; the full list is in 03 §4)

| AC | Status | Evidence |
|---|---|---|
| 1-6, 8-10, 121 | met (engineer's tests, not re-run) | Read `leader_scope`, `_caller`, `make_role`: logic matches |
| 7 | not met as written; acceptable deferral | Refused in v1 (BQ-2). Nav fault m1 |
| 11-16, 19, 20 | met for `/api/method`; **the page uses `/`** | B2. HTTP tests never exercise the page's route |
| 17, 18, 21-24, 104, 110, 117 | met | Read the source. `ignore_permissions` 0 in module, SQL parameterised, `dim` from a fixed tuple |
| 25, 29-31 | partial | One request per tap, DOM-tested. Dwell and out-of-order not tested |
| 26-28, 32-37, 39 | met (engineer) | Read the window and `_window` maths. Identity holds by construction |
| 38 | met (inferred) | No status classes |
| 40-44, 53 | met (engineer) | `_early` and `c_rule` read |
| 45-49, 51, 54-60 | met (engineer) | Read `Rule`. The property logic re-run by me: 0 and 570 |
| **50** | **partial** | **B1**: people series correct, attendance and leave series still sent |
| 61 | met per branch | m5 |
| 62 | partial | Tests `Rule.hidden` unions, not "every allowed response … buckets". That is why B1 was missed |
| 63-70 | met (engineer) | Read the refusal checks |
| **71** | **not met in a real page** | **B2** |
| 72-75 | met | Bins read. Net line is a running total |
| 76-80, 82-84 | met (engineer) | Same formula, same exclusions |
| **81, 90** | **partial** | **B1** |
| 85, 88, 89, 122, 123 | met | Read |
| **86, 87** | **not met** | **M3**, proven |
| 91, 92 | met for the fixture | — |
| 93, 94, 102, 103 | met | m2 is a separate count |
| 95, 98-100 | met in jsdom | 300 ms skeleton not timed |
| **96, 97** | **not met in a real page** | **B2** (15 s wait, pop-up) |
| 101, 119, 120 | not built (US-19) | By decision |
| 105 | not checked in a browser | — |
| 106, 107 | not checked | M4 |
| 108, 109, 111-114, 116 (coded, not tested), 118 | met / partial as in 03 | — |
| 115 | owed | M1 |

## NFR verification

| Budget | Measured or reasoned | Result |
|---|---|---|
| Server ≤ 3 s, attendance part ≤ 1.5 s cold, 5 concurrent (OPS-28) | Local 8x-slow: 1.1-6.9 s. Production-class only inferred | **not proven** (M1) |
| ≤ 30 statements, fixed by branches and people | Engineer's test: ≤ 30, same at 3 and 30 branches | pass per company (m5) |
| Response ≤ 10 KB, flat with headcount | 2.2-2.8 KB (engineer) | pass |
| 3G: skeleton 300 ms, figures 2.5 s | not run | owed (AC-115) |

| Dimension | Impact analysis claimed | What the code does |
|---|---|---|
| Performance | neutral; R1 watch item | **degraded on long chips, unproven.** The multi-company path is unmeasured (M1) |
| Security | improves | **improves on the server.** The page breaks OPS-18 by posting to `/` (B2) |
| Reliability | neutral | **degraded in the page:** refusals and errors are mishandled (B2) |
| Scalability | neutral, one watch item | neutral per company. Grows with company count (m5) |
| Maintainability | neutral to slightly worse | agree: 865 + 311 lines, one copied constant, one private import. Small dead parts (below) |
| Data integrity | neutral | neutral. No cache, END fixed per call. m2 is a wrong count on filtered views |
| Compliance / privacy | improves, residual risk | **improves, with one leak (B1) and one widening by decision (M2)**. The named-type wobble (M3) weakens "decide once" |

## Compliance verification

| Obligation | Mechanism | Test | Status |
|---|---|---|---|
| Totals only (PRIV-1, 11) | Grouped Employee query. Key allowlist. No name or id reaches the response | AC-111/112 scans (engineer) | discharged |
| Hidden means not sent (PRIV-3, 4, OPS-11) | Rule parts A-C, `bin_rule` | property and group tests | **partial: B1** |
| Leave types only at the top, fixed (PRIV-8) | `_leave_types` | `test_leave_types_fold…` | **partial: M3** |
| Minimum read fresh, own record out (PRIV-2) | `min_group_size()` each call, `minus` unit | AC-45/46 tests | discharged |
| Server-side scope, deny by default (SEC-1, 2, 3, 6) | `leader_scope`, `_caller`, filter refusals | scope table, refusals | discharged |
| Endpoint hygiene: POST, CSRF, plan, no-store (SEC-4, OPS-18, 19) | Decorators, header | HTTP tests on `/api/method` | **partial: B2** (page uses `/` with `cmd`) |
| One log line, real sink (SEC-9, OPS-21, 22) | `Call.log` → `security_logger()` | read from the file (engineer) | discharged. Logging fails open on purpose |
| Purpose limitation (PRIV-12) | — | import check AC-24 | discharged as a test. Feature-map C4 not built (as spec 17.2 says) |
| Role with no permissions, no Desk (SEC-5) | `make_role` | AC-8, AC-121 | discharged |
| Lawful basis and notice (CQ1-CQ3) | — | — | **not discharged: counsel open** (M4) |
| Residual risks R1-R10 | — | — | **not accepted** (M4) |
| AI | none in the slice | — | not engaged |

## What to delete (subtract pass on the diff)

- `people_trends.py:67` `after_migrate = make_role`: nothing reads it. `hooks.py` names `make_role`.
- Response keys `scope.branches_only`, `scope.several_companies` and `chart.total`: the page never reads them (grep of `people-trends.js`: 0 hits each).
- `people-trends.js:160`: building `labels` from `leave.series` when the chart is not shared is never used, because the chart is drawn only when shared.
- `_bin_minus` rebuilds the caller's `Person` that `_build` already built as `own_p`. Pass it in.
- Kept: the `share_left=False` path. Live code never reaches it, but it is the PRIV-7 guard the spec asked for (AC-51). Removing it would be fine only with your yes.
- No over-built pieces found: no new DocType, field, cache, job, flag or app. The `Call` statement counter earns its place (OPS-22 asks for the count in the log line).

## What was done well

- **The private names never leave the server.** The people query groups by company, branch, department, type, status and the two dates, with a count. Names and ids never enter Python, and the response size depends on how many groups there are, not on headcount.
- **The property test fails when part C is removed** (I re-ran its logic: 570 violations against 0). The engineer also found a real edge case with it (all siblings hidden under a failing parent).
- **The CSRF test spotted that Frappe skips saving the token under test**, and saves it as a live request would. Without that, the test passed against a missing check. This is the right habit, and the same habit would have caught B2 if it had been applied to the browser fake.
- **Refusals throw and are logged as rule ids, never values.** Filters are refused, never trimmed. Scope is read fresh on every call.
- **Hot files touched with 1-to-4-line additions plus pin tests.** That is why the 23 incoming 086 commits conflict in only one counter line.

## Confidence

- **Proven by me:**
  - B1 and M3, with stand-in-`frappe` runs of the real module;
  - B2, by reading Frappe's `website.js`, `request.js` and `base.html` in `alv090-bench`, and with a jsdom run using a website-shaped fake;
  - the DOM test (17 ok) and three static gates (OK);
  - the property-test logic (0 and 570).
- **Not checked by me:** every Python test count (48, 5 and 2), the HTTP tests, and every timing figure, because the suite was running and I was told not to start it. Also not checked: a real browser at 360 px; the DTC-size dev copy; the multi-company timing; whether DTC's non-punching staff make M2 real.
- **Not reviewed:** uncommitted work in the worktree that is not part of 8c4763e0, almost certainly the test and DevOps sessions': `scripts/run_dom_tests.js` (modified), `alvoraa_portal/tests/people_trends_090_gaps_dom_test.js` (new) and `07-devops-inputs.md` (+202 lines). The new gaps test also fakes `frappe.call` (`:29`), so check it against B2's contract too.

**Must-know question holding the verdict:** M2. Was the "people on the roll who never punch" case part of the option 1 choice? It does not change BLOCK, but it decides whether M2 is P2 or P3.

**Subtract pass on this review:** I removed four candidate findings that I could not turn into a failure scenario:
- the `Call.log` swallowing logger errors (deliberate fail-open);
- `records_start` being one person's joining date (the spec draws it, AC-27);
- the "Management" heading instead of "Company" (parity P1 allows the portal's real nav);
- the chips having no arrow-key movement (AC-107 asks only for a radiogroup).
