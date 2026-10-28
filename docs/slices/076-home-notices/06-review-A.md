---
slice: 076-home-notices
artifact: 06-review-A (senior architect review, change-process step 5, Part A only)
author: hrms-technofunctional-reviewer
date: 2026-10-28
branch: slice/076-home-notices, 5 local commits on origin/dev b2547d1f (re-fetched today: dev has not moved). Nothing pushed.
---

# 076 Part A review

## Verdict: SHIP WITH FIXES

**Part A is safe. Nothing leaks, and nothing in it can lose data. But it is not ready for `dev` as it stands.** Two Pending rows send a manager to the wrong screen. One CXO sentence describes a number that is not what it says. And two approved acceptance criteria (AC-72, AC-112) are not met. By the rules, an unmet AC blocks the release unless Surbhi accepts it in writing. I recommend fixing AC-72 and accepting AC-112 in writing.

`SHIP WITH FIXES` means "ready to show Surbhi once the fixes below are done". It is not permission to push.

**What I could and could not run.** I ran the DOM suite (17 files, 0 failed; the 076 file passed 65 of 65), the static checks, and the scope-trap script, including a deliberately broken copy of it. **I did not run any Python test.** The builder's containers are stopped, and the shared bench does not mount this worktree. All Python results below come from the builder's notes, and I say so wherever I use one.

---

## Findings, worst first

No P0. No live exposure found.

### Major 1 (P2): a "Shift change" row in Pending leads to a dead end
- **Proven.** `portal.js:5584` sends `shift_request` to `"shift-req"`. That screen is the employee's own "request a shift" form and their own history (`loadShiftReqPanel`, `portal.js:8334-8352`). The live portal has no screen where a manager approves a Shift Request: grep finds only `submit_shift_request`, and no approve or decide endpoint exists.
- **What happens.** A manager has a report's shift request waiting. Pending shows "Shift change · waiting 3 days · Open". They tap it, and land on a form to request a shift for themselves. **To a first-week user, that looks broken.**
- **Why it happened.** The prototype assumed a screen called "Time, Shift change" (`prototype-v1.html:581`). That screen exists only on the discarded `-next` page.
- **Smallest fix needs a decision.** Options: (a) for approvers, open the Desk form `/app/shift-request/<name>` and say "opens in the office view" (this does not work on the phone app); (b) leave the shift-request approval part out of Home's Pending until a decide screen exists; (c) build a decide screen (this is new scope). **I recommend (a) for now.** Owner: Surbhi, then `hrms-fullstack-engineer`.

