# 008 — Field Check-in — security & privacy requirements

**Author:** security & privacy engineer · **Date:** 12 Sep 2026
**Scope is fixed by the user (see `01-product-brief.md` §3) and is not re-opened here.**
**Time-box:** demo in 12 hours. Everything below is either *demo-blocking* or *tagged for
the §6 backlog with a reason*. Nothing is listed just because it would be nice.

**I am not a lawyer.** Legal points below are engineering requirements derived from
`.claude/context/security-compliance-baseline.md` (last verified 24 Aug 2026, so it is
current under the 90-day rule). Anything that turns on a point of law is marked
⚠ DECISION or sits in §8, "questions for counsel".

---

## 1 · Threat model, in four lines

1. **Who wants this data, and what is the cheapest way to get it?**
   Not an outsider. The cheapest attack is a colleague, or a competitor's runner, who
   knows one thing: employee IDs look like `HR-EMP-00042`. With an enumerable ID and a
   public registration endpoint, they get a working attendance identity for somebody
   else. Second cheapest: a curious colleague browsing the Employee Checkin list and
   reading everybody's face photo and GPS pin.
2. **Blast radius of one mistake.**
   One employee for a hijacked punch. **Every employee on the site** for the photo and
   location store, because `Employee Checkin` is one list with one permission model.
   Cross-tenant is bounded by one-site-per-tenant — verify that, do not assume it.
3. **What does this make possible that was impossible before?**
   New collection of two things we have never held: a **face image** and a **precise
   location**, both tied to a named person and a timestamp, both created by an
   **unauthenticated** caller. That is a first for this product.
4. **How would we find out?**
   Today, we would not. There is no alert on a device registration, no link from a punch
   to the device that made it, and no photo-access log. Detection is the gap, not
   prevention.

---

## 2 · Data inventory

| Field / object | Sensitivity | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| Face photo at punch (`Employee Checkin.alvoraa_checkin_photo`, private File) | **High.** Image of a person's face. Not biometric *processing* while we do no matching — see §8 Q1 | Prove the punch was made by the person, not a friend holding their phone | ⚠ DECISION — proposed 90 days, then purge | Employee (own), HR, that employee's own line manager |
| Latitude / longitude / accuracy on the punch | **High.** Precise location of a named person at a known minute | Confirm the punch was made at the work location | Same as the attendance record — ⚠ §8 Q2 | Employee (own), HR, own line manager |
| `Alvoraa Field Device.last_latitude` / `last_longitude` | **High**, and a *second copy* with different permissions | None the punch record does not already serve | Should not exist — see PRIV-4 | HR only |
| Device token (plaintext) | **Secret.** Equivalent to a password | Authenticate the phone | Never stored server-side; on the phone only | Nobody |
| `token_hash` | Secret-derived | Look up the device | Life of the device | Nobody — hidden field, never returned by an API |
| Employee ID + name at registration | Medium (identifying) | Bind the phone to a person | Life of the device | HR |
| Device label / platform string | Low | Help HR tell two phones apart | Life of the device | HR |
| `captured_at`, offline flag | Low | Tell a stored-and-forwarded punch from a live one | With the punch | HR, own line manager |

**Everything in this table is personal data under the DPDP Act 2023.** The Act has no
special "sensitive" category the way GDPR does. But the *harm* from a face photo and a
GPS pin is higher than from a punch time, so we treat them as High regardless.

---

## 3 · Access intent — including who must NOT see what

| Actor | Punch time | Location | Photo | Device record |
|---|---|---|---|---|
| The employee themselves | Yes | Yes | Yes | Their own, read only |
| **Line manager of that employee** | Yes | Yes | Yes | No |
| **Any other manager / any colleague** | **No** | **No** | **No** | **No** |
| HR User / HR Manager | Yes | Yes | Yes | Yes |
| System Manager | Yes | Yes | Yes | Yes (needed to operate; should be logged) |
| Guest / the field app | Only the punches of the one device asking | No read path | No read path | No |

