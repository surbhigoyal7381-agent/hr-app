---
slice: 012-leadership-view
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-09-14
status: draft
inputs: [01a-ux-opportunities.md, 07-devops-inputs.md §1, product-context.md, handoff-contract.md, definition-of-ready-done.md, access-review/permission-templates.md, 009-ess-portal-redesign/00-assessment-and-plan.md, 010-portal-security-fixes/00c-review-copies-decisions.md, 010 01c and 00-impact-analysis (CXO and set_org_setting rows), user decisions of 2026-09-15]
---

# 012 · Leadership view — product brief

**I recommend. You decide.** Build, change or drop.

## Gate summary (what you are approving)

1. **Bad news first: today's numbers are wrong, and one of today's endpoints leaks across branches.** Fix those inside this slice, first, before any leader screen.
2. **This slice:** a totals-only view of **People, Attendance and Leave** for a company head or a branch head, phone first.
3. **Not in this slice:** Performance, Pay, Compliance, opening individual people, exports, the Monday email, the department head who spans branches.
4. **How a leader is set up:** a new "Leadership" role, plus a User Permission on their Company or Branch. No permission means they see nothing, not everything.
5. **Privacy:** groups under 5 people are hidden, and so is the next-smallest group, so nobody can be found by subtraction. Headcount and joiners are exempt. No leave reasons. No exports.
6. **One formula:** HR Analytics and the leadership view read the same attendance and leave calculation.
7. **Only System Manager may change the group-size setting.** Every change is recorded.
8. **Unsafe shortcut refused:** adding a leader to the organisation attendance roles would show sick leave by name.
9. **WOW:** the branch head's phone opens on "Attendance 96.1%, up 0.3 · company 96.8% · data up to 9 Sep", with a plain warning when the data looks broken.
10. **Kano class is a proxy** (no survey, no customer quotes). Totals for leaders = Performance class. Privacy-protected leader scope = Attractive.
11. **Flag:** a rating distribution may conflict with slice 010 decision R14. It is not in this slice, but you need to rule on it before the Performance slice.
12. **Five questions block the design step.** Each has a recommended default (§13).
13. **Kill criteria:** stop if real leaders cannot name one action they would take, or if a Branch permission breaks screens they use today.

---

## 1 · Job to be done

**Company head (CXO persona):** *"When I have five minutes on my phone before a review meeting, I want to see how my people side is doing and the one thing that needs me, without reading anyone's payslip or leave reason."*

**Branch head (store in-charge, plant head):** *"When I am on the floor on a Monday, I want to know if my branch is turning up and how we compare with the company, so I can fix the rota before it costs a sale."*

| Persona | What changes |
|---|---|
| **CXO / company head** | Gets a view built for them. No longer needs HR Manager to see the business |
| **HR Manager** | Numbers that match the leader's. Sets group size only if also System Manager. Keeps all name lists |
| **Employee** | Counted, never named. Sees a line saying who can see what about them |

## 2 · Current pain — a story, and the few numbers we have

All measured on the reference tenant copy `ppj.localhost` on 14 Sep 2026 (01a §2, 07 §1). One tenant only, used for measurement, not for design choices.

- **The owner reads every salary to see headcount.** He holds HR Manager because nothing else shows the business (access review). Store in-charges read their 71-person store through "My team, everyone below". That works only because the store tree matches the branch.
- **The headline numbers are wrong.** September attendance shows **65.8%**. Three days show all 330 records "Absent", which looks like a marking run with no check-ins. "Leave utilisation 0.1%" divides this year's leave by every allocation ever made (LV1, LV2).
- **Two attendance formulas disagree** (LV3). An owner and HR can look at "attendance" and see different numbers.
- **`get_hr_analytics()` ignores branch and company** (LV4, OPS-1). A store HR person sees every store's numbers and other stores' names.

I have no customer quotes and no support tickets about this. The demand is one tenant's workaround and your own request.

## 3 · Competitive analysis — whole products

Labels: **read (14 Sep 2026)** comes from the UX designer's search of help and product pages. `[recall — verify]` comes from memory. Nothing here is **seen** in a live product.