### Major 2 (P2): a "Goal / KPI update" row opens My Goals, where nothing can be approved
- **Proven.** `goal_update` goes to `"goals"` (`portal.js:5584`). That panel opens on its Overview tab (`_gpBoot`, `portal.js:11645`). `growth.html` has no approval list. The Approve and Reject buttons for progress updates are on the **Team** panel, under "Pending Progress Approvals" (`team.html:60-63`, `renderProgressApprovals`).
- **This makes things worse than before.** The old bell opened the exact update in a drawer (`pfOpenLog` / `gpOpenGoalDetail`). That path is now removed, and Pending is its only replacement.
- **Smallest fix.** Send `goal_update` to `"team"`. Then check on a fixture that the Team list shows the same updates the inbox counts. **Not checked:** the two lists use different endpoints (`hr_api.get_pending_approvals` and the inbox's `goals_api` scope), so they may not match.

### Major 3 (P2): AC-72 is not met. Home's cost for HR grows with the attendance-fix queue
- **Builder's measurement; I did not re-run it.** For an HR user, `get_inbox` takes 33 queries on the 20-person fixture and 111 on the 980-person one, with p95 at 437 ms. The cause is one DocShare query per queued fix, run twice (`attendance_correction._with_decide_flag` → `decided_as`, `attendance_correction.py:1423-1447`). That is a query inside a loop, which `nfr-budget.md` line 64 forbids.
- **The builder's notes get one thing wrong.** They say this cost "already runs on every page through `get_nav_counts`". **It does not on the live portal.** Grep shows `get_nav_counts` is called only by `next-frame.js`, `next-home.js` and `hrms-employee-next.html`. So for HR on live Home, this cost is entirely new. It also runs again every time Home is reopened after 60 seconds (`hmRefreshIfStale`).
- **What it means at DTC (Inferred).** If the cost grows in a straight line, a queue of about 100 fixes means about 200 extra statements and roughly 1 s for this one call, which is over the 500 ms budget. The card has its own loading state, so Home does not freeze. **DTC's queue depth is not checked.**
- **Fix.** Builder's option (b): read the DocShare rows once for the whole queue. It is small, but it is in `attendance_correction.py`, outside the slice, so Surbhi must approve it. If she prefers to accept the miss instead, she should do so in writing, after someone reads DTC's open-correction count (read-only).

### Major 4 (P2): the CXO Pending rows say "across your companies", but the number is only the CXO's own queue
- **Proven.** `portal.js` `hmPendingRows` writes "{n} waiting · across your companies" from `p.count`. That is the System Manager's own inbox count, which the builder confirms (difference 2).
- **What happens.** A CXO sees "Leave approvals, 3 waiting · across your companies" when 300 are waiting across the group. **That is a wrong number with a confident label.**
- **Fix.** Change the words to "{n} waiting on you". This is a one-string change, but it differs from the prototype, so it needs Surbhi's yes.

### Major 5 (P2, written acceptance needed): AC-112 "no card over 2x the median" fails in 20 of 45 cells
- **Builder's measurement, cause confirmed by reading the code.** The grid stretches cards in a row to the same height (`panels.css:668`, `align-items:stretch`). Team goals has no cap (`renderTeamGoals`, about `portal.js:9506`: every report, 3 goals each). So My Goals, sitting beside it, stretches into a mostly empty card. With 40 reports, that is about 11,000 px.
- **This is new.** The old side-column layout started each card at the top and did not stretch it.
- **Who is affected (Inferred).** DTC has one manager with 64 direct reports, but this only bites if that tenant uses Goals. **Not checked.**
- **Why it needs a decision.** Design row 35 says existing cards keep their content, and AC-112 says the page must be balanced. Those two conflict.
- **Options.** Cap Team goals at 5 people with "See all" (about 10 lines), or accept the miss in writing. **I recommend the cap.**

### Minor (P3)
1. **The scope-trap check misses indirect forms (proven in a scratch copy).** I fed it four bad files. It caught the two required forms (`dict(...permitted_employee_filters(), name=x)` and `{**access.permitted_employee_filters(...), "name": x}`), which meets AC-117. It missed these:
   - `f = permitted_employee_filters(); f["name"] = x`
   - `.update(name=x)`
   - `dict(permitted_employee_filters())` followed by an item assignment

   It also silently skipped a file with a syntax error (`except SyntaxError: continue`). The repo has none of these today (grep). Part B's list-shaped helper is the real defence, and its review should check that.
2. **Unread grooming notices now pile up, and the count stops being exact at 100.** Opening the bell no longer marks them all read (this is by design, per decision 2), and there is no "mark all read". `notices.py` reads at most 100 rows (`READ_CAP`), so above 100 the "N unread" figure is wrong and older unread notices never show. Grooming is switched on at DTC (27 Oct release), so HR there will see this first. Owner: Surbhi, to decide whether she wants "mark all read".
3. **A parity difference the builder did not list.** Goal and KPI rows have no "waiting N days" (`hmRowView`). The prototype draws "Goal update · waiting N days".
4. **AC-58 is tested with one user, not three.** That is weaker than the AC asks, though the single-function design makes a difference between users unlikely.
5. **No desktop bell** (builder's bad news 4). This is a parity difference that needs Surbhi's yes. It is not a regression: the live portal never had one.
6. **The 60-second re-fetch on returning to Home was not in the spec** (`hmRefreshIfStale`). It is sensible, but it doubles Major 3's cost for HR. Keep it only with Surbhi's yes.
7. **CI gates (Not checked).** `check_scope_traps.py` and the `ignore_permissions` ceiling are in `ci.yml`. But Actions currently fail within seconds on the private repo (ALV-164), so neither gate is running in practice.

<details><summary>Nits (P4)</summary>

- `waiting_since` sends a full timestamp, but SEC-19 says "a date". Harmless.
- The grid is 984 px at 1280, not 992, because of the shell's padding. Accept.
- `grooming.my_notices_seen` and `get_employee_dashboard.pending_approvals` are now dead, but the second still runs a query on every Home load. Already listed by the builder.
- `ntBellBoot` can repeat the notices call if Home's call takes more than 1.5 s.
- `measure_076.py` lives in the app's `tests` package but is not a test (the slice 044 precedent allows this).
</details>

---

## Checks the coordinator asked for

| Check | Result |
|---|---|
| SEC-9 (Part A: decline reason, notices text) | **Discharged.** The reason is escaped before it is stored (`hr_api.py` `action_leave`) and passed through `esc()` on display (`lvReason`). Notices and Pending rows use `esc()`. Builder's Python test, plus the DOM test I ran. |
| SEC-18 | **Discharged.** `notices_feed` uses `get_list` filtered on `for_user`. I read Frappe's own `mark_as_read` in `hrlocal-bench` (v16.33.1, `notification_log.py:282-292`): it filters on `for_user = session user` and `read = 0`. `[ASSUMPTION]` production runs the same Frappe version. |
| SEC-19 | **Discharged.** Exactly one key was added to every `ROW_KEYS` entry. No `ignore_permissions` added. The cap is unchanged. Test `test_every_part_row_is_the_old_keys_plus_waiting_since`. Only gap: the timestamp nit above. |
| SEC-20 | **Discharged (proven by grep).** No caller is left in any `.py`, `.js`, `.html`, `.css` or `.yml` outside `docs/`, apart from the measure script's "before" list. The ceiling went from 70 to 67. |
| Scope traps (`dict(...), name=X`) | Part A adds **no** scope code: the diff never calls `permitted_employee_filters` or `employee_in_scope`. The CI script works for the required forms; gaps are in Minor 1. |
| Pending links | All target panels exist (parts are always included and contain no Jinja). `my_leave`, `my_attendance_fix`, `attendance_fix`, `policy` and CXO `leave` go to the right screens. **`shift_request` and `goal_update` do not** (Majors 1 and 2). |
| Notices = grooming only | **Proven.** `NOTICE_DOCTYPES = (Grooming Mark, Grooming Review)`. Test `test_only_grooming_notices_in_part_a`. |
| No Send, expense or Birthdays UI | **Proven.** The diff (tests excluded) mentions none of them apart from one code comment. No hooks, patches, DocTypes or `access.py` changes. The DOM test guards the grid markup. |
| PII in payloads | No new personal field. Decline reason: own rows only, never when HR passes an `employee_id`. Notices: fixed keys. |
| Incoming work | All 5 commits are from this slice's author. No merge commits. `origin/dev` has not moved since the rebase. |

## AC verification (Part A)

| AC | Status | Evidence |
|---|---|---|
| 57, 59, 60, 61, 63, 65, 73 | Met | Read the code; DOM test passed (I ran it) |
| 58 | Met, thin test | One user, not three (Minor 4) |
| 62, 64 | Met | Builder's Python tests; I read them (`test_notices_076`). `EXPLAIN` is deferred to Part B |
| 66, 68, 70, 71 | Met | Code and builder's tests |
| 67 | Partial | Goal and KPI rows have no "waiting N days" (Minor 3); `Open` targets are wrong for 2 kinds (Majors 1 and 2) |
| 69 | Partial | Counts by kind work, but the "across your companies" label is wrong (Major 4) |
| **72** | **Not met** | Major 3 |
| 74, 75, 76 | Met | Code; `test_home_076` read. AC-76's "the bell updates" no longer applies, because decision 2 changed what the bell counts |
| 108, 109 | Met | Grep; ceiling test |
| 110 | Met, except 984 px | Nit |
| 111, 113, 116 | Met | DOM and builder's browser check |
| **112** | **Not met in 20 of 45 cells** | Major 5 |
| 114 | Partial by design | 45 cells, because Birthdays belong to Part C |
| 115 | Met; screen reader and 200% zoom not checked | Builder |
| 117 | Met (literal) | I ran it and broke it on purpose; gaps in Minor 1 |
| 118 | Met through the per-file ceiling test (strategy decision 5) | Does not run while Actions are failing (Minor 7) |

## NFR and the seven dimensions

| Dimension | Impact analysis said | Code shows |
|---|---|---|
| Performance | Degrades, but query count must stay flat in headcount | **Not flat for HR and System Manager** (Major 3). p95 was 437 ms locally, which passes today but has little headroom |
| Security | Improves | **Agree.** One endpoint with 3 `ignore_permissions` is gone; nothing new added |
| Reliability | Neutral | Agree. Each card has its own failure box; a double tap sends once (DOM test) |
| Scalability | Neutral if flat | **Degrades for HR**, growing with the correction queue |
| Maintainability | Improves | Agree. One bell source; the old panel and Activity are deleted. About 400 lines added to a hot file |
| Data integrity | Neutral | Agree. The reason Comment is written in the same request as the decision |
| Compliance / privacy | Improves | Agree. Activity is gone; the reason is shown to its owner only |

DevOps items (`07` §1 and §3): OPS-1 matches. OPS-2a could not be done because the live page has no `get_nav_counts`; the impact analysis already says this. OPS-3 is met for Notices. OPS-4 is met. OPS-12 asset-staleness and OPS-13 rollback belong to the release step, which I did not check. Rolling back Part A loses no data: leftover reason Comments and read marks do no harm.

## What to delete
- Nothing large. The slice is lean.
- `hmRefreshIfStale` is a candidate unless Surbhi wants it (Minor 6).
- `get_employee_dashboard.pending_approvals`, now read by nothing, should go in a follow-up.

## What was done well
- **The bell and the card share one function.** "N unread" cannot disagree with the bell, by construction.
- **No wrapper around Frappe's `mark_as_read`.** It already limits marking to the caller's own row, and I confirmed that in the source.
- **The decline reason is stored as a Comment with a subject marker,** and a test proves an ordinary note is never shown as the reason.
- **Measured before and after, on two fixture sizes, and the bad news came first.** That is how the AC-72 miss was found at all.

## Confidence
- **Proven:** everything above that has a file and line, the grep results, the DOM suite, the static checks, the scope-trap break test, and Frappe's `mark_as_read` source.
- **Taken from the builder, not re-run:** all Python test results, the query counts, and the 45-cell browser check.
- **Not checked:** DTC's attendance-fix queue depth, whether DTC uses Goals or Shift Requests, Safari or a real phone, and whether Frappe sends any notification when a Comment is added to a Leave Application.

## Subtract pass
I removed two draft findings: a "forged decline reason via a REST Comment insert" (I could not trace a real path; creating a Comment needs System Manager) and a "missing panel crash" (all panels are always included). I also folded the "builder misread `get_nav_counts`" point into Major 3 instead of keeping it as its own finding.

---

# Second review (after the fix pass), 28 Oct 2026

Fix commits reviewed: `ddb2e588`, `0b864005`, `c69eb2d9` (`git diff 6c5778be..HEAD`, 10 files). All three are by this slice's author. No merge commits. `origin/dev` was re-fetched today and has not moved since `b2547d1f`.

## Verdict: SHIP WITH FIXES

**One new dead end: a "KPI update" row in Pending opens a screen with no Approve button.** The goal half of the fix works. The KPI half does not, because the KPI history never tells the screen who may approve. Everything else from the first review is fixed in the code, not only in the notes. The new `document` goal id does not leak, and the server refuses out-of-scope goals by itself.

`SHIP WITH FIXES` is not permission to push.

**What I ran.** DOM suite: 17 files, 0 failed (the 076 file: 75 passed, 0 failed). Static checks, all exit 0: `check_scope_traps.py` and its `--self-test`, `check_app_integrity.py` (842), `check_api_paths.py --max 0`, `check_tag_balance.py`, `check_design_system.py`, `check_brand_spelling.py`, `check_undefined_js.js`, `check_portal_handlers.js`, `check_portal_trays.js --static`, `check_day_widget.js`. (That last one needs `portal.js` as its argument. With no argument it crashes, which is a problem with the script, not the code.)

**What I did not run: any Python test.** `hrlocal-076` and its redis stopped minutes before this review. The notes (line 226) say a restarted container may get a new address, and the database refuses it until a user is granted that address. That grant changes a database other work uses, so I did not start the containers. All Python results below are the builder's, and I say so wherever I use one.

## Findings, worst first

No P0. The fix pass opens no new exposure.

### Major A (P2, new): a KPI update row opens a "log your own progress" form, with no Approve button
- **Proven by reading.** `hmPendOpen` sends a `kind: "kpi"` row to `pfOpenLog(document, name)` (`portal.js:5825`). `pfOpenLog` (`portal.js:14214`) opens the employee's own "log a reading" modal: "Amount since your last update" and a Save button. Its history comes from `performance_api.get_kpi_update_log` (`performance_api.py:632-667`), which returns **no `can_action` key**. `renderUpdateTimeline` draws Approve and Reject only when `r.can_action` is true (`portal.js:14324`). So no one ever sees the buttons on a KPI row.
- **What happens.** A manager's report logs a KPI reading. Pending shows "Dinesh Pal · KPI update · Open". The manager taps it. They get a form asking for *their* progress on *his* KPI, and nothing to approve. If they type a number and press Save, the server refuses it (`_require_owns`, `performance_api.py:500`). That is safe, but it looks broken.
- **Not new, but now promised.** The old bell made the same call. KPI approval has had no button on the portal since the `can_action` change, because only `get_goal_update_log` got the flag. What is new: Pending counts KPI updates as "waiting on you" and offers Open. The builder's notes say "Approve and Reject are the existing buttons in those drawers". That is true for goals only. The end-to-end check used a goal. The DOM test only checks that `pfOpenLog` was called.
- **The CXO hits a similar dead end (Inferred from code).** A System Manager's "Goal and KPI updates · N waiting · your queue · Open" goes to the Team page (`HM_SCREEN.goal_update`). The builder measured that page showing 0 of them.
- **Smallest fix (needs Surbhi's yes, because it touches `performance_api.py`).** Add `can_action` to `get_kpi_update_log`, using the rule `approve_kpi_update` already enforces. This copies what `get_goal_update_log` already does. It is about five lines and one test. The "log your own reading" form at the top of the modal stays, as it is today. Alternative: leave KPI rows out of Pending, as was done for shift changes. Owner: Surbhi, then `hrms-fullstack-engineer`.

### Minor (P3)
1. **AC-72 is still not met to the letter. I think that is fine.** HR's `get_inbox` went from 111 to 36 queries at 980 people, and from 33 to 28 at 20 people (builder's numbers). The old cost went up with every queued fix. The new cost goes up with the number of *different managers* behind the queue. That number is limited by the org chart, not by how long the queue gets. To make the cost fully flat, we would have to read the share records ourselves instead of asking Frappe's `has_permission`. That means copying Frappe's permission logic, which is worse than the cost. **I recommend Surbhi accepts AC-72 in writing as "the cost does not grow with the queue".**
2. **"View all 40" lands on Team Attendance, not on a list of goals.** The Team page has no team-goals list. To see the goals, you tap a person and open their drawer (`openEmpDrawer` → `renderDrawerGoals`). With 3 people or fewer, each person's 2nd and 3rd goals are hidden. There is no "View all" then, only the existing "Team View →" link. Nothing is out of reach, but it takes two taps and a guess. A label like "See your team" would match where the button goes.
3. **Shift changes now appear nowhere on the portal for a manager.** This was Surbhi's call, and the notes record the gap. I log it here so it does not get lost. The server still works out the shift part on every Home load, then nothing shows it (P4).
4. **Older than this slice: `get_kpi_update_log` lets any HR-role user read any KPI's log by id.** In a tenant with several companies, that includes companies the user does not look after (`performance_api.py:638`). Unlike `get_goal_update_log`, it has no `_hr_may_act_for` check. This slice does not make it worse: the inbox only hands out ids inside the caller's scope. Route it to `hrms-security-privacy-engineer` as a SEC-26 gap. It is live on `main`.

<details><summary>Nits (P4)</summary>

- `TestGoalUpdateRowsCarryTheGoalOnlyInScope` depends on test order. `approve_goal_update` commits, so the "still Pending" test passes only because `test_the_manager_can_approve...` sorts last.
- The new tests have no check that HR from another company is refused. The scope query is older and was tested in 044, so these tests are thin, not useless.
- No server test covers KPI rows at all. That is how Major A got through.
</details>

## Earlier findings: are they fixed?

| # | Finding | Status | Evidence |
|---|---|---|---|
| 1 | Shift-change row led to a dead end | **Fixed** | Removed from `HM_KIND`, `HM_SCREEN` and `hmRowView`, and skipped in `hmPendingRows`. The chip subtracts the shift count (`portal.js:5747, 5790-5791`). DOM test passed |
| 2 | Goal update opened My Goals | **Fixed for goals, not for KPIs** | Goal rows call `gpOpenGoalDetail(document, name)`. `get_goal_update_log` returns `can_action`, so Approve is drawn. KPI rows: see Major A |
| 3 | AC-72: one query per queued fix | **Fixed in practice** | `once(("ac_mgr_submit", mgr_user), ...)` (`attendance_correction.py:1405`). **Behaviour unchanged (proven by reading).** `has_permission(REQUEST, "submit", user=...)` is given no document, so its answer depends only on the user. The memo lasts one call on `frappe.local` and is dropped in a `finally` (`call_cache.py`). When no memo is open, as in the `decide` endpoint, the check runs every time. `whole_queue` ignores its `filters` argument. That is safe, because `Part` always passes `self.filters` (`inbox_api.py:263, 275`). The new test fails with the old line: its spy counts one lookup per employee. What is left: Minor 1 |
| 4 | CXO "across your companies" | **Fixed** | Now "{0} waiting · your queue" (`portal.js:5739`). DOM test |
| 5 | AC-112 | **Fixed** (builder's browser check: 45 of 45; I did not re-run it) | My Goals shows 3. Team goals shows 3 people with 1 goal each, plus "View all N". My documents scrolls inside the card at 190 px |
| m | Scope-trap script skipped files it could not parse | **Fixed** | It now reports them and fails. `--self-test` covers this, and I ran it |

## The new `document` id (SEC-19, SEC-9)

| Question | Answer |
|---|---|
| Can a caller get a goal id outside their scope? | **No (proven by reading).** `document` comes from the same query as the row, limited by `Goal.employee IN (_pending_approvals_scope_query)` and `!= caller`. If scope cannot be worked out, the query returns nothing (fails closed) in three ways. No employee gives `name IN ()`. If `_scope_of` returns `None`, the count is 0 and the rows are `[]`. No permitted companies gives `[""]`. Employees get no rows (builder's test) |
| Does approve refuse out-of-scope goals on the server? | **Yes (proven by reading).** `approve_goal_update` refuses the caller's own goal (`refuse_own_decision`). Then it allows only the `reports_to` manager or HR. Then it refuses HR for companies they do not look after (`goals_api.py:1301-1323`). `approve_kpi_update` follows the same steps. The builder's test `test_a_manager_outside_scope_gets_no_id_and_cannot_open_or_approve` checks for a `PermissionError` and an unchanged row |
| Can it be opened out of scope? | **No, for goals.** `get_goal_detail` checks the HR company or the reporting line, and throws an error otherwise. The KPI read path has the older gap in Minor 4 |
| Any trap like `dict(permitted_employee_filters(), name=X)`? | **None.** The diff adds no call to `permitted_employee_filters` or `employee_in_scope`. `check_scope_traps.py` passes |
| Does the id itself reveal anything? | No. The row already shows the person and the goal name. The id adds a key, not a new fact |

## Did the caps hide something a person needs?

- **My Goals:** no. "Full Portal →" opens the full list.
- **Team goals:** no, but the route is indirect (Minor 2).
- **My documents:** **scrolling inside the card is acceptable.** There is no documents screen to link to, and building one would be new scope. The card can be reached by keyboard, has a label, and has a summary line above it. **Not checked:** whether missing or expiring documents sort to the top, so the ones that matter land in the first three rows; and how the scroll inside the card feels on a real phone.

## AC changes since the first review

| AC | Was | Now |
|---|---|---|
| 67 | Partial | **Still partial.** Goal rows are right. KPI rows lead nowhere (Major A). Goal and KPI rows still have no "waiting N days" (first review, Minor 3) |
| 69 | Partial | Met |
| 72 | Not met | Not met to the letter, met in practice (Minor 1). Needs written acceptance |
| 112 | Not met | Met (builder's browser check) |

## Seven dimensions, after the fix pass

- **Performance and scalability:** better than at the first review. HR's cost no longer depends on how long the queue is.
- **Security:** unchanged. No new `ignore_permissions`. The one new key stays inside the existing scope.
- **Reliability, data integrity and compliance:** unchanged.
- **Maintainability:** slightly better. The fix reuses the existing memo instead of adding a new mechanism.

## What to delete
- Nothing new. The fix pass added no abstraction. It reused `once()` and the existing drawers, and "View all" opens an existing screen. The server-side shift part is now never shown. It can be deleted once Surbhi decides its future.

## What was done well
- **Reusing the one-call memo instead of a cache.** A permission answer cannot carry over into another request.
- **Taking the goal id from the row's own scoped query.** A second lookup would have needed its own scope check.
- **The builder reported their own bad news** (Team's list did not match the inbox) before the review found it.

## Confidence
- **Proven:** every file and line above, the DOM suite, the static checks, and the scope-trap script.
- **Builder's results, not re-run:** Python tests, query counts, the 45-cell balance check, and the Chrome end-to-end approval.
- **Not checked:** whether any live tenant uses KPIs, which decides how much Major A matters in the first week; the order of My documents; a real phone.

## Subtract pass
I removed a draft finding that `whole_queue` could return rows for the wrong filters, because `Part` always passes the same filters. I also moved a draft P2 about the HR gap in `get_kpi_update_log` down to Minor 4, because this slice does not make it worse.
