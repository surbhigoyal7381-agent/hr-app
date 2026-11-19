---
slice: 085-held-odd-punch-days
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-11-19
status: draft
inputs: [01-product-brief.md (incl. Brief gate), 01a-ux-opportunities.md, 07-devops-inputs.md]
---

# 085 Held days: UX design

**Risk tier 1** (pay). **Rung:** reuse. One new status word, one tag, one tile, one sentence, one filter value, two settings. No new screen except the settings card. **Prototype:** `docs/slices/085-held-odd-punch-days/prototype-v1.html` (copy in `/Users/mac/hrlocal-data/prototypes/085-held-odd-punch-days/`). **Not published: this run had no Artifact tool, so the lead session must publish it.**

**Checked:** `acPaint`, `acRow`, `acDetail` in `public/js/ess/portal.js` (5891-6240, this worktree). **Not done:** no browser capture, no login, no measurement of the real page; the prototype is drawn, not the product. Parity table in section 6.

## 1. Who, and what changes for others
Employee (phone first, shift staff) on a day with a missing punch. Serves: Employee, HR Manager, line manager. **CXO:** nothing changes. **HR:** one new filter value and one sentence on the request. **Employee:** the day is named "Held" and says what to do, instead of looking Absent or Present with no reason. One-way rule: the manager gets no new view of the person; they see the punch count, never a reason.

## 2. The three rules, shown once
1. **One word: "Held".** Amber chip with an icon and the word. Never red (the day is not wrong, it is waiting). The old "Missing punch" tag and tile are replaced by Held when the switch is on, so one idea never has two names.
2. **Say the pay effect in the same breath**: "Not paid until fixed."
3. **Ask only for the missing time.** No reason, no explanation box on a held day.

## 3. Screens (words are final unless marked)
**Employee month** (`acPaint`): banner "2 days are Held. Not paid until fixed. Tap a held day and send the missing time to HR." Tile "Held days" (amber) replaces "Missing punches". Row tag "Held"; after sending, a second tag "Sent to HR". When none: "No held days. Every day this month is paid."

