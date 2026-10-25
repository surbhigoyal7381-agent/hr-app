---
slice: 066-grooming-red-mark
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-10-24
status: draft, revision 1 - written before the functional spec
inputs: 01-product-brief.md (all sections, including "Surbhi's decisions", "Surbhi's answers to the open grooming questions" and "Change to Q5", 22 Oct 2026 - these win); security-compliance-baseline.md (verified 24 Aug 2026, 61 days old, not stale); compliance-feature-map.md; memory legal-retention-rules-2026-09.md; 063 and 065 01c as models. Code read on origin/dev at e0fe3f22 (24 Oct 2026). Two read-only scripts on dtc.alvoraa.co, 24 Oct 2026 (settings and counts only, no names, nothing written, rolled back).
---

# 066 · Security and privacy requirements: the grooming red mark

*I did not write the brief. I am specifying here, not reviewing. Four mechanisms below are my own
choices, not the brief's: the mark is a **submitted** record that is cancelled rather than deleted
(PRIV-3), the slip refuses to submit when marks changed (SEC-9), one `may_mark` function (SEC-1), and
the interim legal cap (SEC-10). At `06`, somebody other than me should check those four.*

The brief's §9 item 2 ("only the manager marks; HR only removes") is **superseded** by "Change to Q5":
the direct manager **and** HR may mark. Everything below follows the later decision.

---

## 0 · Bad news first

**1. This is very likely a "fine" in law, and the law on fines has four conditions the design does
not meet yet. (P1 - blocks switching it on at DTC, not the build.)**
Surbhi's own words: *"a deduction as a fine of not grooming well."* The Code on Wages, 2019 is in
force from 21 Nov 2025. Its **section 19** (fines) says, in summary *(Obligation - secondary sources and
the bare-act page read 24 Oct 2026; I am not a lawyer)*:
- a fine may be imposed only for acts listed in a **notice approved in advance by the appropriate
  government** (or prescribed authority), and **shown at the workplace**;
- **no fine until the employee has had a chance to show cause against it**;
- the total fines in one wage period may **not exceed 3% of the wages payable** for that period;
- fines go in a **register**, and the money may only be used for purposes that benefit the employees;
- no fine on anyone under 15; no recovery in instalments or after 90 days.

What this means here, plainly:
- At ₹100 a day, a Junior on about ₹12,000 a month hits 3% (₹360) after **4 marks**. Surbhi decided
  "every marked day is charged, no allowance". If the law applies, the 5th mark would be an unlawful
  deduction the employee can claim back. SEC-10.
- "Chance to show cause" needs the employee to **know** before the money is taken. See point 2.
- DTC needs an **approved list of fineable acts** that names grooming. I could not check whether it has
  one. Its rule document is not in the repo (brief §1).
- **The same question hangs over the ordinary red marks** (lateness), which are on DTC payslips from
  slice 067. That is wider than this slice. I raise it in §11 as dangerous debt, for counsel.

**2. "The employee is told the same day" is true for nobody at DTC who would be marked.**
*(Verified by running it, 24 Oct 2026.)*
- 445 Active staff. **0** have any email on the Employee record. **0** have a mobile number.
- **10** have a login: 7 managers and 3 HR people. **0** ordinary staff have one.
- **0** field-app phones are registered.
- Outgoing email is muted on the site and no outgoing Email Account exists.

So the bell notice the brief describes reaches only a marked **manager**. The 438 other staff see
nothing in the product until the payslip, which is too late for "show cause". This is the brief's
own "front page test" failing: *"without telling them - not defensible."* PRIV-2 and Q2.

**3. The brief's plan to add `Grooming Mark` to `manager_scope.SCOPED_DOCTYPES` would leave the record
open, not closed. I recommend not doing it. (Verified in code and by running it.)**
- `SCOPED_DOCTYPES` works by User Permissions. A User Permission only narrows a doctype it applies to.
- At DTC, **none** of the 10 logins has an own-Employee User Permission that applies to all doctypes
  (count 0). Each has one row **per named doctype** (about 45 doctypes each). A new doctype is on none
  of those lists.
- So if the `Employee` role is given read on `Grooming Mark`, nothing narrows it: **every login would
  read every mark**. Adding it to `SCOPED_DOCTYPES` adds 425 manager rows but still does not cover the
  managers' or HR's own records, and cannot say "today only", "never yourself" or "not Contract".
- The fix is the pattern already used for Employee Checkin: a `has_permission` and a
  `permission_query_conditions` hook, plus all rules in the record's own controller. SEC-1, SEC-4.

**4. Four DTC staff, not three, would be priced at ₹0.** *(Verified by running it.)* 3 Permanent staff
have a blank `dtc_grade`, and 1 has `External`, which has no rate in the rule set. The rule set also
holds a `No leaves` grade at ₹0 (nobody has it today). SEC-7 refuses to mark all of them.

**5. Two of the brief's worries are already answered.** *(Verified by running it.)*
- The `Grooming Red Value` row in DTC's active salary structure is **₹0**, with no formula. Nobody
  loses money from it. (Brief top note 3 and Q2: closed.)
- The component is a Deduction and does **not** depend on payment days, so a fine is not pro-rated.

**6. The rule set is still switched off at DTC** (enabled = 0, draft), and DTC has **no salary slips**
at all. Nothing in this slice is live, and nothing is a leak today.

---

## 1 · What I checked, and how

