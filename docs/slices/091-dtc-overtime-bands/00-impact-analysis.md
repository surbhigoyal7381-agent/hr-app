---
slice: 091-dtc-overtime-bands
artifact: 00-impact-analysis (impact analysis and proposed strategy; CLAUDE.md section 2, steps 1 and 2)
author: hrms-fullstack-engineer
date: 2026-11-24
status: PROPOSAL. Waiting for Surbhi's approval. No code has been written.
worktree: /Users/mac/hr-app/.claude/worktrees/counsel-reqs-nov24, branch docs/counsel-requirements-nov24, head f45b7f15
base: origin/dev was 2d768a9b when the brief was written. I fetched today: origin/dev is now 215bac59 (5 new commits)
---

# 091 DTC overtime by the last punch: impact analysis and strategy

# SETTLED BY SURBHI, 24 NOV 2026 (this section overrides anything below it)

**The rule: a milestone passed, at or after.** A day is worth the value of the latest band time the last punch has reached. The last punch is on the shift-day clock (`last_out` in minutes from the shift day's midnight: 01:00 is 1500, 03:00 is 1620; `payroll_rules.py` `punch_minutes`). Nothing counts before the person's own shift end + 60 minutes.

| Last punch | Day is worth | Extra |
|---|---|---|
| before 23:00 | 1.00 | nothing |
| 23:00 to 00:59 | 1.25 | **1** quarter |
| 01:00 to 02:59 | 1.50 | **2** quarters |
| 03:00 or later | 2.00 | **4** quarters |

The steps are uneven on purpose (+1, +2, +4) and stored as totals. 21:00 earns nothing; 23:00 and 00:30 both pay 1.25; 01:00 and 02:00 both pay 1.50; 03:00 and 04:30 both pay 2.00. **This replaces the "by" wording everywhere below.** D5 is closed: 01:01 pays 1.50, not 2.00. The edge test results in section 13 are: 22:59 nothing, 23:00 1, 23:01 1, 00:59 1, 01:00 2, 01:01 2, 02:59 2, 03:00 4, 03:01 4, 04:00 4.

- **D1: option C.** One tick on the rule set (`night_green_for_everyone`), labelled "Night Green For All Staff Who Earn Marks" because staff in a category that earns no marks, such as Contract, earn no greens of any kind, ticked or not (confirmed by Surbhi). Night green only. The morning green stays nominated by `green_eligibility_field` and the dated green grants keep deciding the morning green. With the tick on, a dated "None" or "Morning Green" no longer bars the night green; that is the point of the tick. `green_eligibility_field` is not blanked and nothing is hard-coded.
- **D3: the Your Day card row is deliberately NOT built.** It is user-facing, so it waits for a UX prototype Surbhi approves (prototype parity). The engine, the month money line and both Workings report columns are built. **One card fix is in, because the new tick would expose it:** a Contract person (a category that earns no marks) no longer sees a green line on the card (`day_marks._green`).
- **D4: accepted.** DTC pays from the Salary Workings report into Excel, not from posted slips. **HARD CONDITION OF SWITCHING THE ENGINE ON AT DTC: add an "Overtime" salary component and one line to `ENGINE_LINES` in `payroll_slip.py` first.** Without it a slip carries no overtime and staff are underpaid. Whoever does the switch-on must not skip this.
- **No stored field on Attendance.** Reports and the slip re-judge each day from the punches. **When the engine is switched on, add a stored `overtime_quarters` field with the reprocess preview change (about 15 lines), so a reprocess shows overtime movement.**
- **Contract:** reuses `earns_marks`; no new category tick. Overtime is placed after the `if not earns_marks: return v` block in `evaluate_day`.
- **A typed time pays no green and no overtime (Surbhi, 25 Nov 2026).** A check-out time that HR confirmed on a one-punch or odd-punch day pays neither the night green nor overtime. Only a real punch pays.
- **Closed months: accepted, no code, a switch-on condition (Surbhi, 25 Nov 2026).** Nothing is stored, so filling the band table re-prices any month that is re-run. **Enter the band rows only at a month boundary (the first of a month), and never re-run a month that has already been paid.** No stored field, no migration. This sits beside the Overtime salary component as a condition of switching on.
- **Release note (nit, not fixed in code):** one mistyped band row with Next Day unticked, for example "01:00" meant for after midnight, is not caught on its own; two or more rows are. Check the rows after entering them.
- **Not built, by design:** the card row, the stored field, the slip component.

---

**Labels used below:** proven (I read it in the source this session, file and line named), inferred (follows from what I read, not run), not checked.

## 0. Read this first

1. **Two things in the brief are wrong or incomplete, and the second one is a pay bug waiting to happen.**
   - **The brief says the Your Day card "reads the verdict". It does not.** The card builds its own picture from the rule set and today's punches (proven, `day_marks.py` `marks_today`, lines 81-186). It never touches `day_credit` or `total_quarters`.
   - **The card shows a night green to Contract staff who can never earn one.** `_green()` (`day_marks.py` lines 317-362) does not look at `earns_marks`. Today this is hidden because nobody at DTC passes the green field. **The moment the field is blanked, every Contract person is told "Night green: leave after 21:30" and the engine pays them nothing** (proven, section 4). This must be fixed in the same slice. It is two lines.
2. **The Salary Workings report and the Daily Workings report do not read anything stored on Attendance.** They re-judge every day from the punches on every run (proven, `payroll_slip.py` line 118 `verdicts = [judge(r, ctx) for r in rows]`; `daily_attendance_workings.py` line 139 `v = judge(att, ctx)`). So the brief's "one Custom Field on Attendance" is **not needed to make the reports show overtime**. I recommend leaving it out (section 3).
3. **Switching DTC's engine on later would not pay overtime on a salary slip.** The slip takes only paid days plus three Additional Salary lines (red, green, grooming) (proven, `payroll_slip.py` lines 63-68 `ENGINE_LINES`). The brief's "one new money line" lands in the report's Gross and Net only. That is fine while DTC works pay in Excel from the report (the brief's own assumption, not re-verified). It must be settled before switch-on (section 11, D4).
4. **There is no functional spec and no UX design for this slice.** I am treating the approved brief plus the coordinator's note of 24 Nov as the contract (section 10). The card row is user-facing, so prototype parity applies and I propose to build it last, behind a design gate.

