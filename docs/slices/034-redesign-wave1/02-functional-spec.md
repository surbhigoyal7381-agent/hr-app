---
slice: 034-redesign-wave1
artifact: 02-functional-spec
author: hrms-fullstack-engineer, revised after the analyst, security and DevOps reviews
date: 2026-09-22
revision: 2 (ALV-84 — B1–B4, M1–M8 and the minors applied; security M1–M8 and S1–S10 traced; DevOps §4 carried in)
status: draft, revised — for the business analyst to re-review the changed rows
inputs: [02b-ba-review.md, 06-security-review-of-requirements.md, 07-devops-inputs.md §4 and §3b, 01c-security-privacy-requirements.md (revision 2), 00-impact-analysis.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, ../009-ess-portal-redesign/01b-ux-design.md, ../009-ess-portal-redesign/appendix-a-frame.md, prototype-v2.html]
brief: there is no `01` for slice 034. The approved brief is `../009-ess-portal-redesign/00-assessment-and-plan.md` (Wave 1) plus the decisions in `00f-decisions-2026-09-22.md`.
---

# Wave 1 frame — functional spec

**Revision 2.** Every blocker and major from the analyst review is applied, every security
change is traced to a check, and the DevOps measurements are named. What changed is
listed in §16.

**Prototype:** `C:/Surbhi-Git/hrlocal-data/prototypes/009-ess-portal-redesign/prototype-v2.html`.
Screens used below: **rail**, **top bar**, **bottom bar**, **search sheet**, **profile
sheet**, **Inbox**.

---

## 1. Gap analysis, checked in the source

| Need | What exists (file checked) | Decision |
|---|---|---|
| Log out, My account | Frappe's website bar; `/me` | **Configure:** remove the bar, link log out and `/me` from the profile menu |
| Language per user | `User.language`; only System Manager may write `User` (v16.33.1) | **Drop from Wave 1** (decision 4) |
| Translations in the page | Frappe `__()`; `frappe._messages` is empty on website pages (appendix A §E) | **Extend:** wrap frame strings; English only |
| Role and plan flags | `hr_api.get_portal_context:99`, `get_available_features:1213`, `subscription.FEATURES:58` | **Reuse**, behind one call, with a fixed field list (SEC-12) |
| Desk switch target | `module_access.get_switch_target:1099` | **Reuse** |
| Scope helpers | `access.permitted_employees:237`, `permitted_branches:217` | **Extend:** one shared filter helper (SEC-4) |
| People search | `alvoraa_org_structure.api.search_people:559`, `_search_scope:577` | **Extend:** store narrowing, Active-only caller, wildcards escaped |
| Approvals scope | `goals_api._pending_approvals_scope:1162` | **Extend:** `permitted_employees` + own reports |
| Corrections queue | `attendance_correction.to_review:722` | **Extend:** same scope as the count (decision 5) |
| Policy acknowledgements | `alvoraa_policy_library.access.readable_policy_names:163` | **Reuse** |
| Counts in one place | nothing | **Build:** `inbox_api` |
| Menu, bottom bar, routes, sheet, states | hand-written sidebar `hrms-employee.html:2345-2440` | **Build** in the frame includes |
| Pay pages | `panel-finances:2781` holds Salary Slips, Expenses, Leave Encashment; `expenses` is a **required** feature on every plan (`subscription.py:83-90`) | **Extend:** hide the salary parts without payroll, keep the rest (decision 1) |
| Directory, person sheet, Inbox list, feedback | — | **Out of Wave 1** (§12) |

No new DocType, no custom field, no patch, no migration.

---

## 2. Persona resolution — which flags produce which bar (decision 2)

Two flags decide everything. Both come from `get_frame`:

- **`has_reports`** — **someone is recorded as reporting to this person**: at least one
  Active Employee with `reports_to` = this person's Active Employee record. This is *not*
  today's `is_manager`, which is also true for any HR user when anybody in the tenant has
  no manager (the stand-in rule, `hr_api.py:118-124`).
- **`is_hr`** — HR Manager, HR User, System Manager or Administrator, as
  `get_portal_context` sets it today. A CXO is a System Manager, so a CXO is HR here.

| # | Rule (first match wins) | Team group | Bottom bar |
|---|---|---|---|
| 1 | `is_hr` **and** `has_reports` | Yes | Home · Inbox · Company · **Team** |
| 2 | `is_hr` **and not** `has_reports` | No | Home · Inbox · Company · **Time** |
| 3 | `has_reports`, not HR | Yes | Home · **Team** · Inbox · Time |
| 4 | Employee, tenant has `plan_payroll` | No | Home · Time · **Pay** · Goals |
| 5 | Employee, no `plan_payroll` | No | Home · Time · **Inbox** · Goals |
| 6 | No Employee record (platform operator) | No | Home · Inbox · Company (fewer buttons if fewer are allowed) |

**Consequence, stated on purpose:** an HR user with no direct reports loses the Team
panel they see today. Today's stand-in rule shows them the people at the top of the
company — for store HR that is head office, outside their store. Removing it is
intended (decision 2, and it closes the leak the analyst found in §4).

