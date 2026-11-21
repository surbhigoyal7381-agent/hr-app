---
slice: 086-manager-held-days
artifact: 01a-ux-opportunities
author: hrms-ux-designer
date: 2026-11-20
status: draft
inputs: [docs/slices/085-held-odd-punch-days/, founder request 20 Nov 2026]
---

# 086 Managers fix held days in bulk: opportunities scan

**Risk tier I suggest: 1.** It files requests that release pay, and it widens who can act. Recommendation only.

## Bottom line

1. **Most of the screen already exists.** The "Whole team" page already lists the team's days, filters, pages and offers a button per row. **Bad news: its button asks for a reason, not the missing time**, so it cannot fix a held day. The held-day form (time plus In/Out) lives only on one person's month.
2. **The gap is one missing link, not a new page.** Make the team page know what "held" is, and let a manager give the time for several held days in one go.
3. **Bulk means many one-day requests.** A held day is released only by a one-day request that carries the time (from the 085 session, 20 Nov). A manager can never file one long request.
4. **The real risk is made-up times**, not clicks. Section 5 gives a design answer.

## What I read (proven) and what I did not

- **Read:** worktree `086-manager-held-days`, HEAD `2e31151f`, equal to `origin/dev` when I fetched. Files: `attendance_correction.py` (`team_days` 2110, `_flag` 2048, `raise_for_report` 2341, `_held_request_fields` 1231, `_held_flags` 995), `held_day.py` (`enforce_monthly_limit`, `_filed_by_hr`), `portal.js` (team page 15600-15960, held form 6355-6400). Rung and wording come from the 085 brief.
- **Did not run the portal or sign in.** No screenshots. Everything under "today" is **code reading, not a running page**. No login or tenant checked. The coordinator's note says the 085 session built on `31f0e713`; `origin/dev` is `2e31151f` now.
- **Not checked:** what the team page's "Ask HR to fix" does to a Held day (a one-day request with no time). The 085 session should say whether HR's approval releases it. It probably does not, so the manager's request would sit for nothing.
- **Not checked:** whether the HR Settings tick "managers see punches and breaks for the whole line" (ALV-328) changes the team page. It sits in `field_app_access.py` and `field_app_settings.py`. I did not open them. `team_days` itself takes a `depth` choice ("direct" or "all") with no reference to that tick.
- **Not checked:** Hindi wording, phone layout (no measuring done).

## 1. What a manager sees today (code reading)

| Step | What the code does |
|---|---|
| Open Attendance page, choose "Whole team" in the picker | `trOpen` loads `team_days`: a fortnight, 50 rows a page, worst first |
| Filters | From, To, Person, Department and Branch (only if more than one), Group by Person or Date, "Show: My direct reports / Everyone below me" (not shown to HR) |
| Chips | "No clock-out" (red), Absent flavours, "Short hours", "Fine", each with a count |
| What "No clock-out" means | `_flag`: an odd number of punches after double scans are folded. It is judged from punches, **not from the day's Held status**. The row has no held field |
| Row button | "Ask HR to fix" only for direct reports (`can_raise`). Form: reason, notes, "Send to HR". **No time field** |
| Held form | Only on one person's month: tap a day, "What time did X leave?", In/Out if there are 3 or 5 punches, "Send to HR for X" |

**Taps to fix 10 held days (my count from the code, an estimate, not timed):**

| Route | Per day | For 10 days |
|---|---|---|
| Team page, tap name, day sheet, type time, (pick In/Out), Send, then back to the list | about 5 taps plus typing | **50 taps plus 10 reloads** |
| Team page "Ask HR to fix" | 4 taps, no time | does not release the day [not checked] |

Two other facts. (a) `can_raise` also fails for days older than the manager filing window if one is set. (b) `raise_for_report` already refuses anyone who is not a direct report, so "acting" stops at direct reports (Surbhi, 17 Oct).

## 2. How competitors handle it

Source: web searches on **20 Nov 2026**; I read search summaries and result titles, not full help pages. Nothing here was seen in a running product.

