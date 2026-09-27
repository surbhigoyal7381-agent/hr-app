---
slice: 043-redesign-wave3
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-09-24
revision: 1
status: draft — written after the functional spec. Carries one P1 that must be settled before the Why? sheet is written
inputs: [02-functional-spec.md (043, revision 1), ../042-redesign-wave2/01c-security-privacy-requirements.md, ../034-redesign-wave1/01c-security-privacy-requirements.md revision 4, ../034-redesign-wave1/06-security-review-of-requirements.md, ../034-redesign-wave1/00g-decision-register.md (W1D-01 to W1D-21), ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, .claude/context/security-compliance-baseline.md, docs/legal/2026-09-18-retention-and-driver-tracking-proposal.md, the code at origin/dev 8718f27 read in this worktree on 2026-09-24]
---

# Wave 3 — Time and Pay: security and privacy requirements

**Numbering is per slice.** This slice runs `SEC-1` to `SEC-16` and `PRIV-1` to `PRIV-12`.
Cite them as **"043 SEC-4"**. Decisions are `W1D-nn` from
`../034-redesign-wave1/00g-decision-register.md`.

**Every claim carries a label.** *Verified in code* means I opened the file and read the
line, and it is named. *Inference* says what it rests on. `[ASSUMPTION]` is a working guess.
*Unknown* means I could not check it and says what access I would need. Worries are in their
own list and are not requirements.

**Pay is the most sensitive screen in the product, and Time is the second.** A payslip is a
statutory record about one person's money. A punch time is a minute-by-minute account of
where somebody was. Everything below is written on the assumption that a mistake here costs
more than a mistake anywhere else in the portal.

---

## Bad news first

**1 · The contest route the spec proposes does not work, and the sentence it proposes to
show 400 people is wrong.**

`02` §18.4 recommends the Why? sheet ends with *"If a day here is wrong, fix the day first —
the rule follows the attendance record."*

**Verified in code — the rule does not follow the attendance record once the deduction is
submitted.** `hrms/hrms/alvoraa_late_rules/late_rules.py:208-215`:

```python
if found and found.docstatus == 1:
    existing += 1
    continue
```

A submitted Attendance Deduction is skipped by every later run, including HR's catch-up
`run_for_range` (`:251`). So an employee who corrects 4 August in September gets a corrected
Attendance record and **keeps the deduction and keeps the loss of pay**. The only remedy is
an HR person cancelling the Attendance Deduction by hand, which cancels the linked Additional
Salary (*verified in code*, the cancel path at `attendance_deduction.py:175-180`) — **and
that helps only if the Salary Slip has not already been submitted.** After that, nobody in
the product can put the money back.

This is a **P1 — it blocks the release of the Why? sheet**, because Wave 3 is the first time
the employee is told anything at all about how the decision was made, and telling them a
remedy that does not exist is worse than telling them nothing. PRIV-6 to PRIV-10 say what
must be true instead. **The decision about how far to go is Surbhi's, not mine** (Q1).

**2 · One of the three defects handed to me is real but mis-described, and the real shape is
different.** The manager's deduction email does **not** carry the rupee amount. It carries
the **leave type** the days were taken from. See §"The three live defects" below. The
correction matters: fixing the wrong thing would leave the leak in place.

**3 · A fourth live defect, not in the list.** *Verified in code:* `hr_api.get_payslips:1515`
returns `{"payslips": slips, "employee": emp}`, and `emp` is `_get_employee()`'s full row —
`date_of_birth`, `gender`, `cell_number`, `branch`, `reports_to` and the rest
(`hr_api.py:152-160`). This is Wave 1's biggest finding, live today, on the payslip endpoint.
It is the caller's own data, so nobody else sees it — but it is on the Pay screen, which is
the screen people screenshot for a bank and attach to a support ticket. SEC-3.

---

## The three live defects, assessed as findings

### Defect 1 — the manager's deduction email

**The claim as given:** the email carries the stored `explanation`, which names the rupee
amount; Q-b of 14 Sep ruled days at most, never the amount.

**What is actually true. Verified in code**, `attendance_deduction.py:37-59` (`build_explanation`)
and `:182-205` (`notify`):

| Claim | Verdict |
|---|---|
| The manager's email carries the stored `explanation` | **True.** `notify()` sets `message=self.explanation` and puts the manager's `user_id` in the same `recipients` list as the employee's, so both receive the identical body |
| The `explanation` names the rupee amount | **False.** `build_explanation` uses `lwp_days`, never `lwp_amount`. The loss-of-pay clause is `_("{0} as loss of pay").format(flt(self.lwp_days))` — **days**. There is no currency figure anywhere in the function |
| Q-b is therefore breached | **Partly, and by a different route.** Q-b is met on the amount. It is breached on something the spec's own negative list forbids more plainly: **"Any colleague's leave type or reason"** |

**The finding, written as a scenario.** *A manager whose report had 0.5 of a day taken from
Sick Leave receives, by email, on submission of the weekly Attendance Deduction, the sentence
"Taken: 0.5 from Sick Leave, 0.5 as loss of pay."* The manager learns that their report has
**Sick Leave**, and that the product used it. Elsewhere in this same slice a manager is
forbidden a report's leave type on every screen (`02` §5). The email is the one place nobody
looked, which is exactly the shape the analyst identified even though the cause is different.

**Severity: Major. Priority: P2 — fix before Wave 3 ships, and it does not need to wait for
the rest of Wave 3.** Not P1, because the disclosure is to the person's own line manager, who
has a duty of care, and because the leave-type clause only appears when
`deduct_from_leave_first` is on. Not P3, because it is going out by email today on any tenant
with `notify_manager` on, and an email cannot be un-sent.

**Sooner than the wave?** Yes — it is one function and it is independent of every screen in
Wave 3. My recommendation is a separate small commit before the Wave 3 build starts. SEC-8
says what "fixed" means, and it is more than deleting a number.

### Defect 2 — `get_payslips` has no feature gate

**Verified in code.** `hr_api.py:1514` is `@frappe.whitelist()` and nothing else.
`get_payslip:1561` and `download_payslip:1594` both carry `@requires_feature("payroll")`
above the whitelist. The decorator exists and works (`subscription.py:672-692`), and its own
docstring records that this exact mistake — a hidden panel whose endpoint still answered —
was made before, in Wave 6.

**The finding, as a scenario.** *An employee on a tenant that has not bought payroll, signed
in and calling `get_payslips` by hand, gets a JSON object back.* What they get is **their own
submitted Salary Slips** — and the query carries `ignore_permissions=True` (`:1526`), so
Frappe's own permission layer does not save it. If the tenant has never run payroll the list
is empty; if payroll was run and the feature later switched off, it is not.

