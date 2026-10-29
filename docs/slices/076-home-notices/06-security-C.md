# 076 Part C · Security and privacy review (expenses from Pending, and birthdays)

Security and privacy engineer · 29 Oct 2026 · ALV-240 · Diff reviewed: `git diff origin/dev...HEAD` on `slice/076-part-c` (commits `6ae6e203`, `be9c6204`).

**I wrote the requirements in `01c`.** Lesson 6 says I must not be the only person who checks them. The reviewer should check SEC-12 to SEC-16 on their own. Two of my findings below are gaps in **my own** requirements, not in the build. I say so where it applies.

## Verdict: **Pass for the code, with conditions. Two things must be settled before Part C goes live at DTC**

The code does what `01c` asked. The decide endpoint is tight, the self-approval rule holds on every door, and the birthday reply carries no year and no age. I found no secret, no personal data in logs, and no new `ignore_permissions`.

The bad news is about the data and the rules around the code:

1. **Possible live exposure at DTC, not caused by Part C (escalate now, P0 if confirmed).** At DTC, staff logins may be able to read **every colleague's date of birth** (and joining date, gender, manager, status) through Frappe's own API today. I showed the mechanism on the local PPJ copy: one plain staff login, given only a "narrow" Employee permission, could list **403 of 403** employees with their date of birth. Our notes say DTC uses only narrow permissions. I could not check DTC. One read-only query decides it. If it is true, the birthday card's promise "never your birth year" is false at DTC, and the same hole may let staff read and edit each other's expense claims.
2. **Major (P2): a claimant can choose their own approver.** The approver field on an expense claim is open to the claimant. Through the API they can change it to any colleague who holds the Expense Approver role, including a friend in another company. That person can then approve from Home. SEC-12 is met as I wrote it, but I wrote it too loosely. About 8 lines fix it.
3. **Major (P2): people without a portal login appear on the birthday card and cannot hide.** The opt-out lives in My profile, which needs a login. Nobody else may change it. So a person with no login has no way to say no. Must be fixed before the switch is turned on anywhere.

The birthday switch ships **off**, so points 1 and 3 do not reach anyone yet. Point 2 is live the moment Part C is.

## What I ran, and what I could not

- **Ran it (read only, local PPJ copy on `hrlocal-bench`):** as a plain staff user, Frappe HR's own permission check says they **may create** an Expense Claim, **may write** their own, **may write `expense_approver`** (level 0), and **may not write `approval_status`** (level 1).
- **Ran it (read only, in memory):** the same kind of staff login, with its Employee permission replaced in memory by one row that applies only to Attendance (the "narrow" shape). `frappe.get_list("Employee")` then returned **403 rows, all with a date of birth**. With its real (broad) row it returned 1. Nothing was written. The scratch scripts were copied to the container's `/tmp` and deleted after.
- **Ran it (read only):** data shape on local PPJ. 403 Active employees, all with a branch, all with a date of birth, all with a login. 402 have an expense approver. All 44 approvers hold the Expense Approver role. **Zero Expense Claims**, so "0 rows" on PPJ proves nothing about the expense part.
- **Read the installed source:** Frappe `model/db_query.py:1129-1143` (a permission with `applicable_for` set to another doctype does not restrict the Employee list itself). Frappe HR `expense_claim.json` (Employee role: create, read, write, no submit, no row limit) and `expense_claim.py` (no check that the approver is a valid one). `hr_settings.json` (`track_changes: 1`; HR Manager may write).
- `scripts/check_scope_traps.py`: passes on the branch.
- **Could not run:** any Python test on this branch. The builder's container `hrlocal-076c` is not running, and the shared bench does not mount this worktree. Where I rely on the builder's results and break tests, I say so.
- **Could not check:** anything at DTC. Production is off limits to me. See "Questions" for the exact read-only queries.

## Requirement by requirement