**The Company button** opens the first of these the person may open: HR analytics →
Reviews (HR) → Policies → People → Org settings. The prototype opens HR analytics
(`bnavItems`, prototype line 866).

**Fallback order when a bar button is not allowed** (B4): Home → Inbox → Time → Goals →
Pay → Team → Company, skipping anything already in the bar and anything not allowed.
When fewer than four are allowed, the bar has fewer buttons. **More is always last.**

---

## 3. Permission matrix

| | Employee | Manager | HR company-wide | Store HR | HR/owner with reports | Tenant System Manager | Control-plane operator | No Employee record |
|---|---|---|---|---|---|---|---|---|
| Me (Home, Inbox) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Home and Inbox show, with the "no employee record" state on Home |
| Time | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | hidden |
| Growth | ✓ where `goals` (app installed **and** plan) | same | same | same | same | same | same | hidden |
| Pay group | ✓ (Expenses always — a required feature; Request advance where `advance_request`; Leave encashment where `leave_encashment`) | same | same | same | same | same | same | hidden |
| Pay › My pay (salary slips), payslip search result | ✓ where `plan_payroll` | same | same | same | same | same | same | hidden |
| Team | — | ✓ | only with direct reports | only with direct reports | ✓ | only with direct reports | only with direct reports | — |
| Company › People | ✓ where `plan_org_structure` | same | same | same | same | same | same | ✓ where the plan allows |
| Company › HR analytics, Data to review | — | — | ✓ where `plan_analytics` is not `false` | same | same | ✓ (a System Manager is `is_hr`) | ✓ | ✓ |
| Company › Reviews (HR) | — | — | ✓ where `goals` | same | same | ✓ | ✓ | ✓ |
| Company › Policies | ✓ where `plan_policy_library` | same | same | same | same | same | same | ✓ |
| Company › Org settings | — | — | ✓ read and save | ✓ **read only** — Save hidden (decision 3) | ✓ | ✓ | ✓ | ✓ read only |
| Search finds | self and below | self and below | permitted companies | **own store plus own line** | permitted companies | everyone | everyone | nobody |
| Switch to desk | — | — | `/app/hr` | `/app/hr` | `/app` or `/app/hr` | `/app` | `/app` | per role |
| Tenant admin | — | — | — | — | — | **—** | ✓ | only on the control plane |
| Preview page | 403 | 403 | 403 | 403 | 403 unless System Manager | ✓ | ✓ | ✓ if System Manager |

**Missing plan keys.** When entitlement cannot be read, every `plan_*` key is absent.
The rule for every flag: **absent means "not answered yet", and the item is shown**
(`!== false`), except `plan_payroll`, where absent hides only the salary parts and leaves
the rest of Pay — so nobody is shown payslips a tenant did not buy. `goals` is a plain
boolean (installed **and** plan) and absent means hidden.

---

## 4. Routes

| Menu entry | Address | Panel opened |
|---|---|---|
| Home | `#home` | `home` |
| Inbox | `#inbox` | `inbox` (new slot) |
| Attendance & leave | `#time` | `attendance` |
| My days | `#time/days` | `att-record` |
| Insights | `#time/insights` | `attendance-insights` |
| Change shift | `#time/shift` | `shift-req` |
| Fix attendance | `#time/fix` | `att-req` |
| My pay | `#pay` | `finances`, salary tab |
| Expenses | `#pay/expenses` | `finances`, expenses tab |
| Leave encashment | `#pay/encashment` | `finances`, encashment tab |
| Request advance | `#pay/advance` | `adv-req` |
| Goals & reviews | `#growth` | `goals`, overview tab |
| Self-review | `#growth/review` | `pms-review` |
| My team | `#team` | `team` |
| Person | `#team/person` | `scorecard` |
| People | `#company/people` | `org-chart` |
| HR analytics | `#company/analytics` | `analytics` |
| Data to review | `#company/data` | `data-review` |
| Reviews (HR) | `#company/reviews` | `goals`, `hr` tab |
| Policies | `#company/policies` | `policies` |
| Org settings | `#company/settings` | `org-settings` |

An unknown address (`#nonsense`) opens Home and leaves no error. An address for a page
this person may not open shows the no-permission state (AC-30).

---

## 5. What the Inbox counts (M3)

**Rule: count only what the portal can act on today.** Expense claims to approve are not
counted — the portal has no approval screen for them. Salary advances are not counted,
for the same reason.

| Part | Doctype and filter `[UNVERIFIED — field names confirmed before step 5]` | Who gets it | Inbox row | Links to |
|---|---|---|---|---|
| Leave to approve | Leave Application · `leave_approver` = me · `status = Open` · `docstatus = 0` | anyone named as an approver | "3 leave requests to approve" | `#team` (leave list) |
| Goal and KPI updates | KPI Progress Log and Goal Progress Update · pending (empty, NULL or `Pending`) · `_pending_approvals_scope` | manager, HR | "4 goal or KPI updates to approve" | `#growth` approvals list |
| Attendance corrections | Attendance Request · draft, waiting · `permitted_employees()` minus me (decision 5) | whoever may submit one | "2 attendance fixes to decide" | `#time/fix` |
| Shift requests | Shift Request · `approver` = me · draft | named approvers, where the tenant has shift types | "1 shift change to approve" | `#time/shift` |
| Policies to acknowledge | `readable_policy_names()` minus my acknowledgements | everyone | "2 policies to read and accept" | `#company/policies` |
| My open requests | my leave, corrections and shift requests still waiting, for my **Active** Employee only | everyone with an Employee record | "3 of your requests are waiting" | the screen each came from |