| Capability | Frappe HR standard | Zoho People | Keka | CatalystOne | Darwinbox | Label | What we do in 012 |
|---|---|---|---|---|---|---|---|
| Org totals (headcount, joiners, exits) | Desk number cards and "Employee Analytics" / "Employee Exits" reports (in repo code) | Organisation-level reports | Org Dashboard: headcount, growth and retention, attrition | People analytics reports `[recall — verify]` | Persona dashboards | FHR: checked in `hrms/hr/number_card`; others: read | Yes: People card, with honest "no leavers recorded" |
| Scope to a location or unit | User Permission, only on doctypes with a branch field | Reports shared by role or location; rows follow permissions | Filter by location, for admins | Role-based access to org units `[recall — verify]` | Persona dashboards, drill-down | read | Yes: server-side company or branch scope |
| Small-group protection in HR analytics | None | Not stated | Not stated | Not stated `[recall — verify]` | Not stated | read | **Yes: minimum 5 plus subtraction blocking.** Borrowed from survey tools (Culture Amp, Lattice, Workday Peakon, read) |
| Phone view for a unit head | No | `[recall — verify]` | `[recall — verify]` | `[recall — verify]` | `[recall — verify]` | — | Yes, phone first |
| AI attrition risk per person | No | `[recall — verify]` | Yes | `[recall — verify]` | Yes | read | **No** |
| Plan tier | Free | `[recall — verify]` | `[recall — verify]` | `[recall — verify]` | Enterprise suite | — | Our `analytics` feature sits in Enterprise today (`subscription.py`). Question P6 |

**What we will deliberately not do, and why it makes us better:**

- **No per-person attrition "risk score".** It scores a named person on a guess, and their boss sees it.
- **No league table of stores or managers.** Branches appear in a table sorted by name. A 5–15 person team ranked by result is a ranking of one manager.
- **No gender, age or manager filters for leaders.** In small groups they point at people.
- **No CSV export from the leader view.** An export walks around every privacy rule.
- **No 20-chart analytics page.** One number per area, a trend, and the exception.

That is the pitch to a security reviewer: *a leader sees the business, not the people.*

## 4 · Kano class and demand

**There is no priorities review in `docs/product/priorities/` yet.** So I classify now, from proxies. Every class below is **proxy**.

| Feature | Class (proxy) | Why | What would change it |
|---|---|---|---|
| Org totals for a leader | **Performance** — close to Must-be | Keka, Darwinbox and Zoho all ship it (read). I have no lost deals or tickets on record, so the Must-be test is not met | Two lost-deal or demo notes asking for it → Must-be |
| Privacy-protected leader scope (group minimum, no reasons, no pay by default) | **Attractive** | No HR suite I read claims it. It fits our security-conscious buyer | Competitors announcing it → Performance |
| Leaders opening individuals | **Reverse** for employees, Attractive for some owners | Trades employee privacy for leader convenience | Survey both sides. Stays a setting, off by default |
| AI attrition risk | **Reverse** | Surveillance-flavoured | — |

Survey kit (for 5+ owners and 5+ store heads): *"If Alvoraa showed your branch's attendance and leave totals on your phone, how would you feel?"* / *"…did not?"* Also ask the same pair about "small groups hidden to protect privacy", and about "opening individual people". Classify with the standard Kano table. Report CS+ and CS−.

## 5 · The thin slice

**One named outcome:** *a branch head (and a company head, with the same screen at a wider scope) opens a trustworthy totals-only view of People, Attendance and Leave for exactly their scope, on a phone.*

