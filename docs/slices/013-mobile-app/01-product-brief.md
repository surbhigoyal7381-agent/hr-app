---
slice: 013-mobile-app
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-09-17
status: draft — recommendation only; Surbhi decides at the gate
inputs: [01a-ux-opportunities.md, 07-devops-inputs.md §1, 00-sequencing-recommendation.md (incl. User decisions 2026-09-17), 008-field-checkin/10-native-app-background-geofence.md, 008-field-checkin/01-product-brief.md, 009-ess-portal-redesign/00-assessment-and-plan.md (Wave 1 decisions), .claude/context/product-context.md]
---

# 013 — Mobile app, first increment: the Attendance app for field workers

## Gate summary (for Surbhi)

1. **Build a small Android app for field workers: join by HR's QR, then photo check-in. Nothing else.** iPhone runs on one test phone only.
2. **Bad news: no customer has asked us for a store app.** The only real request is PPJ's (a demo tenant) for a phone check-in for drivers and guards. Every Kano class here is a guess (proxy).
3. **Bad news: the app cannot reach any dev tenant until the wildcard certificate is done.** Until then we test against the local bench with a debug build.
4. The app is for **field workers only** in this increment. Office and store staff keep the reception machine or the portal's Check In in a browser.
5. HR issues a single-use QR for one named employee **in the Frappe desk** (not the portal — that file belongs to line A). Lifetime is an organisation setting, default 7 days.
6. The WOW: scan HR's QR, see "Is this you? Ramesh K. · Driver · PP Jewellers", tap Yes, and be checked in within two minutes — **no "waiting for HR"**.
7. HR sees who joined, on which phone, and can block it. Blocking ends everything on that phone.
8. Built-in safety from day one: an "Update the app" screen, error codes instead of English sentences, key files blocked from the public repo, QR token kept out of server logs.
9. **Out:** My HR tab (next increment, after 009 Wave 1 is on dev), store releases, offline punches, push, auto-checkout, routes, company code, batch QR sheets.
10. **Stop rule:** if the Android test build cannot check in reliably on a low-end phone, stop the app and keep the web page.
11. Money: about ₹10,500 a year + ₹2,100 once for store accounts, test phones, and a borrowed Mac. Server run cost is close to zero.
12. Twelve open questions below, each with my recommended default. None blocks design work.

---

## 1. Job to be done

**Field employee (driver, guard):** *"When HR gives me the app on my first day, I want to set it up once and mark my attendance with a photo in a few taps, so I get paid for the days I worked without going into the store or calling HR."*

| Persona | What changes in this increment |
|---|---|
| **Employee — field worker** | Gets a real app. Joins in one scan. No waiting for HR. |
| **HR Manager** | Issues a QR from the employee record. Sees who joined on which phone. Blocks a phone in one action. |
| **CXO / company head** | Nothing visible yet. Field punches keep landing in Frappe HR beside machine punches, as today. |
| Office and store staff | **No change.** They are not in this increment. Nothing is taken away from them. |

**Harm check:** no persona loses anything. The web check-in page (`/checkin`) keeps working, as decided in N9.

## 2. Current pain — a story, not a number

We have **no measured data** and **no live customer**. The story comes from the PPJ demo (seen, 008 brief §1, 12 Sep 2026):

> PPJ's drivers and guards are not allowed into the jewellery store, where the attendance machine is. Today HR tells a driver to open `ppj.alvoraa.co/checkin`, type an employee ID and tick a notice. The screen then says "Waiting for HR" — always (`register_device`, every registration `Pending`). HR must find the phone in the desk and activate it. Then the driver must "Add to Home Screen" in three steps. Only then can they check in.

The app fixes the first-day journey. It also gives us the native shell that later steps (auto-checkout, routes) need.

## 3. Competitive analysis — whole products

Every claim is **read** on 17 Sep 2026, from vendor help pages and store listings gathered in `01a` §4. Nothing is **seen**. **I did not check pricing tiers or which plan includes the mobile app** for any competitor — `[recall — verify]` before quoting.

