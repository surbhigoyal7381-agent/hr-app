---
slice: 066-grooming-red-mark
artifact: 02-design (the UX design; plays the part of 01b in the handoff contract)
author: hrms-ux-designer
date: 2026-10-24
status: draft v1 - waiting for Surbhi's review
inputs: 01c-security-privacy-requirements.md (revision 1, 24 Oct 2026, written in parallel; read before handoff and followed, see §0); 01-product-brief.md to its last section ("Surbhi's decisions", "Surbhi's answers to the open grooming questions", "Change to Q5"); the rules restated in the design request of 24 Oct 2026; ux-learnings.md (P8, prototype parity); portal code on origin/dev read in worktree dev-integration-2026-10-24 (portal.js Attendance and team sections, policies.html panel-att-record, attendance_correction.py); slice 063 prototype-v4 as the visual language; the local leave demo at localhost:8063 (demo site)
prototype: docs/slices/066-grooming-red-mark/prototype-v1.html. Invented data only. NOT published - no Artifact tool in this run; the lead session publishes it.
---

## Read this first - bad news at the top

1. **"Ask HR to look at this" must not use the attendance-correction route.** Approving a
   correction submits an `Attendance Request`, and Frappe HR then marks the day Present
   (`attendance_correction.decide` submits; `_becomes` says every reason except Work From
   Home becomes Present). A grooming dispute sent there would, if HR approved it, rewrite the
   day's attendance and still leave the grooming mark in place. If HR declined it to protect
   the attendance, the employee would read "Not approved" even after HR removed the mark.
   **I recommend a "questioned" state on the grooming record itself** (Q1). That is the route
   drawn in the prototype. **P1** if built the other way.
2. **Today's people are not on the Whole team list.** That list is built from submitted
   Attendance rows (`team_days`), and today's row does not exist until the shift ends. So the
   manager's way to mark needs one small new read: "my direct reports with a punch today",
   from Employee Checkin, through the existing `_punches_by_day` helper. No new page.
3. **At DTC, no ordinary staff member can be told by the app.** The security file (01c §0,
   verified on DTC today) found 0 of 445 staff with an email or mobile, and only 10 logins (7
   managers, 3 HR). So the bell notice, the month tile and "Ask HR to look at this" reach
   **nobody** who is likely to be marked. The prototype draws 01c's recommended stopgap: when
   the person has no login, the manager must tick **"I have told Rahul in person today"**, and
   the sheet tells them to say the person can speak to HR. Surbhi chooses (01c Q2); switch-on
   waits for it.
4. **01c is the authority on rules; this design follows it** (§0 below lists where). Two points
   still disagree and go to Surbhi: the dispute route (Q1) and the employee notice's last
   sentence (Q2).
5. **The prototype is not published.** No Artifact tool in this run.

## 0 · Where this design meets 01c

| Topic | 01c says | This design |
|---|---|---|
| No login (PRIV-2) | Say so to the marker; option (b): a required "told in person" tick | Drawn: tick in the sheet, sentence on the row |
| Removal (PRIV-3) | Cancel, never delete; one fixed removal reason | Drawn: remove sheet with a fixed "why". My labels are plainer; the analyst maps them to 01c's three values |
| HR's days (SEC-3) | Mark from the 1st of this month to today; a punch required; never full-day leave | Drawn: "a day last month", "no punch" and "leave" states |
| HR removal (SEC-5) | Until that person's slip is submitted | Drawn: last month's existing mark can still be removed |
| Grade (SEC-7) | No rate or a ₹0 rate → refused, "ask HR to set the grade" | Drawn for the manager and HR |
| Legal cap (SEC-10, interim) | Month total limited to 3% of wages | Drawn for the employee: the true figure and the limit, in words |
| Manager visibility (§4) | Today's marks on direct reports; afterwards only their own; nothing for skip-level | §6.3 follows it |
| Tenant gating (SEC-6) | Nothing where the pay rule set is off | The Today card, box, tag and tile appear only where the rule set is on |
| Dispute | "Speak to HR" | **Differs.** Surbhi's rule asks for a button; Q1 |

---

## 1 · Frame

**A store manager at DTC, on their phone at the counter, marks one direct report "Grooming
red" for today in under a minute; HR can do the same for anyone in scope on any open day; the
marked person hears about it the same day, sees why, sees what it costs them, and can ask HR
to look at it.**

