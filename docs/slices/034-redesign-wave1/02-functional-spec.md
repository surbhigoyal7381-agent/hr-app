---
slice: 034-redesign-wave1
artifact: 02-functional-spec
author: hrms-fullstack-engineer, revised after the analyst and security re-reviews
date: 2026-09-23
revision: 5 (2026-09-24: §12 corrected — OPS-31 was built before the swap, not after; release gate 9 added for the assets it created. No acceptance check changed.)
status: draft, revised — ready to build once the strategy gate is passed
inputs: [02c-ba-rereview.md, 06b-security-rereview.md, 02b-ba-review.md, 06-security-review-of-requirements.md, 07-devops-inputs.md §4 and §3b, 01c-security-privacy-requirements.md (revision 3), 00-impact-analysis.md, 00g-decision-register.md, ../009-ess-portal-redesign/01b-ux-design.md, ../009-ess-portal-redesign/appendix-a-frame.md, prototype-v2.html]
brief: there is no `01` for slice 034. The approved brief is `../009-ess-portal-redesign/00-assessment-and-plan.md` (Wave 1) plus the decisions in `00g-decision-register.md`.
---

# Wave 1 frame — functional spec

**Revision 4.** Surbhi's three further decisions of 23 September are written in:
**W1D-19** (the desk link is for HR and System Manager only, with the server's labels),
**W1D-20** (for an HR user the Team screen follows HR scope, replacing W1D-13) and
**W1D-21** (the staff list gets its own feature switch, split from the org chart).
**Both remaining open questions are closed** — 1 by W1D-19, and 5 by W1D-20 and W1D-21
together. One new open question is raised in their place (question 6). What changed is in
§19, and the build size is restated in §20.

**Revision 3.** The analyst's two corrections and the security review's three must-fixes
are applied, and Surbhi's six decisions of 23 September are written in.

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
| Desk switch target | `module_access.get_switch_target:1099` | **Reuse, unchanged** — HR and System Manager only, with the server's labels (W1D-19). The prototype was wrong, not the code |
| Scope helpers | `access.permitted_employees:237`, `permitted_branches:217` | **Extend:** one shared filter helper (SEC-4) |
| People search | `alvoraa_org_structure.api.search_people:559`, `_search_scope:577` | **Extend:** store narrowing, Active-only caller, wildcards escaped |
| Approvals scope | `goals_api._pending_approvals_scope:1162` | **Extend:** `permitted_employees` + own reports |
| The Team screen's people, for an HR caller | `hr_api.get_manager_dashboard:291-307` — direct reports, plus (for HR Manager / HR User only) every Active employee with `reports_to` not set, `ignore_permissions=True`, no company or branch filter | **Extend:** build the HR branch from `access.permitted_employees()` and **delete** the no-manager block (W1D-20, SEC-13). A caller who is not HR is unchanged |
| A plain staff list for HR | one flag, `plan_org_structure`, gates the org chart **and** the People screen (`hrms-employee.html:7813`) | **Extend:** one new `opt_in` key in `subscription.FEATURES`, read the existing way through `get_available_features`; the org chart keeps `plan_org_structure` (W1D-21, SEC-16) |
| Corrections queue | `attendance_correction.to_review:722` | **Extend:** same scope as the count, **for an HR caller only** (W1D-05, W1D-14) |
| Policy acknowledgements | `alvoraa_policy_library.access.readable_policy_names:163` | **Reuse** |
| Counts in one place | nothing | **Build:** `inbox_api` |
| Menu, bottom bar, routes, sheet, states | hand-written sidebar `hrms-employee.html:2345-2440` | **Build** in the frame includes |
| Pay pages | `panel-finances:2781` holds Salary Slips, Expenses, Leave Encashment; `expenses` is a **required** feature on every plan (`subscription.py:83-90`) | **Extend:** hide the salary parts without payroll, keep the rest (W1D-01) |
| The staff list screen itself | — | **Build** a plain searchable list — name, job title, department, photo — behind the new switch (W1D-21) |
| Person sheet, Inbox list, feedback | — | **Out of Wave 1** (§12) |

No new DocType, no custom field, no patch, no migration. The staff-list switch is a key in
a Python registry that already exists, not a new setting anywhere.

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
| 1 | `is_hr` **and** `has_reports` | a person with an **Active** Employee record | Yes — their **HR scope** (W1D-20), which contains their own reports | Home · Inbox · Company · **Team** |
| 2 | `is_hr` **and not** `has_reports` | a person with an **Active** Employee record | **Yes** — their HR scope (W1D-20, changed in revision 4; it was "No") | Home · Inbox · Company · **Team** (was Time) |
| 3 | `has_reports`, not HR | a person with an **Active** Employee record | Yes | Home · **Team** · Inbox · Time |
| 4 | **Active** employee, tenant has `plan_payroll` | — | No | Home · Time · **Pay** · Goals |
| 5 | **Active** employee, no `plan_payroll` | — | No | Home · Time · **Inbox** · Goals |
| 6 | **No Active Employee record** — no record at all (platform operator), or one that is Left, Inactive or Suspended | — | No | Home · Inbox · Company (fewer buttons if fewer are allowed) |

A leaver whose login is still enabled (AC-68) therefore gets rule 6's bar, and the
endpoints behind it return his own empty parts — the same shape Asha gets. That is
consistent with SEC-14, which gives him an empty search and zero approvals.

**Changed in revision 4 (W1D-20).** Revision 3 said an HR user with no direct reports
**loses** the Team panel. That is reversed: they keep a Team screen, and it shows **their
HR scope** — their companies, or their branch if they carry a Branch permission. What is
gone is the old stand-in behaviour, which showed them the people at the top of the company
(for store HR, head office — outside their store). So rules 1 and 2 now give the same Team
group, and rule 2's fourth bottom-bar button changes from Time to Team.

The rest of W1D-02 stands: the bars are still decided by `has_reports` and `is_hr`, and
today's `is_manager` stand-in rule is still not used for anything.

**One consequence, raised not assumed.** `is_hr` includes **System Manager**, and
`permitted_employees()` gives a System Manager everyone — so a tenant System Manager with
an Employee record gets a Team screen listing the whole tenant, where today they get their
own direct reports. No new data (the desk already lists every employee for them), but it is
a wider screen, and this slice's rule is that nothing widens by accident. It is
**open question 6**, and it is now **closed as decided (W1D-22, 24 Sep)**: it stays, and `01c` PRIV-7 keeps the row that records it as the one screen that widens.

**How the leak is actually closed (W1D-20, replacing W1D-13).** Hiding a menu entry was
never a data control, and neither is a filter on a list that should not be built that way.
The Team screen's data comes from `get_manager_dashboard` (`hr_api.py:291-307`), which adds
every Active employee with no manager — `ignore_permissions=True`, no company or branch
filter — to anyone holding HR Manager or HR User. **That block is deleted.** For an HR
caller the screen is built from `access.permitted_employees()` instead, so a store's HR
person sees their store and nothing else, and people with no manager still appear because
they are inside that scope. SEC-13 and AC-72 carry it, rewritten in revision 4.

**A caller who is not HR is unchanged, and never leaked.** The deleted block tested
`{"HR Manager", "HR User"}` against the caller's roles at line 296, so a plain manager
never reached it: their Team screen was, and stays, their own direct reports plus the L2
rows read from them. I checked that line again rather than assuming the leak was gone with
the block.

**Where an HR person with no reports finds people:** on their own Team screen, which is now
their HR scope — and, where the tenant has the new staff-list switch on, on the searchable
staff list as well (W1D-21, §3). The org chart stays behind `plan_org_structure`. **This
closes open question 5:** an HR person is never left with no way to see their people,
whatever the two plan flags say.

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
| Team | — | ✓ own reports | ✓ **their HR scope** — their permitted companies, with or without direct reports (SEC-13, W1D-20) | ✓ **their store only** (SEC-13, W1D-20) | ✓ HR scope | ✓ everyone in the tenant — **decided, W1D-22**; the one row that gets wider on release | — (no Employee record) | — |
| Company › People (the **org chart**) | ✓ where `plan_org_structure` | same | same | same | same | same | same | ✓ where the plan allows |
| Company › Staff list (**new**, W1D-21) | — | — | ✓ where the staff-list switch is on, scoped to their permitted companies | ✓ where it is on, **their store only** | ✓ | ✓ | ✓ | — |
| Company › HR analytics, Data to review | — | — | ✓ where `plan_analytics` is not `false` | same | same | ✓ (a System Manager is `is_hr`) | ✓ | ✓ |
| Company › Reviews (HR) | — | — | ✓ where `goals` | same | same | ✓ | ✓ | ✓ |
| Company › Policies | ✓ where `plan_policy_library` | same | same | same | same | same | same | ✓ |
| Company › Org settings | — | — | ✓ read and save | ✓ **read only** — Save hidden (W1D-03) | ✓ | ✓ | ✓ | ✓ read only |
| Search finds | self and below | self and below | permitted companies | **own store plus own line** | permitted companies | everyone | everyone | nobody |
| Switch to desk (W1D-19) | — | **—** (a plain manager gets no link at all) | "Switch to HR Core" → `/app/hr` | "Switch to HR Core" → `/app/hr` | "Switch to Admin" if System Manager, else "Switch to HR Core" | "Switch to Admin" → `/app` | "Switch to Admin" → `/app` | per role |
| Tenant admin | — | — | — | — | — | **—** | ✓ | only on the control plane |
| Preview page (only where `frappe.conf` sets `portal_preview: 1` — local and dev, never production; **404 for everyone elsewhere**, W1D-15) | 403 | 403 | 403 | 403 | 403 unless System Manager | ✓ | ✓ | ✓ if System Manager |

**Missing plan keys.** When entitlement cannot be read, every `plan_*` key is absent.
The rule for every flag: **absent means "not answered yet", and the item is shown**
(`!== false`), except `plan_payroll`, where absent hides only the salary parts and leaves
the rest of Pay — so nobody is shown payslips a tenant did not buy. `goals` is a plain
boolean (installed **and** plan) and absent means hidden.

**The staff-list switch does not follow the "absent means show" rule either.** It is an
`opt_in` feature, so absent means the tenant has not been given it — and when the
entitlement read fails, every `plan_*` key is absent. Showing it then would hand out an
unsold screen because a read failed, so **absent means hidden**, like `goals`. That is
fail-closed and it is the point of the switch (W1D-21, SEC-16).

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
| People (the org chart) | `#company/people` | `org-chart` |
| Staff list | `#company/staff` | `staff-list` (new, W1D-21) |
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
| **US-19** | As Priya (store HR with no direct reports), I want a plain searchable list of my store's people, so that I can find someone without an org chart and without a plan I do not have. | staff list, Team | 8 |

**US-19 is new in revision 4** (W1D-20 and W1D-21). It carries AC-72's "not empty" cases
and AC-76. **AC-75** (the desk link) belongs to US-5, where the profile sheet lives.

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
  absent, People (the org chart) is shown; **given the staff-list key absent, the staff
  list is hidden** — an opt-in feature must not appear because an entitlement read failed
  (W1D-21). **Given `leave_encashment` absent, the Leave encashment tab is
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
- **AC-47** *(changed in revision 4, W1D-20)* `has_reports` is true only when an Active
  Employee has `reports_to` set to this person, and today's `is_manager` stand-in rule is
  not used. **An HR user with nobody reporting to them still gets the Team group and the
  Team button** — their screen is their HR scope, not their reports (W1D-20). For a person
  who is **not** HR, `has_reports` false still means no Team group and no Team button.
- **AC-11** When a bar page is not allowed, the next page in the order Home → Inbox → Time
  → Goals → Pay → Team → Company takes its place, skipping pages already in the bar; with
  fewer than four allowed, the bar is shorter; More is always last. **Named cases** (BA
  note n5 — goals-off tenants exist, so these are fixtures, not a generic rule):

  | Persona and tenant | Missing | Bar |
  |---|---|---|
  | Rahul, payroll on, goals app off | Goals | Home · Time · Pay · **Inbox** |
  | Rahul, payroll off, goals app off | Goals and salary | Home · Time · Inbox · **Pay** (Pay exists — Expenses) |
  | Asha, no Employee record | Time, Goals, Pay, Team | Home · Inbox · Company — **three buttons** |
  | Priya, store HR, no reports | — | Home · Inbox · Company · **Team** (was Time — W1D-20) |
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
  no Employee record); My account opens `/me`; the desk link appears only when
  `get_switch_target` returns a target, with the server's label; Tenant admin appears only
  for a System Manager on a site where `alvoraa_control_plane` is set — tested on both
  site types.
