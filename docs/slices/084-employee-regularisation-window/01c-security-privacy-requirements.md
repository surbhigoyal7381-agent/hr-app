---
slice: 084-employee-regularisation-window
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-11-19
status: draft
inputs: [01-product-brief.md (with Gate 1), 01a-ux-opportunities.md, 01b-ux-design.md (with Gate 2), 07-devops-inputs.md §1]
---

# 084 Security and privacy requirements

**Risk tier 2**, as the brief. I agree with the tier. It touches no pay figure and
deletes nothing, but it narrows a route an employee uses to correct a record that
drives their pay, so it is one step above wording work.

**Recommend only. Surbhi decides.**

## 0. What I read, and what I did not

- **Read (proven):** checkout `/Users/mac/hr-app`, branch `dev`, SHA `a57764c4`
  (`git rev-parse HEAD`, this session).
  - `alvoraa_portal/alvoraa_portal/hr_api.py` 301-311 (`_get_employee`), 1682-1692
    (the `#att-req` nav gate), 2885-2902 (`submit_attendance_request`), 3005-3030
    (own request history), 3311-3330 (`ALLOWED_ORG_SETTINGS`), 3370-3440
    (`get_org_setting`, `set_org_setting`), 3447-3480 (`_require_hr`,
    `_refuse_store_hr`).
  - `attendance_correction.py` 280-300 (`_employee_for`, `_me`), 620-700 (the month
    payload and `can_request`), 1105-1160 (`raise_correction`), 1278-1340
    (`_working_days_away`), 1370-1460 (the manager window), 2244-2268
    (`raise_for_report`).
  - `employee_field_rights.py` 50-100, 203-230, 255-285; `hooks.py` 179-191, 249-276.
  - `frame_api.py` 163-186 (`_may_save_settings`).
  - `hrms/hrms/alvoraa_hr_core/access.py` 28-62 (`log_refusal`, `refuse`,
    `is_own_record`).
  - Frappe HR, in this repo: `hrms/hrms/hr/doctype/attendance_request/`
    (`.json` permissions and `.py` `validate`), `hrms/hrms/hr/utils.py` 216-228
    (`validate_dates`), `hrms/hrms/hr/doctype/hr_settings/hr_settings.json`.
  - `public/js/ess/portal.js` 12156-12171 (`submitAttendanceRequest`).
- **Ran:** `git rev-parse HEAD`; greps and a `python3 -c` read of two DocType JSON
  files. **Nothing was written, no site was touched, no tenant was opened, no
  login was used.**
- **Could not check:** Frappe's own framework source is **not on this Mac**
  (`find / -name defaults.py -path "*frappe*"` returned nothing), so how
  `frappe.db.get_default` scopes a default, and whether `frappe.logger("security")`
  actually writes a file, are **inferred, not proven**. ERPNext source is not here
  either, so I could not check whether `Employee.user_id` is unique. Access needed:
  a bench with `apps/frappe` and `apps/erpnext`, or a running site.
- **Not checked:** per-tenant `Custom DocPerm` rows. The permissions I quote are the
  shipped DocType JSON. On a real tenant the Custom DocPerm table is the one that
  decides (memory: `bench-stale-app-sync`).

**Labels used below:** *proven* (I read the line or ran the command) · *inference*
(drawn from what I read, with the basis named) · *not checked* · `[ASSUMPTION]`.

---

## 1. Your five points: confirmed, corrected, extended

### 1.1 The existing hole — **confirmed, and it is wider than two endpoints**

Proven. `hr_api.submit_attendance_request` (`hr_api.py:2885-2902`) takes `from_date`
and `to_date` from the caller, applies no date check of its own, and inserts with
`ignore_permissions=True`. `attendance_correction.raise_correction`
(`attendance_correction.py:1105-1130`) checks only "end not before start" and "not in
the future". Both must be bound, or the setting is decoration.

**Two corrections to the picture, both in your favour:**

1. **`ignore_permissions=True` does not skip `validate()`.** Frappe HR's own
   `AttendanceRequest.validate` still runs on path B, and it already enforces
   `from_date >= Employee.date_of_joining`, `to_date <= relieving_date`, an active
   employee, and no overlapping request (`attendance_request.py:44-50`,
   `hrms/hr/utils.py:216-228`, `attendance_request.py:109-140`). So path B is not
   unchecked — it is unchecked **by us**. What `ignore_permissions=True` does skip is
   the permission check, which is a separate pre-existing issue, correctly sent to
   its own ticket at Gate 1.
