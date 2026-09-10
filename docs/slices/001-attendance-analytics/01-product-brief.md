---
slice: 001-attendance-analytics
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-09-09
status: ready
inputs: [conversation 2026-09-09]
supersedes: draft of 2026-09-09 which treated "short leave" as undefined
---

# Attendance analytics: three views, one calculation

## The job, in the user's words

> "Create another attendance analytics dashboard for HR to analyse different
> attendance metrics on the employee self service portal. This should tell who
> are taking maximum short leaves, etc. these analytics can be filtered by
> department, branch, role, manager as well as selected group of individuals.
> If any employee is also a manager having some people reporting to him, he can
> switch between his own and his employees attendance analytics."

## Decisions taken (9 September 2026)

These were open questions in the previous draft. They are now settled and the
rest of this brief is written to them.

| # | Question | Decision |
|---|---|---|
| 1 | What is a "short leave"? | **Not completing the working hours for the day.** The question is who does it *repeatedly*, and whether a pattern can be seen. Leave types are still counted, but they are a different metric |
| 2 | Manager sees direct reports, or everybody beneath them? | **Both.** The manager chooses, from the filter |
| 3 | How do the personas differ? | **Three separate views** — Employee, Manager, Organisation — rather than one screen that behaves differently depending on who opens it |
| 4 | Build it for every tenant, or for PP Jewellers? | **Every tenant.** Nothing here may assume PP Jewellers' data shape |
| 5 | Paid feature or base product? | **Base product.** No entry in the feature registry, no switch. Every tenant gets it |
| 6 | Can HR be scoped to particular departments? | **Not today.** HR and organisation leaders get the same Organisation view. See below |

### Decision 1, in the user's words

> "by short leave i meant to present how many people didn't complete working
> hours. who is doing this frequently. can there be any way to present the
> trends and identifying patterns."

So it is not a leave type and not a late arrival. It is **hours actually worked
against hours expected**, and the interesting part is not the day — it is the
repetition.

**The data supports this completely.** Checked on a live tenant with 403
employees and 22,570 attendance records:

| | |
|---|---|
| Records with a clock-in time | 22,570 of 22,570 |
| Records with a clock-out time | 22,570 of 22,570 |
| Records with working hours calculated | 22,570 of 22,570 |
| Average hours worked | 9.39 |
| Shortest / longest day | 5.19 / 10.26 |
| Scheduled shift | 09:30 – 18:30, nine hours |

Nothing new needs to be captured. Frappe already stores `working_hours` on every
attendance record, and the shift already says what was expected.

### The finding that shapes the whole screen

Counting how many people were ever short is useless:

| Tolerance allowed | Short days | Share of all days |
|---|---|---|
| None | 2,903 | 12.9% |
| 15 minutes | 1,869 | 8.3% |
| 30 minutes | 1,434 | 6.4% |
| 60 minutes | 984 | 4.4% |

At a 30-minute tolerance, **370 of 403 people had at least one short day.**
Almost everybody. A list of "people who were short" is a list of the workforce.

**So the metric is frequency, never occurrence.** The people worth looking at,
on that tenant, are the ones like this:

| Person | Short days | Average hours on those days |
|---|---|---|
| Aarti Dhillon | 20 | 7.98 |
| Isha Thakur | 20 | 7.74 |
| Vikram Yadav | 19 | 7.74 |

Twenty days is a habit. One day is a dentist appointment.

### The tolerance must be a setting

Look again at that table. With no tolerance the answer is 12.9% of all days;
with an hour it is 4.4%. **The same data supports a crisis or a non-event
depending on one number nobody has chosen yet.**

So it is an organisation setting, alongside the cover policy settings that
already exist, with a stated default of **30 minutes**. Whatever a customer
picks, the screen says which tolerance produced the number. A dashboard that
hides the assumption behind its headline is a dashboard that will eventually be
used to justify something it does not support.

### Decision 6: department-scoped HR — the honest answer

The question was whether a large organisation can give each HR person their own
departments. I checked rather than guessed.

**The framework has the mechanism. This product does not use it.**

Frappe has *User Permissions*, which restrict a user to particular values of any
field — including Department. The PP Jewellers seed already creates them, for
Branch and for Employee. So the raw capability is there and works.

But it would not take effect here, for a reason worth writing down because it
will bite the engineer building this:

> `frappe.get_all()` **ignores permissions**. `frappe.get_list()` applies them.
> The two names look interchangeable and are not.

The portal calls `get_all` almost everywhere, and `hr_api.py` alone passes
`ignore_permissions=True` in 76 places. The portal deliberately does its own
scoping instead of leaning on Frappe's. That is a defensible choice — it is
explicit and testable — but it means a User Permission on Department would be
silently ignored by this screen.

