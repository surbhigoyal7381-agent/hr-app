---
slice: 089-manager-profile-edits
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-11-22
status: draft, for Surbhi's decision at the brief gate
risk tier: 1 (who can change what, personal data, a leaving date that stops pay)
inputs: 01a-ux-opportunities.md, 07-devops-inputs.md §1, product-context.md, no-over-engineering.md, definition-of-ready-done.md, employee_field_rights.py
---

# 089 · A manager tells payroll "she left", from the portal

**What I read:** worktree `.claude/worktrees/089-manager-profile-edits`, branch `slice/089-manager-profile-edits`, based on origin/dev c9d702f0 (as given to me). **I could not run `git rev-list` to check the checkout is current** (no shell in this run). Every "does not exist" below is limited to the files I name. Labels: **proven** = read in the file named; **inferred** = my reasoning; **not checked** = I did not look.

## Bad news first

1. **The people who confirm may not be allowed to save "Left".** **Proven:** `employee_field_rights.py` line 96 says `LEVEL_2_WRITERS = ("HR User", "HR Manager", "System Manager")`. "Payroll team" is not in it. **Inferred** from the ALV-266 notes: every Employee field not on `SELF_EDITABLE` (status and relieving date are not) sits at permission level 2, so a Payroll-team-only login would have its change refused or put back. **Not checked:** whether the DTC Payroll team users also hold HR User. This must be settled before any build (Q1).
2. **"Payroll team" is a DTC site role, found nowhere in the repo** (grep of the worktree: only ALV-328 slice docs name it). On Grace, PPJ and new tenants there may be nobody to confirm a notice. Q1 covers this too.
3. **"Set to Left" fires many hooks** (DevOps §1: field-phone block, manager scope, own-record, cache). ERPNext's own Employee code was **not read**. A dry run on a copy is a must before main (OPS-1).
4. **Demand evidence is one sentence from Surbhi, not data.** No customer survey, no ticket count, no count of late leavers. See §4.

## 1 · Job to be done

*"As a store manager, when someone on my team stops coming, I want to tell payroll from my phone in under a minute, so pay does not run for a person who has gone."*

Persona: **line manager (frontline supervisor)**. The person who confirms is **payroll or HR**. For the other two: **Employee** sees a plain line if they are reported (never changed silently); **CXO**: no change, nothing here is an aggregate. Administrator chooses what managers see and change.

## 2 · Current pain

No numbers. A story, **told by Surbhi, not measured**: at DTC stores the manager learns first that someone left. There is no HR at the store. Payroll hears late, by call or message. **Proven in code (searched code only, not Desk):** the portal has no "report a leaver" action, and `ACTION_MATRIX` in `team_api.py` has none. **Proven:** a manager cannot change a report's record at all (ALV-266 refuses it).

## 3 · Competitive analysis

Honest limit: only Infor, Workday and Oracle were read (by the UX scan, 22 Nov 2026). **I did not verify Keka, Zoho People, greytHR, Darwinbox, BambooHR, or Frappe HR's own manager screens.** I have not rechecked Infor, Workday or Oracle beyond the UX scan's links.

| Capability | What others do | Label | What we do |
|---|---|---|---|
| Manager starts an exit for a report | Infor: manager starts a resignation on the person's behalf, notice goes to the HR administrator. Workday (Waterloo guide): a delegate starts the termination. Oracle: managers start terminations after the employee resigned | read, 22 Nov 2026 (via 01a) | Manager sends a notice. Payroll confirms. Same shape |
| Same, in Keka, Zoho People, greytHR, Darwinbox, BambooHR | most let a manager start an exit and route to HR | `[recall — verify]` | not claimed |
| Frappe HR standard | Employee Separation exists in Desk, for HR | not checked in source this run | Not reused: it is a heavy Desk process, and a store manager never opens Desk |
| Manager sees or edits a report's profile | varies | not checked | Org ticks what managers see and change; both lists start empty |

