---
slice: 091-dtc-overtime-bands
artifact: 05-review (senior architect review; CLAUDE.md section 2, step 5)
author: hrms-technofunctional-reviewer
date: 2026-11-24
---

# 091 overtime by the last punch: senior architect review

**Verdict: SHIP WITH FIXES.** The band table, the edges, the per-person gate, the
typed-time guard and the month money line are correct and match the rule Surbhi
settled on 24 November; nothing leaks into `day_credit`, paid days, or a held, absent
or leave day. Two things need her word before the tick is switched on at a tenant, and
four small test and wording gaps should close before this goes to dev.

**No P0 and no P1.** `SHIP WITH FIXES` is readiness to present for a dev push, not
permission to push.

## Where I looked, and what I ran

| | |
|---|---|
| Worktree | `/Users/mac/hr-app/.claude/worktrees/counsel-reqs-nov24` |
| Branch / head | `docs/counsel-requirements-nov24`, `ad954a3f` |
| Base | `origin/dev` = `215bac59` (fetched by me this session) |
| Diff read | all 16 files of `git diff origin/dev...HEAD`, and the full text of every production file touched, not only the hunks |
| Ran myself | `python3 -m unittest alvoraa_portal.tests.test_overtime_091` → **19 tests, OK**. `test_payroll_rules` + `test_payroll_month` → **128 tests, OK**. Plus my own probe script against `evaluate_day` / `overtime_quarters_for` |
| Could not run | the 17 database tests (`test_overtime_091_db.py`) and every other DB suite. No bench or site in this session. **Their results are unverified by me** |
| Incoming work from others | none. `origin/dev` is the base and the branch is already rebased on it; the five commits on the branch are all this slice |

Labels below: **proven** = I read it in the source or ran it this session; **inferred** =
follows from what I read; **not checked** = I did not or could not look.

## Noted, already decided

Counsel's written position that a band scheme is not lawful overtime is recorded in the
brief and overruled by Surbhi: Alvora configures the client's policy, with no statutory
floor in code and no override modal. I am not re-opening it.

---

## Findings, worst first

### P2 · Major 1 — a time HR typed still pays a night green, once the new tick is on

**Proven, by my own run.** With a 10:30–20:30 shift, one punch, and HR confirming the
check-out as 01:30:

```
evaluate_day(..., last_out=None, punch_count=1, confirmed_out=1530,
             night_green_eligible=True, overtime_bands=BANDS)
-> overtime_quarters = 0   greens = 1   held = False
```

Same for a three-punch day confirmed at 01:30. `payroll_rules.py:893` guards overtime
with `if not typed_out`, which is right. The night green at `payroll_rules.py:883` has
no such guard and reads the same typed `last_out`.

**Why it matters now.** The slice's own contract says a time an HR user typed must never
pay. Before this slice the night green needed a nomination, so at DTC nobody earned it
(the engineer's and coordinator's reading of DTC's data — **inferred**, I did not read
the tenant). The moment `night_green_for_everyone` is ticked, every mark-earning
employee's HR-typed check-out pays a green mark: Rs 100 junior, Rs 200 senior, on a day
no punch supports. The slice refuses to pay the bigger figure from that same typed time
and pays the smaller one.

**This is a decision, not a bug.** Either answer is defensible:

- consistent with Q7: add `and not typed_out` to the night-green condition (one clause);
- or accept it, because a confirmed departure is a real departure — in which case say so
  in writing and the overtime guard looks arbitrary.

**Owner: Surbhi** (the rule), then `hrms-fullstack-engineer` (one line). **Needed before
the tick is set on any tenant, not before the code lands on dev.**

### P2 · Major 2 — filling the band table changes closed months as well

**Proven.** `Alvoraa Payroll Rule Set` has no Date or Datetime field at all (I listed
the field types from its JSON), and nothing about overtime is stored on Attendance. Both
Workings reports re-judge every day from the punches on every run
(`daily_attendance_workings.py:139`, and the salary report through `month_summary`).

**Scenario.** The three rows are saved on 1 December. On 5 December HR re-runs the
Salary Components and Workings report for October to answer a query. October now shows
overtime quarters and Overtime pay for October nights, and Gross and Net include them.
DTC pay from that report into Excel. Nothing in code says those nights were before the
policy existed.

This is how every rule-set change has always behaved (slabs, mark rates), so it is not
new to this diff — but the money per night is new and large: up to a full extra day per
person. **Cheapest answer is no code:** add one line to the switch-on conditions beside
the "add an Overtime salary component" condition — fill the table on the first of a
month, and treat any closed-month re-run after that as needing a sanity check. A
`from_date` on the band row would make it structural and is not worth it for one tenant
today.

