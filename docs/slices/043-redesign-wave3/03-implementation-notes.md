---
slice: 043-redesign-wave3
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-09-24
spec: 02-functional-spec.md revision 2
branch: slice/043-redesign-wave3, rebased onto slice/042-redesign-wave2
bench: own container hrlocal-043, own redis hrlocal-043-redis, own site test043. hrlocal-bench not used, no docker cp
status: **the three live defects, the shift-type scope and the Why? sheet are built and tested. The Time and Pay SCREENS are not built.** §9 says exactly what is missing
---

# Wave 3 — what was built, and what was not

## 0. Where this sits

**043 sits on 042 sits on 034.** This branch was rebased onto
`slice/042-redesign-wave2` before a line of code was written; `git merge-base
--is-ancestor` confirms 034's tip is an ancestor of 042's. **They must reach `dev` in
that order: 034, then 042, then 043.** Nothing here has been pushed, merged into `dev`,
or put on any server.

## 1. What was built, file by file

| File | Mechanism | Why |
|---|---|---|
| `alvoraa_portal/subscription.py` | **extend** — `requires_feature(name, message=None)` | One optional argument. "Payroll is not included in your plan." and "That payslip is not available." are different sentences, so a caller could tell a tenant without payroll from a slip that is not theirs. Four causes need one sentence, which is only worth anything if it is the same sentence |
| `alvoraa_portal/hr_api.py` — `get_payslips` | **configure** — one decorator | The gate that was missing (ALV-114) |
| `alvoraa_portal/hr_api.py` — `PAYSLIP_UNAVAILABLE`, `ME_FIELDS`, `_me_block` | **build**, small | One refusal sentence in one place; the six-key `me` block replacing a whole Employee row |
| `alvoraa_portal/hr_api.py` — `get_shift_types` | **build** — replaced the body | Active Employee required, `ignore_permissions` gone, scope from Shift Assignment |
| `alvoraa_portal/hr_api.py` — `get_payslip`'s `lines()` | **extend** | Returns the `additional_salary` link on the lines that have one (AC-26) |
| `alvoraa_portal/pay_api.py` | **build** — new, 240 lines | The Why? sheet. New rather than added to the 3,000-line `hr_api.py`, because this is the one module in the product whose whole job is explaining an automated decision, and it should be readable on its own |
| `hrms/.../attendance_deduction.py` — `notify`, `manager_body` | **extend** — one function split into two | ALV-113. No schema change, no rule-logic change |
| `tests/fixtures_043.py` | **build** | This slice's own company, stores and people |
| `tests/test_payslips_gate_043.py`, `test_payslips_payload_043.py`, `test_shift_types_043.py`, `test_why_sheet_043.py` | **build** | |
| `hrms/.../tests/test_deduction_email_043.py` | **build** | Its own company and people, tagged S043E |
| `tests/test_frame_endpoint_registry_034.py` | **extend** — two lines | `pay_api.py` added to `MODULES`, one registry row. Wave 1's and Wave 2's rows untouched |

**Six commits, each independent and revertible on its own.**

## 2. The acceptance criteria, and how each is met

| AC | How | State |
|---|---|---|
| **AC-6** | Six-key `me` block on `get_payslips`; a static walk of the syntax tree fails any Wave 3 function that puts an Employee row in a dict | ✓ |
| **AC-26** | `get_payslip`'s `lines()` adds `additional_salary` only where set | ✓ |
| **AC-27** | Every figure read from the stored record. A test edits the rule and proves the stored figure does not move | ✓ |
| **AC-28** | Somebody else's line refuses with the payslip sentence | ✓ |
| **AC-29** | `{"hand_entered": True}` when the caller's own line has nothing behind it | ✓ |
| **AC-30** | The gate, called for real through the site config, never patched. A static check fails any test in this slice that patches it | ✓, with a correction — see §4 |
| **AC-31** | Four causes, one sentence, one assertion, on all three payslip endpoints **and** the Why? endpoint | ✓ |
| **AC-42** | `pay_api.get_deduction_explanation` in the registry with Guest, wrong-persona and scope tests, in the same commit | ✓ |
| **AC-43** | `pay_api.py` has no `ignore_permissions`, no `global`, no module-level mutable state; a static check asserts it | ✓ |
| **AC-52** | Active Employee required; `ignore_permissions` gone; scope from Shift Assignment plus own `default_shift`; two-company fixture proves absence | ✓ |
| **AC-57** | All seven elements, asserted against **two** rule fixtures | ✓ except element 4 — see §5 (D-3) |
| **AC-58** | Document-level test driven from a correction approved after submission; static check keeps the false sentence out | ✓ |
| **AC-59** | The five blocks, word for word, one message each | ✓ with D-7's fallback in the last two |
| **AC-60** | Fallback wording, never blank, never implying review; a test asserts the rule still has no owner field | ✓ |
| **AC-61** | Write count around two full calls, plus a static check for every write call | ✓ |
| **AC-16, AC-17** | Separate bodies, separate sends, days only, no leave type — asserted on the rendered body per recipient against a Sick Leave fixture | ✓ |
| **AC-1 to AC-5, AC-7 to AC-15, AC-18 to AC-25, AC-32 to AC-41, AC-44 to AC-51, AC-53 to AC-56** | **Not built.** These are the Time and Pay screens | ✗ — §9 |