## 1. Where the extra pay lives (your point 1)

**Proven: `day_credit` cannot carry it.** `DayVerdict.day_credit` (`payroll_rules.py` lines 327-365) returns `1.0 - total_quarters / QUARTERS_PER_DAY` on a worked day, and `total_quarters` is `slab_quarters + extra_quarters` ("every quarter lost", line 319-321). It can never go above 1.0.

**The answer, thin:**

| Piece | Where | What |
|---|---|---|
| New verdict field | `DayVerdict` in `payroll_rules.py` | `overtime_quarters: int = 0`. **Not** part of `total_quarters`. |
| Where it is set | `evaluate_day`, **after** the `if not earns_marks: return v` block (line 835-841) and the "no punches" return (line 845-846), next to the greens (line 848-855) | One lookup of the last punch against the bands, plus one line in `v.reasons`. |
| Month total | `summarise_month` in `payroll_month.py` | `m.overtime_quarters += v.overtime_quarters` in the loop (beside line 148-152). After `daily_rate` is set (line 242): `m.overtime_earning = m.overtime_quarters / QUARTERS_PER_DAY * m.daily_rate`. Gross (line 274) becomes `earning_basic + green_earning + overtime_earning + incentive`. Net (line 275) already starts from gross. |
| Reports | both Workings reports | New columns, section 7. |
| Card | `day_marks.py` and one block in `portal.js` | A read of the same bands. Section 8. |

### Every current reader, and whether any would double-count (counts from grep over `*.py`, `*.js`, `*.html`; tests and `scripts/` excluded)

| Name | Production readers | Would overtime double-count? |
|---|---|---|
| `day_credit` | **1**: `payroll_month.py:152` (`m.day_credits += v.day_credit`). The definition is `payroll_rules.py:328`. | No. I do not change it, and overtime is not inside it. |
| `total_quarters` | `payroll_month.py:148` (sum), `payroll_month.py:108` (`quarter_days`), `payroll_reprocess.py:145,151,156,163`, Daily Workings `:162,187`, Salary Workings `:205`, plus the property uses inside `day_credit` (`payroll_rules.py:325-365`). | No. Overtime is a separate field, so none of these readers sees it. If I had put overtime inside `total_quarters` it would have been subtracted as a loss everywhere. That is the double-count to avoid, and it is why the field is separate. |
| `days_deducted` | defined `payroll_rules.py:324`; no production reader found | No. |
| `quarter_days` (month) | `payroll_month.py:107`; the two reports `daily :194` and `salary :206` | No. |

**Proven: `earning_basic = paid_days x daily_rate`** (`payroll_month.py:243`) and `paid_days = day_credits + leave credits` (line 239). Overtime does not enter `paid_days`, so Basic earned is unchanged.

**Re-run safety (proven by reading, to be proved by a test).** Overtime is worked out from the punches each time, and nothing is added up across runs. A second run of the same month gives the same number. Nothing can be paid twice by re-running.

## 2. The band table as data (your point 2)

**Cost ladder.**