| Persona | In scope | What changes for them |
|---|---|---|
| Line manager (store manager) | Yes, phone first | A "Today" card at the top of Attendance → Whole team. Mark, undo until midnight, a count of their own marks this month. Never a rupee figure. |
| HR Manager | Yes, laptop | A "Grooming red" box in the open day of anyone's month: mark, remove, answer a question. Two saved desk report views. |
| Employee (marked) | Yes, phone | A bell notice; a tag on the day; a box in the day with who, why and the rupee amount; a month tile; "Ask HR to look at this". |
| Contract staff | Yes, by absence | Nothing appears for them, anywhere. |
| CXO | No | Nothing new. One more line on the slip (the brief). |
| Colleagues | No | Never see anyone's mark. |

## 2 · Count the surfaces first (P8)

What already answers "this person's day", and what this slice does with each. **Reused
before new.**

| Surface that exists | Fate | Why |
|---|---|---|
| Attendance → picker → **Whole team** (slice 060) | **Extended**: a Today card above the filters | Where the manager already acts on direct reports' days. |
| Attendance → a person's **month**, open day (`acDetail`) | **Extended**: a tag on the day, a "Grooming red" box in the open day, a month tile for the employee only | One place for HR (any open day), the manager (a report's day) and the employee (their own day). One box, three readers, server flags decide the buttons. |
| The **bell** (Notification Log) | **Reused** through standard Frappe Notifications (configuration) | Already in every top bar. |
| The person **picker** (`whose_months_i_can_open`) | **Reused unchanged** | Already server-scoped; HR finds anyone in scope here. |
| The server's per-row "may I act" flags (`can_raise`) | **Pattern reused**: `can_mark`, `can_undo`, `can_remove` | No button where the server would refuse. |
| Desk **Report Builder** | **Configuration**: two saved views | The monthly marks-per-marker view HR asked for, with no new screen. |
| Attendance correction ("Ask HR to fix") | **Not reused for disputes** | It rewrites attendance on approval (bad news 1). |
| "Waiting for you" (correction queue) on Attendance | Not reused | It lists Attendance Requests only. |
| Attendance Insights, Team View | Not touched | They answer different questions. |

**New things, all small:** the Today card; the Grooming red box; one month tile; three
sheets (mark, remove, ask); two saved views; the notices. No new page, no menu item, no
settings page.

## 3 · Evidence

Captured on the local leave demo (`localhost:8063`, demo data, not production) on 24 Oct 2026
as the manager, HR and an employee, at 1440 × 900 and 390 × 844. Screenshots are outside the
repo: `C:/Surbhi-Git/hrlocal-data/ux-review/2026-10-24-slice066/`.

- **Fact (seen):** on the phone, Whole team stacks six controls (Whose record, From, To,
  Person, Group by, Show) before the first row. Anything placed under them is a long scroll
  away. So the Today card goes **above** the filters.
- **Fact (seen):** the month table has eight columns and scrolls sideways inside its own
  wrapper on the phone; "The day" is the second column, so a tag there stays visible.
- **Fact (seen):** the manager's phone login opened a "Goals & KPIs is not included in your
  plan / Not permitted" pop-up over the page. Unrelated to this slice; worth a ticket.
- **Fact (read):** `team_days` reads `Attendance` with `docstatus = 1` only. Today's people
  are missing until the shift ends.
- **Fact (read):** slice 060's team list carries a rule and a test that it shows **no money**.
  This design keeps it: no rupee figure reaches a manager.
- **Fact (read):** approving an attendance correction submits it and marks the day Present.

**Benchmark:** the brief's §4 covers it; I did no new competitor research for this slice. Its
"will not copy" list stands: no photo, no appearance AI, no grooming scorecard or ranking.

## 4 · Findings