## 3. The seven non-functional dimensions, against the code actually written

| Dimension | Before → after | One line |
|---|---|---|
| **Performance** | **neutral** | The gate is a decorator on a call that already ran. `get_payslips`'s payload lost ~7 fields. `get_shift_types` gained two small queries (a distinct over Shift Assignment, one `get_value`) and lost an unbounded table read. The Why? sheet is **4 queries**: the Additional Salary row, the deduction row, the deduction document, the company's currency — the rule comes from `get_cached_doc`. Under the ≤ 4 budget |
| **Security** | **improves** | An entitlement that was decorative is real. An `ignore_permissions` read of every Shift Type has a caller check and no flag. Four refusal causes are one sentence on four endpoints |
| **Reliability** | **neutral** | Two `sendmail` calls instead of one, each in its own try/except, so one failing send cannot stop the other. The employee's goes first |
| **Scalability** | **improves slightly** | `get_shift_types` is bounded by the caller's company. The Why? sheet is bounded by one week's violations. Nothing added loops over employees |
| **Maintainability** | **improves** | The manager's body is a named function, not a string reused for two audiences. Pay logic is in its own module. One refusal sentence in one constant |
| **Data integrity** | **neutral** | Nothing on any new path writes. Asserted, not promised |
| **Compliance / privacy** | **improves, and it is the point of the slice** | Three live leaks closed; the fourth (five older endpoints) found, named and pinned. An employee is told, truthfully, that a machine cut their pay |

## 4. Two places the spec was wrong, and what was done

### AC-30(c) — the decorator order would have broken the endpoint

AC-30(c) asks for `@requires_feature("payroll")` to sit **textually above**
`@frappe.whitelist()`. Written that way the endpoint stops working **for everybody, on
every tenant**.

`frappe.whitelist()` does `whitelisted.add(fn)` on the object it is handed
(`frappe/__init__.py:465`), and `is_whitelisted` tests the object the module name
resolves to (`:483`). Put the gate outermost and the module name resolves to a wrapper
that was never added, so every call is refused with "You are not permitted to access
this resource."

**What was built:** `@frappe.whitelist()` then `@requires_feature(...)` — byte for byte
the order `get_payslip` and `download_payslip` already use, which is what the AC cites
as the thing to match. The check asserts what the requirement is about: the gate is on
all three, it names payroll, and **all three are still in `frappe.whitelisted`** — a
test that would have caught the broken version, because a gate that unregisters the
endpoint refuses everybody and looks like a working gate to a test that only asserts
"it refused".

### AC-28 and a uniform "hand entered" answer cannot both be true

The first version returned `{"hand_entered": True}` for anything it could not resolve,
including somebody else's line — uniform, and it looked right. AC-28 says a line
belonging to another person must give the **same refusal** as a line that does not
exist, and "hand entered" is not a refusal; it is an answer about a document, and it
tells the caller the id is real.

**What was built:** ownership is checked on the Additional Salary first and refuses.
`hand_entered` now means exactly one thing — this line is yours, and payroll typed it in.
The test that asserted the opposite went red, which is how the conflict was found.

## 5. The unanswered decisions, and the fail-closed default used for each

| Decision | Default built | What changes when it is answered |
|---|---|---|
| **D-3** — is base ÷ calendar days the right daily wage? | **The arithmetic line is not on the sheet.** The payload carries the inputs and the outcome — violations, which were free, the per-violation days, the computed days, the rounding and where the days went — and **no sentence asserting the daily-wage method**. AC-57 element 4 is the one element not met, deliberately | Add one sentence built from `rule.daily_wage_basis`. No structural change |
| **D-6** — how is `get_shift_types` scoped? | **The recommendation, built:** shift types in use in the caller's own company through submitted Shift Assignments, plus their own `default_shift`. Confirmed in the data: `Shift Type` has no `company` field, `Shift Assignment` does | One function body |
| **D-7** — where does the accountable human's name live? | **The fallback.** And the spec's `[UNVERIFIED]` is now **verified**: there is nowhere to read a name from. `Attendance Deduction Rule` has no owner field; HR Settings has no HR-contact field; a tenant's `hr_email` becomes an HR Manager **login** during provisioning, not a contact record | `_accountable_contact` is the only function that changes. A test asserts the rule still has no owner field, so the day somebody adds one it says to revisit the wording |
| **D-2, D-4** | Not reached — they are Pay-screen decisions and the screen is not built | |
| **D-8** | Not built, by design. It is its own slice | |

