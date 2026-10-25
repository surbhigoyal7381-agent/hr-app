---
date: 2026-10-24
author: hrms-product-manager (priorities mode, UX focus)
status: recommendation — Surbhi decides. No code, no prototype, no approval to build.
inputs: [2026-10-24-ux-benchmark.md (UXB-1..15, N1-N7, 11 Sep status), product-context.md v0.1, no-over-engineering.md, 2026-10-01-kano-review.md §6b, alvoraa_portal/public/js/ess/portal.js, alvoraa_portal/*_api.py]
fits_with: 2026-10-01-kano-review.md §6b. This file does not replace that order. It adds five small portal slices to it.
---

# Portal UX priorities against competitors — 24 October 2026

**I recommend. You decide.**

## Read this first

**1. No screen fix reaches anyone until deploys refresh the portal's files (ALV-112).**
Deploys today do not update `sites/assets`, so a CSS or JavaScript change can pass every
test and still not show on dev or production. Every slice below waits on that. It is
already Gate 0 item 4 in the 1 Oct order.

**2. The biggest gaps are basics, not features.** Tiny text, 25 px buttons, "Holiday" on a
weekly off, and "Loading…" that never ends. A shop-floor worker meets these before anything
clever. Fix them first. They are cheap.

**3. Our real advantage is that we explain.** No competitor in the 87 screenshots explains
a rupee or a red mark. We already do on the payslip and the day sheet. The plan is to
make that explanation easier to reach, then say it in Hindi.

**4. I could not check which 1 Oct Gate 0 items have shipped since.** The placements
below assume that order still stands.

N5 ("Payroll Rule Set not found") is dropped. You confirmed it is local only.

---

## 1 · Ranking of UXB-1..15

Every Kano class is a **proxy**. No survey exists yet (ALV-13 is planned for late November).
Size is the UX designer's: S = days, M = one to two weeks, L = more. An engineer has not
sized any of them. **Parity** = competitors do it, we catch up. **Advantage** = none of the
12 products shows it.

| Rank | ID | What | Persona | Kano (proxy) | Demand evidence | Size | Parity / advantage | Slice |
|---|---|---|---|---|---|---|---|---|
| 1 | UXB-7 | "Weekly off", not "Holiday"; one date format (24 Oct 2026) | Frontline | Must-be | seen: Thursdays labelled "Holiday" on our screen. Confirmed: `time_api.py` already returns `weekly_off`, so this is a label change | S | Ours (a bug) | A |
| 2 | UXB-6 | Every "Loading…" ends in 10 s with plain words and **Try again**. The form keeps what was typed | Everyone | Must-be | seen: Leave page stuck. Confirmed: about 20 bare "Loading…" strings in `portal.js` | S | Ours | A |
| 3 | UXB-2 | 44 px tap targets, 16 px form fields, nothing under 12 px on a phone | Frontline | Must-be | measured: "+ Apply Leave" 25 px, fields 13 px, labels 11 px (`report3.json`) | S | Ours (our own NFR §7 rule) | A |
| 4 | UXB-5 | "Why is this month different?" on the payslip list, one line per change | Frontline, one-person HR | **Attractive** | seen-absent in all 12 products. seen: Aug ₹44,052 vs Jul ₹32,200 with no reason. **Evidence required:** how many "why was I cut" calls DTC HR gets after payday | M | **Advantage** | B |
| 5 | UXB-3 | "2 days need fixing" on Home, each opening the existing "What went wrong?" sheet | Frontline | Performance | seen: greytHR "4 exception day(s) · Regularize", Zoho "marked as absent" | S | Parity, but one tap to our inline fix is ahead | C |
| 6 | UXB-4 | Shift in plain words on the check-in card: "9:30 am – 6:30 pm · starts in 15 min · weekly off Thursday" | Frontline | Performance | seen: Deputy "Starting in 15 mins", Keka shift card | S | Parity | C |
| 7 | UXB-10 | "Today" strip: In 14 · Not in yet 3 · On leave 2. Tap a number for the names. "No check-ins yet today" instead of 19 dashes | Supervisor, one-person HR | Performance | seen: Deputy "4 on shift · 1 late", Zimyo team overview | S | Parity | D |
| 8 | UXB-9 (part) | Pending approvals at the **top** of Team View, with Approve / Decline on each | Supervisor | Performance | seen: SAP, Darwinbox, Keka put approvals first | S–M | Parity | D |
| 9 | UXB-1 | Hindi for the frontline journey, switched in the profile menu | Frontline | Performance, drifting to Must-be | read: greytHR 12 languages (help page, June 2026), Keka 6 (App Store, 24 Oct). product-context §5 already requires English–Hindi parity. No direct DTC request recorded | L | Parity alone; **advantage** combined with ranks 4–5 | E |
| 10 | UXB-11 | Check-out reminder on the card | Frontline | Performance | seen: Workday. Same as ALV-161 | M | Parity | Stays ALV-161 (1 Oct #20) |
| 11 | UXB-8 | Leave balance and "also off these days" in the leave form | Employee, manager | Performance | seen: Keka | M | Parity | Later |
| 12 | UXB-14 | One "Requests" page for shift, attendance and advance requests | Employee | Performance | seen: Zimyo "Apply for" sheet | M | Parity | Later — needs your call |
| 13 | UXB-15 | Page name in the desktop top bar; words beside desktop menu icons | HR on laptop | Performance | seen: our own top bar says "Home" everywhere | S | Ours | Page name goes in A; menu words later |
| 14 | UXB-12 | Keep a draft form through a dropped signal, send later | Frontline on 3G | Indifferent until proven | read: Keka and factoHR offline *punch*, not forms | M | Weak advantage | No — A's "keep what was typed" covers most of it |
| 15 | UXB-13 | Share a plain-words summary by the phone's share sheet | Owner on WhatsApp | Attractive **or Reverse** — unknown | No competitor seen. Owners use WhatsApp (your description) | S | Advantage | **Blocked** — privacy check first |

**11 Sep findings bundled in:** G1 (top bar says "Home"), G6 (dates), G8 (grey shadow),
H5 (past holiday card), H6 (25 px quick action), N6 (clipped day table), N7 (greeting
twice, empty Activity card) all go into slice A. TV3 (19 dashes) and TV4 (two Nehas — show
"Neha S.") go into slice D. G2, G4, PH2 stay open and unranked.

---

## 2 · Five slice candidates

Each one is a change to the existing portal. No new page frame, no new menu item, no new
record type, no new settings. Colours stay per tenant. All five are on the **new code** rung
(portal JavaScript, CSS and existing API calls). Nothing on a cheaper rung does it:
Frappe HR's desk forms are not what staff use, and there is no setting for any of this.

### A · "Readable and honest on a ₹8,000 phone" — UXB-7, 6, 2 + G1 G6 G8 H5 H6 N6 N7
- **Outcome:** a helper on a cheap Android phone can read every word, hit every button
  first time, and is never left staring at a dead screen.
- **WOW (frontline):** the signal drops while applying for leave. Instead of "Loading…"
  for ever, the form stays filled and says: *"We could not reach the office. Nothing was
  sent. [Try again]"*.
- **Size:** each part S; together S–M, engineer to size.
- **Measure:** re-run the UX designer's own phone script. Target: 0 controls under 44 px,
  0 fields under 16 px, 0 screens still on "Loading…" after 10 s. Baseline is in
  `report3.json`.
- **Against 1 Oct:** right after Gate 0 (needs ALV-112). The "Weekly off" label should ride
  with ALV-92 (Gate 0 #3) if that is not yet live, so staff see the right word the day the
  holiday list is fixed.

### B · "Why is my pay different this month?" — UXB-5
- **Outcome:** a worker sees why this month's take-home differs from last month without
  calling HR.
- **WOW (frontline):** under August's amount: *"₹11,852 more than July · 4 more paid days
  · incentive ₹6,000 · late deduction ₹548 [Why?]"*. Every line taps to the existing
  explanation.
- **How:** compare this slip's components with last month's slip, in plain arithmetic.
  No AI. No new data — the employee already sees both slips.
- **Size:** M.
- **Measure:** "why was my pay cut" questions to HR in the week after payday. Baseline
  unknown — ask DTC HR to tally one payday before we build. Target: half.
- **Against 1 Oct:** straight after ALV-90 (#12, both figures). Aim for the second DTC
  payroll. This is the slice that most sharpens our positioning.

### C · "Fix my days before payday" — UXB-3 + UXB-4
- **Outcome:** a worker sees which days need fixing and fixes each with one tap, before
  the attendance cut-off.
- **WOW (frontline):** Home says *"2 days need fixing: Tue 14 Oct, Thu 16 Oct"*. One tap
  and "What went wrong?" is already open on Tue 14. The check-in card above it says
  *"Your shift 9:30 am – 6:30 pm · starts in 15 min"*.
- **Size:** S + S.
- **Measure:** exception days still open at the attendance cut-off, per month. Baseline:
  count from DTC data first (a read-only query). Target: down by half.
- **Against 1 Oct:** ahead of ALV-161 (#20, reminders). C is the "pull" version of a
  reminder with no notifications. **If C cuts open exception days, ALV-161 may not be
  needed.** Measure before building ALV-161.

### D · "Who is in today" for the supervisor and the one-person HR — UXB-10 + UXB-9 (approvals part) + TV3 TV4
- **Outcome:** at 9:45 the supervisor knows who has not come in, and clears approvals,
  from one screen.
- **WOW (one-person HR):** Team View opens on *"In 14 · Not in yet 3 · On leave 2"* and
  *"3 requests waiting — Approve / Decline"* above everything else. Before 9:30 it says
  *"No check-ins yet today"*, not 19 dashes.
- **Privacy:** only people the user can already see in Team View. Counts and names, no
  reasons, no ranking, no "most late" list. Nothing new becomes visible.
- **Size:** S–M.
- **Measure:** requests left waiting more than 2 days. Baseline from Leave Application and
  attendance-correction dates. Target: down by half.
- **Against 1 Oct:** weeks 4–8, before ALV-21 → ALV-6. The goal-folding half of UXB-9 waits
  on your ALV-2 answer — if Performance Management is hidden for DTC, it is not needed.

### E · "Hindi for the frontline journey" — UXB-1
- **Outcome:** a Hindi-reading worker can check in, fix a missed day and read the payslip
  explanation without meeting any English.
- **WOW (frontline):** the payslip line reads *"देर से आने की कटौती ₹548 [क्यों?]"* and
  the "Why?" answer is in Hindi too. No competitor explains pay; none explains it in Hindi.
- **How:** Frappe's own translation system and the user's language setting — already
  there. `portal.js` has a `window.__` hook (line 5848) but almost no text goes through it.
  Reuse the field app's Hindi drafts. No new translation service.
- **Size:** L.
- **Hard gate:** a named native Hindi reviewer signs off every string before it is switched
  on. That is the ALV-150 lesson.
- **Measure:** share of DTC staff who choose Hindi, and whether they complete a day fix in
  Hindi without help.
- **Against 1 Oct:** after ALV-150 (Gate 0 #5). The string work can start once the reviewer
  is named. Ship after B and C, so the explanations exist to translate.

**Suggested order:** A → B → C → D → E. A, B and C fit between the end of Gate 0 and
the first ALV-21 work. None of them moves a 1 Oct item down except ALV-161, which waits on
C's number.

---

## 3 · What not to do, and why

| Do not | Seen at | Why not |
|---|---|---|
| Face recognition kiosk or selfie match | Keka, Deputy | Biometric data under DPDP. product-context §6 item 3 refuses facial analysis. DTC already has punch devices |
| A social wall, birthdays or polls at the top of Home | Keka, greytHR, HROne | Pushes the one task below the fold on a small phone |
| An AI chat box as the way in | Darwinbox | Assumes typing and English. A button and a plain sentence do the job |
| Teasing copy ("You've missed the bus 12 times") | sumHR | Guilt-trip wording. We explain the rule; we do not shame |
| A doughnut chart of salary mix | Keka | Answers nothing. "Why is it less?" is the question — that is slice B |
| A grid of 9–12 small icon tiles | Zimyo, factoHR | Small targets; icons need reading skill |
| Stock photos and illustrations | greytHR, Darwinbox | Slow on 3G, mean nothing to a low-literacy reader |
| A WhatsApp Business integration | Darwinbox, uKnowva | A new paid outside service, consent questions, and pay data leaving the product. UXB-13's share sheet is the cheap test, after the privacy check |
| Offline check-in in the web portal | Keka (Android app) | That is the field app's job. The portal keeps the form and offers Try again |
| A "most late" or "least present" list in the Today strip | — | Ranks individuals for a manager. Our refusal list forbids it |
| A full portal redesign, a new frame, a global colour scheme | — | You rejected the redesign on 26 Sep. Colours stay per tenant |
| More languages before Hindi is reviewed and used | greytHR's 12 | Each unreviewed language repeats the ALV-150 consent problem |
| Merging the three request pages now (UXB-14) | Zimyo | Closest to the redesign you rejected. Count how often each page is used first |

---

## 4 · Decisions only you can make

| # | Decision | Why it matters | Blocks | My recommendation |
|---|---|---|---|---|
| 1 | **Is the target segment Indian manufacturing, distribution and trading MSMEs, with frontline staff first?** product-context §2 still says 50–1,000-person mid-market with the HR head as the main user. I have not edited it | It decides who wins when the HR head and the shop-floor worker want different things | How A, C and E are weighed against HR-desk work | Add one line to §2 naming the MSME segment and saying frontline wins on employee screens. The HR head stays the buyer |
| 2 | **Who checks Hindi?** A person, by name, who reads Hindi natively | Unreviewed Hindi on pay and consent screens is a real harm, not polish | Slice E and ALV-150 | A DTC HR person or a paid reviewer, paid per batch |
| 3 | **Commission the privacy check for UXB-13** (sharing a summary via the phone) from hrms-security-privacy-engineer | Pay and attendance text would leave the product. ⚠ COMPLIANCE. I am not a lawyer | Whether UXB-13 can ever be a slice | Yes, but after A–C. It is cheap to check, not urgent |
| 4 | **Do these slices wait for all of Gate 0, or can A run alongside?** | A is CSS and wording only, low risk, but it needs ALV-112 to be visible | Start date of A | A runs as soon as ALV-112 is done; the rest wait for Gate 0 |
| 5 | **Keep or hide Performance Management (ALV-2)** — still open from 1 Oct | If hidden, the 30 goal cards on manager Home disappear for DTC | The goal half of UXB-9 | Unchanged from 1 Oct: hide |
| 6 | **Can we watch five DTC staff use the portal on their own phones for 15 minutes each?** | Every "easier" here is still a judgement. Five people will show us what we got wrong | Confidence in A and C | Yes, before A ships and again after |
| 7 | **Add four items to the ALV-13 survey** (see §5) | Turns these proxies into evidence | Ranking of B, D, E and UXB-13 | Yes |

---

## 5 · Survey kit — add to ALV-13 (late November)

Same method as the 1 Oct kit: functional and dysfunctional question, five answers, the
standard table, CS+ and CS−. Ask in Hindi and English. Report frontline staff, supervisors
and HR separately.

| # | Feature, as worded to staff | Ask |
|---|---|---|
| 9 | "Your payslip says in plain words why it is different from last month" | Employees, HR |
| 10 | "Your home screen shows which days need fixing, and you fix them in one tap" | Employees |
| 11 | "Your supervisor sees, each morning, who is in and who is not in yet" | Employees, supervisors (**watch for Reverse among employees**) |
| 12 | "You can send a short summary of your payslip or a day to WhatsApp yourself" | Employees, owners (only if decision 3 clears it) |

(Item 5 in the 1 Oct kit already asks about Hindi.)

---

## Thriving-workplace lens

| Lens | One line |
|---|---|
| Engagement | B and C give workers clarity about their own pay and days, and the means to act |
| Collaboration | D lets a supervisor see who is missing at the moment it matters |
| Inclusiveness | A and E are for the people we exclude today: cheap phones, low literacy, Hindi readers |
| Transparency | B shows each worker their own numbers. D shows nothing a supervisor cannot already see, and ranks nobody |

## Regulatory read

1. **Regime:** DPDP for E (the notice and consent text in Hindi) and for UXB-13. None for
   A and C. B and D show existing data to people who already see it.
2. **Whose duty:** the employer's — a Hindi notice that workers can read helps our customer
   meet its duty to give notice in a language the worker understands `[ASSUMPTION — counsel
   to confirm]`.
3. **New:** no new data is collected in any slice. No new visibility in A–E. UXB-13 would
   send data out — that is why it is blocked.
4. **Front page test:** A–E, yes. A "most late" board, no — it is on the do-not-build list.

---

## Open questions

| Question | Owner | Blocks | Class |
|---|---|---|---|
| Decisions 1–7 in §4 | Surbhi | As listed | Must know: 1, 2, 4. Should know: 3, 5, 6, 7 |
| Which Gate 0 items are now live? | Surbhi or the session that tracks YouTrack | Exact placement of A | Should know |
| How many "why was I cut" calls DTC HR takes after payday | DTC HR, via Surbhi | B's baseline | Should know |
| Exception days still open at DTC's attendance cut-off | Engineer, read-only query | C's baseline; ALV-161's need | Should know |

## Assumptions

- `[ASSUMPTION]` The 1 Oct §6b order still stands; I did not re-read YouTrack.
- `[ASSUMPTION]` App Store screenshots show each vendor's best screen. "Nobody does it"
  means nobody shows it there.
- `[ASSUMPTION]` Sizes are the UX designer's, not an engineer's.
- `[ASSUMPTION]` Slice B can use last month's slip for the same employee without a new
  permission, because the employee already sees both.
- `[ASSUMPTION]` Every Kano class above is a proxy.

## Subtract pass

Removed on this pass: a sixth slice for desktop menu labels (G2) — it serves the HR head,
not the target worker, and can wait. The offline draft queue (UXB-12) — slice A's "keep
what was typed" covers the common case. The goal-folding half of UXB-9 — it may vanish if
Performance Management is hidden. A separate brief for the check-out reminder — it is
already ALV-161 and should wait on slice C's number.
