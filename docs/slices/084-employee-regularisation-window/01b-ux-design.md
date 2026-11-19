---
slice: 084-employee-regularisation-window
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-11-19
status: draft
inputs: [01a-ux-opportunities.md, 01-product-brief.md (with Gate 1), 07-devops-inputs.md §1]
---

# 084 Design: how far back an employee can ask about their own day

**Prototype:** `/Users/mac/hrlocal-data/prototypes/084-employee-regularisation-window/prototype-v1.html`
**Not published.** I have no Artifact tool in this run. The session that ran me needs to publish it. It is one self-contained file and holds only Sample data (Asha, Ravi, a Sat/Sun holiday list). Open it straight from disk to click through.

**Risk tier 2** (as the brief). **Rung:** a setting plus a few lines on screens that exist. No new page, DocType or component.

## 0. What I looked at, and what I did not

- **Read (code):** `/Users/mac/hr-app`, `dev` at `a57764c4`. `org-settings.html` 115-152; `portal.js` 6200-6250 (day sheet, `acOutsideWindow`, `acNice`), 12156-12171 (`submitAttendanceRequest`), 23440-23535 (the manager box and its save line); `requests.html` 38-85; `attendance_correction.py` 1370-1460, 650-665, 2181.
- **Not seen on a screen.** No browser capture: the shared bench mounts the stale main checkout. Every "today" below is code. The prototype is drawn from the design tokens in `design_system.html` (light and dark); it is **not** the product.
- **Prototype vs code, kept apart below:** "Prototype draws" and "Code does today" are labelled each time.
- **Looked once** at the HR screen in a desktop browser. I could not click through the employee screens in a browser (no Playwright here). I tested the rule logic in Node instead (boundary Mon 16 Nov for 3; joining day alone passes; joining day to today refused; 12 Nov refused; 16 Nov passes; 0 gives today; blank gives none). **Phone and 200% text are not measured.** That is P2-level work still to do before sign-off.

## 1. Who, when, on what

- **Employee** on a phone (Asha, a joiner, whose joining day 11 Nov is eight days old) or a laptop. **HR Manager** on a laptop, setting it once. **Left out:** CXO, line manager (nothing changes on their screens).
- **Frontline employee:** the same sentence on a 390 px phone, field text 16 px, buttons 44-48 px, Hindi about 30% longer. Prototype draws the phone and Hindi; **measured: no**.
- **One-way rule:** HR sets the window, not the manager; HR's own route stays unlimited. Nothing here improves a manager's convenience at an employee's cost.

## 2. The decision that shapes the design