| Rung | Can it carry the bands? |
|---|---|
| Existing child tables on the rule set | **No.** Five exist: `slabs` (Alvoraa Attendance Slab: percent from/to, quarters off, raises red), `mark_rates` (grade, amount), `leave_classes`, `leave_credit_rows` (designation, month length, days, credits), `categories` (read from the DocType JSON this session). `slabs` is a percent-of-shift table, not a clock table, so reusing it would mean a row that means two things. |
| Flat fields on the rule set (6 fields) | Works, but the "next day" part of 01:00 and 03:00 has to be hard-coded in the engine, and nobody can add or move a row. |
| **One new child DocType on the rule set** | **Chosen.** Same shape the engine already reads for `slabs`. DTC can tune a row without a code change. |

**Proposed child DocType `Alvoraa Overtime Band`**, parent field `overtime_bands` (Table) on `Alvoraa Payroll Rule Set`:

| Field | Type | Meaning |
|---|---|---|
| `last_punch_by` | Time | The clock edge, e.g. 23:00, 01:00, 03:00 |
| `next_day` | Check | Tick for 01:00 and 03:00 (after midnight). A Time field cannot hold "01:00 tomorrow" |
| `total_quarters` | Int | **Total** quarters for that band (1, 2, 4), not an increment. This matches the brief's rule 2 |

`prepare()` turns each row into `(edge_minutes, total_quarters)` where `edge_minutes = minutes(last_punch_by) + 1440 if next_day`. So 23:00 is 1380, 01:00 is 1500, 03:00 is 1620.

**Save-time checks** (same spirit as `_check_slabs`, `alvoraa_payroll_rule_set.py` lines 108-150): edges strictly rising, totals strictly rising, every total between 1 and 4, no blank row, an empty table is allowed (it means "no overtime", so no tenant is affected until rows exist).

**The cheapest honest alternative** is the six flat fields. I do not recommend it, for the reason in the table.

## 3. The Attendance field the brief proposed (recommend: leave it out)

The brief lists "one Custom Field on Attendance" (rung 3). Reading the code shows what it would buy and cost:

| | Keep the field | Leave it out (recommended) |
|---|---|---|
| Reports and slip | Do not read it (proven above) | Same |
| Reason text per day | Already stored by `write_verdict` in `alvoraa_rules_why` (`payroll_rules_apply.py:558`), so the overtime sentence is kept either way | Same |
| Cost | A Custom Field in `payroll_fields.py` (runs at `after_migrate`), an entry in `VERDICT_FIELDS` (`payroll_rules_apply.py:44`) and in `write_verdict` (line 540), an edit to `payroll_reprocess.py` preview, and an update to the two existing tests that compare `VERDICT_FIELDS` (`test_payroll_reprocess.py:189,193,212,216`) | Nothing |
| Risk | An image that lands before its migrate makes `write_verdict` and the reprocess read fail on "unknown column", on every tenant with an enabled rule set (ppj.dev today). The code already has to guard `alvoraa_fix_aside_request` for this reason (`payroll_rules_apply.py:401`). A stored copy can also go stale against the live report | None |
| What you lose | | The reprocess **preview** (`payroll_reprocess.preview`) would not show overtime movement, because it compares stored quarters before with judged quarters after (lines 139-156). It is only reachable with the engine ON (`rule_set_for` needs `enabled`), so it does not matter at DTC today. **Add the field at the switch-on decision**, with the preview change. It is about 15 lines. |

This is a deviation from the brief's rung. It removes work and a deploy-order risk. I recommend it, and Surbhi can overrule it.

## 4. Q12: does a Contract person who stays late earn the night green? (your point 4)

**PROVEN: No.** Three places, all read this session:

1. `payroll_rules.py` line 835 `if not earns_marks:` ... line 841 `return v`. This is **before** the greens at lines 848 (morning) and 852 (night). A day for a category that earns no marks returns with `greens = 0`, whatever the green gate says.
2. `payroll_month.py` line 249 `if not earns_marks: m.reds = 0; m.greens = 0`. Even if a verdict had a green, the month zeroes it. The caller passes `earns_marks=(cat.earns_marks if cat else True)` (`payroll_slip.py:186`).
3. Where the flag comes from: `payroll_rules_apply.py` line 287 `"earns_marks": override.get("earns_marks", True)`. `override` is the category row matching the employee's category field.

The coordinator reports DTC's Contract row has `earns_marks = 0` (database value, read by the coordinator, **not re-read by me**). The code path is proven. **So the PM's inference is confirmed, with the card defect in section 0 that the PM did not see.**

**What this means for the design.** `earns_marks` already means "this category is Contract". Overtime is also off for Contract. So **I recommend overtime reuses `earns_marks`** instead of a new "overtime paid" tick:

- Put the overtime lookup after line 841. Contract has already returned. Overtime is off for Contract with no new field, no new default-ON trap on migrate, no extra category column, and the card needs no second rule.
- **The cost is a coupling:** if DTC ever wants a category that earns marks but not overtime (or the reverse), a tick is needed then. That is about 15 lines. I judge it not worth building for a case nobody has asked for.
- **Not recorded for Contract:** satisfied, because no verdict field is stored (section 3) and the early return means the engine never computes it.

## 5. Q11: blanking the green field (your point 3) (Surbhi decides; I cost it both ways)

### (a) What blanking does today (proven)

`payroll_rules_apply.py` lines 302-305:

```
"morning_green_eligible": (green in GREEN_MORNING) if ctx["green_field"] else True,
"night_green_eligible":   (green in GREEN_NIGHT)   if ctx["green_field"] else True,
```

`ctx["green_field"]` is `rule_set.green_eligibility_field` (line 188). **Blank means both are True for everyone.** Four more things, all proven:

- It opens the **morning green** too (arrive 120 minutes before shift start, `MORNING_GREEN_EARLY_MINUTES`, `payroll_rules.py:105`), which Surbhi did not ask for.
- It **switches off the dated grants** (`Alvoraa Green Eligibility` rows, `_green_on`, read at line 240). The grant is looked up and then never used, because the test on lines 302-305 skips it when the field is blank. How many grant rows DTC holds: **not checked**. If any, they stop mattering.
- The Your Day card follows automatically, because it asks `day_rules_on`, which returns these same two flags (lines 355-358). Every employee would see a morning green line.
- **Contract staff would see both green lines on the card and earn neither** (section 0, point 1).

### (b) What separating the two gates costs

