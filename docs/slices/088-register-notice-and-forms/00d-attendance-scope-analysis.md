---
slice: 088d (the change notice also lists a person's changes to the day's record)
author: hrms-fullstack-engineer (impact analysis and strategy only; no production code written)
date: 2026-11-26
worktree: /Users/mac/hr-app/.claude/worktrees/088d-attendance-scope, branch docs/088d-attendance-scope
built on: origin/dev e82bb3f0 (fetched 26 Nov; HEAD of the worktree is the same commit)
risk tier: 1 (pay, who can change what, personal data)
status: waiting for Surbhi's approval. Nothing pushed. No site or container touched.
---

# 088d: day-record changes on the monthly notice

How to read the labels: **proven** = I read it in source this session (file and line named). **inferred** = follows from what I read, not run. **not checked** = I did not look.

What I read: the repo at `origin/dev` e82bb3f0 (this worktree) for `alvoraa_portal`, `hrms` (the in-repo Frappe HR fork) and `alvoraa_goals`; Frappe **16.33.1** and ERPNext, copied out of the image `hr-app:dev-3830ed3` with a container I created and removed without starting it (no running container or site was touched). ERPNext has no Attendance writer that I looked for; I searched `hrms` and `alvoraa_*` only (see section 9).

---

## Decisions of 26 Nov 2026 (Surbhi), added after approval

| Question | Her decision | Note |
|---|---|---|
| Q1 first-ever manual marks | **Listed.** She chose against my recommendation ("no"). | Her decision, not mine. What it costs in pages: **not measured**, because nobody knows how many days are marked by hand. Each marked day is one line and a page holds five (`PER_PAGE = 5`), so a tenant whose HR marks every day of every person by hand would print about 20 to 30 lines a month for each person, which is 4 to 6 pages each. A machine-fed tenant such as DTC pays little. **Second cost, found in the build:** the Employee Attendance Tool and the list button "Mark Attendance" have nowhere to ask for a reason, so while the switch is on they are refused (loudly, up front). For a tenant that marks attendance with those tools every day, this switch cannot be turned on until a way to give a reason is built. |
| Q2 cancel | Two steps, as recommended | |
| Q8 Employee Attendance Tool half-day tick | Refused, as recommended | Because first marks are now listed the whole tool is refused, which includes the tick. |
| Q4 | Two lines, cause and consequence; no merge | |
| Q3, Q5, Q6, Q7, Q9, Q10 | My recommendations stand | |

Where the build found something that 00d got wrong, it is in `03d-implementation-notes.md`.

---

## 0. Bad news first

1. **The lead "automatic attendance never saves an Attendance document" is wrong for the part that matters.** Auto attendance creates its rows with `attendance.save()` then `attendance.submit()` (`hrms/hr/doctype/employee_checkin/employee_checkin.py:342-343`, proven) and `frappe.new_doc` + `insert()` + `submit()` for the "Absent" rows (`attendance.py:338-367`, called from `shift_type.py:314`). Only two helpers use query-builder UPDATEs, and those write **punch** rows, not Attendance (`employee_checkin.py:485-500`, proven). So a document save on Attendance is **not** a sign of a human. Every hook on Attendance fires for the software's own rows.
2. **The scheduler runs as `Administrator`.** `frappe.connect()` defaults to `set_admin_as_user=True` (`frappe/__init__.py:230`) and `execute_job` only calls `set_user` when a user is passed (`utils/background_jobs.py:251`). So background work is "Administrator" unless a person queued it. Since 088c counts Administrator as a person (Surbhi, Q2), **a rule "Administrator is a person" would list the hourly auto-attendance job as a human edit.** (proven in code; inferred that the live scheduler passes no user; I did not run it.)
3. **The figure "1,315 Attendance rows changed by Administrator" cannot be read as human edits.** It is a `modified_by` count (memory note `dtc-october-backfill-not-a-gap`: "changed by Administrator in the 60 days to 23 Nov"). The scheduler and a repair script both leave `modified_by = Administrator`. So the real human share is **unknown**, and the paper-volume estimate in section 7 carries that doubt.
4. **A leave approval, an Attendance Request approval and a Shift Type button all run inside a person's web request and save Attendance rows.** A hook that "refuses unless a reason is given" for every person's save would **refuse HR's leave approvals**. That is the single worst failure available here, and it is why section 3 is built around a short list of doors, not a "is this a person" test.
5. **A stock bulk tool will say "Attendance marked successfully" after skipping rows our rule refused.** `process_bulk_attendance_in_batches` catches `Exception` and `continue`s (`attendance.py:420-421`), and `mark_bulk_attendance` prints the success message regardless (`attendance.py:400-401`). Proven. Edge case (section 3.5), but it is a silent failure.
6. **One hook-less human path cannot be caught by any document hook:** the Employee Attendance Tool's half-day tick uses `frappe.qb.update(Attendance)` and changes `half_day_status`, `shift`, `late_entry`, `early_exit` on existing submitted rows (`employee_attendance_tool.py:205-213`, proven). Question 8.

---

## 1. Step 1, impact analysis

### 1.1 What "a change to the day's record" can mean in this system (proven)

`Attendance` is **submittable**, `track_changes` = 1, `allow_import` = 1 (`attendance.json`). HR User, HR Manager and System Manager hold read, write, create, submit, cancel, delete (HR User also import); Employee holds read only.

After submit, **no stock field is editable** (no `allow_on_submit` in `attendance.json`; Frappe enforces it at `base_document.py:1278`). The only fields editable after submit are our own Custom Fields: 16 are `allow_on_submit` (13 in `payroll_fields.py` VERDICT, counted by script, plus 3 release fields in `held_day.py:47-55`). Two of those are meant for a person: `alvoraa_held_confirmed` and `alvoraa_confirmed_out_time` (`payroll_fields.py:20-24`). The rest are read-only in the form, but I did **not** prove the server refuses a REST write to a read-only field (not checked; inferred that it does not).

So a person changes a submitted day in exactly these ways: (a) tick the two held-day confirm fields; (b) cancel the row; (c) replace it (amend, or a new row where a cancelled one exists); (d) delete a draft or a cancelled row. They create a first-ever row for an unmarked day in many ways.

### 1.2 What pays money (proven from payroll code)

