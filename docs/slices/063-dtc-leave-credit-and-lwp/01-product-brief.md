---
slice: 063-dtc-leave-credit-and-lwp
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-10-21
status: draft — waiting for Surbhi's gate (build, change or drop)
inputs: Surbhi's request 21 Oct 2026; payroll_slip.py, payroll_month.py, payroll_rules.py, payroll_rules_apply.py, hr_api.py, inbox_api.py, portal.js, parts/attendance.html, salary_components_and_workings.py, hrms leave_application.py and setup.py (all read in worktree 060-manager-review on 21 Oct 2026)
---

# 063 · DTC: show this month's leave credit, and let staff apply for leave

**Bad news first.**

1. **No DTC employee can apply for any leave on the portal today, not even leave without pay.** Confirmed in code: the "Apply Leave" list is filled only from leave types that have a balance (`_populateLeaveTypeSelect`, portal.js line 4472). DTC has no Leave Allocations by design, so the list says "No leave has been allocated to you - contact HR". Leave without pay never has a balance, so it never appears.
2. **The brief was written without the UX scan (`01a`) and the DevOps first look (`07` §1).** Both are missing for this slice. I went ahead because the request is small and every surface is named below, but the design step must not start until both exist.
3. **DTC's credits are not a flat 4 / 3 / 2 a month.** They are earned by attending. See §2. A screen that shows "4" on the 10th of the month would be wrong.

---

## 1 · The job to be done

**Employee (DTC, in her words):** "When I open Leave, I want to see how many leave credits I have this month after the leave I've already taken, so I know what I'll be paid for. And when I need a day off with no credit left, I want to apply anyway so my manager knows I'm not coming."

| Persona | What changes for them | Whose numbers they see |
|---|---|---|
| **Employee** (incl. HR people and managers as employees, like Ritika) | The empty "Leave Balance" card becomes a "This month's leave credit" card. The Apply Leave list offers leave without pay. | **Only their own.** |
| **Employee in a zero class** (No Leave, 5-Day Week, Sundays Off, all Contract staff) | One honest sentence instead of an empty card. Can apply for leave without pay. | Only their own. |
| **Line manager** (the named leave approver) | Gets the request in the existing Inbox, with the existing line "N other people in this team are away on those days". Approves or declines. | Dates, days and type. **Not** the person's credits or pay. |
| **HR Manager** | Nothing new to learn. Credits for everyone are already in the desk report *Salary Components and Workings* (columns Leave earned / Leave used / Leave encashed). Can already apply on someone's behalf from the portal. | Everyone in their scope, through that report. |
| **CXO** | No change. | Same report, if they hold the access. |

## 2 · What the engine really does (checked in code — corrections to the brief I was given)

Read in `payroll_rules.py`, `payroll_month.py`, `payroll_slip.py`, `payroll_rules_apply.py`.

| Question | What the code does | Label |
|---|---|---|
| How are credits earned? | **By days attended, not by calendar.** Below 15 days attended in the month: nothing. From 15 days: class A earns 1 per 7.5 days attended (up to 4), B 1 per 10 days (up to 3), C 0.5 per 7.5 days (up to 2). The figures live in the rule set, not in code. | Confirmed |
| Do leave days count as attended? | **No.** A leave day and an absent day both add nothing to days attended. So taking leave also slows the credit, and can push someone under the 15-day gate. Example: class A, 26 days attended, 4 days' leave → 3 credits, not 4. | Confirmed |
| Does leave use credits first? | Yes, as the engine reports it (rule LB-02): credits cover approved leave first; the rest is "encashed"; leave beyond the credits is unpaid. | Confirmed |
| **Does that change the money?** | **No.** Paid days = days worked + all credits earned, whatever the leave. The code says the split into "used for leave" and "encashed" is *reporting, not arithmetic*. In rupees, an approved leave day and an absent day cost the same. The one exception: an **absence on a special day is charged double**; an approved leave on a special day is not. | Confirmed |
| Does a half day use 0.5? | **No.** Frappe marks a half-day leave as "Half Day". The engine ignores the leave and measures the day by punches: the missing half is charged as lost quarters (and may raise a red mark if the slab says so). It counts as a full day attended. With no punches at all, the day is held. | Confirmed |
| Is there carry-over? | **No.** Nothing carries forward; every credit is paid in the same month (LB-05). | Confirmed |
| Does the engine care about the leave type? | **No.** It reads only the attendance status "On Leave". Leave without pay and any other leave are treated the same. | Confirmed |

