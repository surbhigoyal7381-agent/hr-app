---
slice: 009-ess-portal-redesign
artifact: appendix-b-home-inbox
author: hrms-business-analyst (read-only review, run 2026-09-14)
date: 2026-09-14
status: ready
inputs: [prototype a78f9f44 (p3-data.js, p4-core.js, p5-home-inbox.js), hrms-employee.html, hr_api.py, goals_api.py, performance_api.py, attendance_correction.py, ppj.localhost data]
---

# Appendix B — Home and Inbox

Read-only review. Bench date 14 Sep 2026; prototype set on 11 Sep.

## The answer first

Five things on today's Home screen show wrong data or are broken (each backed by a query on the local bench):

1. **Leave balances are wrong.** Portal: Rahul has 3 Casual Leave days left. Frappe HR ledger: 0, because the late-coming rule took 3 days. The portal counts only leave applications (`hr_api.py:177-201`, same code at `1549-1575`). The prototype copied the wrong "3 of 8".
2. **Holidays come from the wrong list.** `get_employee_dashboard` reads every holiday list in the company and removes duplicates (`hr_api.py:236-253`). Rahul (Chandigarh store) is shown Head Office holidays.
3. **"Team this week" is wrong.** With no reports it shows the whole department (40 of 207, alphabetical). Weekly offs come from the viewer's own list (Sandeep's 19 reports use 5 different weekly offs, all shown off on Tuesday). Today can never show "in" — it reads Attendance, created only after shift processing (`hr_api.py:2824-2862`, `2870-2880`).
4. **Goal and KPI approvals are broken (F1 confirmed), and the bell is slow for HR.** `hr_api.get_pending_approvals` raises ImportError. `approve_kpi_progress` / `reject_kpi_progress` point at functions that exist nowhere. The bell calls `goals_api.get_pending_approvals` 1.5 s after every page load: **16.4 s for Kamal** (budget 500 ms).
5. **Declining someone else's leave can crash.** `action_leave` uses `_()` without importing it (`hr_api.py:584, 590`) — a NameError instead of "Only X can action this".

**Demo data will mislead tests:** check-ins stop on 6 Sep; the auto-attendance job marked **330 people Absent** on 7–9 Sep; the only waiting requests company-wide are Kamal's own attendance correction and KPI update — and Kamal, as HR, could approve both himself.

## A. Requirement table

Status: **exists**, **partial**, **missing**, **sample-only**. Personas: E employee, M manager.

### Home

