---
slice: 060-manager-applies-on-behalf
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-10-15
status: draft
inputs: [Surbhi's requirement, refinement, decision and final scope of 15 Oct 2026 (all verbatim, §1), the DTC reports_to exercise of 15 Oct 2026, the security engineer's document-level findings (15 Oct 2026, referenced not re-specified), alvoraa_portal/attendance_correction.py, alvoraa_portal/hr_api.py, alvoraa_portal/hooks.py, hrms Leave Application controller and HR Settings, deploy/Dockerfile, .claude/context/product-context.md, .claude/context/security-compliance-baseline.md]
---

# A reporting manager can apply on their team's behalf — attendance correction inside two working days, and leave with notice

*Folder name kept as `060-manager-records-attendance` so existing links do not break.*

## Read this first — six things

**1. Most of this is purely additive — but one new part is not, and I am carving it out
honestly rather than quietly.**

*Additive:* the employee's own path stays exactly as it is, HR's paths stay, the branch head
stays the leave approver for leave the employee files. We add one more person who may apply —
the reporting manager — "in addition to the employees themselves". No reconfiguration, no
migration, and **nothing about this afternoon's leave-approver work reverses.**

*Not additive:* the new **leave notice rule** (item 5). It is off unless a tenant switches it
on, so no existing tenant changes — but on the day DTC switches it on, **it changes how leave
works for all 363 people, not just managers acting on behalf.** That is my reading of her
words and it is marked as an assumption; if she meant it to bind only the manager path, say so
and it shrinks back to additive.

**2. The rule lives on the document, not in a portal endpoint.** Both doors are in scope —
Frappe HR's desk and the self-service portal — so the permission rule has to sit where every
door passes. `hooks.py` already states that idiom twice in its own comments ("Refused on the
document, so the desk, the REST API and imports all obey it"), and this slice follows it:
one rule on the document, and the portal endpoint becomes a **thin caller** rather than the
place the rule lives. A rule written in the portal would be a rule the desk does not have.

**3. The attendance window is two whole WORKING days, configurable per tenant.** Not 48 clock
hours — "hours" was never her word. Working days, default 2, counted on the employee's own
holiday list.

**This answers the Monday-morning case cleanly.** A manager coming in on Monday still reaches
the previous Friday, because the weekend does not consume the window. Under 48 clock hours it
would not have, and that was the one thing I had flagged as unresolved. It is resolved, and
the clock-hours assumption is deleted rather than left open.

**The counter already exists and must be reused, not rewritten.** `hr_may_act_from`
(`attendance_correction.py:890–936`) already counts working days on the **employee's own**
holiday list, and falls back to calendar days when a store has no list — reporting which basis
it used through its `basis` return instead of pretending. Same file, same module. The spec
points the engineer at it; nobody writes a second working-day counter. The safety cap inside it
becomes a working-day cap rather than 31 calendar days.

**4. A working-day window still needs the paid-period guard, so the guard stays in scope.**
Two working days from the 2nd of a month reaches into the previous month, and that month's
payroll runs in those same first days. So: a manager may not file for a day already covered by
a submitted salary slip. `Leave Application` has this natively
(`validate_salary_processed_days`); `Attendance Request` **does not**, so the attendance half
needs it built. Small, right whatever the window is, and **not optional.** HR's own path stays
unbounded and is the escape hatch for a genuine older case.

**5. New in this pass: an optional leave notice rule.** A tenant may require notice before
leave — 1 day of leave asked at least 2 days ahead, more than 1 day asked at least a week
ahead. **Off unless configured**, so no existing tenant is touched. **There is no native Frappe
rule for this** — `Leave Type.applicable_after` is "Allow Leave Application After (Calendar
Days)", a tenure gate from the joining date, not advance notice — so this is **new code**, not
configuration. HR's path ignores the rule, and that is the only emergency route (§4).

**And the cost of that choice, which you should read before approving it.** Nobody gives a
week's notice for a fever. With the restriction on, **every sick leave at DTC routes to the two
HR people in head office** — 363 staff across six branches — because the manager who knows the
worker is ill cannot file it. You chose this knowingly over an emergency flag, and it is the
simpler design. It is also a real operational load, and it lands on the same two people who are
already the subject of the top risk in §10: a two-party flow nobody services.

**6. Two inputs this brief should have been built on still do not exist.** There is no
`01a-ux-opportunities.md` and no `07-devops-inputs.md` §1. **Treat this as a draft** — the UX
scan and the DevOps note must still run before the design, and the UX designer has two named
entry points to work with (§4).

### The data this depends on is already in place at DTC

Who a manager may apply for is derived from `reports_to` — the derivation
`attendance_correction._subject` and `decided_as` already use. **It was populated across the
whole of DTC on 15 October 2026 (Confirmed):** support staff to the head of the location they
are deputed at, the branch lines, the named one-offs, the last seven, and the remaining 61
through the organogram exercise — each group assigned by you by name, matching pinned on
machine id rather than the sheet's own employee id, and `DTC employees with Reports To.xlsx`
produced from the result. So this reaches the whole company.

The comment in `attendance_correction.py` saying "most people in a shop have no manager
recorded" was true when written and is **no longer true of DTC**. It is still true of a brand
new tenant on day one, which is why the scope rule must **degrade safely**: a caller with no
recorded reports gets an empty picker and a refusal that explains itself, never a silent
fallback to a wider list.

---

## 1 · The requirement, in your words

> "Now start working on the strategy how a manager can automatically apply and approve
> (at the same time) for the attendance correction as well as leave application on behalf of
> the blue collar or grey collar employees who are not educated enough to use laptops. In DTC
> HR has no role in these two process other than reading this information for making payroll.
> This mechanism should work on employee self service portal."

