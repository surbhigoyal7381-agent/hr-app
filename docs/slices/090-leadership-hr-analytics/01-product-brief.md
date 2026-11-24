---
slice: 090-leadership-hr-analytics
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-11-23
status: draft, for Surbhi to approve, change or drop
tier: 1 (who sees which scope, small-group hiding, aggregates over people)
---

# 090 · People trends for leaders and HR: product brief

**Bad news first**

1. **The leader screen from slice 012 was never built.** Push 1 of 012 is in the code (the shared calculations in `org_figures.py` and the privacy setting `Alvoraa Leader View Settings`). The leader screen, and a "Leadership" role, are not. I found the word "Leadership" only as a name in a never-list in `attendance_analytics.py` line 81. So this slice builds the leader's way in as well. It is small, but it is real.
2. **Early attrition is only as good as the relieving date.** A person marked Left with no relieving date cannot be placed in any window. The page must count them and say so.
3. **I could not run git or open a container.** I had file reading only. So I did not run `git rev-list --left-right --count dev...origin/dev`, and I did not open `alv358-bench`. I read the worktree `090-leadership-hr-analytics` (HEAD `412d5361`, cut from origin/dev). Employee fields were checked from code that uses them, not from the Employee JSON (not found in the worktree). A "not found" below means "not found in this worktree".

Labels: **Confirmed** (I read it this session), **Assumption**, **Recommendation**, **Open question**.

---

## 1 · Job to be done

**In Surbhi's words (23 Nov 2026):** "As the best UX expert, having organisation leadership role in focus, create the HR analytics more elaborate... Make sure the data has filters and cumulative pictures. e.g. employees left within 3 months, one month, one week... for the periods: 1 year, 6 months, 3 months, 1 month, 1 week... also include attendance and leave trends."

**One sentence:** *As a company head, when I open the app on Monday on my phone, I want to see in one minute how many people joined and left over the last week, month, quarter, half year and year, and whether attendance and leave are getting better or worse, so that I know whether something is going wrong before anyone tells me.*

**Persona served first: CXO** (sees all companies in their scope). **HR Manager** gets the same page for their companies and fixes the data behind it. **Employee** sees nothing org-wide and loses nothing. Their data appears only inside totals that meet the group minimum. A line on the privacy page says so ("Leaders see totals only, never your name"); that line is later, not now.

## 2 · Current pain (story, no data)

Confirmed in code: today's HR Analytics page (`panel-analytics`, `get_hr_analytics` in `hr_api.py`) has six cards and no leavers, no attrition rate, no period choice and no comparison. Joiners are fixed to the month. To learn "who left in the last 3 months" an owner has to ask HR, who opens a Desk report (Employee Exits). Story: an owner hears on the floor that three new drivers quit in their first week. He cannot check it himself, and nobody can tell him if that is usual. **Baseline numbers: none, I have no usage data.** Evidence required: count of "how many left?" questions HR gets a month, at DTC or Grace.

## 3 · Competitors, whole products

No trial accounts. Nothing here is **seen**. The first three rows were **read on 14 Sep 2026** (carried from slice 012). All else is `[recall — verify]`, so do not use it in a pitch until checked.

| Capability | Frappe HR standard | Keka / Darwinbox / Zoho People | Others (greytHR, Workday, HiBob, BambooHR, Zimyo) | What we do in v1 |
|---|---|---|---|---|
| Headcount, joiners, leavers | Desk number cards and an Employee Exits report (**Confirmed**, folder names). Not on the portal | yes (read 14 Sep) | yes (recall) | Yes, on the portal |
| Attrition % with a period choice | Hiring vs Attrition chart, monthly only (Confirmed) | yes (recall) | yes (recall) | Yes: five fixed windows, against the window before |
| Early attrition (left within 90 days) | no | Darwinbox: yes (recall) | Workday: yes (recall) | Yes: 1 week, 1 month, 3 months |
| Attendance and leave trends | monthly sheets, ledger reports (Desk) | yes (recall) | yes, some light (recall) | One trend each |
| Filters, drill-down to people, export, scheduled email | Desk filters, lists | yes (recall) | yes (recall) | Filters only |
| Per-person attrition risk score | no | Keka, Darwinbox: yes (read 14 Sep) | Workday, HiBob: yes (recall) | **No. Refused.** |
| Small-group hiding | no | not stated | not stated | **Yes** |

