---
slice: 084-employee-regularisation-window
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-11-19
status: draft, for Surbhi's read
inputs: [01-product-brief.md (Gate 1), 01a-ux-opportunities.md, 01b-ux-design.md (Gate 2), 01c-security-privacy-requirements.md (Gate 3), 07-devops-inputs.md §1-4, 02a-strings-that-become-false.md]
---

# 084 Spec: how far back an employee can raise their own day

## 0. Read this first

**Bad news first.**

1. **Surbhi's brief says the guard is a `before_insert` hook. That is not enough.** The Employee role holds `write=1` on `Attendance Request` with no `if_owner` (read from `hrms/hrms/hr/doctype/attendance_request/attendance_request.json`: Employee = `create 1, delete 1, read 1, write 1`). So an employee can raise a request for *today* (allowed), then open the draft and change `from_date` to six months ago. `before_insert` runs only on insert (Frappe's own rule, inferred: Frappe source is not on this Mac). **The spec therefore asks for a `validate` hook that checks when the record is new or its dates changed** (AC-12). Same hook file, same "own record" test, one more condition. This is a correction to requirement 5's *mechanism*, not to its intent. It needs Surbhi's nod (Q1).
2. **An HR Manager's own old day cannot be fixed by themselves on any route**, including the Desk, because the hook binds the *record*, and `refuse_own_submit` already stops them approving it. Another HR person must raise or decide it. That follows from Gate 3 decisions C3 and requirement 5, but Gate 3 calls it "one extra click". On a tenant with one HR person it is a dead end (Q2).
3. **Three more places will say something false on release day** beyond the six in `02a` (section 9, AC-49). One of them is a test docstring.
4. **No test exists today for any new behaviour.** Every AC below names a test to be written. Nothing here is "covered" yet; where I write "covered" in the traceability table I mean "an AC with a named test exists".
5. **The Hindi is a machine draft and phone/200%-text checks were never run** (Gate 2). Both are release gates here (AC-66), with no owner named yet (Q4).

**Tier.** The brief says Tier 2. `usage-discipline.md` §1 puts "who can see or change what" in Tier 1, and this slice adds a refusal hook on a doctype, a write guard path and a security log line. **Recommendation: build and review as Tier 1** (strong engineer, independent reviewer, separate security verification). When unsure, go one up. Surbhi decides.

**What I read.** Checkout `/Users/mac/hr-app`, branch `dev`, SHA `a57764c4` (`git rev-parse --short HEAD`, this session). Files, with lines as they are at that SHA (match on text, not number, because lines move): `alvoraa_portal/alvoraa_portal/hr_api.py` 301-311, 2886-2902, 2992-3030, 3311-3335, 3383-3420, 3447-3455; `attendance_correction.py` 277-295, 364-396, 488, 640-725, 1105-1160, 1278-1345, 1370-1460; `hooks.py` 179-191, 249-262; `leave_rules.py` 425-450; `employee_field_rights.py` 50-57, 203; `hrms/hrms/alvoraa_hr_core/access.py` 28-62, 184-190; `hrms/hrms/hr/utils.py` 216-228; `attendance_request.json` (permissions), `attendance_request.py` 25-50; `hr_settings.json`; `public/js/ess/portal.js` 6190-6250, 6303-6335, 12140-12175, 23400-23545; `templates/includes/ess/parts/org-settings.html` 115-160; `parts/requests.html` 38-85; the prototype file `/Users/mac/hrlocal-data/prototypes/084-employee-regularisation-window/prototype-v1.html` (its `L` string table and `guard()`); the tests named in section 9. I did **not** open the claude.ai artifact link (the local file is the same prototype per 01b). **Not run:** any test, any bench, any browser. **Not checked:** per-tenant Custom DocPerm; Frappe/ERPNext source (not on this Mac); whether `frappe.logger("security").info` is written (see Q6).

## 1. Cross-module reach

| Area | Touched? | How |
|---|---|---|
| `alvoraa_portal` | **Yes, all code** | `attendance_correction.py`, `hr_api.py`, `hooks.py`, `portal.js`, `org-settings.html`, `requests.html`, tests |
| `hrms` (Frappe HR) | Read only | `Attendance Request` DocType and its `validate` are unchanged; our hook rides in `doc_events` |
| `erpnext` | Read only | `Employee` (`date_of_joining`, `holiday_list`, `user_id`), `Holiday List`/`Holiday` |
| `frappe` | Uses | Frappe defaults (settings storage), `doc_events`, `logger` |
| `alvoraa_goals`, `alvox_compensation` | **No.** Grep for the manager key in the main checkout (`--include py/js/html`, excluding `.claude`, `node_modules`) found it only in `attendance_correction.py` and `portal.js`; `hr_api.py` imports it by name | -- |

HRMS domains: **attendance** (the slice). **Payroll** indirectly: a refused correction can leave a day Absent, and Absent can cost pay. **Leaves** coexist: `leave_rules.prepare_half_day_correction` is an existing `before_insert` on the same doctype and must keep working (AC-25 neighbours). **Appraisals** (attendance in score) read the result. Org structure, goals, compensation, learning: none.

Personas: **Employee** (lives under it), **HR Manager** (sets it), **CXO / System Manager** (`_require_hr` lets System Manager write the setting; the brief treats CXO as not touched, so the matrix says "can, not expected to"), **line manager** and **skip-level manager** (must not be bound; must not learn a joining date), **store-scoped HR** (reads, cannot save), **frontline employee** (phone, Hindi).

## 2. Question the ask

- **Is the stated problem the real one?** Yes, and it is dated: on 19 Nov 2026 a Grace joiner was refused their joining day, 11 Nov, by a hidden script that said "48 hours" and allowed three days (brief §2). That is a cause (a rule nobody could see, written by hand beside code), not just a symptom. The fix is a visible setting whose words come from the same function as its behaviour.
- **What decision does it drive, and could the system act instead?** HR decides the number. The system then refuses automatically, but **nothing about a person is decided**: a refusal only closes one route; HR's route stays open and is named in every refusal. Accountable human: the HR Manager who set the number, and HR who decides each request (the Employee role has no `submit`, `refuse_own_submit` blocks self-approval). The employee is told the date before they type and again in the refusal. They contest it by telling HR.
- **Automation test.** We are not automating chaos: today's process (no limit) is replaced by a rule HR chooses, defaulting to the old behaviour.

## 3. Gap analysis

| Requirement | What exists today (read) | Verdict | Cost |
|---|---|---|---|
| A days-back limit on an employee's own day | Frappe HR ships none for `Attendance Request`: `validate()` runs `validate_active_employee`, `validate_dates`, `validate_shifts`, `validate_half_day`, `validate_request_overlap`, `validate_no_attendance_to_create` (`attendance_request.py:44-50`). Its only back-dating control is `restrict_backdated_leave_application` + `role_allowed_to_create_backdated_leave_application` in `hr_settings.json` (lines 34-35, 107), for **leave** | **Extend** (new code, rung 4). Configuration alone cannot do it | S |
| Where the number lives | Manager key `alvoraa_manager_filing_window_days`: a Frappe default through `set_org_setting` (`hr_api.py:3383`), allow-list `ALLOWED_ORG_SETTINGS` (`hr_api.py:3311`) | **Configure** (reuse the mechanism; one new key, `alvoraa_employee_filing_window_days`). No DocType, no Custom Field | S |
| Counting working days on the person's own list | `_working_days_away` (`attendance_correction.py:1278`), "ONE counter, two callers" | **Reuse as is** | -- |
| Joining date ≥ rule, no overlap, active employee, from ≤ to | Already enforced by Frappe HR `validate` (`hr/utils.py:216-228`, `attendance_request.py:44-50`), also when `ignore_permissions=True` (security read; hooks and `validate` still run, **inferred**, AC-10 proves it) | **Already there. Do not respecify** | -- |
| Binding all three ways in | Two portal endpoints plus Desk/REST (Employee has create+write) | **Extend**: one `validate` hook on `Attendance Request` for the caller's own record. Hooks entry exists (`hooks.py:179-191`; value is a string today for `before_insert`, so it becomes a list or a second key) | S |
| The boundary shown before typing | Day sheet already shows a server boundary for managers (`portal.js:6200-6209`, `can_request_from`); `#att-req` already calls `get_requests_history` on open (`portal.js:12140-12147`) | **Extend** existing payloads. **Drop** a new endpoint | S |
| Blank must be saveable | One-key special case `if key == MANAGER_FILING_WINDOW_KEY and value == ""` (`hr_api.py:3395`) | **Extend** (one line) | S |
| Who changed an org setting | `set_org_setting` writes `frappe.db.set_default` + commit and nothing else (`hr_api.py:3383-3420`) | **Extend**: one `frappe.logger("security")` line, six keys | S |
| Six (nine) false strings | `02a` | **Extend** (edit text) | S |
| Cap on number of requests, refusal log/metric, per-company window, "contact HR" button, future-date check, removing Grace's script | -- | **Drop / out** (Surbhi, Gates 1-3) | -- |
| "Fewer wasted submissions" measure (brief §10) | No refusal row, access logs off in places (OPS-13) | **Drop**; replace with the one-off per-tenant count (AC-59) | S |

