---
slice: 034-redesign-wave1
artifact: 02-functional-spec
author: hrms-fullstack-engineer, revised after the analyst and security re-reviews
date: 2026-09-23
revision: 3 (BA re-review 02c and security re-review 06b applied; Surbhi's decisions of 23 Sep, W1D-13 to W1D-18, written in)
status: draft, revised — ready to build once the strategy gate is passed
inputs: [02c-ba-rereview.md, 06b-security-rereview.md, 02b-ba-review.md, 06-security-review-of-requirements.md, 07-devops-inputs.md §4 and §3b, 01c-security-privacy-requirements.md (revision 3), 00-impact-analysis.md, 00g-decision-register.md, ../009-ess-portal-redesign/01b-ux-design.md, ../009-ess-portal-redesign/appendix-a-frame.md, prototype-v2.html]
brief: there is no `01` for slice 034. The approved brief is `../009-ess-portal-redesign/00-assessment-and-plan.md` (Wave 1) plus the decisions in `00g-decision-register.md`.
---

# Wave 1 frame — functional spec

**Revision 3.** The analyst's two corrections and the security review's three must-fixes
are applied, and Surbhi's six decisions of 23 September are written in. What changed is
listed in §19, and the build size is restated in §20.

**Decisions are cited as `W1D-nn`** and live in `00g-decision-register.md`. The bare
"decision 5" numbering that pointed at nothing is gone; the two sets in
`../009-ess-portal-redesign/00f-decisions-2026-09-22.md` are cited as "009 design
decision n" and "009 strategy decision n".

**Prototype:** `C:/Surbhi-Git/hrlocal-data/prototypes/009-ess-portal-redesign/prototype-v2.html`.
Screens used below: **rail**, **top bar**, **bottom bar**, **search sheet**, **profile
sheet**, **Inbox**.

---

## 1. Gap analysis, checked in the source

| Need | What exists (file checked) | Decision |
|---|---|---|
| Log out, My account | Frappe's website bar; `/me` | **Configure:** remove the bar, link log out and `/me` from the profile menu |
| Language per user | `User.language`; only System Manager may write `User` (v16.33.1) | **Drop from Wave 1** (W1D-04) |
| Translations in the page | Frappe `__()`; `frappe._messages` is empty on website pages (appendix A §E) | **Extend:** wrap frame strings; English only |
| Role and plan flags | `hr_api.get_portal_context:99`, `get_available_features:1213`, `subscription.FEATURES:58` | **Reuse**, behind one call, with a fixed field list (SEC-12) |
| Desk switch target | `module_access.get_switch_target:1099` | **Reuse** |
| Scope helpers | `access.permitted_employees:237`, `permitted_branches:217` | **Extend:** one shared filter helper (SEC-4) |
| People search | `alvoraa_org_structure.api.search_people:559`, `_search_scope:577` | **Extend:** store narrowing, Active-only caller, wildcards escaped |
| Approvals scope | `goals_api._pending_approvals_scope:1162` | **Extend:** `permitted_employees` + own reports |
| Team panel's no-manager list | `hr_api.get_manager_dashboard:291-307` — every Active employee with `reports_to` not set, `ignore_permissions=True`, no company or branch filter | **Extend:** narrow it to `permitted_employees()` (W1D-13, SEC-13) |
| Corrections queue | `attendance_correction.to_review:722` | **Extend:** same scope as the count, **for an HR caller only** (W1D-05, W1D-14) |
| Policy acknowledgements | `alvoraa_policy_library.access.readable_policy_names:163` | **Reuse** |
| Counts in one place | nothing | **Build:** `inbox_api` |
| Menu, bottom bar, routes, sheet, states | hand-written sidebar `hrms-employee.html:2345-2440` | **Build** in the frame includes |
| Pay pages | `panel-finances:2781` holds Salary Slips, Expenses, Leave Encashment; `expenses` is a **required** feature on every plan (`subscription.py:83-90`) | **Extend:** hide the salary parts without payroll, keep the rest (W1D-01) |
| Directory, person sheet, Inbox list, feedback | — | **Out of Wave 1** (§12) |

No new DocType, no custom field, no patch, no migration.

---

## 2. Persona resolution — which flags produce which bar (W1D-02)

Two flags decide everything. Both come from `get_frame`:

- **`has_reports`** — **someone is recorded as reporting to this person**: at least one
  Active Employee with `reports_to` = this person's Active Employee record. This is *not*
  today's `is_manager`, which is also true for any HR user when anybody in the tenant has
  no manager (the stand-in rule, `hr_api.py:118-124`).
- **`is_hr`** — HR Manager, HR User, System Manager or Administrator, as
  `get_portal_context` sets it today. A CXO is a System Manager, so a CXO is HR here.

**Precedence, corrected in revision 3 (BA finding 1).** **Rules 1 to 5 apply only to a
person who has an Active Employee record.** Anyone without one — no Employee record at
all, or one that is not Active — falls straight to rule 6. Without that line, Asha (a
platform operator with no Employee record) is a System Manager, so `is_hr` is true and
`has_reports` is false: she would match rule 2 and be given a Time button that §3 hides
and AC-63 forbids. **AC-10 and AC-63 could not both be true.** They can now.

| # | Rule (first match wins) | Applies to | Team group | Bottom bar |
|---|---|---|---|---|
| 1 | `is_hr` **and** `has_reports` | a person with an **Active** Employee record | Yes | Home · Inbox · Company · **Team** |
| 2 | `is_hr` **and not** `has_reports` | a person with an **Active** Employee record | No | Home · Inbox · Company · **Time** |
| 3 | `has_reports`, not HR | a person with an **Active** Employee record | Yes | Home · **Team** · Inbox · Time |
| 4 | **Active** employee, tenant has `plan_payroll` | — | No | Home · Time · **Pay** · Goals |
| 5 | **Active** employee, no `plan_payroll` | — | No | Home · Time · **Inbox** · Goals |
| 6 | **No Active Employee record** — no record at all (platform operator), or one that is Left, Inactive or Suspended | — | No | Home · Inbox · Company (fewer buttons if fewer are allowed) |

A leaver whose login is still enabled (AC-68) therefore gets rule 6's bar, and the
endpoints behind it return his own empty parts — the same shape Asha gets. That is
consistent with SEC-14, which gives him an empty search and zero approvals.

**Consequence, stated on purpose:** an HR user with no direct reports loses the Team
panel they see today. Today's stand-in rule shows them the people at the top of the
company — for store HR that is head office, outside their store. Removing it is
intended (W1D-02).

**What this does *not* do, corrected in revision 3 (BA finding 2).** Revision 2 claimed
hiding the Team group "closes the leak the analyst found". **It did not.** The Team
panel's data comes from `get_manager_dashboard` (`hr_api.py:291-307`), which adds every
Active employee with no manager, with `ignore_permissions=True` and no company or branch
filter, for anyone holding HR Manager or HR User. A store HR person with **one** direct
report is rule 1: they keep the Team group, and they would still see head office. The
leak is closed by **narrowing the query itself** — SEC-13 and AC-72 (W1D-13), which is in
Wave 1's scope. Hiding a menu entry was never a data control.

**Where an HR person with no reports finds people instead:** Company › People, which is
gated by `plan_org_structure` (§3). **On a tenant without that plan they end up with no
people list at all** — a real loss of a page they use today. That is open question 5, and
it is not answered yet.

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
| Team | — | ✓ own reports | only with direct reports; the no-manager list is their own company and store only (SEC-13) | same, narrowed to their store (SEC-13) | ✓ | only with direct reports | only with direct reports | — |
| Company › People | ✓ where `plan_org_structure` | same | same | same | same | same | same | ✓ where the plan allows |
| Company › HR analytics, Data to review | — | — | ✓ where `plan_analytics` is not `false` | same | same | ✓ (a System Manager is `is_hr`) | ✓ | ✓ |
| Company › Reviews (HR) | — | — | ✓ where `goals` | same | same | ✓ | ✓ | ✓ |
| Company › Policies | ✓ where `plan_policy_library` | same | same | same | same | same | same | ✓ |
| Company › Org settings | — | — | ✓ read and save | ✓ **read only** — Save hidden (W1D-03) | ✓ | ✓ | ✓ | ✓ read only |
| Search finds | self and below | self and below | permitted companies | **own store plus own line** | permitted companies | everyone | everyone | nobody |
| Switch to desk | — | — | `/app/hr` | `/app/hr` | `/app` or `/app/hr` | `/app` | `/app` | per role |
| Tenant admin | — | — | — | — | — | **—** | ✓ | only on the control plane |
| Preview page (only where `frappe.conf` sets `portal_preview: 1` — local and dev, never production; **404 for everyone elsewhere**, W1D-15) | 403 | 403 | 403 | 403 | 403 unless System Manager | ✓ | ✓ | ✓ if System Manager |

**Missing plan keys.** When entitlement cannot be read, every `plan_*` key is absent.
The rule for every flag: **absent means "not answered yet", and the item is shown**
(`!== false`), except `plan_payroll`, where absent hides only the salary parts and leaves
the rest of Pay — so nobody is shown payslips a tenant did not buy. `goals` is a plain
boolean (installed **and** plan) and absent means hidden.

**`leave_encashment` and `advance_request` are not `plan_*` keys** and do not follow that
rule (BA note n2). They are set separately (`hr_api.py:1240-1244` and `:1273-1277`), and
today's page reads them straight — `f.leave_encashment`, `f.advance_request` — so an
absent key already behaves as false and hides the item (`hrms-employee.html:7828` and
`:7825`). **The frame keeps that behaviour exactly: absent means hidden.** This is not a
new narrowing; it is what a tenant without those features sees today. When the whole
features call fails, every one of these keys is absent, so Pay shows Expenses alone — the
one part that is required on every plan. AC-45 covers it.

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

**Pay on a tenant without payroll** (BA note n1). `#pay` maps to the `finances` panel's
salary tab, which does not exist without `plan_payroll`. On such a tenant the Pay group
opens **`#pay/expenses`** instead, and `#pay` itself shows the no-permission state of §9.
Nothing in the menu points at `#pay` on those tenants; the address is reachable only by
typing it or by an old bookmark. AC-44 is the check.

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
| Attendance corrections | Attendance Request · draft, waiting · **for an HR caller** `permitted_employees()` minus me (W1D-05); **for a reviewer who is not HR, today's scope unchanged** (W1D-14) | whoever may submit one — `_may_review()` tests the submit permission, not a role | "2 attendance fixes to decide" | `#time/fix` |
| Shift requests | Shift Request · `approver` = me · draft | named approvers, where the tenant has shift types | "1 shift change to approve" | `#time/shift` |
| Policies to acknowledge | `readable_policy_names()` minus my acknowledgements | everyone | "2 policies to read and accept" | `#company/policies` |
| My open requests | my leave, corrections and shift requests still waiting, for my **Active** Employee only | everyone with an Employee record | "3 of your requests are waiting" | the screen each came from |

The bell opens `#inbox`. After a decision in any panel, the frame refreshes the counts
without a page reload. A part with nothing is not shown. "The bell list" means the
Inbox page rows — the frame never loads the old approvals list on boot (PRIV-4).

**Where a list is capped, the count is not** (security note N3). `to_review(limit=50)`
reads at most 50 rows by creation date **and then** drops the non-waiting ones in Python,
so a count built as a plain query and the screen disagree above the cap: the bell could
say 60 while the screen shows 41. The count therefore uses **the list's own definition of
waiting** — `docstatus = 0` and `alvoraa_review_status` not `Declined` or `Withdrawn`,
including rows where it is NULL or empty — applied in the database, and it is **not
capped**. Where the count is above the cap the screen says "showing the first 50 of 60"
rather than quietly showing fewer. The alternative the security review offered — cap the
count and show `50+` — is declined, because a "50+" cannot be added into the one honest
total AC-20 requires. AC-51 tests it at cap + 1.

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
| **US-18** | As the security engineer, I want every new endpoint to be safe on its own — whatever page calls it — so that the preview gate is never the thing protecting anyone's data. | — | 3 |

US-18 is new in revision 3 (BA note n7). AC-69, AC-70 and AC-71 belonged to no story in
revision 2, and they are the three that carry SEC-2, SEC-6 and SEC-15 — the structural
checks. They now belong to US-18.

---

## 8. Acceptance checks

Numbers AC-1 to AC-43 keep their subjects from revision 1, so the review's table still
reads across. New checks start at AC-44.

### US-1 · the menu

- **AC-1** Given an employee on a tenant **without** `plan_payroll`, when the frame loads,
  then there is no My pay entry, no salary tab and no payslip search result, **and
  Expenses is still reachable** under Pay.
- **AC-44** Given the same employee, when they open Pay from the menu, then the frame
  routes to **`#pay/expenses`**, the Expenses tab opens and an expense claim can be
  created (the `expenses` feature is required on every plan). Typing `#pay` directly on
  that tenant shows the §6 no-permission sentence, not an empty salary tab.
- **AC-2** Given an HR user whose feature payload has no `plan_analytics` key, then HR
  analytics is shown; with `plan_analytics: false` it is hidden.
- **AC-45** Given a payload with no `goals` key, then Growth and Reviews (HR) are hidden;
  given `plan_policy_library` absent, Policies is shown; given `plan_org_structure`
  absent, People is shown. **Given `leave_encashment` absent, the Leave encashment tab is
  hidden; given `advance_request` absent, Request advance is hidden** — absent behaves as
  false for those two, matching today's page. Given the whole features call fails, Pay
  shows Expenses alone and no other Pay item.
- **AC-3** Given a tenant **with** the `vendor` feature, then a Vendor User still lands on
  `/vendor-portal` and a Delivery Partner on `/driver-portal` (routing unchanged); and on
  any tenant, the menu list holds no vendor or driver entry.
- **AC-4** Given someone who is both a manager and HR, then *Team › My team* opens the
  `team` panel and *Company › Reviews (HR)* opens the `goals` panel's `hr` tab — the list
  that calls `hr_list_appraisals` (slice 010, decision 37).
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
  and Asha. **Rules 1 to 5 are tried only for a person with an Active Employee record**,
  so Asha (System Manager, no Employee record) reaches rule 6 and gets Home · Inbox ·
  Company with **no Time button**, which is what AC-63 and §3 require. The leaver of
  AC-68 also reaches rule 6.
- **AC-47** `has_reports` is true only when an Active Employee has `reports_to` set to this
  person. An HR user with nobody reporting to them gets no Team group and no Team button,
  even though today's `is_manager` is true for them.
- **AC-11** When a bar page is not allowed, the next page in the order Home → Inbox → Time
  → Goals → Pay → Team → Company takes its place, skipping pages already in the bar; with
  fewer than four allowed, the bar is shorter; More is always last. **Named cases** (BA
  note n5 — goals-off tenants exist, so these are fixtures, not a generic rule):

  | Persona and tenant | Missing | Bar |
  |---|---|---|
  | Rahul, payroll on, goals app off | Goals | Home · Time · Pay · **Inbox** |
  | Rahul, payroll off, goals app off | Goals and salary | Home · Time · Inbox · **Pay** (Pay exists — Expenses) |
  | Asha, no Employee record | Time, Goals, Pay, Team | Home · Inbox · Company — **three buttons** |
  | Priya, store HR, no reports | — | Home · Inbox · Company · Time |
  | Sandeep | — | Home · Team · Inbox · Time |
- **AC-12** At 390 px, in light and dark, on every page reachable from the menu for each
  persona: labels 12 px or larger, targets 44 px or larger, no sideways scroll.
- **AC-48** The same measurement passes with the frame's Hindi test strings loaded
  (fixture only, no Hindi shipped to users — W1D-12), with the test browser's font
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
  `alvoraa_portal` ships a translation for it. In Wave 1 that is English alone. **No
  offered-language list is computed and no language control is built at all**, so the
  oracle is: the profile sheet contains no language row, on a plain site and on a site
  with Frappe's default 17 enabled languages alike (BA note n3 — do not build a test that
  reads a list nothing produces).
