---
slice: 042-redesign-wave2
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-09-24
revision: 1
status: draft — written after the functional spec, which is the wrong order and is said so below
inputs: [02-functional-spec.md (042, revision 1), ../034-redesign-wave1/01c-security-privacy-requirements.md revision 4, ../034-redesign-wave1/06-security-review-of-requirements.md, ../034-redesign-wave1/00g-decision-register.md (W1D-01 to W1D-21), ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, .claude/context/security-compliance-baseline.md, docs/legal/2026-09-18-retention-and-driver-tracking-proposal.md, the code at origin/dev 8718f27 read in this worktree on 2026-09-24]
---

# Wave 2 — Home and Inbox: security and privacy requirements

**Numbering is per slice.** This slice runs `SEC-1` to `SEC-16` and `PRIV-1` to `PRIV-9`.
Wave 1 has its own `SEC-1` and it is a different thing. Cite them as **"042 SEC-4"** and
**"034 SEC-4"**. Decisions are cited as `W1D-nn` from
`../034-redesign-wave1/00g-decision-register.md`, and the two sets in `00f` as "009 design
decision n" and "009 strategy decision n".

**Every claim below carries a label.** *Verified in code* means I opened the file and read
the line, and the file and line are named. *Inference* says what it rests on. `[ASSUMPTION]`
is a working guess. *Unknown* means I could not check it, and says what access I would need.
Worries are in their own list at the end and are not requirements.

---

## Said first, because it changes how this document should be read

**1. This document arrives after the spec, not before it.** The process puts `01c` ahead of
`02` for a reason: a control stated as a requirement is built once; a control found at
review is built twice. Here the analyst wrote `02` first and marked the slice not ready for
exactly this reason. In this case little is lost — the spec is unusually careful about
negatives — but **four requirements below are not in the spec, and the spec must change
before code**: SEC-9, SEC-12, PRIV-2's minimum-n rule and PRIV-4. They are listed in the
verdict.

**2. Wave 2 depends on code that does not exist.** *Verified in code:*
`alvoraa_portal/alvoraa_portal/` at `8718f27` contains no `frame_api.py` and no
`inbox_api.py`. Every "Wave 1 SEC-n covers this" claim in the spec is a claim about unbuilt
code. **This document assumes nothing from Wave 1 is in place** and restates the controls
Wave 2 needs rather than inheriting them. Where Wave 1 genuinely ships the control first,
the Wave 2 test still runs — a duplicate test is cheaper than a control nobody owns.

**3. Wave 2's biggest risk is not a leak. It is a control that looks present.** Three of the
four lessons Wave 1 paid for are about exactly that: an empty filter dict that means
everybody, a hidden menu entry mistaken for a permission, and a test fixture that patches
the feature gate to "on". All three are re-armed in this slice. SEC-4, SEC-5 and SEC-9
exist to stop them.

---

## Threat model — four questions, answered for this slice

**1 · Who would want this data, and what is the cheapest way to get it?**
Not an outsider. The three cheapest attacks are a **curious colleague** who wants to know
why a co-worker is away and reads the peer card's numbers day after day; an **over-scoped
HR user** whose store filter is missing from one of seven count parts; and a **leaver with
an enabled login** who keeps reading a queue. None of them needs a tool. The cheapest path
of all is a whitelisted endpoint called by hand after the card that used it was taken off
the screen — `get_week_presence` is that endpoint today (SEC-9).

**2 · What is the blast radius of one mistake?**
The Inbox count is built from one helper every persona shares. A missing filter in `parts()`
is not one person's mistake — it is **every HR user on every tenant seeing every employee's
work**, in a number they are trained to trust. That is the top of the scale short of
cross-tenant. Home is narrower: its payload is the caller's own, so a mistake there leaks
the caller's own data into logs and screenshots rather than to a colleague — **which is
still the exact shape of Wave 1's worst finding.**

| Scale | What sits here in Wave 2 |
|---|---|
| Cross-tenant | Nothing — **provided** no new module keeps a module-level cache (SEC-13). One worker serves several sites |
| Whole tenant | A missing scope in one of the seven `parts()` filters (SEC-3); the peer query falling back to a whole department (SEC-9) |
| One manager's line | A context line carrying a colleague's name or leave type (PRIV-3) |
| One person | Home's own-data payload reaching a log or a screenshot (SEC-2) |

**3 · What does this make possible that was impossible before?**
Three things. (a) **Aggregated absence, refreshed daily**, on a card every colleague sees —
a new inference channel, not a new field (PRIV-2). (b) **A list of new joiners**, which is a
small, cheap piece of profiling of the newest and least powerful people in the building
(PRIV-4). (c) **Decide-in-place**, which moves a decision about a person from a form opened
deliberately to a row tapped quickly. Nothing is automated — but a decision taken in two
seconds needs the same reason and the same audit entry as one taken in two minutes (PRIV-7).

**4 · How would we find out?**
**We would not.** Refusals go through `access.log_refusal` (*verified in code*,
`hrms/hrms/alvoraa_hr_core/access.py:27`). **A successful over-read leaves no signal at
all**, nobody reads the security log, and nothing alerts on it. This is Wave 1's residual
risk R3, still open, now carrying more traffic. In Wave 2 the tests are the only detection,
and a count that is silently too large looks exactly like a busy week.

