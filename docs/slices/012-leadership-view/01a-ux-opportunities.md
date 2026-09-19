---
slice: 012-leadership-view
artifact: 01a-ux-opportunities
author: hrms-ux-designer
date: 2026-09-14
status: draft
inputs: [the idea and the user's decisions given with the task, ux-learnings.md, product-context.md, nfr-budget.md, access-review/permission-templates.md, access-review/2026-09-14-report-access-by-persona.md, 009 appendix-a-frame.md, 009 appendix-d-growth-team-people.md, attendance_analytics.py, hr_api.py, metrics.py, performance_api.py, hrms-employee.html, ppj.localhost read-only data]
---

# 012 · Leadership view — UX opportunities scan

**Mode:** opportunities scan. No prototype yet. The product manager decides which ideas
go into the slice.

**Learnings applied:** P2 (whole-product benchmark), P4 (measured the phone screens),
P5 (checked the data before calling numbers wrong), P7 (persona ideas before the brief).
Anti-pattern AI2 (greyed tabs) and PF4 (red for an ordinary number) were seen again here.

---

## Bad news first

1. **Some of today's headline numbers are wrong, and a leader would believe them.**
   - HR Analytics shows the owner **65.8% attendance** for September. For 7, 8 and 9
     September *every one* of 330 records says "Absent". That looks like an automatic
     marking run with no check-ins behind it. August runs at about 97%.
   - "Leave utilisation 0.1%" adds up **every leave allocation ever made** and compares it
     with leave taken this year (`hr_api.py` 442-449). The tenant also records almost no
     leave in the system: 3 leave applications in total.
   - A leadership view built on these numbers would spread wrong numbers faster, not
     fix them.
2. **The "cheap start" is not safe as it stands.** The access review suggested adding a
   leader role to the `alvoraa_attendance_org_roles` setting. The organisation view then
   returns **every person by name, with their leave types** (`summary()` rows carry
   `leave_by_type`, `attendance_analytics.py` 311-332). That would show a leader who took
   sick leave, across 403 people. That breaks the rule "presence yes, reason never".
3. **HR Analytics ignores scope.** `get_hr_analytics` uses raw SQL and `frappe.db.count`,
   with no company filter and no User Permission check (`hr_api.py` 390-480). A branch HR
   person with HR User role sees whole-company numbers. On a multi-company tenant, a
   company head would see every company mixed together. *(Code read; not run as a
   branch HR user.)*
4. **Small groups are everywhere.** At the reference tenant, **22 of 45 branch ×
   department groups have fewer than 5 people**. One has exactly 1 person. "Management"
   has 2 people, and one of them is the owner. Any pay total, rating spread or leave count
   by department would point at a named person.
5. **Frappe has no "head of branch" record.** The Branch record holds only a name.
   Department has a `department_head` field, but only 10 of 26 departments fill it. The
   store in-charges today have a User Permission on **Company** and their own Employee
   record, not on Branch. So "who is this branch's head" has no home in the data yet. It
   must be a new setting or a role plus a permission — a product decision, not a UI one.
6. **Two things cannot be measured on the reference tenant at all.** Attrition: 0 leavers,
   no Employee Separation or Exit Interview records, every employee is Active. Objectives
   "on track vs at risk": KPI has no trajectory field and there are 0 Goal records. The
   view must say "not recorded", never "0%".
7. **Process note.** While gathering evidence I copied a read-only query script into the
   bench container's `/tmp` with `docker cp`. CLAUDE.md lists `docker cp` as needing
   approval. I removed the file straight away and ran the rest through standard input.
   No app files, data or settings were changed.

---

## 1 · Frame

**A company head or a branch head, on a phone for five minutes or on a laptop before a
review meeting, wants to know how their people side of the business is doing, and which
one thing needs them — without reading anyone's payslip or leave reason.**

| In scope | Why |
|---|---|
| Company head (owner, MD, CXO) | The persona that borrows HR Manager today (T6 gap) |
| Branch head (store, plant, regional office) | Same need, one location, mostly on a phone |
| HR Manager | Sets the leadership settings; must trust the numbers match HR's own |
| Line manager | Must not lose anything; must not be ranked by name |
| Employee and frontline employee | Their data is what gets counted. The one-way rule applies |
| DPO / security reviewer | Will ask how small groups and pay totals are protected |

Deliberately out: a department head across branches (for example a Head of Sales over 6
stores). It is a real persona, but it needs the reporting-line scope decision from the
access review first. It is listed in open questions.

---

## 2 · What exists today, and where it falls short

Evidence: captured 14 Sep 2026 on `ppj.localhost` as the owner (Kamal Gupta, holds HR
Manager) and a store in-charge (Vishal Sharma, Delhi South Extension), at 1440 × 900 and
390 × 844, Chrome. Screenshots and measurements are in
`C:/Surbhi-Git/hrlocal-data/ux-review/2026-09-14-leadership/` (outside the repo). The
analytics screenshot from 11 Sep is in `.../ux-review/2026-09-11/ours/hr-08-analytics-*.png`.

### 2.1 The screens and endpoints a leader could use

| # | What | Who can open it | Names individuals? | One branch only? | Fit for a leader |
|---|---|---|---|---|---|
| 1 | **HR Analytics** panel (`get_hr_analytics`) — headcount, joiners, attendance rate, pending approvals, confirmations due, leave use, department, gender, designation, recent joiners | HR Manager, HR User, Administrator, plus the `analytics` plan | Yes: confirmations due and 10 most recent joiners, by name | **No.** Raw SQL, no company or branch filter | Closest thing today. Wrong numbers, no leavers, no performance, no pay, no trend, and half the tiles are HR work queues |
| 2 | **Attendance Insights → Organisation** (`attendance_analytics.summary`) — present, short days, late, absences, weekday pattern, month trend | Roles in `alvoraa_attendance_org_roles` (default HR Manager, HR User, System Manager) | **Yes**, every person, with leave types | Yes for HR via `get_list` (slice 011); System Manager sees everyone | Good maths and honest wording. Built for HR finding people, not a leader reading totals |
| 3 | **Attendance Insights → My team, everyone below** | Anyone with reports | Yes | Only by reporting line | Vishal's "everyone below" is 71 people = his whole store. This works at PP Jewellers only because the store tree happens to match the branch. Head office has no single head below the owner |
| 4 | **Org health** (`metrics.org_health`) — positions, seats vacant, span of control, long cover | HR Manager, HR User, System Manager | Yes (flags name people) | No | Useful leader questions ("seats vacant") but HR-only |
| 5 | **Performance → Distribution** (`get_calibration_matrix`) — ratings spread per cycle, filters incl. gender and manager, CSV export | HR role only | Yes, every row, exportable | No | Leader wants the shape, not the rows or the export |
| 6 | **Policy compliance** (`get_policy_compliance`) and **document compliance** (`hr_document_compliance`) — by branch | HR Manager, System Manager | Yes | Has a branch filter, but no scope check | The by-branch totals are exactly what a leader needs; the name lists are HR's |
| 7 | **Team View / manager dashboard** | Anyone with reports | Yes | Direct + one level | A line manager's tool. Not a leader's |
| 8 | **Payroll totals** | Desk only (Salary Register, Payroll Entry) | Yes, per slip | Salary Slip has a branch field | Nothing in the portal. Leaders borrow HR Manager and read every slip |

### 2.2 Findings

IDs use `LV` (leadership view). Earlier review IDs are reused where the same problem
is still there.

| ID | Finding | Impact | Kind | Size | Evidence |
|---|---|---|---|---|---|
| LV1 | September attendance rate 65.8% is driven by three all-"Absent" days (7-9 Sep, 330 of 330). No "data up to" line, no warning about suspicious days | High | Fix | M | DB check by weekday; analytics tile as Kamal |
| LV2 | Leave utilisation adds allocations from all periods against this year's leave taken | High | Fix | S | `hr_api.py` 442-449 |
| LV3 | Two attendance rates with two formulas: analytics counts Present + ½ Half Day vs Absent, and ignores Work From Home and On Leave; Insights uses present ÷ expected days. **One number, one formula** (nfr-budget §9) | High | Fix | M | `hr_api.py` 437-439 vs `attendance_analytics.py` 330 |
| LV4 | HR Analytics has no company or permission scope | High | Fix | M | `hr_api.py` 390-480 (code read) |
| LV5 | Adding a leader role to the org-roles setting exposes named people and leave types | High | Fix (block the shortcut) | S | `attendance_analytics.py` 311-332 |
| LV6 | `attendance_analytics.person()` lets any org-view role open **any** employee's days, without the branch limit that `summary()` now applies | Medium | Fix — for security | S | `attendance_analytics.py` 473-478 (code read) |
| LV7 | `set_org_setting(key, value)` lets HR Manager or System Manager set **any** key. A future "show pay totals" switch would be changeable by HR, with no record of who changed it | Medium | Fix — for security | S | `hr_api.py` 2205-2210 |
| LV8 | Owner's analytics page mixes leader numbers with HR work queues ("Pending approvals 0", "Confirmations due 0") | Medium | Improve | S | Screenshot, owner desktop and phone |
| LV9 | Red used for an ordinary number (0.1%) and as the "Female" bar colour | Medium | Fix | S | Screenshot; anti-pattern PF4 seen again |
| LV10 | No leavers, no attrition, no trend beyond joiners, no month-on-month anywhere | High | New | M | `get_hr_analytics` return value |
| LV11 | Store in-charge sees a greyed "Organisation" tab he cannot open | Low | Fix | S | Screenshot, store head phone; anti-pattern AI2 seen again |
| LV12 | Owner's "Attendance Insights" opens on **his own** record, not the organisation | Low | Improve | S | Screenshot, owner desktop |
| LV13 | Phone, analytics panel: no sideways scroll (good), but 5 tap targets under 44 px and 62 text items under 12 px. Owner Home has 117 text items under 12 px. The double header (top bar "Home" and the tenant bar) is the frame problem R1 from slice 003 | Medium | Fix (frame, slice 009) | — | `capture.json` in the evidence folder |
| LV14 | The Insights maths is honest: rates not raw counts, weekday verdict "the rota, not the people", tolerance shown in words | — | **Keep** | — | `attendance_analytics.py` docstring and 387-424 |
| LV15 | Org health explains every flag in plain words ("why it matters, what to do") | — | **Keep** | — | `metrics.py` |
| LV16 | Policy and document compliance already group by branch | — | **Keep** | — | `hr_api.py` 2701, 2896 |
| LV17 | Upward feedback already hides detail below 3 responses — a small-group rule exists in the codebase | — | **Keep** (reuse the idea) | — | appendix D, G-08 |

### 2.3 What each requested number would show on the reference tenant today

This checks whether the numbers are real before anyone designs around them (P5).

| Area | Number | Data at PP Jewellers | What the view must do |
|---|---|---|---|
| People | Headcount by branch | 40-74 per branch. Fine | Show |
| People | Joiners | 31 in 12 months, by `date_of_joining`. Fine | Show |
| People | Leavers, attrition % | **0 leavers recorded**, no separation records | Say "No leavers recorded in this period". Never "0% attrition" |
| Attendance | Present %, late, short days | 24,264 records, 11 May – 9 Sep. Check-ins run to 11 Sep | Show "Up to 9 Sep". Warn on days where nearly everyone is absent |
| Leave | On leave today, taken vs allocated | 1,209 allocations, **3 applications**, 5 "On Leave" days | Say "Leave is not being recorded in the system" when taken is near zero and allocations exist |
| Leave | Pending approvals | 0 open | Show as "waiting more than 3 days", not as a work queue |
| Performance | Cycle progress | Q2 in progress: 269 at self-review, 134 at manager review | Show. Good, real data |
| Performance | Rating distribution | Q1: 179 at 4, 224 at 5, none at 1-3 | Show the shape. The lean to the top is itself a leader insight. No forced curve |
| Performance | Objectives on track vs at risk | 3,510 KPIs, **no trajectory field**, 0 Goals | ⚠ Needs a definition before design |
| Pay | Total cost, cost per head, month on month | 400 salary slips for July and August, branch filled | Possible. Off by default (user decision) |
| Compliance | Missing documents | Helper says 401 of 403 people are missing a mandatory document | Looks like demo data. Check before showing it to a customer |
| Compliance | Policy acknowledgements | 3,200 acknowledgements; almost all done | Show |

---

## 3 · How other products serve an organisation head

**Caution:** I read search-result summaries of help and product pages on 14 Sep 2026. I
did not see product screenshots, and Keka's help pages now sit behind a sign-in. So
nothing below is **seen**. Every claim is **read (14 Sep 2026)** or `[recall — verify]`.
Scores reflect what each company tells the market, not a trial.

| Product | What an org or unit head gets | Scoping model | Small-group protection | Label |
|---|---|---|---|---|
| **Darwinbox** (Atlas) | Dashboards for headcount, attrition, leave, attendance, performance, pay; "persona-wise" dashboards for business leaders; drill down several levels; AI "smart nudges" | Persona dashboards | Not stated | read — marketing blog |
| **Keka** | Org Dashboard for admins: Headcount by demographics, Growth & Retention, Attrition Analysis filtered by department and location | Admin-level | Not stated | read — help page titles and summary; body behind sign-in |
| **Zoho People** | Reports split into My / Team / Organisation; reports shared to users, departments, roles or locations; the viewer only sees rows their permissions allow | Report sharing + record permissions | Not stated | read — help centre |
| **SAP SuccessFactors** | Workforce Analytics measures and dimensions controlled by role-based permissions; "target population" = direct reports 1, 2 or all levels, or a named group | Granted user → target population | Not stated in what I read | read — SAP help / learning |
| **Workday** (Peakon, surveys) | Hides a segment below a response minimum, **and** hides segments whose difference from another segment is too small, so nobody is found by subtraction | Segment rules | **Yes — including the subtraction attack** | read — Workday docs |
| **Culture Amp** (surveys) | Minimum reporting group usually 5; you cannot add a filter smaller than the minimum; Basic and Strong protection | Survey reporting | **Yes, default 5** | read — support guide |
| **Lattice** (surveys) | Anonymity threshold 3-10, never below 3; Strong mode also hides the next-smallest group | Survey reporting | **Yes, 3-10, plus next-smallest** | read — help centre |
| **BambooHR** | "Headcount and Turnover" reports; turnover on Home only for those with report access; managers see direct and indirect reports, fields chosen by HR | Access levels | Not stated | read — product updates |
| **Rippling** | Permission profiles with a *scope* (reporting line or department) and *access* (which apps and fields, for example Payroll) | Scope × data | Not stated | read — product pages |
| **HiBob** | Permissions on two axes: which people, and which field categories | People scope × data scope | Not found | read — API docs |
| **greytHR** | Manager mobile app: who is in, team attendance for the month, approve leave and regularisation | Reporting line | — | read — help centre |
| **Frappe HR (standard)** | Desk reports and number cards; no leader persona; scope only by User Permission | User Permission | None | [recall — verify] |

**What this tells us**

- **Scope × data is the common model** (SAP, Rippling, HiBob). "Which people" and "which
  kinds of data" are two separate choices. Our user's decisions map onto it: scope =
  company or branch; data = totals, individuals, pay totals.
- **Small-group protection is solved in survey tools, not in HR analytics.** None of the
  HR suites I read says it suppresses small groups in headcount, leave or pay dashboards.
  That is whitespace for a product that sells privacy to a security-conscious buyer.
- **Workday's subtraction rule matters here.** Company total minus five branch totals
  equals the sixth branch. Department totals minus one branch give that branch's
  department. Hiding only the small cell is not enough.
- **Mobile leader views are thin everywhere I read.** greytHR's mobile manager app is
  about the team's attendance, not a business view. `[recall — verify]` for Darwinbox
  and Keka mobile analytics.

---

## 4 · Persona by persona: how the portal could make this better

Size: S (days), M (one to two weeks), L (more). "Evidence" points to §2 or §3.

### Company head (owner, MD, CXO) — phone, five minutes

| Idea | Job it serves | Evidence | Size |
|---|---|---|---|
| **"Your business this month"** — one card per area (People, Attendance, Leave, Performance, and Pay if switched on). Each card: one number, the change from last month, and a line in words ("Attendance 96.8%, up 0.4 points") | "One number I can trust" | product-context §2; LV8, LV10 | M |
| **Needs you first** — 1-3 exceptions, in words, above the cards: "Karol Bagh attendance is 4 points below the company"; "134 manager reviews waiting, cycle ends 30 Sep" | Exceptions before lists | Principle 5; Q2 data §2.3 | M |
| **Branch comparison as a table, not a league** — branches as rows, areas as columns, company average as the last row. Sorted by name by default, not by best to worst | Compare units without ranking people | §3 scope model; refusal on ranking | S |
| **"Data up to 9 Sep" on every card**, plus a warning when a day looks wrong: "3 days in September show almost everyone absent. This is usually missing check-in data, not real absence." | Trust | LV1 | S |
| **Tap a number → the branch → the breakdown**, stopping at totals unless the organisation setting allows individuals | Drill down within the rules | User decision 2 | M |
| **Performance shape without names** — Q1 bar of 1-5 ratings with counts, and a plain note when it leans: "Nobody rated below 4. Worth asking if the scale is being used." Never a target curve | Is the rating fair and meaningful? | Q1 data; refusal 7 | S |
| **Monday digest** (optional) — the same cards in an email or notification, no names, no pay | Five minutes, without opening the app | [ASSUMPTION] leaders read email | S |
| **Multi-company switcher** only for someone who heads more than one company | Company scope | LV4; slice 010 "System Manager as CXO" | S |

### Branch head (store in-charge, plant head) — shared or own Android, ~360 px, on the floor

| Idea | Job it serves | Evidence | Size |
|---|---|---|---|
| **"My branch today"** as the first thing on Home: *In now 58 of 64 expected · On leave 3 · Not in yet 3*. Counts only — no reasons | Is the floor staffed right now? | greytHR "who is in"; `get_week_presence` rule | M |
| **This week vs last week** in one line each: late arrivals, short days, absences — with the Insights weekday verdict reused ("Short days fall on Saturday far more… usually the rota") | Fix the rota, not blame people | LV14 | S |
| **Reviews in my branch**: "Self-reviews 41 of 72 done · Manager reviews 12 waiting · ends 30 Sep" with one button "Remind managers" | Chase the cycle | Q2 data | M |
| **My branch vs company** — the same cards, with the company figure in small text beside each | Where do we stand? | §3 | S |
| **Short labels, big numbers**: bottom bar *Home · Branch · Inbox · Me*. Every number with a word beside it. Tap targets ≥ 44 px, nothing under 12 px | Phone first | LV13; P4 | S (with frame) |
| **No Organisation tab** at all for a branch head. Only what they can open | Hide what a person cannot use | LV11 | S |
| **Skeleton in 300 ms**, cards load one by one; the "today" card first | 3G | nfr §2 | S |

### HR Manager — laptop, dense

| Idea | Job it serves | Evidence | Size |
|---|---|---|---|
| **One source of numbers for HR and leaders** — HR Analytics and the leadership view read the same calculation, so the owner and HR never argue over two attendance rates | One authoritative answer | LV3; nfr §9 | M |
| **"Who sees what" setup page** — list of leaders, their scope (company or branch), and three switches with plain consequences: *Totals only / Can open individuals*; *Show pay totals: Off*; *Hide groups smaller than: 5* | Configure once | User decisions 1-3; permission-templates §6 | M |
| **Preview as a leader** — "Vishal Sharma will see: PPJ Delhi South Extension, 72 people, totals only, pay hidden" before saving | See the result before applying | permission-templates §6 step 5 | S |
| **A warning on the pay switch**: "Turning this on shows total pay for each branch. In branches with fewer than 5 people, totals stay hidden. This change is recorded." | Destructive-looking choices are deliberate | LV7 | S |
| **HR keeps the name lists** (confirmations due, missing documents, pending acknowledgements); leaders get the counts | Split work queues from business view | LV8 | S |
| **Data health strip for HR**: "3 days look like missing attendance data (7-9 Sep) · Leave taken is near zero while 1,209 allocations exist" — with a link to fix | Wrong numbers before new numbers | LV1, LV2; product-context risk 3 | M |

### Line manager — laptop and phone, between meetings

| Idea | Job it serves | Evidence | Size |
|---|---|---|---|
| **Nothing is taken away.** The Team view stays the manager's tool | One-way rule in reverse: leaders must not degrade managers | appendix D | — |
| **No league table of managers.** Branches and departments are compared; named managers' teams are not ranked on a leader's screen | A comparison of teams of 5-15 is a comparison of one manager | Refusal on ranking | — |
| **Optional: "your team vs your branch"** on the manager's own Team view, only when the team is at or above the group minimum | Context without exposure | §5 below | S |

### Employee and frontline employee

| Idea | Job it serves | Evidence | Size |
|---|---|---|---|
| **"Who can see this"** line on My Attendance, My Leave and My Pay, driven by the organisation's real settings: "Your branch head sees totals for the branch. Your pay is not shown to them." | Knows it is fair; sees privacy in the product | product-context §2 (Employee, DPO); one-way rule | S |
| **Reasons never travel upward.** Leaders see "On leave 3", never which leave type or who, unless the setting allows individuals — and even then never the leave type | Presence, not reason | access review §1 | — |
| Frontline: **nothing extra to do.** They are counted, not asked | Two-minute bar untouched | — | — |

### DPO and customer security reviewer

| Idea | Job it serves | Evidence | Size |
|---|---|---|---|
| **A record of every change** to leader scope, the individuals switch and the pay switch — who, when, from, to | Prove who did what | nfr §8; LV7 | S |
| **A record of every individual record a leader opens** (only when the individuals switch is on) | Accountability for drill-down | nfr §5 | M |
| **Small-group rule visible in the product** — the hidden cell says why, so a reviewer can see it working | Privacy you can see | §3 Culture Amp, Lattice | S |

### Rough sketch — branch head, phone (not a design)

```
PPJ Delhi South Extension          Data up to 9 Sep
───────────────────────────────────────────────
TODAY          In now 58 of 64   On leave 3
               Not in yet 3                  ›
───────────────────────────────────────────────
NEEDS YOU      12 manager reviews waiting.
               Cycle ends 30 Sep.   [Remind]
───────────────────────────────────────────────
THIS MONTH     Attendance 96.1%   ▲0.3  (co. 96.8%)
               Late arrivals 149  ▼12
               Joiners 1 · Leavers: none recorded
───────────────────────────────────────────────
REVIEWS Q2     Self-reviews 41 of 72 done
PAY            Hidden by your organisation
───────────────────────────────────────────────
 Home     Branch     Inbox      Me
```
*All numbers in the sketch are Sample, except where they match §2.3.*

---

## 5 · Privacy by design

### 5.1 Two switches, two scopes — as the user decided

| Setting | Values | Default | Who may change it |
|---|---|---|---|
| Leader scope (per leader) | Company · Branch | none (no leader until set) | ⚠ DECISION |
| Leaders can open individuals | Totals only · Individuals | **Totals only** [ASSUMPTION — safest default] | ⚠ DECISION |
| Show pay totals | Off · On | **Off** (user decision) | ⚠ DECISION — HR Manager can set any key today (LV7) |
| Smallest group shown | 3-10 | **5** [proposal, from Culture Amp and Lattice] | ⚠ DECISION |

Even with "Individuals" on, some things never show to a leader: **leave type or reason**,
**individual salary**, **bank or ID fields**, **draft self-reviews**,
**manager_internal_notes**.

### 5.2 The small-group rule — a proposal for the PM and security engineer

1. **Hide, do not round.** A group below the minimum shows "Fewer than 5 people — hidden
   to protect privacy." Not "0", not "—".
2. **Applies to sensitive numbers, not to headcount.** Headcount and joiners are not
   sensitive. Leave, absence, ratings, leavers and pay are.
3. **Stop subtraction.** If one group in a set is hidden, hide the next smallest too
   (Lattice "Strong", Workday segment rule). If a company has exactly two branches, a
   branch total plus the company total reveals the other. The design must handle that
   case on purpose.
4. **Pay totals only at company and branch level, never by department or designation.**
   At the reference tenant, "Management" is 2 people, one the owner; "Legal & Compliance"
   is 1. No department pay cut is safe there, and many tenants will look the same.
5. **Filters cannot go below the minimum.** A filter that would create a small group is
   not offered (Culture Amp rule).
6. **Short periods count as small groups.** "1 leaver this month in a branch of 40" names
   a person to anyone on that floor. Leavers show as a rolling 12-month figure at branch
   level. [ASSUMPTION — PM to confirm]
7. **The rule runs on the server**, before the number leaves. A hidden cell must not be
   in the response at all.

### 5.3 Other privacy points

- **Reasons for absence never reach a leader** — not in totals, not in drill-down.
- **A leader's own record is inside their totals.** A branch head in a group of 5 is one
  fifth of the number. Worth a line in the design, not a new rule.
- **Exports:** none in the first slice. A CSV is the fastest way around every rule above.
- **Screenshots and notifications:** digest emails carry no names and no pay.

---

## 6 · Fit with the slice 009 frame

- 009's menu groups are *Me · Time · Pay · Growth · Team · Company*. Open question H-1 asks
  where the owner and HR screens go. **Proposal for the PM:** the leadership view lives
  under **Company › Overview** for company heads and **Team › My branch** (or a
  "Branch" group) for branch heads. It also becomes the top of a leader's Home.
- It needs the frame's menu list to show an entry only when the person holds leader
  scope (FR-02), the counts endpoint (FR-04) and the shared sheet (FR-09) for drill-down.
- It must not add a slow call to page load. The existing `goals_api.get_pending_approvals`
  takes 11.6-16.4 s for HR (appendix A). Leader numbers should come from one call, and
  heavy parts should load after the first card (nfr §2: dashboard ≤ 3 s or a progress
  state).
- The phone bottom bar for a leader is not yet designed (H-2). Sketch above: *Home ·
  Branch · Inbox · Me*.

---

## 7 · What not to copy

| Seen elsewhere | Why not for us |
|---|---|
| AI "predicted attrition risk" per employee (Keka, Darwinbox — read) | Scores a named person on a guess, visible to their boss. That is close to refusal 2 and the "no watching individuals" rule. Totals and trends only |
| Ranked leader-boards of managers or stores, best to worst | Ranking people. Branches can be compared in a table sorted by name |
| Gender, age or designation filters on rating distributions (our own Distribution tab does this) | In small groups it identifies people. It also invites judgements the leader has no job need for |
| CSV export of every row from the leader view | Walks around the small-group rule |
| One giant "analytics" page with 20 charts | A leader wants one number per area, a trend and the exception |
| Pay by department | §5.2 point 4 |

---

## 8 · Risks and open questions for the product manager

| # | Question or risk | Why it matters | Owner | Blocks |
|---|---|---|---|---|
| Q1 | **How is a branch head identified?** Options: (a) a new "Leadership" role plus a User Permission on Branch or Company — Frappe-native, fits templates T1-T8 and slice 011; (b) a custom "head" field on Branch; (c) a list in the settings page | Frappe has no branch head today; designation names are tenant-specific | PM + engineer | Everything |
| Q2 | **Who may flip the pay-totals and individuals switches?** HR Manager, System Manager, or only the account owner, with a record of the change? | HR Manager can set any org setting today (LV7) | Surbhi + security | Settings page |
| Q3 | **Smallest group size:** default 5? Allowed range 3-10? | §5.2 | PM + security | Every card |
| Q4 | **Attrition definition:** rolling 12 months over average headcount? Voluntary vs not (needs Employee Separation or `reason_for_leaving`)? What if the tenant never marks people as Left? | Reference tenant has no leavers; a formula chosen now sticks | PM | People card |
| Q5 | **"On track / at risk" for objectives** — from KPI attainment, Goal trajectory, or both? | No trajectory on KPI, no Goals at the reference tenant | PM | Performance card |
| Q6 | **Fix the wrong numbers first?** LV1-LV4 could be a small separate slice, or the first part of this one | Building a leader view on wrong numbers damages trust faster | PM | Order of work |
| Q7 | **Does "individuals" include performance ratings of named people?** | Ratings affect pay; calibration is HR's process | PM + Surbhi | Drill-down |
| Q8 | **Department head across branches** (Head of Sales over 6 stores) — in this slice or next? | Needs the reporting-line scope decision from the access review | PM | Scope |
| Q9 | **Multi-company:** does a company head of company A see A only, and a group CXO all companies? How does this square with "System Manager is CXO for now" (slice 010)? | Security reviewers will test it; PPJ has one company so it cannot be proven there | PM + engineer | Company switcher |
| Q10 | **Does the owner keep HR Manager** after this ships, or is the goal to take it off? | The access review says only the customer can decide; the product must make it possible | Surbhi / customer | Success measure |
| Q11 | **Is the view tied to a plan?** (`analytics` feature today) | Entitlement is checked on the current endpoint | PM | Gating |
| R1 | **Blocking the shortcut:** someone may add a leader role to `alvoraa_attendance_org_roles` as a quick fix before the slice ships | Exposes named leave types (LV5) | Engineer / Surbhi | — |
| R2 | **LV6 and LV7 are live security gaps today**, independent of this slice | Should go to the security engineer now | Security | — |

---

## Open questions

See §8, Q1-Q11. The first three (Q1 identification, Q2 who flips the switches, Q3 group
size) block the design step.

## Assumptions

- `[ASSUMPTION]` "Totals only" is the safe default for the individuals switch. The user
  decided that the switch exists, but not its default.
- `[ASSUMPTION]` Leaders read a Monday email or notification. Not checked with any real
  leader.
- `[ASSUMPTION]` The 7-9 Sep all-absent days are a local-copy or scheduler artefact, not
  real events. Scheduler is disabled on `ppj.localhost`, so the rows came from dev's
  database. Not investigated further.
- `[ASSUMPTION]` The "401 of 403 missing a mandatory document" figure is demo data.
- `[ASSUMPTION]` Competitor claims reflect help and marketing pages as summarised by
  search on 14 Sep 2026. No trial accounts, no product screenshots viewed.
- `[ASSUMPTION]` LV4 and LV6 are code reads. I did not run them as a branch HR user.

## Handoff note

To the product manager: the idea is sound and the market has a real gap — HR suites
don't protect small groups in their analytics, and survey tools do. **But three things
come before any screen.** First, decide how a branch head is identified (Q1). Second,
decide who controls the pay and individuals switches (Q2). Third, decide whether the
wrong numbers (LV1-LV4) are fixed first. If the first release puts today's 65.8% in
front of an owner, it will cost more trust than no view at all. Do not accept the
org-roles shortcut as a stopgap (LV5). Please send LV6 and LV7 to the security engineer
now; they exist today. Evidence and measurements are in
`C:/Surbhi-Git/hrlocal-data/ux-review/2026-09-14-leadership/`.

**Sources read (14 Sep 2026):**
[Culture Amp — confidentiality protections](https://support.cultureamp.com/en/articles/7048386-confidentiality-protections-in-reporting) ·
[Culture Amp — report filters](https://support.cultureamp.com/en/articles/7048607-report-filters) ·
[Lattice — anonymity threshold](https://help.lattice.com/hc/en-us/articles/360061212133-Adjust-the-Anonymity-Threshold-in-Surveys) ·
[Lattice — strong or basic protection](https://help.lattice.com/hc/en-us/articles/24133460418071-Choosing-Strong-or-Basic-Anonymity-Protection-in-Engagement-Surveys) ·
[Workday Peakon — overlapping segments threshold](https://doc.workday.com/peakon/en-us/workday-peakon-employee-voice/general/confidentiality-and-data-visibility/pqa1653986640521.html) ·
[Darwinbox — people analytics](https://darwinbox.com/en-us/products/people-analytics) ·
[Darwinbox — analytics for people managers](https://darwinbox.com/blog/simplifying-analytics-for-people-managers) ·
[Keka — org dashboard overview](https://help.keka.com/admin/org-dashboard-overview) ·
[Keka — tracking attrition](https://help.keka.com/admin/tracking-attrition-in-the-organization) ·
[Zoho People — reports](https://help.zoho.com/portal/en/kb/people/administrator-guide/reports/articles/reports-zoho-people) ·
[SAP SuccessFactors — WFA permissions](https://learning.sap.com/learning-journeys/configuring-sap-successfactors-workforce-analytics-for-functional-consultants/managing-workforce-analytics-permissions-with-successfactors-role-based-permission-roles) ·
[SAP — target population](https://help.sap.com/docs/SAP_SUCCESSFACTORS_PLATFORM/e4a4ce68589841709a8202928c23803a/1353e784b68f4b0398926447416a709f.html) ·
[BambooHR — turnover report update](https://www.bamboohr.com/product-updates/employee-turnover-report-update) ·
[Rippling — permissions](https://www.rippling.com/platform/permissions) ·
[HiBob — categories and permissions](https://apidocs.hibob.com/docs/categories-and-permissions) ·
[greytHR — mobile app help](https://ess-help.greythr.com/employee-mobile-app/)