| ID | What the person sees or does | Personas | Data needed | Existing source (verified) | Status | Work needed | Size | Risk / open question |
|---|---|---|---|---|---|---|---|---|
| H-01 | Greeting, first name, date | E, M | Employee name | `get_checkin_status` (1233) returns full employee row | exists | Trim payload (DOB, phone not needed) | S | — |
| H-02 | Check in / out, "Checked in at 09:24" | E, M | Today's Employee Checkin | `get_checkin_status` (1233-1264), `do_checkin` (1283-1315) | partial | Reuse `field_checkin._refuse_duplicate` (354) and `_geofence_message` (374-402) | S | — |
| H-03 | Shift time on hero | E, M | Active Shift Assignment → Shift Type | Not in any Home payload | missing | Add to payload | S | — |
| H-04 | Store name | E, M | Employee.branch | `_get_employee` (88) | exists | Client | S | — |
| H-05 | Location rule | E, M | HR Settings; Shift Location radius | `checkin_needs_location` (1267) | exists | Say "Location needed" only when `needs_location` | S | All 6 Shift Locations have radius 0 — no geofence enforced at PPJ |
| H-06 | Needs you: self-review due / started / sent | E | Appraisal, extension status, pages done, cycle end | `get_my_appraisals` (3146); `get_my_review` (3255) creates a record on read (3273) | partial | Light read in inbox endpoint, no create-on-read | M | No self-review deadline field |
| H-07 | Needs you: "3 days have no attendance" → Fix | E | Past Absent / no-record days not covered by leave or open correction | `attendance_correction.month` (357), whole month, ~6 queries | partial | Smaller "problem days" query; Fix sheet | M | Prototype sends fixes to manager; code sends to HR (609). Demo gap |
| H-08 | Needs you items real data has but prototype omits | E | Final review to acknowledge; returned review; reviewer invite; policies; missing documents | `get_my_appraisals`; `get_my_policies` (2611); `get_my_documents` (2502) | partial | Fold into inbox endpoint | S each | Which count as "needs you" |
| H-09 | Manager needs you: approvals in place | M | IN-13..IN-19 | Home shows leave only (225-232 + `homeActionLeave` 8294) | partial | Inbox endpoint | M | — |
| H-10 | Manager: "8 reviews are waiting for you" | M | Reports in Manager Review | `get_team_reviews` (672-750) | missing on Home | Count + item | S | Not in prototype; real data has 8 of 19 |
| H-11 | Manager: "2 people need a look at Q2 goal" | M | Reports' goals, trajectory | `get_team_goals` (2148-2183) | partial | Server filter | S | Real: Kabir 0% Off Track, Neha 72% At Risk |
| H-12 | "N open" / "All clear"; items turn Done | E, M | Real state | Prototype: browser storage | missing | Server computes done; no manual dismiss for obligations | S | — |
| H-13 | Quick actions | E, M | — | Apply leave, Fix attendance, payslip, 1:1 note exist | partial | "Give feedback", "Welcome" have no backend | S/L | Peer feedback belongs to Growth |
| H-14 | My goals card with evidence status | E, M | Individual Goal + evidence | `get_goals_portal_data` (1923-2003) | partial | Evidence label sample-only; all Q2 goals are drafts → "Draft" badge (client 8615) | S | One Goal Cascade query per goal |
| H-15 | Leave left "X of Y" | E | Ledger balance | `get_employee_dashboard` (177-201) **wrong**; client reads `total_leaves` (6421, 6427), server sends `total` (196) | partial, wrong | Reuse `hrms.api.get_leave_balance_map` (hrms/api/__init__.py:381) or `get_leave_details`; fix key | S | Rahul's CL changes 3 → 0 on screen |
| H-16 | Coming up: weekly off | E | Next weekly_off holiday on own list | None | missing | Server | S | — |
| H-17 | Coming up: public holidays | E, M | Own holiday list | Dashboard wrong (236-253); Frappe HR `get_holidays_for_employee` (409-427) | partial, wrong | Reuse Frappe HR; stop cutting at 31 Dec | S | — |
| H-18 | "Store closed Mon 9 Nov" | E, M | Holiday description | Real row "Diwali next day (store closed for stock-take)" | exists | None | — | — |
| H-19 | Manager's team today (peer view): In / Away / Still to come | E | Peers (same `reports_to`), today's checkins, approved leave, per-person holidays and shift | `get_week_presence` (2797) | partial, wrong | Peers by manager; "in" from Employee Checkin; per-person holidays | M | "Nobody is on leave today" tells peers leave apart from absence — slice 002 rules that out |
| H-20 | Manager "Your team today" | M | Same, for direct reports | `get_manager_dashboard` Attendance (314-321), leave (327-335) | partial | Same fix | M | "Still to come" rule needed |
| H-21 | Celebrations: own work anniversary | E | `date_of_joining` | None | missing | Server | S | — |
| H-22 | New this month; Welcome | E, M | Recent joiners | Count only in `get_hr_analytics` (393) | missing | Server | S | Scope: team, branch or company? |
| H-23 | Birthdays | — | `date_of_birth` (all 403 set) | Frappe HR emails (off at PPJ) | not in prototype | — | — | Privacy decision |
| H-24 | Team Q2 goals bar | M | Reports' goals | `get_team_goals` | partial | Prototype 75% buckets invented; stored `trajectory` disagrees | S | Use stored trajectory? |
| H-25 | "Suggest a September target" for new joiner | M | Goal start < joining date | Real case Kabir | sample-only | Server rule; action opens `goals_api.update_goal` (463) | M | Manager confirms |
| H-26 | Manager's own goals | M | — | `get_goals_portal_data` | exists | Client | S | — |
| H-27 | Inbox count on bell, rail, bottom bar | E, M | Needs + approvals | Bell: goal/KPI only (12195-12222); team badge leave only (8370) | partial | Counts from inbox endpoint | S | — |
| H-28 | Cards the prototype drops: Activity, Documents, Policies, year holiday navigator | E, M | — | `get_portal_activity` (610), `get_my_documents`, `get_my_policies` | exists | Drop or fold into Needs you | S | Owner decision |

