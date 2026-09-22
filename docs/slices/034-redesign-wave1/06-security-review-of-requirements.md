---
slice: 034-redesign-wave1
artifact: 06-security-review-of-requirements
author: hrms-security-privacy-engineer
date: 2026-09-22
status: review of a draft — no code exists yet
reviews: 01c-security-privacy-requirements.md (draft, 2026-09-22, written by the builder)
inputs: [01c-security-privacy-requirements.md, 00-impact-analysis.md, 02-functional-spec.md, 07-devops-inputs.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, ../030-store-hr-scoping/00-impact-and-fix.md, .claude/context/security-compliance-baseline.md, .claude/context/compliance-feature-map.md, docs/legal/2026-09-18-retention-and-driver-tracking-proposal.md, the code at origin/dev 1c4e84c, Frappe v16.33.1 source on the local bench (read only)]
---

# Security review of the Wave 1 requirements (01c)

## Verdict: Pass with changes

The draft is honest and mostly right. Its instincts are good: numbers only in counts,
no phone or email in search, scope enforced on the server, and the wider design search
not built. **But it cannot be called Ready yet.** Eight changes must be made to `01c`
(and traced in `02`) first. None of them needs a new decision from counsel.

## Bad news first

1. **The start-up call would send each person's own date of birth, gender and phone
   number to every page.** `get_frame` is planned to reuse `get_portal_context`. That
   function returns the whole Employee row from `_get_employee`
   (`alvoraa_portal/alvoraa_portal/hr_api.py:87-95`, returned at `:134`), including
   `date_of_birth`, `gender`, `cell_number`, `date_of_joining`, `reports_to` and
   `branch`. The `01c` data inventory says the frame holds "name, job title, photo".
   The code says otherwise. It is the person's own data, so nobody else sees it. But
   the portal is the landing page for every tenant, so this payload goes into every
   page, every error report and every support screenshot. **Change M1.**
2. **The "System Manager only" rule protects the preview page, not the new endpoints.**
   `get_frame`, `get_nav_counts` and `set_my_language`, plus the two changed scope
   helpers, work for every logged-in user on production from the first release that
   carries them. That can happen weeks before the swap. So each endpoint must be
   complete and fully tested in the commit that adds it, not "by the swap". **M2.**
3. **A leaver can still log in, and two of the helpers this slice edits do not check
   whether the caller still works here.** ERPNext does not disable the User when an
   Employee is set to Left (checked: `erpnext/setup/doctype/employee/employee.py` only
   disables the linked Sales Person). `_me()` (`hrms/hrms/alvoraa_org_structure/api.py:783`)
   and `_employee_id()` (`alvoraa_portal/alvoraa_portal/goals_api.py:20-24`) find the
   Employee whatever its status. `01c` has no departing-employee abuse case. **M3.**
4. **The attendance-corrections queue that the new Inbox row links to is not limited
   to the store.** `attendance_correction.to_review` (`attendance_correction.py:722-740`)
   reads under Frappe's own User Permissions. Those let an empty branch through
   (`hrms/hrms/alvoraa_hr_core/access.py:222-228`, DEF-6). So a store's HR person sees
   head-office corrections. If the count uses `permitted_employees()`, as SEC-5 says,
   the count and the list will not match. **M4.**
5. **SEC-6 relies on a CI check that does not exist.** No workflow and no script counts
   `ignore_permissions` (I searched `.github/` and `scripts/`). There are 267 uses
   outside tests today. That gate is mine to build (feature map B4). It is not built,
   and this slice must not claim it. **M7.**
6. **SEC-6 and SEC-9 cannot both hold as written.** In Frappe v16.33.1 only System
   Manager may write a `User` record (`frappe/core/doctype/user/user.json`
   permissions), and Frappe has no endpoint for a user to set their own language. So
   `set_my_language` needs either one narrow, declared `ignore_permissions`, or
   `frappe.db.set_value`. The second is worse: it skips the change history (`User`
   has `track_changes: 1`) and the date-format defaults set in `on_update`
   (`user.py:339-348`). And by decision 14 no tenant can reach the language row in
   Wave 1 anyway. **M6, and decision D1 for you.**

---

## 1. The six checks you asked for

### 1.1 The preview page's exposure