- **AC-49 (SEC-9)** No frame module writes a `User` record; `set_my_language` does not
  exist in Wave 1. A user whose `User.language` is already something else (set in the
  desk) still gets the English frame, with no half-translated labels.
- **AC-19** Light or dark offers Match my phone · Light · Dark; the inline script that sets
  `data-theme` comes **before** `design_system.html` in the page source; the choice is kept
  on the device; "Match my phone" follows a change of the phone's setting without a
  reload; the tenant colour is applied again after a change.

### US-6 · the count

- **AC-20** The Inbox menu item, the bell, **and the Inbox bottom-bar button where the
  bar shows one**, all show the same total: approvals waiting + policies not acknowledged
  + my own open requests. (Rules 1, 2 and 4 of §2 have no Inbox button; the menu item and
  the bell still agree — BA note n6.) The Team
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
  **Capped-list boundary (N3):** with 51 waiting attendance corrections in the caller's
  scope, the count reads 51, the screen lists 50, and the screen says "showing the first
  50 of 51". A fixture also carries a declined and a withdrawn correction inside the first
  50 by creation date, so a count that ignored the state filter would disagree.
- **AC-52 (W1D-05, W1D-14 / SEC-5)** Four cases, with three corrections in the fixture —
  one in store A, one in store B, one from a head-office employee with no branch:

  | Caller | `to_review` returns | Count |
  |---|---|---|
  | Store A's HR | store A's correction only | 1 |
  | Company-wide HR | all three | 3 |
  | An HR person at head office who holds no Branch permission at all | all three — they are company-wide by definition | 3 |
  | **A reviewer who is not HR but holds submit permission on Attendance Request** (a Shift Supervisor role) | **all three — exactly what they see today; no `permitted_employees()` filter is applied** | **3** |

  The fourth row is the point (W1D-14). `_may_review()`
  (`attendance_correction.py:240-248`) tests `frappe.has_permission(REQUEST, "submit")`,
  not a role, so a tenant may give this queue to a Shift Supervisor. Applying
  `permitted_employees()` to them would return the empty set and kill a working flow
  silently — fail-closed, so not a leak, but the kind of break that gets repaired later by
  loosening the filter. The test must fail if their queue comes back empty.
