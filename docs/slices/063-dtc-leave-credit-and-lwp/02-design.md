---
slice: 063-dtc-leave-credit-and-lwp
artifact: 02-design (the UX design; plays the part of 01b in the handoff contract)
author: hrms-ux-designer
date: 2026-10-21 (v3 the same day: credits on the 1st, Surbhi's final answers)
status: draft v3 - waiting for Surbhi's review (she reviews after everything is fixed, with the Positions page)
inputs: 01-product-brief.md to its last section ("Surbhi's FINAL answers before the rework"); 01c-security-privacy-requirements.md (PRIV-1, PRIV-2, SEC-8); 01d-half-day-addendum.md; 01e-credit-at-start-of-month-addendum.md §4-§7; definition-of-ready-done.md (prototype parity); ux-learnings.md; portal code read in worktree 060-manager-review on 21 Oct 2026
prototype: docs/slices/063-dtc-leave-credit-and-lwp/prototype-v3.html (v1 and v2 kept beside it). Not published - no Artifact tool in this run.
---

# 063 · Design v3: Paid Leaves given on the 1st, leave without pay approved by HR

**Bad news first.**

1. **v3 is the contract, and v3 is not published.** The parity rule says the product is
   built as the approved prototype draws it. I had no Artifact tool, so
   `prototype-v3.html` (invented data only) needs publishing by the lead session.
2. **In five places I drew the safer security rule, not what earlier versions or
   Surbhi's own words showed** (§12). The build and the prototype now agree. Each one
   needs her yes or no.
3. **The approver of Paid Leaves is not stated** in her final answers. Only leave without
   pay is "HR". I drew Paid Leaves going to the person's named leave approver (Sunil, as
   today). Question V1.
4. **Nothing was captured on a real screen.** The local copy has no DTC rule set.

## What changed in v3

| Change (source) | What the screens do now |
|---|---|
| **Credits given on the 1st** - A 4, B 3, C 2; the 15-day minimum stays (01e; final answers) | The card shows **Paid Leaves this month · Used · Waiting for approval · To be paid out**. Under 15 days, one line: "These count once you have attended 15 days in October. You have attended 10 so far (up to 22 Oct)." "Earned so far", "So far" chip, "figures so far / they change" and every accrual word are gone, in English and Hindi. |
| **Approved Paid Leaves count toward the 15** (E6) | Said in the rule box and in the Paid Leaves preview while someone is under 15. |
| **HR approves leave without pay; the chain is told on approval** | LWP: **Send to HR** → "Waiting for HR" → "Approved by HR". Paid Leaves: **Send to Sunil Mehra** (V1). Both: "Your managers up to Kavita Arora have been told (2 people)." |
| **5 LWP days a month**, waiting + approved, half = 0.5; when stopped: cancel the earlier waiting request or remind HR | The stop names the waiting request and says "If it is not approved yet, you can cancel it from the list to free its days, or remind HR to approve it." Words only, no button. With nothing waiting: "All of them are approved. If you need more time off, speak to Ritika (HR)." |
| **Special days: leave allowed if approved** (D6 block dropped) | The blocked-day message is gone. One calm line in the preview: "**Sun 25 Oct is a special day (Festive sale).** If this leave is approved, the day is not charged double. A day taken without approved leave is unpaid and charged double." HR's Inbox row carries "Approved, it is not charged double." |
| **Half day** - uses 0.5; the other half by punches; missed punch → attendance correction; until then absent (double on a special day); no green mark | Preview explains it all in one block (§6.3). A past approved half day with a missing punch shows a warning on the request row with **Ask HR to correct 19 Oct** (the existing correction flow). |
| **Both HR and the employee cancel** | Kept from v2. Cancelling an approved leave now tells **HR only** (safe-way choice, §12). |
| Approve/decline result for HR | Kept from v2: "Approved … Manoj's managers up to Kavita Arora have been told (2 people). Manoj has been told too." |
| HR applying for staff without a login | **Drawn again** (parity: the product will do it). The types, figures and the 5-day limit follow the chosen person. |
| Apply pop-up's own "Cancel" button | Renamed **Close**, so "Cancel" only ever means cancelling leave (v2's usability-test worry). |

---

## 1 · Frame

A DTC shop employee, on a cheap Android phone, opens **Leave** to see this month's paid
days off and to ask for a day off, in under two minutes. Second: Ritika (HR) on a laptop,
approving leave without pay in the Inbox and applying for staff with no login. Third:
the store manager, who approves Paid Leaves as today and is *told* about the rest.

