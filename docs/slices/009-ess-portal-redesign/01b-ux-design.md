---
slice: 009-ess-portal-redesign
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-09-19
status: draft
inputs: [00-assessment-and-plan.md, appendix-a-frame.md, appendix-b-home-inbox.md, appendix-c-time-pay.md, appendix-d-growth-team-people.md, .claude/context/ux-learnings.md, docs/priorities/2026-09-18-priority-order.md, prototype v1 (11 Sep 2026)]
---

# Employee portal redesign — the design, and the frame for Wave 1

## Bad news first

**Three things in the approved plan no longer fit the product, and I have not built
them as written.** Each is explained in §10, with my reasoning.

1. **"Who's off" (Q15) should be dropped, not decided.** The plan still asks whether
   colleagues may see each other's approved leave. Now that the portal is every
   tenant's landing page, that question is answered by the one-way rule: presence is
   fine, the reason for an absence is not. I have designed presence only and no leave
   list for peers. Q15 becomes "presence only — confirm", not an open choice.
2. **The prototype's "progress bar per goal" is the wrong lead number for a KPI.**
   Now that a reading is "the amount since your last update" and stays pending until
   approved, the honest headline is the **approved** figure, with the pending amount
   named beside it. A single bar hides the difference and makes the person think their
   number moved when it did not.
3. **Wave 5 is too late for Hindi and Punjabi to be safe.** Every screen in Waves 1–4
   should be laid out and measured in Hindi from the day it is built, even while the
   words stay English. I have measured the prototype in Hindi and Punjabi and it holds,
   but that only stays true if it is checked each wave, not once at the end.

**One honest limit on this run:** I did not open the local bench. The task was
read-only on code and no bench commands, and another session is mid-release. So the
current-state evidence here is carried over from the four analyst appendices (measured
on the local PP Jewellers copy on 14 Sep 2026) and the Sep 2026 portal review. Nothing
new was captured from the running product today.

---

## 1. What this run produced

| # | Asked for | Done |
|---|---|---|
| 1 | Corrections D1–D8 applied to the prototype | Yes — §4 |
| 2 | The owner / HR view (D3), which the plan says is missing | Yes — §6 |
| 3 | A design that fits real PP Jewellers people on a phone | Yes — §3, §5, §9 |
| 4 | The Wave 1 frame: navigation, page shell, first screen | Yes — §5 |
| 5 | The four behaviour changes built in, not designed around | Yes — §7 |
| 6 | A clickable prototype | Yes — §2 |
| 7 | What I am **not** designing | Yes — §11 |
| 8 | What in the plan I now think is wrong | Yes — §10 |

---

## 2. The prototype — how to open it

    C:/Surbhi-Git/hrlocal-data/prototypes/009-ess-portal-redesign/prototype-v2.html

Double-click it. It is one self-contained HTML file and needs no server, no bench and
no internet. Version 1 (11 Sep) sits beside it as `prototype-v1.html`, so the change is
visible.

**It is outside the repo on purpose.** It holds real figures from the local PP
Jewellers demo copy. Everything invented carries a visible **Sample** tag on screen.

⚠ **I cannot publish it myself.** I have no artifact tool in this run. The session that
ran me should publish `prototype-v2.html` and give Surbhi the link.

**The black bar at the top is review scaffolding, not part of the product.** It lets
you switch:

- **Person** — Rahul (senior sales executive), Sandeep (floor manager, 19 people),
  Kamal (owner who also holds HR).
- **View** — Desktop, or a 390 px phone.
- **Payroll on this tenant** — On or Off, so you can see what a tenant without payroll
  gets. This is the evidence for decision Q2.

**Language and light-or-dark are deliberately *not* on that bar any more.** They now
live inside the product, in the profile menu at the bottom of the left-hand menu —
which is what you decided in Q3. Open the menu and press your own name.

---

## 3. Who this is for, and what each one is trying to do

PP Jewellers is a jewellery retailer: four stores, 403 people. Most of them stand on a
shop floor.