**Plain reading:** everyone has the same core. We are behind on it. We can be ahead on privacy, and nobody I read claims that.

**What we will deliberately NOT copy, and why that is better for our user**

| Not copying | Why |
|---|---|
| Attrition-risk score per person | Scores a named person on a guess; their boss sees it. A refusal we do not negotiate |
| Named leaver lists on the leader page | A name plus a date plus a department is one person. Names stay in the Desk Employee Exits report, which HR already has |
| Gender, age, manager cuts | In a group of 6 they point at one person |
| Rankings of branches or managers | Ranks a manager of 8 people. We list branches, we do not rank them |
| Export and scheduled email digest | An export walks around every privacy rule |
| A twenty-chart dashboard | An owner wants the answer in 30 seconds |
| Reasons for leaving or for leave | Free text can name a health or family matter |

## 4 · Three ways to solve it

| | What | Verdict |
|---|---|---|
| **Conventional** | Copy the competitor dashboard: 20 charts, filters on gender, age, manager, named drill-down, export, email digest | Rejected. It is the feature-parity race our context §6 item 10 refuses, and it breaks the privacy rules |
| **Better** | One page: a headline sentence, five period chips, one trend each for people, attendance and leave, filters, small groups hidden | **Proposed** |
| **Reimagined** | A weekly written summary a founder reads on WhatsApp, written by an AI | Rejected for now. A rule-built sentence does the job. An AI would add cost, a wrong-number risk and an outbound email decision (Q4) |
| **Build nothing** | Point HR at the Desk Employee Exits report and the Hiring vs Attrition chart | Does not meet the leader's phone need and has no small-group rule. It is a stop-gap HR can use today |

**Rung on the cost ladder:** new code in the existing `alvoraa_portal` app (one page, one server call), plus configuration (the Leadership role and User Permissions). Cheaper rungs rejected: Desk cards cannot hide small groups. Frappe Insights is a new app with a second permission model (OPS-1, accepted).

## 5 · Kano class and demand

| Feature | Class (**proxy**, no survey) | Why | Evidence that would change it |
|---|---|---|---|
| Leavers, attrition %, period choice | **Must-be** | Every competitor row above has it (recall); we are behind | A survey where owners "can live without" it |
| Early attrition (1 week, 1 month, 3 months) | **Performance** | Buyers compare on it; one competitor has it by name (recall) | Same survey |
| Attendance and leave trends | **Performance** | Competitors have them; Desk already has monthly sheets | Same |
| Small-group hiding on leader figures | **Attractive** | No HR suite I read states it. Fits our security-conscious buyer | Competitor announces it |
| Per-person risk scores, named lists to leaders | **Reverse** | Trades employee privacy for a manager's convenience | — |

**Demand evidence:** **seen:** one request, the founder's, 23 Nov 2026. **Not seen:** no customer, demo or lost-deal note that I could find. This is thin. It is a Kano proxy, not a finding.

**Survey kit (5+ owners or HR heads):** *"If Alvora showed leavers and early leavers for the last week, month and quarter on your phone, how would you feel?"* / *"If it did not?"* Then the same pair for "small groups are hidden to protect people". Answers: Like, Expect it, Neutral, Can live with it, Dislike. Classify with the standard table. Report CS+ and CS−.

## 6 · Thin slice

**The outcome:** one person (the CXO) gets one complete answer on a phone: people in, people out, attendance, leave, for the window they pick. HR sees the same page and the "fix the data" counts.

### In this slice (needed to ship)

