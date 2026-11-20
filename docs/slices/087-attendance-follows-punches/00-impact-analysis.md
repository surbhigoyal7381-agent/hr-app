---
slice: 087-attendance-follows-punches
artifact: 00-impact-analysis (impact analysis and strategy; no code written)
author: hrms-fullstack-engineer
date: 2026-11-20
risk tier: 1 (pay, who may add or set aside a punch, an audit record of a pay change). Build with the strong model; independent review and a separate security check afterwards (usage-discipline.md section 1).
status: waiting for Surbhi's approval. Nothing below is built.
---

# 087 Impact analysis and strategy

## 0 · Bad news first

1. **The agreed "change release_by_hr" is not enough.** `release_by_hr` is never reached for an ordinary-day fix, because two earlier checks in the same file stop the request first (`validate_missing_time`, `held_day.py:240-249`; `note_held_day`, `held_day.py:357-360`). The 085 session needs to agree to a wider, still small, list of edits in `held_day.py` (section 7.2). I propose to delete `release_by_hr` rather than patch it: after 087 every request that carries a time is a punch fix, so its old body can never run.
2. **Two lines in the spec cannot both be true.** AC-37 says the added punch has its `attendance` link set at insert. AC-43 says the approval refuses a punch that gets no `shift`. Stock `fetch_shift` sets the shift only `if not self.attendance` (`employee_checkin.py:92-121`, the `if not self.attendance` branch). So with the link set at insert, the shift is never set, and AC-43 would refuse every approval. Fix: insert without the link, then link the punch in the same transaction (the pattern `release_on_machine_punch` already uses, `held_day.py:393-420`). The effect for the job and the race test is the same (SEC-7). Spec wording changes; nothing else does.
3. **The two-PR split the spec recommends leaves dev broken between the PRs.** If "the one door" (US-9) lands alone, HR cannot approve any held-day request from the portal, the Inbox or the Desk until the screens land. See section 8 for the split I recommend instead.
4. **A manager who holds the submit right can approve a request today** (`decided_as` returns "Manager", `attendance_correction.py:1731`). SEC-3 makes punch fixes HR-only. That removes a route that works today for 085 held-day requests, and it leaves HR waiting two working days for a manager who can no longer decide (`not_yours_yet`, `attendance_correction.py:1783`). Needs Surbhi's word (section 10, D4).

## 1 · What I read, and what I did not

**Worktree** `/Users/mac/hr-app/.claude/worktrees/087-attendance-follows-punches`, branch `slice/087-attendance-follows-punches`, HEAD `f92f0347`, on `origin/dev` `72a046ec`. `git fetch origin` then `git rev-list --left-right --count HEAD...origin/dev` gave `1 0`: I am one commit ahead (the slice docs) and nothing has come in since. The only commit between the spec's base (`7de630df`) and now is `72a046ec` (ALV-396/399: `joiner_invite.py`, a joiner test, one line set in `test_portal_security_010.py`). None of it touches attendance. [proven]

**Read in full:** every file in the slice folder, including prototype-v2 as text (not opened in a browser, as the BA did). **Read in the code (this worktree):** `held_day.py` (170-460), `attendance_correction.py` (245-340, 1073-1300, 1579-1628, 1731-1870, 1893-2110, 2341-2478), `payroll_rules_apply.py` (355-395, 440-520), `punch_dedupe.py` (77-130, 150-279), `field_app_access.py` (286-360), `attendance_doors.py`, `hooks.py` (150-290, 720-775, 860-915), `inbox_api.py` (140-165, 802-880), `next-inbox.js` (55-110, 190-232), `portal.js` (6147-6160, 6571-6665 and every `acApi` call), `branch_geofence.py` (92-150), the vendored `attendance_request.py`, `employee_checkin.py`, `shift_type.py` (149-261), both DocType JSONs, `payroll_reprocess.preview`. **Read in a container (read-only, `docker exec ... cat/grep`):** Frappe `v16.33.1` `frappe/model/base_document.py` and the `hooks.py` of the six apps that bench has.

