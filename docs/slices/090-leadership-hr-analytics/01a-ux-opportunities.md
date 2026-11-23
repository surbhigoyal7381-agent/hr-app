---
slice: 090-leadership-hr-analytics
artifact: 01a-ux-opportunities
author: hrms-ux-designer
date: 2026-11-23
status: draft, for the product manager
mode: opportunities scan (no prototype)
tier: 2 (new screens, report logic). Tier 1 elements inside it: who sees which scope, small-group hiding, and any list of leavers by name.
---

# 090 · Leadership and HR analytics: opportunities scan

**Ask (Surbhi, 23 Nov 2026):** a richer HR analytics view for leadership and HR, matched to the competitors and useful to both. It needs filters and cumulative pictures. Examples: left within 3 months, 1 month, 1 week; cumulative windows of 1 year, 6 months, 3 months, 1 month, 1 week. Added the same day: attendance trends and leave trends.

**Bad news first**

1. **The leadership view that slice 012 designed does not exist in this tree.** I found no leader route or screen. Only the HR-only HR Analytics page exists (proven, below). The 012 design is the nearest ready answer. Reuse it.
2. **Today's HR Analytics cannot answer either of your two examples.** It has no leavers at all, and it has no time window the reader can change.
3. **Early attrition depends on data HR must keep clean.** A leaver with no relieving date cannot be placed in any window.

Labels: **proven** = I opened the file this session. **inferred** = reasoned from proven facts. **not checked** = I did not look. I could not open a live page; I did not open the running portal, so I describe code, not what a person sees on screen. Tree read: worktree `090-leadership-hr-analytics`, branch `slice/090-leadership-hr-analytics`, from origin/dev. Employee fields were read from the ERPNext JSON inside container `alv089-bench` (read only).

---

## 1 · What already exists (reuse before new)

| # | Surface | What it shows | Who | Proof |
|---|---|---|---|---|
| E1 | **HR Analytics page** (`panel-analytics`, nav "HR Analytics"). `team.html` lines 123-200; data from `get_hr_analytics` in `hr_api.py` line 821 | Six cards: Active employees, New joiners (month), Attendance rate, Pending approvals, Confirmations due, Leave utilisation. Then department bars, gender ratio, "Org Health (Month)" (days present / absent, pending leaves), top 10 designations, confirmations due, recent joiners. Server also returns branch split and joiners for 6 months | HR Manager, HR User, Administrator only. Hidden when the tenant plan lacks `plan_analytics` (`next-frame.js` line 127) | proven (code) |
| E2 | Scope on E1 | Limited to the caller's companies, and to their branches for location HR. Not linked to any company = shows a "not linked" page, no numbers | HR | proven (`hr_api.py` 829-846, `org_figures.hr_scope`) |
| E3 | `org_figures.py` | The one shared calculation: `attendance_figures`, `leave_figures`, `people_figures` (active, total, joiners between two dates), `data_up_to`, `open_doubtful_counts` | engine for E1 | proven (function names) |
| E4 | "Data to review" page (`company/data`) and `data_review.py` | Counts of doubtful days and figures marked "Needs review" | HR | proven (route and module; contents not read in depth) |
| E5 | **Attendance Insights** panel, `attendance_analytics.py` | Late, short days, repeat patterns, weekday pattern, one person's page. Views: mine, team (direct or whole line), organisation. Filters by department, branch, role, manager (slice 001) | Employee, manager, org roles | proven (function names `summary`, `_weekday_pattern`, `filter_options`, `person`; filters from slice 001 brief) |
| E6 | Slice 012 design: People, Attendance, Leave cards, "Not shared" small-group rule, scope switcher, Leader role | Designed, reviewed 2026-09-15 (`05-review.md`). Settings and data-review tests exist (`test_leader_settings_012.py`) | CXO, branch head | proven (docs). Leader screen itself: not found in code |
| E7 | Desk number cards (`hrms/hr/number_card`) | Total employees, Employee exits (this year), Separations (this month), Early exit (this month), Employees joining/relieving (this quarter), New hires (this year), On leave today, Late entry, Total absent/present (month) | Desk users | proven (folder names) |
| E8 | Desk dashboard charts | Hiring vs Attrition count (monthly), headcount by department / designation / branch / grade / type / age, gender diversity, attendance count, shift breakup | Desk users | proven (folder names; the Hiring vs Attrition JSON uses monthly intervals) |
| E9 | Desk reports | **Employee Exits** (date of joining, relieving date, exit interview, final decision, full and final statement; has a chart and a summary), Employee Analytics (age, gender; flagged "too much" for managers), Monthly Attendance Sheet, Leave Ledger, Employee Leave Balance and Summary, Shift Attendance | HR, System Manager | proven (folder names; columns read for Employee Exits) |
| E10 | Our Desk reports: Late Coming Deductions, Daily Attendance Workings, Punch Fixes This Month | Operational, not trends | HR | proven (folder names) |
| E11 | Frappe Insights | **No install found.** Surfaces searched: `apps` folders in this tree (alvoraa_portal, alvoraa_goals, hrms), `hooks.py`, product docs. Not checked inside a running site | — | not found, not fully ruled out |

