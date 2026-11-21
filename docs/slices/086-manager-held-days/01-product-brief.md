---
slice: 086-manager-held-days
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-11-20
status: draft
inputs: [01a-ux-opportunities.md, 07-devops-inputs.md §1, 085 product brief, founder request 20 Nov 2026]
---

# 086 A manager finds held days and files the missing times in one go

**Risk tier: 1** (it files requests that release pay, and it touches who may act). **Rung: 4, a small amount of new code** on the existing "Whole team" page. Recommendation only. Surbhi decides.

## Bottom line

1. **Build it, thin.** Add a real "Held" filter to the "Whole team" page, a time box on each held row, and one "Send to HR" bar. No new page, no new menu entry, no new DocType.
2. **Bad news first, in bold: the "Whole team" page cannot fix a held day today.** Its "Ask HR to fix" button asks for a reason, not the missing time (UX scan, code reading). The filter and the send bar are the whole slice.
3. **Good news: the hard part is already built.** `raise_for_report` (`attendance_correction.py` line 2342) already takes `missing_time` and `missing_log`, refuses anyone who is not a direct report, and creates a request HR must decide. The new code is a wrapper that takes a list and calls it once per day.
4. **Three decisions are Surbhi's** (section 8). One of them conflicts with her own wording.

## What I checked, and what I could not

- **Read (proven):** worktree `086-manager-held-days`; `raise_for_report` lines 2342-2427; `validate_missing_time` in `held_day.py` line 240; the UX scan, DevOps §1 and the 085 brief.
- **Could not run:** `git rev-list --left-right --count dev...origin/dev`. This session has no shell. The UX scan and DevOps both say the worktree sits at `2e31151f`, equal to `origin/dev` when they fetched. I did not re-check, so I cannot say how far behind it is today.
- **Where I looked for "does it already exist":** `team_days`, `raise_for_report`, `held_day.py` and the 085 brief, through the UX and DevOps notes. I did not grep `hrms/` for a stock bulk-request screen; I did not check Frappe HR standard at all.
- **Found:** `validate_missing_time` only checks that the day is Held, is one day, and that in/out is named. **I read no check that the time is inside the shift window or not in the future.** That is a gap for decision (2). [engineer to confirm]
- **Not checked:** whether HR's approval releases a Held day when the request has no time (the old "Ask HR to fix" path). It probably does not.

## 1. Job to be done

**Persona: Line manager.** HR Manager reviews; Employee is the person whose day it is. CXO sees nothing.

> "As a supervisor, when my people forgot to punch out last week, I want to see all their held days on one screen and give each missing time once, so nobody loses pay and I am not opening ten month pages."

- **HR Manager:** gets requests that say who vouched for the time, each decided one by one, as today.
- **Employee:** sees on the day sheet that a time was sent for them and that HR will decide (085 already shows who sent a request; wording for the manager case needs a check).

## 2. Current pain (numbers where I have them)

