---
slice: 060-manager-records-attendance
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-10-17
status: approved-by-user-in-the-task
inputs: [01-product-brief.md, 01c-security-privacy-requirements.md, the navigation consolidation Surbhi approved on 17 Oct 2026]
---

# Five doors to attendance become one

## What this is

Not a feature. The portal grew five sidebar entries that all lead to attendance,
and nobody can tell them apart. This is renames, a move, two deletions, and
relocating code that already exists and already has tests.

There is **no `02-functional-spec.md` for this slice**. The approved scope is the
eight-item list Surbhi settled on 17 Oct 2026, repeated verbatim in the task that
started this work. Nothing here goes outside it.

## The ladder

**Rung 4, new code - and only just.** Rung 1 (already there) covers almost all of
it: every screen, endpoint and style this change needs is already built and
tested. What is genuinely new is three things and no more:

1. one boolean on an existing context endpoint, so an existing nav item can be
   hidden from people who have nothing behind it;
2. one word changed in `month()`'s return (`can_request`);
3. one click handler, so a row in the team list opens that person's month.

Rung 2 (configuration) was rejected because a sidebar label is not a setting and
nobody asked for one. Rung 3 (customisation) does not apply - this is our own
page, not a Frappe DocType. Rung 5 (new DocType) and rung 6 (new app) were never
candidates. **No new page, no new endpoint, no new permission concept.**

## Functional impact

### Cross-module reach

| Module | Reached? | Why |
|---|---|---|
| `alvoraa_portal` | Yes | the portal frame, three markup parts, `portal.js`, `hr_api.py`, `attendance_correction.py` |
| `hrms` | No | no DocType, no permission rule, no hook touched |
| `erpnext` | No | - |
| `alvoraa_goals` | No | - |
| `alvox_compensation` | Not installed | - |
| Mobile app (`mobile/`) | No | it has its own screens and does not read this sidebar |

### Callers of everything being changed

| Thing changed | Callers found by grep | Handled |
|---|---|---|
| `hr_api.get_portal_context` | `portal.js` `loadPortalContext`, `test_control_plane`, `test_frame_api_034`, `portal_notes_test.js` | a key is **added**, nothing removed, so every caller is unaffected |
| `attendance_correction.month` | `portal.js` `acLoad`, `test_attendance_correction` | `can_request` widens; the two tests that assert it are updated and three more added |
| `switchTeamTab` | `team.html`, `portal_notes_test.js` (`"notes"`) | goes from three tabs to two; the `"notes"` path is untouched |
| `trOpen` / `trLoad` / `trBar` / `trChips` / `trRows` / `trPager` | only `switchTeamTab` | the one caller becomes `acLoad` |
| `fetchCalendar` / `renderCalendar` / `calNav` | only `loadAttendance` and the calendar's own arrows | all deleted with the widget they drew |
| `hr_api.get_attendance_calendar` | only `fetchCalendar` | **left in place**, see "what I did not do" |
| `data-panel="attendance"` | frame.html x2, drawers.html, home.html | each decided one at a time, below |

### Persona impact

| | CXO / HR | HR Manager | Employee | Manager |
|---|---|---|---|---|
| Sidebar entries leading to attendance | 5 to 3 | 5 to 3 | **5 to 2** | 5 to 3 |
| "Attendance Insights" | unchanged, now under Management | unchanged, now under Management | **disappears** - they only ever had one of its three views and the other two were greyed out | kept, under Management |
| "My Attendance" | becomes "Attendance", second in the list | same | same | same |
| "Attendance & Leave" | becomes "Leave", loses its month calendar and four tiles | same | same | same |
| "Checkin Log" | gone (it was a duplicate of "Attendance & Leave") | gone | gone | gone |
| Team View | loses its "Attendance Review" tab | loses it | never had it | loses it, **and gets it back** inside Attendance, under "Whole team" |
| Raising a correction for somebody else | already could, from the deleted tab | same | no change - still own record only | **new**: can also raise from a direct report's day detail |

The employee is the persona this is really for. They lose two confusing entries
and gain nothing they had before - their own month, their own corrections and
their own leave are all still there, in two places instead of five.

### HRMS domain impact

Leaves: the Leave page keeps Apply Leave, the balance rings, the applications
table and the Late & Deductions card. Attendance: the Attendance page already
showed the month with punches, hours, shift strip and arrival, which is why the
Leave page's mini calendar and four tiles are the duplicate being removed, not
the other way round. Payroll, appraisals and org structure: untouched.

## Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **improves** | the Leave page drops one round trip per visit (`get_attendance_calendar`). The Attendance Insights gate adds **zero** queries: the direct-report count is the one `get_portal_context` already runs for `is_manager`, and the organisation check is a role-set test on roles already fetched. No new endpoint, so no extra call on page load |
| **Security** | **improves** | `nav-att-insights` was visible to every employee with no gate at all; it is now hidden unless the server says there is something behind it. The page's own server-side refusals (`_population`) were and remain the real enforcement - this only stops advertising a door. The `can_request` widening is checked server side by `_subject` plus `_reports_to(deep=False)` inside `raise_for_report`, which was already there; the flag cannot grant anything the endpoint refuses |
| **Reliability** | **neutral** | moved code, same code. The one new failure path - the team list inside the Attendance page - shows the server's own words, as it did in the tab |
| **Scalability** | **neutral** | the team list keeps its paging, its 50-row page and its three-month period cap. Nothing new grows with headcount |
| **Maintainability** | **improves** | about 90 lines of calendar JavaScript and 30 lines of markup deleted; one screen instead of two for the same job; the three-tab switch returns to two |
| **Data integrity** | **neutral, with one note** | `get_portal_context` is cached per user for an hour, cleared on Employee and User saves. A context cached **before** this change has no `att_insights` key, so the item stays hidden until the cache expires or the user's record changes. That is fail-closed, which is the right direction, and it self-heals within the hour |
| **Compliance / privacy** | **improves slightly** | one fewer screen offering a staff-shaped list to people who may not use it. The team list still carries attendance facts only - no pay - and that test travels with it. No new personal data reaches any payload or any log |

## Parallel-work check

| File | Hot? | Who else is in it | Plan |
|---|---|---|---|
| `templates/includes/ess/frame.html` | **yes** | nobody right now | edit |
| `public/js/ess/portal.js` | **yes** | nobody right now | edit |
| `parts/policies.html`, `parts/attendance.html`, `parts/team.html`, `parts/drawers.html` | no | nobody | edit |
| `hr_api.py` | **yes** | nobody right now | one key added |
| `attendance_correction.py` | yes (this slice) | this slice only | one line plus its comment |
| `tests/test_attendance_correction.py` | yes (this slice) | this slice only | two tests updated, three added |

- `git fetch origin` then `git log HEAD..origin/dev`: **nothing incoming.** This
  branch is two commits ahead of `origin/dev` and both are Surbhi's.
- `git status` in this worktree: clean at the start of work.
- No work board file exists on this machine (`.claude/work-in-progress.md` is
  absent), so the evidence is the fetch above plus the task's own statement that
  the tree is clean and the last two commits are the caller's.
- 66 other worktrees exist. None is claimed for this area and none is mine to
  delete.

## Strategy - the eight items, and the mechanism for each

1. **"My Attendance" becomes "Attendance", second in the list.** Label and
   position in `frame.html`; the panel's `<h1>` becomes the constant word;
   `acPaint()` already writes `ac-sub`, so that line is extended to say *whose*
   record it is.
2. **"Attendance & Leave" becomes "Leave", third.** Label in `frame.html` and in
   the panel heading. The mini calendar and the four tiles come out of
   `parts/attendance.html`, and `calNav`/`fetchCalendar`/`renderCalendar` come
   out of `portal.js` with them - leaving them behind would be dead code writing
   to elements that no longer exist.
3. **Attendance Insights moves under Management and is gated.** One boolean,
   `att_insights`, on `get_portal_context`, computed from the two things
   `attendance_analytics.views()` already uses: a direct-report count (free - the
   same count `is_manager` runs) and `_may_see_organisation()` (imported, not
   re-written, so the two cannot drift). `loadPortalContext` hides the item when
   it is false, and the Management header also appears for it, so the item can
   never sit under a hidden heading.
4. **"Checkin Log" and the "Tools" heading are deleted.**
5. **The "Attendance Review" tab and its panel are deleted** from
   `parts/team.html`, and `switchTeamTab` goes back to two tabs.
6. **The team review moves into the Attendance page's picker.** A "Whole team"
   entry at the top; choosing it hides the one-person month and shows the
   `tr-*` list. The `trState`/`trBar`/`trChips`/`trRows`/`trPager` block and the
   `.tr-*` styles are **moved, not rewritten**. One genuinely new line: a row
   click opens that person's month at that date.
7. **`can_request` becomes self OR a direct report**, and the comment above it
   says why it changed. The day detail then offers "Ask HR to fix this day"
   through `raise_for_report`, which already stamps who raised it. For anybody
   deeper in the line the detail stays read-only and says whose job it is.
   `_subject` is not narrowed, so reading still reaches the whole line.