**Owner: Surbhi** to accept in writing; the condition list already exists in
`00-impact-analysis.md` D4.

### P3 · Minor 3 — the tick's own description over-claims about dated grants

**Proven**, `alvoraa_payroll_rule_set.json`, `night_green_for_everyone` description:
"…while the morning green stays as the field above nominates it and **the dated green
grants keep counting**."

With the tick on, `_employee_flags` (`payroll_rules_apply.py:320`) returns
`night_green_eligible = True` before any grant is consulted. A dated grant of "None" or
"Morning Green" therefore no longer bars the night green — which is exactly what the
slice intends, and the DB test
`test_the_tick_opens_the_night_green_to_somebody_barred_from_it` asserts it. The grants
keep counting for the **morning** green only.

HR reads that description to decide a pay policy. Fix is a few words: "the dated grants
keep deciding the morning green". The same unqualified sentence appears in
`00-impact-analysis.md` (D1) and should be corrected there too.

### P3 · Minor 4 — the report tests prove a column exists, not that it carries a figure

`TheReportsCarryTheColumns` asserts only that `overtime`, `overtime_quarters` and
`overtime_earning` are in the two `_columns()` lists. **Proven**: the values are set
(`daily_attendance_workings.py:165` and `:191`,
`salary_components_and_workings.py:221-222`), so there is no live defect. But if those
keys were ever dropped, both columns would render blank while Gross and Net still
include the money, and that test would still pass. A blank "Overtime pay" column beside
a Gross that silently contains it is the worst shape this can fail in, because HR's only
way to check the figure is to read the column.

**Closing test, no database needed:** `_row` takes `(emp, s)`, so
`salary._row(frappe._dict(...), MonthSummary(overtime_quarters=6, daily_rate=1000.0,
overtime_earning=1500.0))` can assert both values; and one assertion that the daily
report's row `overtime` equals the day's `overtime_quarters`.

### P3 · Minor 5 — the real-punch test's power is reasoned, not observed

`test_a_ten_past_one_punch_on_the_next_date_pays_two_quarters` was never watched to fail
on a wrong overtime figure (three DB breaks failed as setup ERRORs). I traced it instead:
if the `+1440` for Next Day were dropped, `prepare` would return `[(60,2),(180,4),(1380,1)]`
and a 1510 punch would score 1, not 2, so the test **would** fail on the number
(**inferred**, from reading `overtime_bands` and `overtime_quarters_for`; I verified the
equivalent arithmetic in the no-DB file, which I ran). Same for the other two breaks:
`test_with_the_tick_off_nothing_changed` and `test_a_contract_person_sees_no_green` both
assert a value that flips if their fix is removed.

So the hole is thinner than it looks, but it is real: nobody has seen those three fail.
**Smallest close:** add to the real-punch test one assertion on the reason sentence
(`"last punch 01:10"` must appear — that can only be true if the punch reached the
engine as minute 1510) and a second case at 03:10 expecting 4. Both one-liners, and they
fail on a number for any clock-conversion mistake.

### P3 · Minor 6 — the neighbouring suites were not re-run

Every suite that saves an `Alvoraa Payroll Rule Set` now runs `_check_overtime_bands`,
and every caller of `prepare` now receives two extra ctx keys. I checked the two ways
that usually break:

- no production or test code builds a ctx dict by hand — `prepare` is the only source
  (**proven**, grep over `*.py`/`*.js` for `_employee_flags(`, `night_for_all`,
  `overtime_bands`);
- no test asserts an exact column list or an exact ctx dict in `test_salary_report.py`
  or `test_daily_workings_alv358.py` (**proven**, grep), and the one Contract case in
  `test_day_marks.py:532` asserts about reds and grace, never about greens, so the
  `_green` change does not move it (**proven**, read).

Risk is low, but it is unverified. **Run before the dev push:** `test_payroll_flags`,
`test_day_marks`, `test_green_eligibility`, `test_salary_report`,
`test_daily_workings_alv358`, `test_payroll_reprocess`, `test_pay_slip_marks_067`,
`test_break_and_reason_alv328`, `test_punch_fix_087`, `test_leave_063_rules`,
`test_grooming_066`, `test_alv291_attendance_fix`, `test_midnight_punch_alv402`.

### Nits (P4)

<details><summary>Three small ones</summary>

1. **`overtime_quarters_for` depends on the list being sorted.** Proven by my own run:
   bands `[(1620,4),(1380,1),(1500,2)]` with a 02:20 punch return 2, not 4. `prepare`
   always sorts, so there is no live defect; the docstring says so. An order-free body
   is the same length: `return max((q for e, q in bands if last_out >= e), default=0)`.
