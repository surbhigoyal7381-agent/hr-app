---
slice: 042-redesign-wave2
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-09-24
status: built and tested LOCALLY only. Not pushed, not merged into dev, no server, no tenant
branch: slice/042-redesign-wave2, rebased onto slice/034-redesign-wave1
bench: own container hrlocal-042, own redis hrlocal-042-redis, own site test042. hrlocal-bench not used
---

# Wave 2 — Home and Inbox: what was built

## Said first, three things

**1. 042 now sits on top of 034.** The branch was rebased onto
`slice/034-redesign-wave1` (`1f3ffdd`) because Wave 2's code imports
`inbox_api`, `frame_api`, `ess_part()` and the static frame files, none of which
are on `origin/dev`. **034 must reach `dev` before 042 can.**

**2. D-2 is not built.** Who may decide an attendance correction, and from when.
The fail-closed default ships: **no new decider.** `review_queue_filters` is
read exactly as Wave 1 left it. There is no two-working-day rule, no
"with <manager> until <date>" label and no new scope, and there is no
"visible but not actionable" state, because the code has none and inventing one
quietly would be the worst of the three options. It is written into
`inbox_api`'s docstring so the next person finds it there rather than here.

**3. Deleting the week-presence endpoint removes a working card from the current
portal.** Anybody who used the "this week" grid on today's Home will notice it
has gone. That is the cost of the security review's SEC-9 and it needs Surbhi's
eye before this goes anywhere.

---

## 1. File by file, and the mechanism chosen

| File | New / changed | Mechanism | Why |
|---|---|---|---|
| `alvoraa_portal/inbox_api.py` | **extended** | extend | Wave 1 wrote it and its docstring said it was written to be extended. Added `Part`, `parts()`, `row_keys()`, `no_rows()`, `PartDefinitionError`, `get_inbox`. `get_nav_counts` keeps its exact payload shape, which is why Wave 1's 17 tests pass unedited |
| `alvoraa_portal/home_api.py` | **new** | build | Nothing existed that answered "everything Home draws" with a fixed key list. Reuses `_ledger_leave_balances` (035), `_own_upcoming_holidays` (035), `checkin_needs_location`, `get_available_features` and `permitted_employees` rather than re-deriving any of them |
| `alvoraa_portal/hr_api.py` | **changed** | delete | The week-presence endpoint and its private holiday helper are gone (SEC-9 / AC-59) |
| `public/js/ess/next-frame.js` | changed | extend | One small seam: `NextFrame.panel(route, draw)` and a context object. Plus Home-with-no-employee is answered before any panel is asked, so Asha costs no call |
| `public/js/ess/next-home.js` | **new** | build | One file per panel (OPS-31 made it free) |
| `public/js/ess/next-inbox.js` | **new** | build | Same |
| `public/css/ess/next-panels.css` | **new** | build | Static file, cached a month, stamped by the build version. Uses the design system's tokens only |
| `templates/includes/ess/parts/next-home.html`, `next-inbox.html` | **new** | configure | Server-rendered skeletons as `ess_part`s — no Jinja, no template cache slot (AC-44) |
| `templates/includes/ess/next/frame.html` | changed | extend | Pastes the two skeletons into `#nf-main` |
| `www/hrms-employee-next.html` | changed | extend | Loads the panels' stylesheet and the two scripts, each with `?v=` |
| `public/js/ess/portal.js`, `templates/includes/ess/parts/home.html` | changed | delete | The old week grid and the call behind it |
| `tests/portal_source.py`, `scripts/lib/portal_source.js` | changed | fix | Neither expanded markup parts for the **preview** page, so every check on it was reading an unexpanded tag as text. Both are now two-page aware, as the asset checks already were |
| `tests/test_ess_parts_034.py`, `tests/test_portal_split_034.py` | changed | extend | Their pinned sets now allow a part or an asset that belongs to the preview page. Belonging to **neither** page is still a failure |
| `tests/test_frame_endpoint_registry_034.py` | changed | extend | `home_api.py` joins the scanned modules; `get_home` and `get_inbox` have their registry rows |
| `alvoraa_portal/tests/next_frame_test.js` | changed | move | The Inbox **screen**'s assertions moved to `next_panels_test.js`, because the screen moved. `load()` waits a third turn |
| `tests/fixtures_042.py` | **new** | build | This slice's own company, stores and people |
| `tests/test_inbox_parts_042.py`, `test_home_api_042.py`, `test_week_presence_retired_042.py`, `test_panel_source_042.py`, `alvoraa_portal/tests/next_panels_test.js` | **new** | build | The checks |