The bell opens `#inbox`. After a decision in any panel, the frame refreshes the counts
without a page reload. A part with nothing is not shown. "The bell list" means the
Inbox page rows — the frame never loads the old approvals list on boot (PRIV-4).

---

## 6. The words the frame says (m5)

| Where | Exact words |
|---|---|
| Page failed | "The portal could not load. Try again. If it keeps happening, tell HR this code: `<time> · <short code>`." |
| Counts failed | "The waiting list could not load. Try again." |
| Search failed | "People search is not answering. You can still open pages from this list." |
| Nothing waiting | "All clear." |
| No permission | "This page is not part of your access. Ask HR if you think it should be." |
| Empty search, employee or manager | "Nothing matches "<term>". You can find your own team and the pages you can open." |
| Empty search, company-wide HR | "Nothing matches "<term>". You can find people in the companies you look after." |
| Empty search, store HR | "Nothing matches "<term>". You can find people in your store and anyone who reports to you." |
| Empty search, no Employee record | "Nothing matches "<term>". You can open the pages in this list." |
| Org settings, read only | "Only company-wide HR can change these settings." |

The code in the page-failed message is the time plus a short reference that matches an
Error Log entry. It holds no personal data.

---

## 7. Stories

Personas: **Rahul** (sales executive), **Sandeep** (floor manager, 19 reports), **Kamal**
(owner who holds HR), **Priya** (store HR, no direct reports), **Asha** (platform
operator, no Employee record). Sizes in points.

| # | Story | Screen | Points |
|---|---|---|---|
| **US-1** | As Rahul, I want a menu of only the pages I can use, so that nothing I tap fails. | rail, bottom bar | 5 |
| **US-2** | As Rahul, I want the menu to be right the first time it is drawn, so that items do not appear late or go missing. | rail | 3 |
| **US-3** | As Sandeep, I want the four buttons I use most on my phone, so that I rarely open the menu. | bottom bar | 5 |
| **US-4** | As Kamal, I want to know where I am and to use Back, so that I can move between pages without losing my place. | top bar | 3 |
| **US-5** | As Rahul, I want to sign out and reach my account from inside the portal, so that I am not sent to a bar that is no longer there. | profile sheet | 3 |
| **US-6** | As Sandeep, I want one honest number for what is waiting on me, so that I know when to act. | bell, Inbox | 8 |
| **US-7** | As Rahul, I want to find a person or a page by typing, so that I do not hunt through menus. | search sheet | 5 |
| **US-8** | As Rahul, I want the portal to tell me what happened when something fails, so that I am not stuck on a blank screen. | all | 3 |
| **US-9** | As Rahul on a phone, I want one sheet that behaves the same everywhere, so that I always know how to close it. | search and profile sheets | 3 |
| **US-10** | As the next engineer, I want the page split into files that render identically, so that two of us can work without clashing. | — | 5 |
| **US-11** | As Surbhi, I want the new frame switched on in one commit that can be undone in about ten minutes, so that a problem on the live site is short. | — | 3 |
| **US-12** | As Rahul on a factory floor, I want no text below 12 px on any portal page, so that I can read it in daylight. | all | 2 |
| **US-13** | As Priya (store HR), I want to read the org settings that govern my store without being offered a Save button that refuses me. | Org settings | 2 |
| **US-14** | As Priya, I must not find, count or open anything about people outside my store and my own reports, so that one store's HR is not everyone's HR. | search, Inbox | 5 |
| **US-15** | As Kamal, a person who has left must not be able to use their old login to read my team's names or approvals, so that access ends when employment does. | search, Inbox | 3 |
| **US-16** | As Asha (platform operator with no Employee record), I must not be shown a portal full of errors, so that the landing page works for everyone who can sign in. | all | 3 |
| **US-17** | As Rahul, my own date of birth, gender and phone number must not be sent to every page I open, so that a screenshot or an error report cannot carry them. | — | 2 |

---

## 8. Acceptance checks

Numbers AC-1 to AC-43 keep their subjects from revision 1, so the review's table still
reads across. New checks start at AC-44.

### US-1 · the menu

- **AC-1** Given an employee on a tenant **without** `plan_payroll`, when the frame loads,
  then there is no My pay entry, no salary tab and no payslip search result, **and
  Expenses is still reachable** under Pay.
- **AC-44** Given the same employee, when they open Pay from the menu, then the Expenses
  tab opens and an expense claim can be created (the `expenses` feature is required on
  every plan).
- **AC-2** Given an HR user whose feature payload has no `plan_analytics` key, then HR
  analytics is shown; with `plan_analytics: false` it is hidden.