## 3 · Leave without pay: Surbhi's rule, and how the deduction happens exactly once

**The rule as stated:** no limit; salary is deducted; the only benefit is that management knows.

**What Frappe HR already gives (confirmed in `leave_application.py`):**
- A leave type with "Is Leave Without Pay" ticked needs no allocation and has no balance check.
- It **cannot be applied for a period whose salary slip is already submitted** (`validate_salary_processed_days`).
- On approval, Frappe writes "On Leave" attendance for each day. That is all the engine needs.
- Frappe HR creates a standard type called "Leave Without Pay" at setup (`hrms/setup.py`). Whether it still exists on dtc.alvoraa.co: **Needs validation.**
- The portal's preview already handles it ("This type is not drawn from an allocation").

**Approval flow (recommendation — all of it exists):** employee applies → status Open → the named leave approver (from the Employee or the department) sees it in the Inbox and by email if leave notifications are on → approves → Frappe writes the attendance. Nobody approves their own leave (already enforced). HR can apply on behalf of staff who have no login (already built).

**Why the deduction happens once — not twice, not never:**
- **Not twice.** The engine does not add a deduction. It *replaces* Frappe's paid days on the draft slip with its own count, built from attendance. Frappe's own leave-without-pay count is overwritten, not stacked. Confirmed (`on_salary_slip_validate`).
- **Not never.** An approved day is "On Leave" attendance, which earns no day credit. There is no other path to pay for it.
- **Two ways it can still go wrong — Risk:**
  1. If the rule set is not switched on, or the engine hook fails, the slip silently keeps Frappe's own figure. The LWP day is still deducted once, but the month's credits are missing, so the person is **underpaid**. The failure is logged to the Error Log only.
  2. Frappe's "Leave Encashment" request must stay switched off at DTC. Encashment is already inside paid days; an approved encashment request would **pay the same credit twice**. (The portal tab is feature-gated; **Needs validation** that it is off for DTC.)

## 4 · Cost ladder — what already exists, and the rung for each part

