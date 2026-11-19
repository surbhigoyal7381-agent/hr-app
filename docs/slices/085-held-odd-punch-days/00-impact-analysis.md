---
slice: 085-held-odd-punch-days
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-11-19
status: STRATEGY FOR APPROVAL. No code written. No file outside docs/ touched.
risk tier: 1 (pay, release rights, a bulk write)
worktree: /Users/mac/hr-app/.claude/worktrees/085-held-odd-punch-days
branch / built on: slice/085-held-odd-punch-days, HEAD e3918b50 on top of origin/dev 101fd29b
---

# 085 Held: impact analysis and strategy (ALV-392)

## 0 · Bad news first

1. **The spec has four holes I found by reading code. None of them can be guessed.**
   - **(a) There is nowhere to put "the missing time".** Attendance Request has no time field (`attendance_request.json` fields: employee, dates, half_day, reason, explanation, shift, include_holidays, amended_from; `reason` is mandatory). Spec section 4 says "no new data, as today". It is wrong. Two Custom Fields are needed (section 5.3).
   - **(b) Stock approval would flip a Held day to Present, always.** `attendance_request.py:create_or_update_attendance` does `doc.db_set({"status": "Present"...})` on any existing row. The "Present or Half Day from the corrected time" rule (D2) needs our own code to run after it. Frappe runs the controller first and `doc_events` hooks after (read `composer`/`compose` in `frappe/model/document.py`, `alv084-bench`).
   - **(c) US-14 has nothing to protect in Release 1**, because the Company fields only exist from Release 2. And US-11 says "own Held day", but a Held day does not exist in Release 1. See section 3.
   - **(d) I could not read Grace's Payroll Settings.** If `payroll_based_on` is "Leave" there, stock Frappe never reads Attendance at all (`salary_slip.py:586`) and the whole "Held costs a day" premise needs a second look. **Blocks Release 2's design of the slip step. Needs a read-only look at Grace (Q-E1).**
2. **Branch `slice/084-employee-window` (8 commits, not on dev) edits the same files** as this slice: `attendance_correction.py`, `hooks.py`, `hr_api.py`, `portal.js`, `org-settings.html`. Section 9.
3. **This is a 65-point slice.** Release 1 alone is about 10 points and is small and safe. Release 2 is where the risk is.

## 1 · What I read (proven) and what I did not

Read in this worktree at e3918b50: the whole of 01, 01b, 01c, 02 (including the Spec gate) and 07; `salary_slip.py` 220-260, 540-680, 780-900; `shift_type.py` 100-300, 365-450; `employee_checkin.py` 225-540; `attendance_request.py` 125-345; `attendance.json` (status, in_time, out_time, shift, permissions); `payroll_slip.py` 96-348; `payroll_rules_apply.py` 365-610; `attendance_correction.py` 250-462, 1105-1162, 1387-1462, 1591-1672, 1734-1850, 2143-2200; `field_app_access.py` 30-110, 240-285; `hooks.py` 140-215, 375-392, 640-670, 815-850; `hrms/.../access.py` 28-320; `company.json` and Frappe `document.py` inside `alv084-bench` (read only).
**Not checked:** any site; Grace's Payroll Settings, Server Script text and Custom DocPerm; production; whether `logs/security.log` is written; any test run (I ran nothing). The spec's line numbers for `access.py`/`field_app_access.py` I re-read and they hold.

## 2 · Fork policy (asked for)

`hrms/` is a vendored fork committed into this repo (ARCHITECTURE.md:62 and :81). It is copied by `deploy/Dockerfile`, so `bench update` does **not** pull upstream into it. The rule in `.claude/context/frappe-conventions.md` is "behaviour on save: `doc_events` in `hooks.py`; avoid editing upstream controllers". The repo has applied it: `hooks.py:380` says "no new edit lands inside the vendored Frappe HR tree (ALV-169)". The only recorded edit was KI-4 (half-day leave), and it needed explicit sign-off.
**So: no edit to `salary_slip.py`, `shift_type.py`, `employee_checkin.py` or `attendance_request.py`.** The two stock files I would otherwise want to edit have had 3 commits in their whole life and no Alvoraa markers, so they are still close to stock; keeping them so keeps a future upstream merge cheap.
**One place where I ask for a one-line sign-off** (section 6, D-3): the stock Monthly Attendance Sheet `status_map`. Everything else is `doc_events` and Custom Fields in `alvoraa_portal`.