2. **There is a third path, and it is the one that breaks the "both paths" plan.**
   `hrms/hr/doctype/attendance_request/attendance_request.json` grants the **Employee**
   role `create=1` and `write=1` (proven, read from the JSON). So an employee with a
   valid session can create an `Attendance Request` through the Desk or
   `/api/resource/Attendance Request` without touching either portal endpoint. A check
   written inside the two whitelisted functions does not bind it. **That is a guard by
   instruction, not by structure** — see SEC-3, where I recommend one `before_insert`
   hook instead of two copies of the check. The hooks entry for this DocType already
   exists (`hooks.py:179-187`), so this is the cheaper rung as well as the safer one.

**Also answered (brief open question 4, and a kill criterion): Frappe HR ships no
days-back limit for an Attendance Request.** Proven: its `validate()` chain has no
such check, and the only back-dating control in `HR Settings` is
`restrict_backdated_leave_application` / `role_allowed_to_create_backdated_leave_application`,
used in `leave_application.py:208` only. The slice is not already configuration.

### 1.2 The joining day as a trust boundary — **confirmed, with four edges**

The joining date must come from the Employee record the request is being created for,
never from the request. Proven that it is currently safe to do so:

- **An employee cannot change their own joining date.** `date_of_joining` is in
  `LEVEL_2` (`employee_field_rights.py:55`), so it is permlevel 2 and an employee has
  no write at that level; and `refuse_own_locked_change`
  (`employee_field_rights.py:203-229`, hooked at `hooks.py:250`) refuses a change to
  any high-permlevel field on one's **own** record, HR included. The joiner module
  states plainly that **no code writes `Employee.date_of_joining`**
  (`alvoraa_joiner_submission.py` docstring, slice 082-SEC-1).
- **Blank joining date.** Frappe skips its own floor check when the field is empty
  (`hr/utils.py:224`). Our exception must do the opposite and **not apply** — see
  SEC-5. Otherwise "blank" would read as "every day is the joining day" in a careless
  comparison against a null.
- **It can still move, legitimately.** `Employee Promotion` / `Employee Transfer` with
  a new company writes `date_of_joining` (`employee_field_rights.py:270-272`). HR only.
  So the exception day is correct whenever it is read, and must not be cached across a
  request.
- **More than one Employee record.** `_me()` and `_get_employee` both call
  `frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, ...)`
  (proven, `attendance_correction.py:283`, `hr_api.py:303`). With two active records
  for one login, `get_value` returns one of them and nothing says which. I **could not
  check** whether ERPNext enforces one Employee per `user_id`. The fix costs nothing:
  read the joining date from the **same** employee row the request is built from
  (SEC-4), so the window, the exception and the document cannot be about three
  different records.
- **A rehire** is normally a new Employee record with a new joining date, so the
  exception follows the new record. That is the right answer. `[ASSUMPTION]` — I did
  not read a rehire flow.

**Leavers:** both employee lookups filter `status = "Active"` (proven). A leaver with
a live session gets the existing "not linked to an employee record" refusal before any
of this runs, and `validate_dates` also caps at `relieving_date`. No new exposure, and
this is one of the lookups that got rule 3 of my standing lessons right.

### 1.3 Who the window must NOT bind — **confirmed, with one open edge**

- **HR's review route** stays unbounded. That is the escape hatch every refusal
  sentence points at. If it is bound, the design breaks and the DPDP correction
  argument in §5 breaks with it.
- **The manager path** (`raise_for_report`, `attendance_correction.py:2244`) keeps its
  own key, `alvoraa_manager_filing_window_days`. Two settings, neither reading the
  other.
- **Open edge I did not find answered anywhere:** an **HR Manager raising a request
  about their own day on the portal day sheet** is on the employee self path, so the
  new window binds them. Binding by *path* is one rule; exempting by *role* is two
  rules and lets an HR person self-serve an old day. I recommend binding by path and
  naming it in the hint. They still cannot approve it — `refuse_own_submit`
  (`hooks.py:183`) refuses that on every route including the Desk. Small, reversible,
  Surbhi's call (⚠ DECISION C3).

### 1.4 The setting's write guard — **confirmed for a new key, with one trap**

Proven by reading `set_org_setting` (`hr_api.py:3383-3387`): `_require_hr()` and
`_refuse_store_hr()` both run **before** any key-specific logic, so they bind a new key
by construction. `_require_hr` allows HR Manager and System Manager only (HR User is
refused, and `test_org_setting_scope_030.py:93` already asserts that for an existing
key). `_refuse_store_hr` refuses anyone holding a Branch User Permission, logs rule
`030-D4` and throws. `frame_api._may_save_settings` mirrors it for the screen.

