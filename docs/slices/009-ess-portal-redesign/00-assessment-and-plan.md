---
slice: 009-ess-portal-redesign
artifact: 00-assessment-and-plan
author: Claude (lead), from four read-only analyst reviews
date: 2026-09-14
status: draft
inputs: [prototype https://claude.ai/code/artifact/a78f9f44-6ff8-4b5f-8335-4046d32972ec, portal UX review https://claude.ai/code/artifact/43eebf35-96e7-4c6c-9172-ab2780f6beb1, docs/slices/002-ess-home-redesign, docs/slices/003-ess-mobile-responsive, appendix-a-frame.md, appendix-b-home-inbox.md, appendix-c-time-pay.md, appendix-d-growth-team-people.md]
---

# Employee portal redesign: what it takes, and how to build it

## The short answer

**It can be built.** Most of the data the prototype shows already exists on the server.

**It cannot be built as drawn, and not first.** Four things stand in the way:

1. **Today's portal shows wrong numbers**, and the redesign would put them on bigger, clearer
   screens: late minutes, leave left, holidays, "team today", and goal percentages.
2. **There are live security and privacy holes** in the screens the redesign rebuilds.
   The worst: an employee's self-review can change a colleague's goal progress. Managers'
   browsers receive a report's loss-of-pay amount. Any employee can search every employee
   in every company.
3. **The prototype needs corrections before it is final.** Some are design problems that
   would break existing screens. Others are data it copied from the wrong source.
4. **About 60 decisions are open.** Around 20 of them block the first waves (section 6).

**Recommendation:** fix what is wrong today first (Wave 0). Build the new frame next
(Wave 1). Then build the screens in four waves, and languages last. Rough total: **8 to 11
weeks of build time**, plus time waiting for decisions and translation review.

## How this was assessed

On 14 Sep 2026 four analysts read the prototype, part by part, against the real code on
`dev` (`30e2d13`). They checked the local copy of PP Jewellers (`ppj.localhost`) using
read-only queries, as Rahul (employee), Sandeep (manager of 19) and Kamal (owner with HR).

| Area | Requirements | Detail |
|---|---|---|
| Frame: menu, top bar, bottom bar, search, sheet, theme, language | 19 (FR) | [appendix-a-frame.md](appendix-a-frame.md) |
| Home and Inbox | 28 (H) + 23 (IN) | [appendix-b-home-inbox.md](appendix-b-home-inbox.md) |
| Time and Pay | 17 (T) + 13 (P) | [appendix-c-time-pay.md](appendix-c-time-pay.md) |
| Growth, self-review, Team, People | 12 (G) + 8 (SR) + 9 (TM) + 8 (PE) | [appendix-d-growth-team-people.md](appendix-d-growth-team-people.md) |

That is **137 requirements**. Every one carries its current status, the work needed, a
size, and the evidence (file and line). The requirement IDs are meant to travel into the
specs.

**Not covered:** real iPhone or Android devices, browser rendering of the new screens,
email delivery, and the owner/HR persona (it is not in the prototype).

**One incident during the review:** an analyst used `docker cp` to put a small read-only
script in the local bench. That command needs approval. The file was removed. Nothing in
the app or its data changed.

---

## 1. What is wrong today (fix before redesigning)

These are live problems. Each has evidence in an appendix.

### 1a. Security and privacy — most urgent

| # | Problem | Where | Appendix |
|---|---|---|---|
| S1 | **The self-review writes to records the employee does not own.** It takes goal and KPI names from saved JSON and sets progress and ratings, with no ownership check and no change history | `performance_api.submit_employee_review` :3575-3597 | D · B4 |
| S2 | **Goal evidence approves itself**, and evidence files are **public links** | `goal_api.submit_goal_evidence` :66; upload `is_private=0` (page :9084) | D · B2, B3 |
| S3 | **Employees can read manager-only fields** on their own review: internal notes, potential rating, and the overall rating before release | list API; `get_my_appraisals` :3195 | D · B6 |
| S4 | **Managers can read a draft self-review** before it is sent. The HR guard is skipped in the manager-review endpoints. Reviewers get every page | :3649, :2310, :3754, :3976, :3889 | D · B7–B9 |
| S5 | **Managers' browsers receive a report's loss-of-pay amount** (₹548.39 for Rahul) | `hr_api.get_team_late_list` :2472-2497 | C · F-3 |
| S6 | **People search shows every employee in every company** to anyone. The org chart skips its own "how far can you see" limit | `search_people`, `search_employees`, `my_view`, `chain_to_top` | A · #3; D · B11 |
| S7 | **HR can approve their own requests** | `attendance_correction.decide` :723, `approve_kpi_update` :372 | B · E9 |
| S8 | **Goal and employee names are not escaped** in the goal drawer, so a script can be planted in a goal name | page :8742-8745 | D · B21 |
| S9 | **A notification helper pushes a script to the browser** (`eval_js`) | `performance_api` :3121 | D · B26 |
| S10 | **HR leave-on-behalf and balance lookups are not limited to HR's own companies** | `hr_api` :1527, :1653 | C · F-10 |

### 1b. Wrong numbers people see

| # | Problem | Evidence | Appendix |
|---|---|---|---|
| W1 | **Every employee's late minutes are wrong.** Two helpers share one cache; a 09:30 shift is judged from 09:00. Rahul shows 27 late days in August; the rule counted 4. Affects every tenant. | `attendance_correction` :500/:516 vs `attendance_analytics` :177 | C · F-1 |
| W2 | **Leave left is overstated.** Days taken by the late-coming rule are ignored. Rahul: portal 3, Frappe HR 0. | `hr_api` :177-201, :1549-1575 | B · E1; C · F-2 |
| W3 | **Holidays come from every holiday list in the company**, not the employee's own | `hr_api` :236-253 | B · E3 |
| W4 | **"Team this week" shows the wrong people** (the whole department, across stores), uses the viewer's weekly offs, and never shows anyone "in" today | `get_week_presence` :2797 | B · E4; D · B19 |
| W5 | **Goal percentages mix review cycles**, and team reviews pick an arbitrary cycle | `hr_api` :913-930; `performance_api` :721 | D · B16, B17 |
| W6 | **The org chart names a different manager** than the reporting line (Rahul: Sandeep Gupta vs Sakshi Verma). This is a data fix for HR. | `my_view` vs `Employee.reports_to` | D · B12 |
| W7 | **The payslip PDF uses Frappe's generic layout**, not PP Jewellers' format | Salary Slip default print format unset | C · F-4 |

### 1c. Broken calls

| # | Problem | Appendix |
|---|---|---|
| B1 | **Team View approvals fail (F1).** It is worse than first reported: the approve and reject calls point at functions that don't exist, and the page expects a different data shape. It cannot simply be re-pointed. | B · E5-E6; D |
| B2 | **Create Goal's call has a wrong path (F2)**, and behind it the template lookup never finds a template | D |
| B3 | **The org chart asks for HR-only numbers (F3)** on every chart move, not just once | D |
| B4 | **Declining leave for someone else's report crashes** (a missing import) | B · E7 |
| B5 | **Goal check-ins return a server error** (a column that does not exist) | D · B1 |
| B6 | **Leave encashment from the portal probably always fails** (two required fields are never set) | C · F-5 |
| B7 | **New future goals get an invalid status**, and the error is hidden | D · B5 |
| B8 | **The Q2 self-review has no goals page** (empty cycle setup) | D · B14 |
| B9 | **The old "Attendance Request" screen is still live** beside the newer correction flow. It skips the reason check and shows "Draft". | B · E11; C · F-6 |
| B10 | **Expense claims made in the portal have no approver** | B · E10 |

### 1d. Too slow

| # | Problem | Appendix |
|---|---|---|
| P1 | **The bell's approvals check runs 1.5 seconds after every page load, for everyone.** It makes 706 queries for a manager and **takes 11.6–16.4 seconds for HR**. It must be replaced, not tuned. | A; B · E8; D |
| P2 | `get_my_goals` makes 138 queries, `my_view` 31, and `get_team_late_list` 31. Each asks one person at a time. | D · §D |

---

## 2. What the prototype must change before it is final

| # | Change | Why |
|---|---|---|
| D1 | **Phone layout: use `@media` rules, not a container query on the whole app** | The container query pins about 30 existing pop-ups to the app box instead of the screen (A · #1) |
| D2 | **Add a profile menu:** log out, My Account, switch to desk, Tenant Admin, language, theme | Removing Frappe's website bar (a phone fix) removes log out. The prototype has no in-product place for these (A · #5) |
| D3 | **Design the owner/HR view** (Kamal): Analytics, Org Settings, Performance setup, Calibration, Policy compliance | Kamal has 17 screens today; the prototype's "Company" group holds one (A · #4) |
| D4 | **Raise small sizes:** bottom-bar labels from 10px, icon buttons from 38px, buttons from 36px and 30px, chips from 11px. Text colour `#8E857D` → `#736D65` | Fails the 44px tap target and 12px text rules, and slice 002's 4.5:1 contrast rule (A · §D, §F) |
| D5 | **Correct the data it copied:** Casual Leave 8 of 8 used (not 5 of 8); Sakshi manages 13 (not 9); 7–9 Sep are "Marked absent" (not "No punch and no leave"); the real holiday text; "more than 60 minutes" (not "60 or more") | Appendix C · F-13, T-07; B · E1 |
| D6 | **Remove "Nobody is on leave today" from the peer view** | It tells colleagues leave apart from absence, which slice 002 rules out (B · C) |
| D7 | **Decide who fixes attendance:** the prototype sends corrections to the manager; the built flow sends them to HR | B · H-07, IN-14 |
| D8 | **Replace "Sample" cards with real rules, or mark them for later:** team status today, goal evidence, example approvals, advance limit and repayment, Form 16 | No data source today (C, D) |

A UX designer run should make these changes, then you do the **design check**
(go / change / drop). That check is the gate before any screen is built.

---

## 3. How to build it: the decisions that shape everything

1. **Keep one page, but split its code into separate files** (Jinja includes, the same way
   `design_system.html` is included today). No build step is needed, and parallel sessions
   edit different files. The first commit only moves code — nothing changes on screen — and
   it teaches every existing check to follow the includes, or those checks would quietly
   check less (A · §F).
2. **One menu list drives everything**: rail, bottom bar, titles, page search, visibility
   rules. Each wave plugs in through `ess.onOpen`, `ess.openSheet`, `toast` and
   `ess.counts`, and never edits `switchPanel` (A · §G).
3. **New server modules in `alvoraa_portal`**, not in the vendored `hrms`:
   - `inbox_api.py` — one inbox call and one decision call (B · §B)
   - `home_api.py` — one Home call
   - one Team call
   - a permission-scoped directory and search call

   Bug fixes inside our own `hrms` modules (late rules, org structure) stay where the code lives.
4. **One "today" function** (in / away / still to come) serves Home, Team, People and Time.
   **One approvals service** serves Inbox and Team (B · §F, D · §F).
5. **Reuse Frappe HR** instead of rebuilding:
   - `get_leave_details` / `get_leave_balance_map` (leave left)
   - `get_holidays_for_employee` (holidays)
   - the `hrms.api` approval filter rules
   - Salary Slip year-to-date fields
   - Frappe's own translation system (`__()` and `.po` files)
6. **A query budget per screen, with a test for each.** Target 500 ms or less at the 95th
   percentile:

   | Screen | Calls | Queries |
   |---|---|---|
   | Home | 3 | — |
   | Inbox | 1 | about 25, whatever the team size |
   | Team | 1 | 15 or fewer |
   | Time | 1 | about 40 |
7. **Parallel work follows `.claude/context/parallel-work.md`**: own worktree, work board, the
   hot-file rules, and a test that pins every feature.

---

## 4. The waves

Every wave goes through the normal gates:

1. design check (where screens change)
2. security and privacy requirements
3. functional spec
4. impact analysis → **you approve the strategy**
5. build and test on the local copy
6. review, security review and release readiness
7. **you decide to push to dev**, and later to main

Sizes are rough build days for one engineer, including tests. They are refined in each
wave's impact analysis. **They do not include waiting for decisions or translation review.**

### Wave 0 — Fix what is wrong today (before and alongside everything else)

Small, separate changes. Each can go to dev on its own. They touch server files, mostly
not the portal page, so they can run in parallel with Wave 1.

| Part | Items | Size |
|---|---|---|
| 0a Security and privacy | S1–S10 | 5–7 days |
| 0b Wrong numbers | W1–W5, W7 (W6 is HR's data fix) | 3–4 days |
| 0c Broken calls | B1 (stop the error; the real fix comes with Inbox), B2–B10 | 3–4 days |
| 0d Speed | P1: stop the boot-time approvals check; add a cheap count | 1 day |

**Outcome:** the current portal is safe and correct. Every later screen starts from true
data. Some of these are serious enough that I recommend doing 0a first, whatever happens
to the redesign.

### Wave 1 — The frame (menu, top bar, bottom bar, sheet, search, theme)

Build order from Appendix A §G:

1. Remove Frappe's website bar, and add the profile menu with log out. This fixes phone
   causes R1–R3 on its own.
2. Split into includes, and teach the checks to follow them.
3. Menu list and one start-up step.
4. Routes, titles and focus.
5. Shared sheet and toast.
6. Count-only call and the bell pointing at the Inbox slot.
7. Scoped search.
8. Theme switch.
9. Language plumbing (switch and `__()`, English only).

Every existing screen moves in unchanged.

**Also fixes these phone-audit gaps:** M01, M03, M07, M08, M11, M16, M20.
**Needs first:** decisions Q1–Q5 (section 6) and design corrections D1–D4.
**Size:** 6–8 days.

### Wave 2 — Home and Inbox

- **Home:** "Needs you" worked out from real state; check-in with shift; leave left from
  Frappe HR; own holidays; team today; celebrations (no birthdays in v1).
- **Inbox:** the combined inbox and decision calls, covering leave, attendance corrections,
  shift requests, goal and KPI updates and evidence; separation of duties; context lines.

This replaces broken F1 for good. **Also needs:** demo data seeded on the local copy
(check-ins stop on 6 Sep, 330 people were auto-marked absent, and almost no open requests
exist).

**Needs first:** decisions Q6–Q14. **Size:** 7–9 days.

### Wave 3 — Time and Pay

- **Time:** calendar and day-by-day list on the fixed late minutes; your shift; days off
  ahead; who's off (presence only); late rule explained from the real rule fields;
  corrections and leave from a tapped day; retire the old calendar and the old
  Attendance Request screen.
- **Pay:** payslip summary; "why was this deducted" following the real chain from slip line
  to extra salary entry to the week's late records; year to date from stored slip fields;
  PDF in the tenant's format.

**Needs first:** decisions Q15–Q20. Wave 0b must be done. **Size:** 6–8 days.

### Wave 4 — Growth, self-review, Team and People

- **Growth:** the guided 5-step self-review on existing endpoints, with debounced autosave
  and a notification to the manager on send; goals with evidence on one progress model;
  open action items.
- **Team:** one Team call, needs attention, late this week, on leave, new joiners, and one
  person sheet.
- **People:** a permission-scoped directory and search.
- **Feedback** (give and ask) needs a new record type. This is the largest single item.

**Needs first:** decisions Q21–Q28. Wave 0a must be done. **Size:** 10–13 days
(about 4 of them for feedback).

### Wave 5 — Languages

- Each wave already wraps its text in `__()`.
- This wave adds `hi.po` and `pa.po`, enables Hindi, and creates Punjabi as a language on
  each tenant.
- It adds a Hindi/Punjabi-capable font, and dates in the chosen language.
- **A native speaker and the tenant's HR must review the HR terms.**
- Size: 4–6 days, plus review time.
- Frappe HR's own server messages are only partly translated into Hindi, and not at all
  into Punjabi (Q29–Q30).

### Later — owner/HR screens

They stay in their current look inside the new frame until they are designed (D3).

### Order and overlap

```
Wave 0a ─ 0b ─ 0c ─ 0d ─────────────┐   (server files; runs alongside Wave 1)
Wave 1 frame ───────────────────────┤
                                    ├─ Wave 2 Home + Inbox ─┬─ Wave 3 Time + Pay ─────┐
                                    │                       └─ Wave 4 Growth/Team/People┤
                                    │                          (3 and 4 can overlap,     │
                                    │                           separate include files)  │
                                    └──────────────────────────────── Wave 5 languages ──┘
```

**Rough total: 42–55 build days (about 8–11 weeks)** with one engineer line. Wave 0 and
Wave 1 can overlap, and so can Waves 3 and 4, which shortens the calendar if two sessions
work in parallel under the parallel-work rules.

---

## 5. What already works and is reused

Much of the plan is new screens on existing, working server code:

- **Check-in** with location rules; **apply leave** with preview; **attendance corrections**
  with reasons and withdraw
- **Payslip ownership** (commit `30e2d13`); **the late-coming rule and its deduction records**,
  which form a clean, traceable model
- **The review model and status flow**; the PPJ 5-point rating scale; company values;
  manager 1:1 notes
- **Attendance Insights views**; upward feedback totals with a minimum group size
- **Design tokens** for light and dark (slice 002)

---

## 6. Decisions I need from you

These block the waves they are listed under. Every other open question sits in its appendix.

**Decided by Surbhi on 2026-09-14**

| # | Question | Decision |
|---|---|---|
| Q0 | Is the prototype the direction, with corrections D1–D8? | **Yes.** The UX designer updates the prototype, then the design check |
| Q-a | Late from the exact shift start, or after a grace period? | **The grace period is each organisation's own setting.** Lateness uses the grace configured on that tenant's Shift Type, never a hard-coded number |
| Q-b | May managers learn a report's loss of pay? | **Agreed: days at most, never the amount** |
| Q-c | Whom may people search find? | **Only their own reporting hierarchy, downwards.** Open point to confirm in 010's strategy: what a person with no reports finds (themselves only?), and what HR finds |
| Q-d | May managers see a self-review before it is sent? | **No** |
| Q-e | Leave left from Frappe HR's ledger, including late-rule days? | **Yes** (Rahul's Casual Leave will show 0) |

Wave 0a (security and privacy) runs as slice `010-portal-security-fixes`, started 2026-09-14.

**Wave 1 (frame)**
- **Q1** Where do owner/HR screens go: one Company group, or a separate Admin group? (A · H-1)
- **Q2** Bottom-bar buttons for HR, and for an employee with no payroll? (A · H-2)
- **Q3** Where do the language and theme switches live, and is the theme saved per device or per user? (A · H-4)
- **Q4** "People": a directory (prototype) or today's org chart? (A · H-5)
- **Q5** Inbox count: approvals only, or also policies to acknowledge and my own open requests? (A · H-7)

**Wave 2 (Home and Inbox)**
- **Q6** Who decides attendance corrections: HR (built) or the manager (prototype)?
- **Q7** Peers' "team today": same manager or department?
- **Q8** Birthdays: never, HR switch only, or with consent? (Consent under DPDP needs an advisor.)
- **Q9** Scope for anniversaries and new joiners: team, branch or company?
- **Q10** Announcements: Frappe Note, a scoped build, or drop for v1?
- **Q11** Self-review "due" date: cycle end or its own deadline, and lock after it?
- **Q12** Which days count as attendance gaps, and do auto-marked absent days count?
- **Q13** Salary advance and expense claims: approved in the portal (and by whom), or on desk for v1?
- **Q14** HR's inbox: own reports, or the whole company's goal and KPI queue?

**Wave 3 (Time and Pay)**
- **Q15** Who's off: may employees see colleagues on approved leave, and from which group?
- **Q16** "This year": financial or calendar year?
- **Q17** Take-home: net pay or the rounded amount paid?
- **Q18** Loss of pay uses base pay ÷ calendar days. Is that agreed? **(This is a payroll/legal question — not ruled on here.)**
- **Q19** Salary advance: limit, instalments and approver (instalments need the lending app or HR-made salary entries)?
- **Q20** Late-rule wording: change the words to "more than 60", or change the code to "60 or more"?

**Wave 4 (Growth, Team, People)**
- **Q21** Who is someone's manager: the reporting line or the org chart? (HR must fix the mismatch either way.)
- **Q22** Who approves goal evidence, and does progress move only after approval?
- **Q23** Values in the self-review: pick 2 with an example, or rate all 7 criteria? Which master list?
- **Q24** Rate goals or KPIs, and whole or half points?
- **Q25** Peer feedback: a new record type or extend Frappe HR's? Who sees it? Is "Ask for feedback" in?
- **Q26** Team scope: direct reports only, or everyone below?
- **Q27** "Needs attention" rule: stored trajectory or a percentage, and how are new joiners handled?
- **Q28** Directory: what "Leadership" means, and whether colleagues can see work phone and email (opt-in?)

**Wave 5 (languages)**
- **Q29** Who writes and reviews Hindi and Punjabi, and may tenant HR edit wording?
- **Q30** Is English acceptable for server error messages in Punjabi at first?

---

## 7. Suggested next steps

1. **You:** answer Q0 and the Wave 0 questions (Q-a to Q-e).
2. **Start Wave 0a (security and privacy) on the local copy now.** It does not depend on
   the design, and several of these holes are live today.
3. **In parallel, the UX designer updates the prototype** with D1–D8 and a first owner/HR
   view. Then **you do the design check**.
4. Then Wave 1 through the normal gates.

---

## Open questions

All of section 6. Owner: product owner, except Q8 and Q18, which also need an advisor
(DPDP privacy, and payroll/legal).

## Assumptions

- [ASSUMPTION] Line numbers and query counts are as of `dev` at `30e2d13` on the local
  copy, single runs with a warm cache.
- [ASSUMPTION] Build-day sizes assume one engineer line, the local bench, and decisions
  answered before each wave starts.
- [ASSUMPTION] Jinja includes render identically to inline code on this www page. Wave 1
  step 2 must prove this before anything else builds on it.
- [ASSUMPTION] Demo data can be seeded on the local copy through `demo/` scripts. Nothing
  is written to dev tenants without your word.

## Handoff note

To the product manager and UX designer (Q0, D1–D8): the prototype's direction holds, but
it currently hides several real problems behind good-looking sample data. Fix the design
before the design check.

To the fullstack engineer (Wave 0): the security items in 1a are real, and several are
reachable today by any logged-in employee. Treat them as their own small changes with tests
that pin them. Do not fold them into the redesign.

To everyone: approvals, "today" status and the person sheet are each shared by several
screens. Build each one once.