**Decision: treat HR and organisation leaders identically.** One Organisation
view, one rule, no per-department carve-up.

Recorded as a future option, not built now: the Organisation view could read
Department and Branch User Permissions for the current user and narrow itself
when any exist. It is a contained change — one filter applied at the top of one
endpoint — and it would serve a large customer without a new feature. It is
worth doing when a customer actually asks. Building it before then means
maintaining a permission path nobody exercises, which is how permission bugs go
unnoticed.

### What decision 4 requires in practice

The screen must stay correct and unembarrassing when a tenant:

- has no branches, or only one — the branch filter hides itself
- has no departments, or no designations set
- has nobody with anybody reporting to them — no Manager view
- has no late-coming rule configured — the time-lost metric hides itself
- has one employee, or four thousand

**A filter with nothing in it must not be drawn.** An empty dropdown is the
clearest possible signal that a product was built for somebody else.

## The pain today

An HR manager who wants to know *who is drifting in this branch* has to open the
Frappe desk, run a report, and read it person by person. The portal's existing
**HR Analytics** panel shows organisation-wide totals — active employees,
attendance rate, pending approvals — with **no filters and no ranking**, so it
cannot answer "who".

A line manager cannot answer it at all without asking HR.

The underlying data is already recorded and already calculated. What is missing
is a way to ask the question.

## The three views

Decision 3, worked out. One screen in the sidebar; the view switches to match
who is looking. Most people only ever see one, and never learn there are others.

### 1 · My attendance — everyone

Their own record. Present days, leave taken by type, late arrivals, time lost,
attendance rate. No filters — it is one person.

Included deliberately, not deferred: an employee should be able to see the same
numbers about themselves that their manager sees about them.

### 2 · My team — anybody with people reporting to them

Appears automatically. No setting, no request to HR.

Filters:
- **Depth** — *My direct reports* · *Everyone under me* (decision 2)
- **Period** — this month, last month, or a range
- **People** — pick specific members of their own team

Shows the team's numbers, each person as a row, and their own row alongside for
comparison. The manager can see their own record next to their team's without
switching views.

### 3 · Organisation — HR, HR User, System Manager

The full instrument.

Filters, all combinable, each hidden when the tenant has no data for it:
- Department · Branch · Designation (the "role" in the request) · Manager
- **People picker** for an ad-hoc group
- Period

Ranked lists, grouped comparisons, and the ability to drill from any group into
the individuals in it.

**Why three views instead of one screen with permissions:** one screen that
quietly shows different things to different people is hard to explain, hard to
test, and hard to reason about when something leaks. Three views have three
plain rules — *yourself*, *your people*, *everyone* — and each can be tested on
its own. It is also honest: a manager can see that an Organisation view exists
and that they do not have it, rather than wondering whether the screen is
broken.

## The metrics

Six, the same six in all three views so nobody has to learn two vocabularies:

1. **Hours shortfall** — days the person did not complete their expected hours,
   as a **rate** (short days over days present) and as **total hours owed**.
   This is the metric the request asked for, and the headline of the screen
2. **Attendance rate** — present days over working days
3. **Leave taken, by type** — every leave type the tenant has defined
4. **Absences** — unplanned, kept separate from approved leave
5. **Late arrivals and early exits** — count and minutes, where a late-coming
   rule is configured
6. **Punctuality** — already calculated by the appraisal scoring code

Metric 1 is expressed two ways on purpose. A rate makes people comparable when
one was present 12 days and another 22. Total hours owed is the honest cost:
twenty days short by an hour is not the same problem as three days short by
four, and a rate alone hides the difference.

Each shows the number, and where more than one person is in view, the group's
middle value so a number has a context.

## Trends and patterns

The second half of the request, and the part that makes this more than a table.

**Five patterns, all computable from data that already exists:**

| Pattern | The question it answers | Why it matters |
|---|---|---|
| **Frequency** | How often, as a share of days worked | Separates a habit from an appointment |
| **Day of the week** | Is it always the same day? | See below — this is the important one |
| **Direction** | Month on month, getting better or worse | A person improving needs no conversation |
| **Runs** | Consecutive short days | A run of five is a life event, not a discipline case |
| **Against the group** | Is this person unusual for their team? | Separates a person from a rota |

### The pattern that changes what you do about it

