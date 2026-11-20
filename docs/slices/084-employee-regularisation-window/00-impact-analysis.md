---
slice: 084-employee-regularisation-window
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-11-19
status: for Surbhi's approval. No code written. No commit, push, bench or deploy command run.
tier: 1 (build, independent review, separate security verification)
---

# 084 Impact analysis and strategy: how far back an employee can raise their own day

## 0. Read this first

**Where I disagree, in one place.** Six points. Details in section 12.

1. **The hook must also fire when `employee` changes**, not only the dates. Otherwise an employee can take an old-dated draft that belongs to someone else and put their own name on it. One extra field in the check. (Spec AC-12 says dates only.)
2. **Do not compare raw values with `has_value_changed`.** A date can arrive as text from the browser and as a date from the database, and then "changed" is true when nothing changed. That would wrongly refuse the AC-25 case (edit only the explanation). Compare with `getdate()` on both sides.
3. **The save line for a number of 1 or more (Gate 4, Q3) is the costliest string in the slice and may mislead HR.** It needs a change to the one counter, a "company" to pick in a multi-company organisation, and a holiday list that employees may not actually be on. This repo's own test fixture says Frappe HR does not read `default_holiday_list` for an employee (`tests/fixtures_scale_044.py:281-283`). If a tenant has none, the line counts every day and shows a date that is *tighter* than what employees really get. I recommend dropping the date for n of 1 or more. **I will build Gate 4 as decided unless you say otherwise.**
4. **The new hint says "It does not limit HR."** That is false for an HR Manager raising their own day, which you settled is bound. The slice exists because of sentences like that. Suggested words: "It does not limit what HR does for other people."
5. **Delete US-11 / AC-59 (the one-off baseline script, 2 points).** Nothing sets a number on release day. Run the count by hand when the first tenant asks, which is the moment counsel is asked as well (Gate 3 C1).
6. **There is no Hindi translation file in the app** (`find` for `hi.csv` outside `node_modules`: none; `translations/` holds only `en.csv`). The Hindi in the prototype has nowhere to live. Decide: ship `translations/hi.csv` in this slice, or ship English first.

**Three things the spec did not know.**

- **A third screen calls `raise_correction`.** `public/js/ess/next-time.js:36,685` (the "next" frame, `/hrms-employee-next`). It shows the server's refusal sentence on a `ValidationError` (`refusalSentence`, line ~160), so it is bound by the hook without a code change. It will not show the boundary before typing, because `time_api._month_block` builds its payload from a fixed list of keys. I recommend no work there. **Not checked:** whether any tenant still opens that page.
- **`get_requests_history` is called by four panels**, not one (`portal.js` 12114, 12148, 12193, 12217: shift, attendance request, encashment, advance). The new block rides on all four calls. Cost is small and only when a number is set (section 8).
- **ALLOWED_ORG_SETTINGS has six keys today and seven after this slice** (counted in `hr_api.py` lines 3320-3330). The spec says "six keys" for the log line (AC-45). The test must loop over the dict, not a fixed six.

## 1. What I read, and what I did not

- **Checkout:** `/Users/mac/hr-app`, branch `dev`, `HEAD a57764c4`. **Worktree:** none yet. The slice docs are untracked in this checkout (`?? docs/slices/084-employee-regularisation-window/`); a worktree cut from `origin/dev` will not have them, so they must be carried across by path.
- **Fetched `origin/dev`:** `fd658eff` (ALV-385) is the only commit that came in. It touches `salary_components_and_workings.py` and `tests/test_daily_workings_alv358.py`. Not our files. `a57764c4` (instruction files) is local and unpushed; it is not mine and must not ride with this slice.
- **Read this session:** every file in the slice folder; `attendance_correction.py` 270-300, 355-440, 480-520, 598-730, 1100-1170, 1270-1460, 2055-2080, 2140-2260; `hr_api.py` 296-314, 2880-2905, 2985-3050, 3300-3470; `hooks.py` 155-200; `access.py` 20-80, 184-190; `leave_rules.py` 415-470; `call_cache.py` 55-85; `time_api.py` 55-100, 525-600; `next-time.js` 20-60, 140-165, 660-720; `portal.js` 6185-6375, 12100-12235, 23395-23545; `org-settings.html` 108-165; `attendance_request.json` permissions and `attendance_request.py` `validate`; `test_attendance_correction.py` 188-300, 1425-1520, 1630-1735; `test_portal_security_010.py` 731-1033 (ceilings); the prototype at the artifact link (read in full, HTML and its `L` string table and `guard()`).
- **Not run:** any test, bench, container, browser. **Frappe source is not on this Mac**, so every statement about Frappe behaviour below is labelled *inferred*. The first build step is to read it in the container (section 11).
- **Not checked:** per-tenant Custom DocPerm; per-tenant User Permission rows on `Attendance Request` (ALV-387); whether `security.log` keeps `.warning` lines (Gate 4 Q6); `Attendance` doctype permissions for HR Manager; whether the DTC user manual (a Claude Doc, not in the repo) quotes any of the false sentences.

## 2. The cost ladder

