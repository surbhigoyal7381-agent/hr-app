---
slice: 091-dtc-overtime-bands
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-11-24
revised: 2026-11-24 (third version: decided by Surbhi, after counsel's answers were noted)
status: decided by Surbhi, 24 Nov 2026. Build the band table as specified. Ready for the UX scan and the spec
inputs: [Surbhi's answers Q1-Q3 of 24 Nov; counsel's two answers, relayed by Surbhi as a Google Doc on 24 Nov 2026 (noted in section 12); the coordinator's read-only measurements on dtc.alvoraa.co on 24 Nov 2026. 01a-ux-opportunities.md and 07-devops-inputs.md section 1 do not exist for this slice]
---

# 091 DTC overtime, paid by the time of the last punch, in quarters

**Risk tier: 1** (it changes pay). **Rung: 3 + 4 + one small 5.** One Custom Field on Attendance, one tick on the existing category table, new engine code, one child table on the rule set. Recommendation to Surbhi, who has decided. Every later gate is hers.

**The policy is DTC's, and Alvora configures it.** Surbhi's decision, 24 Nov 2026: Alvora puts the client's own policy into the system and does not own the client's policies. This slice makes DTC's overtime table operational. It is built as she specified it.

## Bottom line

1. **Build it, thin, and build it as data.** One table of bands on DTC's rule set, one new line in the day's verdict, two report columns, one line on the Your Day card.
2. **Surbhi's answers (24 Nov, the band table and green rule corrected the same day) govern:**
   - The first band starts **one hour after each person's own shift end** (an offset, not a clock time).
   - **Three bands**, in total quarters of a day. The steps are uneven on purpose (+1, +2, +4):

     | Last punch | Day is worth | Extra |
     |---|---|---|
     | by 23:00 | 1.25 days | 1 quarter |
     | by 01:00 | 1.50 days | 2 quarters |
     | by 03:00 | 2.00 days | 4 quarters |

   - **The cap of 4 quarters is reached at 03:00**, not at 01:00. A punch after 03:00 (03:30, 04:00) reads the 03:00 row and pays the same 2.00 days. That needs a written rule and a test (7, rule 1a). "By" means at or before: 23:00, 01:00 and 03:00 exactly each belong to their own row.
   - **The night green goes to every employee** after shift end + 60 minutes. Overtime **stacks** with it. This closes Q10.
   - Overtime is **off and not recorded for Contract staff**, because they do not stay late. That is one tick on a table that exists (7a).
3. **The night green already exists in code, so widening it is configuration, not new code** (section 7b). The same switch also decides the morning green, which she did not mention. That is a question for her (Q11).
4. **The pay engine is OFF at DTC (`enabled = 0`) and that is fine for this slice.** The Salary Workings report and the Your Day card already work with it off (section 8). Switching DTC's engine on is a separate decision.
5. **Frappe HR's own Overtime feature is not the answer** (section 3a).
6. **Stacking makes a late night cost more.** That is her decision. The read-only count puts rupees on it before switch-on (section 9).
7. **Two pieces split out** (sections 13 and 14): the night-work warning report is slice 092, and a women's night-scheduling check is slice 093. Neither is in 091.

## What I checked, and what I could not

- **Read (proven), in the worktree `counsel-reqs-nov24`, branch `docs/counsel-requirements-nov24`:** `payroll_rules.py` (`QUARTERS_PER_DAY` line 102, `DayVerdict` lines 293-316, `day_credit` lines 328-365, `evaluate_day` line 569); `payroll_month.py` (summariser docstring lines 139-143 and money lines 239-274); `alvoraa_payroll_rule_set.json` and `.py`; hrms `overtime_slip.py`, `overtime_type.json`, `shift_type.json`. The first draft of this brief also read `payroll_rules_apply.py`, `day_marks.py`, `shift_standard.py` and the two Workings reports (see git history, commit `2d768a9b`).
- **Branch:** the caller says the worktree is at `origin/dev` = `2d768a9b`. I had **no shell** and did not run the `dev...origin/dev` count myself. "Not built" claims are unproven for any later commit.
- **Slice id:** 091. Unmerged branches are **not checked**.
- **Taken from the coordinator, not re-checked by me:** every DTC production fact (rule set `enabled = 0`, grades, mark rates, shift windows, headcounts, and the section 13 and 14 figures).
- **Not checked:** headcount per shift for overtime purposes; how many nights a month anyone stays past 11 pm; how DTC pays staying-late today; whether `punch_fix` (slice 087) is on production.

## 1. Job to be done

**Persona: HR Manager** (pays people right), then **Employee** (frontline, on a phone).

> "As DTC's HR, when someone stays late and their last punch is after 11 pm, I want the quarters they earned worked out and explained from the punch, so I am not sorting 400 people's nights by eye in Excel."

> "As a frontline employee, when I am deciding whether to stay, I want to see what my last punch will be worth, in quarters of a day, so there is no surprise on pay day."

The **line manager** sees nothing new (deliberately, section 5). The **CXO** sees one extra total in the Workings report, nothing per person.

## 2. Current pain (a story, not a number)

No count of nights past 11 pm exists and I do not know how DTC pays them today. **Baseline unknown, measure first.** The story, from Surbhi, 24 Nov: DTC staff stay late; DTC wants that paid by a fixed table; the engine can only take quarters away. Its docstring says so: `DayVerdict.total_quarters` is "every quarter lost on the day" and `day_credit` ends `return 1.0 - self.total_quarters / QUARTERS_PER_DAY`, so a day can never be worth more than 1.0 (proven, `payroll_rules.py` lines 319-365). The table needs 1.25, 1.5 and 2.0. **So overtime cannot be paid by raising `day_credit`; it is paid through one new money line** (7, rule 6).

## 3. Competitors (whole products)

| Capability | Frappe HR standard | Keka | Zoho People | Us today | Label |
|---|---|---|---|---|---|
| Overtime exists | Overtime Type + Overtime Slip, per shift and employee | Overtime policies | Overtime policies | Nothing. Engine only deducts | Frappe: **seen** in repo. Keka, Zoho: **read** 24 Nov 2026, search snippets only |
| Unit | Hours x multiplier x hourly rate; weekend and holiday multipliers | Hours | Hours; regular, overtime, double-time | Quarters of a day | same |
| By clock time of last punch, in bands | No | **Not confirmed** | **Not confirmed** | This slice | I searched only these two. Darwinbox, CatalystOne, HiBob **not checked** |

**What we deliberately do NOT do that they all do:** hours tracking, multipliers, weekend and holiday ladders, an overtime request-and-approve form, comp-off conversion. DTC's frontline fills in no form and HR approves nothing nightly. Their rule is a table, so the product holds a table.

### 3a. Three ways

| Way | What | Verdict |
|---|---|---|
| **Conventional** | Switch on Frappe HR overtime: an Overtime Type per shift, `allow_overtime` on Shift Types, a monthly Overtime Slip per person | **Rejected.** It pays hours at a rate, not quarters by last punch. It pays through Additional Salary, but DTC's pay is worked in Excel from our Workings report (Surbhi, 26 Oct, from memory notes, not re-verified). A second pay path could pay one night twice. `overtime_slip.py` lines 348-371 multiply a duration by a rate and a multiplier |
| **Better (this slice)** | A bands table on the rule set; the engine adds quarters from the last punch; reports and the card read the same verdict | **Chosen.** Same shape as the slab table the engine already has |
| **Reimagined** | A continuous rule (a quarter per hour, capped), no table | Not proposed. She wrote a table, and a table lets DTC change a row, not code |

**Could we not build it at all?** The Daily Attendance Workings report already prints the last punch, so HR can apply the table by eye in Excel today. Rejected: that is the 400-people-by-30-nights hand work she is trying to end.

**Rung check.** Rung 1 rejected above. Rung 2: the rule set holds no "addition" setting, and the flat `incentive` slot (`payroll_month.py` line 272) would not scale with each person's salary, which is her requirement. Rung 3: a Custom Field for the result on Attendance. Rung 4: the engine must learn to add. Rung 5, a child table: six flat fields would meet today's table; I chose the table because the engine already reads a table this way (`slabs`, `mark_rates`) and she wants to tune the last row. **The cheapest rung, six flat fields, is the honest alternative if she prefers.** Nothing else is a new DocType, app, page, switch or job.

## 4. Kano class and demand

- **Overtime as a feature: Must-be** across the market (proxy: Frappe HR, Keka and Zoho ship it; I have no lost-deal note).
- **This mechanism (last-punch bands, in quarters): Must-be for DTC, Indifferent for the market** (proxy). Evidence: one customer, one request (Surbhi, 24 Nov 2026). I do not call that demand for the product.
- **What would change it:** a count of how many nights a month cross each edge. A handful means a spreadsheet job; hundreds means a pay-accuracy job. The cheapest way to find out is one read-only count on production punches (section 9).

## 5. Persona enhancements through the portal

I had no UX scan, so these are mine. The designer should challenge them.

| Persona | Idea | In this slice? | Why |
|---|---|---|---|
| Employee | One line on Your Day: what a last punch is worth tonight | **Yes** | Same pattern as the night-green line; no new screen |
| Frontline employee | Same card in Hindi, clock times not rules ("after 23:00", never "an hour past shift end") | **Yes** (words at the design gate) | Readable at 22:40 on a cheap phone |
| Line manager | "Who is on overtime tonight" | **No** | It lets a manager rank people by hours stayed |
| HR Manager | Overtime quarters and money in the Salary Workings report; a column in the Daily Workings report; the reason line per day | **Yes** | The proof path, section 8 |
| CXO | Total overtime days this month, company level | **Free** | A column already gets a total row |
| HR / CXO | Overtime in Attendance Insights | **Later** | Slice 090 is rewriting Insights; if built, aggregate by branch with a minimum count, never a per-person league table |
| Held-day releaser | Releasing a held day pays overtime | **No** (Q7) | An HR-typed time must not move money |

## 6. The WOW

**Your Day card, 22:40, a frontline employee on a 10:30 to 20:30 shift.** Under the leave-time line, one new row (words finished by the designer, English first):

> **Overtime tonight.** Last punch by 23:00: 1 quarter. By 01:00: 2 quarters (half a day). By 03:00 or later: 4 quarters (a full extra day). Counted when your day is judged.

After a 23:42 punch the row says: **"Your last punch was 23:42. Overtime counted: 1 quarter."** *(Corrected 26 Nov 2026, ALV-478: the brief said 2 quarters. 23:42 is 1 at 75%, because 75% of the way from 23:00 to 01:00 is 00:30. Surbhi.)* No countdown, no streak, no nudge. Nothing shows before this person's own shift end plus one hour (21:30 for a 20:30 shift), worked out per person. Someone on a 22:00 shift sees their first line only from 23:00. The designer decides how the uneven steps (+1, +2, +4) are shown; they must not be smoothed. **For Contract staff the row is not shown** (7a).

## 7. Thin slice

**Needed to validate now:** the bands table (three rows); the engine adds overtime quarters from the last real punch; one new money line in the month summary; the new field on Attendance; the Salary Workings and Daily Workings columns; the card row.

**Needed before it ships:** the open items in section 11; a save-time check that the table does not overlap and totals 4 quarters or fewer (the kind of check `slabs` has); the table set on the **first of a month**.

**Rules in the engine, written down so nobody guesses:**

1. Overtime reads **only the last real punch** (clock minutes, past midnight as 1440 and up; ALV-402 and `punch_minutes` already do this). Shift hours decide what is lost; the bands decide what is added.
1a. **The 3 am edge needs a rule, and it is this one:** a last punch after the last row's edge pays the last row's total (4 quarters, 2.00 days). It is not a fourth band. Tests at 02:59, 03:00, 03:01 and 04:00, and at the exact edges 23:00 and 01:00. **Capture limit, from the caller's figures:** check-out windows close at 05:00 on 42 of 46 shifts but earlier on four (03:59 on one, 04:29 on two, 04:59 on five variants). On the 03:59 shift a 04:00 punch is not captured and is held, so it pays nothing (section 8).
2. The table stores **total** quarters per band and the engine reads that column only. With an offset start, someone on a 22:00 shift cannot earn before 23:00, so their "by 23:00" band has no width. Adding per-band increments would leave them a quarter short. A last punch at 23:30 on a 22:00 shift reads the 23:00-01:00 row and pays 2 quarters.
2a. **Two clocks, on purpose.** The gate is a per-person offset (nothing before shift end + 60 minutes). The bands are absolute clock times (23:00, 01:00). So 90 minutes of staying pays differently: off an 18:30 shift a 20:00 punch earns 1 quarter; off a 22:00 shift a 23:30 punch earns 2. The offset exists so a fixed 21:30 edge never pays someone on a 10:00-22:00 shift for time before their shift ended (`_window_applies`, `payroll_rules.py` lines 481-502).
2b. **Stacks with the night green.** Both are paid. They are independent: the green is a flat mark at the grade's rate (Rs 200 senior, Rs 100 junior), the quarters scale with each person's own day. **Every employee earns the green** after shift end + 60 minutes (section 7b), so on a night past the gate everyone earns the green and the quarters, except Contract (7a, Q12).
3. **Never doubled on a special day.** The most anyone earns is one extra day. The late-window quarter is already never doubled (`payroll_rules.py` lines 32-37).
4. **None on a held, absent, on-leave or half-day-leave day.** None for a category whose "overtime paid" tick is off (Contract), and nothing stored for it.
5. **Counts once as a day worked.** `days_worked` and the 15-day gate still count the day as 1.
6. **Money goes through one new line, and `day_credit` stays capped at 1.0.** A 2.00-day verdict cannot ride on `day_credit`, which ends `1.0 - total_quarters / QUARTERS_PER_DAY` and can never exceed 1.0 (proven, `payroll_rules.py` line 365). The month summary adds one line: overtime quarters / 4 x `daily_rate` (`daily_rate` is set at `payroll_month.py` line 242), added to gross beside `green_earning` (line 254). No slip change, no incentive slot, and no reader of `day_credit` changes meaning. **This replaces the first draft's idea of letting `day_credit` exceed 1.0.**
7. Show it apart in the Workings report, and make sure Net adds it once, not twice.

### 7b. The night green goes to everyone: it is already built, so this is configuration (Surbhi, 24 Nov 2026)

Her words: "all employees are going to earn green mark after one hr of the shift ends."

**Proven, read this session:** `payroll_rules.py` line 111 sets `NIGHT_GREEN_LATE_MINUTES = 60`, and line 852 reads `if night_green_eligible and last_out >= shift_end + NIGHT_GREEN_LATE_MINUTES:` and adds one green. So the rule "one hour after shift end" is already the rule. What she changed is **who** earns it.

**Proven, read this session, `payroll_rules_apply.py` lines 302-305:** `night_green_eligible` is `(green in GREEN_NIGHT) if ctx["green_field"] else True`. When the rule set names **no** green eligibility field (its `green_eligibility_field`, read at line 188), every employee is eligible. So "everyone" is **a blank value on DTC's rule set**: rung 2, configuration, per rule set. No new code for the green. Cheaper than the first draft implied.

**Two consequences:**
- **Per company, as data. Never delete the gate in code.** The gate is read from each rule set, so blanking the field changes pay only for the tenant whose rule set it is. Removing `night_green_eligible` from `evaluate_day` would change pay at every tenant that uses a nominated list. **Not checked, and must be before the spec:** which rule sets use a green eligibility field today. The coordinator reports the engine is ON at ppj.dev; Grace's state is not checked. Read the field on each tenant's rule set, read-only, and confirm DTC's before and after.
- **The morning green moves with it.** Lines 302-303 apply the same blank-field rule to the morning green, so blanking the field also gives every employee a morning green (for coming in `MORNING_GREEN_EARLY_MINUTES` early, the constant used at line 848). **She spoke only of the night green.** The dated grants (`_green_on`, which `payroll_rules_apply.py` line 240 reads before the field) are another route to a green and need checking. See Q11.

The Your Day card reads the same constant (`day_marks.py` lines 36 and 350), so it follows the rule set with no change.

### 7a. Contract staff: overtime off, nothing recorded (Surbhi, 24 Nov 2026)

Her words: "the contract employees don't stay over time at all, so lets keep it off and ignore it for the contract employees." That is her decision. The earlier "record agency quarters but do not pay them" answer was reversed the same day, and the agency columns and reconciliation are dropped.

**What survives:** one tick on the existing `categories` child table of the rule set, **"overtime paid"**, off for the Contract row. It follows `earns_marks` and `earns_leave_credits`, both already off for Contract (coordinator's check below). For a category with the tick off the verdict's `overtime_quarters` is 0, nothing is stored, `day_credit` does not move.

**Two details the engineer must not trip on.**
- **The tick's default must be ON.** A new Check field defaults to 0, so on migrate the Permanent row would read "overtime off" and every permanent employee would earn nothing. The engine already treats an unlisted category as "marks on, leave on"; overtime follows that rule.
- **The card reads the same answer.** The engine answers who earns what for the card, so the card row is hidden for Contract staff by the same tick, never by a second rule.

**Out of scope, with the pile each cut landed in:**

| Cut | Pile |
|---|---|
| Per-night overtime approval | Not doing (Q8) |
| Attendance Insights and HR analytics figures | Later, after 090 |
| A payslip note line for overtime | Later (DTC works pay in Excel) |
| An eligibility flag for overtime | Not doing |
| Recording or reconciling agency overtime | Not doing |
| Hours, multipliers, comp-off, requests | Not doing |
| A ramp instead of bands | Not doing |
| Manager "who is on overtime" view | Not doing (surveillance) |
| Switching DTC's engine on | A separate decision |

## 8. Run-side reality, and what the engine being off means

No `07-devops-inputs.md` exists. **Inferred, not measured:** no new worker, job, page or storage. The engine already reads the last punch for every day it judges, so the new rule adds a table lookup, not a query. One-time cost: re-judging the month after the table is filled, using the existing `payroll_reprocess`, which must rewrite the new field.

**Engine off (`enabled = 0`):**
- The Salary Workings report loads a not-live rule set and says the figures are what they WOULD produce (proven in the first draft's read of `salary_components_and_workings.py`). Overtime can be proved on real DTC data without switching anything on.
- The Your Day card finds the rule set with no `enabled` filter (proven, `day_marks.py` lines 99-105), so it would show the table even with the engine off. **Fill the table only when DTC is ready to pay from it**; an empty table shows nothing anywhere, so presence of data is the switch and there is no new one.
- **Proof path:** (1) the read-only count; (2) fill the table on a copy; (3) run the Workings report for a closed month and compare 20 hand-picked nights (every band, plus 22:59/23:00/23:01 and 00:59/01:00/01:01) with DTC's own Excel; (4) fill the table on production at the start of a month.

**Capture windows, a real dependency.** Last-punch pay needs the punch captured. Per the caller, check-out windows close at 05:00 next day on 42 of 46 shifts and earlier on four. **Inferred:** `shift_standard.py` lines 101-102 set a standard of 240 minutes both sides, so running that tool against DTC would flag or reset the wider windows. A punch after the window falls on the next calendar day and holds both days (the ALV-402 failure). Held is safe, but that night's overtime is lost until someone fixes it. **Not checked:** how many people hold two shift assignments on one day. Add it to the read-only count.

## 9. Success criteria

| Measure | Baseline | Target | How measured |
|---|---|---|---|
| Accuracy (lagging): 20 hand-picked nights match DTC's own sums | Unknown | 20 of 20, every edge minute included | HR compares the Workings report with Excel on a copy before switch-on |
| Lost to capture (leading): share of nights with a last punch after the first band that end held or with no shift matched | Unknown, measure first | Surbhi sets it after the count; my proposal 2% or lower | Read-only query before, the same query a month after |
| Explained (quality): overtime questions HR cannot answer from the day's reason line | Unknown | 0 in the first pay month | HR logs queries |
| Cost (business): rupees a month the table adds, with the green stacked | Unknown | Surbhi accepts the figure before switch-on | Workings report on a closed month, engine off |

No AI is involved. The rule is deterministic and a person owns every number. Nothing here proposes or sets a rating.

## 10. Risks, red-teamed

| Risk | What breaks | Cheapest check or answer |
|---|---|---|
| **Stacking is larger money, and the green is now for all staff** | A senior who leaves at 01:10 earns a Rs 200 green plus 4 quarters (a full extra day), and so does every other person on that night at their own rates. The wider green is her decision | Show the rupee cost per night from the count before switch-on |
| **Blanking the green field changes pay somewhere else** | If the field is cleared on the wrong rule set, or the gate is removed in code, another tenant's pay moves, and so does the morning green | Per rule set, as data (7b). Read every tenant's rule set before the spec (V1). Test: DTC's rule set with the field blank awards both greens, a rule set with the field set still does not |
| **Bands are clock times** | The same 90 minutes pays 1 quarter off an 18:30 shift and 2 off a 22:00 shift | Written down in 7, rule 2a |
| **A Contract person does stay late** | They earn nothing and nothing is recorded | Her decision. Cheap to reverse: turn the tick on, and `payroll_reprocess` re-judges the nights |
| **Tick defaults to off on migrate** | Permanent staff would silently earn no overtime | Default ON; Contract off as data; a test that a Permanent day still earns |
| **One punch is money** | A person lingers and punches at 11:05 for a quarter | Punches are inside the geofence (ALV-338, memory notes, not re-verified); HR sees the reason line |
| **Uneven cliffs** | The steps are +1, +2, +4. A punch at 01:01 pays 4 where 01:00 pays 2, and the 01:00 to 03:00 jump is twice the 23:00 to 01:00 jump. It is her table and it is kept visible, not smoothed | The card shows clock times and the three rows |
| **Machine clock drift** | A machine 3 minutes slow turns 23:01 into 22:58 | **Not checked.** The engine drops seconds |
| **Table changed mid-month** | Reprocess rewrites the whole month | Set it on the first of a month |
| **The new money line is counted twice** | Net adds it to gross and it is also in another total | A test that gross rises by exactly the overtime figure. `day_credit` is untouched, so no reader of it changes. The engineer still lists the readers of `total_quarters` at impact analysis. **Not done here** |
| **Shift windows reset** | Running `shift_standard` against DTC shrinks capture | Section 8 |
| **Grade blank (2 people)** | No mark-rate row, so greens and reds are Rs 0, but quarters use salary and still pay | Worth telling DTC; not this slice's fix |

**Illustrative money, not DTC data. `[ASSUMPTION]` salaries.** Basic Rs 30,000 over a 30-day month is Rs 1,000 a day, so a quarter is Rs 250. A 01:10 punch adds 2 quarters: the day pays 1.5, Rs 1,500. *(Was "23:42", corrected 26 Nov 2026, ALV-478: 23:42 is 1 quarter.)* At Rs 15,000 Basic a quarter is Rs 125. Same table, each person's own day.

## Thriving-workplace lens

| Lens | Answer |
|---|---|
| Engagement | Recognition for real extra effort, stated in advance. A person can see what a night is worth |
| Collaboration | No effect |
| Inclusiveness | The clock is the same for every shift: a day-shift worker leaving at 22:50 and an evening-shift worker leaving at 22:50 earn the same. Say that to her. With the green for everyone, two people on one floor on one night are paid by the same rule (Surbhi, Q10, closed). Contract staff are left out by her decision, because they do not stay late. The rule is gender-blind and stays so |
| Transparency | Employees see the table before they decide. Managers see no one's overtime hours. HR sees pay data it already sees. Later analytics: aggregate with a minimum count |

## 11. Open questions

**Answered by Surbhi, 24 Nov 2026:**

| # | Answer | Effect |
|---|---|---|
| Q1 | First band starts at **shift end + 60 minutes, per person** | Section 7, rules 2 and 2a |
| Q2 | **Stack** with the night green | Rule 2b |
| Q3 (final) | **Everyone except Contract staff.** Off and not recorded for Contract | Section 7a |
| Policy | **The band table is the design.** Alvora configures the client's policy | The whole slice |
| Q10 (closed) | **Every employee earns the night green** after shift end + 60 minutes. The same-night unfairness no longer exists | Section 7b |
| Table | **Three bands:** by 23:00 = 1 quarter, by 01:00 = 2, by 03:00 = 4; a later punch reads the 03:00 row. "By" means at or before | Section 7, rule 1a |

**Must know (blocks the spec):**

| # | Question | Recommended assumption | Owner / blocks |
|---|---|---|---|
| Q11 | Blanking the green field also gives **every employee the morning green**. Does she want that? | **Ask first.** If the morning green must stay nominated, the night and morning gates need separating, which is a small code change (rung 4), not configuration | Surbhi / blocks 7b's "configuration only" |
| Q12 | A Contract person who does stay late: do they earn the green? The green is for all employees, overtime is off for Contract | **No green for Contract, no change to their rules.** `earns_marks` is 0 for Contract (coordinator's check), and a green is a mark, so on the engine as it stands a Contract person earns none even when the green is open to all. **Inferred; the engineer checks that `earns_marks` really stops the green before the spec.** "All employees" most likely meant the people who earn marks. If she wants Contract to earn it, that is a change to a tick she already set | Surbhi / the spec |
| V1 | Which tenants' rule sets use a green eligibility field today (ppj.dev is ON; Grace not checked) | Read-only check of each rule set before the spec | Coordinator / blocks the spec |

**Should know (improve the design):**

| # | Question | Default I will use |
|---|---|---|
| Q4 | A punch at exactly 23:00, 01:00 or 03:00: which band? | "By" means at or before: 23:00 is band 1, 01:00 is band 2, 03:00 is band 3 |
| Q5 | Late arrival and late stay on one day: separate, or overtime only on a day that lost no quarters? | Separate. The reason line lists both. Net is the sum |
| Q6 | Overtime on a special day | Never doubled |
| Q7 | A held day released by an HR-typed time: pays overtime? | **No.** To earn it HR adds the real punch through slice 087's route. Production state of 087 **not checked** |
| Q8 | Any nightly approval? | None. HR reads the report before Excel |
| U1 | **The counsel document (section 12) is not on letterhead and may be a typed summary.** Is there a signed reply? | Surbhi asks counsel for one. Any figure from it that becomes a rule in code, such as the 10, 10.5 and 50 hours in section 13, should come from the signed words |

**Evidence required before the spec, read-only on production:** (a) a count of last-punch times for Oct and Nov, by band edge and by the 05:00 capture limit; (b) headcount per shift; (c) the number of people with two shift assignments on one day; (d) how DTC pays this today.

## 12. Counsel's answers 5 and 6, noted

**Noted and decided by Surbhi on 24 Nov 2026. This is the audit record and nothing more.** Source: a Google Doc relayed by Surbhi on 24 Nov 2026, not on letterhead (see U1). The numbering "5 and 6" is the coordinator's; the doc as relayed to me did not carry numbers.

- **On the pay scheme:** DTC's retail stores are governed by the Delhi and Punjab/Haryana Shops and Establishments Acts, not the Factories Act. Counsel said paying a fixed share of a day's wage by punch-out band does not satisfy statutory overtime and will underpay workers on earlier shifts, and that the requirement is 2 times hourly wages for actual overtime beyond 9 hours a day or 48 hours a week, with the late-night band on top or whichever is higher.
- **On night work:** counsel said night work in Delhi, Chandigarh and Ambala is permitted only if daily and quarterly overtime caps (10 hours a day and 50 hours a quarter in Chandigarh/Ambala; 10.5 hours spread-over in Delhi), rest intervals and weekly shift rotation are enforced; and, for women past 20:00 or 21:00, scheduling is blocked unless HR logs prior written consent and safe door-to-door transport.
- **Decision (Surbhi, 24 Nov 2026):** Alvora configures what the client's policy says and is not liable for the client's policies. Slice 091 builds the band table as specified.

## 13. Slice 092: a warning report we sell to the client (scope, not built here)

**Reframed on 24 Nov 2026:** 092 is a report that shows a client their own position in their own data. It is a product we sell, not an obligation of ours. It is **warning-only first**, reads punches and shifts that already exist, and writes nothing to pay. It needs its own brief, UX scan and counsel's wording for any limit it uses.

**Evidence for it, measured read-only on `dtc.alvoraa.co` by the coordinator on 24 Nov 2026. Proven by the coordinator; I used the figures as given and did not re-derive them.**

| Finding | Figure |
|---|---|
| Standard roster, every branch | 10:30-20:30: a 10-hour span, **9h20 of work** after DTC's own 40-minute break allowance (`break_allowance_minutes = 40` on the rule set) |
| Staff on that roster | **443 of the 623 staff with a shift set**: Delhi 122, CHD-22 87, Noida 78, Ambala 56, PPR 52, CHD-34 48. 495 active employees |
| Shift Type records over 9 hours net of the break | **24 of 46** |
| Days over 9 hours, Present or Half Day | Sep 2026: 1,158 of 1,954 (59.3%). Oct: 8,501 of 9,477 (89.7%). Nov to the 23rd: 5,576 of 7,384 (75.5%) |
| Caution on October | Inflated by the deliberate regularisation (2,007 hand-made check-ins, 1,315 Administrator edits), so its in and out times are partly reconstructed. **November is the clean month** |
| Work past 20:00 | Nov: 1,904 days by 158 women. Oct: 3,095 days by 153 women |
| Attendance data starts | **20 Sep 2026** (29,605 rows to 23 Nov), so there is no history before that |

**What the report would list, for the client's own reading:** days over a chosen daily line; people near a weekly line; days with a short gap before the next punch (rest); work past 20:00 and past 21:00 by women, set against a consent-on-file column (093). Aggregates by branch where a person is not needed. A person-level list goes to HR only, never to a line manager.

**Rung:** a Report on existing data, no new DocType. The weekly view and the quarterly cap need a pass over several days; that is new report code, not engine code, because the report does not move pay. Quarterly cap and weekly rotation: **not checked** against any DTC data.

## 14. Slice 093: the women's night-scheduling check, and a fact that changes its shape

**Proven by the coordinator on `dtc.alvoraa.co`, 24 Nov 2026:** `tabShift Assignment` has **0 rows**. The columns exist and the table is simply unused. Shifts come from `Employee.default_shift`, which is set for 623 of 625 employees.

**What that means, plainly: there is no scheduling event to intercept.** A check that blocks "the schedule" unless consent and transport are logged, as 093 was first described, has nothing to hook into at DTC. Nobody assigns a night shift; a person's standard shift is set on the Employee record and every day follows from it.

**What would have to change instead (options for 093's own brief, not decided):**

| Option | What it is | Cost |
|---|---|---|
| A. Report only | The 092 report with a "consent on file" and "transport on file" column against women's late work, and Custom Fields on Employee to hold them | Cheapest. Blocks nothing |
| B. Check on the Employee record | A check when `default_shift` is saved on an Employee whose shift ends after the line | A hook on a shared doctype. It only fires when someone changes a shift, so it misses the 443 already on the 20:30 roster |
| C. Start using Shift Assignment | Move DTC's shifts onto Shift Assignment so there is something to check | A change to how DTC is set up and to how the engine finds a shift. **Not checked what else reads `default_shift`** |

**Also needed before 093 is designed:** counsel's wording for "safe transport with security" (what must be recorded), the line (20:00 or 21:00, which state), and the data footing for the consent and transport records (a sensitive record with its own DPDP basis; the security engineer reads it first). The 1,904 November days by 158 women past 20:00 are what an option A report would list on day one.

## Subtract pass

**Removed on the third revision (green and bands):** the open-ended "01:00 or later" band and the claim that the 3 am edge needs no rule; the same-night fairness risk row and the eligibility-flag question (Q10), closed by Surbhi; and the earlier "the money is automatic through `day_credit`" claim, replaced by one new money line. **Added only:** the 03:00 row, the one rule for punches after it, the green-for-all note (configuration), Q11, Q12 and V1.

**Removed on the second revision:** the statutory floor (2 times hourly, the 9-hour and 48-hour lines); the weekly pass and its month-end cases; the validate-refuses-a-more-lenient-value rule; the override-acknowledgment modal, the override log and the "Client Custom Band" tag; the admin IP log; the on-top-or-higher choice; the statutory money line (the one new money line is back in the third revision, for the band); the compliance box with warnings, replaced by section 12's one-paragraph record; and from 091's own scope the 9-hour ordinary-shift point and the women-past-20:00 point, which moved to 092 as evidence.

**Removed in earlier passes and still removed:** a nightly approval step; an Insights chart; a payslip note; a new eligibility field; comp-off; a manager "who is on overtime" view; a ramp alternative; overtime on half-leave days; a version-by-date column; a "default" band row; any per-shift override; the whole agency recording scope and the separate `overtime_paid` yes/no. **Kept, because the requirement fails without it:** the table, the verdict field, the two report columns, the card row, and one "overtime paid" tick on the category table, off for Contract.

## Assumptions

- `[ASSUMPTION]` DTC pays from the Salary Workings report into Excel, not by posting salary slips (memory note of 26 Oct; not re-verified).
- `[ASSUMPTION]` Production check-out windows are as the caller read them.
- `[ASSUMPTION]` The latest DTC shift ends 10 PM (a docstring in `payroll_rules.py`, which may be stale). The coordinator's roster figures in section 13 show the standard roster ends 20:30.
- `[ASSUMPTION]` Illustrative salaries in section 10 are not DTC's.
- `[ASSUMPTION]` Q4-Q8 defaults stand until she says otherwise.
- `[ASSUMPTION]` Contract staff really do not stay late (Surbhi; not measured). Nothing is recorded for them, so our data cannot check it later.
- `[ASSUMPTION]` The table can hold a time past midnight. A plain Time field cannot say "01:00 next day"; the spec writer must pick a shape (minutes after the shift-day midnight, or a next-day tick).

## Kill criteria

Stop and tell Surbhi, and do not build or do not switch on the late-night pay scheme, if:

- the read-only count shows fewer than a handful of qualifying nights a month (it becomes a spreadsheet task);
- the cost per night, with the green now paid to everyone and stacked on top, is more than she expects once shown in rupees;
- the rule-set read (V1) shows the green gate cannot be changed for DTC without moving another tenant's pay;
- the capture windows cannot safely reach the hours the bands need;
- Surbhi withdraws or changes the policy that the table expresses.

## Coordinator's verification, 24 Nov 2026

Read read-only on `dtc.alvoraa.co` (container `compose-backend-1`) the same day. **Contract is identified by `employment_type`, and has a real row in the rule set's `categories` table**, which the "overtime paid" tick hangs on. The table holds exactly two rows:

| category | grace_minutes | earns_marks | earns_leave_credits | doubles_deduction |
|---|---|---|---|---|
| Contract | 15 | 0 | 0 | 0 |
| Permanent | 0 | 1 | 1 | 1 |

**Mark rates confirmed:** Junior Rs 100, Senior Rs 200, "No leaves" Rs 0, External Rs 0. Grades on active staff: Junior 476, Senior 16, External 1, and **2 with a blank grade and so no rate row**.

**Still not checked:** the last-punch distribution for October and November by band edge; headcount per shift; people holding two shift assignments on one day; how DTC pays late stays today.

## Handoff note

To the UX designer and the analyst. Q1-Q3, Q10, the band table and the policy are decided (section 11); Q11, Q12 and V1 are open. Do not add a manager view. Do not remove the green gate in code (7b); it is a blank value on DTC's rule set. The overtime gate is a per-person offset and the bands are clock times; keep both in the spec and the card, and test a 22:00 shift, where the first band has no width. The engine reads the "total overtime" column only. Contract: the category tick is off, so the engine earns and stores no overtime; test that a Contract day carries 0 and a Permanent day still earns (default ON). There is no agency column, no recorded-but-unpaid figure, no `overtime_paid` yes/no, no statutory computation, no override modal; do not add them. Write the card row in Hindi and English with clock times only. Money goes through one new line and `day_credit` stays at or under 1.0 (7, rule 6). Test the 3 am rule (1a): 02:59, 03:00, 03:01, 04:00. Check that `payroll_reprocess` rewrites the new field. Slice 090 is still moving; do not touch Insights. Slices 092 and 093 are separate briefs. If you disagree with anything here, say so in your own handoff and stop, rather than building something different.
