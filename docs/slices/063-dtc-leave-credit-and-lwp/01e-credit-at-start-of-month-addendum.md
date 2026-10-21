---
slice: 063-dtc-leave-credit-and-lwp
artifact: 01e-credit-at-start-of-month-addendum
author: hrms-product-manager
date: 2026-10-21
status: draft — recommendation only, waiting for Surbhi
amends: 01-product-brief.md §2, §8 (WOW), §14; 01d-half-day-addendum.md (example and D2)
inputs: Surbhi's message of 21 Oct 2026 (client confirmed); payroll_rules.py (leave_credits_for_month 185-239), payroll_month.py, payroll_slip.py, alvoraa_payroll_rule_set.py (validation 185-245), tests test_payroll_rules.py 495-583 and test_payroll_month.py; 03-functional-spec.md v2.1; 01c; prototype-v2.html (all read in worktree 060-manager-review)
---

# 063 addendum · Leave is credited on the 1st of the month, not earned by attending

**Surbhi, 21 Oct 2026, after checking with DTC:** "there is no process of accrual, all leaves are credited in the beginning of the month and remaining ones encashed with the salary." (Accrual means building credits up day by day as you attend.)

**Bad news first.**

1. **This contradicts something DTC said on 9 Oct, and only Surbhi can settle which one wins.** The engine's tests quote her from 9 Oct: *"if anyone has come only a few days in a month he get the salary for those days only"* (`test_payroll_rules.py` line 555). That sentence is why there is a 15-day minimum. Today's message does not say whether the minimum goes. **Decision E1.** My recommendation keeps it.
2. **If the 15-day minimum stays, the jump on the 15th day comes back.** Accrual was brought in on 9 Oct to soften it. With a flat credit, a class A person's 15th day attended is worth 5 days' pay: the day itself plus 4 credits. On a ₹23,000 Basic in October that is ₹3,709.68 for one day's work. The old test pinned this on purpose (`test_the_step_at_the_gate_is_three_days_not_five`, line 542).
3. **Nobody is paid less than under the accrual rule. Anyone with less than a full month is paid more.** DTC's payroll cost goes up. I cannot give the total without October's attendance. **Evidence required:** the rehearsal works it out (§5).
4. **The spec, the security file and the prototype all describe credits as "earned so far".** They need the changes listed in §7 before anyone builds.

---

## 1 · The rule as I read it

**Stated by DTC (confirmed through Surbhi):**
- Class A gets 4 days of Paid Leaves, B gets 3 and C gets 2, all on the 1st of each month.
- Paid Leaves taken that month use these days first.
- Days not used are paid with that month's salary.
- Nothing carries over.
- Contract staff and the No Leave, 5-Day Week and Sundays Off classes stay at 0. Nothing changes for them.

**Not stated. My recommended default for each:**

| Gap | Recommended default | Why |
|---|---|---|
| Does the 15-day minimum stay? (E1) | **Stays.** The days are credited on the 1st, but are only paid if the person attends 15 days in the month. | It keeps DTC's 9 Oct rule, which today's message does not withdraw. It needs no code (§3). |
| Someone who joins mid-month (E2) | **Same rule.** Full credit if they reach 15 days attended that month, otherwise none. No pro-rata (a share in proportion to days employed). | Pro-rata is a rule nobody has stated. It would need new code. |
| Someone who leaves mid-month (E3) | **Same rule.** Full credit if they attended 15 days before leaving, paid in their last salary, otherwise none. | Same reason. |
| Someone absent most of the month (E4) | Under 15 days attended means **no credit**. | E1. |
| Days of Leave Without Pay | They do not reduce the credit. They count as days not attended, so they can push someone under 15. | This is what the engine does today. |
| Do approved Paid Leaves days count toward the 15? (E6) | **Today they do not.** I recommend they should (see E6). | Otherwise taking your own Paid Leaves properly can cost you all of them. Example: 14 days attended plus 4 Paid Leaves days loses the 4 credits, and the 4 leave days go unpaid. |
| Half-day leave | **Uses 0.5 of the Paid Leaves.** | 01d, agreed in principle. |
| An absence nobody applied for (E5) | **Costs the same as today.** The day is unpaid and the credits are still paid. The only exception: on a special day an absence is charged double. | DTC have not stated a penalty. Inventing one is not ours to do. |