- **AC-45** Given a payload with no `goals` key, then Growth and Reviews (HR) are hidden;
  given `plan_policy_library` absent, Policies is shown; given `plan_org_structure`
  absent, People is shown.
- **AC-3** Given a tenant **with** the `vendor` feature, then a Vendor User still lands on
  `/vendor-portal` and a Delivery Partner on `/driver-portal` (routing unchanged); and on
  any tenant, the menu list holds no vendor or driver entry.
- **AC-4** Given someone who is both a manager and HR, then *Team › My team* opens the
  `team` panel and *Company › Reviews (HR)* opens the `goals` panel's `hr` tab — the list
  that calls `hr_list_appraisals` (decision 37).
- **AC-5** "Checkin Log" is not a second menu item; it is a tab under Time.
- **AC-6** For every persona fixture, no element in the rail, top bar, bottom bar or search
  results carries `disabled`, `aria-disabled="true"` or a disabled class.

### US-2 · one start-up

- **AC-7** On load the frame makes exactly one `get_frame` call and one `get_nav_counts`
  call, and neither waits on a timer.
- **AC-8** For each of employee, manager, company HR, store HR, System Manager with an
  Employee record, System Manager without one, and a control-plane operator, `get_frame`
  returns the same role, feature and switch-target values as the three old calls.
- **AC-9a** Given a manager fixture, Home's team-goals card has one row per report.
- **AC-9b** Given the same fixture, the manager-notes filter lists that manager's reports.
- **AC-9c** Given an HR fixture, the Data to review badge equals `_with_review_count`.
- **AC-46 (SEC-12)** `get_frame`'s payload keys are exactly the named set; it never carries
  `date_of_birth`, `gender`, `cell_number`, `date_of_joining`, `reports_to`, `branch` or
  the full role list — checked per persona.

### US-3 · the bottom bar

- **AC-10** The bars are exactly the six rows of §2, chosen by `has_reports` and `is_hr`,
  first match wins — tested for Rahul (with and without payroll), Sandeep, Kamal, Priya
  and Asha.
- **AC-47** `has_reports` is true only when an Active Employee has `reports_to` set to this
  person. An HR user with nobody reporting to them gets no Team group and no Team button,
  even though today's `is_manager` is true for them.
- **AC-11** When a bar page is not allowed, the next page in the order Home → Inbox → Time
  → Goals → Pay → Team → Company takes its place, skipping pages already in the bar; with
  fewer than four allowed, the bar is shorter; More is always last.
- **AC-12** At 390 px, in light and dark, on every page reachable from the menu for each
  persona: labels 12 px or larger, targets 44 px or larger, no sideways scroll.
- **AC-48** The same measurement passes with the frame's Hindi test strings loaded
  (fixture only, no Hindi shipped to users — decision 12), with the test browser's font
  named in the test.

### US-4 · where I am

- **AC-13** The top bar shows group then page title in words, never the tenant name as the
  title. On the deep pages — self-review, manager review, scorecard, appraisal setup — the
  group is a link back.
- **AC-14** Every menu entry has the address in §4; Back returns to the previous page; an
  address opened directly opens that page, or the no-permission state; `#nonsense` opens
  Home with no error.
- **AC-15** After a page change focus moves to the page heading; Escape closes the menu and
  any sheet; every menu item is a link or button reachable by keyboard, with visible focus
  and `aria-current` on the current one.

### US-5 · sign out and account

- **AC-16** Frappe's website bar is not rendered, and in the same release the profile menu
  offers Log out. After Log out, `frappe.auth.get_logged_user` returns 401 and the browser
  is on `/login`.
- **AC-17** The profile menu shows the person's name and their Employee `designation` (or
  no role line when it is blank, and the User's full name with no role line when there is
  no Employee record); My account opens `/me`; "Switch to the full desk" appears only when
  `get_switch_target` returns a target, with the server's label; Tenant admin appears only
  for a System Manager on a site where `alvoraa_control_plane` is set — tested on both
  site types.
- **AC-18** A language is *offered* only when it is enabled on the site **and**
  `alvoraa_portal` ships a translation for it. In Wave 1 that is English alone, so the
  language row is not shown — including on a site with Frappe's default 17 enabled
  languages.
- **AC-49 (SEC-9)** No frame module writes a `User` record; `set_my_language` does not
  exist in Wave 1. A user whose `User.language` is already something else (set in the
  desk) still gets the English frame, with no half-translated labels.
- **AC-19** Light or dark offers Match my phone · Light · Dark; the inline script that sets
  `data-theme` comes **before** `design_system.html` in the page source; the choice is kept
  on the device; "Match my phone" follows a change of the phone's setting without a
  reload; the tenant colour is applied again after a change.

### US-6 · the count

- **AC-20** The Inbox menu item, the bell and the Inbox bottom-bar button show the same
  total: approvals waiting + policies not acknowledged + my own open requests. The Team
  and Policies badges, where shown, count team approvals and policies to acknowledge
  respectively — the same numbers as their Inbox rows.
- **AC-21** Given one pending goal update in store A, one in store B and one for a
  head-office employee with no branch: store A's HR sees 1 in the count **and** 1 in the
  Inbox row's list; company-wide HR sees 3 and 3.