| Question | Answer |
|---|---|
| Is the System Manager check on the server, on the page? | **Yes, as specified.** SEC-1 puts it in the page's `get_context`, the way `/alvoraa-admin` does (`www/alvoraa_admin.py`). Good. |
| Is it on every call the page makes? | **No, by design, and `01c` should say so plainly.** The preview uses the same panel files as the live page, so it calls every existing endpoint. Each of those keeps its own checks. The three new endpoints are open to every logged-in user, whatever page they came from. That is acceptable **only if** each one is safe on production from its first commit (M2). |
| Does it disappear with the page? | **The page check does. The endpoints do not, and must not.** They are permanent. The swap commit needs a test showing the route is gone and no file still names it (M2). |
| Missing from SEC-1 | `no_cache = 1` on the page (the live page sets it, `www/hrms_employee.py`), so Frappe's page cache never keeps a copy. `sitemap = 0` / no-index. And the test must load the **route** as each role, not just call `get_context`. The 19 Sep lesson applies: a unit test of a function can pass while the route behaves differently. |
| Open question 1: a 404 instead of "not permitted"? | **Keep "not permitted" (403) and the login redirect.** The route name is in the code and hides nothing. The page shows no data. A 404 would only make support harder. Not worth the code. |

### 1.2 Can any frame call widen what someone sees?

**The new frame calls do not widen anything, if the changes below are made.** Here is
each one:

| Call | Today | What the draft does | Gap |
|---|---|---|---|
| Start-up (`get_frame`) | Three calls; same data | Combines them | **Sends own DOB, gender, phone (M1).** Also passes the full `roles` list and the 1-hour cached context. The cache is fine for drawing the menu. It must never decide what data comes back (M1). |
| Inbox count (`get_nav_counts`) | Goals-only bell count, company-scoped for HR | Six parts; HR parts store-scoped | **Every part needs a named scope helper and a count-matches-list test (M5).** Attendance part: see M4. Leaver: see M3. |
| People search | Company-scoped for HR; line-downwards for others | Store-scoped for store HR | Good. Pin the Active-only rule (PRIV-2). Decide what happens to store HR's own reports outside the store (D5). |
| Profile menu | Desk link and admin link from the server | Same | Fine. Both links are conveniences. The real gates are the desk's own access rules and `/alvoraa-admin`'s control-plane check. Neither changes. |
| **Across companies** | — | `permitted_companies()` everywhere HR is scoped | Fine inside the frame. **The org chart that a search result opens is not company-scoped** (finding F1). |
| **Across stores** | Bell and search leaked across stores | Fixed | Fine, apart from the corrections queue (M4) and the org chart (F1). |
| **User with no branch** | — | — | An **employee** with no branch is outside every store. The Frappe filter `branch in (...)` never matches an empty branch, so this holds. An **HR user** with no Branch permission is company-wide, as intended. One edge fails open: a store HR person whose Branch permission applies only to some record types is treated as company-wide (F5). |
| **Across tenants** | Separate sites | New modules | Not mentioned in `01c`. The blast radius here is every tenant: a module-level cache in a worker that serves several sites would leak between them. **M8.** |

### 1.3 What search may return, and whether names leak anything

- **Search returns Active employees only** (`api.py:568`, `"status": "Active"`). Left,
  Inactive and Suspended people never appear. Good, but `01c` never says so, so a later
  change could drop it without a test failing. Pin it (PRIV-2 change below).
- **Name, title, department and photo within the caller's own line downwards** reveal
  nothing the caller cannot already see on their team screen or the org chart.
- **Sensitive departments or people.** The product has no way to mark a department or
  a person as "do not list" (feature map A1, sensitivity classes, is not built). In
  Wave 1 this does not matter, because search stays inside the caller's line. It
  **will** matter for Wave 4's directory. Recorded as worry W3, not a finding.
- **The real exposure is the org chart, not search.** By default, anyone with one
  direct report, and every HR user, can browse the whole chart across all companies
  (F1). A Wave 1 search result opens that chart. So store HR's store-only search lands
  in a company-wide chart. This is not caused by Wave 1, but Wave 1 makes it one click
  from every page. **You need to accept it by name and date, or schedule it (D3).**
- **Wildcards.** The search term goes straight into `like %q%` (`api.py:568`). Typing
  `%%` lists up to 50 people in scope. That stays inside the scope, so it is not a leak.
  But PRIV-3's claim "nobody pages through a staff list" is not true as written (F6).