| In this slice | Out of scope, and why |
|---|---|
| **Step 0 — fix before any screen:** one shared attendance and leave calculation (LV2, LV3). HR Analytics reads it too. A company and branch scope on it, so the LV4 leak closes | — |
| "Leadership" role, plus a User Permission on Company or Branch. Fails closed | Department head across branches: needs the reporting-line scope decision |
| **People:** headcount, joiners, leavers, attrition % (rolling 12 months), by department and branch | Multi-company picker. System Manager stays CXO (slice 010). A person heading two companies waits |
| **Attendance:** present %, late arrivals, short days, 6-month absence trend. "Data up to" line, and a warning on suspicious days (LV1) | **Performance:** needs indexes, an "on track" definition, and your R14 ruling |
| **Leave:** on leave today (count only), taken vs allocated for the current leave period, approvals waiting more than 3 days (count) | **Pay totals:** its own permission tests and no-cache rule (OPS-3). Off by default anyway |
| Drill-down from company → branch → department, totals only, with the group minimum | **Individuals switch:** needs an access log of who opened whom. The setting is designed now, built next |
| Group-minimum setting (default 5), System Manager only, change recorded | **Compliance card:** "401 of 403 missing a document" looks like demo data. Check it first |
| Indexes OPS-5 (Employee and Attendance parts) | Exports, Monday digest, "Remind managers", HR's "preview as leader" page |
| Employee line "who can see this" on My Attendance and My Leave | Hindi copy follows the slice 009 Wave 5 plan |
| Branch head sees no Organisation tab (LV11) | |

**Which kind of change:** new code in the existing `alvoraa_portal` app, plus one role and User Permissions (configuration), plus custom indexes (customisation). The cheaper options fail:
- **Configuration only** (Frappe HR number cards, or adding a leader to the attendance org roles) cannot hide small groups. It shows names and leave types (LV5).
- **Customising `get_hr_analytics`** means building on an unscoped, raw-SQL function (OPS-1).

**Size:** not sized. The engineer sizes it at impact analysis. The UX sizes for the pieces are mostly S and M.

## 6 · Existing problems — where each is handled

| Problem | Recommendation | Why |
|---|---|---|
| LV1 wrong September attendance (all-absent days) | **This slice, Step 0:** "data up to" date and a suspicious-day warning, for HR and leaders. The data itself is HR's to correct | Does not rewrite data. Tells the truth about it |
| LV2 leave utilisation formula | **This slice, Step 0** | Size S. Both screens need it |
| LV3 two attendance formulas | **This slice, Step 0:** one calculation, used by both | "One authoritative total" is the CXO promise |
| LV4 / OPS-1 `get_hr_analytics` unscoped | **Before or with Step 0.** Security engineer confirms now. Scoping it belongs with slice 011's store HR model. If 011 is closed, Step 0 does it | Store HR is exposed today, whether or not 012 ships |
| LV5 org-roles shortcut | **Refused.** Add "not this" to template T6. No code guard | The view makes the shortcut unnecessary |
| LV6 `attendance_analytics.person()` ignores branch | **Separately, now**, to the security engineer | A live gap. Not a leadership feature |
| LV7 / 010 F-15 `set_org_setting` writes any key | **The general fix is separate** (security). **In this slice:** 012's settings do not go through it. They get their own System Manager check and a change record | Otherwise the future pay switch is open to any HR Manager |
| Attrition: no leavers at the reference tenant | **This slice:** show "No leavers recorded in the last 12 months". Show attrition % only when leavers exist. Formula below | Never show 0% when the data is missing |
| No "on track" field on KPI | **Performance slice.** Recommended default in §13 | Not needed for People, Attendance or Leave |

**Attrition formula (recommended):** leavers in the last 12 months (by `relieving_date`, status Left) ÷ average of the headcount 12 months ago and today. Rebuilt from joining and relieving dates. **Known flaw:** Employee holds only the *current* branch, so a transfer moves history with the person. That is fine at company level and rough at branch level. The OPS-8 nightly summary fixes it later. Say "approximate" on the branch figure.

## 7 · Persona enhancements (from 01a §4)