---

## Data inventory

Every field or object Wave 2 puts on a screen or in a payload, with its class, purpose,
retention and audience. **A field that is not in this table must not be in a payload.**

| Data | Where | Sensitivity class | Purpose | Kept | Who may see it |
|---|---|---|---|---|---|
| Caller's `employee`, `employee_name`, `designation`, `department`, `image`, `company` | `get_home.me` | Personal, low | Show who is signed in | Not stored by Wave 2 | The caller |
| Caller's `date_of_birth`, `gender`, `cell_number`, `date_of_joining`, `reports_to`, `branch` | **Never in any Wave 2 payload** (SEC-2) | Personal, higher | — | — | — |
| Caller's shift today, check-in time | `get_home.today` | Personal, low | Check in | Existing Employee Checkin retention, unchanged | The caller |
| Caller's leave balances by type | `get_home.leave` | **Sensitive** — a leave type implies a medical or family circumstance | Administer leave | Unchanged | The caller only |
| Caller's own holiday list | `get_home.holidays` | Personal, low | Plan | Unchanged | The caller |
| Caller's attendance-gap days | `get_home.needs` | **Sensitive** — a pattern of absence can imply health, caring duties or religious observance | Let the person fix an unpaid day | Not stored; computed live | **The caller only.** No manager-facing gap list in Wave 2 (PRIV-5) |
| Caller's self-review state (status only) | `get_home.needs` | Personal, higher | Remind | Not stored | The caller |
| Peer presence as **counts** (in / away / still to come) | `get_home.team_today` | **Sensitive by inference** below a minimum group size | Let a team see who is on the floor | Not stored | Peers in the caller's own peer group (PRIV-2) |
| Colleague absence **reason** or leave **type** | **Nowhere, in any state, on either screen** | Sensitive | — | — | — |
| New joiners: name, designation, joining date | `get_home.celebrations` | Personal, low — but it is profiling of named individuals | Welcome | Not stored | Per PRIV-4's scope |
| Caller's own work anniversary | `get_home.celebrations` | Personal, low (from `date_of_joining`) | Recognise | Not stored | The caller |
| Birthdays | **Nowhere.** Not in a payload, not behind a flag, not commented out | Personal | — | — | — |
| Counts of pending items, by part | `get_nav_counts`, `get_inbox` | Aggregate — shows that work exists, never whose | Tell a person work is waiting | Not stored | The caller, for their own scope |
| Approval rows: kind, date range, requester's name | `get_inbox` rows | Personal, higher | Take a decision about a person | Not stored by Wave 2; the source document keeps it | Only the person entitled to decide it |
| A decline reason | Written to the source document by the existing action | Personal, higher | Tell the person what to do next | The source doctype's existing retention | The requester and the decider |
| "Your payslip is ready", with a take-home figure | `get_home.needs` (prototype row f) | **Sensitive** | Tell the person a slip exists | Not stored | **The caller only, on a tenant with `plan_payroll`** (PRIV-6) |
| Theme and layout choice | Browser storage | Preference | — | That device only | — |

**Nothing new is collected and nothing new is stored.** *Inference, resting on the spec's §8
and §14 and on my own read of the endpoints it reuses.* What is genuinely new is
**aggregation** — see PRIV-2.

---

## Who must NOT see what

| Who | Must not see |
|---|---|
| Any employee | A colleague's absence reason, leave type, or any number small enough to name one (PRIV-2, PRIV-3). Another person's attendance gaps. Another person's goal figure |
| Any employee | Their own `date_of_birth`, `gender`, `cell_number` **in a payload** — not because it is secret from them, but because the payload reaches logs, screenshots and error reports (SEC-2) |
| A manager | Anyone outside their own line downwards. A report's loss-of-pay **amount** (Q-b, 14 Sep). A report's attendance gaps as a list |
| Store HR | Anyone outside **their store plus their own reporting line** (W1D-07) — in every one of the seven count parts, every Inbox list, the Home team card and the team goal summary. An employee with no branch is outside every store (slice 030, DEF-6) |
| Company-wide HR | People and items outside their permitted companies |
| A non-HR reviewer holding submit on Attendance Request | Unchanged by this slice (W1D-14) — a **recorded gap**, not a control (SEC-8) |
| A leaver (Employee not Active) with an enabled login | Any colleague, any approval count, any queue row. Their own still-open requests are the one thing they keep (SEC-11) |
| Anyone at all | Another person's payslip or take-home, in any state, including HR (PRIV-6) |
| A tenant without `plan_payroll` | The payslip row, **and the endpoints behind it** (SEC-5) |
| Guest | Anything. Every new endpoint refuses Guest |

---

## Obligations engaged, with the date each was last verified

**None of these is stale.** The baseline's oldest entry relied on here was verified 24 Aug
2026 — 31 days old at the time of writing, inside the 90-day rule; its hosting section was
re-verified 6 Sep 2026. **I am not a lawyer and none of this is legal advice.**

