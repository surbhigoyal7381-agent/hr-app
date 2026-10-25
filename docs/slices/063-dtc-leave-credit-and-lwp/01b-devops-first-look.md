---
slice: 063-dtc-leave-credit-and-lwp
artifact: 01b-devops-first-look (07 §1 equivalent)
author: hrms-devops-engineer
date: 2026-10-21
status: advice only - every Decision cell is blank for Surbhi
inputs: 01-product-brief.md incl. her nine decisions; nfr-budget.md; payroll_slip.py, payroll_rules_apply.py, payroll_month.py, hr_api.py (get_leave_summary); hrms leave_application.py and leave_block_list.py (all read in this worktree 21 Oct 2026); READ-ONLY queries on dtc.alvoraa.co, 21 Oct 2026
---

# 063 - DevOps first look

## Bad news first

1. **The DTC rule set is saved but switched OFF (enabled = 0, still a draft).** `month_summary` returns nothing for DTC today, so the card has nothing to read. The card cannot show a number until it is enabled, and enabling it also turns on the pay engine for the next slip. That is a payroll decision, not a card detail. (Fact: read on production 21 Oct 2026, last edited 17 Oct.)
2. **The leave-application flow has never been used at DTC.** Zero Leave Applications, zero Leave Allocations, zero Leave Encashments, ever. Every step of it (approver lookup, mailing, attendance writing, slip check) will run at DTC for the first time with D9, D4 and D6 all new at once. (Fact.)
3. **D9 (no approval) collides with a setting that is ON at DTC.** "Leave approver mandatory" is switched on, and 51 of 476 active staff have no approver (and no department has one). Those 51 cannot file any leave application today, and Frappe will refuse before our code runs unless the build gets round it. (Fact.)

## A. What the slice introduces

### A1. The Leave page reads `month_summary` on every load

| Question | Answer | Label |
|---|---|---|
| Cost in queries | One call does: rule set (cached doc), 1 holiday read, 1 shift-type read (22 shifts), 1 Attendance read, 1 Employee, 1 Salary Structure Assignment, **then per attendance day: about 3 reads** (shift fallback, Employee Checkin, Employee flags). A 30-day month is therefore roughly **100 queries**. | **Estimate** from reading the code; not timed. The brief's "about 30" undercounts. |
| Does it grow with headcount? | No, except one trap below. Per-person cost is the same for 20 or 400 people. | Inference |
| **Trap: whole green table loaded** | `month_summary` called without a prepared context calls `prepare()` with no employee, which reads the whole `Alvoraa Green Eligibility` table (one row per person, **363 rows at DTC**) to answer a question about one person. The code's own comment warns about exactly this. Recommend the page passes `employee=` to `prepare()`. | Fact (code). **P2.** |
| Payload | Small if trimmed (see A2). `MonthSummary` today carries about 30 fields. | Fact |
| Load today | **Only 10 of 476 active DTC staff have a portal login** (all 10 enabled). Even at 476 logins this is well under the 300-concurrent-user design figure and one page load per person per visit. | Fact: counted on production 21 Oct 2026 |
| Cache? | **No.** Rule: no cache until a timing misses the budget. Budget is 500 ms per API call and 2.5 s on a 3G phone. Measure first: time `get_leave_summary` for one DTC employee on dev with a full month of attendance. If it is under 500 ms, stop. If not, the first fix is to read Employee Checkin for the whole month in one query (1 query, not 30), not a cache. | Recommendation |
| If a cache were ever added | It must be dropped when attendance, a Leave Application, the rule set or Employee Checkin changes. That is four write paths for a number that must match the payslip to the rupee. **A stale card is the kill criterion in the brief.** Another reason not to cache. | Inference |
| Test to add | Assert the query count is the **same for 20 and 400 employees** (the NFR property), record the number. | `nfr-budget.md` section 2 |

### A2. Permission scoping and what the response must not carry