- **AC-75 (SEC-7, W1D-19)** **The desk link, settled.** Four cases, and the label strings
  are asserted exactly:

  | Caller | Link |
  |---|---|
  | HR Manager or HR User, not a System Manager | **"Switch to HR Core"** → `/app/hr` |
  | System Manager | **"Switch to Admin"** → `/app` |
  | Both | **"Switch to Admin"** — `ADMIN_ROLES` is tested first |
  | **Sandeep — a plain manager with 19 direct reports, no HR role, not a System Manager** | **no link at all**: `get_frame` carries no switch target and the profile sheet renders no link row |

  The prototype's "Switch to the full desk" appears nowhere. This is the code's existing
  behaviour (`module_access.py:1099-1115`); the test is what is new, so that nobody moves
  the code towards the prototype later (W1D-19).
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

### US-12 to US-19 — the rest

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
- **AC-71 (SEC-6 — reworded after review finding F7, 2026-09-24)** Two halves, because
  the first one alone was claiming more than it proved.
  (a) `frame_api.py`, `inbox_api.py` and `staff_api.py` contain no `ignore_permissions`,
  and the edited bodies of `_pending_approvals_scope`, `_search_scope` and the new
  `permitted_employee_filters` gain none.
  (b) Every **other** call in those files that gets past Frappe's permission layer —
  `frappe.get_all`, `frappe.db.count`, `frappe.db.sql` and their relatives — is named
  and counted in the check, with the reason it is safe. Adding one turns the check red
  until somebody writes it down. **What this proves is "no undeclared bypass", not "no
  bypass".** The calls that exist are safe because the scope filter around them is the
  shared one and fails closed; what they do not honour is any extra narrowing a tenant
  has configured through User Permissions.
