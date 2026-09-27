---
slice: 013-mobile-app
artifact: 01d-ux-redesign-m3
author: hrms-ux-designer
date: 2026-09-27
status: draft — round 1, for Surbhi to click through
inputs: [01b-ux-design.md (incl. design check 2026-09-17), 03-implementation-notes-alv128-password-signin.md (incl. design change 26 Sep), mobile/field-app/web/index.html, css/app.css, js/join-screens.js, js/checkin-screens.js, js/checkin.js, js/join.js, js/signin-core.js, alvoraa_portal/field_app_notice.py, field_app_join.py, field_checkin.py, templates/includes/design_system.html, templates/includes/brand_color.html, .claude/context/ux-learnings.md, nfr-budget.md §2 §7, handoff-contract.md]
---

# 013 · Field app redesign on Material 3 — design note

**I recommend. You decide.** Open the prototype, click through, then say go, change or drop.

**Prototype:** `docs/slices/013-mobile-app/prototype-mobile-m3.html` (one file, sample data only).
A copy is at `C:/Surbhi-Git/hrlocal-data/prototypes/013-mobile-app/prototype-mobile-m3-v1.html`.
**I could not publish a link from here — the lead session publishes it.**

## Read this first

**Bad news first.**

1. **I did not see your phone screenshots.** I worked from your description of them and from
   the app's code on `origin/dev` (6411f73). I did not run the app on a phone.
2. **The app does not show the company's brand colour today.** (Fact: no file in
   `web/js/` reads a brand colour.) Only the QR "check this code" answer carries
   `brand_colour`; the password sign-in answer and the daily status answer do not. The
   design needs one small server change: send `brand_colour` in both (§8).
3. **PP Jewellers' brand colour on the local copy is black (`#000000`).** Material's usual
   colour recipe turns black into **pink** (I measured it: primary `#8c4a60`). The design
   switches to Material's grey ("monochrome") recipe when a brand colour has almost no
   colour in it. Without this rule, PPJ staff would get a pink app (D-M3-5).
4. **Dark theme reopens a decision you agreed on 17 Sep** (D9: "pinned light, for sunlight").
   The prototype has both themes because you asked for them. My recommendation is to follow
   the phone's own setting (D-M3-1).
5. **"Agree always reachable" changes how the notice is read.** Today a person must scroll
   past all six parts to reach the tick box. With the tick box fixed at the bottom, they can
   agree without scrolling. The words do not change. Security / compliance should confirm this
   is fine (D-M3-4).
6. **"Withdraw agreement" has a server endpoint but no screen in the app.** (Fact:
   `field_app_join.withdraw_agreement` exists; `index.html` has no button for it.) I designed
   the screen. It is new work for the engineer, not a restyle.

**The four biggest design decisions**

| # | Decision | Why |
|---|---|---|
| 1 | **One big action per screen, in the bottom half.** Check In / Check Out is a 96 px Material 3 "large" button fixed at the bottom; every other main action is a 56 px "medium" button there too. | One-handed use in a shop or on a site. Today every button is the same 60 px blue block, so nothing stands out. |
| 2 | **A status card answers "where do I stand?" at a glance** — colour, icon **and** words ("Checked in since 9:12 am"), with the check-in rule inside it. | Today the status is one bold line among others. |
| 3 | **The notice becomes six labelled parts with an icon each**, words unchanged, with the tick box and Agree fixed at the bottom. | Today it is a wall of text with a small tick box at the end. |
| 4 | **Hand-written CSS on Material 3 tokens, no component library.** Colour made from the tenant's brand colour with Google's own colour code, vendored. | Keeps the plain-JS app, the strict content-security rule and cheap phones fast. `@material/web` is in maintenance mode and would add 173 KB. |

---

## 1. Frame

**Who, when, where, what.** A shop or field worker (PP Jewellers store staff, Sargam Metals
workers) or an office employee, on a cheap Android phone, often outdoors and in a hurry, often
not confident in English, wants to check in or out in one tap and be sure it worked. Once, on
day one, they sign in or scan HR's code and agree to the notice.

| Persona | What changes |
|---|---|
| **Employee (frontline and office)** | Every screen is redesigned. Same steps, same words (except where §7 says "new words"). Status is clearer; the result shows the true location and how exact it was. A new "Stop agreeing" choice in Settings. |
| **HR Manager** | Nothing on the desk. Fewer "did it work?" questions, because the result screen says where and how exact. The "Code for HR" line stays on every problem screen. |
| **CXO** | Nothing visible. Punches land in Frappe HR as today. |

**One-way rule check.** Nothing here helps a manager at the employee's cost. The result screen
shows the person their own location; nothing new is shown to anyone else.

**Out of scope:** the HR desk screens, iPhone, the My HR tab, Hindi and Punjabi copy (only a
machine-drafted Hindi sample on Home and check-in, to test length).

## 2. Evidence