2. **One mistyped row is not caught.** A single row "01:00" with Next Day unticked is
   edge 60; proven by my run, everyone past shift end + 60 then earns its quarters. With
   two or more rows the rising-quarters check catches a forgotten tick (I traced the
   three-row case: it throws). Optional guard: refuse an un-ticked edge before noon.
3. **`_check_overtime_bands` reads `self.overtime_bands` directly.** Between a code
   deploy and `bench migrate` the field is not yet in the DocType meta, so saving a rule
   set in that window would raise AttributeError. Releases always migrate, so this is
   theory; `self.get("overtime_bands") or []` removes it.

</details>

---

## Acceptance check against the settled rule

The settled section of `00-impact-analysis.md` is the contract. Every row below I either
ran myself or read in the source.

| The rule | Result | Evidence |
|---|---|---|
| before 23:00 → nothing | **met** | my run: 22:59 (1379) → 0 |
| 23:00–00:59 → 1 quarter | **met** | my run: 1380 → 1, 1499 → 1 |
| 01:00–02:59 → 2 | **met** | my run: 1500 → 2, 1619 → 2 |
| 03:00 or later → 4 | **met** | my run: 1620 → 4, 1800 (06:00) → 4 |
| Milestone passed, at or after; totals not increments | **met** | `overtime_quarters_for`, `payroll_rules.py:454-469`; last band reached wins |
| Shift-day clock, Next Day adds 1440 | **met** | `overtime_bands`, `payroll_rules_apply.py:95-105`; DB test pins `[(1380,1),(1500,2),(1620,4)]` (that test not run by me) |
| First band also needs shift end + 60, per person | **met** | `payroll_rules.py:464`; my run on a 22:00-end shift: 22:59 → 0, 23:00 → 1 |
| Stacks with the night green | **met** | my run: 23:05 → greens 1, overtime 1 |
| Contract (earns no marks) earns no overtime and no green | **met** | overtime sits after the `if not earns_marks: return v` at `payroll_rules.py:874-885`; my run with `earns_marks=False` → (0, 0) |
| Never doubled on a special day | **met** | the multiplier touches `slab_quarters` only (`:795-805`); test passes |
| None on held, absent, leave, half-day leave | **met** | every `v.held = True` returns before the overtime block; the greens block returns when `last_out is None`; `_judge_other_half` never sets it. My run confirms all four |
| Nothing typed by HR ever pays overtime | **met** | `typed_out` set at `:700` and `:724`, read at `:892`; my run → 0 on one-punch and three-punch confirmations |
| `day_credit`, `total_quarters`, paid days unmoved | **met** | separate field; my run shows identical `total_quarters` and `day_credit` with and without a late punch, and `day_credit` never above 1.0 |
| Money added to Gross once, Net once | **met** | `payroll_month.py:252, 281-282`; the unit test asserts the rise in both equals `quarters/4 × daily_rate`, and I ran it |
| A month re-run is identical | **met** | derived from punches, nothing accumulated across runs; fresh `MonthSummary` per call (`payroll_month.py:148`) |
| No statutory floor, no override modal | **met** | nothing of the kind in the diff |
| Card row deliberately not built | as agreed | `portal.js` untouched |