**No new DocType, no custom field, no patch, no migration.**

---

## 2. The acceptance criteria, and how each is satisfied

| AC | How | State |
|---|---|---|
| AC-1 | `get_home.needs` holds the caller's own items, most urgent first | **met** |
| AC-2 | **D-1 taken as recommended: no number on Home's heading.** The bell is the one number. Asserted in `next_panels_test.js` | **met, decision recorded** |
| AC-3 | "Needs you — All clear" is a designed state; the hero still draws with a shift | **met** |
| AC-4 | Four cases tested: assignment, `default_shift`, neither (no hero at all), already checked in | **met** — the "assignment beats default" case is covered by code and by the default-shift test, not by a Shift Assignment fixture (see §6) |
| AC-5 | `HOME_KEYS` enforced on the way out; `me` is exactly `ME_FIELDS`; the six forbidden fields asserted absent per persona | **met** |
| AC-6 | Leave from `_ledger_leave_balances`; a fully used type is shown | **met** (code + DOM), no ledger fixture of its own |
| AC-7 | Own holiday list only, through slice 035's helper | **met** by reuse |
| AC-8 | `count()` == `len(rows(limit=None))` for every part enumerated from `parts()`, every persona; scope declared as data; no helper returns `{}`, asserted on the **return value** | **met** |
| AC-9 | Own leave approver counted once, under my requests | **met**, and proved able to fail |
| AC-10 | Store HR sees their store's goal/correction rows; company-wide HR sees both | **met** for corrections; goal-update scope covered by reuse of `_pending_approvals_scope`, not by a KPI fixture (§6) |
| AC-11 | 51 waiting + declined + withdrawn **inside the first 50 by creation** → count 51, list 50, "Showing the first 50 of 51" | **met** |
| AC-12 | Empty part not drawn; all empty → "All clear."; counts payload keys pinned; no name, no reason | **met** |
| AC-13 | Counts re-read from the server after a decision; the browser holds no number | **met** in code and in the panel's structure; not yet driven end to end in jsdom (§6) |
| AC-14 | The bell, the menu, the bottom bar and the Team badge all read `get_nav_counts` — Wave 1's mechanism, unchanged | **met by inheritance** |
| AC-15 | `get_inbox` ≤ 25 queries, asserted on the S042 fixture; **and** a test that the query count does not GROW when the rows go from one to five. `get_nav_counts` ≤ 15 at 1,000 employees is **not proved** — no such fixture (§6) | **partly met, and it found a real N+1** — see §4 |
| AC-16 | No portal boot path calls the old heavy approvals call; the AST check keeps `get_nav_counts`/`get_inbox` from querying directly | **partly met** — the direct-query check is in; a repo-wide "no boot path calls it" check is not |
| AC-17 (a) | Every drawn correction driven through its own action | **met** |
| AC-17 (b) | An **undrawn** document called by hand is refused, and nothing is written | **met** — the half that matters |
| AC-18 | "This one has already been decided." is reused from `decide`; the panel removes the row and refreshes | **met in code**, not driven in jsdom |
| AC-19 / AC-20 | My requests: own Active Employee only, plain-word state, withdraw only where allowed | **met** |
| AC-21 / AC-22 | The Fix button carries the days the gap rule found; the number and the list come from `_gap_days` | **met** for the number/list identity, including the capped case |
| AC-23 / AC-24 | Priya's queue is her store's; head office's correction is in neither her count nor her list | **met** |
| AC-25 | Own item not in own count or list; the decide action refuses through `refuse_own_decision` | **met** for corrections; the other four paths reuse the same helper and are not each fixtured (§6) |
| AC-26 | Every string added is inside `__()` or `_()`, as a whole phrase with a placeholder | **met by construction**, no static check added |
| AC-27 | 390 px, 12 px floor, 44 px targets, no sideways scroll, colour never the only signal | **built, not measured** (§6) |
| AC-28 | The context line is a **number**, built server side in `_leave_context`; no colleague name, no leave type | **met in code**; the two-overlapping-leaves fixture is not built (§6) |
| AC-29 (a) | Counts only — keys pinned to `TEAM_TODAY_KEYS`, no name, no photo, no per-person state, asserted on the payload | **met** |
| AC-29 (b) | A group below five carries no numbers | **met** |
| AC-29 (c) | Complementary suppression: where one category is hidden the next smallest goes with it | **met — and it contradicts AC-29 (b)'s own example.** See §5 |
| AC-30 | "Nobody is on leave today" appears nowhere in the built page | **met**, static check |
| AC-31 | Both skeletons are in the server-rendered HTML | **met**; the 300 ms measurement is not done (§6) |
| AC-32 | One card failing is one card failing, plus a test that **no** card is quietly in the error state on a healthy fixture | **met** |
| AC-33 | A manager with no reports gets no team card at all | **met** |
| AC-34 | Rows failing → "The waiting list could not load. Try again." with Try again | **met** |
| AC-35 | Session ended → `/login` | **met by inheritance** from Wave 1's frame |
| AC-36 | `get_home` failing → the page-error sentence with a code carrying no personal data | **met** |
| AC-37 | Asha: `me: None`, every card empty, no error — **and zero scoped queries**, with a proof the recorder can see queries | **met** |
| AC-38 | Home makes exactly three calls; the six parts are computed once; `get_home` carries no `counts` | **met** |
| AC-39 / AC-40 | 500 ms p95, 2.5 s usable | **not measured** (§6) |
| AC-41 | `get_home` and `get_inbox` are in the registry with Guest, wrong-persona and scope cases | **met** |
| AC-42 | No `ignore_permissions`, no `global`, no module-level mutable in either module — Wave 1's checks now cover `home_api.py` too | **met**, and it caught a module-level dict on the first run |
| AC-43 | POST bodies through `frappe.call`; the card-failure log carries the card's name and the traceback, never an employee id | **met** |
| AC-44 | No new Jinja template; markup as parts holding no tag; style and script as static files with `?v=` | **met**, pinned set still three |
| AC-45 | The gap window starts at `date_of_joining` | **met** |
| AC-46 / AC-47 | `status = "Active"` on every people query; one "who am I" helper | **met** |
| AC-48 / AC-49 | A day covered by approved **or pending** leave is not a gap | **met** for corrections-covered days; the half-day case is covered by the rule, not by its own fixture (§6) |
| AC-50 | An auto-marked Absent day **is** a gap | **met** |
| AC-51 | The gap list is capped with the true total shown | **met** |
| AC-52 | A holiday and a weekly off on the caller's **own** list are never gaps; today and the future never are | **met** for today/future; the holiday case is in the code and reuses 035's list lookup |
| AC-53 | "Today" is the site's date | **met** |
| AC-54 | Multi-company HR through `permitted_employees` | **met by reuse** |
| AC-55 | No manager → no peer card, no department fallback | **met** |
| AC-56 | A cancelled document is in no count and no list (`docstatus` filters) | **met by construction** |
| AC-57 | Two tabs: the other tab's count is stale until its next load | **accepted, stated** |
| AC-58 | Two approvers within a second: one wins | **met by inheritance** — `decide` already refuses a second decision |
| AC-59 | The endpoint is deleted with the card; the name is in no source file of this app; calling it finds nothing | **met**, and the check asserts it really scanned |
| AC-60 | Nothing from the server reaches `innerHTML` unescaped; a hostile Designation is text in a queue row, a context line and the team card | **met**, and proved able to fail |
| AC-61 | **Not built.** D-8 unanswered → own anniversary only, `joiners` empty, asserted | **fail-closed default shipped** |
| AC-62 | The entitlement test changes the site's own `features` list and patches nothing; a static check fires on a real patch and **not** on prose about patching | **met** |

