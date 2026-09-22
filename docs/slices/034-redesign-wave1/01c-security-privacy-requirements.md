---
slice: 034-redesign-wave1
artifact: 01c-security-privacy-requirements
author: hrms-fullstack-engineer, revised after the security review (06-security-review-of-requirements.md)
date: 2026-09-22
revision: 2 (ALV-84 — M1–M8 and S1–S10 applied; the user's decisions of 22 Sep recorded)
status: draft, revised — for the security engineer to re-check the changed items
inputs: [06-security-review-of-requirements.md, 02b-ba-review.md, 00-impact-analysis.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, ../030-store-hr-scoping/00-impact-and-fix.md, .claude/context/security-compliance-baseline.md]
---

# Wave 1 frame — security and privacy requirements

**Revision 2.** Every change the security review required (M1–M8) and every "should"
(S1–S10) is applied. Nothing was declined. The user's decisions of 22 September are
recorded where they settle a point. What changed is listed at the end.

## Threat model

1. **A logged-in employee** changes the calls the page makes, to reach people, counts or
   pages outside their scope. Every new endpoint is whitelisted and callable by hand.
2. **A store's HR person** reads another store's people, corrections or approvals,
   because those paths scope by company today.
3. **A leaver whose login is still enabled** uses the endpoints this slice touches.
   ERPNext does not disable the User when an Employee is set to Left.
4. **Anyone who guesses the preview address** on production sees unfinished screens with
   real data, under their own permissions.
5. **Blast radius:** the portal is the landing page on every tenant and the swap is one
   commit, so one wrong line reaches every person on every tenant. A cache kept in a
   module, in a worker that serves several sites, would be the worst case of all —
   one tenant's data handed to another.
6. **How we would find out:** refusals are logged through `access.log_refusal`. **A
   successful over-read leaves no signal.** Nobody reads the security log and nothing
   alerts on it (residual risk R3). The tests are the only defence.

## Data inventory

| Data | Where it appears | Sensitivity | Purpose | Kept |
|---|---|---|---|---|
| The caller's own `employee`, `employee_name`, `designation`, `department`, `image`, `company` | Rail, profile menu | Personal, low | Show who is signed in | Not stored by the frame |
| The caller's own date of birth, gender, phone, joining date, manager, branch | **Never in `get_frame`** (SEC-12) | Personal, higher | — | — |
| Colleague name, job title, department, photo | Search results | Personal, low | Find a person in your scope | Not stored |
| Colleague phone, email, employee number, branch, manager | **Never** in search or the frame | Personal | — | — |
| Counts of pending items, by part | Bell, menu, bottom bar, Inbox page | Aggregate; shows that work exists, never whose | Tell a person work is waiting | Not stored; counted live |
| Theme choice | Browser storage on the device | Preference | Light or dark | That device only |
| `User.language` | — | — | **Not written in Wave 1** (decision 4, M6) | — |

## Who must NOT see what

| Who | Must not see |
|---|---|
| Employee | Anyone outside their own line downwards in search (decision Q-c). Counts about other people's work |
| Manager | People outside their line downwards. Counts for items that are not theirs to act on |
| Store HR | Anyone outside **their store plus their own reporting line** (decision 7) — in search, counts, the bell list and the corrections queue. An employee with no branch is outside the store (slice 030, DEF-6) |
| Company-wide HR | People and items outside their permitted companies |
| A leaver (Employee not Active) with an enabled login | Any colleague in search, any approval count or bell item (SEC-14) |
| A tenant's own System Manager | The Alvoraa control plane (`/alvoraa-admin`) — not offered |
| Anyone not System Manager | The preview page, until the swap |
| Guest | Anything; every new endpoint refuses Guest |

## Obligations engaged, with dates

| Obligation | Source, checked | How Wave 1 meets it |
|---|---|---|
| DPDP Act 2023 — minimisation and safeguards; Data Fiduciary duties phase in to about May 2027 (⚠ counsel to confirm) | baseline §5, verified 24 Aug 2026 | SEC-12 (fixed field list), PRIV-2 (search fields), PRIV-4 (numbers only) |
| Access rights on every path | baseline §4, verified 24 Aug 2026 | SEC-2 to SEC-5, SEC-14 |
| Logging duties — no personal content in logs | baseline §5 and CERT-In (log content, not residency) | PRIV-5 |
| OWASP ASVS 5.0 L2, access control and output encoding | baseline §4, verified 24 Aug 2026 | SEC-3, SEC-4, SEC-10 |

Counsel's retention rules and the rules on automated decisions are **not engaged**: the
frame stores nothing and decides nothing (security review §6).

## Abuse cases

| # | Actor and path | What must happen |
|---|---|---|
| A1 | Employee calls `search_people` with a colleague's name from another store | No result |
| A2 | Store HR reads the bell list, the counts or the corrections queue | Only their store, plus their own reports |
| A3 | Employee watches their own count over time to work out when a colleague applied for leave | Impossible: an employee's count holds only their own requests and items addressed to them |
| A4 | Anyone opens `/hrms-employee-next` on production | 403 for a signed-in non-System-Manager, login redirect for Guest |
| A5 | Tenant owner un-hides the Tenant admin link and clicks it | `/alvoraa-admin` refuses: it checks `alvoraa_control_plane` itself |
| A6 | Caller sends a search string with SQL, `%`, `_` or HTML in it | Treated as text; wildcards escaped; results escaped when drawn |
| A7 | A tenant's logo URL holds a script | Escaped in the attribute, as slice 025 does |
| A8 | Someone who may create a Designation names one `<img src=x onerror=alert(1)>` | It appears as text in search, the rail and the profile menu; no element is created (SEC-10) |
| **A9** | **A manager resigns; HR sets his Employee to Left; his login stays enabled and his reports are not yet moved. That evening he searches for people and asks for his approvals** | Empty search, zero approvals, empty bell list (SEC-14) |
| **A10** | **A tenant System Manager or a support engineer opens the preview page on production** | They see unfinished screens with real data, under their own permissions. Accepted by decision 3 — **confirmation that this covers real data is still with the user** (R5) |

## Requirements

| ID | Requirement | How it is tested |
|---|---|---|
| **SEC-1** | `/hrms-employee-next` answers 200 only to System Manager, **403** to everyone else signed in, and redirects Guest to login. It sets `context.no_cache = 1` (OPS-12) and is not in the sitemap. The check is in the page's `get_context`, on the server | **Load the route over HTTP** as Guest, Employee, manager, company HR, store HR and System Manager, and check the status code. **Swap-commit test:** the route returns 404 and no tracked file names `hrms-employee-next` |
| **SEC-2** | The preview gate is not a data control. Every new whitelisted function is live on production from the first release that carries it, whatever page calls it. Each ships **in the same commit** as its Guest-refused test, its wrong-persona test and its scope test. The scope changes in SEC-3, SEC-4 and SEC-5 also change today's live portal the moment they are released, so they are tested against the current page as well | A **registry test** lists every whitelisted function in `frame_api.py` and `inbox_api.py` with its cases; a new whitelisted function with no entry fails the test. (`test_portal_call_paths` does not prove this: it checks a path exists and is whitelisted, not that it checks the caller) |
| **SEC-3** | `_pending_approvals_scope` limits HR to `access.permitted_employees()`, Active only, minus the caller, **plus the caller's own Active direct reports** — the union the helper has today, so a store HR person does not lose their own reports in another store. The count and the bell list keep sharing it | Two-store fixture: store HR sees their store; company-wide HR sees both; a store HR person with a report in another store still sees that report |
| **SEC-4** | People search uses one shared definition, not a copy: a new `access.permitted_employee_filters(user)` returns the filters, `permitted_employees()` uses it, and `_search_scope` uses it for HR. **Store HR finds their store plus anyone reporting to them** (decision 7). An employee with no branch is outside every store. System Manager is not narrowed | Two-store fixture plus a head-office employee with no branch: store HR does not find them, company-wide HR does. A store HR person finds their own report in another store |
| **SEC-5** | Every count part names the scope helper it reuses, and the count equals the list the Inbox row links to: |  |
| | · Leave to approve — `leave_approver` = the session user, `status = Open`, `docstatus = 0`, the same filter as today's list | count-matches-list test per part and per persona |
| | · Goal and KPI updates — `_pending_approvals_scope`, `approval_status` empty, NULL or `Pending` | fixtures cover all three pending states |
| | · Attendance corrections — for HR, counted **and listed** among `permitted_employees()`, minus the caller. `attendance_correction.to_review` gains the same filter (decision 5), so a store's HR person never sees a head-office correction | store HR: one correction in their store, one in another store, one from a head-office employee with no branch → count 1, list 1. Company-wide HR → 3 and 3 |
| | · Shift requests — `approver` = the session user, draft | |
| | · Policies to acknowledge — `hrms.alvoraa_policy_library.access.readable_policy_names()`, the same query the list uses; never a new rule written for the batch | |
| | · My own open requests — the caller's own **Active** Employee only | |
| | **Every fixture item is created through the endpoint a real user uses** (apply for leave through the portal, log a goal update through the portal), never inserted in its final state. **Real-data check once before the swap:** on the local PP Jewellers copy, as slice 030's store HR user, the counts and search are compared with that user's Employee list in the desk; the result goes in the implementation notes | |
| **SEC-6** | The new endpoints refuse Guest, take no doctype, field or method name from the caller, and are POST where they write. `frame_api.py` and `inbox_api.py` contain **no** `ignore_permissions`, and the bodies of `_pending_approvals_scope`, `_search_scope` and the new `permitted_employee_filters` gain none | A test that reads those files and counts `ignore_permissions`. **The repo-wide counter does not exist** (267 uses today); it is the security engineer's item (feature map B4) and this slice does not claim it — residual risk R4 |
| **SEC-7** | "Switch to the full desk" shows only when `get_switch_target` returns a target (admins → `/app`, HR → `/app/hr`, nobody else), and the label comes from the server | Test per role on `get_frame`'s payload |
| **SEC-8** | "Tenant admin" shows only when the caller is a System Manager **and** the site is the control plane (`alvoraa_control_plane`). `/alvoraa-admin`'s own check is unchanged | Test on both site types, setting `frappe.conf` in the test |
| **SEC-9** | **`set_my_language` is not built in Wave 1** (decision 4, M6). No frame code writes a `User` record. A language is *offered* only when it is enabled on the site **and** `alvoraa_portal` ships a translation for it; in Wave 1 that is English only, so the row is hidden everywhere. When the endpoint is built in a later wave it must be POST only, take no user argument, accept only an offered language, save through the document (so change history and date formats are kept), and carry the single declared `ignore_permissions` with its justification beside it — never `frappe.db.set_value` | A test that no frame module writes to `User`, and that the offered-language list is English only on a site with the Frappe default 17 enabled languages |
| **SEC-10** | Everything the frame puts on the page from data is escaped — in Jinja (`\| e`, as the rail's logo does) **and in the browser**. Frame include files never assign API data to `innerHTML`; they use `textContent` or one shared escape helper | A check script scans `templates/includes/ess/frame/` for `innerHTML` with API data. **DOM test:** a designation of `<img src=x onerror=alert(1)>` appears as text in a search result, the rail and the profile menu, and creates no element. `test_brand_logo_025` repointed |
| **SEC-11** | Page search offers only pages from the menu list, after the same visibility rules | Test per persona on the searchable page list |
| **SEC-12** | `get_frame` returns **only named keys**. The caller's own block holds `employee`, `employee_name`, `designation`, `department`, `image`, `company` — never `date_of_birth`, `gender`, `cell_number`, `date_of_joining`, `reports_to` or `branch`. Roles go out as the booleans the menu needs (`is_hr`, `is_manager`, `is_system_manager`, `is_control_plane`), not the whole role list. The cached context may decide what the menu shows; it never decides what data an endpoint returns — every data endpoint reads roles live. `get_portal_context` itself is not changed in this slice (follow-up: its other callers) | The payload's keys are exactly this set, per persona |
| **SEC-14** | The frame's endpoints, `_search_scope` and `_pending_approvals_scope` find the caller's Employee **with status Active only**. A caller whose record is not Active and who holds no HR role finds nobody and has nothing to approve; they may still see their own open requests. `_me()` is not changed globally (the org chart uses it widely) — the Active lookup goes inside the two helpers this slice already claims (decision 6). The wider fix across `goals_api` is **ALV-87** | A Left manager with an enabled login and unmoved reports: empty search, zero approvals, empty bell list |
| **SEC-15** | The new modules keep no module-level cache and no mutable global, because a worker can serve several sites. Any cache uses `frappe.cache()` (per site) or `frappe.local` (one request), keyed by user | A static check on `frame_api.py` and `inbox_api.py`: no `global`, no module-level dict, list or set changed at run time |
| **PRIV-1** | People search keeps decision Q-c: an employee or manager finds themselves and people below them; HR finds their permitted people (store HR: their store plus their own line); nobody finds anyone else | Tests per persona |
| **PRIV-2** | A search result returns **Active employees only** — never Left, Inactive or Suspended — and its keys are exactly `employee`, `name`, `title`, `department`, `image`. `employee` is a link key and is never displayed. No phone, email, employee number, branch or manager | Test on the payload keys, not the screen; one Left, one Inactive, one Suspended and one Active person all matching the term — only the Active one returns |
| **PRIV-3** | `%` and `_` in the search term are escaped before they reach `like`. A search needs at least two letters. The frame asks for 12 and the server returns at most 50, all from the caller's scope | Test `%%` and `a_b`; test the 12 and the 50 caps |
| **PRIV-4** | Counts and the Inbox page show **numbers only** — no names, reasons or document ids. The frame never calls `get_pending_approvals` on page load (it returns names, notes and evidence, and costs about 15,000 queries for HR on a 403-person tenant) | Test the payload shape; a test that no boot path calls `get_pending_approvals` |
| **PRIV-5** | Frame logs carry the endpoint, the user id, the outcome and the time — never a name, a search term or a per-person count. Refusals use `access.log_refusal`. **Search and every write send arguments in a POST body, never the query string**, because the web server logs URLs | Automated log-capture test on a refused call and on a search; a test that the frame's search call is a POST |
| **PRIV-6** | The theme is stored on the device only and holds no personal data | Review |
| **PRIV-7** | The frame widens no visibility: **a table** lists each thing the frame shows, per persona, and where that person can already see it today. The wider design search (manager and leadership) is not built | The test engineer checks the table; PRIV-1 and PRIV-2 tests |

## Dependency, not designed around

**The org chart shows every company and every store** to any manager with one report and
to every HR user (security finding F1). A Wave 1 search result opens that chart, so the
problem becomes one click from every page. **The user did not accept this: it is
`ALV-86`, Critical, to be fixed before DTC's go-live** (decision 8). Wave 1 does not work
around it and does not depend on it being fixed first; release readiness records its
state on the day of the swap.

## Residual risk

| # | Risk | State |
|---|---|---|
| R1 | The org chart shows every company and store (F1) | **Not accepted. ALV-86, Critical, before DTC go-live** (decision 8) |
| R2 | A leaver keeps goal-approval access outside the frame's two helpers (F2) | **ALV-87** (decision 6). Not accepted; scheduled |
| R3 | A successful over-read leaves no signal; nobody reads the security log | **With the user — no owner yet** |
| R4 | No repo-wide `ignore_permissions` counter in CI (267 uses) | **With the user — security engineer's item (feature map B4), not built** |
| R5 | The preview page is open to tenant System Managers on production for 2–3 weeks, showing unfinished screens with real data | Decision 3 covers opening it; **the user is confirming it covers real data** |
| R6 | Store HR whose Branch permission applies to only some record types is treated as company-wide (F5) | **With the user — no owner yet** |

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | *Closed:* 403 or 404 for the preview page → **403 and the login redirect** (security review §1.1) | — | — |
| 2 | R3, R4 and R6 need an owner and a date | Surbhi, with the security engineer | Nothing in the build; needed before the security review at the end |
| 3 | Confirmation that decision 3 covers a tenant System Manager seeing unfinished screens with **real data** | Surbhi | The first release that carries the preview page |
| 4 | Re-check of this revision | Security engineer | Ready |

## Assumptions

- `[ASSUMPTION]` `access.permitted_employees()` and `permitted_branches()` behave as their
  docstrings and slice 030's tests say.
- `[ASSUMPTION]` Frappe's `/me` shows only the caller's own record — to be checked once on
  the bench before step 2.
- `[ASSUMPTION]` `goals_api` defines `_is_hr` twice (`:17` and `:245`) and the second wins;
  SEC-3's edit sits between them. Whoever edits it must know which one runs.

## What changed in revision 2

| Review item | Change |
|---|---|
| M1 | New SEC-12: `get_frame` returns a fixed field list, no date of birth, gender or phone |
| M2 | SEC-1 and SEC-2 rewritten: route-level tests, `no_cache`, post-swap 404, endpoint registry test, endpoints safe from their first release |
| M3 | New SEC-14 and abuse case A9 (leaver); fix inside the two helpers, wider fix is ALV-87 |
| M4 | SEC-5's attendance part: `to_review` gains the same filter (decision 5) |
| M5 | SEC-5 rewritten as a table of parts with their scope helpers, a count-matches-list test, fixtures made the way users make them, and the PPJ real-data check |
| M6 | SEC-9: `set_my_language` is not built in Wave 1 (decision 4); "offered language" defined |
| M7 | SEC-6: the test is one that exists; the repo-wide counter is named as R4, not claimed |
| M8 | New SEC-15: no module-level state; blast radius added to the threat model |
| S1–S5 | SEC-10 covers the browser; PRIV-2 pins Active only and the payload keys; PRIV-3 escapes wildcards and states the caps; PRIV-4 names the bell rule; PRIV-5 becomes an automated test and pins POST |
| S6, S7 | SEC-4 uses one shared filter helper; SEC-3 states the union |
| S8, S9 | Threat model gains blast radius and "how we would find out"; abuse cases A9 and A10 added |
| S10 | Obligations carry their dates |
| Decisions 5, 6, 7, 8 | Corrections queue store-scoped; leaver fix in the two helpers; store HR search is store plus own line; the org chart is ALV-86, not accepted |

## Handoff note

To the security engineer: nothing was declined. The three items I would look at first are
SEC-4 (a new shared helper inside `access.py`, a file every app reads), SEC-5's
count-matches-list rule, and SEC-14's Active-only lookup, which changes behaviour for
today's live bell and org-chart search as soon as it is released — not at the swap.
Residual risks R3, R4 and R6 are with the user; I have not accepted any of them here.