| Obligation | Source, and the date it was verified | What Wave 2 must do | Requirement |
|---|---|---|---|
| DPDP Act 2023 s.8 — minimisation and reasonable safeguards | baseline §2 and §5, verified 24 Aug 2026. Rules notified 14 Nov 2025; Data Fiduciary duties phasing to about May 2027 ⚠ counsel to confirm | Send only what the screen draws | SEC-2, PRIV-1 |
| DPDP — purpose limitation | baseline §2, verified 24 Aug 2026 | Attendance data collected for pay must not become a colleague-visible absence signal | PRIV-2, PRIV-5 |
| DPDP — access rights on every path | baseline §2 and §4, verified 24 Aug 2026 | Every queue and every count scoped on the server | SEC-3, SEC-4, SEC-7, SEC-8 |
| CERT-In Directions 28 Apr 2022 — log content, 180-day retention | baseline §3, verified 24 Aug 2026; residency gap re-stated 6 Sep 2026 | Logs carry identifiers, never personal content | PRIV-8 |
| OWASP ASVS 5.0 L2 — access control and output encoding | baseline §5, verified 24 Aug 2026 | List and action share one scope; everything drawn is escaped | SEC-7, SEC-12 |
| Counsel's retention proposal, 18 Sep 2026 | `docs/legal/2026-09-18-retention-and-driver-tracking-proposal.md` | **Not engaged** — Wave 2 creates no record. Stated rather than skipped | PRIV-9 |
| EU AI Act; GDPR Art 22 | baseline §4, verified 24 Aug 2026 | **Not engaged** — nothing in Wave 2 is AI-shaped and no decision is automated. Wave 3 is where that bites | — |

---

## Abuse cases

| # | Actor, state and path | What must happen |
|---|---|---|
| **A1** | **A curious colleague** watches the peer card every day for a fortnight and notices the "away" number rise each Tuesday in a four-person team | **No numbers at all below the minimum group size** (PRIV-2). Above it, counts only, with the sentence saying the card never says why |
| **A2** | **An employee** calls `get_week_presence` by hand after Wave 2 has removed the card that used it | **The endpoint must be gone or scoped** (SEC-9). *Verified in code* (`hr_api.py:3151-3190`): it is whitelisted, returns **named** rows with `employee_name`, `designation` and `image` plus a per-day in/away/due/off state, and **falls back to the caller's whole department, capped at 40, when the caller has no direct reports** (`:3179-3186`). Narrowing the card while leaving this callable narrows nothing |
| **A3** | **A store HR person** loads the Inbox and reads the count | Their store plus their own reports, in **all seven parts**, and the same in every list (SEC-3) |
| **A4** | **A store HR person** meets a part added later that was never given a scope | The structural test fails before release: a part with no declared scope helper is a test failure, not a runtime default (SEC-3) |
| **A5** | **An HR user on a tenant without `plan_payroll`** calls the payslip-row endpoint by hand | Refused **on the server**, with wording identical to a not-entitled refusal (SEC-4, SEC-5) |
| **A6** | **A leaver** whose login is still enabled opens the Inbox that evening | Zero approvals, no queue rows, empty team card; his own still-open requests remain (SEC-11). ERPNext does not disable the User when an Employee is set to Left — checked in Wave 1's review against `erpnext/setup/doctype/employee/employee.py` |
| **A7** | **Asha**, a platform operator with **no Employee record**, loads Home and Inbox | Every part returns **0** and every list is empty, by an explicit early refusal — never by a filter that was skipped because there was no employee to filter on (SEC-14). This is the fail-open shape and it is the one that hurts |
| **A8** | **A manager** taps Approve on a row he is not entitled to, by replaying the call with another document's name | Refused by the same scope function that decided whether to draw the row (SEC-7) |
| **A9** | **Anyone** approves their own request — own leave, own correction, own shift request, own goal update, own KPI update | `access.refuse_own_decision` refuses all five (*verified in code*, `access.py:63`), the refusal is logged with no personal content, and no document is written (SEC-6) |
| **A10** | **A support engineer** reads an error report sent from a phone | It carries the caller's name and job title and **no** date of birth, gender or phone number (SEC-2) |
| **A11** | **Somebody who may create a Designation** names one `<img src=x onerror=alert(1)>`, and it appears in a queue row | Drawn as text; no element created (SEC-12) |
| **A12** | **A test author** patches the feature gate to "on" in a fixture, and every entitlement test goes green | **The gate tests must call the real `subscription.has_feature`** and assert the refusal, on a tenant whose `features` list genuinely lacks the key (SEC-5). A patched gate proves nothing, and this has already happened once in this repo |
| **A13** | **A new joiner** finds themselves listed on 400 colleagues' Home screens on their first day | The joiners list is scoped, time-boxed and Active-only, and **PRIV-4's question about declining is answered before it ships** |
| **A14** | **An employee** infers a colleague's absence from "your team today: 5 in, 1 away" on a six-person team, then looks around the floor | **Accepted and stated.** Physical co-presence already discloses it. The control is that the product adds no *reason*, no *history* and no *trend* — PRIV-2 bounds what the product contributes, not what a workplace reveals. Residual risk R6 |
| **A15** | **A store HR person** whose Branch User Permission is narrowed to a single doctype | `access.py:233` treats them as company-wide (`applicable_for in (None, "", "Employee")` fails open). **Unchanged by Wave 2 and carried as R4** |

