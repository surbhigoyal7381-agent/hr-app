---
slice: 035-wrong-numbers
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-09-22
status: built locally, not merged into dev, not pushed
inputs: [00-impact-analysis.md, decisions Q-e (14 Sep), Q16/Q-G1/Q-G2 (22 Sep)]
---

# Slice 035, commits 1–3: what was built

Approved on 22 Sep 2026: commits 1, 2 and 3 for the second production release.
Commit 4 (one holiday source for the rest of the portal) waits for a decision on the
no-fallback design. Commits 5, 6 and 7 are on hold.

Branch `slice/035-wrong-numbers`, cut from `origin/dev` `1c4e84c`. **Not merged into
local `dev`. Not pushed.** The shared bench and `test_site` were not used at all.

---

## 1. The code, file by file

### Commit 1 — leave left comes from Frappe HR's ledger

| File | What changed | Mechanism | Why |
|---|---|---|---|
| `hr_api.py` | New `_ledger_leave_balances(employee, date)`; `get_employee_dashboard`, `get_leave_summary`, `get_employee_scorecard` and `get_employee_detail_for_manager` now call it instead of summing allocations minus approved applications | **Reuse** Frappe HR | The ledger is what the leave check, the late rule, encashment and the apply-form preview already read. Four private copies of the sum were the defect |
| `www/hrms-employee.html` | `loadHomeLeave` reads `b.total`, the key the server has always sent (2 lines) | **Fix in place** | Without it, "of 8" never showed and a fully used type was hidden — so the ledger fix alone would have made Rahul's Casual Leave vanish from Home instead of reading "0 of 8" |