| Field | Read by | Pay effect |
|---|---|---|
| `status`, `leave_type`, `half_day_status` | `salary_slip.py:812-826` (`get_employee_attendance`), `:653-668` (`get_half_absent_days`) | days paid, LWP, half-absent days. **Yes** |
| `late_entry`, `early_exit`, `in_time`, `out_time` | `alvoraa_late_rules/late_rules.py:120-125` | late and early-exit deductions. **Yes** (inferred that all four are read) |
| `overtime_type`, `standard_working_hours`, `actual_overtime_duration` | `overtime_slip.py:80-92` | overtime pay. **Yes** (inferred) |
| `shift` | the engine, `held_day.py`, `punch_change.MATERIAL` (088c already treats the shift tag as material) | which rules apply. **Yes** |
| `alvoraa_held_confirmed`, `alvoraa_confirmed_out_time` | `payroll_rules_apply.py:528-530` | the held day's hours. **Yes** |
| the 11 engine verdict fields, 3 release fields | the engine writes them with `frappe.db.set_value` (`payroll_rules_apply.py:566`) | derived; **not a person's decision** |
| `working_hours`, `company`, `department`, `employee_name`, `attendance_request`, `leave_application` | derived or links | not material by themselves |

### 1.3 Every way an Attendance row is created or changed

I searched `alvoraa_portal`, `hrms` and `alvoraa_goals` (not `frappe`, not `erpnext`; section 9) for `new_doc`, `get_doc`, `set_value`, `db_set`, `delete_doc`, `qb.update`, raw `tabAttendance` SQL and `"doctype": "Attendance"`, then opened each hit. Reads (reports, `salary_slip`, `payroll_entry`, `home_api`, `hr_api`, `org_figures`, `people_trends`, `grooming`) are not writers. **Count: 31 paths below** (A1 to A31).

"Hooks" means the Attendance `doc_events` that run. Class: **S** system, **ST** a person triggers it but the act is another record's, **H** a person's direct edit, **H-listed** a person's act already on the notice, **H-blind** a person's act no document hook can see.

