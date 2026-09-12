# 008 — Field check-in — UX design

**Slice:** 008-field-checkin · **Stage:** design (step 01b)
**Author:** `hrms-ux-designer` · **Date:** 12 Sep 2026
**Status:** for the user to review by clicking the page
**Upstream:** `docs/slices/008-field-checkin/01-product-brief.md` (scope fixed, not re-opened)
**Downstream:** the business analyst turns §9 into acceptance criteria

**Read this first:** the deliverable and the prototype are the same file, as
agreed for this slice. There is no throwaway mock.

**The page:**
`C:/Surbhi-Git/hrlocal-data/prototypes/008-field-checkin/field-checkin-v1.html`

**I cannot publish a link from here.** The session that ran me should publish
the file and give the user the link.

**To review it without a server:** open the page, type `demo` in the server
address, any employee ID, press **Set up**. A brown bar says "Sample data" and
a black strip at the bottom jumps to any of the 19 states. Sample mode never
touches a server. It only appears when the server address is the word `demo`.

Screenshots of every state (real tenant names are not in them; the sample
person is "Ramesh Kumar", marked Sample):
`C:/Surbhi-Git/hrlocal-data/ux-review/2026-09-12/008-*.png`

---

## 1. Who this is for, and the one job

**A driver or a security guard, standing outside a jewellery store, on a cheap
Android about 360 px wide, in sunlight, wanting to be marked present.**

They may be Hindi or Punjabi first, may read little English, and may never have
used a work app. They are the least confident user Alvoraa has designed for.

| Persona | What changes |
|---|---|
| **Field employee (primary)** | Can mark attendance at all. Setup once, then **one tap a day**. |
| **Internal employee** | No change in this page. Their phone punch is checked against the branch. |
| **HR Manager** | No screen here. They see the punch in `Employee Checkin` with the photo, place and GPS accuracy. |
| **Line manager** | No screen here. Sees the photo behind a punch in Frappe HR. |
| **CXO** | No screen here. Field attendance stops being paper. |

Left out on purpose, for the clock: HR's Org Settings screen for the radius and
the deduction rule (brief P7, P8), and the supervisor's photo review (§6 of the
brief).

---

## 2. The design in one paragraph

The camera fills the screen and the **Check In** button is the biggest thing on
it — 104 px tall, 34 px type, green. Above them sit only two facts: whether you
are in, and today's punches with times. One tap takes the photo, finds the
place and sends the punch. Everything that can go wrong gets its **own full
screen**, with a picture, one sentence saying what happened, numbered steps
where the driver can fix it, and one obvious button. Nothing on the page is
smaller than 15 px, and nothing you must read to act is under 17 px.

---

## 3. Three decisions I took, so they can be argued with

| # | Decision | Why | If you disagree |
|---|---|---|---|
| D1 | **The light theme is pinned.** The design system's dark mode is not used. | The screen is read outdoors in sunlight on a cheap panel. Dark mode there is unreadable. Tokens are otherwise exactly the design system's. | Delete `data-theme="light"` and paste the dark block back. |
| D2 | **A punch without a photo is allowed** if the camera will not start. The result screen says "Photo: Not taken". | A guard who turned up should be marked present. The photo is evidence, not the rule (brief §4). The server already accepts `photo=None`. | Make `snap()` returning null block the punch. One line. |
| D3 | **A Hindi column exists and there is an EN / हिं switch.** Default English. | The brief puts Hindi in the backlog (§6), but the primary user is Hindi-first and the strings cost nothing to carry. **Every Hindi string is a machine draft and must be checked by a native speaker before a customer sees it.** | Delete the `.lang` control; the English column still works. |

⚠ **DECISION for the user, not for me:** how long check-in photos are kept.
The brief calls this a DPDP obligation in §6. The page tells the driver "Only
HR and your supervisor can see this" — it cannot yet tell them for how long.
**Owner: Surbhi.** It does not block the demo.

---

## 4. The flow

```
open app
  |
  +-- no saved token --> SETUP --> registering --> YOU ARE SET UP, {name}
  |                          |                        + add to home screen
  |                          +-- 2nd phone --> WAITING FOR HR
  |                          +-- ID unknown --> error under the ID field
  |
  +-- saved token --> HOME (camera, state, today's punches, one big button)
                         |
                        tap Check In / Check Out
                         |
                 photo -> place -> send
                         |
          +--------------+---------------------------+
          |                                          |
       CHECKED IN / OUT at 9:12 am              a PROBLEM screen
       (time, place, photo saved)               (one of nine, §6)
          |                                          |
        Done --> HOME                          Try again --> resend, same photo
```