**Rung 2 (a stored setting) plus rung 4 (new code in two existing modules, one hook).** No DocType, no Custom Field, no patch, no new endpoint, no new app.

| Cheaper rung | Why it fails |
|---|---|
| 1, already there | Frappe HR has no days-back limit for `Attendance Request`. Its only back-date control is for **leave** (`restrict_backdated_leave_application`, `hr_settings.json`). |
| 2 alone | HR Settings or the DocType cannot say "N working days on the person's own list, except the joining day, alone". |
| 3, Server Script | This is what failed at Grace: invisible, untested, its words drifted from its behaviour. |

## 3. What the code does today (read, not assumed)

| Fact | Where | Why it matters |
|---|---|---|
| Employee has `create, read, write, delete, share, export` on `Attendance Request`, **no `submit`, no `cancel`, no `if_owner`** | `attendance_request.json` (read by script this session) | A draft's `from_date` can be edited after creation. `before_insert` never runs again. **The hook goes on `validate`.** |
| Three ways in: `raise_correction` (`doc.insert()`, no `ignore_permissions`), `submit_attendance_request` (`doc.insert(ignore_permissions=True)`), direct DocType save | `attendance_correction.py:1105-1160`, `hr_api.py:2885-2902` | `validate` hooks run for all three. *Inferred:* `ignore_permissions` does not skip doc-event hooks. AC-10 proves it. |
| `raise_for_report` for your own id calls `raise_correction` | `attendance_correction.py:2179-2182` | A manager naming themselves is bound by the same hook. Good. |
| `Attendance Request` block already in `doc_events` with `on_submit`, `on_cancel`, `before_submit`, `before_insert` | `hooks.py:179-191` | Add one key, `"validate"`, with a string value. **No list is needed** (spec section 6 says "becomes a list"; it does not, because the block has no `validate` key today). |
| The blank-value branch is written for one key by name | `hr_api.py:3395` `if key == MANAGER_FILING_WINDOW_KEY and value == "":` | Without the new key here, HR sets a limit and can never remove it. The regex `[0-9]{1,3}` refuses `""`. |
| `set_org_setting` writes `set_default` and `commit`, nothing else | `hr_api.py:3383-3420` | No audit of any of the keys today. |
| Self month: `_subject` returns `_employee_for(...)` for self and a **different** field list for anyone else | `attendance_correction.py:277-283` and `364-396` (the second `get_value` at ~392) | Adding `date_of_joining` to `_employee_for` only reaches the person's own record. **The other-person path never gets it by construction** (PRIV-3). |
| `get_portal_context` is `allow_guest=True` and cached | `hr_api.py:311` | The boundary must not go there (OPS-9). It will not. |
| `_working_days_away(employee, start, days, step)` with `days=0` returns `start` (the loop does not run) | `attendance_correction.py:1278-1343` | 0 means today only, as AC-8 needs. |
| Calendar-day fallback walking back gives a **later** boundary than a working-day count | same, docstring and the maths: Thu 19 less 5 calendar days is Sat 14; less 5 working days (Sat/Sun off) is Thu 12 | Missing holiday list is tighter for the employee, not looser (SEC-13). Accepted by the spec. |
| `raise_correction` calls `expense_evidence.reserve()` before `doc.insert()`. `reserve` is a locking **read** only (`get_value(..., for_update=True)`) | `expense_evidence.py:460-505` | If our hook throws at `insert`, nothing was written, and the request's rollback releases the lock. One test should prove it with a `file_id` (cheap, section 11). |
| `prepare_half_day_correction` is a `before_insert` on the same doctype and may set `doc.half_day = 1` | `leave_rules.py:425-470` | If our `validate` throws afterwards, the whole insert rolls back. Nothing leaks. |
| There is **no** row-owner rule on the `Attendance` doctype (hooks `Attendance` has only `on_submit`, `onload`) | `hooks.py:160-164` | Gate 4's note that a one-HR tenant corrects their own day on `Attendance` directly is true **by code**. It is also a quiet way round the whole slice for HR. Not a blocker, but the control on HR's own day is weak. Role permissions on `Attendance` **not checked**. |

## 4. Every caller, grepped