| Capability | Keka | Zoho People | Darwinbox | greytHR / HROne | CatalystOne / Frappe HR std | **Us, this increment** |
|---|---|---|---|---|---|---|
| Native app, one for all customers | Yes | Yes | Yes | Yes | CatalystOne `[recall — verify]`; Frappe HR: PWA at `/hrms` only | Yes, Android test build |
| Joining the company | Mobile OTP or email + password | Zoho account | Type organisation URL | greytHR: OTP; HROne `[recall — verify]` | Frappe: site login | **HR-issued, single-use QR for one person** |
| Frontline staff with no email | OTP | Kiosk app on a shared device | Needs a login | OTP | Needs a login | QR — no email, no password |
| Check-in evidence | Selfie **face-matched** every punch, geofence | Face match, geo/IP rules, **location tracking** | Face recognition, geotag, offline | Selfie with liveness, geofence, offline, WhatsApp bot | Frappe: geolocation | **Photo a human can look at**, GPS accuracy check, geofence, plain notice |
| Self-service (leave, payslips) | In the app | In the app | In the app | In the app | Frappe PWA | **Not yet** — next increment |
| Offline punch | `[recall — verify]` | `[recall — verify]` | Claimed | HROne claims | No | Not yet |

**How we sell it:** field check-in is already a paid add-on (`field_checkin` feature key, `subscription.py:175`, checked). The app is the doorway to that add-on, not a separate product.

**What we will deliberately NOT do, and why it makes us better for a driver:**

| Everyone else does | We will not | Why that is better for our user |
|---|---|---|
| Face matching on every punch | Never (product-context §6.3) | Matching fails in sunlight on cheap cameras and blames the worker. A photo is evidence a person can check. |
| General location tracking | Not in this increment; later only for named field roles, on duty, visible to the person | The person knows exactly what is recorded, and when. |
| OTP sign-in by phone number | Not now | SMS cost per login, and a number must be on file. HR already knows the person; the QR is HR vouching for them. |
| Find my company from a phone number | Never | It would tell strangers which company a number works for. |
| Captcha on login, WhatsApp-bot punches | Never | A barely literate driver should not meet "I'm not a robot". Evidence should not travel through a chat service. |
| Race to match all modules in the app | Not our game (§6.10) | We ship one job done well, then My HR on the redesigned portal. |

## 4. Kano class and demand — all proxy

| Part | Class | Evidence | What would change it |
|---|---|---|---|
| Phone check-in for field staff | **Must-be** for frontline-heavy buyers (proxy) | **Seen:** PPJ asked for it (008 brief, 12 Sep 2026). **Read:** Keka, Zoho, Darwinbox, greytHR, HROne all ship it | Built already as a web page. The app raises how well it works |
| A native app in the store | **Performance, close to Must-be** (proxy) | Read only: all Indian competitors ship one | Three of five prospects saying "no app, no deal" → Must-be |
| QR join with no HR waiting | **Attractive** (proxy) | Nobody we read joins frontline staff this way | Prospects shrug in a demo → Indifferent |
| Photo evidence with a plain notice, no face match | **Attractive** for privacy-minded buyers; **Reverse** risk for buyers who want face match (proxy) | Our security-review positioning (product-context §9) | A lost deal over "no face match" |

**No survey data exists.** To turn these into evidence, ask the next five prospect HR heads the two Kano questions for "a store app", "join by QR with no approval", and "photo without face matching".

## 5. Thin slice

**One person gets one complete outcome:** a field worker joins their company by HR's QR on a low-end Android phone and checks in and out with a photo, and HR can see and block that phone.

### In this increment

