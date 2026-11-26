---
slice: 088-register-notice-and-forms (the follow-on: "088c", Surbhi names it)
artifact: 00b-notice-scope-analysis (change-process steps 1 and 2 only; no code written)
author: hrms-fullstack-engineer
date: 2026-11-25
risk tier: 1 (personal data, evidence, a mandatory field on the punch feed)
status: APPROVED by Surbhi, 25 Nov 2026 (Q1 punches only; Q4 option B; Q5 refuse human deletes; the rest as recommended). Built locally, see 03c-implementation-notes.md. Not pushed.
read from: worktree /Users/mac/hr-app/.claude/worktrees/088-notice-scope, branch docs/088-notice-scope-analysis, built on origin/main 7ebc5898 (also read: release worktree release-088-alv436 at 59f95044)
---

# 088c: the notice must list every manual punch change, with a reason code

Labels: **proven** = I read the line or ran the check this session. **inferred** = reasoned from what I read. **not checked** = I did not look.

## 0. Bad news first

1. **The 088 notice code is already on `main`.** `origin/main` is `7ebc5898`, "Release 25 Nov 2026", made 25 Nov 00:08 IST. Its message says Surbhi knowingly overrode counsel's hold. `register_notice.py` is in it (proven: `git ls-tree origin/main`). The brief said main was `f68f2333`; that is out of date. The only protection now is the switch `alvoraa_print_change_notices` on Company, which ships off. **Nobody should tick it for DTC or Grace until this slice lands.** I did not check the live value of the switch on either tenant (not checked).
2. **Main also has a known blocker that is not fixed on it.** Review finding P1-1: a notice of two or more pages cannot be recorded, and the person's pay stays held. The fix is 4 commits on `release/088-alv436` (`eb9c3e5c`, `38680f00`, `6c7be8c3`, `4531ecb5`). `git cherry origin/main 59f95044` shows exactly 5 commits not on main: those 4 plus the two review documents (`59f95044`). The branch is dormant behind the switch, so this is not urgent, but it must land before the switch is ever ticked. Question 9.
3. **The gap is real, and it has a second half.** The notice reads only Attendance Requests (section 1). And no place in the system holds a reason for a typed or edited punch (section 1.2).
4. **"1,315 Administrator edits" were Attendance rows, not punches.** The memory note `dtc-october-backfill-not-a-gap` says "1,315 Attendance rows were changed by Administrator". The slice documents say "Administrator edits" next to "hand-made check-ins", which reads as if both were punches. Whether counsel's "direct edit" covers Attendance rows is the biggest open fork. Question 1.
5. **"Every path" cannot be fully kept. Say "every path through Frappe's document layer except where a script skips it", never "every".** A script that uses `frappe.db.set_value`, raw SQL or a bench console runs no document hook and leaves no record. I can cover every path through Frappe's document layer (section 2). I cannot cover those, and I will not claim to.

## 1. The gap, as I proved it

### 1.1 The notice reads one table

All in `alvoraa_portal/alvoraa_portal/register_notice.py` on `origin/main` (7ebc5898):

| What | Where | Label |
|---|---|---|
| `qualifying_changes` starts at line 160. | line 160 | proven |
| It queries only the doctype `Attendance Request` (`REQUEST`), with `docstatus` 1, `alvoraa_review_status` "Approved", `alvoraa_undone_on` not set. | lines 204-214 | proven |
| It drops a row unless it has `alvoraa_missing_time` or `alvoraa_set_aside`. | line 223 | proven |
| It drops a row whose `owner` is `Administrator`, or is the employee's own login. | **line 225** | proven |
| The file never reads `Employee Checkin` in `qualifying_changes`. The only mention of Employee Checkin is line 470, reading one punch's time to write a sentence. | grep, whole file | proven |

So a punch typed straight into Employee Checkin, or an edit made by anyone, never reaches the notice. Administrator-filed requests are dropped even on the request path.