> "THE HR can do the necessary approvals of leaves and updates of attendance only if needed."

> "ok got it let's get the manager request the changes and the HR to confirm or reject it."

> **"let's keep it as it is. just add a possibility for the reporting manager to apply on
> their employees' behalf for attendance correction, as well as leaves, in addition to the
> employees themselves. This can be done from both, the frappeHR as well as Employee Self
> Service portal. For the employee self service portal it can be done not only from the
> Team's view but also the attendance analytics when the manager is able to see a persons
> individual checkin records. This mechanism only works for the current month."**

> **"A punch missed on the 31st, noticed on the 1st: good point, ok let's keep it a
> customizable window default to 48 hrs. else HR will do the manual adjustments themselves in
> case of some genuine case."**

> **"Two whole working days for the attendance correction."**

> **"leave rules should have an optional setting to make it restrictive for the leave
> application. in case of emergency HRs path ignores the notice rule."**
> — Surbhi, all seven on 15 October 2026 **(Confirmed)**

**The settled shape:** the reporting manager **applies**; the existing approver **confirms or
rejects**. Two parties, both doctypes, both doors.

| | Attendance correction | Leave |
|---|---|---|
| How far back / forward | **Two whole working days back**, configurable per tenant, counted on the employee's own holiday list | **Notice ahead**, optional and off unless switched on: 1 day of leave → 2 days' notice; more than 1 day → a week's notice |
| Who is bound | The manager path only. The employee's own path and HR's are untouched | **Everyone who files a Leave Application**, if my reading is right — see the assumption |
| The emergency route | HR, unbounded | HR, exempt from the notice rule. **No emergency flag, no reason field** |
| Also enforced | A day already covered by a submitted salary slip is refused | Native balance and overlap rules, unchanged |

My earlier one-action recommendation is withdrawn — there is now a second party, so the
argument behind it no longer applies.

### The job to be done

> *"As a branch manager, when I am looking at Ramesh's check-ins and I can see he punched in
> on Tuesday and never punched out, I want to apply for him right there — with the proof
> already attached — so it gets confirmed and his pay is not cut for a day he worked."*