| # | Item | Why it is needed |
|---|---|---|
| S1 | **Native shell (Capacitor), Android.** Bundled `field-checkin.html`, device secret in secure storage, `BASE` address instead of relative calls, tenant name and notice facts from an endpoint | The app itself (008/10 §4b) |
| S2 | **Join screen:** scan QR with the camera, or **pick a QR picture from photos** (MA-5) | HR often sends on WhatsApp; a phone cannot scan its own screen |
| S3 | **"Is this you?"** — first name, initial, designation, company. "Yes, this is me" / "This is not me" (MA-7) | A forwarded QR joins the wrong phone |
| S4 | **One screen for a used, expired or revoked QR** — "Ask HR for a new code", no Try again (MA-6) | People think the app is broken |
| S5 | **Enrolment QR on the server:** single use, bound to one employee, stored as a hash, token in the link's `#fragment` (OPS-13), audited, revocable, expired ones cleaned daily. Redeeming it activates the device — **no Pending step** | Decided by Surbhi |
| S6 | **Organisation settings (3):** which designations are field workers; can field workers use the app (default Yes); QR lifetime (default 7 days) | Decided by Surbhi |
| S7 | **HR in the Frappe desk:** "Invite to the app" on the Employee (show QR, print, copy picture, expiry in words); revoke unused invite; the device list shows how each phone joined, when, phone name, status; **Block this phone** | Decided by Surbhi. Desk, because portal Org Settings is inside `hrms-employee.html` (line A) |
| S8 | **Photo check-in for field workers only.** QR issue and new device registration are refused for non-field designations, with a plain reason for HR | Decided by Surbhi |
| S9 | **Minimum-version check and "Update the app" screen**; the app sends its version; server errors become **codes**, not English sentences (MA-29–31, OPS-8) | Otherwise a web deploy locks drivers out on a Monday |
| S10 | **Small settings screen:** language (EN / हिं), "What this app records" (the notice rows + version agreed), "Remove this phone from {company}", app version and tenant | Privacy in the product; honest "sign out" |
| S11 | **Guards before code:** key-file patterns in `.gitignore` and a secret scan in CI (OPS-6); release build accepts only `*.alvoraa.co` hosts over HTTPS; plain HTTP in debug builds only (OPS-7); separate dev and release app IDs | Public repo; a planted QR must not point the app at another server |
| S12 | **Device-keyed rate limits** on the device endpoints, looser IP limit kept (OPS-10) | Many phones share one IP on Indian mobile networks and site Wi-Fi |
| S13 | Tiny web page at `/enrol` that **never redeems**: "Open the Alvoraa app and scan this code" | Someone scans with the phone's camera instead of the app |
| S14 | **iPhone:** the same build runs on one iPhone from a borrowed Mac with a free Apple ID (7-day limit) | Proves "in parallel" without paying for TestFlight yet |

### Deliberately out

| Out | Where it goes |
|---|---|
| **My HR tab**, one tab bar, portal Check In handing over to the app, hiding the portal's bars, payslip PDFs, app lock | **Next increment**, after 009 Wave 1 is on dev |
| QR sign-in to My HR and features like expense claims (by role, plan, permissions) | Next increment — needs its own security design |
| Store releases (Play production, App Store), store listing and privacy labels, TestFlight | After the pilot; needs D-U-N-S and org accounts |
| Offline punch queue | Later — before the first store release (strongest Apple 4.2 argument) |
| Push notifications | Later — the QR removes the "waiting for HR" wait that push was for |
| Auto-checkout (information only), route tracking for field roles, 3-month routes then daily summary, free location plugin | Steps 2–3 |
| Company code fallback (control-plane lookup) | Later, if needed. The web page's employee-ID path stays for now |
| App Links (tap a WhatsApp link to open the app) | Later — nginx files on every tenant host (OPS-11); "pick from photos" covers the case now |
| Batch QR sheet, "switch company", home-screen shortcut, manager or owner views | Later |
| Moving today's web-page users to the app | No client is live; nothing to migrate |

### Non-field staff in this increment

**The app is not for them yet.** HR cannot issue them an app QR. They mark attendance as today: the reception machine, or the portal's Check In in a browser (`hr_api.do_checkin`, GPS if the organisation requires it, no photo). They get the app with the My HR tab.

### Nothing here may block the next increment

1. **Line B never edits `www/hrms-employee.html`.** The HR screens for this increment live in the desk.
2. The shell is built so a **second tab can be added as a bridge-free web view** (OPS-3). No remote page ever gets the native bridge. In this increment the app loads **no remote pages at all**.
3. The **device record is the anchor** for any future My HR session. "Block this phone" is built as one action that will also end that session later.
4. QR redemption is designed so it can later **also** start a My HR session, without a second QR.
5. **Never switch on Frappe's `allow_cors`** (OPS-1). The engineer chooses between native HTTP (OPS-2) and a narrow nginx rule at strategy.

## 6. Persona enhancements — decided