- **AC-53 (009 design decision 1)** Attendance corrections are counted where they sit today —
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
  **This and AC-10 agree** now that §2's rules 1 to 5 need an Active Employee record: Asha
  reaches rule 6 and is never offered Time. In revision 2 they contradicted each other
  (BA finding 1).

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

- **AC-40 (W1D-15)** Before the swap, on a site where `frappe.conf` carries
  `portal_preview: 1`, loading the route `/hrms-employee-next` gives 200 for a System
  Manager, **403** for any other signed-in persona, and a redirect to `/login` for Guest.
- **AC-74 (W1D-15 / SEC-1)** **Flag off → 404.** With `portal_preview` absent or not `1`,
  the route returns **404 to a System Manager** — the page does not exist. The site flag
  is checked before the role, so the role check is the second of two locks and never the
  only one. A second check reads the repository: no production config file and no
  production compose environment sets `portal_preview`. This is why the preview page
  cannot appear on production at all, and it is what removed residual risk R5.
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
- **AC-67 (US-13, W1D-03)** For store HR and for an HR User, the Org settings page shows
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
- **AC-72 (US-14, SEC-13, W1D-13)** **The Team panel's no-manager list is narrowed.**
  Fixture: two stores and a head office, with one Active employee in each who has
  `reports_to` empty, and a store A HR person who has one direct report.

  | Caller | The Team panel shows |
  |---|---|
  | Store A's HR, one direct report | that report, plus store A's unassigned employee — **not** store B's and **not** the head-office one |
  | Company-wide HR | their reports plus all three unassigned employees |
  | Sandeep (manager, not HR) | his own reports only — no unassigned people, as today |
  | Store A's HR | the panel is **not empty**: their direct report is still there |

  Before this change, store A's HR saw all three unassigned employees. The L2 block is not
  changed — it narrows on its own because it reads from the narrowed list. **This narrows
  a live screen the moment it is released, not at the swap** (release gate 7).
