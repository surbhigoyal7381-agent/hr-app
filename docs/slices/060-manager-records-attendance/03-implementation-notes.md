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

---

# Addendum — 18 October 2026: two tenant settings, and the phantom second request

## What was built, file by file

| File | What changed | Mechanism, and why |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/attendance_correction.py` | `MANAGER_ON_BEHALF_KEY` and `manager_on_behalf_on()` (unset = ON); `manager_filing_window_days()` now returns `None` for blank; new `manager_filing_from()`, the single derivation of the boundary; `_refuse_outside_filing_window` returns early on no limit; the switch is checked inline in `raise_for_report`; `month()` gates on both settings and sends `on_behalf_enabled`; `team_days()` answers `can_raise` per person **and per day**; `raise_for_report` refuses a call that arrives without an employee or a date | **Configure, plus the readers.** Both settings are Frappe defaults, the idiom the late-coming grace period already uses, so there is no new DocType, no migration and nothing for an existing tenant to touch |
| `alvoraa_portal/alvoraa_portal/hr_api.py` | both keys on `ALLOWED_ORG_SETTINGS`; blank accepted for the window key only | **Configure.** The endpoints and their HR guard already existed |
| `.../templates/includes/ess/parts/org-settings.html` | the switch, and the window field indented under it as its sub-setting | **Extend** the Attendance rules card that was already there |
| `.../public/js/ess/portal.js` | load and save both settings; the window box is blank for "no limit" and inert while the switch is off; the day detail explains a switched-off tenant; one request per press; nothing incomplete is sent | **Extend** |
| `.../tests/test_attendance_correction.py` | the window class reworked for the new default, plus 12 new tests | |
| `alvoraa_portal/tests/portal_correction_test.js` | 6 new assertions in the jsdom test | |

## The acceptance criteria, as given in the brief

| Asked for | How it is satisfied |
|---|---|
| A master switch, named for the capability | `alvoraa_manager_on_behalf_enabled`, covering attendance now and leave later |
| Default ON, with the reason in a comment | `manager_on_behalf_on()` — unset is on; the comment says a closed default would take a working screen away from DTC silently |
| Blank = no limit, and it is the default | `manager_filing_window_days()` returns `None`; `test_nothing_stored_means_no_limit` |
| `0` = today only, unchanged | `test_zero_means_today_only`, kept |
| Blank and `0` stay distinguishable | `test_blank_and_zero_are_never_confused` proves it on behaviour, not just on the reader |
| The doc no longer contradicts the code | `01c-security-privacy-requirements.md` gains "SEC-9(a) reworked", with her words and the date, and the two reversed decisions are marked where they stood |
| All three places agree | `raise_for_report`, `month()`, `team_days()` — all read the same two functions, and the boundary comes from `manager_filing_from()` alone |
| The existing disagreement about HR | Settled as **direct reports only, for everybody**; `test_hr_gets_the_same_answer_on_both_screens` |
| Both settings on the Org Settings screen, the sub-setting subordinate and inert | Indented under the switch, disabled and dimmed while it is off |
| `d1f0638a` finished, and `None` must mean "offer it" | Finished, and the shadowing bug in it fixed — see below. `test_no_limit_means_the_month_view_hides_nothing` and the jsdom "no limit offers the form on an old day" |
| A day the server would refuse is never offered | `test_the_month_views_boundary_is_the_one_the_guard_enforces`, `test_the_team_list_drops_the_button_on_a_day_too_old` |
| An employee's own old day still works | `test_neither_setting_narrows_an_employees_own_day`, with the switch off **and** the window at 0 |
| Refuse an incomplete request on the page | `acSubmit` and `trSubmit` both check, and the server refuses one too |

## A real bug inside `d1f0638a`

That commit assigned the window's day count to `days` — the same name as the list of days
built just above it. For **every manager viewing a report's month**, the payload came back
with `days` as an integer instead of the month, so the calendar could not draw at all. It
was committed untested and never run. Fixed, and pinned by
`test_the_month_view_returns_the_days_and_not_the_window`.

## The phantom second request — what I found, and what I did

**I could not find a code path in the portal that sends a second, bodyless call, and I am
not going to guess one.** What I did establish:

* Driving the real page in jsdom with the server refusing exactly as it did on `ppj.dev`
  (417 `ValidationError`), **one press makes exactly one call**. `gpFetch`'s retry is not
  involved: it fires only on a CSRF failure (`exc_type === "CSRFTokenError"`, or a 400
  saying "invalid request"), and a `frappe.throw` is neither.
* `raise_for_report` is called from two places in `portal.js`, both with a full argument
  object, and no version in this repository's history ever called it without one.
* Nothing in the page re-issues a request: there is one retry path, no offline queue, no
  `sendBeacon`, no service worker, and no global handler that re-invokes a button.
* A call whose form data is only `cmd` means the body never arrived. From the page that
  needs `args` to be `undefined` or `{}`, which no call site does. Two explanations remain
  open, and both sit outside this file: a second press (nothing stopped one), or a proxy
  redirect, which turns a `POST` into a bodyless `GET` and drops the body — and dev's
  assets are known to go stale, so the browser may not have been running this code at all.

So I made both harmless rather than claiming a cause:

1. `acSending` — while a request is in flight, a second press does nothing. Pinned: "two
   presses send one request".
2. Nothing incomplete leaves the page. Pinned: "a request with nobody named is never sent".
   **Reintroducing the fault showed something worse than an ugly error:** with the guard
   removed and the employee id lost, the press fell through to `raise_correction` and would
   have filed a correction against *the manager's own* attendance.
3. The server answers an empty call with a sentence. Checked **before** `_subject`, which
   would otherwise read a missing employee as "my own month".

## The seven dimensions, against the code actually written

| Dimension | Before → after | Why |
|---|---|---|
| Performance | **improves slightly** | Blank reads no holiday list at all. The per-person boundary is worked out only for the caller's direct reports, only when a window is set — so HR's 363-row page does none of it, and a manager's page does one small read per report |
| Security | **improves** | The capability can be switched off per tenant; an empty on-behalf call cannot become "my own day"; HR no longer gets a button that lets them raise and then answer themselves. `ignore_permissions` ceiling still 0 (`test_sec16_ignore_permissions_does_not_grow` passes) |
| Reliability | **improves** | One press, one request; the `days` shadowing bug fixed; a correct refusal reads as a refusal |
| Scalability | **neutral** | No query that grows with headcount |
| Maintainability | **improves** | One boundary derivation, one rule for who may raise; a helper with a single caller was inlined in the subtract pass |
| Data integrity | **neutral** | Nothing stored changes; blank and `0` kept apart in the reader and in a test |
| Compliance / privacy | **neutral** | No new field, no new visibility, nothing personal logged. The only movement is narrowing |

## NFR notes

* **Queries.** `month()`: unchanged on no limit; one `Holiday` read when a window is set
  (as before). `team_days()`: unchanged for HR; for a manager with a window set, one
  `Holiday` read per direct report on the page, cached by `holiday_list_for`.
* **Indexes, jobs, caches.** None added. None measured as needed.
* **Permission enforcement.** Server side in `raise_for_report` (`_subject`, the direct-report
  check, the switch, the window) and in `hr_api._require_hr` + `_refuse_store_hr` for the
  settings. The screens only avoid offering what the server would refuse.
* **Sensitive fields.** None touched. No name, id or reason enters a log line.
* **Fallbacks.** An unreadable holiday list already falls back to calendar days, which is
  the tighter answer; unset settings fall back to today's behaviour.

## Known gaps and shortcuts

* **Leave is not wired to the switch** — *acceptable simplification.* Her words cover leave,
  and the key is named for it, but no leave on-behalf path exists yet. The day one is built
  it reads `manager_on_behalf_on()` and nothing else changes.
* **`raise_for_report` still lets an HR caller through its direct-report check** —
  *intentional trade-off.* No portal screen offers it to them any more, so narrowing the
  endpoint as well would change behaviour nobody can reach, for no gain. Said out loud so
  the next person does not read the endpoint as the whole rule.
* **The window still binds an HR caller on that endpoint**, although the requirements say
  the window must not bind HR — *pre-existing, unchanged, and now unreachable* from the
  portal, because HR has no button. Left alone deliberately rather than widened as a
  side effect.
* **The cause of the bodyless second call is not known** — *temporary debt.* What removes
  it: the next time it happens, the browser's own network log, or an nginx access log for
  the same second, will say whether a redirect or a second press was behind it. Both are
  now harmless.

---

# The person picker on the Attendance page (19 Oct 2026)

Surbhi, after opening the page as HR and finding a 403-entry dropdown: *"there should be
a way to do a text based search with the drop down"*.

## What changed, file by file

| File | What | Rung on the ladder |
|---|---|---|
| `alvoraa_portal/attendance_correction.py` | `whose_months_i_can_open` now matches the search term against the employee **ID as well as the name**, with Frappe's `or_filters`. Nothing else about it moved. | New code, four lines inside an endpoint that already existed. The cheaper rungs were rejected because the endpoint simply did not match on ID, and HR knows half the company by ID. |
| `public/js/ess/portal.js` | The `<select>` in `acBar()` becomes a text box with a `role="listbox"` under it: `acPickBuild` / `acPickPaint` / `acPickShow` / `acPickType` / `acPickKey` / `acPickBlur` / `acPickChoose`. Debounced 250 ms, searched on the server, 25 rows a page. | New code. There is no Frappe UI combobox on this page to configure; the portal is plain JS. |
| `public/css/ess/panels.css` | `.ac-pick*` — the box, the list, the highlighted row, the focus rings. Existing tokens only. | Customisation of the existing `.ac-bar` block. |
| `templates/.../parts/policies.html` | `#ac-sub` gains `role="status" aria-live="polite"`, so a screen reader is told whose month the page landed on. | One attribute on an element that was already there. |

