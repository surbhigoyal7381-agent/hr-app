---
slice: 013-mobile-app
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-09-17
status: draft
inputs: [01-product-brief.md (incl. Gate decision 2026-09-17), 01a-ux-opportunities.md, 01b-ux-design.md (incl. Design check decision 2026-09-17 and QR lifetime note), prototype-v1/index.html (https://claude.ai/artifact/XmykPG1vosM1US4iidyFFz, version 1), 01c-security-privacy-requirements.md (incl. User decisions 2026-09-17), 07-devops-inputs.md §1–§3 (incl. User answers 2026-09-17), 00-sequencing-recommendation.md, 014-checkin-security-fixes/00-impact-analysis.md and 03-implementation-notes.md (branch slice/014-checkin-security-fixes), alvoraa_portal/field_checkin.py, www/field-checkin.html, www/field_checkin.py, alvoraa_field_device.json and .py, subscription.py, hooks.py, hr_api.py (org settings), hrms hr_settings.json, hrms employee_checkin.json and .py, alvoraa_goals review_items.py (HR Settings hook), alvoraa_leader_view_settings (Single settings precedent), health.py]
---

# 013 — Mobile app, step 1 — functional spec

**I recommend. You decide.** This spec turns the approved brief, the agreed prototype and the
security and DevOps requirements into stories an engineer can build and a tester can prove.

Nothing was run for this document. No bench, no docker, no build, no request to any server.
I read the slice documents and the code on `dev` (working copy, HEAD `9138251`; `origin/dev`
fetched, at `c27fb56`). **I am not a lawyer.** Where an answer turns on the law, I flag it.

---

## Read this first

**Bad news first.**

1. **Slice 014 is built but not on `dev`.** Its five commits sit on branch
   `slice/014-checkin-security-fixes`. This slice's server code must not reach `dev` before
   them (OPS-43). Local building can start now.
2. **Two input documents disagree, and I did not pick silently.**
   - **Clearing the phone's secret hash (OPS-50) would hide *why* a phone stopped.** If the
     hash is wiped when a phone is Replaced or Removed, the server can no longer find that
     phone, so it cannot answer "You joined on another phone" (D3, SEC-10). Worse, after
     slice 014 an unknown secret is answered "waiting for HR". **My proposal:** move the hash
     into a second hidden field (`retired_token_hash`) in the same save. The live field is
     empty (OPS-50 and OPS-52's self-check still hold), the phone still gets its own screen,
     and the controller stops the status ever going back (SEC-8). DevOps and security to
     confirm (Q-2).
   - **Invite history: delete after 12 months (OPS-52) or never delete while punches exist
     (01c PRIV-10)?** My proposal reconciles both: keep any code that set up a phone while that
     phone has punches; delete codes that never set up a phone after 12 months. Surbhi, as
     interim compliance owner, decides (Q-1). Only the delete step waits on this.
3. **The approved design links to a screen that does not exist.** Field App Settings says
   "Change this in Org Settings › Field check-in" for photo retention. No such screen exists:
   the retention key `alvoraa_checkin_photo_retention_days` is read only in `field_checkin.py`,
   and `hr_api.ALLOWED_ORG_SETTINGS` allows only `kra_link_mandatory` (read in code). The spec
   shows the number with no link (Q-4).
4. **The settings do not get their own page in the desk.** `CLAUDE.md` §4 says organisation
   settings belong in HR Settings, and slice 010 already put three settings there with a
   change history (`alvoraa_goals/review_items.validate_hr_settings`). So "Field App Settings"
   becomes a **"Field attendance app" section of HR Settings**, with the same fields, words,
   confirm and history. The prototype shows a separate page. **Surbhi to agree the difference**
   (Q-5). The server work does not wait on it.
5. **Two things the design needs are missing from the endpoint contract.** "Agree and continue"
   on the notice-changed screen needs a server call (E9, new). And the codes list needs five more
   codes: `QR_NOT_RECOGNISED` and `DEVICE_REMOVED` (both from 01c), plus `DEVICE_PENDING`,
   `LOCATION_MISSING` and `INVALID_REQUEST`. They must be in app version 1, because they ask the
   app to show something specific (07 §2 section 3 point 7).
6. **One rule from slice 014 shapes the codes.** After 014, a well-formed secret nobody holds gets
   the same answer as a phone waiting for HR, so nobody can test employee IDs one by one. The
   app must therefore get **one** code (`DEVICE_PENDING`) for both. Two different codes would
   reopen the leak 014 closed.
7. **Notification wording is not in `01b`.** I drafted it (§10). The designer should confirm it.
8. **A tenant with several companies gets one list of field-worker designations.** In ERPNext a
   Designation belongs to no company. A group cannot make "Driver" a field job in one company
   and not in another. Fine for the pilot; noted as Q-9.

**What I found that is good.** Most of the hard parts already exist and are reused, not rebuilt:
the punch record (`Employee Checkin`), the geofence (Frappe HR's
`validate_distance_from_shift_location`), private photos, the photo access log, the leaver
lock, the plan gate (`requires_feature("field_checkin")`), and slice 014's log wrapper
(`_private_request`).

**The answer in short**

| | |
|---|---|
| Gap analysis | 5 configure · 11 extend (one also configures) · 7 build new (one also configures) · 6 drop |
| Stories | **48** — 30 server (Frappe) = **104 points**; 18 app (Capacitor, build and CI) = **58 points**; **162 total** |
| Acceptance criteria | **234** (AC-1 to AC-235; AC-71 not used) |
| Build first | Server: US-1, US-2, US-4 (after 014 is on dev). App: US-31 (before any key exists) |

---

## 1 · Cross-module reach

| App | Touched? | How |
|---|---|---|
| **`alvoraa_portal`** | **Yes — the main home** | `field_checkin.py` (statuses, codes, new endpoints), `Alvoraa Field Device` (fields, rules, permissions), two new doctypes and one child table, `/enrol` page, `www/field-checkin.html` (notice rows, FC-1, FC-2), `hooks.py` (HR Settings validate, Employee form script, daily job), `patches.txt`, one report, tests |
| **`hrms`** | **Read and extend, no upstream edit** | `HR Settings` gets custom fields (like slice 010). `Employee Checkin` gets one custom field (fake-location flag). The geofence, `Shift Assignment` and `Shift Location` are reused as they are |
| **`erpnext`** | Read only | `Employee` (status, first and last name, designation, company), `Designation`, `Company` |
| **`frappe`** | Used, not edited | `Notification Log`, Version history (`track_changes`), rate limiter, Singles, Data Import, REST |
| **`alvoraa_goals`** | **Indirectly** | Its `validate_hr_settings` hook also runs on every HR Settings save. Both hooks must pass; a test saves HR Settings with both apps installed |
| **`alvox_compensation`** | No | — |
| **New, outside Frappe** | Yes | A Capacitor Android app project, CI workflows in `.github/`, `.gitignore`, `deploy/nginx.conf` (body limits, device-path zone) |
| **`www/hrms-employee.html`** | **Never** | Line B rule (00-sequencing §3) |

**HRMS domains**

| Domain | Effect |
|---|---|
| **Attendance** | Direct. App punches land in `Employee Checkin` beside machine punches and feed auto attendance as today |
| **Payroll** | Indirect. Attendance feeds pay; a wrong or missing punch is a pay question. No payroll code changes |
| **Org structure** | Designation decides who may use the app |
| Leaves, appraisals, goals, compensation, learning | None |

**Personas used throughout**

| Persona | In this slice |
|---|---|
| **Field employee** (driver, guard) — "Suresh Yadav, Driver, Kaveri Transport" | Joins by QR, checks in and out, sees what is recorded, removes the phone. **Has no Frappe user.** Proves who they are with the phone's secret |
| **HR User** | Makes and cancels codes, blocks phones, for employees Frappe lets them see |
| **HR Manager** — "Anita Rao" | All of HR User, plus the Field attendance app settings (D20) |
| **CXO / System Manager** | Same rights as HR Manager, across all companies. No create or delete on phone records |
| **Line manager** | Nothing new. Sees team punches and photos as today |
| **Colleague (Employee role)** | Nothing new. Must not see any code, phone or acknowledgement |
| **The phone itself** | A guest caller holding a device secret. Can act only for its own employee |
| **Guest** (holds nothing, or only a code) | `/enrol` page; checking a live code shows four facts only |
| **Alvoraa (Surbhi)** | Receives technical alerts and daily counts with no names |

---

## 2 · Gap analysis

Verdicts: **Configure** = settings, fields, permissions, no code. **Extend** = hooks, controller
rules, new endpoints on existing records. **Build new** = new doctype, page or app. **Drop** = not
needed; reason given.

| # | Requirement | What exists today (read in source) | Verdict | Cost |
|---|---|---|---|---|
| G1 | Punch record with time, place, photo | `Employee Checkin` (hrms) with `latitude`, `longitude`, `device_id`; our custom fields `alvoraa_checkin_photo`, `alvoraa_gps_accuracy`, `alvoraa_field_device`, `alvoraa_legal_hold` (`field_checkin.after_migrate`) | **Configure** (reuse) | — |
| G2 | Geofence | `EmployeeCheckin.validate_distance_from_shift_location` with `Shift Location.checkin_radius`, on when `HR Settings.allow_geolocation_tracking`; message rewritten by `_geofence_message` | **Configure** (reuse) | — |
| G3 | Who may see a punch and its photo; photo views logged; photo deleted after N days | `checkin_query_conditions`, `checkin_has_permission`, `log_photo_view`, `purge_old_checkin_photos` | **Configure** (reuse, unchanged) | — |
| G4 | Plan gate | `subscription.requires_feature("field_checkin")`, `has_feature` | **Configure** (reuse) | — |
| G5 | Organisation settings: field-worker designations, app on/off (default Yes), code lifetime 1 h–7 days (default 24 h), with change history | Nothing for this. `HR Settings` is a Single with `track_changes: 1`, HR Manager write, HR User read (read in JSON). Slice 010 precedent: custom fields plus a validate hook | **Configure + Extend**: custom fields on HR Settings, one validate hook. A multi-select needs a small child table (see G15) | M |
| G6 | Mark a punch whose phone reported a fake location | No field | **Configure**: one custom field on `Employee Checkin` | S |
| G7 | Only Active phones may do anything; new statuses | `_device_from_token` refuses only `Blocked` and `Pending` (`field_checkin.py:120–123`); status options `Pending/Active/Blocked` | **Extend** | S |
| G8 | Phone record cannot be forged, re-pointed, unblocked or deleted | HR Manager has create and delete, HR User has write, `employee` editable (`alvoraa_field_device.json`); controller only sets `activated_by` | **Extend**: controller rules, permission change, new fields | M |
| G9 | Error codes, version check, no-store, request limits | English sentences only; the web page matches text (`field-checkin.html:629–667`) | **Extend** | M |
| G10 | App start answer, punch answer, remove phone | `field_status` and `field_checkin` exist; no remove | **Extend** (two endpoints) + one new endpoint | M |
| G11 | Leaver: phones blocked, codes cancelled | `block_devices_for_leaver` blocks Active and Pending phones (`field_checkin.py:836`) | **Extend** (cancel codes, record reason) | S |
| G12 | Notice text owned by the server, versioned, old versions kept | `CONSENT_VERSION = "2026-09-13"` constant; rows hardcoded in `field-checkin.html:290–310` | **Extend**: a versioned notice store in code, never edited, only added to | S |
| G13 | **HR-issued single-use code** | Nothing in Frappe HR or ERPNext. Frappe's reset-password key belongs to a `User`; field workers have none | **Build new**: doctype `Alvoraa App Invite`. *Why not a field?* One employee has many codes over time, each with its own outcome; the phone record does not exist until a code is used | M |
| G14 | **Acknowledgement history** | Two single fields on the phone (`consent_given_on`, `consent_version`); a second acknowledgement would overwrite the first (PRIV-3). Compliance map A7 status unknown; nothing found in this repo | **Build new**: doctype `Alvoraa Notice Acknowledgement`, insert-only. *Why not a child table on the phone?* Anyone who can edit the phone could edit a child row; this history must be write-once | S |
| G15 | Multi-select of designations | Frappe needs a child doctype for `Table MultiSelect` | **Build new**: child table `Alvoraa Field Worker Designation` (one Link field) | S |
| G16 | `/enrol` page that never redeems | Nothing | **Build new**: one guest `www` page | S |
| G17 | HR desk: app section on Employee, invite dialog, block dialog, phones list | Phones only in the device list view | **Build new** (desk client script and one HTML area on the Employee form); list view **Configure** | M |
| G18 | HR alerts | `Notification Log` pattern used in `kra_api.py:158`, `goals_api.py:1058` | **Extend** (reuse Notification Log) | S |
| G19 | Daily counts and technical alerts to Alvoraa | `health.collect_scheduled` pulls titles and counts to the control plane | **Extend** | M |
| G20 | Access-request answer for one employee (PRIV-12) | No rights console (compliance map A8) | **Extend**: one Script Report | S |
| G21 | Daily clean-up job | Daily scheduler exists (`hooks.py` `daily`) | **Extend** | S |
| G22 | **The phone app** | Web page `www/field-checkin.html` (1,234 lines), secret in `localStorage` | **Build new**: Capacitor Android shell bundling an adapted page | L |
| G23 | CI guards: key files, host allow-list, permissions, size | None (01c §13, 07 §3) | **Build new** (CI steps) | M |
| D1 | "Copy link" in the invite dialog | In `01b` §9.2 and prototype | **Drop** — user decision 2026-09-17 (01c) | — |
| D2 | "Expired codes cleaned daily" (brief S5) | — | **Drop as written**: codes are marked "Ran out", not deleted (PRIV-10); deletion only per Q-1 | — |
| D3 | A separate "Field App Settings" doctype | Prototype shows a page | **Drop**: HR Settings section instead (CLAUDE.md §4, slice 010 precedent). Q-5 | — |
| D4 | An `app_config` endpoint for the minimum version | `01b` §8 mentions it | **Drop**: E1 and E4 already carry `min_version` (OPS-24: one call on open) | — |
| D5 | Employee-ID join inside the app | Web page has it | **Drop** in the app (D18). The web page keeps it | — |
| D6 | A stored "Stopped" status | `01b` §9.1 shows "Stopped" | **Drop as a stored value**: computed at request time (D5, OPS-30, OPS-53) | — |

**Single source of truth**

| Thing | Truth | Everything else |
|---|---|---|
| Who is a field worker | `HR Settings` designation list + `Employee.designation` **at the moment of the call** | Never copied onto the phone record |
| Who a phone belongs to | `Alvoraa Field Device.employee`, frozen at insert | Punches link to the phone |
| Which notice words a person read | `Alvoraa Notice Acknowledgement` rows + the notice store in code | The old `consent_*` fields stay for history only, never updated again |
| Time of a punch, expiry of a code | Server clock | The phone's clock is kept only as a claim (`alvoraa_captured_at`, existing) |


---

## 3 · Process flows

Screen names in `code` match the prototype. Endpoints E1–E12 are in §6.

### 3.1 HR gives Suresh the app

1. Anita (HR Manager) opens Suresh's Employee record → section **Field attendance app**.
2. **Decision:** is Suresh eligible? Active, designation in the list, app switched on, plan includes field check-in, Anita can read this Employee.
   - No → no Invite button; a plain reason (`empNotField`, `empAppOff`, plan line). **End.**
3. Anita presses **Invite to the app**, picks a lifetime up to the organisation's setting (default 1 day), presses **Make the code** (E7).
4. **Decision:** is a code already waiting? Yes → it is cancelled in the same save ("Newer code made").
5. The QR is drawn in Anita's browser. She prints it or copies the picture into WhatsApp. When the dialog closes, the code can never be shown again.
6. **Unhappy:** she lost it → **Make a new code** (step 3). She sent it to the wrong person → **Cancel this code** (E10).

### 3.2 Suresh joins

1. Suresh installs the app, presses **Scan the QR code from HR** (camera explained first), or **Choose the QR picture from my photos**.
2. **Decision (on the phone, no network):** is it `https://<tenant>.alvoraa.co/enrol#t=<code>`? No → `notAlvoraa` / `pickNoQr`. **End.**
3. App calls E1 (check). **Nothing is used.**
4. **Decision:** code live and person eligible?
   - Ran out / used / cancelled / not recognised → dead-code screen, "Ask HR for a new code". **End.** A used code scanned from a different phone alerts HR (§10).
   - App off / not a field job / plan off → its screen. **End.**
   - App too old → `update`. **End.**
   - No internet → `noSignalJoin` → Try again.
5. `confirm`: **Is this you? Suresh Y. · Driver · Kaveri Transport**.
   - **This is not me** → confirm sheet → **Cancel this code** (E2) → HR alerted → `notMeDone`. **End.**
6. `notice`: six rows, tick box. **Agree and finish** (E3). **The code is used here, inside one locked save.**
7. **Decision at E3:** anything changed since step 3 (used by someone else, ran out, app switched off, designation changed, employee left, notice version moved)? Yes → that screen, nothing saved.
8. Server: code Used; any Active **app** phone of Suresh → Replaced; new phone Active; acknowledgement row written; the secret sent back once. Anita gets "Suresh Yadav joined the Alvoraa app on Redmi 12".
9. `welcome` → **Check In** → location explained → punch.

### 3.3 Every day

1. Suresh opens the app → saved screen shows at once → E4 refreshes it.
2. **Decision at E4:** app too old / phone blocked / replaced / removed / employee left / app off / not a field job / notice changed / plan off → that screen; Check In hidden (notice changed asks for agreement first).
3. **Check In** → photo taken in memory → position → E5.
4. **Decision at E5:** no position / vague / outside the radius / pressed twice / too many tries / no internet / server fault → that screen; **Try again keeps the photo** where the problem is not the photo.
5. Saved → result → home shows "Checked in since 9:02 am". Check Out the same way; afterwards "Checked out at 6:14 pm".

### 3.4 Phone lost, new phone, leaving, removing

| Event | Who acts | What happens | Old phone next opens |
|---|---|---|---|
| Phone lost | HR: **Block this phone** + reason (E11) | Status Blocked; cannot be undone (D4) | `blocked` |
| New phone | HR makes a new code; Suresh joins on the new phone | Old app phone → Replaced in the same save (D3) | `replaced` |
| Suresh leaves | HR sets Employee status Left | Phones Blocked ("Left the company"), waiting codes Cancelled ("Employee left") | `left` or `blocked` |
| Suresh removes the phone | Suresh: Settings → **Remove this phone** (E6); needs internet (D10) | Status Removed; HR sees "Removed by Suresh" | First launch |
| Someone else joins on Suresh's phone | Ramesh scans his own code on it | Suresh's phone record → Removed; HR alerted "one phone, two people" | — |

### 3.5 Switching the app off (rollback)

1. Anita unticks **Field workers can use the app** in HR Settings.
2. Confirm shows live counts: "3 codes waiting to be used will stop working", "31 phones that joined will stop marking attendance". A reason from the list is required.
3. Saved with the reason in the change history. No phone record or code is edited.
4. Within 60 seconds every app phone gets `APP_OFF_FOR_FIELD` at its next call, and waiting codes get it at E1. Web-page phones keep working.
5. Ticking it again restores the same phones with no new codes.

Removing a designation from the list works the same way for people with that designation.

---

## 4 · Data model

Every new field says why an existing field cannot carry it.

### 4.1 `Alvoraa Field Device` (existing, `alvoraa_portal`) — changed

| Fieldname | Label | Type | Reqd | Default | Options / rules | Why new |
|---|---|---|---|---|---|---|
| `status` | Status | Select | 1 | Pending | **Options become** `Pending`, `Active`, `Blocked`, `Replaced`, `Removed` | D3 and D10 need statuses of their own |
| `employee` | Employee | Link Employee | 1 | — | **Now `set_only_once`**; controller refuses any change (SEC-9) | existing |
| `join_method` | How it joined | Select | 1 | — | `Web check-in page`, `App QR code`; set by server code only; frozen | Nothing records how a phone arrived (HD-2) |
| `invite` | App code | Link Alvoraa App Invite | 0 | — | read only; frozen; set only by E3 | Links the phone to the HR decision that let it in |
| `app_version` | App version | Data (20) | 0 | — | read only; set at join, updated on each saved punch (never on app open) | Support needs it; `platform` holds the OS only |
| `block_reason` | Why it was blocked | Select | 0 | — | `Phone lost or stolen`, `Has a new phone`, `Someone else was using it`, `Left the company`, `Other`; required when status is Blocked; **never sent to any phone** (PRIV-13) | D7 |
| `replaced_by` | Replaced by | Link Alvoraa Field Device | 0 | — | read only; set by E3 | "Which phone replaced this one" for a grievance |
| `status_changed_on` | Status changed on | Datetime | 0 | — | read only; set on every status change | `modified` also moves on other saves |
| `status_changed_by` | Status changed by | Link User | 0 | — | read only; empty when the employee or the system changed it | `activated_by` covers only Pending → Active |
| `status_change_source` | Changed by | Select | 0 | — | `HR`, `The employee`, `System`; read only | A change by the employee has no desk user |
| `retired_token_hash` | — | Data | 0 | — | hidden, read only, `no_copy`, `search_index`; receives `token_hash` when a phone becomes Blocked, Replaced or Removed | Keeps "why did this phone stop" answerable while the live hash is empty (Read this first 2; Q-2) |
| `last_seen` | **Last punch** (relabel only) | Datetime | — | — | same fieldname, no data change; updated only by a saved punch (PRIV-9) | — |
| `device_label` | Device | Data | — | — | app sends ≤ 80 characters | existing |
| `consent_given_on`, `consent_version` | (unchanged) | — | — | — | never written by new code; kept as history | existing |

A `company` field (fetched from the employee) is added to this doctype and to the invite **only if** the W1 permission test (AC-148) shows it is needed to scope an HR User by company.

**Permission change:** remove `create` and `delete` from HR Manager and System Manager; HR User and HR Manager keep read and write (write is still needed for the web flow Pending → Active). Administrator is not limited by Frappe (noted, not changed).

**Controller rules (same for desk, list edit, Data Import, `frappe.client.set_value`, REST):**

- Insert refused unless the server join code (E3) or `register_device` marks the insert as theirs.
- `employee`, `token_hash`, `retired_token_hash`, `join_method`, `invite`, `registered_on` refused after insert (the server's block, replace and remove code excepted for the two hash fields).
- Status changes a person may make: Pending → Active (web phones only; sets `activated_by`), Pending → Blocked, Active → Blocked (both need `block_reason`). Everything else refused. Replaced and Removed are set only by server code.
- Any move into Blocked, Replaced or Removed moves `token_hash` into `retired_token_hash` in the same save and sets the three `status_changed_*` fields.

### 4.2 `Alvoraa App Invite` — new doctype (`alvoraa_portal`)

Naming: random hash. `track_changes: 1`. No Print Format, no `email` or `print` permission.

| Fieldname | Label | Type | Reqd | Rules |
|---|---|---|---|---|
| `employee` | Employee | Link Employee | 1 | `search_index`, frozen after insert |
| `employee_name` | Employee name | Data | 0 | fetched from the employee, read only |
| `status` | Status | Select | 1 | `Waiting`, `Used`, `Cancelled`, `Ran out`; set by server code only |
| `lifetime_hours` | Works for (hours) | Int | 1 | one of 1, 4, 12, 24, 72, 168; ≤ organisation setting |
| `expires_at` | Works until | Datetime | 1 | server time at insert + lifetime |
| `token_hash` | — | Data | 0 | hidden, `no_copy`, `search_index`; SHA-256 of the code; **emptied the moment the status leaves Waiting** (OPS-52) |
| `used_at` | Used at | Datetime | 0 | set by E3 |
| `used_device` | Phone it set up | Link Alvoraa Field Device | 0 | set by E3 |
| `cancel_reason` | How it was cancelled | Select | 0 | `By HR`, `This is not me (on a phone)`, `Newer code made`, `Employee left` |
| `cancelled_by` | Cancelled by | Link User | 0 | HR user, or empty |
| `cancelled_at` | Cancelled at | Datetime | 0 | — |

Who made it and when: Frappe's own `owner` and `creation` (no new field). The plain code is never stored anywhere.

Permissions: HR Manager, HR User, System Manager — **read and report only**. No role has create, write or delete; rows are written only by server code (E1–E3, E7, E10, leaver hook, daily job).

### 4.3 `Alvoraa Notice Acknowledgement` — new doctype (`alvoraa_portal`)

Insert-only. Naming: random hash.

| Fieldname | Label | Type | Reqd | Rules |
|---|---|---|---|---|
| `employee` | Employee | Link Employee | 1 | `search_index` |
| `device` | Phone | Link Alvoraa Field Device | 0 | — |
| `notice_version` | Notice version | Data | 1 | — |
| `acknowledged_at` | Read on | Datetime | 1 | server time |
| `language` | Language | Select | 1 | `en`, `hi`, `Not recorded` |
| `channel` | Where | Select | 1 | `App`, `Web check-in page`, `Backfill` |
| `app_version` | App version | Data | 0 | — |

Permissions: HR Manager, HR User, System Manager — read and report only. No role has create, write or delete.

### 4.4 `Alvoraa Field Worker Designation` — new child table

| Fieldname | Label | Type | Reqd |
|---|---|---|---|
| `designation` | Designation | Link Designation | 1 |

### 4.5 `HR Settings` (hrms) — custom fields, section "Field attendance app"

Created by `alvoraa_portal` on migrate and on install, the way `field_checkin.after_migrate` adds fields today.

| Fieldname | Label | Type | Default | Rules |
|---|---|---|---|---|
| `alvoraa_field_app_section` | Field attendance app | Section Break | — | — |
| `alvoraa_field_worker_designations` | Field worker designations | Table MultiSelect (4.4) | **empty** | Help: "Only people with these designations can get the app and check in with a photo." |
| `alvoraa_field_app_enabled` | Field workers can use the app | Check | 1 | Help: "When this is off, you cannot make codes, and phones that joined stop marking attendance. Field workers can still use the web check-in page." |
| `alvoraa_app_code_lifetime` | App codes work for | Select | `1 day` | `1 hour`, `4 hours`, `12 hours`, `1 day`, `3 days`, `7 days`. Help: "From 1 hour to 7 days. Shorter is safer. Longer is easier when you hand out printed codes before a joining day. HR can choose a shorter time for one code." |
| `alvoraa_field_app_change_reason` | Why? (kept in the change history) | Select | empty | `Pausing the pilot`, `Field workers use the reception machine again`, `Other`. **Required** when the switch goes from on to off or a designation is removed; emptied after the save (the `Alvoraa Leader View Settings` pattern) |
| `alvoraa_field_app_info` | — | HTML | — | Live counts, photo retention line, last 20 changes to these fields |

*Why custom fields, not a new Single?* `CLAUDE.md` §4 names HR Settings for organisation settings, and it already has `track_changes` and the permissions D20 wants (HR Manager write, HR User read — read in `hr_settings.json`). *Privacy check:* the Employee role can read HR Settings. Nothing here is personal; the reason is a fixed list, not free text.

### 4.6 `Employee Checkin` (hrms) — one custom field

| Fieldname | Label | Type | Rules | Why |
|---|---|---|---|---|
| `alvoraa_mock_location` | Phone reported a fake location | Check | read only, `no_copy`, `in_standard_filter`, default 0 | SEC-21; no existing field carries it |

### 4.7 Notice store (in code, not a doctype)

A versioned table in `alvoraa_portal` code: version → six English rows, a `what_changed` line, later Hindi rows. **Versions are only ever added; an existing version's text never changes** (a test pins it). *Why not a doctype?* The words must be reviewed and shipped with code, and the retention days are filled in per tenant at request time.

New version: the six rows of `01b` §7.7 (adds "When you set up: this phone's model name."; says "HR and your manager. Not your colleagues."). `what_changed`: "We now also record this phone's model name when you set it up." Version string: the ship date, never `2026-09-13`. `CONSENT_VERSION` becomes the new version.

---

## 5 · States and transitions

### 5.1 Phone (`Alvoraa Field Device.status`)

| State | Who can move it | Next states | Read only in this state | Notified | Phone sees |
|---|---|---|---|---|---|
| **Pending** (web page only) | HR User, HR Manager, System Manager | Active, Blocked | employee, hashes, join method | — | "waiting for HR" (`DEVICE_PENDING`) |
| **Active** | HR (block); server (replace, remove, leaver) | Blocked, Replaced, Removed | employee, hashes, join method, invite | Join → code maker (§10) | Attendance screen |
| **Blocked** — final | nobody | none | everything | — | `blocked` |
| **Replaced** — final | nobody | none | everything | — | `replaced` |
| **Removed** — final | nobody | none | everything | "one phone, two people" when the system removed it | first launch |

**Nothing is reversible.** Getting the app back always needs a new code (D4). "Stopped" is not a state: it is shown when an Active **app** phone fails the switch or designation check at the moment of the call, and it clears by itself when the setting is restored.

### 5.2 Code (`Alvoraa App Invite.status`)

| State | Entered by | Next | Hash | Notified |
|---|---|---|---|---|
| **Waiting** | E7 (HR) | Used, Cancelled, Ran out | kept | — |
| **Used** — final | E3 | none | emptied | maker; a rescan from another phone → HR Managers |
| **Cancelled** — final | E10 (By HR), E2 (This is not me), E7 (Newer code made), leaver hook (Employee left) | none | emptied | "This is not me" → maker + HR Managers |
| **Ran out** — final | daily job; also treated as ran out at E1/E3 once `expires_at` has passed | none | emptied | — |


---

## 6 · Endpoint contract

Working names; the engineer names them. **E1–E6 and E9 are guest `POST`, under one module path, wrapped by slice 014's `_private_request`, answer `Cache-Control: no-store`, ignore any session cookie, and share one nginx per-IP zone of 600 a minute, burst 100.** Every number is a starting point to measure at the pilot (07 §3).

| # | Endpoint (screen) | Caller proves itself with | Limit (keyed on the SHA-256 hash) | Body cap | Server p95 | Answer ceiling | Success answer |
|---|---|---|---|---|---|---|---|
| E1 | Check the code (`checking`) — uses nothing | QR token (+ the device secret, if the phone already has one) | 20/hour per code | 16 KB | ≤ 500 ms | 8 KB | `first_name`, `surname_initial`, `designation`, `company`, `brand_colour`, `notice {version, rows, retention_days}`, `min_version` — nothing else |
| E2 | This is not me (`notMe`) | QR token | 5/hour per code | 16 KB | ≤ 500 ms | 1 KB | `{}` |
| E3 | Agree and finish (`joining`) | QR token, `notice_version`, `device_label`, `platform`, optional old device secret | 5/hour per code | 16 KB | ≤ 500 ms | 4 KB | device secret (**the only answer that ever carries it**), `first_name`, `company`, `workplace {name, radius_m}`, `todays_checkins` |
| E4 | App start (extends `field_status`) | Device secret | 60/hour per phone | 16 KB | ≤ 500 ms | 4 KB | `first_name`, `employee_name`, `designation`, `company`, `workplace {name, radius_m}` (**no coordinates**), `checked_in`, `todays_checkins`, `server_time`, `min_version`, `notice_version`, `joined_on` |
| E5 | Punch (extends `field_checkin`) | Device secret + `mock_location` flag | 30/hour per phone | **1 MB** | ≤ 500 ms (at risk: photo write; a miss gets a dated exception) | 4 KB | `log_type`, `time`, `todays_checkins` |
| E6 | Remove this phone (`leaveConfirm`) | Device secret | 5/hour per phone | 16 KB | ≤ 500 ms | 1 KB | `{}` |
| E7 | Make a code (desk) | Session; HR role; read permission on that Employee | 30/hour per HR user | default | ≤ 500 ms | 2 KB | `link` = `https://<site host>/enrol#t=<code>` (**the only answer that ever carries the code**), `expires_at`, `lifetime_hours` |
| E8 | `/enrol` page | none | nginx only | GET | ≤ 300 ms | 10 KB | static page |
| **E9** *(new)* | Agree to a changed notice (`noticeAgain`) | Device secret, `notice_version` | 5/hour per phone | 16 KB | ≤ 500 ms | 1 KB | `{}` |
| **E10** *(new, desk)* | Cancel a waiting code | Session; HR role; permission on the Employee | 30/hour per user | default | ≤ 500 ms | 1 KB | `{}` |
| **E11** *(new, desk)* | Block this phone | Session; HR role; permission on the Employee | 30/hour per user | default | ≤ 500 ms | 1 KB | `{}` |
| **E12** *(new, desk)* | Employee app section data; settings counts | Session; HR role; permission on the Employee | — | default | ≤ 500 ms | 16 KB | state, phones, code history; counts |

`register_device` (web page) keeps its answer shape (slice 014), is not asked for a version header, and writes one acknowledgement row for a real employee.

**Rule for the life of the app (OPS-8):** device endpoints only ever **add** arguments, answer keys and codes. Nothing is renamed or removed while an app version that uses it is supported (90 days after its replacement is available, counted from the first store release; OPS-48, OPS-58).

**Request header:** `X-Alvoraa-App-Version: MAJOR.MINOR.PATCH`, compared as three numbers. No header = the web page, allowed.

---

## 7 · Error-code contract

**The app picks a screen by `code` only.** The JSON body carries `code` and `values`; the English sentence stays in Frappe's `_server_messages` for logs and for today's web page, which still matches text (MA-30). One HTTP status per code, all codes in one server file. **The HTTP statuses are my proposal; the engineer confirms them at strategy, and they are frozen when the first pilot build ships** (Q-6).

### 7.1 Codes the server sends

| Code | HTTP | Sent by | Values | App screen | Try again? |
|---|---|---|---|---|---|
| `QR_NOT_RECOGNISED` *(01c SEC-3)* | 404 | E1, E2, E3 | — | dead-code screen (copy in AC-193) | No |
| `QR_EXPIRED` | 410 | E1, E2, E3 | `expired_at` | `qrExpired` | No |
| `QR_USED` | 410 | E1, E2, E3 | `used_at` | `qrUsed` | No |
| `QR_CANCELLED` | 410 | E1, E2, E3 | — | `qrCancelled` | No |
| `APP_OFF_FOR_FIELD` | 403 | E1, E2, E3, E4, E5, E9, E7 | — | `appOff` | No |
| `NOT_FIELD_ROLE` | 403 | E1, E2, E3, E4, E5, E9, E7 | `designation` | `notField` | No |
| `FEATURE_OFF` | 403 | every device endpoint, E7 | — | `featureOff` (008 screen) | No |
| `NOTICE_CHANGED` | 409 | E3, E4, E5 | `version`, `rows`, `retention_days`, `what_changed` | `noticeAgain` (at E3: the notice again with the new rows) | Agree |
| `APP_TOO_OLD` | 426 | E1–E6, E9 | `min_version` | `update` | Update only |
| `NOT_SET_UP` | 401 | E4, E5, E6, E9 | — | first launch, line "This phone is not set up." | — |
| `DEVICE_PENDING` *(new; one answer for a Pending phone and for a well-formed secret nobody holds — slice 014 rule)* | 401 | E4, E5, E6, E9 | — | first launch, line "This phone is not set up." | — |
| `DEVICE_BLOCKED` | 403 | E4, E5, E6, E9 | — (**never a reason**) | `blocked` | No |
| `DEVICE_REPLACED` | 403 | E4, E5, E6, E9 | `replaced_at` | `replaced` | No |
| `DEVICE_REMOVED` *(01c SEC-10)* | 403 | E4, E5, E6, E9 | `removed_at` | first launch, line "This phone is no longer linked to {company}." | — |
| `EMPLOYEE_NOT_ACTIVE` | 403 | E3, E4, E5, E6, E9 | — | `left` | No |
| `LOCATION_MISSING` *(new)* | 422 | E5 | — | `locOff` | Yes, photo kept |
| `GPS_NOT_EXACT` | 422 | E5 | `accuracy_m`, `limit_m` | `gpsVague` | Yes, photo kept |
| `OUTSIDE_WORKPLACE` | 422 | E5 | `distance_m` (may be empty), `site`, `radius_m` | `outside` | Yes, photo kept |
| `ALREADY_RECORDED` | 409 | E5 | `time` | `duplicate` | No |
| `INVALID_REQUEST` *(new)* | 400 | all | — (no field names) | `serverError` | Yes |
| `TOO_MANY_TRIES` | 429 | all | `retry_after_s` | `tooMany` | Yes, after the wait, photo kept |
| `SERVER_ERROR` | 500 | all | — (no detail) | `serverError` | Yes |

### 7.2 Codes the app makes itself (no server call)

| Code | When | Screen |
|---|---|---|
| `QR_NOT_ALVORAA` | Scanned or picked code fails the host rule | `notAlvoraa` |
| `QR_NOT_FOUND` | No QR in the chosen picture | `pickNoQr` |
| `NO_INTERNET` | No connection; the 30-second timeout; or a 200 HTML page (a Wi-Fi login page) | `noSignalJoin` before joining, `noSignal` after |
| `CAMERA_DENIED` | Camera permission refused | `camDenied` |
| `LOCATION_DENIED` | Location permission refused | `locDenied` |
| `LOCATION_OFF`, `LOCATION_SLOW` | Location off, or no fix within 20 s | `locOff` |

### 7.3 Answers that are not JSON

| Arrives | App shows |
|---|---|
| nginx 429 page | `tooMany`, wait 60 s |
| 413, 502, 503, 504 page | `serverError` |
| 200 HTML page | `noSignal` / `noSignalJoin` |
| JSON with a code this app version does not know | `unknownCode` ("Check for an update", code shown) |

Every problem screen ends with **Code for HR: {CODE}** (D11).

---

## 8 · Permission and visibility matrix

C = create, R = read, W = write, D = delete. Submit and cancel do not apply (none of these doctypes is submittable). "Own-scope" = only employees Frappe's own permission check lets that user read (User Permissions on Employee or Company).

### 8.1 Doctypes

| Role | Alvoraa Field Device | Alvoraa App Invite | Alvoraa Notice Acknowledgement | HR Settings — field app fields | Employee Checkin (unchanged) |
|---|---|---|---|---|---|
| **System Manager / CXO** | R W (rules in 4.1), **no C, no D** | R | R | R W | as today (all) |
| **HR Manager** | R W (rules), **no C, no D**; own-scope | R; own-scope | R; own-scope | **R W** (D20) | as today |
| **HR User** | R W (rules), no C, no D; own-scope | R; own-scope | R; own-scope | R only | as today |
| **Line manager (Employee role)** | none | none | none | R (HR Settings is readable by Employee today; nothing personal in these fields) | own + direct reports (existing hooks) |
| **Employee / colleague** | none | none | none | R (same note) | own only |
| **The phone (guest + secret)** | its own row, through E4–E6, E9 only | — | writes its own rows through E3, E9 | — | creates its own punches through E5 |
| **Guest with a code** | — | its own code's state through E1–E3 | — | — | — |
| **Guest with nothing** | none | none | none | none | none |
| **Administrator** | not limited by Frappe | not limited | not limited | not limited | not limited |

### 8.2 Actions

| Action | System Manager | HR Manager | HR User | Line manager | Employee | Phone |
|---|---|---|---|---|---|---|
| Make a code (E7) | yes | yes, own-scope | yes, own-scope | **no** | no | no |
| Cancel a code (E10) | yes | yes, own-scope | yes, own-scope | no | no | "This is not me" with the live code (E2) |
| Block a phone (E11) | yes | yes, own-scope | yes, own-scope | no | no | no |
| **Unblock** a phone | **no one** | **no** | **no** | no | no | no |
| Activate a Pending **web** phone | yes | yes | yes | no | no | no |
| Change who a phone belongs to | **no one** | no | no | no | no | no |
| Remove a phone | no | no | no | no | no | its own, E6 |
| Change field app settings | yes | **yes** | **no** | no | no | no |
| Access-request report (US-28) | yes | yes, own-scope | yes, own-scope | no | no | no |

### 8.3 Negative cases — who must NOT see what

| Must not | Whom | Enforced by | AC |
|---|---|---|---|
| See the plain code after the dialog closes | everyone, including the HR person who made it | never stored (hash only) | AC-39, AC-50 |
| See the block reason | the employee and their phone | never in any device answer | AC-2, AC-111 |
| See any phone, code or acknowledgement row | colleagues, line managers, guests | doctype permissions, no Employee role rows | AC-150, AC-151 |
| See phones, codes or acknowledgements of employees outside their remit | HR User or HR Manager limited to one company | Frappe permission check on the Employee (W1, tested) | AC-149 |
| See a "last seen", "online now" or map of a worker | everyone | not built; app opens change nothing | AC-77, AC-107, AC-114 |
| See the full name, employee ID, email, phone, date of birth or workplace of a code's owner | whoever holds a code | E1 answer key set | AC-53, AC-54 |
| See a name for a dead or ineligible code | whoever holds a code | E1 answer key set | AC-54, AC-55 |
| See workplace coordinates | the phone | E4 answer | AC-76 |
| See another tenant's code, phone or person | other tenants | one database per site; code tested cross-site | AC-57 |
| See names, employee IDs, phone models or tokens in counts | Alvoraa staff | counter payload keys | AC-131 |


---

## 9 · Epic and user stories

**Epic E-013 · Field workers join by HR's QR and mark attendance with a photo in an Android app, and HR can see and stop each phone.**

**How to read a story.** Each story has a line for its persona and outcome, the prototype screens it builds, the requirements it carries, and its acceptance criteria as Given / When / Then with something a tester can observe. **Line:** *Server* = Frappe code, desk, nginx; *App* = Capacitor app, its build and CI. Points: 1, 2, 3, 5, 8.

**INVEST check, for all stories.** Each story can be tested alone; the server stories can be tested with a script before any app exists. No story is 8 points: the three that were (make a code, join, the join screens) were split. Stories that were only technical were kept because each carries a named `SEC`, `PRIV` or `OPS` item a tester must prove. "Must not" stories are US-2, US-27 and parts of US-8, US-12, US-17.

**Build order**

| Order | Server (Frappe) | App (Capacitor) |
|---|---|---|
| 0 — before anything | — | **US-31** key-file guard (before any key exists) |
| 1 — first server change, never reverted | **US-1**, **US-2**, **US-4**, US-29 (after slice 014 is on dev for any push) | US-32, US-33, US-34 (shell and CI checks) |
| 2 | US-3, US-5, US-7, US-8, US-9, US-10, US-11, US-23, US-26 | US-35, US-36, US-37, US-38 against a local bench (debug build) |
| 3 | US-12, US-13, US-14, US-15, US-6, US-16, US-17, US-18, US-19, US-20 | US-39, US-40, US-41, US-42, US-43, US-44, US-45, US-46 |
| 4 | US-21, US-22, US-24, US-25, US-27, US-28, US-30 | US-47, US-48 |

The app can start in step 1 because the error-code contract (§7) fixes what the server will send. Until the endpoints exist, the app is tested against the local bench.

---

### Server stories (Frappe)

#### US-1 · Only a working phone can punch — Server · 3 pts

*As* **Anita, HR Manager**, *I want* every phone that is not Active refused with its own reason *so that* a replaced, removed or blocked phone can never mark attendance.
Screens: phone `blocked`, `replaced`, first launch. Carries: SEC-10, OPS-28, OPS-50, D3, D10.

| AC | Given | When | Then (oracle) |
|---|---|---|---|
| AC-1 | A phone record with status Pending, **or** a well-formed secret no record holds | E4 or E5 is called with that secret | HTTP 401, code `DEVICE_PENDING`; no `Employee Checkin` row created; both cases give byte-identical bodies |
| AC-2 | Phones with status Blocked, Replaced, Removed | E4, E5, E6 or E9 is called | HTTP 403 with `DEVICE_BLOCKED` (no `reason` key, no block reason text anywhere in the body), `DEVICE_REPLACED {replaced_at}`, `DEVICE_REMOVED {removed_at}`; no row created |
| AC-3 | A missing secret, or one under 20 characters | E4 or E5 is called | HTTP 401, `NOT_SET_UP` |
| AC-4 | The status field's Select options | the test suite runs | a test reads the options and fails if any status other than Active is not refused with a named code |
| AC-5 | An Active phone | it becomes Blocked, Replaced or Removed by any path | in the same save `token_hash` is empty and `retired_token_hash` holds the old hash; the old secret still gets its own code (AC-2), never 200 |
| AC-6 | An Active app phone, app switched on, eligible employee | E5 is called inside the radius | 200 and one `Employee Checkin` row (control case) |

#### US-2 · A phone record cannot be forged, re-pointed, unblocked or deleted — Server · 5 pts

*As* **Suresh, field employee**, *I must not* have my phone record pointed at someone else, unblocked or erased by anyone in HR, *so that* the record of who punched for me stays true.
Screens: desk `blockConfirm`, `empBlocked`. Carries: SEC-8, SEC-9, D4, OPS-30, Q-U6.

| AC | Given | When | Then |
|---|---|---|---|
| AC-7 | A Blocked phone | an HR Manager sets status to Active or Pending through (a) the desk form (b) list bulk edit (c) Data Import update (d) `frappe.client.set_value` (e) REST `PUT` | each is refused with "A blocked phone cannot be switched back on. Make a new code instead."; the row and its Version count are unchanged. Same result for Replaced and Removed |
| AC-8 | HR Manager, HR User and System Manager users (not Administrator) | they insert a phone record by desk or REST, or delete one | both refused (permission error); no row added or removed |
| AC-9 | An existing phone | anyone changes `employee`, `token_hash`, `retired_token_hash`, `join_method`, `invite` or `registered_on` by any path in AC-7 | refused; row unchanged |
| AC-10 | A Pending **web** phone | an HR User sets it Active in the form | saved; `activated_by` = that user; `status_changed_on`, `status_changed_by` set; `status_change_source` = HR |
| AC-11 | An Active or Pending phone | status set to Blocked by form, list edit or import with no `block_reason` | refused "Choose a reason. It is kept in the record."; with a reason: saved, `status_changed_*` set, hash moved as in AC-5 |
| AC-12 | Any phone | a person sets status Replaced or Removed, or Active → Pending | refused; only server code sets Replaced and Removed |
| AC-13 | An app-joined phone | anyone sets `join_method` to `Web check-in page` to unlock web-only rules | refused (AC-9) |

#### US-3 · HR Manager controls who can use the app, with a change history — Server · 5 pts

*As* **Anita, HR Manager**, *I want* to choose the field-worker designations, switch the app on or off, and set how long codes work, with every change recorded, *so that* only field staff get the app and I can stop it in a minute.
Screens: desk `fieldSettings`, `settingsOffConfirm`, remove-a-designation confirm (described in 01b §9.4). Carries: S6, D5, D20, OPS-53, gate decisions 1–3, user decision "24 hours default, up to 7 days".

| AC | Given | When | Then |
|---|---|---|---|
| AC-14 | An existing tenant before this slice | migrate runs | HR Settings shows designations **empty**, "Field workers can use the app" **ticked**, "App codes work for" **1 day**; every HR Settings value that existed before is unchanged (before/after compare) |
| AC-15 | Anita (HR Manager) | she changes any of the three settings and saves | saved; a Version row on HR Settings shows her user, the time, old and new values |
| AC-16 | An HR User, an Employee-role user | they try to save these fields by desk or REST | refused (no write on HR Settings); values unchanged |
| AC-17 | The switch is on, 3 waiting codes and 31 Active app phones exist | Anita unticks it | a confirm shows "3 codes waiting to be used will stop working." and "31 phones that joined will stop marking attendance. They will say: "The app is not switched on for field staff."" plus "Field workers can still use the web check-in page."; the counts equal the database counts; Turn off with no reason shows "Choose a reason. It is kept in the change history."; a REST save that turns it off with no reason is refused by the server too |
| AC-18 | "Driver" is in the list, 12 active Drivers, 9 with Active app phones | Anita removes "Driver" | the same confirm with those counts, reason required, server-enforced |
| AC-19 | A save with a reason | after the save | the Version row holds the reason; the reason field is empty afterwards |
| AC-20 | A REST save | "App codes work for" is any value outside the six options | refused |
| AC-21 | List = [Driver] | eligibility is checked for a Driver / a Store Associate / anyone with an empty list / when HR Settings cannot be read | field worker / not / nobody / nobody (fail closed) |
| AC-22 | A settings save | the next E1, E4, E5 or E7 call comes | it applies the new values; no call more than 60 s after the save uses old values |
| AC-23 | The section | it is shown | "Check-in photos are kept for {days} days, then deleted." (or "Check-in photos are kept until your organisation removes them." for 0); **no link** (Q-4) |
| AC-24 | Changes exist | the section is shown | "Change history" lists the last 20 changes to these fields only, newest first: time, person's name, "App codes work for: 3 days → 1 day", reason; with the line "HR cannot change this list." |
| AC-25 | The designation list | it changes on screen | "{n} active employees have these designations." matches the database count |

#### US-4 · The server speaks in codes old apps can rely on — Server · 5 pts

*As* **Suresh**, *I want* my app to keep showing the right screen after the server is updated, *so that* a Monday deploy does not lock me out.
Screens: every problem screen, `update`. Carries: OPS-8, OPS-26, OPS-27, OPS-44, OPS-48, OPS-49, SEC-19, SEC-24.

| AC | Given | When | Then |
|---|---|---|---|
| AC-26 | Each code in the server codes file | a test triggers it | the body has `code` and `values` with the names in §7.1 and the fixed HTTP status; the English sentence is still in `_server_messages` |
| AC-27 | E1–E6, E9 | called with GET | refused; no database read of invites or phones |
| AC-28 | E1–E6, E9 | any answer, success or refusal | header `Cache-Control: no-store` |
| AC-29 | A device endpoint, minimum version 1.2.0 | header is 1.1.9 / 1.2.0 / missing / `abc` / 25 characters / a version on the security deny-list | 426 `APP_TOO_OLD {min_version:"1.2.0"}` / normal / normal / 426 / 426 / 426; "1.10.0" counts as newer than "1.9.0" |
| AC-30 | E3 or E5 | `device_label` over 80 characters, `platform` not `android` or `ios`, a token or secret over 128 characters, `log_type` not IN or OUT | 400 `INVALID_REQUEST`, no field name in the body, nothing written |
| AC-31 | Fixture data with the English notice | each endpoint answers | sizes are under the ceilings in §6 |
| AC-32 | The full test run | answers are collected | the device secret appears only in E3's success answer and the code only in E7's |
| AC-33 | A contract file for every released app version in CI | CI replays version 1's requests against the current server | only codes in version 1's table come back; otherwise the build fails |
| AC-34 | The server codes file and the app's code table | CI runs | the build fails if a server code is missing from the app's table |
| AC-35 | Today's web check-in page | register → HR activates → punch → refused punch | the same web screens and sentences as before this slice (hand trace plus existing tests) |
| AC-36 | Frappe's own rate limit refuses | the answer is sent | 429 `TOO_MANY_TRIES {retry_after_s}` |
| AC-37 | The minimum-version constant | a commit raises it above a version whose replacement has been out under 90 days, after the first store release | CI fails unless the commit carries the security-exception marker Surbhi approved; before the first store release (pilot) CI allows it |

#### US-5 · HR makes a single-use code for one field worker (server) — Server · 5 pts

*As* **Anita, HR Manager**, *I want* to make a code that only Suresh can use, once, for a limited time, *so that* he can join without me approving his phone later.
Screens: desk `inviteCreate`. Carries: S5, SEC-1, SEC-2, SEC-4, SEC-6, D6, D17, OPS-13, OPS-51, Q-U4.

| AC | Given | When | Then |
|---|---|---|---|
| AC-38 | An HR User who can read Active employee Suresh (Driver, in the list), app on, plan includes field check-in | E7 with lifetime 24 hours | one invite: status Waiting, employee Suresh, `owner` = that user, `lifetime_hours` 24, `expires_at` = server time + 24 h, `token_hash` = SHA-256 of the code; answer `link` = `https://<site host>/enrol#t=<code>`; the code is at least 43 characters |
| AC-39 | A code made in a test | the test searches for it | not in the invite row, `tabVersion`, `tabComment`, `tabNotification Log`, `tabError Log` or the log file |
| AC-40 | Setting = 1 day | E7 asks for 3 days / 30 days / 30 minutes | each refused ("Choose a time up to your organisation's setting of 1 day."); no row |
| AC-41 | Suresh already has a Waiting code | E7 makes another, or two E7 calls arrive together | the old one is Cancelled with reason "Newer code made" and hash emptied; exactly one Waiting code remains |
| AC-42 | Employee not a field worker / app off / plan without field check-in / employee not Active | E7 | `NOT_FIELD_ROLE` / `APP_OFF_FOR_FIELD` / `FEATURE_OFF` / "Only active employees can be invited."; no row |
| AC-43 | An HR User limited to company A; a line manager; an Employee-role user | E7 for an employee in company B / for their report / for anyone | permission error; no row |
| AC-44 | One HR user | the 31st E7 in an hour | 429 `TOO_MANY_TRIES` |
| AC-45 | The invite doctype | reviewed | no Print Format, no `print` or `email` permission, no GET route, no File row and no PDF that carries a code |

#### US-6 · HR hands the code over: show once, print, copy picture — Server (desk) · 3 pts

*As* **Anita**, *I want* to print the code or paste its picture into WhatsApp, *so that* Suresh gets it wherever he is.
Screens: desk `inviteCreate`, `inviteShow`, `printSheet`, `empInvited`. Carries: S7, D6, D14, OPS-32, SEC-2, user decision "Copy link dropped".

| AC | Given | When | Then |
|---|---|---|---|
| AC-46 | `empField`, setting 3 days | Anita presses **Invite to the app** | dialog "Invite Suresh Yadav to the app" with the 01b §9.2 step 1 words; the time choices are 1 hour, 4 hours, 12 hours, 1 day, 3 days (nothing above the setting), preselected 3 days; amber line when a code is waiting; grey line when a phone is Active |
| AC-47 | The dialog | Anita presses **Make the code** | the QR is drawn in the browser from E7's answer (network panel: no other request carries the code); shows "Waiting to be used", "Works once.", "Works until Thu 24 Sep 2026, 10:05 am (in 1 day)", "Made by you today at 10:05 am", the three steps, the amber warning, the grey "You can see this code only now."; buttons **Print**, **Copy picture**, **Done**; **no "Copy link"** |
| AC-48 | The code is shown | Anita presses **Copy picture** | the picture is on the clipboard; message "Picture copied. Paste it in WhatsApp to Suresh." |
| AC-49 | The code is shown | Anita presses **Print** | the browser prints one A4: company, "Your Alvoraa app code", "For Suresh Yadav", "Driver", the QR, three steps in English, "This code works once, until {date, time}. Do not share it. If this sheet is lost, tell HR."; **no employee ID**; no Hindi in the pilot (D15) |
| AC-50 | Anita closed the dialog | she reopens the Employee | `empInvited` with "This code cannot be shown again. If Suresh lost it, make a new one. That cancels this one."; no control shows the QR again |

#### US-7 · HR cancels a waiting code — Server · 2 pts

*As* **Anita**, *I want* to cancel a code I sent to the wrong person, *so that* nobody else can join as Suresh.
Screens: desk `cancelConfirm`. Carries: SEC-7.

| AC | Given | When | Then |
|---|---|---|---|
| AC-51 | Suresh has a Waiting code | Anita presses **Cancel this code** and confirms (E10) | invite Cancelled, `cancel_reason` By HR, `cancelled_by` Anita, `cancelled_at` set, hash emptied; history reads "Cancelled by you, 17 Sep 2026" (her name for other readers); E1 with that code → 410 `QR_CANCELLED` |
| AC-52 | An HR User without permission on Suresh | E10 | permission error; invite still Waiting |

#### US-8 · The app checks a code without using it — Server · 5 pts

*As* **Suresh**, *I want* to know whether the code works and whether it is mine before I read anything, *so that* I never agree to a notice for a join that cannot work.
Screens: `checking`, `confirm`, `qrExpired`, `qrUsed`, `qrCancelled`, `appOff`, `notField`. Carries: SEC-3, SEC-15, PRIV-5, D8, OPS-24.

| AC | Given | When | Then |
|---|---|---|---|
| AC-53 | A live code for eligible Suresh Yadav | E1, twice | 200 with exactly the keys `first_name` (Suresh), `surname_initial` (Y), `designation`, `company`, `brand_colour`, `notice`, `min_version`; the body has no employee ID, full name, email, mobile, date of birth or workplace; the invite is still Waiting after both calls |
| AC-54 | Codes that ran out, were used, were cancelled, or were never made | E1 | 410 `QR_EXPIRED {expired_at}` / 410 `QR_USED {used_at}` / 410 `QR_CANCELLED` / 404 `QR_NOT_RECOGNISED`; no name, phone model or place in any of them |
| AC-55 | A live code whose employee is not a field worker / app off / plan off | E1 | 403 `NOT_FIELD_ROLE {designation}` / `APP_OFF_FOR_FIELD` / `FEATURE_OFF`; no name keys |
| AC-56 | An employee with no last name | E1 | `surname_initial` is empty |
| AC-57 | A code made on site A | E1, E2, E3 are sent to site B | 404 `QR_NOT_RECOGNISED`; nothing written on either site |
| AC-58 | A Waiting code whose `expires_at` passed one second ago (job not yet run) | E1 | 410 `QR_EXPIRED` |
| AC-59 | One code | the 21st E1 in an hour | 429 `TOO_MANY_TRIES` |
| AC-60 | A Waiting code whose employee is no longer Active | E1 | 410 `QR_CANCELLED`; the invite becomes Cancelled, reason Employee left |

#### US-9 · "This is not me" cancels the code — Server · 2 pts

*As* **Ramesh, a driver who got Suresh's code by mistake**, *I want* to cancel it from my phone, *so that* it cannot be used in the wrong hands.
Screens: `notMe`, `notMeDone`. Carries: D2, SEC-7.

| AC | Given | When | Then |
|---|---|---|---|
| AC-61 | A live code | E2 | 200; invite Cancelled, reason "This is not me (on a phone)", `cancelled_at` set, hash emptied; the US-19 alert is queued |
| AC-62 | A dead or unknown code | E2 | the same code as E1 would give; nothing changes; no alert |
| AC-63 | One code | the 6th E2 in an hour | 429 |

#### US-10 · "Agree and finish" joins the phone at once — Server · 5 pts

*As* **Suresh**, *I want* my phone set up the moment I agree, *so that* I can check in without waiting for HR.
Screens: `joining`, `welcome` (WOW). Carries: S5, SEC-5, OPS-51, PRIV-1, brief §7.

| AC | Given | When | Then |
|---|---|---|---|
| AC-64 | A live code for eligible Suresh, current notice version, `device_label` "Redmi 12", `platform` android, header 1.0.0 | E3 | in one save: invite Used with `used_at` and `used_device`; a new phone Active, `join_method` App QR code, `invite` set, `device_label` Redmi 12, `app_version` 1.0.0, `token_hash` set; one acknowledgement row (version, time, `en`, App, that phone); answer 200 with the secret, first name, company, workplace name and radius, empty punches; **no Pending state at any moment** |
| AC-65 | One live code | two E3 calls arrive at the same moment on two database connections | exactly one 200; the other 410 `QR_USED`; exactly one new phone row |
| AC-66 | A forced failure after the phone row is inserted | E3 | 500 `SERVER_ERROR`; no phone row, no acknowledgement row; invite still Waiting |
| AC-67 | The notice version sent is older than the current one | E3 | 409 `NOTICE_CHANGED` with the new rows; nothing written; invite Waiting |
| AC-68 | Between E1 and E3: the app was switched off / Suresh's designation changed / the code ran out / Suresh was set Left | E3 | `APP_OFF_FOR_FIELD` / `NOT_FIELD_ROLE` / `QR_EXPIRED` / `EMPLOYEE_NOT_ACTIVE`; nothing written |
| AC-69 | E3 body also carries `imei`, `android_id`, `serial` | E3 succeeds | none of these values is stored in the phone row, the acknowledgement row or anywhere else searched |
| AC-70 | E3 and E7 for the same employee at the same moment | both run | both finish with no deadlock error; afterwards there is at most one Waiting code and at most one Active app phone |

#### US-11 · One working app phone per person — Server · 3 pts

*As* **Anita**, *I want* a new phone to stop the old one by itself, *so that* a lost old phone cannot keep punching.
Screens: `replaced`. Carries: D3, SEC-14 (shared phone part), abuse case A10.

| AC | Given | When | Then |
|---|---|---|---|
| AC-72 | Suresh has Active app phone A | he joins on phone B with a new code (E3) | in the same save A is Replaced, `replaced_by` = B, `status_changed_on` set, hash moved; A's next E4 → 403 `DEVICE_REPLACED {replaced_at}` |
| AC-73 | Suresh also has an Active **web-page** phone W | B joins | W stays Active (as 01c SEC-5 says; Q-3 asks whether it should be replaced too) |
| AC-74 | Phone P holds Suresh's secret | Ramesh joins on P with his own code, and the app sends Suresh's secret | Suresh's phone record becomes Removed, `status_change_source` System; the "one phone, two people" alert is queued (US-19); Ramesh's new phone is Active |
| AC-75 | Phone P holds Suresh's own secret | Suresh joins again on P with a new code | the old record becomes Replaced; **no** "two people" alert |

(AC-71 intentionally not used; numbering kept stable.)

#### US-12 · The app start answer — Server · 3 pts

*As* **Suresh**, *I want* the app to show today's state as soon as I open it, *so that* I know whether I am checked in.
Screens: `home`, `homeIn`, `homeOut`, `appOff`, `notField`, `left`, `noticeAgain`. Carries: OPS-24, PRIV-6, PRIV-9, D5, OPS-53.

| AC | Given | When | Then |
|---|---|---|---|
| AC-76 | An Active eligible app phone | E4 | 200 with only the keys in §6; `workplace` has `name` and `radius_m` and **no latitude or longitude**; body ≤ 4 KB |
| AC-77 | An Active phone | E4 is called 5 times | `last_seen` (Last punch), `checkin_count` and `modified` of the phone are unchanged |
| AC-78 | An Active **app** phone | the switch is turned off / its employee's designation leaves the list; then it is restored | next E4 → 403 `APP_OFF_FOR_FIELD` / `NOT_FIELD_ROLE {designation}`; after restoring, next E4 → 200 with no new code; the phone row's Version count never changed |
| AC-79 | An Active **web-page** phone, switch off, employee not a field worker | E4 | 200 (web phones keep working, brief Q4) |
| AC-80 | An app phone whose latest acknowledgement is an older notice version | E4 | 409 `NOTICE_CHANGED {version, rows, retention_days, what_changed}` |
| AC-81 | The plan no longer includes field check-in | E4 from an app phone and a web phone | 403 `FEATURE_OFF` for both |
| AC-82 | One phone | the 61st E4 in an hour | 429 |
| AC-83 | An Active phone whose employee is now Left but the phone not yet blocked | E4 | 403 `EMPLOYEE_NOT_ACTIVE` |

#### US-13 · A punch from the app — Server · 3 pts

*As* **Suresh**, *I want* my check-in saved with my photo and place, and a fake position marked, *so that* HR can trust my attendance.
Screens: `punching`, `resultIn`, `resultOut`, `gpsVague`, `outside`, `duplicate`, `tooMany`, `locOff`. Carries: SEC-21, PRIV-14, OPS-21 (server limit), G1–G3.

| AC | Given | When | Then |
|---|---|---|---|
| AC-84 | An Active eligible app phone within the radius, accuracy 20 m, a 50 KB JPEG, mock flag false | E5 IN | one `Employee Checkin`: `device_id` alvoraa-field-app, server time, latitude, longitude, accuracy, `alvoraa_field_device`, `alvoraa_mock_location` 0, a private photo file; phone's Last punch, count and `app_version` updated; answer has `log_type`, `time`, `todays_checkins` |
| AC-85 | Mock flag true | E5 | punch saved with `alvoraa_mock_location` 1; HR can filter the Employee Checkin list on "Phone reported a fake location" |
| AC-86 | No latitude / accuracy 140 m (limit 100) / 380 m from a 100 m site / no shift location distance available / a second IN within 60 s | E5 | 422 `LOCATION_MISSING` / 422 `GPS_NOT_EXACT {accuracy_m:140, limit_m:100}` / 422 `OUTSIDE_WORKPLACE {distance_m:380, site, radius_m:100}` / `OUTSIDE_WORKPLACE` with empty `distance_m` / 409 `ALREADY_RECORDED {time}`; no new row in each refused case |
| AC-87 | A photo over 400 KB or not a JPEG | E5 | punch saved without a photo (existing rule); no Error Log or log file line holds the photo text (slice 014) |
| AC-88 | One phone | the 31st E5 in an hour | 429 `TOO_MANY_TRIES` |
| AC-89 | An app punch with a photo | Anita opens it | one `Alvoraa Photo Access Log` row (existing) |
| AC-90 | Suresh's line manager and a colleague | they open the punch | the manager can, the colleague cannot (existing hooks unchanged) |
| AC-91 | E5 from a phone in any state covered by AC-78 to AC-83 | E5 | the same code as E4 would give; no row created |

#### US-14 · A new notice version, and a history of who read which words — Server · 5 pts

*As* **Suresh**, *I want* to be told when what the app records changes, and to read it again, *so that* I always know what is kept about me.
Screens: `notice`, `noticeAgain`, `records`; web page notice and result. Carries: D19, FC-2, FC-3, PRIV-2, PRIV-3, PRIV-4, OPS-31, user decision "notice, not consent".

| AC | Given | When | Then |
|---|---|---|---|
| AC-92 | The new notice version | E1, E4 (`NOTICE_CHANGED`) or the records screen needs rows | the six rows equal `01b` §7.7 (with "When you set up: this phone's model name." and "HR and your manager. Not your colleagues."), with `{days}` from the tenant; the version is not `2026-09-13` |
| AC-93 | The old version `2026-09-13` | a test reads it from the notice store | its rows are returned and equal a pinned copy |
| AC-94 | An app phone acknowledged the old version | E9 with the current version | a new acknowledgement row; the old row unchanged; next E4 → 200. E9 with a stale version → 409 `NOTICE_CHANGED` |
| AC-95 | The web page at `/checkin` after deploy | it is opened | its notice shows the same six rows as the current version, and the result screen says "Only HR and your manager can see this." (FC-2); a real registration writes one acknowledgement row with channel Web check-in page |
| AC-96 | A web phone registered under `2026-09-13` | it punches after deploy | the punch is saved; no `NOTICE_CHANGED` for web phones (OPS-31 option chosen: app phones only) |
| AC-97 | App strings, desk strings, notice rows | a string check runs | none contains "consent", "I consent" or "I agree to"; the tick box reads "I have read this and I understand." (code field names may keep "consent") |
| AC-98 | Acknowledgement rows | HR Manager, HR User or System Manager try to write or delete one by desk or REST | refused; they can read rows only for employees they can read |

#### US-15 · The employee removes their own phone — Server · 2 pts

*As* **Suresh**, *I want* to remove my company from this phone, *so that* it stops marking attendance for me.
Screens: `leaveConfirm`, `removed`. Carries: SEC-22, D10.

| AC | Given | When | Then |
|---|---|---|---|
| AC-99 | An Active app phone | E6 | 200; phone Removed, `status_change_source` The employee, `status_changed_on` set, hash moved; the Employee section shows "Removed by Suresh, 17 Sep 2026" |
| AC-100 | A Blocked or Replaced phone | E6 | its own code (AC-2); no change |
| AC-101 | One phone | the 6th E6 in an hour | 429 |


#### US-16 · HR sees the app state on the Employee record — Server (desk) · 5 pts

*As* **Anita, HR Manager**, *I want* to see on Suresh's record whether he has a code waiting, which phone joined, how and when, *so that* I can sort out a problem in one place.
Screens: desk `empField`, `empInvited`, `empJoined`, `empBlocked`, `empNotField`, `empAppOff`, plan-has-no-field-check-in state (01b §9.1). Carries: S7, D13, HD-1, HD-2, PRIV-9, brief Q4 default.

| AC | Given | When | Then |
|---|---|---|---|
| AC-102 | A user with HR Manager, HR User or System Manager and read permission on Suresh | they open his Employee record | tab Attendance & Leaves shows the section "Field attendance app" with "The Alvoraa phone app for field workers: photo check-in with place and time." |
| AC-103 | Each state in 01b §9.1 | the section is shown | the status line and actions are exactly as in that table: not joined + **Invite to the app**; code waiting + "Works until **Thu 24 Sep 2026, 10:05 am** (in 7 days)" + **Make a new code** · **Cancel this code**; joined + **Invite to the app again**; blocked + **Invite to the app**; not a field worker — no Invite button, link "Change field worker designations" to the HR Settings section; app off — no Invite button, link to the section; plan without field check-in — "Field check-in is not part of your plan." and no buttons |
| AC-104 | Anita made the code; Vikram (HR User) opens the same record | the joined line is shown | Anita reads "Joined 9:01 am today · Redmi 12 · by the QR code you made yesterday"; Vikram reads "… by the QR code Anita Rao made yesterday" (D13) |
| AC-105 | Suresh has phones in several states | the phones table is shown | columns Phone (model / platform · app version), How it joined ("QR code made by {you / name}, {date}" or "Web check-in page, approved by {name}, {date}"), Joined, Last punch (time, place name), Status (dot **and** word: Active, Waiting for HR, Blocked, Replaced, Removed, Stopped); **Block this phone** on Active and Pending rows only; "Stopped" shown for an Active app phone failing the switch or designation check |
| AC-106 | A web-page phone of a non-field worker | the table is shown | an extra pill "Not a field worker" with "Joined before this rule. Keeps working." |
| AC-107 | Any state | the section and table are shown | no column, word or icon for "last seen", "online", "active now" or a map; opening the app (E4) changes nothing shown |
| AC-108 | Suresh has codes | the code history is shown | one line per code: when made, who made it and for how long, outcome "Waiting to be used · until {date}" / "Used {date, time} on {phone}" / "Cancelled by {you / name}, {date}" / "Cancelled on a phone: "This is not me", {date}" / "Ran out {date}" / "Replaced by a newer code, {date}" / "Cancelled: left the company, {date}" |
| AC-109 | An employee with 10 phones and 30 codes, Typical volume | the record opens | the section's data call (E12) returns in ≤ 500 ms p95 and the section is drawn within 1.5 s p95; an Employee-role user calling E12 is refused |

#### US-17 · HR blocks a phone, with a reason — Server · 3 pts

*As* **Anita**, *I want* to stop a lost phone in one action and record why, *so that* nobody can punch for Suresh with it.
Screens: desk `blockConfirm`, `empBlocked`; phone `blocked`. Carries: D4, D7, PRIV-13.

| AC | Given | When | Then |
|---|---|---|---|
| AC-110 | An Active phone "Redmi 12" | Anita presses **Block this phone** | dialog "Block Redmi 12?" with the 01b §9.3 lines including "**This cannot be undone.** If Suresh gets the phone back, make a new code."; reason list Phone lost or stolen / Has a new phone / Someone else was using it / Left the company / Other; hint "Kept in the record. Suresh does not see the reason."; **Block this phone** with no reason → "Choose a reason. It is kept in the record." under the field; E11 without a reason is refused by the server too |
| AC-111 | A reason is chosen | Anita blocks (E11) | status Blocked, `block_reason`, `status_changed_by` Anita, `status_change_source` HR, hash moved; status line "Redmi 12 was blocked today at 11:40 am by you · Phone lost or stolen"; the phone's next E4 or E5 → 403 `DEVICE_BLOCKED` whose body contains no reason text |
| AC-112 | A Blocked phone | the section and the device form are shown | there is no "Unblock" or "Activate" action anywhere; the only way forward is **Invite to the app** |
| AC-113 | A Pending web-page phone | Anita blocks it with a reason | same result as AC-111 |

#### US-18 · HR sees all app phones in one list — Server (desk) · 2 pts

*As* **Anita**, *I want* one list of phones for rollout days and lost phones, *so that* I can find a phone without opening each employee.
Screens: desk `deviceList`. Carries: S7, PRIV-9, HD-1.

| AC | Given | When | Then |
|---|---|---|---|
| AC-114 | The phone list view | Anita opens it | columns Employee, Phone, How it joined, Joined, Status (with block reason or date); default filter "Joined in the last 7 days"; page size 20; line under the list "There is no "last seen" column or map, on purpose."; no Last punch, online or map column |
| AC-115 | An HR User limited to company A | the list opens | only phones of employees they can read (US-27) |

#### US-19 · HR is told when something needs a look — Server · 5 pts

*As* **Anita**, *I want* to be told when a code is used, refused by the person, or scanned again by someone else, *so that* I notice a stolen code the same day instead of when I happen to look.
Screens: desk bell (Notification Log). Carries: SEC-13, SEC-12 (spike alert), user answer "data alerts to the customer's HR". Copy in §10.

| AC | Given | When | Then |
|---|---|---|---|
| AC-116 | Anita made Suresh's code | Suresh joins (E3) | one Notification Log for Anita with the §10 N1 subject and body; no email unless Anita's notification settings have email on |
| AC-117 | Anita made the code; Vikram and Meera are HR Managers who can read Suresh; Farah is an HR Manager limited to another company | "This is not me" (E2) | N2 to Anita, Vikram and Meera; **not** to Farah; not to Suresh |
| AC-118 | Suresh's code was used by phone A | E1 is called for that code from a phone that does not send phone A's secret | N3 to HR Managers who can read Suresh; a second such scan within the hour sends nothing more |
| AC-119 | The "one phone, two people" case (AC-74) | E3 completes | N4 to HR Managers who can read both employees |
| AC-120 | Starting threshold 50 an hour | the 51st refused or unknown code check on the site within an hour | N5 to HR Managers of the tenant, at most one an hour; the same count goes to the daily counts (US-22) |
| AC-121 | Every alert above | a test reads subject and body | none holds the code, a secret, a hash, a photo, coordinates or a block reason; recipients are enabled users only |
| AC-122 | Sending an alert fails | during E2 or E3 | the join or cancel is still saved; the alert is sent after the save, on the `short` queue |

#### US-20 · The `/enrol` page never uses a code — Server · 2 pts

*As* **Suresh**, *I want* a plain page telling me to use the app if I scan HR's code with my phone camera, *so that* I know what to do, and my code is not used or exposed.
Screens: `/enrol` (brief S13; copy drafted here, not in 01b). Carries: S13, SEC-2, abuse case A19, OPS-32.

| AC | Given | When | Then |
|---|---|---|---|
| AC-123 | A live code | `/enrol#t=<code>` is opened in Chrome | the page shows "**Open the Alvoraa app to use this code**" / "This code sets up the Alvoraa attendance app. Open the app, press "Scan the QR code from HR", and scan it again. If you do not have the app, ask HR." ; `noindex` in a meta tag and `X-Robots-Tag` header; the network panel shows no request carrying the code; the address bar no longer shows `#t=…`; the invite is still Waiting |
| AC-124 | A live code | `/enrol?t=<code>` is requested | no database read of invites (query log); invite still Waiting |
| AC-125 | The page's HTML | it is checked | no URL to any other host (no fonts, scripts, images or analytics from outside) |

#### US-21 · Old codes run out and old data is cleaned — Server · 3 pts

*As* **Anita**, *I want* codes that ran out marked as such and dead secrets removed, *so that* nothing old can be used and the history I need is kept.
Carries: OPS-52, PRIV-10, brief S5 (changed), Q-1.

| AC | Given | When | Then |
|---|---|---|---|
| AC-126 | Waiting codes past `expires_at` | the daily job runs | they become Ran out with hash emptied |
| AC-127 | The job has run | it runs again at once | nothing changes; the log line holds counts only |
| AC-128 | A code not Waiting, or a phone not Active or Pending, still holding a live hash (seeded) | the job runs | its self-check count is above 0 and the technical alert fires (US-22) |
| AC-129 | Per Q-1 default | the job runs | codes that never set up a phone and ended more than 12 months ago are deleted; Used codes whose phone has any `Employee Checkin` are kept; phones and acknowledgement rows with any linked `Employee Checkin` are kept; anything linked to a punch on legal hold is kept |
| AC-130 | 5,000 seeded rows | the job runs | it runs on the `default` queue and commits at most 500 rows at a time |

#### US-22 · Daily counts and technical alerts reach Alvoraa, with no names — Server · 5 pts

*As* **Surbhi, for Alvoraa**, *I want* daily counts per site and alerts when the app is failing, *so that* the pilot has numbers and a broken version is seen before a tester complains.
Carries: OPS-34, OPS-59, OPS-61, PRIV-11, success measures 1–4, user answer "technical alerts to Alvoraa (Surbhi)".

| AC | Given | When | Then |
|---|---|---|---|
| AC-131 | A tenant site | the daily health pull runs | counts per site are sent for: joins completed; code checks refused by code (including not recognised); "This is not me" cancels; codes made, cancelled, ran out; punches saved by app version; punch refusals by code and app version; `APP_TOO_OLD` answers; app starts by app version; rate-limit refusals (Frappe and nginx 429); 5xx on device paths; photo size p50 and p95 by app version. **Payload keys and values hold no name, employee ID, phone record name, phone model or token** (scanner test) |
| AC-132 | A scripted run of each outcome once | counters are read | each moved by exactly one |
| AC-133 | Seeded conditions on the local bench | the checks run | each alert fires once to Surbhi through the control plane: clean-up job failed or found a live hash; more than 5 server errors an hour on device paths for one site; punch refusals above 10% of punches in a day for one app version; refused code checks above the threshold |
| AC-134 | Counter rows | 13 months pass | older rows are removed |

#### US-23 · A leaver's codes and phones stop — Server · 2 pts

*As* **Anita**, *I want* a leaver's waiting codes cancelled and phones blocked when I mark them Left, *so that* nobody punches for someone who has gone.
Carries: SEC-7, abuse case A18, existing `block_devices_for_leaver`.

| AC | Given | When | Then |
|---|---|---|---|
| AC-135 | Suresh has one Active phone, one Pending web phone and a Waiting code | HR sets his status to Left | both phones Blocked, reason Left the company, `status_changed_by` that HR user, hashes moved; the code Cancelled, reason Employee left, hash emptied |
| AC-136 | Suresh is rehired (status Active again) | HR saves | the phones stay Blocked and the code stays Cancelled; **Invite to the app** is offered |

#### US-24 · nginx protects the device paths — Server · 3 pts

*As* **Surbhi**, *I want* the device paths to refuse huge requests and never allow cross-site logged-in calls, *so that* a guest endpoint cannot be used to load the server or reach the portal.
Carries: OPS-45, OPS-47, OPS-1, OPS-2, SEC-18. **Changes the nginx that also serves production: needs Surbhi's go-ahead before any push.**

| AC | Given | When | Then |
|---|---|---|---|
| AC-137 | The new nginx file on the local bench | a 2 MB body is posted to the punch path, and a 20 KB body to E1 | both get 413 and Frappe receives neither; answers from the new location blocks carry the same security headers as other paths; `nginx -t` passes in a throwaway container |
| AC-138 | Site and common config | a bench test reads them | `allow_cors` is not set; a preflight from `Origin: https://example.org` to `/api/method/frappe.auth.get_logged_user` gets no `Access-Control-Allow-Origin`; if the nginx CORS option is chosen, a preflight from `capacitor://localhost` to a non-device path gets none, and device-path answers have no `Access-Control-Allow-Credentials` |
| AC-139 | A logged-in HR session cookie and no secret | E4, E5 or E1 is called | refused as `NOT_SET_UP` / `QR_NOT_RECOGNISED`; the session is ignored |

#### US-25 · A busy depot is not refused, and answers stay fast — Server · 5 pts

*As* **Suresh at a depot with 400 drivers on one Wi-Fi**, *I want* my 9 am check-in accepted, *so that* I am not marked absent because others punched at the same time.
Carries: OPS-10, OPS-29, OPS-46, OPS-62, SEC-12.

| AC | Given | When | Then |
|---|---|---|---|
| AC-140 | 400 simulated phones from **one** IP on the local bench | 160 requests a minute for 5 minutes across E4 and E5 | zero 429 answers; p95 ≤ 500 ms |
| AC-141 | After all tests | Redis keys are listed | no key contains a raw code or secret; limit keys use the hash |
| AC-142 | Typical volume (250 employees, 90 days of punches) | each endpoint E1–E7, E9–E12 runs | its query count equals the ceiling set at the first green run; the build fails if it rises; no query runs inside a loop |
| AC-143 | Typical volume | timed tests run | p95 ≤ 500 ms for each endpoint; a miss on E5 is recorded as a dated exception in the implementation notes |
| AC-144 | The nginx file | read by a test | the device path zone is 600 a minute, burst 100, keyed on the real address |

#### US-26 · No code, secret, photo, place or name reaches a log — Server · 3 pts

*As* **Suresh**, *I want* my photo and position kept only on my attendance record, *so that* they are not copied into logs that nobody deletes.
Carries: SEC-11, SEC-25, OPS-20 (owned by slice 014), OPS-43, OPS-60.

| AC | Given | When | Then |
|---|---|---|---|
| AC-145 | The release checklist | before any E1–E12 code is pushed to dev | it lists slice 014's commits as already on `origin/dev` |
| AC-146 | E1, E2, E3, E5, E6, E9, each wrapped by `_private_request` | a forced 5xx with canary code, secret, photo, coordinates and name | no canary in `frappe.log`, the Error Log, Version rows or Redis keys |
| AC-147 | The full test suite and a scripted pilot day on the local bench | a scanner searches logs, nginx access logs, Version, Redis and counters | no code, secret, photo text, coordinates or employee name found |
| AC-148 | The implementation notes | the reviewer counts `ignore_permissions` in the diff | every new use is listed with a one-line reason and the count matches |

#### US-27 · Must not: people outside HR's remit, colleagues and managers see nothing new — Server · 3 pts

*As* **Suresh**, *I must not* have my phone, codes or acknowledgements visible to colleagues, my manager, or HR people who do not look after my company, *so that* only the right HR people know how I mark attendance.
Carries: 01c §3 access intent, abuse case A20, W1, Q-U4.

| AC | Given | When | Then |
|---|---|---|---|
| AC-149 | An HR User with a User Permission for company A; Suresh is in company B | they list or open by name, or call REST, on phones, codes or acknowledgements of Suresh; or call E7, E10, E11, E12 for him | nothing listed; open and REST refused (403); actions refused |
| AC-150 | Suresh's line manager and a colleague (Employee role) | they list, open or call REST on the three doctypes | nothing listed; 403 |
| AC-151 | A guest | `/api/resource/` on the three doctypes | 403 |
| AC-152 | HR Manager | tries create, write or delete on codes or acknowledgements by any path | refused |

#### US-28 · HR can answer "what does the app hold about me?" — Server · 2 pts

*As* **Anita**, *I want* one report of a person's phones, codes and acknowledgements, *so that* I can answer Suresh's request to see what is recorded.
Carries: PRIV-12.

| AC | Given | When | Then |
|---|---|---|---|
| AC-153 | Report "Field app records for one employee" (Script Report, HR roles) | Anita runs it for Suresh (employee filter required) | three blocks: phones (model, how joined, joined, status, last punch), codes (made, by, outcome — **no hash**), acknowledgements (version, date, where); only Suresh's rows; it can be exported; an HR User without permission on Suresh gets nothing |

#### US-29 · Existing tenants move over safely — Server · 3 pts

*As* **Surbhi**, *I want* the migration to leave existing phones working and nobody newly eligible, *so that* deploying the code changes nothing until a tenant switches it on.
Carries: migration (§13), OPS-50, OPS-53, PRIV-3.

| AC | Given | When | Then |
|---|---|---|---|
| AC-154 | Existing phone rows | migrate runs, then runs again | each gets `join_method` Web check-in page; Pending and Active keep status and hash; Blocked rows have their hash moved to `retired_token_hash`; second run changes nothing |
| AC-155 | Existing phones with `consent_version` set | migrate runs twice | exactly one acknowledgement row per phone: that version, `acknowledged_at` = `consent_given_on`, channel Backfill, language Not recorded |
| AC-156 | A test site where Role Permission Manager gave HR Manager create and delete on the phone doctype | migrate runs | afterwards HR Manager cannot create or delete (AC-8 passes) |
| AC-157 | Migrate and a fresh `bench install-app` | each runs twice | the HR Settings fields, the child doctype and `alvoraa_mock_location` exist once each |
| AC-158 | HR Settings with slice 010's review settings | HR Manager saves any HR Settings change | both `alvoraa_goals` and `alvoraa_portal` validate hooks run and the save succeeds |
| AC-159 | The implementation notes | read | they state that rollback is the switch (US-30) and a code revert never goes back past US-1 |

#### US-30 · Roll out by the switch; roll back without a deploy — Server · 2 pts

*As* **Surbhi**, *I want* "deployed" and "switched on" to be two separate steps, *so that* I can stop the pilot in under a minute.
Carries: OPS-53, OPS-64, OPS-65.

| AC | Given | When | Then |
|---|---|---|---|
| AC-160 | Server code on dev with the empty designation list | HR tries to invite anyone | E7 → `NOT_FIELD_ROLE`; the web check-in page works as before |
| AC-161 | The demo tenant with designations picked (a dev-stage action on Surbhi's word) | untick the switch, then tick it again, **before the first tester joins** | within 60 s joined app phones get `APP_OFF_FOR_FIELD` at E4 and E5 and waiting codes get it at E1; a web phone still punches; after ticking, the same app phones work with no new code |
| AC-162 | The release checklist | read | it lists OPS-64 steps 1–8 in order, each with a line for Surbhi's word |


---

### App stories (Capacitor, build and CI)

#### US-31 · No signing key can reach the public repo — App · 2 pts

*As* **Surbhi**, *I want* key files blocked from the repo before anyone makes a key, *so that* a key is never published by mistake.
Carries: OPS-6, OPS-37, SEC-23. **First story of the slice.**

| AC | Given | When | Then |
|---|---|---|---|
| AC-163 | `.gitignore` and CI on `dev` | a throwaway branch force-adds an empty `test.jks` (and, separately, `google-services.json`) | CI fails on the tracked-file check; `.gitignore` holds every pattern in OPS-37; a pinned secret scanner runs on every push and pull request; the date these land on dev is earlier than the date the first key is made (both written in the implementation notes) |
| AC-164 | GitHub repo settings | Surbhi checks them | push protection is on (Surbhi's action, recorded with a date) |

#### US-32 · Three kinds of build, each with its own rules — App · 5 pts

*As* **Surbhi**, *I want* debug, pilot and release builds kept apart, *so that* a test setting never reaches a worker's phone and every build can be traced to its code.
Carries: OPS-5, OPS-15, OPS-38, OPS-39, OPS-40, OPS-41, user decision "Bitwarden, plus offline copy".

| AC | Given | When | Then |
|---|---|---|---|
| AC-165 | The three build types | built | app IDs end `.debug`, `.pilot`, and the store ID; all three install side by side on one phone |
| AC-166 | The debug build | its network settings are read | plain HTTP is allowed only to the named local bench address, never the server's address |
| AC-167 | The pilot workflow | someone starts it | it runs only by hand, from a commit on `dev`, in environment `mobile-pilot` that needs Surbhi's approval; the release workflow refuses any commit not on `main` |
| AC-168 | Two builds | CI compares versions | it fails if `versionCode` does not rise, or `versionName` is not `MAJOR.MINOR.PATCH`; `versionCode` = MAJOR × 1,000,000 + MINOR × 10,000 + PATCH × 100 + build number |
| AC-169 | One commit | CI builds it twice | same version, same permission list, same bundled file hashes; the lock file is committed and `npm ci` used; tool versions pinned in one file |
| AC-170 | Before the pilot | the second key holder restores the pilot key from Bitwarden or the offline copy and signs a build | its SHA-256 fingerprint equals the one recorded in the repo |
| AC-171 | The build | CI reads the target Android level | it meets Google Play's current requirement (API 36 today, OPS-15) |

#### US-33 · The app talks only to real tenants and has no open doors — App · 5 pts

*As* **Suresh**, *I want* my photos and position to go only to my employer's Alvoraa site, *so that* a planted QR cannot send them anywhere else.
Carries: OPS-7, OPS-55, SEC-14 (app side), SEC-16, OPS-3 (no remote pages in step 1).

| AC | Given | When | Then |
|---|---|---|---|
| AC-172 | A table of at least 15 links, including `http://ppj.alvoraa.co/enrol#t=…`, `https://evilalvoraa.co/…`, `https://alvoraa.co.evil.com/…`, `https://x.alvoraa.co@evil.com/…`, `https://x.alvoraa.co:8443/…`, `https://alvoraa.co/…`, `https://a.b.c.alvoraa.co/…`, a punycode label, a code of the wrong length or characters | the host check runs (JS unit test with a network spy) | every one → `QR_NOT_ALVORAA` with **zero** network calls; `https://ppj.alvoraa.co/enrol#t=<43 chars>` passes in pilot and release; `https://ppj.dev.alvoraa.co/…` passes in the pilot build only |
| AC-173 | The built pilot package and config | CI inspects them | not debuggable; no cleartext allowed; no trust of user-installed certificates; no `server.url`; `allowNavigation` empty; WebView debugging off; `allowBackup="false"` with data-extraction rules |
| AC-174 | The bundled page | its content policy is read | scripts only from the app; `connect-src` only `https://*.alvoraa.co` (debug also the bench address); `object-src 'none'`; no outside fonts or images |
| AC-175 | A pilot phone | a link to an outside page is tapped inside the app | it opens in the system browser; the app never loads a remote page |
| AC-176 | A test server that answers E4 with a redirect to another host | the app calls it | the redirect is not followed; the app shows `serverError` |

#### US-34 · The app cannot quietly gain powers or load outside content — App · 3 pts

*As* **a customer's security reviewer**, *I want* the build to fail if the app asks for more than camera and location or adds tracking code, *so that* "no background location, no analytics" is a control, not a promise.
Carries: SEC-20, OPS-22, PRIV-8, OPS-14 (crash tool not adopted — gate decision 6).

| AC | Given | When | Then |
|---|---|---|---|
| AC-177 | The merged Android manifest | CI reads it | it fails if any permission is outside `INTERNET`, `ACCESS_NETWORK_STATE`, `CAMERA`, `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`; a throwaway branch adding `ACCESS_BACKGROUND_LOCATION` fails |
| AC-178 | The dependency tree | CI reads it | it fails on any analytics, crash-reporting, ads or Firebase SDK library |
| AC-179 | The bundled files and the package | CI checks them | it fails if a file holds a URL to any host other than the tenant pattern, or if the release package is over 10 MB |
| AC-180 | A pilot phone after the first punch | Android's app permission page is opened | location shows "Allow only while using the app" |

#### US-35 · First launch and scanning HR's code — App · 5 pts

*As* **Suresh**, *I want* to scan HR's code with the camera or pick its picture from WhatsApp, *so that* I can join wherever I got the code.
Screens: `first`, `camExplain`, `osCam`, `scan`, `checking`, `notAlvoraa`, `pickNoQr`, `camDenied`. Carries: S1, S2, MA-5, MA-26, FA-1, D1, D9, D18, PRIV-7.

| AC | Given | When | Then |
|---|---|---|---|
| AC-181 | A fresh install | the app opens | the `first` screen with the exact 01b §7.1 words; buttons **Scan the QR code from HR** and **Choose the QR picture from my photos**; no employee-ID or company-code field (D18); no bottom tab bar (D1); light theme even when the phone is in dark mode (D9); no network call |
| AC-182 | Camera never asked for | Suresh presses Scan | `camExplain` with 01b §7.2 words; **Continue** opens Android's camera prompt; if the camera is already allowed, the scanner opens directly |
| AC-183 | The scanner is open | a valid Alvoraa code is read / a UPI payment QR is read | `checking` ("Checking the code") and one E1 call / `notAlvoraa` with no network call |
| AC-184 | Suresh chooses a picture | the Android system photo picker returns it | no storage permission is requested; the code is read on the phone; a network capture shows the picture is never uploaded; a picture with no QR → `pickNoQr` |
| AC-185 | No internet, or E1 takes over 30 s | during `checking` | `noSignalJoin`; **Try again** calls E1 again |

#### US-36 · "Is this you?", the notice, and set up — App · 5 pts

*As* **Suresh**, *I want* to see my name before I agree, and then be set up at once, *so that* I am sure the code is mine and can check in within two minutes.
Screens: `confirm`, `notice`, `joining`, `welcome`. Carries: S3, brief §7 WOW, MA-7, PRIV-4, PRIV-5, OPS-24, OPS-25.

| AC | Given | When | Then |
|---|---|---|---|
| AC-186 | E1 returned 200 | `confirm` shows | initials circle (no photo), "Suresh Y.", "Driver", "Kaveri Transport", "HR made this code for one person only.", **Yes, this is me** (green) and **This is not me**; no network call on this screen |
| AC-187 | Suresh presses Yes | `notice` shows | the six rows and "{days}" from E1's answer (no call); tick box **not** ticked; **Agree and finish** without the tick → "Please tick the box to show you have read the notice." under the box with `role="alert"`, focus on the box, no call |
| AC-188 | The box is ticked | Suresh presses **Agree and finish** | busy "Setting up this phone"; one E3 call; the secret is written to Keystore-backed secure storage; `welcome`: "Welcome, Suresh. This phone is set up.", "You do not need to wait for HR. You can mark attendance now.", card Company / Your workplace / Check in within, **Check In**, **Not now** |
| AC-189 | E3 answers `QR_USED` or `QR_EXPIRED` | at Agree | `qrUsed` / `qrExpired`; nothing saved on the phone |
| AC-190 | Suresh goes Back from `notice`, or closes the app, before Agree | he scans the same code again | the flow starts again; nothing was saved; the code still works |
| AC-191 | Pilot phones P1–P3 on the 3G profile, 10 runs each | scan → `confirm`, and Agree → `welcome` | each ≤ 2.5 s p95, recorded in the pilot report |

#### US-37 · Clear screens when a code cannot be used — App · 3 pts

*As* **Suresh**, *I want* to be told plainly that the code is dead and what to do, *so that* I do not think the app is broken.
Screens: `qrExpired`, `qrUsed`, `qrCancelled`, `appOff`, `notField`, `noSignalJoin`, `featureOff`, not-recognised code. Carries: S4, MA-6, D8, D11.

| AC | Given | When | Then |
|---|---|---|---|
| AC-192 | Each join refusal code in §7.1 | it arrives | the screen shows the 01b §7.12 heading, body, steps and buttons, with values filled ("It ran out on Thursday 24 September at 10:05 am."; "It was already used today at 9:01 am. Each code works once. If that was not you, tell HR today."; "In HR's records your job is Store Associate."); dead-code screens have **no Try again**; "Code for HR: {CODE}" at the bottom |
| AC-193 | `QR_NOT_RECOGNISED` | it arrives | heading "This code cannot be used any more", body "HR's codes work once, for a limited time." and the two steps "Ask HR for a new code." / "Scan the new code with this app.", buttons **Scan a new code** · **Done**, "Code for HR: QR_NOT_RECOGNISED" (drafted here; designer to confirm) |
| AC-194 | `camDenied` | Suresh presses **Open phone settings** / **Choose a picture instead** | Android opens this app's settings page / the photo picker opens |

#### US-38 · "This is not me" on the phone — App · 2 pts

*As* **Ramesh**, *I want* to say the code is not mine and cancel it, *so that* nothing is set up with someone else's name.
Screens: `notMe`, `notMeDone`. Carries: D2.

| AC | Given | When | Then |
|---|---|---|---|
| AC-195 | `confirm` | Ramesh presses **This is not me** | bottom sheet with the 01b §7.6 words; **Go back. It is me.** returns to `confirm` with no call; **Cancel this code** sends E2 and shows "The code is cancelled" / "Nothing was set up on this phone. If you are waiting for your own code, ask HR." / **Done** → `first`; nothing stored |
| AC-196 | No internet | Ramesh presses **Cancel this code** | `noSignalJoin`; the code is not cancelled |

#### US-39 · The Attendance screen and the punch — App · 5 pts

*As* **Suresh**, *I want* one big button that takes my photo and place, *so that* I mark attendance in one tap each day.
Screens: `home`, `homeIn`, `homeOut`, `camOff`, `locExplain`, `osLoc`, `punching`, `resultIn`, `resultOut`. Carries: FC-K1, FC-1, FC-2, MA-26, OPS-21, OPS-24, OPS-63, SEC-21 (app side).

| AC | Given | When | Then |
|---|---|---|---|
| AC-197 | A joined phone | `home` shows | top bar company · name · **Settings** (gear and word); status line "Not checked in yet today" / "Checked in since 9:02 am" (green dot and words) / "**Checked out at 6:14 pm**" after a check-out (FC-1); "You need to be within 100 m of Okhla Depot" or no rule line when there is no workplace; today's punch list from the latest answer |
| AC-198 | The first Check In ever | Suresh presses it | `locExplain` with 01b §7.10 words; **Continue** shows Android's prompt asking only for "while using the app", precise; later punches skip `locExplain` |
| AC-199 | A punch | it runs | busy lines one at a time "Taking your photo" → "Finding where you are" → "Saving your attendance"; one E5; `resultIn` shows the saved photo, "Checked in", time, date, "Where you were · At Okhla Depot", "Photo · Taken", "Saved · In your HR record", "**Only HR and your manager can see this.**" (FC-2); **Done** returns to home updated from E5's answer with no extra E4 call |
| AC-200 | The camera is refused or broken | Suresh presses Check In | `camOff` panel "The camera is off. You can still check in, but there will be no photo."; the punch saves; result shows "Photo · Not taken" and "The camera was not on. Your attendance still counts." |
| AC-201 | A 4000 × 3000 busy test picture | the photo code runs (unit test) | output long edge ≤ 640 px, short edge ≤ 480 px, JPEG 0.6, saved again at 0.45 when over 120 KB, never over 150 KB |
| AC-202 | The app comes back to the front several times in a minute | — | at most one E4 a minute; on opening, the saved screen shows within 300 ms marked as updating (pilot measure) |
| AC-203 | Any server call | it is sent | it carries `X-Alvoraa-App-Version`, times out after 30 s, and is retried only when the person taps Try again |
| AC-204 | A pilot phone running a fake-GPS app | Suresh punches | the punch reaches the server with the mock-location flag true, and HR sees "Phone reported a fake location" ticked (device test) |

#### US-40 · Check-in problems explained, photo kept — App · 3 pts

*As* **Suresh**, *I want* to know why a punch did not save and what to do, without retaking my photo, *so that* I can fix it on the spot.
Screens: `locDenied`, `locOff`, `gpsVague`, `outside`, `noSignal`, `duplicate`, `tooMany`, `serverError`, `unknownCode`. Carries: FC-K2, D11, OPS-26.

| AC | Given | When | Then |
|---|---|---|---|
| AC-205 | Each check-in code in §7.1 and §7.2 | it arrives | the 01b §7.12 screen with values ("about 380 m from Okhla Depot. You need to be within 100 m"); "Code for HR: {CODE}" at the bottom; for `LOCATION_OFF`, `LOCATION_SLOW`, `LOCATION_MISSING`, `GPS_NOT_EXACT`, `OUTSIDE_WORKPLACE`, `NO_INTERNET`, `TOO_MANY_TRIES`, **Try again** re-sends the same photo from memory with no second camera capture |
| AC-206 | The answers in §7.3 | they arrive | nginx 429 page → `tooMany` with a 60 s wait; 413/502/503/504 → `serverError`; a 200 HTML page → `noSignal`; an unknown JSON code → `unknownCode` showing "For HR · {code}", "This version does not know this code yet.", **Check for an update** · **Try again** |
| AC-207 | `serverError` | it shows | card "For HR · SERVER_ERROR / When · {date, time} / App · {version} · Android"; no secret, code or employee ID on screen |
| AC-208 | `OUTSIDE_WORKPLACE` with empty `distance_m` | it arrives | "You are too far from Okhla Depot to check in." |

#### US-41 · When the phone is stopped, it says so — App · 3 pts

*As* **Suresh**, *I want* a plain screen when my phone cannot be used any more, *so that* I know to update the app or speak to HR instead of pressing a dead button.
Screens: `update`, `blocked`, `replaced`, `left`, `appOff` and `notField` after joining, first launch with a line. Carries: S9, MA-29, MA-30, MA-31, MA-34, OPS-58, D5 (phone side).

| AC | Given | When | Then |
|---|---|---|---|
| AC-209 | `APP_TOO_OLD` on opening | the app shows `update` | only this screen is reachable (no Check In, no Back to home); card "On this phone {ver} / Needed {min} or newer"; the one button opens: pilot build → the Firebase tester page for this app; release build → the Play Store listing; debug → the line "Ask the developer". The address is built into the app, never taken from the server |
| AC-210 | `DEVICE_BLOCKED`, `DEVICE_REPLACED`, `EMPLOYEE_NOT_ACTIVE` | on opening or at a punch | `blocked` / `replaced` / `left` with 01b §7.12 words; Check In hidden; Settings reachable; **Remove {company} from this phone** clears the secret and saved data on the phone after a confirm, with no server call, and returns to `first` |
| AC-211 | `APP_OFF_FOR_FIELD` or `NOT_FIELD_ROLE` after joining | on opening | `appOff` / `notField` with a **Remove** button; the secret is **kept**, so the phone works again if HR restores the setting |
| AC-212 | `NOT_SET_UP`, `DEVICE_PENDING` or `DEVICE_REMOVED` | on opening | the secret and saved data are deleted; `first` shows "This phone is not set up." (or "This phone is no longer linked to {company}." for removed) |

#### US-42 · The notice changed: read it again — App · 2 pts

*As* **Suresh**, *I want* to be shown the new notice before my next check-in, *so that* I know what changed.
Screens: `noticeAgain`. Carries: D19, OPS-31, PRIV-2.

| AC | Given | When | Then |
|---|---|---|---|
| AC-213 | `NOTICE_CHANGED` from E4 or E5 | it arrives | `noticeAgain`: "The notice has changed", "Please read it again before your next check-in. What is new: {what_changed}.", the six rows from the answer, an unticked box; **Agree and continue** sends E9 with that version and then shows home; Check In cannot be reached until E9 returns 200 |

#### US-43 · Settings, "What this app records", and removing the phone — App · 3 pts

*As* **Suresh**, *I want* to see what the app records and remove my company from the phone, *so that* I stay in control of my own phone.
Screens: `settings`, `records`, `leaveConfirm`, `removed`. Carries: S10, SEC-22 (phone side), D10, PRIV-12 (worker side).

| AC | Given | When | Then |
|---|---|---|---|
| AC-214 | A joined phone | Settings opens | groups You (full name / designation, company, workplace, "Check in within {radius} m"), Privacy (**What this app records** › "You agreed on {date}"), This phone (**Remove this phone from {company}** › "Attendance on this phone stops"), About (app version and build, "Connected to {host}", "Joined {date, time}", "For any problem, speak to HR. Tell them the app version above."); **no "Sign out"**; the Language group is hidden in pilot builds (D15) |
| AC-215 | Suresh opens **What this app records** | — | the six rows of the version he agreed, "You agreed on Thursday 17 September at 9:01 am. Notice version {v}." and "If this notice changes, the app asks you to read it again before your next check-in."; shown from saved data, no call |
| AC-216 | **Remove this phone** | Suresh confirms | the 01b §7.13 sheet; **Remove this phone** sends E6; on 200 the secret and saved data are deleted and `first` shows "This phone is no longer linked to Kaveri Transport."; with no internet: "Connect to the internet to remove this phone. Nothing has changed." and the secret is kept |

#### US-44 · What the phone keeps, and what it never keeps — App · 3 pts

*As* **Suresh**, *I want* my secret locked away and my photos never saved on the phone, *so that* a lost or backed-up phone gives nothing away.
Carries: OPS-25, PRIV-1 (phone side), PRIV-7, SEC-16 (backup).

| AC | Given | When | Then |
|---|---|---|---|
| AC-217 | A joined debug build | its storage is inspected | the secret is only in Keystore-backed secure storage; not in `localStorage`, Preferences or WebView storage |
| AC-218 | The join flow | Suresh leaves it at any point | the code was only in memory; never in storage, the page address or history |
| AC-219 | After a punch and a picture join | the app's folders are inspected | no image file anywhere (files, cache, gallery) |
| AC-220 | The app code | reviewed and searched | the only phone facts sent are model (trimmed to 80 characters), platform and app version; no call to `Device.getId()` or anything reading IMEI, Android ID, serial, advertising ID, phone number, SIM or contacts |
| AC-221 | A pilot phone | an Android backup or data extraction is attempted | no app data is included |

#### US-45 · Names from the server are shown as plain text — App · 2 pts

*As* **Suresh**, *I must not* have a company or job name typed by someone in HR run as code on my phone, *so that* nobody can reach my secret or camera that way.
Carries: SEC-17, abuse case A16.

| AC | Given | When | Then |
|---|---|---|---|
| AC-222 | A fixture tenant with designation `<img src=x onerror=alert(1)>` and company `</div><script>alert(1)</script>` | `confirm`, `home`, `settings` and `records` are drawn (JS unit test) | both show as literal text; no script runs |
| AC-223 | The app's JavaScript | CI lint runs | it fails on any `innerHTML` set from anything other than escaped values or fixed strings |

#### US-46 · English only in the pilot; readable on a small phone — App · 2 pts

*As* **Suresh on a 360 px phone in sunlight**, *I want* big clear text and buttons, *so that* I can use the app without help.
Carries: D15, 01b §10, nfr-budget §7.

| AC | Given | When | Then |
|---|---|---|---|
| AC-224 | Pilot and release builds | any screen | English only; the language switch hidden; Hindi strings exist in the string table but cannot be reached |
| AC-225 | Every phone screen at 360 px wide in English | an automated and a hand check | no sideways scroll; tap targets ≥ 44 px; app text ≥ 15 px; every status has a dot **and** words; focus outline visible; errors announced with `role="alert"` |
| AC-226 | The app code | lint runs | every user-facing string comes from the string table; none is written inline |

#### US-47 · The same build runs on one iPhone — App · 2 pts

*As* **Surbhi**, *I want* proof that the app runs on an iPhone too, *so that* "Android first, iPhone in parallel" is real before paying for Apple.
Carries: S14, OPS-42.

| AC | Given | When | Then |
|---|---|---|---|
| AC-227 | One borrowed iPhone, free Apple ID, a non-production tenant with invented data | the app is installed from the borrowed Mac | it joins with a code and saves one punch with a photo |
| AC-228 | The repo and the borrowed Mac | CI and the release checklist | CI fails if the iOS project has `DEVELOPMENT_TEAM` with a value; no Apple ID, team ID, `*.mobileprovision`, `*.p12`, `*.cer`, `xcuserdata/` or `ExportOptions.plist` is committed; the checklist records that the Apple ID was signed out and the clone deleted |

#### US-48 · The pilot: testers, phones, numbers, stop rule — App · 3 pts

*As* **Surbhi**, *I want* a pilot on real low-end phones with numbers at the end, *so that* I decide to continue or stop on evidence.
Carries: OPS-9 (done), OPS-23, OPS-36, OPS-54, OPS-56, OPS-57, OPS-63, PRIV-15, brief §10 measures 1–4, brief kill criteria, user answers (Firebase on Surbhi's account; phones partly owned, rest borrowed).

| AC | Given | When | Then |
|---|---|---|---|
| AC-229 | The pilot tenant on dev (for example `ppj.dev.alvoraa.co`) | before the first tester joins | invented employees only; photo retention 7 days (set on Surbhi's word); a pilot build reaches it over HTTPS with the wildcard certificate |
| AC-230 | Firebase App Distribution | testers are added and one is removed | testers are invited by email into group `pilot-013`; no public invite link exists; the removed tester no longer sees the release, and their phone, blocked in the desk, gets `DEVICE_BLOCKED` |
| AC-231 | The pilot phone list | written | a table in the repo per phone: maker, model, Android version, RAM, processor type, Google Play services yes/no, owned or borrowed; three makers among P1–P3; **no tester names** |
| AC-232 | P1–P3, 10 runs each on the 3G profile | the pilot report is written | cold start ≤ 2.5 s p95; saved screen ≤ 300 ms; scan → confirm ≤ 2.5 s; Agree → welcome ≤ 2.5 s; punch network part ≤ 2.5 s with GPS time shown apart; package ≤ 10 MB; first-scan result with the QR model inside the app vs downloaded, and the choice made (OPS-23) |
| AC-233 | 5 working days, 3 makers, ≥ 20 punches per phone, inside the geofence with signal | counts are read | measure 1 (first-tap saves) is reported per maker; ≥ 95% meets the target; **below 90% on any maker after one round of fixes → the report recommends stopping the app (the kill rule); Surbhi decides** |
| AC-234 | The pilot counts | read | measure 2: median time from code used to first saved punch, and HR actions needed (target ≤ 2 min, zero); measure 3: codes used by the right person first time (target ≥ 9 of 10), with "This is not me" and re-issue counts; measure 4: 0 punches after a block, and 0 unexplained errors on a build kept one version behind |
| AC-235 | The release checklist | before the first tester joins | a signed line: testers read the notice, know it is a test, and pilot photos are deleted at the end or follow the 7-day retention (PRIV-15) |

---

### YouTrack-ready story table

Do not create issues from here without Surbhi's word.

| ID | Summary | Line | Persona | Points | ACs | Requirements |
|---|---|---|---|---|---|---|
| US-1 | Only a working phone can punch | Server | HR Manager | 3 | AC-1–6 | SEC-10, OPS-28, OPS-50 |
| US-2 | Phone record cannot be forged, re-pointed, unblocked or deleted | Server | Field employee | 5 | AC-7–13 | SEC-8, SEC-9, D4, OPS-30 |
| US-3 | Field attendance app settings with change history | Server | HR Manager | 5 | AC-14–25 | S6, D5, D20, OPS-53 |
| US-4 | Error codes and version check | Server | Field employee | 5 | AC-26–37 | OPS-8, 26, 27, 44, 48, 49; SEC-19, SEC-24 |
| US-5 | HR makes a single-use code (server) | Server | HR Manager | 5 | AC-38–45 | S5, SEC-1, 2, 4, 6; D6, D17; OPS-13, 51 |
| US-6 | Invite dialog: show once, print, copy picture | Server | HR Manager | 3 | AC-46–50 | S7, D6, D14, OPS-32 |
| US-7 | HR cancels a waiting code | Server | HR Manager | 2 | AC-51–52 | SEC-7 |
| US-8 | Check a code without using it | Server | Field employee | 5 | AC-53–60 | SEC-3, SEC-15, PRIV-5, D8, OPS-24 |
| US-9 | "This is not me" cancels the code | Server | Field employee | 2 | AC-61–63 | D2, SEC-7 |
| US-10 | Agree and finish joins the phone | Server | Field employee | 5 | AC-64–70 | S5, SEC-5, OPS-51, PRIV-1 |
| US-11 | One working app phone per person | Server | HR Manager | 3 | AC-72–75 | D3, SEC-14 |
| US-12 | App start answer | Server | Field employee | 3 | AC-76–83 | OPS-24, PRIV-6, PRIV-9, D5 |
| US-13 | Punch from the app | Server | Field employee | 3 | AC-84–91 | SEC-21, PRIV-14 |
| US-14 | New notice version and acknowledgement history | Server | Field employee | 5 | AC-92–98 | D19, PRIV-2, 3, 4; OPS-31 |
| US-15 | Employee removes the phone | Server | Field employee | 2 | AC-99–101 | SEC-22, D10 |
| US-16 | App state on the Employee record | Server | HR Manager | 5 | AC-102–109 | S7, D13, PRIV-9 |
| US-17 | Block a phone with a reason | Server | HR Manager | 3 | AC-110–113 | D4, D7, PRIV-13 |
| US-18 | All app phones list | Server | HR Manager | 2 | AC-114–115 | S7, PRIV-9 |
| US-19 | HR alerts | Server | HR Manager | 5 | AC-116–122 | SEC-12, SEC-13 |
| US-20 | `/enrol` page never uses a code | Server | Field employee | 2 | AC-123–125 | S13, SEC-2 |
| US-21 | Codes run out; clean-up | Server | HR Manager | 3 | AC-126–130 | OPS-52, PRIV-10 |
| US-22 | Daily counts and technical alerts | Server | Alvoraa (Surbhi) | 5 | AC-131–134 | OPS-34, 59, 61; PRIV-11 |
| US-23 | Leaver's codes and phones stop | Server | HR Manager | 2 | AC-135–136 | SEC-7 |
| US-24 | nginx protects the device paths | Server | Alvoraa (Surbhi) | 3 | AC-137–139 | OPS-1, 2, 45, 47; SEC-18 |
| US-25 | Busy depot: limits and speed | Server | Field employee | 5 | AC-140–144 | OPS-10, 29, 46, 62; SEC-12 |
| US-26 | Nothing secret or personal in logs | Server | Field employee | 3 | AC-145–148 | SEC-11, SEC-25, OPS-20, 43, 60 |
| US-27 | Must not: outside remit, colleagues, managers | Server | Field employee | 3 | AC-149–152 | SEC-9, access intent |
| US-28 | Access-request report | Server | HR Manager | 2 | AC-153 | PRIV-12 |
| US-29 | Migration and backfill | Server | Alvoraa (Surbhi) | 3 | AC-154–159 | OPS-50, 53; PRIV-3 |
| US-30 | Rollout by the switch | Server | Alvoraa (Surbhi) | 2 | AC-160–162 | OPS-53, 64, 65 |
| US-31 | No signing key in the repo | App | Alvoraa (Surbhi) | 2 | AC-163–164 | OPS-6, 37; SEC-23 |
| US-32 | Three build types | App | Alvoraa (Surbhi) | 5 | AC-165–171 | OPS-5, 15, 38, 39, 40, 41 |
| US-33 | Real tenants only; no open doors | App | Field employee | 5 | AC-172–176 | OPS-3, 7, 55; SEC-14, SEC-16 |
| US-34 | No hidden powers or outside content | App | Security reviewer | 3 | AC-177–180 | SEC-20, OPS-14, 22; PRIV-8 |
| US-35 | First launch and scanning | App | Field employee | 5 | AC-181–185 | S1, S2, D1, D9, D18 |
| US-36 | Is this you, notice, set up | App | Field employee | 5 | AC-186–191 | S3, WOW, PRIV-4, 5 |
| US-37 | Dead-code screens | App | Field employee | 3 | AC-192–194 | S4, D8, D11 |
| US-38 | "This is not me" on the phone | App | Field employee | 2 | AC-195–196 | D2 |
| US-39 | Attendance screen and punch | App | Field employee | 5 | AC-197–204 | FC-1, FC-2, OPS-21, SEC-21 |
| US-40 | Check-in problems, photo kept | App | Field employee | 3 | AC-205–208 | D11, OPS-26 |
| US-41 | Phone stopped screens | App | Field employee | 3 | AC-209–212 | S9, OPS-58, D5 |
| US-42 | Notice changed on the phone | App | Field employee | 2 | AC-213 | D19, OPS-31 |
| US-43 | Settings and remove phone | App | Field employee | 3 | AC-214–216 | S10, SEC-22, D10 |
| US-44 | What the phone keeps | App | Field employee | 3 | AC-217–221 | OPS-25, PRIV-1, PRIV-7 |
| US-45 | Server names shown as text | App | Field employee | 2 | AC-222–223 | SEC-17 |
| US-46 | English only; readable at 360 px | App | Field employee | 2 | AC-224–226 | D15 |
| US-47 | iPhone test build | App | Alvoraa (Surbhi) | 2 | AC-227–228 | S14, OPS-42 |
| US-48 | Pilot, numbers, stop rule | App | Alvoraa (Surbhi) | 3 | AC-229–235 | OPS-9, 23, 36, 54, 56, 57, 63; PRIV-15 |
| | **Totals** | | | **Server 104 · App 58 · 162** | **234 ACs** (AC-71 not used) | |


---

## 10 · Notifications and messages

**Owners (user answer 2026-09-17):** data alerts go to the **customer's HR**; technical alerts go to **Alvoraa (Surbhi)**. All HR alerts are Frappe `Notification Log` rows (desk bell); email only when the person has email on in their notification settings. Sent after the save, on the `short` queue. **Wording drafted by me — `01b` has none. The designer to confirm (Q-7).**

| # | Trigger | To | Subject | Body | Must never contain |
|---|---|---|---|---|---|
| N1 | Code used (E3) | The HR person who made it | "{Employee name} joined the Alvoraa app" | "{Employee name} set up {phone model} at {time} with the code you made on {date}. If this was not {first name}, block the phone from their employee record." | code, secret, hash, photo, coordinates |
| N2 | "This is not me" (E2) | Maker + HR Managers who can read the employee | "App code for {Employee name} was refused on a phone" | "Someone pressed "This is not me" on the app code for {Employee name}. The code is cancelled. Make a new code if {first name} still needs one, and give it only to {first name}." | same |
| N3 | A used code scanned again from a different phone (E1) | HR Managers who can read the employee | "Used app code for {Employee name} was scanned again" | "The app code for {Employee name} was used at {time} on {phone model}, and has now been scanned on another phone. If {first name} did not set up {phone model}, block that phone and make a new code." | same |
| N4 | A phone that held one person's secret joined as another (E3) | HR Managers who can read both | "One phone was used by two employees" | "A phone set up for {Employee A} was just set up for {Employee B}. {Employee A}'s phone has been removed. Check with both of them." | same |
| N5 | Refused or unknown code checks above the threshold in one hour | HR Managers of the tenant | "Many app codes that do not work were tried" | "{n} app codes that do not work were tried in the last hour. This may be someone guessing codes. No phone was set up with them." | same, plus no IP addresses |
| T1–T4 | Clean-up job failed or found a live hash; > 5 server errors an hour on device paths; punch refusals > 10% for one app version; refused checks above threshold | Surbhi, through the control plane | titles and counts only | — | any name, employee ID, phone model, token |

**Phone and page messages** are the exact words of `01b` §7 and §9, plus the drafts in AC-123 (`/enrol`) and AC-193 (`QR_NOT_RECOGNISED`). **Toasts in the desk:** "Picture copied. Paste it in WhatsApp to {first name}." No message to a peer ever names another person's phone, place or block reason.

---

## 11 · Edge cases

| Case | What happens | AC |
|---|---|---|
| **Mid-period joiner** — Employee is Active but `date_of_joining` is next week | A code can be made and used; punches before the joining date are saved as today (Frappe HR does not refuse them). Flagged, not changed | — (Q-10) |
| **Leaver** | Phones Blocked, waiting codes Cancelled at the status change | AC-135 |
| **Leaver with a future relieving date, still Active** | Keeps working until status changes (existing rule) | — |
| **Re-hired employee** | Old phones stay Blocked; old codes stay Cancelled; HR makes a new code | AC-136 |
| **Designation changed after joining** | Next call → `NOT_FIELD_ROLE`; changing it back restores the phone | AC-78 |
| **Employee with no designation** | Not a field worker; no Invite button | AC-21, AC-103 |
| **Designation renamed** | Frappe's rename updates Link fields in child tables [UNVERIFIED — engineer to confirm for Table MultiSelect] | AC-21 |
| **Designation deleted** | Frappe refuses while it is linked (standard link check) [UNVERIFIED] | — |
| **Multi-company tenant** | One designation list for all companies (Q-9); HR Users see only their companies (AC-149); alerts go only to HR who can read the employee (AC-117) | AC-117, AC-149 |
| **Employee with no manager** | Nothing changes; notice still says "HR and your manager" (true where one exists) | — |
| **Two employees both "Suresh Y., Driver"** | "Is this you?" cannot tell them apart; the code is still bound to one record. Usability test decides whether to add the last digits of the employee ID (01b §13) | AC-186 |
| **Back-dated punch** | Not possible from the app; time is always server time | AC-84 |
| **Phone clock wrong or other time zone** | Expiry and punch times come from the server, in the site time zone; the phone clock is never used for rules | AC-58, AC-84 |
| **DST** | Not used in India; site time zone rules apply elsewhere | — |
| **Holidays, shifts, auto attendance** | Unchanged; punches feed Frappe HR as machine punches do | AC-84 |
| **No shift location assigned** | No geofence refusal; no rule line on home | AC-197 |
| **Geolocation tracking off in HR Settings** | Frappe HR skips the distance check (existing) | — |
| **Code expires while the notice is open** | `QR_EXPIRED` at Agree; nothing saved | AC-68, AC-189 |
| **Two people press Agree on one code together** | One wins; the other gets `QR_USED` | AC-65 |
| **HR makes a new code while the phone is joining** | Both finish; at most one waiting code, one active app phone | AC-70 |
| **HR blocks a phone while it is punching** | The punch either saves before the block or is refused after; never both | AC-2, AC-111 |
| **HR switches the app off during a punch** | Next call refused; a saved punch stays | AC-78 |
| **Bulk import of phone statuses** | Refused for any change out of a final state or without a reason | AC-7, AC-11 |
| **Bulk Employee import changing designations** | Takes effect at each phone's next call | AC-78 |
| **Plan downgraded** | `FEATURE_OFF` for app and web phones | AC-81 |
| **Web-page phone and app phone for the same person** | Both can stay Active (01c SEC-5 wording); Q-3 asks whether the app join should stop the web phone | AC-73 |
| **Pending web phone for a field worker who then joins the app** | Stays Pending; HR could still activate it later (a second working phone). Covered by Q-3 | — |
| **Shared family phone** | Only one person per phone; a second join removes the first | AC-74 |
| **Phone reinstalled or storage cleared** | Secret lost; needs a new code; the old record becomes Replaced at the next join | AC-72 |
| **Duplicate punch after a lost answer** | Server's 60-second window refuses the second one | AC-86 |
| **Captive Wi-Fi login page** | Treated as no internet | AC-206 |
| **Printed code left on a desk** | Works until used, cancelled or run out; the owner's own scan shows "already used at 9:01" and HR is alerted | AC-54, AC-118 |
| **HR person makes a code for themselves** | Allowed if they are a field worker; recorded like any other | AC-38 |
| **Cancelled and amended documents** | Not submittable doctypes; nothing to amend. Deleting a punch is unchanged HR behaviour | — |

---

## 12 · Non-functional requirements for this slice

From `nfr-budget.md` and `07` §2–§3.

| Dimension | Requirement for this slice | AC |
|---|---|---|
| **Volume** | Design for 1,000 employees per tenant, up to 400 field workers on one site. Codes ≈ employees × 3 a year (≤ 3,000 rows); phones ≤ 2,000; acknowledgements ≤ 5,000; punches ≈ 400 × 2 × 26 = 20,800 a month | AC-140, AC-142 |
| **Worst-case query** | E4 today's punches for one employee (index on `Employee Checkin.employee`, `time` exists in Frappe HR [UNVERIFIED]); code lookup by `token_hash` (indexed); phone lookup by `token_hash` and `retired_token_hash` (indexed); counts for the settings confirm (one grouped query each) | AC-142 |
| **API speed** | Every endpoint p95 ≤ 500 ms at Typical volume; E5 at risk (dated exception if missed); desk section ≤ 1.5 s p95 | AC-109, AC-143 |
| **Phone speed (3G profile, P1–P3)** | Cold start ≤ 2.5 s; saved screen ≤ 300 ms; scan → confirm ≤ 2.5 s; Agree → welcome ≤ 2.5 s; punch network ≤ 2.5 s | AC-191, AC-232 |
| **Payload** | Answer ceilings in §6; photo ≤ 150 KB from the phone, 400 KB server backstop; package ≤ 10 MB | AC-31, AC-201, AC-179 |
| **List views** | Phones list page size 20, default filter last 7 days | AC-114 |
| **Background jobs** | Daily clean-up on `default` (batched, safe to run twice); alerts on `short` after commit; daily counts with the existing health pull | AC-127, AC-122, AC-131 |
| **Rate limits** | Per code or phone, keyed on the hash (§6); nginx device zone 600/min burst 100 | AC-140, AC-144 |
| **Reliability** | Every join is one locked save; phone-side timeout 30 s; retry only on tap; rollback by the switch in under a minute | AC-65, AC-66, AC-203, AC-161 |
| **Security** | Guest endpoints POST only, no-store, no session use; permissions in controllers for every entry path; CI gates for keys, hosts, permissions, libraries | US-2, US-4, US-24, US-31–34 |
| **Sensitive data** | Photo and GPS: sensitive (unchanged storage). Code and device secret: secret (hash only). Phone model, block reason, acknowledgement: personal. Never in logs | AC-39, AC-146, AC-147 |
| **Retention** | Codes: Q-1 default (§13); phones and acknowledgements while any linked punch exists; photos per tenant setting (unchanged); counts 13 months; logs under the existing 180-day rule | AC-129, AC-134 |
| **Observability** | Daily counts per outcome and app version; four technical alerts with an owner (Surbhi) | AC-131, AC-133 |
| **Accessibility** | WCAG 2.2 AA at 360 px; text ≥ 15 px in the app; targets ≥ 44 px | AC-225 |

---

## 13 · Data migration and backfill

**For existing tenants. No client is live (14 Sep 2026); PPJ is a demo tenant.**

| # | What | How | Safe twice? | Rollback | AC |
|---|---|---|---|---|---|
| M1 | Phone doctype: new statuses and fields | Doctype JSON change | yes | fields stay after a revert (Frappe keeps columns); harmless | AC-157 |
| M2 | Existing phones get `join_method` = Web check-in page; Blocked phones' hash moved to `retired_token_hash` | Patch | yes | none needed; a revert of US-1 is not allowed | AC-154 |
| M3 | One acknowledgement row per existing phone with `consent_version` (channel Backfill, language Not recorded) | Patch | yes (skips phones that already have one) | delete rows with channel Backfill | AC-155 |
| M4 | Remove create and delete for HR roles on the phone doctype, including any Role Permission Manager override on the tenant | Doctype JSON + patch for Custom DocPerm rows [UNVERIFIED whether any exist] | yes | re-add in Role Permission Manager (not recommended) | AC-156 |
| M5 | HR Settings fields, child table, Employee Checkin flag | `after_migrate` and `after_install`, like `field_checkin.after_migrate` | yes | fields stay; switch off | AC-14, AC-157 |
| M6 | Field-worker designation list **empty** everywhere | default | — | — | AC-14, AC-160 |
| M7 | Notice version bump (D19) | new `CONSENT_VERSION`; old text kept in the notice store | — | — | AC-92, AC-93 |
| M8 | Web-page phones (joined via `/checkin`) | **Nothing.** They keep working, are not asked to re-read the notice, and are not moved to the app (MA-32: nothing to migrate) | — | — | AC-79, AC-96 |
| M9 | Nothing is recomputed on `Employee Checkin` | — | — | — | — |

**Rollback of the slice:** untick the switch (US-30). A code revert, if ever needed, never goes back past US-1 and US-2, or Replaced and Removed phones would punch again (07 §3 point 2).

---

## 14 · Localisation and accessibility

| Item | Rule | AC |
|---|---|---|
| Language in the pilot | **English only** (D15). Hindi drafts stay in the string table, hidden until a native speaker checks them | AC-224 |
| App strings | All from one string table; no inline text | AC-226 |
| Server and desk strings | Python `_()`, JavaScript `__()`; no sentences glued from pieces | review |
| Notice rows | From the server per version; Hindi rows added later as the same version's translation | AC-92 |
| Dates and times on the phone | English, "Thu 24 Sep 2026, 10:05 am" style, from server times in the site time zone | AC-192 |
| Dates in the desk | User's Frappe date format | review |
| Numbers | Whole metres ("380 m"); no currency | AC-205 |
| Printed sheet | English only in the pilot; no employee ID | AC-49 |
| Screen readers | Labels on inputs; `role="dialog"` with heading; `role="alert"` on errors; status in words, not colour only | AC-187, AC-225 |
| Low-end phone | 360 px width, text ≥ 15 px, buttons 60 px, punch button 96 px, light theme pinned | AC-181, AC-225 |
| Frontline worker without a laptop | Everything they need is on the phone; HR screens are desk only | — |

---

## 15 · Audit and traceability of actions

Can each be answered a year later?

| Question | Where the answer lives | AC |
|---|---|---|
| Who made Suresh's code, when, for how long? | Invite `owner`, `creation`, `lifetime_hours` (+ Version) | AC-38 |
| Was it used, cancelled (by whom, how) or did it run out? | Invite `status`, `used_at`, `cancel_reason`, `cancelled_by`, `cancelled_at` | AC-51, AC-61, AC-64, AC-126 |
| Which phone did it set up? | Invite `used_device`, phone `invite` | AC-64 |
| Who blocked a phone, when and why? | Phone `status_changed_by`, `status_changed_on`, `block_reason` (+ Version, `track_changes` on) | AC-111 |
| Which phone replaced which? | Phone `replaced_by` | AC-72 |
| Did the employee remove it? | `status_change_source` The employee | AC-99 |
| Which notice words did Suresh read, on which phone, when? | Acknowledgement rows + notice store text for that version | AC-64, AC-93, AC-94 |
| Which phone sent a punch, was the position faked? | `Employee Checkin.alvoraa_field_device`, `alvoraa_mock_location` | AC-84, AC-85 |
| Who looked at a punch photo? | `Alvoraa Photo Access Log` (existing) | AC-89 |
| Who changed the field-app settings, from what to what, why? | HR Settings Version rows with the reason | AC-15, AC-19 |
| Could anyone erase this? | No role can delete codes, phones or acknowledgements; only Administrator. Version rows follow Frappe rules | AC-8, AC-98, AC-152 |

**Honest gap:** Frappe Version rows are not tamper-evident (compliance map A2 is not built). A System Manager or Administrator with database access could change history. Unchanged by this slice.


---

## 16 · Compliance-impact sub-analysis

**I am not a lawyer.** This builds on `01c` and does not re-decide it. Working position recorded by Surbhi (interim compliance owner, 2026-09-17): the customer company is the Data Fiduciary, Alvoraa the Data Processor; attendance photo and location rest on the employment "legitimate use" basis (DPDP s.7(i)) with a clear notice, not a consent request; a DPA template, a privacy notice template and a DPDP lawyer's review come before the first paying customer.

### 16.1 Data touched

Classes per the baseline: `public / internal / sensitive / statutory-id`. (`01c` uses Secret / Sensitive / Personal / Internal; mapped here.)

| Field / object | Class | Purpose | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| Photo at punch | sensitive | Evidence the person was there | Legitimate use, employment (working position) | No (008) |
| GPS position and accuracy at punch | sensitive | Geofence; settle a dispute | same | No (008) |
| Fake-location flag at punch | internal (personal) | Flag a doubtful punch for HR | same | **Yes** — without it, a faked position looks real to HR |
| Phone model name | internal (personal) | Tell phones apart for HR and the worker | same | **Yes for the notice** (the web page already sent it; now stated, D19) — without it HR cannot tell which phone to block |
| App version | internal | Refuse old apps; support | same | **Yes** — without it an old app fails silently |
| Code hash, device secret hash | internal (derived from a secret) | Prove HR chose this person; prove the phone | same | Code hash **yes** — the no-approval join is impossible without it |
| Code record (made by, when, outcome, which phone) | internal (personal) | Audit who let which phone in | same | **Yes** — with no HR approval step, this is the audit trail |
| Block reason | sensitive (may be an allegation) | Explain a block in a grievance | same | **Yes** (D7) |
| Notice acknowledgement rows | internal (personal) | Show which words the person read | same | **Yes** — replaces fields that overwrote history (PRIV-3) |
| First name, surname initial, designation, company on "Is this you?" | internal (personal) | Catch a forwarded code | same | Shown, not stored |
| Field-worker designations, switch, lifetime, change reason | internal | Decide who may use the app | not personal | Yes |
| Daily counts | internal, no person | Pilot measures; retire old versions | not personal | Yes |

**Not collected, by rule (01c §2):** IMEI, Android ID, serial, advertising ID, MAC, phone number, SIM, contacts, installed apps, gallery, location outside a punch.

### 16.2 Obligations engaged

| Obligation | Source | What this slice must do | Feature that does it |
|---|---|---|---|
| Notice, itemised, versioned; record of version seen | DPDP (baseline §2); compliance map A7, G1 | New version with phone model; server-owned rows; history of who read which version; shown again on change | US-14, US-42, US-43 |
| Data minimisation | DPDP | Collect only the listed facts; server ignores extras; no workplace coordinates to the phone | AC-69, AC-76, AC-220 |
| Reasonable security safeguards | DPDP; OWASP ASVS L2 (baseline §5) | Hashes only, single use under a lock, final blocks, permissions on every path, no secrets in logs, host allow-list | US-1, 2, 4, 5, 10, 26, 33 |
| Retention and erasure with legal hold | DPDP; compliance map A6 | Ran-out not deleted; delete per Q-1; keep while punches exist; legal hold wins | US-21 |
| Rights: access and correction | DPDP; compliance map A8 (not built) | Worker sees what is recorded; HR can produce one person's records | US-43, US-28 |
| No personal data in logs | nfr-budget §5; 008 SEC-8 | 014 wrapper on all new endpoints; scanner | US-26 |
| Breach reporting (CERT-In 6 h) | Baseline §3 | Nothing new to build; a leak of photos or positions from this feature is reportable. Detection helps: HR alerts, technical alerts | US-19, US-22 |
| Hosting in France stated before a real customer | Baseline §3a | Nothing in this build; the privacy notice template must say it | — (Q-C, before first customer) |
| Store data-safety forms | Google Play / Apple | Not engaged (no store listing) | — |
| EU AI Act Art. 5 | Baseline §4 | Not engaged: no face matching, no inference | — |

### 16.3 Visibility delta

| Who | Can see after this slice that they could not before |
|---|---|
| HR Manager, HR User, System Manager (own scope) | How each phone joined, the code history, block reasons, acknowledgement history, the fake-location flag on punches |
| Whoever holds a live, eligible code | First name, surname initial, designation, company, the notice rows |
| Whoever holds a dead code | Its outcome and one time |
| The field worker | The notice version and date they agreed, the host, their own join date |
| Alvoraa (Surbhi) | Daily counts per site with no people in them |

**Negative cases — who must NOT see:**
- **Colleagues and line managers** see no phone, code or acknowledgement (AC-150). Line managers see punches as before, nothing more.
- **HR outside their companies** see nothing for other companies (AC-149).
- **The worker never sees the block reason** (AC-2, AC-111).
- **Nobody sees a "last seen", online status or map** (AC-77, AC-107, AC-114).
- **Nobody, including the HR person who made it, sees the code after the dialog closes** (AC-50).
- **A code holder never sees full name, employee ID, contact details or workplace** (AC-53).

### 16.4 Decision automation

**Does this slice automate or materially influence a decision about a person? Yes, in a narrow way.**

| What the system decides | Effect on the person | Accountable human | Where they step in | What the employee is told | How they contest |
|---|---|---|---|---|---|
| Refuses a punch (too far, vague GPS, blocked phone, not a field job, app off) | A missing punch can mean an absent day and less pay | The customer's **HR Manager** | Attendance review; manual Attendance or Attendance Request correction (existing, `attendance_correction.py`) | The exact reason on screen with a "Code for HR" | Show HR the code; HR corrects the attendance |
| Stops a phone when the designation leaves the list or the app is switched off | Must use the web page or the reception machine | **HR Manager** who changed the setting (named in the change history, with a reason) | Restore the setting, or the person uses another way to mark attendance | `appOff` / `notField` with "Keep marking attendance the usual way" | Ask HR; "If your job is wrong in the records, tell HR" |
| Flags a punch with a fake-location flag | May lead HR to question a day | **HR Manager** | The flag only marks; the punch is saved. Refusing such punches is **not** built (Q-U3) | Not shown to the worker in step 1 (Q-11) | Through HR, like any attendance dispute |
| Replaces an old phone at a new join | Old phone stops | **HR person who made the new code** | Block, new code | `replaced` screen: "If that was not you, tell HR today" | Tell HR |

**The system never decides pay, rating or discipline.** No AI, no face matching, no scoring.

### 16.5 Retention and deletion

| What | Kept for | On whose instruction | Survives an erasure request? |
|---|---|---|---|
| Photos | Tenant setting (default 90 days; 0 = keep); legal hold wins | Customer (Fiduciary) | No, unless on legal hold |
| Punches (time, place, fake-location flag) | As attendance records today (unchanged) | Customer | Yes, while the pay record needs them (decision-bearing) — counsel to confirm (Q-C3) |
| Phones and acknowledgement rows | While any linked punch exists | Customer; default proposed here | Yes while punches exist (they explain the punches) |
| Codes | Q-1 default: codes that set up a phone kept with that phone; others deleted 12 months after they ended | **Surbhi (interim compliance owner)** | As phones |
| Block reason | With the phone | Customer | As phones |
| Daily counts | 13 months | Alvoraa | Not personal |
| Logs | Existing rule (180 days), no personal data in them | Alvoraa | Not personal |

### 16.6 ⚠ Open compliance questions

**I flag; I do not rule. None of these blocks the first day of build.**

| # | Question | Who must decide | What it blocks |
|---|---|---|---|
| ⚠ C-1 | Delete codes after 12 months (OPS-52) or keep while punches exist (PRIV-10)? My default reconciles them (Q-1) | Surbhi (interim compliance owner) | AC-129 delete step only |
| ⚠ C-2 | Is "legitimate use for employment" the right basis for photo and precise location (Q-C1)? Does "Remove this phone" need to count as withdrawal? | DPDP lawyer, before the first paying customer (Surbhi's decision) | Final notice words; store listing; first real customer — **not** the build or the pilot |
| ⚠ C-3 | Retention for phones, codes, acknowledgements and exact coordinates (Q-C3) | Lawyer, then Surbhi | Final periods in US-21 |
| ⚠ C-4 | Must the notice be offered in Hindi (Eighth Schedule) rather than optional (Q-C2)? | Lawyer | When D15's "English only" must end |
| ⚠ C-5 | A short DPIA before the first real customer (Q-U8) | Surbhi | First customer |
| ⚠ C-6 | Should the worker see that a punch was flagged as a fake location? (Transparency; not in 01c) | Surbhi with security | Q-11; nothing in step 1 |
| ⚠ C-7 | Refuse punches with the fake-location flag (Q-U3) | Surbhi, with pilot numbers | Nothing now |
| ⚠ C-8 | The notice mentions "HR and your manager"; is "hosted in France" needed in the app notice or only the privacy notice template? | Lawyer | Privacy notice template |

### 16.7 The prohibitions

**No prohibited capability is required.** No AI rating, no emotion, voice or facial inference (photos are looked at by people, never matched), no passive behavioural monitoring (location only at the moment of a punch; no "last seen"; no map), no individual surveillance framed as transparency (the HR phone list has no online status). The fake-location flag is a property of one punch the person chose to make, not a watch on behaviour. The alerts are about codes and phones, not about people's movements.

---

## 17 · Traceability

**Status:** covered · changed (with the user's decision) · not adopted (user's decision) · **gap** (no AC and no user decision) · outside this slice (owner named).

### 17.1 Brief

| Source | Line | Story | ACs | Status |
|---|---|---|---|---|
| Brief §5 S1 | Native shell, bundled page, secret in secure storage, BASE address, facts from an endpoint | US-33, US-35, US-39, US-44 | AC-172–176, 181, 197, 217 | covered |
| S2 | Scan or pick a QR picture | US-35 | AC-183, AC-184 | covered |
| S3 | "Is this you?" | US-8, US-36, US-38 | AC-53, AC-186, AC-195 | covered |
| S4 | One screen for used, expired, revoked codes | US-37 | AC-192, AC-193 | covered |
| S5 | Single use, bound, hash, fragment, audited, revocable, no Pending | US-5, US-7, US-10, US-20, US-21 | AC-38–45, 51, 64–65, 123, 126 | covered; "expired ones cleaned daily" **changed** to "marked Ran out" (PRIV-10) |
| S6 | Three settings | US-3 | AC-14–25 | covered; default lifetime **changed** to 24 h (Surbhi, 2026-09-17) |
| S7 | Desk invite, revoke, device list, block | US-6, US-7, US-16, US-17, US-18 | AC-46–52, 102–115 | covered; "copy link" **not adopted** (Surbhi, 2026-09-17) |
| S8 | Field workers only; refusal with a reason | US-3, US-5, US-12, US-16 | AC-21, 42, 78, 103 | covered |
| S9 | Minimum version, update screen, codes | US-4, US-41 | AC-26–37, 209 | covered |
| S10 | Settings screen: language, records, remove, version | US-43, US-46 | AC-214–216, 224 | covered; language switch hidden in pilot (D15) |
| S11 | Key guards, HTTPS host allow-list, dev and release IDs | US-31, US-32, US-33 | AC-163, 165, 172 | covered |
| S12 | Device-keyed rate limits | US-25 | AC-140, 141 | covered |
| S13 | `/enrol` never redeems | US-20 | AC-123–125 | covered |
| S14 | iPhone on a borrowed Mac | US-47 | AC-227, 228 | covered |
| §7 WOW | Scan → Is this you → Welcome, no HR wait; HR sees the join | US-10, US-36, US-16, US-19 | AC-64, 188, 104, 116 | covered |
| §10 Measure 1 | ≥ 95% first-tap saves | US-22, US-48 | AC-131, AC-233 | covered |
| Measure 2 | ≤ 2 min, zero HR actions | US-48 | AC-234 | covered |
| Measure 3 | ≥ 9 of 10 right person first time | US-48 | AC-234 | covered |
| Measure 4 | 0 punches after block; old build never fails silently | US-1, US-17, US-48 | AC-2, AC-111, AC-234 | covered |
| Kill criteria | < 90% after one fix round → stop | US-48 | AC-233 | covered |
| Gate decisions 1–7 | Designation; off = no codes; lifetime; desk; offline later; no crash tool; 90 days | US-3, US-16, US-34, US-4 | AC-14, 21, 103, 178, 37 | covered (5: offline out of scope) |
| §5 "Nothing may block next increment" 1–5 | Never edit `hrms-employee.html`; bridge-free later; device is the anchor; redemption can grow; never `allow_cors` | US-33, US-24, US-4 | AC-175, AC-138, AC-33 | covered; point 3 and 01c §9 "one revoke function" → **gap** (see 17.6) |

### 17.2 Prototype screens (61)

| Group | Screens | Story | ACs | Status |
|---|---|---|---|---|
| Join (11) | `first`, `camExplain`, `osCam`, `scan`, `checking`, `confirm`, `notMe`, `notMeDone`, `notice`, `joining`, `welcome` | US-35, US-36, US-38 | AC-181–190, 195–196 | covered |
| Attendance (9) | `home`, `locExplain`, `osLoc`, `punching`, `resultIn`, `homeIn`, `resultOut`, `homeOut`, `camOff` | US-39 | AC-197–203 | covered |
| Join problems (9) | `qrExpired`, `qrUsed`, `qrCancelled`, `notAlvoraa`, `appOff`, `notField`, `noSignalJoin`, `camDenied`, `pickNoQr` | US-35, US-37 | AC-183–185, 192–194 | covered |
| Check-in problems (7) | `locDenied`, `locOff`, `gpsVague`, `outside`, `noSignal`, `duplicate`, `tooMany` | US-40 | AC-205, 208 | covered |
| Phone stopped (6) | `update`, `blocked`, `replaced`, `left`, `serverError`, `unknownCode` | US-41, US-40 | AC-206, 207, 209–212 | covered |
| Settings (5) | `settings`, `records`, `noticeAgain`, `leaveConfirm`, `removed` | US-43, US-42 | AC-213–216 | covered |
| Desk: Employee record (9) | `empField`, `inviteCreate`, `inviteShow`, `printSheet`, `empInvited`, `cancelConfirm`, `empJoined`, `blockConfirm`, `empBlocked` | US-6, US-7, US-16, US-17 | AC-46–51, 102–113 | covered |
| Desk: Not available (2) | `empNotField`, `empAppOff` | US-16 | AC-103 | covered |
| Desk: Settings, lists (3) | `fieldSettings`, `settingsOffConfirm`, `deviceList` | US-3, US-18 | AC-17, 23–25, 114 | **changed**: settings become an HR Settings section (Q-5, needs Surbhi's agreement); retention link removed (Q-4) |
| Not drawn, described | remove-a-designation confirm; plan-without-field-check-in state; `featureOff` | US-3, US-16, US-37 | AC-18, AC-103, AC-192 | covered |

### 17.3 Design decisions

| D | Decision (accepted 2026-09-17) | Story | ACs | Status |
|---|---|---|---|---|
| D1 | No bottom bar | US-35 | AC-181 | covered |
| D2 | "This is not me" cancels | US-9, US-38 | AC-61, AC-195 | covered |
| D3 | New phone replaces old | US-11 | AC-72–75 | covered (web phone: Q-3) |
| D4 | No unblock | US-2, US-17 | AC-7, AC-112 | covered |
| D5 | App off / designation removed stops joined phones | US-3, US-12, US-41 | AC-78, AC-161, AC-211 | covered |
| D6 | Shorter per code, never longer | US-5, US-6 | AC-40, AC-46 | covered |
| D7 | Block reason required | US-17 | AC-110 | covered |
| D8 | Used-code screen shows the time | US-8, US-37 | AC-54, AC-192 | covered |
| D9 | Light theme pinned | US-35 | AC-181 | covered |
| D10 | Remove needs internet | US-15, US-43 | AC-99, AC-216 | covered |
| D11 | Code for HR on every problem screen | US-37, US-40 | AC-192, AC-205 | covered |
| D13 | "you" only for the maker | US-16 | AC-104 | covered |
| D14 | No employee ID on the sheet | US-6 | AC-49 | covered |
| D15 | English only in pilot | US-46 | AC-224 | covered |
| D17 | One waiting code | US-5 | AC-41 | covered |
| D18 | No employee-ID join in the app | US-35 | AC-181 | covered |
| D19 | New notice version | US-14, US-42 | AC-92–97, 213 | covered |
| D20 | HR Manager changes settings | US-3 | AC-15, AC-16 | covered |
| D12, D16 | Folded into the design (01b §11) | — | — | not separate decisions |

### 17.4 Security (SEC) and privacy (PRIV)

| ID | Story | ACs | Status |
|---|---|---|---|
| SEC-1 | US-5 | AC-38, AC-39 | covered |
| SEC-2 | US-5, US-6, US-20 | AC-45, AC-47, AC-123, AC-124 | covered |
| SEC-3 | US-8 | AC-53–56 | covered (unknown code = `QR_NOT_RECOGNISED`) |
| SEC-4 | US-5 | AC-40, AC-58 | covered |
| SEC-5 | US-10, US-11 | AC-64–68, AC-72 | covered |
| SEC-6 | US-5 | AC-41 | covered |
| SEC-7 | US-7, US-9, US-23, US-10 | AC-51, 61, 135, 68 | covered |
| SEC-8 | US-2 | AC-7, AC-12 | covered |
| SEC-9 | US-2, US-27 | AC-8–10, AC-149 | covered |
| SEC-10 | US-1 | AC-1–5 | covered (with `DEVICE_PENDING` per slice 014; Q-2) |
| SEC-11 | US-26 | AC-146, AC-147 | covered; depends on slice 014 |
| SEC-12 | US-25, US-19 | AC-140, 141, 120 | covered |
| SEC-13 | US-19 | AC-116–122 | covered |
| SEC-14 | US-33, US-11 | AC-172, 176, 74 | covered |
| SEC-15 | US-8 | AC-57 | covered (unknown-host bench check W3 stays with security) |
| SEC-16 | US-33, US-44 | AC-173–175, 221 | covered |
| SEC-17 | US-45 | AC-222, 223 | covered |
| SEC-18 | US-24 | AC-138, 139 | covered |
| SEC-19 | US-4 | AC-29 | covered |
| SEC-20 | US-34 | AC-177, 178 | covered |
| SEC-21 | US-13, US-39 | AC-85, AC-204 | covered |
| SEC-22 | US-15, US-43 | AC-99, AC-216 | covered |
| SEC-23 | US-31 | AC-163 | covered |
| SEC-24 | US-4 | AC-28 | covered |
| SEC-25 | US-26 | AC-148 | covered |
| PRIV-1 | US-10, US-44 | AC-69, AC-220 | covered |
| PRIV-2 | US-14, US-42 | AC-92, 93, 96, 213 | covered |
| PRIV-3 | US-14, US-29 | AC-94, AC-155 | covered |
| PRIV-4 | US-14 | AC-97 | covered |
| PRIV-5 | US-8, US-36 | AC-53, AC-186 | covered |
| PRIV-6 | US-12 | AC-76 | covered |
| PRIV-7 | US-35, US-44 | AC-184, AC-219 | covered |
| PRIV-8 | US-34 | AC-177, AC-180 | covered |
| PRIV-9 | US-12, US-16, US-18 | AC-77, 107, 114 | covered |
| PRIV-10 | US-21 | AC-126, AC-129 | covered; periods per Q-1 / C-3 |
| PRIV-11 | US-22 | AC-131 | covered |
| PRIV-12 | US-28, US-43 | AC-153, AC-215 | covered |
| PRIV-13 | US-17, US-1 | AC-2, AC-111 | covered |
| PRIV-14 | US-13 | AC-89 | covered |
| PRIV-15 | US-48 | AC-235 | covered |

### 17.5 DevOps (OPS)

| ID | Story | ACs | Status |
|---|---|---|---|
| OPS-1 | US-24 | AC-138 | covered |
| OPS-2 | US-24 | AC-138 | covered (engineer's choice, tested either way) |
| OPS-3 | US-33 | AC-175 | covered for step 1 (no remote pages); bridge-free My HR is the next increment |
| OPS-4 | — | — | **outside this slice**: store accounts and D-U-N-S, Surbhi (applying) |
| OPS-5 | US-32 | AC-167 | covered |
| OPS-6 | US-31 | AC-163 | covered |
| OPS-7 | US-33 | AC-172 | covered |
| OPS-8 | US-4 | AC-33 | covered |
| OPS-9 | US-48 | AC-229 | covered; wildcard certificate live (Surbhi, 2026-09-17) |
| OPS-10 | US-25 | AC-140 | covered |
| OPS-11 | — | — | **outside this slice**: App Links are "later" (brief §5 out of scope, approved at the gate) |
| OPS-12 | — | — | **outside this slice**: compression is for the My HR tab (slice 012 OPS-26) |
| OPS-13 | US-5, US-20 | AC-38, AC-123 | covered |
| OPS-14 | US-34 | AC-178 | **not adopted** — no crash tool in the pilot (gate decision 6, Surbhi) |
| OPS-15 | US-32 | AC-171 | covered |
| OPS-16 | — | — | FYI, no action in step 1 (developer verification from 2027); **not traced** |
| OPS-17 | — | — | FYI for My HR; **not traced** |
| OPS-18 | — | — | FYI for My HR; **not traced** |
| OPS-19 | — | AC-145 (dependency check) | **owned by slice 014** |
| OPS-20 | US-26 | AC-145, AC-146 | **owned by slice 014**; this slice applies its wrapper |
| OPS-21 | US-39, US-13 | AC-201, AC-87 | covered |
| OPS-22 | US-34 | AC-179 | covered |
| OPS-23 | US-48 | AC-232 | covered (decided during the pilot) |
| OPS-24 | US-8, US-12, US-39 | AC-53, 76, 202, 203 | covered |
| OPS-25 | US-44, US-4 | AC-217–221, AC-28 | covered |
| OPS-26 | US-4, US-40 | AC-26, AC-206 | covered |
| OPS-27 | US-4 | AC-29, AC-37 | covered |
| OPS-28 | US-1 | AC-1–4 | covered |
| OPS-29 | US-25 | AC-140–144 | covered |
| OPS-30 | US-2, US-3, US-10, US-11 | AC-7, 78, 65, 72 | covered |
| OPS-31 | US-14, US-42 | AC-92, 96, 213 | covered |
| OPS-32 | US-6, US-20 | AC-45, 47, 125 | covered |
| OPS-33 | — | — | **gap — waiting for Surbhi**: binary photo upload "later, not now" (DevOps' own advice); no decision recorded |
| OPS-34 | US-22 | AC-131 | covered |
| OPS-35 | — | — | FYI (storage growth); **not traced** |
| OPS-36 | US-48 | AC-232 | covered |
| OPS-37 | US-31 | AC-163, AC-164 | covered |
| OPS-38 | US-32 | AC-165–167 | covered |
| OPS-39 | US-32 | AC-170 | covered (Bitwarden + offline copy, Surbhi 2026-09-17) |
| OPS-40 | US-32 | AC-168 | covered |
| OPS-41 | US-32 | AC-169 | covered |
| OPS-42 | US-47 | AC-227, AC-228 | covered |
| OPS-43 | US-26 | AC-145 | covered |
| OPS-44 | US-4 | AC-27, 30, 31, 32 | covered |
| OPS-45 | US-24 | AC-137 | covered; **push needs Surbhi's go-ahead** (production nginx) |
| OPS-46 | US-25 | AC-140, AC-141, AC-36 | covered |
| OPS-47 | US-24 | AC-138 | covered |
| OPS-48 | US-4 | AC-29, AC-37 | covered |
| OPS-49 | US-4 | AC-26, AC-34, AC-35 | covered |
| OPS-50 | US-1, US-29 | AC-5, AC-154 | covered, **changed**: hash moved to a retired field, not wiped (Q-2) |
| OPS-51 | US-10, US-5 | AC-65, AC-70, AC-41 | covered |
| OPS-52 | US-21 | AC-126–130 | covered; delete period per Q-1 |
| OPS-53 | US-3, US-12, US-30 | AC-14, 78, 79, 160, 161 | covered |
| OPS-54 | US-48 | AC-229 | covered |
| OPS-55 | US-33 | AC-172, AC-173 | covered |
| OPS-56 | US-48 | AC-230 | covered, **changed**: Firebase on Surbhi's own Google account, not a company account with two owners (Surbhi, 2026-09-17) |
| OPS-57 | US-48 | AC-231 | covered; phones partly owned, rest borrowed (Surbhi) |
| OPS-58 | US-41, US-4 | AC-209, AC-37 | covered |
| OPS-59 | US-22 | AC-131, AC-132 | covered |
| OPS-60 | US-26 | AC-147 | covered |
| OPS-61 | US-22, US-19 | AC-133, AC-116–120 | covered; owners per Surbhi's answer |
| OPS-62 | US-25 | AC-142, AC-143 | covered |
| OPS-63 | US-48, US-36, US-39 | AC-232, 191, 201 | covered |
| OPS-64 | US-30 | AC-162 | covered |
| OPS-65 | US-30 | AC-161 | covered |
| OPS-66 | — | — | FYI; **not traced** |

### 17.6 Not traced, and why

| Item | Why | Owner |
|---|---|---|
| **01c §9 point 2 "one revoke function" and brief §5 point 3** | Not a numbered SEC item, so it had no AC. It matters for the next increment. **Gap** — proposed AC for the engineer: "blocking, replacing, removing and the leaver hook each call one server function (a test asserts each path calls it)". Add to US-2 if Surbhi agrees | Security engineer / Surbhi |
| OPS-4 | Store accounts, D-U-N-S — paperwork, not this build | Surbhi |
| OPS-11, OPS-12, OPS-17, OPS-18 | App Links and My HR items, out of scope by the approved brief | Next increment |
| OPS-14 | Not adopted (gate decision 6) | Surbhi (decided) |
| OPS-16, OPS-35, OPS-66 | FYI only | — |
| OPS-19, OPS-20 | Owned and built by slice 014; this slice checks the dependency | Slice 014 |
| OPS-33 | **Waiting for Surbhi's decision** | Surbhi |
| Brief open questions 6, 11, 12 | Store name, My HR user accounts, compliance owner (now Surbhi interim) | Next increment / Surbhi |


---

## Open questions

**None blocks the first day of work.** US-31, US-1, US-2 and US-4 can start at once (locally).

| # | Question | Owner | My default | Blocks |
|---|---|---|---|---|
| Q-1 ⚠ | Codes: delete after 12 months (OPS-52) or keep while punches exist (PRIV-10)? | Surbhi (interim compliance owner) | Keep codes that set up a phone with that phone; delete the rest 12 months after they ended | AC-129 delete step |
| Q-2 | Move the secret hash to `retired_token_hash` instead of wiping it (OPS-50 vs SEC-10/D3)? | DevOps + security | Yes, move it | AC-5 wording; the replaced/removed screens |
| Q-3 | When a field worker joins the app, should their Active or Pending **web-page** phone also stop? 01c SEC-5 says app phones only; D3 says one working phone per person | Security + Surbhi | Follow 01c (app phones only) until decided | AC-73 |
| Q-4 | The settings "change retention" link points at a screen that does not exist. Show the number only, or add a retention field to the same HR Settings section? | UX designer + Surbhi | Number only, no link | AC-23 wording |
| Q-5 | Settings as a section of HR Settings instead of the prototype's separate "Field App Settings" page — agreed? | Surbhi | HR Settings section (CLAUDE.md §4) | Desk layout of US-3 only |
| Q-6 | HTTP status per code (§7.1) | Engineer at strategy; frozen at first pilot build | As proposed | Nothing before the app's first build |
| Q-7 | Notification wording N1–N5, `/enrol` copy, `QR_NOT_RECOGNISED` screen copy | UX designer | Drafts in §10, AC-123, AC-193 | Copy only |
| Q-8 | New endpoint E9 and new codes `DEVICE_PENDING`, `DEVICE_REMOVED`, `QR_NOT_RECOGNISED`, `LOCATION_MISSING`, `INVALID_REQUEST` added to the contract — confirmed? | DevOps + security | Yes | US-4 code list |
| Q-9 | Multi-company tenants get one designation list. Acceptable for step 1? | Surbhi | Yes for step 1 | Nothing now |
| Q-10 | Allow app codes and punches before an employee's joining date? | Surbhi | Allow (today's behaviour) | Nothing now |
| Q-11 ⚠ | Should the worker see that a punch was flagged as a fake location? | Surbhi with security | Not in step 1 | Nothing now |
| Q-12 | Add the "one revoke function" AC (01c §9 point 2) to US-2? | Security + Surbhi | Yes, +1 point on US-2 | Next increment's session end |
| Q-13 | Invite dialog offers 1 h, 4 h, 1 day, 3 days, 7 days in `01b`; settings offer 12 hours too. Same six in both? | UX designer | Same six in both | AC-46 list |
| Q-14 | "Remove {company} from this phone" on blocked, replaced and left screens clears the phone only, with no server call (the server already refuses it). OK? | UX + security | Yes | AC-210 |
| Q-15 | Refuse punches with the fake-location flag (Q-U3) | Surbhi, with pilot numbers | Flag only | Nothing now |

### OPS items still waiting for Surbhi

| OPS | What needs your word | When |
|---|---|---|
| OPS-43 (with slice 014) | Push slice 014 to dev (after the 010 D + 012 push 1 release, and after rebasing 014 onto the wildcard nginx file) | Before any 013 server code goes to dev |
| OPS-45, OPS-47 | Any nginx change (body caps, device zone, CORS) — it is the production nginx too | Before pushing US-24 |
| OPS-37 (3) | Confirm GitHub push protection is on | Week 1 |
| OPS-38 | Approve each pilot build in the `mobile-pilot` environment | Each pilot build |
| OPS-52 | Invite retention period (Q-1) | Before AC-129 ships |
| OPS-54 | Demo tenant settings on dev: designations, switch, 7-day photo retention (a dev-stage action) | Before the pilot |
| OPS-58 | Raising the minimum version during the pilot (testers told a day ahead) | When needed |
| OPS-64 | Each rollout step 1–8 | Step by step |
| OPS-33 | Binary photo upload — defer or not | Any time |
| OPS-4 | Organisation store accounts, D-U-N-S | Store release only |
| OPS-23 | QR model inside the app or downloaded | After the pilot phones are tried |

---

## Assumptions

- [ASSUMPTION] Slice 014 lands on dev as built on its branch, including `_private_request` and the "unknown secret answers like Pending" rule.
- [ASSUMPTION] Frappe applies an HR User's Employee or Company User Permissions to doctypes that link Employee (W1). If the AC-149 test shows it does not, a query condition and `has_permission` hook are added, as `Employee Checkin` already has, plus a `company` field if needed.
- [ASSUMPTION] Frappe renames update links inside a `Table MultiSelect` child table when a Designation is renamed.
- [ASSUMPTION] `Employee.first_name`, `last_name`, `designation`, `company` hold the data "Is this you?" needs (seen in test fixtures and `field_status`; ERPNext's JSON not read — ERPNext is not in this repo).
- [ASSUMPTION] Frappe's notification settings decide whether a Notification Log also sends email, and the default is acceptable to HR.
- [ASSUMPTION] Clipboard image copy works in the desk browsers HR uses (Chrome on HTTPS). If not, the dialog says "Right-click the picture to copy it".
- [ASSUMPTION] An index on `Employee Checkin (employee, time)` exists in Frappe HR [UNVERIFIED — engineer to confirm].
- [ASSUMPTION] Pilot testers are employees or friends of Alvoraa, invented as employees on the demo tenant; their faces are real (PRIV-15).
- [ASSUMPTION] Everything the prototype shows as "Sample" (counts, names, dates) is invented.
- [ASSUMPTION] The 12-month invite retention starting point in OPS-52 is DevOps' assumption, not a legal answer.

---

## Ready check — Definition of Ready

| Item | Pass / fail | What is missing |
|---|---|---|
| One named user, one complete outcome | **Pass** | Brief §5 |
| Job to be done in the user's words | **Pass** | Brief §1 |
| Competitive analysis, labelled, with what we will not copy | **Pass** | Brief §3, 01a §4 (all "read", none "seen") |
| Kano class, survey or proxy | **Pass** | Brief §4, proxy |
| Persona enhancements decided | **Pass** | Brief §6 |
| WOW moment named and achievable | **Pass** | Brief §7; AC-64, AC-188 |
| Out of scope written | **Pass** | Brief §5 |
| User approved the brief | **Pass** | Gate decision 2026-09-17 |
| Clickable prototype reviewed at the design check | **Pass** | Design check decision 2026-09-17 |
| User's feedback logged in `ux-learnings.md` | **Partial** | The designer's lessons are logged; line 152 still lists D1–D20 as open. The user's acceptance of D1–D20 and the 24-hour lifetime are not yet logged. Owner: UX designer. Does not block build |
| Every state designed: empty, loading, error, no permission, first-time | **Pass**, with three small gaps | Drafts needed for `/enrol`, `QR_NOT_RECOGNISED`, notification copy (Q-7) |
| `01c` written with SEC and PRIV | **Pass** | SEC-1–25, PRIV-1–15 |
| `07` §1–3 with OPS items | **Pass** | OPS-1–66 |
| Gap analysis against real source | **Pass** | §2 |
| Epic and stories, INVEST, sized, linked, "must not" stories | **Pass** | 48 stories, 162 points |
| Every story has Given/When/Then with an oracle | **Pass** | 234 ACs |
| Traceability complete | **Pass with 2 open items** | OPS-33 waits for Surbhi's decision; the "one revoke function" item (Q-12) has no AC yet. FYI rows and items owned elsewhere are listed with reasons |
| Permission matrix with negative cases | **Pass** | §8 |
| Edge cases | **Pass** | §11 |
| NFR numbers made specific | **Pass** | §12 |
| Migration and backfill stated | **Pass** | §13 |
| Compliance sub-analysis | **Pass** | §16 |
| Every ⚠ COMPLIANCE question names a human and what it blocks | **Pass** | §16.6 |
| No prohibited capability | **Pass** | §16.7 |
| New Frappe app checklist | **Not applicable** | No existing Frappe app is installed (01c §12) |
| Open questions have owners; none blocks day one | **Pass** | 15 questions |

**Verdict: Ready, with one partial box and two traceability items to close.** Fewer than two boxes fail, so the slice does not go back. **Two conditions stand outside this checklist:** slice 014 must be on dev before any of this slice's server code is pushed, and Surbhi must agree Q-1, Q-2, Q-3 and Q-5 before the stories that depend on them are finished (they do not stop the stories starting).

---

## Handoff note

To the full-stack engineer (and DevOps and security for the strategy view): **start with US-31 before any key exists, then US-1, US-2 and US-4 as one first server change that is never reverted.** Build on slice 014's branch state — reuse `_private_request` on every new guest endpoint, and keep its rule that a well-formed unknown secret gets the same answer as a Pending phone, or the employee-ID leak comes back. **I diverged from two inputs and said so rather than building around them:** the secret hash is moved to `retired_token_hash`, not wiped (Q-2), and the settings live in HR Settings, not in a new page (Q-5). If DevOps, security or Surbhi disagree, change the spec before the code. Watch four places where a quiet mistake would do real harm: the E3 locked save (lock Employee, then invites, then phones, always in that order), the status rules on **every** entry path (form, list edit, import, REST), the web page (its screens and sentences must not change, AC-35), and HR Settings, which `alvoraa_goals` also validates. Nothing in this slice may touch `www/hrms-employee.html`, and nothing goes to dev, `main`, nginx or a tenant's settings without Surbhi's explicit word.

---

## User decisions (Surbhi, 2026-09-17)

The analyst's recommended defaults are **accepted**:

- **Q-1 Invite retention:** keep any code that set up a phone for as long as that phone has punches; delete other codes after 12 months (also settles OPS-52 and compliance flag C-1 for now).
- **Q-2 Replaced phones:** move the old device's secret hash into a hidden `retired_token_hash` field instead of wiping it, so the old phone can still be told "You joined on another phone".
- **Q-3 Web-page phones:** an app join stops only earlier **app** phones, not phones set up on the web check-in page (as in 01c).
- **Q-5 Settings location:** a "Field attendance app" section in **HR Settings**, not a separate page.
- **OPS-33 Binary photo upload:** **deferred** to a later increment.

Also agreed: start `/slice-build 013-mobile-app`; draft a Data Processing Agreement template and an employee privacy notice template for a DPDP lawyer to review.

---

## Consent gate (Surbhi, 2026-09-17)

**An employee must not be able to use the app unless they give consent.** This replaces the earlier working position that the notice screen only asks the employee to confirm they have read it.

- The notice screen asks for an explicit **"I agree"** (not only "I have read this"). Without it the join does not complete and nothing is set up on the phone; no check-in is possible.
- Consent is recorded with time, notice version and phone (append-only history, as already planned for acknowledgements).
- When the notice changes (D19), the app is blocked until the employee agrees to the new version.
- **Withdrawal:** "Remove this phone" (and HR blocking) ends app use; withdrawing consent must be as easy as giving it `[LAWYER TO CONFIRM]`.
- **Consent must be freely given:** an employee who says no must still have another way to mark attendance (web check-in page without photo/location, reception machine, or HR marking it) and must not be penalised. This keeps the consent valid under DPDP s.6 `[LAWYER TO CONFIRM]`.
- Legal basis for the app's photo and location is therefore **consent** (DPDP s.6), not only employment legitimate use; the customer company remains the Data Fiduciary. The lawyer review before the first paying customer must confirm the wording and the alternative-method requirement.

Affects: PRIV-4 (tick-box wording), the join flow ACs, the notice-changed flow, the privacy notice template, and the "decline" state (a new screen: "You chose not to agree. You can mark attendance the usual way. You can set up the app later with a new code from HR.").

### Changing their mind (Surbhi, 2026-09-17)

**An employee who does not agree gets the chance to agree the next time they open the app.**

Recommended mechanism (keeps the QR code off the phone, per 01c):
- At "Is this you? → Yes", if the employee reaches the notice and chooses **Not now / I do not agree**, the code is used to link the phone in a **"Consent not given"** state. The phone keeps its device secret in secure storage, but **cannot check in**, and the server refuses every punch with a consent code (e.g. `CONSENT_REQUIRED`).
- **Every time the app opens** while in that state, it shows the notice again with **"I agree"** and **"Not now"**. Agreeing records consent (time, version, phone) and makes the phone Active; no new code from HR is needed.
- The same applies when a **changed notice** is declined on an already-joined phone: it stays linked, cannot check in, and asks again on the next open.
- HR sees the phone as **"Joined · consent not given"** (no reason shown, no pressure prompts), and can still block or remove it. No reminders are sent to the employee beyond the prompt on opening the app `[LAWYER TO CONFIRM]` — so the choice stays free.
- Blocking, "Remove this phone" and the retention job treat a "Consent not given" phone like any other; it holds no photos or locations.

### Purpose and reminders (Surbhi, 2026-09-17)

- **Why the app matters:** it is meant to cover employees who intentionally do not check out (auto-checkout comes in step 2), so the business wants field workers on the app.
- **Keep asking until they agree:** an employee who has not given consent is **reminded to give consent every time they open the app, until they agree** (as in "Changing their mind"). No automatic effect on pay or attendance for not agreeing. Whether further reminders (e.g. push notifications, or HR follow-up) would amount to pressure is `[LAWYER TO CONFIRM]`.
- **Alternative for those who decline:** **HR or the manager marks attendance** (or the reception machine) — confirmed possible by Surbhi; lawyer to confirm this keeps consent freely given.

---

## Approvals and clarifications (Surbhi, 2026-09-17, later)

- **Strategy approved** (00-impact-analysis.md, with the engineer's recommended answers to C-1..C-17 and DevOps §4 conditions: QR reader chosen by a side-by-side test of jsQR vs zxing-wasm on the pilot phones with the decoder bundled; a CI check for drift between the web page and app copies of the camera/photo/GPS code, with a dated merge plan after the pilot; `ci.yml` keeps running on `mobile/` pushes). **Build locally only; no push.**
- **Changing phone deletes nothing.** Photos and locations stay and follow the normal retention (default 90 days).
- **"Remove this phone" is not a withdrawal of consent.** It only removes the phone. Withdrawing consent is a separate, explicit choice.
- **Deleting a person's photos and exact locations on withdrawal of consent: not built now.** Wait for the DPDP lawyer to say whether it must happen immediately or whether normal retention is enough; add before the first customer if required. The attendance record (time, present) is never deleted by this.