**The photo is kept in memory while a problem is on screen.** "Try again" after
"No internet" or "Too far" resends the same photo. The driver never poses twice.

---

## 5. Screen by screen, with the exact words

Hindi is a **machine draft — needs native review** everywhere below.

### 5.1 Setup (once)

| Element | English | Hindi (draft) |
|---|---|---|
| Title bar | Attendance | हाज़िरी |
| Heading | Set up this phone | यह फ़ोन सेट करें |
| Intro | You only do this once. HR gives you these two things. | यह केवल एक बार करना है। ये दो चीज़ें HR से मिलेंगी। |
| Field 1 label | Server address | सर्वर पता |
| Field 1 hint | HR gives you this. It usually starts with https:// | HR यह देगा। यह आम तौर पर https:// से शुरू होता है। |
| Field 2 label | Your employee ID | आपकी कर्मचारी आईडी |
| Field 2 hint | On your ID card, or ask HR. Example: HR-EMP-00042 | आपके आईडी कार्ड पर, या HR से पूछें। जैसे: HR-EMP-00042 |
| Privacy line | This phone is linked to you. Your photo and place are recorded only at the moment you press Check In. You are not tracked at any other time. | यह फ़ोन आपसे जुड़ा है। आपकी फ़ोटो और जगह केवल तभी दर्ज होती है जब आप चेक इन दबाते हैं। बाकी समय आप पर नज़र नहीं रखी जाती। |
| Button | Set up | सेट करें |

Field errors, shown under the field, in red, with `aria-invalid`:

| Case | Words |
|---|---|
| Server empty | Please enter the server address HR gave you. |
| Employee ID empty | Please enter your employee ID. |
| Server unreachable | We could not reach that server. Check the address, and check you have internet. |
| ID not found | *(the server's own words)* We could not find an active employee with that ID. Please check it with HR. |

The server address is pre-filled with `https://ppj.dev.alvoraa.co` for the
demo. The engineer should change that default per customer, or bake it in.

### 5.2 You are set up

Green tick. **"You are set up, {employee_name}"**, then *"Now put this app on
your home screen, so you can open it like any other app."*

Then the Add-to-Home-Screen card, chosen automatically from the user agent, with
a link to the other one ("I have an iPhone" / "I have an Android phone").

**On Android**
1. In Chrome, press the three dots at the top right.
2. Press "Add to Home screen" or "Install app".
3. Press "Add". The app is now on your home screen.

**On iPhone**
1. In Safari, press the Share button at the bottom (a box with an arrow).
2. Scroll down and press "Add to Home Screen".
3. Press "Add". The app is now on your home screen.

Primary button: **Start**.

### 5.3 Home

| Part | Words | Notes |
|---|---|---|
| State chip, out | Not checked in yet today | Grey, grey dot. Colour is never the only signal — the words carry it. |
| State chip, in | You are checked in since 9:12 am | Green, green dot. |
| Camera caption | Your photo is taken when you press the button | Over the live preview. |
| Camera off | The camera is off. You can still check in, but there will be no photo. + button **Turn on the camera** | See D2. |
| Punch list header | Today · 12 Sep | |
| Punch row | Checked in · This phone · 9:12 am | Machine punches read "Reception machine", so one person's day reads as one story. |
| Empty list | No punches yet today. | |
| Above the button | You must be within 100 m of PPJ Noida | From `field_status.work_location`. Told **before** they walk, not after they are refused. |
| The button | **Check In** (green) / **Check Out** (purple) | 104 px tall. Arrow points in for In, out for Out. |

Busy messages, one at a time, on a dark overlay: *Taking your photo* → *Finding
where you are* → *Saving your attendance*.

### 5.4 After a punch

Green tick. **Checked in** (or **Checked out**), then the time in 54 px —
**9:12 am** — then *Saturday, 12 September*.

| Row | Value |
|---|---|
| Where you were | At PPJ Noida *(or "Your place was recorded" if no shift location is set)* |
| Photo | Taken / Not taken |
| Saved | In your HR record |

Then: *Only HR and your supervisor can see this.* Button: **Done**.

### 5.5 Every problem state

Each is a full screen: a picture, a heading, one sentence, sometimes numbered
steps, and one or two buttons. Amber = you can fix it. Red = you cannot, go to
HR. The red ones offer **Go back** only — never a button that will fail again.

| # | State | Trigger | Heading | Body | Buttons |
|---|---|---|---|---|---|
| E1 | Location off | no `navigator.geolocation`, or the server says "could not get your location" | Location is off | We need to know where you are to mark your attendance. Turn on location, then try again. | Try again · Go back |
| E2 | Location refused | geolocation error code 1 | This app cannot see your location | You said no to location earlier. Allow it for this app, then try again. | Try again · Go back |
| E3 | Location slow | 20 s with no fix | Still looking for your location | Your phone is taking too long to find you. Step into the open, wait a few seconds, and try again. | Try again · Go back |
| E4 | GPS too vague | server: "accurate to about {n} m" | Your location is not exact enough | Your phone is not sure where you are. Step outside or away from buildings, wait a few seconds, and try again. | Try again · Go back |
| E5 | Outside the branch | Frappe HR's radius refusal, rewritten by `_geofence_message` | You are too far from work | **You are about 140 m from PPJ Noida. You need to be within 100 m to check in.** Walk closer and press Try again. Nothing has been saved. | Try again · Go back |
| E6 | No signal | fetch failed | No internet | Your attendance has not been saved yet. Move to a place with signal and press Try again. Your photo is kept until then. | Try again · Go back |
| E7 | Phone not registered | server: "not set up" | This phone is not set up | Set it up again with the server address and employee ID HR gave you. It takes a minute. | Set up this phone again |
| E8 | Second phone, waiting | server: "waiting for HR" | Waiting for HR to approve this phone | Another phone is already set up in your name, so HR has to approve this one. They have been told. Use your old phone until then. | Try again · Set up this phone again |
| E9 | Phone blocked | server: "blocked" | This phone has been stopped | HR has blocked this phone from marking attendance. Please speak to HR. | Go back |
| E10 | Employee left | server: "no longer active" | You cannot mark attendance here | Your employee record is not active any more. If that is wrong, please speak to HR. | Go back |
| E11 | Not in the plan | subscription gate (`requires_feature`) | This app is not switched on for your company | Field check-in is not part of your company's plan yet. Please tell HR. | Go back |
| E12 | Anything else | any other failure | Something went wrong | Your attendance was not saved. Press Try again. If it keeps happening, show this screen to HR. | Try again · Go back |

E1 and E2 also carry three numbered steps (swipe down, press Location, come
back / press the lock icon, press Permissions, come back).

**No raw server error ever reaches the driver.** E5's body is the exception and
it is deliberate: the server's own sentence already names the real distance and
the real branch, which is the whole point of that message.

---

## 6. How it talks to the server

Exactly the shapes in `alvoraa_portal/alvoraa_portal/field_checkin.py`, read on
12 Sep 2026. All three are `POST /api/method/alvoraa_portal.field_checkin.<fn>`,
JSON in, `{"message": ...}` out, `credentials: "omit"`.

| Call | Sent | Used from the reply |
|---|---|---|
| `register_device` | `employee_id`, `device_label` (e.g. "SM-A125F / web"), `platform` (Android / iOS / Other) | `status`, `token`, `employee`, `employee_name`. `status: "pending"` → E8. |
| `field_checkin` | `token`, `log_type` IN/OUT, `latitude`, `longitude`, `accuracy`, `photo` (data URL, JPEG, 480 px wide, quality 0.6) | `log_type`, `time` (**server time — the screen never shows the phone's clock for a saved punch**), `employee_name` |
| `field_status` | `token` | `employee_name`, `checked_in`, `todays_checkins[]`, `server_time`, `work_location{name,radius}` |

Errors are read from Frappe's `_server_messages`, HTML stripped, then matched
on their text in `handle()` — because the module throws sentences, not codes.
**If those sentences are ever reworded, update `handle()` in the same commit.**
A cleaner answer is a machine-readable key in the exception; it is not worth the
risk today. → backlog.

Only `token` is stored, in `localStorage` under `alvoraa.field.v1`. The photo
never touches storage. Nothing is logged to the console.

---

## 7. Accessibility and privacy

Measured on the real render at 360 × 740 (not eyeballed — learning P4):

- Page width 360 px, no horizontal overflow. Same in Hindi.
- Every control the driver uses is ≥ 60 px tall; the main button is 104 px.
  The only items under 44 px are the sample-mode switcher, which never ships to
  a driver.
- No text under 15 px. Nothing you must read to act is under 17 px.
- Both inputs have real `<label>` elements; errors use `role="alert"` and
  `aria-invalid`.
- Focus is a 3 px outline with 2 px offset, visible on every control.
- State is never colour alone: the chip has a word, the button has a word, the
  punch rows say "Checked in" / "Checked out".
- `prefers-reduced-motion` turns off the flash and slows the spinner.
- Contrast: all text uses design-system pairs (`--text` on `--bg`,
  white on `--primary-d`, white on `--green`), which pass WCAG 2.2 AA at these
  sizes. *(WCAG 2.2 AA contrast minimums, checked 12 Sep 2026 — `[recall — verify]`
  against the published table if a formal report is needed.)*
- Privacy: the setup screen says in plain words that the person is not tracked
  between punches. The result screen names who can see the punch. No other
  employee's data is ever on this page. No personal data in any error.

**Two accessibility gaps I did not close, for the clock:** a screen-reader pass
with TalkBack, and dates staying English in Hindi mode ("12 Sep").

---

## 8. The frontline bar — can a driver do it in two minutes?

| Step | Taps | Note |
|---|---|---|
| Type the server address | pre-filled | HR can bake this in |
| Type the employee ID | ~12 keys | The only typing there is |
| Set up | 1 | |
| Add to home screen | 3 | Guided, per phone type |
| Start | 1 | |
| **Every day after that: open, tap Check In** | **1** | |

First run is well under two minutes if HR pre-fills the address. **The daily
job is one tap.** That is the whole design.

---

## 9. What the business analyst must turn into acceptance criteria

1. A phone with no saved token opens on Setup. A phone with a token opens on Home.
2. Setup refuses an empty server address or an empty employee ID, with the
   exact words in §5.1, under the field that is wrong.
3. A successful registration shows "You are set up, {employee_name}" with the
   employee's real name, and Add-to-Home-Screen steps matching the phone
   (Android steps on Android, iPhone steps on iOS), with a link to the other set.
4. The token is stored and survives closing the app and restarting the phone.
   The token is never shown on screen and never logged.
5. Home shows the current state in words ("Not checked in yet today" /
   "You are checked in since {time}") and the button matches it
   (Check In when out, Check Out when in).
6. Home lists today's punches with the time of each, and says which came from
   this phone and which from the reception machine.
7. Home shows "You must be within {radius} m of {location}" whenever
   `field_status` returns a `work_location`, and shows nothing there when it
   does not.
8. One tap on the main button takes a photo, gets a position and sends a punch.
   No second confirmation.
9. The success screen shows the **server's** time, the date, the place, whether a
   photo was taken, and "In your HR record".
10. The punch appears in Frappe HR's `Employee Checkin` list with the photo as a
    **private** file, the latitude, longitude and GPS accuracy, and
    `device_id = alvoraa-field-app`.
11. Each of E1–E12 in §5.5 shows its own screen with the exact words listed. No
    raw server text and no stack trace ever reaches the screen, except the
    geofence sentence in E5, which must contain the real distance and the real
    branch name.
12. "Try again" after E5 or E6 resends the **same photo**; the driver is not
    asked to pose again.
13. E9, E10 and E11 offer no action that would fail again.
14. If the camera cannot start, Home says so and a punch still succeeds, with
    the result screen reading "Photo: Not taken".
15. At 360 px wide the page has no horizontal scroll, every control is at least
    44 px tall and no text is under 15 px — in English and in Hindi.
16. Switching to Hindi changes every label on screen and nothing overflows.
17. Nothing on this page requests a position except at the moment the main
    button is pressed.

---

## 10. Usability test plan (for the High-impact screens: Home and E5)

Five people: three drivers or guards, two office staff who have never seen the
app. On a real 360 px Android, outdoors.

| Task | Success is |
|---|---|
| Set the phone up from a card with the address and ID on it | Done in under 2 minutes, no help |
| Mark yourself present | One tap, no hesitation at the button |
| You are refused because you are too far — what do you do next? | Says "walk closer and press the button again", unprompted |
| The screen says location is off — fix it | Follows the three steps without asking |

**What would change the design:** if two of five cannot say what E5 means, the
distance sentence moves to the top and the heading becomes the instruction
("Walk 40 m closer"). If anyone taps Check In twice because nothing seemed to
happen, the busy overlay gets a bigger first frame.

---

## 11. Open items and risks

| Item | Owner | Blocks |
|---|---|---|
| Hindi strings are machine drafts | Surbhi / a native reviewer | Showing Hindi to a customer |
| Photo retention period (DPDP) | Surbhi | Nothing for the demo; a real obligation after |
| The blob manifest is a stop-gap; a real `.webmanifest` and an icon file are needed for the Android install banner | Engineering | A polished Android install |
| Offline queue (brief P11) is **not built** — E6 asks the driver to retry instead | — | Punching in a dead zone |
| Error matching is on English sentence text; translating the server's messages would break it | Engineering | Server-side i18n later |
| Sample mode ships inside the page. Remove it, or leave it — it only wakes on the literal server address `demo` | Surbhi | Nothing |
