---
slice: 063-dtc-leave-credit-and-lwp
artifact: 04-impact-and-strategy (change process steps 1 and 2; the 00-impact-analysis of the handoff contract)
author: hrms-fullstack-engineer
date: 2026-10-21
status: waiting for Surbhi's approval. No feature code written, nothing committed, nothing pushed, nothing written to any server.
inputs: 03-functional-spec.md v3.0, 01c rev. 3, 01d, 01e, 01-product-brief.md (last sections, including "OD-1 answered"), 02-design.md v3, prototype-v3.html, 01b-devops-first-look.md
code read: worktree 060-manager-review at 59906139 (hr_api.py, inbox_api.py, payroll_rules.py, payroll_rules_apply.py, payroll_month.py, payroll_slip.py, payroll_reprocess.py, attendance_correction.py, hooks.py, portal.js 4455-4760, parts/attendance.html, parts/request-modals.html, the salary report), hrms leave_application.py and attendance_request.py, hrms alvoraa_hr_core/access.py, Frappe v16.33.1 in hrlocal-bench (Document.discard, notification_log)
---

# 063 · Impact analysis and strategy

## 0 · Bad news first

1. **Surbhi's OD-1 remedy (iv) works, but not the way it was first described.** I tried it on the
   local bench. Frappe **refuses to even create** an attendance correction on a date that already
   has an approved half-day leave - both with and without the half-day tick ("No attendance
   records to create"). So "the engine reads an approved request" alone would never get a request
   to read. **It becomes feasible with one extra step that uses Frappe's own design:** when the
   correction is raised for such a day, the attendance row's "other half" is first marked
   **Absent** (true - there are no punches for it). Frappe then accepts the half-day correction,
   and when HR approves it, **Frappe itself** sets the other half back to **Present** and links the
   request to the day. I proved that sequence on the bench, inside a transaction I rolled back.
   The engine then trusts that link. Details in section 5.
2. **A second trap for (iv), found on DTC data:** 12,632 of 12,674 DTC attendance rows carry a
   shift, and DTC has **0 Shift Assignments**. Frappe's correction looks for the attendance row by
   shift, so a correction with no shift would not find the row and would try to create a second
   attendance for the same day, which fails at approval. The same small hook must copy the row's
   shift onto the request. **My bench probe used a row with no shift, so this part is not yet
   proven by running** - it is the first thing step 1 proves.
3. **Bench answers to the spec's checks:** `apply_leave` does leave `leave_approver` empty
   (confirmed). `discard()` works when the employee calls it on their own Open request (confirmed,
   status becomes Cancelled). **No DTC employee has an email on the Employee record** (0 of 445
   active); only the 10 people with a login can get Frappe's status email. Whether the portal
   loads Hindi: the code says no (see 7.3), not checked by running.
4. **DTC headcount moved:** 445 active today, not the 476 the spec quotes. Nothing here depends on
   the exact figure.
5. **`hr_api.py` is at exactly 69 bypasses in code**, its ceiling. The employee cancel takes it to
   70, as SEC-8 decided. Every other new read is written without the word.
6. **Three changes move money** (E6, the half-day rule, OD-1 (iv)) plus one settings change. None
   reaches DTC until the rehearsal on a local copy passes and Surbhi says so.

---

## 1 · Impact analysis

### 1.1 Cross-module reach

| App | Touched | How |
|---|---|---|
| `alvoraa_portal` | **Yes** | `hr_api.py`, `inbox_api.py`, `payroll_rules.py`, `payroll_rules_apply.py`, `payroll_month.py`, `payroll_slip.py`, `payroll_reprocess.py`, the salary report, `hooks.py`, `portal.js`, three page parts, **one new module `leave_rules.py`** (section 2.2 says why) |
| `hrms` (our copy) | **No change** | `access.py` helpers called as they are (`is_own_record`, `refuse`, `refuse_own_decision`, `refuse_own_submit`, `permitted_employee_filters`). Frappe HR's Leave Application, Leave Type, Attendance and Attendance Request used as shipped |
| `frappe`, `erpnext` | No | `Document.discard` and `notification_log.make_notification_logs` called as shipped (both verified in v16.33.1) |
| `alvoraa_goals`, `alvox_compensation` | No | Nothing reads leave or the pay engine |

### 1.2 Every caller of every function I would change (grepped, whole repo)

| Function | Callers found | Effect on them |
|---|---|---|
| `payroll_rules.evaluate_day` | `payroll_rules_apply.judge`; tests `test_payroll_rules.py` (wrapper `judge(**kwargs)`) | Two new keyword arguments, both default off. Every existing call behaves as today |
| `payroll_rules.DayVerdict` | `evaluate_day`; `judge` (no-shift case); `test_payroll_month.py` builders | One new field `half_leave`, default False. `day_credit` unchanged when it is False |
| `payroll_rules_apply.judge` | `payroll_slip.month_summary`; `payroll_reprocess.preview` and `.run`; `evaluate_attendance`; `on_attendance_submit` | Reads three more attendance fields. Callers that do not fetch them (`evaluate_attendance`, the hook's doc) are updated to fetch them; a missing field reads as "not a half-day leave", so today's answer |
| `payroll_month.summarise_month` | `payroll_slip.month_summary`; `test_payroll_month.py` | Counters become decimals; E6 adds approved Paid Leaves days to the gate count **only when the caller passes them**. Existing tests pass `20 == 20.0` |
| `payroll_slip.month_summary` | the salary report; `push_marks_to_additional_salary`; `on_salary_slip_validate`; `test_salary_report.py`; **new: the card** | Reads `leave_type`, `leave_application`, `attendance_request`; counts approved Paid Leaves days; all three callers get E6 and halves (that is the point: card = report = slip) |
| `payroll_reprocess._attendance_rows` | `preview`, `run` | Three more fields in the list |
| `hr_api._can_action_leave` | `action_leave`; `_mark_actionable` (scorecard 1236, manager detail 1551); `test_portal_security_010` 329; `test_leave_permissions` (source pins) | New LWP branch after `is_own_record`, only where the company has an enabled rule set. Source pins still hold (`_can_action_leave` still in `action_leave`; no role list in `action_leave`) |
| `hr_api.apply_leave` | `portal.js` 4712; `test_leave.py`; `test_leave_permissions.py`; `test_portal_security_010` 427-433 | Same signature. New refusals: non-HR `on_behalf_of` (SEC-7), types off at a disabled rule set (SEC-2), Paid Leaves with no approver (SEC-12). Sets `leave_approver` for Paid Leaves |
| `hr_api.preview_leave_request` | `portal.js` 4628; `test_leave.py`; `test_leave_ledger_035`; `test_leave_permissions`; `test_portal_security_010` 442 | Same signature, more keys returned; existing keys unchanged |
| `hr_api.get_leave_summary` | `portal.js` 4459, 4525, 4587; `test_leave_ledger_035`; `test_numbers_match_035`; `test_portal_security_010` 444-508 | New keys `paid_leaves`, `types_offered`, and per-application extras; existing keys unchanged |
| `hr_api.get_all_active_employees` | `portal.js` 4545 (the on-behalf picker) only | Narrowed to `permitted_employee_filters()` (company **and** branch) and gains `no_login` (AC-93) |
| `inbox_api._part_leave_approvals` | `parts()` -> `get_nav_counts`, `get_inbox` | Filter widens with one OR branch (HR's LWP rows at an enabled-rule-set company). Same part, same key list plus three keys |
| `hooks.py` doc_events | Leave Application (`before_submit` today), Leave Type (cache hooks today), Attendance Request (060 hooks today) | Entries **added at the end** of each block; nothing removed |

Not changed, and pinned by tests that stay: `refuse_own_submit`, `refuse_own_decision`,
`_leave_approver_for`, `access.py` (0 bypasses), `attendance_correction.py` (0 bypasses - the OD-1
hook lives outside it), `rule_set_for` itself.

### 1.3 Personas

| Persona | What changes |
|---|---|
| **Employee at DTC** (Priya, 10 with a login) | Card "Paid Leaves - October" (own figures, days only); Apply list offers Paid Leaves and LWP; current-month-only, limit of 5; cancel a waiting request or an approved one before it starts; half-day leave counts 0.5; a missed punch on a half day is fixed by a half-day correction HR approves |
| **Employee at DTC with no login** (435) | Nothing on screen; HR files for them. Their pay follows the engine changes once the rule set is on |
| **Employee, other tenants** | LWP appears in the Apply list and follows their normal approval (D5). A non-HR user passing `on_behalf_of` is now refused instead of silently filed for themselves (SEC-7) - nobody should be doing that from the screen |
| **HR Manager / HR User at DTC** (7) | LWP requests of people in their scope in the Inbox, approvable there; files for staff with no login (branch-scoped picker); cancels as today on the desk; cannot approve their own |
| **Named leave approver / store manager** | Paid Leaves requests in the Inbox as today, plus the "managers up to X are told" line. Cannot approve LWP unless also HR in scope |
| **Managers up the Reports To chain** | One four-fact notice (name, dates, days, "approved") per approved leave below them. The top of the chain hears of every approved absence (Q6a) |
| **System Manager** | Changes the DTC rule set from the written list; creates "Paid Leaves" once; the type is then locked |
| **CXO** | No change |

### 1.4 HRMS domains

- **Leaves:** two types used (LWP exists; Paid Leaves created once by hand at DTC). No allocation, no
  ledger change (Paid Leaves has `allow_negative` 1, so Frappe's balance check passes).
- **Attendance:** half-day leave rows read differently by the engine; OD-1 (iv) marks the other
  half Absent on raising a correction and Frappe marks it Present on approval.
- **Payroll:** paid days move for DTC once the rule set is on (credits on the 1st by settings; E6;
  halves). Every other tenant has no rule set, so `rule_set_for` returns None and the engine does
  nothing - unchanged.
- **Org structure:** the Reports To chain picks who is told. Not the seat tree (slice 064).
- **Appraisals, goals, compensation:** not touched.

### 1.5 Non-functional verdicts (against the plan; re-checked against the code at step 5)

| Dimension | Verdict | Reason |
|---|---|---|
| **Performance** | **degrades slightly, inside budget** | The Leave page at DTC now runs `month_summary` for one person: about 100 queries for a 30-day month (01b estimate), the same at 20 or 400 staff. `prepare(..., employee=)` keeps the 363-row green table out. Budget 500 ms per call; measured in step 7, and if over, the first fix is one checkin query per month, not a cache. Inbox HR scope stays in the database. Chain walk at most 10 reads (2 at DTC). Other tenants: one extra `rule_set_for` lookup per leave call |
| **Security** | **improves, one deliberate widening** | New refusals: non-HR on-behalf, branch scope on-behalf, types off when the rule set is off, Paid Leaves with no approver, self-approval on every door. Widening by decision: LWP approval moves from one named person to the HR users in scope (SEC-3), and one new bypass for the employee's cancel (69 -> 70, after own-record and future-date checks). OD-1 (iv): an HR approval now stands in for a punch on half-day leave days (section 5.6) |
| **Reliability** | **improves** | Every refusal says why and what to do. The chain notice cannot fail an approval (wrapped; the "told" line reads rows actually created, so it never lies). The card failing never blocks the list or Apply. Engine changes are pure functions with tests |
| **Scalability** | **neutral** | Nothing grows with headcount per request. The limit check reads one person's LWP for one month. No job, no cache |
| **Maintainability** | **neutral to slightly degrades** | `hr_api.py` and `portal.js` grow (hot files). Kept in check by putting the DTC rules in one new module and making every rule ask `rule_set_for(company)`. No new DocType, field, setting or job |
| **Data integrity** | **improves** | One source for each number: credits = rule set `monthly_credits`; used and gate count = `month_summary`, which the slip and the report also use, so card = report = slip. No cache, so nothing to go stale. Limit and date rule sit on `validate`, so every door is covered and approval re-checks |
| **Compliance / privacy** | **improves, with one new flow** | Card is own-record only with a fixed key list, no rupees. Chain notice carries four facts, never type, reason, approver or job title. New flow: managers up the chain learn of approved absences (Surbhi's choice). No log line carries a name, reason or figure |

---

## 2 · The strategy

### 2.1 The rung for each part

| Part | Rung | Why the cheaper rung was rejected |
|---|---|---|
| LWP type | 1 - already there | - |
| Credits on the 1st (US-23) | 2 - configuration (rule set values) | - |
| "Paid Leaves" type (US-19) | 2 - one record, by hand, at DTC | A patch runs on every tenant (OPS-7) |
| Approvers for the people without one | 2 - data, by DTC HR | - |
| Lock on "Paid Leaves" (OD-8) | 4 - three doc_event lines | No per-record lock in Frappe; a Property Setter makes the whole Leave Type form read-only for every type. DevOps advised no lock; Surbhi chose a lock (D1). OD-8 still open |
| Date rule, limit of 5 (SEC-6, SEC-13) | 4 - a `validate` hook | The endpoint alone is not a gate: the Employee role can create through REST (verified by security) |
| HR approves LWP (SEC-3) | 4 - one branch in `_can_action_leave` + the Inbox filter | No Frappe setting gives "HR in scope approves this type" |
| Chain notice (PRIV-1) | 4 - code on `on_submit` | A Frappe Notification record can be edited by any System Manager to add the reason; security ruled it out |
| Employee cancel (SEC-8) | 4 - one endpoint, one bypass | Giving the Employee role `cancel` would let REST cancel past approved days |
| Card, previews, Apply list | 4 - inside existing endpoints | No new endpoint that takes its own employee argument (SEC-1) |
| E6, half-day rule, OD-1 (iv) | 4 - engine change | Config cannot express them (01e section 3) |
| New DocType, field, setting, job, cache, app | **none** | - |

### 2.2 Files to touch, by story group

| Group | Stories | Files |
|---|---|---|
| **A · Engine** | US-25 E6, US-26 half day, US-27 OD-1 (iv), US-20, US-21 | `payroll_rules.py` (`DayVerdict.half_leave`, `evaluate_day` two inputs), `payroll_rules_apply.py` (`judge` reads the flags; `evaluate_attendance` field list), `payroll_month.py` (halves; E6), `payroll_slip.py` (`month_summary` fields; Paid Leaves day count), `payroll_reprocess.py` (field list), `report/salary_components_and_workings/*.py` (Worked / On leave / Absent columns Int -> Float) |
| **B · Rules on every door** | US-6, US-9 (server), US-13, US-19, US-27 (the correction hook) | **new `leave_rules.py`**: `validate_leave_application` (SEC-6, SEC-13), `lock_paid_leaves` (validate / on_trash / before_rename), `prepare_half_day_correction` (Attendance Request `before_insert`, section 5); `hooks.py` (entries added at the end of the Leave Application, Leave Type and Attendance Request blocks) |
| **C · Filing and approving** | US-7, US-8, US-9, US-10, US-12, US-17 | `hr_api.py` (`apply_leave`, `preview_leave_request`, `_can_action_leave`, `get_all_active_employees`), `inbox_api.py` (`_part_leave_approvals` filter, three row keys) |
| **D · Chain notice** | US-11 | `leave_rules.py` (`notify_chain_on_approval`, on `on_submit`), `hooks.py` |
| **E · Cancel** | US-16 | `hr_api.py` (new `cancel_leave`), `leave_rules.py` (N-5, N-6 notices), `test_portal_security_010.py` ceiling 69 -> 70 with the endpoint named |
| **F · Card** | US-1..US-5, US-15 (server side) | `hr_api.get_leave_summary` (calls `leave_rules.paid_leaves_card(emp)`; adds `types_offered` and application extras) |
| **G · Screens** | US-1..US-4, US-7..US-18, US-27 row warning | `portal.js` (leave block only: `loadLeaves`, `_populateLeaveTypeSelect`, `openLeaveModal`, `laPreview`, `submitLeaveApp`, `renderLeave*`, new `lp*` functions for the card and cancel), `parts/attendance.html` (card in place of `#leave-rings` when `paid_leaves` is present), `parts/request-modals.html` (Apply pop-up), the Inbox row renderer (`next-inbox.js`), `translations/en.csv` |
| **H · Release** | US-22, US-23, US-24 | No code. `07-devops-inputs.md` section 5 (evidence), the rehearsal note |

**Why one new module rather than more of `hr_api.py`:** the hooks need a home anyway, `hr_api.py`
is the hottest server file and at its bypass ceiling, and putting every DTC rule beside the others
makes "each asks `rule_set_for`" checkable in one read. It starts at a bypass ceiling of **0** in
the SEC-16 test. It is one module with plain functions - no class, no registry.

### 2.3 "DTC only" - one check

Every rule calls the existing `payroll_rules_apply.rule_set_for(company)` with the **employee's**
company and does nothing when it returns None. No company or site name appears in code. The one
extra question - "is there a rule set that is switched off?" - is asked only where SEC-2 needs to
refuse (`apply_leave`, the Apply list): `frappe.db.exists("Alvoraa Payroll Rule Set", {"company": c})`.

| Rule | Where it asks |
|---|---|
| Card, Paid Leaves offered | `get_leave_summary` |
| Types refused when the rule set is off | `apply_leave`, `preview_leave_request` |
| HR approves LWP | `_can_action_leave`, the Inbox filter |
| Current month, limit of 5 | `leave_rules.validate_leave_application` |
| Chain notice | `leave_rules.notify_chain_on_approval` |
| Half-day engine rule, OD-1 (iv) | the engine itself (it already runs only with a rule set); the correction hook |
| Paid Leaves lock | the lock hook (any enabled rule set on the site) |

One table-driven test runs each rule with the rule set enabled, disabled and absent (AC-27).
`rule_set_for` uses `get_cached_doc`; switching the rule set off is a save, which clears that
document's cache, so the switch takes effect on the next request. Step 3 has a test for it.

### 2.4 HR approves LWP, in `_can_action_leave`

```
1. is_own_record(doc.employee)                     -> False   (unchanged, stays first)
2. LWP branch, only if all hold:
     Leave Type is_lwp = 1
     rule_set_for(employee's company) is not None
     caller holds HR Manager or HR User
     employee inside permitted_employee_filters()   (one exists() query, company AND branch)
   -> return frappe.has_permission("Leave Application", "submit", doc)
   An LWP at such a company that fails the branch -> False (a named non-HR approver cannot approve it)
3. Otherwise: the named-approver rule, unchanged.
```

`action_leave` already calls `refuse_own_decision` first and then this function, so the button and
the action keep one rule. Approval runs `doc.submit()`, which runs `validate` again, so the date
rule and the limit are re-checked at approval (AC-44, AC-69). `refuse_own_submit` keeps the desk
and REST honest. **LWP rows are filed with `leave_approver` empty** (spec 7.2), so they never land in
one person's approver queue.

### 2.5 The employee cancel, and why 69 becomes 70

New endpoint `hr_api.cancel_leave(leave_id)`:

1. Load the doc. If its `employee` is not the caller's own Active Employee (`_get_employee()`)
   **and** the caller is not HR with the employee inside `permitted_employee_filters()` -> refuse
   "You can only cancel your own leave." (rule 063-SEC-8). Checked in our code, not left to User
   Permissions (3 of 10 DTC logins have none).
2. Open, draft -> `doc.discard()` **as the user** (0 bypass; proven on the bench). N-5 notice.
3. Approved, `from_date` after today, and the caller is the employee -> `doc.flags.ignore_permissions = True`
   on this one document, then `doc.cancel()`. **This is the +1.** N-6 notice, no chain notice.
4. Approved, today or earlier -> refuse "This leave has started, so only HR can cancel it." HR keeps
   the desk, as today.
5. Anything else -> refuse with the reason.

**Why the bypass is the right price:** the Employee role has no `cancel`, and giving it one would let
REST cancel past approved days (SEC-8). The bypass sits on one document, after the own-record and
future-date checks. The ceiling comment names `cancel_leave`. No new `allow_guest`.

### 2.6 The limit of 5 and the current-month rule, on `validate`

`leave_rules.validate_leave_application(doc, method)` - hooked on Leave Application `validate`,
added beside the existing `before_submit`:

- Return at once unless `rule_set_for(company)` is set (DTC only).
- Skip when status is Cancelled or Rejected (freeing days must never be refused).
- **Date rule:** any day before the 1st of the **current** month (server date) -> refuse with the
  first sentence of AC-68, or AC-69's sentence when the leave is being approved. Binds HR on the desk
  too (OD-4).
- **Limit (LWP only):** for each calendar month the request touches, read this employee's other LWP
  applications that are Open or Approved and overlap that month (one query), count each one's days
  inside the month with Frappe's own `get_number_of_leave_days` (half = 0.5, follows
  `include_holiday`), add this request's in-month days, refuse over **5** with AC-43's message.
  `LWP_MONTH_LIMIT = 5  # Surbhi, 21 Oct 2026` - a constant, no setting.
- Uses `frappe.throw` (a business rule), not `refuse()`; nothing personal in the message.
- Needs no bypass: it only reads.

### 2.7 The chain notice walk

`leave_rules.notify_chain_on_approval(doc, method)` on Leave Application `on_submit`:

- Only when status is Approved and `rule_set_for(company)` is set.
- Walk `Employee.reports_to` from the person: stop at no manager, at a person seen before (one
  `refuse`-style security-log line with ids only, no throw), at a non-Active manager, or after 10
  steps. Skip the employee themselves and anyone already told. One `get_value` per step.
- Recipients = the managers' `user_id`s; Frappe's own `make_notification_logs` keeps only enabled
  users and creates one desk bell each, and sends the email where the user's notification settings
  allow (production email is muted until go-live). Called directly, not through the after-commit
  queue, so the "told" count read straight afterwards is true.
- Subject and body built from four facts only: name, dates, days, "approved" (AC-58). The Notification
  Log stores `document_type`/`document_name` so "who was told" is answerable a year later and the
  "told" line can count rows. Opening the link still needs the manager's own read permission - no
  widening.
- Wrapped: a failure writes an Error Log titled with the document name only and never blocks the
  approval.

### 2.8 Half day, E6, OD-1 (iv) in the engine - and the tests that change

**`payroll_rules.evaluate_day`** gets `half_day_leave=False` and `other_half_regularised=False`.
When `half_day_leave` is set:

| Punches on the day | Verdict |
|---|---|
| 2 or more | Worked half measured against **half the shift**; slab quarters capped at 2 before any doubling; **no** late, early or late-window charge; **no greens**; reds only from the slab |
| fewer than 2, and `other_half_regularised` | Worked half counted in full: 0 quarters, no reds, no greens (OD-1 iv) |
| fewer than 2, not regularised | Other half **absent**: 2 quarters, doubled on a special day for staff who double |

`DayVerdict.half_leave = True`; `day_credit` = 0.5 minus a quarter-day per quarter for a worked half,
or minus only the quarters above 2 for an absent half (the same "do not charge the day twice" rule
the full absent day uses, at half size).

**`payroll_rules_apply.judge`** sets `half_day_leave` when status is "Half Day" **and**
`leave_application` is filled (an automatic "Half Day" with no leave keeps today's treatment; DTC has
22 such rows today), and `other_half_regularised` when `attendance_request` is filled and that request
is submitted (one `get_value`, only on half-day-leave days with fewer than two punches).

**`payroll_month.summarise_month`:** a half-leave verdict adds 0.5 to worked (or 0.5 to absent) and
0.5 to on leave. **E6:** when the caller passes `approved_leave_days` (Paid Leaves days), the gate
compares `days_worked + approved_leave_days` with the threshold, and the same figure drives "used"
(U1). When nobody passes it (old tests), behaviour is today's.

**`payroll_slip.month_summary`** reads `leave_type`, `leave_application`, `attendance_request` and
counts approved Paid Leaves days from the same attendance rows (On Leave = 1, Half Day with a Paid
Leaves leave = 0.5) and passes them. So the slip, the report and the card all get E6 and U1.

**Credits on the 1st need no code** (01e section 3): the rule set values do it.

**Tests that change (wording or figures):**

| Test | Change |
|---|---|
| `test_payroll_rules.py` 495-583 (leave-credit class) | Still pass. Docstrings that call the 7.5-day cadence "DTC's rule" are corrected - words only |
| `test_payroll_month.py` `test_a_leave_day_is_not_a_day_worked` (138) | Still true for LWP and for callers that pass nothing; a sibling test pins E6 |
| `test_payroll_month.py`, `test_salary_report.py`, `test_payroll_reprocess.py`, `test_day_marks.py` fixtures | Unchanged figures (they set their own cadence values). Run once to prove nothing compares counters by type |
| `test_portal_security_010.py` CEILINGS | `hr_api.py` 69 -> 70 (comment names `cancel_leave`); new row `leave_rules.py: 0` |

**New engine tests (CI, no site data):** half day with the worked half complete, short, one punch,
no punches; the same on a special day (double and single-deduction staff); regularised with no
punches; an automatic "Half Day" with no leave unchanged; no green on a half-day leave day even with
an early punch; gate at 14.5 and 15; E6 with approved and with Open Paid Leaves; half-day LWP equals
half-day Paid Leaves in pay; quarter cap of 2.

### 2.9 The card payload - the fixed key list

Built inside `get_leave_summary`, **only when `emp` is the caller's own record** and the company has
an enabled rule set. Built by naming each key; `MonthSummary` is never turned into a dict.

`month`, `class`, `earns`, `credited`, `used` (with `used_dates`, halves marked), `waiting`,
`to_be_paid_out`, `approver`, `lwp_in_play`, and **only while under the gate** `attended_so_far` and
`gate`; or `error: true` and nothing else.

- `credited` = the class row's `monthly_credits`; `earns` = that > 0 and the category earns.
- `used` and `waiting` from this person's Paid Leaves applications in the month (half = 0.5, a request
  across months counted day by day). `waiting` counts Open only.
- `attended_so_far` = `month_summary`'s days worked + approved Paid Leaves days (E6).
- `to_be_paid_out` = max(0, credited - used - waiting).
- `lwp_in_play` serves R-15 and the Apply list (the LWP limit figure is the employee's own).
- **Never:** any rupee field, `paid_days`, reds, greens, notes, the Basic. SEC-1's test asserts the
  key set **equals** this list. `prepare()` is called with `employee=`.
- On an exception: Error Log titled with the employee id only; `{"error": true}`; the list and Apply
  still load (AC-16, PRIV-5).
- Two keys SEC-1 rev. 3 still lists (held-day count and dates) are **left out** - the v3 card does not
  show them. Security to confirm (spec Q-1).

### 2.10 Release stories - settings change and rehearsal

**US-23 · the DTC rule set values (desk, by a System Manager, local copy first):**

| Field | Old (today, read on DTC 21 Oct) | New | Rollback |
|---|---|---|---|
| `leave_threshold_days` | 15 | 15 | - |
| `accrual_month_days` | 30 | **15** | 30 |
| Class A `period_days` / `credit_per_period` / `monthly_credits` | 7.5 / 1 / 4 | **15 / 4 / 4** | 7.5 / 1 / 4 |
| Class B | 10 / 1 / 3 | **15 / 3 / 3** | 10 / 1 / 3 |
| Class C | 7.5 / 0.5 / 2 | **15 / 2 / 2** | 7.5 / 0.5 / 2 |
| `enabled` | 0 | 1 - **only after RC-4, Surbhi's word** | 0 (the faster rollback: one tick) |

A comment on the record quotes Surbhi's 21 Oct decision. The Version row keeps old and new values.
No patch, no script on production.

**Other data at DTC, by hand:** "Paid Leaves" Leave Type (`is_lwp` 0, `allow_negative` 1,
`include_holiday` 1, no encashment, no carry forward, not earned); DTC HR names Paid Leaves approvers
for staff with none (01b counted 51); release checks RC-7 to RC-12 as the spec lists.

**Settings vs code:** everything a client might want to change (credits, gate, special days, who is
whose approver) stays data. Code holds only rules Surbhi stated as rules: the limit of 5, current
month only, who approves LWP, the four-fact notice, the half-day treatment.

**US-24 · rehearsal on a local copy:** a fresh throwaway container with a copy of DTC data (never
`hrlocal-bench`'s shared sites, never dtc.alvoraa.co); apply US-23 there; switch the rule set on there
only; run the ten SEC-14 items including the **extra October cost against accrual** (summed from the
report, both rule set versions) and **item 9 = OD-1 (iv)** (section 5.5); time the rollback. Output
kept as release evidence in `07` section 5. Nothing goes to DTC until all ten pass and Surbhi says so.

### 2.11 Order of work - thin steps, each green

Each step ends with its own module tests passing; the full suite runs once at the end
(change-process rule 4).

| Step | What | Proves |
|---|---|---|
| 0 | New worktree `.claude/worktrees/063-dtc-leave` on `slice/063-dtc-leave` from `origin/dev`; bring the 063 doc commits across; work-board row | - |
| 1 | **Bench proof for OD-1 (iv) on a row that carries a shift**, plus the Attendance Request hook (`prepare_half_day_correction`) and its test | The trap in bad news 2 |
| 2 | Engine: half day, E6, regularised half (pure functions + tests) | AC-109..115, 117 at unit level |
| 3 | Engine plumbing: `judge`, `month_summary`, reprocess, report columns; slip tests (SEC-10) | AC-99..102, 110 |
| 4 | `leave_rules.validate_leave_application`, the lock, SEC-2 refusals and SEC-7/SEC-12 in `apply_leave`; the table-driven DTC-only test | AC-24..28, 32, 36, 37, 42..46, 66..70, 91, 92, 96..98 |
| 5 | `_can_action_leave` LWP branch + Inbox part | AC-47..56 |
| 6 | Chain notice | AC-57..62 |
| 7 | `cancel_leave` + N-5/N-6 + ceiling 70 | AC-83..90 |
| 8 | Card block, `types_offered`, preview payload, application extras; query count at 20 and 400; one timing on the bench | AC-1..23 (server), AC-23 |
| 9 | Screens; walk all 75 parity rows on the running page; 390 px and 200% zoom | AC-1..16, 29..41, 63..95 (UI) |
| 10 | Full suite once (throwaway container); integrity script; then stop for review | - |

---

## 3 · Risks, trade-offs, and what I would NOT build

### 3.1 Risks

| Risk | Level | Handling |
|---|---|---|
| A pay mistake in the engine change reaches DTC payslips | High if switched on unproven | Pure-function tests + rehearsal on a local copy + Surbhi's word before switch-on |
| OD-1 (iv): HR approval pays a half with no punch evidence | Medium | Section 5.6 |
| If HR later **cancels** an approved half-day correction, Frappe's own `on_cancel` cancels every attendance row linked to it - the whole half-day leave row with it | Medium | Release note for HR: decline before approving, never cancel after; the rehearsal includes this case so we see what it does |
| `hr_api.py`, `portal.js`, `hooks.py`, `inbox_api.py` are hot files | Medium | Hot-file rules: new functions, entries appended, no reformatting; rebase often; pin tests per feature |
| The card costs about 100 queries a load | Low (10 users) | Measured in step 8 against 500 ms |
| The chain top learns of every approved absence | Accepted by Surbhi (P3), to confirm (OD-7) | - |
| LWP approval widens from one person to 7 HR users | Accepted by Surbhi | - |
| The Team View "Pending Approvals" count still counts only named-approver rows, so it does not include HR's LWP queue | Low | The Inbox is where HR acts (spec). Written down, not built |
| Slip hook fails open (Frappe's figures stay) | P2, pre-existing | Unchanged by this slice |

### 3.2 What I would NOT build

- No new DocType, field, setting, page, report, job, cache or app.
- No Frappe `Notification` record for the chain notice.
- No server-side cap on Paid Leaves "left" (AC-34 says the server does not enforce it).
- No Leave Block List (dropped).
- No "Remind HR" button (V2 default: words only).
- No first-half / second-half choice (01d D7).
- No change to `attendance_correction.py` - the OD-1 hook sits on the Attendance Request doctype, so
  the 060 flow stays exactly as written and approved.
- No fix for F-1 (other tenants' empty `leave_approver`), F-2 (`month_summary` ignores held-day
  confirmations), F-3 (`_hr_target_employee` company-only), F-4. Each is written down for Surbhi.
- Hindi is supplied as a file but not switched on (X-5).

### 3.3 The bench checks the spec asked for

| Check | Answer | How (nothing written to any server) |
|---|---|---|
| Q-3 Does `apply_leave`'s insert leave `leave_approver` empty? | **Yes, empty.** Frappe's validate does not fill it; only the desk form's script does | Local `test_site`, one transaction rolled back, commits blocked |
| Q-2 Does `discard()` work when the employee calls it? | **Yes**, for their own Open request: status Cancelled, docstatus 2. That employee had a User Permission on their own record | Same probe, run as the employee's user |
| OD-1 (iv) Can a correction be raised on a half-day leave date? | **Not as Frappe ships it** (refused both ways). **Yes** once the other half is marked Absent; on approval Frappe sets it Present and links the request | Same probe. Not yet proven with a shift on the row (bad news 2) |
| Q-4 Does the portal page load Hindi? | **From the code, no.** `drT` uses `window.__` if present, and `alvoraa_portal` has only `translations/en.csv`; nothing on the page loads a translation dictionary. Not checked by running (needs a signed-in browser session) | Code read |
| Q-5 How many DTC staff have an email? | **0 of 445 active** have a personal, company or preferred email; 10 have a login. Frappe's status email goes to `prefered_email`, `user_id`, company or personal email - so only the 10 can be told by email | Read-only counts on dtc.alvoraa.co (no writes, no names) |

---

## 4 · Size and commit plan

**Estimate:** 13 files changed (8 Python, 1 report, `hooks.py`, `portal.js`, 2-3 page parts, `en.csv`)
plus 1 new Python module. About 700-900 lines of Python, 500-700 of JS/HTML. Tests: 5 new files
(`test_leave_063_engine.py`, `test_leave_063_rules.py`, `test_leave_063_approval.py`,
`test_leave_063_cancel_notice.py`, `test_leave_063_card.py`), 70-90 new tests, plus edits to
`test_portal_security_010.py` (ceilings). Story points in the spec: 75. Honest guess: 4-5 working
sessions including the rehearsal.

**Commits** (one concern each, in the worktree, never pushed without Surbhi's word):

1. Half-day leave corrections reach the right attendance row (the hook + test)
2. The pay engine counts a half-day leave as half leave, and approved Paid Leaves toward the 15
3. The slip, the report and the reprocess read the half-day and Paid Leaves facts
4. At DTC, leave is current-month only, LWP is capped at 5, and Paid Leaves is locked
5. HR in scope approves leave without pay; Paid Leaves keeps its named approver
6. Managers up the chain are told when a leave is approved
7. An employee can cancel their own leave before it starts (ceiling 69 to 70)
8. The Leave page carries the month's Paid Leaves, days only
9. The Leave page, Apply pop-up and Inbox match prototype v3
10. (docs) implementation notes

---

## 5 · OD-1 remedy (iv): half-day regularisation, no punches - feasibility

**Verdict: feasible, with one small hook and a small engine change. Not feasible as "the engine
just reads an approved request", because Frappe will not create the request.**

### 5.1 What the code and the bench show

- The engine judges a day only from Employee Checkin punches (`judge` -> `_punches`); status is
  read only for Absent and On Leave.
- Frappe's Attendance Request, on a date with an approved half-day leave, **refuses at insert**:
  - half-day ticked -> "Attendance status unchanged - Skip" (the leave already wrote the other half
    as Present);
  - not ticked -> "On Leave - Skip".
  Both end in "No attendance records to create" (bench, rolled back).
- **But Frappe has a designed path for exactly this case:** if the attendance row is "Half Day" with
  the other half **Absent**, a half-day Attendance Request is accepted, and its approval sets the
  other half to **Present** and fills `attendance_request` on the row (bench: confirmed).

### 5.2 The design

1. **Hook, Attendance Request `before_insert`** (`leave_rules.prepare_half_day_correction`), runs
   before Frappe's `validate`. Only when all hold: the company has an enabled rule set; the request is
   one day with the half-day tick on that day; that day's attendance is "Half Day" with a
   `leave_application`; the day is before today; and it has fewer than two punches. Then:
   - copy the attendance row's `shift` onto the request (DTC rows carry a shift; DTC has no Shift
     Assignments - bad news 2);
   - set the row's `half_day_status` to "Absent" (a true fact: no punches for it), with
     `update_modified=False`, through `frappe.db.set_value`.
   If the insert then fails for any other reason, the transaction rolls back and the row is unchanged.
2. **Frappe does the rest:** HR approves through the existing 060 `decide` (the raiser is never the
   decider; `refuse_own_submit` on every door); Frappe sets the other half Present and links the
   request. Declined -> the half stays Absent, which is the truth.
3. **Engine** (`judge`): a half-day leave day with fewer than two punches counts the other half as
   **fully worked** (no quarters, no absence, no reds, no greens) when `attendance_request` is filled
   and that request is submitted. Otherwise the half is absent (doubled on a special day for staff
   who double).

### 5.3 Exactly where it goes

| Place | Change |
|---|---|
| `payroll_rules.evaluate_day` | `other_half_regularised` input (section 2.8 table) |
| `payroll_rules_apply.judge` | Sets it from `attendance_request` + one `get_value` of that request's docstatus |
| `payroll_rules_apply.evaluate_attendance`, `payroll_slip.month_summary`, `payroll_reprocess._attendance_rows` | Add `leave_application`, `leave_type`, `attendance_request` to the fields read |
| `leave_rules.prepare_half_day_correction` + `hooks.py` Attendance Request `before_insert` | The hook above |
| `portal.js` | The row's "Ask HR to correct {date}" opens the existing correction form for that date with the half-day box ticked |

### 5.4 Which requests the engine trusts

- **Any reason** on the 060 list. The reason is the employee's explanation; what makes it count is
  that someone other than the employee approved it. "Work From Home" also lands as "Half Day" on a
  half-day request, so it is treated the same.
- **Only submitted** (docstatus 1). A waiting, declined (draft with "Declined") or withdrawn request
  counts for nothing; Frappe only links a request to the row when it is submitted anyway.
- **Who approved:** whoever holds submit on Attendance Request under 060 (`_may_review`) - HR, or a
  direct manager acting in their own capacity. Surbhi said "HR approves". **Question OD-1a below:**
  trust any approved request (my recommendation - one rule, the 060 rule), or only those whose
  `alvoraa_decided_as` is HR.

### 5.5 How the rehearsal proves it (AC-117, AC-118, SEC-14 item 9)

On the local copy with the rule set on there only: a past half-day leave day with one punch and
another with none, **on rows that carry a shift**:
1. the employee raises the half-day correction from the portal -> accepted; the row's other half reads
   Absent; the slip shows that half absent;
2. HR approves -> the row's other half reads Present and is linked; saving the slip again counts the
   half as worked (0.5 + 0.5 leave), not doubled on a special day;
3. the same with HR declining -> stays absent;
4. an approved half-day correction later cancelled on the desk -> recorded as found (section 3.1 risk).

AC-118 holds: the DTC rule set is not switched on until this passes and Surbhi says so. The row
warning's wording (R-27, AC-116) stays as drawn, because under (iv) "HR approves a correction" is now
true.

### 5.6 The pay risk, said plainly

- **An HR approval replaces punch evidence** for half a day. Bounded: half-day leave days only, at
  most 0.5 day each, the subject can never approve their own (portal, desk, REST), the raiser is never
  the decider (060), and the record keeps who raised, who approved and when.
- **It treats a half day more generously than a full day.** A full day corrected with no punches is
  still **held** by the engine today (ATT-06: "no punches, marked present -> held"); a half day
  corrected with no punches will be **paid**. That is what Surbhi asked for; she should see the
  difference (OD-1b).
- NFR: one extra `get_value` only on half-day-leave days with a missing punch; no new bypass (the hook
  writes one engine-owned fact through `frappe.db.set_value`, which the reviewer must check by eye
  because the bypass counter cannot see it); no personal data in any log.

### 5.7 Tests

- Engine (CI): regularised half with 0 and 1 punches -> 0.5 worked, no quarters, no greens; not
  regularised -> absent half, doubled on a special day; a request that is only a draft does not count.
- Hook (site): fires only at an enabled rule set, only for a past, single, half-day-ticked day with a
  half-day leave and fewer than two punches; copies the shift; sets the other half Absent; does
  nothing at another tenant; a full day request is untouched.
- End to end (site): raise -> approve -> `month_summary` counts the half; decline -> it does not.

---

## 6 · Parallel-work check

| File | Hot? | Who else is in it | Plan |
|---|---|---|---|
| `hr_api.py` | yes | origin/dev last 7 days: ALV-199 and 060 commits; no open work-board row in the leave functions | New functions; existing ones changed only in their leave branches; rebase before each step |
| `portal.js` | yes | slice 064a (worktree from this one) edits `posPaint`/positions | Split: I touch only the leave block (4455-4760) and add `lp*` functions |
| `hooks.py` | yes | - | Append entries at the end of three blocks, with a comment |
| `inbox_api.py` | medium | - | One part's filter and rows only |
| `payroll_*.py`, report | no open work | slice 059 engine (already on dev) | Sequence: 059 is in; I build on it |
| `attendance_correction.py` | yes (060) | 060 work | **Not touched** |
| `test_portal_security_010.py` | shared | any slice adding a file | One ceiling edit, one new row |

- **This worktree** (`060-manager-review`) is now on branch `slice/062-widget-after-checkin`, and the
  063 docs sit on it as commits plus untracked files. I will not build here: the build gets its own
  worktree from `origin/dev`, and the 063 doc commits are brought across.
- **Main checkout** has another session's uncommitted edits to `.claude/context/definition-of-ready-done.md`
  and `ux-learnings.md`. Not mine; not touched.
- **Incoming:** `origin/dev` holds nothing this branch lacks (checked 21 Oct).
- **Other developers:** I cannot see other machines. Surbhi, is anyone else working in `hr_api.py`'s
  leave functions, `inbox_api.py` or the pay engine?
- **Pin tests:** every commit carries a test named for its feature (section 4), so a bad merge fails CI.

---

## 7 · Questions for Surbhi before I build

**OD-1 (iv) - the chosen remedy, three small confirmations**

- **OD-1a** Trust any approved half-day correction (HR or the direct manager, as 060 allows), or only
  ones HR decided? *Recommend: any approved - one rule.*
- **OD-1b** A half day corrected with no punches is paid; a full day corrected with no punches stays
  held. Accept the difference? *Recommend: accept for now, and ask DTC about full days separately.*
- **OD-1c** Raising the correction marks the other half "Absent" on the attendance record until HR
  approves (it is true, and it is what lets Frappe accept the request). Accept? *Recommend: yes.*

**Engine detail the spec leaves open**

- **E-a** On a special day, a short worked half: cap the quarters at 2 **before** doubling (so the
  worst case equals an absent half, doubled)? *Recommend: yes.*
- **E-b** One punch on a half-day leave day: the half is **absent** until corrected (spec), not
  **held** as a full one-punch day is. Confirm? *Recommend: absent, as the spec says.*

**The five conflicts**

- **X-1** Resolved by (iv): the row's warning and "Ask HR to correct" stay as drawn.
- **X-2** HR filing on behalf sees no Paid Leaves figure for the person (SEC-1c). *Recommend: keep.*
- **X-3** "(up to 22 Oct)" on the under-15 line - needs security to add one key. *Recommend: add it.*
- **X-4** "has been told" only when an email exists. The data now says 0 of 445 have an email on the
  Employee record and only 10 have a login. *Recommend: keep the interim wording permanently.*
- **X-5** Hindi supplied, not switched on, until a native reviewer signs off and the page is shown to
  load it. *Recommend: keep.*

**Design confirmations (drawn defaults)**

- **V1** Paid Leaves approved by the named leave approver, as today? *Recommend: yes.*
- **V2** "Remind HR" as words, no button? *Recommend: yes.*
- **V4** Under 15 days, show "To be paid out 4 ... once you reach 15 days"? *Recommend: yes.*
- **S1-S5** Four-fact notice; no cancellation notice to managers; no type on Team View; name only on
  the HR row; "Only the person who approves it and HR can read this." *Recommend: yes to all five.*

**Also open in the spec**

- **OD-7** The top of the chain learns of every approved absence - confirm.
- **OD-8** Lock "Paid Leaves" in code (D1), against DevOps' advice? *Recommend: lock (three small hooks).*
- **SEC-7 scope** The non-HR `on_behalf_of` refusal applies to **every tenant**, not only DTC (it is a
  silent-misfiling bug everywhere). Confirm? *Recommend: every tenant.*
- **F-1..F-5** Separate YouTrack tickets? *Recommend: yes, not in this slice.*

---

## Subtract pass

Removed while writing: a separate Inbox part for HR's LWP (one OR branch in the existing part does
it); a second "is this DTC" helper (every rule calls `rule_set_for`); reading the Leave Application
from the engine (the attendance already carries the link); a background job for the chain notice
(Frappe's own `make_notification_logs`, called directly); a "told" field (Notification Log rows are
the record); a change to `attendance_correction.py` for OD-1 (a doctype hook keeps 060 untouched);
a change to `_hr_target_employee` (F-3 stays outside; the branch check sits in the two leave
endpoints). Kept and why: the new `leave_rules.py` module (the hooks need a home and `hr_api.py` is at
its ceiling); the lock (Surbhi's D1, pending OD-8).