**One sentence, one function, three places.** The same words appear on the day sheet, under the date box, and as the refusal after Submit. They are built from the oldest-day date the **server** sends. No number of days or hours is ever typed into a string (that is how Grace's "48 hours" drifted from a real 3 days). The sentence has a fixed order: what is wrong, the date, HR's way out, then the joining-day exception if it applies.

## 3. Findings table (page by page)

| ID | Impact | Kind | Size | Evidence |
|---|---|---|---|---|
| OS1 | High | New | S | Org settings has no row for the employee. Must not sit under the manager switch or it greys with it (01a C7). Prototype draws it above the manager switch, not indented |
| OS2 | High | Fix, **P2** | S | The manager hint says "it does not limit ... an employee asking about their own day" (`org-settings.html` 148). **False on release day.** Rewrite, section 6 |
| OS3 | Medium | Improve | S | Manager save line says "last 3 working days", not a date (`portal.js` ~23516). The new row names the date |
| DS1 | High | New | S | Day sheet draws the form for every past day of an employee's own month. The manager sentence already exists and is reused (code 6200-6209) |
| DS2 | High | New | S | The sheet's `can_request_from` is only filled for a manager filing for someone else (code, `attendance_correction.py` 660-665). It must also be sent for the employee's own days. **Engineering, not a design choice** |
| AR1 | High | New, **P2** | S | `#att-req` has two free date boxes, no limit, no note. Refusal after Submit is `toast(e.message)` (code 12170). Three sentences typed, then refused: the Grace failure |
| AR2 | High | Fix | S | A toast vanishes. A refused person must be able to read it again, in Hindi, at length. Put the refusal beside the button, in a `role="alert"` box. Typed text stays (it does today: `clearForm` runs only on success) |
| AR3 | Medium | Decision | - | `min` on the date boxes cannot express "this day, plus a gap, plus the days from Mon 16". Prototype leaves `min` off and checks inline instead. Section 5 |
| JD1 | High | New | S | The joining day. Section 4 |
| **Keep** | | | | Saves on change with no Save button; one coloured line at the top of the card; the manager box greying with its own switch; blank = no limit, 0 = today only; the server sends the basis sentence (`can_request_basis`) and the screen repeats it as written |

## 4. The joining day, made visible (the new work)

**Problem.** Asha joined Wed 11 Nov. With a 3-day window the oldest day is Mon 16 Nov. Her joining day is allowed; Thu 12 and Fri 13 are not. Without a word of explanation, the 12th looks like a bug beside the 11th.

**Design: say it in three places, always in the words "joining day".** One word for one thing: the setting, the sheet and the refusal all say "joining day", never "first day".

| Where | What the person sees | Shown when |
|---|---|---|
| Day sheet, the joining day | Green strip above the form: **"This is your joining day, so you can always ask about it, however long ago it was."** Then the normal form | The day is the joining day **and** is older than the oldest day. If it is inside the window, no strip (nothing to explain) |
| Day sheet, any other too-old day | The refusal sentence ends with: **"The one exception is your joining day, Wed 11 Nov."** | The person's joining day is older than the oldest day. For Ravi (joined 2019) it says so too, which is true and harmless; he can see it is not for him |
| `#att-req`, under the title | The note ends: **"Your joining day, Wed 11 Nov, is always allowed."** | Same condition. And, under From, when the joining day is picked: **"Your joining day: you can always ask about this day."** (green, words not only colour) |

**Why not a chip on every month row?** It would be a second place saying the same thing on a screen the slice does not otherwise change. Removed (subtract pass).

**Prototype draws** all three. **Code does today:** none of it. The browser needs `joined_on` from the server beside `oldest day`; the server's refusal and the screen must not be able to disagree. ⚠ **Engineering note:** the cleanest way is for the server to send, for each day on the sheet, whether it can be raised. If it sends the two dates and the browser compares, the rule lives in two places. I recommend the first; I do not choose.

### ⚠ DECISION 1 (Surbhi): a range that starts on the joining day

The brief says a range whose first day is too old is refused whole, and checks the first day. Surbhi's change says the joining day is always allowed. Put together, a joiner could pick **From = joining day, To = today** and the first-day check lets the whole range through, including the old days between (12 to 15 Nov). That leaks the window.

| Option | What happens | Cost |
|---|---|---|
| **a) Joining day only on its own (recommended)** | Allowed when From and To are both the joining day. A longer range starting there is refused whole with: "Your joining day, Wed 11 Nov, can be asked about on its own: set To to the same day. Days after it that are older than Mon 16 Nov are HR's to fix: tell HR which days and why." | One extra comparison. A joiner who missed days 11 to 13 sends the 11th, and HR fixes 12 and 13. Two steps for that person |
| b) First-day check only | Joining day as From passes any range | Simplest. Window leaks for joiners, and nobody can say "every other day obeys the window" |

**Prototype draws (a).** Press "Joining day to today" in the review bar on Asha's Attendance Request screen to see it. Blocks: the acceptance criterion for ranges.

## 5. Flows and states

### 5.1 HR sets the number (laptop; phone also works)

Prototype draws: the row above the manager switch, **not indented**, with its own label naming the person. Greying: switching the manager box off greys only the manager number. The employee number stays live. Prototype note under the card lets the reviewer try it.

| State | Words |
|---|---|
| Label | **How far back an employee can ask about their own day** |
| Box | number, 0 to 30, placeholder **No limit**, saves on change |
| Hint (replaces nothing; new) | "Leave this empty for no limit. Counted in working days, using the employee's own holiday list. An employee's joining day is always allowed. It does not limit HR. Use 0 to let an employee ask about today only. This is one number for every company in this organisation." |
| Save, blank | "Saved. There is no limit: an employee can ask about any past day." |
| Save, 0 | "Saved. An employee can now ask about today only, Thu 19 Nov. Their joining day is always allowed. HR can still fix any day." |
| Save, 3 | "Saved. Today, an employee on the company's usual holiday list can ask back to Mon 16 Nov. Their joining day is always allowed. HR can still fix any day." |
| Not a whole number, or outside 0 to 30 | "Give a whole number of working days between 0 and 30, or leave it empty for no limit." (existing words; box goes back to the saved value) |
| Save fails | The server's sentence, else "The setting could not be saved. Try again, or ask your administrator." (existing) |
| Not HR | Whole card hidden, as today (code) |