**Callers of `qualifying_changes`: 4.** Three in the same file (`list_people` line 314, `open_notices` line 549, the employee's own `my_changes` view line 926) and one test (`test_held_team_086.py:456`). Counted with grep over `alvoraa_portal/` and `hrms/` (proven). Nothing outside `register_notice.py` calls it in production code.

### 1.2 Frappe does not hold a reason (read from Frappe 16.33.1, image `dev-3830ed3`, copied out of a stopped container I created and removed)

| Frappe record | Who | When | What changed | Why | Label |
|---|---|---|---|---|---|
| Row's own `owner` and `creation` on an inserted punch | yes | yes | the row itself | **no** | proven |
| `Version` row on a plain **insert** | no row at all: `save_version` returns when there is no earlier copy and no `updater_reference` (`document.py:1607`) | | | | proven |
| `Version` row on an **edit** through `doc.save()` | yes (Version.owner) | yes | field, old, new | **no**: `Version.data` holds only the diff (`version.py` `set_diff`) | proven |
| `Version` row on `doc.db_set`, `frappe.db.set_value`, raw SQL | **none** | | | | proven (`save_version` is called only from the save path, `document.py:1472`) |
| `Version` row on a Data Import insert | yes, with `updater_reference` | | | | proven (`importer.py:283`) |
| `Deleted Document` on a delete | owner = deleter | yes | the full row as JSON | **no** | proven (`delete_doc.py:237`) |
| Who may delete a Version | `Administrator` has delete on Version; System Manager has read only | | | | proven (`version.json`) |

Two more facts:
- `Employee Checkin` has `track_changes` = 1 (`hrms/.../employee_checkin.json`), so edits do leave Version rows (proven).
- `Employee Checkin` has **no reason field** and no "how was this made" field. I listed every field in the JSON, and the custom fields added by `field_checkin.after_migrate` and `punch_fix` (photo, GPS, offline, mock-location, legal-hold, the four 087 marks). None is a reason (proven).

**Conclusion (proven):** Frappe's audit records answer who, when and what. They can never answer why. And a plain insert of a punch leaves no Version row, only the row's own owner and creation. A reason must be captured at the point of entry. Reading Frappe's own records can supply who, when and what, but cannot be the only source.

### 1.3 What Frappe HR gives us that I checked (reuse first)

| Candidate | Verdict | Why |
|---|---|---|
| `Version` | **Reuse partly, not alone** | Good for edits (who, when, diff). No reason, no row on insert, none on `db_set`, Administrator can delete it, and it is one shared table for every doctype (a scan by `ref_doctype` and date on it is the wrong shape for a notice query; inferred, not measured). |
| Attendance Request's `reason` Select | **Reject for this** | `attendance_correction.REASONS` and the field are the employee's dropdown; the hrms controller reads `reason == "Work From Home"`. Putting HR codes ("Machine was down") into it widens a list employees see. |
| `Comment` | **Reject** | The code would live inside free text I would have to parse, and a comment is editable and deletable by its author (inferred; not checked in source). |
| `Deleted Document` | Reuse as-is for deletes, but see Question 5 | Holds who and when, no reason. |
| Frappe's Audit Trail report | **not checked** | I did not find it in the image in the time I allowed. Do not rely on it. |
| `Attendance Request` | Already the 087 path, and has a reason | Used for requests. Not for typed punches. |

## 2. Every way a punch can be added or changed

`files_as_machine()` (`field_app_access.py:59`) is the test for "machine": the user holds role `Biometric Sync`, has no Employee record, and is not Administrator (proven). The code comments say never judge by `device_id`. I follow that.

| # | Path | Who writes | Leaves today | Manual addition / direct edit for counsel? | On the notice today? | Proposed |
|---|---|---|---|---|---|---|
| P1 | **087 correction request**, approved. The approval inserts a real punch marked `alvoraa_fix_added_request` and sets others aside (`punch_fix.py:1296-1314`, under `frappe.flags.in_punch_fix_apply`). | HR or manager approves; filer is HR, a manager or the employee | the request, with its reason, explanation and before/after snapshots | **Yes**, when filed by somebody else | **Yes**, except Administrator-filed and the employee's own | Keep. **Remove the Administrator skip** (line 225). The employee's own request stays out: they asked for it. Do not log the punch rows it writes (the flag already marks them), or each change would be listed twice. |
| P2 | **Punch typed straight into Employee Checkin** in Desk (HR User, HR Manager, System Manager have create, `employee_checkin.json`) | a human login | row owner and creation; no Version row; **no reason** | **Yes** | **No** | New log row with reason, listed. |
| P3 | **Direct edit** of an existing punch in Desk: `time`, `log_type`, `employee`, `skip_auto_attendance` | a human login | Version row (who, when, diff); no reason | **Yes** (these four fields change what counts) | **No** | New log row with reason, listed. Other fields (shift, attendance link, photo, geolocation, shift times) are not material and are not logged. |
| P4 | P2 and P3 **by Administrator** | `Administrator` | same as P2/P3. On a punch with an 087 mark, `guard_marks` lets Administrator through and writes a security log line by id | **Yes** (counsel's wording has no exception) | **No** | Same as P2/P3. Question 2. |
| P5 | **Delete** a punch | a human login | `Deleted Document` row (who, when, full JSON); no reason. `guard_marks` already refuses deleting a marked punch for everyone except Administrator | **Yes** in effect (a punch vanishes) | **No** | Do not cover it. **Remove it**: refuse human deletes when the switch is on and say "set the punch aside by editing it and give a reason". Question 5. |
| P6 | **Data Import** of punches (`allow_import` = 1) | the importing human | Version row with `updater_reference`; **no reason** | **Yes** | **No** | Same as P2. The reason is a column in the import file, because it is an ordinary field. A row with no reason is refused with its row number. |
| P7 | The whitelisted `add_log_based_on_employee_field` (`employee_checkin.py:160`) called by **a person** | the caller's session | same as P2 | **Yes**, if the caller is not a machine account | **No** | Same as P2. It has no reason argument, so a person calling it is refused and told to use the normal insert. A machine account is unaffected. |
| P8 | **Biometric machine sync** (`Biometric Sync` role, no Employee record) | machine account | the row | **No**: a machine reading, not a person's entry | n/a | Never refused, never logged. The hard test (section 5). |
| P9 | **Field-app phone punch** (`field_checkin.py:670`, an `allow_guest` token endpoint, `doc.insert(ignore_permissions=True)`) and **web-portal punch** (`hr_api.do_checkin`, device_id "web-portal") | the employee's own phone or session | the row | **No**: the employee's own punch | n/a | Never refused, never logged. Session user for the phone path is probably `Guest` (inferred; I did not run it). A test must prove it. |
| P10 | **Punch-fix undo** (`punch_fix._reverse`, lines 1078-1082) edits and removes the punches an earlier fix wrote | the person who undoes | the request's `alvoraa_undone_*` fields (with a reason) | arguably | The undone request **drops out** of the list, even for a month already printed | **Not proposed.** Noted as an inferred gap: a signed notice can describe a change that is later reversed with no second notice. Surbhi to say if she wants it. |
| P11 | **Software flags a duplicate**: `punch_dedupe.py:253,273` set `skip_auto_attendance` with `frappe.db.set_value`, `update_modified=False` | the process of the inserting user | no Version row | **No**: the system, not a person's decision (inferred) | n/a | Not logged. The hook sees the write only through `db.set_value`, which runs no hook anyway. |
| P12 | **Scheduler and engine writes**: Frappe HR's auto attendance links punches (`update_attendance_in_checkins`, `skip_attendance_in_checkins`), `held_day.py:435` links a punch to a held day, `field_app_photos.py:171` clears a photo | system | none | **No** | n/a | Not logged. None changes `time`, `log_type` or who the punch belongs to. |
| P13 | **`alv291_attendance_fix.py`** (CORRECTED 25 Nov after review: see the note under the table): Administrator-only, run by hand with `bench execute`, built for DTC's October. It clears the skip flag by `frappe.db.set_value` (`:937`, `:1194`, `:1205`) and re-tags shifts by `doc.save()` (`:967`) | `Administrator` | the first leaves no Version row; the second leaves one | **Yes in effect** (it changes which punches count) | **No** | **Cannot be covered** by a hook, because `db.set_value` runs none. It is a one-off for October, which is untouched. If it is ever run again after switch-on, its changes are invisible to the notice. Written into the runbook warning, not code. |
| P14 | **Raw SQL, bench console, a script that writes the table directly** | anyone with shell | nothing | Yes in effect | No | **Cannot be covered.** I will say so in the release note, not hide it. |
| P15 | **Attendance rows** (`Attendance`: submittable, `track_changes` = 1, no field editable after submit; proven from `attendance.json`). A change means cancel, then re-create or amend | HR, Administrator, scripts | Version and docstatus history | **Unknown.** Not a punch. This is where the 1,315 October rows were. | No | **Not covered.** Question 1. |

Count: 15 paths. P1 to P7 are manual and I propose to cover them (P4 is P2 and P3 done by Administrator). P8 and P9, and the self-edit below, are not manual. P10 is a gap I leave open. P11 and P12 are system writes. P13 and P14 cannot be covered. P15 is a question.

****Correction to P13 (review 05c, P2-2, verified in the source).** The script's *skip-flag* steps use `frappe.db.set_value` (`:937`, `:1194`, `:1205`) and run no hook: not covered. Its *retag* step (`:966-970`) uses `doc.save()` with `doc.flags.ignore_validate = True`, and a retag moves a punch to another working day. 088c now covers it: `shift` and `shift_start` count as material, and the rule runs in `before_validate`, which runs even with `ignore_validate`. Consequence: with the switch on, running `retag` as Administrator is refused until a reason is supplied. That is intended.

**Three escapes found in review that this table did not list:** (1) `ignore_validate` (closed, above); (2) the shift tag (closed, above); (3) **a sync login a person can use**: a login that holds `Biometric Sync` is treated as a machine, and the real accounts also hold an HR role (ALV-302), so a person who knows that login's password can type punches that are never logged. Not closed by code; it is an access-control matter for the customer (who holds those passwords). Also open: raw SQL and `frappe.db.set_value` (P13, P14).

**For the runbook, not solved in code (review item 15).** Two repair paths in this repo write punches straight to the database and leave no record: `alv291_attendance_fix.py:937,1194,1205` and `punch_dedupe.flag_existing` / `unflag_existing` (`:253`, `:273`). With the switch on, Desk bulk edit is refused row by row, so bulk corrections move to exactly those unlogged paths. Anyone running either after switch-on must know their changes will not be on the notice.

**Moving a punch between people (P-move, Surbhi 25 Nov):** refused while the switch is on. HR adds the punch to the right person and sets the wrong one aside with a reason, which is notified on both sides.

**Record is tamper-evident, not tamper-proof.** The log refuses edits and deletes through the app, including Administrator. Server code, a migration patch or a database login can still alter or remove a row and leave no trace in the app. The evidence pack must say "tamper-evident", never "tamper-proof".

One more exclusion: an employee editing their own punch.** The Employee role has create and write at level 0, but `time` is level 1. If `frappe.session.user` equals the punch employee's `user_id`, it is the employee's own act and is not logged. HR editing their own punch is treated the same way (a known, small blind spot; inferred).

## 3. Strategy

### 3.1 The ladder, with the rung named

| Rung | Verdict |
|---|---|
| 1. Already there | **Rejected.** Frappe has who, when, what. It has no why (proven, 1.2). |
| 2. Configuration | **Used for the switch only.** The existing Company switch `alvoraa_print_change_notices` (read by `notices_are_on`) is reused. No new switch. |
| 3. Customisation | **Used.** One Custom Field on Employee Checkin: a Select "Reason for this change", the entry point for Desk, import and API. Same pattern as `field_checkin.after_migrate` and `attendance_correction.install_reasons`. |
| 4. New code | **Used.** One small module with three hook handlers on Employee Checkin, and the widening of `qualifying_changes`. |
| 5. New DocType | **Proposed, for you to approve or reject: one append-only log, "Alvoraa Punch Change".** See 3.2 for exactly what fails without it. |
| 6. New app | No. |

### 3.2 Where the reason comes from: both, and why a log

**Recommended (Option B).** The reason is compulsory at the point of entry. The Select field takes it. A handler copies it into one row of a small append-only DocType and blanks the field, so it never sits stale on the punch. The notice reads the log.

**Cheaper alternative (Option A), if you reject the new DocType.** Keep the Select on the punch, persistent, and read the notice from Version plus the row itself. It fails in three named places:
1. **A stale reason.** An edit that leaves the old reason in place looks identical to one that supplied it. The only fix is to refuse a save where the reason did not change, which means HR cannot give the same reason twice in a row on one punch.
2. **No row on insert, no reason on delete.** A typed punch has only its own owner and creation; a deleted punch has no field to hold a reason. A is workable only if humans may not delete (Question 5) and the notice reads the punch row for additions and Version for edits, two shapes of source.
3. **Evidence and speed.** Version is one table for every doctype, and Administrator can delete rows from it (proven). The notice and any "who changed what" breach query would scan it. A log table indexed on employee and day is one query.

I recommend B because counsel's test is evidence, and a row that nobody can edit or delete is the stronger evidence. B costs three files for the DocType (JSON, controller, init), one Custom Field, one module. I have not measured Version volume (not checked).

**The log row holds:** the punch (a plain `Data` copy of its name, not a Link, so it survives a delete), the employee, the company, the day, the kind (Added or Changed), the before and after of the material fields as short text, the reason code, `changed_by`, `changed_on`. No free text. It is created under a module flag and refused for edit or delete otherwise, the same pattern as `alvoraa_register_notice.py` (proven by reading it). Index on `(employee, day)`.

### 3.3 Reason code, not free text

> **DRAFT LIST. It needs sign-off (the employer and counsel) before the notice switch is ticked on any tenant.** It is not a code blocker. The list is the `reason_code` Select options in `alvoraa_punch_change.json`; changing it is one JSON edit.

**A fixed list.** Counsel's word is "reason code". Free text was the thing ALV-436 had to defend against (markup, personal detail in a sentence one person writes about another), and it cannot be counted or checked. The list lives in the log DocType's Select options (one source). The Custom Field's options are filled from that same list at `after_migrate`, so the two cannot drift. A Property Setter or HR Settings page for the list is rejected: one tenant list, edited by nobody asking for it.

Draft list, **mine, not counsel's and not a legal list** (Question 3):
1. Employee forgot to punch
2. Punch machine was down or offline
3. Wrong direction (in and out swapped)
4. Duplicate or accidental scan
5. Employee not yet enrolled on the machine
6. Employee was on approved duty away from the machine
7. Other (details are in the HR file)

No text box. "Other" points to the employer's own paper record.

### 3.4 What the notice must list

For one person and one month (the punch's day in that month), every row of:
- **(a)** the 087 request changes it lists today, **plus those filed by Administrator** (the Administrator skip at line 225 goes);
- **(b)** the log rows of kind Added or Changed.

Per row: the day, what changed in the same words style as today, "HR" (no name, per decision OQ-1 already built in `sheet_rows`), the date made, and the reason, which for (b) is the code's label. A row with no reason cannot exist in the log (the reason is compulsory), so the paper never prints a blank.

Direct changes **do not hold pay** (`blocks_pay` False, no `alvoraa_needs_confirm`). That is my assumption: counsel's own question of whether the signature must also gate pay for direct edits is still open (Question 6).

**State of a direct-change row** (printed, signed, not right) is read from the notice record that covers it, not written onto the punch. The signature marker for requests (`punch_fix.record_register_signature`) stays for requests only.

### 3.5 Switch-on, and the boundary

- **Mechanism:** the existing Company switch. The three handlers return at once when `notices_are_on(company)` is false. So **nothing before the switch is ever demanded, and nothing before it is ever in the log.**
- **No boundary date field is needed.** The log is written only while the switch is on. The notice reads only the log (plus requests as today). Nothing reads Version for punches, so October cannot leak in. The "boundary" is the first log row (a query, not a column).
- **No back-fill, no migration, no disclosure.** The migrate creates an empty DocType and the Custom Field. No patch reads or writes existing punches (Surbhi's decisions 1 and 2).
- **If the switch is turned off and later on again:** changes made while off are never logged. That is the organisation's own override. Company has `track_changes` = 1 (proven from `company.json` in the image), so the toggle's who and when is in Version for free. Question 8.
- The Company field's description (in `register_notice.FIELDS`) must say that ticking it also makes HR give a reason for every punch they add or change.

### 3.6 Files and touch points (so the blast is visible)

| File | Change | New or existing |
|---|---|---|
| `alvoraa_register_punch_change` DocType (JSON, controller, `__init__`) | the append-only log | new, 3 files |
| `alvoraa_portal/alvoraa_portal/punch_change.py` | the validate check, the log writer, the Custom Field | new |
| `hooks.py` | Employee Checkin: `validate` list +1; `after_insert` string becomes a list (+1); new `on_update`; `on_trash` string becomes a list (+1); `after_migrate` +1 | existing, **hot file** |
| `register_notice.py` | `qualifying_changes`, `_latest_notices` (:246-249), `_write_the_notice` (:616), `_still_the_same` (:644), `record` (:748, :781), `my_changes` (:926-947), `sheet_rows` | existing |
| `alvoraa_register_notice_change.json` | add `punch_change` Link; `request` stops being required | existing DocType, ours |
| `translations/en.csv` | new sentences and the reason labels | existing |
| tests | below | |

`register_notice.py` has 7 places that assume a change is an Attendance Request (the lines above). Widening it is real work in a 965-line file, not a one-line change. That is the honest size.

## 4. What breaks, and for whom

**Until a company ticks the switch, nothing changes for anyone** (proven by design: the handlers return first; the switch defaults 0, `register_notice.py` FIELDS). Only `test_register_notice_088.py` turns the switch on (grep: 2 files mention `NOTICE_SWITCH`, one is the module itself).

After a company ticks it:

| Who | What they will see |
|---|---|
| **HR, HR Manager, System Manager, Administrator** adding or editing a punch in Desk | A required "Reason for this change" field. Saving without one is refused: "Pick a reason for this change. It is printed on the employee's monthly notice." |
| Anyone using **Data Import** for punches | The file needs a reason column. A row without one is refused with its row number. Today's imports of the 2,007 kind would fail until the column is added. |
| A person calling **`add_log_based_on_employee_field`** | Refused, with a message to use the normal insert. A machine account is not affected. |
| A person **deleting a punch** | Refused, told to edit it and tick "Skip Auto Attendance" with a reason (Question 5). |
| **Machine accounts, phone app, web portal, the employee's own edit** | Nothing. This is the guard rail. |
| **The employee** (in the app, `my_changes`) | The same list gains direct changes with their reason code. |
| **HR printing the notice** | More rows per person. The volume is **not known**: October's ~3,300 was a deliberate catch-up, so a normal month is probably far fewer (inferred). Measure the first normal month after switch-on before promising anything about page counts and photo storage. |
| **Pay** | Unchanged. Direct changes hold nothing (assumption, Question 6). |

**Suites and features in the blast radius** (named by reading, not by running):
- `test_register_notice_088.py` (80 tests): the Administrator exclusion test (a fix `by="Administrator"` around line 437) must flip; the `changes` table tests change.
- `test_held_team_086.py` (calls `qualifying_changes` at line 456) and `test_punch_fix_087.py` (the register seam, `guard_marks`).
- Every suite that **inserts a punch**: 25 test files create an `Employee Checkin` by document, 40 mention it (counts by grep). They run the new handler's early-return path. The ones that matter most: `test_alv302_sync_punch.py`, `test_held_p1_machine_accounts_085.py`, `test_held_day_085.py`, `test_punch_dedupe_alv337.py`, `test_checkin_security_014.py`, `test_field_checkin_fixes_013.py`, `test_branch_geofence_alv338.py`, `test_portal_security_010.py` (the permission ceilings: the new DocType needs a row).
- `portal_register_notice_088_test.js` (DOM test), `scripts/check_portal_trays.js`, the translation and integrity checks (memory: `check_app_integrity.py`).
- Features: the field app punch, the web check-in, the biometric sync and ALV-302 date window, ALV-337 duplicate skip, 085 held-day release (`held_day.release_on_machine_punch`, after_insert, which I must not disturb), 087 approval and undo, 086 bulk held fixes (they go through the request flow; not read in full, not checked).
- Hook order on Employee Checkin: `before_insert` (ALV-302, ALV-337), `validate` (geofence, `guard_marks`), `after_insert` (085). My handlers are added after these and must not reorder them.

## 5. The first test, written before the code, and shown to fail first

**A machine punch is never refused, and never logged.** (PM handoff, `01d`.) Cases: machine account inserts with the switch on; phone-app insert as `Guest`; web-portal insert as the employee; the 087 approval insert; the employee editing their own punch. Each must succeed and write no log row. Then the people cases: HR with no reason is refused; HR with a reason writes exactly one row; Administrator the same; an edit of only `shift` writes nothing. Plus: a notice for a month containing a log row lists it, and a log row from before the switch cannot exist.

## 6. Non-functional verdicts

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **neutral** with the switch off; small cost on | Off: one cached Company read per punch, before any query. On, for a machine punch: `files_as_machine()` is 2 existence queries, and two handlers already pay it on every punch, so order the cheap tests first (switch, then own-user, then machine). The notice adds one indexed query per list and per print. Not measured; baseline unknown. |
| Security | **improves** | A person's change to a punch now needs a reason and leaves a record that cannot be edited or deleted. New DocType: HR roles read only; no create or write role; row scope by the existing HR employee scope. Refusing a human delete closes a path. Risk: the check must be server-side only (it is a `validate` hook, not a client rule). |
| Reliability | **degrades slightly, guarded** | A new mandatory rule sits on a table the machines write to. A fault in my handler must never fail a machine punch (the sync tool stops a machine's whole batch on an error it does not know, `field_app_access.py`). So: machine and Guest return first, and the handler logs its own errors and never raises for those. The log row and the punch save in one transaction. |
| Scalability | **neutral** | Log rows are one per material change; indexed `(employee, day)`. The notice's employee-scope query (review finding P3-8) already exists and is unchanged. |
| Maintainability | **degrades slightly** | One more DocType and one more source for the notice. Offset by one reason list in one place and a single writer function. |
| Data integrity | **improves** | The reason is stored with the change, not left stale on the punch. The punch's name is stored as text so a log row outlives a delete. Risk: paths with no hook (P13, P14) produce no row. Mitigation: a read-only reconciliation query (punches created or edited after the first log row, by a non-machine owner, with no log row) for the release check. It is a query, not a feature. |
| Compliance / privacy | **improves, one new item** | Meets counsel's condition for the paths I can reach. The log holds two punch times, a user and a code: personal data, kept in our own DocType, HR-only, not in any log line (log lines carry document names only). **Retention: 5 years maximum, same as the notice (Surbhi).** I propose the `day` column so a future purge can compute its own date, and no purge job now. That is the same trade as the notice and needs a dated ticket (Question 10). Reason codes (fixed list) avoid free text about a person. |

## 7. Parallel-work check

- Fetched `origin` (dev `215bac59`, main `7ebc5898`). Read the incoming difference between the merge base and dev: 088 itself is on both. I read only the files I need.
- Work board `.claude/work-in-progress.md`: no row names 088, `register_notice.py` or `punch_fix.py`. Five rows list `hooks.py` (ALV-318, ALV-281, ALV-337, 082, 084), all dated 5 to 19 Nov. ALV-337 is the one in the same `Employee Checkin` hook block; its file `punch_dedupe.py` is already on main, so it has landed (inferred). I did not check whether the other four rows are live. Ask before the hook edit.
- Worktrees touching my files (checked all 32 for a diff against `origin/main` in these files): only `release-088-alv436`, which is the release branch I read and which is **behind main** except for its 5 commits.
- `hooks.py` is a hot file. My edits are three lines inside the existing `"Employee Checkin"` block. I will rebase just before the edit, not hold it open.
- Other live containers (`alv086`, `alv089`, `alv090`, `alv091`, `alv436rel`, `alv440`) are other sessions'. **I touched none.** The only Docker commands I ran were `docker create`, `docker cp` and `docker rm` on one throwaway container of my own, to read Frappe's source.

## 8. Questions for Surbhi

1. **Does "direct edit" include Attendance rows, or punches only?** The 1,315 October Administrator changes were Attendance rows (proven in the memory note), not punches. **Recommend: punches only for now**, and ask counsel to confirm in the same message as question 6. Attendance has no field that can change after submit, so a change is a cancel and re-create, which is a different mechanism and its own slice.
2. **Administrator.** Count it, demand a reason from it, and show it on paper as "HR" (the sheet already shows HR with no name, so there is no "shared account" wording problem on the page). **Recommend yes.** The log still records the real login.
3. **The reason list.** Section 3.3 is a draft. Who approves it? It is not mine to make a legal list. **Recommend** you approve it with the customer's HR, and that "Other" has no text box.
4. **New log DocType (B) or field-only (A)?** **Recommend B**, for the three failures in 3.2. A is workable only if humans may not delete punches and a reason must change on every edit.
5. **Deleting punches.** **Recommend refuse human deletes when the switch is on**, and send HR to "edit and tick Skip Auto Attendance with a reason". Alternative: ignore deletes, which leaves a gap counsel will see.
6. **Pay.** Direct changes hold no pay and need no signature to release it. **Recommend yes, notice only** (my assumption; counsel has not answered). If counsel says the signature must gate pay, this becomes a larger slice.
7. **A change made after switch-on to a day in an earlier, already-paid month.** **Recommend it is listed on that earlier month's notice.** The decision is about the date of the change, not the date of the day. October stays untouched because nothing before switch-on exists in the log.
8. **Switch off then on.** Changes made while off are never logged, and nothing warns. **Recommend accept**, with the Company's own Version history as the record of the toggle.
9. **The page-count fix.** Main carries a known blocker (two-page notices cannot be recorded). **Recommend cherry-picking the 4 fix commits to dev as a small separate change first**, and that **nobody ticks the switch on any tenant until this slice and that fix are both live.** It needs your word.
10. **Retention for the new log.** **Recommend** the same rule as the notice (5 years maximum, `day` stored so the date can be worked out) and one dated ticket for the expiry job. No purge in this slice.
11. **Scope of the first release.** **Recommend** the notice covers P1 to P7 (section 2). P10 (undo) stays out unless you say.

## 9. Subtract pass: considered and left out

- A boundary date field on Company (the log is itself the boundary).
- A second switch for the reason rule (reuse the existing one).
- A Reason Code DocType, an HR Settings list, a tenant-editable list.
- A free-text note beside the code.
- A reconciliation or alarm job (a read-only query at release instead).
- A purge job (a dated ticket instead).
- Reading Version for old punches, any backfill, any disclosure of October.
- Logging machine, phone, web, system or scheduler writes.
- A wrapper around `frappe.db.set_value` to catch P13 (it is a one-off for October).
- Fixing `alv291`, the undo path (P10) or anything else I noticed. Written down, not built.

I removed nothing from the build because nothing is built.

## 10. What I did not check

- The live value of the notice switch on DTC and Grace (not checked).
- How the 2,007 hand-made October punches were made: import, script or typing. The slice documents do not say (not checked).
- The session user on the phone-app path: probably `Guest` (inferred). A test proves it.
- Whether Frappe's Audit Trail report exists in this version (not checked).
- Version-table size and a measured time for the notice query (not checked).
- `held_team.py` (086 bulk fixes) in full. I saw it reads Employee Checkin at line 107 and found no insert by grep (inferred that it uses the request flow).
- A Comment's delete rights in source (inferred).
- That no notice rows exist on production (inferred from "the list is empty").
- I did not run any test and did not start any container or site.

## 11. Surbhi's decision on paper volume (25 Nov 2026)

**Ship it, and measure the first month. No mechanism is added now.** The worry: once direct punch changes are on the notice, the paper grows. The figure it rests on: October had about 3,300 changes for about 600 people, roughly **5.5 changes per person**, and a page holds 5 rows (`PER_PAGE = 5`), so a month like October would be two pages for most people who had any change. October was a deliberate catch-up (the machine sync and training were late), so a normal month is probably much lower, but nobody knows. After the first full month with the switch on, count changes per person and pages printed, and judge them against 5.5 and against one page. If the count is near October's, that is the time to decide about a summary page or a higher page size, not before.

## 12. The retention job, and the tension it carries (for the ticket)
A purge job has to delete rows that the log's `on_trash` refuses to every role, Administrator included. So it will need `frappe.db.delete` or a module flag, and **that becomes the supported way to remove audit rows**. Nobody should add an exemption flag casually before then: the migrate exemption was removed in review for exactly this reason, and a flag added "for the purge" will also be available to a migration patch. Decide the mechanism once, in the ticket, with its own test and its own log line for every run.
