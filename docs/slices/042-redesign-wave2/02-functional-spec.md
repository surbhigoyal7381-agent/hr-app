---
slice: 042-redesign-wave2
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-09-24
revision: 1
status: draft — written ahead of the build so Wave 1 does not stall. Needs the six decisions in §20 before the strategy gate
inputs: [../009-ess-portal-redesign/00-assessment-and-plan.md §4 Wave 2 and Appendix A, ../009-ess-portal-redesign/appendix-b-home-inbox.md, ../009-ess-portal-redesign/01b-ux-design.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, ../034-redesign-wave1/00g-decision-register.md (W1D-01 to W1D-21), ../034-redesign-wave1/02-functional-spec.md revision 4, ../034-redesign-wave1/01c-security-privacy-requirements.md revision 4, ../034-redesign-wave1/03-implementation-notes.md §4, prototype-v2.html]
brief: there is no `01` for this slice. The approved brief is `../009-ess-portal-redesign/00-assessment-and-plan.md` (Wave 2), the design is `../009-ess-portal-redesign/01b-ux-design.md`, and the decisions are in `00f-decisions-2026-09-22.md` and `../034-redesign-wave1/00g-decision-register.md`
---

# Wave 2 — Home and Inbox: functional spec

## Bad news first

**Three things in the approved plan and the approved prototype cannot both be true, and
the build will pick one of them at 11pm unless somebody decides now.**

1. **The prototype's Home shows a number that is not the Inbox number.** On Home the
   "Needs you" heading reads "N open", worked out as *needs items + approvals*
   (`parts/p5-home-inbox.js:106`). The Inbox number Surbhi decided in Q5 is
   *approvals + policies to acknowledge + my own open requests*. For Sandeep on a normal
   Tuesday those are two different integers, side by side on one screen, neither labelled.
   **§6 says exactly what each number counts.** My recommendation is in §20 D-1.
2. **The corrections queue moves, and that moves the count.** 009 design decision 1 says
   the manager decides an attendance fix and HR steps in after two working days. The code
   sends every correction to HR (`attendance_correction._may_review`, line 240 — it tests
   submit permission on Attendance Request, not a role). Wave 1 deliberately counted them
   **where they sit today** (034 AC-53). Wave 2 is where that changes, and it changes who
   sees what. §20 D-2.
3. **Wave 2 cannot add include files until OPS-31 is done.** Wave 1 measured a cliff in
   Frappe's Jinja template cache: 4 include files cost +7.4 %, 5 cost +97 %
   (`../034-redesign-wave1/03-implementation-notes.md` §4). Home and Inbox are two new
   panels. **This spec assumes Wave 2 adds no new include file** and that its markup,
   style and script go into the four files Wave 1 created — which means panel-versus-panel
   collisions are real until OPS-31 moves style and script into static assets. §20 D-6.

Everything else in this spec is buildable on what is installed today.

---

## 0. How to read the numbers in this file

**Story and check numbers are per slice.** This slice runs `US-1` to `US-14` and `AC-1`
to `AC-58`. Wave 1 has its own `US-1` and `AC-1` and they are different things. Cite them
as "042 AC-12" and "034 AC-12" so nobody confuses the two.

Claims carry a label: **Confirmed fact** (read in the source, with file and line),
**Stakeholder statement**, `[ASSUMPTION]`, **Recommendation**, **Risk**, **Open question**.

---

## 1. Cross-module reach — named before anything is specified

| App | Touched how |
|---|---|
| `alvoraa_portal` | **Most of the work.** New `inbox_api.py` and `home_api.py`; edits to `hr_api.py`, `goals_api.py`, `attendance_correction.py`; the Home and Inbox markup, style and script inside Wave 1's four include files |
| `hrms` (our fork) | Read only, except `alvoraa_policy_library/access.py` (`readable_policy_names`, line 163) and `alvoraa_hr_core/access.py` (`permitted_employees`, `refuse_own_decision`) — both **reused, not changed** |
| `erpnext` | Read only — Employee, Holiday List, Expense Claim |
| `frappe` | Read only — `frappe.get_all`, `frappe.db.count`, permissions, `__()` |
| `alvoraa_goals` | Read only. Goal Progress Update and Individual Goal are read through `goals_api`, never queried directly from the new modules |
| `alvox_compensation` | **Not touched.** Not installed on either client tenant |

