---
slice: 085-held-odd-punch-days
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-11-19
status: draft
inputs: [01a-ux-opportunities.md, 07-devops-inputs.md §1]
---

# 085 A day with a missing punch is held, not guessed

**Risk tier: 1** (it changes pay). **Rung: 3 (custom fields and a setting) plus 4 (a small amount of code).** Recommendation only. Surbhi decides.

## Bottom line

1. **Build it, thin.** One company switch, one monthly-limit setting, odd-count days written as held, one clear sentence for the employee, release through the regularisation paths that already exist, and a dry-run-first November backfill.
2. **Bad news first, in bold: the held logic today lives only behind DTC's pay-rule set.** Grace has no rule set, so for Grace "held" does not exist yet. That is the real work in this slice.
3. **Bad news, second: 80 Grace employees lose pay for days that show Present today.** That needs a notice before it happens (decision a).
4. **Overlap with 084 is settled** (section 8).

## What I checked, and what I could not

- **Read (proven):** worktree `085-held-odd-punch-days`; `payroll_rules_apply.py` 470-590 (the held verdict, `attendance_onload`); `payroll_fields.py` (the three held fields); `payroll_slip.py` 341 and 421 (a held-days note on the slip); `attendance_correction.py` 1383-1400 (settings are site defaults) and `decide` at 1734 (HR review queue); slice 084 brief.
- **Could not run:** `git rev-list --left-right --count dev...origin/dev`. This session has no shell. **I cannot say how far behind `origin/dev` the checkout is.** The UX scan names HEAD `fd658eff`. Before anyone writes "X is not built" from this brief, run it.
- **Not checked:** whether the Daily Attendance Workings report can list held days for Grace; what Frappe's Salary Slip does with a held row (I assume an Absent-status row costs a day, as Frappe treats unmarked days); where Grace's 3-a-month Server Script lives (site data, not in the repo).

## 1. Job to be done

**Persona: HR Manager** (pays people right), **Employee** (is paid for days they worked). CXO sees nothing new.

> "As an HR manager, when someone has one punch on a day, I want that day neither paid nor refused until a person has looked at it, so payroll is never a silent guess."

> "As an employee who forgot to punch out, I want to be told the day is waiting on me, and what to do, so I am not surprised on pay day."

## 2. Current pain (a story, not a statistic)

I have no count of disputed pay. The data we do have, from Surbhi, 19 Nov: Grace, 1-18 Nov, has **86 one-punch days now marked Absent and 80 three- or five-punch days now marked Present**. Same kind of fault, opposite pay result, decided by whichever way the machine counted. DTC's engine already holds one-punch days (ATT-06) and ALV-351 on dev holds odd counts, but DTC's rule set is off and its pay is in Excel.

## 3. Competitors (whole products)

Source: the UX scan, one web search on 19 Nov 2026, help pages read as search summaries only. I did not re-search.

| Capability | Keka | Zoho People | factoHR | Frappe HR standard | Us |
|---|---|---|---|---|---|
| Employee regularises missing in/out | Yes (read, 19 Nov) | Yes (read) | Yes (read) | Attendance Request exists; held state not checked | Yes, today |
| HR or manager files on behalf | Yes, with bulk (read) | Yes (read) | Manager then HR (read) | Not checked | Yes, today |
| Monthly request cap | Not found | Yes (read) | Not found | Not checked | Grace only, hidden script |
| Missing punch is a **held, unpaid-until-fixed** state | Not found | Not found | Not found | Not checked | **DTC only, engine path** |

greytHR, Darwinbox: nothing found. Pricing tier: not found, so I say nothing about plans.

**Not copied:** (a) bulk regularisation (people approve a pile without looking, which defeats the point of holding); (b) a reminder-and-nag loop; (c) a manager-visible "missing punch" ranking of people. **Honest claim:** I found no source for a held state. That is "I found none", not "nobody has one".

## 3a. Three ways, and could we not build it?