**The trap, and it costs an employee their right:** the "blank is a real answer" branch
is written for one key by name —
`if key == MANAGER_FILING_WINDOW_KEY and value == ""` (`hr_api.py:3390-3396`). For any
other key the validator is `re.fullmatch(r"[0-9]{1,3}", value)`, which an empty string
fails. So unless the new key is added to that branch, **HR can set a limit and then
never remove it**: the smallest value they could reach would be `0`, which is the
tightest setting there is. That is a right taken away with no way back. SEC-9.

### 1.5 Does the refusal text disclose anything? — **No, with one condition**

Stated explicitly, as asked.

- The refusal carries **two dates and a basis phrase**. The boundary comes from
  `_working_days_away`, whose basis string is "working days on this person's own
  holiday list" or "calendar days, because this person has no holiday list" (proven,
  `attendance_correction.py:1304-1319`). No holiday list name, no company, no other
  person, no reason for absence, no attendance status.
- Both dates are **the reader's own**: their boundary, their joining date. On the
  self path the reader is the subject.
- A joining date is the person's own employment fact. Showing it back to them discloses
  nothing they do not have on their letter.
- **The one condition.** The month payload
  (`attendance_correction.py` ~660-700) is also served to a **manager and to a
  skip-level reader** — the code says reading reaches the whole reporting line, and
  only `can_request` is narrowed to direct reports. A direct manager and scoped HR can
  already see a report's `date_of_joining` (`hr_api.py:1169`, `1505`), but a
  **skip-level** manager cannot through those endpoints. So if `joined_on` is added to
  the month payload unconditionally, it becomes a new, small disclosure to skip-level
  managers. Send it only when `is_self` — PRIV-3. `time_api` already has exactly this
  shape to copy, including a test that the non-self payload carries nothing outside an
  allow-list (`time_api.py:71`, `SUBJECT_KEYS`).

---

## 2. Threat model in four lines

1. **Who would want this, and what is the cheapest way?** Nobody is attacking this
   setting for data. The realistic actor is an **employee working around the limit** to
   get an old day regularised — and the cheapest way is not an attack at all: open the
   Desk or call `/api/resource/Attendance Request`, which the Employee role is allowed
   to do (proven, §1.1). Second cheapest: a range that starts on the joining day.
2. **Blast radius of one mistake.** One person, one of their own days. There is **no
   cross-tenant and no cross-company surface here**: both endpoints build the document
   from the caller's own employee record, and the setting is a site default. A wrong
   refusal costs one person an unfixed day of attendance, which can cost pay. A wrong
   allow costs nothing by itself, because an employee cannot submit their own request:
   the Employee role has no `submit` on the DocType (proven, JSON) and
   `refuse_own_submit` blocks self-approval on every route. **HR still decides every
   one.**
3. **What does it make possible that was impossible before?** One new org-level
   number; one new refusal; one new date on the employee's own screen. No new
   collection, no new export, no new outbound flow, no new public route, no model
   prompt.
4. **How would we find out if it went wrong?** Today: a support ticket. The window
   writes no record of a refusal, and `set_org_setting` writes no record of who changed
   the number (§4, SEC-12). That is the detection gap, and it is the honest answer.

---

## 3. Data inventory

| Field or object | Sensitivity | Purpose | New in this slice? | Retention | Who may see it |
|---|---|---|---|---|---|
| `alvoraa_employee_filing_window_days` (name is a proposal; the engineer names it) — a whole number 0-30 or blank, stored as a Frappe default | **Not personal data.** Organisation config | Apply the employer's own attendance-correction policy | **Yes** | Until HR changes it. Nothing to purge | Read: HR Manager / System Manager through `get_org_setting`. Write: the same, minus a store-scoped HR person |
| The boundary date shown to an employee | Personal-ish: derived from **their own** holiday list and today | Tell them before they type | Yes, as a value on screen | Not stored | The employee themselves |
| `Employee.date_of_joining` | Personal data, already held, permlevel 2 | The always-allowed day | **No.** Read only | Existing employee-record retention | The person; HR; their direct manager (already). **Not** a skip-level manager — PRIV-3 |
| Employee's holiday list | Already held | Count working days | No. Read only | Existing | Not shown; only the basis phrase |
| The refusal event (who was refused, which day) | Would be personal data | — | **Not stored, deliberately** (PRIV-2) | n/a | n/a |
| `Attendance Request` row | Personal data, existing DocType | The correction itself | No new field | Existing | Existing |

**No new personal data is collected, stored, exported, logged or sent anywhere.**

---

## 4. Access intent — including who must NOT