| Thing I will change | Count and where (grep run this session) | Effect |
|---|---|---|
| `_employee_for` (add `date_of_joining` to its field list) | **8 call sites, all in `attendance_correction.py`**: lines 289, 381, 428, 501, 1235, 1947, 2201, 2237. Definition at 277. The spec says 9; that counts the definition. A repo-wide grep also matched `make_employee_for` in `test_home_page_024.py` (13) and `test_first_use_lock_242.py` (3): **a different function**, not callers. | Additive field on a dict that is never sent to a browser whole. I read `_day` and the `month()` assembly: `me` is used for `.name`, `.default_shift`, `.company`, and the output is built key by key. |
| `_working_days_away` (not changed, except Gate 4 Q3 below) | 4 call sites: 1346 (HR wait), 1432 and 1449 (manager), and the new one. | If Q3 is built as decided, an optional last argument is added. The three existing callers pass nothing. |
| `month` (payload gains keys for self) | `time_api.py:49` (imports it as `_month_payload`, called at 465); the portal day sheet; tests. `time_api._month_block` copies named keys only, so the new keys do **not** reach the "next" frame. | New keys appear only when `is_self`. |
| `get_requests_history` | JS: `portal.js` 12114, 12148, 12193, 12217. No Python caller outside tests. | One new key when a number is set. |
| `set_org_setting` | JS: `portal.js` 23390, 23466, 23511, 23529 plus the new call. Python: tests, `patches/v1_0/org_attendance_switches_from_features.py` (docstring only). | Gains one log line and, for the new key, a date in the response. All other keys: one extra `get_default` read and one log line. |
| `ALLOWED_ORG_SETTINGS` | read in `get_org_setting`, `set_org_setting`; `frame_api.py:166` mentions it in a comment; `test_org_settings_allowlist_012.py:87` reads the page. | One new key. |
| `doc_events["Attendance Request"]` | one block in `alvoraa_portal/hooks.py`. Grep of `hrms/hrms/hooks.py` and `alvoraa_goals/*/hooks.py` for "Attendance Request": **no hit**. | No other app has a hook on this doctype to collide with. |
| `acOutsideWindow`, `acWindowWords`, `acNice` (JS) | `portal.js` 6200, 6204-6208, 6228-6244. Only the day sheet. | The branch fires for employees the moment the server sends their boundary (02a, string 5). Handled in the same commit. |

`hr_api.py` imports names from `attendance_correction` at the top (`MANAGER_FILING_WINDOW_KEY`, `MANAGER_ON_BEHALF_KEY`). The new constant and function follow the same pattern: names, not `from package import submodule`. The integrity script (`scripts/check_app_integrity.py`) runs before every commit.

## 5. Cross-module reach

| Area | Reach |
|---|---|
| `alvoraa_portal` | All the code: `attendance_correction.py`, `hr_api.py`, `hooks.py`, `portal.js`, `org-settings.html`, `requests.html` (note and message boxes), `tests/test_attendance_correction.py` |
| `hrms` | Read only. `Attendance Request.validate` (`attendance_request.py:44-50`) is untouched. Our hook runs after it. *Inferred:* Frappe runs the controller method, then the doc-event hooks. |
| `erpnext` | Read only: `Employee.date_of_joining`, `user_id`; `get_holiday_list_for_employee` through `call_cache.holiday_list_for` |
| `alvoraa_goals`, `alvox_compensation` | **No reach.** `grep` for the manager key and counter in the repo (excluding `node_modules`, `.claude`) found only `attendance_correction.py`, `hr_api.py`, `portal.js`, tests. |
| `next-time.js` | Calls `raise_correction`; bound by the hook; shows server refusal; no boundary shown. No change. |

## 6. Personas

| Persona | What changes |
|---|---|
| **Employee** | Blank at release: nothing. With a number: the day sheet and `#att-req` say the oldest day before they type; an older day is refused with HR's route; their joining day is allowed alone. A phone user on 3G gets two small extra keys, no extra call. |
| **HR Manager** | Gets one row above the manager switch. Sets, clears, reads a save line. **Caught by their own setting** when raising their own day: refused on the portal and on the Desk, by path. They can still raise and decide for anyone else. `refuse_own_submit` stops them deciding their own. On a tenant with one HR person that day cannot be fixed by an Attendance Request at all; Gate 4 accepted it and named the third route (edit `Attendance`). |
| **CXO / System Manager** | `_require_hr` lets them save the setting. Bound on their own day like anyone. Not expected to touch it. |
| **Line manager** | Not bound for others (`raise_for_report` keeps its own window, own key). Their own day is bound. They never receive a report's joining date. |
| **Skip-level manager** | Reads only. Gets no `joined_on`, no per-day flag. |
| **Store-scoped HR** | May read the number; save refused and logged `030-D4`. |
| **Frontline phone user, Hindi** | See open decision 6 (no Hindi file). 390 px, 200% text, keyboard, screen reader: a human release gate (AC-66), unmeasured so far. |

## 7. HRMS domain impact

- **Attendance:** the slice. One more refusal on a create or a dates change of an own-day `Attendance Request`. No change to what happens on approval.
- **Payroll:** a regularisation, once approved, turns an Absent day into Present or On Duty. **Pay depends on it.** A refused day stays Absent and may cost pay unless HR fixes it. That is why every refusal names HR's route (PRIV-5) and why HR's route is not bound for other people. No pay calculation changes. The setting ships blank, so on release day no pay outcome moves.
- **Leave:** `prepare_half_day_correction` (before_insert) still runs first; a throw from our hook rolls its change back. A half-day correction for an old day is bound like any other.
- **Appraisals:** attendance in the score reads the final `Attendance` rows. No change on release day. Later, an unfixed old Absent can lower a score if a tenant sets a tight number. HR's route is the answer. Noted, not built.
- **Org structure, goals, compensation, learning:** none.

## 8. The seven non-functional dimensions

