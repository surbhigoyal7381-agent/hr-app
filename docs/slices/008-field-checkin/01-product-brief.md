# 008 — Field Check-in — product brief

**Status:** scope fixed by Surbhi, 12 Sep 2026. **Deadline: a working demo to
PP Jewellers within 12 hours of 12 Sep 2026.**
**Customer:** PP Jewellers (PPJ), demo on `ppj.dev.alvoraa.co`.
**Priority is fixed by the user and is not for any agent to re-open.** Anything
not in §3 goes to §6, the backlog.

---

## 1. The problem, in the customer's words

PPJ's attendance machine sits at the **reception of the store**, and it covers
internal employees. It does not cover **field workers — drivers, guards and
similar — who are not allowed into the jewellery store to mark attendance.**

They need a phone app for those people. Every field employee will have it on
their phone. At install they are given the **server address and their employee
ID**, entered once and saved. After that: **take a photo, press Check In, and
attendance is marked for that day.** It must show **what time the punch was
made** and **record where the person was**.

A second need, for internal employees: check the person is **at the office** when
they punch, with the allowed **distance configurable**, down to Frappe's own
minimum.

## 2. Who it is for

| Persona | What changes |
|---|---|
| **Field employee** (driver, guard) — low-end Android, often Hindi or Punjabi, may have no email | Can mark attendance at all, for the first time. Two taps. |
| **Internal employee** | Punch from the phone is checked against the branch location |
| **HR Manager** | Sees field and machine punches in one place; sets the radius and the deduction rule; approves a second phone |
| **Line manager / supervisor** | Can see the photo and place behind a punch |
| **CXO** | Field staff attendance stops being paper |

## 3. In scope — phase 1, the demo

Fixed by the user. Build in this order.

| # | Item | Note |
|---|---|---|
| P1 | **PWA installed to the home screen.** Android is the priority; **iPhone must work too** (Safari → Share → Add to Home Screen) | Not a native app — see §5 |
| P2 | **One-time setup:** server URL + employee ID, saved permanently | Plus a device secret — see §4 |
| P3 | **Photo + Check In** → `Employee Checkin` in Frappe HR | Photo is **evidence**, not matched — see §4 |
| P4 | **Check Out**, and today's punches **with times** on screen | |
| P5 | **Geolocation recorded on every punch**, with the phone's accuracy reading | |
| P6 | **Geofence at punch time**, using Frappe HR's existing `Shift Location.checkin_radius`. Message names the real distance: "You are 140 m from PPJ Noida" | Frappe HR already enforces this — do not rebuild it |
| P7 | **Radius configurable in Org Settings** of the ESS app. Floor is **Frappe's own minimum (1 m)**; warn below 50 m because phone GPS is only good to 10–20 m | User asked for Frappe's minimum to be the limit; the warning is advisory only |
| ~~P8~~ | ~~Deduction rule editable in Org Settings~~ | **DROPPED by Surbhi, 12 Sep 2026.** `Attendance Deduction Rule` already has 21 controls in the desk; surfacing them is not worth demo hours. Moved to §6. |
| P9 | **Sold as an add-on to core HR.** New feature key in `subscription.py`; `sync_registry()` then lists it on the tenant admin page for pricing | Costing is set on the admin page, not in code |
| P10 | Punches visible **in the app and in Frappe HR** (`Employee Checkin` list) | |
| P11 | Offline queue — punch with no signal, send on reconnect | **First thing to drop if the clock runs out** |
| P12 | **Geofence exemption by designation.** Some roles have no fixed workplace — a driver is *supposed* to be away. HR sets which designations are exempt, in Org Settings. | Added by Surbhi, 12 Sep 2026, replacing P8 |

## 3a. This is a product, not a PPJ build

Stated by Surbhi, 12 Sep 2026: the feature must serve **any** customer, not only
PP Jewellers. That is a constraint on every agent and every file.

- No customer name, branch, company, designation or URL in any shipped file.
  Checked and cleaned on 12 Sep: a hardcoded `ppj.dev.alvoraa.co` and a sample
  branch name were removed from the phone app.
