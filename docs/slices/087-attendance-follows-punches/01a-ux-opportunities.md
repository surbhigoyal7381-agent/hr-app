---
slice: 087-attendance-follows-punches
artifact: 01a-ux-opportunities
author: hrms-ux-designer
date: 2026-11-20
status: draft
inputs: [Surbhi's idea of 20 Nov 2026, slice 085 docs, code on dev 2e31151f]
---

# 087 Attendance follows the punches: UX opportunities scan

**Risk tier 1** (pay, and who may change a punch). **Mode:** scan only, no prototype.

**What I read:** this worktree (`.claude/worktrees/087-attendance-follows-punches`, dev `2e31151f`): `held_day.py`, `payroll_rules_apply.py`, `payroll_reprocess.py`, `public/js/payroll_entry_reprocess.js`, `public/js/ess/portal.js` (`acDetail`), and Frappe HR's own `shift_type.py`, `employee_checkin.py`, `attendance.py`, `attendance_request.py` in `hrms/`. **What I did not do:** I did not sign in, click, or run anything. Every step count below is read from code and Frappe's docs, not timed on a screen. No login, no tenant. Web pages were read on **20 Nov 2026**.

## 1. Bad news first

**B1. "Ignore the wrong punch" does not change pay at DTC as the code stands.** `payroll_rules_apply._punches` (line 378) reads every Employee Checkin of the day with no filter on `skip_auto_attendance`. Slice 085's `held_day._day_logs` (line 278) does filter it. So the two already disagree about what a day's punches are. Case 2 fixed by "ignore the 14:00 punch" would pass the held check and still be judged on three punches by the pay engine. *Fact (both read).*

**B2. "Skipped" already means something else.** Frappe's job, when it meets a punch for a day that already has an Attendance, tries to create a second one, fails, and **sets that punch to skip** with a comment "Reason for skipping auto attendance" (`handle_attendance_exception`, `employee_checkin.py:461`). So a late punch on a marked day is probably already skipped by the system. The same flag cannot also mean "HR says this punch is wrong". *Inferred from reading the code. Not run.* ⚠ DECISION for the BA: one flag, two meanings. A second field for "ignored by HR" may be needed.

**B3. A punch stays locked once the day is marked.** Frappe refuses to change a linked punch's time until the Attendance is cancelled (`validate_time_change`, `employee_checkin.py:78`). This is why HR "has to cancel first". Adding a new punch is not blocked; editing an old one is. *Fact.*

**B4. "Recalculate" already exists, but only for pay.** The Payroll Entry has a "Reprocess Attendance" button under Tools (`payroll_entry_reprocess.js`). It shows the money change first, skips submitted slips, and is safe to click twice (`payroll_reprocess.py` header). It does not re-mark the Attendance status. HR will not look for it on a Payroll Entry when the problem is one person's day. *Fact (read).*

## 2. Today: what HR does for a late punch

Fixed starting point (all three cases): a day already has an Attendance row, and a punch arrives or is added afterwards. Stock Frappe does nothing with it (Frappe HR docs, "Employee Checkin", read 20 Nov 2026: a log added after the day was marked "does not change attendance by itself"; the fix is to cancel the Attendance). Rough count; **not clicked**:

| Day was | HR steps today | Screens | Where it goes wrong |
|---|---|---|---|
| **Absent** | 1) Find the day in the Attendance list (Desk). 2) Open it, press Cancel, confirm. Frappe unlinks the punches (`on_cancel`). 3) If the late punch was marked skipped (B2), open that Employee Checkin and untick Skip Auto Attendance. 4) Wait for the 3 to 4 minute job, or open the Shift Type and press its mark-attendance button. 5) Open the new row to check it. | 4 to 5 | Nobody tells HR the late punch arrived. Step 3 is invisible unless you know the flag. Cancelling an Absent day leaves a gap that, on some tenants, reads as Present until the job runs (`consider_unmarked_attendance_as`, from slice 085 notes). |
| **Present** | Same five steps. A Present day is only a problem if the late punch changes the hours or the late mark. | 4 to 5 | Same. HR often does not know the late mark is now wrong, so nothing prompts them. |
| **Half Day** | Same. One exception in stock: a Half Day made by a leave on the other half is updated by the job without a cancel (`get_existing_half_day_attendance`). A Half Day from low hours is an ordinary row. | 4 to 5, or 0 | HR cannot tell which kind of Half Day they hold. |
| **Held (slice 085)** | Nothing. A late **machine** punch that evens the count releases the day (`release_on_machine_punch`). Already built. | 0 | Only machine punches. Not the portal Check In, not a fix HR adds. |