**Gap table (what neither E1 nor E5 gives today)**

| Need | State |
|---|---|
| Leavers, in any window | none on E1 (proven: no leaver query in `get_hr_analytics` lines 852-890). Desk only (E7-E9) |
| Attrition rate | none on portal |
| Pick a period | none on E1 (fixed to the month). 6-month joiners fixed |
| Compare with the period before | none on E1 |
| Branch / grade / employment type / manager cuts | branch split returned by the server; department and gender shown. No grade, type, manager |
| Leave by type, peaks, balances | only "Leave utilisation %" and "Pending approvals" on E1 |

---

## 2 · The data, checked (Employee, Attendance, Leave Application)

**Employee** (ERPNext JSON, read in `alv089-bench`) — proven: `status` (Active / Inactive / Suspended / Left), `date_of_joining`, `relieving_date`, `resignation_letter_date`, `notice_number_of_days`, `reason_for_leaving` (Small Text, free text), `held_on`, `new_workplace`, `feedback`, `company`, `branch`, `department`, `designation`, `reports_to`, `gender`, `date_of_birth`. `grade` and `employment_type` are **not in the list I read**; I did not find them in that query, so I treat them as **not checked**. The 012 and slice 001 filters mention "role" and "grade" only in prose. Confirm both before naming them in a spec.

**Attendance** — proven fields in `attendance.json`: `status` (Present, Absent, On Leave, Half Day, Work From Home; **Held** is added by a property setter in `held_day.py`), `attendance_date`, `company`, `department`, `shift`, `late_entry`, `early_exit`, `working_hours`, `in_time`, `out_time`, `leave_type`, `leave_application`, `overtime_type`, `actual_overtime_duration`. **There is no branch field on Attendance.** Branch comes from the Employee row (inferred from `org_figures.condition`, which takes a `branch_field`). Held-day fields are Custom Fields (`alvoraa_release_how`, `alvoraa_release_on`, `alvoraa_missing_time`; proven in `held_day.py`).

**Leave Application** — proven: `leave_type`, `from_date`, `to_date`, `total_leave_days`, `half_day`, `status` (Open / Approved / Rejected / Cancelled), `posting_date`, `company`, `department`, `leave_balance`, `leave_approver`, `description` (the reason; **never shown to leaders**). Whether a Leave Type is "leave without pay" is a field on Leave Type: **not checked**.

**Answers to the data questions**

| Question | Answer |
|---|---|
| Can we place a leaver in "left within 1 week / 1 month / 3 months of joining"? | **Yes, when `relieving_date` is filled.** Tenure = `relieving_date` minus `date_of_joining` (inferred, both proven). A `Left` person with no relieving date is outside every window: show them as "Needs review", with a count, never drop them quietly. |
| Voluntary or involuntary? | **Not reliable.** `reason_for_leaving` is free text. Exit Interview and Employee Separation doctypes are referenced by the Employee Exits report (proven), but whether tenants fill them: not checked. Do not ship this cut without a fixed list of reasons. |
| Who counts as "left in a window"? | `relieving_date` inside the window. `status` can be Left before the relieving date arrives (notice period). Recommend: Left = relieving date passed. Say it in words on the page. |
| Headcount on a past date? | Inferred: Active now, plus those whose `relieving_date` is later than that date, minus those who joined after it. Fine for a trend only if `relieving_date` is clean. |