## 6. Findings this slice turned up that were not in the spec

| # | Finding | State |
|---|---|---|
| 1 | **Five endpoints, not one, hand the whole Employee row to the browser**: `get_portal_context`, `get_employee_dashboard`, `get_manager_dashboard`, `get_expense_claims`, `get_checkin_status`. Each carries date of birth, gender, phone number, branch and reporting manager. A hand grep found three; the syntax walk found all five | **Pinned as declared debt**, not fixed. All five ARE read by the live screens, so trimming them changes working pages and needs its own impact analysis. A sixth fails the test |
| 2 | AC-30(c)'s decorator order would break the endpoint | Corrected, §4 |
| 3 | AC-28 and a uniform "hand entered" answer conflict | Corrected, §4 |
| 4 | There is **no per-site HR contact setting anywhere** in the product | D-7's `[UNVERIFIED]` resolved; the fallback says so plainly |
| 5 | `late_rules.covered_employees` keeps only employees with an **Active Shift Assignment for the rule's shift type**. A fixture without one makes `_process_week` iterate nobody — so a test of the skip passes whatever the skip does | Found by breaking the guard; a coverage assertion now sits above AC-58's document test |

## 7. Three guards were broken on purpose, because a green test that cannot go red is not a pass

| Guard removed | What went red |
|---|---|
| The payroll gate on `get_payslips` | 4 assertions: "PermissionError not raised", "get_payslips did not refuse", "None != 'payroll'", and the one-sentence check |
| The six-key `me` block, row put back | 5 assertions, including the payload printed with `date_of_birth`, `gender` and the phone number in it |
| The email: both people sent one body | 3 assertions: the leave type present, the stored explanation present, the two bodies equal |
| `get_shift_types` put back to its old body | **8** assertions |
| The false remedy put back into the Why? sheet | 2 assertions — **only 1 the first time**, which found a hole in the static check (§8) |
| `late_rules`'s `docstatus == 1` skip disabled | AC-58's document test — **nothing, the first time**, which found finding 5 (§6) |

**Two of those six found a defect in the test rather than confirming the code.** That is
the whole reason for doing it.

## 8. Three checks that were wrong before they were right

| Check | Wrong how | Now |
|---|---|---|
| "no test patches the gate" | Fired on its own docstring; then on a genuine `has_feature()` call in a file whose test method is named `..._patches_the_gate`; then on its own proving test, because the name match `"patch" in name` caught `_patch_targets` | Walks the syntax tree and matches `…patch(…)` or `…patch.object(…)` exactly. Two tests prove it sees a real patch and does not fire on a real call |
| "the false remedy is nowhere" | Stripped string literals out of Python before searching — borrowed from the `ignore_permissions` check, where prose is the false positive. Here the wording **is** a string literal, so putting the false sentence back left it **green** | Strips comments, keeps strings. `pay_api` never quotes the false sentence, not even to say it is false. A test writes the sentence to a temporary file and proves the reader finds it |
| AC-58's document test | Could not fail — the fixture employee was not covered by the rule | A coverage assertion sits above it |

## 9. What was NOT built, and why

**The Time and Pay screens are not built.** This slice delivered the server side: the
three live defects, the shift-type scope, and the Why? sheet's endpoint and wording.

| Not built | Which ACs | Why |
|---|---|---|
| Time · Days, the month calendar, day sheet, shift card, days off ahead | AC-1 to AC-5, AC-10, AC-45 to AC-51 | Not reached. Needs `attendance_correction.month` extended with `Holiday.weekly_off`, a `time_api.py`, a markup part, a stylesheet and a script |
| Time · Leave, Time · Late rule | AC-12 to AC-15 | Not reached |
| Fixing a day from the calendar | AC-7 to AC-9 | Not reached |
| Retiring `get_attendance_calendar` and `submit_attendance_request` | AC-18, AC-19 | **Deliberately not done yet.** Release gate 2 says the deletion ships in its own commit so a rollback is one step, and the panels that replace them do not exist yet. Deleting them now would take a working screen away and put nothing in its place |
| The Pay screen, year to date, the payslip PDF format, the comparison line | AC-22 to AC-25, AC-39 | Not reached. `get_payslip` now carries the link the sheet needs; nothing draws it |
| Leave encashment fix | AC-55 | Not reached |
| Every-state wording, 390 px, Hindi fixture | AC-32 to AC-41 | Not reached — they are screen checks |
| Payload byte budgets, skeleton timing | §13, AC-32 | Not measured. There is no screen to measure |
| **Payroll rounding** | — | **Deliberately untouched.** 555 of 800 PP Jewellers slips print a net the bank does not pay. That is an open decision, and hiding it behind a nicer Pay screen would make it harder to see, not easier |
| **Automatic recomputation after a correction** | AC-58 | **Deliberately not built.** It would let one approval move money with nobody involved, on a decision that already has too little human involvement |

