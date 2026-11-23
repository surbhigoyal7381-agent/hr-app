---
slice: 090-leadership-hr-analytics
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-11-23
status: draft, for Surbhi; feeds the business analyst's spec
tier: 1 (who sees which scope, small-group hiding, aggregates over people)
read_at: worktree .claude/worktrees/090-leadership-hr-analytics, branch slice/090-leadership-hr-analytics, HEAD 412d5361
inputs: [01-product-brief.md (approved 23 Nov), 01a-ux-opportunities.md, 01b-ux-design.md (approved 23 Nov), prototype-v1.html, 07-devops-inputs.md (OPS-1..16 accepted), slice 012 01c and 06]
---

# 090 · People trends: security and privacy requirements

**I recommend. You decide.** No code was changed. I ran no bench, docker or server command. I am not a lawyer; every ⚠ COMPLIANCE item names who decides.

## The short answer

**Bad news first.**

1. **UX-3: yes, the subtraction rule must cover all four: department, employment type, company × branch, and time.** The prototype covers branches only. Its rule is also weaker than slice 012's: it hides exactly one more branch and never checks that the hidden ones add up to the minimum (`prototype-v1.html` lines 105-106, read). The spec must not copy it. Section 5 sets the smallest rule I can show is safe. **It needs three changes to the approved design, each Surbhi's call** (⚠ Q1-Q3): one filter at a time below company, leave types only at the top of the scope, and dropping the "count under 5" rule.
2. **An open risk is carried into this page: a store HR person can be treated as company-wide.** `permitted_branches()` counts a Branch permission only when it applies to all record types or to Employee (`hrms/hrms/alvoraa_hr_core/access.py`, read at 412d5361). A Branch permission narrowed to one record type is ignored, and the person falls back to company scope. This is R6 from slice 034. Its code fix was due 15 Nov with ALV-86. **It is not in this worktree.** DTC narrows its Employee permissions per record type on purpose (memory, 26 Oct). **I could not check what DTC's Branch rows look like.** If any are narrowed, a store HR person would see company-wide leavers, early leavers and leave types on this page. SEC-8 asks for the fix before HR roles get the page.
3. **The adoption measure in the brief (S1) cannot work as written.** It counts users from `log_if_slow`. That function writes only when a call takes over a second, and it writes at `info` level to the `leader_view` logger (`org_figures.py` line 356, read). `access.py` lines 31-36 record that Frappe's default logger level is ERROR in our images, and that `security.log` measured 0 bytes on dev on 19 Nov. **Inference:** `leader_view` lines are thrown away too. I did not open that log file. SEC-9 fixes this with a sink that is proven to write.
4. **Baseline entry was stale.** The DPDP section was last checked on 24 Aug (91 days ago). I re-checked the phase dates and the s.7(i) wording today and updated the baseline (section 4). The CERT-In entry (24 Aug) is also stale and I did **not** re-check it. This slice only relies on it for "logs are in France", which has not changed.

**Requirements set here: 10 SEC, 13 PRIV.** Each says how it is tested.

---

## 0 · What I read and checked

| Checked | How | Label |
|---|---|---|
| Slice 090 brief, 01a, 01b with decisions, prototype, 07 §1 and §2 | Read in the worktree | — |
| `org_figures.py` (whole file): `Scope`, `hr_scope`, `condition`, `attendance_figures`, `leave_figures`, `people_figures`, `log_if_slow`, `PURPOSE` | Read | Verified in code |
| `alvoraa_leader_view_settings.py` and its JSON: minimum 3-10, default 5, bad value reads as 10, System Manager writes, HR Manager reads, change tracking on | Read | Verified in code |
| `hr_api.get_hr_analytics` (line 821 on) | Read. POST only, `requires_feature("analytics")`, HR roles or Administrator, `Cache-Control: no-store`, scope from `hr_scope()` | Verified in code |
| `access.py`: `security_logger`, `log_refusal`, `refuse`, `permitted_companies`, `permitted_branches` | Read | Verified in code |
| "Leadership" role | Only in `NEVER_ORG_ROLES` (`attendance_analytics.py` line 81). No role record or fixture found in this worktree | Verified in code (not found in this worktree) |
| Slice 012 `01c` (SEC-1..22, PRIV-1..16, abuse cases) and `06` (findings, residual risk) | Read | — |
| `ignore_permissions` | My grep in `alvoraa_portal/alvoraa_portal`, `alvoraa_goals`, `hrms/hrms/alvoraa_*`, outside `tests/`: 392 lines | Verified by running it |
| DPDP Rules phase dates; DPDP Act s.7(i) text | Web, 23 Nov 2026 (sources at the end) | Obligation |

**Not checked:** any tenant's data (row counts, how many leavers have no relieving date, how many people have an employment type, DTC's Branch permission rows). Any running system. The Employee JSON (01a read it in `alv089-bench`; I did not).

---

## 1 · Threat model in four lines

1. **Who wants this, and what is the cheapest way in?** Insiders with a valid login. A company head who wants to know who in the 4-person Security team took sick leave, or who in the kiosk left. The cheapest way is not hacking. It is **arithmetic on numbers the page is allowed to show**: company minus the other branches, 3 months minus 1 month, all departments minus the shown ones. Second cheapest: post another company's or branch's name to the endpoint by hand.
2. **Blast radius of one mistake.** One tenant: each tenant is its own site and database (07 §1, red flag 4). A scope bug shows one person **a whole company or every company in the tenant**. A small-group bug points at **one to four people**, and the data is absence and leave type, which can point at illness, pregnancy or family trouble.
3. **What is new?** New **visibility**: a Leadership role that sees nothing today will see company totals. New **figures over time**: leavers, early leavers, leave by type, over five windows with comparisons. **No new personal data is collected.** No decision is made about a person. No data leaves the app (no export, no email, no AI).
4. **How would we find out?** **Mostly we would not.** A leader doing subtraction makes only allowed requests. We can log requests outside scope (SEC-2). We cannot see misuse of what is inside scope. So the small-group rules must be **right by construction and proven by a test**, not watched.

