---
slice: 071-unseated-names
artifact: 06b-security-verification
author: hrms-security-privacy-engineer
date: 2026-10-25
status: 26 Oct re-verification at 71c25de4 - F1 and F2 MET on the branch. No security blocker for the push to dev. Main still carries the gap until this lands there (see Re-verification).
first verdict (25 Oct, bec85cb9): NOT READY TO SWITCH ON. One P0, found in code this slice extends (it is already on main).
code: branch slice/071-unseated-names (bec85cb9) in .claude/worktrees/071-unseated-names, compared with origin/dev
ran on: container hrlocal-071, site test071 only. Every probe was rolled back. Nothing pushed, no code edited.
---

# 071 · Names in the "In no seat" tray — security and privacy verification

## Bad news first

1. **P0, stop the line: `assign_person` checks the seat, but never checks the person.** An HR
   Manager can put **somebody from another company** (or, for a store's HR person, another store)
   into their own seat by sending that person's employee ID. The person's name then shows on the
   caller's chart. I did it on test071 (scenario F1 below). This gap is **not new in 071**: it came
   with ALV-194 (commit `e455ffc2`, 15 Oct) and **is already on `main`**. But 071 adds a new way
   in ("Place in seat", "Place anyway") and a new effect (`add_place` raises the other seat's
   count too). The fix is about five lines and one test, in the same function 071 changes.
2. **The same call is also a lookup tool.** Send any employee ID with a start date before they
   joined, and the refusal says "*Name* joins on *date*". Nothing is saved, so nothing is in any
   audit trail. That is a quiet way to read the name and joining date of anyone in the tenant.
3. **There was no `01c` for this slice.** The brief said "one file changes, no server change". The
   strategy then added a server change (`add_place`, D1), and nobody re-asked the security
   questions. That is how F1 was missed. My verification is therefore against the brief's claims and
   the caller's list, not against numbered `SEC`/`PRIV` items.
4. **I could not run the browser print check.** It needs the probe login's password, which I do not
   have. I checked print by reading the CSS and by running the jsdom wall chart check (below).

## The answers, one line each

| Question | Answer | Evidence |
|---|---|---|
| Who receives the unseated names? | System Manager / Administrator (all), HR Manager and HR User (their companies, narrowed to their branches). Nobody else gets the key. | Verified in code `register.py:444-448`, `access.py:276-286`. Tests `test_positions_064` lines 125-158 (6 tests). |
| In any other payload? | No. The list is built only in `position_table`, from a fixed list of six keys. | Verified in code `register.py:454`, `:490-492`. Test `test_each_person_carries_exactly_the_six_allowed_fields`. |
| `add_place`: who may call it? | Anyone with Write on Alvoraa Position, for a seat in their scope (role checked on the server). | Verified in code `register.py:749` → `_position_in_scope` `:613-620`, then `save_position` checks again `:508-521`. |
| Scope on the seat? | Yes, company and branch. | Test `test_another_branch_seat_is_refused_and_keeps_its_count`. |
| **Scope on the person?** | **No. Not checked anywhere.** | **F1. Verified by running it.** |
| New `ignore_permissions`? | No. `register.py` still has 4 (CEILINGS = 4). | `git diff` has none; `grep -c` = 4 on both sides. |
| Audit trail | A Version row on the seat: who, when, `seats` 1 → 2. The assignment row carries owner and time. | Verified by running it (F1 probe: Version owner `probe071@example.com`, changed `seats 1 → 2`). |
| Both-or-neither | Yes. A refusal after the raise leaves the count unchanged. | Test `test_a_refusal_after_the_place_is_added_leaves_the_count_as_it_was`; my oracle probe (raise, then refusal, then rollback). |
| Search by employee ID enumerates people? | Not from the dialog: the browser only pre-picks an ID that came in the in-scope list, and `candidates_for` searches names inside the caller's scope. **But `assign_person` and `what_they_hold` accept any ID** (F1, F2). | `portal.js` `posUnPlace` (reads `POS.unseated` only); `register.py:1008-1016`. |
| Names in notices, logs, errors, print | No new log or notice. Print hides the tray and both dialogs. Error messages show names, which is fine for in-scope people and **a leak for out-of-scope ones** (F1). | `panels.css:2121-2123`, `:2194-2198`; diff has no `console.log`, `frappe.log`, `log_error`. |
| Employee link | `/app/employee/<id>`, new tab. Frappe's own Employee permission decides what opens. No data travels in the link except the ID the reader already has. | `portal.js` `posUnseatedSheet`. |
| 065 / 066 keys | None in the new rows. The tray draws only name, ID, joined, no-manager, and the seat's title, branch, filled and seats. | Diff read; `UNSEATED_KEYS`; 065's `plan` and `opening` are on seat and people rows, not on `unseated`. |
| CSRF / method | The page sends POST with the CSRF token. The endpoint also accepts GET, but this Frappe (16.33.1) never commits a GET. | `portal.js:10410-10420`; `frappe/app.py:465`. |
| HR placing all 82 at once | No bulk call exists. A script could call 82 times; each is an allowed, audited act by someone with Write. No rate limit needed. | Read in code. |

## Findings

### F1 · P0 · Blocker (blocks switch-on; pre-existing, already on main) — the person is never scoped

**Who, what, how.** An HR Manager whose companies are "Demo071 Retail", calling
`register.assign_person(<their own seat>, <employee ID from "Alvoraa Test Company">, add_place=1)`,
**places that other company's person in their seat, raises the seat from 1 to 2, and then sees the
person's name on their own Positions chart.**

**Where.** `hrms/hrms/alvoraa_org_structure/register.py:733-804`. `_position_in_scope` (`:606-621`)
checks only the seat. Nothing compares `employee` with `_scope()`. The doctype does not either
(`alvoraa_position_assignment.py:38-46`: no company or branch rule). Then `a.insert(ignore_permissions=True)`
at `:803`.

**Demonstration (Verified by running it, test071, rolled back).** As `probe071@example.com`
(HR Manager, User Permission Company = Demo071 Retail):

| Step | Result |
|---|---|
| The foreign person is in the caller's scope? | `false` |
| `assign_person(seat, foreign, from_date="1990-01-01", add_place=1)` | Refused with ValidationError. **The message contains the person's name and joining date.** Nothing saved, so no audit row. |
| `assign_person(seat, foreign, add_place=1)` | **PLACED.** Seat count 1 → 2. Assignment owned by the caller. |
| `position_table()` as the caller | **The foreign person's name is in the reply.** |

The same path with a store's HR person and another store's employee: **Inference** from the same
code (no branch test on the person anywhere in `assign_person`). Not run.

**Why it matters.** Priority 2 in our order: cross-company isolation. Employee IDs are a naming
series (`HR-EMP-00001`, `00002`, ...), so guessing them is trivial. The lookup (step 2) leaves no
trace at all. The placement (step 3) also changes another company's person's record of "where they
sit", which feeds 072's chart lines (seats follow reporting) and any report that reads assignments.

**Live exposure.** `assign_person` has been on `main` since ALV-194. The caller needs Write on
Alvoraa Position (HR Manager or System Manager by default). It only matters on a tenant with more
than one company, or with a store-limited HR person. **I could not check whether any production
tenant has either** (production is off limits to me). Someone with production read access should
answer that today.

**Fix (engineer's call, smallest rung).** In `assign_person`, straight after `_position_in_scope`,
refuse when the person is outside `_scope()` (their company in `companies`; their branch in
`branches` when that is not `None`), with the same wording as `_refuse` and **without** the
person's name. Use `_scope()`, not `permitted_employee_filters()`, so the owners who reach Positions
without an HR role keep working, as today. Same guard in `what_they_hold` (F2).

**Test that must exist (server, CI, in `test_unseated_071.py`):**
(a) another company's employee, with and without `add_place` → PermissionError, no Assignment row,
seat count unchanged; (b) a store editor and another store's employee → same; (c) the refusal
message does not contain the person's name (use a marker name such as `SNTL-OTHERCO-NAME`);
(d) `what_they_hold` for an out-of-scope ID → refused. Break the guard once on purpose and see
(a) fail.

### F2 · P1 · Major (pre-existing, on main) — `what_they_hold` answers for anyone

**Who, what, how.** Any login with Read on Alvoraa Position, calling
`register.what_they_hold(<any employee ID>)`, gets the titles of every seat that person holds, in
any company. Verified by running it: `probe071` asked about an "Alvoraa Test Company" employee and
got back the seat "SEC071 Secret Other-Co Seat", 100%.

**Where.** `register.py:624-661`: `may_view()` only, then reads by `employee`. 071 calls it from
the dialog (`posShowWhatTheyHold`), but only for in-scope people, so the browser is not the leak;
the endpoint is. Same fix and test as F1 (d).

### F3 · P4 · Minor — `assign_person` takes GET

`register.py:732` is `@frappe.whitelist()` with no `methods=["POST"]`, unlike `delete_position`
(`:556`). Not a CSRF hole today: Frappe 16.33.1 commits only POST/PUT/DELETE/PATCH
(`frappe/app.py:465`, Verified in code), so a GET's writes are thrown away. Worth one word when F1
is fixed; not a blocker. **Label: acceptable simplification.**

### F4 · Process — no `01c`, and the server change was not re-reviewed

The brief's kill rule said "if placing needs a server change, ship B". The strategy argued that an
optional parameter does not trigger it, which is fair, but the security question ("is the person
scoped too?") was never asked. **Label: temporary debt**, removed by writing a short `01c` with F1's
requirement before the fix is built.

## What I checked and found sound

- **List scope (unchanged code, still right).** Company-wide HR gets every active unseated person of
  their companies; a store HR gets only their branch, and nobody with no branch; another company's
  person is never listed; a reader with no HR scope gets no key; leavers are not listed; each person
  carries exactly six keys. Six tests in `test_positions_064.py:125-158`.
- **HR User.** By default HR User has **no** Read on Alvoraa Position (`alvoraa_position.json`:
  HR Manager and System Manager only), so an HR User sees the tray only if a tenant adds that row.
  Then the buttons follow `may_edit`, and the server refuses a write anyway
  (`test_somebody_who_may_not_change_seats_is_refused`).
- **Role on the server, not only the browser.** `posUnPlace` hides buttons without `POS.may_edit`,
  but the server checks Write and seat scope twice (`_position_in_scope`, then `save_position`).
- **`add_place` gives no new power.** Someone with Write could already raise the count through
  `save_position`. The server reads the count fresh and adds nothing to a seat with room or with no
  limit (`test_a_seat_with_room_gets_no_extra_place`, `test_a_seat_with_no_limit_stays_with_no_limit`).
- **Atomic.** One request, one transaction. A refusal after the raise rolls the raise back (test,
  plus my own probe). Two HR people on one full seat at once: the second either hits Frappe's
  "modified since" check on the seat or reads the new count; nothing half-done (Inference from
  `save_position` using `doc.save()`).
- **Audit.** The raise writes a Version row on the seat (`track_changes: 1`) naming the user and
  `seats` old → new. The assignment records owner, time, from date, and "move approvals" off.
  Enough to answer "who added this place and who went in it" a year later. Nothing ties the two
  rows together except user and time; I am not asking for more.
- **No XSS from names.** Every name, ID, title and role in the new HTML goes through `posEsc`;
  inline handlers use `posJs`, which escapes for both JS and HTML; the context line uses
  `textContent`.
- **No names in URLs or logs.** The pre-filled search goes in a POST body (`gpSend`). The diff adds
  no `console.log`, `frappe.log_error` or notice.
- **Print.** `@media print` hides `.pos-sheet` (`panels.css:2122`) and `#pos-layer` and every
  `.gp-backdrop` (`:2194-2198`); both new dialogs are `.gp-backdrop`. The wall chart prints only a
  count of unseated people (`portal.js` around `:2873`). `check_wall_chart.js`: 183 checks pass
  ("nothing private reaches paper ... only allowed keys").
- **065 / 066.** The new rows read only the six unseated keys and four seat fields. 065's `plan`
  and `opening` keys are not read. 066 grooming touches its own `gm*` block only.

## Commands run and what they said

| Command | Result |
|---|---|
| `node scripts/check_positions_tree.js` | 219 checks, 0 failures |
| `node scripts/check_wall_chart.js` (jsdom borrowed from another worktree; this worktree has no `node_modules`) | 183 checks, all pass |
| `check_portal_handlers.js`, `check_undefined_js.js` | OK |
| `check_app_integrity.py` | 822 checks, OK |
| `check_tag_balance.py`, `check_design_system.py`, `check_no_demo_passwords.py` | OK |
| `bench --site test071 run-tests --module alvoraa_portal.tests.test_unseated_071` | **8 run, 5 errors, all the same: `DuplicateEntryError: User scope194.<x>071@example.com is already assigned to Employee ...`.** Leftover test logins, not a code fault. See the note below. |
| `... test_positions_064` | **No result.** Stopped by my 25-minute limit with no output (the engineer saw 17 OK earlier). Cause not known. |
| `... test_portal_security_010` | 45 + 5 OK (CEILINGS hold, including `register.py` = 4) |
| Two probe scripts as `probe071@example.com`, rolled back | F1 and F2 as above. Checked afterwards: no `SEC071` seat or Version row left. |

**Note on the 071 errors — partly my doing.** Another session started the same 071 tests on test071
at 15:51 while my run (15:45) was going. Two runs on one database can corrupt each other, so I
stopped mine part way. That, or the other run, left the fixture's test logins linked to employees.
The fixture cannot run again over that. I did not clean it up: I do not know exactly which rows the
fixture owns, and the site is shared. **Before anyone re-runs these tests on test071, clear the
`scope194.*071@example.com` users and their employees, or reset test071 from its copy.** Small test
debt worth a line: `hr_user` should reuse or remove an existing login, so one interrupted run does
not break every later run. The engineer's earlier clean run (8 OK) stands as the evidence for the
eight tests; I could not reproduce it.

Not run: `browser_check_positions.js` (needs the probe password); the full `alvoraa_portal` suite
(the engineer's run hung for 6.5 hours; CI or a clean full run is still owed).

## Worries (not findings)

- **065, once it lands.** 065 hides a job opening on a full seat from non-plan readers, because there
  it means a replacement plan. If "Place anyway" raises a full seat and the person goes in at less
  than 100%, the seat now has room, and the hidden opening may start to show. I cannot state it as a
  finding until 065 and 071 are on one branch. Check it at that merge.
- **Duplicate names.** The pre-pick is by ID and a stale pick is cleared, but if the name search
  returns more than 20 rows the person may not be in the list. The pick is then cleared and Save
  refuses; safe, just annoying.

## Residual risk

| Risk | Label | Owner | Accepted? |
|---|---|---|---|
| F1 on `main` today | **Dangerous debt — escalate now** | Surbhi decides; `hrms-fullstack-engineer` fixes | Not accepted. Nobody has accepted it. |
| F2 on `main` today | Dangerous debt (smaller) | Same | Not accepted |
| F3 GET accepted | Acceptable simplification | Engineer, with F1 | Not needed |
| Browser print check not re-run by me | Temporary debt | Test engineer, before switch-on | — |

## Escalation

- **Decision needed:** fix F1 and F2 in this slice before 071 goes to dev, and decide whether `main`
  needs the same fix before any multi-company or store-limited tenant uses Positions.
- **Context:** the person in `assign_person` is never scoped; `what_they_hold` reads anyone.
- **Who is affected:** every employee in a tenant with more than one company or with store-limited
  HR. Count unknown; I cannot read production.
- **Options:** (1) recommended: one scope check in each of the two functions, plus the four tests
  above, in this slice; (2) ship 071 without the "Place" buttons (names only, option B) and fix the
  endpoint separately. Option 2 still leaves the endpoint open on main.
- **Risk if it waits:** an HR login can read names and joining dates across companies with no trace,
  and change another company's org data.
- **Owner:** Surbhi (decision), `hrms-fullstack-engineer` (fix), `hrms-test-automation-engineer` (tests).

## Subtract pass

Removed from my draft: a request for a "reason" on every Place-anyway assignment (the Version row and
the assignment owner already answer the audit question); a rate-limit suggestion (no real abuse
case); a separate finding for the error-message lookup (it is part of F1, fixed by the same check).

---

## Re-verification — 26 Oct 2026, tip 71c25de4 (ALV-228)

**Result: F1 met, F2 met.** The fix is the smallest one that works: one helper, `_person_in_scope`
(`register.py:624-637`), called right after the seat check in `assign_person` (`:767`) and after
`may_view` in `what_they_hold` (`:656`). It reads the person's company and branch and compares them
with `_scope()`, the same rule the seat uses. An unknown ID and an outsider get the same refusal,
with no name and no person ID in the message or in the refusal log (`name=None`). It runs before
`add_place` and before any insert, so nothing is written first.

Checked on hrlocal-071 / test071, nobody else on the site, every probe rolled back (afterwards: no
`SEC071` seat or Version row left). Container code matched the worktree (md5).

| Attack (from 25 Oct) | Before | Now | How shown |
|---|---|---|---|
| HR for Demo071 Retail puts an Alvoraa Test Company person in own full seat, `add_place=1` | Placed, seat 1 → 2, name on their chart | **PermissionError.** Seat stays 1, no Assignment row | Verified by running it; test `test_another_companys_person_is_refused_with_and_without_add_place` |
| Same, with a start date before joining (the lookup) | Message gave name and joining date | **PermissionError, no name, date or ID in the message** | Verified by running it; test `test_the_refusal_names_nobody` (marker name `SNTL-OTHERCO-NAME`) |
| Unknown ID vs outsider: same words? | — | **Identical text** | Verified by running it; same test |
| Unknown ID vs outsider: same time? | — | Median 3.33 ms vs 3.70 ms over 30 calls each (in-process, no network). The gap is far below normal network noise; I do not count it as a usable signal | Verified by running it |
| `what_they_hold` for another company's person | Returned their seat title | **PermissionError**; an in-scope person still answered | Verified by running it; test `test_what_they_hold_refuses_an_outsider_and_answers_for_an_insider` |
| Store-limited HR (Branch permission added to the probe login), person from another store, `add_place=1` | (Inference: placed) | **PermissionError**; `what_they_hold` also refused; own-store person placed fine | Verified by running it; test `test_another_branchs_person_is_refused` |
| In-scope "Place anyway" still works | Worked | Works | Verified by running it |
| Atomic | Yes | Yes; the person check runs before any write, and the earlier rollback test still passes | Code `:767` before `:778-785`; test run below |
| New `ignore_permissions` | — | None. `register.py` still 4 = CEILINGS | `grep -c` |

The only internal caller, `_make_room` → `what_they_hold` (`:700`), runs after the person was already
checked, so it does not refuse anything new.

**Tests:** `bench --site test071 run-tests --module alvoraa_portal.tests.test_unseated_071`:
**12 run, OK** (8 earlier + 4 new). The leftover test logins from 25 Oct are gone. I did not re-run
`test_portal_security_010` (8 minutes); the ceiling is checked by the grep above, and it passed
45 + 5 on 25 Oct.

**Still open (not blockers for the push to dev):**
- **Main still has F1 and F2** until this branch reaches main. Whether a production tenant can be hurt
  today depends on whether any has several companies or store-limited HR. I still cannot check that.
  Surbhi decides whether the fix goes to main on its own, ahead of 071.
- Browser print check: not re-run by me (no probe password). Test engineer, before switch-on.
- No 01c for this slice (process debt, F4).

**Residual risk now:** F1/F2 on main — dangerous debt until the fix lands there; owner Surbhi
(decision); not accepted by anyone yet. On the branch: none open from security.