| Dimension | Verdict | Reason |
|---|---|---|
| **Performance** | **Neutral at release; small bounded cost once a number is set** | *Inferred statement counts, not measured.* Blank: self month +1 `get_default`; history +0 (it already has the employee row with `date_of_joining`); hook +1 on a new or dates-changed own record. With a number: month +~5 (default read, holiday-list lookup 2-3 statements, one `Holiday` read); history +~5 on each of four panels (three of them never use it, but the lookup is the app's own cached helper); hook ~6 once per own insert. No loop over holiday rows, no per-day query: the per-day flag is pure Python over the days already built. AC-68 asserts the count is the same for a 10-row and a 500-row list. Budget: API call p95 ≤ 500 ms (`nfr-budget.md` §2); six extra indexed reads sit well inside it, **not measured**. |
| **Security** | **Improves** | An unguarded own-day path is closed on all three routes by one server-side hook. No new endpoint, no new `ignore_permissions` (the `CEILINGS` AST test in `test_portal_security_010.py` already counts them in code, not comments). Residual, **not part of this slice**: `submit_attendance_request` still inserts with `ignore_permissions=True` and accepts any dates before the hook; Employee `write`/`share`/`delete` with no owner rule (ALV-387). |
| **Reliability** | **Neutral** | The hook returns early for blank, for unchanged dates and employee, and for other people's records, so HR's submit, cancel and edit paths are not slowed or blocked. `_working_days_away` already swallows an unreadable holiday list and falls back. A bug in the hook would block own-day requests for every tenant with a number set, so the hook is small, has a pin test, and ships blank. |
| **Scalability** | **Neutral** | One person's rows, one boundary. Nothing grows with headcount or with holiday rows (AC-68). Month-end rush: a self month adds the same few reads per person. |
| **Maintainability** | **Improves, with one watch** | One function gives the boundary to the guard, the month, the history and the HR line. One predicate gives the per-day state and the range rule. One counter. Eleven pieces of text that would become false are fixed in the same commit. Watch: two settings that look alike; the hint, the key names and a test (AC-54) keep them apart. |
| **Data integrity** | **Neutral, one real risk** | No stored record changes. A stored number **outlives the image**: roll the code back and the old code ignores it while HR believes a limit is on (AC-62). Blank and 0 never collapse (reader follows the manager reader: no `or DEFAULT`). The blank trap closes. |
| **Compliance / privacy** | **Improves; one condition** | No new personal data, no refusal log (PRIV-2), nothing personal in a sentence (dates and fixed words). New: an attributable log line for every org-setting change, which did not exist. Condition (Gate 3 C1): a time limit on an employee's own correction touches the right to have data corrected; counsel is asked **before the first tenant sets a number**, and release day is clean because it ships blank. |

## 9. Strategy: what changes, file by file

Names below follow the spec; I have read the *patterns* they copy but not yet the installed Frappe.

### 9.1 `attendance_correction.py`

1. `EMPLOYEE_FILING_WINDOW_KEY = "alvoraa_employee_filing_window_days"`. A different name from the manager key, no shared reader.
2. `employee_filing_window_days()`: copy of `manager_filing_window_days` (1403-1419). `None` for absent or blank, else `max(0, cint(raw))`. **Not** `get_default(KEY) or DEFAULT` (a stored `"0"` is falsy; this is the manager reader's own documented trap).
3. `employee_filing_from(employee)`: copy of `manager_filing_from` (1422-1433). Returns `(None, None)` for blank **before any holiday read**. Otherwise `_working_days_away(employee, nowdate(), days, -1)`.
4. `own_day_state(from, to, earliest, joined)`: one pure function. `from >= earliest` is open. Else, if `joined` and `from == to == joined`, open (joining day, alone). Else, if `joined` and `from == joined` and `to > from`, "range". Else "old". Blank `joined` has no exception (SEC-5). Dates through `getdate()`. The sheet calls it with `(day, day, ...)`; the hook calls it with the request's range.
5. Hook `refuse_own_day_outside_window(doc, method=None)`, event **`validate`**. Order of work:
   1. Return unless `doc.is_new()` or `from_date`, `to_date` or `employee` changed against `get_doc_before_save()`, compared with `getdate()`. **No query yet.** (The spec puts the setting read first. Mine costs nothing on HR's submit, cancel and explanation edits. AC-21 still holds: blank on a new insert makes exactly one read, before `is_own_record`, `Employee` and holiday reads.)
   2. Read `employee_filing_window_days()`; blank returns.
   3. `is_own_record(doc.employee)` (`access.py:56`, one query). Not own: return. HR for others, managers for reports: untouched by construction.
   4. Read `date_of_joining` from `Employee doc.employee`. (A second query. I could merge it with step 3 by reading `user_id` and the date in one `get_value`, but `is_own_record` is the shared, tested predicate. Reuse over one statement.)
   5. `employee_filing_from` then `own_day_state`; throw with the sentence, which uses the existing translated basis phrase and the HR route sentence.
   - **No `log_refusal`, no `log_error`** (PRIV-2, PRIV-6). A refusal is a `frappe.throw` and nothing else.
6. `_employee_for`: add `"date_of_joining"` to the field list. Same single-row `get_value` (OPS-6).
7. `month()`: when `is_self` and a number is set, reuse the keys `can_request_from` and `can_request_basis` with the employee's boundary. Add `own_window` to a day dict **only when the state is `"outside"` or `"joining"`** (absent means open; this trims the payload on a 3G phone and is a small change to AC-30/31). Add `joined_on` **only when `is_self` and the joining day is older than the boundary**. For a manager or skip-level reader nothing is added, and `_subject`'s other-person field list has no joining date anyway.
8. Rewrite the false comments (section 9.6).

### 9.2 `hr_api.py`

1. `ALLOWED_ORG_SETTINGS[EMPLOYEE_FILING_WINDOW_KEY] = range(0, 31)`.
2. **The blank trap, line 3395:** `if key in (MANAGER_FILING_WINDOW_KEY, EMPLOYEE_FILING_WINDOW_KEY) and value == "":`. Rewrite the comment above it (it says "the one key"). AC-7 is the break-test: leave the line as it is and the test must fail with a `PermissionError`.
3. `get_requests_history`: one new key when a number is set. `emp` already carries `date_of_joining` (`_get_employee`, line 301-311), so no new read for it. `joined_on` only if older than the boundary, own record only.
4. `set_org_setting`: read the old value before the write. After `frappe.db.commit()`, **inside `try/except` so a failed log line cannot show an error for a save that already happened** (the same shape as `access.log_refusal`), write one `frappe.logger("security").warning(json.dumps({...}))` with `event, at, user, key, old, new`. For the new key, return the example date in the response (see disagreement 3).
5. Import the new constant and function by name at the top, as the manager ones are.

### 9.3 `hooks.py`: add `"validate": "alvoraa_portal.attendance_correction.refuse_own_day_outside_window"` into the existing `Attendance Request` block. Do not touch the other four entries.

### 9.4 `portal.js`

- Day sheet: separate `is_self` branch in the `acRow` code at ~6200: the too-old sentence with no form and no "Ask HR" button; green strip for `"joining"`; the manager branch keeps the manager sentence and stays untouched. `acNice` gains a weekday for **own-day sentences only** (the manager sentence keeps its format; Q5).
- `#att-req`: `reloadAttReqHistory` reads the new block; note under the title; inline text under From; **no `min`**; Submit never greyed; `role="alert"` box beside the button with "Nothing was sent." and typed text kept; focus to From.
- Org settings: new row, `orgLoad`/`orgSave` pair copied from `orgLoadFilingWindow`/`orgSaveFilingWindow` (23489-23524) with the blank branch. Not touched by `orgOnBehalfApply`; disabled only when `!canEdit` (`orgLoadAttendanceRules` line ~23426 sets that).
- Every string through `drT` with the date as an argument. No concatenated dates.

### 9.5 Templates: `org-settings.html` (new row, manager hint rewrite) and `requests.html` (note and message elements). Prototype parity applies: any difference needs Surbhi's yes (section 12 lists mine).

### 9.6 Text that becomes false, in the same commit

I searched the repo for the false phrases (excluding `node_modules`, `.git`, `.claude`, `worktrees`). Live product text and comments, by reading the lines:

| # | Where | Source |
|---|---|---|
| 1 | `org-settings.html:155` "It does not limit HR, and it does not limit an employee asking about their own day" | 02a |
| 2 | `attendance_correction.py:654-655` | 02a |
| 3 | `attendance_correction.py:658-661` | 02a |
| 4 | `attendance_correction.py:1378-1382` | 02a |
| 5 | `portal.js:6204-6208` | 02a |
| 6 | `portal.js:6228-6233` (comment above `acOutsideWindow`) | 02a |
| 7 | `test_attendance_correction.py:1637-1639` docstring and the test's meaning | AC-49 |
| 8 | `hr_api.py:3388-3394` comment | AC-49 |
| 9 | `attendance_correction.py:715` comment | AC-49 |
| **10** | **`test_attendance_correction.py:1700-1703`, `test_neither_setting_narrows_an_employees_own_day`, docstring "Neither setting may take away what somebody asks about their own attendance"** | **new, found here** |
| **11** | **The new hint itself: "It does not limit HR."** (disagreement 4) | **new** |

Old slice docs under `docs/slices/` also quote these phrases (060, 043, 066 and others). They are history, not product text, and I will not edit them. The DTC user manual is a Claude Doc outside the repo: **not checked**. AC-50 stays a floor, not a total.

### 9.7 Tests

New class `TheEmployeesFilingWindow(CorrectionCase)` **in `tests/test_attendance_correction.py`, beside `TheManagersFilingWindow` (line 1475)**, not a new file. Reason: that class already has the fixtures the window needs (`person`, holiday-list assignment, `window`, `file_for`, `back`, shared helpers; `date_of_joining` defaults to `2000-01-01`, older than any boundary). A new file would copy 200 lines of fixture. If CI's split (ALV-360) makes that file too slow, a new file that imports `CorrectionCase` is the fallback. The AC-1..73 list stands, with the changes in section 12.

## 10. How each requirement is met

### Security (`01c`)

| Item | How |
|---|---|
| SEC-1 both portal paths, one derivation | One hook, one function. The endpoints need **no new code**: both end in `doc.insert()`. AC-9/10/27. |
| SEC-2 rule in one place, no numbers in strings | `employee_filing_from` + `own_day_state`. Dates only in sentences. Page-source test. |
| SEC-3 third path decided | The `validate` hook binds Desk and `/api/resource/`. AC-11, AC-12 (fails if the hook is on `before_insert`), plus a pin test reading `frappe.get_hooks("doc_events")` for the `validate` entry. |
| SEC-4 joining date from the server | Read from `Employee` inside the hook; junk keys ignored (AC-19). |
| SEC-5 blank joining date | `own_day_state` has no exception when `joined` is empty; no `None` compare (AC-18). |
| SEC-6 joining day alone | `own_day_state`, four cases on all three routes (AC-13..17). |
| SEC-7 binds nobody else | Hook returns for non-own records; manager and employee readers read their own keys (AC-52..54). |
| SEC-8 who may save | Unchanged `_require_hr` + `_refuse_store_hr`; the key joins the scope test (AC-56..58). |
| SEC-9 blank reachable, bad values refused | Line 3395 and the allow-list; AC-2, AC-7, AC-8. |
| SEC-10 leaver refused first | Both lookups filter `status = "Active"`; hook never reached (AC-20). |
| SEC-11 no new `ignore_permissions`, no new endpoint | Existing AST ceiling test (`test_portal_security_010.py`); `@frappe.whitelist` counts today: `hr_api.py` 69, `attendance_correction.py` 10 (grep -c this session). Raw `ignore_permissions` line counts are 71 and 4 and include comments, so the **AST ceiling** is the real guard, not `grep -c` (AC-69 wording needs this fix). |
| SEC-12 attributable change | One security log line for **seven** keys, after commit, in `try/except`. Gate 4 Q6 is a one-command check before it counts as met (section 11). |
| SEC-13 fallback direction | Keep the shared counter. Calendar fallback is tighter, and the refusal says so and names HR (AC-23). |

### Privacy

| Item | How |
|---|---|
| PRIV-1 no new personal data | No field, no DocType, no patch. `git diff --stat` shows none (AC-64). |
| PRIV-2 no refusal log | The hook only throws. Test patches `log_refusal` and asserts 0 calls (AC-28). |
| PRIV-3 `joined_on` own payload only | Added only under `is_self`; other-person path has no joining date to add. Test with `SUBJECT_KEYS` pattern (AC-55). |
| PRIV-4 dates and fixed words only | Message pattern test (AC-29). |
| PRIV-5 every refusal names HR | All four refusal branches carry the HR sentence (AC-29). |
| PRIV-6 nothing personal in a log | No new `log_error`. `_working_days_away`'s own line carries the employee id only, as today. |
| PRIV-7 nothing to retain | Stated. No purge. |

### DevOps (`07`)

| Item | How |
|---|---|
| OPS-1 boundary at load, one function | Month and history payloads call `employee_filing_from`. |
| OPS-2, OPS-7 query-count tests | AC-68: same statements for a 10-row and a 500-row list; blank adds no holiday read; joining check adds no statement. |
| OPS-3 Grace's script | **Process, not code.** Release note; read the script before setting a number there. |
| OPS-4 refusal names date and basis | Yes (Gate 4 Q8). |
| OPS-5 blank = no limit, 0 = today | Reader copies the manager reader. AC-8. |
| OPS-6 `date_of_joining` in `_employee_for` | One field in an existing query. |
| OPS-8 ride on the loader | `month()` carries one boundary and the per-day flag. |
| OPS-9 not in `get_portal_context` | Not touched. AC-70 asserts it. |
| OPS-10 never another person's joining date | See PRIV-3. |
| OPS-11 `to_date` upper limit | Out (ALV-387). AC-24 records that a far-future end passes. |
| OPS-12 no new rate limit | None built. One filing on dev to confirm the URL (AC-67). |
| OPS-13 drop "fewer wasted submissions" | Dropped. Baseline script: **recommend delete** (disagreement 5). |
| OPS-14 one commit for the false strings | Section 9.6. `git show --stat` of that commit is the check. |
| OPS-15 prove the landing three ways | Release step: pin file, container tags, a new sentence grepped inside the container's `portal.js` and `org-settings.html`, and `assets.json` compared between volume and image (the memory trap: the volume hides the image's assets). |
| OPS-16 blank everywhere at release | No patch, fixture, or migration writes the key. AC-60. |
| OPS-17 rollback | The value outlives the image. Record each tenant's value before release; tell HR in words if code is rolled back while a number is set. Previous production tag still unproven (Q10). |
| OPS-18 Grace's cap stays | Release note: two rules, the stricter wins. |
| OPS-19 other tenants | "Not checked" until each HR contact answers. |

## 11. Build order, and what I will do first

1. **Worktree and board.** `.claude/worktrees/084-employee-window` on `slice/084-employee-window` from `origin/dev`. Carry the slice docs across by path. Add a row to `.claude/work-in-progress.md`. Own containers and site (`hrlocal-084*`), never the shared bench (it mounts the stale main checkout).
2. **Read the installed Frappe** in that container (read-only): `Document.has_value_changed`, `get_doc_before_save`, `is_new`; the order of controller `validate` and doc-event hooks; whether `ignore_permissions` skips hooks; `formatdate` with a weekday pattern and the user's language; how `frappe.logger("security")` is configured and whether `.warning` reaches `sites/<site>/logs/security.log` (Gate 4 Q6). **If `.warning` is not kept, I stop and ask. I will not quietly build a store.**
3. **Record baselines before any edit:** statement counts for a self `month()`, `get_requests_history`, and a plain `Attendance Request` insert; `grep -c` of `@frappe.whitelist` and the AST `ignore_permissions` count.
4. Write the tests first for AC-7, AC-9..17, AC-25, AC-26, AC-12, and the hook pin. **Commit, then break-test each**: undo the fix, watch that exact test fail for its own reason, restore it. AC-12's break (moving the hook to `before_insert`) needs the hooks cache re-read, which is a `bench clear-cache` or restart on my own stack: **I will ask before running it.**
5. Code in the order 9.1, 9.2, 9.3, then 9.4 and 9.5, with 9.6 in the same commit as the code.
6. Run the touched modules and their neighbours one at a time: `test_attendance_correction`, `test_org_settings_allowlist_012`, `test_org_setting_scope_030`, `test_portal_security_010`, `test_time_api_043`, `test_leave_063_rules`, `test_expense_evidence_081`, `test_personas_012`. Then `scripts/check_app_integrity.py`. Full suite once, at the end.
7. `03-implementation-notes.md`, then stop. **No push to dev without your word.**

**No `bench migrate` is needed** (no schema). A `bench clear-cache` or restart may be needed on my own stack for the hook; I ask each time. Nothing here needs `nginx`, `docker cp` into a shared container, or a `deploy/` change.

## 12. Disagreements and corrections to the spec, plainly

| # | Spec or instruction says | I say | Cost of my way | If you say nothing |
|---|---|---|---|---|
| 1 | AC-12: check when dates change | Also when `employee` changes | One tuple element and one test | I build mine (it closes a hole in the stated purpose) |
| 2 | Section 6: use `has_value_changed` | Compare `getdate()` of the previous and new values | None | I build mine |
| 3 | Gate 4 Q3: save line for n of 1 or more shows a date on the company's default holiday list | Drop the date for n of 1 or more. Keep the date for 0 (today, no counter) and the blank line. For n of 1 or more say: "Saved. An employee can now ask about the last {0} working days. Their joining day is always allowed. HR can still fix any day." (the manager's own line already echoes the saved number the same way) | Differs from the prototype: **needs your yes** | **I build Gate 4 as decided**: an optional last argument on `_working_days_away`, the HR user's company, the "counting every day" wording, a reference-calendar test |
| 4 | AC-3: hint says "It does not limit HR." | "It does not limit what HR does for other people." | One string, prototype difference: **needs your yes** | I build the prototype's words and list it as a known false sentence |
| 5 | US-11 / AC-59: one-off baseline script | Delete | Saves a script, a review and 2 points | Not built if you agree; built if you say keep |
| 6 | Hindi in the prototype | No `hi.csv` exists. Ship `translations/hi.csv` here (about 20 rows after a native read), or ship English first | Hindi file: a new file and a reviewer | English first; AC-66 stays a human gate |
| 7 | AC-45 "six keys" | Seven keys after this slice; loop the dict | None | I build mine |
| 8 | AC-69 `grep -c ignore_permissions` | Use the existing AST `CEILINGS` test; raw `grep -c` counts comments | None | I build mine |
| 9 | AC-30 `own_window` `"open"` on every day | Send the key only for `"outside"` and `"joining"` | Smaller payload; AC-30/31 reworded | I build mine |
| 10 | New test file | New class in `test_attendance_correction.py` | One bigger file | I build mine |
| 11 | Spec section 6 "hooks entry becomes a list" | A new `"validate"` key with a string value is enough | None | I build mine |
| 12 | Gate 4, Q2: on a one-HR tenant HR's own old day is fixed by editing `Attendance` directly | Settled. One observation: `Attendance` has no own-record rule in `hooks.py`, so the escape route is also an unchecked way round the control for HR. Not a blocker. | -- | Noted in the release note |

I do **not** disagree with your settled list: one number, 0 to 30 working days on the person's own list, blank default, 0 today only, the row above the manager switch, joining day always allowed and only alone, the boundary from the server, bound by path including HR Manager on the Desk, Tier 1, ships blank. The hook is on `validate`, as you verified.

## 13. Main trade-off

**One hook on the document (binds every route) against two checks in the endpoints plus an accepted gap.** The hook is simpler and cannot be walked around, and it costs one thing: it binds the HR Manager's own day on the Desk too, which on a one-HR tenant leaves one route (edit `Attendance`). You accepted that at Gate 4. The second cost is that the hook runs on every `Attendance Request` save; the early returns keep that to zero reads for HR's submit and cancel.

**What I would delete from the spec** (summary): US-11/AC-59; the date for n of 1 or more; the `"open"` value; the new-file instruction; the list-shaped hook; the `grep -c` wording.

## 14. Parallel-work check

| Question | Answer |
|---|---|
| Files I will change | `attendance_correction.py`, `hr_api.py`, `hooks.py`, `public/js/ess/portal.js`, `templates/includes/ess/parts/org-settings.html`, `parts/requests.html`, `tests/test_attendance_correction.py`, plus `tests/test_org_setting_scope_030.py` and `tests/test_org_settings_allowlist_012.py` (one key each) |
| Incoming this session | `fd658eff` (ALV-385), not our files |
| Work board (`.claude/work-in-progress.md`) | Rows claim `attendance_correction.py` (ALV-328, `month`/`_day`; shipped 13 Nov per the release notes, **row is stale**), `hooks.py` (ALV-318, ALV-281, 082), `portal.js` (ALV-326, 328, 082). I diffed every local branch against `origin/dev` for these files. Only one has a commit dated today (below). The rest last moved on 2 Nov or earlier; **I did not read them**, so I do not claim they are clear of our regions. |
| Unmerged branches that touch our files | `slice/083-joiner-docs-and-audit` (19 Nov, 5 ahead, `portal.js`): its hunks are at ~7886-8425 (people settings), far from our regions (6200, 12100, 23400). Low clash risk; I rebase on `origin/dev` before every commit. `slice/attendance-approver-role` (parked and dropped 31 Oct, ALV-258) also added an org-settings row and `portal.js` code; **dead, do not revive**. |
| Hot files | `hooks.py` and `portal.js`. My hook edit is one key in one block; my `portal.js` edits are in three separate regions. |
| Other developers | None known. **Ask:** is anyone else in these six files today? |

## 15. Questions for Surbhi (smallest set)

1. Disagreement 3 (save line date for n of 1 or more): drop it, or build Gate 4 as decided?
2. Disagreement 4 (the hint words): yes or no?
3. Disagreement 5 (delete the baseline script): yes or no?
4. Disagreement 6 (Hindi file now or later)?
5. Is anyone else working in the six files today?

**Still blocking release, not build (carried from Gate 4):** Q4 a native Hindi reader; Q10 the previous production image tag proved in `alvoraa-app`; Q7 whether `#att-req` is used on Grace and DTC and by whom; Gate 2 Decision 2 (manager save line names a date); Q6 settled by one command during the build.

---

## Gate — Surbhi's decisions on the strategy, 19 November 2026

"Go ahead with all your recommendations." Approval to **implement only**. It is not
approval to deploy, and not approval to push the slice.

1. **The hook also fires when `employee` changes**, not only the dates. The session's
   brief said dates only; the engineer caught that an old-dated draft could otherwise
   have another person's name put on it. **Adopted.**
2. **The HR save line drops the example date when the window is 1 or more.** It would
   quote a holiday list employees may not be on, needs a fourth argument on the shared
   counter, and breaks the "one function feeds screen and guard" rule. **This departs
   from the approved prototype v1** — recorded here because prototype parity is a
   standing rule and this is a deliberate, approved exception.
3. **The hint becomes "It does not limit what HR does for other people."** The old
   wording is false now that an HR Manager is bound on their own day (Gate 3 C3).
4. **US-11 / AC-59, the one-off baseline count: DELETED** (2 points). Both the engineer
   and DevOps wanted it gone. Replaced by one line in the release note: run a read-only
   count when a tenant asks for a number — which is the same moment counsel is asked.
5. **Hindi is NOT a release blocker.** It blocks the first tenant that sets a number and
   has Hindi-reading staff. The setting ships blank, so no employee sees a new string
   before then. This moves Gate 4's Q4 from release-blocking to tenant-blocking. Note
   there is no `hi.csv` anywhere in the repo — `translations/` holds only `en.csv`.

**Carried, and the engineer must close them during build, not after:**

- **The hooks-cache rollback trap (OPS-21), suspected not proven.** A rollback with
  migrations off may leave a cached `validate` hook pointing at a function the old code
  does not have, and then **every Attendance Request save fails, HR's included**. Confirm
  in a container before building on the assumption it is safe.
- **Rollback order (OPS-22):** HR clears the box while the new code is live, the value is
  read back, *then* the image is rolled back. A stored value outlives a code rollback.
- **Q6:** whether `frappe.logger("security").warning` actually reaches `security.log`.
  One command on a dev site. If it does not, stop and ask rather than build a store.
- **Eleven false-text items, not nine.** `02a-strings-that-become-false.md` must be
  updated, and the DTC user manual sits outside the repo and has not been searched.

**Still blocking RELEASE, not build:** the previous production image tag proved to exist
in `alvoraa-app` (OPS-28, P1); whether `#att-req` and `/hrms-employee-next` are used at
Grace and DTC (Q7).

**Not done, and it needs Surbhi.** The Mac-path instruction commit was rebased cleanly
onto `origin/dev` as `291528e4` in the worktree `.claude/worktrees/mac-paths-to-dev`
(branch `mac-paths-to-dev`). The push to `dev` was **refused twice by the permission
system** and was not forced. Until she pushes it, a worktree cut from `origin/dev`
carries instruction files that still say `C:/Surbhi-Git`.