8. **The phone bottom bar's middle item repoints** from `attendance` (now Leave)
   to `att-record`.

## Where an instruction turned out to be wrong

**Item 8's second half.** The task says to check `home.html` line 91's
"Details" link and repoint it. Read in place, that link is **not** an attendance
card - it sits inside `#home-leave-card`, headed "Leave balance", and it is the
only `switchPanel('attendance')` call in `home.html`. After the rename it points
at the page called "Leave", which is exactly where a leave-balance card's
"Details" should go. **Repointing it would make it wrong.** Left alone, and said
out loud here rather than worked around.

## Known gap, declared not fixed

`raise_for_report` enforces the reporting line and refuses future days. It does
**not** enforce SEC-9's filing window (`alvoraa_manager_filing_window_days`, two
working days) or SEC-9(b)'s paid-period guard - those were specified for this
slice and have not been built on either path. Item 7 adds a **second door to the
same endpoint**, so it widens no rule and bypasses no control that exists; the
gap is the same size before and after. Building the window here would be work
nobody approved in this list. Flagged for Surbhi to schedule.

---

# Addendum, 18 October 2026 — SEC-9(a), the filing window, now built

Surbhi approved this on 18 Oct 2026, with one decision attached: **no
paid-period guard.** Salaries are paid in the first week of the following month
*after* a thorough attendance review, so a correction filed in that window is
what the review is for. SEC-9(b) therefore stays unbuilt **by decision**, not by
oversight, and the "Known gap" above shrinks to that one half.

## Rung on the cost ladder

**Rung 2 for the number, rung 4 for the rule.** The number is a Frappe default
(`alvoraa_manager_filing_window_days`), the idiom
`alvoraa_attendance_late_grace_mins` already uses — no migration, no new
DocType, nothing for an existing tenant to touch. The rule is one `if` in the
endpoint that already exists.

Cheaper rungs rejected, with the reason:

| Rung | Why not |
|---|---|
| 1 — already there | Frappe HR's `Attendance Request` bounds nothing but the future. There is no setting, anywhere, for how far back a filing may reach |
| 2 — configuration alone | A number nobody reads changes nothing. The number needs the one `if` |
| 3 — a Server Script | It would have to re-derive "is this the manager's path or HR's", which the endpoint already knows. A rule in two places is the way the two come to disagree |
| 5 — a new DocType | Nothing to store but one integer per tenant |

## Functional impact

**Cross-module.** None. No `hrms`, `erpnext`, `alvoraa_goals` or
`alvox_compensation` file is touched. Three files change, all in
`alvoraa_portal`.

**Callers grepped.** `raise_for_report` — `portal.js` (two entry points) and
`test_attendance_correction.py`. `hr_may_act_from` — `decide()` at
`attendance_correction.py:1211` and `test_decided_as_045.py` (four places); its
signature and its answer are unchanged, only its body moved into the shared
counter. `ALLOWED_ORG_SETTINGS` — the two org-setting endpoints and
`test_org_settings_allowlist_012.py`.

**Personas.**

| Persona | What changes |
|---|---|
| **Employee** | Nothing. `raise_correction` is untouched, and `raise_for_report` still hands a self-named request straight to it. An employee may still ask about any past day of their own — narrowing that was never approved and would be a regression |
| **HR Manager** | Gains the number on Org Settings. Their own filing path is **not** bounded: HR is the way out when a day is too old, so the guard sits in the manager's endpoint and never on the document |
| **CXO** | Nothing beyond what HR sees. The setting is HR's, deliberately not in `ACCESS_GRANTING`: it changes *when* a bounded actor may file, never *who* they may file for |

**HRMS domain.** Attendance only. Leave is untouched — the slice's optional
leave-notice rule is not in this change.

## Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | One extra `get_default` (cached by Frappe) and at most one `Holiday` query per manager filing, both on a path a human presses by hand |
| Security | **improves** | A bounded actor's reach shrinks from "any past day" to a configured window, server side, on the only endpoint that path has. No new endpoint, no new permission concept, no `ignore_permissions` |
| Reliability | **improves** | The working-day walk gains a hard stop, so a holiday list full of holidays can no longer spin. An unreadable holiday list still falls back to calendar days, which is the tighter answer |
| Scalability | neutral | Nothing grows with headcount |
| Maintainability | **improves** | Two working-day counters became one, used forwards by the HR wait and backwards by the window. They can no longer disagree about what a working day is |
| Data integrity | neutral | No stored data changes; the setting is read per request, never cached by us |
| Compliance / privacy | neutral | No new field is read or shown. The one log line carries the Employee document name and nothing about the person |

## Parallel-work check

