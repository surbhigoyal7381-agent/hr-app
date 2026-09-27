---
slice: 013-mobile-app
artifact: 04-impact-analysis-server
author: hrms-fullstack-engineer
date: 2026-09-18
status: draft — waiting for the user's decision
scope: the SERVER stories only (US-1 to US-21). The app stories (US-31 to US-48) are not covered here.
inputs: [02-functional-spec.md, 03-implementation-notes.md, 01c-security-privacy-requirements.md, 07-devops-inputs.md, .claude/context/change-process.md, frappe-conventions.md, nfr-budget.md, parallel-work.md, .claude/work-in-progress.md, alvoraa_portal/alvoraa_portal/field_checkin.py at dev d1fd9c6]
---

# 013 — Impact analysis for the server stories

**I recommend. You decide.** Nothing was built. No bench command, no docker command, no
site touched, no commit. I read code and documents in the main checkout on branch `dev`.

**What I read the code at:** working checkout `dev` = `d1fd9c6`, `origin/dev` = `baa9f68`,
one commit apart. **Slice 014 is in both**, so `field_checkin.py` already has
`_private_request`, `_refuse_as_pending` and the "identical answer for a real and a fake
employee ID" rule. The spec's blocking condition ("014 must be on dev first") is met.

**One thing I could not verify.** `frappe` and `erpnext` are **not** in this checkout —
only `hrms`, `alvoraa_portal`, `alvoraa_goals` and `alvox_compensation`. So every claim
below about Frappe's own behaviour (how a refusal body is built, whether User Permissions
reach a linked doctype, `Table MultiSelect` rename behaviour, `rate_limit` keying) is
marked **[UNVERIFIED]** and must be checked against the installed source on the bench
before that story is coded. I did not guess at any Frappe function signature.

---

## 0 · The consent conflict — read this before anything else

### What the two positions actually say

| | The spec's US-14 / AC-97 | The user's decision, 17–18 Sep |
|---|---|---|
| The words on the screen | "I have read this and I understand." The words "consent", "I consent", "I agree to" are **banned** from every string, and a test fails the build if one appears | An explicit **"I agree"** |
| What it is called | A **notice**. The company tells you what it records | **Consent**. You choose |
| Legal basis claimed | DPDP s.7(i) — employment is a "legitimate use", so no consent is needed | DPDP s.6 — consent |
| What happens if the person does not act | Not stated. The spec already refuses to finish the join without the tick | The join links the phone but leaves it unable to check in, and asks again on every open |

Both sit **inside the same document**. AC-97 is in §9 (written 17 Sep). The "Consent gate"
section is appended at the end of the same file, also 17 Sep, and says in so many words
that it **"replaces the earlier working position"**. So the spec contradicts itself, and
US-14's acceptance criteria are the stale half.

### Are they in conflict behaviourally, or only in vocabulary?

**Mostly vocabulary. But not only vocabulary — there are three real behaviour changes.**

Behaviour that is **already the same in both**:

- Nothing is set up on the phone unless the person ticks the box. AC-64 requires the join
  to fail without it; `register_device` already does exactly this today
  (`field_checkin.py:267` — `if not cint(consent): frappe.throw(...)`).
- The tick is recorded with time, version and phone, append-only (the new
  `Alvoraa Notice Acknowledgement` doctype).
- A changed notice blocks the app until the person acts (AC-80, `NOTICE_CHANGED`).
- Removing the phone, or HR blocking it, ends app use.

So the gate the user asked for **already exists in the spec**. Calling it consent does not
add a gate.

Behaviour that is **genuinely new** and is not in US-1 to US-21 anywhere:

1. **A "Consent not given" phone state.** Today the spec has five phone statuses
   (Pending, Active, Blocked, Replaced, Removed) and a code that is used *at the moment of
   agreement* (AC-64: "no Pending state at any moment"). The user's mechanism uses the code
   to link the phone **before** agreement, leaving a sixth state that holds a live device
   secret but may not punch. That changes US-10 (the locked save), US-1 (only Active may
   punch), US-12 and US-13.
2. **A new error code `CONSENT_REQUIRED`**, and a new app screen, which must be in app
   version 1 or an old app will show "unknown code" forever (the §6 rule: codes are only
   ever added, never removed, for the life of a supported version).
3. **Ask again on every open, forever.** E4 must return the notice rows to a linked phone
   that has not agreed, on every single open, until it agrees.

There is also a **fourth conflict the user's own decisions create with each other**:

- "Consent must be freely given… an employee who says no must still have another way to
  mark attendance and must not be penalised" (17 Sep), **against**
- "an employee who has not given consent is reminded to give consent every time they open
  the app, until they agree" (17 Sep, "Purpose and reminders").

Those two pull in opposite directions. A prompt the person cannot dismiss, shown on every
open, with no way to say "stop asking", is the sort of thing a regulator looks at when
deciding whether a yes was free. The user already marked this `[LAWYER TO CONFIRM]`. I
flag it because **it is the one part of the design that could make the consent invalid**,
and therefore make the whole photo-and-location processing unlawful.

### What each framing costs, legally

I am not a lawyer. This is what the framing does mechanically, so counsel can decide.

**If it is a notice (s.7(i), legitimate use for employment):**

- There is **no withdrawal right** to honour. The person can stop using the app, but the
  company keeps processing attendance photos and locations for everyone who does use it.
- There is no "freely given" test to pass, so the reminders question disappears.
- The person keeps the DPDP access, correction and grievance rights — those do not depend
  on the basis. PRIV-12 and US-28 already cover access.
- Risk: if counsel later decides a photo of someone's face plus their exact position is
  **not** "necessary for employment" under s.7(i), every punch taken under the notice was
  taken without a lawful basis. That is the risk the spec's PRIV-4 was written to avoid by
  keeping both doors open.

**If it is consent (s.6):**

- **A withdrawal right comes with it, and it is not optional.** Under DPDP s.6(4)-(6) the
  person may withdraw as easily as they gave it, and on withdrawal the company must stop
  processing and, within a reasonable time, **erase** the personal data unless some other
  law requires keeping it. That is a real obligation, and **we have decided not to build
  it**: the user's 17 Sep note says deleting a person's photos and exact locations on
  withdrawal is "not built now… wait for the DPDP lawyer".