**Business fit.** HR can check the figure: the Daily Workings report shows the overtime
quarters per day plus a reason line that names the clock time ("Overtime: last punch
01:10, 2 quarter(s) of a day on top."), the month total comes from the same
`month_summary` the slip uses, and the Salary Workings report shows quarters and rupees
beside Basic earned with `add_total_row` on (**proven**, report JSON). That is checkable.
The one weakness is Minor 4 above — nothing fails if a cell stops being filled.

**Three personas.** Employee: nothing new on screen (agreed). HR Manager: two new
columns and a reason sentence, inside the scoping that already exists
(`_may_read_days_of`, read this session). CXO: the auto-totalled columns. Line manager:
nothing. **No widening of who sees what** — the new keys sit inside rows the viewer could
already see (**proven**, the diff adds no query and no new endpoint).

## Non-functional, re-checked against the code

| Dimension | Analysis claimed | My finding |
|---|---|---|
| Performance | neutral | **Neutral, proven by reading.** No new query: the bands ride inside the rule set doc that `prepare` already loads, and `overtime_bands()` is an in-memory sort of at most a handful of rows. Per day it adds one loop over ≤3 tuples. Speed on real DTC data **not measured** (accepted) |
| Security | neutral | **Neutral, proven.** No new endpoint, no `@frappe.whitelist()`, no `ignore_permissions`, no raw SQL, no client-supplied value choosing a field or doctype. No new field exposed to a wider audience |
| Reliability | improves slightly | **Agreed.** Empty table = no overtime, no error. Save-time checks refuse an unusable table. One gap the analysis did not name: a single mistyped row passes (nit 2) |
| Scalability | neutral | **Neutral, inferred.** At ~620 staff × ~30 days the added work is ~56,000 integer comparisons per report run and no extra database reads |
| Maintainability | neutral to slight degrade | **Agreed.** One child DocType (identical in shape to `Alvoraa Attendance Slab`, including its controller), one 15-line function, one constant. `OVERTIME_AFTER_SHIFT_MINUTES` duplicates the value of `NIGHT_GREEN_LATE_MINUTES`; a test pins the two gates together, so drift is caught |
| Data integrity | improves | **Mostly agreed.** Derived, never accumulated, so no double pay on a re-run (I ran that test). The analysis did not name the retroactive effect on closed months — that is Major 2 |
| Compliance / privacy | neutral, one open item | **Neutral, proven.** No new log line, no new personal field, no third party, no model prompt. The reason line carries the person's own last-punch time, as the existing green reason already does |

## Compliance axis

**Partly unreviewable, and that is a process gap worth naming.** Slice 091 has no
`02-functional-spec.md`, no `01c-security-privacy-requirements.md` and no
`07-devops-inputs.md`, so there is no compliance-impact sub-analysis to walk row by row.
I will not improvise one. What I can say:

| Obligation | Mechanism in the diff | Test | State |
|---|---|---|---|
| Pay rule is configuration per tenant, not code | `overtime_bands` on the rule set; empty = off | `test_no_table_means_no_overtime_and_saves_fine` (not run by me) | discharged |
| No tenant changes until rows exist | empty table returns `[]`; new Check defaults to 0 | same | discharged |
| The day's figure is explainable to the employee | reason sentence with the clock time | `test_the_reason_line_says_what_was_paid` (I ran it) | discharged |
| Derivation replayable from stored inputs | punches only; nothing stored, nothing accumulated | re-run test (I ran it) | discharged |
| Statutory overtime floor | none, by Surbhi's decision | — | not adopted, decision recorded |

## What to delete

**Nothing.** I looked for the usual suspects and did not find them: no feature flag, no
abstraction layer, no cache, no new app or module, no settings page, no stored field, no
migration for data that does not exist, no hook on a shared doctype, no new dependency.
The child DocType is three fields and a `pass` controller, byte-for-byte the pattern
`Alvoraa Attendance Slab` already uses, and the engineer's own subtract pass had already
removed the Attendance custom field, the extra category tick and a card feature flag.
The one shared helper has two real callers planned and one today; it stays because the
alternative is two copies of the gate.

## What was done well

- **Keeping the earned quarters out of `total_quarters`** instead of letting `day_credit`
  exceed 1.0. That single decision is why none of the dozen existing readers of
  `total_quarters`, `quarter_days`, `day_credit` and `paid_days` changes meaning, and I
  could confirm it in one run.
- **Placing the overtime block after the `earns_marks` return** rather than adding a
  second category tick. Contract is excluded by a rule that already existed, with no new
  default-ON trap on migrate.
- **The `typed_out` flag.** It is the part most likely to have been coded wrong, it is
  right, and it has a test that asserts both the one-punch and the odd-punch route.
- **Fixing the card's green for Contract staff in the same slice.** The tick would have
  exposed it; shipping the tick without it would have told hundreds of people they could
  earn a mark they cannot.
- **Validating the band table at save, against the sorted edges rather than row order.**
  A Next Day row typed above a 23:00 row is read correctly and still validated correctly
  — I traced that case specifically, and there is no hole there.

## Confidence, and what I could not check

**Proven by running:** the full edge table, the per-person gate on two shift ends, the
typed-time behaviour (both routes), the stacking, the Contract exclusion, the isolation
from `day_credit` and `total_quarters`, the month money and its re-run, 19 new unit tests
and 128 neighbouring engine tests.

**Not checked:**

- the 17 database tests, and every other DB suite — no bench or site in this session.
  Their green state is the engineer's claim, not mine (Minor 6 says which to run);
- DTC's live data: who holds a green nomination today, how many dated grants exist, the
  last-punch distribution, the rupee cost of the tick plus the bands;
- report speed on real DTC data (accepted as out of scope);
- the Your Day card row, the salary slip component and the stored field — all three
  deliberately not built, and the slip component is already a written condition of
  switching the engine on.

**One question that would change nothing in the code but should be answered before the
tick goes on:** Major 1, the typed-time night green. I am ranking it P2 rather than P1
because the code can land on dev with the tick off and no tenant is affected until
somebody ticks it.