### Inbox

| ID | What the person sees or does | Personas | Data needed | Existing source (verified) | Status | Work needed | Size | Risk / open question |
|---|---|---|---|---|---|---|---|---|
| IN-01 | Tabs "Waiting on me" / "My requests (n)" | E, M | Counts | — | missing | Client from endpoint | S | — |
| IN-02 | Waiting on me: needs items | E, M | H-06..H-12 | — | — | Same as H-06..H-12 | — | — |
| IN-03 | "Your August payslip is ready · Take-home ₹44,052" | E | Latest Salary Slip | `get_payslips` (1378) | partial | Latest slip only | S | Only the employee |
| IN-04 | Announcements | E, M | — | No announcement doctype; Frappe `Note` (0 rows) | missing | Reuse Note or drop v1 | M | Note is site-wide |
| IN-05 | My leave requests with approver name | E, M | Leave Application | `get_leave_summary` (1577) | partial | Endpoint | S | Only 3 leave apps in tenant |
| IN-06 | My attendance corrections + Withdraw | E, M | Attendance Request + review fields | `attendance_correction.my_requests` (635), `withdraw` (685) | exists | **Retire** `hr_api.submit_attendance_request` (1803) | S | — |
| IN-07 | Change of shift status | E, M | Shift Request | `get_requests_history` (1866) | partial | Endpoint | S | Both PPJ shift types are 09:30–18:30 |
| IN-08 | Salary advance status | E, M | Employee Advance | same (1900) | partial | Plain status words | S | — |
| IN-09 | Expense claims | E, M | Expense Claim | `get_expense_claims` (1492) | partial | Endpoint | S | **Portal creates claims without `expense_approver`** (1627-1643) |
| IN-10 | Leave encashment | E | Leave Encashment | `get_requests_history` (1876) | partial | Endpoint | S | Not in New request sheet |
| IN-11 | Goal evidence, KPI progress, goal update | E | Three child tables | Per document only (perf 402, goals 1077) | partial | One query per child table | S–M | Three models; pick one |
| IN-12 | New request sheet (leave, correction, shift, advance) | E, M | — | Existing endpoints | exists (separate forms) | Client sheets | M | Advance limit/repayment sample-only; advance has no approver field |
| IN-13 | Approve/decline leave in place | M | Open leave, `leave_approver` = me | `get_employee_dashboard` (225); `action_leave` (572) | exists | Fix `_` import | S | 0 open leave in demo |
| IN-14 | Approve/decline attendance fix | M (prototype) / HR (code) | Attendance Request drafts | `to_review` (707), `decide` (723), gated on submit permission (HR only) | exists for HR | Decision, then Workflow or manager rule | M | Decline needs reason (751) |
| IN-15 | Approve evidence / KPI progress / goal update | M | Pending child rows | Working: `approve_kpi_update` (372), `approve_goal_update` (1046), `approve_goal_evidence`. Broken: F1, `approve_kpi_progress` (2056). Client expects `goals`/`kpis`+`idx` (8417-8470); working function returns `kpi_updates`/`goal_updates`+`row_name` | partial | One query per child table; call working actions | M | Evidence approval by row position breaks on reorder; mixed manager checks |
| IN-16 | Approve shift change | M | Shift Request Draft, `approver` = me | None in portal | missing | Small action | S–M | HR-fallback approver may be rejected |
| IN-17 | Approve expense claim | M | Expense Claim | None | missing | Action or desk for v1 | M | Accounting side effects |
| IN-18 | Approve salary advance | M | Employee Advance drafts | None | missing | Approver rule / Workflow | M | Open question |
| IN-19 | Leave encashment, comp-off approvals | HR | Drafts | Desk only | missing | If HR inbox in scope | S each | HR not designed |
| IN-20 | Context lines on approvals | M | Overlapping leave, day's checkins, goal effect | — | sample-only | Bounded queries | M | Never name leave types |
| IN-21 | Approver sees requester's note | M | description/note | Present | exists | Named approver only | — | — |
| IN-22 | Nobody approves their own request | HR, M | employee ≠ me | **Missing** in `decide` and `approve_kpi_update` | missing | Server check in each action | S | Separation of duties |
| IN-23 | After action: row disappears, toast, counts drop | M | — | Client decrements by hand (8307-8325) | partial | Re-read counts | S | — |

