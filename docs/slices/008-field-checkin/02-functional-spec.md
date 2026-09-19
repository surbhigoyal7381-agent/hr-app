# 008 — Field Check-in — functional spec

**Author:** business analyst · 12 Sep 2026 · **Time-boxed: demo in 12 hours.**
**Scope and priority are the user's and are not re-opened here.** This document makes
P1–P11 testable.

---

## 0. Read this first — what is missing, and what is already broken

**Three required inputs do not exist.** Only `01-product-brief.md` is in
`docs/slices/008-field-checkin/`. There is no `01b-ux-design.md`, no
`01c-security-privacy-requirements.md` and no `07-devops-inputs.md`.

| Missing input | What it costs this spec |
|---|---|
| `01c` security & privacy | The `SEC`/`PRIV` rows in §15 are **provisional and written by me**, labelled `SEC-BA-n` / `PRIV-BA-n`. When the security engineer's file lands, its numbering replaces mine and the table must be re-checked. |
| `01b` UX design + clickable prototype | No screen is prototype-matched. Screen copy below is **mine** and the designer may overrule it. The slice does not meet the Definition of Ready on the design gate. |
| `07` DevOps inputs | No `OPS` items exist. NFRs in §8 come from `nfr-budget.md` only. |

**Second, and more urgent: the three custom fields this feature needs are never
created.** `field_checkin.after_migrate()` is written, and its docstring says it is
wired to both migrate and install — it is not. `alvoraa_portal/hooks.py` lists only
`attendance_correction.after_migrate` in both `after_migrate` and `after_install`.
Until `alvoraa_portal.field_checkin.after_migrate` is added to both lists, every field
punch fails on "Unknown column `alvoraa_gps_accuracy`". This is the first thing to fix
tomorrow morning. → **US-12 / AC-33.**

**Third: `field_status` has no plan gate.** `register_device` and `field_checkin` both
carry `@requires_feature("field_checkin")`; `field_status` (line 374) does not. A tenant
who has not bought the add-on can still read an employee's name, designation, today's
punch times and the branch's coordinates with a valid token. → **US-13 / AC-35.**

**Fourth: the geofence quietly does nothing when there is no shift.** Verified in
`hrms/hr/doctype/employee_checkin/employee_checkin.py`: the Shift Assignment lookup
filters on `shift_type: self.shift`, and `self.shift` is `None` whenever `fetch_shift()`
finds no shift covering the punch time. `shift_type` is mandatory on Shift Assignment,
so a `None` filter matches nothing, the function returns early, and **the punch is
accepted from anywhere**. A driver punching at 05:00 when the shift starts at 09:00 is
not geofenced. This is Frappe's behaviour, not something we introduced, and phase 1 does
**not** change it — but the demo script must not claim "you cannot punch from home"
without adding "during your shift". → **US-6 / AC-16, AC-17.**

---

## 1. Which apps and modules this touches

| App / module | How |
|---|---|
| `alvoraa_portal` | New endpoints (`field_checkin.py`, already written), new `Alvoraa Field Device` doctype, new PWA page, new Org Settings cards in `www/hrms-employee.html`, feature key in `subscription.py` |
| `hrms` | Reads and writes `Employee Checkin`; reads `Shift Assignment`, `Shift Location`, `HR Settings`; adds 3 Custom Fields to `Employee Checkin`. Surfaces `alvoraa_late_rules`' `Attendance Deduction Rule` |
| `erpnext` | `Employee` (read only: name, status, company, designation) |
| `frappe` | `File` (private), `Custom Field`, rate limiter, guest whitelist |
| `alvoraa_goals`, `alvox_compensation` | **Not touched.** |

**HRMS domains:** attendance (primary), payroll (only indirectly — Attendance Deduction
already creates Additional Salary; this slice only moves where its settings are edited),
org structure (Shift Location as the branch).

---

## 2. Gap analysis — P1 to P11

Everything below was read in the source on 12 Sep 2026, not recalled.

| # | Requirement | What the installed code already gives us | Verdict | Cost |
|---|---|---|---|---|
| **P1** | PWA on the home screen | **Nothing.** No `manifest.json`, no service worker anywhere in `alvoraa_portal` (searched `*.py`, `*.html`, `*.json`). The ESS app is a single server-rendered page, `www/hrms-employee.html`. | **Build new** — one `www/field-checkin.html` + context file + manifest + a minimal service worker | M |
| **P2** | Server URL + employee ID saved once, plus a device secret | **Nothing in Frappe.** Frappe's guest auth is either a User with an API key or nothing; there is no device-registration concept. `register_device()` is already written and correct in shape: SHA-256 only (`_hash`), secret returned once, rate-limited 6/hour per employee ID, second phone → `Pending`. | **Build new** (done — review only) | M |
| **P3** | Photo + Check In → `Employee Checkin` | `Employee Checkin` exists with `employee`, `log_type`, `time`, `device_id`, `shift`, `attendance`. **No photo field** — an `Attach Image` custom field `alvoraa_checkin_photo` plus a private `File` is the right answer. `_attach_photo()` is written, private, capped at 2 MB, and never kills the punch. | **Extend** | S |
| **P4** | Check Out + today's punches with times | `field_status()` is written and returns today's rows. The **screen does not exist**. | **Build new** (UI only) | S |
| **P5** | Geolocation + accuracy on every punch | `Employee Checkin.latitude`, `.longitude`, `.geolocation` all ship in v16. `hrms.hr.utils.set_geolocation_from_coordinates` writes the GeoJSON point — **but only when `HR Settings.allow_geolocation_tracking` is on**. Accuracy has no home in any doctype → one new Float field. | **Configure + extend** | S |
| **P6** | Geofence at punch time, with the real distance in the message | **Confirmed — already in Frappe HR, do not rebuild.** `EmployeeCheckin.validate_distance_from_shift_location()` (lines 119–157) reads the employee's submitted, Active Shift Assignment for the punch's shift, takes `Shift Location.checkin_radius`, measures with `get_distance_between_coordinates()` (haversine, returns metres) and throws `CheckinRadiusExceededError`. **Three gates you also inherit, which the brief does not mention:** (a) it returns immediately unless `HR Settings.allow_geolocation_tracking` is ON; (b) it returns if `checkin_radius <= 0`; (c) it returns if no Shift Assignment matches — including when `self.shift` is `None`. `_geofence_message()` in our code catches the exception and rewrites it with the real distance. | **Configure** (the rule) + **extend** (wording only) | S |
| **P7** | Radius configurable in Org Settings, floor 1 m, warn below 50 m | `Shift Location.checkin_radius` is a plain `Int` with **no minimum and no validation** — 0 and negatives are accepted and mean "no geofence". The Org Settings panel exists (`#panel-org-settings`, HR-only, line 3516) but has no attendance card. | **Extend** — new card + 2 HR-only endpoints | M |
| **P8** | Deduction rule editable in Org Settings | `Attendance Deduction Rule` (module `alvoraa_late_rules`) already carries every control: `late_threshold_minutes` (default 60), `count_early_exit`, `early_exit_threshold_minutes` (60), `free_violations_per_week` (1), `deduction_per_violation_days` (0.25), `round_up_from_days` (0.75), `round_up_to_days` (1.0), `deduct_from_leave_first`, `leave_types`, `lwp_salary_component`, `daily_wage_basis`, `exempt_grades`, `notify_employee`, `notify_manager`, `week_start_day`, `process_from`, `enabled`. Permissions: HR Manager, HR User, System Manager. **Invent nothing.** | **Extend** — a read/write card over the existing doctype | M |
| **P9** | Feature key + `sync_registry()` | **Done.** `subscription.py` line 175 defines `field_checkin` — opt-in, `requires: ["attendance"]`, app `alvoraa_portal`. It is not in `pricing.PLATFORM_FEATURES`, so `_sellable_registry_keys()` includes it and `sync_registry()` creates one `Alvoraa Module Price` row, status **Built**, no rate — exactly the "built and unpriced" state the admin page surfaces. | **Configure** (done — verify only) | S |
| **P10** | Punches visible in the app and in Frappe HR | Same `Employee Checkin` list. `device_id` is set to `alvoraa-field-app` (portal punches use `web-portal`, the machine uses its own id), so the three sources are separable with a list filter and no new field. | **Configure** | S |
| **P11** | Offline queue | Nothing exists. Needs a local queue, a client request id for de-duplication, and a server-side idempotency check. `captured_at` is already accepted and sets `alvoraa_checkin_offline`, but **the punch is stamped with server `now()`, so a queued punch lands at the wrong time** (see §7, E8). | **Build new** — **first to drop** | M |