- **AC-72 (US-14, SEC-13, W1D-20 — rewritten in revision 4; it was W1D-13's narrowed
  orphan query)** **For an HR caller the Team screen is built from `permitted_employees()`.**
  Fixture: two stores and a head office; in each place one Active employee whose
  `reports_to` is empty and one whose manager is set; a store A HR person with one direct
  report; a store A HR person with **no** direct reports; and one **Left** employee in
  store A.

  | Caller | The Team screen shows |
  |---|---|
  | Store A's HR, one direct report | **store A, and only store A** — their report, store A's unassigned employee and store A's other Active people. **Not** store B, **not** head office |
  | Store A's HR, **no** direct reports | the same store A list. The screen exists and is **not empty** — this is what W1D-20 gives back (open question 5) |
  | Company-wide HR | everyone Active in their permitted companies, capped at 50 with the true total shown |
  | Sandeep (manager, not HR) | his own direct reports and their L2 rows — **unchanged**, and no unassigned people, exactly as today |
  | Store A's HR | the **Left** employee in store A does **not** appear — `permitted_employees()` returns every status, so `status = "Active"` must survive on the Team query |
  | Any caller | their own record is not in the list, as today |

  A static check proves **no "employees with no manager" query survives in `hr_api.py`** —
  the block is deleted, not left behind a condition. The L2 block is not changed; it
  follows the new list. **This changes a live screen the moment it is released, not at the
  swap** (release gate 7).