Files changed: `attendance_correction.py`, `hr_api.py` (one import, one
allowlist row), `templates/includes/ess/parts/org-settings.html`,
`public/js/ess/portal.js`, `tests/test_attendance_correction.py`. `hr_api.py`
and `portal.js` are hot files; both additions are self-contained blocks at the
end of an existing section, which is the shape that merges cleanly. The main
checkout was clean of modified tracked files and `dev` was an ancestor of this
branch, so the work came in by fast-forward with nobody else's commits in
between.

---

# Addendum — 18 October 2026: the on-behalf capability becomes two tenant settings

Written after Surbhi tested the manager's on-behalf path on `ppj.dev` and asked for it to
be a per-tenant setting with a sub-setting. Her words are in
`01c-security-privacy-requirements.md`, "SEC-9(a) reworked".

## Where on the cost ladder

**Configuration, plus the code that reads it.** Rung by rung:

| Rung | Verdict |
|---|---|
| Already there | No. There was one control, the filing window, and no way to switch the capability off. |
| Configuration | **Yes, for the storage.** Both settings are Frappe defaults on the existing `hr_api.set_org_setting` allow-list, written from the Org Settings screen that already exists. No new DocType, no new endpoint, no migration, and nothing for an existing tenant to touch. |
| Customisation / new code | Only the readers and the three places that gate on them. |
| New DocType / new app | Rejected: two values do not need a document, and HR Settings is not per-capability. |

## Functional impact

**Cross-module.** None. `alvoraa_goals`, `alvox_compensation`, `hrms` and `erpnext` are
untouched; nothing outside `attendance_correction.py` reads either key, proved by grep.
Frappe HR's Attendance Request is unchanged, and HR's Desk route past the window is
unchanged.

**Callers of what changed.**

| Changed | Callers | Effect |
|---|---|---|
| `manager_filing_window_days()` | `_refuse_outside_filing_window`, `manager_filing_from`, `team_days`, tests | now returns `None` for blank, which every caller handles explicitly |
| `_refuse_outside_filing_window()` | `raise_for_report` only | no limit returns early |
| `month()` payload | `portal.js` day detail | two new keys, `on_behalf_enabled` and the existing `can_request_from`, now usually `None` |
| `team_days()` `can_raise` | `portal.js` row | HR no longer gets it on every row; a day outside the window no longer gets it either |
| `raise_for_report()` signature | `portal.js`, tests | `employee` and `from_date` are optional and refused in plain words, so an empty call cannot become "my own day" |

**Personas.**

* **CXO** — nothing. They read; they never raised.
* **HR Manager** — gains both settings. **Loses the raise button on the team list**, which
  disagreed with the month view. They still decide every request and still fix any day from
  the Desk.
* **Employee** — nothing changes, by design and by test. Their own day keeps its form with
  either setting off or at `0`.
* **Manager** — on an unset tenant: the same capability as today, with *more* reach, because
  blank now means no limit instead of two working days. On a tenant that sets a window:
  exactly what HR chose, and the screen stops offering days the server would refuse.

**HRMS domain.** Attendance only today. The switch is named for the capability so leave can
join it without a second switch or a second answer to one question.

## Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **neutral**, mildly better on the common path | Blank costs no holiday read at all. The per-person boundary in `team_days` is computed only for the caller's direct reports and only when a window is set, so HR's 363-person page does none of it. |
| Security | **improves** | The capability can be switched off per tenant. An empty call to `raise_for_report` is refused before `_subject` could read it as "my own month". `ignore_permissions` ceiling stays 0. |
| Reliability | **improves** | One press sends one request. Nothing incomplete leaves the page. A correct refusal is no longer masked by a Python error about arguments. |
| Scalability | **neutral** | No new query that grows with headcount. |
| Maintainability | **improves** | One derivation of the boundary for the guard and both screens, and one rule for who may raise instead of two that disagreed. |
| Data integrity | **neutral** | No stored data changes. Blank and `0` are kept apart in the reader and in a test. |
| Compliance / privacy | **neutral** | No new field, no new visibility, nothing personal in any log line. Switching the capability off narrows visibility; nothing widens it. |

## Parallel-work check

Files changed: `attendance_correction.py`, `hr_api.py`, `portal.js`,
`parts/org-settings.html`, `tests/test_attendance_correction.py`,
`tests/portal_correction_test.js`. Worked in the worktree
`.claude/worktrees/060-manager-review` on `slice/060-manager-review`, from `d1f0638a`.
Nothing came in from anybody else during this change, and nothing was merged or rebased.
`hooks.py`, `patches.txt` and the DocType JSON — the hot files — were not touched.