| ID | Finding | Impact | Kind | Size | Severity | Evidence |
|---|---|---|---|---|---|---|
| GR1 | Today's punched-in people are not on Whole team, so a manager cannot mark today from it | High | New | M | P1 if left | `team_days` query |
| GR2 | Disputes through attendance correction would rewrite attendance | High | Fix (before build) | S | P1 if built that way | `decide`, `_becomes` |
| GR3 | On the phone the filters push the list below the fold | Medium | Improve | S | P3 | 390 capture |
| GR4 | No login means no notice, and at DTC no ordinary staff member has a login | High | Question (01c Q2) | S | **P1 for switch-on** | 01c §0, verified on DTC 24 Oct |
| GR5 | Removing by delete would lose who removed it and why | Medium | Settled by 01c PRIV-3 (cancel, never delete) | S | - | Brief §9 vs §15 |
| K1 | Server flags decide every button (`can_raise`) | - | **Keep** | - | - | portal.js `trDay` |
| K2 | No money on the manager's team list, with a test | - | **Keep** | - | - | portal.js comment, test |
| K3 | Picker, filters, chips, pager, the month table, the correction section | - | **Keep** | - | - | Unchanged |

## 5 · Flows

### 5.1 Manager marks today (phone) - 6 taps, 7 when the person has no login (the tick)

1. Attendance (bottom bar).
2. Tap the "Whose record" box → **Whole team**.
3. The **Today** card is first. Tap **Grooming red** on the person's row.
4. A sheet: pick one reason.
5. **Mark grooming red**.
6. The row now says what happened, with **Undo**.

Unhappy paths: no reason chosen → "Choose a reason first." in the sheet, focus moves to the
first reason. Network fails → the sheet stays open with the reason still chosen, the error
says nothing was saved, the button says **Try again**. Pressed twice → the button shows
"Saving…" and is disabled until the answer.

### 5.2 Manager undoes - 1 tap, same day only

**Undo** on the row. No confirm: undoing restores the person's pay, and the employee is told.
After midnight the button is gone and the row says "To remove it now, ask HR."

### 5.3 HR marks or removes (laptop)

Attendance → type the name in "Whose record" → open the day → the **Grooming red** box →
**Mark grooming red** (same sheet, "You are marking as HR") or **Remove this mark** (a sheet
with a fixed "why" list).

### 5.4 Employee is told, checks, asks (phone)

Bell → the notice → tap → their Attendance month opens at that day → the box says who, why
and how much → **Ask HR to look at this** → one confirm → the box says "You asked HR…".
HR answers with **Remove** or **Keep it and tell Rahul**; either way the employee gets a bell
notice.

## 6 · Screens and exact words

English first. Hindi in §9. *Rahul, Ravi, Ritika* and every time and amount are Sample.

### 6.1 Manager · Whole team · the Today card

Placed **above** the existing filters. Shown only to someone with direct reports (the
existing "Nobody reports to you…" message is unchanged and the card does not appear).

| Part | Words |
|---|---|
| Heading | **Today · Sat 24 Oct · Grooming red** |
| Sub-heading | Your direct reports who have clocked in |
| Help line | Off unless you mark it. Mark someone only if they are not groomed well today. They are told at once, with your name and the reason. |
| Row | **Rahul Sharma** / Sales Associate · Clocked in 10:24 · button **Grooming red** (spoken name: "Mark a grooming red for Rahul Sharma") |
| Row, marked by me | tag **Grooming red** + "Not in uniform", button **Undo**, then: "Marked by you at 10:31. Rahul has been told. You can undo this until midnight." |
| Row, marked by me, person has no login (every DTC staff member today) | "Marked by you at 10:31. Rahul has no login and will not get a notice. You confirmed you told them in person today. You can undo this until midnight." (amber background, words carry the meaning) |
| Row, grade not set (01c SEC-7) | "Rahul's grade is not set, so a grooming red cannot be priced. Ask HR to set it." No button. |
| After undo, no login | "Grooming red removed. Rahul has no login, so tell them it was removed." |
| Row, after undo | "Grooming red removed. Rahul has been told." and the **Grooming red** button is back |
| Row, marked by me, after midnight | "Marked by you yesterday at 10:31. The undo closed at midnight. To remove it now, ask HR." No button. (Only seen if a page is left open past midnight; next day the row is not in Today.) |
| Row, marked by HR | "Marked by Ritika Mehra (HR) at 11:05. Only HR can remove it." No button. |
| Row, Contract staff | "Contract staff are not given grooming reds." No button. |
| Row, half-day leave and punched in | Normal row; can be marked. The sub-line may say "Half-day leave this afternoon" because the manager already approves leave; it never says the leave type. |
| Not clocked in | "Asha Rani and 1 other have not clocked in today, so they cannot be marked yet." |
| Nobody clocked in | "None of your people have clocked in yet today. They appear here after their first punch." |
| Loading | Three grey bars and "Loading today's people…" |
| Count line | "You have marked 3 grooming reds this month." Count only. No names, no money. |