- Everything a customer differs on is **configuration they own**: the radius per
  Shift Location, the exempt designations, whether the feature is bought at all.
- Sold per tenant through the `field_checkin` key, priced on the admin console.
- Reads only standard doctypes — Employee, Designation, Shift Assignment, Shift
  Location, Employee Checkin. Nothing assumes PPJ's six branches or its shifts.

## 4. Decisions already taken

- **No face matching in phase 1.** The user's flow is photo → Check In → marked.
  The photo is evidence a supervisor can look at. On-device matching is §6.
- **Device token, not employee ID alone.** Field staff have no login, so the
  phone registers once and keeps a secret; only its SHA-256 is stored. An
  employee ID on its own cannot punch.
- **Photos are private files.** Never `/public/files`, never in a log.
- **A vague GPS fix is refused**, not silently trusted.
- **Every phone waits for HR.** An earlier design trusted the first phone to
  register for an employee. That is backwards: on somebody's first day nobody
  has registered, so an attacker only had to be first. Corrected 12 Sep 2026
  after the security review.
- **Frappe-first.** `Employee Checkin` already has `latitude`, `longitude`,
  `geolocation`; `Shift Location` already has `checkin_radius` and
  `Employee Checkin.validate_distance_from_shift_location` already enforces it.
  We add three custom fields and nothing else.

## 5. Rejected, with the reason

- **Face App** (`Momscode-Technologies/face_app`) — **rejected.** Three pre-auth
  holes: a guest `login()` that trusts a caller-supplied site URL and then
  returns the user's decrypted `api_secret`; a guest `sign_up()` that creates a
  System User with the **HR User** role; SQL built by string formatting. It also
  needs `dlib` (will not build on our Python 3.14), targets Frappe v13/v14
  against our v16, and **contains no mobile app at all**.
- **Background location tracking with a 10-minute auto-checkout** — **not
  possible in a PWA.** A web page stops running when the screen locks; iOS has no
  background location for web apps. Needs a native app plus Google's background
  location review. → §6.

## 6. Backlog — explicitly out of phase 1

| Item | Why it is not now | Rough size |
|---|---|---|
| **On-device face matching** | 6 MB model download and tuning; would risk the demo | M |
| **Background location + 10-min auto-checkout** | Needs a native app; Play Store background-location approval takes days to weeks | L (4–6 weeks) |
| **Native Android / iOS apps** | Only needed for background location and push | L |
| **"Stepping out" / "Back" buttons** | The non-surveillance way to get the same outcome as auto-checkout | S |
| **Exceptions list for HR** — still checked in, last seen outside the branch | Needs the above | M |
| Hindi and Punjabi on the field app | Field staff are often Hindi/Punjabi first | S |
| Push notification "you forgot to check out" | | S |
| Supervisor view of photos with a bulk "looks right" action | | M |
| Retention job: delete check-in photos after N days | **Raise with the user — it is a DPDP obligation, not a nicety** | S |
| Deduction rule surfaced in Org Settings (was P8) | Dropped 12 Sep to protect the demo. The rule already works from the desk. | S |
| HR-issued one-time enrolment code instead of HR approving each phone | Better setup experience than waiting for approval, but half a day | M |

## 7. Success

- A driver with no email installs it, sets it up once, and punches in under
  **two minutes on a 360 px Android**.
- The punch appears in Frappe HR beside reception-machine punches.
- HR changes the radius in Org Settings and the next punch obeys it.
- Nothing in phase 1 tracks anybody between punches.

## 8. Constraints every agent must respect

- `CLAUDE.md` §1 — local → dev → main, **each step on the user's explicit word**.
  Nothing deploys in this slice without her saying so.
- `CLAUDE.md` §3 — production is untouchable.
- `CLAUDE.md` §6 — plain English, in documents and on screen.
- **Time-box: the demo is in 12 hours.** Prefer a short, correct answer over a
  complete one. If something cannot be done well in the time, put it in §6 and
  say so, rather than half-building it.
- Work already done by the session, to review rather than redo:
  `alvoraa_portal/alvoraa_portal/field_checkin.py` and the
  `Alvoraa Field Device` doctype.
