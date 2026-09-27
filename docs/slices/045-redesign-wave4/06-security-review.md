---
slice: 045-redesign-wave4
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-09-25
status: verification of 01c against the code on slice/045-redesign-wave4 @ b5d892b
---

# Wave 4 — security and privacy verification

**Conflict of interest, said first.** I wrote `01c` for this wave, including SEC-18 and
SEC-19, and I am now marking them. SEC-18 is the one where a second pair of eyes matters,
because I am the person who wrote both the requirement and the judgement that it is not met.

## Verdict in one line

**No Blocker. No P0. Three requirements are recorded as met and are not** — SEC-18 in the
implementation notes, and SEC-10 and SEC-13 by a static check that does not reach the two
modules they are about. SEC-19, the audit field, **is** met and is the best control in the
wave.

## The three that are recorded as met and are not

### 1 · SEC-18 — "eleven UI rows are eleven server checks"

`03` section 8 records: *"eleven rows enforced server side and callable by hand."*
The test class is called `TestTheElevenRowsCalledByHand`.

**What is actually there.** `team_api.ACTION_MATRIX:71-83` is the matrix as data;
`allowed():90-110` reads it in one place; `may():235-267` derives the relationship from the
database and refuses identically whatever the cause. All of that is good, and the section
really is derived: `relationship():270-296` asks `reports_to` at the moment of the question,
and no endpoint takes a `section` or `basis` argument.

**What is missing.** `team_api.may` has **no caller outside `team_api` itself and its own
tests.** I grepped the three apps. The payload builder calls `actions_for()`; nothing else
calls `may()`. So what the eleven rows control is **which buttons the payload carries** —
and a control absent from the payload is a screen decision, not a permission.

*Scenario:* Priya, HR Manager, covers a store. Someone in that store is not her direct
report, so `approve_leave` is `False` on the covered column and the button is absent. If she
is the named `leave_approver` on that person's application, `inbox_api._part_leave_approvals`
(`inbox_api.py:372-389`) still lists it and the existing approval path still decides it.
Nothing consults the matrix. The same is true of `set_goals`, `see_scorecard` and
`cancel_deduction`: each is enforced — or not — by its own older rule in `goals_api`,
`hr_api` or `attendance_correction`.

**This is not necessarily wrong behaviour.** It may be entirely right that a named leave
approver can approve. What is wrong is the **claim**. The matrix is a UX convention with a
central helper; the requirement said eleven server checks and the test name says they were
called by hand. They were not: `team_api.may` was.

**What I would do.** Not bolt `may()` onto eleven endpoints in a hurry. Instead: (a) correct
`03` section 8 and the test class name; (b) for each of the eleven rows write one line saying
which existing server rule actually enforces it, and (c) test **that** rule by hand for a
covered caller. Four of the eleven lead to screens that do not exist yet (`03` section 15.1),
so this is about six rows of real work. **P2, owner: engineer, with me.**

### 2 and 3 · SEC-10 and SEC-13 — the static checks do not cover the new modules

SEC-10: *"`growth_api.py` and `team_api.py` carry no `ignore_permissions` of their own."*
SEC-13: *"no module-level cache and no module-level mutable state in either."*

Both were to be proved by the static check in `tests/test_frame_endpoint_registry_034.py`.
`MODULES` at `:41` is `frame_api, inbox_api, staff_api, home_api, pay_api, time_api,
language_api`. **`team_api` and `growth_api` are not in it**, and no Wave 4 test replaces it —
`test_endpoint_guards_045.py` does the endpoint discovery well, and no static source check
at all.

And the modules do carry the flag: `team_api.py:212`, `:225`, `:294`, `:353` and
`growth_api.py:193`. I read all five. **Each raises the flag after the scope is built**, so
the spirit of SEC-10 — check before the flag — holds, and I found no exposure. But the
requirement as written says none, the notes do not record the exception, and the guard that
would have caught a sixth one does not run on these files.

**Fix: two lines in `MODULES`, then either remove the five or declare each one** in the same
file's declared-exception list, which already exists for `language_api`. **P2, cheap.**

## Requirement by requirement