- **AC-76 (SEC-16, W1D-21)** **The staff list has its own switch, and the org chart keeps
  `plan_org_structure`.**

  | Case | What must happen |
  |---|---|
  | Tenant with the staff-list key on, HR caller | The Staff list entry is in the Company group and `#company/staff` opens a searchable list of name, job title, department and photo |
  | Store A's HR, key on | Their list is **store A only**; a head-office name is not found (an employee with no branch is outside every store) |
  | Key on, `plan_org_structure` **off** | The staff list works; **the org chart entry is not shown** — the two flags are independent |
  | Key **off**, `plan_org_structure` on | The org chart works; **no staff-list entry**, and typing `#company/staff` shows the §6 no-permission sentence — never a blank list and never an error |
  | Key off, HR caller calls the staff-list endpoint by hand | **Refused on the server** (SEC-16). Hiding the menu entry is not the control |
  | Key off, HR person with no direct reports | They still have their **Team screen** (AC-72), so they are never left with no way to see their people |
  | Plan bundles | A test that the new key is in **no** plan bundle and in `OPT_IN`, so shipping it grants it to nobody: `plan_features("enterprise")` does not contain it, and a site with no `features` recorded does not get it |
  | Payload | The list's keys are exactly PRIV-2's set, Active employees only |
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
| HR without reports | AC-31 | AC-23 | AC-30 (`#company/staff` where the switch is off) — **no longer `#team`**: they have a Team screen now (W1D-20) | AC-32 | AC-33 |
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
| Store HR who also holds System Manager | Not narrowed — System Manager sees everyone, on the Team screen and the staff list alike. Intended; stated so a tester does not file it |
| HR user with no direct reports | Team screen present, showing their HR scope (AC-72). Their own name is not on it |
| Tenant System Manager with an Employee record | Team screen is the whole tenant. No new data — the desk already lists everyone for them — but wider than today's screen. **Decided: it stays (W1D-22, 24 Sep)**, and PRIV-7 keeps the row |
| Tenant where **both** `plan_org_structure` and the staff-list switch are off | HR has no org chart and no staff list, but still has the Team screen. No dead menu entry, and a typed address shows the no-permission line (AC-76) |
| A plain manager looking for the desk link | There is none, and there never was one for them in the code (AC-75, W1D-19). Stated so a tester does not file it against the prototype |
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
| a | "Switch to the full desk" for every manager | Only when the server returns a target — **HR and System Manager only, never a plain manager** — with the server's label, "Switch to Admin" or "Switch to HR Core" | **Closed by W1D-19.** The prototype was wrong, not the code; the prototype is not changed, and the register says why so nobody moves the code towards it later. AC-75 |
| b | Tenant admin for the owner | Control-plane operators only | Decision 9 |
| c | Language row always | Hidden until a translation ships | Decisions 4 and 14 |
| d | Empty search says "your own team, your manager" | Says team only, per scope | Q-c (14 Sep) and **W1D-07** (revision 2 cited "decision 5", the corrections-queue one — wrong reference, corrected here) |
| e | Company › People for everyone | **Two entries now.** The **org chart** keeps `plan_org_structure`; a plain **staff list** has its own switch, on for both client tenants | **W1D-21.** AC-76. The commercial question — free or paid, and on which plans — is deliberately left open and settled by configuration later |

---

## 12. Out of scope for Wave 1