**Severity: Major. Priority: P1 — it blocks the Wave 3 release**, because Wave 3 is the slice
that puts an entitlement boundary around Pay (W1D-01) and shipping that boundary with one
door still open would make the claim false. It is not P0: the data returned is the caller's
own, so no one person sees another's pay through it.

**Sooner than the wave?** It can wait for the Wave 3 build, provided it is the first commit
in it. `02 AC-30` already covers it. SEC-2 adds the part `AC-30` does not: the refusal must
read the same as a not-entitled refusal, or it tells the caller what the tenant has bought.

### Defect 3 — `get_shift_types` returns everything with `ignore_permissions=True`

**Verified in code**, `hr_api.py:1879-1885`: `@frappe.whitelist()`, no feature gate, no
employee check at all, `frappe.get_all("Shift Type", fields=["name","start_time","end_time"],
ignore_permissions=True)`.

**A correction the spec needs.** `02` §3 and `AC-52` say to "scope to the caller's company".
**Verified in code — Shift Type has no `company` field.**
`hrms/hrms/hr/doctype/shift_type/shift_type.json` has no company among its fields. So the
acceptance check as written cannot be implemented, and an engineer at 11pm will either invent
a custom field or quietly drop the check. Scoping must be by something that exists: the shift
types **assigned in the caller's own company** (via Shift Assignment), or the ones sharing the
caller's `holiday_list`, or — simplest and safest — **the shift types a tenant has marked
selectable**. That is a design choice and it belongs in the spec (Q3).

**The finding, as a scenario.** *Any logged-in user of the tenant — including one with no
Employee record at all, and including a leaver whose login is still enabled — calling
`get_shift_types`, gets every Shift Type name and its start and end times across every company
and every store in the tenant.* No personal data. Configuration data: the tenant's shift
structure, and through the names, often its site list ("Night Shift — Ludhiana Warehouse").

**Severity: Minor. Priority: P3 — fix in Wave 3, after release is also acceptable.** Each
tenant is its own site, so there is no cross-tenant path. Nothing returned is about a person.
What makes it worth fixing at all is the *shape*: a whitelisted endpoint with
`ignore_permissions=True` and no caller check is the pattern that becomes a leak the next time
somebody adds a field to it. SEC-7.

**Ranking the three against each other, since that is what the ordering is for:**
**Defect 2 first** (it makes an entitlement claim false and it is one line),
**Defect 1 second** (it is going out by email now, but to a duty-bearing recipient),
**Defect 3 third** (shape, not substance).

---

## Threat model — four questions, answered for this slice

**1 · Who would want this data, and what is the cheapest way to get it?**
For **Pay**, the wanted thing is a colleague's salary, and the cheapest path is a document
name: guess or obtain a Salary Slip name and call `get_payslip`. The whole defence is
`_own_payslip` (*verified in code*, `hr_api.py:1545-1558`) and the fact that it refuses
identically whether the slip belongs to somebody else, is a draft, or does not exist. Wave 3
adds a **second** such door — the "why" endpoint — and it must be built the same way or it
becomes the probe.

For **Time**, the wanted thing is a colleague's movements. The cheapest path is
`attendance_correction._subject:251`, which decides whose month you may open. One weakened
condition there and a manager reads a stranger's punch times.

For both, the second attacker is an **over-scoped manager** who is entitled to a report's
day-level attendance and becomes entitled — by a payload that returns too much — to their
health-shaped leave data or their money.

**2 · What is the blast radius of one mistake?**

| Scale | What sits here in Wave 3 |
|---|---|
| Cross-tenant | Nothing — provided no module-level cache (SEC-13) |
| Whole tenant | `_deduction_rows`'s raw-filters-plus-`ignore_permissions` shape, if a second caller passes a client-supplied filter (SEC-5). This is the single worst path in the slice |
| One company / store | `get_shift_types` (configuration only, SEC-7) |
| One manager's line | The deduction email's leave type (SEC-8); a team payload carrying more than days (PRIV-2) |
| One person, but the most sensitive record they have | `_own_payslip` and the Why? endpoint (SEC-4, SEC-6) |

**3 · What does this make possible that was impossible before?**
Two things, and only one of them is new data. (a) **Nothing new is collected** — every figure
Wave 3 shows already exists. (b) **An automated decision about a person's pay becomes
visible and, for the first time, arguable.** That is not a new risk; it is the discharge of an
existing obligation that has been unmet since the late-coming rule shipped. It creates one new
duty: what the product says about that decision must be **true**, and the remedy it offers
must **work**. See PRIV-6 to PRIV-10.

**4 · How would we find out?**
**We would not, and here it is worse than in Wave 2.** A wrong payslip read leaves the same
absence of signal as any other over-read: refusals are logged through `access.log_refusal`,
successes are not. There is no access log on the two client tenants (W1D-18, `ALV-93`) and
Alvoraa's own access is one shared `Administrator` login, so a read of a customer's payroll
data **cannot be traced to a person**. For the most sensitive screen in the product that is
worth saying plainly rather than carrying as a table row. Residual risk R1 and R5.

---

## Data inventory

| Data | Where | Sensitivity class | Purpose | Kept | Who may see it |
|---|---|---|---|---|---|
| Caller's `employee`, `employee_name`, `designation`, `department`, `image`, `company` | `get_time.me`, `get_pay.me` | Personal, low | Show who is signed in | Not stored | The caller |
| Caller's `date_of_birth`, `gender`, `cell_number`, `date_of_joining`, `reports_to`, `branch` | **Never in any Wave 3 payload** (SEC-3) | Personal, higher | — | — | — |
| Own punch times, per day, to the minute | Day sheet | **Sensitive** — a pattern of arrivals can imply caring duties, health or religious observance | Attendance and pay | Employee Checkin's existing retention, unchanged | The caller; and their own line upward through `_subject` |
| Own attendance status per day | Calendar | Sensitive | Attendance and pay | Unchanged | Same |
| Own leave balances and past leave **with types** | Leave tab | **Sensitive** — a leave type can imply a medical or family circumstance | Leave administration | Unchanged | **The caller only** (PRIV-3) |
| Own late-rule violations, minutes, counted flag | Late rule tab, Why? sheet | Sensitive | Explain a pay decision | Attendance Deduction's retention — **unset, see PRIV-11** | The caller only |
| Own loss-of-pay **days and amount** | Why? sheet | **Sensitive** | Explain a pay decision | Unchanged | The caller only |
| Own salary components, gross, deductions, net, year to date | Pay | **Sensitive — the most sensitive in the product** | Pay | Salary Slip's statutory retention, unchanged | **The caller only, including from HR** |
| Own payslip PDF | Download | **Sensitive** | Give the person the document a bank accepts | Not stored by the portal; rendered on demand | The caller only |
| A report's late **days** (`deduction_days`, `lwp_days`) | Team late list | Internal | A manager's duty of care | Unchanged | Their own direct reports only |
| A report's late **amount**, the `explanation` text, the **leave type** | **Nowhere — on a screen, in a payload or in an email** (SEC-8, PRIV-2) | Sensitive | — | — | — |
| A report's punch times, per violation | `get_team_late_list`'s `detail` array | Sensitive | — | — | **Open — Q4.** *Verified in code:* it is returned today (`hr_api.py:2832-2834`), in the same function whose comment three lines later says a manager never receives per-day punch times |
| Late-rule settings (thresholds, free count, week start, wage basis) | Late rule tab | Not personal — it is the employer's policy | Explain the rule | Unchanged | Anyone the rule covers |
| Shift Type names and times | Change-shift sheet | **Configuration**, not personal | Request a shift change | Unchanged | Per SEC-7's scope |