| # | What | Notes |
|---|---|---|
| 1 | **A portal page "People trends"**, one server call, numbers only | Reads Employee, Attendance, Leave Application. **No Employee Checkin, no Salary Slip, no pay** (OPS-2, OPS-6). Charts use what the portal already ships |
| 2 | **Period bar, five chips:** 1 week (7 days), 1 month (30), 3 months (90), 6 months (180), 1 year (365). Rolling, ending today. Remembered per person | Every figure shows the change against the equal-length window before. Buckets: week for 1 week to 3 months, month for 6 months and 1 year (OPS-8) |
| 3 | **People:** Headcount, Joined, Left, Net change, Attrition % (leavers divided by average headcount in the window) | "Left" = status Left and relieving date on or before today, inside the window. A person in their notice period is not yet Left. Said in words on the page |
| 4 | **Early leavers row:** left within 1 week, 1 month, 3 months of joining, as "3 of 48 joiners". Cohort = people who joined in the window | A cohort still inside its window says "Too early to tell: 14 of these 48 are still inside 3 months". Never a number that will grow |
| 5 | **One chart:** joined and left per bucket, with a running net-change line | This is the "cumulative picture". One chart, not five |
| 6 | **Attendance:** one absenteeism-% trend over the window, using the shared `rate()` from `org_figures.py` (weekly offs and holidays excluded). Keeps "Data up to" and "Needs review" | No second formula |
| 7 | **Leave:** days taken, by leave type, and one trend by bucket. Pending approvals as a count only | A leave across a window edge counts only the days inside the window (OPS-10). Leave types merge into "Other" when the group is under the minimum (OPS-9) |
| 8 | **Filters:** Company, Branch, Department, Employment type. The page says what is applied: "Showing: DTC Delhi, last 3 months" | All four are on Employee (see §9). A filter the user may not use is refused, not ignored (OPS-3) |
| 9 | **Small-group rule:** any cut under the minimum shows "Not shared: too few people in this group for a fair picture" | The setting already exists (`min_group_size()`, default 5, range 3 to 10, System Manager only). Same rule for HR and leader on this page |
| 10 | **Data-quality line (HR):** "N leavers have no relieving date" with a link to the Desk Employee list filtered to them | The link must lead somewhere. Shown to leaders as a count only |
| 11 | **Leader access:** a "Leadership" role plus a Company or Branch User Permission; none = sees nothing. HR roles also open the page | Per the 012 design. Not the "Alvoraa CXO" role (policy library collision, noted in 012) |

### Out of scope, with the pile each cut landed in

| Cut | Pile | Why |
|---|---|---|
| Named lists of leavers on this page | Later | Desk Employee Exits already gives HR names. Adds a Tier 1 read-log |
| Voluntary vs involuntary | Not doing until a fixed reason list exists | Reason is free text, so the number would be a guess |
| Grade filter | Later | Field exists (§9). Four filters are enough to validate |
| Gender, age, manager cuts | Not doing for leaders | Point at people. HR-only later, if asked |
| Custom date range, tenure bands, span of control | Later | Five windows meet the ask |
| Weekly email digest | Needs its own decision (Q4) | Mail leaves the app |
| Export | Later, Tier 1 review | Needs scope, minimum and an audit row |
| Pay, cost, overtime, diversity trends | Not in v1 (OPS-6) | Pay by small group is disclosure |
| Held-day trend, leave by weekday, balances, oldest pending leave | Later | Not needed to validate. Held days are count-only when added (OPS-9) |
| "What needs me" exception strip | Later | The headline sentence covers it first |
| Hindi labels | Later | `[ASSUMPTION]` leader page is English first; Hindi parity binds employee screens |
| Fix of the old "Leave utilisation" card | Separate | New leave figures do not use it |

## 7 · Persona enhancements through the portal

| Persona | How the portal helps | Job | In this slice? | Why |
|---|---|---|---|---|
| **CXO** | Headline sentence, period chips, trends, filters | Know if something is wrong | **Yes** | The ask |
| CXO with several companies | "All companies" total plus a table, no ranking | Group view | **Yes** (company filter and total) | Scope already supports many companies |
| CXO | Weekly digest on Monday | Check without opening the app | No | Q4 |
| **HR Manager** | Same page, plus "no relieving date" counts and links | Make the numbers believable | **Yes** | Data quality decides trust |
| HR Manager | Named leaver lists, gender and manager cuts, CSV export | Month-end packs | No (Desk covers names) | Tier 1 each |
| **Line manager** | Nothing new. Team attendance stays in Attendance Insights | No new surveillance | No | One-way rule |
| **Employee** | Nothing org-wide | Trust | No | A privacy-page line comes later |
| **Frontline employee (360 px phone)** | Sees nothing here. The leader's page still must work at 360 px | Leader on the floor | **Yes**, as a build rule | Chips scroll sideways, cards stacked, no wide tables |