## 2 · What this supersedes in the brief and 01d

| Where | What goes | Replaced by |
|---|---|---|
| Brief §2, rows "How are credits earned?" and "Do leave days count as attended?" | 1 credit per 7.5 or 10 days attended | Flat 4 / 3 / 2 on the 1st, kept from 15 days attended (if E1 = stays) |
| Brief §8, the WOW ("2 earned so far — from 18 days attended…") | "Earned so far" | "4 days of Paid Leaves for October" from day 1 (§4) |
| Brief §14, "Mid-month alarm: on the 10th everyone shows 0 earned" | The whole risk | Gone. The card shows 4 from the 1st, with one line about the 15 days. |
| 01d §1, the 30/31-day worked example (29.5 days → 3 credits) | **Withdrawn entirely.** Credits no longer depend on the exact number of days. | — |
| 01d, the card's "to be paid out can end in .5" | Now only after a half day | — |
| Card projection wording ("These are figures so far. They change as you attend more days") | Gone | "Paid with your October salary. Nothing carries over." |

**01d's decisions:**

| 01d | Still matters? |
|---|---|
| D1: the other half of a half day is measured by punches against half the shift | **Yes.** Without the 01d engine change, the leave half is still charged as missing time. That is money, whatever the credit rule. |
| D2: a half-day leave counts 0.5 toward attended days | **Only at the 15-day line** (14.5 or 15). Moot if E1 = goes. |
| D3: ignore late, early and the late window on a half day | Yes. Already agreed by Surbhi. |
| D4: no green marks on a half day | Yes. Still open. |
| D5: no punches means the other half is absent | Yes. Already agreed. |
| D6: the 5-day limit on Leave Without Pay | Already settled: 5 a calendar month (brief, last sections). |
| D7: first half or second half | Still "not now". |

## 3 · What changes in the engine — **configuration first, not code**

**If E1 = the 15-day minimum stays, this is configuration of the existing rule set. No engine code changes.** I checked the arithmetic against `leave_credits_for_month` (lines 229-239) and the rule set's own validation (`alvoraa_payroll_rule_set.py` lines 185-239):

| Rule set field | Today | New value | Effect |
|---|---|---|---|
| `leave_threshold_days` | 15 | 15 | Under 15 days attended: 0 |
| `accrual_month_days` | 30 | **15** | Attended days stop counting at 15 |
| Class A: `period_days` / `credit_per_period` / `monthly_credits` | 7.5 / 1 / 4 | **15 / 4 / 4** | One 15-day block = all 4 credits |
| Class B | 10 / 1 / 3 | **15 / 3 / 3** | |
| Class C | 7.5 / 0.5 / 2 | **15 / 2 / 2** | |

- **Check:** at 15 or more days, 15 ÷ 15 gives 1 block, times the class figure = 4, 3 or 2. Under 15 gives 0.
- **Check:** the rule set's validation passes. Its sum at full attendance (15 days, one block) equals `monthly_credits` for every class.
- The record can say this plainly: "4 credits per 15 days attended; counting stops at 15." Add a comment on the record with Surbhi's message and the date.

**Rejected cheaper or quicker options:**
- Leaving the rule set as it is. It produces accrual.
- A config trick for E1 = goes: an "accrual month" of 1 day, so that 1 day attended gives the full credit. The fields would then say "4 credits every 1 day in a 1-day month", which the next person will "correct". I recommend code instead if the minimum goes.

**Code is needed only if Surbhi chooses any of these:**
- E1 = the minimum goes.
- E2 or E3 = pro-rata.
- E6 = Paid Leaves days count toward the 15.

The change would be:

| File | Change |
|---|---|
| `payroll_rules.leave_credits_for_month` | Becomes "the class figure if the condition holds, otherwise 0". The 7.5-day cadence is deleted. |
| `payroll_month.summarise_month` | E6 only: count approved Paid Leaves days (already passed in as `approved_leave_days`, spec US-21) toward the 15. |
| `payroll_slip.month_summary` | E2/E3 only: also read `date_of_joining` and `relieving_date`. |
| Rule set and Leave Class doctypes | Delete `period_days`, `credit_per_period`, `accrual_month_days` and the cadence check (lines 210-239). The rule set is off and holds one DTC record, so there is no live data to move. |
| Desk report *Salary Components and Workings* | **No logic change.** It already shows `month_summary`'s figures. Its "Leave earned" column then means "credited". |
| `on_salary_slip_validate` | No change. |

**Tests that encode accrual:**

| Test | Config route | Code route |
|---|---|---|
| `test_payroll_rules.py` lines 495-583, the leave-credit class: `test_below_the_gate…`, `test_full_attendance…`, `test_class_A/B/C_scales…`, `test_the_step_at_the_gate_is_three_days_not_five`, `test_a_few_days…`, `test_a_new_joiner…`, `test_the_cap_holds…`, `test_a_contract_employee…`, `test_both_the_gate_and_the_cadence…` | Still pass, because they test the function with their own figures. But their docstrings call the 7.5-day cadence "DTC's" rule, which is no longer true. Update the words only. | Rewritten or deleted (the cadence tests go, the gate tests stay if E1 = stays). |
| `test_payroll_month.py` lines 14-17 (`CLASS_A`, `CLASS_B` fixtures) | Pass. Words stale. | Change to flat figures. |
| `test_payroll_month.py`: `test_a_few_days_in_a_month…` (109), `test_a_leave_day_is_not_a_day_worked` (138), `test_leave_cannot_be_funded_below_the_gate` (198) | Pass | Stay if E1 = stays. 138 changes if E6 = yes. |
| `test_payroll_month.py`: `test_leave_beyond_the_credits_is_unpaid` (188: 24 days gives 3) and `test_a_complete_month_end_to_end` (252: 3 credits, 2 encashed, 25.5 paid days) | Pass | Change to 4 credits, 3 encashed, 26.5 paid days, and net and gross to match. |
| Fixtures with `leave_threshold_days` / `accrual_month_days`: `test_day_marks.py` 48-49, `test_payroll_reprocess.py` 85-86, `test_salary_report.py` 94-95 | Pass | Remove the deleted keys. |

## 4 · The card

The credit figure now comes from the rule set's own `monthly_credits` for the person's class. It is the same number the engine pays once the 15 days are met. Used and Waiting are unchanged from the spec.

| | 1 October (0 days attended) | 20 October (18 attended, 1 approved, 1 waiting) |
|---|---|---|
| **Paid Leaves this month** | 4 | 4 |
| **Used** | 0 | 1 |
| **Waiting for approval** | 0 | 1 (set aside) |
| **Left to be paid out** | 4 | 2 |
| Line under the figures | "These count once you have attended 15 days in October. You have attended 0 so far." | (none — 15 reached) |

**Rule shown to the employee:** "Class A: 4 days of Paid Leaves on the 1st of every month. They count once you have attended 15 days that month. Days you do not use are paid with that month's salary. Nothing carries over."

If E1 = goes, the second sentence and the "count once" line disappear.

## 5 · Pay compared with the accrual rule

**Method.** These use the engine's own sum (`payroll_month.py` lines 176-180): paid days = day pay + credits, and daily rate = Basic ÷ days in the month. October has 31 days. Attended days counted up to 30 under accrual. **₹23,000 is the engine tests' example Basic, not a DTC salary.** Daily rate = ₹741.94. Each row assumes the remaining days are leave or absence, not on a special day.

