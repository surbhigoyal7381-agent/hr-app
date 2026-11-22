---
slice: 087-attendance-follows-punches
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-11-20
status: draft
inputs: [01a-ux-opportunities.md, 07-devops-inputs.md section 1, 085 product brief, held_day.py, payroll_rules_apply.py]
---

# 087 Attendance follows the punches

**Risk tier: 1** (it changes pay and who may add a punch). **Rung: 3 (Custom Fields on Employee Checkin) plus 4 (code inside the approval that already exists).** Recommendation only. Surbhi decides.

## Bottom line

1. **Build a smaller slice than the three-part proposal.** Build part 3 (HR approves a fix and the punch is added) plus the "ignore a wrong punch" step it needs. Do not build part 2 (the button). Hold part 1 (late machine punch re-works any day) for a second slice, after we count how often it happens.
2. **Bad news first, in bold: case (a) is not fixed by adding a punch alone.** The employee pressed Check In at 11:15. If HR adds 10:30, the day has 10:30, 11:15 and the evening out: three punches, odd, held again. The 11:15 punch must be set aside. And **the DTC pay engine does not look at "ignored" today** (`_punches` in `payroll_rules_apply.py`, line 378, has no filter). So ignoring must be built into the engine's read, or case (a) changes nothing at DTC.
3. **Linked bug ALV-410 is the same fault** and is fixed by the same step (decision 3).
4. Order: 087 first, then 086. 086's "Back from a break" choice becomes a form for the same added punch.

## What I checked, and what I could not

- **Read (proven):** worktree `087-attendance-follows-punches`: `01a`, `07-devops-inputs.md`, the 085 brief, `held_day.py` (lines 270-460), `payroll_rules_apply.py` lines 365-390.
- **Could not run:** `git rev-list --left-right --count dev...origin/dev`. This session has no shell. I am told the worktree is at `2e31151f` and `origin/dev` is at `7de630df` with 085 commits. **So `held_day.py` may have changed since I read it.** Before anyone writes "X is not built" from this brief, re-check on `origin/dev`.
- **Not checked:** whether the request form already carries a corrected time for a day that is not held; the compose queue layout; anything run on a screen. I did not look at Grace, because Grace has no pay rule set (085 brief).
- **One more fact from code:** `punch_dedupe.py` also sets `skip_auto_attendance` (for repeat scans). So that flag already has **three** meanings: Frappe's "day already made", the repeat-scan flag, and now "HR says wrong". It cannot be reused for the third. See decision 1b.

## 1. Job to be done

**Persona: HR Manager** (main), **Employee**, **line manager**. CXO: nothing changes.

> "As an HR manager, when someone's real arrival or return is not in the punches, I want to approve the fix once and have the day, the punches and the pay all agree, so I never cancel an attendance and rebuild it by hand."

> "As a shop-floor employee who forgot to punch, I want to say the real time and see HR add it, so I am paid for the hours I worked."

## 2. Current pain (a story, not a number)

I have no count of how often this happens. **Evidence required:** fix requests per month, and late punches per day (OPS-5). The story, from Surbhi, 20 Nov: a punch arrives after the day was marked, and HR must cancel the Attendance, then redo several steps. The UX scan counts about 4 to 5 screens, read from code, not timed. Worse, an approved fix today changes only the **status** of the day; the punches stay as they were. At a company with a pay rule set, the engine reads the punches, so the approval may not change pay (ALV-410, confirmed from code, not run).

## 3. Competitors (whole products)

Source: the UX scan, help pages read 20 Nov 2026. No trial accounts, no screenshots. Keka's own help page returned a 403, so Keka is from search snippets.

| Capability | Frappe HR | Zoho People | Keka | greytHR | Us |
|---|---|---|---|---|---|
| Fix adds a log, original kept | No. Cancel the Attendance, then correct the log (read, docs.frappe.io, 20 Nov) | Yes, by option "add new entry" (read, help.zoho.com) | Yes, "+ Add" in Regularize Logs (read, snippets) | Approver edits in/out times (read, third-party guide) | Not today |
| Fix replaces the original | No | Yes, by option (page does not say whether kept) | Not found | Yes, edit | **No, never** |
| Late log re-works a marked day by itself | No | Not found | Not found | Not confirmed | 085 does it for held days only |
| Employee names the real time, HR decides | Status only | Yes (read) | Yes (read) | Yes (read) | Yes for held days; part of this slice for other days |

