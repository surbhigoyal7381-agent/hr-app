---
slice: 043-redesign-wave3
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-09-24
spec: 02-functional-spec.md revision 2
branch: slice/043-redesign-wave3, rebased onto slice/042-redesign-wave2
bench: own container hrlocal-043, own redis hrlocal-043-redis, own site test043. hrlocal-bench not used, no docker cp
status: **the three live defects, the shift-type scope, the Why? sheet AND the Time and Pay screens are built and tested.** Rebased onto `slice/042-redesign-wave2` at `f34e68f`, which now carries slice 044's scale fixtures and five performance commits. What is still NOT done is AC-18/19, retiring the two old endpoints - §13 says why, and it is deliberate
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
| **AC-1 to AC-5, AC-7 to AC-15, AC-20 to AC-25, AC-32 to AC-41, AC-44 to AC-51, AC-53 to AC-56** | **Not built.** These are the Time and Pay screens | ✗ — §9 |
| **AC-18, AC-19** (retire `get_attendance_calendar` and `submit_attendance_request`) | **NOT MET, deferred with a reason.** Their only callers are `hrms-employee.html`, the page every tenant is on today. The screens that replace them live on `/hrms-employee-next`, which is 404 on production behind two locks. Deleting the endpoints now takes a working calendar away from every customer and puts nothing in its place - which is what release gate 2 forbids. **What unblocks it:** the preview page becoming the real page; then the deletion is its own commit so a revert is one step, and it must carry the same test shape as Wave 2's `test_week_presence_retired_042.py` - a source walk with a positive control, plus a call-by-hand test. Recorded as not met on the review's F4, which agreed with the decision | **✗ not met, deliberately deferred** - §18, §21.3 |

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
| `bench run-tests --module …test_endpoint_entitlement` | **13 ran, OK** — it exercises `requires_feature` directly, which this slice changed, so it is the real pin for the new `message` argument |
| `bench run-tests --module …test_frame_api_034` (Wave 1's, unedited) | **33 ran, OK** |
| `bench run-tests --module …test_inbox_counts_034` (Wave 1's, unedited) | **17 + 2 ran, OK** |
| `bench run-tests --module …test_home_api_042` (Wave 2's, unedited) | **23 ran, OK** |
| `bench run-tests --module …test_inbox_parts_042` (Wave 2's, unedited) | **24 ran, OK** — matching Wave 2's own recorded number |
| `npm ci` then `node scripts/run_dom_tests.js` | **129 passed, 0 failed** — 8 + 12 + 82 + 27, and the same 3 files not run for Wave 1's recorded reasons. `jsdom` was not installed in this worktree, which is why the first attempt reported 4 failures that meant nothing |
| `node scripts/check_undefined_js.js` | undefined identifiers: none |
| `node scripts/check_portal_handlers.js` | all reachable and callable |

**A phantom failure I caused and caught.** One run of
`test_inbox_parts_042` reported **19 ran, 2 setUpClass errors**. It was not
reproducible: the next clean run gave 24 ran, OK. The cause was mine - I had a
backgrounded sweep still holding `test043` when I started that run, so two
`bench run-tests` were on one site at once. That is the exact thing this project
learned on 2026-09-10, arrived at again from the other direction. **Nothing of
Wave 2's was broken; I broke the measurement.** Every number above is from one
run at a time.

**The jsdom caveat, stated because it matters for the part not yet built.** The jsdom
harness is kinder than a real browser - its stub calls an error path `website.js` never
calls. This slice changed no JavaScript, so the 129 above are a regression check and
nothing more. When the Time and Pay screens exist, anything that depends on a failed
call being noticed must be proved with `scripts/browser_check_frame.js`, not jsdom.

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

---

# Part two — the screens, the rebase, and what the numbers actually say

Written after the second working session. Everything above stands; this part
adds what was built on top of it and corrects two things it claimed.

## 13. The rebase, and what came in

This branch was rebased onto `slice/042-redesign-wave2` again, at `f34e68f`.
**Ten commits came in** — slice 044's two scale fixtures and its measuring tool,
plus five performance commits on 042. The rebase replayed twelve commits with
**no conflict**: 042's one hunk in `hr_api.py` is near line 336 and mine are at
1,598 and beyond, exactly as their work-board row predicted.

| Came in | What it meant for Wave 3 |
|---|---|
| `call_cache.py` — a memo that lives for one call and dies in a `finally` | Used, not reinvented. `get_time` asks "which holiday list is this person on" twice — the days-off card and the weekly-off weekdays — so it opens one and closes it in a `finally` |
| `goals_api._pending_approvals_scope_query` is a subquery now | Read, and the rule behind it applied: no scope in this slice is a list of ids. Every read `time_api` makes is filtered to **one** employee id |
| `fixtures_scale_044.py`, sites `test044` (981 people) and `test044s` (20) | **Reused, not rebuilt.** Both screens measured on both |
| `measure_044.py` | Extended with two rows rather than copied |
| `test_scale_flatness_044.py` | Extended with four tests rather than copied |
| The rewritten budgets in `nfr-budget.md` | Followed: flatness is the gate, the count is a note, and both were measured rather than guessed |

Nothing of theirs is behind me and nothing of theirs was edited except by
addition — two lines in `measure_044._calls`, four test methods and an import in
`test_scale_flatness_044`, and one pinned set in `test_portal_split_034`.

## 14. What was built in part two, file by file

| File | Mechanism | Why |
|---|---|---|
| `alvoraa_portal/time_api.py` | **build** — new | The whole Time screen in one call. Own-record throughout, except the month calendar, which follows `attendance_correction._subject` — and which returns the month **and nothing else** when the subject is not the caller |
| `attendance_correction.py` | **extend**, three small things | `weekly_off` per day (AC-1), `grace_source` per day (AC-5), and the holiday list resolved the way payroll resolves it — see §16 finding 1 |
| `hr_api.py` — `_own_slips`, `_payslip_payload` | **extend** | One definition of "the caller's own slips" and one of "a payslip's payload", so the list, the payslip page and the Pay screen cannot drift |
| `hr_api.py` — `submit_leave_encashment` | **extend** | AC-55. See §16 finding 3 |
| `pay_api.py` — `get_pay` | **extend** | The Pay screen in one call |
| `public/js/ess/next-time.js`, `next-pay.js` | **build** — new static files | One file per panel, as Wave 2 established |
| `public/css/ess/next-time-pay.css` | **build** — new static file | Its own, so two waves do not meet in one stylesheet |
| `templates/includes/ess/parts/next-time.html`, `next-pay.html` | **build** — new parts | No Jinja, no template cache slot (AC-44) |
| `public/js/ess/next-frame.js` | **extend** — two keys | `openSheet` and `closeSheet` handed to a panel. The frame already had a sheet with a focus trap, Escape and focus return; a panel writing its own would be a second copy of that work |
| `www/hrms-employee-next.html`, `next/frame.html` | **extend** | Two parts pasted, one stylesheet and two scripts loaded with a `?v=` stamp |
| `tests/test_time_api_043.py`, `test_pay_screen_043.py`, `test_encashment_043.py` | **build** | |
| `alvoraa_portal/tests/next_time_pay_test.js` | **build** | The panels in jsdom |
| `scripts/browser_check_time_pay.js` | **build** | The panels in a REAL browser, which is where the things jsdom cannot answer get answered |

## 15. The numbers, measured on both fixture sites

**The gate is flatness, and it holds.** Steady state, 20 warm calls each, three
warm-ups, nothing written in between.

| Call · persona | test044s (20 people) | test044 (981 people) | Flat? |
|---|---|---|---|
| `get_time` · employee | **35 q**, p50 97 ms, p95 173 ms, 17,069 B | **35 q**, p50 75 ms, p95 128 ms, 17,069 B | yes |
| `get_time` · manager | **35 q**, p50 161 ms, p95 306 ms | **35 q**, p50 332 ms, p95 **656 ms** | queries yes, time no |
| `get_time` · store HR | **36 q**, p50 94 ms, p95 118 ms | **36 q**, p50 84 ms, p95 110 ms | yes |
| `get_time` · company HR | **35 q**, p50 75 ms, p95 101 ms | **35 q**, p50 127 ms, p95 157 ms | yes |
| `get_time` · System Manager | **32 q**, p50 66 ms, p95 99 ms | **32 q**, p50 129 ms, p95 217 ms | yes |
| `get_pay` · every persona | **2 q**, p50 3-10 ms, 317 B | **2 q**, p50 11-26 ms, 317 B | yes - **but this was the EMPTY screen. Superseded by §21** |

**Against the budgets.** `get_time` is 35 queries against the spec's §13 limit of
40, and 17 KB against its 40 KB. Payload bytes are identical at 20 people and at
981, which is the other half of the same property.

**`get_pay`'s "2 queries" was the empty path**, because the 044 fixture people had
no Salary Slips. The review's F3 is that §13's Pay budget was therefore backed by
nothing. **It is measured now - see §21, and the real number is 11.**

**The 656 ms was investigated after the review asked for it. It did not
reproduce, and the reason is in §21.** This table's manager row should be read
with that section beside it.

## 16. Findings from part two that were not in the spec

| # | Finding | State |
|---|---|---|
| 1 | **The month calendar and the days-off card read two different holiday lists.** `attendance_correction.month` read `Employee.holiday_list`; `hr_api._own_upcoming_holidays` reads the Holiday List Assignment, which is the list payroll and leave actually use (slice 035 moved it there after store staff were shown Head Office's holidays). One person, two lists on one screen, and the calendar's was the one payroll ignores | **Fixed.** The assignment wins, `Employee.holiday_list` is the fallback, so a tenant that only ever set the Employee field keeps exactly the calendar it had |
| 2 | **`get_pay` answered a Guest with an empty page instead of refusing.** Both a Guest and a signed-in person with no Employee record reach `_get_employee() -> None`. The request layer stops a real Guest, so nothing was exposed — but a soft answer behind a hard door is a door somebody removes later | **Fixed**, with the test that found it |
| 3 | **Leave encashment: I had half the diagnosis wrong.** `leave_period` genuinely crashes every claim. `currency` does **not** — it is `read_only` and `reqd`, so Frappe fills it from the site's Global Defaults before the mandatory check runs, and the claim was quietly stamped with the SITE's currency rather than the one the employee is paid in | **Both fixed**, and the notes, the docstring and the test now say the true thing. Found by a test that asserted a crash that does not happen |
| 4 | **Both panels re-parsed `_server_messages` off a rejection.** The frame's `api` has already consumed it and put the sentence on `err.message`. So every refusal fell through to the page error: a person who opened a month they may not see was told the page had broken | **Fixed.** Caught by the new DOM test, three assertions at once |
| 5 | **The sites volume hides the app's `public/` assets.** On my own container `sites/assets/alvoraa_portal` was a real directory holding one file from the image, not a link to the app — so no portal static file was served at all and the browser check found `window.NextTime` missing | **Worked around locally** with a symlink; no `bench build` was run. It is the same trap ALV-112 is about, and it is worth knowing that a *local* bench has it too |
| 6 | **A test fixture can hide itself.** `Attendance Deduction.validate` recomputes `deduction_days` from the violation rows, so a figure passed to `insert` is thrown away. The year table then summed to 0.0 and every assertion about it still passed, because 0 equals 0 | Fixed in the fixture, with the reason written beside it |

## 17. Guards broken on purpose in part two

| Guard removed | What went red |
|---|---|
| `weekly_off` forced to False in `_day` | **4** Python assertions (the state set, the two-way distinction, and two totals) |
| The weekly-off state dropped from the panel's `dayState` | **3** DOM assertions |
| The "it does not undo this deduction" line dropped from the Why? sheet | **1** DOM assertion |
| The false remedy written into `next-pay.js` | AC-58's static check fired — which **proves that check reaches the new JavaScript**, not only the Python |

The last one is the one worth having: AC-58(c) was written before any
JavaScript existed, so "it walks `public/js/ess`" was a claim until this.

## 18. What is still NOT built, and why

| Not built | ACs | Why |
|---|---|---|
| **Retiring `get_attendance_calendar` and `submit_attendance_request`** | AC-18, AC-19 | **Deliberate, and this is the honest reason.** Their only callers are `hrms-employee.html` — the page that is LIVE. The panels that replace them are on `/hrms-employee-next`, which is 404 on production by design (two locks: the `portal_preview` flag, then System Manager). Deleting the endpoints now takes a working calendar away from every tenant and puts nothing in its place, which is exactly what release gate 2 forbids. **What unblocks it: the preview page becoming the real page.** Then the deletion is its own commit and a revert is one step |
| The arithmetic line on the Why? sheet | AC-57 element 4 | D-3 unanswered. Unchanged from part one |
| A named accountable human | AC-60's full form | D-7 unanswered. The fail-closed fallback ships |
| Payroll rounding | — | **Untouched on purpose.** The Pay screen shows the rounded total as take-home *and* the exact net beside it, so the difference stays visible rather than being hidden behind a nicer screen |
| Automatic recomputation after a correction | AC-58 | It would move money with nobody involved |
| The Hindi fixture at 390 px, and 200% zoom | AC-41 (part) | English at 390 px in a real browser: proved. The Hindi fixture: **not run** |

## 19. Things I could not prove in part two

| Claim | Why not |
|---|---|
| Where a manager's extra ~250 ms of `get_time` goes at 981 people | SQL is 44 ms of it and no statement grows with headcount. The rest is outside SQL and I could not attribute it. **Named, not rounded off** |
| `get_pay`'s query count on a full Pay screen at scale | The 044 fixture people have no payslips, so the measured 2 queries are the empty path |
| AC-41 with the Hindi fixture, and at 200% zoom | Only English at 390 px was driven in a real browser |
| AC-54, a deduction dated in an already-paid month | Still no demo data. Unchanged from part one |
| AC-22's PDF in a tenant's own print format | `download_payslip` is unchanged and untested here; setting the format is a per-tenant action (release gate 3) |
| That the encashment AMOUNT is right | Valuing one needs a real payroll run. What is proved is that a claim now saves, with the right period and the employee's own currency |
| That no other developer is in these files on another machine | The work board is per-machine. A check, not a guarantee |

## 20. The seven dimensions, re-assessed against part two's code

| Dimension | Verdict | One line |
|---|---|---|
| **Performance** | **improves** | Time was 35–40 queries across several calls; it is **one** call of 35, flat from 20 people to 981, 17 KB. One p95 is over the line and is named in §15 rather than smoothed |
| **Security** | **improves** | A Guest now gets a refusal from `get_pay` rather than a page. `time_api` and `pay_api` carry no `ignore_permissions` at all; the one payslip read that needs it lives in `hr_api`, behind an ownership check, where that pattern is declared and tested |
| **Reliability** | **neutral to improves** | A card that fails leaves the rest of the screen working. A refusal is a sentence rather than an error page — which was a real defect until the DOM test found it |
| **Scalability** | **improves** | Every read in `time_api` is filtered to one employee id; no scope is a list of ids; the year table is bounded by the financial year and says when it was capped |
| **Maintainability** | **improves** | One definition of the payslip payload and of "the caller's own slips". The panels hold no number and no day of the week, so a tenant changing a setting changes the screen and nobody has to remember to edit the copy |
| **Data integrity** | **neutral** | Nothing on any new path writes, asserted with a write-count spy on both screens — and the spy is proved able to see a write |
| **Compliance / privacy** | **improves** | A manager opening a report's month gets the month and nothing else — no leave balance, no rule, no pay. The Why? sheet tells a person a machine cut their pay, in the server's words, and creates no record of their having read it |

---

## 21. The two numbers the review sent back (2026-09-25)

`05-review.md` F3 and F2. Both are measured now rather than reasoned about.
Measured on my own container `hrlocal-r43` against the same two sites
(`test044`, 981 people; `test044s`, 20), same `measure_one`, 20 warm calls after
three warm-ups.

### 21.1 `get_pay`, measured on the FULL screen: **11 queries, flat**

F3 was right and the caveat in section 15 was honest, but a budget backed by the
empty path is still a budget backed by nothing.
`fixtures_scale_044.seed_payslips` now puts twelve submitted Salary Slips on each
of the five persona logins, each with eight earning rows and four deduction
rows - because the risk the reviewer named is not the count, it is `get_doc` on
a slip with a long salary structure, and `_payslip_payload` walks every child
row.

Only the five persona logins, not all 981 people: `get_pay` is an own-record
call, so a thousand other people's payslips would add build time and change no
number here.

| `get_pay` | 20 people | 981 people | flat? |
|---|---|---|---|
| employee | **11 q**, p50 28.8 ms, p95 40.7 ms, 4,465 B | **11 q**, p50 18.8 ms, p95 24.6 ms, 4,465 B | **yes** |
| manager | **11 q**, p50 17.6, p95 25.5, 4,459 B | **11 q**, p50 42.7, p95 55.7, 4,459 B | **yes** |
| store HR | **11 q**, p50 16.4, p95 47.6 | **11 q**, p50 41.1, p95 64.6 | **yes** |
| company HR | **11 q**, p50 11.5, p95 18.4 | **11 q**, p50 54.8, p95 77.3 | **yes** |
| System Manager | **11 q**, p50 17.4, p95 32.3 | **11 q**, p50 21.8, p95 36.9 | **yes** |

**11 queries against section 13's budget of 15, identical at both headcounts, and
the payload is byte-identical.** The reviewer's inferred "roughly 5-6 statements"
was low - the real figure is 11 - but the property that matters, that nothing in
it grows with the company, holds and is now measured instead of reasoned.

So section 13's Pay row reads **11 queries, measured**, not "2" and not "not
measured".

**Still not measured, and still named:** the payslip PDF download path.
`07-devops-inputs.md` flags it separately and this did not touch it.

### 21.2 The 656 ms: **it is measurement noise, not a persona and not headcount**

F2 asked for an hour of attribution and offered a hypothesis, marked as a guess:
`_may_review()` calls `frappe.has_permission`, and the three slow personas are
the three where it returns True.

The test is written down as `measure_044.attribute_time(shape)` so it can be run
again rather than described. It does four things: asks who `_may_review()`
actually returns True for, takes a baseline, times `_may_review()` on its own,
then re-measures with it stubbed True and stubbed False.

**The hypothesis is disproved, three ways.**

1. **The correlation does not hold.** `_may_review()` returns True for store HR,
   company HR and System Manager - and **False for the manager**, who was the
   slowest persona in section 15's table. The three slow personas and the three
   True personas are not the same three.
2. **The function is far too cheap.** Timed alone at 981 people: 2.6 ms and one
   query for the two who get False, and **0.0 ms and zero queries** for the three
   who get True - Frappe has it cached by then. It cannot account for a 170 ms
   gap.
3. **Stubbing it changes nothing.** Stub True and stub False run the *same number
   of statements* as each other, so they are exactly comparable, and they differ
   from each other by up to **166 per cent**.

**And the 2x itself did not reproduce.** Same method, same sites, same session:

| `get_time` p50 | 20 people | 981 people | ratio | section 15 said |
|---|---|---|---|---|
| employee | 76.6 ms | 78.5 ms | 1.0x | 0.8x |
| **manager** | 75.4 ms | 84.9 ms | **1.1x** | **2.1x** |
| store HR | 119.7 ms | 103.8 ms | 0.9x | 0.9x |
| company HR | 67.9 ms | 110.2 ms | 1.6x | 1.7x |
| **System Manager** | 105.6 ms | 62.1 ms | **0.6x** | **2.0x** |

No p95 anywhere near 656 ms. The manager's p50 at 981 came out at 84.9 ms
against section 15's 332 ms.

**The honest conclusion: the spread between runs that should be identical is as
large as the effect that was being attributed.** Between stub True and stub
False - two sweeps minutes apart, identical query counts - one persona's p50
moved from 46.0 ms to 122.2 ms. A local Docker container sharing a host with a
dozen other containers is not an instrument that can resolve a 2x difference in
sub-second wall-clock. The query count and the payload size can be trusted
because they are counted, not timed; the milliseconds cannot.

**What this does NOT mean.** It does not mean `get_time` is fast on a real
tenant, and it does not mean the 656 ms never happened - it did, on that run. It
means the number was never evidence of a persona problem or of a headcount
problem, and no code change is justified by it. **Nothing was capped and nothing
was cached to make the number go down.** The engineer refused that, the reviewer
agreed, and this session did not do it either.

**What is real, and is what the budget should watch:** `get_time` is 32-36
queries at twenty people and the same 32-36 at 981, with a byte-identical
payload. That is the property `nfr-budget.md` makes the gate, and it holds.

**What I would ask for before production**, and it is not this slice's job:
wall-clock budgets need to be measured somewhere quieter than a developer's
Docker host, or they will keep producing numbers nobody can act on. Owner:
`hrms-devops-engineer`, with a date. Until then section 13's wall-clock lines
should be read as indicative, and only the query and byte counts as gates.

### 21.3 AC-18 and AC-19 in the AC table

F4 asked that they be recorded as "not met, deferred with a reason" rather than
left looking met. Section 2's table now says exactly that. The decision itself is
unchanged and the reviewer agreed with it.

### 21.4 `_subject` - confirmed still true, and it belongs on the risk register

The review's F7, checked again on this branch and **still exactly as described**:

`attendance_correction._subject` is the whole control for opening another
person's month, and the check it makes is `_may_review()`, which is
`frappe.has_permission("Attendance Request", "submit")` - **a doctype-level
permission with no document and no company narrowing.** So anybody a tenant
grants that permission to can open **any** employee's month, in any company on
the site, including their punch times.

This session's measurement confirms the shape from the other side: on the
981-person fixture, spanning four companies, `_may_review()` returns True for
store HR, company HR **and** System Manager, with no company narrowing anywhere
in the call.

Wave 3 does not widen it - `get_time(employee=...)` returns strictly less than
`attendance_correction.month` already did, and
`TestSomebodyElsesMonthCarriesNothingElse` asserts that. `01c` SEC-9 names
`_subject` as the control on purpose. **Nothing was changed here**, as asked.

**For the risk register, in one line:** *whoever holds submit permission on
Attendance Request can open any employee's attendance month in any company on
the site; pre-existing, intended, narrowable by `permitted_employees()` in Wave
4 or 5 without changing anybody's screen who is correctly scoped today.*

### 21.5 F5, the browser check

See its own commit. Both halves were run: with the data seeded, **27 passed and
0 failed in a real browser - the first recorded run in which the Why? sheet's
seven assertions actually executed** - and with a user whose payslip has no
deduction line, exit 2.

### 21.6 The payslip rounding (F6) was not touched

Deliberately. Surbhi has not answered which figure the bank pays, and the
reviewer flagged that the answer changes the severity. No sentence was added to
the screen, because any sentence I could write there would be a guess about
money.

### 21.7 Two tests I found erroring, which I did not cause and did not fix

`bench --site test044f run-tests --module …test_scale_flatness_044`:
**15 ran, 13 passed, 2 errors.** Both are `get_pay`:

```
ERROR  test_get_pay_is_flat_for_a_plain_employee
ERROR  test_get_pay_is_flat_for_hr
frappe.exceptions.PermissionError: That payslip is not available.
```

**The cause is the site, not the code.** That sentence is `PAYSLIP_UNAVAILABLE`,
the payroll entitlement gate AC-30 added. `test044f` has no `payroll` in its
feature list; `test044` and `test044s` do. So these two tests pass where payroll
is sold and error where it is not, and `test044f` is the bare site the rest of
the flatness file is designed to run on.

**It is not mine.** My change to `fixtures_scale_044.py` adds functions and
deletes nothing — `git diff` shows zero removed lines — and I did not touch
`test_scale_flatness_044.py` at all. The other thirteen tests in the file,
including both positive controls, pass.

I have **not** fixed it, for two reasons. It is slice 044's test file and
another session may be in it; and the honest fix is a judgement I should not
make alone — either the test asserts its precondition and says so, or the bare
site gains the entitlement, and those are different decisions about what
`test044f` is for.

**An error is loud, so nothing is hiding.** But a test that passes or fails on
the site's *plan* is a test whose result is about configuration, and that is
worth one line in the follow-up. Owner: `hrms-test-automation-engineer`.

### 21.8 What is still NOT measured, said plainly

- **The payslip PDF path.** `07-devops-inputs.md` flags it separately; this did
  not touch it.
- **Wall-clock on anything quieter than a developer's Docker host.** See §21.2.
- **390 px, dark mode, 200 % zoom and the Hindi fixture.** Still not run, as the
  notes already said.