---

## 2 · Data inventory

Classes follow the baseline (`public / internal / sensitive / statutory-id`). **No code applies these classes today** (feature map A1 is not built), so this is a declaration, not a control.

| Field or object | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| Employee `company`, `branch`, `department`, `employment_type`, `status`, `date_of_joining`, `relieving_date` (read to count) | internal | People records | Existing, unchanged | HR in scope. The page only counts them |
| Employee `reason_for_leaving`, `gender`, `date_of_birth`, `grade`, `designation`, `reports_to` | sensitive / internal | — | Existing | **Not selected by this page at all** (PRIV-1) |
| Attendance `status`, `attendance_date`, `company`, `alvoraa_branch`, `employee` (distinct count only) | sensitive | Attendance records | Existing | Same as today. The page returns rates and counts only |
| Leave Application `leave_type`, dates, `total_leave_days`, `status`, `docstatus`, `company`, `alvoraa_branch`, `employee` (distinct count only) | sensitive (leave type can point at health or pregnancy) | Leave records | Existing | Same as today. Leave type leaves the server only under PRIV-8 |
| Leave Application `description` (reason) | sensitive | — | Existing | **Never selected** (PRIV-1) |
| **Group sizes before hiding** (people inside each figure, per group, per stretch of days) | sensitive | Working out the rule | **Memory only, for one request.** Never cached, logged or returned | Nobody |
| **The answer after hiding** (counts, rates, bucket labels, company/branch/department labels in scope) | internal. Still personal data about groups, never "anonymous" | Operational oversight | Not stored (no cache in v1, OPS-15) | The caller |
| Remembered period (one of five values, per user) | internal | Convenience | Life of the user | The user |
| One log line per call (SEC-9) | internal | Detection, adoption measure (S1) | Log rotation (about 2 MB, `access.py` docstring); France, so the CERT-In residency gap stays open | Operators |

---

## 3 · Access intent: who may see what, and who must NOT

"Scope" means the companies and branches the server works out from the caller's roles and User Permissions (SEC-1). The analyst builds the permission matrix from this.

| Persona | May see | Must NOT see | Enforced by |
|---|---|---|---|
| **Company head**: Leadership + one or more Company permissions that apply to Employee | Totals for those companies; "All companies" and By company when more than one; one filter at a time inside one company | Names, employee IDs, dates of a person's absence or leaving, leave reasons, pay. Any figure under the minimum or hidden to protect a smaller group. Any company not in their permissions, in any form, including filter lists. The HR "no relieving date" link | SEC-1-3, PRIV-1-9 |
| **Branch head**: Leadership + Branch permissions that apply to Employee | Their branches together, and each branch, inside the company those branches belong to | Every other branch, the company total, the rest of the company by subtraction, and everything in the row above | SEC-1-3, PRIV-6 |
| **Leadership, no usable permission** (none, or only narrowed to another record type) | The "not set up" page | **Any figure at all**, including headcount | SEC-1 (fail closed) |
| **Leadership whose own Employee record is Left or Inactive** | Nothing | Everything | SEC-6 |
| **HR Manager / HR User** | The same page for `hr_scope()`: their companies, narrowed to their branches when they are store HR. The "no relieving date" count and the Desk link | Other companies or branches. Exact figures the small-group rule hides (names stay in the Desk, under their normal Desk permissions) | SEC-1, SEC-8 |
| **System Manager** without an HR role or Leadership | Nothing on this page (same as `get_hr_analytics` today) | Everything on this page | SEC-1 |
| **Line manager** without Leadership | Nothing new | This page and its endpoint | SEC-1 |
| **Employee** | Nothing | Everything. Their data appears only inside totals that pass the rules | SEC-1, PRIV-2-9 |
| **Guest** | Nothing | Everything | SEC-4 |

---

## 4 · Obligations engaged

**I am not a lawyer.** These are engineering requirements drawn from published sources. The compliance owner is still not a named person.

| Obligation | Source | Last verified | What it means here |
|---|---|---|---|
| DPDP s.7(i): processing "for the purposes of employment or those related to safeguarding the employer from loss or liability" as a legitimate use | Act text on dpdpa.com | **23 Nov 2026** | The likely basis for leadership totals, so no consent screen is designed. **The duty is the employer's** (our customer). ⚠ COMPLIANCE, counsel (CQ1, carried from 012 and still unanswered) |
| DPDP purpose limitation and data minimisation | Baseline §2 | 24 Aug 2026; phase dates re-checked 23 Nov | Totals only; no names, reasons or pay; figures not reused to rate people or managers (PRIV-1, PRIV-11, PRIV-12) |
| DPDP phase dates: Data Fiduciary duties, including s.7, in force **13 May 2027** in most sources | Mondaq/AZB Partners, SCC Online summaries | **23 Nov 2026** | Build to it now. No date changes the design |
| DPDP notice (itemised; Eighth Schedule languages) | Baseline §2 | 24 Aug 2026 | The employer's notice may need to say leaders see totals. The brief puts the privacy-page line later. ⚠ counsel (CQ3) |
| DPDP Rules 2025 Rule 6(1)(c)/(e): access visible in logs, logs kept a year | 012 01c, as quoted on dpdpa.com | 15 Sep 2026 | One line per call (SEC-9). The rotating file keeps about 2 MB, not a year. ⚠ counsel (012 CQ3, open) |
| CERT-In: 180-day logs in India | Baseline §3, §3a | 24 Aug / 6 Sep 2026, **[stale — re-verify]** | Open gap (France). Not caused or fixed here |
| GDPR Art 5, Art 88 | Baseline §4 | 24 Aug 2026, **[stale — re-verify]** | Only if the founder confirms EU exposure (still open). The same design covers minimisation |
| OWASP ASVS 5.0 L2: access control, logging | Baseline §5 | 24 Aug 2026 | Server-side scope, deny by default, refusals logged |
| EU AI Act / GDPR Art 22 | Baseline §4 | — | **Not engaged.** No AI, no automated decision |