| Class | Days attended | Credits under accrual | Credits now | Change |
|---|---|---|---|---|
| A | 31 | 4 | 4 | none |
| A | 28 (+3 Paid Leaves) | 3 | 4 | **+1 day, +₹741.94** |
| A | 20 | 2 | 4 | +2 days, +₹1,483.87 |
| A | 15 | 2 | 4 | +2 days, +₹1,483.87 |
| A | 14 | 0 | 0 | none (under 15) |
| B | 28 | 2 | 3 | +1 day, +₹741.94 |
| B | 15 | 1 | 3 | +2 days, +₹1,483.87 |
| C | 28 | 1.5 | 2 | +0.5 day, +₹370.97 |
| C | 15 | 1 | 2 | +1 day, +₹741.94 |
| Contract, No Leave, 5-Day Week, Sundays Off | any | 0 | 0 | none |

**Nobody loses.** The accrual credit was always capped at the class figure.

There is also a fairness gain worth naming. Under accrual, a Paid Leaves day also slowed the credit. Now 4 Paid Leaves days in a full month truly cost nothing: class A, 27 attended plus 4 Paid Leaves gives 27 + 4 = 31 paid days, a full month.

**What the rehearsal on a local copy must prove** (rule set changed as in §3 and switched on locally only, never on dtc.alvoraa.co):
1. The rule set saves with the new values.
2. For named October staff: full attendance gives 4, 3 or 2; 15 to 30 days gives the full class figure; 14 days gives 0; all zero classes give 0.
3. The desk report's "Leave earned" equals the card's figure for everyone at 15 days or more.
4. Slip paid days equal the report's paid days, and saving a slip twice gives the same answer.
5. One case worked by hand: 28 attended plus 3 Paid Leaves gives used 3, paid out 1, paid days 32.
6. **The extra October cost against accrual**, summed from the report, shown to Surbhi before switch-on.

## 6 · Decisions for Surbhi

| # | Question | My recommendation |
|---|---|---|
| E1 | DTC said on 9 Oct "if anyone has come only a few days he gets salary for those days only". Does the 15-day minimum still apply to the credited days? | **Yes, keep it.** It is configuration only. Know that the 15th day then jumps by 4 credits. |
| E2 | Someone joins mid-month: full credit, a share, or none? | **Same 15-day rule, no share.** |
| E3 | Someone leaves mid-month? | **Same 15-day rule, paid in the last salary.** |
| E4 | Someone absent most of the month? | **No credit under 15 days** (follows E1). |
| E5 | Should an absence nobody applied for cost more than a Paid Leaves day? | **No.** Same as today, except double on special days. DTC have not asked for more. |
| E6 | Do approved Paid Leaves days count toward the 15 days? | **Yes.** Otherwise using your own leave properly can lose it. This is the one small code change. |
| E7 | A half-day leave uses 0.5 of the Paid Leaves? | **Yes** (01d). |
| E8 | Contract and the zero classes unchanged? | **Yes.** |

## 7 · What the analyst, security engineer and designer must revise

**Spec (`03-functional-spec.md`), by parity row and section:**