| Fact | Where | Label |
|---|---|---|
| `ENGINE_LINES` is the one list of engine pay lines; the comment already names this slice's line | `payroll_slip.py:61-66` | Verified in code |
| `_set_additional_salary` replaces, never adds: same amount writes nothing; a new amount cancels and amends; 0 cancels | `payroll_slip.py:151-207` | Verified in code |
| The slip hook runs only while the slip is a draft (`docstatus != 0` returns) | `payroll_slip.py:268-270` | Verified in code |
| A failure writing the lines rolls all of them back and leaves a note on the slip | `payroll_slip.py:225-253` | Verified in code |
| `payroll_slip.py` has **2** `ignore_permissions` (lines 183, 204) and is **not** in the SEC-16 ceiling list | `test_portal_security_010.py:731-806` | Verified in code |
| Grade rate: `mark_rates` row whose `grade` equals the Employee's `grade_field`; no row means rate 0 | `payroll_slip.py:116-124` | Verified in code |
| Contract: the rule set's `category_field` (DTC: `employment_type`) and the category's `earns_marks`; an unlisted category earns marks | `payroll_rules_apply.py:180-200, 276`; `payroll_month.py:206-208` | Verified in code |
| `rule_set_for(company)` returns the **enabled** rule set or None | `payroll_rules_apply.py:66-77` | Verified in code |
| `permitted_employees()` gives System Manager and Administrator **everyone**; HR their companies (and branches); anyone else nobody; every status, not only Active | `hrms/.../access.py:252-308` | Verified in code |
| `decided_as` labels a System Manager "HR", because `permitted_companies` returns every company for them | `attendance_correction.py:1244-1273`, `access.py:193-205` | Verified in code |
| `team_days` for any user with submit on Attendance Request reads **all Active employees on the site**, not `permitted_employees()` | `attendance_correction.py:1533-1554` | Verified in code |
| `_subject` lets a manager open the month of anyone in their **whole** line, not only direct reports | `attendance_correction.py:324-330` | Verified in code |
| `refuse_own_submit` (before_submit) and `refuse()` (ids-only security log) exist and can be reused | `access.py:28-53, 184-190` | Verified in code |
| No Comment / ToDo / DocShare guard exists on dev (065's is not merged) | `hooks.py` on origin/dev | Verified in code |
| DTC: 445 Active; 403 Permanent, 42 Contract; all 42 Contract report to a manager; 20 report to nobody | read-only query | Verified by running it |
| DTC grades: Junior 428 (386 Permanent + 42 Contract), Senior 13, External 1, blank 3 | read-only query | Verified by running it |
| DTC rule set: enabled 0; `grade_field` = `dtc_grade`; `category_field` = `employment_type`; rates Junior 100, Senior 200, No leaves 0; Contract `earns_marks` 0 | read-only query | Verified by running it |
| DTC: 7 HR users (enabled); 0 with a Branch permission; 1 enabled System Manager; 7 managers, all with logins, none of them HR | read-only query | Verified by running it |
| DTC time zone: Asia/Kolkata. Payroll frequency: Monthly | read-only query | Verified by running it |
| `dtc_grade` and `employment_type` are at permission level 0 (063 SEC-17 not yet done) | read-only query | Verified by running it |
| 405 people punched in the last 7 days | read-only query | Verified by running it |

---

## 2 · Threat model, four lines

**Who wants this, and what is the cheapest way?** Not an outsider. (1) A **manager with a grudge**
marking one person day after day, or the whole team - cheapest by tapping the tick. (2) **HR acting
out of spite** on a past day nobody saw - cheapest from the desk. (3) A **curious colleague or a
skip-level manager** reading who was fined for what - cheapest through REST if the record's read is
not gated (§0 point 3), or through the month screen a manager can open for their whole line. (4) A
**marked manager** (one of the 7 logins) making themselves unmarkable by editing their own `dtc_grade`
to `External`, or halving the fine Senior → Junior (063 SEC-17 is not done). (5) A comment box used to
write about someone's religion or body.

**Blast radius of one mistake.** One person-day per wrong mark (₹100-200). The top of the scale is
**one company's payroll month**: if the rule-set gate (SEC-6) fails, marks open at every tenant; if the
legal cap (SEC-10) is wrong, every heavily marked person at DTC is over-deducted in the same month.
Cross-tenant: not reachable - one tenant per site, and every rule reads the subject's own company.

**What becomes possible that was impossible before.** A manager can now cut a named person's pay, daily,
by a judgement about their appearance, with no second person involved. HR can do the same for any past
day in the month. That is the compliance event.

**How would we find out?** The record itself (who marked, as what, when; who removed it and why) and
the HR monthly view by marker (PRIV-6). **What we would not see:** a mark the employee never heard about
(PRIV-2), and a manager who quietly stops marking one group of people and not another - an absence of
marks leaves no trace. I do not ask for a control for the second; I name it.

---

## 3 · Data inventory

Classes follow `compliance-feature-map.md` A1. A1 is not built, so they are declared here and applied
by hand.

| Field or object | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| `Grooming Mark.employee` (link) | sensitive (it names who was fined) | Who the fine is for | Q-C2 (counsel); no purge in this slice | Subject, marker, subject's direct manager for today's row, HR in scope (SEC-4) |
| `mark_date` | sensitive | The day the fine is for | as above | as above |
| `reason` - one value from a fixed list in code | sensitive - **a judgement about a person's appearance** | Say why, to the employee and in the register | as above | as above |
| `marked_as` - `Manager` or `HR`, set by the server | internal | Accountability; the day rule that applies | as above | as above |
| `told_in_person` (Check) - only if Surbhi chooses option (b) in Q2 | sensitive | Evidence of the chance to show cause | as above | as above |
| `removal_reason` - one value from a fixed list, set only when removed | sensitive | Why a fine was withdrawn (dispute upheld, wrong person, mistake) | as above | as above |
| Who marked / when (`owner`, `creation`); who removed / when (`modified_by` on cancel, Version row) | internal | Audit | as above | HR in scope; subject sees the marker's name |
| Grooming count and ₹ on the slip and in the desk report | sensitive (pay) | Price the slip | Slip retention, as today | The subject (slip), HR (report) |
| Bell notice (Notification Log) to the subject | sensitive | Tell the person, same day | As Frappe keeps Notification Log | The subject only |

**Not collected, on purpose:** no photo, no free text, no note, no comment, no copy of company, branch,
grade or money on the mark. The rupee figure is worked out when the slip is priced, never stored on the
mark.

---

## 4 · Access intent, including who must NOT see what

| Actor | May | Must NOT |
|---|---|---|
| **Direct manager** (`reports_to` of the subject; Active; enabled login) | Mark a direct report **today**, once. Undo **their own** mark until midnight. See today's mark on each direct report's row | Mark a past or future day. Mark themselves, a Contract person, someone not their direct report, someone with no punch today. Remove a mark made by HR or by another manager. See marks on skip-level people. See marks after the day except their own |
| **HR** (HR Manager / HR User; the subject inside `permitted_employees()`; if the user has an Employee, it is Active) | Mark any day from the 1st of the current month to today, until that person's slip is submitted. Remove any mark in scope until then. See marks in scope; run the monthly view | Mark or remove anything about themselves. Act outside their companies or branches. Act after the slip is submitted |
| **Employee (the subject)** | See their own marks: date, reason, who marked. Dispute by speaking to HR | Edit, cancel or delete their own mark, on any door. See anyone else's marks |
| **Skip-level manager** (2+ levels up) | Nothing about grooming | See a grooming line on a report's month or team row (`_subject` and `team_days` depth "all" let them open those screens) |
| **Colleagues** | Nothing | See any mark, count or notice |
| **System Manager / owner / CXO** | Nothing by default (Q3) | Mark anyone. Read individual marks, until Surbhi says otherwise |
| **Contract staff** (42) | Nothing changes for them | Be marked at all |
| **Leaver with a live login** | Nothing | Mark, remove or read anything |
| **Guest** | Nothing | Reach any path here. Nothing is `allow_guest` |

**New-Frappe-app checklist: not engaged.** No app is installed. No public page, no guest access, no self
sign-up, no new role.

---

## 5 · Obligations engaged

I am not a lawyer. These are engineering readings of published sources.

| Obligation | What it asks of this slice | Source and date checked |
|---|---|---|
| **Code on Wages, 2019, s.19 (fines)** - in force 21 Nov 2025 | Approved notice of fineable acts; show cause before the fine; 3% of the period's wages at most; a register; proceeds for employees' benefit | Bare-act page (advocatekhoj) and secondary sources, **24 Oct 2026**. State and Central Rules were still being finalised in early 2026 - **counsel, Q-C1** |
| **Code on Wages, s.18(4)** | All deductions together at most 50% of wages | Same sources, 24 Oct 2026. Not reachable by this slice alone; noted for counsel |
| **DPDP Act 2023 + Rules 2025** - legitimate use for employment (s.7(i)), notice, purpose limitation, security | A human judgement about a named person, used for one purpose (the fine); told to the person; read by few | Baseline §2, verified 24 Aug 2026 (61 days, not stale); s.7(i) reading from secondary commentary, 24 Oct 2026. Substantive duties expected from about May 2027 - counsel |
| **Counsel's retention rules, 18 Sep 2026** | Performance records: employment + 6 months, then erased; **no indefinite soft delete**. Wage records were left open | Memory `legal-retention-rules-2026-09.md` |
| **Equality / religious dress** | The reason list must not reach religious dress, body or appearance beyond clothing | Brief §12; **counsel, Q-C3** |
| **CERT-In 180-day log residency** | Unchanged gap (baseline §3a). No new log stream here | Baseline §3, verified 24 Aug 2026 |
| **OWASP ASVS 5.0 L2** | Access control on every request; no data beyond need in responses | Baseline §5 |

**No AI, no automated judgement.** A person decides every mark. The system only multiplies a person's
decision by a rate. GDPR Art 22 and the AI Act are not engaged.

**DPIA: not required by a rule I can name, but I recommend a one-page note before switch-on** because
this is a daily judgement about appearance that cuts pay. It goes in `docs/security/` only if Surbhi
agrees (Q9). I do not make it a gate.

---

## 6 · Abuse cases

| Who | Tries | What stops it |
|---|---|---|
| **Manager** | Marks the whole team every day | One mark per person per day (SEC-2); same day only (SEC-3); the legal cap limits each person's monthly loss (SEC-10); HR's view shows marks per marker (PRIV-6) |
| **Manager** | Marks the same person every day | As above. PRIV-6's second view (marker × person) shows it |
| **Manager** | Marks last Tuesday, or tomorrow | SEC-3: refused, every door |
| **Manager** | Marks a skip-level person, a colleague's report, or a Contract person | SEC-1: refused, every door |
| **Manager** | Removes a mark HR made | SEC-5: refused |
| **HR** | Marks out of spite, for a day nobody saw | Needs a punch that day (SEC-3); the name is on the record and told to the person; PRIV-6 counts HR marks too |
| **HR** | Marks someone in another branch or company | SEC-1: `permitted_employees()` |
| **HR or a manager** | Marks themselves, or removes their own mark | SEC-1, SEC-5: refused, no role exempt |
| **Subject** (a manager with a login) | Cancels or deletes their own mark through REST | SEC-5: refused; nobody has delete |
| **Subject** | Sets own `dtc_grade` to `External` to become unmarkable, or Senior → Junior | **Not stopped today.** 063 SEC-17 must land first (SEC-7) |
| **Curious colleague** | Reads marks through `/api/resource/Grooming Mark` | SEC-4: the record's own hooks |
| **Skip-level manager** | Opens a report's month and reads the grooming line | SEC-4 point 3 |
| **Anyone with read** | Writes a comment ("his beard ...") on the mark | SEC-8: comments refused |
| **Anyone** | Shares or assigns the mark to someone | SEC-8: share and assignment refused |
| **A script** | Creates 300 marks through `insert_many` | Every record still meets every rule in the controller (SEC-1-3). Bulk = many single marks, each visible in PRIV-6 |
| **System Manager** | Edits the reason list in Customize Form to add "Beard not trimmed" | SEC-11: the controller only accepts reasons from the list in code |
| **Departing employee** with a live login | Marks people on their last day | SEC-1: the marker must be an Active employee |
| **Guest** | Any of it | Nothing here is `allow_guest` |

---

## 7 · Requirements

Each says what must be true and how a test proves it. The analyst must trace every one to an
acceptance criterion, or record Surbhi's decision not to adopt it.

### Security

**SEC-1 · One function decides who may mark whom, and the server applies it on every door.**
One function, `may_mark(employee, date, user)`, returns the capacity (`Manager` or `HR`) or a refusal
with its reason. It is the **only** definition. The record's controller calls it on `validate` and again
on `before_submit` (so desk, REST, import and the portal all meet it), and the screen calls the same
function to decide whether to show the tick - so the button and the guard cannot disagree (the 060
lesson). The user may pass:
1. **Not self.** The subject is not the caller's own Employee. `refuse_own_submit` is also hung on the
   record's `before_submit`, as for Attendance Request. No role is exempt.
2. **Subject is Active**, and the date is on or after their joining date.
3. **Subject earns marks** - the rule set's category for them has `earns_marks` (Contract: no). Read
   through the same rule-set fields the engine reads, never by the word "Contract" in code.
4. **Capacity, derived, never typed:**
   - **Manager** if the caller's **Active** Employee is the subject's `reports_to`. This wins, as in
     `decided_as` (nobody at DTC is both today).
   - else **HR** if the caller holds **HR Manager or HR User**, the subject is inside
     `permitted_employees(user)`, and, if the caller's login is linked to an Employee, that Employee is
     Active (lesson 3). **Holding System Manager alone is not HR** - `permitted_employees()` gives a
     System Manager everyone, so the HR-role check is required (Q3).
   - else refused.
5. **The day rule for that capacity** (SEC-3).
6. **The rule set is on** (SEC-6) and **the rate is above 0** (SEC-7).

`marked_as` is set by the server from point 4. There is no argument for it on any endpoint, and a value
sent in a request body is ignored.
*Ladder:* rung 4. Frappe's role permission (rung 1) cannot express points 1-6, and User Permissions
cannot express "today", "never yourself" or "not Contract" (§0 point 3).
*Test:* through the portal endpoint **and** `POST /api/resource/Grooming Mark` (insert + submit), as each
actor: (a) direct manager, report with a punch today → saved, `marked_as` = Manager; (b) the same body
with `marked_as: "HR"` → stored Manager; (c) skip-level manager → refused; (d) manager of another team
→ refused; (e) self, as manager and as HR → refused; (f) Contract report → refused; (g) Left subject →
refused; (h) HR in scope → saved, HR; (i) HR with a Company permission that excludes the subject →
refused; (j) HR with a Branch permission, subject in another branch → refused; (k) System Manager with
no HR role → refused; (l) HR user linked to a **Left** Employee, login still enabled → refused; (m) a
manager whose own Employee is Left, login still enabled → refused; (n) the screen's tick flag equals
`may_mark` for every row in the fixture.

**SEC-2 · At most one live mark per person per day, and the pay counts days, not rows.**
The controller refuses a second mark (draft or submitted) for the same employee and date. Removed
(cancelled) marks do not count, so a mark can be made again after removal. No database unique index -
it would block re-marking after a removal. Two markers in the same second could both pass the check, so
**the pay counts distinct dates**, never rows.
*Test:* (a) a second mark the same day → refused, whoever makes it; (b) mark, remove, mark again →
allowed; (c) two submitted marks for one date written straight to the table → the slip charges one day.

**SEC-3 · The day rules, in the site's time zone.**
"Today" is `frappe.utils.nowdate()` - the site's time zone (DTC: Asia/Kolkata), never the server's
(the host runs Europe/Berlin).
- **Manager:** the mark's date is today. Nothing else.
- **HR:** from the **1st of the current calendar month** to today `[ASSUMPTION: the pay month is the
  calendar month - DTC's structures are Monthly; Q8]`. Never a future day.
- **Both:** the subject has **at least one Employee Checkin on that date** - a fine for how someone
  came to work needs them to have come to work. So: never on a full-day leave, a holiday they did not
  work, or an absence (Q4). The brief already required a punch for the manager.
- **Both:** refused when a **submitted** Salary Slip for the subject covers that date (SEC-9).
The rules are checked when the mark is made **and** when it is submitted, so a draft made through REST
yesterday cannot be submitted today.
*Test:* (a) manager, yesterday → refused; tomorrow → refused; (b) HR, the 1st of this month → allowed;
the last day of last month → refused; tomorrow → refused; (c) a day with no punch → refused, both
capacities; (d) a draft made yesterday by a manager, submitted today → refused; (e) a time-zone test,
with the site set to Asia/Kolkata: at 00:10 IST (still the previous evening in Berlin) the manager may
mark the new IST day and may not mark the day before.

**SEC-4 · Who may read a mark is decided by the record's own hooks, and fails closed.**
`Grooming Mark` gets a `has_permission` and a `permission_query_conditions` hook in `hooks.py`, the
pair already used for Employee Checkin. They are the **one** read gate, used by desk lists, the form,
REST, `get_list` / `get_count`, link search and reports. A reader passes only when one of these holds:
1. they are the **subject** (their Active Employee is the mark's employee);
2. they are the **marker** (`owner`);
3. they are the subject's **current direct manager** and the mark's date is **today** (so their team
   row can show it, and a refusal of a second mark is not a surprise);
4. they hold **HR Manager or HR User** and the subject is inside `permitted_employees()` (with lesson 3's
   Active check).

Anything else: nothing, and the list condition matches no rows (never "no condition").
- The `employee` link has **`ignore_user_permissions` = 1**, so DTC's per-doctype User Permission rows
  cannot half-apply and the hooks are the only gate. `Grooming Mark` is **not** added to
  `manager_scope.SCOPED_DOCTYPES` (§0 point 3; Q6).
- **Screens:** the line on a day in the Attendance month (`month()`) and the state on a team row
  (`team_days`) are added **only** when the same gate passes for that viewer. A manager who opens a
  skip-level person's month (allowed today by `_subject`) sees no grooming line.
- **DocPerm:** `Employee` - read, create, submit, cancel (the controller narrows every one); **HR Manager
  and HR User** - read, create, submit, cancel, report; **HR Manager** - export (the fines register,
  Q-C1). **Nobody** - write after submit except the removal reason (PRIV-3), delete, share, email,
  print, import, amend by anyone other than through the same rules.
*Test:* as each actor in §4: (a) `get_list` and `get_count`; (b) `frappe.get_doc` + `has_permission`;
(c) `/api/resource/Grooming Mark` and `/api/resource/Grooming Mark/<name>`; (d) `search_link`. The
subject, marker and HR in scope see exactly their rows; a colleague, a skip-level manager and a System
Manager without an HR role get nothing and a 403 on one record. Plus: (e) **a login with no User
Permission rows at all** and the `Employee` role → nothing (this is the DTC shape); (f) a mark HR
made yesterday on a manager's report → not visible to that manager; (g) `month()` for a
skip-level viewer carries no grooming key; (h) the doctype's DocPerm rows equal the list above
exactly.

**SEC-5 · Removing a mark: the manager their own until midnight, HR in scope until the slip; the
subject never.**
Removal is Frappe's **cancel** (PRIV-3). On `before_cancel` the controller allows it only when:
- the caller is the **marker**, the mark is `marked_as` Manager, and its date is **today**; or
- the caller is **HR** for that subject (SEC-1 point 4) and no submitted slip covers the date;
- and in **both** cases the caller is not the subject (`is_own_record` → refuse; no role exempt).
A manager's undo is allowed even if the reporting line changed during the day - an undo only ever helps
the employee. A removal reason from the fixed list is required (PRIV-3).
*Test:* (a) manager undoes own mark today → removed; (b) tomorrow → refused; (c) manager removes an HR
mark on their report → refused; (d) HR removes a manager's mark → removed; (e) HR out of scope → refused;
(f) after a submitted slip → refused, both; (g) the **subject** cancels their own mark through
`frappe.client.cancel` → refused; (h) `DELETE /api/resource/Grooming Mark/<name>` as any user (HR
included) → refused, record intact.

**SEC-6 · Nothing in this slice is reachable where the pay rule set is off.**
One check: the subject's company has an **enabled** rule set (`rule_set_for`), the same switch slice 063
uses (its SEC-15). No company or site name in code.

| Company state | Tick on screen | Server | Slip |
|---|---|---|---|
| Enabled rule set | shown where `may_mark` passes | marks allowed under SEC-1-3 | GRV line priced |
| Rule set exists, **not enabled** (DTC today) | not shown | **refused** | nothing |
| No rule set (every other tenant) | not shown | **refused** | nothing |

Switching the rule set off is also the rollback: marking stops at once; existing marks stay, unpriced.

*Amended 25 Oct 2026 (pre-push review P-1; Surbhi chose option 2):* grooming has its own switch.
It is on only while the `Grooming Red Value` Salary Component exists and is not disabled; every
row above is "off" whatever the rule set says while the component is missing or disabled. The
rollback is now ticking Disabled on that component.
*Test:* the three states × (screen flag, portal endpoint, REST insert, slip). The middle row must use a
disabled **draft** rule set, as DTC has.

**SEC-7 · A mark that would cost ₹0 is refused, and the grade that sets the rate is HR's to change.**
`may_mark` refuses when the subject's grade has **no `mark_rates` row or a rate of 0**: today 3 blank, 1
`External`, and anyone ever given `No leaves`. The message tells the marker to ask HR to set the grade.
Reason: a mark that prices at ₹0 is a record about someone's appearance with no purpose, and the notice
would say "costs ₹0".
The rate is **read when the slip is priced**, as for ordinary reds - nothing about money is stored on the
mark. So **063 SEC-17 must be done before switch-on**: today any of the 10 logins can edit their own
`dtc_grade` (level 0, verified), and a marked manager could set it to `External` or `Junior`.
*Test:* (a) blank grade → refused, with the message; (b) `External` → refused; (c) a grade with rate 0 →
refused; (d) Junior → ₹100 a day on the slip, Senior → ₹200; (e) release check: `dtc_grade` is at
permission level 1 at DTC (063 SEC-17's check).

**SEC-8 · No free text can be attached to a mark, and no one else can be given it.**
- **Comments refused.** A small `validate` on Comment refuses any row whose reference is a Grooming
  Mark. If 065's SEC-3 guard (Comment, ToDo, DocShare) lands first, add the doctype to its list - one
  line - instead of a second function.
- **Share and assign refused** by DocPerm: no role has `share`, so Frappe refuses a share and refuses
  assigning the mark to anyone who cannot already read it.
- No `email_append_to`, no web view, no print format, `allow_import` 0, `allow_rename` 0,
  `track_views` 0, no field in global search.
*Ladder:* rung 2 for share and assign (DocPerm). Rung 4 for comments - I know of no doctype setting
that switches comments off `[verify on the bench]`.
*Test:* (a) `add_comment` on a mark → refused, 0 Comment rows; (b) `frappe.share.add` → refused;
(c) `assign_to.add` to a user without read → refused, 0 ToDo, 0 DocShare; (d) the meta flags above,
one by one.

**SEC-9 · The slip and the marks always agree; nothing changes after the slip is submitted.**
- **Pricing:** `month_summary` counts the subject's **submitted** marks in the period, by **distinct
  date**, and only on dates the engine did not judge a full-day leave or absence (so a leave approved
  later cannot leave a fine on a day off). `summarise_month` gets `grooming_deduction` = days × the
  grade rate, after SEC-10's cap; `earns_marks = 0` gives 0. **No free allowance** (Surbhi, Q3).
- **The line:** `("Grooming Red Value", "grooming_deduction")` is added to `ENGINE_LINES`. Nothing
  else in `payroll_slip.py` changes. It goes through `_set_additional_salary`, so saving twice writes
  nothing new, a changed figure cancels and amends (trail kept), and 0 cancels.
- **A late mark on a draft slip:** the draft is re-priced the next time it is saved. Because the hook
  does nothing at submit, a draft saved **before** a late mark would be submitted with the old figure.
  So a Salary Slip **`before_submit`** check (only where the rule set is on) recomputes the grooming
  figure and **refuses the submit** if it differs from the slip's live GRV line: "Grooming marks changed
  since this slip was saved. Save it again." One count query. Fails closed.
- **After submit:** no mark can be made or removed for a date the submitted slip covers (SEC-3, SEC-5).
- The GRV component must exist at the company. If it is missing and a grooming figure is due, the whole
  line set rolls back with the existing note (`payroll_slip.py:236-245`). Release check: it exists.
*Test:* (a) 3 marks, Junior → GRV ₹300 on the slip, red and green unchanged; (b) save twice → one
Additional Salary; (c) mark on a draft, save → amended record, the old one cancelled; (d) mark after the
draft was saved, then submit without saving → refused; save, then submit → succeeds; (e) after submit,
mark or remove for that month → refused; (f) a mark on a day later covered by an approved full-day leave
→ not charged; (g) Contract person with a mark written straight to the table → ₹0; (h) the before_submit
check does nothing at a tenant without a rule set.
*Observable only if* the fixture has an **enabled** rule set, a submitted Salary Structure Assignment,
the GRV component, real Employee Checkins on the marked dates, and a Junior and a Senior person.

**SEC-10 · A fine never goes above the legal limit. (Interim, pending counsel - Q-C1.)**
If counsel confirms the mark is a fine under s.19, the month's grooming deduction may not exceed **3% of
the wages payable for that period**. Until counsel says which figure "wages payable" is, the interim cap
uses the engine's `earning_basic` for the month (the smaller base, so it errs toward the employee). When
the cap bites, the report's "why" column says so ("4 grooming reds at ₹100, capped at ₹348 by the legal
limit"). One line in `summarise_month`; no setting.
**Surbhi decides, with counsel, before switch-on:** (a) keep the cap (my recommendation until counsel
answers), or (b) counsel says it is not a fine and the cap is removed in writing. Her decision "every
day charged" stands **within** the limit either way.
*Test:* (a) Junior, Basic ₹12,000, 30-day month, 30 days paid, 5 marks → ₹360, not ₹500, and the note;
(b) 3 marks → ₹300, no note; (c) 0 paid days → ₹0.

**SEC-11 · The reason list is fixed in code, clothing only, and nobody changes it on the site.**
- The reasons are a constant in the module. The controller accepts only those values, so a System Manager
  who adds an option through Customize Form gets a refusal, not a new reason.
- Changing the list is a code change: reviewed, with **Surbhi's and counsel's approval recorded in the
  slice folder** (Q-C3). That is stricter than "System Manager only", and needs no settings page.
- Starting list (brief §12), **pending DTC's wording and counsel**: *Not in uniform · Uniform
  incomplete · No name badge · Wrong footwear.* I dropped "unclean" from the brief's wording - it can hit
  people who cannot afford a second uniform (brief §13). "Wrong footwear" may hit medical or orthopaedic
  shoes: counsel.
- **Never** about religion or religious dress, caste, gender, disability, body, hair, beard, skin,
  jewellery or head covering.
*Test:* (a) a reason not in the constant, sent through REST → refused; (b) the Select options **equal**
the constant; (c) a word test: no reason contains any of a fixed list of words (hair, beard, turban,
hijab, burqa, veil, tilak, bindi, sindoor, kara, skin, weight, jewel, caste, religion, ...), so a future
edit trips CI.

**SEC-12 · No new bypass.**
- **Zero `ignore_permissions`** in the new code. The manager and HR create, submit and cancel as
  themselves - the DocPerm gives the right and the controller narrows it. The bell uses Frappe's own
  notification helper. Reads in the pricing path use `frappe.get_all` keyed on the slip's own employee.
- SEC-16 ceilings: the new doctype controller and the new module at **0**; `payroll_month.py` at 0;
  **add `payroll_slip.py` at 2**, its count today - it has two bypasses and no ceiling, so this slice
  could add a third unseen.
- **Purpose fence (lesson 2, made structural):** the string `Grooming Mark` may appear only in its own
  doctype folder and module, `payroll_slip.py`, `attendance_correction.py` (the two screens), `hooks.py`,
  the desk report, and tests. A test walks every `.py` and `.js` file in our apps and fails on any other
  occurrence - so appraisal, PMS, feedback, Attendance Insights, the org chart or an AI prompt cannot
  start reading it quietly (PRIV-5).
*Test:* (a) SEC-16 passes with the new rows; (b) the occurrence test passes, and fails when a fixture
file naming the doctype is dropped elsewhere; (c) review check at `06`: no `frappe.get_all` on the
doctype in any reader that serves a person other than the slip's employee.

### Privacy

**PRIV-1 · The record holds the least.**
Fields: `employee` (link, `ignore_user_permissions` 1), `mark_date`, `reason`, `marked_as` (read-only),
`removal_reason` (set only on cancel), and `told_in_person` only if Q2 chooses it. Who and when come from
Frappe's own `owner`, `creation`, `modified_by`. **No** copy of company, branch, grade, amount, name or
photo; if the HR view needs the person's name on screen, one `employee_name` fetched from Employee and
nothing more. Name is random (`autoname: hash`), never built from the person or the date. Submittable,
`track_changes` 1.
*Test:* the field list **equals** the above plus Frappe's standard columns; the created name contains
no part of the fixture's employee id, name or date.

**PRIV-2 · The employee is told, the same day - and the product says honestly who cannot be.**
- **Bell:** on submit, one Notification Log to the subject's own user, **only** if that user is enabled
  and the Employee is Active. Fixed fields, built in code, not a Notification record a System Manager
  could edit to add fields (063 PRIV-1): *who marked* (name), *the day*, *the reason*, *what it costs*,
  and *"If it is wrong, speak to HR."* On removal, a second notice: the day, "removed", by whom. Never to
  anyone else - not the manager, not HR, not colleagues.
- **The gap:** at DTC only the 7 managers and 3 HR people have a login, so **no frontline person gets
  the bell** (§0 point 2). The design must not claim "told" for them. The marker's screen says plainly,
  when the person has no login: *"[Name] has no login and will not get a notice. Tell them today, and
  tell them they can speak to HR."*
- **What closes the gap is Surbhi's choice (Q2), and switch-on waits for it.** Options, cheapest first:
  (a) the marker tells the person face to face and the product only reminds them (instruction, not a
  control); (b) as (a), plus a required "I told them in person today" tick stored on the mark
  (`told_in_person`) - self-attested, but evidence for show cause; (c) give staff a way to see their own
  record (logins or the field app) - a rollout, not a slice; (d) SMS or WhatsApp - impossible today
  (**0 mobile numbers on file**), and would need new collection of phone numbers and a new third-party
  processor. **My recommendation: (b) now, (c) when DTC rolls out staff access.**
- **The payslip line** names the number of grooming reds. That is the last notice, not the first.
*Test:* (a) a subject with an enabled login → one Notification Log, to them only, with exactly the fixed
fields; (b) no login → no Notification Log, and the marker's response carries the "no login" message;
(c) a Left subject's login → nothing sent; (d) removal → the second notice; (e) with (b) chosen: a mark
without the tick → refused through REST too.

**PRIV-3 · A removed mark stays accountable - it is cancelled, never deleted.**
The brief said "removing it is deleting it". I recommend against: Frappe's delete keeps a full copy in
**Deleted Document for ever**, which is the "indefinite soft delete" counsel prohibited on 18 Sep, and a
plain delete loses who removed it and why.
Instead: the mark is **submitted** when made (its fields can then never be edited - no silent change of
reason), and **removal is a cancel**. The cancelled mark keeps who marked, as what, when, who removed it
(`modified_by`, Version row), when, and one `removal_reason` from a fixed list: *Marked in error · Wrong
person · Employee showed cause (dispute upheld)*. No role has delete. A removed mark counts nowhere in pay.
*Test:* (a) remove → `docstatus` 2, the four facts above readable by HR, a Version row; (b) 0 Deleted
Document rows after any removal; (c) `reason` changed through `frappe.client.set_value` on a submitted
mark → refused; (d) a removal with no reason → refused.

**PRIV-4 · Retention: no purge here, no "keep for ever", and the conflict goes to counsel.**
Live and removed marks are kept alike until the retention slice (feature map A6) sets the period. This
slice adds **no** delete, purge, archive or retention setting.
The conflict, for counsel (Q-C2): a mark is **both** a judgement about a person (close to counsel's
"performance records": employment + 6 months, then erased) **and** an entry in the **register of fines**,
a wage record with its own minimum. Removed marks are evidence of how markers behave; whether they may be
kept as long as live ones is part of the same question.
*Test:* review check at `06`: no delete, purge or retention code in the diff.

**PRIV-5 · Used for one purpose: the grooming fine. Nothing else reads it.**
Not in appraisals, PMS, feedback, Attendance Insights, Team View counts, the org chart, any dashboard, any
ranking, any AI feature, any export other than HR's register. No branch or company "grooming score" (brief
§4: no scorecard). If grooming ever fed an appraisal, it would become a performance record and counsel's
6-month rule would bind it - that is a separate decision.
*Test:* SEC-12 (b), the occurrence test.

**PRIV-6 · HR sees marks per marker every month, including HR's own.**
Configuration only: two saved Report Builder views on Grooming Mark, scoped by SEC-4's hook - (1) by
marker and month: marks, and how many were removed; (2) by marker and person: marks on each person. HR's
marks appear like anyone's. No server-side threshold, no alert job (my recommendation, Q7): a flag needs a
reader, and the reader is HR looking at view (2). The legal cap (SEC-10) already limits what one person
can lose. **Process control:** in the first month, HR looks at both views weekly; the brief's kill
criteria apply.
*Test:* the two views exist as fixtures; as an HR user with a Branch permission, they show only that
branch's marks.

**PRIV-7 · No personal content in logs or errors.**
Refusals use `refuse()` - ids and rule only, never the reason or a name. A pricing failure's Error Log
names the slip only, as today.
*Test:* force a refusal and a pricing exception → the security log and Error Log hold no fixture name and
no reason text.

---

## 8 · Data that must exist for each test to prove anything

| Test | Without this, it passes and proves nothing |
|---|---|
| SEC-1 (i), (j); SEC-4 (a); PRIV-6 | Two companies, two branches, an HR user with a narrowing Company permission and one with a Branch permission. **DTC has 0 HR users with a Branch permission and appears to have one company**, so on DTC data these show nothing |
| SEC-1 (a)-(d) | A two-level line (manager → report → their report) and a second team |
| SEC-1 (l), (m) | A Left HR user and a Left manager, both with **enabled** logins |
| SEC-3 (c); SEC-9 (f) | Real Employee Checkin rows on some dates and none on others; an approved full-day leave |
| SEC-3 (e) | The site time zone set to Asia/Kolkata in the fixture (the test server may run UTC) |
| SEC-4 (e) | A login with the Employee role and **no** User Permission rows - the DTC shape |
| SEC-7; SEC-9; SEC-10 | An **enabled** rule set with `mark_rates` (Junior 100, Senior 200, one at 0), a submitted Salary Structure Assignment with a non-zero Basic, the GRV component. Without a Basic every figure is 0 and the cap test proves nothing |
| SEC-6 | A **disabled draft** rule set (DTC's shape), not only "no rule set" |
| PRIV-2 (a) | A subject with an enabled login - at DTC only a manager is |

**At DTC, the control is observable only after switch-on and the first marks.** Before then the HR views
read 0, and 0 means nothing (lesson 1).

---

## 9 · Questions

### Must know - each blocks switching it on at DTC (not the build)

**Q-C1 · For counsel: is the grooming red a "fine" under s.19 of the Code on Wages?**
*My reading:* yes - Surbhi calls it a fine for conduct. *Unclear:* whether a pay rule agreed in DTC's
policy is a "fine" or another permitted deduction. *Why it changes the control:* if a fine, DTC needs an
approved notice of acts naming grooming, a chance to show cause before the deduction (PRIV-2), the 3% cap
(SEC-10), a register in the prescribed form (HR's export, SEC-4), and the money used for staff benefit.
*Questions for counsel:* (1) fine or not; (2) what "wages payable" is for the 3%; (3) is a same-day
face-to-face notice with a chance to dispute to HR before the slip enough to be "showing cause";
(4) does the register need fields this record lacks; (5) the same question for the ordinary red marks
(§11). *Default meanwhile:* the cap is on (SEC-10), and the rule set is not switched on for grooming.

**Q2 · For Surbhi: how is a person with no login told?** Options (a)-(d) in PRIV-2. *Default:* (b) - the
required "told in person" tick, and the plain on-screen warning. Switch-on waits for her answer, and for
counsel's answer to Q-C1 (3).

**Q-C3 · For counsel, through Surbhi: the reason list.** DTC's words, checked for religious dress,
disability (footwear) and affordability (clean uniform). Blocks release (brief, already agreed).

### Should know - defaults hold until she answers

- **Q3 · Does the owner / System Manager read individual marks, or mark?** Default: **no** to both - a
  System Manager is not HR for this (SEC-1, SEC-4). They see the totals on slips and in the desk report.
- **Q4 · May a mark be made on a day the person did not punch (leave, holiday off, absent)?** Default:
  **no** - SEC-3. The brief already required a punch for the manager.
- **Q6 · Not adding `Grooming Mark` to `SCOPED_DOCTYPES`** (against the brief's recommendation), for the
  reason in §0 point 3. I can decide this as a security design choice; I ask her to note it.
- **Q7 · A server-side "too many marks" flag?** Default: **none** - two saved views (PRIV-6) and the
  legal cap. If she wants a push: one line in the HR view highlighting a marker over N a month. No job.
- **Q8 · "Current pay month" = calendar month?** Default: yes; HR cannot mark October on 2 November even
  if October's slips are not submitted (same as 063 SEC-6).
- **Q9 · A one-page privacy note (DPIA-style) before switch-on?** Default: yes, short, in
  `docs/security/dpia-grooming-mark.md`. I would write it.
- **The 4 staff priced at ₹0** (3 blank grade, 1 External): HR sets their grade, or they stay
  unmarkable. Default: unmarkable (SEC-7).

### For counsel (no build impact)

- **Q-C2 · Retention** of live and removed marks: fines register (wage record) vs counsel's
  performance-record rule. Blocks the retention slice, not this one. Default: keep, delete nothing.

---

## 10 · Dependencies

- **063 SEC-17** (pay-setting Employee fields HR-only) must be done before switch-on: `dtc_grade` and
  `employment_type` decide the rate and the Contract exclusion. Verified still at level 0 at DTC.
- **067 (ALV-208)** - the slip hook and `ENGINE_LINES` - is on dev. This slice adds one row to it.
- **065 SEC-3** (Comment / ToDo / DocShare guard): reuse it if it lands first (SEC-8).

---

## 11 · Findings against existing code (not SEC items, because they predate this slice)

1. **The ordinary red marks may also be "fines" under s.19, with no cap and no show cause.** *(Inference
   from s.19 and `payroll_month.py:204-211`.)* A DTC employee late on many days loses `deductible_reds ×
   ₹100/200` with no 3% limit. Not live (rule set off, no slips). **Dangerous debt - escalate now**, to
   Surbhi and counsel, with Q-C1 (5). Owner: Surbhi. It belongs to slice 059/067, not here.
2. **`team_days` gives anyone with submit on Attendance Request every Active employee on the site** -
   not `permitted_employees()`, not even the company (`attendance_correction.py:1533-1554`). Lesson 2 and
   lesson 4. *Scenario:* an HR user of company A opens Whole team and sees company B's people and their
   days. **Not live at DTC** as far as I can tell (one company; I did not count companies). SEC-1 makes
   the grooming tick independent of it. P2, owner `hrms-fullstack-engineer`.
3. **`decided_as` records a System Manager's decision as "HR"** (`attendance_correction.py:1271-1273`),
   because `permitted_companies` returns every company for a System Manager. A false label in an audit
   field. P3, owner `hrms-fullstack-engineer`.
4. **The slip hook does not re-price at submit** (`payroll_slip.py:269`), so any change after the last
   save (a late attendance fix, a red) is submitted stale. SEC-9 guards grooming only. The same guard for
   every engine line is a decision for slice 067's owner. P2.

---

## 12 · Worries (not findings - I cannot yet write "this actor, this path, sees this")

- **`insert_many` through REST lets a manager mark many people in one call.** Each still meets every
  rule, so it is speed, not a bypass. I do not ask for a block.
- **A manager who stops marking one group** leaves no trace. Fairness by omission is invisible to any
  view. Named, not controlled.
- **The notice amount can differ from the slip** if HR changes the grade between the mark and payroll.
  The grade is HR-only once 063 SEC-17 lands and every change is recorded, so I accept it.
- **The "told in person" tick is self-attested.** It is evidence, not proof.

---

## 13 · What I could not verify, and what I would need

- **Whether DTC has an approved notice of fineable acts** - needs DTC's rule document (not in the repo).
- **The text of RED-02/04/05** - same document.
- **That Frappe has no per-doctype switch for comments** - needs a look at Frappe 16 on the bench.
- **That a `has_permission` hook cannot grant beyond DocPerm** in this Frappe version - the design assumes
  it only narrows; one bench run confirms it.
- **How many companies DTC's site holds** - one more read-only query.
- **The state rules for the register's form** - counsel.
- **No timing** - the extra count in `month_summary` is one grouped query per person; not measured.

---

## 14 · Subtract pass

Removed on the final read:
- A per-marker threshold job and alert (now Q7, default none).
- A stored rate or amount on the mark - priced at slip time, as reds are.
- Adding the doctype to `SCOPED_DOCTYPES` (§0 point 3) - 425 more rows that would not have gated it.
- A dispute record for disputes HR rejects - not asked for; the removal reason records upheld ones.
  Counsel's Q-C1 (3) may bring it back.
- A database unique index - it would block re-marking after a removal; the controller check plus
  "count distinct dates" does the job.
- A DPIA as a hard gate - kept as a recommendation (Q9).

Kept, and why: SEC-9's submit check (without it a late mark is silently not charged while the register
says it was); SEC-10's cap (law first, one line).

---

## Residual risk

| Risk | Kind | Level | Who accepts | Date |
|---|---|---|---|---|
| Grooming fine may breach s.19 (no approved notice, no show cause, no cap) | **Dangerous debt - escalate now.** Not live; live on switch-on | **P1 - blocks switch-on** | **Surbhi, with counsel (Q-C1)** | open |
| Ordinary reds may be uncapped fines (§11.1) | **Dangerous debt - escalate now** | P1 for the first DTC payroll | **Surbhi, with counsel** | open |
| 438 of 445 DTC staff cannot be told in the product (PRIV-2) | Temporary debt; removed by Q2's choice | **P1 - blocks switch-on** | **Surbhi (Q2)** | open |
| A marked manager can edit their own grade (SEC-7 → 063 SEC-17) | Dangerous debt, already escalated in 063 | P1 - blocks switch-on | Surbhi | open |
| A manager's fairness by omission is invisible | Intentional trade-off | P3 | Surbhi - to confirm | open |
| The "told in person" tick is self-attested | Acceptable simplification, if Q2 = (b) | P3 | Surbhi | open |
| Marks have no retention period (PRIV-4) | Temporary debt; removed by the retention slice after Q-C2 | P3 | **Unowned - Surbhi to name an owner** | open |
| `team_days` HR path is unscoped (§11.2) | Temporary debt; not live at DTC | P2 | `hrms-fullstack-engineer` to propose | open |

---

## Handoff note

To the business analyst: trace every SEC and PRIV item to an acceptance criterion. The five that matter
most: **SEC-1** (one `may_mark`, every door, capacity derived), **SEC-4** (the record's own read hooks;
not `SCOPED_DOCTYPES`), **SEC-9** (slip and marks agree; nothing after submit), **SEC-10** (the legal cap,
pending counsel) and **PRIV-2** (who is actually told). The brief's §9 item 2 is superseded by "Change to
Q5". Write Q2's default (b) and Q4's default (no punch, no mark) into the spec until Surbhi answers.

To the engineer: zero new `ignore_permissions`; give the `Employee` role the rights and let the controller
narrow them. Add `payroll_slip.py` to the SEC-16 ceilings at 2. Do not add the doctype to
`SCOPED_DOCTYPES`. Submittable; removal is cancel; nobody deletes.

To the test engineer: run SEC-4 (e) as a login with **no** User Permission rows - that is DTC's shape,
and the one that would leak. Run SEC-1 and SEC-5 through REST as well as the portal. Every test in §8
fails silently on the wrong fixture.

Sources checked 24 Oct 2026:
[Code on Wages s.19, bare act](https://www.advocatekhoj.com/library/bareacts/codeonwages/19.php) ·
[Nyaaya - deductions from wages](https://nyaaya.org/legal-explainer/what-can-employers-deduct-from-employees-wages/) ·
[Mondaq - labour codes compliance roadmap](https://www.mondaq.com/the-new-labour-codes-in-practice-a-compliance-roadmap-for-employers/1727808) ·
[EY - labour codes effective 21 Nov 2025](https://www.ey.com/content/dam/ey-unified-site/ey-com/en-in/alerts-hub/2025/11/new-labour-codes-implemented-across-the-country-effective-21-november-2025.pdf) ·
[DLA Piper - labour codes update](https://knowledge.dlapiper.com/dlapiperknowledge/globalemploymentlatestdevelopments/2025/government-of-india-notifies-the-labour-codes-ushers-a-new-era-of-compliances) ·
[Bar & Bench - DPDP legitimate use for employee data](https://www.barandbench.com/view-point/navigating-legitimate-use-exemption-employee-data-digital-personal-data-protection-act-2023)