**Nothing new is collected. Nothing new is stored.** *Inference, resting on the spec's §8 and
§14 and on my own read of the endpoints it reuses.*

---

## Who must NOT see what

| Who | Must not see |
|---|---|
| **Anyone at all, including HR, including a System Manager through the portal** | Another person's payslip, take-home, salary component, or payslip PDF. HR uses the desk, where the access is at least attributable to a role |
| A manager | A report's loss-of-pay **amount**, the stored `explanation`, or the **leave type** the days came from — on screen, in a payload, or **in an email** (SEC-8) |
| A manager | Anyone outside `_subject`'s rule. `attendance_correction._subject:251` is the whole control for another person's month and stays it (SEC-9) |
| Any employee | Another person's punch times, attendance gaps, leave balances or leave types |
| Any employee | A ranking, league table or comparison of colleagues by lateness — in any payload, on any screen, in any export (PRIV-4) |
| A tenant without `plan_payroll` | Every payslip endpoint, including the list (SEC-2) |
| A leaver (Employee not Active) with an enabled login | Their own screens up to the point their login stops is acceptable; they must appear in **nobody's** team late list and **nobody's** queue (SEC-12) |
| A caller with no Employee record | Everything, by explicit refusal rather than by an absent filter (SEC-14) |
| Guest | Anything |
| A log, an error message, a notification body or a push preview | Any salary figure, any punch time, any slip name, any deduction name (PRIV-1, PRIV-5) |

---

## Obligations engaged, with the date each was last verified

**None stale.** Baseline entries relied on here were verified 24 Aug 2026 (31 days old) and
6 Sep 2026. Counsel's proposal is dated 18 Sep 2026 and is **a proposal, not an answer** —
the 14 questions in it are still open. **I am not a lawyer. Nothing here is legal advice, and
the automated-decision items below are the sharpest example of that: they name a decision that
turns on law and hand it to counsel rather than guessing it.**

| Obligation | Source, and date verified | What Wave 3 must do | Requirement |
|---|---|---|---|
| DPDP Act 2023 s.8 — minimisation and safeguards | baseline §2, §5, verified 24 Aug 2026 | Fixed payload key lists; days-only for managers | SEC-3, SEC-8, PRIV-2 |
| DPDP s.11 — a person's right to information about processing of their own data | baseline §2, verified 24 Aug 2026 | Time and Pay **are** that access path for 400 people with no desk login. This slice discharges an obligation rather than creating a risk | PRIV-6 |
| DPDP s.12 / correction | baseline §2, verified 24 Aug 2026 | The correction flow — **and it must actually reverse the consequence, or be described honestly** | PRIV-8 |
| DPDP s.8(7) / Rule 8 — storage limitation | counsel's note §1.3, 18 Sep 2026 | **Attendance Deduction has no retention period and nobody has proposed one.** Counsel's note covers performance records and driver location; this record is in neither table | PRIV-11 |
| DPDP — grievance redressal, named officer, response clock | baseline §2, verified 24 Aug 2026; counsel's note records the product route as **"Not built. Handled by hand"** | A named contact and a real route from the Why? sheet | PRIV-9 |
| GDPR Art 22 — automated decisions with a significant effect; human intervention, express a view, contest | baseline §4, verified 24 Aug 2026. **⚠ Applicability unconfirmed** — the founder has still not said whether we process EU data | **The late-coming rule is squarely in scope if GDPR applies.** DPDP has no direct Art 22 analogue, which is why counsel's question 13 asks the same thing under Indian law | PRIV-6 to PRIV-10 |
| Counsel's note, question 13 — an automated flag against a named worker | `docs/legal/2026-09-18-...`, 18 Sep 2026, **unanswered** | The same question, asked for the late-coming rule rather than the driver scorecard | Q1, Q2 |
| CERT-In — log content, 180-day India-resident retention | baseline §3, verified 24 Aug 2026; residency gap 6 Sep 2026 | No salary figure, punch time or slip name in a log | PRIV-5 |
| OWASP ASVS 5.0 L2 — access control | baseline §5, verified 24 Aug 2026 | Ownership checked **before** any `ignore_permissions`, proved by test | SEC-10 |
| EU AI Act | baseline §4, verified 24 Aug 2026 | **Not engaged.** Nothing in this slice is AI-shaped. The Article 5 prohibitions are not approached | PRIV-4 |

---

## Abuse cases