**Single source of truth.** The branch's position and allowed radius live in **one
place: `Shift Location`.** Org Settings edits that record; the app only displays it
(`field_status().work_location`). No radius is stored in the portal, in HR Settings, or
on the device.

### What we are NOT building, and why

- No geofence maths of our own. Frappe's is already there and correct.
- No parallel "field attendance" doctype. Punches go in `Employee Checkin`.
- No face matching, no background tracking (brief §5, §6).
- No new radius field. `Shift Location.checkin_radius` is it.

---

## 3. Process flow

**Setting up (once, per phone)**

1. HR gives the driver the address `ppj.dev.alvoraa.co/field-checkin` and his employee
   ID (for example `HR-EMP-00042`).
2. He opens it in Chrome → menu → **Add to Home screen**. On iPhone: Safari → Share →
   Add to Home Screen.
3. He types the employee ID and presses **Set up**.
4. *Decision:* does this employee already have an Active or Pending phone?
   - **No** → the phone is handed a secret, saved in the browser. Screen: "Set up for
     Ramesh Kumar."
   - **Yes** → the registration is saved as **Pending**. Screen: "A phone is already
     registered for Ramesh Kumar. HR has been asked to approve this one." He cannot
     punch until HR sets it to Active.

**Punching**

1. He opens the app from the home screen. It shows his name, today's punches, and
   "You need to be within 100 m of PPJ Noida".
2. He presses **Check In**. The camera opens; he takes a photo.
3. The app asks the browser for a position.
   - *Location off or refused* → "We could not get your location. Turn on location for
     this app and try again." No punch.
   - *Accuracy worse than 100 m* → "Your location is only accurate to about 340 m,
     which is not close enough to record. Step outside or into the open and try again."
     No punch.
4. The punch is sent. The server decides:
   - *Outside the radius* → "You are about 140 m from PPJ Noida. You need to be within
     100 m to check in." No punch, and the photo is discarded.
   - *Inside, or no geofence in force* → `Employee Checkin` is created, the photo is
     attached privately, the screen shows "Checked in at 9:04 am".
5. **Check Out** works the same way. Today's list grows a row each time.

**HR's day**

1. HR opens **Org Settings → Attendance & location**, picks PPJ Noida, sets the radius,
   saves.
2. HR sees a new Pending device, checks with the supervisor, sets it to **Active**;
   `activated_by` records who did it.
3. HR opens the `Employee Checkin` list and sees field punches beside machine punches.

---

## 4. Epic and user stories

**Epic:** *A field employee with no email and no desk marks his own attendance from his
phone, with the time, the place and a photo, and HR sees it beside the machine punches.*

Personas from brief §2: **Ramesh** (field employee — driver or guard, low-end Android,
Hindi first, no email), **Anita** (internal employee), **Priya** (HR Manager),
**Suresh** (line manager / supervisor), **CXO**.

| ID | Story | Brief item | Points | INVEST note |
|---|---|---|---|---|
| US-1 | As **Ramesh**, I want to add the check-in app to my phone's home screen, so that I open it in one tap like any other app. | P1 | 3 | Independent of the punch itself; testable by install prompt plus standalone launch |
| US-2 | As **Ramesh**, I want to type the address and my employee ID once, so that I never type anything again. | P2 | 3 | |
| US-3 | As **Ramesh**, I want to take a photo and press Check In, so that my attendance is marked for today. | P3 | 5 | Largest story; splitting the photo out would leave a punch with no evidence, so it stays whole |
| US-4 | As **Ramesh**, I want to press Check Out and see my punches with times, so that I know the day is recorded. | P4 | 3 | |
| US-5 | As **Priya**, I want every punch to carry where the phone was and how sure it was, so that I can answer "was he actually there". | P5 | 2 | |
| US-6 | As **Anita**, I want to be stopped if I punch away from the branch, and told how far away I am, so that I can walk the last 50 m instead of guessing. | P6 | 3 | |
| US-7 | As **Priya**, I want to set the allowed distance for each branch in Org Settings, so that a small site and a large campus each work. | P7 | 5 | |
| US-8 | As **Priya**, I want to change the late-coming deduction rule in Org Settings without opening the desk, so that I can adjust it myself. | P8 | 5 | |
| US-9 | As a **CXO**, I want field check-in sold as a separately priced add-on, so that customers who do not need it are not charged for it. | P9 | 1 | Mostly done |
| US-10 | As **Suresh**, I want field punches in the same `Employee Checkin` list as machine punches, so that I have one attendance story per person. | P10 | 1 | |
| US-11 | As **Ramesh**, I want a punch made with no signal to be sent when I get signal back, so that a dead zone does not cost me a day's pay. | P11 | 5 | **Drop first.** |

### The "must not" stories

| ID | Story | Points |
|---|---|---|
| US-12 | As **Priya**, punches **must not** fail on a fresh or migrated site because the photo, accuracy and offline columns were never created. | 1 |
| US-13 | As a **CXO**, a tenant who has not bought the add-on **must not** be able to reach any field endpoint — including the one that reads a name and today's punches. | 1 |
| US-14 | As **Ramesh**, my phone **must not** be able to punch for anybody else, and knowing my employee ID alone **must not** let somebody punch as me. | 3 |
| US-15 | As **Ramesh**, my check-in photo and my coordinates **must not** be visible to a colleague, and **must not** be reachable by a URL without logging in. | 3 |
| US-16 | As **Ramesh**, the app **must not** know where I am at any moment other than the two seconds when I press a button. | 2 |
| US-17 | As **Priya**, a phone belonging to somebody who has left **must not** be able to punch. | 1 |
| US-18 | As **Ramesh**, my device secret **must not** appear in any log, any error message, or any list view HR can read. | 2 |

