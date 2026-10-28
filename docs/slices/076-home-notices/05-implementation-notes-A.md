---
slice: 076-home-notices
artifact: 05-implementation-notes-A (Part A, Home only)
author: hrms-fullstack-engineer
date: 2026-10-28
status: built and tested LOCALLY on branch slice/076-home-notices. Not pushed. No server, shared bench, dev or production site touched.
tier: 2 (usage-discipline). Strategy approved by Surbhi on 28 Oct 2026; her answer for a CXO on Pending: System Manager, counts by kind.
---

# 076 Part A: Home. Implementation notes

## Fix pass after the review (06-review-A.md), 28 Oct 2026

Surbhi approved these. Local only, not pushed.

| # | Review finding | What I did | Result |
|---|---|---|---|
| 1 | Shift change rows lead nowhere | I checked: the live portal has **no screen where a manager decides a shift change** (only the employee's own request form; no approve endpoint). Shift-change rows are **left out of Pending**, and the chip and CXO rows no longer count them. **Gap for Part C (or a decide screen): a manager cannot see or act on shift requests from Home.** | DOM test: the row and the count are gone |
| 2 | Goal update rows open My Goals | They open the **Team** panel, where the Approve buttons are. **Not checked:** that Team's list (`hr_api.get_pending_approvals`) shows the same updates the inbox counts; the two use different endpoints. Someone should compare them on a fixture with goal updates. | DOM test: opens `team` |
| 3 | AC-72 | `attendance_correction.not_yours_yet` asked the permission system whether the employee's manager may submit, once per queued fix. It now asks **once per manager** (the existing per-call memo). `inbox_api` also works the whole queue out **once per call**, not once for the count and again for the rows. Behaviour is identical (all 042, 045, 068 attendance tests pass). New test `TestTheQueueDoesNotCostAQueryPerFix` fails with the old line (3 lookups) and passes with the new (1). | `get_inbox`, HR caller: **111 to 36 queries** at 980 people, **33 to 28** at 20 people. Payload unchanged (23 KB). p95 438 ms to 190 ms (a record, not a pass: wall time moves). **Still not perfectly flat:** 28 to 36, because it is now one lookup per distinct manager in the queue, and the large fixture has more managers. Employee 14 to 17, manager 23 to 23. |
| 3b | My notes said `get_nav_counts` "already runs on every page" | **Wrong, corrected.** Only the discarded `/hrms-employee-next` page calls it. On the live portal this cost was entirely new with Part A. | |
| 4 | CXO label | "across your companies" is now "{n} waiting · your queue". | DOM test |
| 5 | Team goals uncapped | Home shows **five people** then a "View all N" button that opens the existing Team panel (no new screen). | DOM test. **Browser check: still 0 failures on the grid, but 24 of 45 cells (was 20) carry an existing card over 2x the median.** Capping people did not cure it: five people at three goals each is still about 1,500 px, and the median fell (302 px) because the new cards are short. Cells by card: My Goals 14, Team goals 6, My documents 4. A further cap (one goal per person, or five goals) or Surbhi's written acceptance is needed. |
| 6 | `check_scope_traps.py` skipped unparsable files | It now reports "cannot be parsed, so it was not checked" and fails. `--self-test` proves a bad file is reported. | OK |

Home's total queries, after the fix (before the fix in brackets), at 980 people: store HR 82 (157), company HR 82 (157), System Manager 72 (147), manager 69 (69), employee 62 (62). At 20 people: store and company HR 74 (79), System Manager 70 (75), manager 69, employee 59. `measure_076.py` was re-run on `test076l` and `test076s`.

### Second fix pass: AC-112 (Surbhi chose "cap the three old cards")

- **My Goals** shows 3 goals (was 5); the header's "Full Portal" link has the rest. **Team goals** shows 3 people with 1 goal each, then "View all N" opening the Team panel. **My documents** has no screen of its own, so it cannot say "View all": it shows about three rows and the rest scroll inside the card (keyboard-reachable, labelled). Nothing is hidden. The new Pending and Notices cards are unchanged.
- The first try (5 people, 3 goals each) still failed; 3 goals per person would too (a person with 3 goals is about 300 px), so I went to 1 goal per person. That is more than the suggested start.
- **Browser check: 45 of 45 cells pass, 0 noted, 0 failing AC-112.** The check itself is unchanged.
- **Open item answered, and it is bad news: Team's list does NOT match the inbox's goal-update count.** On the 980-person fixture: manager inbox 19, store HR 59, company HR 59, System Manager 59; the Team panel's "Pending Progress Approvals" shows **0** for all of them. They are different things: the inbox counts Goal Progress Updates and KPI Progress Log rows (what the old bell listed); the Team panel lists goal *evidence* (`hr_api.get_pending_approvals`). So a "Goal update" row in Pending opens a screen that does not list it. The inbox row carries no goal id, so Pending cannot open the goal drawer (where `approveUpdate` lives) either. **Fix needs a decision:** add the goal id to the goal-update row (a new key, so it needs Surbhi's yes because of SEC-19) and open the drawer. Until then, a manager cannot approve goal progress updates from anywhere on the live portal now that the bell list is gone. `measure_076.compare_goal_approvals` reproduces the numbers.

