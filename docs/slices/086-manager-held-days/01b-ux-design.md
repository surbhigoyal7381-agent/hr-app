---
slice: 086-manager-held-days
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-11-20
status: draft
inputs: [01-product-brief.md (with Surbhi's decisions, 20 Nov 2026), 01a-ux-opportunities.md, 07-devops-inputs.md §1, .claude/context/ux-learnings.md]
---

# 086 Whole team: find held days and send the missing times to HR

**Prototype:** `docs/slices/086-manager-held-days/prototype-v1.html` (also copied to `/Users/mac/hrlocal-data/prototypes/086-manager-held-days/prototype-v1.html`). **I have no Artifact tool in this run, so it is not published.** The session that ran me publishes it. It uses invented names (tagged "Sample"). No tenant data is in it.

## Bottom line

1. **One page, one new component, no new screen.** The "Whole team" page gets a **Held** chip, a time box on each held row, and one "Send N to HR" bar. One confirm. One result.
2. **Bad news first, in bold: Surbhi's decision 4 (an optional reason box) reverses a privacy rule slice 085 wrote.** 085's PRIV-2 says a held-day request carries "the time and In/Out and nothing else", and its test AC-28 asserts there is no reason or explanation box. I drew the box, but it needs a yes and a security check (⚠ COMPLIANCE, section 9).
3. **I could not run the real portal.** Everything about "today's page" is code reading of `portal.js` lines 15600 to 15930 and `attendance_correction.py` in this worktree at `2e31151f`. No login, no tenant, no screenshots of the real page. The "Today's page" view in the prototype is drawn from that code, not photographed.

## 1. Frame

A line manager (laptop, sometimes phone), at the start of the week or before payroll cut-off, opens Attendance, then "Whole team", and wants to give the missing punch time for every held day of her direct reports in one pass.

**Serves:** line manager. **Changes for the others:**
- **Employee:** nothing to do. Their day sheet already says who sent a request (085). The wording for "a manager sent a time for you" needs a check (section 8, AC list).
- **HR manager:** each request arrives as a one-day request with the manager's name on it, and any note. HR decides each one. No bulk approval.
- **CXO:** sees nothing new.
- **Frontline supervisor on a phone:** the phone layout is drawn (section 5).

**The one-way rule check:** this makes the manager's work easier. It does not make the employee's worse: nothing is decided by the manager, the employee still sees the request, and the employee can still send their own time.

## 2. Evidence: what I read, and what I did not

| Label | What |
|---|---|
| **Read (proven)** | Worktree `.claude/worktrees/086-manager-held-days`, branch `slice/086-manager-held-days`, HEAD `2e31151f`. `portal.js` `trState`, `trOpen`, `trLoad`, `trChips`, `trRows`, `trDay`, `trAskForm`, `trSubmit`, `trPager` (15600 to 15930). `panels.css` `.tr-*` rules (2543 to 2610) and `frame.css` phone rules (332 to 345). `policies.html` lines 20 to 50 (the page markup). `attendance_correction.py`: `_flag` (2048), `team_days` (2111), `raise_for_report` (2342), `_held_request_fields` (1231), `_held_flags` (995). `held_day.py` `validate_missing_time` (240). `acHeldForm` and `acHeldSubmit` in `portal.js` (about 6355 to 6400). |
| **Not done** | No browser, no login, no tenant, no measuring of the real page. Hindi not checked by a native reader. |
| **Surfaces searched for "does the page already do this?"** | The team page code above, the held form (one person's month), the HR request screens by name only. It does not: the row has no held field, the chip follows punch count, "Ask HR to fix" sends a reason and no time. |

## 3. Benchmark

Unchanged from `01a` §2 (read on 20 Nov 2026, search summaries only, nothing seen running). One line: Keka lets a manager apply many regularisations and **skips approval**. We keep HR's decision. **Deliberately not copied:** bulk that skips HR, one status or one time for many, a manager league table, reminders.

## 4. Findings on the page as it is (code reading)

| ID | Impact | Kind | Size | Severity | Finding |
|---|---|---|---|---|---|
| WT1 | High | Fix | M | P2 | The row's only action, "Ask HR to fix", asks for a reason and sends no time. It cannot release a held day. (`trAskForm`, `trSubmit`) |
| WT2 | High | New | S | P2 | No Held filter. The chip "No clock-out" is judged from the punch count (`_flag`), not from the Held status that holds pay. |
| WT3 | Medium | Fix | S | P3 | `can_raise` is per row, so the button is absent where the server would refuse. |
| WT4 | Medium | Keep | | | **Keep:** "no button where the server would refuse" (`can_raise`), the real total in "Showing 1 to 50 of N" (counts are for the whole period, not the page), the name as a real keyboard button, grouping by Person or Date, "Show: My direct reports / Everyone below me". |
| WT5 | Medium | Fix | S | P3 | Chip counts sit inside the chips ("No clock-out 12"). This is the page's existing pattern, so I keep it for Held, but see ⚠ DECISION UX-4. |
| WT6 | Low | Keep | | | A refusal shows the server's own sentence (`trErr`). I keep that for every refusal below. |

## 5. The design

### 5.1 The flow

1. Manager opens Attendance, picks "Whole team". Same page, same filters.
2. A new chip **Held 11** is there (only when at least one held day exists; zero-count chips are already hidden, `trChips`). She taps it.
3. Above the list: one sentence saying what Held means and one line splitting the number: **"9 need a time from you · 2 waiting for HR"** (and "· 2 are another manager's to send" when she looks at the whole line).
4. Each row she can act on has a time box. She types the time for the days she knows. Rows with a time get "Ready". Rows left empty stay as they are.
5. A bar sticks to the bottom: **"3 days ready. HR reviews each day. Your name goes on each request. [Send 3 to HR]"**. It appears only when at least one row is ready.
6. She taps Send. **One confirm** opens: it lists each person, day and time, says "Your name goes on each request. HR decides each one. Until HR does, the day stays held.", has the optional note, and two buttons.
7. While sending: the button says "Sending 3... please keep this page open" and is disabled. Nothing else moves.
8. Result: a banner at the top of the list, and each row shows its own outcome (5.5).

**One component:** the time box belongs to the row, not the chip. It shows in "Everything" and in "Held" alike.

### 5.2 The Held chip, and how it differs from "No clock-out" (answers Q6)

- **Look:** amber outline with a pale amber fill, and the word "Held". Not red: red means wrong or overdue, and a held day is waiting, not wrong. Selected looks like every other selected chip (filled purple).
- **Explained on the page:** "Held days have a punch missing, so pay for the day is on hold until HR fixes it. Give the missing time, and HR decides."
- **Count rule:** the chip counts every Held day in view (the same days the list shows), including days already waiting for HR. The line under the chips splits it: need a time / waiting for HR. So the number on the chip always equals the rows underneath.
- **Why they differ today:** "No clock-out" is a punch-count guess and keeps flagging a day after HR has fixed it (the day is Present with one punch). Held is the status that holds pay and ends when HR decides.
- ⚠ **DECISION UX-1 (Q6, owner: Surbhi, with the engineer on feasibility).** **Recommendation: on a tenant where the hold is switched on, show Held and hide "No clock-out"; where it is off, show "No clock-out" only, as today.** The two chips then never appear together, because for the same tenant they count nearly the same days with different numbers, and a manager would have to guess which one is real. The prototype's "Page" switch shows both versions. Cost of the alternative (keep both): two chips, two numbers, one question from every manager. The engineer must confirm the page can tell whether the hold is on for the tenant.

### 5.3 A held row (what each part says)

| Part | Words | Source |
|---|---|---|
| Person and day | The person's name (Group by Person: the day is the row title) | existing `trDay` |
| Tag | "Held" (amber, with words, not colour alone) | new |
| Real punches | "Punches: **09:00 · 09:04 · 18:10** · Shift 09:00-18:00" | the day's punches, already read by `team_days` |
| Time box, one punch that is an arrival | "What time did Ravi leave?" | same words as `acHeldForm` |
| Time box, one punch that is a leaving | "What time did Anita arrive?" | same |
| Time box, 3 or 5 punches | "What time was the missing punch?" plus "Which punch is missing?" with two buttons **Arrival** and **Leaving**. **Neither is chosen.** The row is not Ready until both are filled. | `acHeldForm` shows a default of Out; decision 2 says no pre-filled guess, so I removed the default |
| Help under the box | "Type the time you know it was. Nothing is filled in for you." | new |
| "Ready" | "✓ Ready" (green, word beside the tick) | new |

The time box is an ordinary time field (`type=time`), the same as the held form on the month page. 16 px text and 44 px tall on a phone (`frame.css` phone rule), 24 px minimum target on desktop.

**Three kinds of row, all in the list, worst first:**

| Row kind | Shows | Sorted |
|---|---|---|
| **Needs a time from you** (direct report, held, no request yet) | the time box | first |
| **Waiting for HR** | "**Waiting for HR.** Sakshi Verma sent 18:15 on 19 Nov 2026. HR will decide." Or "Imran Khan sent 18:05 himself on 19 Nov 2026. HR will decide." No time box. | second |
| **Not yours to send** (skip-level) | "Deepak reports to Meena Joshi, so Meena sends this one. You can see the punches, but you cannot send a time for this day." No time box, no button | third |

A day stays Held after the manager sends: pay is held until HR decides. So the row **does not disappear**; it turns into "Waiting for HR". That is also why the chip count does not fall after sending.

**Skip-level rows (decision 1).** They appear only under "Show: Everyone below me", exactly as the page works today. They show real punches. They have no time box and no button, and the sentence above says why in plain words, naming who sends it. ⚠ **DECISION UX-2 (owner: engineer, Q7).** The brief says to show the line "where the ALV-328 tick allows". I did not open that tick. My design: **if the tick does not allow it, the "Everyone below me" choice is not offered at all** (no greyed option, principle 7). If the tick allows punches only for part of the line, rows without punches are not listed. The engineer must say which it is.

### 5.4 The send bar, the cap, the confirm

- **Bar:** sticks to the bottom of the list. Appears only when at least one row is Ready. Never greyed. "N days ready." is the count of Ready rows on the whole list, not only the visible page.
- **Cap (decision 3):** at most 50 per send. Above 50 the bar adds: "50 at most in one send. The first 50 go now; 13 stay here for the next send." The page already shows 50 rows a page, so in practice the cap matches one page. Times typed on a page stay while she changes page (kept in memory only).
- **The confirm** (role dialog, focus on the note box, Escape and "Go back" close it, Tab stays inside, focus returns to the Send button):
  - Title: "Send 3 days to HR?"
  - "Your name goes on each request. HR decides each one. Until HR does, the day stays held."
  - A list: "Ravi Kumar · 16 Nov 2026 · left 18:30", one line per day, scrolls after about 6 lines. This is the brake on a mistyped time: she reads what she is saying.
  - "Note for HR (optional)", with help "The note goes on all 3 requests. HR and the person can read it. Please do not write health or family details."
  - Buttons: **Send 3 to HR** and "Go back". No pre-ticked box, no guilt wording.
- **Where the optional reason lives, and why:** one note box in the confirm, applied to every request in this send. A box on every row would put a text field next to every time and double the height of the list for a thing that is optional. A shared note fits the real case (one cause for many days, such as "machine was slow that week"). A day that needs its own explanation can go in a second, smaller send.

### 5.5 The result after sending (and every refusal)

**Banner at the top of the list** (stays until the next send or a reload; it announces itself to a screen reader):

| Case | Words | Colour and icon |
|---|---|---|
| All sent | "**3 of 3 sent to HR.** HR will decide each one. Until then the days stay held." | green |
| Some refused | "**Sent 48 of 50 to HR. 2 not sent.** The reason is on each one below. The 48 that went are waiting for HR." with a button "Go to the first one" | amber |
| None sent | "**Nothing sent. 3 not sent.** The reason is on each one below. | red |
| Offline | "**Nothing was sent.** You are offline. The times you typed are still here. Connect, then press Send again." | red |
| Answer lost | "**We did not get an answer from the office.** Some days may have gone through. Checking now, please do not send again." Then, after the check: "**Checked with the office.** 3 of 3 sent to HR..." | amber |

The answer-lost wording follows the 070 decision ("may have gone through"). It reuses 085's AC-30 guard.

**Each row:** a sent row turns into "✓ Waiting for HR. You sent 18:30 just now. HR will decide. Until then the day stays held." A refused row stays as it was, keeps the typed time, and gets a red box under it: "**Not sent.** [reason] Change the time and send again." The box goes away when she edits the time. The refused row is not counted as Ready until she edits it.

**Refusal words** (the server's own sentence wins when it names a real number: pattern from slice 008):

| Cause | Words |
|---|---|
| Missing leaving time is not after the last punch | "18:05 does not fit the punches. A leaving time has to come after the last punch (18:10)." |
| Missing arrival time is not before the first punch | "09:30 does not fit the punches. An arrival time has to come before the first punch (09:00)." |
| A time that has not happened yet (today's day) | "It is only 14:20 now, so 18:30 has not happened yet. Enter the time the person really left." |
| Too far from the shift (only if the engineer adopts it) | "23:30 is more than 4 hours after this shift ends (18:00). A missing punch for this shift cannot be that late." |
| Request already filed | "Already waiting with HR. Someone sent a time for this day a moment ago, so nothing more is needed." The row then shows as Waiting for HR, and the banner counts it as not sent by this send. |
| Day no longer held | "This day is no longer held. A machine punch or HR may have fixed it. Reload the page to see where it stands." |
| Not a direct report (should be unreachable) | The server's own sentence: "Deepak Rao does not report directly to you, so this is their own manager's to raise." |
| Anything else | "Could not send this one. Nothing was filed for it. Try again." No raw server text, no names or ids in the words. |

### 5.6 States

| State | What the person sees |
|---|---|
| Loading | The existing "Loading..." line; with the Held filter run on the server before the punch read (OPS-39). Every loading state ends with "Try again" after a timeout (checklist). |
| Empty (no held day) | **"Nothing is held."** "No day in this period is waiting for a missing punch. When somebody forgets to punch out, the day shows up here." Button "See everything". Reached when she is on the Held view and the last held day has been decided. (The chip itself is hidden at zero, as every chip is.) |
| First time | Same as the list. The sentence explaining "Held" is the first-time help. |
| No direct reports, or nobody | The existing "Nobody reports to you, so there is nothing to review here." Unchanged. |
| Failed load | The existing server sentence (`trErr`). |
| No permission | There is no button where the server would refuse (`can_raise`). The time box is the same: it exists only on rows the server says are hers to send. |
| Long names, 400 people | The page already pages 50 rows at a time. The bar and confirm count Ready rows across pages. The confirm list scrolls. |
| Sending (up to 50 days) | Button disabled, label says "Sending 50... please keep this page open". DevOps estimate (not measured): 3 to 5 s for 50 (OPS-40). If it takes longer than about 10 s, the lost-answer path takes over. |
| Typed and then the network drops | Typed times stay on the page (in memory). **Not saved to the phone's storage:** 441 DTC logins share handsets, so nothing about attendance goes in `localStorage`. Reloading the page loses unsent times; the bar's first line makes unsent work visible. |

### 5.7 Phone (390 px, drawn in the prototype)

- Each day is a card. Person, day, tag, punches, then the time box full width, 16 px text, 44 px tall.
- **Arrival / Leaving** are two full-width buttons, 44 px tall, words only (no icons), neither chosen.
- The **send bar sticks to the bottom, above the portal's own bottom bar**, with a full-width 44 px button. The count text sits above it.
- The confirm becomes a **bottom sheet** pinned to the app, with the same content. The list inside scrolls; the Send button stays in view.
- Filters wrap as they do today (`.tr-f` takes the row). Chips wrap.
- The prototype's phone rules are the same rules the product would put in `@media(max-width:768px)` (`frame.css:332`), copied under a wrapper class.
- **Not yet tested:** 200% text (195 px of room), 360 px, 3G timing. The prototype is at 390. **P3 until measured.**

### 5.8 Words in Hindi (machine-drafted, needs a native reader before it ships)

Held: रुका हुआ. Send 3 to HR: 3 HR को भेजें. Your name goes on each request: हर अनुरोध पर आपका नाम जाएगा। Waiting for HR: HR के फ़ैसले का इंतज़ार. Note for HR (optional): HR के लिए नोट (वैकल्पिक). Which punch is missing? कौन सा पंच छूटा है? Arrival / Leaving: आने का / जाने का. Nothing is held: कोई दिन रुका हुआ नहीं है. The prototype's language switch shows these; the rest stays in English. Hindi runs about 30% longer: the chip and bar wrap, they do not clip.

## 6. Privacy and accessibility

**Privacy**
- **Who sees what:** a manager sees the punches she could already see (direct reports; the whole line only where the ALV-328 tick allows). No reason for absence is shown, and none is asked on a held day except the optional note.
- ⚠ **COMPLIANCE UX-3 (owner: `hrms-security-privacy-engineer`, then Surbhi). The optional note reverses 085's PRIV-2.** PRIV-2 and AC-28 say a held request has no reason or explanation. `_held_request_fields` today forces `explanation` to none. Decision 4 asks for a note, so: (a) it needs a yes that PRIV-2 is changed for the manager's send only; (b) a free-text box can hold health or family detail; (c) who reads it. **Recommendation:** adopt it, as one shared note per send, max 140 characters, plain text, shown to HR and to the employee on their day sheet (so a manager cannot say something about a person that the person cannot see), with the help line above. **Not adopted by me until security says yes.** If not adopted, remove the note box; the rest of the design stands.
- **No watch view:** no count of how many days a manager sent, no list of who forgets most, no reminders, no ageing colours.
- **Shared handsets:** nothing in `localStorage` or `sessionStorage`; Back after logout shows nothing from cache (checklist item for pages holding HR data).
- **Errors and logs:** refusal words carry the person's name only on screen to the manager who may already see them; none in logs or exports (as 085 PRIV-2).
- **No dark patterns:** nothing pre-filled, nothing pre-ticked, no nagging, no guilt wording. "Go back" is as visible as "Send".

**Accessibility (WCAG 2.2 AA, `nfr-budget.md` §7):**
- Every field has a visible label (the question above it). In/Out is a labelled radio group with the question as its name.
- Colour is never the only signal: Held, Ready, Waiting for HR and Not sent all carry words.
- The confirm is `role="dialog"` with `aria-modal`, a focus trap, Escape, and focus returned to Send. (Slice 059 and 078 found portal dialogs without these.)
- The banner is a status region (`aria-live="polite"`); a refusal row is `role="alert"`.
- Typing a time never redraws the page: only the Ready mark and the bar change, so the keyboard stays where it is (learning, 4 Nov).
- Targets: 44 px on a phone, 24 px minimum on desktop. Text 12 px or more (`--fs-xs` is 11 px on a laptop: **use `--fs-sm` for the explanatory lines, and raise `--fs-xs` as the design-system decision already open**).
- Dark theme drawn. Amber on its pale amber fill uses `--amber` and `--amber-lt`, which are re-toned in the dark theme.

## 7. Nielsen, persona walk, frontline bar, red team

**Heuristics:** system status (banner, per-row state); real world (words from the held form); user control (Go back, Escape, nothing sent without the confirm); consistency (same time-box words as the month page, same chip style); error prevention (confirm lists what is being said, no blanket time, no default, refusals in words); recognition over recall (real punches beside the box); minimalist (no new page, one note box).

**Persona walk, 10 held days:** today about 50 taps and 10 reloads (UX estimate from code, not timed). Now: tap Held, type 10 times, tap Send, tap Send in the confirm: about 3 taps plus 10 typed times, **no reload**. HR: unchanged queue, 10 one-day requests with the manager's name. Employee: day sheet shows the request.

**The frontline bar (two minutes on a phone):** a supervisor with 10 held days: open the page (3G, skeleton within 300 ms, `nfr-budget.md` §2), 10 times typed, one send. Plausibly under two minutes. **Not timed: experiment needed** (section 10).

**Red team:**
- *Brand-new manager:* the first line explains Held; "Nothing is filled in for you" says what to do.
- *Expert in a hurry:* Tab goes time, time, time. Enter in a time box does not send (it must go through the confirm).
- *No data:* empty state with "See everything".
- *400 people / 100x:* Held is filtered on the server before the punch read (OPS-39); 50 a page; cap 50 a send.
- *Network drops mid-send:* three words for three cases (offline, answer lost, refused). Typed times stay on the page.
- *Double tap:* the button is disabled while sending; the server refuses a duplicate (OPS-44).
- *Manager types the wrong time and confirms:* **she cannot take it back.** `withdraw` works only for the employee's own request (`attendance_correction.py`, `doc.employee != me.name`). ⚠ **DECISION UX-5 (owner: Surbhi; engineer on feasibility).** Recommendation: **do not add "Take back" in this slice**; the confirm list is the brake and HR can decline a wrong time. Watch the HR decline count (brief §9) and add it later if it shows. If she wants it now, the Waiting row gets one "Take back" button.
- *Chip and status disagree:* see UX-1.
- *Manager leaves or changes mid-flow:* request keeps the name stamped at filing (brief §12).

## 8. What the business analyst must turn into acceptance criteria

1. The Held chip follows `status == "Held"`, is hidden at zero, and its number equals the number of Held rows in the list at the current Show setting, across all pages (UX-1 decides what happens to "No clock-out").
2. The line under the chips splits the number: needs a time / waiting for HR / another manager's.
3. Time box on a held row the server says is the caller's to send; none on skip-level rows; skip-level rows say who sends, in the words in 5.3. No button on rows the server would refuse.
4. One time per row. **No default** In/Out, no pre-filled time, no "apply to all". Ready only when the time (and In/Out when the day has 3 or 5 punches) is filled.
5. The bar appears only when at least one row is Ready; counts across pages; send button's label carries the number; 50 at most per send and the words for 51 or more.
6. Exactly one confirm, listing person, day, In/Out and time per row, with the sentence "Your name goes on each request." and the optional note (subject to UX-3).
7. The send is one call carrying a list, answered with one outcome per day. Never one browser call per day (OPS-41). The payload per day is date, employee, time, In/Out; the note is shared (UX-3). A test presses the real Send and asserts the payload.
8. Per-day result: sent, refused with a plain cause, already filed. Banner states "N of M sent" in every case; the numbers add up.
9. Every refusal in 5.5 has its exact words, and shows no raw server text. The time-fit and future-time refusals exist **in the server** (brief Q4: the engineer must confirm `validate_missing_time` or the request refuses them; today only "day is Held", "one day" and "In or Out named" are read).
10. A sent row becomes "Waiting for HR" in place; the Held count does not fall until HR decides.
11. A duplicate for the same person and day is refused (OPS-44), and a double tap files once.
12. Lost answer: reuse 085 AC-30; the check says how many went.
13. The old "Ask HR to fix" button is hidden on Held rows the time box serves (Q5, once the engineer confirms what HR's approval does to a request with no time); it stays on non-held rows.
14. A day sheet line for the employee when a manager sent a time (wording check, brief §5).
15. Phone: 16 px fields, 44 px targets, bar fixed above the portal's bottom bar, confirm as a bottom sheet; checked at 390, 360 and 200% text.
16. Typed times are not stored in `localStorage` or `sessionStorage`; Back after logout shows nothing.
17. No per-manager count, no ranking, no reminder anywhere in this slice.
18. Accessibility items in section 6, each testable by keyboard.

## 8a. Parity table for Surbhi

Any later difference between the code and prototype v1 needs her yes. The prototype draws these, in this order: Held chip (amber), explanation line, split line, row with real punches and time box, In/Out buttons with no default, Ready mark, bottom bar with count, one confirm with list and note, banner, per-row result, the three row kinds, empty state, phone layout, Hindi for the key words, Today-versus-086 switch. The prototype's fake office applies the refusal rules above so every refusal can be seen; the real rules are the server's.

## 9. Decisions and flags

| Marker | Item | Owner | Blocks |
|---|---|---|---|
| ⚠ COMPLIANCE UX-3 | Optional note reverses 085's PRIV-2. One shared note, 140 characters, visible to HR and the employee? | `hrms-security-privacy-engineer`, then Surbhi | The note box (and AC-6) |
| ⚠ DECISION UX-1 | Show Held and hide "No clock-out" when the hold is on? | Surbhi; engineer on feasibility | Chip wording and AC-1 |
| ⚠ DECISION UX-2 | If ALV-328's tick is off, "Everyone below me" is not offered (not greyed) | engineer to confirm what the tick does to `team_days` | Skip-level rows |
| ⚠ DECISION UX-4 | Count inside the chip (the page's own pattern, and equals the list) versus a count only in the heading (the 083 learning). I kept the page's pattern. | Surbhi | Chip look |
| ⚠ DECISION UX-5 | No "Take back" in this slice? | Surbhi | The Waiting row |

## 10. Usability test plan (High impact: money moves)

Five supervisors or line managers (two on a shared Android phone, ~360 px, 3G), real or realistic held days. Tasks: (1) find the held days; (2) send times for six of ten days, leaving four unsent; (3) read what happened after one is refused; (4) fix and resend. **Success:** all five finish tasks 1 and 2 in under two minutes on the phone, nobody types the same time into every row, and every person can say "HR decides" and "my name goes on it" in their own words. **A result that changes the design:** two or more people read "Waiting for HR" as "done" (the banner or the row wording changes); two or more miss the unsent four; anyone tries to take a request back (UX-5 moves to build).

## 11. Not in this slice (for Surbhi to decide)

Double-scan label ("Two scans 4 minutes apart"); amber flag to HR on odd times; "Take back" for the manager; per-row note; any reminder or ageing colour; bulk approval (rejected in 085); a company held-days figure for the CXO.

## Subtract pass

Removed from my own first idea: a client-side check of every refusal (the server must do them anyway, so two copies would drift); a per-row note box; a progress bar for the send; a "select all" tick; a separate "waiting" filter (the split line says it); a second confirm for more than 50. Nothing in the page's existing filters changes.

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| UX-1 to UX-5 | See section 9 | as listed | as listed |
| Q4 | Does the server already refuse a time that does not fit the punches, a future time, or a time far outside the shift? | engineer | Refusal AC 9 |
| Q5 | What does HR's approval do to a held day when the request has no time? | engineer | Hiding "Ask HR to fix" on Held rows |
| Q7 | What does ALV-328's tick change on `team_days`? | engineer | UX-2 |
| Q8 | Can the page tell the hold is on for the tenant? | engineer | UX-1 |
| Q9 | Does 085's day-sheet wording read right when a manager sent the time? | analyst | AC 14 |

## Assumptions

- [ASSUMPTION] The portal's real chip, fonts and spacing are as in the CSS I read; I did not see them render.
- [ASSUMPTION] A 4-hour allowance around the shift applies to the "too far" refusal (from the shift-window setting in my notes; the engineer must confirm).
- [ASSUMPTION] A sent request leaves the day Held until HR decides, so the row stays in the list.
- [ASSUMPTION] The 50-row page and the 50-day cap line up; if the page size changes, the "first 50" wording must follow.
- [ASSUMPTION] 3 to 5 s for a 50-day send (DevOps estimate, not measured).

## Handoff note

For the analyst: the screen is the existing page plus one component, so most acceptance criteria are about words, counts that must equal their list, and per-day results that must add up. Watch three traps. (1) A sent row stays in the list as "Waiting for HR", so the chip number must not fall until HR decides, and the split line must say so. (2) UX-3 is not mine to settle: if security says no, drop the note box and AC-6's note, and nothing else changes. (3) The prototype's fake office shows refusals the real server may not make yet (Q4): do not write those acceptance criteria as met until the engineer reads `validate_missing_time` and the request's own checks. I did not run the real portal, so every statement about today's page is code reading, not a screenshot.


---

## v2 (21 Nov 2026): one day, one reason per row, built in 087's language

**Prototype:** `prototype-v2.html` in this folder (copy at `/Users/mac/hrlocal-data/prototypes/086-manager-held-days/`). **Not published: I have no publish tool in this run.** Everything not named here is as v1 section 5. All names, times and reasons are **Sample**. It reuses 087 prototype-v4: the same tokens, the strip, the punch timeline with tappable gaps, the add sheet, the bottom sheet and the status chips. Checked by script at 360 px, desktop, Hindi, 55 rows: nothing wider than the screen, no target under 44 px, no field text under 16 px, nothing under 12 px. Looked at once, light and dark. I did not run the build; the page is not in the product yet. Hindi is machine-drafted.

**Serves:** the line manager (phone and laptop). **Changes for others:** the employee gets 087's Confirm block (Case B) or a notice (Case A); HR gets the requests it already knows; CXO nothing. **One-way rule:** a manager's convenience never removes the employee's say, which is why Case B is the default.

### v2.1 The page

1. **Show:** one control, a day list (latest day with held days first) plus "All days in this period" for catching up. A day with no rows left drops out of the list.
2. **Chips:** Everything, and Held with its count. The count equals the rows under it. One line: "4 held days need a time from you." One explanation: "Held days have a punch missing, so pay for the day is on hold until HR fixes it. Give the missing time and a reason, and HR decides."
3. **A row (direct reports only):** name, day, the Held chip, Ready mark, the strip, the real punches, then two boxes.
   - **Time.** One punch: "What time did Ravi leave?" (or arrive) with "Type the time you know it was. Nothing is filled in for you." Which end is missing is inferred from where the single punch falls in the shift. **[ASSUMPTION]** the engineer keeps `acHeldForm`'s own rule for this; I show the result, not the rule. 3 or more punches: "Where is the missing punch?" and a button that opens 087's timeline. Tap a gap, 087's add sheet asks the time and shows the kind it worked out ("Back in after a break"), with the same checks. The row then shows "+14:40 · Back in after a break" and Change. **One punch per row.**
   - **Reason**, required, one line that grows: "Your reason · Required", "HR and Ravi can read this. No health or family details.", example "e.g. Forgot to scan after lunch". Never copied between rows.
4. **Ready** shows only when the time (or gap) and the reason are both there. A time with no reason shows the quiet line "Add a reason to include this day": no red, no error before the person has tried anything.
5. **Bar:** "3 days ready" and "Each person confirms in the app first. Then HR decides." with **Send 3 to HR**. Over 50: "50 at most in one send. The first 50 go now; 5 stay here for the next send."
6. **Confirm** (bottom sheet on a phone, centred on a laptop): "Send 3 days to HR?", "Your name goes on each request. Each person must confirm in the app before HR can decide. Until HR does, the day stays held.", one line per day with the person, day, time and **the reason typed for it**, then Send and Go back. No shared note box.
7. **After sending:** sent rows **leave the list**. Banner: "3 of 3 sent to HR. Ravi, Anita and Preet: HR will decide each one. Each person must confirm in the app before HR can decide." A refused row stays with its time and reason and the server's sentence ("Not sent. This day is no longer held..."). Offline, answer-lost and refusal wording are v1's, kept.
8. **Empty:** "Nothing is held on Thu 20 Nov." and a button to the next day that still has rows, or "See everything".

### v2.2 Case B (default), and the one Case A variant

**Case B, until counsel answers.** A direct report with no login shows no time box and no reason box, only: "Imran has no login, so this cannot be confirmed in the app. Ask HR to fix this day." Neutral words, nothing about ability. **Case A** (manager's request counts as the request itself) changes four things, switched in the review bar and outlined in amber with a "Case A" tag in the prototype: (1) a no-login person gets the boxes; (2) the bar line "Each person is told on their day sheet. HR decides."; (3) the confirm sentence ("...Each person is told on their day sheet and can say it is not right..."); (4) the banner line "Each person has been told on their day sheet." Nothing else differs, so it is one condition in one place, as the brief said.

### v2.3 Parity: v2 against prototype-v1 (the last design Surbhi saw)

| # | v1 | v2 | Why |
|---|---|---|---|
| H-1 | Period filter, Held chip with a split line (need a time / waiting / another manager's) | Day control (+ catch-up), Held chip, one line "N held days need a time from you" | Surbhi, 21 Nov |
| H-2 | Three row kinds ("Waiting for HR", "Not yours to send") | Dropped. Only held days with no request, direct reports | same |
| H-3 | Row shows the punches as a line | The strip and the line, and 087's timeline for 3+ punches | reuse 087 |
| H-4 | Arrival / Leaving buttons with no default for 3 or 5 punches | Tap the gap on the timeline; the kind is worked out and shown (087 decision ⚠8) | one way to say where; consistent with 087 |
| H-5 | Optional shared note in the confirm | Required reason on every row; the confirm lists each reason | ALV-418 |
| H-6 | Sent row turns into "Waiting for HR" and stays | The row leaves; a banner names who was sent | Surbhi, 21 Nov |
| H-7 | "Everyone below me" option | Not offered (direct reports only) | Surbhi, 21 Nov |
| H-8 | no no-login state | Case B no-login line (Case A: boxes) | ALV-419 |
| H-9 | Bar line "HR reviews each day. Your name goes on each request." | Adds who must act next (the person's Confirm, B) | ALV-419 |
| H-10 | Kept: Held chip, real punches, no pre-filled time, Ready mark, bottom bar, cap of 50, confirm dialog, banner and refusal words, answer-lost guard, phone, Hindi, nothing in `localStorage` | unchanged | Surbhi, 21 Nov |

Where the 087 screens appear (Confirm block, Not right with a time), they are 087 v4 and are not redrawn here.

### v2.4 ⚠ and risks

- **⚠ DECISION (small, owner: engineer, then Surbhi):** the inferred missing end for one punch (v2.1 point 3). v1 never said how it is decided. If the existing held logic cannot tell, show Arrival / Leaving buttons with no default for those rows too (v1's way). Cost: one more tap.
- **Risk (P3 until measured):** on a 360 px phone the page head (Show, chips, two lines) is about 300 px before the first row. Measure it with real DTC rows; if it is too much, the explanation line goes behind a "What is Held?" link.
- **Risk:** each row needs its own reason, so 20 rows is 20 typed lines. That is counsel's condition, not a design choice. **Not in this slice (yours to decide):** a "same reason as the row above" link. I recommend against it: it is the blanket text the condition is meant to stop.
- The employee sees the manager's **reason** on their Confirm block (087 v3), which is why each row says "HR and Ravi can read this" and asks for no health or family details.

### v2.5 Subtract pass

Removed from the v1 page: two row kinds, the split line, the shared note, the whole-line choice, the "Waiting for HR" row state. Removed from my own draft: an Inbox link, a count inside the day list, a "copy reason down" link, an Undo after sending, a sort control.

### v2.6 For the business analyst

Turn into criteria: only direct reports' held days with no request; one day by default; rows leave on send; reason required per row and shown in the confirm; one punch per row; Ready needs both; cap of 50 with the sentence; Case B no-login line (test: no box, no request created for a person with no login); Case A is a single condition. Test what it sends: the payload carries one reason per day.
