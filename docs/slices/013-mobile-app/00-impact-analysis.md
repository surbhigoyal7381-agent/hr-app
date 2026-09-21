---
slice: 013-mobile-app
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-09-17
status: draft — step 1 and 2 of the change process. Waiting for Surbhi's approval. No code written.
inputs: [02-functional-spec.md (incl. "User decisions", "Consent gate" and "Changing their mind", all 2026-09-17), 01-product-brief.md (Gate decision), 01b-ux-design.md (Design check decision), prototype-v1/index.html, 01c-security-privacy-requirements.md (incl. User decisions, Consent gate, Changing their mind), 07-devops-inputs.md §1–§3 (incl. User answers), 00-sequencing-recommendation.md, 014-checkin-security-fixes/00-impact-analysis.md (Strategy approval, Pre-push checks run), 014 03-implementation-notes.md (on branch slice/014-checkin-security-fixes), field_checkin.py (on the 014 branch), www/field-checkin.html, www/field_checkin.py, alvoraa_field_device.json and .py, subscription.py, hooks.py, hr_api.py, alvoraa_goals/review_items.py, hrms hr_settings.json and employee_checkin.json, .github/workflows, deploy/Dockerfile, deploy/nginx.conf (014 branch), work board]
---

# 013 — Mobile app, step 1 — impact analysis and strategy