| Persona | What changes | One line |
|---|---|---|
| **Employee (phone)** | Card shows the month's 4/3/2; two types; LWP "N of 5"; cancel own request; half-day guidance | Own figures only |
| **Contract / zero class** | One sentence with "N of 5"; only LWP offered | No dead end |
| **HR Manager** | Inbox row adds "N of 5", special-day line, who is told. Applies on behalf with the same rules | No new screen |
| **Leave approver (store manager)** | Approves Paid Leaves in the Inbox as today | Unchanged, plus the "who is told" line |
| **Managers up the chain** | One email + desk-bell notice on approval: who, dates, days, approved | Nothing to do |
| **CXO** | No change | Desk report |

## 2 · Count the surfaces first (P8)

Unchanged from v2: the Leave card (extended), Apply Leave (extended), Leave Applications
(extended: status, told line, Cancel, missed-punch warning), Inbox leave approvals (two
lines added), Team View (kept; type column removed - §12), Attendance correction (reused
for the half-day missed punch, not redrawn). **New pages, tabs, Inbox sections: none.**

## 3 · Evidence

- The card's credit figure is the rule set's `monthly_credits` for the class (01e §4).
  The page never types the number.
- A half-day leave uses 0.5 and the other half is measured by punches against half the
  shift; late/early are not judged; no green mark (01d, final answers).
- PRIV-1 (01c): the chain notice carries name, dates, days, "approved" - not type,
  reason, credits, class or pay. PRIV-2: no type on Team surfaces (045 AC-76).

## 4 · Benchmark

Unchanged. Not copied: rings per type, rupee forecasts, an encashment form.

## 5 · Findings

| ID | Page | Finding | Impact | Kind | Size | Severity |
|---|---|---|---|---|---|---|
| LV-1 | Leave | Empty "Leave Balance" card at DTC | High | Fix | S | P1 |
| LV-2 | Apply Leave | No type offered at DTC - nobody can apply | High | Fix | S | P1 |
| LV-3 | Apply Leave | Half day says nothing about its cost or the missed-punch rule | High | Fix | S | P2 |
| LV-4 | Apply Leave | ~~Blocked special day~~ - block dropped; replaced by the double-charge line | - | - | - | closed |
| LV-5 | Apply Leave | Success is a toast | Medium | Improve | S | P3 |
| LV-7 | Team View | "Leave Type" column is blank today | Low | Fix | S | P3 - removed (§12) |
| LV-8 | Scorecard / drawer | "No leave allocations found" at DTC | Medium | Fix | S | P3, not this slice |
| LV-10 | Leave | No employee cancel today | Medium | New | S | P2 |
| LV-11 | Leave | A half day with a missed punch silently becomes half absent | High | New | S | P2 - drawn |

## 6 · Screens and exact words

Today in the prototype: Fri 23 Oct 2026; attendance in up to 22 Oct. Days, never
"credits". Pending days are "set aside", never "held".

### 6.1 The card - "Paid Leaves - {Month}"

```
Paid Leaves - October
Class A · 4 days of Paid Leaves for October
 Paid Leaves this month 4   | Used 1.5               | Waiting for approval 1 | To be paid out 1.5
 given on 1 Oct             | 19 Oct (half), 6 Oct   | set aside for now      | with October salary
(i) 1 day is set aside for your 27 Oct request until Sunil Mehra approves or declines
    it. If it is declined or you cancel it, the day comes back.
Paid with your October salary. Nothing carries over.
How Paid Leaves work - class A
4 days of Paid Leaves on the 1st of every month. They count once you have attended 15
days that month; approved Paid Leaves days count toward the 15. Days you do not use are
paid with that month's salary. Nothing carries over.
```

| Figure | Source |
|---|---|
| Paid Leaves this month | class `monthly_credits` (4 / 3 / 2) |
| Used | approved Paid Leaves days this month; a half day is 0.5, listed "19 Oct (half)" |
| Waiting for approval | open Paid Leaves requests this month (half = 0.5) |
| To be paid out | this month − used − waiting, never below 0. Note: "with October salary"; under 15 days: "once you reach 15 days" |

**Under 15 days (Rohit, 10):** the same four figures, plus "These count once you have
attended 15 days in October. You have attended 10 so far (up to 22 Oct)." Neutral
colour. The "up to" date appears only here.