| Actor | May | Must NOT |
|---|---|---|
| Employee (self) | See their own boundary date and their own joining date; raise a day on or after the boundary; raise their joining day alone | See or read the setting's raw value through any endpoint; raise a day before the boundary on **any** path, including the Desk and the REST API (SEC-3) |
| Line manager | Everything they have today, unchanged | Be bound by the employee window; see a report's `joined_on` in the month payload unless they could already see it (PRIV-3) |
| Skip-level manager | Read a month as today | Receive `joined_on` (PRIV-3) |
| Store-scoped HR (Branch User Permission) | **Read** the setting | **Save** it — refused and logged as `030-D4` (SEC-8) |
| HR Manager / System Manager, company-wide | Read and save the setting; raise and decide corrections for any day through the HR route | Be exempt from the window on the **employee self path** — unless Surbhi decides otherwise (⚠ C3) |
| HR User | Decide corrections as today | Save the setting (already refused) |
| Anyone, any role | — | **Approve their own request** (`refuse_own_submit`, existing). This slice must not weaken it |
| Guest | Nothing | Everything. No endpoint here is `allow_guest` and none may become one |

---

## 5. Obligations engaged

| Obligation | Source and date I checked | What it means here |
|---|---|---|
| **DPDP Act 2023 — accuracy and correction** (the Data Principal's right to correction; the baseline's row: "Employee-initiated correction request with a routed workflow and an audit trail") | `.claude/context/security-compliance-baseline.md` §2, **verified 24 Aug 2026** — 87 days old, **stale on 22 Nov 2026**. I did **not** re-verify against a primary source in this run, because this slice needs no new legal fact, only the existing one | An attendance regularisation **is** the employee's route to correct a personal-data record that drives pay. This slice puts a time limit on it. The control that keeps it defensible is that HR's route stays open and is **named in every refusal** (PRIV-5) |
| **DPDP — grievance redressal** | same, same date | If a refused employee complains, somebody must be able to say what the rule was and who set it. Today nothing records who changed the number (SEC-12) |
| **DPDP — data minimisation** | same | Do not build a refusal log or a counter. PRIV-2 |
| **The employer is the Data Fiduciary; we are the processor.** The setting is their policy choice, not ours | baseline §2 closing paragraph | Our duty is to make the alternative route visible and to store nothing extra |
| **CERT-In directions** | baseline §3, verified 24 Aug 2026 | Not engaged. No incident surface, no new log, no new outbound flow |
| **EU AI Act** | baseline §4, verified 24 Aug 2026 | **Not engaged.** No model, no profiling, no inference about a person. A date comparison is not an automated decision about an individual in that sense, and nothing is decided about the person — only whether one route is open |
| **Programme state, honestly** | `.claude/context/compliance-feature-map.md` row A8 | The **data-principal rights console is P0 and its status column is `?`** — it is not built. So the only correction route a tenant has is the one this slice narrows, plus HR by hand. Say that out loud rather than letting the setting ship as if a console existed |

**I am not a lawyer.** The compliance questions are in §8.

---

## 6. Abuse cases