The helper calls Frappe HR's lower functions (`get_leave_allocation_records`,
`get_leaves_for_period`, `get_leaves_pending_approval_for_period`,
`get_manually_expired_leaves`, `get_allocation_expiry_for_cf_leaves`,
`get_remaining_leaves`) in the order `get_leave_balance_on(...,
consider_all_leaves_in_the_allocation_period=True)` uses them, rather than calling
`get_leave_balance_on` itself. That function begins with `validate_leave_access`, which
refuses a manager who is the reporting manager but not the named leave approver, and a
store HR person whose desk read is branch-scoped — both of whom the portal already lets
see this figure, and both of whom would have hit a permission error on a screen that
works today. **Every caller checks who may see the employee before calling** (the
caller's own record, `get_effective_manager`, or `_hr_target_employee`), and the
docstring says so in capitals. A test compares the helper with `get_leave_balance_on`
and with `get_leave_details`, so if Frappe HR changes that shape, CI says so.

### Commit 2 — Home's holidays are the employee's own

| File | What changed | Mechanism | Why |
|---|---|---|---|
| `hr_api.py` | New `_own_upcoming_holidays(employee, date)`; `get_employee_dashboard` returns `holidays` from the employee's own list and a new `holiday_note` | **Reuse** ERPNext's lookup | The old query read the `Holiday` table with no `parent` filter — every list on the site, every company — and stopped at 31 December |
| `www/hrms-employee.html` | `renderHolidays(holidays, note)` shows the note; the Home loader passes `data.holiday_note` (3 short edits) | **Fix in place** | An empty card reads as "no holidays". The note says what is actually wrong |

The list is found with
`erpnext.setup.doctype.employee.employee.get_holiday_list_for_employee`, which is what
the salary slip calls. With Frappe HR installed it hands off through the
`employee_holiday_list` hook and answers from **Holiday List Assignment only** — never
`Employee.holiday_list`, never the company default. **No fallback**, as approved: a
fallback would have shown `aahr`'s employees a calendar payroll ignores and hidden the
setup gap. Where the lookup finds nothing the card says *"No holiday list is assigned
to you yet. Ask HR to set one up."*, translated server-side with `_()`.

Window: from the start of this month to the end of that list's period (decision Q16),
so January to March of an April–March list are no longer hidden. Named holidays only;
weekly offs are not holidays.

### Commit 3 — goal percentages are about one cycle

| File | What changed | Mechanism | Why |
|---|---|---|---|
| `goals_api.py` | New `current_cycle_name(company)` and `goal_average(goals)`; `_dashboard_stats` and `get_team_goals` use both | **Build** (two small helpers) | Three screens each averaged every goal a person ever had |
| `hr_api.py` | `get_team_scorecard` filters each member's goals to their company's current cycle and uses `goal_average`; `get_employee_scorecard` lists the current cycle's goals first | **Reuse** the new helpers | The comparison chart is what a manager rates beside |
| `performance_api.py` | `get_team_reviews` reads appraisals oldest-first, so "last one wins" keeps the **newest** | **Fix in place** (one `order_by`) | With no cycle chosen — which happens between cycles, and Q2 ends 30 Sep — managers saw last quarter's review |

`current_cycle_name`: In Progress, else the newest not Completed, else (all Completed)
the newest — per company, since every Appraisal Cycle belongs to one (decision Q-G1).
`goal_average`: weighted by `weightage` when any goal carries one, a plain average when
none do (decision Q-G2), which is how the appraisal's own goal score treats weights.
Cancelled goals are dropped from averages.

`get_team_goals` also stopped running one goal query per direct report: it is now one
query for the whole team plus one cycle lookup per company. That was not asked for, but
the loop was the line being changed.

---

## 2. Tests

Three new files, one per commit, each named after the defect it keeps closed.

| Module | Tests | Result |
|---|---|---|
| `test_leave_ledger_035.py` | 9 | **OK** |
| `test_home_holidays_035.py` | 8 | **OK** |
| `test_goal_cycle_035.py` | 12 | **OK** |

### Fail-without-fix

Each module was run again with only the product code of its own commit put back to the
`origin/dev` version, then restored and compared byte for byte.

| Module | Without the fix | The failures |
|---|---|---|
| `test_leave_ledger_035` | **8 of 9 fail** | Five say `8.0 != 5` — the whole bug: 8 days shown where 5 remain. Two say the helper does not exist. One says the page still reads `total_leaves` |
| `test_home_holidays_035` | **5 of 7 fail** (the note pin was added after this run; it fails without the fix by construction, since the function signature it looks for does not exist) | "Head Office's holiday shown to a store employee"; "2027-01-26 not found" (the December cut-off); the helper does not exist |
| `test_goal_cycle_035` | **11 of 12 fail** | `70 != 40` and `65 != 40` (Q1 blended into Q2); the older review returned instead of the newest; `current_cycle_name` does not exist |

Tests that pass either way, said plainly rather than counted as proof:
- `test_late_rule_days_reach_frappe_hr_at_all` — it guards the 4-line local edit inside
  Frappe HR's `get_leaves_for_period`, which is what makes late-rule days reach any
  balance. It is a guard, not a proof of this slice.
- `test_weekly_offs_are_not_listed_as_holidays` — the old query already skipped weekly
  offs.
- `test_salary_slip_and_home_share_the_lookup` — a fact about Frappe HR that the pin
  keeps true.
- `test_plain_average_when_no_goal_carries_a_weight` — the old average was plain.

---

## 3. The seven dimensions, against the code as written

| Dimension | Before → after | Why |
|---|---|---|
| **Performance** | **degrades slightly, inside budget** | The ledger balance costs more than a two-query sum: measured at 30–37 queries and about 35 ms warm per person against Frappe HR's own function, and the new test asserts one leave type stays inside 12 queries. Budget is 500 ms per call. Holidays **improve** (one list, not every list on the site). `get_team_goals` **improves** (one query for the team instead of one per report) |
| **Security** | **neutral** | No new endpoint, no new permission, no new `ignore_permissions` — the count in `hr_api.py` fell, since the allocation and application reads went. The helper skips Frappe HR's `validate_leave_access` deliberately; every caller checks access first, and two tests cover the manager and HR paths |
| **Reliability** | **improves** | One source per figure. No holiday list is handled, not thrown. No cycle gives the newest rather than an arbitrary one |
| **Scalability** | **improves** | Bounded per person or per team; one loop of queries removed |
| **Maintainability** | **improves** | Four copies of the leave sum became one helper; three goal averages share one rule; each comment names the defect so it is not re-introduced |
| **Data integrity** | **improves** | Nothing stored changed, so there is nothing to backfill; every figure is computed per request. No cache added, so no invalidation to define. The screens now agree with the ledger, the assignments and the appraisal |
| **Compliance / privacy** | **improves** | No personal data logged. No field added to any list, export or notification. `taken` now includes late-rule days, which the same people already see on the deduction card. `appraisal_cycle` is read for ordering and removed before the scorecard replies |

---

## 4. What else moved while I worked

`origin/dev` was at `1c4e84c` at the start and at the end: nothing came in. The mobile
app (013), worker health (026) and the private image package (033) were already in my
base. The main checkout holds another session's Android files in
`mobile/field-app/` — untouched.

Slice 010's board rows claim `get_leave_summary` and `get_team_reviews`; both landed in
`origin/dev` long ago (`git log origin/dev..slice/010-portal-security-fixes` is empty),
so there was nothing to sequence. Slice 034's plan is still unwritten; my page edits are
four small changes inside `loadHomeLeave`, `loadHome` and `renderHolidays`, and nothing
was moved, renamed or re-indented.

---

## 5. Known gaps and shortcuts

- **The ~12 copied lines of `get_leave_balance_on`'s shape** — *intentional trade-off*.
  The alternative refuses managers and store HR on screens that work today. A test
  compares the helper with Frappe HR's own answer, so a drift fails CI.
- **Goals with no cycle are left out of a company's averages when that company has a
  cycle** — *acceptable simplification*, and an [ASSUMPTION] worth confirming: a goal
  belonging to no cycle has no quarter to be counted in. Tenants that never use cycles
  are unaffected (no cycle, no filter).
- **"All cycles Completed" falls back to the newest cycle** — an [ASSUMPTION] beyond the
  letter of Q-G1, so the figure still speaks about one cycle rather than reverting to
  all of them. Say the word and it becomes "no filter".
- **The Time calendar, the correction screen and "team this week" still read
  `Employee.holiday_list`** — *temporary debt*, removed by commit 4, which is waiting
  for the no-fallback decision. Until then the Home card and those screens can disagree
  on a tenant with no assignments.
- **No browser check yet** — *temporary debt*. The page edits were traced by reading,
  and the two page pins are static checks on the file. Home should be opened once on the
  local instance before this ships.
- **The leadership "leave used %"** (`org_figures.py`, slice 012's file) still ignores
  late-rule days: 5 days of 8,045 where the ledger says 81. Untouched on purpose.

---

# Takeover, 23 September 2026 — the numbers checked against each other

A second session picked this slice up after the first one stalled with everything
uncommitted. Two things happened, in this order.

## 0. The inherited work was saved before anything was read

The only copy of commits 1-3 was sitting unsaved in the worktree. It was committed
exactly as found, by path, as `20622b7` ("WIP inherited from a stalled session,
unreviewed"), before a single character was read or changed.

**Then it was checked rather than believed.** All 29 tests the notes above claim were
re-run: `test_leave_ledger_035` 9 OK, `test_home_holidays_035` 8 OK,
`test_goal_cycle_035` 12 OK. Every API the inherited code calls was verified against
the installed source (`get_holiday_list_for_employee` at
`erpnext/setup/doctype/employee/employee.py:373`, and the six leave-ledger helpers in
`hrms/hr/doctype/leave_application/leave_application.py`). The helper's call shape
matches `get_leave_details` exactly.

**Verdict: the inherited work is sound.** Nothing in it was reverted.

## 1. What the second pass added, and why

Surbhi, 23 Sep: *"there should be hundred percent accuracy in calculations and
numbers."* Commits 1-3 made each figure right **on its own**. Read against the
standard literally - *a count must equal the list it links to* - the screens still
carried seven contradictions. Each is a number that was right by itself and a lie
where it was printed.

| # | Where | What the screen did | Now |
|---|---|---|---|
| 1 | Goals page | "Active Goals 1" sat on top of a list of 2. The chips counted one cycle; `get_my_goals` returned every cycle | One rule, `in_cycle`, used by the chips and the list |
| 2 | Goals page | "Due in 30 Days" had **no lower bound**, so a goal whose date had gone by was counted as due and then was not in the list the chip opens | The count is the list: Active, ending today to today + 30 |
| 3 | Goals page | The cycle banner was **site-wide**; the numbers under it were **per company**. On a tenant with two companies the screen named one quarter and counted another | `_get_active_cycle(company)` returns the cycle the chips count |
| 4 | Manager | `get_team_goals` averaged **Active** goals; `get_team_scorecard` averaged **all non-cancelled** ones. One manager, two screens, two "average progress" for one person - a report who had finished their goals read "0 goals, 0%" on one and "100%" on the other | Both use `in_cycle`, both drop Cancelled |
| 5 | Manager | The same two screens rounded differently: `67` and `66.7` | Both to one decimal |
| 6 | Leave | `total - taken` did not equal the balance whenever leave expires, and nothing said where the missing days went. Frappe HR's own screen computes `expired_leaves`; the portal dropped it | `expired` is carried and shown on the ring: total = taken + expired + left |
| 7 | Leave | `max(balance, 0)` on four screens. A leave type set to allow a negative balance can genuinely be below zero; the portal told an employee two days in debt that they had none left, while the leave gate read the ledger and said otherwise | The ledger's own figure, negative and all |

**And one the fix itself introduced.** Filtering goals to "this cycle" would have taken
a goal that names **no** cycle off its owner's screen. PP Jewellers has one such goal
today. `in_cycle` now keeps this quarter's goals **and** goals that belong to no
quarter - a goal with no cycle has no quarter that ended, so it is still live work.
Only *another* quarter's goals are dropped, which was the original defect.

Also: the Home holiday card's `limit=200` was removed. It reads one list now, not
every list on the site, so a cap could only ever drop a real holiday off the end.

## 2. The tests

New file `tests/test_numbers_match_035.py`, 13 tests. It checks the figures **against
each other**, which is the part the first pass did not cover.

| Run | Result |
|---|---|
| `test_numbers_match_035` | **13 OK** |
| The same file with only the product code put back to `20622b7` | **11 of 13 fail** |

The 2 that pass either way, said plainly rather than counted as proof:
`test_the_helper_says_minus_two` and `test_the_ledger_agrees`. Both are about the
helper and Frappe HR's ledger, which were already right - the clamp to zero happened
one layer up, at the screen.

The product files were copied out before that experiment and copied back after, and
the md5 of all three matched byte for byte.

## 3. Real-shaped data: the PP Jewellers copy

Two read-only scripts, run against `ppj.localhost`, each ending in a rollback. Nothing
was written to any site.

**Leave - 403 active employees, 1,209 balance rows:**

| Check | Result |
|---|---|
| Rows where the helper differs from Frappe HR's `get_leave_balance_on` | **0 of 1,209** |
| Rows where total does not equal taken + expired + left | **0 of 1,209** |
| Rows the old portal figure got wrong | **97** - exactly the 97 in the analysis |
| Rows now showing a negative balance | 0 (no PPJ leave type allows negative today) |

**Goals - 213 employees with goals, 425 goals:**

| Check | Result |
|---|---|
| Employees whose average was blended across cycles | **209** (the analysis predicted 210) |
| Worst single overstatement | **50 percentage points** - the analysis's figure |
| Employees who lost an undated goal from their own screen | **0** |

**Holidays - 403 active employees:**

| Check | Result |
|---|---|
| Employees whose Home holiday card was wrong before | **403 of 403** |
| Employees who now see holidays past 31 December | **403** (the old query stopped at the calendar year) |
| Employees with no holiday list payroll can find | **0** - so the deliberate "no fallback" shows the "ask HR" note to nobody on PPJ |

## 4. The seven dimensions, against the code as it now stands

| Dimension | Before -> after | Why |
|---|---|---|
| **Performance** | **neutral vs. the inherited version** | No new query per person. `_dashboard_stats` moved its cycle filter from SQL to Python over one employee's goals (at most 2 on PPJ). `get_team_goals` keeps the single batched query. Removing the holiday cap reads one list, not 200 rows from every list |
| **Security** | **neutral** | No new endpoint, no new permission, no new `ignore_permissions`. Every caller of the ledger helper still checks access first, and the negative-balance test proves the manager path through a manager who is **not** the named leave approver |
| **Reliability** | **improves** | One cycle rule instead of four copies of it; a goal with no cycle can no longer fall between them |
| **Scalability** | **neutral** | Everything stays per person or per team |
| **Maintainability** | **improves** | `in_cycle` and `cycle_by_employee` are the single rule; the two manager screens can no longer round differently or filter differently without a test saying so |
| **Data integrity** | **improves** | Nothing stored changed. The screens now agree with the ledger **and with each other** |
| **Compliance / privacy** | **neutral to improves** | No field added to any list, export or notification. `expired` is the employee's own figure on their own card. Nothing personal logged |

## 5. What I could NOT make exact, and why

- **The payslip's net pay (P5, ticket ALV-90).** 555 of 800 PP Jewellers slips print a
  net that differs from what the bank pays, by up to 50 paise. This is the **single
  biggest accuracy gap in the slice** and it is not mine to decide: whether the slip
  prints the exact figure, the rounded one with a "Rounding" line, or HR turns rounding
  off in Payroll Settings, is Q17 / Q-P1. Untouched, waiting on Surbhi.
- **What an Indian wage slip must legally carry (Q-P3).** Not guessed, as the first
  session also refused to. It needs someone qualified.
- **The leadership "leave used %"** (`org_figures.py`, slice 012's file) - still counts
  only Leave Applications: 5 days of 8,045 where the ledger says 81. Left alone
  deliberately; it belongs to 012.
- **The scorecard's goal list is capped at 15** (30 fetched, current cycle first). The
  cap is silent. PPJ's largest is 2 goals per person, so nothing is cut today -
  *acceptable simplification*, named here rather than hidden.
- **The leave ring's arc, when days have expired.** Every *number* on the card is
  exact and they reconcile: "3 left" in the centre, "3 / 8 used, 2 expired" beneath.
  The arc itself is drawn from `pct_used` (taken over total), so with expired days the
  filled part is not the mirror image of "left". The arc is decoration, not a figure,
  and `hrms-employee.html` is the file slice 034 is waiting on, so it was left alone
  rather than changed for a case that does not exist on PP Jewellers today.
  *Intentional trade-off* - say the word and it becomes one line.
- **No browser check.** The page edits were traced by reading and pinned by static
  checks on the file. Home, the Leave page and the Goals page should each be opened
  once before this ships. *Temporary debt.*

## 6. A mistake worth recording

Partway through, an earlier version of the new test file created a Company inside a
test. Inserting a Company commits (ERPNext builds its chart of accounts), which ended
the test's transaction and left two Appraisal Cycles behind in `test035`. They then
broke `test_goal_cycle_035` on the next run. The rows were deleted from the throwaway
site and the fixture rewritten so the second company is found, not created. Nothing
outside `test035` was touched. Recorded because a fixture that commits is exactly the
kind of thing that makes a wrong number look right.