**I recommend. You decide.** Nothing here is built. I did not create a worktree, did not
commit, did not install anything, and did not touch the local bench. I read files, ran
`git` commands, and ran read-only checks on this PC (`node -v`, `java -version`, folder
checks). I read one web page (Capacitor's setup page).

---

## Read this first — bad news first

1. **Two new decisions from you change the spec, and the spec has not caught up yet.**
   "Consent gate" and "Changing their mind" (both 2026-09-17) turn the notice tick box into
   a real **"I agree"**, and add a phone that is linked but not agreed. Several accepted
   ACs now say the opposite. The clearest one: **AC-97 says no screen may say "I agree"**,
   and PRIV-4 says the same. I list every AC that must change in §7. **The business analyst
   should update the spec before US-10, US-14, US-36 and US-42 are built.** US-1, US-2,
   US-4 and the app guard (US-31) do not wait for it.

2. **A worker who says "no" may have no real other way to mark attendance.** Your decision
   says a person who declines must still be able to mark attendance, "for example the web
   check-in page without photo or location". **That page does not exist.** Today's web
   check-in page also takes a photo when the camera works, **always needs the location**
   (`_require_position` refuses a punch without it), and has its own tick box. The portal's
   Check In needs a Frappe login, which field workers do not have. So the real other ways
   today are: **the reception machine, or HR marking the attendance by hand.** If that is
   not enough for consent to count as "freely given", something new is needed. **This is a
   decision for you, and a question for the lawyer** (decision C-3 in §12).

3. **Slice 008's field check-in has no Python tests.** I searched every test folder. Only
   slice 014's new file (13 tests) and one plan-gate list test touch `field_checkin.py`.
   So "the web page keeps working exactly as before" (AC-35) is protected by nothing today.
   **I will write tests that pin today's web behaviour first, before changing anything.**

4. **Slice 014 is not on `dev`, and it needs work before it can go.** Its five commits sit on
   `slice/014-checkin-security-fixes`, built on an older base (`8a53522`). Its Frappe tests
   have not run. Its nginx commit uses the old certificate paths and must be rebased onto
   `main`'s wildcard-certificate commit `d6613ea`, which is still not on `dev`. **This slice's
   server code builds on 014's file, so 014 goes first** (§10).

5. **This slice changes the answers slice 014's tests pin.** 014's test
   `test_014_refusal_response_shape_unchanged` expects HTTP 417 for a bad check-in type.
   The error-code contract gives that case 400 (`INVALID_REQUEST`). The web page does not
   care about the number (it only checks "not OK" and matches the sentence), so this is
   safe, **but the 014 test must be updated in a commit that says why.**

6. **This is a big slice.** About **113 server points and 61 app points** after the consent
   changes and the "one revoke function" (was 104 + 58). My estimate is **5 to 6 weeks of
   server work and 4 weeks of app work**, plus a 5-day pilot. See §11.

7. **The PC can build Android apps only after installing Android Studio.** Node 24 is here
   and new enough. Java 25 is here, but Android Studio brings its own Java and that is the
   one to use. No Android SDK is installed. The PC has 16 GB of memory, and Docker (the
   local bench) already uses a lot of it. **iPhone builds need a Mac.** See §9.

**What is good.** Most hard parts exist and are reused: the punch record (`Employee
Checkin`), Frappe HR's geofence, private photos, the photo access log, the plan gate, and
slice 014's log wrapper `_private_request`. The web page only matches on English sentences
and "not OK" status, so adding codes to the answers does not break it.

---

## 1 · Cross-module reach

| App or area | Touched? | How |
|---|---|---|
| **`alvoraa_portal`** | **Yes, main home** | `field_checkin.py` (guest endpoints), new small modules for codes, invites, consent and device changes, `Alvoraa Field Device` (fields, statuses, rules, permissions), 3 new doctypes, `www/enrol.html`, `www/field-checkin.html` (notice rows from the server, FC-1, FC-2 only), `hooks.py` (append only), `patches.txt` (append only), `subscription.py` (`TENANT_DOCTYPES`, append only), one Script Report, an Employee desk script, `health.py` (daily counts), tests |
| **`hrms` (our fork)** | **Read and extend, no edit to its files** | `HR Settings` gets custom fields made by `alvoraa_portal` code (the slice 010 pattern). `Employee Checkin` gets one custom field (`alvoraa_mock_location`). Geofence, `Shift Assignment`, `Shift Location` reused as they are |
| **`erpnext`** | Read only, plus one custom field | `Employee` (status, names, designation, company) gets one HTML custom field for the desk section. `Designation`, `Company` read only |
| **`frappe`** | Used, never edited | Notification Log, Version history, Singles, cache, scheduler, REST |
| **`alvoraa_goals`** | **Indirectly** | Its `validate_hr_settings` hook runs on every HR Settings save. Both apps' hooks must pass (AC-158). No file of `alvoraa_goals` changes |
| **`alvox_compensation`** | No | — |
| **New Capacitor app** | Yes | New top-level folder **`mobile/field-app/`** (see §8). Not a Frappe app. Not copied into the Docker image: `deploy/Dockerfile` copies only `hrms`, `alvoraa_goals`, `alvoraa_portal` (read) |
| **CI** | Yes | One step added to `ci.yml` lint job (key-file check + secret scan, US-31). A **new** workflow `mobile.yml` for app checks, run only when `mobile/**` changes. Pilot build workflow later (US-32) |
| **`deploy/nginx.conf`** | Yes, **last, own commit, own go-ahead** | Body caps on device paths and one per-IP zone (US-24). **No CORS lines** (§8.6). This file also serves production |
| **`www/hrms-employee.html`** | **Never** | Line B rule |

**What the public repo means for `mobile/`.** The repo is public. The app source holds no
secrets: no keys, no `google-services.json` (the app has no Firebase code), no tenant
addresses except the `*.alvoraa.co` pattern. Keys live in Bitwarden and in GitHub
environment secrets (OPS-39).

**One side effect to fix with DevOps.** `build-image.yml` builds and deploys on **every**
push to `dev`, and a dev deploy restarts the nginx that also serves production. A push that
only changes `mobile/` would still trigger it. I recommend adding `paths-ignore: mobile/**`
to the push trigger of `build-image.yml` (and `deploy.yml` if it has its own trigger).
That is a workflow change, so **DevOps confirms in `07` §4, and you decide.**

### HRMS domains

| Domain | Effect |
|---|---|
| **Attendance / Employee Checkin** | Direct. App punches land in `Employee Checkin` beside machine punches, with `device_id = alvoraa-field-app` as today, plus the fake-location flag. Auto attendance unchanged |
| **Geofence** | Reused unchanged (`validate_distance_from_shift_location`). Only the wording becomes a code with values |
| **Employee** | Read at every device call (status, designation). A leaver's phones and codes stop (existing hook, extended). One new HTML field on the form |
| **Designation** | Decides who is a field worker, through a list in HR Settings |
| **Plan gating** | `requires_feature("field_checkin")` stays on every device endpoint and on the HR endpoints. Its refusal also gets the code `FEATURE_OFF` |
| **Payroll** | Indirect only: a refused punch can mean an absent day. No payroll code changes |
| Leaves, appraisals, goals, compensation | None |

---

## 2 · Persona impact

| Persona | What changes |
|---|---|
| **Field worker** (no Frappe user) | Joins by scanning HR's QR code in the app. Sees "Is this you?", then the notice with **I agree / Not now**. On "I agree": works at once. On "Not now": the phone is linked but cannot check in, and the notice is shown again each time the app opens. Can remove the phone. Never sees the block reason. The web check-in page keeps working as before for those who use it |
| **HR User** | Can make and cancel codes, and block phones, **only for employees Frappe lets them read**. Sees phones, codes and consent history. **Loses** write on how a phone joined, who it belongs to, and cannot unblock. Cannot change the new settings |
| **HR Manager** | Everything HR User has, plus the "Field attendance app" section of HR Settings. **Loses create and delete** on phone records (today they have both) |
| **System Manager / CXO** | Same as HR Manager, for all companies. Also loses create and delete on phone records. Administrator is not limited by Frappe (noted, unchanged) |
| **Line manager** | Nothing new. Sees team punches and photos as today. Cannot see phones, codes or consent rows |
| **Employee who is not a field worker** | Nothing new. HR cannot invite them. They cannot see any phone, code or consent row. They can read HR Settings (they can today); nothing personal is in the new fields |
| **Guest with a code** | Sees first name, surname initial, designation, company and notice rows for a live code; only an outcome and one time for a dead code |
| **Alvoraa (Surbhi)** | Gets daily counts with no names, and four technical alerts |

---

## 3 · Every function I will change, and every caller (grep)

Grep run on 2026-09-17 over the whole repo (excluding `docs/`), on the main checkout and
on the 014 branch. Where a function has no caller outside `field_checkin.py`, it is said.

| Function or thing | Callers found | What changes for the callers |
|---|---|---|
| `register_device` | `www/field-checkin.html:749` (`call("register_device", …)`), `:24` (comment), `:1131` (sample mode); 014 tests `test_014_register_device_*`; `test_014_endpoints_are_wrapped` | Answer shape **unchanged** (014 rule). New: writes one consent row for a real employee; checks the new notice version; refusals carry a code too. Web page unaffected |
| `field_checkin` (punch, E5) | `www/field-checkin.html:893`; comment `:25`; 014 tests (5) | Only Active + eligible + consent current (app phones) may punch; coded refusals; new `mock_location`; hash-keyed limit replaces the per-IP 60/hour. **Answer keeps every key it has** (`status`, `log_type`, `time`, `name`, `employee_name`) and adds `todays_checkins` |
| `field_status` (app start, E4) | `www/field-checkin.html:839`, `:1138` (sample); 014 tests | Adds keys for the app. **Removes `latitude` and `longitude` from `work_location`** (PRIV-6). The web page reads only `work_location.name` and `.radius` (lines 873–874, 919–920), so it is safe. Per-IP 120/hour replaced by hash-keyed limit |
| `_device_from_token` | Only inside `field_checkin.py` (`field_checkin`, `field_status`) | Refuses every status except Active, each with its code; also looks up `retired_token_hash`; keeps 014's rule (unknown secret = same answer as Pending) |
| `_refuse_as_pending` | Only inside `field_checkin.py` | Adds code `DEVICE_PENDING`; sentence unchanged |
| `_attach_photo` | Only `field_checkin` | **No change.** Mentioned because AC-87 pins it |
| `_require_position`, `_refuse_duplicate`, `_geofence_message` | Only `field_checkin` | Same sentences; each refusal gains a code and values (`LOCATION_MISSING`, `GPS_NOT_EXACT`, `ALREADY_RECORDED`, `OUTSIDE_WORKPLACE`) |
| `_shift_location_for` | `field_checkin`, `field_status`, `_geofence_message` | No change |
| `block_devices_for_leaver` | `hooks.py:97` (Employee `on_update`) | Goes through the one revoke function: reason "Left the company", hash moved, waiting codes cancelled. Today it uses `frappe.db.set_value` and skips the controller |
| `purge_old_checkin_photos` | `hooks.py:187` (daily) | **No change.** New daily job is a separate function, added at the end of `daily` |
| `notice_facts` | `www/field_checkin.py:26–27` | Returns the current version's rows from the notice store too, so the web page stops hardcoding them (AC-95) |
| `photo_retention_days` | `field-checkin.html:454` (via `notice_facts`) | No change |
| `CONSENT_VERSION` | Only `field_checkin.py` (`register_device`, `notice_facts`) | Becomes the new version (D19). Old text kept in the notice store |
| `after_migrate` (field_checkin) | `hooks.py:224` and `:239` | Adds `alvoraa_mock_location`, the HR Settings fields, the Employee HTML field. Safe to run twice |
| `checkin_query_conditions`, `checkin_has_permission`, `log_photo_view` | `hooks.py:168`, `has_permission`, `:86` | **No change** (AC-89, AC-90 pin them) |
| `app_icon`, `manifest`, `service_worker` | `field-checkin.html:12, 13, 1214` | No change |
| `AlvoraaFieldDevice.validate` / `on_update` | Frappe on every save of a phone record (desk, list edit, import, REST) | New rules (§6.2). `on_update` keeps setting `activated_by` |
| `Alvoraa Field Device` doctype JSON | `subscription.py:395` (`TENANT_DOCTYPES`), the JSON | Statuses, fields, permissions |
| `www/field_checkin.py` `get_context` | Frappe page render for `/checkin` | Receives the notice rows from `notice_facts` |
| `hr_api.ALLOWED_ORG_SETTINGS` | `hr_api.py:2282–2293`, `test_org_settings_allowlist_012.py:97` | **Not changed** (Q-4: photo retention shown as a number, no link) |
| `subscription.TENANT_DOCTYPES` | `test_invoicing.test_every_billing_doctype_is_named_as_control_plane_only` | 3 new names appended, or that test fails |
| `test_portal_security_010.TestSec16IgnorePermissionsCeiling.CEILINGS` | Itself | New files added at their counted number; `field_checkin.py` added with its count |

**The web page's JavaScript calls** (all in `www/field-checkin.html`): `register_device`
(line 749), `field_status` (839), `field_checkin` (893), `service_worker` (1214), the
manifest and icon links (12–13). Its error handling (`handle()`, lines 1103–1119) matches
on sentences: "not set up|register it again", "waiting for HR|already registered",
"blocked", "no longer active", "already recorded", "could not get your location",
"accurate to about", "m from|too far", "not available|subscription|feature". **Every one of
those sentences stays word for word.** A small existing gap I noticed and will not change:
the plan-gate sentence "… is not included in your plan." matches none of these patterns,
so the web page shows its "unknown" screen with that sentence.

---

## 4 · The two new consent decisions, turned into a design

### 4.1 What the decisions need

- An explicit **I agree**. Without it, no check-in is possible.
- A record of each agreement: time, notice version, phone. Append-only.
- A changed notice blocks the app until the new version is agreed.
- Withdrawal through **Remove this phone** (and HR blocking ends use).
- **Not now** at the first notice still links the phone (so the QR code is never kept on
  the phone), but the phone cannot check in. Every app open shows the notice again.
- HR sees **"Joined · consent not given"**. No reason, no pressure, no reminders.

### 4.2 My proposal: consent is read from the consent history, not stored as a status

**Recommended (option B).** The phone's `status` stays about the link only: Pending,
Active, Blocked, Replaced, Removed. Whether the person agreed is answered from the
append-only consent rows: **an app phone may check in only if it has an "Agreed" row for
the current notice version.** This check runs at request time on every device call, like
the app switch and the designation check (D5).

- "Not now" at join: the code is used, the phone is linked as **Active**, **no consent row
  is written**. Every E4/E5 answer is `CONSENT_REQUIRED`. HR sees "Joined · consent not
  given" (worked out when shown, like "Stopped").
- "I agree" later: E9 writes one consent row. The next call works. **No write to the phone
  record**, so no lock, no Version row, no chance of a race with HR blocking it.
- Changed notice declined: nothing is written. The old row is for an old version, so the
  phone is refused with `CONSENT_REQUIRED` until E9 is called with the new version.
- **Fail closed by construction:** no row → no punch. There is nothing to "forget to update".

**Option A (a stored status "Consent not given").** Also works, and lets HR filter the phone
list on it. But a changed notice still needs the version check on every call, so there
would be **two** mechanisms for one rule, and the status and the rows could disagree. I do
not recommend it. **The cost of B:** the desk phone list (US-18) cannot filter on consent;
the Employee section, the access report and the daily counts show it. **Your decision
(C-1).**

### 4.3 Data model change

`Alvoraa Notice Acknowledgement` (spec §4.3) becomes **`Alvoraa App Consent`**, same rules
(insert only, no role may create, write or delete, HR reads in own scope):

| Field | Type | Notes |
|---|---|---|
| `employee` | Link Employee | indexed |
| `device` | Link Alvoraa Field Device | indexed |
| `action` | Select `Agreed`, `Withdrawn` | **Withdrawn** is written in the same save as "Remove this phone" (E6). There is no "Declined" row: saying "not now" leaves no record about the person (nothing HR could hold against them) |
| `notice_version` | Data | |
| `recorded_at` | Datetime | server time |
| `language` | Select `en`, `hi`, `Not recorded` | |
| `channel` | Select `App`, `Web check-in page`, `Backfill` | |
| `app_version` | Data | |

Index on (`device`, `notice_version`) for the gate query. HR blocking does **not** write a
Withdrawn row: it is HR's act, not the person's, and the phone record already says who
blocked it and why.

### 4.4 Endpoint and error-code changes

| Change | Detail |
|---|---|
| **E3 "Agree and finish" takes `consent` (0 or 1), required.** | Missing or anything else → 400 `INVALID_REQUEST`, nothing written. `consent=1` → as spec, plus one Agreed row. `consent=0` → the code is used, the phone is linked Active, **no consent row**, the secret is returned once, answer has `consent_given: false` |
| **E9 "I agree" (spec E9)** | Takes `notice_version` and `consent=1`. Allowed for an Active app phone whose latest agreement is missing or old. Stale version → 409 `CONSENT_REQUIRED` with the new rows |
| **`NOTICE_CHANGED` is replaced by `CONSENT_REQUIRED`** (409) | Values: `version`, `rows`, `retention_days`, `what_changed` (empty when never agreed), `agreed_before` (true/false, so the app picks "The notice has changed" or the first-time wording). One code, one screen family. Nothing has shipped, so renaming is free now and never later |
| **E6 "Remove this phone" works without consent, with the app switched off, and when the designation left the list.** | Withdrawal must be as easy as giving. E6 checks only: version header, the secret, and that the phone is Active. It writes the Withdrawn row only if an Agreed row exists |
| E4 and E5 order of checks | version → secret and status → employee active → plan → app on → field role → **consent** (app phones only) → the rest. The first failure answers |
| Web-page phones | Not asked again (AC-96 stays), unless you decide otherwise (C-4) |

### 4.5 Retention

- Consent rows are the proof that a punch had consent. **Kept while the phone has any
  punch**, and for legal hold, like phones (Q-1 pattern).
- A phone that **never agreed has no punches, photos or places.** I propose: once it is
  Blocked, Replaced or Removed for 12 months, the daily job deletes it together with the
  code that set it up. **Your decision (C-5).**
- A phone linked with "Not now" that is simply never opened again stays Active and holds
  nothing. I propose to leave it (no reminder, no automatic removal); HR can block it.

### 4.6 UX changes for the designer

1. Notice tick box and button: replace "I have read this and I understand." with explicit
   agreement wording, for example tick **"I agree to this."** and buttons **I agree** /
   **Not now**. The designer writes the final words; the lawyer checks them later.
2. New **decline screen** after "Not now" at join: your text "You chose not to agree. You
   can mark attendance the usual way. You can set up the app later with a new code from HR."
   **Must change**: with the "changing their mind" decision the person does **not** need a
   new code. Proposed: "…You can agree later: open this app and the notice shows again."
3. **Notice-on-open screen** for a linked phone with no current agreement: the notice rows,
   **I agree**, **Not now**. "Not now" closes to a quiet screen with **Remove this phone**
   and no Check In. For a changed notice, the "The notice has changed / What is new" lines
   stay on top.
4. Desk: Employee section and phone table show **"Joined · consent not given"** (dot and
   words). No reason, no "remind" button.
5. Notification N1 ("{name} joined the Alvoraa app") must not push HR to chase. Proposed
   neutral line for a "Not now" join: "…set up {phone}. They have not agreed to the notice
   yet, so the phone cannot mark attendance." No other alert.
6. `records` screen: "You agreed on {date}" stays; for a phone with no agreement, "You have
   not agreed. This phone does not mark attendance."
7. Settings: **Remove this phone** stays reachable on every consent screen.

---

## 5 · Non-functional verdicts (the seven dimensions)

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **Degrades slightly, inside budget** | Every device call gains about 4 small indexed queries (HR Settings from Frappe's document cache, designation rows, consent row, retired-hash lookup only on a miss). E4 ≈ 8–9 queries, E5 ≈ 12–15 including Frappe HR's own geofence queries. Budget p95 ≤ 500 ms; query counts pinned by tests (AC-142). Body caps make big uploads cheaper to refuse |
| **Security** | **Improves** | Only Active phones pass; blocks are final on every path; HR loses create/delete and cannot re-point a phone; hashes only; no-store; hash-keyed limits; body caps; host allow-list and permission gates in the app build. **New attack surface, named:** five new guest endpoints (E1, E2, E3, E6, E9) and the `/enrol` page. Each is POST-only, wrapped by 014's `_private_request`, limited, and answers codes with no personal data |
| **Reliability** | **Improves on the server; adds a new kind of risk** | Coded answers, locked joins, rollback by one tick box with no deploy. New risk: old app versions in the field that the server must keep answering (contract file per version in CI, 90-day rule) |
| **Scalability** | **Improves** | Today Frappe's per-IP limits (60 punches/hour per address) would refuse a depot of 400 drivers on one Wi-Fi. Replaced by per-phone limits keyed on the hash, plus a 600/minute nginx zone. Tables stay small (§12 of spec). **Limit:** one designation list per tenant, not per company (Q-9) |
| **Maintainability** | **Degrades** | A second client codebase (Capacitor app) with its own build and CI; the app's page is a separate copy of the web page's camera, photo and GPS code (§8.3); 3 new doctypes; 5 new guest endpoints and 4 desk endpoints. Kept in check by one codes file, one revoke function, contract tests and pin tests |
| **Data integrity** | **Improves** | Append-only consent history replaces two overwritten fields; `employee` frozen; final statuses; one locked save per join (Employee → invites → phones, always that order); eligibility read at the moment of the call, never copied; no own cache (uses Frappe's document cache, which Frappe clears on save) |
| **Compliance / privacy** | **Improves** | Real consent gate with history and easy withdrawal; no workplace coordinates to the phone; block reason never sent to the phone; code holder sees the least; retention with legal hold; counts without people. **New personal data, named:** phone model (stated in the new notice), consent rows, block reasons, code history, fake-location flag. Gap: the "freely given" alternative (bad news 2) |

---

## 6 · How each requirement will be met

### 6.1 Security (SEC) — mechanism and where

| ID | How it will be met | Spec ACs |
|---|---|---|
| SEC-1 | `secrets.token_urlsafe(32)`; only SHA-256 stored in `Alvoraa App Invite.token_hash`; field name contains `token` so Frappe hides it in logs; canary test searches Version, Comment, Notification Log, Error Log, log file | AC-38, AC-39 |
| SEC-2 | E7 POST only, returns `link` once; QR drawn in the browser from that answer; invite doctype has no print/email permission, no Print Format; `/enrol` page never reads the fragment, clears it with `history.replaceState`, `noindex` meta + header, no outside URL | AC-45, AC-47, AC-123–125 |
| SEC-3 | E1 builds its answer from a fixed key list; dead codes answer code + one time; unknown code → `QR_NOT_RECOGNISED` | AC-53–56 |
| SEC-4 | Lifetime must be one of the six options and ≤ the HR Settings value; refused, never clamped silently; expiry by server time | AC-40, AC-58 |
| SEC-5 | E3: lock Employee row, then invite, then the employee's phone rows (`for_update`), re-check everything, write, one commit; 014 wrapper rolls back on any error | AC-64–68, AC-70 |
| SEC-6 | E7 in the same lock order cancels the waiting code ("Newer code made") | AC-41, AC-70 |
| SEC-7 | Cancel paths: E10 (HR), E2 (phone), leaver hook, E7 (newer code); app off / designation / plan refused at E1 and E3 | AC-51, 60, 61, 68, 135 |
| SEC-8 | Controller `validate` refuses any move out of Blocked/Replaced/Removed on every save path; the one revoke function is the only way in | AC-7, AC-12 |
| SEC-9 | Permission JSON: no create/delete for any role; controller refuses insert unless server code sets an internal flag (REST cannot set flags); frozen fields refused after insert; patch removes Custom DocPerm overrides | AC-8–13, AC-156 |
| SEC-10 | `_device_from_token` answers each non-Active status with its own code; looks up `retired_token_hash` second; a test reads the Select options | AC-1–5 |
| SEC-11 | Every new guest endpoint wrapped by 014's `_private_request`; secrets named `token`/`secret`; no log line with a person in it | AC-146, AC-147 |
| SEC-12 | Hash-keyed counters per code and per phone; nginx zone; per-site refused-code count with N5 | AC-59, 63, 88, 101, 120, 140, 141 |
| SEC-13 | Notification Log rows N1–N5, queued after commit on `short`; recipients filtered by Frappe permission on the employee | AC-116–122 |
| SEC-14 | App: URL-parser host check (unit test with 15+ hostile links, no fetch); E3 accepts the old secret and removes that phone, alert if another person | AC-74, AC-172, AC-176 |
| SEC-15 | One database per site; test with two sites where the bench allows, otherwise a unit test that a hash from another site is not found | AC-57 |
| SEC-16 | App config and merged manifest checked in CI after build: not debuggable, no cleartext, no `server.url`, no `allowNavigation`, backup off; content policy in the bundled page | AC-173–175 |
| SEC-17 | App draws server text only with `textContent`; CI lint forbids other `innerHTML` | AC-222, AC-223 |
| SEC-18 | **Native HTTP (no CORS at all)**; CI check that `allow_cors` is never set; device endpoints ignore the session cookie | AC-138, AC-139 |
| SEC-19 | `MIN_APP_VERSION` and a deny-list in the one codes module; three-number compare | AC-29 |
| SEC-20 | CI permission allow-list on the merged manifest; dependency deny-list (analytics, crash, ads, Firebase) | AC-177, AC-178 |
| SEC-21 | Small local Android plugin in the app reads the platform's mock-location flag (see §8.5); server stores `alvoraa_mock_location` | AC-85, AC-204 |
| SEC-22 | E6 marks Removed through the revoke function, writes Withdrawn; app deletes the secret only after 200 | AC-99, AC-216 |
| SEC-23 | US-31 first: `.gitignore` patterns, `git ls-files` check, pinned secret scanner in `ci.yml` | AC-163, AC-164 |
| SEC-24 | `Cache-Control: no-store` set by the wrapper for all device endpoints | AC-28 |
| SEC-25 | New `ignore_permissions` uses listed with a reason; CEILINGS rows added | AC-148 |

### 6.2 Privacy (PRIV)

| ID | How it will be met | ACs |
|---|---|---|
| PRIV-1 | E3 reads only `device_label` (≤ 80), `platform` (fixed list), header version; extra fields ignored; app never calls anything that reads IDs | AC-69, AC-220 |
| PRIV-2 | Notice store in code, versions only added; rows sent by the server; **with the consent gate, a new version blocks app phones until agreed** | AC-92, 93, 96, 213 (to be reworded) |
| PRIV-3 | `Alvoraa App Consent` rows; old `consent_*` fields never written again; backfill patch | AC-94, AC-155 |
| PRIV-4 | **Changed by your decision:** wording becomes explicit agreement. AC-97 must be rewritten (§7) | AC-97 (rewrite) |
| PRIV-5 | E1 fixed key list | AC-53, AC-186 |
| PRIV-6 | `latitude`/`longitude` removed from `field_status`; app answer has none | AC-76 |
| PRIV-7 | Photo taken in the web view with the camera stream, held in memory, never a file; QR picture decoded in the page | AC-184, AC-219 |
| PRIV-8 | Only "while using" location; CI blocks background location | AC-177, AC-180 |
| PRIV-9 | `last_seen` relabelled "Last punch", written only by a saved punch; no online/map anywhere | AC-77, 107, 114 |
| PRIV-10 | Daily job marks "Ran out"; deletes per Q-1; keeps anything linked to punches or legal hold | AC-126–130 |
| PRIV-11 | Counter payload keys fixed; scanner test | AC-131 |
| PRIV-12 | Script Report for one employee, HR roles, own scope; app `records` screen | AC-153, AC-215 |
| PRIV-13 | `block_reason` never in any device answer | AC-2, AC-111 |
| PRIV-14 | Same photo field, so `log_photo_view` covers app punches (no change) | AC-89 |
| PRIV-15 | Release checklist line before the pilot | AC-235 |
| **Consent gate** (new) | §4: E3 `consent`, E9, `CONSENT_REQUIRED`, gate from consent rows, Withdrawn on E6 | new ACs (§7) |

### 6.3 DevOps (OPS) adopted

| ID | How | ACs |
|---|---|---|
| OPS-1, OPS-2, OPS-47 | Native HTTP from the app (Capacitor's built-in HTTP, called explicitly, cookies not used). No nginx CORS block, no `allow_cors`. CI check for `allow_cors` | AC-138 |
| OPS-3 | Step 1 loads no remote page; `allowNavigation` empty | AC-175 |
| OPS-5, OPS-38 | Three build types with their own app IDs; pilot in a protected `mobile-pilot` environment | AC-165–167 |
| OPS-6, OPS-37 | US-31 first (§11) | AC-163, AC-164 |
| OPS-7, OPS-55 | Host check in the app, network rules, CI inspection of built files | AC-172, AC-173 |
| OPS-8, OPS-44, OPS-48, OPS-49 | One codes module; answers only ever add; contract file per released version replayed in CI; min version constant | AC-26–37 |
| OPS-9, OPS-54 | Wildcard certificate is live (d6613ea); pilot on a dev demo tenant, invented people, 7-day photo retention — on your word | AC-229 |
| OPS-10, OPS-29, OPS-46 | Hash-keyed counters; nginx zone 600/min burst 100; one-IP load test | AC-140–144 |
| OPS-13 | Code only in `#fragment` and POST bodies | AC-38, AC-123 |
| OPS-15 | Target Android level checked in CI | AC-171 |
| OPS-21, OPS-63 | Photo resized in the app (640 px, JPEG 0.6/0.45, ≤ 150 KB); 400 KB backstop unchanged | AC-201, AC-87 |
| OPS-22 | CI: bundle has no outside URL; package ≤ 10 MB | AC-179 |
| OPS-23 | QR decoding is in the page, so there is no model to download (§8.4). Pilot measures scan speed | AC-232 |
| OPS-24, OPS-25 | One E4 on open, at most one a minute; secret in Keystore-backed storage; no-store | AC-202, AC-217 |
| OPS-26, OPS-27 | Codes and min version (as OPS-48/49) | AC-26, AC-29 |
| OPS-28, OPS-50 | Only Active passes; hash moved to `retired_token_hash` in the same save (Q-2 accepted); **first server change, never reverted** | AC-1–5 |
| OPS-30, OPS-51 | Lock order Employee → invites → phones in E3 and E7 | AC-65, AC-70 |
| OPS-31 | App phones only; with consent gate the app phone is blocked until agreed | AC-96, AC-213 |
| OPS-32 | Print from the browser; no server PDF | AC-45, AC-49 |
| OPS-33 | **Deferred** (your decision) | — |
| OPS-34, OPS-59, OPS-61 | Daily counts through `health.py`; four technical alerts to Surbhi; data alerts to the customer's HR | AC-131–134 |
| OPS-36, OPS-57 | Pilot phones table in the repo, no tester names | AC-231 |
| OPS-39, OPS-40, OPS-41 | Bitwarden + offline copy; version formula; lock file, `npm ci`, pinned tools | AC-168–170 |
| OPS-42 | iPhone from a borrowed Mac; CI check for `DEVELOPMENT_TEAM` | AC-227, AC-228 |
| OPS-43 | 014 on `origin/dev` before any 013 server commit is pushed | AC-145 |
| OPS-45 | nginx body caps 1 MB (punch) / 16 KB (other device paths), security headers repeated, `nginx -t` in a throwaway container | AC-137 |
| OPS-52 | Hash emptied at the moment of change; daily job; delete per Q-1 | AC-126–130 |
| OPS-53, OPS-64, OPS-65 | Empty designation list on migrate; switch checked at request time; rollback = untick | AC-14, 78, 160–162 |
| OPS-56 | Firebase App Distribution on Surbhi's account; no Firebase code in the app | AC-230 |
| OPS-58 | Update link built into each build type | AC-209 |
| OPS-60, OPS-62 | Log scanner; query-count ceilings | AC-147, AC-142 |

---

## 7 · Spec changes needed (for the business analyst, not by me)

**Because of the consent decisions:**

| AC / item | Today says | Must say |
|---|---|---|
| PRIV-4, **AC-97** | No "consent", no "I agree"; tick "I have read this and I understand." | Explicit agreement wording; the string check now looks for the agreed words instead |
| AC-64 | One acknowledgement row | With `consent=1`: one Agreed consent row |
| AC-67, AC-80, AC-94, AC-213 | `NOTICE_CHANGED` | `CONSENT_REQUIRED` with `agreed_before` |
| AC-187, AC-188 | "Agree and finish" after the tick | **I agree** and **Not now** |
| AC-190 | Back before Agree → code still works | Still true for Back or closing the app. **"Not now" uses the code** |
| AC-99, AC-216 | Remove | Also writes a Withdrawn row when an Agreed row exists; works with the app off, designation removed, or no agreement |
| AC-104, AC-105, AC-108 | States list | Add "Joined · consent not given" |
| AC-155 | Backfill acknowledgement rows | Backfill **Agreed** rows with channel Backfill for web phones (they ticked a box that was required). Your call whether that counts (C-4) |
| §4.3 doctype | `Alvoraa Notice Acknowledgement` | `Alvoraa App Consent` with `action` |
| §7.1 codes | `NOTICE_CHANGED` | `CONSENT_REQUIRED` |
| New ACs | — | (a) E3 with `consent=0`: code Used, phone Active, no consent row, secret returned, E4/E5 → 409 `CONSENT_REQUIRED`, no `Employee Checkin` row. (b) E9 afterwards: one Agreed row, next E5 saves. (c) A declined changed notice writes nothing and punches stay refused. (d) E3 without `consent` → 400. (e) Decline screen and notice-on-open screen words. (f) No alert or reminder to the worker; HR sees the state with no reason. (g) Retention of never-agreed phones (C-5) |
| **US-2 (Q-12)** | — | **Added in my plan, +1 point:** "Blocking (desk and E11), replacing (E3), removing (E6 and the two-people case) and the leaver hook all call one server function; a test asserts each path calls it." |

**Also found while reading:**

- Spec §4.5 and §2 G5 say the photo retention key is read only in `field_checkin.py`. True,
  though a code comment says Org Settings could edit it; `ALLOWED_ORG_SETTINGS` does not
  allow it. Q-4 stands.
- Spec §12 says the `Employee Checkin (employee, time)` index is unverified. Read:
  `employee` has `search_index` in the hrms JSON; `time` gets an index from slice 012's
  `data_review.after_migrate` (in the pending release). Enough for "today's punches for one
  employee".
- AC-35 relies on "existing tests" for the web page. There are none (bad news 3).

---

## 8 · Proposed strategy

### 8.1 Server stories first, in this order

**Step 0 — before any server code (tests only).** Pin today's web behaviour: register (real
and fake ID same answer), HR activates, punch, each refusal sentence, `field_status` keys the
page reads. File `test_field_checkin_web_pin_013.py`. These fail if any later commit changes
what the web page sees.

**Step 1 — US-4, US-1, US-2 (+Q-12), US-29 part. One group, never reverted.**

- **Codes module** `alvoraa_portal/field_app_codes.py`: every code with its HTTP status,
  `MIN_APP_VERSION`, version deny-list, and one helper that refuses with `frappe.throw` (so
  the English sentence stays in `_server_messages` for the web page) **and** puts
  `code` and `values` in the JSON body. 014's wrapper already answers refusals with Frappe's
  status; it will read the status from the code. HTTP statuses as proposed in spec §7.1
  (Q-6) — I agree with them. The 014 test expecting 417 for a bad `log_type` is updated to
  400 in the same commit, with the reason in the message.
- The wrapper also sets `Cache-Control: no-store`, refuses a malformed or too-old
  `X-Alvoraa-App-Version` (no header = web page, allowed), and maps Frappe's rate-limit
  refusal to `TOO_MANY_TRIES`.
- **Device record** (`alvoraa_field_device.json`, `.py`): statuses Pending, Active, Blocked,
  Replaced, Removed; new fields per spec §4.1 plus `retired_token_hash` (Q-2 accepted);
  `employee` `set_only_once`; permissions without create/delete.
- **One revoke function** `revoke_device(device, to_status, source, reason=None,
  replaced_by=None)` in `alvoraa_portal/field_app_devices.py`. It sets the status, moves the
  hash to `retired_token_hash`, fills `status_changed_*`, `block_reason`, `replaced_by`, and
  (for Removed by the employee) writes the Withdrawn consent row. **The controller calls the
  same function** when a person blocks a phone from the form, list edit or import, so there
  is one place for the rule.
- **Controller rules** in `validate`: insert only with the server flag; frozen fields;
  allowed moves only (Pending → Active for web phones, Pending/Active → Blocked with a
  reason); final states cannot move.
- `_device_from_token`: live hash, then retired hash; each status its code; 014's rule kept.
- **Patch M2 + M4** (appended to `patches.txt` after 014's line): `join_method` = Web
  check-in page for existing rows; Blocked rows' hash moved; Custom DocPerm create/delete
  removed for the phone doctype. Safe to run twice. Rollback: none needed; a code revert must
  never go back past this group (OPS-65).
- `block_devices_for_leaver` goes through `revoke_device`.

**Step 2 — US-3, US-14 (+consent), US-5, US-7, US-23.**

- **HR Settings section** (Q-5 accepted): custom fields prefixed `alvoraa_field_app_*`,
  created by `field_checkin.after_migrate` (already on `after_migrate` and `after_install`).
  Child doctype `Alvoraa Field Worker Designation` (one Link). A validate hook on HR Settings
  added at the **end** of `doc_events["HR Settings"]` in `alvoraa_portal/hooks.py` (this app
  has no HR Settings entry today; `alvoraa_goals` has its own, and both run). Reason field
  required when switching off or removing a designation; emptied after save (the
  `Alvoraa Leader View Settings` pattern). Default list empty, switch on, 1 day.
- **Eligibility** read at call time from `frappe.get_cached_doc("HR Settings")`. **No cache
  of our own**, so there is no invalidation to get wrong: Frappe clears a document's cache
  when it is saved. **To verify in the installed Frappe before use** (§8.7).
- **Consent**: `Alvoraa App Consent` doctype; notice store (a dict in
  `alvoraa_portal/field_app_notice.py`, versions only added, a test pins old text);
  new `CONSENT_VERSION`; `register_device` writes an Agreed row with channel Web check-in
  page; backfill patch M3 (Agreed, Backfill) for existing phones.
- **Invites**: `Alvoraa App Invite` doctype (spec §4.2), read-only for HR. E7 (make) and E10
  (cancel) as desk `@frappe.whitelist()` endpoints with **Frappe's normal permission check
  on the Employee** (`frappe.has_permission("Employee", "read", doc=…)`), a per-user limit.
- Leaver hook also cancels waiting codes.

**Step 3 — US-8, US-9, US-10, US-11, US-12, US-13, US-15, E9, US-25.**

- Guest endpoints E1, E2, E3, E6, E9 added to `field_checkin.py` (so one nginx path covers
  all device endpoints), each under `_private_request` naming its secret fields; E4 and E5 are
  the existing `field_status` and `field_checkin`, extended **by adding only**.
- **Locked transactions (D3, D17):** E3 and E7 lock the Employee row, then invite rows, then
  phone rows, always in that order, one commit. Concurrency tests with two database
  connections (AC-65, AC-70). **Honest risk:** true parallel tests are awkward in Frappe's
  test runner; I will use two threads with their own `frappe.connect`, and if that proves
  flaky on the bench I will say so rather than hide it.
- **Rate limits keyed on the hash:** a small counter in Redis keyed on
  `sha256(token)` (never the raw value — Frappe's `rate_limit(key=…)` writes the key's value
  in clear). Per code: E1 20/h, E2 5/h, E3 5/h. Per phone: E4 60/h, E5 30/h, E6 5/h, E9 5/h.
  The existing per-IP `@rate_limit` on `field_status` and `field_checkin` is **replaced**
  (it would refuse a busy depot); `register_device` keeps its per-IP 10/h. **Trade-off:** a
  flood of random well-formed secrets is no longer limited per IP inside Frappe; each costs
  one indexed lookup, and nginx's 600/min zone caps it. I think that is right; DevOps to
  confirm.
- `mock_location` stored on the punch. `app_version` updated on a saved punch only.
- Minimum app version on every device endpoint.

**Step 4 — desk and the rest: US-6, US-16, US-17, US-18, US-19, US-20, US-21, US-22, US-26,
US-27, US-28, US-30, then US-24 (nginx) last.**

- Employee desk: one HTML custom field `alvoraa_field_app_html` on the Attendance & Leaves
  tab (created in `after_migrate`), and a client script registered with a **new**
  `doctype_js = {"Employee": …}` key at the end of `alvoraa_portal/hooks.py`. Data from E12.
  QR drawn in the browser with a small bundled QR library in `alvoraa_portal/public/js/`
  (no outside host). Block dialog calls E11 → `revoke_device`.
- Phone list: list view settings (columns, 7-day default filter, page size 20).
- Alerts N1–N5: `Notification Log` inserts, `frappe.enqueue(queue="short")` after commit.
- `/enrol`: `www/enrol.html` + `enrol.py`, `no_cache`, no scripts except the fragment clear.
- Daily job `alvoraa_portal.field_app_jobs.daily_cleanup` appended to `daily`: Ran out,
  deletes per Q-1 and C-5, live-hash self-check, batches of 500, counts only in the log.
- Daily counts: counters in Redis per day per site, pulled by `health.collect_scheduled`;
  13-month keep.
- Access report: Script Report "Field app records for one employee".
- Web page (`field-checkin.html`): notice rows from `notice_facts`, FC-1 ("Checked out at"),
  FC-2 line. **Nothing else in the page changes.** Wording change there only if you decide C-4.
- **US-24 nginx last, as its own commit, with its own push approval:** a regex location for
  `^/api/method/alvoraa_portal\.field_checkin\.` with body caps and the new zone, security
  headers repeated, in both server blocks, on top of 014's and `main`'s nginx. `nginx -t` and
  014's `check_nginx_*` scripts in a throwaway container.

### 8.2 Doctypes and fields — summary

| Object | Kind | New / changed |
|---|---|---|
| `Alvoraa Field Device` | existing doctype | statuses, `join_method`, `invite`, `app_version`, `block_reason`, `replaced_by`, `status_changed_on/by`, `status_change_source`, `retired_token_hash`; `last_seen` relabelled; permissions; controller |
| `Alvoraa App Invite` | new doctype | spec §4.2 |
| `Alvoraa App Consent` | new doctype | §4.3 here (replaces spec's acknowledgement doctype) |
| `Alvoraa Field Worker Designation` | new child doctype | one Link |
| HR Settings | custom fields | section "Field attendance app": designations, switch, lifetime, reason, info HTML |
| Employee Checkin | custom field | `alvoraa_mock_location` |
| Employee | custom field | `alvoraa_field_app_html` (HTML, no data) |
| `subscription.TENANT_DOCTYPES` | list | append the three new names |

### 8.3 The app: where it lives and how it is built

- **Folder:** `mobile/field-app/` at the top of the repo. `package.json` and lock file there;
  `node_modules/`, build outputs and every key pattern git-ignored. The generated `android/`
  project is committed (Capacitor's normal practice) with the Gradle wrapper and its
  checksum. `ios/` is added only for US-47.
- **Capacitor 8** (read today on capacitorjs.com: needs Node 22+, Android Studio 2025.2.1+,
  which brings its own Java; Android 7.0 / API 24 minimum).
- **The bundled page is the app's own page, not the web page file.** `field-checkin.html` is a
  Jinja template, has an employee-ID join, text matching, `localStorage`, and about 10 screens;
  the app needs 50+ screens driven by codes. Sharing one file would mean changing the web page
  a lot, which AC-35 forbids. So `mobile/field-app/web/` holds the app page, **starting from a
  copy** of the web page's camera, photo-resize, GPS and `esc()` code. **Cost:** two copies of
  that code (maintainability degrades). **Later:** move the shared parts into one JS file used
  by both, once the web page may change.
- **All calls go to `https://<tenant host>/api/method/alvoraa_portal.field_checkin.*`**, the
  host fixed at join from the checked QR.
- **Secure storage:** a maintained open-source Capacitor 8 plugin backed by Android Keystore
  and iOS Keychain. First candidate `@aparajita/capacitor-secure-storage`. **Not verified**
  for Capacitor 8 or 32-bit phones (security's W4); checked in the first app spike before it
  is pinned.
- **Photo:** taken inside the page with the camera stream, as today (no camera plugin, so no
  image file is ever written — PRIV-7).
- **Build types:** debug (`.debug`, this PC, HTTP only to the bench's LAN address), pilot
  (`.pilot`, GitHub Actions from `dev`, `mobile-pilot` environment, pilot key, Firebase),
  release (store ID, from `main`, not built in step 1).
- **Keystore guard first (US-31)**, before anyone creates a key.
- **Permission CI check:** after `npx cap sync` and a Gradle build, read the merged manifest;
  fail on any permission outside the five. Same job: dependency deny-list, outside-URL scan,
  size ≤ 10 MB, `DEVELOPMENT_TEAM` check.
- **App tests:** Node's built-in test runner (`node --test`), so no new test framework.

### 8.4 QR scanner choice

**Recommend: decode the QR inside the page with a small pinned pure-JavaScript library**
(for example `jsQR`), reading frames from the same camera stream the punch already uses, and
from the picture returned by the system photo picker (`<input type="file"
accept="image/*">`, which on Android needs no storage permission).

- **Why:** no Google code inside the app (a native ML Kit scanner brings Google libraries
  that may send usage data, which clashes with SEC-20 and "no Google code"); no model to
  download (answers OPS-23); the same code works on the iPhone test; one less native plugin.
- **Cost:** slower on the cheapest phones than a native scanner. The pilot measures
  scan → confirm ≤ 2.5 s (AC-232). **Fallback** if it fails on P1–P3: a native scanner
  plugin, after security checks its network behaviour.

### 8.5 Fake-location flag

The web view's location API does not say whether a position is faked. So the app needs a
**small local Android plugin** in `mobile/field-app/android/` (our own ~50 lines of Java,
using Android's own `LocationManager`, not Google Play services) that returns latitude,
longitude, accuracy and the mock flag. **Not verified** how Xiaomi, Realme and Samsung
report it (W6); the pilot checks.

### 8.6 CORS

**No CORS at all.** The app calls the server through Capacitor's native HTTP, explicitly, so
the web view's cross-origin rule does not apply, and no nginx CORS block or `allow_cors` is
needed. The app does not send or keep cookies for these calls, and the server ignores any
session on device endpoints (AC-139). **To verify in the spike:** that native HTTP does not
follow a redirect to another host (AC-176); if it does, the app refuses any 3xx itself.

### 8.7 APIs to verify against the installed Frappe (v16.33.1 per slice 014) before use

I could not read the installed Frappe: it lives only inside the bench container, and this
step must not use the bench. **Nothing below will be called until it is found in the source.**

| API | Why I need it |
|---|---|
| `frappe.get_cached_doc` and that saving HR Settings clears it | Settings effective within 60 s with no own cache |
| `frappe.db.get_value(..., for_update=True)` or `frappe.qb` `for_update` | Locked join |
| `frappe.cache` increment with expiry | Hash-keyed counters |
| `frappe.enqueue(..., enqueue_after_commit=True)` | Alerts after commit |
| `set_only_once` on a field, `Table MultiSelect` as a custom field on a Single | Data model |
| Rename of a Designation updates rows in the child table | Spec assumption |

---

## 9 · Toolchain on this PC (read-only check, 2026-09-17)

| Tool | Found | Needed for Android | Action for you |
|---|---|---|---|
| Node.js | **v24.13.1**, npm 11.8.0 | Node 22+ | Nothing |
| Java | Temurin **25.0.2** on PATH, `JAVA_HOME` not set | Android Studio's own bundled Java | Nothing to install; the build uses Android Studio's Java. Java 25 on PATH is likely too new for Android's Gradle; builds should point `JAVA_HOME` at Android Studio's copy |
| Android Studio | **Not installed** | 2025.2.1 or newer | **Install** (about 3 GB) |
| Android SDK, platform tools (`adb`) | **Not installed** (`%LOCALAPPDATA%\Android\Sdk` missing, `ANDROID_HOME` unset) | SDK platform for the target API (Play's current level, 36 today) and build tools | **Installed through Android Studio's setup wizard** (about 5–8 GB more) |
| Git | 2.52 | — | Nothing |
| `keytool` | present (with Java 25) | Only for the pilot key, made **outside any git folder** | Nothing now |
| Memory | **15.8 GB**; Docker runs the bench | Android Studio + Gradle want 4–8 GB while building | Expect slowness if the bench and a build run together. Build when the bench is idle |
| Disk | 115 GB free on C: | ~10–15 GB for Studio, SDK, Gradle cache | Enough |
| Emulator | Windows reports firmware virtualisation off (Docker works, so it may be on through Hyper-V) | Optional | **Test on a real phone by USB** instead; turn on Developer options and USB debugging on one pilot phone |
| **iPhone builds** | Not possible on Windows | **A Mac with Xcode** | Borrow a Mac (US-47), free Apple ID |

**Also your actions, not code:** confirm GitHub push protection is on (AC-164); set up
Bitwarden and the offline key copy before the pilot key is made; create the `mobile-pilot`
environment with you as approver; Firebase App Distribution on your account (decided).

---

## 10 · Parallel-work check

### 10.1 State of the repo (verified with git, 2026-09-17)

- `origin/dev` = `c27fb56`. **Nothing on `origin/dev` is missing from local `dev`**, so no
  incoming commits to read.
- Local `dev` = `9138251`, **114 commits ahead** of `origin/dev` (010 group D + 012 push 1 +
  F1 + 010 fix rounds). Another session pushes it on your word.
- `origin/main` has `d6613ea` (wildcard nginx), `42c165d` (demo stubs) and two merge commits
  that are **not on `dev`**.
- Slice 014: branch at `a8f2580`, based on `8a53522`, five commits, **not in local `dev`, not
  pushed, Frappe tests not run**.
- Main checkout has other sessions' uncommitted work: `.claude/context/ux-learnings.md`,
  `backlog/KPI_AUTOMATION_BACKLOG.md`, `docs/slices/009…/00-assessment-and-plan.md`,
  `hrms/…/alvoraa_position.py`, a deleted `OBJECTIVES_KPI_REQUIREMENTS.md`, and several
  untracked files. **None is mine. I will not touch them.** This document is also untracked
  (the whole `docs/slices/013-mobile-app/` folder is).

### 10.2 Files I will change, who else is in them, and the plan

| File | Hot? | Who else | Plan |
|---|---|---|---|
| `alvoraa_portal/field_checkin.py` | shared API file | **Slice 014** (wrapper, `register_device`, `_device_from_token`) | **Sequence:** 014 lands in `dev` first; 013 branches from there |
| `alvoraa_portal/www/field-checkin.html` | no | nobody on the board | Claim; change only notice rows, FC-1, FC-2 |
| `alvoraa_portal/www/field_checkin.py` | no | nobody | Claim |
| `alvoraa_field_device.json` / `.py` | **DocType JSON** | nobody | Claim on the board |
| `alvoraa_portal/hooks.py` | **hot** | 010 (doc_events, `daily` line), 012 (`cron`, `after_migrate`) — both in local `dev` | Append only: Employee `on_update` list unchanged (existing handler extended inside its function), new `doc_events["HR Settings"]`, one `daily` line at the end, new `doctype_js` key at the end |
| `alvoraa_portal/patches.txt` | **hot** | **014** adds one line at the end | Sequence after 014; append after its line |
| `alvoraa_portal/subscription.py` | **hot** | 012 appended to `TENANT_DOCTYPES` (in local `dev`) | Append three names at the end |
| `tests/test_portal_security_010.py` (CEILINGS) | shared test | 010, 012 F1 add rows | Append rows at the end |
| `tests/test_checkin_security_014.py` | 014's | **014** | Change one assertion (417 → 400) in its own commit, with the reason; ask the 014 owner if still in flight |
| HR Settings custom fields | custom fields by code | **010 group D** (`alvoraa_review_*`, from `alvoraa_goals`) | **Split:** our own prefix `alvoraa_field_app_*`, own section, inserted after a standard field, not after 010's. AC-158 test saves HR Settings with both |
| Employee custom field + `doctype_js` | shared doctype | nobody in this repo adds an Employee script in `alvoraa_portal` | Claim |
| `alvoraa_portal/health.py` | no | nobody | Claim |
| `.gitignore`, `.github/workflows/ci.yml` | **deploy/CI** | **014** adds one lint step | Sequence after 014; add our step at the end of the lint job |
| `.github/workflows/mobile.yml` (new), `build-image.yml` paths filter | CI | nobody | New file; `build-image.yml` only with DevOps' view and your word |
| `deploy/nginx.conf` | **deploy, serves production** | **014** and **`main`'s d6613ea** | Last commit of the slice, after both are on `dev`; own go-ahead |
| New: 3 doctypes, `field_app_*.py`, `www/enrol.*`, report, `mobile/`, new tests | — | nobody | New files |
| `www/hrms-employee.html` | hot | 009, 010, 012 | **Never touched** |

**Other developers:** the board is local to this PC. `git log origin/dev --since="7 days ago"`
shows no one else in `field_checkin.py`, `field-checkin.html`, the device doctype or
`nginx.conf` on `origin/dev`. **Surbhi, please confirm no other developer is working in
these files.**

### 10.3 Proposed sequence

1. **"010 group D + 012 push 1 + F1 + fix rounds"** pushed to `origin/dev` by the session that
   owns it, on your word. The release rule says no new slice commits go into local `dev`
   before that.
2. **Slice 014:** bring `d6613ea` into `dev`, rebase 014 onto it, run its owed Frappe tests on
   the bench, bring it into local `dev`, push on your word (OPS-43).
3. **Slice 013 worktree** `.claude/worktrees/013-mobile-app`, branch `slice/013-mobile-app`
   from `origin/dev` **after 014 is on it**.
4. **What can start before 3, with no bench and no conflict:** the app work that does not
   depend on the server — US-31's patterns and check written on a branch (landed after 014's
   `ci.yml` step), the `mobile/` skeleton, the host-check module and its `node --test` unit
   tests, the photo-resize unit test. Only if you want that head start; it lives in the same
   worktree, branched from `origin/dev`, rebased later.
5. Server steps 0 → 4 (§8.1), then nginx. App stories alongside, tested against the local
   bench with debug builds once the server steps are in local `dev`.

**When the strategy is approved I will add a row to the work board.**

### 10.4 Tests that pin behaviour I touch

| Existing test | Pins | Effect of this slice |
|---|---|---|
| `test_checkin_security_014.py` (13, on the 014 branch) | wrapper on the 3 endpoints, no personal data in logs, same answer for real/fake ID, 401 for a bad secret, 403 for the plan gate, 417 refusal shape, redaction patch | All kept; one status assertion changes (417 → 400) with its reason; the wrapped-endpoint list grows |
| `test_opt_in_features.py` | `field_checkin` is opt-in | unchanged |
| `test_invoicing.test_every_billing_doctype_is_named_…` | every `Alvoraa %` doctype classified | three names appended |
| `test_portal_security_010` CEILINGS | `ignore_permissions` counts | rows appended |
| `test_checkin_location.py` | portal `do_checkin` location | unaffected (different endpoint) |
| `alvoraa_goals` HR Settings tests (slice 010) | review settings validate | must still pass (AC-158) |
| **Slice 008 web flow** | **nothing** | new pin tests, step 0 |

**Tests I will add** (each named for what it keeps alive):
`test_field_checkin_web_pin_013` (AC-35), `test_field_app_contract_013` (US-4),
`test_field_app_devices_013` (US-1, US-2 incl. every save path and the one revoke function,
US-23, US-29), `test_field_app_settings_013` (US-3, AC-158), `test_field_app_consent_013`
(US-14, consent gate, decline, withdrawal), `test_field_app_invites_013` (US-5, 7, 8, 9, 10,
11, concurrency), `test_field_app_device_calls_013` (US-12, 13, 15, E9),
`test_field_app_permissions_013` (US-27, 28), `test_field_app_logs_013` (US-26),
`test_field_app_jobs_013` (US-21, 22), `test_field_app_load_013` (US-25 query counts and
timings). App: `node --test` suites for the host check, code table vs server codes file,
photo resize, text-only rendering, string table; CI checks for manifest, dependencies, URLs,
size, keys.

---

## 11 · Size and commit order

**Estimate, not measured.** Points from the spec, adjusted.

| Line | Points | Engineer days (estimate) | Notes |
|---|---|---|---|
| Server | 104 + ~8 consent + 1 revoke = **~113** | **24–30 days** | Includes tests, patches, desk screens, nginx |
| App | 58 + ~3 consent screens = **~61** | **18–22 days** | Includes toolchain setup (1 day), spike on storage/scanner/mock flag (2 days), CI checks |
| Pilot | — | 5 working days + report | Needs server on dev and your word at each step |

Running both lines in one session: about **10–11 weeks** to the end of the pilot. Two
sessions in parallel: about 6–7 weeks.

**Commit order (each commit small, one reason, with its test):**

1. Web behaviour pin tests (no code change)
2. Codes module + wrapper additions (no-store, version header, rate-limit code) + 014 test update
3. Device statuses, fields, permissions + controller rules + one revoke function + lookup of retired hash
4. Patch: existing phones (join method, retired hash, DocPerm)
5. Leaver hook through the revoke function (+ code cancel added in 9)
6. HR Settings section + child doctype + validate hook + eligibility
7. Consent doctype + notice store + new version + `register_device` writes consent
8. Patch: backfill consent rows
9. Invite doctype + E7 + E10 + leaver cancels codes
10. E1 + E2
11. E3 (join, decline, replace, two-people case)
12. E4 + E5 extensions + E9 + mock-location field
13. E6 remove
14. Hash-keyed limits (replacing per-IP limits on E4/E5)
15. Employee desk section + E11 + E12 + phone list settings
16. Alerts N1–N5
17. `/enrol` page
18. Daily job + daily counts + technical alerts
19. Access report
20. Web page notice rows, FC-1, FC-2
21. Load and query-count tests; implementation notes
22. **nginx body caps and zone (own push approval)**

App (from the step 4 head start in §10.3): A1 key guard in CI → A2 `mobile/` skeleton and
pinned tools → A3 host check + tests → A4 build types and debug network rules → A5 CI
permission/dependency/URL/size checks → A6 spike: secure storage, QR decode, mock flag, native
HTTP redirect → A7 join screens → A8 consent screens (notice, decline, notice on open) →
A9 attendance and punch → A10 problem and stopped screens → A11 settings and remove →
A12 pilot workflow → A13 iPhone check (borrowed Mac).

---

## 12 · Decisions needed from you

| # | Decision | My recommendation | Blocks |
|---|---|---|---|
| **C-1** | Consent state: worked out from consent rows (B) or a stored phone status (A)? | **B** (§4.2) | Data model, US-1/US-14 |
| **C-2** | "Not now" at join uses the code and links the phone (your note); confirm the decline screen should say "open the app to agree later", not "get a new code" | Yes | Decline screen, E3 |
| **C-3** | ⚠ A worker who declines: are the reception machine and HR marking attendance enough as "another way"? The web page is not photo- and location-free. **Lawyer to confirm** | Accept for the pilot (invented employees); decide before the first customer | First customer, not the build |
| **C-4** | Web check-in page: change its tick-box wording to "I agree" too, and backfill web phones as Agreed? Web phones stay not re-asked (AC-96)? | Change the wording (same notice store); backfill as Agreed; web phones not re-asked (demo phones only) | US-14, patch M3 |
| **C-5** | Delete a phone that never agreed (no punches) 12 months after it ended, with its code | Yes | US-21 |
| **C-6** | "Remove this phone" works even with no agreement, app switched off, or designation removed | Yes (withdrawal must be easy) | E6 |
| **C-7** | Replace `NOTICE_CHANGED` with `CONSENT_REQUIRED` | Yes (nothing shipped yet) | Codes |
| **C-8** | One revoke function added to US-2 (Q-12), +1 point | Yes — **already in this plan** | US-2 |
| **C-9** | HTTP statuses per code as in spec §7.1 (Q-6), and 014's 417 test becomes 400 | Yes | US-4 |
| **C-10** | No CORS: native HTTP from the app | Yes | US-24 scope |
| **C-11** | QR decoded in the page with a JS library, not a Google scanner | Yes, native scanner only as a fallback | App |
| **C-12** | The app page is its own copy, the web page stays nearly unchanged | Yes | App, AC-35 |
| **C-13** | `build-image.yml` ignores `mobile/**` pushes (DevOps to confirm) | Yes | CI |
| **C-14** | Sequence: pending release → 014 → 013; app head start (key guard, skeleton, host check) now | Yes | Start date |
| **C-15** | Ask the analyst to update the spec for the consent decisions (§7) before US-10, US-14, US-36, US-42 | Yes | Those stories |
| **C-16** | Install Android Studio (with its SDK) on this PC | Yes, when you are ready to start app work | App build |
| **C-17** | Confirm no other developer is working in the files in §10.2 | — | Start |

---

## What I did and did not check

| Checked | How |
|---|---|
| Spec incl. all three decision sections; brief gate; design check; 01c incl. decisions; 07 §1–§3 incl. answers; sequencing | Read |
| 014 approval, pre-push checks, owed items, its tests and code | Read on the 014 branch |
| Every caller in §3 | `git grep` over the repo, main checkout and 014 branch |
| No slice 008 Python tests | `git grep` over all test folders, `scripts/`, `.github/` |
| Web page uses only `work_location.name/radius`; matches sentences, not statuses | Read `field-checkin.html` |
| Device doctype fields, permissions, controller | Read JSON and `.py` |
| HR Settings: Single, `track_changes`, HR Manager write, HR User read, Employee read | Read `hr_settings.json` |
| Employee Checkin `employee` indexed; `time` index from 012 | Read JSON and `data_review.py` |
| Docker image copies only three app folders | Read `deploy/Dockerfile` |
| Toolchain | `node -v`, `npm -v`, `java -version`, folder and PATH checks, memory and disk |
| Capacitor 8 requirements | capacitorjs.com environment setup page, 2026-09-17 |

**Not checked:** the installed Frappe source (bench not used — §8.7 lists what must be
verified); any Capacitor plugin's behaviour; any phone; the live server; whether another
developer works in these files.

Sources: [Capacitor — Environment setup](https://capacitorjs.com/docs/getting-started/environment-setup)

---

## Approvals and clarifications (Surbhi, 2026-09-17, later)

- **Strategy approved** (00-impact-analysis.md, with the engineer's recommended answers to C-1..C-17 and DevOps §4 conditions: QR reader chosen by a side-by-side test of jsQR vs zxing-wasm on the pilot phones with the decoder bundled; a CI check for drift between the web page and app copies of the camera/photo/GPS code, with a dated merge plan after the pilot; `ci.yml` keeps running on `mobile/` pushes). **Build locally only; no push.**
- **Changing phone deletes nothing.** Photos and locations stay and follow the normal retention (default 90 days).
- **"Remove this phone" is not a withdrawal of consent.** It only removes the phone. Withdrawing consent is a separate, explicit choice.
- **Deleting a person's photos and exact locations on withdrawal of consent: not built now.** Wait for the DPDP lawyer to say whether it must happen immediately or whether normal retention is enough; add before the first customer if required. The attendance record (time, present) is never deleted by this.

## App ID (Surbhi, 2026-09-18)

The Android/iOS application ID is **`co.alvoraa.app`** (not `co.alvoraa.fieldattendance`), because the app will grow beyond attendance (My HR next). It cannot change after the first store release.