**Contract / zero class:** "Contract staff do not get monthly Paid Leaves." / "You can
still ask for Leave Without Pay, up to 5 days a month. HR approves it. You have 5 of 5
days waiting or approved in October." (Zero class: "Your leave class (No Leave) does
not get monthly Paid Leaves.")

**Loading:** skeleton within 300 ms + "Getting your Paid Leaves...". **Error:** "Your
Paid Leaves figures could not be shown just now. Your leave requests below are not
affected, and you can still apply." [Try again]

### 6.2 Apply Leave - types, preview, buttons

Options: `Paid Leaves - 1.5 days left` · `Leave Without Pay - 4 of 5 used`.
Button: **Send to Sunil Mehra** (Paid Leaves) or **Send to HR** (LWP). The other button
is **Close**. Every allowed request ends with: "{Approver} decides. Once it is approved,
your managers up to Kavita Arora are told."

| Case | Words (bold lead) | Button |
|---|---|---|
| Paid Leaves, enough left | "**Asking for 1 day of Paid Leaves.** Until Sunil Mehra decides, 1 day is set aside from your 4. The leave is paid." Under 15 adds: "and approved Paid Leaves days count toward your 15 days." | Send to Sunil Mehra |
| Paid Leaves, not enough | "**2 days asked for, but you have 0.5 days of Paid Leaves left for October.** Days already used or waiting for approval are taken off the 4. You can ask for Leave Without Pay instead (1 of 5 used this month)." + **Ask for Leave Without Pay instead** (only if LWP days are left) | none |
| LWP, within the limit | "**Asking for 1 day of Leave Without Pay.** If approved, you are not paid for this day; your Paid Leaves for October are still paid out." (under 15: "…once you reach 15 days.") + "This will be 5 of 5 days of Leave Without Pay in October." | Send to HR |
| LWP, over - something waiting | "**Only 1 day of Leave Without Pay left in October; these dates need 2 days.** Up to 5 days a month, counting requests that are waiting or approved (4 of 5 so far). Shorten the dates to 1 day. A request that is still waiting counts too: Tue 20 Oct (1 day). If it is not approved yet, you can cancel it from the list to free its days, or remind HR to approve it." | none |
| LWP, over - all approved | "**You have used all 5 days of Leave Without Pay for October.** Up to 5 days a month… All of them are approved. If you need more time off, speak to Ritika (HR)." | none |
| Previous month | "**Leave can only be asked for days in October.** September is closed. If a September day needs changing, speak to Ritika (HR)." | none |
| Past day this month | adds "This includes a past day. Past days in October can be asked for until 31 Oct." | as the type |
| HR on behalf | the same sentences in the third person ("Manoj has used all 5 days…", "it can be cancelled to free its days, or approved by HR") | Send to HR |

The limit binds HR's on-behalf requests too (OD-4).

### 6.3 Half day and special days

**Half day ticked** (amber), added under the type's lead sentence:
> **Half day:** it uses half a day of Paid Leaves. *(LWP: "it counts as 0.5 of the 5
> days.")* You must check in and check out for the other half; it is measured against
> half the shift. Arriving late or leaving early does not count against you that day,
> and there is no green mark on a half-day leave day. If a punch is missed, ask HR to
> approve an attendance correction; until then the other half counts as absent *(on a
> special day: "and, on this special day, is charged double.")*

**After the day, if a punch is missing** (on the request row, amber):
> **Your check-out for the other half of Mon 19 Oct is missing.** Until HR approves a
> correction, that half counts as absent. Ask for the correction on Attendance and HR
> will approve it. [Ask HR to correct 19 Oct]

The link opens the existing attendance correction for that date. Nothing new is built
for the correction itself.

**Special day in the dates** (amber, one line, no block):
> **Sun 25 Oct is a special day (Festive sale).** If this leave is approved, the day is
> not charged double. A day taken without approved leave is unpaid and charged double.

### 6.4 Result (in the pop-up, one Done)

> **Sent to HR**
> **Leave Without Pay · Thu 29 Oct · 1 day**
> Ritika (HR) will approve or decline it. You will see the answer here, under Leave
> Applications.
> Once it is approved, your managers up to Kavita Arora are told.
> If approved, you are not paid for this day. 5 of 5 days of Leave Without Pay are now
> waiting or approved in October.
> *Changed your mind? It can be cancelled from the list.*

Paid Leaves: "Sent to Sunil Mehra … 1 day is set aside from your Paid Leaves until Sunil
Mehra decides." Half day adds "Check in and check out for the other half as usual."
Failed send: "Not sent: the connection dropped. Nothing was saved. Your choices are
still here - try again."

### 6.5 Leave Applications - status, told line, Cancel

| Status | Badge | Under it |
|---|---|---|
| Waiting | **Waiting for HR** / **Waiting for Sunil Mehra** | [Cancel request] |
| Approved, not started | **Approved by HR** / **Approved by Sunil Mehra** | "Your managers up to Kavita Arora have been told (2 people)." [Cancel this leave] |
| Approved, started or past | same | told line + "This day has started or passed. To change it, speak to HR." |
| Approved half day, punch missing | same | the §6.3 warning and link |
| Declined / Cancelled | red / grey | - |

**Cancel a waiting request:** "**Cancel this request?** … HR will no longer see this
request. 1 day goes back on your 5-day Leave Without Pay limit for October." *(Paid
Leaves: "The 1 day set aside comes back to your Paid Leaves.")* [Keep the request]
[Cancel request] → "Request cancelled. HR has been told."