### YouTrack-ready table

| Summary | Persona | Points | ACs | Requirements |
|---|---|---|---|---|
| Field app installs to the home screen (Android and iPhone) | Field employee | 3 | AC-1..3 | P1 |
| One-time setup: server address, employee ID, device secret | Field employee | 3 | AC-4..8 | P2, SEC-BA-1 |
| Photo plus Check In creates an Employee Checkin | Field employee | 5 | AC-9..13 | P3, PRIV-BA-1 |
| Check Out and today's punches with times | Field employee | 3 | AC-14, AC-15 | P4 |
| Position and accuracy recorded on every punch | HR Manager | 2 | AC-18..20 | P5 |
| Geofence refusal names the real distance | Internal employee | 3 | AC-16, AC-17, AC-21..23 | P6 |
| Check-in radius per branch in Org Settings | HR Manager | 5 | AC-24..29 | P7 |
| Late-coming deduction rule in Org Settings | HR Manager | 5 | AC-30..32 | P8 |
| Field check-in as a priced add-on | CXO | 1 | AC-34 | P9 |
| Field punches in the Employee Checkin list | Supervisor | 1 | AC-36 | P10 |
| Offline queue with de-duplication | Field employee | 5 | AC-37..40 | P11 |
| Custom fields created on install and on migrate | HR Manager | 1 | AC-33 | — |
| Plan gate on every field endpoint | CXO | 1 | AC-35 | P9 |
| A device punches only for its own employee | Field employee | 3 | AC-41..44 | SEC-BA-1..3 |
| Photos and coordinates stay private | Field employee | 3 | AC-45..48 | PRIV-BA-1..3 |
| No tracking between punches | Field employee | 2 | AC-49 | PRIV-BA-4 |
| A leaver's phone cannot punch | HR Manager | 1 | AC-50 | SEC-BA-4 |
| The device secret never leaks | Field employee | 2 | AC-51, AC-52 | SEC-BA-5 |

---

## 5. Acceptance criteria

Every one has an oracle a test can assert on.

**US-1 — home screen (P1)**
- **AC-1** Given Chrome on Android and the page `/field-checkin`, When it loads over
  HTTPS, Then a `manifest.json` is linked with `display: "standalone"`, a `start_url` of
  `/field-checkin`, and 192 px and 512 px icons, and `navigator.serviceWorker` reports a
  registered worker. *Oracle: the manifest link tag in the DOM, and the registration
  promise resolving.*
- **AC-2** Given Safari on iPhone, When the user does Share → Add to Home Screen and
  opens the icon, Then the page opens with no Safari address bar
  (`window.navigator.standalone === true`).
- **AC-3** Given a 360 px-wide viewport, When the punch screen renders, Then the Check
  In button is at least 44 × 44 CSS px and no horizontal scrollbar appears.

**US-2 — one-time setup (P2)**
- **AC-4** Given a phone with nothing saved, When the app opens, Then the setup screen
  is shown and the punch screen is not.
- **AC-5** Given employee ID `HR-EMP-00042` of an Active employee, When Set up is
  pressed, Then `register_device` returns `status: "active"` with a token, one
  `Alvoraa Field Device` row exists with `status = "Active"` and
  `token_hash = sha256(token)`, and the plain token appears in **no** database column.
- **AC-6** Given the token is saved, When the app is closed and reopened, Then no setup
  screen appears and `field_status` returns the employee's name.
- **AC-7** Given an unknown ID, and separately the ID of a Left employee, When Set up is
  pressed, Then **the same** message is returned — "We could not find an active employee
  with that ID. Please check it with HR." *Oracle: byte-identical response bodies.*
- **AC-8** Given 6 registration calls in an hour for one employee ID, When a 7th is
  made, Then the response is Frappe's rate-limit error (HTTP 417) and no new device row
  is created.

**US-3 — photo and Check In (P3)**
- **AC-9** Given an Active device, a good fix inside the radius, and a 300 KB JPEG,
  When `field_checkin(log_type="IN")` is called, Then one `Employee Checkin` exists with
  `employee` = the device's employee, `log_type = "IN"`,
  `device_id = "alvoraa-field-app"`, and `time` within 5 s of server time.
- **AC-10** Given that punch, Then a `File` exists with
  `attached_to_doctype = "Employee Checkin"`, `attached_to_name` = the punch,
  `is_private = 1` and a `file_url` starting `/private/files/`, and
  `Employee Checkin.alvoraa_checkin_photo` holds that URL.
- **AC-11** Given a photo larger than 2 MB, When the punch is sent, Then the
  `Employee Checkin` is still created, `alvoraa_checkin_photo` is empty, and an Error Log
  row exists whose content contains **no base64 image data**.
- **AC-12** Given a photo string that is not valid base64, When the punch is sent, Then
  the punch is created and the response is `status: "ok"`.
- **AC-13** Given no photo at all, When the punch is sent, Then the punch is created.
  *(The photo is evidence, not a gate — brief §4. Making it mandatory is a scope change;
  see §16 Q3.)*

**US-4 — Check Out and today's list (P4)**
- **AC-14** Given one `IN` today, When `field_status` is called, Then `checked_in` is
  `true`, `todays_checkins` has exactly 1 row, and `server_time` is present.
- **AC-15** Given `IN` at 09:04 and `OUT` at 18:10, When the screen renders, Then both
  rows show in ascending time in 12-hour format ("9:04 am", "6:10 pm") and `checked_in`
  is `false`.

**US-6 — geofence (P6)**
- **AC-16** Given `HR Settings.allow_geolocation_tracking = 0`, When a punch is sent
  from 5 km away, Then it is **accepted**. *This is Frappe's behaviour; the test records
  it so nobody demonstrates "it blocks you" with the switch off.*
- **AC-17** Given the switch is on but the punch time falls outside every Shift
  Assignment (so `Employee Checkin.shift` is empty and `offshift = 1`), When a punch is
  sent from 5 km away, Then it is **accepted** and `offshift = 1`. *Known limitation,
  recorded not fixed.*
- **AC-21** Given the switch on, an Active submitted Shift Assignment for today with
  Shift Location "PPJ Noida" (radius 100 m), and a punch 140 m away inside shift hours,
  Then no `Employee Checkin` row is created and the message is exactly
  "You are about 140 m from PPJ Noida. You need to be within 100 m to check in."
- **AC-22** Given the same setup and a punch 40 m away, Then the punch is created.
- **AC-23** Given the radius is set to 0, When a punch is sent from 5 km away, Then it is
  accepted. *Frappe returns early on `checkin_radius <= 0`.*

**US-5 — position and accuracy (P5)**
- **AC-18** Given a punch with lat 28.5355, lon 77.3910, accuracy 12.4, Then the
  `Employee Checkin` holds those values in `latitude`, `longitude` and
  `alvoraa_gps_accuracy`, and (with the geolocation switch on) `geolocation` holds a
  GeoJSON FeatureCollection whose coordinates are `[77.3910, 28.5355]` — longitude first.
