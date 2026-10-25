---
slice: 070-readable-on-phone (YouTrack ALV-217)
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-10-24
status: draft (waiting for Surbhi's design check)
inputs: [01-product-brief.md incl. "Decisions — Surbhi, 24 Oct 2026", 01a-ux-opportunities.md, 07-devops-inputs.md §1, docs/product/design-benchmark/2026-10-24-ux-benchmark.md, 2026-10-24-ux-priorities.md, ux-learnings.md, nfr-budget.md §2 §7, design_system.html, frame.css, panels.css, portal.js, hr_api.py, attendance_correction.py]
---

# 070 · Readable and honest on a cheap phone — UX design

**Prototype (v1):** `C:\Users\Dell\AppData\Local\Temp\claude\c--Surbhi-Git-hr-app\4725b69c-fe07-474c-864d-7fa2e0ca0d3c\scratchpad\070-prototype-v1.html`
(copy: `C:/Surbhi-Git/hrlocal-data/prototypes/070/prototype-v1.html`). **Not published yet — I have
no Artifact tool in this run; the lead session publishes it and adds the link here.**

## Read this first

- **Bad news first: the brief's sentence "Nothing was sent" is not always true.** When the phone
  waits 15 s and gives up, the office may already have saved the request — the answer was lost on
  the way back. The prototype shows this case ("No answer"). I kept her sentence for the case
  where it is true (the phone knows it has no signal, so it sends nothing) and wrote a second,
  honest sentence for the other case. **⚠ DECISION 1.**
- **"Try again" can never create a second leave request.** Before it re-sends after a lost answer,
  it checks the person's own leave list for the same type and dates (an endpoint we already
  have). Frappe HR also refuses a second overlapping request on the server (Fact:
  `leave_application.py:493`), so a duplicate is blocked twice.
