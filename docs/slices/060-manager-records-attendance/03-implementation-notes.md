---
slice: 060-manager-records-attendance
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-10-17
status: built locally, tested, NOT pushed
---

# Five doors to attendance became two

The eight approved items, all eight done. One instruction turned out to be
wrong when read against the code; it is below, and I did not work around it.

## What I changed, file by file

| File | What | Mechanism | Why that one |
|---|---|---|---|
| `templates/includes/ess/frame.html` | "My Attendance" renamed "Attendance" and moved to second; "Attendance & Leave" renamed "Leave"; Attendance Insights moved under Management and given `display:none`; "Checkin Log" and the "Tools" heading deleted | **configure** (markup only) | labels and order are markup; nothing else was needed |
| `parts/policies.html` | the Attendance panel's heading is now the constant word; added the `#ac-team` container holding `tr-bar`, `tr-chips`, `tr-body`, `tr-pager` | **configure** | the containers are the *same ids* the deleted tab used, so the JavaScript did not have to change |
| `parts/attendance.html` | the Leave page: renamed, mini calendar and four tiles removed, the `att-leave-grid` wrapper removed with them | **configure** | the grid was `minmax(240px,300px) 1fr` — one child left in it would have been squeezed into the narrow column |
| `parts/team.html` | "Attendance Review" tab and `tv-review-panel` deleted, with a comment saying where the list went | **configure** | — |
| `parts/drawers.html` | the phone bar's middle item now opens `att-record` | **configure** | — |
| `public/js/ess/portal.js` | the gate for `nav-att-insights`; `acState.team`, `AC_TEAM`, `acPick`, `acFromTeam`, the team branch in `acLoad`, the picker and subtitle in `acBar`/`acPaint`; `switchTeamTab` back to two tabs; `calNav`/`fetchCalendar`/`renderCalendar` and the `calYear`/`calMonth` globals deleted (92 lines) | **extend** | the team list itself was moved by changing its one caller, not rewritten |
| `public/css/ess/panels.css` | `.tr-open` (6 lines) for the row-opening button; the section heading corrected — it still named the deleted tab | **extend** | a real `<button>` so the row is keyboard reachable with visible focus |
| `hr_api.py` | `att_insights` on `get_portal_context`; `has_reports` captured from the count already being taken | **new code** (one boolean) | `_may_see_organisation` is imported, not re-written, so the nav and the page cannot drift |
| `attendance_correction.py` | `can_request` is now self OR a direct report; `asker` read only on that path; the stale comment replaced | **new code** (one expression) | `_reports_to(..., deep=False)` is the same call `raise_for_report` enforces with, so flag and guard cannot disagree |
| `tests/test_attendance_correction.py` | one test renamed and re-scoped to HR, four new tests in `WhoMayAskFromSomebodyElsesMonth` | — | each new case checks the flag **and** the endpoint |
| `tests/test_nav_consolidation_060.py` (new) | 15 text checks pinning the consolidation | — | a rename is exactly what a careless merge restores, and nothing else in the suite would notice |

**No new page, no new DocType, no new endpoint, no new permission concept.** The
only new whitelisted surface is zero: `att_insights` rides on an endpoint that
already existed, and `can_request` is a field on a payload that already existed.

## The approved list, item by item

| # | Item | Done | How |
|---|---|---|---|
| 1 | "My Attendance" → "Attendance", second, constant heading, `ac-sub` says whose | yes | heading is the word; `acPaint` writes "Your record · October 2026" / "Priya Mehta · October 2026", and the team branch writes "Whole team · days that need a look" |
| 2 | "Attendance & Leave" → "Leave", third, lose the calendar and the four tiles | yes | Apply Leave, the balance rings, the applications table and the Late & Deductions card all kept and asserted |
| 3 | Attendance Insights into Management, gated on `team` or `organisation` | yes | one boolean on the context the nav gating already reads; no extra round trip |
| 4 | Delete "Checkin Log" and the empty "Tools" heading | yes | — |
| 5 | Delete the Attendance Review tab and panel; `switchTeamTab` back to two | yes | — |
| 6 | Fold the team review into the Attendance picker, "Whole team" at the top; a row opens that person's month at that date | yes | code **moved**, not rewritten — same ids, same `trState`/`trBar`/`trChips`/`trRows`/`trPager`, same `.tr-*` styles |
| 7 | `can_request` for self or a direct report; "Ask HR to fix this day"; read-only deeper in the line; `_subject` not narrowed | yes | plus four tests |
| 8 | Phone bottom bar points at the consolidated page | yes (see below for `home.html`) | — |

## Where the instruction was wrong

**Item 8's second half — `home.html`'s "Details →" link. I did not change it,
on purpose.**

That link is the only `switchPanel('attendance')` call in `home.html`, and it
sits inside `#home-leave-card`, whose header reads "Leave balance". It is not an
attendance card. After the rename it points at the page now called "Leave" —
which is where a leave-balance card's "Details" belongs. Repointing it would
have made it wrong. Everything else in item 8 is done.