| Persona | Real person in the prototype | Their moment | What the design owes them |
|---|---|---|---|
| **Frontline retail staff** | Rahul Kumar, senior sales executive, Chandigarh | Between customers, on his own phone, two minutes | One big Check In. "What needs you" before anything else. Every number explained in one tap. Hindi or Punjabi. |
| **Floor manager** | Sandeep Sodhi, 19 reports, Noida | Between the counter and the back office | The two people who need him, not the 19 who don't. Approve or decline where he sees the problem. |
| **Store HR / owner who holds HR** | Kamal Gupta, owner and MD | Five minutes, often on a phone | One trustworthy number. What needs him first, the business second, HR's queues never mixed into the business. |
| **Employee with no payroll on their tenant** | Rahul, with the Payroll switch Off | — | No Pay menu at all. Nothing greyed out. |

**Deliberately out of scope this run:** the vendor and driver portal (it is opt-in and
off for PP Jewellers, so it appears nowhere except as something the owner can ask for),
the desk, and any screen for a CXO across several companies — PP Jewellers has one.

---

## 4. The corrections D1–D8: what changed and why

| # | What the plan asked for | What I did | Where to look |
|---|---|---|---|
| **D1** | Phone layout by `@media`, not a container query on the whole app | The stylesheet now has one `@media (max-width: 760px)` block and **no `container-type` anywhere**. So every pop-up stays anchored to the screen. To still show a 390 px phone inside a wide browser, a short script copies *the same rules* under `.stage.phone`. Nothing is written twice by hand, so the two cannot drift apart. | Any screen, Phone view |
| **D2** | A profile menu with log out | Bottom of the left menu, your own name and role, opens a sheet: language, light or dark, My account, Switch to the full desk (managers and owner), Tenant admin (owner), **Log out**. | Press your name |
| **D3** | Design the owner / HR view | A whole persona — see §6. | Switch Person to Kamal |
| **D4** | Raise small sizes and fix contrast | `--text3` is now `#736D65` (4.74:1, was 3.36:1). Smallest text is 12 px, everywhere. Measured: **42 screen renders, 3 people × 2 devices — no text under 12 px, no target under 24 px on a mouse or 44 px on a phone, nothing wider than the screen, no script errors.** | §9 |
| **D5** | Correct data copied from the wrong source | Casual Leave now reads **8 of 8 used, 0 left** (the late rule took 2.5 days). Sakshi manages **13**, not 9. 7–9 Sep say **"Marked absent"**, not "No punch and no leave". The 9 Nov holiday is **Diwali Padva**. The late rule says **"more than 60 minutes"**. | Rahul → Time; Apply leave |
| **D6** | Remove "Nobody is on leave today" from the peer view | Gone. Replaced with a line that says what the card *is*: "Who is in, and who is still to come. Nothing about why anyone is away." | Rahul → Home, right column |
| **D7** | Decide who fixes attendance | Not mine to decide — raised as **Decision 1** in §13 with my recommendation. The prototype currently sends it to the manager, and there is a single constant in the code (`FIX_GOES_TO`) so it can be flipped in one place once you rule. | Rahul → Home → "Fix" |
| **D8** | Replace Sample cards with real rules, or mark them | Every invented number still carries a **Sample** tag. Three former "Sample" cards now run on real rules instead: team presence ("in / still to come", no leave), goal evidence (approved vs pending), and the late rule. Advance limit, repayment and Form 16 stay labelled Sample, because there is no data source yet. | Everywhere |

---

## 5. Wave 1 — the frame

Everything after Wave 1 hangs off this, so it is specified to the word.

### 5.1 The menu

One list drives the left rail, the phone bottom bar, the page title and page search. An
item only exists if this person's role, plan and features allow it — **there are no
greyed items and no buttons that fail on click.**

| Group | Item | Who sees it |
|---|---|---|
| **Me** | Home · Inbox | Everyone |
| **Time** | Attendance & leave | Everyone |
| **Pay** | My pay | Only where the tenant has payroll. Otherwise the whole group disappears |
| **Growth** | Goals & reviews | Everyone |
| **Team** | My team | Anyone with direct reports — manager *or* owner |
| **Company** | People | Everyone (a staff directory, per Q4) |
| **Company** | HR analytics · Reviews (HR) · Policies · Org settings | HR and the owner only |

