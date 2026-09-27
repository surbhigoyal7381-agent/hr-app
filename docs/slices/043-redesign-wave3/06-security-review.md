---
slice: 043-redesign-wave3
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-09-25
status: verification of 01c against the code on slice/043-redesign-wave3 @ 5f2b314
---

# Wave 3 — security and privacy verification

**Conflict of interest, said first.** I wrote `01c` for this wave and am marking my own
requirements. The `05-review.md` compliance table was written by the reviewer, not by me;
where I disagree with it I say so.

## Verdict in one line

**No Blocker. No P0.** Wave 3 is the strongest of the four on evidence quality — the Why?
sheet's static check is the only check in this repo that documents the hole it used to have
and pins it with a test. **One requirement is not met and nobody recorded it (SEC-5), and
one privacy requirement is contradicted by a payload nobody pinned (PRIV-2).**

## Requirement by requirement

| ID | Verdict | Evidence |
|---|---|---|
| SEC-1 | **met** | Registry test enumerates `pay_api.py`, `time_api.py` from `MODULES` |
| SEC-2 | **met, with the spec corrected** | `hr_api.py:1876-1877`: `@frappe.whitelist()` then `@requires_feature("payroll")`. The spec's demanded order would have broken every call — `frappe/__init__.py:465,483` — and the note explains why. Correct call |
| SEC-3 | **met** | `hr_api.ME_FIELDS:1853` and `_me_block:1857-1873`, built key by key on purpose. `tests/test_payslips_payload_043.py:77-108` populates the sensitive fields **first** and then asserts their absence recursively |
| SEC-4 | **met** | `pay_api._refuse:101-103`; `tests/test_why_sheet_043.py:277-298` asserts all four causes give one byte-identical sentence, in **one** test |
| SEC-5 | **NOT met, and not recorded anywhere** | `hr_api._deduction_rows:3115` still takes a raw `filters` dict and still reads with `ignore_permissions=True` (`:3121`, `:3128`). The requirement said change the signature to take an employee id it resolves itself. It has one caller today (`:3150`, the caller's own employee), so there is no live exposure — but this is the shape the requirement existed to remove, and neither `03` nor `05` lists it as outstanding. **P3, owner: engineer** |
| SEC-6 | **met** | `pay_api.get_deduction_explanation:155` takes an `additional_salary` link, never a deduction name; `_own_additional_salary:125-151` and `_own_deduction:106-122` both check ownership before reading, and the note explains why "hand entered" was the wrong answer for somebody else's line |
| SEC-7 | **met** | `hr_api.get_shift_types:2132-2200`: no `ignore_permissions`, Active Employee required, scope is the shift types in use in the caller's own company plus their own `default_shift`, and an empty scope returns `[]` rather than an unfiltered read |
| SEC-8 | **met** | `attendance_deduction.py:207-221` `manager_body()` — days only, no amount, no minutes, no leave type — and `:244-258` sends **one recipient per send**. All four rules present |
| SEC-9 | **not re-verified in this pass** | `03` section 21.4 says `_subject` is confirmed and on the risk register |
| SEC-10 | **met for `pay_api` / `time_api`** | Neither carries `ignore_permissions`; the registry test covers both |
| SEC-11 | **not met, declared** | `03` section 9: the two old endpoints are deliberately not retired until the screens replace them. **Intentional trade-off, correctly labelled.** While `submit_attendance_request` is callable, every reason guarantee has a hole beside it |
| SEC-12 | **met** | `hr_api._get_employee:254-262` filters `status = "Active"` |
| SEC-13 | **met** | The registry test bans module-level mutables by AST |
| SEC-14 | **met** | Per-endpoint early returns; `test_payslips_payload_043.py:110-114` |
| SEC-15 | **not re-verified in this pass** | |
| SEC-16 | **met** | Verified by running `scripts/check_js_translation_calls.py` in this pass: 246 calls, clean |
| PRIV-1 | **not re-verified in this pass** | |
| PRIV-2 | **NOT met** | See F1 |
| PRIV-3 | **partial** | The leave type is out of the manager's email (SEC-8). Not re-verified on every Wave 3 path |
| PRIV-4, PRIV-5 | **not re-verified in this pass** | |
| PRIV-6 | **met** | `pay_api._explanation:184-255` carries all seven elements; `test_why_sheet_043.py:349-389` asserts each, with **two rule fixtures**, so no element can be a hard-coded sentence |
| PRIV-7 | **partial, correctly** | `_accountable_contact:257-286` names nobody and says so. `test_why_sheet_043.py:539-560` asserts the rule really has no owner field, so the day somebody adds one the test tells them. **D-7 is still unanswered** |
| PRIV-8 | **met, and it is the best test in this repo** | `test_why_sheet_043.py:392-478` drives the remedy text from a correction approved **after** the deduction was submitted and asserts on the documents. `:479-537` is the static check, and it **keeps string literals in and says why the first version, which stripped them, made itself useless**. `test_the_check_reads_strings_and_not_just_code` pins that hole |
| PRIV-9 | **met at the minimum** | The contact line is never blank |
| PRIV-10 to PRIV-12 | **met** | Nothing written on the read path; no new store; no model client anywhere |

## Findings

**F1 · Major (P2) — the manager gets a report's per-day punch times.**
*Scenario:* Sandeep, a manager who holds no HR role, opens Team; `portal.js:2070` calls
`hr_api.get_team_late_list`. For each of his Active direct reports the payload carries
`detail` — a per-day list built at `hr_api.py:3196-3197` as `"09-12 Late 10:35"`, the
report's actual clock-in time. PRIV-2 says *no minute figures, on screen or in a payload*.
The comment at `:3202-3204` states that a manager never receives per-day punch times; it is
describing `recent` only, three lines below the code that sends them, and a reader will take
it as covering the whole function.

`01c` R7 offered to accept this **with the payload pinned by a test**. The acceptance was
never recorded and the pin was never written: the two tests that touch this endpoint
(`test_portal_security_010.py:552-566`, `test_late_minutes_017.py:786-791`) check for
`lwp_amount`, `explanation` and stray Employee fields. Neither looks at `detail`.

Either Surbhi accepts it in writing and a test pins `detail`, or `detail` comes out.

**F2 · Minor (P3) — `_deduction_rows` unchanged.** As in the table. One caller, own employee,
no live exposure. The correction is a signature change and about twenty lines.

**F3 · Minor (P4) — a clumsy true sentence.** With no owner set, `getting_it_put_back`
renders as *"Only your HR team - no individual is named on this rule yet can cancel a
deduction…"*. True, and hard to read. One wording pass when D-7 is answered.

## Residual risk

| # | Risk | Owner | Date | State |
|---|---|---|---|---|
| R3 | An automated deduction reaches pay with no human in the loop and no lawful-basis answer from counsel | Surbhi with counsel | question by 2026-10-15 | **open.** Wave 3 made it visible and contestable; it did not make it lawful |
| R4 | Attendance Deduction has no retention period and no legal-hold rule. It is decision-bearing about pay and is kept for ever | Security and privacy engineer with counsel | proposal 2026-10-15, rule 2026-12-15 | **open** |
| R7 | The manager's punch-time detail (F1) | Surbhi | **2026-10-10** | **not accepted** |
| R8 | The payslip PDF is 1–3 s of CPU per call. Own-only, but loopable by one signed-in employee | DevOps | before the Pay screen reaches a tenant | open |
| — | `notify_manager` may still be ticked on a live tenant, and the old single-body email cannot be un-sent | Surbhi | before this ships | a tenant action; it needs her word |
