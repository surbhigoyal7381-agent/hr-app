---
slice: 085-held-odd-punch-days
artifact: 01a-ux-opportunities
author: hrms-ux-designer
date: 2026-11-19
status: draft
---

# 085 Held days: UX opportunities scan

Mode: scan only, no prototype. Tier is the PM's call; I rate it Tier 1 (it changes pay).
Requirement is Surbhi's, 19 Nov 2026, taken as decided.

## What I read, and what I did not

- **Read (proven):** worktree `085-held-odd-punch-days`, HEAD `fd658eff`. `public/js/ess/portal.js` (`acPaint` 5891, the day sheet 6168-6225, `TR_FLAGS` 15282), `payroll_fields.py` (held fields, 41-61), `attendance_correction.py` (odd-count comments 867, 1862). Slice 084 brief, first 60 lines.
- **Not done:** no browser capture, no login. Screens below are described from code, not seen running. Not checked: the Daily Attendance Workings report, `attendance_onload` HR confirm fields, and `acLoad` server payload. Say so before the PM relies on those rows.
- **Competitors:** one web search, 19 Nov 2026, vendor pages **read as search summaries only**, no screenshots seen. Darwinbox and greytHR: nothing found. Everything below marked `[recall - verify]` is memory.

## 1. Current screens and gaps (read in code)

| # | Screen | What it does today | Gap for held days |
|---|---|---|---|
| C1 | Employee month, `acPaint` | Tiles "Missing punches" (amber), row tag "Missing punch" | No state called "held". A one-punch day shows as Absent or short, which is a verdict, not "waiting for you". No tile for "held days: pay waiting" |
| C2 | Day sheet, `x.missing_punch` | "One punch never registered... what the correction below is for" | Good words, but says nothing about pay. A held day must say "No pay for this day until it is fixed" |
| C3 | Same sheet, `acForm` | Employee raises one correction (`raise_correction`). Manager files only for a direct report, and only if `on_behalf_enabled` | Form is generic (reason, explanation). For a missing punch it should ask only for the missing time |
| C4 | Team page `TR_FLAGS` | "No clock-out" is the worst flag, red | Flags the person, not an owed action. No "you can fix this for them" in the row |
| C5 | Grace | Hidden Server Script: 3 requests a month, Sales Executives exempt | Employee is refused with a message nobody can trace. Moves to a company setting (slice 084 left the cap out) |
| C6 | HR | HR corrects any day | No list of "still held before payroll" found in what I read. Not checked in the report |

## 2. Competitors, whole products

| Product | Employee | Manager / HR | Payroll link | Evidence |
|---|---|---|---|---|
| Keka | Self-regularise; shows on attendance screen once approved | HR regularises on behalf; bulk regularisation for missing in/out, wrong status, device failure | not found | read, help pages via search, 19 Nov |
| Zoho People | Request, manager or HR approves | HR caps requests per month and how far back | not found | read, search summary, 19 Nov |
| factoHR | Request with reason, date, corrected times | Manager then HR, per policy | not found | read, glossary, 19 Nov |
| greytHR, Darwinbox | not found | not found | not found | searched, nothing |

**Honest gap:** I found no source that makes a missing punch a *held* state that pays nothing. Competitors mostly mark Absent or "Missing punch" and let people regularise. A held state is therefore our own design, not something to copy. I did not find how any rival turns a regularisation into a pay change.

## 3. Persona by persona ideas

| Persona | Idea | Job | Evidence | Size |
|---|---|---|---|---|
| Employee | Held is its own colour-plus-word state: "Held: one punch. Not paid yet." Tap opens a one-field form: "What time did you leave?" with the pay line above it | Know where I stand, fix it fast | C1, C2 | M |
| Employee | After approval, the day sheet says what changed: "Held, now Present. Pay restored for 12 Nov" | Understand every number | principle 76 (approved vs pending, named beside) | S |
| Employee (frontline, phone) | Held days on Home "Needs you": "2 days held. Fix now" | 2-minute task on a phone | pattern "Needs you" strip | S |
| Manager | In "Exceptions before lists": "Ravi: 1 punch on 12 Nov. Ask HR to fix" with the missing time field inline | One action | C4, pattern 49 | M |
| HR | One "Held days" list before payroll: person, day, how many punches, who asked, Release or Decline. Bulk select | See who is not ready | C6 | M |
| HR | Month-end warning: "14 days still held. They will pay nothing" | Not be surprised | requirement | S |
| HR | Company settings: held switch + monthly request cap, each saying who it affects | Config once, no scripts | C5, slice 084 | S |
| CXO | Nothing new. One aggregate: held days across the company, no names | Trust the pay number | scope rule | S |

## 4. Not to copy / traps

- Do not show the reason a person was away, only presence. Held rows show punches, never why.
- No countdown or nagging loop on the employee. One strip, one count.
- Do not count held days in the "Absent" tile. Absent and held are different words.
- Do not let a manager's filing change the employee's view of who asked (name the filer).
- Backfill: 166 Grace days change at once. Employees will see Present become Held and Absent become Held. Needs a notice, not a silent flip.

## 5. Decisions and risks

- **⚠ DECISION 1 (owner: Surbhi/PM): wording for Grace days that were Present (80 three/five-punch days).** Going from Present to Held takes pay away retroactively for those employees. Needs a plain notice and a say on whether payroll already run is touched.
- **⚠ DECISION 2 (owner: PM/BA): who approves an employee's own request.** HR only, or the manager? The requirement lists "HR directly, own request, manager on behalf" but not who approves the request.
- **⚠ DECISION 3 (owner: PM): the monthly cap.** Slice 084 left the cap out of scope; this slice moves it to a setting. Confirm 085 owns it, or the two overlap.
- **Risk:** the held word must replace "Absent" on the employee month, the team list, the HR report and payroll slips. One word, everywhere (anti-pattern MA2, seen three times).
- **Risk:** held on DTC engine ATT-06 and on Grace Attendance rows must show the same words. DTC's pay is in Excel, so "pays nothing" is not visible in the portal there. Not checked.

## 6. Not in this slice (for the PM to decide)

Reminders by email, a "held for N days" ageing colour, mobile push, manager bulk-filing.