Who is listed: direct reports only (`reports_to` = me), with at least one punch today,
Contract staff included but without a button. Sorted by name. A team of 40 is 40 rows of
about 70 px on the phone; no paging is needed at DTC's team sizes `[ASSUMPTION]`.

### 6.2 The reason sheet (manager and HR)

Bottom sheet on the phone, dialog on the desktop. Focus moves to the heading; Escape and
Cancel close it and return focus to the button that opened it.

| Part | Words |
|---|---|
| Heading | **Grooming red for Rahul Sharma today?** (HR: "…on Wed 21 Oct?") |
| Help | Choose the one reason that fits. You cannot add your own words. |
| Reasons (radio, 48 px rows) | Not in uniform · Uniform incomplete or unclean · No name badge · Wrong footwear — **draft**: DTC gives the list, counsel checks it. None touches hair, beard, head covering, jewellery, skin or religious dress. |
| Info line | Manager: "Rahul will be told now, with your name and this reason. You can undo this until midnight." HR: "Rahul will be told now, with your name and this reason. You are marking as HR." |
| Buttons | **Mark grooming red** (primary) · **Cancel** |
| Person has no login (manager) | Instead of the info line: "Rahul has no login and will not get a notice from the app. Tell them today, and tell them they can speak to HR." and a required tick, a full 48 px row: **I have told Rahul in person today**. Not ticked → "Tick the box to confirm you told Rahul in person." (01c PRIV-2 option b; Surbhi decides) |
| No reason | "Choose a reason first." |
| Network failure | "Could not save the grooming red. Nothing was saved. Check your connection and try again." Button becomes **Try again**. The chosen reason stays. |
| Server refusal | The server's own sentence, shown in the sheet (for example "Rahul's manager changed today. Only Rahul's current manager or HR can mark him."). |

The reasons are read from the record's field options, the same way `reasons()` reads the
correction reasons, so the list and the screen cannot drift.

### 6.3 Manager · a report's month

The day gets a **Grooming red** tag, **only for marks this manager made** (01c §4: after the
day a manager sees only their own marks; a mark HR made shows on the Today card that day and
not after; a skip-level manager sees nothing). The open day shows the box: tag + reason,
"Marked by you on Sat 24 Oct at 10:24. Rahul has been told. You can undo this until midnight."
and **Undo** when it is theirs and today. **No rupee figure, ever, on someone else's record.**
The tiles, table and correction section are unchanged.

### 6.4 HR · the Grooming red box in an open day

| State | Words | Buttons |
|---|---|---|
| No mark, can mark | "No grooming red on this day." | **Mark grooming red** |
| No reporting manager | "Kiran has no reporting manager in Alvoraa, so only HR can mark Kiran's days." then "No grooming red on this day." | **Mark grooming red** |
| Marked | tag + "Uniform incomplete or unclean." / "Marked by Ravi Kumar (manager) on Wed 21 Oct at 10:31." | **Remove this mark** |
| Marked, employee asked | as above + "Rahul asked HR to look at this on Wed 21 Oct at 14:02." | **Remove this mark** · **Keep it and tell Rahul** |
| Kept | "You checked it on Sat 24 Oct and kept it. Rahul has been told." | **Remove this mark** |
| After marking | "Saved. Rahul has been told, with your name and the reason." | - |
| After removing | "Removed. Rahul has been told it was removed, by you: Marked by mistake." | **Mark grooming red** |
| A day last month, no mark | "No grooming red on this day." / "Marks can be added only for days in this month. A September mark that already exists can still be removed until September's pay slip is submitted." | none |
| Grade not set | "Rahul's grade is not set, so a grooming red would cost nothing and cannot be marked. Set Rahul's grade on his employee record first." | none |
| Contract staff | "Geeta is Contract staff. Contract staff are not given grooming reds, so there is nothing to mark." | none |
| Month closed | "Rahul's pay slip for September is submitted, so grooming reds for September are closed. They cannot be added or removed now." | none |
| On leave all day | "Rahul was on leave all day (Paid Leave), so there is nothing to mark." | none |
| No punch | "Rahul has no punch on this day, so there is nothing to mark. A grooming red is only for a day somebody came to work." | none |
| Own record | HR opening their own record sees the employee view. Nobody marks themselves. | - |

