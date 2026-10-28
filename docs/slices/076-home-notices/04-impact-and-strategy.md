---
slice: 076-home-notices
artifact: 04-impact-and-strategy (change process steps 1 and 2)
author: hrms-fullstack-engineer
date: 2026-10-27
status: waiting for Surbhi's approval. No product code written. Nothing committed, pushed or deployed.
inputs: 01b-surbhi-decisions.md (last sections win), 01c, 02-design.md, 03-functional-spec.md, 07-devops-inputs.md, the code on origin/dev
---

# 076 · Impact analysis and strategy

ALV-240 · Engineer · 27 Oct 2026 · I propose; Surbhi decides.

The handoff contract calls this file `00-impact-analysis.md`. In this slice the numbers 01 to 03 are taken, and the coordinator asked for `04-impact-and-strategy.md`, so that is its name.

Every claim below was read in code unless it is marked `[UNVERIFIED]`. Line numbers are on the worktree at `a964985e` (5 commits behind `origin/dev`, see section 1).

---

## Bad news first

1. **The live Home has nothing to reuse for Pending.** DevOps OPS-2a says "reuse the counts `get_nav_counts` already fetched in the frame". That is true only for the discarded `/hrms-employee-next` page. The live portal (`hrms-employee.html` + `portal.js`) never calls `get_nav_counts` or `get_inbox` (grep: only `next-frame.js`, `next-home.js`, `next-inbox.js` call them). So Pending adds the **whole** inbox cost to Home: up to 6 count queries plus up to 6 row queries (7 of each after Part C). What Home loses in return: `get_portal_activity`, the bell's `goals_api.get_pending_approvals_count`, and the old leave banner. Nobody has measured either side. I measure before I build the card (section 7).
2. **The inbox routes do not fit the live portal.** `inbox_api.PARTS` carries routes like `#team`, `#growth`, `#time/fix` (`inbox_api.py:74-81`). Those are the discarded page's routes. The live portal moves between screens with `switchPanel('team')` and so on. The Pending card needs its own small "kind → screen" map in `portal.js`. The server routes stay as they are.
3. **There is no "My profile" screen in the live portal.** The design puts the birthday opt-out tick on "My profile" (prototype line 432). The live portal has no such panel (grep of every `switchPanel('…')` and of "my profile": none). The account menu's "My Account" goes to Frappe's own `/me` page. Part C needs a home for the tick. This is decision 2 in section 12.
4. **Decision 4 makes Part C depend on DTC's data.** She chose: a claim with no approver is **refused** ("Ask HR to set your approver."). If DTC staff have no `expense_approver` on their Employee record and no expense approver on their Department, every portal expense claim at DTC is refused the day Part C ships. I could not check DTC (production is off limits). PPJ has zero claims. Someone must read that count before Part C goes to a live tenant.
5. **The bell changes for everyone in Part A, and grooming notices change how they get marked read.** Today opening the bell marks every grooming notice read at once (`grooming.my_notices_seen`, `portal.js:9846`). In the approved design a notice is marked read when it is **tapped**. So after Part A the bell number stays until each notice is opened. This follows the drawing; I state it so nobody is surprised at DTC.
6. **Two things 01c says about CI are out of date.** CI does run `bench run-tests --app alvoraa_portal` and treats it as blocking (`.github/workflows/ci.yml:494-496`), and `test_portal_security_010.py:731` already holds a per-file `ignore_permissions` ceiling. So "permission tests do not run in CI" is wrong on paper. In practice CI runs only when Actions run, and on the private repo they fail in 2 seconds (memory, ALV-164). The new CI script should not duplicate the ceiling test (section 6).
7. **Main checkout is not usable for bringing work into `dev`.** `C:/Surbhi-Git/hr-app` has uncommitted changes in `hr_api.py`, `inbox_api.py`, `hooks.py`, `portal.js` and `home.html`. Those are the exact files this slice changes, and the changes are not mine. Under `parallel-work.md` §4 I must not `merge --ff-only` into it. I test only in my own container that mounts this worktree.

---

## 1 · Start of work (parallel-work §1)

**Incoming on `origin/dev` since this branch was made** (5 commits, read):

| Commit | What | Touches a file I will change? |
|---|---|---|
| 6329bef3 | 062: portal installs as a PWA | `hooks.py` (6 lines), `test_home_page_024.py`, new `field_app_pwa.py` |
| b7431697, 477ae4bf | ALV-222: Sign out on the phone bar | `frame.html` (end of `.mob-header`), `frame.css`, DOM test, `run_dom_tests.js` |
| 64d054e3, 639ee222 | ALV-232: one `override_whitelisted_methods` dict; issued-password redirect | `hooks.py`, `auth.py` |

`frame.html` holds the bell button (`frame.html:129-141`). ALV-222 added its link after the bell, in the same header block. I rebase before the first edit and keep both.

**Main checkout:** uncommitted edits in the hot files listed in bad news 7, plus `.claude/` and `CLAUDE.md`. Another session's work. Not touched.

**Work board:** no live row claims `inbox_api.py`, `home.html` or the bell. Slice 066 (grooming) and 063 rows are old and say "not pushed"; their code is already on `origin/dev`. I will ask Surbhi whether anyone else is in `portal.js` Home or the bell this week (question 6, section 12).

---

## 2 · Impact analysis

### 2.1 Callers of every function I will change (grep, not memory)