| # | Actor, state, path, result | Bound by |
|---|---|---|
| A1 | An employee with a valid session **calls `submit_attendance_request` directly** from a console with `from_date` six months back. Today: the request is created (proven by reading the function). | SEC-1 |
| A2 | The same employee **posts to `/api/resource/Attendance Request`** or uses the Desk form. The Employee role holds `create` and `write` (proven, DocType JSON). Two endpoint checks do not touch this. | **SEC-3 — the one that decides whether this is a control or a suggestion** |
| A3 | **A range that straddles the boundary**: `from_date` = yesterday, `to_date` = two months back — refused already by `from > to`. The live case is `from_date` inside the window and `to_date` **before** it; Frappe refuses that too (`from > to`). The real straddle is the other way: a range **starting** before the boundary and ending today. Refused whole, naming the oldest day. | SEC-6 |
| A4 | **The joining-day leak** (UX decision 1, Gate 2 chose (a)): `from` = joining day, `to` = today carries every too-old day between. Refused whole unless `from == to == joining day`. | SEC-6 |
| A5 | **A client sends another employee's id.** Not possible on either path: neither function takes an employee argument — `raise_correction` builds from `_me()` and `submit_attendance_request` from `_get_employee()` (proven; `raise_correction`'s docstring says why). The Desk path is bounded by the User Permission on Employee for that login — **not checked per tenant** (memory: DTC's rows are narrow per DocType). | SEC-4, and a check named in SEC-3 |
| A6 | **Replay / flooding.** Frappe refuses an overlapping request for the same employee while one exists at `docstatus < 2` (proven, `validate_request_overlap`). So the same day cannot be raised twice. **The missing monthly cap does not matter for this slice, and the window makes it matter less:** once a window is set, the number of distinct days an employee can raise at all drops to the window length plus their joining day. Two small residuals, accepted: the overlap query narrows by `shift` when a shift is set, so two requests for one day under different shifts can coexist; and cancelling a request frees its dates for a new one. Neither creates exposure — only rows HR must read. Frappe's own request rate limiting: **not checked**. |
| A7 | **Employee edits their own joining date** to re-open an old day. Refused by permlevel 2 plus `refuse_own_locked_change` (proven). An HR person editing **their own** record is refused too. | SEC-4, SEC-5 |
| A8 | **A store-scoped HR person sets the window** for the whole organisation. Refused and logged `030-D4` (proven for existing keys, and the guard runs before the key check). | SEC-8 |
| A9 | **HR sets a limit and then cannot remove it** because blank is refused for the new key. A self-inflicted denial of an employee right. | SEC-9 |
| A10 | **An employee with no holiday list** is refused a day a colleague may raise, because the fallback counts calendar days and is tighter walking back (proven, `_working_days_away` docstring and loop). Configuration narrows a person's right. | SEC-13 |
| A11 | **A leaver with a live session** raises a day. Refused earlier: both lookups filter `status = "Active"`. | SEC-10 |
| A12 | **The screen and the guard disagree** after HR changes the number while a page is open. The UX design already accepts this and says the refusal names the live date. The risk is the opposite one: a browser that computes the rule itself would offer a day the server throws on. | SEC-2 |

---

## 7. Requirements

Every item says what must be true and how it is tested. The analyst traces each to an
acceptance criterion.

### Security

**SEC-1 — Both portal employee paths are bound, by one derivation.**
`attendance_correction.raise_correction` and `hr_api.submit_attendance_request` both
refuse a request whose **first day** is older than the boundary, computed by one
function that also produces the date the screens show.
*Test:* a test that calls each endpoint directly with a too-old `from_date` and asserts
a throw and that no `Attendance Request` row was created; and a second that asserts the
date in the thrown message equals the date in the screen payload. Extend
`tests/test_attendance_correction.py` (it already covers the manager window).

**SEC-2 — The rule lives in one place; the browser never computes it.**
The boundary date, and (recommended, per the UX handoff) the per-day "can raise" flag,
come from the server. No day count or hour count appears in any string.
*Test:* a grep-style assertion in the test suite that the new sentence strings contain
no digit-plus-"day"/"hour" literal, plus the payload-equals-refusal test in SEC-1.
*This is the Grace "48 hours" failure, written as a test.*

**SEC-3 — The third path is decided, not forgotten.** ⚠ DECISION
The Employee role holds `create` on `Attendance Request` in the shipped DocType, so
Desk and `/api/resource/...` bypass both whitelisted functions.
**Recommended: put the check in a `before_insert` hook on `Attendance Request`, applied
when `is_own_record(doc.employee)`.** One mechanism; it binds all three paths; the
hooks entry for this DocType already exists (`hooks.py:179-187`); `raise_for_report`
(manager, not own record) and HR's route are untouched by construction. The alternative
— two endpoint checks and a documented accepted gap — is a guard by instruction, and
this file's rule is that a prohibition enforced by instruction is not a control.
*Fail-closed default if nobody decides:* the hook.
*Test:* create an `Attendance Request` for a too-old day **as the employee, through
`frappe.get_doc(...).insert()`**, not through the portal endpoint, and assert it is
refused. Also assert the manager path and an HR-created request for another person are
**not** refused by it.

**SEC-4 — The joining date is read from the server, from the same employee row.**
It is taken from the `Employee` record the request is being created for — never from
the request payload, a session value or a browser field.
*Test:* call both endpoints with extra junk keys (`date_of_joining`, `employee`,
`joined_on`) in the payload and assert the outcome is identical to the clean call.

**SEC-5 — A blank joining date means no exception.**
When `Employee.date_of_joining` is empty, the window applies to every day with no
exception, and no sentence about a joining day is shown.
*Test:* an employee fixture with `date_of_joining` cleared; assert the too-old refusal,
assert the payload carries no `joined_on`, and assert no null-versus-date comparison
throws.

**SEC-6 — The joining day is allowed only alone.**
Allowed when `from_date == to_date == date_of_joining`, however old. A range whose
first day is the joining day but whose last day is later is **refused whole**, with the
sentence from the design. A range whose first day is any other too-old day is refused
whole.
*Test:* four cases on **both** paths — joining day alone (allowed); joining day to
today (refused whole, nothing created); a day after joining but before the boundary
(refused); the boundary day itself (allowed). **Observability note:** the fixture
employee's `date_of_joining` must be older than the boundary, and the tenant's setting
must be non-blank, or all four assertions pass for the wrong reason.

**SEC-7 — The window binds nobody it was not meant to.**
It does not change `raise_for_report` (the manager path keeps
`alvoraa_manager_filing_window_days`), does not change HR's review and submit route,
and neither setting reads, greys or counts the other.
*Test:* with the employee window set to 0, assert a manager can still file within the
manager window, and an HR Manager can still submit a correction for a day a year old.

**SEC-8 — Who may change it is unchanged, and proven for the new key.**
HR Manager or System Manager with company-wide reach may save. A store-scoped HR person
may read and is refused on save, logged with rule `030-D4`, with the stored value
unmoved. HR User and a plain employee are refused.
*Test:* the new key added to the existing scope test
(`tests/test_org_setting_scope_030.py`, which is written for one key at a time), and to
the allow-list test (`tests/test_org_settings_allowlist_012.py`).

**SEC-9 — Blank must remain reachable, and out-of-range values must be refused.**
The key is added to `ALLOWED_ORG_SETTINGS` as `range(0, 31)` **and** to the
blank-accepted branch at `hr_api.py:3390-3396`, so HR can return the tenant to "no
limit". `31`, `-1`, `"3 "`, `"abc"` and `"999"` are refused with nothing stored.
*Test:* save `""` and assert the stored default is `""` and the reader returns `None`
(no limit); save `0` and assert the reader returns `0` (today only) — the two must
never collapse into each other; then the refusal cases, each asserting the stored value
did not move.

**SEC-10 — A leaver is refused before any of this runs.**
*Test:* set the fixture employee to `Left` and assert both endpoints throw the existing
"not linked to an employee record" error and create nothing.

**SEC-11 — The slice adds no `ignore_permissions` and no new whitelisted endpoint.**
The boundary rides on payloads that already exist (the month payload and the requests
panel), per DevOps OPS-1. `submit_attendance_request`'s existing
`ignore_permissions=True` is **out of scope** (its own ticket, Gate 1) and must not be
quietly removed or quietly copied.
*Test:* the repo's `ignore_permissions` count does not rise; `grep -c "@frappe.whitelist"`
in the two changed modules does not rise.

**SEC-12 — The setting change is attributable.** ⚠ DECISION, P2
Proven: `set_org_setting` writes `frappe.db.set_default` and commits, and **writes no
audit record of any kind** — no Version row, no log line. This is true of all six keys
today, so it is pre-existing debt; it lands here because this is the first key that
**removes an individual's right**, and the grievance question ("who set it to 0, and
when?") has no answer.
**Smallest sufficient fix:** one `frappe.logger("security").warning(...)` line in
`set_org_setting` carrying `user`, `key`, old value, new value, timestamp — the same
mechanism `log_refusal` already uses (`access.py:34`). **No new DocType, no ledger.**
*Test:* patch the logger, save the setting, assert one line with both values.
*If Surbhi declines:* record it as accepted residual risk with a date, in §9.

**SEC-13 — The fallback direction is chosen on purpose.** ⚠ small decision
When the holiday list is unreadable, `_working_days_away` counts calendar days, which
walking back is **tighter** — so missing configuration takes a day or two away from the
employee. For a control that **restricts a person**, "fail closed" and "protect the
person" point in opposite directions. My recommendation: **keep the existing shared
counter** (one counter, as the docstring argues) and accept that the error is at most a
weekend, because HR's route stays open and nothing is auto-approved. Do not write a
second counter for this slice.
*Test:* an employee with no holiday list gets a boundary computed in calendar days, the
basis phrase says so, and the sentence still names HR.

### Privacy

**PRIV-1 — No new personal data.**
The slice stores no new field, creates no new DocType, and sends no personal data
anywhere new.
*Test:* the migration/fixture diff adds no field to `Employee` or `Attendance Request`;
`git diff --stat` shows no new DocType folder.

**PRIV-2 — No refusal log, no counter, no new store of who was refused.**
A refusal is a `frappe.throw` and nothing else. In particular it must **not** call
`access.refuse()` / `log_refusal`: that writes `{user, endpoint, doctype, name}` to the
security log under a rule id, and an ordinary employee asking about an old day is
lawful behaviour, not misuse. Filing it there would (a) build a per-person record of
denied corrections with no retention answer, and (b) dilute the signal that log exists
for (SEC-17 misuse detection).
*Test:* patch `hrms.alvoraa_hr_core.access.log_refusal`, trigger the window refusal on
both paths, assert `call_count == 0`.
*The PM's "wasted submissions" measure therefore has no in-product baseline. That is
the right trade: the measure is worth less than the record would cost.*

**PRIV-3 — `joined_on` only on the person's own payload.**
The joining date is added to the month payload only when `is_self` is true, and to the
`#att-req` panel only for the caller. It never appears on a manager's or skip-level
reader's view of someone else's month.
*Test:* open a report's month as their manager and as a skip-level manager and assert
the payload has no `joined_on` key — the shape `time_api` already uses for
`SUBJECT_KEYS` (`time_api.py:71`).

**PRIV-4 — The sentences carry dates and nothing else.**
No employee name, no employee id, no holiday list name, no company, no attendance
status, no reason for absence, in any of the three places or in the server's throw.
*Test:* assert the refusal message matches a pattern of dates plus fixed words, and
contains neither the fixture's name nor its employee id.

**PRIV-5 — Every refusal names the way out.**
Each refusal sentence, on every path, says HR can still fix the day and what to tell
them. This is the control that keeps a time-limited correction route defensible under
DPDP (§5) — it is a compliance requirement, not a wording preference.
*Test:* assert the HR sentence is present in the thrown message on **all** refusal
branches: window, range-straddle, joining-day-with-a-range, and the 0 case.

**PRIV-6 — Nothing personal reaches a log or an error.**
The existing `log_error` in `_working_days_away` carries the employee id and no name or
reason (proven, `attendance_correction.py:1322-1327`); keep it that way, add no second
one.
*Test:* patch `frappe.log_error`, run both refusal paths, assert either no call or a
call whose message contains no name and no date-of-joining.

**PRIV-7 — Retention answer: nothing to retain.**
The setting lives until HR changes it. No refusal record exists. No purge job, no legal
hold interaction.
*Test:* none needed; stated in the spec so the question is not asked again at review.

---

## 8. Questions, sorted

### Must know — these change a requirement or an AC

| # | Question | Who decides | Blocks | My fail-closed default meanwhile |
|---|---|---|---|---|
| Q1 | **SEC-3:** hook on the DocType, or two endpoint checks plus an accepted Desk/REST gap? | Surbhi, with `hrms-fullstack-engineer` on feasibility | The shape of the guard and three ACs | The hook |
| Q2 | ⚠ **COMPLIANCE C1.** Is it acceptable for a tenant to set `0` (today only) on a route an employee uses to correct a pay-bearing record, given the rights console (feature map A8) does not exist? Specifically: must the product **force** HR's route to be named in the refusal (PRIV-5 says yes), and must the release note require the employer to tell staff before switching it on? | **Counsel**, through Surbhi. I am not a lawyer | Whether `0` stays on the allow-list, and the release note | Keep `0`, keep PRIV-5 mandatory, and put the "tell your staff" line in the release note |
| Q3 | ⚠ **COMPLIANCE C2 / SEC-12.** Does a setting that removes an employee's correction right need an attributable record of who changed it, for grievance? | Surbhi; counsel if she wants it | SEC-12 | Write the one log line |

### Should know

| # | Question | Who | Why it matters |
|---|---|---|---|
| Q4 | ⚠ **C3.** Does the window bind an **HR Manager raising their own day on the portal**? | Surbhi | One comparison. Binding by path is one rule; exempting by role is two |
| Q5 | Per-tenant `Custom DocPerm`: do employees actually hold `create` on `Attendance Request` on Grace, DTC and PPJ, and does a User Permission pin `employee` to their own record on the Desk path? | `hrms-fullstack-engineer` on **dev only** | How much A2/A5 matter in practice. The shipped JSON says yes; the tenants are not checked |
| Q6 | Grace's hidden 3-a-month Server Script (DevOps OPS-3, carried from Gate 1) | Surbhi with Grace | Two rules in force, one invisible |

### Nice to know

| # | Question | Who |
|---|---|---|
| Q7 | Does `frappe.logger("security")` actually write on our sites? The level is unset in config and `log_refusal` uses `.warning` while 23 `logger("alvoraa")` calls use `.info` (counted this session). **Inference:** warnings are written and infos are not. Settle it by triggering one refusal on a dev site and reading `sites/<site>/logs/security.log` | `hrms-devops-engineer`, one command |
| Q8 | Is `Employee.user_id` unique in ERPNext? | engineer, when a bench is available |

---

## 9. Residual risk

| Risk | Level | Owner | Accepted on |
|---|---|---|---|
| The Desk / REST path stays open if Q1 goes the "two endpoint checks" way. The window is then a convenience, not a control, and the spec must say so in those words | **P1 if unresolved at build** | Surbhi (Q1) | Open, 19 Nov 2026 |
| No record of who changed the setting, or when (SEC-12) | P2 | Surbhi (Q3) | Open, 19 Nov 2026 |
| No record of who was refused — deliberate (PRIV-2). We cannot evidence "the control fired" except by test | P3, accepted by design | this document | 19 Nov 2026 |
| The compliance baseline's DPDP section was verified 24 Aug 2026 and goes stale on 22 Nov 2026. I relied on its correction-right row without re-verifying | P3 | `hrms-security-privacy-engineer` (me) — re-verify at the next slice that touches a right | 19 Nov 2026 |
| Per-tenant Custom DocPerm not checked (Q5) | P3 | engineer on dev | 19 Nov 2026 |
| Fallback to calendar days narrows the window for an employee with no holiday list (SEC-13) | P4, accepted | this document | 19 Nov 2026 |

**Debt labels:** Q1 unresolved is **dangerous debt — escalate now**, because it decides
whether the slice ships a control or a label. SEC-12 is **temporary debt**, removed by
five lines. PRIV-2's missing baseline is an **intentional trade-off**. SEC-13 is an
**acceptable simplification**.

---

## 10. Observability — what must exist before any "0 findings" means anything

Lesson from slice 028, applied here:

1. The setting must be **non-blank** on the site under test. Blank is the default on
   every tenant, so on a fresh site every one of these controls is inert and every test
   passes without exercising anything.
2. The fixture employee's `date_of_joining` must be **older than the boundary**, or the
   joining-day exception never fires.
3. The fixture must have **no overlapping `Attendance Request`**, or Frappe's own
   overlap check throws first and the test proves nothing about the window — the
   `OverlappingShiftAttendanceError` trap from the verify file, in a different costume.
4. Each window test must be **made to fail once** by removing the guard, and the right
   test must fail, before "it passes" is written down.

---

## 11. Subtract pass

**Removed from my own draft before sending:**

- A refusal-event DocType and an exposure metric. Nothing obliges it, nobody asked, and
  it would create a per-person record of denied corrections with no retention answer.
  Replaced by PRIV-2, which forbids it.
- A dedicated "employee window" permission or role check. The existing `set_org_setting`
  guards already bind a new key by construction (§1.4). Only a test was needed.
- A second working-day counter that fails open for employees with no holiday list.
  One counter, SEC-13 names the trade instead.
- A rate limit on request creation. Frappe's overlap check already blocks the real
  replay, and the window shrinks the attack surface rather than widening it (A6).
- A requirement that the employee be shown the setting's raw number. The derived date
  is strictly better and `get_org_setting` stays HR-only.
- A DPIA. The processing is not new, no new data is collected, and the blast radius is
  one person's own day. A DPIA here would be paperwork that makes the next one weigh
  less.

**Not removed:** SEC-3. Without it the slice is a sign on an unlocked door.

---

## Gate 3 — Surbhi's decisions, 19 November 2026

All three compliance flags answered, plus two carried from earlier gates. She said
"go ahead with all your recommendations".

**C1 — the legal question: DECOUPLED from the release, not escalated.**
The setting **ships blank on every tenant**. Blank means no limit, so on release day no
employee anywhere loses anything and there is nothing for counsel to rule on. Counsel is
asked **before the first tenant sets a non-blank value**, when there is a concrete
question ("tenant X wants 7 days") rather than a hypothetical. Both safeguards stay
mandatory meanwhile: HR is never bound (SEC), and **every refusal names HR's route**
(PRIV-5). Noted: `.claude/context/security-compliance-baseline.md` §2 goes stale on
22 Nov 2026, so an opinion sought today would rest on an expiring document.

**C2 — attributability of a setting change: BUILD IT, in this slice.**
`set_org_setting` today writes `frappe.db.set_default` and commits with **no audit record
of any kind** — no Version row, no log line — for any of the six keys. That was tolerable
while no setting removed anyone's rights. This one does. **One `logger("security")`
line, covering all six keys.** No new DocType, no screen. Resolves SEC-12.

**C3 — does the window bind an HR Manager raising their own day? YES. Bind by path.**
One rule: raising your own day on the portal is bound, whoever you are. Rejected:
exempting by role, which means two rules that must agree for ever, and role exemption
lists do not stay at one entry. An HR Manager who is blocked on the portal fixes the day
through the HR route, which is deliberately unbounded — one extra click, not a block.

**Carried decisions, also settled at this gate:**

- **Grace's leftover 3-a-month Server Script: LEAVE IT RUNNING.** Removing it is a
  separate change to a live tenant with no benefit this release. The release note says
  Grace has two rules and the stricter wins (DevOps OPS-18).
- **Other tenants: ASK, do not grep.** Reading other tenants' Server Scripts was refused
  as unauthorised access, and a grep on dev is no evidence about a live site. One
  question to each HR contact. Until answered, every note says **"not checked"** and
  never "all clear" (OPS-19).

**The item she singled out as not to be let slide:** the blank-value trap in
`set_org_setting` (`hr_api.py:3393`). The branch that permits an empty value is written
for one key **by name** — `if key == MANAGER_FILING_WINDOW_KEY and value == ""`. Unless
the new key is added there, **HR can set a limit and never remove it**: blank fails the
numeric validator and the smallest saveable value is `0`, the tightest setting there is.
This belongs in the spec as an acceptance criterion, not in a review comment.