---

## 3. The seven non-functional dimensions, against the code actually written

| Dimension | Before | After | Verdict |
|---|---|---|---|
| **Performance** | The portal's bell called `get_pending_approvals`, which walked one employee at a time — 16.4 s for HR | The portal never calls it. `get_home` carries no counts, so the six parts are computed once per page load. Every list is a set-based query with an `in` list and a cap; nothing queries inside a loop. `_leave_context` is one count per drawn leave row — the one place a per-row query survives, bounded by the 50-row cap | **improves** |
| **Security** | A whitelisted endpoint returned named per-day absence for up to 40 department colleagues | Deleted, with a check that keeps it deleted. Both new endpoints ship Guest, wrong-persona and scope tests. No scope helper returns `{}`. An **undrawn** row is proved refusable by hand. A hostile Designation is text | **improves** |
| **Reliability** | One failing card could fail the page | Each card fails alone, and a test asserts none fails quietly on a healthy fixture — which caught two wrong field names on the first run. No new background job, no new external call | **improves** |
| **Scalability** | — | Bounded queries and caps throughout; no per-employee loop. But the 1,000-employee and 20-person fixtures do not exist, so every number in the spec's §13 is still a target nobody has measured | **neutral, unproven** |
| **Maintainability** | Six hand-written filter pairs | One `parts()` helper, one filter per part, a scope declaration checked at construction, and a fixed row key list per part. A seventh part with no scope or no key list cannot be built | **improves** |
| **Data integrity** | The count and the list could drift | One filter, two uses, with a test that enumerates the parts from `parts()` itself. Nothing cached to disk. The browser never decrements a number | **improves** |
| **Compliance / privacy** | Named per-day absence for a department; a start-up payload with six personal fields | Fixed key list on `get_home`, counts with no names or ids, presence counts under a minimum group size with complementary suppression, and the one new disclosure — the joiners card — **not built at all** | **improves** |