| Persona | Idea | Job | In this slice? | Why |
|---|---|---|---|---|
| Company head | "Your business this month" cards: one number, change, a line in words | One number I trust | **Yes** (3 cards) | Core outcome |
| Company head | Branch comparison table, sorted by name | Compare without ranking | **Yes** | Size S, and the privacy stance made visible |
| Company head | "Data up to" line and suspicious-day warning | Trust | **Yes** | LV1 |
| Company head | Tap to branch, then department, totals only | Drill within the rules | **Yes**, totals only | Individuals come later |
| Company head | "Needs you first" exceptions | Exceptions before lists | **Later** | Needs rules we have not tested. Cards first |
| Company head | Performance shape without names | Is rating fair? | **Later** | Performance slice, R14 |
| Company head | Monday digest | Five minutes without the app | **Later** | Unchecked assumption that leaders read it |
| Company head | Multi-company switcher | Company scope | **Later** | Cannot be proven on a one-company tenant |
| Branch head (phone) | "My branch today": in so far, on leave, not in yet | Is the floor staffed? | **Yes**, if DevOps confirms a today-only check-in count is cheap (OPS-13 tension). If not, "On leave today" only | Real Monday job |
| Branch head | This week vs last week, with the weekday verdict reused | Fix the rota | **Yes** | Reuses LV14 maths |
| Branch head | My branch vs company, beside each number | Where do we stand? | **Yes** | This is the WOW |
| Branch head | Reviews in my branch and "Remind" | Chase the cycle | **Later** | Performance slice |
| Branch head | No Organisation tab, big numbers, 44 px targets | Phone first | **Yes** | Slice 009 frame rules |
| HR Manager | One source of numbers | One answer | **Yes** (Step 0) | LV3 |
| HR Manager | "Who sees what" page and preview as leader | Configure once | **Later** | Belongs to the tenant permission page (templates §6). Set up by hand until then |
| HR Manager | Warning text on the pay switch | Deliberate choices | **Later** | Pay slice |
| HR Manager | HR keeps the name lists | Split work queue from business view | **Yes** | Leaders get counts only |
| HR Manager | Data health strip | Fix wrong numbers | **Yes**, same warning as leaders see | One mechanism |
| Line manager | Nothing taken away. No league table of managers | Must not be ranked | **Yes** (a rule, not a feature) | — |
| Line manager | "Your team vs your branch" | Context | **Later** | Adds the group rule to another screen |
| Employee / frontline | "Who can see this" line | Knows it is fair | **Yes** | Size S. Transparency toward the least powerful person |
| Employee / frontline | Reasons never travel upward. Nothing to do | Presence, not reason | **Yes** (a rule) | — |
| DPO / security | Change record for scope and settings | Prove who did what | **Yes** for group size. Role and permission changes already have Frappe's own history | — |
| DPO / security | Log of individual records a leader opens | Accountability | **Later**, with the individuals switch | — |
| DPO / security | Hidden cell says why | Privacy you can see | **Yes** | — |

## 8 · The WOW

**Screen:** the branch head's Home, top card, on a 360 px phone.
**Moment:** Monday, first thing, before walking the floor.
**Copy (sample numbers):**

> **PPJ Delhi South Extension · September**
> **Attendance 96.1%** ▲ 0.3 points on August · *Company 96.8%*
> Late arrivals 149, 12 fewer than August
> *Data up to 9 Sep*

When the data looks broken, the card says so, instead of showing a bad number as if it were true:

> ⚠ *3 days in September show almost everyone absent. This is usually missing check-in data, not real absence. HR can see this too.*

A hidden group reads: *"Fewer than 5 people — hidden to protect privacy."*

## 9 · Privacy by design

1. **Group minimum 5** (range 3–10) for sensitive numbers: leave, absence, late, short days, leavers, and later ratings and pay. **Headcount and joiners are exempt.**
2. **Subtraction blocking:** if one group in a set is hidden, hide the next-smallest too. A two-branch company shows no branch split for sensitive numbers.
3. **Enforced on the server.** A hidden number is not in the response at all.
4. **No leave type or reason**, ever, at any level.
5. **Leavers are shown only as a rolling 12-month figure at branch level**, never "1 leaver this month".
6. **Pay (later slice):** company and branch level only. Never by department or designation. Not cached (OPS-3).
7. **No exports** in this slice. No names, pay or scope in URLs or logs (OPS-11).
8. **A leader's own record counts** inside their totals. The design notes this. No new rule.

## 10 · Run-side reality (DevOps red flags carried in)

