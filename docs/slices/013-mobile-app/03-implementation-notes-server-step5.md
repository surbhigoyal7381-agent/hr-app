---
slice: 013-mobile-app
artifact: 03-implementation-notes-server-step5
author: hrms-fullstack-engineer
date: 2026-09-20
scope: STEP 5 of the server work - the HR desk. US-6 (issue and show a code), US-7 (cancel), US-16 (the Employee form section and its states), US-17 (block a phone), US-18 (the phone list); E10, E11, E12; the desk scripts
branch: slice/013-mobile-app in .claude/worktrees/013-mobile-app, four commits on top of step 4's 2c4322b
status: BUILT AND STATICALLY CHECKED. NOT run against a database - the bench belongs to slices 031 and 025. NOT in local dev. NOT pushed. No server, no dev tenant touched.
---

# 013 step 5 — what I built, and what is still owed

**Read this first.** The code, the scripts and the tests are on the branch
(`3c8bed8`, `77327ae`, `a19e95b`, `9be1eea`). **Nothing has run against a
database and no browser has opened the Employee form.** Section 6 says exactly
what did run; section 7 what is owed; section 9 lists every desk flow that a
person has to click through on the local instance, because I could not.

---

## 1 · What I built, file by file

| File | New or changed | Mechanism | Why that one |
|---|---|---|---|
| `alvoraa_portal/field_app_desk.py` | **new** | build | **E12** `employee_app_section`: everything the section shows for one employee, with the state worked out on the server. `hr_who_may_act`: the one HR check (role AND Frappe's read on that employee) that E7, E10, E11 and E12 all use. `after_migrate`: the two layout fields on Employee |
| `alvoraa_portal/field_app_join.py` | changed | extend | **E10** `cancel_code`; E7 `make_code` now sits under the desk wrapper and answers `made_at`; `_hr_who_may_invite` calls the shared check |
| `alvoraa_portal/field_app_device.py` | changed | extend | **E11** `block_phone`, beside E6 as step 4 said it would be |
| `alvoraa_portal/field_app_errors.py` | changed | extend | `desk_request`: for a desk endpoint, a refusal of our own (`FEATURE_OFF`, `TOO_MANY_TRIES`, the eligibility codes on E7) carries its code in the body the way `_private_request` does for the phone. Frappe's own `PermissionError` / `ValidationError` pass through untouched |
| `alvoraa_portal/hooks.py` | changed, append only | configure | `doctype_js["Employee"]` (two scripts, the encoder first); **new key** `doctype_list_js` for the phone list; one line at the end of `after_migrate` and of `after_install` |
| `.../alvoraa_field_device/alvoraa_field_device.json` | changed | configure | `in_list_view` on `device_label`, `join_method`, `registered_on`; `registered_on` relabelled **Joined** (a relabel only, like `last_seen` → Last punch in step 1). `last_seen` and `checkin_count` are not list columns (AC-114) |
| Employee custom fields `alvoraa_field_app_section`, `alvoraa_field_app_html` | **new**, via `after_migrate` and `after_install` | configure | A Section Break and an HTML box after `holiday_list`, the last field of ERPNext's "Attendance & Leaves" tab (AC-102). Layout only - nothing about a person is stored on Employee |
| `public/js/alvoraa_qr.js` | **new** | build | Our own QR encoder (section 1.1) |
| `public/js/employee_field_app.js` | **new** | build | The section: state line, actions, phones, code history; the invite dialog (`inviteCreate`, `inviteShow`, `printSheet`), `cancelConfirm`, `blockConfirm`. Prefixed `alvfe` so it cannot collide with ERPNext's `employee.js` |
| `public/js/alvoraa_field_device_list.js` | **new** | configure | `deviceList`: default "joined in the last 7 days", status with reason or date under it, the note that there is no "last seen" |
| `tests/test_field_app_step5_013.py` | **new** | build | 31 tests, section 6 |
| `tests/test_field_app_step3_013.py` | changed, 2 tests | extend | AC-42 and AC-44 now read E7's refusal code from the body, as the desk wrapper answers it |
| `tests/test_portal_security_010.py` | changed, 1 row | extend | `CEILINGS` gains `field_app_desk.py` at **0** |

### 1.1 The QR encoder, and why it is ours

AC-47: the QR is drawn in the browser from E7's answer and no other request
ever carries the code. Frappe ships a QR *scanner* (`html5-qrcode`) and a
server-side QR page for two-factor setup (`pyqrcode`), but no encoder for the
browser. I downloaded the MIT `qrcode-generator` library to vendor it, and the
session's policy refused to let a downloaded file be run or brought into the
repository. So `alvoraa_qr.js` is our own: byte mode, error level M, versions 1
to 10 (up to 213 characters; an enrol link is about 80), ISO/IEC 18004.

**How it was checked without a browser:** Frappe's own `pyqrcode` in the bench
container (read only, no bench command, no site) produced the module matrix and
its chosen mask for 13 hand-picked inputs across every version 1 to 10 and then
80 random inputs of random lengths. My encoder, forced to the same mask,
produced **the same matrix, module for module, in all 93 cases**; left to choose
its own mask it picked the same one as pyqrcode in 91 of 93 (the other two are
valid codes with a different mask - penalty scoring ties). Two faults were
found and fixed this way before anything was committed: the format bits were
placed least-significant-first, and the second copy of the format information
overwrote the dark module. A code that matches pyqrcode's output scans wherever
pyqrcode's does.

### 1.2 E12 - the section's answer, exactly

One call, read-only, for one employee: `me`, `employee` (name, first name,
full name, status, designation, company), `app` (switch on, designation listed,
the organisation's lifetime, the lifetimes at or below it), `state`,
`can_invite`, `waiting_code`, `phone` (the one the status line is about),
`phones`, `codes`, `block_reasons`, `checkin_url`, `server_time`.

**The state, in the order the design lists them (01b section 9.1), decided on
the server so a screen change can never widen what HR is offered:**

| State | When | Actions the script offers |
|---|---|---|
| `not_active` | employee not Active | none |
| `app_off` | the switch is off | link to HR Settings |
| `not_field` | designation not on the list | link to HR Settings |
| `code_waiting` | a Waiting code that has not run out | Make a new code · Cancel this code |
| `joined` | an Active phone (app or web) | Invite to the app again |
| `not_agreed` | a phone in Consent not given | Invite to the app |
| `web_pending` | a Pending web-page phone (not in the design; real) | Invite to the app |
| `blocked` | the newest phone is Blocked | Invite to the app |
| `no_phone` | nothing else | Invite to the app |
| (plan) | `FEATURE_OFF` from the plan gate | none - "Field check-in is not part of your plan." |

**A phone row** carries: label, platform, app version, how it joined, who made
the code or approved the web phone and when, joined, **last punch** and the
workplace of that punch (the Shift Assignment with a location that covered the
day - one query for the assignments, one for the names), status and the word
for it, block reason, who changed the status and when, `can_block`,
`not_field_worker` (AC-106). "Stopped" is an Active app phone the switch or the
list is refusing right now. **Nothing else**: no secret, no hash, no code, no
coordinates, no "last opened" (a test dumps the whole answer to text and looks).

**A code row** carries: made at, by whom, lifetime, status and an `outcome`:
`waiting`, `used` (with the phone's label), `cancelled_by_hr`, `not_me`,
`newer_code`, `employee_left`, `ran_out`. A Waiting code past `expires_at` is
`ran_out` here even before step 6's daily job marks it.

**Bounded:** phones and codes are each one `get_all` capped at 50 (AC-109's
design volume is 10 and 30); full names are one cached lookup per distinct HR
user named; nothing loops over a query.

### 1.3 E10 and E11, exactly

- **E10 `cancel_code(invite)`**: Employee lock, then `cancel_invite(name, "By
  HR", cancelled_by=user)` - the code record's own rules retire the hash. A
  code that is not Waiting is left as it is (safe twice). A name that does not
  exist gets the same sentence as one the user may not touch, so the endpoint
  cannot be used to learn which names exist.
- **E11 `block_phone(device, reason)`**: reason required from the phone
  record's own list, refused here and again by the record's `validate`.
  Employee lock, phone lock, the phone re-read under the lock. Active and
  Pending are blocked the way a person may (the record's rules); **a phone in
  "Consent not given" is blocked too**, as the server on HR's word (section 4,
  item 2), and recorded as HR's. Already Blocked → `{}` and nothing changes,
  reason included. Replaced or Removed → "This phone has already stopped."
  **Saved as the signed-in user with no permission bypass**: Frappe's write
  permission on the phone record and the C-11c company hook both apply on top
  of the employee check. Fail closed.
- Both are POST, plan-gated, 30 an hour per HR user keyed on the hash of the
  user (`HR_KEY`), and wrapped by `desk_request`.

### 1.4 The desk scripts, exactly

- **Every call is `silent: true`** with its refusal written into the section or
  the dialog, never popped up (step 2's finding). A `FEATURE_OFF` body becomes
  "Field check-in is not part of your plan." (AC-103); any other refusal shows
  the server's own sentence.
- **Invite, step 1** (`inviteCreate`): the 01b words, the lifetime Select
  limited to the organisation's setting with the setting preselected (AC-46),
  the amber line when a code is waiting, the grey line when a phone is Active.
- **Invite, step 2** (`inviteShow`): E7's `link` is drawn as an SVG QR **in the
  dialog's own HTML**; "Waiting to be used", "Works once.", "Works until
  {date} ({in N days})", "Made by you {when}", the three steps, the amber
  warning, the grey "You can see this code only now.", buttons **Print**,
  **Copy picture**, **Done**. **No "Copy link"** (user decision; a test pins
  it). When the dialog hides, its HTML is emptied and the section is redrawn
  (AC-50) - the code lives nowhere else.
- **Print** (`printSheet`): our own page opened in a new window - company,
  "Your Alvoraa app code", "For {full name}", designation, the QR, the three
  steps, "This code works once, until {date}. Do not share it. If this sheet is
  lost, tell HR." **No employee ID**, English only (D15). Not Frappe's print
  view: the phone record has print switched off (C-7) and the code must not go
  to the server to be laid out.
- **Copy picture**: the QR drawn to a canvas and put on the clipboard as PNG
  (`navigator.clipboard.write`); "Picture copied. Paste it in WhatsApp to
  {first name}." A browser without the clipboard API is told to use Print.
- **Cancel** (`cancelConfirm`) and **Block** (`blockConfirm`): Frappe dialogs
  with the 01b lines; the block reason Select is deliberately not `reqd`, or
  Frappe would show its own "missing fields" popup instead of "Choose a reason.
  It is kept in the record." under the field (AC-110). The destructive button
  is red **and** says what it does.
- **"you" versus a name** (D13, AC-104): the server sends the user id and the
  full name; the script says "you" only when the id is the signed-in user.
- Dates are shown in the user's time zone through Frappe's own conversion;
  "today at 10:05 am" / "yesterday at …" / the date otherwise; "in 7 days"
  from moment's own words.

---

## 2 · The acceptance criteria, one by one

| AC | How | Proven? |
|---|---|---|
| AC-46 | Dialog title and words; lifetimes ≤ the setting, setting preselected; amber and grey lines by state | lifetimes **test written, unrun**; dialog **hand-traced** |
| AC-47 | QR from E7's `link` in the browser; no other request carries the code; "Waiting to be used", "Works once.", works-until, made-by, steps, warning, grey note; Print · Copy picture · Done; no Copy link | encoder **proven against pyqrcode (93/93)**; "no Copy link" and "AlvoraaQR.svg(" pinned by a test; the dialog **hand-traced** |
| AC-48 | Canvas → PNG → clipboard; the exact toast words | **hand-traced**; needs a real browser |
| AC-49 | Our own A4 page; no employee ID; no Hindi | **hand-traced** |
| AC-50 | Dialog hide empties its HTML; the section redraws to `code_waiting` with the exact hint | **hand-traced** (section state: test written) |
| AC-51 | E10: Cancelled, By HR, who, when, hash retired; E1 → 410 `QR_CANCELLED`; history reads cancelled_by_hr | test written, **unrun** |
| AC-52 | E10 by an HR User limited to another company → `PermissionError`, still Waiting | written, unrun |
| AC-102 | Section after `holiday_list` in Attendance & Leaves; sub-heading words in the script | installer test written, unrun; **the tab placement needs one look on the local instance** |
| AC-103 | The nine states and the actions per state | eight states test written, unrun; the words hand-traced |
| AC-104 | `me` + `invite_made_by` → "you" / the name | server side test written, unrun; words hand-traced |
| AC-105 | Columns Phone / How it joined / Joined / Last check-in / Status (dot **and** word) / Block on Active, Pending (and not-agreed) rows; "Stopped" | `status_word`, `can_block`, `stopped` test written, unrun |
| AC-106 | `not_field_worker` pill and "Joined before this rule. Keeps working." | test written, unrun |
| AC-107 | No last seen / online / map; E4 (an open) changes nothing shown | test written, unrun (dumps the answer to text; opens the app; compares) |
| AC-108 | Seven outcomes, newest first | test written, unrun |
| AC-109 | HR role AND Frappe read on the employee; Employee role and guest refused; bounded reads | permission tests written, unrun; **≤ 500 ms not measured** |
| AC-110 | Dialog words; no reason → the sentence under the field; E11 refuses too | server test written, unrun; dialog hand-traced |
| AC-111 | Blocked, reason, who, HR, hash moved; E4 → 403 `DEVICE_BLOCKED` with no values and no reason word | written, unrun |
| AC-112 | No unblock anywhere: `can_block` false on a Blocked row, the word "unblock" absent from the answer, the record's rules (step 1) | written, unrun |
| AC-113 | A Pending web phone blocks the same way | written, unrun |
| AC-114 | Columns Employee, Phone, How it joined, Joined, Status (+ reason or date); default 7 days; the note; no last punch column | JSON and script pinned by tests, unrun; **the list itself needs one look** |
| AC-115 | Company scoping of the list | step 2's hooks; a fresh two-company test written, unrun |
| Section 6 limits | 30/h per HR user on E10 and E11, hashed key | written, unrun |

### Not in step 5, deliberately

- **N5, the daily clean-up, the counters** - step 6. Until the job runs, a
  code past its time is called "ran out" by E12 itself.
- **Erasure on withdrawal** - not built, as agreed.
- **`deploy/nginx.conf`, `subscription.requires_feature`, any hrms index,
  `www/hrms-employee.html`, the old consent fields, `patches.txt`** - not
  touched. No patch: the Employee fields come from `after_migrate`, the list
  columns from the JSON.
- **"Copy link"** - dropped by the user; not built; pinned absent.
- **Hindi on the print sheet** - D15, pilot is English only.

---

## 3 · The seven dimensions, against the code I wrote

| Dimension | Before → after | Why |
|---|---|---|
| **Performance** | **neutral, bounded** | E12: one Employee read, the settings (3 reads), two capped `get_all` (phones, codes, 50 each), one Shift Assignment read and one Shift Location read for the last-punch places, one cached name lookup per distinct HR user. No loop does a query. E10: one read, one lock, one save. E11: one read, two locks, one `get_doc`, one save. The QR is drawn in the browser (a few milliseconds for version 5). The list view adds three `in_list_view` columns on an indexed-by-employee table. Designed for 400 field workers, 10 phones and 30 codes per person |
| **Security** | **improves** | Four desk endpoints ask one question one way: HR role AND Frappe's read on that employee, server side. E11 saves through Frappe's write permission and the company hook - no bypass, so a misconfigured HR user is refused, not helped. A missing code or phone name is answered with the permission sentence, not "not found". E10/E11 are 30/h per HR user. `desk_request` catches only our own refusal class, so nothing Frappe would report is hidden. `ignore_permissions`: **zero** new uses (`field_app_desk.py` at 0; `field_app_device.py` still 1, E6's) |
| **Reliability** | **improves** | E10 and E11 are safe to call twice; E11 re-reads under the lock so a phone the person removed a moment earlier is refused honestly; the same fixed lock order as steps 3 and 4 (Employee → code / phone). The section fails visibly (a sentence in the box) rather than silently. The clipboard and pop-up paths each have a spoken fallback |
| **Scalability** | **neutral** | Everything is per employee and capped. The list view is Frappe's own paging (20) |
| **Maintainability** | **improves** | One HR check for four endpoints (was one for one); one desk wrapper; the state decided in one function on the server; the words in one script. Against that: `field_app_join` and `field_app_device` now import from `field_app_desk` (no cycle: desk imports nothing from them), and the QR encoder is 300 lines of ours to own |
| **Data integrity** | **improves** | A block goes through the record's `validate`/`before_save` (reason required, hash retired, who/when/source recorded) whichever door; a second block cannot change the reason; a cancel goes through `cancel_invite`, the one writer. No cache added, so nothing to invalidate. `registered_on` relabel changes no data |
| **Compliance / privacy** | **improves** | The block reason never reaches the phone (E4 test) and, on the desk, is shown only to HR who may read the person. No "last seen" or map anywhere (PRIV-9, AC-107): the only time on a phone is its last saved punch, and an open moves nothing. The print sheet carries no employee ID. **No visibility widened**: the section is HR-only and per-employee; the list columns added are label, how-joined and joined date on a doctype already company-scoped; `last_seen` and `checkin_count` were removed from the list, not added. The code exists in the HR user's browser for the life of one dialog and nowhere else |

---

## 4 · Things I found that the spec has wrong or unsettled

1. **The design's `inviteShow` still lists "Copy link"** (01b section 9.2) and
   AC-47 says "no Copy link". The user's decision wins; 01b should be updated.
2. **A phone in "Consent not given" was blockable by nobody.** The record's
   rules (step 1, per section 4.1) let a person block Active or Pending only;
   the not-agreed state arrived later (17 Sep) and nobody said what HR may do
   to it. Such a phone holds a live secret that can, with E9, become Active. A
   lost one had no stop button except waiting for the person to leave. **Built:
   E11 blocks it, as the server on HR's word, recorded as HR's.** The desk form
   itself still refuses that move by hand (step 1's tests stand). If the user
   would rather HR could not, it is one line.
3. **A Pending web-page phone has no state in 01b section 9.1.** Built as
   `web_pending` - "Waiting for HR" - with Invite offered. The web flow's
   approval stays where it is (the phone record).
4. **"Last punch (time, place name)" - the place is not stored on the punch.**
   `Employee Checkin` has no location name. E12 names the workplace of the
   Shift Assignment that covered the punch's day, which is what the geofence
   measured against. If the person had no located assignment that day, the
   place is empty and only the time shows.
5. **Section 6 says E12 has no rate limit ("—").** Built that way. It is one
   call per Employee form open, HR-only, and bounded; if the bench shows a
   pathological HR user, `HR_KEY` at 120/h is one decorator.
6. **AC-103 says the plan state has "no buttons".** The section for a tenant
   without field check-in shows the one sentence and nothing else - not even
   the phones table. That is what "not part of your plan" should mean.
7. **`registered_on` was labelled "Registered On".** Relabelled "Joined" so
   the list column reads as AC-114 wants. The fieldname is unchanged.

---

## 5 · Three personas

| Persona | What changes | What must not change - and did not |
|---|---|---|
| **CXO / System Manager** | Sees the section on every employee, in every company; can invite, cancel and block; sees the whole phone list | Cannot unblock (no such action exists); cannot see a code after the dialog closes |
| **HR Manager / HR User** | The section for employees they may read; invite, cancel, block; the phone list for their companies | An HR user limited to company A gets `PermissionError` for company B's employee on all four endpoints; an HR Manager with no company and no employee record is refused by the phone list and by E11's save (fail closed, pinned in step 2) |
| **Employee (field worker)** | Nothing new on the phone. A block still answers `DEVICE_BLOCKED` with no reason | Never learns the reason; never sees who blocked |
| **Employee (office colleague), line manager** | Nothing. The section is empty for them (the script does not ask; the server would refuse) | No new row readable |

---

## 6 · What I ran, and what I did not

**No bench command, no site, no database, no browser.** The bench belongs to
slices 031 and 025. Static checks only:

| Check | Result |
|---|---|
| `ast.parse` on every changed `.py` (8 files); `json.load` on the doctype JSON | all parse |
| `ruff check --config hrms/pyproject.toml` on the 7 Python files I wrote or changed | **All checks passed** |
| `scripts/check_app_integrity.py` | **620 checks, OK** (614 at step 4; the new hook paths and the new module add six). Run before every one of the four commits |
| `scripts/check_api_paths.py` | 2 unresolved - **both the known pre-existing hrms `payment_entry.js` debt**, same as steps 1 to 4 |
| `node --check` on the three scripts | all parse |
| The QR encoder against `pyqrcode` (Frappe's own, in the bench container, read only) | **93 of 93 matrices identical** with the same mask forced; 91 of 93 pick the same mask unforced |
| Frappe v16.33.1 source read from the container | `doctype_js` takes a list per doctype (`get_code_files_via_hooks`); `doctype_list_js` is a real hook (`desk/form/meta.py:112`); `frappe.listview_settings` `filters` (3-tuples), `formatters`, `hide_name_column`, `add_fields`, `onload`, `$paging_area`; `frappe.has_indicator` (no `get_indicator` → `status` is an ordinary column, so the formatter applies); `frappe.ui.Dialog` `size`, `onhide`, `get_primary_btn`, `fields_dict`; a `reqd` dialog field makes `get_values()` return null with Frappe's own popup (hence `reqd: 0` on the reason); the Select control takes `{label, value}` options and sorts only when asked; `frappe.datetime.convert_to_user_tz(dt, false)` returns a moment, `now_date()` is user-tz, `add_days` returns an ISO string (so the "yesterday" test uses moment); `frappe.show_alert`; `frappe.permissions.has_permission(..., print_logs=)`; `get_fullname` caches per request; `rate_limit` counts a call **before** running it, so refused calls count |
| ERPNext Employee JSON in the container | the "Attendance & Leaves" tab is `attendance_and_leave_details` … `holiday_list`, then the Salary tab - so `insert_after: holiday_list` lands in that tab |
| `ignore_permissions` counts | `field_app_desk.py` 0, `field_app_device.py` 1 (unchanged), `field_app_join.py` 6 (unchanged), `field_app_errors.py` 0 |

**The 31 tests, by class** (the commit message says 33 - I miscounted there; 31 is right): TheSectionIsForHrWhoMayReadThePerson 5,
TheStateMachine 9, CancelAWaitingCode 3, BlockAPhone 6,
ThePhoneListIsShapedForRollouts 3, TheDeskLimitsArePerHrUser 1, TheContract 4
(one of which also checks the installer twice), plus 2 step-3 tests changed.

---

## 7 · Owed to the bench, in order

1. `bench --site test_site migrate` from a throwaway container mounting this
   worktree - **needed**: two custom fields on Employee (`alvoraa_field_app_section`,
   `alvoraa_field_app_html`) and the list-column change on the phone doctype.
2. `run-tests --module alvoraa_portal.tests.test_field_app_step5_013` (31
   tests). Where the first run is most likely to correct the test module: (a)
   the maker's Company User Permission in `DeskCase.setUpClass` - if
   `_company_permission` on a user who already has one from another class
   collides, it is the fixture; (b) `test_013_ac107` compares `last_seen` before
   and after an E4 open - E4 needs the app phone's reading, which E3 writes;
   (c) `test_013_ac115` builds two web phones for two companies - if
   `ensure_company()` and `_company()` disagree about "company A", the
   assertion set is what to look at, not the hooks.
3. **The fail-without-fix proof:** delete the two lines
   `if not has_permission("Employee", "read", doc=employee, user=user, print_logs=False):`
   / `frappe.throw(_("You cannot see this employee."), frappe.PermissionError)`
   in `field_app_desk.hr_who_may_act`; run
   `test_013_ac109_an_hr_user_limited_to_another_company_is_refused`,
   `test_013_ac52_...`, `test_013_ac111_an_hr_user_without_permission...` and
   step 3's `test_013_ac43_...`; watch all four fail; restore with
   `git checkout --`; re-run green.
4. The step-1, step-2, step-3, step-4 and 014 modules (E7's answer grew by
   one key and its refusals now come back in the body; step 3's two changed
   tests must pass).
5. Full `alvoraa_portal` and `alvoraa_goals` once. Baseline 1,387 / 18; expect
   **1,418 / 18** (31 new).
6. Custom DocPerm count before and after (228 rows / 45 doctypes at step 4).
7. **A person on the local instance clicks through section 9.** No browser
   ran here; the scripts are traced, not run.

---

## 8 · Known gaps and shortcuts, declared

1. **Nothing has run against a database and no browser has opened the form.**
   The whole of section 7 is open. The three scripts have passed `node --check`
   and nothing more.
2. **The QR encoder is ours, 300 lines, level M, versions 1 to 10 only.** An
   enrol link longer than 213 characters (a very long tenant host) would throw
   in the browser; the dialog would show the refusal sentence. No tenant host is
   near that. A vendored library would have been cheaper to own; it was not
   allowed in.
3. **"Made by you {when}" on the code dialog uses E7's `made_at`.** Added to
   E7's answer (keys only ever added, OPS-8).
4. **E12's "last punch place" is the day's located Shift Assignment**, not a
   place stored on the punch (section 4, item 4). Honest, but approximate for a
   person who changed sites mid-day.
5. **The list's status formatter replaces Frappe's indicator pill.** The list
   therefore has no status *filter chip* on the pill; the standard filter on
   `status` is still there.
6. **E12 is not rate limited** (section 4, item 5).
7. **The board row was appended, not restructured.** The 013 row is one long
   line with the cells already run together by earlier steps; I added a STEP 5
   note at its end rather than reflow it.
8. **`HR_ROLES` in `field_app_join` is now unused there** (the check moved).
   Left in place: a step-3 test may name it; removing a public name is a
   separate, deliberate change.

---

## 9 · Hand-traced desk flows - for somebody to click through

Every client API used was read in Frappe v16.33.1's own source before use
(section 6). These are the flows I traced and could not click:

1. **Open an Employee as HR Manager** (a listed field worker, app on): the
   Attendance & Leaves tab shows "Field attendance app" with the sub-heading,
   "**Not joined yet.** {first} can use the app: **{designation}** is a field
   worker designation.", one primary button **Invite to the app**, "No phones
   yet.", "No codes made yet."
2. **Open an Employee as an Employee-role user**: the section is empty (no call).
3. **A tenant without field check-in**: "Field check-in is not part of your
   plan." and nothing else in the section.
4. **Invite to the app** → dialog "Invite {full name} to the app", the intro
   sentence with "**You do not need to approve it.**", "The code works for" with
   the options up to the setting (setting preselected and marked), the hint,
   Cancel · **Make the code**.
5. **Make the code** → dialog "App code for {full name}" with the QR, "Waiting
   to be used", "**Works once.**", "Works until **{date}** ({in N …})", "Made
   by you today at …", "Tell {first}" and the three steps, the amber warning,
   the grey note, **Print**, **Copy picture**, **Done**. No "Copy link".
   Network panel: one call to `make_code`, nothing else carries the code.
6. **Copy picture** → "Picture copied. Paste it in WhatsApp to {first}."; paste
   into any image field to see the QR. In a browser without the clipboard
   image API: "This browser cannot copy a picture. Use Print instead."
7. **Print** → a new window with the A4 sheet and the print dialog; company,
   title, "For **{full name}** · {designation}", the QR, three steps, the
   footer; **no employee ID**. If pop-ups are blocked: the orange toast.
8. **Done** (or Escape) → the dialog's HTML is emptied; the section redraws as
   "[Code waiting] Made by you today at … Works until **{date}** (in …).", the
   hint "This code cannot be shown again. If {first} lost it, make a new one.
   That cancels this one.", buttons **Make a new code** · **Cancel this code**,
   the code in the history as "Waiting to be used · until {date}".
9. **Invite again while a code waits** → the amber line "{first} already has a
   code waiting to be used. Making a new code cancels it." in step 1; after
   making, the old code reads "Replaced by a newer code, {when}".
10. **Cancel this code** → "Cancel this code?" with the one sentence, **Keep
    it** · **Cancel the code** (red) → the section redraws as not joined; the
    history reads "Cancelled by you, {when}". As a different HR user it reads
    the maker's name.
11. **After a phone joins** (scan with the app or call E3): "[Joined] **Joined
    {when} · {phone} · by the QR code you made {today/yesterday/on date}**",
    "No check-in from this phone yet." (or "Last check-in {when} at {place}."),
    **Invite to the app again**; the phones table row with Active (green dot +
    word) and **Block this phone**; the code as "Used {when} on {phone}".
12. **Block this phone** → "Block {phone}?" with the four lines including
    "**This cannot be undone.** If {first} gets the phone back, make a new
    code.", the reason Select, the hint "Kept in the record. {first} does not
    see the reason.", **Keep it working** · **Block this phone** (red). Press
    Block with no reason → "Choose a reason. It is kept in the record." under
    the field, dialog stays. Choose one → the section redraws "[No working
    phone] {phone} was blocked today at … by you · {reason}.", **Invite to the
    app**; the row shows Blocked with the time and reason under it; no Unblock
    anywhere - also open the phone record itself and confirm the Status field
    refuses to move.
13. **Switch the app off in HR Settings, reopen the employee** → "[App switched
    off] Field workers cannot use the app at the moment. You cannot make
    codes.", "{first} can still use the web check-in page at {host}/checkin.",
    link **Open Field App Settings**; an Active app phone's row reads "Stopped ·
    App switched off".
14. **Take the designation off the list** → "**The app is not available for
    {full name}.** Designation **{x}** is not a field worker designation.",
    "{first} marks attendance at the reception machine, or with Check In in the
    portal.", link **Change field worker designations**; a web-page phone's row
    gets the amber "Not a field worker" pill and "Joined before this rule.
    Keeps working."
15. **The phone list** (`/app/alvoraa-field-device`): opens filtered "Joined ≥
    7 days ago", columns Employee Name, Joined, Device, How it joined, Status
    (pill with the reason or date under it), no ID column, no last punch; the
    note under the paging: 'There is no "last seen" or "online now" column, on
    purpose…'. As an HR User limited to one company: that company's phones
    only.
16. **Zoom to 200% and a narrow window**: the status line wraps (flex), the
    phones table scrolls sideways inside its own region (keyboard-focusable,
    labelled), the dialogs are Frappe's (Escape closes, focus moves in).

---

## 10 · What else moved while I worked

`git fetch origin dev` succeeded this time (the broken `slice/025-brand-logo`
ref from step 3 is gone). **`origin/dev` is `886c8c4`, which is behind local
`dev`** - nothing new came in from the remote. Local `dev` is at `11a7db6`, two
commits past my base `6fb97d2` besides steps 1 to 4 themselves: `41ebe4d`
(slice 030 decision 4: `hr_api.py`, `test_org_setting_scope_030.py`) and
`11a7db6` (`test_tenant_logo_029.py`). **Neither touches a file I changed.** Not
rebased: the instruction was to commit on the branch only while steps 1 to 4
are being brought into local `dev`. When the branch is next rebased onto local
`dev` the result should be clean.

The main checkout's uncommitted changes (`ux-learnings.md`, `alvoraa_position.py`,
the KPI backlog, the 009 plan, several untracked documents) are other sessions'
work in progress. Not touched, not staged. The slice's own documents, this one
included, remain untracked in the main checkout like the rest of `docs/slices/013-mobile-app/`.

---

## 11 · Step 5 proven (2026-09-20, later the same day)

The coordinator handed over the bench: slice 025's session had confirmed it was
done, `docker ps` showed no other `hrlocal-0xx` container and `pgrep` in
`hrlocal-bench` was idle. The branch was first rebased onto local `dev`
`11a7db6` (clean; `check_app_integrity` **621 OK** afterwards - one more than
before because `dev` gained a hook path of its own). Then, claimed on the work
board from the first command to the last, everything below ran from a
throwaway container `hrlocal-013` mounting **this worktree's** three apps
against the shared `hrlocal-sites` volume, on the `hrlocal` network, as user
`frappe`, one run at a time. No `docker cp`, no dev tenant, no server, nothing
pushed, nothing in local `dev`.

### 11.1 · What ran, and the real numbers

| Step | Command / check | Result |
|---|---|---|
| Rebase | `git rebase dev` in the worktree (four commits onto `11a7db6`) | clean; the four commits are now `7a9864f`, `5436355`, `5d6cbbb`, `c0a4347` |
| Baseline | Custom DocPerm on test_site | **228 rows / 45 doctypes** |
| Migrate | `bench --site test_site migrate` | **1 min 58 s, 0 failed.** `alvoraa_field_app_section` (Section Break, after `holiday_list`) and `alvoraa_field_app_html` (HTML) present as Custom Fields on Employee; the phone doctype's list columns are `employee`, `employee_name`, `status`, `registered_on` (now labelled **Joined**), `device_label`, `join_method` |
| **First run, step-5 module** | `run-tests --module ...test_field_app_step5_013` | **28 + 3 = 31 OK, first time.** 15 s + 2.5 s. No fixture needed correcting |
| **Fail-without-fix (the per-employee read check)** | the two `has_permission` / `frappe.throw` lines deleted from `field_app_desk.hr_who_may_act`; the four permission tests run | **3 of 4 FAILED**: AC-109 "PermissionError not raised" (a store HR user got another company's section); AC-52 "PermissionError not raised" and `'Cancelled' != 'Waiting'` (the store HR user cancelled another company's code); step 3's AC-43 failed twice (made a code for another company's employee, row count 1 not 0). **AC-111 (block) still passed without the check** - E11 saves as the signed-in user, so Frappe's own write permission and the C-11c company hook refused the store HR user on their own. That is the second gate doing its job; the test's docstring now says so instead of claiming all four fail. Restored with `git checkout --`, tree clean, the four re-run: **3 OK, then 1 OK** |
| Step 1 module | `...test_field_app_step1_013` | **15 + 13 = 28 OK** |
| Step 2 module | `...test_field_app_step2_013` | **27 + 7 = 34 OK** |
| Step 3 module | `...test_field_app_step3_013` | **41 + 9 = 50 OK** (the two tests changed for the desk wrapper included) |
| Step 4 module | `...test_field_app_step4_013` | **33 OK** |
| Slice 014 module | `...test_checkin_security_014` | **14 + 2 = 16 OK** |
| Full `alvoraa_portal`, first time | `run-tests --app alvoraa_portal` | 46 min (00:56 to 01:42). The second group: **874 tests, OK**. **The first group's summary line was lost by my own `tail -60` on the output** - my mistake, not the suite's - so its count and verdict could not be read back. The testing log for that window carries no failure (the only lines matching "fail" or "error" are five test-class *names*). `test_usage` ran inside the run (01:41 to 01:42) with no failure logged. Not good enough to report as a number, so the suite was run again with the whole output kept |
| Full `alvoraa_goals` | `run-tests --app alvoraa_goals` | **18 OK**, 2 skipped, 2.6 s |
| Custom DocPerm after the above | | **228 rows / 45 doctypes** - unchanged |
| **Full `alvoraa_portal`, second time** (whole output kept) | `run-tests --app alvoraa_portal` | _filled in below_ |