- **AC-73 (SEC-4, security note N1)** `access.permitted_employee_filters(user)` **never
  returns an empty or partial filter dict.** Called as a plain employee, as a manager and
  as a Vendor User, it returns an explicit refusal — a sentinel the caller must handle, or
  filters that match nothing — and a query built from it returns **zero rows**. A direct
  assertion proves the return value is never `{}`. The reason is in one line: in Frappe an
  empty filter dict means every record, so a filter-shaped twin of `permitted_employees()`
  — which fails closed by returning an empty **set** (`access.py:237-267`) — would fail
  **open** if it copied that shape.

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
| d | Empty search says "your own team, your manager" | Says team only, per scope | Q-c (14 Sep) and **W1D-07** (revision 2 cited "decision 5", the corrections-queue one — wrong reference, corrected here) |
| e | Company › People for everyone | Needs `plan_org_structure` | Existing plan gate (appendix A §C) |

---

## 12. Out of scope for Wave 1

Home content and the "Needs you" rules; the Inbox list and decisions; who decides an
attendance fix (009 design decision 1 changes the routing in Wave 2); the check-in rule
for the owner (009 design decision 6); the Time, Pay, Growth, Team and People screens; the
staff directory and person sheet; "Who's off" (009 design decision 3); the grace wording
(009 design decision 7); peer feedback (009 design decision 4); the review's own copy of goals, KPI increments as
amounts, the reporting-line note on HR review steps, absence reasons, small-group
suppression, "Needs review" and data dates (01b §14 items 5–12); moving the existing
drawers into the shared sheet; Hindi and Punjabi for users; compression (slice 036);
cached script files (OPS-31, after the swap); the owner/HR screen redesign; the CXO
multi-company view; the mobile app's in-app mode; `set_my_language`; the org-chart
company scope (ALV-86); the wider leaver fix (ALV-87); named logins in place of the shared
`Administrator` and the tenant access log (ALV-93, W1D-18); `approve_kpi_update` and the
other company-scoped performance endpoints.

