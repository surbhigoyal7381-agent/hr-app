---
slice: 034-redesign-wave1
artifact: 02-functional-spec
author: hrms-fullstack-engineer (short spec, written at the coordinator's request; hrms-business-analyst to review)
date: 2026-09-22
status: draft
inputs: [00-impact-analysis.md, 01c-security-privacy-requirements.md, 07-devops-inputs.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, ../009-ess-portal-redesign/01b-ux-design.md §5 §9 §14, ../009-ess-portal-redesign/appendix-a-frame.md, prototype-v2.html]
---

# Wave 1 frame — functional spec

**Short on purpose.** It lists the stories and the checks the frame must pass. The
business analyst should review it before it is called Ready. The detail behind each story
is in `appendix-a-frame.md` (FR-01 to FR-19) and `01b-ux-design.md` §5; this spec does not
repeat it.

**Prototype:** `C:/Surbhi-Git/hrlocal-data/prototypes/009-ess-portal-redesign/prototype-v2.html`
(the frame: left menu, top bar, phone bottom bar, search sheet, profile sheet).

## 1. Gap analysis

| Need | Frappe / our code today | Decision |
|---|---|---|
| Log out, My account | Frappe's website bar and `/me` | **Configure:** remove the bar, link to `/me` and Frappe's log out from the profile menu |
| Language per user | `User.language` | **Configure:** save it for the caller; English only in Wave 1 |
| Translations in the page | Frappe `__()` | **Extend:** wrap frame strings; plumbing only |
| Role and plan flags | `get_portal_context`, `get_available_features`, `subscription.FEATURES` | **Reuse**, combined in one call (`get_frame`) |
| Desk switch target | `module_access.get_switch_target` | **Reuse** |
| Store-HR scope | `access.permitted_employees`, `permitted_branches` | **Reuse** in `_pending_approvals_scope` and `_search_scope` |
| People search | `search_people` | **Reuse**, with the store narrowing |
| Counts | Pieces exist (goal/KPI count, leave approver filter, policy acknowledgement, attendance review queue) | **Build:** `inbox_api.get_nav_counts` |
| Menu, bottom bar, routes, sheet, states | Hand-written sidebar | **Build** in the frame include files |
| Directory, person sheet, Inbox list | — | **Drop from Wave 1** (Waves 2 and 4) |

No new DocType, no custom field, no migration.

## 2. Permission matrix

| | Employee | Manager | HR (company-wide) | Store HR | Owner with HR | Tenant System Manager | Control-plane operator |
|---|---|---|---|---|---|---|---|
| Me, Time, Growth | ✓ | ✓ | ✓ | ✓ | ✓ | if an employee | if an employee |
| Pay | where `plan_payroll` | same | same | same | same | same | same |
| Team | — | ✓ | if they have reports | if they have reports | ✓ | — | — |
| Company › People | ✓ where `plan_org_structure` | same | same | same | same | same | same |
| Company › HR analytics, Data to review | — | — | ✓ where `plan_analytics` is not false | same | same | same | same |
| Company › Reviews (HR) | — | — | ✓ where `goals` | same | same | same | same |
| Company › Policies | where `plan_policy_library` | same | same | same | same | same | same |
| Company › Org settings | — | — | ✓ | ✓ **read only** — saving is refused (slice 030, decision 4) | ✓ | — unless HR | — unless HR |
| Search finds | self and below | self and below | permitted companies | **own store only** | permitted companies | permitted companies | permitted companies |
| Switch to desk | — | — | `/app/hr` | `/app/hr` | `/app` | `/app` | `/app` |
| Tenant admin | — | — | — | — | — | **—** | ✓ |
| Preview page | — | — | — | — | if System Manager | ✓ | ✓ |

## 3. Stories and acceptance checks

**US-1 · The menu shows only what I may open.** As any portal user, I want a menu of only
the pages I can use, so that nothing I tap fails. *(FR-01, FR-02, FR-15, FR-19; S)*

- **AC-1** Given an employee on a tenant without payroll, when the frame loads, then no Pay
  group, no Pay button and no Pay search result exist anywhere.
- **AC-2** Given an HR user whose feature payload has no `plan_analytics` key, when the frame
  loads, then HR analytics is shown (absent is not "not bought").
- **AC-3** Given any user on a tenant without the `vendor` feature, then no vendor or driver
  item appears.
- **AC-4** Given someone who is both a manager and HR, then *Team › My team* and *Company ›
  Reviews (HR)* both appear, under different groups and titles, and open the team panel
  and the goals panel's HR tab respectively.
- **AC-5** Given any user, then "Checkin Log" no longer appears as a second menu item; it is
  a tab under Time.
- **AC-6** No menu item, button or search result is ever greyed out or disabled.

**US-2 · One start-up, no racing.** As any user, I want the menu drawn once with the right
items, so that items do not appear late or not at all. *(FR-03; S)*

- **AC-7** Given the page loads, then exactly one `get_frame` call and one `get_nav_counts`
  call are made for the frame, and neither waits on a timer.
- **AC-8** `get_frame` returns the same role, feature and switch-target values as the three
  old calls for the same user (tested per persona).
- **AC-9** Given a manager, then the Home panel still loads its team goals, the notes filter
  still knows the team, and HR still sees the Data to review badge (what
  `loadPortalContext` did for panels).

**US-3 · The phone bottom bar fits my job.** As a phone user, I want the four buttons I
use most, so that I rarely open the menu. *(FR-08, decisions 2 and 8; S)*

- **AC-10** The sets are: employee with payroll Home · Time · Pay · Goals; employee without
  payroll Home · Time · Inbox · Goals; manager Home · Team · Inbox · Time; owner or HR with
  reports Home · Inbox · Company · Team; HR without reports and CXO Home · Inbox · Company ·
  Time. Each set ends with More, which opens the menu.
- **AC-11** Given a button whose page this person may not open, then the next allowed page
  takes its place; a button never opens a refusal.
- **AC-12** At 390 px, in light and dark, labels are 12 px or larger, targets 44 px or
  larger, and nothing scrolls sideways.

**US-4 · I always know where I am, and Back works.** *(FR-06, FR-11, FR-16; S)*

- **AC-13** The top bar shows the group, then the page title in words — never the tenant
  name as a title. On a deep page the group is a link back.
- **AC-14** Opening a page changes the address (`#time`, `#time/requests`); the browser's
  Back returns to the previous page; opening an address directly opens that page if the
  person may, or the no-permission state (AC-30) if not.
- **AC-15** After a page change, focus moves to the page heading. Escape closes the menu and
  any sheet. Every menu item is a link or button reachable by keyboard, with visible focus
  and `aria-current` on the current one.

**US-5 · I can sign out and reach my account from inside the portal.** *(FR-12, FR-13; S)*

- **AC-16** Frappe's website bar is not shown. In the same release, the profile menu offers
  Log out, and Log out ends the session.
- **AC-17** The profile menu shows the person's name, role and tenant; My account (`/me`);
  Switch to the full desk only when the server returns a target, with the server's label;
  Tenant admin only for a System Manager on the control plane.
- **AC-18** Given a tenant with only English enabled, then the Language row is not shown.
  Given two or more enabled languages, then it shows them, and a choice saves the caller's
  `User.language` and reloads.
- **AC-19** Light or dark offers Match my phone · Light · Dark; the choice is kept on that
  device, applies before the first paint (no flash), and the tenant colour is applied
  again in the new theme.

**US-6 · The bell tells me the truth.** As any user, I want one number for what waits on
me, so that I know when to act. *(FR-04, FR-07, decision 6; M)*

- **AC-20** The total equals approvals waiting on me + policies I have not acknowledged + my
  own open requests. The bell, the menu and the bottom bar show the same number.
- **AC-21** Given a store HR person and pending goal updates in two stores, then the count
  and the bell list include only their store.
- **AC-22** Given my own pending leave, then it is counted under "my requests", never under
  "approvals".
- **AC-23** The Inbox page shows one row per part that has something, with its number and a
  link to today's screen where it is acted on. A part with nothing is not shown. With
  nothing at all, the page reads "All clear".
- **AC-24** `get_nav_counts` makes no more than 15 queries whatever the team size, and
  answers within 500 ms p95 on a 1,000-employee fixture.

**US-7 · Search finds what I may open, and nothing else.** *(FR-05; M)*

- **AC-25** Pages in search are exactly the pages in this person's menu.
- **AC-26** People results follow the scope in §2. An employee searching for someone outside
  their line gets no person result.
- **AC-27** A person result shows name, job title, department and photo only. It opens the
  org chart on that person where the tenant has `org_structure`; where it does not, search
  shows pages only.
- **AC-28** Fewer than two letters: pages only, no people. Ctrl K / ⌘K opens search.
- **AC-29** When nothing matches, the message says what this person can find, matching the
  scope actually enforced (for an employee: "your own team and the pages you can open").

**US-8 · The frame never leaves me stuck.** *(01b §5.7; S)*

- **AC-30** Opening a page the person may not open shows "This page is not part of your
  access. Ask HR if you think it should be."
- **AC-31** The shell and a skeleton are painted before any call returns.
- **AC-32** If the counts fail, the bell shows no number and the Inbox page says the count
  could not load, with Try again; the rest of the page works.
- **AC-33** If `get_frame` fails, the page shows one sentence, a Try again button and a
  short reference to read out to HR — never a server error.

**US-9 · One sheet, announced messages.** *(FR-09, FR-10; S)*

- **AC-34** The shared sheet is a dialog with a title, traps focus while open, closes on
  Escape and returns focus to the control that opened it.
- **AC-35** `toast()` messages are announced by screen readers (`role="status"`), and
  `toast(msg, type)` keeps its signature.

**US-10 · The page is split without changing anything.** *(appendix A §G step 2; M)*

- **AC-36** After the split, the page rendered from its includes is byte-for-byte identical
  to the page before the split, apart from the include tags.
- **AC-37** Every existing test and CI check that read the page reads it with includes
  expanded, and fails if it finds none.
- **AC-38** The full `alvoraa_portal` suite and `alvoraa_goals` suite pass after the split
  with no test removed.
- **AC-39** The layout test bans `container-type` on the wrapper elements, and the frame
  uses `@media`, not container queries.

**US-11 · The switch happens once, and can be undone once.** *(decisions 2, 3, 4; S)*

- **AC-40** Before the swap, `/hrms-employee-next` renders only for System Manager; others
  get the not-permitted response; Guest goes to login.
- **AC-41** The swap is one commit: `/hrms-employee` uses the new frame, the preview page and
  the classic frame files are deleted, and the pinned tests are repointed in the same
  commit. Reverting it restores the old frame with every test passing.
- **AC-42** The rail mark never shows a broken image, and the letter behind it is visible in
  both themes (slice 025's two tests, repointed).

**US-12 · One text floor everywhere.** *(decisions 5 and 10; S)*

- **AC-43** `--fs-xs` is 12 px. On the employee, driver and vendor portals at 390 px, no text
  is under 12 px and nothing scrolls sideways.

## 4. Edge cases

- A person with no Employee record (a platform operator) who opens the portal: the frame
  still loads with Me pages hidden where they need an employee, and no error.
- A leaver whose session is still open: `get_frame` answers from their current roles; the
  menu follows.
- Multi-company HR: counts and search cover every permitted company; a CXO gets the HR set.
- An employee with no branch on a store-HR tenant: outside every store (AC-21, AC-26).
- An owner with HR and reports who is also in a subject's line: Reviews (HR) still appears;
  the review list's own rule (decision 37) applies inside it.
- A cached `get_portal_context` from before a role change: cleared by the existing hooks;
  at most one hour stale otherwise, as today.

## 5. NFR numbers for this slice

See `07-devops-inputs.md` §1–3: skeleton ≤ 300 ms, Home ≤ 2.5 s on 3G (depends on
compression), each new endpoint ≤ 500 ms p95 and ≤ 15 queries, WCAG 2.2 AA, 390 px and
200 % zoom.

## 6. Migration

None. No schema change, no data change, no patch.

## 7. Localisation and accessibility

Every frame string in `__()`, no joined sentences, dates through the existing formatter.
Labels 12 px or larger; 44 px targets on phones; inputs 16 px on phones; colour never the
only signal; `prefers-reduced-motion` respected.

## 8. Audit trail

The only write is the caller's own `User.language`; Frappe's version history on User
records it. Refused calls log through `access.log_refusal`.

## 9. Compliance impact

- **Data touched:** names, titles, departments, photos in search; counts; a language
  preference.
- **Visibility change:** narrower for store HR (counts, bell list, search). No widening
  anywhere.
- **Decision automation:** none.
- **Retention:** nothing new is stored except `User.language`.

## 10. Traceability

| Requirement | AC |
|---|---|
| SEC-1 | AC-40 |
| SEC-2 | AC-7, AC-8, AC-40 |
| SEC-3 | AC-21 |
| SEC-4 | AC-26 |
| SEC-5 | AC-20, AC-21, AC-22 |
| SEC-6 | AC-8, AC-18 |
| SEC-7 | AC-17 |
| SEC-8 | AC-17 |
| SEC-9 | AC-18 |
| SEC-10 | AC-42 |
| SEC-11 | AC-25 |
| PRIV-1 | AC-26 |
| PRIV-2 | AC-27 |
| PRIV-3 | AC-28 |
| PRIV-4 | AC-23 |
| PRIV-5 | tested in the security review (log capture); no user-facing AC |
| PRIV-6 | AC-19 |
| PRIV-7 | AC-26, AC-27 |
| OPS-1 | not an AC here: dependency on the compression slice, checked before the swap |
| OPS-2, OPS-3 | AC-40, AC-41 |
| OPS-4 | release plan (§5 of `07`), not an AC |
| OPS-5 | release plan |
| OPS-6, OPS-7 | AC-36, AC-37, AC-38 |
| OPS-8 | not in this slice (decision 12) |
| OPS-9 | AC-24, AC-31 (measured, recorded in implementation notes) |
| OPS-10 | AC-40 |
| OPS-11 | AC-43 |

## 11. Ready check

| Box | State |
|---|---|
| Clickable prototype reviewed | Yes (design check, 22 Sep) |
| Every state designed | Yes, `01b` §5.7 |
| `01c` and `07` §1–3 written | Yes, drafts — **need specialist review** |
| Stories with ACs | Yes, US-1 to US-12, AC-1 to AC-43 |
| Permission matrix with negatives | Yes, §2 |
| Traceability | Yes, §10 |
| Migration stated | Yes, none |
| Frappe details verified in source | **No** — four items in `00` §9, checked before the step that needs them |
| Open questions block day 1? | No |

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | Review of this spec | Business analyst | Ready |
| 3 | Store HR sees Org settings today but cannot save (slice 030, decision 4). Keep it in their menu as a read-only page, or hide it? I propose keep it, as today — Wave 1 does not change it | Surbhi | Nothing in Wave 1 |
| 2 | Frame strings in Hindi are not written in Wave 1, but should each screen be measured at 390 px in Hindi now (`01b` §14 item 14)? I propose yes, with machine-drafted strings in a test fixture only | Surbhi | AC-12, AC-43 scope |

## Assumptions

- `[ASSUMPTION]` Frappe's `/me` page is the right target for "My account".
- `[ASSUMPTION]` The field names on Shift Request and Attendance Request match what the
  count needs; checked before step 5.

## Handoff note

To the business analyst: AC-11 (the bottom-bar fallback), AC-18 (the hidden language row)
and AC-23 (the Inbox rows) are the three places this spec goes beyond the prototype, each
because of a decision taken on 22 Sep. Please check them against the prototype and say if
you would word them differently.