---

## 3 · Competitors, whole products

No trial accounts. Nothing here is **seen** in a live product. **read (14 Sep 2026)** rows are carried from slice 012's scan. Everything else is `[recall — verify]`. The PM should verify before using any of it in a pitch.

| Capability | Darwinbox | Keka | greytHR | Zoho People | BambooHR | Workday | HiBob | Rippling | Zimyo | sumHR | Label |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Headcount, joiners, leavers | yes | yes (org dashboard) | yes | yes | yes | yes | yes | yes | yes | yes | Keka, Zoho, Darwinbox: read 14 Sep; rest recall |
| Attrition % with period pick | yes | yes | yes | yes | yes (reports) | yes | yes | yes | yes | yes | recall |
| Early attrition (left within 90 days) | yes, as a retention cut | not sure | not sure | not sure | not sure | yes (new-hire turnover) | not sure | not sure | not sure | not sure | recall |
| Voluntary vs involuntary | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | recall. All depend on a fixed exit reason list |
| Tenure bands | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | recall |
| Absenteeism, leave and overtime trends | yes | yes | yes | yes | light | yes | light | light | yes | yes | recall |
| Payroll cost trend | yes | yes | yes | yes | light | yes | yes | yes | yes | yes | recall |
| Diversity and span of control | yes | partly | partly | partly | yes | yes | yes | yes | partly | partly | recall |
| Filters (location, department, grade, manager) | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | recall |
| Drill-down to people | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | recall |
| Export and scheduled email digest | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | recall |
| AI attrition risk per person | yes | yes | no | no | no | yes | yes | no | yes | no | Keka, Darwinbox: read 14 Sep; rest recall |
| Small-group hiding | not stated | not stated | not stated | not stated | not stated | in survey tools only | not stated | not stated | not stated | not stated | read 14 Sep (012) |

Plain reading: **every product shows the same core**. Joiners, leavers, attrition rate, period pick, filters, drill-down, export, email digest. We are behind on leavers and period pick. We can be ahead on privacy.

**What we will deliberately not copy**

| Not copying | Why this is better for our people |
|---|---|
| Per-person attrition risk score | It scores a named person on a guess, and their boss sees it. Refusal in the agent brief (inferring sensitive things about one person) |
| Drill-down to a named list for a leader | A leaver list with a reason names a person. Keep names with HR, and only for the HR scope |
| Gender, age and manager cuts for leaders | In a group of 6 they point at one person. Hide below the group minimum (012: 5, with subtraction rule) |
| League tables of branches or managers | Ranks a manager of 8 people. List branches by name, not by result |
| Free export from the leader screen | An export walks around every privacy rule. HR export only, logged |
| Twenty-chart dashboard | A CXO wants the answer in 30 seconds |
| Showing the reason for a leave or a departure to leaders | Reason for absence is never shown (refusal). Free-text exit reasons can name a health or family matter |

---

## 4 · The two examples, answered

### (a) Early attrition: "left within 1 week / 1 month / 3 months of joining"

**What it means:** of the people who joined in a chosen period, how many left within 7, 30 or 90 days of their joining date.

| Cut | Rule (proven fields) | Shown as |
|---|---|---|
| Left within 1 week | `relieving_date` minus `date_of_joining` is 7 days or fewer | "3 of 48 joiners" and a percentage |
| Within 1 month | 30 days or fewer | same |
| Within 3 months | 90 days or fewer | same |

Design rules:

- **Use "of N joiners", not a bare count.** 3 leavers means nothing without how many joined. Cohort = joined in the chosen window. Say so in one line under the figure.
- **A cohort that joined less than 90 days ago cannot show the 3-month figure yet.** Show "Too early to tell: the 3-month window is still open for 14 of these 48 people". Never show a number that will grow.
- **Recommendation: show the three cuts as one row of three chips with counts**, not three charts. One tap opens the HR list (names, HR scope only). Leaders see the counts, by branch and department where the group is large enough.
- **Dependence on data quality:** the count is only right when relieving dates are filled. The page shows "N leavers have no relieving date" with a link to Data to review (E4 pattern: the label must lead somewhere).

### (b) Cumulative rolling windows: last 1 week / 1 month / 3 months / 6 months / 1 year

**Recommendation: one period bar at the top, five fixed choices plus a custom range for HR only.**

| Choice | Window | Compared with |
|---|---|---|
| 1 week | last 7 days up to today | the 7 days before |
| 1 month | last 30 days | the 30 days before |
| 3 months | last 90 days | the 90 days before |
| 6 months | last 180 days | the 180 days before |
| 1 year | last 365 days | the 365 days before |

- "Cumulative" is read here as **rolling: everything from the start of the window up to today**, so 3 months includes the last month. This is an **assumption**; see question Q1.
- Every figure on the page changes with the bar. Same words everywhere: "Joined", "Left", "Net change", "Attrition %" (leavers in window divided by average headcount in window, annualised only when she asks).
- Each figure carries its change line against the earlier window, using equal-length windows (012 pattern: never compare a part period with a whole one).
- A small line chart of cumulative joiners and leavers inside the window, with the net line between them. One chart, not five.
- A window shorter than the data the tenant has ("1 year" for a company live for 3 months) says "Your records start on 1 Sep 2026", not zero.

**Filters, and who sees which**

| Filter | HR (own companies) | CXO / leader | Small-group rule |
|---|---|---|---|
| Company | yes (own only) | yes, with an "All companies" total plus a table | totals exempt |
| Branch | yes | yes | hide cut below N and the next-smallest |
| Department | yes | yes | same |
| Designation | yes | yes, top bands only | same |
| Employment type | yes **if the field exists** (not checked) | yes | same |
| Grade | yes **if the field exists** (not checked) | optional | same |
| Gender | HR only | **no** (points at people in small groups) | same |
| Manager | HR only | **no** | same |

Filters combine, and the page says what is applied: "Showing: PPJ Noida, Sales, last 3 months". A filter that leaves fewer than N people shows "Not shared: too few people in this group for a fair picture" (the wording Surbhi approved for slice 012).

---

## 5 · Attendance trends (added scope)

**Fields, proven:** `status`, `attendance_date`, `late_entry`, `early_exit`, `working_hours`, `shift`, `department`, `company`; Held days through `status = Held`. Branch via Employee (inferred).

| Measure | How it is read | Note |
|---|---|---|
| Present, absent, half day, on leave, work from home | count of Attendance rows by `status` per window | exists today as one figure (E1 "Attendance rate" and "Org Health") |
| Absenteeism rate | Absent days divided by days a person was expected | **Expected days must exclude weekly offs and holidays.** The shared `rate()` in `org_figures.py` already defines this; reuse, do not invent a second formula (012 step 0) |
| Late and short days | `late_entry`, working hours below shift | exist in E5 for individuals, not as org trends |
| Missing-punch / held days | `status = Held` | switch is per company (`alvoraa_hold_odd_punch_days`). Show "Held days: 12, waiting on a punch". Show only where the switch is on |
| By branch, department | group the rows through Employee | hide small groups |
| Doubtful days | `open_doubtful_counts` | keep the "Data up to" line and the "Needs review" label |

Design:

- One trend: **absenteeism % across the chosen window**, weekly dots for 1 to 3 months, monthly for 6 months and 1 year.
- One exception strip, like the manager Home pattern: "2 of 11 branches are below the company rate", branch names only, no person.
- **Leaders see rates and counts. Never a person's name, never the reason for an absence.** Names stay in Attendance Insights (E5), which already has scope rules.
- The shared "Data up to" line stays.

## 6 · Leave trends (added scope)