| Persona | Idea (from `01a` §5) | Job it serves | In this slice? | Why |
|---|---|---|---|---|
| **Field employee, low-end Android** | Scan once; "Is this you?"; pick QR from photos; clear expired-QR screen | Join on day one without calling HR | **Yes** | The core outcome |
| | Language once, everywhere | Read the app in Hindi | **Yes** | Attendance is already EN / हिं |
| | QR also opens My HR, no password | See leave and payslips | Next increment | Needs Wave 1 and a security design |
| | Offline punch queue | Punch from a basement | Later | Size, plus a time-rule decision. **Honest downside: drivers without signal still cannot punch** |
| | Push "HR approved your phone" | Stop checking | No | QR removes the wait |
| | "This week" punches; home shortcut | Did yesterday save? | Later | Nice, not needed for the outcome |
| **HR admin issuing QRs** | Invite on the Employee: show, print, copy; expiry in words | Hand over the app in one action | **Yes** (desk) | Decided by Surbhi |
| | See who joined on which phone; Block this phone; revoke invite | Lost phone, wrong person | **Yes** | Decided by Surbhi |
| | Batch QR sheet; app-status column; company poster QR | Onboard 30 at once | Later | No client to roll out to yet |
| | Same screens in portal Org Settings | HR on a phone | Later, line A | Hot file |
| **Line manager / store in-charge** | Photo and place behind a team punch | Trust a punch | **Already built** (008) | Unchanged |
| | Leave push; "12 of 14 checked in" | Approve and cover | Later | Needs My HR and 009 Home |
| | Live team map, punch-time ranking, "last seen" | — | **Never** | Surveillance (§6.4) |
| **Company head** | Opens My HR, not the desk | Use the app as an employee | Next increment | No My HR tab yet |
| | Rollout count, no names | Is it working? | Later | Nothing to roll out yet |
| **Security reviewer / DPO** | "What this app records" in settings; version agreed | Privacy they can check | **Yes** | Cheap; wins the review |
| | Keys out of the repo; HTTPS-only release; QR token not in logs; no bridge for remote pages | A defensible design | **Yes** | Written in before the first key |
| | Store privacy labels match the notice | Consistent claims | With store release | No listing yet |

## 7. The WOW moment

**Screen:** the join confirmation, right after the scan.

> **Is this you?**
> Ramesh K. · Driver
> PP Jewellers
> [ **Yes, this is me** ] (large)
> This is not me

After "Yes" and the six-row notice, the Check in screen opens straight away — no waiting screen:

> **Welcome, Ramesh. This phone is set up.**
> You do not need to wait for HR.
> [ **CHECK IN** ]

And on HR's desk, seconds later, the employee's device list shows: *"Joined 9:01 am today · Redmi 12 · by QR you issued yesterday"*.

**The moment:** from HR's QR to "Checked in at 9:02 am · PPJ Noida" in under two minutes. Today that journey ends at "Waiting for HR". Hindi copy to be written by the designer.

## 8. Run-side reality (DevOps §1)

- **Server:** close to zero. One small token table, one daily clean-up job, no new container.
- **The real cost is running an app:** signing keys, a release train separate from web deploys, old versions to keep working (support each for at least 90 days, OPS-8), a Mac for iPhone.
- **Money:** about ₹10,500 a year + ₹2,100 once (store accounts), test phones at an estimated ₹8,000–15,000 each, a Mac only if none can be borrowed.
- **Build releases only from a commit on `main`** (OPS-5). Test builds come from the slice branch.
- **This does not change the size.** It does make "Update the app" and error codes musts, not polish.

## 9. How the UX gaps and DevOps red flags are handled

| Risk | Handling in this increment |
|---|---|
| **Apple 4.2** ("just a website") | No App Store submission. iPhone on one developer phone only. The 4.2 case (native tab bar, offline, push) is built before any store release |
| **Old app versions** (MA-29–31) | S9: minimum version from the server, "Update the app" screen, error codes; a test calls endpoints the way the oldest supported app does |
| **CORS** | Never Frappe's `allow_cors`. Native HTTP or a narrow nginx rule on field-checkin paths only, no credentials — engineer proposes, security confirms |
| **Native bridge and remote pages** (OPS-3) | No remote pages in this increment. Rule written now for My HR: bridge-free web view |
| **Signing keys, public repo** (OPS-6) | Ignore patterns + CI secret scan land **before** the first key exists. Play App Signing. Two named key holders |
| **Rate limits per IP** (OPS-10) | Key device endpoints on the device; measure on a shared Wi-Fi in the pilot |
| **QR token in logs** (OPS-13) | Token in `#fragment`, sent in a POST body, stored as a hash |
| **Wildcard certificate** (OPS-9) | **Dependency.** Fallback: debug build against the local bench over HTTP (debug only). If the wildcard is not done by pilot week, ask Surbhi's go-ahead to add `ppj.dev.alvoraa.co` to the current certificate |
| **Planted QR** (OPS-7) | Release build accepts only `*.alvoraa.co` over HTTPS |
| **Two check-in paths** (MA-18) | Not an issue yet — the app has one. Solved in the next increment by the hand-over |
| **Lost phone keeps My HR open** (MA-35) | Not an issue yet. Block action designed to cover it later (§5 point 3) |
| **7-day QR can be photographed** | Single use, "Is this you?", HR sees the join at once, one-tap block. Residual risk named in §11 |