| Req | Status | Mechanism (file:line) | How I checked |
|---|---|---|---|
| SEC-12 only the named approver, Active | **Met as written. Weak as designed** (Major 1) | `hr_api.py:2484` approver must be the caller and have an Active Employee (`_get_employee`, `:300-308`, filters `status = "Active"`). A missing or guessed claim id gets the same words (`:2480-2485`), so it does not say whether the claim exists. Filing sets the approver (`:2406-2410`, `:2433`), else refuses | Read the code. Leaver test is the builder's |
| SEC-13 no self-approval, every door | **Met** | Portal: `hr_api.py:2486`. Desk, REST, import, bulk submit: `hooks.py:397-399` `refuse_own_submit` on `before_submit`, which compares the claim's employee login with the session user (`access.py:184-190`, `:56-61`). Does not depend on the HR Setting | Read the code. Builder's test uses both `doc.submit()` and `frappe.client.submit` with the HR Setting at 0, and failed when the hook was removed |
| SEC-14 once, through Frappe, no `ignore_permissions` | **Met** | Locked read first (`:2481`), then Draft and undecided (`:2487-2488`), then `doc.submit()` (`:2502`). No `ignore_permissions`, `db_set`, `set_value` or SQL in the function (a test reads its source). Without the Expense Approver role it refuses in plain words (`:2489-2491`) instead of bypassing | Read the code. True two-connection race not run (builder says so too); the row lock is the guard |
| SEC-15 decline reason safe and private | **Met** | 1 to 140 characters after trimming, checked before escaping (`:2494-2500`). Stored escaped in its own field `alvoraa_decline_reason` (`home_people.py:50-54`), so the title (`remark`) is never touched. Unescaped only in the caller's own claims (`hr_api.py:2206`, filtered on their own Active Employee). The page escapes it again (`portal.js`, "Declined: …" row uses `esc`) | Read the code and the JS |
| SEC-16 amounts reach only the approver | **Met** | `inbox_api.py:531-588`: `expense_approver = caller`, Draft, not their own, `get_list` for rows and count (`:319-329`), `no_rows()` with no Active Employee, fixed keys (`ROW_KEYS`). The claim lines are read with `get_all` only for claims the caller already got through `get_list` (`:556`), and that bypass is declared in the registry test | Read the code |
| SEC-19 inbox not widened | **Met for Part C** | One new part, one fixed key list, no `ignore_permissions`, 50-row cap kept | Read the code |
| SEC-21 logs carry ids only | **Met for the planned paths** | Every refusal goes through `refuse()` → `log_refusal` with claim id and rule only (`access.py:28-53`). The backfill prints counts only. The Part B worry still applies: an unplanned 500 in `decide_expense` would put `reason` into the Error Log through Frappe's local-value snapshot (codebase-wide, Worry 1) | Read the code |
| PRIV-5 no year, no age | **Met in the endpoint. The premise was wrong** (Escalation 1) | `home_people.py:91-116` builds each row from name, kind, day, month, and years for anniversaries. No id, no date, no photo. But my `01c` said "level 2, so a plain employee cannot read them through Frappe". That is wrong: `employee_field_rights.py:12-13` gives level-2 **read** to every role that reads Employee. Level 2 is a write lock. The only thing that stops a colleague reading the date is the Employee User Permission | Read the code. Ran the in-memory check above |
| PRIV-6 switch and opt-out on the server | **Partly met** (Major 2) | Switch off returns `{"on": 0}` before any Employee query (`:125-127`). Default 0 (`:39`). Only HR Manager or System Manager change it, through the document, so HR Settings' own history records who (`:148-181`; `track_changes` verified). Opt-out filtered in SQL (`:99`). `set_birthday_hide` takes no employee (`:136-145`). Any other save is put back (`keep_hide_birthday`, `:63-69`). Wording says "on Home" (decision 5). **Gap:** people without a login cannot opt out | Read the code and installed `hr_settings.json`. Builder's break tests |
| PRIV-7 same company and branch, Active only | **Met** | Viewer's own Active Employee gives company and branch (`:76-78`); no branch or no record gives an empty list without reading colleagues (`:129-131`). The query filters Active, company, branch (`:98`) | Read the code |
| AC-120 colleague cannot read the dates through Frappe | **Met only with a broad Employee permission** | Builder's test adds the permission real data "has". At DTC the shape may be different (Escalation 1) | Read the test |
| SEC-14 ceiling (no new bypass) | **Met** | Counted in code, not prose: no new `ignore_permissions` in non-test code. The plain text count rose 289 → 290 only because a docstring says "No ignore_permissions" | Ran `git grep` on both sides and read the diff |