| ID | Verdict | Evidence |
|---|---|---|
| SEC-1 | **met, and the check checks itself** | `tests/test_endpoint_guards_045.py:28-48` discovers endpoints from the module by membership of `frappe.whitelisted`, and `:104-115` asserts the discovery finds the ones we know about — written because the first version discovered nothing and passed over an empty loop |
| SEC-2 | **met in fact, gate missing** | `staff_api.get_staff_list:240-242` checks `has_feature` on the server. No Wave 4 test patches the gate. The **static check banning the patch was never written**, and ten older tests do patch it. P3 |
| SEC-3 | **met** | `staff_api.ROW_KEYS:84` and the key-by-key rebuild at `:294`. `get_manager_dashboard` is off the whole-row list — see SEC-15 |
| SEC-4 | **met** | Fixed key tuples per module: `team_api.ROW_FIELDS`, `staff_api.ROW_KEYS`, `pay_api.PAY_KEYS` |
| SEC-5 | **partial** | `on_leave_today` is now `frappe.get_all` (`hr_api.py:627-634`) — the string SQL is gone. **`get_team_scorecard` still builds SQL with `.format()`** (`hr_api.py:1378-1395`), which is the exact shape SEC-5 banned. It inserts only `"%s"` placeholders and a fixed status list, so it is **not injectable** — I read every interpolation. The **static check SEC-5 asked for does not exist**. P3 |
| SEC-6 | **met** | `access.permitted_employee_filters:275-286` can never return `{}`; `staff_api._own_scope_filters:142-171` returns `NO_EMPLOYEES` for every failure including **an unknown value in the scope constant** (`:159-163`) — fail closed on a typo, which is the case most helpers get wrong |
| SEC-7 | **not re-verified in this pass** | |
| SEC-8 | **met** | `team_api.REFUSAL:87` used for every cause (`may():253-266`); `staff_api._refuse:187-215` is one sentence for Guest, no feature and no scope alike, and logs through `access.refuse` with no personal content |
| SEC-9 | **not re-verified in this pass** | |
| SEC-10 | **recorded as met, is not** | Above |
| SEC-11 | **not re-verified in this pass** | |
| SEC-12 | **met on the wave path** | `_get_employee` filters Active. **Off the wave path it is still false in nine places** — `goals_api.py:24,411,1248`, `performance_api.py:66,577,5045,5192,5265`, `field_app_records.py:64` query Employee by `user_id` with no status, and Growth reads performance data. Lesson 3, still live. **P2, owner: engineer** |
| SEC-13 | **recorded as met, is not** | Above |
| SEC-14 | **met** | `team_api._caller:112-127` fails closed with no Employee record, and threads the user through rather than mixing one person's record with another's roles |
| SEC-15 | **not re-verified in this pass** | |
| SEC-16 | **met** | Verified by running `scripts/check_js_translation_calls.py` extended over `next-team.js` and `next-growth.js` in this pass: 246 calls, clean. **But those two files are not in the shipped check's list** — see the Wave 5 review, F2 |
| SEC-17 | **on dev, tenant check still owed** | The hooks are on `origin/dev` (`42f89c4`). The check that proves it is the census on the tenant, before DTC's staff load. See the hand-back note |
| SEC-18 | **recorded as met, is not** | Above |
| SEC-19 | **met, and it is the best control in the wave** | `attendance_correction.decided_as:976-1006` derives Manager / HR / None from the caller's real relationship at the moment of the decision. There is no argument for it anywhere: `decide()` takes `name, approve, note` only, and `tests/test_decided_as_045.py:220-251` supplies one in the body and asserts the stored value does not move. `_decided_as_is_storable:1008-1024` means a missed migration loses the capacity, not the approval. And **None for a Shift Supervisor is the honest answer**, not a false "HR" in an audit field |
| PRIV-1 to PRIV-4 | **not re-verified in this pass**, except PRIV-4's scope | `staff_api` keeps the POST-only rule and `_escape_like:175-181`. Designation matching (AC-27) is **not implemented** — the term searches `employee_name` only (`:274`). Narrower than specified, so not a privacy defect |
| PRIV-5 | **met** | `hr_api.py:1386` — `review_status IN (...)` is in the `WHERE`, so an unreleased rating is never fetched. Exactly what the requirement asked for |
| PRIV-6 to PRIV-13 | **not re-verified in this pass** | |

## Other findings

**F4 · Minor (P3) — a document id in a URL.** `growth_api.get_self_review:559` is a plain
`@frappe.whitelist()` taking `appraisal`, so it answers a GET and the Appraisal name lands in
the web server's access log. Wave 3's PRIV-5 made the same argument about a payslip name.
One decorator.

**F5 · Minor (P3), outside the wave — a whole Employee row into a Notification Log.**
`kra_api.report_missing_kra:163-164` passes `emp`, which is `_get_employee()`'s **whole row
object**, as `document_name` on a Notification Log sent to every HR user. Untouched by these
waves. **I could not run it**, so I cannot say whether Frappe casts it to a string containing
the date of birth, gender and mobile number, or throws. It needs one run on the local bench.

**F6 · Minor (P4) — the People directory's constant.** `DIRECTORY_SCOPE_FOR_EMPLOYEES` is a
good shape: both branches implemented, fail-closed on an unknown value. Surbhi said
"employees get it" and the **width was chosen by the engineer**, as the comment honestly
records. It should be confirmed by her rather than inherited.

## Residual risk

| # | Risk | Owner | Date | State |
|---|---|---|---|---|
| R1 | The eleven-row matrix is a payload rule, not eleven server rules (SEC-18) | Engineer with me | **2026-10-15** | **not accepted — the claim must be corrected either way** |
| R2 | `team_api` and `growth_api` sit outside the `ignore_permissions` and module-state guards | Engineer | **2026-10-05** | two lines |
| R3 | No repo-wide `ignore_permissions` counter in CI. 901 occurrences across our two apps | Security and privacy engineer | 2026-10-31 | **carried since Wave 1, now four waves old** |
| R4 | Nine "who am I" lookups outside the wave modules do not filter `status = "Active"`, so a leaver with an enabled login keeps access | Engineer | before DTC go-live | open |
| R5 | `permitted_branches` fails open on a Branch permission scoped to another doctype | Surbhi (live check) and engineer (fix) | 2026-09-30 / 2026-11-15 | open |
| R6 | The org chart still shows every company and store; a Team row is a click away | Engineer, `ALV-86` | before DTC go-live | **not accepted** |