- So the current plan is: **call it consent, but do not build what consent obliges.** That
  is the single most consequential gap in this slice. It is not a code problem; it is a
  decision that needs to be made on purpose.
- The consent must be **free**, which is what makes the "alternative way to mark
  attendance" and the "remind on every open" points load-bearing rather than nice-to-have.
- "Remove this phone" has already been declared **not** a withdrawal (17 Sep). So if we go
  with consent, there is currently **no withdrawal path at all** in the design. That must
  be built, or the basis cannot honestly be consent.

### My recommendation

**Build the behaviour the user asked for. Do not settle the legal word yet, and do not
build it in a way that is expensive to change either way.**

Concretely:

1. **Ship the gate, the "Consent not given" state, the decline screen and the re-ask on
   open.** These are good product behaviour whichever basis counsel picks. They cost the
   same either way.
2. **Put the exact tick-box wording in the notice store, as data, with the version.**
   Then changing "I have read this and I understand" to "I agree" is a new notice version —
   one line of data and a version bump — not a code change across the app, the desk and
   the web page. Today `CONSENT_VERSION` is a bare constant at `field_checkin.py:55` and
   the rows are hardcoded in `www/field-checkin.html:290-310`; §4.7 already fixes this.
3. **Replace AC-97's string ban with a pin test on the current version's exact words.**
   A test that bans the word "consent" will fight the user's decision on day one. A test
   that pins "version 2026-09-XX row 6 reads exactly <this>" protects the same thing —
   nobody quietly changing what a person agreed to — without taking a side on the law.
4. **Keep the field names as they are** (`consent_given_on`, `consent_version`). AC-97
   already allowed this. Renaming database columns for a word is pure cost.
5. **Decide the withdrawal question before the first paying customer, not before the
   pilot.** For the pilot the testers are Alvoraa's own people (PRIV-15), so the exposure
   is small. But put it on the record as a known, dated gap.
6. **Ask counsel the reminders question specifically**, because it is the one that could
   invalidate the consent rather than merely complicate it.

**This is the user's decision, not mine.** What I need before coding US-10, US-12, US-13
and US-14 is a yes or no to: "build the consent gate as described, keep the wording in
versioned data, and drop AC-97's word ban".

---

## 1 · Functional impact

### 1.1 What the 21 stories touch, file by file

Every path is relative to `C:/Surbhi-Git/hr-app`.

| File | Exists? | What the server stories do to it | Stories |
|---|---|---|---|
| `alvoraa_portal/alvoraa_portal/field_checkin.py` | yes, 1,126 lines | The main site of work. New endpoints E1-E7, E9-E12; a codes table; the notice store; status rules; `_device_from_token` gains three new statuses; `block_devices_for_leaver` rewritten | US-1, 4, 5, 7-15, 17, 19, 21 |
| `alvoraa_portal/.../doctype/alvoraa_field_device/alvoraa_field_device.json` | yes | 10 new fields, 2 new Select options, permission change, `set_only_once` on `employee` | US-1, 2 |
| `alvoraa_portal/.../doctype/alvoraa_field_device/alvoraa_field_device.py` | yes | Controller rules for every entry path | US-1, 2, 17 |
| `alvoraa_portal/.../doctype/alvoraa_app_invite/` | **new** | The code record | US-5, 7-10, 21 |
| `alvoraa_portal/.../doctype/alvoraa_notice_acknowledgement/` | **new** | Append-only history | US-14 |
| `alvoraa_portal/.../doctype/alvoraa_field_worker_designation/` | **new** child table | One Link field | US-3 |
| `alvoraa_portal/alvoraa_portal/hooks.py` | yes | Append: HR Settings `validate`, Employee form script, daily job entry | US-3, 21 |
| `alvoraa_portal/alvoraa_portal/patches.txt` | yes | Append 3-4 patch lines, **after** 014's line | US-2, 14 |
| `alvoraa_portal/alvoraa_portal/subscription.py` | yes | `TENANT_DOCTYPES` gains the 3 new doctypes (line 402) | US-5, 14 |
| `alvoraa_portal/alvoraa_portal/www/field-checkin.html` | yes, 1,234 lines | **Notice rows only** (FC-1, FC-2). Nothing else | US-14 |
| `alvoraa_portal/alvoraa_portal/www/field_checkin.py` | yes, 27 lines | Reads `notice_facts()`; follows the notice store change | US-14 |
| `alvoraa_portal/alvoraa_portal/www/enrol.html` + `.py` | **new** | Static page, no database read | US-20 |
| `alvoraa_portal/alvoraa_portal/tests/test_checkin_security_014.py` | yes | **Extend, do not rewrite.** Its endpoint→fields map (lines 160-162) is a pin test for `_private_request` | US-4 |
| `hrms` HR Settings custom fields | via `after_migrate` | New section, 6 fields | US-3 |
| `hrms` Employee Checkin custom field `alvoraa_mock_location` | via `after_migrate` | One Check field | US-13 |
| `www/hrms-employee.html` | yes | **NEVER.** Line B rule, and the work board says so | — |

**Not touched by US-1 to US-21:** `alvoraa_goals`, `alvox_compensation`, any `erpnext`
file, any `frappe` file, `deploy/nginx.conf` (that is US-24, outside this scope).

### 1.2 Callers of every existing function that changes

I grepped the whole repository. Code callers only — I have left out the 30-odd documents
that merely mention these names.

