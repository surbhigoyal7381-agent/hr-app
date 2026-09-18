# Slice 017 — the late-minutes figure. Impact analysis

Wave 0b item W1 from `docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md`
(detail in `appendix-c-time-pay.md`, F-1). Approved 2026-09-18 as the one Wave 0b item
to fix before the production release. Local only.

Branch `slice/017-late-minutes`, worktree `.claude/worktrees/017-late-minutes`, cut from
local `dev` at `c83b37d`.

---

## 1. What the number is doing today

One line of code causes it. Two helpers take the **same cache dictionary** and store
**different facts under the same key**:

| Helper | Lives in | Stores under `cache[shift]` |
|---|---|---|
| `_shift_minutes` | `attendance_analytics.py` | how **long** the shift lasts, in minutes |
| `_shift_start` | `attendance_correction.py` | what time the shift **begins**, in minutes past midnight |

In `attendance_correction._day`, `_shift_minutes` is called first (line 500) and
`_shift_start` second (line 516). The second finds the key already there and returns the
**length** as if it were the start time.

PP Jewellers' two shifts both run **09:30–18:30**. Start = 570. Length = 540. So the
screen judges every day from **09:00** — half an hour before anyone is due.

### Verified on the local `ppj.localhost` copy (read-only, nothing written)

| Measure | Rows |
|---|---|
| Submitted Attendance rows with a punch-in | 22,570 |
| Rows whose late-minutes figure is wrong | **22,570 — every one** |
| Days the screen calls late **today** | **22,570 — every punched day** |
| Days truly past the shift start (no grace) | 8,280 |
| Days past the Shift Type's 15-minute grace | 2,477 |
| Days past the pay rule's 60-minute threshold | 594 |
| Frappe HR's own `late_entry` flag says | 2,531 |

Sample: `2026-09-05`, PPJ-0040 — screen says **11 minutes late**, the truth is **0**. The
employee arrived before the shift started.

This also corrupts the drawn day: `shift_starts`/`shift_ends` are reported as
**09:00–18:00** on a 09:30–18:30 shift, so the bar and the punch times disagree on screen.

**Night shifts are worse.** A 22:00–06:00 shift has a length of 480 minutes, which reads
as 08:00, so clocking in at 22:05 is reported as **14 hours late**. No tenant runs a night
shift today, so nothing is live — but the fix must not assume that.

## 2. Does the wrong figure drive the pay deduction? **No — and this corrects the brief.**

I checked the whole path before changing anything.

The late-coming rule (`hrms/hrms/alvoraa_late_rules/late_rules.py`, `violations_for`)
reads the Shift Type's `start_time` **through its own cache**, which holds the row and has
no collision. It has always measured from the true 09:30.

Proof from the stored data on `ppj.localhost`: 341 `Late Arrival` violations with
**minimum 61 minutes** and maximum 120, against a 60-minute threshold. Judged from 09:00
the count would be in the thousands. 212 submitted deductions, of which one reached pay,
₹548.39 total.

**So the money is right and the screen is wrong.** That is still a serious defect, because
the screen and the deduction card sit on the same page: the calendar says 27 late days in
August and the deduction card says 4 counted violations. The employee cannot reconcile
the money with what the app shows them, and neither can the manager. It is a
defensibility problem rather than an overcharge — worth saying plainly before release.

**No screen figure feeds pay.** `_totals` → `late_days` is returned in the `month()`
payload and read only by the page. Nothing else consumes it.

## 3. Every caller, and every screen that shows a late figure

There are **three different definitions of "late"** in the product today.

| # | Definition | Where it is computed | Who shows it | State |
|---|---|---|---|---|
| 1 | Frappe HR's `late_entry` yes/no — `in_time > shift_start + Shift Type grace` | `shift_type.py:280` (upstream) | `attendance_analytics.py` (`late` counts, :280, :602), `org_figures.py` (:164), `hrms/alvoraa_hr_core/attendance_score.py` (:179/:183, punctuality %) | **Correct.** Reads the flag, not the arithmetic. Untouched. |
| 2 | `late_by_mins` — minutes past shift start, **no grace** | `attendance_correction._day` :516–527 | Time screen calendar, day detail, month `late_days` total; page `hrms-employee.html` :6246, :6367 | **Broken.** This slice fixes it. |
| 3 | Deduction violation — `minutes > rule.late_threshold_minutes` (60) | `late_rules.violations_for` :75 | `hr_api.get_my_attendance_deductions`, `hr_api.get_team_late_list`; page :7046, :7061 | **Correct.** Pinned by new tests, not changed. |