### Third fix pass: the goal id on goal-update rows (Surbhi said yes)

- **What changed.** The `goal_updates` inbox row has one more key, `document`: the Individual Goal (or KPI) the update belongs to. It is read in the same query as the row, through the same scope subquery (`goals_api._pending_approvals_scope_query`), so it can only name goals inside the caller's scope. I did not use `employee_in_scope` or `permitted_employee_filters`: there is no id coming from the caller to check, so nothing to lay over a scope. A goal update row now opens the goal drawer on that update (KPI rows open the KPI log); with no id it falls back to the Team page. Approve and Reject are the existing buttons in those drawers, drawn when the server says `can_action`.
- **Tests (new, `TestGoalUpdateRowsCarryTheGoalOnlyInScope`, 5 tests, all pass).** A manager gets the id of their own report's goal and no other; a manager of someone else gets no id for it, and calling `approve_goal_update` on it is refused and leaves the update Pending; an ordinary employee gets no rows and no ids; HR and System Manager get both goals in scope; the manager can approve the update the row points at. DOM test: goal row opens `gpOpenGoalDetail(goal, update)`, KPI row opens `pfOpenLog(kpi, update)`, no id falls back to Team.
- **End to end on the real site (test076, Chrome, real login as the manager):** Pending showed "Goal update · Smoke goal", tapping it opened the goal drawer, the drawer had an Approve button, pressing it changed the update to **Approved** in the database. No page error. The smoke goal was deleted afterwards.
- **Cost.** Query counts are unchanged: store and company HR 82 at 980 people (74 at 20), System Manager 72 (70), manager 69, employee 62 (59). Payload grew about 1.5 KB for HR (24.8 KB for the inbox call) because each of the 50 rows carries one id. Times in that run are not comparable (the dev server was running beside it).
- **SEC-19 note for the review:** `document` is a second key added to `ROW_KEYS` for `goal_updates`; `test_every_part_row_is_the_old_keys_plus_waiting_since` now names it.
- Balance check after this change: **45 of 45 pass, 0 noted.** DOM suite 17 of 17.

### Fourth fix pass: the second review's recommendations (Surbhi said yes, 28 Oct 2026)