**The one that matters:** a colleague must not be able to open the `Employee Checkin`
list and page through other people's faces and locations. Today that depends entirely on
whether a `User Permission` row for `Employee` exists for each ESS user, because the
`Employee` role has plain `read` on `Employee Checkin` and **no permission query
condition is registered for it** in either `hrms/hooks.py` or
`alvoraa_portal/hooks.py`. See SEC-14 — prove this on the demo site.

---

## 4 · Obligations engaged

Source: `.claude/context/security-compliance-baseline.md`, verified 24 Aug 2026.

| Obligation | Regime | Legal duty or good practice? | What it forces here |
|---|---|---|---|
| Notice, itemised, in a language the person reads | DPDP s.5 | **Legal** (phased; fiduciary duties bite around May 2027) | PRIV-2. Hindi/Punjabi is backlog; an English notice at registration is not optional |
| Lawful basis — consent vs "legitimate use" for employment | DPDP s.4, s.7 | **Legal** | §8 Q3. The screen design differs depending on the answer |
| Purpose limitation | DPDP s.6(1), s.8(3) | **Legal** | PRIV-12 — location collected for geofencing must not quietly become a movement report |
| Data minimisation and erasure once the purpose is served | DPDP s.8(7) | **Legal** | PRIV-3, PRIV-4. **Photo retention is the clearest legal gap in this slice** |
| Reasonable security safeguards | DPDP s.8(5) | **Legal** | Every SEC item |
| Breach: intimate affected people and the Board, detailed report in 72 h | DPDP s.8(6) | **Legal** | A hijacked device is a reportable breach. SEC-12 and PRIV-9 are what make "who was affected" answerable |
| Incident report to CERT-In within **6 hours** of awareness | CERT-In 2022 | **Legal** | Same event. The 6-hour clock is the binding one |
| Grievance route | DPDP s.13 | **Legal** | Out of slice — an existing product-level gap |
| Photo not used to uniquely identify a person | GDPR Art 4(14) framing | Good practice here; **legal if GDPR applies** | PRIV-11 — keep "no face matching" structural, not a promise |
| No secrets in URLs or logs; rate limiting; fail closed | OWASP ASVS 5.0 | Good practice, and what a security reviewer tests | SEC-3, SEC-4, SEC-8 |

---

## 5 · Abuse cases

| # | Actor and situation | What they try |
|---|---|---|
| A1 | Anyone on the open internet, no account | Walks `HR-EMP-00001…00500` at the registration endpoint to learn who works at PPJ, and their names |
| A2 | Same person | Registers the **first** phone for an employee who has not installed the app yet, gets an **Active** token, and punches as them — or simply locks the real employee out, because their later registration lands in Pending |
| A3 | A driver | Hands the phone to a friend, or replays yesterday's photo with a spoofed GPS, to be marked present from home |
| A4 | A curious colleague with an ESS login | Opens the Employee Checkin list or report view and reads everybody's photos and coordinates |
| A5 | An over-scoped line manager | Looks at the location of people who do not report to them |
| A6 | A departing employee | Keeps the token on their phone after the last day and keeps punching |
| A7 | Anyone with a script | Floods the punch endpoint with 2 MB photos until the disk fills, or floods registrations until the device table is unusable |
| A8 | A support engineer | Opens a face photo from `/private/files` with no record that they did |

---

## 6 · Requirements

Each says what must be true and how it is tested. The analyst traces every one to an
acceptance criterion. **Blocking** = must hold before the demo. **Phase 1.1** = must hold
before any real employee data is loaded. **§6** = goes to the brief's backlog, with the
reason given.

### Security

