# Slice 066 — Grooming red mark, set by the reporting manager

**Product brief · 22 Oct 2026 · Status: DRAFT for Surbhi's gate (build, change or drop)**
Author: hrms-product-manager. I recommend; Surbhi decides.

> **Read these four lines first.**
>
> 1. **The UX scan (`01a`) and the DevOps first look (`07` §1) do not exist for this slice.**
>    The process wants them before the brief. I wrote the brief anyway because the request
>    came straight from Surbhi with a clear shape. The persona table (§7) is mine, not the
>    designer's. Both documents must be written before design starts.
> 2. **Today no red or green money reaches a DTC payslip at all.** The function that turns the
>    month's reds into a `Red Value` line (`push_marks_to_additional_salary` in
>    `alvoraa_portal/payroll_slip.py`) is called by nothing. The slip hook sets paid days only.
>    A grooming line built on the same path would also never reach a slip. This is not a
>    grooming problem, but this slice cannot deliver its outcome without it. See §9 and Q1.
> 3. **DTC's `Grooming Red Value` (GRV) line already sits in one salary structure as a fixed
>    amount.** If that amount is not zero, every employee on that structure would lose it on
>    every slip, marked or not. No slip has ever been made at DTC, so it has cost nobody
>    anything yet. It needs checking before the first DTC payroll, with or without this slice.
> 4. **"BTC" is taken to mean DTC** (Durga Trading Company, `dtc.alvoraa.co`, our first client
>    tenant). `[ASSUMPTION]` — Surbhi wrote "BTC"; nothing else in the repo is called BTC.

---

## 0 · The recommendation in five lines

1. A reporting manager ticks **"Grooming red"** for a direct report on a day. It is off by
   default. One tick per person per day, with one short reason from a fixed list.
2. Each ticked day costs **₹200**, or **₹100 for Junior grade**. These are the rates DTC's rule
   set already uses for ordinary reds. No new rate is needed (Surbhi, 22 Oct 2026).
3. The money goes on the existing **`Grooming Red Value`** line. It sits beside `Red Value` on
   the slip and in two new columns of the desk report *Salary Components and Workings*.
4. The employee sees the mark that day: a bell notice and a line on that day in their
   Attendance month, naming who marked it and why. HR can remove a mark; the manager can
   remove their own on the same day.
5. **The mark lives in a tiny new record (rung 5), not in a field on Attendance.** At the
   moment a manager sees someone at the counter, that day's Attendance does not exist yet.
   And DTC's attendance fixes delete and rebuild Attendance, which would wipe the marks.

---

## 1 · What already exists — checked in the repo (worktree = `origin/dev`, 22 Oct 2026)

| Question | Answer | Label |
|---|---|---|
| Does any DTC rule ID name grooming, dress or uniform? | **No.** The IDs quoted in code and tests are GBL-02/03/04/06/09, ATT-01 to 07, WSD-01 to 06, GRN-02/03/04, LB-01/02/05, RED-01, RED-03, RED-06. **RED-02, RED-04 and RED-05 are never quoted anywhere.** One of them may be the grooming rule. | Confirmed (grep); the gap is an inference |
| Is DTC's rule document in the repo? | **No.** Only its IDs, quoted in code. I could not read the rule text. | Confirmed |
| Is a grooming red modelled anywhere — a field, a verdict column, a rule row? | **No.** "groom" appears in no Python or JSON file of the app. The day's verdict (`DayVerdict.reds`) comes only from the slab table and the late-and-early rule. | Confirmed |
| Is there a pay line for it? | **Yes.** DTC has a Salary Component `Grooming Red Value` (GRV, Deduction, fixed amount, no formula). It sits in 1 of DTC's 2 salary structures. Nothing feeds it. | Confirmed by the coordinator's read-only look at DTC, 22 Oct |
| How do ordinary reds become money? | Month total of reds, minus `free_reds_per_month` (DTC: **2**, RED-03), times the grade's rate from the rule set's `mark_rates` table (DTC: **Junior ₹100, Senior ₹200**, "No leaves" ₹0). Greens and reds are separate lines and never netted (RED-06, GRN-04). | Confirmed: `payroll_month.py` L204–211; DTC figures from the prepared rule-set script |
| Who is "junior"? | The rule set reads grade from the Employee field **`dtc_grade`** (values Junior / Senior). The same table already prices ordinary reds. | Confirmed in the script; I did not count DTC's Junior staff (no server access) |
| Contract staff? | `employment_type = Contract` → category with `earns_marks = 0`. They get no reds and no greens. | Confirmed: `payroll_rules.py` L574–586 |
| Is the rule set live at DTC? | **Saved, not enabled.** Until it is enabled, the engine does nothing at DTC. | Confirmed (memory, 15 Oct; the report says "not live") |
| Can managers act on direct reports' records? | Yes. `manager_scope.py` grants one User Permission per manager, per report, per doctype. It covers four doctypes: Attendance, Employee Checkin, Attendance Request and Leave Application. `reports_to` is the only source of who the manager is. | Confirmed |
| A manager screen listing team days? | Yes. The **Attendance page → "Whole team"** (slice 060), fed by `attendance_correction.team_days`. It lists days for direct reports first, with problem chips first. Each row says whether the caller may act (`can_raise`). | Confirmed |
| Does the employee see reds per day in the portal today? | **No.** The today banner (`day_marks.py`) explains how a red *could* happen and says "the first 2 a month are free". The engine's per-day "Why" text is not shown in the portal. The Leave page card shows leave credits, not reds. | Confirmed |
| Audit of changes on Attendance? | Attendance has `track_changes = 1`, so Frappe keeps a version history. | Confirmed |