Darwinbox: nothing usable found. **Scope:** "I found none", not "none exists". `[recall — verify]` for greytHR and Darwinbox auto-reprocess.

**What we will NOT do that others do:** (a) replace or edit the original punch (Zoho option, greytHR) because the record of what the machine said must stay; (b) invent punches ("dirty swipes", greytHR) because nobody made them; (c) auto-approve. This makes us better for the DPO and for the employee who is later asked "who changed my hours?".

## 3a. Three ways, and could we not build it?

| Way | What | Verdict |
|---|---|---|
| Conventional | Zoho style: HR edits or replaces times on the day | Rejected. Loses the original; Frappe also blocks editing a linked punch (`employee_checkin.py:78`) |
| **Better (recommended)** | Approval adds one punch, marked regularised and linked to the request; a wrong punch is set aside with a reason; the day is re-judged by the same function 085 already uses (`worked_out`) | Smallest thing that fixes both cases and ALV-410 |
| Reimagined | Never store a status; always compute the day live from the punches | Rejected. Rewrites attendance for every report and slip |
| Build nothing? | HR keeps cancelling. The "Confirmed Out Time" shortcut fixes only a missing OUT, not case (a) or (b) | Rejected |

## 4. Kano class and demand

- **Must-be for the payroll owner, `proxy`.** Frappe makes you cancel; Keka and Zoho let you add a log; being forced to cancel and rebuild is the kind of tedium that fills support queues. Right pay earns no praise, wrong pay causes anger.
- **Demand I actually have (seen):** one founder statement (20 Nov), the 085 session's bug ALV-410, and DTC's own odd-punch days (slice 085). **No survey, no customer count.** I will not say "high demand".
- **Would change:** if the count of fix requests per month is tiny, class falls to Indifferent and the slice shrinks to ALV-410 alone.

## 5. Persona enhancements through the portal

| Persona | How the portal helps | Job | In this slice? | Why |
|---|---|---|---|---|
| HR Manager | Request card button "Approve and add the punch". One line shows the result: "This day becomes Present, 8h 20m, paid." | Fix a day without cancel and rebuild | **Yes** | The WOW |
| HR Manager | A day the system will not touch says why ("on a paid slip") | Trust | **Yes, as one sentence** | Guards need words or they look like bugs |
| HR Manager | "Recalculate from punches" button | Redo a day | **No** | Decision 2 |
| Employee | Day sheet line: "HR added 14:40 (In) on 21 Nov, from your request." Set-aside punch shown struck through with the reason | Understand each figure touching pay | **Yes** | Day sheet already draws punches (`acDetail`, `portal.js`) |
| Frontline employee, phone | Case (a) in two minutes: name the real time, send | A true time, not an invented one | **Yes** | Needs the request to carry a time, 360 px wide |
| Line manager | Files for a report (exists); same result line | Keep the one-way rule | **Later, in 086** | 086 owns manager filing |
| CXO | Nothing | n/a | **No** | |
| DPO / IT | Every added or set-aside punch says who, when, which request. HR cannot approve a fix for their own day | Audit | **Yes** | Counsel's logging line; 085 already bars own-punch editing |

## 6. The WOW

HR opens a request: "Raju, 21 Nov. Back from break at 14:40." Under the Approve button: **"Approve and add 14:40 (In). This day becomes Present, 8h 20m, and is paid."** Raju's day sheet then reads: **"HR added 14:40 (In) on 21 Nov, from your request."** In case (a) the sheet shows "11:15 In, set aside by HR" next to "10:30 In, added by HR". No cancelling anything.

## 7. Thin slice

- **Needed to validate this now:** on approval, add the punch (marked regularised, linked to the request); for case (a), set the wrong punch aside with a reason; re-judge that one day with `worked_out`; show the result line; the pay engine reads the same set of punches the day was judged on.
- **Needed before it can ship:** the guards (leave day, a day on a submitted slip, a deliberate hand-marked day) each with a plain sentence, and each tested to fail first; HR cannot approve a fix for their own day; draft slip refreshed for that one employee-month (same call 085 uses); a dry run on a copy showing no other day changes.
- **Worth doing later:** part 1 (late machine punch re-works any day), after OPS-5 counts; manager filing (086).
- **Not doing:** part 2 button, bulk recalculate, a late-punches list, reminders, a backfill patch (OPS-6), editing or deleting a punch, past-time Check In on the portal.