| Function in `field_checkin.py` | Who calls it | What breaks if I change it |
|---|---|---|
| `field_checkin()` (the punch, line 337) | `www/field-checkin.html:659` (via `/api/method/alvoraa_portal.field_checkin.field_checkin`); `tests/test_checkin_security_014.py:185, 196, 211, 218, 235` | The web page. Its screens and sentences must not change (AC-35). **Only add arguments** |
| `register_device()` (line 240) | `www/field-checkin.html`; `tests/test_checkin_security_014.py:325, 338, 353, 373` | Same. 014's "identical answer" tests will fail if the shape moves |
| `field_status()` (line 601) | `www/field-checkin.html`; `tests/test_checkin_security_014.py:222, 225, 241, 247, 333, 380` | The spec makes this E4. PRIV-6 removes `work_location.latitude/longitude` from the answer — **the web page reads those today** and must be checked line by line before they go |
| `notice_facts()` (line 675) | `www/field_checkin.py:26-27` only | Changing its return shape changes the web page's template context |
| `photo_retention_days()` (line 688) | inside `field_checkin.py` only (`notice_facts`, `purge_old_checkin_photos:715`) | Nothing outside |
| `log_photo_view()` (line 827) | `hooks.py:86` — `doc_events["Employee Checkin"]["onload"]` | Not changed by this slice. Must keep working for app punches (AC-89) |
| `block_devices_for_leaver()` (line 952) | `hooks.py:97` — `doc_events["Employee"]["on_update"]`, second of two handlers | **Changes (see the finding below)** |
| `checkin_query_conditions()` (line 784) | `hooks.py:168` — `permission_query_conditions` | Not changed. Must still hold for app punches (AC-90) |
| `checkin_has_permission()` (line 809) | `hooks.py:172` — `has_permission` | Same |
| `purge_old_checkin_photos()` (line 696) | `hooks.py:187` — `scheduler_events["daily"]` | Not changed. The **new** clean-up job (US-21) is a separate daily entry |
| `after_migrate()` (line 875) | `hooks.py:224` (`after_migrate`) **and** `hooks.py:239` (`after_install`) | Both lists must get the new fields, or a `bench install-app` site has no columns. CI builds its site that way |
| `CONSENT_VERSION` (line 55) | `field_checkin.py:269, 321, 684`; `tests/test_checkin_security_014.py:327, 375` | Bumping it makes every existing web registration's stored version stale. AC-96 says web phones are **not** asked again — that must be coded deliberately |
| `_private_request()` (line 135) | Every guest endpoint in the file. `tests/test_checkin_security_014.py:158-162` pins the exact field tuple per endpoint | **Every new guest endpoint must be added to that test's map**, or the pin test passes vacuously |
| `_device_from_token()` (line 195) | `field_checkin`, `field_status` | Gains Replaced / Removed / Consent-not-given branches |
| `_refuse_as_pending()` (line 226) | `_device_from_token` twice | Becomes `DEVICE_PENDING` |
| `_hash()`, `_setting()`, `_shift_location_for()`, `_geofence_message()`, `_attach_photo()`, `_require_position()`, `_refuse_duplicate()`, `_validated_captured_at()` | private, this file only | Safe |
| `"Alvoraa Field Device"` as a string | `field_checkin.py:50` (`DEVICE`), `subscription.py:402` (`TENANT_DOCTYPES`), the doctype JSON, and `Employee Checkin.alvoraa_field_device` Link options | The subscription list must gain the 3 new doctypes or a test that classifies every `Alvoraa %` doctype will fail |
| `"field_checkin"` feature key | `subscription.py:182` (FEATURES), 3 `@requires_feature` decorators, `tests/test_opt_in_features.py:121` | See §1.6 |

### 1.3 Four findings in the existing code that would bite

**Finding A — `block_devices_for_leaver` bypasses the controller.** Line 972:

```python
frappe.db.set_value(DEVICE, name, "status", "Blocked", update_modified=False)
```

`frappe.db.set_value` writes straight to the table. It does **not** run the document's
`validate` or `on_update`. So every new rule the spec puts in the controller — move
`token_hash` into `retired_token_hash`, set `status_changed_on` / `_by` / `_source`,
require a `block_reason` — **will not fire for a leaver**. AC-135 and AC-5 would pass in a
desk test and fail in real life. This must be rewritten to `frappe.get_doc(...).save()` (or
a shared helper both paths call), and there must be a test that leaves an employee and then
asserts the hash moved. This is the single most likely silent defect in the slice.

**Finding B — `register_device` still writes the old consent fields.** Lines 318-321 set
`consent_given_on` and `consent_version` on every new web phone. §4.1 says those fields are
"never written by new code, kept as history". Two choices, and the spec does not pick one:
either `register_device` keeps writing them **and also** writes an acknowledgement row
(AC-95 needs the row), or it stops writing them and only writes the row. I recommend: write
the row, stop writing the two fields, and let the backfill patch (M3) fill rows for the
phones that already exist. One place, not two.

**Finding C — the phone doctype currently gives HR Manager and System Manager create and
delete.** I read the JSON: System Manager and HR Manager both have `create: 1, delete: 1,
email: 1, print: 1, share: 1, export: 1`. US-2 removes create and delete. **But
`register_device` inserts with `ignore_permissions=True`** (line 315) so it is unaffected —
good. What *is* affected: any test fixture, demo script or `bench` console that creates a
device the normal way will start failing. And `email`, `print` and `share` are still on,
which US-5 explicitly closes for the invite doctype but nobody has asked about for the
device. A shared device record is a leak of who has which phone. I would close `email`,
`print` and `share` on the device too, and say so.

**Finding D — the assumption about the punch index is wrong.** The spec assumes
"[UNVERIFIED] an index on `Employee Checkin (employee, time)` exists in Frappe HR". I read
`hrms/hrms/hr/doctype/employee_checkin/employee_checkin.json`: `employee` has
`search_index: 1`, `shift` has `search_index: 1`, **`time` does not**. So the E4/E5 query
`employee = X AND time >= today` uses the single-column `employee` index and then filters.
At the spec's own volume that is about 52 rows per employee per month, so it is fine — but
the **daily clean-up job** and the **duplicate-window check** must be written knowing there
is no composite index, and the spec's NFR row should be corrected rather than left as an
assumption. Adding an index to a standard hrms doctype is an upgrade-safety question, not a
free choice; if it is ever needed it goes in as a custom index from `after_migrate`, not an
edit to the hrms JSON.

### 1.4 Doctypes, hooks and jobs — the complete list

**New doctypes (3):** `Alvoraa App Invite`, `Alvoraa Notice Acknowledgement`,
`Alvoraa Field Worker Designation` (child). All three go into `TENANT_DOCTYPES`.

**Existing doctypes changed (1):** `Alvoraa Field Device` — 10 fields, 2 statuses,
permissions, controller.

**Existing doctypes extended by custom field (2):** `HR Settings` (6 fields, one section),
`Employee Checkin` (1 field, `alvoraa_mock_location`).

**Existing doctypes read only (5):** `Employee`, `Designation`, `Company`,
`Shift Assignment`, `Shift Location`. Plus Frappe's `Notification Log`, `Version`,
`Error Log`, `File`.

**Hooks:**

