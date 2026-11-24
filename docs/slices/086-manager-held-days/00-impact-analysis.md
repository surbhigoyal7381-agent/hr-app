---
slice: 086-manager-held-days
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-11-23
status: strategy for Surbhi. STEP 1 ONLY. No code written, nothing pushed, nothing deployed. Waits for her approval.
risk tier: 1 (files requests that release pay; who may act for whom; personal free text) - strong model to build, independent reviewer, separate security check
built on: worktree /Users/mac/hr-app/.claude/worktrees/086-manager-held-days, branch slice/086-manager-held-days, rebased onto origin/dev 412d5361 (23 Nov 07:52 UTC, "Slice 088: the paper round gets its own switch")
---

# 086 - Impact analysis and strategy

## 0 - The short version

**Good news first: the spec is bigger than the code needs. 087 and 088 already built three things 086's spec still lists as work.** Bad news after.

1. **Already on dev, so 086 builds only tests for them:** the "no Confirm for a manager's added time" rule (G8: `punch_fix._own_the_confirm_fields`, `manager_adds`), the employee's "Not right" on a manager-added request (G13/AC-61: `punch_fix.confirm` says so in its docstring), and the day-sheet notice (`day_sheet` returns `can_not_right`, `filed_by_name`, `filer_reason`; `portal.js` `pfxConfirmBlock`). Also on dev: 088's printed monthly notice lists manager-added times.
2. **The spec's F5 worry is already fixed by 087.** A Declined or Withdrawn draft no longer blocks a new request for the same day (override in `overrides/attendance_request.py`). AC-2 and the state table in the spec are stale on this point.
3. **F1 (ALV-425) is still open on dev.** Nothing closed it. `raise_for_report` still skips the direct-report check for anyone who may submit (`attendance_correction.py:2488`).
4. **F2 is still open on dev.** Nothing stops a manager (or the employee) editing or deleting a filed request. Under case A there is no Confirm to clear, so 086 must add a guard.
5. **A trap the spec did not see:** a row lock plus the stock duplicate check is not enough on MariaDB's default isolation. The duplicate check must be a *locking* read too (section 6.4).
6. **The employee's printed notice carries the manager's reason.** 088 prints it. 086's reason box must say so (today's `acHeldForm` already does). The approved prototype does not. Needs her yes (decision D-4).

**Rung 4: a small amount of new code.** One new server file with two calls, a small guard in `punch_fix.py`, one line in the stamp, one hook line, and a Held view in the existing Whole team page. No DocType, field, setting, patch, queue, cache or app.

## 1 - What I read, and on which checkout