**Cancel an approved leave before its day:** "**Cancel this approved leave?** … You
will be expected at work on this day. HR is told it is cancelled. Your managers are not
sent a message about it, so if Sunil Mehra is expecting you to be away, tell him
yourself. You are paid for this day if you work it." [Keep the leave] [Cancel leave] →
"Leave cancelled. HR has been told. You are expected at work."

### 6.6 Approvers and the chain

**HR Inbox row (LWP), existing row plus three lines:**
> **Manoj Singh** · Leave Without Pay · Tue 27 Oct · **1 day**
> 1 other person in this team is away on those days
> 5 of 5 Leave Without Pay days in October, counting this one
> *(if a special day)* Tue 27 Oct is a special day. Approved, it is not charged double.
> Once it is approved, Manoj's managers up to Kavita Arora are told.
> [Approve] [Decline]

After Approve: "Approved · Leave Without Pay · Tue 27 Oct. Manoj's managers up to Kavita
Arora have been told (2 people). Manoj has been told too." After Decline: "Declined. Manoj
has been told. Managers are not told about a declined request."

**Leave approver's Inbox row (Paid Leaves):** as today, plus "Once it is approved,
Priya's managers up to Kavita Arora are told." The direct approver sees the type, as today.

**The notice to each manager in the chain** (email + desk bell, once, on approval):
> **Subject:** Priya Sharma will be away on Fri 30 Oct
> Priya Sharma's leave for Fri 30 Oct (1 day) has been approved.
> You are told because Priya is in your team. There is nothing for you to do.
> You can see your team's leave on the Team View page.

**Team View → Team Leaves This Month:** Employee · From · To · Days. No type column.

## 7 · Privacy and accessibility

The employee sees only their own figures. The reason reaches the approver and HR only
("Only the person who approves it and HR can read this. Managers are never sent it.").
The chain learns four facts (§6.6). No notice on decline or cancel. Accessibility as v2:
labels, `role="status"` previews, `alertdialog` confirms with Escape and focus on the
title, words beside every colour.

## 8 · Hindi

Every new and changed string has a Hindi machine draft in the prototype, including the
card, the 15-day line, the limit messages, the half-day block, the special-day line and
the cancel confirms. The accrual strings ("अब तक मिली", "ये अब तक के आँकड़े हैं") are
gone. **Needs a native reviewer.**

## 9 · Checks

- **Measured** (Playwright, Chrome, 38 renders): all six people at 390 and 1440 px in
  light and dark (24), every "Try" case, Manoj at 5 of 5, both cancels and results, the
  Paid Leaves form and result, HR on behalf of Manoj, Hindi card and limit, HR after
  Approve. No sideways scroll, no text under 12 px, no phone field under 16 px, no
  target under 44 px on the phone or 24 px on the desktop, no script errors. One fix on
  the way: a half-day preview said "These days are paid"; it now says "The leave is paid".
- **Frontline bar.** Ask for a day: 5 taps. Cancel: 3 taps. Fix a missed half-day punch:
  1 tap to the existing correction.
- **Red team.** At the limit with a waiting request: the way out is named. Under 15
  days: "To be paid out 4" says "once you reach 15 days", so nobody reads it as certain.
  Network drop: nothing saved, form kept. No manager above: "only HR knows".