**Fields, proven:** `leave_type`, `from_date`, `to_date`, `total_leave_days`, `half_day`, `status`, `posting_date`, `company`, `department`, `leave_balance`. Leave without pay as a type flag: not checked.

| Measure | How it is read | Note |
|---|---|---|
| Leave taken by type | sum of `total_leave_days` where `status = Approved`, by `leave_type` | days, not people, to avoid naming anyone |
| Leave without pay (LWP) | the LWP leave types | needs the Leave Type flag; not checked |
| Peaks by month | group `from_date` by month | chart of 12 bars |
| Peaks by day of week | group start dates by weekday | a Monday or Friday spike is the useful finding; the shape is a pattern, not a person |
| Pending approvals, and how old | `status = Open`, age from `posting_date` | exists as a count today (E1). Add "oldest waiting 9 days". Opens the approver's inbox for HR; a leader sees only the count |
| Balances | `leave_balance` per application; Leave Ledger and Leave Balance Summary are Desk reports (E9) | show **average balance by type** and "carried liability" only if payroll wants it. Never an individual's balance to a leader |

**Fix first:** E1 "Leave utilisation" divided this year's leave by every allocation ever made (012 brief §2, LV2). Slice 012 reports a shared fix (`leave_year`, `leave_figures`, proven in `org_figures.py`). Do not build new leave figures on the old formula.

**Privacy:** no `description` anywhere in leader screens. No leave type that identifies a condition (maternity, medical) in a group below N. Hide the type, not the total.

---

## 7 · Ideas by persona

| Persona | Idea | Job it serves | Evidence | Size |
|---|---|---|---|---|
| **CXO / leader** (phone, 5 minutes) | **Opens on one answer:** "Headcount 330, down 4 in 3 months. 6 left in 3 months, 2 of them within 30 days of joining." One tap to the branches behind it | Trust one number, know if something is wrong | E6 (012 design); competitors all open on headcount and attrition | M |
| CXO | Period bar of five choices at the top, remembered per person | Her own request | Section 4(b) | S |
| CXO | **"What needs me" strip**: branches under the company rate; early leavers above the usual level; oldest pending leave | Exceptions before lists | Principle 5; manager Home pattern in `ux-learnings.md` | M |
| CXO with several companies | "All companies" total plus a comparison table (no ranking) | Group view | 012 scope-switcher pattern, applied | S, reuse |
| CXO | Weekly email digest of the same five figures, HR-approved wording | Check on a Monday without opening the app | all competitors (recall); 012 left it out | M, **needs its own decision** (Q4) |
| **HR Manager** (laptop, month-end) | Same page with named lists: leavers in window, early leavers with relieving date and tenure in days | Act on it: call, exit interview, fix records | Desk Employee Exits report (E9) | M |
| HR Manager | "Leavers with no relieving date" and "Left with no reason" counts that link to a fix list | Clean data makes the window numbers believable | E4 pattern | S |
| HR Manager | Filter set, plus gender and manager cuts | Diversity and hiring-quality checks | competitors; 001 filters | M |
| HR Manager | Export to CSV of the HR table, every export logged | Month-end packs | competitors; joiner audit decision (every export logged) | S, **Tier 1 review** |
| **Line manager** | Nothing new here. Team attendance stays in Attendance Insights (E5) | One-way rule: not more surveillance | — | none |
| **Employee** | **Nothing.** Employees never see org analytics. One line on their profile or privacy page: "Leaders see totals only, never your name" (012 idea) | Trust | 012 | S |
| **Frontline / phone at 360 px** | Applies to the leader on a phone: period chips scroll sideways, one card per area stacked, the chart below the number, no table wider than the screen. HR tables switch to a card list | Leader on the floor | P4 measuring rule | M |

---

## 8 · Findings on today's HR Analytics page (E1)