- **AC-19** Given no latitude, When a punch is sent, Then it is refused with "We could
  not get your location. Turn on location for this app and try again." and no row exists.
- **AC-20** Given accuracy 340, When a punch is sent, Then it is refused with "Your
  location is only accurate to about 340 m…" and no row exists. Given accuracy exactly
  100, Then it is accepted (the bound is `> 100`).

**US-7 — radius in Org Settings (P7)**
- **AC-24** Given Priya (HR Manager) opens Org Settings, Then an "Attendance & location"
  card lists every `Shift Location` with its name, coordinates and current radius.
- **AC-25** Given she sets PPJ Noida to 150 and saves, Then
  `Shift Location.checkin_radius` is 150, a Version row records the change, and the next
  punch 140 m away is accepted.
- **AC-26** Given she types 30, Then an advisory warning shows — "30 m is smaller than a
  phone can reliably measure. Phone GPS is usually accurate to 10–20 m, so people
  standing at the door may be refused." — and **Save still works**.
- **AC-27** Given she types 0 or a negative number, Then it is refused with "The
  smallest distance Frappe allows is 1 m. To switch the check off completely, use 'Do
  not check location here'." and nothing is saved.
- **AC-28** Given she sets 1, Then it saves and a punch 3 m away is refused.
- **AC-29** Given Anita (Employee role, not HR) calls the save endpoint directly, Then it
  returns `PermissionError` and the radius is unchanged.

**US-8 — deduction rule in Org Settings (P8)**
- **AC-30** Given the `late_rules` feature is on for the tenant and Priya opens Org
  Settings, Then a "Late-coming deductions" card shows the existing
  `Attendance Deduction Rule` with its current values, using the doctype's own labels
  (Late Arrival Threshold (minutes), Count Early Exit, Early Exit Threshold (minutes),
  Free Violations per Week, Deduction per Counted Violation (days), Round Up From/To
  (days), Deduct from Leave Balance First, Exempt Grades, Notify Employee, Notify
  Manager, Enabled).
- **AC-31** Given she changes Free Violations per Week from 1 to 2 and saves, Then the
  `Attendance Deduction Rule` document holds 2 and a Version row records the change with
  her user and timestamp.
- **AC-32** Given the `late_rules` feature is **off** for the tenant, Then the card is
  not rendered and the save endpoint returns `PermissionError`.

**US-12, US-13, US-9, US-10 — plumbing**
- **AC-33** Given a brand-new site built with `bench install-app alvoraa_portal` and no
  migrate, Then Custom Fields `alvoraa_checkin_photo`, `alvoraa_gps_accuracy` and
  `alvoraa_checkin_offline` all exist on `Employee Checkin`, and a punch succeeds.
  *(Requires `alvoraa_portal.field_checkin.after_migrate` in both `after_migrate` and
  `after_install` in `hooks.py`.)*
- **AC-34** Given `sync_registry()` runs on the control plane, Then one
  `Alvoraa Module Price` row exists with `feature_key = "field_checkin"`,
  `status = "Built"` and no rate; running it a second time adds nothing.
- **AC-35** Given a tenant whose feature list omits `field_checkin`, When
  `register_device`, `field_checkin` **or `field_status`** is called, Then each returns
  `PermissionError` with "Field Check-in & Geofencing is not included in your plan."
- **AC-36** Given one machine punch, one portal punch and one field punch today, When
  the `Employee Checkin` list is filtered on `device_id = "alvoraa-field-app"`, Then
  exactly the field punch is returned.

**US-11 — offline (P11, droppable)**
- **AC-37** Given the phone is offline, When Check In is pressed, Then the punch is held
  locally and the screen says "Saved on your phone. It will be sent when you have
  signal."
- **AC-38** Given the phone reconnects, Then the queued punch is sent with `captured_at`
  set, and the resulting `Employee Checkin` has `alvoraa_checkin_offline = 1`.
- **AC-39** Given the same queued punch is sent twice (a retry, or the app reopened),
  Then exactly **one** `Employee Checkin` exists for it. *Oracle: row count = 1, matched
  on the client request id.*
- **AC-40** Given a queued punch made at 07:50 and delivered at 11:30, Then the recorded
  `time` is **07:50** — the moment of the punch, not of the upload — and
  `alvoraa_checkin_offline = 1`. **This does not work today**; the code writes server
  `now()`. See §7 E8.

**Must-not stories**
- **AC-41** Given device D registered to employee A, When `field_checkin` is called with
  D's token, Then the punch is created for A. There is **no** parameter by which a
  different employee can be named. *Oracle: the endpoint signature carries no employee
  argument.*
- **AC-42** Given a valid employee ID but no token, When `field_checkin` is called with
  that ID in place of the token, Then `AuthenticationError` "This phone is not set up."
  and no row is created.
- **AC-43** Given employee A already has an Active phone, When a second phone registers
  with A's ID, Then the new device is `Pending`, no token is returned, and a punch with
  it fails with "This phone is waiting for HR to approve it."
- **AC-44** Given Priya sets that Pending device to Active, Then `activated_by` holds her
  user id and a punch with it now succeeds.
- **AC-45** Given the photo's `/private/files/...` URL, When it is fetched while logged
  out, Then HTTP 403.
