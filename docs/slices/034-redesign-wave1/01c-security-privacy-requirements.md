---
slice: 034-redesign-wave1
artifact: 01c-security-privacy-requirements
author: hrms-fullstack-engineer, revised after the security re-review (06b-security-rereview.md)
date: 2026-09-23
revision: 3 (N1–N9 applied; Surbhi's decisions of 23 Sep, W1D-13 to W1D-18, written in)
status: draft, revised — ready for build once the strategy gate is passed
inputs: [06b-security-rereview.md, 02c-ba-rereview.md, 06-security-review-of-requirements.md, 02b-ba-review.md, 00-impact-analysis.md, 00g-decision-register.md, ../030-store-hr-scoping/00-impact-and-fix.md, .claude/context/security-compliance-baseline.md]
---

# Wave 1 frame — security and privacy requirements

**Revision 3.** The security re-review's three must-fixes (N1, N2, N4) and its five smaller
notes (N3, N5, N6, N7, N8) are applied, and Surbhi's six decisions of 23 September are
written in. Nothing was declined. What changed is listed at the end.

**Decisions are cited as `W1D-nn`** and live in `00g-decision-register.md`. Bare
"decision 5" numbers are gone from this document; the two sets in
`../009-ess-portal-redesign/00f-decisions-2026-09-22.md` are cited as "009 design
decision n" and "009 strategy decision n".

## Threat model

1. **A logged-in employee** changes the calls the page makes, to reach people, counts or
   pages outside their scope. Every new endpoint is whitelisted and callable by hand.
2. **A store's HR person** reads another store's people, corrections, approvals or team
   list, because those paths scope by company today.
3. **A leaver whose login is still enabled** uses the endpoints this slice touches.
   ERPNext does not disable the User when an Employee is set to Left.
4. **Anyone who guesses the preview address.** On the local bench and on dev the page
   exists and shows unfinished screens with real data to a System Manager. **On production
   the page does not exist at all** (SEC-1, W1D-15): the site flag is missing, so the route
   is 404 for everyone including a System Manager.
5. **Blast radius:** the portal is the landing page on every tenant and the swap is one
   commit, so one wrong line reaches every person on every tenant. A cache kept in a
   module, in a worker that serves several sites, would be the worst case of all —
   one tenant's data handed to another.
6. **How we would find out:** refusals are logged through `access.log_refusal`. **A
   successful over-read leaves no signal.** Nobody reads the security log and nothing
   alerts on it (residual risk R3, now owned and dated). The tests are the only defence
   in Wave 1.
7. **A fail-closed helper turned fail-open by refactoring.** `permitted_employees()`
   fails closed by returning an empty **set**. Its new filter-shaped twin cannot: in
   Frappe an empty filter **dict** means everybody. SEC-4 requires the refusal to be
   explicit so that no later caller can turn a denial into a full-tenant read by accident.

## Data inventory

| Data | Where it appears | Sensitivity | Purpose | Kept |
|---|---|---|---|---|
| The caller's own `employee`, `employee_name`, `designation`, `department`, `image`, `company` | Rail, profile menu | Personal, low | Show who is signed in | Not stored by the frame |
| The caller's own date of birth, gender, phone, joining date, manager, branch | **Never in `get_frame`** (SEC-12) | Personal, higher | — | — |
| Colleague name, job title, department, photo | Search results, Team panel | Personal, low | Find a person in your scope | Not stored |
| Colleague phone, email, employee number, branch, manager | **Never** in search or the frame | Personal | — | — |
| Counts of pending items, by part | Bell, menu, bottom bar, Inbox page | Aggregate; shows that work exists, never whose | Tell a person work is waiting | Not stored; counted live |
| Theme choice | Browser storage on the device | Preference | Light or dark | That device only |
| `User.language` | — | — | **Not written in Wave 1** (W1D-04) | — |

## Who must NOT see what

| Who | Must not see |
|---|---|
| Employee | Anyone outside their own line downwards in search (009 strategy decision 5, and Q-c of 14 Sep). Counts about other people's work |
| Manager | People outside their line downwards. Counts for items that are not theirs to act on |
| Store HR | Anyone outside **their store plus their own reporting line** (W1D-07) — in search, counts, the bell list, the corrections queue **and the Team panel's no-manager list** (SEC-13, W1D-13). An employee with no branch is outside the store (slice 030, DEF-6) |
| Company-wide HR | People and items outside their permitted companies |
| A leaver (Employee not Active) with an enabled login | Any colleague in search, any approval count or bell item (SEC-14) |
| A tenant's own System Manager | The Alvoraa control plane (`/alvoraa-admin`) — not offered. **The preview page on production** — it does not exist there (SEC-1, W1D-15) |
| Anyone who is not a System Manager | The preview page, on any site, until the swap |
| Guest | Anything; every new endpoint refuses Guest |

## Obligations engaged, with dates

| Obligation | Source, checked | How Wave 1 meets it |
|---|---|---|
| DPDP Act 2023 — minimisation and safeguards; Data Fiduciary duties phase in to about May 2027 (⚠ counsel to confirm) | baseline §5, verified 24 Aug 2026 | SEC-12 (fixed field list), PRIV-2 (search fields), PRIV-4 (numbers only) |
| Access rights on every path | baseline §4, verified 24 Aug 2026 | SEC-2 to SEC-5, SEC-13, SEC-14 |
| Logging duties — no personal content in logs | baseline §5 and CERT-In (log content, not residency) | PRIV-5 |
| OWASP ASVS 5.0 L2, access control and output encoding | baseline §4, verified 24 Aug 2026 | SEC-3, SEC-4, SEC-10 |

Counsel's retention rules and the rules on automated decisions are **not engaged**: the
frame stores nothing and decides nothing (security review §6, unchanged at re-review).

## Abuse cases

| # | Actor and path | What must happen |
|---|---|---|
| A1 | Employee calls `search_people` with a colleague's name from another store | No result |
| A2 | Store HR reads the bell list, the counts or the corrections queue | Only their store, plus their own reports |
| A3 | Employee watches their own count over time to work out when a colleague applied for leave | Impossible: an employee's count holds only their own requests and items addressed to them |
| A4 | Anyone opens `/hrms-employee-next` **on production** | **404** — the site flag `portal_preview` is not set there, so the route does not exist (SEC-1, W1D-15). On dev and the local bench: 200 for a System Manager, 403 for any other signed-in person, login redirect for Guest |
| A5 | Tenant owner un-hides the Tenant admin link and clicks it | `/alvoraa-admin` refuses: it checks `alvoraa_control_plane` itself |
| A6 | Caller sends a search string with SQL, `%`, `_` or HTML in it | Treated as text; wildcards escaped; results escaped when drawn |
| A7 | A tenant's logo URL holds a script | Escaped in the attribute, as slice 025 does |
| A8 | Someone who may create a Designation names one `<img src=x onerror=alert(1)>` | It appears as text in search, the rail and the profile menu; no element is created (SEC-10) |
| A9 | A manager resigns; HR sets his Employee to Left; his login stays enabled and his reports are not yet moved. That evening he searches for people and asks for his approvals | Empty search, zero approvals, empty bell list (SEC-14) |
| **A10** *(corrected, W1D-18)* | **A tenant's own System Manager opens the preview page** | On production there is nothing to open (A4). On dev they see unfinished screens with their own tenant's data, under their own permissions — which they already see in the desk. **Alvoraa's own staff are not System Managers on client tenants**; our access is the shared `Administrator` account (W1D-18). That shared account is its own problem — a read cannot be traced to a person — and it is `ALV-93`, outside Wave 1 |
| **A11** *(new, W1D-13)* | **A store's HR person with one direct report opens the Team panel**, which is built by `get_manager_dashboard` | They see their own reports plus employees with no manager **from their own company and store only** — never head office (SEC-13). Before this change they saw every employee in the tenant who had no manager set |
| **A12** *(new, W1D-14)* | **A Shift Supervisor who holds submit permission on Attendance Request opens the corrections queue** | Their queue still works, scoped by Frappe's own permissions exactly as today. The `permitted_employees()` narrowing applies to HR callers only (SEC-5). A failure here would be fail-closed, not a leak — but a dead flow gets repaired under pressure by loosening the filter, which is how the leak comes back |

## Requirements

| ID | Requirement | How it is tested |
|---|---|---|
| **SEC-1** | `/hrms-employee-next` exists **only where `frappe.conf` carries `portal_preview: 1`** (W1D-15) — the local bench and the dev stack, never production. Without the flag the route is **404** for everyone, System Manager included. With the flag it answers 200 only to System Manager, **403** to everyone else signed in, and redirects Guest to login. It sets `context.no_cache = 1` (OPS-12) and is not in the sitemap. Both checks are in the page's `get_context`, on the server; the flag is tested first, so the role check is the second of two locks, never the only one | **Load the route over HTTP** with the flag set, as Guest, Employee, manager, company HR, store HR and System Manager, and check the status code. **Flag-off test:** with `portal_preview` absent, a System Manager gets 404. **Deployment test:** no production config file or compose environment in the repository sets `portal_preview`. **Swap-commit test:** the route returns 404 and no tracked file names `hrms-employee-next` |
| **SEC-2** | The preview gate is not a data control. Every new whitelisted function is live on production from the first release that carries it, whatever page calls it — the site flag hides the **page**, never the endpoints. Each ships **in the same commit** as its Guest-refused test, its wrong-persona test and its scope test. The scope changes in SEC-3, SEC-4, SEC-5 and SEC-13 also change today's live portal the moment they are released, so they are tested against the current page as well | A **registry test** lists every whitelisted function in `frame_api.py` and `inbox_api.py` with its cases; a new whitelisted function with no entry fails the test. (`test_portal_call_paths` does not prove this: it checks a path exists and is whitelisted, not that it checks the caller) |
| **SEC-3** | `_pending_approvals_scope` limits HR to `access.permitted_employees()`, Active only, minus the caller, **plus the caller's own Active direct reports** — the union the helper has today, so a store HR person does not lose their own reports in another store. The count and the bell list keep sharing it | Two-store fixture: store HR sees their store; company-wide HR sees both; a store HR person with a report in another store still sees that report |
| **SEC-4** | People search uses one shared definition, not a copy: a new `access.permitted_employee_filters(user)` returns the filters, `permitted_employees()` uses it, and `_search_scope` uses it for HR. **Store HR finds their store plus anyone reporting to them** (W1D-07). An employee with no branch is outside every store. System Manager is not narrowed. **The helper never returns an empty or partial filter dict** (N1): `permitted_employees()` fails closed today by returning an empty **set** (`hrms/hrms/alvoraa_hr_core/access.py:237-267`), and an empty **dict** in Frappe means every record, so the filter-shaped twin must refuse explicitly — either a sentinel the caller is forced to handle, or filters that match nothing (`{"name": ["in", []]}`). A caller with no HR entitlement gets the refusal, never a wide read | Two-store fixture plus a head-office employee with no branch: store HR does not find them, company-wide HR does. A store HR person finds their own report in another store. **N1 tests:** called as a plain employee, as a manager and as a Vendor User, the helper produces a query returning zero rows; and a direct assertion that the return value is never `{}` and never a dict with no keys |
| **SEC-5** | Every count part names the scope helper it reuses, and the count equals the list the Inbox row links to: |  |
| | · Leave to approve — `leave_approver` = the session user, `status = Open`, `docstatus = 0`, the same filter as today's list | count-matches-list test per part and per persona |
| | · Goal and KPI updates — `_pending_approvals_scope`, `approval_status` empty, NULL or `Pending` | fixtures cover all three pending states |
| | · Attendance corrections — **for an HR caller**, counted **and listed** among `permitted_employees()`, minus the caller; `attendance_correction.to_review` gains the same filter (W1D-05). **For a reviewer who is not HR** — `_may_review()` (`alvoraa_portal/alvoraa_portal/attendance_correction.py:240-248`) tests submit permission, not a role, so a tenant may grant the queue to a Shift Supervisor — **no `permitted_employees()` filter is applied and the queue is exactly what it is today** (W1D-14). The HR test is the same role test `permitted_employees()` uses internally. The non-HR reviewer's scoping is a known gap, recorded here, not silently altered | store HR: one correction in their store, one in another store, one from a head-office employee with no branch → count 1, list 1. Company-wide HR → 3 and 3. **Non-HR reviewer holding submit: count 3, list 3 — unchanged by this slice** |
| | · Shift requests — `approver` = the session user, draft | |
| | · Policies to acknowledge — `hrms.alvoraa_policy_library.access.readable_policy_names()`, the same query the list uses; never a new rule written for the batch | |
| | · My own open requests — the caller's own **Active** Employee only | |
| | **Capped lists** (N3): `to_review(limit=50)` reads at most 50 rows by creation date **and then** drops the non-waiting ones in Python, so a naive count and the screen disagree above the cap. The count must use **the same definition of "waiting" the list uses**, expressed so the database applies it — `docstatus = 0` and `alvoraa_review_status` not in `Declined`, `Withdrawn`, **including rows where it is NULL or empty** `[UNVERIFIED — whether Frappe's "not in" wraps the column in ifnull(); confirmed on the bench before step 4. If it does not, the count reads the ids and applies the same Python filter]`. **The count is not capped**; where it exceeds the list's cap the screen says "showing the first 50 of 60" rather than quietly showing fewer. *(The security review offered the alternative — cap the count and show it as `50+`. I did not take it: a "50+" cannot be added into the one honest Inbox total that AC-20 requires.)* | **Boundary test:** a fixture with one more waiting correction than the cap — the count reads 51, the screen lists 50 and says so |
| | **Every fixture item is created through the endpoint a real user uses** (apply for leave through the portal, log a goal update through the portal), never inserted in its final state. **Real-data check once before the swap:** on the local PP Jewellers copy, as slice 030's store HR user, the counts and search are compared with that user's Employee list in the desk; the result goes in the implementation notes | |
| **SEC-6** | The new endpoints refuse Guest, take no doctype, field or method name from the caller, and are POST where they write. `frame_api.py` and `inbox_api.py` contain **no** `ignore_permissions`, and the bodies of `_pending_approvals_scope`, `_search_scope` and the new `permitted_employee_filters` gain none. `get_manager_dashboard`'s existing `ignore_permissions=True` is not removed by this slice — SEC-13 narrows what it reads instead, and removing it is `ALV-86` territory | A test that reads `frame_api.py` and `inbox_api.py` and counts `ignore_permissions`. **The repo-wide counter does not exist**; it is the security engineer's item (feature map B4) and this slice does not claim it — residual risk R4, now owned and dated. No count of today's uses is quoted here: the two figures that have been quoted in these reviews disagreed, and the baseline is whatever the B4 script measures on the day it runs (N7) |
| **SEC-7** | "Switch to the full desk" shows only when `get_switch_target` returns a target (admins → `/app`, HR → `/app/hr`, nobody else), and the label comes from the server | Test per role on `get_frame`'s payload |
| **SEC-8** | "Tenant admin" shows only when the caller is a System Manager **and** the site is the control plane (`alvoraa_control_plane`). `/alvoraa-admin`'s own check is unchanged | Test on both site types, setting `frappe.conf` in the test |
| **SEC-9** | **`set_my_language` is not built in Wave 1** (W1D-04). No frame code writes a `User` record. A language is *offered* only when it is enabled on the site **and** `alvoraa_portal` ships a translation for it; in Wave 1 that is English only, so the row is hidden everywhere. When the endpoint is built in a later wave it must be POST only, take no user argument, accept only an offered language, save through the document (so change history and date formats are kept), and carry the single declared `ignore_permissions` with its justification beside it — never `frappe.db.set_value` | A test that no frame module writes to `User`, and that no language row is rendered on a site with the Frappe default 17 enabled languages |
| **SEC-10** | Everything the frame puts on the page from data is escaped — in Jinja (`\| e`, as the rail's logo does) **and in the browser**. Frame include files never assign API data to `innerHTML`; they use `textContent` or one shared escape helper | A check script scans `templates/includes/ess/frame/` for `innerHTML` with API data. **DOM test:** a designation of `<img src=x onerror=alert(1)>` appears as text in a search result, the rail and the profile menu, and creates no element. `test_brand_logo_025` repointed |
| **SEC-11** | Page search offers only pages from the menu list, after the same visibility rules | Test per persona on the searchable page list |
| **SEC-12** | `get_frame` returns **only named keys**. The caller's own block holds `employee`, `employee_name`, `designation`, `department`, `image`, `company` — never `date_of_birth`, `gender`, `cell_number`, `date_of_joining`, `reports_to` or `branch`. Roles go out as the booleans the menu needs (`is_hr`, `is_manager`, `is_system_manager`, `is_control_plane`), not the whole role list. The cached context may decide what the menu shows; it never decides what data an endpoint returns — every data endpoint reads roles live. `get_portal_context` itself is not changed in this slice (follow-up: its other callers) | The payload's keys are exactly this set, per persona |
| **SEC-13** *(new, W1D-13)* | **The Team panel's "employees with no manager" list is narrowed to the caller's own people.** `get_manager_dashboard` (`alvoraa_portal/alvoraa_portal/hr_api.py:291-307`) today adds **every** Active employee with `reports_to` not set, with `ignore_permissions=True` and no company or branch filter, for anyone holding HR Manager or HR User. It must instead add only those also inside `access.permitted_employees()` for the caller — so a store's HR person sees their store's unassigned people and never head office. The caller's own record stays excluded, as today. The direct-report block and the L2 block are unchanged; the L2 query narrows on its own because it reads from the narrowed list. **This is a narrowing of a live screen and takes effect the moment it is released, not at the swap** | Two-store fixture with an unassigned employee in store A, one in store B and one at head office with no branch: store A's HR sees their own reports plus store A's unassigned person only; company-wide HR sees all three; a manager who is not HR sees no unassigned people at all, as today. Also a test that the panel does not become empty for a store HR person who has one direct report |
| **SEC-14** | The frame's endpoints, `_search_scope` and `_pending_approvals_scope` find the caller's Employee **with status Active only**. A caller whose record is not Active and who holds no HR role finds nobody and has nothing to approve; they may still see their own open requests. `_me()` is not changed globally (the org chart uses it widely) — the Active lookup goes inside the two helpers this slice already claims (W1D-06). The wider fix across `goals_api` is **ALV-87**. **This changes today's live bell and org-chart search on release, not at the swap** | A Left manager with an enabled login and unmoved reports: empty search, zero approvals, empty bell list |
| **SEC-15** | The new modules keep no module-level cache and no mutable global, because a worker can serve several sites. Any cache uses `frappe.cache()` (per site) or `frappe.local` (one request), keyed by user | A static check on `frame_api.py` and `inbox_api.py`: no `global`, no module-level dict, list or set changed at run time |
| **PRIV-1** | People search keeps 009 strategy decision 5 and Q-c of 14 Sep: an employee or manager finds themselves and people below them; HR finds their permitted people (store HR: their store plus their own line); nobody finds anyone else | Tests per persona |
| **PRIV-2** | A search result returns **Active employees only** — never Left, Inactive or Suspended — and its keys are exactly `employee`, `name`, `title`, `department`, `image`. `employee` is a link key and is never displayed. No phone, email, employee number, branch or manager | Test on the payload keys, not the screen; one Left, one Inactive, one Suspended and one Active person all matching the term — only the Active one returns |
| **PRIV-3** | `%` and `_` in the search term are escaped before they reach `like`. A search needs at least two letters. The frame asks for 12 and the server returns at most 50, all from the caller's scope | Test `%%` and `a_b`; test the 12 and the 50 caps |
| **PRIV-4** | Counts and the Inbox page show **numbers only** — no names, reasons or document ids. The frame never calls `get_pending_approvals` on page load (it returns names, notes and evidence, and costs about 15,000 queries for HR on a 403-person tenant) | Test the payload shape; a test that no boot path calls `get_pending_approvals` |
| **PRIV-5** | Frame logs carry the endpoint, the user id, the outcome and the time — never a name, a search term or a per-person count. Refusals use `access.log_refusal`. **Search and every write send arguments in a POST body, never the query string**, because the web server logs URLs | Automated log-capture test on a refused call and on a search; a test that the frame's search call is a POST |
| **PRIV-6** | The theme is stored on the device only and holds no personal data | Review |
| **PRIV-7** | The frame widens no visibility. **The table is below** (N5 — it was required in revision 2 but never written; it is written now). The wider design search (manager and leadership) is not built | The test engineer checks the table below against the built screens; PRIV-1 and PRIV-2 tests |

### There is no SEC-13 gap any more

Revision 2 skipped SEC-13 by accident (N8). The number is now used by the Team-panel
requirement above, so the series runs SEC-1 to SEC-15 with nothing missing.

## PRIV-7 — the visibility table

Every thing the frame shows, who sees it, and where that same person can already see it
today. **Nothing in the frame is wider than what the person has today; six rows are
narrower.**

| What the frame shows | Who sees it | Where that person sees it today | Wave 1 |
|---|---|---|---|
| Own name, designation, department, photo, company | Everyone with an Employee record | Today's sidebar header on `hrms-employee.html`, and `/me` | Same |
| Own date of birth, gender, phone, joining date, manager, branch | Nobody — not in the payload | `/me` and the desk, for the person themselves | **Narrower** (SEC-12: revision 1's payload carried them) |
| Colleague name, job title, department, photo | Employee, manager | Today's org-chart search, same downward scope | Same |
| Colleague name, job title, department, photo | Store HR | Today's org-chart search, **company-wide** | **Narrower** (SEC-4, W1D-07) |
| Colleague name, job title, department, photo | Company-wide HR | Today's org-chart search, permitted companies | Same |
| Colleague name, job title, department, photo | A leaver with an enabled login | Today's org-chart search — it still works for them | **Narrower** (SEC-14: nothing) |
| Team panel: own direct and L2 reports | Manager, HR with reports | Today's Team panel | Same |
| Team panel: employees with no manager | HR Manager / HR User | Today's Team panel, **every one of them in the tenant** | **Narrower** (SEC-13, W1D-13) |
| Count: leave to approve | Whoever is named approver | Today's leave list | Same |
| Count: goal and KPI updates | Manager, HR | Today's Growth approvals list | Same for managers; **narrower** for store HR (SEC-3) |
| Count and list: attendance corrections | HR reviewer | Today's `to_review` queue, company-wide | **Narrower** for store HR (SEC-5, W1D-05) |
| Count and list: attendance corrections | A non-HR reviewer with submit permission | Today's `to_review` queue, scoped by Frappe permissions | Same — deliberately unchanged (W1D-14) |
| Count: shift requests | Named approvers | Today's shift panel | Same |
| Count: policies to acknowledge | Everyone | Today's Policies panel | Same |
| Count: my own open requests | Everyone with an Active Employee record | Today's own panels | Same |
| "Switch to the full desk" | HR and admins, when the server returns a target | Today's switch control | Same |
| "Tenant admin" | Control-plane operators | Today's admin console | Same |
| The preview page | System Manager, on dev and local only | — (new) | New page, **no new data**: own permitted data only, and it does not exist on production (SEC-1, W1D-15) |

## Dependency, not designed around

**The org chart shows every company and every store** to any manager with one report and
to every HR user (security finding F1). A Wave 1 search result opens that chart, so the
problem becomes one click from every page. **The user did not accept this: it is
`ALV-86`, Critical, to be fixed before DTC's go-live** (W1D-08). Wave 1 does not work
around it and does not depend on it being fixed first; release readiness records its
state on the day of the swap.

Note that SEC-13 narrows the **Team panel**, not the org chart. They are different screens
with different queries, and ALV-86 still stands.

## Residual risk — every one now has an owner and a date

| # | Risk | Owner | Date | State |
|---|---|---|---|---|
| R1 | The org chart shows every company and store (F1) | Fullstack engineer | Before DTC go-live | **Not accepted. `ALV-86`, Critical** (W1D-08) |
| R2 | A leaver keeps goal-approval access outside the frame's two helpers (F2) | Fullstack engineer | With `ALV-87` | **Not accepted; scheduled** (W1D-06) |
| R3 | A successful over-read leaves no signal; nobody reads the security log | Security & privacy engineer, with DevOps for delivery | **Logging first step 2026-10-15; the detection slice 2026-11-30** | **Accepted for Wave 1, with the dates** (W1D-17). Step 1 is a structured event whenever an HR-scoped read runs company-wide, plus a weekly digest to one named person. The full slice waits until after DTC go-live |
| R4 | No repo-wide `ignore_permissions` counter in CI | Security & privacy engineer (feature map B4) | **Baseline script 2026-10-31; blocking gate on the next commit after** | **Accepted for Wave 1, with the dates** (W1D-17). The gate must exist before Wave 2 adds endpoints. Until then SEC-6's file-scoped test holds two files |
| R5 | A tenant System Manager sees unfinished screens with real data on production | — | — | **Removed, not accepted** (W1D-15). The preview page does not exist on production. What remains is dev only, where the viewer sees their own tenant's data under their own permissions — the same data the desk gives them |
| R6 | Store HR whose Branch permission applies to only some record types is treated as company-wide (`access.py:233` — `applicable_for in (None, "", "Employee")` fails open) | **Live-tenant check:** Surbhi, with the tenant admin. **Code fix:** fullstack engineer, in `ALV-86` | **Live-tenant check by 2026-09-30, before DTC go-live; code fix by 2026-11-15** | **Accepted for Wave 1, with the dates** (W1D-16). The check lists the Branch User Permissions on `dtc`, `aahr` and PP Jewellers and reads `applicable_for`. If any is narrowed to a single doctype, the risk is live today and the priority changes immediately |
| R7 *(new)* | Alvoraa staff reach client tenants through one shared `Administrator` login, so a read cannot be traced to a person | Surbhi, with the security engineer | `ALV-93` | **Recorded, outside Wave 1** (W1D-18). Named logins and the access log on the two client tenants |

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | *Closed:* 403 or 404 for the preview page → **404 where the site flag is absent, 403 where it is present and the caller is not a System Manager, login redirect for Guest** (W1D-15) | — | — |
| 2 | *Closed:* R3, R4 and R6 owners and dates → **accepted as recommended** (W1D-16, W1D-17) | — | — |
| 3 | *Closed:* whether a tenant System Manager may see unfinished screens with real data → **moot; the page does not exist on production** (W1D-15) | — | — |
| 4 | *Closed:* re-check of revision 2 → `06b-security-rereview.md`, closed with notes; those notes are applied here | — | — |
| 5 | **Open:** `ALV-93` — named logins in place of the shared `Administrator`, and the access log on `dtc` and `aahr` | Surbhi, with the security engineer | Nothing in Wave 1 |

## Assumptions

- `[ASSUMPTION]` `access.permitted_employees()` and `permitted_branches()` behave as their
  docstrings and slice 030's tests say. Both were read in this worktree on 23 Sep.
- `[ASSUMPTION]` Frappe's `/me` shows only the caller's own record — to be checked once on
  the bench before step 2.
- `[ASSUMPTION]` `goals_api` defines `_is_hr` twice (`:17` and `:245`) and the second wins;
  SEC-3's edit sits between them. Whoever edits it must know which one runs.
- `[ASSUMPTION]` Frappe's `"not in"` filter wraps the column in `ifnull()`, so a NULL
  `alvoraa_review_status` is counted as waiting. **Not verifiable here — the Frappe source
  is in the bench container, not the repository.** SEC-5 carries the fallback if it is
  wrong.
- `[ASSUMPTION]` `frappe.conf` is readable in a website page's `get_context`, as SEC-8's
  `alvoraa_control_plane` check already assumes. Confirmed by that check existing; still to
  be run once.

## What changed in revision 3

| Review item | Change |
|---|---|
| **N1** | SEC-4: the shared filter helper must never return an empty or partial dict; explicit refusal (sentinel or `{"name": ["in", []]}`), with the "never `{}`" assertion and three non-HR callers as tests. New threat-model point 7 |
| **N2** (W1D-14) | SEC-5's attendance row splits by caller: the `permitted_employees()` filter applies to HR only; a non-HR reviewer holding submit keeps today's queue. New abuse case A12 |
| **N3** | SEC-5 gains the capped-list rule: the count uses the list's own definition of waiting, applied in the database; the count is not capped; the screen says "showing the first 50 of 60". Boundary test at cap + 1. The `50+` alternative is declined, with the reason |
| **N4** | Every bare "decision n" is replaced by `W1D-nn`, and `00g-decision-register.md` holds the set. The two sets in `00f` are cited by name |
| **N5** | PRIV-7's table is written — 18 rows, per persona, with today's equivalent. Six rows are narrower, none wider |
| **N6** | (in `02` §17) The SEC-2 traceability row now points at AC-69 alone |
| **N7** | SEC-6 no longer quotes a number of `ignore_permissions` uses, and says why |
| **N8** | SEC-13 exists — the numbering gap is filled by a real requirement, not a note |
| **W1D-13** | New SEC-13: the Team panel's no-manager list is narrowed to `permitted_employees()`. New abuse case A11. Added to SEC-2's "changes the live portal on release" list and to SEC-6's `ignore_permissions` note |
| **W1D-15** | SEC-1 gains the `portal_preview` site flag as the first lock, the flag-off 404, and a check that no production config sets it. Threat-model point 4, A4, A10 and R5 rewritten |
| **W1D-16, W1D-17** | The residual-risk table gains an owner and a date on every row |
| **W1D-18** | A10 corrected: our staff are not tenant System Managers. New R7 for the shared `Administrator`, `ALV-93` |

## Handoff note

To the security engineer, for the review at the end: the three things I would check first
are **SEC-4's refusal** (the one place where a fail-closed control could turn fail-open),
**SEC-5's split by caller** (the non-HR reviewer must still have a working queue — a dead
flow is how the filter gets loosened later), and **SEC-13**, which like SEC-14 narrows a
live screen the moment it is released rather than at the swap. Both of those go in the
release note.

R5 is gone rather than accepted: the preview page no longer exists on production. R3, R4,
R6 and the new R7 are accepted with owners and dates, in Surbhi's words, not mine.