Q1 is honoured: **one Company group**, no separate Admin group.

### 5.2 The top bar

Group name above, then the page title in words — "Home", "Attendance & leave",
"Reviews (HR)". Never the tenant name on every page, which is anti-pattern G1. On a
deep page (self-review, a person) the group is a link back. Search and the bell sit on
the right, **on desktop as well as phone** — desktop has no bell today (G4).

### 5.3 The phone bottom bar (Q2)

Four buttons and More. The four are the ones that person actually uses:

| Person | The four buttons |
|---|---|
| Employee, tenant has payroll | Home · Time · Pay · Goals |
| Employee, **no payroll** | Home · Time · Inbox · Goals |
| Floor manager | Home · Team · Inbox · Time |
| Owner / HR | Home · Inbox · Company · Team |

Labels are short words, 12 px, centred, allowed to wrap to two lines — because Hindi
and Punjabi run about 30% longer. Measured in all three languages at 390 px: no wrap
failure, no overflow.

### 5.4 The Inbox count (Q5)

Everything: approvals waiting on you, policies you have not acknowledged, and **your own
open requests**. The number on the bell and on the menu are the same number, worked out
in one place.

### 5.5 Search

Pages come from the menu, so **search can never offer a page this person cannot open**.
People come from the list this person is allowed to see:

- an employee finds their own team, their manager and the leadership;
- a manager finds their own team plus their own manager;
- the owner finds everyone.

When nothing matches, the empty state says what you *can* find, so a blank result never
reads as "the product is broken":

> Nothing matches "Kamal".
> You can find your own team, your manager and the pages you can open.

### 5.6 The profile menu

> **Kamal Gupta** · Owner & Managing Director · PP Jewellers
> **Language** — English · हिंदी · ਪੰਜਾਬੀ — *Saved to your account, so it follows you to any device.*
> **Light or dark** — Match my phone · Light · Dark — *Saved on this device only.*
> My account — *Your details, password and photo*
> Switch to the full desk — *Reports and settings that are not in this portal*
> Tenant admin — *Plan, users and features for PP Jewellers*
> **Log out**

### 5.7 States the frame must have

| State | What it says |
|---|---|
| Loading | A skeleton of the page within 300 ms (nfr-budget §2). Never a spinner on a blank screen. |
| First time, nothing due | "Needs you — **All clear**". The Check In button is still the largest thing on the page. |
| No permission | The item is not in the menu. If reached by a link: "This page is not part of your access. Ask HR if you think it should be." |
| Error on one card | The card says what failed and offers "Try again". The rest of the page still works. |
| Whole page failed | One sentence, one button, and a line the person can read out to HR. Never a raw server error. |

---

## 6. The owner and HR view (D3)

Two rules run through every screen here.

**Rule 1 — what needs him first, the business second, and HR's queues never inside the
business.** Slice 012 found HR work queues mixed into a page an owner reads as the state
of the company (LV8). So Kamal's Home is: *greeting strip → Needs you → PP Jewellers
right now*. The cycle progress and his own team sit in the right-hand column, clearly
his work, not the company's health.

**Rule 2 — reviews come from two lists, because he is two people.**

- **My team** — his own four direct reports. Here he acts as a manager: read the
  self-review, remind, add a 1:1 note.
- **Reviews (HR)** — everyone in the cycle. For anyone in his own reporting line the
  Open and Remind buttons are **not there**. In their place, a plain sentence:

  > You are Sandeep Sodhi's manager, so the HR steps on this review are done by someone
  > else. You can still see where it has reached.

  No greyed button. The person is told why, not shown a door that will not open.

**Honest numbers.** The company figures carry the date their data runs to. September's
attendance shows **"Needs review"**, not a number and not 0%, because 330 people were
auto-marked absent on 7–9 Sep. Tapping it opens **Data to review**, where HR can settle
the days behind it. That is the slice 012 pattern, kept: a "needs review" label always
leads somewhere for the person who can fix it.

