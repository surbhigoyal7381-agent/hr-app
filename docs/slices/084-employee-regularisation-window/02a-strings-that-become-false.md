# The twelve strings that became false (updated at build, 19 Nov 2026)

First written as six by the UX designer, grown to nine by the analyst, eleven by the
engineer's impact analysis, and **twelve at build** by a repo-wide grep. Every one was read
in the source on `dev` at `a57764c4` / `fd658eff`. Match on the quoted text, not the line
number, because lines move.

**All twelve are fixed in the SAME commit as the code** (DevOps OPS-14): `b1d57b0a` on branch
`slice/084-employee-window` (items 1-11 and the JS-test comment in the follow-up commit
`d9519e89`). If the code lands without them, the product says the opposite of what it does,
which is the fault that started this slice.

| # | Where | What it said | Now |
|---|---|---|---|
| 1 | `templates/includes/ess/parts/org-settings.html` (manager hint) | "It does not limit HR, and it does not limit an employee asking about their own day" | Clause removed. Says the employee's own day is "the separate setting above" |
| 2 | `attendance_correction.py` in `month()` | "Never applied to somebody's own day: neither setting may narrow what a person asks about their own attendance" | Rewritten: the manager switch never applies to an own day; the employee window is read below |
| 3 | `attendance_correction.py` in `month()` | "Only a MANAGER filing for somebody else is bound by the window. Their own month is not" | Rewritten: two windows, one key in the payload |
| 4 | `attendance_correction.py`, comment above `MANAGER_ON_BEHALF_KEY` | "An employee raising their OWN day ... is not bounded by it either: narrowing ... was never asked for" | Rewritten: not bounded by THIS window; has its own key |
| 5 | `public/js/ess/portal.js`, day detail | "This day is outside the window a manager can file within" (shown to an employee the moment the server sends their own boundary) | The manager branch now needs `!d.is_self`; an employee has their own sentence |
| 6 | `public/js/ess/portal.js`, comment above `acOutsideWindow` | "Null means no window binds this caller - their own month, or HR" | Rewritten |
| 7 | `tests/test_attendance_correction.py`, docstring of `test_an_employees_own_old_day_is_not_touched_by_the_window` | "Narrowing what a person may ask about their own attendance was never asked for" | Test renamed `..._by_the_manager_window`; docstring says the manager window does not bind an own day |
| 8 | `hr_api.py`, comment above the blank-value branch | "No other numeric setting takes a blank, so this is spelt out for the one key" | Says two keys |
| 9 | `attendance_correction.py`, comment above `can_request_from` | "One value, not a flag per day" | Rewritten: one boundary per month, plus a flag per own day |
| **10** | `tests/test_attendance_correction.py`, docstring of `test_neither_setting_narrows_an_employees_own_day` | "Neither setting may take away what somebody asks about their own attendance" | Test renamed `test_the_manager_settings_leave_an_employees_own_day_alone`; docstring says MANAGER settings |
| **11** | The new employee hint, written during design: "It does not limit HR" | False for an HR Manager raising their own day (bound, Gate 3 C3) | **"It does not limit what HR does for other people."** (Surbhi, Gate: question 2) |
| **12** | `alvoraa_portal/tests/portal_correction_test.js`, comment before the "my own month" block | "Narrowing what an employee may ask about their OWN attendance would be a regression, so this half is pinned too" | **New at build.** Now says only that an own day goes to the ordinary endpoint |

## The grep, and what it found

Run on 19 Nov 2026 in the worktree `.claude/worktrees/084-employee-window` (branch
`slice/084-employee-window`, on `fd658eff`), over `*.py *.js *.html *.md *.json *.csv *.txt`,
excluding `node_modules`, `.git`, `.claude`:

`does not limit | not bounded | their own month | neither setting | never asked for | a manager can file within | take away what somebody asks | narrow what a person | narrowing what`

After the fix, every remaining hit in product text, comments and tests was read:

- `org-settings.html` employee hint and manager hint: **true** (HR-for-others, and the manager window).
- `attendance_correction.py` new comments saying an own month is "bound": true.
- Others (`joiner_public.py`, `grooming.py`, `fixtures_079.py`, `test_scale_flatness_044.py`, `test_time_api_043.py`, `next-time.js`, `portal_salary_test.js`) matched the loose phrases `never asked for` or `their own month` in unrelated sentences: **not about this setting**.
- `docs/slices/0xx` hits (060, 043, 045, 066, 078 and others) are **history**, not product text, and were left alone.

## Not searched, and who must

- **The DTC user manual** is a Claude Doc outside the repo. **Nobody has searched it.** It may
  quote the old hint ("it does not limit an employee asking about their own day") or describe
  the manager window as applying to everyone. It does not block release (nothing changes for
  DTC while the setting is blank). It **blocks the first number set at DTC.** One person opens
  it and searches the same phrases, plus `neither setting` and `take away what somebody asks`.
- Desk help text and other apps: only the `alvoraa_portal` and `hrms` trees in this worktree
  were grepped. Any help text stored in a database record is **not checked**.
- "Twelve" is the count found by this grep on this date. It is a floor until the manual and
  stored help text have been searched.