| # | Actor, state and path | What must happen |
|---|---|---|
| **A1** | **Sandeep**, a manager, signed in, sends `get_payslip` with a report's Salary Slip name | Refused, with **"That payslip is not available."** — the identical message he gets for a slip that does not exist and for a draft, so the answer cannot be used to probe (SEC-4) |
| **A2** | **The same manager** sends the Why? endpoint a report's Attendance Deduction name, obtained from the team late list, which returns `name` today (*verified in code*, `hr_api.py:2843`) | Refused, identically. **And the endpoint must not take a deduction name from the caller at all** — it resolves the deduction from the caller's own slip line, server side (SEC-6) |
| **A3** | **An employee on a tenant without payroll** calls `get_payslips` by hand | Refused by the real feature gate, in wording identical to a not-entitled refusal (SEC-2, SEC-4) |
| **A4** | **An HR user** opens the portal's Pay screen hoping to see an employee's slip | There is no path. Pay is own-only for every persona, and the desk is the place with roles and an audit trail (PRIV-1) |
| **A5** | **A manager** receives the weekly deduction email for a report who had days taken from Sick Leave | The email carries **days only**: no amount, no `explanation` text, no leave type, no punch times. The employee's own email is unchanged (SEC-8) |
| **A6** | **A manager** opens a month for somebody outside their line | `_subject:251` refuses, and the refusal is a sentence, not a stack trace (SEC-9) |
| **A7** | **Anyone** calls `get_shift_types` — including a user with no Employee record and a leaver with an enabled login | Scoped and gated. Today it returns every shift type in the tenant with `ignore_permissions=True` (SEC-7) |
| **A8** | **An employee** corrects 4 August in September and expects the ₹548 back | **The product must not promise this.** Either the deduction is genuinely re-opened (Q1 option B or C), or the screen says plainly what happens next and who to ask (PRIV-8). What must never happen is the spec's current sentence, which is false |
| **A9** | **An employee** asks who decided the deduction | The screen names a **person or a role with a working contact route**, and says the calculation was made automatically by a rule on a date (PRIV-6, PRIV-9) |
| **A10** | **A tester** patches `has_feature` to `True` and every payroll-gate test passes | Forbidden. The gate tests call the real function on a tenant whose `features` list genuinely lacks the key (SEC-2) |
| **A11** | **A support engineer** reads a portal error report from the Pay screen | No salary figure, no slip name, no deduction name, no punch time — a time and a short reference matching an Error Log entry (PRIV-5) |
| **A12** | **Anyone** retrieves a payslip PDF from a browser history, a proxy log or a shared link | The PDF is generated on demand behind the same own-only check, its arguments are in a POST body, and no pre-generated file is written to a web-readable path (SEC-15) |
| **A13** | **A curious HR user** asks for a report of the ten latest employees | No such payload, no such endpoint, no such export. A per-person lateness tally exists for the person it is about and for their own manager in days; there is no comparison anywhere (PRIV-4) |
| **A14** | **A leaver** with an enabled login opens Time | Their own months, until the login stops. They appear in **nobody's** team late list (SEC-12) |
| **A15** | **A developer** adds a second caller to `_deduction_rows`, passing a filters dict built from a request argument | **Must be impossible by shape, not by care.** `_deduction_rows` takes a raw `filters` dict and reads with `ignore_permissions=True` (*verified in code*, `hr_api.py:2752-2759`). Wave 3 adds the second caller. SEC-5 requires the signature to change first |
| **A16** | **HR** cancels an Attendance Deduction after the Salary Slip is submitted | The product cannot reverse the payment. The screen and the runbook must say who does, and how (PRIV-8, Q1) |

---

## Requirements

### Security

| ID | Requirement | How it is tested |
|---|---|---|
| **SEC-1** | **Every whitelisted function in `time_api.py` and `pay_api.py` is safe on its own, from the commit that adds it**, with its Guest-refused, wrong-persona and scope cases in the same commit | Registry test enumerating the functions **from the module**, not from a hand-written list (`043 AC-42`) |
| **SEC-2** | **`get_payslips` gains `@requires_feature("payroll")`**, above `@frappe.whitelist()`, matching `get_payslip:1561` and `download_payslip:1594`. **And the gate tests call the real `subscription.has_feature`** — no test in this slice may patch `has_feature`, `requires_feature` or `enabled_features` to `True`. A patched gate makes every entitlement test pass while proving nothing | `043 AC-30`, extended: a tenant whose `features` list genuinely lacks `payroll` gets a refusal from all three endpoints; **plus a static check that no test patches the gate**; **plus a decorator-order check** that the feature decorator is above the whitelist on all three |
| **SEC-3** | **`get_time` and `get_pay` return only named keys, and the exclusions are named.** The `me` block is exactly `employee`, `employee_name`, `designation`, `department`, `image`, `company` and never `date_of_birth`, `gender`, `cell_number`, `date_of_joining`, `reports_to` or `branch`. **`get_payslips` is fixed in the same slice:** *verified in code*, `hr_api.py:1533` returns `"employee": emp`, the whole `_get_employee` row (`:152-160`). Pay is the screen people screenshot for a bank and attach to a support ticket | Exact key-set assertion per persona on `get_time`, `get_pay` **and `get_payslips`** (`043 AC-6`, extended to the third); a static check that no Wave 3 module passes a `_get_employee` result through unfiltered |
| **SEC-4** | **Every refusal on Pay reads identically, whatever the reason.** "You are not allowed", "that record does not exist", "it is a draft" and **"your tenant did not buy payroll"** must be one message — `_own_payslip`'s existing "That payslip is not available." — or the refusal itself tells the caller what the tenant has, or what exists. This binds all three payslip endpoints and the Why? endpoint | `043 AC-31`, extended to the feature-off case and to the Why? endpoint: four causes, one byte-identical message and one status code, asserted together in one test so a later change to one of them fails |
| **SEC-5** | **`_deduction_rows` stops taking a raw filters dict.** *Verified in code* (`hr_api.py:2752-2759`) it takes `filters` and reads with `ignore_permissions=True`; its one caller today passes the caller's own employee. Wave 3 adds the second caller, which is exactly when this shape fails. **Change the signature to take an employee id that the function resolves and checks itself**, and make the refusal explicit — never an empty or partial filter dict, because in Frappe an empty dict means every record | A direct assertion that the function cannot be called with an arbitrary filter (signature test), **plus** a call as a manager, a store HR user, a Vendor User and a caller with no Employee record, each returning zero rows by refusal rather than by an empty result |
| **SEC-6** | **The Why? endpoint never takes a deduction name from the caller.** It takes the caller's own Salary Slip line, resolves `Salary Detail.additional_salary` → `Additional Salary.ref_docname` → Attendance Deduction **on the server**, and checks the resulting deduction's `employee` against the caller's own Active Employee before reading a single violation row. A client-supplied deduction name is not an input to any Wave 3 endpoint | `043 AC-28`, strengthened: (a) the endpoint's signature accepts no deduction name; (b) another person's slip line is refused identically; (c) a caller's own slip line whose linked deduction belongs to someone else — a data fault — is **refused, not shown** |
| **SEC-7** | **`get_shift_types` is scoped, gated and loses `ignore_permissions`.** *Correction to the spec:* **Shift Type has no `company` field** (*verified in code*, `hrms/hrms/hr/doctype/shift_type/shift_type.json`), so `043 AC-52`'s "the caller's company's only" cannot be implemented as written. The scope must be by something that exists — Q3. Three things hold whatever is chosen: the caller must have an **Active Employee record**; the read must not carry `ignore_permissions`; and the list must not be every shift type in the tenant | Per-persona test once Q3 is answered; a caller with no Employee record is refused; a static check that the function carries no `ignore_permissions`; **and `043 AC-52` is rewritten before it is implemented** |
| **SEC-8** | **The manager's deduction email is rebuilt, not trimmed.** *Verified in code*, `attendance_deduction.py:182-205`: one `frappe.sendmail` sends the identical `self.explanation` body to the employee **and** the manager. Four rules: **(1) separate bodies** — the employee's is unchanged; the manager's is composed for a manager. **(2) The manager's body carries days only** — no `lwp_amount`, no stored `explanation` text, **no leave type**, no punch times, no per-day violation list. **(3) The subject line** carries the employee's name and the week; nothing else. **(4) Separate `sendmail` calls**, so a future change to one body cannot reach the other recipient. *The leave-type clause is the real leak here and it is not what the defect report said — see "The three live defects"* | A rendered-body assertion per recipient, on a fixture where `deduct_from_leave_first` is on and days came from **Sick Leave**: the manager's body contains no currency symbol, no leave type name and no minute figure; the employee's body is byte-identical to today's |
| **SEC-9** | **`attendance_correction._subject:251` is the whole control for opening another person's month, and it is tested as such.** No Wave 3 endpoint reaches a month, a day sheet, a punch time or a correction for another person by any other path | Per-persona test: a manager inside their line succeeds; a manager one step outside is refused; a store HR person inside `_may_review`'s allowance succeeds and outside is refused; the refusal is a sentence, not a trace |
| **SEC-10** | **Ownership is checked before `ignore_permissions` is raised, and the test proves the order, not the presence.** This binds `_own_payslip`, `_deduction_rows`, `download_payslip`'s print flag, and anything Wave 3 adds. `time_api.py` and `pay_api.py` carry **no** `ignore_permissions` of their own | For each such helper, call it with a caller who fails the check and assert the refusal happens **before** any read — assert on the query count as well as on the exception (`043 AC-43`, strengthened from "presence" to "order") |
| **SEC-11** | **Retiring `get_attendance_calendar` and `submit_attendance_request` means removing them from the whitelist, in their own commit.** Deleting the panel is not the control; the endpoint is. `submit_attendance_request` is the weaker path that skips the reason check and carries `ignore_permissions=True` — while it is callable, every reason and review-status guarantee in this slice has a hole beside it | `043 AC-18` plus a **call-by-hand test** expecting a missing method, and `043 AC-19`'s proof that no Attendance Request can be created from the portal without a reason |
| **SEC-12** | **Every "who am I" lookup in this slice resolves an Employee with `status = "Active"`, through one helper**, and a rehire with two Employee records resolves to the Active one everywhere | `043 AC-46`; a static check that no Wave 3 module queries Employee by `user_id` without `status` |
| **SEC-13** | **No module-level cache and no mutable global in the new modules**, because one worker serves several sites. Any cache uses `frappe.cache()` or `frappe.local`, keyed by user. **The shift cache in the late-rule run is a per-call dict and must stay one** | Static check on both modules (`043 AC-43`) |
| **SEC-14** | **A caller with no Employee record is refused explicitly, not filtered by an absent value.** No Wave 3 query may run with an employee filter of `None` | Per endpoint: call as a user with no Employee record; assert empty **and** assert the scoped query did not run |
| **SEC-15** | **The payslip PDF stays on demand, own-only, and leaves nothing behind.** No pre-generation, no bulk download, no file written to a web-readable path, no slip name in a query string. The session must survive the download — `download_payslip` deliberately avoids `set_user` and that must not be undone | `043 AC-23` plus: a static check for a pre-generation path; a check that the download's arguments are in a POST body; a check that no generated file remains on disk after the response |
| **SEC-16** | **Everything drawn from data is escaped, in Jinja and in the browser.** Wave 3's panels go into Wave 1's include files, so 034 SEC-10's check must be extended to them rather than assumed. A salary component name and a leave type name are both tenant-editable text | A scan for `innerHTML` with API data; a DOM test with a salary component named `<img src=x onerror=alert(1)>` |

