---
slice: 066-grooming-red-mark
artifact: 04-impact-and-strategy (change-process steps 1 and 2; the engineer's 00-impact-analysis for this slice)
author: hrms-fullstack-engineer
date: 2026-10-24
status: proposal - waiting for Surbhi's approval. Paper only. No feature code written, nothing committed, nothing pushed, no server or container touched.
inputs: 03-functional-spec.md (16 stories, 79 ACs, parity table P1-P52), 01c-security-privacy-requirements.md (SEC-1..12, PRIV-1..7), 02-design.md, 01-product-brief.md (to "Decisions 24 Oct 2026"), Surbhi's final decisions of 24 Oct 2026 as relayed by the lead session (listed in 0.1)
code read: origin/dev at eb33129b (worktree dev-integration-2026-10-24, read only): payroll_slip.py, payroll_month.py, payroll_rules_apply.py, attendance_correction.py (_subject, month, team_days, _punches_by_day), hr_api.py (manager notes), inbox_api.py, leave_rules.py (_send), hooks.py, the workings report, test_portal_security_010.py CEILINGS, test_pay_slip_marks_067.py; hrms/alvoraa_hr_core/access.py. Frappe v16.33.1 on hrlocal-bench (read only): desk/form/load.py, notification_log.py, comment.json, erpnext employee.json; hrms payroll_entry.py
measured: nothing. No DevOps inputs (07) exist for this slice. Every number below is worked out from code, not measured, and is marked so.
---

# 066 · Impact analysis and strategy: the grooming red mark

## 0 · Bad news first

1. **A manager note is not private, and that is true of every manager note in the product today,
   not only this one.** *(Verified in code, not by running it.)* Frappe's form loader
   (`frappe/desk/form/load.py`, `add_comments`, lines 139-173) reads **every** Comment on a record
   with `frappe.get_all` - no permission check - and returns `Info` comments as `info_logs` to
   anyone allowed to open that record. A manager note is an `Info` comment on the Employee. So the
   note's full text reaches:
   - every **HR Manager and HR User** who can open that Employee (the portal shows a note only to
     its author - the desk does not);
   - a **System Manager** (the owner, the CXO login);
   - **the employee the note is about**, through `frappe.desk.form.load.getdoc("Employee", <own id>)`:
     the `Employee` role has read on Employee (`employee.json`), and at DTC each login's User
     Permission on Employee is its own record.
   Three more faults in the same four functions (`hr_api.py:3562-3655`): any HR User may write a note
   on **any** employee in **any** company (no scope check); an edit overwrites the text with
   `frappe.db.set_value`, so no history; a delete goes through `frappe.delete_doc`, which keeps a full
   copy in Deleted Document for ever (counsel's no-soft-delete rule, 18 Sep).
   **So the review note will not be a manager note** (Surbhi's decision). It gets its own small
   record that only HR in scope can read (2.1, step 11). **I recommend a separate YouTrack ticket for
   the existing notes** - owner the security engineer - and I do not fix them in 066.

2. **The "bell" in this spec reaches the desk only. The portal has no list of notices.**
   *(Verified in code.)* `make_notification_logs` writes Notification Log rows, which show in the
   desk's bell. The portal's bell is `inbox_api.get_nav_counts` - counts of things to decide (leave,
   goal updates, attendance fixes). Nothing in `portal.js` or `www/` reads Notification Log. So an
   employee who uses only the portal never sees N1-N4, and HR never sees N5 ("asked") or N6 ("review
   pending") unless they open the desk. The employee still sees the mark on their Attendance month
   (US-6), and HR still has the saved view "Asked to look at, not yet answered" (US-16).
   At DTC this changes little today - 438 of 445 staff have no login at all - but the spec's
   "told the same day" rests on it. **Question 4.** My recommendation: build the Notification Log
   rows as specified (cheap, the same as slice 063's leave bells), and ask the designer to put HR's
   two notices into the Inbox in prototype v2, which is being drawn now.

3. **"The first mark the 3% cap stops" never happens as a button press.** The screen replaces the
   button with "has reached the most grooming reds the law allows" once the next mark would pass
   the limit (AC-47). Nobody can try, so nothing is "stopped". I read the decision as **"the moment
   the next mark would be stopped"**: the flag rises with the last mark the limit allows. Worked
   out from the marks, so nothing is written on a refusal (Question 2). Effect at DTC:

   | Person | Limit (3% of Basic) | Flag rises at |
   |---|---|---|
   | Junior, Basic ₹12,000 | ₹360 | 3rd mark (a 4th, ₹400, would pass it) |
   | Junior, Basic ₹15,000 | ₹450 | 4th mark (both rules at once) |
   | Senior, Basic ₹18,000 | ₹540 | 2nd mark |

   The literal reading (record a refused attempt) needs a button that is pressed and then refused,
   and a row written on a refusal path. It costs more and shows the manager a button that cannot work.

4. **The release must wait for the later steps.** Prototype v2 holds back US-10 (the 3% stop) and
   US-11 (the slip line and the back-stop). Without US-10, a mark past 3% could be made, and that is
   an unlawful fine once the rule set is on. So **steps 1-7 are built and tested locally, and nothing
   of 066 goes to `dev` until steps 8-11 are in.** The server halves of US-10 and US-11 do not depend
   on the prototype; if Surbhi wants, they can start before v2 arrives (Question 7).

5. **No `07-devops-inputs.md` for this slice**, so no OPS items to trace, and nobody has measured
   anything. The query counts below are worked out from the code I would write.

6. **Slice number 066 is used twice.** `066-attendance-decide` (ALV-attendance bug, now on
   `origin/dev`) owns containers `hrlocal-066` and `hrlocal-066-redis`. This slice will use
   `hrlocal-066g` with site `test066g`, and branch `slice/066-grooming-red-mark`.

### 0.1 · Decisions this plan treats as final (Surbhi, 24 Oct 2026, via the lead session)

| # | Decision | Where it lands |
|---|---|---|
| D1 | The flag rises at the 4th live mark in a calendar month, or at the first mark the 3% limit stops, whichever comes first. Once cleared it never returns in that month | Step 10 (with Question 2's reading) |
| D2 | A second 3% check at slip pricing (the back-stop) | Step 9 |
| D3 | HR also ticks "I have told them in person today" when the person has no login | Step 1 (R13 for both capacities) |
| D4 | "Unclean" is dropped. Reasons: Not in uniform · Uniform incomplete · No name badge · Wrong footwear | Step 1 |
| D5 | The review note is stored privately, not as a plain manager note | Step 11, new record |
| D6 | The employee sees only "Action agreed on {date}" | Step 11 |
| D7 | An owner who holds an HR role counts as HR | Step 1 (R6 reads roles, not "owner") |
| D8 | No Hindi in this slice | Strings wrapped with `_()` / `__()`, English only |
| D9 | Prototype v2 draws the flag, the review note and the limit-reached screens; US-10, US-11, US-14, US-15 come later | Steps 8-11 |

---

## 1 · Impact analysis

### 1.1 Parallel-work check

| Check | Result |
|---|---|
| `git fetch origin` | `origin/dev` at **eb33129b**. That is the base. It holds slice 067 (`ENGINE_LINES`, 3a74148d), 066-attendance-decide (6e826a6c..eb33129b) and ALV-210/211 (653521de) |
| Local `dev` in the main checkout | 10 commits **behind** `origin/dev` (ALV-199 at 2cbcc4b5). Not touched. Another session's uncommitted files are in the main checkout (`ux-learnings.md`, untracked slice docs, `mobile/field-app/*`) - **not mine, not touched** |
| This docs worktree (dev-integration-2026-10-22) | Holds untracked `docs/slices/066-grooming-red-mark/` and `067-pay-slip-marks/`. I add only this file |
| Work board | No 066-grooming row yet. `065-plan-a-replacement` (server side done, **not on dev**) adds a Comment / ToDo / DocShare / Tag Link / File `validate` guard in `hooks.py`. Nobody else has an open row on `payroll_slip.py`, `payroll_month.py` or the workings report |
| Other developers | I cannot see other machines. **Surbhi: is anyone else working in `payroll_slip.py`, `attendance_correction.py`, `hooks.py` or the Attendance screens of `portal.js`?** |

**Files 066 would change**

| File | New or changed | Hot? | Who else is in it | Plan |
|---|---|---|---|---|
| `alvoraa_portal/.../doctype/grooming_mark/` (json, py, `__init__`) | New | DocType JSON (one slice per DocType) | Nobody | Claim on the board |
| `alvoraa_portal/.../doctype/grooming_review/` (json, py, `__init__`) | New (step 11) | DocType JSON | Nobody | Claim on the board |
| `alvoraa_portal/alvoraa_portal/grooming.py` | New: `may_mark`, the read gate, the flag, the notices, the endpoints, the side-record guard | No | - | - |
| `alvoraa_portal/alvoraa_portal/hooks.py` | About 9 new lines: `doc_events` (Grooming Mark before_submit `refuse_own_submit`; Comment validate; Salary Slip before_submit), `has_permission` and `permission_query_conditions` (2 doctypes each) | Yes | 065 (Comment guard, not on dev) | **Split**: new lines at the end of each block. If 065 lands first, add the two doctypes to its guard list instead of a second function |
| `attendance_correction.py` | `month()` only: one call into `grooming.month_lines(...)` | Yes (busiest Attendance file) | 066-attendance-decide and ALV-211 are already on dev; no open row | One call at the end of `month()`; nothing else in the file changes. `team_days` is **not** touched - the Today card is its own endpoint |
| `payroll_month.py` | `MonthSummary` gains `grooming_days`, `grooming_deduction`, `grooming_capped`; `summarise_month` gains `grooming_days`, `grooming_rate`; `net` subtracts it (step 9) | No | 067 is on dev, no open row | - |
| `payroll_slip.py` | One `ENGINE_LINES` row; one count in `month_summary`; note wording; new `check_grooming_before_submit` (step 9) | 067's file | 067 is on dev | - |
| `report/salary_components_and_workings/*.py` | Two columns and the Why line (step 9) | No | - | - |
| `public/js/ess/portal.js` | Attendance month day box and the Whole team Today card: new `gm*` functions in their own block; one call from the month renderer and one from Whole team | Yes | ALV-199 / 060 screens on dev | Own block with its own prefix; no existing function rewritten |
| `tests/test_portal_security_010.py` | CEILINGS rows at the end | Yes | 063, 065 | Rows at the end |
| `tests/test_grooming_066.py` | New | No | - | - |
| Two saved Report Builder views (`report/` JSON as standard records) | New (step 7) | No | - | - |

**Not changed (on purpose):** `hr_api.py` (the review note no longer uses `save_manager_note`),
`manager_scope.py` (SEC-4: not in `SCOPED_DOCTYPES`), `inbox_api.py` (Question 4), `team_days`.

**Pin tests that keep existing features alive:** `test_pay_slip_marks_067.py` runs unchanged (it
checks the first two `ENGINE_LINES` rows and that every figure exists on `MonthSummary` - both still
true). `test_payroll_month.py`, `test_leave_063_engine.py`, `test_salary_report.py`,
`test_leave_063_card_cancel.py` and `test_attendance_correction.py` run unchanged. The new test file
names each feature it adds (one class per story), and "a normal comment on an Employee still saves"
pins the Comment guard.

### 1.2 Functional: cross-module reach

| App | Touched? | How |
|---|---|---|
| `alvoraa_portal` | **Yes** | Two new doctypes, one new module, `month()` (one call), payroll files (step 9), report, `portal.js`, `hooks.py` |
| `hrms` (our `alvoraa_hr_core`) | Read only | `permitted_employees`, `permitted_companies`, `permitted_branches`, `is_own_record`, `refuse`, `refuse_own_submit` reused unchanged |
| `hrms` (Frappe HR) | No edits | Salary Slip gets one `before_submit` hook. Payroll Entry catches a `ValidationError` per slip and carries on (`payroll_entry.py:1686-1690`), so one refused slip does not stop the batch |
| `erpnext` / `frappe` | No edits | Additional Salary, Salary Component, Notification Log, Comment, Report Builder reused. **Every Comment in the system** passes the new `validate` (one name comparison) |
| `alvoraa_goals` | **Must not be touched** | Has its own Comment hooks (`comment_query`, permission). Ours is `validate`, a different event. PRIV-5: appraisals and goals never read a mark (occurrence test) |
| `alvox_compensation` | No | - |

### 1.3 Functional: every caller of what I would change (grep on eb33129b)

| Function | Change | Callers | Effect on them |
|---|---|---|---|
| `payroll_slip.month_summary` | Adds one count of the person's submitted marks (only where a rule set exists) and passes two new inputs | `payroll_slip.on_salary_slip_validate`; the workings report (one call per employee); `leave_rules._card` (the Leave page card); `test_salary_report.py` (2), `test_leave_063_card_cancel.py` (1); `scripts/rehearsal_063.py`, `scripts/seed_rehearsal_063.py` | +1 query per call. With no marks, every existing figure is byte-for-byte the same; `net` drops only by a grooming figure. The Leave card does not show grooming |
| `payroll_month.summarise_month` | Two new keyword inputs, default 0 | `payroll_slip.month_summary`; `test_payroll_month.py`, `test_leave_063_engine.py` | Defaults keep every existing call identical |
| `payroll_slip.ENGINE_LINES` | One row added at the end | `push_marks_to_additional_salary`; `test_pay_slip_marks_067.py` (2 reads); `scripts/rehearsal_067.py` (3) | 067's test checks `owned[:2]` and that each figure exists - still passes. `rehearsal_067.py` loops the tuple: it will also check GRV; no change needed |
| `payroll_slip.push_marks_to_additional_salary` | Unchanged; loops one more line | `_apply_engine_lines` | GRV goes through the same savepoint: if it fails, red and green roll back too, with the existing note (wording widened) |
| `attendance_correction.month` | Adds a `grooming` key for permitted viewers only | `portal.js` (month screen); `test_attendance_correction.py` | No existing key changes. A viewer who fails the gate gets **no** `grooming` key (not empty) |
| `hr_api.save_manager_note` / `delete_manager_note` / `get_manager_notes` | **Not changed** (spec §5.2 rows withdrawn) | `portal.js` (9), `tests/portal_notes_test.js` (6) | None |

New functions, no existing callers: everything in `grooming.py`, the two controllers,
`payroll_slip.check_grooming_before_submit`.

### 1.4 Personas

| Persona | What changes |
|---|---|
| **CXO / owner (System Manager only)** | Nothing new: cannot mark, cannot read marks, flags or review notes. Sees the GRV total on slips and in the workings report, as with red marks today |
| **Owner holding HR Manager or HR User** | Treated as HR (D7). Because `permitted_employees` gives a System Manager everyone, such an owner is HR for **every** company |
| **HR Manager / HR User** | Marks any open day this month for people in scope (with the told-in-person tick when the person has no login); removes; keeps after an ask; reads every mark in scope; sees the flag and records the review; reads the review note. HR Manager exports the register |
| **Store manager** | The Today card on Whole team; marks direct reports today; undoes own mark until midnight; sees today's marks on reports and their own marks after; sees the flag on a report's month and "Action agreed on {date}", never the note or a ₹ figure |
| **Employee** | Sees own marks, who marked, why and the ₹ cost on the Attendance month; asks HR once per mark; sees the flag and "Action agreed on {date}"; never sees the note. Contract staff see nothing about grooming |
| **Skip-level manager, colleague** | Nothing, on any screen or API |

**HRMS domains:** attendance (the day, the punch), payroll (one new slip line, the submit check),
org structure (`reports_to` decides the manager). **Fenced off:** appraisals, PMS, goals, feedback,
org chart, directory, Attendance Insights, Team View counts.

### 1.5 Numbers (worked out from the code, not measured)

| Call | Queries added | Notes |
|---|---|---|
| Today card (`grooming.today`) | **~7, flat** for 5 or 400 reports | direct reports (1), punches today grouped (1), marks today (1), my count this month (1), rule set (cached doc, 1), the caller's employee (1), logins of the reports (1) |
| `month()` for a permitted viewer | **+3 to +5** | marks in the month (1), flag counts for this and last month (1 grouped), Basic for the limit (1), the review row dates (1), the rate (cached rule set) |
| `month()` for anyone else | **+1** | the gate check only |
| Mark / undo / remove / ask / keep | one whitelisted call, about 12-20 statements | one insert + submit, or one save, plus one Notification Log |
| Slip save (`month_summary`) | **+1** | one grouped count of distinct mark dates |
| Workings report | **+1 per employee** (DTC: +445) | the report already makes about 4 per employee; this keeps its shape. Measured at 445 in step 9; if it misses the 3 s budget, the counts come through the shared `ctx` in one grouped query |
| Slip submit check | **~6 per submit** | reuses `month_summary` (one definition of the price) instead of the spec's "≤ 2" second pricing path. Payroll Entry submits in the background |
| HR notices (N5, N6) | 1 per HR user (DTC: 7) | `permitted_employees` per HR user |
| Every Comment insert in the system | +0 queries | one doctype-name comparison |

### 1.6 The seven non-functional dimensions

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **degrades, slightly** | +1 query per slip and per Leave-card read; +3-5 on a permitted month view; +445 on the workings report at DTC (measured in step 9). Every Comment pays one name comparison. No N+1 on any screen |
| **Security** | **degrades, slightly, then guarded** | A new record holding a judgement about a person, writable by the `Employee` role. Guarded by one `may_mark` on every door (portal, REST insert, `frappe.client.submit`), its own read hooks (fail closed), no share, no comments, no delete, no import. **Zero new `ignore_permissions`.** Improves on the spec: the review note gets a record nobody but HR can read, instead of a desk-visible comment |
| **Reliability** | **neutral** | No job, no cache. The slip line goes through 067's savepoint. The submit check refuses with a `ValidationError`, which Payroll Entry handles per slip. Notices are wrapped so a failure never blocks a mark, and log the document name only |
| **Scalability** | **neutral** | Every screen query is flat in headcount. The read gate is one SQL condition with a sub-query, never a list of 445 names sent back as `IN (...)`. 13,795 rows a month is the worst case; tens in practice |
| **Maintainability** | **degrades** | Two new doctypes, one module of about 400 lines, ~9 hook lines, ~300 lines of screen code. Kept to one module and one `may_mark` |
| **Data integrity** | **neutral** | The flag and "live" are worked out on every read, never stored. Pay counts distinct dates. The slip cannot be submitted with a stale grooming figure. Removal is a cancel, so nothing is lost |
| **Compliance / privacy** | **degrades inside the system, by design** | Writes down a fine about a person and, at the flag, a free-text conversation note. Controls: least fields, fixed clothing-only reasons, tiny audience, cancel never delete, ids-only logs, a purpose fence, the 3% stop and back-stop. Open with counsel: wages definition, show cause, register form, retention of the note |

---

## 2 · The strategy

**Rung of the ladder: 5, a new DocType (two of them), plus rung 4 code and rung 2 configuration.**

- *Already there / configuration:* nothing in Frappe HR records a daily fine with a reason and a
  capacity. Attendance cannot carry it: today's Attendance does not exist until the shift ends,
  and DTC deletes and rebuilds Attendance (brief §9).
- *Custom field:* on Attendance, rejected above. On Employee, it is read on many screens and
  Employee keeps change history, so a note there could never be private.
- *The review note as a manager note (rung 4):* rejected - bad news 1.
- *The review note as a permission-level-1 field on the mark:* rejected. The mark keeps change
  history, and Frappe's form loader returns the last 10 Version rows with **no** field-level
  filter (`load.py:241-250`), so the subject would read the note through their own mark. The flag
  is also per month, not per mark.
- *The review note as a hidden comment type:* rejected - it relies on Frappe dropping an unknown
  comment type from the timeline, and every System Manager can read all Comments through REST.

So: `Grooming Mark` (one row per mark) and `Grooming Review` (one row per person per month, written
only when HR clears a flag). No new app, page, setting, role, job, cache or index.

### 2.1 Thin steps, in order. Each step stays green.

Each step is one commit (or two) with its tests, on `slice/066-grooming-red-mark` in
`.claude/worktrees/066-grooming-red-mark`, cut from `origin/dev` (eb33129b or later). Tests run in a
throwaway container `hrlocal-066g`, site `test066g`, never `hrlocal-bench`. Every guard is broken
once on purpose to prove its test can fail.

**Built now (no screen waits on prototype v2): steps 1-7.**

**Step 1 · The record and its rules (US-2, US-4, US-9, US-13 server; SEC-1, 2, 3, 6, 7, 8, 11; PRIV-1, 3).**
- DocType `Grooming Mark`, module Alvoraa Portal, the spec's §5.1 fields. `is_submittable` 1,
  `track_changes` 1, `autoname` hash, `allow_import` 0, `allow_rename` 0, `track_views` 0, no web
  view, no print format, nothing in global search. `employee` has `ignore_user_permissions` 1.
- `reason` options **equal** the constant `REASONS` in `grooming.py`: Not in uniform · Uniform
  incomplete · No name badge · Wrong footwear (D4).
- `grooming.may_mark(employee, date, user)` - the only definition - R1-R11 and R13. **R13 applies
  to both capacities** (D3): when the subject has no enabled login, `told_in_person` must be 1.
  R6: Manager when the caller's Active Employee is `reports_to`; else HR when the caller holds HR
  Manager or HR User, the subject is in `permitted_employees`, and the caller's linked Employee (if
  any) is Active. An owner with an HR role passes as HR (D7); System Manager alone does not.
  R12 (the 3% stop) is **not** in this step (step 8).
- Controller calls `may_mark` on `validate` and `before_submit`, sets `marked_as`, ignores any sent
  value. `refuse_own_submit` hung on `before_submit` through `hooks.py`.
- Comment guard: one `validate` on Comment refusing any row whose reference is a Grooming Mark (or,
  from step 11, a Grooming Review). If 065's guard is on dev first, add the two names to its list.
- DocPerms as spec §13 (Employee: create, read, write, submit, cancel - all narrowed; HR User and HR
  Manager the same plus report; HR Manager export; nobody delete, amend, share, email, print, import).
- Tests: AC-10, 10a, 10b, 13 (REST, both capacities), 39, 41-46, 76-79, SEC-6's three states, "a
  normal comment on an Employee still saves".

**Step 2 · One read gate (US-12; SEC-4, PRIV-5).**
- `has_permission` and `permission_query_conditions` for Grooming Mark in `hooks.py`, the same pair
  as Employee Checkin. Reader passes when: subject; `owner`; current Active direct manager and
  `mark_date` = today; or HR in scope. The list condition for HR is one sub-query on `tabEmployee`
  from `permitted_companies` / `permitted_branches`, values through `frappe.db.escape`. Anyone else:
  `1=0`.
- Tests: AC-68, 69, 70, 72, run as named users with **no** User Permission rows (DTC's shape).

**Step 3 · Removal and the two writes after submit (US-3, US-5, US-8 server; SEC-5, PRIV-3).**
- `before_cancel` (spec §7.3), `before_update_after_submit` (§7.4): only `asked_on` by the subject,
  `kept_by`/`kept_on` by HR in scope after an ask, `removal_reason` only during cancel. Month
  closed by a submitted slip refuses all of them.
- Tests: AC-20, 22, 22a, 28, 29, 35-38 (server half), SEC-5 (g) and (h).

**Step 4 · The notices (US-7, PRIV-2, PRIV-7).**
- N1-N5 built in code with `make_notification_logs`, as `leave_rules._send`; only to an enabled user
  whose Employee is Active; never to anyone else for N1-N4. Wrapped: a failure is logged by mark
  name only and never undoes the mark.
- Frappe also emails a Notification Log where the person's own settings allow (`after_insert`). N1-N4
  go only to the person they are about; N5 carries no reason. DTC has outgoing email muted and no
  Email Account. Stated, not changed.
- Tests: AC-21, 33, 33a; a forced failure leaves the mark saved and no name in the Error Log.

**Step 5 · The endpoints the screens call (US-1, US-6 server).**
- `grooming.today()` (the Today card, its own endpoint; `team_days` untouched),
  `grooming.mark`, `undo`, `remove`, `ask`, `keep` - each `@frappe.whitelist(methods=["POST"])`
  except `today`, each running as the user, each a thin call into insert/submit/cancel/save so the
  controller's rules apply.
- `month()` gets one call, `grooming.month_lines(subject, start, end)`, which returns the `grooming`
  key only for a viewer who passes the read gate, with no ₹ figure for a manager.
- Tests: AC-1-7, 18, 19, 2a, 30 (JSON has no ₹ for Ravi), 31, 32, 40, and query counts equal at 5
  and 400 reports.

**Step 6 · The screens from prototype v1 (US-1 to US-9 screens).** Built exactly as drawn (P1-P48,
P50, P52), with the two agreed differences: the reason list (D-1, now D4) and HR's no-login tick
(D-2, now D3). Own `gm*` block in `portal.js`. Browser checks: AC-8, 9, 11, 12, 14-17, 23-27, 71.

**Step 7 · HR views, the fence and the ceilings (US-16; SEC-12, PRIV-5, PRIV-6, PRIV-7).**
- Two saved Report Builder views as standard records (AC-66, 67).
- Occurrence test: `Grooming Mark` and `Grooming Review` appear only in their doctype folders,
  `grooming.py`, `attendance_correction.py`, `payroll_slip.py`, `hooks.py`, the workings report,
  the saved views, `portal.js` and tests. Broken once on purpose.
- CEILINGS rows (2.2). AC-73, 74, 75.

**Later, after prototype v2 lands (D9): steps 8-11.** None of these is pushed until all are done
(bad news 4).

**Step 8 · The 3% stop (US-10; SEC-10).** R12 in `may_mark`: (live marks this month + 1) × rate ≤
3% × `base` (latest submitted Salary Structure Assignment with `from_date` ≤ month end - the query
`month_summary` already uses). No assignment: refused. The "limit reached" row and box as v2 draws
them; the HR variant names the figures. Tests: AC-47, 48, 49.

**Step 9 · The slip line and the back-stop (US-11; SEC-9, SEC-10, D2).**
- `payroll_month`: `grooming_deduction` = min(days × rate, 3% × `earning_basic`); 0 when
  `earns_marks` is 0; `grooming_capped` set when the clamp bites; `net` subtracts it; the Why line.
- `payroll_slip.month_summary`: one grouped count of distinct submitted mark dates in the period,
  skipping dates the engine judged a full-day leave or absence. `ENGINE_LINES` gains
  `("Grooming Red Value", "grooming_deduction")`. Note wording "red, green and grooming lines".
- `check_grooming_before_submit` on Salary Slip (only where a rule set is on): re-run
  `month_summary`, compare with the slip's live GRV row, refuse with a `ValidationError`.
- Report columns and Why. Employee tile and box copy for the capped case as v2 draws it.
- Tests: AC-50-54; SEC-10 (a)-(c); Payroll Entry with one stale slip submits the rest; the report
  measured at 445 people (query count and bytes).

**Step 10 · The review flag (US-14; D1).**
- Worked out, never stored. For person P and calendar month M: **live** = distinct dates of
  submitted marks. **Pending** when live ≥ 1 **and** (live ≥ 4 **or** (live + 1) × rate > 3% ×
  `base`) **and** no Grooming Review exists for P and M. A review for P and M means cleared for
  good that month (D1). Removing a mark can lower a flag that has not been cleared.
- Carried over: this month and last month are checked (one grouped query). `[ASSUMPTION]` an
  uncleared flag older than last month stops showing; HR had its notice at the time (Question 6).
- N6 to HR in scope when a submit makes the flag pending (inside the mark's `on_submit`, same
  transaction, wrapped). N1's extra sentence as v2 words it (the 4th-mark wording does not fit a
  flag raised at the 2nd or 3rd mark).
- Visibility exactly as spec §7.6 (subject, marker in that month, current direct manager, HR in
  scope; nobody else). The count behind the flag is read with `frappe.get_all` (the manager cannot
  read all marks); only yes/no reaches the screen.
- Tests: AC-55-60 with D1's two triggers (Junior ₹12,000 flags at the 3rd mark; ₹15,000 at the
  4th; Senior ₹18,000 at the 2nd), and "cleared, then a 5th mark: no flag".

**Step 11 · The private review note (US-15; D5, D6).**
- DocType `Grooming Review`: `employee` (Link, `ignore_user_permissions` 1), `review_month` (Date,
  the 1st), `review_note` (Small Text, mandatory). Who and when: `owner` and `creation`. Not
  submittable. **`track_changes` 0** (so no Version row ever holds the text), `track_views` 0,
  `allow_import` 0, `allow_rename` 0, no web view, no print format, nothing in global search,
  `autoname` hash.
- DocPerms: HR Manager and HR User **create and read only**. Nobody writes, deletes, shares,
  exports, prints or emails. So the note is locked from the moment it is saved.
- Read gate: its own `has_permission` and `permission_query_conditions` - HR in scope who is not the
  subject. Owner with an HR role passes (D7); System Manager alone, manager, subject: nothing.
- Controller `validate`: caller is HR for the subject and not the subject; a flag is pending for that
  month; no review exists yet for that person and month; note not blank. Two HR users saving in
  the same second could both pass: the result is two true notes and a cleared flag - accepted
  (no unique index).
- `grooming.record_review(employee, month, note)` (POST): inserts as the user. Comment guard covers
  this doctype too.
- Everyone else who sees the flag gets only **"Action agreed on {date}"** (D6), from the review's
  `creation` date. It is read with `frappe.get_all(..., fields=["creation"])` - the note is never
  selected on that path.
- It does **not** appear in Team → Manager Notes (that list reads Comments). Question 3.
- Tests: rewritten AC-61-65: the note text is absent from `getdoc` on the Employee, on the mark, and
  from `/api/resource/Grooming Review` for the subject, the manager, a System Manager alone and an
  out-of-scope HR user; edit and delete refused for everyone; "Action agreed on" shows to the
  subject and the manager; flag gone for all readers; marks and slip figure unchanged.

### 2.2 The permission-bypass budget (`ignore_permissions`)

| File | Now | After 066 | CEILINGS row |
|---|---|---|---|
| `grooming.py` (new) | - | **0** | new, 0 |
| `doctype/grooming_mark/grooming_mark.py` (new) | - | **0** | new, 0 |
| `doctype/grooming_review/grooming_review.py` (new) | - | **0** | new, 0 |
| `payroll_slip.py` | 2 | **2** | **new row at 2** (it has none today; 01c SEC-12) |
| `payroll_month.py` | 0 | **0** | new row, 0 |
| workings report `.py` | 0 | **0** | new row, 0 |
| `attendance_correction.py` | 0 | **0** | unchanged |
| `hr_api.py` | 70 | **70** | unchanged (not touched) |

**Reads that do not use the caller's permission, named so the reviewer can check each:**

| Where | What it reads | Why the caller's own permission cannot be used |
|---|---|---|
| `payroll_slip.month_summary` | distinct mark dates of the slip's own employee | runs inside the slip save as whoever saves the slip |
| `grooming.month_lines` / `today` (flag) | count of live marks and the review's `creation` for **one subject**, after the read gate passed | a manager or the subject cannot read every mark or the review; only a yes/no and a date leave the server |
| `grooming.may_mark` | the subject's login, punches, leave, slips, existing marks | the rules need facts the caller may not read; nothing is returned but a refusal code |
| notices N5, N6 | the HR users whose scope includes the subject | the caller is not HR |

The mark is created, submitted, cancelled and updated as the user. The review is inserted as the
user. Notification Log rows are inserted by Frappe's own helper.

### 2.3 Tests per requirement

| Requirement | Test (AC) | Runs as |
|---|---|---|
| SEC-1 one `may_mark` | AC-10, 10b, 13, 45, 46; screen flag equals `may_mark` per fixture row | each named user, portal and REST |
| SEC-2 one a day | AC-10a, 53 | manager, HR |
| SEC-3 day rules, time zone | AC-27, 42-44, 46 (00:10 IST with a Berlin server clock) | manager, HR |
| SEC-4 read gate | AC-68-70, 72; skip-level `month()` has no key | each actor, no User Permission rows |
| SEC-5 removal | AC-20, 22, 22a, 28; subject cancel refused; DELETE refused | manager, HR, subject |
| SEC-6 rule set off | three company states × screen, endpoint, REST, slip | manager, HR |
| SEC-7 ₹0 refused | AC-41 | manager, HR |
| SEC-8 no free text on the mark | AC-76, 77 | manager, HR |
| SEC-9 slip agrees | AC-50-53 | HR |
| SEC-10 3% stop and back-stop | AC-47-50; SEC-10 (a)-(c) | manager, HR |
| SEC-11 fixed reasons | AC-78 | System Manager (Customize Form option refused) |
| SEC-12 no bypass, fence | AC-73, 74 | - |
| PRIV-1 least fields | AC-79 | - |
| PRIV-2 told | AC-12, 17, 21, 33, 33a | manager, HR |
| PRIV-3 cancel not delete | AC-28 (0 Deleted Document) | HR |
| PRIV-4 no purge | review check: no delete or purge code in the diff | - |
| PRIV-5 one purpose | AC-57, 73 | - |
| PRIV-6 HR views | AC-66, 67 | HR with a Branch permission |
| PRIV-7 logs | AC-75 | forced failures |
| D5/D6 private note | rewritten AC-61-65 | subject, manager, System Manager alone, HR out of scope |

### 2.4 Bench checks (own container `hrlocal-066g`, site `test066g`; never production)

| # | Check | What proves it |
|---|---|---|
| B-1 | `getdoc("Employee", <subject>)` as the subject, after a review is recorded | no review text anywhere in the reply (docinfo included) |
| B-2 | `getdoc("Grooming Mark", <name>)` as the subject | Version rows hold no review text (the review is a different record) |
| B-3 | Frappe's `validate` on Comment fires for `add_comment`'s insert | a comment on a mark is refused, 0 Comment rows |
| B-4 | Payroll Entry with one slip refused by the submit check | the other slips submit; the refused one stays draft with Frappe's own error |
| B-5 | `make_notification_logs` under a muted outgoing email | rows exist; no Email Queue row at DTC's settings |
| B-6 | Query counts | Today card at 5 and 400 reports; `month()` per viewer; the report at 445 |

---

## 3 · Risks, trade-offs, and what I would not build

### 3.1 Risks

| # | Risk | What I do about it |
|---|---|---|
| R-1 | Notices never seen by portal-only users (bad news 2) | Question 4; the Attendance month shows the mark either way |
| R-2 | A bug in the Comment guard blocks every comment in the system | One name comparison; pin test that a normal comment saves |
| R-3 | The slip submit check holds back a slip at month end | Its message says what to do ("Save it again"); Payroll Entry submits the rest (B-4) |
| R-4 | The workings report gets slower at 445 people | Measured in step 9; one grouped query through `ctx` only if it misses 3 s |
| R-5 | The flag reading in Question 2 is not what Surbhi meant | One line in the flag rule changes if she answers differently |
| R-6 | 065's Comment guard lands later and adds a second Comment `validate` | Either order works; whoever lands second merges the two lists into one function |
| R-7 | Prototype v2 changes the words or the place of the flag | Steps 10-11 wait for v2; the server rules do not depend on the drawing |
| R-8 | 063 SEC-17 (ALV-215) not done: a marked manager could change their own `dtc_grade` | Switch-on blocker, not a build blocker (spec §20) |

### 3.2 Rollback

- **Fast, no deploy:** disable the company's Payroll Rule Set. Marking stops at once on every door
  (SEC-6), screens hide the card and the day box, slips stop being priced by the engine.
- **Before reverting step 9's code** at a tenant that has priced slips: the engine-made GRV
  Additional Salary records for open months stay submitted, and Frappe keeps pulling them into
  draft slips even when the engine is off. HR (or one `bench execute`, on her word) cancels them
  first. This goes in the release note.
- **Code revert:** one `git revert` per step commit. Frappe does not drop the two tables; rows stay
  and are read by nothing. No data migration either way.

### 3.3 What is reused

`rule_set_for`, the rule set's `grade_field`, `category_field`, `mark_rates`, `earns_marks`;
`permitted_employees`, `permitted_companies`, `permitted_branches`, `is_own_record`, `refuse`,
`refuse_own_submit`; the Employee Checkin hook pair as the read-gate pattern; `leave_rules._send`'s
way of calling `make_notification_logs`; `ENGINE_LINES`, `_set_additional_salary`, the 067
savepoint and slip notes; `month_summary` (one price for slip, report, submit check and tile);
`_punches_by_day` for the Today card; Frappe submit, cancel and Version for the audit trail; Report
Builder and DocPerm export for the register.

### 3.4 What I would NOT build

- Any change to `save_manager_note` or the existing notes (separate ticket, bad news 1).
- A stored flag field, a flag job, or a "review pending" list page.
- An Inbox part, until v2 draws it (Question 4).
- A unique index on the review, or on marks (SEC-2 says none).
- A setting for the 3% figure, the reasons or the flag number.
- A bell when the flag clears, a review history, an action-plan list.
- Hindi strings (D8).
- Changes to `team_days`.

---

## 4 · Size and commit plan

**About 2,600 lines, a little over half of them tests. About 5-6 working days: ~3.5 for steps 1-7,
~2 for steps 8-11 once v2 lands.**

| # | Commit | Stories | Rough size |
|---|---|---|---|
| 1 | Grooming Mark record and `may_mark`; no comments on a mark | US-2, 4, 9, 13 (server) | 260 + 380 test |
| 2 | One read gate for marks | US-12 | 90 + 200 test |
| 3 | Undo, remove, ask and keep, with their rules | US-3, 5, 8 (server) | 110 + 220 test |
| 4 | Same-day notices built in code | US-7 | 70 + 100 test |
| 5 | Today card and month endpoints | US-1, 6 (server) | 150 + 180 test |
| 6 | Screens from prototype v1 | US-1-9 (screens) | 300 JS/CSS + 150 check |
| 7 | HR views, purpose fence, ceilings | US-16, US-12 | 40 + 80 test |
| 8 | The 3% stop (after v2) | US-10 | 30 + 70 test + screen state |
| 9 | Grooming line on the slip, back-stop, submit check, report (after v2) | US-11 | 90 + 220 test |
| 10 | Review flag (after v2) | US-14 | 80 + 160 test + screen line |
| 11 | Private review record and "Action agreed on" (after v2) | US-15 | 120 + 180 test + sheet |

---

## 5 · Questions for Surbhi before I build

1. **Approve the strategy**: two new records (`Grooming Mark`, `Grooming Review`), steps 1-7 now,
   8-11 after prototype v2, nothing to `dev` until step 11 is green. *My recommendation: yes.*
2. **"The first mark the 3% limit stops" = the moment the next mark would be stopped.** The flag
   rises with the last mark the limit allows (Junior on ₹12,000: the 3rd; Senior on ₹18,000: the
   2nd). *My recommendation: yes.* The literal reading needs a button that is pressed and refused.
3. **The review note will not appear in HR's Team → Manager Notes list**, because it is no longer
   a manager note. HR reads it on the person's month. *My recommendation: accept.*
4. **Notices show in the desk bell only.** Build them as specified now, and ask the designer to put
   "asked to look at this" and "review pending" into HR's portal Inbox in v2? *My recommendation:
   yes.* Without it, HR learns of asks from the saved view.
5. **Open a separate ticket for the existing manager notes** (readable by the subject, all HR and
   System Manager through the desk; HR can write on anyone; no edit history; delete keeps a copy).
   *My recommendation: yes, owner the security engineer, before staff logins are created at DTC.*
6. **An uncleared flag is carried into the next month only.** *My recommendation: yes;* older ones
   stop showing. Checking every past month needs each month's Basic and is not worth it.
7. **May the server halves of steps 8 and 9 start before v2 arrives?** They do not depend on the
   drawing. *My recommendation: yes,* screens still wait.
8. **The slip submit check re-runs the month's pricing (~6 queries) instead of a second, shorter
   calculation (≤ 2).** One definition of the price cannot drift. *My recommendation: yes.*

**Not for Surbhi, but needed:** the analyst updates the spec for D3 (AC-12/13/24), D4 (P8), the
review record (§5.2 hr_api rows, §7.6, AC-61-65, AC-73's file list) and the submit-check number in
§16; the security engineer re-checks the three after-submit fields and the review record at `06`;
DevOps writes `07` §3; the designer's v2 brief gains Question 4 and the flag sentence for a flag
raised before the 4th mark.

---

## Subtract pass

Removed on this pass:
- **The `save_manager_note` change and its lock** - the review is its own record, so `hr_api.py`
  is not touched at all.
- **Any write on a refused mark** - the "stopped" trigger is worked out (Question 2).
- **A Today-card change to `team_days`** - a small endpoint of its own touches no shared function.
- **A second, shorter pricing path for the submit check** - reuses `month_summary`.
- **A unique key on the review** - a same-second double note is harmless.
- **A `reviewed_by` / `reviewed_on` field** - `owner` and `creation` already hold them.
- **An Inbox part** - waits for v2.

Kept, and why: `Grooming Review` as a doctype (the only private place I found - bad news 1 and the
Version leak); the submit check (otherwise a stale slip is paid); the Comment guard (otherwise free
text reaches a mark); the occurrence test (otherwise an appraisal can start reading marks quietly).

## Assumptions

- `[ASSUMPTION]` "Wages" for the stop is the full monthly Basic (`base`); the back-stop uses
  `earning_basic`. Until counsel answers (Q-C1).
- `[ASSUMPTION]` Pay month = calendar month; "today" = site date (Asia/Kolkata).
- `[ASSUMPTION]` A mark later covered by approved leave counts toward the flag but is not charged.
- `[ASSUMPTION]` The subject can call `getdoc` on their own Employee at DTC - true by the shipped
  DocPerm and the per-doctype User Permission described in 01c; I did not run it.
- `[ASSUMPTION]` DTC's managers and HR do not rely on the desk bell today.
- `[ASSUMPTION]` Frappe 16.35 on DTC behaves as the local 16.33.1 in `load.py`,
  `notification_log.py` and `payroll_entry.py`.