## The two decisions worth naming

**Shape, not code, from "Apply on behalf of".** It reads the same — same debounce, same row
of name, ID and job, same dropdown under the box — but it is its own code. Two reasons,
both about correctness. The leave picker's data source is `get_all_active_employees`, which
`frappe.throw`s for anybody who is not HR, and this control has to work for a line manager.
And the leave picker is a plain `<div>` of clickable rows: no focus, no arrow keys, nothing
for a screen reader. Sharing one component would have meant generalising the leave modal's
picker — a new abstraction with two users, and a behaviour change to the leave screen that
this slice was not asked to make. **When a third picker appears, extract one then.**

**An empty box is not an empty list.** With nothing typed the list shows "Whole team"
first, then "My own record" / "Choose a person", then the first 25 people the server will
give this caller. So a manager with twelve reports sees twelve names and never has to guess
what to type. Once there is a query those two fixed rows step aside, so Enter lands on a
person rather than on "Whole team" — and clearing the box brings them back. For HR, where
25 is a page of 403, the list ends with a plain line: *"Showing the first 25. Type a name
or an employee ID to find somebody else."*

## How the keyboard works

Tab reaches the box, which has a visible focus ring. Down or Up opens the list and moves the
highlight; it wraps at both ends. Enter takes the highlighted row. Escape closes the list and
leaves what was typed alone. Tab moves on. The box is `role="combobox"` with
`aria-expanded` and `aria-activedescendant`; the list is `role="listbox"` and each row is
`role="option"` with `aria-selected`. The highlighted row carries an outline as well as a
shade, so the highlight does not depend on seeing colour. After a choice the keyboard is put
back in the box, because choosing somebody repaints the whole page. The list opens on click,
on typing and on the down arrow — deliberately **not** on focus, or that focus restore would
reopen the list it had just closed.