## 8 · The WOW moment

The owner opens **People trends** on his phone. The first thing, above any chart:

> **Headcount 330, down 4 in 3 months.** 6 left in 3 months. 2 of them within 30 days of joining.
> Attendance 91.2%, up 0.8 on the 3 months before. 41 leave days taken, Casual leave the most.

He taps **1 month**. Every number and the chart change at once, each with its change against the month before. Under "Early leavers" a small group reads **Not shared: too few people in this group for a fair picture**. He sees at once that the page protects people.

## 9 · Answers to the open data questions (checked)

| Question | Answer |
|---|---|
| Do `grade` and `employment_type` exist on Employee? | **Yes, both. Confirmed from code, not from the JSON.** `grade` is read as an Employee field in `hr_api.py` line 3852 (`EMP_RULE_FIELDS`), is on the field-rights list (`employee_field_rights.py` line 54) and is set in `tests/leave_063_fixtures.py` line 106. `employment_type` is read on Employee in `alv291_attendance_fix.py` and `salary_components_and_workings.py`. The payroll rule set note says it is "a standard ERPNext field that was sitting unused" at DTC, so **a filter on it may be mostly empty on some tenants**. Not checked on a live site |
| Does Attendance have a branch? | **Yes: `alvoraa_branch`.** 01a said it did not; DevOps' index list and `org_figures.py` line 118 both use it. The correction belongs in 01a |
| Group minimum? | A setting exists: default 5, allowed 3 to 10, only a System Manager changes it, a bad stored value reads as 10. **Confirmed** (`alvoraa_leader_view_settings.py`) |
| Is `relieving_date` clean? | **I do not know.** Not checked on any tenant. A measuring step comes before the spec (Q6) |

## 10 · Run-side reality (DevOps §1)

Own page, no Insights. Reads Employee and Attendance (indexed on company and date) and Leave Application (indexed). **No timing at DTC scale exists.** Estimate only: about 110,000 Attendance rows for 6 months and 220,000 for a year. The slice does not grow in size because of this, but the measure-first rule (OPS-5) stands: time it on a dev copy, add a time-based cache keyed by user scope and today's date only if a query misses 3 seconds. Numbers are sent as a few KB of JSON. No new job, no new table, no new app, no new index.

## 11 · Thriving-workplace lens

| Lens | Answer |
|---|---|
| Engagement | Slight: an owner who sees early leaving can act on onboarding. No effect on employees directly |
| Collaboration | HR and the owner read one set of numbers instead of two reports |
| Inclusiveness | Contract and agency staff count only if the tenant fills Employee records for them (DTC has 44 agency staff). The phone layout serves a leader on the floor. English only in v1 |
| Transparency | Makes leaving and absence visible to leadership, as totals. The least powerful person is protected by the group minimum, no names, no reasons |

## 12 · Regulatory read (not a lawyer)

1. **Regime:** DPDP (personal data in aggregate), employment law on retention of leaver records. No AI, so no AI Act duty. ⚠ COMPLIANCE for the minimum-group wording at leaver cells.
2. **Whose obligation:** the employer's. We help them show leadership totals without exposing people.
3. **New in this slice:** new visibility (leader totals), a new role. No new data collected, no automated decision.
4. **Honest downside:** "1 left from Security" in a team of 6 is a name to the people in that team. The minimum and the merge-into-Other rule are the defence. Counsel and the security engineer must set the exact rule for leaver and leave-type cells. I propose a default in Q2.

## 13 · Success measures

| # | Measure | Type | Baseline | Target | How measured |
|---|---|---|---|---|---|
| S1 | Leaders who open People trends at least once a week, of those given the Leadership role | Adoption (leading) | not measured | 3 of 5 leaders at day 30 [ASSUMPTION: 5 leaders exist across tenants] | A count of distinct users per week from the server call log (`log_if_slow` pattern), not page views |
| S2 | Times HR is asked "how many left in X?" | Efficiency (lagging) | unknown, measure first | Down by half at day 60, asked of the 2 HR contacts | A two-question check-in with DTC and Grace HR |
| S3 | Leavers with no relieving date, per tenant | Quality (lagging) | unknown, measure first | Under 5% of leavers in the last year, or falling | The count the page already shows |
| S4 | Page answers within the report budget | Quality (leading) | no timing | 3 s on the DTC-size copy | Timed on a dev copy before release |

