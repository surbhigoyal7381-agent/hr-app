---
slice: 013-mobile-app
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-09-17
status: draft — round 1, for Surbhi to click through
inputs: [01-product-brief.md (incl. Gate decision 2026-09-17), 01a-ux-opportunities.md, 00-sequencing-recommendation.md (incl. User decisions 2026-09-17), 07-devops-inputs.md §1, 008-field-checkin/01b-ux-design.md, alvoraa_portal/www/field-checkin.html, alvoraa_portal/www/field_checkin.py, alvoraa_portal/field_checkin.py, alvoraa_field_device.json, templates/includes/design_system.html, templates/includes/brand_color.html, .claude/context/ux-learnings.md, product-context.md §2 §6, nfr-budget.md §2 §5 §7, handoff-contract.md]
---

# 013 · Mobile app, step 1 — UX design

**I recommend. You decide.** Click the prototype, then say go, change or drop.

## Read this first

**Bad news first.**

1. **I did not open the real product.** The local bench was off limits for this run, as it was for
   the scan. Everything about "today" comes from reading `field-checkin.html` and
   `field_checkin.py` on `dev`, plus the measured audits of 11 and 12 Sep.
2. **Security's design (`01c`) is not written yet.** The QR screens here assume the controls in
   the brief (single use, bound to one person, hash only, one-tap block). If security adds a step
   (for example a PIN, or a shorter default lifetime), the join flow changes.
3. **The notice needs a new version.** The app records one new thing, the phone's model name at
   set-up, and the current notice does not say so. Changing the words means a new
   `CONSENT_VERSION`, and that needs a "the notice has changed" screen. Both are designed (D19).
4. **Two small wording bugs in today's web page travel into the app unless fixed:** after a
   check-out the status line says "Not checked in yet today" (FC-1), and the page says "manager"
   in the notice but "supervisor" on the result screen (FC-2).
5. **Android permission dialogs differ by phone maker.** I drew a plain Android 14 style. Xiaomi,
   Realme and Samsung word them differently. Check on the three pilot phones.

**The prototype:** `docs/slices/013-mobile-app/prototype-v1/index.html` (one file, invented data
only). **I cannot publish a link from here — the lead session publishes it.** See §15 for how to
review it.

**The three biggest design decisions**

| # | Decision | Why |
|---|---|---|
| 1 | **No bottom tab bar in step 1** (D1). A top bar with the company name and a labelled **Settings** button. The two-tab bar arrives with My HR. | A bar with one real tab is decoration, and a greyed "My HR" tab is an anti-pattern we have seen twice (AI2, LV11). It also costs 60 px on a 640 px-tall phone where the camera needs the height. |
| 2 | **The code is used up only at "Agree and finish"**, after "Is this you?" and the notice. Every eligibility check (ran out, used, cancelled, app switched off, not a field job) happens **before** the name is shown. | Nobody reads a notice or sees a name for a join that cannot work. A person who stops half-way has used nothing. |
| 3 | **One screen per failure, with a short code for HR at the bottom** (D11), driven by codes from the server, not English sentences. Real numbers (140 m, 380 m) arrive as values. | Keeps the 008 pattern that works, and stops a server wording change from breaking every older app (MA-29–31). |

---

## 1. Frame

**Who, when, where, what.** A driver or guard on the day HR hands them the app, on a
360–412 px Android phone on patchy 3G, often Hindi first, wants to join their company and be
marked present within two minutes, without waiting for anyone. Then, every working day, check in
and out in one tap.

| In scope | Left out, on purpose |
|---|---|
| **Field employee** (driver, guard) — the employee app | Office and store staff (not in this increment; brief §5) |
| **HR Manager** — invite, see who joined, block, organisation settings, in the Frappe desk | My HR tab, portal Org Settings screens (line A, next increment) |
| **Security reviewer / DPO** — "What this app records", notice version, honest remove | iPhone screens (one test phone only, S14), store listing |

**Three-persona check**

| Persona | What changes |
|---|---|
| **Employee (field)** | Joins by scanning HR's QR; no employee ID, no "Waiting for HR", no "Add to Home Screen". Check-in screen is the one they know from the web page. |
| **HR Manager** | New section "Field attendance app" on the Employee record; new "Field App Settings" page; a list of all app phones. |
| **CXO** | Nothing visible. Punches keep landing in Frappe HR as today. |

**One-way rule check.** Nothing here makes a manager's job easier at the employee's cost. The
phone list has no "last seen" or "online now" column (§10).

## 2. Evidence

- **Screens not captured.** Bench off limits (task rule). No screenshot of the real product was
  taken. The 12 Sep measured screenshots of the web check-in page are in
  `C:/Surbhi-Git/hrlocal-data/ux-review/2026-09-12/`.
- **Code read on 17 Sep 2026:** `www/field-checkin.html` (all 1,234 lines), `www/field_checkin.py`,
  `field_checkin.py` (errors, `register_device`, `field_status`, `notice_facts`, retention),
  `alvoraa_field_device.json` (fields: employee, status Pending/Active/Blocked, device_label,
  platform, token_hash, registered_on, activated_by, last_seen, checkin_count, consent fields),
  `design_system.html`, `brand_color.html`.
- **My own look at the prototype** (Playwright, Chrome, local file only, no server): all 47 phone
  screens at 390 px and 360 px in English and Hindi, all 14 desk screens at 1440 px and 390 px.
  **Result:** no page wider than the screen, no tap target under 44 px, no text under 12 px, no
  script errors; the full join → check-in click path works. Fixes made after the look: the review
  controls made the page scroll sideways at 360 px (now wrap); a sticky review panel covered the
  phone (now scrolls away); the "I agree" tick carried over between codes (now resets).
  Screenshots hold invented data only and sit in the session scratchpad, not the repo.

## 3. Benchmark

Unchanged from `01a` §4, all **read** on 17 Sep 2026, nothing **seen**, no trial accounts. The two
lessons used in this design:

- **SAP's personal QR** proves "show a code, the phone joins" is a known pattern, but it expires in
  30 seconds because the person is logged in on a desktop. Our worker is not, so HR issues it.
- **greytHR and Keka** solve "no email" with mobile OTP. We do not, for the reasons in brief §3.

**What we deliberately do not copy:** face matching; a "last seen" or live map for HR; captcha;
WhatsApp-bot punches; finding the employer from a phone number. Each would either blame the
worker for a cheap camera, or turn a punch tool into a watching tool.

## 4. Findings