| What | Source | Label |
|---|---|---|
| Today's screens and words | `web/index.html`, `css/app.css` (70 lines), `join-screens.js`, `checkin-screens.js`, `checkin.js`, `signin-core.js` on `origin/dev` | Fact (read) |
| The notice's exact words, version 2026-09-22 | `alvoraa_portal/field_app_notice.py` | Fact (read) |
| The server's refusal values (`distance_m`, `accuracy_m`, `limit_m`, `radius_m`) | `field_checkin.py` | Fact (read) |
| Brand colour handling | `brand_color.html`, `field_app_join.py` (`brand_colour` in the code check only) | Fact (read) |
| PPJ's brand colour | `site_config.json` on the local bench, read only: `"primary_color": "#000000"` | Fact (read) |
| Material palettes and contrast | Generated with `@material/material-color-utilities` 0.3.0; contrast computed | Fact (measured) |
| Bundle sizes | esbuild, minified + gzip, 27 Sep 2026 (§9) | Fact (measured) |
| Your screenshots | Your description in the task | I did not see them |

Screens of the prototype, measured at 360 px in light, dark and 200% text: in
`C:/Surbhi-Git/hrlocal-data/ux-review/2026-09-27/` (outside the repo).

## 3. Benchmark — what I took from each

Labels: **read** = a product or help page read on 27 Sep 2026 (search summaries, not product
screenshots). `[recall — verify]` = from memory. No trial accounts, so this reflects what each
company shows the market.

| Source | What they do | What I took | What I did not take, and why |
|---|---|---|---|
| **Material Design 3 + M3 Expressive** (read, m3.material.io, 27 Sep 2026) | Colour roles from one seed colour; tonal surfaces instead of shadows; Expressive button sizes and a shape change on press | Tonal palette from the brand colour; surface containers; M and L button sizes; the pressed-shape morph; top app bar, cards, lists, dialog, bottom sheet, snackbar | Expressive's decorative shapes and springy motion: noise on a cheap phone. Exact button sizes (56 / 96 px) are `[recall — verify]` — the spec page did not render for me |
| **Material Web (`@material/web`)** (read, GitHub + 9to5Google, June 2024) | Google's web components for M3; **in maintenance mode, no new work** | Nothing in code; I used its token names (`--md-sys-color-*`) so a later move is easy | The library itself (§9) |
| **greytHR** (read, ess-help.greythr.com) | Selfie sign-in, geofence with a 50 m minimum, **auto sign-in by tracking the phone's location**, liveness checks | A single clear "mark attendance" action with the photo step | Auto sign-in and live tracking (product-context §6: no passive tracking); face "liveness" (no face analysis) |
| **Keka** (read, docs.keka.com, help.keka.com) | Remote clock-in with GPS and an optional selfie; asks for location **"Allow all the time"** | Showing where the clock-in happened | "Allow all the time". We ask only "While using the app", and the notice promises "never in between" |
| **Zoho People** (read, zoho.com/people) | Geo restriction to set places; recommends the app over the website for GPS accuracy | Saying the rule plainly on the screen where you act | — |
| **Darwinbox** (read, marketplace.darwinbox.com) | Geo-fencing and geo-tagging for check-in and check-out | — | "Monitoring employee movement" framing: our words never say "track" |

**What none of them showed me, and we do:** the result screen tells the person the true
location and how exact the phone was, and a refusal says the real distance and what to do.

## 4. Findings on today's app

| ID | Screen | Finding | Impact | Kind | Size | Release level |
|---|---|---|---|---|---|---|
| M3-1 | Welcome | "Welcome, Arjun. This phone is set up." is one heading that wraps awkwardly (your screenshot) | Medium | Fix | S | P3 |
| M3-2 | Welcome, Result, Settings | Facts written as "Label · Value" sentences in a grey box; hard to scan | Medium | Fix | S | P3 |
| M3-3 | Notice (3 places) | Six parts as plain paragraphs; a 24 px tick box at the very end | High | Fix | M | P2 |
| M3-4 | All | Every button is the same 60 px block; Check In does not stand out; no brand; no hierarchy | High | Fix | M | P2 |
| M3-5 | All | No tenant brand colour applied (the server sends it once, the app ignores it) | Medium | New | S | P3 |
| M3-6 | Result | "Where you were · At PPJ Head Office" is shown even when the person was not there (it is the site name, not the checked position) | High | Fix | M | **P2** — says something untrue about attendance |
| M3-7 | Refusal | Distance shown only in metres ("about 13200 m") | Medium | Fix | S | P3 |
| M3-8 | Remove this phone | A full screen **and then** a browser `window.confirm()` pop-up: two confirmations, the second looks broken | Medium | Fix | S | P3 |
| M3-9 | Settings | No way to withdraw agreement, though the server supports it; DPDP wants withdrawal as easy as agreeing | High | New | M | **P2** |
| M3-10 | Notice after withdrawal | The reused screen would say "before your first check-in" — untrue after a withdrawal | Low | Fix | S | P3 |
| M3-11 | Home | "You need to be within 200 m of …" reads like a telling-off; no wording for "from anywhere" | Low | Fix | S | P4 |
| M3-12 | Sign-in | NETWORK_LOCKED gives no way out on a shared shop Wi-Fi on day one | Medium | Improve | S | P3 |
| M3-13 | All | `<meta name="color-scheme" content="light">`: no dark theme | Low | Improve | S | P4 |
| K-1 | Problem screens | One screen per failure, "Code for HR" at the bottom, chosen by error code | — | **Keep** | — | — |
| K-2 | Camera, location | Explain before Android asks | — | **Keep** | — | — |
| K-3 | Punch | Photo kept across a retry; camera off still allows the punch | — | **Keep** | — | — |
| K-4 | All | Server words set with `textContent`, never `innerHTML` | — | **Keep** | — | — |