**Usability test:** five DTC staff, own phones. (1) "How many paid days off do you have
this month, and when are they paid?" (2) "Ask for next Tuesday off." (3) "Your half day
last Monday shows a warning - what do you do?" (4) "You no longer need Friday off - undo
it." Success: 4 of 5 unaided, each under two minutes. If two read "To be paid out 4"
under 15 days as money already theirs, change its note.

## 10 · Open questions for Surbhi

| # | Question | My recommendation |
|---|---|---|
| **V1** | Who approves **Paid Leaves**? Your final answers name HR only for LWP. | **The named leave approver, as today** (drawn). If you want HR for both, the prototype changes in two words. |
| **V2** | "Remind HR to approve it" - words only, or a button? | **Words only** (drawn), as your answer said. |
| **V3** | Should the limit period be the calendar month? (still marked open in the brief) | **Yes** (drawn). |
| **V4** | Under 15 days, "To be paid out" shows the full 4 with "once you reach 15 days". Or show it only from 15 days? | **Show it with the note** (drawn): people see what is at stake. |
| §12 | The five safe-way choices | Each needs your yes or no |

Carried from v2 and still assumed accepted: U1 (only Paid Leaves days count as "used"),
U3 (Paid Leaves capped at what is left), U5 (the told line names who was actually sent
it), U7 (employee cancels until the day starts, HR after), U10 (a request across two
months counts each day in its own month), U13 (Ritika's own leave goes to her approver).
U8 and the old D6 are gone with the block.

## 11 · Not in this slice

Scorecard and drawer "No leave allocations found" at DTC (LV-8). Native date inputs show
the browser's format.

## 12 · Safe-way choices - drawn so build and prototype agree; Surbhi to confirm

| # | Where the earlier versions or her words differed | What v3 draws | Rule it follows |
|---|---|---|---|
| S1 | v2's chain notice showed **Leave type**, **Approved by Ritika (HR)** and the **job title** | Four facts only: name, dates, days, "approved". No type, no approver, no job title | 01c PRIV-1 |
| S2 | v2 sent the chain a **cancellation notice** | **None.** Cancelling an approved leave tells HR only; the employee's confirm says so and asks them to tell their manager | 01c Q6(b) unanswered; no notice until Surbhi says so |
| S3 | v2's Team table had a **Leave Type** column (blank today) | **Column removed**; type stays hidden on Team View | 01c PRIV-2, 045 AC-76 |
| S4 | v2's HR Inbox row showed the job title beside the name | **Name only** on the row | Least data for the decision |
| S5 | v2 said the reason is read by "HR" only | "Only the person who approves it and HR can read this. Managers are never sent it." - true now that Paid Leaves has a non-HR approver | 01c data inventory |

The direct approver still sees the type and the reason on the record, as today.

## Subtract pass

Removed in v3: every accrual sentence and the "So far" chip; the "not counted yet
(missing check-out)" line on the card (with credits given on the 1st, a missing
check-out matters only through the 15-day line and the half-day row, where it is now
said); the blocked-day message and its "Change the dates" link; the cancellation notice
to managers; the type and approver from the notice; the Team type column. Kept: the
under-15 line, the HR on-behalf picker (parity: the product does it).

---

## Open questions

V1-V4 and S1-S5 above, for Surbhi. From the brief: is the rule set switched on at DTC
(rehearsal first, 01e §5); does "Leave Without Pay" exist there; is Leave Encashment off.

## Assumptions

- `[ASSUMPTION]` Paid Leaves go to the named leave approver (V1).
- `[ASSUMPTION]` The chain for the three sample staff is Sunil Mehra → Kavita Arora.
- `[ASSUMPTION]` The missed-punch warning can be worked out from the attendance record
  for that day (no check-in or no check-out on a half-day leave date).
- `[ASSUMPTION]` Special days have a short name to show in brackets; if not, the line
  reads "…is a special day."
- `[ASSUMPTION]` All names, classes and numbers in v1-v3 are invented (Sample).

## Handoff note

To the business analyst: walk the parity table against **v3**, not v2. Rows that moved:
the card (01e §7, R-3 to R-12), the limit messages, the special-day line (replaces the
block), the half-day block and the missed-punch row warning, the approvers per type,
the chain notice (four facts), Team View (no type), cancel (HR told only), the Apply
button "Close". To the engineer: the card's first figure is `monthly_credits`; the
under-15 line needs days attended (Paid Leaves days included, E6). To security: S1-S5
follow your file; S2 and S4 are choices I made the safe way, not ones you required.
