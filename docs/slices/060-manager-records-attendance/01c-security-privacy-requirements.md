---
slice: 060-manager-applies-on-behalf
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-10-15
status: draft
inputs: [01-product-brief.md, security-compliance-baseline.md, compliance-feature-map.md, the capability as stated by Surbhi on 2026-10-15 and revised twice the same day, her answers on the approver cascade and the notification channel the same day]
---

# A manager requests a change on behalf of an employee; HR confirms or rejects it

*Folder is `060-manager-records-attendance`, matching the brief. I did not write the
brief, the personas, the Kano class or the success measures.*

**Scope note, taken from Surbhi and not decided here.** The time bound is a rolling window of
**two whole working days**, configurable per tenant, with HR's manual route as the escape hatch (her
words, 15 Oct 2026). It is **not** "current month only" — an earlier version of the brief said that
— and it is not clock hours. SEC-9, SEC-10 and SEC-11 are written against the working-day window.
**The change matters to the controls rather than only to the scope:** current-month-only made the
paid-period guard redundant,
because the current month cannot have been paid. A rolling window crosses the month boundary, and a
month's payroll runs in the first days of the next — so on the 2nd the window reaches the 31st, and
the paid-period guard is now load-bearing. SEC-9 states the two conditions and why neither
substitutes for the other.

I have not read the rest of the brief against these requirements. Reconciling the two is the
analyst's job at `02`, and if the brief and this file disagree anywhere else, say so rather than
picking one.

**This file was rewritten twice today as the design changed.** Surbhi's final
instruction, 15 Oct 2026: *"ok got it let's get the manager request the changes and the
HR to confirm or reject it."* So it is a **two-party flow** and there is no
create-and-approve in one call. Earlier drafts of this same file addressed the
single-actor design; nothing was handed off from them, so I replaced the file rather than
leaving a superseded version nobody read. If you want the earlier analysis it is in git
history for this path.

**I am specifying here, not reviewing.** SEC-8's CI gate is my own idea, so somebody else
should sanity-check the gate at review.

---

## 0 · The headline

**Two-party is the right shape, and it is much easier to defend than what it replaced.**
Three things stand between it and working, and two of them are live today.

**1 — The two-party rule is not enforced anywhere. The guard that looks like it does,
does not.** `refuse_own_decision(employee, ...)` tests `is_own_record(employee)` — the
employee the request is **about**. A branch head who raises a correction for Ramesh and
then decides it passes that guard cleanly, because the request is about Ramesh, not about
them. **Today there is nothing in the codebase that stops the raiser being the decider.**
SEC-1.

**2 — With today's leave configuration, the new design deadlocks.** Every DTC employee's
`leave_approver` was set to their branch head earlier today. `_can_action_leave`
(`hr_api.py:938-968`) requires the session user to **be** the named approver. So if the
branch head raises the leave application, they are also the only person who may approve
it — and SEC-1 will refuse them. Nobody else can approve, because HR is not the named
approver. **The record would be unapprovable by anyone.** The fix writes the approver onto
the document at insert, resolved by Surbhi's cascade — HR of the department, else the
branch, else the company. It reverses none of today's work and needs two Custom Fields.
SEC-3, §2.

**3 — With today's `reports_to`, HR cannot confirm an attendance correction for two
working days.** `decide()` refuses an HR decision while the subject's `reports_to` has a
login and the two-working-day window has not passed
(`attendance_correction.py:1118-1140`). That window exists to give the manager first
refusal. **Under the new design the manager is the raiser, so there is nothing to wait
for** — and because `reports_to` was populated across DTC today, the window now fires for
almost everybody where yesterday it fired for almost nobody. HR will meet *"This is still
with X until <date>"* on every request a manager raises. SEC-4.

None of the three is a leak. All three are the difference between a design that works and
one that looks like it works.

**And it does move money — verified in code, not inferred.** `hooks.py:113-115` —
`Attendance` `on_submit` runs `payroll_rules_apply.on_attendance_submit`, so confirming a
correction submits the Attendance Request, writes the Attendance row and runs the pay-rule
engine. `payroll_rules.py:342-351` — an approved leave day stops being an absence: "no
quarters, no marks; the day is funded by a leave credit in the monthly total."

---

## 1 · The missing guard (question 1)

### What is missing, precisely

`refuse_own_submit` (`hrms/hrms/alvoraa_hr_core/access.py:184-190`) asks one question:
*is this document about me?* It is wired as `before_submit` on both doctypes
(`alvoraa_portal/alvoraa_portal/hooks.py:134` and `:249`) so the desk, REST and imports get
it. That part of the design is right and should be copied exactly.

The second question — *did I raise this?* — is asked nowhere.

### Sibling, not a change to the existing one

**A sibling.** Four reasons, and the fourth is the one that matters:

1. **Different question, different rule id.** Refusals are logged with a rule id so misuse
   can be found later (`log_refusal`, `access.py:28-49`). `SEC-9` means "decided their own
   request". A raiser-as-decider refusal needs its own id, or the security log cannot tell
   the two apart — and telling them apart is the only reason the id is there.
2. **Different message.** "You cannot decide your own request" is wrong for a branch head
   deciding Ramesh's day. The right message is "You raised this one, so HR confirms it." A
   merged function cannot say the right thing, and a refusal that misdescribes itself sends
   the next person to the wrong screen.
3. **Different signature.** The existing guard takes an employee id and is called from
   places that only have one. The new one needs the document, because the raiser is
   `doc.owner`.
4. **The existing guard is still needed on its own.** An employee raising their own request
   and then deciding it is caught by `refuse_own_decision` and not by the new rule in every
   case — and HR raising on behalf of somebody and then confirming it is caught by the new
   rule and not by the old one. **Neither guard subsumes the other.** Two rules, two tests,
   two log ids.

Recommended shape, in `alvoraa_hr_core/access.py` beside its sibling:

- `refuse_raiser_as_decider(doc, endpoint=None)` — refuses when
  `frappe.session.user == doc.owner`. New rule id, its own message.
- Called from inside `refuse_own_submit` (which already has the doc), so it reaches the
  desk, REST and imports through the hook that is already wired.
- **And called explicitly from the portal's `decide()`**, because declining does **not**
  submit — `decide()` uses `db_set` for a decline (`attendance_correction.py:1140-1148`), so
  `before_submit` never fires on that path. This is the same belt-and-braces the module
  already uses for `refuse_own_decision`: the guard in the endpoint gives the clear message,
  the hook covers the other doors.

**Honest limit of `doc.owner`.** It is set by Frappe at insert to the session user, so for
every path this slice creates it is the raiser. It is **not** the raiser for a record created
by a data import or a background job run as Administrator — there the owner is Administrator
and the guard is vacuous. That is acceptable here, because an imported attendance correction
is a different problem with a different answer, but it must be written in the docstring so
the next reader does not over-trust it.

**One related gap worth fixing in the same place, because it follows from the rule.**
`withdraw()` is self-only: `if doc.employee != me.name: throw`
(`attendance_correction.py:800-803`). So a manager who raises a request on behalf and then
realises it is wrong **cannot take it back** — they have to ask HR to reject it. Withdrawing
cannot change anybody's pay, so the clean rule is: **the raiser may withdraw, never decide.**
One condition on an existing endpoint. SEC-2.

---

## 2 · The leave approver conflict (question 2)

### The conflict, stated once

`_leave_approver_for(doc)` (`hr_api.py:914-935`) returns `doc.leave_approver` if it is set,
and otherwise falls back to `get_employee_leave_approver(doc.employee)` — the employee's own
approver, or their department's. `_can_action_leave` then requires the session user to **be**
that person, with no role bypass, deliberately: *"holding HR Manager does not make somebody
the approver."*

Every DTC employee's `leave_approver` is now their branch head. So a manager-raised leave
application names the manager as its own approver, SEC-1 refuses them, and no HR user can act
because none of them is the named approver. **Deadlock.**

### The correct configuration, and it reverses nothing

**Set `leave_approver` on the document, at creation, when the manager raises it on behalf — to
whoever Surbhi's cascade resolves: HR of the department, else the branch, else the company.**

`_leave_approver_for` reads `doc.leave_approver` **first** — verified at `hr_api.py:918-919` — so a
per-document value already wins over the employee's default. Therefore:

- **Employee raises their own leave** → the document inherits the employee's default →
  branch head approves. **Exactly what was configured today. Unchanged.**
- **Manager raises on behalf** → the server writes the cascaded HR approver into
  `Leave Application.leave_approver` at insert → HR confirms. The branch head is not the
  approver of that document and SEC-1 never has to fire.

**Cost: nothing is reversed.** Today's work setting every employee's `leave_approver` to
their branch head stays exactly as it is and remains correct for the employee-raised path,
which is the common one. No `Employee` record changes. No User Permission changes. The new work is
one field written at insert on one code path, plus two Custom Fields so the branch and company
rungs have somewhere to live — rung 3 on the ladder, and SEC-3 explains why it reuses Frappe HR's
own `Department Approver` child table rather than inventing two fields of its own.

The alternative — setting every employee's `leave_approver` to an HR user — **does** reverse
today's work, and it is worse: it takes the branch head out of the loop for leave the employee
raises themselves, which nobody asked for.

**The cascade also answers the availability worry I raised and could not answer myself.** I asked
for a named HR approver and a named deputy. A cascade whose rungs each allow more than one approver
removes the single point of failure by construction — there is no deputy to appoint, and no stopped
flow for anyone to work around. It replaces a person with a rule, which is the right trade in a
two-party control.

### Is "branch head for employee-raised, HR for manager-raised" a trap?

**It is not a trap, on one condition, and the condition is already met.**

The distinction is safe **because it lives on the document and is set by the server at
creation, never inferred afterwards.** A rule that re-derived "who should approve this?" from
who raised it would be a trap, because it would have to be re-derived identically in the
portal, the desk, the list view's action buttons and any future code path — and one of them
would get it wrong.

**Where it would become a trap, named precisely:** if `doc.leave_approver` is ever left blank
on a manager-raised record — a desk entry, an import, a future endpoint that forgets —
`_leave_approver_for` falls back to `get_employee_leave_approver(doc.employee)`, which returns
the branch head. The two-party flow then silently collapses to one party, and it collapses
**quietly**, which is the worst failure mode.

**That is exactly why SEC-1 is the primary control and the configuration is secondary.** With
SEC-1 in place, a blank approver falling back to the branch head who raised the record is
still refused — the request stops, visibly, instead of being approved by its own author. The
two controls back each other up: the configuration puts the right person on the document, the
guard stops the wrong one acting. Neither alone is enough, and that is the honest reason to
build both.

### Attendance needs the opposite of what I recommended this morning

For attendance there is no approver field; `_may_review()` asks the framework —
`frappe.has_permission("Attendance Request", "submit")` (`attendance_correction.py:259-267`).
Verified in `attendance_request.json`: `HR Manager`, `HR User` and `System Manager` hold
submit; the `Employee` role holds `create` but **not** submit.

**So attendance already works for the two-party design, with no change at all.** A manager on
the `Employee` role can raise but cannot decide, which is the rule we want, enforced by the
framework rather than by our code.

**Therefore: do not grant managers `submit` on `Attendance Request`.** An earlier draft of
this file treated the missing submit permission as a gap to close. Under the two-party design
it is the control. SEC-5 states it as a requirement so nobody closes it as a convenience
later.

---

## 3 · What the record must carry (question 3)

To answer, six months later, *who raised it, for whom, in what capacity, who decided it, when,
and on what grounds.*

### Attendance Request — mostly there

