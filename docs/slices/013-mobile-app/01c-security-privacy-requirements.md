---
slice: 013-mobile-app
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-09-17
status: draft — recommendation only; Surbhi decides
inputs: [01-product-brief.md (incl. Gate decision 2026-09-17), 01a-ux-opportunities.md, 01b-ux-design.md (incl. Design check decision 2026-09-17), prototype-v1/index.html, 07-devops-inputs.md §1–§2 (OPS-1..OPS-36), 00-sequencing-recommendation.md (User decisions), 008-field-checkin/10-native-app-background-geofence.md, 008-field-checkin/01c-security-privacy-requirements.md, alvoraa_portal/alvoraa_portal/field_checkin.py, www/field_checkin.py, www/field-checkin.html, alvoraa_field_device.json and .py, hooks.py, subscription.py (requires_feature), deploy/nginx.conf (git copy), .github/workflows/*.yml, .claude/context/security-compliance-baseline.md, compliance-feature-map.md, product-context.md]
---

# 013 — Mobile app, step 1 — security and privacy requirements

**I recommend. You decide.** I am not a lawyer. Where an answer turns on the law, I say so
and write a question for counsel instead of guessing.

Nothing was run for this document. No bench, no docker, no server, no build. I read the
code on `dev` and the slice documents. Regulatory points were checked against public
sources on 17 Sep 2026 (listed at the end).

---

## Read this first

**Bad news first.**

1. **Joining with no HR approval is defensible for the Attendance app only, and only with
   the conditions in §6.** It is **not** safe to reuse for signing in to My HR. That needs
   its own security design (§9). The step-1 verdict does not carry over.
2. **I challenge the 7-day default.** I recommend **24 hours as the default, 7 days as the
   most an organisation can set.** A code that lives a week sits in WhatsApp chats, phone
   galleries and chat backups for a week. If you keep 7 days, it works, but it is a named
   risk that needs your name and a date (R1).
3. **Today's phone record can be edited in ways that break this design.** In
   `alvoraa_field_device.json`, the `employee` field can be changed after the phone joins,
   HR Manager can create and delete phone records, and HR User can write the status. So
   an HR user could point Ramesh's working phone at Suresh, or delete the record that
   proves who joined. With no approval step, the phone record **is** the audit trail. This
   must be fixed in this slice (SEC-8, SEC-9).
4. **This slice must not reach `dev` before slice 014.** Two live problems are being fixed
   there: a made-up `X-Forwarded-For` header dodges every Frappe per-IP rate limit
   (OPS-19), and a server error can write the photo, GPS and name into logs (OPS-20).
   The new join endpoints would inherit both, and would add the QR token to that path.
5. **The safety gates this design leans on do not exist yet.** There is no secret scan in
   CI, no `ignore_permissions` counter, and no check of the app's Android permissions
   (checked `.github/workflows/*.yml`). Without them, "no background location" and "no
   keys in the repo" are promises, not controls.
6. **Nobody has decided the legal basis for photo and location.** Consent, or "legitimate
   use for employment" under DPDP section 7(i)? The screens work either way if the tick box
   keeps saying "I have read this and I understand", not "I consent" (PRIV-4). The
   compliance owner is still not named.
7. **The phone and the photo are claims, not proof.** A rooted phone or a script with a
   copied device secret can send any position and any picture. Photos help only if a
   person looks at them. This is true today on the web page too (R3).

**My verdicts on the design decisions**

| Decision | Verdict | Conditions |
|---|---|---|
| **No HR approval step** | **Accept for Attendance, with conditions** | SEC-1 to SEC-25 and PRIV-1 to PRIV-15 — above all single use under a lock (SEC-5), no forging or unblocking phones (SEC-8, SEC-9), HR told at once (SEC-13) and server text drawn as text (SEC-17) |
| **7-day default lifetime** | **Challenge.** Keep 7 days as the maximum; default 24 hours | Server clamps the lifetime (SEC-4). If 7 days stays the default: accepted risk R1 |
| **D2** "This is not me" cancels the code | **Accept** | Needs the live code; rate limited; recorded as "cancelled on a phone"; the HR person who made it is alerted (SEC-7, SEC-13) |
| **D3** a new phone replaces the old | **Accept** | Only through a fresh HR code; inside one locked database transaction; only `Active` phones may punch (SEC-5, SEC-10) |
| **D4** no unblock | **Accept, strongly** | Enforced in the phone record's controller for every path — form, list edit, import, API — not by hiding a button (SEC-8) |
| **D8** used-code screen shows when | **Accept** | Time only. No phone model, no name, no place (SEC-3). A second scan of a used code from another phone alerts HR (SEC-13) |
| **D17** one code at a time | **Accept** | Making a new code cancels the old one inside one locked transaction (SEC-6) |
| **"Copy link"** in the invite dialog (01b §9.2) | **Drop it in step 1** | The app cannot open a pasted link (no App Links in step 1). The link only adds a text copy of a live code. Keep **Copy picture** and **Print** |

---

## 1 · Threat model, in four lines

1. **Who wants this, and what is the cheapest way?** Not an outsider. The cheapest attack
   is **a colleague or friend who gets the QR picture** — from a forwarded WhatsApp message,
   a printed sheet on a desk, or HR's screen — and joins as the worker first. Next: **a
   worker who hands their own code to a friend** so the friend punches for them. Next: **an
   HR user** who makes a code and joins on their own phone. The data they get is small
   (first name, designation, company, workplace, today's punches). What they really get is
   **the power to mark attendance, which feeds pay.**
2. **Blast radius of one mistake.** Designed well: **one employee per code.** One bad
   mistake widens it fast. A join endpoint that trusts an employee ID, or an issue endpoint
   a guest can call, makes it **every employee in the tenant.** A script injected through a
   tenant-controlled name (designation, company) runs inside the app with native access,
   in **every worker's phone in that tenant** (SEC-17). Cross-tenant is bounded by one site
   per tenant, and a token lives in one tenant's database only — but test it (SEC-15).
3. **What is newly possible?** A phone becomes able to punch **with no human decision at
   the moment it joins.** An unauthenticated person holding a code sees a name, a job and a
   company. The server collects the **phone's model name**. HR gets a join history.
4. **How would we find out?** Today, only if HR opens the Employee record and looks. That
   is the gap. So this slice must **tell** HR when a code is used, when "This is not me" is
   pressed, when a used code is scanned again from another phone, and when one phone joins
   two people (SEC-13). The real worker also finds out, because their own scan says "already
   used at 9:01" (D8) or their old phone says "You joined on another phone" (D3).

**Why no-approval is not much weaker than today.** In slice 008, HR "approves" a phone that
typed an employee ID. HR sees nothing more than a phone model and a time. The approval
stops the "first to register wins" attack, not much else. The QR moves HR's decision to
the moment HR makes the code, and binds it to a secret. **The new exposure is the window
between making the code and using it.** So lifetime and detection are what matter most.

---

## 2 · Data inventory

Sensitivity classes used here: **Secret** (a credential), **Sensitive** (photo, precise
location), **Personal** (identifies or describes a person), **Internal** (no person).
**Honest note:** the shared sensitivity-class mechanism (compliance map A1) has no verified status, and I found none applied to these doctypes.
These classes are labels in this document. They drive nothing automatically yet.

| Item | Class | Purpose | Retention (recommended — counsel to confirm, Q-C3) | Who may see it |
|---|---|---|---|---|
| **QR token** (plaintext) | Secret | Prove HR chose this person, once | **Never stored on the server.** In the HR browser only while the dialog is open. In the app's memory only from scan to "Agree and finish" | The person HR gives it to |
| QR token hash (SHA-256) | Internal | Look up the code without keeping it | Same as the invite record | Nobody reads it; hidden field |
| **Invite record** — employee, made by, made at, lifetime, expires at, outcome (waiting / used / cancelled by HR / cancelled on a phone / ran out), used at, which phone | Personal | Audit: who let which phone in, and how | **Keep, do not delete when it runs out.** Mark it "ran out". Keep while any attendance record from the phone it created exists. Brief S5 said "expired ones cleaned daily"; that would delete the audit trail | HR with permission on that Employee |
| **Device secret** (plaintext) | Secret | Prove each call comes from the joined phone | **Never stored on the server.** On the phone, Keystore-backed secure storage only | Nobody |
| Device secret hash | Internal | Look up the phone | With the phone record | Nobody reads it |
| **Phone record** — employee, status, how it joined, joined at, phone model name, platform, app version at join, status changes with who / when / why | Personal | Show HR which phone punches for whom; block it | While any attendance record links to it (`Employee Checkin.alvoraa_field_device`) | HR with permission on that Employee |
| **Phone model name** (e.g. "Redmi 12") | Personal | Let HR and the worker tell phones apart | With the phone record | HR; the worker in Settings |
| **Block reason** ("Someone else was using it", …) | Personal — may be an allegation | Explain a block later, in a grievance | With the phone record | **HR only. Never sent to the phone** |
| **Photo at punch** | Sensitive | Evidence the person was there | Organisation setting, default 90 days, legal hold wins (built: `purge_old_checkin_photos`) | HR; the person's manager (built: `checkin_has_permission`); the person. Every non-owner view logged (built: `log_photo_view`) |
| **GPS position + accuracy at punch** | Sensitive | Check the geofence; settle a dispute | With the attendance record (existing). Q-C3 asks whether exact coordinates must stay that long | Same as the photo |
| **Mock-location flag at punch** (new, SEC-21) | Personal | Flag a faked position for HR | With the attendance record | HR; the person's manager |
| **Name on "Is this you?"** — first name, surname initial, designation, company | Personal | Stop honest mistakes (a forwarded code) | Not stored. Sent once in the check answer | Whoever holds a **live, eligible** code |
| `used_at` / `expired_at` on a dead code | Personal (thin) | Let the real owner report a hijack (D8) | Not stored beyond the invite record | Whoever holds that code |
| **Notice acknowledgement** — notice version, time, language, which phone, app or web | Personal | Show which words the person read | **Append-only history.** Keep as long as any data collected under that version is kept | HR; the person (Settings › What this app records) |
| **Notice text of each version** (EN, later HI) | Internal | Answer "agreed to what?" years later | For ever, or as long as any acknowledgement points to it | Anyone |
| App version on each call | Internal | Refuse old apps; know when a version can retire | Logs only; daily counts with no names (OPS-34) | Engineering |
| Workplace name and radius | Internal | "Be within 100 m of Okhla Depot" | Phone may keep | The worker |
| Workplace **latitude and longitude** | Internal | **None on the phone** | **Stop sending it** (PRIV-6) | — |
| Org settings: field worker designations, app on/off, code lifetime; change history | Internal | Decide who may use the app | Change history kept | HR Manager (D20) |

**What the app must never collect:** IMEI, Android ID, serial number, advertising ID, MAC
address, phone number, SIM details, contacts, the list of installed apps, gallery contents,
or location outside the moment of a punch. Capacitor's `Device.getId()` is on this list.

---

## 3 · Access intent — including who must NOT see what

The business analyst builds the permission matrix from this table.

| Who | May see / do | Must NOT see / do |
|---|---|---|
| **Guest** (no code) on `/enrol` | A page that says "Open the Alvoraa app and scan this code" | Anything about any person or company beyond the host name. The page must never look up or redeem a code |
| **Whoever holds a code** before joining | For a live, eligible code: first name, surname initial, designation, company, notice rows. For a dead code: its outcome and one time | Full name, employee ID, photo, email, phone number, date of birth, workplace, anything about other employees. Names for a dead or ineligible code |
| **Field worker, on their joined phone** | Their own name, designation, company, workplace name and radius, today's punches, notice version and date agreed, app version, host | Block reason, who made the code, other people, workplace coordinates |
| **HR Manager** | Make and cancel codes; see phones, invite history, phone model, join time, status, block reason; block; change Field App Settings (D20) | The plaintext code after the dialog closes. "Last seen", "online now" or a map. **Unblock** (D4). **Delete** a phone or invite record. **Create** a phone record by hand. **Change** which employee a phone belongs to |
| **HR User** | Same as HR Manager for employees they have permission on, **except** Field App Settings | Same as HR Manager. **Employees outside their user permissions** (for example another company in a multi-company tenant) — Q-U4 |
| **Line manager** | Nothing new in step 1. Team punches and photos as today (built) | Phone records, invite history, block reasons |
| **Colleague (Employee role)** | Nothing new | Any phone record, invite, or other person's punch |
| **CXO / System Manager** | As HR Manager | As HR Manager |
| **Alvoraa staff (control plane)** | Daily counts of outcome codes and app versions per site, no names, no phone IDs (OPS-34) | Any person-level record |
| **Other tenants** | Nothing | Any code, phone or person on another site |
| **Third parties** (Google Fonts, analytics, crash tools) | Nothing — the app loads nothing from outside (OPS-22); no crash tool in the pilot (gate decision 6) | Worker IP addresses, device data, anything |

**Fail closed.** If the field-worker designation list is empty or cannot be read, nobody is
a field worker for the app. If the plan check fails, refuse. If a phone's status is anything
but `Active`, refuse.

---

## 4 · Obligations engaged

| Obligation | What it means for this slice | Source and date verified |
|---|---|---|
| **DPDP Act 2023 — lawful basis** | Photo and location at punch rest on either consent (s.6) or legitimate use "for the purposes of employment…" (s.7(i)). The product design differs: consent must be free and as easy to withdraw as to give. **Counsel decides** (Q-C1) | Section 7(i) text read 17 Sep 2026 (dpdpa.com, Bar & Bench) |
| **DPDP Rules 2025 — timing** | Notified in November 2025. The notice, consent, security, breach and rights duties apply **18 months later, about May 2027.** Sources differ by a day (13 or 14 Nov 2025 start; 13 or 14 May 2027). No live customer today, so nothing here is overdue — but build to it now | Read 17 Sep 2026 (Shardul Amarchand Mangaldas; PIB PDF; timeline summaries). **The baseline says 14 Nov; some sources say 13 Nov. I did not edit the baseline in this run (documents in this folder only). To fix in the baseline next.** |
| **DPDP — notice, minimisation, security, retention** | Versioned notice with an acknowledgement history; collect only the phone model name; secrets hashed; retention per item | Baseline §2, verified 24 Aug 2026 (24 days old, current) |
| **CERT-In Directions 2022** | No new infrastructure duty. A leak of photos or positions from this feature is a reportable incident with a 6-hour clock. 180-day India log residency is still unmet (existing gap) | Baseline §3 and §3a, verified 24 Aug and 6 Sep 2026 (current) |
| **Hosting in France** | Photos and positions are stored in France. The notice or privacy policy must say so before a real customer (baseline §3a decision) | Baseline §3a, 6 Sep 2026 |
| **GDPR — only if EU exposure** | Founder has not answered. If yes: employee consent is valid only in exceptional cases (EDPB Guidelines 05/2020), so another basis is likely; location of employees points to a DPIA. **Photos are not "biometric" special-category data unless processed to identify a person by technical means** (Recital 51) — our refusal of face matching (product-context §6.3) keeps it that way | EDPB 05/2020 and Recital 51 read 17 Sep 2026 |
| **OWASP ASVS 5.0 Level 2** | Adopted. The join, token and device-secret requirements below map to its authentication and session chapters | Baseline §5, 24 Aug 2026. I did not re-read ASVS today. **OWASP MASVS** (the mobile checklist) is a sensible second checklist — **not verified today** |
| **Google Play / Apple store rules** (data safety form, disclosures) | Not engaged in step 1 (no store listing). Engaged before any store release | **Not verified today** |
| **EU AI Act** | Not engaged. No AI, no face matching | Baseline §4 |

---

## 5 · Abuse cases

Each row: who, how, what they get, what stops or reveals it, and what is left.

| # | Actor and path | What they get | Control (requirement) | What is left |
|---|---|---|---|---|
| A1 | **Photographed printed sheet or HR screen.** A colleague photographs the QR on a desk, or over HR's shoulder, and joins before the worker | Punch as the worker (with their own face in the photo); first name, designation, company, workplace, today's punches | Single use under a lock (SEC-5); lifetime (SEC-4); HR told at once (SEC-13); the worker's own scan says "used at 9:01, tell HR" (D8); one-tap block and a new code replaces the phone (D3, D4) | Wrong punches until someone notices. **Detected, not prevented.** R1 |
| A2 | **WhatsApp copy.** HR sends the picture; it is forwarded, sits in a group, the gallery, a Google Drive chat backup | Same as A1, for anyone who ever sees the picture while the code lives | Same as A1. Invite dialog warning (built in design). **Drop "Copy link"** (§ Read this first). Shorter default lifetime | Same as A1; this is the main reason I challenge 7 days |
| A3 | **Shoulder-surfing** the code while HR shows it on screen for a person standing in front of them | Same as A1 | HR can pick 1 hour for an in-person handover (D6) | Small |
| A4 | **Buddy punching by agreement.** The worker gives their code to a friend, or later lets the friend use the joined phone | Attendance without being there | One working phone per person (D3); photo at every punch; mock-location flag (SEC-21); HR alert when one phone install joins a second person (SEC-13) | **Not prevented.** Photos deter only if someone looks. No face matching, by product rule. R2 |
| A5 | **"Is this you?" as a leak.** Anyone who scans a live code learns first name, surname initial, designation and company | Those four facts | Only for live, eligible codes; server sends only those fields (SEC-3); no employee ID; the printed sheet already carries the full name (D14) | Accepted. It tells the holder less than the paper sheet does |
| A6 | **Replay.** Re-send a captured redeem, peek, "not me" or punch request | A second phone; a second punch | Redeem is single use under a lock (SEC-5); peek changes nothing; "not me" works only on a live code; punch uses the device secret over HTTPS, server time, 60-second duplicate window (built) | Small |
| A7 | **Guessing codes.** Script tries random tokens against the check endpoint | Nothing, unless a guess hits | 256-bit random tokens (SEC-1). **Per-code limits do not slow guessing** (each guess is a new code), so: a real-IP nginx limit and a per-site alert on unknown codes (SEC-12). Frappe IP limits mean nothing until slice 014 lands | None worth worrying about. Entropy does the work |
| A8 | **Token in logs or URLs.** Query string in nginx access logs; a GET URL that draws the QR; a Print Format or PDF; a URL shortener; Version history; a 5xx request dump | A live code for anyone who reads logs or backups | Fragment only, POST only, hash only, field name contains `token`, QR drawn in the browser, no print format, PDF, email or shortener; coded 4xx for expected refusals (SEC-2, SEC-11); slice 014 for 5xx dumps | Small, once 014 lands |
| A9 | **Lost or stolen phone.** No app lock in step 1 | Punch as the worker; name, workplace, today's punches | HR block works on the next call (SEC-10); a new code replaces it (D3); leaver hook blocks (built) | Until HR is told. **For My HR an app lock is required** (§9). R4 |
| A10 | **Shared phone.** Worker B joins on worker A's phone | A's phone record stays `Active` but the phone no longer holds A's secret — an orphan | The app sends its current secret when joining; the server marks the old record `Removed` and flags HR (SEC-14). Step 1 does not support two people on one phone | Small |
| A11 | **Old app version** with a known flaw | Whatever the flaw allows | Minimum version plus a security deny-list the server can apply at once (SEC-19); raising it for security is your call each time (OPS-27) | Small |
| A12 | **Rooted phone, fake-GPS app, or a script** with a copied device secret | Punch from anywhere, with any photo | Mock-location flag from Android (SEC-21) catches common fake-GPS apps. **A script bypasses the app entirely.** No root blocking in step 1 (it locks out cheap phones and custom ROMs, and is easy to hide) | **Position and photo are claims.** R3. Revisit hardware key attestation or Play Integrity before a store release |
| A13 | **Tenant confusion.** A code from tenant A used against host B, or a host that is not a tenant | Nothing, if built right | The token lives in tenant A's database only; the app keeps the host from the QR and talks to no other (SEC-14, SEC-15). **Unknown host must not fall through to a default site** — to verify on the bench | Rogue tenant phishing another company's workers with a look-alike company name: worry W2 |
| A14 | **Planted QR** pointing at a server we do not own | The worker's photos and positions go to the attacker | Release build accepts only `https://<tenant>.alvoraa.co`, parsed strictly, with **no network call** for anything else (SEC-14, OPS-7) | Small |
| A15 | **CORS** turned on to make the bundled page work | Logged-in portal calls from `localhost` origins | Never Frappe's `allow_cors`; prefer native HTTP; if nginx CORS, exact origins, device paths only, no credentials (SEC-18) | Small |
| A16 | **Native bridge via a hostile name.** An HR User sets a designation or company name to `<img src=x onerror=…>`. The bundled page draws it as HTML | Script runs **with the native bridge** in every worker's app on that tenant: reads device secrets, uses the camera | Every server string drawn as text (SEC-17); strict content policy in the bundled page (SEC-16); no remote pages (SEC-16) | Small, if tested. Today's page escapes through `esc()` (`field-checkin.html:623`) but also writes `innerHTML` in four places (lines 822, 871, 1066, 1080) — each must stay fed only by escaped or fixed strings |
| A17 | **HR insider.** HR makes a code for a worker and joins on their own phone, or re-points a joined phone to another employee, or deletes the record | Punches for someone else; an erased trail | Invite and phone records not deletable or re-pointable by HR (SEC-8, SEC-9); the worker's real phone shows "replaced" (D3); the join alert goes to all HR Managers, not only the maker (SEC-13) | A small tenant with one HR person who is the insider. Ghost employees are an HR-process risk outside this app |
| A18 | **Departing employee** with a joined phone | Punches after leaving | Leaver hook blocks phones (`field_checkin.py:836`); punch refuses non-`Active` employees (built); **waiting codes are cancelled too** (SEC-7) | None once status changes |
| A19 | **Guest on `/enrol`** | Nothing | Page never reads the fragment, never calls the server with it, loads nothing from outside, removes the fragment from the address bar (SEC-2) | None |
| A20 | **HR User in a multi-company tenant** issuing codes for, or viewing phones of, another company | Staff and phones outside their remit | Issue and view use Frappe's permission check on that Employee, never `ignore_permissions` for the check (SEC-9). **I could not verify** whether Frappe applies Employee user permissions to the phone doctype today (W1) | Unknown until tested |

---

## 6 · Requirements

Each one says what must be true and how it is tested. "Unit" means a Python test run with
`bench run-tests` on the test site. "CI" means a check that fails the build. "Device" means
a test on a real pilot phone. The business analyst traces each one to an acceptance criterion.

### Security — the code (QR)

**SEC-1 · The code is strong and never kept.** The server makes each code with at least
128 bits from a secure random source (`secrets.token_urlsafe(32)` gives 256). Only its
SHA-256 hash is stored. The plaintext never reaches the database, Version history, a
Comment, a Notification, a realtime message, the Error Log or `frappe.log`.
*Test (unit):* make a code with a known canary value; search the invite row, `tabVersion`,
`tabComment`, `tabNotification Log`, `tabError Log` and the test log file for the canary;
expect none. Assert token length and that the stored value equals its hash.

**SEC-2 · The code only travels in the fragment and in POST bodies.** The link is
`https://<host>/enrol#t=<code>`. The issue, check, redeem and cancel endpoints accept POST
only. The QR image is drawn in HR's browser from the POST answer. There is no GET URL, Print
Format, PDF, stored file, email button or link shortener that carries the code. The `/enrol`
page never reads the fragment, never calls the server with it, loads nothing from other
sites, sends `noindex`, and clears the fragment from the address bar with
`history.replaceState` without reading it.
*Test (unit):* GET to each endpoint is refused. `/enrol?t=<live code>` looks nothing up
(assert no database read of invites) and the code stays live. *Test (manual, once):* open
`/enrol#t=…` in Chrome with the network panel; no request carries the code.

**SEC-3 · Checking a code uses nothing and says little.** The check call changes no state.
For a live, eligible code it returns only: first name, surname initial, designation,
company, notice rows and version, retention days, minimum app version. For a dead code it
returns only the outcome code and one time (`used_at` or `expired_at`) — no phone model, no
name. An unknown code returns one code (for example `QR_NOT_RECOGNISED`) with no values,
shown on the same "cannot be used" screen. Eligibility refusals (`NOT_FIELD_ROLE`,
`APP_OFF_FOR_FIELD`, `FEATURE_OFF`) return no name.
*Test (unit):* assert the exact key set of each answer; assert the body contains no employee
ID, full name, email, phone or date of birth for a fixture employee; call check twice and
assert the invite is still waiting.

**SEC-4 · The server decides the lifetime.** The lifetime is clamped to between 1 hour and
the organisation's setting, which is itself at most 7 days. A larger value from the browser
is refused, not silently used. Expiry is computed and checked with server time only.
*Test (unit):* ask for 30 days → refused; ask for 3 days with a 1-day setting → refused;
a code checked one second after expiry → `QR_EXPIRED`.

**SEC-5 · A code is used once, inside one locked transaction.** "Agree and finish" does, in
one transaction: lock the invite row; re-check it is waiting and not expired; re-check the
employee is `Active`, a field worker, the app is on and the plan includes field check-in;
check the notice version sent matches the current one; lock the employee's phone rows; mark
any `Active` app phone `Replaced` (D3); create the new phone `Active` with a new device
secret hash; mark the invite used with the time and the new phone; write the notice
acknowledgement; commit. Any failure rolls back everything.
*Test (unit):* two redeems of one code in parallel threads → exactly one succeeds, the other
gets `QR_USED`; a redeem that fails half-way leaves no phone row and a waiting invite; a
redeem with a stale notice version gets `NOTICE_CHANGED` and uses nothing.

**SEC-6 · One waiting code per person (D17).** Making a code cancels any waiting code for
that employee in the same locked transaction, recording "replaced by a newer code".
*Test (unit):* make two codes → first is cancelled; make two in parallel → exactly one is
waiting.

**SEC-7 · Codes can be cancelled from every place they should be.** HR cancel (desk).
"This is not me" (phone): needs the live code in a POST body, is rate limited, records
"cancelled on a phone" (D2). Employee leaves (existing leaver hook): waiting codes are
cancelled. App switched off, designation removed or plan changed: the redeem re-check
refuses (SEC-5), no bulk edit.
*Test (unit):* one test per path; after each, check and redeem return `QR_CANCELLED`.

### Security — the phone record

**SEC-8 · A block is final, for every path (D4).** The phone record's controller refuses
any status change out of `Blocked`, `Replaced` or `Removed`. This holds for the form, list
bulk edit, Data Import, `frappe.client.set_value` and the REST API — not only a hidden
button. Only server code that sets a phone to `Blocked` may bypass the controller.
*Test (unit):* for each path, as HR Manager, try `Blocked` → `Active`; expect refusal and an
unchanged row.

**SEC-9 · HR cannot forge, re-point or erase a phone record.** After insert, `employee`,
`token_hash`, "how it joined", "joined at" and the invite link cannot change. HR roles lose
**create** and **delete** on `Alvoraa Field Device` (today HR Manager has both, and HR User
has write — `alvoraa_field_device.json`, permissions block). App phones are created only by
redeem; web-page phones only by `register_device`. The existing web flow (HR sets a
`Pending` web phone to `Active`) keeps working.
*Test (unit):* as HR Manager via REST, insert a phone with a chosen `token_hash` → refused;
change `employee` on an existing phone → refused; delete → refused. Pending → Active on a
web-page phone → allowed, with `activated_by` set.

**SEC-10 · Only `Active` phones may do anything (OPS-28).** `_device_from_token`
(`field_checkin.py:103`) refuses every status except `Active`, each with its own code
(`DEVICE_BLOCKED`, `DEVICE_REPLACED`, `DEVICE_REMOVED`, `NOT_SET_UP`). Today it refuses only
`Blocked` and `Pending` (lines 120–123). The check also runs, at request time, the app-on
setting, the plan and the employee's **current** designation for app phones (D5, OPS-30).
*Test (unit):* one test per status, including any status added later (the test reads the
Select options and fails if a new one is not covered).

**SEC-11 · Secrets never leave through logs.** No code, device secret, photo, coordinates,
employee name or phone model in `frappe.log`, the Error Log, nginx logs, Redis rate-limit
keys or the app's release console. Expected refusals are coded 4xx answers, not 5xx. Every
secret request field name contains `token` or `secret`. **Depends on slice 014 (OPS-20).**
*Test (unit):* force a 5xx inside check, redeem, "not me", remove and punch with canary
values; search both logs and Redis keys for every canary; expect none.

**SEC-12 · Rate limits that match the attack.** Per code and per phone, keyed on the
**hash** (OPS-29 starting numbers). A real-IP nginx zone for the field check-in paths. A
per-site count of unknown or dead codes, with an HR alert above a threshold set after the
pilot. Frappe's own per-IP limits count only after slice 014 (OPS-19).
*Test (unit):* exceed each limit → `TOO_MANY_TRIES` with `retry_after_s`; Redis keys hold no
raw code or secret. *Test (pilot):* shared Wi-Fi with many phones is not refused.

**SEC-13 · HR is told, not left to look.** A Frappe Notification (the desk bell; email only
if HR has it on) goes out, with no code and no photo, when:

| Event | To |
|---|---|
| A code is used — employee, time, phone model | The HR person who made it |
| "This is not me" is pressed | The HR person who made it **and** HR Managers |
| A used code is scanned again from a phone that is not the one that used it | HR Managers — **a likely hijack** |
| A phone that already held one person's secret joins as a second person (SEC-14) | HR Managers |
| Unknown or dead codes above the per-site threshold (SEC-12) | HR Managers |

*Test (unit):* one test per event checks the recipient list and that the message holds no
code, secret, photo or coordinates.

**SEC-14 · The app talks to one real tenant only, and knows who it holds.**
- Release build: accepts only `https://<one label>.alvoraa.co/enrol#t=<code>`, parsed with a
  URL parser. Refuses: other schemes, user-info (`x@evil.com`), ports, extra labels,
  `alvoraa.co` itself, look-alike hosts (`alvoraa.co.evil.com`), punycode labels, a code of
  the wrong length or characters. A refusal makes **no network call** (`QR_NOT_ALVORAA`).
- Dev app ID: also `*.dev.alvoraa.co`; plain HTTP only in debug builds (OPS-7).
- The host is fixed at join. The app never follows a redirect to another host. Changing
  tenant needs "Remove this phone" first.
- When joining, the app sends its current device secret if it has one. The server marks
  that old phone `Removed` in the same transaction and raises the SEC-13 alert if it
  belonged to another person.
*Test (unit, JS):* a table of at least 15 hostile links → all refused with no fetch.
*Test (CI):* the release build's network config has no cleartext and no dev hosts.
*Test (unit):* join as B with A's secret → A's phone `Removed`, alert raised.

**SEC-15 · A code works only on the site that made it.** *Test (unit / bench):* a code made on
site A, redeemed with host B → `QR_NOT_RECOGNISED`, nothing written on either site. *Test
(local bench only, never production):* a request with a host that is no tenant is not served
by any site. **Not verified today** — see W3.

**SEC-16 · The native shell has no open doors.** No `server.url` in the release config;
`allowNavigation` empty; any other link opens the system browser; WebView debugging off in
release; `android:allowBackup="false"` plus data-extraction rules; cleartext off in release.
The bundled page carries a content policy: scripts only from the app; `connect-src` only
`https://*.alvoraa.co` (dev build: plus local); no `object-src`; no remote fonts or images.
The app loads **nothing** from the internet except the tenant API (OPS-22).
*Test (CI):* read the built `capacitor.config` and merged `AndroidManifest.xml` and fail on
any of the above; fail if the bundle contains an outside URL. *Test (device):* try to
navigate the web view to an outside page → it opens outside the app.

**SEC-17 · Server text is always drawn as text.** Every value from the server — company,
designation, names, workplace, notice rows, error values — is set with `textContent` or goes
through `esc()`. QR contents are never drawn as HTML.
*Test (unit, JS):* fixture tenant with designation `<img src=x onerror=alert(1)>` and company
`</div><script>…` → both shown literally, no script runs. *Test (CI):* a lint rule flags
`innerHTML` assignments not built from escaped values.

**SEC-18 · No CORS surprises.** Frappe's `allow_cors` is never set, on any site. Prefer
Capacitor's native HTTP. If nginx CORS is used instead: exact origins, only
`/api/method/alvoraa_portal.field_checkin.*`, no `Access-Control-Allow-Credentials`,
security headers repeated. Device endpoints trust only the body secret and ignore any
session cookie. *Test (CI):* fail if any site config or deploy file sets `allow_cors`.
*Test (unit):* a call carrying a logged-in HR session but no device secret is refused.

**SEC-19 · Old apps can be stopped.** Every call carries the app version. The server refuses
below the minimum version (`APP_TOO_OLD`) and also refuses any version on a short security
deny-list, both in one reviewed constant (OPS-27). *Test (unit):* both cases on every device
endpoint; no header (the web page) is allowed.

**SEC-20 · The app cannot quietly gain powers.** CI fails if the merged Android manifest asks
for any permission outside: `INTERNET`, `ACCESS_NETWORK_STATE`, `CAMERA`,
`ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`. So `ACCESS_BACKGROUND_LOCATION`, storage,
media, phone state, contacts and microphone need a deliberate change to that list, in review.
CI also fails on any analytics, crash or ads library in the dependency tree.
*Test (CI):* add `ACCESS_BACKGROUND_LOCATION` on a throwaway branch → build fails.

**SEC-21 · A faked position is flagged.** The app sends Android's mock-location flag with each
punch. The server stores it on the punch and HR can filter on it. Whether to **refuse** such a
punch is Q-U3. **Honest limit:** the flag comes from the phone; a script or rooted phone can
hide it. *Test (unit):* punch with the flag → stored. *Test (device):* a fake-GPS app on a
pilot phone → flag is true.

**SEC-22 · Remove this phone is real.** Needs the device secret and the internet. The server
marks the phone `Removed` (who: the employee; when). The app deletes the secret from secure
storage only after the server confirms. HR sees it. *Test (unit + device).*

**SEC-23 · Signing keys never reach the public repo (OPS-6).** Key and config patterns in
`.gitignore` and a CI secret scan exist **before the first key is created**. Play App Signing.
Two named key holders. *Test (CI):* a fake key committed on a throwaway branch fails the build.

**SEC-24 · Answers are not cached.** `Cache-Control: no-store` on every device and join
endpoint (OPS-25). *Test (unit):* header present on each.

**SEC-25 · New `ignore_permissions` uses are counted and justified.** Guest endpoints need it
for inserts; each new use carries a one-line reason. The issue, view and block paths for HR use
Frappe's normal permission check. Today `alvoraa_portal` and the Alvoraa `hrms` modules hold
**559** uses and there is no CI counter (compliance map I3). *Test (review):* the reviewer
lists every new use; the count only rises by those.

### Privacy

**PRIV-1 · Collect only what the inventory lists.** The phone sends model name (from
Capacitor `Device.getInfo()` model, trimmed), platform and app version. Nothing from the
"never collect" list in §2. The server ignores extra fields. *Test (unit):* a redeem with
extra fields (`imei`, `android_id`) stores none of them. *Test (review):* no call to
`Device.getId()` or similar in the app code.

**PRIV-2 · The new notice version (D19) is server-owned.** The notice rows and version come
from the server, never hardcoded in the app (OPS-31). The new version adds the phone model
name and says "manager" in both places. English only in the pilot; Hindi only after a
native speaker checks it (D15). Each version's text is kept and can be shown again later.
If the server starts refusing web-page phones on an old version, the web page's "read it
again" screen ships in the same deploy — or the check applies to app phones only.
*Test (unit):* change the version → next status call returns `NOTICE_CHANGED` for app phones;
an old version's text is still retrievable; web-page phones keep punching unless the web
screen exists.

**PRIV-3 · Acknowledgements are a history, not a field.** Today `consent_given_on` and
`consent_version` sit as single fields on the phone record, so a re-acknowledgement would
overwrite the first. Store each acknowledgement as a new row: version, time, language, phone,
app or web. *Test (unit):* acknowledge v1 then v2 → two rows, v1 unchanged.

**PRIV-4 · Words do not decide the legal basis before counsel does.** The tick box stays "I
have read this and I understand". No screen, store text or HR screen calls it "consent"
until Q-C1 is answered. The code may keep its field names. *Test (review):* string check on
app and desk text for "consent".

**PRIV-5 · The confirm screen shows the least.** First name, surname initial, designation,
company. No photo, no employee ID. Enforced by the server answer (SEC-3), not only by the page.

**PRIV-6 · Stop sending workplace coordinates to the phone.** `field_status` sends the
workplace latitude and longitude (`field_checkin.py:520`); neither the page nor the app uses
them (OPS-25). Remove them from the answer. *Test (unit):* answer has no coordinates.

**PRIV-7 · Photos and QR pictures stay in memory.** The photo is taken inside the page
(`getUserMedia`), held in memory, sent, dropped. Never a file, the gallery or a cache. A QR
picture chosen from photos is decoded on the phone and never uploaded or copied.
*Test (device):* after a punch and a picture join, the app's storage folders hold no image;
a network capture of the picture join shows no image upload.

**PRIV-8 · Location only at the moment of a punch.** Only "while using the app" is requested
(SEC-20 makes background location a build failure). *Test (device):* app settings show
location "only while using".

**PRIV-9 · HR screens are not a watching tool.** No "last seen", "online now" or map. The
existing `last_seen` field on the phone record is updated only by a punch
(`field_checkin.py`, `field_checkin`); relabel it "Last punch" so nobody later wires it to app
opens. *Test (unit):* opening the app (`field_status`) does not change it.

**PRIV-10 · Retention with a legal hold.** Invite records are marked "ran out", never deleted
by the daily job. Phone records and acknowledgement rows are kept while any linked attendance
record exists, then purged by a job that skips anything on legal hold. Final periods follow
Q-C3. *Test (unit):* the daily job on an expired invite changes only its status; the purge job
skips a held record.

**PRIV-11 · Counts leave the tenant, people do not.** The daily outcome and version counts
(OPS-34) hold no names, employee IDs, phone IDs or phone models. *Test (unit):* assert the
payload keys.

**PRIV-12 · The worker can see what is held, and HR can answer a request.** "What this app
records" shows the notice and the version and date agreed (in design). HR can produce, for one
employee, their phones, invite history and acknowledgements from the desk, for an access
request. **Honest gap:** there is no rights console (compliance map A8); this is a desk report,
not a workflow. *Test (unit):* the report returns only that employee's rows.

**PRIV-13 · The block reason stays with HR.** Never in any answer to the phone. *Test (unit):*
`DEVICE_BLOCKED` answer has no reason.

**PRIV-14 · Photo views keep being logged.** App punches carry the photo in the same field, so
`log_photo_view` (built) covers them. *Test (unit):* HR opens an app punch → one access row.

**PRIV-15 · Pilot people are real people.** Pilot testers get the notice, know it is a test,
and pilot photos follow the tenant's retention (or are deleted at the end of the pilot). The
iPhone test with a free Apple ID uses invented data on a non-production tenant.
*Test (release checklist):* a signed-off line before the pilot starts.

---

## 7 · Decisions for you (with my recommended defaults)

| # | Decision | My recommendation | Blocks |
|---|---|---|---|
| Q-U1 | Default code lifetime | **24 hours default, 7 days maximum.** If you keep 7 days, accept R1 by name and date | SEC-4, invite dialog |
| Q-U2 | Drop "Copy link" in step 1 | **Drop.** Keep Copy picture and Print. Bring it back with App Links | Invite dialog |
| Q-U3 | A punch with a fake-GPS flag | **Flag it in the pilot; decide "refuse" with the pilot numbers, before the first customer** | SEC-21 |
| Q-U4 | Who may make codes | **HR Manager and HR User, each only for employees Frappe lets them see.** Never line managers | SEC-9 |
| Q-U5 | Who gets the hijack alerts | **HR Managers, plus the HR person who made the code** (SEC-13 table) | SEC-13 |
| Q-U6 | Take create and delete on phone records away from HR, and freeze `employee` | **Yes.** It changes today's desk slightly; nothing live uses it | SEC-9 |
| Q-U7 | Keep phone and invite records while linked punches exist | **Yes, until counsel says otherwise** | PRIV-10 |
| Q-U8 | A short DPIA (a written privacy risk check) before the first real customer uses the app | **Yes** — employee location plus photos is the classic trigger. Not needed for the pilot with testers | First customer |
| Q-U9 | If the pilot shows real hijacks: an org setting "HR confirms each new phone" | **Do not build now.** Revisit with pilot data (brief kill criterion) | Nothing now |
| Q-U10 | Name the compliance owner | Founder to name. Several questions below wait on this person | Q-C1–Q-C4 |

---

## 8 · Questions for counsel or the compliance owner

| # | Question | What it blocks |
|---|---|---|
| Q-C1 | For photo and precise location at the moment of a punch, is the basis **consent (DPDP s.6)** or **legitimate use for employment (s.7(i))**? If consent: is it "free" when the other ways to mark attendance are limited, and does "Remove this phone" count as withdrawal? | Final notice wording; whether the tick box can stay an acknowledgement; store data-safety text. **Not the build** (PRIV-4 keeps both open). Blocks the first real customer |
| Q-C2 | Under legitimate use, what must the notice still say, and must it be offered in the worker's language (the Eighth Schedule list)? | D19 final text; when Hindi is required rather than optional |
| Q-C3 | How long must we keep (a) phone and invite records, (b) acknowledgements, (c) exact coordinates on attendance records? Can coordinates be reduced to "inside / outside" after a period? | PRIV-10 periods; a possible coordinate-reduction job |
| Q-C4 | For an app published under Alvoraa's store account that sends data to the employer's tenant, are we a Data Processor for the employer, a Fiduciary for anything (install data, store data), or both? | Store listing privacy policy; not step 1 |
| Q-C5 | (Founder) Do we have EU data subjects? | Whether a DPIA is a legal duty or good practice |
| Q-C6 | Do the IT Act SPDI Rules 2011 still treat a face photo as sensitive data where no face matching is done, now that DPDP is in force? | Wording in questionnaires; nothing in the build |

---

## 9 · What must not be blocked for the next increment (My HR)

The user plans QR sign-in to My HR next. **The step-1 verdict does not transfer.** My HR shows
payslips, bank details and leave, so a hijacked code would leak confidential data, not just
allow a wrong punch. That increment needs its own `01c`. Step 1 must keep these doors open:

1. **The phone record is the anchor.** Every future session hangs off it.
2. **One revoke function.** Blocking, replacing, removing and leaving all call one server
   function. Later it also ends the My HR session. *Test (unit):* each path calls it.
3. **The redeem answer can grow.** New fields only ever added (OPS-8), so a session can be
   added without a second QR.
4. **The invite binds an Employee, not a User.** A User can be attached later.

**What I expect the My HR design to require** (to be confirmed then, not built now):

- A shorter code lifetime for sign-in, or HR present at the handover.
- An app lock (the phone's own PIN or fingerprint) before My HR opens.
- A key made inside the phone's hardware key store that cannot be copied out, with the server
  holding only its public half — instead of a copyable secret — for anything that starts a
  session.
- My HR in a web view with **no** native bridge (OPS-3), and no cookie sharing with the
  bundled page's native HTTP.
- **A QR must never sign in a user who holds HR, System Manager or any admin role.** Refused
  by the server, not left to HR's care.
- Plan user limits and how no-email Frappe users are created (brief open question 11).

---

## 10 · Worries — things I could not turn into findings

These are not findings. I could not write "this actor, this path, sees this data" for them
without access I did not have.

| # | Worry | What would settle it |
|---|---|---|
| W1 | Frappe may or may not apply Employee user permissions to `Alvoraa Field Device` through its `employee` link. If not, an HR User limited to company A sees company B's phones | A permission test on the local bench with a restricted HR User |
| W2 | A rogue tenant could name itself like another company and invite that company's workers, collecting their photos and positions | Low today (no self sign-up for tenants that I saw). Show the host on the confirm screen as well as in Settings, if you want it closed |
| W3 | With `server_name … _` in `deploy/nginx.conf`, a request for a host that is no tenant might reach a default site. I did not read the live nginx file or the bench's site settings | A local-bench request with an unknown Host header |
| W4 | Capacitor's secure-storage plugin choice decides whether the secret is really Keystore-backed on 32-bit low-end Android | Engineer's plugin choice, checked on the three pilot phones |
| W5 | Capacitor native HTTP may keep cookies or a response cache | Engineer to check; matters more for My HR |
| W6 | Android's mock-location flag may behave differently across Xiaomi, Realme and Samsung | Pilot phones |

---

## 11 · Residual risk

**None of these is accepted yet.** An accepted risk needs a name and a date. The owner column is
my proposal.

| # | Risk after the requirements are met | Size | Proposed owner | Accepted by / date |
|---|---|---|---|---|
| R1 | An unused code that leaks lets someone join as the worker and punch until noticed. Bigger with a 7-day default | Medium with 7 days; low with 24 hours | Surbhi (lifetime decision) | — |
| R2 | Buddy punching by agreement is not prevented. Photos deter only if someone looks. No face matching, by product rule | Medium | Customer HR; Surbhi for the product rule | — |
| R3 | Position and photo are claims from the phone. A rooted phone or a script can fake them | Medium | Surbhi; revisit key attestation before store release | — |
| R4 | A lost phone with no app lock shows name, workplace and today's punches, and can punch until HR blocks it | Low (step 1); **High if carried into My HR** | Surbhi; closes with the My HR app lock | — |
| R5 | This slice depends on slice 014 (OPS-19, OPS-20). Without it, rate limits can be dodged and logs can hold photos, positions and codes | High if 014 slips | Engineer; Surbhi decides the order of pushes | — |
| R6 | The legal basis is undecided and no compliance owner is named. The notice may change again (another version) | Medium | Founder | — |
| R7 | The web check-in page is unchanged: its secret stays in `localStorage` (`field-checkin.html:469–471`) and its approval path stays | Low (no live customer) | Surbhi | — |
| R8 | The four CI gates (permission suite, cross-tenant suite, `ignore_permissions` counter, secrets-in-logs scan) do not exist. Controls here can decay without anyone seeing | Medium, growing | Security engineer with the engineer | — |
| R9 | Existing: data hosted in France; CERT-In 180-day India log residency not met | Unchanged by this slice | Founder (decided 6 Sep 2026 to stay) | Founder, 6 Sep 2026 (hosting decision) |

---

## 12 · New Frappe app checklist

**Not applicable.** This slice installs no existing Frappe app. It adds one guest page
(`/enrol`) and guest endpoints inside `alvoraa_portal`; their security answers are SEC-2, SEC-3,
SEC-12 and SEC-15. No self sign-up and no new roles are created.

---

## 13 · Verified in the code (17 Sep 2026, working copy on `dev`, HEAD `8a53522`)

| Fact | Where |
|---|---|
| Device check refuses only `Blocked` and `Pending` | `alvoraa_portal/alvoraa_portal/field_checkin.py:120–123` |
| Notice version is a code constant | `field_checkin.py:53` |
| `field_status` sends workplace latitude and longitude | `field_checkin.py:520` |
| Leaver hook blocks `Active` and `Pending` phones; does not touch codes (none exist yet) | `field_checkin.py:836–853` |
| Punch and registration rate limits are per caller IP | `field_checkin.py:136, 221, 484` |
| Phone record: HR Manager has create and delete; HR User has write; `employee` is not read-only; `track_changes` on; consent kept as two single fields | `alvoraa_portal/alvoraa_portal/alvoraa_portal/doctype/alvoraa_field_device/alvoraa_field_device.json` |
| Web page keeps the secret in `localStorage` | `www/field-checkin.html:469–471` |
| Web page escapes through `esc()` and writes `innerHTML` in four places | `www/field-checkin.html:623, 822, 871, 1066, 1080` |
| nginx appends to the caller's `X-Forwarded-For` | `deploy/nginx.conf:98` and every proxied `location` |
| No secret scan and no `ignore_permissions` counter in CI | `.github/workflows/*.yml` (grep) |
| `ignore_permissions` uses in `alvoraa_portal` and Alvoraa `hrms` modules: 559; in `field_checkin.py`: 6 | grep |

**Not verified:** the live nginx file (production wall); unknown-host behaviour; Frappe user
permissions on the phone doctype; any Capacitor plugin behaviour; any phone. Nothing was run.

---

## Sources (read 17 Sep 2026)

- [DPDP Act 2023, section 7 — legitimate uses](https://www.dpdpa.com/dpdpa2023/chapter-2/section7.html)
- [Bar & Bench — legitimate use exemption for employee data](https://www.barandbench.com/law-firms/view-point/navigating-legitimate-use-exemption-employee-data-digital-personal-data-protection-act-2023)
- [Shardul Amarchand Mangaldas — enforcement of the DPDP Act and Rules](https://www.amsshardul.com/insight/enforcement-of-the-dpdp-act-and-notification-of-the-dpdp-rules/)
- [PIB — DPDP Rules, 2025 notified](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)
- [DPDP Rules 2025 timeline summary (ProtectComply)](https://protectcomply.com/blog/dpdp-rules-2025-timeline)
- [EDPB Guidelines 05/2020 on consent](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-052020-consent-under-regulation-2016679_en)
- [GDPR Recital 51](https://gdpr-info.eu/recitals/no-51/)

---

## User decisions (Surbhi, 2026-09-17)

- **"Copy link" dropped** from HR's invite screen in step 1 (security's recommendation). Print and Copy picture stay.
- **QR lifetime:** default **24 hours**; an organisation may set up to 7 days.
- **Password manager:** **Bitwarden (free plan)**, plus an offline encrypted backup of the signing keystore.
- **Legal basis and compliance owner:** no lawyer engaged. **Interim compliance owner: Surbhi (founder).** Working position until a DPDP lawyer reviews it before the first paying customer:
  - Each **customer company is the Data Fiduciary** for its employees' data; **Alvoraa is the Data Processor**. The customer chooses and owns the legal basis.
  - The product defaults to the **employment "legitimate use" basis (DPDP s.7(i))** for attendance photo and location, with a **clear notice** (not a consent request): the tick box stays "I have read this and I understand" (PRIV-4).
  - Collection stays minimal (photo, location and time only at a punch; no background tracking; no face matching); retention is configurable; employees can see what is recorded and ask HR to correct it.
  - Before the first paying customer: a **Data Processing Agreement** template for customers, a **privacy notice** template customers can adapt, and a **one-off review by a DPDP lawyer**.

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