| Hook | Change |
|---|---|
| `doc_events["Employee"]["on_update"]` | Existing entry `block_devices_for_leaver` rewritten (Finding A). Also cancels waiting codes |
| `doc_events["HR Settings"]["validate"]` | **New.** Must coexist with `alvoraa_goals.review_items.validate_hr_settings`, which already validates the same Single. Both run; a test must save HR Settings with both apps installed |
| `doctype_js["Employee"]` | **New.** The desk section (US-16). Client script only |
| `after_migrate` / `after_install` | Both lists gain the new custom fields |
| `scheduler_events["daily"]` | **New** entry for the clean-up job (US-21), separate from `purge_old_checkin_photos` |

**No new hourly or `all` jobs. No change to `permission_query_conditions` or
`has_permission`.**

### 1.5 Persona impact

| Persona | What changes | What must not change |
|---|---|---|
| **CXO / System Manager** | Sees the new section on every Employee across all companies; can edit the HR Settings section; **loses create and delete** on the phone record | Their read of attendance and photos is unchanged. They must not gain a way to unblock a phone |
| **HR Manager** | New buttons: Invite, Cancel, Block. New settings section, with a reason box and a change history. Alerts in the bell. **Loses create and delete** on the phone record; gains nothing on codes or acknowledgements beyond read | Must not see a code after the dialog closes. Must not see employees outside their companies — and this is the **one permission behaviour I cannot verify from this checkout** (assumption W1: does Frappe apply an Employee or Company User Permission to a doctype that merely links Employee?). AC-148/AC-149 must be run before this is called done. If it does not hold, a `company` field plus a query condition is needed on both new doctypes |
| **HR User** | Same as HR Manager minus the settings (read-only there) | Same |
| **Employee (field worker)** | Joins by QR with no login; punches with a photo; can remove their own phone. **Has no Frappe user at all** — every one of their calls is a guest call proving itself with a secret | Must never learn why their phone was blocked (PRIV-13). Must never be shown workplace coordinates (PRIV-6) |
| **Employee (office colleague)** | **Nothing.** No new rows readable, no new menu | A colleague must not be able to read any phone, code or acknowledgement row. There is no Employee-role permission on any of the three |
| **Line manager** | **Nothing new.** Still sees their team's punches and photos through the existing `checkin_query_conditions` | Must not get a "last seen" or a map. AC-107, AC-114 |
| **Guest with nothing** | `/enrol` page, which reads no database | Must not be able to probe employee IDs. 014's rule protects this; `DEVICE_PENDING` must keep it |

### 1.6 Plan gating — do the new endpoints need it, and under which feature?

**Yes, and the feature id is `field_checkin`.** It already exists at `subscription.py:182`,
is `opt_in: true`, `app: alvoraa_portal`, `requires: ["attendance"]`, and is already on all
three existing endpoints. Slice 016 gated ~28 vendor and driver endpoints the same way. The
new ones follow.

| Endpoint | Gate | Note |
|---|---|---|
| E1 check code, E2 not-me, E3 join, E4 start, E5 punch, E6 remove, E9 agree again | `@requires_feature("field_checkin")` | Same as today's three |
| E7 make a code, E10 cancel, E11 block, E12 desk data | `@requires_feature("field_checkin")` | Desk calls, but the spec's AC-42 and AC-103 already require `FEATURE_OFF` there |
| `/enrol` (E8) | **No gate** | It reads no database and reveals nothing. Gating it would give a tenant-plan signal to an anonymous visitor |

**Two ordering rules that matter, both learned from the existing file:**

1. `@requires_feature` goes **above** `@frappe.whitelist()` in source order but **below**
   `_private_request` — read `field_checkin.py:236-239`. `_private_request`'s own docstring
   says it must sit directly under the whitelist "so it also covers the plan gate and the
   rate limit beneath it". Get this wrong and a plan refusal crashes out with the request's
   fields in the log.
2. **`requires_feature` throws a plain sentence, not a code.** I read it at
   `subscription.py:634-663`: it does `frappe.throw(_("{0} is not included in your
   plan."), frappe.PermissionError)`. §7.1 needs a `FEATURE_OFF` code in the body.
   **Do not change `requires_feature`** — 28 vendor endpoints and the goals, analytics and
   payroll endpoints depend on its current behaviour, and slice 016 has only just settled
   them. Add the code in this slice's own wrapper instead (see §2, security).

### 1.7 HRMS domain impact — does a field punch reach pay?

**Yes, indirectly, and nothing in this slice changes that path.**

- An app punch is an ordinary `Employee Checkin` row with `device_id = alvoraa-field-app`.
  Frappe HR's auto-attendance reads `Employee Checkin` against `Shift Type` exactly as it
  reads a biometric machine's rows. So a field punch becomes an `Attendance` row, and
  `Attendance` feeds `Salary Slip` through the payroll's working-days calculation.
- **Therefore a missing or wrong app punch is a pay question, not a convenience question.**
  That is the reason the reliability rules below are not negotiable, and the reason
  `block_devices_for_leaver` (Finding A) matters: a rehire whose old phone silently re-arms
  could punch for themselves.
- The geofence is Frappe HR's own: `EmployeeCheckin.validate_distance_from_shift_location`
  at `hrms/.../employee_checkin.py:122`, gated on
  `HR Settings.allow_geolocation_tracking` (line 123) and using
  `Shift Location.checkin_radius` (line 145). We reuse it and only rewrite its message. **We
  do not touch it** — that keeps us upgrade-safe.
- **Leave, appraisals, goals, compensation, learning: no effect.** No code path reaches
  them.
- **Shifts:** read only. If an employee has no `Shift Assignment` with a location, there is
  no geofence refusal (existing behaviour, AC-197).
- **One thing the 100 m minimum radius decision (18 Sep) touches:** `checkin_radius` is a
  **Frappe HR field on a standard doctype**. We can refuse to *use* a radius under 100 m in
  our own code, and warn in ours, but we must not add a validation to hrms' own Shift
  Location — that is an upstream edit. The constants already in our file
  (`FRAPPE_MIN_RADIUS_M = 1`, `ADVISED_MIN_RADIUS_M = 50`, `DEFAULT_RADIUS_M = 100` at
  lines 86-92) are where the 100 m decision lands, and `ADVISED_MIN_RADIUS_M` becomes 100.

### 1.8 Parallel-work check