| Product | What I found | Label |
|---|---|---|
| **Keka** | "Bulk Regularisation" for HR **and managers**: pick a date range and a status, select employees one by one or "select all", apply. Keka's own page says it **bypasses the normal approval** and marks the day "R". Its advice: confirm each discrepancy is genuine and keep a record for audit. Employees raise their own from Me, Attendance. Admin can also regularise on someone's behalf | read, 20 Nov [help.keka.com bulk article](https://help.keka.com/hc/en-us/articles/39946611032721-Bulk-Attendance-Regularisation), [admin help](https://help.keka.com/admin/admin-help/bulk-attendance-regularisation) |
| **Zoho People** | Managers and admins **approve** regularisations from Approvals or Team, Regularization. I found no bulk raise for a team. On behalf of one employee: Zoho Payroll's page shows one person at a time | read, 20 Nov [Zoho guide](https://help.zoho.com/portal/en/kb/people/administrator-guide/attendance-management/operations/articles/managing-regularization-requests), [Payroll on-behalf](https://www.zoho.com/in/payroll/help/employer/employees/leave-and-attendance.html) |
| **greytHR** | Manager "override team attendance in bulk" is listed as a manager activity in the ESS help; an admin Excel importer handles bulk permissions. Exact steps not in what I read | read, 20 Nov [ESS help](https://www.greythr.com/help-ess-web/attendance-activities), [admin bulk](https://www.greythr.com/help-admin/attendance-management/view-employees-attendance-bulk) |
| **Darwinbox, factoHR** | Search returned no Darwinbox page; factoHR only a glossary page. **I found nothing, which is not the same as "they have none"** | read, 20 Nov |
| **CatalystOne, Frappe HR standard** | Not searched this run | not checked |

What this says (inferred): bulk filing by a manager exists in at least one major product (Keka), and it **skips review**. Ours keeps HR's decision, so we are safer by design, and that is also our point of difference.

## 3. Ideas by persona

| Persona | Idea | Job | Evidence | Size |
|---|---|---|---|---|
| **Line manager** (laptop, phone) | The team page chip "Held" (real Held status) with a count, opened by default for a manager when any exist | Find the held days without hunting | Code: today's chip is punch-based; DTC 1-16 Nov had 355 held days (Surbhi's count) | S |
| Line manager | Tick the held days, one box per day, a "Send N to HR" bar at the bottom | Fix 10 in one pass | 50 taps today; Keka has the select-many pattern | M |
| Line manager | Per row, a time box (with In/Out when 3 or 5 punches) sitting on the row itself, not behind a day sheet | Give the time where the problem is (principle 4) | Held form fields exist: `acHeldSubmit` | M |
| Line manager | A **result line per day** after sending: "8 sent. 2 not sent: Nov 12 for Ravi (already requested)" | Know what happened | One call per day can fail on its own | S |
| Line manager | Double-scan days (3 to 10 minutes apart, about 76 of 355 at DTC) shown with the two close punches named: "Two scans 4 minutes apart" | Tell a double scan from a real missing punch | Surbhi's numbers, 1-16 Nov | S to M [engine may already fold them; not checked] |
| **HR manager** | Each manager-filed request says "Filed by Sakshi Verma for 9 days in one go" and sits in the existing review queue | Review a batch with the context to decide, not a pile of unmarked rows | `raise_for_report` already stamps the manager's name in the note | S |
| HR manager | A per-day time that is plainly outside the shift or in the future is shown to HR in amber | Catch made-up times | Section 5 | M |
| HR manager | Nothing new for bulk **approval** (still one by one; 085 rejected it) | Keep review honest | 085 brief | none |
| **Employee** | Sees on the day sheet "Sakshi Verma sent 18:30 for you. HR will decide" (085 already shows who sent a request: `held_sent_by_you`; check the wording for the manager case) | Knows a time was given for them, can object | The one-way rule: a manager must not make the employee's day worse unseen | S |
| Employee | Can still file their own time; a manager's pending request does not block it [ASSUMPTION, not checked] | No lock-out | | S |
| Frontline employee, phone | No change in this slice | | | none |
| **CXO** | No names. At most one company figure "held days still open" | | 085 brief already says CXO sees nothing new | none, leave out |

## 4. Not to copy

- **Keka's bulk that skips review.** Pay is at stake and 085 put HR in the loop on purpose.
- A "select all, apply one status" button. For held days it would mean one invented time for everyone.
- A manager ranking of who forgets most. That is a watch view (product-context §6). Counts on the page must stay per day to fix, not a league table.
- A nag loop of reminders to managers.

## 5. The open questions the brief must answer

| # | Question | My recommendation | Why it matters |
|---|---|---|---|
| Q1 | **Direct reports only, or the whole line?** | **Direct reports only**, the same as `raise_for_report` today (Surbhi, 17 Oct). The page may still show the whole line to look at, with the tick/time hidden on rows that are not direct | Widening it is a permission change. ⚠ DECISION, owner Surbhi. The ALV-328 tick is about **seeing punches**, not about filing; do not reuse it for filing without her say |
| Q2 | **One time for many people, or one time per person?** | **One time per day, per person.** No "apply 18:30 to everyone". A shortcut is fine: copy the shift end time into a row's box as a suggestion the manager must confirm | Two people never leave at the same minute; one shared time is how a pile of made-up times is made. The engine's rule is that the time is a real punch someone is vouching for |
| Q3 | **Does the monthly limit count manager-filed requests?** | Already answered by code: **held-day requests never count** (they carry `alvoraa_missing_log`), and HR-filed ones never count. A manager's **ordinary** request counts against the employee. Recommend: leave as is. Bulk held filing cannot burn an employee's limit | Confirm with Surbhi that it is intended for the employee's allowance to be spent by a manager's ordinary requests (it is today). Not changing it keeps the slice small |
| Q4 | **Which page?** | **The existing "Whole team" page** (reached from the Attendance picker). Add a real "Held" chip, a time box per held row and a send bar. No new page, no new menu entry | A second page would repeat the duplication the 17 Oct consolidation removed |
| Q5 | **Made-up times** | See below | |

### Q5: how to stop a pile of made-up times (recommendations, in order of cost)

1. **Nothing is final.** HR still decides each request, and the person who raised it cannot approve it (already true). Say so on the bar: "HR will review each day. Your name goes on all of them."
2. **No blanket time** (Q2) and **no time pre-filled as if confirmed.** A suggestion is greyed text, not a value.
3. **Show the evidence beside the box**: the day's real punches ("Punch: 09:02. Shift ends 18:00") so the manager sees what they are completing. HR sees the same punches on the request (085 already does, at `portal.js` 6620).
4. **Refuse the impossible in words**: a time that would put the day outside the shift's window or in the future. Needs the engineer to say what `validate_missing_time` already refuses [not checked].
5. **A short confirm, once:** "You are saying the missing punch was 18:30 on 7 days. HR will see your name on each." No pre-ticked box, no guilt wording.
6. **Optional, not recommended now:** a per-manager count of bulk sends for HR. It leans toward watching a manager. Leave it out unless Surbhi asks.

**I would not** add an "approve as is" mode or any auto-approval for a small time difference. That is a rubber stamp.

## 6. Other questions the brief should settle

- **Phone.** A table of ticks and time boxes at 360 px is the hard part. A list, one day per card, a time box of 16px text and 44px tall, and a bar fixed at the bottom. Not designed yet.
- **Limit of one send.** 10 requests in one tap means 10 server calls. What if 3 fail? Recommend a per-day result, no silent partial success. The 085 session has a lost-answer guard (AC-30) for single sends; the bulk form must not skip it.
- **ALV-404** (on a log-type shift one OUT punch gives Absent, not Held): some days will not appear under "Held" for log-type shifts until it is fixed.
- **The Whole team page and the Held status disagree today** (punch-count flag against `status == "Held"`). The brief should say which one the chip follows. I suggest the Held status, because it is the one that holds pay.
- **Test data:** ppj.dev has held days on 19 Nov that testers use. Do not change them.
- **Success measure idea:** held days still open at payroll cut-off, by tenant (085's own leading measure); time from a held day appearing to its request being sent.

## 7. What I would leave out of this slice (for Surbhi to decide)

Reminders to managers; ageing colours; bulk approval; a manager league table; a CXO figure; anything that works on a day other than a held day.

## Subtract pass

Removed from my own first list: a "held days" home card for managers, a mobile push to managers, a copy-from-yesterday time, and a manager league table. Kept only what the founder's sentence asks for (filter, whole team, bulk request).

## Next step

Hand to `hrms-product-manager` to write the brief. Answer Q1 and Q3 with Surbhi first, because both are permission or pay questions. No prototype in this mode.