**Privacy on the owner's screens.** Head office is shown as "Not shared" in the store
table, and the *next* smallest group is left out too, so the hidden one cannot be worked
out by subtraction. The explanation leads with fairness:

> Head office has fewer than five people in this figure. Showing it could point at one
> person's attendance or leave. The next smallest group is left out too. If it were not,
> you could work the hidden one out by taking it away from the total.

**What the owner does not get.** No per-person attendance ranking. No reason for anyone's
absence. No rating suggested by a machine — the Performance tab says so in one line, and
says forced distribution is off.

---

## 7. The four behaviour changes, built in

### 7.1 A review works on its own copy

On step 1 of the self-review, above the goals:

> **These figures were copied into your review on 1 Oct 2026.**
> They stay as they are while the review is open, so you and your manager are looking at
> the same numbers. Your live goals keep moving on the Goals page.

The same sentence, shortened, sits under the owner's cycle card. Two consequences for
the build: the review screen must never re-read the live goal, and the Goals page must
never show the review's frozen figure.

### 7.2 KPI progress is the amount since your last update

The KPI card leads with the **approved** figure and a chip that says "Approved figure".
Anything pending is named separately, never folded in:

> **₹3.1 L is waiting for Sakshi Verma.**
> Logged on 10 Sep 2026 for 1 – 10 Sep. The figure above does not move until it is
> approved, so nobody sees a number that has not been checked.

The logging sheet asks the right question, in the person's words:

> **How much since your last update? (₹ lakh)**
> *Only the new amount. It is added to ₹28.4 L once it is approved.*
> Covers from … To …
> **What happens next.** This goes to Sakshi Verma and stays Pending until she approves
> it. Your figure on the Goals page does not change today.

And the confirmation is honest rather than congratulatory:

> Sent. Your figure changes only when Sakshi Verma approves it.

### 7.3 Lateness has a grace period, set per organisation

The day always shows the true minutes. Grace only decides whether it counts.

| Arrival | What the day says | Chip colour |
|---|---|---|
| 09:25, shift 09:30 | On time | green |
| 09:42, grace 15 min | **Late by 12 min (within grace)** | neutral grey, not amber |
| 10:45 | Late by 75 min | amber |

Three consequences, all built into the prototype: the "Arrived on time" statistic becomes
**"Arrived within grace"**; the day sheet shows a **Grace** row that names the setting
("15 minutes, set by PP Jewellers"); and Org settings carries the grace period as a
setting the owner can see, with the rule written next to it in plain words.

### 7.4 The vendor and driver portal is opt-in

It is off for PP Jewellers, so it appears in **no menu, for anyone**. The only place it
exists is Org settings, under a heading that is true rather than teasing:

> **Not switched on for PP Jewellers**
> **Vendor and driver portal** — Lets outside drivers and vendors check in and send
> documents. It is off unless a company asks for it, so nobody here sees a menu item they
> cannot open. → *Ask about it*

That is a sales conversation for a buyer, not a locked door for a shop assistant.

### 7.5 The portal is now the landing page

This is the biggest change of all and it lands on Home. Three things follow:

1. **Home must be honest before it is full.** The first screen after logging in is the
   one a brand-new tenant sees with no data. "Needs you — All clear" is a real state,
   designed, not an accident.
2. **Speed is a design requirement, not a footnote.** Skeleton within 300 ms, page within
   2.5 s on 3G (nfr-budget §2). Home fills in card by card — "Needs you" first, because
   that is why the person came.
3. **The 1.5-second approvals check must go before this ships.** It takes 11.6–16.4
   seconds for HR today (Wave 0d, P1). On a landing page that is the first thing every
   person in the company experiences, every morning.

---

## 8. Findings from my own look, this run

Measured, not eyeballed (P4). Evidence:
`C:/Surbhi-Git/hrlocal-data/ux-review/2026-09-19-slice009/`