| Way | What | Verdict |
|---|---|---|
| Conventional | Mark odd days Absent, let people regularise (what Keka, Zoho do) | Rejected. It is today's Grace Absent, and it does nothing for the 80 Present days |
| **Better (recommended)** | Reuse the three held fields on the Attendance row; extend the marking to non-rule-set companies behind a company switch; release by the existing regularisation paths | Smallest thing that meets all seven decisions |
| Reimagined | A held-days inbox for HR with ageing, reminders, bulk release | Rejected. Not asked for, and it is a new screen |
| Build nothing? | Keep Present/Absent | Rejected. It is the decision Surbhi made |

## 4. Kano class and demand

- **Must-be for the payroll owner, `proxy`.** Wrong pay in either direction is the kind of fault that causes anger and earns nothing when right. For the employee it is close to **Reverse** (a day paid today becomes unpaid): hence the notice.
- **Demand I actually have (seen):** Surbhi's own Grace roster check (16-17 Nov) and the DTC feedback of 18 Nov, which found 340 Present days on 0 hours. That is **two tenants, one founder**. No survey. **Evidence required:** DTC's count of odd days; would change class if Grace HR says the 80 are rare real mistakes.

## 5. Persona enhancements through the portal

| Persona | Enhancement | In this slice? | Why |
|---|---|---|---|
| Employee | Day sheet says "Held: one punch. Not paid until fixed", and asks only for the missing time | **Yes** | The WOW; wording plus a form that exists |
| Frontline employee, phone | "2 days held. Fix now" on Home | **Later** | Nice, not needed to pay people right |
| Employee | After release: "Held, now Present. Pay restored" | **Yes, as one line** | Employee sees the effect |
| Line manager | Files for a direct report (exists today); nothing new | **No** | Existing path |
| HR | A held-days list before payroll | **No** | Use the Daily Attendance Workings report (see Q3) |
| HR | Month-end "14 days still held" warning | **No** | The slip already carries a held-days note on the engine path |
| HR | Switch and monthly limit as settings | **Yes** | Retires the hidden Grace script |
| CXO | One company total, no names | **No** | Not needed |

## 6. The WOW

An employee at Grace opens 12 Nov and sees, in amber: **"Held. One punch on this day. It is not paid until it is fixed. What time did you leave? [ 18:30 ] [Send to HR]."** One field. No "Absent" for a day they worked.

## 7. Thin slice

**Needed to validate this now:** the company switch; odd-count days written as held for a company with the switch on (Grace first); the one-sentence day-sheet wording; release flips the day to Present and refreshes that one employee's slip.
**Needed before it can ship:** the monthly-limit setting (held days outside it) and the Grace script retired in the same release; November backfill, chunked, dry-run first, with a saved undo list (OPS-1, OPS-8); the compliance answer in Q1.
**Later:** Home strip, reminders, ageing, a held list, manager bulk filing.
**Not doing:** a new DocType, a new settings page, a rules engine, email, push.

**Storage and payroll recommendation (assumption):** a held Grace day is stored as an Attendance row marked held **with Absent status**, so Frappe payroll needs no change; release sets Present. The engineer must prove this against the real slip.

**Subtract pass.** Removed from the UX scan: Home strip, ageing colour, month-end warning, held list, CXO aggregate, nag loop. Removed from my own first draft: an email notice build. The brief does not need them to meet the seven decisions.

## Decisions raised by the scan