## Findings, worst first

### Escalation 1 · possible live exposure at DTC (not caused by Part C) · **P0 if confirmed**

- **Who and how:** a DTC staff member with the Employee role, whose Employee User Permissions all have `applicable_for` set to another doctype (Attendance, Leave Application, Employee Checkin, Attendance Request). They call `GET /api/resource/Employee?fields=["employee_name","date_of_birth","date_of_joining"]&limit_page_length=0`.
- **What they would see:** every DTC employee's date of birth, joining date, and every other level-0 and level-2 field (gender, manager, department, status). **Not** bank, PAN or salary: those are level 1, HR Manager only.
- **Why:** Employee has no row-scope hook in our apps, Frappe HR or ERPNext (checked `hooks.py` in all three). The only limit is the User Permission. Frappe ignores a permission meant for another doctype when it lists Employee (`frappe/model/db_query.py:1129-1143`). Our field-rights code gives level-2 read to every role that reads Employee (`employee_field_rights.py:12-13, 73-79`).
- **Evidence:** **demonstrated** on local PPJ in memory: 1 row with a broad permission, **403 rows with DOB** with a narrow one. **Inference** for DTC: our own note (memory, 26 Oct, "every Employee User Permission on that tenant is the narrow kind") says DTC is shaped that way. **I could not check DTC.**
- **Same hole, expense claims (inference, not demonstrated):** Expense Claim has no row hook either, and the Employee role has read **and write** on it with no owner limit (`expense_claim.json`). If a DTC staff login has no permission that applies to Expense Claim, they may read every claim (amounts, notes) and edit another person's draft claim, including its approver. PPJ has zero claims, so I could not show it.
- **Part C's part in it:** none in the code. But the birthday card makes the dates more interesting, and Part C starts real expense traffic at DTC.
- **What to do now:** one read-only query at DTC (below, Q-A). If it confirms, this is a live exposure and goes to its own ticket at once. It is not a Part C fix.
- **Engineer's bad news 4 rated:** the engineer described the case of a login with **no** Employee permission. That is the same mechanism, and the narrow case is the bigger version. Rated with this escalation.

### Major 1 (P2, fix before release or accept in writing) · the claimant picks their own approver

- **Who and how:** Employee A files a claim in the portal. Then, through the API (`PUT /api/resource/Expense Claim/<own claim>` or `frappe.client.set_value`), A sets `expense_approver` to colleague B. Or A creates the claim directly through the API with B already named. B holds Expense Approver (Frappe HR gives that role to every saved approver).
- **What happens:** Frappe HR shares the claim with B with submit right (`hrms/hr/utils.py:800-808`). B sees it in Pending and approves it from Home. It posts to the ledger. B can be in another branch or another company: nothing checks.
- **Why it is allowed:** `expense_approver` is level 0 and the Employee role writes level 0 (**verified by running it**). Frappe HR does not check that the approver is the right one (`expense_claim.py` `validate`, read in the installed source). Our filing code sets the right approver (`hr_api.py:2406`) but nothing stops a later change.
- **Why P2 and not P1:** it needs a willing second person who already approves claims, and the record names who approved. It is also how Frappe HR behaves in Desk today. But Part C makes "the named approver" the **only** control, so the name has to be trustworthy.
- **My part:** SEC-12 should have said "and the claimant cannot choose the approver". That is my gap, not the builder's.
- **Fix (rung 4, about 8 lines):** an Expense Claim `validate` hook: when the person saving is the claim's own employee, `expense_approver` must equal `expense_approver_for(employee)`; otherwise refuse with "Ask HR to change your approver." HR's own changes in Desk still work.
- **Test:** as the claimant, `frappe.client.set_value` the approver to another user → `ValidationError`, field unchanged. Insert through the API with a wrong approver → refused.