---

## Requirements

Each says what must be true and **how it will be tested**. Where an existing `042 AC-n`
already carries it, it is named; the analyst must trace every `SEC` and `PRIV` here to an
acceptance criterion, and six of them have no home in §10 today.

### Security

| ID | Requirement | How it is tested |
|---|---|---|
| **SEC-1** | **Every whitelisted function in `home_api.py` and `inbox_api.py` is safe on its own, from the commit that adds it.** The portal page is not a gate: these endpoints answer any logged-in caller from the first release that carries them, whatever page called them. Each ships **in the same commit** as its Guest-refused test, its wrong-persona test and its scope test | A **registry test** that enumerates the whitelisted functions **from the module itself** and requires an entry with all three cases. A new whitelisted function with no entry fails. (`042 AC-41` has this, but it must enumerate from the module, not from a hand-written list, or it becomes a list somebody forgets) |
| **SEC-2** | **`get_home` returns only named keys, and the exclusions are named too.** The `me` block is exactly `employee`, `employee_name`, `designation`, `department`, `image`, `company`. It **never** carries `date_of_birth`, `gender`, `cell_number`, `date_of_joining`, `reports_to` or `branch`. Roles go out as the booleans the screen needs, never the role list. The same binds `get_nav_counts` and `get_inbox`. **The reason is not secrecy from the caller — it is that this payload reaches every log, screenshot and error report on the tenant's landing page.** *Verified in code:* `hr_api._get_employee` (`:152-160`) returns all twelve fields and `get_portal_context` (`:164`) is built on it, so the wrong thing is the easy thing here | Exact key-set assertion **per persona**, on the payload and not on the screen (`042 AC-5`); plus a check that no Wave 2 module passes a `_get_employee` result through unfiltered |
| **SEC-3** | **One scope, declared per part; a part with no declared scope does not exist.** `inbox_api.parts()` returns part objects, **each naming the scope helper it reuses as data, not as a comment**, and the same expression produces both `count()` and `rows()`. No caller of `parts()` writes a filter of its own. For an HR caller the scope is `access.permitted_employees()` (*verified in code*, `access.py:237`); for a manager their own line; for an employee themselves | `042 AC-8` (count equals list, enumerated from `parts()` itself) **plus a new structural test**: every part exposes a non-empty scope declaration, and a part constructed without one raises at import. Two-store fixture with a head-office employee who has **no branch** (`042 AC-10`) |
| **SEC-4** | **A filter helper refuses explicitly and never returns an empty or partial filter dict.** In Frappe an empty filter **dict** means **every record**. Any helper Wave 2 adds that returns filters must, for a caller with no entitlement, return filters matching nothing (`{"name": ["in", []]}`) or a sentinel the caller is forced to handle. *Wave 1's N1 lesson, re-armed: Wave 1 added one filter expression, Wave 2 adds seven* | A direct assertion that the return value is never `{}` and never a dict with no keys — as a plain employee, a manager, a Vendor User and **a caller with no Employee record** — plus a query built from each returning zero rows |
| **SEC-5** | **A feature switch is enforced in the endpoint, on the server, and the test calls the real gate.** The payslip row and any other plan-gated part are refused server-side on a tenant without the feature; hiding a row is not a permission. **No test may patch `subscription.has_feature` to `True`.** *Verified in code:* `subscription.requires_feature` (`:672-692`) exists, sits above `@frappe.whitelist()`, and its own docstring records that Wave 6 shipped hidden panels whose endpoints still answered | A static check that no test in this slice patches `has_feature`, `requires_feature` or `enabled_features`; and a flag-off test per gated endpoint asserting the refusal from the real function |
| **SEC-6** | **Nobody decides their own request, on any of the five paths** — leave, attendance correction, shift request, goal update, KPI update. `access.refuse_own_decision` (*verified in code*, `access.py:63`) is called on **every** decide action, not only the one that has it today, and the caller's own item is absent from their own count and their own list | `042 AC-25`, extended: for each of the five — (a) not in the count, (b) not in the list, (c) the action called by hand is refused, (d) the refusal is logged with no personal content, (e) **no document was written** |
| **SEC-7** | **The list and the action share one scope function, and the test proves it in both directions.** Every drawn row is actionable; **and an undrawn row is not actionable by hand.** The second half is the one that matters — the first only proves the screen is tidy | `042 AC-17` covers the first direction. **New:** per persona, take a document that is *not* in their list, call its decide action, and expect a refusal, a logged refusal and no write |
| **SEC-8** | **D-2 is a permission change, not a routing change, and it must be decided before code.** *Verified in code:* `attendance_correction._may_review` (`:240-248`) tests **submit permission on Attendance Request**, not a role, so a tenant may have granted the queue to a Shift Supervisor (W1D-14). Whatever D-2 decides, three things hold: (a) a manager gains the ability to decide only for **their own Active direct reports**; (b) an HR caller stays inside `permitted_employees()`; (c) a non-HR reviewer holding submit is **unchanged**, and that remains a recorded gap rather than a silent alteration. **Fail-closed default until Surbhi answers: no new decider is added.** Count and list move together, so a correction is never counted twice | Fixtures across manager, store HR, company HR and a Shift Supervisor holding submit; each one's count equals their list; a correction visible to two deciders is counted **once** in each of their own totals and cannot be decided twice (`042 AC-18`, `042 AC-58`) |
| **SEC-9** | **`get_week_presence` is retired, or scoped, in the same commit that stops calling it.** See A2 for what it returns today. Replacing the card with counts while leaving the endpoint live narrows the screen and nothing else. Either **delete it and its panel in one commit** — my recommendation — or keep it and give it the new card's peer scope and minimum-n rule. **This is not in the spec and the spec must change:** §3 lists it as "Extend" and §18.3 claims the visibility is narrower, which is true of the card and not of the endpoint | A static check that no tracked file names `get_week_presence`, **and** a call-by-hand test expecting a refusal or a missing method. If it is kept instead, PRIV-2's tests run against it too |
| **SEC-10** | **No `ignore_permissions` in `home_api.py` or `inbox_api.py`, and no new one in any file this slice edits.** Where Wave 2 reuses an existing helper carrying the flag, **the ownership or scope check happens before the flag is raised, and a test proves the order, not the presence** | A test that reads both modules and counts `ignore_permissions` — zero (`042 AC-42`). For each reused helper carrying one, a test that calls it with a caller who fails the check and asserts refusal **before** any read |
| **SEC-11** | **Every "who am I" lookup in this slice finds an Employee with `status = "Active"`, through one helper.** A caller whose record is not Active and who holds no HR role finds nobody and has nothing to approve; they keep their own still-open requests. A rehire with two Employee records resolves to the Active one everywhere, so two cards cannot describe two different people | `042 AC-37`, `042 AC-46`, `042 AC-47`; plus a static check that no Wave 2 module queries Employee by `user_id` without `status` |
| **SEC-12** | **Everything drawn from data is escaped, in Jinja and in the browser.** Wave 2's markup never assigns API data to `innerHTML`; it uses `textContent` or one shared escape helper. **This is not in the spec and the spec must change** — 034 SEC-10 covers Wave 1's include files, and Wave 2's panels go into those same four files, so the check must be extended rather than assumed | A scan of the include files for `innerHTML` with API data, **plus** a DOM test: a designation of `<img src=x onerror=alert(1)>` appears as text in a queue row, a context line and the team card, and creates no element |
| **SEC-13** | **The new modules keep no module-level cache and no mutable global**, because one worker serves several sites. Any cache uses `frappe.cache()` (per site) or `frappe.local` (one request), keyed by user. *This is the only cross-tenant path in Wave 2, which is why it is a requirement and not a note* | Static check on both modules: no `global`, no module-level dict, list or set mutated at run time (`042 AC-42`) |
| **SEC-14** | **A caller with no Employee record is refused explicitly, not filtered by an absent value.** Asha reaches "All clear" and total 0 by a path that **returns early** — never by a query whose employee filter was `None`. A `None` in a Frappe filter is not a refusal | For every part and every list: call as a user with no Employee record and assert (a) the result is empty **and** (b) **the scoped query was not run** — a query count of zero. An unscoped query that happened to return nothing looks identical from the outside |
| **SEC-15** | **Counts and rows are read over POST with arguments in the body**, and every write is POST. The web server logs URLs; a document name or a search term in a query string is a log entry nobody meant to write | A test that the Wave 2 calls are POST, and a log-capture test on a normal and a refused call (`042 AC-43`) |
| **SEC-16** | **Wave 2 adds no second pending-count query anywhere.** The bell, the menu entry, the bottom bar and the Team badge all read one endpoint, and no boot path calls `goals_api.get_pending_approvals` or `get_pending_approvals_count`. *This is a security requirement, not a performance one: a second counter is a second scope, and the second one is the one that goes wrong quietly* | `042 AC-14`, `042 AC-16` — static check on callers plus a boot-path assertion |

