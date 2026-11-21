---
slice: 087-attendance-follows-punches
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-11-20
status: draft (v2 appended below)
inputs: [01-product-brief.md incl. Surbhi's decisions, 01a-ux-opportunities.md, 07-devops-inputs.md, portal.js, attendance_correction.py, held_day.py, next-inbox.js]
---

# 087 Attendance follows the punches: UX design

**Risk tier 1.** **Prototype:** `prototype-v1.html` in this folder (copy kept at `/Users/mac/hrlocal-data/prototypes/087-attendance-follows-punches/prototype-v1.html`). **I have no publish tool in this run, so it is not published.** The session that ran me publishes it. Every name, time and rule figure in it is **Sample**.

**Serves:** Employee (phone, main), HR Manager (laptop). **Changes for the others:** CXO, nothing. Line manager, nothing in this slice (086 owns manager filing; the manager sees no new view of a person).

**Applied from `ux-learnings.md`:** "Count the existing surfaces before drawing a new one" (17 Oct), "Hide what a person cannot use / a plain sentence instead of a button" (slice 013, 084), "One person, two roles" (slice 009), "Test what it sends" (28 Oct). Nothing in it contradicts this request.

## 1. What I read, and what I did not do

All **Fact**, read in this worktree (`087-attendance-follows-punches`, HEAD `2e31151f`). I could not fetch (GitHub unreachable), so "not built" claims are against this checkout, not `origin/dev`.

| Surface | Where | What it does today |
|---|---|---|
| Day sheet | `portal.js` `acDetail` (line 6147) | Facts, punches as chips (In/Out, time, where), "Why this day", then exactly one of: request card, held form, "too old" sentence, or the reason form |
| Reason form | `acForm` (6422) | "What went wrong?" list + "Anything HR should know" + file + "Ask HR to fix this day". Changes **status only** |
| Held-day form (085) | `acHeldForm` (6349) | Time, plus In/Out when 2+ punches, "Send to HR". Held days only |
| HR decides | `acReviewQueue` (6571), card in the Attendance page | Name, reason, date, punches and "If you approve: this day becomes ..." for held days; Approve / Decline; the browser prompt asks for a note |
| HR decides, second door | Inbox row, `next-inbox.js` `ACTIONS.attendance_fixes` | Row has **no punches and no result line** (`inbox_api.py` field list, line 151). It can approve inline |

**Not done:** I did not sign in or run anything. No tenant, no login. Prototype shapes are my drawing of the approved flow, not a screenshot. I looked once at the prototype in headless Chrome at 390 px and desktop.

## 2. Findings on today's screens

| ID | Finding | Impact | Kind | Size | Sev |
|---|---|---|---|---|---|
| D1 | The Inbox row can **Approve inline with no punches and no result line**. For a punch fix that is a pay change decided blind | High | Fix | S | **P1 for this slice** |
| D2 | The reason form says "It decides what the day becomes". A punch fix has no such choice: the result comes from the punches | Medium | Improve | S | P2 |
| D3 | Existing punch chips are **11 px** (`.ac-punch`), under our 12 px floor | Low | Fix | S | P3 |
| D4 | The browser `prompt()` is HR's only place to type a note. Not phone friendly or screen-reader friendly. Desk-only user, so left | Low | Keep, note | - | P4 |
| D5 | The 085 held form already answers "time + In/Out" in two fields. **Keep that spirit**: nothing else to fill in | - | Keep | - | - |
| D6 | The set-aside / added marks must show on the day sheet in words, not only colour | Medium | New | S | P2 |

## 3. The design in one paragraph

One form, "Fix a punch", replaces the 085 held form and goes in front of the reason form. The employee says **which punch is missing** in the four plain names Surbhi chose, gives the time, and may tick a punch that is wrong. HR sees the real punches and, **under the Approve button, one sentence of result**. After approval the employee's own day sheet says what HR did, and a set-aside punch stays on screen, struck through with its reason.

**Rung:** reuses the day sheet, the held form's pattern, the request card and `decide`. No new page, tab or dashboard. New: one form body, two lines on the HR card, two punch marks. Rejected cheaper rung: leaving the 085 held form plus a second form for non-held days would give two forms for one job.

## 4. The four names and what they send

| Employee sees | Sends | Time must sit |
|---|---|---|
| Arrival | In | before every punch that still counts |
| Back in after a break | In | after the first and before the last |
| Out for a break | Out | after the first and before the last |
| Leaving | Out | after every punch that still counts |
| No punch is missing (use with a ticked wrong punch) | nothing added | not asked |

The position test is what lets the server say "that time does not fit" in plain words. It is also why three-punch day (b) works: 10:30 In, 14:00 Out, **14:40 In (added)**, 19:30 Out, so 3h 30m + 4h 50m = **8h 20m**.

## 5. Flow

```
Employee: open day -> [Fix a punch] -> pick punch -> time -> (tick wrong punch) -> (note) -> Send to HR
          -> day says "Sent to HR at 09:12 ... stays as it is until HR decides" + Withdraw
HR:       Attendance page card (or Inbox "Review", never inline Approve) -> sees punches, says, note,
          result line -> Approve (+ optional note) | Decline (reason required)
Employee: day sheet: "HR added 14:40 (In) on 21 Nov, from your request." / struck-through punch with reason
          or: "HR did not add this. Reason from HR: ..."
```

Both cases from Surbhi are in the prototype: **(a)** Wed 19 Nov, add 10:30 In, tick 11:15, result "Present, 9h 00m, and is paid." **(b)** Thu 20 Nov, a Held day, add 14:40 "Back in after a break", result "Present, 8h 20m, and is paid."

### States

| State | What the person sees |
|---|---|
| First time / day with no punches | The form opens the same. "Which punch is missing?" works; the "wrong punch" block says nothing is there to tick (not drawn) |
| Loading / sending | Existing `showLoad`; one press = one call (existing `acSending` guard). Typed time kept on failure |
| Network lost mid-send | Same as 085: "It may have gone through. Checking with the office." then the sheet reloads; the typed time and ticks come back if it did not save |
| Error from server | The server's own sentence, shown beside the button and kept after the toast goes (084 pattern), form left filled in |
| Waiting | Violet box: "Sent to HR at 09:12" + what you said + Withdraw |
| Approved | Green box + marked punches (section 6.4) |
| Declined | Grey box "HR did not add this. Reason from HR: ..." |
| 400 punches / long name | A day has few punches; the list wraps. Names truncate with the full name in the card title |
| Hindi (about 30% longer) | Rows are 52 px tall and wrap; no fixed widths. Drafted in the prototype, **machine drafted, needs native review** |
| No permission | The form and its button are not drawn. A sentence says why (section 7) |

## 6. Screens and exact words (English; Hindi is in the prototype)

### 6.1 Day sheet, before (employee, phone 390 px)
Facts and punches as today (chips at 14 px in the prototype, see D3). Button: **Fix a punch** (primary). Under the form a quiet link: **It is not about a punch. Something else went wrong** opens today's reason form unchanged.

### 6.2 The form
- Title: **Fix a punch on Thu 20 Nov**
- **Which punch is missing?** five radio rows, each 52 px tall, name plus one hint line: Arrival "When you came in for the day"; Back in after a break "When you came back from a break"; Out for a break "When you went out for a break"; Leaving "When you left for the day"; No punch is missing "Use this if one punch below is wrong". **None is pre-selected.**
- **What time was it?** native time field, 16 px, shown once a punch is chosen.
- **Is a punch on this day wrong?** "Tick a punch that should not count. It stays on record, set aside. Tick nothing if all are right." One tickable row per punch: "11:15 In" and "Check In on this portal". **None pre-ticked.**
- **Anything HR should know (optional)**
- "HR sees your punches, this time and your note, and decides. Nothing changes until HR approves."
- Buttons: **Send to HR** (primary, full width on phone), **Cancel**.
- Errors, plain: "Choose which punch is missing, or choose "No punch is missing" and tick the wrong one." / "Enter the time first." / "Tick the punch that is wrong." / **"14:40 does not fit. Arrival has to come before your first punch of the day (10:30). Check the time, or choose another punch."** (and the Leaving and break versions).
- On a one-punch held day the form adds a hint, not a pre-selection: "You have one punch, an Out at 19:30, so Arrival is probably the missing one." (`held_single_is_out` already exists.) **Not drawn in the prototype.**

### 6.3 HR card (laptop; works at 390 px too)
- Title: **Ravi Sample · Missing punch** (or "Wrong punch" when only a set-aside is asked). Date at the right.
- "Punches on record:" times as chips. On a held day, no In/Out is written (the machine gave none).
- "Ravi says: Back in after a break at 14:40." and, if given, "Note from Ravi: ...". If a set-aside is asked: "Also asks to set aside 11:15."
- Buttons: **Approve and add 14:40 (In)** · **Decline** · See their month. For case (a): **Approve: add 10:30 (In), set aside 11:15 (In)**. Set-aside only: **Approve: set aside 11:15 (In)**.
- **Directly under the buttons, tied to Approve by `aria-describedby`: "This day becomes Present, 8h 20m, and is paid."** Late shows only when late: "Present, 8h 15m, 45 min late, and is paid." If the result is still odd: **"This day stays Held. The punches would still be an odd number (3), so it is not paid yet."** (amber).
- Approve opens the **same prompt as today**: "Anything to tell the employee? (optional)". Decline: "Why is this not being approved? The employee will see this." Reason required.
- Toast: "Approved. 14:40 was added. The day is now Present."

### 6.4 Day sheet, after approval (employee)
- Green box: **Fixed by HR. Present, 8h 20m. Paid.**
- **HR added 14:40 (In) on 21 Nov, from your request.** (exact words from Surbhi)
- The added punch has a green tag **Added by HR**. A set-aside punch has a grey tag **Set aside**, is struck through, and carries: **"Set aside by HR on 21 Nov, from your request. Your note: ..."**; and the line "HR set aside 11:15 (In) on 21 Nov, from your request. It stays on record but no longer counts."
- Words and a tag always, never colour or strike-through alone.

## 7. Refusals, in plain words

Where the server can know in advance, the day sheet shows the sentence **in place of the form** (as 084 does with `own_window`). There is no button that dies on click. The server still refuses a send that slips through, and its sentence is shown beside the button.

| Refusal | Employee's day sheet | HR card |
|---|---|---|
| Day on a submitted slip | "This day is on a salary slip that is already final, so its punches cannot be changed here. Tell HR which day it was and what happened. HR can pay the difference with an Additional Salary." | If the slip became final after sending: "Since this was sent, the day went onto a salary slip that is final. Its punches cannot be changed. Decline it and say why, or add an Additional Salary." Decline only |
| Leave day | "This day is covered by approved leave, so punches do not change it. If you worked that day, ask HR to cancel the leave first." (Uses "approved leave", never the type, so nothing about the reason travels to a manager view.) | Same sentence, no Approve |
| Deliberate hand-marked day | "HR marked this day by hand on 16 Nov, so punches do not change it. If it is wrong, ask HR to look at it." | Same, no Approve |
| HR's own day | The HR person can send it | To that person: "This is your own day, so you cannot approve it. Another HR person will decide it." No buttons. Another HR person sees normal buttons |
| Time does not fit | Inline error (6.2) | Cannot reach HR |
| Employee has left | not drawn | "This person has left, so no punch can be added. Decline it and say why." **Not drawn** (BA to specify) |

## 8. Phone and the frontline bar

- 360 and 390 px, one column, no horizontal scroll. Rows 52 px, buttons 48 px, field text 16 px, nothing under 13 px in the new parts. **Measured in the prototype? No.** I looked once; I did not run a measuring script. The BA should make the checks acceptance criteria.
- Two minutes on a phone: open day, tap **Fix a punch**, tap one of five rows, set a time, **Send to HR**. Five taps and one time entry. Case (a) adds one tick.
- 3G: the form is plain HTML in the existing sheet and adds no call until Send. Same payload size class as 085 (a time, a kind, a list of punch times, a note).

## 9. Accessibility (WCAG 2.2 AA) and privacy

- Radios in a `fieldset` and `legend`; every input has a label; ticks are real checkboxes in a labelled row; error is `role="alert"`; the result line is linked to Approve with `aria-describedby`; focus lands on the first radio when the form opens and on the time field after a choice. Escape closes the prompt.
- Colour is never alone: every state has words and a tag.
- **Privacy:** the reason for leave is not shown to a manager. HR sees punches, the stated time and the note, nothing else. No raw server errors. "Added by HR" is plain on the record so it is never passed off as a machine read. Audit (who, when, which request) is the engineer's; the employee sees "HR added ... from your request", not the HR person's name. ⚠ DECISION 7.

## 10. Benchmark (from 01a, read 20 Nov, no trial accounts)

Keka and Zoho add a log and keep the old; Frappe makes you cancel. **We copy** "add, keep the original". **We do not copy** Zoho's replace, greytHR's synthetic punches, or auto-approve. **Seen:** none (help pages only). Nothing new was benchmarked in this run.

## 11. ⚠ DECISIONS

| # | Decision | Context | Options | Recommendation | Owner |
|---|---|---|---|---|---|
| ⚠ 1 | **Inbox "Approve" on a punch fix.** The Inbox row carries no punches or result line and can approve inline | Pay change decided blind. Real, read in code (D1) | A. Row for a punch fix shows **Review** only and opens the card. B. Add the result line to the Inbox row | **A.** Smaller. B needs the same preview in a second place | Surbhi; BA to specify |
| ⚠ 2 | **One punch per request?** An employee missing Arrival **and** Leaving sends two, the second after HR decides the first | Existing rule: one request per day. You did not say | A. One (as drawn). B. Allow two lines in one request | **A**, then count how often two are needed. B is more form and more server | Surbhi |
| ⚠ 3 | **Pre-empt refusals on the day sheet** (needs a server flag per day, like `own_window`) or refuse only on send | Hide-what-cannot-be-used rule vs less server work | A. Pre-empt (drawn). B. Refuse on send only | **A**: a 360 px user on 3G should not fill a form that cannot work | BA with engineer |
| ⚠ 4 | **Set-aside alone** (no punch added) allowed? I drew "No punch is missing" so a lone wrong punch can be set aside | Your "or" suggested yes | A. Allow. B. Always require an added punch | **A** | Surbhi |
| ⚠ 5 | **The old reason form** stays behind a link on days with punches. On days with **no** punches the new form still works (add Arrival, later Leaving). ALV-410 says status-only approvals may not move pay | Keep today's route for reasons that are not punches (e.g. on duty away) | A. Link (drawn). B. Remove the old form | **A** | Surbhi |
| ⚠ 6 | **Approve when the result is still Held.** Drawn as allowed, with the amber line saying so | HR may want to record a half fix | A. Allow. B. Hide Approve | **A** | Surbhi |
| ⚠ 7 | **Does the employee see HR's name** on "added by HR"? Drawn: "HR", no name | Transparency vs the person being named | A. "HR" (drawn). B. Name | **A**; the audit row holds the name | Surbhi with counsel |
| ⚠ COMPLIANCE | Whether an HR-added punch can stand as attendance evidence at DTC and Grace (brief, still open) | Blocks switch-on, not the design | - | - | Surbhi with counsel |

## 12. Parity

The prototype is the approved reference. **Anything the build does differently needs Surbhi's yes first.** The parts that are **code today** and kept as they are: the browser prompt, the reason form, Withdraw, the Attendance-page card. The parts that are **only drawn**: everything in section 6 that is new.

## 13. Usability test plan (High impact: pay)

Five people: three frontline staff on a 360 px phone, two HR users. Tasks: (1) fix case (b) on the phone; (2) fix case (a); (3) HR approves and says what will happen; (4) employee opens a leave day and says what to do. **Success:** employees finish in under two minutes with no help; every HR user states the result before pressing Approve. **Changes the design if:** two or more pick the wrong punch name (reword or add a picture), or HR presses Approve without reading the line (move it above the button).

## 14. For the business analyst: acceptance criteria to write

1. The four names map to In/Out and the position test in section 4. Each refusal in section 7, including the "does not fit" sentence for Arrival, Leaving and both break kinds.
2. The preview on the HR card comes from **the same function the approval runs**. Test that the line and the result agree, case (a) and (b), and "stays Held".
3. Approve adds exactly one punch and sets aside only the ticked ones. A second approval does nothing. The held 085 extra time is not counted twice.
4. HR cannot approve their own day at the server, not only on screen.
5. The Inbox does not approve a punch fix inline (⚠ 1).
6. After approval the day sheet shows the lines in 6.4; a set-aside punch keeps its time on screen.
7. Phone checks: 360 and 390 px, no horizontal scroll, rows 48 px or more, field text 16 px, nothing under 12 px in new parts. Existing 11 px chips fixed (D3).
8. Test what is sent: pressing Send posts the kind, the time, the ticked times and the note, and nothing else; a refusal shows the server's sentence, never "check your connection".
9. Hindi strings reviewed by a native reader before they ship.

## Not in this slice (for you to decide)

Two punches in one request; a manager filing the same fix (086); a reverse "undo a fix"; "Recalculate from punches"; a late-punches list; editing the browser prompt into a proper dialog.

## Subtract pass

Removed from my own draft: a separate "set aside" screen, a timeline of changes on a day, a confirm dialog on Approve (the result line and the existing note prompt do that job), a picture for each punch name, pre-selecting a punch kind. I removed nothing else; every item left serves case (a), (b) or a refusal.

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| Q1 | ⚠ 1 to 7 above | Surbhi | The spec |
| Q2 | Which field does the request carry for kind, time and ticked punches? | BA with engineer | The spec |
| Q3 | Can the server send a per-day "cannot fix, because ..." flag? | Engineer | ⚠ 3 |
| Q4 | Counsel on an HR-added punch | Surbhi | Switch-on |

## Assumptions

- [ASSUMPTION] Today's `to_review` card is where HR decides, and the Inbox row is a link plus an inline action (read, not run).
- [ASSUMPTION] A request is for one day and one punch, as 085's held request is.
- [ASSUMPTION] Sample shift 10:30 to 19:30, Present from 8h, 40-minute break allowance. Invented for the prototype.
- [ASSUMPTION] Hindi strings are machine drafts.

## Handoff note

For the BA: the HR sentence "This day becomes ..." must be the output of the function approval runs, never a second calculation (the 085 rule, and the brief's kill criterion 2). Watch the Inbox door (⚠ 1): it is the one way to approve without seeing the result. The employee must never lose the original punch from view; set-aside is shown, not hidden. I did not sign in to anything, did not measure the prototype, and did not check `origin/dev`.

---

# v2 (20 Nov 2026): a timeline, not a form

**Prototype:** `prototype-v2.html` in this folder (copy at `/Users/mac/hrlocal-data/prototypes/087-attendance-follows-punches/prototype-v2.html`). **Not published: I have no publish tool in this run.** v1 above stays for history. Everything in v1 that is not named below is unchanged. All names, times and rule figures are **Sample**.

**Why:** Surbhi on v1, 20 Nov 2026: "as per the user experience this design is too not optimized. Use your best UX skills to see how we can make it look professional and elegant." Logged in `ux-learnings.md`. The orchestrator's five points are all **Fact** against v1: a long form (five radio rows, time, checkboxes, note), punches shown twice, a category question before anything else, tinted boxes everywhere, and HR buttons that were whole sentences.

## v2.1 What changed, and the rule behind each change

| v1 | v2 | Why |
|---|---|---|
| Five radio cards "Which punch is missing?" | **Tap the gap where it happened.** Kind is worked out, then said in plain words in the sheet ("It will be added as: Back in after a break.") | People know where in the day, not the category name |
| Punch list, then the same punches as checkboxes | **One timeline.** Tap a punch to say "This punch is wrong" | One object, nothing to match up |
| Form in the page | **Compact bottom sheet**: a time field (empty, no prefill) and an optional note. Nothing else | Short, one thumb, 16 px field |
| Send button at the foot of a long form | **Sticky bar**: "+10:30 In · 11:15 set aside" and Send to HR | The person sees what will be sent without scrolling |
| Amber, green, purple and grey boxes | **One status line with an icon** (check, warning, clock, lock). Colour sits in the icon only. No tinted panels, no tags with fills | Hierarchy comes back; colour means something |
| HR: sentence-long Approve labels, a result box, a browser-style prompt | **Before and after mini timelines**, a short **Approve**, **Decline**, and an inline "Add a note for Ravi" link | The change is seen, not read. No modal |

## v2.2 How the kind is worked out (rule for the BA)

Count the punches that still count (not set aside) before the gap.
- None before: **Arrival** (In).
- Otherwise odd/even: an even count before means the new punch is an **In**, an odd count means an **Out**.
- An Out with nothing after it is **Leaving**. An In in the middle is **Back in after a break**. An Out in the middle is **Out for a break**.

So on case (b), 10:30, 14:00, 19:30, the gap after 14:00 has two before it, so the new punch is an In: "Back in after a break". On case (a), the gap before 11:15 has none before it: "Arrival". The kind is shown **before** the person types a time, and is recomputed if they set a punch aside afterwards. **Fact:** this is the v1 position test, turned round: v1 asked the person for the kind and checked the time; v2 takes the position and derives the kind. The server must still check the time sits between the two neighbours (the sentence is "14:40 is not between 14:00 and 19:30. Check the time.").

## v2.3 Employee screens

- **Day sheet** (tap a day, as today): one status line, one muted line ("Shift 10:30–19:30 · Expected 9h 00m"), a 28 px strip (shift band, dots, worked bars, `aria-hidden`), then the timeline. Rows: time (16 px, tabular), rail and dot, plain label and source. Punch rows are 56 px, gap rows 44 px; both are real buttons.
- **Rail:** solid purple = worked, dashed = break, grey = unknown (a held day has no In/Out, so none is drawn). A new punch is a green dot with the words "New · not sent yet" and a Remove link. A set-aside punch keeps its time, struck through, with the words "Set aside · not sent yet".
- **One punch per request** (decision 2): after one is added the gaps disappear and a line says "One punch per request. If another is missing, send this first and add the next after HR decides." A lone set-aside is allowed (no add needed).
- **Waiting:** status line "Sent to HR at 09:12 · Waiting", the day unchanged, the asked-for punch drawn dashed, and Withdraw.
- **Approved:** "Fixed by HR · 8h 20m · Paid". The HR-added row says "Added by HR on 21 Nov, from your request." The set-aside row says "Set aside by HR on 21 Nov, from your request. It stays on record but no longer counts." plus the person's note.
- **Declined:** "HR did not add this. Reason from HR: ..." and the timeline is editable again.
- **Unfixable days** (final slip, leave, hand-marked): the status line says "This day cannot be fixed here" and the one sentence of why, up front, with the punches read-only. No gaps, no buttons. Same three sentences as v1 section 7.
- **Employee never sees a predicted result.** The sticky bar says "Nothing changes until HR approves." (**Recommendation:** a predicted "would be Present" on the employee's side would read as a promise. HR's side shows it.)

## v2.4 HR screens

- **Card:** name and "Missing punch" or "Wrong punch", the date, one line of "Ravi says: Back in after a break at 14:40." with the note as a quote.
- **Before → after**, side by side on a laptop and stacked in a narrow card (container query, not a device guess). Each side: a proportional strip (09:00 to 20:00, shaded shift band), the times in one line (added in bold green with a +, set-aside struck through), then one status line: "Held · 3 punches" → "Present · 8h 20m · paid", or "Still held · 3 punches · not paid".
- **Actions:** **Approve** (short, primary, tied to the "if approved" result by `aria-describedby`), **Decline**, "Add a note for Ravi" link, "See their month" link. The note opens in the card. **Decline with no reason does not send**: the note opens, focus lands in it, and it says "Write a reason so Ravi knows what to do next." The modal in v1 is gone.
- **One caption** under the buttons: "Approving adds 14:40 (In), marked “added by HR”. It is never deleted." (kept from v1: HR must know what the record will say).
- **Own day / final slip:** the card shows the Now side only, one lock status line with the sentence, and (slip only) Decline. Another HR person sees normal buttons on Kavita's day.
- **Inbox:** unchanged from v1 (⚠ 1: "Review" only, opens this card). Not drawn.

## v2.5 Phone, theme, accessibility, privacy

- **Looked at once** in headless Chrome, 450 px wide: case (a) staged with the send bar, case (b) with the sheet open, HR on desktop (1280) and on the phone, and the dark theme on a locked day. **Not measured by script.** Targets are set in CSS: gap rows 44 px, punch rows 56 px, buttons 48 px (44 px in the HR card), fields 16 px, nothing under 12 px. The BA should keep v1's criterion 7. **Not looked at:** 360 px in a browser (the CSS has a 360 frame; I did not open it), Hindi in a browser (drafted, machine, needs native review).
- **Dark:** same tokens as `design_system.html`. I added `--on-primary` (dark text on the light purple in dark theme) because white on `#A99AD4` fails contrast (ux-learnings, 6 Nov).
- **Accessibility:** sheet is `role="dialog"`, `aria-modal`, focus lands on the time field, Escape closes. Colour is never alone: every state has words and an icon; strike-through always comes with "Set aside". The strip is decorative (`aria-hidden`); the list holds every fact. Errors `role="alert"` with an icon, in words.
- **Privacy:** nothing new. HR sees punches, the stated time and the note. The employee sees "HR", not a name (⚠ 7 unchanged). A leave day says "approved leave", never the type.
- **Frappe-first rung:** same as v1: the day sheet, `decide` and the request card exist. New is markup and CSS, plus one derived field (the kind) that today's server check already needs. No new page or DocType. **Not in the build ladder:** the strip is the one new component (about 20 lines, reused on both sides). Cheaper rung rejected: a plain list of times does not show the shift or the gap, and the gaps are the tap targets.

## v2.6 Parity (hard rule)

Code today and kept: the day sheet, the Attendance-page card, Withdraw, the reason form behind a link. **Drawn only, new:** the timeline with gap and punch taps, the bottom sheet, the sticky bar, the before/after card, the inline note, no modal. **v2 differs from v1 on the employee's choice screen** (gap tap instead of five radios). That is a design change; it needs Surbhi's yes at the gate.

## v2.7 ⚠ items for Surbhi

| # | Item | Why | Recommendation |
|---|---|---|---|
| ⚠ 8 | **In or Out is now worked out, not asked.** On an odd day it comes from counting; if the person picks the wrong gap they get the wrong kind | Rare, and HR sees the before/after and declines | Accept. Count how often HR declines a "wrong kind" |
| ⚠ 9 | **Employee sees no predicted result** (v1 did not either, but the bar invites it) | A prediction reads as a promise | Keep it off |
| ⚠ 10 | **Decline needs a reason, Approve does not:** the note field is optional on Approve | Same as v1 | Keep |
| ⚠ 11 | The shift band on the day sheet is only in the strip. The timeline list is in event order, not to scale, so labels never collide at 360 px | A to-scale vertical axis would waste space on a long break | Keep |

## v2.8 Subtract pass

Removed from v1: the five radio cards, the checkbox list, the "Is a punch wrong?" block, the tinted boxes and fill tags, the HR modal, the long Approve labels, the result box. Removed from my own draft: a "Change mode" toggle before gaps appear (the gaps are always there on a fixable day), a to-scale vertical axis, a predicted result for the employee, a count badge on the strip. Nothing else removed; each part left serves case (a), case (b) or an unfixable day.

## v2.9 For the business analyst

Replace v1 criterion 1 with the kind rule in v2.2 (position and parity, shown before the time is typed, recomputed after a set-aside). Keep criteria 2 to 9. Add: the "before → after" line and the result on approval come from the same function; Decline without a reason is refused at the server as well as in the card; a request carries one added time (or none), the set-aside times, and one note.

---

## Design gate (Surbhi, 20 Nov 2026)

v1 was rejected: "as per the user experience this design is too not optimized … make it look professional and elegant." v2 (the timeline) was approved: "go with this design, all recommendations". Prototype: https://claude.ai/artifact/FWLLW4sa9UmAYKccSHYGpz (version 2).

Accepted with the recommendations:
- ⚠8: the punch kind is inferred from the gap's position and parity, not chosen (a parity change from v1, approved).
- ⚠9: the employee sees no predicted result; HR does.
- v1 ⚠1-7 as recommended:
  1. the Inbox shows "Review" for punch fixes and opens the card;
  2. one punch per request;
  3. unfixable days are shown up front;
  4. a lone set-aside is allowed;
  5. the reason-only form stays behind a link;
  6. approval is allowed even if the day stays Held, with a warning;
  7. "Added by HR" is shown without the name, which stays in the audit record (counsel still to confirm).


---

## Counsel's conditions, 21 Nov 2026 (ALV-418, ALV-419)

**PRIV-2 is reversed by counsel, 21 Nov 2026 (ALV-418).** A reason is required on every request, a Held day included: one required reason box (label keeps the Q3 rule that HR and the manager read it), in the send bar. ALV-419: a request somebody else files for the employee waits for the employee's Confirm / Not right on their day sheet. **New, not in prototype-v2, needs Surbhi's yes.**


---

## v3, counsel's conditions (21 Nov 2026, ALV-418 and ALV-419)

**Prototype:** `prototype-v3.html` in this folder (copy at `/Users/mac/hrlocal-data/prototypes/087-attendance-follows-punches/prototype-v3.html`). It is v2 plus these screens only. Buttons "Show 1 to 4" at the top jump to each one. All names, times and reasons are **Sample**. **Not published: I have no publish tool in this run.** The session that ran me publishes it.

**What I read (Fact):** `portal.js` `acPfPaint`, the send bar, `acPfConfirm`, `acPfCard` (this worktree, HEAD `659a1c2d`); `punch_fix.py` `confirm`, `send`, `day_sheet`; `next-home.js` and `home_api._needs`; spec section "Counsel's conditions". **I did not run the build** (the bench is in use). Checked by script at 360 px, 390 px and desktop, English and Hindi: nothing wider than the screen, no tap target under 44 px, no field text under 16 px, nothing under 12 px. Looked at once, light and dark. Hindi is machine-drafted and needs native review.

**Serves:** the employee (phone) and HR. Line manager: unchanged. CXO: nothing. **One-way rule:** the employee gains a veto over what others write into their day. HR loses nothing but a shortcut.

### v3.1 ALV-418: one required reason, in the send bar

- **Words.** Label "Your reason", the word "Required" beside it, then "HR and your manager can read this." (the Q3 rule). Example in the box: "e.g. Forgot to scan after lunch". Error, beside the box, with a red border and focus moved into it: "Write a reason so HR can decide."
- **Light on a Held day.** One box, one line that grows to three, no category list. The same bar serves a Held day and an ordinary day.
- **At 360 px** the bar is about 215 px tall: summary line, box, then one row with "Nothing changes until HR approves." and Send to HR. **Risk:** with the keyboard open it covers most of the screen. **Test at build:** 360 px with the keyboard open on a real Android.
- The add sheet and the set-aside sheet lose their optional note, so the reason lives in one place. The draft text stays on the device until it is sent.
- The employee's own ordinary request without a time keeps the dropdown reason (decided 21 Nov). Not drawn.

### v3.2 ALV-419: the employee's Confirm

- **Day sheet, top of the day.** Status line: "HR sent this for you. Is it right?" (manager: "Your manager Sunita Rao sent this for you. Is it right?"). Then what was filed: "Add a punch at 14:40 · Back in after a break" (or "Set aside your punch at 11:15"). Then the filer's reason, labelled "Reason from HR". Then "Press Confirm only if this is what happened. After that HR decides. Nothing on your day changes until then." Then **Confirm** (primary) and **Not right**. The timeline below draws the asked-for punch dashed: "Added by HR · waiting for you". No Withdraw: the employee did not file it.
- **Not right.** The two buttons are replaced by a box "What is not right?" (Required; "HR will read this."), the line "HR will not add it, and your day stays as it is.", and **Back** / **Send to HR**. Empty: "Say what is not right, so HR knows what to fix." (the coded words, kept).
- **After Confirm.** "You confirmed at 09:40 · Waiting for HR". Toast "Confirmed. HR can now decide it."
- **After Not right.** "You said this is not right", "HR will not add it, and your day stays as it is.", "Your reason: ...". The day is editable again. Toast "Sent to HR. Nothing was changed."
- **After HR approves.** "Added by HR on 21 Nov. You confirmed it." (manager: "..., asked for by Sunita Rao. You confirmed it.").
- **HR card.** Under the header: "Anil Sample (HR) asked to add: Back in after a break at 14:40." and the reason. Then a clock line "Waiting for Ravi to confirm" and "Filed on 21 Nov at 09:12. You can approve it after Ravi presses Confirm in the app. You can still decline it." **Decline only.** After Confirm: a tick line "Ravi confirmed this in the app on 21 Nov, 09:40" and the normal Approve and Decline. If Ravi says Not right, it moves to Decided as "Declined by Ravi" with his reason.
- **Privacy.** The employee sees the manager's name and "HR" without a name (v1 decision 7 stands). HR sees the filer's name. Nobody else sees any of it.

### v3.3 How the employee finds it (Recommendation)

**Add one row to Home's existing "Needs you" card:** "HR sent a punch fix for Thu 13 Nov. Is it right?" with a **Check** button that opens that day. One row per request.
- **Why it is needed (Fact, read from code):** the card lists only days with no attendance record (`attendance_gap`), not Held days. No email or push exists (spec G13). A Held day is **unpaid until fixed**, so a request nobody opens costs the employee money and HR a phone call.
- **Cost:** rung 3, customisation. One more entry from `home_api._needs` and a few lines in `next-home.js`. It reuses the card and the "Fix" button style. No new count, so the "one number" rule (042 D-1) is untouched.
- **Rejected:** a month-row tag (needs a new field on the month payload and still needs someone to open the month); an Inbox entry (a new count, and a new row kind to keep equal to its list).
- **Not done by it:** a reminder after N days. That is in "not in this slice".

### v3.4 Parity: every difference from the engineer's coded version

| # | Coded now (`portal.js`, `punch_fix.py`) | v3 | Needs from the server |
|---|---|---|---|
| P-1 | Label "Reason (required). HR and your manager can read this." as one line | "Your reason", "Required" beside it, the Q3 sentence as a second small line | none |
| P-2 | No example | Placeholder "e.g. Forgot to scan after lunch" | none |
| P-3 | Box of 2 rows | One line, grows to 3 | none |
| P-4 | Error in a block under the box | Same words, with icon, red border, focus in the box; clears on typing | none |
| P-5 | Bar order: summary and help, box, error, button | Summary, box, error, then one row: help line left, Send right | none |
| P-6 | "Your note: ..." on the waiting line | "Your reason: ..." | none |
| P-7 | 085 held form has the box | Same box and words there (not drawn) | none |
| P-8 | Block header only; manager shown as "Your manager" | Adds the filed item, the filer's reason, the truth line; manager's **name** | `request.filed_by_name` for a manager (not for HR) |
| P-9 | "It goes to HR only after you confirm." **This is untrue: HR already sees it, waiting.** | "Press Confirm only if this is what happened. After that HR decides. Nothing on your day changes until then." | none |
| P-10 | Not right: box appears under the unchanged buttons; button "Send" | Buttons replaced by Back and Send to HR, "Required", the consequence line | none |
| P-11 | After Confirm: "Sent to HR at <HR's filing time> · Waiting" **and a Withdraw button** | "You confirmed at 09:40 · Waiting for HR", no Withdraw | `request.confirmed_on` (time) |
| P-12 | After Not right: "HR did not add this. Reason from HR: <the employee's own words>" **(wrong: the employee wrote it)** | "You said this is not right ... Your reason: ..." | `request.declined_by_you` (reviewer is the employee's own user) |
| P-13 | Approved: "Added by HR ..., from your request." **(untrue for a filed request)** | "Added by HR on 21 Nov. You confirmed it." (manager variant names the manager) | `request.filed_by`, already sent |
| P-14 | Asked-for punch tag "Asked for · waiting for HR" | "Added by HR · waiting for you" until confirmed | none |
| P-15 | HR card: "{Employee} says: ..." and the filer's reason quoted as theirs **(untrue; this is evidence)** | "{Filer} (HR/manager) asked to add: ..." | filer name on the card |
| P-16 | HR waiting sentence at the foot | Clock status line under the header, with when it was filed; Decline only | filed time on the card |
| P-17 | Nothing after confirm | "Ravi confirmed this in the app on 21 Nov, 09:40" above the buttons | `card.confirmed_on` |
| P-18 | Not right just disappears into declined | Decided list: "Declined by Ravi" and his reason | none (the note is stored) |
| P-19 | No Home row | One row in Needs you (v3.3) | `home_api._needs` entry. **Needs Surbhi's yes** |

P-9, P-12, P-13 and P-15 are wrong sentences, not taste: I rate them **P2** (misleading words on a screen that is evidence). The rest are P3.

### v3.5 ⚠ for Surbhi

- **⚠ DECISION 1: the Home row (P-19).** Recommend yes. Without it nothing tells the employee, and a Held day stays unpaid. Owner: Surbhi. Blocks: only P-19; the rest of v3 stands without it.
- **⚠ DECISION 2 (P1): a request that is not a punch fix, filed for an employee, can never be confirmed.** Read from code, **not run**: the server flags every request not filed by the employee, but `day_sheet` returns only punch-fix requests and Confirm exists only on that sheet. A manager's ordinary request ("Forgot to Punch Out", no time) is flagged, has no Confirm screen, and HR can only decline it. Options: (a) show the same block on the older request card (recommended: one component, shown twice); (b) flag punch fixes only (changes AC-104 and what counsel agreed). Owner: Surbhi, with `hrms-business-analyst` for the spec and counsel if (b). Risk if it waits: manager-filed requests stop working the day this ships.
- **⚠ 3: the manager's name is shown, HR's is not.** As the brief said, and v1 decision 7 stands for HR. Counsel was still to confirm decision 7.

### v3.6 Subtract pass, and not in this slice

Removed from my own draft: a month-row tag, an Inbox row, a way to take back a Confirm, a minimum length on reasons, a counter, a second note field in the sheets. **Not in this slice (yours to decide):** a reminder after some days; the filing manager seeing "Waiting for Ravi to confirm" on their own list (086 owns that screen); an HR "chase" button.

### v3.7 For the business analyst

Add to AC-103: label words, "Required", the example, the error beside the box. Add to AC-106: the five employee states (to confirm, confirmed, not right, approved after confirm, declined by HR), and that after Confirm there is no Withdraw. Add to AC-107: the filer is named, the line "confirmed this in the app on" shows after Confirm. New: P-12 (declined by the employee is worded as the employee's own), P-15 (the HR card never says the employee said it), and DECISION 2.


---

## v4, the employee can correct the time (Surbhi's feedback on v3, 21 Nov 2026)

**Prototype:** `prototype-v4.html` (copy in `/Users/mac/hrlocal-data/prototypes/087-attendance-follows-punches/`). v3 plus this change only. Looked at once, plus a script check at 360 px (English and Hindi): nothing wider than the screen, no target under 44 px, no field text under 16 px. Not published: I have no publish tool. Hindi is machine-drafted.

**What changes.** On "Not right", when a time was filed, a time field sits above the required reason. Its label follows the inferred kind: "What time did you arrive?", "What time were you back?", "What time did you go out?", "What time did you leave?". Tag "Optional"; help "14:40 was sent. Leave this empty if you do not know the time." It uses the add sheet's checks (before, after, between, duplicate, same words) plus one new sentence: "That is the time that was sent. If it is right, go back and press Confirm." A filed set-aside has no time field. The line above the buttons changes as the time is typed: with a time, "HR will not add 14:40. Your own request for 14:15 goes to HR instead, and you do not need to confirm it."; without, the v3 line.

**Behaviour shown.** With a time: the filed request is declined and the employee's OWN request goes in with their time and reason. It needs no Confirm (the employee filed it). Without a time: as v3.
- **Employee after:** "Sent to HR at 09:40 · Waiting", "This replaces the 14:40 that HR sent. You said it was not right.", "Your reason: ...", the new time drawn dashed, and Withdraw (it is theirs).
- **HR card:** an ordinary card, "Ravi says: Back in after a break at 14:15." with the reason, and "Replaces the 14:40 that Anil Sample (HR) sent. Ravi said that one was not right." Approve and Decline.
- **HR Decided:** "Declined by Ravi", his reason, "Ravi sent 14:15 instead."

### Parity (v4 against v3 and the coded build)
| # | Now | v4 | Needs |
|---|---|---|---|
| V4-1 | Not right: reason only | Optional time field above the reason, label by inferred kind | none |
| V4-2 | no time check | Add-sheet checks + "same as sent" | server runs the same checks as `send` |
| V4-3 | consequence line fixed | changes with the time | none |
| V4-4 | Not right only declines | With a time: declines the filed request and creates the employee's own, in ONE transaction (both or neither) | `confirm(name, ok, reason, time=None)` calls the `send` path; link field `alvoraa_replaces` on Attendance Request |
| V4-5 | HR sees one declined request | HR card says "Replaces the one {filer} sent"; Decided shows both | the link, read at card time |
| V4-6 | no Withdraw after Not right | Withdraw on the replacement | existing |

**⚠ DECISION (Surbhi).** I kept the proposed "decline and re-file" over the alternative of letting the employee edit the filed request's time. Why: counsel's condition makes the filer's claim and the employee's claim two separate records; editing would blur whose statement it is. Cost: one Link field. **Questions for `hrms-business-analyst`:** (a) does the replacement count against the employee's monthly limit (it should not, since they did not choose to file)? (b) the one-open-request-per-day rule: the decline must come first. Neither checked in code.

**Subtract pass.** Removed: a time field on a set-aside, a third "edit" path, a "reply to HR" thread.


---

## v5, Confirm redesigned (Surbhi's decisions, 21 Nov 2026)

**Prototype:** `prototype-v5.html` (copy in `/Users/mac/hrlocal-data/prototypes/087-attendance-follows-punches/`). v4 plus the changes below; everything else is v4. Show buttons 2, 3, 5 and 6 jump to the new screens; HR: Kavita can record a signature on Anil's request (Anil cannot). **Not published: I have no publish tool.** Checked by script at 360 px and desktop in English and Hindi (nothing wider than the screen, no target under 44 px, no field text under 16 px, nothing under 12 px) and looked at three screens once. Hindi is machine-drafted. I did not run the build.

**The rule drawn.** Approval never waits. An **HR-filed change, or any cut (set aside)**, needs the employee's confirmation before pay is locked: an app Confirm, or "Signed on the register" by an HR person who did not file it, with a photo. A **manager's addition** needs nothing. The employee can always say "Not right".

### v5.1 What each person sees

- **HR card.** No waiting gate, Approve and Decline always there. For an HR-filed or cut change, one quiet line under the reason: "**Needs Ravi's confirmation before pay is locked** · Not yet" (other states: "Confirmed in the app on 21 Nov, 09:40"; "Signed on the register on 21 Nov, recorded by Kavita Sample (photo kept)"; "Ravi says it is not right"). Under the buttons, **Signed on the register** for any HR person but the filer; for the filer a sentence instead: "You filed this, so another HR person records the signature."
- **Signed on the register** (dialog): "Record this only if Ravi signed next to this change on the printed register: Added 14:40, Thu 13 Nov." A required **photo of the signed page** ("Show only this person's line if you can. Other people's names are on the page."), "Your name, today's date and the photo are kept with the request." Empty: "Add the photo of the signed page first."
- **Employee day sheet**, for a request filed for them, pending or already approved: the filed item, who filed it ("HR", or the manager's name), their reason, then the buttons.
  - Manager addition: **Not right** only. Words: "HR decides this. Nothing on your day changes until then. If it is not right, say so and give your own time."
  - HR-filed or cut: **Confirm** and **Not right**. Words: "Press Confirm only if this is what happened. HR can decide it now. Your salary slip for this month waits until you confirm it, or sign for it on the register." If HR already approved, the header says so ("HR added this for you and has approved it. Is it right?") and the day above already shows the approved result.
  - After Confirm the block stays: "You confirmed this at 09:40" and "You can still say it is not right."
  - Timeline lines say where things stand: "Added by HR on 21 Nov. Not confirmed by you yet." / "...You confirmed it." / "...You signed for it on the register." Tags before a decision say "sent for you", not "waiting for you".
- **Not right.** As v4: optional own time (by kind), required reason. **Pending:** the filed request is declined and the employee's own goes in (with a time), or it is declined with the reason (no time, or a cut). **Already approved:** the day **stays as approved**. With a time it becomes a **new request** ("You sent your own time, 14:15 · Waiting for HR"). With no time, or for a cut, the reason goes to HR as a **dispute** ("You told HR this is not right · Waiting for HR"). The consequence line says which, before the button.
- **Home** "Needs you" row: as v4, now also for approved changes still waiting on the employee.
- **Before payroll (HR).** A card at the top of the HR page: "**2 changes not yet confirmed this month**" with "A salary slip cannot be submitted for these people until each change is confirmed, signed on the register, or withdrawn." One row each: person, day, what, who sent it, where it stands, and the actions: Signed on the register (not for the filer), Withdraw (while still pending). A button tries the slip; the refusal reads: "The salary slip for Ravi Sample, Nov 2026, cannot be submitted. 2 changes are not confirmed: 13 Nov: added 14:40, sent by Anil Sample (HR); 10 Nov: set aside 11:00, sent by Sunita Rao (manager). Ask Ravi to confirm in the app, record the signed register, or withdraw the change."
- **Salary Workings (DTC), note only.** One row mock with a flag "Unconfirmed change: Thu 13 Nov added 14:40; Mon 10 Nov set aside 11:00". The report keeps its columns; the words match the list.

### v5.2 Parity: v5 against v4 and the coded 087 build

| # | v4 / coded | v5 | Needs |
|---|---|---|---|
| F-1 | HR card waits for the employee ("Waiting for X to confirm", Decline only) | Approve always; quiet line with state | `awaiting_confirm` gate removed; `refuse_unconfirmed` removed |
| F-2 | Block only while pending; Confirm + Not right for everyone | Pending or approved; manager addition Not right only | `needs_confirm` rule: HR filer or any set-aside |
| F-3 | After Confirm: "waiting for HR" status, block gone | Block stays with "You confirmed this", Not right still there | `confirmed_by/on` shown |
| F-4 | Not right only before HR decides | After approval: new request or dispute, day unchanged | new request path from `confirm`; ⚠ D-1 |
| F-5 | no register route | Signed on the register + photo, not by the filer | new fields: signed by, on, file; refuse if signer = filer |
| F-6 | no pre-payroll view | Card with rows and actions; slip refusal names them | list query; refusal on slip submit; ⚠ D-2 |
| F-7 | none | One flag in Salary Workings | report column or note |
| F-8 | "...from your request" on approved filed items | "Added by HR on 21 Nov. Not confirmed by you yet." etc. | `filed_by`, `conf` state in payload |
| F-9 | HR card said "{Employee} says" for filed requests (fixed in v3 P-15) | unchanged | none |

### v5.3 ⚠ DECISIONS and risks

- **⚠ D-1 (owner: BA and Surbhi): after HR approves a cut, what can "Not right" do?** 087 never cancels an approved fix, so there is no way to bring a set-aside punch back. I drew a **dispute**: the reason goes to HR, the day stays as approved, HR decides what to do by hand. If you want a real "restore this punch", that is a new mechanism and a new slice. Risk if it waits: an employee can say "not right" and nothing visible happens.
- **⚠ D-2 (owner: BA): "unless the change is withdrawn".** I could draw Withdraw only on changes still pending (it is a decline). An **approved** change cannot be withdrawn today. Until you say how, an approved, unconfirmed change blocks the slip until it is confirmed or signed.
- **⚠ D-3 (owner: `hrms-security-privacy-engineer`, counsel for retention): the register photo shows other people's names and signatures.** Recommend: one line per person on the printed register or a crop, visible to HR only, never in exports, a retention period set with counsel (nothing in the product sets one yet). I have not checked what the joiner documents do for this.
- **Risk (fairness):** "Your salary slip waits until you confirm it" is the true rule (Option 1), but it presses on the person with the least power. The register route is the way out for staff who cannot use the app (no login). I kept the words factual and put no timer or warning colour on it. **Experiment:** count slips held for this reason and for how long.
- **Risk:** an employee with no login can only be cleared by the register route or a withdrawal. That is by design, and it is why the pre-payroll list exists.

### v5.4 Subtract pass

Removed from the first draft: a reminder button for HR, a "chase" message to the employee, a count badge on the Home row, a separate page for the pre-payroll list (it is a card on the HR page), a column in the Salary Workings frame beyond one flag. **Not in this slice:** a reminder after some days; HR filtering the list by branch; photo capture on the phone's camera app inside the product.

### v5.5 For the business analyst

Replace AC-105 and AC-107 (approval waits). New criteria: the gate rule (HR filer or any set-aside; manager addition none; Administrator unchanged, decide); register signature (photo required, signer is not the filer, who/when/photo kept); the pre-payroll list and the slip refusal sentence; the Salary Workings flag; employee states (pending, approved-unconfirmed, confirmed, signed, disputed, replaced); and decisions D-1 to D-3.

## v5 design gate — Surbhi's decision, 21 Nov 2026

**Go with prototype-v5** (https://claude.ai/artifact/UdDqFpD4vzYgpqkAQXqUgU), with the Not right time required.
- **D-1:** after HR approves a cut, "Not right" is a dispute. HR decides by hand.
- **D-2:** Withdraw shows only on pending changes.
- **D-3:** the register photo shows only this person's line where possible. It is HR-only and never exported. Counsel is asked how long to keep it, and whether one photo per page (slice 088) is enough.

## v5 build parity (what 087 built, 21 Nov 2026)

| v5 row | Status |
|---|---|
| F-1 HR card: Approve always, quiet line "Needs X's confirmation before pay is locked · Not yet" | built |
| F-2 block pending or approved; manager addition Not right only | built |
| F-3 after Confirm the block stays ("You confirmed this at ...") | built |
| F-4 Not right after approval: new request or dispute; the consequence line says which | built |
| F-5 **Signed on the register** dialog, the HR button and sentence, the photo, signer/date/photo fields; the "Signed on the register" state lines | **moved to 088** (the HR card shows "Signed on the register" only if a request carries 088's field; the employee sheet shows "You signed for it on the register" the same way) |
| F-6 list before payroll: card, rows, "Not yet", Withdraw (pending only); slip refusal naming each change | built. The "button tries the slip" is not built |
| F-7 Salary Workings flag | built as one column |
| F-8 timeline lines "Added by HR on 21 Nov. Not confirmed by you yet." etc. | built |
| D-3 hint "This reason is printed on the employee's monthly notice." on every reason box (088) | built, Hindi in `translations/hi.csv` (machine-drafted) |