### 1.4 The language write, and the desk and admin links

- **Language:** see bad news 6 and M6. If it is built, it must be POST only, take no
  user argument, accept only an enabled Language, change only `User.language`, and save
  through the document so the change history is kept.
- **Desk link:** `module_access.get_switch_target` (`module_access.py:1099-1115`)
  returns `/app` for admins, `/app/hr` for HR, nothing for others. SEC-7 is right. The
  desk's own access rules are the control. Note, though, that inside the desk store HR
  sees head-office records with an empty branch (DEF-6). That is an existing issue,
  unchanged here.
- **Tenant admin link:** SEC-8 is right. `/alvoraa-admin` refuses first on
  `alvoraa_control_plane`, then on role (`www/alvoraa_admin.py`). A tenant owner who
  un-hides the link reaches a "does not exist" page.

### 1.5 Is each SEC and PRIV item testable, and traced to 02?

See §3. In short: **eight items are testable and traced well, seven are weakly traced,
and three are not testable as written** (SEC-6's CI counter, PRIV-5 "tested in the
security review", PRIV-7 "review against today's panels").

### 1.6 What is missing

Items M1, M2, M3, M4, M5 and M8 in §2, plus two threat-model lines (blast radius and
"how would we find out"), dates on the obligations, and the departing-employee and
support-engineer abuse cases.

---

## 2. Changes I require, ranked

### Must change before the spec is Ready

**M1 — `get_frame` returns a fixed list of fields, not a copy of `get_portal_context`.**
New requirement SEC-12:

> `get_frame` returns only named keys. The caller's own block holds `employee` (the
> record name), `employee_name`, `designation`, `department`, `image` and `company`.
> It never holds `date_of_birth`, `gender`, `cell_number`, `date_of_joining`,
> `reports_to` or `branch`. Roles go out as the booleans the menu needs (`is_hr`,
> `is_manager`, `is_system_manager`, `is_control_plane`), not the full role list.
> The cached context may decide what the menu shows. It never decides what data an
> endpoint returns: every data endpoint reads roles live.
> **Test:** the payload's keys are exactly this set, for each persona.

`get_portal_context` itself need not change in this slice. Its other callers may rely
on it. Record it as a follow-up.

**M2 — The preview gate is not a data control. Say so, and test the endpoints as
production code from day one.** Rewrite SEC-1 and SEC-2:

> **SEC-1.** `/hrms-employee-next` answers 200 only to System Manager, 403 to everyone
> else signed in, and redirects Guest to login. It sets `no_cache = 1` and is not in the
> sitemap. **Test:** load the route over HTTP as Guest, Employee, Manager, HR, store HR
> and System Manager, and check the status code. **Swap-commit test:** the route
> returns 404, and no tracked file contains `hrms-employee-next`.
>
> **SEC-2.** Every new whitelisted function is live on production from the first
> release that carries it, whatever page calls it. Each one therefore ships **in the
> same commit** as its Guest-refused test, its wrong-persona test and its scope test.
> A registry test lists every whitelisted function in `frame_api.py` and
> `inbox_api.py` with its cases. **A new whitelisted function with no entry fails the
> test.** The scope changes in SEC-3 and SEC-4 also change today's live portal (the
> org-chart search and the bell) as soon as they are released. They are tested
> against the current page as well.

`test_portal_call_paths` does not prove this. It checks that a called path exists and
is whitelisted, not that it checks the caller (its own docstring says so).

**M3 — The caller must still work here.** New requirement SEC-14, and a new abuse case
A9:

> A9. *A manager resigns. HR sets his Employee to Left on his last day. His login stays
> enabled, because ERPNext does not disable it. His reports are not yet moved. That
> evening he calls `search_people("a")` and `get_pending_approvals`.* Today he gets his
> former team's names, and their pending goal updates with notes and evidence files.
>
> **SEC-14.** The frame's endpoints, `_search_scope` and `_pending_approvals_scope`
> find the caller's Employee **with status Active only**. A caller whose record is not
> Active, and who holds no HR role, finds no people and has no approvals to count.
> They may still see a count of their own open requests. **Test:** a Left manager
> with an enabled login and unmoved reports gets an empty search, zero approvals, and
> an empty bell list.

Do not change `_me()` globally: the org chart uses it in many places. Use an Active
lookup inside the two helpers this slice already claims. The rest of `goals_api`
(`_employee_id`, `_require_employee`) is a residual risk (R2) unless you widen the fix.

