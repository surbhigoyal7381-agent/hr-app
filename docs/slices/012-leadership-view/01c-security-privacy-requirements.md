---
slice: 012-leadership-view
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-09-15
status: draft
inputs: [01-product-brief.md (incl. Gate decision 2026-09-15), 01a-ux-opportunities.md, 01b-ux-design.md (round 2, incl. Design check decision 2026-09-15), prototype-v2/index.html, 07-devops-inputs.md (§1, §2, §2a, Decisions), .claude/context/security-compliance-baseline.md, compliance-feature-map.md, product-context.md, docs/product/access-review/permission-templates.md, docs/product/access-review/2026-09-14-report-access-by-persona.md, docs/slices/010-portal-security-fixes/00c-review-copies-decisions.md (R13-R14), code at local dev 17828d2 (same as origin/dev c27fb56 for every file cited here) and origin/main, Frappe 16.22.0 source read from another local project]
---

# 012 · Leadership view — security and privacy requirements

**I recommend. You decide.** No code was changed. No bench, docker or server command was run.

## The short answer

**Bad news first. Three gaps are live on `dev` today, whether or not this slice ships.**

| # | Gap | Severity | Where it is | My recommendation |
|---|---|---|---|---|
| G1 | **HR Analytics is not limited to a branch or a company.** A store HR person gets every branch's totals, plus **names, departments and joining dates** of people in other branches, and the **gender** of the 10 newest joiners anywhere | **Major** | `hr_api.py:374-520` (dev and main) | Fix in **Step 0** of this slice. You already decided this (P4) |
| G2 | **`set_org_setting` writes any setting key, with no record.** One call can give every employee the organisation attendance view, which shows **names and leave types** | **Major** | `hr_api.py:2217-2222` (dev) | Fix in **Step 0**: a short list of allowed keys. Small |
| G3 | **`attendance_analytics.person()` opens any employee's days, in any branch or company**, for any role in the organisation attendance roles (HR User by default). Includes **leave type** and any date range | **Major** | `attendance_analytics.py:462-508` (dev only; the file is not on main) | Fix in **Step 0**, with the same scope check as G1 |

None of these crosses tenants. Each is inside one tenant. I found no sign of a live customer being affected (your note of 14 Sep 2026 says production has no live customers). I did not run any of them; they are code reads with a concrete scenario each (section 5).

**For the slice itself, the design is sound, with five holes in the small-group rules** (section 6):

1. **A change line leaks last month.** "Up 0.3 points on 1-13 Aug" gives away August's figure, even when August's group was too small to share.
2. **Headcount and joiners (always shown) rebuild leavers.** Headcount a year ago + joiners − headcount today = leavers.
3. **The department tab across branches (D15) leaks by subtraction (Q1b: yes).** It needs a two-way rule, or it should wait.
4. **A leader who is also a line manager can subtract the people they already see by name** in My team. Their own record also counts in their group.
5. **The trend check "group big enough today" is not enough.** Each month must be checked for its own people.

**OPS-32 (compression and the CSRF token): approve, with conditions.** BREACH is not a realistic risk here today. The main reason is the `SameSite=Lax` session cookie. There is one weak spot you should know about: every tenant on `*.alvoraa.co`, and dev, counts as the same "site" to a browser (section 10).

**This artifact sets 22 SEC and 16 PRIV requirements.** Each says how it is tested.

Baseline entries I rely on were verified on 24 Aug and 6 Sep 2026. That is under 90 days, so they are not stale. Two DPDP points I checked again today (section 4).

---

## 0 · What I read and checked

| Checked | How |
|---|---|
| Slice files, prototype v2, DevOps §1, §2, §2a and decisions | Read |
| `hr_api.py`, `attendance_analytics.py`, `branch_scope.py`, `hrms/.../alvoraa_hr_core/access.py`, `alvoraa_policy_library/access.py`, `alvoraa_org_structure/settings.py`, `field_checkin.py` settings block, `www/hrms_employee.py` | Read at local `dev` 17828d2. `git diff` shows these files match `origin/dev` c27fb56 for every line I cite |
| Whether G1-G3 are on `main` | `git show origin/main:...` |
| Frappe CSRF, cookie, User Permission and template code | Read in **Frappe 16.22.0**, from another project on this PC (`C:/Surbhi-Git/recruitment-AI-automation/frappe`). Our build pins `version-16` (`deploy/Dockerfile:25`). **Same major version, not proven to be the same build** |
| `ignore_permissions` count | 279 uses in our apps outside tests (`alvoraa_portal`, `alvoraa_goals`, `hrms/hrms/alvoraa_*`); 77 in `hr_api.py`. This slice must not add one (SEC-8) |
| DPDP Act s.7(i) and DPDP Rules 2025 Rule 6(1) | Web, 15 Sep 2026 (sources at the end) |

**Not checked:** anything that needs a running system. Those are listed as verification steps (section 14).

---

## 1 · Threat model in four lines

1. **Who wants this data, and what is the cheapest way in?** Insiders, not outsiders. A **branch head** who wants to know who in the 4-person kiosk is taking sick days. An **area manager** who opens "All my branches", then each branch, and subtracts. A **store HR person** who calls an HR endpoint by hand for another store. A **company head** who compares the department tab with each branch's departments. All of them have a valid login and can call any whitelisted endpoint (a server function the browser may call) with any parameter.
2. **Blast radius of one mistake.** One tenant. A scope bug shows one branch head **every branch** (hundreds of people). A small-group bug points at **one to four people**, but the data is about absence, which can point at illness, pregnancy or money trouble. A cache-key bug shows one leader **another leader's** answer. Nothing here crosses tenants: each tenant is its own site, and Frappe puts the site name in front of every cache key (07 §1 OPS-2).
3. **What is new?** New **visibility**: a role that could see nothing now sees totals. New **stored records**: doubtful days, HR confirmations, a settings history, a remembered scope. **No new personal data is collected.** No automated decision about a person.
4. **How would we find out?** **Mostly we would not.** Nobody would notice a leader subtracting two screens: every request is allowed. We can detect requests *outside* the leader's scope (SEC-14 logs them). We cannot detect misuse of what is inside it. That is why the suppression rules must be right by construction and proven by tests, not watched.

### Short STRIDE view

| Threat | Example in this slice | Main control |
|---|---|---|
| **S**poofing | A leader asks for a scope they do not hold | SEC-1, SEC-2 |
| **T**ampering | HR Manager changes the minimum through REST; a stale reason is re-used; a store HR person confirms another store's doubtful day | SEC-10, SEC-13 |
| **R**epudiation | "I never lowered the minimum" | SEC-10, SEC-11 |
| **I**nformation disclosure | Subtraction across views, periods, cache keys; hidden figures in the payload or in Redis | PRIV-2 to PRIV-10, SEC-9 |
| **D**enial of service | 7 calls per page hold web slots | DevOps OPS-15/16 (not repeated here) |
| **E**levation of privilege | Adding "Leadership" to the organisation attendance roles; a Branch permission that widens desk reads | SEC-5, SEC-18, SEC-19 |

---

## 2 · Data inventory

Classes follow the baseline: `public / internal / sensitive / statutory-id`. **No code applies these classes today** (feature map A1 is not built). The classes below are a declaration, not a control.