## 3 · The two releases

| | Release 1 (safety doors) | Release 2 (Held) |
|---|---|---|
| Stories | **US-11, US-12, US-13** | US-1 to US-10, US-14 to US-18 |
| New fields, new status | none | Property Setter "Held", 3 Attendance release fields, 2 Attendance Request fields, 3 Company fields |
| Needs Held to exist | no (see below) | yes |
| Can ship alone | **yes** | after Release 1 |

**Two deviations from the spec's story text, for Surbhi to confirm (D-1, D-2):**
- **D-1 US-14 moves to Release 2.** It protects the hold switch, limit and exempt roles. Those fields do not exist in Release 1. Shipping inert fields on the Company form that "do nothing" would confuse HR. The alternative (ship the three fields inert, with the guard) is possible and I will do it if she prefers.
- **D-2 US-11 in Release 1 closes the doors for any own Attendance row and any own punch, not only a Held one.** A Held day cannot exist yet. The rule is simpler and stricter: HR cannot confirm, cancel, amend, delete or hand-edit **their own** attendance row, or add/change/delete **their own** punch (an ordinary new punch "now" stays allowed). It matches SEC-9's stance, "no role is exempt". Cost: an HR person who today fixes their own attendance must ask a colleague. That is a behaviour change on live tenants; it is the point of the fix.

## 4 · Ladder (no-over-engineering.md)

| Need | Rung used | Cheaper rung rejected because |
|---|---|---|
| "Held" status | **2 Property Setter** in `payroll_fields.py` pattern | Rung 1: stock options have no Held (`attendance.json:96`) |
| Held is unpaid | **4 code**: one `validate` hook on Salary Slip, in our app | Rung 2: no setting makes stock read an unknown status (`salary_slip.py:824`). Editing the vendored file rejected: fork policy, section 2 |
| Hold at marking | **4 code**: one `validate` hook on Attendance | Frappe has no "hold" option anywhere |
| Release by a late punch | **4 code**: one `after_insert` hook on Employee Checkin | auto-attendance counts any row with docstatus < 2 as marked (`shift_type.py:380-390`) so it never touches or releases a Held row |
| Release by HR | **4 code**: `before_submit` + `on_submit` on Attendance Request | stock sets "Present" with no hours check (see 0.1b) |
| Per-company switch, limit, roles | **2 Custom Fields on Company** + a `validate` hook for who may change them | A new DocType: rung 5, rejected. A permlevel on the fields: rejected, see 5.6 |
| Backfill | **4 code**: one script file in `scripts/`, dry run default | none exists |
| Own-day doors, raiser rule, scope | **4 code**: reuse `refuse` / `refuse_own_decision`, hooks, 2 small edits | no standard control covers them |

**New DocType: none. New app: none. New queue or container: none. New dependency: none.**

## 5 · Strategy

### 5.1 How "Held" is made unpaid without touching upstream (Release 2)

Stock reads statuses `Absent, Half Day, On Leave` only (`salary_slip.py:824`; the loop at `:841-872` counts `absent` only for `Absent`). Held is paid by default.
**Mechanism:** a second `validate` hook on Salary Slip, `held_day.deduct_held_days`, wired **after** `payroll_slip.on_salary_slip_validate` (the existing hook, `hooks.py:150`). Frappe's own validate recomputes `payment_days` from scratch on every save, so a hook that subtracts afterwards is safe to run twice. The hook:
1. returns at once for a submitted slip (`docstatus != 0`) and for a company that has an Alvoraa Payroll Rule Set (that path prices from `judge()` and already treats an odd count as held, `payroll_rules_apply.py:448-500`; AC-5 proves a Held-status row there still prices right);
2. counts the employee's `Held` rows in the slip period (one query), skipping dates in the employee's holiday list the way stock skips Absent on holidays (`salary_slip.py:848-852`);
3. sets `payment_days -= n` (floor 0), `absent_days += n`, then calls `calculate_net_pay()` and the three year-to-date helpers, exactly as the existing hook does (`payroll_slip.py:336-343`).