| # | Requirement | Priority | How it is tested |
|---|---|---|---|
| **SEC-1** | Registration alone must never produce a usable token. Either (a) **every** device registers as `Pending` and an HR person activates it, or (b) registration needs an **HR-issued enrolment code**, single-use, with an expiry. ⚠ **DECISION — D1 below** | **Blocking** | Register a fresh employee ID from a clean client; assert `status == "Pending"` and that no token comes back; assert a punch fails until HR activates |
| **SEC-2** | The registration response, and its error, must be **the same shape and content** whether the ID exists, has left, or was never real. No `employee_name`, no designation, no company in a guest response | **Blocking** | Call with a valid ID, an inactive ID and `HR-EMP-99999`; assert the three bodies are indistinguishable and contain no name |
| **SEC-3** | Rate limiting must be keyed on something the **attacker does not control**. `key="employee_id"` gives every guessed ID a fresh bucket, so it limits nothing. Needed: a per-IP limit on registration **and** a site-wide ceiling per hour that alerts HR when crossed | **Blocking** | Loop 100 distinct IDs from one IP; assert refusal long before 100. Assert the site-wide counter raises an alert |
| **SEC-4** | All three endpoints accept **POST only** (`@frappe.whitelist(allow_guest=True, methods=["POST"])`). A token, an employee ID, a photo or a coordinate must never be able to travel in a query string, where nginx writes it to an access log | **Blocking** | `GET /api/method/...?token=x` returns 405; grep the nginx access log after a full punch and assert no token and no coordinate appear |
| **SEC-5** | The device token is at least 128 bits of CSPRNG randomness, returned exactly once, stored only as a hash, and **never appears in a URL, a log line, an error message, a cache key or a rate-limit key**. Setting a device to `Blocked` takes effect on the very next call | **Blocking** | Unit test on entropy and one-shot return; block a device mid-session and assert the next punch fails; assert no Redis key contains a token |
| **SEC-6** | The punch and status endpoints are rate limited, per device and per IP. Today they have **no limit at all** | **Blocking** | 50 punches in a minute from one token; assert refusal, and that 50 files were not written |
| **SEC-7** | Photo: reject on **encoded length before decoding**; enforce 2 MB; check the decoded bytes really start with a JPEG or PNG magic number; always `is_private=1`. A non-image is refused, not stored | **Blocking** | Post a 50 MB base64 string — assert refusal with no memory spike. Post a ZIP — assert refusal. Assert the stored path starts `/private/files` |
| **SEC-8** | No personal data reaches any log: not the photo bytes, the token, the coordinates, the employee ID or the employee name — in no `Error Log` row, no `frappe.log_error` call, no traceback, no nginx log. **Including Frappe's own unhandled-exception logging**, which can capture the request body | **Blocking** | Force a failure inside the punch (break the shift setup) and assert the resulting `Error Log` row contains none of the five. Run the PII-in-logs scanner over the module |
| **SEC-9** | Replay: two punches from the same device with the same `log_type` within 60 seconds are refused as a duplicate. `captured_at` is validated as a real timestamp inside a bounded window (say 24 h) and is **stored** — today it is read and thrown away, so the "offline" flag can be set by anyone and means nothing | Blocking (dedupe) · Phase 1.1 (window) | Send the same payload twice; assert one punch. Send `captured_at` of 2019; assert refusal |
| **SEC-10** | The employee lookup at registration is scoped to the tenant's own company set and cannot resolve an employee outside it | **Blocking** (assert only) | With two companies on one site, register company B's ID through company A's app; assert refusal. If the site really is single-tenant, write the assertion anyway, so it fails the day that stops being true |
| **SEC-11** | The guest endpoints may write exactly three things: one `Employee Checkin`, one private `File` attached to it, and one `Alvoraa Field Device` row or its activity fields. Nothing else, ever — and never a `User`, a `Role` or a permission | **Blocking** | Code review plus a test asserting the set of doctypes touched in one call. This is the `face_app` mistake, written as a test |
| **SEC-12** | Every punch records **which device** made it — a link field to `Alvoraa Field Device`, not just `device_id = "alvoraa-field-app"`. Without it, "which phone punched for this person on 3 March" cannot be answered, and a breach cannot be scoped | **Blocking** — one custom field | Punch, then assert the checkin's device link resolves to the registering device |
| **SEC-13** | `token_hash` is never returned by any API, report or export | Blocking | Call `frappe.client.get_list` on the device doctype as HR User and assert the field is absent |
| **SEC-14** | A user holding only the `Employee` role can read **their own** check-ins and nobody else's — in the list view, the report view, the API, and the private-file route | **Blocking, and it is a verification, not a build.** If the `User Permission` on `Employee` is missing, add a `permission_query_conditions` entry for `Employee Checkin` | As an ESS user, list `Employee Checkin` unfiltered and assert only own rows; fetch a colleague's photo URL directly and assert 403 |
| **SEC-15** | Registration and activation are **noticed**: HR is alerted on every new registration and every `Pending`. ⚠ Alerting the **employee** needs an email or phone number a field worker may not have — §8 Q4 | Blocking (HR side) | Register; assert a notification exists |