## 10. Things I could not prove

| Claim | Why not |
|---|---|
| The Why? sheet renders correctly in a real browser | There is no sheet yet. When it exists, the jsdom harness is **not** enough — its stub calls an error path `website.js` never calls, so anything depending on a failed call being noticed must go through `scripts/browser_check_frame.js` |
| AC-54, a deduction dated in an already-paid month | The spec marks it `[UNVERIFIED]` and no demo data exists for it. Still unverified |
| The payload and query budgets in §13 | No screen to measure |
| That no other developer is in these files on another machine | The work board is per-machine; `git log origin/dev --since="7 days ago"` over these paths shows nobody, which is a check, not a guarantee |
| The `notify_manager` tick was turned off on the two client tenants | That is a tenant action and needs the user's word. **The leak is still live on any tenant with `notify_manager` on until this ships** |

## 11. Commands run, and what they said

| Command | Result |
|---|---|
| `git rebase slice/042-redesign-wave2` | clean, 4 docs commits replayed |
| `docker run` ×2 + `bench new-site test043 --install-app …` | site up with frappe, erpnext, hrms, alvoraa_goals, alvoraa_portal. First attempt failed on the db root password — the shared MariaDB's is `root`, not the usual one |
| `python scripts/check_app_integrity.py` | **638 checks, OK** — run before every commit. It caught one bad import (`from hrms.alvoraa_late_rules import late_rules`) that `run-tests` does not |
| `bench run-tests --module …test_payslips_gate_043` | **15 ran, OK** (after 3 real failures and 3 wrong versions of one static check) |
| `bench run-tests --module …test_payslips_payload_043` | **12 ran, OK** (after 1 failure — it found four more leaky endpoints than the hand grep did) |
| `bench run-tests --module …test_deduction_email_043` | **13 ran, OK** (after 2 real failures: the violation type enum, and a fixture whose violation date collided with the week start) |
| `bench run-tests --module …test_shift_types_043` | **15 ran, OK** first time |
| `bench run-tests --module …test_why_sheet_043` | **36 + 4 ran, OK** (after 2 failures that found the AC-28 conflict, 1 that found a draft-vs-submitted fixture bug, and 1 syntax error) |
| `bench run-tests --module …test_late_rules` (unedited, Wave 0b's) | **5 ran, OK** |
| `bench run-tests --module …test_frame_endpoint_registry_034` (Wave 1's) | **8 ran, OK** |
| `bench run-tests --module …test_opt_in_features` | **8 + 11 ran, OK** — the pin for `subscription.py` |

One `bench run-tests` at a time, on my own container and site. `hrlocal-bench` untouched.
No `docker cp` — the worktree reaches the container through a bind mount, and the two
config files were written with `docker exec -i … bash -c 'cat > …'`.

## 12. Known gaps and shortcuts, labelled

| # | Thing | Label | What removes it |
|---|---|---|---|
| 1 | The Time and Pay screens are not built | **intentional trade-off** | The rest of Wave 3 |
| 2 | Five older endpoints still hand out the whole Employee row | **dangerous debt — escalating now.** Every load of the portal's home, dashboard, expenses and check-in screens carries a person's date of birth, gender and phone number to the browser. It is live today on both client tenants, and the first client goes live in the first week of October | Its own small slice: trim the five, with the JS change each needs. Pinned so it cannot grow |
| 3 | `AC-57` element 4, the arithmetic line, is absent | **acceptable simplification** | D-3 answered |
| 4 | Nobody is named as accountable for a deduction | **temporary debt** | D-7 answered. One field on the rule, one function changed |
| 5 | The two old endpoints are not retired | **intentional trade-off** | The screens that replace them, then their own deletion commit (release gate 2) |
| 6 | The Salary Slip fixture skips `validate()` | **acceptable simplification** | Nothing in this slice calculates a slip; building a real structure, assignment and payroll period per fixture would make the fixture the thing most likely to break |
| 7 | Tests were run per module, not as a whole-app suite | **acceptable simplification** | The whole `alvoraa_portal` suite takes hours on one site, and one run at a time is Wave 1's lesson |
| 8 | `notify_manager` is still on wherever it was | **dangerous debt until the release** | A one-tick tenant action available today, for a leak that cannot be un-sent. It needs the user's word |

**What I would fix with more time, honestly:** finding 2. It is a bigger live leak than
the one this slice was written to fix, it affects more screens, and it has a go-live date
against it.