**Persona:** the **line manager** (DTC's five branch heads and the two owners).

- **Employee** — a wrong day, or a day off, gets filed by the person who saw them at work.
  Their own route is untouched. They still cannot see it themselves; §5 is about that.
- **HR Manager / approver** — **this gives them work, and the brief says so.** A queue of
  manager-filed requests to confirm. Small work per request, because the evidence travels with
  it (§6), but new work. §8 measures whether it is serviced.
- **CXO** — nothing in this slice. The owners can already read a branch's month.

---

## 2 · One slice, both halves — and the risk note that survives the merge

Your earlier split (attendance first, leave second) is **overtaken as a scope decision**: you
asked for both in one breath, and both are in this slice. The reasoning behind the split was
not wrong, though, and it survives as a **sequencing and risk note**, which I recommend the
spec and the test plan carry:

| | Attendance correction | Leave |
|---|---|---|
| Document | Attendance Request | Leave Application |
| Effect on pay | Marks an unmarked or wrong day as worked. Pay usually goes **up** | Consumes a balance, or becomes unpaid leave. Pay usually goes **down** |
| Extra work it needs | **The paid-period guard** — `Attendance Request` has no `validate_salary_processed_days`, so it is ours to build. The working-day counter already exists | **The notice rule — entirely new code**, plus the balance preview reusing `preview_leave_request`. The paid-period guard is already native here |
| Who the time rule binds | The manager path only | **Everyone who files leave**, once a tenant switches the rule on `[ASSUMPTION]` |
| If something has to land first | Attendance. It is the daily event and it cannot reduce pay | Leave second, same slice, same mechanism |
| ⚠ Policy question still open | None | §9 — may a manager apply for unpaid leave for a worker who did not ask in writing? |

**Why attendance is still the one to get working first inside the slice:** the check-ins carry
no `log_type`, so punches are counted and an odd count means a lost punch; with
`payroll_based_on = Attendance` and unmarked days treated as Absent, every lost punch is a pay
cut. Leave is weekly, not daily, and it is the direction that can take money away.

---

## 3 · How to build it — the cheapest rung that works

| Rung | Option | Verdict |
|---|---|---|
| 1 — already there | HR files it themselves; `apply_leave(on_behalf_of=...)` and the desk already allow it | **Keep as the exception route**, not the default. Relaying 363 people's missed punches through two HR users is the bottleneck that leaves days unmarked at cut-off |
| 2/3 — configuration | Give branch managers desk access and permission, and call it done | **Half-true now, and worth stating.** The desk *is* in scope, so configuration is part of the answer — but permission alone would let a manager file for anybody in the tenant. The missing piece is the **scope and date rule**, which no setting provides |
| 4 — new code on existing doctypes, **recommended** | A document-level rule — may this caller file for this employee, for this date — plus thin portal callers at the two entry points she named | **Yes.** No new DocType, no new role, no new page, no new status, no new app. The request's existing `Waiting / Approved / Declined / Withdrawn` labels already say everything |

### The pattern question, settled

`attendance_correction.py`'s pattern wins, and the new rule follows it:

| | `attendance_correction.py` | `hr_api.apply_leave(on_behalf_of=...)` |
|---|---|---|
| Who the record is about | Derived server-side from the caller's real relationship | Taken from the request body, gated on a hardcoded role list |
| Permissions | `get_list` / document checks. **No `ignore_permissions` anywhere, deliberately** | `insert(ignore_permissions=True)` + a manual `frappe.db.commit()` |
| Capacity recorded | `alvoraa_decided_as`, derived, never declared, no backfill | Not recorded |

`raise_correction()`'s self-only rule stays exactly as it is — its docstring is right that a
whitelisted endpoint taking an employee name "would let anyone rewrite anyone's attendance".
The new ability is a separate path with its own derivation, and the derivation is on the
document.

**`apply_leave`'s HR on-behalf ability: keep the capability, fix how it is built — but not in
this slice.** It is HR's exception route and it stays. What is wrong is the implementation: the
hardcoded role list instead of the entitlement helpers, `ignore_permissions`, the manual
commit, no capacity recorded. Once the document-level rule exists, that endpoint should be
rebuilt on it so both routes share one mechanism. **Recommendation: its own small ticket, not
this slice** — it is not needed for the manager path to work, and folding it in is scope creep
by our own definition.

---

## 4 · The flow, the doors, and the two controls that are new

**What happens, end to end**

1. The manager picks the day, from one of three places: the **desk** (Frappe HR), the portal's
   **Team view**, or the portal's **attendance analytics** screen where they are looking at one
   person's check-ins.
2. The document-level rule asks four questions: does this employee report to this caller; is
   the day being filed for **inside the filing window** (two working days back, for attendance);
   is that day **not already covered by a submitted salary slip**; and is the caller anyone
   other than the employee themselves. For leave there is a fifth, when the tenant has switched
   it on: **is there enough notice.** Any no is a refusal that explains itself and says where to
   go instead.
3. The request is created against the **employee**, with the manager recorded as the person who
   filed it, left **waiting** — the same state an employee-filed request sits in.
4. The existing approver confirms or rejects. For attendance that is the existing review queue
   (`to_review` / `review_queue_filters`); for leave it is the configured approver, resolved
   **department → branch → company, whoever is set** (your answer; see Open questions, closed).
5. The record ends up saying who filed it, who decided it, when, and in what capacity —
   `alvoraa_decided_as`, derived server-side, never declared.

**Why her second entry point is the better one.** On the attendance analytics screen the
manager is **already looking at the evidence** when they decide to act: the punch strip, the
shift, the hours. That is exactly where "the proof travels with the request" (§6) pays off,
because the facts for the pre-filled grounds are on the screen in front of them. The Team view
is the place they go when they already know what is wrong; analytics is the place they find
out. Both are in scope; if the UX designer has to make one excellent, make it analytics.

**Control 1, new: the person who filed it must not be the person who decides it.** The existing
guard does not cover this — `refuse_own_decision(employee, ...)` tests whether the request is
*about* the caller, not whether they *filed* it for a third party (Confirmed; the security
engineer is writing it up, and I am deliberately not specifying it here). Without it, anyone
holding both the manager relationship and the approval right can file and confirm their own
request, and the two-party design you chose quietly becomes a one-party design.

**Control 2, new: the two-working-day HR wait must not apply to a manager-filed request.**
`hr_may_act_from()` makes an HR caller wait two working days to give the employee's own manager
first refusal (045 D-12). That was written for the world where the manager decided. When the
manager is the one *asking*, there is nobody to wait for, and the window would block exactly
the requests this slice creates. `decide()` already has the shape of this exemption for
employees with no manager; this is a second clause, not a new mechanism.

### Where the two settings live, and the ways to get them wrong

**The app already has the right idiom, so we do not invent one.** An organisation-wide number
stored as a Frappe default and read per request — exactly how
`alvoraa_attendance_short_tolerance_mins` works (`attendance_analytics.py:41–42`, read at line
135 as `frappe.db.get_default(KEY) or DEFAULT`). **Rung 2 of the cost ladder** — no migration,
no new DocType, per tenant, and an existing tenant needs nobody to touch their site.

| Setting | Unit | Unset means | Reuses |
|---|---|---|---|
| `alvoraa_manager_filing_window_days` | **Working days** | 2 | `hr_may_act_from`'s working-day counter |
| The leave notice rule | **Calendar days** (see assumptions) | **Off. No notice required** | Nothing — it is new code |

Three things the spec must state unambiguously:

1. **Working days, not clock hours.** "Two whole working days", counted on the **employee's
   own** holiday list by `hr_may_act_from` (`attendance_correction.py:890–936`) — including its
   honest fallback to calendar days, with the `basis` it returns, when a store has no holiday
   list. The safety cap inside it becomes a working-day cap. Nobody writes a second counter.
   **The Monday case is now answered by construction:** Monday reaches Friday, because the
   weekend is not a working day.
2. **A window of 0 must mean "nobody may file on behalf", not "no limit".** Note the trap: the
   tolerance idiom reads `get_default(KEY) or DEFAULT`, so a stored **0 falls through to the
   default** — deliberate for shift grace (`attendance_analytics.py:54–56`) and exactly wrong
   here, because it would turn "allow nothing" into "allow two days". Read it as "unset → 2;
   set → use it, including 0".
3. **Unset must leave the leave notice rule OFF**, and that is the same trap pointing the other
   way. `get_default(KEY) or DEFAULT` with a default of 2 and 7 would switch the restriction on
   for **every tenant that never asked for it**. The notice rule must be read as "nothing stored
   → no notice required", and a test must pin it.

### The leave notice rule, and why HR is the only emergency route

- **1 day of leave: at least 2 days ahead. More than 1 day: at least a week ahead.** Both
  numbers configurable with the rule; both meaningless until a tenant turns it on.
- **No emergency flag and no emergency reason field on the request.** The exemption is simply
  that HR's path does not apply the rule — the simplest of the options put to you, and the one
  you chose. A flag would have meant a new field, a new word for "emergency", and an argument
  about who may tick it.
- **Who counts as HR comes from the canonical `HR_ROLES`** (`access.py:25`,
  `frozenset({"HR Manager", "HR User"})`), never a new hardcoded list. The security engineer
  found seventeen hand-rolled variants of "who is HR" in `hr_api.py`; this slice does not add an
  eighteenth, in either half.

**On leave approvers: nothing reverses.** The security engineer's document-level `leave_approver`
fix means today's configuration stands as it is. The clash I flagged earlier — branch head as
both filer and approver — is **closed**, and the cost I named (partly undoing this afternoon's
work) is **withdrawn**.

**What the capacity stamp is for.** With more than one legitimate route — the manager path, the
employee's own, and HR's exception — "who did this, in what capacity" is the only way to tell
afterwards which route a record came through, and to **count how often the exception is used**.
Report Builder on that field already does it, with nothing to build.

---

## 5 · What the employee gets

| What | How | In this slice? |
|---|---|---|
| **A record naming both humans** — who filed it, who decided it, in what capacity, when | `owner` + `alvoraa_reviewed_by` / `_on` + `alvoraa_decided_as`, already in the data | **Yes.** This is where the design hangs |
| **To be told by their manager**, in person | Your answer: "they will be informed by their manager" | **Yes, as a process** — and the brief is honest that it is a human promise, not a software one |
| **WhatsApp, where a tenant has it** | `frappe_whatsapp` is genuinely in the production image (`deploy/Dockerfile` 68–76, 193–196, pinned `08bc1f6af2e3`), gated by the `whatsapp` feature in subscription. **Per-tenant availability unverified** | **No, not in this slice.** Named so nobody thinks it was missed; it is the obvious next step once availability is known |
| **A route to contest it** | Tell the manager or HR; HR cancels and Frappe reverses the attendance it wrote. Exists today | **Yes**, written down. No new code |
| **For the few with a login:** their own month says it in words — "Your manager applied for this on 15 Oct. It was confirmed on 16 Oct. The day is marked Present." | `month()` already returns the request per day and its capacity; the screen must print the filer too | **Yes** — small, and the only employee-facing thing we can honestly claim |
| **A printed copy of their month, handed over at the branch** | A Print Format — rung 2, configuration | **Your decision.** I recommend it; it is a process promise, not a software one |
| An "employee informed" checkbox the manager ticks | — | **No, and this is a refusal, not a gap.** Your answer — the manager tells them — does not change the reasoning: a tick box is a claim nobody made, the same mistake `alvoraa_decided_as` avoided by having no default. If we ever want to *prove* the worker was told, the proof has to come from the channel that told them, not from the person who filed the request |
| A branch noticeboard list | — | **No, and never in this shape.** One worker's leave type or reason on a shared list is exactly the privacy trade we refuse |

**The gap, plainly:** for roughly 350 DTC workers this changes their pay and tells them nothing
digital. The honest mitigation is the manager's conversation, the printed month, and WhatsApp
when a tenant has it — plus the fact that an attendance correction moves pay **up**. Leave is
the direction that can take money away, which is why §9 still carries a question.

---

## 6 · The WOW moment — the proof travels with the request

**Screen:** attendance analytics, one person's check-in records — her own second entry point,
and the one where the manager is already holding the evidence.

The manager is looking at Ramesh's October. 14 October shows one punch IN at 09:32 and no OUT.
Under the row, one button and one sentence:

> **Apply for Ramesh — "Forgot to Punch Out"**
> *If this is confirmed, 14 Oct will be marked Present for Ramesh Kumar.*

They tap. The row changes in place:

> **Waiting — applied by you for Ramesh, 15 Oct**

**And here is the WOW, on the approver's side:** the request arrives in the queue they already
use, carrying the facts the manager was looking at, pre-filled into the existing `explanation`
field as one editable sentence:

> *"Applied by Vaneet Garg (reporting manager). Punched in 09:32, no out punch recorded. Shift
> 09:30–18:30. Day currently unmarked."*

It is confirmed in one look, without a phone call to the branch. Both sides get the moment: the
manager applies in one tap from the screen they were already reading, and the approver gets a
request that explains itself instead of an empty text box.

**(Recommendation. The exact words, and whether the sentence stays editable, are the UX
designer's to settle in `01b`. The field already exists.)**

---

## 7 · The thin slice

**One outcome:** a reporting manager applies, for someone on their team, for a correction
within two working days or a leave with the required notice, from the desk or from either
portal entry point — and the existing approver confirms it from the queue they already use.

**In**

1. The document-level rule: reports-to scope, the filing window, the paid-period guard, and
   "not for yourself through this path". On both doctypes. One rule, every door — desk, REST,
   import, portal.
2. **The paid-period guard.** A manager may not file for a day already covered by a submitted
   salary slip. `Leave Application` has it natively (`validate_salary_processed_days`);
   `Attendance Request` does not, so the attendance half needs it built. Small, right whatever
   the window is, and the thing that stops two working days from the 2nd of a month rewriting a
   month that has already been paid.
3. The attendance window setting: `alvoraa_manager_filing_window_days`, **working days**,
   default 2, stored and read the way the tolerance already is, counted by `hr_may_act_from`;
   0 means nobody may file on behalf.
3a. **The leave notice rule — new code.** Optional, off unless configured; 1 day → 2 days'
   notice, more than 1 day → a week; HR exempt via `HR_ROLES`; enforced on the document so the
   desk obeys it too. Frappe has no native equivalent (`Leave Type.applicable_after` is a tenure
   gate from the joining date, not notice), so nothing cheaper exists.
4. Thin portal callers at both entry points she named: Team view, and attendance analytics for
   one person's check-ins.
5. The desk works by the same rule, with no portal code involved.
6. The filer is recorded, and **the filer may not be the decider** (control 1 — security
   engineer's to specify).
7. The two-working-day HR wait does not apply to a manager-filed request (control 2).
8. For leave: the balance preview reusing `preview_leave_request`, so a manager cannot apply
   for a balance that is not there.
9. The confirm line states what is being asked and what happens if it is agreed. A half-day
   request can lower a day, so the manager sees the outcome, not the form.
10. **Three refusals that say where to go instead**, because all three will be met often: out of
    window ("this day is more than two working days old — ask HR"), already paid ("this day is
    in a month that has been paid; HR can still adjust it"), and not enough notice ("a day of
    leave needs two days' notice — for an emergency, ask HR"). **The third is the one most
    people will meet, and the one whose words matter most**, because it is the sentence an ill
    worker's manager reads.
11. The employee's own month screen prints who filed it as well as who decided it.
12. Empty scope degrades safely: empty picker, explained refusal, never a wider list.
13. A reader can count manager-filed versus HR-filed, and how long requests wait — Report
    Builder on fields that already exist. Nothing to build, but written down so somebody looks.

**Needed before it ships (not before we validate):** Hindi strings; the accessibility pass; the
`07` §5 release plan.

**Worth doing later:** rebuilding `apply_leave`'s HR on-behalf path on the document-level rule
(its own ticket); the printed month Print Format; WhatsApp to the employee once per-tenant
availability is known; bulk apply for a branch-closed day, if the data ever shows one manager
filing the same date for three or more people.

**Not doing**

- **No back-dating role setting.** Frappe's `restrict_backdated_leave_application` and
  `role_allowed_to_create_backdated_leave_application` are Leave-Application-only and are about
  *roles*, not a time window. The window plus the paid-period guard is the whole date defence.
- Nothing older than the window, for a manager, through this path. HR's existing routes reach
  those days — which is exactly what Surbhi said should happen for a genuine case — and ATT-07's
  reprocess still exists for a period that needs re-running.
- **No emergency flag, no emergency reason field, no "override" button on the notice rule.** HR
  is the emergency route, full stop.
- **No second working-day counter.** `hr_may_act_from` is the one, holiday-list fallback and all.
- **No eighteenth definition of "who is HR".** `HR_ROLES` from `access.py:25`.
- No new role, DocType, page, inbox or status. **Two settings**, both Frappe defaults read per
  request, not a settings page.
- No bulk action.
- No reminder or escalation machinery for requests nobody has decided. **If §8 shows a queue
  sitting unserviced, that is the next conversation, not a pre-emptive build.**
- No pay figure on screen. We say "unmarked days are paid as absent"; we do not compute a rupee
  amount, because a wrong number here is worse than none.
- No change to the employee's path, HR's paths, or the leave-approver configuration.
- No "employee informed" flag (§5).
- No special case for the 44 agency staff on Contract. Same rule; the policy check is below.

---

## 8 · Success criteria

| Measure | Baseline | Target | How it is instrumented |
|---|---|---|---|
| **Share of corrections and leaves filed by the reporting manager** | 0 today — the path does not exist. Count employee-filed and HR-filed for Sep–Oct 2026 first | ≥ 80% of DTC's corrections, and a rising share of leaves, in the first full month after go-live | Attendance Request and Leave Application by filer and relationship |
| **How long a request waits to be decided** *(the measure the two-party shape makes essential)* | **No baseline — this flow does not exist.** For reference, measure today's employee-filed waits | Median decided **within one working day**, and **zero** manager-filed requests still waiting at the payroll cut-off | `creation` → decision timestamp; plus a count of waiting requests on cut-off day |
| **Unmarked days at payroll cut-off** *(the money metric)* | **baseline unknown — measure first**, per branch, from the `no_record` count the screen already computes | A real reduction, the number agreed once the baseline exists. I will not invent one | Same count, on the cut-off date |
| **How often HR's exception route is used** | Everything is HR or self today | HR-filed stays a minority and keeps falling. If most records are still HR-filed after three months, the manager path did not take, and we say so | Count by capacity and filer, per month and per branch |
| **Quality — five counts that must stay 0** | 0 today | **0**: records with no capacity; manager-filed requests accepted outside the window; requests accepted for a day already covered by a submitted salary slip; requests decided by their own filer; **leave accepted without notice on a tenant that switched the rule on, or refused for notice on a tenant that did not** | Each is a test of a control in §7 |
| **How often a time rule is the thing that stops somebody** | None — new | Watch both for the first two months. A high out-of-window count means two working days is too short for how DTC works; a high no-notice count means the notice rule is pushing work to HR. Both are settings, not rebuilds | Count the refusals, split by reason. **The cheapest evidence we will ever get for whether the defaults are right** |
| **Share of leave filed by HR after the notice rule is switched on** *(the cost of the emergency route)* | Measure for a month **before** switching the rule on | If HR's share of leave jumps and stays up, the notice rule moved the work to head office rather than improving planning — and that is a conversation about the rule, not about the software | Leave Application by filer, before and after the switch |

No AI in this slice, so no acceptance or override rate. Logins and page views are not measures.

---

## 9 · Thriving-workplace check, and the regulatory read

| Lens | Answer |
|---|---|
| **Engagement** | A wrong day is filed in the week it happened by the person who saw the work. **Honestly: the fix is not immediate** — it depends on the approver servicing a queue, which is why the waiting measure is not optional. |
| **Collaboration** | The strongest lens here. The manager's knowledge reaches the approver as a request that explains itself, and the confirmation closes it. Two people, one record, no phone call. |
| **Inclusiveness** | The point of the slice: no laptop, no literacy, no device needed, because the manager is the interface. The gap: the worker still cannot check it themselves (§5). |
| **Transparency** | It makes visible *who filed* a change to a person's day, *who decided it*, and *in what capacity* — nothing recorded that before. Safe for the least powerful person, because it names the powerful ones. Refused: any branch list showing one worker's leave type or reason. |

**Regulatory read**

1. **Regime:** DPDP 2023 — accuracy and correction, purpose limitation, grievance redressal. No
   AI Act exposure: nothing is automated, and two named humans are in the loop.
2. **Whose duty:** the **employer's** (DTC). We build the thing that helps them discharge it — a
   correction path their non-literate workforce can actually reach, with an audit trail. That is
   the version that survives a security review.
3. **What is newly possible:** one employee can file a record about another that changes that
   person's pay, and a second employee can make it real. A new write path and a new visibility —
   a compliance event, which the security engineer turns into `SEC`/`PRIV` requirements, including
   the filer-is-not-decider control.
4. **The honest downside:** "a manager applies within two working days, the approver confirms,
   the record names both, and nothing already paid can be touched" is a headline we defend
   comfortably. The notice rule is the part to watch: a rule that sends every ill worker's leave
   to head office is defensible as policy, but it is the employer's policy choice, not something
   the product should impose — which is exactly why it is **off unless a tenant switches it on.** ⚠ **COMPLIANCE, and I am not a
   lawyer:** *may a manager apply for leave — including unpaid leave — for a worker who did not
   ask in writing and will be told only in conversation?* **Owner: Surbhi, with DTC's HR owner
   (raj.kumar@ / rama.pandey@).** It does not block the attendance half. For the leave half it
   decides whether the spec needs anything more than the record and the conversation.

---

## 10 · Risks, red-teamed

| Risk | What happens | Cheapest way to find out first |
|---|---|---|
| **A two-party flow nobody services** | **The top risk.** If 363 staff generate hundreds of monthly requests and nobody decides them before cut-off, the worker's pay is still wrong *and* we added work. Worse than today for everyone | Count missing-punch days for one branch in September and multiply. One read, no code. It gives the approvers' monthly load before we ship |
| **Every sick leave routes to two people in head office** | **The cost of the notice rule, and it compounds the risk above.** Nobody gives a week's notice for a fever, so with the rule on, the branch manager who knows the worker is ill cannot file it and HR must. 363 staff, six branches, two HR people. **A deliberate trade — the emergency route is HR, not a flag — but it is a real operational load, and the people carrying it are the same two already carrying the top risk** | Count DTC's sick and casual leaves filed with less than two days' notice over the last three months. It is the volume that would land on HR, and it is one read |
| **The window reaches into a month that has already been paid** | **Back on the list, and this is the cost of a rolling window.** On the 2nd, two working days reaches into the previous month, and a month's payroll runs in the first days of the next. Without a guard a manager could rewrite a paid day. `Leave Application` refuses natively (`validate_salary_processed_days`); `Attendance Request` **does not** — so the attendance half needs it built. Not optional | §7 item 2, with a test named after it. There is nothing to investigate: the guard either exists in the diff or the slice is not done |
| A day older than the window | The manager cannot file it and must ask HR — which is exactly what Surbhi chose, and HR's path is unbounded. The refusal must say so in words, not just refuse | §7 item 10. Watch the refusal count (§8) to learn whether two working days is the right default |
| **The rule gets written in the portal** | The desk and the REST API would not have it, and the slice would half-work through the door she named first | It is a review item: the rule is on the document or the slice is not done |
| **The filer is also the decider** | An owner, or anyone holding both the relationship and the approval right, files and confirms their own request. The two-party design collapses | Control 1 and its negative test. The guard that exists today does **not** cover it |
| **The two-working-day HR wait blocks the design** | HR cannot decide a manager-filed correction for two working days | Control 2. Found by reading `decide()` and `hr_may_act_from()` |
| Manager applies for a half-day, or for leave, and lowers the pay | The worker is docked by the person meant to protect them | §7 items 8 and 9 — the balance preview, and the outcome stated before the tap |
| **The window is read with `or DEFAULT` and a zero becomes two days** | A tenant that set the window to 0 to switch on-behalf filing off would find it fully on. The tolerance idiom falls through deliberately; this setting must not | One test with the value stored as 0. Named in §4 |
| **The notice rule switches itself on everywhere** | The same storage trap pointing the other way: an unset value falling through to "2 and 7" would impose notice on **every tenant that never asked for it** — a silent change to how leave works for people who are not DTC | One test on a tenant with nothing stored: leave filed for tomorrow must be accepted |
| **The notice rule binds more people than she meant** | My reading is that it binds every Leave Application, not only the manager path. If that is wrong, we will have restricted 363 people instead of five managers | **Assumption 1 below. One sentence from Surbhi settles it, and it is worth asking before the spec** |
| False days for friends | Payroll fraud — now with a second pair of eyes, which is what the two-party shape buys | Visible in Report Builder by filer and decider. A monthly count per manager is a financial control over accountable decision-makers, not monitoring of a worker |
| **A brand new tenant has no `reports_to`** | The scope rule must return nobody and refuse clearly. Not a DTC risk; it is the day-one state of every future tenant | One test: empty scope → empty picker → explained refusal |
| `reports_to` changes, or the manager leaves, after the record | The record must keep saying who filed and who decided | Already solved: the capacity is stored, not re-derived at read time |
| Employee leaves mid-flow | Frappe's `validate_active_employee` refuses. Confirmed in the controller | — |
| 10x volume — a manager with 80 reports | `_reports_to(deep=True)` plus a month of punches per employee | DevOps `07` §1/§3 to put a query count on it |
| **Support tickets this will create** | "I applied three days ago and nothing happened" (the waiting risk), "Why can't I see my staff?" (scope), "Why can't I fix Tuesday?" (the window), "It was confirmed and his pay is still wrong" (059 reprocess not run) | Every refusal names the person or the reason, in this module's existing voice |

**The two trades on this page, stated once.** *(a)* Two working days instead of current-month
costs us the paid-period guard and buys back the month-boundary case that would have gone to HR
every month for every branch — a recurring tax traded for a guard written and tested once. I
would make that trade again. *(b)* HR-as-the-only-emergency-route instead of an emergency flag
costs HR every unplanned sick leave and buys a design with no new field, no new word for
"emergency" and no argument about who may tick it. **That one I would want the volume number
beside before switching the rule on at DTC** — it is one read, and it is in the risk table.

---

## Open questions

**Closed by your answers of 15 Oct 2026**

| Was | Your answer | What it settles |
|---|---|---|
| Which HR user confirms a manager-filed leave, and what happens when they are away | "HR of their department > branch > company whoever is set" | A **resolution order, not a person**. The backup worry I raised is answered by construction: if the department has nobody, it falls to the branch, then the company. Nothing to build and nobody to name |
| Does DTC's leave-approver configuration have to change | No — the security engineer's document-level `leave_approver` fix covers it | **Nothing reverses.** This afternoon's work stands, and the cost I named is withdrawn |
| How the employee is told | "they will be informed by their manager or if there is any whatsapp integration then that would go" | A human conversation now, WhatsApp where a tenant has it. `frappe_whatsapp` is in the production image, gated by the `whatsapp` subscription feature; **per-tenant availability unverified**, so it is named as the next step, not scoped |
| How far back a manager may file | "a customizable window… else HR will do the manual adjustments themselves in case of some genuine case", then **"Two whole working days for the attendance correction"** | A per-tenant window in **working days**, default 2, counted by `hr_may_act_from` on the employee's own holiday list. HR unbounded as the escape hatch. **My 48-clock-hours assumption is resolved and deleted** — and the Monday-morning case is answered by construction, because a weekend is not a working day |
| Whether the paid-period guard exists on Attendance Request | It does not | **So we build it.** `Leave Application` has it natively; the attendance half does not. Two working days from the 2nd reaches into the previous month, so this is not optional |
| Whether notice can be required before leave | "leave rules should have an optional setting to make it restrictive for the leave application. in case of emergency HRs path ignores the notice rule" | **New scope, and new code** — Frappe has no native advance-notice rule. Optional and off unless configured; 1 day → 2 days' notice, more than 1 day → a week; **HR's path is the only emergency route**, so no flag and no reason field |
| `reports_to` coverage | Populated across DTC on 15 Oct | Reaches the whole company |

**Still open**

| # | Question | Owner | Blocks | My recommendation |
|---|---|---|---|---|
| 1 | **Must know, and it is one sentence.** Does the leave notice rule bind **every** Leave Application, or only a manager filing on behalf? I have read it as every one, which means it changes leave for all 363 DTC people the day it is switched on | Surbhi | The leave half of the spec. The attendance half is unaffected | Bind the document — it is what "for the leave application" says — but **do not switch it on at DTC until the volume in §10 has been counted** |
| 2 | **Should know.** Who owns the queue, per branch, and do they know it is coming — including every emergency leave once the notice rule is on? The flow only works if somebody services it within a working day | Surbhi + DTC HR | Nothing on day one. It decides whether §8's waiting target is realistic | Name one person per branch's requests, not "HR" |
| 3 | **Should know.** Do the 44 agency staff on Contract fall under their branch head here too, or should a manager not file for outsourced staff? A policy question, not a data one | Surbhi + DTC HR | Whether 44 people are in or out | In, same rule, no special case |
| 4 | **Should know.** Do we promise the printed month handed over at the branch? Configuration, but a promise managers have to keep | Surbhi | Whether §5 can claim the worker is told | Build the record and the on-screen line; offer the print, promise nothing |
| 5 | **Nice to know.** One read for the exact count: how many of the 363 active staff have `reports_to` pointing at a head who has a login | anyone with production read access | Nothing. It sizes the rollout and gives §8 its denominator | Everyone bar a handful of named exceptions |
| 6 | **Nice to know.** The seven Kano answers from the branch heads and owners, to turn the proxies into evidence | Surbhi | Nothing | Ship on the proxy; it is a Must-be either way |

## Assumptions

- `[ASSUMPTION]` **The most important one: the leave notice rule binds every Leave Application,
  not only a manager filing on behalf.** Your words were "for the leave application", so I read
  it as the document's rule. If you meant it to bind only the manager path, say so — it is a
  smaller change and it keeps the whole slice additive. **This is the one sentence I would most
  like answered before the spec is written.**
- `[ASSUMPTION]` The notice is counted in **calendar** days — "a week" is 7 days, not 5 working
  days — measured from the day of filing to the first day of leave. The attendance window is
  **working** days, because that is what she said. The two units differ on purpose, and the spec
  must say so in one line so nobody "tidies" them into one.
- `[ASSUMPTION]` The attendance window applies to the **day being filed for**, not to when the
  punch was recorded.
- `[ASSUMPTION]` DTC's branch managers will mostly use the portal on a phone; the desk route
  matters for HR, the owners and future tenants. The rule is the same either way.
- `[ASSUMPTION]` The branch managers do **not** hold the approval right on Attendance Request, so
  they cannot decide what they file. The two owners may. That is what makes control 1
  load-bearing rather than belt-and-braces.
- `[ASSUMPTION]` `payroll_based_on = Attendance` with unmarked = Absent is live for DTC as
  described, so an unmarked day really is a pay cut today.
- `[ASSUMPTION]` The capacity values `Manager` / `HR` already on the field are enough to tell the
  routes apart. A reviewer who is neither gets "not recorded", as today.
- `[ASSUMPTION]` Every branch head named in the 15 Oct exercise has a working login.
- `[ASSUMPTION]` No other tenant wants this on in the next quarter. The window setting doubles as
  the off switch — 0 means nobody may file on behalf — so no separate toggle is needed, and the
  notice rule is off until somebody configures it.
- `[ASSUMPTION]` The notice numbers (2 days and a week) are configurable with the rule rather
  than hard-coded. If you would rather they were fixed, that is less code, not more.

## Kill criteria

Stop, and do not build, if any of these is true:

1. The approvers cannot commit to deciding these requests within the payroll period. A
   two-party flow with an unserviced queue leaves the pay wrong *and* adds work.
2. A branch manager, shown the one-tap-to-apply idea, says they would rather telephone HR. Then
   the bottleneck is not the software.
3. The rule cannot be made to sit on the document, so the desk and the portal would behave
   differently. Then we are building two features, not one.
4. The paid-period guard cannot be built on Attendance Request. Two working days from the 2nd
   reaches into the previous month, and without the guard a manager could rewrite a paid day.
   Then the bound goes back to "current month only" and the month-boundary case goes to HR.
5. HR tells us they cannot absorb every emergency leave for 363 people across six branches.
   Then the notice rule is not ready to switch on at DTC — **the slice still ships, with the
   rule off**, and the question goes back to Surbhi with the volume number beside it.
6. The first month shows requests confirmed for days a worker did not work. The second pair of
   eyes failed, and no audit trail fixes a wrong number in payroll.
7. Three months in, most requests are still filed by HR. The manager path did not take; stop
   extending it rather than adding screens to it.

## Handoff note — to the UX designer and DevOps, who both go before me

You two were skipped and should not have been. **Read this brief as a proposal, not a
constraint.** Four things to push back on: whether attendance analytics really is the better
entry point and deserves the polish (§4 argues it is, because the manager is already holding the
evidence); whether the pre-filled grounds sentence in §6 is the right WOW and is safe to leave
editable; **what the three refusals should say** — out of window, already paid, and not enough
notice — because "no" is not enough, and **the notice one is the sentence a manager reads when
their worker is ill, so it has to point at HR kindly and in Hindi too**; and whether the
employee-facing line in §5 is enough to call this fair. **DevOps:** the three numbers I most
want in your §1 are the query cost of a manager with 80 reports opening a month, the approvers'
likely monthly decision volume if every missing punch becomes a request, and what the notice
rule would add to that volume — the last two are the top two risks in §10.

**Revision note — this brief was rewritten five times on 15 Oct 2026.**

1. An early warning that this "may reach almost nobody" was **wrong** and is gone: `reports_to`
   was populated across DTC that afternoon.
2. "HR can do the necessary approvals only if needed" made HR an exception route rather than a
   removed one; `apply_leave`'s on-behalf ability **stays**, with its implementation rebuilt on
   its own ticket.
3. The shape became **two parties** — manager applies, the approver confirms — on your decision.
   My one-action recommendation is withdrawn.
4. The scope **merged the two slices into one** (both doctypes), **added the desk** (so the rule
   lives on the document and the portal endpoint is a thin caller), and **named two portal entry
   points**. Three open questions closed by your answers, and the leave-approver cost I named is
   withdrawn.
5. **The time bound moved from "current month only" to a window**, which brought the
   paid-period guard **back into scope and made it non-optional**: the window reaches into the
   previous month early in a month, and that month's payroll runs in those same first days. The
   "quiet win" credit for current-month-only is gone, and so is the not-doing line that said no
   salary-slip guard was needed — it was wrong the moment the window changed.
6. **The window became two whole WORKING days, not 48 clock hours**, and the setting's name
   changed with its unit (`alvoraa_manager_filing_window_days`). It reuses `hr_may_act_from`'s
   existing counter on the employee's own holiday list rather than a second one, and it
   **answers the Monday-morning case by construction** — Monday reaches Friday, because a
   weekend is not a working day. My 48-clock-hours assumption is resolved and deleted.
7. **New scope: an optional leave notice rule** — 1 day of leave needs 2 days' notice, more than
   1 day needs a week; off unless a tenant switches it on; **new code, because Frappe has no
   native equivalent** (`Leave Type.applicable_after` is a tenure gate, not notice); **HR's path
   is the only emergency route**, so no flag and no reason field; "who is HR" comes from the
   canonical `HR_ROLES`. This is the one part of the slice that is **not purely additive** if it
   binds every Leave Application, which is how I have read it — carved out in Read-this-first
   item 1 and raised as the first open question. Its cost is in the risk table: every
   unplanned sick leave at DTC would route to two people in head office.

**Subtract pass on this revision.** Removed: the 48-clock-hours assumption and the sentence
asking the analyst to pin it down, both answered by "working days"; the old window name; and the
temptation to make the notice rule's two numbers into a new DocType — they are Frappe defaults
like everything else here. Resisted adding: an emergency flag, a reason field, an override
button, a second working-day counter and an eighteenth definition of "who is HR" — all five are
now explicit not-doing lines so nobody re-proposes them. What is left: one rule on two
documents, two thin portal callers, two new controls, two settings, one guard, one notice check,
one balance preview, one pre-filled sentence.