**M4 — The attendance-corrections count and the queue it links to use one scope.**
Rewrite the attendance part of SEC-5:

> For HR, attendance corrections are counted **and listed** among
> `permitted_employees()`, minus the caller's own. `attendance_correction.to_review`
> gains the same filter, so a store's HR person never sees a head-office correction.
> **Test:** store HR with a correction from their store, one from another store and
> one from a head-office employee with no branch. Count = 1 and list = 1. Company-wide
> HR: 3 and 3.

This is one filter in `to_review`. It is outside the files `00` claims, so it needs
your agreement (D2).

**M5 — Every count part names its scope helper and matches the screen it links to.**
This is the lesson of 19 Sep (a rule that never saw real data) and of slice 030 (readers
that skipped the helper). Rewrite SEC-5:

> | Part | Scope, reused, never re-written |
> |---|---|
> | Leave to approve | `leave_approver = session user`, `status = Open`, `docstatus = 0` — the same filter as today's list (`hr_api.py:245`) |
> | Goal and KPI updates | `_pending_approvals_scope`, with `approval_status` empty, NULL or `Pending`, as the count does today |
> | Attendance corrections | M4 |
> | Shift requests | `approver = session user`, draft |
> | Policies to acknowledge | `hrms.alvoraa_policy_library.access.readable_policy_names()` (`access.py:163`), the same query the list uses. Never a new rule written for the batch |
> | My own open requests | the caller's own **Active** Employee only |
>
> **Count-matches-list test, per part and per persona:** the number equals the rows on
> the screen that the Inbox row links to. Every fixture item is created **through the
> endpoint a real user uses** (apply for leave through the portal, log a goal update
> through the portal), not inserted already in its final state. Goal-update fixtures
> cover all three "pending" states: empty, NULL and `Pending`.
> **Real-data check, once, before the swap:** on the local PPJ copy, as the store HR
> user from slice 030, the counts and search are compared with that user's Employee
> list in the desk (72 people in slice 030). The result goes in the implementation notes.

A count wider than its list is a leak: it reveals that items exist which the person may
not see. A count narrower than its list misleads. The test catches both.

**M6 — Resolve the language write.** Either:

- **(a) Recommended: do not ship `set_my_language` in Wave 1.** By decision 14 no tenant
  can reach the row, so the endpoint would be attack surface with no use. Ship it in the
  wave that enables a second language, under the rule in (b).
- **(b) Build it now under this rule (rewrite SEC-9):**

> `set_my_language(language)` is `@frappe.whitelist(methods=["POST"])`. It takes no
> user argument and reads `frappe.session.user`. It refuses Guest. It accepts only a
> Language that exists and is enabled. It loads the caller's own `User`, changes only
> `language`, and saves through the document, so the change history and Frappe's date
> formats for that language are kept. Because ordinary users have no write right on
> `User`, the save sets `doc.flags.ignore_permissions = True`. That is **the one
> declared exception** to SEC-6, with this justification written next to it. Never
> `frappe.db.set_value`.
> **Tests:** disabled, unknown and valid languages; a `user` argument is ignored; a GET
> is refused; after the save, every field of the `User` record except `language` and
> `modified` is unchanged; a Version row exists.

**M7 — SEC-6's test must be one that exists.** Rewrite:

> New endpoints refuse Guest, take no doctype, field or method name from the caller,
> and are POST where they write. `frame_api.py` and `inbox_api.py` contain no
> `ignore_permissions` except the one M6(b) names, and the bodies of
> `_pending_approvals_scope` and `_search_scope` gain none.
> **Test:** a test that reads those files and counts `ignore_permissions`.

The repo-wide counter that can only go down (feature map B4) is my item. It is not
built. I am recording it as a gap rather than hiding it in this slice.

**M8 — Nothing leaks between tenants.** New requirement SEC-15, and a blast-radius line
in the threat model:

> The new modules keep no module-level cache or mutable global. A worker process can
> serve more than one site, so such a cache could hand one tenant's data to another.
> Any cache uses `frappe.cache()`, which is per site, or `frappe.local`, which lasts one
> request, and is keyed by user.
> **Test:** a static check on `frame_api.py` and `inbox_api.py` (no `global`, no
> module-level dict, list or set that is changed at run time), plus a code-review item.