**Correction to an earlier draft of this brief.** It said Saturday ran about 40%
above Monday on the tenant I checked, and called that a rota problem. That was
wrong. It compared raw *counts* of short days by weekday — and there are simply
more Saturdays and Thursdays worked than Mondays, so the counts were always
going to lean that way. Measured as a rate (short days divided by days worked),
the same tenant runs 5.8% to 6.6% on every weekday. There is no weekday effect
there at all.

The lesson stands, and it is now built into the screen: a count by weekday is
meaningless, so the screen only ever compares rates, and it says nothing when
the rates are level — as they are here.

When a real one does appear, it matters more than anything else on the screen:

**A whole group short on the same weekday is not people deciding to leave early.
It is a rota, a shift definition, or a closing routine that does not match the
roster.** No amount of managing individuals will fix it, and every conversation
held about it with an individual will be unfair.

This is the single most valuable thing this screen can do, and it is what
separates it from every competitor's version: **tell the user whether they are
looking at a person problem or a system problem.**

Concretely, the screen shows a person's shortfall next to their team's median
for the same period, and flags a weekday where the whole group is short. If
everybody in a store is short on Saturday, the screen says so, in words, above
the list of names — rather than presenting seventeen people who all appear to be
individually at fault.

### What we will not build into the patterns

No predictions, no risk scores, no "likely to leave" flags. The screen describes
what happened. Inferring intent from attendance is where this class of product
does real damage, and it is not something we can do responsibly from a clock.

## What we will not do

Competitors — Darwinbox, Keka, greytHR — all ship an attendance analytics
screen. Two things they do that we should deliberately not copy:

- **The shame leaderboard.** A plain "worst offenders" list with a red badge
  damages trust and lets a manager outsource a conversation to a screen. We show
  a person against their own team's median, and the default view is not a
  ranking of names.
- **Penalties from the dashboard.** We already have a late-coming rules module
  that decides deductions against a written policy, with an appeal path. An
  analytics screen that also punished people would be a second, undocumented
  policy. Analytics observes; the rules module decides. **No action buttons on
  this screen.**

## The WOW moment

An HR manager opens **Attendance Insights**, picks *a branch · last month*, and
in about two seconds sees the six numbers, and underneath them the people whose
leave or lateness sits furthest from their team's middle — with the amount, and
what "normal" is for that team. One click on a name gives the day-by-day
pattern, so they can see whether it is every Monday or one bad fortnight.

The moment is not the chart. It is that **a question that took a spreadsheet now
takes two clicks**, and the answer arrives with enough context that the next
step is a conversation rather than a penalty.

## The thin slice

One screen, three views, one endpoint, six metrics, the filters above.

**Out of scope, named so nobody guesses:** CSV or PDF export · scheduled email
digests · period-over-period comparison · shift and hourly heatmaps · predictive
scoring · any link into disciplinary or payroll action · biometric device health
· attendance correction from this screen.

Each is defensible later. None is needed to prove the screen useful.

## Permissions

Attendance is personal data about a named person, and this screen makes it easy
to read in bulk. Under the DPDP Act that raises the stakes above a normal
report.

| View | Who gets it | Sees |
|---|---|---|
| My attendance | Everyone | Themselves |
| My team | Anybody with reports | Themselves and their reporting line, to the chosen depth |
| Organisation | HR Manager, HR User, System Manager | Everyone in the company |

Three rules, all enforced in the **endpoint**, never in the page:

1. **The people picker only offers people the viewer may already see.**
   Otherwise it becomes a way to read anybody's record by typing their name.
2. **Filtering by manager never widens anything.** Choosing another manager's
   name returns their team only if the viewer could already reach that team.
3. **Refusals are explicit.** If a request names somebody out of reach, refuse
   the whole request and say so — do not quietly return the subset they may see.
   A silent subset teaches nobody where the boundary is and hides a permission
   bug for months.

We learned rule 3 the hard way on the org chart: a limit written in JavaScript
is a suggestion, because the endpoint is open to anyone who can load the portal.

For the "everyone under me" depth, reuse `alvoraa_org_structure.api.reach()`,
which already answers how far somebody may see. One answer in the product, not
two.

## Success measures

| Measure | Baseline | Target | How we will know |
|---|---|---|---|
| HR uses it instead of the desk | 0 — does not exist | Opened weekly by every HR user in month one | Page views per user |
| Time to answer "who is drifting in branch X" | Spreadsheet export, minutes | Under 30 seconds | Timed with an HR user, before and after |
| Managers using the team view | 0 | A quarter of managers with reports, in month one | Distinct users |
| Fast enough to trust | — | Under 2 seconds for 400 employees over a month | Timed on the largest tenant available |
| Works on a bare tenant | — | No empty filters, no broken metrics, on a tenant with one department and no branches | A deliberately minimal test site |