1. **KPI dead end fixed.** `performance_api.get_kpi_update_log` now returns `can_action` on each row, by the rule `approve_kpi_update` already enforces: never your own KPI; the reporting manager; HR for companies they look after. 11 lines, in a file outside the slice, approved. **What HR may read is unchanged**: the read check was not touched, so the older gap (any HR-role user can read any KPI's log by id, across companies) is still there and is a separate item for the security engineer. The drawer then draws Approve and Reject, as it does for goals. New tests (4): the in-scope manager and HR get `can_action` true; the employee themselves get false and `approve_kpi_update` is refused; an outside manager can neither read nor approve and the update stays Pending; the manager can approve what the log offered. **I checked KPI end to end in the tests, not in the browser** (the browser end-to-end earlier used a goal).
2. **AC-72, accepted in writing by Surbhi on 28 Oct 2026:** HR's Home cost grows with the number of *different managers* in the attendance-fix queue (28 to 36 queries for an HR caller between 20 and 980 people), no longer with the length of the queue. No code change.
3. **Team goals button.** It opened the Team page on its attendance tab, which has no goals list, so "View all N" was untrue. It now says "See your team of N" and opens the Team page; goals are reached by tapping a person there. No new screen.

Not changed and still open (from the review): CXO "Goal and KPI updates" opens the Team page, which lists none of them; goal and KPI rows have no "waiting N days"; shift changes appear nowhere for a manager; KPI log read scope (above).

### Fifth fix pass: the CXO row, and KPI in a real browser (Surbhi chose A)

- **CXO "Goal and KPI updates" row.** It is a count with no single id, so the smallest honest behaviour is: it opens the **oldest** goal or KPI update in the caller's scope (the first row `get_inbox` already returned), and its label says so: "N waiting · opens the oldest". Other CXO rows are unchanged. No new key and no new query: it reuses `document`, so SEC-19 holds as before (ids only from the scope subquery).
- **Tests.** DOM: the goal row says "opens the oldest" and opens that goal; the leave row still opens Team. Python: a System Manager (the CXO, by Surbhi's answer) gets the ids in scope (existing test). **"CXO outside scope" does not exist for a System Manager: `access.permitted_companies` gives a System Manager every company on the site, by design** (a company User Permission does not narrow it). So the outside-scope test is the nearest real case: HR limited by User Permission to another company gets no id and `approve_goal_update` is refused (`test_hr_limited_to_another_company_gets_no_id_and_cannot_approve`). If Surbhi wants a System Manager who can be narrowed, that is a change to `permitted_companies`, not to Home.
- **Real browser, KPI, on test076 (Chrome, real login as the manager).** What I saw: Pending listed "G076A Staff · KPI update · Smoke KPI · Open"; tapping it opened the KPI log modal; an Approve button was visible; I pressed it; the database then showed the update as **Approved**; no page error. The test KPI was deleted afterwards.
- Balance check 45 of 45, DOM suite 17 of 17, static checks and scope-trap script pass; Python modules touched pass (see the run in the report).

The sections below are the first write-up. Where they differ from this table, this table wins (bad news 1, the `get_nav_counts` sentence, and the CXO wording in difference 2).

## Bad news first

1. **Home is not flat for HR and System Manager callers.** `get_inbox` (the Pending card) sends 33 queries on the 20-person fixture and **111 on the 980-person one** for an HR caller (104 for a System Manager). Payload 3 KB to 23 KB. p95 437 ms against a 500 ms budget, so it is inside the budget, but AC-72 says the count must be the same at both sizes, and it is not.
   - Cause (measured, not guessed): one `tabDocShare` lookup **per queued attendance fix**, sent twice (once to count, once to list). It is `attendance_correction._with_decide_flag`, which the inbox has used since slice 042. The cost follows the **depth of the correction queue** (40 on the large fixture), not headcount itself. Employees and managers are flat (14 to 17 and 23 to 23).
   - It already runs on every page through `get_nav_counts`. Home now pays it a second time.
   - I did **not** change `attendance_correction.py`: it is not in this slice, and the strategy's fallback (a `limit` argument) cannot remove it, because the count has to scan the whole queue. **Decision for Surbhi:** (a) accept it for now; (b) one small separate change that reads the DocShare rows once for the whole queue, which would also make the bell's count on every page cheaper; (c) a 30 to 60 second cache (not recommended before (b)). I recommend (b).
2. **The "no card over 2x the median" rule (AC-112, rule 2) is not met in 20 of 45 cells.** In every one of them the tall card is an EXISTING card that this slice leaves alone: Team goals (it lists every direct report with three goals each, no cap; 658 px with only 2 reports, 11,000 px with 40), My Goals when stretched beside it, and My documents with 12 rows. The grid itself and the two new cards pass every cell. The prototype used three-row stand-ins for these cards, which is why it passed. Capping them (for example five people and five documents with "See all") changes their content, so it needs Surbhi's yes. I did not do it.
3. **The grid is 984 px wide at 1280, not 992** (two 484 px columns, not 488). The live shell pads the page by 28 px and the design's arithmetic used 24. Also, the live portal starts with the sidebar collapsed to 56 px, so a 1280 laptop out of the box gets a 1224 px grid unless the person pins the sidebar. Both states pass.
4. **The live portal has no bell on a laptop.** The bell is on the phone header only (`.mob-header` is phone-width). The prototype draws a bell on the desktop top bar. I did not add one. On a laptop the Notices card is the only place the number shows. Needs her yes if she wants a desktop bell.
5. `.claude/context/ux-learnings.md` shows as modified in this worktree. It is not mine and I did not commit it. I set it aside by copy while rebasing and put it back.

## What changed, file by file

| File | Change | Rung and why not lower |
|---|---|---|
| `alvoraa_portal/inbox_api.py` | One key, `waiting_since`, on every part's row (and in `ROW_KEYS`). Leave, shift, attendance and "my requests": the filing date. Goal update: its logged date. Policy: effective date, else last change. Nothing else added. | 4, one key. Without it "oldest first across kinds" cannot be drawn. |
| `alvoraa_portal/hr_api.py` | `get_portal_activity` deleted. `action_leave(leave_id, action, reason=None)`: a decline reason of 1 to 140 characters, HTML-escaped, saved as a Comment with the subject "Decline reason". `get_leave_summary` adds `decline_reason` to the caller's OWN Rejected rows, one query. | 4. A reason has no field on Leave Application; a Frappe Comment is the cheaper rung. |
| `alvoraa_portal/notices.py` (new) | `notices_feed(see_all=0)`: the caller's own Notification Log rows about grooming marks and reviews, through `get_list`, behind `grooming._readable`, fixed field list, `unread` count, `any` flag. Card: unread, five rows. Sheet: last 30 days, unread first. | 4. No wrapper for marking read: Frappe's own `mark_as_read` already limits to the caller's row. |
| `templates/includes/ess/parts/home.html` | Activity card and the old "Pending approvals" banner removed. One `home-grid` in the design's order: Pending, Notices, Leave balance, Holidays, Goals, Team goals, Documents, Policies. Today strip moved inside the check-in card. | markup |
| `public/css/ess/panels.css` | Fixed 300 px column and its rules removed; Activity styles removed; old bell-panel and grooming-bell styles removed; new `home-grid` and `hm-` block. | CSS |
| `public/css/ess/frame.css` | The bell is a button: padding, font and a focus ring. | CSS |
| `templates/includes/ess/frame.html` | Bell is a `<button>` named "Notices" (reworded "Notices, N unread" by script). The old dropdown panel is removed. | markup |
| `public/js/ess/portal.js` | New block (prefix `hm` / `nt`): Pending, the leave sheet, Notices, the sheet, See all, the bell's number, the grid reflow, one click handler. Removed: `homeActivity`, `renderActivityFeed`, `renderTimeline`, `homeActionLeave`, `toggleHomeApprovals`, the banner code, the grooming bell (`gmBell`, `gmPaintBadge`, `gmBellLoad`), `loadNotifPanel` and its click handler. Two one-line additions: `is_system_manager` in the portal context, and `hmRefreshIfStale` in `switchPanel`. The employee's leave list shows "Declined: reason". | 4 |
| `scripts/check_portal_trays.js` | Inventory: `.notif-panel` out (it no longer exists), `.hm-ov` in. | test list |
| `scripts/check_scope_traps.py` (new) and `.github/workflows/ci.yml` | AC-117: fails on `dict(permitted_employee_filters(...), name=...)` and `{**permitted_employee_filters(...)}`; read with `ast`, so prose does not trip it; `--self-test` proves it fails. The `ignore_permissions` ceiling (AC-118/109) stays in `test_portal_security_010`: `hr_api.py` 70 to 67, `notices.py` 0. | 4 |
| Tests | `test_home_076.py`, `test_notices_076.py`, `alvoraa_portal/tests/portal_home_076_test.js` (registered in `run_dom_tests.js`, expected count 16 to 17), `scripts/browser_check_home_076.js`, `measure_076.py`. | |

Three commits on the branch, rebased onto `origin/dev`: `3ad7c61d` (server), `162d4978` (front end), `e93aed0c` (tests and checks).

## How Part A ships alone

- **No "Send a notice" button and no expense sheet exist in the code.** There is nothing to hide: the Notices footer holds only "See all"; the Pending sheet handles leave only; the inbox has no expense part. The DOM test fails if a "Send a notice" button or the words "Send a notice", "expense_approvals" or "Expense claim" appear in the grid markup.
- No Birthdays card and no organisation setting. The grid was drawn and measured without Birthdays, which is the design's own "switch off" layout.
- Notices in A shows grooming alerts only, with the drawn empty sentences.

## Acceptance criteria for A

| AC | Status |
|---|---|
| 57 unread only, chip "N unread" (pinned is B) | met (DOM test) |
| 58 chip equals bell, from one function | met: `test_bell_and_card_share_one_count`, DOM test (card, badge, label). I tested one user with several states, not "three users" literally; one function serves them all |
| 59 tap opens a sheet and marks read through Frappe's `mark_as_read` | met (DOM test names the call and the docname) |
| 60 See all, 30 days, "Read" marks; bell opens the same sheet | met |
| 61 empty states | met, as drawn |
| 62 B cannot mark A's row; Guest refused; fixed fields | met (`test_a_colleague_cannot_read_or_mark_my_notice`, `test_guest_is_refused`) |
| 63 hostile text is text | met on card, sheet and See all; also on Pending (DOM test). "Notices I sent" is B |
| 64 one query regardless of headcount | met: 2 queries, same at 1 and 41 notices (`test_the_query_count_does_not_grow...`). The `EXPLAIN` on 100,000 rows is B's (no Announcements yet) |
| 65 failure box and skeleton | met (DOM test: Try again on both cards; skeleton is in the markup) |
| 66 Pending from `get_inbox`, no second filter | met (the card calls only `get_inbox`) |
| 67 five rows, oldest first across kinds, Review/Open, whole row a button | met (DOM test) |
| 68 old keys plus `waiting_since`; total still the sum | met (`test_every_part_row_is_the_old_keys_plus_waiting_since`, `test_the_count_is_still_the_sum_of_the_parts`) |
| 69 CXO sees counts by kind, no people | met with System Manager = CXO (her answer). See difference 2 below |
| 70 empty sentences; See all up to 50 per kind | met |
| 71 existing inbox tests pass unchanged | met: 25, 17+2, 2, 6, 9 passed. Only `test_portal_security_010`'s ceiling row changed |
| 72 flat in headcount; p95 under 500 ms | **not met for HR and System Manager callers** (bad news 1). p95 437 ms |
| 73 calls fire together; each card its own skeleton and failure box | met |
| 74 to 76 leave sheet, reason 1 to 140, decided row leaves | met (DOM and Python). The bell does not move on a decision, because it counts notices now; the left menu's Team badge steps down as before |
| 108, 109 Activity gone; `ignore_permissions` ceiling | met (`test_activity_endpoint_is_gone`, `test_nothing_in_the_app_still_asks_for_it`, ceiling 70 to 67) |
| 110 grid | met except the 992/488 arithmetic (bad news 3) |
| 111 order, phone order | met (browser check: check-in, Pending, Notices in all 15 phone cells) |
| 112 balance rules | grid, gaps, caps, no sideways scroll, phone order, columns: met in all 45 cells. Rule 2 (2x median): **not met in 20 cells** by existing cards (bad news 2) |
| 113 new cards never hidden; old cards still hide | met |
| 114 60 cells | 45 run, not 60: the Birthdays "on" half is Part C. 30 are the real set (1280 with the sidebar pinned, and 360) plus 15 with the sidebar collapsed |
| 115 accessibility | rows are buttons; sheets `role=dialog`, `aria-modal`, focus in, Escape closes, focus returns (DOM test); Tab is trapped in the sheet; focus ring 3 px; bell name "Notices, N unread"; nothing under 12 px in the new rules; field text 16 px. **Not checked:** a screen reader, and 200% zoom |
| 116 Today strip inside the check-in card | met (DOM test) |
| 117 CI trap script | met (`--self-test` and the repo scan both pass) |
| 118 `ignore_permissions` count | met through the existing ceiling test, as Surbhi's decision 5 recommended |

## Tests run, and what they said

All Python in my own container `hrlocal-076`, site `test076`, one module at a time, after checking no other run was going. `bench run-tests` prints **two batch summaries**; both are listed.

| Module | Batch 1 | Batch 2 |
|---|---|---|
| `test_home_076` (new) | 5 ran, OK | 8 ran, OK |
| `test_notices_076` (new) | 9 ran, OK | |
| `test_inbox_parts_042` | 25, OK | |
| `test_inbox_counts_034` | 17, OK | 2, OK |
| `test_count_matches_list_045` | 2, OK | |
| `test_browser_call_args_045` | 6, OK | |
| `test_frame_endpoint_registry_034` | 9, OK | |
| `test_leave_permissions` | 12, OK | |
| `test_leave_063_rules` | 43, OK | |
| `test_decide_now_068` | 13, OK | |
| `test_leave_privacy_045` | 11, OK | |
| `test_grooming_066` | 64, OK | 1, OK |
| `test_portal_security_010` | 45, OK | 5, OK |
| `test_home_page_024` | 21, OK | |
| `test_home_holidays_035` | 8, OK (1 skipped) | |
| `test_home_api_042` | 27, OK | |
| `test_no_repeat_queries_044` | 11, OK | |
| `test_scale_flatness_044` | 15, OK (1 skipped) | |

- **Failures I met and what they were.** (1) The first run of `test_home_076` on a fresh site gave 7 errors "Not permitted" from Frappe HR's leave check: the named approver was not on the employee record. I put the approver on the records, as real data has it; it has passed on every run since. (2) Two neighbour runs gave "Throttled" and then a type error: Frappe limits user creation to 60 an hour, and `set-config` stores the limit as text unless `--parse` is given (the 044 note says the first half, not the second). (3) One of my own notices tests used a query that does not do what I thought; fixed in the test.
- **Guards proven able to fail.** The DOM test was run with the oldest-first sort flipped and the bell number off by one: nine checks went red, then the file was restored. `check_scope_traps.py --self-test` fails on the bad shapes.
- DOM suite: `node scripts/run_dom_tests.js`: **17 run, 0 failed** (my new file is 65 checks). jsdom is not installed in this worktree; I borrowed `node_modules` from `.claude/worktrees/063-housekeeping` through `NODE_PATH` (same pinned version, 27.1.0).
- Static checks, all OK: `check_app_integrity.py` (842), `check_api_paths.py --max 0`, `check_undefined_js.js`, `check_portal_handlers.js`, `check_tag_balance.py`, `check_design_system.py`, `check_brand_spelling.py`, `check_portal_trays.js --static`, `check_day_widget.js`, `check_scope_traps.py`. `check_design_system.py` caught me twice (two new font sizes and a gradient); both removed. `ruff` on the alvoraa apps is non-blocking in CI and already reports 931 findings; my new files add only style notes.
- **Not run:** the full suite (CI does), the other slices' Python modules, anything on a real tenant, any other browser than Chrome.

## Real browser

- **Balance check** (`scripts/browser_check_home_076.js`, Chrome 1280 and 360 px, five personas, none, few and 200 rows): the page is the real `hrms-employee.html` with its real CSS and `portal.js`, laid out by a real browser. **The server is a stub that answers from synthetic data.** So the cards, renderers, CSS and reflow are real; the rows in them are not. Result: **45 cells, 0 failures on the grid and the new cards; 20 cells noted for an existing card over 2x the median** (My Goals 12, Team goals 6, My documents 2). Gaps are 24 px in every cell (the grid gap, never more); columns end together (a lone last card spans the row); Pending and Notices never show more than five rows; no sideways scroll; phone order is right. Pairs that stretch beyond 1.5x on natural height are named by the script; they are Leave balance with Holidays (1.6x, only with 30 holidays) and Goals with Team goals (2.4x with two reports, 21x with 40).
  - Harness traps: the page is a Jinja template, so unrendered comments printed as text and made the phone header scroll sideways, and the design tokens live in a separate include. Both are handled in the script, with the reason in a comment.
- **Smoke against the real site** (my container, real login as a manager, Chrome at 1280 and 360 px): Pending showed the real leave request with "Review", the chip said "1 waiting", Notices showed the empty card, the leave sheet opened with Approve and Decline, `get_inbox` and `notices_feed` answered 200, no console error. I looked at both screenshots. I did not approve or decline through the browser; that path is covered in jsdom and in the Python tests.
- **Not checked:** Safari or any phone, a real DTC-size login in a browser, a screen reader, 200% zoom, the dark theme by eye.

## Measurements: Home before and after

Fixtures: slice 044's two shapes, built on my own sites (`test076s` 20 people, `test076l` 980 people). Method: `measure_076.py`, which reuses 044's: three warm-ups, 20 runs, every SQL statement counted. "Before" is `origin/dev` code in a second container of mine; "after" is this branch. Wall time varies more than the effect on this machine (the same call gave 80 ms and 131 ms in two runs), so the **query count and bytes are the proof; times are a record**.

Home's calls, per persona, total queries (payload bytes):

| Persona | Before, 20 people | Before, 980 | After, 20 | After, 980 |
|---|---|---|---|---|
| Employee | 50 (2,938) | 50 (2,938) | 59 (4,298) | 62 (4,606) |
| Manager | 53 (7,981) | 53 (12,419) | 69 (10,630) | 69 (18,637) |
| Store HR | 53 (2,938) | 53 (2,939) | 79 (5,728) | **157 (26,186)** |
| Company HR | 53 (2,938) | 53 (2,939) | 79 (5,978) | **157 (26,435)** |
| System Manager | 51 (3,299) | 51 (2,939) | 75 (6,439) | **147 (26,435)** |

- Before was flat in headcount. After is flat for Manager (69 and 69) and nearly so for Employee (59 and 62), and **not** for HR and System Manager (bad news 1).
- What Home stopped calling: Activity (4 queries), the bell's goal count (2 to 5), `my_notices` (1). What it started: `get_inbox` (14 to 111) and `notices_feed` (2, flat at both sizes, 40 bytes when empty).
- `get_inbox` on the large fixture: employee 17 queries, p95 59 ms; manager 23, p95 96 ms; store HR 111, p95 438 ms; company HR 111, p95 437 ms; System Manager 104, p95 378 ms. `notices_feed` p95 8 to 12 ms.
- The worst case is deeper than this fixture: a queue of 100 fixes would send about 200 DocShare statements. DTC's real queue depth is not known to me.

## The seven dimensions, against the code I wrote

| Dimension | Before to after | Why |
|---|---|---|
| Performance | **degrades** | Home makes 9 to 26 more queries (small tenant) and up to ~100 more for HR when the correction queue is deep. Notices adds 2. Activity, the goal count and the banner are gone. |
| Security | improves | An endpoint with three `ignore_permissions` is gone; the ceiling is 67. The notices read is the caller's own rows through `get_list` with a fixed field list; marking read is Frappe's own call. The reason is escaped before it is stored. No `ignore_permissions` added. |
| Reliability | neutral | Each card has its own skeleton, failure box and Try again. A lost answer on Approve or Decline shows the existing "may have gone through" line and keeps the button off. A double tap sends once. |
| Scalability | **degrades for HR** | Same cause as Performance. |
| Maintainability | improves | One source for the bell and the card; Activity, the banner and the dead bell panel are deleted. Cost: 400 more lines in a 20,000-line file, in one block with its own prefix. |
| Data integrity | neutral | The reason is a Comment written in the same transaction as the decision. Marking read only ever changes the caller's row. Home refreshes after a minute away, so the card is not stale at lunch. |
| Compliance and privacy | improves | Activity (a record of what people clicked) is gone. A colleague cannot read a notice or a decline reason; a CXO's Pending shows no person. The decline reason is read by the employee only. |

## Differences from the prototype (Surbhi's yes needed for each)

The parity table's rows for Part A are built as drawn, with these differences:

1. **Grid width 984/484 at 1280, not 992/488** (bad news 3). Not a choice: the shell's padding.
2. **CXO rows say "across your companies" as drawn, but the number is the CXO's own queue from the inbox**, not a count across every company. The inbox cannot give the second. A System Manager with no employee record sees "Nothing waiting on you". If she wants the real across-companies number, that is a new count and a decision.
3. **"Your request" rows:** the second line says "Waiting for your approver", not the approver's name as drawn. The inbox sends no approver name and its rules forbid adding one.
4. **My Goals and Team goals are styled as cards** (the prototype draws them as cards; before, they were bare lists). Their content is unchanged.
5. **No bell on a laptop** (bad news 4).
6. Two things the prototype shows are not in A by design: "Send a notice" and the Pinned mark (Part B), the Birthdays card (Part C).

## Traps from the strategy that I met

| Trap | What happened |
|---|---|
| T7 leave has no reason field | Comment with a subject marker, shown on the employee's own Rejected row only; an ordinary note is not shown as the reason (tested). |
| T8 the bell changes meaning | Bell = unread notices only, from `notices_feed`; goal and KPI approvals are in Pending. Marking read now happens on tap, so the number stays until each notice is opened. Grooming notices that are unread today stay counted until each is opened. |
| T10 Desk draws a subject as HTML | The decline reason is escaped before it is stored (tested). Notices stay as Part B's. |
| T11 write names | `mark_as_read` and `action_leave` start with write verbs, so they wait for a real answer and cannot be tapped twice. |
| Bad news 1 and 2 of the strategy | Confirmed: the live portal reused nothing for Pending; the inbox routes are for the discarded page, so Pending has its own kind-to-screen map (`HM_SCREEN`). |
| New, not in the strategy | The inbox's attendance part is the cost (above); existing cards have no cap (above); the sidebar defaults to collapsed. |

## What else moved while I worked

- At the start `origin/dev` had six commits I did not write (062 phone install, ALV-222 sign-out, ALV-232, a button-check fix); I fast-forwarded to them. They touch `field_app_pwa.py`, `auth.py`, `hooks.py`, `frame.css`, `frame.html`, `hrms-employee.html`, `test_home_page_024.py`.
- Later `b2547d1f` ("cleanup pass over 062, ALV-222 and ALV-232") came in: `auth.py`, `field_app_pwa.py` and 6 lines of `frame.html` around the sign-out. My bell edit is a different part of that file. The rebase had no conflict. I proved their lines survived: `portal_signout_222_test.js` passes (10), `frame.html` still renders on the real site and contains the sign-out, and `test_home_page_024` passes (21).
- I did not touch the main checkout.

## Subtract pass

Removed from my own output: the `kind` key from the notices payload (nothing in A uses it; Part B adds it with the Pinned mark) and two unused variables in the balance script. Removed from the product: the old bell panel (HTML, CSS, JS), the `.act-*` styles, `renderTimeline`. What I kept that a reviewer might question: `measure_076.py` (it is how the numbers above were made and Part B/C re-run it), and the 60-second refresh when Home is opened again (without it the card shows the morning's list).

## Known gaps

| Gap | Label |
|---|---|
| Home grows with the correction queue for HR (bad news 1) | **dangerous debt if the queue is deep at DTC.** Escalated above with a recommendation. Not hidden. |
| Existing cards have no cap (bad news 2) | intentional trade-off pending Surbhi's yes |
| `get_employee_dashboard` still returns `pending_approvals` and runs its query on every Home load though nothing reads it | acceptable simplification; removing it touches six test modules |
| `grooming.my_notices_seen` has no caller now | acceptable simplification (the endpoint stays) |
| The notices read looks at the newest 100 rows, so "N unread" is exact up to 100 | acceptable simplification; grooming notices per person are few |
| No desktop bell | for Surbhi |
| Leave-decline reason is shown on the Leave list only, not in a notification to the employee | as the spec says; B's notices may carry it |
| Containers `hrlocal-076`, `hrlocal-076b`, `hrlocal-076-redis`, `hrlocal-076-proxy` are STOPPED, not removed, and so is the extra worktree `.claude/worktrees/076-before` (old code, for the before numbers). They are mine and local. If `hrlocal-076` is started again it may get a new network address, and the database then refuses it until its user is granted that address (what I did for `hrlocal-076b`). Sites: `test076`, `test076s`, `test076l` | remove when Surbhi has read this |