## 8. Run-side reality

DevOps section 1: no new container, no new schedule, no new app. The heavy risks (the race with Frappe's auto-attendance job, a slip refresh per punch, queue workers) belong to **part 1**. They are why I hold it back. Part 3 runs inside one human approval, so a refresh is once per approval, not once per punch. OPS-7 (how to tell a hand-marked day from a machine-made one) also bites only on part 1. If Surbhi chooses part 1 inside 087, OPS-1 to OPS-5 become requirements and the slice roughly doubles.

## 9. Success measures

| Measure | Baseline | Target | Instrument |
|---|---|---|---|
| Screens HR uses to fix a late-punch day (efficiency) | About 4 to 5, read from code, not timed | 1 (the approval) | Walk through on dev, then ask HR |
| Approved fixes after which the pay engine still holds or misprices the day (quality, the ALV-410 fault) | Unknown, measure first | 0 | Compare engine verdict to the result line on every approval, on ppj.dev |
| Fixes needing HR to open the Desk or cancel an Attendance (adoption) | Unknown, measure first | 0 | HR's own count for the first month |
| Fix requests per month (demand) | Unknown, measure first | Recorded | Count of requests that added a punch |

## 10. Risks (red-team)

- **Double count.** 085's `release_by_hr` passes the typed time as an "extra" into `worked_out`. Once the punch really exists, `worked_out` would count it twice. The engineer must drop the extra. Needs a test.
- **Two readers disagree.** `release_on_machine_punch` counts with `_punches` (no skip filter) but judges with `_day_logs` (skip filter). Setting a punch aside widens that gap. Both must read one list.
- **Changing `_punches` changes DTC counts for unrelated days.** If it filters on `skip_auto_attendance`, repeat scans are dropped too. Recommend: filter only on the new "set aside by HR" field. Dry run first.
- **A day already on a submitted slip.** Refuse, in words. A submitted slip is never changed.
- **Employee leaves or manager changes mid-flow.** A request for a left employee should refuse, not add a punch. Needs a test.
- **Wrong fix approved.** The set-aside punch is never deleted, so it can be reversed by HR adding a note and a new fix. The record shows both.
- **10x data:** one approval is one day. Fine. Part 1 is where 10x hurts.
- **Support tickets:** "why did my 11:15 disappear?" Answered by the day sheet line.

## 11. Thriving-workplace lens

- **Engagement:** agency. The employee says the real time and sees it honoured.
- **Collaboration:** HR and employee see the same record; manager sees nothing new.
- **Inclusiveness:** phone, 360 px, Hindi. The new lines need a Hindi check (UX). Contract and agency staff use the same path.
- **Transparency:** every added or set-aside punch names who and why, visible to the employee. No new manager view of a person.

## 12. Regulatory read

1. **Regime:** employment and wage records; DPDP accuracy duty. No AI, no emotion or behaviour monitoring.
2. **Whose obligation:** the employer's (DTC, Grace). We help them keep an honest, correctable record and show who changed it.
3. **New:** a punch the machine did not make, created by a named HR person on the employee's word, and a machine punch set aside. Each is a data change by a person, logged.
4. **Honest downside:** "HR added a punch that was never scanned." Defensible only if it is plainly marked, linked to a request, and never passed off as a machine read. ⚠ COMPLIANCE: whether an HR-added punch is acceptable as attendance evidence at DTC and Grace. I am not a lawyer. **Owner: Surbhi with counsel. Blocks switching on at a customer.**

## ⚠ DECISIONS for Surbhi

**1. The UX open questions that are hers**

| | Question | My recommendation |
|---|---|---|
| 1a (UX Q2) | Should the DTC pay engine honour "set aside" punches? | **Yes.** Without it case (a) changes nothing at DTC. Make the engine skip only punches carrying the new field, and run a dry run on ppj.dev to prove no other day moves. |
| 1b (UX Q1) | One flag or two? | **Two.** Keep Frappe's `skip_auto_attendance` set on the set-aside punch (so Frappe's job and 085 skip it) and add a field that says "set aside by HR, request X". The new field is what the pay engine reads. |
| 1c (UX Q5) | Who vouches for 10:30 in case (a)? | **The employee names the time; HR approves; both names are on the record.** HR never approves a fix for their own day (another HR person does). The 11:15 portal punch stays on record. |
| 1d (UX Q7) | Per company, or on for all? | **On for all companies.** Adding a punch happens only when a human approves, so nothing runs by itself. Part 1 (the automatic one) should get a per-company switch like 085's, when it is built. |
| 1e (UX Q4) | Draft slip after a fix? | **Refresh that one draft slip**, as 085 does. Submitted slip: refuse in words. |
| 1f (UX Q8) | Does 086's manager request carry the same punch? | **Yes.** Same approval, decided by HR. The manager gets no new view. |