- **Employee reads only their own.** `get_leave_summary` already does this: a non-HR caller gets `_get_employee()` (their own record), and an HR caller passing `employee_id` is checked against the companies they look after (`_hr_target_employee`, SEC-13). Recommend the new block is added **inside that function, after `emp` is resolved**, never as a new endpoint that takes its own employee argument. (Fact: code read.)
- **Trim the response on the server.** `month_summary` returns `daily_rate`, `earning_basic`, `gross`, `net`, red deductions and incentive. D8 says days only. Hiding rupees in JavaScript leaves them in the network response, readable by the employee, and by an HR User who passes `employee_id`. **Recommend a fixed list of day fields only** (credits earned, used, held, days worked, class, up-to date). **P1 for the build**: a salary figure on the wire is a privacy fault, not a style one. (Fact: `MonthSummary` fields read.)
- **HR/CXO elsewhere** stay on the desk report *Salary Components and Workings*; no change to its permissions.
- **No `ignore_permissions` growth.** The existing list of applications already uses it, scoped to the one employee. The new reads should not add more.
- **Mid-month and pending numbers (D3):** pending credits shown must be labelled "projection". Pending Leave Applications are read for the same one employee only.

### A3. Leave Without Pay with no approval (D9), and half days (D4)

| Concern | What I found | Label | Advice |
|---|---|---|---|
| **How can it have "no approval" in Frappe?** | Frappe only writes "On Leave" attendance when a Leave Application is **Approved** and submitted. "No approval" therefore means the portal creates it already approved and submitted. That is new code (rung 4) and bypasses the approver logic for LWP only. | Fact (hrms code) / Inference | Say so plainly in the strategy. Keep it to LWP only, and only for the employee's own record. |
| **Mandatory approver blocks it** | See bad news 3. | Fact | Engineer to confirm what Frappe checks when the portal sets status Approved. **Needs validation on dev.** |
| **Abuse: unlimited, instant, self-approved** | Anyone can mark any day, including back-dated days, as unpaid leave and escape what an absence would cost (marks, and the double charge on special days). D6 is the only barrier. | Inference | Not a security hole, a policy hole. The cost lands on the employee's own pay in most cases, but a manager is not asked. Surbhi has chosen this (D9); record it as an accepted risk. |
| **Audit trail** | Frappe's Leave Application keeps owner, creation time, version history and (if enabled) comments. A self-approved record shows `leave_approver` empty or the employee. | Fact | Make sure the record says it was **auto-approved on filing** (a fixed remark, no new field), so a reviewer can tell it from a manager's decision. |
| **"Management is told"** | Frappe sends leave mail only when "Send Leave Notification" is on. It is ON at DTC. A mail to the named approver needs an approver; 51 staff have none. | Fact | For those 51, nobody is told. Recommend HR assigns approvers (configuration, rung 2) before go-live. Data fix, not code. |
| **Double deduction / under-payment** | Brief section 3 is right. Engine overwrites Frappe's paid days, so no double deduction from LWP. Under-payment happens if the rule set is **off**. It is off now. | Fact | Rule set must be enabled before LWP is opened to staff, or an LWP day is deducted by Frappe's own count while credits are missing. **P1.** |
| **Leave Without Pay type has "include holidays" = 1 at DTC** | A leave spanning a Sunday or special day counts that day as leave and writes On Leave for it. The brief's engine analysis never considered this. | Fact: read on production. Effect on pay | **Needs validation (engineer, on a copy):** apply 3 LWP days over a Sunday and compare paid days with the engine's. Do not change the setting (it is not ours to change) until this is known. **P2.** |
| **Leave Encashment** | None exist, and `allow_encashment` is off on all three DTC leave types. | Fact | Double-payment risk is closed today. Recommend a one-line check in the release checklist. |
| **Half day (D4)** | Frappe writes status "Half Day"; the engine ignores it and judges the day by punches. A half day with full punches is paid in full and nobody notices; a half day with half the punches costs lost quarters and maybe a red mark, as the brief says. | Fact (brief, code) | Data-integrity risk is on the **over-pay side** as much as the under-pay side. The form must say what it costs (already in the brief). Add a test: half-day leave, full punches, expect paid days. |
| **Back-dated approval after a slip draft** | Frappe stops LWP for a period whose slip is **submitted**. A draft slip can still be regenerated. | Fact | Fine. Test: LWP on a day in a month with a draft slip, then re-run the slip. |

### A4. Does a Leave Block List on special days (D6) cover Leave Without Pay?

**Yes in part, but not the way the brief assumes. Two traps.** (Fact: `leave_application.py` and `leave_block_list.py` read.)