Home content and the "Needs you" rules; the Inbox list and decisions; who decides an
attendance fix (009 design decision 1 changes the routing in Wave 2); the check-in rule
for the owner (009 design decision 6); the Time, Pay, Growth and org-chart screens; the person sheet; "Who's off" (009 design decision 3); the grace wording
(009 design decision 7); peer feedback (009 design decision 4); the review's own copy of goals, KPI increments as
amounts, the reporting-line note on HR review steps, absence reasons, small-group
suppression, "Needs review" and data dates (01b §14 items 5–12); moving the existing
drawers into the shared sheet; Hindi and Punjabi for users; compression (slice 036);
the owner/HR screen redesign; the CXO
multi-company view; the mobile app's in-app mode; `set_my_language`; the org-chart
company scope (ALV-86); the wider leaver fix (ALV-87); named logins in place of the shared
`Administrator` and the tenant access log (ALV-93, W1D-18); `approve_kpi_update` and the
other company-scoped performance endpoints.

**Three things moved *into* scope. Two were restated for revision 4; the third is
recorded here in revision 5.**

**1. The Team screen's query** (SEC-13, AC-72, W1D-20 — this replaces revision 3's W1D-13
wording). The Team **screen's look** stays out of Wave 1; **what it is allowed to read does
not**. For an HR caller `get_manager_dashboard` is rebuilt on `permitted_employees()` and
the no-manager block is deleted. Two visible changes come with it, because the screen
renders what the query returns: the list is **capped at 50 with the true total shown**
(company-wide HR could otherwise get a thousand cards), and an HR user with no direct
reports now has a screen where revision 3 said they would have none. `get_manager_dashboard`
still refuses nobody at the door — the Team gate stays in the browser, accepted for Wave 1
(BA note n4), so a tester should not file it.

**2. A plain staff list and its switch** (SEC-16, AC-76, W1D-21). New in revision 4. The
**org chart** stays where it is, on `plan_org_structure`, with `ALV-86` still open against
it. What Wave 1 builds is a searchable list of people — name, job title, department, photo
— scoped by `permitted_employees()` from its first line, behind its own `opt_in` key in the
existing registry. The **person sheet** is still out of scope: a row opens what it opens
today.

**3. Cached style and script files** (OPS-31). **Amended 2026-09-24 — this line used to
say the opposite.** Revision 4's list put OPS-31 out of Wave 1, "after the swap". It was
built *before* the swap instead, on the instruction given on 24 September and on the
recommendation the engineer made after measuring the template-cache cliff. The spec and
the code disagreed until this amendment; they agree now.

Why it had to come first, in one line: Frappe compiles at most 32 Jinja templates per
worker, this page's chain already used about 28 of them, and the styles and script were
three of those. Splitting the markup into one file per area — US-10, the thing Waves 2
to 5 depend on — was unaffordable until they stopped being templates. Moving them out
also cut the HTML sent on every visit from 1,071,272 bytes to 209,574 (−80 %) and the
server render by about 22 %.

What this changes elsewhere in this document: nothing in §8 — AC-64 was always the check
on the split, and it passes at −4 %. §16's release gate 1 (compression, slice 036) is
**not** replaced by this: gzip on `/assets/` is already on in nginx, so the script now
arrives compressed, but the remaining HTML and the 2.5 s "Home usable" budget still need
036. §13's own line is unchanged. The one new obligation is §16's gate 9 below, because
the portal's styles and script are now fetched from `/assets/` rather than carried in the
page.

---

## 13. NFR numbers for this slice

Measured on the local copy in Chrome with **"Slow 4G" and 4× CPU slow-down**, cache off
(W1D-09, OPS-17) — not the undefined "3G".

| What | Number |
|---|---|
| Shell and skeleton painted | ≤ 300 ms, median of 5 loads |
| Home usable | ≤ 2.5 s at p95 of 20 loads — **only reachable once slice 036's compression is live**; recorded before and after |
| `get_frame`, `get_nav_counts` | ≤ 15 queries; ≤ 500 ms p95 over 20 warm calls, as company-wide HR at 1,000 employees |
| Team screen for company-wide HR at 1,000 employees (W1D-20) | **capped at 50 rows**, true total shown; ≤ 8 queries; ≤ 700 ms p95 over 20 warm calls. Measured before and after the rebuild — today's version returns direct reports plus every unassigned employee, so the cap is what keeps this bounded |
| Staff list, first page (W1D-21) | 12 asked for, 50 maximum, ≤ 4 queries, ≤ 400 ms p95 — the same budget as people search |
| Start-up calls | 2, with no timer |
| Server time for the page after the split | within 10 % of before (AC-64) |
| Accessibility | WCAG 2.2 AA; 390 px; 200 % zoom |

---

## 14. Migration, audit, localisation