**Rung:** 2 (a stored setting) plus 4 (a few lines in two existing modules and one hook). Rejected cheaper rungs: *already there* (Frappe HR has no limit); *configuration only* (nothing in HR Settings or `Attendance Request` can express "N working days on the person's own list, except joining day"); *Server Script* (the exact thing that failed at Grace: invisible, no test, words drift). Rejected dearer rungs: a new DocType or a policy record (banned list, brief §3a).

**Single source of truth.** One function in `attendance_correction.py` gives the oldest allowed day and the basis for an employee; the guard, the month payload, the history payload and the HR save line all call it. The manager function `manager_filing_from` stays as it is and reads its own key.

## 4. Process flow

1. HR opens Org settings > Attendance rules. The new row sits **above** the manager switch. HR types a whole number 0-30 or leaves it empty. Saved on change. The save line names a date.
2. **Employee, day sheet:** the month payload carries, for the employee's own month only, the oldest allowed day, its basis, each day's state, and (only if their joining day is older than that) the joining date.
   - Day inside the window, or no limit: the form, as today.
   - Day too old: one sentence, no form.
   - Joining day, too old: green strip, then the form.
3. **Employee, `#att-req`:** `get_requests_history` carries the same block. A note sits under the title. Picking a too-old From shows red text under it. Submit is never greyed.
4. Employee presses Submit. The server runs the one function.
   - Allowed: the request is created as today, HR decides.
   - **Unhappy 1:** first day too old: refused whole, naming the oldest day, the basis, and HR's route.
   - **Unhappy 2:** range starts on the joining day and ends later: refused whole with the joining-day sentence.
   - **Unhappy 3:** HR changed the number while the page was open: the refusal names the *live* date; typed text stays.
   - **Unhappy 4:** a request sent around the portal (Desk, `/api/resource/Attendance Request`, editing a draft's dates): the same `validate` hook refuses it.
5. Refused employee tells HR which day and why. HR raises or decides it by HR's own route, which this setting never binds (HR raising for *another person*; see Q2 for HR's own day).
6. HR clears the box to remove the limit (blank). It must work (AC-7).

## 5. Epic and user stories

**Epic E-084: A company can limit how far back an employee raises their own day, and the employee is told before they type.**

Points: 1, 2, 3, 5, 8. Every story passes INVEST; US-3 is a 5 and is the one to watch (a warning, not a split: the hook, the function and the joining rule are one indivisible guard).

| ID | Story | Pts | Prototype | SEC / PRIV / OPS | ACs |
|---|---|---|---|---|---|
| US-1 | As an **HR Manager** I want one row in Org settings for how far back an employee can ask about their own day, so that I set the company's rule myself without an engineer writing a script | 3 | P1 HR card | SEC-8, SEC-9, OPS-5, OPS-16 | AC-1..AC-6 |
| US-2 | As an **HR Manager** I want to clear the limit again, so that I can never be stuck with a number I cannot remove (the blank-value trap) | 1 | P1 (save blank) | SEC-9, OPS-5 | AC-7, AC-8 |
| US-3 | As an **Employee** I want the company's limit applied the same way on every route I could use, so that the words I read and the refusal I get agree, and nobody gets around it by another door | 5 | P3, P4 (refusal) | SEC-1..6, 10, 13; PRIV-2, 4, 5, 6; OPS-1, 2, 4, 5, 6, 7, 11 | AC-9..AC-29 |
| US-4 | As an **Employee** on the attendance sheet I want to be told a day is too old *instead of* being shown a form that will fail, and to be told my joining day is always allowed, so that I never write three sentences for nothing | 3 | P2, P3 | SEC-2, PRIV-3, PRIV-5, OPS-8 | AC-30..AC-36 |
| US-5 | As an **Employee** on Attendance Request I want the oldest allowed day shown under the title and a plain refusal beside the button, so that I know before I type and can reread after | 3 | P4 | SEC-2, PRIV-5, OPS-1, OPS-9 | AC-37..AC-44, AC-72, AC-73 |
| US-6 | As an **HR Manager answering a grievance** I want a record of who changed an organisation setting and what it was before, so that "who set it to 0, and when?" has an answer | 1 | none | SEC-12 | AC-45..AC-47 |
| US-7 | As an **HR Manager** I want nothing on any screen, hint or code comment to say an employee's own day is not limited once it is, so that the product does not say the opposite of what it does | 2 | P1 (hint) | OPS-14 | AC-48..AC-51 |
| US-8 | **Must not:** as a **line manager** I must not be bound by the employee window, and as **HR** I must not be blocked from raising or deciding for another person | 1 | none | SEC-7 | AC-52..AC-54 |
| US-9 | **Must not:** as a **skip-level manager** I must not receive a report's joining date because of this slice; as an **employee** I must not be able to read the setting's raw number | 1 | none | PRIV-3, OPS-10, SEC §4 | AC-55, AC-57 |
| US-10 | **Must not:** as a **store-scoped HR person, HR User or plain employee** I must not be able to save the setting | 1 | P1 (greyed) | SEC-8 | AC-56..AC-58 |
| US-11 | As **Surbhi** I want a one-off read-only count per tenant of past requests that the proposed limit would have refused, so that HR picks a number knowing its effect, without us building a refusal log | 2 | none | OPS-13, PRIV-2 | AC-59 |
| US-12 | As **Surbhi** I want the release to change nothing for any tenant and to prove what landed, so that "green" is never the only evidence | 2 | none | OPS-3, 12, 14-19, PRIV-1, PRIV-7 | AC-60..AC-67 |

Total 25 points. Cross-cutting test-quality and NFR ACs: AC-68..AC-71, attached to US-3.

### YouTrack-ready table (not created; the user decides)

| Summary | Description | Persona | Pts | ACs | Requirements |
|---|---|---|---|---|---|
| 084 Org settings: employee window row | New key, allow-list, row above manager switch, hint, save lines | HR Manager | 3 | AC-1..6 | Brief §7, SEC-8/9, OPS-5/16 |
| 084 Blank must clear the limit | Add key to blank branch at `set_org_setting` | HR Manager | 1 | AC-7, 8 | SEC-9, Gate 3 |
| 084 Guard on all three routes | One function + `validate` hook, joining day alone, range refusal | Employee | 5 | AC-9..29, 68-71 | SEC-1..6,10,13; PRIV-2,4,5,6 |
| 084 Day sheet: sentence instead of form | Server sends boundary + per-day state; joining strip | Employee | 3 | AC-30..36 | UX DS1/DS2/JD1, PRIV-3 |
| 084 `#att-req`: note, inline check, refusal box | Boundary in `get_requests_history` | Employee | 3 | AC-37..44, 72, 73 | UX AR1/AR2/AR3 |
| 084 Log who changed an org setting | One security log line, six keys | HR Manager | 1 | AC-45..47 | SEC-12, Gate 3 C2 |
| 084 Fix the nine false strings in one commit | `02a` six + three found here | HR Manager | 2 | AC-48..51 | OPS-14 |
| 084 Must-not: manager/HR unaffected; no joined_on to others; no save by others | Negative tests | Manager, HR, Employee | 3 | AC-52..58 | SEC-7/8, PRIV-3 |
| 084 One-off baseline count per tenant | Read-only script run by a person | Surbhi | 2 | AC-59 | OPS-13 |
| 084 Release proof | Blank default, landing proof, rollback, release note, Hindi/phone gate | Surbhi | 2 | AC-60..67 | OPS-3,12,14-19 |

## 6. Data model

**New DocType: none. New field on any DocType: none. Custom Field: none. Patch/fixture: none.** (PRIV-1.)