**Remove sheet:** "Remove this grooming red?" / "Why are you removing it?" / Marked by
mistake · Marked on the wrong person · The employee showed it was wrong / "Rahul will be told
it was removed, by you, and why. The person who marked it will see it is gone. A record of the
mark and of its removal is kept." / **Remove it** · **Keep the mark**. No reason → "Choose why
you are removing it." Failure → "Could not remove the mark. Nothing changed. Check your
connection and try again."

**Keep sheet:** "Keep the grooming red?" / "Rahul will be told that HR has checked it and the
mark stays. ₹200 still comes off his October pay." / **Keep it and tell Rahul** · **Cancel**.
(HR sees the amount here because HR sees it in the pay report anyway.)

### 6.5 HR · the monthly view per marker (desk, configuration)

Two saved Report Builder views on the grooming record:

1. **Marks per marker per month** — filter Date = this month; group by Marked by, Marked as;
   count; sorted highest first. HR's own marks are in it. No colour on a high count: the
   number speaks, and a large team can explain a large count.
2. **Asked to look at, not yet answered** — filter: asked, not answered.

### 6.6 Employee

**Bell notices** (Frappe Notifications; one per event):

| Event | Words |
|---|---|
| Marked | "Ravi Kumar, your manager, marked a grooming red for you today (Sat 24 Oct): Not in uniform. It takes ₹200 off your October pay. If you think it is wrong, open the day and tap "Ask HR to look at this"." (HR marks: "Ritika Mehra (HR) marked…") |
| Manager undid it | "Ravi Kumar, your manager, removed the grooming red he marked for you today (Sat 24 Oct). Nothing will come off your pay for it." |
| HR removed it | "Ritika Mehra (HR) removed the grooming red on Sat 24 Oct: Marked by mistake. Nothing will come off your pay for it." |
| HR kept it | "Ritika Mehra (HR) checked the grooming red on Sat 24 Oct and kept it. ₹200 still comes off your October pay." |

Tapping a notice opens Attendance at that day.

**Legal limit reached (01c SEC-10, interim):** the day says "A grooming red costs ₹200 a day
(the Senior rate). You have 5 this month, which would be ₹1,000. The law limits fines to 3% of
your wages, so **₹540** comes off your October pay." The tile reads "5 · ₹540, the legal limit".

**The month:** a tile **"1 · ₹200 — Grooming red · off October pay"**, shown only when there is
at least one mark, and only on the person's own record. The day carries the **Grooming red**
tag.

**The open day:** tag + "Not in uniform." / "Marked by Ravi Kumar, your manager, on Sat 24 Oct
at 10:24." / "This takes **₹200** off your October pay (the Senior rate)." / **Ask HR to look
at this**.

**Ask sheet:** "Ask HR to look at this grooming red?" / "HR will see your request and decide.
You will be told on the bell. Until then the mark stays." / **Send to HR** · **Cancel**. No
text box (Surbhi: "a plain 'Ask HR to look at this'").

**After asking:** "You asked HR to look at this on Sat 24 Oct at 14:02. HR will decide, and you
will be told on the bell." No button (one question per mark).

**Rupee rule, recommended:** the employee sees the amount, because it is their own pay. They
never see the marker's other marks or counts. Managers never see an amount. HR sees amounts in
the pay report and in the Keep sheet.

### 6.7 Contract staff

Nothing: no tile, no tag, no box, no notice. Their month is as it is today.

## 7 · What the screens need from the server (for the analyst)

The screens never work out a rule themselves. Each row or day carries flags:

| Flag | True when |
|---|---|
| `can_mark` | Exactly 01c SEC-1 and SEC-3: not yourself; not Contract; the grade has a rate above ₹0; no live mark that day; a punch that day and not a full-day leave; **and** either (you are their Active `reports_to` manager and the day is today) or (you are HR, the person is in your `permitted_employees()`, the day is in this calendar month, and no submitted slip covers it). |
| `needs_told_tick` | The person has no enabled login (01c PRIV-2 option b, if Surbhi chooses it). |
| `can_undo` | You made the mark as their manager, and it is still the same day (tenant time). |
| `can_remove` | You are HR, the person is in your scope, the month's slip is not submitted, and it is not your own record. |
| `can_ask` | You are the marked person, the mark exists, you have not asked yet, and the month is open. |
| `reason_closed` | One sentence, chosen by the server, when no button shows (Contract, month closed, leave, no punch, no manager). |