| Field or object | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| Source rows read: Attendance (`status`, `attendance_date`, `late_entry`, `early_exit`, `working_hours`, `alvoraa_branch`) | sensitive | Attendance records | Existing, unchanged | Employee (own), manager line, HR in scope |
| Attendance `leave_type`, Leave Application `leave_type`, `description` (reason) | sensitive | Leave records | Existing | Same. **Leader code must not select these fields at all** (PRIV-1) |
| Leave Allocation, Leave Application dates and status | sensitive | Leave records | Existing | Same |
| Employee `company`, `branch`, `department`, `status`, `date_of_joining`, `relieving_date` | internal | People records | Existing | HR; leader code reads to count only |
| Employee Checkin `time`, `alvoraa_branch` | sensitive | Attendance capture | Existing | HR; leader code counts people only |
| **Group counts before suppression** (people per group, per figure, per period) | sensitive | Computing the rule | **Memory only.** Never cached, logged or returned | Nobody |
| **Leader answer after suppression** (totals ≥ minimum, headcount, joiners) | internal — still personal data about small groups, never "anonymous" | Operational oversight | Cache only: 3, 15 or 60 minutes (OPS-17). Redis writes to disk, so also in its backups | The leader whose scope it is |
| Leader view settings: minimum group, reason, modified by, modified on | internal | Governance of the privacy rule | Life of the tenant [Q10] | System Manager (edit), HR Manager (read) |
| Settings history (`Version` rows for that doctype) | internal (holds System Manager names and free-text reasons) | Accountability | Life of the tenant, at least one year [Q10] | System Manager, HR Manager through one filtered endpoint |
| Doubtful-day record: date, company, branch, expected, absent, checked in, status | internal (counts only) | Data quality | 13 months after the date, plus one year [Q10] | HR in scope. Leaders see only the warning |
| HR confirmation ("absence was real", "figure is right"): item, scope, who, when, figure before and after | internal (holds HR staff names) | Data quality; defends a changed figure | Same as above | HR in scope; System Manager |
| "Needs review" item: rule, scope, count (for example "14 people marked left with no leaving date") | internal | Data quality | Until the rule stops firing; confirmations kept as above | HR in scope. Names only through the existing Employee list with HR's own permissions |
| Remembered scope (a user default holding one branch name) | internal | Convenience | Life of the user | The leader |
| "Who has leader access" list (leader names, their company or branches) | internal | Configuration check | Not stored; built live | System Manager, HR Manager |
| Employee "who can see" line | internal (about access, not about others) | Transparency toward the employee | Not stored; built live | The employee, about themselves |
| Refusal log lines (user id, endpoint, rule, time) | internal | Detection | At least one year (DPDP Rules Rule 6(1)(e), see section 4). CERT-In India-residency gap stays open (baseline §3a) | Operators |

---

## 3 · Access intent — who may see what, and who must NOT

"Scope" below means the company or branches the server resolves from the person's User Permissions (SEC-1). The business analyst builds the permission matrix from this table.

| Persona | May see | Must NOT see | Enforced by |
|---|---|---|---|
| **Company head** (Leadership + one Company permission) | Company overview: totals for the company, by branch, by department; drill into a branch; departments of a shared branch | Names, employee IDs, days, times, leave types or reasons, pay. Any figure for a group under the minimum, or hidden to protect one. Any figure of another company. The department tab (D15) unless PRIV-8 is built. HR's Data to review page | SEC-1-3, PRIV-1-8 |
| **Branch head** (Leadership + one Branch permission) | Their branch: totals, departments, Today strip, trend; "Company x%" when rule 5 allows | Every other branch's figures, in any form: table row, drill, Today, cache. The company table. Any hidden figure. The Organisation tab (LV11) | SEC-1-3, SEC-9, PRIV-5, PRIV-6 |
| **Multi-branch leader** (Leadership + two or more Branch permissions, one company) | "All my branches" combined, a table of **their** branches, each branch alone; "Company x%" under rule 5b | Branches outside their set. A branch hidden in their own table, when chosen alone (inheritance). Anything from another company (D19) | SEC-1, SEC-2, SEC-9 (set in the key), PRIV-5 |
| **Leadership, no Company or Branch permission** | "Your leader view is not set up yet" | **Any figure at all**, including headcount | SEC-1 (fail closed) |
| **Leadership, two companies** (D19) | The company on their own active Employee record, if that company is in their permissions | Combined totals across companies. Anything if they have no active Employee record or its company is not in their permissions | SEC-20 |
| **HR User / location HR** (HR User + Branch permission) | HR Analytics for their branch only (after G1). Data to review items **for their branch only**; confirm those items | HR Analytics for other branches or companies. Other branches' Data to review items or confirmations. Another employee's days outside their branch through `person()` (after G3). The leader view, unless they also hold Leadership. The settings page | SEC-13, SEC-16, SEC-17 |
| **HR Manager** (central or company-scoped) | HR Analytics for their permitted companies (and branches, if limited). All Data to review items in that scope. Settings value and change history, read-only. "Who has leader access" | Settings **save** (any path: portal, desk, REST). `Version` records of other doctypes. The leader view, unless they also hold Leadership | SEC-10, SEC-11 |
| **System Manager** | Settings: change the minimum with a reason; the history; the leader access list | The leader view **unless they also hold Leadership** (no implicit grant). Note: System Manager already reads everything in the desk as CXO (slice 010 decision). That is outside this slice and is recorded as a known wide grant, not widened here | SEC-4, SEC-10 |
| **Employee** | Their own "who can see your attendance and leave" line | Any aggregate. Names of other employees. Which specific users hold Leadership (the line uses role words only) | PRIV-12 |
| **Line manager** (no Leadership) | My team, unchanged | Any leader endpoint, company comparison, branch table, ranking of managers | SEC-1, PRIV-11 |
| **Guest** | Nothing | Everything. All new endpoints refuse Guest | SEC-7 |

**Data to review, in one line:** HR sees items for the scope their User Permissions allow, through Frappe's own permission check on the stored records; leaders see only the "Needs review" label and the short reason; employees see nothing.

---

## 4 · Obligations engaged

**I am not a lawyer.** These are engineering requirements drawn from published sources. The compliance owner is not named yet (`product-context.md` §5), so every ⚠ item waits for that person or counsel.

| Obligation | Source | Last verified | What it means here |
|---|---|---|---|
| DPDP — purpose limitation, data minimisation | Baseline §2 | 24 Aug 2026 | Totals only; leave type never selected; aggregates not reused to rate managers (PRIV-1, PRIV-13) |
| DPDP — notice (itemised; languages of the Eighth Schedule) | Baseline §2 | 24 Aug 2026 | The employee line must be accurate. English-only at launch is a gap for Hindi-first staff (PRIV-12, PRIV-15) ⚠ |
| DPDP s.7(i) — processing "for the purposes of employment" as a legitimate use | Act text, as quoted by dpdpa.com and Lexology | **15 Sep 2026** | Likely basis for leader totals, so no consent screen is designed. ⚠ **Counsel to confirm (CQ1)** |
| DPDP Rules 2025, Rule 6(1)(c) visibility of access through logs; 6(1)(e) keep logs one year | Rules text, as quoted by dpdpa.com | **15 Sep 2026** | Refusal logs and settings history kept at least one year (SEC-14, PRIV-14) ⚠ counsel on whether settings history counts as such a log |
| DPDP phased dates (Data Fiduciary duties fully effective around May 2027) | Baseline §2 | 24 Aug 2026 | Build now; no date pressure changes the design |
| CERT-In — 180-day logs in India | Baseline §3, §3a | 6 Sep 2026 | Open gap (France hosting). Not caused or fixed by this slice |
| GDPR Art 5 principles, Art 88 employment data | Baseline §4 | 24 Aug 2026 | **Only if the founder confirms EU exposure** (still open). The same design covers minimisation. Small-group aggregates remain personal data |
| OWASP ASVS 5.0 Level 2 — access control, logging | Baseline §5 | 24 Aug 2026 | Server-side scope, deny by default, refusal logging |
| ISO 27001 — access control, access rights review | Baseline §5 | 24 Aug 2026 | "Who has leader access" list is a start of recertification evidence |

---

## 5 · Gaps live today

Each has a concrete scenario. Line numbers are at local `dev` 17828d2.

### G1 · `get_hr_analytics` is unscoped — Major