## B. Proposed combined Inbox endpoint

New module `alvoraa_portal/inbox_api.py`. Reads only; reuses Frappe HR doctypes and existing permission rules.

**`get_inbox(sections="counts,needs,approvals,mine", limit=10)`** — `limit` capped at 50.

```
{
  counts:    {needs, approvals, my_open},
  needs:     [{id, kind, title, detail, due_date, done, action: {go | act, arg}, doc: {doctype, name}}],
  approvals: [{key, kind, doctype, name, row_name, employee, employee_name, image,
               summary, note, context, created, can_approve, can_decline, decline_needs_reason}],
  mine:      [{kind, doctype, name, title, detail, state, state_label,
               waiting_on_name, decided_on, decision_note, can_withdraw}],
  more:      {approvals: bool, mine: bool}
}
```

- `needs.kind`: `self_review`, `final_review`, `review_returned`, `review_invite`, `attendance_gap`, `policy_ack`, `document_missing`; managers also `reviews_to_write`, `goal_attention`.
- `approvals.kind`: `leave`, `attendance_request`, `shift_request`, `expense_claim`, `kpi_progress`, `goal_update`, `goal_evidence`.
- `mine.state`: `waiting`, `approved`, `declined`, `withdrawn`, `cancelled`, `paid` (reuse `attendance_correction._state` for corrections). Labels in `_()`.

| Kind | Query rule (one query each) | Action it calls |
|---|---|---|
| leave | `status=Open, docstatus=0, leave_approver=user` (as `hrms.api.get_filters`) | `hr_api.action_leave` |
| shift_request | `status=Draft, docstatus=0, approver=user` | new `decide_shift_request` |
| expense_claim | `approval_status=Draft, docstatus=0, expense_approver=user` | new action, or desk (v1) |
| attendance_request | if `_may_review()`; draft; review Waiting | `attendance_correction.decide` |
| kpi_progress | KPI Progress Log ⋈ KPI, Pending, KPI.employee in my reports | `performance_api.approve_kpi_update` |
| goal_update | Goal Progress Update ⋈ Individual Goal, same | `goals_api.approve_goal_update` |
| goal_evidence | Goal Evidence ⋈ Individual Goal, Pending | evidence approve, by **row name** |

Every list filters `employee != me`. HR sees goal/KPI queues for own reports by default; company-wide only with explicit `scope=all`, paged.

**`decide(kind, name, approve, row_name=None, note=None)`** — dispatcher. Checks `employee != me` and still-waiting, calls the existing action, returns fresh `counts`. No new permission rules.

**Permissions in the endpoint:** "mine" filtered on the session's own employee id; approvals limited to the named approver (or the owner's manager for goal/KPI rows); HR only where HR decides by design; only on-screen fields returned.

**Query count:** fixed regardless of team size — about 22–25 for a manager (setup 3, needs ~6, approvals 7, mine 9). Add a query-count test (`nfr-budget.md:64`); target < 500 ms p95 (`nfr-budget.md:57`).