### Privacy

| ID | Requirement | How it is tested |
|---|---|---|
| **PRIV-1** | **Pay is own-record only for every persona, including HR and a tenant System Manager, on every portal path.** There is no "view as" and no HR lookup in the portal | Per-persona test across all three payslip endpoints and the Why? endpoint |
| **PRIV-2** | **A manager receives a report's late **days** and nothing more** — no amount, no `explanation`, no leave type, no minute figures, on screen or in a payload. `043 AC-16` pins today's payload; this requirement extends it to every new Wave 3 path and to the email (SEC-8) | `043 AC-16`, plus a payload key-set assertion on every team-facing Wave 3 response |
| **PRIV-3** | **A leave type is the employee's own.** It appears on their own Leave tab and their own Why? sheet, and nowhere a manager or a colleague can reach — including the "Past leave" rows labelled "Taken by the late-coming rule" | Payload test: a manager's Wave 3 responses contain no `leave_type` for any employee but themselves |
| **PRIV-4** | **No ranking, no league table, no comparison of colleagues by lateness — in any payload, on any screen, in any export, behind any flag.** The employee sees their own record; a manager sees days for their own line. `02` §18.4 refuses this in writing and I am turning the refusal into a testable requirement, because a running per-person tally is one product decision away from a leaderboard | A static check that no Wave 3 payload contains a sorted-by-lateness list of more than one employee; a payload test that no team response carries a rank, a position or a percentile |
| **PRIV-5** | **No salary figure, punch time, slip name or deduction name reaches a log, an error message, a notification body or a push preview.** The page-error code is a time plus a short reference matching an Error Log entry. Refusals use `access.log_refusal` | Log-capture on a normal call, a refused call and a failed call, for both screens; a mail-capture test on the "payslip is ready" path |
| **PRIV-6** | **The automated decision must be described truthfully and completely.** The Why? sheet must tell the employee, in plain words: **(a) that the calculation was made automatically by a rule, with no person reviewing the individual case**; (b) **when** it ran and **which rule** it applied; (c) the inputs — the days, the true minutes, which were free; (d) the arithmetic; (e) where the days came from (leave and/or pay); (f) **what to do if it is wrong, truthfully** (PRIV-8); (g) **who to contact**, by name or role, with a working route (PRIV-9). *This is the obligation DPDP s.11 and, if it applies, GDPR Art 22 put on this feature — and the reason this section is a requirement and not background* | A content test on the rendered sheet asserting all seven elements are present, with two different rule fixtures so no element is a hard-coded sentence |
| **PRIV-7** | **The accountable human must be a person, not a function.** "HR" is not a name. The rule must carry, or the tenant must configure, **one named accountable owner**, shown on the Late rule tab and on the Why? sheet. **Fail-closed default until Surbhi decides (Q2): where no owner is named, the Why? sheet says the calculation is automatic and names the tenant's HR contact from the existing settings; it must never show a blank, and it must never imply that a person reviewed the case** | A test with an owner set and one with none; the second shows the fallback and never an empty name; a static check that no sentence in the sheet asserts human review |
| **PRIV-8** | **The remedy the screen offers must be the remedy that exists.** **Verified in code** — `late_rules.py:208-215` skips any Attendance Deduction already submitted, in the weekly run and in `run_for_range`, so correcting the attendance day afterwards does **not** reverse the deduction. The spec's proposed sentence *"fix the day first — the rule follows the attendance record"* is **false and must not ship**. Whichever option Q1 takes, the screen must state truthfully: what correcting the day does, what it does not do, that a submitted deduction is reversed only by a person cancelling it, and that a deduction already paid in a submitted slip needs a payroll correction | A test that the sheet's remedy text matches the behaviour of the code, driven from a fixture where a correction is approved **after** the deduction was submitted: the assertion is on the deduction's `docstatus` and the ledger, and the text must agree with it |
| **PRIV-9** | **A contest must have a route, a recipient and a clock.** Counsel's note of 18 Sep 2026 records the grievance route as *"Not built. Handled by hand."* Wave 3 must not ship a "contest this" affordance that leads nowhere. **Minimum, and my recommendation: the Why? sheet carries a named contact and one sentence saying how to raise it** — it does not need a workflow to be honest. If Surbhi wants a recorded, clocked contest, that is its own slice and I would recommend it (Q2) | A content test that the contact is present and comes from tenant configuration, not from a literal; a check that no control claims to lodge a contest unless one is actually recorded |
| **PRIV-10** | **Showing the decision must not become a new record about the person.** Wave 3 does not log what an employee was shown, does not record that they read it, and does not infer acceptance from a close. `02` §17 says this and I am making it a requirement, because "they saw the explanation" is a tempting thing to store and it is a new personal-data record with no purpose tag and no retention | A static check that no Wave 3 endpoint writes on a read path; a check that no new DocType, field or log line records a view |
| **PRIV-11** | **Attendance Deduction has no retention period, and Wave 3 must say so rather than inherit one.** Counsel's note of 18 Sep 2026 covers performance-review records and driver location; **this record is in neither table.** It is decision-bearing about a person's pay, so it must survive an erasure request under legal hold — and "survives for ever" is what Wave 1 already learned is not a lawful long-term answer. Wave 3 changes nothing here; it must **record the gap, name it as a question for counsel, and not create a second, undocumented copy of the data** | Assert that Wave 3 adds no DocType, no field and no patch; the question goes to counsel with the date (Q5) |
| **PRIV-12** | **Nothing in this slice is AI-shaped.** No rating, no inference, no emotion, voice or facial analysis, no passive behavioural monitoring, no individual-level surveillance, no personal data reaching a model prompt. **There is no model anywhere in this slice, so there is no redaction boundary to build** — stated so nobody later assumes one exists | A static check that no Wave 3 module imports or calls a model client |