### Major 2 (P2, must be fixed before the switch is turned on anywhere) · no opt-out for people without a login

- **Who and how:** an Active employee with no portal login (for example DTC's agency staff, if they have none). Their colleagues in the same branch see their name, birthday day and month, and years of service on Home.
- **Where:** `home_people.py:95-102` selects every Active employee in the branch. It does not require a login.
- **Why it matters:** the opt-out is set only in My profile (`:136-145`), which needs a login. `keep_hide_birthday` (`:63-69`) stops HR changing it, on purpose. So this person has **no way** to say no. Counsel's oral advice was for "on by default, **with a per-person opt-out**" (01b D10). For these people there is none.
- **Evidence:** verified in code. On local PPJ every Active employee has a login, so the gap does not show there (lesson 1). I could not count DTC.
- **Fix (one condition, fail closed):** add `user_id` is set to the query, so only people who can opt out are shown. **Test:** an Active employee with no login and a birthday this month is not in the list.

### Minor 1 (P3) · the switch is for the whole site, not one company

- **Who and how:** an HR Manager limited to company X turns birthdays on in Organisation settings. Company Y's staff now see each other's birthdays too. The confirm shows the whole site's head count (`home_people.py:170`).
- **Spec says:** "HR Manager (or System Manager) may change it", tenant-wide. So this is as specified, but it is a cross-company effect inside one tenant. **A decision for Surbhi** (below, D-3). Cheapest safe option: System Manager only.

### Minor 2 (P3) · an opt-out change leaves no history

- `set_birthday_hide` writes with `frappe.db.set_value` (`:144`), so no Version row is made. If someone later says "I hid myself and I was still shown", nobody can check when they changed it. Fix: save through the document (it already skips `keep_hide_birthday` only because of `set_value`, so the hook would need to allow the person's own save). Small. Can wait.

### Minor 3 (P3) · new files have no `ignore_permissions` ceiling

- `test_portal_security_010.py` only counts files listed in `CEILINGS`. `home_people.py`, `inbox_api.py` and the new backfill patch are not listed. The script's docstring says "new files start at zero"; the test does not do that. Fix: three lines at 0. Note: `home_people._month_rows` reads past permissions with the query builder, which no word counter can see. That read is on purpose and limited to fixed keys.

### Minor 4 (P4) · my `01c` has two wrong statements

- PRIV-5's "level 2, so a plain employee cannot read them" is wrong (see Escalation 1).
- Section 9 and residual risk 4 say CI does not run `bench run-tests`. It does now (`.github/workflows/ci.yml:504-505`, on push to `dev`). Whether those runs succeed while the repo is private (ALV-164) I could not check.
- I will correct both in `01c` when asked; I have not edited anything.

### Worries (not findings)

1. **Every 500 error writes local values to the Error Log** (carried from Part B). For `decide_expense` that would include the decline reason. Codebase-wide; it belongs to its own ticket.
2. **A leaver with a working login and the Expense Approver role can still approve in Desk.** The portal refuses them (`hr_api.py:2484`); Desk does not. Local PPJ has 0 leavers with enabled logins. Not changed by Part C.
3. **Department approvers without the Expense Approver role** see the claim but cannot decide it (engineer's bad news 2). Safe (it fails closed), but it will look broken. Count it at DTC with Q-B.

**Unneeded surface:** none found. No new public route, no guest access, no cache, no export, no stored copy of a date of birth. Three Custom Fields, one endpoint for decisions, four for birthdays, each with its own role or own-record check.

## Lesson 1 · what must exist to see each control working

| Control | Needs |
|---|---|
| Expense part and decide | At least one portal claim **with** an approver. PPJ has 0 claims. DTC: unknown |
| Self-approval | One employee who is their own expense approver |
| Birthdays | People in two branches with dates this month, one opted out, one Left, **one with no login** (missing from the builder's fixtures) |
| Escalation 1 | One staff login with narrow-only Employee permissions (the DTC shape). The builder's AC-120 test uses the broad shape, so it passes whatever DTC looks like |

## Questions, and what Surbhi must decide

### Must know before Part C goes to `main` (each a read-only query at DTC, by someone with access)

- **Q-A (urgent, blocks nothing in the code, may be a live exposure):** how many enabled DTC logins with the Employee role have **no** Employee User Permission with `apply_to_all_doctypes = 1` or `applicable_for = "Employee"`? And the same for `"Expense Claim"`. *Fail-closed default meanwhile:* birthdays stay off at DTC; treat staff API reads of Employee as possible until answered.
- **Q-B (from the engineer's bad news 1 and 2):** how many Active DTC employees have no expense approver on their record or their department, and how many approvers lack the Expense Approver role? *Default:* their claims are refused with "Ask HR to set your approver."
- **Q-C:** how many Active DTC employees have no login? This sizes Major 2.

### Surbhi must decide

| # | Decision | My recommendation |
|---|---|---|
| D-1 | Escalation 1: if Q-A confirms, fix it as its own urgent ticket (data: give each staff login a permission that applies to Employee and Expense Claim, or code: a row rule on Employee for staff roles) | Run Q-A today. Open a YouTrack ticket either way. Data fix first, because it is configuration (rung 2) and reversible; but read the memory note on DTC's pattern first, because a broad row on an HR user cuts them off |
| D-2 | Major 1: fix the approver lock in Part C now, or accept it in writing with a date | Fix now. About 8 lines, one test |
| D-3 | Minor 1: who may flip the birthday switch — any HR Manager (as built) or System Manager only | Keep as built if DTC has one company; System Manager only if not |
| D-4 | Major 2: exclude people without a login from birthdays | Yes, before the switch is ever turned on. One condition |
| D-5 | Counsel's written note for birthdays (01c Q2) | Still missing. The switch stays off until it arrives. Already accepted by you on 28 Oct on that condition |

## Residual risk

| Risk | Label | Owner | Accepted? |
|---|---|---|---|
| Possible tenant-wide read of colleagues' dates at DTC (Escalation 1) | **dangerous debt, escalate now** | Surbhi | **Not accepted.** Needs Q-A first |
| Claimant can choose their approver (Major 1) | temporary debt; the validate hook removes it | Surbhi | **Not accepted** |
| No opt-out for people without a login (Major 2) | temporary debt; one SQL condition removes it. Harmless while the switch is off | Surbhi | **Not accepted** |
| Birthdays rest on oral counsel advice | temporary debt; the written note removes it | Surbhi | Accepted by Surbhi, 28 Oct 2026; switch stays off |
| Anniversary emails ignore the opt-out | acceptable simplification; tick says "on Home" | Surbhi | Accepted by Surbhi, 28 Oct 2026 |
| Approve-and-decline race proven by the lock, not by two live connections | acceptable simplification | Engineer | Not yet named; recommend Surbhi accepts with the release |

## Subtract pass

Removed from my draft: a finding that the filing alert shows the claimant their approver's email (Frappe HR's own share message; the claimant is entitled to know their approver); a finding that Employee can read HR Settings (it holds only the switch value); a request for a DPIA (the processing is still small and switched off; I would write one if counsel asks); a request to add a two-connection race test (the lock is Frappe's own and Part B already accepted the same method). I kept the four Minors short because none of them changes the verdict.