The last one is decision 4 made testable.

If HR opens it once and never returns, the screen has failed however correct the
numbers are.

## Thriving-workplace check

- **Engagement** — Positive if it prompts an early conversation, negative if it
  becomes a stick. The median comparison, and no name ranking by default, push
  it toward the first.
- **Collaboration** — Gives managers something they currently have to ask HR
  for, removing a queue and a dependency.
- **Inclusiveness** — Real risk. Somebody with a caring responsibility or a
  disability may show a pattern that looks like drift. The late-rules module
  already supports exempt grades; this screen must **show** when an exemption
  applies rather than quietly dropping the person, and must never present a
  pattern as a verdict.
- **Transparency** — The employee view is in the thin slice, not deferred,
  precisely so people can see what is said about them.

## Risks and kill criteria

| Risk | What we do about it |
|---|---|
| It becomes a surveillance tool | No default name ranking · medians for context · exemptions shown · no action buttons |
| Numbers disagree with payroll | Reuse `attendance_numbers()` and the late-rules violations. Two calculations of one thing will diverge, and then neither is believed |
| Slow on a large tenant | `numbers_for_many()` is already a batch call. Budget one query per metric, never one per employee |
| Looks broken on a small tenant | Hide any filter with no data. Test on a deliberately bare site, not only on PP Jewellers |
| Three views become three code paths | One calculation, one endpoint. The view decides the population, not the arithmetic |

**Kill this slice if:** the intent turns to automatic penalties or a
disciplinary workflow. That belongs in the late-coming rules module, which
already exists and has a policy and an appeal path behind it. A second route to
the same outcome without those safeguards is worse than nothing.

## What already exists and should be reused

- `hrms.alvoraa_hr_core.attendance_score.attendance_numbers(employee, from, to)`
  — present, half, absent and leave days, late days, punctuality
- `...attendance_score.numbers_for_many(employees, from, to)` — the batch
  version, and the backbone of this screen
- `hrms.alvoraa_late_rules.late_rules.violations_for(...)` — late arrivals and
  early exits with minutes, stored as `Attendance Deduction Violation`
- `hrms.alvoraa_org_structure.api.reach()` — how far somebody may see

The slice is thin because the arithmetic is done. What is missing is the
question and the screen.

---

## Open questions

1. None outstanding. Every question from the 9 September review is answered
   and recorded in the decisions table above.

   One recommendation carried forward for the spec to adopt or reject: make the
   **roles that get the Organisation view a setting**, defaulting to HR Manager,
   HR User and System Manager, exactly as the org chart does. A customer can
   then add their own leadership role without us shipping code, which is the
   cheapest possible answer to "our directors need this too".

## Assumptions

- `[ASSUMPTION]` "Role" in the request means the Designation field, not a Frappe
  permission role. Designation is what the org chart and other filters use.
- `[ASSUMPTION]` Live data, read on request. No stored snapshot — a stored count
  drifts, and a confidently wrong dashboard is worse than none.
- `[ASSUMPTION]` One company at a time. Multi-company comparison is a CXO
  feature and not in this slice.
- `[ASSUMPTION]` Where a tenant has no late-coming rule, metrics 4 and 5 are
  hidden rather than shown as zero. Zero reads as "nobody is ever late", which
  is a lie.

## Handoff note

To the business analyst: the metrics are arithmetic over data that already
exists and is already tested. **Spend your attention on two other things.**

Before either, one trap, spelled out because it is the most likely way this
screen leaks data: **`frappe.get_all()` ignores permissions and
`frappe.get_list()` applies them.** The names are nearly identical and the
behaviour is opposite. The portal uses `get_all` almost everywhere and does its
own scoping on top. That is fine as long as the scoping is actually there — but
it means a missing scope check fails **open**, returning everybody, rather than
failing closed. Specify the scoping as an explicit step that happens before any
query, and specify a test that a manager calling the Organisation endpoint
directly gets a refusal.

First, the permission model. It is new, it is bulk personal data, and the people
picker is the component most likely to leak — it takes a list of names from the
browser and returns records. Specify explicitly that a name out of reach fails
the whole request loudly.

Second, the empty states. Decision 4 says this is for every tenant, and the
difference between a product that feels built for you and one that does not is
almost entirely what happens when the data is thin. Specify, for each filter and
each metric, what appears when a tenant has none of that thing. "Hidden" and
"shown as zero" are different answers and the spec must say which, every time.

The three views are a simplification, not three features. One endpoint, one
calculation; the view chooses the population. If the spec starts describing
three different sets of numbers, it has gone wrong.