| ID | Finding | Impact | Kind | Size | Evidence |
|---|---|---|---|---|---|
| N1 | Menu links in the phone drawer were 37 px tall — under the 44 px rule, in the one place a phone user must tap | High | Fix | S | Measured, all personas, 390 px |
| N2 | "Ctrl K" hint and the tenant monogram were 10–11 px | Medium | Fix | S | Measured |
| N3 | Section links ("Inbox →", "All 4 →") were 18 px tall; under WCAG 2.2 AA's 24 px on a mouse and far under 44 px on a phone | Medium | Fix | S | Measured, every screen |
| N4 | Rating buttons in the self-review were 32 px tall on a phone — the one screen that has to finish in two minutes | High | Fix | S | Measured, phone |
| N5 | The design system's `--fs-xs` is 11 px, below our own 12 px floor. I raised it to 12 px in the prototype | Medium | New | S | `design_system.html`; raised as **Decision 5** |
| N6 | Everything above is now clean: 42 renders, nothing under the limits, no sideways scroll, no script errors | — | Keep | — | Measured after the fixes |
| N7 | Hindi and Punjabi at 390 px, light and dark: no overflow, no wrap failure, no error | — | Keep | — | Measured |

**Kept from the earlier review, because they still work:** the tenant-coloured check-in
hero; the late-rule explanation that walks through the week day by day; the guided
five-step self-review with autosave; "act in place" on a tapped day.

---

## 9. Accessibility and privacy

**WCAG 2.2 AA** (nfr-budget §7), on the screens in this design:

- Smallest text 12 px. Body 13 px. Inputs 16 px, so a phone does not zoom on focus.
- Targets: 44 px on a phone, never below 24 px on a mouse. Measured on all 42 renders.
- Contrast: `--text3` raised to `#736D65` (4.74:1 on the page background).
- Colour is never the only signal. Every chip says its state in words: "Late by 12 min
  (within grace)", "Marked absent", "Waiting for Sakshi Verma", "Needs review".
- Every input has a real label. The sheet is a dialog with a title, closes on Escape.
  The toast is announced (`role="status"`).
- Usable at 390 px and in dark mode; `prefers-reduced-motion` respected.

**Still to do, and I say so plainly:** focus is not yet trapped inside the sheet and
returned to the control that opened it. That is Wave 1's shared-sheet step (FR-09) and
it must not be skipped.

**Privacy:**

- Presence is shown; **the reason for an absence is never shown to a colleague**. The
  peer card says so out loud.
- A manager sees a report's late **days**, never the rupee amount (Q-b, already decided).
- Search returns only people this person may see, and never a phone number, an email or
  an employee ID.
- Aggregates: minimum group of five, and the next-smallest group is suppressed too.
- Nothing invented is passed off as real. Every invented figure carries a Sample tag.

---

## 10. What I think the plan now gets wrong

**1. Q15 "Who's off" is not a real choice any more.** The plan asks whether employees may
see colleagues on approved leave and from which group. Approved leave *is* the reason for
an absence — it tells a colleague this person is not ill, not absent without leave, but on
holiday. Slice 002 already ruled that out, and the one-way rule in product-context §2
settles it. I have designed presence only ("in / away / still to come") with no names
attached to leave. **My recommendation: close Q15 as "presence only", do not ask it.**

**2. Wave 4's "Feedback" is the largest single item and the least evidenced.** It needs a
new record type, about four build days, and nobody has asked for it in any evidence I can
see. The frontline job — "know what I am measured on, and that it is fair" — is served by
Waves 2 and 3. **My recommendation: move Feedback to the end of Wave 4 as a separate go
or no-go, so it cannot delay Team and People.**

**3. The KPI headline (see Bad news, point 2) and languages (point 3).** Covered above.

**4. One thing the plan is right about that I want to underline.** Wave 0b (wrong numbers)
must land before Wave 3. The redesign puts late minutes and leave balances on bigger,
clearer screens with an explanation attached. Explaining a wrong number carefully is worse
than showing it quietly.

---

## 11. What I am deliberately **not** designing in this run

So the scope is honest:

- **Wave 3 Time and Pay screens beyond the corrections.** The v1 designs stand; I fixed
  the data, the grace wording and the sizes, and did not redesign them.
- **Wave 4 Growth, Team and People beyond the two new behaviours.** Feedback, the person
  sheet and the directory are v1 as they were.