**2. Is part 2 (Recalculate from punches) needed once 1 and 3 exist?**
Recommendation: **No. Drop it.** The only case left is HR editing a punch in the Desk, which I have no sign is common. The Payroll Entry already has "Reprocess Attendance" for pay (UX B4). Ask again after HR has used the approval for a month.

**3. Is ALV-410 fixed inside this slice by part 3?**
Recommendation: **Yes.** It is the same code: the approval writes the punch the engine needs. The alternative (setting "Confirmed Out Time") fixes only a missing OUT and leaves case (b) broken. Grace is unaffected (no rule set).

**4. Part 1 inside 087 or after?**
Recommendation: **after**, as its own slice. It carries the race, queue and slip-volume risks (OPS-1 to 5, OPS-7) and I have no count of late punches. Part 3 stands alone and fixes both of her cases.

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| Q1 | Decisions 1 to 4 above | Surbhi | Design gate |
| Q2 | Does the request form already carry a corrected time for a non-held day (case a)? Name the field | BA, with engineer | The spec |
| Q3 | Does DTC pay change when only the status changes (UX Q3)? Test on a copy | Engineer | Size of the slice |
| Q4 | Is an HR-added punch acceptable as evidence at DTC and Grace? | Surbhi with counsel | Switch-on |
| Q5 | Is the checkout current? Run `git rev-list --left-right --count dev...origin/dev` | Any session with a shell | Every "not built" claim here |

## Assumptions

- [ASSUMPTION] The pay engine at DTC prices by punches, not by the Attendance status (UX inferred; not tested).
- [ASSUMPTION] Custom Fields on Employee Checkin are enough; no new DocType.
- [ASSUMPTION] HR already approves requests in the Inbox with the existing role checks.
- [ASSUMPTION] `held_day.py` on `origin/dev` 7de630df is the same in the parts I read.

## Kill criteria

Stop and rethink if: (1) the dry run shows making the engine skip set-aside punches changes any day other than the test days; (2) an approval cannot be shown to give one count and one verdict across the day sheet, the Attendance row and the engine; (3) counsel says an HR-added punch cannot stand as evidence; (4) the count of fix requests is so small that ALV-410 alone is enough.

## Subtract pass

Removed: part 2 button, bulk recalculate, late-punches list, reminders, Hindi build, a backfill. Held back: part 1. I removed nothing else; every remaining item is needed for case (a) or (b) or the guards.

---

## Notes from the slice 085 session (20 Nov 2026) - for the spec and the engineer

- That session reports that Surbhi put ALV-410 into 087 there, as a subtask of ALV-409. **Not yet confirmed at this slice's own gate.**
- The punch added on approval must cover a missing IN and a missing OUT, so `judge` sees an even count.
- `release_on_machine_punch` fires only for machine accounts (`files_as_machine`), so an HR-added punch should not trigger a second release. Prove it in a test.
- The F1/R4 punch checks in `field_app_access.py` refuse a punch on the actor's own record and outside their companies. Insert as the approver, or through a path that respects those checks.
- `release_by_hr` passes the typed time as an "extra" into `worked_out`. If a real punch is added too, it would be counted twice.
- ppj.dev test rows from 19 Nov (device_id alv085-test) are in use by testers. Do not touch them.

## Decisions (Surbhi, 20 Nov 2026)

"build it, go with all recommendations"

1. The DTC pay engine honours set-aside punches, using a new field next to the skip flag (not `skip_auto_attendance`), with a dry run first.
2. The employee names the corrected time; HR approves; HR never approves a fix for their own day.
3. On for every company: a person approves each fix.
4. Part 2 (the Recalculate button) is dropped. Part 1 (a late machine punch re-works any day) is held for a later slice.
5. ALV-410 is fixed inside 087: on approval, the missing punch (IN or OUT) is added.

Still open: the ⚠ COMPLIANCE question whether counsel accepts an HR-added punch as evidence (Surbhi with counsel).

Gate passed: build.