| OPS | Carried into this slice as |
|---|---|
| OPS-1 | Do not reuse `get_hr_analytics`. One server-side scope check feeds every number |
| OPS-2, OPS-10 | Cache totals only. The key includes scope type, scope value, settings version and period. Every key expires |
| OPS-4 | Refresh on a timer (10–15 min). Show "as of 10:40". Clear on settings change, not on document saves |
| OPS-5 | Indexes on Employee (`company`, `branch`, `department`, `date_of_joining`, `relieving_date`) and Attendance (`alvoraa_branch`, `attendance_date`). KPI and Appraisal indexes come with the Performance slice |
| OPS-6 | Count with SQL GROUP BY. Do not reuse `_analyse`, `get_team_goals` or `_mark_actionable` as they fetch |
| OPS-7 | Fixed query count per endpoint in tests. Time on a synthetic 2,000-person site: ≤ 500 ms per call, ≤ 3 s per page |
| OPS-8 | Consider, not in this slice. Becomes needed if a 5,000-person customer is real. That is 2.5 times the NFR design ceiling. **You need to confirm the customer size** |
| OPS-13 | Tiles use Attendance, not Employee Checkin. The only exception is the "in so far today" count, which needs a DevOps check at design (§7) |
| — | Slice 011's branch field has not been migrated on `ppj.localhost` yet. Measurement needs that first |

No new service, domain or spend at the reference tenant's size (07 §1).

## 11 · Success criteria

| # | Measure | Baseline | Target | How measured |
|---|---|---|---|---|
| S1 (lagging) | Leaders served without HR Manager | 1 of 1 known leader holds HR Manager (reference tenant) | At least one leader works from the Leadership role alone within 30 days. Removing HR Manager is the customer's choice | Role assignments on the tenant, checked at day 30 |
| S2 (leading) | Number agreement between HR Analytics and the leadership view | Two formulas disagree (LV3) | 0 differences for the same scope and period | Automated test comparing both endpoints, plus a monthly spot check |
| S3 (leading) | Scope leaks | Store HR sees all branches today (LV4) | 0: no response to a branch head holds another branch's data or any hidden group | Negative permission tests on every endpoint |
| S4 (outcome) | Time to answer three questions on a phone ("attendance vs company", "on leave today", "leavers this year") | Baseline unknown — measure first, with today's screens | Under 2 minutes, unaided, for 3 of 3 test leaders | Moderated test with the owner and 2 store heads |

## 12 · Thriving-workplace check and regulatory read

| Lens | Answer |
|---|---|
| Engagement | Branch heads get clarity and momentum: their branch against the company, in words |
| Collaboration | The data warning makes HR's data gaps visible to the leader who can push for fixing them |
| Inclusiveness | Phone first for store heads without laptops. Hindi waits for 009 Wave 5, which is a gap for Hindi-first store heads |
| Transparency | Leaders see totals that used to need HR Manager. Employees see who sees what. Small groups stay hidden, so this is safe for the least powerful person in the picture |

**Regulatory read** (I am not a lawyer):
1. **Regime:** DPDP Act 2023 (purpose limitation, data minimisation). No AI. No employment-law change.
2. **Whose duty:** the employer's, as Data Fiduciary. This slice helps the customer meet it: minimum data by default, with a change record. That is the one that wins the security review.
3. **What is new:** new visibility (totals for a role that could not see them). No new personal data collected. No automated decisions.
4. **Front page test:** "Owner sees branch totals, not who took sick leave." Yes, we would defend it. The pay slice will need its own read.

No ⚠ COMPLIANCE ruling is needed for this slice.

## 13 · Risks

- **Branch User Permission side effects.** Adding a Branch permission narrows *every* doctype with a branch field for that user. A store head may lose sight of head-office colleagues or records they use today. **Cheapest check:** on the local copy, the engineer lists what a store head can see before and after the permission.
- **Role name collision.** `alvoraa_policy_library/access.py:50` already gives anyone holding "Alvoraa CXO" (and any department head) "sees all" on policies. A new leadership role must not reuse that name for branch heads.
- **Rating distribution vs R14.** R14 says a rating is visible only inside the review, to authorised people. An aggregate with a group minimum shows no one's rating, but it is still ratings shown outside the review. With the individuals switch on, it would conflict directly. It also must read the frozen review copies (R13), completed cycles only.
- **Data poverty.** If most cards say "not recorded", the view shows a data-capture problem, not a leadership insight.