It is the same shape as an existing, tested hook, and it costs one indexed query per slip save. It needs no change to `consider_unmarked_attendance_as`: a Held row is a submitted row, so it is never "unmarked" (AC-4).
**Caveat (D-4 / Q-E1):** this deducts Held even if Grace's `payroll_based_on` is "Leave". That would make Held stricter than Absent there. I will not decide it silently; read Grace's Payroll Settings first.
Also the grooming copies of "not charged on an absent day" (`payroll_slip.py:164`, `daily_attendance_workings.py:212`) get `"Held"` added: a day that is not paid carries no grooming charge. One word each, same rule in two places.

### 5.2 Where the hold is applied (Release 2)

`doc_events["Attendance"]["validate"] = held_day.hold_odd_punch_day`. It changes `doc.status` **before the first save**, so the row is written once, never created then rewritten. That is what makes AC-11 (the 3-minute tick leaves it) hold: the row exists as Held, and `get_marked_attendance_dates_between` counts docstatus < 2 as marked (`shift_type.py:380-390`).
It fires only when all are true: `doc.is_new()`; `status in (Present, Absent, Half Day)` and not a leave day; `doc.in_time` is set (**`in_time` and `out_time` are read-only on the Attendance form, `attendance.json`, so only auto-attendance sets them. A hand-marked row and an Attendance Request row have none**); no `attendance_request`; the Company switch is on; and the folded punch count for that employee and date (`payroll_rules_apply._punches`, which already folds repeat scans) is odd. Cost when the switch is off: one cached Company value (`frappe.get_cached_value`, cleared by Frappe when Company is saved). When on: one more query, `_punches`.
It writes status only. Auto-attendance then links the log as it does today.
[ASSUMPTION, to prove with a test on a fresh site] a row hand-made by HR with `in_time` typed is impossible from the form (read-only) and rare by REST; if it happens, the day is Held, which is safe (unpaid until a human looks).
**The no-shift Held day (Q3b) cannot be created by this hook**: `in_time` has `depends_on: shift`, and auto-attendance always passes `self.name` as the shift (`shift_type.py:_process`).

### 5.3 How HR release works (Release 2)

Two Custom Fields on Attendance Request, `alvoraa_missing_time` (Time) and `alvoraa_missing_log` (Select In/Out). The portal's held form fills them and sends a fixed existing reason ("Forgot to Punch Out" / "Missed Punch Both Ways" for a 3-punch day); no reason box (D1). `reason` is mandatory in stock, so the server sets it.
- `before_submit` (a list: existing `refuse_own_submit`, then the new raiser refusal in 5.8, then `held_day.note_held_day`): remembers that the target row was Held (`doc.flags`), because stock is about to overwrite it.
- `on_submit` (a list: existing `attendance_correction.on_submit`, then `held_day.release_by_hr`): after stock's `db_set("Present")`, works the result out from the day's real punches plus the one missing time, using **the Shift Type's own `get_attendance(logs, absent_threshold, half_day_threshold)`** (`shift_type.py:266`), with the half-holiday halving that `_process` applies. No threshold logic of our own (G5). Then `frappe.db.set_value` the status, `working_hours`, `half_day_status` when Half Day, and the three release fields. `set_value` skips the Version row, which is why the three release fields exist (PRIV-3, SEC-7). Same method as the engine's own `write_verdict`.

### 5.4 How the late machine punch releases (Release 2)

