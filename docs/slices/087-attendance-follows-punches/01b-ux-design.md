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