**Scenario.** A store HR person (HR User, Branch permission on "Lakeside Mall"), logged in to the portal, calls `alvoraa_portal.hr_api.get_hr_analytics`. They receive, for **every branch and every company** in the tenant:

- headcount, department, designation, branch and **gender** distributions (`:390-416`, `:476-480`) — raw SQL with no company or branch condition;
- attendance and leave totals (`:430-449`, `:466-473`);
- **names, designation, department, joining date** of everyone due confirmation this month (`:455-463`, `get_all` with `ignore_permissions=True`);
- **names, designation, department, joining date and gender** of the 10 newest joiners anywhere (`:483-490`, same).

An HR User of company A on a two-company site gets company B the same way.

**Also wrong, not only open:** leave use divides this year's leave by every allocation ever made (`:442-449`, LV2).

**On `main` too** (`origin/main hr_api.py:375`). On main there is no branch model for store HR yet, so the exposure there is "all HR users see all companies".

**Why Major, not Blocker:** inside one tenant; names, gender and joining dates, not health or pay.

**Fix:** Step 0 (P4, already decided). Requirement SEC-16.

### G2 · `set_org_setting` writes any key — Major

**Scenario.** An HR Manager (or anyone holding that login) calls `alvoraa_portal.hr_api.set_org_setting` with `key = "alvoraa_attendance_org_roles"` and `value = "HR Manager,HR User,System Manager,Employee"`. From the next request, **every employee** passes `_may_see_organisation()` (`attendance_analytics.py:55-61`). Every employee can then open `summary(view="organisation")` with each person's name and `leave_by_type` (`:320`, `:353`), and `person()` for anyone, with leave type (`:503`). **No record says who made the change** (`hr_api.py:2217-2222` calls `frappe.db.set_default` and commits).

Other keys the same call reaches today:

| Key | What changing it does |
|---|---|
| `alvoraa_attendance_org_roles` | Grants named attendance and leave types to any role, **including "Leadership"** — the shortcut the brief refused (LV5) |
| `alvoraa_checkin_photo_retention_days` (`field_checkin.py:533`) | Keeps check-in face photos for as long as someone types |
| `alvoraa_attendance_short_tolerance_mins` | Changes every short-day figure, silently |
| `alvoraa_org_full_reach_roles` | Widens the org chart (also writable by HR Manager through `set_cover_setting`, `settings.py:139-148`, which at least checks the key name) |
| Frappe and ERPNext defaults read by core code, for example `currency`, `country`, `float_precision` (`hrms/hr/utils.py:42`, `:142`) | Can break payroll and report maths |

`get_org_setting` (`:2211-2214`) reads any key the same way.

**On `main`**, the guard calls `frappe.has_role`. The comment on dev (`:2226-2228`) says that function does not exist and threw an error for everyone. So on main it is probably closed by accident. `[inferred from the code comment; not run]`

**The portal UI writes only one key** through this function today: `kra_link_mandatory` (`hrms-employee.html:16002`). An allowlist breaks nothing on screen.

**Why Major:** it changes who can see named leave data, with no record. It also makes P2 ("only System Manager changes sensitive settings") untrue for the most sensitive setting that already exists.

**Fix:** Step 0, small: allowlist the keys; access-granting keys become System Manager only with a change record. The wider move of org settings to a tracked doctype stays separate. Requirements SEC-18, SEC-19.

### G3 · `attendance_analytics.person()` has no branch or company limit — Major

**Scenario.** A store HR person with an Employee record (HR User, Branch permission "Lakeside Mall") calls `alvoraa_portal.attendance_analytics.person` with the employee ID of a cashier in another store, or another company, and `date_from = "2020-01-01"`. They receive every day's status, hours, late and early flags and **leave type** for that person (`:462-508`). The check at `:473-475` lets anyone in the organisation roles through, with no population check. `_gather` reads with `get_all` (`:199-207`). Dates are not bounded.

Employee IDs usually follow a naming series, so guessing them is easy `[ASSUMPTION — default naming series]`.

`summary(view="organisation")` does apply the Branch permission (`:157`, `get_list`), so the list view is scoped and `person()` is not. That is the gap.

**Also, smaller (Minor):** `filter_options()` (`:427-459`) uses `get_all`. A store HR person gets every department, branch and designation name, and **the names of every manager** in the company (all companies, if they have no Employee record).

**Only on `dev`.** The file is not on `main`.

**Why Major:** leave type can point at health or pregnancy; one call per person; no trace.

**Fix:** Step 0 — reuse the organisation population check from `summary()`. It is the same scope helper Step 0 builds for G1. Requirement SEC-17.

---

## 6 · The small-group rules — confirmed, and where they need tightening

This answers 01b §7, D3, Q1b and Q2.

| 01b rule | My ruling |
|---|---|
| Rule 1 — count distinct people inside each figure for its period | **Confirmed.** Defined exactly in PRIV-2 |
| Rule 2 / D3 — keep hiding until ≥ 2 hidden and the hidden groups together reach the minimum | **Confirm option (a).** Option (b) can leave two tiny groups summing under the minimum |
| Rule 3 — sensitive list; headcount and joiners exempt | **Confirmed, with one addition:** "headcount a year ago" and any headcount change line become sensitive whenever leavers are hidden for that group (PRIV-7) |
| Rule 4 — inheritance on drill-down | **Confirmed, and widened** to every figure family: Today, trend, last 7 days, the "with doubtful days" figure (PRIV-5) |
| Rule 5 / 5b — company comparison | **Confirmed** (PRIV-6) |
| Rule 5a / 5c — rules run per leader's own set | **Confirmed.** The cache key must then include the leader's set, not just the branch on screen (SEC-9) |
| Rule 6 — Today not shown below the minimum | **Confirmed.** Population = people expected today |
| Rule 7 — hidden figure absent from the response | **Confirmed**, and absent from the cache too (SEC-9) |
| Rule 8 — trend shown when the group passes today | **Not enough.** Each month's point is checked for the people inside that month (PRIV-6) |
| Rule 8 — collusion between leaders | **Accept as residual risk** with a named owner (section 13). No design can stop two people pooling |
| Q1b — department tab across branches (D15) | **Yes, it leaks** without a two-way rule. See AB-4 and PRIV-8 |

**One simplification I recommend (Q3):** decide "shared or not shared" **once per group per period**, using the smallest group count among its sensitive figures. Deciding per figure is legal but gives a table where each column hides different rows. That is harder to test and harder to read.

---

## 7 · Abuse cases

Each names the actor, what they do, what they would learn, and the requirement that stops it.