Greps run: `late_by_mins`, `late_minutes`, `late_entry`, `_shift_start`, `_shift_minutes`,
`shift_cache`, `violations_for`, `current_week_projection`, `late_threshold`, `grace`,
`deduction` across `alvoraa_portal`, `hrms`, `alvoraa_goals`, `demo`, `scripts`.

Callers of the two functions I change:
- `_shift_minutes` — `attendance_analytics.py:283`, `:589`, `attendance_correction.py:500`.
  Each passes its own cache. Return value and signature unchanged.
- `_shift_start` — `attendance_correction.py:516` only. Signature unchanged.
- `org_figures.py` imports only `TOLERANCE_KEY`/`DEFAULT_TOLERANCE_MINS`. Not affected.
- `scripts/check_attendance_strip.js` uses fixed sample data, not the server. Not affected.

## 4. Persona impact

| Persona | Before | After |
|---|---|---|
| **Employee** | Every punched day marked late; August shows 27 late days against 4 counted violations; the drawn shift bar is half an hour out | Late only when actually after the shift start, by the real number of minutes; the bar matches the shift |
| **HR Manager** | Cannot defend the deduction — the portal contradicts it | Portal and rule tell a consistent story about *when* the person arrived |
| **CXO** | Org figures and the attendance score already use Frappe's flag, so leadership numbers were never wrong | Unchanged. No leadership figure moves. |

No permission, visibility or field changes. Nobody sees anything they could not see before.

## 5. Edge cases checked

| Case | Behaviour after the fix |
|---|---|
| **No shift on the day and no default shift** | `late_by_mins` 0, no bar. Fail safe — no shift means no expectation. Pinned. |
| **Shift name that does not exist** | Both helpers return `None`, no lateness. Pinned. |
| **Night shift crossing midnight** | Judged from 22:00, not 08:00. Length arithmetic already handled midnight. Pinned. |
| **Punch after midnight on a night shift** | Gives a negative, clamped to 0. Under-reports rather than accuses. Unchanged behaviour, safe direction. |
| **Missing punch / no `in_time`** | No late figure at all. Unchanged. |
| **Half day** | `late_by_mins` still computed (it is about arrival); the deduction rule counts only `status = "Present"`, unchanged. |
| **Holiday / weekly off** | No Attendance row, so no late figure. Unchanged. |
| **Approved correction / regularisation** | Frappe HR's Attendance Request rewrites the Attendance row; the screen recomputes from the rewritten `in_time`. Whether an approved correction should erase lateness is **not decided** — see §7. Unchanged by this slice. |
| **Employee's own timezone** | Unchanged. `in_time` and `start_time` are both read as site-local wall-clock, as before. Out of scope and not made worse. |
| **Multi-company** | Shift Type is per company and read by name. No cross-company read added. |
| **Grace per organisation** | The Shift Type grace (15 min) and the pay rule threshold (60 min) are both per-organisation and **both ignored** by this figure. See §7. |

## 6. Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **improves** | The cache now holds the row, so a shift is read **once** instead of twice. `attendance_correction.month` drops one query per distinct shift (was 15 queries, the slowest call on the Time page). |
| **Security** | **neutral** | No permission path, no new endpoint, no `ignore_permissions`. The `attendance_analytics.py` CEILINGS entry stays at 0. |
| **Reliability** | **improves** | A whole class of mistake is gone: nothing derived is stored under the shift's key, so no helper can read another's answer. Missing shift still fails safe. |
| **Scalability** | **improves** | One fewer query per shift, on the page's heaviest call. |
| **Maintainability** | **improves** | One fact cached, each helper does its own sum. The comment names the bug so nobody re-introduces it. |
| **Data integrity** | **improves** | No stored data is wrong — the figure is computed per request — so there is nothing to backfill. 22,570 rows start reading correctly the moment the code ships. |
| **Compliance / privacy** | **improves** | An employee was being told a wrong fact about their own conduct next to a pay deduction. Correcting it is the point. No new personal data is read, logged or shown. |

## 7. The one thing I will not guess: which grace the screen should use

**This is the open decision and I am not coding it.** Pay is not a place to guess.

Fixing the arithmetic moves PPJ's Time screen from **22,570** late days to **8,280**. The
number that actually costs money is **594**. So after this fix the screen is *correct* but
still not *reconcilable* with the deduction card next to it.

Three defensible rules, all per organisation, all already configured:

| Option | Rule | PPJ late days | Argument for | Argument against |
|---|---|---|---|---|
| **A** | No grace — exact minutes past shift start (today's intent) | 8,280 | Factual. "How late, measured rather than taken on trust" — the existing comment. | Reconciles with nothing. Calls a 1-minute arrival late next to a card that says 4. |
| **B** | Shift Type `late_entry_grace_period` (15 min) | 2,477 | The literal wording of decision **Q-a** (2026-09-14). Matches Frappe HR's own `late_entry` flag, so the Time screen agrees with the analytics screen, org figures and the attendance score. | Still flags 2,477 days that cost nothing. |
| **C** | Attendance Deduction Rule `late_threshold_minutes` (60 min) | 594 | The number next to money becomes the number that *moves* money. Calendar and deduction card finally agree. | Two employees on different rules get different definitions of "late". Says nothing about people no rule covers. |

**My recommendation: C for the count, A for the detail.** Keep `late_by_mins` as the true
minutes past shift start on the day itself — that is a fact and people should see it — and
make the **month total and the "late" chip** count only days past the threshold that
actually counts towards a deduction, falling back to the Shift Type grace (B) for anyone no
rule covers. Then the calendar says 4 and the deduction card says 4, and the day detail
still shows "17 minutes late" without claiming it cost anything.

Related open questions already on the board, unchanged by this slice: **Q20 / F-7**
("60 or more" wording versus `> 60` in code) and **H-1** (chip for 4 minutes?). Also
undecided and out of scope: **whether an approved attendance correction should erase
lateness** — today it does, because the rule recomputes from the rewritten `in_time`.

## 8. Two further defects found on the way — reported, not fixed

Out of this slice's scope ("fix only the late-minutes figure and what it feeds"), but they
belong in the record:

1. **Early exit past midnight creates a false violation** —
   `late_rules.violations_for` :82. For a day shift ending 18:30, an `out_time` of 00:30
   reads as **1,080 minutes early exit**, a violation worth a quarter day. Not live: no
   tenant has a day shift with post-midnight punches today. This is in the **pay** path and
   should be fixed before anyone works past midnight.
2. **The projection an employee sees can differ from what is deducted** (F-11).
   `hr_api._late_rule_for` picks a rule by company and default shift, while
   `late_rules.covered_employees` also applies exempt grades, `process_from` and date of
   joining. An employee on an exempt grade is shown projected days that will never be
   taken. Worse, `hr_api.get_team_late_list` looks up **the first team member's rule and
   applies it to everyone**, so a mixed-shift team is projected against one person's rule.
   `get_team_late_list` is **claimed by slice 010 on the work board**, so I have not touched
   it, and the fix needs the §7 decision anyway.

## 9. Parallel-work check

**What came in.** My branch is cut from local `dev` at `c83b37d`, which is **33 commits
ahead of `origin/dev`** — the other session's slice 014 (check-in security, nginx), 015
(repo hygiene) and 016 (portal API permissions) fixes, plus their reviews and notes. I read
the incoming log. None of it touches attendance, shifts, late minutes or the deduction
path. Newest five: `c83b37d` plan label, `245e6b2` slice 016 notes, `b04356e` slice 016
reviews, `77ed55c` pin tests scan, `0daaf8c` customer name removal.

**Another session's uncommitted work in the main checkout** — not mine, not staged, not
touched: `.claude/context/ux-learnings.md`, `backlog/KPI_AUTOMATION_BACKLOG.md`,
`docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md`,
`hrms/.../alvoraa_position.py`, deleted `OBJECTIVES_KPI_REQUIREMENTS.md`, and a number of
untracked files and folders.

**Files I change, and who else is in them.**

| File | Hot? | Who else | Plan |
|---|---|---|---|
| `alvoraa_portal/.../attendance_analytics.py` | shared | Slice 012 claims `_org_roles`, `person`, `filter_options` — already in `dev` | **Split.** I touch only `_shift_minutes` and add `_shift_row`. Different part of the file. |
| `alvoraa_portal/.../attendance_correction.py` | shared | Slice 010 claims `decide` — already in `dev` | **Split.** I touch only `_shift_start` and one import line. |
| `alvoraa_portal/.../tests/test_late_minutes_017.py` | new | nobody | New file. |
| `docs/slices/017-late-minutes/*` | new | nobody | New folder. |

**Not touched, by instruction:** `field_checkin.py`, `portal_api.py`,
`controllers/delivery_assignment.py`, `deploy/nginx.conf`, `.github/workflows/ci.yml`,
`hrms-employee.html`, `hooks.py`, `patches.txt`, any DocType JSON.

**Tests pinning what I touch.** `test_attendance_correction.py` already covers
`late_by_mins`, `shift_starts` and `shift_ends` — but its fixture shift is **09:00–18:00**,
where the start (540) and the length (540) are the same number, so the collision is
invisible to it. **That coincidence is why this bug shipped and survived.** Every fixture in
the new file uses a shift whose start and length differ, so a bad merge cannot bring the
bug back without CI failing.

**Not merging into local `dev`** — the other session is mid-release. The work stays on
`slice/017-late-minutes` for the user to sequence.