| ID | Impact | Kind | Size | Severity | Finding |
|---|---|---|---|---|---|
| H1 | High | New | M | P2 | No leavers, no attrition, no early attrition (proven: no leaver query in `get_hr_analytics`) |
| H2 | High | New | S | P2 | No period choice, no comparison with the earlier period |
| H3 | Medium | Improve | S | P3 | Six cards link out to Desk lists (`window.open('/app/employee…')`). A person on a phone is thrown onto a screen not built for it. Link inside the portal |
| H4 | Medium | Fix | S | P3 | Leave utilisation card: 012 fixed the formula in `leave_figures`. Confirm the card now reads it (not checked in the page script) |
| H5 | Medium | Improve | M | P3 | Gender ratio on the HR page is fine for HR; do not copy it to leaders |
| H6 | Low | Improve | S | P4 | Emoji icons on the joiner cards (`🆕`) against labelled-icon rule |
| K1 | — | Keep | — | — | Scope by company and branch; fails closed with a "not linked" page |
| K2 | — | Keep | — | — | "Data up to" line and "Needs review" for doubtful figures |
| K3 | — | Keep | — | — | One shared calculation (`org_figures.py`) |

---

## 9 · What I recommend the PM weighs (the ladder)

| Rung | Verdict |
|---|---|
| Already there | E1, E3, E4 give scope, shared formulas, doubtful-data label. Desk charts E7-E9 give a Hiring vs Attrition chart and an Employee Exits report. **Cheapest start: point HR at those today** |
| Configuration | A Desk Number Card or Dashboard Chart per window is configuration only. It does not meet the leader's phone need and has no small-group rule |
| Customisation / new code | Extend `get_hr_analytics` and the E1 page with a period bar, a Leavers card and the early-attrition row. This is the smallest build that answers both examples |
| New page | Only for the leader view of slice 012, which was approved as its own slice. Do not build a second one for HR |
| New app (Insights, BI tool) | No. Heavy, no small-group rule, a second login |

## 10 · Not in this slice (for the PM and Surbhi to decide)

Voluntary vs involuntary cut. Scheduled email digest. Payroll cost, overtime and diversity trends. Tenure bands. Span of control. Custom date range for leaders. Forecast or "risk" of leaving (refused). Hindi labels for the new words.

## 11 · Subtract pass

Removed from my own first list: a heatmap of absence by weekday and branch (E5 already has a weekday pattern); a leaver "reasons" word cloud (free text, privacy risk); a department head view (needs the reporting-line scope decision from 012); alerts and thresholds the user can set. I kept the competitor grid as one table rather than ten, and kept 5 windows only.

## 12 · Open questions

| # | Question | Why it changes the design | My default |
|---|---|---|---|
| Q1 | "Cumulative" means rolling (last 1 week to last 1 year) or running totals inside a year? | Changes every chart | Rolling windows, plus a cumulative line inside the window |
| Q2 | Is the group minimum still 5, and does it apply to HR too? | HR sees names today in scope | 5 for leaders. HR sees names inside their own scope |
| Q3 | Who is in scope for the leader view: Leadership role, System Manager, or both? Slice 012's role is designed but not found in code | A CXO who is also a System Manager | Leadership role, per 012 |
| Q4 | Weekly email digest: in or out? | A mail goes outside the app; counsel and unmuted email rules apply | Out, until the page is liked |
| Q5 | Do `grade` and `employment_type` exist on Employee in this tenant version? | Two filters you named | Check in a running site before the spec |
| Q6 | Do DTC and the other tenants keep `relieving_date` clean? | Early attrition depends on it | Measure leavers with no relieving date on two tenants first |

## 13 · Persona check

- **CXO:** gets the headline, windows, exceptions. No names. Scope across companies.
- **HR Manager:** gets the same numbers plus named lists in own scope, and a fix list for bad data.
- **Employee:** sees nothing new. Their data appears only inside totals at or above the group minimum.

## 14 · Evidence location

No screenshots taken (a code-only scan, local instance not opened). Nothing stored under `/Users/mac/hrlocal-data/`.

## 15 · Learning loop

I did not add entries to `.claude/context/ux-learnings.md` (no feedback yet). Patterns from slice 012 (small-group wording, "Needs review", equal-length comparison, scope switcher) are reused, not changed.