| ID | Actor and action | What leaks without a control | Stopped by |
|---|---|---|---|
| **AB-1** | **Company head subtracts across views.** Company table hides Hilltop Kiosk (4) and Station Road (42). Opens Station Road's own page | Station Road's figure, then company total − shown branches − Station Road = kiosk | PRIV-4, PRIV-5 (inheritance) |
| **AB-2** | **Area manager Dev (kiosk + Station Road) subtracts.** Opens "All my branches" (46 shown), then Station Road alone, then its Today strip | Kiosk = combined − Station Road, on any figure family that forgot inheritance (Today strip is the usual one) | PRIV-5 across all figure families |
| **AB-3** | **Area manager Neha uses the company comparison.** Sees her set, each branch and "Company 96.8%" | "Rest of company" by subtraction — safe only if the rest ≥ minimum for both the set and the branch on screen | PRIV-6 (rule 5b) |
| **AB-4** | **Company head uses the D15 department tab.** "Security, all branches" late arrivals = 23. Lakeside's page hides Security (4); the other five branches show Security | 23 − the five shown = Lakeside Security's late arrivals. Counts add up, so this is exact | PRIV-8, or cut D15 (Q2) |
| **AB-5** | **Branch head reads the change line.** September (group 6) shows "Up 0.3 points on 1-13 Aug". August's group was 4 | August = September − 0.3 | PRIV-6 (each side checked; delta only when both pass) |
| **AB-6** | **Branch head reads the trend.** Branch has 6 people today; June attendance came from 4 (slice 011 keeps the branch a record was saved with) | June's figure for 4 people | PRIV-2, PRIV-6 |
| **AB-7** | **Anyone reads exempt figures.** Kiosk: "4 people · Down from 5 a year ago · 1 joined in 12 months" while leavers are hidden | Leavers = 5 + 1 − 4 = 2 | PRIV-7 |
| **AB-8** | **Branch head who manages most of the branch.** Store in-charge sees 60 of 64 people by name in My team (attendance rates per person). The other 4 report to head office | Branch total − 60 known people = the 4 | PRIV-9 (complement rule) or residual risk (Q1) |
| **AB-9** | **Leader inside a group of 5.** A department of 5 includes the leader | The other 4's combined figure, since the leader knows their own | PRIV-9 (self excluded from the count) or residual (Q1) |
| **AB-10** | **Today strip against cards.** Home cached 3 min says "3 on leave"; card cached 15 min says "2" | One person's leave landed between the two times. Presence only, no reason | Same computation and "as of" time for both (PRIV-5 note); residual R3 |
| **AB-11** | **Changing the minimum.** At 5: kiosk (4) and Station Road hidden, Riverside (5) shown. System Manager raises to 6: kiosk and Riverside hidden (together 9 ≥ 6), Station Road shown. A leader who saw both views of a **closed** month (trend) | Kiosk = company − shown branches, using Riverside from the first view and Station Road from the second | Rare, recorded, reasoned changes (SEC-10); residual R2. Lowering gets a confirm; the history is visible to HR Manager |
| **AB-12** | **Crafted branch set.** Someone who can create User Permissions links a leader to {kiosk, Station Road}, later to {Station Road} | Kiosk on closed months, as in AB-11 | Only System Manager creates User Permissions (Frappe 16.22 `user_permission.json`; verify on our build, V7). Leader access list shows the current set; residual R2 |
| **AB-13** | **Whitelisted API parameters.** Branch head posts `branch = "Station Road"`, `company = "Other Co"`, `min_group = 1`, `inherited = 0`, `date_from = date_to = "2026-09-14"`, `raw = 1` | Another scope; figures below the minimum; single-day slices that make differencing easy | SEC-2, SEC-3 (no such inputs; scope checked and refused; period is a fixed choice) |
| **AB-14** | **Cache keys.** Dev (set includes kiosk) opens Station Road → hidden. Station Road's own branch head opens Station Road → shown (rule 5c). Both keys are "branch:Station Road" | One leader gets the other's answer: either a leak or a wrong "not shared" | SEC-9 (set in the key); test with both leaders |
| **AB-15** | **Stale cache after raising the minimum** | Groups of 5-6 shown for up to 15 minutes | SEC-9 (minimum value in the key; delete on save) |
| **AB-16** | **Employee "who can see" line.** Line says "you, your manager and HR see your leave type". At the reference tenant, store managers with a Branch permission read the whole store's Attendance with leave type in the desk (access review §1) | A notice that says less than the truth | PRIV-12 |
| **AB-17** | **Endpoint behind the line.** An employee calls the "who can see" endpoint with another employee's ID | Another person's branch and leader set | PRIV-12 (no employee parameter) |
| **AB-18** | **Store HR on Data to review.** Confirms "the absence was real" on another store's doubtful day by record name | Changes another store's attendance figure | SEC-13 |
| **AB-19** | **HR Manager changes the minimum** through `/api/resource/<settings doctype>` or `frappe.client.set_value`, not the page | A change without System Manager, or without a reason | SEC-10 (rule in the doctype controller, all paths) |
| **AB-20** | **HR Manager reads all history** through `/api/resource/Version` | Every document's change history, including salary edits | SEC-11 |
| **AB-21** | **Org roles shortcut.** Someone adds "Leadership" to `alvoraa_attendance_org_roles` "until the view ships" | Named people and leave types for every leader | SEC-18, SEC-19 |
| **AB-22** | **Departing leader.** Store head resigns; their Employee record is Left; User still enabled; role and permission not yet removed | Branch totals after leaving | SEC-6 |
| **AB-23** | **Branch permission widens the desk.** A store head with the Employee role and only a Branch permission (the reference tenant's seed) | Every Employee record in the store (date of birth, gender) through the desk. Pre-exists; Leadership setup must not add more | SEC-5 |
| **AB-24** | **Two companies share a branch name.** ERPNext's Branch is, as far as I recall, not tied to a company `[recall — verify V6]` | A branch head counts the other company's people in "their" branch | SEC-2 (company and branch together) |
| **AB-25** | **Remembered scope tampered.** Leader sets their user default to a branch they do not hold | Home card for that branch | SEC-21 |
| **AB-26** | **Guest or plain employee** calls a leader endpoint | Any figure, or a slow query run for nothing | SEC-7 |

---

## 8 · Security requirements (SEC)

Every requirement says what must be true, and how the test engineer proves it. "Fixture tenant" means a test site with: one company "Kavya Retail" with branches Lakeside Mall (64), Station Road (42), Hilltop Kiosk (4), Old Market (71), Riverside (49), Meadow (4 departments incl. Security 4); a second company "Other Co" with a branch of the **same name** as one of Kavya's; users Meera (company head), Arjun (Lakeside), Neha (Old Market + Riverside), Dev (kiosk + Station Road), Farah (kiosk), Rohan (Leadership, no permission), a store HR user, a central HR Manager, a System Manager, a plain employee, and a line manager with 60 of Lakeside's people below them.

**SEC-1 · One scope resolver, server side, fail closed.**
One function turns the session user into (company, set of branches, scope type). Nothing else decides scope. Rules:
- No Leadership role → refuse (PermissionError).
- Leadership, no usable Company or Branch permission → a "not set up" answer with **no figures, not even headcount**.
- A User Permission counts only when it applies to Employee (applies to all doctypes, or applicable for Employee). A permission limited to another doctype grants nothing.
- Company plus Branch permissions → the branches win (D7).
- Branches set, company resolved from: exactly one Company permission; else the caller's own **active** Employee record; else "not set up". Branches whose people are in another company are not counted.
- Branches equal to every branch of the company → company scope.
- More than one company → SEC-20.
- **Test:** a table-driven test over every fixture user asserts the resolved scope, including Rohan (nothing), a user with a Branch permission applicable only to Salary Slip (nothing), and a user with Company + Branch (branches).

**SEC-2 · Every leader query is filtered by company and branch set from SEC-1, and nothing else widens it.**
A request that names a branch or company outside the resolved scope is **refused, not trimmed**, and logged (SEC-14). This matches `attendance_analytics._population`.
- **Test:** Arjun posts Station Road → 403 and one log line; Arjun posts "Other Co" → 403; Arjun's response contains no row, key or total for any other branch; the same-named branch in Other Co contributes nothing to Arjun's figures.

**SEC-3 · The client chooses only from fixed options.**
Accepted inputs: the scope choice (one of "all my branches" or a branch in the caller's set; for the company head, a branch or department of their company), a period from a fixed list (this month so far; the 6-month trend), and the "show with doubtful days" switch. **Not accepted as input:** minimum group, inherited-hidden flag, free dates, employee IDs, department of another scope. Unknown values are refused.
- **Test:** post each forbidden parameter with a tempting value; assert the response is unchanged or refused, never wider.

**SEC-4 · "Leadership" is a new role with no document permissions.**
Named "Leadership", **not** "Alvoraa CXO" (`alvoraa_policy_library/access.py:50` treats that name as "sees all" on policies). The role has no DocPerm or Custom DocPerm rows. It is a label the leader endpoints check, nothing more. System Manager does not get the leader view unless it also holds Leadership.
- **Test:** assert zero DocPerm/Custom DocPerm rows for the role; for a Leadership-only user, `frappe.has_permission` is False on Employee, Attendance, Leave Application, Salary Slip, Employee Checkin; a System Manager without Leadership is refused by the leader endpoints.

**SEC-5 · Setting up a leader must not widen what they can read in the desk.**
The P1 side-effect check becomes a test, not a one-off look.
- **Test:** for Arjun and Meera, count `frappe.get_list` rows on Employee, Attendance, Leave Application, Salary Slip, Expense Claim **before** and **after** adding Leadership and the permission. After ≤ before for every doctype. Record the numbers in the test output.

**SEC-6 · Access ends on the next request.**
The authorisation decision is never cached. Removing the role, removing a permission, disabling the user, or the caller's own Employee becoming Left or Inactive (when they have one) takes effect on the next call.
- **Test:** load as Arjun (200); remove each in turn; the next call is refused or narrowed, with a warm cache.

**SEC-7 · Endpoint hygiene.**
Every new endpoint: `@frappe.whitelist(methods=["POST"])`; `@requires_feature("analytics")` (until P6 is decided); refuses Guest; the Home endpoint returns an empty answer and runs **no figure query** for a user without Leadership; responses carry `Cache-Control: no-store` (DevOps check C).
- **Test:** GET is refused; Guest is refused; a plain employee's Home call runs a fixed small number of queries (query-count assertion) and returns no figures; response header asserted.

**SEC-8 · No new `ignore_permissions`; SQL is parameterised.**
Leader counts use SQL `GROUP BY` (OPS-6). Scope values come only from SEC-1 and are passed as parameters, never formatted into the SQL string.
- **Test:** the `ignore_permissions` counter (feature map I3) does not rise; the reviewer checks every new SQL statement for `%s` parameters; one test passes a branch name containing a quote and asserts a normal refusal.

**SEC-9 · The cache holds only final answers, under keys that cannot be shared by mistake.**
- Value: the payload **after** suppression. No pre-suppression counts, no employee IDs, names, leave types or pay.
- Key (after Frappe's site prefix): scope type, company, a hash of the caller's **sorted branch set**, the scope on screen, the minimum group value, formula version, period, data-up-to date, doubtful-day version, the doubtful-days switch.
- Every key expires (OPS-10). Authorisation runs before the cache read (SEC-6). Saving the settings deletes every leader key (OPS-17).
- **Test:** (1) Dev and Station Road's branch head open Station Road: different answers, different keys. (2) Raise the minimum 5 → 7, load immediately: no group of 5 or 6 shows figures; lower 5 → 3: small groups now show (OPS-25). (3) After a load that hides the kiosk, read the Redis value for that key and assert the kiosk's sensitive figures are absent.

**SEC-10 · The minimum group setting: System Manager only, reason required, every path.**
A Single doctype with change tracking (OPS-23). The rules live in the **doctype controller**, so the portal, the desk, REST and data import all obey them:
- Only System Manager may write (DocPerm). HR Manager read-only. Others nothing.
- Value is a whole number from 3 to 10.
- A reason is required **in the same save** that changes the value. The reason field is cleared after each save, so an old reason can never be re-recorded for a new change.
- Saving without changing the value is refused.
- If the stored value is missing or outside 3-10 (for example set from a console), the leader code uses **10**, the strictest allowed value, and writes an error log line.
- **Test:** HR Manager save refused through the portal endpoint, `PUT /api/resource/...`, and `frappe.client.set_value`; System Manager save without a reason refused; with reason, a `Version` row exists with before, after and reason; value 2 and 11 refused; a DB value of 1 makes the leader code behave as 10.

**SEC-11 · HR Manager reads the history through one filtered endpoint only.**
The endpoint hard-codes the settings doctype; it takes no doctype or document parameter. HR Manager gets **no** read permission on `Version`.
- **Test:** HR Manager `GET /api/resource/Version` → refused; the endpoint returns only rows for the settings doctype; System Manager and HR Manager get 200, others 403.

**SEC-12 · The leader settings never use Frappe Defaults or `set_org_setting`.**
- **Test:** the minimum is absent from `tabDefaultValue`; `set_org_setting` with any leader setting key is refused (depends on SEC-18).

**SEC-13 · Data to review records follow Frappe permissions; confirmations are scoped and kept.**
Doubtful-day and review-item records carry `company` and `alvoraa_branch`, so User Permissions apply by themselves (as `branch_scope.py` does). Listing and confirming go through `frappe.get_list` and `frappe.has_permission`, with no `ignore_permissions`. A confirmation records who, when, the item, the scope and the figure before and after. Confirmations cannot be edited; a mistake is undone by a new confirmation. A company-wide item (for example the D6 leave rule at company level) can be confirmed only by someone whose scope covers the whole company.
- **Test:** store HR lists only Lakeside items; confirming a Station Road item by name → 403; store HR cannot confirm a company-wide item; each confirmation leaves a record with the before and after figure.

**SEC-14 · Refusals are logged the existing way.**
Use `hrms.alvoraa_hr_core.access.log_refusal` (slice 010 SEC-17): user, endpoint, rule id, time. **Never** a figure, a name or the requested scope's figures. The requested branch name is not logged either (it is scope data, OPS-11).
- **Test:** a refused out-of-scope call writes one JSON line to the `security` logger with the rule id and no other values.

**SEC-15 · No figures, names or scope in URLs, logs, error messages or tracebacks.**
- **Test:** force an exception inside a leader endpoint (patch a query to raise); assert the Error Log entry and the response contain no figure, no employee name and no branch name; the UI message is generic ("figures did not load").

**SEC-16 · Step 0: scope HR Analytics (G1).**
HR scope = companies from `permitted_companies()`, narrowed by the caller's Branch permissions when they have any. Central HR with no Branch permission sees all branches of their permitted companies. Every count gets company and branch conditions. `confirmations_due` and `recent_employees` use `get_list` without `ignore_permissions`. Leave use uses this leave year's allocations only (LV2).
- **Test:** store HR sees only Lakeside counts and names; HR User of Kavya sees nothing of Other Co; central HR Manager sees all of Kavya; a numbers test compares HR Analytics and the leader view for the same scope and period (brief S2: zero difference).

**SEC-17 · Step 0: scope `person()` and `filter_options()` (G3).**
`person()` opens an employee only if they are the caller, in the caller's reporting line, or inside the caller's **organisation population** as `summary(view="organisation")` builds it (company + `get_list`). The date range is limited (for example 12 months). `filter_options()` uses `get_list`.
- **Test:** store HR opening a Station Road employee → 403 and a log line; opening a Lakeside employee → 200; a 5-year range → refused or cut to the limit; `filter_options` for store HR lists only Lakeside's departments and managers.

**SEC-18 · Step 0: `set_org_setting` and `get_org_setting` accept listed keys only (G2).**
An explicit allowlist in code. Today that is `kra_link_mandatory` (the only key the UI writes) and, if the Org Settings screen is meant to edit it, `alvoraa_checkin_photo_retention_days` with a range check. Keys that **grant visibility** (`alvoraa_attendance_org_roles`, `alvoraa_org_full_reach_roles`, `alvoraa_org_managers_see_all`) are refused here; if they stay editable anywhere, that path is System Manager only and leaves a change record. Unknown keys are refused and logged.
- **Test:** HR Manager writing `alvoraa_attendance_org_roles`, `currency` and an unknown key → refused; `kra_link_mandatory` → allowed; `get_org_setting("currency")` → refused.

**SEC-19 · The org roles shortcut is blocked by structure, not by a note.**
`_org_roles()` ignores "Leadership" (and "Employee", "Employee Self Service") even if the stored setting lists them, and logs that it did. The brief proposed "no code guard" for LV5. **I disagree:** a prohibition written only in a template is not a control (Q6).
- **Test:** store `"HR User,Leadership"` in the setting; a Leadership-only user is refused `summary(view="organisation")` and `person()`.

**SEC-20 · A leader of more than one company (D19).**
Company = the company on the caller's own active Employee record, and only if it is one of their Company permissions. No Employee record, or its company is not in the set → "not set up". Never combined totals.
- **Test:** a leader with permissions on Kavya and Other Co and an Employee in Kavya sees Kavya only, with the D19 line; the same leader with no Employee record sees nothing.

**SEC-21 · The remembered scope is a preference, never an authority.**
Stored under a namespaced user-default key (for example `alvoraa_leader_scope`), **not** `branch` or `Branch`, because Frappe uses plain field-name user defaults to pre-fill desk forms. Re-checked against SEC-1 on every read; falls back to "All my branches" when no longer valid.
- **Test:** set the default to Station Road for Neha → Home shows All my branches, and no Station Road figure is in the response.

**SEC-22 · Scope of the doubtful-day job.**
The scheduled job writes counts only (no employee IDs) and runs only for groups with at least the minimum expected people (OPS-22). It runs as a system job and writes records carrying company and branch (SEC-13).
- **Test:** after the job on the fixture tenant, no record exists for the kiosk; records hold no employee field.

---

## 9 · Privacy requirements (PRIV)

**PRIV-1 · Totals only, and only allowed fields ever leave the server.**
No name, employee ID, date of a person's absence, time, leave type, leave reason, pay, date of birth, gender, age or manager filter in any leader response, cache value or log. The leader queries **do not select** `leave_type` or `description` at all.
- **Test:** a response-schema test: every leader response's keys match an allowlist; a recursive scan of each response and cache value for fixture employee names and IDs finds nothing; a code check that leader SQL does not name `leave_type` or `description`.

**PRIV-2 · Group size is the people inside the figure for its period.**
For each figure: the number of distinct employees in the population the figure is computed over (numerator and denominator together) for that group and period, using the branch the records were saved with (`alvoraa_branch`). For Today: people expected today. For leave used: people with a leave allocation in the leave year. For leavers and attrition: the headcount basis used in the formula. Never today's headcount for a past period.
- **Test:** a branch with 6 people today and September attendance from 4 → September hidden at minimum 5.

**PRIV-3 · Primary rule, server side, minimum read fresh.**
A sensitive figure (01b §7 rule 3 list, plus PRIV-7) for a group under the minimum is **absent** from the response: the key is missing, not zero, not null with a hint. Only headcount and joiners are exempt.
- **Test:** kiosk response has no sensitive keys; headcount and joiners present.

**PRIV-4 · Subtraction rule D3 (a), decided per group.**
In any set of sibling groups whose parent total the caller can see (branches in a company; branches in a leader's set; departments in a branch), if any group is hidden, keep hiding the next-smallest until at least two are hidden **and** the hidden groups together reach the minimum. With two siblings and one hidden, both are hidden. A parent with one child: the child is hidden exactly when the parent is. Decision is per group per period, using the smallest group count among its sensitive figures (Q3).
- **Test:** property test on generated sets (sizes 1-60, 1-12 siblings): in every result, the number of hidden siblings is 0 or ≥ 2, and hidden sizes sum to ≥ the minimum. Plus the fixed cases in 01b (Lakeside departments; two-branch company).

**PRIV-5 · Inheritance, per caller, across every figure family.**
A group hidden in any table this caller can see stays hidden on every other view this caller can open, and so do its children. "Figure family" includes the cards, the Today strip, the trend, the last-7-days card, the by-department table and the "with doubtful days" figure. The Home card and the overview use the same computation, so the same scope and time give the same number.
- **Test:** Meera → Station Road: headcount and joiners only, all departments hidden, no Today, no trend. Dev → Station Road alone: same. Arjun: Home "on leave today" equals the card for the same "as of" time.

**PRIV-6 · Comparisons and time are figures too.**
Every comparison value — same days last month, a year ago, each trend point, the company figure — passes PRIV-2 to PRIV-5 **for its own group and period**. A change line ("Up 0.3 points") appears only when both sides are shown. "Company x%" follows 01b rule 5 (single branch) and rule 5b (several branches).
- **Test:** September group 6, August group 4 → September shown, no change line, August trend point absent. Two-branch company with a 4-person branch → no company comparison for the big branch's head.

**PRIV-7 · Exempt figures must not rebuild a hidden one.**
When leavers are hidden for a group: attrition, "headcount a year ago" and any headcount change line are hidden too. Headcount today and joiners stay.
- **Test:** kiosk with leavers hidden → response has headcount and joiners, and no year-ago headcount, change or attrition.

**PRIV-8 · Department tab across branches (D15) only with a two-way rule.**
The company head's branch × department grid, its department totals, branch totals and company total are one table. Apply PRIV-4 along every row and every column and repeat until nothing changes. A department total is shown only when its column passes.
- **Test:** property test on generated grids: no row, column or total line has exactly one hidden cell; hidden cells in each line sum to ≥ the minimum; AB-4 fixed case hides "Security, all branches" or a second Security branch cell.
- **If the engineer cannot build and prove this inside the slice, cut the tab** (Q2).

**PRIV-9 · The caller's own knowledge (recommended; Q1).**
(a) When the caller is inside a group, the size check counts the group **without them**. (b) When the caller can already see some of a group's people by name through their reporting line, the people left over must be either none or at least the minimum; otherwise the figure is hidden.
- **Test:** Arjun in a department of 5 → hidden at minimum 5. Line manager with 60 of Lakeside's 64 below them and Leadership on Lakeside → Lakeside's sensitive figures hidden for them (4 left over); a manager whose line covers all 64 → shown.

**PRIV-10 · Doubtful days do not become a side door.**
Detection only for groups with at least the minimum expected people. The "with doubtful days" figure is suppressed on its own population. Banner counts ("96-99% marked absent") appear only for groups that pass.
- **Test:** kiosk never shows a doubtful-day banner; "with doubtful days" for a hidden department is absent.

**PRIV-11 · No export, no ranking.**
No CSV or download endpoint for leader data. Tables are sorted by name **on the server**; no sort by a result column is accepted.
- **Test:** no whitelisted leader method returns a file; a sort parameter is refused.

**PRIV-12 · The employee "who can see" line tells the truth and nothing more.**
Built from real configuration, not fixed text. It must never claim **less** access than exists. It covers: the employee; their manager line; HR in scope (location HR where it applies, D14); the organisation attendance roles; **System Manager**; and any manager who can read their Attendance in the desk through a Branch permission. Leaders are named by role words, never by user. It quotes the current minimum and the employee's own branch. The endpoint takes **no employee parameter**; it answers only about the caller.
- **Test:** on the fixture tenant, enumerate users for whom `frappe.has_permission("Attendance", doc=<employee's record>)` is True, map them to categories, and assert every category appears in the line. Calling with an `employee` argument changes nothing.

**PRIV-13 · Purpose limitation.**
Leader totals are for operational oversight. They are **not** an input to any rating, KPI, pay or disciplinary record. No KPI source, adapter or appraisal code reads the leader module or its cache. A purpose constant in the module and one line on the settings page say so.
- **Test:** an import check fails if `alvoraa_goals` or appraisal code imports the leader module; code review confirms no KPI source uses leader figures.

**PRIV-14 · Retention, declared.**
Settings history: kept for the life of the tenant, at least one year; `Version` stays out of Frappe's log clean-up (confirmed by DevOps in Frappe source). HR confirmations and doubtful-day records: kept 13 months after the date they concern, plus one year [Q10]. The reason box says "Do not name employees" because the reason is kept and shown to HR Managers. **There is no retention engine today (feature map A6), so nothing is purged automatically.** This is a declared retention, not an enforced one.
- **Test:** assert `Version` is not in the log settings clean-up list on our build; the reason field carries the hint.

**PRIV-15 · Language of the employee line.**
The line is a transparency statement to frontline staff, many Hindi-first. Recommended: ship the Hindi line reviewed by a native speaker with the English one, or record the gap with the compliance owner (Q11).
- **Test:** when shipped, a parity check that both strings exist.

**PRIV-16 · Privacy changes are deliberate.**
Lowering the minimum shows the confirm dialog (01b §9) and cannot be done by a single click. The history shows the change to HR Managers.
- **Test:** UI test that lowering needs the confirm; server test is SEC-10.

---

## 10 · OPS-32 sign-off — compressing pages that carry the CSRF token

**Verdict: BREACH is not a realistic risk for Alvoraa's portal today. Approve OPS-26 compression, with conditions C1-C5.**

BREACH needs **all** of these at once. Here is each one, checked.

| Condition BREACH needs | Here | Evidence |
|---|---|---|
| 1. Responses are compressed | Yes, after OPS-26 | DevOps §2a |
| 2. A secret in the response body | **Yes.** The CSRF token and the user's email are in every portal page. The token is made **once per session and reused** on every page, so it does not change per request. That is the case BREACH likes | `hrms_employee.py` (reuses the token); Frappe `sessions.py:194-202` |
| 3. Attacker-chosen text reflected in the **same** response | **Not found on a default tenant.** The portal page takes no request input; its Jinja prints the session user, tenant name and support email. Frappe's base template prints the route (escaped). **One optional reflection:** if a tenant turns on navbar search in Website Settings, Frappe prints `?q=` into the page (`templates/includes/navbar/navbar_search.html:5`) | Read in Frappe 16.22.0; verify on our build (V4) |
| 4. The attacker makes the victim's browser send many logged-in requests | **Blocked for other websites.** The `sid` cookie is `SameSite=Lax` (Frappe default, `auth.py:403`; DevOps measured it). Other sites' images, scripts and fetches carry no cookie. Top-level page opens do carry it, but BREACH needs thousands, which a user would see | Frappe source; DevOps §2 |
| 5. The attacker sees response sizes on the network | Possible on shared store Wi-Fi | — |

**The weak spot, stated plainly.** `SameSite` works by **site** (`alvoraa.co`), not by host. Every tenant (`minda.alvoraa.co`, `demo.alvoraa.co`) and every dev site (`*.dev.alvoraa.co`) is the **same site** to a browser (`deploy/nginx.conf:67`, `:158`). A page on any of them — for example a Web Page with custom script that a tenant's own System Manager publishes, or unreviewed code on dev — **can** send logged-in requests to another tenant's portal. It would still need condition 3 (a reflection) and condition 5 (watching the network). Together that is unlikely. It matters more for people who are logged in to many tenants at once, such as our own support staff.

**Conditions:**

| # | Condition | How to check |
|---|---|---|
| C1 | `sid` stays `SameSite=Lax` or `Strict`. Never `None` | Look at `Set-Cookie` after login on the local bench (V3) |
| C2 | Navbar search stays **off** on tenants, or the portal page overrides the navbar block, so `?q=` is never printed on a page carrying the token | Open `/hrms-employee?q=ZZQX` on the bench; `ZZQX` must not be in the page (V4). Add this as a test in `test_portal_csrf.py` |
| C3 | No new code prints request input into portal HTML | Reviewer checklist line; the C2 test with extra marker parameters |
| C4 | New leader endpoints are POST-only (SEC-7), so a same-site page cannot fetch them with a simple GET | SEC-7 test |
| C5 | `allowed_referrers` and `ignore_csrf` are never set in site config | Grep site configs at deploy (not `server.env`) |

**Not a condition, but worth doing (hardening):** `deploy/nginx.conf` has **no `Strict-Transport-Security` header** (I grepped the repo file; the live file may differ). Also check that `sid` has the `Secure` flag behind the proxy: Frappe sets `Secure` only when it believes the request came over HTTPS (`auth.py:407-408`). On store Wi-Fi, a missing HSTS header or `Secure` flag is a much bigger risk than BREACH. This is a worry, not a finding, until V3 is run.

**This verdict does not change** when OPS-31 moves the script out of the page. The page still carries the token.

---

## 11 · DPDP and GDPR notes

**I am not a lawyer. Each ⚠ point needs the compliance owner, who is not named yet, or counsel.**

1. **Purpose.** Leader totals serve operational oversight of attendance and leave. The likely basis is DPDP s.7(i), "for the purposes of employment" (text checked 15 Sep 2026). That is why the design has no consent step. ⚠ Counsel confirms the basis (CQ1). Our own role — Data Fiduciary or Processor for tenant data — is still an open baseline question.
2. **Purpose creep is the real risk.** A branch's attendance total can quietly become a score for the branch manager. That is a different purpose and needs its own review. PRIV-13 blocks it in code.
3. **Aggregates are not "anonymous".** Totals for groups of 5 can still relate to people. In sales material and questionnaires, say "totals with small groups hidden", never "anonymised data". ⚠ Counsel on how to describe it (CQ2).
4. **Notice.** The formal privacy notice is the employer's duty. The "who can see" line is transparency, not the notice. It must be accurate (PRIV-12). The tenant setup guide should tell the employer to mention leader totals in their own notice. ⚠ CQ4. The baseline says notices belong in the languages the workforce reads; English-only is a gap (PRIV-15).
5. **Retention.** Settings history is an accountability record. DPDP Rules Rule 6(1)(e) asks for logs to be kept one year; I recommend at least that, and life of tenant for this small record. HR confirmations defend a changed figure, so keep them while that figure can appear, plus one year. Nothing purges today. ⚠ Counsel sets the upper bounds (CQ3).
6. **Security safeguards.** Rule 6(1)(c) asks for visibility of access through logs. SEC-14 covers refused access. Allowed leader views are not logged one by one; they hold totals only. ⚠ Confirm that is proportionate (CQ3).
7. **GDPR** applies only if the founder confirms EU exposure. If it does, the same design meets data minimisation; Art 88 member-state employment rules would need counsel per country.
8. **No DPIA gate triggered, in my reading.** No new collection, no automated decision, aggregates only. ⚠ The compliance owner confirms, and records the decision.

---

## 12 · Detection and incident readiness

- **What we can detect:** out-of-scope requests (SEC-14), settings changes (SEC-10), confirmations (SEC-13).
- **What we cannot detect:** subtraction by a leader within their own scope. Controls are preventive only.
- **Breach query for this slice:** if a suppression bug is found, the affected set is "leaders in scopes containing a group under the minimum, since the release date". The refusal log does not answer that; the **Frappe web request logs** would, if kept. ⚠ The breach workbench (feature map A5) does not exist, so this query is manual.

---

## 13 · Residual risk

None of these has been accepted yet. **Each needs a name and a date.** I propose Surbhi as owner.

| # | Risk | Why it remains | Size | Accepted by | Date |
|---|---|---|---|---|---|
| R1 | Two leaders pool what they see (company head + Station Road head; area manager + branch head) | No design stops collusion | Low | — | — |
| R2 | Differencing across changes of the minimum, or of a leader's branch set, on closed months | Suppression is not stable when the minimum or the set changes | Low (rare, recorded changes) | — | — |
| R3 | Day-to-day differencing of running totals (leave used, 12-month leavers) shows that "someone" took leave or left on a day | Running totals change daily. No names, no types | Low | — | — |
| R4 | Self-knowledge and line-manager overlap (AB-8, AB-9) | **Only if PRIV-9 is not adopted** | Medium | — | — |
| R5 | Branch attrition is approximate after transfers; old records stay with the old branch | Decided in slice 011 | Low (integrity, not privacy) | — | — |
| R6 | Administrator or direct database access can delete settings history | Frappe `Version` | Low | — | — |
| R7 | All tenants and dev share one browser "site" (OPS-32) | Domain design | Low | — | — |
| R8 | Redis keeps post-suppression totals on disk and in its backups for up to 60 minutes | Redis `appendonly yes` (07 §1) | Low | — | — |
| R9 | System Manager reads everything in the desk as CXO | Slice 010 decision; not widened here | Known, wide | Recorded in slice 010 | 2026-09-14 |

### Worries (not findings — I cannot write the full scenario yet)

- Frappe skips the CSRF check for a session that has no CSRF token yet (`auth.py:87`). A session made by an API login might have none. Combined with R7, a same-site page could then post as that user. Needs V9.
- ERPNext or Frappe HR may give HR Manager the right to set User Permissions on Employee or Branch. If so, an HR Manager could build a leader's branch set (AB-12). Needs V7.
- Whether User Permission changes leave a change history on our build. If not, AB-12 leaves no trace.

---

## 14 · Verification steps for later (need a running system — each needs your word)

| # | Check | Where | Proves |
|---|---|---|---|
| V1 | As a store HR user, call `get_hr_analytics`; count branches and names in the answer | Local bench | G1 by running, not only reading |
| V2 | As a store HR user, call `person()` for another branch's employee | Local bench | G3 |
| V3 | Log in; read `Set-Cookie` for `sid` (`SameSite`, `Secure`, `HttpOnly`); read response headers for HSTS | Local bench; dev read-only on your word | OPS-32 C1, hardening |
| V4 | Open `/hrms-employee?q=ZZQX` logged in; search the page for `ZZQX` | Local bench | OPS-32 C2 |
| V5 | As System Manager, try to delete a `Version` row (DevOps check D) | Local bench | SEC-11, R6 |
| V6 | Read the Branch doctype fields on our build: is there a company link? | Local bench (read-only) | AB-24, SEC-2 |
| V7 | Which roles can create or edit User Permission on our build, including `set_user_permissions` rights on Employee, Branch, Company | Local bench (read-only) | AB-12 |
| V8 | P1 side-effect counts before and after a Branch permission for a store head (SEC-5) | Local bench copy | SEC-5 baseline |
| V9 | Does a session from `/api/method/login` carry a CSRF token? | Local bench | Worry 1 |

---

## Open questions

### For you (Surbhi)

| # | Question | Recommended default | Blocks |
|---|---|---|---|
| Q1 | Adopt PRIV-9 (caller's own record, and people they already see in My team, do not count toward the minimum)? | **Yes.** Both parts. It is one grouped query | PRIV-9, AB-8/9, R4 |
| Q2 | D15 department tab across branches: build it with the two-way rule (PRIV-8), or cut it from this slice? | **Build only if the engineer sizes PRIV-8 as S and proves it with the property test; otherwise cut to the next slice** | D15, PRIV-8 |
| Q3 | Decide "shared or not" once per group, or per figure? | **Once per group**, using the smallest count | PRIV-4 |
| Q4 | Fix G2 (`set_org_setting` allowlist) in Step 0? | **Yes** | SEC-18, SEC-12 |
| Q5 | Fix G3 (`person()`, `filter_options()`) in Step 0? | **Yes** — same scope helper and tests as G1 | SEC-17 |
| Q6 | Block "Leadership" in the organisation attendance roles in code (SEC-19)? The brief said "no code guard" | **Yes.** A rule written only in a template is not a control | SEC-19 |
| Q7 | If the stored minimum is broken, use 10 (strictest)? | **Yes.** A support ticket costs less than a leak | SEC-10 |
| Q8 | A leader with only Branch permissions and no Employee record: "not set up"? | **Yes**, until they get a Company permission or an Employee record | SEC-1 |
| Q9 | A leader whose own Employee record is Left or Inactive: refused? | **Yes** | SEC-6 |
| Q10 | Retention: settings history for the life of the tenant; confirmations and doubtful days 13 months + 1 year | **Yes**, pending counsel's upper bound | PRIV-14 |
| Q11 | Ship the employee line in Hindi at launch? | **Yes, for that one line**, reviewed by a native speaker; otherwise record the gap | PRIV-15 |
| Q12 | May branch attendance ever become a manager's KPI? | **No, not from this slice.** It would need its own review | PRIV-13 |

### For the founder

| # | Question | Blocks |
|---|---|---|
| F1 | Name the compliance owner (a person) | Every ⚠ in section 11; accepting residual risks formally |
| F2 | EU exposure yes or no (still open from the baseline) | Whether section 11 point 7 is an obligation |

### For counsel or the compliance owner

| # | Question | Blocks |
|---|---|---|
| CQ1 | Is DPDP s.7(i) the right basis for showing leaders attendance and leave totals, with no consent step? | The employee line wording and the tenant setup guide |
| CQ2 | Totals with groups under 5 hidden: may we describe them as anything other than personal data? | Questionnaire answers and sales copy |
| CQ3 | Retention upper bounds for settings history and HR confirmations; whether settings history counts as a Rule 6(1)(e) log; whether per-view logging of allowed leader views is needed | PRIV-14, SEC-14 |
| CQ4 | Must the employer's privacy notice mention leader totals? | Tenant setup guide |
| CQ5 | G1-G3 were live on dev (demo data) and G1 is on main. With no live customers (14 Sep 2026), is anything reportable? | Nothing technical; the record of the decision |

## Assumptions

- `[ASSUMPTION]` Frappe 16.22.0 source (another local project) behaves like our `version-16` build for CSRF, cookies, User Permission and templates. V3, V4, V7 confirm.
- `[ASSUMPTION]` ERPNext's Branch doctype has no company field. From memory; V6 confirms.
- `[ASSUMPTION]` Employee IDs follow a guessable naming series.
- `[ASSUMPTION]` Dev and the reference tenant copy hold demo or copied data, not a live customer's production data, as your 14 Sep note says for production.
- `[ASSUMPTION]` `set_org_setting` on `main` fails for everyone because `frappe.has_role` does not exist there, as the dev code comment says. Not run.
- `[ASSUMPTION]` The only key the portal UI writes through `set_org_setting` is `kra_link_mandatory` (grep of `hrms-employee.html`).
- `[ASSUMPTION]` A tenant's System Manager can publish a Web Page with custom script on their subdomain (standard Frappe). Not checked on our build.
- `[ASSUMPTION]` DPDP text checked through secondary sites that quote the Act and Rules, not the Gazette PDF.

## Handoff note

To the business analyst: map every SEC and PRIV item to an acceptance criterion, or mark it "not adopted" with your decision date. Build the permission matrix from section 3, including the negative rows. Four things to watch. **First**, the change line, trend points and "headcount a year ago" are figures in their own right (PRIV-6, PRIV-7); 01b §16 does not say so yet. **Second**, the cache key must carry the leader's whole branch set, not just the branch on screen (SEC-9), or rule 5c makes two leaders share an answer. **Third**, D15 is not safe as drawn (Q1b); wait for Q2 before writing its stories. **Fourth**, Step 0 now carries three live fixes (G1-G3), and they should land and be tested before any leader screen. To the engineer: SEC-1 is the one function everything depends on; write its table test first, and run V6 and V7 before strategy, because a Branch without a company would change SEC-2. I disagree with the brief in one place: LV5 needs a code guard (SEC-19), not only a note in template T6.

---

**Sources checked on 15 Sep 2026:**
- [DPDP Act Section 7 text — dpdpa.com](https://www.dpdpa.com/dpdpa2023/chapter-2/section7.html)
- [Key implications for employers — Lexology](https://www.lexology.com/library/detail.aspx?g=acf9c719-ea09-437f-97ba-5d857c2db249)
- [DPDP Rules 2025, Rule 6 — dpdpa.com](https://www.dpdpa.com/dpdparules/rule6.html)
- [BREACH attack — breachattack.com](https://www.breachattack.com/)
- [Drupal core discussion of BREACH defences and SameSite](https://www.drupal.org/node/2234243)