- **AC-46** Given Anita (Employee role, no HR rights, not Ramesh's manager), When she
  fetches Ramesh's photo URL, Then HTTP 403.
- **AC-47** Given Anita opens the `Employee Checkin` list, Then she sees only her own
  rows. *Oracle: row count. **This needs a User Permission on Employee — see the §6
  warning.***
- **AC-48** Given any Error Log written by this feature, Then it contains no base64
  string longer than 100 characters and no latitude or longitude value.
- **AC-49** Given the app is open for 30 minutes with no button pressed, Then
  `navigator.geolocation.watchPosition` was never called and no request reaches the
  server. *Oracle: an empty network log, and no `watchPosition` in the source.*
- **AC-50** Given Ramesh's `Employee.status` is set to Left, When his phone punches,
  Then `AuthenticationError` "This employee record is no longer active." and no row is
  created.
- **AC-51** Given the `Alvoraa Field Device` list in the desk, Then `token_hash` is
  hidden, no plain token is shown anywhere, and there is no endpoint that returns a token
  for an existing device.
- **AC-52** Given a failed punch, Then neither the response body nor any log contains the
  token.

---

## 6. Permission and visibility matrix

`EC` = `Employee Checkin`, `SL` = `Shift Location`, `AFD` = `Alvoraa Field Device`,
`ADR` = `Attendance Deduction Rule`. Verified against each doctype's JSON.

| Role | EC | SL | AFD | ADR | HR Settings |
|---|---|---|---|---|---|
| System Manager | CRUD | CRUD | CRUD | CRUD | write |
| HR Manager | CRUD | CRUD | CRUD | CRUD | write |
| HR User | CRUD | CRUD | read + write (**no create, no delete**) | CRUD | read |
| Employee | create, read, write (own record, via User Permission) | read only | **none** | **none** | none |
| Line manager (Employee role + team) | own and team, read | read | none | none | none |
| Guest (the phone) | **no doctype access at all** — reaches data only through the three whitelisted endpoints, each of which resolves an Active device token first | — | — | — | — |

`time` on `Employee Checkin` is **permlevel 1**: the Employee role has read but not
write, so a person cannot back-date their own punch. Keep it that way.

### The negative cases — who must NOT see what

| Must not | Why | Enforced by |
|---|---|---|
| A colleague sees Ramesh's check-in photo | It is a photo of a person's face at a place and time | Private `File` plus `Employee Checkin` read permission (AC-45, AC-46) |
| A colleague sees Ramesh's coordinates | Location is personal data | The same row permission (AC-47) |
| Anyone reads a photo by URL without logging in | face_app's exact failure (brief §5) | `is_private = 1` (AC-45) |
| A phone punches for another employee | Fraudulent attendance | No employee parameter on the endpoint (AC-41) |
| Somebody with a stolen employee ID punches | Employee IDs are printed on ID cards | Second phone goes to Pending (AC-43) |
| A leaver punches | | Active check at punch time (AC-50) |
| An employee changes the radius | | HR-only endpoint (AC-29) |
| An employee changes the deduction rule | | HR-only endpoint plus feature gate (AC-32) |
| HR of company A sees company B's punches | Multi-company tenants | **Gap — see the warning below** |

> **⚠ Two row-level gaps, flagged not fixed.**
> 1. **`Employee Checkin` has no permission query condition in HRMS** — verified:
>    `hrms/hooks.py` registers none. An Employee-role user sees *every* check-in unless a
>    **User Permission on Employee** exists for them. AC-47 will fail on a site without
>    them. Check PPJ's site before the demo; if they are missing, this is a **P0 privacy
>    defect**, not a nicety.
> 2. **Nothing scopes field punches by company.** `register_device` reads `company` and
>    then discards it. For PPJ (one company) this is fine for the demo. On a
>    multi-company tenant an HR Manager sees every company's devices. Recorded as E12.

---

## 7. Edge cases

| # | Case | Expected behaviour | Status today |
|---|---|---|---|
| E1 | A second phone for one employee | Registers **Pending**, cannot punch, waits for HR; `activated_by` records who approved | **Works** (AC-43, AC-44) |
| E2 | Employee leaves | The punch is refused at the moment of the punch, because `Employee.status` is re-read every time. Registration is refused too. The old device row survives as history | **Works** (AC-50). HR should also set the device to Blocked — no automation; §16 Q5 |
| E3 | Punch at a shift boundary or past midnight | Frappe's `get_actual_start_end_datetime_of_shift` decides which shift a punch belongs to, including night shifts crossing midnight. Outside every shift window `shift` is empty, `offshift = 1`, **and the geofence is skipped** | **Partly.** Recorded in AC-17, not fixed |
| E4 | Two punches in quick succession | Frappe's `validate_duplicate_log` only refuses an exact same-second, same-`log_type` duplicate. Two `IN`s three seconds apart both save | **Accepted for phase 1.** The screen must disable the button while a punch is in flight. Backlog: a "you already checked in at 9:04" confirmation |
| E5 | No Shift Assignment at all | No geofence. The punch is accepted from anywhere and `offshift = 1` | **Works as Frappe intends.** The Org Settings card must say so plainly |
| E6 | Shift Assignment with no Shift Location | Frappe filters on `shift_location: ["is", "set"]`, so there is no geofence and the punch is accepted | Works as intended |
| E7 | Radius 0, or 1 m | 0 or less means no geofence — Frappe returns early. 1 m is the tightest real fence; almost everybody is refused | **Works**; Org Settings makes "off" an explicit choice rather than a silent 0 (AC-27, AC-28) |
| E8 | Offline punch arriving hours late | Should record the **punch** time, not the upload time | **Broken by design today** — `time = now()`. If P11 ships, `field_checkin` must accept `captured_at`, sanity-check it (not in the future, not more than 48 h old) and use it as `time`. If P11 is dropped, this does not arise |
| E9 | The same offline punch sent twice | Exactly one record | **Not handled.** Needs a client-generated request id stored on the punch and checked before insert. Frappe's duplicate check only catches identical seconds |
| E10 | Phone with the wrong clock | Cannot shift the record. `time` is always the server's; `captured_at` only flags "this was offline" | **Works** — and it is the reason to keep server time for live punches |
| E11 | Weak or absent GPS | Two different refusals with two different messages | **Works** (AC-19, AC-20) |
| E12 | Multi-company | No company scoping on devices or on the field endpoints | **Gap.** Fine for PPJ; must be closed before a multi-company tenant buys it |
| E13 | Employee re-hired on the same record | A re-hired employee with an old Active device can punch immediately, with no re-registration | **Flagged.** HR should Block devices at exit (§16 Q5) |
| E14 | Photo fails to decode, or is oversized | The punch survives; the photo is lost and logged | **Works** (AC-11, AC-12) |
| E15 | Geofence refuses the punch after the photo was taken | The photo is never stored, because `_attach_photo` runs only after a successful insert | **Works** — and that is the right order |
| E16 | Device is Blocked mid-shift | The next punch fails with "This phone has been blocked. Please speak to HR." An already-recorded punch stands | **Works** |
| E17 | Cancelled or amended Shift Assignment | Frappe filters `docstatus: 1` and `status: "Active"`, so a cancelled assignment stops geofencing from the moment it is cancelled | Works as intended |

---

## 8. Non-functional requirements for this slice

Numbers from `.claude/context/nfr-budget.md`. **No `07-devops-inputs.md` exists, so
there are no `OPS` items to carry.**

| What | Budget for this slice | How it is proven |
|---|---|---|
| Volume | PPJ demo: about 30 field staff × 2 punches a day = 60 rows a day. Design for 1,000 employees × 4 punches = 4,000 rows a day, 1.5 M a year | Seeded test at 250 employees |
| Punch round-trip on a 3G phone, p95 | **≤ 2.5 s** including a 300 KB photo upload; the button shows a spinner within 300 ms | Timed test |
| `field_status` API, p95 | **≤ 500 ms** | Integration test |
| App first paint on a 360 px Android, cold | **≤ 2.5 s**; the whole install-to-first-punch journey **under 2 minutes** (brief §7) | Manual timing on a real low-end handset |
| Photo size | Client downscales to 800 px long edge, JPEG q0.6, target ≤ 300 KB; server hard cap 2 MB | AC-11 |
| Queries per punch | ≤ 8 (device, employee, shift fetch, shift assignment, shift location, insert, file, device update). **No N+1 anywhere** | Query counter in the test |
| Background jobs | **None.** Every punch is synchronous — a driver must see "Checked in at 9:04" before he walks away | — |
| Storage | 300 KB × 1.5 M punches a year is about **450 GB a year at full scale**. At PPJ's 30 staff it is about 5 GB a year. **This is the biggest running cost in the feature and there is no retention job** — see §9.5 |
| Personal data | Photo (a face), coordinates, times. Private files, HR-scoped rows, never in logs | AC-45 to AC-48 |
| Rate limits | Registration 6/hour per employee ID (already there). **The punch endpoint has none** — add one, for example 30/hour per device, before this leaves the demo |

---

## 9. Compliance-impact sub-analysis

**I am not a lawyer. Nothing below is a legal ruling.** The security engineer's `01c`
does not exist yet; when it does, it supersedes the `SEC-BA` / `PRIV-BA` items here.

### 9.1 Data touched

| Field / object | Class | Purpose collected for | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| `alvoraa_checkin_photo` — a face at a moment | **sensitive** (image of an identifiable person) | Evidence that the named person made the punch | Employment contract / attendance record ⚠ to confirm | **Yes — new** |
| `latitude`, `longitude` | **sensitive** (location) | Confirming presence at the branch | Same ⚠ | Extended — the portal already stores these; the field app adds them for staff who had none |
| `alvoraa_gps_accuracy` | internal | Deciding whether the fix can be trusted | Same | **Yes — new** |
| `Alvoraa Field Device.token_hash` | internal (secret material, hashed) | Proving the phone is the registered one | Security | **Yes — new** |
| `device_label`, `platform`, `last_latitude`, `last_longitude` | internal | HR recognising which phone is which; the device's last known position | Security / support | **Yes — new** |
| `Employee` name, designation, status | internal | Showing the driver his own name | Existing | No |

**Why a photo is unavoidable:** without it a punch proves only that a registered phone
was near the branch, not that the person was, and the whole point is attendance for staff
nobody at reception sees. **But `last_latitude` and `last_longitude` on the device record
are not needed for the outcome** — the punch already carries them. **Recommendation: drop
those two fields**, or write down why HR needs a device's last position.

### 9.2 Obligations engaged

| Obligation | Source | What this slice must do | Feature that does it |
|---|---|---|---|
| Notice to the employee about what is collected | DPDP 2023 §5 | A plain line on the setup screen: what is taken, when, and who sees it | **Missing — §9.6, §16 Q1** |
| Data minimisation | DPDP; baseline §2 | Position only at the button press; nothing between punches | AC-49 |
| Purpose limitation | DPDP | Photos used for attendance verification only; no face matching in phase 1 | Brief §4 |
| Storage limitation and erasure | DPDP; baseline §4 | A retention period for photos | **Missing — brief §6 backlog, raised again at §9.6** |
| Security safeguards | DPDP §8; SPDI Rules | Private files, hashed secrets, nothing secret in logs | AC-45, AC-51, AC-52 |
| Audit trail of who allowed what | ISO 27001 / SOC 2 | `activated_by` plus `track_changes` on the device; Versions on Shift Location and the deduction rule | AC-44, AC-25, AC-31 |
| No behavioural monitoring | baseline prohibitions | Nothing runs between punches | AC-49 |

### 9.3 Visibility delta

**New:** HR Manager, HR User and System Manager can now see a photo of a field
employee's face and his coordinates at each punch. A line manager sees them **only** if
the site's permissions already let him read that person's `Employee Checkin`.

**Explicitly not new:** no colleague, no guest, no unauthenticated URL holder, and nobody
at all between punches. See the §6 warning — on a site with no User Permissions on
Employee, *any* Employee-role user can read every check-in row today. That predates this
slice, but this slice makes the data far more sensitive.

### 9.4 Decision automation

**Does this slice decide anything about a person? Partly, and a human can always
intervene.**

- The **geofence refusal** is automatic: it prevents a punch. The employee is told the
  real distance and can walk closer or ask HR. HR can create the `Employee Checkin`
  by hand. That human path must be in the demo script.
- The **deduction rule** does decide money — but it already exists and already creates a
  submitted `Attendance Deduction`. This slice only changes where its settings are
  edited. Whether a human approves each deduction belongs to the slice that built it.
- **Nothing here rates, scores or infers anything about a person.** No face matching, no
  emotion, no behaviour. If face matching is asked for during the demo, the answer is
  brief §6.

### 9.5 Retention and deletion

**Nothing is deleted today, and that is the weakest point of the feature.** Check-in
photos accumulate for ever. The brief already lists a retention job in §6 and marks it
"raise with the user — it is a DPDP obligation, not a nicety". I am raising it. It does
not block the demo; it blocks selling the feature.

On an erasure request, punch times are decision-bearing (they feed attendance and pay)
and stay. **The photo is not decision-bearing and should go.** That split needs counsel.

### 9.6 ⚠ Open compliance questions

| Question | Who must decide | What it blocks |
|---|---|---|
| How long are check-in photos kept, and who deletes them? | Surbhi + counsel | Selling the add-on; not the demo |
| What notice does the field employee see at setup, and in which language? | Surbhi + counsel | Nothing tonight; a DPDP §5 gap the day it goes live |
| Is a stored face photo "personal data" only, or does keeping it for verification make it biometric on any reading? | Counsel | Whether a stronger basis and a consent record are needed |
| Does PPJ's site have User Permissions on Employee, so one employee cannot read another's punches? | Surbhi, tonight | **The demo** |
| Erasure versus attendance audit — what survives? | Counsel | The retention job's design |

---

## 10. Data migration and backfill

| Item | Action | Rollback |
|---|---|---|
| Three Custom Fields on `Employee Checkin` | Created by `field_checkin.after_migrate()`, which must be wired into `hooks.py` (`after_migrate` **and** `after_install`). It is safe to run twice — `create_custom_fields` skips what exists | Delete the three Custom Fields; existing punches lose only the photo link |
| `Alvoraa Field Device` doctype | Created by migrate | Delete the doctype; nothing else refers to it |
| `field_checkin` price row | `sync_registry()` on the control plane | Delete the `Alvoraa Module Price` row |
| Existing check-ins | **Nothing.** Old punches simply have empty photo and accuracy fields | — |
| Existing Shift Locations | **Nothing changes automatically.** A location with no radius, or radius 0, keeps behaving as "no geofence". HR opts in per location | Set the radius back to 0 |
| `HR Settings.allow_geolocation_tracking` | **Must not be switched on silently.** Turning it on makes latitude and longitude mandatory for *every* check-in on the site, including the reception machine's, which may send none — every machine punch would then fail. **Check how PPJ's machine punches arrive before switching this on.** | Switch it off |

> That last row is the single biggest deployment risk in the slice. Prove it on the local
> bench with a simulated machine punch before touching the demo site.

---

## 11. Org Settings specification

Two new cards in the existing **Org Settings** panel (`#panel-org-settings` in
`www/hrms-employee.html`), which is already HR-only (`nav-org-settings` is shown when
`ctx.is_hr`). Follow the pattern already there: a `.pf-card`, a heading, one line of
plain explanation, and endpoints in `hr_api.py`.

### Card A — "Attendance & location"

Shown when the `field_checkin` feature is on. HR Manager and HR User only.

**Row 1 — the master switch** (writes `HR Settings.allow_geolocation_tracking`)

> ☐ **Record where check-ins happen, and check them against the branch**
> When this is off, no check-in records a place and no distance is checked, wherever the
> person is. When it is on, every check-in must carry a position — including punches sent
> by an attendance machine. Turn it on only after checking that your machine sends one.

That warning is not decoration. See §10.

**Row 2 — a table of branches**, one row per `Shift Location`:

| Column | Source | Editable |
|---|---|---|
| Branch | `Shift Location.location_name` | no |
| Position | `latitude`, `longitude` to 6 decimals | yes, with a "Use my current position" button |
| People may check in within | `checkin_radius`, in metres | yes |
| | "Do not check location here" toggle | yes — writes 0 |

**The rules on the radius field** — exactly the constants already in the code
(`FRAPPE_MIN_RADIUS_M = 1`, `ADVISED_MIN_RADIUS_M = 50`, `DEFAULT_RADIUS_M = 100`):

| Entered | Behaviour |
|---|---|
| blank | Treated as "do not check location here". The toggle is set and the number greys out |
| 0 or less | **Refused**: "The smallest distance Frappe allows is 1 m. To switch the check off completely, use 'Do not check location here'." Nothing is saved |
| 1 to 49 | **Saved**, with an advisory warning under the field, in amber, that does not block: "30 m is smaller than a phone can reliably measure. Phone GPS is usually accurate to 10–20 m, so people standing at the door may be refused." |
| 50 and above | Saved with no warning |
| Default for a new location | **100** |

A helper line under the table, because E5 and E6 will otherwise generate support calls:

> This applies only to people who have a shift assignment with this branch on it, during
> their shift hours. Somebody with no shift assignment, or punching outside their shift,
> is not checked against any distance.

**Endpoints** (new, in `hr_api.py`; each carries `frappe.only_for("HR Manager", "HR User")`
and `@requires_feature("field_checkin")`):

- `get_checkin_locations()` → `[{name, location_name, latitude, longitude, checkin_radius}]`
  plus `geolocation_tracking_on`.
- `save_checkin_location(name, latitude, longitude, checkin_radius)` — validates the table
  above and writes through `frappe.get_doc(...).save()` so a Version is recorded.
- `set_geolocation_tracking(on)` — writes the HR Settings single.

### Card B — "Late-coming deductions"

Shown only when the `late_rules` feature is on for the tenant (`has_feature("late_rules")`).
It edits the **existing** `Attendance Deduction Rule` — no new doctype, no new settings,
no duplicate defaults. If a company has more than one rule, show a picker; if it has
none, show "No rule set up yet" with a link to the desk, not a create form.

Fields surfaced, with the doctype's own labels and defaults:

| Group | Field | Type | Default in the doctype |
|---|---|---|---|
| On or off | Enabled | check | 1 |
| What counts | Late Arrival Threshold (minutes) | int | 60 |
| | Count Early Exit | check | 1 |
| | Early Exit Threshold (minutes) | int | 60 |
| How much | Free Violations per Week | int | 1 |
| | Deduction per Counted Violation (days) | float | 0.25 |
| | Round Up From (days) | float | 0.75 |
| | Round Up To (days) | float | 1.0 |
| Where it comes from | Deduct from Leave Balance First | check | 1 |
| Who | Exempt Grades | multi-select | — |
| Telling people | Notify Employee / Notify Manager | check | 1 / 1 |

**Not surfaced here, deliberately:** `lwp_salary_component`, `daily_wage_basis`,
`week_start_day`, `process_from`, `shift_type`, `company`, `leave_types`. They change how
pay is calculated or which weeks get reprocessed; those belong in the desk with a payroll
person. Card B says so in one line and links to the desk document.

---

## 12. Notifications and messages

No emails are added by this slice. Every message is on screen.

| Trigger | Exact words | Who sees it | Must never contain |
|---|---|---|---|
| Setup done | "Set up for Ramesh Kumar." | the phone | the token |
| Second phone | "A phone is already registered for Ramesh Kumar. HR has been asked to approve this one." | the phone | which phone, or where it is |
| Unknown or left employee ID | "We could not find an active employee with that ID. Please check it with HR." | the phone | whether the ID exists |
| Blocked device | "This phone has been blocked. Please speak to HR." | the phone | who blocked it |
| No position | "We could not get your location. Turn on location for this app and try again." | the phone | |
| Weak position | "Your location is only accurate to about 340 m, which is not close enough to record. Step outside or into the open and try again." | the phone | |
| Outside the fence | "You are about 140 m from PPJ Noida. You need to be within 100 m to check in." | the phone | anyone else's position |
| Punch saved | "Checked in at 9:04 am" / "Checked out at 6:10 pm" | the phone | |
| Offline (P11) | "Saved on your phone. It will be sent when you have signal." | the phone | |
| Leaver | "This employee record is no longer active. Please speak to HR." | the phone | the reason they left |

> **Gap:** "HR has been asked to approve this one" is not true — **nothing notifies HR**.
> Either send a notification to the HR Manager role, or change the words to "Ask HR to
> approve this phone." Truth in the message is cheaper than a notification tonight.

---

## 13. Localisation and accessibility

- Every string above goes through `_()` on the server and a single lookup on the client,
  so Hindi and Punjabi (brief §6) drop in later without touching the markup.
- Times shown in 12-hour format with am/pm, which is what PPJ's staff read. Server times
  are plain site-local times — **do not** print a timezone offset on the phone; it will
  confuse more than it explains.
- Distances in whole metres. No decimals on a phone screen.
- The app must work at 360 px, with one thumb, in sunlight: buttons at least 44 px,
  contrast at least 4.5:1, the camera and the punch button reachable without scrolling.
- Every control has a text label as well as an icon. A driver who cannot read English
  still recognises a green button that says "Check In" in his own language.
- The photo carries alt text: "Photo taken at check-in".

---

## 14. Audit and traceability

| Question, a year later | Answered by |
|---|---|
| Who punched, when, and from where? | `Employee Checkin`: `employee`, `time`, `latitude`, `longitude`, `alvoraa_gps_accuracy`, `geolocation` |
| Was it the field app or the machine? | `device_id` (`alvoraa-field-app` / `web-portal` / the machine's id) |
| Which phone? | `Alvoraa Field Device`, `track_changes: 1`, `last_seen`, `checkin_count` |
| Who allowed a second phone? | `activated_by` plus the Version row |
| Who changed the radius, and to what? | Version history on `Shift Location` — which requires saving through the ORM (AC-25) |
| Who changed the deduction rule? | Version history on `Attendance Deduction Rule` (AC-31) |
| Was the punch made offline? | `alvoraa_checkin_offline` |

---

## 15. Traceability

| Source | ID or line | Story | Acceptance criteria | Status |
|---|---|---|---|---|
| Brief | P1 PWA to home screen | US-1 | AC-1, AC-2, AC-3 | covered |
| Brief | P2 one-time setup and device secret | US-2 | AC-4…AC-8 | covered |
| Brief | P3 photo and Check In | US-3 | AC-9…AC-13 | covered |
| Brief | P4 Check Out and today's times | US-4 | AC-14, AC-15 | covered |
| Brief | P5 position and accuracy | US-5 | AC-18, AC-19, AC-20 | covered |
| Brief | P6 geofence, real distance | US-6 | AC-16, AC-17, AC-21, AC-22, AC-23 | covered, with two limits recorded |
| Brief | P7 radius in Org Settings | US-7 | AC-24…AC-29 | covered |
| Brief | P8 deduction rule in Org Settings | US-8 | AC-30, AC-31, AC-32 | covered |
| Brief | P9 feature key and sync_registry | US-9, US-13 | AC-34, AC-35 | covered (code already done) |
| Brief | P10 visible in both places | US-10 | AC-36 | covered |
| Brief | P11 offline queue | US-11 | AC-37…AC-40 | covered; **droppable**, AC-40 fails today |
| Brief §4 | photo is evidence, never public | US-15 | AC-10, AC-45 | covered |
| Brief §4 | a vague GPS fix is refused | US-5 | AC-20 | covered |
| Brief §4 | an employee ID alone cannot punch | US-14 | AC-42, AC-43 | covered |
| Brief §7 | under two minutes on a 360 px Android | US-1, US-2 | §8 budget plus AC-3 | covered |
| Brief §7 | nothing tracks anybody between punches | US-16 | AC-49 | covered |
| **`01b` prototype** | — | — | — | **MISSING — no prototype exists. The screen copy in §12 is the analyst's and unreviewed.** |
| `SEC-BA-1` the device secret proves identity; the ID alone does not | mine, provisional | US-14 | AC-41, AC-42, AC-43 | covered |
| `SEC-BA-2` a second phone needs a human | mine | US-14 | AC-43, AC-44 | covered |
| `SEC-BA-3` registration cannot be used to list staff | mine | US-2 | AC-7, AC-8 | covered |
| `SEC-BA-4` a leaver cannot punch | mine | US-17 | AC-50 | covered |
| `SEC-BA-5` the secret is stored hashed and never returned twice | mine | US-18 | AC-5, AC-51, AC-52 | covered |
| `SEC-BA-6` every field endpoint is plan-gated | mine | US-13 | AC-35 | **not met today** — `field_status` is ungated |
| `SEC-BA-7` the punch endpoint is rate-limited | mine | — | — | **GAP — no AC, no code. Add before go-live** |
| `PRIV-BA-1` photos are private files | mine | US-15 | AC-10, AC-45, AC-46 | covered |
| `PRIV-BA-2` a colleague cannot read another's punch | mine | US-15 | AC-47 | **covered only if User Permissions exist — verify** |
| `PRIV-BA-3` no personal data in logs | mine | US-15 | AC-11, AC-48 | covered |
| `PRIV-BA-4` position is read only at the button press | mine | US-16 | AC-49 | covered |
| `PRIV-BA-5` a retention period for photos | mine | — | — | **GAP — user decision needed (§9.6)** |
| `PRIV-BA-6` the employee is told what is collected, at setup | mine | — | — | **GAP — no notice text exists (§9.6)** |
| **`07` OPS items** | — | — | — | **MISSING — the file does not exist. No OPS row could be completed.** |

**Gaps with no acceptance criterion:** `SEC-BA-7` (punch rate limit), `PRIV-BA-5`
(retention), `PRIV-BA-6` (notice). None blocks the demo; all three block selling it.

---

## 16. Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| Q1 | What notice do we show the field employee at setup, and in which language? | Surbhi + counsel | Go-live, not the demo |
| Q2 | How long are check-in photos kept, and who deletes them? | Surbhi + counsel | Selling the add-on |
| Q3 | Is the photo mandatory, or may a punch go through without one? Today it is optional (AC-13). | Surbhi | The demo script |
| Q4 | Does PPJ's site have User Permissions on Employee, so one employee cannot read another's check-ins? | Surbhi, tonight | **The demo** |
| Q5 | Should a device be Blocked automatically when an employee leaves, or is HR doing it by hand? | Surbhi | Nothing today; E13 |
| Q6 | How do PPJ's reception-machine punches arrive, and do they carry coordinates? Switching on `allow_geolocation_tracking` will break them if they do not. | Surbhi + engineer, before deploy | **Deploying P6 and P7** |
| Q7 | If P11 is dropped, do we keep `alvoraa_checkin_offline` on the record? (Recommend yes — it costs nothing and P11 is coming.) | Surbhi | Nothing |

---

## 17. Assumptions

- `[ASSUMPTION]` PPJ is a single-company tenant for the demo, so E12's missing company
  scoping does not show.
- `[ASSUMPTION]` Field staff have a data connection most of the time, so P11 can be
  dropped without breaking the demo.
- `[ASSUMPTION]` PPJ Noida will be set up as a `Shift Location` with real coordinates,
  and the field staff will have a submitted, Active Shift Assignment pointing at it. If
  they do not, the geofence demonstrates nothing (E5).
- `[ASSUMPTION]` 100 m is an acceptable default radius for a store. Not measured.
- `[ASSUMPTION]` The 100 m accuracy cut-off is sensible. It comes from the code, not from
  a measurement on PPJ's phones. Worth checking on the actual handsets.
- `[ASSUMPTION]` The line manager's view of photos (brief §2) is whatever the site's
  existing `Employee Checkin` permissions already give him. **No new supervisor screen is
  built in phase 1** — if the user expected one, that is brief §6 ("Supervisor view of
  photos"), not this slice.

---

## 18. Ready check

| Definition of Ready | |
|---|---|
| Brief approved, scope fixed | ✅ |
| One named user, one complete outcome | ✅ |
| Out of scope written down | ✅ (brief §5, §6) |
| **Clickable prototype reviewed at the design check** | ❌ **no `01b`, no prototype** |
| **Every screen state designed** | ❌ same |
| **`01c` security and privacy with numbered SEC/PRIV** | ❌ **missing — provisional items written here instead** |
| **`07` DevOps inputs §1–3 with OPS items** | ❌ **missing** |
| Gap analysis against verified source | ✅ |
| Stories, INVEST-checked, sized, must-nots included | ✅ |
| Every story has a Given/When/Then with an oracle | ✅ |
| Traceability complete | ⚠ complete for the brief; three rows have no AC and are named as gaps |
| Permission matrix with negative cases | ✅, with two row-level gaps flagged |
| Edge cases | ✅ (17) |
| NFR numbers made specific | ✅ |
| Migration and backfill | ✅ |
| Compliance sub-analysis | ✅ |
| Nothing prohibited | ✅ — no face matching, no tracking, no inference |
| Open questions have owners | ✅ — Q4 and Q6 need answering before the demo |

**Verdict, plainly: four boxes fail, so by the book this slice is not Ready.** Three of
them are missing documents, and the user fixed the scope and the deadline knowing that.
Build can start on P1–P10 tonight without them. What must not happen is the feature being
**sold or deployed to a live customer** until `01c` exists, Q2 (retention), Q4 (who can
see whose punches) and Q6 (machine punches) are answered, and the punch endpoint is
rate-limited.