Plus, for the Today card: direct reports with a punch today, and my mark count this month.

## 8 · Privacy and accessibility

- **Who sees a mark:** the person; anyone who can already open their month (their reporting
  line and HR in scope). Never colleagues. The Today card lists only the manager's own direct
  reports. The count line is the manager's own count.
- **Least data:** the manager sees reason and time, no amount, no grade. The employee sees who
  marked them (Surbhi's rule) but nothing else about that person's marking.
- **No free text anywhere** in marking or removing. The employee's "ask" has no text box.
- **Leave:** a manager may see "Half-day leave this afternoon" (they approve it); the leave
  type is shown only to HR, who already sees it.
- **WCAG 2.2 AA:** every button names the person in its spoken name; the reason list is a
  radio group with a label; focus moves into each sheet and back; Escape closes; the tag says
  "Grooming red" in words, colour is never the only signal; amber, not red, because red is
  kept for "wrong" or "overdue". Phone targets ≥ 44 px (48 px reason rows); text ≥ 12 px.
- **NFR (nfr-budget §2):** employee-facing on 3G, p95 ≤ 2.5 s with a skeleton within 300 ms:
  the Today card shows grey bars at once and fills in. A whitelisted call ≤ 500 ms: marking is
  one call. The punch read must keep a flat query count for 20 or 400 people.

## 9 · Hindi (machine draft, for native review)

Drawn in the prototype for the Today card, the reason sheet, and the employee's notice and day:
ग्रूमिंग रेड · आज · वापस लें · ग्रूमिंग रेड लगाएँ · रद्द करें · वर्दी में नहीं · वर्दी अधूरी या
गंदी · नाम का बैज नहीं · गलत जूते-चप्पल · HR से इसे देखने को कहें · HR को भेजें. Measured at 390 px
with no overflow. HR screens stay English (laptop, office staff) `[ASSUMPTION]`.

## 10 · Checks

**Measured** (Playwright, Chrome, 24 Oct 2026): 240 renders — every state of every person, plus
each sheet open, at 390 and 1440, light and dark, English and Hindi on the phone. **No sideways
scroll, no text under 12 px, no phone target under 44 px, no script errors.** The first pass
found the month-table rows at 42 px on the phone; fixed. Two click-throughs passed: mark with no reason → error; choose → mark;
undo. And no login: reason, no tick → error; tick → mark.

| Check | Result |
|---|---|
| Frontline bar: done in two minutes on a phone | Manager: 6 taps. Employee: 4 taps from the bell to "Send to HR". |
| Visibility of status | Every action ends in a sentence on the row or box where it was taken. |
| Error prevention | Default off; one reason required; one mark a day; no undo after midnight. |
| Recognition, not recall | Reasons are a list; the count line saves the manager counting. |
| User control | Undo same day; HR remove; the employee's ask. |
| Refusals | No photo, no AI, no free text, no ranking, no colleague visibility, no colour flag on a manager's count. |
| Red team: network drops | The sheet keeps the reason; nothing half-saved. |
| Red team: manager changes mid-day | The server refuses with its own sentence. |
| Red team: nobody can be told (DTC today) | The manager cannot mark without confirming they told the person; HR's view shows who marked. |
| Red team: wrong person on a shared phone | The row says the name; undo is one tap; the employee is told. |
| Red team: 400 people (HR) | HR marks from one person's month, found by the server-side search; nothing lists 400 rows. |

## 11 · What I am NOT changing

The page name "Attendance"; the picker and its search; Whole team's filters, chips, grouping,
pager and "Ask HR to fix"; the month tiles that exist; the month table's columns and phone
behaviour; the day facts and punches; the correction form and its window rules; the "Waiting
for you" queue; the bell; the bottom bar; Attendance Insights; Team View. The one visible move:
on the phone, Whole team's filters now sit under the Today card.

## 12 · Questions for Surbhi

| # | Question | My recommendation |
|---|---|---|
| Q1 | How does "Ask HR to look at this" reach HR? | **A "questioned" state on the grooming record + a bell notice to HR; HR answers Remove or Keep, and the employee is told either way.** Not the attendance correction: approving one rewrites the day to Present. |
| Q2 | The employee notice's last line: 01c fixes it as "If it is wrong, speak to HR." | Follows Q1. If Q1 is the button: "If you think it is wrong, open the day and tap "Ask HR to look at this"." If not: 01c's line. |
| Q3 | Nobody at DTC can get a notice (0 staff logins). How are they told? (= 01c Q2) | **01c's option (b): the manager's required "I have told them in person today" tick** (drawn), then staff access when DTC rolls it out. |
| Q4 | HR marks only this calendar month (01c SEC-3), but may remove until the slip. On 1-2 November HR cannot add an October mark. Accept? | **Yes, accept.** A late mark is a new fine the person was never shown on the day; a late removal only helps them. |
| Q5 | Does the employee see the rupee amount? | **Yes, on their own record only** (tile, day, notice), with the legal-limit sentence when it applies. Never the manager. |

Settled by 01c, no longer questions: removal is a cancel with a reason, never a delete (PRIV-3);
HR and the manager can mark only a day with a punch and never a full-day leave (SEC-3).

## 13 · Not in this slice

A Today card on the manager's Home; opening Attendance straight on Whole team for managers; an
employee text box on the ask; a grooming count for the CXO; a cap per manager; email or SMS
notices.

## 14 · Usability test plan (High impact)

Five DTC store managers, five frontline staff, one HR person, on their own phones.

| Task | Success | What would change the design |
|---|---|---|
| Manager: mark Rahul for no badge today | Done in under 60 s with no help | More than 2 of 5 do not find Whole team → open Attendance on Whole team for managers |
| Manager: undo it | Under 10 s | Anyone looks for undo elsewhere |
| Employee: say who marked you, why, and what it costs | All three right after reading the notice | Anyone misreads the amount as a monthly total or misses "your manager" |
| Employee: ask HR | Done in under 30 s | Anyone expects to type a reason → reopen the no-text decision with Surbhi |
| HR: find who marked most this month | Under 1 min from the desk | HR cannot find the saved view → pin it on the HR workspace |

## 15 · What the analyst must turn into acceptance criteria

Every row in §6 (each state and its exact words), the flags in §7, the rupee rule in §6.6, the
Contract rule in §6.7, the notices in §6.6, and "the Today card sits above the filters on the
phone". **Prototype parity:** each of these is a row in the spec's parity table, tied to a
story and a test.

## Subtract pass

Removed on this pass: a confirm before the manager's Undo (undo restores pay and the employee
is told; a confirm only slows the fix); a colour flag on high counts in the HR view; a text box
on the employee's ask; a "removed" history line in the employee's day (the bell already says
it); paging on the Today card; Hindi for HR screens. Kept the "no login" sentence: without it
the "told the same day" promise is silently false.