**Migration:** none. No schema change, no data change, no patch, and no `bench migrate`,
`bench build` or cache clear (07 §4.2). **One configuration action, not a migration:** the
staff-list key has to be ticked on for the two client tenants, which writes the key into
each tenant's own `features` list (W1D-21, release gate 8). It is a dev-stage and
production-stage action and needs Surbhi's word on the day, like every other tenant change.

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
   - **SEC-13** — the **live** Team screen changes for every HR user the moment this ships,
     not at the swap (W1D-20). A store HR person's screen becomes their store: shorter in
     one direction (no head office) and longer in another (their store's people who do have
     a manager). A company-wide HR user's becomes their companies, capped at 50 with the
     total shown. **Tell the two client tenants' HR before the release**, or a screen that
     has changed in both directions reads as a bug. A manager who is not HR sees no change
     at all.
   - **SEC-3, SEC-4 and SEC-5** — store HR's counts, bell list, search and corrections
     queue narrow on the live portal on release.
   Not all of these are narrowings any more. SEC-3, SEC-4, SEC-5 and SEC-14 are.
   **SEC-13 is a re-scoping**: narrower for store HR in the direction that mattered (head
   office is gone) and, on the same screen, longer for anyone whose scope holds people they
   were not shown before — their own store's or company's staff. Nothing outside the
   caller's `permitted_employees()` scope is exposed in either direction, but "nothing new
   is exposed" is no longer the whole sentence, and the release note must say what it says
   above.
8. **The staff-list key is ticked on for `dtc` and `aahr`** after the release that carries
   it, and on the local PP Jewellers copy for testing (W1D-21). Until it is ticked the
   screen is invisible, which is safe but is not what was decided. It is a tenant
   configuration change, so it waits for Surbhi's word on the day.