| What a reader needs | Field | State |
|---|---|---|
| For whom | `employee` | **Exists** |
| Who raised it | `owner` | **Exists** (Frappe's own) |
| When raised | `creation` | **Exists** |
| Who decided | `alvoraa_reviewed_by` | **Exists** |
| When decided | `alvoraa_reviewed_on` | **Exists** |
| Decided in what capacity | `alvoraa_decided_as` — `Manager` / `HR` / `None`, derived server-side, no argument anywhere (`attendance_correction.py:976-1005`) | **Exists** |
| Why rejected | `alvoraa_review_note` | **Exists** |
| State | `alvoraa_review_status` | **Exists** |
| Every change, replayable | `track_changes: 1` (`attendance_request.json:210`) | **Exists** |
| **Raised in what capacity** | — | **New** |
| **What the employee said, and how we got it** | — | **New** |
| **Whether the employee was told** | — | **New** |

### Leave Application — much thinner

| What a reader needs | Field | State |
|---|---|---|
| For whom, when raised, who raised it | `employee`, `creation`, `owner` | **Exists** |
| Who may decide | `leave_approver` | **Exists** — and §2 makes it carry the design |
| Decided by whom | `modified_by` on the submit | **Exists, but weak** — `modified_by` is whoever last touched it, not whoever decided |
| Decided when, why rejected, in what capacity | — | **Missing** |
| Every change, replayable | — | **Missing. `leave_application.json` has no `track_changes` key at all**, so an Open→Approved transition leaves no Version row |

### The new fields — four, on both doctypes

1. **`alvoraa_raiser_capacity`** — Select: `Manager` / `HR` / `Other`. Derived server-side at
   insert, the same way and from the same helper as `decided_as`. **It must be stored, not
   derived later**, for the same reason `decided_as` is: `reports_to` changes, so "were they
   this person's manager?" can only be answered truthfully if it was frozen at the time. Set
   only when the record is raised on behalf, so a value present *is* the on-behalf flag.
2. **`alvoraa_grounds`** — Small Text. What the employee told the manager. The manager's words
   do **not** go into `explanation` or `description`; those are the employee's own fields and
   overwriting them destroys the provenance a grievance turns on.
3. **`alvoraa_grounds_source`** — Select: `In Person` / `Telephone` / `Written Slip`. How the
   word was obtained, so a grievance can test it.
4. **`alvoraa_employee_notified_on`** — Datetime. Evidence the subject was told (PRIV-3).

Plus, for Leave Application only: **`track_changes = 1`**, and the three decision fields
`alvoraa_reviewed_by` / `_on` / `_note` plus `alvoraa_decided_as`, reused from Attendance
Request rather than named differently.

**All of it by Custom Field and Property Setter** — rung 3, customisation. Not a JSON edit: we
vendor a fork of `hrms` and a JSON edit conflicts on every rebase, which is the reason
`install_reasons` already uses a Property Setter (`attendance_correction.py:100-120`). Not a
new DocType: a new DocType adds a permission surface, a migration, a report and a second place
for the truth to live, and I can name nothing it buys here.

---

## 4 · Threat model, four lines

**Who wants this, and what is the cheapest way?** Not an outsider. The cheapest route is a
branch head who raises a request for somebody and confirms it themselves — which today nothing
stops (§1). The second cheapest is a leave application whose `leave_approver` is blank, falling
back to the branch head who raised it (§2). The third is editing `Employee.reports_to`, which
now decides who may raise for whom and which no application code writes — verified by a grep
over every tracked `.py` — so its only writers are the desk form, REST and data import, all
held by HR roles.

**Blast radius of one mistake.** Cross-tenant is not reachable: one tenant per site. The
realistic top of the scale is one branch's payroll month — roughly 60 of 363 people — because a
manager can only raise for their own line. If HR is the party that fails rather than the
manager, it is the whole company, bounded by `permitted_employee_filters()`.

**What becomes possible that was impossible before.** A whitelisted endpoint that names
somebody else and asks for their attendance to change — the thing `raise_correction`'s docstring
refuses on purpose (`attendance_correction.py:752-759`). A record about a person, authored by a
colleague, that changes their pay and that they were not asked about. And back-dating: today
`raise_correction` has **no lower bound at all** (`attendance_correction.py:764-765` checks only
that the date is not in the future), which is what SEC-9's window closes — but note the window is
what makes the paid-period guard necessary rather than optional, because 48 rolling hours reach
back across a month boundary into a month that has been paid. **Two-party removes the worst of the
rest:** the author no longer decides, so one mistake needs two people.

**How would we find out?** Today, we would not. `log_refusal` logs **refusals only**
(`access.py:28-49`); a successful on-behalf raise writes nothing. `Alvoraa Payroll Reprocess
Log` covers a reprocess, not a decision. There is no report of "requests raised for somebody
else". **The detection is the gap, not the prevention** — and under two-party the detection that
matters most is cheap, because HR already has to open a queue to confirm these.

---

## 5 · Data inventory

Classes follow `compliance-feature-map.md` A1 (`public / internal / sensitive / statutory-id`).
A1 is not built, so these are **declared here and applied by hand until it is** — which is itself
the argument for A1.

| Field / object | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| `Attendance Request.employee`, `from_date`, `to_date`, `reason`, `half_day` | sensitive | Correct the attendance that prices the payslip | One year (business rule); **statutory floor open, §8 Q2a** | Subject; the raiser; HR within `permitted_employee_filters` |
| `Attendance Request.explanation` | sensitive | The employee's own account of the day | As above | As above |
| `Leave Application.employee`, `leave_type`, `from_date`, `to_date`, `description`, `status` | sensitive | Fund a day that would otherwise be an absence | As above | As above |
| `Leave Application.leave_approver` | internal — **and it now carries the two-party design** | Decides who may confirm | As above | As above |
| `leave_approvers` rows on Department, Branch, Company (rung 1 native, rungs 2 and 3 new) | internal | Resolve who confirms a manager-raised request | Life of the org record | Anyone who may read the parent record |
| **new** `alvoraa_manager_filing_window_days` — a Frappe default, 2 working days | internal — **a pay-affecting control, not a preference** | How far back a manager may file | Life of the tenant; changes keep a Version row (SEC-11) | HR Manager and System Manager may change it; anyone may be affected by it |
| **new** `Leave Type.alvoraa_notice_rule_exempt` — a Check, default off | internal | Mark a leave type the notice rule does not apply to (Sick Leave) | Life of the leave type | Anyone who may read the Leave Type |
| **new** `alvoraa_leave_notice_rule_enabled` — a Frappe default, **absent means off** | internal — a policy restriction on all 363, not a preference | Turn the advance-notice rule on | Life of the tenant; changes keep a Version row (SEC-11's mechanism) | HR Manager and System Manager may change it; **every employee is affected by it** |
| **new** outbound WhatsApp message — the employee's number plus a one-line awareness notice | sensitive, **and it leaves our infrastructure** | Tell the employee something was raised for them | Meta's retention, not ours — **we do not control it**, which is why the body carries the minimum | The employee; Meta as sub-processor |
| **new** `alvoraa_grounds` | sensitive | Evidence for a change requested without the employee present | As above | As above |
| **new** `alvoraa_grounds_source` | internal | How the word was obtained, so a grievance can test it | As above | As above |
| **new** `alvoraa_raiser_capacity` | internal | Who was entitled to raise it, frozen at the time | As above | As above |
| **new** `alvoraa_employee_notified_on` | internal | Evidence the subject was told | As above | As above |
| `alvoraa_reviewed_by` / `_on` / `_note` / `_decided_as` | internal | Who confirmed, when, why not, in what capacity | As above | As above |
| `Employee.reports_to` | internal — **but it decides who may raise for whom** | Scope | Life of the employee record | Anyone who may read the Employee row |
| `Attendance` row and the engine's verdict columns | sensitive | Price the payslip | As above | As above |
| `security` logger line — user id, endpoint, doctype, document name, rule, capacity | internal | Detection | CERT-In 180 days, **not met today**, baseline §3a | Provider operations |

**Leave reason is a near-miss for special-category data.** "Sick Leave" against a named person
on a named date is health-adjacent. Frappe HR already has it, so this slice does not create it —
but a **manager** now authors it. The grounds field must not invite a diagnosis. PRIV-2 covers
the field; the wording is the designer's job and I check it at `06`.

---

## 6 · Access intent, including who must NOT see what

| Actor | May do | Must NOT |
|---|---|---|
| Location manager (5 at DTC) | Raise for employees in their own `reports_to` line, deep · withdraw what they raised while it waits | **Decide anything they raised** · raise outside their line · raise for themselves · raise on a date in a paid period · hold `submit` on `Attendance Request` · be the `leave_approver` on a record they raised |
| HR (`HR Manager` / `HR User`) | Confirm or reject, within `permitted_employee_filters()` · raise on behalf, on the same terms as a manager | Decide anything they themselves raised · act outside their companies **and branches** · decide their own request |
| Owner / `System Manager` (2 at DTC) | As HR | As HR — one definition, not a second role literal |
| The subject employee | Raise their own · be told when somebody raises for them · obtain a print of what was raised · dispute it | — |
| Whoever may edit `Employee.reports_to` | Change it | Change it without the change leaving a record (SEC-7) |
| Whoever may edit the `leave_approvers` rows on a Department, Branch or Company | Set who confirms manager-raised leave | Change it without the change leaving a record — it decides the second party in a two-party control, so it is the same class of privilege path as `reports_to` (SEC-7) |
| Agency supervisor (five agencies, 44 staff) | **Undecided — fail closed.** §8 Q1 | Anything, until Q1 is answered |
| Any other employee | Nothing | See another employee's request, grounds, note or notification |
| Guest | Nothing | Reach any of this. No endpoint here may be `allow_guest` |

**New-Frappe-app checklist: not engaged.** This capability installs no app. No new public page,
no guest access, no self sign-up, no role created by an installer.

---

## 7 · Requirements

Each says what must be true and how a test proves it. The analyst must trace every one to an
acceptance criterion, or record Surbhi's decision not to adopt it.

### Security

*Order note: SEC-1 to SEC-8 and SEC-12 to SEC-13 are below. **SEC-9 to SEC-11 — the time bound, the
working-day counter and the two settings — are in the last subsection of §7**, "Also required", with
the paid-period guard they belong beside.*

**SEC-1 · The raiser can never be the decider. (The two-party rule.)**
A new sibling guard, `refuse_raiser_as_decider(doc, endpoint=None)`, in
`hrms/hrms/alvoraa_hr_core/access.py` beside `refuse_own_decision`, with its own rule id and
its own message. It refuses when `frappe.session.user == doc.owner`. It is called from inside
`refuse_own_submit` so the `before_submit` hook already wired at
`alvoraa_portal/alvoraa_portal/hooks.py:134` and `:249` covers the desk, REST and imports —
**and** called explicitly from the portal's `decide()`, because a decline uses `db_set` and never
submits, so `before_submit` does not fire on it. No role is exempt: HR Manager, System Manager
and Administrator included. The `doc.owner` limitation for imports goes in the docstring.
*Test, and all five are needed:*
(a) manager raises for Ramesh, same manager approves → refused, with the new rule id in the
`security` log, **not** `SEC-9`;
(b) same, but declines → refused (this is the path `before_submit` misses);
(c) same, via the desk `submit` → refused;
(d) same, via the REST API → refused;
(e) manager raises for Ramesh, **HR** approves → allowed, and `refuse_own_decision` still
refuses an employee deciding their own.
*Observable only if:* the fixture has a record whose `owner` is the deciding user. A test that
creates the record as Administrator and decides as HR passes while proving nothing.

**SEC-2 · The raiser may withdraw, never decide.**
`withdraw()` is self-only today (`attendance_correction.py:800-803`), so a manager who raised a
request on behalf cannot take it back. Extend it to the raiser (`doc.owner`), while it is still
waiting. Withdrawing changes nobody's pay, so this widens nothing that matters and it removes
the incentive to go looking for a decide button.
*Test:* the raiser withdraws a waiting request → status `Withdrawn`, record intact (not deleted).
The raiser withdraws one already decided → refused. A third party who is neither the subject nor
the raiser → refused.

**SEC-3 · A manager-raised leave application names its HR approver at insert, by cascade.**
The server resolves an HR approver and writes it into `Leave Application.leave_approver` at insert.
`_leave_approver_for` already reads `doc.leave_approver` first (`hr_api.py:918-919`), so this needs
no change to `_can_action_leave` and **no change to the `leave_approver` set on every Employee
today.** An employee-raised application is untouched and the branch head still approves it.

**The cascade** (Surbhi, 15 Oct 2026: *"HR of their department>branch>company whoever is set"*) —
first rung that is set wins:

| Rung | Where it is read from | What has to exist |
|---|---|---|
| 1 · Department | `Department Approver` rows on the employee's Department, `parentfield = "leave_approvers"`, lowest `idx` | **Nothing new.** Frappe HR ships it, and `get_employee_leave_approver` already reads exactly this shape (`leave_application.py:1563-1568`). Rung 1 is configuration |
| 2 · Branch | the same `Department Approver` child table, as a Custom Field `leave_approvers` on `Branch` | One Custom Field |
| 3 · Company | the same again, on `Company` | One Custom Field |

**Read the department rung directly, not through `get_employee_leave_approver`.** That function
reads `Employee.leave_approver` **first** (`leave_application.py:1561-1563`) and only falls through
to the department when it is blank. At DTC it is never blank — it is the branch head, the very
person this cascade exists to exclude. So the helper for this path reads the three rungs itself and
never consults `Employee.leave_approver`.

**Why reuse `Department Approver` rather than add two Link fields.** One query shape serves all
three rungs — same child doctype, same `parentfield`, different `parenttype` — so one helper reads
them and there is nothing to keep in step. It is `istable: 1` with a single required `approver` Link
to User and `ignore_user_permissions: 1`
(`hrms/hrms/hr/doctype/department_approver/department_approver.json`), so a Branch or Company User
Permission cannot hide the HR user from the picker. And a table allows more than one approver per
rung, which is what answers the cover-while-they-are-away problem **by construction** instead of by
naming a deputy. **Its cost, stated plainly:** the doctype's label reads "Department Approver" on a
Branch form, which will look odd, and a child grid is a slightly heavier control than a Link field.
Two plain Link fields would also work and would be marginally simpler; they would cap each rung at
one person and give the helper two read shapes to maintain. I recommend the reuse. Surbhi decides.

**No rung set, and the raiser-is-the-approver case — both refuse, at the raise.**
- If no rung is set, **refuse at raise time and name what is missing**: "No HR approver is set for
  this person's department, branch or company. HR should add one before a request can be raised for
  them." It must **never** fall back to `Employee.leave_approver`, because that is the branch head
  and that is the deadlock in §0 item 2.
- If every rung that is set resolves to the raiser — an HR user raising on behalf where they are
  also their own department's approver — **refuse at raise time too**, rather than creating a
  record nobody can confirm. Skipping to the next rung instead would be defensible, but refusing is
  one line, says what is wrong, and never produces a stuck record. Fail closed at the cheapest
  moment.

*Test:*
(a) department rung set → `doc.leave_approver` is the department's first approver;
(b) department blank, branch set → the branch's;
(c) department and branch blank, company set → the company's;
(d) **none set → the raise is refused, with a message naming department, branch and company** —
    and assert `doc.leave_approver` was never filled from `Employee.leave_approver`;
(e) the only approver that resolves is the raiser → the raise is refused;
(f) `_can_action_leave` is false for the manager and true for the resolved HR user;
(g) employee raises their own → the document's approver is the branch head, unchanged;
(h) **the trap test:** force `doc.leave_approver` blank on a manager-raised record, assert
    `_leave_approver_for` falls back to the branch head **and that SEC-1 still refuses them** — the
    two controls must be shown to back each other up.
*Observable only if:* the fixture sets the three rungs independently. A fixture that sets all three
cannot show the cascade; one that sets none cannot show rungs 1 to 3 at all.

**SEC-4 · The two-working-day HR wait does not apply when the manager is the raiser.**
`decide()` refuses an HR decision while the subject has a manager with a login and the window has
not passed (`attendance_correction.py:1118-1140`). The window exists to give that manager first
refusal. When the manager **is** the raiser there is nothing to wait for, and because `reports_to`
was populated across DTC today the window now fires for almost everybody. Skip it when
`doc.owner` is the subject's manager's login — one condition, reusing `_manager_user_for`, which
is already the same derivation `decided_as` uses so the two cannot drift.
*Test:* manager raises on behalf, HR decides the same day → allowed. Employee raises their own,
their manager has a login, HR decides the same day → still refused with the date and the
manager's name (today's behaviour, unchanged). Subject has no `reports_to`, or their manager has
no login → HR allowed at once (the existing no-manager clause, unchanged).
*This is a behaviour change to live code and it must be called out in the spec, not folded in.*

**SEC-5 · Managers are not granted `submit` on `Attendance Request`.**
Verified in `attendance_request.json`: `HR Manager`, `HR User` and `System Manager` hold submit;
the `Employee` role holds `create` but not submit. That absence **is** the attendance half of the
two-party rule, enforced by the framework rather than by our code. It must not be closed as a
convenience later.
*Test:* the permission freeze check already in `scripts/` / `permission_health.py` watches
`Attendance Request`; add an assertion that no role beyond the three holds submit on it, and that
the `Employee` role does not. A failure means somebody granted it in the Desk.

**SEC-6 · The subject is authorised server-side, on every raise.**
A manager is refused any subject outside `_reports_to(caller, deep=True)`. An HR caller is
refused any subject outside `permitted_employee_filters(caller)` — slice 030's single definition,
which includes branch. The subject lookup filters `status = "Active"` (ERPNext does not disable a
leaver's login). A missing employee and an out-of-scope employee return the **same** message, so
the refusal is not an existence oracle. Fails closed.
**Including the fix this inherits:** `_hr_target_employee` (`hr_api.py:2155-2171`) scopes by
`permitted_companies()` and never by branch. Six callers share it — `hr_api.py:1123, 1456, 2179,
2327, 2375, 3127`. One function changes to `permitted_employee_filters()`.
*Test:* manager raises for an employee not in their line → refused plus one `security` line. A
store HR person with a Branch permission raises for another branch's employee of the same company
→ refused. Non-existent id → byte-identical message. Caller whose Employee row is `Left` →
refused. Plus **six negative tests**, one per existing caller above — this slice's
unscoped-sibling check.
*Observable only if:* the fixture has two branches with employees in each **and** Branch User
Permission rows whose `applicable_for` is empty or `Employee` — §8 Q5. Say so in the test, or a
green result means nothing (slice 028's lesson).

**SEC-7 · Provenance is derived and stored; `reports_to` changes leave a record.**
Two halves of one rule about trusting the record later.
(a) `alvoraa_raiser_capacity` and `alvoraa_decided_as` are computed server-side. No endpoint takes
an argument for either. Both are stored at the time, because `reports_to` changes and "were they
this person's manager?" cannot be re-derived truthfully afterwards.
(b) A change to `Employee.reports_to`, or to the `leave_approvers` rows on a Department, Branch or
Company, leaves a Version row and writes one `security` line in `log_refusal`'s shape, carrying
document **ids** and the acting user, never a name. `reports_to` decides who may raise for whom and
the approver rows decide who confirms, so changing either is a privilege change in a two-party
control.
*Test:* post `raiser_capacity="HR"` and `decided_as="Manager"` in the request body; assert both
stored values are unmoved — the pattern already used for `decided_as`
(`attendance_correction.py:976-990`). Change `reports_to`; assert a Version row with old and new
values, one log line with no personal content, and that the manager's reach under `_reports_to`
changed accordingly. Change a Department's `leave_approvers`; assert a Version row and that a newly
raised request resolves to the new approver.
*Rests on an assumption I could not check:* whether `Employee` carries `track_changes: 1`.
`erpnext` is not in this repo — §9.

**SEC-8 · A CI gate that stops the two-party rule regressing.**
`scripts/check_two_party_guards.py`, in the style of `check_api_paths.py` and
`check_no_demo_passwords.py` — static, no database, runs in the Lint job. Four assertions:

1. For `Attendance Request` and `Leave Application`, some app's `hooks.py` wires `before_submit`
   to `refuse_own_submit`. **This is the check that matters most**, because deleting one line in
   `hooks.py` silently removes the rule from the desk and REST while every portal test still
   passes.
2. `refuse_own_submit`'s body calls **both** `refuse_own_decision` and
   `refuse_raiser_as_decider`.
3. Every `@frappe.whitelist()` function in `alvoraa_portal` whose body contains `.submit()`, or a
   `db_set` touching `review_status` or `status` on a watched doctype, also calls one of the two
   guards.
4. No whitelisted function anywhere takes a parameter named `decided_as`, `raiser_capacity`,
   `raised_by` or `entered_by`. Provenance must not be settable from a request body.

*Test:* the gate's own fixture — remove the `before_submit` line from a copy of `hooks.py`, assert
non-zero exit; add a whitelisted function with a `decided_as` parameter, assert non-zero; restore,
assert zero.
*Honest limit, and it belongs in the script's docstring:* a static check cannot prove the guard was
applied to the right document, and assertion 3 cannot see a decision made through a helper it does
not recognise. It is a tripwire, not a proof. The proof is SEC-1's five tests.

**SEC-12 · The leave advance-notice rule: off unless configured, enforced on the document, exempted
by a stored fact and not by a live session role.**

Surbhi, 15 Oct 2026: *"leave rules should have an optional setting to make it restrictive for the
leave application. in case of emergency HRs path ignores the notice rule."*

| Leave asked for | Notice required |
|---|---|
| 1 day | at least 2 days ahead |
| more than 1 day | at least a week ahead |

**(a) Off unless configured, and the read must make that true.** One key,
`alvoraa_leave_notice_rule_enabled`, and **the restriction applies only when it is explicitly set
to a true value.** The idiom I recommended for the filing window is **wrong here, with the sign
reversed, and it is the dangerous direction:** `cint(get_default(KEY) or DEFAULT)` on an unset key
would switch a **restriction** on for every tenant that never asked for one — a silent policy
change, applied to every employee, delivered by a deploy. So the read is: fetch the raw value;
`None` or `""` means **off**; only an explicit truthy value turns it on. There is no default to fall
back to, because the default is "no rule".

**One key, not three.** The two thresholds are the rule as Surbhi stated it. Making them
configurable would be three settings where one answers the requirement, and a tenant wanting
different numbers is a new decision, not a feature to pre-build.

**(b) On the document, in `validate` — your reading is right.** Desk, REST and import all obey, the
same argument as SEC-9(b)'s placement.

**(c) But the exemption must key on a stored fact, not on the live session role — and that is the
part that would have bitten.** You asked whether a role test inside `validate` is the kind of thing
that bites later. **It is, for a specific and non-hypothetical reason:** `validate` runs in contexts
where `frappe.session.user` is not the human who decided anything — a background job, a scheduled
task, a patch, a `bench execute`, or a data import run as Administrator. In those contexts a session
role test fails in both directions: Administrator holds every role, so the restriction is **silently
skipped**; and a worker with no user context would **wrongly block**. This project already has a
logged trap where an Administrator-run change back-dated a joining date and Frappe marked Absent for
every day since. A policy rule whose exemption depends on who happens to be holding the save is a
rule that reports the wrong answer on exactly the paths nobody tests.

So the exemption reads the record's **`alvoraa_raiser_capacity`** — the server-derived, stored field
SEC-7(a) already requires — and skips the notice rule when it is `HR`. Three things that buys:
it is stable under re-save, background jobs and imports; it is **auditable**, because a reader six
months later can see *why* the rule was skipped; and it cannot be flipped by who presses Save. For a
record with no stored capacity (pre-existing rows, or one created straight on the desk), derive the
capacity once with the same server-side helper and store it — so the rule is always reading a stored
fact, never a session.

**(d) The HR test reads the canonical `HR_ROLES`, and this must not be the eighteenth variant.**
Wherever capacity is derived, the role set comes from `HR_ROLES` at
`hrms/hrms/alvoraa_hr_core/access.py:25`, never a literal. §9 records seventeen hardcoded variants
in four forms in `hr_api.py`; adding an eighteenth here would be the clearest possible
demonstration that nobody reads their own findings. **This needs no new gate work:** SEC-8's
assertion 4 already fails any whitelisted function containing a literal with both `"HR Manager"` and
`"HR User"`, so the gate catches it on the way in.

*Test:*
(a) **unset key → no restriction at all**, for every leave length. This is the first test and the
    one that protects 363 people from a policy nobody chose;
(b) key on: 1 day asked for 1 day ahead → refused · 2 days ahead → allowed;
(c) key on: 3 days asked for 5 days ahead → refused · 8 days ahead → allowed;
(d) key on, record's capacity is `HR` → allowed at any notice, including same day;
(e) key on, the same document re-saved by a background job or by Administrator → **the stored
    capacity still decides**, and a manager-raised record is still refused. This is the test that
    proves (c) above was built and not just written down;
(f) the refusal names the notice required and the route out, and does not read as "not allowed".

**(e) Sick Leave is exempt, and the exemption is a property of the Leave Type.**
Surbhi, 15 Oct 2026: *"Sick Leave as an exempt type."* So a leave type can be marked as one the
notice rule does not apply to, and the rule skips it for **everybody** — not only for HR. No
emergency marker, no reason field, no per-request override: she rejected those, and this does not
reintroduce them, because the exemption describes the **type** and not the **request**.

**Ruling: a Check on `Leave Type` by Custom Field, not a setting naming exempt types.** I agree with
your lean, and there are two reasons beyond the one you gave:

- **A setting naming types is a second copy of a list of type names.** It drifts the moment a type is
  renamed or a new one added — and nobody is told. A Check on the type cannot disagree with itself.
  This is the same argument `install_reasons` already makes in this codebase
  (`attendance_correction.py:100-120`): build from the field, never from a copy of it.
- **A Check is one read, not a parse.** `frappe.db.get_value("Leave Type", lt,
  "alvoraa_notice_rule_exempt")` — no splitting a comma list, no trimming, no case question.

And your reason stands on its own: a tenant with two sick-leave-like types marks both, which a
single named setting cannot express.

**This exemption fails toward *not applying the rule*, which is the opposite of my usual default,
and that is deliberate.** Fail-closed exists to protect the person the data is about. Here the
restriction is the thing that harms them — it stops a sick day being taken — so "closed" means not
applying it. If the Check cannot be read for any reason, the leave goes through. The cost of being
wrong that way is a policy not enforced; the cost of being wrong the other way is somebody refused
sick leave by a database error.

*Test:* a type marked exempt, 1 day asked for the same day, raised by a **manager** → allowed, with
the rule switched on. The same type and date for a non-exempt type → refused. The Check unset or
unreadable → allowed. And the default: a Leave Type created after this ships is **not** exempt
unless somebody marks it.

### A ruling you did not ask for, on the scope, because it changes who this rule lands on

**Your assumption is almost certainly right and it matters more than the rule does.** *"for the
leave application"* reads as binding everyone, not only managers acting on behalf. If so **this part
of the slice is not additive: it changes leave for all 363 people at DTC**, and it should be flagged
to Surbhi in those words before it is built, because the rest of the slice is a new capability and
this one is a restriction on an existing one.

**There was a privacy angle, and (e) closes it.** Sick leave is unpredictable by definition, so a
2-day notice rule would have made genuine sick leave **structurally non-compliant** — not
occasionally, but every time. Every sick day at DTC would have routed to HR, which means **more
people learning about an illness than before**: previously the manager, now the manager plus
whichever HR person handled the exception. That was a need-to-know regression on health-adjacent
data, caused by a policy setting rather than by a code defect.

**Marking Sick Leave exempt removes it. A sick day no longer has to be explained to head office in
order to be taken, and that was the strongest argument for the exemption** — stronger than the
volume argument, because volume is an operational cost and this was a privacy harm to the person the
data is about. **Closed, not open.**

**The fairness shape also drops, and it is worth saying why rather than just that it does.** A rule
applied uniformly that bites hardest on the people who can least comply is the shape of indirect
adverse impact, and the staff this slice exists to help are exactly the ones with no login, who
cannot read the rule, and whose manager is their only route. Exempting the one leave type nobody can
plan removes most of that, because the days they could not have given notice for are the days the
rule no longer touches. **What remains open** is the rest of the rule on all 363 people — planned
leave with a week's notice is a real restriction, just not an unfair one in the same way — which is
why the scope assumption above still needs Surbhi's word.

**SEC-13 · A manager login must not hold an HR role, and a grant must be visible.**

**I agree with your concern and it is sharper than you put it.** An exemption everybody needs daily
stops being an exemption, and the predictable relief valve — give the branch heads an HR role so
they can self-exempt — is not one reversal. **One role grant silently defeats four requirements at
once:**

| What it is meant to do | What else it does, unintended |
|---|---|
| Bypass the notice rule (SEC-12) | Grants `submit` on `Attendance Request`, **reversing SEC-5**, so the manager can now confirm their own filings |
| | Widens their reach from their `reports_to` line to `permitted_employee_filters`, **changing SEC-6** from team scope to company-or-branch scope |
| | Makes them eligible as SEC-3's cascade approver, so a manager-raised leave can resolve back to a manager — **collapsing the two-party split** |
| | Changes their stored `alvoraa_raiser_capacity` to `HR`, so SEC-12's own audit trail stops showing that a manager raised it |

**So pin it the way SEC-5 is pinned, with a check rather than a note.** Extend the permission
freeze check (`alvoraa_portal.permission_health`, runbook at
`docs/runbooks/permission-freeze-check.md`) to assert: **no user who is any employee's `reports_to`
holds a role in `HR_ROLES`.** It reads only role names and permission flags, it is already safe to
run on a live tenant, and it turns "somebody will notice" into a line of output. A tenant that
genuinely wants a branch head to be HR can record that decision and accept the finding — which is
governance — rather than discovering it a year later in a grievance.
*Test:* grant `HR User` to a login that is some employee's `reports_to`; assert the check reports it
by name. Revoke it; assert the check is clean. **And the four consequence tests:** with the role
granted, assert the slice's own guards still refuse — SEC-1 still stops them deciding what they
raised, and SEC-3's cascade still refuses to resolve to the raiser. Those two are the last line if
SEC-13 is ignored, and they must be shown to hold.

### Privacy — unchanged by the redesign, because something is still recorded about a person who was not involved

**PRIV-1 · No new field without a class, a purpose and a retention answer.**
Every field this slice adds appears in §5 before the engineer opens a file. A field with no class
inherits the loosest treatment in the system, which is how personal data reaches an export nobody
specified.
*Test:* §5's table and the diff's new fieldnames match exactly, both directions. I check this at
`06`.

**PRIV-2 · The grounds are the employee's reported reason, with its source, in their own field.**
`alvoraa_grounds` plus `alvoraa_grounds_source` (In Person / Telephone / Written Slip). The
manager's words do **not** go into `Attendance Request.explanation` or
`Leave Application.description` — those are the employee's own fields, and overwriting them
destroys the provenance a grievance turns on. The help text asks what the employee said, not why
the manager believes it, and must not invite a medical detail.
*Test:* an on-behalf raise leaves `explanation` / `description` empty unless the employee's own
words were supplied, and populates both new fields. A raise with no `alvoraa_grounds_source` is
refused.

**PRIV-3 · The employee is told — by their manager, and by WhatsApp where it is available.**
Surbhi, 15 Oct 2026: *"they will be informe by their manager or if there is any whatsapp
integration then that would go."*

**Say the honest thing first: the primary channel is a human conversation, and the system cannot
evidence it.** The manager tells the employee. That genuinely discharges the duty — a person being
told by their manager is better notice than a message on a phone they may not have — but **no
record of it exists, and none should be invented.** I am not asking for a "I told them" checkbox:
a tick-box makes the manager attest to something nobody can check, which produces a field that
reads as evidence and is not. That is worse than an empty field, because an empty field is honest.

So PRIV-3 has three parts:

1. **WhatsApp, where the tenant has it.** `frappe_whatsapp` (shridarpatil/frappe_whatsapp, pinned
   at commit `08bc1f6af2e3`) is in the production image — `deploy/Dockerfile` ARG at line ~76 and
   the `bench get-app` at ~193 — and the Dockerfile's own comment says it is "sold as the
   `whatsapp` feature in subscription.py", registered at `subscription.py:403-414`. So it is
   **present in the stack and gated by the tenant's plan**. Where the feature is on and the
   employee has a number, a message goes out when a request is raised for them and
   `alvoraa_employee_notified_on` is set from the send, not from a human claim.
   *Availability on DTC is unverified — see §10.*
2. **Nothing is faked where WhatsApp is not available.** `alvoraa_employee_notified_on` stays null
   and the row in HR's confirmation queue reads **"employee not notified by the system"** — not
   "employee not told", because the manager probably did tell them. Under two-party this costs
   nothing to surface: HR has to open that queue anyway, so the one person who can ask "did you
   tell them?" sees it at the moment they decide.
3. **A printed slip, if evidence is ever required.** The honest fallback, and it is **not built in
   this slice.** If a grievance, a customer's DPO or an auditor ever needs proof that a specific
   employee was told, a human conversation will not provide it. The mechanism that would is the
   screen producing a printable slip the employee signs, with the branch recording its receipt
   against the same field. **That is a known, named, accepted gap today** — recorded in residual
   risk, not quietly omitted.

**And one thing Q4's answer introduces that was not there before: WhatsApp is a disclosure to a
third party.** `frappe_whatsapp` uses Meta's WhatsApp Cloud API, so the message content leaves our
infrastructure and reaches Meta. Two consequences, and both are cheap:

- **The message carries the minimum and nothing more.** No leave type, no reason, no grounds text,
  no dates beyond the one the request is about. *"A request about your attendance was raised for
  you on 15 Oct. Please speak to your manager or HR."* That is enough to make the person aware,
  which is the entire purpose. Sending "Sick Leave, 3 days, fever" to Meta would put
  health-adjacent data about a named person through a third party to achieve nothing extra. This is
  DPDP minimisation (baseline §2) applied to an outbound channel, and it is testable.
- **Meta belongs on the sub-processor register.** Feature-map A9, status `?`. Not this slice's job
  to build the register, but if WhatsApp notification ships, Meta is a sub-processor for DTC's
  employee data and the privacy notice and any customer DPA must say so. Flagged, with an owner, in
  residual risk.

Fail-closed here is **not** blocking the record; a person needs their pay fixed. It is refusing to
record a notification that did not demonstrably happen.

*Test:* a raise on a tenant with the `whatsapp` feature on and a number on the Employee →
a message is queued and `alvoraa_employee_notified_on` is set from the send. Feature off, or no
number → the field stays **null**, and the HR queue row shows "employee not notified by the
system". **Assert the outbound payload, not the intent** (feature-map H3's rule, applied here):
capture the message body and assert it contains no leave type, no reason, no grounds text and no
employee name beyond what is needed to address it. **And the negative test that matters:** no
endpoint on this path accepts an argument that sets `alvoraa_employee_notified_on` — post one and
assert it is unmoved. The field records a send, never a claim.
*No longer blocked.* Q4 is answered.

**PRIV-4 · Access without a login.**
A branch-operated print of "every request raised for this person, this month", produced without an
HR ticket, covering both doctypes, the grounds, the capacity and the outcome. The print is itself a
disclosure, so it writes one log line: who printed, for whom, when.
*Test:* the print for employee X contains X's records and no other employee's; produces one log
line; is refused for a subject outside the caller's scope (SEC-6's rule, reused).

**PRIV-5 · Dispute without a login.**
A route for the employee to contest a record they did not raise, lodged at the branch on their
behalf and **recorded as the employee's dispute, not HR's**. The disputed record is flagged and
reaches HR before payroll. The cheapest rung is the existing `Attendance Request` plus
`alvoraa_review_note` — no new DocType, and I would refuse one.
*Test:* a dispute lodged for employee X flags the original record, appears in HR's list, and the
original record's values are unchanged (feature-map D5, "dispute without edit").

**PRIV-6 · No personal content in any log or error message on this path.**
User ids, endpoint names, document names, employee ids, capacity and rule ids only. Never the
employee's **name**, the grounds text, the dates, the leave type or the reason. `access.py:28-49`
already does this and says why; the new raiser-as-decider refusal, the `reports_to` line and every
`frappe.log_error` on this path must match it.
*Test:* force an exception on the on-behalf path and assert the captured traceback and log lines
contain none of the employee's name, the grounds string or the leave type.
**If this fails it is a P0, not a Major.**

**PRIV-7 · Retention: one year is the business rule. No deletion job runs until counsel confirms
the statutory floor.**

Surbhi, 15 Oct 2026: *"records are kept for a year."* That settles the **business rule**. It does
not settle whether we are allowed to delete at a year, and those are two different questions.

**The caveat, stated plainly and not smoothed over.** Attendance and leave records are **payroll
records**. Indian statutory retention for wage and attendance registers is commonly longer than a
year, and **I will not state a period from memory** — I refused to earlier and the reason has not
changed. So:

- the business rule is **one year**;
- a **statutory floor must be confirmed by counsel before any deletion job runs**;
- **until it is confirmed, nothing on this path is deleted.**

**Why that asymmetry is not caution for its own sake.** Keeping data too long is a privacy finding
and it can be fixed later, by running the job once the period is known. **Deleting a wage record
below a statutory floor cannot be fixed at all**, and it surfaces in a labour inspection rather than
in a test. The baseline already names this tension — §6, erasure versus defensibility — and resolves
it the same way: legal hold on decision-bearing records, and counsel signs the boundary.

### A year from what, and over what — because "a year" alone is not implementable

**A year from what.** Two patterns are already in use in this project and the difference must not be
guessed: the recorded counsel note of 18 Sep 2026 uses **employment + N months** for performance
records, while GPS uses a flat period from the record's own date. For a payroll record my reading is
that it should run from **the date the record is about** — the attendance or leave date, not the
creation date, and not the end of employment — because that is the date a payroll register is
indexed by and the date an inspection asks about. **But that is a reading, not a ruling**, and it
goes to counsel with the floor question. *Fail-safe default meanwhile: keep.*

**Over what — four things, four arguments. They should not all get the same answer by default.**

| What | My recommendation | Why |
|---|---|---|
| The `Attendance Request` / `Leave Application` record | The business rule, once the floor is known | It is the payroll record |
| `alvoraa_grounds` and `alvoraa_grounds_source` | **Tied to the record — never a separate, shorter period** | Deleting the justification while keeping the record leaves a pay decision with no stated reason. That is worse than deleting both, because it looks complete and is not |
| The Version rows that carry the audit trail | **At least as long as the record, and plausibly longer** | You are right that it outlives what it describes. It is the only thing that answers "who did this, for whom, on what grounds" in a grievance — and **a grievance can arrive after the record is gone.** A one-year business rule may be shorter than the window in which somebody contests a deduction, which is the erasure-versus-defensibility conflict landing in one concrete place |
| The `frappe_whatsapp` message document, where PRIV-3 sent one | **The shortest of the four** | It is a second copy of personal data in another doctype, it has served its purpose once delivered, and PRIV-3 already minimised its content. Keeping it is exposure with no defensive value. **Nobody has looked at this one** — it is not in any retention decision today |

**And one thing I found while writing this that is not a decision anybody has made.** Version rows
are noted in `hrms/hrms/alvoraa_org_structure/settings.py:184-190` as **not cleared by Log
Settings** — which is why that module uses them to record access changes. The consequence here is
that **the audit trail's retention today is whatever Log Settings happens to do, inherited rather
than chosen.** Choose it deliberately, in the same counsel question.

**A disputed record is held, whatever the period says.** Legal hold on anything under dispute, and
the hold survives the purge job.

*Test:* seed an expired record, an expired-but-disputed record, and an expired record whose Version
rows are inside the audit period; run the purge; assert the first goes **with a receipt**, the
second survives on hold, and the third's audit trail survives even where the record did not. **And
the test that matters most before the floor is known:** with no confirmed statutory period
configured, **the purge job refuses to run at all** and says why — it does not default to a year, to
a guess, or to "no limit configured means delete".
*Observable only if:* the fixture can age a record past the period without waiting a year, and the
purge receipt is asserted rather than the absence of rows — "nothing found" and "deleted and
recorded" look identical in a count.
*Q2 is closed as a business rule and reopened as a legal floor — see §8 and §10.*

### Also required, and not new to this slice

**SEC-9 · Two independent conditions. Both must hold. Neither substitutes for the other.**

Surbhi, 15 Oct 2026: *"let's keep it a customizable window default to 48 hrs. else HR will do the
manual adjustments themselves in case of some genuine case."* So the bound is a **rolling window,
configurable per tenant, default **two whole working days**, with HR's manual path as the escape hatch.

**Why both conditions are now needed, where current-month-only needed one.** Current-month-only
made the paid-period half free: the current month's payroll has not run, so it could not be
touched. **A rolling 48-hour window crosses the month boundary, and a month's payroll runs in the
first days of the next.** On the 2nd, the window reaches the 31st — a day that may already be paid.
So:

**(a) The day filed for is inside the configured window.** Surbhi, 15 Oct 2026: *"Two whole working
days for the attendance correction."* So **working days, not clock hours** — default 2, per tenant,
read per request. Checked at the raise **and** at the confirmation, because a request filed inside
the window and confirmed a day later has aged while it waited, and the confirmation is the door that
writes the `Attendance` row and runs the pay engine. The refusal names the route out: *"This day is
older than the filing window. Ask HR to correct it."* — never "not allowed". It stays in the
endpoint, on the manager's path only, so HR's manual route is not bounded by it.

**(b) No submitted `Salary Slip` covers that day for that employee.** This is the rule
`payroll_reprocess.py:18` states ("NEVER TOUCH A PAID SLIP"). It is **not** a weaker restatement of
(a) and (a) is not a weaker restatement of it:

- Inside the window and already paid → **(a) passes, (b) must refuse.** The 31st on the 2nd.
- Outside the window and not paid → **(b) passes, (a) must refuse.** A missed punch from six weeks
  ago in an unrun month.

Drop either and one of those two cases goes through.

### Where each one goes, and they go in different places on purpose

**(a) the window → in the endpoint, on the manager's filing path only.** It is a rule about *when a
bounded actor may file*, and Surbhi's answer makes HR's manual route the escape hatch — so the
window must **not** be enforced on the document, or it would block the very path it depends on.

**(b) the slip guard → on the document, in `validate`.** Nobody, by any route, writes a day that was
paid: portal, desk, REST, import. Same argument as SEC-1's placement. One `doc_events` entry per
doctype in `alvoraa_portal/alvoraa_portal/hooks.py`, beside the `before_submit` wiring already
there at `:134` and `:249`. **`validate` is enough and `before_submit` is not needed:** Frappe's
`submit()` saves the document, so `validate` runs again at the submit — which is exactly how Frappe
HR relies on it for leave (`leave_application.py:125`). One hook, both moments.

### Correction: the Leave Application guard does **not** already cover this

`validate_salary_processed_days` exists, and it is called from `validate`
(`leave_application.py:125`, body at `:387-406`) — **but its first two lines return immediately
unless the Leave Type is Leave Without Pay:**

```python
if not frappe.db.get_value("Leave Type", self.leave_type, "is_lwp"):
    return
```

At DTC leave is credited 4, 3 or 2 days a month and taken against that credit — **not LWP** — so
for the common case the native guard is silent. **So (b) has to be written for both doctypes, not
only for attendance.** The asymmetry is real but smaller than it looks: `Attendance Request` has
nothing at all, and `Leave Application` has something that almost never fires here.

One shared function, called from `validate` on both. It must **not** re-implement the SQL: read the
overlapping submitted slip the same way (`docstatus = 1`, the day between `start_date` and
`end_date`), and when the native LWP guard has already thrown, this one simply never runs. Where
both could fire, the message must be one message, not two.

*Test — six, and the first two are the ones that matter:*
(a) inside the window, a submitted `Salary Slip` covers the day → **refused**, for an ordinary
    credited leave type and for an attendance correction, and assert **the guard fired** rather than
    that the call merely failed;
(b) outside the window, no slip → **refused**, by the window;
(c) inside the window, no slip → allowed;
(d) filed inside the window, confirmed after it has aged out → refused at **confirmation**, with
    the message naming HR as the route;
(e) the slip guard refuses from the **desk** and over **REST**, not only from the portal — the
    placement test;
(f) HR's own manual path is **not** bounded by the window (that is the escape hatch) but **is**
    bounded by the slip guard.
*Observable only if:* the fixture really has a `Salary Slip` at `docstatus = 1` whose date range
covers the test day, and the window tests control the clock rather than hoping to run at a
convenient hour. On a fresh test site there is no slip, so a test that only asserts "call failed"
passes for the wrong reason. **And test (a) must use a non-LWP leave type**, or Frappe HR's own
guard fires and the new one is never exercised.

**SEC-10 · The window is counted in working days, by the counter that already exists, and the
reported basis must be true.**

**Reuse `hr_may_act_from`'s counter** (`attendance_correction.py:890-936`): working days on the
**employee's own** holiday list, with a calendar-day fallback and a reported `basis` when a store
has none. One counting rule for the HR wait and for the filing window, so the two can never
disagree about what a working day is.

**One thing it cannot be reused as-is, and this is the trap.** The existing function walks
**forward** from the request date and fetches holidays for the **forward** range
`[raised, raised + 30 days]` (`:904` and `:921`). The filing window walks **backward** from today.
Reuse the counting loop, but **the holiday query range must be reversed too.** Get that wrong and
the holiday set comes back empty, the count silently becomes the calendar answer, **and `basis`
still claims "working days on this person's own holiday list"** — a refusal message that
misdescribes itself, which is lesson 5 in this project's own list: a wrong explanation sends the
next person to the wrong file. The answer would be *tighter*, so nothing leaks; the message would
be a lie, which is its own defect.

### The fallback direction — confirmed, and it cannot go the other way

**You asked me to confirm the direction, so here it is with the numbers, because a reader will
wonder.** Working days always reach back **at least as far** as calendar days, never less:

| | Walking back 2 days from today |
|---|---|
| Holiday list, yesterday was a holiday | day −1 skipped · day −2 counts (1) · day −3 counts (2) → **earliest filable day is 3 days ago** |
| No holiday list, calendar fallback | day −1 counts (1) · day −2 counts (2) → **earliest filable day is 2 days ago** |

**So the fallback is tighter, not looser, and that is the right direction** — a store whose holiday
list nobody has set up gets a slightly narrower window, not a wider one, and the failure mode of
missing configuration is a refusal rather than an opening. *(Small wording correction to the brief
you sent me: the parenthetical said the fallback "widens the window" while the clause after it said
calendar days reach back less far. The second is right and your conclusion was right; only the word
"widens" was the wrong way round.)*

**Could a missing holiday list ever widen it? No, and it is not a matter of opinion.** Skipping a
day can only push the earliest filable day further back, so `reach(working) ≥ reach(calendar)`
always, with equality when there are no holidays in the span. The same holds when the list is
present but unreadable — `hr_may_act_from` catches that and falls back to calendar (`:925-933`),
which is also the tighter side. **If a future change ever made a missing holiday list widen the
window, that is a finding, and this is the sentence to quote at it.**

*Test:* with a holiday in the backward range, a day 3 calendar days old is filable and a day 4 days
old is not. With no holiday list, 2 days old is filable and 3 is not — and `basis` **says** calendar
days. **And the test that catches the trap:** assert that a holiday in the backward range actually
extends the reach. If it does not, the range was built forward and the message is lying.

**SEC-11 · The window setting is a pay-affecting control, so changing it is governed and recorded —
but it stays with HR.**

Stored as a Frappe default read per request, the idiom at `attendance_analytics.py:41-42` and `:135`
(`TOLERANCE_KEY` / `DEFAULT_TOLERANCE_MINS`): key `alvoraa_manager_filing_window_days`, default
**2 working days**. No migration for existing tenants, which is why that idiom was chosen there and
is right here.

**My ruling on `ACCESS_GRANTING`: no, and the same protection by a different route.** You asked me
to rule rather than leave it, so:

- **`ACCESS_GRANTING`'s own comment draws the line, and it draws it against this key.**
  `hrms/hrms/alvoraa_org_structure/settings.py:85-95` says the set is for keys where "changing any
  of them can show people parts of the company they could not see before, or let them rewrite its
  structure", and then explicitly: *"The cover and span keys stay with HR — they change alerts and
  pay rules, not who can see or change anybody."* The filing window changes **when** a bounded actor
  may file, never **who** they may file for. By that boundary it stays with HR.
- **And the practical consequence decides it the same way.** `_set_access_setting` is System Manager
  only (`settings.py:184-190`). At DTC that is the two owners. **HR is exactly who knows whether 48
  hours is right** for a store that closes on Tuesdays, and making them raise a ticket to the owner
  to tune their own queue is how a control gets routed around. A control people cannot operate is
  not a control.
- **Blurring a documented frozenset is its own cost.** The value of `ACCESS_GRANTING` is that
  membership means one specific thing. Add a key that is not about visibility and the next person
  cannot trust the set.

**So: `HR Manager` or `System Manager` may change it, and a change writes a Version row** — the
`_set_access_setting` *mechanism* (`settings.py:184-190`: a real change writes a Version record in
the same transaction, and Version rows survive Log Settings) without `ACCESS_GRANTING`
*membership*. No change to `hrms/alvoraa_org_structure/settings.py` and no new frozenset.

**And a bound on the bound, which is the real security content here.** A numeric window that can be
set to anything is a control a tenant can switch off by typing a big number. Server-side, the setter
refuses a value that is not a positive integer, and refuses anything above a hard ceiling.
**I recommend 22 working days** — about one month of working days, so the outer limit is still
"something noticed within the pay cycle" rather than "managers may rewrite any month". Beyond that
it is a different capability and needs its own decision. *(This replaced a 744-hour ceiling written
against an earlier clock-hours version; same reasoning, new unit.)*

*Test:* an `HR Manager` sets it to 5 → accepted, and a Version row records who, when, old and new.
An `Employee` or a plain manager sets it → refused and logged. Set it to `0`, to `-1`, to `"abc"`
and to `365` → all four refused. Unset on a fresh tenant → `2` is used, with no migration. And the
end-to-end one: set it to 5, assert a day that was refused at the default is now accepted, with the
working-day counting still applied.

---

## 8 · Questions

### Must know

**Q1 · Agency staff: who is the data fiduciary for the 44 outsourced people?**
*My reading:* they are on Contract with five agencies. If the agency is the employer, DTC may be a
processor, a joint fiduciary, or neither for these records.
*Ambiguous:* who gives notice, who answers a grievance, and whether a DTC manager may raise a
record about an agency worker at all.
*Why it changes the control:* §6's agency row is "fail closed" because I cannot answer it, and that
may be wrong in both directions.
*Smallest question:* do the agency contracts say who holds the employment record and who answers an
employee's grievance about attendance?
*Blocks:* PRIV-3, PRIV-4, PRIV-5 for 44 of 363 people.
*Owner:* **counsel.** This is a point of law and I am not a lawyer.

**Q2a · Is there a statutory floor under the one-year business rule, and a year from what?**
*(Q2 was "what is the retention period". **Surbhi answered the business rule — one year — on 15 Oct
2026. This is what her answer does not settle**, and it is deliberately re-opened rather than marked
done.)*
*My reading:* attendance and leave are **payroll records**. Indian statutory retention for wage and
attendance registers is commonly longer than a year, and **I will not state a period from memory.**
*Ambiguous:* whether a year is permitted at all; and whether it runs from the record's own date, the
creation date, or the end of employment — this project already uses **both** shapes (GPS from the
record's date, performance records at employment + 6 months), so the pattern cannot be guessed.
*Why it changes the control:* PRIV-7's purge job cannot run without it, and the four things it would
delete have four different arguments.
*Smallest question, in three parts:* (1) is there a statutory minimum for attendance and wage
registers that is longer than a year? (2) does the year run from the record's date or from the end
of employment? (3) must the audit trail — the Version rows that record who filed and who confirmed —
outlive the record it describes, given a grievance can arrive after the record is gone?
*Fail-closed default meanwhile:* **nothing is deleted.** Keeping too long is fixable later; deleting
a wage record below a statutory floor is not.
*Blocks:* PRIV-7's purge, not the rest of PRIV-7.
*Owner:* **counsel.** This is a point of law and I am not a lawyer.

### Answered — 15 Oct 2026, by Surbhi

**Q8 · Should the notice rule exempt a leave type nobody can plan? → Yes, Sick Leave.**
*"Sick Leave as an exempt type."* **Closed, and it closes two things with it.** The exemption is a
Check on `Leave Type` (SEC-12(e)) — a property of the type, not a flag on a request, so it
reintroduces none of the override she rejected. Two consequences are now **closed rather than
open**: most of the volume stops reaching HR, and **the health need-to-know regression goes away** —
a sick day no longer has to be explained to head office in order to be taken. The second was the
stronger argument, because volume is an operational cost and that one was a privacy harm to the
person the data is about.
**SEC-13 and its permission-freeze check stay exactly as written.** The pressure to grant a manager
an HR role falls with the volume; it does not vanish, planned leave still routes to HR, and the
check costs nothing to keep.

**Q2 · How long are records kept? → One year, as the business rule.**
*"records are kept for a year."* PRIV-7 is written against it. **Closed as a business rule and
re-opened as a legal floor, as Q2a** — not marked done, because her answer settles what we *want* to
do and not whether we are *allowed* to. Attendance and leave are payroll records and I will not state
an Indian statutory period from memory. Until counsel confirms, **no deletion job runs.**

**Q3 · Which HR user approves manager-raised leave? → A cascade, not a person.**
*"HR of their department>branch>company whoever is set."* **This is a better answer than the one I
asked for.** I asked for a named person and a named deputy; a cascade with more than one approver
allowed per rung removes the single point of failure **by construction**, so there is no deputy to
forget to appoint and no stopped flow to work around. SEC-3 is rewritten as the cascade, with what
each rung needs, and with two refusals: no rung set, and every set rung resolving to the raiser.
**What remains open is only a configuration task**, not a decision: somebody must actually set at
least one rung for every employee, or SEC-3 refuses the raise. That refusal naming the three places
is the right failure, but it is a day-one setup job and it should be in the release plan.

**Q4 · Which channel reaches a blue/grey collar employee? → The manager tells them, plus WhatsApp
where the tenant has it.**
*"they will be informe by their manager or if there is any whatsapp integration then that would
go."* PRIV-3 is rewritten. The part worth repeating: **the primary channel leaves no record, and I
have not turned it into a checkbox.** A manager ticking "I told them" is an attestation nobody can
check, which produces a field that reads as evidence and is not — worse than an empty field. So
`alvoraa_employee_notified_on` records a **send**, never a claim, and where there is no send it
stays null and the HR queue says "not notified by the system". The printed-slip fallback is named,
not built, and sits in residual risk as an accepted gap.

### Should know

**Q5 · What `applicable_for` do DTC's Branch User Permission rows carry?**
`permitted_branches` (`access.py:218-251`) counts only Branch permissions whose `applicable_for` is
in `(None, "", "Employee")`. DTC's managers are configured with 44 pinned doctypes plus 7 branch
doctypes because of the AND gotcha. If those 7 name specific doctypes, `permitted_branches()`
returns `None` — which every caller reads as **unrestricted** — and SEC-6's HR scope is company-wide
without anyone choosing it. *Fail-closed default meanwhile:* require a Branch permission with
`applicable_for` empty or `Employee`; with none, HR's reach is their own company only. *Owner:*
Surbhi.

**Q6 · Who, at DTC, may edit `Employee.reports_to`, and should that be narrower now?**
It decides who may raise for whom. If every HR user may edit it, every HR user can widen any
manager's reach. I am not proposing a `permlevel` — bigger than this slice — but somebody should
decide knowingly rather than by inheritance. *Owner:* Surbhi, with the analyst.

**Q7 · Is there a named grievance officer yet?** The baseline's own open-questions table still lists
it. PRIV-5 routes to a person; without one it routes to a role. *Owner:* founder.

---

## 8a · One finding against existing code — not a `SEC` requirement, and here is why

**F-1 · Slice 059's `on_attendance_submit` judges a paid day and rewrites its verdict.
`alvoraa_portal/alvoraa_portal/payroll_rules_apply.py:419-436`. P2. Temporary debt — its own
ticket.**

**The scenario, concretely.** An `Attendance` row is submitted for a day inside a month whose
`Salary Slip` is already submitted — by a biometric sync backfill, a data import, or HR from the
desk. The hook fires, `judge()` runs, and `write_verdict()` overwrites that day's quarters and
marks. **The payslip is not changed and is not re-run.** So the attendance record now says one
thing and the money that was paid says another, and nothing anywhere records that they disagree.
`payroll_reprocess.py` refuses exactly this case on purpose — it counts `skipped_paid_slips` and
says "a correction after payment is a decision, not a recalculation" — and the hook has no such
check.

**Why it is not folded into SEC-9.** SEC-9's guard sits on `Attendance Request` and
`Leave Application`, which is the right place for *this slice's* path. The hook fires on
**`Attendance` itself**, for rows this slice never creates — biometric sync, imports, the desk. A
requirement this slice cannot satisfy by itself would be a requirement that gets marked "partial"
for ever. It is pre-existing code, pushed today, outside this slice's diff.

**Why it is not a worry either.** I can write the actor, the state, the path and the data, which is
the test for a finding. So it is a finding, with a ticket.

**P2, not P1, and what would make it P1.** It does not leak, and it does not alter a submitted
slip. It corrupts the reconciliation between what was paid and what the record says — which is the
record a grievance turns on, so it is not cosmetic. **It becomes P1 the moment a biometric backfill
or an import runs across a closed month**, and this project already has a logged trap where a
back-dated joining date made Frappe mark Absent for every day since. That is not a hypothetical
shape here.

**The smallest fix, for the ticket and not for this slice:** the hook skips a day covered by a
submitted `Salary Slip` for that employee and logs that it skipped — the same decision
`payroll_reprocess` already makes, reusing its check rather than writing a second one. Skipping is
right rather than throwing: the comment at `:420-426` is correct that a day which cannot be judged
must still be recorded.

---

## 9 · Worries — not findings

I cannot yet write these as *this actor, in this state, calling this path, sees this data*, so they
are not findings and nobody should act on them as if they were.

- **`Leave Application` ships with `All read 1`** (`leave_application.json` permissions) and there
  is no `permission_query_conditions` entry for it in either app's `hooks.py`. On the face of it
  every logged-in user could list every leave application. The ESS User Type's nine custom rows and
  the tenant's 44 pinned doctypes probably close it — ALV-117 was exactly this shape on another
  doctype — but I could not check the runtime permission rows. **Not this slice's doing, and bigger
  than this slice.** Worth its own look.
- **`Attendance` has no row filter either.** Same reasoning, same unknown.
- **Seventeen hardcoded definitions of "who is HR" in `hr_api.py`, in four variants** — lines 286,
  506, 745, 1115, 1450, 2138, 2177, 2324, 2371, 2819, 3115, 3222, 3245, 3274, 3310, 3365, 3408,
  against the canonical `HR_ROLES` in `access.py:25`. The demonstrable asymmetry: a System Manager
  may raise leave on behalf (2324) but may not open the subject's scorecard (1115); an Administrator,
  the reverse. I read the lines and the variants; I have not traced what each gates, so I cannot say
  which are exploitable. **Out of scope here, and it needs its own ticket.**
- Whether the five location managers share a login on a shop-floor machine. If they do, every
  attribution in §7 names a device, not a person, `doc.owner` stops distinguishing people, and SEC-1
  weakens accordingly. No evidence either way.

---

## 10 · What I could not verify, and what I would need

| Could not check | Access I would need |
|---|---|
| Whether `Employee` carries `track_changes: 1`, and whether `reports_to` has a `permlevel` — SEC-7(b) rests on both | `erpnext` is **not in this repo** (verified: no `employee.json` under any tracked path). I would need the installed `erpnext/setup/doctype/employee/employee.json` from a bench |
| Whether the dormant HR wait (§0, item 3) is already causing refusals at DTC today | A count, on a dev copy, of `Attendance Request` rows at `docstatus 0` whose subject's `reports_to` has a login |
| DTC's `User Permission` rows — `allow`, `for_value`, `applicable_for` (Q5) | A read-only query on a dev copy, or an export. **Not by probing production** |
| Which runtime permission rows exist for `Leave Application` and `Attendance` on a real tenant (§9) | The same dev copy |
| Whether a submitted `Salary Slip` exists for a past period on any demo tenant, so SEC-9 is observable | A count on a dev copy |
| **Whether `frappe_whatsapp` is installed on DTC's site, and whether DTC's plan has the `whatsapp` feature on.** PRIV-3 part 1 depends on both. It is **present in the production image** — `deploy/Dockerfile` ~line 76 and ~193, pinned at `08bc1f6af2e3`, registered as a sold feature at `subscription.py:403-414` — but presence in the image is not installation on a site | `bench --site dtc… list-apps` and the tenant's feature flags, read on a dev copy. Production reads are blocked in this session |
| **How many DTC employees have a WhatsApp number on their Employee record.** If the answer is "few", PRIV-3 is in practice the manager-tells-them path for almost everybody, and the printed-slip gap matters more | A count on a dev copy |
| **Whether a statutory minimum retention applies to attendance and wage registers in India, and whether it exceeds one year (Q2a).** Surbhi has answered the business rule — one year — so **Q2 is closed as a business rule and re-opened here as a legal floor with a named owner, not marked done.** I will not state a period from memory | **Counsel.** Nothing in the repo or in any source I can verify today settles it, and **PRIV-7's purge job must refuse to run until it is settled** |
| Whether the Version rows carrying this slice's audit trail are currently retained longer or shorter than the records they describe. `settings.py:184-190` says Version rows are not cleared by Log Settings, which implies longer — **but that is inherited, not chosen** | The tenant's Log Settings, read on a dev copy, plus counsel's answer to Q2a part (3) |
| Whether any Department, Branch or Company at DTC currently has a `leave_approvers` row set. If none do, SEC-3 refuses **every** manager-raised leave on day one | A count on a dev copy |

I ran no commands against any site. Everything marked **Verified in code** is a file and a line I
read in this worktree. The `reports_to` claim in §4 is a grep over every tracked `.py` in this
worktree — it does not cover the desk form or data imports, which is the point.

---

## 11 · The subtract pass

The redesign to two-party deleted a great deal by itself. On top of that, what I removed:

- **The whole bounded-vs-unbounded actor analysis** (a capacity field for HR, a mandatory
  "why HR stepped in" reason, an HR-exception ratio with a threshold and a named monthly reader).
  Two-party makes it moot: HR is the decider by design, not the exception. Dropped on instruction
  and I agree with the instruction.
- **`alvoraa_raised_on_behalf`, a separate boolean.** `alvoraa_raiser_capacity` is set only when
  the record is raised on behalf, so a value present *is* the flag. One field, not two.
- **`alvoraa_entered_by`, a separate link to the raiser.** Frappe's `owner` already holds it, and
  SEC-1 depends on `owner` anyway — a second copy would be the kind of copy that drifts, which is
  the bug `install_reasons` was written to fix.
- **A snapshot of the reporting tree on each record.** `alvoraa_raiser_capacity` and
  `alvoraa_decided_as` already freeze the two facts a grievance needs, in one word each.
- **A per-manager monthly cap on raises.** A guessed threshold with nobody to tune it, and
  two-party means every raise is read by HR before it takes effect — which is a better control than
  a number, and it is free.
- **A new `Alvoraa On-Behalf Record` DocType.** Four Custom Fields on two existing doctypes do the
  whole job — rung 3, customisation.
- **A dedicated DPIA.** A11 already gates one for the measurement engine; this is one path into an
  existing processing activity. If counsel's answer to Q1 makes DTC a joint fiduciary for agency
  staff, I would reopen it.
- **Fixing the other sixteen HR-role literals.** Named in §9, scoped out. Scope creep is
  over-engineering too.
- **A named deputy HR approver, and the "what if they are away" handling I asked for.** Surbhi's
  cascade removes the need: each rung allows more than one approver, so there is no single person to
  cover for. A rule beat a person, and the requirement got shorter.
- **Two new Link fields for the branch and company approver rungs.** Reusing Frappe HR's existing
  `Department Approver` child table on all three rungs gives one query shape and one helper. Fewer
  new things, and nothing to keep in step.
- **An "I told the employee" checkbox for the manager.** Refused on purpose, and Surbhi's answer
  does not change that: an attestation nobody can check produces a field that reads as evidence and
  is not. `alvoraa_employee_notified_on` records a send, never a claim, and where there is no send
  the field stays empty and says so.
- **A new settings page, a new DocType or an HR Settings field for either setting.** A Frappe
  default read per request — the `attendance_analytics.py:41-42` idiom — needs no migration and no
  new surface. SEC-11 adds governance to it, not a home for it.
- **A second working-day counter.** SEC-10 reuses `hr_may_act_from`'s, so the HR wait and the filing
  window cannot disagree about what a working day is. The only new code is reversing the walk and
  its holiday range.
- **Two more settings for the notice rule's thresholds.** One switch; the numbers are the rule as
  Surbhi stated it. A tenant wanting different numbers is a new decision, not a feature to
  pre-build.
- **An emergency flag, a reason field or a per-request override on the notice rule.** Surbhi chose
  HR as the only exemption, and the Sick Leave exemption is a property of the **type** rather than
  an override on a **request**, so none of the three comes back.
- **A setting naming the exempt leave types.** A Check on `Leave Type` beats it: no second copy of a
  list of names to drift, one read instead of a parse, and a tenant with two sick-leave-like types
  can mark both. SEC-12(e).
- **Four separate retention settings for the four things PRIV-7 covers.** PRIV-7 gives four
  *recommendations* and one *question to counsel*, not four configurable periods. The periods are a
  legal answer, not a product feature, and three of the four should simply follow the record.
- **A new CI gate for the canonical `HR_ROLES` read in SEC-12.** SEC-8's assertion 4 already fails
  any literal containing both `"HR Manager"` and `"HR User"`. Already there; nothing to add.
- **`ACCESS_GRANTING` membership for the filing window.** Ruled against in SEC-10: the set's own
  comment draws the line against it, and System-Manager-only would stop HR tuning their own queue.
  The *mechanism* (role check plus Version row) is kept; the membership is not.
- **A separate `before_submit` hook for the paid-period guard.** Frappe's `submit()` saves the
  document, so a `validate` hook already fires at the submit. One hook, both moments.
- **A second copy of the overlapping-slip SQL.** The shared function reads it the same way
  `validate_salary_processed_days` does rather than inventing a second query that can disagree.
- **Folding F-1 into SEC-9.** It fires on `Attendance` rows this slice never creates, so a
  requirement here could only ever be marked "partial". Its own ticket, §8a.
- **Building the printed acknowledgement slip in this slice.** It is the only thing that would
  evidence a manager's conversation, and nobody has asked for that evidence yet. Named in PRIV-3,
  accepted as a gap in residual risk, not built.

What I did **not** remove, though they cost the most: **PRIV-3 and PRIV-4** — telling the employee,
and letting them get a print. They answer "prove it" in a grievance, and two-party made PRIV-3
cheaper rather than less necessary, because HR's confirmation queue is already a screen somebody
opens.

---

## Open questions

See §8. **Q2, Q3, Q4 and Q8 are all closed** — Surbhi answered them on 15 Oct 2026, and SEC-3,
SEC-12, PRIV-3 and PRIV-7 are rewritten accordingly.

**Still must-know, and both are for counsel:**

- **Q1 — agency staff fiduciary.** Blocks PRIV-3 to PRIV-5 for 44 of 363 people.
- **Q2a — is there a statutory floor under the one-year rule, and a year from what?** Blocks
  PRIV-7's **purge job**, not the rest of PRIV-7. **Q2 is closed as a business rule and re-opened
  here as a legal floor** — that is deliberate, not bookkeeping. Her answer settles what we want to
  do; it does not settle whether we may.

**Two things the answers left behind, neither of them a decision:**

- **A day-one configuration task.** At least one `leave_approvers` rung must be set for every
  employee before a manager can raise leave for them, or SEC-3 refuses the raise. The refusal naming
  the three places is the right failure, but it belongs in the release plan rather than in a support
  ticket on the first morning.
- **A second day-one task:** Sick Leave must actually be marked exempt (SEC-12(e)) before the notice
  rule is switched on, or the regression the exemption closes re-opens on the first sick day.

## Assumptions

- `[ASSUMPTION]` `Employee` carries `track_changes: 1` and `reports_to` has no `permlevel`, so any
  holder of write on Employee may change it and the change leaves a Version row. **`erpnext` is not
  in this repo and I could not read the file** — SEC-7(b) rests on this and must be checked against
  the installed app before it is called met.
- `[ASSUMPTION]` `doc.owner` is the raiser on every path this slice creates. True for `doc.insert()`
  under a session; **not** true for a data import or a job run as Administrator. SEC-1's docstring
  must say so.
- `[ASSUMPTION]` One tenant per site, so cross-tenant leakage is not reachable. Consistent with
  baseline §3a and with how slice 030 scopes; I did not re-verify the site layout.
- `[ASSUMPTION]` The capability is portal-only — no new desk form, no new public page, no
  `allow_guest`. A desk form would need §6 and SEC-5 re-read, because the desk reaches these
  doctypes by a different door.
- `[ASSUMPTION]` A `Department Approver` child table can be attached by Custom Field to `Branch` and
  `Company`. It is `istable: 1` with one required `approver` Link to User and
  `ignore_user_permissions: 1`, and nothing in its JSON constrains its parent
  (`hrms/hrms/hr/doctype/department_approver/department_approver.json`) — but **I have not built it
  and tried it.** If a Table Custom Field on an ERPNext doctype misbehaves, SEC-3's rungs 2 and 3
  fall back to two plain Link fields, which is the alternative SEC-3 already names.
- `[ASSUMPTION]` `frappe_whatsapp` being in the image means it *can* be available per tenant, not
  that it is on for DTC. §10 says what would settle it. PRIV-3 is written so the feature being off
  is a normal, visible state rather than a failure.
- `[SETTLED by Surbhi, 15 Oct 2026]` SEC-9's date bound is **two whole working days, configurable
  per tenant**, with HR's manual route as the escape hatch. Not clock hours and not calendar months.
  **So this slice gets two new settings** — `alvoraa_manager_filing_window_days` (default 2) and
  `alvoraa_leave_notice_rule_enabled` (absent means off) — both as Frappe defaults, neither a new
  DocType or settings page. SEC-11 governs how they may be changed and caps how far the window may
  be opened.
- `[ASSUMPTION — needs Surbhi's word before build]` SEC-12's notice rule binds **everyone**, not
  only managers acting on behalf. *"for the leave application"* reads that way, and the coordinator
  read it the same way. **If that is right, this part of the slice is a restriction on all 363
  people rather than a new capability**, and it should be said in those words rather than discovered
  at release. If she means it only for manager-raised leave, SEC-12's scope note and both of its
  residual-risk rows shrink considerably.

## Residual risk

| Risk | Why it remains | Who must accept it | Date |
|---|---|---|---|
| A manager and an HR user acting together, or an HR user confirming without reading, can still change somebody's pay without asking them. Two-party reduces this; it does not remove it | Inherent to the design. PRIV-3 and PRIV-4 are the counterweight, and they put the employee in the loop after the fact rather than before | **Surbhi** | open as of 2026-10-15 |
| `reports_to` decides who may raise for whom, and the `leave_approvers` rows decide who confirms. Both are editable by every HR user with no approval, so one person can set both ends of a two-party control | Follows from today's deliberate backfill and from SEC-3's cascade. SEC-7(b) records the changes; it does not gate them. Q6 | **Surbhi** | open as of 2026-10-15 |
| **The employee's notice is given by their manager in conversation, and the system cannot evidence it.** Where WhatsApp is off or there is no number, nothing proves a specific person was told | Accepted deliberately: the alternative is a checkbox that attests to something nobody can check, which is worse. PRIV-3 names the printed-slip mechanism that would close it, and it is **not built in this slice** | **Surbhi** | open as of 2026-10-15 |
| CERT-In 180-day India-resident log retention is unmet, so the refusal and raise log lines do not sit where that direction requires | Pre-existing, baseline §3a, out of scope here | **founder** | open, recorded 6 Sep 2026 |
| Field sensitivity classification (A1) is not built, so §5's classes are applied by hand and a later field can be added without one | Pre-existing, P0 on the feature map, status `?` | **Surbhi** | open as of 2026-10-15 |
| No named grievance officer, so PRIV-5 routes to a role | Pre-existing, baseline open question | **founder** | open as of 2026-10-15 |
| **With the leave notice rule on, every sick day at DTC routes to HR — two people for 363 staff across six branches.** An exemption everybody needs daily stops being an exemption, and the predictable relief valve is to grant branch heads an HR role, which **silently defeats SEC-3, SEC-5, SEC-6 and SEC-12's audit trail at once** | Surbhi chose HR as the only exemption over an emergency marker. SEC-13 turns the role grant into a line of check output rather than a surprise; it does not prevent it. **Q8 (exempting Sick Leave) is the cheaper fix and would remove most of the volume** | **Surbhi** | open as of 2026-10-15 |
| **The leave notice rule changes leave for all 363 people, not only manager-raised leave.** Planned leave now needs a week's notice for everybody | Follows from the rule as stated. SEC-12 records the scope reading as an assumption to be **confirmed with Surbhi before build** | **Surbhi** | open as of 2026-10-15 |
| ~~Genuine sick leave becomes structurally non-compliant, so an illness must be explained to HR to be taken — a need-to-know regression on health-adjacent data~~ | **Closed 15 Oct 2026.** Sick Leave is an exempt type (SEC-12(e)), so a sick day no longer routes to HR and no longer has to be explained to head office | — | closed 2026-10-15 |
| **No deletion job may run until counsel confirms the statutory floor under the one-year business rule (Q2a).** Until then this slice keeps attendance and leave data longer than the business rule says | Deliberate, and the cheaper wrong of the two: keeping too long is a privacy finding fixable by running the job later; deleting a wage record below a statutory floor cannot be fixed and surfaces in a labour inspection | **counsel**, then **Surbhi** | open as of 2026-10-15 |
| **A one-year business rule may be shorter than the window in which somebody contests a deduction**, so the audit trail that defends the decision could be gone before the grievance arrives | The erasure-versus-defensibility conflict in baseline §6, landing in one concrete place. PRIV-7 recommends the audit trail outlives the record; **counsel must say so**, because today its retention is inherited from Log Settings rather than chosen | **counsel** | open as of 2026-10-15 |
| **F-1: slice 059's `on_attendance_submit` rewrites the verdict on a day that was already paid** (§8a). The attendance record and the payslip disagree and nothing says so | Pre-existing code outside this slice's diff, fires on rows this slice never creates. **P2, and P1 the moment a biometric backfill or import crosses a closed month.** Needs its own ticket, not a `SEC` row here | **Surbhi** — it is her commit from today | open as of 2026-10-15 |
| **If WhatsApp notification ships, Meta becomes a sub-processor for DTC's employee data.** The sub-processor register and tenant-visible change notification (feature-map A9) do not exist, and the privacy notice does not say so | New, and it follows from Q4's answer. PRIV-3 keeps the message minimal so the disclosure is small; it does not remove the disclosure | **founder** (register and notice) | open as of 2026-10-15 |

An accepted risk with a name and a date is governance. **None of these six has a name against it
yet. They are not accepted; they are open.**

## Handoff note

To `hrms-business-analyst`: trace all twenty requirements — SEC-1 to SEC-13, PRIV-1 to PRIV-7 —
to acceptance criteria, plus finding F-1 in §8a to its own ticket, or record
Surbhi's decision not to adopt one. Four things to watch.

**First, §0's three items are what to read if you read nothing else.** The two-party rule is not
enforced anywhere today (SEC-1); today's `leave_approver` configuration deadlocks the new design
(SEC-3); and today's `reports_to` backfill makes HR wait two working days on every manager-raised
correction (SEC-4). The second and third are consequences of work done this afternoon, not of this
design.

**Second, SEC-4 changes live code behaviour** and SEC-1 adds a refusal that will fire on paths
people use today. Both need their own story and their own line in the release notes. Do not fold
them into the new feature's story.

**Third, SEC-3 is now a cascade and it has a setup job attached.** Department, else branch, else
company — first rung that is set. Rung 1 is configuration on a Frappe HR feature that already
exists; rungs 2 and 3 need two Custom Fields reusing `Department Approver`. **If no rung is set for
an employee, the raise is refused** — which is the right failure, but it means somebody must set at
least one rung for all 363 before this ships. Put that in the release plan, with a check that counts
employees with no reachable approver.

**Fourth, SEC-9 is two conditions and they are enforced in two different layers.** The window goes
in the endpoint, because HR's manual route must stay unbounded — that is the escape hatch Surbhi's
answer depends on. The paid-period guard goes on the document, because nobody writes a paid day by
any route. Do not let them collapse into one check in one place: the §8a note and SEC-9's six tests
say which case each one catches alone. **And note the correction in SEC-9:** Frappe HR's
`validate_salary_processed_days` only fires for Leave Without Pay, so it does **not** already cover
DTC's credited leave — the guard must be written for both doctypes.

**Fifth, SEC-10 and SEC-11: the window is two whole working days, counted by the counter that
already exists.** Reuse `hr_may_act_from`'s loop so the HR wait and the filing window cannot
disagree about a working day — **but reverse its holiday query range as well as its walk.** Leave
the range pointing forward and the count silently becomes the calendar answer while `basis` still
claims the holiday list was used: tighter, so nothing leaks, but a refusal message that lies. SEC-10
has the test that catches it. The settings are capped at 22 working days, because a numeric control
over a pay-affecting window with no ceiling is a control a tenant can switch off by typing a big
number.

**Sixth, SEC-12 is the one requirement in this file that takes something away from people rather
than giving it.** Three things must survive the spec: **unset means off** (the opposite read from
every other setting here, and getting it wrong switches a restriction on for every tenant by
deploy); **the exemption keys on the stored capacity, not the live session role**, because `validate`
runs under background jobs and Administrator imports where a session role test fails in both
directions; and **the scope reading is an assumption**, not a settled fact — confirm with Surbhi
whether the rule binds all 363 or only manager-raised leave before anybody builds it.

**Seventh, SEC-13 is a tripwire for a reversal nobody will intend, and it stays.** Granting a branch
head an HR role defeats SEC-3, SEC-5, SEC-6 and SEC-12's audit trail together — one grant, four
requirements. **The Sick Leave exemption cuts most of the pressure, which is why it won over
policing the valve, but planned leave still routes to HR and the check costs nothing.** Keep it in
the existing permission freeze check. **And put two things in the release plan:** Sick Leave must be
marked exempt *before* the notice rule is switched on, and at least one `leave_approvers` rung must
be set for every employee *before* a manager can raise leave at all.

**Eighth, PRIV-7 has a gate in it, not just a period.** The business rule is one year; the statutory
floor is unconfirmed; **so the purge job must refuse to run and say why, rather than defaulting to a
year or treating "no period configured" as permission to delete.** That refusal is the requirement,
and its test is listed. Do not let a spec turn "one year" into a configured number with no gate in
front of it — deleting a wage record below a statutory floor is the one mistake in this file that
cannot be undone.

**Ninth, SEC-6 carries a fix to existing code with six callers** (`_hr_target_employee` scoping by
company and not branch). It is not strictly part of the new capability and it is the
highest-leverage line here. Put it in the spec as its own story, because the new path inherits the
gap if it is left.

To `hrms-fullstack-engineer`: the pattern to copy is `attendance_correction.py` — no
`ignore_permissions`, the framework asked rather than roles named, capacity derived server-side,
refusals logged in one shape. Not `hr_api.apply_leave`, whose on-behalf insert uses
`ignore_permissions=True` and a hand-rolled `frappe.db.commit()` on a path that moves money.

I disagree with nothing above me, because nothing is above me yet — the brief is being written in
parallel. If the brief asks for anything that lets one person both raise and confirm, SEC-1 is
where to argue it out.

---

## SEC-9(a) settled — Surbhi, 18 October 2026

Two things in SEC-9(a) could not both be built as written. Both are now decided, and the
code already matches. **Do not reopen either without her.**

> **Reopened and re-decided the same evening, after she tested it live. Read
> "SEC-9(a) reworked" at the end of this section before acting on anything
> below: the default window changed, and so did what a blank one means.**

### 1. A filing window of `0` means TODAY ONLY, not "nobody may file"

This file said *"0 means nobody may file on behalf"*. It does not. `0` is the tightest
window: the manager may still correct **today's** day, and nothing older.

**Why.** The setting is a count of days, and the smallest number must mean the smallest
window. If `0` meant "switched off", somebody tightening 5 → 2 → 1 → 0 would expect each
step to be stricter and instead fall off a cliff into a different kind of rule altogether.
A number box that silently becomes a permission is a trap, and the person who sets it would
have no way of knowing.

Turning the capability off for a tenant is a separate switch with its own label, if it is
ever wanted. It is not a `0` hidden in a day count. **It was wanted the same evening —
that switch is built, and the rework below describes it.**

Pinned by tests: `0` accepts today and refuses yesterday, and a **stored** `0` is not read
as unset — `0` is falsy in Python, so `get_default(KEY) or DEFAULT` would have silently
turned it back into 2.

### 2. The window is checked when the manager RAISES, and never when HR CONFIRMS

This file asked for the window to be checked at the raise **and** at the confirmation,
while also saying the window must not bind HR. Those contradict, and following both
literally produces requests that can be raised but never approved:

> Monday — the manager raises Friday's missing punch. Inside the window, accepted.
> Thursday — HR opens the queue. Friday is now more than two working days old, so a check
> at confirmation refuses it. The manager did nothing wrong and has no way to fix it.

That would punish HR's queue time, not the thing the window exists to prevent.

**Surbhi, 18 Oct 2026:** *"the window doesn't apply to HR. This actually takes care of any
worst case scenario and also management discretion in some edge cases."*

So the window is a limit on the **manager's** reach, and HR is the deliberate way round it
— the escape hatch for a genuine old correction and for management discretion. `decide()`
is unchanged and must stay unchanged.

### What this does NOT include

**No paid-period guard**, decided the same day. DTC pay in the first week of the following
month *after* a thorough attendance review, so a correction filed in that window is exactly
what the review is for. The guard is not built and must not be added as a precaution.

---

## SEC-9(a) reworked — Surbhi, 18 October 2026, after testing it live

**This section wins over anything earlier in this file about the filing window's default.**
It reverses two decisions taken that same day: the default of two working days, and
blank meaning two. Her words:

> "it should be a setting per tenant in the organisation setting. First setting: allow
> manager to approve request for attendance and leaves on behalf of their reporting
> [staff]. with sub setting - how many working days is allowed for manager to raise
> approval request, default to blank meaning no limit. this will keep it flexible for an
> organisation to decide."

### What a tenant now has

| Setting | Key | Values | Default |
|---|---|---|---|
| **The switch** — may a manager raise a request on behalf of their direct reports at all | `alvoraa_manager_on_behalf_enabled` | `1` on, `0` off | **ON**, and unset counts as on |
| **Its sub-setting** — how far back that manager may reach | `alvoraa_manager_filing_window_days` | blank = **no limit**, `0` = today only, `N` = N working days back | **blank** |

Both are set by HR with company-wide permission in Organisation Settings → Attendance
rules, through `hr_api.set_org_setting`, which holds them on its allow-list. Neither is a
new DocType and neither is a new endpoint.

### Why the switch defaults to ON

The capability already ships and DTC's managers use it. A switch that failed closed would
take a working screen away from every existing tenant the moment it was added, silently,
with nobody having chosen that. So the reader treats unset as on, and only a stored `0`
switches it off. This is deliberately **not** `org_features.org_switch`, which fails closed
— right for a rule that deducts pay and starts off, wrong for something people already have.

### Why blank means no limit

Her words, and the reason behind them: the tenant decides. Two working days was the
product imposing a policy on organisations that never asked for one. HR remains the way
round an old day either way.

**`0` still means today only.** That part of the earlier decision stands, and blank and `0`
are now at opposite ends of the same box — so the reader must keep them apart. It does:
`frappe.db.get_default(KEY) or DEFAULT` is still banned here, because a stored `0` is falsy
and would be read as "no limit", which is the loosest answer there is. Pinned by
`test_blank_and_zero_are_never_confused`.

### Where the two settings are enforced, and they must agree

| Place | What it answers | How |
|---|---|---|
| `raise_for_report` | the guard | the switch is checked inline, then `_refuse_outside_filing_window()` |
| `month()` | may this screen offer a form, and from which day | `can_request`, `on_behalf_enabled`, `can_request_from` |
| `team_days()` | may this row offer a button | `can_raise`, per person **and per day** |

All three read the same two functions, and the boundary comes from one call,
`manager_filing_from()`. A boundary worked out twice is one that drifts, and then the screen
offers a day the server throws on — which is exactly what happened on 18 October.

### One more thing settled here: HR does not raise, on either screen

`month()` withheld the form from HR; `team_days()` handed HR a button on every row. The same
HR user got two different answers, found by pressing it live. **Settled as direct reports
only, for everybody, HR included.** HR decides every request, and their own route — the
Attendance Request itself — is deliberately outside the window. `decide()` refuses a person
deciding their *own* record, not a person deciding what they themselves raised, so the only
thing keeping HR's two hats apart is not offering the button.

### Still not included

**No paid-period guard.** Unchanged, and still her decision. **`raise_correction` is
untouched**: neither setting may narrow what somebody asks about their own attendance, and a
test says so.