| | Recommendation |
|---|---|
| (a) Notice before 80 Present days lose pay | **Yes, and cheaply.** Run the backfill after the release lands, give HR the list of names, HR tells them. Employees keep until payroll cut-off to regularise. No new email. [ASSUMPTION: Grace's November payroll is not yet run, so nothing paid is clawed back.] |
| (b) Who approves the employee's own request | **Keep today's route:** HR reviews (`decide`, role-checked). A manager who files for a report is also decided by HR. No new routing. |
| (c) Who owns the cap | **085 owns it**, per company, replacing the Grace script. 084 left it out. |
| (d) DTC payroll is in Excel | **Do not touch Excel or the engine.** DTC gets the same held marking; "pays nothing" shows in the Salary Workings report. The portal does not show it, and the brief says so plainly. |

## 8. Overlap with 084

084 sets how many days back an employee may raise a day. 085 owns the monthly cap. They are two separate settings and can ship in either order. **One trap:** if 084's window refuses an old held day, the employee loses the day's pay for ever. **Recommend held days be exempt from the window too** (Q2).

## 9. Success measures

| Measure | Baseline | Target | Instrument |
|---|---|---|---|
| Held days still open at payroll cut-off (leading) | 166 on day one | Down to those HR chose to leave | Count of held rows at cut-off |
| Slips that paid a held day (lagging) | Unknown, measure first | 0 | Compare slip days with held rows |
| "Why am I Absent" questions to HR (efficiency) | Unknown, measure first | Fewer than the first month | HR's own count |

## 10. Thriving-workplace lens

- **Engagement:** clarity, not recognition. A day waiting on me has a name.
- **Collaboration:** a manager can file for a report.
- **Inclusiveness:** contract and shift staff use a phone; wording must fit 360 px and Hindi. Needs a UX check.
- **Transparency:** the employee sees their own held state. Managers see punch counts, never reasons.

## 11. Regulatory read

1. **Regime:** employment and wage law (pay withheld). DPDP: no new data.
2. **Whose obligation:** the employer's (Grace, DTC). We help them hold pay by a rule they can show.
3. **New:** an automatic pay hold. That is an automated decision about pay, with a human release, which meets counsel's earlier "access and grievance" line.
4. **Honest downside:** "your day was paid, now it is not." ⚠ COMPLIANCE: whether withholding pay for a day worked, on the strength of a missing punch, is allowed at Grace and DTC. I am not a lawyer. **Owner: Surbhi with counsel. Blocks switching on for Grace.**

## 12. Risks

- A late machine punch (Grace hourly, DTC about 5 min) makes an odd day even after marking. The day must release itself, and the 3-4 minute auto-attendance must not re-mark it (OPS-2).
- Grace's draft slip job is dead since 18 Nov (five leavers). Release must refresh one employee's slip, not rely on the batch (OPS-3).
- At 10x staff, the backfill is chunked per site; DTC could be up to about 8,000 rows (OPS-1, estimate).
- Removing the Grace script before the setting works would leave no cap, or two caps (OPS-5).

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| Q1 | Is holding pay for the 80 Present days allowed? | Surbhi and counsel | Switching on at Grace |
| Q2 | Are held days exempt from 084's days-back window too? | Surbhi | The 084 check |
| Q3 | Can the Daily Attendance Workings report list held days for Grace? | Engineer, to check | Whether HR needs a list |
| Q4 | Is Grace's November payroll still unrun? | Surbhi | Decision (a) |
| Q5 | The switch is "per company", but settings today are site defaults. Company custom fields fit; confirm | Surbhi | Setting design |

## Assumptions

- [ASSUMPTION] A held Grace row with Absent status costs a day in Frappe payroll.
- [ASSUMPTION] November payroll for Grace and DTC is not yet run.
- [ASSUMPTION] The checkout is current; not verified.

## Kill criteria

Stop and rethink if: (1) the dry run shows held marking changes Grace days other than the 86 and 80 expected; (2) a slip cannot be proved to drop a held day; (3) counsel says no to the 80; (4) auto-attendance re-marks a held row on the next tick.

---

## Brief gate: Surbhi's answers (19 Nov 2026), decided: BUILD THIS

1. **Q1, compliance: settled.** Held days are regularised at the end of the month, before salaries are paid. The point is not to mark people who were present as absent.
   The practice tells Grace whether a day was full or half, and it builds the habit of punching every day. Grace can be switched on.
2. **Storage: a true "Held" status**, not Absent plus a flag. Reports, the register and slips must read "Held".
3. **Scope: October stays as it is. The backfill applies to November only, for Grace.** (The 084 window question was not decided; she did not need it.)
   Whether DTC's November is backfilled was asked before and answered "yes, backfill November". Confirm this at the design gate.
