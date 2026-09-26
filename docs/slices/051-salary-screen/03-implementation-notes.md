# Slice 051 — the salary screen on the existing portal

Approved 2026-09-27. Four ideas taken out of the discarded redesign's Pay screen
and built into the portal Surbhi is keeping. Local only: not pushed, not merged.

## What changed

Two files.

**`alvoraa_portal/hr_api.py` — `_payslip_payload`, two keys.**
`year_to_date` and `gross_year_to_date`, read off the Salary Slip. Frappe HR's
payroll run works them out against the payroll period and stores them there.
Summing the slips the screen happens to list gives a different number for a
mid-year joiner, for anyone whose slips do not start in April, and for anyone
whose list is capped — and it would be the portal's number rather than
payroll's, which is the one a Form 16 agrees with.

**`public/js/ess/portal.js` — the SALARY block only.**

1. **Both pay figures.** The big number is `rounded_total`, the amount actually
   paid into the bank. `net_pay` is shown beside it, to the paisa, and only when
   the two really differ. The old screen drew `rounded_total || net_pay` and
   never said which — so on 555 of 800 PP Jewellers slips it showed one figure
   and the employee could not reconcile it with anything. Payroll's rounding is
   NOT touched here (ALV-90 stays open, by her decision on 2026-09-27); this
   makes the gap visible instead of hiding it.
2. **The year so far**, shown only when payroll worked one out. A confident ₹0
   would be worse than no line.
3. **A "Why?" control** on a deduction the server can explain, opening
   `pay_api.get_deduction_explanation` in the same drawer with a Back control.
4. **"Entered by hand"** — see the correction below.

## A correction to what was said before building

The "entered by hand" line was described to Surbhi as a fix for a payslip header
showing "Working days 0". **It is not.** `hand_entered` is a property of the
DEDUCTION, not the slip: it is what the server answers when the line has no
Attendance Deduction behind it because payroll typed the component in. So it is
part of the Why? view, not a separate change. Three changes were built, not four,
and nothing was dropped.

## Decisions worth keeping

- **The explanation is rendered exactly as the server sent it.** Not one
  sentence is rewritten, shortened or added. The wording lives in
  `pay_api._explanation` and a static check reads those strings to keep the
  false version of one of them out — that correcting the day does **not** undo
  the deduction. Rephrasing it on the client would walk straight round that
  check.
- **Whether a line gets a Why? is the server's answer, never a guess.** The
  payload carries `additional_salary` on a line it can explain and leaves the
  key off one it cannot. A component called "Late Coming Deduction" that HR
  typed by hand has no link.
- **Nothing is written on this path.** Opening the explanation creates no record
  about the person — no read receipt, no acknowledged flag, nothing inferred
  from closing it. This is why Back calls nothing and why the test counts the
  server calls.
- **Back re-draws the payslip already in hand.** No second call.

## Non-functional

| | |
|---|---|
| Performance | Neutral on load. One extra call, only when somebody taps Why?. Two extra numbers on a payload that already carried twenty |
| Security | Neutral. No new endpoint. `get_deduction_explanation` already existed, already ownership-checked, already in the 034 endpoint registry |
| Reliability | Improved. A failed explanation shows the refusal and keeps the Back control, so the drawer is never a dead end |
| Data integrity | Improved. The year figure is payroll's, not the portal's; the pay figures no longer hide a disagreement |
| Privacy | Neutral. Own record only, on every path |
| Maintainability | One block of one file. The explanation code is untouched |

## Tests

**`alvoraa_portal/tests/portal_salary_test.js`** — 17 assertions, the real page
in jsdom, driven through `openPayslip` the way a click does. Registered in
`scripts/run_dom_tests.js`; `EXPECTED_BROWSER_TESTS` 8 → 9.

**`alvoraa_portal/alvoraa_portal/tests/test_salary_screen_051.py`** — 5 tests.
The fixture stores a year-to-date that is deliberately NOT the sum of the slips,
so the file can tell reading from summing.

**Every new check was proved able to fail.** Five mutations, each reverted:

| Mutation | Result |
|---|---|
| Drop the exact-net line | 16 passed, 1 failed |
| Drop the year-so-far line | 16 passed, 1 failed |
| Put the Why? control on every line | 14 passed, 3 failed |
| Rewrite the server's correction sentence on the client | 16 passed, 1 failed |
| Sum the slips instead of reading the stored figure | 2 passed, 3 failed |

**Neighbours, all green on test048:** `test_payslips_payload_043` (13),
`test_pay_screen_043` (27), `test_why_sheet_043` (36 + 4),
`test_numbers_match_035` (6 + 7), `test_payslips_gate_043` (15). The whole DOM
suite: 9 files, 406 assertions, 0 failures.

**Static guards, all green:** `check_portal_handlers.js`,
`check_undefined_js.js`, `check_design_system.py`, `check_tag_balance.py`,
`check_app_integrity.py`.

**Still owed before a push:** one clean run of the full `alvoraa_portal` suite.

## Found while working, not fixed here

`scripts/check_api_paths.py` runs at `--max 2`, and the two unresolved paths it
tolerates are both `hrms.overrides.employee_payment_entry` — the Create Payment
button that the 31 July ERPNext sweep broke. Slice 050 restores them, and
`--max` should drop to 0 in that same commit.