**Not checked:** (a) the `override_doctype_class` hooks of crm, frappe_whatsapp, payments, lms, telephony and helpdesk. The image has 12 apps (`deploy/Dockerfile` lines 169-263); the local benches have 6. (b) Any tenant's Custom DocPerm (does HR User hold create and write on Employee Checkin there?). (c) Any run: no test, no site. (d) `alv291_attendance_fix.py` beyond the grep lines in section 5.

## 2 · Which rung of the ladder

| Need | Rung | Why a cheaper rung was rejected |
|---|---|---|
| 8 new fields | Configuration: Custom Fields from one function | A new DocType or child table is dearer; the BA already rejected it |
| Insert a punch, set one aside, re-judge, write the day | New code (rung 4), one new module `punch_fix.py`, reusing `worked_out`, `_write_release`, `refresh_draft_slip` as they are | No Frappe setting does it. Stock only changes a status |
| Three stock blocks (overlap, "status unchanged", writes Present) | `override_doctype_class`, one small subclass | A `doc_events` hook cannot help: stock `validate` runs first and has already thrown. Editing the vendored file clashes on every rebase |
| The count report (AC-100) | Report in the same folder as the three existing Report Builder reports | See D5: Report Builder cannot say "has a time OR has a set-aside" |

New DocType: none. New app: none. New queue, job, schedule, cache, index: none. [Rung 5 and 6 never reached.]

### The subclass, checked

- **Nothing else overrides Attendance Request.** The hooks of the 6 apps in the local bench: `alvoraa_portal` overrides CRM Invitation only (`hooks.py:904`), `hrms` overrides Payment Entry and Project (`hrms/hooks.py:197`), `india_compliance` overrides Customize Form, and `erpnext` has `extend_doctype_class` for Address only. `frappe` and `alvoraa_goals` have none. [proven for 6 of 12 apps; the other 6 not checked]
- **v16 requires the subclass to inherit the stock class: proven.** `frappe/model/base_document.py:119-131` (v16.33.1): it takes `class_overrides[doctype][-1]` (the last app wins, silently) and throws "must be a subclass of ..." unless `issubclass(custom, stock)`. So `class AlvoraAttendanceRequest(AttendanceRequest)` importing from `hrms.hr.doctype.attendance_request.attendance_request` is the right shape. Same pattern as `overrides/crm_invitation.py`.
- **Because the last app wins silently, I add a pin test:** `frappe.get_hooks("override_doctype_class")["Attendance Request"]` equals exactly our one path, run in CI on a site with all 12 apps. That also closes the "not checked" for the six other apps.
- The three methods exist with these names in the vendored file: `validate_request_overlap` (109), `validate_no_attendance_to_create` (57), `create_attendance_records` (154). The subclass changes behaviour only when `punch_fix.is_punch_fix(self)`; otherwise it calls `super()`.

## 3 · Callers, counted

