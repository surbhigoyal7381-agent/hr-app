# ALV-328 - Impact analysis and strategy

| | |
|---|---|
| Slice | ALV-328, now with ALV-332 and ALV-333 (Surbhi's yes, 12 Nov 2026) |
| Step | `/slice-build` step 1: impact analysis and strategy. **No feature code written.** |
| Author | `hrms-fullstack-engineer`, 12 Nov 2026 |
| Worktree | `.claude/worktrees/alv-328`, branch `slice/alv-328-break-and-reason`, on `origin/dev` `75149184` |
| Reads | `01-product-brief.md`, `02-design.md`, `prototype.html` (by its parity table), `03-security-privacy.md` incl. Re-check and both answer sections, `03-devops.md` incl. Re-check, `04-functional-spec.md` incl. Q-A..D |
| Next | Surbhi approves, adjusts or redirects this strategy. Then the build, on my own containers only |

## Bad news first

1. **Managers will lose the right to add a punch for their direct reports.** Today any
   manager (and DTC's 5 Location Managers, if they have an employee record) can create,
   edit and delete a direct report's punch, because `checkin_has_permission` says yes to
   every right. ALV-332/333 close edit and delete, as you asked. Your rule "staff may
   create their own new punch" also closes **creating a punch for someone else**. The
   DTC check counted edits and deletes, not creates. **I need one more read-only count
   on DTC before release** (section 12, count E), and your decision D1.
2. **There is a third copy of the break sum** that the spec did not list: the home
   banner, `day_marks._break_over` (line 192), added by ALV-326. AC-17 says one copy, so
   the plan changes that line too. It is a one-line change, covered by `test_day_marks`.
3. **The main checkout cannot be used to test this.** Its local `dev` is at `5aa654d2`,
   426 commits behind `origin/dev`, and it holds another session's uncommitted edits in
   six of my files (`attendance_correction.py`, `attendance_analytics.py`,
   `payroll_rules.py`, `payroll_rules_apply.py`, `portal.js`, `panels.css`). So the shared bench `hrlocal-bench` does not run ALV-326 either. I will
   test in my own throwaway containers, as ALV-326 did (`hrlocal-326`, now stopped).
4. **`.claude/context/data-doors.md` is untracked in the main checkout**, so it is not in
   git and not in my worktree. I read it from the main checkout. It should be committed
   by whoever wrote it; I have left it alone.

## 0 · Where this was done, and what came in

- Worktree created from `origin/dev` `3665700c`, then rebased onto `75149184` on the
  coordinator's word. **Came in, from other sessions, tests only:**
  - `6232a09e` ALV-309: `tests/test_inbox_counts_034.py` (counts "three more than there
    were").
  - `75149184` `tests/test_install_hooks_parity.py` (new): every job in `after_migrate`
    must also be in `after_install`. **This affects me**: my new field must be created on
    install as well. The plan uses a function already in both lists, so it passes.
  - Before that, `f2136622` and `3665700c` ALV-329: `test_grooming_066.py`,
    `test_grooming_erase_066.py` (grooming tests and a midnight bug pin). Not my files.
- Slice docs copied from `.claude/worktrees/alv-326` into this worktree, untracked.
  `alv-326-shift-hours/06-review.md` and `06-security.md` were **not** copied.
- Frappe on the bench is `v16.33.1`. Every Frappe behaviour below was read in that
  source, read-only, inside `hrlocal-bench`. One read-only `SELECT` was run on
  `ppj.localhost` to prove MariaDB 10.8 accepts the SQL shape in section 5.

## 1 · Cross-module reach

| App | Touched? | How |
|---|---|---|
| `alvoraa_portal` | **Yes** | 8 files, listed in section 9 |
| `hrms` | Read only | `Employee Checkin`, `Attendance`, `Shift Type`, `HR Settings` (one Custom Field, no upstream edit) |
| `erpnext` | No | `Employee` read as today |
| `frappe` | No | |
| `alvoraa_goals` | No, but shares a hook | Its `review_items.validate_hr_settings` runs on the same HR Settings save. My guard only throws for my field, so the two stay independent |
| `alvox_compensation` | No | |

## 2 · Every caller of every function I will change

| Function | Callers (grep, outside tests unless said) | Effect of my change |
|---|---|---|
| `field_app_access.checkin_query_conditions` | `hooks.py:491` (every list, report, `get_list`, `get_count`, link search on Employee Checkin); `field_checkin.py:77` re-export; tests `test_field_app_step1_013` (names resolve), `test_alv302_sync_punch` | Same answer with the switch off (self + Active direct reports), now as one subquery instead of a Python list. Wider with it on |
| `field_app_access.checkin_has_permission` | `hooks.py:507` (every `has_permission` on one punch: REST get/put/delete, `frappe.client.*`, Desk form, delete_doc, rename, share, File download through the attached-to check); `field_checkin.py:76` re-export | **Behaviour change**: outside HR, only read/select, plus create of one's own new punch. Machine account unchanged |
| `field_app_access._viewer` | `checkin_query_conditions`, `checkin_has_permission`, `log_photo_view` | **Not changed.** HR = `HR Manager`, `HR User`, `System Manager`, `Administrator` |
| `payroll_rules_apply._punches` | `judge` (engine); `leave_rules.py:464, 485` (uses `[2]`, the count) | Internal refactor only. Return value unchanged, so `leave_rules` is unaffected |
| `payroll_rules._worked_percent` | `evaluate_day`, `_judge_other_half` | Internal: the sum moves into a shared helper. Same numbers |
| `payroll_rules.collapse_duplicate_punches` / `break_gaps` | `payroll_rules_apply`, `day_marks.py`, tests | **Not changed** |
| `day_marks._break_over` | `day_marks` home banner | The sum expression replaced by the shared helper. Same numbers |
| `attendance_correction.month()` | `portal.js:5486` (`acLoad`); tests in 5 files (`test_attendance_correction`, `test_grooming_cap_066`, `test_team_scope_259`, `test_late_minutes_017`, `test_grooming_066`) | New keys only, added; nothing removed or renamed |
| `attendance_correction._day()` | `month()` only | Two optional keys |
| `attendance_analytics.person()` | `portal.js:5189` (`aiPerson`); tests in `test_attendance_analytics`, `test_attendance_scope_012`, `test_hr_analytics_scope_012`, `test_own_record_permission_alv249` | New keys only, plus one Employee Checkin read |
| `field_app_settings.validate_hr_settings` | `hooks.py:390`; `test_field_app_step2_013` | A guard added at the top, before the early return |
| `field_app_settings.after_migrate` | `hooks.py` `after_migrate` **and** `after_install`; 3 tests | One more field in its list. Already in both lists, so `test_install_hooks_parity` stays green and `hooks.py` is not touched |
| `portal.js` `acRow`, `acPaint`, `acDetail`, `aiPerson` | the Attendance page and the Insights one-person view only | Additive drawing |

**Who writes or deletes Employee Checkin today, and whether the fix touches them:**

| Writer | How | Goes through `checkin_has_permission`? | After the fix |
|---|---|---|---|
| Field app check-in (`field_checkin.py:691`) | `insert(ignore_permissions=True)`, photo via `db_set` | No | Unchanged |
| Frappe HR phone app (`CheckInPanel.vue`) | `insert` as the person, own punch | Yes, `create`, new doc, own employee | **Allowed** |
| Biometric machine account (ALV-302) | `insert` as the machine, `create`, new doc | Yes | **Allowed**, same branch as today |
| Frappe HR auto-attendance, Attendance cancel | `frappe.qb.update` / `db.set_value` | No | Unchanged |
| `bulk_fetch_shift` (Frappe HR, Desk list action) | `doc.save()` | Yes, `write` | HR only (it is an HR action) |
| ALV-291 repair, photo purge | `db.set_value`, run as system jobs | No | Unchanged |
| HR in Desk or REST | `save`, `delete` | Yes | Unchanged: HR passes |
| A manager or Location Manager in Desk or REST | `save`, `delete`, `insert` for a report | Yes | **Refused** (ALV-332, and D1 for create) |
| A staff login editing or deleting their own punch | REST `PUT`/`DELETE` | Yes | **Refused** (ALV-333, closes W4/R4) |
| Tests | almost all use `ignore_permissions` or `db.*` | No | Run the whole suite to be sure |

**Roles you named that must keep working:** Biometric Sync keeps create. HR User, HR
Manager, System Manager pass as HR. Location Manager, the Payroll team and HR Data
Officer are **not** in `_viewer`'s HR list. Today they already get nothing on other
people's punches unless they hold one of the four HR roles or are the person's direct
manager. So the fix takes from them only what it takes from every manager. If one of
those roles needs to edit punches as a job, it must also hold HR User, or we add it to
the HR list (D2). Their Desk role rights (write, create) stay as rows; the hook can only
deny, never grant (`frappe/permissions.py:483-500`).

## 3 · Personas

| Persona | What changes |
|---|---|
| Employee | Sees their break per day and the stored reason on their Attendance page. **Can no longer edit or delete their own punches through the API** (ALV-333). Can still check in from any app |
| Direct manager | Sees a report's break and reason, same as the report. **Can no longer edit, delete or add a report's punch** (ALV-332, D1) |
| Skip-level manager | Switch off: nothing new (no punches, no break; still the reason text, as today). Switch on: punches (time, photo, place) and break for the whole Active line |
| HR Manager / HR User | Break on a person's Insights list and Attendance page. Cannot flip the switch. Punch rights unchanged |
| System Manager / CXO | Can flip the switch, with a Version row. No new group view |
| Machine account | Unchanged |

## 4 · HRMS domains

- **Attendance:** display of break and reason; punch write rights narrowed.
- **Payroll:** no figure changes. The engine refactor must give byte-identical reasons;
  `test_payroll_rules` and `test_shift_hours_alv326` pin that.
- **Org structure:** the reporting line decides punch visibility; the switch widens it.
- **Leaves:** a leave day shows no break. Half-day leave is measured, as the engine does.
- Appraisals, goals, compensation: none.

## 5 · The punch rule (ALV-328 setting, ALV-332, ALV-333)

**Rung: edit of existing code (4) plus one Custom Field (3).** Already-there and
configuration were rejected: Frappe HR ships no row rule for punches, and a Custom
DocPerm cannot say "read only for a manager, write for HR" on the same role, because
manager and staff share the Employee role.

One private function in `field_app_access.py` builds **one SQL subquery**: the people
whose punches a non-HR caller may read besides their own.

- Switch off: `select name from tabEmployee where reports_to = <me> and status = 'Active'`.
- Switch on: a recursive query over `reports_to`, Active at every level, `UNION` so a
  loop in the data ends. This is the same set as `_reports_to(me, deep=True)`.

Both hooks use that one text:

- `checkin_query_conditions`: `employee = <me> or employee in (<subquery>)`. HR returns
  `""` and no employee returns `1=0`, as today.
- `checkin_has_permission`, in this order:
  1. HR → yes, any right (unchanged).
  2. Machine account, `create`, new doc → yes (unchanged, ALV-302).
  3. No Active employee → no (unchanged).
  4. Own punch: `read` or `select` → yes; `create` on a new doc → yes; anything else
     (write, delete, share, print, email, `None`) → **no**.
  5. Someone else's punch: `read` or `select` and the person is in the subquery → yes
     (one parameterised query); anything else → **no**.

Why one subquery and not a list of IDs: `nfr-budget.md` §2 says a scope stays in the
database, never a list read into Python and sent back as `IN (...)`. With the switch on,
a top manager's line at DTC can be hundreds of people. MariaDB 10.8 runs on the bench,
dev, production and CI (compose files and `ci.yml`), and accepts this shape (one
read-only `SELECT` run on `ppj.localhost`).

**Why `None` is "no":** Frappe's Desk form asks with no right named
(`frappe/desk/form/load.py:123`). Saying no there only stops the form claiming extra
rights; the page still opens because the read check is separate, and Desk shows buttons
from the role rows, which the server then refuses. I checked `frappe/model/perm.js:86`.

**The switch.** HR Settings Custom Field `alvoraa_manager_sees_whole_line_punches`
(Check, default 0), added to the existing list in `field_app_settings.after_migrate`.
That function is already in `after_migrate` and `after_install`, so `hooks.py` is not
edited. Read with `frappe.db.get_single_value(..., cache=False)` inside a `try`; a
missing field or any error means off (PRIV-4). Read only for non-HR callers who have an
employee record, once per hook call.

**The guard (SEC-9).** At the top of `validate_hr_settings`, before its early return:
compare `cint` of the old and new value; if they differ and the user is not System
Manager or Administrator, `frappe.throw` with the spec's sentence, as a
`PermissionError`. It runs on every door that saves the document (Desk, REST,
`frappe.client.set_value`, `save`). History is HR Settings' own `track_changes` (SEC-10).

**What this does not change:** `log_photo_view` (SEC-11: only Desk opens are logged;
you accepted that, R3). The Employee role's rows on Employee Checkin. Attendance doors.

## 6 · The shared break helper

Two small pure functions in `payroll_rules.py`, and one function in
`payroll_rules_apply.py` that both screens call.

| Function | What it holds | Who calls it |
|---|---|---|
| `payroll_rules.punch_minutes(times)` | R2 + R3: whole minutes (seconds dropped), then `collapse_duplicate_punches` | engine `_punches`; `breaks_by_day` |
| `payroll_rules.minutes_on_break(gaps, start, end)` | R6: `sum(max(0, min(back, end) - max(out, start)))` | engine `_worked_percent`; home banner `day_marks._break_over`; `breaks_by_day` |
| `payroll_rules_apply.breaks_by_day(employee, company, days, times_by_date)` | R5, R7, R8 and the "when" rules of spec §5: enabled rule set, allowance > 0 (category, else rule set), not On Leave, shift known with length > 0, 0-2 punches = none, odd = not measured, even = minutes and over | `month()`, `person()` |

`breaks_by_day` reads the rule set once (`rule_set_for`), builds the engine's own context
once (`prepare`, which also gives the shift times the engine uses), and reads the
person's allowance once (`_employee_flags`). Then it loops over days in memory. It
returns the allowance and a dict per date, holding only keys that have a value.

**Why the window is safe to state on its own:** with "shift hours only" on, the engine's
window is `[max(counted_from, shift start), min(last punch, shift end)]`. Every break
starts after the first punch, so for the break sum this equals `[shift start,
min(last punch, shift end)]` whatever the grace. With it off, the window is the first to
last punch and clips nothing. So `breaks_by_day` does not need the grace. The
engine-match test (AC-13) proves it on the fixture month.

## 7 · Query plan

| Call | Today | After | Notes |
|---|---|---|---|
| `month()` Attendance read | 1 `get_list` | same query, 2 more fields | `alvoraa_rules_why`, `alvoraa_evaluated_on` |
| `month()` Employee Checkin | 1 `get_list` | **same 1**; times grouped by calendar date in the same loop | 0 extra |
| `month()` break context | - | about 4-5 queries, **once**, only if the person has punches and a rule set | `rule_set_for`, Shift Type list, holiday list (if set), green grants for one person, Employee flags |
| `person()` Employee Checkin | none | **1 `get_list`** for the whole range (max 12 months) | `checkin_query_conditions` applies |
| `person()` break context | - | same 4-5, once | plus `company` added to the existing Employee name read |
| Punch query condition | 1 query (direct reports list) | 1 query (the switch), the rest is inside the SQL | HR: 0, as today |
| One punch `has_permission` | 0-1 | 1-2 | switch + one parameterised check |

The count does not depend on days or punches. Tests assert that: `month()` with 2 and
6 punches a day gives the same count; `person()` over 1 and 12 months gives the same
count, each with exactly one Checkin query (OPS-3, AC-46, AC-47). Before and after
numbers go in `06-implementation-notes.md`. No index (OPS-5), no cache, no job.

**Worst case designed for:** DTC, 597 staff, 4-6 punches a day: ~190 punches a month,
~2,200 for 12 months for one person; a whole-line subquery over ~600 Employee rows.

## 8 · Non-functional verdicts

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **neutral** | `month()` +0 Checkin queries, +4-5 constant; `person()` +1 Checkin read, +4-5 constant; payload +~3 KB gzipped worst case |
| Security | **improves** | Closes ALV-332 (manager edit/delete) and ALV-333 (self edit/delete) in the permission layer; new values come only through two existing endpoints after their checks; no new endpoint, no new `ignore_permissions`. **Degrades only when the switch is on**, by your choice: whole-line punch read |
| Reliability | **neutral** | Missing field, missing rule set or missing shift means no break, never an error; the reason is shown as stored. Risk: a manager who used to add punches for staff will now be refused (D1) |
| Scalability | **neutral** | Bounded queries; the line scope stays in SQL, not an ID list |
| Maintainability | **improves** | Three copies of the break sum become one; one SQL text for both punch hooks instead of two queries |
| Data integrity | **improves** | Fewer people can change or delete a punch, which changes pay. Nothing new is stored; no cache to invalidate |
| Compliance / privacy | **improves** | DPDP transparency: a person sees why their pay was cut. No break on any group view (PRIV-1). The switch, when on, is the one widening, off by default, System Manager only, with history |

## 9 · Parallel-work check

| File | Hot? | Who else is in it | Plan |
|---|---|---|---|
| `field_app_access.py` | no | nobody on the board; no unpushed board branch touches it | edit |
| `field_app_settings.py` | no | nobody | edit (field list + guard) |
| `payroll_rules.py` | no | main checkout has someone's uncommitted edits (stale `dev`) | edit in worktree only; never touch main |
| `payroll_rules_apply.py` | no | same | same |
| `day_marks.py` | no | nobody | one line |
| `attendance_correction.py` | shared API | main checkout uncommitted edits | worktree only |
| `attendance_analytics.py` | shared API | main checkout uncommitted edits | worktree only |
| `public/js/ess/portal.js` | **yes** | main checkout uncommitted edits | touch only `acRow`, `acPaint`, `acDetail`, `aiPerson`; no reformatting |
| `public/css/ess/panels.css` | no | main checkout uncommitted edits | a few lines beside `.ac-help` |
| new test files | - | - | `tests/test_break_and_reason_alv328.py`, `tests/test_punch_rights_alv332.py` |

`hooks.py`, `patches.txt` and DocType JSON are **not** touched. Board branches checked
for overlap (`slice/alv-318`, `alv-281`, `alv-266-rebased`, `alv309`, `alv-329`): none
touch these files. **Question for you:** is anyone else, on another machine, working in
these files? I cannot see other machines.

Pin tests that must stay green: `test_payroll_rules`, `test_shift_hours_alv326`,
`test_day_marks`, `test_alv302_sync_punch`, `test_field_app_step1_013`,
`test_field_app_step2_013`, `test_install_hooks_parity`, `test_attendance_correction`,
`test_attendance_analytics`, `test_portal_security_010`. The new tests name ALV-328,
ALV-332 and ALV-333 so a merge that drops the feature fails CI.

## 10 · Race conditions, edge cases, states

**Races.** The switch flips during a request: each hook reads it once; the worst case
is one page drawn under the old value, read-only. A punch arrives while `month()` reads:
the page shows what was there at the read, like today. The engine re-judges a day while
the page is open: break is live from punches, the reason carries its own "Worked out on"
time (design S8). Two saves of HR Settings: last one wins, each with a Version row.

**Edge cases** (all in spec §9, plus): a person with no company or no rule set (no
break); no shift on the day or the employee (no break; engine holds); night shift, end
before start (no break; engine holds); category allowance 0 (rule set's figure); a Left
person opened by HR in `person()` (break shows, as the reason does); a Left caller (no
punches at all, as today); a loop in `reports_to` (the SQL `UNION` ends); a punch after
midnight linked to yesterday (counted on its own date, AC-17a); the subject has punches
but the caller cannot read them (the list is empty, so no break and no rule-set reads).

**States.** Switch: 0 → 1 and 1 → 0, System Manager only; a refused change throws in
`validate`, so nothing is saved and no Version row is written. Punch: new → saved by its
owner, the machine, the field app or HR; saved → changed or deleted by HR only.
Attendance: only submitted rows are read; a cancelled day falls away and its amendment
shows.

## 11 · Test plan

All on my own throwaway containers with a **freshly created site**, never the shared bench.

1. **Engine unchanged:** `test_payroll_rules`, `test_shift_hours_alv326`, `test_day_marks`
   green before and after the refactor.
2. **Break per day (AC-1..17a):** pure tests on `punch_minutes`, `minutes_on_break`,
   `breaks_by_day`; then the AC-13 engine-match month: run `evaluate_attendance` on each
   day, then `month()`, and compare to the stored "Breaks: N minutes" text.
3. **Reason (AC-18..23):** keys only when set; screen escapes `<img onerror>` (AC-21).
4. **Punch rule, as a plain staff login, a direct manager, a skip-level manager, an HR
   Manager and the machine account, switch off and on:** REST list and get, `PUT`,
   `DELETE`, `POST` (own and someone else's), `frappe.client.set_value`, `.delete`,
   `.save`, `get_list`/`get_count`, `frappe.desk.reportview.get`, link search, share,
   File download of a punch photo. Each refusal has a **negative control**: with the new
   rights check removed, the manager `DELETE` succeeds, or the test is invalid.
5. **SEC-6:** for every manager in a 3-level fixture with a Left middle manager and an
   Inactive report, the `get_list` set equals the `has_permission` set, record by record.
6. **Switch (AC-28..36):** field exists at 0 after install and after migrate; HR Manager
   refused on Desk save, REST `PUT`, `set_value`, `client.save`; System Manager allowed;
   Version row; off again on the next request.
7. **Must-nots:** colleague refused by `month()` and `person()` (AC-41); Frappe's doors
   on Attendance as a plain staff login with the own-record negative control (AC-42);
   no `break` key in `summary`, `filter_options`, `team_days` (AC-40); ceiling test
   unchanged (AC-43); no log or throw with a break or reason (AC-45).
8. **Query counts** (AC-46, 47) and **payload** (AC-48).
9. **UI by hand**, then once in a browser at 360 px and 1440 px: rows, Break column,
   tiles, "Why this day", Insights column in `.tbl-wrap`, no sideways scroll.
10. **Whole `alvoraa_portal` suite** once at the end, both batch summaries read
    (lesson: `bench run-tests` prints two).

## 12 · Release steps

Each needs your word. Nothing here is run in this step.

1. Local: build and test in my own containers; report; stop.
2. Before the push to dev, **read-only counts on DTC**:
   - A: active logins due an own-record row but without one (must be 0).
   - B: Custom DocPerm on Employee Checkin and Attendance by role.
   - C: Location Manager User Permissions.
   - D: Attendance rows with `alvoraa_evaluated_on`, by month.
   - **E (new): Employee Checkin rows in the last 120 days whose `owner` is not HR, not
     the machine, not Administrator, and not the person's own login.** If E is above 0,
     somebody creates punches for others today, and D1 decides what happens.
3. Push to dev on your word (it carries ALV-326 too; it is already on dev). Migrate runs
   in the deploy. Then OPS-9a: field exists, value 0, Custom DocPerm and User Permission
   counts unchanged, `deploy/nginx.conf` unchanged, and one manager API probe.
4. OPS-7: `?v=` changed on `/hrms-employee`, served `portal.js` contains "Break not
   measured".
5. Main only on your word after dev testing; repeat 3 and 4, plus count E again after.

## 13 · Rollback

Revert the ALV-328 commits on `dev` and redeploy (OPS-8). **Not** a previous image tag,
which would also undo ALV-326. Before reverting, untick the switch if anyone turned it
on (OPS-8a). The Custom Field left behind does nothing. A rollback also gives managers
back edit and delete on their reports' punches, so ALV-332/333 reopen; say so to DTC if
it happens.

## 14 · Risks

| # | Risk | Label | What I do |
|---|---|---|---|
| K1 | Someone at DTC adds punches for their staff today and will be refused | needs D1 | Count E before release |
| K2 | A tenant role that edits punches is not in the HR list | needs D2 | Count B; you decide |
| K3 | Break on a day judged before a category or allowance change differs from the reason text | acceptable simplification (spec §9) | The reason carries its date |
| K4 | "Missing punch" tag disagrees with "Break 40 min" on a repeat-scan day | acceptable simplification (design A4, out of scope) | none |
| K5 | Desk shows a Save button to a manager on a report's punch, then the server refuses | acceptable simplification | the refusal message says only HR can change a punch |
| K6 | Skip-level photo reads outside Desk not logged when the switch is on | accepted by you (R3) | none |
| K7 | HR company scope still lives in portal code (W2), Location Manager Attendance (W1), manager share of Attendance (W3) | temporary debt, pre-existing | not touched; own tickets |

## 15 · Decisions for Surbhi

- **Approve this strategy** (rungs: one Custom Field, edits to existing code; no new
  endpoint, DocType, job, cache or hook entry).
- **D1 · May a manager still add a punch for a direct report?** Your rule says staff
  create only their own. My recommendation: **no, HR only**, as you said; but only after
  count E shows nobody relies on it. If E is above 0, we talk before release.
- **D2 · Should Location Manager, the Payroll team or HR Data Officer edit punches?**
  Recommendation: **no change to the HR list**; a role that needs it also gets HR User.
- **D3 · The screens do not call the punch rule directly.** They read punches with
  `get_list`, so Frappe applies the rule for them; if the list is empty, no break is
  worked out. This is one copy fewer than the spec's handoff note asked for. Recommend
  you accept it; security to confirm at review.
- Tell me if anyone else is working in the files in section 9.

## 16 · Subtract pass

Removed on this pass:
- A new `hooks.py` entry for the field and for the guard. The existing
  `field_app_settings.after_migrate` and `validate_hr_settings` already run on every door
  and on install.
- A separate "may C read P's punches" Python function for the screens (D3).
- A Python walk of the reporting line for `has_permission`; the one SQL text serves both.
- A section break for the new field (spec AC-44 says exactly one field).
- A third pure helper for the day's state; that logic lives once, in `breaks_by_day`.
- Any change to `day_marks.py` beyond the one sum line.

Kept on purpose: `punch_minutes`, because without it the "drop the seconds" rule would
exist twice (engine and screens), and AC-16 is exactly that bug.

## Approved (12 Nov 2026)

Surbhi approved the strategy and accepted every recommendation:

- **D1:** No. Only HR (and the machine account) add a punch for someone else. Condition: the DTC read-only count E (`grace-ops/step31-punches-added-for-others-readonly.py`) must show nobody outside HR relies on it **before release**. Not yet run at approval time.
- **D2:** No change to the HR list. A role that needs to edit punches gets HR User.
- **D3:** Accepted. The screens rely on `get_list` to apply the punch rule; security confirms at review.

**Count E result (12 Nov 2026, DTC, read only):** 0 punches added for other people by non-HR logins in the last 120 days. D1 condition met.