| # | Path (file, function) | How it writes | Hooks that run | Who | Class and why |
|---|---|---|---|---|---|
| A1 | Hourly auto attendance: `hooks.py:362-364` `process_auto_attendance_for_all_shifts` → `shift_type._process` (`:176`) → `employee_checkin.mark_attendance_and_link_log` → `create_or_update_attendance` | new row `save()` + `submit()` (`employee_checkin.py:342-343`) | validate, on_update, on_submit (ours: `hold_odd_punch_day`, `on_attendance_submit`) | `Administrator` (scheduler) | **S** |
| A2 | Same, started by a person's click on Shift Type "Mark Attendance" (`shift_type.js:31`, `shift_type.py:149-167`) | same; inline up to 1000 punches, else queued | same | the person, in a web request | **ST**. Same code as A1; the person's act belongs to Shift Type |
| A3 | Absent for days with no punch: `shift_type.mark_absent_for_dates_with_no_attendance` (`:302-327`) → `attendance.mark_attendance` | new row, `insert()` + `submit()` (`attendance.py:366-367`) | validate, on_update, on_submit | as A1 | **S** |
| A4 | Other half Absent: `shift_type.mark_absent_for_half_day_dates` (`:432-463`) | `frappe.db.set_value` + a Comment | none | as A1 | **S** |
| A5 | Existing half-day row updated by auto attendance: `employee_checkin.create_or_update_attendance` (`:306-312`) | `frappe.db.set_value` | none | as A1 | **S** |
| A6 | Leave approved: `leave_application.update_attendance` → `create_or_update_attendance` (`:308-374`) | existing row: `doc.db_set` (status, leave_type, leave_application, half_day_status); no row: `insert(ignore_permissions)` + `submit()` with `ignore_validate=True`; holiday: `cancel()` + `delete_doc(force=1)` | db_set: none. New row: before_validate, on_update, on_submit (validate and before_submit skipped). Holiday: before_cancel, on_cancel, on_trash | the approver, in a web request | **ST**. The Leave Application is the record |
| A7 | Leave cancelled: `leave_application.cancel_attendance` (`:376-385`) | `frappe.db.set_value("Attendance", name, "docstatus", 2)` | none (not even on_cancel, so the punches stay linked: a side effect of stock code, not ours) | the person cancelling | **ST** |
| A8 | Attendance Request approved: `attendance_request.create_attendance_records` (`:155-221`) | existing: `db_set` + Comment "Changed the status from X to Y via Attendance Request"; none: `insert()` + `submit()` with `attendance_request` set | db_set: none; new row: validate, on_update, on_submit | the approver | **ST**. The request carries a reason. On the notice today only if it is a punch fix (`register_notice._request_changes:241-243`) |
| A9 | Attendance Request cancelled: `attendance_request.on_cancel` (`:145-152`) | `attendance_obj.cancel()` | before_cancel, on_cancel | the person cancelling | **ST** |
| A10 | 087 punch fix approved: `punch_fix.apply` (`:1264-1339`) → `_write_day` or `held_day._write_release` | `frappe.db.set_value` on status, hours, late, early, in/out, half-day, plus `attendance_request` | **none** | HR or manager approving | **H-listed**. One act, one line: the request. Punches are written under `in_punch_fix_apply` (088c exempts them) and the day by `set_value`, so no hook sees either. **Double reporting is avoided by construction here.** |
| A11 | 087 undo: `punch_fix.undo_change` (`:1090-1124`) | `_write_day` (set_value) | none | HR | **H**, and a known gap (00b P10: the undone request drops off the list). Not changed by 088d |
| A12 | Machine punch releases a held day: `held_day.release_on_machine_punch` (`:413-443`) | `_write_release` (set_value) | none | machine account | **S** |
| A13 | The hold: `held_day.hold_odd_punch_day` (Attendance `validate`, `:256-273`) | sets `status = "Held"` on a new auto-made row | it IS a hook | scheduler | **S** (our own handler) |
| A14 | Verdict: `payroll_rules_apply.write_verdict` (`:557`) from `on_attendance_submit` (`:637`), `evaluate_attendance`, `payroll_reprocess.apply` (`:182-209`, a person clicks "Reprocess") | `set_value(..., update_modified=False)` on the 11 derived fields | none | system, or a person's click | **S / ST**. Writes only derived fields |
| A15 | `leave_rules.prepare_half_day_correction` (`:477`) | `set_value half_day_status = "Absent"`, an engine fact | none | the employee's own request | **S** |
| A16 | Desk form: person makes a new row, saves, submits (`frappe.desk.form.save.savedocs`, `save.py:15-48`) | document layer | before_validate, validate, before_save, on_update, before_submit, on_submit | a person | **H** (first-ever mark: Q1) |
| A17 | Desk "Update" on a submitted row (same `savedocs`, action Update) | document layer, `allow_on_submit` fields only | before_update_after_submit, on_update_after_submit. **before_validate does not run** (`document.py:1404`: only for save and submit) | a person | **H**: tick the two confirm fields |
| A18 | Desk "Cancel" (`save.py:53-66`, `cancel(doctype, name)`) | `doc.cancel()` | before_cancel, on_cancel. **Carries no field values, so no reason can ride on it** | a person | **H** (the "reset": `on_cancel` unlinks the punches, `attendance.py:247-259`, so the hourly job re-marks the day from the punches (inferred)) |
| A19 | Amend: a new draft with `amended_from`, saved and submitted through A16 | document layer | as A16 | a person | **H**: this is "updating the day" the Frappe way |
| A20 | Delete a draft or a cancelled row | `delete_doc` | on_trash (ours: `refuse_own_attendance_change`) | a person | not in force either way, so **not listed**. A submitted row cannot be deleted without cancelling first (Frappe rule; inferred) |
| A21 | `frappe.client.insert / save / submit / cancel / delete / set_value / bulk_update` (`client.py:184-306`) and the REST resource `api/v1.py:44-67`, `api/v2.py:171-210` | document layer | as A16 to A18 | a person or an API login | **H**. REST has no `cmd` (inferred: path-based) |
| A22 | List-view bulk submit, cancel, update: `bulk_update.submit_cancel_or_update_docs` (`:52-92`) | document layer, in the request or an enqueued job | as A16 to A18 | a person | **H** |
| A23 | List button "Mark Attendance": `attendance.mark_bulk_attendance` (`:375-401`) → `process_bulk_attendance_in_batches` (`:404-424`) | `insert()` + `submit()`; over 10 days it is queued as a job | validate, on_update, on_submit | a person | **H** (first-ever marks, Q1). Swallows refusals (section 0, item 5) |
| A24 | Employee Attendance Tool: `employee_attendance_tool.mark_employee_attendance` (`:169-213`) | new rows: `insert()` + `submit()`; half-day tick: `frappe.qb.update(Attendance)` on existing rows | new rows: yes. Half-day tick: **none** | a person | new rows **H**; half-day tick **H-blind** (Q8) |
| A25 | Upload Attendance: `upload_attendance.upload` → `import_attendances` (`:174-235`) | `csvutils.import_doc(..., submit=True)`; inline under 200 rows, else queued | document layer | a person | **H** |
| A26 | Data Import on Attendance (`allow_import` = 1) | document layer; `frappe.flags.in_import = True` (`data_import/importer.py:74`); Frappe skips its Select check (`base_document.py:1102`) | all, but Select values unchecked | a person | **H** (this is F3) |
| A27 | `alv291_attendance_fix.cancel_wrong` (`:901-950`, `doc.cancel()` at `:915`), then `enable_and_mark` re-creates through A1 | document layer | before_cancel, on_cancel | `Administrator`, `bench execute`, no web request | a person's act in effect, **not at a door**: **H-blind** in practice. This, or something like it, is the likely source of the October rows (inferred) |
| A28 | The same script also writes punches (`:937`, `:1194`, `:1205`, set_value; `:967-970`, `doc.save()` with `ignore_validate`) | | | `Administrator` | punches: 088c already named this (00b P13) |
| A29 | Bench console, raw SQL, a script on the server | anything | none | anyone with a shell | **uncoverable**, as P14 |
| A30 | Frappe HR patches, e.g. `patches/v15_0/set_half_day_status_to_present_in_exisiting_half_day_attendance.py` (`qb.update`) | one-off at migrate | none | migrate | **S** |
| A31 | Employee Checkin edited by a person (088c) | punch only | none on Attendance | a person | The day record does **not** follow. Nothing in this repo re-judges the day when a punch is edited in Desk (checked `hooks.py` Employee Checkin handlers and `employee_checkin.py` validate/before_validate: none touches Attendance). |

**What this table says, in plain words**

- A person's direct edit of a day record is **A16 to A19, A21 to A26** (and A27 in effect). A20 is not in force.
- The system's own work **uses the same document layer** as the person (A1, A3, A6, A8, A9), and often runs in a person's own web request (A2, A6, A8, A9, A14). So the **only** reliable difference is the door the work came in by.
- The paths that already bypass hooks (A4, A5, A7, A10 to A12, A14, A15, and the half-day tick in A24) are invisible to any document hook. For the system ones that is the gift. For A10 it is the gift (it is already listed through the request). For the half-day tick it is a hole.

### 1.4 Who is affected (persona impact)