### Privacy

| ID | Requirement | How it is tested |
|---|---|---|
| **PRIV-1** | **Counts and count payloads carry numbers only** — no names, no reasons, no leave types, no document ids. The frame never calls an endpoint that returns names on page load | Payload-shape test per persona (`042 AC-12`); a test that no boot path calls `get_pending_approvals` |
| **PRIV-2** | **The peer card is the one new inference channel in this slice, and it is bounded by a rule rather than by good sense.** Three parts: **(a) counts only** — no name, no photo, no per-person state, no leave type, no reason, in the payload as well as on the screen; **(b) a minimum group size — below it the card shows its sentence and no numbers at all**, and where one category is suppressed the next smallest is suppressed with it, so the total cannot be used to recover it; **(c) no history and no trend** — the card is today, it is not stored, and no endpoint returns a run of days. **The spec proposes five and does not state the complementary-suppression rule; both belong in the spec.** `[ASSUMPTION]` five is the right number — it is `01b` §9's figure and the baseline supports a threshold without naming one. **Decision for Surbhi (Q2)** | `042 AC-29`, extended and asserted **on the payload**: a four-person team shows the sentence and **no numbers**; a six-person team with one away and five in shows both; a six-person team where suppressing one category would leave the other recoverable suppresses both |
| **PRIV-3** | **No colleague's name, leave type or absence reason appears in a context line, a toast, a count or a notification.** "2 other people in this team are away on those days" is a number. The phrase "Nobody is on leave today" and every equivalent appears nowhere in the built page — it discloses the absence backwards | `042 AC-28` with a fixture of two overlapping leaves of **different types**; `042 AC-30`'s static check over the include files |
| **PRIV-4** | **The celebrations card is profiling of named individuals and needs an answer before it ships.** A new joiner's name, job title and joining date on every colleague's Home is a deliberate disclosure about the newest and least powerful person in the building. Three things must be settled and written into the spec: **the scope** (the spec recommends own branch, last 30 days — I agree); **whether a person may decline to be listed**; and **that the card draws Active employees only**. **Fail-closed default until Surbhi answers: own work anniversary only, and no joiners list.** **This is a decision row in the spec, not a requirement, and the spec must change** | Scope test per persona; a Left employee never appears; a joiner outside the window never appears; if an opt-out is agreed, a test that a declining employee is absent from every viewer's payload |
| **PRIV-5** | **Attendance gaps are the caller's own, and Wave 2 builds no manager-facing gap list.** A pattern of absence can imply health, caring duties or religious observance. The gap list is on Home for the person it is about; it is not on the team card, not in a count a manager sees, and not in an export | Payload test: the gap array exists only for the caller's own employee; a manager's `get_home` for a team of 19 carries no gap data for anyone but themselves |
| **PRIV-6** | **The "your payslip is ready" row is own-only and payroll-gated, and the take-home figure appears in no email, no push preview and no notification.** The row states a fact — a slip exists. The figure, if shown at all, is on the screen the caller opened | Own-only test (another person's slip name refused with identical wording); flag-off test through the real gate (SEC-5); a log- and mail-capture test asserting no amount |
| **PRIV-7** | **The audit entry must let someone reconstruct the decision a year later, in the only situation anyone reads it — a grievance.** Wave 2 writes through the existing actions and never sets a status with a `db_set` of its own, so the decider, the time and the decline reason keep being recorded. **Decide-in-place must not become decide-without-a-reason:** a decline requires a reason on every one of the five paths, including the fast one on Home | For each of the five: decide from the Inbox row **and** from the Home card, then assert the source document carries the decider, the timestamp and, on a decline, the reason text — and that a decline with an empty reason is refused |
| **PRIV-8** | **Logs carry the endpoint, the user id, the outcome and the time — never a name, a search term, a document id or a per-person count.** Refusals use `access.log_refusal` | Automated log-capture on a refused call and on a normal call (`042 AC-43`) |
| **PRIV-9** | **Wave 2 stores nothing new, and this is asserted rather than assumed.** No new DocType, no new field, no new log line carrying personal data, no server-side cache of a count. Counsel's retention periods of 18 Sep 2026 are therefore **not engaged** — stated, not skipped | A static check that Wave 2 adds no DocType JSON, no custom-field fixture and no patch; a test that no count is written to disk or to a cross-request cache |

---

## Visibility delta — everything Wave 2 shows, and where that person sees it today

**Nothing gets wider. Five rows get narrower. One row is new.**

| What Wave 2 shows | Who sees it | Where they see it today | Wave 2 |
|---|---|---|---|
| Own name, job title, department, photo, company | Everyone with an Employee record | Today's sidebar and `/me` | Same |
| Own DOB, gender, phone, joining date, manager, branch | **Nobody — not in any payload** | `/me` and the desk, for themselves | **Narrower** (SEC-2) |
| Own leave balances, own holidays | The caller | Today's Leave panel (slice 035) | Same |
| Own attendance gaps, as a list | The caller | Today's month calendar, less clearly | Same data, clearer |
| Peer presence, **named, per day, whole department** | Any employee with no reports | `get_week_presence:3151` today, up to 40 department colleagues | **Narrower** — counts only, peer-scoped, minimum-n — **only if SEC-9 retires the old endpoint** |
| Team card: own direct reports | A manager who is not HR | Today's Team panel | Same |
| Team card: HR scope | HR | Today's Team panel, which shows them every employee in the tenant with no manager | **Narrower** for store HR (W1D-20) |
| Queue rows: leave, corrections, goal/KPI, shift | Whoever may decide them | Today's three separate, partly broken lists | Same data, one place |
| Queue rows | Store HR | Today's queues, company-wide | **Narrower** (034 SEC-3, SEC-5) |
| Anything at all | A leaver with an enabled login | Today's search and queues still work for them | **Narrower** — nothing (SEC-11) |
| New joiners, named | Colleagues in scope | **Nowhere today** | **New** — the only new disclosure in the slice (PRIV-4) |
| Birthdays | Nobody | `/me` and the desk | Same — not built |
| Take-home figure | The caller only | Today's Pay panel | Same, payroll-gated (PRIV-6) |

---

## Questions

### Must know — these block the requirements or the build

| # | Question | My reading, and the fail-closed default meanwhile | Owner | Blocks |
|---|---|---|---|---|
| **Q1** | **D-2: who may decide an attendance correction, and from when?** | This is a permission change dressed as a routing change: it adds a decider to a queue that today reaches whoever holds submit permission. Until it is answered I require **no new decider** — the queue stays as today, scoped per W1D-05 and W1D-14. The analyst's recommendation (HR sees from day one, may act from day three) is reasonable and I do not object; it must be written down before code, because "visible but not actionable" is a third state the code does not have | Surbhi | SEC-8; the corrections part of the count and the list |
| **Q2** | **The peer card's minimum group size — is five right, and does complementary suppression apply?** | Five is `01b` §9's figure and I have no better one. Complementary suppression is not optional arithmetic: with three categories and a known total, suppressing one recovers it. Until answered I require **five, with complementary suppression** | Surbhi, with me | PRIV-2 and `042 AC-29` |
| **Q3** | **Is `get_week_presence` deleted, or kept and scoped?** | Delete. Keeping a whitelisted endpoint that returns named per-day absence states for a whole department, purely because a card no longer calls it, is "a hidden menu is not a permission" wearing a different hat. If it is kept for another caller, name that caller | Surbhi, with the engineer | SEC-9 |
| **Q4** | **The joiners card: scope, and may a person decline to be listed?** | Branch, last 30 days, Active only. On declining I genuinely do not know what is right — a small kindness with a real cost in code. Until answered: **own anniversary only, no joiners list** | Surbhi | PRIV-4 |

### Should know

| # | Question | Owner |
|---|---|---|
| Q5 | Does the peer card survive the usability test in `01b` §12? If it does not, dropping it removes PRIV-2 and one inference channel with it | Surbhi, with the UX designer |
| Q6 | D-1 (the Home number) has no security consequence — but if option B is taken, **every Home item must be one of the six counted parts**, which moves the self-review and gap reminders and changes what PRIV-5 has to check | Surbhi |

### Nice to know

| # | Question | Owner |
|---|---|---|
| Q7 | Is a decline reason shown to the requester verbatim, or summarised? Verbatim today; I propose no change. Noted because a free-text field written in haste and shown to the person is a grievance in waiting | Surbhi |

---

## Worries — not findings, and deliberately separate

I cannot yet write *this actor, in this state, calling this path, sees this data* for any of
these. Nothing should be built from them.

1. **`goals_api` defines `_is_hr` twice** (`:17` and `:245`) and Wave 2 edits
   `_pending_approvals_scope` between them. Whoever edits it must know which one runs. I
   have not traced which wins in every import order.
2. **Department-based queries carry no company filter.** `get_week_presence` filters on
   `me.department` alone. ERPNext department names are company-suffixed, so this is
   *probably* company-safe — but "probably" is the word that precedes a finding. If SEC-9
   retires the endpoint, this worry dies with it.
3. **`_may_review` tests submit permission rather than a role**, so the corrections queue's
   audience is whatever a tenant's permission setup happens to produce. I cannot enumerate
   that from the code.
4. **The demo tenant cannot show these controls working.** Wave 1's lesson 1 exactly: §14 of
   the spec says the local copy has no check-ins after 6 Sep and no open requests that are
   not the owner's own. **Until that data exists, "0 findings" on the scope tests means
   nothing.**

### What must exist in the data before each control is observable

| Control | What the data must contain |
|---|---|
| SEC-3, SEC-4 | Two stores, a head-office employee **with no branch**, and a waiting item in each place |
| SEC-6 | One request raised by the approver themselves, on each of the five paths |
| SEC-8 | A correction from a manager's own report **and** one from outside their line |
| SEC-11 | An Employee set to Left whose User is still enabled, with an unmoved report and an open request |
| PRIV-2 | A peer group of four, and one of six |
| PRIV-4 | A joiner inside the window and one outside it, in two different branches |

---

## Residual risk — each with an owner and a date

| # | Risk | Owner | Date | State |
|---|---|---|---|---|
| **R1** | A successful over-read leaves no signal. Nobody reads the security log and nothing alerts on it. Wave 2 multiplies the traffic through the scoped readers without adding detection | Security & privacy engineer, with DevOps | Logging first step **2026-10-15**; detection slice **2026-11-30** | **Carried from Wave 1 R3, unchanged and now larger.** Accepted for Wave 2 on the same dates. If those dates slip, this should be re-presented rather than re-accepted quietly |
| **R2** | No repo-wide `ignore_permissions` counter in CI. SEC-10's check covers two files | Security & privacy engineer (feature map B4) | Baseline script **2026-10-31**; blocking gate on the next commit after | **Carried from Wave 1 R4.** Wave 1 recorded that the gate "must exist before Wave 2 adds endpoints". **Wave 2 is here and the gate is not.** Either the date holds and Wave 2 waits, or the date moves with Surbhi's name on it |
| **R3** | The org chart shows every company and every store; a Wave 2 queue row is a click from it | Fullstack engineer | Before DTC go-live — `ALV-86`, Critical | **Not accepted** (W1D-08). Wave 2 does not work around it |
| **R4** | A store HR person whose Branch User Permission is narrowed to a single doctype is treated as company-wide (`access.py:233` fails open) | Live check: Surbhi with the tenant admin. Code fix: engineer, in `ALV-86` | Live check **2026-09-30**; code fix **2026-11-15** | **Carried from Wave 1 R6.** Every scope requirement here rests on `permitted_employees()`, so this is the single assumption most of Wave 2 stands on |
| **R5** | Alvoraa staff reach client tenants through one shared `Administrator` login, so a read cannot be traced to a person | Surbhi, with me | `ALV-93` | **Recorded, outside Wave 2** (W1D-18) |
| **R6** *(new)* | The peer card is a real inference channel. Minimum-n bounds it; it does not remove it. In a six-person team, "1 away" plus a look around the floor names the person | Surbhi | Accept or decline **at the strategy gate**, before the first Home commit | **Proposed for acceptance, not yet accepted.** Recommendation: accept — co-presence already discloses it and the product adds no reason, no history and no trend (A14) |
| **R7** *(new)* | Decide-in-place makes a decision about a person cheaper to take. Nothing is automated and the reason is still required, but a two-second decline is a thinner decision than a two-minute one | Surbhi | Review after 30 days on dev | **Proposed for acceptance.** No control is available that would not defeat the feature; PRIV-7's mandatory reason is the mitigation |

---

## Assumptions

- `[ASSUMPTION]` **Five is the right minimum group size** for PRIV-2. From `01b` §9 and the
  baseline's "minimum n" language; no source names a number. Q2.
- `[ASSUMPTION]` `access.permitted_employees()` and `permitted_branches()` behave as their
  docstrings and slice 030's tests say. *Verified in code* that both exist (`access.py:217`,
  `:237`); their behaviour is taken from slice 030, not re-proved here.