All reads are in **worktree `086-manager-held-days`, branch `slice/086-manager-held-days`, SHA 412d5361 (= origin/dev)**. **Not run:** no test, no bench, no browser, no site. Every "the server does X" below is code reading, labelled **proven (read)**. One Docker read: `grep` and `git describe` inside `alv089-bench` (a different session's stack, read only) gave Frappe `v16.33.1` and showed `frappe.db.get_value(..., for_update=)` exists and `rollback(save_point=)` exists.

**Rebase note (said out loud).** The 10 doc commits on this branch were already on dev under other SHAs (086 docs on dev are byte-identical to the branch; I diffed the folder). Replaying them conflicted on `ux-learnings.md`, `01b-ux-design.md` and `prototype-v2.html`. I aborted that, then moved the branch to origin/dev with `git rebase --onto origin/dev 407a8bd8`. Nothing was lost: dev holds every one of them. The branch now has **zero commits of its own** until this file is committed.

**What came in (164 commits since 20 Nov, base 2e31151f):**

| Group | Commits | What it means for 086 |
|---|---|---|
| **Slice 087** (attendance follows punches) | 61 on 21 Nov, 6 on 22 Nov, 1 on 20 Nov | The foundation. 22 commits touched `punch_fix.py`, 10 `attendance_correction.py`. Ships the day sheet, Confirm/Not right, case A (counsel 21 Nov), reason on every request (ALV-418). **087 is on main** (`f68f2333`, the 22 Nov release) |
| **Slice 088** (register notice + signed paper) | 9 on 22 Nov, 2 on 23 Nov, plus 2 fixes | `register_notice.py` (951 lines), its own company switch `alvoraa_print_change_notices` (ships off). **088 is on dev only, not on main** (checked: `7e1071a1` is not an ancestor of origin/main) |
| **Slice 089** (manager profile edits) | 31 on 22 Nov | Different surface (profile edits). No overlap with 086 files found |
| **ALV-430** | 3 + 2 test commits | Confirm is now a **per-company switch** (`alvoraa_employee_confirms_changes`). Off = no Confirm at all. DTC and Grace run it off |
| **ALV-434** | 1 | `attendance_correction.py` - a refused approval says why (HR card) |
| **ALV-432** | 1 | The manager's form says the reason is required. `portal.js` |
| **ALV-402 / 404** | 3 | A punch after midnight counts on its shift day; a lone OUT is held. `held_day.extra_when` and `punch_fix.derive` use it |
| **ALV-411 / 412** | 5 | Attendance writes are POST only; HR reads punches only in scope |
| ALV-392 / slice 085 | 2 | Accepted risks, screen fixes |
| ALV-428, ALV-435, ALV-394/396/397/399, ALV-422/423, sidebar | about 20 | Joiner sign-in, secret scan, sidebar. No overlap |

**Files 086 will touch, and how busy each is:** `punch_fix.py` (22 commits since the base), `attendance_correction.py` (10), `held_day.py` (8, read only for 086), `register_notice.py` (7, read only), `hooks.py` (9), `portal.js` (24 commits; now 26,758 lines, 1,389,551 bytes), `overrides/attendance_request.py` (1, read only).

## 2 - The questions the spec asked me to answer first

### F8 - the one-punch inference, and whether the page knows the hold is on

- **How the inference works (proven, read).** `portal.js acHeldForm` asks "arrive" when `x.held_single_is_out` is true, otherwise "leave". The server sets that in `attendance_correction._held_flags` (line 1014): `len(punches) == 1 and punches[0].log_type == "OUT"`. So: one punch tagged OUT means "arrive is missing". **Anything else, including an empty log type, means "leave is missing".**
- **Consequence for DTC (memory note, DTC check-ins carry no log type, not re-checked today):** the page will always say "leave". That is the right guess for most days but is exactly why the Change link exists.
- **The inference is cosmetic.** The server decides the kind from where the typed time falls among the counted punches (`punch_fix.derive`, line 329, "a log type sent by a client is never read"). So the Change link is only a label unless the send call compares (spec G10, AC-26). I agree with that finding.
- **Can the page tell the hold is on?** The month view can (`"hold_on": _switch_on(me.company)`, `attendance_correction.py:695`, read by `acHeldOn`). **`team_days` returns no `hold_on`**, so the Whole team page cannot. The new list call returns `hold_on` for the caller's company, same as the month view. Multi-company managers see the caller's company answer; I treat that as an acceptable simplification (label **acceptable simplification**).

### F5 - declined or withdrawn request at docstatus 0

- **Decline and withdraw leave a draft** (`attendance_correction.py:1097-1106`, `_state`; the `withdraw` comment at 1274). That part of the spec is right.
- **The stock check would block it** (`hrms/.../attendance_request.py:109-132`: `docstatus < 2`).
- **But 087 replaced that check for punch fixes** (`overrides/attendance_request.py`, `validate_request_overlap`): a new punch fix is refused only while another request for the day is `docstatus 0` and **not** Declined/Withdrawn, or an ordinary request is approved. **So a Declined or Withdrawn draft does not block a new request.** `hooks.py:968` registers the override; the file says a test pins it is the only override.
- **What it means for 086:** the Held list should offer a day again when its only request is Declined or Withdrawn. "Open request" = `docstatus 0` and `alvoraa_review_status not in DONE_STATES`. `attendance_correction.DONE_STATES` already exists (line 1316). **The spec's AC-2 and section 7 table ("`docstatus < 2`") must change to this.** The edge-case row "declined day is not re-offered" is wrong.
- **Not run.** [inferred from reading; the engineer proves it with a test: decline a held-day request, then file a new one.]

### F1 - ALV-425, shut the hole inside `raise_for_report` too?

- **Open on dev (proven, read).** `if not _may_review():` guards the direct-report check at `attendance_correction.py:2488`. 087 and everything since left it. No commit mentions ALV-425 (searched `git log origin/dev --grep`; no code comment names it either).
- **What shutting it inside would break (grep counts).** `raise_for_report`: 42 lines in 7 files, **12 non-test**. Non-test callers: 3 JS call sites in `portal.js` (lines 7527, 7654, 17522), every one drawn only where the server says `can_raise`, and `can_raise` is `r.employee in direct_ids` for HR too (`attendance_correction.py:2396`; the comment at 721 says HR is "NOT given it"). So **no screen offers a non-direct report to anyone.** Tests: 19 lines in 4 files. **At least one test uses an HR login to call it for someone who is not their direct report:** `test_punch_fix_087.py:976-983` ("HR is used here because..."). It would need a direct-report setup. `test_held_day_085.py:607` needs checking.
- **My recommendation: shut both, and delete the `if`** (one line removed; the check then always runs). Cost: update the 087 test above. Benefit: ALV-425 closes in full, the old single door and the new bulk door agree.
- **Decision D-1 for Surbhi** (she has not answered F1). If she says "new call only", the old door stays open and ALV-425 stays open.

### F2 - SEC-7, the filer's edit and delete (case A)

- **What exists (proven, read):** `punch_fix._own_the_confirm_fields` clears a Confirm when content changes (line 491). Under case A there is no Confirm, so that does nothing. `attendance_doors.refuse_raiser_submit` stops the raiser **approving**. **There is no `on_trash` hook for Attendance Request** (`hooks.py`: `on_trash` appears at lines 203, 299, 335, 421, 426, 543, 593, none on this DocType). Stock permissions (`attendance_request.json`, read): the **Employee role holds read, write, create, delete with no `if_owner`**. `validate` blocks changing the employee (`punch_fix.validate`, "never changes ... for anyone").
- **What 086 must add (small, ~12 lines):** in `punch_fix.validate` (it already holds `before`), refuse a change to `CONFIRMED_CONTENT` fields on a request **filed for someone else** (owner is not the employee's own login) unless the saver is HR (`held_day._filed_by_hr`) or Administrator; and one `on_trash` line in `hooks.py` with the same test for delete.
- **A point beyond the spec:** the stock Employee role lets the *employee* edit the manager-filed request too (self-serving time change) and delete it (erasing what was said in their name). I propose the rule "nobody but HR changes or deletes a request filed for someone else", not only "the filer". It is the same ~12 lines and closes both. **Decision D-2** (tell Surbhi; it is wider than 01c's wording).
- Approval is unaffected: `decide` writes with `db_set` and submit changes no content field; the guard keys on changed content, not on the user alone.

### F10 / ALV-426 - does 088 already satisfy it?

- **For staff with no login and no app: mostly yes, in substance, once 088 is on main and its switch is on.** Read: `register_notice.qualifying_changes` (line 160) lists every approved, not-undone punch fix **filed by anyone other than the employee** (owner test at line 224), and does **not** test `alvoraa_needs_confirm`. So a manager-added time with no Confirm is on it. `sheet_rows` (line 486) prints `filed_role: "Manager"` and `filed_by` = the manager's name; `_reason_of` takes the text before the first blank line, so the manager's reason is printed and the stamp is not. The 088 design gate (D-4, `docs/slices/088.../01b-ux-design.md` lines 218, 227) says in so many words that manager-added changes appear.
- **For staff who have the app: yes.** `my_changes` (line 897) returns the same list with state "shown" for a manager's plain addition (comment: AC-53).
- **What is missing (sized):**
  1. **088 is not on main.** 086 cannot ship before it. (Blocks release, not build.)
  2. **The switch is off by default** (`alvoraa_print_change_notices`; `notices_are_on` answers no when off or the column is missing). DTC and Grace need it switched on by Surbhi's word, each on its own site. (Config, not code.)
  3. **The notice appears only after HR approves**, only in the month's round, and **only if HR runs the round**. Nothing forces it. Whether counsel's "register or payslip" is met by an HR-run monthly print is Surbhi's and counsel's call. **Payslip lines are not built** and 088's brief deliberately left them out ("differs per tenant; DTC pays outside the portal").
  4. **No test proves a 086-style request reaches the notice** (stamp text and "One of n" must not leak into the printed reason). That is 1 test.
- **Size: S.** One integration test, one config change per site, one sentence for counsel. **No new build.** I recommend Surbhi marks ALV-426 "covered by 088 + switch on" and not a separate build, unless counsel says paper alone is not enough (then payslip lines become a real piece of work: M, and not in 086).

## 3 - Cross-module reach

| Area | Reach |
|---|---|
| `alvoraa_portal` | New file `held_team.py` (proposed name, with `held_days` and `send_held`; the recheck is D-5). Edits: `punch_fix.py` (guard), `attendance_correction.py` (stamp line, F1 line), `hooks.py` (1 `on_trash` line), `public/js/ess/portal.js` (Held view), `scripts/check_portal_trays.js` (the confirm dialog joins the inventory, as 088 had to), tests |
| `hrms` | Read only: stock Attendance Request (overlap, now overridden), Employee `reports_to`, `user_id`. **No file edited** |
| `erpnext` | Not touched |
| `alvoraa_goals`, `alvox_compensation` | Not touched |
| Pay | A Held day is unpaid until fixed. HR's approval releases it (087 `apply`) and refreshes the slip (087's job on queue `short`). 086 files requests only; it moves no money itself |
| Attendance | Reads Held rows and punches; writes only Attendance Request drafts through `raise_for_report` |
| Leave, appraisals, goals, org structure | Leave: `day_state` refuses a leave day (087). Org structure: reads `reports_to`. The rest untouched |

### Callers I grepped (counts from this worktree, `*.py *.js *.html` under `alvoraa_portal` and `hrms/hrms`)

| Function / text | Lines, files | Non-test lines | What 086 does to it |
|---|---|---|---|
| `raise_for_report` | 42 lines, 7 files | 12 (3 JS call sites, rest comments and the def) | Stamp gains the manager id (1 line). Maybe the `_may_review` line (D-1). Signature unchanged. The new call is a 4th caller |
| `"on behalf of the employee"` (the stamp text) | 4 lines, 3 files | 3 | One test asserts the old text: `test_held_day_085.py:616` (updated in the same change) |
| `_own_the_confirm_fields` | 10 lines, 4 files | 3 | **Not changed** (G8 is already built) |
| `derive(` | 10 lines, 2 files | 7 | Called, not changed |
| `day_state(` | 9 lines, 2 files | 9 | Called, not changed |
| `team_days` | 20 lines, 8 files | 6 | **Not changed** (sibling function; section 6.1) |
| `_may_review()` | 30 lines, 9 files | 13 | Not changed (except line 2488 if D-1) |
| `qualifying_changes` | 4 lines, 1 file | 4 | Not changed; one new test reads it |
| `punch_fix.validate` | 1 hook entry (`hooks.py` "Attendance Request" `validate`, first) | | Gains the guard |

## 4 - Personas

| Persona | What changes |
|---|---|
| **CXO** | Nothing new. Sees no new list. Counts as a manager for the Held list only if they have direct reports. A CXO login with an HR role is still limited to **their own direct reports** on this page (SEC-1) |
| **HR Manager / HR User** | Receives requests as today (087 card). Sees who vouched, as whose manager, and "one of n" (stamp). Approves without waiting for Confirm. **Cannot** use the new list for people outside their direct reports (same fence as everyone) |
| **Manager** | New: Held view, one send, up to 50 rows. Cannot edit or delete after filing. Needs the tenant manager switch on. Gets per-row refusals in words |
| **Employee** | Told on the day sheet (already built) and on the monthly notice (088, if the switch is on). Can say Not right. **More of their day is visible to a manager's reason**: the reason prints on the paper notice |
| **Colleague, skip-level manager, guest** | Nothing. Refused with one fixed sentence, no name |

## 5 - The seven non-functional dimensions

| # | Dimension | Verdict | Why (what I checked) |
|---|---|---|---|
| 1 | **Performance** | **Neutral** for everything that exists. **One number to measure:** the send | List: held rows are filtered on the Attendance query **before** the punch read, one punch read for the page's rows, one open-request read: about 8 queries at 5 and at 50 rows (AC-6). **The send is linear by design** and I found why it is heavier than the spec's 50-100 ms guess: per row, `raise_for_report` calls `_subject`, which for a non-HR manager runs `_reports_to(me, deep=True)`, a walk down the reporting line, **once per row**; plus `_employee_for` three times, the filing-window and switch reads, the 087 `validate` (day state, derive, repeat check) and the insert. That is dozens of queries per row. **20 rows = the daily case; 50 rows = the cap.** I do not add a cache. If the measured 20-row send is over about 3 s or the 50-row over the 10 s kill number (AC-40), the one change I would make is to hand `_subject` the manager's reports once per request. Not before a number says so. Payload: 50 rows, about 4-6 KB gzipped (estimate, not measured) |
| 2 | **Security** | **Improves** | New per-row direct-report check (SEC-1), filer edit/delete guard (SEC-7, was missing), ALV-425 closed for the new door (and the old one if D-1). **Risk added:** a new write door that files pay-releasing requests in bulk. Held in by: POST only, CSRF, rate limit, 5 keys only, no `ignore_permissions`, `NoQuietBypass` coverage |
| 3 | **Reliability** | **Neutral** | A savepoint per row; a lock wait stops the loop and answers "not sent" for the rest with **one** Error Log entry of counts and ids (OPS-56). A refused row leaves no document. Answer lost: the page recovers by asking, never re-sending |
| 4 | **Scalability** | **Neutral** | Bounded: 50 rows a call, 50 a page, direct reports only, 30 sends an hour. A 442-person HR view is never listed (the list is direct reports only). A manager has tens of reports, not hundreds |
| 5 | **Maintainability** | **Neutral to improves** | One new file with two calls that **call** `raise_for_report`, `derive` and `day_state` rather than copy them. The Held view is added to one existing page. The one thing that worsens: `portal.js` grows by roughly 400 lines (my estimate) in a 26,758-line file |
| 6 | **Data integrity** | **Improves, with a trap** | The per-day row lock (below, 6.4). The stamp gives a record that can be rebuilt a year later (SEC-8). **Trap:** lock plus a plain read of "is there an open request" does not hold under MariaDB's default REPEATABLE READ if the request's snapshot started earlier. The fix is one extra locking read, in the same function |
| 7 | **Compliance / privacy** | **Slightly degrades, controlled** | New: one reason per row (sensitive free text) per request, as 087 already allows one at a time. **New fact: 088 prints that reason on the employee's monthly notice, on paper.** So the manager's reason box must warn like the employee's own `acHeldForm` does ("This reason is printed on the employee's monthly notice."). Not in the approved prototype (D-4). Nothing in a log, error, email or the send's answer. No count per manager, no ranking, no reminder |

## 6 - Proposed approach

### 6.1 The smallest path (three lines)

1. **Read:** a new `held_days` call lists the caller's direct reports' Held days that have no open request, one day at a time. **Write:** a new `send_held` call takes up to 50 rows of `{employee, date, time, in_or_out, reason}` and, per row in its own savepoint, checks the caller and the time, locks the day, then calls the existing `raise_for_report`, which inserts the 087 request. Results come back per row.
2. **Reuse, do not rebuild:** `raise_for_report` (stamp, reason rule, held-day fields, window), `punch_fix.derive` (kind of punch), `punch_fix.validate` and the stock-override overlap check (087), `field_app_limits._limited` (the 30 an hour limit, exactly as `register_notice.open_notices` uses it), `access.log_refusal` (security log), 087's day sheet and Not right for the employee, 088's notice for the register. On the screen, reuse `acHeldForm`'s words ("Send to HR for <first name>", the reason box and its printed-notice line), 085's Held chip, and 087's strip and gap sheet.
3. **Add only what is missing:** the two refusals (AC-25, AC-26), the lock with its locking read, the filer edit/delete guard, the stamp's manager id, and the Held view on the Whole team page.

### 6.2 Functions and files

| File | Change | Rung / why not cheaper |
|---|---|---|
| NEW `alvoraa_portal/held_team.py` | `held_days(day=None, start=0)` (GET, read-only); `send_held(rows)` (POST, `_limited(SELF_KEY, "user", 30, 3600)`) | New code. Configuration cannot do it. `team_days` cannot be reused as is: it reads every Attendance row for the period and the punches **before** it counts and pages, and its `only` filter is a punch-count flag, not the Held status. Browser loop on `raise_for_report` rejected: nginx `/api/` allows 120 a minute (07 OPS-41) and a half-done send the manager cannot see is worse. A new file, not more lines in the 2,569-line `attendance_correction.py` |
| `punch_fix.py` `validate` | Filer edit guard (F2): about 8 lines | Extend. A permission change would be a Custom DocPerm and cannot say "unless changed content" |
| `hooks.py` | One `on_trash` entry for Attendance Request, at the end of the list with a comment (hot-file rule) | Extend |
| `attendance_correction.py` | Stamp: add `({employee id})` and "their reporting manager" (1 line). D-1: delete `if not _may_review():` guard (1 line) | Extend |
| `public/js/ess/portal.js` | Held chip, day control, rows, bar, one confirm, banner, per-row refusals. New functions in their own prefix (`hdl...`, 0 existing matches for `hdl[A-Z]`), hooked at `trChips`/`trRows` | Extend. Prefix rule from `parallel-work.md` |
| `scripts/check_portal_trays.js` | Register the confirm dialog (088 had to, in `5cf7e418`) | Gate |
| tests | One new module (name: engineer's), plus updates to `test_held_day_085.py:616` and, with D-1, `test_punch_fix_087.py:976-983` | |

**No Custom Field, patch, fixture, `patches.txt` line, DocType, queue, cache, setting, or nginx change** (OPS-61).

### 6.3 Where I differ from the spec (so Surbhi can say no)

| Spec says | I propose | Why |
|---|---|---|
| G8: change `_own_the_confirm_fields` | **Do not.** It is already there. Add a pin test (AC-54, AC-55) | `manager_adds` (`punch_fix.py:456`) exists. One gap: it tests "not HR and not the employee", not "the direct manager". After D-1 and per-row scope in `send_held` that gap cannot be reached by 086's door; Desk and REST inserts are limited by `manager_scope` (direct reports only, per the comment at `raise_for_report`). **[inferred; the AC-55 five-case test proves it]** |
| G13 / AC-59 / AC-61 / P-7: build the day-sheet notice and check `confirm` | **Do not build.** Test it. `confirm` accepts an unmarked request and Not right works (`punch_fix.py:1097-1131`); `day_sheet` returns `can_not_right`; `pfxConfirmBlock` draws it | Already built by 087. One small check: the notice text for the *held* day (decision 4: "Your manager already sent this day to HR") - to confirm in a browser test whether the employee's form is hidden while a request is waiting |
| G5 / SEC-1: per-row check by calling `_reports_to` per row | Compute the manager's direct reports **once** per call, a set, then check each row against it | Avoids an extra N queries. `raise_for_report` still repeats its own check per row (the cost in 5.1) |
| AC-25 "time later than the server clock now" on the raw time | Compare the **derived datetime** (`derive` returns it) to now | Handles a night shift (a time after midnight belongs to the shift's day; ALV-402) |
| AC-36 order of the stamp | Reason, then "Raised by {name} ({id}), their reporting manager, on behalf of the employee.", then "One of {n} days sent together." as in the spec. **To avoid a parameter on a client-callable function, `send_held` appends the "One of n" line to the text it passes as `explanation`... this would put it before the "Raised by" line.** Choices: (a) accept the reversed order, or (b) drop "One of n" | `raise_for_report` appends the stamp after what it is given; adding a `batch` argument to a whitelisted function is a new input. Smallest: (a). Decision D-3 |
| AC-38 / OPS-58: a separate recheck call | **Candidate to drop:** after a lost answer, call `held_days` again. A row no longer listed is either sent or fixed meanwhile; either way the manager has nothing more to do. The banner says so | Removes one endpoint, one rate-limit row, one test. **Weaker than AC-38** (cannot say "sent" for sure). Decision D-5 |

### 6.4 The lock, written out (data integrity)

- Inside each row's savepoint: `frappe.db.get_value("Attendance", {employee, attendance_date, docstatus: 1}, "name", for_update=True)` (the same call `punch_fix.day_row(for_update=True)` already makes, line 240), **then a second locking read** of open requests for that employee and day (`frappe.db.get_value(..., for_update=True)`; `frappe.get_all` has no `for_update` in this Frappe, read in `db_query.py`: no match), then `raise_for_report`.
- **Why the second read matters [inferred, MariaDB default REPEATABLE READ; Frappe sets no isolation level I could find in `database/*.py`]:** the second caller waits at the first lock, then the stock overlap check uses a plain read from a snapshot taken earlier, and may not see the first caller's new request. A locking read always sees the latest. **The test must fail first with both locks removed, and I prove it on two real connections, not by calling the function twice** (AC-31).
- **InnoDB keeps row locks until the transaction ends even after `ROLLBACK TO SAVEPOINT` for rows that were already locked [inferred from MySQL documentation recall, not read in this repo]. So up to 50 locks are held until the call ends.** Rows are processed **sorted by (employee, date)** so two overlapping sends take locks in the same order (no deadlock between them). A lock wait stops the loop (AC-32). Not run.

### 6.5 The refusal sentences and the log

Per-row refusal comes back as a sentence from the server; `frappe.clear_messages()` after each caught row (memory: `frappe.message_log` is a proxy, use the function). A stranger row logs one `security.log` line through `access.log_refusal` and returns the fixed sentence with no name (SEC-1). **Note for the build, ALV-391 (fixed on dev):** security log lines were never written until 20 Nov; check the logger level is the fixed one in this checkout before relying on AC-22's "six lines".

## 7 - How each SEC, PRIV and OPS item is met

| Item | How | Proof planned |
|---|---|---|
| **SEC-1** scope per row, every caller | Direct-report set computed once from `Employee.reports_to` (Active); each row checked; own id, skip-level, other manager's report, other company, leaver, made-up id all get the same fixed sentence; manager Left or tenant switch off: whole call refused | 7-case test AC-22, then as HR User and as a submit-right login (AC-23). Fails first with the check removed |
| **SEC-2** every row through `raise_for_report`, nothing around it | The row calls it; no `ignore_permissions`; no copy of its rules | `NoQuietBypass` extended (AC-41); blank-reason break test (AC-28) |
| **SEC-3** fixed shape, cap of 50 | Read five keys only; more than 50 refused whole; duplicate employee-day in one send refused | AC-19, 20, 21 |
| **SEC-4** POST, CSRF, rate limit | `@frappe.whitelist(methods=["POST"])`; `_limited(SELF_KEY, "user", 30, 3600)` (limit counts calls per endpoint name, so the list and the send do not share a counter) | CSRF proved **over HTTP** with the break-and-restore (AC-18); the 31st send refused (AC-35). `check_api_paths.py` gate run locally |
| **SEC-5** replay / double send | Lock + locking read (6.4); a repeat gets "Already waiting with HR" | Two-thread test, fails first with the locks removed (AC-31) |
| **SEC-6** case A | **Already built** by 087 (`manager_adds`, `punch_fix.py:456`) and gated per company by ALV-430. 086 pins it. The send reads no `needs_confirm` or `set_aside` key | AC-29, 54, 55 (five requests, five values) |
| **SEC-7** filer cannot change or delete | New guard in `punch_fix.validate` + one `on_trash` line (F2, D-2) | Manager's `set_value` refused, HR's allowed; manager's and employee's delete refused (AC-57, 58). Fails first with the guard removed |
| **SEC-8** rebuild a year later | Stamp gains the manager id and "one of n"; `owner`, `creation`, `alvoraa_*` fields already hold the rest | AC-36, 37, run for file, approve and Not right |
| **PRIV-1** time, In/Out and one reason, nothing else | Five keys; no photo, GPS or login yes/no in either call | AC-7, 34 |
| **PRIV-2** reason goes nowhere new | Not in logs, Error Log, emails, notifications or the send's answer; Error Log entry holds ids and counts only. **Exception to disclose: 088 prints it on the notice (D-4)** | Marker-string search across `logs/*.log`, `tabError Log`, `tabEmail Queue`, `tabNotification Log` (AC-63); the script reason shown as text on three screens (AC-27) |
| **PRIV-3** what employee and HR see | List and answer carry no `user_id`, email, GPS, another person's punches | AC-7 |
| **PRIV-4** nothing on a shared phone | No `localStorage`, `sessionStorage`, no draft; no `frappe.cache` entry | AC-10, 52 (both stores inspected; Back after logout) |
| **OPS-39, 53, 54** list: server filter before the punch read, constant queries, one page | `held_days` as 6.1; punches read once, grouped with `shift_day` (not `_punches_by_day`, which groups by wall-clock date and would put a midnight punch on the wrong day: ALV-402) | Query count equal at 5 and 50 rows (AC-6); p95 on a 60 and a 442-person copy, **recorded not assumed** |
| **OPS-40, 41, 55** one call, cap 50, per-row savepoint, sync | `send_held` as above | 50-row timing on a DTC-size copy; **over 10 s = stop and rethink** (AC-40) |
| **OPS-42, 43** cost lands on HR; no new emails | No email, Notification Log or Inbox row of its own (087's Inbox behaviour is 087's) | Counts of Email Queue and Notification Log around a send (AC-39) |
| **OPS-44, 57** idempotent per employee and day | 6.4 | AC-31 |
| **OPS-45, R-1** no daily cap | None built (Surbhi) | |
| **OPS-46, 47** page weight | No new file; estimated 6 KB gzipped extra; one page of 50 | Measure once on dev (gap: no test) |
| **OPS-48, 60** answer shape, logs | Per row `{employee, date, ok, request or sentence}` plus counts that equal the entries; Error Log on a fault only, counts and ids | AC-33, 34 |
| **OPS-49, 50** no caching, nothing public | No `frappe.cache`; GET list is read-only; the response header is **written down from a real call, not assumed** | AC-10 |
| **OPS-51** shared note | Gone: a reason per row (v2) | |
| **OPS-52** time it on a copy | DTC-size throwaway stack (`REHEARSAL.md` route), before the usability test | |
| **OPS-56** partial failure is a normal answer | Per-row sentences; a lock wait or unexpected error handled as in 6.4 | AC-28, 32, 33 |
| **OPS-58** answer-lost recheck | `held_days` re-read (D-5) or a small read-only call | AC-38 or its replacement |
| **OPS-59** rate limits, nginx unchanged | One send is one call | AC-35 |
| **OPS-61** no migration | None. `portal.js` needs `assets.json` moved after any `docker cp` (memory: asset version trap) | Release check |
| **OPS-62, R-2** order and release checks | 087 on main: **done** (`f68f2333`). **088 must reach main before 086** (ALV-426). A worker on `short` registered | Pin file + container + file, per the deploy-pipeline note |

## 8 - Cost-ladder position and what I would subtract

**Rung 4 (new code, no new DocType).** Rungs rejected, each with the reason: (1) *already there* - the Whole team page has no Held view and the `only` filter is a punch-count flag; (2) *configuration* - no setting makes one send fan out to many requests; (3) *customisation of an existing page* - this **is** that, taken as far as it goes; the send call is the part that cannot be a customisation. (5) New DocType and (6) new app: nothing to store.

**Subtract pass (what I remove from the spec's plan):**
- G8 code change (already in 087). Replaced by a pin test.
- G13, P-7, AC-59 and AC-61 as *build* work (already in 087). Replaced by tests and one browser check.
- The F5 "stale" edge case and its special code (087's override already lets a Declined day back in).
- Possibly the separate recheck endpoint (D-5).
- No cache, no job, no batch-id field, no setting, no counter on the reason box, no "Take back" (the spec already dropped these).
- **Not subtracted, kept on purpose:** the two refusals (AC-25, 26), the lock with its locking read, the filer guard. Each stops a real harm, found in the spec or here.

I removed nothing else. If the 20-row send measures well I would still keep the lock.

## 9 - Risks

1. **A manager invents times (R1).** Reduced by design (no blanket time, real punches beside the box, a reason per row, the employee told, HR looks, 088's notice), not removed.
2. **A manager's false earlier time could pay someone less than they worked (spec risk 5).** Same protections.
3. **The send's speed is unmeasured.** The N+1 in `_subject` is real; the kill number is 10 s for 50 rows. **I will measure before I call it done.**
4. **The 3+ punch row is the riskiest screen piece.** 087's strip and gap sheet (`acPf*`, lines 6367-6629) keep their state in one global `acPf` for one day. A list of rows needs that state per row. I would build rows with one or two punches first and the timeline row last, and say if it does not fit (then it is a spec change, not a quiet cut).
5. **The reason is now printed on a paper notice (D-4).** A manager who types "his mother is ill" puts it on paper in the shop. The box warning is the only protection; HR can still see it before printing.
6. **Release depends on two other pieces:** 088 on main with its switch on at DTC and Grace (ALV-426), and F2. Neither blocks the build.
7. **Hot files.** `portal.js` (24 commits in three days) and `hooks.py`: new functions with their own prefix, one hook line at the end, fetch before every commit.
8. **My own labels to keep honest:** the isolation-level claim in 6.4 and the InnoDB savepoint-lock claim are **inferred, not proven**. Both are decided by tests on two real connections, not by this document.

## 10 - Parallel-work check

- **Fetched:** `git fetch origin dev main`. Incoming read (table in section 1). 164 commits; none from another session touches 086's new file (it does not exist). **Every changed file I did not touch is someone else's.**
- **Branches and worktrees (22 worktrees, `git worktree list`):** I diffed every local and remote branch against `origin/dev` for the five files above. The only branches ahead of dev that touch them are stale (Sept-Oct, e.g. `slice/attendance-approver-role` 31 Oct, `slice/066-attendance-decide` 23 Oct) or are release branches. **No live branch touches 086's files.** `slice/088-register-notice-and-forms` is 12 commits ahead of dev, all docs already on dev under other SHAs (diff: docs only, same content); the 089 worktree has no uncommitted changes; the 088 worktree has none. `release/2026-11-22` is the last release (main `f68f2333`).
- **Work board** `/Users/mac/hr-app/.claude/work-in-progress.md`: 7 rows, last updated 19 Nov. Row "084 employee own-day window" claims `attendance_correction.py` and `portal.js` (branch `slice/084-employee-window` at `fe93be35`, **not ahead of origin/dev**, so landed or abandoned). No row names 086, 087, 088 or 089 files. **The board is out of date; I could not tell from it who is working today.**
- **Other developers:** I cannot see them. **Surbhi, please say if anyone else is in `portal.js`, `punch_fix.py` or `attendance_correction.py` now.**
- **Plan:** sequence after you approve; own worktree; rebase on origin/dev before each commit; stage by path; one test run at a time on my own stack (the shared bench mounts the stale main checkout and cannot test a branch).
- **Local gates I will run before any hand-off** (from what 088 learned on 22 Nov): `scripts/check_app_integrity.py`, `check_portal_trays.js`, `check_design_system.py`, `check_portal_handlers.js`, `check_api_paths.py`, `check_brand_spelling.py`, and the 087, 088 and 085 suites. Not run today.

## 11 - Open decisions for Surbhi

| # | Decision | My recommendation | Blocks |
|---|---|---|---|
| **D-1** | F1: shut `_may_review()` inside `raise_for_report` as well as in the new call? (one line, and one 087 test changes) | **Both.** HR is not offered the button anyway | Whether ALV-425 closes fully |
| **D-2** | F2 guard: "only HR may change or delete a request filed for someone else" (covers the manager and the employee), not just "the filer" | Yes | Release |
| **D-3** | The "One of {n} days sent together" line: accept it *before* the "Raised by" line, or drop it | Accept the order | AC-36 wording |
| **D-4** | The manager's reason box must say "This reason is printed on the employee's monthly notice." (already in `acHeldForm`; not in prototype-v2) | Yes. Needs her yes because it is a difference from the approved prototype | The reason-box words |
| **D-5** | Drop the separate recheck call and reuse the list call (weaker than AC-38) | Yes, if she accepts "sent or fixed meanwhile" | AC-38, OPS-58 |
| **D-6** | A day the **employee** declined ("Not right") comes back on the manager's list. Is that wanted, or should it stay off until HR acts? | Back on the list (simplest, matches 087's override). HR sees the history | Edge case |
| **D-7** | ALV-426: treat as "covered by 088 plus the switch on at DTC and Grace", or does counsel need payslip lines? | Covered, and ask counsel one question | 086 release |
| **D-8** | Surbhi's earlier yes on P-1..P-7 stands. P-7 is already built (087), so only P-3, P-5, P-6 (new words) are still new text | Confirm | Screens |

## 12 - What I did not check

Not run: any test, bench, site or browser. Not read: `held_day.validate_missing_time` body (spec read it), `access.permitted_employee_filters`, the Employee `manager_scope` User Permission code (the comment in `raise_for_report` is my only source), Frappe's `db_query.py` beyond a grep for `for_update`, the old "Ask HR to fix" button on a Held day (F4, unchanged, not 086's), how `trRows` draws a row (the screen build reads it first), the DTC site's switch values, and counsel's own text. Written without using a bench.

## 13 - Strategy gate, 23 Nov 2026

Surbhi approved the strategy above with every recommendation ("approve, all recommendations"). Her answers, as given to the build:

| # | Decision | Answer | What the build does |
|---|---|---|---|
| D-1 | Close F1 (HR acts only on direct reports) | **Yes** | The `if not _may_review():` guard in `raise_for_report` is removed, so the direct-report check always runs, and the new call checks each row too. The 087 and 085 tests that pinned the old behaviour are updated |
| D-2 | Only HR may change or delete a request filed for someone else | **Yes** | Guard in `punch_fix.validate` (change to a confirmed-content field) and an `on_trash` hook on Attendance Request |
| D-3 | "One of n" stamp line | Joined with a blank line (`"\n\n"`) so it never enters the reason that 088 prints | A test proves the printed reason is only the manager's words (DevOps P1) |
| D-4 | Reason box says the reason is printed on the employee's monthly notice | **Yes** | `acHeldForm` wording reused |
| D-5 / OPS-65 | No separate recheck endpoint | **Yes** | After a lost answer the page calls the list again; a row no longer listed is "sent or fixed meanwhile" |
| D-6 | A day the employee declined comes back on the manager's list | **Yes** | "Open request" = `docstatus 0` and not Declined/Withdrawn |
| D-7 | ALV-426 | Covered by 088 plus its switch on; no payslip line | One test pins a 086 request reaching 088's notice data |
| D-8 | New words P-3, P-5, P-6 | **Yes**, as in the spec | |
| OPS-63 | Release order | 088 first (switch on at DTC and Grace), 086 in a separate release | Release step, not code |
| OPS-64 | Own switch | None; the existing hold switch | |
| OPS-66 | DTC-size throwaway stack for timing | **Yes**, at the test stage | Not built in this step |
