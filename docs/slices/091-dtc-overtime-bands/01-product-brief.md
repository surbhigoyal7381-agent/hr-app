---
slice: 091-dtc-overtime-bands
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-11-24
status: draft
inputs: [none. 01a-ux-opportunities.md and 07-devops-inputs.md section 1 do not exist for this slice. The brief was commissioned directly, from the engine source and Surbhi's own words]
---

# 091 DTC overtime, paid by the time of the last punch, in quarters

**Risk tier: 1** (it changes pay). **Rung: 3 + 4 + one small 5.** One Custom Field on Attendance, one tick on the existing category table, new engine code, and one child table on the rule set. Recommendation only. Every gate is Surbhi's.

## Bottom line

1. **Build it, thin, and build it as data.** One table of bands on DTC's rule set, one new line in the day's verdict, two report columns, one line on the Your Day card. Nothing else.
2. **Surbhi answered Q1-Q3 on 24 Nov (updated the same day, twice).** (a) The first band starts **one hour after each person's own shift end** (an offset, not a clock time). (b) Overtime **stacks** with the night green; both are paid. (c) Overtime applies to **everyone except Contract staff**. Her first answer on (c) was "record Contract staff's quarters but do not pay them"; she then **reversed it**: Contract staff do not stay late, so overtime is **off and not recorded** for them. That is one tick on a table that exists (7a). **Bad news, in bold: stacking makes the total paid for a late night larger, so the statutory-minimum question in the compliance box is more pressing, not less. She has not yet consulted counsel on this.** Open items are in section 11.
3. **The 3 am edge needs no new rule.** The table caps at 4 quarters, so "1:00 am or later" is one open-ended band. 3:30 and 4:00 pay the same as 2:59. This answers her point 3 fully.
4. **The pay engine is OFF at DTC (`enabled = 0`) and that is fine for this slice.** Both the Salary Workings report and the Your Day card already work with it off (section 8). Switching DTC's engine on is a separate decision and this slice must not depend on it.
5. **Frappe HR's own Overtime feature is not the answer.** Section 3a says why.

## What I checked, and what I could not

- **Read (proven):** `payroll_rules.py` (whole), `payroll_rules_apply.py` (whole), `payroll_month.py` lines 1-277, `day_marks.py` (whole), `shift_standard.py` lines 1-50, the Salary Workings and Daily Workings reports (the parts named below), `payroll_slip.py` function list, `hrms/hr/doctype/overtime_type` and `overtime_slip` controllers, slice 090's impact analysis (first 62 lines), slice 085's brief (first 40 lines).
- **Branch:** the worktree's branch `fix/leave-card-date-bomb` is at `80dc5cbf`; `origin/dev` is `14a9d115`. I had no shell; the coordinator then checked and reports the branch is **0 ahead and 1 behind** `origin/dev` (not run by me). One commit I have not read may touch files I cite, so treat any "not built" below as unproven for that one commit.
- **Slice id:** highest id in this worktree is 089. The main checkout also holds an untracked `090-attendance-insights-correctness`. I took **091**. Unmerged branches are **not checked**, so another session could have claimed 091.
- **Taken from the caller, not re-checked by me:** every DTC production fact (rule set `enabled = 0`, grades, mark rates, shift windows 420-600 minutes, headcount per grade).
- **Not checked:** headcount per shift (the caller's query returned 0 for every shift; I treat it as unknown); how many nights a month anyone stays past 11 pm; how DTC pays staying-late today; whether `punch_fix` (slice 087) is on production.

## 1. Job to be done

**Persona: HR Manager** (pays people right), then **Employee** (frontline, on a phone).

> "As DTC's HR, when someone stays late and their last punch is after 11 pm, I want the quarters they earned worked out and explained from the punch, so I am not sorting 400 people's nights by eye in Excel."

> "As a frontline employee, when I am deciding whether to stay, I want to see what my last punch will be worth, in quarters of a day, so there is no surprise on pay day."

What changes for the others: the **line manager** sees nothing new (deliberately, section 5). The **CXO** sees one extra total in the Workings report, nothing per person.

## 2. Current pain (a story, not a number)

I have **no count** of nights past 11 pm and no record of how DTC pays them today. **Baseline unknown, measure first.** The story, from Surbhi, 24 Nov: DTC staff stay late; DTC wants that paid by a fixed table; the engine can only take quarters away. Its own docstring says so: `DayVerdict.total_quarters` is "every quarter lost on the day" and `day_credit` ends `return 1.0 - self.total_quarters / QUARTERS_PER_DAY`, so a day can never be worth more than 1.0 (proven, `payroll_rules.py` lines 319-365). The table needs 1.25, 1.5 and 2.0.

## 3. Competitors (whole products)

| Capability | Frappe HR standard | Keka | Zoho People | Us today | Label |
|---|---|---|---|---|---|
| Overtime exists | Overtime Type + Overtime Slip, per shift and employee | Overtime policies (Time and Attendance) | Overtime policies (Attendance and Timesheet) | Nothing. Engine only deducts | Frappe: **seen** in repo. Keka, Zoho: **read** 24 Nov 2026 (help.keka.com, help.zoho.com search results, snippets only) |
| Unit | Hours x multiplier x hourly rate; weekend and holiday multipliers; max hours cap | Hours, gross or effective; min hours to qualify | Hours; regular, overtime, double-time | Quarters of a day | same |
| Paid how | Additional Salary from a monthly Overtime Slip | Pay codes (needs their payroll module); or comp-off | Pay rate per policy | Paid days x daily rate | same |
| Approval | Slip per employee per month | Approval chain | Alerts; scheduler to auto-submit (on request to support) | None proposed | same |
| By clock time of last punch, in bands | No | **Not confirmed**: I found no slab or tier page | **Not confirmed**: one community thread titled "tiered overtime", I saw the title only | This slice | I searched only these two. I did **not** check Darwinbox, CatalystOne or HiBob. `[recall - verify]` |

**What we will deliberately NOT do that they all do:** hours tracking, multipliers, weekend and holiday ladders, an overtime request-and-approve form, comp-off conversion. For DTC's frontline that means no form to fill and no nightly approval for HR. The employee sees one line; HR reads one column. That is better for them because their rule is a table, not a policy.

### 3a. Three ways

| Way | What | Verdict |
|---|---|---|
| **Conventional** | Switch on Frappe HR overtime: an Overtime Type per shift, `allow_overtime` on 46 Shift Types, a monthly Overtime Slip per person | **Rejected.** It pays hours at an hourly rate, not quarters by last punch. It pays through Additional Salary and Salary Slip, but DTC's pay is worked in Excel from our Workings report (Surbhi's 26 Oct decision, from memory notes, not re-verified today). It would be a second pay path beside the rule engine and could pay one late night twice. `hrms/.../overtime_slip.py` lines 195-216, 339-372 |
| **Better (proposed)** | A bands table on the rule set; the engine adds quarters from the last punch; reports and the card read the same verdict | **Proposed.** Same shape as the slab table the engine already has, and money flows with no new pay code (section 7) |
| **Reimagined** | A continuous rule (a quarter per hour, capped) with no table | **Not proposed.** She wrote a table and her third band is exactly where she wants room. A table lets DTC change a row, not code |

**Could we not build it at all?** Yes, one smaller move exists. The Daily Attendance Workings report already prints the last punch ("in, out, minutes", its own docstring), so HR can apply the table by eye in Excel today. I reject it: that is the 400-people-by-30-nights hand work she is trying to end, and the table lives only in a head. A middle cut (reports only, no verdict field) is possible, but the verdict field is the cheap part and keeps reprocess and every report agreeing.

**Rung check.** Rung 1 (Frappe overtime): rejected above. Rung 2 (configuration): the rule set holds no "addition" setting; the `incentive` slot (`payroll_month.py` line 272) is a flat rupee figure nothing feeds, and it would not scale with salary, so it fails her "a quarter of THAT person's day" requirement. Rung 3 (Custom Field): needed, for the result on Attendance. Rung 4: the engine must learn to add. Rung 5, a child table: three flat pairs of fields would meet today's table; I recommend the table because she is already asking to tune the last row and the engine already reads a table the same way (`slabs`, `mark_rates`). **If Surbhi wants the cheapest rung, six flat fields is the honest alternative.** Nothing else here is a new DocType, app, page, switch or job.

## 4. Kano class and demand

- **Overtime as a feature: Must-be** across the market (proxy). Frappe HR, Keka and Zoho all ship it (above). Absence is a lost-deal reason for buyers with shifts, but I have no lost-deal note, so this is a proxy.
- **This mechanism (last-punch bands, in quarters): Must-be for DTC, Indifferent for the market** (proxy). Demand evidence: **one customer, one request** (Surbhi, 24 Nov 2026). I will not call that demand for the product.
- **What would change it:** a count of how many nights a month cross each edge. If it is a handful, this is a spreadsheet job. If it is hundreds, it is a pay-accuracy job. **Cheapest way to find out before building:** one read-only count on production punches (section 9).

## 5. Persona enhancements through the portal

I had no UX scan, so these are mine, not the designer's. The designer should challenge them at the design gate.

| Persona | Idea | Job | In this slice? | Why |
|---|---|---|---|---|
| Employee | One line on Your Day: what a last punch is worth tonight | "Should I stay?" | **Yes** | Same pattern as the night-green line (`day_marks._green`); no new screen |
| Frontline employee | Same card, in Hindi, clock times not rules ("after 23:00", never "an hour past shift end") | Readable at 22:40 on a cheap phone | **Yes** (words at the design gate) | `day_marks.py` docstring already sets this rule |
| Line manager | "Who is on overtime tonight" | Plan the floor | **No** | It lets a manager rank people by hours stayed. That is the surveillance line in our own rules |
| HR Manager | Overtime quarters and money in the Salary Workings report; a column in the Daily Workings report; the reason line on each day | Check before Excel; answer "why is my overtime X" | **Yes** | The proof path, section 8 |
| CXO | Total overtime days this month, company level | One number | **Free** | A column already gets a total row; no new chart |
| HR / CXO | Overtime in Attendance Insights or HR analytics | Trend | **Later** | Slice 090 is rewriting Insights' denominators and says "draw no new chart"; adding a figure now collides. If built later: aggregate by branch, minimum-n suppression, never a per-person league table |
| Held-day releaser | Releasing a held day pays overtime | Fair pay | **No** (section 11, Q7) | An HR-typed time must not move money |

## 6. The WOW

**Your Day card, 22:40, a frontline employee on a 10:30 to 20:30 shift.** Under the leave-time line, one new row (words to be finished by the designer, English first):

> **Overtime tonight.** Last punch from 21:30: 1 quarter. After 23:00: 2 quarters (half a day). After 01:00: 4 quarters (a full extra day). Counted when your day is judged.

After they have punched out at 23:42, the same row says: **"Your last punch was 23:42. Overtime counted: 2 quarters."** No countdown, no streak, no nudge. It states the table and nothing more. The `21:30` is this person's shift end (20:30) plus one hour, Surbhi's answer to Q1, worked out per person. Someone on a 22:00 shift sees "from 23:00" as their first line, and no "21:30" row at all.

**For Contract staff the row is not shown.** They earn no overtime (section 7a).

## 7. Thin slice

**Needed to validate now:** the bands table; the engine adds overtime quarters from the last real punch; `day_credit` gains `overtime_quarters / 4`; the new field on Attendance; the Salary Workings and Daily Workings columns; the card row.

**Needed before it ships:** the open items in section 11 (Q4-Q10; Q1-Q3 are answered); a rule that the table must be non-overlapping with a total of 4 or fewer quarters (the same kind of save-time check `slabs` has); setting the table on the **first of a month**; the compliance read (below).

**Rules in the engine, written down so nobody guesses:**

1. Overtime reads **only the last real punch** (clock minutes, past midnight as 1440 and up; ALV-402 and `punch_minutes` already do this). It never reads the minutes the deduction reads: shift hours decide what is lost, the bands decide what is added.
2. The table stores **total** quarters per band, and the engine reads that column and nothing else. "Added in this slab" is display only. **This is now required, not tidy** (confirmed against Q1): with an offset start, someone on a 22:00 shift cannot earn before 23:00, so their first band ("by 23:00") has no width. Adding up per-band increments would leave them a quarter short. Reading the total for the band their last punch lands in is well defined for every shift. A last punch at 23:30 on a 22:00 shift reads the 23:00-01:00 row and pays 2 quarters, as it should.
2a. **Two different clocks, on purpose, written down.** The gate is a **per-person offset** (earns nothing before shift end + 60 minutes). The bands are **absolute clock times** (23:00, 01:00). So 90 minutes of staying is worth different amounts: off an 18:30 shift, a 20:00 punch earns 1 quarter; off a 22:00 shift, a 23:30 punch earns 2. That is defensible as a night-work premium, and it is also the shift-by-clock quirk in the inclusiveness row below. The reason for the offset is the ATT-04 lesson: a fixed 21:30 edge would pay someone on a 10:00-22:00 shift for 30 minutes **before** their shift ended (`_window_applies`, `payroll_rules.py` lines 481-502, exists to stop exactly that). The engine takes the first of: the offset gate, or the band the punch lands in.
2b. **Stacks with the night green (Q2).** Both are paid on one late night. They are independent: the green is a flat mark at the grade's rate (Rs 200 senior, Rs 100 junior, per the caller), the quarters scale with each person's own day. Neither reads the other. Unflagged staff (other than Contract) earn the quarters and no green (Q3); flagged staff earn both. **`dtc_green_eligibility` now gates only the green, never overtime.** The engine's "night green" threshold and the overtime gate both equal shift end + 60, so on any night the green is earned the first overtime band can also open, and the card shows both.
3. **Never doubled on a special day.** She said the most anyone earns is one day; doubling breaks that. The late-window quarter is already never doubled (`payroll_rules.py` lines 32-37), which is the precedent.
4. **None on a held, absent, on-leave or half-day-leave day.** Half-day leave already gets no green and no late charge (D4); same reason. **None for a category whose "overtime paid" tick is off (Contract), and nothing stored for it (7a).**
5. **Counts once as a day worked.** `days_worked` and the 15-day gate still count the day as 1, not 1.25 (`payroll_month.py` lines 172, 188).
6. **Money is automatic.** `paid_days x daily_rate` already turns a quarter into 1/4 of that person's own day (`payroll_month.py` lines 242-243). No pay code, no slip change, no incentive slot.
7. Show it apart in the Workings report the way the 11 AM quarter is shown (`late_window_quarters`, lines 245 and 307-308): it is already inside Basic earned, so Net must not add it twice.

### 7a. Contract staff: overtime off, nothing recorded (Surbhi's decision, 24 Nov 2026)

**History, so it reads in order.** Earlier on 24 Nov Surbhi answered Q3 as "everyone earns it; agency staff are recorded but not paid", so DTC could reconcile what each agency charges. Later the same day she **reversed it**, in her words: "the contract employees don't stay over time at all, so lets keep it off and ignore it for the contract employees." That is her decision, not my recommendation. The recording scope, the agency columns, the reference value and the reconciliation are all **dropped**. Nothing about agency staff is stored or reported.

**What survives, the whole of it.** One tick on the existing `categories` child table of the rule set: **"overtime paid"**, off for the Contract row. It is the same pattern as `earns_marks` and `earns_leave_credits`, both already off for Contract (coordinator's check, below; `payroll_rules_apply.py` lines 197-210). For a category with the tick off the engine earns **no overtime quarters at all**: the verdict's `overtime_quarters` is 0, nothing is stored, `day_credit` does not move. Rung 3, a field on a table that exists. No new DocType, report, column or flag.

**Two details the engineer must not trip on.**
- **The tick's default must be ON.** A new Check field defaults to 0, so on migrate the Permanent row would read "overtime off" and every permanent employee would silently earn nothing. The engine already treats a category not listed as "marks on, leave on" so that forgetting a row cannot strip anyone (`payroll_rules_apply.py` lines 197-199); overtime follows that rule.
- **The Your Day card must read the same answer.** The engine answers who earns what for the card (`day_rules_on`), so the card row is hidden for Contract staff by the same tick, never by a second rule.

**Out of scope, with the pile each cut landed in:**

| Cut | Pile |
|---|---|
| Per-night overtime approval | Not doing (Q8) |
| Attendance Insights and HR analytics figures | Worth doing later, after 090 |
| A payslip note line for overtime | Worth doing later (DTC works pay in Excel; the Workings report carries it) |
| An eligibility flag for overtime | Not doing: everyone earns it (Q3); the one exception is the category tick (7a) |
| Recording, reporting or reconciling agency overtime | Not doing (Surbhi, 24 Nov, reversing her earlier answer): Contract staff earn and record none |
| Hours, multipliers, comp-off, requests | Not doing |
| A ramp instead of bands | Not doing; her table is bands |
| Manager "who is on overtime" view | Not doing (surveillance) |
| Switching DTC's engine on | A separate decision, not this slice |

## 8. Run-side reality, and what the engine being off means

No `07-devops-inputs.md` exists. **Inferred, not measured:** no new worker, job, page or storage. The engine already reads the last punch for every day it judges, so the new rule adds a table lookup, not a query. One-time cost: re-judging the month after the table is filled, using the existing `payroll_reprocess` (which rewrites every field in `VERDICT_FIELDS`, so the new field must join that list).

**Engine off (`enabled = 0`):**
- The Salary Workings report loads a not-live rule set and says "These rules are not switched on. The figures below are what they WOULD produce" (proven, `salary_components_and_workings.py` lines 74-98 and 250-260). So **overtime can be proved on real DTC data without switching anything on.**
- The Your Day card finds the rule set with no `enabled` filter (proven, `day_marks.py` lines 99-105), so it would show the table even while the engine is off. That is safe only if DTC really pays it from the report into Excel. **Fill the table only when DTC is ready to pay from it**; an empty table shows nothing anywhere (the same "presence of the data is the switch" idea as `day_marks.py` lines 24-26, so no new switch).
- **Proof path:** (1) the read-only count; (2) fill the table on a copy; (3) run the Workings report for a closed month and compare 20 hand-picked nights (every band, plus 22:59/23:00/23:01 and 00:59/01:00/01:01) with DTC's own Excel; (4) fill the table on production at the start of a month.

**Capture windows, a real dependency.** Last-punch pay needs the punch to be captured. Per the caller, DTC's check-out windows close at 05:00 next day on 42 of 46 shifts, and earlier on four (03:59 for "CHD-34 08:00 AM - 08:00 PM", 04:29 on two, 04:59 on five variants). **Inferred: `shift_standard.py` lines 101-102 set the standard at 240 minutes both sides, so running that tool against DTC would flag or reset the wider windows.** A punch after the window gets no shift, falls on the next calendar day, and makes both days odd, so both are held (the ALV-402 failure). Held is safe (neither paid nor refused) but the overtime for that night is then lost until someone fixes it. Its own comment warns that wide windows risk a punch being claimed by the wrong shift when someone holds two assignments. **Not checked:** how many DTC people hold two. Add that to the read-only count.

## 9. Success criteria

| Measure | Baseline | Target | How measured |
|---|---|---|---|
| Accuracy (lagging): hand-picked 20 nights match DTC's own sums | Unknown; no overtime is calculated today | 20 of 20, every edge minute included | HR compares the Workings report with Excel on a copy before switch-on |
| Lost to capture (leading): share of nights with a last punch after the first band that end held or with no shift matched | Unknown, measure first | Surbhi sets it after the count. My proposal: 2% or lower | Read-only query before, the same query a month after |
| Explained (quality): overtime questions HR cannot answer from the day's reason line | Unknown | 0 in the first pay month | Count of HR queries, logged by HR |
| Adoption (leading): share of overtime-eligible staff who opened Your Day on a night they stayed past the first edge | Unknown | A number Surbhi will accept; I will not invent one | `Alvoraa` usage log, if one exists. **Not checked** |

No AI is involved. The rule is deterministic and a person owns every number. **Nothing here proposes or sets a rating.**

## 10. Risks, red-teamed

| Risk | What breaks | Cheapest check or answer |
|---|---|---|
| **Stacking is larger money** | A green-flagged senior who leaves at 01:10 earns a Rs 200 green plus 4 quarters (a full extra day). Her decision (Q2), so not a defect, but it raises the statutory-floor question and the cost per night | Show her the rupee cost per night from the read-only count before switch-on. Counsel first (below) |
| **Fairness: same night, different pay** | Unflagged staff earn quarters and no green; flagged staff earn both. Two people on the same floor, the same night, are paid differently | **Not yet confirmed she has seen this consequence.** Q10 |
| **First band start** | Answered (Q1): shift end + 60, per person. Residual: bands are clock times, so the same 90 minutes pays 1 quarter off an 18:30 shift and 2 off a 22:00 shift | Written down in 7, rule 2a |
| **A Contract person does stay late** | Surbhi says they do not. If one does, they earn nothing and nothing is recorded, so there is no later way to see it | Her decision, accepted. Cheap to reverse: turn the tick on. Nights already worked are re-judged by `payroll_reprocess` |
| **Tick defaults to off on migrate** | A new Check field is 0 by default, so Permanent staff would silently earn no overtime | Field default ON; Contract turned off as data; a test that a Permanent day still earns (7a) |
| **Rewards long nights** | A full day's pay for a 1 am punch pays people to stay and lowers rest | Thriving lens below; HR sees an aggregate, never a ranking |
| **One punch is money** | A person lingers and punches at 11:05 for a quarter | Punches are inside the geofence (ALV-338, per memory notes, not re-verified); HR sees the day's reason line; Q8 asks if she wants approval |
| **Cliffs at 23:00 and 01:00** | 00:59 pays 2, 01:00 pays 4, a jump of two quarters. This is her table, as slab edges are today | The card shows them as clock times, as the ladder does |
| **Machine clock drift** | A machine 3 minutes slow turns 23:01 into 22:58 | **Not checked** whether DTC machines drift. The engine drops seconds, so 23:00:59 reads 23:00 |
| **Table changed mid-month** | Reprocess rewrites the whole month under the new bands | Set it on the first of a month; same limit the slab table has today |
| **`day_credit` can now exceed 1.0** | Any reader assuming a day is at most 1 | The engineer greps every reader at impact analysis. Not done here |
| **Shift windows reset** | Running `shift_standard` against DTC shrinks capture | See section 8 |
| **Employees leave or change grade mid-month** | Overtime follows the day's own verdict and the grade at pay time; same as every other quarter | No new case |
| **Grade blank (2 people)** | No mark-rate row means their greens and reds are worth Rs 0, but quarters use salary, so overtime still pays | Worth telling DTC; not this slice's fix |

**Illustrative money, not DTC data. `[ASSUMPTION]` salaries.** Basic Rs 30,000 over a 30-day month is Rs 1,000 a day, so a quarter is Rs 250. A last punch at 23:42 adds 2 quarters: the day pays 1.5, Rs 1,500. At Rs 15,000 Basic a quarter is Rs 125. Same table, each person's own day. That is her point 1.

## Thriving-workplace lens

| Lens | Answer |
|---|---|
| Engagement | Recognition for real extra effort, stated plainly in advance. A person can see what a night is worth |
| Collaboration | No effect |
| Inclusiveness | **The clock is the same for every shift.** A day-shift worker who leaves at 22:50 and an evening-shift worker who leaves at 22:50 earn the same, though one stayed 4 hours past shift end and the other under 1. That is her table; say so to her. **Stacking with "all" staff also means green-flagged staff earn two rewards for a late night and unflagged staff one (Q10).** Contract staff are left out by Surbhi's decision, on the ground that they do not stay late (7a); that is a fact about their work, not a judgement of their worth, and the tick is the lever if it ever changes. Night work has rest and safety implications for all staff and has extra conditions for women in some states; the rule itself is gender-blind and must stay so |
| Transparency | Employees see the table before they decide. Managers see no one's overtime hours. HR sees pay data it already sees. Any later analytics is aggregate with a minimum count |

## Regulatory read (I am not a lawyer)

1. **Regime:** employment and wage law (overtime wages, working hours, night work), not data protection: punch times are already collected and already drive pay. No new personal data.
2. **Whose obligation:** DTC's. We help by giving a reason line per day and a reproducible month.
3. **What is new:** an automatic pay decision from one punch, deterministic, no AI. New visibility: none beyond what HR sees.
4. **Honest downside:** **stacking (Q2) makes the total for a late night larger, which helps the statutory-floor question but also raises DTC's cost, and she has not consulted counsel on this.** A band table pays a fixed share of a day regardless of hours. **If a state Shops and Establishments Act or the Factories Act applies, statutory overtime is a multiple of the hourly wage for hours past the legal day, and a band may pay less than that floor for some shift and hour combinations. I do not know whether it applies to DTC's staff, or what Delhi, Chandigarh and Ambala require.** `[recall - verify]`

**⚠ COMPLIANCE.** Owner: Surbhi, with DTC's counsel (the counsel who gave oral approval on 25 Oct and advised on HR punches on 21 Nov, per memory notes). **Counsel has not been asked about this slice.** Blocks: **switching it on at DTC**, not building it. Questions to counsel: (1) does paying overtime as a fixed share of a day by band, plus a night green, satisfy, or sit on top of, the statutory overtime rate for DTC's staff; (2) what are the night-work conditions. Both still block switch-on. **A third question I raised earlier, whether recording overtime DTC does not pay changes contract-labour liability, was removed because the recording was dropped. It was not answered by counsel and nobody should read it as settled.** I am not a lawyer.

## Subtract pass

Removed on this pass: a nightly approval step; an Insights chart and HR analytics tile; a payslip note; a new eligibility field; comp-off; a manager "who is on overtime" view; a ramp alternative; overtime on half-leave days; a version-by-date column on the table; a "default" band row; any per-shift override of the table. Kept, because the requirement fails without it: the table, the verdict field, the two report columns, the card row, and one "overtime paid" tick on the existing category table, off for Contract. On the updates of 24 Nov I also removed the overtime eligibility flag and the replace-the-green option (both overtaken by her answers), and, when she reversed Q3, **the whole agency recording scope**: stored but unpaid quarters, the agency column, the reference value, the reconciliation, the field-rights question on `dtc_agency`, and the third counsel question. **I also cut the separate `overtime_paid` yes/no on the verdict.** It existed only to tell "recorded and unpaid" from "paid"; nothing is recorded-but-unpaid any more, so one `overtime_quarters` figure (0 for Contract) is the whole of it. I can name no other reason to keep the pair.

## 11. Open questions

**Answered by Surbhi, 24 Nov 2026 (relayed by the coordinator):**

| # | Answer | Effect |
|---|---|---|
| Q1 | First band starts at **shift end + 60 minutes, per person** (not a fixed 21:30; that was her example for the 20:30 shift). My recommendation, confirmed | Section 7, rules 2 and 2a |
| Q2 | **Stack** with the night green. Not my "replace" recommendation | Rule 2b; risk table; compliance box |
| Q3, first answer | **Everyone** earns it; agency staff **recorded, not paid** so DTC could reconcile each agency. **Superseded the same day, see next row** | None. Withdrawn |
| Q3, final (Surbhi, 24 Nov, reversing her first answer: "the contract employees don't stay over time at all, so lets keep it off and ignore it for the contract employees") | **Everyone except Contract staff.** Overtime is off for Contract and **not recorded** at all | Section 7a: one tick on the `categories` table |

(Q9, the agency reconciliation question, is withdrawn with that scope. The number is left unused so earlier references stay readable.)

**Must know (block the spec):**

| # | Question | My reading, and why it matters | Recommended assumption | Owner / blocks |
|---|---|---|---|---|
| Q10 | Has she seen that same-night pay now differs? Flagged staff: green plus quarters. Unflagged: quarters only | Fairness between people on one floor, and a likely question from staff | She confirms it is intended, or says whether `dtc_green_eligibility` should be widened | Surbhi / none technical; it is a people decision |

**Should know (improve the design):**

| # | Question | Default I will use |
|---|---|---|
| Q4 | A punch at exactly 23:00 or 01:00: which band? | "By" means at or before: 23:00 is band 1, 01:00 is band 2 |
| Q5 | Late arrival and a late stay on one day: separate, or overtime only on a day that lost no quarters? Her DTC docstring says staying late does not make up for arriving late | Separate. The day's reason lists both lines. Net is still the sum |
| Q6 | Overtime on a special day: never doubled | Never doubled |
| Q7 | A held day released by an HR-typed time: does it pay overtime? | **No.** An HR-typed time must not move money. To earn it, HR adds the real punch through slice 087's route (reason and confirm required, per counsel). Slice 087 is on this branch; **production not checked** |
| Q8 | Any nightly approval? | None. HR reads the report before Excel |

**Evidence required before the spec, read-only on production:** (a) a count of last-punch times for Oct and Nov, by band edge and by the 05:00 capture limit; (b) headcount per shift (the caller's query returned 0); (c) the number of people with two shift assignments on one day; (d) how DTC pays this today.

## Assumptions

- `[ASSUMPTION]` DTC pays from the Salary Workings report into Excel, not by posting salary slips (memory note of 26 Oct; not re-verified today).
- `[ASSUMPTION]` Production check-out windows are as the caller read them (420-600 minutes, close 05:00).
- `[ASSUMPTION]` The latest DTC shift ends 10 PM (a docstring in `payroll_rules.py`, which may be stale).
- `[ASSUMPTION]` Illustrative salaries in section 10 are not DTC's.
- `[ASSUMPTION]` Q4-Q8 and Q10 defaults stand until she says otherwise.
- `[ASSUMPTION]` Contract staff really do not stay late (Surbhi's statement; not measured). Nothing is recorded for them, so this cannot be checked later from our data. If it matters, the read-only count in section 11 could be run once for Contract staff.
- `[ASSUMPTION]` The table can hold a time past midnight. **A plain Time field cannot say "01:00 next day".** The spec writer must choose a shape that can (minutes after the shift-day midnight, or a next-day tick). Not decided here.

## Kill criteria

Stop and tell Surbhi if: the read-only count shows fewer than a handful of qualifying nights a month (this becomes a spreadsheet task); counsel says band pay cannot stand in for the statutory rate and DTC will not change the table; the cost per night, with the green stacked on top, is more than she expects once shown in rupees; or the capture windows cannot safely reach the hours the bands need.

## Coordinator's verification, 24 Nov 2026

The product manager had no shell and marked several facts unchecked. I read these
read-only on `dtc.alvoraa.co` (container `compose-backend-1`) the same day. They
settle two of the assumptions above. (Trimmed after Surbhi dropped the agency
scope: the agency table and the 45-versus-44 count are removed with it.)

**Contract is identified by `employment_type`, and it has a real row in the rule
set's `categories` table.** That is what the "overtime paid" tick in 7a hangs on.
Verified on production the same day. The table holds exactly two rows:

| category | grace_minutes | earns_marks | earns_leave_credits | doubles_deduction |
|---|---|---|---|---|
| Contract | 15 | 0 | 0 | 0 |
| Permanent | 0 | 1 | 1 | 1 |

Contract already earns no marks and no leave credits, so an "overtime paid" tick
turned off for Contract follows a pattern that is there twice already.

**Mark rates confirmed** (the green-rate assumption is discharged): Junior Rs 100,
Senior Rs 200, "No leaves" Rs 0, External Rs 0. Grades on active staff: Junior 476,
Senior 16, External 1, and **2 with a blank grade and so no rate row** — the
section 10 risk row is real and counted.

**Still not checked**, and still owed before the spec: the last-punch distribution
for October and November by band edge; headcount per shift; how many people hold
two shift assignments on one day; and how DTC pays late stays today.

## Handoff note

To the UX designer and the analyst. Q1-Q3 are answered (section 11; Q3 was reversed once, read the final row); Q10 is not. Do not add a manager view. The overtime gate is a per-person offset and the bands are clock times; keep both in the spec and the card, and test a 22:00 shift, where the first band has no width. The engine must read the "total overtime" column only. Contract staff: the category tick is off, so the engine earns and stores no overtime for them; test that a Contract day carries 0, and that a Permanent day still earns (the tick's default is ON). There is no agency column, no recorded-but-unpaid figure and no `overtime_paid` yes/no; do not add them. Write the card row in Hindi and English with clock times only. In the spec, grep every reader of `day_credit` and `total_quarters` (the Workings reports, `payroll_slip.py`, `payroll_reprocess.py`, `alv291_attendance_fix.py` line 1164, and the tests) because a day can now be worth up to 2.0. Check that `payroll_reprocess` rewrites the new field. Slice 090 is still moving; do not touch Insights. If you disagree with anything here, say so in your own handoff and stop, rather than building something different.