### Privacy

| # | Requirement | Priority | How it is tested |
|---|---|---|---|
| **PRIV-1** | Every new field carries a sensitivity class and a purpose tag as in §2. A field with no class inherits the loosest handling in the system | Phase 1.1 | Field list diffed against §2; CI fails on an unclassified new field |
| **PRIV-2** | Before the first registration completes, the phone shows a **plain-language notice**: what is collected (face photo, location), why, who can see it, how long it is kept, and who to complain to. The version and timestamp are stored on the device record | **Blocking.** The screen and the stored version are a morning's work; translations are §6 | Register; assert `notice_version` and `notice_accepted_on` are set; assert the punch endpoint refuses a device with no recorded notice |
| **PRIV-3** | **Photos are deleted after N days** by a scheduled job, with a legal-hold flag that stops deletion while a disciplinary or grievance case cites the punch. ⚠ **DECISION — D2.** Proposed: 90 days | **Phase 1.1 — before real employees are enrolled, not before the demo.** Say that to PPJ out loud | Age a photo past N days, run the job, assert the File is gone and the punch survives. Set legal hold, re-run, assert the photo survives |
| **PRIV-4** | `last_latitude` / `last_longitude` on the device record are **removed**. They are a second copy of location data, on a record with different permissions and no retention rule, serving no purpose the punch does not serve. Keep `last_seen` | **Blocking** — deleting two fields is cheaper than governing them | Assert the fields are gone from the doctype and no code writes them |
| **PRIV-5** | Location is collected **at the moment of a punch and at no other time**. The app must not request background location, must not poll, and must not hold a watch handle between punches | **Blocking** | Review the PWA for `watchPosition`; assert only `getCurrentPosition` on a button press. State it in the notice |
| **PRIV-6** | A line manager sees the photo and location **only for their own reports**. Any wider view is HR-only | **Blocking** | As a manager, open a punch for somebody outside the team; assert 403 |
| **PRIV-7** | The employee can see their own punches, times, locations and photos in the app | Blocking (already P4) | Covered by the functional tests |
| **PRIV-8** | When an employee stops being `Active`, their devices move to `Blocked` automatically. Today the punch is refused but the token stays live, waiting for a rehire | Blocking | Set an employee to Left; assert the device is Blocked and the next call fails on the device, not the employee |
| **PRIV-9** | The audit trail can reconstruct a punch a year later, in the only situation anyone reads it — a grievance about a deduction. It must answer: which device, which employee, server time, phone-claimed time, coordinates, accuracy, whether a geofence refusal came first, and, for a `Pending` device turned on, **who activated it and when** | **Blocking.** `track_changes` and `activated_by` cover half; SEC-12 covers the rest | Reconstruct one punch end to end from stored data alone |
| **PRIV-10** | Reading a check-in **photo** is recorded: who looked, at which punch, when. A face photo anyone in HR can open with no trace is abuse case A8 | **§6 backlog** — needs a hook on the private-file route, not a 12-hour job. Name it to the customer as a known gap | — |
| **PRIV-11** | No face matching, structurally: no embedding computed, no image leaves the site, no photo sent to any model or third party. A property of the code, not an instruction | **Blocking** (true today — keep it true) | Grep the module for outbound HTTP or model calls; assert none, and add a CI rule that fails if one appears |
| **PRIV-12** | Location is used for the geofence decision and the punch record, and nothing else. It feeds no analytics, no movement report, and no export that was not authorised here | Blocking (assert) | Grep for readers of `latitude`/`longitude` on `Employee Checkin`; assert the set is the geofence and the punch view only |