- **Where the "one number for every company" line lives:** on this row's hint, once. The manager row has the same limit; I do not repeat it there.
- **The date in the save line is an example, and says so** ("an employee on the company's usual holiday list"), because each employee counts on their own list and the real date can differ by person. **Question for the engineer:** which list does the example use? My assumption: the company's default list; if none exists, count every day and say "counting every day". Not a Surbhi question.

### 5.2 Employee, day sheet (path A)

Prototype draws: Asha and Ravi, tap a day. **Code does today:** any past day draws the form.

| State | What the sheet shows |
|---|---|
| No limit set | The form, exactly as today. Nothing changes |
| Inside the window | The form, as today |
| Too old | No form. One sentence: **"This day is older than your organisation lets you raise yourself. The oldest day you can raise yourself is Mon 16 Nov. HR can still fix it: tell HR which day it was and why."** + the exception sentence when the person's joining day is older |
| Joining day, too old | Green strip, then the form (section 4) |
| Sent | "Sent to HR. HR will decide, and you will see the answer here." and the month row says "Waiting for HR" (existing words in the prototype are stand-ins; the engineer keeps the product's own) |
| Server refuses anyway (setting changed while the sheet was open) | The same sentence, in place of the form's button area, with "Nothing was sent." first. Typed text stays |

The existing sentence already adds the basis ("counted in working days on this person's own holiday list"). I kept it out of the prototype to keep one idea per sentence; the engineer should keep it as the manager one does, in the server's own words.

### 5.3 Employee, `#att-req` (path B)

Prototype draws: a note under the title, both date boxes, an inline sentence under From, and the server's refusal beside the button.

| State | What the person sees |
|---|---|
| No limit set | Nothing new: no note, no inline check |
| Limit set | Note under the title: **"You can ask about days from Mon 16 Nov onwards. Your joining day, Wed 11 Nov, is always allowed. For any other older day, HR can still fix it: tell HR which day and why."** The joining-day sentence only if their joining day is older. If the window is 0: "You can ask about today only (Thu 19 Nov)." |
| From is too old | Red text under From (red border, plus the words): the same sentence as section 5.2. The button is **not** greyed. A greyed button does not say why |
| From is the joining day | Green text: "Your joining day: you can always ask about this day." |
| Range starts on joining day and goes on | Section 4, decision 1 sentence |
| Submit with a too-old day anyway | Box beside the button, `role="alert"`: "Nothing was sent." + the sentence + "What you typed is still here." Focus goes to From |
| Page open a while, HR changed the number | The note and inline text use the number from page load. Submit uses the live number. The refusal then names the **new** date. Prototype shows this (change the HR number, return, press Submit) |
| End before start | "Please enter a valid date range." (existing) |
| Network drops | Existing behaviour: `mayHaveGone` says it may have gone through. Not changed |

**Why no `min` on the date boxes (AR3).** The phone's date picker would grey Wed 11 Nov, the one day the person is allowed. `min` cannot draw a gap. I recommend no `min`, the note, and the inline sentence. Reversible if Surbhi prefers `min` for non-joiners.

## 6. Words that must change (the brief's false statements)

**OS2: the manager hint.** Replace
> "...A manager who asks later than this is told to go to HR instead. **It does not limit HR, and it does not limit an employee asking about their own day** - HR can still fix any day. Use 0 to let a manager ask about today only."

with
> "...A manager who asks later than this is told to go to HR instead. It does not limit HR - HR can still fix any day. How far back an employee can ask about their own day is the separate setting above. Use 0 to let a manager ask about today only."

**Code comments that become false** (engineer to rewrite with the change; the key name is a proposal, the engineer names it):

1. `attendance_correction.py` ~1378-1382, ends "An employee raising their OWN day (`raise_correction`) is not bounded by it either ...". Replace the last sentence with: *"This setting binds the MANAGER's filing path only. An employee asking about their OWN day is bound by a separate setting (its own key, its own row in Org settings), except on their joining day, which is never bounded. Neither setting reads, greys or counts the other. HR's manual route is bounded by neither."*
2. `attendance_correction.py` ~654-655, "Never applied to somebody's own day: neither setting may narrow what a person asks about their own attendance." Replace with: *"The manager's switch and the manager's window never apply to somebody's own day. An employee's own day has its own window, and never on their joining day."*
3. `attendance_correction.py` ~658-661, "Only a MANAGER filing for somebody else is bound by the window. Their own month is not ..." True of the **manager** window only. Say so, and say the own-month boundary comes from the employee setting.
4. `portal.js` ~6228-6232, the comment above `acOutsideWindow`: "Null means no window binds this caller - their own month, or HR". Their own month can now be bound. Rewrite.
5. The day-sheet sentence in `portal.js` 6204 says "outside the window a manager can file within". An employee must not read that. Use the new sentence for `is_self`; leave the manager's as is.

**Acceptance check for the analyst:** after release, no string, comment or test name says an employee's own day is "not limited" or "not bounded". I found five places above by search for "does not limit", "not bounded", "their own month", "neither setting" in `alvoraa_portal` (searched `.py`, `.js`, `.html` under `alvoraa_portal/alvoraa_portal`; the first search pattern errored in my shell, so I re-read the lines by number instead of trusting a count). **Not searched:** other apps, docs, Desk Help articles, the DTC user manual. The engineer should search those.

## 7. Hindi (machine drafts, native review needed)

All strings are in the prototype's `L` table and show when you switch language. Hindi runs longer; the date is a value in the string (`drT` with an argument, as the code does), never glued on. **Not tested at 200% text.** The HR card is English only in the prototype: I did not check whether HR screens are translated in the product.

## 8. Accessibility and privacy

- Every input has a real `<label>`; the new HR number box is `aria-describedby` its hint. Save line is `role="status"`. The refusal box is `role="alert"`. The day sheet is `role="dialog"`, moves focus in, and Escape closes (prototype). **Not run:** screen reader, keyboard-only test. Colour is never the only signal: red and green text always come with words.
- Phone: 16 px field text, 44-48 px targets in the prototype CSS. **Not measured.**
- Privacy: the sentences carry a date only. No name, no reason for absence, nothing about anyone else. The joining date shown is the person's own.

## 9. What I removed (subtract pass)

- A "Joining day" chip on every month row (the sheet and the sentences say it).
- A live "right now the limit is back to ..." line on the HR row. The save line is what was asked for.
- `min` on date boxes (cannot draw the exception).
- A "contact HR" button (accepted; sentence only).
- Per-company text on the manager row (said once, on the new row).
- Nothing else. I did not draw the two other switches in the card; they do not change.

## 10. Not in this slice, for Surbhi to say yes or no (⚠ DECISION 2)

| Idea | Why it might matter | My view |
|---|---|---|
| Manager save line also names a date ("Saved. A manager can ask back to Mon 16 Nov.") | The two rows sit side by side with different save styles (01a C5) | One string. Worth doing in this slice if you agree; I did not draw it |
| A standing "Right now: an employee can ask back to Mon 16 Nov" under the box | HR coming back next week sees a "3" and no date | Not asked. Skip unless HR gets confused |
| A note to staff when the limit is first switched on | PM section 12: it narrows a right employees have today | Not a screen. HR's job; flag in the release note |

## 11. Usability test plan (High-impact: the joining day and the "before you type" note)

Five people, three of them on a phone: one new joiner, two long-serving, one HR person, one shift worker with a low-end phone. Tasks: (1) HR sets "3" and says what it means; (2) Asha raises 11 Nov; (3) Asha tries 12 Nov and says what to do next; (4) Ravi raises 3 Nov and says who can fix it. **Success:** HR names the right date unaided; every employee names HR as the way out without help; nobody calls the joining-day exception "a bug". **Changes the design:** if two of five call the exception a bug, add the row chip I removed.

## 12. For the business analyst: acceptance behaviours

1. Setting row exists above and separate from the manager switch; greys under no condition except no-permission; 0 to 30, blank, 0 each read as written; non-whole or out-of-range is refused with the existing words.
2. Save lines per section 5.1, naming a date from the **server**; blank, 0, n.
3. The date on the day sheet, the note, the inline sentence and the refusal come from one server function and are equal in a test that presses Submit on both paths and reads the payload.
4. Day sheet: too-old day shows the sentence and no form; joining day shows the green strip and the form; no limit changes nothing.
5. `#att-req`: note present only when a limit is set; joining-day sentence only when the joining day is older than the oldest day; Submit never greyed; refusal box keeps typed text and names the live date.
6. **Joining day always allowed** on both paths, whatever the setting (decision 1 for ranges).
7. Range whose first day is too old: refused whole, naming the oldest day.
8. No string says an employee's own day is "not limited"; the five places in section 6 are rewritten.
9. HR's own route is untouched by this setting.
10. Blank returns before any holiday lookup (OPS-5). Query count the same for a short and a long holiday list (OPS-2).
11. Hindi strings reviewed by a native speaker before release; sheet checked at 390 px and 200% text.

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | ⚠ DECISION 1: range starting on the joining day, (a) or (b) | Surbhi | AC 6 and 7 |
| 2 | ⚠ DECISION 2: manager save line gets a date too? | Surbhi | One string |
| 3 | Does the server send one "can raise" flag per day, or two dates? | `hrms-fullstack-engineer` | Where the rule lives; DS2 |
| 4 | Which holiday list does the HR save-line example use? | `hrms-fullstack-engineer` | Save-line words |
| 5 | Does `acNice` get a weekday ("Mon 16 Nov")? It has none today (code 6234). Weekday helps because a 3-day window moves over weekends; changing `acNice` also changes the manager sentence | `hrms-fullstack-engineer` | Date format across both |
| 6 | Grace's 3-a-month script, other tenants' rules, who uses `#att-req` (carried from Gate 1) | Surbhi | Release on Grace |

## Assumptions

- `[ASSUMPTION]` Joining date is `Employee.date_of_joining`; I did not read the code that would fetch it.
- `[ASSUMPTION]` Sat/Sun off in the prototype stands for a holiday list. Real lists differ.
- `[ASSUMPTION]` HR screens are English only today. Not checked.
- `[ASSUMPTION]` The product's own "Sent" and "Waiting for HR" words are kept; the prototype's are stand-ins.
- `[ASSUMPTION]` The setting starts blank on every tenant, so nothing changes for anyone until HR types a number.

## Handoff note

For the analyst and engineer: the one hard thing is that the screen and the guard must never hold two copies of the rule. Send the oldest day (and, better, a per-day yes or no) from the server and test that the screens and the refusal agree on both paths. Decision 1 changes one comparison. Note the attached joining-day exception is the case that started the slice, so its test must press Submit for a real joiner whose joining day is older than the window, on both screens. I do not disagree with the brief. I extend it in one place: the "first day decides a range" rule needs Decision 1 once the joining day is exempt. The prototype is on local disk only and unpublished.

---

## Gate 2 — Surbhi's decision, 19 November 2026

**Approved: go with this design.**

**⚠ DECISION 1 — answered: option (a), "joining day alone".**
The joining day is allowed only when From and To are both that day. A range that
starts on the joining day and ends later is refused whole, with a sentence saying
what to change. A joiner who missed 11, 12 and 13 November sends the 11th and asks
HR for the other two.

Rejected: option (b), a first-day check only. It would have let a joiner pass
From = joining day, To = today and carry every old day in between through the
window.

Prototype v1 as approved: https://claude.ai/artifact/HBQG6ExkZ9c9RKFEwmNJmG

**⚠ DECISION 2 — not answered and not asked again.** Whether the manager's save
line should also name a date so the two rows match. One string. Carried to the
spec as a small open item; it changes nothing structural.

**Unmeasured at this gate, and it must not be claimed as done later:** no screen
was opened in a browser. Phone width, 200% text, tap targets and keyboard-only
use are unmeasured. The Hindi is a machine draft awaiting a native reader.