| Row / section | Today | Change to |
|---|---|---|
| R-3 chip | "So far · up to {date}" | "{Month}" only. Keep the "up to {date}" line only while under 15 days. |
| R-4 class line | "up to {cap} days a month · {n} days attended up to {date}" | "Class {c} · {cap} days of Paid Leaves for {Month}" |
| R-5 figures | "Earned so far" | "Paid Leaves this month". Used, Waiting and To be paid out unchanged. |
| R-6 figure notes | "from {n} days attended" / "{n} of the 15 days needed" | Under-15 note only. "with {Month} salary" stays. |
| R-7 | "These are figures so far. They change as you attend more days…" | **Delete.** Replace with "Nothing carries over." |
| R-9 under-15 line | "You start earning Paid Leaves once you have attended 15 days…" | "These count once you have attended 15 days in {Month}. You have attended {n} so far." Delete if E1 = goes. |
| R-12 rule box | Per-period sentence from `period_days` / `credit_per_period` | §4's sentence, from `monthly_credits` and `leave_threshold_days` only |
| R-33 preview, Paid Leaves short | "…or ask for Paid Leaves once more days are earned" | Drop that clause. Nothing more is earned in the month. |
| R-34 preview under 15 | "Paid Leaves start after 15 days attended…" | "Your Paid Leaves count once you have attended 15 days…" Delete if E1 = goes. |
| R-35 preview, Leave Without Pay | "any Paid Leaves earned this month are still paid out" | "your Paid Leaves for {Month} are still paid out" |
| R-42 preview, half day | "A half day is counted as a short working day, not as leave" | Per 01d: "A half day uses half a day of Paid Leaves. Check in for the other half." |
| R-64 rule | "A half day uses no Paid Leaves and never sets a day aside" | **Reversed:** uses 0.5, sets 0.5 aside while waiting |
| §7.5 card keys | `earned`, `gate`, `period`, `gain`, `cap`, `days_attended`; `earns` tests `period_days` / `credit_per_period` | Add `credited` (= class `monthly_credits`). Drop `period` and `gain`. `earns` = `monthly_credits` > 0 and the category earns. `days_attended` and `gate` only while under 15. |
| §7.7 fields read | includes `period_days`, `credit_per_period` | Drop both |
| §11 fixture | class A 7.5 / 1 / 4 | 15 / 4 / 4, `accrual_month_days` 15 |
| AC-1, AC-2, AC-3, AC-7, AC-10, AC-11, AC-13, AC-100 | Accrual figures and wording | Rewrite to §4's table. AC-3 becomes "changing `monthly_credits` changes the card with no code change". |
| AC-66, AC-67, E-1 | Half day uses none | Per 01d |
| E-14 mid-month joiner | "Cannot reach the gate" | Per E2 |
| H-3, H-4, H-11 (Hindi) | "अब तक मिली", "figures so far" lines, "earned so far" | Retranslate the new English |
| US-2 | "under the 15-day gate, why I have 0" | "why my 4 days are not counted yet". Drop if E1 = goes. |

**Security (`01c`):**
- Line 153 (data inventory): the card no longer needs `period` or `gain`. It needs days attended only while under 15. Less pay-derived data shown — an improvement, nothing new exposed.
- Lines 236-239 (allowed keys): remove "period, gain". Add `credited`.
- No new threat and no new requirement. SEC-1's key list must match spec §7.5.

**Design (`prototype-v2.html`, and the matching parts of `02-design.md` §6.1-6.3):**
- Line 203: `CLASSES` per / gain — drop.
- Lines 268-269: rule sentence — replace with §4's.
- Line 290: class line — R-4.
- Line 293: "Earned so far" figure and note — R-5, R-6.
- Line 298: under-15 line — R-9.
- Line 308: "figures so far" line — R-7.
- Line 310: "So far" chip — R-3.
- Line 432: half-day box — R-42.
- Line 441: preview under-15 sentence — R-34.
- Each with its Hindi string.

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| O1 | E1: does the 15-day minimum survive the 21 Oct message? | Surbhi, with DTC | Config route or code route |
| O2 | The total extra October cost against accrual | Engineer, in the rehearsal | Surbhi's switch-on decision |
| O3 | The memory note `dtc-leave-classes.md` and the docstring of `payroll_rules.leave_credits_for_month` still describe accrual as DTC's rule | Coordinator / engineer | Nothing; stale words mislead the next session |

## Assumptions

- `[ASSUMPTION]` "Credited in the beginning of the month" means the class figure (4 / 3 / 2), not a different number.
- `[ASSUMPTION]` The rule set is still off at DTC, so nothing live changes until the rehearsal passes and Surbhi switches it on.
- `[ASSUMPTION]` "Paid Leaves" is the leave type from brief D1, and only it draws on the credits (spec U1).

## Subtract pass

Removed:
- A proposal to relabel the desk report's "Leave earned" column. It is words only, and the report is HR's.
- A pro-rata formula for joiners and leavers. Nobody asked for it.
- A separate "credited" field on the rule set. `monthly_credits` already is that number.

Kept: E6's small code change, as a decision rather than a default, because it changes pay.

## Handoff note

To the engineer: if E1 = stays and E6 = no, do not touch engine code. Change the rule set values in §3 on the local copy only, and run the rehearsal. To the analyst and designer: §7 lists every row that moves. The card's credit figure is the rule set's `monthly_credits`, never typed into the page.