| Part | Rung | Why the cheaper rung was not enough |
|---|---|---|
| A leave type that needs no allocation | **Already there** (Frappe's Leave Without Pay) | — |
| Leave approvers for DTC staff | **Configuration** (data on Employee or Department) | — . **Needs validation:** are approvers set for DTC staff? With none, requests go nowhere. |
| No limit on LWP | **Configuration** (leave type maximums left at 0) | — |
| HR's view of everyone's credits | **Already there** (desk report *Salary Components and Workings*) | — |
| Manager's approval with team context | **Already there** (Inbox, `_part_leave_approvals`) | — |
| Apply list offers LWP when there is no balance | **New code, small** — one change where the list is built | The bug is in our portal code; no setting reaches it. |
| "This month's leave credit" card | **New code, small** — the leave summary the page already loads gains one block, read from `payroll_slip.month_summary` | Frappe's Earned Leave was rejected: it accrues by calendar, has no 15-day gate, and needs allocations, which Surbhi ruled out on 16 Oct. Writing the rules again in the portal was rejected: a second copy of the rules got all four cases wrong on 17 Oct (ux-learnings, banner). **The card asks the engine; it does not restate it.** |

No new DocType, page, setting, report, job or app.

## 5 · Existing surfaces (principle P8 — reuse before new)

| Surface | Today at DTC | Fate |
|---|---|---|
| Portal Leave page → "Leave Balance" card | "No leave allocations found for the current period." | **Extended**: the card shows the month's credit instead. Same place, no new page. |
| Apply Leave pop-up and its preview | "No leave has been allocated to you" | **Extended**: lists LWP. Preview already works. |
| Inbox → leave approvals | Works | **Kept** as is. |
| Desk report *Salary Components and Workings* | Shows leave earned / used / encashed per person | **Kept** — it is HR's and the CXO's answer. |
| My Finances → Leave Encashment tab | Feature-gated | **Must stay off at DTC.** |
| Attendance page, payslip | Work | **Kept**. |

## 6 · Kano class and competition

**Proxy, not survey.** Seeing your leave balance and applying for unpaid leave are **Must-be**: every product a DTC employee might compare us with has both `[recall — verify]`, and the founder read the empty card as a fault on first sight (**seen**, 21 Oct 2026). A credit built from attendance, explained in one line, is **Attractive** — it fits our "explainable derivation" whitespace. A survey of 5 DTC staff would settle it (questions in the open-questions table).

| Capability | Frappe HR | Zoho People | Keka | greytHR | Us after this slice |
|---|---|---|---|---|---|
| Balance on the employee's leave page | From allocations only | Per type, with accrual `[recall — verify]` | Per type, accrued to date `[recall — verify]` | Per type `[recall — verify]` | From the pay engine, earned to date |
| Unpaid leave with no limit | Standard LWP type | LOP type `[recall — verify]` | LOP type `[recall — verify]` | LOP type `[recall — verify]` | Frappe's LWP type |
| Credit tied to days attended, paid same month | No | Not seen | Not seen | Not seen | Yes, explained on screen |

**What we will deliberately not do that others do:** a rupee forecast on the leave page, a balance ring per leave type, and an encashment request form. At DTC encashment is automatic; a form would invite double payment.

## 7 · Persona enhancements through the portal

| Persona | Idea | Job it serves | In this slice? | Why |
|---|---|---|---|---|
| Employee | Credit card on the Leave page | "What will I be paid for this month?" | **Yes** | The core outcome |
| Frontline employee (phone) | The same card, readable at 360 px | Same, on a phone | **Yes** | Same card; no extra build |
| Zero-class / contract employee | One sentence + LWP in the list | Not to think the system is broken | **Yes** | Costs one sentence |
| Line manager | See the employee's credits when approving | Judge the request | **No** | Pay information about an individual; the team-away line is enough |
| Line manager | Warning when a request falls on a special day | Spot the double-deduction escape | **No — Decision D6** | Frappe's Leave Block List can do it by configuration if wanted |
| HR Manager | Credit card for the person picked in "apply on behalf" | Answer a phone call | **Later** | The desk report already answers it |
| CXO | Company leave-credit totals | Cost view | **No** | The desk report already sums it |

## 8 · The WOW

On the Leave page, where "No leave allocations found" sits today, an employee in class A on 21 October sees:

> **October leave credit** · Class A, up to 4 a month
> **2 earned so far** — from 18 days attended up to 20 Oct
> 1 used for leave on 6 Oct · **1 will be paid with your October salary**
> 1 day waiting for approval (24 Oct)
> *You earn 1 credit for every 7.5 days you attend, once you reach 15 days. Credits do not carry over.*

The rule line is built from the rule set's own fields, not typed into the page. Every number is the engine's.

## 9 · Thin slice

**Needed to validate now:** the card for the signed-in employee (read-only, from the engine); LWP in the Apply list.
**Needed before it can ship:** the LWP leave type and approvers confirmed on dtc.alvoraa.co; the rule set confirmed live there; the zero-class sentence; the decisions below.
**Worth doing later:** the card for HR's "apply on behalf" person.
**Not doing:** rupee forecast; manager or team credit view; any engine change (half days, special days); leave allocations or Earned Leave; Leave Encashment requests; a new page, report or setting; Hindi beyond the existing string mechanism.

**Out of scope, stated:** every tenant without a live rule set sees no card — unchanged. Whether they see LWP in the list is Decision D5.

## 10 · Run-side reality

No new app, worker, storage or public page `[ASSUMPTION — DevOps §1 missing]`. The card costs one engine read per page load: roughly one query per attendance day for checkins (about 30 a month) for one person. **Evidence required:** DevOps to confirm against `nfr-budget.md`.

## 11 · Success measures

| Measure | Baseline | Target | How measured |
|---|---|---|---|
| DTC leave applications filed through the portal per month | 0 — impossible today (confirmed in code) | Any non-zero in month 1; trend up | Count of Leave Application, company DTC, by creator |
| Share of DTC "not worked" days covered by an approved leave applied on or before the day | Baseline unknown — measure first | Up month on month (the "management is aware" outcome) | Attendance On Leave vs Absent, with the application date |
| Slips where paid days ≠ the engine's paid days, after LWP | Unknown | 0 in the first payroll month | The desk report against submitted slips |
| Card figure vs final payslip at month end | — | Identical for every employee | Same report, run on the last day |

## 12 · Thriving-workplace check

- **Engagement:** agency — a person can say "I'm off" and see what it costs, instead of being marked absent.
- **Collaboration:** the manager learns of an absence before it happens, at the moment it matters.
- **Inclusiveness:** staff without logins still depend on HR applying for them (exists). Contract staff get an honest sentence, not an empty card.
- **Transparency:** the employee sees how their own credit is worked out. Nothing about one person is shown to anyone new.

## 13 · Regulatory read (I am not a lawyer)

1. **Regime:** data protection (DPDP) lightly — pay-related figures shown only to their owner; employment law — deduction for absence.
2. **Whose obligation:** the employer's. This helps DTC show staff how pay was worked out.
3. **New possibility:** an employee sees a pay-related figure about themselves. No new data collected; no new visibility for anyone else.
4. **Front page test:** yes, we would defend it.

## 14 · Risks — red team

- **Mid-month alarm:** on the 10th everyone in class A shows 0 earned (under the gate). The card must say why, every time. Risk of support calls if the line is missing.
- **Held days** (missing check-out) do not count as attended, so credits look low. The card should name them — **Needs validation** with the designer.
- **Attendance lag:** the card is only as current as the last submitted attendance. It must say "up to <date>".
- **Special-day escape:** an approved leave avoids the double charge an absence would bring. Back-dated LWP could turn a doubled absence into an ordinary day. Decisions D2 and D6.
- **Half-day leave is charged as a short working day,** maybe with a red mark. Decision D4.
- **Back-dated approval after an absence was already submitted:** Frappe rewrites the status without re-running our attendance hook, so the stored daily verdict goes stale. Pay is still right (the slip re-judges), but daily screens may disagree for a day. Engineer to check.
- **Other tenants:** fixing the Apply list would show LWP to every tenant that has the type. Decision D5.
- **Hook failure** leaves Frappe's figure on the slip silently (§3).
- **Cheapest test before building:** run the desk report for October for 5 named DTC staff and read the leave columns aloud to Surbhi. If those numbers are what she would put on the card, build. If not, stop — the problem is the rules, not the screen.

## 15 · Decisions only Surbhi can make

| # | Question | My recommendation |
|---|---|---|
| D1 | The engine pays a leave day and an absent day the same, and uses credits for any leave first. So **one leave type is enough.** Should staff see it named "Leave Without Pay" (Frappe's own, no setup), or a DTC type named "Leave" that behaves the same? | **One type.** Keep Frappe's "Leave Without Pay" for the first release — it is your word and needs no setup — and let the card say "credits cover your first days of leave". Rename only if staff find it confusing. |
| D2 | Can staff apply for **past days** in the current month? | **Yes, until the month's slip is submitted** (Frappe already stops it after). Manager approval is the check. |
| D3 | Do **pending** requests count against the month? | **No.** Only approved leave counts, as in the engine. Pending is shown beside it in words: "1 day waiting for approval". |
| D4 | Offer **half-day** leave at DTC? The engine charges the missing half as lost quarters and may give a red mark. | **No half days at DTC in this slice.** Hide the box where the card shows. Fixing the engine is a separate decision. |
| D5 | Show leave without pay in the Apply list for **every tenant**, or only DTC? | **Every tenant.** Frappe allows it on the desk already; our list hiding it is the bug. |
| D6 | Should leave be **blocked or flagged on DTC's special days** (where an absence costs double)? | **Your call on policy.** If yes, it is configuration: put the special days on a Frappe Leave Block List. No code. |
| D7 | What does a **zero-credit** employee see? | "Your leave class (No Leave) does not earn monthly credits. You can still apply for leave without pay." |
| D8 | Show a **rupee** figure for the month's encashment, or days only? | **Days only.** Rupees move with marks and attendance until the last day; a changing rupee figure will cause more questions than it answers. |
| D9 | Does LWP need the manager's **approval**, or is telling them enough? | **Approval.** It costs nothing (it is Frappe's flow), and an approved day escapes the special-day double charge, so an accountable person should say yes. |

---

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| Is the DTC payroll rule set saved and **enabled** on dtc.alvoraa.co? If not, the card has nothing to read. | Surbhi / engineer | The card |
| Does "Leave Without Pay" still exist on dtc.alvoraa.co, with no maximums? | Engineer (read-only check) | The LWP part |
| Are leave approvers set for DTC staff (Employee or Department)? Is "leave approver mandatory" on in HR Settings? | Surbhi / DTC HR | Requests reaching a manager |
| Is the Leave Encashment feature off for DTC? | Engineer | Double-payment risk |
| How many DTC staff have portal logins? | Surbhi | Who can apply themselves vs through HR |
| UX scan `01a` and DevOps `07` §1 | UX designer, DevOps | The design step |
| Kano check: ask 5 DTC staff "If the Leave page showed your month's credit / did not, how would you feel?" | Surbhi | Turning the proxy class into evidence (does not block) |

## Assumptions

- `[ASSUMPTION]` The memory notes are right that DTC has no Leave Allocations by design and that classes A/B/C are the only rows in the rule set.
- `[ASSUMPTION]` The engine code in worktree `060-manager-review` is the code running (or about to run) at DTC.
- `[ASSUMPTION]` The 15-day gate in the rule set is 15 at DTC (the code's default; the rule set can change it).
- `[ASSUMPTION]` No new infrastructure, pending DevOps §1.
- `[ASSUMPTION]` Folder number 063: folders stop at 060, and 061 and 062 are already used by branch names.

## Kill criteria

- The desk report's leave columns for 5 named staff are not what Surbhi would show them → stop; fix the rules first.
- In the first month, the card's figure on the last day differs from the payslip for **any** employee → withdraw the card.
- Surbhi wants the card to show a flat 4 / 3 / 2 regardless of attendance → stop; that would be a second set of rules that disagrees with pay.

## Subtract pass

Removed on the final read: a manager-side credit view, an HR "apply on behalf" card, a special-day warning built in code (replaced by the configuration option in D6), a rupee forecast, a second credit-funded leave type, and a "next credit at N days" line (it would restate the rule). Kept the zero-class sentence: it costs one line and avoids the exact fault Surbhi reported.

## Handoff note

To the UX designer: extend the existing Leave Balance card and Apply pop-up; do not draw a new page. Design the 10th-of-the-month state (0 earned, under the gate), the held-days line, the zero-class sentence and the "up to <date>" line before the happy path. Every number must come from `month_summary`; the rule sentence must be built from the rule set's fields. To the engineer: the engine is type-blind and replaces Frappe's paid days — keep it that way; the test that matters is "2 approved LWP days → slip paid days equal the engine's, and nothing extra deducted".

---

## Decisions by Surbhi, 21 Oct 2026

Some differ from the recommendations above. Hers stand.

| # | Decision | Differs from recommendation? |
|---|---|---|
| D1 | Create a NEW DTC leave type named **Paid Leaves** (if it does not exist). It stands for the leave counted by the employee's leave class, which is worked out dynamically, so it is **locked: nobody can edit it**. Leave Without Pay stays as its own type. The Leave page shows Paid Leaves with the rule written out so employees understand it. | Yes - two types, not one |
| D2 | Past days in the current month can be applied for, until that month's salary slip is submitted. | No |
| D3 | **Pending requests DO count against the month**, until they are approved or rejected. The employee gets a clear message saying why. | **Yes** (recommended: no) |
| D4 | **Half-day leave is offered at DTC.** Engine risk to be designed around: it treats a half day as a short working day and may give quarters lost or a red mark. | **Yes** (recommended: no) |
| D5 | Leave Without Pay appears in the Apply list for every tenant. | No |
| D6 | Leave is **blocked on DTC's special days** (Frappe Leave Block List, configuration). | No |
| D7 | A zero-credit class sees: the class does not earn monthly credits; leave without pay is still available. | No |
| D8 | Days only, no rupee figure. | No |
| D9 | **Leave Without Pay needs NO approval**; management is told. No limit. | **Yes** (recommended: approval) |

Consequences to design for, not to argue with:
- D9 means an approved-by-nobody absence must not escape the special-day double charge. D6 (block on special days) must therefore cover Leave Without Pay too.
- D3 means the card shows credits held by pending requests, while the engine only counts approved leave. The card must label the figure as a projection.
- D4 means the card and the form must say plainly what a half day costs.