## The seven dimensions, against the code as written

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **improves** | The page asked for 500 people on load and now asks for 25. Each search is one indexed `LIKE` on `Employee`, bounded to 25 rows, debounced 250 ms. |
| Scalability | **improves** | Nothing on this screen grows with headcount any more. The 403-row payload was the only thing that did. |
| Security | **neutral** | Same endpoint, same scoping, no `ignore_permissions` anywhere (the module's ceiling of 0 holds). `or_filters` is ANDed with the status-and-reporting-line filters as one bracketed group, so a term can only narrow the answer, never widen it — pinned by `test_a_search_cannot_reach_outside_the_managers_line`. |
| Reliability | **improves** | A failed search says so in words and keeps the control usable. A slow answer to an old query is discarded by sequence number instead of overwriting a newer one. |
| Maintainability | **neutral** | One `<select>` became about 110 lines of picker. Set against that, the inline `style=` on the old control is gone and the whole thing is tested. |
| Data integrity | **neutral** | Read-only control. `acState.people` is the default page only; a search result is never merged into it. |
| Compliance / privacy | **neutral** | No widening of visibility: the rows shown are exactly the rows the endpoint already returned to this caller, and the designation and department on each row were already in that payload. Nothing personal is logged. |

## Personas

* **CXO / HR** — the dropdown they could not use becomes a search box; 25 at a time with a
  line saying so.
* **HR Manager** — same.
* **Line manager** — unchanged in scope, better in use: twelve reports listed with no typing,
  and the search still cannot reach past their own line.
* **Employee with no reports** — unchanged. The control does not appear at all, which is
  what keeps the screen from being a staff directory.

## Tests run, and what they said

| Command | Result |
|---|---|
| `node scripts/run_dom_tests.js` | 10 run, 0 not run, **0 failed**; the correction suite went 13 → **32 passed, 0 failed** |
| `bench --site test_site run-tests --app alvoraa_portal --module ...test_attendance_correction` | **98 OK** and **9 OK** (both batches) — includes the two new search tests |
| `... --module ...test_portal_security_010` | **45 OK** and **5 OK** |
| `... --module ...test_nav_consolidation_060` | **15 OK** (after updating one pin, below) |
| `check_app_integrity.py` · `check_design_system.py` | 774 checks OK · the visual system holds |
| `check_api_paths.py --max 0` · `check_portal_handlers.js` · `check_undefined_js.js` · `check_tag_balance.py` · `check_brand_spelling.py` · `check_tracked_keys.py` | all pass |

`test_nav_consolidation_060.test_the_picker_offers_whole_team` pinned the literal
`>Whole team</option>`. The option element is gone, so the pin now asserts the same fact
about the control that exists: the row is built with that label and `AC_TEAM` is still the
value behind it.

## Known gaps and shortcuts

* **The leave modal's picker is still mouse-only** — *declared, not fixed.* It is a different
  screen and a different endpoint, and fixing it was not in this slice. Worth a ticket.
* **`scripts/check_attendance_strip.js` was already broken before this work** —
  *pre-existing, reported, not fixed.* It evals functions pulled out of `portal.js` by name
  and now dies on `ReferenceError: acOutsideWindow is not defined`, a helper added by
  commit `d1f0638a`. It is **not** in CI. Fixing it is a separate, small job.
* **Nothing was verified in a real browser.** The proof here is 32 jsdom assertions plus
  the checks above; the focus ring, the phone width and a real screen reader have not been
  seen by a human on this change.