- DTC, 1-16 Nov (Surbhi's count): **182 one-punch and 173 three/five-punch held days, 355 in all.** About 76 are double scans 3-10 minutes apart.
- Fixing 10 held days today is about **50 taps and 10 page reloads** (UX estimate from the code, not timed).
- I have no count of how many of the 355 a manager, as opposed to the employee, would fix. **Evidence required.**

## 3. Competitors (whole products)

Source: UX scan, web searches on 20 Nov 2026, search summaries and help-page titles only. Nothing seen running.

| Capability | Keka | Zoho People | greytHR | Frappe HR standard | Us today |
|---|---|---|---|---|---|
| Employee raises a regularisation | Yes (read, 20 Nov) | Yes (read) | Not read | Attendance Request exists | Yes |
| Manager raises for a team in bulk | **Yes.** Date range, select many, apply. Skips approval (read, 20 Nov) | Approve only; no bulk raise found | "Override team attendance in bulk" listed (read, exact steps not) | Not checked | One report, one day at a time |
| Missing punch is a held, unpaid-until-fixed state | Not found | Not found | Not found | Not checked | Yes, from 085 |
| Review by HR of each manager request | Bypassed in bulk | Yes | Not read | Not checked | Yes |

Darwinbox, CatalystOne: not searched. I found nothing, which is not the same as "they have none."

**What we deliberately will NOT do that Keka does:** let the bulk action skip HR's decision, and let one status or one time be stamped on many people. Pay is at stake; a pile approved without looking defeats the hold. Keka's own help page tells admins to confirm each discrepancy is genuine, which is our rule built into the screen.

## 3a. Three ways, and could we not build it?

| Way | What | Verdict |
|---|---|---|
| Conventional | Keka-style: tick people, apply one time or status | Rejected. One invented time for many people |
| **Better (recommended)** | Held chip, one time box per held day, a list-taking call that files one-day requests, result per day | Smallest thing that meets the founder's sentence |
| Reimagined | Manager inbox with reminders, ageing and suggested times from the shift | Rejected. Not asked for; suggested times drift toward guessing |
| Build nothing? | Managers keep using the month page | Rejected: 50 taps for 10 days. But a **cheaper rung** is worth one test: file the held chip alone (filter only), no bulk. See kill criteria |

**Cost ladder.** Already there: team list, filters, `raise_for_report`, the held form. Configuration: none can add a time box. Customisation: no. **New code, small:** one filter value, one row control, one wrapper. New DocType or app: not needed.

## 4. Kano class and demand

- **Performance, `proxy`.** Managers compare vendors on how quickly they can fix attendance; Keka sells this. Not Must-be: nobody loses a deal for lack of it, because the one-by-one path exists. Not Attractive: Keka has bulk. **It becomes Attractive only because HR still decides** (our difference).
- **Demand (seen):** one source, the founder's request of 20 Nov, plus DTC's 355 held days. **No manager has asked for it by name to me. No survey.** This is one founder and one tenant's numbers.
- **Evidence that would change this:** DTC managers saying they already file from the month page without trouble, or HR saying held days are mostly fixed by employees themselves.

## 5. Persona enhancements through the portal

| Persona | Idea | In this slice? | Why |
|---|---|---|---|
| Line manager | "Held" chip with a count, following the real **Held status** | **Yes** | The founder's "filter the held days" |
| Line manager | Time box (and In/Out for 3 or 5 punches) on each held row, one "Send N to HR" bar | **Yes** | The founder's "bulk request" |
| Line manager | Result per day after sending: "8 sent. 2 not sent: 12 Nov for Ravi, already requested" | **Yes** | No silent partial success |
| Line manager | The day's real punches beside the box ("Punch 09:02. Shift ends 18:00") | **Yes** | Evidence next to the guess; it is the main brake on made-up times |
| HR manager | Each request reads "Filed by X for N days in one go" | **Yes, one line of text** | Context to decide; `raise_for_report` already stamps the name |
| HR manager | Amber flag on a time outside the shift or in the future | **Yes if cheap** (a refusal at filing is the cheaper form) | Catches made-up times |
| Line manager | "Two scans 4 minutes apart" label on double scans | **Later** | The engine may already fold them [not checked] |
| HR manager | Bulk approval | **No** | Rejected in 085 |
| Employee | Day sheet line "Sakshi sent 18:30 for you. HR will decide" | **Check, then yes** | Employee must see a time given in their name |
| Frontline employee, phone | No change | **No** | Out of scope |
| CXO | A company "held days open" figure | **No** | Not needed; no names |
| Anyone | Reminders, ageing colours, manager league table | **No** | Watch features (product-context §6) |

## 6. The WOW

A supervisor opens **Attendance, Whole team, Held (9)**. Nine cards, each one a person and a day, each with the real punches and one time box. Under the list a bar:

> **"9 days ready. HR will review each one. Your name goes on all of them. [ Send 9 to HR ]"**

She types nine times in about a minute, taps once, and sees: **"9 sent to HR."** Before, it was 50 taps and 10 reloads.

## 7. Thin slice

**Needed to validate now (one outcome: a manager files missing times for direct reports in one pass):**
- A "Held" chip on the Whole team page, following the Held status, filtered on the server before the punch read (DevOps OPS-39).
- A time box per held row, In/Out when 3 or 5 punches, no pre-filled value (a grey hint at most).
- One call that takes a list, a cap per call, one savepoint per day, and a per-day result (OPS-40, OPS-41). The call goes through `raise_for_report`, so every existing check stays.
- Refuse a duplicate for the same person and day (OPS-44).

**Needed before it can ship:**
- A confirm once, in words, before sending.
- Refuse a time in the future or outside the shift window, if `validate_missing_time` does not already (engineer to say).
- The lost-answer guard from 085 (AC-30) applied to the bulk call.

**Worth doing later:** double-scan label, amber flag, employee's day-sheet line if the wording check fails.
**Not doing:** bulk approval, one time for many, auto-approval for small differences, reminders, a new page, a new setting, a CXO figure, a per-manager count.

**Out of scope:** any day that is not Held; any person who is not covered by decision (1); a change to the monthly limit (held-day requests and HR-filed ones never count against it; that stays).

**Subtract pass.** Removed from the UX scan's list: double-scan label, amber flag as a separate feature, per-manager count, default-open Held chip. Removed from my own first draft: a "copy the shift end time" shortcut (it invites guessing). Nothing else.

## 8. Decisions for Surbhi

**⚠ DECISION (1): "All of their reporting employees": direct reports only, or the whole line?**
- **Recommendation: direct reports only.** This is your own rule of 17 Oct ("direct reports only"), and `raise_for_report` already refuses skip-level staff. UX and DevOps both recommend it. The page can still **show** the whole line where the ALV-328 tick allows it, with the time box hidden on rows that are not direct.
- **Conflict, stated plainly:** your sentence says "all of their reporting employees." If you mean the whole line, this reverses the 17 Oct rule, so it needs your explicit yes, and a change to who may act, which is Tier 1.
- Why it matters: for a skip-level person, the direct manager is the one who knows if the punch was really missed.

**⚠ DECISION (2): A time per person per day, or one time for many?**
- **Recommendation: one time per person per day.** No "apply 18:30 to all." Two people never leave at the same minute. One shared time is how a pile of made-up times gets into pay.
- Cost of saying yes to a shared time: HR sees many requests with an identical time and cannot tell a guess from a fact.

**⚠ DECISION (3): The cap per bulk action.**
- **Recommendation: 50 days per send.** DevOps estimate (not measured): 50-100 ms an insert, so 50 rows is 3-5 s in one request. The monthly limit does not bound held-day requests, so this cap is the only bound. A manager with more sends twice.
- If you want a daily cap per manager, that is a number for you to set.

## 9. Success measures

| Measure | Baseline | Target | Instrument |
|---|---|---|---|
| Held days still open at payroll cut-off, by tenant (leading, from 085) | 166 on day one at Grace; DTC 355 for 1-16 Nov | Down to those HR chose to leave | Count of Held rows at cut-off |
| Held days filed by a manager in a bulk send, as a share of manager-filed held days (adoption) | Unknown, measure first | Most manager-filed held days by the second month | Request note "in one go" vs single |
| Requests HR declines because of the time (quality) | Unknown, measure first | Not higher than for employee-filed ones | Decline count by filer type |
| Time from a held day appearing to its request being sent (efficiency) | Unknown, measure first | Shorter than the month before | Row creation to request creation |

No logins or page views.

## 10. Thriving-workplace lens

- **Engagement:** agency for the manager; clarity for the employee. Small.
- **Collaboration:** a manager's knowledge of what happened reaches HR at the moment it matters.
- **Inclusiveness:** supervisors on cheap phones: a card list, a 16px time box 44px tall, a fixed send bar; not designed yet. Hindi wording needs a check.
- **Transparency:** the employee is told a time was given for them. **Hard limit kept:** no per-manager forgetting count, no ranking of who forgets most.

## 11. Regulatory read

1. **Regime:** employment and wage law (the request releases pay). DPDP: no new data kinds; managers see punches they could already see.
2. **Whose obligation:** the employer's. We help them keep a record of who vouched for each time, which helps them in a wage dispute.
3. **New:** a manager can file for many days in one action. Not new visibility, not an automated decision; HR still decides each one.
4. **Honest downside:** a manager invents times to help their people, and HR approves them without looking. Mitigated, not removed: no blanket time, punches beside the box, the manager's name on every request, HR reviewing one by one. I am not a lawyer. If decision (1) goes to "whole line", ⚠ COMPLIANCE: who is accountable for a time given by someone two levels away. Owner: Surbhi with counsel. Blocks that option only.

## 12. Risks (red-team)

- **Made-up times** (above). Cheapest early test: ask HR at DTC how many of today's manager-filed times they decline.
- **Partial failure:** 3 of 10 fail. Show the per-day result; never "all done" without a count.
- **Double click files twice:** HR's queue doubles. Needs the duplicate refusal tested.
- **Lost answer:** the 085 guard must cover the bulk call.
- **ALV-404 (open):** on a log-type shift one OUT punch gives Absent, so some days will not appear under Held until fixed.
- **Chip and status disagree:** today's "No clock-out" chip is punch-based; the new chip follows the Held status. Both would show on one page. **The engineer must say how they are told apart or merged.**
- **A manager leaves or changes mid-flow:** the request keeps the name stamped at filing; `raise_for_report` checks the direct-report link at filing time only. [not checked what happens at approval]
- **At 10x:** HR at DTC reads about 13,000 rows for a month (DevOps estimate); the Held filter must run before the punch read.
- **Cost moves to HR:** each approval re-saves one slip, inline. Not changed by this slice; measure it, do not add bulk approval to hide it.
- **Support tickets likely:** "my day is still held" (it is waiting for HR), "why was my time refused."
- **Test data:** ppj.dev held days of 19 Nov are used by testers; do not change them.

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| D1 | Direct reports only, or the whole line? | Surbhi | Who gets the time box |
| D2 | One time per person per day? | Surbhi | The row design |
| D3 | Cap per send: 50? | Surbhi | The call's limit |
| Q4 | Does `validate_missing_time` or the request refuse a future time or one outside the shift window? | Engineer | The "refuse the impossible" item |
| Q5 | Does HR approval release a Held day whose request has no time? | Engineer | Whether the old "Ask HR to fix" button should be hidden on Held rows |
| Q6 | How are the old "No clock-out" chip and the new Held chip told apart? | UX and engineer | Chip wording |
| Q7 | Does ALV-328's tick change what the team page shows? | Engineer | Decision (1)'s "show the whole line" half |

## Assumptions

- [ASSUMPTION] The worktree equals `origin/dev` at `2e31151f`; I could not run git to re-check.
- [ASSUMPTION] One request insert takes 50-100 ms (DevOps estimate; not measured).
- [ASSUMPTION] A manager's pending request does not stop the employee filing their own time.
- [ASSUMPTION] The "filed by X for N days" line can be added to the existing note with no new field.
- [ASSUMPTION] Kano class is a `proxy`, not a survey.

## Kill criteria

Stop and rethink if: (1) on a copy with DTC-size data, the Held filter makes `team_days` slower than 500 ms p95, or a 50-day send takes over 10 s; (2) a test proves a manager can file for a person outside decision (1)'s scope; (3) HR at DTC says manager-filed times are mostly guesses they cannot check; (4) fewer than a handful of managers use the bulk bar in the first month, in which case keep only the Held filter and drop the bar.

---

## Decisions (Surbhi, 20 Nov 2026)

"build it, go with all three recommendations. yes the only file the request to the HR for regularizing with an optional box of entering reason."

1. **Scope:** show the whole reporting line where the ALV-328 tick allows it; a manager FILES only for direct reports (17 Oct rule kept).
2. **Times:** one time per person per day. No blanket time.
3. **Cap:** 50 days per send.
4. **Added:** the manager only files the request to HR for regularising, with an **optional** reason box. HR decides each request.

Gate passed: build.

---

## Update, 21 Nov 2026: the DTC daily routine, and counsel's two conditions

**Status: revised proposal, needs Surbhi's yes. Risk tier: 1 (unchanged). Rung: 4, small new code (unchanged).** Recommendation only. Sections 1 to 12 above are kept as history. Where this section differs, this section wins.

### What I read for this update (and what I could not)

- **Read (proven):** `punch_fix.py` `send` (line 348) in the 087 worktree; the end of 087's `02-functional-spec.md` (AC-101 to AC-107, Surbhi's five decisions); this brief; `01b-ux-design.md`.
- **Could not check:** git state (this session has no shell, so no `rev-list` count), the real 086 folder in the 087 worktree (it is not there; this file lives in the 086 worktree), how many DTC held-day staff have a login, and whether `raise_for_report` on the 087 branch already carries AC-102 and AC-104 (the spec says it will; I did not read that code).
- **A correction to the way the request was framed:** 087's `punch_fix.send` is the **employee's own send, own record only** (its own docstring; AC-72). A manager cannot call it. **The manager's path stays `raise_for_report`**, which 087 already changes (a reason required, the Confirm flag set). So 086 reuses 087's send path in the sense that matters (same rules, same reason, same Confirm), but through `raise_for_report`, not `send`. No new send path is built.