| Function I change | Callers found (non-test) | Tests that mention it | Change |
|---|---|---|---|
| `payroll_rules_apply._punches` | 7 call sites in 4 files: `payroll_rules_apply.py:468` (judge), `:587` (attendance_onload), `held_day.py:264`, `:407`, `leave_rules.py:466`, `:487`, `daily_attendance_workings.py:111`. (`field_app_records._punches` and `attendance_correction._punches_by_day` are different functions.) | 21 files mention `_punches`; some are other functions | One filter: skip rows with `alvoraa_fix_aside_request` set. Guarded on the column existing (section 4.4) |
| `payroll_rules_apply.judge` | 7 call sites in 5 files: `payroll_slip.py:118`, `payroll_rules_apply.py:556`, `:608`, `payroll_reprocess.py:143`, `:209`, `alv291_attendance_fix.py:1164`, `daily_attendance_workings.py:139` | 22 files mention `judge(` or `_punches` | **No change** to `judge`. It reads `_punches`, so all 7 inherit the filter. The Salary Workings report reaches it through `payroll_slip.month_summary` (`payroll_slip.py:118`) [proven by import and call, the 01c "not checked" row is now answered] |
| `held_day.worked_out` | 3: `held_day.py:327` (preview), `:387` (release_by_hr), `:413` (machine release) | 3 files | New optional `aside` argument (punch names to leave out). Default keeps all three callers as they are |
| `held_day.preview` | 1: `attendance_correction.py:1924` (`to_review`) | 1 | Takes the set-aside list; returns the data the card needs |
| `held_day.release_by_hr` | 1: `hooks.py:222` | `test_held_day_085.py` (2 mentions) | Deleted (section 7.2) |
| `held_day.note_held_day`, `validate_missing_time`, `enforce_monthly_limit` | `hooks.py:242`, `:229`, `:233` | `test_held_day_085.py` (6 mentions of a missing time), `test_held_slip_085.py` (1) | Section 7.2 |
| `attendance_correction.decide` | **0 Python callers.** 2 client call sites: `portal.js:6644` (`acDecide`), `next-inbox.js:65` (the `ACTIONS` map) | 25 test files mention `decide`; not all call it | New optional `seen=None`. Existing callers keep working |
| `attendance_correction.to_review` | 1 client: `portal.js:6575`. The Inbox does not call it (`inbox_api.py:149` says so) | 4 | Adds `seen` and the punch-fix info per row |
| `attendance_correction.raise_correction`, `raise_for_report`, `withdraw`, `team_days` | JS: `portal.js:6384`, `:6499`, `next-time.js:36` (raise_correction); `portal.js:6383`, `:6494`, `:15915` (raise_for_report); `portal.js:6549`, `next-inbox.js:81` (withdraw); `portal.js:15660` (team_days) | 4, 2, 2, 4 | **No change by me.** `methods=["POST"]` on the first four is ALV-411 (section 9) |
| `punch_dedupe` (`skip_repeat_scan`, `earlier_kept_punch`) | `hooks.py:276` only | `test_punch_dedupe_alv337.py` | **No change.** I read it. Two facts it forces on me are in section 4.3 |
| `attendance_correction.month` (own-day reader, `:559-575`) and `_punches_by_day` (`:2089`) | `portal.js:5623`, `:15313`; `team_days` | | Show the mark; the break counts 2 (spec AC-58) |

## 4 · Mechanism, and four traps the spec did not name

### 4.1 One approval, in order
`decide` (as the approver, never `ignore_permissions`): lock the request and the day's Attendance with `get_doc(..., for_update=True)`; re-run every guard; compute `expected = worked_out(row, extra=added, aside=ticked)`; check `seen`; set the document flag; `doc.submit()`. In `on_submit` (our hook, after stock's): **set the ticked punches aside first, then insert the added punch**, then link it to the day, then `actual = worked_out(row)` from the real punches, **assert `actual == expected`** (this is the "preview equals result" proof, AC-29, and the engine agreement, AC-54), `_write_release`, write `alvoraa_fix_before/after`, refresh the draft slip (own savepoint, as today). Any exception rolls the whole request back (AC-56). [proven that Frappe wraps one request in one transaction; each `refresh_draft_slip` keeps its own savepoint, `held_day.py:432`]

`flags` cannot be sent by a client: `RESERVED_KEYWORDS` includes `"flags"` (`base_document.py:1601`, v16.33.1), so a JSON body cannot set the flag the one-door check depends on. [proven]

### 4.2 Trap 1: link at insert vs shift. See section 0, point 2.

### 4.3 Trap 2: the dedupe hook and the order of writes
`skip_repeat_scan` (before_insert) flags a new punch if a **kept** punch lies in the 2 minutes **before** it. It does not look forward. And a kept punch is one with `skip_auto_attendance = 0`. So: (a) if the approval inserted first and set aside second, an added 11:16 next to a still-kept 11:15 would be stored but not counted (the exact thing AC-40 forbids). Set-aside first removes the anchor. (b) The raise-time and approval-time "within 2 minutes" check must ignore the punches ticked in the same request, and must look both ways. (c) After the insert, assert `skip_auto_attendance == 0`, else roll back (already AC-40).

### 4.4 Trap 3: a deploy before the migrate
`_punches` runs on every day judged, every payslip and every attendance save. If the image starts and the column `alvoraa_fix_aside_request` does not exist yet, every one of those fails with "Unknown column". The migrate can stop part way (5 Nov 2026, memory). So the filter is guarded with `frappe.db.has_column(...)`, exactly as `_decided_as_is_storable` does for `alvoraa_decided_as` (`attendance_correction.py:1764`). Without the column: no filter, identical to today.