**Frappe HR standard:** it has no grooming or dress-code check. The nearest pieces are
`Additional Salary` (a one-off pay line, already used by our engine) and `Employee Grievance`
(a desk-only complaint form). Neither does this job. See §9 for why each was rejected.

---

## 2 · Job to be done

*"As a store manager at DTC, when I see one of my people at the counter without uniform, I
want to mark it in ten seconds on my phone, so the rule is applied the same way every month
and I don't have to keep a paper list for HR."* — **Line manager** `[ASSUMPTION — her words
paraphrased; not heard from a DTC manager]`

| Persona | What changes for them |
|---|---|
| **Reporting manager** (marks) | A "Grooming red" tick on each direct report's day, today only. No paper list. |
| **HR Manager** | One column in the report they already use shows each person's grooming reds and the deduction. They can remove a mark, and the history shows who did what. |
| **CXO / owner** | One more line on the slip that matches DTC's own policy. Nothing new to read. A dress-code count by branch is **not** in this slice. |
| **Employee** (is marked) | Told the same day, by name and reason. Sees it on that day in their Attendance month and on the payslip line. Can ask the manager or HR to remove it. |
| **Contract staff** | Not marked at all, matching the engine's rule that they carry no marks (Q6). |

## 3 · Current pain

**No numbers.** I do not know how DTC records grooming today. It may be a paper register, a
WhatsApp message to HR, or nothing. **Evidence required:** how DTC did it in September, and
how many grooming deductions they made. The story: a counter manager notices a missing
uniform, tells HR at month end from memory, and the employee first hears of it when the
salary is short by ₹200. That is the unfair version this slice replaces.

## 4 · Competitive view (short — this is a client rule, not a market feature)

| Capability | Frappe HR | Zoho People | Keka | Darwinbox | Retail-ops apps (store audit) | Us after this slice |
|---|---|---|---|---|---|---|
| Manager marks a dress-code breach per person per day | No (seen, repo) | Custom form possible `[recall — verify]` | Not found; its penalties are for late/early attendance `[recall — verify]` | Not found `[recall — verify]` | Store-level grooming checklists, often with photos `[recall — verify]` | Yes, one tick, one reason |
| Breach feeds pay automatically | No | Via custom payroll input `[recall — verify]` | No `[recall — verify]` | No `[recall — verify]` | No | Yes, on the GRV line |
| Employee told the same day | No | Depends on setup | — | — | Rarely | Yes |

**What we will NOT do that others do:** no photo of the person, no AI check of appearance,
and no store "grooming scorecard" that ranks staff. A photo of someone's appearance is
sensitive personal data, kept for a ₹100 judgement. Automated appearance checks are
facial analysis, which we refuse (product-context §6 item 3). A ranking invites managers to
compete on how many people they catch.

## 5 · Three ways, and could we not build it

| Way | What it is | Verdict |
|---|---|---|
| Conventional | A "Disciplinary Action" module with incident types, approvals, photos and a penalty matrix | No. A module for one tick. |
| **Better** (recommended) | One tick per person per day on the manager's existing team list, one fixed reason, priced by the rules the engine already has, told to the employee at once | **Yes** |
| Reimagined | The employee confirms "in uniform" at check-in and the manager only checks exceptions | No. It adds a step for 300 people to catch a handful, and self-reporting appearance is awkward. |
| **Not building at all** | HR types a GRV amount into `Additional Salary` by hand each month from the managers' lists | This works **today**, with zero code, once the GRV structure row is zero. It loses the daily record, the employee notice and the audit trail. **Offer it to DTC as the stopgap for October/November.** |

## 6 · Kano class and demand

- **For DTC: Must-be (proxy).** The rule is in their policy and the pay line is already in
  their salary structure. Without it, their payroll needs a side spreadsheet. Evidence: **seen**
  — Surbhi, 22 Oct 2026, and the GRV component found on DTC.
- **For the market: Indifferent, leaning Reverse (proxy).** No buyer has asked for it. Staff
  may see a manager-judged pay cut on appearance as unfair. It belongs to DTC's rule set and
  must stay invisible to tenants without one, just as greens and reds are today.
- **What would change this:** a second retail client asking for the same rule would move it to
  Performance for retail.

## 7 · Persona enhancements through the portal (no `01a` yet — my own list)

| Persona | Idea | Job it serves | In this slice? | Why |
|---|---|---|---|---|
| Line manager | Tick on today's row in "Whole team", reason picker, undo until midnight | Mark it in seconds, fix a mistake | **Yes** | It is the slice |
| Frontline employee | Bell notice + a line on that day in their Attendance month | Hear it the same day, not on payday | **Yes** | Fairness. A pay cut nobody was told about is the main risk |
| Employee | "Ask to remove" button that raises a request to HR | Dispute | **Later** | Talking to the manager or HR covers it at first. Build it only if disputes happen often |
| HR Manager | Two columns in *Salary Components and Workings*; remove a mark in desk | Check before payroll | **Yes** | It is the report they already reconcile against |
| HR Manager | Marks per manager per month | Spot a manager who marks everyone | **Yes, as a saved desk report view** (configuration) | The guard in §12, at no build cost |
| CXO | Grooming trend by branch | — | **No** | Nobody asked; it starts a ranking |
| Contract staff | — | — | **No** | Engine gives them no marks |

## 8 · The WOW

On the manager's phone, in **Attendance → Whole team**, today's row for Rahul reads
"Present · in 10:24". The manager taps **Grooming red**, picks "Not in uniform", and the row
immediately says:

> **Grooming red today · Not in uniform · Rahul has been told. You can undo this until midnight.**

At the same moment, Rahul's bell shows: *"Ravi Kumar marked a grooming red for you today:
Not in uniform. It costs ₹100 on this month's salary. If it is wrong, speak to Ravi or HR."*

## 9 · The thin slice

**Rung on the ladder: 5 — a tiny new DocType, plus small engine changes (rung 4) and some
configuration (rung 2).** Every cheaper rung was tried first:

| Rung | Option | Why rejected |
|---|---|---|
| 1 Already there | Frappe HR has nothing for this | — |
| 2 Configuration | HR types `Additional Salary` per breach (§5) | No daily record, no notice to the employee, managers would need access to pay records. **Kept as the stopgap.** |
| 3 Customisation | A tick field on **Attendance** | **Fails twice.** (a) Today's Attendance is created only after the shift ends (Frappe HR's auto-attendance waits for `shift_actual_end`), so at 10:24 there is nothing to tick. (b) DTC's fixes **delete and rebuild Attendance** (memory, 16 Oct: "the day must be deleted first"; 4,000 records cancelled once). Every grooming mark on a rebuilt day would vanish, a pay judgement lost without a trace. |
| 3 Customisation | A tick on **Employee Checkin** | Punches are machine evidence. They are also re-tagged, re-imported and deduplicated at DTC. Same loss, and it mixes a person's judgement into the machine record. |
| **5 New DocType** | **`Grooming Mark`**: employee, date, reason (Select), marked by (set by the system). One per person per day. Removing it is deleting it. Track changes on. | **Chosen.** It exists from the first moment, survives Attendance rebuilds, and is scoped by the same User Permissions mechanism (add it to `SCOPED_DOCTYPES`, one line). |

**What is built:**

1. **The record** — `Grooming Mark`, four fields, unique on employee + date.
2. **Who may create or delete it** — only the employee's own `reports_to` manager, only for
   **today**, only if the person has a punch today and is not Contract staff. HR may remove
   any mark in desk until the month's slip is submitted. All of this is checked on the server.
3. **The count** — `payroll_slip.month_summary` counts the person's marks in the period.
   The month summary adds `grooming_reds` and `grooming_deduction`, using the **same grade
   rate** from `mark_rates` (Junior ₹100, Senior ₹200). Contract staff (`earns_marks = 0`)
   count zero. **No new rate field, no new child table.**
4. **The pay line** — the grooming amount goes into an `Additional Salary` on `Grooming Red
   Value`, through the same `_set_additional_salary` routine that replaces rather than adds.
   The GRV structure row must be set to **₹0** (configuration, Q2).
5. **The report** — two columns beside `Reds charged` / `Red deduction`: **Grooming reds** and
   **Grooming deduction**. Net subtracts it. The "Why" column says, e.g., "3 grooming reds at
   ₹100".
6. **The employee** — a bell notice on save (a standard Frappe Notification: configuration),
   and one line on that day in their own Attendance month.
7. **The manager screen** — the tick and reason on today's row in "Whole team", for rows
   where the caller is the direct manager.

**Separate from the slice, but this slice's outcome depends on it (Q1):** nothing calls
`push_marks_to_additional_salary`, so `Red Value` and `Green Value` never reach a slip
either. Whoever fixes that wires GRV in the same place. I have **not** put that fix in this
slice's scope. It is a gap in slice 059 and belongs to it.

| Pile | Items |
|---|---|
| Needed to validate now | The rule text (RED-02/04/05?), Q2 and Q3 answered |
| Needed before it ships | Items 1–7; GRV structure row at ₹0; the 059 slip wiring (Q1) |
| Worth doing later | Employee "Ask to remove" button; stand-in manager |
| Not doing | Photos; HR approval step; branch scorecards; marking in advance or in bulk; a cap on marks |

## 10 · The screen — surfaces counted first (P8)

Surfaces that already answer "my team's day": **Attendance → Whole team** (slice 060),
**Attendance → a person's month**, **Attendance Insights**, and desk **Attendance** list.
**Reuse Whole team.** It is where the manager already acts on direct reports' days, and its
rows already carry the "may I act" flag. One honest gap: **that list is built from Attendance
rows, and today's do not exist until the shift ends.** So "today" needs the list to include
direct reports who have punched in today. That is the one real design question for the UX
designer (Q9). No new page, no new menu item, no settings page.

## 11 · Run-side reality

No new app, no worker, no file storage, no public page. About 363 people × 30 days at most
→ under 11,000 small rows a month, in practice far fewer. One extra grouped query in
`month_summary`. **DevOps §1 is missing — this is my estimate, not theirs.**

## 12 · Privacy and fairness

This is **a manual judgement about a named person's appearance that cuts their pay.** That
is the most sensitive kind of input this product handles. So:

- **Audit:** who marked, when, and who removed it — the record's own `owner`, plus track
  changes, plus a comment kept when HR deletes one. **No silent edits:** the reason cannot be
  changed; to change it you remove the mark and make a new one.
- **Fixed reasons only, about clothing, never the body:** e.g. *Not in uniform · Uniform
  incomplete or unclean · No name badge · Wrong footwear.* **No free text, and no reason
  about hair, beard, head covering, jewellery or skin.** A free-text box invites comments on
  religion or looks. ⚠ COMPLIANCE — a dress rule that touches religious dress can be
  indirect discrimination. I am not a lawyer. The reason list must be DTC's, approved by
  Surbhi, and checked by counsel.
- **Guard against marking everyone:** a saved desk report of `Grooming Mark` grouped by
  marker and month (configuration). HR sees at a glance if one manager marked 40 people.
  **No hard cap** — a cap is a rule nobody asked for.
- **Employee told the same day**, every time. No mark is ever visible to colleagues.
- **Retention:** a grooming mark is both a performance-style judgement (counsel: employment
  + 6 months, then erased) and an input to wages (kept longer by wage law). Counsel left that
  conflict open on 18 Sep. ⚠ COMPLIANCE — owner: Surbhi with counsel. It blocks the purge
  rule, not the build.

## 13 · Thriving-workplace check

| Lens | One line |
|---|---|
| Engagement | Mostly negative by nature. The same-day notice turns a payday surprise into a fair warning. |
| Collaboration | No effect. |
| Inclusiveness | Risk: dress rules can hit religious dress or people who cannot afford a second uniform. Hence clothing-only reasons, and counsel review. |
| Transparency | The employee sees who marked them and why, the same day. Nobody else does. |

## 14 · Regulatory read

1. **Regime:** DPDP (personal data about an identified person), Indian wage law (deductions
   from wages), and possibly equality law on dress. No AI.
2. **Whose duty:** DTC's, as employer. The notice and audit help DTC defend each deduction.
3. **New possibility:** a manager can now cut pay by a judgement, daily. That is the
   compliance event, and security must turn it into requirements next.
4. **Front page test:** "Manager docks ₹200 for a missing badge, employee told the same day,
   can ask HR to remove it" — defensible. "Without telling them" — not, which is why the
   notice is in the slice.

## 15 · Success criteria

| Measure | Baseline | Target | How measured |
|---|---|---|---|
| Grooming deductions on DTC's first enabled month that come from marks, not hand-typed amounts | Unknown — measure first | 100% | GRV `Additional Salary` rows with no `Grooming Mark` behind them = 0 |
| Marks removed after being made (wrong or disputed) | None yet | Under 10% in month one | Deleted ÷ created, from the version history |
| Employees told the same day | None yet | 100% | Notification Log entries ÷ marks |
| HR time to work out grooming deductions | Evidence required from DTC | Near zero | Ask DTC's payroll person before and after |

## 16 · Risks — red team

| Risk | What happens | Cheapest check |
|---|---|---|
| **The slip wiring gap (Q1) stays open** | Marks are counted, the report shows money, no payslip carries it | Fix in 059 first; test one slip on local |
| GRV structure row non-zero | Everyone pays it every month | Read the row's amount (Q2) |
| Manager changes mid-month | New manager can mark from the change onward; old marks stay with their author | Follows `reports_to` already |
| Employee leaves | Marks stay until the retention rule purges them | Counsel's ruling |
| A manager marks the whole team | HR sees it in the saved view | Look at the first two weeks |
| Shared phone, wrong person ticked | Undo same day; HR after | The reason line in the notice makes it visible quickly |
| Rule is not per day, or has its own free allowance | Wrong money | Read RED-02/04/05 (Q3) |

---

## Decisions only Surbhi can make

**Must know** (they block the spec):

| # | Question | My recommendation |
|---|---|---|
| Q1 | Red and Green Value never reach a slip today. Fix that in slice 059 before this ships? | **Yes, first.** Grooming then joins the same wiring. |
| Q2 | Is the GRV row in DTC's structure a non-zero fixed amount? May I ask HR to set it to ₹0? | **Set to ₹0.** The engine supplies the amount each month. |
| Q3 | "Works the same as the red mark rules": do DTC's **2 free reds** apply to grooming reds? Shared with ordinary reds, separate, or none? | **None — every marked day is charged.** You said "₹200 per day when the mark is on", and a separate line is clearer to the employee. If DTC's rule text says otherwise, that wins. |
| Q4 | Is "Junior" the `dtc_grade = Junior` field the rule set already uses? | **Yes.** It already prices ordinary reds at ₹100/₹200, so grooming uses the same table. I could not count DTC's Junior staff without the server. |
| Q5 | Who may mark: only the direct manager? A stand-in when away? HR? | **Direct manager only. No stand-in. HR may only remove.** HR was not there to see it. |
| Q6 | Contract staff: marked or not? | **Not**, matching the engine (no marks for Contract). Their tick is not shown. |
| Q7 | Cut-off: today only, N working days, or until the slip? | **Today only for the manager**, undo until midnight. HR may remove until the slip is submitted. |

**Should know:**

| # | Question | My recommendation |
|---|---|---|
| Q8 | Is the employee told, and may they dispute? | **Told the same day, always.** Dispute by speaking to the manager or HR; HR removes. A dispute button only if disputes become common. |
| Q9 | Reason or photo? | **One fixed reason, clothing only. No photo.** DTC to give the list. |
| Q10 | One red per day, whatever happens? | **Yes, at most one grooming red a day.** |
| Q11 | Does it interact with late/early reds on the same day? | **No.** It is a separate line, counted separately, never doubled on a special day. |
| Q12 | HR approval before it counts? | **No.** It slows the daily habit; the notice and the HR view are the check. |
| Q13 | Does the employee see it on a month card? | **On that day in their Attendance month, and on the payslip.** Not on the Leave card, which is about leave. |

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| Q1–Q7 above | Surbhi | The spec |
| The text of RED-02, RED-04, RED-05 in DTC's rule document | Surbhi / DTC | Q3 and Q10 |
| The reason list in DTC's words, checked for religious dress | Surbhi, counsel | Release |
| Retention of a mark that fed pay | Surbhi with counsel | The purge rule |
| `01a` UX scan and `07` §1 DevOps first look | UX designer, DevOps | Design |

## Assumptions

- `[ASSUMPTION]` "BTC" means DTC.
- `[ASSUMPTION]` "Junior" means `dtc_grade = Junior`, and "200" is the Senior rate in the same table.
- `[ASSUMPTION]` DTC managers have portal logins and use the Attendance page on a phone (true for managers given logins in October; not checked per manager).
- `[ASSUMPTION]` A Frappe Notification can fire on a new `Grooming Mark` for the employee's user. Needs validation; standard behaviour.
- `[ASSUMPTION]` DTC's rule document is the source of truth if it disagrees with this brief.

## Kill criteria

- DTC's rule says grooming is judged monthly, not daily, or is handled outside payroll — stop; use the `Additional Salary` stopgap.
- After the first month, more than 25% of marks are removed, or one manager makes over half of all marks with complaints — pause marking and review the rule with DTC.
- Counsel says the reason list cannot be made safe — stop.

## Subtract pass — what I removed

- A rule-set field for a separate grooming rate: removed. The existing `mark_rates` table already holds ₹100 and ₹200.
- A separate free allowance setting for grooming: removed, unless Q3 says otherwise.
- A free-text note beside the reason: removed (privacy and religion risk).
- An "Ask to remove" button for the employee: moved to later.
- A branch-level grooming trend for the CXO: removed.
- A daily cap per manager: removed; the saved HR view does the job.
- HR approval step: removed.

---

## Surbhi's decisions, 22 Oct 2026

Her words: "The grooming red mark is a deduction as a fine of not grooming well. I mentioned earlier. If the manager has marked the grooming red on, then only this reduction happens for that day. Yes, it is the DTC grade of junior and senior that is used for evaluating the green red mark fine deduction amount. So in case the manager marks someone grooming red mark on some days, for every day that amount of deduction is accounted into."

| Question | Decision |
|---|---|
| What it is | A fine for not being groomed well. Deducted only for a day the manager has marked. |
| Rate | By the employee's `dtc_grade`: Junior Rs 100, Senior Rs 200 per marked day (Q4: YES, Junior means dtc_grade = Junior). |
| Free allowance (Q3) | **None.** Every marked day is charged ("for every day that amount of deduction is accounted"). The 2 free reds of RED-03 do not apply to grooming. |
| Still open | Q1 fix the slip gap (ALV-208) first; Q2 GRV structure row to Rs 0; Q5 who may mark (recommended: the direct manager only; HR removes only); Q6 Contract staff (recommended: not marked); Q7 cut-off (recommended: same day for the manager, HR until the slip is submitted); plus the should-know questions Q8-Q13 and the two legal points. |

## Surbhi's answers to the open grooming questions, 22 Oct 2026 ("Rest I go with your recommended answers")

- **Q1** Fix the missing red/green payslip lines first (ALV-208), then grooming: YES.
- **Q2** HR may set the Grooming Red Value (GRV) structure row to Rs 0: YES.
- **Q3** No free allowance for grooming (her earlier words): decided.
- **Q4** Junior means `dtc_grade = Junior`: decided.
- **Q5** Only the direct reporting manager marks; no stand-in; HR may only remove: YES.
- **Q6** Contract staff are not marked: YES.
- **Q7** Cut-off: same day for the manager; HR may remove until the slip is submitted: YES.
- **Q8-Q13** (employee told the same day naming who marked and why, with a way to dispute; one reason from a fixed list and no photo or free text; at most one grooming red a day; no HR approval step; the employee sees it on that day in their Attendance month): the brief's recommendations, YES.
- Legal points stay with counsel, through Surbhi: the reason list must not touch religious dress; retention of a pay input against counsel's erase rule.

## Change to Q5, 22 Oct 2026 (later)

Surbhi: "The HR may also mark as they are responsible for the organisation culture and discipline."

So **Q5 is now: the direct reporting manager AND HR may mark.** HR does not only remove. Defaults until she says otherwise (to confirm in the spec):
- HR may mark any employee inside the HR user's own scope (company and branch: the existing `permitted_employees()`), for any day in the current pay month until that month's slip is submitted (the manager is still same-day only).
- The record stores who marked and in what capacity (manager or HR), derived by the server and never typed (as `decided_as` does for attendance corrections).
- The HR monthly view (marks per marker per month) covers HR's own marks too, so the abuse guard applies to both.
- A person never marks themselves. HR may remove any mark in scope until the slip is submitted; a manager may undo only their own mark until midnight.

## Decisions 24 Oct 2026

**Recorded as decided (Surbhi):** the marks are fines under the Code on Wages. DTC runs the legal conditions (approved list of fineable acts, show cause, use of the money) in its own process. One mark per person per day. The month's total is deducted once, as one slip line. Rs 200 Senior, Rs 100 Junior. The marks are the fines register, and HR can export them. (This settles 01c Q-C1 in her favour; the 3% cap in SEC-10 still applies by law, and she has not said to remove it.)

**New request.** Her words: the mark *"means the person is not taking it seriously and should have some symbol on his profile about not following the organisation integrity. This mark is an indicator that HR must have a conversation with this person and after a clear action plan this mark can be removed."*

**Bad news first: a symbol that says "integrity" about a uniform is a statement about someone's character.** Integrity means honesty. Writing "does not follow organisation integrity" next to a person's name, for a missing badge, is out of proportion, and any later manager or a reference check could read it as "dishonest". That is the defamation and fairness risk. I am not a lawyer. ⚠ COMPLIANCE, owner Surbhi with counsel.

**Second: the fine and the flag must be two different things.** A fine is a register entry. It is cancelled only for error, wrong person or upheld show cause (01c PRIV-3), never after the slip. "Removed after an action plan" must clear the *flag*, not cancel the fines. Otherwise the register stops matching the payslips.

### Options

| | What | Verdict |
|---|---|---|
| **A (recommended)** | A **"Grooming: HR conversation due"** flag. It switches on when a person has **3 live marks in one calendar month** `[ASSUMPTION — her number]`. HR clears it by recording the conversation: date, who held it, and one action-plan item from a fixed list (e.g. *Wear full uniform every day · Second uniform issued · Name badge reissued*) plus a review date. The employee sees the plan. The flag clears; the fines stay. New marks after the clear start the count again. One small record (rung 5). | Meets her outcome: a visible prompt, a conversation, a clear path to removal. Neutral, factual words. |
| B | Her literal version: a red "Not following organisation integrity" symbol on the Employee profile, set by any mark, removed by HR | **No.** Wording as above. The Employee profile is read on many screens (org chart, directory), and at DTC per-doctype permission rows do not narrow a new field. It becomes a character record that drifts into appraisals (breaks PRIV-5). |
| C (smallest) | No flag. HR's saved view (PRIV-6, marker × person) shows anyone with 3+ marks; HR talks to them offline | Zero build. But no symbol, no recorded plan, no clear "removed" moment. Fails her outcome. |

**Who sees the flag (fits 01c §4):** the employee (own), their **current direct manager** (extends 01c's "today only" — the manager needs to know a plan exists), and HR in scope. Never colleagues, skip-level managers, the org chart, the directory, appraisals or owners by default. Not in any export except HR's.

**Retention:** the conversation record is closer to a disciplinary/performance record than a wage record, so counsel's "employment + 6 months, then erase" likely applies to it, separately from the fines register. Counsel to confirm.

### Questions for Surbhi

1. Option A, B or C? (Recommend A.)
2. Trigger: 3 marks in a calendar month — or another number? Or every mark?
3. Wording: "Grooming: HR conversation due" instead of "integrity" — agreed?
4. Does the conversation ever **waive** that month's fines (a fourth removal reason, only before the slip)? Recommend **no** — the flag clears, the fines stand.
5. Should owners (Org Structure Editor) see the flag? Recommend **no**.
6. Action plan: fixed list (recommended, no free text per 01c SEC-8) or a short note the employee can read?

## Decisions 24 Oct 2026 (3)

**Her words:** "It is for everyone: after 3 marks it stops, with a warning to HR / managers. If
this still doesn't stop the manager, they can raise a complaint to HR."

**Decided:** at most **3 grooming marks per person per calendar month**, for every marker
(manager and HR alike). The review flag rises on the **3rd** mark. A manager who reaches the
limit sees a warning and has no Mark button.

**Bad news first: the "raise it with HR" route must never add a fine.** Under the Code on
Wages a fine is capped at 3% of wages and needs a chance to show cause. A route that let HR
"approve a 4th mark" would be a fine over DTC's own limit, and for many staff over the legal
one. So the route asks for a **conversation**, never for money. I am not a lawyer.

**Two limits, whichever comes first.** The 3-mark rule is DTC's policy. The 3% stop (SEC-10)
is the law and stays, with its pricing back-stop. A Senior needs Basic of at least ₹20,000 for
3 marks (₹600) to fit under 3%; below that the 3% stop bites at mark 2. The flag rises at the
mark that **reaches either limit** (prototype v2's Y1 way). This replaces the "4th mark" rule
in spec §5.3 and AC-55.

### What the route is (reuse first)

| Piece | Reuse | What it does |
|---|---|---|
| Manager's warning | The limit-reached sentence on the Today card (v2) | "Rahul has had 3 grooming reds this month, the most allowed. HR has been told and will talk to Rahul. If it carries on, you can raise it with HR." Button: **Raise it with HR** |
| Where it is stored | The **"Ask HR" pattern already on the mark** (`asked_on`): two more fields on the mark that reached the limit, `raised_on` and `raised_by`, set by the server | No new doctype, no comment on the Employee profile (which the desk timeline shows widely, spec bad news 3) |
| What it says | One fixed reason, picked from the same reason list ("Still not in uniform"…). **No free text** | Nothing about health, family or religion can enter a notice |
| HR's side | The review flag goes back to **pending**; bell to HR in scope; a line on the review: "Ravi Kumar raised it again on 26 Oct: Still not in uniform" | HR talks to the person and records the outcome with the **same "Record the review" sheet**. That clears it. |
| Bounds | One raise per person per month. After it is answered, the button reads "Raised with HR on 26 Oct. HR recorded a review on 27 Oct." | At most two reviews a month; next month starts from zero |

**What HR can do:** talk to the person, record the review, and use DTC's own disciplinary
process outside Alvoraa. **HR cannot add marks beyond the limit** — "for everyone" includes HR.

**What the employee is told (fixed words):** on the 3rd mark, "This is your 3rd grooming red
this month, the most allowed. HR will talk to you about it." On a raise, "Ravi Kumar, your
manager, has asked HR to talk to you about grooming. This adds no fine." No reason text, no
note text.

**Stale "asked" states** (no scheduled job, no reminders):
- *Employee asked HR, not answered:* the Salary Slip submit check (already in spec §8) also
  refuses while a mark in the period is still "asked": "Rahul asked HR to look at the grooming
  red on 21 Oct. Keep or remove it first." A fine deducted with the dispute unread is the
  show-cause risk.
- *Manager raised, not answered:* it adds no money, so it does not block pay. It stays on HR's
  "Grooming review pending" list, oldest first, with its age, and carries into the next month
  (as the flag already does). It drops off if the person leaves or the manager changes.

### Options

| | What | Effort `[my estimate, engineer to confirm]` | Risks |
|---|---|---|---|
| **A (recommended)** | Two fields on the mark + one button + the flag rule above | Small: about a day with tests | Needs prototype v3 or her yes on these words (parity) |
| B | Frappe HR's standard **Employee Grievance** | Medium: it is desk-only and managers have no desk | A permanent "grievance against" record with free text; detached from the 3-mark rule; the character-record problem from option B earlier |
| C | No button. The warning says "If it carries on, speak to HR" | None | HR is already told at the limit, but there is no record that the manager asked again |

**Subtract pass:** removed an HR override, a free-text box, a reminder job and a separate
complaint list. Nothing else could go.

### Questions for Surbhi

1. Option A, B or C? (Recommend **A**.)
2. Does the 3-mark limit cover HR's own marks too? (Recommend **yes**, her "for everyone".)
3. Confirm HR can **never** add a 4th mark, even with a reason? (Recommend **confirm**.)
4. Is the employee told when the manager raises it, naming the manager? (Recommend **yes**.)
5. Should an unanswered "Ask HR" block that person's slip? (Recommend **yes**.)

