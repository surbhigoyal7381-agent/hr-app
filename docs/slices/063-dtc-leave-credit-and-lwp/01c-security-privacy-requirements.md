---
slice: 063-dtc-leave-credit-and-lwp
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-10-21
status: draft, revision 3 (21 Oct 2026, after Surbhi's final answers) - written before the functional spec
inputs: 01-product-brief.md (incl. its last three sections, final answers 21 Oct 2026; 01d-half-day-addendum.md; 01e-credit-at-start-of-month-addendum.md; "Decisions by Surbhi", D1-D9, and "Changes by Surbhi ... later the same day"); 01b-devops-first-look.md; 02-design.md (U1-U8); prototype-v1.html; security-compliance-baseline.md; compliance-feature-map.md; memory legal-retention-rules-2026-09.md; 060's 01c as the model. Code read in worktree 060-manager-review on 21 Oct 2026. One read-only script on dtc.alvoraa.co, 21 Oct 2026 (settings and counts only, no names, nothing written).
---

# 063 · Security and privacy requirements: Paid Leaves card, and Leave Without Pay with no approval

*I did not write the brief or the design. I am specifying here, not reviewing. SEC-8, SEC-13 and
PRIV-1 are my own mechanisms, so at `06` somebody other than me should check them.*

## Revision 3 - Surbhi's final answers (21 Oct 2026). This box wins over everything below.

| Her answer | Effect here |
|---|---|
| **Credits given on the 1st** (A 4, B 3, C 2), 15-day minimum stays (01e) | **SEC-1** keys changed: `credited`, `used`, `waiting`, `to_be_paid_out`, `attended_so_far` (+ `gate` only while under 15). `period`, `gain`, `earned` and the "up to" date are dropped. The card carries **less** pay-derived data. SEC-2 unchanged |
| **HR approves leave without pay** | **SEC-3 rewritten:** for LWP only, any HR user whose `permitted_employees()` covers the employee may approve. Self-approval stays refused. Paid Leaves keep the named-approver rule. **SEC-12** now applies to Paid Leaves only. Q3 answered |
| **Special days: leave allowed if approved** | **SEC-5 DROPPED**, with the Leave Block List and its release checks. The risk this leaves is in Residual risk |
| **Limit 5 a calendar month** | SEC-13 unchanged, and now explicitly **DTC only** |
| **Everything is DTC only** | **New SEC-15:** one test of "is this DTC" - the employee's company has an **enabled** rule set - used by every rule here |
| **Half-day leave: the other half's punches decide; a missed punch goes through the existing correction flow HR approves; no green mark** | **New SEC-16.** No new permission path. **New blocker:** in code, the existing flow writes nothing on a half-day leave date (below) |
| **E6 (approved Paid Leaves count toward the 15) and the half-day engine change** | **New SEC-14:** pay-affecting changes proven by rehearsal on a local copy; the rule-set settings change is a data change with a written rollback |
| **Notice: "all higher level managers in the hierarchy"** | PRIV-1 stays (Reports To chain, cap 10, loop-safe). Now explicit: **never the type, the approver or a job title. No cancellation notice** until she asks. Q6 (b) answered: no |

**New finding (Verified in code), and it blocks the half-day part:** Frappe's Attendance Request
**writes nothing** on a date covered by an approved half-day leave:
- A correction that does not tick "half day": `should_mark_attendance` finds the approved leave and
  skips the date (`hrms/.../attendance_request.py:233-240, 244-255`).
- A correction that does tick "half day" for that date: the status is already "Half Day", and the
  leave already set the other half to "Present" (`leave_application.py:349-371`). So neither
  branch at `attendance_request.py:169-209` changes anything.
- And the engine judges the day by **punches** in Employee Checkin, not by the status
  (`payroll_rules_apply.py:380`). A correction that only changes a status would not move pay
  anyway.

So, as far as I can read, "apply for HR to approve the regularisation" **does not change the
engine's answer** for the other half of a half-day leave day. The day then stays half absent
(doubled on a special day). I could not run it. The only path I found that feeds the engine a
missing time is the held-day confirmation (ATT-06: `alvoraa_held_confirmed` and
`alvoraa_confirmed_out_time`, `payroll_rules_apply.py:382-388`), and that covers a missing
check-out only. **The rehearsal must prove the remedy works before the half-day rule ships
(SEC-14 item 9).** If it does not, Surbhi has to choose a remedy (Q7).

## Revision 2 - what Surbhi's later changes did to this file

Her later decisions (brief, last section) override D2 and D9. **Where this file and the text
below disagree, this box wins.**

| Her change | Effect here |
|---|---|
| **HR approves Leave Without Pay** (D9 reversed) | **Removed:** SEC-4 (the self-approval exception), the no-approval half of SEC-3 and SEC-5, PRIV-4 (the "recorded without approval" marker), Q1. `refuse_own_submit` stays exactly as it is. Every leave is filed **Open** and approved by someone else |
| **LWP limit: 5** (default 5 days per calendar month, pending + approved, half day = 0.5) | **New SEC-13**, enforced on the server at every door |
| **Current month only, never before** (U6 = no) | **SEC-6 tightened** |
| **Both HR and the employee can cancel** | **SEC-8 rewritten.** Withdrawing an Open request uses Frappe's own `discard` and needs no bypass. Cancelling an **approved** leave is the only part that needs one (`hr_api.py` 69 to 70) |
| **On HR approval, every manager up the Reports To chain is told** | **PRIV-1 rewritten** as a personal-data flow |
| Q1 moot | Removed |

**Removed sections, and why:** §0 points 1 and 4 (no self-approval, no no-approval path any
more); the abuse-case rows about recording without approval; the "recorded" status word.
Kept unchanged: SEC-1, SEC-2 (one table cell), SEC-7, SEC-10 (its LWP cases now mean approved
LWP), SEC-11, PRIV-3, PRIV-5, PRIV-6. Updated: SEC-9 (ceiling 70), SEC-12 (now every type),
PRIV-2 (no "Recorded" tag). New: SEC-13, Q3-Q6, finding §10 point 3.

**Two new facts, checked read-only on dtc.alvoraa.co, 21 Oct 2026 (Verified by running it):**
- **3 of the 10 DTC logins have no User Permission on their own Employee.** All 3 hold an HR
  role, so today they see nothing they could not already see. But Leave Application has **no
  row-level permission hook** (checked in `hrms/hooks.py:155-180`), and the Employee role has
  read and write on it with no "only if owner" rule. So for a plain employee, "only my own leave"
  depends on that User Permission row existing. A non-HR login without one could read every
  reason and withdraw anyone's Open request through REST. Not live today; it becomes live the
  first time a non-HR login is made without that row. SEC-8 and a release check cover it.
- **The Reports To chain at DTC is short and clean:** longest chain 2 steps above the employee,
  **no loops**, no chain that ends at a non-active person, 7 distinct managers, all with enabled
  logins. (Counts only.)

**Decisions treated as settled:** D1-D9 (Surbhi, 21 Oct 2026), and her design approval the same
day. **Treated as accepted but flagged for her to confirm:** U1-U8. **Still open, and every
requirement below holds whichever way she answers:** (a) whether "Paid Leaves" is locked by
wording or by code; (b) the 51 DTC staff with no leave approver; (c) the special-day block
covering Leave Without Pay.

---

## 0 · Bad news first

**1. [REMOVED in revision 2 - D9 reversed.]** It said D9 needed a hole in `refuse_own_submit`
(`access.py:184-190`). HR now approves, so the guard stays exactly as it is - and it now
**protects** this slice: nobody approves their own leave, on any door.

**2. At DTC, Frappe's "salary already processed" guard has never fired, so it bounds nothing.**
DTC has **no salary slips in the system at all** - 0 submitted, 0 draft. *(Verified by running it,
21 Oct 2026.)* D2 says "past days until the slip is submitted". With no slips, that means "any
past day, back to the joining date". And Frappe's guard only covers Leave Without Pay types anyway,
not "Paid Leaves" (`leave_application.py:387-389`). **Our code must set the date bound itself.**
SEC-6.

**3. Two things the DevOps first look says are not quite right, and they change the controls.**
- *"Approver mandatory" does not refuse anything on the server.* It is enforced only by the desk
  form's JavaScript (`hrms/.../leave_application.js:25-36` sets the field required). The server
  `validate` never reads the setting, and `leave_approver` is not required in
  `leave_application.json`. *(Verified in code.)* So the portal will happily file a request with no
  approver, and it will sit with nobody able to act on it. SEC-12 closes that.
- *Leave Application keeps no version history.* `track_changes` is off in
  `leave_application.json`, and DTC has no Property Setter that turns it on. *(Verified in code and
  by running it.)* What makes the record trustworthy is that a submitted record cannot be edited.
  That is enough here (rev. 2: PRIV-4's marker is no longer needed).

**4. [REMOVED in revision 2 - Q1 is moot.]** Nothing is recorded without approval at any tenant.

**5. (Revision 2) "HR approves" does not match how approval works in this portal today.** The
portal lets only the **named leave approver** act (`_can_action_leave`, `hr_api.py:967-997`) and
deliberately refuses "any HR Manager". At DTC the named approvers are mostly branch heads. So
"HR approves LWP" needs one of three things, and they differ in security: Q3.

None of these is a leak today. Nothing in this slice is live.

---

## 1 · What I checked, and how

| Fact | Where | Label |
|---|---|---|
| `get_leave_summary` gives a non-HR caller only their own record; HR with `employee_id` is checked against their companies | `hr_api.py:2233-2241`, `_hr_target_employee` `2214-2230` | Verified in code |
| `_get_employee` requires `status = "Active"`, so a leaver gets nothing | `hr_api.py:260-268` | Verified in code |
| `apply_leave` is the **only** place our code creates a Leave Application | grep of all `.py` in `alvoraa_portal` and `alvoraa_hr_core` | Verified in code |
| `apply_leave`: a non-HR caller who passes `on_behalf_of` is **silently** filed for themselves | `hr_api.py:2385-2388` | Verified in code |
| `MonthSummary` carries `daily_rate`, `earning_basic`, `gross`, `net`, `red_deduction`, `green_earning`, `mark_rate`, `incentive`, `other_deductions`, `notes` | `payroll_month.py:46-88` | Verified in code |
| `month_summary` returns `None` unless the company's rule set is **enabled** | `payroll_slip.py:55-57`, `rule_set_for` `payroll_rules_apply.py:59-69` | Verified in code |
| Only System Manager can edit the rule set; HR Manager reads it; edits keep a Version row | `alvoraa_payroll_rule_set.json` (permissions, `track_changes: 1`) | Verified in code |
| DTC rule set: one record, draft, **enabled = 0** | read-only query | Verified by running it, 21 Oct 2026 |
| Employee role on Leave Application: create and write, **no submit, no cancel**; `status` is permlevel 1, which Employee cannot write | `leave_application.json`; DTC Custom DocPerm | Verified in code and by running it |
| DTC has a custom role **Location Manager** with submit and cancel (no create) on Leave Application | DTC Custom DocPerm | Verified by running it |
| Frappe refuses a leave over a day already marked Present | `leave_application.py:627-654` | Verified in code |
| A Leave Block List refuses only when the application is **Approved**; a list with no leave type covers every type; users on its Allow table are exempt | `leave_application.py:423-429`, `leave_block_list.py:77-115` | Verified in code |
| Approving writes or overwrites the Attendance row by `db_set`, so an earlier "Absent" leaves no trace | `leave_application.py:346-359` | Verified in code |
| Frappe's standard leave email template carries name, type, dates and status, **not the reason**. DTC's two templates do not mention `description` | `leave_application_email_template.html`; read-only query | Verified in code and by running it |
| DTC HR Settings: self-approval prevention **off**, approver mandatory **on**, leave notifications **on**, back-dated restriction **off** | read-only query | Verified by running it |
| DTC: 7 HR users, **0** with a Branch User Permission; 12 users with the Leave Approver role; 0 Notification records on Leave Application; 0 Leave Block Lists | read-only query | Verified by running it |
| `hr_api.py` has **69** `ignore_permissions` in code - exactly its ceiling of 69. No headroom | counted the same way as `test_portal_security_010.py:810-844`; ceiling at line 740 | Verified by running it |
| Leave Type keeps a Version row on every edit; only HR Manager / HR User can edit | `leave_type.json` (`track_changes: 1`, permissions) | Verified in code |
| Leave Block List keeps **no** Version row | `leave_block_list.json` | Verified in code |

---

## 2 · Threat model, four lines

**Who wants this, and what is the cheapest way?** Not an outsider. (1) An employee who did not come
in and wants the day to read as notified leave, after the fact - cheapest by back-dating an LWP
(rev. 2: an approver must now say yes, and SEC-6 limits it to the current month). (2) An employee
avoiding the **double charge on a special day** by getting leave approved for it - rev. 3: allowed by Surbhi when approved; an HR user in scope decides. (3) Anyone curious about a colleague's pay - cheapest by reading the network response
of the leave page, which would carry the daily rate and net pay if we sent `MonthSummary` whole.
(4) An HR person, or a script calling the API, filing unpaid leave **for someone else** - a pay cut
the person may never see, since 466 of 476 DTC staff have no login. (5) Rev. 2: the **notice up the
chain** tells more people about every absence than before (PRIV-1).

**Blast radius of one mistake.** Cross-tenant: not reachable; one tenant per site and every read is
keyed on the caller's own Employee. Wrong-person pay: one employee per record. The top of the scale
is **one company's payroll month**: if the gate in SEC-2 fails, Paid Leaves and LWP
open to all 476 DTC staff before the engine that prices them is on. If the response trim in SEC-1
fails, every user who opens the leave page sees their own rupee figures (not someone else's - the
endpoint has no other-person path for the card).

**What becomes possible that was impossible before.** Rev. 2: no-approval is gone. New are:
a pay-derived figure (credits) on the employee's screen; an employee cancelling an approved leave
(SEC-8); and every manager up the chain hearing of every approved absence below them (PRIV-1).

**How would we find out?** The record itself is the evidence: who filed it (`owner`), who approved it
(the submit), who cancelled it (`modified_by` on `docstatus 2`). A back-dated one shows `creation`
after `from_date`. The chain notices are a second witness. **What we would not see:**
an HR user's edits to the Leave Block List (no Version row) and any change to the special-day list
outside the rule set. Rev. 3: no block list any more; special-day leave is allowed when approved.

---

## 3 · Data inventory

Classes follow `compliance-feature-map.md` A1. A1 is not built, so they are declared here and
applied by hand.

| Field or object | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| Credit figures on the card (rev. 3): class, credited this month, used, waiting, to be paid out; days attended and the 15-day minimum only while under 15; held days and their dates | **sensitive** (pay-derived) | Tell the employee what this month's leave is worth in days (D8) | **Not stored.** Worked out on each load, never cached or copied (PRIV-3) | The employee, about themselves. Nobody else through this endpoint |
| `MonthSummary` rupee fields (`daily_rate`, `earning_basic`, `gross`, `net`, `red_deduction`, `green_earning`, `mark_rate`, `incentive`, `other_deductions`) and `notes` | **sensitive** (pay) | Price the slip | Not stored by this slice | **Never leaves the server on this path** (SEC-1) |
| `Leave Application` - employee, type, dates, half day, status, days | sensitive | Record leave that changes pay | Existing; **statutory minimum unknown**, Q-C1 | The employee; their leave approver; HR within scope |
| `Leave Application.description` (the employee's reason) | sensitive, and health-adjacent when it names an illness | Context for the approver | As above | The employee, the approver, HR. **Never in a notice, a log or an error** (PRIV-1, PRIV-5) |
| `Attendance` rows written by the leave | sensitive | Feed the pay engine | Existing | As today |
| Notice up the Reports To chain on approval (rev. 2) | sensitive, and the email leaves our servers through Brevo | Managers know who is away | Email Queue and Notification Log as Frappe keeps them; the copy at Brevo and in the inbox is outside our control, which is why the body is minimal | Every Active, enabled manager above the person, at most 10 steps (PRIV-1). Name, dates, days only |
| Leave Type "Paid Leaves" | internal | Name the leave the class pays for (D1) | Life of the tenant | Everyone who can read Leave Types |

**Nothing new is collected about anyone.** The card shows the employee figures the engine already
works out about them. The notice moves existing data to a person already entitled to it.

---

## 4 · Access intent, including who must NOT see what

| Actor | May | Must NOT |
|---|---|---|
| Employee (incl. HR people and managers as employees) | See their own card. Ask for LWP (limit SEC-13) or Paid Leaves. Withdraw their own Open request; cancel their own approved leave before it starts (SEC-8) | See anyone else's card, credits or leave. Receive any rupee figure through the leave page. File or cancel leave for anyone else. Cancel an approved leave that has started. Get leave approved on a special day, or before the 1st of the current month |
| Leave approver / Location Manager | Approve or decline for people they are named approver for (as today, Paid Leaves; rev. 3: LWP is approved by HR in scope, SEC-3) | See the employee's credits, class or pay. See the reason in the notice (they may read it on the record, as today). |
| Managers up the Reports To chain (rev. 2) | Receive the approval notice: name, dates, days. See that the person is on leave in Team View, as today | See the type, the reason, credits or pay (PRIV-1, PRIV-2; 045 AC-76 stands) |
| HR Manager / HR User | File LWP or Paid Leaves **on behalf**, and cancel within scope; approve LWP in scope (SEC-3, rev. 3), for employees inside `permitted_employees()`. Read credits through the desk report, as today | Get the card for another person through the portal (brief: "later"). Act outside their companies **or branches**. Approve their own leave (SEC-3) |
| System Manager | Enable the rule set (which opens this slice - SEC-2) | Enable it without the rehearsal evidence (process control, SEC-2) |
| A non-HR caller passing `on_behalf_of` | Nothing | Have the call quietly turn into a record about themselves (SEC-7) |
| Leaver with a live login | Nothing (`_get_employee` filters Active) | Anything on these paths |
| Guest | Nothing | Reach any endpoint here. None may be `allow_guest` |

**New-Frappe-app checklist: not engaged.** No app is installed. No public page, no guest access, no
self sign-up, no new role.

---

## 5 · Obligations engaged

I am not a lawyer. These are engineering readings of published sources.

| Obligation | What it asks of this slice | Source and date checked |
|---|---|---|
| **DPDP Act 2023 + Rules 2025 - reasonable security safeguards; purpose limitation; minimisation** | Pay figures only to their owner; no rupee field on the wire when days are enough; no new copy | Baseline §2, verified 24 Aug 2026 (58 days old - inside the 90-day rule, not stale) |
| **DPDP - phase dates and our role** | Unchanged and still open: fiduciary vs processor, exact phase dates | Baseline §2 open questions - counsel |
| **Code on Wages, 2019** - in force from 21 Nov 2025; its records provisions (ss. 43-66) are in force | An approved LWP is a deduction for absence: the record of it is a wage record. **The minimum period to keep it is not verified** | Secondary sources read 21 Oct 2026 (indiacode.nic.in text not read; Central and State Rules status disputed between sources). **Counsel, Q-C1** |
| **Counsel's retention rules of 18 Sep 2026** | Cover driver GPS and performance records only. They **do not cover** leave or attendance. Do not apply the 6-month rule to these by analogy | Memory `legal-retention-rules-2026-09.md` |
| **CERT-In 180-day log residency** | Unchanged gap (baseline §3a). This slice adds no new log stream | Baseline §3, verified 24 Aug 2026 |
| **OWASP ASVS 5.0 L2** - access control on every request; no sensitive data in responses beyond need | SEC-1, SEC-3, SEC-7 | Baseline §5 |

**DPIA: not needed for this slice.** No new collection, no systematic evaluation, no new recipient
outside the employment relationship. I would change that answer if the card ever showed rupees or
reached a manager.

---

## 6 · Abuse cases

| Who | Tries | What stops it |
|---|---|---|
| **Curious colleague** | Calls `get_leave_summary` with a colleague's employee id | A non-HR caller is always resolved to themselves (`hr_api.py:2237-2240`). SEC-1 test (d) |
| **Curious colleague** | Opens the network tab to read a daily rate | SEC-1: rupee fields never leave the server |
| **Employee** | Did not come in on a special day; asks for LWP for it the next morning | Rev. 3: allowed if an HR user in scope approves it, inside the current month (SEC-3, SEC-6). Accepted trade-off |
| **Employee** | Asks for LWP for a day in last month | SEC-6: refused at filing and at approval, on every door |
| **Employee** | Files 6 days of LWP this month through REST, around the portal | SEC-13: the check is on `validate`, so REST meets it too |
| **Employee** | Calls the API with `status: "Approved"` | SEC-3: always filed Open |
| **Employee** | Cancels an approved Paid Leaves day from last week through `frappe.client.cancel` | No cancel permission (Frappe); SEC-8 test (d) pins it |
| **Employee with an HR role** | Approves their own LWP on the desk | `refuse_own_submit`, unchanged (rev. 2) |
| **Over-scoped manager** (Location Manager has submit and cancel on Leave Application at DTC) | Approves a Paid Leaves request on a special day | Rev. 3: allowed by policy. Only the named approver can, and never for themselves |
| **Over-scoped HR** (a store's HR person, if one is ever given a Branch permission) | Files LWP for someone in another store | SEC-7: on-behalf recording checks `permitted_employees()`, which includes the branch |
| **Script or mistake** | A non-HR call with `on_behalf_of` | SEC-7: refused, not silently filed for the caller |
| **Departing employee** | Asks for LWP for their last weeks | Normal approval; the limit applies. Once they are not Active, `_get_employee` returns nothing |
| **Guest** | Any of it | No endpoint here is `allow_guest` |

---

## 7 · Requirements

Each says what must be true and how a test proves it. The analyst must trace every one to an
acceptance criterion, or record Surbhi's decision not to adopt it.

### Security

**SEC-1 · The card is the caller's own, and carries days only - a fixed list of fields.**
The credit block is added **inside `get_leave_summary`, after `emp` is resolved, and only when
`emp` is the caller's own record** (not when HR passes `employee_id` - the brief puts the
on-behalf card "later"). No new endpoint, and nothing that takes its own employee argument. The
block is built by **naming each field it sends**, never by converting `MonthSummary` to a dict
and removing some. **Allowed (rev. 3, matching spec 7.5 and 01e section 7):** `month`, `class`,
`earns` (class `monthly_credits` > 0 and the category earns), `credited` (the class's
`monthly_credits`), `used`, `waiting`, `to_be_paid_out`, `attended_so_far` and `gate` (**only
while under 15 days**), held-day count and dates. **Dropped in rev. 3:** `earned`, `period`,
`gain`, `cap` as a separate key, and the "up to" date. **Never:** `daily_rate`, `earning_basic`, `gross`, `net`,
`red_deduction`, `green_earning`, `mark_rate`, `incentive`, `other_deductions`, `reds`, `greens`,
`free_reds`, `deductible_reds`, `total_quarters`, `paid_days`, `notes`, or the Basic it was
priced from. `prepare()` is called with `employee=` (OPS-6), which also keeps every other
person's green grants out of memory for this request.
*Test:* (a) the block's keys **equal** the allowed set exactly - a field added to `MonthSummary`
later fails this test rather than leaking; (b) with a Salary Structure Assignment base of
31,000, the serialised response contains neither "31000" nor the daily rate string; (c) HR
passing `employee_id` gets no credit block; (d) a non-HR caller passing a colleague's id gets
their own figures; (e) a leaver's login gets `no_employee`.
*Observable only if* the fixture has an **enabled** rule set and a non-zero base. Without them
every rupee field is 0 and test (b) proves nothing.

**SEC-2 · Nothing in this slice is reachable where the pay engine is set up but switched off.**
One check, in one place, used by the card, the Apply list and `apply_leave`:

| Company state | Card | Paid Leaves | LWP |
|---|---|---|---|
| Rule set exists and is **enabled** | shown | offered | offered, filed Open, approved by someone else; limit SEC-13 (rev. 2) |
| Rule set exists but is **not enabled** (DTC today) | not shown | **not offered, and refused by the server** | **not offered, and refused by the server** |
| No rule set at all (every other tenant) | not shown | n/a | offered through the **normal approval flow** (D5) |

"Refused by the server" matters: hiding an option in the list is not a gate. `apply_leave` must
refuse the type if the list would not have offered it.
**How the "enabled and rehearsed" gate is enforced, honestly:** *enabled* is structural - only
System Manager can switch the rule set on, and the switch leaves a Version row naming who and
when (`track_changes: 1`). *Rehearsed* is a **process control**, not code: the release checklist
must hold the rehearsal evidence (one month of real attendance, engine against slip, on a copy)
before anyone enables it. I am not asking for a "rehearsed" field - it would be a box anyone can
tick. Disabling the rule set is also the **rollback**: it closes the card, Paid Leaves and
LWP again in one move.
*Test:* the three states above × (Apply list, `apply_leave`, card). The middle row is the one
that matters, and it must use a disabled **draft** rule set, as DTC has.

**SEC-3 · Every leave is filed Open. For LWP only, any HR user in scope approves. (Rewritten in rev. 3.)**
*Filing:* `apply_leave` files every type with status Open (`hr_api.py:2401`). It accepts no status
argument.
*Approving LWP (DTC only, SEC-15):* in `_can_action_leave` (`hr_api.py:967-997`), the one rule both
the button and `action_leave` use, a **leave type with `is_lwp = 1`** may be approved or declined by a
user who:
1. is **not** the employee - `is_own_record` stays the first check, and `refuse_own_decision` stays
   first in `action_leave` (no role is exempt);
2. holds **HR Manager or HR User**;
3. has the employee inside `permitted_employees()` - company **and** branch - read for that user at
   that moment;
4. still passes Frappe's own `has_permission("Leave Application", "submit", doc)`.

*Paid Leaves and every other type:* the **named approver** rule, unchanged.
*What this widens, honestly:* LWP for DTC staff moves from one named person to the 7 HR users. That
is what Surbhi chose. The 51 staff with no named approver no longer matter for LWP.
*No new bypass:* HR roles already hold submit on Leave Application. `refuse_own_submit` still guards
every other door.
*The desk, a second door:* HR can already submit any Leave Application they can read on the desk,
for any type. This slice does not change that. SEC-6 and SEC-13 sit on `validate`, so they bind the
desk too. Narrowing the desk is a separate decision.
*Test:* (a) LWP and Paid Leaves with `status="Approved"` in the request body → both filed Open, the
client's status ignored; (b) an HR user in scope approves an employee's LWP → Approved, Attendance
written; (c) an HR user **out of scope** (a fixture HR user with a Company or Branch User Permission
that excludes the employee) → refused, nothing written; (d) an HR user approves **their own** LWP
→ refused (rule SEC-9), on the portal and on the desk; (e) an HR user who is **not** the named
approver tries to approve a **Paid Leaves** request → refused; (f) a non-HR named approver tries to
approve LWP for someone with no named approver → refused; (g) LWP at a tenant without an enabled
rule set → the named-approver rule, as today.
*Observable only if* the out-of-scope fixture HR user really has a narrowing User Permission. **At
DTC all 7 HR users see the whole company** (0 have a Branch permission), so on DTC data test (c)
shows nothing.

**SEC-4 · [REMOVED in rev. 2.]** The self-approval exception is not needed: HR approves LWP.
`refuse_own_submit` and `access.py`'s ceiling of 0 stay exactly as they are.

**SEC-5 · [DROPPED in rev. 3.]** Surbhi allows leave on special days when it is approved. The
Leave Block List, its configuration and its release checks are removed. What remains is a pay rule,
proven in SEC-14: an approved leave on a special day is not doubled; an absence nobody got approved
is unpaid and doubled.

**SEC-6 · Current month only, never before - checked by our code at every door. (Tightened in rev. 2.)**
A leave (any type, whole or half day) is refused when any of its days is **before the 1st of the
current month**. U6 is no: October days cannot be filed on 1-5 November. The check runs **when the
leave is filed and again when it is approved**, so a request filed on 31 Oct and approved on 2 Nov
is refused at approval. It lives in the same one server check as SEC-13 (Leave Application
`validate`), because an employee can create a Leave Application through REST without passing
`apply_leave` (the Employee role has create, verified). Frappe's own guard is not enough: it skips
every non-LWP type (`leave_application.py:387-389`), and DTC has never had a slip for it to look at.
*Scope:* DTC only (SEC-15).
*Test:* (a) 30 Sep, filed on 1 Oct → refused, through the portal **and** through a REST insert;
(b) filed 31 Oct for 31 Oct, approved on 2 Nov → refused at approval; (c) a day today or later in the
current month → allowed.
*Settled (OD-4):* the rule binds HR on the desk too, at DTC.

**SEC-7 · On-behalf is HR-only, refused loudly otherwise, and scoped to the branch.** *(Unchanged in
substance; the reason changes.)*
`apply_leave` and `preview_leave_request`: a caller without an HR role who passes `on_behalf_of` is
**refused** - not filed for themselves as today (`hr_api.py:2385-2388`). A silent fallback files a
leave on the wrong person's record and uses up their LWP limit (SEC-13). On-behalf filing requires the
target to be inside `permitted_employees()` - companies **and** branches.
*Test:* (a) non-HR with `on_behalf_of` → `PermissionError`, nothing written; (b) an HR user with a Branch
User Permission files for another branch of the same company → refused; (c) their own branch → filed.
*Observable only if* the fixture gives the HR user a Branch permission. **DTC has none today** (0 of 7 HR
users).

**SEC-8 · Cancelling: the employee withdraws through Frappe's own path; only an approved leave needs
more. (Rewritten in rev. 2.)**

| State of the leave | Who may cancel it | How | New `ignore_permissions` |
|---|---|---|---|
| **Open** (waiting) | The employee, for their own; HR within scope | Frappe's own **`discard`** (`frappe/model/document.py`, `Document.discard`): it needs only **write**, which the Employee role has. Leave Application's `on_discard` sets status Cancelled (`leave_application.py:173-174`). Our endpoint calls it **as the user** | **0** |
| **Approved, starts tomorrow or later** | The employee, for their own; HR within scope | One portal endpoint. The Employee role has **no cancel**, so the employee's cancel needs one bypass | **1** (`hr_api.py` 69 to 70) |
| **Approved, today or earlier** | **HR only** (Frappe's cancel, HR's own permission, as today on the desk) | Unchanged | 0 |
| **Rejected, or already cancelled** | Nobody | - | - |

**Rules for the employee's path, all checked on the server, before anything else:**
1. The leave's `employee` is the caller's **own Active Employee** (`_get_employee()`). This check is in
   our code, not left to User Permissions - 3 of 10 DTC logins have no User Permission on their own
   Employee (all HR today), and without that row the Employee role's write reaches every Leave
   Application.
2. Open → `discard()`. Approved → only if `from_date` is after today, then `cancel()` with the one
   bypass, set on that one document after rules 1 and 2 have passed. Anything else → refused, with the
   reason.
3. Any leave type, Paid Leaves included. Cancelling a future approved day before it starts changes no
   pay that has already happened.

**Why the bypass is the right price, and the alternatives are worse:**
- *Give the Employee role `cancel` on Leave Application:* refused. Through REST
  (`frappe.client.cancel`) every employee could then cancel **any approved leave they can read,
  including past Paid Leaves days** - more than Frappe allows today, which is nothing.
- *Put the endpoint in a new file to escape the counter:* refused. That games the gate. A new file
  would carry a ceiling of 1, in the same test, with the same justification.
- *HR cancels approved leave on the employee's behalf:* works with 0 bypasses, but contradicts her
  decision ("both HR and the employee can cancel").

**What REST still allows an employee, and why that is safe:** Frappe's `discard` on their **own** Open
request - the same thing our path does. They still cannot submit or cancel anything: they have no
submit or cancel permission, and the bypass exists only inside our endpoint after rule 1.
*Test:* (a) own Open → Cancelled, record kept; (b) own Approved LWP starting tomorrow → cancelled,
Attendance rows cancelled, record kept (`docstatus 2`); (c) own Approved, starting today → refused;
(d) own Approved past Paid Leaves day through `frappe.client.cancel` as the employee →
`PermissionError` (pins "nothing beyond Frappe"); (e) someone else's Open, by a non-HR user **with no
User Permission row** → refused by rule 1; (f) the counter reads 70 for `hr_api.py`, and the ceiling
comment names this endpoint.
*Release check:* every Active, non-HR DTC login has a User Permission on its own Employee (read-only
query, attached to the release).

**SEC-9 · `ignore_permissions` does not grow, except as SEC-8 decides.**
`hr_api.py` is at **69, its ceiling** (`test_portal_security_010.py:740`). Rev. 2: filing stays on
the existing insert (0 new). Withdrawing an Open request uses Frappe's `discard` as the user (0 new).
The employee's cancel of an approved future leave is the only new use (SEC-8), so the ceiling goes
to **70**, with the endpoint named in the comment beside it. The new Leave Application `validate`
check (SEC-6, SEC-13) reads and needs none. The card reads the applications this employee already
gets, filtered by the `emp.name` resolved on the server. `access.py` stays at 0. `payroll_slip.py` is not touched.
**An honest limit of the gate:** the counter counts a word. `frappe.get_all` skips permissions
without that word, so every new `get_all` in this slice must filter on the server-resolved
employee, and the reviewer checks each one by eye.
*Test:* the existing SEC-16 test passes at 70 for `hr_api.py`, and at 0 for `access.py`. No new
`allow_guest`.

**SEC-10 · The pay arithmetic is proven with the rule set on - once, never twice, never never.**
Slip-level tests with the engine enabled: (a) 2 LWP + 1 Paid Leaves + 1 absence → the slip's
`payment_days` equals the engine's `paid_days`, and no Additional Salary or LWP deduction is
added on top; (b) 3 LWP days over a Sunday, with `include_holiday = 1` as DTC has it (OPS-4) →
paid days match the engine and the weekly off is neither lost nor paid twice; (c) half-day LWP
with full punches → a full worked day; (d) half-day LWP with no punches → held, not paid; (e) the
same mix with Paid Leaves configured either way on `is_lwp` → identical `payment_days` (the engine
is type-blind; this test pins it).
*Observable only if* the fixture has a submitted Salary Structure Assignment and real Employee
Checkins. Today DTC has no slips at all - the first real proof is the rehearsal in SEC-2.

**SEC-11 · "Paid Leaves" is created as data, at DTC only, with a written rollback - locked or not.**
Created by hand in the desk by a System Manager, from a checklist, **after** the rule set is
enabled. Not a patch: a patch runs on every tenant. The checklist records the flags it was
created with (`is_lwp`, `allow_negative`, `include_holiday`, `allow_encashment = 0`,
`is_carry_forward = 0`, no allocation). **Holds whether the lock is wording or code (question
a):** any edit leaves a Version row (`leave_type.json`, `track_changes: 1`; no Property Setter at
DTC), only HR roles can edit, and SEC-2 makes the type inert whenever the rule set is off.
**Rollback:** disable the rule set (SEC-2); delete the type only if no Leave Application uses it -
Frappe refuses the delete otherwise (*inference from Frappe's link check*), and the type then
stays as harmless data.
*Test:* the release step attaches a read-only check of those flags on DTC. A unit test cannot see
tenant data, so this one is evidence, not CI.

**SEC-12 · A Paid Leaves request with nobody to approve it is refused when it is filed. (Rev. 3:
Paid Leaves only again - LWP is approved by HR in scope, SEC-3.)**
"Approver mandatory" is only a desk-form rule in Frappe. So `apply_leave` refuses a request when
nobody who may approve it resolves for that employee, and says to ask HR. Who counts as "may
approve" follows Q3. **Holds whichever way question (b) goes:** if HR names approvers for the 51,
or if Q3 makes any in-scope HR user the approver, this never fires. If not, those 51 get a clear
refusal instead of a request nobody can act on, which would also keep a day "set aside" (D3) and
count against their LWP limit (SEC-13) for ever.
*Test:* an employee with no `leave_approver` and no department approver → Paid Leaves refused with
the message; LWP for the same person → filed, and an HR user in scope can approve it.

**SEC-13 · Leave Without Pay is limited to 5 days a calendar month, counted on the server. (New in
rev. 2.)**
*Rule (Surbhi's default, open for confirmation, Q4):* for one employee, the days of LWP that are
**Open or Approved** in a calendar month, plus the request being checked, may not exceed **5**. A
half day counts 0.5. The count uses Frappe's own `total_leave_days` (which already gives 0.5 for a
half day and follows the type's `include_holiday`). A request that spans two months is counted
day by day into each month.
*Where it is enforced:* **one check, on the server, hung on Leave Application `validate`** - so it
runs when the leave is filed (portal, REST, desk, import) and again when it is approved. The portal
screen and the preview only repeat the server's answer. Not only in `apply_leave`: the Employee role
can create a Leave Application through REST without going through it (verified). This is a hook on a
Frappe HR doctype, which the ladder allows only when the requirement fails without it. It does: the
endpoint alone is not a gate. It sits beside the existing `before_submit` entry in
`alvoraa_portal/hooks.py:252-254`, and SEC-6's date rule lives in the same function.
*Scope:* **DTC only** (SEC-15; OD-3). Other tenants are untouched.
*The number:* a constant in that function, with the date of her decision beside it. No setting, no
new field. If she later wants it changed per tenant, the rule set (System Manager only, versioned)
is the next step - not before.
*Fails closed:* a Rejected or Cancelled request frees its days. Two requests filed in the same
second could both pass the count, but the second check at approval refuses whichever goes over.
*Test:* (a) 4.5 days Open + a half day → allowed; plus another half day → refused; (b) 5 Approved +
1 new → refused through the portal **and** through a REST insert; (c) two Open requests of 3 days each,
put in the database directly (as if made before the check existed) → the approver's first approval
is refused too, because 3 Open + 3 being approved = 6 (fails closed); (d) 3 days on 30-31 Oct and 1 Nov → 2 count in October, 1 in November;
(e) a Rejected 5-day request does not count; (f) Paid Leaves days never count.
*Observable only if* the fixture's LWP type has `include_holiday` set as DTC has it (1). Otherwise a
range over a Sunday counts differently from production.

**SEC-14 · Pay-affecting changes are proven before the DTC rule set is switched on, and the
settings change can be undone. (New in rev. 3.)**
Three changes move money: the credit-on-the-1st settings (01e section 3), E6 (approved Paid Leaves
days count toward the 15), and the half-day engine change (01d section 3, with D4: no green mark on
a half-day leave day). **None is switched on at DTC until the rehearsal passes on a local copy** -
the rule set switched on there only, never on dtc.alvoraa.co.
*The rehearsal must show, with the output kept as release evidence:*
1-6. The six items in **01d section 3** (half day: 0.5 leave and no red, late or early charge; an
   automatic "Half Day" with no leave judged as before; 5 named staff by hand; slip equals report
   and saving twice gives the same answer; an Absent day changed by a half-day leave; half-day LWP
   the same as any half day).
7. The six items in **01e section 5**, including the **extra October cost against accrual, shown to
   Surbhi before switch-on.**
8. E6: class A, 13 attended + 2 approved Paid Leaves days → reaches 15 and gets 4; 13 attended + 2
   **Open** Paid Leaves days → does not.
9. **The half-day remedy (SEC-16):** a half-day leave day with no punch for the other half,
   regularised through the existing correction flow and approved by HR → the engine counts the
   other half. *This is the item I expect to fail* (finding in the Revision 3 box).
10. Special days: an approved leave on a special day is not doubled; an absence on a special day
    is doubled.

*The rule-set change is a data change, with a rollback:*
- Made by a System Manager in the desk, from a written list of old and new values (01e section 3).
  Not a patch, not a script on production.
- The record keeps a Version row of every field changed (`track_changes: 1`, verified).
- A comment on the record quotes Surbhi's decision and its date.
- **Rollback:** put back the old values from that Version row (`accrual_month_days` 30; A 7.5 / 1 / 4,
  B 10 / 1 / 3, C 7.5 / 0.5 / 2). If the rule set is already switched on, switching it off first is
  the faster rollback (SEC-2). Rehearse the rollback on the local copy too, and time it.

*Tests in CI (engine, no site data):* E6 with approved and with Open Paid Leaves; half-day leave
with the worked half complete, short, and with no punches (normal day and special day); a "Half
Day" with no leave behind it behaves as today; **no green mark on a half-day leave day even when the
punches would earn one** (D4); the gate at 14.5 and 15 days.

**SEC-15 · Every rule in this slice applies to DTC only - and "DTC" is one check, not a name.
(New in rev. 3.)**
"DTC" in code means: **the employee's company has an enabled `Alvoraa Payroll Rule Set`**, read by
the existing `rule_set_for(company)` (`payroll_rules_apply.py:59-69`). No company name and no site
name appear in code. Every rule here asks that one function: the card (SEC-1), Paid Leaves and LWP
being offered (SEC-2), HR approving LWP (SEC-3), the current-month rule (SEC-6), the limit of 5
(SEC-13), the chain notice (PRIV-1), and the half-day treatment (SEC-16; the engine only runs where a
rule set is enabled).
*Why this shape:* it is already the switch the pay engine uses, only a System Manager can turn it
on, and switching it on is recorded. A second switch ("is this DTC?") could disagree with the
engine.
*Test:* each rule above, run with the company's rule set enabled, disabled, and absent. The rule
fires only in the first case. One table-driven test is enough.

**SEC-16 · Half-day leave: the other half is judged by punches, and a missed punch uses the
existing correction flow - no new permission path. (New in rev. 3.)**
- **No new permission path.** A missed punch is fixed only through the existing attendance
  correction (`attendance_correction.py`), which has **no** `ignore_permissions` (ceiling 0) and is
  decided by whoever holds submit on Attendance Request (`_may_review`). This slice adds no endpoint,
  no role and no bypass for it. The 060 rules (the raiser is never the decider) stay as they are.
- **Until it is regularised, the other half is absent** (and doubled on a special day). The engine
  decides this from punches. The screen states it (design R-42); the screen does not decide it.
- **No green mark on a half-day leave day** (D4). This is an engine rule, tested in SEC-14.
- **Blocked until proven:** in code, the existing flow writes nothing on a half-day leave date (see
  the Revision 3 box). SEC-14 item 9 must pass before the half-day rule is switched on at DTC. If it
  fails, the remedy is Surbhi's decision (Q7), and the engineer must not invent a new correction path
  without it.
*Test:* SEC-14 item 9 on the local copy. In CI: a half-day leave with no punches for the other half
→ 0.5 leave and 0.5 absent; on a special day → the absent half doubled.

### Privacy

**PRIV-1 · When a leave is approved, every manager up the Reports To chain is told - a fixed few
fields, never the reason. (Rewritten in rev. 2.)**
*The flow, as a personal-data flow.* Today, one approver learns of one person's leave. After this
change, **everyone above the person in the Reports To chain** learns of every approved leave, of any
type, for everyone below them. At DTC that is 1 to 2 people per leave (chain at most 2 steps, 7
managers in total; verified by running it). The person at the top learns of **every approved
absence in the company**. That is what Surbhi asked for. It is proportionate because the notice
carries almost nothing, so I accept it - but say it plainly to her (Q6).
*Fixed fields, built in code:* employee name, first and last date, number of days, "approved". **Not**
the type, the reason, the approver's name, anyone's job title, credits, class or pay (rev. 3: her
list). **DTC only** (SEC-15). **No notice on cancellation** until Surbhi asks for one. The direct approver already sees the type on the record.
Managers further up need to know the person is away, not whether they are paid. This also keeps
045 AC-76 (type withheld from team surfaces) true. Built in code, not as a Frappe Notification
record, because a Notification template can be edited by any System Manager to add
`{{ doc.description }}`, and no test sees tenant data.
*Which chain:* **`Employee.reports_to`**, the field Frappe and our scope helpers use. **Not the seat
(position) tree.** The two disagree at DTC today (slice 064). The notice follows Reports To until 064
settles which one is true, and the spec must say so.
*Walking the chain safely:*
- Start at the person's `reports_to`. Stop at the top (no `reports_to`).
- **Cap at 10 steps.** DTC's longest chain is 2, so the cap is far above real use and only stops a
  broken tree.
- **Stop at a loop** (a person seen before). Send to those found so far, and write one line to the
  security log - ids only - so HR can mend the chain.
- **Stop at a person who is not Active**, and do not go past them. A leaver's own `reports_to` is
  stale, so walking through it would tell the wrong people. Fewer recipients is the safe way to fail.
- Send only to **enabled** Users. Skip a manager with no login, but keep walking above them.
- Never send to the employee, and send at most once per person.
*When:* on approval (Frappe's `on_submit`). Not when the request is filed. Not on rejection.
*Test:* reason text `SECRET-REASON-063` → absent from Email Queue, Notification Log, the security log
and the Error Log; the leave type is absent from the body. Chain fixtures: (a) 3 levels → all 3 told;
(b) A→B→A loop → stops, one security-log line, no repeat; (c) 12 levels → 10 told; (d) a non-Active
manager in the middle → the walk stops there; (e) a manager with a disabled user → skipped, the one
above is told; (f) a rejected leave → nobody in the chain is told.

**PRIV-2 · Team surfaces show LWP exactly as any approved leave. (Rev. 2: the "Recorded" tag no longer
exists.)**
No type on Team View or the team table: 045 AC-76 withheld the type and still stands. **Answer to U4:**
the direct approver sees the type on the record and in Frappe's own request email, which already shows
it (verified). The chain notice (PRIV-1) does not.
*Test:* the Team payload for a day with one approved LWP and one approved Paid Leaves has identical keys
and no `leave_type`.

**PRIV-3 · No copy of the credit figures anywhere.**
No cache, no stored field, no new report, export, print format or log line carrying them. The desk
report *Salary Components and Workings* remains HR's view. A cache would also break the brief's
kill criterion (card equals payslip).
*Test:* review check at `06` - the diff adds no DocType, no field holding a figure, no
`frappe.cache()` call on this path.

**PRIV-4 · [REMOVED in rev. 2.]** The "recorded without approval" marker is not needed: every leave
is approved by a person. The audit trail is Frappe's own (`owner`, `creation`, the approver on
`action_leave`'s submit, and `docstatus 2` with `modified_by` on cancel). Recording *who decided* more
strongly is 060's work (its §3), not this slice's.

**PRIV-5 · No personal content in logs or errors on these paths.**
Refusals use `refuse()` - ids and rule only. If `month_summary` fails for the card, the Error Log
title names the employee id only, the traceback holds no figures, and the client gets the design's
"could not be worked out" sentence with no detail.
*Test:* force an exception inside `month_summary` in the card path → the response holds no number
from the fixture; the Error Log row holds no rupee amount and no reason text.

**PRIV-6 · Retention: no new rule, no deletion, and no "keep for ever" setting.**
This slice keeps leave and attendance the way they are kept today. It must not add a purge, and it
must not add a retention setting. The 18 Sep counsel rules do not cover these records. Leave
records are wage records; the statutory minimum is Q-C1 for counsel, and its answer belongs to the
retention slice (feature map A6), not here.
*Test:* review check at `06` - no delete, purge or retention code in the diff.

---

## 8 · The three open DevOps questions - how each requirement holds either way

| Question | If she says yes | If she says no | Requirements that hold both ways |
|---|---|---|---|
| **(a)** Real lock on Paid Leaves? | A Property Setter or hook; editing is refused | Wording only; HR can edit | SEC-11 (Version row, checklist, inert when the engine is off), SEC-10 (e) (pay is the same however the flags are set), SEC-2 |
| **(b)** 51 staff with no approver | HR names approvers before go-live (data) | They stay without | SEC-12 (any request with no possible approver is refused at filing, with a message). Rev. 2: LWP now needs an approver too, so (b) matters more - and Q3 may make it disappear |
| **(c)** Block covers LWP? | - | - | Rev. 3: **moot** - no block; special-day leave is allowed when approved |

---

## 9 · Questions

### Must know (blocks the spec)

**Q1 · [REMOVED in rev. 2 - moot.]** **Q2 · [ANSWERED in rev. 2]:** both HR and the employee cancel;
SEC-8 sets the ceiling at 70 for the one path that needs it.

**Q3 · [ANSWERED in rev. 3: option (ii), as SEC-3 now says.]** Kept below for the record.

**Q3 (history) · Who is "HR" when HR approves Leave Without Pay?**
*My reading:* "keep HR as approver" means a person in HR, not the branch head. *Unclear:* the portal
today lets only the **named leave approver** act, and refuses "any HR Manager" on purpose
(`_can_action_leave`, `hr_api.py:967-997`). At DTC the named approvers are mostly branch heads.
*Why it changes the control:* the three answers carry different risks.
- (i) **Data only:** HR users are named as approvers - on the Employee, or as the department's first
  approver. No code change; the named-approver rule holds. But one person then approves every leave
  type for those people, Paid Leaves included.
- (ii) **For LWP only, any HR user whose `permitted_employees()` includes the person may approve.**
  A code change to `_can_action_leave`, limited to `is_lwp` types. `refuse_own_decision` still applies.
- (iii) **Approval in two steps** (manager, then HR). Not asked for; I would not build it.

*The question:* "For leave without pay, should any HR person who looks after that employee approve it,
or one named HR person per employee?" **My recommendation: (ii)**, scoped by `permitted_employees()`.
It also removes question (b) for LWP. **Fail-closed default meanwhile:** the named-approver rule,
unchanged. HR approves only where HR is the named approver.

**Q4 · [ANSWERED in rev. 3: 5 per calendar month, pending + approved, half day 0.5.]**

**Q4 (history) · The LWP limit: per month or per year, and does
pending count?** SEC-13 is written for "5 per calendar month, pending + approved, half day 0.5". The
constant and one date range change if she answers otherwise. **Default:** as written.

**Q5 · [ANSWERED: yes, at DTC (OD-4).]** **Q5 (history) · Does "current month only" bind HR on the desk too?** Default: yes, every user.
A correction to a past month goes through Attendance, not leave.

**Q6 · (b) [ANSWERED: no cancellation notice for now.] (a) still open.** **Q6 (history) · Notices up the chain.** (a) The top of the chain will learn of every approved
absence in the company. Is she content with that? (b) When an approved leave is **cancelled**, should
the same people be told? Without that, managers keep believing in an absence that is no longer true.
I recommend yes - same fields, same chain. Not included until she says so.

**Q7 · (New in rev. 3, must know before the half-day rule ships) If the existing correction flow
cannot fix a missed punch on a half-day leave day, what should?**
*My reading:* her rule is "the other half counts if its punches are there; if not, ask HR to approve
the regularisation". *Unclear:* in code, that flow writes nothing on such a day, and the engine reads
punches, not status (Revision 3 box). *Why it changes the control:* every option is a pay-affecting
write that someone must approve. Options: (i) extend the held-day confirmation (ATT-06), which already
feeds a confirmed time to the engine, to a missing check-**in** as well; (ii) accept that a half-day
leave day with a missed punch stays half absent; (iii) HR adds the missing Employee Checkin by hand on
the desk. *Question:* "When someone on a half-day leave forgot to punch for the other half, should HR
be able to fix it in the system, or does that half stay unpaid?" **Default meanwhile:** the half stays
absent, and nobody builds a new correction path. **Prove first (SEC-14 item 9) - I may be wrong.**

### Should know (from revision 1, still open)

- **U4** answered in PRIV-2: the direct approver sees the type; the chain notice and Team surfaces do not.
- **(b)**: assign approvers to the 51, or answer Q3 with (ii).

### For counsel

**Q-C1 · How long must leave and attendance records be kept as wage records?** Code on Wages, 2019
(in force 21 Nov 2025; records sections 43-66 in force) and the Delhi Shops and Establishments rules
`[ASSUMPTION: DTC is in Delhi - confirm]`. *Blocks:* the retention slice (A6), not this one.
*Default meanwhile:* keep as today; delete nothing.

---

## 10 · Three findings against existing code (not SEC items here, because they predate this slice)

1. **`_hr_target_employee` checks companies only, not branches** (`hr_api.py:2214-2230`). It feeds
   `get_leave_summary`, `apply_leave` and `preview_leave_request`. This is lesson 2 again: a store's
   HR person could act for another store. **Not live at DTC** (0 HR users with a Branch permission,
   verified by running it). SEC-7 closes it only for on-behalf LWP recording. Fixing the helper for
   all three callers is a separate decision. P3, owner `hrms-fullstack-engineer`.
2. **The DevOps first look says Leave Application has version history and that "approver mandatory"
   makes Frappe refuse.** Neither is true (§0 point 3). Worth correcting in `01b` so the release plan
   does not rely on them.
3. **(Rev. 2) "Only my own leave" rests on a data row, not on a rule.** Leave Application has no
   row-level permission hook, and the Employee role has read and write on it with no "only if owner"
   (Custom DocPerm at DTC, verified by running it). An employee login without a User Permission on
   its own Employee therefore reads every leave reason and can withdraw anyone's Open request through
   REST. **Not live at DTC:** the 3 logins without that row all hold HR roles. SEC-8 makes our own
   cancel path independent of it, and the release check catches a new login without the row. A
   permission hook for every door is the full fix - a separate decision. P2, owner
   `hrms-fullstack-engineer`.

---

## 11 · Worries (not findings - I cannot yet write "this actor, this path, sees this")

- **The slip hook fails open.** `on_salary_slip_validate` catches every error and leaves Frappe's
  own figures on the slip (`payroll_slip.py:186-208`). With Paid Leaves set `is_lwp = 0`, Frappe's
  own arithmetic would pay every approved Paid Leaves day in full, uncapped. Not created by this
  slice, but made larger by it. A slip priced by Frappe instead of the engine should not be
  submittable without someone seeing it. That is an engine change - a decision for Surbhi, not this
  slice.
- **Back-dating erases the "Absent" it replaces.** Approval overwrites the Attendance status by
  `db_set` (no Version row). Rev. 2: a person now approves it and SEC-6 keeps it to the current
  month, so this is smaller. If DTC ever charges for absences differently, it becomes a finding.
- **(Rev. 2) Two LWP requests filed in the same second** could both pass SEC-13's count. The second
  check at approval catches it, unless two approvers approve both in the same second. I do not ask for
  a lock.
- **Half-day LWP with no punches makes a no-show "held" instead of "absent".** A manager must then
  confirm it. A human is in the loop, so I do not raise a requirement.
- **Location Manager can cancel Leave Applications at DTC** (Custom DocPerm). Cancelling a past LWP
  leaves the day with no record (unpaid), so no money is gained. I have not checked which records a
  Location Manager can reach.

---

## 12 · What I could not verify, and what I would need

- **That `discard()` called as the employee works end to end on Leave Application** (it needs write
  only - verified in Frappe's `document.py` on the local bench; the hooks around it are not run).
  Needs one bench run.
- **That Frappe refuses to delete a Leave Type that is in use** - inference. Needs one bench run on
  a copy.
- **The statutory retention period** - needs counsel (Q-C1).
- **Which state's shop rules apply to DTC** - needs Surbhi.
- **Which records a Location Manager can reach** - needs a read of DTC's User Permissions for that
  role, which I did not run.
- **No timing** - the card's cost is DevOps's estimate (about 100 queries), not measured.

---

## 13 · Subtract pass

Removed on the final read:

- A "rehearsed" field on the rule set: anyone could tick it, so it adds nothing to the Version row of
  who enabled it.
- An upper bound on future dates: a far-future request can be withdrawn.
- A server-side cap on Paid Leaves at "available now" (U3): pay is the same either way, so it is a
  usability rule, not a control.
- A change to `_hr_target_employee` for every caller: moved to §10 as a separate decision.

**Removed in rev. 2, because her changes made them unnecessary:** SEC-4 (self-approval exception);
the no-approval path and server flag in SEC-3; the engine-list check in SEC-5 (one mechanism, the
block list, now that a person approves); PRIV-4 (the marker Custom Field); the "Recorded" status word
and Team tag; the security-log line per recorded LWP; Q1. **Not added in rev. 2, on purpose:** a
setting for the LWP limit (a constant until she wants another number); a lock against two requests in
the same second; the leave type in chain notices; a cancellation notice up the chain (Q6, her call).

Kept, and why: SEC-12 (it is how the requirements hold whichever way question (b) goes).

---

## Residual risk

| Risk | Kind | Level | Who accepts | Date |
|---|---|---|---|---|
| ~~U2 and no-approval LWP~~ | Removed in rev. 2 - every leave is approved | - | - | - |
| The top of the Reports To chain learns of every approved absence (PRIV-1) | Intentional trade-off (her change, 21 Oct 2026); minimal fields | P3 | **Surbhi - to confirm (Q6)** | open |
| ~~Leave Block List edits~~ | Removed in rev. 3 - no block list | - | - | - |
| An approved leave on a special day avoids the double charge, including when HR approves it after the day, inside the current month (SEC-5 dropped, SEC-6) | Intentional trade-off | P3 | Surbhi (final answers, 21 Oct 2026) | 21 Oct 2026 |
| LWP approval widens from one named person to every HR user in scope (SEC-3) | Intentional trade-off | P3 | Surbhi (final answers, 21 Oct 2026) | 21 Oct 2026 |
| The half-day remedy may not work (SEC-16, Q7) | **Dangerous until proven** - a half day could stay unpaid with no way to fix it. Removed by SEC-14 item 9 passing, or by Q7 | P1 for the half-day rule | **Surbhi - decide Q7 if item 9 fails** | open |
| "Only my own leave" rests on a User Permission row (§10 point 3) | Temporary debt; removed by a permission hook on Leave Application | P2 | `hrms-fullstack-engineer` to propose | open |
| "Rehearsed" is a process step, not code (SEC-2) | Acceptable simplification | P2 | **Surbhi - to confirm** | open |
| The slip hook fails open (§11) | Temporary debt; removed by an engine change that stops such a slip being submitted | P2 | **Unowned - Surbhi to name an owner** | open |
| Leave records have no retention rule (PRIV-6) | Temporary debt; removed by the retention slice once counsel answers Q-C1 | P3 | **Unowned** | open |
| `_hr_target_employee` is company-scoped only (§10) | Temporary debt; not live at DTC | P3 | `hrms-fullstack-engineer` to propose | open |

Nothing here is **dangerous debt** as long as SEC-2 holds.

---

## Handoff note

To the business analyst (rev. 3 supersedes rev. 2 below): the most important now are **SEC-3** (HR in scope approves LWP; self refused), **SEC-15** (one DTC check), **SEC-14** (rehearsal and rollback), **SEC-13** (limit on every door) and **SEC-1** (new keys). SEC-4, SEC-5 and PRIV-4 are removed. **SEC-16 is blocked** until SEC-14 item 9 passes or Surbhi answers Q7.

To the business analyst (rev. 2, history): trace every SEC and PRIV item to an acceptance criterion. Write
Q3's fail-closed default (named approver, unchanged) into the spec until Surbhi answers. The five that
matter most now are **SEC-13** (the limit, on every door), **SEC-8** (cancel: discard for Open, one
bounded bypass for approved), **SEC-2** (nothing reachable while the engine is off), **SEC-1** (the
field list) and **PRIV-1** (the chain notice). SEC-4 and PRIV-4 are removed - do not trace them.

To the engineer: the only creator of a Leave Application in our code is `apply_leave`, but REST is a
second door. That is why SEC-6 and SEC-13 sit on `validate`. Do not grant the Employee role submit or
cancel. `hr_api.py` goes to 70 for the SEC-8 cancel endpoint and nothing else.

To the test engineer: every test above that says "observable only if" fails silently on the wrong
fixture. Run SEC-8 as the employee's own user, plus one user with no User Permission row; SEC-14 item 10 in a
month with a special day; SEC-3 (c) with a narrowing User Permission; SEC-7 with a Branch permission; SEC-13 through REST as well as the portal.

Sources checked for the Code on Wages, 21 Oct 2026:
[Mondaq - Code on Wages 2019](https://www.mondaq.com/india/employee-rights-labour-relations/1713462/code-on-wages-2019),
[Lexplosion - State Rules status](https://lexplosion.in/?p=143963),
[India Code - the Act](https://www.indiacode.nic.in/bitstream/123456789/15793/1/aA2019-29.pdf) (listed, not read).