- **AC-50** A store HR person with a direct report in another store still sees that
  report's item (the union in SEC-3).
- **AC-22** My own pending leave is counted under "my requests", never under approvals. A
  person who is their own leave approver sees it once, under "my requests".
- **AC-23** The Inbox page shows one row per part that has something, with the wording and
  the link in §5; a part with nothing is not shown; with nothing at all it reads "All
  clear". The rows hold numbers only — no names, reasons or document ids.
- **AC-51 (SEC-5)** For every part and every persona, the count equals the number of rows
  on the screen the row links to. Every fixture item is created through the endpoint a
  real user uses. Goal-update fixtures cover pending as empty, NULL and `Pending`.
- **AC-52 (decision 5 / SEC-5)** `attendance_correction.to_review` returns only
  `permitted_employees()` minus the caller: store HR sees their store's correction, not
  another store's and not a head-office one.
- **AC-53 (00f decision 1)** Attendance corrections are counted where they sit today —
  HR's queue. A manager's count does not include them in Wave 1.
- **AC-54** After a decision is taken in a panel, the counts refresh without a page reload.
- **AC-24** `get_nav_counts` makes no more than 15 queries whatever the team size, and
  answers within 500 ms at p95 — 20 warm calls, none dropped, as company-wide HR on a
  1,000-employee fixture.
- **AC-55 (PRIV-4)** No boot path calls `get_pending_approvals`.

### US-7 · search

- **AC-25** The pages offered in search are exactly the pages in this person's menu.
- **AC-26** Rahul finds himself and anyone below him, and not a colleague in another line.
  Priya (store HR) finds her store **plus anyone reporting to her**, and not a head-office
  employee with no branch. Company-wide HR finds that person.
- **AC-27** A person result opens the org chart on that person where the tenant has
  `plan_org_structure`; where it does not, search offers pages only. Someone with no photo
  shows initials, and a broken photo URL falls back to initials.
- **AC-56 (PRIV-2)** The payload's keys per result are exactly `employee`, `name`, `title`,
  `department`, `image`; `employee` is never displayed; only Active employees are
  returned, with one Left, one Inactive and one Suspended person in the fixture matching
  the term.
- **AC-28** Under two letters returns no people; the frame asks for 12; `limit=500` returns
  at most 50. Ctrl K / ⌘K opens search.
- **AC-57 (PRIV-3)** `%` and `_` in the term are escaped: searching `%%` or `a_b` returns
  only real matches inside the caller's scope.
- **AC-29** The empty-search sentence matches the scope actually enforced, in the words of
  §6, for employee or manager, company-wide HR, store HR and no-Employee-record.
- **AC-58 (SEC-10)** A designation of `<img src=x onerror=alert(1)>` appears as text in a
  search result, the rail and the profile menu, and creates no element.
- **AC-59 (PRIV-5)** The frame's search and every write send their arguments in a POST
  body; a log-capture test shows the endpoint, user id, outcome and time, and no name or
  search term, on a normal call and on a refused one.

### US-8 · states

- **AC-30** A page this person may not open shows the §6 sentence.
- **AC-31** The shell and the page skeleton are in the server-rendered HTML (checkable in
  the source, with no timing). The 300 ms figure is measured and recorded (§13).
- **AC-32** When the counts fail, the bell shows no number and the Inbox page shows the §6
  sentence with Try again; the rest of the page works.
- **AC-60** When people search fails, the sheet shows the §6 sentence and still lists pages.
- **AC-33** When `get_frame` fails, the page shows the §6 sentence with a Try again button
  and a code that holds no personal data.
- **AC-61** A badge of zero shows no number, and a screen reader hears "Inbox, nothing
  waiting".
- **AC-62** When the session has ended, the frame sends the person to `/login`, not to the
  page-error state.