| Thing | Detail | Why an existing thing cannot carry it |
|---|---|---|
| New Frappe default, key **`alvoraa_employee_filing_window_days`** (constant `EMPLOYEE_FILING_WINDOW_KEY`; name is mine, matching the manager key's pattern; the engineer may rename, but one name must appear in the allow-list, the reader, the page and the tests) | Value: `""` or `"0"`..`"30"`. Absent or `""` = no limit. `"0"` = today only. Mandatory: no. Default: blank. | The manager key means something else and must not be read by this path (SEC-7). HR Settings has no such field (§3). |
| `ALLOWED_ORG_SETTINGS[EMPLOYEE_FILING_WINDOW_KEY] = range(0, 31)` | `hr_api.py:3311` | Same list, same guard |
| Reader `employee_filing_window_days()` | Returns `None` for absent/blank, else `max(0, cint(raw))`. **Not** `get_default(KEY) or DEFAULT` (a stored "0" is falsy; see the manager reader's docstring, `attendance_correction.py` ~1400) | -- |
| Function `employee_filing_from(employee)` | Returns `(earliest_iso, basis)` or `(None, None)`. Returns **before any holiday read** when blank (OPS-5). Calls `_working_days_away(employee, nowdate(), days, -1)` | One derivation for guard and screens |
| Pure predicate (name the engineer's) `own_day_state(from, to, earliest, joined)` returns `"open"`, `"old"`, or `"range"` | `from >= earliest` → open. Else if `joined` and `from == to == joined` → open (joining exception). Else if `joined` and `from == joined` and `to > from` → range. Else old. Blank `joined` → no exception (SEC-5). The per-day sheet flag is `own_day_state(day, day, ...)` | One rule for the guard (ranges) and the sheet (days) |
| Hook `refuse_own_day_outside_window(doc, method=None)` on `Attendance Request` **`validate`** | Order of work: (1) read the setting; blank → return; (2) return unless `is_new()` or `from_date`/`to_date` changed (`has_value_changed`, **inferred Frappe API; engineer confirm**); (3) return unless `is_own_record(doc.employee)` (`access.py:58`); (4) read `date_of_joining` from `Employee doc.employee`; (5) call the function and predicate; throw with the sentence | By construction binds portal, Desk and REST |
| `_employee_for` field list gains `date_of_joining` | `attendance_correction.py:277` reads `name, employee_name, company, default_shift, holiday_list` today; same single-row `get_value`, no new statement (OPS-6). Other callers: 9 in this file plus tests (`grep -c "_employee_for("`); engineer greps again | `_get_employee` in `hr_api.py` already has it (line 301-311) |
| Month payload (self only), when a window binds | Reuses `can_request_from`, `can_request_basis`; adds per-day state (proposed key `own_window` on each day dict: absent when no limit; `"outside"` or `"joining"` or `"open"`) and `joined_on` **only when `is_self` and the joining day is older than `can_request_from`** | The manager keys exist and already carry this meaning; extending beats a second pair |
| History payload | `get_requests_history` (`hr_api.py:2992`) gains one block (proposed key `att_window`: `from`, `basis`, `joined_on`), present only when a limit is set; `joined_on` only if older than `from` | `#att-req` already calls it on open (`portal.js:12140`) |
| Org setting save response | `set_org_setting` returns `{"ok": True}` today; for this key add the example date (§12 save line) | A new endpoint is banned (SEC-11) |

The comment `attendance_correction.py:715` ("One value, not a flag per day") stops being true for the self path and is rewritten (AC-49).

## 7. States and transitions

**None.** No workflow, no new status, no new field. `Attendance Request` `docstatus`, `alvoraa_review_status` ("Waiting", set at `attendance_correction.py` in `raise_correction`) and the review flow are untouched. A refusal is a thrown error; nothing is stored. The only "state" is the setting: blank (default) → a number → blank, reversible at any time; the effect starts on the next request.

## 8. Permission and visibility matrix

Roles read from shipped DocType JSON (`attendance_request.json`): System Manager, HR Manager, HR User have create/read/write/submit/cancel/delete; Employee has create/read/write/delete, **no submit, no cancel**. The per-tenant Custom DocPerm table is what actually applies on a live site and **was not checked**. Window-bound means "refused if first day is too old".

| Actor | Set the setting | Read the raw number | Raise own day, portal | Raise own day, Desk/REST | Raise/decide **another person's** day | See own boundary date | See another person's joining date via this slice |
|---|---|---|---|---|---|---|---|
| Employee (own company, own record) | **No** | **No** (`_require_hr`) | Yes, window-bound | Yes, window-bound (hook) | n/a | **Yes** (own) | No |
| Line manager (direct reports) | No | No | Own day: window-bound | Own day: window-bound | Raise for a direct report via `raise_for_report`: bound by the **manager** window only | Own only | **No** (not in payload, AC-55) |
| Skip-level manager | No | No | Own: bound | Own: bound | Read a month only | Own only | **No** |
| HR User | **No** (existing) | No | Own: bound | Own: bound | Decide; create for others | Own only | No new exposure |
| HR Manager, company-wide | **Yes** | Yes | **Own day: bound** (C3) | **Own day: bound** (hook; see Q2) | Yes, unbounded by this setting | Own only | No new exposure |
| HR Manager, store-scoped (Branch User Permission) | **No**, refused and logged `030-D4` | Yes (read) | Own: bound | Own: bound | As today | Own only | No new exposure |
| System Manager / CXO | Yes (`_require_hr`) | Yes | Own: bound | Own: bound | Yes | Own only | No new exposure |
| Guest | No | No | No | No | No | No | No. No endpoint here is `allow_guest` |

**Negative cases, stated.** An employee must not: save or read the raw number; raise their own day before the boundary by any route (portal, Desk, REST, editing a draft's dates); approve their own request (`refuse_own_submit`, `hooks.py:183`, untouched). A manager or skip-level reader must not receive `joined_on`, the per-day state or an employee boundary on someone else's month. HR is never bound when raising or deciding for **another** person. A leaver (status not Active) is refused earlier by both lookups (`status = "Active"`, `attendance_correction.py:283`, `hr_api.py:303`). The two settings must not read each other.

## 9. Acceptance criteria

Fixture rules that apply to every AC below (01c §10, a "0 findings" test is meaningless otherwise): the setting is **non-blank**; the fixture employee's `date_of_joining` is **older than the boundary** unless an AC says otherwise; the fixture has **no overlapping `Attendance Request`** (or Frappe's overlap check throws first); the manager tests already delete holidays near today (`test_attendance_correction.py` ~1510-1514), do the same so dates do not depend on the weekday the suite runs; **each window test is made to fail once** by removing the guard and the *right* test must fail (AC-71). Test files: new `alvoraa_portal/alvoraa_portal/tests/test_employee_filing_window_084.py` unless another is named. "Page source test" means the `portal_source` pattern in `test_org_settings_allowlist_012.py:87`.

### US-1 The setting row

- **AC-1** Given an HR Manager with company-wide reach, when they call `set_org_setting(EMPLOYEE_FILING_WINDOW_KEY, v)` for v in `"0"`, `"3"`, `"30"`, then `frappe.db.get_default(KEY)` equals v and `employee_filing_window_days()` returns `0`, `3`, `30` as integers (the `0` case returns `0`, not `None`). *Test:* new file.
- **AC-2** Given the same HR Manager and a stored `"3"`, when they save `"31"`, `"-1"`, `"3 "`, `"abc"`, `"999"` or `"1.5"`, then each raises `frappe.PermissionError` (via `_refuse_org_setting`) and `get_default(KEY)` is still `"3"`. *Test:* new file; same pattern as `test_attendance_correction.py` ~1809-1817.
- **AC-3** Given the Org settings template, then the new row (label text exactly **"How far back an employee can ask about their own day"**, a number input `min=0 max=30` with placeholder **"No limit"**, `aria-describedby` its hint) appears in document order **before** the `org-on-behalf-on` checkbox and is **not** inside `org-filing-window-field`. The hint reads exactly: **"Leave this empty for no limit. Counted in working days, using the employee's own holiday list. An employee's joining day is always allowed. It does not limit HR. Use 0 to let an employee ask about today only. This is one number for every company in this organisation."** (01b §5.1; "does not limit HR" is true for HR raising for *others*; see Q2 for the nuance, which is not put on screen). *Test:* page source test + manual on dev.
- **AC-4** Given the manager switch is off, when HR opens the card, then the employee box is **enabled** and the manager box is greyed. *Test:* page source test that `orgOnBehalfApply` references no id of the new row; manual check on dev (not run here).
- **AC-5** Given a successful save, then the line at the top of the card (`org-attrules-msg`, `role="status"`) reads: blank → **"Saved. There is no limit: an employee can ask about any past day."**; 0 → **"Saved. An employee can now ask about today only, {date}. Their joining day is always allowed. HR can still fix any day."**; n≥1 → **"Saved. Today, an employee on the company's usual holiday list can ask back to {date}. Their joining day is always allowed. HR can still fix any day."**, where `{date}` is the date the **server returned in the save response** (format "Mon 16 Nov"), never worked out in the browser. *Test:* the response carries the date and equals the boundary from `_working_days_away` for the reference calendar in Q3; page source test that the line uses the response; manual.
- **AC-6** Given the save fails, then the box shows the server's sentence, else **"The setting could not be saved. Try again, or ask your administrator."**, and the box returns to the stored value; and given the box holds a non-whole or out-of-range value, then **"Give a whole number of working days between 0 and 30, or leave it empty for no limit."** appears with nothing sent. *Test:* page source test + manual.

### US-2 The blank-value trap (Surbhi named this one)

- **AC-7** Given stored `"3"`, when HR calls `set_org_setting(EMPLOYEE_FILING_WINDOW_KEY, "")`, then it succeeds, `get_default(KEY)` is `""` (or `None`), `employee_filing_window_days()` is `None`, `employee_filing_from(emp)` returns `(None, None)`, and an employee can then raise a request six months back on `raise_correction`, on `submit_attendance_request` and by a direct insert. **Break-it check:** with the one line at `hr_api.py:3395` left as `key == MANAGER_FILING_WINDOW_KEY` only, this test must fail with a `PermissionError`. *Test:* new file; also the page's Clear path (empty box sends `""`, as `portal.js:23511` does for the manager key).
- **AC-8** Given stored `"0"`, then `employee_filing_window_days()` is `0`, the boundary is **today**, yesterday is refused and today is allowed; and given stored `""`, yesterday is allowed. Blank and 0 never collapse. *Test:* new file.

### US-3 The guard, all three ways in

For AC-9 to AC-26, "the three routes" means (a) `attendance_correction.raise_correction`, (b) `hr_api.submit_attendance_request`, (c) `frappe.get_doc({...Attendance Request...}).insert()` run as the employee's own user (`frappe.set_user`). Window 3 on a Sat/Sun-off list, today Thu 19 Nov, boundary Mon 16 Nov, joining Wed 11 Nov unless stated.

- **AC-9** Given the employee, when they raise Fri 13 Nov (single day) by (a), then `frappe.ValidationError` is thrown, **no** `Attendance Request` row exists for that employee afterwards, and the message is: **"This day is older than your organisation lets you raise yourself. The oldest day you can raise yourself is Mon 16 Nov, counted in working days on this person's own holiday list. HR can still fix it: tell HR which day it was and why. The one exception is your joining day, Wed 11 Nov."** (basis phrase is the existing translated string from `_working_days_away`; the last sentence only when the joining day is older than the boundary).
- **AC-10** Same as AC-9 by (b). This also proves `ignore_permissions=True` does not skip the hook.
- **AC-11** Same as AC-9 by (c): refused, no row.
- **AC-12** Given the employee has a draft request for today, when they change its `from_date` to Fri 13 Nov and save (`doc.save()`), then it is refused and the stored `from_date` is unchanged. **Break-it check:** with the hook on `before_insert` instead of `validate`, this test must fail. This is why the event is `validate`.
- **AC-13** Given the same employee, when they raise Mon 16 Nov (the boundary day) by each of the three routes, then each succeeds; and when they raise Fri 13 Nov (the last working day before it; Sat 14 and Sun 15 are holidays on this list) each route refuses. The test works the dates out from the fixture's own list and asserts `from >= earliest` allows and the day before refuses.
- **AC-14** Given from = Fri 13 Nov and to = Thu 19 Nov, then each route refuses the whole request, no row, message names Mon 16 Nov.
- **AC-15** Given from = to = Wed 11 Nov (the joining day, older than the boundary), then each route succeeds.
- **AC-16** Given from = Wed 11 Nov, to = Thu 19 Nov, then each route refuses whole, no row, and the message is exactly **"Your joining day, Wed 11 Nov, can be asked about on its own: set To to the same day. Days after it that are older than Mon 16 Nov are HR's to fix: tell HR which days and why."** (01b Gate 2 decision (a); prototype key `rangeJoin`).
- **AC-17** Given from = to = Thu 12 Nov (the day after joining, before the boundary), then each route refuses (the exception is one day only).
- **AC-18** Given `Employee.date_of_joining` is blank, then the window applies to every day with no exception, no sentence mentions a joining day, the payloads carry no `joined_on`, and no comparison against `None` throws (SEC-5).
- **AC-19** Given `raise_correction` and `submit_attendance_request` are called with extra keys `date_of_joining`, `employee`, `joined_on` set to values that would allow the day, then the outcome is identical to the clean call (endpoints ignore them; SEC-4). *Test note:* `raise_correction` has a fixed signature, so call through `frappe.call`/`frappe.form_dict` as the other tests do, or assert the hook reads only `Employee`.
- **AC-20** Given the employee's status is `Left`, then both endpoints throw the existing not-linked error and create nothing; the hook is never reached (SEC-10).
- **AC-21** Given the setting is blank, then all three routes accept any past day exactly as they do today, and the hook returns after **one** `get_default` read, **before** `is_own_record`, `Employee` and holiday reads (OPS-5). *Test:* patch/count `frappe.db.get_value` and `holiday_list_for` calls; zero.
- **AC-22** Given window 0, then today is allowed and yesterday refused by all three routes; the refusal names today's date.
- **AC-23** Given the employee has a holiday list with Sat/Sun off, then the boundary skips them (Thu 19 → Mon 16 for window 3, basis "working days on this person's own holiday list"). Given the employee has **no** holiday list and window 5, then the boundary counts calendar days (Thu 19 → Sat 14 Nov, where the Sat/Sun-off list would give Thu 12), the refusal says **"calendar days, because this person has no holiday list"** and still names HR (SEC-13). The test asserts `_working_days_away` was the function used (one counter, no second loop).
- **AC-24** Given from = Wed 18 Nov (inside) and to = Mon 30 Nov (future), then all three routes accept (future ends are legitimate; the limit looks backwards only). *Note:* a far-future `to_date` passes; that is Surbhi's decision (out of scope) and is ticket ALV-387's.
- **AC-25** Given a draft raised under a wider window (dates Fri 13 Nov), when the window is tightened and the employee edits only `explanation` and saves, then it **succeeds** (dates unchanged); and when an HR user submits that employee's request, it succeeds; and `leave_rules.prepare_half_day_correction` still runs on insert (its existing tests stay green).
- **AC-26** Given an HR Manager with an Employee record, when they raise their **own** day Fri 13 Nov by (a), (b) or (c), then it is refused like any employee (C3). HR Manager and employee are bound by the same function.
- **AC-27** (one function) Given the same fixture, then for each of (a), (b), (c) the date in the refusal message equals `formatted(can_request_from)` from `month()` for that employee, and equals `att_window.from` from `get_requests_history()`. *Test:* presses Submit on both paths and reads the three payloads; if the sentences are built in JS this is asserted by a page source test that the JS builds the date only from server values.
- **AC-28** Given a refusal on either path, then `hrms.alvoraa_hr_core.access.log_refusal` is called **0 times** and `frappe.log_error` is called 0 times (PRIV-2, PRIV-6). A refused correction is lawful behaviour, not misuse.
- **AC-29** Given any refusal branch (first day too old; range from too-old day; range from the joining day; window 0), then the message (i) contains the HR route sentence ("HR can still fix it: tell HR which day it was and why", or the range form), (ii) contains only dates and fixed words, and contains neither the fixture's name nor its employee id nor a holiday list name nor a company, and (iii) contains no digit directly followed by "day" or "hour" in the new strings (SEC-2, PRIV-4, PRIV-5).

### US-4 Day sheet

- **AC-30** Given a window is set and an employee opens their **own** month, then the payload has `can_request_from` = the function's date, `can_request_basis` = its basis, and each day dict has `own_window` set by the predicate (`"outside"` for Fri 13 Nov, `"joining"` for Wed 11 Nov, `"open"` for Mon 16 Nov, and `"open"` for days after today); `joined_on` is present **only** when the joining day is older than `can_request_from`.
- **AC-31** Given the setting is blank, then none of `own_window`, `joined_on` or an employee boundary is in the payload, and a self month costs the queries it does today (AC-68). *Observable:* "no limit changes nothing".
- **AC-32** Given a day with `own_window == "outside"`, then the sheet shows, instead of the form: **"This day is older than your organisation lets you raise yourself. The oldest day you can raise yourself is Mon 16 Nov, counted in working days on this person's own holiday list. HR can still fix it: tell HR which day it was and why."** plus **"The one exception is your joining day, Wed 11 Nov."** when `joined_on` is present; and no "Ask HR to fix this day" button. *Test:* page source test that the `is_self` branch is separate from the manager branch and uses these words; manual on dev (prototype P3).
- **AC-33** Given `own_window == "joining"`, then a green strip reads **"This is your joining day, so you can always ask about it, however long ago it was."** and the form follows; given the joining day is inside the window there is no strip.
- **AC-34** Given `"open"` or no limit, the form is drawn exactly as today.
- **AC-35** Given the sheet was opened under a wider window and HR then tightened it, when the employee presses "Ask HR to fix this day", then the server refusal is shown in place of the button area, starting **"Nothing was sent."**, with the same sentence, and the typed reason and text are still in the form.
- **AC-36** Given a **manager** opens a direct report's month, then the manager's own sentence ("outside the window a manager can file within") still appears for manager-bound days, and an **employee** viewing their own month never sees the words "a manager can file within" (that is string 5 of `02a`).

### US-5 `#att-req`

- **AC-37** Given a limit is set, then `get_requests_history` for the employee carries `att_window` with `from`, `basis` and (only if older than `from`) `joined_on`; given blank, no such block; given another employee, only their own values.
- **AC-38** Given a limit is set, then under the page title: **"You can ask about days from Mon 16 Nov onwards. Your joining day, Wed 11 Nov, is always allowed. For any other older day, HR can still fix it: tell HR which day and why."** The joining sentence appears only when `joined_on` is present. With window 0: **"You can ask about today only (Thu 19 Nov)."** (+ joining sentence + HR sentence as above). With no limit: nothing is drawn.
- **AC-39** Given From is too old and not the joining day, then red text under From (red border and the words) gives the AC-32 sentence; given From is the joining day, green text **"Your joining day: you can always ask about this day."**
- **AC-40** Given From is the joining day and To is later, then the inline text is the AC-16 sentence.
- **AC-41** Given any state, then the Submit button is never disabled, and neither date input has a `min` attribute (a `min` greys the one day that is allowed; 01b AR3).
- **AC-42** Given Submit is pressed with a too-old day, then a box beside the button with `role="alert"` shows **"Nothing was sent."** + the server sentence + **"What you typed is still here."**, focus moves to From, and every typed field keeps its value. No toast is the only signal.
- **AC-43** Given the page was loaded, then HR changes the number, then Submit is pressed, then the note and inline text still show the load-time date and the refusal names the **live** date (accepted behaviour, 01b §5.3).
- **AC-44** Given the slice is built, then `submit_attendance_request`'s `ignore_permissions=True` is neither removed nor copied, and no new `@frappe.whitelist` exists (AC-69).

### US-6 Setting changes are attributable

- **AC-45** Given any successful `set_org_setting` for **each of the six keys** in `ALLOWED_ORG_SETTINGS`, then exactly one `frappe.logger("security")` call is made carrying JSON with `event`, `at`, `user` (the session user), `key`, `old` (the stored value before) and `new`. *Test:* patch the logger, loop the six keys.
- **AC-46** Given a refused save (bad value, wrong role, store HR, unknown key), then **no** change line is written (the existing refusal lines are unchanged). The line is written **after** `frappe.db.commit()`.
- **AC-47** Given the line, then it holds no person's name, reason or attendance data (org settings are not personal data; the user id is the actor). The level is `.warning`, the level `log_refusal` uses; see Q6, and the dev check "trigger one save and read `sites/<site>/logs/security.log`" is a release step (AC-61).

### US-7 The false strings

- **AC-48** The six strings of `02a` are changed **in the same commit** as the code (`git show --stat` for that commit lists `org-settings.html`, `attendance_correction.py`, `portal.js`, `hr_api.py`). New manager hint (01b §6): **"...A manager who asks later than this is told to go to HR instead. It does not limit HR - HR can still fix any day. How far back an employee can ask about their own day is the separate setting above. Use 0 to let a manager ask about today only."** The `<strong>` clause "it does not limit an employee asking about their own day" is gone. Replacement comments are as 01b §6 items 1-5.
- **AC-49** Three more places are rewritten in the same commit, **found by this spec, not in `02a`**: (7) the docstring of `test_an_employees_own_old_day_is_not_touched_by_the_window` (`test_attendance_correction.py:1637`: "Narrowing what a person may ask about their own attendance was never asked for") and the test itself, which is rewritten to say the **manager** window does not bind an employee's own day; (8) the comment above the blank branch at `hr_api.py:3388-3394`: "No other numeric setting takes a blank, so this is spelt out for the one key" (now two keys); (9) the comment at `attendance_correction.py:715` ("One value, not a flag per day"), true only for the manager path now.
- **AC-50** At review, a grep for `does not limit`, `not bounded`, `their own month`, `neither setting`, `never asked for`, `a manager can file within` over the **whole repo and `docs/`** (not only `alvoraa_portal/alvoraa_portal`, which is all the UX scan searched), plus the DTC user manual and Desk help text, returns no sentence that describes an employee's own day as unlimited. **Until it has been run, "nine" is a floor, not a total.** *Test:* a source-grep test for the phrases inside `alvoraa_portal`; the wider search is a review step with its output pasted in `05-review.md`.
- **AC-51** Given the new sentences, every one is built from a server date (AC-27) and none types a number of days or hours.

### US-8 Must not: managers and HR

- **AC-52** Given the employee window is 0, then a manager can still file for a direct report inside the **manager** window with `raise_for_report` (the hook does not fire: `is_own_record` is false), and an HR Manager can still create and submit a correction for **another** person for a day a year old. And given the **manager** window is 0 and the employee window 3, an employee's own Mon 16 Nov request succeeds.
- **AC-53** Given HR (System Manager/Administrator session) inserts an `Attendance Request` for another employee with `from_date` a year back, then it succeeds (existing `test_hr_is_never_bounded_by_it` stays green).
- **AC-54** Given `EMPLOYEE_FILING_WINDOW_KEY` and `MANAGER_FILING_WINDOW_KEY`, then neither reader reads the other's key (source test), setting one does not change the other's boundary, and switching the manager switch off does not change the employee boundary.

### US-9, US-10 Must not: visibility and write

- **AC-55** Given a manager (direct) and a skip-level manager open a report's month, then the payload has **no** `joined_on`, no `own_window` and no employee boundary, and `can_request_from` is the manager's own as before. *Test:* the `time_api.SUBJECT_KEYS` allow-list pattern (`time_api.py:71`).
- **AC-56** Given a store-scoped HR Manager (Branch User Permission), then `get_org_setting(KEY)` works and `set_org_setting(KEY, "3")` is refused, logged `030-D4`, and the stored value does not move. *Test:* the key added to `test_org_setting_scope_030.py`.
- **AC-57** Given an HR User or a plain employee, then `set_org_setting` and `get_org_setting` for the key are refused (`_require_hr`), nothing stored.
- **AC-58** Given the page, then every `_org_setting` key it calls is in `ALLOWED_ORG_SETTINGS` (existing `test_the_page_still_calls_only_the_allowed_key`, `test_org_settings_allowlist_012.py:87`, stays green with the new key); and a made-up key is still refused.

### US-11 One-off baseline

- **AC-59** A read-only script (kept outside the app package; the engineer chooses the folder) counts, per tenant, `Attendance Request` rows whose `from_date` was older, **at the time of creation**, than the working-day boundary for a number HR is considering, using `_working_days_away` from the creation date. It contains no `INSERT`, `UPDATE`, `DELETE` or `set_default` (checked by reading it), it is run by a person on a tenant only on Surbhi's word, and its output is a count, not names. **Not built here to run on any live tenant.**

### US-12 Release

- **AC-60** Given a tenant at release, then `get_default(EMPLOYEE_FILING_WINDOW_KEY)` is absent or blank, `employee_filing_window_days()` is `None`, and both portal endpoints and the Desk behave exactly as before (AC-21). No patch, fixture or migration changes it.
- **AC-61** Given the build is on dev, then the landing is proved three ways, not by a green tick (OPS-15): the pin file `.image.dev.env`; `docker ps` image tags the same on every app container; a grep for a **new sentence** inside the container's `portal.js` and `org-settings.html`; and `assets.json` in the sites volume compared with the image's, with `portal.js` loaded from the dev URL and grepped for the new sentence. One `set_org_setting` save is triggered and `sites/<site>/logs/security.log` read for the line (Q6). Same three-way proof on the production stack's `.image.env` after main.
- **AC-62** The rollback note says: record the key's value on each touched tenant before release (expect blank); the stored number **outlives the image** (old code ignores it, so HR would believe a limit is on when it is not); tell HR in words if code is rolled back while a number is set; never delete the row; the fast undo with no deploy is HR clearing the box; read the value back after any change and write the value that came back (OPS-16, 17). The previous production image tag is named and proved to exist in `alvoraa-app` (open, OPS-17).
- **AC-63** The release note states, in these terms: Grace enforces a 3-a-month cap that is not in Org settings, **two rules exist and the stricter wins**; before a number is set on Grace the script is read and its counting basis compared (calendar days against our working days); other tenants **"not checked"**, never "all clear" or "no other tenant has one" (OPS-3, 18, 19); the employer should tell staff before switching a limit on (brief §12); and counsel is asked before the first tenant sets a non-blank value (Gate 3 C1).
- **AC-64** The diff contains no `deploy/nginx.conf` change, no new DocType folder, no Custom Field, no patch (`git diff --stat`), so the one-nginx trap and the migrate queue trap do not arise (PRIV-1).
- **AC-65** `scripts/check_app_integrity.py` passes before commit.
- **AC-66** **Release gate, manual:** a native Hindi reader has reviewed the Hindi strings (machine drafts in the prototype's `L` table); the day sheet and `#att-req` are checked at 390 px and at 200% text, tap targets 44 px, keyboard-only and with a screen reader (all unmeasured at Gate 2). Not done in this run; must not be claimed done later without the record.
- **AC-67** On dev, one filing is sent and the request line read, to confirm which URL the call uses and so that nginx's 120/min limit applies (OPS-12). No new rate limit is built.

### Non-functional and test-quality ACs (attached to US-3)

- **AC-68** Query count: for a self month and for a submit, the statement count is **the same** for a holiday list of 10 rows and of 500 rows, and a blank setting adds **no** holiday read and no extra statement to `month()` (OPS-1, 2, 6, 7). The number is recorded, the property is asserted.
- **AC-69** `grep -c "@frappe.whitelist"` and `grep -c "ignore_permissions"` in `attendance_correction.py` and `hr_api.py` do not rise against the counts taken at the start of the build (SEC-11).
- **AC-70** The boundary is **not** in `get_portal_context` output (cached under `portal_ctx_<user>` and `allow_guest`; OPS-9).
- **AC-71** Each of AC-7, 9-12, 14-17, 26 is shown to fail once with the guard removed, and the *right* test fails, before "it passes" is written in `04-test-report.md` (SEC §10 item 4).

### Accessibility and language

- **AC-72** The new input has a real `<label>` and `aria-describedby`; the save line is `role="status"`; the refusal box is `role="alert"`; the sheet is `role="dialog"` with focus moved in and Escape closing it, as the prototype does (P3); red and green text always come with words. *Test:* page source test; the rest is AC-66.
- **AC-73** Every new user-visible string passes through `_()` (Python) or `drT` (JS), with the date passed as an argument (`drT("...{0}...", [date])`), never glued on. A page source test finds no concatenated date in the new strings.

## 10. Edge cases

Only cases that can happen here.

| Case | What the spec says |
|---|---|
| Joined in the last few days | Joining day always allowed alone (AC-15); other days obey the window (AC-17); a joiner with joining day inside the window sees no special text. |
| Joining date blank | No exception (AC-18). |
| Joining date later changed by HR (promotion/transfer into a new company writes it, `employee_field_rights.py:270-272` per 01c) | Read live each time, never cached. |
| Re-hire | New Employee record, new joining date, exception follows (01c, `[ASSUMPTION]`, no rehire flow read). |
| Two active Employee rows for one login | Read the joining date from the **same** row the request is built from (the hook reads `doc.employee`). Whether `Employee.user_id` is unique: **not checked** (Q8 in 01c). |
| Leaver with a live session | Refused earlier (AC-20). Frappe also caps `to_date` at `relieving_date`. |
| Employee with no holiday list | Calendar days, and the sentence says so (AC-23). It is the tighter direction; accepted (SEC-13). |
| Sat/Sun or other weekly offs | Come from the employee's own list; never assumed. |
| Half-day correction | Window applies to `from_date`; `half_day_date` is between from and to (Frappe). No special case. |
| Future-dated or WFH-ahead request | Allowed (AC-24). Far-future `to_date` is not limited here: Surbhi's decision, ALV-387. |
| Back-dated entries to the exact boundary | Boundary day allowed (AC-13). |
| Time zone | `nowdate()` is the site's date. One site, one zone per tenant; an employee abroad sees the site's "today". `[ASSUMPTION]` no tenant has employees working a different calendar day than the site. |
| Cancelled/amended | Cancelling frees dates (existing); the replacement is checked by the hook as a new record. Employee has no cancel right. |
| HR changes the number while a page is open | Live number wins at submit (AC-43, AC-35). |
| Concurrent submits of the same day | Frappe's overlap check (existing). Not changed. |
| Bulk import by HR for others | Not own record; not bound. |
| Multi-company / multi-branch | One number for the whole site (a Frappe default has no company dimension; stated on the row's hint). A tenant with two companies cannot have two windows. |
| Employee with no manager / circular lines | Irrelevant: the guard uses the employee record, not `reports_to`. |
| HR Manager's own old day | Bound everywhere (AC-26); see Q2. |
| Grace's script plus the new setting | Both run; stricter wins (AC-63). |

## 11. Non-functional requirements (from `nfr-budget.md` §2, made specific)

| Item | Number |
|---|---|
| Volume | Design 1,000 employees, prove at 2,000 (`nfr-budget.md` §1). Volume of requests is a few a month per person. No list, so no page size. |
| Query cost | Blank: **one** default read per `Attendance Request` save and per month/history load. Set: 1 default read + `holiday_list_for` (2-3 statements, request-cached) + 1 `Holiday` query + a Python loop of at most `days*2+30` steps with no queries (`_working_days_away`). Estimate 4-5 statements, **not measured**; assert the property "same count for short and long lists" (AC-68). Not per day row: compute once per month load. |
| Side effect | `get_requests_history` is also called by the shift, encashment and advance panels (it returns all four histories); with a limit set they pay the same 4-5 statements for a block they ignore. Accepted: the alternative is a new endpoint (banned, SEC-11). |
| Response time | Employee self-service action p95 ≤ 1.5 s; whitelisted call p95 ≤ 500 ms (budget). Not measured; AC-68 is the guard. |
| Page weight | A few strings; under 1 KB raw against a 346 KB gzipped `portal.js` (DevOps §2). No new request, file or round trip. |
| Background jobs | None. |
| Cache | None. No cache for the setting, boundary or joining date; the history/month payloads are live. Do **not** add the boundary to `get_portal_context`. |
| Retention | Setting: until HR changes it. Refusals: none stored. Log line: the security log's existing rotation; **I did not check it.** |
| Personal data | None new. Joining date is the person's own, shown only to them. |
| Rate limiting | None new (OPS-12). |

## 12. Migration and backfill

**Nothing.** No patch, fixture, Custom Field or DocType. The key does not exist on any tenant and blank is the default, so release changes no behaviour (AC-60). Existing `Attendance Request` rows are never re-checked: the hook fires on new records and on date changes only (AC-25). **Rollback:** redeploy the previous tag; the stored number stays as a dead value; see AC-62. Hooks load with the app, so no `bench migrate` is needed for this slice as designed; if the engineer adds anything that needs one, this section is wrong and the DevOps rehearsal applies (`REHEARSAL.md`).

## 13. Notifications and messages

No email, push or notification is sent by this slice. **Messages on screen** (all dates "Mon 16 Nov" form, built from server values):

| Where | Copy | Source |
|---|---|---|
| Refusal, first day too old | AC-9 | 01b §5.2, prototype `oldLead/oldDate/hrCan/exc`, **plus** "counted in {basis}" |
| Refusal, joining day with a longer range | AC-16 | Prototype `rangeJoin` |
| Day-sheet strip | AC-33 | Prototype `joinNote` |
| `#att-req` note | AC-38 | Prototype `note/noteToday/noteJoin/noteHR` |
| `#att-req` inline | AC-39 | Prototype `joinHere` |
| Client lead-in on refusal | "Nothing was sent." / "What you typed is still here." | Prototype `nothing` |
| HR save lines | AC-5 | 01b §5.1 |
| Manager hint | AC-48 | 01b §6 |

**Never leak:** a name, employee id, reason, status, holiday list name or company in any message (AC-29). The joining date is shown only to the person it belongs to.

## 14. Localisation and accessibility

Every string through `_()`/`drT` with arguments (AC-73). Hindi in the prototype is a **machine draft** and runs about 30% longer: native review and a 390 px / 200% check are release gates (AC-66, open). `[ASSUMPTION]` HR screens are English only (01b; not checked). The frontline employee on a 360-390 px phone sees the same sentence, 16 px field text, 44-48 px targets (prototype CSS; **not measured**). Dates show a weekday ("Mon 16 Nov") because a 3-day window moves over weekends; the manager sentence keeps its existing format (Q5).

## 15. Audit and traceability of what happened

| What | Recorded | Reconstructable in a year? |
|---|---|---|
| Who changed any of the six org settings, from what to what, when | One `frappe.logger("security")` line (AC-45) | Only as long as the security log is kept: **unchecked**. This is a log line, not a ledger. A longer record is a decision for Surbhi (Q6). |
| An `Attendance Request` | The existing Version history on the doc, existing owner/creation fields | Existing |
| A refusal | **Deliberately not recorded** (PRIV-2). We can prove the control only by test. | n/a, by design |

## 16. Compliance-impact sub-analysis (I am not a lawyer)

### 1 · Data touched

| Field / object | Class | Purpose | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| `alvoraa_employee_filing_window_days` | internal (organisation config, not personal) | Apply the employer's own correction policy | n/a | Yes, config only |
| Boundary date on screen | internal, derived from the person's own list and today | Tell them before they type | n/a | Not stored |
| `Employee.date_of_joining` | sensitive (employment record, permlevel 2) | The always-allowed day | Existing employment records | **No**, read only |
| `Attendance Request` | sensitive (existing) | The correction | Existing | No new field |
| Refusal event | would be personal data | none | none | **Not collected**; the outcome (a rule HR chose, applied fairly) needs no record |

### 2 · Obligations engaged

| Obligation | Source | What this slice must do | Feature that does it |
|---|---|---|---|
| DPDP: correction right / grievance | `security-compliance-baseline.md` §2 (verified 24 Aug 2026, stale 22 Nov 2026; I did not re-verify); `compliance-feature-map.md` A8, G3 (both P0, status `?`, **not built**) | Keep the correction route open and named | HR route unbounded; every refusal names it (AC-29); blank default (AC-60) |
| DPDP: minimisation | same | Store no refusal record | AC-28, AC-64 |
| Accountability for a rule that removes a right | Gate 3 C2 | Know who set it | AC-45 |
| CERT-In, EU AI Act | baseline §3, §4 | Not engaged (no incident surface, no model) | -- |

### 3 · Visibility delta

An employee now sees **their own** boundary date and joining date on their own screens. Nobody else sees more: a manager or skip-level reader of someone else's month gets no joining date or window (AC-55). **Negative cases:** no employee reads the raw number or another person's joining date; no refusal reveals a name, id, reason or list name.

### 4 · Decision automation

The system closes one route (a date comparison against a number HR chose). It decides nothing about a person: HR still decides every request. Accountable human: the HR Manager who set the number (named in the log line) and the HR decider. The employee is told the date and HR's route before and after the refusal and contests it by telling HR. Not an automated decision in the EU AI Act sense; **that is my reading, not a legal ruling.**

### 5 · Retention and deletion

Setting: until changed. Refusals: none. Joining date: existing retention. Erasure requests: nothing here survives or is created. **Nothing changes** beyond the log line.

### 6 · ⚠ Open compliance questions

| Question | Who must decide | What it blocks |
|---|---|---|
| ⚠ May a tenant set a limit (especially 0) on the only self-service correction route while the data-principal rights console (A8) is not built? | Counsel, via Surbhi; Gate 3 C1 decoupled this from release | **The first non-blank value on any tenant**, not the release |
| ⚠ Is a security-log line enough as the record of who changed a rights-reducing setting, given the log's retention is unknown? | Surbhi (counsel if she wants) | Whether a longer record is needed |
| ⚠ Must the employer be told to inform staff before switching a limit on? Spec default: yes, in the release note (AC-63) | Counsel via Surbhi | Release-note wording only |

### 7 · AI features

None. No AI, scoring, profiling or monitoring. Prohibitions not engaged.

## 17. Prototype parity (Surbhi's rule: build as drawn; any difference needs her yes)

| Prototype element | Built as | Difference needing Surbhi's yes |
|---|---|---|
| P1 HR card, row above manager switch, not indented | AC-3, AC-4 | None |
| P1 save lines for blank, 0, n | AC-5 | n≥1 example date needs a reference calendar (Q3) |
| P2 month list | AC-30, AC-31 | None |
| P3 sheet: too-old sentence, no form; joining strip; "Nothing was sent." | AC-32, AC-33, AC-35 | **Refusal sentence adds ", counted in {basis}"** (the prototype omits it; 01b §5.2 last paragraph, OPS-4 and SEC-13 want it). Flag: yes or no? |
| P3 "Sent" wording | Keep the product's own words (01b assumption) | None |
| P4 note, inline red/green, range inline sentence, `role="alert"` box, focus to From, no `min`, Submit never greyed | AC-38..AC-42 | None |
| Weekday in dates ("Mon 16 Nov") | Own-day sentences and save lines only; manager sentence keeps its format | Format on the server side is the engineer's to prove (Q5) |
| Hindi, phone 390 px, dark theme | AC-66, AC-72 | Unmeasured |
| Review bar (persona/device/language/theme), "Sample" tags | Not built | None (scaffolding) |

## 18. Subtract pass

Removed from my own draft: a special refusal sentence for window 0 (the general sentence already names today's date); a second counter for the HR save-line example (one counter, optional holiday-list argument, Q3); a per-day server call (one date per month, a per-day state computed from it with no queries); a refusal counter or log (PRIV-2); a `to_date` upper bound (Surbhi: future dates out, ALV-387); an automated Hindi layout test (a human gate instead); a manager save line with a date (open, not adopted). **Kept** despite the subtract pass: the `validate` hook (the slice is decoration without it), the per-day state (otherwise the joining rule lives in the guard and again in JS), the nine-string rewrite. Nothing else removed.

## 19. Traceability

"Covered" = an AC with a named test or manual check exists. **No test is written yet.**

### Brief (`01-product-brief.md`, Gate 1) and the approved scope

| Source | ID or line | Story | ACs | Status |
|---|---|---|---|---|
| Scope 1 | One Org setting, employee own day, 0-30 working days on own list, blank default, 0 = today, row above manager switch | US-1, US-2 | AC-1..8 | covered |
| Scope 2 / Gate 1 | Joining day always allowed, only on its own | US-3 | AC-15..18 | covered |
| Scope 3 | Boundary from the server, one function | US-3, 4, 5 | AC-27, 30, 37, 51 | covered |
| Scope 4 | Bound by path, HR Manager included | US-3 | AC-26 | covered (see Q2) |
| Scope 5 | Guard binds all three ways in | US-3 | AC-9..12 | covered; mechanism corrected to `validate` (Q1) |
| Scope 6 | Blank-value trap | US-2 | AC-7, 8 | covered |
| Scope 7 | One security log line, six keys | US-6 | AC-45..47 | covered |
| Scope 8 | Six strings, same commit | US-7 | AC-48..51 | covered (nine) |
| Scope 9 | Ships blank on every tenant | US-12 | AC-60 | covered |
| Brief §6 WOW | Date before typing; sentence instead of form | US-4, 5 | AC-32, 38 | covered |
| Brief §7 | Blank returns before holiday lookup | US-3 | AC-21, 68 | covered |
| Brief §7 | Refusal uses the date and says HR can still fix it | US-3 | AC-9, 29 | covered |
| Brief §7 | Range starting too early refused whole | US-3 | AC-14 | covered |
| Brief §7 | Known limit: one value per site, said in the hint | US-1 | AC-3 | covered |
| Brief §5 | Manager hint reworded | US-7 | AC-48 | covered |
| Brief §10 | "Fewer wasted submissions" | -- | -- | **Not adopted, Surbhi's instruction in this task; replaced by the one-off count** (AC-59) |
| Brief §10 | One tenant sets a value without an engineer; Grace has no hidden time rule | US-12 | AC-63 | **partly traced**: the outcome is Surbhi's to check, no AC can prove it |
| Brief §8 | Dec. 2 (sentence only, no button); Dec. 3 (refuse the range whole) | US-3 | AC-14, 29 | covered |
| Brief §9 / Gate 1 open items 1-3 | Grace script, other tenants, `#att-req` use | US-12 | AC-63 | Items 1-2 decided Gate 3 (leave running; ask, not grep). **Item 3 (is `#att-req` used on Grace/DTC, by which roles) is unanswered and untraced**: Q7 |
| Out of scope | Cap, refusal log, per-company window, button, future-date check, Grace script removal | -- | -- | **Not adopted, Surbhi's decision** (task scope, Gates 1-3) |
| Gate 1 raised | `submit_attendance_request` unchecked insert with `ignore_permissions=True` | -- | AC-10, 44 | The date check is covered here; the `ignore_permissions` issue stays its own ticket (ALV-387 per `07` §4), **not fixed here** |

### Prototype screens

| Screen | Story | ACs | Status |
|---|---|---|---|
| P1 HR card (row, hint, save lines, greying) | US-1, 2, 10 | AC-3..8, 56 | covered |
| P2 Attendance month | US-4 | AC-30, 31 | covered |
| P3 Day sheet (too old, joining strip, server refusal, no limit) | US-4 | AC-32..36 | covered |
| P4 `#att-req` (note, inline, range sentence, refusal box, stale page) | US-5 | AC-37..43 | covered |
| Hindi / phone / dark | US-5, 12 | AC-66, 72, 73 | covered as a **manual gate; nothing measured yet** |
| Gate 2 Decision 2 (manager save line names a date) | -- | -- | **Not answered by Surbhi, not specified, not drawn.** Open (Q5b). No AC |

### Security (`01c`)

| ID | ACs | Status |
|---|---|---|
| SEC-1 | AC-9, 10, 27 | covered |
| SEC-2 | AC-27, 29, 51 | covered |
| SEC-3 | AC-11, 12 | covered (`validate`, not `before_insert`) |
| SEC-4 | AC-19 | covered |
| SEC-5 | AC-18 | covered |
| SEC-6 | AC-15..17 | covered |
| SEC-7 | AC-52..54 | covered |
| SEC-8 | AC-56, 57, 58 | covered |
| SEC-9 | AC-2, 7, 8 | covered |
| SEC-10 | AC-20 | covered |
| SEC-11 | AC-44, 69 | covered |
| SEC-12 | AC-45..47 | covered |
| SEC-13 | AC-23 | covered |

### Privacy (`01c`)

| ID | ACs | Status |
|---|---|---|
| PRIV-1 | AC-64 | covered (diff check) |
| PRIV-2 | AC-28 | covered |
| PRIV-3 | AC-30, 55 | covered |
| PRIV-4 | AC-29 | covered |
| PRIV-5 | AC-29 | covered |
| PRIV-6 | AC-28 | covered |
| PRIV-7 | none | **No AC by design**: "nothing to retain" is a statement (section 16.5), not a behaviour. Listed so it is not read as dropped. |

### DevOps (`07`)

| ID | ACs | Status |
|---|---|---|
| OPS-1 | AC-27, 68 | covered |
| OPS-2 | AC-68 | covered |
| OPS-3 | AC-63 | covered as a release-note and process step; **needs Surbhi/Grace to read the script, no test** |
| OPS-4 | AC-9, 29 | covered |
| OPS-5 | AC-7, 8, 21 | covered |
| OPS-6 | AC-68 | covered |
| OPS-7 | AC-68 | covered |
| OPS-8 | AC-30, 68 | covered |
| OPS-9 | AC-70 | covered |
| OPS-10 | AC-55 | covered |
| OPS-11 | AC-24 | **Not adopted: Surbhi's decision** (future dates out; Gate 1 separate ticket). A far-future `to_date` still passes. |
| OPS-12 | AC-67 | covered (manual) |
| OPS-13 | AC-59 | covered; the measure is dropped |
| OPS-14 | AC-48..50 | covered |
| OPS-15 | AC-61 | covered (manual) |
| OPS-16 | AC-60, 62 | covered |
| OPS-17 | AC-62 | covered; previous-tag proof **open** |
| OPS-18 | AC-63 | covered |
| OPS-19 | AC-63 | covered |
| `02a` strings 1-6 | AC-48 | covered; 7-9 added by AC-49 |
| `07` §4 Q1 (`#att-req` calls `get_requests_history`) | AC-37, 44 | covered |

### What I could not trace

1. Brief §10 "HR changes the value without an engineer" and "0 hidden rules": **an outcome, not a behaviour**; no AC can prove it.
2. Gate 1 open item 3 (is `#att-req` used on Grace and DTC): **no AC, unanswered** (Q7).
3. Gate 2 Decision 2 (manager save line date): **no AC**, not decided.
4. PRIV-7: a statement, no test.
5. Hindi quality, phone width, 200% text, keyboard and screen reader: **manual gate AC-66; never measured**.
6. OPS-3 reading Grace's script: process step only.

## 20. Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| Q1 | **Hook event.** `before_insert` (as the brief says) misses an edit of a draft's dates; I spec `validate` with a "new or dates changed" condition. Agree? | Surbhi, with `hrms-fullstack-engineer` on `has_value_changed` | The shape of the hook and AC-12. Default if no answer: `validate`. Does **not** block the first day of work. |
| Q2 | An HR Manager's own old day is refused on the portal **and** the Desk (the hook binds the record). A tenant with one HR person and no other System Manager cannot fix it. Accept, or exempt the Desk route for HR roles (which Gate 3 C3 rejected as "two rules")? | Surbhi | AC-26 wording only |
| Q3 | **HR save-line example date** (n ≥ 1) needs a reference calendar. My assumption: the company default holiday list, else "counting every day". The shared counter takes an employee, so an optional holiday-list argument is needed. `Company.default_holiday_list` is **[UNVERIFIED, ERPNext not on this Mac]**. If it costs more than S, fall back to the saving HR user's own Employee record. | `hrms-fullstack-engineer` (UX said "not a Surbhi question"); Surbhi only if it changes the line | AC-5 for n ≥ 1 only |
| Q4 | Who is the native Hindi reader, and who runs the 390 px/200%/keyboard/screen-reader check? | Surbhi | **Release** (AC-66), not build |
| Q5 | Weekday format ("Mon 16 Nov"): the manager sentence uses `acNice` with no weekday; I change it only for own-day sentences and for the server's messages. The server needs a weekday formatter, `frappe.utils.formatdate` precedent has none. | Engineer | Message format in AC-9 |
| Q5b | Gate 2 Decision 2: manager save line names a date too? One string; not adopted until she says. | Surbhi | Nothing structural |
| Q6 | Does `frappe.logger("security").warning` reach `security.log` on our sites, and how long is that log kept? 01c inferred warnings are written and infos not; `grooming.py:996` and `performance_api.py:3574` use `.info` on the same logger. | `hrms-devops-engineer`, one command on dev | AC-47, AC-61; whether SEC-12 is real |
| Q7 | Is `#att-req` used on Grace and DTC, and by which roles? (Gate 1 item 3, still open.) | Surbhi / engineer on dev data | How much path B matters. Does not change the build, since both paths are bound. |
| Q8 | Refusal sentence adds "counted in {basis}" against the prototype (section 17). | Surbhi | AC-9/32 wording |
| Q9 | The loading state: before `get_requests_history` returns, the note and inline check are not drawn (BA default). Submit still works and the server guards. Needs UX confirmation (01b designed no loading state). | `hrms-ux-designer` | One AC detail |
| Q10 | Previous production image tag proven in `alvoraa-app` (OPS-17). | DevOps | Release |

## 21. Assumptions

- `[ASSUMPTION]` `Employee.date_of_joining` is the joining day (01b; `_get_employee` already reads it, `hr_api.py:301-311`).
- `[ASSUMPTION]` `Document.has_value_changed()` and `is_new()` exist and behave as in standard Frappe; Frappe source is not on this Mac.
- `[ASSUMPTION]` Frappe runs `validate` doc-event hooks when `insert(ignore_permissions=True)` is used (AC-10 proves it).
- `[ASSUMPTION]` Rehire creates a new Employee record.
- `[ASSUMPTION]` No tenant has employees whose calendar day differs from the site's.
- `[ASSUMPTION]` HR screens are English only today.
- `[ASSUMPTION]` Key name `alvoraa_employee_filing_window_days`; per-day key `own_window`; history key `att_window` are proposals.
- `[ASSUMPTION]` The `Attendance Request` hooks entry becomes a list for `validate` (the existing `before_insert` string is untouched).

## 22. Ready check (`definition-of-ready-done.md`)

**Result: PASS, with two boxes not fully ticked and five items to close. Not "ready" on every line: I say which.** The rule is that more than two failing boxes sends a slice back; two does not.

| Box | State |
|---|---|
| Brief: one user, one outcome; JTBD in user's words; competitive analysis labelled; Kano (proxy) stated; persona enhancements decided; WOW named; out of scope written; user approved | Tick (Gate 1) |
| Design: clickable prototype reviewed | Tick (Gate 2, local file and artifact link) |
| Design: user feedback logged in `ux-learnings.md` | **Partly.** Gate 1 feedback is at lines 311-314 (file modified, uncommitted in the working tree). I found no entry for Gate 2's Decision 1 answer by a grep for "084"; **not checked beyond that**. |
| Design: every state designed (empty, loading, error, no permission, first-time) | **Not fully.** Empty, error, no-permission, first-time are in 01b. **Loading is not** (Q9; BA default given). |
| `01c` SEC/PRIV numbered | Tick |
| `07` §1-3 with OPS numbered | Tick (§4 answers added) |
| Gap analysis against what Frappe HR **actually** ships (verified in source) | Tick (section 3, cited) |
| Epic, stories, INVEST, sized, linked to prototype, "must not" stories | Tick (US-1..12, 25 points) |
| Every story has Given/When/Then with an observable oracle | Tick (AC-1..73) |
| Traceability complete | Tick, **with six named untraceable items** (section 19) |
| Permission matrix with negative cases | Tick (section 8) |
| Edge cases | Tick (section 10) |
| NFR numbers made specific | Tick (section 11; nothing measured) |
| Migration stated | Tick ("nothing", section 12) |
| Compliance sub-analysis | Tick (section 16) |
| Every COMPLIANCE question names an owner and what it blocks | Tick |
| No prohibited capability | Tick |
| New Frappe app installed | n/a |
| Open questions have owners; none blocks the first day of work | Tick. **Q4 and Q10 block release, not build. Q3 blocks one AC's wording.** |

**Missing pieces, named:** (1) Gate 2 feedback entry in `ux-learnings.md`; (2) a loading-state decision (Q9); (3) Surbhi's yes or no on Q1 (hook event), Q2 (HR's own day) and Q8 (basis in the refusal); (4) a native Hindi reader and the device checks (Q4); (5) the Q3 reference calendar for the HR save line.

---

## Gate 4 — Surbhi's decisions on the spec, 19 November 2026

She said "go ahead with all your recommendations". Every question in §20 is answered.

**Q1 — `validate`, not `before_insert`. CONFIRMED.**
The session that briefed this slice had recommended `before_insert`; that was wrong and
the analyst corrected it. `Employee` holds `write=1` on `Attendance Request` with **no
`if_owner`** (read from `attendance_request.json` this session). So a request can be
created for a permitted day and its `from_date` edited afterwards, and `before_insert`
never runs again. The hook goes on `validate`, checking when the record is new or its
dates changed, and only when the record is the caller's own. **AC-12 must fail if the
hook is moved to `before_insert`.**

**Q2 — an HR Manager's own old day stays bound, on the Desk too. CONFIRMED.**
Gate 3 called it "one extra click"; the analyst showed that on a tenant with a single HR
person it is a dead end, because `refuse_own_submit` also blocks self-approval. Accepted
anyway. The alternative is a role exemption, which Gate 3 rejected on the grounds that
such lists never stay at one entry. A one-HR-person tenant corrects the Attendance record
directly in the Desk, which is a third route and is not bound by this slice.

**Q8 — yes, the refusal names the counting basis.** ", counted in working days on your
own holiday list", or the calendar-day fallback wording. Without it, "the oldest day is
Mon 16 Nov" looks arbitrary on a Thursday. Satisfies 01b §5.2, OPS-4 and SEC-13.

**Q3 — the HR save-line example uses the company's default holiday list**, and the
words "counting every day" where there is none. It governs one sentence on one screen.

**Q6 — carried, not answered here.** Whether `frappe.logger("security").warning` reaches
`security.log` on our sites, and for how long, is settled by one command on a dev site
during build, not by a decision.

**Tier — build and review as TIER 1, not the brief's Tier 2. CONFIRMED.**
It adds a refusal hook on a DocType and touches a settings-write path, and
`usage-discipline.md` puts who-can-change-what in Tier 1.

**Open, and blocking RELEASE rather than build:**
- Q4: a native Hindi reader for the strings (AC-66 has no owner named).
- Q10: the previous production image tag, proved to exist in `alvoraa-app`, before
  anyone needs a rollback.
- Q7: whether `#att-req` is used on Grace and DTC, and by which roles.
- Gate 2 Decision 2: whether the manager's save line should also name a date.

**Raised during this gate and NOT part of this slice.** `Employee` holds `create`,
`write`, `delete`, `export` and `share` on `Attendance Request` with no owner
restriction in either app, and no `get_permission_query_conditions` for that DocType in
`hrms/hooks.py` or `alvoraa_portal/hooks.py`. What scopes an employee to their own
requests is therefore a per-tenant **User Permission**, which is configuration, not code.
**No tenant has been checked.** This is not a claim that anything is broken; it is a
claim that nothing in the code prevents it. Belongs to **ALV-387**.