### 4.5 Trap 4: `time` is permlevel 1
A role without write at permlevel 1 gets `time` silently replaced by "Now" on insert. Stock JSON gives HR User, HR Manager, System Manager that right [proven, `employee_checkin.json`]; a tenant's Custom DocPerm could differ [not checked]. The approval therefore asserts the stored time equals the typed time and rolls back with a plain sentence if not.

### 4.6 Other design points
- **Raise-time checks live on the document** (`validate`), not in the new endpoint, so `raise_correction`, the Desk and REST are bound too. After 087, `raise_correction` with `missing_time` on an ordinary day would otherwise reach the document with no guard.
- **`alvoraa_for_held_day` is computed by the server on a new document, always overwritten, and reset to the stored value on an edit.** A client posting `1` must not dodge the limit.
- **`refuse_own_day_outside_window`** (`attendance_correction.py:1594`) returns early on any time. That is how a time escapes the window today. AC-74 keys it on `alvoraa_for_held_day` instead.
- **SEC-3 on the document**: use `access.employee_in_scope` (`access.py:334`, company and branch, fails closed). `refuse_outside_company` (`attendance_doors.py:47`) checks the company only and is kept.
- **`hand`-marked guard (Q10)** is built last and proved on ppj.dev first. Frappe's "Process Attendance" button also runs as a named user, but still sets `in_time`, so the rule holds. [inferred]

## 5. Reach

**alvoraa_portal:** almost everything. **hrms (vendored):** no file edited. Reached through Custom Fields, hooks, one subclass. `attendance_request.py` (3 methods overridden), `employee_checkin.py` (validate, fetch_shift, validate_time_change run on our insert), `shift_type.py` `get_employee_checkins` (filters `attendance is not set`, `skip_auto_attendance = 0`: the job takes neither a linked nor a set-aside punch [proven, lines 255-261]). **erpnext:** Employee read. **alvoraa_goals:** 0 files mention Employee Checkin, Attendance Request or skip_auto_attendance (grep). **grace_compensation / alvox_compensation:** no such code in this tree (grep returned nothing).

**Punch readers (SEC-8), all 20 files that mention Employee Checkin were listed;** the ones that turn punches into pay or a pay figure: `_punches` (and through it `judge`: payslips, the daily workings, Salary Workings, reprocess, ALV-291 verdicts, leave rules at `leave_rules.py:466/487`); `_day_logs` (already filters `skip_auto_attendance`); month view `attendance_correction.py:559-575`; `attendance_analytics.py:653-659`; team days `:2089`; grooming `grooming.py:332-337`. Not pay: `hr_api.py` and `home_api.py` today's status; `field_app_records.py`. **One reader the spec did not list:** `alv291_attendance_fix.py` reads and clears `skip_auto_attendance` in 20 places (e.g. `:367-377`, `:460-477`, `:574`). Its "free the punches" step clears that flag with `db.set_value`, which would reinstate a set-aside punch in Frappe's eyes. ALV-291 has not yet run at DTC (memory, 4 Nov), so nothing is set aside yet. See D6.

## 6 · Personas and HRMS domains

| Persona | Changes |
|---|---|
| Employee | Taps a gap, sends one punch (and ticks a wrong one). Sees Waiting, Fixed, Declined and the marks on their own day. Cannot approve; cannot read a colleague's request or punch |
| HR User / HR Manager | One card with Now and If approved; decides only through it; never their own day; only their companies and branches; HR with no company or branch sees nobody |
| Line manager | Sees the words "Added by HR" / "Set aside", never the note, HR's note or the approver. **Loses approval of punch fixes** (D4). Keeps 085's `raise_for_report` on a Held day |
| CXO (System Manager) | May approve in every company, not their own day. No new screen. Administrator is the one logged exception for marked punches |
| Payroll | Pay follows the real counted punches. A set-aside punch no longer counts anywhere pay is read |

**Domains:** attendance (the day), payroll (engine verdict, draft slip refresh, final-slip guard), leaves (approved or half-day leave blocks a fix), org structure (company and branch scope). Appraisals: none.

## 7 · Approach, file by file