No vanity metrics. Logins and page views are not used.

## 14 · Risks, red-teamed

| Risk | What happens | Cheapest check |
|---|---|---|
| Scope leak through totals (P1) | An HR Manager asks for another company's id and sees its totals | Test it as OPS-3 says. Scope lives inside the query |
| Small cells name a person | "1 left within a week, Security, Ambala" is one person | Hide below the minimum; merge into Other; test the subtraction case |
| Blank relieving dates | Numbers too low, owner is misled | Show the "no relieving date" count; measure on two tenants first |
| Rejoin or back-dated date | Figures move | "As of" time on the page; time-based cache only |
| Leader with a manager role also | Sees more than intended | Leadership role alone gives only this page |
| 10x data | Slower | Buckets, indexed ranges, measure first |
| Misread of "cumulative" | We build the wrong chart | Q1 default confirmed by Surbhi before design |
| Two numbers for one thing | Page and old HR Analytics disagree | Both read `org_figures.py`. The old page stays untouched |
| Support tickets | "Why is this 'Not shared'?" | One plain line on the page explains it |

## 15 · Subtract pass

Removed from my own first draft: the named leaver list, a "what needs me" strip, a grade filter, a held-day trend, leave by weekday, balances and a separate leave-without-pay line (its flag was not checked), a second Insights comparison, and a privacy-page line. I kept five windows and one chart per area. Honest note: this is still four areas on one page. If the engineer finds it too big, the cut order is leave, then attendance, then filters; people comes first because it is the founder's example.

## Open questions

| # | Question | Owner | Blocks | Recommended default |
|---|---|---|---|---|
| Q1 | "Cumulative" = rolling windows ending today, plus a running net line inside the window? | Surbhi | Chart design | Yes |
| Q2 | Group minimum 5, the same for HR and leaders on this page? Leaver and leave-type cells under the minimum shown as "fewer than 5" below the whole-scope total, and merged into Other | Surbhi, counsel, security engineer | Spec, ⚠ COMPLIANCE | Yes, use the existing setting |
| Q3 | Leader = new "Leadership" role plus Company or Branch User Permission, per 012? | Surbhi | Access design | Yes |
| Q4 | Weekly digest in or out? | Surbhi | Nothing in v1 | Out |
| Q5 | How does payroll count a leave across a window edge: Leave Application days overlapping the window, or Attendance "On Leave" rows? They may differ | Engineer, with a sample from DTC | Leave figure, OPS-10 | Compare both on a DTC sample. Use whichever payroll reads; day split, never by start date |
| Q6 | Share of Left staff without a relieving date at DTC and Grace | Engineer (read-only count, needs her word for production) | Whether early attrition is believable | Measure before the spec |
| Q7 | Does a Leadership role already exist on any tenant, and who would get it first? | Surbhi | Rollout | Create it in this slice; Surbhi names the first leaders |

## Assumptions

- `[ASSUMPTION]` Five windows are fixed days, not calendar months.
- `[ASSUMPTION]` The leader page is English in v1.
- `[ASSUMPTION]` "Left" means relieving date passed and status Left.
- `[ASSUMPTION]` About 5 leaders exist across tenants (for S1). I have no count.
- `[ASSUMPTION]` Demand is one request (the founder's). No customer evidence.
- `[ASSUMPTION]` The Employee JSON confirms grade and employment_type. Code use is proof they exist, not of their data quality.

## Kill criteria

Stop and rethink if any of these happens:

1. Leaver rows without a relieving date are over 25% on both reference tenants, so early attrition cannot be believed.
2. The query misses 3 s on the DTC-size copy and a time-based cache does not fix it.
3. Security finds that the minimum rule cannot stop a small cell being worked out from two figures, without hiding the headline.
4. Surbhi's five leaders, after 30 days, do not open it. Then it is a Desk-report problem, not a page.

---

## Gate decision

**Brief approved — Surbhi, 23 Nov 2026:** "go with your recommendations, build it". The recommended defaults for the open questions are accepted. The production read of relieving-date quality (Q6) still needs its own word before it runs, and the small-group rule (Q2) goes to the security engineer and counsel.