Impact H / M / L. Kind Fix / Improve / New / Keep. IDs from `01a` are reused.

| ID | Page | Finding | Impact | Kind | Size | Evidence |
|---|---|---|---|---|---|---|
| FC-K1 | Check-in | One big Check In, camera above, today's punches, "within 100 m of …" shown before walking | H | **Keep** | — | `field-checkin.html` home; 008 demo |
| FC-K2 | Check-in | One screen per failure, real numbers from the server, photo kept on retry, camera-off still counts | H | **Keep** | — | `PROBLEMS` table in the page |
| FC-K3 | Setup | Six-row plain notice, retention from the organisation's setting | H | **Keep** | — | `notice_facts()` |
| FC-1 | Check-in | After a check-out the status line says "Not checked in yet today" — untrue | M | Fix | S | `renderHome`: every "not in" state uses `home.state.out` |
| FC-2 | Notice / result | "HR and your **manager**" vs "HR and your **supervisor**" — one idea, two words | L | Fix | S | `notice.who` vs `res.privacy` |
| FC-3 | Notice | App stores the phone's model name at set-up; the notice does not say so | M | Fix | S | `device_label` field; brief §11 "new data: phone name" |
| MA-4 | Join | Every join waits for HR | H | New | M | `register_device` always `Pending` |
| MA-5 | Join | Code sent on WhatsApp cannot be scanned by the same phone | H | New | S | Brief S2 |
| MA-6 | Join | Used / ran out / cancelled code needs its own screen with no Try again | H | New | S | Brief S4 |
| MA-7 | Join | Forwarded code joins the wrong phone | M | New | S | Brief S3 |
| MA-26 | Join / check-in | System permission prompts with no warning | M | New | S | Store practice |
| MA-29 | Setup | "Close the app, open it again" loops in an installed app | H | Fix | S | `field_checkin.py:170` |
| MA-30 | All | Errors matched on English text | H | Fix | M | `handle()` in the page |
| MA-31 | All | No "Update the app" screen | H | New | S | Brief S9 |
| MA-34 | Stopped | A blocked or leaver phone offers nothing to do | L | Improve | S | 008 E10 |
| FA-1 | Join | UPI payment QR codes are on every counter in India; scanning one must not look like a broken app | M | New | S | Common sight; no data |
| HD-1 | Desk | HR has no place to see how a phone joined, or to block it from the employee | H | New | M | Device list only in desk list view |
| HD-2 | Desk | The web page's device registration shows status but not "how it joined" | M | Improve | S | `alvoraa_field_device.json` has no join-method field |

## 5. The design in one paragraph

The app opens on one job: **Scan the QR code from HR**, with **Choose the QR picture from my
photos** under it. The camera is explained before Android asks. The server checks the code and the
person's eligibility first; only then does **Is this you? Suresh Y. · Driver · Kaveri Transport**
appear. **Yes** leads to the six-row notice; **Agree and finish** uses the code and sets up the
phone with no HR step. **Welcome, Suresh. This phone is set up. You do not need to wait for HR**
sits over a big **Check In**. Location is explained at that first Check In. From then on, the
Attendance screen is the web page's screen. Every failure is one screen with one sentence, steps
if needed, one or two buttons, and a short code for HR. HR works from the Employee record:
**Invite to the app** (show, print, copy picture, copy link), see **Joined 9:01 am today ·
Redmi 12 · by the QR code you made yesterday**, and **Block this phone**.

## 6. Flows, with every state

State names match the prototype switcher.

```
EMPLOYEE — JOIN
first ──Scan──> camExplain ──Continue──> osCam ──Allow──> scan ──code read──> checking
  │                                         └─Don't allow──> camDenied ──Choose a picture──┐
  └──Choose the QR picture──> (Android photo picker) ───────────────────────────────────────┤
                                                                                            v
checking ──(server checks, nothing used yet)──┬─ QR_EXPIRED / QR_USED / QR_CANCELLED ─> codeDead
                                              ├─ QR_NOT_ALVORAA (no server call) ─────> notAlvoraa
                                              ├─ QR_NOT_FOUND (picture) ──────────────> pickNoQr
                                              ├─ APP_OFF_FOR_FIELD ───────────────────> appOff
                                              ├─ NOT_FIELD_ROLE ──────────────────────> notField
                                              ├─ FEATURE_OFF ─────────────────────────> featureOff (008 screen)
                                              ├─ APP_TOO_OLD ─────────────────────────> update
                                              ├─ no internet ─────────────────────────> noSignalJoin ─Try again─> checking
                                              └─ ok ─> confirm
confirm ──Yes──> notice ──Agree and finish (code used here)──> joining ──> welcome ──Check In──> locExplain
   └──This is not me──> notMe ──Cancel this code──> notMeDone ──> first
                              └─Go back. It is me.──> confirm
notice ──no tick──> inline error, focus on the tick box
joining ──code used by someone in the meantime──> codeDead (QR_USED)

EMPLOYEE — EVERY DAY
home ──Check In (first time)──> locExplain ──> osLoc ──Allow──> punching ──> resultIn ──Done──> home (checked in)
                                                  └─Don't allow──> locDenied
home ──Check In / Check Out──> punching ──┬─ ok ──> resultIn / resultOut
                                          ├─ LOCATION_OFF / LOCATION_SLOW ─> locOff (Try again keeps photo)
                                          ├─ GPS_NOT_EXACT ─> gpsVague   (Try again keeps photo)
                                          ├─ OUTSIDE_WORKPLACE ─> outside (Try again keeps photo)
                                          ├─ no internet ─> noSignal     (Try again keeps photo)
                                          ├─ ALREADY_RECORDED ─> duplicate
                                          ├─ TOO_MANY_TRIES ─> tooMany
                                          ├─ SERVER_ERROR ─> serverError
                                          └─ unknown code ─> unknownCode (Check for an update)
camera refused or broken ─> home with camera-off panel; punch still counts, "Photo: Not taken"

ON OPENING THE APP (before home)
app version below minimum ─> update (nothing else reachable)
DEVICE_BLOCKED ─> blocked      DEVICE_REPLACED ─> replaced      EMPLOYEE_NOT_ACTIVE ─> left
APP_OFF_FOR_FIELD / NOT_FIELD_ROLE (changed after joining) ─> appOff / notField, with Remove
NOTICE_CHANGED ─> noticeAgain ─Agree and continue─> home

SETTINGS
home ─Settings─> settings ─> records
                         └─> leaveConfirm ─Remove this phone─> removed (first launch + one line)
                                          └─ no internet ─> "Connect to the internet to remove this phone. Nothing has changed."
```