- **HR Manager / HR User:** new reason box on the Attendance form, and on cancel a two-step (section 3.6). Bulk tools that cannot ask a reason will refuse some rows.
- **CXO:** sees the same notice rows for the companies in scope; no change in what they can open (the log's read rights and `punch_change_query_conditions` are reused).
- **Employee:** the notice lists the day change and the reason. A worker without the app sees it on paper. The employee's own view already draws `what` and `why` through `gpEsc` (`portal.js:7787`, proven).
- **Manager:** holds no HR role; not a door user for Attendance. Managers' punch fixes are already on the notice.

### 1.5 Callers of what I would change (counts)

| Thing | Callers | Count and how |
|---|---|---|
| `punch_change._valid_reason` | `require_reason`, `write_log` (both in `punch_change.py`) | 2 (proven, grep) |
| `punch_change.require_reason`, `write_log`, `refuse_delete` | `hooks.py` Employee Checkin only | 3 hook lines |
| `register_notice.sheet_rows`, `_content_hash` | `open_notices`, `_write_the_notice`/`record`, tests | read at build; **the file is being edited by the page-count engineer** |
| The log DocType JSON (`punch` required, reason options) | `punch_change.write_log`, `register_notice._punch_changes`, tests `test_punch_change_088c`, `test_register_notice_088` | 4 files (grep at build) |
| Attendance `doc_events` in `hooks.py` | one block, lines 180-203 | 7 events already registered by 085 and the engine |
| Tests that create Attendance rows | `alvoraa_portal` 24 files, `hrms` 14, `alvoraa_goals` 0 | proven by grep (`"doctype": "Attendance"`, `new_doc("Attendance")`, `doctype="Attendance"`, `mark_attendance(`, `get_doc("Attendance"`). With the switch off by default the new handlers return at once, so only suites that tick `alvoraa_print_change_notices` can feel them: `test_register_notice_088` and `test_punch_change_088c` (inferred) |

### 1.6 Seven non-functional verdicts, for the proposed change

| Dimension | Verdict | One line |
|---|---|---|
| Performance | **neutral off, small cost on** | A hook on a hot table; see 1.7 |
| Security | **improves** | Server-side demand; the free text and Data Import hole (F3) closed; refusals logged like 088c |
| Reliability | **degrades slightly, and this is the main risk** | A wrong "door" answer either refuses leave or approval work, or misses a change. Section 3.3 |
| Scalability | **neutral** | Door test is in memory; one indexed read only on a person's replace-or-cancel |
| Maintainability | **neutral to slightly worse** | One door list to keep correct; it is one constant, pinned by a path-table test |
| Data integrity | **improves** | The log row and the Attendance save are in one transaction (as 088c) |
| Compliance / privacy | **improves, with one new exposure** | Free text can hold personal detail; capped, escaped, retained like the log (section 4) |

### 1.7 Performance, specifically (Attendance is written in bulk)

- **Volume the hook sees (inferred):** DTC has about 442 people (memory: "all 442 ticked"). That is about 13,000 Attendance rows in a 30-day month from the hourly job, plus the leave and request writes. Every one passes through the handlers.
- **Cost per row, switch off:** the handler returns after (1) an in-memory look at `frappe.form_dict.cmd` and `frappe.local.job`, then (2) one cached Company read, the same cached read 088c uses (`notices_are_on`: cached value, 0 queries when warm, per 088c notes). Nothing else. **Expected: 0 extra queries, microseconds.** Not yet measured.
- **Cost per row, switch on, system path:** the same two steps and out. The door test comes first, so a system row never costs a query.
- **Cost per row, switch on, a person at a door:** a replace test (`frappe.db.exists` on a cancelled row for the same employee and date, 1 query) and the log insert. Rare and human-paced.
- **Month-end:** payroll and the engine write derived fields with `set_value` (A14), which fires nothing, so the payroll run itself adds **zero** hook calls.
- **How I will measure it:** in a test on my own stack, run 1,000 inserts of `attendance.mark_attendance` (the auto path's own function) with the handlers registered and with them removed; assert **the same query count at 20 rows and at 1,000** (the `nfr-budget.md` gate, line 64) and record the wall time for both. Number to be written into `03d` from the run, not guessed.

---

## 2. Rung of the ladder (`no-over-engineering.md`)

**Rung 4 (new code) plus two small edits to the existing log DocType and one Custom Field.** No new DocType, no new app, no flag.

| Rung | Why it is rejected |
|---|---|
| 1 Already there | Frappe's `track_changes` writes a Version row (who, when, diff) for document saves, and HRMS writes an "Info" Comment for a request-made change (`attendance_request.py:180`). Neither holds a reason, neither can be printed as a sentence the employee reads, neither is append-only, and both **miss every `set_value` / `db_set` / `qb.update` path** (A4 to A12, A14, A15, A24). |
| 2 Configuration | No setting asks for a reason. |
| 3 Customisation alone | A Custom Field with `mandatory_depends_on` demands a reason in the Desk form only. Import, REST, bulk tools and Cancel (no field values on cancel) would walk past it. |
| 5 New DocType (`Alvoraa Day Change`) | See 3.2. It would copy the log's permissions, append-only guards, scope function, notice link field and tests for no gain. |

---

## 3. Step 2, strategy

### 3.1 What counts as a material change to a day record

The rule has two halves, because a day record is only "in force" when it is submitted (payroll reads `docstatus == 1` only: `salary_slip.py:826`, `:662`, proven). **A draft is not a change to the employee's record, so a draft save is never listed and never refused.**

| Act | Listed? | Why |
|---|---|---|
| A person **submits a row that replaces** an earlier one (amended, or a cancelled row exists for the same employee and date) | **Yes**, with the old and new status | The employee's day was changed by hand. `status`, `leave_type`, `half_day_status` all move pay (1.2). The sentence names the status that moved. |
| A person **updates a submitted row** (the confirm fields, or any change at all) | **Yes** | After submit the only fields a person can change are the `allow_on_submit` ones (1.1). So at a door **any** difference counts; no field list to keep. Confirm fields move pay. |
| A person **cancels a submitted row** | **Yes**, with the reason picked first (3.6) | The day goes from a record to none; the hourly job re-marks it from the punches (inferred). |
| A person **marks a day that has never had a row** (Mark Attendance, Employee Attendance Tool, a new form) | **No (Q1, recommended)** | That is making the record, not changing it. Surbhi's words are "updating the day's record". Listing it would put every manually marked day of a tenant on paper. |
| The system's own writes (A1 to A9, A12 to A15, A30) | **No** | Not a person's decision. |
| A person's trigger of a system write (A2, A6 to A9, A14) | **No** | The record is the Leave Application, the Request, the Shift Type. |
| 087 punch fix (A10) | **Already listed**, once | See 3.4. |
| `employee` or `attendance_date` changed on a draft | not applicable | A draft is not in force. After submit these cannot change. (A "move to another person" cannot happen to a submitted row, so no new refusal is needed. Inferred from the `validate_update_after_submit` rule, `base_document.py:1278`.) |

### 3.2 One log or two: **one**

Recommendation: **reuse `Alvoraa Punch Change`.** Straight answer, with the cost of two:

- The notice already reads this log by `employee` and `day` (`register_notice._punch_changes:250-282`), prints `what` and `reason_code`, links rows through the notice child's `punch_change` field, scopes with `punch_change_query_conditions`, and signs and hashes them. A day-record entry is a row with the same shape: who, which day, what (one sentence), reason. **The notice side needs no new query and no new child field.**
- A second DocType means a second set of permissions, append-only guards, scope function, hooks, notice link field, hash branch, `TENANT_DOCTYPES` entry (the `test_invoicing` gate failed on exactly that last time, 03c) and tests. I cannot name anything it buys.
- The cost of one: the name says "Punch". I would **not rename it** (a rename touches every reference and a migration; the DocType holds zero rows on every production site). I add the word to the description and leave the name. **Acceptable simplification.**

Schema edits to the log (zero rows exist anywhere, per the standing facts, so no migration of data):
1. `punch` stops being required (a row has either a punch or an `attendance`). Add `attendance` (Data, read-only, the Attendance's name; text, not a Link, so the row outlives the document, as `punch` does).
2. Add `reason_text` (see section 4).
3. The last reason option changes from `Other (details are in the HR file)` to `Other` (the old wording says there is no text box, which stops being true).

### 3.3 How the system is told from the person: the door

**Recommendation: a positive list of doors, not a test of the user.** Why not the other way:

| Way to tell | Fails because |
|---|---|
| By session user | Scheduler is `Administrator`, and a person approving leave is a person (section 0, items 2 and 4) |
| "Is there a web request?" | A2, A6, A8, A9, A14 all run in a person's web request |
| "Does the document have a cause link?" (`leave_application`, `attendance_request`) | Auto attendance rows have no link, and a person's hand-made row has none either |
| A deny-list of system writers that set a flag | Needs edits inside stock `hrms` files (`leave_application.py`, `attendance_request.py`, `shift_type.py`): upstream code, not allowed without escalation |
| **Allow-list of doors** | Needs no stock edit. A wrong "no" misses a notice line (silent, but pinned by tests). A wrong "yes" refuses a system path (loud, and tests pin every system path as not refused). |

**A door is: the request or job was addressed to the Attendance itself.** One function, one constant, checked in this order (cheapest first):

| Door | How it is recognised | Status |
|---|---|---|
| Desk form save, submit, update | `form_dict.cmd == "frappe.desk.form.save.savedocs"` and the posted doc's `doctype == "Attendance"` | `cmd` read is the same one 088c already uses (`punch_change.py`, `form_dict.get("cmd")`, proven); posted-doc parse is inferred |
| Desk cancel and discard | `cmd == "frappe.desk.form.save.cancel"` and `form_dict.doctype == "Attendance"` | inferred |
| `frappe.client.*` (7 functions, A21) | `cmd` starts with `frappe.client.` and `form_dict.doctype == "Attendance"`, or the posted doc is Attendance | inferred |
| REST resource | request path begins `/api/resource/Attendance` (v1) or `/api/v2/document/Attendance` (v2) | **not checked**; I did not read how Frappe exposes the path |
| List bulk update | `cmd` ends `submit_cancel_or_update_docs`, `form_dict.doctype == "Attendance"`; and the job it queues (`frappe.local.job.kwargs`) | `frappe.local.job` has `method` and `kwargs` (`background_jobs.py:260-267`, proven); inferred for this job |
| `mark_bulk_attendance`, `mark_employee_attendance`, `upload_attendance.upload` | `cmd` equals the dotted name; and the queued jobs by `frappe.local.job.method` | names proven (A23 to A25); the job-side check is inferred |
| Data Import | `frappe.flags.in_import` and the Data Import's reference doctype is Attendance | flag proven (`importer.py:74`); the reference lookup is inferred |

If the list grows or Frappe moves a door, **a path-table test fails**: the test drives each row of 1.3 and asserts listed or not listed (section 6). That test, not the list, is the safety.

A person at a door is then judged the same way 088c judges a punch: not a machine account, not Guest, not the employee's own login (`punch_change._is_a_persons_change`, reused as it stands). Administrator at a door counts (Surbhi, Q2). **Administrator in a script is not at a door and is not listed** (A27, A29; Question 5).

### 3.4 Double reporting

- **The 087 path (A10): one act, one line, by construction.** `punch_fix.apply` writes the punches under `in_punch_fix_apply` (088c exempts that flag, `punch_change.py:68`) and the day with `frappe.db.set_value`, which fires no Attendance hook. The request is the only entry, and it already prints "This day now counts X" from the snapshot (`register_notice._counts_after`). 088d adds nothing to this path, and a test pins it (a person approves a punch fix with the switch on: exactly one notice entry).
- **Machine release and verdict writes (A12, A14): no entry**, same reason.
- **The Desk case is two acts, not one.** HR edits a punch (A31, logged by 088c) and the day does **not** follow (checked, A31). To make the day follow, HR cancels the row (A18) so the hourly job re-marks it. That is a second human act and gets its own line, worded as a consequence, not a second event (section 5): *"Day record reset so it is worked out again from your punches (was Absent)"*, with the same reason. I **do not recommend merging** the two lines. A merge needs a rule such as "same person, same day, any earlier time", and a wrong match **hides** a real change, which is the worse error. Question 4.
- **Check for a repeat entry inside one human act:** `on_submit` and `on_update` both fire on a submit. The writer logs on `on_submit` (new or replacement), `on_update_after_submit` and `on_cancel` only, never `on_update`, so one act writes one row. Pinned by a test.

### 3.5 What would start being refused, and what breaks

While the switch is on, for a person at a door:

| HR does today | After 088d |
|---|---|
| Opens a submitted day, ticks "Out Time Confirmed", Update | Needs a reason picked in the same save. Refused with "Pick a reason..." |
| Cancels a day from Desk or the list | Needs the reason picked first and saved with Update (3.6), else refused with a sentence that says how |
| Amends a day | The replacement needs a reason at submit |
| Marks a day that never had a row | **Unchanged** (Q1) |
| Re-marks a day whose row HR cancelled, through **Mark Attendance** or the **Employee Attendance Tool** | The tools have nowhere to ask for a reason, so the replacement is refused. **Dead button for that case**, like 088c's "Fetch Shift". Worse: the list button swallows the refusal and still says "Attendance marked successfully" (section 0, item 5). The fix is one sentence in the release note, and I recommend a test that proves the message so nobody is surprised. |
| Approves leave, approves or cancels a request, clicks Shift Type "Mark Attendance", clicks Reprocess | **Unchanged**, and pinned as such by tests (A2, A6, A8, A9, A14) |
| Imports Attendance (Upload or Data Import) | Needs the reason columns on every replacing row |
| Employee Attendance Tool half-day tick | Hook-less today and after. Q8 |

Features in the blast radius: Attendance form and list (`attendance_list_held.js`), Employee Attendance Tool, Upload Attendance, Shift Type button, leave approval, Attendance Request approval and cancel, 085 held-day release (A12), 086 bulk held fixes (they file requests, A10 path), 087 punch fix and undo, the payroll engine and reprocess, `alv291`. Suites to run: `test_attendance_doors_085`, `test_held_day_085`, `test_held_team_086`, `test_punch_fix_087` and `_proof`, `test_attendance_correction`, `test_attendance_request_shift_346`, `test_payroll_reprocess`, `test_alv291_attendance_fix`, `test_company_scope_085`, `test_leave_063_card_cancel`, `test_register_notice_088`, `test_punch_change_088c`, `test_portal_security_010` (ceiling rows), `test_invoicing` (tenant doctype list), and the `hrms` Attendance tests. One at a time, own stack, per `usage-discipline.md`.

### 3.6 The reason on the Attendance form, and why cancel is two steps

- **Where it is asked:** one Custom Field on Attendance, `alvoraa_change_reason` (Select, same options read from the log DocType in `after_migrate`, exactly the 088c pattern for Employee Checkin), `allow_on_submit`, and `reason_text` beside it. Both are blank once the row is logged.
- **When it is demanded:** on submit of a replacement (`before_validate`: it runs for save and submit, `document.py:1404`) and on update after submit (`before_update_after_submit`). **088c's `before_validate`-only pattern does not transfer on its own:** `before_validate` does **not** run for cancel or update-after-submit (proven, `document.py:1404-1419`), and `before_cancel` / `before_update_after_submit` are skipped under `ignore_validate` (proven, `:1407`). That is fine for a person at a door (they do not set `ignore_validate`); a script that does is not at a door anyway.
- **Why cancel is two steps:** Desk's Cancel sends only the doctype and name (`save.py:53-66`), so it cannot carry a reason. The only way to have a reason at the moment of cancel is to have saved it on the row first (it is `allow_on_submit`): pick the reason, click Update, then Cancel. The refusal sentence says exactly that. The reason is cleared from the cancelled row after logging with `frappe.db.set_value(..., update_modified=False)`. This is clumsy, and Question 2 offers the alternatives.
- **On a draft** the reason field is not blanked (otherwise HR picks it, saves, and has to pick again at submit); it is blanked when the row is submitted and logged.

### 3.7 Does a day-record change hold pay?

**Recommend no, the same as punch changes (Surbhi, 25 Nov, "notice only, no pay hold").** Reasons: (1) the notice stays information, not a gate; (2) the only hold in the system is 087's, tied to an employee Confirm on a request (`punch_fix.refuse_slip_while_unconfirmed`), and a hold on every hand edit would stall payroll on exactly the days HR is correcting; (3) counsel has not asked for it. **The difference to say out loud:** a day change can be **adverse** (Present to Absent cuts pay) where a punch correction is usually in the employee's favour, and the employee would learn of it from the monthly paper after the slip. Counsel was asked about gating (01d Q4) and has not answered. Question 6.

---

## 4. The free-text reason, and finding F3

**Rule:** the reason is one of the fixed list. Only the code **"Other"** may carry text, and "Other" **must** carry text.

| Question | Answer |
|---|---|
| Where it lives | `reason_text` on the log row; the same-named Custom Field on Attendance and on Employee Checkin (blank once saved). One new field per place, no new DocType. |
| Type and size | Data, **100 characters**, one line, spaces collapsed, control characters and line breaks removed. 100 is a proposal: `PER_PAGE = 5` was checked on a printer with the longest *code* (about 51 characters, "Employee was on approved duty away from the machine"), not with free text. **A real print with a 100-character line is not checked.** Lower it if five rows no longer fit. |
| Required | Non-blank after trimming, when the code is "Other". |
| Forbidden | Any text with any code other than "Other". |
| Stored as typed, shown escaped | Not stripped of angle brackets, so the record says what the person wrote. The printed sheet and the employee's own view already draw `why` through `gpEsc` (`portal.js:7083`, `:7787`, proven); the server returns it as text and never as markup. A test with `<img onerror=...>` in the text asserts it appears as text on both. |
| What the printed line says | `why` = `Other: <the text>`. One extra branch in `register_notice.sheet_rows`. |
| In the content hash | Included, so a later change is detectable (the hash is a SHA-256 of the text, not the text). |
| Who may read it | Same as the log: HR User, HR Manager, System Manager, scoped by `punch_change_query_conditions`; the employee sees it on their own notice. Not `in_list_view`. Never in a log line: log lines carry document names only. |
| Retention | Same as the log (5 years maximum, Surbhi 25 Nov; the expiry job is still its own ticket). |
| Personal-data risk | HR may type a name or a medical reason. The field's description says: *"Do not write medical details or the names of other people."* A hint is not a control; it is the cheapest one that exists. Counsel should see this. |
| Counsel | Counsel asked for a **reason code** (01d, line 25). "Other" plus text is still a code plus text. **Not checked with counsel; Question 7.** |

### 4.1 Closing F3 and the free text together

F3 (06c): a Data Import skips Frappe's Select check because `_validate_selects` returns at once when `frappe.flags.in_import` (`base_document.py:1102`, proven). 088c closed the reason **code** (`_valid_reason`, called in `require_reason` and again in `write_log`). Free text re-opens the same door, so the same two places must check the **pair**:

1. `reason_code` is in the log's own option list (as today).
2. `reason_text` is empty unless the code is exactly "Other"; non-empty and within 100 characters when it is.

Our checks are our own hooks, so they run under import (Frappe skips only its own Select validation). Put them in **one shared function**, called from `require_reason` (punches), the new Attendance handler and `write_log`, so a punch import and a day import cannot differ. That is not an abstraction for a third use: it replaces `_valid_reason`, which already has two callers, with the same function taking one more argument.

**What the person uploading sees:** Data Import lists the error against the row. The messages say what to do, in plain words:

- *"This row has text in 'Reason Text' but the reason is not 'Other'. Clear the text, or set the reason to 'Other'."*
- *"The reason is 'Other', so say what happened in 'Reason Text' (up to 100 characters)."*
- *"That is not one of the reasons on the list. Use one of the listed reasons."* (the 088c sentence)

Whether Data Import prints the row number beside our message: **inferred, not run**. A real Data Import file was not driven in 088c either (03c, "Not tested"); I will drive one for both punches and Attendance in 088d.

---

## 5. The sentences the employee reads

These go in `what`, English only, never through `_()` (the paper is English by Surbhi's 21 Nov decision, `register_notice.WHAT`). Same register as today's "Out time 18:30 added".

| Case | Sentence on the paper | Reason column |
|---|---|---|
| A person replaced the day | **Day changed from Absent to Present** | `Employee forgot to punch` |
| Replacement, the status unchanged but something else moved (leave type, half-day, shift) | **Day changed: leave type, half day** (names only the fields that moved, from a short fixed list of labels) | reason |
| The day was reset | **Day record reset so it is worked out again from your punches (was Absent)** | reason |
| Held day confirmed by hand | **Out time confirmed as 18:30 for a day with a missing punch** | reason |
| Any other change after submit | **Day record changed** (never empty; a record needs a sentence, as 088c learned in R-2) | reason |
| Reason "Other" | the reason column reads **Other: Machine was being repaired** | |

The words use the status values Frappe HR already shows the employee ("Present", "Absent", "Half Day", "On Leave"). **"Held" is our own status;** the paper should say "not yet decided" where it appears. I would show Surbhi this one row before build.

---

## 6. Tests this needs (before I write the code)

1. **The path table is the test.** One test per row of 1.3 that touches a hook (A1, A3, A6, A8, A9, A12 to A19, A21 to A26): switch on, drive the real function, assert **listed or not listed**, and for every system and system-triggered row that it is **not refused**. Without this the door list is a guess.
2. **Break tests, each undone on purpose** (commit first, per the rule): door test always true (expect: leave approval refused), always false (expect: Desk replacement unlisted), reason demand removed, text-with-wrong-code check removed (under `in_import`), text length cap removed, `on_update` logging instead of `on_submit` (expect: two rows per submit), replace test removed (expect: every first mark listed).
3. **Persona tests** read as each role (CXO, HR with and without entitlement, employee), like 088c's scope tests.
4. **F3:** a Data Import with free text under a non-"Other" code is refused for punches and for Attendance, in one run each, after a control proving Frappe would have accepted it.
5. **Pin** that a person approving a punch fix writes exactly one notice entry (3.4).
6. **Release-note test:** the bulk list button's swallowed refusal (section 0, item 5) shows the sentence, or the note says it will not.
7. **Cost:** query count equal at 20 and 1,000 rows (1.7).
8. Run: the suites in 3.5, `scripts/check_app_integrity.py`, `scripts/check_brand_spelling.py`, `test_invoicing`.

---

## 7. Volume on paper

- Known: **3,322** changes in the period 01d measured (2,007 punches + 1,315 Attendance rows; 01d line 145 gives "0 of 3,322"). A page holds 5 (`PER_PAGE = 5`, `register_notice.py:430`).
- **The headcount in the documents disagrees:** 00b §11 says "about 600 people", giving 5.5 each; 06c line 236 says "about 440 people" (DTC has 442 ticked, memory), giving about 7.5 each. I use both.
- **Punches alone (088c):** 2,007 over 440 people is about 4.6 each, over 600 about 3.3. Typically one page, with the busy people on two.
- **Punches plus every Attendance change (the figure Surbhi quoted):** about 5.5 to 7.5 each. **A typical person crosses 5, so two pages becomes ordinary.** Evenly spread, that is roughly 665 sheets as a floor (3,322 / 5) and more in practice, since a person with 6 changes still takes 2. The real spread is **not known** (no per-person counts; no site access this session).
- **But the 1,315 is probably inflated as a measure of this slice** (section 0, item 3): it includes the scheduler's own work, which 088d never lists. And first-time marks are not listed (Q1). So the listed volume should come **below** 3,322. I cannot say by how much.
- **Therefore:** keep Surbhi's decision ("ship and measure one month"). Two additions that cost nothing: count **log rows per person per month and pages printed**, split into punch rows and day rows (the new `attendance` field makes the split a simple filter), so the next decision rests on numbers.
- **Hard dependency:** a two-page notice **cannot be recorded** until the page-count fix lands. With day records on, two pages is ordinary, so **nobody ticks the switch on any tenant before it**. Already so in 00b Q9; stronger now.

---

## 8. Parallel-work check

| File I will change | Hot? | Who else is in it |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/hooks.py` (Attendance `doc_events` block, `after_migrate`) | **Yes** | Several rows on the work board touch it (alv-318, 082, 084 etc.; board entries are from early to mid November and may be stale). Read `origin/dev` again before I edit. |
| `register_notice.py` (`sheet_rows` one branch, `_content_hash` one field) | Yes (965+ lines, 1038 now) | **The 088 page-count engineer is editing it now** (worktrees `088-pagecount`, `release-088-alv436` exist). **Sequence: the page-count fix goes first; I rebase and then make a three-line change.** I do not edit it before then. |
| `punch_change.py` (one shared reason check; `_valid_reason` gains the text rule) | No | 088c's own file |
| `alvoraa_punch_change.json` (2 fields, `punch` not required, "Other" label) | DocType JSON (hot) | nobody known |
| New `day_change.py`, new `test_day_change_088d.py`, Custom Fields via `after_migrate` | new | none |
| `en.csv` | no | none |

Other sessions running now (containers `pc088-*`, `alv469-*`, `alv090-*` and others are up): I touched **none**. **Not checked:** `git status` of the main checkout and the uncommitted work of other sessions; I read only `origin/dev`.

**What came in from others:** nothing to absorb. My worktree starts at `origin/dev` e82bb3f0, and `git fetch` brought no commits beyond what I branched from.

Pin tests that guard what I touch: `test_punch_change_088c` (the existing punch rules), `test_register_notice_088`, `test_attendance_doors_085` (the existing Attendance hooks) and the new path-table test.

---

## 9. What I could not check

1. **No real run of anything.** No site, no bench, no containers other than the one I made and removed to read Frappe's source. Everything marked "inferred" is reading, not running.
2. **The REST doors** (v1 and v2 paths) and what `form_dict` holds inside a Data Import job, a bulk-update job and a `mark_bulk_attendance` job. I proved that `frappe.local.job` carries `method` and `kwargs`; I did not read what each job is queued with.
3. **Whether the server refuses a REST write to a read-only `allow_on_submit` field.** If it does not, a person with API access can edit the engine's verdict fields (a money path) with no hook seeing it as anything but an update after submit. That would be covered by "any change after submit counts" at a door, but it is a finding on its own.
4. **Frappe `erpnext`** was copied but not searched for Attendance writers.
5. **`frappe/` itself** was read for the document lifecycle, `save.py`, `client.py`, `bulk_update`, `data_import/importer.py` and the Select check only. Other core writers (workflow actions, "Assign to") were not searched.
6. **How HR actually corrects days in Desk today** (cancel and amend, or the tool, or the request). I cannot count it without production access, and the instruction was not to touch it. This decides how often the two-step cancel and the dead tool buttons bite.
7. **Who files plain Attendance Requests** (HR on the employee's behalf, or the employee): Q3.
8. **A real print of a 100-character free-text line.**
9. **Whether the scheduler in production passes a user** to the queue (inferred it does not).
10. **The `hrms` in the image `dev-3830ed3` against the in-repo fork:** I read the repo's `hrms`; I did not diff the two.
11. **Production counts** (people per notice, per-person change counts).

---

## 10. Questions for Surbhi, each with my recommendation

1. **First-time manual marking of a day (Mark Attendance, Employee Attendance Tool, a new Attendance form, an Upload): on the notice?** Recommend **no**. It makes the record; it does not update one. Listed only when it replaces a cancelled or amended row. Reason: a tenant that marks attendance by hand would print every day of every person every month. Ask counsel in the same message as Q7.
2. **Cancelling a day by hand needs a reason, and Desk's Cancel cannot take one.** Three ways: **(a, recommended)** pick the reason, click Update, then Cancel (clumsy, complete, nothing refused for good); (b) refuse a person's cancel and send HR to a request (kills the only way to make a day follow corrected punches, A18); (c) allow cancel with no reason and list only the replacement (a known hole against counsel's "every edit has a reason").
3. **Plain Attendance Requests (work from home, on duty, half day) filed by HR for an employee** change the day too, carry the request's own reason and an approval, and are **not on the notice** (only punch fixes are, `register_notice._request_changes`). Recommend **leave out now**: they are not "direct edits" and they have their own record. First **count** how many are HR-filed on each tenant (a read-only count I have not run). Grace holds 137 requests and no punch fixes (memory, 23 Nov). If many are HR-filed, this becomes its own small change.
4. **HR edits a punch, then cancels the day to make it follow: two lines or one?** Recommend **two lines**, worded as cause and consequence (section 5). One line needs a "same person, same day" match that can hide a real change. The cost is one extra line on the paper for those days.
5. **Repair scripts run by Administrator on the server (A27, A29, `alv291`) are not at a door and are not listed.** Recommend **accept and write it in the runbook**, as 088c did for punches (P13, P14). The alternative is a logging call inside each script, built the first time one is run again after switch-on.
6. **Does a day-record change hold pay?** Recommend **no**, as for punches. Say so to counsel with the one new fact: a day change can cut pay (Present to Absent), and the employee learns of it from the monthly paper.
7. **Free text under "Other".** Recommend **100 characters, one line, a "no medical details or other people's names" hint, "Other" must carry text and nothing else may.** Counsel asked for a reason **code**; send counsel the one-line change. The reason list itself is still **not legal's** (03c, first line): the "Other" label changes.
8. **The Employee Attendance Tool's half-day tick changes pay fields on existing rows with no hook at all (A24).** Two ways: **(a, recommended)** while the switch is on, refuse that tick with one sentence and send HR to the form; one small wrapper (`override_whitelisted_methods`, to be verified in `hooks.py` at build) ; or (b) accept it as an unlisted path and say so in the runbook. I recommend (a) because it is a **direct edit that cannot be seen by design**.
9. **Order of work.** The page-count fix first; 088d starts only after it lands on `dev` and `register_notice.py` is quiet. I make no edit to that file before then. Also: nobody ticks the switch on any tenant until both are live.
10. **Name.** The log keeps the name `Alvoraa Punch Change`. Fine, or do you want it renamed (cost: every reference, one migration, zero data)?

---

## 11. Subtract pass: what I considered and left out

- **A second DocType** for day changes (3.2).
- **A before-and-after snapshot** on the log. The sentence is enough; 087's snapshots are its own.
- **A generic "classify the writer" framework**, a registry of doors, or a base class. One tuple of doors and one function.
- **A flag set inside stock `hrms` files** to mark system writes (upstream edit, escalation).
- **Merging or suppressing** the reset line (Q4), and **grouping** day changes into a summary line (Surbhi decided to measure first).
- **A pay hold** (3.7). **A backfill or any migration that invents reasons** (not proposed; October untouched).
- **A reason list for days that differs from the one for punches.** One list.
- **An HTML sanitiser or text library.** Escape on output is the control; a length cap and whitespace collapse are one line each.
- **Employee notifications** for a day change. Not asked.
- **Refusing cancel and delete** outright (Q2b).
- **Listing system triggers** (leave, requests, Shift Type, Reprocess) in any form.
- **A cache, an index, a job.** One indexed read already exists (`employee, day`); I add none. Nothing has measured a miss.

Removed on this pass: a draft idea to log on every Attendance `on_update` (it writes a row for a draft and again at submit), and a draft rule "list when `docstatus` changes" (it lists the system's rows).

---

## 12. Files the build will touch (for the work board, after approval)

`alvoraa_portal/alvoraa_portal/day_change.py` (new), `punch_change.py` (shared reason check), `hooks.py` (Attendance block: `before_validate`, `before_update_after_submit` +1, `before_cancel` +1, `on_submit` +1, `on_update_after_submit`, `on_cancel`; `after_migrate`), `alvoraa_punch_change.json` and its controller (fields and guard), `register_notice.py` (after the page-count fix), `tests/test_day_change_088d.py` (new), `tests/test_portal_security_010.py` (ceiling row for `day_change.py`), `subscription.py` only if a new doctype appeared (none does). Implementation notes go in `03d-implementation-notes.md`.

**Waiting for your answers to 1 to 10, and your word on the strategy, before any code is written.**
