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

---

# Addendum, 18 October 2026 — SEC-9(a), the filing window

Approved by Surbhi on 18 Oct 2026, with the paid-period guard explicitly **out**.

## What was built, file by file

| File | What changed | Mechanism, and why |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/attendance_correction.py` | `_working_days_away()` (the old `hr_may_act_from` body, now walking either way); `hr_may_act_from()` is three lines calling it; `MANAGER_FILING_WINDOW_KEY`, `DEFAULT_FILING_WINDOW_DAYS`, `manager_filing_window_days()`, `_refuse_outside_filing_window()`; one call in `raise_for_report` | **Extend.** The endpoint and the counter both existed. SEC-10 said reuse the counter and reverse the range, so the counter took a direction rather than gaining a twin |
| `alvoraa_portal/alvoraa_portal/hr_api.py` | One import, one row in `ALLOWED_ORG_SETTINGS`: `range(0, 31)` | **Configure.** The allowlist already takes a numeric range for the late grace. Nothing else needed changing: `get_org_setting` / `set_org_setting` and `_require_hr` are untouched |
| `templates/includes/ess/parts/org-settings.html` | A number field in the existing **Attendance rules** card, with a label and help text | **Configure.** No new card, no new panel, no new endpoint |
| `public/js/ess/portal.js` | `orgLoadFilingWindow()`, `orgSaveFilingWindow()`, and two lines in `orgLoadAttendanceRules()` | **Extend**, following `orgSaveAttendanceSwitch` next to it |
| `tests/test_attendance_correction.py` | New class `TheManagersFilingWindow` (12 tests); three existing manager tests now pick a recent working day | — |

## How the decisions landed

- **Working days, not calendar days.** Counted by `_working_days_away`, on the
  employee's **own** holiday list, which in Frappe carries the weekly offs as
  Holiday rows — so there is no Monday-to-Friday assumption anywhere. The
  holiday query range is reversed with the walk, which is the trap SEC-10
  named: get it wrong and the count silently becomes the calendar answer while
  `basis` still claims it used the holiday list. A test asserts a holiday in
  the range **actually extends the reach**, which is what catches that.
- **No readable holiday list** falls back to calendar days and says so in the
  refusal. That is the tighter answer, so missing configuration narrows the
  window instead of opening it.
- **0 means today only**, and the code says so in a comment. "No limit" was
  rejected: it would make the tightest-looking number the loosest behaviour,
  which is how a control gets switched off by somebody trying to tighten it.
  **This differs from the brief**, which says 0 should mean "nobody may file on
  behalf" — see "Where the brief and the code differ" below.
- **A stored 0 is not read as unset.** `manager_filing_window_days()`
  deliberately does **not** use `get_default(KEY) or DEFAULT`, the idiom next
  door, because a stored "0" is falsy and would silently become 2. Two tests
  pin both halves.
- **The ceiling is 30 working days** — about six calendar weeks, which already
  reaches a month whose pay has run. Past that it is HR's own route, which this
  window never binds.
- **Manager path only.** The check sits after `raise_for_report`'s self-check,
  so a self-named request still goes straight to `raise_correction` untouched,
  and it is **not** on the document, so HR's desk route and an employee's own
  request are unaffected. Three tests pin that.

## Acceptance criteria

| From the spec | How it is met |
|---|---|
| SEC-9(a) — the day filed for is inside the configured window | `_refuse_outside_filing_window` in `raise_for_report` |
| SEC-9(a) — the refusal names the route out | "…ask HR to correct it", with the configured number and the oldest filable day |
| SEC-9(a) — checked at the raise **and** at the confirmation | **Only at the raise.** Not met; see the gaps below |
| SEC-9(b) — the paid-period guard | **Not built, by decision** (Surbhi, 18 Oct 2026) |
| SEC-10 — one counter, the employee's own holiday list, a true `basis` | `_working_days_away`, used by both callers; `basis` is in the refusal |
| SEC-11 — HR may change it, not only a System Manager | `ALLOWED_ORG_SETTINGS` + `_require_hr`, the existing mechanism. Not added to `ACCESS_GRANTING`, per the security engineer's ruling |

## The seven dimensions, against the code as written

| Dimension | Before to after | Why |
|---|---|---|
| Performance | neutral | One cached `get_default` and at most one `Holiday` query per manager filing. No change to any list or report |
| Security | **improves** | A bounded actor's reach went from every past day to a configured window, enforced server side on the one endpoint that path has. The `ignore_permissions` count in this module is still 0 |
| Reliability | **improves** | The walk now has a hard stop, so a holiday list full of holidays cannot spin. The unreadable-list fallback is the tighter side |
| Scalability | neutral | Nothing scales with headcount |
| Maintainability | **improves** | Two counters became one with a direction; the HR wait and the window can no longer disagree about a working day |
| Data integrity | neutral | No stored data changes |
| Compliance / privacy | neutral | No new field read or shown. The one log line carries the Employee document name and nothing about the person |

## NFR notes

- **Queries added per manager filing:** one `get_default` (Frappe caches
  defaults per request) and one `Holiday` read through the app's own
  `holiday_list_for` cache. Nothing in a loop.
- **No index, no job, no cache added.** Nothing measured says one is needed.
- **Permission enforcement point:** `raise_for_report`, server side, after the
  reporting-line check. The screen's number is HR-only through `_require_hr`.
- **Sensitive fields touched:** none. The refusal names a date and a number.
- **Fallback:** no holiday list means calendar days, stated in the message.

## Where the brief and the code differ — said rather than chosen quietly

1. **What 0 means.** The brief (section 7, item 3) says *"0 means nobody may
   file on behalf"*. The code makes 0 mean **today only**: walking back zero
   working days from today lands on today, and today is still a day a manager
   may file for. The task approved on 18 Oct asked for a choice between "same
   day only" and "no limit", and this is the first. **Nobody-at-all is a
   different rule** — it switches the capability off, which is a permission
   question rather than a window — and it is not built. If Surbhi wants 0 to
   mean "off", that is one more line and should be its own decision.
2. **Checked at the confirmation too.** SEC-9(a) asks for the window to be
   re-checked at `decide()`, because a request filed inside the window ages
   while it waits. Not built: the approved task names `raise_for_report` only,
   and `decide()` is HR's path, which the same requirement says the window must
   not bind. **The two halves of SEC-9(a) disagree with each other here**, and
   that needs Surbhi's answer rather than my guess.

## Known gaps and shortcuts

- **Intentional trade-off — the button can still refuse when pressed.**
  `month()`'s `can_request` flag is per month, not per day, and it does not know
  about the window. A manager opening an old month still sees the ask button and
  now gets a refusal that explains itself. Making the flag honest means a
  per-day answer, which is a UX change nobody has approved. Flagged, not built.
- **Declared, not built — SEC-9(b), the paid-period guard.** Surbhi's decision
  of 18 Oct 2026: pay runs in the first week of the following month *after* a
  thorough attendance review, so a correction filed in that window is what the
  review is for.
- **Temporary debt — a test that leaked onto the site.** The first run of the
  settings test called `set_org_setting`, which commits, so that test's
  employees and users escaped Frappe's rollback and broke the next run. Fixed by
  stubbing the commit in that one test, and the 21 leaked Employee rows and 21
  Users were deleted from `test_site`. **The same pattern is live in
  `test_late_minutes_017.py`**, which calls the same endpoint without the stub.
  Not touched here — it is not this slice — but it will leak the same way.

## Commands run, and what they said

| Command | Result |
|---|---|
| `bench --site test_site run-tests --app alvoraa_portal --module ...test_attendance_correction` | **82 OK** (integration) + **9 OK** (unit). Both batches read |
| `... --module ...test_portal_security_010` | **45 OK** + **5 OK** |
| `... --module ...test_org_settings_allowlist_012` | **10 OK** |
| `... --module ...test_nav_consolidation_060` | **15 OK** |
| `... --module ...test_decided_as_045` | **20 OK** — the counter refactor's other caller |
| `... --module ...test_ess_parts_034` | **8 OK** — the page's includes |
| `python scripts/check_app_integrity.py` | 774 checks, OK |
| `python scripts/check_design_system.py` | OK — the visual system holds |
| `node scripts/check_portal_handlers.js` | all reachable and callable |
| `node scripts/check_undefined_js.js` | none |
| `python scripts/check_tag_balance.py` | OK |

## Subtract pass

Removed: a `days_off()` test helper with exactly one caller, inlined into it.
Resisted: a per-day `can_request` answer, a window check in `decide()`, a
paid-period guard, a second counter, and a "window" DocType. Nothing else came
out — the change is one `if`, one read, one shared counter and one input.