## 10. Success criteria

| # | Measure | Baseline | Target | How measured |
|---|---|---|---|---|
| 1 | **Punches saved on the first tap** on low-end Android, inside the geofence with signal (lagging) | Unknown for the web page — measure it on the same phones first | ≥ 95% over 5 working days, 3 makers, ≥ 20 punches each | App sends version and outcome code; server counts codes per device. No names, no photos in the count |
| 2 | **Time from QR scan to first successful check-in** (leading) | Today: blocked on HR approval, not measured | Median ≤ 2 minutes, zero HR actions | Token redeemed-at vs first `Employee Checkin` for that device |
| 3 | **QRs used by the right person first time** (leading) | None | ≥ 9 of 10 in the pilot; count of "This is not me" and re-issues | Invite status: redeemed / revoked / expired / re-issued |
| 4 | **Blocked phone cannot punch; old app version never fails silently** (guard) | Block works today (008) | 0 punches after block; 0 unexplained errors on an older build | Automated tests; pilot with one build kept one version behind |

Not measures: installs, logins, app opens.

## 11. Thriving-workplace check and regulatory read

| Lens | One line |
|---|---|
| Engagement | A driver joins and is paid for days worked without asking anyone — agency on day one. |
| Collaboration | HR sees a join the moment it happens instead of chasing it. |
| Inclusiveness | Works with no email and no password, in Hindi, on a cheap phone. **Excludes** people with no smartphone and people with no signal (no offline yet) — they keep the reception machine or a supervisor's record. |
| Transparency | The employee can see "What this app records" at any time. Nothing new is shown to managers. |

**Regulatory read** — I am not a lawyer.
1. **Regime:** DPDP (photo, precise location at punch, device identifier) and store privacy rules later. No AI. No CERT-In change.
2. **Whose duty:** mostly the **employer's** (notice, purpose, retention). This increment helps them discharge it: the notice in the app, "What this app records", retention from their settings.
3. **What is newly possible:** a phone activates **without an HR approval step**, on a QR valid up to 7 days. New data: phone name, join time, invite audit. No new visibility for managers.
4. **Honest downside:** a photographed, unused QR lets someone else join as that employee and punch for them until HR notices. Single use, "Is this you?", the join shown to HR and one-tap block reduce it; they do not remove it. ⚠ COMPLIANCE: whether consent or "legitimate use for employment" is the basis for photo and location — **compliance owner (not yet named; founder to name)**; it blocks the store listing, not the build.

## 12. Dependencies

| Dependency | Owner | Date | Blocks |
|---|---|---|---|
| Security design of QR redemption (`01c`) | Security engineer | Next step after this gate | Build |
| Clickable prototype and design check (`01b`) | UX designer, then Surbhi | After this gate | Build |
| Key-file guard and secret scan (OPS-6) | Engineer, line B | Week 1, before any key | First build |
| Wildcard certificate — DNS and browser steps | **Surbhi** | In progress, date not known | Testing on dev tenants (fallback in §9) |
| Wildcard certificate — server steps | Engineer, **on Surbhi's go-ahead** | After DNS | Same |
| 3 low-end Android phones (3 makers) | Surbhi | Before pilot week | Success measure 1 and the stop rule |
| A Mac to borrow + free Apple ID | Surbhi | Not known | S14 only |
| Firebase project for test builds | Surbhi / engineer | Week 2 | Sending test APKs to testers |
| D-U-N-S, organisation store accounts | Surbhi | Applying now | **Store release only**, not this build |
| 009 Wave 1 on dev | Line A | Estimated 3–4 weeks | **Next increment only** |

---

## Open questions