**Day sheet** (the existing inline detail, `acDetail`):
- One punch: **"Held. One punch on this day."** The punch is shown. **"Not paid until fixed."** "HR looks at held days at the end of the month, before pay." Field **"What time did you leave?"** (or "arrive", if the one punch is an Out). Button **"Send to HR"** (manager: "Send to HR for Rohit").
- Three or five punches: "Three punches on this day. One punch is missing, so nobody can tell which time is right." Field "What time was the missing punch?" and a choice In / Out.
- Sent: "Sent to HR at 17:40 by you. The day stays Held and is not paid until HR decides." No button (no second send).
- Released by HR: green, **"Held, now Present. Pay restored."** "HR approved the time 18:30. This day is paid again and your salary slip is updated." Row tag shows "Present" plus "Was held, pay restored".
- Released by a late machine punch: same line plus "The missing punch arrived from the machine at 18:41, so the day released itself." (DevOps OPS-2.)
- Declined: back to Held, the decline reason shown (today's behaviour, not changed).
- Hindi (machine draft, native review needed): Held = "रोका गया"; the key sentences are in the prototype's हिं switch.

**Manager:** same sheet on a direct report's month, same form, through today's `raise_for_report` route. If the manager route is off or the day is not theirs, today's existing sentences stay. No team-wide held list, no ranking.

**HR request card (existing `decide`):** adds the Held tag, the punches, "the missing punch was 18:30" and one grey line: "If you approve: this day becomes Present, 9h 28m, and is paid on the slip." Buttons "Approve: day becomes Present", "Decline: stays Held". Held days nobody has asked about are not in this queue.

**Register and slip:** the existing status filter gains the value Held (amber). The slip shows a line "Held days, not paid: 2", and, if any, "12 Nov, 17 Nov. Paid when HR releases them; this slip updates by itself."

**Settings, one card per company** (HR Manager only):
- Switch **"Hold days with a missing punch"**. Beside it, who it affects ("everyone in Grace Drinks"), what it does, and a live count before saving. The Save button carries the effect: **"Save for Grace Drinks: 166 days will be held"** (learned pattern, slice 078). Off: "days already Held stay Held until HR releases them."
- **"Requests a person can raise each month"**, empty = no limit. Says who it affects, that **held days never count**, and the exact sentence the employee reads when over: "You have used your 3 requests this month. Held days do not count. For another day, ask HR."
- **Exempt roles** as tags with a "Change roles" button (Sales Executive for Grace), the chosen-list pattern.
- After save: "This replaces the old hidden rule of 3 requests a month."

## 4. States and the phone
Loading: skeleton in 300 ms (nfr-budget 2); a failed send keeps the typed time and says "Not sent. Your time is saved on this phone. Try again." (a timeout says "It may have gone through" and checks first, learning from slice 070). Empty: "No held days". No permission: no form, a sentence saying whose job it is. Targets 44 px, field 16 px, 360 px wide, nothing sideways; at 200% text the three tags wrap under the date. A team of 400 sees only their own direct reports' held days when they open a person, so no list grows. Backfill (November, Grace) and the HR list of the 80 names are outside the screens.

## 5. Privacy and accessibility
Employee sees their own days. Manager sees "Held" and the punch times of a direct report, never a reason for absence. HR sees all. No personal data in errors. Colour is never alone: icon plus word. The release is announced in a status region. Focus returns to the day row after send.

## 6. Parity table (prototype vs code)
| Prototype shows | Code today | Same? |
|---|---|---|
| Inline day detail | `acToggle` / `acDetail` | Same |
| Tile "Held days" and tag "Held" | "Missing punches" tile, "Missing punch" tag | **New, needs her yes** |
| Short form, time only | `acForm`, reason and explanation | **Different, needs her yes** (⚠ 1) |
| Settings card with two settings | none (site defaults today) | New |

## ⚠ Decisions
1. **⚠ DECISION (Surbhi): drop the reason box on a held day.** I recommend yes: the missing time is the evidence. Risk: HR loses a free-text note. Owner: Surbhi.
2. **⚠ DECISION (Surbhi, BA): who picks Present or Half day on release.** I drew it automatic from the corrected time against the shift, HR sees the result before approving. Her words say "full or half". If HR must choose, the approve button splits in two. Blocks the spec.
3. **⚠ DECISION (Surbhi): switch off with held days open.** I drew "they stay Held". The alternative, auto-release to Present, silently pays.
4. **⚠ DECISION (Surbhi): the date employees are told.** "Before pay" has no date on screen. I did not invent one. A date per company would be a third setting; I recommend no.
5. **⚠ DECISION: DTC backfill.** Brief says "confirm at the design gate". DTC's pay is in Excel; the portal would show Held but not drive pay. Owner: Surbhi.
6. The 084 window question stays open (held days exempt?). I recommend exempt, or an old held day can never be paid.

## 7. Not in this slice
Home strip "2 days Held", reminders, a held-days list for HR, month-end warning, manager bulk filing, CXO total.

## 8. Subtract pass
Removed: the manager's held list, an ageing colour, a reason box, a second approval screen, a date setting, a separate Held report. Kept nothing new beyond the list in the rung line.

## 9. Usability test (High impact)
Five shift staff on a 360 px phone. Task: "Your pay is short a day. Find out why and fix it." Success: under 2 minutes, correct time sent, can say whether the day is paid. Redesign if two read "Held" as a punishment or cannot say what happens next.

## 10. For the business analyst
Acceptance criteria: the word "Held" is identical on month page, sheet, team view, register and slip; one punch and 3 or 5 punches each get their own sentence; a held day never offers the reason box; limit never blocks a held day; Sales Executives exempt; settings sentences name the audience; Save button shows the count; release shows the green line on employee, and the slip changes for that employee only; a late machine punch releases the day by itself; 360 px and 200% text pass; an existing "Missing punch" label is gone when the switch is on.

---

## Design gate: Surbhi's answers (19 Nov 2026), decided: GO WITH THIS DESIGN (prototype v1)

- **D2:** automatic. The corrected time, measured against the shift, decides Present or Half Day.
- **D5:** Grace only. No DTC backfill. The switch is still per company, and DTC can turn it on later.
- **D1, D3, D4, D6** were not answered separately. "Go with this design" accepts them **as drawn**:
  - D1: no reason box on a held day;
  - D3: days already held stay Held when the switch is turned off;
  - D4: no "fix by" date shown;
  - D6: held days are exempt from the 084 days-back window (the designer's recommendation).