### 7.1 New
| File | What | Rung |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/punch_fix.py` | `FIELDS` (8 Custom Fields) and `after_migrate`; `is_punch_fix`; `day_state` (the one function that says fixable or blocked: `slip`, `leave`, `hand`, `unmarked`, `left`); `kind_for` and the added-time helper (night shift); the document `validate` (raise guards); `before_submit` (SEC-1, SEC-3); `apply` (the on_submit writer); Employee Checkin `guard_marks` (validate, on_trash); `refuse_cancel`; the employee `send` endpoint (POST) | new code |
| `alvoraa_portal/alvoraa_portal/overrides/attendance_request.py` | The subclass, three methods | new code |
| `alvoraa_portal/alvoraa_portal/patches/...` and `patches.txt` | One patch: `alvoraa_for_held_day = 1` on existing requests that carry `alvoraa_missing_log` (AC-92). Batched if over 500 rows | new code |
| a report folder beside the existing three | AC-100 (D5) | configuration |
| `scripts/087_dry_run.py` | The AC-59 dry run: counts and Attendance ids only, no names, no times | throw-away script |

### 7.2 Edited, with the exact change
**`held_day.py` (085's file).** The agreed part: `release_by_hr` (`:380-391`). **I would delete it**, with its hook line, because its only live path (a Held day with a time) is now handled by `punch_fix.apply`, and the `extra` argument it passes at `:387` is the ALV-410 fault (the typed time is counted but no real punch exists, so the engine still sees an odd count and holds the day). Its two useful calls, `_write_release` and `refresh_draft_slip`, stay and are called from `apply`. **The part that was not agreed, and is needed:**
1. `validate_missing_time` (`:240`): drop the "day must be Held" condition; keep the In/Out check. The day-state rules move to `punch_fix.validate`.
2. `enforce_monthly_limit` (`:194`, `:227`): replace the `_has_time(doc)` early return and the `alvoraa_missing_log is not set` count filter with `alvoraa_for_held_day` (Q2, decided).
3. `note_held_day` (`:353`): return at once for a punch fix; delete the now unreachable "no longer held" branch (`:357-360`). The multi-day guard (F3) stays.
4. `worked_out` (`:287`): add `aside=()`. `preview` (`:320`): pass it; return the card's data.
Nothing else in `held_day.py` moves: `release_on_machine_punch`, `refresh_draft_slip`, `_write_release`, the hold, `after_migrate`.

**`payroll_rules_apply.py`**: `_punches` (`:378`), one guarded filter. **`attendance_correction.py`**: `decide` (new `seen`, HR-role check for a punch fix, `for_update`); `to_review` (per-row `seen` and the card data); `month` (the day's marks and the blocked code, bounded: one slip read, one leave read per month); `refuse_own_day_outside_window` (key on `alvoraa_for_held_day`); `not_yours_yet` (D4); `_punches_by_day` and grooming (AC-58, Q13). **`hooks.py`** (hot file, 7 spots): `override_doctype_class`; Attendance Request `before_submit` (+1), `before_cancel` (string to list), `on_submit` (drop `release_by_hr`, add `apply`); Employee Checkin `validate` (string to list) and `on_trash`; `after_migrate` and `after_install` (+1 each). **`inbox_api.py`**: add `alvoraa_missing_time` and `alvoraa_set_aside` to the read, one `punch_fix` flag to the row and to the key list at `:151` (flag only, no times, no note). **`next-inbox.js`**: a punch-fix row draws **Review** (opens the card) in place of Approve/Decline. **`portal.js`** (1,297,945 bytes today, `acDetail` at `:6147`): the day sheet, strip, send bar and the HR card replace `acHeldBox/acHeldForm` (`:6318-6375`) and `acHeldHrLines` (`:6618`); `acDecide` (`:6637`) sends `seen`. `attendance_analytics.py` (`:653`): honour the set-aside. **Tests:** update `test_held_day_085.py` and `test_held_slip_085.py` (they approve a held-day request with no `seen`); new tests named in section 11.

**Not touched:** `field_app_access.py` (the F1/R4 punch checks are the second lock and stay as they are), `punch_dedupe.py`, `deploy/nginx.conf` (AC-88 asserts it), `hr_api.py`, `home_api.py`, any vendored `hrms` file.

## 8 · Order of work: I change the split

The spec recommends PR 1 = US-8 + US-9, PR 2 = the rest. **Problem:** US-9 closes the old door (`decide` with no `seen`, Desk Submit, Inbox Approve) before the new card exists. Between the PRs, HR cannot approve a held-day request from anywhere, and the old `acDecide` and Inbox cannot send `seen`.

**Proposal: still two pushes to dev, drawn differently.**
- **PR 1, the whole server side plus two small edits to the old screens:** the 8 fields and patch (US-15); engine reads (US-8); the approval, ALV-410 fixed (US-6, US-7); the one door (US-9); scope and own-day (US-10); the closed marks (US-12); exactly once (US-13); raise guards, the send endpoint and the blocked-day rule (US-11, US-4 server part); the subclass (US-17 server part). Plus: `acDecide` and `to_review` carry `seen`; the Inbox row shows Review. Nothing regresses; HR keeps approving, with the old screen.
- **PR 2, the screens:** the day sheet, strip, send bar, HR card, accessibility, phone checks (US-1 to US-5 screens, US-16, the screen parts of US-14).
- **Inside PR 1, the order of commits is the review order:** (1) fields + `_punches` filter + dry run, **run and read before anything else is built** (kill criterion 1; if one day moves, stop); (2) the door and scope (the closed doors, each test seen to fail first); (3) the approval and ALV-410; (4) raise guards. Each commit is green on its own.
- Size: PR 1 is about 40 of the 64 points. It is large for one review; the commit order above is how a reviewer reads it in parts. Splitting PR 1 in two pushes would, by the 10 Sep lesson, risk cancelled deploys, so I do not recommend it.

## 9 · Coordination

### ALV-411 and ALV-412 (`slice/alv411-412-security`, commits `dc671775`, `15eaad63`)
Read: the branch is based on `7de630df`, two commits behind dev. Its **own** diff is 3 files: `attendance_correction.py` (4 one-line decorator changes: `raise_correction`, `withdraw`, `decide`, `raise_for_report` become `methods=["POST"]`), `field_app_access.py` (`checkin_query_conditions`, a new `_hr_read_sql`, and the read rights in `checkin_has_permission`) and a new test. (A `git diff` against current dev also shows the joiner files; that is only the two commits it lacks.)
- **Overlap is small.** My edits in `attendance_correction.py` are inside the `decide` body and its `def` line, which is the line directly under the decorator it changes: git will report a conflict there even though the intentions agree. In `field_app_access.py` I make **no edit**.
- **How the two work together.** The approval inserts and saves punches as the approver. ALV-412 leaves HR's create, write and delete exactly as they are (it scopes only read, select, print, export and share), so the insert and the set-aside are unaffected. The card reads punches through `get_all` inside `worked_out`, which ignores row rules; the month view uses `get_list`, so after 412 HR sees only in-scope punches there, which is what we want. [read in the diff; not run]
- **Recommendation: land 411/412 on dev first** (Surbhi's word to push; it is small, tested and Tier 1). Then I rebase 087 on it and keep the decorator lines. If she prefers 087 first, I do not copy the four decorators (that guarantees the same conflict); I add `methods=["POST"]` on my **new** endpoints only, and AC-64 for the four old ones is ticked by 411. Either way AC-64 needs one run after both are on the same branch.
- 087 does not use the branch's tests. Both touch `test_portal_security_010.py` ceilings only if someone adds an `ignore_permissions`; I add none (AC-88).

### Slice 085's session (`held_day.py`)
They agreed to `release_by_hr` only. Exact list in section 7.2: delete `release_by_hr` and its hook; `validate_missing_time`, `enforce_monthly_limit`, `note_held_day`, `worked_out` and `preview` change as listed; nothing else. **This is wider than what was agreed.** I will not start those edits until that session (or Surbhi) confirms the list. 085 is not on `.claude/work-in-progress.md`, so I cannot see what it holds uncommitted. The board's rows for 084 (`attendance_correction.py`, `portal.js`, `hooks.py`) and ALV-326 (`_punches`, `judge`) say "not pushed", but their code is already in my tree, so those rows are stale. [proven by finding the code]

## 10 · Decisions for Surbhi

| # | Decision | My recommendation |
|---|---|---|
| D1 | The PR split in section 8 | Take the server-first split |
| D2 | Wider `held_day.py` edits and deleting `release_by_hr` (section 7.2) | Yes; ask the 085 session to confirm |
| D3 | Land ALV-411/412 on dev before 087's PR 1 | Yes |
| D4 | Punch fixes become HR-only to approve (a manager with the submit right loses the route 085 gave them), and HR no longer waits two days for the manager on a punch fix | Yes to both. SEC-3 already says it; the wait is the unlisted consequence |
| D5 | AC-100 as a small Script Report, not Report Builder (Report Builder filters are all "and", [inferred, to confirm on the bench]; "Forgot to Punch In/Out" are also ordinary reasons, `attendance_correction.py:91`, so the reason cannot identify a punch fix) | Script Report. Same folder as the three existing reports |
| D6 | `alv291_attendance_fix.py` clears the skip flag on set-aside punches | A one-line guard in 291 before it next runs after any fix exists. Ticket it; I do not fix what the slice did not ask |
| D7 | Spec amendment: the added punch is linked to the day in the same transaction, not at insert (section 0, point 2) | Amend AC-37; AC-43 stands |

## 11 · How each requirement is met

| Item | Mechanism (and the test that must be seen to fail first) |
|---|---|
| SEC-1 one door, what HR saw | `before_submit` refuses a punch fix unless `decide` set a flag clients cannot send; `seen` = request `modified` + punch ids, preview recomputed inside the approval. Fail first: remove the check, the Desk-submit test goes green |
| SEC-2 POST only | New endpoints get `methods=["POST"]`; the four old ones are ALV-411 (D3) |
| SEC-3 HR in scope, not own day | `before_submit`: HR role + `employee_in_scope` + `refuse_own_decision` + `refuse_raiser_submit`; insert as approver with no `ignore_permissions`, so `checkin_has_permission` F1/R4 is the second lock. Fail first: neuter `refuse_own_decision`, the insert still refuses |
| SEC-4 own day, gates | `validate` on the document; `alvoraa_for_held_day` server-set. Fail first: restore the `_has_time` early return, the 4th request passes |
| SEC-5 unfixable days | `day_state`, at raise and again at approval; one test per guard |
| SEC-6 marks only by approval | Employee Checkin `validate` and `on_trash` check a document flag; Administrator exempt and logged |
| SEC-7 exactly once | `for_update`; link in the same transaction; no second release (`release_on_machine_punch` exits for non-machine owners, `held_day.py:400`); cancel refused; one transaction |
| SEC-8 one list for pay | one `_punches` filter, reading only the new field; dry run |
| PRIV-1 to PRIV-4 | Payload is date, time, set-aside names, note; no new reader (no `get_list` widening); no photo or GPS key in any 087 response; ids-only logs; no `frappe.cache`; no `allow_guest`; the dry run prints counts and Attendance ids |
| OPS-R1 | Inline; slip refresh moves to `short` only if one save measures over about 2 s |
| OPS-R2 | One open fix per employee-day (the document check). **The daily cap is dropped (Surbhi, 20 Nov).** |
| OPS-R6 | Race test with Frappe's `process_auto_attendance`, both orders |
| OPS-R8 | `scripts/087_dry_run.py`, on ppj.dev and a fresh CI site. **Honest note:** with the field set on no row the filter is the identity by construction, so this is a belt check; the real proof is the ALV-410 test going red when the filter is removed |
| OPS-R9, R11, R12 | Release plan: exact previous tag, asset-version bump, rollback by a new request (never delete a punch), sites migrated counted against sites that exist |
| OPS-R10 / AC-100 | The report, D5 |

## 12 · Verdict on the seven dimensions (change as proposed, before building)

| Dimension | Verdict | One line |
|---|---|---|
| Performance | neutral | `_punches` gains one predicate on an already filtered query; no new query per day. An approval is about one request: estimate 40 to 60 queries plus one slip save, **to be measured**. `to_review` with 50 cards: target 1.5 s, measured at build |
| Security | improves | Closes the blind-approve door (Inbox, Desk, GET) and adds two locks on own-day approval. New surface: one send endpoint (own record only, POST) and an insert as the approver |
| Reliability | improves, with a trap | One transaction and a fail-closed check replace today's "Present but still held". Trap: the pre-migrate column (4.4) |
| Scalability | neutral | One day, one employee, inline. No burst, no job |
| Maintainability | degrades slightly | One new module and one subclass; it deletes `release_by_hr`. Hot-file edits to `hooks.py`, `portal.js` |
| Data integrity | improves | Day, punches and pay agree; before/after on the request; marked punches cannot be edited or deleted. Risk: ALV-291 (D6) |
| Compliance / privacy | improves, with a gate | Every change has a named human and a before/after; no wider view. The release to main waits for counsel (Q1) |

## 13 · Subtract pass

Kept out: a cache, a job, a queue, a daily cap, a per-company switch, a "seen" token other than `modified` + punch ids, a Hindi bundle, a backfill, a notification. **Removed from the plan:** `release_by_hr` (dead after 087). **Considered and kept:** the fail-closed `actual == expected` assertion (it costs one comparison and is the whole proof of AC-29 and AC-54); `alvoraa_fix_aside_by` and `_on` (an update has no owner).

## 14 · Assumptions

- `[ASSUMPTION]` Report Builder cannot express "or" (D5).
- `[ASSUMPTION]` "Other" is accepted as a reason with an empty explanation (spec 4.2).
- `[ASSUMPTION]` Frappe's "Process Attendance" button leaves `in_time` set, so the hand-marked rule (Q10) holds. Proved on ppj.dev before AC-25 is written.
- `[ASSUMPTION]` HR User holds create and write on Employee Checkin on every tenant (4.5).
- `[ASSUMPTION]` Tens of fixes a month per company (spec 9), so inline is enough.
- Do not touch the ppj.dev rows with `device_id alv085-test`.

---

## Conditions from the slice 085 session (20 Nov 2026), on the held_day.py changes

1. **Deleting `release_by_hr` is acceptable only if the new path keeps everything it does:**
   - the release fields `alvoraa_release_how` / `_by` / `_on` through `_write_release` (the only record of who released, PRIV-3/SEC-7), which the employee's "Held, now X. Pay restored." box reads (attendance_correction.py ~1010-1016, portal.js ~6339-6346);
   - `refresh_draft_slip` (AC-16), and no change to an Attendance inside a submitted slip (AC-18, Q4);
   - the status from the shift thresholds through `worked_out` (Q3);
   - the `note_held_day` refusals: no longer held, a multi-day request covering a held day (F3), no shift or no time;
   - an approver's punch never triggers `release_on_machine_punch` (keep a test);
   - the F1/R4 punch checks, with no new `ignore_permissions` (test_portal_security_010 counts them);
   - update test_held_day_085, test_held_slip_085 and test_held_p1_machine_accounts_085 to the new path with the same intent. Never delete them.
2. **Times on ordinary days are fine.** Keep PRIV-2 for held days: the held-day form sends date, time and In/Out only, with no reason box (AC-28, plus a JS test).
3. **`alvoraa_for_held_day`:**
   - (a) the server sets it at insert, from whether a Held Attendance exists for that employee and date. Never take it from the client.
   - (b) existing requests (missing log set, no flag) are backfilled or read as held. Keep the `_filed_by_hr` exemption.
4. **Keep `worked_out`'s night-shift handling.**
5. **D4 (HR-only approval)** matches Surbhi's rule. Only managers with a Desk submit right lose a route.
6. **ALV-404** lives in `hold_odd_punch_day` (a lone OUT on a log-type shift becomes Absent). Leave it unless asked.
7. **ppj.dev 19 Nov rows (device alv085-test) are in use by testers. Do not touch them.**

## Strategy gate — Surbhi's decision, 21 Nov 2026

**Approved**, together with D1–D7 as recommended:

- D1: two pushes.
- D2: replace 085's `release_by_hr`, keeping everything it does.
- D3: ALV-411/412 land first.
- D4: punch fixes are approved by HR only.
- D5: AC-100 is a small Script Report.
- D6: the ALV-291 guard gets its own ticket.
- D7: AC-37 is amended so the punch is linked after insert.

The 085 session confirmed her approval of the held_day.py changes on the same day, with eight conditions (see the 085-session notes above). Before main, count the HR approvers on each tenant.

This approves the **local build only**. Pushing to dev needs her separate word.