9. **The portal's styles and script are fetched and checked after every deploy**
   (OPS-35, OPS-36; new in revision 5, because OPS-31 moved into scope — §12 item 3).
   The page no longer carries its own CSS and JavaScript; it loads three files from
   `/assets/`. If that path serves the wrong thing the portal is a blank page that does
   nothing, which is a worse failure than the old inline copy. Two checks, both about a
   minute's work, and both **before anyone looks at the page**:
   - Fetch `/assets/alvoraa_portal/css/ess/frame.css`, `/assets/alvoraa_portal/css/ess/panels.css`
     and `/assets/alvoraa_portal/js/ess/portal.js`. Each must answer **200** with a
     **non-zero content length**. A 404 on the script is the whole portal gone.
   - Confirm **`sites/assets/assets.json`'s modified time moved** with the deploy. That
     file is the version stamp; if it did not move, browsers keep the previous release's
     script and the deploy has not really landed.
   These run on dev and again on production. They are release gates, not acceptance
   checks: they test the delivery, not the code.


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
| SEC-7 | AC-17, **AC-75** (HR and System Manager only; no link for a plain manager; the server's labels) |
| SEC-8 | AC-17 |
| SEC-9 | AC-18, AC-49 |
| SEC-10 | AC-58, AC-42 |
| SEC-11 | AC-25 |
| SEC-12 | AC-46 |
| **SEC-13** | **AC-72** (the Team screen follows HR scope — rewritten in revision 4, W1D-20) |
| SEC-14 | AC-68 |
| SEC-15 | AC-70 |
| **SEC-16** | **AC-76** (the staff list's own switch, server-side, scoped, capped) |
| PRIV-1 | AC-26 |
| PRIV-2 | AC-56 |
| PRIV-3 | AC-28, AC-57 |
| PRIV-4 | AC-23, AC-55 |
| PRIV-5 | AC-59 |
| PRIV-6 | AC-19 |
| PRIV-7 | **the table is now written** — `01c` §"PRIV-7 — the visibility table", checked by the test engineer against the built screens; AC-26, AC-27, AC-46, AC-72, AC-76. **Revision 4 adds three rows and one of them is the table's only *wider* row** — a tenant System Manager's Team screen (open question 6). Revision 2's row was circular (security note N5) |
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
| **W1D-13 to W1D-18** (`00g-decision-register.md`) — Surbhi, 23 Sep | **13: replaced by W1D-20** — not kept alongside it. 14: AC-52 row 4. 15: AC-40, AC-74. 16: `01c` R6. 17: `01c` R3, R4. 18: `01c` A10, R7 — and `ALV-93` in §12 |
| **W1D-19 to W1D-21** (`00g-decision-register.md`) — Surbhi, 23 Sep, later the same day | **19:** AC-75, AC-17, SEC-7, §11 row (a) — closes open question 1. **20:** AC-72, SEC-13, §2 rules 1 and 2, AC-47, AC-11's Priya row, §3's Team row, §13's Team row, release gate 7. **21:** AC-76, SEC-16, AC-45, §3's two People rows, §4's `#company/staff`, release gate 8, US-19. **20 and 21 together close open question 5** |
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
| Open questions owned, none blocks day 1 | ✓ **all closed.** The two from revision 3 by W1D-19 and by W1D-20 with W1D-21; question 6 — a tenant System Manager's Team screen — by **W1D-22 on 24 Sep**, as decided |
| Frappe details verified in source | **Partly** — three items marked `[UNVERIFIED]` here and four in `00` §9, each checked before the step that needs it |
---

## 19. What changed in revision 4

Three decisions, taken later on 23 September. Nothing was declined. One thing they
**replaced** rather than added to, and one new open question came out of them.

| Decision | Change |
|---|---|
| **W1D-19** — the desk link | §11 row (a) **closed**; AC-17 reworded and **AC-75** added, with the plain manager as a named case and the label strings asserted; §3's switch row and §1's gap row say HR and System Manager only; `01c` SEC-7 rewritten. **No code changes** — the code was already right and the prototype was wrong; the register says so in writing |
| **W1D-20** — the Team screen follows HR scope | **Replaces W1D-13.** §2's rules 1 and 2 both give the Team group, and rule 2's fourth button becomes Team; the "loses the Team panel" consequence is reversed; **AC-72 rewritten** (six cases, including "not empty", "no leaver" and a static check that the no-manager query is gone); AC-47 and AC-11's Priya row follow; §3's Team row rewritten; §12 restated; §13 gains a capped Team-screen budget; release gate 7 rewritten; `01c` SEC-13 rewritten with A11, A13 and three PRIV-7 rows |
| **W1D-21** — the staff list's own switch | New **AC-76** and `01c` **SEC-16**; §1, §3 and §4 gain the staff list beside the org chart; AC-45 says an absent key means hidden for an opt-in feature; new **US-19**; release gate 8 for the tenant tick; §14 names the tick as a configuration action, not a migration |
| Both 20 and 21 | **Open question 5 is closed**: an HR person with no direct reports has a Team screen, and a staff list where the switch is on |
| New | **Open question 6**: `is_hr` includes System Manager, so a tenant System Manager's Team screen becomes the whole tenant. No new data, but a wider screen. Raised, not assumed |

## 19b. What changed in revision 3

Nothing was declined. Two things the reviews asked for are **not** closed and are named as
open questions instead — see the list at the end of this section.

### From the analyst re-review (`02c-ba-rereview.md`)

| Item | Change |
|---|---|
| Verdict 1 — persona precedence | §2: rules 1 to 5 apply only to a person with an **Active** Employee record; rows 4 and 5 say "Active"; a leaver falls to rule 6. AC-10 and AC-63 now agree |
| Verdict 2 — the Team-panel leak *(superseded in revision 4 by W1D-20 — the list is not narrowed, it is gone)* | **Surbhi chose to narrow it in Wave 1** (W1D-13). §2's false claim is replaced by the truth; SEC-13 and AC-72 do the work; §12 says the query is in scope although the screen is not |
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

### Still open after revision 3 — **both now closed in revision 4**

1. ~~The desk-link label, and whether plain managers get it~~ — **closed by W1D-19**.
2. ~~An HR person with no reports, on a tenant without `plan_org_structure`, has no people
   list at all~~ — **closed by W1D-20 and W1D-21 together**.

---

## 20. Build size after revision 4

**15 to 18 build days, including tests.** It was 13 to 15 in revision 3, 11 to 13 in
revision 2, and 10 to 12 in the first estimate. Day 1 and the critical path are unchanged.

**What moved it.** W1D-20 replaced W1D-13's half day with about a day and a quarter, and
W1D-21 added a screen that was out of scope before. W1D-19 costs a test.

| What changed in revision 4 | Days | Why |
|---|---|---|
| **W1D-19 — the desk link** | **+0.25** | No code: `get_switch_target` already does this. The cost is AC-75's four cases and the register entry that keeps somebody from "fixing" the code towards the prototype |
| **W1D-20 — the Team screen follows HR scope** (replaces W1D-13's +0.5) | **+1.0 to +1.25, in place of +0.5 — a net +0.5 to +0.75** | See the honest-sizing note below |
| **W1D-21 — the staff list and its switch** | **+1.5 to +2.0** | The registry key and the split gate are about half a day. The plain searchable list screen is about a day — it is a new screen, and revision 3 had the staff directory out of scope. Its tests (flag on, flag off, store HR's list is their store, the endpoint refuses when the flag is off, the key is in no plan bundle) are the rest |
| **Revision 4 total** | **+2.25 to +3.0, less the 0.5 that W1D-13 no longer costs** | 13–15 → **15–18** |

**The sizing note Surbhi should read.** She was told W1D-20 **replaces** the half-day fix
and costs **about a quarter of a day more than it, not on top of it**. The "replaces" part
is right. **The quarter-day is too low.** My estimate is **half a day more**, so 1 to 1¼
days in place of the 0.5, for three things that were not inside W1D-13's half day:

1. **The cap and the total.** W1D-13 filtered a small list. W1D-20 hands company-wide HR
   their whole company, so the screen needs a 50-cap, a true total and the "showing the
   first 50 of 412" line — and the attendance query behind it has to stay bounded.
2. **Keeping `status = Active`.** `permitted_employees()` returns leavers on purpose, so
   the rebuild needs one more fixture and one more test to prove the Team screen does not
   start listing them.
3. **The bottom bar moves.** An HR user with no reports now has a Team button, so §2's
   rules, AC-10, AC-11's five named bars and AC-47 and their fixtures all change. Small
   each; four checks in total.

If that is wrong, it is wrong on the low side, not the high side: the quarter-day number
assumed the screen stayed the same size, and it does not.

| What grew in revision 3 | Days | Why |
|---|---|---|
| **The Inbox counts** (N3 capped count, W1D-14 split by caller) | **+0.75** | The bigger of the two. The count must use the list's own "waiting" rule in the database, the screen needs the "showing the first 50 of 60" line, the boundary fixture needs 51 items, and the corrections part now has two code paths and four test callers instead of one |
| **The shared scope helper** (SEC-4, N1) | **+0.25** | The refusal value, every caller handling it, and the "never `{}`" assertion |
| **The preview page** (SEC-1, W1D-15) | **+0.25** | A few lines in `get_context`, the flag-off test, the repository check that no production config sets the flag, and setting `portal_preview: 1` on the local bench and dev |
| Documents — the decision register, PRIV-7's table, the wording fixes | 0 | Done in that revision; no build cost |
| **Total added in revision 3** | **+1.75** | 11–13 → **13–15** (then revision 4's table above) |

**What did not grow:** day 1 (the page split, US-10), the frame includes, the bottom bar,
the routes, the search sheet, the profile sheet, the five states, and the swap commit. The
critical path is unchanged, and the page-split freeze is still the thing to schedule
first.

**One thing to watch, said plainly.** SEC-13 puts `alvoraa_portal/alvoraa_portal/hr_api.py`
into this slice's claimed files, and W1D-21 adds `alvoraa_portal/alvoraa_portal/subscription.py`
and the plan gate in `hrms-employee.html:7813`. `hr_api.py` is one of the busiest files in
the repository and other sessions edit it — slice 035 has already listed a dozen of its
functions as planned claims, although **not** `get_manager_dashboard`.

The SEC-13 change is no longer one filter on one `frappe.get_all`; it is a rebuild of the
HR branch of `get_manager_dashboard` plus a cap. It still belongs in **its own commit,
early**, touching that one function and nothing else, with the claim on the work board
before the first edit. The staff list should be a second, separate commit — the registry
key first, the screen after it.

---

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | *Closed 23 Sep (W1D-19):* the desk link keeps **the server's labels**, and a plain manager **does not get it at all**. The prototype was wrong, not the code — the register says so, so nobody changes the code towards it later. AC-75 | — | — |
| 2 | *Closed 23 Sep:* R3, R4 and R6 owners and dates — **accepted as recommended** (W1D-16, W1D-17) | — | — |
| 3 | *Closed 23 Sep:* the preview page with real data — **moot, the page does not exist on production** (W1D-15) | — | — |
| 4 | *Closed 22 Sep:* re-review of revision 2 — `02c-ba-rereview.md`, closed with notes, all applied here | — | — |
| 5 | *Closed 23 Sep (W1D-20 with W1D-21):* an HR person with no direct reports **keeps a Team screen**, built from their HR scope, and **gets a searchable staff list** where the tenant's new switch is on. They are never left with no way to see their people. AC-72, AC-76 | — | — |
| 6 | *Closed 24 Sep (W1D-22):* **yes, leave it as decided.** A tenant System Manager who has an Employee record sees the whole tenant on the Team screen; `is_hr` keeps System Manager in it and no second version of `permitted_employees()` is written. No data crosses a tenant boundary — that person's desk already lists every employee. **It stays on the record as a widening**: `01c` PRIV-7 keeps the row naming this as the one screen that gets wider on release. ALV-102 | — | — |

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
**Difference (a) — the desk link — is answered in revision 4** (W1D-19): the server's
labels, HR and System Manager only, and the prototype is recorded as the thing that was
wrong. The one thing I did **not** decide for her is open question 6 — whether a tenant
System Manager's Team screen should be the whole tenant. It is a consequence of W1D-20
rather than part of it, so it is raised with a recommendation, not assumed.

To the test engineer: the three structural tests the security review asked for are AC-69
(registry), AC-51 (count matches list, fixtures made the way users make them) and AC-70
(no module-level state). Revision 3 adds three more that are easy to get wrong:
**AC-73** — the assertion is that the helper never returns `{}`, not merely that a query
comes back empty; **AC-52 row 4** — the test must **fail** if the Shift Supervisor's queue
is empty, which is the opposite of the other three rows; and **AC-74** — the flag-off case
expects **404**, not 403, and must run with `portal_preview` genuinely absent rather than
set to 0.