## 5. Design tokens

All tokens are CSS custom properties on the app's root. Names follow Material's
(`--md-sys-color-*`), so the design and the code speak the same words.

### 5.1 Colour roles

Made from one seed: the tenant's brand colour, or Alvoraa's purple `#5B4B8A` (the portal's
`--primary`) before the app knows the company. Values below are the Alvoraa default.

| Role | Light | Dark | Used for |
|---|---|---|---|
| `primary` / `on-primary` | `#64558f` / `#ffffff` | `#cebdfe` / `#35275d` | Filled buttons, Check In, focus ring, section headings |
| `primary-container` / `on-…` | `#e8ddff` / `#4c3e76` | `#4c3e76` / `#e8ddff` | Explain-screen pictures, avatars |
| `secondary-container` / `on-…` | `#e8def8` / `#494458` | `#494458` / `#e8def8` | Tonal buttons, notice icons, "Checked out" card, info cards |
| `tertiary-container` / `on-…` | `#ffd9e3` / `#633b49` | `#633b49` / `#ffd9e3` | "What is new" on a changed notice |
| `error` / `error-container` | `#ba1a1a` / `#ffdad6` | `#ffb4ab` / `#93000a` | Wrong password, blocked, Remove this phone |
| `surface` / `on-surface` | `#fdf7ff` / `#1c1b20` | `#141218` / `#e6e1e9` | Page and text |
| `on-surface-variant` | `#48454e` | `#cac4cf` | Secondary text (8.9:1 light, 10.9:1 dark) |
| `surface-container-low … highest` | `#f8f2fa` … `#e6e1e9` | `#1c1b20` … `#36343a` | Cards, the fixed bottom bar, dialogs, sheets |
| `outline` / `outline-variant` | `#79757f` / `#cac4cf` | `#938f99` / `#48454e` | Field borders (4.3:1), dividers |
| `inverse-surface` / `inverse-primary` | `#322f35` / `#cebdfe` | `#e6e1e9` / `#64558f` | Snackbar |

**Fixed meaning colours** — the same for every tenant, so green always means "done" and amber
always means "fix this", whatever the brand:

| Role | Light | Dark | Source |
|---|---|---|---|
| `--alv-success-container` / `--alv-on-success-container` | `#a9f2cc` / `#005237` (7.2:1) | `#005237` / `#a9f2cc` | Tones of the design system's `--green #1B7F5A` |
| `--alv-warning-container` / `--alv-on-warning-container` | `#ffddb6` / `#643f00` (7.2:1) | `#643f00` / `#ffddb6` | Tones of the design system's `--amber #9A6510` |

**How the app makes a tenant's palette** (recommended):
1. Read `brand_colour` from the sign-in, code-check or status answer.
2. If its chroma (how much colour it has) is under 8, use Material's **monochrome** scheme;
   otherwise **tonal spot**, Material's default. (PPJ's black → greys; Sargam's blue → blues.)