### The DTC routine, as Surbhi describes it (seen: her words, 21 Nov)

Every day, each manager sends HR a regularisation request for all their reporting staff. Many of those staff do not file for themselves. So the manager is the person who knows what happened, and the daily send is HR's input. Today this is outside the product. The product gives the manager no single place for it.

### The slice, in one sentence

**Each day, a manager opens one page that lists only the held days of their direct reports that have no request yet, types the missing time and a reason for each, and sends them to HR in one go.**

### What changes from the 20 Nov design

| Part | 20 Nov | Now | Why |
|---|---|---|---|
| Which rows the page shows | Held days, in three kinds (needs a time, waiting for HR, not yours to send) | **Only held days with no request yet.** The other two kinds are gone | Surbhi's rule. It also deletes the "Waiting" and skip-level row designs |
| Whose rows | Direct reports file; the whole line shown where the ALV-328 tick allows | **Direct reports only, shown and filed.** Skip-level rows are not on this page | One rule instead of two. The 17 Oct rule stays. Removes open questions UX-2 and Q7 |
| The day | A period, with a Held chip | **One day at a time**, defaulting to the latest day that has held days; the period filter stays for catching up [ASSUMPTION] | Matches the daily routine |
| Reason | Optional shared note per send | **Required, one box on each row** (ALV-418) | Counsel: a reason on every request. One shared reason copied to many people would be the blanket text we refused for times |
| After sending | Row turns into "Waiting for HR" and stays | **Row leaves the list.** A banner says "N of M sent"; the sent days are listed in it | A day with a request no longer qualifies for the page |
| Employee's part | Day sheet shows a request was sent (check wording) | **Depends on counsel's answer, below** | ALV-419 |