## Open questions

Q1–Q5 above, for Surbhi. 01c's own open questions (counsel on the Code on Wages fine rules,
Q-C1) block switch-on, not this design. The reason list in DTC's words, checked by counsel (brief). Retention
of a mark (brief, with counsel).

## Assumptions

- `[ASSUMPTION]` "Today" is the calendar date in the tenant's time zone; for a shift that crosses
  midnight it is the date of the person's first punch of that shift.
- `[ASSUMPTION]` DTC's pay month is the calendar month.
- `[ASSUMPTION]` DTC teams are small enough (under about 40 direct reports) that the Today card
  needs no paging.
- `[ASSUMPTION]` The rate on screen is the grade on the day of marking; if the grade changes in
  the month, the slip's figure wins and the tile follows the slip.

## Handoff note

- Prototype: `docs/slices/066-grooming-red-mark/prototype-v1.html`, invented data only, **not
  published** (no Artifact tool). The lead session publishes it.
- I did not edit `ux-learnings.md` (this run was told to create files only). Entries to add:
  (1) *a reused route must be checked for what its approval DOES, not only where it goes — the
  correction route rewrites attendance*; (2) *a list built from end-of-day records cannot serve
  "today"; check when the row is created before placing a same-day action on it*; (3) *on the
  phone, a new same-day action goes above stacked filters, measured, not below them*.
- I agree with the brief and follow 01c. The disagreements are the request's suggested dispute
  route (Q1) and 01c's "speak to HR" in place of Surbhi's button (Q1, Q2), raised rather than
  changed quietly.
- 01c appeared in the slice folder while I worked. I read it before handoff and changed the
  prototype to match it (no-login tick, grade refusal, last-month rule, legal cap, manager
  visibility).