**DPDP framing in one paragraph.** The page shows aggregates of employee personal data to the employer's leaders and HR for an employment purpose: knowing whether people are leaving or staying away. Aggregates about small groups are still personal data, because a colleague can work out who they are about. So the design goal is not "anonymous". It is **"no figure about fewer than the minimum number of people can be read or worked out by the person looking."** Section 5 is how.

---

## 5 · UX-3 settled: the subtraction rule

### 5.1 The question

01b UX-3 asked whether the "next-smallest" rule must also cover department, employment type, company × branch, and adjacent periods. **Yes, all four.** Here is why, each with a worked case on the prototype's made-up tenant:

| Cut | How it leaks without the rule | Example |
|---|---|---|
| **Department** | The company total is exact. Show every department but one, and the last one is the difference | Kavya Retail leave days 665; every department shown except Security (4 people) → Security = 665 minus the rest |
| **Employment type** | Same, and worse: **the blank value is a sibling nobody can pick.** The brief says employment type "may be mostly empty". If 398 people have a type and 3 do not, company minus every type = those 3 | Company Left 33; Full-time 30, Contract 3 hidden… and blank (3) never checked |
| **Company × branch** | ERPNext's Branch has no company (`org_figures.Scope` docstring, read). "All companies, Branch X" minus "Company A, Branch X" = Company B's people in Branch X | Two companies sharing a branch name |
| **Branch × department together** | With combined filters, the page becomes a grid. A grid needs the rule along every row and column, and on every parent cut. That is a much bigger build | Civil Lines × Stores × Contract |
| **Adjacent and nested periods** | All five windows end on the same day, and each comparison window is the window just before. So "6 months" minus "3 months" **is** the 3-month comparison, and "1 year" minus "6 months" minus the 6-month comparison is the 5 days from 360 to 365 days ago. A group can pass in each window and still be 3 people in the stretch you get by subtracting | A branch that grew from 3 to 12 people four months ago: 6 months and 3 months both pass; 6 months minus 3 months is the figure for the 3 people |
| **Leave type across cuts** | Fold-into-Other works inside one list. Across lists it does not: company "Maternity 40 days" minus each shown branch's Maternity = the one branch that folded it | The exact maternity/medical case in the brief |

### 5.2 The rule I recommend (the smallest one I can show is safe)

