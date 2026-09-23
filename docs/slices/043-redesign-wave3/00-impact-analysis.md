---
slice: 043-redesign-wave3
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-09-24
spec: 02-functional-spec.md revision 2 (commit c302fcc, replayed as 71e4199 after the rebase)
branch: slice/043-redesign-wave3, rebased onto slice/042-redesign-wave2
bench: own container hrlocal-043, own redis hrlocal-043-redis, own site test043. hrlocal-bench not used, no docker cp
---

# Wave 3 — Time and Pay: impact analysis and strategy

## 0. Where this sits, and the order it must land in

**043 sits on 042 sits on 034.** `git merge-base --is-ancestor` proves 034's tip is an
ancestor of 042's tip, and this branch was rebased onto 042 before a line was written.
So they must reach `dev` in that order: **034, then 042, then 043.** Pushing 043 first
would carry 78 commits of other people's slices under my name.

The rebase replayed four docs-only commits cleanly. Nothing conflicted, because this
branch had no source file in it yet.

### What came in from 034 and 042, read before building

`git diff 8718f27..HEAD` over the app code — 112 files, the parts that matter to me:

| Came in | From | What it means for Wave 3 |
|---|---|---|
| `ess_parts.py` + `ess_part()` Jinja global, `hooks.py:59` | 034 (OPS-31, `a2439e3`) | Markup parts cost no template cache slot. Time and Pay get their own part files for free. **No new Jinja include** — AC-44 |
| `frame_api.py` (318 lines), `FRAME_KEYS`, `ME_FIELDS` | 034 | The fixed-key-list discipline AC-6 extends to `get_payslips` |
| `inbox_api.py` (921), `home_api.py` (691), `staff_api.py` (190) | 034, 042 | **Extend these. Do not recreate.** Wave 3 adds `pay_api.py` only because nothing there owns pay |
| `test_frame_endpoint_registry_034.py` | 034 | Every whitelisted function in the listed modules needs a registry row naming a Guest, wrong-persona and scope test **in the same commit** |
| `hr_api.py` +218/−… — `get_week_presence` **deleted** | 042 | Confirms the retire-an-endpoint pattern Wave 3 repeats for AC-18 |
| `attendance_correction.py` +79 | 034 | The month payload I will extend later in this slice |
| `access.py` +65 (`log_refusal`) | 034 | Reuse for refusals; do not write a second one |
| `scripts/browser_check_frame.js` | 034 | The real-browser check. jsdom is kinder than a browser — anything that depends on a failed call being noticed is proved here, not in jsdom |
| `scripts/check_app_integrity.py` | on `dev` already | Runs before every commit |

Nothing of theirs is behind me and nothing of theirs is edited by the first four commits.

## 1. Functional impact

### Cross-module reach

| App | Touched | How |
|---|---|---|
| `alvoraa_portal` | **Yes** | `hr_api.py` — `get_payslips` (gate + payload), `get_shift_types` (scope). New `pay_api.py` for the Why? sheet |
| `hrms` (our fork) | **Yes, one function** | `attendance_deduction.notify()` — ALV-113. No schema change, no rule-logic change |
| `erpnext` | Read only | Salary Slip, Salary Detail, Additional Salary, Shift Type, Shift Assignment |
| `frappe` | Read only | `frappe.sendmail`, the print pipeline |
| `alvoraa_goals` | **Not touched** | |
| `alvox_compensation` | **Not touched**, not installed | |

### Callers of everything I change — grepped, not assumed

| Function | Callers found | Consequence |
|---|---|---|
| `hr_api.get_payslips` | `portal.js` (the old Pay panel) and the mobile app's API list — checked below | Adding a gate changes behaviour on a tenant **without** payroll only. On PP Jewellers, which has payroll, nothing changes |
| `hr_api.get_shift_types` | `portal.js` shift-change modal | The list gets shorter for a caller in a company that uses fewer shift types. That is the fix |
| `attendance_deduction.notify` | `on_submit` only | One call site. The employee's body is unchanged byte for byte |
| `_get_employee()` | many, inside `hr_api` | I do **not** change it. I stop `get_payslips` from returning its result whole |

### Persona impact

| | CXO / owner | HR Manager (Kamal, Priya) | Employee (Rahul) | Manager (Sandeep) | Asha (no Employee record) |
|---|---|---|---|---|---|
| `get_payslips` gate | No change on a payroll tenant; refused on one without | same | same | same | already refused (no Employee row) |
| `get_payslips` payload | **Stops receiving their own DOB, gender, phone, branch, reporting manager** on the Pay screen | same | same | same | — |
| Deduction email | — | — | **No change — their body is byte-identical** | **Stops learning which leave type their report used** | — |
| `get_shift_types` | Sees the types their own company uses | same | same | same | **Refused** — no Active Employee record |
| Why? sheet | Own deduction only | Own only | Own only | Own only | Refused |