3. Write the roles onto the root with `style.setProperty` (allowed under the app's CSP).
4. Keep the result per company on the phone, so it is worked out once, not every launch.
5. Before any company is known (sign-in, joining), use the Alvoraa default in the CSS file.

Every generated `on-X` / `X` pair I checked is at least 6.1:1 (the black palette 16:1+).
Material's recipe keeps these pairs readable for any seed, which is the same job
`brand_color.html`'s lightness clamp does on the portal.

### 5.2 Type scale (Material 3, with Alvoraa floors)

Font stack: `"Roboto Flex", Roboto, "Noto Sans", "Noto Sans Devanagari", "Noto Sans Gurmukhi",
system-ui, sans-serif`. Roboto and the Noto fonts ship with Android, so nothing is downloaded
(the app's CSP forbids that anyway). Not Google Sans: it is not licensed for other companies' apps
`[recall — verify]`.

| Role | Size / line | Weight | Used for |
|---|---|---|---|
| Display small | 36 / 44 | 400 | The time on the result ("9:12 am") |
| Headline medium | 28 / 36 | 400 | Screen headings ("Sign in", "Welcome, Arjun"); status ("since 9:12 am") |
| Headline small | 24 / 32 | 400 | Problem-screen headings, dialog and sheet headings, the Check In label |
| Title large | 22 / 28 | 400 | Top app bar title (company name), greeting |
| Title medium | 16 / 24 | 500 | Button labels, notice part headings |
| Title small | 14 / 20 | 500 | Section headings in lists ("Privacy") |
| Body large | 16 / 24 | 400 | All reading text, list items, field text |
| Body medium | 14 / 20 | 400 | Supporting lines, cards, field help |
| Label medium | 12 / 16 | 500 | "Code for HR", field labels on the border |

**Floors (ours, stricter than Material):** nothing under 12 px (Material's label small is 11 —
not used); field text 16 px; button labels 16 px (Material's default is 14).

**Large text:** sizes scale with Android's font size. The prototype's "Text size" switch shows
130% and 200%. At 150% and above, the top bar's "Settings" keeps its icon and spoken name but
drops the word, so the company name still fits — the only exception to "words beside icons".

### 5.3 Spacing, shape, elevation, motion, touch

| Token | Values |
|---|---|
| Spacing | 4 px grid: 4, 8, 12, 16, 20, 24, 32. Screen margin 16 px. |
| Shape (corner radius) | xs 4 (text fields, snackbar) · s 8 (photo thumbnail) · m 12 (cards) · l 16 · xl 28 (dialogs, sheets, status card, Check In) · full (buttons) |
| Elevation | Mostly tone, not shadow. Level 1 (elevated card, sheet), level 3 (dialog, snackbar). The fixed bottom bar on the notice is `surface-container` with a 1 px line. |
| Motion | Standard easing `cubic-bezier(.2,0,0,1)`, 250 ms. Buttons change shape on press (full → 12 px). Spinner slows and linear progress stops under "reduce motion". |
| Touch | **48 px minimum** for every target (Material's rule, above our 44 px phone rule). Buttons 56 px; Check In 96 px; list rows 56–72 px; the whole tick-box row is the target. |

## 6. Components, and where each is used

| Component (M3) | Screens |
|---|---|
| **Top app bar, small** — brand mark (initials on `primary`), company name, person's name below; labelled Settings | Home, problem screens, Welcome |
| Top app bar with Back / Close | OTP, joining screens, notice, Settings, Records, location and camera explain |
| **Filled button, medium (56 px)** | Sign in, Continue, Agree, Done, Try again, Yes this is me |
| **Filled button, large (96 px)** | Check In / Check Out only |
| **Tonal button** | "Remove … from this phone" on blocked / replaced |
| **Outlined button** | I have a joining code, Go back, This is not me, Keep it |
| **Text button** | Not now, Start again, Change, dialog actions |
| **Danger filled button** | Remove this phone (inside the sheet only) |
| **Outlined text field**, label always on the border, supporting text, error state, show-password icon button | Sign in, OTP |
| **Status card** (xl radius, success / neutral / secondary container) | Home |
| **Cards**: outlined (facts), elevated ("Is this you?"), tonal info / success / warning / error / tertiary | Everywhere facts or reassurance appear |
| **List items**, one- and two-line, leading icon, trailing value or chevron, dividers | Welcome, Today's punches, Result, Settings, Records, Update, Server error, Remove sheet |
| **Icon bubble** (72 px tonal square) | The one picture on every explain, problem and result screen |
| **Checkbox row** (whole row, 56 px) | Notice (3 places) |
| **Fixed bottom action area** | Every screen with a main action |
| **Dialog** | This is not me; Stop agreeing |
| **Bottom sheet** | Remove this phone |
| **Snackbar** | After "Stop agreeing" |
| **Circular progress** / **linear progress** / step list | Signing in, checking the code, setting up; Punching |
| **Skeleton** | Home while loading |
| Camera screen (full-bleed, dark, big round shutter with its word under it) | Scan, Take photo, Use / Retake |

No navigation bar: D1 still stands (no tab bar until My HR arrives).

## 7. Screen by screen — what changed, and why

Every word not listed here stays exactly as it is in the app today (`index.html`,
`join-screens.js`, `checkin-screens.js`, `signin-core.js`). **New words are marked NEW.**

### 7.1 Sign in (and its errors)

| Before | After | Why |
|---|---|---|
| "Alvoraa" h1, then a long h2 "Sign in with your work email and password" | App bar "Alvoraa Attendance"; heading **Sign in**; one line under it | A short heading does not wrap |
| Label above a 52 px box | Material outlined field, label always visible on the border, help text under Company code | Current Android look; the label never disappears |
| Company code asked every time the form shows | Once remembered, a grey row "Company code · ppj · **Change**" (NEW word: Change) | "You type it only once" becomes visible |
| No show-password | Eye button, "Show password" / "Hide password" (NEW) | Fewer typing errors on small keyboards |
| Error as red text above the button | Error card at the top of the form with icon, message and "Code for HR"; focus moves to it; password box emptied and marked, "Type your password again." (NEW) | Seen first, read out to HR easily |
| All errors red | **Red** only for wrong details; **amber** with a lock icon for ACCOUNT_LOCKED and NETWORK_LOCKED (a wait, not a mistake); **tonal info** for PASSWORD_SIGNIN_OFF and PASSWORD_CHANGED_SIGN_IN_AGAIN | Colour means something (principle 9) |
| PASSWORD_SIGNIN_OFF: joining-code button stays outlined | It becomes the filled (main) button | It is now the only way in |
| NETWORK_LOCKED: "Too many sign-in attempts from this network. Try again later." | **Security's words (27 Sep 2026, D-M3-6):** "Too many wrong sign-in attempts from this network. Try again in a few minutes, or turn off Wi-Fi and use your mobile data." (NETWORK_LOCKED is Frappe's per-network lock after repeated wrong passwords, which lasts minutes; the 500-an-hour limit is TOO_MANY_TRIES) | Day one at a shop: one Wi-Fi for everyone |
| Password changed | Sign-in screen with a tonal card: **"Your password was changed. Please sign in again."** + "Use your new password. Attendance you already marked is safe." (NEW second line) | Not the person's fault, so not red |

**One-time code:** app bar with Back ("Start again"); key picture; "Type the code you were sent";
the server's prompt; one large box with wide spacing, number keypad, Android autofill
(`autocomplete="one-time-code"`). One box, not six: codes can be 6–12 characters. Error under the box.

**Busy:** "Signing you in" + NEW "This can take a few seconds on a slow connection."

### 7.2 Joining code

Same five steps: explain camera → scan → checking → Is this you? → (Not me) → notice.

- **Join with a code** (the `first` screen): NEW heading "Join with a code from HR"; the two
  reassurance lines become a two-row list; buttons in the thumb zone.
- **Scan:** full-screen camera, square viewfinder, Close top-left (Android habit), "Choose a
  picture instead" at the bottom.
- **Is this you?:** elevated card with initials, "Arjun K.", job, company with a shop icon.
  **The company's colour starts here** (the code-check answer carries `brand_colour`).
- **This is not me:** a **dialog** instead of a full screen (same words). "Go back. It is me."
  first; "Cancel this code" last, in the error colour. Then "The code is cancelled" screen.

### 7.3 The notice

**Words, heading, tick-box words and button words: unchanged.** Layout only:
- A card with the six parts, each with an icon (camera · eye crossed out · question · people ·
  hourglass · shield), a bold heading and the body under it.
- The person's line ("PP Jewellers · Arjun K. · Sales Executive") moves into the app bar as a
  subtitle.
- **Tick box and button fixed at the bottom**, always reachable. The whole row is the tick box
  (56 px). If Agree is pressed unticked: the existing error line appears above the row, the box
  turns red, focus moves to it. Agree is never greyed out (a greyed button does not say why).
- NEW small line: "Notice version 2026-09-22" under the card.
- **Notice has changed:** a "What is new" card first, with the server's own sentence.
- **After "Stop agreeing":** NEW heading "You stopped agreeing", NEW intro "To mark attendance
  with this phone again, read the notice and agree." (M3-10).

The icons need a stable key per part (§8), not the English heading.

### 7.4 Welcome

| Before | After |
|---|---|
| "Welcome, Arjun. This phone is set up." (one wrapping heading) | Tick picture; heading **Welcome, Arjun**; body "This phone is set up. You can mark attendance now. You do not need to wait for HR." |
| "Company · …", "Your workplace · …", "Check in within · 200 m" | A list: PP Jewellers / *Company* · PPJ Head Office Chandigarh / *Your workplace* · Within 200 m / *Where you can check in* (NEW sub-labels) |
| Green Check In, "Not now" link | Large Check In at the bottom, "Not now" text button under it |

### 7.5 Home

- App bar: brand mark, company name, the person's name under it, **Settings** (icon + word).
- NEW greeting "Good morning, {first name}" (by the phone's clock: morning before 12, afternoon
  before 5, evening after) and the date.
- **Status card**, three states:

| State | Card | Icon | Words |
|---|---|---|---|
| Nothing yet | Neutral | Clock | "Today" / **Not checked in yet** |
| In | Green (success container) | Tick | "Checked in" / **since 9:12 am** |
| Out | Tonal (secondary container) | Arrow out | "Checked out" / **at 6:14 pm** |

- The rule sits inside the card, under a line: NEW "Check in within 200 m of PPJ Head Office
  Chandigarh" (was "You need to be within …"), or NEW "**Check in from anywhere**" + "Your
  location is still saved with each check-in."
- "Today" list of punches (arrow icon, "Checked in", time). Empty: NEW "No check-ins yet today."
  (was "No punches yet today." — "punch" is office English).
- Disclosure line under the list: NEW "A photo and your location are taken when you press the
  button." (replaces 01b's camera tag).
- **Check In / Check Out**: one 96 px button, brand colour, icon + word. I dropped the green-in /
  purple-out colour swap: with a tenant colour the two would clash, and the status card already
  carries the state in colour, icon and words.
- Camera off: amber card, existing words, "Turn on the camera".
- Loading: skeleton within 300 ms; the button waits for status so it can never say the wrong thing.

### 7.6 Check-in flow

1. **Location explained** (first time only): same words, new layout.
2. **Camera** (NEW screen): full-bleed live preview; app bar "Take your photo" with Close
   ("Cancel"); hint "Hold the phone in front of your face"; round 80 px shutter with **Take photo**
   written under it; "Only HR and your manager can see this photo." No face outline or oval: it
   would suggest face matching, which we do not do.
3. **Check your photo** (NEW): "Is your face clear?" · **Retake** (left) · **Use photo** (right, thumb side).
4. **Punching:** app bar "Checking you in", linear progress, then three steps that tick off:
   Photo taken · Finding where you are · Saving your attendance. NEW: "Keep the app open. This can
   take up to 20 seconds on a slow connection." After 10 s, NEW: "Still working. Your photo is
   kept." (not drawn in the prototype).
5. **Result:** tick picture, "Checked in", **9:12 am** large, the date, then a list:

| Case | Line 1 | Line 2 |
|---|---|---|
| Inside the rule | At PPJ Head Office Chandigarh | Within 200 m · accuracy 14 m |
| Allowed anywhere, far away | About 13.2 km from PPJ Head Office Chandigarh | You may check in from anywhere · accuracy 14 m |
| Allowed anywhere, close | At PPJ Head Office Chandigarh | Within 200 m · accuracy 14 m |
| No workplace set | Location saved | Accuracy 14 m |

   then "Photo taken" with a thumbnail (or "Photo not taken" + the existing sentence), "Saved in
   your HR record", "Only HR and your manager can see this.", **Done**.
   This fixes M3-6: today the result says "At {site}" whatever the distance.
6. **Refused, too far** (your words): heading "You are too far from work"; body "You are **13.2 km**
   from your workplace. Move within 200 m and try again."; the workplace in a card; "Your photo is
   kept. Nothing has been saved."; Try again / Go back; Code for HR.

**Distance format (all screens):** under 1,000 m → whole metres ("140 m"); from 1 km to 99.9 km →
one decimal ("1.4 km", "13.2 km"); 100 km and more → whole km ("140 km").
Always "about" when the phone's accuracy is worse than 20 m `[ASSUMPTION]`.

### 7.7 Problems and edge states

One template (Keep K-1): brand app bar · 72 px picture in a tone that matches the meaning ·
heading · body with the real numbers in bold · optional card (photo kept, "you are safe") ·
numbered steps · buttons at the bottom · "Code for HR: X".

| Screen | Picture / tone | Change from today |
|---|---|---|
| GPS not exact (> 50 m) | Crosshair / amber | Layout only |
| No internet | Wi-Fi off / neutral | Layout only |
| Blocked by HR | Block / red | Green "safe" card; the Remove button is tonal, not the main colour; Settings stays in the bar |
| Phone replaced | Phone / neutral | Layout only |
| Password changed | (sign-in screen, §7.1) | Tonal card, not red |
| Notice changed | (notice, §7.3) | "What is new" card |
| App out of date | Download / primary | Version facts as a list; green "you stay set up" card |
| Something went wrong | Error / red | "For HR" facts as a list |

### 7.8 Settings and records

**Settings:** avatar, full name, job · company. Sections (Material list with coloured section headings):
- **Your workplace:** workplace / rule.
- **Privacy:** "What this app records ›" (you agreed on …) · NEW "**Stop agreeing to the notice ›**"
  with "Attendance on this phone pauses until you agree again".
- **This phone:** "Remove this phone from {company}" in the error colour.
- **About:** version, "Connected to {host}", the existing help line.

**Stop agreeing (NEW dialog):** "Stop agreeing to the notice?" · "This phone stops marking
attendance for you until you agree again." · "Nothing is deleted. Attendance you already marked
stays in your HR record." · "HR will see that you stopped agreeing." · **Keep agreeing** /
**Stop agreeing**. Then the notice (§7.3, "You stopped agreeing") with a snackbar "You stopped
agreeing. Attendance on this phone is paused."

**What this app records:** green card "You agreed on Monday 22 September at 9:01 am. Notice
version 2026-09-22." · the six parts · NEW "Recorded today on this phone": today's punches with
"Photo, location (at …), time" · NEW "To see older records, or to correct one, ask HR." · the
existing "If this notice changes …" line.

**Remove this phone:** a **bottom sheet** with the existing five sentences as a list with icons,
"You need the internet for this.", **Remove this phone** (red, filled) and **Keep it**. The extra
`window.confirm()` goes (M3-8).

## 8. What the engineer needs from the server

| # | Need | Why | Today |
|---|---|---|---|
| E-1 | `brand_colour` in the password sign-in answer and the status answer (`field_status`) | Brand colour after sign-in and every launch | Only in the code check |
| E-2 | On a saved punch: `distance_m`, `accuracy_m`, `within` (true/false), and the rule (`radius` or `anywhere`) | The true-location result (§7.6) | The accepted punch does not return them `[ASSUMPTION — engineer to confirm; being fixed in parallel]` |
| E-3 | In `field_status`: the rule (`radius` or `anywhere`) | "Check in from anywhere" on Home | Only `workplace.name` and `radius_m` |
| E-4 | A stable `key` per notice part (`record`, `not_record`, `why`, `who`, `how_long`, `rights`) | Icons that survive translation. **Adding a key is not a change to the words** and needs no new notice version `[ASSUMPTION — security to confirm]` | Heading and body only |
| E-5 | Confirm HR sees a withdrawal (phone status "Consent not given", source "The employee") | The dialog says "HR will see that you stopped agreeing." | Server sets the status; desk display not checked |

## 9. How to build it — library or hand-written CSS

**Recommendation: hand-written CSS on the tokens in this note, in the one `app.css` file.
Vendor only Google's colour code (`@material/material-color-utilities`, Apache-2.0) for the
tenant palette.**

| Option | Size (measured 27 Sep 2026, esbuild, minified / gzip) | For | Against |
|---|---|---|---|
| **`@material/web` 2.2** — 9 components we would use (buttons, text field, checkbox, dialog, list, progress) | **173 KB / 35.5 KB** of JavaScript | Exact M3 behaviour | **In maintenance mode since June 2024, no new work.** Shadow DOM makes our own error states and Hindi text harder to style. Needs a build step the app does not have. Its components inject styles at runtime, which the app's strict `style-src 'self'` may block `[recall — verify on a phone]`. Parse cost on a cheap phone. |
| **Hand-written CSS** (the prototype's "APP TOKENS" and "APP COMPONENTS" blocks) | About 12 KB of CSS, no JavaScript | Plain HTML buttons and inputs the app already has; works with the CSP; easy to read; screen readers see native controls | We keep the M3 look up to date ourselves |
| Colour code `@material/material-color-utilities` 0.3 (5 functions) | **69 KB / 14 KB** | Material's exact palettes from any brand colour, including the black case | A fourth place that turns a brand colour into a palette (see D-M3-3) |

**How to lift it:**
1. Copy the "APP TOKENS" and "APP COMPONENTS" blocks from the prototype into `web/css/app.css`,
   changing the `.app` selector to `:root` / `body`. Drop the "BEFORE" and "REVIEW" blocks.
2. Keep `index.html`'s screen sections and `data-action` wiring; change the markup inside each
   section to the prototype's classes (`top-bar`, `btn filled block`, `field`, `list-item`, …).
   The JS that fills text (`textContent`) keeps working if the element ids stay.
3. Dark theme: change the meta to `<meta name="color-scheme" content="light dark">` and switch
   palettes on `prefers-color-scheme` (if D-M3-1 is "follow the phone").
4. Text size: check that the WebView follows Android's font size. If it does not, the app must
   pass the system font scale to the CSS `--s` `[recall — verify on a phone]`.
5. The status bar and navigation bar colours should match `surface`; that may need Capacitor's
   status-bar plugin, which the app does not have yet — a new plugin needs the usual review.

## 10. Accessibility and privacy

| WCAG 2.2 AA | How |
|---|---|
| 1.4.3 / 1.4.11 contrast | Every text pair ≥ 6.1:1 in all three sample palettes, light and dark; field borders 4.2:1+ |
| 1.4.1 colour not alone | Status: colour + icon + words. Problem screens: tone + picture + heading. |
| 1.4.4 / 1.4.10 resize, reflow | Measured at 360 px with 200% text: nothing wider than the screen |
| 2.5.8 target size | Measured: nothing under 48 × 48 px on any of the 48 screens |
| 3.3.1 errors | Error cards `role="alert"`, focus moves to them; fields `aria-invalid` + `aria-describedby` |
| 4.1.2 name, role | Native buttons and inputs; the tick row is `role="checkbox"` with `aria-checked` and Space/Enter; dialogs `role="alertdialog"` with a heading |
| 2.4.7 focus | 3 px ring in `primary` |
| 3.1.2 language | `lang="hi"` on Hindi strings |
| 2.3.3 motion | Reduced-motion rules for spinner, progress and shape change |

**Privacy.** No new personal data is shown or collected. The result shows the person their own
distance and accuracy (it was sent to the server anyway). The camera screen says who sees the
photo. The notice words are unchanged. Withdrawal is now one tap and one confirm — as easy as
agreeing. Refusals checked (product-context §6): no face outline or face matching, no tracking
between punches, no "Allow all the time", no pre-ticked box, no greyed-out Agree nagging.

## 11. Checks before handoff

- **Measured, not looked at** (Playwright, Chrome, 27 Sep 2026): 48 screens × {360 px light,
  360 px dark, 360 px at 200% text}: **no sideways scroll, no target under 48 px, no text under
  12 px, no script errors.** The first pass found an 11 px "Sample" tag and an unbreakable
  error code at 200% text; both fixed.
- **One look** at Home, notice, sign-in, result, refusal, sheet and camera: the 200% Home cut the
  company name to "PP J…", so Settings becomes icon-only at 150%+.
- **Nielsen, briefly:** status visible (status card, progress steps) · match the real world ("Check
  in within 200 m") · user control (Cancel on camera, Keep it, Keep agreeing) · consistency (one
  problem template) · error prevention (confirm on cancel-code, remove, withdraw) · recognition
  (icons with words) · recovery (every error says what to do, Code for HR).
- **Frontline two-minute bar:** daily check-in is 3 taps (Check In → Take photo → Use photo) plus
  Done; first day (sign-in) is under 2 minutes on a good signal `[ASSUMPTION — test on a phone]`.
- **Red team:** brand colour black → grey palette (done); brand colour pale yellow → Material keeps
  contrast; 200% text → fixed; no network mid-punch → photo kept; wrong password twice → form keeps
  email; blocked person → no Check In anywhere; long company name → two lines then "…"; Hindi about
  30% longer → Home fits at 360 px in the sample.

## 12. Usability test plan (High impact: Home, check-in, notice)

Five people: three PPJ store staff, two Sargam workers; at least two Hindi-first; own phones.

| Task | Success | What would change the design |
|---|---|---|
| "Are you checked in right now?" (Home, shown for 3 s) | Right answer in 3 s | If two or more hesitate: stronger status contrast or bigger time |
| Check in, from a locked phone | Done in under 30 s, no help | If people tap the photo preview instead of "Use photo": swap to one button "Use photo" and a small Retake |
| After a refusal: "What do you do now?" | Says "walk closer" | If not: move the distance into the heading |
| Read the notice and agree | Can say one thing that is **not** recorded | If nobody can: add a one-line summary above the parts (words then need a new notice version) |
| Find how to stop agreeing | Found in under 60 s | If not: move it under "What this app records" |

## 13. Decisions for you

| # | ⚠ DECISION | Options | My recommendation | Owner | Blocks |
|---|---|---|---|---|---|
| D-M3-1 | Theme (reopens D9, "pinned light") | Pinned light · follow the phone · a switch in Settings | **Follow the phone.** Most cheap phones are in light mode, so sunlight is unchanged; people who chose dark get dark. No extra setting. | Surbhi | CSS build |
| D-M3-2 | Check In / Check Out colour | Brand colour for both (prototype) · keep green-in / purple-out | **Brand colour for both.** The state is in the status card; two fixed colours clash with a tenant's brand | Surbhi | Home |
| D-M3-3 | Where the palette is made | App vendors Google's colour code (14 KB gzip) · server makes the palette once and sends the roles · reuse `brand_color.html`'s lightness clamp (not Material colours) | **App vendors it**, caching per company. Honest cost: a fourth place turning a brand colour into colours, which `brand_color.html` warns about; the portal and app shades will differ slightly | Surbhi, engineer | Palette code |
| D-M3-4 | Agree always reachable on the notice | Fixed at the bottom (prototype) · at the end of the scroll (today) · appears after scrolling to the end | **Decided: OK with a change (security, 27 Sep 2026).** Fixed at the bottom, no forced scroll, parts not collapsed - and the fixed Agree bar never covers the notice (the last part scrolls fully clear of it), and at 360 × 640 the first part's heading and body show above the bar. Words unchanged | Security / compliance | Notice layout |
| D-M3-5 | Black or grey brand colours | Monochrome palette (prototype) · refuse and use Alvoraa purple | **Monochrome.** It is the tenant's choice and stays readable | Surbhi | Palette code |
| D-M3-6 | NETWORK_LOCKED words | Today's · proposed "…or turn off Wi-Fi and use your mobile data" | **Decided: OK with new words (security, 27 Sep 2026):** "Too many wrong sign-in attempts from this network. Try again in a few minutes, or turn off Wi-Fi and use your mobile data." The designer's first words described the wrong limit | Security | Sign-in copy |
| D-M3-7 | Greeting by time of day | "Good morning, Arjun" · "Hello, Arjun" · none | **Good morning / afternoon / evening.** Warm, costs three strings per language | Surbhi | Home copy |

## 14. What the business analyst must turn into acceptance criteria

1. Every target ≥ 48 × 48 px; no text under 12 px; field and button text ≥ 16 px; nothing wider
   than a 360 px screen at 200% text.
2. Check In / Check Out is the only 96 px button, fixed in the bottom area of Home.
3. Home's status card shows, for each of the three states, the words, the icon and the colour in §7.5.
   After a check-out it never says "Not checked in yet".
4. The result screen's location lines follow the table in §7.6, from the server's values (E-2).
   It never says "At {workplace}" when `within` is false.
5. Distances follow the format in §7.6.
6. The notice's words, tick-box words and button words match the server byte for byte; only the
   layout changes; the tick box is never pre-ticked; Agree unticked shows the existing error and
   moves focus.
7. The tick box and Agree stay visible without scrolling; the bar never covers the notice; at 360 × 640 the first part's heading and body are above it (D-M3-4 as decided).
8. "Stop agreeing" calls `withdraw_agreement`, then shows the notice with the §7.3 words; the
   notice then works as the way back in.
9. Remove this phone has exactly one confirmation (the sheet), no `window.confirm`.
10. The palette comes from `brand_colour`; chroma under 8 uses the monochrome scheme; before a
    company is known, the Alvoraa default; success and warning colours never change with the tenant.
11. Light and dark as decided in D-M3-1; every text pair ≥ 4.5:1 in both.
12. Every problem screen still shows "Code for HR: {code}".

---

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| D-M3-1 to D-M3-7 above | Surbhi (D-M3-4, D-M3-6 with security) | CSS build, Home, notice, sign-in copy |
| Does the saved punch return distance, accuracy and "within"? (E-2) | Engineer (fixing check-in in parallel) | The result screen |
| Does adding a `key` to each notice part need a new notice version? (E-4) | Security / compliance owner | Notice icons |
| Does the WebView follow Android's font size, and does `@material/web`'s style injection pass the CSP? | Engineer, on a phone | Large-text support; confirms §9 |
| Does the desk show HR that a person stopped agreeing? (E-5) | Engineer | Withdraw dialog's third line |

## Assumptions

- [ASSUMPTION] Your screenshots show what you described; I did not see them.
- [ASSUMPTION] M3 Expressive button heights are 56 px (medium) and 96 px (large) — `[recall — verify]`.
- [ASSUMPTION] The accepted punch does not yet return distance and accuracy.
- [ASSUMPTION] "About" is shown when accuracy is worse than 20 m.
- [ASSUMPTION] A first-day sign-in fits in two minutes on a good signal.
- [ASSUMPTION] Retention in the sample notice is 90 days (the tenant's setting decides the real line).

## Handoff note

To the engineer: build from the prototype's "APP TOKENS" and "APP COMPONENTS" blocks and §7; keep
every element id that `checkin.js`, `join.js` and `signin.js` fill, and keep `textContent`. Three
things are not a restyle: the camera screens (you are already on them), the result's true-location
lines (need E-2), and the new "Stop agreeing" path (endpoint exists, screen does not). Watch the
black-brand trap (use monochrome under chroma 8) and do not reintroduce a colour swap on the Check
In button. To security: D-M3-4 and D-M3-6 are yours. I disagree with nothing above me, but D-M3-1
reverses a decision you agreed on 17 Sep, so it needs your word, not mine.