| Option | Change | Size | Effect | Risk |
|---|---|---|---|---|
| **A. Blank the field** (the brief's way) | Data only, on DTC's rule set | 0 lines | Night and morning green for all 495 | Morning green for everyone; dated grants void |
| **B. Hard-code "night green for all"** | `"night_green_eligible": True` in `_employee_flags` | 1 line | Night green for all, morning still nominated | Policy hard-coded in shared code. Any tenant that names a field loses its night nominations. Today that is only DTC (coordinator's measurement) but it is the wrong place for a client policy |
| **C. One tick on the rule set, "Night green for everyone"** (default off) | New Check on `Alvoraa Payroll Rule Set`; `prepare` reads it; `_employee_flags` line 304 becomes `True if ctx["night_for_all"] else ...` | About 8 lines plus a test for tick on and tick off | Does exactly what Surbhi said. Policy stays data. Nothing changes anywhere until a rule set ticks it | Rule set JSON is a hot file; needs a migrate |

**Recommendation: C**, because Surbhi's words were "green mark after one hr of the shift ends", about the night only, and the morning green for everyone is a separate pay decision. **If she also wants the morning green for everyone, choose A and it costs nothing.** Either way, **the card fix for Contract (section 0) is in the slice.**

### Rupees (inferred ceiling; the real figure is not measured)

- Mark rates, from the coordinator: Junior Rs 100, Senior Rs 200, External and "No leaves" Rs 0. Active staff: Junior 476, Senior 16, External 1, blank grade 2.
- **Ceiling for one green type** if every one of them earned it on a day: 476 x 100 + 16 x 200 = **Rs 50,800 a day**. That is the most it can be, not a forecast. It also counts Contract people, who earn nothing, so it overstates.
- **Blanking moves night-green eligibility from 0 to 495 people** (coordinator). Whether a person actually earns it depends on leaving after shift end + 60 (21:30 on the 10:30-20:30 roster).
- The real figure needs one thing I have not got: the last-punch distribution. **The way to get it, with no new code:** on a copy of DTC's data, blank the field (or tick C), and run the Salary Workings report for November. It already prints **Greens** and **Green pay** per person (`salary_components_and_workings.py` `_row`, lines 218-224). The report works with the engine off (proven, its message at lines 280-288). Not run by me.
- The same run gives the overtime rupees once the bands exist (Rs 250 a quarter at Rs 30,000 basic over 30 days; illustrative, not DTC's).

## 6. The 03:00 band and the midnight boundary (your point 5)

**PROVEN: the engine already works on a shift-day clock, not a wall clock. The bands must be stored on that clock.**

- `punch_minutes(times, day=date)` (`payroll_rules.py` lines 187-202): `late = (t.date() - day).days * 1440`, then `+ hour*60 + minute`. A punch on the next calendar date runs on past 1440. The docstring says so (ALV-402).
- `_punches` (`payroll_rules_apply.py:376`) reads the day and the next calendar day (`between date 00:00:00 and add_days(date,1) 23:59:59`), keeps only punches whose `shift_day()` equals the day, and passes `day=date` to `punch_minutes`. `shift_day` is the date of the punch's `shift_start` (line 365), falling back to its calendar date.
- The existing test `test_midnight_punch_alv402.py` line 56 pins `_punches(...) == (655, 1440, 4, ...)`: 00:00 after the shift day is minute 1440.

So `last_out` reaching `evaluate_day` is already minutes from the shift day's midnight: **23:00 = 1380, 01:00 = 1500, 03:00 = 1620, 03:30 = 1650, 04:00 = 1680.** A band edge stored as plain wall-clock minutes (01:00 = 60) would be wrong: a 01:10 punch (1510) would never match. That is why the table has `next_day` (section 2) and `prepare` adds 1440.

**Superseded by the settled rule at the top.** On a 10:30-20:30 shift (gate 21:30): 21:29 pays 0; 22:59 pays 0; 23:00, 23:01 and 00:59 pay 1; 01:00, 01:01 and 02:59 pay 2; 03:00, 03:01 and 04:00 pay 4.

**Other things I read that bite here:**

- **Seconds are dropped** (`punch_minutes`, `minute()`; ALV-326 D3). 23:00:59 reads as 23:00 and pays band 1. That is the existing DTC rule for every figure, so I keep it and put a test on it.
- **A real punch only.** `evaluate_day` replaces `last_out` with the typed time on a one-punch or odd-punch day (`last_out = confirmed_out` at `payroll_rules.py` lines 669 and 692). Brief Q7 says an HR-typed time must not pay overtime. So the new code must remember that `last_out` was typed. A local flag set in those two branches does it. **This is the part most likely to be coded wrong, and gets its own test.**
- **A shift that ends after midnight is held** (`shift_minutes <= 0`, `payroll_rules.py:613`). So `shift_end` is always on the same day and the gate arithmetic `shift_end + 60` never wraps.
- **Capture window.** A punch after the shift's check-out window gets no `shift_start`, keeps its calendar date, and lands on the next day, which holds both days (ALV-402). The brief names four shifts whose window closes before 05:00. Not re-measured by me. Overtime for those nights is lost until HR fixes the punch.
- **The card is a calendar-day card.** `_punches_today` (`home_api.py:224`) reads today's calendar date. After midnight the card is already on the new day, so a 00:30 punch is not on it. The card row is therefore a **table before midnight**, not a record of the finished night. HR sees the finished night in the report. Not checked what the card does between 00:00 and 05:00 beyond that.

## 7. Reports (your point 1, second half)

| Report | Change | Proven shape |
|---|---|---|
| Daily Attendance Workings | `row["overtime"] = v.overtime_quarters or None` in `_day` (beside line 162); one column in `_columns` (line 278-295); the month total row (`_totals`, line 187) shows the sum; the existing `remarks` line already carries `v.reasons`, so the sentence "Overtime: last punch 23:42, by 01:00: 2 quarters" appears with no extra code | The report calls `judge` itself (line 139), so it needs no stored field |
| Salary Components and Workings | `overtime_quarters` and `overtime_earning` in `_row` (line 218-224 area) and `_columns` (line 295-340); one sentence added to `_message` (line 280-303) so HR reads that Net already includes it | Gross and Net come from `MonthSummary`, so Net adds it once |

**Two guards.** (1) A test that gross rises by exactly `overtime_quarters / 4 x daily_rate` and that Net equals gross minus the same deductions as before. (2) The message under the report must not say "Net already takes off both new columns" in a way that now reads wrong; I will re-read that text when I edit it.

## 8. The Your Day card

- Reads: the rule set (bands) and the punches, through `marks_today`. **No verdict is involved.**
- New data in the `marks_today` payload: the three bands as clock times, this person's gate (`shift end + 60`), and, before midnight, what the last punch so far is worth.
- **To keep the engine and the card from drifting** (the file's own header warns about exactly this), both call one small function `overtime_quarters_for(last_out, shift_end, bands)` in `payroll_rules.py`, and the card imports the gate constant the way it imports `NIGHT_GREEN_LATE_MINUTES` (`day_marks.py:36`). That is two real callers, so the function is justified.
- Hidden for staff who do not earn marks, by the same `earns_marks` answer the card already receives in `rules` (`day_marks.py:164`). The same check fixes the green defect in section 0.
- JS: one block in `dmMarks` (`portal.js` line 11144 on). `portal.js` is a hot file (big, many slices touch it). **Held behind the UX gate** (section 10).

## 9. Non-functional assessment (all seven dimensions, CLAUDE.md section 2)

| Dimension | Verdict | Reason |
|---|---|---|
| **Performance** | **Neutral** | No new query on the engine path. The bands arrive inside `prepare()`, which already loads the rule set's child rows once (`rule_set` is a cached doc, `rule_set_for` returns `get_cached_doc`, `payroll_rules_apply.py:78`). Per day it adds a loop over at most a handful of rows in memory. The month report is 495 people x about 30 days of `judge` calls, and the number of database reads per day does not change. **Not measured**: I will time the November Salary Workings run before and after on a copy and report the numbers. |
| **Security** | **Neutral** | No new endpoint, no `ignore_permissions`, no new whitelisted function. The new money columns sit in two reports that already scope by `_days_scope` / `permitted_employee_filters` (`salary_components_and_workings.py` around line 110-135, read this session). The card shows a person only their own row. The line manager sees nothing new. |
| **Reliability** | **Improves, slightly** | An empty table means no overtime and no error. The rule set refuses bad tables at save. The engine uses only the verdict, so a rules problem cannot block saving attendance (the submit hook is already wrapped, `payroll_rules_apply.py` lines 625-637). The card fix removes a statement that is wrong for Contract staff. |
| **Scalability** | **Neutral** | Cost grows with headcount x days exactly as today; one extra comparison per day. Re-running a month is a pure function of punches. |
| **Maintainability** | **Neutral to slight degrade** | One new child DocType and one new function. Offset by: no stored field, no new category tick, and the card and engine share one function. The one coupling I accept: overtime follows `earns_marks`. |
| **Data integrity** | **Improves** | Overtime is derived, never accumulated, so a re-run cannot pay twice. It is kept out of `total_quarters` so no existing total moves. `day_credit` is untouched. With no stored field there is no second copy to go stale. The slip gap (section 0, point 3) is the one integrity risk and is named. |
| **Compliance / privacy** | **Neutral, with one open item** | No personal data in any new log line (I add no logging). The reason line holds a clock time of the person's own last punch, as the engine's reasons already do. No new sensitive field. Counsel's document says a band scheme does not meet statutory overtime (brief section 12). **Surbhi has decided; the policy is DTC's and Alvora configures it.** No statutory floor, no override modal, no IP log. U1 (the document is unsigned) is carried, not solved here. |

**Persona impact.** *CXO:* one extra figure in the Salary Workings total, no per-person view. *HR Manager:* two new columns and a reason sentence per day. *Employee:* one new row on Your Day, only if they earn marks, and only once the table has rows. *Line manager:* nothing, by design.

## 10. What I am treating as the requirement contract (your point 9)

- **Requirement source:** `01-product-brief.md` (approved, Surbhi, 24 Nov 2026) plus the coordinator's message of 24 Nov, which settles the three bands, the "by means at or before" rule, the open-ended 03:00 band, the night green for everyone at shift end + 60 per person, stacking, and Contract off.
- **U1 (the counsel document is not signed):** not resolved by me. **No figure from that document enters the code in this slice.** The band numbers are Surbhi's. It matters for 092 and 093, not 091.
- **There is no `02-functional-spec.md`, no `01b-ux-design.md`, no `01c-security-privacy-requirements.md`, no `07-devops-inputs.md`** for 091 (the folder holds only the brief; checked with `ls`). My own working rule says "no spec, no code". So **the build needs one of two things from Surbhi:** (a) a short spec first, or (b) her written word that the brief is the spec. I will not start on an assumption.
- **Prototype parity.** The Your Day row is user-facing, so the approved prototype is the contract and any difference needs her yes first. There is no prototype. **I propose the engine, rule set, validation and both reports are built first** (no screen the brief's WOW depends on), **and the card row waits for the UX designer's prototype and her approval.** The brief's WOW text is wording, not a design.

## 11. Decisions that need Surbhi

| # | Decision | My recommendation |
|---|---|---|
| D1 | **Q11:** blank the green field (morning green for all as well, and dated grants stop counting), or keep morning nominated | **C**: a tick "Night green for everyone", about 8 lines. If she wants the morning green for everyone too, blank the field |
| D2 | A spec: write a short one, or confirm in words that the brief is the spec | Her choice; I will not guess |
| D3 | The card row: wait for a UX prototype, or ship the engine and reports first and the card after | Engine and reports first; card after the design gate |
| D4 | Salary slip: the engine, when switched on, will not carry overtime onto a slip (only report Gross and Net). Accept for now since DTC pays from the report, or add a "Overtime" salary component and one line to `ENGINE_LINES` at switch-on | Accept now; **a hard condition on the switch-on decision** |
| D5 | CLOSED: milestone passed, at or after (see the top). 01:01 pays 2 quarters | |

**Decisions I am making inside the strategy, which she can overrule:** overtime reuses `earns_marks` (no new tick); no stored field on Attendance. Both remove work from the brief's rung.

## 12. Strategy: the smallest change that meets the requirement

**Rung:** 4 (new engine code) plus one small rung 5 (a child table on the rule set). Rungs 1 to 3 rejected: Frappe's own Overtime Slip pays hours at a rate, not quarters by last punch (brief section 3a); no rule set setting holds a table; the flat `incentive` slot is a rupee amount, not scaled per person.

**Files touched (7 production, 1 new DocType folder, 1 or 2 test files):**

| # | File | Change |
|---|---|---|
| 1 | `alvoraa_portal/alvoraa_portal/payroll_rules.py` | `overtime_quarters` on `DayVerdict`; `OVERTIME_AFTER_SHIFT_MINUTES = 60`; `overtime_quarters_for(...)`; new `overtime_bands` argument to `evaluate_day`; the typed-time flag; reason line |
| 2 | `alvoraa_portal/alvoraa_portal/payroll_month.py` | `overtime_quarters`, `overtime_earning`, gross |
| 3 | `.../doctype/alvoraa_overtime_band/` (new: JSON, `__init__.py`, `.py`) | The child table |
| 4 | `.../doctype/alvoraa_payroll_rule_set/` (`.json`, `.py`) | `overtime_bands` field; `_check_overtime_bands`; if D1 is C, one Check field |
| 5 | `alvoraa_portal/alvoraa_portal/payroll_rules_apply.py` | `prepare()` builds the band list; `judge()` passes it; one line for D1 |
| 6 | The two report files | Columns and one message sentence |
| 7 | `alvoraa_portal/alvoraa_portal/day_marks.py` | The `earns_marks` fix in `_green` (now); the overtime payload (after the design gate) |
| 8 | `public/js/ess/portal.js` | The card row (after the design gate) |

**Not touched:** `payroll_slip.py`, `payroll_reprocess.py`, `payroll_fields.py`, `hooks.py`, `patches.txt`, any Custom Field, `apps/frappe`, `apps/erpnext`, `apps/hrms`, `alvoraa_goals`, the 088 folder. **Callers of `evaluate_day`:** 1 production call (`payroll_rules_apply.py:518`, which passes `**flags`) and 5 test files; the new argument has a default, so none breaks. **Callers of `prepare`:** 12 call sites by grep (`leave_rules.py` 558 and 637, `payroll_slip.py` 105, `payroll_rules_apply.py` 354, 436, 580, 632, `payroll_reprocess.py` 116 and 201, `alv291_attendance_fix.py` 1162, and the two reports; the salary report line was truncated in my grep and is inferred). A key added to the returned dict changes none of them.

**Order:**
1. Pure engine and month sum, with tests (no database). Break-test each test.
2. Child DocType, rule set field, validation, `prepare` and `judge`. Needs a local migrate: **asks for approval first** (it is on the never-run-without-asking list).
3. D1 gate, `_green` card fix, with tests.
4. Both reports.
5. Card row, after the design gate and prototype approval.
6. DTC data (three rows, set on the first of a month, and the green gate) is a **dev-stage action** and waits for Surbhi's word; it is not part of the build.

## 13. Test plan

New file `alvoraa_portal/alvoraa_portal/tests/test_overtime_091.py`. Each test is broken on purpose (fix undone, that test must fail for its reason, fix restored) after a commit, and the report says so.

| Group | Cases |
|---|---|
| **The edges** (10:30-20:30 shift, minutes 630 and 1230) | 22:59, 23:00, 23:01, 00:59, 01:00, 01:01, 02:59, 03:00, 03:01, 04:00. Expected 0,1,1,1,2,2,2,4,4,4 quarters (22:59, 23:00, 23:01, 00:59, 01:00, 01:01, 02:59, 03:00, 03:01, 04:00; settled rule) |
| **Wall clock must fail** | 01:10 pays 2, not 0 (proves the shift-day clock) |
| **The gate** | shift end + 59 minutes gives 0 overtime and no night green; + 60 gives both |
| **A 22:00 shift** (the band has no width at the start) | Last punch 22:59 pays 0 (before gate 23:00); 23:00 pays 1 |
| **Night green and overtime stack** | One night past the gate gives one green and the quarters. Gross rises by green pay plus overtime pay |
| **Contract** | `earns_marks` off: no green, no overtime, even at 02:00 |
| **Permanent still earns** (default-ON trap) | A Permanent day past the gate earns |
| **Typed time pays nothing** | A one-punch and a three-punch day confirmed by HR at 01:30: 0 overtime |
| **No overtime on** | a held day, an absent day, an approved-leave day, a half-day-leave day |
| **Day that lost quarters and earned overtime** | Arrived 30 minutes late (quarter lost) and left 00:30: day = 0.75 + 0.50 = 1.25 days (arrived 60 minutes late); `total_quarters` unchanged by overtime |
| **Special day** | Overtime is never doubled |
| **A re-run of the same month** | Two runs of `month_summary` give identical overtime and gross; a reprocess apply twice changes nothing |
| **Net adds it once** | Gross up by exactly overtime quarters / 4 x daily rate; Net up by the same |
| **Seconds** | 23:00:59 pays band 1 |
| **Rule set save** | Overlapping or unordered edges refused; total above 4 refused; empty table allowed; a message that says what to fix |
| **Q11 / D1** | With the tick on: night green for everyone, morning still nominated. With it off: today's behaviour. Another rule set that names a field is unmoved |
| **Card defect** | A Contract person gets no green line even when the green gate is open |
| **Pins** | The existing midnight test (`test_midnight_punch_alv402.py`) and the slab, late-window and green tests stay green, so a bad merge that drops the overtime lines fails a test by name |
| **Reports** | Salary Workings: new columns present, figures match `month_summary`. Daily Workings: the overtime cell and the reason sentence |

Full suite run once at the end (one test run at a time, on `test_site`, not the shared bench with another session).

## 14. Parallel-work check

- **Incoming from `origin/dev` since the brief (5 commits, read by file name):** `215bac59`, `b894b518`, `8ae4127d` (slice 090 docs), `9c19e705` and `245369fb` (ALV-443, `people-trends.html` and `test_people_trends_090.py`). **None touches a payroll file.**
- **Local branches ahead of `dev` that touch my payroll files:** none, checked across all local branches with `git diff --name-only origin/dev...<branch>` on the seven payroll paths. Other developers' remote work: **not checked; asking Surbhi whether anyone else is in these files.**
- **Work board** `.claude/work-in-progress.md`: **does not exist** on this machine. No claim to read. On approval I will create it and add a row.
- **Hot files I will touch:** the rule set DocType JSON (claim it on the board; one slice at a time), and `portal.js` (last, minimal block). `hooks.py` and `patches.txt` are not touched.
- **Another session's work in progress in the main checkout:** not looked at; I work only in my own worktree and build the slice on its own branch from `origin/dev`.

## 15. Risks

| Risk | Answer |
|---|---|
| Card tells Contract staff about a green they cannot earn | Fixed in the slice (section 0) |
| Dated green grants silently stop counting if the field is blanked | Option C avoids it; count the grant rows on DTC read-only before choosing A |
| Engine switched on and slips used: overtime not on the slip | D4; a condition of switch-on |
| A table changed mid-month moves the whole month on the next run | Set it on the first of a month (brief) |
| Seconds and machine drift | Seconds dropped by the existing rule; drift not checked |
| Capture window closes before 05:00 on four shifts | Held, not paid; named in the brief; not re-measured |
| Hot file clash in `portal.js` and the rule set JSON | Last, minimal, claimed on the board |

## 16. Subtract pass

I read this proposal once more asking only "what can I delete and still meet the requirement?"

**Removed from the brief's plan:** the Custom Field on Attendance and everything that came with it (the `VERDICT_FIELDS` entry, the `write_verdict` entry, the reprocess preview edit, the two existing test updates, a deploy-order risk); the new "overtime paid" tick on the category table (and its default-ON migrate trap, its `prepare` dict entry, its validation and its second card rule); a separate stored "overtime paid" figure for the reprocess log.

**Removed from my own first draft:** a payroll-slip component (moved to D4 as a switch-on condition); a feature flag for the card; a `reprocess` change; a cache for the bands (they ride inside the cached rule set already).

**Kept, because the requirement fails without it:** the child table, the `DayVerdict` field, the month sum and the one money line, the two report columns, the shared lookup function (two real callers), the `earns_marks` card fix, and the typed-time guard.

**Not removed, and why:** the shared `overtime_quarters_for` function stays even though it is small, because without it the card and the engine would hold two copies of the gate and the edges, which the card file's own header says caused wrong answers before.

## 17. Not checked, listed plainly

DTC's live data (every figure from the coordinator); how many dated green grants DTC holds; the last-punch distribution; headcount per shift; whether Frappe fills a new Check column's default into existing rows on migrate (not needed now, since I avoid a new Check on the category row; it applies only if D1 is C, and then the default is off, so it does not matter); the salary report's `prepare` line (inferred); what the card shows between 00:00 and 05:00; machine clock drift; whether DTC really pays from the report rather than from slips.