1. **Frappe only refuses a block date when the application is Approved.** On an Open application it shows a warning and lets it through. For D9 the portal files LWP as Approved, so the refusal does fire. If the build ever files LWP as Open first, the block does nothing.
2. **A list that names no leave type applies to every leave type including LWP.** A list pinned to one type does not. So the list must have the **leave type left blank** to cover LWP. (Fact: block list code filters on type only when one is given.)

Other facts:

- The list applies per company (all departments ticked). No Leave Block List exists at DTC yet. (Fact.)
- **Users on the list's Allow table are exempt.** Keep it empty, or HR could approve on a block date.
- **There are two special-day lists at DTC**: "DTC Special Days 2026-27" and "DTC Special Days FY 2026-27", 3 dates each. The rule set uses the first. (Fact.) A block list is a **second copy** of the dates. Add or move a special day in one place and the other drifts. Recommend building the block list from the rule set's list once, and writing the "two places" fact in the release notes. Not a script.
- **Policy tension for Surbhi (not mine to settle):** blocking leave on a special day means the person cannot tell management in advance, and then an absence on that day is charged double. D6 therefore removes the "management knows" benefit on exactly the days it matters most. Worth one sentence to her.

### A5. A locked DTC leave type "Paid Leaves" (D1)

| Question | Answer | Label |
|---|---|---|
| Does it exist? | **No.** DTC has Compensatory Off, DTC Compensatory Leave and Leave Without Pay only. | Fact |
| How do you lock it? | Leave Type is a standard Frappe doctype. Employees already have no write rights (checked: only HR Manager and HR User can edit). So "locked" means **HR Manager/HR User can still edit it** unless we add a rule. A lock beyond that is new code on a Frappe doctype (a hook), for no benefit I can name. | Fact / Inference |
| Advice | **Do not build a lock.** Create the type as a fixture or a one-time patch in our app, with a clear name, and accept that HR could edit it. If she insists, set `read_only` through a Property Setter on that tenant, which survives upgrades. | Recommendation, rung 2 |
| Upgrade safety | A new Leave Type **record** is data, not a change to Frappe or HRMS code. `bench update` does not touch it. Rule 7 (never redefine a Frappe doctype) is not broken. A patch that inserts it must be safe to run twice (check by name first). | Inference |
| Other tenants | A patch in our app runs on **every** tenant on migrate. It must be scoped to the company with the live rule set, or other tenants would get a "Paid Leaves" type they never asked for. **Recommend creating it from the rule-set activation step or a DTC-only patch**, never a global one. | Recommendation, **P2** |
| Does the engine care about type? | No, it reads only "On Leave" attendance (brief section 2). So "Paid Leaves" is a label. Nothing breaks if HR edits or deletes it, apart from the Leave page card, which must handle a missing type. | Fact (brief, code) |
| Allocations | The type needs no allocation and must not be given one. Frappe's balance check would otherwise stop applications. Confirm "Paid Leaves" shows in the Apply list on a type with no balance (that is the same code fix as LWP). | Inference |

## B. Open checks, answered from read-only looks at dtc.alvoraa.co (21 Oct 2026)

I ran one read-only Python script through the approved route. Nothing was written, no bench command was run, nothing under `/var/www/html/hr-app` was touched. Counts and names only.

| Open check | Answer | Label |
|---|---|---|
| Payroll Rule Set for DTC saved and enabled? | **Saved, NOT enabled.** One record, "Durga Trading Company", draft (docstatus 0), enabled = 0, last edited 17 Oct 2026. Special-day multiplier 2, 15-day gate, special-day list "DTC Special Days 2026-27". | Fact |
| Leave Type "Leave Without Pay"? | **Exists.** is_lwp = 1, max leaves allowed = 0 (no limit), no max continuous days, no encashment, **include holidays = 1**, created by Administrator 18 Sep 2026. | Fact |
| Leave Type "Paid Leaves"? | **Does not exist.** | Fact |
| Which leave types exist, are they used? | Three: Compensatory Off, DTC Compensatory Leave, Leave Without Pay. **No Leave Applications at all, in any status. No Leave Allocations.** | Fact |
| Leave approvers set? | **425 of 476 active employees have one; 51 do not.** No department has a leave approver set (0 of 19). "Leave approver mandatory" is **ON**. Leave notifications **ON**. Backdated-leave restriction OFF. | Fact |
| Leave Encashment used? | **No.** Zero Leave Encashment documents. `allow_encashment` is off on all three leave types. | Fact |
| Leave Block List? | **None.** | Fact |
| Holiday Lists for special days? | **Yes, two:** "DTC Special Days 2026-27" and "DTC Special Days FY 2026-27", 3 dates each (the rule set uses the first). Also 5-Day Week (105 dates), Sundays Off (53), and a Holidays list (1). | Fact |
| DTC staff with enabled portal login (User linked via Employee.user_id)? | **10** (all enabled). 466 of 476 active employees have no linked user. | Fact |
| Headcount | 476 active employees, all in Durga Trading Company. The brief's "363 grants" is the Green Eligibility row count, not headcount. | Fact |