## Gate decision (2026-09-15)

**Build.** The user accepted the recommended defaults for P1–P4:
- **P1** "Leadership" role plus a Company or Branch User Permission; no permission = sees nothing.
- **P2** System Manager only may change the sensitive settings; every change recorded (who, when, before, after).
- **P3** Minimum group size 5 (allowed 3–10), with subtraction blocking; headcount and joiners exempt.
- **P4** Fix the wrong numbers as Step 0 of this slice, including scoping HR Analytics (`get_hr_analytics`) to the caller's company or branch. Slice 011 is closed, so the scope fix belongs here.

P5–P9 stay open; none blocks this slice.

## Open questions

| # | Question | Recommended default | Owner | Blocks |
|---|---|---|---|---|
| P1 | How is a leader identified? | New role "Leadership", plus a User Permission on Company (company head) or Branch (branch head). No permission = sees nothing. Not "Alvoraa CXO" | Surbhi; engineer checks side effects | Design, everything |
| P2 | Who may change the group minimum, and later the individuals and pay switches? Are changes recorded? | **System Manager only.** HR Manager can read the settings. Every change is recorded with who, when, before and after | Surbhi, with security | Settings, 01c |
| P3 | Minimum group size | 5, allowed 3–10, with subtraction blocking. Headcount and joiners exempt | Surbhi, with security | Every card |
| P4 | Fix the wrong numbers first? | Yes, as Step 0 of this slice. The LV4 scope fix goes with it unless slice 011 takes it | Surbhi | Order of work |
| P5 | How is "on track" defined? | `Individual Goal` already has `trajectory` (On Track / At Risk / Off Track, from time elapsed vs progress). Use it. For KPI, apply the same thresholds to `attainment_pct` (SRS FR-H3). Show "not recorded" when there are no goals | Surbhi | Performance slice |
| P6 | Which plan includes the view? `analytics` is Enterprise only today | Keep it under `analytics` for now. Pricing is yours | Surbhi / founder | Gating |
| P7 | Does an aggregate rating distribution break R14? | Allow counts at company and branch level, completed cycles only, group minimum applied. Never in individual drill-down | Surbhi | Performance slice |
| P8 | Real customer size: is 5,000 employees a real target? | Plan for 2,000 (NFR budget). Revisit OPS-8 if it is real | Founder | OPS-8 |
| P9 | Default for the individuals switch when it is built | Totals only | Surbhi | Next slice |

P1–P4 block the design step. P5–P9 do not block this slice.

## Assumptions

- `[ASSUMPTION]` A company head and a branch head can share one screen at two scopes. The design check will test that.
- `[ASSUMPTION]` The all-absent days on 7–9 Sep are a data artefact, not real absence (01a).
- `[ASSUMPTION]` Store heads read their numbers on a phone of about 360 px.
- `[ASSUMPTION]` A today-only check-in count by branch is cheap. DevOps has not confirmed this.
- `[ASSUMPTION]` Competitor claims come from search summaries, not trials. The CatalystOne row is entirely from memory.
- `[ASSUMPTION]` Rebuilding headcount 12 months ago from joining and relieving dates is good enough at company level.

## Kill criteria

- In the prototype test, the owner and 2 store heads cannot name one action they would take from the view. Stop and rethink the job.
- A Branch User Permission breaks screens a store head uses today, and there is no clean alternative. Stop and redesign how leaders are identified before building.
- After Step 0, more than half the cards at the measurement tenant say "not recorded". Pause the view and fix data capture first.

## Handoff note

To the UX designer: design only People, Attendance and Leave, at two scopes, phone first, inside the slice 009 frame (Company › Overview; the branch head's Home). Design these states on purpose: hidden group, "not recorded", suspicious data, no permission (a leader role with no Company or Branch permission), and a company with exactly two branches. To security (01c): LV6 and LV7 are live today, so take them now. Confirm LV4 and who fixes it. Write the group-minimum and subtraction rules as PRIV requirements. To the engineer: Step 0 comes first, and P1's side-effect check comes before any strategy. I disagree with nothing upstream. I cut Performance, Pay and Compliance to the next slices on DevOps' order.