**The one persona regression to watch:** a manager's email gets shorter. That is a
narrowing, and release gate 4 says HR must be told rather than surprised.

### HRMS domain impact

Attendance (the deduction chain, read only), leaves (the Leave Type name leaves one
email), payroll (the payslip list and the deduction explanation), org structure
(untouched — `_subject` and `_may_review` are reused, not changed).

## 2. Non-functional verdict, dimension by dimension

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **neutral to improves** | The gate is a decorator on a call that already runs. The payload shrinks by ~7 fields per call. The shift-type scope adds **one** query (a distinct over Shift Assignment) and removes an unbounded read. The Why? sheet is a new call, budgeted at ≤ 4 queries and ≤ 8 KB |
| **Security** | **improves** | An entitlement that was decorative becomes real (AC-30). An `ignore_permissions=True` read of every Shift Type gains a caller check and loses the flag (AC-52). Refusals stay byte-identical across four causes (AC-31) |
| **Reliability** | **neutral** | Two `sendmail` calls instead of one, both inside the existing `try/except` that logs and never raises. If the manager's send fails the employee's has already gone |
| **Scalability** | **improves slightly** | `get_shift_types` stops returning every Shift Type in a tenant. At 1,000 employees the Why? sheet is bounded by one week's violations |
| **Maintainability** | **improves** | The email body is built by two named functions instead of one string reused for two audiences. `pay_api.py` keeps pay logic out of the 3,000-line `hr_api.py` |
| **Data integrity** | **neutral** | Nothing is written on any path this slice adds. AC-61 asserts the write count around a full Why? call |
| **Compliance / privacy** | **improves, and this is the point** | Three live leaks close: a whole Employee row on the screen people email to banks, a leave type in a manager's inbox, and an entitlement claim that was false. The Why? sheet tells a person their pay was cut by a machine — and tells them the truth about the remedy |

### Where each SEC and PRIV item is met

| Item | Met by |
|---|---|
| SEC-2 (real gate, no patched gate, decorator order) | Commit 1; the test calls the real `has_feature`, and a static check fails any test that patches it |
| SEC-3 (fixed key list on `get_payslips`) | Commit 2; a six-key `me` block, plus a static check that no Wave 3 module passes a `_get_employee()` result into a payload |
| SEC-4 (four causes, one message) | Commit 1 + the Why? endpoint; one test asserting all four together |
| SEC-5 (`_deduction_rows` stops taking a raw filters dict) | The Why? commit |
| SEC-7 (shift types: Active Employee, no `ignore_permissions`, real scope) | Commit 4, D-6's recommendation |
| SEC-8 (the email: separate bodies, separate sends, days only, no leave type) | Commit 3 |
| PRIV-6, 7, 8, 9, 10 | The Why? commit — AC-57 to AC-61 |

### Where each adopted OPS item is met

| Item | Met by |
|---|---|
| OPS-W3-2 (Wave 1 to dev first; OPS-31 not to production before ALV-112 on main) | Stated in §0 and in the report. **I do not push anything** |
| OPS-W3-6 (measure the payslip PDF before production) | A release gate, not an acceptance check. Not built, not measured here |
| OPS-W3-9 (an image rollback restores the old email) | Recorded in the notes so release day knows to check the template after a rollback |
| OPS-W3-11, 12 (query counts and payload **bytes** asserted) | The Why? sheet's budget test asserts both |

## 3. Parallel-work check

| File I will change | Hot? | Who else is in it | Plan |
|---|---|---|---|
| `alvoraa_portal/alvoraa_portal/hr_api.py` | **Yes** — 042 deleted `get_week_presence` from it; 035 added `_ledger_leave_balances` | 042 (already merged under me by the rebase). No other live row on the board touches it | **Sequence.** I am rebased onto 042, so their deletion is already in my tree. I touch only `get_payslips` and `get_shift_types`, neither of which 042 went near |
| `hrms/.../attendance_deduction.py` | No | Nobody on the board. `git log origin/dev --since="7 days ago"` shows no commit in `alvoraa_late_rules` since slice 017 | Free |
| `pay_api.py` (new) | No | Nobody | Free |
| `tests/test_frame_endpoint_registry_034.py` | **Yes** — Wave 1 owns it, 042 added rows | 034, 042 | **Split.** I add registry rows only. I do not change its rules, and 034's and 042's rows stay untouched |
| New test files (`*_043.py`), `tests/fixtures_043.py` | No | Nobody | Free. **Their own company, stores and people** — shared fixtures have cost four slices time |

**Other developers:** `git log origin/dev --since="7 days ago"` over these paths shows
only slices 017, 035, 039, 040 and 041, none of them in `get_payslips`, `get_shift_types`
or `notify()`. I have no way to see another machine, so this is stated as a check I ran,
not a guarantee.