- `[ASSUMPTION]` ERPNext department names are company-suffixed, so a department filter is
  company-safe. Worry 2.
- **Unknown — I could not check this.** Whether any tenant has granted submit permission on
  Attendance Request to a non-HR role, and to whom. It decides who `_may_review` lets into
  the corrections queue. **Access I would need:** a read of the Role Permission and Custom
  DocPerm rows on `dtc`, `aahr` and the local PP Jewellers copy. I did not probe any live
  tenant and will not.

---

## Verdict for this slice

**Not ready to build, and four of the reasons are mine.**

**What must change in `02` before code:**

1. **SEC-9** — retiring the peer card is not the same as retiring `get_week_presence`. §3's
   row must become a deletion with a static check and a call-by-hand test, and §18.3's
   "narrower" claim must be qualified until it is.
2. **SEC-12** — output escaping for Wave 2's panels. §10's cross-cutting checks cover
   `ignore_permissions`, module state, POST and the registry, but not `innerHTML`.
3. **PRIV-2** — the minimum-n rule needs the number **and** complementary suppression as an
   acceptance check asserted on the payload. §17 states it as a design intention; that is
   not a control.
4. **PRIV-4** — the joiners card needs a scope, an Active filter and an answer on declining,
   as an acceptance check rather than a decision row.