---

## 4. NFR notes

**The N+1 I shipped and then caught.** The leave approval row's context line -
"2 other people in this team are away on those days" - was asked for one row at
a time. At the fifty-row list cap that is fifty extra queries and it breaks
AC-15's budget of twenty-five for the whole call. I had written it into the notes
as an "acceptable simplification" before checking the arithmetic against the
budget, which is exactly the shortcut the NFR rules exist to stop.

**What fixed it, and what keeps it fixed.** `_leave_contexts` reads every
overlapping leave in the departments on the page in **one** query and counts in
Python; the number is identical because the filter is the same.
`TestTheQueryCountIsBounded` now asserts two things: that `get_inbox` stays
inside twenty-five queries, and - the one that generalises - that **the query
count does not grow when the rows go from one to five.** That second assertion
catches a query-in-a-loop without needing the 1,000-employee fixture at all, and
it carries a guard that at least four rows were drawn, so it cannot pass on an
empty list.

**A second thing found the same way.** `_shift_today` read the newest Shift
Assignment by start date and then checked whether it had ended, so an assignment
that finished last week hid one that is still running. It is one query with the
open-ended case in it now.

**Query counts.** Not measured against a 1,000-employee fixture, which does not
exist. What is asserted:

- `parts()` for a caller with **no** Employee record runs **zero** scoped
  queries, proved by wrapping `frappe.db.sql` and asserting the recorder can see
  queries for a real employee.