**One thing moved *into* scope in revision 3.** The Team **screen** stays out of Wave 1,
but the **query behind it** does not: `get_manager_dashboard`'s no-manager list is
narrowed (SEC-13, AC-72, W1D-13). The screen is unchanged; what it is allowed to read is
not. Nothing else about the Team panel is touched, and `get_manager_dashboard` still
refuses nobody at the door — a caller with no reports gets whatever the query returns for
them, and the Team gate stays in the browser. That is accepted for Wave 1 (BA note n4), so
a tester should not file it.

---

## 13. NFR numbers for this slice

Measured on the local copy in Chrome with **"Slow 4G" and 4× CPU slow-down**, cache off
(W1D-09, OPS-17) — not the undefined "3G".

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
(AC-48, W1D-12); labels 12 px or larger; 44 px targets on phones; 16 px inputs;
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
   on dev for 5 days** (W1D-11).
4. The previous production image tag is written down before the swap; rollback is a
   redeploy of it, about 10 minutes (OPS-14).
5. `ALV-86` (the org chart across companies and stores) — its state is recorded on the day
   of the swap. Wave 1 does not wait for it and does not work around it (W1D-08).
6. No pushes to dev in the hour after the production swap (OPS-19).
7. **Three scope changes take effect on release, not at the swap**, and the release note
   must say so (BA note n9, and the same principle applied to SEC-13):
   - **SEC-14** — the Active-only Employee lookup changes today's **live** bell and
     org-chart search. A leaver with an enabled login stops finding people and stops
     seeing approvals the moment this ships.
   - **SEC-13** — the Team panel's no-manager list narrows on today's **live** Team
     screen. A store HR person's panel gets shorter the moment this ships. Tell the two
     client tenants' HR before the release, or the shorter list reads as a bug.
   - **SEC-3, SEC-4 and SEC-5** — store HR's counts, bell list, search and corrections
     queue narrow on the live portal on release.
   None of these waits for the frame. All four are narrowings, so nothing new is exposed;
   what changes is what people are used to seeing.