**HRMS domains involved:** leaves (approve, apply, balances), attendance (check-in,
corrections, gaps), appraisals and goals (updates to approve, self-review due), payroll
(one read-only "your payslip is ready" row — see §8's negative list), org structure
(who reports to whom), policies (acknowledgements).

**Personas, as Wave 1 fixed them** (`034` §2, W1D-02 and W1D-20 — first match wins, and
rules 1 to 5 need an **Active** Employee record):

| Short name | Who | Rule |
|---|---|---|
| **Rahul** | sales executive, no reports, not HR | 4 or 5 |
| **Sandeep** | floor manager, 19 reports, not HR | 3 |
| **Kamal** | owner who holds HR, 4 reports | 1 |
| **Priya** | store HR, no reports | 2 |
| **Asha** | platform operator, no Employee record | 6 |

---

## 2. Questioning the ask before specifying it

**The brief's problem is real and the cause is named.** Appendix B does not say "people
miss things"; it says the bell costs 16.4 seconds for HR, the approvals call is broken
(F1, `ImportError`), and the only waiting items in the demo tenant are the owner's own.
So the fix is a working, fast, honest queue — not a reminder engine. **Confirmed fact:**
`goals_api.get_pending_approvals` (line 1335) still walks one employee at a time
(line 1344 onwards), and Wave 0d added `get_pending_approvals_count` (line 1410) as the
cheap stand-in. Wave 2 replaces both for the portal.

**What happens after each thing we put on the screen:**

| Thing | Decision it drives | Who decides | Could the system act instead? |
|---|---|---|---|
| Approval row | approve / decline | the named approver | No. A person must decide about a person (§18.4) |
| "3 days have no attendance" | raise a correction or apply leave | the employee | **Partly, and we deliberately do not.** The system could auto-raise a correction; it must not, because it would put words in the employee's mouth |
| "Your self-review is due in 19 days" | start it | the employee | No |
| Policies to acknowledge | read and accept | the employee | No |
| "Your August payslip is ready" | open it | the employee | No |
| Peer "team today" counts | nothing | — | **This one earns its place only because it stops people asking each other.** It carries no action and no names; if it does not survive the usability test in `01b` §12, drop it rather than grow it |

**Dropped from the ask, with reasons, in §12.**

---

## 3. Gap analysis — what already exists, checked in the source

Line numbers are from `origin/dev` at `8718f27`, read in
`.claude/worktrees/042-redesign-wave2` on 2026-09-24.

| Requirement | What exists today (file : line) | Verdict | Cost |
|---|---|---|---|
| Greeting, name, shift, store | `hr_api.get_checkin_status:1370` returns the whole Employee row | **Extend** — one Home call with a fixed key list, like Wave 1's `frame_api.ME_FIELDS:43` | S |
| Check in / out | `hr_api.do_checkin:1420`, `checkin_needs_location:1404`; duplicate guard and geofence wording live in `field_checkin.py` | **Reuse** — Home calls the same endpoints and reuses `field_checkin`'s refusal wording | S |
| Check-in hero only when the person has a shift (009 design decision 6) | nothing reads Shift Assignment for Home | **Extend** — read today's Shift Assignment, else `Employee.default_shift` | S |
| Leave left | `hr_api._ledger_leave_balances:88` — slice 035, on dev, reads Frappe HR's ledger | **Reuse, unchanged** | — |
| Own holidays | `hr_api._own_upcoming_holidays:312` — slice 035, on dev, employee's own list, with a note when none is assigned | **Reuse, unchanged** | — |
| Self-review due | `performance_api.get_my_appraisals:4013`; `get_my_review:4125` **creates an extension record on read** (`_get_or_create_extension`) | **Extend** — Home reads status only and must never call `get_my_review` | S |
| Attendance gaps ("3 days have no attendance") | `attendance_correction.month:360` reads a whole month, ~15 queries | **Build** a narrow "problem days" query; reuse `month`'s own `_state` definitions | M |
| Approvals — leave | `hr_api.action_leave:694`; `_can_action_leave:653`; `_leave_approver_for:639` | **Reuse** the action; **Build** the list | S |
| Approvals — goal and KPI | `goals_api._pending_approvals_scope:1308`, `approve_goal_update:1220`; `performance_api.approve_kpi_update:564` | **Extend** — one set-based query; the actions are reused | M |
| Approvals — attendance corrections | `attendance_correction.to_review:722`, `decide:743`, `_may_review:240` | **Extend** — see D-2 | M |
| Approvals — shift requests | nothing decides one in the portal; `hr_api.submit_shift_request:1917` only creates | **Build** a small decide action | S |
| Nobody approves their own request | `access.refuse_own_decision`, already called in `attendance_correction.decide:743` | **Reuse** — extend the same call to leave, shift and goal/KPI | S |
| Policies to acknowledge | `hrms/alvoraa_policy_library/access.readable_policy_names:163`; `hr_api.get_my_policies:2955` | **Reuse** | S |
| My own open requests | `hr_api.get_requests_history:2000`; `attendance_correction.my_requests:650` | **Extend** — one list, one shape | M |
| The count itself | Wave 1 builds `inbox_api.get_nav_counts` (034 §5). **It does not exist yet** — `alvoraa_portal/inbox_api.py` is absent on this branch | **Build**, if Wave 1 has not; **Extend** if it has | M |
| The old bell call | `goals_api.get_pending_approvals:1335` (16.4 s for HR) and `get_pending_approvals_count:1410` | **Drop** from the portal. Left in place for any other caller; a test pins that no boot path calls either | S |
| Peer "team today" | `hr_api.get_week_presence:3151` — falls back to **department** at line 3183 when the person has no reports, capped at 40 | **Extend** — peers are people with the same manager; no department fallback (§20 D-3) |  M |
| Manager "your team today" | `hr_api.get_manager_dashboard:354` | **Extend** — reuse, and keep W1D-20's HR-scope rule | S |
| Celebrations | nothing | **Build** — own work anniversary and new joiners (§20 D-4) | S |
| Birthdays | `Employee.date_of_birth` exists on every record | **Drop** for v1 (`01b` §9; Q8 needs a DPDP advisor) | — |
| Announcements | no doctype; Frappe `Note` has 0 rows and is site-wide | **Drop** for v1 (§12) | — |
| Expense and advance approvals | no portal screen; `hr_api.apply_expense_claim:1750` creates a claim **with no `expense_approver`** | **Drop** from the count (034 §5's rule: count only what the portal can act on). The missing approver is a **defect**, §11 E-2 | — |
| Activity feed | `hr_api.get_portal_activity:737` | **Drop** from Home (`01b` did not design it); the endpoint stays for the existing panel | — |

**No new DocType. No custom field. No patch. No migration.** Every list this spec adds is
a query over records that already exist.

**Where two models describe the same thing.** "Waiting on me" exists in three places
today: the bell (`goals_api`), the Team badge (leave only, page) and HR's corrections
queue. **The single source of truth from Wave 2 on is `inbox_api`.** Every other counter
is deleted or repointed at it in the same commit; AC-14 pins that.

---

## 4. Process flow — what actually happens

### 4a. The morning (Rahul, frontline)

1. Rahul opens the portal. It is the tenant's landing page.
2. The frame asks for two things: `get_frame` (Wave 1) and `get_nav_counts`.
3. Home asks for one thing: `get_home`.
4. **Decision point — has he a shift today?** Yes → the check-in hero is the biggest thing
   on the page. No → Home leads with "Needs you" (009 design decision 6).
5. **Decision point — has he anything waiting?** No → "Needs you — All clear", which is a
   designed state, not an accident. Yes → the items, most urgent first.
6. He taps a "Fix" on "You are marked absent on 7, 8 and 9 Sep" → the correction sheet
   opens with those three days pre-filled.
7. He sends it. The row turns to "Request sent · waiting for <decider>". **The Inbox count
   goes up by one** — it is now one of *his own open requests* — and the number on the bell
   and the number in the menu both change without a page reload.

**Unhappy paths:** no Employee record (§9 state table); shift assignment missing; no
holiday list assigned (slice 035 already shows "Ask HR to set one up"); the counts call
fails while `get_home` succeeds (the bell shows no number, Home still works); the whole
page fails (Wave 1's page-error sentence).

### 4b. The floor manager (Sandeep)

1. Home shows the two people who need him, not the nineteen who do not.
2. Approval cards sit at the top of "Needs you", each with a context line that carries
   **no colleague's name, leave type or reason** (§8).
3. He approves in place. The row disappears, a toast confirms, the counts are re-read from
   the server — never decremented in the browser (E-23 in appendix B; AC-13).
4. **Decision point — somebody else decided it first.** The action returns "This one has
   already been decided", the row disappears, the counts refresh. No error state.

### 4c. HR (Priya, store HR)

1. Her Inbox holds corrections and goal/KPI updates **for her store only** (Wave 1 SEC-3
   and SEC-5, which narrow the live portal on release).
2. She never sees her own request in her own queue (`refuse_own_decision`).
3. After 009 design decision 1 she sees a manager's un-acted corrections **after two
   working days** — §20 D-2 decides whether she sees them before that too.

---

## 5. Permission and visibility matrix

Rows are what Wave 2 adds. Wave 1's matrix (034 §3) still governs the menu.

| | Rahul (employee) | Sandeep (manager) | Priya (store HR) | Kamal (HR + reports) | Asha (no Employee record) |
|---|---|---|---|---|---|
| Home: own check-in, shift, store | ✓ | ✓ | ✓ | ✓ | — ("not linked to an employee record") |
| Home: own leave left, own holidays | ✓ | ✓ | ✓ | ✓ | — |
| Home: own self-review state | ✓ | ✓ | ✓ | ✓ | — |
| Home: own attendance gaps | ✓ | ✓ | ✓ | ✓ | — |
| Home: peer "team today" counts | ✓ (presence only) | replaced by "your team today" | ✓ | replaced by "your team today" | — |
| Home: "your team today" | — | ✓ own reports | ✓ **HR scope** (W1D-20) | ✓ HR scope | — |
| Home: team goal summary | — | ✓ own reports | ✓ HR scope, capped at 50 | ✓ | — |
| Inbox: leave to approve | ✓ only where named `leave_approver` | ✓ same | ✓ same | ✓ same | — |
| Inbox: goal / KPI updates | — | ✓ own reports | ✓ `permitted_employees()` minus self | ✓ | — |
| Inbox: attendance corrections | — | ✓ **after D-2** | ✓ their store, minus self | ✓ | — |
| Inbox: shift requests | ✓ where named `approver` | ✓ same | ✓ same | ✓ same | — |
| Inbox: policies to acknowledge | ✓ own | ✓ own | ✓ own | ✓ own | ✓ if any are readable; else the count is 0, not an error |
| Inbox: my own open requests | ✓ own | ✓ own | ✓ own | ✓ own | — (count 0) |
| Inbox: decide | only what is theirs to decide | same | same | same | — |

### The negative cases, stated on purpose

**Home must NOT show:**

| Must not | Why |
|---|---|
| The caller's own `date_of_birth`, `gender`, `cell_number`, `date_of_joining`, `reports_to` or `branch` in the payload | Wave 1's biggest security finding: a start-up call that sent all of these to every page. `get_home` has a fixed key list (AC-5), the same discipline as `frame_api.ME_FIELDS:43` |
| Any colleague's leave **type**, leave **reason** or reason for absence | `01b` §9; slice 002's one-way rule. The peer card says so on screen |
| "Nobody is on leave today" or any equivalent | Design correction D6. It tells a colleague that an absence is *not* leave, which is the same disclosure backwards |
| Anyone's birthday | Q8 is open and needs a DPDP advisor; out of scope (§12) |
| Any loss-of-pay **amount** for anyone, including the caller's own reports | Q-b, 14 Sep. `get_team_late_list:2806` was fixed to days only — Wave 2 must not put the amount back |
| A colleague's goal percentage to a peer | Only a manager (or HR in scope) sees a report's goal figure |
| A take-home figure for anyone but the caller | `_own_payslip:1545` is the whole check and it stays the whole check |
| A self-review that has not been sent, to anyone but its subject | `performance_api.get_my_review:4125` already refuses (PRIV-2); Home must read **status only** and must never call it |
| Names in the counts payload | 034 PRIV-4: counts are numbers |

**Inbox must NOT show:**

| Must not | Why |
|---|---|
| A request the caller may not act on | The list and the action use the same scope function, so a row that is drawn is always actionable |
| The caller's own request in the caller's own approval queue | `refuse_own_decision`; AC-25 |
| Another person's decision note, or their approver's name, to anyone but the requester and the approver | "My requests" is the caller's own Employee only |
| A colleague's leave type inside an approval context line | "Two other people in this team are away on those days" — a number, never a name, never a type (AC-28) |
| Expense-claim or salary-advance amounts | Not counted and not listed in Wave 2 (§12) |
| Document ids or record names in the count payload | 034 PRIV-4 |

---

## 6. The Inbox count — what it counts, exactly, for each persona

**Surbhi's standing rule: the number equals the list.** This section is the contract.

### 6.1 The one helper

`inbox_api.parts(user)` returns an ordered list of **part** objects. Each part has one
filter expression and two uses of it:

```
part.count()          -> int      the same filters, counted in the database
part.rows(limit=n)    -> [rows]   the same filters, ordered, limited
```

**Rule 1 — one filter, two uses.** A part may never build its number from a different
query than its list. `get_nav_counts` and `get_inbox` both call `parts()`; neither writes
a filter of its own. AC-6 fails if a part's `count()` and `len(part.rows(limit=None))`
disagree for any persona in the fixture set.

**Rule 2 — the list is capped, the count is not** (Wave 1's N3 rule, 034 §5). Where a
part's count is above the list cap of 50, the screen says *"showing the first 50 of 60"*.
No part ever shows "50+", because a "50+" cannot be added into the one honest total.

**Rule 3 — "waiting" is defined once per part, in the database.** For attendance
corrections that means `docstatus = 0` **and** `alvoraa_review_status` not `Declined` and
not `Withdrawn`, **including rows where it is NULL or empty**. Today
`attendance_correction.to_review:722` reads 50 rows and then filters in Python
(`return [r for r in out if r["state"] == "waiting"]`) — which is exactly how a count and
a screen come to disagree above the cap. **Confirmed fact**, read at line 740.
`[ASSUMPTION]` Frappe's `"not in"` wraps the column in `ifnull()`. If the bench says
otherwise the part reads ids and applies the same Python filter — same definition, one
place.

**Rule 4 — a part with nothing is not shown, and contributes 0.** It is never hidden by
throwing.

### 6.2 The seven parts

| # | Part | Filter (the one expression) | Who has it | Row wording |
|---|---|---|---|---|
| 1 | Leave to approve | Leave Application · `leave_approver` = session user · `status = "Open"` · `docstatus = 0` · `employee != my own` | anyone named as an approver | "3 leave requests to approve" |
| 2 | Goal and KPI updates | Goal Progress Update ⋈ Individual Goal and KPI Progress Log ⋈ KPI · pending is empty, NULL or `Pending` · employee in `_pending_approvals_scope(me, is_hr)` · minus me | manager, HR | "4 goal or KPI updates to approve" |
| 3 | Attendance corrections | Attendance Request · waiting by rule 3 · **scope per D-2** · minus me | see D-2 | "2 attendance fixes to decide" |
| 4 | Shift requests | Shift Request · `approver` = session user · `status = "Draft"` · `docstatus = 0` · minus me | named approvers | "1 shift change to approve" |
| 5 | Policies to acknowledge | `readable_policy_names()` minus my acknowledgements | everyone with a readable policy | "2 policies to read and accept" |
| 6 | My own open requests | my leave (`status = "Open"`), my corrections (waiting by rule 3), my shift requests (Draft) — **my own Active Employee only** | everyone with an Active Employee record | "3 of your requests are waiting" |
| 7 | *(not a part)* Needs-you items — self-review due, attendance gaps, documents | — | — | **Not counted.** §6.4 |

**The Inbox total = parts 1 to 6, added.** That is Q5 in Surbhi's words: approvals waiting
+ policies not acknowledged + my own open requests.

### 6.3 What each persona's total is made of

| Persona | Parts that can be non-zero | Parts that are always 0, and why |
|---|---|---|
| **Rahul** (employee) | 1 (only if he is somebody's named `leave_approver` — possible and real), 4 (same), 5, 6 | 2 — `_pending_approvals_scope` gives him nobody. 3 — he holds no submit permission and, after D-2, has no reports |
| **Sandeep** (manager) | 1, 2, 3 (after D-2), 4, 5, 6 | none |
| **Priya** (store HR, no reports) | 1, 2 (her store), 3 (her store), 4, 5, 6 | none |
| **Kamal** (HR + 4 reports) | 1, 2, 3, 4, 5, 6 | none |
| **Asha** (no Employee record) | 5 only, and usually 0 | 1, 2, 3, 4 — no Employee record, no approver rows. 6 — no Employee record. **Total 0, shown as "All clear", never as an error** |
| **A leaver with an enabled login** | 6 only (his own still-open requests) | 1 to 4 — Wave 1 SEC-14 makes the scope helpers find Active records only. 5 — no readable policies |

**A person who is their own leave approver** (real, and it happens on small tenants) is
counted **once**, under part 6, never under part 1. Part 1's filter carries
`employee != my own`. AC-9.

### 6.4 The Home number, which is a different number

**This is the trap the plan did not name.** The prototype's Home heading counts
*needs items + approvals* (`p5-home-inbox.js:106`). The Inbox number counts
*approvals + policies + my own open requests*. For Sandeep with 2 approvals, 1 policy,
1 open request of his own and 1 needs item, the prototype's Home says **3** and the bell
says **4**.

**Recommendation (D-1): Home's "Needs you" heading carries no number at all.** The bell
and the Inbox menu item are the one number, and Home's list simply shows the items. If
Surbhi prefers a number on Home, it must be the same total, labelled "waiting on you", and
every Home item must then be one of the six counted parts — which means the self-review
reminder and the attendance-gap reminder move below the fold under a heading with no
count. AC-2 tests whichever she picks; the test is written against the decision, not
against the prototype.

---

## 7. Stories

Personas as §1. Points are the YouTrack scale (1, 2, 3, 5, 8). **An 8 is a warning to
split, and US-4 is flagged as such.**

| # | Story | Screen | Points | Carries |
|---|---|---|---|---|
| **US-1** | As **Rahul**, I want Home to open with the one thing that needs me, so that two minutes between customers is enough. | Home | 5 | AC-1, AC-2, AC-3 |
| **US-2** | As **Rahul**, I want to check in from Home with my shift shown, so that I do not have to remember when my shift starts. | Home hero | 3 | AC-4 |
| **US-3** | As **Rahul**, I want my own numbers on Home — leave left, my holidays, my days with no attendance — and nobody else's, so that Home is mine. | Home | 5 | AC-5, AC-6, AC-7 |
| **US-4** | As **Sandeep**, I want one honest queue of everything waiting on me, with the number matching the list, so that I trust the badge. | Inbox, bell | 8 — **split for the build**: (a) the parts and the count, (b) the rows and their wording, (c) decide-in-place | AC-8 to AC-16 |
| **US-5** | As **Sandeep**, I want to approve or decline where I see the problem, so that I do not open three screens to answer one question. | Inbox, Home | 5 | AC-13, AC-17, AC-18 |
| **US-6** | As **Rahul**, I want to see my own requests and what is happening to them, so that I stop asking HR. | Inbox | 3 | AC-19, AC-20 |
| **US-7** | As **Rahul**, I want to fix a day with no attendance from Home, so that an unpaid day does not sit there because the form was hard to find. | Home → correction sheet | 5 | AC-7, AC-21, AC-22 |
| **US-8** | As **Priya** (store HR), I want my queue to be my store's, so that I am not shown head office's work. | Inbox | 3 | AC-23, AC-24 |
| **US-9** | As **Rahul**, I must not learn why a colleague is away, so that an absence stays between them and HR. | Home peer card | 3 | AC-29, AC-30 |
| **US-10** | As **Rahul**, my date of birth, gender and phone number must not be sent to Home, so that a screenshot or an error report cannot carry them. | — | 2 | AC-5 |
| **US-11** | As **Kamal**, nobody must be able to approve their own request, including me, so that a queue is a control and not a formality. | Inbox | 3 | AC-25 |
| **US-12** | As **Rahul**, I want Home to tell me what happened when something fails, so that a blank card never reads as "you have nothing". | Home, Inbox | 3 | AC-31 to AC-36 |
| **US-13** | As **Asha** (platform operator with no Employee record), I must get a working Home and an Inbox that says "All clear", not a page of errors. | Home, Inbox | 2 | AC-37 |
| **US-14** | As **Surbhi**, I want Home and Inbox to cost three calls and a bounded number of queries whatever the team size, so that the landing page is not the slowest page in the product. | — | 3 | AC-38, AC-39, AC-40 |

### YouTrack-ready table

| Summary | Description | Persona | Points | ACs |
|---|---|---|---|---|
| Home leads with what needs you | Home's first block is "Needs you", computed from real state, with "All clear" as a designed empty state | Rahul | 5 | AC-1, AC-2, AC-3 |
| Check in from Home with the shift shown | Hero appears only when the person has a shift today (009 design decision 6) | Rahul | 3 | AC-4 |
| Home's own numbers, and only the caller's | Fixed payload key list; leave left from the ledger; own holiday list; own attendance gaps | Rahul | 5 | AC-5, AC-6, AC-7 |
| One inbox count that equals its list | One `parts()` helper serves the count and the rows; capped list, uncapped count | Sandeep | 8 (split 3/3/2) | AC-8 to AC-16 |
| Decide in place | Approve/decline from Inbox and from Home; counts re-read from the server | Sandeep | 5 | AC-13, AC-17, AC-18 |
| My requests and their state | One list of the caller's own open and recent requests, with withdraw where allowed | Rahul | 3 | AC-19, AC-20 |
| Fix an attendance gap from Home | Tapping Fix pre-fills the days; multi-day supported | Rahul | 5 | AC-7, AC-21, AC-22 |
| Store HR's queue is their store | `permitted_employees()` scope on counts and lists | Priya | 3 | AC-23, AC-24 |
| A colleague's absence reason is never shown | Presence only on the peer card, with the sentence on screen | Rahul | 3 | AC-29, AC-30 |
| No personal fields in the Home payload | Fixed key list, asserted per persona | Rahul | 2 | AC-5 |
| Nobody approves their own request | `refuse_own_decision` on every decide path | Kamal | 3 | AC-25 |
| Every state is designed | Loading, empty, error, no-permission, no-data on both screens | Rahul | 3 | AC-31 to AC-36 |
| A person with no Employee record gets a working page | Home's plain line, Inbox "All clear", no errors | Asha | 2 | AC-37 |
| Three calls and a bounded query count | `get_frame`, `get_nav_counts`, `get_home`; no query in a loop | Surbhi | 3 | AC-38 to AC-40 |

---

## 8. Data model

**No new DocType, no new field, no patch, no migration.** Everything read already exists.

For each thing Wave 2 shows, the field it comes from — so nobody invents one:

| Shown | Doctype · field | Why an existing field carries it |
|---|---|---|
| Shift on the hero | Shift Assignment · `shift_type` → Shift Type · `start_time`, `end_time` | Frappe HR's own precedence: an assignment beats `Employee.default_shift` |
| "Checked in at 09:24" | Employee Checkin · `time`, `log_type` | — |
| Leave left | Leave Ledger Entry, through `_ledger_leave_balances:88` | Slice 035 already made this the one source |
| Own holidays | Holiday List Assignment, through `_own_upcoming_holidays:312` | Slice 035; no fallback, on purpose |
| Self-review state | Appraisal · `status`; Alvoraa Appraisal Extension · its status | Read only. **Never** `get_my_review`, which creates a row |
| Self-review "due" date | Appraisal Cycle · `end_date` | **Recommendation:** there is no separate deadline field and we are not adding one. Q11 closed this way unless Surbhi says otherwise |
| Attendance gap days | Attendance · `status`, `attendance_date`; Holiday; Leave Application; Attendance Request | §10's rule |
| Approval rows | the four source doctypes in §6.2 | — |
| Policies | Alvoraa Policy + its acknowledgement child, through `readable_policy_names:163` | — |
| My requests | Leave Application, Attendance Request, Shift Request | — |
| Own work anniversary | Employee · `date_of_joining` | — |
| New joiners | Employee · `date_of_joining`, `branch` | Scope per D-4 |

**`get_home`'s payload keys are a fixed list**, the same discipline as Wave 1's
`FRAME_KEYS:49`:

```
me            employee, employee_name, designation, department, image, company   (six, as frame_api.ME_FIELDS)
today         date, shift {name, start, end} or None, checkin {time, type} or None, needs_location
needs         [{id, kind, title, detail, action, route}]           numbers and the caller's own facts only
leave         [{leave_type, total, used, left}]                    the caller's own
holidays      [{date, description, weekly_off}] , holiday_note
goals         the caller's own, and for a manager/HR the team summary (counts, no names below 5 — see §17)
team_today    {in, away, due, basis}                               counts only, never names or reasons
celebrations  {own_anniversary_years or None, joiners:[{name, designation, joined}]}
counts        the six part counts, so Home need not make a fourth call
```

Nothing else leaves the module. AC-5 asserts the key set per persona.

---

## 9. Every state, on both screens, per persona

A missing state is where a blank list gets mistaken for "you have nothing". Each cell
names the check that proves it.

### Home

| Persona | Loading | Empty / nothing due | No data | Error on one card | No permission | Page error |
|---|---|---|---|---|---|---|
| Rahul | skeleton ≤ 300 ms (AC-31) | "Needs you — All clear" (AC-3) | no holiday list → slice 035's "Ask HR to set one up"; no shift → no hero, not an empty hero (AC-4) | the card says what failed + Try again; the rest works (AC-32) | n/a — Home is everyone's | Wave 1's page-error sentence (AC-36) |
| Sandeep | AC-31 | "All clear", and the team cards still render (AC-3) | no reports yet → the team card is not drawn at all (AC-33) | AC-32 | n/a | AC-36 |
| Priya | AC-31 | AC-3 | HR scope empty → "No one is in your store's list yet. Ask HR if that looks wrong." (AC-33) | AC-32 | n/a | AC-36 |
| Kamal | AC-31 | AC-3 | AC-33 | AC-32 | n/a | AC-36 |
| Asha | AC-31 | "Your account is not linked to an employee record." — a plain line, no cards, **no errors** (AC-37) | AC-37 | AC-37 | AC-37 | AC-36 |
| Session ended | — | — | — | — | — | sent to `/login`, not the error state (AC-35) |

### Inbox

| Persona | Loading | Empty | No data | Error | No permission | Page error |
|---|---|---|---|---|---|---|
| Rahul | skeleton, never a spinner on blank (AC-31) | "All clear." (AC-12) | a part with nothing is not drawn (AC-12) | "The waiting list could not load. Try again." (AC-34) | a row he may not act on is never drawn, so there is no refusal state to reach (AC-17) | AC-36 |
| Sandeep | AC-31 | AC-12 | AC-12 | AC-34 | AC-17 | AC-36 |
| Priya | AC-31 | AC-12 | AC-12 | AC-34 | AC-17 | AC-36 |
| Asha | AC-31 | "All clear." with total 0 — **not** an error and **not** "no employee record" (AC-37) | AC-37 | AC-34 | — | AC-36 |
| Anyone, above the cap | — | — | "showing the first 50 of 60" (AC-11) | — | — | — |
| Anyone, a row decided elsewhere | — | — | — | "This one has already been decided." Row goes, counts refresh, no error page (AC-18) | — | — |

**Wording** (translatable, `__()`, taken from Wave 1 §6 where it exists there):

| Where | Exact words |
|---|---|
| Nothing waiting | "All clear." |
| Counts failed | "The waiting list could not load. Try again." |
| One card failed | "This could not load. Try again." |
| Above the cap | "Showing the first 50 of 60." |
| Already decided | "This one has already been decided." |
| No Employee record, on Home | "Your account is not linked to an employee record. Ask HR to link it if that looks wrong." |
| No holiday list | "No holiday list is assigned to you yet. Ask HR to set one up." *(slice 035's wording, unchanged)* |
| Peer card | "Who is in, and who is still to come. Nothing about why anyone is away." |
| Decline needs a reason | "Please say why, so the person knows what to do next." *(`attendance_correction.decide:743`'s wording, reused)* |

---

## 10. Acceptance criteria

Given / When / Then. Each one has an observable oracle.

### US-1 · Home leads with what needs you

- **AC-1** *Given* Rahul has one self-review not started and three days marked absent,
  *when* Home loads, *then* the first block below the hero is "Needs you" and it holds
  exactly two items, in that order, **and** `get_home`'s `needs` array has exactly two
  entries with `kind` `self_review` and `attendance_gap`.
- **AC-2** *Given* the decision taken in D-1, *when* Home loads for Sandeep with 2
  approvals, 1 unacknowledged policy, 1 open request of his own and 1 needs item,
  *then* **(option A, recommended)** the "Needs you" heading shows no number and the bell
  shows **4**; **or (option B)** the heading and the bell both show **4** and the heading
  reads "4 waiting on you". The test asserts one of these, chosen by D-1 — never both,
  and never the prototype's **3**.
- **AC-3** *Given* a brand-new tenant with no data at all, *when* Home loads, *then*
  "Needs you" reads "All clear", the page renders with no error and no empty card frames,
  and the check-in hero is still the largest element **if** the person has a shift.

### US-2 · the hero

- **AC-4** Four cases, all asserted on the rendered page and on the payload:

  | Case | What must happen |
  |---|---|
  | Shift Assignment for today exists | hero shows "Shift 09:30 – 18:30" from that assignment's Shift Type |
  | No assignment, `Employee.default_shift` set | hero shows the default shift's times |
  | Neither (Kamal) | **no hero at all** — not an empty hero and not a hero with blank times (009 design decision 6) |
  | Already checked in at 09:24 | the button reads "Check out" and the line reads "Checked in at 09:24" |

  A second tap within the duplicate window returns `field_checkin`'s existing refusal
  wording, not a new message.

### US-3 and US-10 · Home's own numbers, and only the caller's

- **AC-5 (the Wave 1 lesson)** `get_home`'s payload keys are exactly §8's list, per
  persona, and the `me` block holds exactly `employee`, `employee_name`, `designation`,
  `department`, `image`, `company`. It **never** carries `date_of_birth`, `gender`,
  `cell_number`, `date_of_joining`, `reports_to` or `branch`. A test asserts the key set,
  not the screen.
- **AC-6** *Given* Rahul whose Casual Leave ledger balance is 0 of 8, *when* Home loads,
  *then* the Leave-left card reads "0 of 8" — the ledger figure from
  `_ledger_leave_balances:88` — and a fully used type is **shown**, not hidden.
- **AC-7** *Given* Rahul, Chandigarh store, *when* Home loads, *then* the holidays shown
  are his own list's only (2 Oct, 9 Nov, 26 Jan), not head office's, and the 9 Nov row
  carries its real description.

### US-4 · one honest count

- **AC-8** For every part in §6.2 and every persona in §6.3, `part.count()` equals
  `len(part.rows(limit=None))`. The test enumerates parts from `parts()` itself, so a new
  part with no matching row fails the test.
- **AC-9** *Given* a person who is their own `leave_approver` with one open leave
  application of their own, *then* the total is **1**, it sits under "my requests", and
  part 1 (leave to approve) is **0**.
- **AC-10** *Given* one pending goal update in store A, one in store B and one for a
  head-office employee with no branch: store A's HR sees **1** in the count **and 1** in
  the row's list; company-wide HR sees **3 and 3**.
- **AC-11** *Given* 51 waiting attendance corrections in the caller's scope, plus one
  declined and one withdrawn correction **inside the first 50 by creation date**, *then*
  the count reads **51**, the list shows **50**, and the screen says "Showing the first 50
  of 51". A count that ignored the state filter would read 53 and fail.
- **AC-12** *Given* a part with nothing in it, *then* no row is drawn for it; *given*
  every part empty, *then* the Inbox reads "All clear."; *and* the rows hold numbers only
  — no names, no reasons, no document ids (asserted on the counts payload).
- **AC-13** *Given* Sandeep approves a leave request, *when* the action returns, *then*
  the row is removed, a toast is announced (`role="status"`), and the counts come from a
  **fresh server read** — a test asserts the browser does not decrement a stored number.
- **AC-14** A static check finds **no other pending-count query** left in the portal page
  or in `goals_api.get_pending_approvals_count:1410`'s callers: the bell, the menu item,
  the bottom-bar button and the Team badge all read `get_nav_counts`.
- **AC-15** *Given* any persona, `get_nav_counts` makes **no more than 15 queries** and
  `get_inbox` no more than **25**, whatever the team size, measured on a 1,000-employee
  fixture as company-wide HR.
- **AC-16** No boot path calls `goals_api.get_pending_approvals` or
  `hr_api.get_pending_approvals:2179`.

### US-5 · deciding

- **AC-17** *Given* a row is drawn in the Inbox, *when* its Approve is pressed, *then* it
  never returns a permission refusal — the list and the action share one scope function.
  The test drives every row of every persona fixture through its own action.
- **AC-18** *Given* two approvers, *when* the second one approves after the first, *then*
  the answer is "This one has already been decided.", the row disappears, the counts
  refresh, and **no second decision is written** (asserted on the document's
  `alvoraa_reviewed_by` / `docstatus`).

### US-6 · my requests

- **AC-19** *Given* Rahul's open leave, open correction and open shift request, *then*
  "my requests" lists three rows, each with a plain-word state ("Waiting for Sakshi
  Verma", "Approved", "Declined — <the reason he was given>") and a Withdraw button only
  where `attendance_correction.withdraw:700` would allow it.
- **AC-20** *Given* somebody else's request, *then* it never appears in his "my requests"
  list — the filter is his own **Active** Employee record.

### US-7 · fixing a day

- **AC-21** *Given* Rahul is marked Absent on 7, 8 and 9 Sep with no leave and no open
  correction, *when* he taps Fix, *then* the sheet opens with `from_date` 7 Sep and
  `to_date` 9 Sep pre-filled, and one Attendance Request is created covering the range
  (`raise_correction:659` already accepts `to_date`).
- **AC-22** *Given* the gap rule of §11, *then* the number in "3 days have no attendance"
  equals the number of day rows the Fix sheet lists. Same helper, same filter, as §6.1
  rule 1.

### US-8 · store HR

- **AC-23** *Given* Priya, store HR with no direct reports, *when* the Inbox loads,
  *then* every part is scoped to her store; head office's correction does not appear in
  the count or the list; her screen is **not empty** where her store has work.
- **AC-24** *Given* Priya has a direct report in another store, *then* that report's item
  still appears (Wave 1 SEC-3's union).

### US-11 · separation of duties

- **AC-25** For **each** of leave, attendance correction, shift request, goal update and
  KPI update: the caller's own item is not in their own approval count, not in their own
  list, and calling the decide action on it by hand is refused by
  `access.refuse_own_decision` with a logged refusal that carries no personal content.

### US-9 · the peer card

- **AC-29** *Given* Rahul's peer card, *then* it shows three numbers — In, Away, Still to
  come — the sentence "Who is in, and who is still to come. Nothing about why anyone is
  away.", and **no names, no leave types and no absence reasons** anywhere in the payload.
- **AC-30** The phrase "Nobody is on leave today" and any equivalent appears nowhere in
  the built page (static check on the include files).

### US-12 · states

- **AC-31** The Home and Inbox skeletons are in the server-rendered HTML and paint within
  **300 ms**, median of 5 loads, measured on "Slow 4G" with a 4× CPU slow-down
  (W1D-09's rig).
- **AC-32** *Given* the team-goals card's query fails, *then* that card shows "This could
  not load. Try again." and every other card on Home still renders.
- **AC-33** *Given* a manager with no reports yet, or an HR user whose scope is empty,
  *then* the team card is **not drawn at all** (manager) or carries the §9 no-data
  sentence (HR) — never an empty card frame and never a silent zero.
- **AC-34** *Given* `get_nav_counts` fails while `get_home` succeeds, *then* the bell
  shows no number, the Inbox page shows "The waiting list could not load. Try again." and
  Home works.
- **AC-35** *Given* the session has ended, *then* the browser is sent to `/login`, not to
  the page-error state.
- **AC-36** *Given* `get_home` fails, *then* the Wave 1 page-error sentence is shown with
  a Try again button and a code that holds no personal data.

### US-13 · no Employee record

- **AC-37** *Given* Asha, *then* Home shows one plain line and no cards, Inbox shows
  "All clear." with total 0, **no endpoint throws**, and no console error is raised. The
  same holds for a leaver whose login is still enabled, except that his own still-open
  requests are counted (Wave 1 SEC-14).

### US-14 · speed

- **AC-38** Home makes exactly **three** calls: `get_frame`, `get_nav_counts`, `get_home`.
  None waits on a timer.
- **AC-39** `get_home` answers within **500 ms at p95** over 20 warm calls as a manager
  with 19 reports, and no query runs inside a loop (asserted, not eyeballed).
- **AC-40** Home is usable within **2.5 s at p95** of 20 loads on the W1D-09 rig, with
  slice 036's compression live. Recorded before and after.

### Cross-cutting

- **AC-26** Every user-facing string added by this slice is inside `__()`, and no sentence
  is built by joining fragments.
- **AC-27** At 390 px, light and dark, on Home and Inbox for all five personas: no text
  under 12 px, no target under 44 px, no sideways scroll; the same passes with the Hindi
  test fixture loaded (W1D-12 — fixtures only, no Hindi shipped).
- **AC-28** An approval context line for a leave request says "2 other people in this team
  are away on those days" — **a number**. The payload carries no colleague name and no
  leave type. A fixture with two overlapping leaves of different types proves it.
- **AC-41** Every whitelisted function in `home_api.py` and `inbox_api.py` is in the
  registry test with its Guest-refused, wrong-persona and scope cases (Wave 1 SEC-2's
  mechanism). A new function with no entry fails the test.
- **AC-42** `home_api.py` and `inbox_api.py` contain no `ignore_permissions`, no `global`
  and no module-level dict, list or set changed at run time (Wave 1 SEC-6 and SEC-15).
- **AC-43** Every write from Home and Inbox is a POST with its arguments in the body; a
  log-capture test shows endpoint, user id, outcome and time, and **no name and no
  reason**, on a normal call and on a refused one.
- **AC-44** Home and Inbox add **no new include file** (static check counting the files
  under `templates/includes/ess/`), unless OPS-31 has landed first — see D-6. The check
  reads the count from one constant so it moves in one place when OPS-31 does.

### The edge cases that bite (each is a check)

- **AC-45** *New joiner.* Someone who joined on 12 Sep has **no** attendance gaps before
  12 Sep. The gap query starts at `date_of_joining`.
- **AC-46** *Leaver.* An employee set to Left mid-month: his own Home is unaffected while
  his login works; he appears in nobody's peer card and nobody's team card
  (`status = "Active"` on every people query — the rule Wave 1 W1D-20 had to spell out).
- **AC-47** *Rehire.* A person with two Employee records, one Left and one Active: every
  Home and Inbox query uses **the Active one**, through one "who am I" helper, so two
  cards cannot describe two different people.
- **AC-48** *Half day.* A half-day leave on a day with a check-in is **not** an attendance
  gap.
- **AC-49** *Back-dated leave.* Leave approved after the gap list was drawn removes that
  day from the next load, and the count moves with it.
- **AC-50** *Auto-marked absent.* A day marked Absent by the auto-attendance job **is** a
  gap (this is exactly Rahul's 7–9 Sep) — see D-5 if Surbhi decides otherwise.
- **AC-51** *Bulk.* On the demo tenant where 330 people were auto-marked absent on 7–9
  Sep, no Home call exceeds its query budget and the gap list is capped with "Showing the
  first 50 of N".
- **AC-52** *Holidays and weekly offs.* A holiday, a weekly off and a future day are never
  gaps. The holiday source is the employee's own list (slice 035), not the company's.
- **AC-53** *Time zone.* "Today" on Home is the **site's** date, not the browser's; a test
  with the browser set to a different time zone still shows the site's date.
- **AC-54** *Multi-company.* An HR user who looks after two companies sees both in their
  counts; a store HR user with a Branch permission sees their branch only.
- **AC-55** *Employee with no manager.* Home renders; the peer card is **not drawn**
  (there are no peers) rather than falling back to the department — see D-3.
- **AC-56** *Cancelled or amended documents.* A cancelled leave application
  (`docstatus = 2`) is in no count and no list; an amended one is counted once, under its
  current name.
- **AC-57** *Two tabs.* A decision in one tab leaves the other tab's count stale until its
  next load. Accepted, stated so a tester does not file it.
- **AC-58** *Concurrency.* Two HR users pressing Approve on the same correction within the
  same second: one succeeds, the other gets AC-18's sentence, and the document carries one
  `alvoraa_reviewed_by`.

---

## 11. The attendance-gap rule, written out

The count and the list share it (AC-22). **A day is a gap when all of these are true:**

1. it is on or after the employee's `date_of_joining`;
2. it is in the past (not today, not future);
3. it is **not** on the employee's own holiday list and **not** a weekly off on that list;
4. there is **no** Attendance record, **or** the Attendance record's `status` is `Absent`;
5. it is **not** covered by an approved **or pending** Leave Application;
6. it is **not** covered by an Attendance Request that is waiting or approved.

**Window:** the current month and the previous month. **Recommendation** — a wider window
turns a screen into a year's homework, and the correction flow is for recent days. D-5.

**Known data problems this rule meets on day one** (from appendix B §E, still true):

| # | Problem | What the spec does |
|---|---|---|
| E-1 | Demo check-ins stop on 6 Sep; 330 people auto-marked Absent 7–9 Sep | The rule counts them; AC-51 caps the list. **Demo data must be seeded before the build is tested**, or every test reads as a bug |
| E-2 | Portal expense claims have no `expense_approver` (`apply_expense_claim:1750`) | Wave 2 does **not** count or list expense approvals (§12). The defect is filed separately; this spec does not fix it and does not hide it |
| E-3 | `get_week_presence:3151` falls back to the department (40 of 207) and never shows "in" | Replaced — §3 and D-3 |
| E-4 | 2,002 unread Notification Log rows | The count **never** reads Notification Log. Stated so nobody reaches for `get_unread_notifications_count` |
| E-5 | `submit_attendance_request:1943` is a second, weaker correction path that skips the reason check | Not used by Wave 2. It is retired in **Wave 3** (043), not here |

---

## 12. Out of scope for Wave 2, and where it goes instead

| Thing | Where it goes |
|---|---|
| The Time screen, the calendar, the day list, the late rule, the leave screen | **Wave 3 (043)** |
| The Pay screen, payslips, "why was this deducted", year to date | **Wave 3 (043)** |
| Growth, the self-review wizard, goal evidence, the Team screen's look, the person sheet, the staff directory | **Wave 4** |
| Peer feedback and "ask for feedback" | **Wave 4, with its own go/no-go** (009 design decision 4) |
| Birthdays | **Dropped.** Q8 needs a DPDP advisor; `01b` §9 recommends never |
| Announcements | **Dropped for v1.** No doctype; Frappe `Note` is site-wide and holds 0 rows. Revisit with a brief, not inside this wave |
| Expense-claim and salary-advance approvals in the portal | **Dropped from Wave 2.** 034 §5's rule: count only what the portal can act on. Revisit when the approver defect (E-2) is fixed |
| The Activity feed | **Dropped from Home.** The existing panel is untouched |
| "Suggest a September target" for a new joiner (H-25) | **Wave 4** — it edits a goal |
| Hindi and Punjabi for users | **Wave 5.** Wave 2 wraps strings and measures in Hindi fixtures only (W1D-12) |
| Moving existing drawers into the shared sheet | **After OPS-31** |
| The org-chart company scope (`ALV-86`), the wider leaver fix (`ALV-87`), named logins (`ALV-93`) | Their own tickets; Wave 2 neither waits for them nor works around them |

---

## 13. Non-functional requirements for this slice

Measured on "Slow 4G" with a 4× CPU slow-down, cache off (W1D-09).

| What | Number |
|---|---|
| Calls on Home | **3** (`get_frame`, `get_nav_counts`, `get_home`), no timer |
| `get_nav_counts` | ≤ **15** queries, ≤ 500 ms p95 over 20 warm calls as company-wide HR at 1,000 employees — **Wave 1's budget; Wave 2 must not regress it** |
| `get_inbox` | ≤ **25** queries whatever the team size, ≤ 500 ms p95 |
| `get_home` | ≤ **20** queries, ≤ 500 ms p95 for a manager with 19 reports |
| Skeleton painted | ≤ 300 ms, median of 5 |
| Home usable | ≤ 2.5 s p95 of 20 loads, with slice 036's compression live |
| Every list | capped at **50**, with the true total shown |
| Background work | **None.** Nothing in Wave 2 takes more than 2 s, so nothing is queued. If the gap query ever does, it moves to the `short` queue and Home shows the loading state for that card only |
| Record volume assumed | 1,000 employees per tenant, 4 companies, 50 open requests per approver |
| Retention | **Nothing new is stored.** No new record, no new log line carrying personal data |
| Personal or sensitive fields | Names, job titles, photos (counts carry none); absence **facts** but never absence **reasons** |
| Accessibility | WCAG 2.2 AA; 390 px; 200 % zoom; 12 px floor; 44 px targets |

---

## 14. Data migration and backfill

**Nothing.** No schema change, no data change, no patch, no `bench migrate`.

**One thing that is not a migration and must still happen:** the local demo copy needs
seeding before Wave 2 can be tested honestly — check-ins after 6 Sep, a handful of open
requests that are **not** the owner's own, and at least one policy awaiting
acknowledgement (appendix B §E, D1 and D4). Without it every count is 0 and every test
passes for the wrong reason.

**Rollback:** the Home and Inbox panels are new routes behind Wave 1's frame. Reverting
the Wave 2 commits restores Wave 1's small counted-row Inbox and today's Home. About ten
minutes, the same as Wave 1's rollback (W1D-10).

---

## 15. Notifications and messages

**Wave 2 sends no email and creates no notification.** It reads queues that other code
already fills. The messages it shows on screen are in §9's wording table.

**What must never leak into a message:**

| Message | Must not carry |
|---|---|
| Any toast after a decision | the requester's leave type or reason |
| The approval context line | a colleague's name or leave type (AC-28) |
| The page-error code | anything personal — it is a time plus a short reference matching an Error Log entry |
| Any refusal logged by `access.log_refusal` | names, search terms, per-person counts (Wave 1 PRIV-5) |

**One existing message worth naming:** `attendance_deduction.py`'s manager email carries
the explanation including loss of pay when `notify_manager` is on. **Wave 2 does not touch
it** — it is Wave 3's question (043 §20) — but nothing in Wave 2 may quote that
explanation on screen.

---

## 16. Localisation and accessibility

- Every string added is wrapped in `__()`; no sentence is assembled from fragments
  (AC-26). Counts go into a message as a whole phrase with a placeholder, so Hindi and
  Punjabi word order works.
- Dates, times and currency go through the existing formatter. The hero's clock is the
  **site's** time (AC-53).
- Measured at 390 px in light and dark with the Hindi fixture (AC-27). Hindi and Punjabi
  run about 30 % longer; bottom-bar-adjacent labels must wrap to two lines rather than
  clip.
- **Rahul is a shop-floor worker with no laptop.** On a phone: the check-in hero is the
  largest thing on the page; "Needs you" is above the fold; an approval can be taken with
  one thumb; nothing needs a horizontal scroll; inputs are 16 px so the phone does not
  zoom on focus.
- Colour is never the only signal — every chip says its state in words.
- The shared sheet traps focus, closes on Escape and returns focus to the control that
  opened it (Wave 1's FR-09; `01b` §9 records that it was not yet prototyped).

---

## 17. Audit and traceability

| What must be reconstructable | How |
|---|---|
| Who approved or declined what, and when | The source doctypes already record it: Leave Application's workflow fields, Attendance Request's `alvoraa_reviewed_by` / `alvoraa_reviewed_on` / `alvoraa_review_note`, Shift Request's own fields, the goal and KPI approval rows. **Wave 2 writes through the existing actions so this keeps working** — it never sets a status with `db_set` of its own |
| Why a decline happened | The reason is mandatory on a decline and is stored on the document (`decide:743` already enforces it); Wave 2 keeps that for every decide path |
| Who read a queue | **Not recorded today.** Wave 1's residual risk R3 owns this (logging first step by 2026-10-15). Wave 2 adds no new signal and does not pretend to |
| Small groups | Any aggregate on Home that describes a group (the team goal summary, the peer counts) follows `01b` §9: suppressed under five, and the next smallest group suppressed with it. For the peer card that means: **under five peers, show the sentence and no numbers.** AC-29's fixture includes a four-person team |

---

## 18. Compliance-impact sub-analysis

*The analyst is not a lawyer. Nothing below is a legal ruling.*

### 18.1 Data touched

| Field / object | Sensitivity | Purpose it was collected for | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| Own name, designation, department, photo, company | internal | identify the signed-in person | employment contract (as recorded in `01c` baseline) | No |
| Own leave balances, own holidays | internal | administer leave | employment / statutory | No |
| Own attendance records and gaps | sensitive — a pattern of absence can imply health | attendance and payroll | employment / statutory | No |
| Colleague presence (in / away / due), as **counts** | internal | let a team see who is on the floor | legitimate operational need | No |
| Colleague absence **reason** | sensitive | — | — | **Never shown.** Not collected by this slice and not displayed by it |
| Counts of pending work | aggregate | tell a person work is waiting | operational | No |
| Own payslip existence and take-home, on the "payslip ready" row | sensitive | pay | statutory | No — own record only |

**Nothing new is collected.** Every field this slice shows is already in the database for
a purpose already recorded.

### 18.2 Obligations engaged

| Obligation | Source | What this slice must do | Feature that does it |
|---|---|---|---|
| DPDP minimisation | `security-compliance-baseline.md` §5 | Send only what the screen draws | AC-5's fixed key list; AC-12's numbers-only counts |
| DPDP access rights | baseline §4 | Every queue scoped on the server | AC-10, AC-23, AC-24, AC-25 |
| Logging duties — no personal content | baseline §5, CERT-In | Refusals and search logged without names | AC-43 |
| OWASP ASVS 5.0 L2 access control | baseline §4 | List and action share one scope | AC-17, AC-41 |
| Purpose limitation on absence data | baseline §5 | Presence yes, reason never | AC-29, AC-30 |

**Checked `compliance-feature-map.md` first:** the refusal log (`access.log_refusal`) and
the small-group suppression rule already exist and are **reused**, not respecified.

### 18.3 Visibility delta

| Who | Can now see | Could they before? |
|---|---|---|
| Rahul | his own attendance gaps as a list | Yes — in the month calendar, less clearly |
| Rahul | peer counts: in / away / still to come | **Narrower than today.** `get_week_presence:3151` today falls back to the whole department, 40 of 207, and shows the viewer's own weekly offs for everybody. Wave 2 replaces it with the caller's own peers |
| Sandeep | one queue instead of three broken ones | Same data, reachable today, mostly failing |
| Priya (store HR) | her store's queue | **Narrower** — Wave 1 already narrows counts and search; Wave 2 keeps the same scope for the lists |
| A leaver | nothing | **Narrower** (Wave 1 SEC-14) |
| Anyone | a colleague's absence reason | **No — and it is not shown anywhere, in any state, on either screen** |
| Anyone | a colleague's leave type in a context line | **No** (AC-28) |
| Any manager | a report's loss-of-pay amount | **No** (Q-b) |

**Nothing gets wider.**

### 18.4 Decision automation

**No decision about a person is automated.** Every approval and every decline is taken by
a named human, and the decline requires a reason that the person receives. The system
orders and counts; it never decides.

The one place a machine could act and deliberately does not: the attendance gap. The
product **could** raise a correction automatically. It must not — a correction is the
employee's own account of their day, and generating it would put words in their mouth and
remove the only place they get to say what happened.

**No AI in this slice.** No rating, no inference, no emotion or voice or facial analysis,
no passive behavioural monitoring, no individual-level surveillance. §18.7 is therefore
empty by construction, and the prohibitions are not approached.

### 18.5 Retention and deletion

**Nothing changes.** Wave 2 stores nothing new. The counts are computed live and never
cached to disk. Theme and layout preferences stay on the device (Wave 1 PRIV-6).
Counsel's binding periods (GPS 30 days, performance records employment + 6 months) are
**not engaged** because no new record is created.

### 18.6 Open compliance questions

| Question | Who must decide | What it blocks |
|---|---|---|
| Are birthdays shown at all, and on what basis (Q8)? | Surbhi, with a DPDP advisor | Nothing in Wave 2 — birthdays are out of scope until that answer exists |
| Does the peer card's "away" count, in a team of four, let a colleague infer who is away? | Surbhi, with the security engineer | The small-group rule in §17 is my recommendation (show the sentence, hide the numbers under five); AC-29 tests it |

### 18.7 AI features

**None.** Nothing in this slice is AI-shaped, so there are no guardrails to specify and
nothing to refuse.

---

## 19. Traceability

| Source | ID or line | Story | Acceptance criteria | Status |
|---|---|---|---|---|
| Plan §4 Wave 2 | "Needs you worked out from real state" | US-1 | AC-1, AC-2, AC-3 | covered |
| Plan §4 Wave 2 | "check-in with shift" | US-2 | AC-4 | covered |
| Plan §4 Wave 2 | "leave left from Frappe HR" | US-3 | AC-6 | covered (reuses slice 035) |
| Plan §4 Wave 2 | "own holidays" | US-3 | AC-7 | covered (reuses slice 035) |
| Plan §4 Wave 2 | "team today" | US-9 | AC-29, AC-30, AC-55 | covered |
| Plan §4 Wave 2 | "celebrations (no birthdays in v1)" | — | — | **partly — anniversaries and joiners need D-4; birthdays dropped (§12)** |
| Plan §4 Wave 2 | "the combined inbox and decision calls" | US-4, US-5 | AC-8 to AC-18 | covered |
| Plan §4 Wave 2 | "separation of duties" | US-11 | AC-25 | covered |
| Plan §4 Wave 2 | "context lines" | US-5 | AC-28 | covered |
| Plan §4 Wave 2 | "replaces broken F1 for good" | US-4 | AC-14, AC-16 | covered |
| Plan §4 Wave 2 | "demo data seeded on the local copy" | — | §14 | **not an AC — a build precondition, named in §14** |
| Appendix B | H-01 to H-28 | US-1 to US-3, US-9 | AC-1 to AC-7, AC-29 | covered, except H-23 (birthdays, dropped), H-25 (Wave 4), H-28 (Activity dropped) |
| Appendix B | IN-01 to IN-23 | US-4 to US-6, US-11 | AC-8 to AC-25 | covered, except IN-04 (announcements, dropped), IN-09/IN-17 (expenses, dropped), IN-18 (advance, dropped), IN-19 (HR-only types, dropped) |
| Design `01b` §14 item 1 | no greyed items | — | Wave 1 034 AC-6 | covered in Wave 1 |
| Design `01b` §14 item 2 | one Inbox count | US-4 | AC-8, AC-9, AC-10, AC-11 | covered |
| Design `01b` §14 item 9 | no screen shows an absence reason | US-9 | AC-29, AC-30 | covered |
| Design `01b` §14 item 10 | small-group suppression | — | AC-29, §17 | covered |
| Design `01b` §14 item 13 | skeleton 300 ms, boot approvals check gone | US-12, US-14 | AC-31, AC-16 | covered |
| Design `01b` §14 item 14 | strings wrapped, measured in Hindi | — | AC-26, AC-27 | covered |
| 009 design decision 1 | manager decides an attendance fix, HR after 2 days | US-4, US-5 | AC-23, and **D-2** | **open — D-2 blocks the corrections part** |
| 009 design decision 3 | who's off: presence only | US-9 | AC-29, AC-30 | covered |
| 009 design decision 6 | check-in hero only with a shift | US-2 | AC-4 | covered |
| W1D-01 | Pay stays without payroll | US-1 | the "payslip ready" row is drawn only where `plan_payroll`; AC-5's payload | covered |
| W1D-02, W1D-20 | persona table, Active Employee required | all | AC-37, AC-46, AC-47 | covered |
| W1D-20 | Team follows HR scope | US-8 | AC-23, AC-33 | covered (Home's team card follows the same scope) |
| W1D-05, W1D-14 | corrections queue scoping, HR only | US-8 | AC-23, and **D-2** | **open** |
| Wave 1 SEC-2 | every endpoint safe on its own | — | AC-41 | covered |
| Wave 1 SEC-3 | approvals scope, store HR union | US-8 | AC-10, AC-24 | covered |
| Wave 1 SEC-6, SEC-15 | no `ignore_permissions`, no module state | — | AC-42 | covered |
| Wave 1 SEC-12 | fixed payload key list | US-10 | AC-5 | covered |
| Wave 1 SEC-14 | leaver finds nobody | US-13 | AC-37, AC-46 | covered |
| Wave 1 PRIV-4 | counts are numbers only | US-4 | AC-12, AC-16 | covered |
| Wave 1 PRIV-5 | POST bodies, clean logs | — | AC-43 | covered |
| DevOps OPS-31 / 009 strategy decision 12 | cached script files | — | AC-44, **D-6** | **open — it decides Wave 2's build order** |
| DevOps OPS-17 / W1D-09 | measurement rig | US-14 | AC-31, AC-40 | covered |
| Prototype | Home hero, Needs you, Coming up, Leave left, Celebrations, Inbox tabs | US-1 to US-6 | as above | covered, with §21's differences |

**Gaps, listed rather than hidden:** the celebrations row (needs D-4); the corrections
routing (needs D-2); the Home number (needs D-1); the build order (needs D-6).

---

## 20. Needs a decision

Six. Each would change what gets built; nothing here is a nice-to-know.

| # | Question | My recommendation |
|---|---|---|
| **D-1** | **Home's "Needs you" heading shows a number that is not the Inbox number** (§6.4). Which is it? | **No number on Home.** The bell and the menu are the one number. Home shows the items; the badge shows the total. One number in the product is the whole point of Q5 |
| **D-2** | **009 design decision 1 says the manager decides an attendance fix and HR steps in after two working days.** The code sends every correction to whoever holds submit permission on Attendance Request — HR in practice (`_may_review:240`). Does HR see a manager's corrections **from day one** (visible, not actionable, until day 3) or **only after two working days**? And is "two working days" counted on the employee's own holiday list or the company's? | **HR sees every correction from day one and may act on any of them from day three**, with the row labelled "with <manager> until <date>". A backstop nobody can see is not a backstop. Count **two working days on the requester's own holiday list**, because that is the list the rest of the product already uses. The manager's count includes his own from day one; HR's count includes only the ones past day two, so no correction is counted twice |
| **D-3** | **Peer "team today": who are the peers?** Today the code falls back to the whole department (40 of 207) when the viewer has no reports (`get_week_presence:3183`). | **People with the same manager, and no fallback.** Someone with no manager sees no peer card at all (AC-55). A department is not a team, and a 207-person "team" card is worse than no card |
| **D-4** | **Celebrations: whose anniversaries and which new joiners?** (Q9) | **Own work anniversary only, plus new joiners in the viewer's own branch in the last 30 days.** Branch is the unit a shop-floor worker recognises. Company-wide would put 403 people's joinings on one card |
| **D-5** | **The attendance-gap rule** (§11): does a day the auto-attendance job marked Absent count as a gap, and is a two-month window right? | **Yes, it counts** — that day is unpaid and it is exactly the case Rahul has. **Two months** — current and previous. Anything older belongs on the Time screen (Wave 3), not on Home |
| **D-6** | **Build order against the Jinja template cliff.** Wave 1 could fit only four include files; a fifth costs +97 %. Wave 2 adds two panels. Does OPS-31 (move style and script into static files) come **before** Wave 2's build? | **Yes — bring OPS-31 forward, ahead of Wave 2.** The engineer recommended the same in `034/03-implementation-notes.md` §4 and it is the same answer for both waves. Without it, Wave 2's markup, CSS and JavaScript all land inside Wave 1's four files, and Wave 3 then edits the same four files — two sessions in one file, which is what the split was for |

---

## 21. Differences from the approved prototype

The prototype is a review artifact. **It is not changed**; this table is the record, the
same way Wave 1 recorded its five.

| # | Prototype | Built | Why |
|---|---|---|---|
| a | Home's "Needs you" heading shows "N open" = needs + approvals | Per D-1 — recommended: no number | §6.4. Two unlabelled numbers on one screen |
| b | Manager approval cards on Home are tagged **Sample** and are invented | Real approvals from the six parts | D8 said sample cards become real rules or stay tagged |
| c | Peer "team today" shows "6 in / 1 away / 1 still to come" as **Sample** counts | Real counts from the caller's own peers | D-3 |
| d | "Fix" on an absent day goes to the manager (`FIX_GOES_TO = "manager"`) | Per D-2 | 009 design decision 1 chose the manager; the code sends it to HR today |
| e | Inbox has tabs "Waiting on me" / "My requests (n)" | Kept, and "My requests" is one of the six counted parts | — |
| f | "Your August 2026 payslip is ready · Take-home ₹44,052" row | Kept, **only where the tenant has `plan_payroll`** | W1D-01 |
| g | "Give feedback" and "Welcome" quick actions | **Not built.** No backend exists | Feedback is Wave 4 with its own go/no-go (009 design decision 4) |
| h | Coming up shows a weekly off, a public holiday and "Store closed Mon 9 Nov" | Kept, from the employee's **own** holiday list | slice 035 |
| i | The owner's Home leads with "PP Jewellers right now" | **Out of scope.** The owner/HR screens keep their current look inside the new frame | Plan §4, "Later — owner/HR screens" |
| j | Prototype search / rail / bottom bar | Wave 1's, not Wave 2's | Wave 1 already recorded its own five differences, including the desk link (W1D-19) |

---

## 22. Ready check

| Box | State |
|---|---|
| Brief approved | ✓ — the 009 plan (Wave 2) and the decisions stand in for `01` |
| Clickable prototype reviewed | ✓ 22 Sep, with §21's differences recorded |
| `01c` security and privacy written | **✗ — not written for this slice.** Wave 1's `01c` covers the shared helpers; Wave 2 adds new endpoints and needs its **own** `01c` before the build. This spec names what it expects (§5's negatives, §18) but does not replace it |
| `07` DevOps inputs written | **✗ — not written for this slice.** D-6 is the one that matters and is raised here |
| Every state designed and specified per persona | ✓ §9 |
| Gap analysis verified in source | ✓ §3, with file and line |
| Stories: personas, sized, "must not" stories | ✓ §7 — US-9, US-10, US-11, US-13 are the "must not" stories |
| Every story has checks with observable oracles | ✓ §10 |
| Traceability complete | ✓ §19, with four gaps listed |
| Permission matrix with negatives | ✓ §5 |
| Edge cases | ✓ §10 AC-45 to AC-58 |
| NFR numbers | ✓ §13 |
| Migration stated | ✓ none (§14) |
| Compliance sub-analysis | ✓ §18 |
| No prohibited capability | ✓ nothing AI-shaped, no monitoring |
| Open questions owned, none blocks day 1 | **✗ — D-2 and D-6 block the build.** D-6 blocks the first commit; D-2 blocks the corrections part |

**Verdict, plainly: this slice is NOT ready to build.** Three things are missing — its own
`01c`, its own `07`, and answers to D-2 and D-6. The spec is ready; the slice is not. I am
saying so rather than passing a soft spec downstream.

---

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | D-1 — the Home number | Surbhi | AC-2, and one line of Home's markup |
| 2 | D-2 — who decides an attendance fix, and when HR sees it | Surbhi | The corrections part of the count and the list; a permission change |
| 3 | D-3 — who counts as a peer | Surbhi | The peer card, and whether `get_week_presence` is rewritten or retired |
| 4 | D-4 — celebrations scope | Surbhi | One query and one card |
| 5 | D-5 — the gap rule's boundaries | Surbhi | The gap query, and the number on Home |
| 6 | D-6 — OPS-31 before Wave 2 | Surbhi, with DevOps | The build order and where Wave 2's code lives |
| 7 | Peer counts in a team under five (§18.6) | Surbhi, with the security engineer | AC-29's fixture, not the build |

## Assumptions

- `[ASSUMPTION]` Wave 1 ships `inbox_api.get_nav_counts` and the six parts. **It has not
  been built yet** — `alvoraa_portal/inbox_api.py` does not exist on `origin/dev` at
  `8718f27`. If Wave 1 ships without it, §6.1's helper is Wave 2's first commit and the
  build grows by about a day.
- `[ASSUMPTION]` Frappe's `"not in"` filter wraps the column in `ifnull()`, so a NULL
  `alvoraa_review_status` counts as waiting. Confirm on the bench before the count is
  written; §6.1 rule 3 carries the fallback.
- `[ASSUMPTION]` Field names on Shift Request (`approver`, `status`) and Leave Application
  (`leave_approver`, `status`) match what §6.2 needs. Read from the calling code, not from
  the doctype JSON; confirm before the first query.
- `[ASSUMPTION]` Employee does not allow the same `user_id` on two Active records, so
  "the Active one" is singular (AC-47). Confirm on the bench.
- `[ASSUMPTION]` Slice 035 (leave ledger, own holidays, goal cycles) and slice 017 (late
  minutes and grace) are on `origin/dev` — **verified at `8718f27`**, so this is a
  confirmed fact, recorded here because Wave 2's numbers depend on it.

## Handoff note

**To the security and privacy engineer:** this slice needs its own `01c` and three things
deserve your eye first. **The count helper** (§6.1) is where a scope mistake becomes a
number a manager trusts. **The peer card** (§5, AC-29) is the one place an absence reason
could leak by inference rather than by disclosure. **`get_home`'s key list** (AC-5) is
Wave 1's own lesson repeated — the payload, not the screen, is the control.

**To the DevOps engineer:** D-6 is yours. Wave 2 cannot be shaped until OPS-31's place in
the order is settled, and the answer serves Wave 3 too.

**To the fullstack engineer:** build the count helper first and the screens second. Every
number on both screens comes out of `parts()`, and the day somebody writes a second filter
"just for the badge" is the day the number stops matching the list.

**To the test engineer:** three checks are easy to get wrong. **AC-8** must enumerate the
parts from `parts()` itself, or a new part ships untested. **AC-11** must put the declined
and withdrawn rows *inside* the first 50 by creation date, or it proves nothing. **AC-17**
must drive every drawn row through its own action, not a sample.