- `get_home` for a caller with no Employee record likewise.
- `get_nav_counts` and `get_inbox` are proved by AST not to query the database
  directly — every number comes out of `parts()`.
- `get_inbox` stays inside **25** queries on the S042 fixture, and its query
  count does not grow with the number of rows.

**Indexes.** None added. Every filter is on a column Frappe already indexes
(`employee`, `docstatus`, `status`, `attendance_date`, `from_date`) or on a Link.

**Background jobs.** None. Nothing in Wave 2 takes more than two seconds. If the
gap query ever does it moves to the `short` queue and that card shows its own
loading state.

**Permission enforcement points.** `inbox_api.parts()` (six scope declarations),
`attendance_correction._may_review` + `review_queue_filters` (unchanged),
`goals_api._pending_approvals_scope`, `hrms.alvoraa_hr_core.access.permitted_employees`
and `permitted_companies`, `refuse_own_decision` inside the existing decide
actions, `frappe.get_list` (the caller's own permissions) on every list,
`subscription.has_feature` through `get_available_features` for the payslip row.

**Sensitive fields touched.** Attendance status (a pattern of absence can imply
health) — read and collapsed to three buckets before it leaves `_presence_counts`,
so a leave type cannot reach a caller even by accident. `date_of_birth`,
`gender`, `cell_number`, `date_of_joining`, `reports_to` and `branch` — the last
three are **read** where the gap rule and the anniversary need them and asserted
absent from the payload; the first three are never read.

**Fallbacks.** Counts failing leaves the bell blank and Home working. `get_home`
failing shows the page-error sentence with a Try again. One card failing shows
that card's own sentence. A missing plan key hides the payslip row.

---

## 5. The one place I could not satisfy the spec as written

**AC-29 (b) and AC-29 (c) contradict each other, and I took the fail-closed half.**

- (b) says a group below five carries no numbers, and gives an example: *"a
  six-person team with one away and five in carries both"*.
- (c) says where one category is suppressed the next smallest is suppressed with
  it, and gives an example: *"a six-person fixture built so that suppressing one
  category would leave the other recoverable must suppress both"*.

Those are the same fixture with opposite answers. A per-category threshold makes
(c) mean something and makes (b)'s example false; no per-category threshold makes
(b)'s example true and (c) vacuous.

**What is built:** the group rule (below five, no numbers) **and** a per-category
rule — a non-zero count below five describes fewer than five people, so it is
suppressed, and the next smallest goes with it. The consequence is honest and
worth saying: **on a small team the presence card will often show no numbers at
all.** The spec itself says this card "earns its place only because it stops
people asking each other" and that it should be dropped rather than grown if it
does not survive the usability test. On the current rule it may not.

`_suppress` carries this paragraph in its docstring. **D-7 is the decision that
settles it**, and it now has a concrete question attached rather than a number
nobody sourced.

---

## 6. Known gaps and shortcuts, each labelled

| # | What | Label | What removes it |
|---|---|---|---|
| 1 | **D-2 not built** — no new decider for attendance corrections | **intentional trade-off** (fail-closed) | Surbhi answers D-2. It is a permission change and needs her word |
| 2 | **The joiners card not built** — own anniversary only | **intentional trade-off** (fail-closed) | Surbhi answers D-8 |
| 3 | **Every number in §13 is unmeasured.** No 1,000-employee fixture, no 20-person store fixture. AC-15, AC-39, AC-40, AC-31's 300 ms, AC-27's 390 px pass and the payload byte budgets are all **not proved** | **dangerous debt — escalating now** | Build the two fixtures (OPS-W2-8) and record the numbers before any production release. The old bell's 16.4 s is exactly what an unmeasured budget looks like, and `_pending_approvals_scope` — the helper that caused it — is reused here |
| 4 | **Deleting the week-presence endpoint removes a working card from today's portal** | **intentional trade-off, needs Surbhi's eye** | Her decision on D-3. The security review asked for the deletion; the visible loss is real |
| 5 | AC-29's contradiction, §5 | **escalated, fail-closed** | D-7 |
| 6 | AC-13 and AC-18 are structural in the panel and in the server's existing actions, but not driven end to end in jsdom | **temporary debt** | A jsdom test that clicks Approve, makes the second call fail, and asserts the row goes and `get_nav_counts` is called again |
| 7 | AC-25 is fixtured for corrections only; the other four paths reuse `refuse_own_decision` | **acceptable simplification** | One fixture per path; the test engineer's dedicated coverage |
| 8 | AC-28's two-overlapping-leaves fixture, AC-10's KPI fixture, AC-48's half-day fixture, AC-4's Shift Assignment fixture | **temporary debt** | Fixtures. The rules are in the code and reviewed; the checks are thinner than the ACs ask |
| 9 | AC-16's repo-wide "no boot path calls the old approvals call" check | **temporary debt** | A static check over the portal's boot paths |
| 10 | ~~`_leave_context` runs one count per drawn leave row~~ | **fixed** | It was fifty queries at the list cap and broke AC-15's budget of twenty-five. `_leave_contexts` now reads the whole page in one query. §4 |
| 11 | The Fix button routes to `#time/fix?from=…&to=…`; the Time screen that reads those parameters is **Wave 3** | **intentional trade-off** | Wave 3 (043) builds the sheet that consumes them. Today the route opens Wave 1's placeholder |
| 12 | The Inbox's decide buttons cover leave and corrections; goal/KPI and shift requests are listed with no buttons | **acceptable simplification** | The spec's own §3 says a shift-request decide action must be **built**; it is not in this wave's commits |
| 13 | `npm install` was run in the worktree to get `jsdom`, which the DOM tests need | note, not debt | Nothing. `package.json` is unchanged |
| 14 | `bench run-tests` was run per module, not as a whole-app suite | **acceptable simplification** | The whole `alvoraa_portal` suite takes hours on one site; one run at a time is Wave 1's lesson |

**What I would fix first with more time:** number 3. Everything else is a
decision or a fixture; that one is a budget nobody has tested, on the page every
employee lands on, using the helper that produced the 16.4-second bell.

---

## 7. What else moved while I worked

| Question | Answer |
|---|---|
| Commits that came in from others | **None.** `git fetch origin dev` found nothing past `8718f27`, before and after the work |
| The rebase | `slice/042-redesign-wave2`'s four docs-only commits replayed onto `slice/034-redesign-wave1` (`1f3ffdd`) with **no conflict** |
| Conflicts | **None** |
| How I proved nothing of Wave 1's was lost | **Wave 1's `test_inbox_counts_034.py` was not edited and all 17 of its tests pass** against the reshaped `inbox_api`. That is the regression proof for the one collision this slice was warned about. Its `test_frame_endpoint_registry_034` caught a module-level dict I had added, and `test_portal_split_034` caught three unpinned asset files — both were Wave 1's guards doing their job, and both are fixed rather than loosened |
| Wave 1 files I did change, and why | `next-frame.js` (a panel seam), `next_frame_test.js` (a third turn, and the Inbox **screen**'s assertions moved to the file that owns the screen now), `portal_source.py` / `portal_source.js` (they never expanded parts for the preview page), `test_ess_parts_034.py` and `test_portal_split_034.py` (their pinned sets now allow a preview-page part or asset; belonging to **neither** page still fails) |
| Board | Claimed by path in `.claude/work-in-progress.md` before the first edit |
| Bench | Own container `hrlocal-042`, own redis, own site `test042`, own sites volume. `hrlocal-bench` untouched. One `bench run-tests` at a time. No `docker cp` — every file reached the container through the bind mount, and the two config writes through `docker exec -i … bash -c 'cat > …'` |

---

## 8. Commands run, and what they said

| Command | Result |
|---|---|
| `git rebase slice/034-redesign-wave1` | clean, 4 commits replayed |
| `docker run` ×2 + `bench new-site test042 --install-app …` | site up with frappe, erpnext, hrms, alvoraa_goals, alvoraa_portal |
| `python scripts/check_app_integrity.py` | 636 checks, OK — run before every commit |
| `bench run-tests --module …test_inbox_counts_034` | **17 ran, OK** — Wave 1's file, unedited |
| `bench run-tests --module …test_inbox_parts_042` | **22 ran, OK** (after 3 real failures: a Left employee needs a relieving date; Frappe HR refuses two overlapping Attendance Requests; the cap assertion was wrong) |
| `bench run-tests --module …test_home_api_042` | **22 ran, OK** (after 4 real failures: Appraisal has no `status`, Individual Goal has no `progress`, and the gap list was ordered oldest-first so the cap hid the days a person came to fix) |
| `bench run-tests --module …test_week_presence_retired_042` | **2 ran, OK** (after 1 failure: the test's own docstring named the endpoint) |
| `bench run-tests --module …test_panel_source_042` | **7 ran, OK** (after 1 failure: the gate check fired on prose; tightened to match a real patch) |
| `bench run-tests --module …test_frame_endpoint_registry_034` | **7 ran, OK** (after 1 failure: it caught my module-level dict — Wave 1's SEC-15 guard working) |
| `bench run-tests --module …test_portal_split_034` | **12 ran, OK** (after 1 failure: three new asset files were not in its pinned set) |
| `bench run-tests --module …test_ess_parts_034` | **8 ran, OK** |
| `bench run-tests --module …test_preview_page_034` | **14 ran, OK** (2 skipped) |
| `bench run-tests --module …test_frame_api_034` | **33 ran, OK** |
| `bench run-tests --module …test_staff_list_034` | **9 ran, OK** |
| `bench run-tests --module …test_next_frame_034` | **22 ran, OK** |
| `node scripts/run_dom_tests.js` | **110 passed, 0 failed** — 4 files run, 3 still not run for Wave 1's recorded reasons |
| `node scripts/check_undefined_js.js` | undefined identifiers: none |
| `node scripts/check_portal_handlers.js` | all reachable and callable |

**Three guards were deliberately broken to prove the checks can fail**, which is
the Wave 1 lesson about assertions written so they never could:

| Guard removed | What went red |
|---|---|
| `employee != my own` on the leave part | `test_my_own_leave_is_mine_and_not_an_approval`: `1 != 0` |
| `esc()` on the Inbox queue row's name | `a hostile name in a queue row creates no element (got 1, wanted 0)` — and the "shown as text" assertion too |
| — | Each was restored and the suite re-run green |

Two more checks carry their own "can this fail" proof in the test itself: the
zero-scoped-query test asserts the recorder **does** see queries for a real
employee, and the entitlement check asserts the real gate **does** say payroll is
not bought before it looks for the row.

---

## 9. What Surbhi decides next

| # | Decision | Effect |
|---|---|---|
| **D-2** | Who may decide an attendance correction, and from when | Unblocks the corrections routing. **It is a permission change.** Nothing is built until she answers |
| **D-3** | Deleting the week-presence endpoint takes a working card off today's portal | It is done in this branch. If that is not acceptable, the commit comes out and SEC-9 stays open |
| **D-7** | The minimum group size, and §5's contradiction | The presence card may show no numbers on small teams as built |
| **D-8** | May a person decline being listed as a new joiner | Unblocks the joiners card. Not built |
| **R2** | Wave 1 recorded that a repo-wide `ignore_permissions` CI gate must exist **before** Wave 2 added endpoints. Wave 2 is here and the gate is not | Either the 2026-10-31 date holds and this waits, or the date moves with her name against it |
| **OPS-W2-8** | The two fixtures and the numbers | Gap 3 above. My strongest recommendation: before any production release |
| Push | Nothing is pushed. **034 must reach `dev` first** | Local only, as asked |