### Should change (traced in 02, before Ready)

**S1 — SEC-10 covers the browser too, not only Jinja.** Search results, names and
titles are drawn by JavaScript from API data, so Jinja's `| e` does not protect them.

> The frame puts API text on the page with `textContent` or one shared escape helper.
> Frame include files never assign API data to `innerHTML`. A check script scans
> `templates/includes/ess/frame/` for it. **DOM test:** a designation named
> `<img src=x onerror=alert(1)>` appears in a search result and in the profile menu,
> and no element is created.

Attacker: anyone who may create a Designation or Department. Target: every colleague
who searches, including a System Manager, whose session could then be used.

**S2 — PRIV-2 pins Active only.** Add: "Only Active employees. Left, Inactive and
Suspended people are never returned. **Test:** one of each, all matching the search
term, and only the Active one comes back."

**S3 — PRIV-3 escapes wildcards and says what is true.** Escape `%` and `_` in the
search term before it goes into `like`. Replace "so nobody pages through a staff list"
with "search returns at most 50 people, all from the caller's own scope". Test the cap
at 50 and the frame's request for 12.

**S4 — PRIV-4 says what the bell shows.** "In Wave 1, the bell and the Inbox page show
numbers only. The frame never calls `get_pending_approvals` on page load." That
function returns names, notes and evidence files. Its own docstring says it costs about
15,000 queries for HR on a 403-person tenant (`goals_api.py:1264-1267`).

**S5 — PRIV-5 is an automated test, and the search term never goes in a URL.** Add:
"Search and every write send their arguments in a POST body, never the query string."
The web server logs URLs. `deploy/nginx.conf` turns the access log off only for health
checks. Today's search already uses POST (`gpSend`, page line 9969). Pin it with a
test. In `02` §10, replace "tested in the security review" with the log-capture test.

**S6 — SEC-4: reuse the definition, do not copy it.** Add a small shared function in
`access.py`, for example `permitted_employee_filters(user)`. `permitted_employees()`
uses it, and so does `_search_scope`. Then search filters in SQL without a list of
2,000 names, and the two cannot drift apart. System Manager is not narrowed, the same
as `permitted_employees`. Test: a head-office employee with no branch is not found by
store HR, and is found by company-wide HR.

**S7 — SEC-3 states the union.** HR scope is (Active people in `permitted_employees()`,
minus yourself) **plus** your own Active direct reports, as the helper does today
(`goals_api.py:1162-1184`). State it, so the fix does not silently drop a store HR
person's own reports who sit in another store.

**S8 — Threat model: add the two missing lines.**

- *Blast radius:* one wrong line reaches every person on every tenant. The frame is the
  landing page everywhere, and the swap is one commit. A cross-tenant leak is the top
  of the scale (M8).
- *How would we find out:* refusals are logged through `access.log_refusal`. **A
  successful over-read, like store HR reading another store, leaves no signal at all.**
  Nobody reads the security log, and nothing alerts on it. Say that plainly. The tests
  are the only defence.

**S9 — Abuse cases: add A9 (M3) and A10.** A10: *a support engineer or tenant System
Manager opens the preview on production.* They see unfinished screens with real data,
under their own permissions. Acceptable by decision 3. Say it is accepted.

**S10 — Obligations carry dates.** DPDP minimisation and safeguards, and OWASP ASVS 5.0
L2: from the baseline, verified 24 Aug 2026 (29 days old, not stale). CERT-In is
relevant only to what goes into logs, not to where they are kept. DPDP Data Fiduciary
duties are phased to about May 2027 (baseline §2, ⚠ counsel to confirm). We build to
them now anyway.

### Minor

- `goals_api.py` defines `_is_hr` twice (`:17` and `:245`). The second wins at import.
  Both sets are the same today (HR Manager, HR User, System Manager), so nothing is
  wrong now. But SEC-3's edit sits between them. Whoever edits it should know which
  one runs.
- PRIV-6 and the theme choice are fine as "review" items.
- `01c`'s assumption that `/me` shows only the caller's own record: fine to keep, but
  check it once on the bench before step 2.

---

## 3. Testability and traceability