**What this means for the brief's "Open checks":** the LWP type is there and unlimited (good); approvers, the rule set and the block list need action before staff use any of this; Encashment is safe.

**Reach:** only 10 people can use the Leave page card themselves. For everyone else, HR files on their behalf. That should shape how much effort the card deserves, and I would say so to Surbhi before the design step. (Inference.)

## C. Top risks, in order

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-1 | Do not open LWP or show the card to DTC staff until the rule set is **enabled and proven on a copy** (`REHEARSAL.md` style: one month of real attendance, compare engine against slip). | The rule set is OFF. LWP then deducts through Frappe's count with no credits: staff under-paid, silently. | Wrong salaries on the first slip. | **P1** | |
| OPS-2 | Trim the leave summary on the server to day fields. No rupee fields on the wire. | `MonthSummary` carries daily rate, gross and net. | A salary figure readable by anyone who opens the network tab. | **P1** | |
| OPS-3 | Settle approvers: assign them to the 51 staff, or decide how the portal files LWP when "approver mandatory" is on. | D9 collides with the setting. | LWP fails for 51 people, or is filed with no one told. | **P2** | |
| OPS-4 | Test on a copy: LWP over a Sunday, with "include holidays" = 1. | Paid weekly off could be lost or counted twice. | Pay error that appears only in a month with a Sunday inside a leave. | **P2** | |
| OPS-5 | Block list: leave type blank, Allow table empty, dates copied from the rule set's list, file LWP as Approved. | Otherwise the D6 block does not cover LWP. | Special-day escape returns. | **P2** | |
| OPS-6 | Pass `employee=` into `prepare()` on the page. Time one call on dev before anything else is added. | Reads 363 rows to answer for one person. | Wasted work on every load. Small today (10 users). | **P2** | |
| OPS-7 | Create "Paid Leaves" for DTC only, as data, no code lock. | A global patch would add it to every tenant. | Clutter on other tenants. | **P3** | |
| OPS-8 | Ask Surbhi: D6 blocks the one day management most needs to hear about. | Policy tension, see A4. | A decision made without seeing the cost. | **FYI** | |

## What the build needs from DevOps later (so it is not a surprise at section 3)

- No new container, queue, job, volume, app or dependency. **Fact:** the plan as written needs none.
- Release order for DTC: approvers fixed (data) -> rule set rehearsed on a copy -> rule set enabled -> block list made -> code deployed -> card checked on a fresh month. The code can ship before the rule set is enabled; the card then shows nothing, and no one is hurt.
- Rollback: redeploy the previous tag with migrations off; the data created (Paid Leaves, block list) is harmless to leave in place. Real rollback time must be measured, not assumed (lesson 22).
- Dev push freeze context from memory (Amata demo) has passed; I did not check for any current freeze.

## Not checked

- No timing was taken (no bench or dev run). Query counts above are read from code.
- I did not check the dev site, nor what `dev.alvoraa.co`'s DTC copy looks like.
- I did not check whether the portal's Leave Encashment tab is feature-gated off at DTC (the doctype is empty, which is what matters for payment).
- I did not check HR Settings fields on the Employee/Department approver fallback behaviour inside Frappe when the department list is empty (0 of 19 set).

## Subtract pass

Removed: a recommended cache with an invalidation plan (no measurement justifies it); a Property-Setter-based lock as a first choice (kept only as the fallback if she insists); a monitoring/alert idea for LWP volume (no NFR needs it yet); a plan for a block-list sync script (two copies of three dates do not need a script). Nothing else.