- **AC-63 (US-16)** Asha, a System Manager with no Employee record, gets: Home with a plain
  "your account is not linked to an employee record" line, no Time, Pay or Growth items, a
  working Company group, and **no error state** — the counts endpoint returns her own
  empty parts instead of throwing (today's helper throws "No Employee record found").

### US-9 · sheet and toast

- **AC-34** The shared sheet is a dialog with a title, traps focus, closes on Escape and
  returns focus to the control that opened it.
- **AC-35** Toast messages are announced (`role="status"`), and `toast(msg, type)` keeps
  its signature.

### US-10 · the split

- **AC-36** The page rendered from its includes is byte-for-byte identical to the page
  before the split, apart from the include tags.
- **AC-37** Every test and CI check that reads the page reads it with includes expanded,
  and fails if it finds no include tags where the page has them.
- **AC-38** The full `alvoraa_portal` and `alvoraa_goals` suites pass after the split, with
  no test removed.
- **AC-39** The layout test bans `container-type` on the wrapper elements, and the frame
  uses `@media`, not container queries.
- **AC-64 (OPS-13)** Server time for the page, 20 warm requests before and after the split,
  is no more than 10 % slower. If it is, the includes are merged into about 15 files.

### US-11 · the swap

- **AC-40** Before the swap, loading the route `/hrms-employee-next` gives 200 for a System
  Manager, **403** for any other signed-in persona, and a redirect to `/login` for Guest.
- **AC-65 (OPS-12 / SEC-1)** The preview page sets `context.no_cache = 1` and is not in the
  sitemap.
- **AC-41** The swap is one commit: `/hrms-employee` uses the new frame, the preview page
  and the classic frame files are deleted, and the pinned tests are repointed in the same
  commit. Reverting it restores the old frame with every test passing.
- **AC-66** After the swap, `/hrms-employee-next` returns 404 and no tracked file names it.
- **AC-42** The rail mark never shows a broken image and the letter behind it is visible in
  both themes.

### US-12, US-13, US-14, US-15, US-17

- **AC-43** `--fs-xs` is 12 px, changed in **its own commit** (OPS-11). On the employee,
  driver and vendor portals at 390 px no text is under 12 px and nothing scrolls sideways;
  the login page, admin console and field check-in render with no visual change (the token
  has no uses there). The driver and vendor checks run on a tenant with `vendor` on.
- **AC-67 (US-13, decision 3)** For store HR and for an HR User, the Org settings page shows
  no Save controls and shows the §6 line. For company-wide HR the Save controls are there
  and saving works. `get_frame` carries the "may save settings" flag the panel reads.
- **AC-68 (US-15, SEC-14)** A manager whose Employee is Left, whose login is still enabled
  and whose reports have not moved: empty search, zero approvals, empty bell list; their
  own open requests still count.
- **AC-69 (SEC-2)** A registry test lists every whitelisted function in `frame_api.py` and
  `inbox_api.py` with its Guest-refused, wrong-persona and scope cases; a new whitelisted
  function with no entry fails the test.
- **AC-70 (SEC-15)** A static check finds no `global`, and no module-level dict, list or set
  changed at run time, in `frame_api.py` and `inbox_api.py`.
- **AC-71 (SEC-6)** `frame_api.py` and `inbox_api.py` contain no `ignore_permissions`, and
  the edited bodies of `_pending_approvals_scope`, `_search_scope` and the new
  `permitted_employee_filters` gain none.

---

## 9. Personas × the five states

| Persona | Loading | Nothing due | No permission | Card error | Page error |
|---|---|---|---|---|---|
| Rahul | AC-31 | AC-23, AC-61 | AC-30 (`#team`) | AC-32, AC-60 | AC-33 |
| Rahul, no payroll | AC-31 | AC-23 | AC-30 (`#pay` salary route) | AC-32 | AC-33 |
| Sandeep | AC-31 | AC-23 | AC-30 (`#company/analytics`) | AC-32 | AC-33 |
| HR with reports | AC-31 | AC-23 | — | AC-32 | AC-33 |
| HR without reports | AC-31 | AC-23 | AC-30 (`#team`) | AC-32 | AC-33 |
| Priya, store HR | AC-31 | AC-23 | AC-67 (Org settings Save) | AC-32 | AC-33 |
| Kamal | AC-31 | AC-23 | — | AC-32 | AC-33 |
| Manager and HR in one | AC-31 | AC-23 | — | AC-32 | AC-33 |
| Asha, no Employee record | AC-31 | AC-63 | AC-63 | AC-63 | AC-33 |
| Session ended | — | — | — | — | AC-62 |

---

## 10. Edge cases

| Case | What must happen |
|---|---|
| No photo, or a broken photo URL | Initials, in the rail, profile menu and search (AC-27) |
| Very long name, title or tenant name | Cut with "…" on one line in the rail and top bar, full text in the profile sheet and in the accessible name, no sideways scroll at 390 px. Test values: "Venkata Satya Lakshmi Narasimha Subrahmanyam Chakravarthy", "Senior Assistant Manager – Customer Relationship (Bridal Jewellery)" |
| No manager (`reports_to` empty) | Search finds this person and anyone below; nothing breaks |
| No branch | The employee is outside every store (AC-21, AC-26); for everyone else nothing changes |
| A second language on a tenant | The row stays hidden until a translation ships (AC-18) |
| One user, two Employee records | The frame uses **one** "who am I" helper — the Active record, as `hr_api._get_employee` does — in `get_frame` and `get_nav_counts`, so the two cannot describe different people `[UNVERIFIED — whether Employee allows the same `user_id` on two records; confirmed before step 3]` |
| Store HR who also holds System Manager | Not narrowed — System Manager sees everyone. Intended; stated so a tester does not file it |
| HR User (not HR Manager) | Same read-only Org settings as store HR (AC-67) |
| Administrator | Sent to the desk; opening the portal directly behaves as Asha does |
| Role change while logged in | Cached context is cleared by today's hooks; at most one hour otherwise |
| Two tabs, one decision | The other tab's count is stale until its next load. Accepted in Wave 1 |
| Leaver with an enabled login | AC-68 |

The usual HR edge cases — mid-period joiners and leavers, back-dating, negative balances,
time zones, cancelled or amended documents — **do not apply: the frame changes no business
rule.** The one exception is the leaver, who is covered above.

---

## 11. Differences from the approved prototype (M8)

| # | Prototype | Built | Covered by |
|---|---|---|---|
| a | "Switch to the full desk" for every manager | Only when the server returns a target (HR and admins), with the server's label — "Switch to Admin" or "Switch to HR Core" | **Open question 1** — the user's word on the label, and on whether plain managers get it |
| b | Tenant admin for the owner | Control-plane operators only | Decision 9 |
| c | Language row always | Hidden until a translation ships | Decisions 4 and 14 |
| d | Empty search says "your own team, your manager" | Says team only, per scope | Decision Q-c (14 Sep) and decision 5 |
| e | Company › People for everyone | Needs `plan_org_structure` | Existing plan gate (appendix A §C) |

---

## 12. Out of scope for Wave 1

Home content and the "Needs you" rules; the Inbox list and decisions; who decides an
attendance fix (00f decision 1 changes the routing in Wave 2); the check-in rule for the
owner (00f decision 6); the Time, Pay, Growth, Team and People screens; the staff
directory and person sheet; "Who's off" (00f decision 3); the grace wording (00f decision
7); peer feedback (00f decision 4); the review's own copy of goals, KPI increments as
amounts, the reporting-line note on HR review steps, absence reasons, small-group
suppression, "Needs review" and data dates (01b §14 items 5–12); moving the existing
drawers into the shared sheet; Hindi and Punjabi for users; compression (slice 036);
cached script files (OPS-31, after the swap); the owner/HR screen redesign; the CXO
multi-company view; the mobile app's in-app mode; `set_my_language`; the org-chart
company scope (ALV-86); the wider leaver fix (ALV-87); `approve_kpi_update` and the other
company-scoped performance endpoints.

---

## 13. NFR numbers for this slice

Measured on the local copy in Chrome with **"Slow 4G" and 4× CPU slow-down**, cache off
(decision 9, OPS-17) — not the undefined "3G".

| What | Number |
|---|---|
| Shell and skeleton painted | ≤ 300 ms, median of 5 loads |
| Home usable | ≤ 2.5 s at p95 of 20 loads — **only reachable once slice 036's compression is live**; recorded before and after |
| `get_frame`, `get_nav_counts` | ≤ 15 queries; ≤ 500 ms p95 over 20 warm calls, as company-wide HR at 1,000 employees |
| Start-up calls | 2, with no timer |
| Server time for the page after the split | within 10 % of before (AC-64) |
| Accessibility | WCAG 2.2 AA; 390 px; 200 % zoom |

---

## 14. Migration, audit, localisation

**Migration:** none. No schema change, no data change, no patch, and no `bench migrate`,
`bench build` or cache clear (07 §4.2).

**Audit trail:** the frame writes nothing. Refused calls log through `access.log_refusal`
with no personal content.

**Localisation and accessibility:** every frame string in `__()`, no joined sentences,
dates through the existing formatter; Hindi measured at 390 px in test fixtures only
(AC-48, decision 12); labels 12 px or larger; 44 px targets on phones; 16 px inputs;
colour never the only signal; `prefers-reduced-motion` respected.

---

## 15. Compliance sub-analysis

| Question | Answer |
|---|---|
| Data touched | Names, job titles, departments and photos in search; counts; the caller's own identity block (SEC-12) |
| Obligations engaged | DPDP minimisation and access rights; logging duties; OWASP ASVS 5.0 L2 — with dates in `01c` |
| Visibility delta | **Narrower** for store HR (counts, bell list, search, corrections queue) and for leavers. Nothing wider |
| Decision automation | None. No AI, no scoring, no monitoring |
| Retention and deletion | Nothing new stored. The theme choice lives on the viewer's device only |
| Open compliance question | None blocking (security review §6) |

The analyst is not a lawyer, and neither is the engineer: nothing here is a legal ruling.

---

## 16. Release gates (not acceptance checks)

1. Compression (slice 036) live on dev before the swap goes to dev, and on production
   before the swap goes to production — checked by the engineer on the day.
2. The swap ships in a release of its own (OPS-16).
3. Production swap only after go-live settles: **≥ 10 working days after DTC goes live, no
   client-blocking issue for 5 days, outside payroll close, compression live, and the frame
   on dev for 5 days** (decision 11).
4. The previous production image tag is written down before the swap; rollback is a
   redeploy of it, about 10 minutes (OPS-14).
5. `ALV-86` (the org chart across companies and stores) — its state is recorded on the day
   of the swap. Wave 1 does not wait for it and does not work around it (decision 8).
6. No pushes to dev in the hour after the production swap (OPS-19).

---

## 17. Traceability

| Item | AC |
|---|---|
| SEC-1 | AC-40, AC-65 |
| SEC-2 | AC-69, plus the Guest and wrong-persona cases inside AC-8, AC-21, AC-26 |
| SEC-3 | AC-21, AC-50 |
| SEC-4 | AC-26, AC-56 |
| SEC-5 | AC-20 to AC-23, AC-51, AC-52, AC-53 |
| SEC-6 | AC-71 |
| SEC-7 | AC-17 |
| SEC-8 | AC-17 |
| SEC-9 | AC-18, AC-49 |
| SEC-10 | AC-58, AC-42 |
| SEC-11 | AC-25 |
| SEC-12 | AC-46 |
| SEC-14 | AC-68 |
| SEC-15 | AC-70 |
| PRIV-1 | AC-26 |
| PRIV-2 | AC-56 |
| PRIV-3 | AC-28, AC-57 |
| PRIV-4 | AC-23, AC-55 |
| PRIV-5 | AC-59 |
| PRIV-6 | AC-19 |
| PRIV-7 | the table in `01c` PRIV-7, checked by the test engineer; AC-26, AC-27 |
| OPS-1 | release gate 1 |
| OPS-2, OPS-14 (was OPS-3) | AC-40, AC-41, AC-66; release gate 4 |
| OPS-4 | release gate 3 |
| OPS-5 | §14 |
| OPS-6, OPS-7 | AC-36, AC-37, AC-38 |
| OPS-8 | out of scope (decision 12) |
| OPS-9, OPS-17 | §13, AC-24, AC-31 |
| OPS-10 | AC-40 |
| OPS-11 | AC-43 |
| OPS-12 | AC-65 |
| OPS-13 | AC-64 |
| OPS-16, OPS-19 | release gates 2 and 6 |
| OPS-15, OPS-18 | with the user (07 §3b) |
| 00f design decisions 1–7 | 1: AC-53. 2: AC-10. 5: AC-43. 3, 4, 6, 7: §12 |
| 00f strategy decisions 1–14 | 1: this revision. 2, 3: AC-40, AC-41. 4: gate 3. 5: AC-26, AC-27. 6: AC-23. 7: AC-21, AC-26, AC-52. 8: AC-10, AC-47. 9: AC-17. 10: AC-43. 11: process. 12, 13: §12. 14: AC-18 |
| 22 Sep review decisions 1–12 | 1: AC-1, AC-44. 2: §2, AC-10, AC-47. 3: AC-67. 4: AC-18, AC-49. 5: AC-52. 6: AC-68. 7: AC-26. 8: gate 5. 9: §13. 10: gate 4. 11: gates 2 and 3. 12: AC-48 |
| 01b §14 items 1–4, 13, 14 | AC-1, AC-6, AC-16, AC-18, AC-19, AC-20, AC-31, AC-48 |
| 01b §14 items 5–12 | §12 |
| Prototype screens | US table in §7; differences in §11 |

---

## 18. Ready check

| Box | State |
|---|---|
| Brief approved | ✓ — the 009 plan and the decisions stand in for `01` (header) |
| Clickable prototype reviewed | ✓ 22 Sep |
| Every state designed and specified per persona | ✓ §9 |
| `01c` written and reviewed | ✓ revision 2, **re-check by the security engineer pending** |
| `07` §1–4 written and reviewed | ✓ including the DevOps §4 and the decisions in §3b |
| Gap analysis verified in source | ✓ §1, with file and line |
| Stories: personas, sized, linked to screens, "must not" stories | ✓ §7 (US-14 to US-17 are the "must not" stories) |
| Every story has checks with observable oracles | ✓ §8 |
| Traceability complete | ✓ §17 |
| Permission matrix with negatives | ✓ §3 and `01c` |
| Edge cases | ✓ §10 |
| NFR numbers | ✓ §13 |
| Migration stated | ✓ none |
| Compliance sub-analysis | ✓ §15 |
| No prohibited capability | ✓ nothing AI-shaped, no monitoring |
| Open questions owned, none blocks day 1 | ✓ day 1 is the split (US-10) |
| Frappe details verified in source | **Partly** — three items marked `[UNVERIFIED]` here and four in `00` §9, each checked before the step that needs it |

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | The desk link: keep the server's labels ("Switch to Admin", "Switch to HR Core") or the prototype's "Switch to the full desk"? Should a plain manager get it at all? | Surbhi | AC-17, difference (a) |
| 2 | Residual risks R3, R4, R6 in `01c` need an owner and a date | Surbhi with the security engineer | The security review at the end |
| 3 | Confirmation that decision 3 covers a tenant System Manager seeing unfinished screens with real data | Surbhi | The first release carrying the preview page |
| 4 | Re-review of this revision | Business analyst | Ready |

## Assumptions

- `[ASSUMPTION]` `/me` is the right target for My account; checked on the bench before step 2.
- `[ASSUMPTION]` Field names on Shift Request and Attendance Request match what §5 needs.
- `[ASSUMPTION]` The prototype's `bnavItems()` is the approved behaviour for the Company
  button (it opens HR analytics).

## Handoff note

To the business analyst: the four blockers are answered in §1 (Pay), §2 (the persona
table, with the consequence stated), §8 AC-18 (offered languages) and §2's fallback order.
The one thing I did **not** do is invent an answer for difference (a) — the desk link's
label and whether plain managers get it. It needs the user's word, and until then the
build follows the server's current behaviour.

To the test engineer: the three structural tests the security review asked for are AC-69
(registry), AC-51 (count matches list, fixtures made the way users make them) and AC-70
(no module-level state).