---

## §18.4 answered concretely — the late-coming rule as an automated decision

The brief asked me to say what the legal note's requirement means in practice. Here it is,
with what is specified, what is missing and what is a decision rather than a requirement.

**What it is.** A weekly scheduled job (`late_rules.process_previous_week:240`) reads every
covered employee's punches, counts violations past a threshold, applies a free allowance,
multiplies by a per-violation day rate, rounds up, takes the result from leave and then from
pay, creates an Additional Salary, and submits — **with no person reviewing the individual
case, and no gate between the calculation and the money.** *Verified in code:*
`_process_week:201-238`, `attendance_deduction.on_submit:63-73`, `apply_deduction:76`.

| Element | What is true today | What Wave 3's spec gives | Verdict |
|---|---|---|---|
| **The accountable human** | Nobody is named. The rule record has settings and no owner. "HR" is a function | `02` §18.4 says "the tenant's HR" | **Not enough.** A function cannot be contacted, cannot be held to an answer and cannot appear in a grievance file. **PRIV-7** requires one named owner, with a fail-closed fallback |
| **Where a human can intervene — before** | Real: the rule's thresholds, exempt grades, leave types, `process_from` | Named | **Adequate**, and it is genuine control — but it is control over *the rule*, not over *this decision about this person* |
| **Where a human can intervene — during** | **Nowhere. There is no step between the calculation and the submitted Additional Salary** | Not addressed | **The gap.** Whether to add one is Surbhi's call (Q1), not mine. I can say what the absence costs: every contest is retrospective and every remedy is a reversal |
| **Where a human can intervene — after** | HR can cancel the Attendance Deduction, which cancels the Additional Salary (`:175-180`) — **but only while the Salary Slip is unsubmitted.** After payment, the product has no route | `02` §18.4 says "HR can cancel", without the qualification | **Materially incomplete.** PRIV-8 requires the qualification to be on the screen |
| **What the employee is told** | Today: one technical email built from `build_explanation` | Wave 3's Why? sheet — the days, the minutes, which were free, the arithmetic, where the days came from, the settings | **The best part of this slice, and close to sufficient.** PRIV-6 adds the three elements missing from the spec: *that it was automatic*, *when and under which rule*, and *who is accountable* |
| **How they contest it** | The correction flow, plus asking HR informally. **No grievance route exists in the product** (counsel's note) | "Fix the day first — the rule follows the attendance record" | **Wrong, and it is the P1.** Verified in code: a submitted deduction is never recomputed (`late_rules.py:208-215`). PRIV-8 and PRIV-9 |
| **Is a human accountable for the outcome?** | In substance, no — the rule is configured once and runs weekly | Not claimed | **Honest, and it is the thing to decide.** Q1 |

**Is what is specified enough?** For **transparency**, nearly — with PRIV-6's three additions
it becomes genuinely good, and better than most HR products manage. For **intervention and
contest**, **no**: the spec's remedy sentence is false, the accountable human is a function,
and the grievance route does not exist. Those three are fixable inside Wave 3 without a new
slice. **A human gate before the money moves is a separate slice and a separate decision, and
I recommend it** — but I am not requiring it here, because it is a product and payroll choice
with a real cost, and because the transparency this slice delivers is worth shipping either
way.

**I am not a lawyer.** Whether an automatic deduction from wages, with no human in the loop,
is lawful under Indian law — and what the worker must be told and able to do — is counsel's
question 13 of 18 September, asked about the driver scorecard and **unanswered**. It applies
word for word here, to a rule that is **live on a client tenant today**, which the driver
scorecard is not. That is Q5, and it is the sharpest question in this document.

---

## Questions

### Must know — these block the requirements or the build

| # | Question | My reading, and the fail-closed default meanwhile | Owner | Blocks |
|---|---|---|---|---|
| **Q1** | **A submitted deduction is never recomputed. What does the Why? sheet tell the employee to do?** Three options: **(A)** tell the truth and stop — the sheet says correcting the day fixes future weeks and that a submitted deduction is reversed only by HR cancelling it, and names who to ask. **(B)** make a correction approved for a week with a submitted deduction **flag** that deduction for HR review, without automating any reversal. **(C)** re-open and recompute automatically — I do **not** recommend this: it would let one approval move money with no human at all, which is more automation, not less | **Recommendation: A now, B in Wave 4.** A is honest and costs a sentence; B closes the loop without automating money. **Until Surbhi answers, option A is the fail-closed default and the spec's current sentence must be struck** | Surbhi | PRIV-8, and the last section of the Why? sheet |
| **Q2** | **Who is the named accountable human for a deduction, and is a recorded contest in scope?** | A named owner on the rule, shown on both screens. A recorded contest is a separate slice and I would recommend it, not require it here. **Until answered: the fallback in PRIV-7 — say it is automatic, name the tenant's HR contact, never imply human review** | Surbhi | PRIV-7, PRIV-9 |
| **Q3** | **How is `get_shift_types` scoped, given Shift Type has no `company` field?** | Simplest honest answer: the shift types **in use in the caller's own company** through Shift Assignment, plus the caller's own `default_shift`. `043 AC-52` must be rewritten before it is implemented, or it will be quietly dropped. **Until answered: require an Active Employee record and drop `ignore_permissions`** — that alone removes the worst of it | Surbhi, with the engineer | SEC-7 and `043 AC-52` |
| **Q4** | **`get_team_late_list` returns a `detail` array of per-violation dates and punch times for each direct report** (*verified in code*, `hr_api.py:2832-2834`), three lines above a comment saying a manager never receives per-day punch times. Is that intended? | A manager may already see a report's day sheet through `_subject`, so this is probably permitted — but **the comment and the code disagree, and one of them is wrong.** Wave 3 renders this screen, so it should be settled now. **Until answered: leave the behaviour, fix the comment, and pin the payload with a test so it cannot widen** | Surbhi, with the engineer | Nothing in the build; PRIV-2's payload assertion |
| **Q5** | **For counsel, and it is the sharpest question here.** Question 13 of the 18 September paper asked whether an automated flag against a named worker is acceptable under Indian law with a human confirming it. **The same question applies to the late-coming rule, which deducts money automatically with no human confirming anything, and which is live on a client tenant today — unlike the driver scorecard it was asked about.** What must the worker be told, and what must they be able to do, before it reaches their pay? **And what retention period applies to an Attendance Deduction record** (PRIV-11)? | I cannot answer either and will not guess. **Meanwhile: ship the transparency (PRIV-6), tell the truth about the remedy (PRIV-8), name a human (PRIV-7), and do not add automation** | Counsel, commissioned by Surbhi | Nothing in Wave 3's build. It blocks any claim that this feature is compliant, and it blocks the **wording confidence** of the Why? sheet |

### Should know

| # | Question | Owner |
|---|---|---|
| Q6 | **D-3 — is base ÷ calendar days the right daily wage?** Not a security question, but it becomes one the moment the method is shown to 400 people: a wrong method explained carefully is worse than a right number shown quietly. I agree with the analyst — ship the Why? sheet without the arithmetic line until it is confirmed | Surbhi, with a payroll or legal advisor |
| Q7 | Does `notify_manager` stay on at all on the two client tenants until SEC-8 ships? Turning it off is a one-tick mitigation available today | Surbhi |

---

## Worries — not findings

1. **`frappe.sendmail` with two recipients.** I could not verify whether Frappe queues one
   message per recipient or one message to both. If it is the latter, each recipient sees the
   other's address in the header — a minor disclosure, but the wrong one to discover later.
   SEC-8's "separate `sendmail` calls" removes the question either way. **I could not check
   it: the Frappe source is in the bench container, not this repository.**
2. **`_may_review` tests submit permission, not a role.** Who can decide a correction is
   whatever each tenant's permission setup produces. I cannot enumerate it from the code.
3. **`Salary Detail.additional_salary` is assumed populated on every deduction line.** The
   spec confirms one real case and says one case is not a rule. If it is ever empty, the Why?
   control must be absent, not broken — and an absent control on a real deduction is a
   transparency gap, not just a UI bug.
4. **The demo data cannot show most of this working.** One of 212 deductions reached pay.
   Until more do, a passing Pay test proves very little. Wave 1's lesson 1.

### What must exist in the data before each control is observable

| Control | What the data must contain |
|---|---|
| SEC-2, SEC-4 | A tenant whose `features` list genuinely lacks `payroll`, **and** submitted slips on it |
| SEC-4, SEC-6 | Two employees with slips; one deduction each; one slip in draft |
| SEC-8 | A deduction where `deduct_from_leave_first` is on and days came from a named leave type, with `notify_manager` on and a manager with a `user_id` |
| PRIV-8 | A correction approved **after** its week's deduction was submitted |
| PRIV-6, PRIV-7 | Two rule fixtures with different settings, one with a named owner and one without |
| SEC-9 | A manager one step outside another manager's line |

---

## Residual risk — each with an owner and a date

| # | Risk | Owner | Date | State |
|---|---|---|---|---|
| **R1** | A successful read of another person's pay or punch times leaves no signal. Refusals are logged; successes are not | Security & privacy engineer, with DevOps | Logging first step **2026-10-15**; detection slice **2026-11-30** | **Carried from Wave 1 R3.** For the most sensitive screen in the product this is the risk I would raise first if the dates slip |
| **R2** | No repo-wide `ignore_permissions` counter in CI; SEC-10's checks cover named helpers only | Security & privacy engineer (feature map B4) | Baseline script **2026-10-31**; gate on the next commit | **Carried from Wave 1 R4.** Wave 1 recorded the gate as due before Wave 2 adds endpoints; Waves 2 and 3 are both here |
| **R3** | An automated deduction reaches pay with no human in the loop, and no lawful-basis answer from counsel | Surbhi, with counsel | **Question to counsel by 2026-10-15**, alongside the 18 Sep paper's 14 | **Not accepted — open.** Wave 3 makes it visible and contestable; it does not make it lawful or unlawful. A control that is only explained is still only explained |
| **R4** | Attendance Deduction has no retention period and no legal-hold rule. It is decision-bearing about pay and is currently kept for ever | Security & privacy engineer, with counsel | **Proposal to counsel by 2026-10-15**; a rule by **2026-12-15** | **Not accepted — open.** Wave 3 creates nothing new, so it is not made worse; it is named here because nobody else owns it |
| **R5** | Alvoraa staff reach client tenants through one shared `Administrator` login, so a read of a customer's **payroll** data cannot be traced to a person | Surbhi, with me | `ALV-93` | **Recorded (W1D-18).** Worth re-stating at Wave 3's scale: this is the slice where the data behind that login is at its most sensitive |
| **R6** | A store HR person whose Branch User Permission is narrowed to a single doctype is treated as company-wide (`access.py:233` fails open) | Live check: Surbhi. Code fix: engineer, `ALV-86` | Live check **2026-09-30**; fix **2026-11-15** | **Carried from Wave 1 R6** |
| **R7** *(new)* | A manager's own line already gives them a report's punch times through `_subject`, and the team late list adds a convenient per-violation list of them (Q4). Proportionate to a duty of care, or surveillance-shaped? | Surbhi | Decide at the strategy gate | **Proposed for acceptance with the payload pinned.** My recommendation: accept, pin the fields with a test, and fix the comment that says otherwise |
| **R8** *(new)* | The payslip PDF is rendered by wkhtmltopdf in the web worker, 1–3 s of CPU per call. A deliberate loop by one signed-in employee is a cheap way to make the tenant slow. Not a data risk; an availability one | DevOps, in `07` | Before the Pay screen reaches a tenant | **Not accepted — hand to DevOps.** A per-user rate limit on the download is the obvious answer and it is not in the spec |

---

## Assumptions

- `[ASSUMPTION]` `Salary Detail.additional_salary` is populated on every deduction line that
  came from an Additional Salary. One real case is confirmed in the spec; one case is not a
  rule.
- `[ASSUMPTION]` Frappe queues one Email Queue entry per recipient. **Not verified — the
  Frappe source is in the bench container, not this repository.** SEC-8 removes the dependency.
- `[ASSUMPTION]` `access.permitted_employees()` behaves as its docstring and slice 030's tests
  say. *Verified in code* that it exists (`access.py:237`).
- **Unknown — I could not check these:**
  - Whether `notify_manager` is currently **on** for any tenant. It decides whether Defect 1
    is leaking today or only would. **Access I would need:** a read of the Attendance Deduction
    Rule rows on `dtc`, `aahr` and the local copy. I did not probe production and will not.
  - Whether any Salary Slip has already been submitted carrying a deduction whose attendance
    day was later corrected. That would make PRIV-8 a live grievance, not a design question.
    **Access I would need:** the same, plus a read of Attendance Request approvals.
  - Which roles hold submit permission on Attendance Request on each tenant.

---

## Verdict for this slice

**Not ready to build. One P1 of mine, plus five spec changes.**

**P1 — must be settled before the Why? sheet is written.** The proposed remedy sentence is
false: `late_rules.py:208-215` never recomputes a submitted deduction, so correcting the day
does not reverse the money. Q1 decides what replaces it. **The sentence must be struck from
`02` §18.4 today, whatever Q1 decides,** because it is the one line in these two specs that
would be read by an employee as a promise.

**What must change in `02` before code:**

1. **PRIV-8 / §18.4** — strike the false remedy sentence; replace it per Q1.
2. **PRIV-6, PRIV-7** — the Why? sheet must say it was automatic, when and under which rule,
   and name an accountable human. §18.4 has none of the three as a check.
3. **SEC-7 / `AC-52`** — rewrite it. Shift Type has no `company` field, so "the caller's
   company's only" cannot be built as written (Q3).
4. **SEC-8 / `AC-17`** — the email fix is not "remove the amount", because the amount is not
   there. It is: separate bodies, separate sends, days only, **and no leave type**. `AC-17`
   as written would pass while the real leak survived.
5. **SEC-3 / `AC-6`** — extend the fixed-key-list check to **`get_payslips`**, which returns
   the whole Employee row today. This is Wave 1's own lesson, live, on the Pay screen.

**Two extensions to checks the spec already has:** `AC-30`'s gate tests must call the real
`has_feature`, with a static check that no test patches it (SEC-2); and `AC-31`'s uniform
refusal must include the **feature-off** cause and the Why? endpoint (SEC-4).

**Decisions for Surbhi, not requirements:** Q1 (the remedy), Q2 (named human and whether a
recorded contest is in scope), Q3 (shift-type scope), Q4 (the team late list's punch-time
detail), Q6 (D-3's wording), Q7 (turn `notify_manager` off in the meantime), and the
acceptance of R7 and R8. **Q5 goes to counsel and only Surbhi can commission it.**

**No P0 in this slice.** No cross-tenant path, no secret in a log, no personal data reaching
a model, and no live exposure of one person's pay to another that I could demonstrate. The
three handed-over defects rank **P1 (payslip gate), P2 (the email), P3 (shift types)**.

**Debt this document leaves behind, labelled:**
**intentional trade-off** — no human gate before a deduction reaches pay (Q1, R3);
**temporary debt** — Attendance Deduction retention, removed when counsel answers (R4);
**acceptable simplification** — shift-type scoping by assignment rather than a new field (Q3);
**dangerous debt** — **none is left sitting quietly.** The false remedy sentence would have
been exactly that, which is why it is the P1 at the top rather than a row in a table.

---

## Handoff note

**To the analyst:** the five spec changes and two check extensions above. Every `043 SEC-n`
and `043 PRIV-n` needs an acceptance criterion; eight have no home in §10 today, and PRIV-6
to PRIV-11 are the ones that will be hardest to write as observable checks. Ask me rather
than guessing the oracle.

**To the engineer:** change `_deduction_rows`'s signature **before** you write the Why?
endpoint, not after. A function taking a raw filters dict and reading with
`ignore_permissions=True` is safe exactly as long as it has one careful caller, and Wave 3 is
the commit that gives it a second.

**To the test engineer:** four tests here are easy to write so they prove nothing.
`AC-30`'s gate test must not patch the gate. `AC-31`'s refusal test must compare **all four**
causes in one assertion. `AC-17` must assert on the **rendered body**, per recipient, with a
leave-type fixture. And PRIV-8's test must be driven from a correction approved *after* the
deduction was submitted, asserting on the deduction's `docstatus` — a test written the other
way round will pass and prove the opposite.

**To me, at review:** SEC-5 first (the filters-dict shape), then PRIV-8 (does the screen tell
the truth?), then SEC-4 (are all four refusals genuinely identical?), then SEC-8's rendered
bodies.