- **Calibration, performance setup and policy compliance as full screens.** They appear in
  the owner's menu and as honest stubs; each needs its own design run.
- **The desk.** Anything the portal cannot do goes to the desk through the profile menu.
- **The vendor and driver portal.** Off, opt-in, not designed.
- **A multi-company CXO view.** PP Jewellers has one company. Slice 012 owns leader views.
- **The mobile app's My HR tab.** Slice 013 owns it. Wave 1 only has to leave room:
  hide the portal's own bottom bar inside the app, and send the portal's Check In to the
  app's photo check-in.
- **Real Hindi and Punjabi wording.** The strings in the prototype are machine drafts.
  A native speaker and PP Jewellers' own HR must review the HR terms.
- **A fresh competitor benchmark.** The Sep 2026 review's benchmark is carried over and is
  `[recall — verify]`. I made no new competitor claims today.

---

## 12. Usability test plan (for the High-impact items)

Five people from PP Jewellers, on their own phones, in the store, 20 minutes each: three
sales staff (at least one who prefers Hindi or Punjabi), one floor manager, one store HR.

| Task | Counts as success | What would change the design |
|---|---|---|
| "You were marked absent on Monday. Sort it out." | Sends a correction or leave in ≤ 2 min without asking anyone | If they look for it in a menu instead of tapping the day, "act in place" is not discoverable — put a Fix button on Home permanently |
| "₹548 came off your August pay. Why?" | Explains the rule in their own words | If they cannot, the walk-through is too long — lead with the sentence, not the table |
| "Log what you sold since your last update." | Enters the *new* amount, not the running total | If two of five enter the total, the field label is wrong — show the running total next to the box |
| Floor manager: "Two people need you. Deal with them." | Approves or declines from Home without opening another page | If they go to Team first, the Home approval card is not trusted — add the person's photo and the request date |
| Owner: "How is attendance this month?" | Says "it is not settled yet" rather than reading a number | If anyone reads "Needs review" as a figure, change the word |

---

## 13. Decisions I need from you

Each with my recommendation, so you can answer in one line.

| # | Decision | My recommendation |
|---|---|---|
| **1** | **Who decides an attendance fix** (Q6, D7): the manager, who was on the floor that day, or HR, which is how it is built today? | **The manager decides, and HR can see every one and step in after two working days.** The manager holds the evidence; HR holds the backstop. One constant in the code flips it. |
| **2** | **The bottom-bar sets in §5.3.** | Take them as drawn. The only one I am unsure of is the owner's fourth button — "Team" (his four reports) versus "Reviews (HR)" during a cycle. I recommend **Team**, because it is his own work and it is there all year. |
| **3** | **Q15 "Who's off".** | **Close it: presence only.** Do not ask employees or managers whether they want to see leave. See §10. |
| **4** | **Where Feedback sits.** | **Move it to the end of Wave 4 as its own go or no-go.** It is the biggest item with the least evidence. |
| **5** | **`--fs-xs` in the design system is 11 px, below our 12 px floor.** | **Raise the token to 12 px** in `design_system.html` as part of Wave 1, rather than leaving each screen to work around it. This is a one-line change that affects every page, so it is yours to approve. |
| **6** | **Does the owner get a Check In button on Home?** | **No, unless they have a shift.** The rule I have built: the check-in hero appears when the person has a shift. Kamal has none, so his Home leads with the company instead. |
| **7** | **The grace period wording**: "Late by 12 min (within grace)". | Take it. It is the only wording I found that is both true (the minutes are real) and fair (it did not count). If you prefer shorter, "12 min — within grace" also fits at 360 px. |

Everything else stays as the plan has it. Q1–Q5 are already decided and are built as
decided.

---

## 14. For the business analyst — behaviours to turn into acceptance criteria

1. A menu item, a bottom-bar button and a search result exist **only** if that person's
   role, plan and features allow it. No greyed items anywhere in the portal.
2. The Inbox count = approvals waiting + policies not acknowledged + that person's own
   open requests, computed once and identical on the bell and in the menu.