**Reuse from Frappe HR:** filter rules `hrms.api.get_filters`, `get_leave_applications`, `get_shift_requests`, `get_attendance_requests` (hrms/api/__init__.py:168-272); `get_leave_balance_map` (381); `get_holidays_for_employee` (409); `get_unread_notifications_count` (101) — but 2,002 unread "Employee document expired" alerts exist, so the bell must not count raw Notification Log rows; realtime `hrms.refetch_resource` (shift_request.py:57-60) for later live refresh. Do not add ToDo for approvals.

## C. Permission and privacy rules

| Who | May see | Must not see |
|---|---|---|
| Employee | Own requests, states, decision notes; own balances, payslip, check-ins | Any colleague's request, leave type, reason, balance, payslip. Peers: In / Away / Still to come only |
| Line manager | Requests where named approver, incl. note; reports' goal/KPI updates; which reports are on leave | Requests for people he does not approve; advances/expenses unless named approver; own requests in own queue |
| HR (not designed) | Attendance corrections for the company; HR-only request types | **Own requests in any approval queue** (Kamal can approve his own today) |
| Peer | Presence only | "Nobody is on leave today" (breaks slice 002 brief `01-product-brief.md:246`) |

- Approval context lines may be shown to the approver; never name a colleague's leave type.
- Payslip update: employee only; no take-home in notification or email previews.
- **Birthdays:** recommend not on Home in v1. If wanted: HR switch, day and month only, ideally consent. Not a legal ruling — needs an advisor on DPDP.
- Anniversaries and joiners: work data, lower risk, still pick a scope.
- Location: asked only when pressing the button, only where switched on (built).

## D. Non-functional notes

**Home load today (manager): 12 calls** — `get_portal_context`, `get_checkin_status`, `get_portal_activity`, `get_employee_dashboard`, `get_available_features`, `get_my_documents`, `get_my_policies`, `get_week_presence`, `get_switch_target`, `get_goals_portal_data`, `get_team_goals`, and `goals_api.get_pending_approvals` 1.5 s later for everyone (`hrms-employee.html:6473-6568, 7580-7704, 12222`).

**Proposed: 3 calls** — `get_portal_context` (cached), new `get_home` (check-in + shift, ledger balance, holidays, celebrations, team today, own and team goals), `get_inbox(sections=counts,needs,approvals, limit=5)`. Remove the boot-time bell call.

**Queries inside loops:** `goals_api.get_pending_approvals` (1147-1196) — 16.4 s HR, 0.8 s Sandeep, must be replaced; `get_my_appraisals` invited list (3218-3227); `get_goals_portal_data` (1971-1983); dashboard holidays (all 21 lists).

**Caching:** never cache approvals or needs; holidays and shift times via Frappe document cache; keep portal-context cache.

**At 400+ employees:** every proposed query is filtered by me, my approver email or my direct reports; HR company scope must be paged.

## E. Bugs and data problems