| ID | Testable as written? | Traced in 02 | Change |
|---|---|---|---|
| SEC-1 | Partly: needs a route-level test and a post-swap test | AC-40 | M2 |
| SEC-2 | **No**: the named test checks paths exist, not that callers are checked | AC-7, AC-8, AC-40: **none of them tests a permission** | M2. Add an AC for the registry test |
| SEC-3 | Yes | AC-21 | S7; M5 fixtures |
| SEC-4 | Yes | AC-26 covers employees only | Add store-HR and no-branch cases to AC-26 (S6) |
| SEC-5 | Partly: parts not named | AC-20, 21, 22: no policy or attendance scoping | M4, M5. Add a count-matches-list AC |
| SEC-6 | **No**: the CI counter does not exist | AC-8, AC-18: **neither tests this** | M7. Add an AC |
| SEC-7 | Yes | AC-17 | — |
| SEC-8 | Yes (set `frappe.conf` in the test) | AC-17 | — |
| SEC-9 | Yes, but conflicts with SEC-6 | AC-18 says nothing about refusals | M6 |
| SEC-10 | Server side only | AC-42 is about a broken image, **not escaping** | S1. Add an AC |
| SEC-11 | Yes | AC-25 | — |
| PRIV-1 | Yes | AC-26 | — |
| PRIV-2 | Yes | AC-27 says "shows", not "returns" | S2. Test the API keys, not the screen |
| PRIV-3 | Yes, but the claim is untrue | AC-28 lacks the caps | S3 |
| PRIV-4 | Yes | AC-23 | S4 |
| PRIV-5 | **No**: "tested in the security review" | No AC | S5. An automated log-capture test |
| PRIV-6 | Review | AC-19 | — |
| PRIV-7 | **No**: "review against today's panels" | AC-26, AC-27 | Make it a table: each item the frame shows, per persona, and where the person can see it today. The test engineer checks the table |
| New SEC-12, 14, 15 | Yes | — | Add ACs |

---

## 4. Findings in existing code, found during this review

These are not caused by Wave 1. They matter because Wave 1 puts them one click from
every page.

| # | Rank | Where | Scenario |
|---|---|---|---|
| F1 | **Major** | `hrms/hrms/alvoraa_org_structure/api.py:56-72` (`get_children`), `:612-652` (`reach`); defaults in `settings.py:55` and `:59` | `alvoraa_org_managers_see_all` is on by default, so **anyone with one direct report** gets unlimited reach, and so does every HR user. `get_children(company="All Companies")` has no `permitted_companies` check. *A store manager in company A on a group tenant calls `get_children(company="All Companies")` and walks company B's whole tree: name, title, department, branch and photo of every Active person.* Store HR can do the same across all stores. A Wave 1 search result opens this chart. |
| F2 | **Major** | `api.py:783` (`_me`), `goals_api.py:20-32`; ERPNext `employee.py` does not disable the User on Left | *A departing manager with an enabled login gets his former team's pending goal updates, with notes and evidence files, from `get_pending_approvals`.* Fixed for the frame by M3. The rest of `goals_api` stays open (R2). The wider fix is feature map B1 (removing access on exit), which is not built. |
| F3 | **Major** | `alvoraa_portal/alvoraa_portal/attendance_correction.py:722-740` | *Store HR opens the corrections queue and sees a head-office employee's correction, with the reason, because a record with an empty branch passes a Branch permission (DEF-6, `access.py:222-228`).* Fixed by M4 if you agree (D2). |
| F4 | Minor | `goals_api.py:17` and `:245` | Two `_is_hr` definitions; the second wins. No wrong result today. |
| F5 | Minor | `access.py:233` | `permitted_branches` counts only Branch permissions that apply to all record types or to Employee. *A store HR person given a Branch permission that applies only to, say, Salary Slip is treated as company-wide in search, counts and reviews.* It fails open. Check how store HR is set up on each live tenant. |
| F6 | Minor | `api.py:568` | `like %q%` with no escaping of `%` and `_`. Stays inside the caller's scope. S3 fixes it. |

## 5. Worries (not findings: I could not write the full scenario)

- **W1.** Employee photos. If a tenant's photos are public files (`/files/...`), anyone
  with the link can load them without logging in. I could not check tenant data.
- **W2.** If search fails with a server error, Frappe's Error Log may record the
  request's arguments, which include the search term (a name). Check on the bench by
  forcing an error, before PRIV-5's test is written.
- **W3.** There is no way to mark a person or department as "do not list". It is not
  needed for Wave 1's line-only search. It will be needed before Wave 4's directory.