---

## 17. Traceability

| Item | AC |
|---|---|
| SEC-1 | AC-40, AC-65, **AC-74** (flag off → 404) |
| SEC-2 | **AC-69 alone.** Revision 2 also pointed at AC-8, AC-21 and AC-26; none of them tests Guest or a 403, so the row was wrong (security note N6). AC-69's registry requires a Guest-refused case for every whitelisted function, which is the real mechanism |
| SEC-3 | AC-21, AC-50 |
| SEC-4 | AC-26, AC-56, **AC-73** (never an empty filter dict) |
| SEC-5 | AC-20 to AC-23, AC-51, AC-52, AC-53 |
| SEC-6 | AC-71 |
| SEC-7 | AC-17 |
| SEC-8 | AC-17 |
| SEC-9 | AC-18, AC-49 |
| SEC-10 | AC-58, AC-42 |
| SEC-11 | AC-25 |
| SEC-12 | AC-46 |
| **SEC-13** | **AC-72** (the Team panel's no-manager list) |
| SEC-14 | AC-68 |
| SEC-15 | AC-70 |
| PRIV-1 | AC-26 |
| PRIV-2 | AC-56 |
| PRIV-3 | AC-28, AC-57 |
| PRIV-4 | AC-23, AC-55 |
| PRIV-5 | AC-59 |
| PRIV-6 | AC-19 |
| PRIV-7 | **the table is now written** — `01c` §"PRIV-7 — the visibility table", 18 rows, checked by the test engineer against the built screens; AC-26, AC-27, AC-46, AC-72. Revision 2's row was circular (security note N5) |
| OPS-1 | release gate 1 |
| OPS-2, OPS-14 (was OPS-3) | AC-40, AC-41, AC-66; release gate 4 |
| OPS-4 | release gate 3 |
| OPS-5 | §14 |
| OPS-6, OPS-7 | AC-36, AC-37, AC-38 |
| OPS-8 | out of scope (W1D-12) |
| OPS-9, OPS-17 | §13, AC-24, AC-31 |
| OPS-10 | AC-40 |
| OPS-11 | AC-43 |
| OPS-12 | AC-65 |
| OPS-13 | AC-64 |
| OPS-16, OPS-19 | release gates 2 and 6 |
| OPS-15, OPS-18 | with the user (07 §3b) |
| 009 design decisions 1–7 (`../009-ess-portal-redesign/00f-decisions-2026-09-22.md`, first table) | 1: AC-53. 2: AC-10. 5: AC-43. 3, 4, 6, 7: §12 |
| 009 strategy decisions 1–14 (same file, second table) | 1: this revision. 2: AC-40, AC-41. **3: superseded by W1D-15** — the role check survives inside AC-40. 4: gate 3. 5: AC-26, AC-27. 6: AC-23. 7: AC-21, AC-26, AC-52. 8: AC-10, AC-47. 9: AC-17. 10: AC-43. 11: process. 12, 13: §12. 14: AC-18 |
| **W1D-01 to W1D-12** (`00g-decision-register.md`) — this replaces revision 2's "22 Sep review decisions 1–12", which named a list that existed in no file (security note N4) | 01: AC-1, AC-44. 02: §2, AC-10, AC-47. 03: AC-67. 04: AC-18, AC-49. 05: AC-52. 06: AC-68. 07: AC-26, AC-50. 08: gate 5. 09: §13. 10: gate 4. 11: gates 2 and 3. 12: AC-48 |
| **W1D-13 to W1D-18** (`00g-decision-register.md`) — Surbhi, 23 Sep | 13: AC-72, SEC-13. 14: AC-52 row 4. 15: AC-40, AC-74. 16: `01c` R6. 17: `01c` R3, R4. 18: `01c` A10, R7 — and `ALV-93` in §12 |
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
| `01c` written and reviewed | ✓ **revision 3** — reviewed twice; `06b` closed it with notes and every note is applied |
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
| Open questions owned, none blocks day 1 | ✓ two remain (the desk-link label, and the people list for HR without reports on a tenant without `plan_org_structure`); day 1 is still the split (US-10) |
| Frappe details verified in source | **Partly** — three items marked `[UNVERIFIED]` here and four in `00` §9, each checked before the step that needs it |
---

## 19. What changed in revision 3

Nothing was declined. Two things the reviews asked for are **not** closed and are named as
open questions instead — see the list at the end of this section.

### From the analyst re-review (`02c-ba-rereview.md`)

| Item | Change |
|---|---|
| Verdict 1 — persona precedence | §2: rules 1 to 5 apply only to a person with an **Active** Employee record; rows 4 and 5 say "Active"; a leaver falls to rule 6. AC-10 and AC-63 now agree |
| Verdict 2 — the Team-panel leak | **Surbhi chose to narrow it in Wave 1** (W1D-13). §2's false claim is replaced by the truth; SEC-13 and AC-72 do the work; §12 says the query is in scope although the screen is not |
| n1 | §4: Pay opens `#pay/expenses` without payroll; AC-44 says so |
| n2 | §3: `leave_encashment` and `advance_request` are not `plan_*` keys — absent means hidden, as today; AC-45 covers them |
| n3 | AC-18 reworded: no language row is built at all, so the oracle is "no row is rendered", not "the list is English" |
| n4 | §12: `get_manager_dashboard` still refuses no caller at the door; the Team gate stays in the browser; accepted for Wave 1 and written down so a tester does not file it |
| n5 | AC-11 gains five named bars, including the two goals-off ones |
| n6 | AC-20: "and the Inbox bottom-bar button **where the bar shows one**" |
| n7 | New story **US-18** gives AC-69, AC-70 and AC-71 a home |
| n8 | §17's SEC-2 row trimmed to AC-69 (same as security note N6) |
| n9 | Release gate 7: SEC-14, SEC-13 and the store-HR narrowings change the **live** portal on release, not at the swap |

### From the security re-review (`06b-security-rereview.md`)

| Item | Change |
|---|---|
| **N1** | `01c` SEC-4 and **AC-73**: the shared filter helper never returns an empty filter dict; explicit refusal; the reason written beside it |
| **N2** | **Surbhi chose option (a)** (W1D-14): the `permitted_employees()` filter applies to HR callers only. `01c` SEC-5 split by caller; AC-52 has a fourth case, the Shift Supervisor |
| **N3** | §5 and AC-51: capped list, uncapped count, the list's own "waiting" definition in the database, "showing the first 50 of 60", boundary test at cap + 1. The `50+` alternative declined with a reason |
| **N4** | `00g-decision-register.md` written; every citation repointed to `W1D-nn`; the two sets in `00f` cited by name |
| **N5** | `01c` PRIV-7's table written — 18 rows, six narrower, none wider |
| **N6** | §17's SEC-2 row now points at AC-69 alone |
| **N7** | `01c` SEC-6 no longer quotes a number of `ignore_permissions` uses |
| **N8** | SEC-13 exists, so the numbering has no gap |
| **R5** | **Surbhi took option 1** (W1D-15): the preview page is gated on `frappe.conf` `portal_preview: 1`, so it does not exist on production. AC-74 is the flag-off 404. R5 is **removed**, not accepted |
| **R3, R4, R6** | Owners and dates accepted as recommended (W1D-16, W1D-17); `01c`'s residual-risk table now has an owner and a date on every row |
| **R5 point 1** | A10 corrected: our staff are not System Managers on client tenants; the shared `Administrator` is `ALV-93` (W1D-18), out of scope |

### Still open

1. **The desk-link label**, and whether plain managers get it (open question 1). Not day 1.
2. **An HR person with no reports, on a tenant without `plan_org_structure`, has no people
   list at all** (open question 5, new). Not day 1, but it bites the day the frame is
   switched on for such a tenant.

---

## 20. Build size after revision 3

**13 to 15 build days, including tests.** It was 11 to 13 in revision 2
(`00-impact-analysis.md` revision note), and 10 to 12 in the first estimate. The shape of
the work has not changed; five decisions added real code.

| What grew | Days | Why |
|---|---|---|
| **New: the Team panel's no-manager query** (SEC-13, AC-72, W1D-13) | **+0.5** | The query change is about ten lines. The cost is the two-store fixture, the four cases in AC-72, and the fact that `hr_api.py` is a shared file this slice did not claim before. This is the half day Surbhi was told about, and it is honest — but see the note below |
| **The Inbox counts** (N3 capped count, W1D-14 split by caller) | **+0.75** | The bigger of the two. The count must use the list's own "waiting" rule in the database, the screen needs the "showing the first 50 of 60" line, the boundary fixture needs 51 items, and the corrections part now has two code paths and four test callers instead of one |
| **The shared scope helper** (SEC-4, N1) | **+0.25** | The refusal value, every caller handling it, and the "never `{}`" assertion |
| **The preview page** (SEC-1, W1D-15) | **+0.25** | A few lines in `get_context`, the flag-off test, the repository check that no production config sets the flag, and setting `portal_preview: 1` on the local bench and dev |
| Documents — the decision register, PRIV-7's table, the wording fixes | 0 | Done in this revision; no build cost |
| **Total added** | **+1.75** | 11–13 → **13–15** |

**What did not grow:** day 1 (the page split, US-10), the frame includes, the bottom bar,
the routes, the search sheet, the profile sheet, the five states, and the swap commit. The
critical path is unchanged, and the page-split freeze is still the thing to schedule
first.

**One thing to watch, said plainly.** SEC-13 puts `alvoraa_portal/alvoraa_portal/hr_api.py`
into this slice's claimed files. That file is one of the busiest in the repository and
other sessions edit it. The change is small and self-contained — one filter on one
`frappe.get_all` — so it should be made as **its own commit, early**, rather than inside
the frame work, and the work board must show the claim before the first edit.

---

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | **Open.** The desk link: keep the server's labels ("Switch to Admin", "Switch to HR Core") or the prototype's "Switch to the full desk"? Should a plain manager get it at all? | Surbhi | AC-17, difference (a). Not day 1 |
| 2 | *Closed 23 Sep:* R3, R4 and R6 owners and dates — **accepted as recommended** (W1D-16, W1D-17) | — | — |
| 3 | *Closed 23 Sep:* the preview page with real data — **moot, the page does not exist on production** (W1D-15) | — | — |
| 4 | *Closed 22 Sep:* re-review of revision 2 — `02c-ba-rereview.md`, closed with notes, all applied here | — | — |
| 5 | **Open, new (BA re-review question 2).** An HR person with no direct reports loses the Team panel (W1D-02) and is pointed at Company › People instead — but People needs `plan_org_structure`. **On a tenant without that plan they end up with no people list at all.** Accept that, or give them People regardless? | Surbhi | §3's matrix row. Not day 1; it bites on the day the frame is switched on for a tenant without the plan |

## Assumptions

- `[ASSUMPTION]` `/me` is the right target for My account; checked on the bench before step 2.
- `[ASSUMPTION]` Field names on Shift Request and Attendance Request match what §5 needs.
- `[ASSUMPTION]` The prototype's `bnavItems()` is the approved behaviour for the Company
  button (it opens HR analytics).
- `[ASSUMPTION]` Frappe's `"not in"` filter wraps the column in `ifnull()`, so a NULL
  `alvoraa_review_status` counts as waiting (§5, AC-51). **I could not verify this: the
  Frappe source lives in the bench container, not in this repository.** §5 carries the
  fallback — read the ids and apply the same Python filter — if the check on the bench
  says otherwise. Confirmed before step 4.
- `[ASSUMPTION]` `frappe.conf` is readable in a website page's `get_context` (AC-74). The
  existing `alvoraa_control_plane` check in SEC-8 already relies on this; still to be run
  once on the bench.

## Handoff note

To the business analyst: the four blockers are answered in §1 (Pay), §2 (the persona
table, with the consequence stated), §8 AC-18 (offered languages) and §2's fallback order.
The one thing I did **not** do is invent an answer for difference (a) — the desk link's
label and whether plain managers get it. It needs the user's word, and until then the
build follows the server's current behaviour.

To the test engineer: the three structural tests the security review asked for are AC-69
(registry), AC-51 (count matches list, fixtures made the way users make them) and AC-70
(no module-level state). Revision 3 adds three more that are easy to get wrong:
**AC-73** — the assertion is that the helper never returns `{}`, not merely that a query
comes back empty; **AC-52 row 4** — the test must **fail** if the Shift Supervisor's queue
is empty, which is the opposite of the other three rows; and **AC-74** — the flag-off case
expects **404**, not 403, and must run with `portal_preview` genuinely absent rather than
set to 0.