## The seven dimensions, re-assessed against the code I actually wrote

| Dimension | Verdict | Against the real diff |
|---|---|---|
| **Performance** | **improves** | the Leave page drops one call per visit (`get_attendance_calendar`) and 92 lines of render work. `att_insights` adds **zero queries**: `has_reports` is the count `is_manager` already ran, and `_may_see_organisation` is a role-set test plus a defaults-cache read. `can_request` adds **two reads, on the non-self path only** (`_employee_for` + one `get_all` of direct reports) — a manager or HR opening somebody's month, never an employee opening their own. The team list keeps its 50-row page |
| **Security** | **improves** | `nav-att-insights` went from no gate at all to server-decided, and an absent flag reads as "no". `can_request` cannot grant anything: `raise_for_report` still runs `_subject` and then `_reports_to(deep=False)` itself, and `test_and_the_endpoint_agrees_about_the_skip_level` proves the refusal is still there. `ignore_permissions` in `attendance_correction.py` is still **0** (ceiling test green). No new whitelisted endpoint |
| **Reliability** | **neutral** | moved code, same code. The team branch shows the server's own refusal text (`trErr`), as the tab did. `acBar` now reads `acState.data || {}` so it cannot throw before the first month lands |
| **Scalability** | **neutral** | paging, the 50-row page and the three-month period cap all travelled with the list. Nothing new grows with headcount |
| **Maintainability** | **improves** | net −14 lines across the portal despite ~60 lines of new comment; 92 lines of calendar JavaScript and 41 lines of markup deleted; one screen for one job; three tabs back to two; 15 new pin checks |
| **Data integrity** | **neutral, one declared note** | `get_portal_context` is cached per user for an hour. A context cached before this deploy has no `att_insights`, so the item stays hidden until the cache expires or that user's Employee/User row is saved. Fail-closed, self-healing within the hour |
| **Compliance / privacy** | **improves slightly** | one fewer screen advertised to people who may not use it. No field was added to any list, export, notification or payload. The team list still carries attendance facts only — `test_it_carries_no_pay_figures` travelled with it and is green. Nothing personal added to any log |

## NFR detail

- **Query counts.** `get_portal_context`: unchanged. `month()` for your own
  record: unchanged. `month()` for somebody else: +2 reads. `team_days`: not
  touched. Leave page: −1 call.
- **Indexes added:** none. Nothing new is filtered or joined on.
- **Background jobs:** none added.
- **Permission enforcement points:** `_subject` (read), `_reports_to(deep=False)`
  inside `raise_for_report` (act), `_population` in `attendance_analytics`
  (the Insights page), the document's own permission check on insert. All
  pre-existing; none loosened.
- **Sensitive fields touched:** none. The team list shows attendance facts; pay
  is excluded by a test that already existed.
- **Fallbacks:** absent `att_insights` hides the item; `acBar` tolerates no
  month data; `trErr` shows the server's words.
- **Accessibility:** the row opener is a real `<button class="tr-open">` —
  keyboard reachable, visible focus ring, and underlined so the affordance is
  not carried by colour alone.
- **Internationalisation:** no new server-side user-facing string was added;
  the two changed ones are existing portal JavaScript strings, which this page
  has never run through a translation layer. Not made worse, not fixed.

## Tests — what I ran and what it said

One `bench run-tests` at a time against `test_site`, after checking
`pgrep -af run-tests` found nothing. Both summaries read for every module.

| Module | Integration | Unit | Result |
|---|---|---|---|
| `test_attendance_correction` | **71 in 346.8s OK** | **9 in 0.2s OK** | the 4 new tests included; one renamed |
| `test_portal_security_010` | **45 in 108.7s OK** | **5 in 3.7s OK** | includes the `ignore_permissions` ceiling (still 0) |
| `test_portal_split_034` | — | **12 in 2.6s OK** | one category only |
| `test_panel_source_042` | — | **7 in 0.7s OK** | one category only |
| `test_browser_call_args_045` | — | **6 in 0.8s OK** | one category only |
| `test_day_marks` | **42 in 59.3s OK** | — | one category only |
| `test_nav_consolidation_060` (new) | — | **15 in 11.9s OK** | — |
| `test_control_plane` | — | **7 in 0.1s OK** | reads `get_portal_context` |
| `test_frame_api_034` | **34 in 231.3s OK** | — | reads `get_portal_context` |
| `test_ess_parts_034` | — | **8 in 0.3s OK** | markup parts |
| `test_frame_endpoint_registry_034` | — | **9 in 1.5s OK** | endpoint registry |
| `test_attendance_analytics` | **17 in 56.0s OK** | — | I import from this module now |
| `test_attendance_scope_012` | **13 in 75.6s OK** | — | the Insights scope |

**334 tests, 0 failures, 0 errors.**

Static and browser checks:

| Command | Result |
|---|---|
| `python scripts/check_app_integrity.py` | **774 checks, OK - all consistent** |
| `python scripts/check_design_system.py` | **OK - the visual system holds** (every counter at or under its limit) |
| `node scripts/check_portal_handlers.js` | **all reachable and callable** (9 pages) |
| `node scripts/check_undefined_js.js` | **undefined identifiers: none** |
| `node scripts/check_attendance_strip.js` | **every case draws cleanly** (13 cases) |
| `node scripts/run_dom_tests.js` | **9 run, 0 not run, 0 failed** — including `portal_notes_test.js` (12/12), the one test that calls `switchTeamTab` |
| `node --check portal.js` | clean |

I also drove the real page in jsdom with a throwaway probe (deleted; it is not
in the commit) to prove the behaviour rather than only the markup — **16 of 16**:
the gated item appears for somebody entitled to it, "Whole team" is first in the
picker, choosing it swaps the month grid for the cross-person list and hides the
month arrows, the subtitle changes, the chips and rows draw, the row's name is a
real button, clicking it opens **that person at that month** ("Priya Mehta ·
September 2026"), and a direct report's row offers "Ask HR to fix".

## What else moved while I worked

**Nothing.** `git fetch origin` then `git log HEAD..origin/dev` was empty at the
start and at the end. No conflicts, so nothing of anyone's to lose. The two
commits this branch already carried are Surbhi's and are untouched.

Two things I noticed and left alone, as somebody else's:

- `stash@{0}` is `On chore/rename-alvox: chore/rename-alvox working changes` —
  not mine. Not touched.
- 66 other worktrees exist. None is claimed for this area.

`npm ci` installed `node_modules` (git-ignored) and left `package-lock.json`
unchanged.

## Subtract pass — what I deleted from my own work

Six things, after it was all working:

1. **`_raisable_by_caller`** — a helper called once. Inlined into the expression,
   which also made the two reads conditional, so an employee opening their own
   month pays nothing for a manager's feature.
2. **A two-way button label.** I had "Ask HR to correct this day" for yourself
   and "Ask HR to fix this day" for a report. One button, one label — the
   approved wording, which is true for both.
3. **`test_your_own_month_still_offers_it`** in my new class —
   `ReviewingSomebodyElse` already covers it.
4. **`test_somebody_outside_the_line_is_refused_before_the_flag_matters`** —
   `test_a_manager_cannot_open_somebody_outside_their_line` already covers it.
5. **The fixture that test needed** (`self.outsider` in the new class), now unused.
6. **`.tr-open:hover`** — `cursor:pointer` already says it is clickable.

## Known gaps and shortcuts

**Dangerous debt — escalating now, not just noting it.**

`raise_for_report` enforces the reporting line and refuses future days. It does
**not** enforce SEC-9's filing window (`alvoraa_manager_filing_window_days`, two
working days) or SEC-9(b)'s paid-period guard. Both were specified for this
slice in `01c-security-privacy-requirements.md` and neither exists in the code on
either path. SEC-9(b) is the one that bites: a rolling window crosses the month
boundary, and a month's payroll runs in the first days of the next — so on the
2nd a manager can file for the 31st, a day that may already be paid.

Item 7 adds a **second door to the same endpoint**, so it widens no rule and
bypasses no control that exists; the gap is exactly the same size before and
after. Building the window was not in the approved list and I did not build it.
**It should be scheduled before this reaches a tenant that runs payroll.**

**Acceptable simplifications.**

- `hr_api.get_attendance_calendar` is left in place with no caller in the
  portal. Deleting a whitelisted endpoint is a bigger decision than this list
  authorised, and `test_browser_call_args_045`'s "no endpoint is named but never
  read" check is green either way. Worth removing in a later tidy.
- `.att-leave-grid`, `.cal-mini` and a few `.cal-*` rules in `panels.css` are now
  unused by the live portal. **I deliberately did not delete them**: `.cal-cell`
  is redefined further down the same file for the calibration nine-box grid,
  which is in use, so pruning that namespace is a risk this change did not need
  to take. About 25 lines of dead CSS, flagged rather than removed.
- Portal JavaScript strings are not wrapped for translation anywhere in this
  file, and the two strings I changed follow the existing practice. Not made
  worse; not fixed here.

**Intentional trade-off.**

`att_insights` sits inside the hour-long `portal_ctx_<user>` cache. The
alternative was a second round trip on every page load for a sidebar label. The
failure mode is the safe one — the item stays hidden a little longer — and role
and Employee saves already clear the cache.

**Observation, not a finding.** `node scripts/run_dom_tests.js` prints
`SyntaxError: Unexpected token '{'` five times from one inline script jsdom
cannot parse. It appears the same number of times on the committed page, so it
is pre-existing and nothing to do with this change.

## What I would do with more time

Build SEC-9's window and the paid-period guard. Prune the dead `.cal-*` CSS
properly, after separating the nine-box grid's use of `.cal-cell` from the
calendar's. Remove `get_attendance_calendar`. None of it belongs in this commit.