- **Desktop sizes do not change.** Only phones (≤ 768 px, the portal's existing phone breakpoint)
  get bigger tokens. Desktop gets the page name, the dates, "Weekly off" and the failure states.
- **No Hindi.** The brief puts Hindi in slice E. Every new string goes through `__()` so slice E
  can translate it. This differs from the handoff contract's "English and Hindi" — by the brief's
  decision, not by oversight.

**Rung: new code** (portal CSS and `portal.js`). Nothing cheaper exists: staff do not use desk
forms, and there is no setting for text size, labels or timeouts. No new page, menu item, setting,
DocType, font, image or colour.

---

## 1 · Personas and jobs

| Persona | Job in this slice | What changes for them |
|---|---|---|
| **Frontline employee** (in scope, wins any trade-off) | Read the screen and press the right thing first time on a ₹8,000 phone; know whether a request went | Bigger text and tap areas; "Weekly off"; dates in words; a wait that ends in plain words |
| Supervisor / line manager (in scope, phone) | Approve between tasks | Same tokens cover Team View and approvals; nothing else |
| **HR Manager** (desktop) | Know which page is open; no frozen card | Page name in the top bar; the HR holidays card ends its wait. Nothing taken away |
| **CXO / owner** | — | Nothing new. A link opened from WhatsApp is readable. No harm |

The one-way rule holds: no manager convenience costs the employee anything; nothing new becomes
visible to anyone.

## 2 · Evidence

**Fact** — all re-used from the 24 Oct benchmark (ALV-213 build, local bench `ppj.localhost`,
Rahul Kumar PPJ-0058, 390 × 844 and 1440 × 900). Screenshots and `report3.json`:
`C:/Surbhi-Git/hrlocal-data/ux-review/2026-10-24-benchmark/ours/`. My prototype's own look:
`…/scratchpad/shots070/` (outside the repo).

Checked in the data today (read-only console, no data changed):

- Rahul's holiday list is "Chandigarh Store Holiday List - Off Thursday". Oct: 1, 8, 15, 22, 29 are
  `weekly_off = 1` ("Thursday"); 2 Oct "Gandhi Jayanti" is `weekly_off = 0`. Nov: 9 Nov "Diwali
  next day (store closed for stock-take)" — a real long name.
- Payslips: Aug net 44,051.61 / deductions 2,348.39; Jul 32,200 / 1,800.
- His last leave requests: Casual Leave, May–June 2026, Approved.

Read in code (Fact):

- Size tokens live once, in `design_system.html` line 11. Font sizes in `frame.css` / `panels.css`
  are almost all tokens (203 × `--fs-xs`, 114 × `--fs-sm`, 101 × `--fs-base`); only 3 literal
  sizes, none under 11 px in the employee panels. **So raising tokens really does do most of it.**
- `design_system.html` is included by **7 pages** (portal, portal-next, admin, login, driver
  portal, field check-in, vendor portal). Raising the tokens there would change all seven.
- `api()` (`portal.js:5`) is the single wrapper around `frappe.call` — one place for the 15 s rule.
- `acRow()` prints "Holiday" for every holiday; the day already carries `weekly_off` and the
  holiday's own name (`attendance_correction.py:643-648`).
- `fmtDate()` uses `toLocaleDateString("en-IN", {day:"2-digit"…})` → "01 Aug 2026"; some browsers
  write "Sept" for September in `en-IN`. `[recall — verify]` on the target Chrome.
- Today's failures: payslip list → a 3 s toast "Failed to load payslips" and "Loading payslips..."
  stays; attendance month → "Could not load your attendance." with no button; leave submit (most
  tenants) → "Failed to submit leave application." at the **top** of the form; a call that never
  answers → "Loading…" / "Submitting…" for ever.
- `get_leave_summary` returns the 10 newest applications (type, dates, half day, status) and
  accepts an HR "on behalf" employee — enough for the check before a re-send.

## 3 · Findings

IDs reused from the 11 Sep review and the 24 Oct benchmark where the problem is the same.

| ID | Finding | Impact | Kind | Size | Release severity | Evidence |
|---|---|---|---|---|---|---|
| N3 | 11 px text on every phone screen | High | Fix | S | P2 | `report3.json`, every 390 capture |
| N2 | Form fields 13 px; iPhone zooms in | High | Fix | S | P2 | apply leave: 5 fields @13 px |
| N1/H6 | Controls 17–38 px tall ("+ Apply Leave" 25, arrows 24 × 25, tabs 34, × 30, header 32–36) | High | Fix | S | P2 | `report3.json` |
| MA2 | Weekly off reads "Holiday" — third sighting | High | Fix | S | P2 | att-record 390; data checked today |
| N4 | A failed or silent call never ends | High | Fix | S–M | P2 | Leave page, leave-type list, HR holidays card |
| G6 | Three date styles (`01 Aug 2026`, `mm/dd/yyyy` in date boxes, `2026-08-03`) | Medium | Fix | S | P3 | apply leave, late table |
| **U1 (new)** | "Nothing was sent" is untrue when the 15 s limit cuts off a call that reached the office | High | Fix | S | **P1 if shipped as written** — a person told "nothing was sent" re-sends or gives up on leave that is in fact pending | prototype "No answer" path |
| **U2 (new)** | Today, re-sending after a lost answer shows Frappe's raw "Employee PPJ-0058 has already applied for … : HR-LAP-…" | Medium | Fix | S | P3 | `leave_application.py:493`; shown in the prototype's Before |
| **U3 (new)** | Today's submit error appears at the top of the form; on a phone the person is at the bottom, by the button | Medium | Fix | S | P3 | `request-modals.html:10`; checklist "confirm where the action was taken" |
| **U4 (new)** | Raising tokens in `design_system.html` would also change login, admin, driver, vendor and field check-in pages | Medium | Avoid | S | P2 if it happens | 7 includers |
| G1 | Desktop top bar says "Home" on every page | Medium | Fix | S | P3 | all desktop captures |
| G8 | Grey shadow down the right edge on the phone | Low | Fix | S | P4 | every capture. **Cause not found** — engineer to locate |
| H5 | Home holiday card shows a past holiday (2 Oct on 24 Oct) | Low | Fix | S | P4 | home 390 |
| N6 | Attendance day table wider than the phone; WORK column cut off | Medium | Fix | S | P3 | att-record 390 |
| N7 | Home greets twice, shows the date twice, empty Activity card 200 px | Low | Fix | S | P4 | home 390 |
| **U5 (new)** | Desktop: 5 targets on Home and 6 in the leave form are under 24 px (WCAG 2.2 AA 2.5.8) — "Details →", "Full Portal →", holiday arrows, "All year", the footer link, the Half Day box | Medium | Backlog | S | P3 | prototype desktop measurement. **Not in this slice** (brief: phone floors only) |
| Keep | No sideways page scroll (ALV-213); payslip **Why?**; tap a day → "What went wrong?"; DTC's "Sent to …" result | — | Keep | — | — | all captures |

## 4 · Design decisions

| # | Decision | Why | Undo cost |
|---|---|---|---|
| D1 | Raise the size tokens **only at ≤ 768 px**, in **`frame.css`** (loaded by the employee portal only), not in `design_system.html` | One change reaches every portal screen (brief: "not screen by screen"); the other six pages that share the design system stay as they are (U4) | Delete one block |
| D2 | `--fs-base` goes 13 → 15 px on phones, not just the floors | The job is "read it". 13 px meets the 12 px floor but is still small body text on a cheap 5.5" screen. Measured: no sideways scroll at 360 or 390 | Change one number |
| D3 | Tap areas reach 44 × 44 px; **drawn shapes stay the same** where the shape is a circle or icon (bell, avatar, menu stay 36 px drawn inside a 44 px box) | Same look, bigger target | CSS only |
| D4 | "Weekly off" when `weekly_off` is true; otherwise the holiday's **own name** ("Gandhi Jayanti"). Both stay grey | A day off is normal, not wrong (colour means something). The name is more useful than "Holiday" | Label only |
| D5 | One date format: **`6 Nov 2026`** — day without a leading zero, three-letter English month (`Sep`, never `Sept`), four-digit year. Built from the ISO string, not `toLocaleDateString` | Same on every phone and browser; no time zone can move the day | One helper |
| D6 | Under each date box, the chosen date in words: **"Friday, 6 Nov 2026"** | We cannot change how the phone draws its own date box (it showed `11/06/2026` in the prototype's Chrome). The words make `11/06` impossible to misread | Remove one line |
| D7 | Every call ends: **no signal → at once; no answer → at 15 s**; then plain words and one **Try again**. No automatic retry (DevOps OPS-4) | Surbhi's 15 s decision; the phone knows when it is offline, so waiting 15 s then is pointless | Helper only |
| D8 | On the leave form, the failure sits **just above the buttons**, and the same primary button becomes **Try again** | The person is looking at the button they just pressed. One button, one job — no second "Try again" competing with "Submit" | Copy and placement |
| D9 | Try again after a lost answer **checks first**, then sends only if nothing matching is found | Brief risk: "Try again must not create a second leave application" | Client logic |
| D10 | A late answer still counts: a load that answers after the message replaces the message with the data; a send that answers late shows the normal success | The 15 s message is a promise to stop waiting, not a claim the call failed | Client logic |
| D11 | Phone attendance: each day is one block of two lines (day + label; then "In 09:28 · Out 18:34 · 9.1h worked · On time"). The day strip graphic is not drawn on phones; the table stays on desktop | It cannot fit at 390 px with readable text (N6). Words beside colour are better on a phone anyway. **⚠ DECISION 3** | Revert to table |

## 5 · The exact sizes (phone, ≤ 768 px) — the engineer builds these

Add to `frame.css` (employee portal only):

| Token / rule | Today | After (phone) |
|---|---|---|
| `--fs-xs` | 11 px | **12 px** |
| `--fs-sm` | 12 px | **13 px** |
| `--fs-base` | 13 px | **15 px** |
| `--fs-md` | 15 px | **16 px** |
| `--fs-lg`, `--fs-xl`, `--fs-2xl` | 18, 24, 32 | unchanged |
| `input, select, textarea, .gp-input, .form-control` | 13 px, 42 px tall | **16 px text, min-height 44 px**; textarea min-height 88 px |
| `.btn`, `.btn-sm` | 25–38 px | **min-height 44 px**, padding `0 18px` |
| In-card links ("Details →", "Full Portal →", footer link) | 18–19 px | `display:inline-flex; min-height:44px; padding:0 8px` |
| Header: menu, bell, avatar | 36 / 32 / 32 px | **44 × 44 px box**, drawn shape 36 px (padding 4 px, `background-clip:content-box`) |
| Pop-up close × | 30 × 30 | **44 × 44** |
| Month arrows ‹ › (attendance) | 24 × 25 | **44 × 44**; month select 44 px tall, 16 px |
| Holiday card ‹ › and "All year" | 17 × 21, 57 × 23 | **44 × 44** min; `.card-header` may wrap (`flex-wrap:wrap`, `min-height:56px`) |
| Finance tabs | 34 px | **44 px** |
| Slide-out menu items | 38 px | **44 px** |
| Half Day | 16 px box | whole row is the `<label>`, **min-height 44 px**, box 20 × 20 |
| Phone day row (D11) | table row | `min-height:52px`; line 2 in `--fs-sm` |

Nothing under 12 px remains on a phone. Desktop tokens are unchanged.

**Measured in the prototype** (its own script, same rules as `report3.json`):

| View | Smallest text | Targets under 44 px | Fields | Sideways scroll |
|---|---|---|---|---|
| Before, 390 — Home / Attendance / Leave / Finances | 11 px | 10 / 6 / 17 / 6 | 12–13 px | none (the day table scrolls inside its card) |
| **After, 390 and 360 — all four** | **12 px** | **0** | **16 px** | **none** |

## 6 · Screens, exact words

Words in quotes are the exact English. Unchanged words are marked (unchanged).

### Home (phone and desktop)
- Page header: "Good evening, Rahul!" / "Saturday, 24 Oct 2026" / "+ Apply Leave" (unchanged words).
- Check-in card: the "Hey there," line is removed. The date under the clock is removed (it is in
  the page header). Name, job and "Not checked in" stay — on a shared phone the name tells you
  whose account is open.
- Activity card: **not shown when it has nothing in it**. Shown as today when it has items.
- Holidays card: past days are not listed. If none are left in the month: **"No more holidays in
  October."** (month name from the card). ‹ › and "All year" work as today. Long names wrap.

### Attendance month
- Day labels: **"Weekly off"** · the holiday's own name (e.g. "Gandhi Jayanti") · "To come" ·
  "No record" · the status (unchanged).
- Day column: "1 Oct Thu" (no leading zero; the month heading carries the year).
- Phone line 2 (only for a day with attendance): **"In 09:28 · Out 18:34 · 9.1h worked · On time"**
  or "… · 17 min late" (late in red, as today). Tap the day → the existing "What went wrong?".

### Apply for Leave (pop-up)
- Under each date box: **"Friday, 6 Nov 2026"** (empty until a date is picked).
- Button while sending: **"Sending…"** (replaces "Submitting…", matching the DTC form).
- Button while checking: **"Checking…"**.
- Failure, phone had no signal (nothing left the phone):
  **"We could not reach the office. Nothing was sent."** / "Your details are still here. When you
  have signal, tap Try again." Button: **"Try again"**.
- Failure, no answer in 15 s (it may have reached the office):
  **"No answer from the office. It may have gone through."** / "Tap Try again. We check first, so it
  is never sent twice." Button: **"Try again"**. *(⚠ DECISION 1)*
- Second failure in a row: heading becomes **"Still no signal. Nothing was sent."** or **"Still no
  answer from the office."**; if a send may already have arrived and the signal is now gone:
  **"Still no signal."** / "Your details are still here. Tap Try again when you have signal. We
  check first, so it is never sent twice."
- Success: as today — most tenants: pop-up closes, toast "Leave application submitted."; DTC: the
  "Sent to …" result (unchanged). A check that finds the request shows the **same** success.
- Leave types could not load: under the box, **"We could not load the leave types."** + the reason
  line + **Try again** (reloads only the list).
- Server validation messages ("dates overlap", balance, permission) show **exactly as today**.

### Finances — payslip list
- Date line: **"1 Aug 2026 – 31 Aug 2026"**. Everything else unchanged.

### Panel loads (Attendance, Finances, Leave page, HR holidays card, every "Loading…")
- 0–15 s: "Loading…" as today (no skeleton work in this slice).
- No signal: **"We could not reach the office."** / "Check your signal, then tap Try again." /
  **Try again**.
- No answer in 15 s: **"We could not reach the office."** / "The office did not answer in 15
  seconds. Tap Try again." / **Try again**.
- Server error with no message (5xx): **"Something went wrong at the office."** / "Tap Try again in a
  minute. If it keeps happening, tell HR." / **Try again**. *(Not clickable in the prototype.)*
- Second failure: heading **"Still could not reach the office."**
- Try again reloads only that panel's call. While it runs, "Loading…" shows again.
- The box sits where "Loading…" was, amber left edge (not red: nothing is wrong with the person),
  `role="alert"`.

### Desktop top bar
- Shows the open page's name ("Home", "Attendance", "My Finances", …) instead of "Home" always.

## 7 · Flows and states

**Leave request — every path** (all clickable in the prototype; the note under the frame counts
how many requests the "server" holds):

| Network when Submit is tapped | What the person sees | Saved on server |
|---|---|---|
| Normal | Sending… → success | 1 |
| No signal (phone knows) | at once: "We could not reach the office. Nothing was sent." — nothing leaves the phone | 0 |
| → signal back, Try again | Sending… → success | 1 |
| No answer | Sending… → at 15 s "No answer from the office. It may have gone through." | 1 (answer lost) |
| → still no answer, Try again | Checking… → at 15 s "Still no answer from the office." — nothing new sent | 1 |
| → signal back, Try again | Checking… → found → success, **nothing re-sent** | **1** |
| → Try again, check finds nothing | Checking… → Sending… → success | 1 |
| Before (today), no answer | "Submitting…" for ever; re-sending later → Frappe's raw overlap message | 1, plus a confusing error |

**Rules the engineer must keep:**
1. Submit / Try again is disabled while "Sending…" or "Checking…" — a double tap cannot send twice.
2. The check: `get_leave_summary` (with `employee_id` when HR applies on someone's behalf); match
   leave type, from date, to date and half day, status Open or Approved. The check has the same
   15 s rule.
3. If nothing has left the phone, Try again sends straight away (no check needed).
4. Never an automatic retry.
5. The form's values are never cleared by a failure, by Try again, or by a late answer.
6. Closing the pop-up during a lost answer is allowed; the request may still be in the list. No
   extra screen for this.

**Other states:** empty (unchanged; Activity hidden when empty) · loading (unchanged until 15 s)
· no permission (unchanged — server messages show as today) · first-time user (nothing new) ·
long names (holiday names and job titles wrap; brand name ellipsis as today) · a team of 400
(Team View only gets tokens; no layout change) · Hindi (out of scope).

## 8 · Parity table — what the engineer builds, exactly as drawn

| # | Screen / element | Build exactly | Prototype control to see it |
|---|---|---|---|
| 1 | Phone tokens | §5 values in a `@media (max-width:768px)` block in `frame.css` | After · Phone 390 / 360 |
| 2 | Phone controls | §5 table, every row | Markers: Show |
| 3 | Desktop | tokens unchanged; top bar shows page name | Desktop 1440 |
| 4 | Home | no "Hey there,", no clock date, no empty Activity card, past holidays hidden, "No more holidays in October." | Home |
| 5 | Attendance labels | "Weekly off" / holiday's own name / grey chip; wraps | Attendance, ‹ › to November |
| 6 | Attendance phone rows | two-line day blocks, strip hidden on phone, table on desktop (⚠ D3) | Attendance, phone |
| 7 | Dates | `6 Nov 2026` everywhere; day lists "1 Oct Thu"; "Friday, 6 Nov 2026" under date boxes | Finances, Apply leave |
| 8 | Leave failure | message above the buttons, button turns into "Try again", form kept | Network: No signal / No answer → Submit |
| 9 | No second request | check first after a lost answer; button disabled while busy | No answer → Submit → Normal → Try again; note shows "saved: 1" |
| 10 | Panel failure | amber box, heading, reason line, Try again, in place of "Loading…" | Network: No signal → Attendance or Finances |
| 11 | Leave types failure | box under the select | Network: No signal → Apply leave |
| 12 | Late answer | data or success replaces the message | Not clickable — §7 rule |
| 13 | 5xx wording | §6 | Not clickable — words only |

Anything built differently from rows 1–11 needs Surbhi's yes first (prototype-parity rule).

## 9 · Accessibility (WCAG 2.2 AA) and privacy

- 1.4.4 / 1.4.10: text bigger, no sideways scroll at 360 px (measured). **Not checked at 200 %
  phone text** — the test engineer checks Android "Largest" font on a real phone.
- 2.5.8: 44 px on phones (our rule, above AA's 24 px). Desktop gaps listed as U5, not fixed here.
- 4.1.3: failure boxes `role="alert"`; preview and success stay `role="status"`. Focus stays on the
  button the person pressed — it now reads "Try again".
- 1.4.1: colour is never the only signal — every state has words; Weekly off and holidays are
  told apart by words, not colour.
- 1.4.3: the removed hero lines were white at 40–55 % opacity — low contrast; removing them helps.
- Phone attendance rows are real buttons with a spoken name ("Monday, 5 Oct 2026, open the day").
- **Privacy:** nothing new is shown to anyone. The check reads only the person's own leave list (or,
  for HR on behalf, a list HR can already read). No personal data in the new messages.

## 10 · Checks before hand-off

- **Nielsen:** visibility of system status (every wait ends and says what happened) · match with
  the real world ("Weekly off", dates in words) · error recovery (plain cause + one action, form
  kept) · error prevention (no double send) · consistency (one date format, one failure pattern).
- **Persona walkthrough — frontline, apply leave with a dropping signal:** before: tap Submit →
  "Submitting…" for ever → retype later → raw overlap error → call HR. After: tap Submit → message
  in ≤ 15 s → Try again when the bar returns → done. Two minutes on a phone: yes.
- **Red team:** brand new person — the words say what to do. No signal for a long time — the form
  waits; nothing is lost unless they close it. Answer arrives late — success replaces the message.
  HR applying on someone's behalf — check uses that person's list. 10 applications already newer
  than the lost one — impossible in practice within one minute; Frappe's overlap check is the
  backstop.
- **Refusals:** none touched. No nagging, no auto-retry loop, no dark pattern.

## 11 · Usability test plan (High impact)

Five people, on their own phones: 2 DTC HR/managers and 3 staff once DTC and Grace logins exist
(Surbhi's 24 Oct decision). Tasks: (1) find your 8 Oct attendance and say what kind of day it was;
(2) apply for 6–7 Nov leave; mid-task we switch the phone to airplane mode before Send, then back;
(3) read August's take-home pay and the payslip dates.
**Success:** all three with no help and no zoom; in task 2, nobody re-types, nobody sends twice, and
each can say whether the request went. **Would change the design:** anyone reading "It may have gone
through" as "it failed" and giving up → reword; anyone tapping Try again more than twice in a row →
add a "When to try again" line.

## 12 · What the business analyst must turn into acceptance criteria

1. At 360 and 390 px on every employee portal screen: no text under 12 px, no field under 16 px,
   no control under 44 × 44 px, no sideways page scroll. Desktop sizes unchanged.
2. Other pages that include `design_system.html` look exactly as before.
3. A weekly-off day shows "Weekly off"; a named holiday shows its own name, HTML stripped.
4. Every date shown to a person reads `6 Nov 2026` (no leading zero, never "Sept"); date boxes show
   the date in words underneath.
5. Every call: offline → the message at once; no answer → the message at 15 s; 5xx → its message;
   validation and permission messages unchanged; one Try again; no automatic retry.
6. The leave form keeps every value through any failure; the button reads Sending… / Checking… /
   Try again as in §6; it is disabled while busy.
7. Try again after a lost answer never creates a second Leave Application (test: server saves,
   answer dropped, Try again → exactly one record).
8. A late answer replaces the message (load) or shows success (send).
9. Home: no "Hey there,", no clock date, no empty Activity card, no past holidays, the "No more
   holidays in …" line. Desktop top bar shows the page name. No right-edge shadow.
10. Phone attendance rows as in parity row 6 (if ⚠ DECISION 3 is yes).

## 13 · Not in this slice

Desktop targets under 24 px (U5) · skeleton loading · Hindi · offline drafts that survive closing
the pop-up (UXB-12) · the check-first for forms other than leave (see ⚠ DECISION 2) · desktop menu
words (G2) · Team View fixes (TV3/TV4) · DTC's holiday list (ALV-92).

## 14 · ⚠ Decisions for Surbhi

**⚠ DECISION 1 — the wording when the answer is lost.**
*Decision needed:* may the "no answer" case say "No answer from the office. It may have gone
through." instead of "Nothing was sent"? *Context:* after 15 s the phone cannot know whether the
office saved it; in the prototype it did. *Conflict:* the brief's WOW sentence vs. honesty (an
uncertain result must not sound certain). *Who:* every employee sending leave on a weak signal.
*Options:* (a) **recommended** — two sentences: "Nothing was sent" only when the phone was offline
and sent nothing; the honest sentence otherwise; (b) one sentence everywhere ("Nothing was sent") —
untrue in the lost-answer case, and a person may give up on leave that is pending. *Risk if it
waits:* the copy blocks the spec. *Owner:* Surbhi.

**⚠ DECISION 2 — other forms.** *Decision needed:* does the full leave pattern (check first, then
re-send) cover only the leave form in 070? *Context:* expense claims and advances have **no**
server duplicate guard, so a blind Try again after a lost answer could file a second claim.
*Options:* (a) **recommended** — leave form gets the full pattern; every other form gets the
no-signal case (nothing sent, form kept, Try again) and, for a lost answer, "No answer from the
office. It may have gone through. Look in your list before you send it again." with **Close**, no
Try again; (b) build a check for every form — larger, needs per-form matching rules; (c) leave form
only, other forms unchanged — they keep "Loading…" for ever, which the brief forbids. *Owner:*
Surbhi, with `hrms-product-manager` for scope.

**⚠ DECISION 3 — phone attendance rows.** *Decision needed:* on phones, replace the 8-column day table
with two-line day blocks and drop the strip graphic there (words carry the same facts)? It is
brief item 5 (N6), "first to cut". *Options:* (a) **recommended** — yes, as drawn; (b) keep the table
scrolling inside its card (works today, but WORK and ARRIVAL stay off-screen and the text will be
wider). *Owner:* Surbhi.

---

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| ⚠ DECISION 1, 2, 3 above | Surbhi | Copy, scope of the submit pattern, attendance phone layout |
| Does any other portal screen print "Holiday" for a weekly-off day (e.g. the older calendar `.cal-cell`)? | `hrms-fullstack-engineer` (grep) | AC 3 coverage |
| What causes the right-edge shadow (G8)? | `hrms-fullstack-engineer` | Clean-up item only |
| Does Frappe's `frappe.call` on this version raise its own pop-up on a network error that would show alongside ours? | `hrms-fullstack-engineer` | Whether the engineer must suppress it |

## Assumptions

- `[ASSUMPTION]` Rows 5–7 Oct (worked days), the attendance tiles, the second goal's title, the reason
  text and the Leave Application number in the overlap message are **Sample** in the prototype.
- `[ASSUMPTION]` `navigator.onLine === false` is reliable enough on Android Chrome to say "Nothing was
  sent" before sending; if the phone wrongly says online, the call fails and the honest "may have
  gone through" wording applies — never the false one.
- `[ASSUMPTION]` 15 s counts from the moment the call starts, for loads, sends and the check alike.
- `[ASSUMPTION]` The "Requesting 2 days of 5 available" preview in the prototype is computed by the
  prototype, mimicking `preview_leave_request`; the real one comes from the server.
- `[ASSUMPTION]` ALV-112 is live, so CSS and JS reach phones (DevOps §1).

## Handoff note

To `hrms-business-analyst`: §12 is your AC list and §8 the parity table; do not write the spec's
failure copy until ⚠ DECISION 1 and 2 are answered. Watch two traps: the tokens must go in
`frame.css`, not `design_system.html` (seven pages share it), and "Try again" must be tested with
a call that **succeeds on the server but loses its answer** — that is the only case that can make a
duplicate, and a plain "network off" test will never find it. The DTC leave path (`lpSubmit`) has
its own failure sentence today; it must use the same words.

**Subtract pass:** removed a "slow network" banner during the first 15 s, a skeleton, a separate
"Try again" button inside the leave message (the footer button already does it), automatic retry,
a "tried again at 10:42" timestamp line, a different chip colour for named holidays, and Hindi
drafts. Kept the 5xx wording (one string, no screen) and the "Still …" headings (without them a
second tap looks broken).

## Decisions — Surbhi, 25 Oct 2026

"Go with this design, seen all the designs in the prototype." Prototype v1 (https://claude.ai/artifact/6EMBxjZa97BZWwSPnfVJeY) is the approved design; build it as drawn (parity rule).
- D1 wording: "We could not reach the office. Nothing was sent." only for no signal; "No answer from the office. It may have gone through." when the answer is lost — as drawn.
- D2: check-then-resend Try again on the leave form only. Expense claim and advance forms say "Look in your list before you send it again" with Close, no Try again (not drawn; Claude's recommendation, confirmed by DevOps OPS-5 — tell Surbhi if this changes).
- D3: on phones each attendance day is a two-line block; the day strip graphic is dropped on phones — as drawn.
- D4: one date format everywhere: "6 Nov 2026" (no leading zero). The ALV-213 leave cards ("06 Nov") change to match.