### The test that pins each existing feature I touch

| Existing behaviour | Pin |
|---|---|
| A payroll tenant can still list its own payslips | `test_payslips_gate_043.TestAPayrollTenantStillWorks` |
| The employee's deduction email body | `test_deduction_email_043` compares it **byte for byte** to the stored `explanation`, so a later change to the manager's body cannot drift it |
| `get_team_late_list` carries days and never `lwp_amount` | AC-16's pin, asserted on the field list |
| The shift-change modal still gets the caller's own shift | `test_shift_types_043.test_my_own_default_shift_is_always_offered` |

## 4. Strategy, and what I recommend

**Build order — defects before screens, smallest first.** Each of the first four is
independent of every screen, so each can be reviewed, reverted and released on its own.

1. **ALV-114 — the payroll gate on `get_payslips`** (one decorator, above
   `@frappe.whitelist()`), with the four-cause refusal test and the no-patched-gate
   static check. The spec ranks this P1 because it makes W1D-01's entitlement claim false.
2. **The `get_payslips` payload** — a six-key `me` block, plus the static check that no
   Wave 3 module hands a `_get_employee()` row to a payload. Separate commit from the
   gate: one is an entitlement fix and one is a minimisation fix, and they should be
   revertible apart.
3. **ALV-113 — the deduction email.** Two bodies, two sends, days only, no leave type.
   Asserted on the **rendered body per recipient**, with a Sick Leave fixture.
4. **AC-52 — `get_shift_types`.** Active Employee required, `ignore_permissions` dropped,
   and D-6's scope: the types in use in the caller's own company through Shift Assignment,
   plus their own `default_shift`.
5. **The Why? sheet** (`pay_api.py`) — the own-only read, and the truthful wording.

### Trade-offs and consequences I am naming now, not when asked

- **Two `sendmail` calls cost one more outbound message per deduction.** At PP Jewellers'
  ~212 deductions a quarter with `notify_manager` on, that is ~212 extra emails a quarter.
  Negligible, and the alternative — one send with two bodies — does not exist in Frappe.
- **The shift-type scope can return an empty list** for a company that has never made a
  Shift Assignment. The caller's own `default_shift` is added for exactly that case; if
  they have neither, the modal must say so rather than show an empty dropdown. **No scope
  helper returns an empty filter dict** — an empty scope means an empty list, never
  "everything".
- **The gate changes an error where there was data.** On a tenant without payroll the
  old `get_payslips` returned slips. After this it refuses with the same sentence as a
  missing slip. That is deliberate (AC-31): a refusal that varies tells the caller what
  the tenant bought.
- **D-3, D-6 and D-7 are unanswered.** I use the fail-closed default for each and say so:
  D-3 → the Why? sheet ships **without** the arithmetic line; D-6 → the Shift Assignment
  scope, which is the recommendation and which I will confirm exists in the data; D-7 →
  AC-60's fallback wording, never a blank and never a hint that a person reviewed the case.
- **No automatic recomputation** (AC-58). A correction approved after a submitted
  deduction leaves the deduction alone, and the screen says so. Building the other thing
  would let one approval move money with nobody involved.
- **Payroll rounding is not touched.** 555 of 800 PPJ slips print a net the bank does not
  pay. That is Surbhi's decision and papering over it on the Pay screen would hide it.

### What I am not building, and why

| Not built | Why |
|---|---|
| Payroll rounding | Undecided. Current behaviour left alone, and the report says so |
| Automatic recomputation of a deduction after a correction | AC-58 — it would move money with nobody involved |
| Anything needing D-3's, D-6's or D-7's unanswered halves | Fail-closed default, named in the notes |
| "Who is away · next two weeks" | 009 design decision 3 — approved leave **is** the reason |
| Form 16, salary advance limits and instalments | No data source (§12) |
| A per-person lateness ranking | §18.4 refuses it in writing |

## 5. What could go wrong, and how I would know

| Risk | How it shows | Guard |
|---|---|---|
| The gate test passes because the test patched the gate | Every entitlement test green, the gate never exercised | A static check fails the build on any patch of `has_feature`, `requires_feature` or `enabled_features` in this slice's tests |
| The email test passes because it asserts on the wrong string | Green, leak still sending — **this already happened in revision 1 of the spec** | Assert on the **rendered body per recipient**, and break the guard deliberately to prove it goes red |
| The shift-type scope quietly becomes "everything" | A two-company fixture still shows company B's night shift | A test with two companies, asserting absence |
| A refusal varies by cause | A slip name can be used to probe | All four causes compared in **one** assertion |
| An assertion that can never fail | Green forever | Every new guard is broken once on purpose and the failure recorded |