---

## 7 · ⚠ Decisions the user must take

| # | Decision | What it blocks | Recommendation |
|---|---|---|---|
| **D1** | SEC-1: every device `Pending` with HR activating, **or** an HR-issued enrolment code | The demo script, and whether today's code is safe to show anyone | For a 12-hour demo: **all devices Pending**. Roughly five lines and one list-view click. It closes the hijack completely; the enrolment code can follow |
| **D2** | PRIV-3: how many days a check-in photo is kept | Nothing in the demo; everything after real data | 90 days, with legal hold |
| **D3** | Is the demo tenant loaded with **real PP Jewellers employees** or seed data? | If real, PRIV-2 and PRIV-3 stop being Phase 1.1 and become blocking today | Demo on seed data |
| **D4** | Do we tell PPJ in writing that photo retention and photo-access logging are not built yet? | Trust, and the security review they will run later | Yes, in the demo follow-up note. It costs nothing now and a lot later |

---

## 8 · Questions for counsel

| # | Question | What it blocks |
|---|---|---|
| **Q1** | Is a stored face photo used purely as visual evidence — never matched, no template computed — "biometric information" under the SPDI Rules 2011, and does DPDP change that answer? | Whether the photo needs SPDI-grade handling on top of what is here. My reading is that without matching it is not biometric *processing* — that is a reading, not advice |
| **Q2** | What is the minimum retention for attendance records under the relevant state's Shops & Establishments Act and any wage-register rule, and does that floor cover the photo and coordinates or only the punch? | The numbers in PRIV-3 and PRIV-4 |
| **Q3** | For location and photo capture, is our customer relying on **consent** or on DPDP's "legitimate uses" for employment? Consent must be withdrawable as easily as it is given — and an employee who withdraws then cannot mark attendance at all | The registration screen. A consent flow with no working withdrawal path is worse than none |
| **Q4** | Must notice reach the **employee** directly, when many field workers have no email and perhaps no personal phone? Is an on-screen notice on the device they hold enough? | PRIV-2 and SEC-15 |
| **Q5** | If a device token is hijacked and false attendance recorded, is that a reportable breach under DPDP s.8(6) and a CERT-In "unauthorised access" category? | The incident runbook, and whether the 6-hour clock starts |

---

## 9 · To the brief's §6 backlog, with reasons

| Item | Why not now |
|---|---|
| Photo access log (PRIV-10) | Needs a hook on the private-file route; not a 12-hour job |
| Hindi and Punjabi privacy notice | Translation, not engineering — but it is a DPDP expectation, so weeks away, not quarters |
| HR-issued single-use enrolment codes (the better half of SEC-1) | Half a day; Pending-by-default closes the same hole today |
| Device self-revoke from the phone ("this is not my phone") | S |
| A record of a geofence **refusal** — today a refused punch leaves no trace, so "he says he was there" has no evidence either way | M |
| Breach drill for a hijacked device | Must happen before this reaches real employees at scale. A runbook nobody has exercised is a document, not a capability |

---

## 10 · Residual risk

| Risk | Who accepts it | Date |
|---|---|---|
| A phone with a valid token can still be handed to somebody else, and phase 1 does no face matching. The photo is the only deterrent, and nobody reviews photos in bulk | Surbhi — to confirm | 12 Sep 2026 |
| GPS can be spoofed with a mock-location app on Android. We record accuracy, not authenticity | Surbhi — to confirm | 12 Sep 2026 |
| Photo retention and photo-access logging are not in phase 1 | Surbhi — to confirm | 12 Sep 2026 |
| Logs live in France, not India — the CERT-In 180-day residency gap (baseline §3a) | Already accepted 6 Sep 2026 | 6 Sep 2026 |

An accepted risk with a name and a date is governance. Unnamed, it is an accident
waiting for an owner — so the first three need a name before this feature meets real
staff.