**The portal route today.** The employee presses "Ask HR to fix this day". HR approves in the Inbox. Stock Attendance Request then changes the **status only**, with `db_set` on the existing row, no cancel (`attendance_request.py:170`). Hours, in and out times and punches are not touched. Slice 085 added one exception: a held day released with a typed missing time writes the hours too. So for Absent, Present and Half Day, an approved request makes the status say Present while the punches say something else. At DTC the pay engine reads the punches (inferred, not tested), so **the approval may not change pay**.

**Neither of Surbhi's cases has a fix path that touches a punch.** I searched these surfaces: `attendance_correction.py` (`raise_correction`, `raise_for_report`, `decide`), `held_day.py`, and every `Employee Checkin` hook in `hooks.py`. Only the machine, the phone app and the portal Check In create punches. HR can edit one in the Desk, but nothing links that edit to a request.

## 3. Who sees what today

- **Employee.** The day sheet draws the punches from the checkin records (`acDetail`, `portal.js:6171`) whatever the status. So an Absent day can show three punches next to the word Absent. *Inferred from code; not seen on a screen.* The employee sees no reason and no "HR is looking at this". On a Held day (085) they get a clear sentence and a Send to HR form.
- **Manager.** Per the 085 design, same sheet on a direct report's month. I did not open the manager code. A manager sees counts and times, never a reason for absence.
- **HR.** The request card shows the status change and, for held days, the punches. It does not show "the punch that arrived after this day was marked".

## 4. How competitors handle it

Honest limit: no trial account, no screenshots. Help centres only, plus search summaries. Keka's own help article returned a sign-in page and an HTTP 403, so Keka is from search snippets of its help centre.