3. Removing Frappe's website bar must ship in the same change as the profile menu, or log
   out disappears.
4. Language saves to the user's account; light or dark saves to the device.
5. A review reads its own copy of goals and KPIs, taken when the review opened. The live
   goal is never read by the review screen, and the review's figure never appears on the
   Goals page.
6. A KPI reading is an increment with a date. The live figure changes only on approval.
   Pending amounts are displayed separately and never added to the headline.
7. A day is "late" only after the tenant's configured grace has passed. The true minutes
   are always displayed. No hard-coded grace value anywhere.
8. Someone in the subject's own reporting line cannot perform the HR steps on that review,
   and sees an explanatory note instead of a disabled control.
9. No screen shows a colleague the reason for an absence.
10. Any aggregate is suppressed when its group is under five, and the next-smallest group
    in the same table is suppressed with it.
11. A figure that cannot be trusted shows "Needs review", never 0, 0% or "Not recorded",
    and links to a page where HR can settle it.
12. Every total or rate carries the date its data runs to.
13. Home renders a skeleton within 300 ms and completes within 2.5 s on a 3G phone
    profile; the boot-time approvals check is gone.
14. Every string is wrapped for translation from Wave 1, and every screen is measured at
    390 px in Hindi before its wave is called done.

---

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1–7 | The decisions in §13 | Surbhi (1, 3, 4, 6, 7); Surbhi with the engineer (2, 5) | The design check, then Wave 1's spec |
| 8 | Hindi and Punjabi wording in the prototype is machine-drafted | Surbhi, or a native reviewer plus PP Jewellers' HR | Wave 5, and any customer demo in Hindi |
| 9 | No current-state capture was taken today (bench untouched by instruction) | Designer, when the bench is free | Nothing in this design; it would confirm the carried-over evidence |
| 10 | Focus trapping and return in the shared sheet (FR-09) is specified but not prototyped | Designer with the engineer, in Wave 1 | WCAG 2.2 AA sign-off for Wave 1 |
| 11 | Whether the owner's Home should show his own attendance at all | Surbhi | Nothing; the shift rule in Decision 6 covers it either way |

## Assumptions

- `[ASSUMPTION]` The figures carried into the prototype from the four analyst appendices
  are still true of the local copy. They were measured on 14 Sep 2026; I did not re-check
  them today.
- `[ASSUMPTION]` PP Jewellers' grace period is 15 minutes. The number is illustrative; the
  design only requires that it is read from the tenant's own Shift Type.
- `[ASSUMPTION]` Kamal's four direct reports, the store splits, the review counts and the
  policy names are invented and are tagged **Sample** on screen. 403 people, four stores,
  the 7–9 Sep absence problem and the 6 Sep check-in stop are real from the demo copy.
- `[ASSUMPTION]` The competitor picture is the Sep 2026 review's and is `[recall — verify]`.

## Handoff note

**To Surbhi:** the prototype is the thing to react to, not this document. Open it, switch
to Kamal, then to Phone — that is the half of the product the plan says was never
designed. Please answer the seven decisions in §13; four of them change words on screen
and I would rather change them once than twice.

**To the security and privacy engineer (`01c`):** three rules here need your eye. First,
the conflict-of-interest rule on the HR review list must be enforced on the server, not
only by hiding a button. Second, the scoped people search — an employee must not be able
to reach anyone outside their own team, their manager and the leadership, and the endpoint
must enforce it, not the page. Third, the small-group rules on the owner's screens travel
through drill-down and comparison lines, not just the table they first appear in.

**To the business analyst:** §14 is the list. Item 7 (no hard-coded grace) and item 6 (a
KPI reading is an increment, not a total) are the two most likely to be quietly lost in
implementation, because both are easy to build the old way.

**To the fullstack engineer:** the phone layout must use `@media`. If a container query
appears anywhere on the app wrapper, about thirty existing pop-ups break, and the layout
test does not catch it yet — add `container-type` to its banned properties in the same
commit.

**Where I disagree with the plan above me:** §10, three points. I have designed what I
believe is right and flagged each one rather than building around it quietly.
