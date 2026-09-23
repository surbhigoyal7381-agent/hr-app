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