`.claude/work-in-progress.md` row for 013 claims, for later use: `field_checkin.py`,
`www/field-checkin.html` (notice rows only), `www/field_checkin.py`, the device doctype
JSON and `.py`, the three new doctypes, new `field_app_*.py`, `www/enrol.*`, `hooks.py`
(append), `patches.txt` (append after 014's line), `subscription.py` TENANT_DOCTYPES
(append), `test_portal_security_010` CEILINGS (append), the HR Settings and Employee custom
fields, `health.py`, and `deploy/nginx.conf` **last**. That matches this analysis.

**Clashes I can see:**

| File | Who else | How to avoid it |
|---|---|---|
| `hooks.py` | Slice 010 claims `doc_events` for Attendance Request and Leave Application. We append to `doc_events["Employee"]` and add `doc_events["HR Settings"]` | Different keys. Append at the end of each dict, never reorder |
| `patches.txt` | 010, 014, 015 all append | Append **after** whatever is last when we rebase, never in the middle |
| `.gitignore`, `.github/workflows/ci.yml` | **Slice 015 claims both**, and 013's app work already appended to them | These belong to the app stories, not US-1 to US-21. No new conflict from the server work |
| `subscription.py` | Slice 016 is in this file | We append 3 strings to `TENANT_DOCTYPES` (line 402 region). 016 worked on the decorator and the endpoints. Small risk, but rebase and re-read before committing |
| `www/hrms-employee.html` | Slices 009, 010 | **We never touch it.** Confirmed |
| HR Settings | `alvoraa_goals/review_items.validate_hr_settings` (slice 010) | Both validate hooks run on the same Single. A test must prove both pass on one save |
| The bench | Several sessions; the board says a release train of 014, 015, 016 is being sequenced | **I used no bench and no site.** Before any build starts, confirm nobody else holds the bench |

**Plan:** do all work in `.claude/worktrees/013-mobile-app` on `slice/013-mobile-app`,
rebased onto `origin/dev` at the moment work starts. Fetch and re-read the incoming diff
before every commit.

---

## 2 · Non-functional assessment

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **neutral, with one watch** | Every new call is bounded and single-employee. E1 is two lookups (invite by hash, employee by name). E4 is three (device by hash, employee, today's punches). E5 adds the photo write. **No loop does a query.** The two places that could go wrong: (a) the settings confirm dialog needs live counts — those must be **one grouped query each**, not a loop over designations; (b) US-16's desk section (E12) must fetch phones and codes in **two** `frappe.get_all` calls with an `in` filter, not one call per row. The punch query relies on the `employee` index only (Finding D) — adequate at 52 rows per employee per month. **Photo storage:** at the new 960x720 / quality 0.7 setting the implementation notes measure ~198 MB a month for 200 staff over 22 days, on a server with 43 GB free. At the spec's design volume of 400 field workers it is roughly **400 MB a month, 4.8 GB a year** — still fine against 43 GB, but it crosses 10% of free disk inside a year, so the 90-day photo purge (already built, `purge_old_checkin_photos`) is what keeps it flat at about **1.2 GB steady state**. That job is now load-bearing for disk, not just for privacy. Worth a disk alert. |
| **Security** | **improves** | Today a phone is created by anyone who posts an employee ID and is then approved by a human. After this slice a phone exists only because HR made a single-use code for one named person. US-2 closes four holes that are open right now: HR can re-point a phone at another employee, unblock a blocked phone, delete the record, and insert one by hand. **`ignore_permissions` scope:** it is used today at `field_checkin.py:315` (insert) and in `field_status`'s punch query, and both are correct — a guest caller has no session to check. Every **new** use must be justified line by line, and the desk endpoints E7, E10, E11, E12 must use **the real permission check on the Employee**, never `ignore_permissions`. **Device secret handling is already right** and stays right: `secrets.token_urlsafe(32)`, SHA-256 hash stored, never echoed. The new `retired_token_hash` must get the same treatment — hidden, `no_copy`, never in any answer. **Rate limits:** Frappe's `rate_limit` is already used per endpoint; §6 wants limits keyed on the code or phone hash, which is a different key from today's. **[UNVERIFIED] whether Frappe's `rate_limit` supports a custom key** — check the installed source before promising AC-44, AC-59, AC-63, AC-82, AC-88, AC-101. If it does not, the limit has to be written by hand against the cache, and that is a design decision, not a detail. **One structural risk: the error-code contract.** §7 needs a `code` and `values` in every refusal body. Today `_private_request` answers a refusal by setting `http_status_code` and returning `None`, and the web page reads the English sentence out of `_server_messages` (`field-checkin.html:629-667`). Adding `code` is **additive** and safe for the web page *if* `_server_messages` keeps carrying the same sentences — but it means editing `_private_request`, which slice 014 wrote three days ago and which a pin test guards. **Do not touch `requires_feature`**, which 28 other endpoints share. |
| **Reliability** | **degrades slightly, and must be designed for** | Today's file has one write path. This slice adds a join that must do four writes in one locked save (invite → Used, old phone → Replaced, new phone → Active, acknowledgement row) and must leave nothing behind if any step fails (AC-66). **Lock order must be fixed and written down: Employee, then invites, then phones — always.** E3 and E7 can run at the same moment for the same person (AC-70), and a deadlock there is a real possibility. **Offline:** the app queues nothing in step 1 — a punch with no signal is not saved, and that is deliberate, but it means a worker in a basement is not marked present, and attendance is pay. **Retries:** the duplicate window is 60 seconds (`DUPLICATE_WINDOW_SECONDS`, `field_checkin.py:81`), which makes a retried punch safe. The new endpoints need the same treatment: E6 (remove) and E9 (agree) must be safe to call twice. **Hook side effects:** Finding A is the live one. Also, the new HR Settings validate hook runs beside `alvoraa_goals`' — if ours throws on a value the goals hook set, HR cannot save HR Settings at all. Fail-closed on eligibility (AC-21) is right; fail-closed on *saving the settings page* is not. |
| **Scalability** | **neutral** | Multi-tenant: one database per site, so a code from tenant A cannot exist in tenant B (AC-57). **Concurrent punches:** 400 workers at a depot at 9 am is the design case. Each punch is one insert plus one file write; the photo write is the slow part and it is why E5 is the only endpoint the spec lets miss its 500 ms budget. **Invite storms:** E7 is capped at 30 an hour per HR user, and each E7 cancels the previous waiting code inside the same save, so one employee can never accumulate codes. The risk that is **not** capped is an attacker hammering E1 with random codes — per-code limits do nothing there, because each guess is a new code. That is what the nginx per-IP zone and the US-19 spike alert are for, and they are **outside these 21 stories** (US-24, and US-19's AC-120). So until US-19 and US-24 ship, E1 is the least protected new surface. |
| **Maintainability** | **degrades** | `field_checkin.py` is 1,126 lines today. The 21 stories roughly double it. **Split it before writing, not after:** the spec already names `field_app_*.py`. My proposal — `field_app_codes.py` (E1, E2, E3, E7, E10), `field_app_device.py` (E4, E5, E6, E9, E11), `field_app_notice.py` (the notice store), `field_app_errors.py` (the one codes table §7 demands), leaving `field_checkin.py` as the web page's endpoints plus the shared helpers. One file for the codes table is a spec requirement, not a preference. The duplication risk is real: three copies of "is this person eligible" would drift, so that is **one function** used by E1, E3, E4, E5, E7 and the desk section. |
| **Data integrity** | **improves, with two new risks** | Improves: `employee` becomes `set_only_once`; statuses become one-way; the acknowledgement history becomes append-only instead of two overwritable fields; the secret hash is preserved rather than lost, so "why did this phone stop" stays answerable. **New risk 1 — duplicate punches.** The 60-second window is the only guard, and it is measured on server time. Two taps 61 seconds apart both save. That is today's behaviour and the spec keeps it. **New risk 2 — clock skew.** The phone's clock is stored as a claim (`alvoraa_captured_at`) and never used for a rule. Expiry and punch time are server time. That is correct and must stay correct: an expiry compared against a phone clock would be trivially defeated. **Cache:** AC-22 says a settings change must apply within 60 seconds. Frappe caches Single values, so **[UNVERIFIED]** whether a plain `get_single_value` read is already fresh after a save on another worker process. If it is cached, the settings read needs explicit invalidation on save — and that invalidation belongs in the same change as the caching, per CLAUDE.md §2. If it is not cached, every eligibility check is a database read, which is fine at this volume. **This must be settled at strategy, not discovered later.** |
| **Compliance / privacy** | **improves, with one large open item** | Improves: acknowledgement becomes a history, not a field (PRIV-3); workplace coordinates stop being sent to the phone (PRIV-6); the block reason never reaches the worker (PRIV-13); no "last seen" or map anywhere (PRIV-9); photo views keep being logged (PRIV-14, existing); the codes never exist in plain form anywhere. **PII touched:** face photo, exact position, GPS accuracy, phone model, designation, company, first name and surname initial. The device secret and the code are secrets and exist only as hashes. **Retention:** photos 90 days by default (existing job); codes and phones kept while linked punches exist (Q-1, answered); acknowledgements kept while the phone has punches; logs 180 days. **Role scoping:** the three new doctypes give no role to Employee at all, which is right. **The large open item is §0** — if the basis is consent, a withdrawal right comes with it and we have decided not to build the erasure that follows. That is a decision on the record, not an oversight, but it must stay on the record. |

---

## 3 · Sequencing and risk

### 3.1 The spec has 30 server stories, not 21

The brief for this analysis names US-1 to US-21. The spec's §9 has **US-1 to US-30** as
server stories; US-31 onwards are the app. US-22 to US-30 are not optional extras — they
carry the privacy and permission **proof**:

| Story | What it carries | Why it cannot simply be dropped |
|---|---|---|
| US-22 | Daily counts and technical alerts, with no names | The only way anyone knows the pilot is working or broken |
| US-23 | A leaver's codes and phones stop | This is **Finding A**. It is a correctness fix, not a report |
| US-24 | nginx protects the device paths | The only real defence against code guessing on E1 |
| US-25 | A busy depot is not refused | The performance proof |
| US-26 | No code, secret, photo, place or name reaches a log | The privacy proof |
| US-27 | People outside HR's remit see nothing | The W1 permission proof — the assumption I could not verify |
| US-28 | "What does the app hold about me?" | A DPDP access-request obligation |
| US-29, US-30 | Migration, and rollback by the switch | How existing tenants get here and how you turn it off |

**I recommend treating US-23, US-26 and US-27 as part of the first increment**, not as a
later batch. US-23 is a bug fix. US-26 and US-27 are the tests that prove the rest did not
break privacy — and per CLAUDE.md, a feature without the test that pins it is one bad merge
away from disappearing.

### 3.2 The smallest safe order

Six steps. Each is a complete, testable thing. Nothing in a step depends on a later step.

**Step 1 — the foundation that is never reverted.** US-1, US-2, US-4, plus US-23
(Finding A) and the file split.

- Why first: US-2 closes holes that are open in production-shaped code **today**. US-4
  freezes the error-code contract, and every later story speaks it. US-1 defines the
  statuses everything else uses.
- Depends on: slice 014 (done, it is on `origin/dev`).
- What ships: nothing user-visible. The phone doctype gets its new shape, the codes table
  exists, the web page behaves exactly as before (AC-35).
- **Not revertable** once the status rules are in — a revert would re-open the unblock hole.

**Step 2 — the settings.** US-3, plus the migration parts of US-29 that create the fields.

- Why here: every eligibility check in every later story reads these settings. Building
  them later means writing the check twice.
- Depends on: step 1 only.
- Watch: the second HR Settings validate hook, beside `alvoraa_goals`.

**Step 3 — the join, end to end.** US-5, US-8, US-9, US-10, US-11, US-14, US-20, plus the
consent gate from §0 if the user says yes.

- Why together: a code that can be made but not used is not testable, and E1/E3 share the
  eligibility function and the notice store.
- Depends on: steps 1 and 2.
- **This is the first usable increment.** After it, HR can make a code and a phone can
  join. It still cannot punch.
- Riskiest single piece in the slice: the E3 locked save. Fixed lock order, one test that
  runs two E3 calls on two connections (AC-65), one test that forces a failure halfway
  (AC-66).

**Step 4 — the daily use.** US-12, US-13, US-15.

- Depends on: step 3.
- **This is the first shippable increment for a pilot.** A field worker can now join,
  punch and remove their phone.
- Watch: PRIV-6 removes the coordinates from `field_status`'s answer and **the web page
  reads them today**. Trace the page by hand before removing the keys.

**Step 5 — the HR desk.** US-6, US-7, US-16, US-17, US-18.

- Depends on: steps 3 and 4 for the data to show.
- Largely client-side work on the Employee form plus E12. No new risk to the punch path.
- Watch: the QR must be drawn in the browser from E7's answer. No other request may carry
  the code (AC-47).

**Step 6 — the housekeeping and the proof.** US-19, US-21, US-26, US-27, US-28, and then
US-22, US-24, US-25, US-29, US-30.

- US-24 (nginx) goes **last** and is a separate approval, because `deploy/nginx.conf` is
  the production nginx too (memory note, 18 Sep: one nginx serves dev and production).

### 3.3 What each story depends on

| Story | Depends on | Blocked by an open question? |
|---|---|---|
| US-1 | 014 (done) | no |
| US-2 | US-1 | Q-12 (one revoke function) — can be added later |
| US-3 | US-1 | Q-5 answered (HR Settings section). Q-4 is copy only |
| US-4 | US-1 | Q-6 (HTTP statuses) — engineer confirms at strategy. Q-8 (new codes) — answer needed |
| US-5 | US-3, US-4 | no |
| US-6 | US-5 | Q-13 (which lifetimes appear) — copy only |
| US-7 | US-5 | no |
| US-8 | US-5 | no |
| US-9 | US-8 | no |
| US-10 | US-5, US-8, US-14 | **§0 — the consent gate.** Blocks the final shape of the locked save |
| US-11 | US-10 | Q-3 answered (app phones only) |
| US-12 | US-10 | **§0** — the "consent not given" branch lives here |
| US-13 | US-12 | Q-11, Q-15 (show and refuse the fake-location flag) — both "not now" |
| US-14 | US-3 | **§0 — this is where the conflict lands.** AC-97 is the stale criterion |
| US-15 | US-12 | Q-14 — copy only |
| US-16 | US-5, US-10 | no |
| US-17 | US-1, US-2 | no |
| US-18 | US-1 | no |
| US-19 | US-9, US-10 | Q-7 — copy only |
| US-20 | none | Q-7 — copy only |
| US-21 | US-5 | Q-1 answered (keep codes that made a phone; delete the rest after 12 months) |

### 3.4 What must NOT be built yet, and why

1. **The nginx change (US-24).** `deploy/nginx.conf` is bind-mounted and the same nginx
   serves production. A dev push carrying it restarts the live site's proxy. It goes last,
   on its own, after `nginx -t`, with its own approval. Slice 018 is separately adding a
   parse gate to the deploy for exactly this reason — **wait for it**.
2. **Any erasure-on-withdrawal code.** The user decided on 17 Sep to wait for counsel.
   Building a delete now and getting the scope wrong destroys records that cannot be
   recovered. Build the consent *record*; do not build the delete.
3. **Refusing a punch because the fake-location flag is set (Q-15).** Flag only in step 1.
   We have no idea yet what the false-positive rate is on cheap Android phones, and a false
   refusal means somebody is not marked present, which means pay.
4. **Any index added to a standard hrms doctype.** Finding D says the composite index does
   not exist. It is not needed at this volume. If it ever is, it goes in as a custom index
   from our own `after_migrate`, never as an edit to `hrms`.
5. **Changing `requires_feature`.** 28 vendor endpoints and the goals, analytics and
   payroll endpoints share it, and slice 016 has only just stabilised them.
6. **Deleting the old `consent_given_on` / `consent_version` fields.** They are the only
   record of what existing web-page users agreed to. Keep them, stop writing them.
7. **Anything in `www/hrms-employee.html`.** Three slices are in that file.
8. **A second attempt at the "one designation list per tenant" question (Q-9).** Answered:
   fine for step 1. Do not build per-company lists on spec.

### 3.5 The three biggest risks, ranked

1. **The consent question (§0).** It changes US-10, US-12, US-13 and US-14, and it changes
   what we owe the person afterwards. Everything else waits on nothing; this waits on a
   decision.
2. **The E3 locked save.** Four writes, two callers that can collide, and a failure halfway
   leaves a person unable to join with a code that says it was used. Fixed lock order plus
   two hostile tests.
3. **The W1 permission assumption.** If Frappe does not apply an HR User's company
   restriction to a doctype that only links Employee, then an HR User in a two-company
   tenant can read every phone and every code in the tenant. That is a visibility change we
   did not authorise. **This must be tested on the bench before step 3 finishes**, not at
   the end.

---

## 4 · Open questions for the user

Each one has my recommendation. **You decide; I have not acted on any of them.**

| # | The question, plainly | My recommendation |
|---|---|---|
| **C-1** | **The consent wording.** Your 17 Sep decision says the screen must say "I agree". The spec's AC-97 bans that exact word and would fail the build. Which wins? | **Your decision wins.** Drop AC-97's word ban. Put the wording in the versioned notice store as data, so changing it later is a version bump and not a code change |
| **C-2** | **Does calling it consent oblige us to delete a person's photos and locations when they withdraw?** You decided on 17 Sep not to build that yet. | Build the gate and the record now; ask counsel about erasure before the first paying customer. But **note on the record** that until then we are calling it consent while not honouring what consent obliges. If you would rather not carry that, call it a notice for the pilot and switch the word when counsel answers — the mechanism is identical either way |
| **C-3** | **Is there any way to withdraw at all?** You decided "Remove this phone" is **not** a withdrawal. So today the design has no withdrawal path. | Add one small thing in step 3: a "I no longer agree" action that puts the phone into the same "consent not given" state. It costs almost nothing because that state already has to exist |
| **C-4** | **"Remind on every open, until they agree" against "consent must be freely given."** These two decisions of yours pull against each other. | Ask counsel specifically about this one. My engineering recommendation: show the notice on open, but let the person dismiss it for that session. Same prompt, no trap |
| **C-5** | **There are 30 server stories, not 21.** US-22 to US-30 carry the privacy and permission proof. | Include **US-23, US-26 and US-27** in the first build. US-23 is a real bug (see Finding A); the other two are the tests that keep the rest honest |
| **C-6** | **`block_devices_for_leaver` writes straight to the table and skips the controller.** So the new block rules will not fire when someone leaves. | Rewrite it to save the document properly, with a test that leaves an employee and checks the secret was retired. Small change, big consequence |
| **C-7** | **The phone record can currently be emailed, printed and shared** by HR Manager and System Manager. The spec closes this for codes but never mentions the phone. | Close `email`, `print` and `share` on the phone record too. A shared device record says who carries which phone |
| **C-8** | **Do the desk endpoints (E7, E10, E11, E12) need the plan gate?** | Yes, `field_checkin`, same as the phone endpoints. The spec's own AC-42 and AC-103 already expect it |
| **C-9** | **The spec assumes a database index that does not exist** on Employee Checkin (`time` is not indexed). | Correct the spec; add no index. At your volumes the existing `employee` index is enough. Revisit only if a measurement says otherwise |
| **C-10** | **Splitting `field_checkin.py`.** It is 1,126 lines and these stories roughly double it. | Split it into four files at the start of step 1, while it is still small. Splitting a 2,200-line file later, across another slice's changes, is how merges go wrong |
| **C-11** | **Three things I cannot check without the bench** (which another session may be using): does Frappe's rate limiter take a custom key; are HR Settings values cached across worker processes; does an HR User's company restriction reach a doctype that only links Employee. | Give me one short bench window before step 3 to run these three checks, or accept that the first two could change the design mid-build and the third could turn out to be a visibility hole |
| **C-12** | **When the notice version changes, what happens to the 90-day photo retention line inside it?** The notice quotes the tenant's number, and the tenant can change it without a new notice version. | Keep quoting it live, as `notice_facts()` already does. The words are versioned; the number is the tenant's current setting. Say so in the notice |

---

## Appendix — what I ran

| Command | Result |
|---|---|
| `git rev-parse HEAD origin/dev` | `d1fd9c6` / `baa9f68`; one commit apart, slice 014 is in both |
| `git status --short` | 5 modified, 7 untracked; none of them a file this slice would change |
| Grep for every `field_checkin` symbol across the repo | 43 files, of which **9 are code**; the rest are documents. Full caller table in §1.2 |
| Read `alvoraa_field_device.json` fields and permissions | 17 fields today; HR Manager and System Manager hold create, delete, email, print, share |
| Read `subscription.py` FEATURES and `requires_feature` | `field_checkin` exists, opt-in, requires `attendance`; the decorator throws a sentence, not a code |
| Read `employee_checkin.json` search indexes | `employee` and `shift` indexed; **`time` is not** |
| Read `employee_checkin.py` geofence | `validate_distance_from_shift_location` at line 122, gated on `allow_geolocation_tracking`, uses `Shift Location.checkin_radius` |

**No bench command. No docker command. No site touched. No commit. No push.**

---

## User decisions on this analysis (2026-09-18)

All four taken on the recommendation given. Behaviour is unchanged from what she
asked for on 17-18 September; only the framing and two gaps move.

**C-1 · The tick box says "I have read this and I understand." Not "I agree".**

The gate she asked for stays exactly as it was: no tick, no app, and the person is
asked again next time. What changes is what we promise. Asking for *consent* under
DPDP s.6 creates a right to withdraw it, and honouring that withdrawal would mean no
longer recording someone's attendance - a strange promise about an ordinary condition
of employment. The notice framing under s.7(i) needs no such promise.

Consequences for the build:
- AC-97's ban on the word stands for the pilot, but as a **pinned test on the current
  version's exact words**, not a blanket string ban. The wording lives in the
  versioned notice store **as data**, so a later change to "I agree" is a version
  bump, not a code change across app, desk and web page.
- Database field names stay as they are. `consent_given_on` is a column name, not a
  promise to the employee.

**C-3 · Build a withdrawal path.** There is currently none, in either framing. Someone
who agrees on Monday and regrets it on Friday can do nothing. It reuses the
"not agreed" phone state that has to exist anyway, so it is close to free, and it is
the honest half of a gate.

**C-4 · The re-ask can be dismissed for that session.** Her instruction was that a
person who declines is asked again every time they open the app. That stands. But a
prompt with no way past it is the textbook example of agreement that is not freely
given - it would undermine the very thing it collects. So: dismissible for that
session, returning on the next open.

**C-6 · The leaver hook is fixed inside this slice.** `block_devices_for_leaver` writes
with `update_modified=False`, which skips `validate` and `on_update`, so every new rule
- retiring the secret hash, the status-changed fields, the required block reason -
would silently not fire for the one case that matters most. With a test that leaves an
employee and checks the secret was actually retired.

**Still open, and deliberately so:** erasure on withdrawal waits for counsel, as agreed
on 17 September. The gap is recorded rather than quietly carried - see [[C-2]] in §0.

## Two more decisions (2026-09-19)

Both taken after step 1 was proven on the bench.

**C-7 · `email`, `print` and `share` come off the phone record** for HR Manager and
System Manager. A shared device record says who carries which phone. No workflow
needs to email one.

**C-11c · The company scoping hole is fixed in this slice, in step 2.** An HR user
restricted to one company could list every company's phone records - name, model,
last seen, check-in count - because `Alvoraa Field Device` links only Employee and
had no query-conditions or has-permission hook. Pre-existing since slice 008; the
step-1 probe was the first to look. Fix: a query-conditions + has-permission pair
scoped through the Employee's company, shaped like `checkin_query_conditions`, with a
pinned two-company test. **This overrides the analysis's earlier "no change to
permission_query_conditions"** - that line was written before the hole was known.
The step-3 doctypes (App Invite, App Consent) link only Employee too and get the same
treatment when they are built.

## Decisions after step 4 (2026-09-20)

- **One GPS accuracy limit, 50 m, for the app AND the existing web check-in page.** The
  page was at 100 m. Two rules for the same act would confuse HR the first time a person
  is refused on one and not the other. This is a declared change to live web behaviour.
- **Steps 1-4 merge into local dev now**, as the first pilot-shippable unit, rather than
  waiting for steps 5 (HR desk screens) and 6 (housekeeping, nginx last on its own
  approval), which follow on the same branch.
- Decision 4 (slice 030, separate commit): a store-limited HR Manager is refused
  organisation-wide settings writes. Confirmed by the user directly on 2026-09-20.

**Release-note sentence, quotable as is:** "The web check-in page now refuses a GPS
reading worse than 50 m (it was 100). Some check-ins that used to pass will be asked to
step outside and try again. This is deliberate: one accuracy rule for the app and the
page, decided 2026-09-20."