`doc_events["Employee Checkin"]["after_insert"] = held_day.release_on_machine_punch`. Order of tests, cheapest first, so a normal punch costs almost nothing:
1. `is_machine_account()` (`field_app_access.py:47`): false means return. This is SEC-5: judged by who filed it, never by `device_id`.
2. `doc.skip_auto_attendance` or a folded repeat scan: return (AC-21, AC-23).
3. One query: Held submitted Attendance for this employee and the punch's calendar date (the same calendar day `_punches` counts). None: return.
4. Recount with `_punches`; odd or fewer than 2: return. Even: release as 5.3 does, with `how = Machine punch`, `by = the checkin name`.
Whole body in `try/except` with a savepoint: a fault goes to Error Log and **never fails the punch** (the sync tool halts a machine's batch on a refusal it does not know, `field_app_access.py:69-73`). Limit I could not remove: a night shift that crosses midnight is matched by calendar day, as the hold is. Not new.

### 5.5 How a release refreshes that one employee's draft slip (Release 2)

`held_day.refresh_draft_slip(employee, date)`, called by both release paths, after the status write. One query for that employee's **draft** slip whose period contains the date; if found, `frappe.get_doc(...).save()` (`ignore_permissions=True`, a deliberate flag: the caller may be the machine account, which holds no Salary Slip right, and the act is system-owed). Our slip hook in 5.1 then re-prices it. A submitted slip: untouched, and HR gets the sentence (AC-18, Q4). **Own savepoint and own try**: an error is written to Error Log by slip name only and the release stands (AC-17, OPS-3, OPS-19). It never loops over other employees (OPS-4). Inline, not queued: one slip save is the only heavy step and runs only on a release. **I will time the heaviest slip on the bench before asking to ship; if it is over about 2 s the machine path moves to `frappe.enqueue(..., enqueue_after_commit=True)`** (nfr-budget rule for >2 s work). Not measured yet.

### 5.6 The per-company fields (Release 2)

Three Custom Fields on Company, created in `payroll_fields.py`'s existing pattern and wired to `after_migrate` and `after_install` (OPS-6, OPS-10): `alvoraa_hold_odd_punch_days` (Check, 0), `alvoraa_monthly_request_limit` (Int, 0 = none), `alvoraa_limit_exempt_roles` (Small Text, comma list, validated against `Role`).
**Who may change them: a `validate` hook on Company, not a permlevel.** The hook refuses a change to any of the three unless the user is Administrator, System Manager, or an HR Manager whose `permitted_companies()` contains this company (`access.py:193`). Reasons for rejecting permlevel: it needs a Custom DocPerm row per role per tenant, and tenants' Custom DocPerm is exactly what the clean-up job and the 5 Nov migrate stall (memory: 1,780 deletes) dealt with; a hook works on every door (Desk, REST, import) and reads company scope, which a permlevel cannot. Company already has `track_changes: 1` (stock `company.json`, read in `alv084-bench`), so AC-54's Version row is free for normal saves. **This differs from the spec's permlevel assumption; flagged (D-5).**
Only HR Manager, System Manager and Administrator can change them: count of roles = 2 plus Administrator.
The monthly limit: `before_insert` on Attendance Request (existing hook `prepare_half_day_correction` becomes a list). Counts this employee's requests in the calendar month that carry no `alvoraa_missing_time` (a held-day request carries one, and `validate` refuses a time on a request whose day is not Held, so nobody can use it to dodge the limit). Exempt-role test is on the **employee's login** (assumption, Q2).
**The live count** (`N days will be held`): one whitelisted function, integer only, scoped by `permitted_companies`, fail closed.

### 5.7 Retiring Grace's Server Script (Release 2, operator step)

Site data, not in the repo; I cannot read it. Order, all by file with `env/bin/python`, never piped to the console: read the script text and its type read-only (Q2) → write the three Company values at Grace → read them back → one test day → set the script `disabled = 1` (not delete, OPS-20) → read it back disabled → test again. If both rules ran, a fourth request would be refused twice, with two different sentences. The disable is last.

### 5.8 Release 1 mechanisms

| Story | Change | Files |
|---|---|---|
| US-11 | New module `attendance_doors.py`. Four small functions using `refuse_own_decision`: Attendance `before_update_after_submit` (the confirm fields and any REST PUT), `before_cancel`, `on_trash`, and `validate` for a new row of one's own. `checkin_has_permission` returns False for write/delete on **one's own** punch **before** the HR early return (`field_app_access.py:259-261`); a new own punch stays allowed | `attendance_doors.py` (new), `hooks.py`, `field_app_access.py` |
| US-12 | `refuse_raiser_submit` on Attendance Request `before_submit`, added to the existing list beside `refuse_own_submit`. Same test as `not_yours_yet` (`owner == session user`, line 1611). **`Administrator` is exempt**: 19 test files mention Attendance Request and many insert and submit as Administrator in one go, and `refuse_own_decision` already cannot bite Administrator (no Employee record). `not_yours_yet` stays: it draws the sentence on the screen | `attendance_doors.py`, `hooks.py` |
| US-13 | `_scope_conditions` (`attendance_correction.py:307`) returns a no-match condition instead of `None` when the caller is HR with no company and no branch. Callers, counted: **3 in-file** (`_refuse_outside_scope` at 357, the picker at 435) plus **1 test file** (`test_picker_scope_349.py`). System Manager/Administrator keep everyone (`permitted_companies` returns all) | `attendance_correction.py` (about 5 lines) |

Callers I grepped (counts are files, in `alvoraa_portal/` + `hrms/` + `alvoraa_goals/`):
`_scope_conditions` 2 files; `_refuse_outside_scope` 2; `checkin_has_permission` 5 (2 code incl. the def and `hooks.py:552`, `field_checkin.py`, 2 tests); `not_yours_yet` 4 (`inbox_api.py` is one; 3 tests); `refuse_own_submit` 4 (`hooks.py` x4 uses, 3 test/doc refs).
**Release 1 needs the Company User Permission for `hr@grace.alvoraa.co` first (Q1).** The ALV-385 commit already says this login is cut off from the two reports; US-13 extends that to the release screens. Without it, Grace's HR cannot approve a correction after Release 1 ships. Recommended: yes, before the push.

## 6 · Pay readers, one verdict each (proposed; AC-5 makes the final call at build)

Greps: files that contain the literal `"Absent"` outside tests, `alvoraa_portal` + `hrms` + `alvoraa_goals`: **31**. I read the line in each of the following.

| Reader | What it does with status | Verdict for Held |
|---|---|---|
| `salary_slip.py:824,854,866` (stock) | sums LWP/absent from Absent, Half Day, On Leave | **Fixed from outside** by the validate hook (5.1). Not edited |
| `salary_slip.py:619-664` | unmarked days, half-absent | Held is a submitted row so never unmarked. Correct, no change; AC-4 proves it |
| `payroll_slip.py:164` | `not_charged` for grooming | **Add `"Held"`** |
| `daily_attendance_workings.py:212` | same rule, a copy | **Add `"Held"`** (keep in step with the line above) |
| `payroll_rules_apply.py:500` (`judge`) | `marked_absent` | DTC path; odd count is already held. No change; AC proves |
| `payroll_reprocess.py` (`judge` x2) | re-judges from punches | No change; reads Attendance rows by filters without status |
| `salary_components_and_workings.py:293` | a column title "Absent" | No change (title only); reads `month_summary` |
| `salary_register` (hrms) | reads Salary Slip, not Attendance | Correct through the slip. No change |
| `attendance_analytics.py:351` | counts absent / expected | Held is in no branch, so it is left out of expected. **Add a `held` branch** so the sheet does not understate |
| `org_figures.py:40,182,213` | `COUNTED` tuple and sums | Add `Held` to COUNTED only if the denominators matter; propose **leave and list** |
| `hr_api.py:1209,1366,1471` | employee card counts | Held shows in none. Propose **add a Held count to the dict**; today it vanishes |
| `home_api.py:315` | days to fix: unmarked or Absent | Held days belong to the Held flow, not this list. **Exclude** |
| `data_review.py:326,341` | branch absent % outlier | Held counts in `expected`, not `absent`. Understates slightly. **Leave and list** |
| `leave_rules.py:859` | "worked day" block for a leave | Held is not in the list. A leave over a Held day: **not checked, add a test** |
| `attendance_score.py:190` (performance) | score from present/absent | Not pay. **Leave and list** |
| `gratuity.py:214` | counts Absent for service years | Not monthly pay. Held ignored until released. **Leave and list** |
| `alv291_attendance_fix.py` (8 uses) | one-off repair script | Not a live reader. No change |
| `monthly_attendance_sheet.py:27,662` (stock) | `status_map.get(status, "")` blank | **D-3: one-line edit adding `"Held": "HLD"`, needs Surbhi's sign-off** (fork policy). Without it, a Held cell prints blank on the sheet HR prepares payroll from. Totals queries (lines 589-600) are separate and not changed |
| `employee_checkin.py:253`, `attendance_request.py` | knows Present/Absent/Half Day only | Not pay; why the release is our code |

The final record, as the spec demands, goes in the PR: every module that holds "Absent" gets "reads Held correctly / fixed / not a pay reader".

## 7 · Cross-module reach, personas, HRMS domains

- **`alvoraa_portal`**: almost all code (`held_day.py` and `attendance_doors.py` new; `hooks.py`, `attendance_correction.py`, `field_app_access.py`, `payroll_fields.py`, `payroll_slip.py`, `attendance_analytics.py`, `hr_api.py`, `home_api.py`, `daily_attendance_workings.py`, `portal.js`, `org-settings.html`).
- **`hrms` fork**: no edit unless D-3 is approved (one dict line). `alvoraa_hr_core/access.py` is our own code in that tree and is read, not changed.
- **`erpnext`**: only Company Custom Fields and a Company `validate` hook. No edit.
- **`alvoraa_goals`, `alvox_compensation`**: not touched. `alvoraa_portal`'s tenant/control-plane split: no new route, so nothing control-plane-only becomes reachable.
- **Personas.** Employee: sees Held, the reason, the pay effect and how it ended; sends a time only. Line manager: same sheet for a direct report, no reason. HR User/Manager in scope: decides, cannot decide their own day or a request they raised; HR Manager alone sets the switch. HR login with no company: nobody. CXO: no change. Machine account: its insert may release a day.
- **HRMS domains.** Attendance (new status, hold, release), payroll (unpaid day, slip refresh), leaves (a Held day with a leave: untested edge), org structure (company and branch scope).

## 8 · Seven dimensions (against the plan; I will re-assess against the code)

| Dimension | Verdict | One line |
|---|---|---|
| Performance | **neutral** | Switch off: one cached read per Attendance insert. Per machine punch: one indexed query. Slip: one query per save. Measured: nothing yet; budget in 5.5 |
| Security | **improves** | Closes the self-release doors, the raiser door, and the fail-open scope. New `ignore_permissions` count: **1** (slip refresh, 5.5), named and justified. No `allow_guest` |
| Reliability | **neutral, with one watch item** | Every new hook is wrapped and never blocks a punch or a save. Watch: a slip re-save inside a machine POST (5.5) |
| Scalability | **neutral** | No loop over employees anywhere in a hook. Backfill chunked at 50 (OPS-15). DTC: switch off, so nothing changes |
| Maintainability | **degrades slightly** | Pay is now correct through an extra hook beside the engine's. Two copies of the "not charged" rule already existed and a third reader list grows. Mitigation: one `held_day.py`, AC-5 list recorded in the PR |
| Data integrity | **improves** | Held row written once, never re-created; releases write a record (how, who, when); no cache added; the unpaid day cannot fall back to "unmarked". **Risk**: `set_value` writes skip Version, so the three release fields carry the audit |
| Compliance / privacy | **improves, one accepted risk** | An automated pay decision now has a named human owner, a visible state and a challenge route (PRIV-3). R1 (wage-law basis) stays Surbhi's accepted risk. No new data class, no new reader |

**Only one dimension degrades: maintainability, slightly.** Cache: none added, so no invalidation to define. The Company switch read uses Frappe's own cached value, which Frappe clears on save.

## 9 · Parallel-work check (parallel-work.md)

- Worktrees: 7. Branches ahead of `origin/dev` that touch our files: **only `slice/084-employee-window` (df6889da, 8 commits, never pushed)**. `alv385-company-scope`, `alv358-daily-workings`, `083`, `ci-shard-trial` are 0 ahead.
- **Overlap with 084:** `hooks.py` (it adds `validate` to the same Attendance Request block I turn into lists), `attendance_correction.py` (`month()`, `_employee_for`, filing-window helpers), `hr_api.py` (org setting), `portal.js` (172 lines), `org-settings.html` (my settings card's home), `requests.html`. Other 084 text mentions the manager filing window that US-18 also touches.
- **Plan: sequence, then split.** Release 1 touches `hooks.py` (3 lines), `attendance_correction.py` (about 5 lines at 307) and `field_app_access.py`: small and in different hunks to 084's, so it can go first. For Release 2's `portal.js`, `hr_api.py`, `org-settings.html`, **I will wait for 084 to reach `dev` and rebase onto it**, because three of those are the same functions. **Ask Surbhi: is anyone else (a human) in these files?** No `.claude/work-in-progress.md` exists in this tree to read.
- Hot file `hooks.py`: edit by hunk, re-read after every rebase, add a pin test per hook.
- Work in this worktree only. Test runs: one at a time, on my own stack (the shared bench mounts a stale checkout).

## 10 · SEC, PRIV and OPS, how each is met

| Item | How | Release |
|---|---|---|
| SEC-1 | Slip hook 5.1 + AC-3, AC-4 fixtures both modes; submitted slip untouched with a sentence | 2 |
| SEC-2 | `attendance_doors.py` + `checkin_has_permission` own-record first | **1** |
| SEC-3 | Raiser refusal on `before_submit`; Administrator exempt | **1** |
| SEC-4 | `_scope_conditions` fails closed; settings and count use `permitted_companies` | **1** (screens), 2 (settings) |
| SEC-5 | `is_machine_account()` first test in 5.4; five negative tests | 2 |
| SEC-6 | Company `validate` hook (5.6); limit on the document's `before_insert` | 2 |
| SEC-7 | Script with dry-run default, Grace and November only, undo file first, audit Comment per row (it uses `db.set_value`, so it writes its own), re-run harmless | 2 |
| PRIV-1 | No new route, list or cache; test the three negatives | 2 |
| PRIV-2 | Form payload keys asserted; log lines ids only (existing `log_refusal`); grep for `employee_name` | 2 |
| PRIV-3 | Release fields on the row; day sheet returns state, reason code, pay effect, release source | 2 |
| OPS-1,15,16,17 | Backfill chunks of 50, undo list outside the repo read back, order from 07 | 2 |
| OPS-2,11 | Hold writes once at validate; AC-11 break-test | 2 |
| OPS-3,4,19 | Re-save one slip, own try, never a batch | 2 |
| OPS-5,20 | Script disabled last, read back | 2 |
| OPS-6,10,14 | `payroll_fields.py` pattern, `after_migrate` and `after_install`, fresh CI site | 2 |
| OPS-7,13,18,22,23 | Runbook, no code | 1 and 2 |
| OPS-9 | Section 6 | 2 |
| OPS-12 | Existing `Cache-Control` for API calls **not read from nginx.conf yet**; I will read it | 2 |

Not adopted or deferred, as Surbhi cut: Hindi, second "Sent to HR" tag, tag picker for roles (comma list), monitoring beyond one count, Grace's dead slip batch.

## 11 · Q3 and Q4, my recommendations (Surbhi decides)

**Q3a. Corrected time below the shift's absent threshold.** Recommend: **the day becomes Absent, by the shift's own rule, and HR sees that on the card before pressing the button** ("If you approve: this day becomes Absent, 0h 40m. It stays unpaid."). Reason: it is exactly what the same punches would have produced on an even day (`shift_type.py:get_attendance`); a different rule for corrected days would be a second rule. A day sent as "I left at 09:40" that results in Absent is a real answer. The card must not say "paid". The alternative, refusing the approval, leaves a day stuck Held for ever. **Note:** my version moves D2's "Present or Half Day" to "Present, Half Day or Absent". Change the button label to say what will happen.
**Q3b. No-shift Held day.** Recommend: **do not build the HR picker.** By 5.2 the hook cannot write a Held row without a shift (`in_time` needs `shift`), and the backfill only changes rows the auto job already wrote. If a Held row somehow has no shift, refuse the approval with "This day has no shift, so its hours cannot be worked out. Ask a System Manager to set the shift on the day, then approve again." One sentence, no picker, no new rule. This also removes the spec's "needs her yes" row for that.

**Q4. Release after the slip is submitted.** Recommend: **the spec's default, no automatic change, HR told in words.** HR's card says "This day is in a slip that is already final. It was not changed. To pay this day, add an Additional Salary for it" (a stock document HR already uses). Reasons: arrears is new money code with its own wage-law question; Surbhi's own rule is that HR looks at Held days **before** pay, so this should be rare. **To make "rare" a number, not a hope, the release records it and the checklist reads one count: releases that landed on a submitted slip.** The employee's sheet must not say "your slip is updated" in that case (AC-18).

## 12 · Anticipated side-effects (the questions nobody has asked yet)

1. **Grace HR is locked out** of releasing until the Company User Permission exists (Q1). Fix before the Release 1 push.
2. Every HR person loses the ability to edit **their own** attendance row and punches, on every tenant, from Release 1 (D-2).
3. Tests that insert and submit an Attendance Request as one user: the raiser rule exempts Administrator; any test that uses a named user for both will fail and must be fixed. Unknown number until run (19 test files mention the doctype).
4. The Held row is "submitted" and counts as marked: Frappe will not auto-Absent it, and a leave application over a Held day is **not tested** yet.
5. The stock Monthly Attendance Sheet prints a blank for Held unless D-3 is approved. Its total columns do not count Held as absent or present.
6. Rolling back Release 2's code with Held rows left behind pays them as normal days (OPS-22). Restore from the undo list first.
7. Release 1 and 2 share the `attendance_doors.py` own-row rule. A Held row cancelled by HR for a colleague must not fall back to unmarked (AC-4).
8. **R4 (01c, pre-existing, out of scope):** any HR role can write another company's punches by name. Release 1's own-record check does not close it. I recommend its own ticket, P2.
9. A night shift crossing midnight is matched by calendar day in both the hold and the release. Not new, not widened.

## 13 · Questions for Surbhi

| # | Question | My default |
|---|---|---|
| D-1 | Move US-14 (who may change the three settings) to Release 2? | Yes |
| D-2 | Own-row doors close for any own attendance and punch, not only Held? | Yes |
| D-3 | One-line edit to the vendored Monthly Attendance Sheet (`"Held": "HLD"`)? | Yes, sign-off as KI-4 |
| D-4 / Q-E1 | May I read Grace's Payroll Settings (`payroll_based_on`, `consider_unmarked_attendance_as`) and its Server Script text, read-only? | Yes, before Release 2 design is final |
| D-5 | A `validate` hook on Company, not a permlevel, for who may change the settings? | Yes |
| Q1 | Company User Permission for `hr@grace.alvoraa.co` before the Release 1 push | Yes |
| Q3, Q4 | Section 11 | As recommended |
| Q2, Q5, Q6 | Q2 needs the script text (D-4). Q5 is answered: two releases. Q6: host the card in `org-settings.html` beside the other site switches; confirm after 084 lands | |

## 14 · Subtract pass

Removed from my own plan: a queue and a job for the release (inline, measured first); a base class or shared "doors" framework (one function per door); a permlevel and Custom DocPerm rows; a cache; a picker for no-shift days; an Absent-on-release warning dialog (the card line says it); a separate time-stamp field (the release fields carry it). Removed nothing from the approved scope. **What I would still cut if asked:** the third release field (`release_on`, because `modified` carries it) and the `org_figures` and `data_review` changes (listed, not changed).

**No code has been written. Waiting for approval of the strategy and the D-1 to D-5, Q1, Q3, Q4 answers. A separate approval is needed for any deploy.**

---

## Strategy gate: Surbhi (19 Nov 2026): APPROVED, with the lead's recommendations

- **D-1 yes:** US-14 moves to Release 2.
- **D-2 yes:** HR cannot confirm, cancel, amend or delete ANY own attendance, or edit own punches.
- **D-3:** the small edit to the vendored Monthly Attendance Sheet. Add "Held" AND a ninth colour (DevOps P1: an 8/9 IndexError), and add a test that opens the report with a Held row.
- **D-5 yes:** a Company validate hook, not a permlevel.
- **Q3:** a corrected time below the absent threshold gives Absent, and the HR card warns before approval. A held day with no shift is refused with one sentence.
- **Q4:** a release after the slip is submitted changes nothing automatically. HR is told to use Additional Salary, and the employee sheet does not say "slip updated".
- **Machine-punch slip refresh: ENQUEUE** (DevOps view; enqueue_after_commit, ids only). An HR release stays inline.
- **Release 2 waits for slice 084 to be on dev, and rebases onto it.**
- **Before the Release 1 push:** hr@grace.alvoraa.co needs a Company User Permission (Q1).
- The approval covers local implementation only, NOT deploy.