| # | What | Evidence |
|---|---|---|
| E1 | Leave balance ignores late-rule deductions | `hr_api.py:177-201`; PPJ-0058 ledger +8, −5, −3; Frappe HR says 0, portal 3 |
| E2 | Home drops "of Y", hides fully used types | client `b.total_leaves` (6421, 6427) vs server `total` (196) |
| E3 | Holidays from every list | `hr_api.py:236-253`; Rahul shown 20 Oct, 8 Nov, 24 Nov, 25 Dec; his list: 15 Aug, 2 Oct, 9 Nov, 26 Jan, 23 Mar |
| E4 | Week presence wrong group, weekly offs, never "in" | Rahul "department", 40 rows, all off Thursday; Sandeep all 19 off Tuesday; week starts Sunday |
| E5 | F1 confirmed | ImportError; same missing target breaks `approve_kpi_progress`/`reject_kpi_progress` (2056-2064) |
| E6 | Approval renderer expects a different shape | client 8417-8461 vs goals_api.py:1198-1202 |
| E7 | `_` not imported in `action_leave` | `hr_api.py:584, 590` |
| E8 | Bell costs 16.4 s for HR on every page | `hrms-employee.html:12222` |
| E9 | HR can approve own requests | `decide` (723), `approve_kpi_update` (372) |
| E10 | Portal expense claims have no approver | `apply_expense_claim` (1627-1643) |
| E11 | Two attendance-request paths | `submit_attendance_request` (1803) skips reason check; history shows docstatus words (7789) |
| E12 | Reading a review creates a record | `get_my_review` → `_get_or_create_extension` (3273) |
| E13 | Web check-in: no double-tap guard, raw geofence message | `do_checkin` (1283-1315) vs `field_checkin.py:354, 374` |
| D1 | Demo check-ins stop 6 Sep; 330 auto-Absent 7–9 Sep; no attendance after 9 Sep | Bench |
| D2 | All Shift Location radii are 0 | Bench |
| D3 | All Q2 Individual Goals are drafts | Bench |
| D4 | Almost no open requests; the two waiting items are Kamal's own | Bench |
| D5 | 2,002 unread Notification Log alerts | Bench |

## F. Dependencies

- **Frame:** counts, sheet, toast, routes, manager/HR flags, `_()` labels, removal of boot-time bell call.
- **Time:** attendance month and correction flow; apply leave; ledger balance (E1 affects both).
- **Pay:** payslip route.
- **Growth:** self-review; evidence; peer feedback / "Welcome" (no backend).
- **Team:** `get_team_reviews`, 1:1 notes, goal edit for the new-joiner suggestion.
- **People:** search, person cards.
- **Decisions / seed data:** shift, expense, advance approvals; correction decider; demo data after 6 Sep plus open requests.

## G. Open questions

| # | Question | Blocks |
|---|---|---|
| 1 | Attendance corrections decided by HR (built) or line manager (prototype)? | H-07, IN-14 |
| 2 | Peer "team today": department (slice 002) or same manager (prototype)? Remove "Nobody is on leave today" for peers? | H-19 |
| 3 | Confirm leave balance from Frappe HR ledger (Rahul's CL shows 0, not 3) | H-15 |
| 4 | Birthdays: never, HR switch, or with consent? | H-23 |
| 5 | Anniversaries and joiners scope: team, branch, company? | H-21, H-22 |
| 6 | Announcements: Frappe Note, scoped build, or drop v1? | IN-04 |
| 7 | Self-review "due": cycle end or separate deadline? | H-06 |
| 8 | Attendance gap rule: which days, do auto-Absent days count? | H-07 |
| 9 | Salary advance approver (Workflow?) and limit rule? | IN-12, IN-18 |
| 10 | Expense claims in portal or desk for v1? Copy `expense_approver` from employee? | IN-09, IN-17 |
| 11 | HR inbox contents; company-wide goal/KPI queue or direct reports? | B, IN-19 |
| 12 | Team goal buckets: stored trajectory or 75% cut-off? | H-24 |
| 13 | Declined leave needs a reason? | IN-13 |
| 14 | Which of documents, policies, final-review ack, reviewer invites are "Needs you"? Drop Activity feed? | H-08, H-28 |
| 15 | New-joiner target suggestion in scope? | H-25 |

**Could not check:** whether Frappe HR fills `expense_approver` server-side; Shift Request approver validation with HR fallback; Employee Advance repayment fields; `get_my_policies` performance at 400; every boot-time call in the page.

## Open questions / Assumptions / Handoff note

- **Open questions:** section G (owner: product owner).
- **Assumptions:** [ASSUMPTION] `inbox_api.py` lives in `alvoraa_portal`, not the vendored `hrms`. [ASSUMPTION] query counts measured once, warm cache.
- **Handoff note:** Inbox and Team approvals are the same list — build one approvals service once. Fix E1, E3, E7 and E9 before any new Home screen shows the numbers more prominently.
