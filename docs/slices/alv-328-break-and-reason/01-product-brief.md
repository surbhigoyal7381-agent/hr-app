# ALV-328 - Break time per day, and "why" for each day's cut

Product brief (thin). Asked for by Surbhi on 12 Nov 2026. Builds on ALV-326, branch
`slice/alv-326-shift-hours`, which is **on dev at `4ae8499a` but not on production yet**.
This slice cannot reach production before it. *(Corrected 12 Nov 2026 by the business
analyst at the lead session's request; the line said ALV-326 was not on dev.)*

**Bad news first.**

1. **No UX scan (`01a`) and no DevOps first look (`07` §1) exist for this slice.** The
   brief was asked for as a thin one without them. The design gate should not be skipped
   because of that: the two screens change, so the UX designer still draws them.
2. **I could not check how many DTC Attendance days carry a "why" today.** The text is
   written only when the pay-rule engine judges a day. If DTC's rule set has not judged
   November yet, part 2 shows an empty line on every day until it does. *Evidence
   required:* a read-only count of DTC Attendance rows with `alvoraa_evaluated_on` set,
   by month.
3. **The "why" text is English only**, and written for HR (it says "slab", "band",
   "rule set"). Staff on the shop floor may not read it easily.

---

## 1 · The job

- **Employee (incl. frontline):** "When my pay shows a quarter cut or a red, I want to see
  in one place how long my breaks were and why that day cost me, so I can check it myself
  and only go to HR when I think it is wrong."
- **Line manager:** "When someone in my team asks about a cut day, I want to see the same
  break and the same reason they see, so we talk about one set of facts."
- **HR Manager:** "I want to stop reading the reason out of the Attendance form for every
  person who asks."
- **CXO:** no change.

## 2 · Current pain (a story, no numbers)

ALV-326 makes breaks cost money: a break past the allowance (40 minutes at DTC) is deducted
from the day. Today the Attendance page draws every punch, but adds nothing up. A person
must do the sums on 4 to 6 punches in their head. The engine already writes the reason
(`alvoraa_rules_why` on Attendance), but grep finds no screen that shows it (confirmed in
ALV-326's security review, M3). So every "why was I cut?" is a trip to HR.

## 3 · Competitors (two lines)

Keka and Zoho People show break time per day on the employee's own attendance log
`[recall - verify]`. None that I know of shows a plain-words reason per deduction; that is
our "explainable" whitespace (product-context §1, §7).

## 4 · What exists already, to reuse (confirmed in the worktree)

| Need | Already there | Where |
|---|---|---|
| Punches per day on the Attendance page | Yes, every punch is fetched and drawn | `attendance_correction.month()`, `portal.js` `acLoad`/`acPaint` |
| Merge repeat punches within 2 min | Yes | `payroll_rules.collapse_duplicate_punches` (`DUPLICATE_PUNCH_MINUTES = 2`) |
| Break gaps (2-3, 4-5, ...) | Yes | `payroll_rules.break_gaps` |
| The reason per day | Yes, stored | Attendance `alvoraa_rules_why`, `alvoraa_evaluated_on` |
| Who may see whose month | Yes | `month()` via `_subject` and `frappe.get_list`; `attendance_analytics.person()` via its own reports-to and HR check |
| Per-day list on Attendance Insights | Yes, one person's days | `attendance_analytics.person()` and the Attendance Insights panel |

**Rung: new code (small).** Nothing to configure: no standard Frappe HR screen sums breaks
or shows this field to staff. No new DocType, no new field, no new endpoint, no setting.
Two existing endpoints return one or two more values per day, and two existing screens
show them.

## 5 · The thinnest slice

**Attendance page (`panel-att-record`), one person's month:**
- Each day shows **"Break 52 min"** beside the hours already shown. Sum of the gaps from
  `break_gaps` after `collapse_duplicate_punches`, over the punches `month()` already
  reads. Server side, so it uses the same two functions as the engine.
- On a day with an odd number of punches: **"Break: a punch is missing"**, not a number.
  The engine deducts no break on such a day, so a number would mislead.
- When the open day has a reason: a **"Why this day"** line with the stored text, and
  "Judged on 3 Nov 2026" beneath it, so a person knows if it predates a correction.
- No reason stored: show nothing. No "not judged yet" banner.

**Attendance Insights, one person's days (`person()`):**
- The same **Break** figure per day. One Employee Checkin read for the person's range
  (already capped at `PERSON_MAX_MONTHS`). The reason is **not** added here; the
  Attendance page is where a person goes for one day.

**The WOW.** A person opens 4 Nov, sees "Break 55 min", and under it: "Breaks 55 minutes,
15 over the 40 allowed ... Slab 90-97%: 0 quarters, 1 red." They see the answer before they
think of asking HR.

**Out of scope (do-not-build, with reasons):**
- Break on the team list or the organisation list, or any sort by break. It would rank
  people on a behaviour signal (product-context §6 item 4). Per person, per day only.
- A month total of break time. Not asked for as a need; see question 1.
- Rewriting the reason text into staff wording or Hindi. A separate change to the engine;
  see question 3.
- A grievance button on the day. "Ask for a correction" already exists on this page.
- Breaks for October at DTC. The muster upload holds only first and last punch, so October
  honestly shows 0 or nothing; see risk R1.

## 6 · Access expectations

| Data | Employee | Manager (their reports) | HR (their companies) | CXO | Outsider | Kano |
|---|---|---|---|---|---|---|
| Break per day | See own; change none | See; change none | See | No new view | None | Must |
| Reason ("why") per day | See own | See | See | No new view | None | Must |

Purpose: a person's right to see why their pay was cut (counsel, 18 Sep 2026: access and
grievance for automated pay decisions). The reason text holds only that person's own
times, their own grace, limit and band figures, and their own category's rule. **I read
every line the engine writes (`payroll_rules.py` 530-755): no other person's name, ID or
data appears.** Nobody may change either value; both are read-only.

**For Surbhi, the five questions:**
1. Who can read it: the person, their reporting line and HR, through the two endpoints'
   existing checks. The reason sits on Attendance at permission level 0, so *Needs
   validation:* a plain staff login can probably already read its own reason through
   `/api/resource/Attendance`. This slice opens no new door; the engineer must confirm it,
   and confirm a staff login cannot read a colleague's.
2. Test as a plain staff login and a plain manager login through the API, on a fresh site.
3. Fresh site: the field is empty until a rule set judges a day. Real tenant: count first
   (bad news 2).
4. Bypasses: none expected. `person()` already uses `get_all` behind its own check; no new
   `ignore_permissions`.
5. A manager can change or share nothing new.

## 7 · Thriving-workplace check

- **Engagement:** clarity. A person can check their own pay day without asking.
- **Collaboration:** manager and employee look at the same reason.
- **Inclusiveness:** risk. The reason is English and HR-worded (bad news 3).
- **Transparency:** shows a person their own decision; shows no ranking of anyone.

## 8 · Regulatory read

1. DPDP (access to own data) and counsel's ruling on automated pay decisions.
2. The employer's duty; this helps DTC discharge it.
3. New: staff see their own reason on screen. No new data is collected.
4. We would defend it: it shows a person their own pay reasoning, nothing about others.

## 9 · Success criteria

| Measure | Baseline | Target | How measured |
|---|---|---|---|
| "Why was I cut?" questions to DTC HR in November pay week | unknown, measure first (ask DTC HR) | half of the baseline | DTC HR's own count, before and after |
| Break shown matches the engine's break for the same day | n/a | 100% of DTC November days | test: sum on screen vs `_punches` gaps, every day |
| Corrections asked on days with a reason shown | unknown | no rise beyond DTC's usual | existing correction requests, by month |

## 10 · Risks

- **R1** October shows no breaks at DTC (muster upload). Staff may read "0 min" as wrong.
  Recommend: show "Break" only when the day has 3 or more punches.
- **R2** Night shifts: `month()` groups punches by their linked Attendance, the engine by
  calendar date. The two sums could differ for a shift crossing midnight. The engineer must
  check DTC has none, or use one rule.
- **R3** A stale reason: a correction changes punches but the day is not re-judged. The
  "Judged on" line makes that visible.
- **R4** ALV-326 changes before release; this slice rebases on it.

## Open questions for Surbhi

1. **Break per day only, or also a month total?** Blocks the screen. I recommend per day only.
2. **Highlight a break over the allowance?** E.g. "Break 55 min (15 over)" in red. Blocks the
   screen. I recommend yes, the words only, no colour alone; it reuses the allowance figure
   the banner already reads.
3. **Show the reason text as written, or hide HR-only lines** (such as "the rule set has a
   gap")? Blocks the spec. I recommend as written now; staff wording or Hindi is a separate
   ticket.
4. **Show break and reason to the manager too, or the person only?** I assume yes, as both
   pages already show the manager the punches.

## Surbhi's decisions (12 Nov 2026)

Brief approved. All four recommendations accepted:

1. Break per day only. No month total.
2. Yes, flag a break over the allowance in words, e.g. "Break 55 min (15 over)".
3. Show the reason as written for now. Staff wording or Hindi is a later ticket.
4. Yes, managers see a team member's break and reason.

## Assumptions

- [ASSUMPTION] The 2-minute merge in the request is the engine's `DUPLICATE_PUNCH_MINUTES`.
- [ASSUMPTION] "Attendance Analytics" means the Attendance Insights panel's one-person view.
- [ASSUMPTION] A plain staff login can already read its own `alvoraa_rules_why` via the API.

## Kill criteria

- The screen break and the engine break disagree on any DTC November day and the cause is
  not a missing punch: stop and fix the rule before showing it.
- DTC's November days carry no reason at all: ship break only and say so.

## Subtract pass

Removed: the reason on Attendance Insights (one place is enough); a month total; a
"not judged yet" message; a grievance button; a staff-language rewrite of the reasons.