```
HR — DESK
Employee (field worker) ─> empField ─Invite to the app─> inviteCreate ─Make the code─> inviteShow
inviteShow ─Print─> printSheet │ Copy picture │ Copy link │ Done─> empInvited
empInvited ─Cancel this code─> cancelConfirm ─> empField (history shows "Cancelled by …")
           ─Make a new code─> inviteCreate (warning: cancels the waiting one)
phone joins ─> empJoined ─Block this phone─> blockConfirm ─reason chosen─> empBlocked ─Invite─> inviteCreate
                                                         └─ no reason ─> inline error
Employee (not a field worker) ─> empNotField (no Invite button; reason + link to settings)
App switched off ─> empAppOff
Field App Settings ─> fieldSettings ─untick "can use the app"─> settingsOffConfirm ─Turn off─> empAppOff
All phones ─> deviceList
```

**Edge cases checked**

| Case | What happens |
|---|---|
| Long name ("Venkatanarasimha Raghavan") | "Is this you?" shows first name + initial; the top bar truncates with an ellipsis; the settings row wraps |
| Hindi runs ~30% longer | Checked at 360 px in Hindi: buttons wrap to two lines inside 60 px+ height; nothing overflows |
| Person stops half-way through joining | Nothing is used. Scanning the same code again starts over |
| Two people scan the same forwarded code | The first to press **Agree and finish** gets it; the second meets **QR_USED** at that moment |
| Code ran out while the notice was open | **QR_USED/QR_EXPIRED** screen at Agree; nothing saved |
| HR makes a second code | The first is cancelled at once (D17) |
| New phone joins with a new code | Old phone shows **replaced** at next open (D3) |
| Team of 400 at one depot at 9 am | Limits counted per phone (OPS-10); **tooMany** screen if hit |
| First launch with no internet | **noSignalJoin**; the notice is never shown with a blank "How long" row (MA-25) |
| Pilot test build, not from Play Store | **update** button opens the tester download link instead |

## 7. Employee app — screen by screen, exact words

English is the shipped wording. **Hindi for every screen is in the prototype, machine-drafted,
not for customers until a native speaker checks it** (D15).

Type scale: the 008 field scale (15 / 17 / 19 / 22 / 26–28 / 32–34 px). Nothing under 15 px in the
app. Theme: light pinned (D9). Colours: design-system tokens, tenant brand colour through
`brand_color.html` for the top bar and primary buttons.

### 7.1 First launch — `first`

- Top bar: **Alvoraa** · language switch **EN | हिं**
- Picture: QR symbol
- Heading: **Mark your attendance with this phone**
- Lead: Your HR team gives you a QR code. Scan it once to join your company.
- Body: You do not need an email address or a password.
- Small: No QR code yet? Ask HR to invite you to the Alvoraa app.
- Primary button (icon + words): **Scan the QR code from HR**
- Second button: **Choose the QR picture from my photos**

No employee-ID box and no company code (D18).

### 7.2 Camera, explained — `camExplain`

- Heading: **The app needs your camera to scan the code**
- Body: Next, your phone will ask if Alvoraa may take pictures. Press "While using the app".
- Card: The camera is used only when you scan a code, or when you press Check In or Check Out.
- Buttons: **Continue** · **Choose a picture instead**

Shown only if the camera has never been asked for. If already allowed, **Scan** opens the scanner.

### 7.3 Scanner — `scan`

- Full-screen camera, framed square. Text: **Point the camera at the QR code**
- Buttons: **Choose a picture instead** · **Cancel**
- The app reads codes only. A code that is not an Alvoraa link, or whose host is not
  `*.alvoraa.co` over HTTPS in a release build (OPS-7), goes to `notAlvoraa` **without any
  network call**.

### 7.4 Checking — `checking`

Busy overlay: **Checking the code**. The server confirms the code is live and the person is
eligible. **Nothing is used up.**

### 7.5 Is this you? — `confirm` (WOW, part 1)

- Heading: **Is this you?**
- Card: initials circle (no photo) · **Suresh Y.** · Driver · **Kaveri Transport**
- Small: HR made this code for one person only.
- Primary (green): **Yes, this is me** · Second: **This is not me**

Data shown: first name, surname initial, designation, company. Nothing else.

### 7.6 This is not me — `notMe`, `notMeDone`

Bottom sheet:
- Heading: **This code is for someone else**
- Nothing has been set up on this phone.
- If you cancel the code, it stops working. HR will see that it was cancelled on a phone, and can make a new one.
- Please tell HR the code came to you by mistake.
- Buttons: **Cancel this code** · **Go back. It is me.**

Then: **The code is cancelled** — Nothing was set up on this phone. If you are waiting for your own code, ask HR. **Done**

### 7.7 Notice — `notice`