- **W4.** I do not know whether `dtc.alvoraa.co` or `aahr.alvoraa.co` use Branch
  permissions at all. If they do not, SEC-3 and SEC-4 never run on production data.
  That is why M5 asks for the check on the PPJ copy.
- **W5.** Leave whose `leave_approver` field is empty can still be approved by the
  department's approver (`hr_api.py:570-581`). But it is in neither today's list nor
  the planned count. This is a correctness gap of the 19 Sep kind, not a leak. M5's
  "create it the way a user does" test will show whether real applications have the
  field filled.

## 6. Counsel policies

The frame counts performance items (goal and KPI updates) but stores nothing, decides
nothing and changes no retention. Counsel's retention periods (the 18 Sep paper) and
the rules on automated decisions are **not engaged** by Wave 1. Search returning Active
people only fits the rule that a leaver's performance records are not surfaced for
ordinary use. **No question for counsel blocks this wave.** I am not a lawyer. This is
a reading of what the frame does, set against the policies as written.

## 7. What I could not check

- Production. I did not look at it, by rule. So I cannot say how store HR is set up on
  the live tenants (F5, W4), or whether photos are public (W1).
- Frappe's Error Log contents on a failed search (W2). It needs one forced error on the
  local bench.
- How the Frappe v16 website renderer caches a page that raises "not permitted". The
  route-level test in M2 settles it.

## 8. Decisions for you

| # | Decision | My recommendation |
|---|---|---|
| D1 | Language setting: leave `set_my_language` out of Wave 1, or build it now with one declared `ignore_permissions`? | **Leave it out.** Decision 14 already hides the row. Add it with the first second language |
| D2 | Store-scope the attendance-corrections queue (`to_review`) in this slice? It is outside the files `00` claims | **Yes.** One filter, and the Inbox row links straight to it |
| D3 | The org chart lets managers and HR browse every company and every store (F1). Accept it for Wave 1, by name and date, and schedule a fix? Or fix it before the swap? | **Accept for Wave 1 with your name and a date, and schedule a small slice before Wave 4's directory.** HR reach should follow `permitted_employees`; managers should stay in their own company |
| D4 | The leaver gap (F2): fix only in the two helpers this slice touches (M3), or across `goals_api`? | **The two helpers now** (in scope, small). The rest of `goals_api` goes to a follow-up |
| D5 | Store HR search: store only, or store **plus** their own line below them (matching the approvals scope)? | **Store plus own line.** It is no wider than today, and it lets them find their own reports |

## 9. Residual risk

None of these is accepted yet. Each needs a name and a date. **An accepted risk with a
name and a date is governance. An unnamed one is an accident waiting for an owner.**

| # | Risk | Why it remains | Accepted by | Date |
|---|---|---|---|---|
| R1 | The org chart shows every company and every store to managers and HR (F1) | Outside Wave 1's frame | — | — |
| R2 | A leaver with an enabled login keeps goal-approval access outside the frame's helpers (F2) | No removal of access on exit (feature map B1) | — | — |
| R3 | A successful over-read leaves no signal; nobody reads the security log | No alerting built | — | — |
| R4 | No repo-wide `ignore_permissions` counter in CI (267 uses) | Feature map B4, owned by me, not built | — | — |
| R5 | The preview page is open to tenant System Managers on production for 2–3 weeks | Decision 3 | Surbhi (decision 3) | 2026-09-22 — please confirm this covers seeing unfinished screens with real data |
| R6 | Store HR whose Branch permission applies only to some record types is treated as company-wide (F5) | Definition from slice 030 | — | — |

## Handoff

- **To the engineer:** make M1–M8 in `01c`, and S1–S10 where you agree. Where you
  disagree, say so in `01c`, and Surbhi decides.
- **To the business analyst:** add the ACs in §3 and fix the traceability rows for
  SEC-2, SEC-6, SEC-9, SEC-10, PRIV-5 and PRIV-7.
- **To the test engineer:** the three structural tests: the endpoint registry (M2),
  count-matches-list with items made the way users make them (M5), and the static check
  for no module-level state (M8). They are the tests that stop the next slice
  repeating the 030 lesson.
- **To me, at review (`06-security-review.md`):** verify each SEC and PRIV item against
  the diff, and run the PPJ-copy check from M5 myself.