| # | Question | Owner | My recommended default | Blocks |
|---|---|---|---|---|
| 1 | What marks a "field worker": designations, Frappe roles, or a tick on the Employee? | Surbhi | **Designations** — HR already thinks in them, and route tracking (N6) uses the same list | S6, S8 |
| 2 | If "field workers can use the app" is No, what happens? | Surbhi | HR cannot issue app QRs; field workers keep the web check-in page | S6 |
| 3 | QR lifetime range | Surbhi | Setting between 1 hour and 7 days, default 7 days | S5, S6 |
| 4 | Non-field staff who already registered a phone on the web page | Surbhi | Keep working; the desk list flags them. No client is affected | S8 |
| 5 | Where HR issues QRs in this increment | Surbhi | Frappe desk now; portal Org Settings later on line A | S7 |
| 6 | Name on the phone and in the store: "Alvoraa" or "Alvoraa HR"? | Surbhi | "Alvoraa" for test builds; decide before any store listing | Store release only |
| 7 | Offline punch queue — this increment or before store release? | Surbhi | Before the first store release, not now | Scope |
| 8 | Company code fallback | Surbhi | Out; QR only in the app | Scope |
| 9 | Crash reporting (OPS-14) in the pilot? | Surbhi, security | No — use server outcome codes; avoids a new sub-processor | Pilot diagnostics |
| 10 | How long must an old app version keep working? | Surbhi, DevOps | 90 days | S9 |
| 11 | Next increment: a QR sign-in to My HR needs a Frappe user for people with no email. Does that count toward plan user limits? | Surbhi, security | Decide before the next increment; count as employees, not paid seats | Next increment only |
| 12 | Who is the named compliance owner? | Founder | — | Store listing wording |

## Assumptions

- [ASSUMPTION] Capacitor can use the camera, precise location and secure storage on low-end Android as reliably as Chrome does for the web page. The stop rule tests this.
- [ASSUMPTION] Field workers in target tenants have their own smartphone, not a shared one.
- [ASSUMPTION] HR commonly sends onboarding material on WhatsApp, so "pick QR from photos" matters.
- [ASSUMPTION] Designations are set correctly on Employee records in a tenant.
- [ASSUMPTION] 009 Wave 1 lands on dev in about 3–4 weeks.
- [ASSUMPTION] All competitor claims are vendor pages, read not seen; none checked for pricing tier.

## Kill criteria

- **If the Android test build cannot check in reliably on a low-end phone** (below 90% first-tap saves after one round of fixes, on any of the three makers), **stop the app work.** Keep the web page and move line B to 009 Wave 0 fixes.
- If the security design cannot make a 7-day single-use QR safe enough to skip HR approval, **drop the no-approval part**: the QR sets the tenant and person, and HR still approves.
- If Capacitor's camera or location on the test phones is worse than the same phone's Chrome, stop and keep the web page.

## Handoff note

To the UX designer and security engineer: the thin slice is **field workers, Attendance, QR join, desk HR screens** — nothing that touches `hrms-employee.html`. The designer should prototype the join, "Is this you?", expired-QR, update-the-app and settings screens, and the desk invite and device list; not a tab bar. Security: the 7-day QR that skips HR approval is the riskiest decision in this brief — challenge it, and propose the smallest control that makes it defensible. Watch §5 "Nothing here may block the next increment": the block action and QR redemption must be shaped for a My HR session later. I mildly disagree with applying the 7-day default without a lower minimum; question 3 asks for it.

---

## Gate decision (2026-09-17)

**Build.** The user approved the brief. No change was asked to the open questions, so the product manager's recommended defaults apply (tell the user if any turns out to matter more than it looked):

1. A field worker is marked by **Designation**, set per organisation.
2. If "field workers can use the app" is **No**, HR cannot issue app QRs; field workers keep the web check-in page.
3. QR lifetime: an organisation setting from **1 hour to 7 days, default 7 days**; security to challenge the no-HR-approval case.
4. HR issues QRs **in the desk now**; in portal Org Settings later, on line A after slice 009 Wave 1.
5. Offline punches: **later**, before the first store release.
6. Crash reporting in the pilot: **no** third-party tool; use server error counts.
7. Old app versions keep working for **90 days**.

Still open for later increments: user accounts for field workers without email (and plan user limits); a named compliance owner before the store listing.