### The gating question, and the design that works both ways

**⚠ COMPLIANCE, blocks release of this slice: does a manager-filed held-day request count as "the request itself", or must the employee press Confirm? Owner: Surbhi to counsel. I am not a lawyer.**

Why it clashes: ALV-419 says any request filed by someone other than the employee waits for that employee's Confirm in the app, and a person with no login can never confirm. The people this page is for are mostly the people who do not use the app. Under the strict reading the page would create requests that wait for ever.

| | **Answer A: manager's request counts** | **Answer B: Confirm applies** |
|---|---|---|
| What the server does | `raise_for_report` on a **held day** does not set the Confirm flag. HR decides as in 085 | The flag is set, as 087 already does (AC-104). Nothing new to build |
| Employee sees | A notice on the day sheet: "Your manager sent 18:30 for you. HR will decide." With Not right (needs their reason) so they can object | Confirm and Not right (087 AC-106) |
| Page change | None | **A row for a person with no login gets no time box.** It says "Ravi has no login, so he cannot confirm. Ask HR." Otherwise the manager types a time that can never be approved [engineer to confirm `user_id` is the test] |
| Value of the slice | Full | **Only for staff who have a login and press Confirm.** Evidence required: how many DTC held-day staff that is |
| Cost of the difference | One condition in one place | One condition in one place, plus the no-login row |

