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