| Function | Callers found | What I do |
|---|---|---|
| `hr_api.get_portal_activity` (`hr_api.py:1120`) | `portal.js:5611` (`homeActivity()`), `5617`, `6223`, `8666`. Nothing else in Python, JS, tests or other apps | Delete the endpoint, `homeActivity`, `renderActivityFeed` and all four call sites (A) |
| `loadHome()` (`portal.js:5562`) | `portal.js:19960` only | Rewritten to start the new cards (A) |
| `homeDashboard()` banner block (`portal.js:5633-5660`), `homeActionLeave`, `toggleHomeApprovals` | Home only | Banner and its two functions removed; Pending replaces it (A). `homeActionLeave` is also called from `8632`'s own definition only — re-grep at build |
| `get_employee_dashboard` key `pending_approvals` (`hr_api.py:463-478`) | Home banner; tests `test_leave_privacy_045`, `test_no_repeat_queries_044`, `test_scale_flatness_044`, `test_portal_security_010`, `test_review_fixround_010d`, `fixtures_scale_044` | **Left alone.** Removing it would touch six test modules. After A nobody on Home reads it; listed as a follow-up (section 10) |
| `inbox_api.get_inbox` / `get_nav_counts` / `parts()` / `ROW_KEYS` | `next-inbox.js`, `next-frame.js`, `next-home.js` (discarded page, still served at `/hrms-employee-next`); tests `test_inbox_parts_042`, `test_inbox_counts_034`, `test_count_matches_list_045`, `test_browser_call_args_045`, `test_frame_endpoint_registry_034`, `test_no_repeat_queries_044`, `test_scale_flatness_044`, `measure_044` | Add one key `waiting_since` to every part (A). Add part `expense_approvals` (C). No signature change unless the measurement fails (then an optional `limit=None` argument, which no caller passes today) |
| `hr_api.action_leave(leave_id, action)` (`hr_api.py:1060`) | `portal.js:8439, 8608, 8636, 8832`; `next-inbox.js:59`; tests `test_leave_permissions`, `test_leave_063_rules`, `test_decide_now_068`, `test_portal_security_010`, `leave_063_fixtures` | Add optional `reason=None` at the end. Every existing caller passes two arguments and behaves as today (A) |
| `hr_api.get_leave_summary` (`hr_api.py:2306`) | `portal.js:6412, 6523, 6596, 6811`; `recent_leaves` render at `8566` | Add the decline reason to the caller's own **Rejected** rows only, read in one batched query (A; decision 3) |
| `hr_api.apply_expense_claim` (`hr_api.py:2429`) | `portal.js:7559`; `test_expense_and_scoping` | Sets `expense_approver`; refuses when none can be found (C; decision 4) |
| `hr_api.get_expense_claims` (`hr_api.py:2247`) | `portal.js:7447`; `test_expense_and_scoping` | Add the field `alvoraa_decline_reason` to the field list (C). Still the caller's own claims only |
| Bell: `gmPaintBadge`, `gmBellLoad`, `loadNotifPanel`, `loadNotifBadge`, `toggleNotifPanel` (`portal.js:9822-9850`, `14156-14234`) | `gmPaintBadge` at 9834, 9848, 14199, 14230; `gmBellLoad` at 14162, 14232; `toggleNotifPanel` from `frame.html:129`; `_pfIsManager` set at 14197 and read at 14083 only as a comment | Bell number and panel come from the one notices function (A). Goal and KPI approvals leave the bell (they are in Pending through the inbox's `goal_updates` part) |
| `grooming.my_notices` / `my_notices_seen` (`grooming.py:1014, 1036`) | `portal.js:9832, 9846`; the write-verb list at `portal.js:11282`; `test_grooming_066` | `my_notices` gate `_readable` is reused by the new feed. `my_notices_seen` loses its only caller; the endpoint stays (section 10) |
| `hrms.alvoraa_hr_core.access` | `permitted_employee_filters` has many callers | **Not changed.** One new function beside it (B) |
| `hooks.py` `doc_events["Expense Claim"]` (`hooks.py:~277`) | — | One line added: `before_submit: refuse_own_submit` (C) |
| `hooks.py` `scheduler_events["all"]` (`hooks.py:408`) | — | One line added at the end (B) |
| Module access (`module_access.py`) | — | **Not changed.** A blocked module does not affect `has_permission` or `get_list` in this Frappe (grep of `permissions.py`, `db_query.py`). The new DocType must be listed as tenant-side in `subscription.py`, or the billing test fails (commit 4fdf8046) |
| `ALLOWED_ORG_SETTINGS` / `set_org_setting` (`hr_api.py:3200, 3272`) | — | **Not used.** The switch is a Custom Field on HR Settings so Frappe's own history shows who changed it (spec G14) |

### 2.2 Cross-module reach

| App | Touched | How |
|---|---|---|
| `alvoraa_portal` | Yes, main | All three parts |
| `hrms` (our `alvoraa_hr_core` folder only) | B | One new function in `access.py`. Frappe HR's own code is not edited |
| `hrms` (Frappe HR) | Used | Expense Claim submit, share with approver, `calculate_total_amount` zeroes the sanctioned amount on Rejected so a decline posts nothing (`expense_claim.py:493`, read) |
| `erpnext` | Used (C) | GL Entry on approval, made by Frappe HR |
| `frappe` | Used | Notification Log (`type` is a Link to Notification Type; "Alert" is a built-in type and in `notification_skip_email_types`), `mark_as_read`, Version, Comment |
| `alvoraa_goals` | Read only | Goal and KPI rows arrive through the inbox `goal_updates` part. They leave the bell |
| `alvox_compensation` | No | Not on this bench |

HRMS domains: leave (decide sheet, reason), expenses (C), org structure (scope), goals (Pending rows only), attendance (Pending rows; Today strip moves). Payroll, appraisals: no change.

### 2.3 Personas

| Persona | Part A | Part B | Part C |
|---|---|---|---|
| Employee | New balanced Home; Pending shows own requests and policies; Notices shows grooming notices; bell counts unread notices only; sees a decline reason on own leave | Receives notices | Sees branch birthdays (only when HR turns it on); can hide self; sees "Declined: reason" on own claim; portal claim refused if no approver |
| Manager | Leave decisions from Pending with a sheet; goal/KPI approvals move from the bell to Pending | — | Decides expense claims where they are the named approver |
| HR Manager | Same as manager; Pending is in scope | Holds Notice Sender from install (Q8); sends within their companies and branches | Turns the birthdays switch on or off; sees the list of Notice Sender holders |
| CXO | Pending rows are counts per kind, no people (needs decision 1) | Sends to every company if System Manager; to their Company permissions only if not | Same as HR for the switch if System Manager |

### 2.4 Non-functional verdicts (all seven, per part)

| Dimension | A · Home | B · Send | C · Expenses and birthdays |
|---|---|---|---|
| Performance | **Degrades, size unknown until measured.** Adds the full inbox (12 queries at worst) and a notices read; removes Activity, the bell's goal count and the banner render. Query count must stay flat in headcount | **Neutral on Home** (no read counts on Home). A send writes one row per person plus Frappe's own "unseen" update and realtime push per row, in a background job | **Degrades slightly**: one birthdays query on Home when switched on, zero when off; one more inbox part |
| Security | **Improves**: removes an endpoint with three `ignore_permissions`. New feed reads only the caller's own rows through `get_list` | **Degrades by design, then held**: a new way to reach hundreds of people. Held by role check, server scope at create and send, list-form scope, sender re-check | **Degrades by design, then held**: money moves from a phone. Held by named-approver check, row lock, self-approval hook on every door, no `ignore_permissions` |
| Reliability | Neutral. Each card has its own failure box | Improves on plain inserts: status guard, chunked commits, resume, Not sent / Failed end states | Neutral. Row lock against double decisions; refusal instead of a claim nobody can see |
| Scalability | Neutral if counts stay flat (measured at small and 981 people) | Degrades at 5,000 people: tens of thousands of Notification Log rows a month; no purge yet (Q1) | Neutral: one query per Home, filtered in SQL |
| Maintainability | Improves: one source for the bell, Activity gone. Cost: the Home grid is rewritten in a 20,000-line hot file | Degrades: one new DocType, a job, one new module | Neutral: one endpoint, one part, three Custom Fields |
| Data integrity | Neutral. Decline reason stored as a Comment, not on the leave | Improves on any hand-rolled send: a notice goes once; the audience is fixed at send time | Improves: a claim always carries an approver; a decline zeroes the sanctioned amount (Frappe HR) |
| Compliance / privacy | Improves: Activity (passive monitoring of clicks) is gone | Degrades until Q1 is answered: no retention number for notices and read marks | Degrades by design: day, month and years of service become visible in the branch. Held by switch OFF, opt-out, fixed key list |

---

## 3 · Strategy, part by part

**Rule for all three parts: each part is built, tested, reviewed and pushed on its own, and each push waits for Surbhi's word.** A part never ships code that only a later part uses. No feature flag is used to hide unfinished work: the later part's code simply does not exist yet.

### Part A · Home (about 28 points, Tier 2)

**Rungs.**

| Piece | Rung | Why the cheaper rung was rejected |
|---|---|---|
| Pending card | 1 + 4: the existing `get_inbox`; one new row key; front-end card | Nothing cheaper shows mixed kinds oldest first |
| `waiting_since` key | 4: one key per part in `ROW_KEYS` | Without it, oldest-first across kinds is impossible (design 4.1) |
| Leave decide sheet | 4: front end over `action_leave`; optional `reason` | The reason has no field on Leave Application; a Frappe Comment (rung 1) holds it |
| Reason shown to the employee | 4: one batched Comment read in `get_leave_summary` for own Rejected rows | Decision 3 |
| Notices card + bell, grooming only | 1 + 4: one read function over Notification Log reusing `grooming._readable`; marking read uses Frappe's own `mark_as_read` | No wrapper: Frappe's function already limits to the caller's row. This removes the spec's `notice_mark_read` endpoint |
| Remove Activity | deletion | — |
| Balanced grid, Today strip | CSS + markup | — |
| CI trap script | 4: one small script | See section 6 |

**Files.**

| File | Change |
|---|---|
| `templates/includes/ess/parts/home.html` | Activity card and old banner removed; `#day-widget` moved inside the check-in card; new Pending and Notices cards; one grid of rows |
| `public/css/ess/panels.css` | `.home-body-grid` (line 662) becomes a two-column row grid; the fixed 300 px column and `.home-left-col` / `.home-actions-col` rules (662-665, 1742) go. New rules in one block with a new prefix |
| `public/js/ess/portal.js` | `loadHome` starts the cards together; new Pending block (prefix checked unused at build); leave sheet; Notices card and See all sheet; bell rewired; Activity code deleted. A new block, one line in each existing function that must change, nothing moved or re-indented |
| `templates/includes/ess/frame.html` | Bell: accessible name "Notices, N unread"; old panel body removed only if nothing else reads its ids (grep at build) |
| `inbox_api.py` | `waiting_since` in `ROW_KEYS` and in each part's rows; the date source per part (`creation`; `logged_on` for goal updates; policies: the engineer names the field, else rows sort last) |
| `hr_api.py` | `get_portal_activity` deleted; `action_leave(..., reason=None)`; `get_leave_summary` reason for own Rejected rows |
| new `alvoraa_portal/notices.py` | `notices_feed(see_all=0)`: caller's own rows, fixed field list, unread count and rows in one place. In A it reads grooming rows only. B adds `"Announcement"` to its document-type list (one line) |
| new `scripts/check_scope_traps.py` + one step in `ci.yml` lint job | Section 6 |
| tests | new `tests/test_home_076.py`; new `tests/portal_home_076_test.js` registered in `scripts/run_dom_tests.js`; new `scripts/browser_check_home_076.js` (not in CI) |
| `test_portal_security_010.py` `CEILINGS` | `hr_api.py` ceiling 70 → 67; `notices.py` row at 0 |

**Build order inside A.**
1. Measure the old Home (section 7) on old code. Record it.
2. `waiting_since` key and its test (inbox tests changed on purpose, not relaxed).
3. Measure `get_inbox` on Home's personas. If it misses 500 ms p95 or grows with headcount, add the optional `limit` argument (OPS-2a) before any card is drawn.
4. `notices_feed` + bell rewire + Notices card and sheet.
5. Pending card, kind → screen map, leave sheet, `action_leave` reason, reason on the employee's leave row.
6. Remove Activity (endpoint, JS, card) and lower the ceiling.
7. Grid, Today strip, the screen test at 1280 and 360 px.
8. `check_scope_traps.py` with `--self-test`.
9. Measure the new Home. Subtract pass. Notes.

**How Part A stays shippable alone.**
- No "Send a notice" button exists in A. Its code is written in B, behind the server's answer "this person holds Notice Sender". There is nothing to hide.
- No expense rows can reach Pending in A, because the `expense_approvals` part does not exist until C. The sheet in A handles leave only; C adds the expense branch.
- No Birthdays card in A. The grid is drawn and measured with it absent, which is the design's own "switch off" layout, already balanced.
- Notices in A shows grooming alerts only. Its empty text "Messages from HR and management, and alerts about your work, appear here." is kept exactly as drawn (parity). It becomes fully true in B.
- No Organisation settings change in A.

**Tests for A** (own container, own site, one module at a time):
- New: `test_home_076` (keys exactly old set + `waiting_since`; `get_nav_counts` total still equals the sum; `action_leave` reason 1 to 140, stored as a Comment, refused for non-approver and claimant as today, callers with two arguments unchanged; employee B never sees A's reason; `notices_feed` own rows only, fixed keys, Guest refused, count equals bell; `mark_as_read` on someone else's row leaves it unread; old Activity method returns "not found"; one Home-shape query count at two sizes).
- DOM: `portal_home_076_test.js` (empty states, escaping `<img onerror>`, sheet focus and Escape, Pending row order, CXO count rows, failure box and retry).
- Screen: `browser_check_home_076.js` (section 8).
- Re-run, one at a time: `test_inbox_parts_042`, `test_inbox_counts_034`, `test_count_matches_list_045`, `test_browser_call_args_045`, `test_frame_endpoint_registry_034`, `test_leave_permissions`, `test_leave_063_rules`, `test_decide_now_068`, `test_leave_privacy_045`, `test_grooming_066`, `test_portal_security_010`, `test_home_page_024`, `test_home_holidays_035`, `test_no_repeat_queries_044`, `test_scale_flatness_044`; the whole DOM suite (`node scripts/run_dom_tests.js`, fast); `check_portal_handlers.js`, `check_undefined_js.js`, `check_day_widget.js`, `check_tag_balance.py`, `check_api_paths.py`, `check_app_integrity.py`.

### Part B · Send (about 33 points, Tier 1)

**Rungs.**

| Piece | Rung | Why the cheaper rung was rejected |
|---|---|---|
| `Announcement` DocType | 5, the only new DocType | A Custom Field on Notification Log has no audience, send time or status; a Notification rule cannot say "these 12 people on Monday" (spec G7) |
| Recipient rows | 1: Notification Log, `type = "Alert"`, `document_type = "Announcement"` | No child table, no counter field |
| Notice Sender role | 2: one Role, seeded once by a patch | — |
| Scope | 4: one new function beside the existing helpers | Changing `permitted_employee_filters` would widen every other screen |
| Scheduled send | 4: one line in `scheduler_events["all"]` that only enqueues on `long` | Existing scheduler and queue; no new worker |
| Double-send guard | Frappe row lock (`for_update=True`) as the first read, then a status check | OPS-8's raw `UPDATE … WHERE status` works too, but the ORM row lock does the same job without raw SQL (SEC-7) |
| Replay safety | Skip anyone who already has a row for this notice, one query per chunk on the indexed `document_name` | A unique key on a Frappe table is not upgrade-safe |
| Email copy | 1: `frappe.sendmail` per chunk, only when ticked and email is active | — |

**Files.**

| File | Change |
|---|---|
| new DocType `alvoraa_portal/alvoraa_portal/doctype/announcement/` | Fields exactly as spec 5.1; Track Changes on; DocPerm: Notice Sender create/read/write if owner; System Manager full; nobody else. Controller: trim and length, write only while Scheduled |
| `subscription.py` | `Announcement` named as tenant-side (one line) |
| new `alvoraa_portal/announcements.py` | `create_notice`, `cancel_notice`, `my_sent_notices`, `notice_reach`, `search_notice_people`, `notice_sender_holders`, `send_due_announcements`, the worker, `email_is_active` |
| `hrms/hrms/alvoraa_hr_core/access.py` | New `notice_audience_conditions(user)` (below). Nothing else in the file changes |
| `notices.py` | `"Announcement"` added to the document types it reads; announcements first, marked "Pinned" |
| `hooks.py` | One line at the end of `scheduler_events["all"]` |
| `patches.txt` + one patch | Create the role; grant it once to users who hold HR Manager at that moment; never again |
| `portal.js`, new `parts/notice-compose.html` (or a panel in an existing parts file) | Compose screen, Notices I sent, Cancel, "Send a notice" link for holders only |
| `parts/org-settings.html` + `portal.js` org block | Read-only holders list |
| `test_portal_security_010.py` `CEILINGS` | `announcements.py`: 1 (writing other people's Notification Log rows) |

**Endpoint names follow the portal's write-verb rule.** `gpFetch` treats a call as a write only if its last name part starts with a verb from the list at `portal.js:11279` (`create`, `cancel`, `set`, `decide`, `mark`…). A write that does not match times out at 15 s and can be tapped again. So: `create_notice`, `cancel_notice`; reads are `notice_reach`, `search_notice_people`, `my_sent_notices`, `notices_feed`. The spec's `notice_search_people` is renamed for readability only; `notice_mark_read` is dropped (Frappe's `mark_as_read` matches "mark").

**The scope function returns a list, not a dict.** `notice_audience_conditions(user)` returns Frappe filter conditions as a **list** of `[field, op, value]`, the same shape `employee_in_scope` builds (`access.py:289-299`). A caller then appends `["name", "in", ids]`, `["status", "=", "Active"]` and the user conditions. With a list, a later `name` condition can never replace the "nobody" condition. This removes the `dict(…, name=X)` trap by shape, not only by review. Rules:
- Administrator or System Manager: everyone (documented; AC-13).
- HR Manager / HR User: `permitted_employee_filters(user)`, unchanged, turned into a list.
- Anyone else (a director holding Notice Sender): companies from their Company User Permissions only, narrowed by Branch User Permissions; **no fallback to their own company**; none means nobody.
- Never empty. "Nobody" is `[["name", "in", []]]`.

**The send, step by step.** Create checks role, Active Employee if one exists, text, limits, scope, then writes one Announcement with the User row locked for the daily count. "Now" to 200 or fewer writes rows in the request. Over 200, or "Later": Scheduled. Each tick takes at most two due notices and enqueues one job each on `long` with a job id per notice. The worker: lock the notice (first read), stop unless Scheduled or Sending-and-stale (over 10 minutes); re-check the sender (role, enabled User, Active Employee, non-empty scope) **as the sender** (`user=sender` everywhere); resolve the audience at that moment; write rows in chunks of 200, skipping people who already have a row and the sender themself (as Frappe's own `make_notification_logs` does); commit after each chunk; email per chunk only if ticked and still active; set Sent. Three stale resumes with no new rows: Failed, one Error Log row with the id and counts only.

**Tests for B:** new `test_announcements_076` (AC-1 to AC-56 that are B tests, including the trap test AC-8 and the as-Administrator test AC-23, each guard broken on purpose once to prove its test can fail), DOM test for Compose (AC-44 to AC-51), the 1,200-recipient send and kill-and-resume (measured, section 7). Re-run: `test_home_076`, `test_grooming_066`, `test_portal_security_010`, `test_frame_endpoint_registry_034`, the billing/tenant-side test (`subscription` tests), `test_employee_field_rights_alv215` (role seeding touches users), DOM suite.

### Part C · Expenses and birthdays (about 25 points, Tier 1)

**Rungs.**

| Piece | Rung | Why |
|---|---|---|
| Approver set at filing | 4: three lines in `apply_expense_claim`, same lookup Frappe HR uses (`hrms/api/__init__.py:612-622`) | The new part shows nothing without it (01c bad news 3) |
| Refusal with no approver | 4 | Decision 4 |
| `expense_approvals` part | 4: one part in `inbox_api` | Same contract as the other six |
| `decide_expense` | 4: lock, check, set `approval_status`, `doc.submit()` | No Desk path works on a phone |
| Self-approval | 3: one `doc_events` line reusing `refuse_own_submit` | Frappe HR's own check is off unless an HR Setting is on |
| Decline reason | 3: Custom Field `alvoraa_decline_reason` on Expense Claim | `remark` is the claim's title on the portal (`portal.js:7455`) |
| Birthdays | 4: one endpoint, one query on existing Employee fields | No new DocType |
| Org switch | 3: Custom Field on HR Settings (Version history gives "last changed by") | The Default-value store has no history |
| Opt-out | 3: Custom Field on Employee, set only through the person's own endpoint | — |
| Backfill of open Draft claims | 4: one patch using `doc.save` so the share is made | AC-79 |

**Files.** `hr_api.py` (`apply_expense_claim`, `get_expense_claims`), `inbox_api.py` (`PARTS`, `APPROVAL_PARTS`, `ROW_KEYS`, `parts()`, new `_part_expense_approvals`), `announcements.py` or a new small `home_people.py` for `birthdays_this_month`, `set_birthday_hide`, `set_birthdays_switch` (I recommend the new small file: birthdays have nothing to do with notices), `hooks.py` (one `doc_events` line; one `after_migrate` line for the three Custom Fields), `employee_field_rights.py` (classify the new Employee field), `patches.txt` + backfill patch, `portal.js` (expense branch of the sheet, claim row "Declined: reason", Birthdays card, opt-out tick, switch), `parts/org-settings.html`, `CEILINGS` rows.

**`decide_expense` rules.** First read `frappe.get_doc("Expense Claim", name, for_update=True)`. Refuse unless the caller is `expense_approver`, has an Active Employee, is not the claimant, and the claim is `docstatus 0` and `approval_status "Draft"`. Approve: set Approved, `doc.submit()`. Decline: reason 1 to 140, set Rejected, store the reason, `doc.submit()` (Frappe HR zeroes the sanctioned amount on Rejected, so no ledger entry). No `ignore_permissions`, no `db_set` on status, no raw SQL. The approver's submit right comes from the share Frappe HR adds on save. `[UNVERIFIED]` that a share alone lets a non-HR approver submit in this Frappe version and that GL entry creation needs no extra right; AC-86 proves it. **If it does not hold, I stop and ask** — the fix would be an `ignore_permissions`, which SEC-14 forbids.

**Birthdays query.** One Frappe query-builder query: viewer's own Active Employee gives company and branch; no branch means an empty list without a query; filters status Active, same company, same branch, not opted out, and `MONTH(date_of_birth)` or `MONTH(date_of_joining)` equal to this month, in SQL. Dates are read on the server only to work out day, month and years; the reply keys are exactly name, kind, day, month (+ years). Switch off returns `[]` before any Employee query. One counted `ignore_permissions` (the fields are level 2).

**Tests for C:** new `test_expense_birthdays_076` (AC-77 to AC-107, AC-119 to AC-121; a portal-filed claim **with** an approver in the data, or "0 rows" proves nothing). Re-run: `test_expense_and_scoping`, `test_inbox_parts_042`, `test_inbox_counts_034`, `test_count_matches_list_045`, `test_home_076`, `test_employee_field_rights_alv215`, `test_portal_security_010`, DOM suite, and Frappe HR's own `Expense Claim` doctype tests in my container (CI runs them, `ci.yml:524-528`; the new `before_submit` hook must not break them).

---

## 4 · The trap list (from 01c, 03 and this reading)

| # | Trap | What I do | Proved by |
|---|---|---|---|
| T1 | The job runs as Administrator; the scope helper gives Administrator everybody | Every scope call in the job passes `user=sender`. No module-level state | AC-23: run the job function directly as Administrator; only branch-A rows |
| T2 | `dict(permitted_employee_filters(), name=X)` lets a user with no companies in | Never written. The new scope function returns a list. Chosen ids are checked with list conditions, as `employee_in_scope` does | AC-8; `check_scope_traps.py` |
| T3 | A plain Notification Log row emails by itself | Rows are `type = "Alert"` (in `notification_skip_email_types`, verified in Frappe v16.33.1). Email only through the explicit copy | AC-55: email-on recipient, no tick → zero Email Queue rows |
| T4 | Portal claims carry no approver, so the expense part is always empty | Filing sets it; no approver → refused (decision 4) | AC-77, AC-83 with a real portal-filed claim |
| T5 | Self-approval is off in HR Settings | `refuse_own_submit` on Expense Claim `before_submit`, plus the check in `decide_expense` | AC-91 on portal, `doc.submit()` and REST |
| T6 | The decline reason written to `remark` would replace the claim's title | Its own field `alvoraa_decline_reason` | AC-94 |
| T7 | Leave has no reason field | Comment on the Leave Application; shown on the employee's own row only | AC-75 and the "B never sees A's" test |
| T8 | The bell number changes meaning | Bell = unread notices from the one function the card uses; goal/KPI approvals move to Pending | AC-58: chip equals bell for three users, including mid-send |
| T9 | A stale read before the lock gives a stale snapshot (slice 021) | The locked read is the **first** read in the transaction, for send, cancel and decide | AC-38, AC-88 |
| T10 | Desk renders a Notification Log title/subject as HTML | Escape the text before writing `title`, `subject`, `description` and `email_content` (Frappe mirrors title↔subject on insert) | AC-20 and the DOM test AC-63 |
| T11 | A write call whose name does not start with a write verb times out at 15 s and can be tapped twice | Names in section 3 B | Review check |
| T12 | A leaver with a working login | Every "who am I" uses `status = "Active"` | AC-10, AC-26, AC-85, AC-98 |
| T13 | New DocType not named tenant-side fails the billing test | One line in `subscription.py` | That test |
| T14 | New Employee field unclassified in field rights | Add it to the right list in `employee_field_rights.py` `[UNVERIFIED]` whether an unclassified field fails a test | `test_employee_field_rights_alv215` |

---

## 5 · The DevOps view (07) — where I disagree

- **OPS-2a:** not available on the live page (bad news 1). I keep the rest: measure first, then `limit`, cache only after a recorded miss.
- **OPS-8 raw `UPDATE`:** I use the ORM row lock instead (section 3 B). Same effect, no raw SQL. If the measurement shows lock waits, I will say so.
- **OPS-8 unique key on `(announcement, recipient)`:** not added to a Frappe table; skip-existing per chunk instead (the spec agrees).
- **OPS-11 "recipient child table":** none; Notification Log rows are the recipients.
- **5,000-person measurement:** the existing scale site `test044` has 981 people. I propose: Home flatness measured at `test044s` (small) and `test044` (981); a one-off seed of 5,000 only for the birthdays worst case (C), 1,300 only for the 1,200-recipient send (B), and 100,000 Notification Log rows only for `EXPLAIN` (B). All on my own site, never committed to `demo/`.

---

## 6 · The CI gate script `scripts/check_scope_traps.py`

- Fails when a Python file contains `dict(permitted_employee_filters(` with `name=` in the same call, or `{**permitted_employee_filters(`. Read with `ast`, so a comment or docstring that mentions the pattern (as `access.py:293` does) is not a hit.
- `--self-test` builds a bad sample in memory and proves the check fails on it, like the other scripts in `ci.yml`.
- Runs in the `lint` job, so it needs no bench.
- **The `ignore_permissions` count (AC-118):** `test_portal_security_010.CEILINGS` already does this per file, with new files starting at zero, and CI runs it. I recommend meeting AC-118 through that test (lower `hr_api.py` by 3, add the new files' rows) rather than a second global counter in the script. If Surbhi wants the global number too, it is ten more lines (decision 5).

---

## 7 · Measuring Home before and after

- **Where:** my own container and site (section 9), never the shared bench.
- **How:** `alvoraa_portal/tests/measure_044.py` already counts every SQL statement through `frappe.db.sql`, warms up three times and reports payload bytes. A small `measure_076.py` reuses its `_Spy` and runs Home's call set per persona (employee, manager, HR Manager, System Manager).
- **Before:** on `origin/dev` code: `get_checkin_status`, `get_portal_activity`, `get_employee_dashboard`, `get_my_documents`, `get_my_policies`, the goals card call, `goals_api.get_pending_approvals_count`, `grooming.my_notices`.
- **After (A):** the same minus Activity, the bell's goal count and `my_notices`, plus `get_inbox` and `notices_feed`. After C, plus `birthdays_this_month`.
- **What counts:** query count per call at `test044s` and `test044` must be **equal** (flat in headcount), and payload bytes. Wall time is recorded as p95 over 20 runs, but `change-process.md` warns it varies more than the effect on this machine, so a time result is reported with that caveat and is not a pass on its own.

---

## 8 · The balance test at 1280 and 360 px

`scripts/browser_check_home_076.js`, the same `puppeteer-core` pattern as `browser_check_frame.js` (Chromium inside my own container, not CI). It logs in as each of the five personas, seeds three data sizes (none, few, 200 rows), renders the **real** Home at 1280 and 360 px with birthdays on and off (C only; in A the "off" half is the whole set), and measures in the page: largest gap ≤ 24 px, columns end within 120 px, no card over 2× the median card, at most 5 rows per list, no horizontal scroll, phone order check-in → Pending → Notices, and pairs within 1.5× or stretched with the pair named. Target 60 cells (C) or 30 cells (A), 0 failures. The readout is saved in the implementation notes.

---

## 9 · Parallel-work check

| File | Hot? | Who else is in it | Plan |
|---|---|---|---|
| `portal.js` | Yes | Main checkout has uncommitted edits (not mine); slices 064, 065, 071, 072 own the Positions block | New Home/Notices blocks with their own prefix; one-line edits in `loadHome`, the bell functions and the leave/claims renders; nothing moved or re-indented |
| `home.html` | Medium | Main checkout edits (4 lines, not mine) | Rebase, then rewrite only the grid block |
| `frame.html` | Medium | ALV-222 added a link after the bell (incoming) | Edit only the bell's attributes and its panel |
| `panels.css` | Yes | Positions slices own other blocks | Home block only |
| `inbox_api.py`, `hr_api.py`, `hooks.py`, `patches.txt` | Yes | Main checkout edits (not mine); 063 and 066 already landed | Add, never rewrite; hooks and patches lines at the end |
| `access.py` (hrms) | Medium | none seen | New function at the end |
| `test_portal_security_010.py` | Shared | many slices add rows | Rows at the end |

**Container and site.** Own containers `hrlocal-076` and `hrlocal-076-redis` from the current local image, with this worktree's `alvoraa_portal/` and `hrms/` bind-mounted, and a new volume `hrlocal-076-sites`; own site `test076` on `hrlocal-mariadb` (new site with `--install-app` erpnext, hrms, alvoraa_goals, alvoraa_portal, as slices 042, 043 and 067 did), plus `test044s`/`test044` copies for measuring if they still exist. `hrlocal-bench` and `test_site` are not used. One test run at a time; the board row is claimed before every run and cleared after. Containers stopped when I report.

**Pin tests** (so a bad merge cannot drop the feature): `test_home_076.test_activity_endpoint_is_gone`, `…test_bell_and_card_share_one_count`, `test_announcements_076.test_job_resolves_scope_as_the_sender`, `…test_no_id_outside_scope_is_accepted`, `test_expense_birthdays_076.test_only_the_named_approver_decides`, `…test_birthday_reply_has_no_year`.

The work-board row is added after approval, not before.

---

## 10 · Risks, trade-offs, what I would cut

| Risk | Label | What happens |
|---|---|---|
| Pending makes Home slower than budget | to be measured | `limit` argument first; a 30-60 s per-user cache only after a recorded miss, with its invalidation (clear on every decide) in the same change |
| A non-HR approver cannot submit through a share | unknown until AC-86 | Stop and ask; no `ignore_permissions` added on my own |
| DTC staff have no expense approver | release blocker for C | Read the count first; HR fills approvers before C goes to DTC |
| Notification Log grows with no purge (Q1) | temporary debt; a counsel number removes it | B not switched on at a live tenant until then (her working default) |
| Writing 1,200 rows: each Frappe insert also updates the user's "unseen" flag and queues a realtime push | to be measured | If one notice cannot finish inside a tick, the stale-resume rule still prevents duplicates; I report the number |
| The Home grid rewrite in a hot file conflicts with another session | trade-off | Rebase often; one commit for the grid alone |
| `get_employee_dashboard` still runs its `pending_approvals` query on every Home load though nothing shows it | acceptable simplification for this slice | Listed for Surbhi; removing it touches six test modules |
| `grooming.my_notices_seen` has no caller after A | acceptable simplification | Left in place; listed for Surbhi |
| The discarded `/hrms-employee-next` page gains a seventh inbox part in C | acceptable | Its Inbox shows an unknown part with its count; it is not a live page |

**What I would cut if the slice must shrink** (each needs her yes, because she approved the spec):
1. The open-claims backfill patch (AC-79) if a read shows no open portal claims without an approver at DTC.
2. The holders list in Organisation settings (design 6 offers to delete it).
3. The email copy (US-9) while email is muted at DTC — it cannot be seen working there until go-live.

**Spec text I will correct, because her later decisions override it** (no question needed): AC-78 (decision 4: refuse, not accept); open decisions 1, 2, 3, 10 are now "yes" (Sending wording; bell = notices only; reason as a Comment shown on the employee's row; "It may have gone through. Check Notices I sent.").

---

## 11 · Size, models and reviews (usage-discipline)

| Part | Stories | Points | Engineer model | Agent hours (estimate) | Review |
|---|---|---|---|---|---|
| A · Home | US-10 (grooming only), 11, 12, 20, 21, 22, 23, part of 27 | ~28 | `sonnet` (Tier 2) | build 8-10, tests incl. screen test 4-6 | One independent review (`hrms-technofunctional-reviewer`, strong) that also checks SEC-9, 18, 19, 20 and breaks the CI script on purpose |
| B · Send | US-1 to 9, US-10 (announcements), US-24, part of 27 | ~33 | `opus` (Tier 1: scope, send job) | build 12-16, tests and measurements 6 | Independent review (strong) **and** a separate security verification (`hrms-security-privacy-engineer`, strong, not the author of 01c alone) of SEC-1 to 11, 17, 21, PRIV-1 to 4 |
| C · Money and people | US-13 to 19, 25, 26, part of 27 | ~25 | `opus` (Tier 1: expense approval, birthdays) | build 10-12, tests 5 | Independent review (strong) and separate security verification of SEC-12 to 16, PRIV-5 to 8 |

Hours are my estimate for agent time, not measured; I have no past record to calibrate them against. The full suite runs once per part, at the end, before asking for the dev push.

---

## 12 · Decisions I still need from Surbhi (real blockers only)

1. **Who counts as a CXO on Pending?** The design shows counts only, no names, for a CXO. The code has no CXO role; everywhere else "System Manager" is treated as CXO (`access.py:196`, `attendance_analytics.py:573`). **Recommend: System Manager = CXO here too.** Blocks AC-69 in Part A.
2. **Where does the birthday opt-out tick live?** The live portal has no "My profile" screen. Options: (a) a small new "My profile" screen with only this tick, opened from the account menu (matches the drawing's words, one new screen); (b) a "Hide me" line inside the Birthdays card (no new screen, differs from the drawing). **Recommend (a).** Blocks US-19 in Part C only.
3. **DTC expense approvers.** Before Part C goes to DTC, someone with access reads how many active DTC employees have neither an expense approver nor a department expense approver. If it is many, HR fills them first, or every claim is refused. Not a build blocker; a release blocker for C. Owner: Surbhi or DevOps.
4. **How email is muted at DTC** (her decision 11). My helper treats email as active only if `mute_emails` is not set in site config **and** an enabled outgoing Email Account exists. If DTC mutes it another way, the helper needs one more check. Release blocker for B's email tick only.
5. **AC-118 through the existing ceiling test** instead of a second global counter (section 6). Recommend yes. Small.
6. **Is anyone else changing the Home page, the bell, or `inbox_api.py` this week?** (parallel-work §1 step 3; other developers cannot see the work board.)

Not blockers, already decided by her working defaults: Q1 (no purge; B not live until a number), Q2 (birthdays switch ships OFF), Q4, Q5, Q6. **The five residual risks in 01c section 12 are still not accepted by name and date; each needs her yes before B or C goes to `dev`.**

---

## Subtract pass (on this document's proposal)

Removed: the spec's `notice_mark_read` endpoint (Frappe's `mark_as_read` does it); a second global `ignore_permissions` counter (the ceiling test does it); OPS-8's raw `UPDATE` (ORM row lock); OPS-2a's "reuse the frame's counts" (not possible on the live page); a dict-shaped scope helper (list shape removes the trap); removing `get_employee_dashboard.pending_approvals` and `my_notices_seen` (not asked for; listed instead). Kept on purpose: the backfill patch (approved AC-79, cheap, safe to run twice).

**Stop. Waiting for Surbhi's approval before any file other than this one is written.**