Either way it is a small switch in the same code, not two builds. **Build A and B behind nothing: pick one when counsel answers; do not build a setting for it** (no-over-engineering). Until then the slice cannot be released, but its page can be built and tested against B, the safe default.

**Recommendation to counsel (a wording, not an ask to bypass):** ask whether a held-day request filed by the person's own reporting manager, naming the manager, shown to the employee, and decided by HR, meets the condition, or whether the employee's own act is needed. A weaker middle path I would not propose first: A with a notice and a Not right button.

### The page, as it now stands (what holds from 01b and prototype-v1)

| 01b / prototype-v1 part | Holds? |
|---|---|
| One page (Whole team), no new screen or menu entry | **Holds** |
| Held chip, amber, with words; "Held" explanation line | **Holds**, but it counts only days with no request |
| Split line "need a time / waiting for HR / another manager's" | **Dropped** (those rows are not shown). Replace with one line: "N held days need a time from you" |
| Real punches beside the box (087's per-day timeline replaces the plain line) | **Holds**, uses 087's timeline |
| Time box, no pre-filled value, Arrival / Leaving buttons with no default for 3 or 5 punches | **Holds.** 087 sends one punch per request, so the manager adds one punch per row |
| Ready mark, bottom bar with count, cap of 50 | **Holds** |
| Confirm dialog with list of person, day, time | **Holds**; the one shared note box in it is **dropped**, the reason moves to each row |
| Banner and per-row results, refusal words, answer-lost guard | **Holds**; "Waiting for HR" per-row state **dropped** |
| "Waiting for HR" and "Not yours to send" row kinds | **Dropped** |
| Phone layout, Hindi words, no `localStorage` | **Holds**; Hindi needs words for "Reason" and "has no login" |
| Hiding "No clock-out" when the hold is on (UX-1), no Take back (UX-5) | **Hold** as pending decisions, unchanged |
| Prototype-v1 | **Needs a v2 from the UX designer** before build: per-row reason box, rows that leave after sending, the day control, and (under B) the no-login row. I did not draw it |

### What the manager sees after filing

The banner: "**3 of 3 sent to HR.** Ravi, Anita and Imran: HR will decide each one." A refused row stays, keeps its time and reason, and shows the server's sentence. A sent row leaves the list. The manager does not get a tracking list, ageing colours or reminders. Under B the banner adds one line: "Each person must confirm in the app before HR can decide." If a manager asks "why is Ravi's day still held?", the answer is on the employee's day sheet and the HR inbox, which already exist.

### How it reuses 087, and what is not built

- One call takes a list (cap 50), runs `raise_for_report` once per day, one savepoint per day, one result per day. The reason is passed per day. 087's checks (reason required, direct report only, window, one punch, duplicate refusal) all stay in `raise_for_report`, so there is no second copy of any rule.
- **Not built:** a new send path, a new DocType, a new field, a new setting. The Confirm flag is 087's.
- **Deliberately out (reasons):**
  - **Bulk approval by HR.** Pay is at stake and HR must look at each time. It was refused in 085 and stays refused.
  - One time or one reason for many people.
  - A manager-filed request that skips HR, or one that skips the employee's say (that is the counsel question).
  - Skip-level staff on this page.
  - A per-manager count, a "who forgot most" view, reminders.
  - Take back, double-scan label, amber flag: still "later".
- **Subtract pass:** removed this round: the two extra row kinds, the split line, the shared note box, the whole-line display and its two open questions. Nothing was added except a per-row reason box and the no-login row (B only).

### Thriving-workplace lens (what moved)

- **Inclusiveness:** the page helps staff who do not use the app, which is the point. Keep the wording neutral: "has no login", never a word about education or ability. **Risk:** under B those same staff are the ones the page cannot help. That is a real equity cost, and counsel's answer decides it.
- **Transparency / dignity:** a manager vouches for a time on another person's behalf. The employee's right to see it and say "not right" (A's notice or B's Confirm) is the protection for the least powerful person in the picture.

### Updated success measures

| Measure | Baseline | Target | Instrument |
|---|---|---|---|
| Held days with no request at the end of the next day (leading) | DTC 355 for 1-16 Nov; share unknown | Falling week on week | Held rows with no request, by day |
| Share of manager-sent held-day requests HR declines (quality) | Unknown, measure first | No higher than for employee-filed | Decline count by filer |
| Share of manager-sent requests that are decided within 2 days (B only) | Unknown | Most | Confirm and decision dates |
| Requests waiting for a Confirm that cannot come (B only, risk) | 0 by design | Stays at 0 because the page refuses to create them | Count of flagged requests on staff with no login |
| Managers sending at least once a week | Unknown | Most DTC managers by week 3 | Distinct managers per week (internal check only, never shown to anyone) |

### Updated kill criteria

Keep the four above. Add: (5) counsel says B, and fewer than about half of DTC's held-day staff have a login that is used: the page then helps a minority, so keep only the filter and drop the send bar; (6) HR declines most manager-filed times, which means the manager is guessing for others; (7) a test shows a manager's request can be approved with no reason, or for a person who is not a direct report.

### Questions for Surbhi (recommendation for each)

| # | Question | My recommendation | Blocks |
|---|---|---|---|
| N1 | **Ask counsel the gating question above.** | Ask this week, in the wording given. Build to B meanwhile | Release |
| N2 | A reason box on each row, or one shared box? | **Each row.** A shared text on many requests defeats counsel's condition | The row design |
| N3 | Direct reports only on this page? | **Yes.** Does DTC ever have a mid-level manager send for another manager's staff? If yes, tell me | Who appears |
| N4 | One day at a time (latest day with held days), with the period filter to catch up? | **Yes** | The day control |
| N5 | How many DTC held-day staff have a login? | I cannot check; ask the engineer for a count on the DTC copy before choosing between A and B in the plan | Kill criterion 5 |

**Gate:** Surbhi approves this revised brief, then the UX designer draws prototype-v2, then she agrees the design. Release also waits for N1. Nothing here is built, pushed or deployed.

**New assumptions:** [ASSUMPTION] "single day" means one day at a time on the page, one request per person per day. [ASSUMPTION] `Employee.user_id` tells whether a person has a login. [ASSUMPTION] `raise_for_report` on the 087 branch already requires a reason and sets the Confirm flag (spec says so; code not read).