| Product | Late or corrected punch: logs or only the status? | Evidence |
|---|---|---|
| **Frappe HR standard** | Neither, by itself. A late log does not change a marked day. Fix is cancel the Attendance, correct the log, let the job mark again. Cancelling is the reprocess. | **Read** 20 Nov 2026: docs.frappe.io/hr/employee-checkin. **Seen in code:** `employee_checkin.py:78`, `attendance.py:86` |
| **Zoho People** | **Both, by option.** Regularisation either "adds a new attendance entry without modifying existing entries" (old kept, hours added) or "replaces existing entries" (first check-in or last check-out replaced). Records update only after approval. The page does not say whether replaced entries are kept for audit. Users report wrong total hours after regularising past dates. | **Read** 20 Nov 2026: help.zoho.com attendance-regularization article; community threads (user posts, not confirmed) |
| **Keka** | **The logs.** An admin or manager opens the day's logs, picks "Regularize Logs", presses "+ Add" and enters new time entries. A second choice raises a request to exempt the day from penalty. Employees can be limited to missing swipes only. | **Read (search snippets of help.keka.com), 20 Nov 2026.** Help pages not opened (403). `[recall — verify]` on whether originals are kept |
| **greytHR** | **Punch times, edited by the approver.** The approver may correct the in and out times before approving (a third-party Freshdesk guide, not greytHR's own). greytHR adds "dirty swipes", synthetic out-swipes, to pair a missing sign-out. Not confirmed whether a late swipe re-runs processing. | **Read** 20 Nov 2026: greythr.freshdesk.com articles; third-party guide |
| **Darwinbox** | **Not found.** Search returned marketing pages only: employee raises a request for a wrong entry or missing time-out, manager approves, bulk approval from the Task Box. Nothing on logs vs status. | **Read** 20 Nov 2026: Darwinbox whitepaper and blog. I could not check this one. |

**What this says.** Two of four with evidence (Keka, Zoho's "new entry" option) add a log and keep the old ones. Frappe makes you cancel to reprocess. None of what I read shows an automatic re-judge when a machine punch arrives late; Alvoraa's 085 already does that for held days. `[recall — verify]`: Darwinbox and greytHR may have auto-reprocess I did not reach. **Scope word:** "none of what I read", not "no competitor".

## 5. Her proposal, tested against the code

| Part | Fits? | Note |
|---|---|---|
| 1. A late machine punch re-works an already-marked day | Extends `release_on_machine_punch` from Held to any status. Same hook, same guards. | Must handle B2: the late punch may already be skipped by the job. Must not touch leave days, hand-marked days, or days in a submitted slip (`is_in_final_slip`, `held_day.py:333`, already there). |
| 2. "Recalculate from punches" for HR | Pay half exists (B4). Status half does not. | **Smallest idea first:** if parts 1 and 3 exist, HR rarely needs it. Keep it only for the case "HR edited a punch in the Desk". PM to decide. |
| 3. HR approving a fix adds the missing punch, marked regularised, linked to the request | Fixes both cases and the late portal Check In. Also makes the approval change pay at DTC. | Needs a visible mark on the punch ("added by HR, request ..."). Slice 085 bars HR from editing **their own** punches; the same rule must cover approving a fix for themselves. |
| 3b. A wrong punch is set to ignored, never deleted | Right idea (the record stays). | B1 and B2 block it as built. Case 2 is better fixed by **adding the 14:40 In** than by ignoring the 14:00 Out: the break (40 min) shows, and DTC's break allowance (40 min, from the DTC memory note) applies. |

## 6. Persona ideas

Serves, in order: HR Manager, Employee, line manager. **CXO:** nothing changes. **HR:** the main change. **Employee:** sees what was added and why. One-way rule held: the manager gets no new view of the person.

| Persona | Idea | Job it serves | Evidence | Size |
|---|---|---|---|---|
| **HR Manager** | One action on the request card: "Approve and add the punch 14:40 (In)". The result line: "This day becomes Present, 8h 20m, and is paid." | Fix a day without cancel, untick, wait | Steps in section 2; Keka's "+ Add" is the same idea | M |
| **HR Manager** | When a late punch re-works a day, the day shows one line: "Changed by the 19:41 machine punch. Was Absent." | Know why a day moved | Slice 085 already writes "how, by whom" on a release | S |
| **HR Manager** | A day the system will not touch (leave, hand-marked, paid slip) says why, in words, instead of silently staying. | Trust the automation | Guards in the brief | S |
| **Employee** | The day sheet adds a line for a punch HR added: "HR added 14:40 (In) on 21 Nov, from your request." | Understand every number that touches pay | Day sheet already shows punches (`acDetail`) | S |
| **Employee** | An Absent day that has punches stops looking contradictory: the day re-works itself, or says "A punch arrived after this day was marked. HR will look at it." | Not having to know to ask | Section 3; inferred | S |
| **Frontline** | Case 1 done on a phone in two minutes: the employee names the time they really arrived, sends, and sees "HR will add it". The late portal Check In stays on record. | A real time, not an invented one | Surbhi's case 1 | S |
| **Line manager** | Nothing new. If the manager already raises for a report (`raise_for_report`), the same result line shows. No list of "late punches". | Keep the one-way rule | 085 design | none |
| **CXO** | Nothing. | n/a | n/a | none |
| **IT / DPO** | Every added or ignored punch says who, when, which request. HR cannot add or ignore their own punch. | Audit and conflict of interest | 085 doors (US-11) | S |

## 7. What not to copy

- **Zoho's "replace first check-in / last check-out".** It destroys the original, and the page does not say it is kept. Our rule stays: never delete a punch.
- **greytHR's synthetic "dirty swipes".** It invents a punch the person never made. Ours is added by a named HR person, marked as such.
- **Auto-approve** (greytHR option). A pay change with nobody's name on it.

## 8. Not in this slice (for the PM to decide)

Bulk "recalculate a team"; a "late punches" list for HR; reminders to HR; a Hindi version of the new lines; changing the portal Check In to allow a past time.

## 9. Open questions for the brief

1. **One flag, two meanings (B2).** Do we add a separate "ignored by HR" field, or reuse skip? Owner: BA, with the engineer. Blocks the spec.
2. **Should the pay engine honour "ignored"?** Today `_punches` does not. If not, part 3b does nothing at DTC. Owner: Surbhi. Blocks the design of case 2.
3. **Does the pay engine at DTC change when only the Attendance status changes?** I inferred no. Someone must test it on a copy. Owner: engineer. If yes, much of this is smaller.
4. **Which machine punches re-work a day?** Only those that arrive before pay is final, or any? Guard "days on a submitted slip" is stated; what about a draft slip? 085 refreshes a draft slip. Owner: Surbhi.
5. **Does the portal Check In at 11:15 count as a "late punch" that HR corrects, or the truth?** Case 1 says HR adds 10:30. Who vouches for 10:30: the employee, the manager, or HR alone? Owner: Surbhi. Recommendation: the employee names the time, HR decides, both are on the record.
6. **Is part 2 (the button) needed once 1 and 3 exist?** Recommendation: build 1 and 3, ask again after HR uses them.
7. **Tenant switch.** Is this on for every tenant, or per company like slice 085's hold? Owner: PM.
8. **Slice 086.** Manager bulk filing is on hold behind this. Does the manager's request carry the same added punch? Owner: PM.

## 10. Rung and subtract pass

**Rung:** new code (a hook on the existing punch insert, and a step in the existing approval). Configuration rejected: nothing in settings re-works a marked day. Standard Frappe rejected: it needs cancel, which is the pain. A new DocType rejected: Custom Fields on Employee Checkin (regularised, request link, and maybe ignored) are enough, to be confirmed by the BA.

**Subtract pass.** I dropped from my own list: a "late punches" dashboard, a timeline of every change on a day, and a separate "fix a punch" screen for HR. I kept the existing request card as the only HR screen. Part 2 is marked as possibly removable.

## 11. Next

Brief is the PM's. This scan changes nothing in the product and was not published; there is no prototype in scan mode.