**What we deliberately will NOT do:** a reason-for-leaving box (the manager's screen would invite a judgement about a person, and the code refuses to record it today); a status change that lands on the manager's tap (one tap would stop someone's pay); a full HR profile for managers (only what the org ticks). That makes us safer for the least powerful person: the one being reported.

## 3a · Three ways

- **Conventional:** a full exit workflow (notice period, exit interview, asset checklist, approvals). Weeks. Rejected: most of it nobody asked for.
- **Better:** a "Report left" button in Team, one date, a to-do for the confirmer. **I recommend this.**
- **Reimagined:** the store manager's WhatsApp message becomes the notice, read by AI. Rejected: AI is not needed when a date picker does it, and the product refuses AI that decides about a person.
- **Could we not build it?** The smaller move is a phone call, which is today's pain. No cheaper rung solves "payroll hears late".

**Rung:** customisation and new code, no new DocType, no new app. Rejected below it: configuration alone cannot give a manager an action; standard Employee Separation is a Desk process. Rejected above it: a new DocType adds a table, permissions, migrate and retention (DevOps OPS-2).

## 4 · Kano class and demand

- **Leaver report: Must-be for a tenant with stores and no HR, Performance elsewhere. Class is a proxy, not a survey.** Evidence I have: Surbhi's account of DTC (**seen**: her statement, 22 Nov 2026). Three vendors I read ship the manager-starts shape (**read**, 22 Nov 2026), which supports Must-be only weakly. No complaint, ticket or lost deal counted.
- **Manager can see profile fields: Performance (proxy).** Overlaps the 078 mini profile, which already shows eleven ticked work facts.
- **Manager can change profile fields: Indifferent to Reverse risk (proxy).** Staff may not want a manager changing their personal phone or address. No one has asked for it in evidence I hold. See Q3.
- **Evidence that would change this:** a count of DTC leavers reported late, and what a late report cost. A survey kit is not written; I can write one on request.

## 5 · Persona enhancements (from 01a ideas A to F)

| Persona | Idea | In this slice? | Why |
|---|---|---|---|
| Store manager (frontline, phone) | A. "Report that someone left": date picker, one button, plain after-message | **Yes. This is the slice.** | The job |
| Payroll / HR (Desk) | B. A to-do with who, last day, who reported, when; Confirm through the normal Employee save; a decline goes back in words | **Yes** | Without it the notice goes nowhere |
| Administrator | C. Two tag lists in Organisation Settings: "Managers can see" and "Managers can change", both empty by default | **Yes**, reusing the 078 card | She decided this |
| Employee | D. A line on their own page: "Your manager reported a last working day of 30 Nov. Payroll has not confirmed it yet. Not right? Tell HR." | **Yes, small** | Never be surprised by a change to pay. **Needs a security view**: it shows the employee a manager's report |
| Employee | E. "Changed by your manager on 22 Nov" on My profile | **Yes, only if "can change" ships** | The Version row exists |
| Store manager | F. "Can see" fields reuse the 078 mini profile | **Yes** | One component |
| Manager | Undo after sending; history page | **Later** | Confirmer can decline |
| All | Hindi words for the new screens | **Before store use, not code** | Native review needed |
| CXO | none | **No** | Nothing aggregate |
| Anyone | Notice period, exit interview, asset checklist, bulk leavers, push to employee | **No** | Not asked for |

## 6 · The WOW

On the report's row in Team, on a phone, the manager taps **"Left? Tell payroll"**. One screen: "Last working day" (date, today by default) and a green button **"Tell payroll that Ravi left"**. After: **"Sent to payroll on 22 Nov. Ravi shows as working until they confirm."** When payroll confirms in Desk, Ravi leaves the team list and the manager sees "Payroll confirmed: last day 30 Nov". Under a minute, no Desk, no call.

## 7 · Thin slice

**Needed to validate now:** the Team action, the notice reaching the confirmer, the confirm in Desk, the "reported, not confirmed" line for manager and employee.
**Needed before it ships:** the confirmer question (Q1) answered; the dry run on a copy; Hindi words reviewed; the Administrator card with both lists empty by default; server-side checks that only a direct report can be reported.
**Later:** undo, history, other reported changes (transfer, shift).
**Not doing:** reason for leaving, notice period, exit interview, asset checklist, instant Left, bulk, AI, new roles, new DocType, reminder job, push notification.

**Recommendation on size:** my 8 to 11 day estimate to Surbhi stands, but it holds two outcomes: the leaver report and "manager can see or change fields". The leaver report stands alone. **If the design gate runs long, ship the leaver report with "see" only, and drop "change" until a tenant asks.** The "change" half is where the privacy questions are. For "change", I propose a closed list that is a subset of `SELF_EDITABLE` (not the whole list), and `NEVER` fields (pay, bank, IDs, date of birth) untouched. Note from the ALV-266 notes: `MANAGER_EDITABLE` only works for self-edit fields, and it is a code constant today, so turning it into an Organisation Settings list is real work, not a free switch.

## 8 · Run-side reality (DevOps §1)

Run cost about zero: no new container, job, service or nginx change (inferred, not measured). Real costs: Left hooks need a dry run (OPS-1); one query set for a manager's 50 reports, not one per report (OPS-5); one settings field means a small migrate. DevOps says it should not ship alone with 078's field-rights gaps open. This does not change the size, but it adds a gate before main.

## 9 · Success criteria

| Measure | Baseline | Target | Instrument |
|---|---|---|---|
| Days from last working day to payroll confirmation (lagging, efficiency) | baseline unknown, measure first from DTC's recent leavers | fewer days, target set after baseline | notice date vs Left date vs relieving date |
| Share of leavers at DTC stores reported through the portal (adoption) | 0 | most, number set after baseline | notices sent / Employees set to Left |
| Notices confirmed or declined within 2 working days (quality) | not measured | set with payroll | open to-do age |
| Pay slips run for a person after their last day (business impact) | unknown, measure first | fewer | slip date vs relieving date |

No login or page-view measures.

## 10 · Risks, red-teamed

- **P1 if missed:** a manager reports the wrong person or in anger. Mitigation: it is only a request; payroll confirms; the screen says so; the employee sees it. **Employee leaves mid-flow:** if HR sets Left first, the open notice closes on its own (to define in spec). **Manager changes mid-flow:** the notice stays with the confirmer.
- **A direct report with their own reports** is set Left: what happens to their Reports To is not checked (DevOps). Decide before build.
- **Confirmer cannot save:** see Bad news 1.
- **Slow nightly slip job after a leaver:** five leavers once rolled back a whole Grace batch silently. Dry run must include the nightly job.
- **Manager who is also HR:** cannot be the only confirmer of their own report's exit.
- **Support tickets:** "I reported it, why is he still on the list?" Answer is in the after-message and the line on the row.
- **Cheapest way to find out first:** ask DTC payroll to walk the Desk confirm on a copy, and read what the user's roles can open.

## Thriving-workplace lens

- **Engagement:** no effect, except that a leaver's colleagues are not paid late or wrongly.
- **Collaboration:** yes. The store's knowledge reaches payroll at the moment it matters.
- **Inclusiveness:** phone-first, Hindi needed before store use; agency staff and those with no login are covered because the manager acts, not the employee.
- **Transparency:** the employee sees a manager's report about them. Nothing is ranked or inferred. No reason for leaving is collected.

## Regulatory read (not a lawyer)

1. **Regime:** DPDP (personal data of staff), employment law around ending employment. `⚠ COMPLIANCE`: counsel's joiner-form clocks and the 087 advice are the nearest rulings; none covers a leaver notice.
2. **Whose duty:** the employer's. We help it keep an accurate record and avoid paying a leaver.
3. **New:** a manager can write about a report; a manager can see more of a report's record; a notice about a person is stored. Each is a compliance event for the security engineer. Retention of the notice is **not decided** (Q4).
4. **Honest downside:** on a front page, "managers can edit their staff's personal details" would be hard to defend unless staff are told. The leaver notice is easy to defend because a human confirms it.

## Subtract pass

Removed: a "my reports who left" history page, an undo button, a reminder job, a notification queue, an employee push, a new DocType, a reason box, and a new role. Removed from the default: "can change" personal fields (lists start empty). Nothing else could go and still meet her decision.

## Open questions

| # | Question | Owner | Blocks | My recommendation |
|---|---|---|---|---|
| Q1 **must know** | Who confirms a notice? Today only HR User, HR Manager or System Manager can save status or relieving date (proven). DTC's "Payroll team" is not in that list. | Surbhi | Whole slice | One Organisation Settings value, "who confirms leaver notices" (a role), default HR Manager. At DTC set it to the role payroll holds, **and** confirm those users hold HR User, or decide to widen the list. Widening to Payroll team gives them every employee field, so say yes on purpose |
| Q2 **must know** | How is the confirmer told? | Surbhi, engineer | Design | A to-do per user holding the role, pointing at the Employee, plus a note on the Employee timeline. Not a new record. **Not checked:** the exact Frappe mechanism for a role-wide to-do |
| Q3 **should know** | May a manager change a report's personal phone or address at all? | Surbhi, security engineer | The "change" half | Start with "see" only, or a subset of two fields |
| Q4 **should know** | How long is a notice kept, and is it erased with the Employee record? | counsel via Surbhi | Release | Follow the employee-record clock |
| Q5 **should know** | A report who has their own reports: what happens to their Reports To? | Surbhi, DevOps dry run | Build | Do nothing automatic; show HR a warning |
| Q6 **nice** | Competitor checks for Keka, Zoho, greytHR, Darwinbox, BambooHR | PM, on request | Nothing | Fine to skip |

## Assumptions

- `[ASSUMPTION]` Status and relieving date are at permission level 2 today (from ALV-266 notes, not read in the Desk permission table).
- `[ASSUMPTION]` DTC leavers are mostly staff with no login or cheap phones; the manager does the reporting.
- `[ASSUMPTION]` Managers are direct managers by Reports To, as in `team_api`.
- `[ASSUMPTION]` 8 to 11 days holds with one confirmer mechanism and no new DocType.

## Kill criteria

Stop if: (a) the confirmers cannot save Left without a role change Surbhi will not accept; (b) the dry run shows Left half-applying or blocking on a leaver with a field phone, login or reports; (c) DTC payroll says they would rather hear by call than by a to-do; (d) counsel says a stored notice needs a retention clock we cannot meet.

## Surbhi's decisions, 22 Nov 2026

**Brief gate: BUILD, with all recommendations.**

1. **Who confirms a leaver notice:** one setting holding a role name, defaulting to HR Manager. At DTC both "Payroll team" users (raj.kumar, rama.pandey) also hold HR User, so they can save Left today. Read on production, read only, 22 Nov 2026 (proven).
2. **How the confirmer is told:** a ToDo for each enabled user who holds that role.
3. **A report's personal phone and address:** managers may SEE them only, never change them.
4. **How long a leaver notice is kept:** open, for counsel.
5. **A leaver's own reports' Reports To:** decided by the dry run.

The fallback stands: if design runs long, ship the leaver report with "see" only and drop "change".