- Top bar: Kaveri Transport · Suresh Y. · Driver · **Back**
- Heading: **Before you start**
- Body: Kaveri Transport asks you to read this. It says what the app records about you.
- Six rows (the web page's rows, two changed — FC-2, FC-3, D19):
  - **What we record** — A photo of you, where you are, and the time — only when you press Check In or Check Out. When you set up: this phone's model name.
  - **What we do not record** — Nothing between punches. You are not tracked while you work.
  - **Why** — To mark your attendance, and to confirm you were at your workplace.
  - **Who can see it** — HR and your manager. Not your colleagues.
  - **How long** — Photos are deleted after {days} days. Your attendance record is kept. (This is {company}'s setting.) · if 0: Photos are kept by your employer until they choose to remove them.
  - **Your rights** — Ask HR to see what was recorded about you, or to correct it.
- Tick box: **I have read this and I understand.** (not pre-ticked)
- Button: **Agree and finish**
- Error if not ticked (under the box, focus moves to the box): Please tick the box to show you have read the notice.
- Busy: **Setting up this phone**

### 7.8 Welcome — `welcome` (WOW, part 2)

- Heading: **Welcome, Suresh. This phone is set up.**
- Lead: You do not need to wait for HR. You can mark attendance now.
- Card: Company · Kaveri Transport / Your workplace · Okhla Depot / Check in within · 100 m
- Big green button: **Check In** · link: **Not now**

### 7.9 Attendance — `home`, `homeIn`, `homeOut`, `camOff`

Top bar: company name · person's name · **Settings** (gear + word).

| Part | Words |
|---|---|
| Status line, nothing yet | Not checked in yet today |
| Status line, in | Checked in since 9:02 am (green, dot + words) |
| Status line, out | **Checked out at 6:14 pm** (FC-1 fix) |
| Camera tag | Your photo is taken when you press the button |
| Camera off | The camera is off. You can still check in, but there will be no photo. **Turn on the camera** |
| Punch list | Today · 17 Sep / Checked in · This phone · 9:02 am / "No punches yet today." |
| Rule line | You need to be within 100 m of Okhla Depot |
| Button | **Check In** (green) / **Check Out** (purple, arrow flipped) |

### 7.10 Location, explained — `locExplain` (first Check In only)

- Heading: **The app needs your location to check you in**
- Body: Next, your phone will ask about location. Press "While using the app", and keep "Precise" on.
- Card: Your location is read only at the moment you press Check In or Check Out. Never in between.
- Button: **Continue**

Only "while using the app" is ever requested in step 1.

### 7.11 Saving and result — `punching`, `resultIn`, `resultOut`

Busy, one at a time: **Taking your photo** → **Finding where you are** → **Saving your attendance**.
Result: saved photo with tick (or a tick circle if no photo) · **Checked in** · **9:02 am** ·
Thursday, 17 September · card: Where you were · At Okhla Depot / Photo · Taken (or Not taken +
"The camera was not on. Your attendance still counts.") / Saved · In your HR record · small:
**Only HR and your manager can see this.** · **Done**

### 7.12 Problem screens

Every one: icon in a circle (colour **and** icon **and** words), heading, one or two sentences,
numbered steps where the person must do something on the phone, one or two buttons, and
**Code for HR: {CODE}** in small text at the bottom.

| State | Heading | Body | Buttons | Code |
|---|---|---|---|---|
| `qrExpired` | This code cannot be used any more | It ran out on {weekday} {date} at {time}. HR's codes work for a limited time. + steps: 1 Ask HR for a new code. 2 Scan the new code with this app. | Scan a new code · Done | QR_EXPIRED |
| `qrUsed` | same | It was already used {today / on date} at {time}. Each code works once. If that was not you, tell HR today. + same steps | same | QR_USED |
| `qrCancelled` | same | HR cancelled it. They may have made a newer one for you. + same steps | same | QR_CANCELLED |
| `notAlvoraa` | This is not an Alvoraa code | It may be a payment code or a website link. Scan the code HR gave you for this app. Nothing was sent anywhere. | Scan again · Choose a picture instead | QR_NOT_ALVORAA |
| `pickNoQr` | No QR code found in that picture | Choose the picture HR sent you. A small code is fine, but it must not be cut off. | Choose another picture · Scan with the camera | QR_NOT_FOUND |
| `appOff` | The app is not switched on for field staff | {Company} has not turned on the app for field staff. Nothing was set up on this phone. Keep marking attendance the way you do now. HR can tell you more. | Done | APP_OFF_FOR_FIELD |
| `notField` | This app is not for your job yet | In HR's records your job is {designation}. For now the app is only for field staff, such as drivers and guards. Keep marking attendance the usual way. If your job is wrong in the records, tell HR. | Done | NOT_FIELD_ROLE |
| `noSignalJoin` | No internet | The app needs the internet to check your code and finish setting up. Nothing has been saved yet. Move to a place with signal and press Try again. | Try again · Go back | NO_INTERNET |
| `camDenied` | The camera is off for this app | You said no to the camera. You can still join: choose the QR picture from your photos. Or turn the camera on. + steps: Press Open phone settings. / Press Permissions, then Camera. / Press "Allow only while using the app", then come back. | Choose a picture instead · Open phone settings | CAMERA_DENIED |
| `locDenied` | This app cannot see your location | You said no to location. Attendance needs it. Allow location for Alvoraa, then press Check In again. + steps: Press Open phone settings. / Press Permissions, then Location. / Press "Allow only while using the app". Keep "Use precise location" on. | Open phone settings · Go back | LOCATION_DENIED |
| `locOff` | Location is off | (008 wording) + swipe-down steps | Try again · Go back | LOCATION_OFF |
| `gpsVague` | Your location is not exact enough | Your phone can only place you within about {accuracy} m. It needs to be within {limit} m. Step outside or away from buildings, wait a few seconds, and press Try again. · Your photo is kept. You will not need to take it again. | Try again · Go back | GPS_NOT_EXACT |
| `outside` | You are too far from work | You are about {distance} m from {site}. You need to be within {radius} m to check in. Walk closer and press Try again. Nothing has been saved. · photo kept | Try again · Go back | OUTSIDE_WORKPLACE |
| `noSignal` | No internet | Your attendance has not been saved yet. Move to a place with signal and press Try again. · photo kept | Try again · Go back | NO_INTERNET |
| `duplicate` | That is already recorded | You pressed the button twice. Your check-in at {time} is saved. There is nothing more to do. | Done | ALREADY_RECORDED |
| `tooMany` | Too many tries | This phone tried many times in a short time. Wait one minute, then press Try again. · photo kept | Try again · Go back | TOO_MANY_TRIES |
| `update` | Update the app to keep marking attendance | This version of Alvoraa is too old to work with {company} any more. Updating takes about a minute on Wi-Fi. Card: On this phone {ver} / Needed {min} or newer. Green card: You stay set up. You will not need a new code. Attendance you marked before is safe. | **Update in Play Store** (only button) | APP_TOO_OLD |
| `blocked` | This phone has been stopped | HR has stopped this phone. It cannot mark attendance for you any more. Please speak to HR. Card: Attendance you already marked is safe in your HR record. If you have a new phone, HR can give you a new code. | Remove {company} from this phone | DEVICE_BLOCKED |
| `replaced` | You joined on another phone | {Today at time / On date} you joined {company} on another phone. Use that phone to mark attendance. If that was not you, tell HR today. | Remove {company} from this phone | DEVICE_REPLACED |
| `left` | You cannot mark attendance here | Your employee record at {company} is not active any more. If that is wrong, please speak to HR. | Remove {company} from this phone | EMPLOYEE_NOT_ACTIVE |
| `serverError` | Something went wrong | Your attendance was not saved. Press Try again. If it keeps happening, show this screen to HR. Card: For HR · SERVER_ERROR / When · {date, time} / App · {ver} · Android | Try again · Go back | SERVER_ERROR |
| `unknownCode` | Something went wrong | Your attendance was not saved. This app may be out of date. Check for an update, then try again. Card: For HR · {code} / This version does not know this code yet. / App · {ver} | Check for an update · Try again | (as sent) |
| `noticeAgain` | The notice has changed | Please read it again before your next check-in. What is new: {one line from the server}. Six rows, tick box. | Agree and continue | NOTICE_CHANGED |
| `featureOff` | This app is not switched on for your company | (008 wording) | Done | FEATURE_OFF |

Screens **blocked**, **replaced**, **left** and **update** hide Check In entirely. Settings stays
reachable from the top bar.

### 7.13 Settings — `settings`, `records`, `leaveConfirm`

**Settings** (top bar: **Back** · Settings)

| Group | Rows |
|---|---|
| You | {Full name} / {designation} · Company · {company} · Workplace · {site} / Check in within {radius} m |
| Language | ◉ English ○ हिंदी (radio rows, 56 px) |
| Privacy | **What this app records** › / You agreed on {date} |
| This phone | **Remove this phone from {company}** › / Attendance on this phone stops |
| About | App version · {ver} ({build}) · Connected to · {host} · Joined · {date, time} · Help / For any problem, speak to HR. Tell them the app version above. |

No "Sign out": there is no password to sign out of. **What this app records** shows the six rows, then:
"You agreed on {weekday} {date} at {time}. Notice version {version}." and "If this notice changes,
the app asks you to read it again before your next check-in."

**Remove this phone?** (bottom sheet)
- Heading: **Remove this phone from {company}?**
- This phone stops marking attendance for you.
- Attendance you already marked stays in your HR record.
- Photos already taken are deleted after {days} days, as the notice says.
- HR will see that you removed this phone.
- To use the app again, you need a new code from HR.
- Small: You need the internet for this.
- Buttons: **Remove this phone** (red) · **Keep it**
- After: first launch with one line, "This phone is no longer linked to {company}."
- No internet: "Connect to the internet to remove this phone. Nothing has changed." (D10)

## 8. Error codes — the contract the app depends on

The server sends `{code, values}`; the app picks the screen by `code` and fills numbers from
`values`. The English sentence may still be sent for logs, but the app never matches on it.

| Code | Sent by | Values | Retry? |
|---|---|---|---|
| QR_EXPIRED | check, redeem | expired_at | No |
| QR_USED | check, redeem | used_at | No |
| QR_CANCELLED | check, redeem | — | No |
| APP_OFF_FOR_FIELD | check, redeem, status, punch | — | No |
| NOT_FIELD_ROLE | check, redeem, status, punch | designation | No |
| FEATURE_OFF | any | — | No |
| NOTICE_CHANGED | redeem, status, punch | version, retention_days, what_changed | Agree |
| APP_TOO_OLD | any (or `app_config.min_version`) | min_version | Update only |
| NOT_SET_UP | status, punch | — | → first launch |
| DEVICE_BLOCKED | status, punch | — | No |
| DEVICE_REPLACED | status, punch | replaced_at | No |
| EMPLOYEE_NOT_ACTIVE | redeem, status, punch | — | No |
| GPS_NOT_EXACT | punch | accuracy_m, limit_m | Yes, photo kept |
| OUTSIDE_WORKPLACE | punch | distance_m (may be empty), site, radius_m | Yes, photo kept |
| ALREADY_RECORDED | punch | time | No |
| TOO_MANY_TRIES | any | retry_after_s | Yes |
| SERVER_ERROR | any | — | Yes |
| QR_NOT_ALVORAA, QR_NOT_FOUND, NO_INTERNET, CAMERA_DENIED, LOCATION_DENIED, LOCATION_OFF, LOCATION_SLOW | **the app itself** | — | as §7.12 |

Any code the app does not know → `unknownCode`. `OUTSIDE_WORKPLACE` with no distance uses the
server's other sentence today: "You are too far from {site} to check in."

## 9. HR in the desk — screen by screen

A sketch of a Frappe desk form. **Frappe-first:** a section on the Employee form (Attendance &
Leaves tab), a dialog (`frappe.ui.Dialog`), a Single doctype for settings, a list view for phones.
No custom page needed. The engineer chooses the exact Frappe pieces.

### 9.1 Section "Field attendance app" on the Employee

Sub-heading: The Alvoraa phone app for field workers: photo check-in with place and time.

| State | Status line | Actions |
|---|---|---|
| Field worker, no phone (`empField`) | **Not joined yet.** {First name} can use the app: **{designation}** is a field worker designation. | **Invite to the app** |
| Code waiting (`empInvited`) | [Code waiting] Made by {you / name} today at 10:05 am. Works until **Thu 24 Sep 2026, 10:05 am** (in 7 days). · hint: This code cannot be shown again. If {first name} lost it, make a new one. That cancels this one. | Make a new code · Cancel this code |
| Joined (`empJoined`) | [Joined] **Joined 9:01 am today · Redmi 12 · by the QR code {you / Anita Rao} made yesterday** · Last check-in 9:02 am today at Okhla Depot. | Invite to the app again |
| Blocked (`empBlocked`) | [No working phone] Redmi 12 was blocked today at 11:40 am by {you / name} · {reason}. | **Invite to the app** |
| Not a field worker (`empNotField`) | **The app is not available for {full name}.** Designation **{designation}** is not a field worker designation. · {First name} marks attendance at the reception machine, or with Check In in the portal. | link: Change field worker designations |
| App switched off (`empAppOff`) | [App switched off] Field workers cannot use the app at the moment. You cannot make codes. · {First name} can still use the web check-in page at {host}/checkin. | link: Open Field App Settings |
| Plan has no field check-in | Field check-in is not part of your plan. | none (no Invite button) |

Wording uses the person's name, never "he" or "she".

**Phones table:** Phone (model / Android · app version) · How it joined ("QR code made by {you /
name}, {date}" or "Web check-in page, approved by {name}, {date}") · Joined · Last check-in (time,
place) · Status (dot + word: Active, Waiting for HR, Blocked, Replaced, Removed, Stopped) ·
**Block this phone**. A web-page phone of a non-field worker shows an extra pill **Not a field
worker** / "Joined before this rule. Keeps working." (brief Q4 default).

**App codes history:** when made · who made it and lifetime · outcome pill: Waiting to be used ·
until {date} / Used {date, time} on {phone} / Cancelled by {name}, {date} / Cancelled on a phone:
"This is not me", {date} / Ran out {date}.

### 9.2 Invite dialog — `inviteCreate`, `inviteShow`, `printSheet`

**Step 1: Invite {full name} to the app**
- This makes a QR code that only {first name} can use, once. When {first name} scans it with the Alvoraa app and confirms the name, the phone is set up straight away. **You do not need to approve it.**
- Field: **The code works for** — 1 hour / 4 hours / 1 day / 3 days / 7 days (your organisation's setting). Options above the setting are not offered (D6).
- Hint: You can choose a shorter time than your organisation's setting, not a longer one. Shorter is safer.
- If a code is waiting (amber): {First name} already has a code waiting to be used. Making a new code cancels it.
- If a phone is active (grey): Use this when {first name} changes phone. When the new phone joins, {phone} stops working.
- Buttons: Cancel · **Make the code**

**Step 2: App code for {full name}**
- QR picture · [Waiting to be used] · **Works once.** · Works until **{date, time}** ({in N days}). · Made by {you} today at {time}.
- **Tell {first name}:** 1 Install **Alvoraa** from the Play Store. 2 Open it and press **Scan the QR code from HR**. 3 Check the name and press **Yes, this is me**.
- Amber, bold: **Anyone who has this code or link can join as {first name} until it is used.** Give it only to {first name}. If it goes to the wrong person, cancel it.
- Grey: You can see this code only now. If it is lost, make a new one.
- Buttons: Print · Copy picture · Copy link · **Done**
- After copy: "Picture copied. Paste it in WhatsApp to {first name}." / "Link copied. Send it only to {first name}."

**Printed sheet (one A4):** company · **Your Alvoraa app code** · For **{full name}** · {designation} ·
QR · three steps in English, then Hindi · "This code works **once**, until **{date, time}**. Do not
share it. If this sheet is lost, tell HR." **No employee ID** (D14).

### 9.3 Block — `blockConfirm`

- Title: **Block {phone}?**
- {First name} cannot mark attendance on this phone from now on.
- Attendance already marked stays.
- The phone will say: "This phone has been stopped. Please speak to HR."
- **This cannot be undone.** If {first name} gets the phone back, make a new code. (D4)
- Field (required): **Why are you blocking it?** — Phone lost or stolen / Has a new phone / Someone else was using it / Left the company / Other
- Hint: Kept in the record. {First name} does not see the reason.
- Error: Choose a reason. It is kept in the record. (D7)
- Buttons: Keep it working · **Block this phone** (red)

### 9.4 Field App Settings — `fieldSettings`, `settingsOffConfirm`

| Section | Field | Words |
|---|---|---|
| Who is a field worker | Field worker designations (multi-select of Designation) | Only people with these designations can get the app and check in with a photo. · live count: "42 active employees have these designations." |
| The app | ☑ **Field workers can use the app** (default on) | When this is off, you cannot make codes, and phones that joined stop marking attendance. Field workers can still use the web check-in page. |
| | **App codes work for** — 1 hour, 4 hours, 12 hours, 1 day, 3 days, **7 days (default)** | From 1 hour to 7 days. Shorter is safer. Longer is easier when you hand out printed codes before a joining day. HR can choose a shorter time for one code. |
| Photos (read only) | — | Check-in photos are kept for **90 days**, then deleted. Change this in Org Settings › Field check-in. |
| Change history | who, when, old → new | HR cannot change this list. Only the Administrator account can delete from it. |

**Turn off the app for field workers?**
- You will not be able to make new codes.
- **{n} codes** waiting to be used will stop working.
- **{n} phones** that joined will stop marking attendance. They will say: "The app is not switched on for field staff."
- Field workers can still use the web check-in page.
- Field (required): Why? (kept in the change history)
- Buttons: Keep it on · **Turn off** (red)

Removing a designation shows the same kind of confirm with its own counts (not drawn).

**Who may change these settings: ⚠ D20** — recommendation: HR Manager, with every change in
the history.

### 9.5 All app phones — `deviceList`

List view of the device doctype with: Employee · Phone · How it joined · Joined · Status (+ reason
or date). Default filter "Joined in the last 7 days". **No "last seen", "online now" or map**, by
design (hint under the table says so).

## 10. Accessibility and privacy

**WCAG 2.2 AA (nfr-budget §7)**

| Check | How the design meets it |
|---|---|
| 1.4.3 contrast | Token colours; white on `--primary-d` and `--green`; tenant colour clamped by `brand_color.html` |
| 1.4.1 colour not alone | Every status has a dot **and** words; every problem screen has an icon **and** heading |
| 1.4.4 / 1.4.10 resize, reflow | Measured at 360 px, no sideways scroll, in English and Hindi |
| 2.5.8 target size | Measured: nothing under 44 px (app buttons 60 px, punch 96 px) |
| 3.3.1 / 3.3.3 errors | Notice tick error under the box, `role="alert"`, focus moves to the box; block reason error the same |
| 4.1.2 name, role, value | Labelled inputs, `role="dialog"` with heading, `aria-current` on tabs, radio group for language |
| 2.4.7 focus visible | 3 px focus outline everywhere |
| 3.1.2 language of parts | `lang="hi"` on Hindi strings |
| 2.3.3 motion | Spinner slows under reduced motion |
| Frontline | Field text ≥ 16 px (app base 17 px) |

**Privacy — who sees what**

| Screen | Who | Least needed? |
|---|---|---|
| Is this you? | Whoever holds the code | First name, initial, designation, company only. HR gave it to that person anyway |
| QR_USED screen | Whoever holds the code | Time used, no phone model (D8) |
| Result screen | The employee | Their own photo; says who else can see it |
| Employee section, phones table | HR with Employee access | Phone model, how joined, dates, status. No location history, no "last seen" |
| Block reason | HR | Never shown to the employee |
| Printed sheet | The employee | Name + designation; no employee ID |
| Error code card | The employee, shown to HR | Code, time, app version. No token, no employee ID |
| All app phones list | HR | No map, no online status, no ranking |

Refusals checked (product-context §6): no face matching, no tracking between punches, no
manager view of one person's movements, no pre-ticked consent, no nagging (the update screen
appears only when the version truly cannot work; no "newer version available" pop-ups).

## 11. Decisions for you

Each has my recommendation. The prototype shows the recommended one unless it has a switch.

| # | ⚠ DECISION | Options | My recommendation | Owner | Blocks |
|---|---|---|---|---|---|
| D1 | App frame in step 1 | A: no bottom bar, labelled Settings in the top bar · B: bottom bar "Attendance · Settings" · C: bottom bar with a greyed "My HR" | **A.** One-tab bars are decoration; greyed tabs are a known anti-pattern; the camera needs the height. Add the bar with My HR. Switch in the prototype | Surbhi | Shell build |
| D2 | What "This is not me" does | Cancel the code (after a confirm) · leave the code working | **Cancel it.** A code in the wrong hands should die at once. Cost: someone who taps it by mistake needs a new code. HR sees why | Surbhi, security | Redeem endpoint |
| D3 | A second phone joins with a new code | New phone replaces the old one (old shows "You joined on another phone") · both stay active | **Replace.** One working phone per person; a stolen old phone stops without HR noticing it | Surbhi, security | Device model |
| D4 | Can HR unblock an app phone? | No, make a new code · Yes, unblock | **No.** A blocked phone may be in someone else's hands; a new code proves the person again | Surbhi, security | Desk actions |
| D5 | App switched off, or designation no longer a field worker, for phones that already joined | Stop them (confirm shows counts) · let them keep working | **Stop them.** Your rule is "photo check-in applies to field workers only". Web-page phones set up before this rule keep working, as the brief says | Surbhi | Server checks, desk confirm |
| D6 | Lifetime per code | Org setting only · HR may pick shorter for one code | **Shorter allowed, never longer.** A 1-hour code for someone standing in front of HR is safer | Surbhi | Invite dialog |
| D7 | Block reason | Required · optional · none | **Required**, short list, never shown to the employee | Surbhi | Desk dialog |
| D8 | Used-code screen tells when it was used | Show time · say nothing | **Show the time.** The real owner can tell HR "that was not me" the same day. Security to confirm it helps no attacker | Security | QR_USED values |
| D9 | App theme | Pinned light (008 D1) · follow the phone's dark mode | **Pinned light** for step 1: sunlight on cheap screens. Toggle in the prototype | Surbhi | Shell build |
| D10 | Remove this phone with no internet | Needs internet · remove on the phone and tell the server later | **Needs internet.** Simpler and honest; the next join replaces it anyway (D3) | Surbhi | Settings |
| D11 | Code for HR on problem screens | On every problem screen · only on server errors | **Every screen**, small, at the bottom. HR support calls start with "what does it say at the bottom?" | Surbhi | All problem screens |
| D13 | Wording of the joined line | Brief: "by QR you issued yesterday" · "by the QR code you made yesterday", name when the reader is not the maker | **Second.** "Issued" is office English; "you" is untrue for any other HR person. Switch in the prototype | Surbhi | Desk wording |
| D14 | Printed sheet content | Name + designation · add employee ID | **No employee ID.** The sheet may be left on a desk | Surbhi | Print format |
| D15 | Hindi in the pilot | English only until a native check · ship the drafts | **English only** until checked; the switch stays hidden in pilot builds | Surbhi | Pilot build |
| D17 | One waiting code per person | Making a new code cancels the old · several can be live | **One at a time.** Fewer stray codes | Surbhi, security | Invite |
| D18 | Employee-ID join in the app | None (QR only) · keep the web page's employee-ID path in the app too | **None.** The web page keeps it (brief). Two joins in one app need two explanations | Surbhi | First launch |
| D19 | Notice change | New notice wording (phone model name; "manager" everywhere) with a new version and the "notice has changed" screen · leave the notice as is | **Change it now**, before any pilot user agrees to the old words | Surbhi, compliance owner | Consent version |
| D20 | Who may change Field App Settings | HR Manager · System Manager only | **HR Manager**, with the change history. Not a privacy threshold like 012's | Surbhi | Settings permissions |

(D12 and D16 were folded into the design; numbers kept so the prototype's references line up.)

## 12. Checks before handoff

**Nielsen's heuristics, where they apply**

| Heuristic | Line |
|---|---|
| Visibility of status | Status line with words; busy messages name the step; HR sees "Code waiting / Joined / Blocked" |
| Match with the real world | "QR code from HR", "This phone", "made the code", not "enrolment token" or "device" |
| User control | "This is not me", "Go back. It is me.", "Keep it", "Not now" |
| Consistency | Every problem screen has the same shape; one word each for manager, code, phone |
| Error prevention | Eligibility checked before the name; confirm before cancel, block, remove, switch off |
| Recognition over recall | No IDs to type; the next step is on the screen |
| Flexibility | Scan or picture; copy picture or link or print |
| Minimal design | One primary action per screen |
| Recover from errors | Plain cause, what to do, photo kept, code for HR |
| Help | "For any problem, speak to HR. Tell them the app version above." |

**Persona walkthrough — top task, steps before and after**

| Persona | Task | Today (web page) | After |
|---|---|---|---|
| Field employee | Join and first check-in | Open link, type ID, tick, set up, **wait for HR** (hours), add to home screen (3 steps), check in | Scan, Yes, tick, Agree, Check In, Continue, Allow ≈ **7 taps, no wait** |
| Field employee | Daily check-in | Open, Check In | Open, Check In (same) |
| HR Manager | Get a new driver working | Find pending device in desk list, open, set Active | Employee › Invite › Make the code › Copy picture (then nothing) |
| HR Manager | Lost phone | Find device in list, set Blocked | Employee › Block this phone › reason › Block |

**Frontline bar — two minutes on a phone?** Yes for joining with signal: about seven taps and one
short read. Honest risks: reading the notice in a second language, and Android's location dialog
wording differing by maker. The usability test times it.

**Plain-language test.** Every screen reads without knowing Alvoraa. Two words to watch in testing:
"notice" and "code for HR".

## 13. Usability test plan (High-impact screens: join and daily check-in)

- **Who:** 5 people — 3 drivers or guards who have never used a work app (1 Hindi-only), 1 store
  employee, 1 HR person. Their own or a pilot low-end Android phone.
- **Tasks**
  1. "HR sent this picture on WhatsApp. Set up the app." (success: welcome screen, no help, ≤ 2 min)
  2. "Mark that you have arrived." (success: result screen ≤ 30 s, including the location dialog)
  3. Given a code for someone else: "Set up the app." (success: taps "This is not me")
  4. Given a used code: "What would you do now?" (success: says "ask HR for a new code")
  5. Standing 150 m away: "Check in." (success: understands to walk closer, does not retake the photo)
  6. HR: "Give Suresh the app, then pretend he lost his phone." (success: both done from the Employee, ≤ 90 s)
- **What would change the design**
  - 2 of 5 do not notice "Choose the QR picture" → make it a full-width primary when the app opens from a share.
  - 2 of 5 press **Yes** on someone else's name → add the last digits of the employee ID to "Is this you?".
  - 2 of 5 stall at Android's location dialog → add a picture of the dialog to `locExplain`.
  - Anyone reads "Code for HR" as something to type → move it into a "For HR" card only on server errors (D11).

## 14. What the business analyst must turn into acceptance criteria

1. The code is checked (live, eligible, plan) **before** any name is shown; nothing is used until **Agree and finish**.
2. "Is this you?" shows only first name, surname initial, designation, company.
3. Redeeming activates the phone with no Pending step; the notice version and time are stored.
4. Every server refusal carries a `code` and `values` (§8); the app never matches English text; unknown codes show `unknownCode`.
5. `app_config` returns a minimum version; below it, only the **update** screen is reachable; pilot builds open the tester link.
6. Notice version change → `NOTICE_CHANGED` → the notice is shown again before the next punch.
7. FC-1: after a check-out the status line says "Checked out at {time}".
8. FC-2 and FC-3: "manager" in both places; the notice mentions the phone's model name (new version).
9. Camera explained before the first scan; location explained before the first punch; only "while using the app" is requested.
10. A code for a host other than `*.alvoraa.co` over HTTPS (release build) goes to `notAlvoraa` with no network call.
11. Photo is kept across Try again for GPS, distance, signal and rate-limit refusals.
12. Blocked, replaced, left, app-off and not-field phones show their screen on opening and never show Check In.
13. Remove this phone: needs internet; server marks the phone "Removed by employee"; HR sees it; the phone returns to first launch.
14. Desk: Invite dialog offers lifetimes up to the organisation setting only; making a new code cancels a waiting one; the code picture is shown once and never again.
15. Desk: the joined line says "you" only when the reader made the code.
16. Desk: Block needs a reason; the reason is never sent to the phone; block cannot be undone (D4).
17. Desk: no Invite button for a non-field designation, when the app is off, or when the plan lacks field check-in; each shows its plain reason.
18. Settings off / designation removed: confirm shows live counts of waiting codes and joined phones; a reason is required; the change is in the history.
19. No "last seen", "online now" or map anywhere HR looks.
20. The code history records: made (who, lifetime), used (when, which phone), cancelled by HR, cancelled on a phone ("This is not me"), ran out.
21. Every screen passes at 360 px in English and Hindi: no sideways scroll, targets ≥ 44 px, text ≥ 15 px in the app.

## 15. The prototype

**File:** `C:/Surbhi-Git/hr-app/docs/slices/013-mobile-app/prototype-v1/index.html` — one
self-contained file, invented data only ("Kaveri Transport", "Suresh Yadav", "Anita Rao"). Only
outside request: Google Fonts, with system fonts as fallback. **Not published yet — the lead
session publishes it and adds the link here.**

**How to review**
- Top panel (not part of the product): **Phone app / HR desk**, language, page theme, phone
  width 390 / 360, **App frame A / B / C** (D1), "App follows dark mode" (D9), and on the desk
  **HR person looking** (D13).
- Row of buttons: jump to any of the **47 phone screens** or **14 desk screens**.
- Or click through for real: First launch › Scan › Continue › While using the app › press the
  square › Yes › tick › Agree › Check In › Continue › While using the app › Done › Check Out.
- The panel beside the phone says what each screen shows and which decision it belongs to.

**Not in the prototype:** iPhone screens; Android's photo picker (we hand off to the system);
the store listing; the "remove a designation" confirm (described in §9.4); the plan-has-no-field-
check-in desk state (described in §9.1); the phone's `featureOff` screen (unchanged from 008).

---

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | D1–D20 above | Surbhi (D2, D3, D4, D8, D17 with security) | Design check |
| 2 | Does security's design (`01c`) add any step to joining (PIN, shorter default, second confirmation)? | Security engineer | Join flow |
| 3 | Is "phone model name" the right and only new item for the notice, and is the legal basis consent or legitimate use? | Compliance owner (founder to name) | Notice wording (D19) |
| 4 | Where do "Removed by employee", "Replaced" and "Stopped: app switched off" live — new statuses on the device, or a separate field? | Engineer | §9.1 status words |
| 5 | Current-state capture on the bench at 390 × 844, still owed from `01a` | Designer, when the bench is free | Nothing in this design; confirms FC-1 on screen |
| 6 | Android permission dialog wording on the three pilot phones | Engineer / tester | `camExplain`, `locExplain` wording |

## Assumptions

- [ASSUMPTION] Security accepts the join controls in the brief; the screens change if not.
- [ASSUMPTION] The server can check a code's eligibility without using it (a "peek" call before redeem).
- [ASSUMPTION] Capacitor can open the app's own Android permission settings page ("Open phone settings").
- [ASSUMPTION] Android's system photo picker needs no storage permission on the pilot phones.
- [ASSUMPTION] Field workers rarely have dark mode on and read the screen outdoors (D9).
- [ASSUMPTION] "Kaveri Transport", every person, phone count and date in the prototype are invented.
- [ASSUMPTION] Hindi strings are machine drafts; none has been checked by a native speaker.

## Handoff note

To the security engineer and then the business analyst: the design keeps the web page's
check-in screen and adds the doorway in front of it. **Watch three things.** First, the code must
be checkable without being used, and used only at "Agree and finish" — this is what stops people
reading a notice for a join that cannot work, and it is also where a race between two scanners is
decided. Second, the app is driven by the error codes in §8; if the server keeps sending only
sentences, every screen in §7.12 falls back to "Something went wrong". Third, D2, D3, D4 and D8 are
security-shaped choices I have made from the person's point of view; please challenge them in
`01c` rather than letting them pass by default. **One mild disagreement with the brief:** its
joined-line wording ("by QR you issued yesterday") is untrue for any HR person other than the
issuer, so I changed it (D13). I also changed two notice lines (D19), which needs a new consent
version — please do not build against `CONSENT_VERSION = "2026-09-13"`. I did not look at the real
product in this run; nothing in the design depends on it, but FC-1 should be confirmed on screen.


---

**Published prototype (2026-09-17):** https://claude.ai/artifact/XmykPG1vosM1US4iidyFFz (version 1, private).

## Design check decision (2026-09-17)

**Design agreed with prototype v1** (https://claude.ai/artifact/XmykPG1vosM1US4iidyFFz, version 1). Surbhi reviewed the prototype and accepted the designer's recommendations for every ⚠ DECISION (D1–D20). D2, D3, D4, D8 and D17 still go to the security engineer to confirm or challenge in `01c`; D19 (notice change) to the compliance owner when named.

**QR lifetime (Surbhi, 2026-09-17):** default **24 hours**, organisation may set up to 7 days (security's recommendation in `01c`).