**Words used below.**
- **Cut**: the people a figure is about (the caller's scope, narrowed by a filter).
- **Population of a figure**: the number of distinct employees the figure is counted over, for its own days (PRIV-2 defines each one).
- **Passes**: the population is **0** (nobody, so nothing to reveal) or **at least the minimum** (`min_group_size()`, read fresh on every call; 5 today; 10 if the stored value is bad).
- **Stretch**: the days between two neighbouring window edges. The edges are 0, 7, 14, 30, 60, 90, 180, 360, 365 and 730 days back, which are every end of the five windows and their comparison windows. That gives 9 stretches.

**The rule has four parts.**

| Part | Rule | What it stops |
|---|---|---|
| **A · One filter at a time** (⚠ Q1) | Below company, the caller picks **at most one** of Branch, Department or Employment type, and only **inside one company**. "All companies" shows company totals only | Removes grids and the company × branch leak. Each cut then has exactly one parent: the company (or the branch head's set of branches) |
| **B · Decide once per cut, over time** | For each cut and each figure family (people, attendance, leave days, each leave type), the family is shown **only if its population passes in every stretch**. Then it is shown on all five chips, or on none. Chart series are sent whole or not at all: if any bucket fails, that chart is "Not shared" and its totals stay | Any subtraction between chips, comparisons and windows. Also means a figure does not flip between shown and hidden as the leader taps chips |
| **C · Siblings, including the blank one** | Along the chosen dimension, the siblings are **every** value inside the parent: every branch, every department, every employment type, **and "none set"**, even though nobody can pick "none set". If any sibling fails (part B), hide it and keep hiding the next-smallest (by population, ties by name) until **at least two are hidden and the hidden ones together pass**. A parent with one child: hide the child exactly when the parent is hidden. The same applies to companies under "All companies" | Parent minus shown siblings. Because it is worked out the same way on every request, asking for each sibling in turn gets the same answer |
| **D · Leave types only at the top** (⚠ Q2) | "By leave type" is shown **only** when no filter is applied, for one company. A type is named only if the **people who took it** pass in each of the five window stretches (0-7, 7-30, 30-90, 90-180, 180-365). Otherwise it joins "Other". Other must pass too; if not, the next-smallest named type joins it; if Other still fails, show the total only | The maternity/medical case, within one list and across lists |

**What I removed from the design to make it safe** (⚠ Q3): the rule that hides a **count** under 5 inside a narrowed cut (01b §6: "a count of fewer than 5 (joined, left, an early-leaver cell, pending leave) also shows Not shared"). With exact whole-company totals, a hidden count of 3 is just company minus the others. To keep it honestly, parts B and C would also have to run on the counts. That would hide nearly every narrowed leaver figure. It protects nobody that parts B and C do not already protect, because the population behind that count is already at least the minimum. "2 people left Civil Lines (59 people)" does not point at a person, and the leader can see who is no longer at work. **Keeping a "Not shared" that anyone can work out is worse than showing the number**, because the page then claims a protection it does not give.

**Why this is the smallest safe rule.** Without part A, part C has to run along every filter of the cut and every parent cut: up to 7 cuts and 12 lines per request, plus a property test over 3-dimensional grids. I estimate that doubles the privacy code and its tests. Without part B, the leak between chips stays open. Without part D, leave types need part C for each type along each dimension. Part B's 9 stretches are fixed, so the query count is fixed (OPS-14): one grouped query per family, by sibling and stretch.

**Cost you will see.** A group that was small at any point in the last two years (for example, a new branch with 3 people for a month) stays "Not shared" until the small stretch is older than 730 days. A team of 4 is never shared. In small companies most leave types will show as "Other". This is the rule working.

### 5.3 What remains (residual, in section 11)

- **Ranges, not exact numbers, across separate filters.** Branch A (shown) and Department Security (shown) and the company total give a lower bound for "Security at A". No exact figure.
- **Day-to-day visits.** Windows roll forward each day. A leader who opens the page every day sees each day's change. Day buckets for 1 week already show daily figures, so this adds little. It cannot be stopped without fixed calendar windows.
- **Chart buckets of different sizes.** Week buckets (1 and 3 months) and month buckets (6 months and 1 year) cross at a few short stretches, such as days 30-35. These are not checked on their own. The population of a few working days is close to the whole group, so this is small.
- **What the leader already knows.** A leader who is also a line manager sees their team by name elsewhere. A leader on the shop floor sees who is missing. A group minus the people you know can be small. PRIV-2 removes the caller's own record. The rest is residual.
- **Two leaders pooling their views**, and **the minimum being changed between two views** (012 AB-11, AB-12).

---

## 6 · Abuse cases

| ID | Actor and action | What leaks without a control | Stopped by |
|---|---|---|---|
| AB-1 | **HR Manager of Company A posts `company = "B"`** (or a branch or department of B) to the endpoint by hand | Company B's totals | SEC-2 (refused, logged) |
| AB-2 | **Branch head posts a branch outside their set**, or the same-named branch of the other company | That branch's totals | SEC-1, SEC-2 |
| AB-3 | **Anyone posts extra values**: `min_group = 1`, free dates, a sixth period, two filters at once, `raw = 1` | Figures under the minimum, single-day windows | SEC-2 (fixed inputs; unknown parameters have no effect) |
| AB-4 | **Company head subtracts branches**: company total minus every shown branch | The hidden kiosk (4 people) | PRIV-6 (part C) |
| AB-5 | **Company head subtracts departments or employment types**, including the "none set" group nobody can pick | A small department; the 3 people with no type | PRIV-6 (blank is a sibling) |
| AB-6 | **Company head with two companies** compares "All companies, Branch X" with "Company A, Branch X" | Company B's share of Branch X | PRIV-5 (part A) |
| AB-7 | **Leader subtracts periods**: 6 months minus 3 months, or 1 year minus 6 months minus its comparison | A group's figure for a stretch when it had 3 people | PRIV-4 (part B) |
| AB-8 | **Leader reads leave by type** in a branch, then the company, then each branch | One person's maternity or medical leave | PRIV-8 (part D) |
| AB-9 | **Leader reads the early-leaver row**: "1 of 3 joiners left within a week, Security, Ambala" | One named new joiner | PRIV-2 (cohort is the population), PRIV-4 |
| AB-10 | **Leader rebuilds leavers from shown figures**: headcount now, headcount change, joined | Leavers = start + joined − now, when Left is hidden | PRIV-7 |
| AB-11 | **Leader opens the network tab** to read figures the screen hides, or the headline inputs | Every hidden number | PRIV-3 (hidden = not sent) |
| AB-12 | **Leader reads the filter lists** for names of other companies, branches or departments | Structure of companies outside scope | SEC-3 |
| AB-13 | **Leader inside a group of 5** (their own department) | The other 4 together, since they know their own record | PRIV-2 (caller not counted) |
| AB-14 | **Departing leader**: Employee record Left, login still enabled (ERPNext does not disable it), role and permission still there | Company totals after leaving | SEC-6 |
| AB-15 | **Store HR whose Branch permission is narrowed to one record type** | Company-wide figures (R6) | SEC-8 |
| AB-16 | **Someone adds "Leadership" to the organisation attendance roles** "until the page ships" | Named people and leave types | Already blocked: `NEVER_ORG_ROLES` (`attendance_analytics.py` line 81); SEC-5 keeps it tested |
| AB-17 | **Guest or plain employee** calls the endpoint, or opens the page | Any figure; a heavy query run for nothing | SEC-4 |

---

## 7 · Security requirements (SEC)

**Fixture tenant for the tests** (the analyst may rename): Company "Kavya Retail" with branches of 88, 59, 4 and 38 people; a second company "Kavya Foods" with a branch of the **same name** as one of Retail's; departments including one of 4 people and a group with no department; an employment type filled for 3 people and blank for the rest; one branch that grew from 3 to 12 people four months ago; leave types including one taken by 1 person. Users: company head (one company), company head (two companies), branch head (one branch), branch head (two branches), Leadership with no permission, Leadership with a Branch permission narrowed to Attendance only, a leader whose Employee record is Left, a central HR Manager, a store HR with a normal Branch permission, a store HR with a Branch permission narrowed to Attendance, a System Manager with no HR role, a line manager, a plain employee, Guest.

**SEC-1 · One scope resolver, on the server, fail closed.**
- HR role (HR Manager or HR User) or Administrator → `hr_scope()`, as `get_hr_analytics` does. If the caller holds an HR role **and** Leadership, the HR scope is used. One answer, never a union.
- Leadership only → companies and branches from the caller's **Company and Branch User Permissions that apply to Employee** (applicable to all record types, or to Employee). A permission narrowed to another record type grants nothing. Branch permissions win over Company ones. A branch counts only together with its company.
- No usable permission → the "not set up" answer, with **no figures, not even headcount**, and **no figure query run**.
- Anyone else, including System Manager without an HR role or Leadership → refused (PermissionError).
- **Test:** a table-driven test over every fixture user asserts the resolved scope, including the two "nothing" leaders. A query-count assertion shows the "not set up" answer runs no figure query.

**SEC-2 · Filters are checked against the scope and refused, never trimmed.**
Accepted inputs: a period (one of the five), and at most one of: company (in scope), branch (in the caller's set, and used by employees of the chosen company), department (held by an employee of the chosen company in scope), employment type (an existing value). Anything else is refused with a PermissionError and one `log_refusal` line (rule id, no values). Unknown parameters have no effect.
- **Test:** each of AB-1, AB-2, AB-3 as a real call → refused, one log line read back from the log file (SEC-9), response carries no figure. Two filters at once → refused (if Q1 is yes).

**SEC-3 · Filter lists come from inside the scope only.**
The company, branch, department and employment-type choices are built from employees inside the caller's scope. A branch that is "Not shared" may be listed with that label (01b); a branch outside scope is never listed.
- **Test:** HR Manager of Retail gets no Foods value anywhere in the response; branch head gets only their branches.

**SEC-4 · Endpoint hygiene (OPS-12).**
`@frappe.whitelist(methods=["POST"])`, `@requires_feature("analytics")`, Guest refused, role checked first, `Cache-Control: private, no-store`. The remembered-period save is a POST that Frappe's CSRF check covers, and the page template carries the CSRF token (lesson: ALV-343, a page without the token).
- **Test over real HTTP, not a direct function call:** GET refused; Guest refused; the response header asserted; a save without a valid CSRF token refused for a signed-in user.

**SEC-5 · "Leadership" is a new role with no document permissions.**
Named "Leadership", not "Alvoraa CXO" (012 SEC-4). No DocPerm or Custom DocPerm rows. Giving it, plus a Company or Branch permission, must not widen what the person can read anywhere else.
- **Test:** zero permission rows for the role; for the fixture leaders, `frappe.get_list` row counts on Employee, Attendance, Leave Application, Salary Slip and Employee Checkin are the same or lower after the role and permission are added; a Leadership-only user is refused by `summary(view="organisation")` even when the stored org-roles setting lists Leadership.

**SEC-6 · Access ends on the next request.**
The scope is worked out on every call and never cached. If the caller has an Employee record linked to their user and none of them is Active, the call is refused (ERPNext leaves a leaver's login enabled). Removing the role, the permission or disabling the user takes effect on the next call.
- **Test:** load as a branch head (200); mark their Employee Left → refused; restore; remove the Branch permission → "not set up".

**SEC-7 · SQL is parameterised; no new `ignore_permissions`.**
Filter values reach SQL only as parameters, as `org_figures.condition()` already does. Column and table names are constants.
- **Test:** the `ignore_permissions` count does not rise (392 lines by my grep at 412d5361; I did not check how the CI counter counts, so compare like with like); a branch name containing a quote gets a normal refusal; the reviewer reads every new SQL statement.

**SEC-8 · A narrowed Branch permission still narrows the person (R6).** ⚠ Q4
For HR users, a Branch permission with **any** `applicable_for` limits them to those branches on this page. **Preferred:** land the R6/ALV-86 fix in `permitted_branches()` itself, so HR Analytics and People trends give one answer. That is a change to a shared helper and needs the engineer's caller list in the impact analysis. **Until it lands, HR roles do not get People trends** at any tenant where a narrowed Branch row exists.
- **Test:** the store HR with a Branch permission narrowed to Attendance sees only that branch; the central HR Manager sees the whole company.

**SEC-9 · One log line per call, in a sink that is proven to write. No figures, no names, no filter values.**
Write through `security_logger()` (or a logger raised the same way): endpoint, caller user, role class (HR or Leadership), period, duration, outcome (shown, not set up, refused). This is also the source for the brief's S1. Error messages and tracebacks carry no figure, name or filter value; the screen shows only "We could not load People trends" (01b).
- **Test:** call the endpoint, then **read the line back from the log file**, not from a patched logger (the ALV-391 lesson). Force an exception inside the endpoint and assert the Error Log and the response hold no figure, name or branch name.

**SEC-10 · No cache in v1 (OPS-15).**
If a later measure needs one: the key holds the site, the user, the resolved scope, the minimum, the period, the filter and today's date; the value holds only the answer after hiding.
- **Test (v1):** no cache write from the endpoint. (If a cache is added, two leaders with different scopes get different keys, and the stored value holds no hidden figure.)

---

## 8 · Privacy requirements (PRIV)

**PRIV-1 · Totals only, from an allowlist of fields.**
No name, employee ID, a person's date of joining, leaving or absence, leave reason, reason for leaving, pay, gender, age or manager in any response or log. The page's queries do not select `description` or `reason_for_leaving` at all. `leave_type` is selected only for PRIV-8.
- **Test:** every response's keys match an allowlist; a scan of every fixture response for every fixture employee's name and ID finds nothing (DevOps §2 item 2); a code check that the new SQL does not name the two reason fields.

**PRIV-2 · Population defined for each figure. The caller is not counted.**
| Figure | Population (distinct employees, inside the cut, for the figure's own days) |
|---|---|
| Headcount, Joined, Left, Net change, Attrition, leave days, pending requests | Employed on any day of the stretch: joined by its end and not relieved before its start |
| Early leavers "within X" | The finished cohort: joined in the window and past X days |
| Absence % | With a counted attendance row (Present, Work From Home, Half Day, Absent) in the stretch, as `org_figures.COUNTED` |
| One leave type | Took approved leave of that type with days inside the stretch |
When the caller's own Active Employee record is inside the cut, it is left out of every population. The minimum is read from `min_group_size()` on every call.
- **Test:** a department of 5 that includes the caller → hidden at minimum 5; a stored minimum of 1 behaves as 10.

**PRIV-3 · Hidden means not sent (OPS-11).**
A hidden figure is absent from the response: the key is missing, with only a "not shared" flag and the reason ("too few people" or "would reveal a smaller group", 01b UX-1). The same figure is hidden everywhere it appears: tile, headline sentence, chart, "Show as a table", By company block, change line. The headline sentence is built on the server from sent figures only.
- **Test:** for every hidden figure in the fixture, a recursive scan of the whole response finds no number equal to it in its place, and the sentence does not mention it.

**PRIV-4 · Time rule: decide once per cut, over all nine stretches (part B).**
For each cut and family, every stretch must pass (0 or at least the minimum). If not, the family is hidden on all five chips. Each chart series is sent whole or not at all. Each window total equals the sum of its own buckets, and buckets count back from the last day of data.
- **Test:** the branch that grew from 3 to 12 people → people figures hidden on every chip; a stable branch of 59 → shown on every chip; a series with one failing bucket → no series sent, window total sent.

**PRIV-5 · One filter at a time, inside one company (part A).** ⚠ Q1
- **Test:** two filters at once → refused (SEC-2); "All companies" carries no branch, department or type figures.
- **If Surbhi wants combined filters:** part C must run along every filter of the cut and of every parent cut, and the property test in PRIV-13 must cover grids. The engineer must prove that before it ships.

**PRIV-6 · Sibling rule, blank included, the same answer every time (part C).**
As 5.2 part C. Siblings include "none set". The same rule applies to companies under "All companies" and to branches inside a branch head's set. Ties are broken by name.
- **Test:** the fixed cases: kiosk (4) hides the next-smallest Retail branch too; employment type filled for 3 → both that type and the next-smallest hidden, and blank is counted as a sibling; Kavya Retail + Market Yard reads "Not shared: it would let someone work out a smaller group's figures" (01b).

**PRIV-7 · Shown figures must not rebuild a hidden one.**
When Left is hidden for a cut: Net change, the headcount change line, any start-of-window headcount, Attrition and the net line on the chart are hidden too. Headcount today and Joined may stay.
- **Test:** a cut with Left hidden: the response holds headcount and joined, and none of the five figures listed.

**PRIV-8 · Leave types only at the top, folded by the people who took them (part D).** ⚠ Q2
As 5.2 part D. The list of named types is the same on all five chips. "Casual the most" in the sentence names only a sent type, never "Other".
- **Test:** a type taken by 1 person is never named at company level or under any filter; with any filter applied, the response holds the leave total and no type names; Other always passes.

**PRIV-9 · The "count under 5" rule is removed, or carried by parts B and C.** ⚠ Q3
Default: removed (section 5.2). If Surbhi keeps it, it must run through PRIV-4 and PRIV-6 on the counts, so that no "Not shared" figure can be worked out from figures on the page.
- **Test (if kept):** for every count hidden by it, company total minus shown siblings is never that count.

**PRIV-10 · The data-quality line does not become a side door.**
Leaders see "N leavers have no relieving date" only at the top of their scope and only when N is at least the minimum. HR sees the count and a Desk link that is filtered to their companies and branches. In the Desk, HR's normal Desk permissions apply; the link grants nothing.
- **Test:** a leader with a filter applied gets no data-quality count; the HR link carries company and branch filters for a store HR.

**PRIV-11 · No export, no ranking, no named lists.**
No file or CSV method. Branch and company lists are sorted by name on the server. No sort parameter is accepted.
- **Test:** no new whitelisted method returns a file; a sort parameter has no effect.

**PRIV-12 · Purpose limitation.**
These figures are for operational oversight (`org_figures.PURPOSE = "operational-oversight-only"`, read). They are never an input to a rating, KPI, pay or disciplinary record, and never used to rank managers or branches.
- **Test:** an import check fails if `alvoraa_goals` or appraisal code imports the new module.

**PRIV-13 · The rule is proven by one property test, not by examples alone.**
On generated tenants (random branch, department and type sizes including blanks; random joining and leaving dates over two years; attendance; leave of several types), as each fixture user: collect every allowed response (5 chips × every allowed filter). Then work out every figure that can be **subtracted**: parent minus sent siblings along each dimension, and every difference between sent windows, comparisons and buckets of the same cut. **Assert each one's population passes.** This test must fail when part C's "together they pass" check is removed (lesson 5 of `verify-before-you-say-it.md`: break it, watch it fail, restore it).
- **Test:** this is the test. Plus "the number of queries is the same for 3 branches and 30" (OPS-14).

**Retention.** No new stored personal data except the remembered period (a user setting, life of the user). No cache. Log lines carry no figures. **There is no retention engine (feature map A6)**, so nothing is purged automatically; nothing new here needs purging.

---

## 9 · Questions and decisions

### For Surbhi (must know: these block the spec)

| # | ⚠ | My reading | Why it changes the control | Question | Default meanwhile |
|---|---|---|---|---|---|
| Q1 | ⚠ COMPLIANCE, Surbhi | The approved design allows several filters at once | Combined filters turn each request into a grid, and the rule must then cover every row, column and parent. One filter at a time makes the rule small and provable | **Is one filter at a time (below company) acceptable?** | One at a time |
| Q2 | ⚠ COMPLIANCE, Surbhi | The design shows "By leave type" under any filter | Under filters, fold-into-Other leaks across lists (company minus branches) | **Show leave types only with no filter applied, for one company?** | Only at the top |
| Q3 | Surbhi | The design hides counts under 5 in narrowed cuts | That "Not shared" can be worked out from the exact company total. It protects nobody the population rule does not | **Drop the count-under-5 rule?** | Dropped. If you keep it, PRIV-9 applies |
| Q4 | Surbhi (live check with the tenant admin), engineer (fix) | R6 is still open in code | A store HR with a narrowed Branch row would see the whole company | **Land the R6 fix in this slice, or hold HR roles off People trends until ALV-86?** And may someone read DTC's and Grace's Branch User Permission rows (`applicable_for`) on a dev copy? | HR roles off the page where a narrowed row exists |

### For counsel (should know: they do not block the build)

| # | Question | Blocks |
|---|---|---|
| CQ1 | Does DPDP s.7(i) ("for the purposes of employment…") cover the employer showing **aggregate** leaver, absence and leave figures to its leaders, with groups under 5 hidden? Carried from 012. I found only an oral "OK with our approaches" (memory, 25 Oct), no written answer | Whether any notice or consent step is needed |
| CQ2 | May a leave type that points at health or pregnancy (maternity, sick, medical) be **named** to leaders in an aggregate of at least 5 people, or must it always fold into "Other"? Counsel said on 1 Nov that health data is not for managers (memory, ALV-249); that was about individuals | PRIV-8. Meanwhile PRIV-8's rule stands; in practice it folds rare types |
| CQ3 | Must the employer's privacy notice say that leaders see totals? | The privacy-page line (brief: later) |

### Nice to know

- Q5 (engineer, analyst): Employee `branch` and `department` are **today's** values, while Attendance carries the branch the day was saved with (`alvoraa_branch`). A person who moved branch is counted under the new branch for leavers and under the old one for attendance. That is a numbers question for the spec, and part C must count distinct people, not add up cells.

---

## 10 · Detection and incident readiness

- **What we can see:** refusals (SEC-2) and one line per call (SEC-9), once that line is proven to write.
- **What we cannot see:** subtraction inside scope. Every request is allowed. This is why the rule is built to be safe, not watched.
- **Incident path:** a leak through this page is a personal-data breach in one tenant. DPDP and CERT-In clocks apply; **no breach workbench exists** (feature map A5). Counsel's 1 Nov advice on ALV-249 (memory) says a breach can exist without logged reads. Nothing in this slice changes that.

---

## 11 · Residual risk

**None of these is accepted yet.** I propose Surbhi as owner for each. An accepted risk needs a name and a date.

| # | Risk | Size | Kind | Owner | Accepted on |
|---|---|---|---|---|---|
| R1 | Range (not exact) inference across separately chosen filters | Low | Acceptable simplification | Surbhi (proposed) | — |
| R2 | Day-to-day visits show each day's change | Low (day buckets show it anyway) | Intentional trade-off (rolling windows were chosen) | Surbhi (proposed) | — |
| R3 | Short crossings between week and month buckets are not checked on their own | Low | Acceptable simplification | Surbhi (proposed) | — |
| R4 | What the leader already knows: team members by name (line manager), who is missing on the floor | Medium | Intentional trade-off; cannot be stopped by counting rules | Surbhi (proposed) | — |
| R5 | Two leaders pooling their views; the minimum changed between two views | Low | Acceptable simplification (012 R2) | Surbhi (proposed) | — |
| R6 | Store HR with a narrowed Branch permission treated as company-wide | **Medium, possibly live** | **Dangerous debt until checked: escalate now** | Surbhi (live check), engineer (fix) | — |
| R7 | No detection of misuse inside scope | Medium | Intentional trade-off | Surbhi (proposed) | — |
| R8 | Log history is about 2 MB and held in France (CERT-In) | Medium | Temporary debt, removed by a log store in India | Founder | — |
| R9 (carried) | System Manager reads everything in the Desk as CXO | Known, wide | Recorded in slice 010 | Surbhi | 2026-09-14 |

## 12 · Worries (not findings: I cannot yet write the full "this actor, this state, this path, sees this data")

1. **HR Company permissions narrowed to another record type.** `permitted_companies()` counts every Company permission, whatever it applies to (`access.py`, read), while `permitted_branches()` filters. An HR user with a Company permission narrowed to Leave Application could get that company's totals. I do not know if any such row exists.
2. **`leader_view` log lines are probably written nowhere** (short answer item 3). Inference; I did not open the file.
3. **Relieving-date quality is unknown** (brief Q6). If many leavers have none, the people figures are low, and part B's populations are computed from fewer people than really left. That makes hiding slightly less strict, not more. The measure must come before the spec.

## 13 · New Frappe app checklist

**Not engaged.** This slice installs no app (OPS-1: no Frappe Insights). It adds one portal page, one endpoint and one role.

---

## Subtract pass

Removed from my first draft: a separate rule set for HR (HR already sees names in the Desk, so one rule for both is simpler and was approved); a rate limit for "many filter requests" (part C gives the same answer every time, so repeating requests teaches nothing; nginx's 120 a minute stays); a "sensitive leave type" flag on Leave Type (a new field, and counsel has not asked for it; part D's people count does the job); a per-chip time rule (part B's "decide once" is simpler to build, test and read); requirements copied from 012 that this page does not need (doubtful-day job, settings history endpoint, remembered scope, employee "who can see" line). Kept: 10 SEC and 13 PRIV. Each answers a named abuse case.

## Sources (read 23 Nov 2026)

- [DPDP Act s.7, dpdpa.com](https://www.dpdpa.com/dpdpa2023/chapter-2/section7.html)
- [India's DPDP Act: phased rollout, AZB Partners](https://www.azbpartners.com/bank/indias-digital-personal-data-protection-act-phased-rollout-and-key-compliance-milestones/)
- [DPDP Rules 2025 notified, Mondaq](https://webiis08.mondaq.com/india/data-protection/1708164/digital-personal-data-protection-rules-2025-notified)
- [DPDP Rules 2025 key highlights, SCC Online](https://www.scconline.com/blog/post/2025/12/26/digital-personal-data-protection-rules-2025-key-highlights/)

---

## Decisions

**Surbhi, 23 Nov 2026 ("go with your recommendations"):**
- Q1 accepted: at most one of Branch, Department or Employment type, inside one company.
- Q2 accepted: leave types named only with no filter applied, and only if the people who took it pass in every window; otherwise folded into "Other".
- Q3 accepted: the "count under 5" rule for narrowed cuts is dropped; protection comes from the group rule (A–C).
- Residual risks listed above: proposed owner Surbhi; not yet formally accepted.
- Q4 (narrowed Branch permissions read as company-wide): logged on ALV-359; SEC-8 keeps HR roles off the page until fixed or the rows are checked.

---

## SQ-1 after the production measure (23 Nov 2026)

**Correction first.** Section 5.2 part B made early leavers pass in **all 9 stretches**. That was wrong for this figure, and it is why nothing shows at any live company. Early leavers are counted over **joining-date groups (cohorts)**, not over days employed. The page can only ever show 4 cohort stretches, so only those 4 can be worked out by subtraction. Checking the other 5 hid the row and protected nobody.

**Input.** Joiners in each stretch, counts only, run by Surbhi on production on 23 Nov 2026 and passed to me by the coordinator. I did not run it and have not seen the query.

### Which cohorts the page can show

The row has no comparison (01b §5). For the stretch "within X days", the window W shows the people who joined between X and W days ago (only they have finished X days). So:

| Within | Cohorts shown (by chip) | Stretches that subtraction can reach |
|---|---|---|
| 1 week | 7-30, 7-90, 7-180, 7-365 | 7-30, 30-90, 90-180, 180-365 |
| 1 month | 30-90, 30-180, 30-365 | 30-90, 90-180, 180-365 |
| 3 months | 90-180, 90-365 | 90-180, 180-365 |

The 1 week chip never has a finished cohort, so it always says "Too early to tell". Stretches 0-7, 7-14 (on its own), 360-365 and 365-730 can never be reached. Comparing "within 1 week" with "within 1 month" on the same chip only reaches the same four stretches. **The rule: early leavers pass when each of the 4 cohort stretches 7-30, 30-90, 90-180 and 180-365 has 0 joiners or at least the minimum.**

### What that gives on the measured data (minimum 5)

| Company | 7-30 | 30-90 | 90-180 | 180-365 | Early leavers |
|---|---|---|---|---|---|
| DTC (495) | 21 | 297 | 163 | 46 | **Shown**, every chip except 1 week |
| Grace Drinks (60) | 0 | 11 | 11 | 9 | **Shown**, every chip except 1 week |
| Grace Sales (34) | 1 | 4 | 1 | 3 | Not shared |
| Grace Enterprises (9) | 1 | 0 | 3 | 1 | Not shared |

Grace Sales and Grace Enterprises: one joiner in a stretch, plus a count of early leavers, points at that person. Hiding it is correct.

**Headcount, Joined and Left are not hit the same way.** Their group is everyone employed in a stretch, not the joiners. Every one of these companies has 9 or more active people. **Inference:** they pass at company level in all four. I did not see per-stretch headcounts. Joined is exempt anyway (PRIV-7).

### Options for early leavers

| Option | Shows at DTC / Grace Drinks | What still leaks | Build cost |
|---|---|---|---|
| **1 · The 4 cohort stretches above** | Yes / yes | A lower limit such as "at least 2 of the 21 joiners from 7-30 days ago left within a week". This is never about fewer than 5 people | Smallest: 4 counts per cut |
| **2 · Option 1, whole company only (no filter)** | Same | Same as 1. Branches and departments do not show early leavers, so the sibling rule (part C) is not needed for this row | **Smaller than 1** |
| 3 · Longer chips only (6 months, 1 year) | Yes / yes | Same as 1, and the 1-month and 3-month answers are lost. Does not help Grace Sales (180-365 is 3) | Same as 1, less useful |
| 4 · One fixed cohort (joined 30-365 days ago), one cell | Yes / yes | Least: no differences at all | Small, but loses the 1-week and 3-month cuts the founder asked for |
| 5 · Show counts with no small-group rule | Yes everywhere | "1 of 1 joiners left within a week" names a person. **Not safe** | — |

**Recommendation: Option 2.** Early leavers at company level only, with the 4-stretch check. It answers the founder's headline at DTC and Grace Drinks on the 1-month, 3-month, 6-month and 1-year chips. It drops the hardest part of the rule for this row. With a filter applied, the row reads "Early leavers are shown for the whole company only." A multi-company leader sees it per company, not for "All companies". ⚠ Surbhi: this narrows the approved design for this one row.

**Changes to the requirements:**
- **Part B and PRIV-4:** early leavers use the 4 cohort stretches above, not the 9.
- **PRIV-2:** the early-leaver group is the joiners in each cohort stretch.
- **New rule:** the early-leaver row is shown only when no filter is applied.
- **PRIV-13 test:** add DTC's and Grace Sales's measured counts as fixed cases. The first must show and the second must hide.

### Leave trends at DTC: flag only (DevOps and the analyst decide)

DTC has 3 Leave Applications in a year and runs payroll from Attendance. So a leave trend read from Leave Application (OPS-7) would be **near empty and wrong** at DTC, and right at Grace (198). Attendance "On Leave" rows are what DTC's payroll counts. They also match the window-edge rule (OPS-10), because there is one row per day. They are already counted in `org_figures.attendance_figures` (`on_leave`, read).

Privacy is the same either way. Leave days use the employed group. Leave types (part D) use the people who took the type. One unknown: **I do not know whether DTC's On Leave rows carry a leave type.** If they do not, "By leave type" is empty at DTC, and nothing leaks.

Owner: the DevOps engineer (OPS-7 is about the Leave Ledger index, not this) and the business analyst (brief Q5).

### Residual added

R10: lower-limit inference on early leavers across cohort stretches. Every stretch shown holds at least 5 joiners or none. Low. Acceptable simplification. Owner proposed: Surbhi. Not accepted yet.