**Two extensions to checks the spec already has:** `042 AC-17` must also drive an **undrawn**
row through its action and expect refusal (SEC-7); and the entitlement tests must call the
real feature gate, with a static check that no test patches it (SEC-5).

**Decisions for Surbhi, not requirements:** Q1 (D-2's routing), Q2 (minimum group size),
Q3 (delete `get_week_presence` or scope it), Q4 (the joiners card and declining), and the
acceptance of R6 and R7. **R2 is the one to look at first:** Wave 1 recorded that the
`ignore_permissions` gate must exist *before* Wave 2 adds endpoints, and Wave 2 is here.

**Nothing in this slice is a P0.** No cross-tenant path, no live exposure inside Wave 2's own
scope, and no model anywhere near it. The live defects in this area belong to Wave 3 and are
assessed there.

---

## Handoff note

**To the analyst:** the four spec changes and the two check extensions above. Trace every
`042 SEC-n` and `042 PRIV-n` to an acceptance criterion; six have no home in §10 today.

**To the engineer:** build `parts()` with its scope declaration first, before any screen. The
day somebody adds an eighth part without a scope is the day the number stops being
trustworthy, and SEC-3's structural test is the only thing that catches it.

**To the test engineer:** three tests here are easy to write so that they prove nothing.
SEC-4's "never `{}`" must assert on the **return value**, not on the rows. SEC-5's gate tests
must not patch the gate. SEC-14's no-Employee test must assert **zero scoped queries**, not
just an empty list — an unscoped query that happened to return nothing looks identical.

**To me, at review:** SEC-9 first (the retired endpoint), then SEC-14 (the fail-open shape),
then PRIV-2 asserted on the payload rather than the screen.
