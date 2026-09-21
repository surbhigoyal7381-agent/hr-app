---
slice: 013-mobile-app
artifact: 01a-ux-opportunities
author: hrms-ux-designer
date: 2026-09-17
status: draft
inputs: [docs/slices/008-field-checkin/10-native-app-background-geofence.md, docs/slices/008-field-checkin/09-wildcard-certificate.md, docs/slices/008-field-checkin/01-product-brief.md, docs/slices/008-field-checkin/01b-ux-design.md, docs/slices/008-field-checkin/07-devops-inputs.md, docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md, docs/slices/009-ess-portal-redesign/appendix-a-frame.md, docs/slices/003-ess-mobile-responsive/00-current-state-assessment.md, .claude/context/product-context.md, .claude/context/nfr-budget.md, .claude/context/ux-learnings.md, alvoraa_portal/www/field-checkin.html, alvoraa_portal/field_checkin.py, alvoraa_portal/www/alvoraa-login.html, alvoraa_portal/www/alvoraa_login.py, alvoraa_portal/hr_api.py (do_checkin)]
---

# 013 — Mobile app (step 1): UX opportunities scan

**Mode:** opportunities scan. No prototype. The product manager decides what goes in the slice.
**Step 1 only:** a Capacitor app with two tabs — **Attendance** (bundled field check-in) and
**My HR** (the ESS portal, loaded from the tenant's site). No background location.

---

## 0. The short answer

**Bad news first.**

1. **The people this app is mainly for may not be able to open My HR at all.** The field
   check-in exists *because* drivers and guards have no email and no password
   (`field_checkin.py`, top of file; 008 brief line 31). The My HR tab signs in with
   **"Email / Username" and "Password"** (`alvoraa-login.html:435`). So the question is not
   "does the employee log in twice?" It is "**does the frontline employee have a login at
   all?**" I could not count how many PPJ employees have a user account: the bench was
   off limits for this run. **⚠ DECISION Q1.**
2. **Inside one app there would be two Check In buttons with different rules.** The portal's
   Home has its own Check In (`hrms-employee.html:2468` → `hr_api.do_checkin`): no photo, no
   GPS accuracy check, `device_id = web-portal`. The Attendance tab takes a photo and refuses a
   vague GPS fix. The evidence behind a punch would depend on which tab someone tapped.
3. **An installed app cannot be "closed and reopened" into a newer version.** The server
   refuses a setup when the page's notice version differs (`field_checkin.py:170-176`), and
   the page matches server errors **by their English sentence** (008 01b §6). A web page
   picks up a fix on reload. A store app keeps the old bundled page until the person updates.
   Without an "update the app" screen, a server change can lock drivers out.
4. **The portal is not phone-ready until slice 009 Wave 1 ships.** The 11 Sep audit found four
   tasks that cannot be finished on a phone and 22 layout gaps (003, M01–M22). Inside the app it
   gets worse: the portal's own bottom bar (Home · Attendance · Finances) would sit on top of
   the app's tab bar — **two bottom bars, and "Attendance" meaning two different things.**
5. **QR enrolment is designed but not built.** Today every phone registers with an employee ID
   and **always waits for HR approval** (`register_device`, every registration `Pending`).
   "Waiting for HR" is the normal first-day experience today, not an edge case.

**The good news.** The hardest part — a one-tap, photo-and-place check-in that a barely
literate driver can use, with a plain consent notice and twelve honest error screens — is
built, tested on a real phone and demoed. Step 1 is mostly about **the doorway into it**:
joining a company, signing in once, and what happens when things change.

**My recommendation to the PM, in one line:** make step 1 "**one sign-in, one check-in, one
bottom bar**" — the QR joins the company *and* opens My HR; My HR's Check In hands over to the
Attendance tab; the portal's own bars are hidden inside the app.

---

## 1. Frame

**Who, when, where, what:** a driver, guard or store employee, on the day HR hands them the app,
on a ~360 px Android on patchy 3G, wants to join their company in under two minutes and then mark
attendance with one tap — and, later that week, see their leave or payslip without calling HR.

| In scope | Deliberately left out of this scan |
|---|---|
| Field employee (driver, guard), store employee, line manager / store in-charge, HR admin who issues QRs, company head | Background location (steps 2 and 3); the portal redesign itself (slice 009); desktop users |
| Customer IT / DPO — only where the app changes what they see (store listing, notice) | Vendor and driver portals (`driver-portal.html`, `vendor-portal.html`) |

---

## 2. Evidence — what exists today

**How I looked.** The local bench (`hrlocal-bench`) was in use for another slice's release test,
so **I did not open any screen or take any screenshot in this run.** Everything below comes from
reading the code on `dev` today, and from two earlier measured audits: the phone audit of
11 Sep (slice 003, screenshots in `C:/Surbhi-Git/hrlocal-data/mobile-audit/2026-09-11/`) and the
field check-in design of 12 Sep (slice 008, screenshots in
`C:/Surbhi-Git/hrlocal-data/ux-review/2026-09-12/`). **Before the design step, the current state
must be captured on the bench at 390 × 844** — see §9, R-open.

### 2.1 What the app reuses, and what state it is in

| Piece | Where | State today | What the app needs from it |
|---|---|---|---|
| Field check-in screen | `www/field-checkin.html` (1,234 lines) | **Built and demoed.** Setup → Home → result → 12 error screens. EN / हिं switch (Hindi machine-drafted). Sample mode on `?demo` | Bundled. `BASE` address instead of relative calls; tenant name and notice facts from an endpoint instead of Jinja; secret in native secure storage (doc 10 §4b) |
| Device registration | `field_checkin.register_device` | Employee ID + consent tick + notice version → **always Pending** → HR activates in the desk. Same answer for a real or fake ID | Becomes the **fallback** path. QR redemption is a new endpoint |
| Consent notice | `field-checkin.html:290-310` | Six plain rows: what, what not, why, who, how long (from settings), rights. Version `2026-09-13` stored on the device record | Shown inside the app before the first punch. Retention and version must come from the tenant, not the bundle |
| Punch and status | `field_checkin`, `field_status` | Server time; photo private; GPS accuracy ≤ 100 m; "You must be within 100 m of PPJ Noida" shown before walking | Unchanged |
| Leaver lock | `block_devices_for_leaver` | Phone blocked the day status leaves Active | Unchanged; **does not end a My HR session** (see §3.9) |
| Home-screen install (PWA) | `manifest`, `app_icon`, `service_worker` | Tenant-coloured icon, name "PP Jewellers" on the home screen | **Replaced** by the store app — and the icon becomes "Alvoraa", not the employer's name (§3.1) |
| ESS portal | `www/hrms-employee.html` (~17k lines) | Session cookie + CSRF. 22 phone gaps (003). Own phone header and own bottom bar | Loaded remotely in the My HR tab |
| Portal check-in | `hr_api.do_checkin` | GPS only if the org needs it, **no photo, no accuracy check** | Must not be a second, weaker path inside the app (§3.4) |
| Sign-in page | `www/alvoraa-login.html` | Email / Username + Password. "Forgot password?" goes to `/update-password` (needs email). An already-signed-in visit sends desk roles to `/app` (`alvoraa_login.py`) | If the tab opens on the sign-in page, HR and owners land on the Frappe desk, which is not a phone screen (MA-15) |
| Support link on sign-in | `alvoraa-login.html:489` | `support@kinexus.in` — an old brand name | Should be the tenant's HR contact inside the app |

### 2.2 The journey today (PWA) vs step 1 (app)

```
TODAY (PWA)                                   STEP 1 (APP), as briefed
HR says "open ppj.alvoraa.co/checkin"         HR says "install Alvoraa, scan this"
 → type employee ID, tick notice              → install from Play Store (name to search?)
 → "Waiting for HR"   (always)                → scan QR  → joined, no waiting
 → HR activates in desk                       → notice → camera / location prompts
 → Add to Home Screen (3 steps)               → Attendance tab: Check In
 → Check In                                   → My HR tab: ??? sign in with what?
```

---

## 3. Gaps a phone user will hit, moment by moment

Impact: **H** stops the task or harms trust · **M** painful · **L** polish.
IDs use the prefix **MA-** (mobile app).

### 3.1 First launch and finding the app

| ID | Gap | Impact | Evidence / reasoning |
|---|---|---|---|
| MA-1 | **The employee does not know what to search for.** One listing for all tenants means the store name is "Alvoraa", a name a PPJ driver has never heard. Their PWA icon today says "PP Jewellers". | M | doc 10 §4a (one app); `manifest()` names the tenant |
| MA-2 | **Scanning a QR before the app is installed** opens the web page, which offers the app. After installing, the person has to **scan again** — unless the link is carried through the install. Android can pass it (install referrer, `[recall — verify]`); iPhone generally cannot. | M | doc 10 §4a "the same QR works whether or not the app is installed" |
| MA-3 | **A first screen that asks for a tenant code or employee ID before explaining anything** loses people. The current setup screen leads with "Set up this phone" and a notice — good — but has no "I have a QR" path. | M | `field-checkin.html:264-315` |

### 3.2 Joining a company

| ID | Gap | Impact | Evidence / reasoning |
|---|---|---|---|
| MA-4 | **QR not built.** Every join today waits for HR. | H | `register_device` always `Pending` |
| MA-5 | **The employee is at home** (joins before day one, or works remotely) and HR sends the QR on WhatsApp. **A phone cannot scan a QR shown on its own screen.** The app needs "Open the link" and "Choose a QR picture from my photos" as well as the camera. | H | Common Indian HR practice `[ASSUMPTION]`; scanning physics |
| MA-6 | **Expired or already-used QR** (24 h, single use — doc 10 §4a). Without a clear screen, the driver thinks the app is broken. Needs its own screen: "This code has already been used or has run out. Ask HR for a new one." — **no Try again**, per the pattern "no action button where no action would work". | H | ux-learnings patterns |
| MA-7 | **A forwarded QR.** First scan wins. If a colleague scans it by mistake, the right person is locked out and the wrong phone is joined. A **"Is this you? Ramesh K. · PP Jewellers · Driver"** step before joining, with "This is not me", catches it. Show a short name, not the full record. | M | doc 10 §4a single-use design |
| MA-8 | **Tenant code path still waits for HR**, by design (the code proves the company, not the person). The waiting screen needs to say how long and what to do meanwhile ("Use the reception machine until then"). Push "HR approved your phone" removes the polling. | M | doc 10 §4a; 008 E8 |
| MA-9 | **Wrong or unknown tenant code** must give one answer for every failure, and it must still be helpful: "We could not find that company code. Check it with HR." | L | doc 10 §4a "never lists tenants" |
| MA-10 | **Works for two companies** (contractors). One at a time, "Switch company" in settings, fresh join each time. | L | doc 10 §4a edge cases |

### 3.3 Signing in to My HR

| ID | Gap | Impact | Evidence / reasoning |
|---|---|---|---|
| MA-11 | **Frontline staff may have no login.** My HR needs a Frappe user with email or username and password. | **H** | `alvoraa-login.html:435`; `field_checkin.py` "A driver has no email address and no password" |
| MA-12 | **Those who have a login sign in twice**: once by QR (device), once by password (My HR). Two different "who are you" moments in one app, with two different "forgot" stories. | H | doc 10 §4b: device token vs session cookie |
| MA-13 | **"Forgot password?" needs an email.** A store employee with a username only is stuck. | M | `/update-password` |
| MA-14 | **Session runs out.** After the session expires the My HR tab silently becomes the sign-in page again. Frappe's default expiry is days, not months `[recall — verify the tenant setting]`. The person has no idea why. | M | Frappe session model |
| MA-15 | **HR managers and owners can be sent to the desk** (`/app`). A fresh sign-in sends anyone linked to an Employee to the portal (`auth.get_portal_redirect`), but **opening the sign-in page while already signed in** sends desk roles to `/app` (`alvoraa_login.py`), and so does a sign-in by a user with no Employee link. If the app's My HR tab starts at the sign-in page, HR users land on the desk, which is unusable in a phone webview. The tab should start at `/hrms-employee`. | M | `alvoraa_login.py`; `auth.py:67-85` |

### 3.4 Moving between the tabs

| ID | Gap | Impact | Evidence / reasoning |
|---|---|---|---|
| MA-16 | **Two bottom bars.** The portal draws its own phone bottom bar (Home · Attendance · Finances) and a phone header; the app adds its own tab bar underneath. | H | 003 M20; appendix A FR-08 |
| MA-17 | **One word, two things.** App tab "Attendance" = check in. Portal bar "Attendance" = my attendance history. | M | Principle 6 (one word for one thing) |
| MA-18 | **Two Check In buttons with different evidence rules** (portal: no photo, no accuracy; app: photo, accuracy). | H | `hr_api.do_checkin` vs `field_checkin` |
| MA-19 | **Losing my place.** If switching tabs reloads My HR, a half-filled leave form is lost. The webview must keep its page alive. | M | Engineering note for the spec |
| MA-20 | **After a punch, My HR is stale.** The portal's Home still says "Not checked in" until reloaded. | L | Two separate pages |
| MA-21 | **Links that leave the app**: payslip PDFs, attachments, `mailto:`, "Switch to desk", Tenant Admin. A webview does not download or open these by itself. A payslip that does nothing when tapped reads as "the app is broken". | M | Portal features; webview behaviour `[recall — verify on Capacitor]` |

### 3.5 No signal

| ID | Gap | Impact | Evidence / reasoning |
|---|---|---|---|
| MA-22 | **My HR with no signal shows a blank page or a browser error** — the single most "this is just a website" moment, and the one Apple's reviewers test by switching on airplane mode. | H | doc 10 §4b "Remote … ❌ blank screen"; §6 below |
| MA-23 | **Attendance opens with no signal but cannot save a punch.** The offline queue (008 P11) is not built; E6 says "move to a place with signal". A driver in a basement car park cannot mark in. | M (H for drivers) | 008 01b §11 |
| MA-24 | **A slow start on 3G.** Budget: skeleton within 300 ms, usable ≤ 2.5 s p95 (nfr-budget §2). The bundled tab can meet it; the remote portal did not in the audit (Home loads approvals 1.5 s after page load; the pending count took 11.6 s for HR). | M | appendix A finding 2 |

### 3.6 Consent notice and phone permissions inside an app

| ID | Gap | Impact | Evidence / reasoning |
|---|---|---|---|
| MA-25 | **The notice's facts live on the server** (retention days, version) but the page will be in the bundle. It must fetch them; if it cannot (no signal on first launch), it must **not** show a notice with a blank "How long" row. Say "Connect to the internet to finish setting up." | M | `notice_facts()`; `field-checkin.html:301` |
| MA-26 | **Operating-system prompts appear with no context** unless the app explains first. Ask for camera and location **at the first Check In**, after one line of explanation, not at launch. In step 1 ask only for "While using the app" location. | M | Store practice; 008 E1/E2 already handle "refused" |
| MA-27 | **Store privacy labels must say the same as the notice.** Google Play "Data safety" and Apple's privacy label will list photo, precise location, employee ID. If the store says one thing and the notice another, a security reviewer will notice. | M | Customer IT persona |
| MA-28 | **The notice promises "You are not tracked while you work."** True for step 1. Steps 2 and 3 break it, and the store listing for step 1 should not be written in a way that must be withdrawn. Plan a new notice version and re-consent screen for step 2 now. | M (later H) | doc 10 §3; `CONSENT_VERSION` |

### 3.7 App updates vs web updates

| ID | Gap | Impact | Evidence / reasoning |
|---|---|---|---|
| MA-29 | **"This screen is out of date. Close the app, open it again"** — the server's own sentence for a notice mismatch. In a store app, reopening does not help. It loops. | H | `field_checkin.py:173-176` |
| MA-30 | **Error text matched by English sentence.** A server rewording breaks every old app version at once, silently turning helpful screens into "Something went wrong". | H | 008 01b §6 |
| MA-31 | **My HR updates on every deploy; Attendance updates only through the store.** Two tabs of one app can be different ages. Need a minimum-version check and an "Update the app" screen with one button to the store. | H | doc 10 §4b |
| MA-32 | **Today's PWA users must move.** Their device secret lives in the browser's storage and the app cannot read it. Every current phone re-joins. For PPJ that is a rollout day, not a code task. | M | `localStorage` key `alvoraa.field.v1` |

### 3.8 Signing out and leaving

| ID | Gap | Impact | Evidence / reasoning |
|---|---|---|---|
| MA-33 | **"Log out" means three different things**: end My HR session; remove this phone from the company; switch company. Today the portal's log out lives in Frappe's website bar, which slice 009 removes (appendix A D2). | M | appendix A FR-13 |
| MA-34 | **An employee who leaves** — the phone is blocked (built). The app should say so plainly (008 E10) and offer "Remove company from this phone", not keep showing a dead Check In. | L | `block_devices_for_leaver` |

### 3.9 Lost phone and shared phone

| ID | Gap | Impact | Evidence / reasoning |
|---|---|---|---|
| MA-35 | **Lost phone: HR blocks the device, but a signed-in My HR session on that phone stays alive** — with payslips and personal details behind it. Blocking the phone should end its My HR session too, or HR needs one action that does both. | **H** (privacy) | Two separate credentials, doc 10 §4b |
| MA-36 | **Shared phone** (a store counter phone, a family phone). The device secret belongs to one employee, so a second person cannot punch; a signed-in My HR shows the last person's payslip to whoever picks it up. | H (privacy) | Device bound to one employee |
| MA-37 | **No app lock.** Anyone holding an unlocked phone can open My HR. Deel offers biometric login in its app (read, see §4). | M | — |

### 3.10 Language and branding

| ID | Gap | Impact | Evidence / reasoning |
|---|---|---|---|
| MA-38 | **Attendance is EN / हिं; My HR is English only** until slice 009 Wave 5. One language switch in the app that only half works is confusing. Say it: "My HR is in English for now." | M | 009 Wave 5 |
| MA-39 | **Tenant colours inside, Alvoraa outside.** The app icon cannot be the tenant's. Inside, the header should carry the company name and colour from the manifest endpoint, so the person sees "PP Jewellers" within a second of opening. | L | `_brand()` |

---

## 4. How competitors' whole mobile apps handle this

**Honesty about the evidence.** Every claim below is **read** — from help pages, product pages
and store pages, on **17 Sep 2026**, mostly through search summaries. **I did not view any
product screenshots in this run**, so nothing is marked "seen". I have no trial accounts. These
are what each company says about itself.

### 4.1 Joining the company and signing in

| Product | How the app finds the company | How the person signs in | Label |
|---|---|---|---|
| **SAP SuccessFactors** | **Personal QR**: log in on desktop → Options → Mobile → QR shown; it **expires in 30 s** with "Get New Code". Also a **company-wide QR** from the login screen | Personal QR activates for that user | read, [SAP Help — personal QR](https://help.sap.com/docs/SAP_SUCCESSFACTORS_MOBILE/f9554a84b1394ee5accc0f8fce5cfc7b/89cc667583ed4fd88105592685ab1339.html), [company-wide QR](https://help.sap.com/docs/SAP_SUCCESSFACTORS_MOBILE/9e71f63fdafb41f990459283403ee8be/8ead9e921ff24db0828bfcf6e3e079c3.html) |
| **Workday** | Type an **Organization ID** (case sensitive), or show the org's QR from the web profile; "Find My Organization" by work email | Company SSO, plus app security steps | read, [Workday mobile setup, UT Austin](https://workday.utexas.edu/find-help/workday-mobile-app-setup), [Lesley support](https://support.lesley.edu/support/solutions/articles/4000198424-how-to-sign-up-for-workday-mobile) |
| **BambooHR** | Now asks for **email first instead of the company domain**; QR scanning also offered | Password, SSO or QR, by company setup | read, [BambooHR product update](https://www.bamboohr.com/product-updates/mobile-login-simplification) |
| **greytHR** (India) | **OTP to mobile number or email** (OTP valid 15 min, resend after 30 s, max 5), or "Log in with Web Address" | OTP, or login ID + password, or SSO | read, [greytHR help](https://www.greythr.com/employee-mobile-app/answers/5SkNBWVGQo-KBblLKISX6A) (page fetched) |
| **Keka** (India) | **Mobile OTP** login from the sign-in screen (with a captcha) | OTP or email + password | read, [Keka help](https://help.keka.com/admin/admin-help/logging-in-to-keka) |
| **Darwinbox** (India) | Type the **organisation URL**, pick domain if several | Email + password; the organisation must allow mobile access | read, search summary of Darwinbox help video and store listing |
| **Zoho People** | One Zoho account; people in several organisations **switch portal** from the account menu | Zoho account (OneAuth for MFA) | read, [Zoho switch organisation](https://help.zoho.com/portal/en/kb/one/admin-guide/managing-organization/articles/switch-organization-portals) |
| **Deel** | — | **Biometric login** in the app; offline use claimed | read, [Deel mobile app](https://www.deel.com/mobile-app/) |
| **Frappe HR (standard)** | None — the PWA is opened at `<site>/hrms` | Site credentials | read, [Frappe HR docs](https://docs.frappe.io/hr/mobile-app-installation) |

**What this tells us.**
- The Indian products for frontline staff (**greytHR, Keka**) solved "no email" with **mobile
  number + OTP**. The global ones assume an email or SSO.
- **Nobody I read ties the attendance device and the self-service login together** the way our
  two-credential design would require. They have one account.
- SAP's personal QR expires in 30 seconds because the employee is **already logged in on a
  desktop**. Our frontline person has no desktop, so a 24-hour HR-issued QR (doc 10) is the right
  shape for us.

### 4.2 Attendance and check-in

| Product | What they do | Label |
|---|---|---|
| **Keka** | Selfie registration, then **face matched** on every clock-in; geofence | read, [Keka help / attendance pages](https://www.keka.com/gps-mobile-attendance) |
| **Zoho People** | Face matched to the profile photo; geo and IP restrictions; **location tracking**; a separate **Kiosk** app for shared devices | read, [Zoho location tracking](https://help.zoho.com/portal/en/kb/people/administrator-guide/attendance-management/settings/articles/location-tracking-using-zoho-people-mobile-application), [Zoho Kiosk](https://www.zoho.com/people/kiosk.html) |
| **Darwinbox** | Facial recognition + geotagging; **offline mode stores and syncs** | read, [Darwinbox mobile HRMS](https://darwinbox.com/en-us/innovations/mobile-hrms) (vendor marketing) |
| **HROne** | Selfie with liveness, geofence, **offline punch with auto-sync**; punches also by WhatsApp and Teams bots; a non-face path for those who decline | read, [HROne attendance app blog](https://hrone.cloud/blog/employee-attendance-app/) (vendor's own blog) |
| **Workday** | Separate **Time Kiosk** app for shared tablets; third parties sell kiosks because frontline staff lack corporate logins | read, [Workday Time Kiosk on Play](https://play.google.com/store/apps/details?id=com.workday.timekiosk&hl=en_US); frontline claim from a kiosk vendor's page — treat as marketing |
| **Frappe HR (standard)** | Check-in with geolocation in the PWA | read, [Frappe HR docs](https://docs.frappe.io/hr/employee-checkin) |

### 4.3 Self-service inside the app

| Product | What they show | Label |
|---|---|---|
| **Rippling** | Time off request and approve, expenses, payslips, time cards, benefits | read, [Rippling on the App Store](https://apps.apple.com/us/app/rippling-hr-it-finance/id1231325957) |
| **greytHR, Keka, Darwinbox, HROne** | Leave, payslips, attendance, approvals for managers — all in **one native app**, not a website tab | read, store listings and product pages above; depth of each `[recall — verify]` |

### 4.4 What we will deliberately not copy

| Pattern | Who does it | Why not, for our people |
|---|---|---|
| **Face matching on every punch** | Keka, Zoho, Darwinbox, HROne | product-context §6.3 refuses facial analysis. The photo is evidence a human can look at, not a match (008 brief §4). Also: matching fails in sunlight on cheap cameras and blames the worker |
| **Location tracking as a general feature** | Zoho People | Step 1 has no background location. Steps 2–3 are limited to named field roles, on duty, visible to the person (doc 10 §3) |
| **Find my employer from a phone number or email** before anyone proves who they are | Workday "Find My Organization", BambooHR email-first | Tells anyone which company a number works for (doc 10 §4a option C). Using a phone number **after** the company is known, for OTP, is a different thing and worth considering (Q1) |
| **30-second personal QR** | SAP | Needs a logged-in desktop the frontline worker does not have |
| **Punching through a WhatsApp bot** | HROne | Puts attendance evidence through a third-party chat service; no photo standard |
| **Captcha on a login** | Keka | A barely literate driver on a small screen should never meet "I'm not a robot" |

**One idea worth borrowing:** SAP's **company-wide QR**. For us this is just the tenant code as a
picture — no secret in it. A poster at the store entrance or a link in the HR WhatsApp group
answers "which company?" for anyone without a personal QR. It still needs HR approval, as the
tenant code does.

---

## 5. Persona by persona — ideas, and which step they belong to

Size: S / M / L, rough. **Step 1** = propose for this slice. **Later** = step 2+ or another slice.

### 5.1 Field employee — driver or guard, low-end Android, Hindi first

| Idea | Job it serves | Evidence | Size | Step |
|---|---|---|---|---|
| **Scan once, done:** the QR joins the company **and** opens My HR with no password (Q1 option A) | "Let me use the app without remembering anything" | MA-11, MA-12; greytHR/Keka OTP shows the need | L (security-heavy) | **1** — or decide Q1 |
| "Is this you?" confirm before joining | Stop a forwarded QR joining the wrong phone | MA-7 | S | **1** |
| "Open the link" and "Pick QR from photos" beside the camera scan | Join from home when the QR came on WhatsApp | MA-5 | S | **1** |
| One screen for an expired or used QR, with "Ask HR for a new code" and no retry | Know what to do instead of thinking it is broken | MA-6 | S | **1** |
| Push: "HR approved your phone. You can check in now." | Stop re-opening the app to see if HR has acted | MA-8 | M | **1** |
| **Offline punch queue**, clearly labelled "Saved on this phone. It will be sent when you have signal." with the server time rule explained | Mark in from a basement or highway | MA-23; 008 P11; Darwinbox and HROne both claim it | M | **1** (strongest 4.2 argument, §6) — PM call |
| Language chosen once, applies everywhere; "My HR is in English for now" | Read the app in Hindi | MA-38 | S | **1** |
| Long-press the app icon → "Check in" shortcut | Punch in two taps from the home screen | App shortcuts `[recall — verify on Capacitor]` | S | Later |
| "This week" list of my punches in the Attendance tab | "Did yesterday's check-out save?" | Frequent HR call reason `[ASSUMPTION]` | S | Later |
| My own route and automatic check-outs | See what was recorded about me | doc 10 §3, N4 | M | Step 2–3 |

### 5.2 Store employee — fixed branch, reception machine exists

| Idea | Job it serves | Evidence | Size | Step |
|---|---|---|---|---|
| **Today strip at the top of Attendance:** "Today 10:00–7:00 pm · PPJ Station Road" plus punches from **this phone and the reception machine** in one list | Know my shift and whether I'm marked, in one look | Punch list already names "Reception machine" (008 5.3) | S–M | **1** (list built; shift line new) |
| My HR's Check In **hands over** to the Attendance tab inside the app | One check-in, one set of rules | MA-18 | S | **1** |
| Portal's own header and bottom bar hidden inside the app; one app tab bar | Not two bars, not two "Attendance" | MA-16, MA-17 | S | **1** |
| App tab bar labels: **Check in** · **My HR** (not "Attendance") | One word for one thing | Principle 6 | S | **1** |
| Leave balance and "Apply leave" reachable in two taps from My HR | The second most common phone job | 003 audit: leave pop-up submit below the fold (M12) | depends on 009 | 009 Wave 1–3 |
| Payslip opens as a PDF inside the app, with "Share" / "Save" | Show a payslip to a bank or landlord | MA-21 | M | **1** (must not be a dead tap) |

### 5.3 Line manager / store in-charge — phone between customers

| Idea | Job it serves | Evidence | Size | Step |
|---|---|---|---|---|
| Push: "Sonia Kumar asked for leave on 20 Sep" → opens the request in My HR | Approve without opening a laptop | product-context §2 "approve in one action" | M | Later (needs server events) |
| "Today at Station Road: 12 of 14 checked in" — names only for those not in, **no reason for absence shown** | See who needs cover | Principle 5; refusal on reasons | M | Later (009 Home) |
| **Must not:** live map of team, ranking by punch time, "last seen" | — | product-context §6.4 | — | Never |

### 5.4 HR admin — issues QRs, approves phones

| Idea | Job it serves | Evidence | Size | Step |
|---|---|---|---|---|
| **"Invite to the app" on the Employee record:** show QR on screen, print, or copy a link to send on WhatsApp; "Expires tomorrow at 3:10 pm" in words | Hand a new joiner the app in one action | doc 10 §4a; MA-5 | M | **1** |
| **Batch QR sheet** for a list of employees (one per page or 8 per A4, with name and "Scan within 24 hours") | Onboard 30 drivers on a Monday | 400-person PPJ rollout; MA-32 | M | **1** (PPJ migration needs it) |
| **App status column**: Not invited · Invited (expires …) · Joined · Waiting for approval · Blocked | See who is not ready before the go-live day | Principle: "see who is not ready" (HR persona) | M | **1** |
| **One action "Block this phone"** that also ends that phone's My HR session | Lost or stolen phone | MA-35 | S–M | **1** |
| Revoke an unused invite | Wrong person, printed by mistake | doc 10 §4a | S | **1** |
| Company poster QR / company code, printable | Staff without a personal invite | §4.4 borrow | S | Later |
| Where HR does this: **desk or portal Org Settings?** | — | 008 set radius in Org Settings; devices approved in desk | — | ⚠ Q6 |

### 5.5 Company head — phone, five minutes

| Idea | Job it serves | Evidence | Size | Step |
|---|---|---|---|---|
| "312 of 400 people have joined the app · 9 waiting for HR" — a count, no names | Know the rollout is working | Adoption is not a success measure on its own (product-context §8 bans logins) — use it only during rollout | S | Later |
| Opens My HR as an ordinary employee, **not** the desk | The owner of PPJ is also an employee with HR roles | MA-15 | S | **1** |

### 5.6 Customer IT / security reviewer, DPO

| Idea | Job it serves | Step |
|---|---|---|
| **"What this app records"** reachable from settings at any time — the same six rows as the notice, plus the notice version and date agreed | Show privacy in the product, not only in a PDF | **1** |
| Store listing and privacy labels say "No location in the background" in step 1 | A claim they can check | **1** |
| App settings show app version and "Signed in to ppj.alvoraa.co" | Support and audit | **1** |

### 5.7 Rough sketch — app frame (not a design)

```
┌────────────────────────────┐        First launch
│ PP Jewellers        ⚙      │        ┌────────────────────────────┐
│                            │        │  Join your company         │
│  (Check in tab: bundled)   │        │                            │
│  Not checked in yet today  │        │  [ Scan the QR from HR ]   │  ← biggest
│  [ camera ]                │        │  Open a link from HR       │
│  You must be within 100 m  │        │  Pick a QR from my photos  │
│  ┌──────────────────────┐  │        │  I have a company code     │
│  │      CHECK IN        │  │        │                            │
│  └──────────────────────┘  │        │  EN | हिं                   │
├──────────────┬─────────────┤        └────────────────────────────┘
│  ◉ Check in  │  ☰ My HR    │   ← one tab bar, words beside icons
└──────────────┴─────────────┘
⚙ Settings: Language · What this app records · Sign out of My HR ·
  Remove this phone from PP Jewellers · Switch company · App version · Help
```

---

## 6. Apple 4.2 — what makes step 1 more than a website

**Apple's words (read 17 Sep 2026, [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)):**
4.2 — "features, content, and UI that elevate it beyond a repackaged website … 'app-like'".
4.2.2 — apps shouldn't primarily be "web clippings, content aggregators, or a collection of
links". Google Play treats apps that are "just webviews of existing websites" as spam
(read, [Android Developers Blog](https://android-developers.googleblog.com/2020/10/developer-tips-and-guides-common-policy.html)).

**The risk is real because step 1 removes background location**, which was doc 10's main argument
that the app is native. What is left must carry the case. From a UX point of view:

| # | What the reviewer can see and touch | Native? | Also good for users? | Rating |
|---|---|---|---|---|
| 1 | **A native tab bar** (not a web menu) switching between two live screens that keep their state | Yes | Yes — one bar, MA-16 | Must |
| 2 | **QR scanner with the native camera**, plus pick-from-photos | Yes | Yes — joining in seconds | Must |
| 3 | **Airplane mode works gracefully**: Check in opens and (if built) queues the punch; My HR shows a native "No internet" screen, not a browser error | Yes | Yes — MA-22, MA-23 | Must |
| 4 | **Camera and location prompts with our own explanation first**, and purpose strings in plain words | Yes | Yes — MA-26 | Must |
| 5 | **Device secret in the Keychain / Keystore**, survives cache clears | Invisible to a reviewer | Yes | Must (security), weak as evidence |
| 6 | **Push notification** "HR approved your phone" (and later, leave decisions) | Yes | Yes — MA-8 | Strongly recommend |
| 7 | **Offline punch queue** | Yes | Yes — drivers | Strongly recommend; PM call on size |
| 8 | **Native settings screen**: language, what this app records, remove phone, switch company | Partly | Yes — MA-33 | Recommend |
| 9 | **App lock with the phone's fingerprint / face unlock** for My HR (the OS does the check; we store nothing about the face) | Yes | Yes — MA-37 shared phones | Consider. Note: uses the phone's own unlock, not our facial analysis — still check wording against refusal §6.3 |
| 10 | Haptic tick on a saved punch; home-screen shortcut | Yes | Small | Later |

**Two reviewer-access traps (both High):**
- **The reviewer cannot scan a QR from HR.** App Review needs a working path: a demo company code
  plus demo employee, in the review notes, pointing at a demo tenant with sample data — never a
  customer's tenant.
- **If My HR is the first thing a reviewer sees and it shows the 003 layout gaps,** the app reads
  as a squeezed website. Open on the **Check in** tab by default; make sure the My HR frame fixes
  (hide the portal's bars, MA-16) are in the reviewed build.

**Apple 5.1.1(v)** asks for in-app account deletion when an app **creates** accounts. Ours does
not — the employer creates the record. Offering "Remove this phone from {company}" is still the
honest equivalent and helps the case. `[read 17 Sep 2026 — confirm with whoever submits]`

---

## 7. Checks against the refusals and privacy

- **No refusal is needed for step 1.** No background location, no face matching, no ranking.
- **Watch these as the app grows:** a manager "last seen" or "online now" indicator; a team map;
  "punctuality score". All are passive monitoring (§6.4). Presence yes, reasons never.
- **Personal data on screen at join:** the "Is this you?" step shows first name, initial,
  company and designation — enough to catch a mistake, not a record.
- **Lost and shared phones are the main privacy exposure** of step 1 (MA-35, MA-36). They belong in
  `01c`.

---

## 8. Ranked risks and open questions for the product manager

### 8.1 Risks, ranked

| Rank | Risk | Why it matters | What would reduce it |
|---|---|---|---|
| 1 | **Frontline staff cannot sign in to My HR** (MA-11) | The My HR tab is a locked door for the persona the app is built for | Decide Q1 before the brief |
| 2 | **Old app versions break when the server changes** (MA-29–31) | Drivers locked out on a Monday with no fix they can apply | Minimum-version check + "Update the app" screen; error codes instead of sentence matching |
| 3 | **Two check-in paths with different evidence** (MA-18) | A punch's trustworthiness depends on the tab tapped; disputes | Portal Check In hands over to the Check in tab inside the app |
| 4 | **Portal not phone-ready; two bottom bars** (MA-16, 003) | App looks broken; Apple 4.2 rejection | Hide portal bars in the app now; decide whether My HR waits for 009 Wave 1 (Q3) |
| 5 | **Lost / shared phone exposes My HR** (MA-35, MA-36) | Payslips and personal data on a phone HR has "blocked" | One HR action that blocks the phone and ends its session; app lock (Q7) |
| 6 | **App Review cannot get in** (§6) | Weeks lost to a rejection that is about access, not quality | Demo tenant + company code in review notes |
| 7 | **QR logistics** — at home, forwarded, expired (MA-5–7) | First-day failures land on HR's phone | Link + photo import; "Is this you?"; clear expiry screen |
| 8 | **PWA users must re-join** (MA-32) | PPJ rollout day for every current phone | Batch QR sheet; rollout plan with DevOps |
| 9 | **Wildcard certificate still undecided** (09) | The app cannot reach a tenant without HTTPS on its name; dev tenants need `*.dev.alvoraa.co` | Surbhi's DNS decision (09 §3) — before any test build points at a new tenant |
| 10 | **Dead taps on payslips and attachments** (MA-21) | "App is broken" on the most valued self-service job | Handle downloads and outside links natively |
| 11 | **Store name "Alvoraa" unknown to staff** (MA-1) | People install the wrong app or none | Store listing text; HR's invite says the exact name and shows the icon |
| 12 | **Half the app in Hindi** (MA-38) | Confusion; trust | Say so on screen until 009 Wave 5 |

### 8.2 Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| **Q1** ⚠ DECISION | **How does a frontline employee with no email or password get into My HR?** (A) the QR join also signs them in to My HR — the device secret is exchanged for a web session; (B) mobile number + OTP, as greytHR and Keka do (SMS cost, number must be on the Employee record); (C) HR creates a username and password for everyone; (D) step 1 shows My HR only to people who already have a login, and says so to the rest. My UX preference is **A**, with a security review; **D** is the honest fallback. | Surbhi, with security | The whole My HR tab; brief scope |
| Q2 | Should the portal's Check In button, inside the app, open the Check in tab instead? (Recommend yes.) | Surbhi | MA-18 |
| Q3 | Does the My HR tab ship before slice 009 Wave 1 (the frame), or wait for it? If before: hide the portal's own header and bottom bar inside the app as a small step-1 change. | Surbhi, PM | App look; Apple review; 009 plan |
| Q4 | Is the offline punch queue in step 1? What time does a queued punch carry — server time on arrival (today's rule) or phone time, shown as "sent late"? | Surbhi, with security | MA-23; 4.2 case; attendance rules |
| Q5 | Push notifications in step 1 — only "phone approved", or also leave decisions? | PM | MA-8; server work |
| Q6 | Where does HR issue QRs and approve phones — Frappe desk or portal Org Settings? | PM, HR persona | HR flow design |
| Q7 | App lock for My HR (phone's own unlock) — step 1 or later? And does it sit well with refusal §6.3 in the customer's eyes? | Surbhi | MA-36, MA-37 |
| Q8 | Store listing name and icon: "Alvoraa" or "Alvoraa HR"? What words does HR use in the invite? | Surbhi | MA-1 |
| Q9 | QR lifetime — doc 10 N10 suggests 24 h. For a batch printed on Friday for Monday joiners, is 72 h needed? | Surbhi | Batch invite design |
| Q10 | Which Frappe session length for app users, and what the person sees when it ends | Security, DevOps | MA-14 |
| Q11 | Will the step 1 store listing and privacy labels be written knowing steps 2–3 add location? (Recommend: describe step 1 truthfully; plan a re-consent screen for step 2.) | Surbhi, security | MA-27, MA-28 |
| Q12 | Rename the old `support@kinexus.in` link on the sign-in page to the tenant's HR contact | Engineering | MA sign-in polish |

---

## 9. What I could not check

- **R-open: no current-state capture.** The bench was off limits. Before the design step, capture
  at 390 × 844: the sign-in page, portal Home with its Check In and bottom bar, and the field
  check-in setup — for one field employee, one store employee, one manager and one HR user.
- **How many PPJ employees have a user account** (drives Q1). One read-only query when the bench is
  free.
- **Capacitor behaviour** for file downloads, keeping a webview alive across tabs, install
  referrers and app shortcuts — all `[recall — verify]`.
- **Competitor apps first-hand.** No screenshots viewed, no trial accounts.

---

## Open questions

See §8.2. The one that blocks the brief is **Q1 (owner: Surbhi, with security)**. Q3 and Q4 shape
the slice size.

## Assumptions

- [ASSUMPTION] Many frontline employees in target tenants have no Frappe user account, as the
  008 brief states for drivers. Not counted for PPJ in this run.
- [ASSUMPTION] HR commonly sends onboarding material on WhatsApp, so QR-on-the-same-phone is a
  normal case, not an edge case.
- [ASSUMPTION] The QR, the tenant-code lookup and the version check are built as doc 10 §4a
  describes; none exists in code today.
- [ASSUMPTION] Slice 009 Wave 1 (portal frame) will not ship before step 1's first test build.

## Handoff note

To the product manager: **decide Q1 before writing the brief** — without it the My HR tab may
serve only office staff, which is not who this app is for. I disagree mildly with one line of the
idea as framed: "session login" for My HR is stated as fixed, but for frontline staff it likely
means **no login**; please confirm that is accepted or pick another option. Treat MA-18 (two check-in
paths), MA-29–31 (app versions vs server) and MA-35 (lost phone keeps My HR open) as step-1 musts
even though none is a visible feature. The 4.2 case in §6 depends on the native tab bar, the QR
scanner and a graceful offline state; background location no longer carries it. Every competitor
claim is **read**, not seen, and should not be quoted externally without a check.
