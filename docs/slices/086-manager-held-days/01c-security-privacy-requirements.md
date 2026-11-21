---
slice: 086-manager-held-days
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-11-21
status: draft for the business analyst. Recommendations only. Surbhi decides; I approve nothing.
risk tier: 1 (files requests that release pay; who may act for whom)
inputs:
  - 01-product-brief.md, incl. the 21 Nov update and the brief gate (Surbhi, 21 Nov 2026)
  - 01b-ux-design.md, incl. v2 and the design gate (Surbhi, 21 Nov 2026: the Change link)
  - prototype-v2.html (read as text, not opened in a browser)
  - 087's 01c-security-privacy-requirements.md and 02-functional-spec.md, "Counsel's conditions, 21 Nov 2026 (ALV-418, ALV-419)" and the decisions after it
  - code in the 087 worktree at c05704bc (slice/087-attendance-follows-punches), because 086 builds on 087
---

# 086 · Security and privacy requirements: a manager sends held-day times for direct reports

## 0 · The short version

**Bad news first.**

1. **A manager may be able to change a request after the employee has confirmed it, and the confirmation stays.** The stock Employee role holds `write` and `delete` on Attendance Request with no owner limit (`hrms/hr/doctype/attendance_request/attendance_request.json`, read). The manager gets a User Permission on each direct report's requests (`raise_for_report` docstring, `attendance_correction.py:2514-2524`, read, not run). On an edit, 087 puts the Confirm fields back to their stored values (`punch_fix._own_the_confirm_fields`, `punch_fix.py:325-327`, read). I found no hook that refuses the edit itself. So: the employee confirms 18:30, the manager changes it to 20:30 through REST, and HR sees 20:30 marked "confirmed". **Inference from code, not run.** This sits in 087's code, so it affects 087 today. SEC-7 closes it. **Tell the 087 session now.**
2. **`raise_for_report` skips the direct-report check for anyone who may approve requests** (`if not _may_review():`, `attendance_correction.py:2445`). A login with the submit right but no HR role (a tenant's Shift Supervisor) has no company limit either (`_scope_conditions` returns `None`, line 337). So through `raise_for_report` that login can file for anybody on the site. The bulk call must not inherit this. SEC-1 applies the direct-report rule to every caller.
3. **Counsel has not answered case A or case B.** Build and test against B (Confirm applies). Do not release to production until counsel answers (⚠ C1).

**Good news, verified in code:** `raise_for_report` is POST only (line 2385), uses no `ignore_permissions` (`doc.insert()`, line 2525), requires a reason (ALV-418, lines 2491-2492), and refuses a non-direct report for a manager (lines 2445-2452). `_employee_for` and `_reports_to` both filter `status = "Active"` (`attendance_correction.py:279-287`, `attendance_analytics.py:106-121`). So a manager who has left, and a report who has left, are both refused. 087 sets the Confirm flag on any request filed by someone other than the employee (`punch_fix.py:318-321`) and refuses approval until it is confirmed (`punch_fix.py:637-641`).

**Counts: 8 SEC, 4 PRIV. Two ⚠ COMPLIANCE flags (C1, C2).**

## 1 · What I read, and on which checkout

- **086 worktree** `slice/086-manager-held-days` at `eba7beaf` (docs only; its code is at `2e31151f`, older than 087).
- **087 worktree** `slice/087-attendance-follows-punches` at `c05704bc`. Read this session: `attendance_correction.py` 275-420 (`_employee_for`, `_me`, `_may_review`, `_scope_conditions`, `_refuse_outside_scope`, `_subject`), 1252-1270 (`_held_request_fields`), 1500-1515 (`manager_on_behalf_on`), 2385-2526 (`raise_for_report`); `attendance_analytics._reports_to`; `punch_fix.py` 255-330 (`validate`, `_own_the_confirm_fields`) and 630-680 (`refuse_unconfirmed`, `confirm`); `held_day.py` 225-262; `hooks.py` 205-258 (the Attendance Request hooks); `field_app_limits.py` 95-125 and `expense_evidence.py` 620-635 (the existing rate-limit wrapper); `hrms/alvoraa_hr_core/access.py` 10-49 (`security_logger`, set to INFO by ALV-391); the stock `attendance_request.json` permissions.
- **Not run:** no test, no site, no container, no production. Every permission statement is about the stock role rows in the code. A tenant's Custom DocPerm can differ. I could not check any tenant.

## 2 · Threat model, four questions

1. **Who wants it, and the cheapest way?** The manager. Most likely to help a friend: type a later leaving time so the day is paid in full. Less likely, but worse: type an earlier time to hurt someone. Next, a manager who files for people who are not theirs, by sending an employee id the page never offered. The cheapest attack is the page's own call with an edited payload.
2. **Blast radius.** One row is one person's pay for one day. One send is at most 50 days. A scope bug is every employee on the site, across companies on a multi-company site. Each site is one tenant, so nothing here crosses tenants.
3. **What becomes possible that was not.** Filing many held-day times in one call. The parts are not new: `raise_for_report` already files one held-day time for one direct report. What is new is speed and volume, and a free-text reason on every row (ALV-418).
4. **How would we find out?** A false time is found only if HR looks at the punches, or the employee says "Not right". A probe with guessed ids is found only if the refusal is logged (SEC-1). Today the direct-report refusal in `raise_for_report` is a plain `frappe.throw`, so it writes nothing to `security.log`.

## 3 · Data inventory: what 086 touches

No new field, no new DocType. Classes use the A1 vocabulary, which is written down and enforced by nothing automatic.

| Item | Where | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|---|
| The missing time and In/Out | Attendance Request `alvoraa_missing_time`, `alvoraa_missing_log` (existing) | sensitive (decides pay) | release the held day | as the request; no new clock | employee; HR in scope; the filing manager |
| The manager's reason, one per row | Attendance Request `explanation` (existing) | sensitive free text (may hold health or family detail) | counsel's condition ALV-418; context for HR | as the request | employee; HR in scope; the filing manager. **Never** in a log, an error, a refusal sentence, the bulk response, a notification or a model prompt |
| Who filed, and when | `owner`, `creation`, plus the server's stamp in `explanation` (existing) | internal | audit | as the request | as above |
| Confirm state | `alvoraa_needs_confirm`, `alvoraa_confirmed_by`, `alvoraa_confirmed_on` (087) | internal | ALV-419 | as the request | as above |
| "Has a login" | worked out from `Employee.user_id` and `User.enabled`; **sent to the page as a yes/no only** | internal | the case B no-login row | not stored | the manager, as yes/no |
| The day's punches beside the box | Employee Checkin (existing read) | sensitive | evidence next to the typed time | unchanged | the manager already sees them today |

**Retention.** Nothing gets a new clock. Attendance Request keeps what it keeps today. The wage-record retention question is still open (087 01c §3). 086 adds no deletion path.

## 4 · Access intent, including who must NOT

| Actor | May | Must NOT |
|---|---|---|
| Line manager (active Employee, `reports_to` points at them) | list held days with no request for **direct** reports; file one time and one reason per held day for them | file for a skip-level person, another manager's report, another company's person, a leaver, themselves, or an id the page never offered; change or delete a request after filing; see the "has a login" detail beyond yes/no |
| Manager who has left (login still enabled, lesson 3) | nothing | file anything (`_employee_for` finds no Active record) |
| Login with the submit right, no HR role (Shift Supervisor) | what it may do today elsewhere | use the bulk call for anyone who is not its own direct report (SEC-1) |
| HR User / HR Manager | decide each request as today | approve a case B request before the employee confirms (087 AC-105); use the bulk call for anyone but their own direct reports |
| Employee whose day it is | see the time and reason filed in their name; Confirm or Not right (B), or see the notice and Not right (A) | be filed for without being able to see it |
| A colleague | nothing | read another person's request or reason |
| Guest | nothing | anything: the calls are not `allow_guest` |

## 5 · Abuse cases

| # | Actor and act | Today, in code | Closed by |
|---|---|---|---|
| A1 | **A manager files a false later time for a friend.** Under B the friend confirms gladly | Allowed by design. Only HR's look at the real punches stands in the way | Not preventable by structure. Punches beside the box and on HR's card; the manager's name on the record (SEC-8); residual R1 |
| A2 | **A manager files a false earlier time to cut someone's pay** | Under B the employee can say Not right. Under A, and for a person with no login, nobody but HR sees it | SEC-6 (B: Confirm); ⚠ C2 (A); SEC-8 |
| A3 | **Filing for someone who is not a direct report** (skip-level, another team, another company) by editing the payload | `raise_for_report` refuses for a manager (2445-2452); not for a `_may_review` login (gap §0.2) | SEC-1 |
| A4 | **A guessed or sequential employee id** to learn names or probe | For a non-reviewer `_subject` refuses before any name is read (404-406); the skip-level refusal names the person (2449) | SEC-1: one sentence for every scope refusal, no name, logged |
| A5 | **Bulk spam**: many sends, or more than 50 rows | No bulk call yet. Structure bounds it: one open request per person per day, direct reports only | SEC-3 (cap and shape), SEC-4 (rate limit) |
| A6 | **Replay or double send**: the same payload sent twice, or a retry after a lost answer | Stock refuses an overlapping request (087 01c §13, read, not run). Two calls at the same moment may both pass the check | SEC-5 |
| A7 | **Confirm then swap**: the manager edits the time after the employee confirms | Possible, see §0.1 | SEC-7 |
| A8 | **Delete the evidence**: the manager deletes a request they filed | Employee role holds `delete` (stock json). No guard found | SEC-7 |
| A9 | **A request for a person with no login** under B waits for ever and takes the day's one open slot, so HR cannot file their own | 087: "waits until HR declines it" (decision 2, 21 Nov) | SEC-6 refuses to create it |
| A10 | **Stored script in the reason**: a reason like `<img src=x onerror=...>` drawn on HR's card or the employee's day sheet | Not checked how each screen draws `explanation` | SEC-3 |
| A11 | **A forged link or another site's form** posting the send | POST only by design | SEC-4 |
| A12 | **The departing manager** with a valid session files a last batch | Refused: no Active Employee record (279-287) | SEC-1 test |
| A13 | **Shared handset**: the next person on the phone sees typed times and reasons | Design keeps nothing in browser storage (01b 5.6) | PRIV-4 |

## 6 · Requirements

Each one says what must be true and how it is tested. **"Fails first"** means: break the control, watch that exact test fail, put it back (verify rule 5).

### SEC-1 · Scope is checked on the server, for every row and every caller

- The bulk call asks, **for each row**: does the caller have an Active Employee record, and is the row's employee in `_reports_to(me, deep=False)` (Active, `reports_to` = the caller)? This applies **even when the caller may approve requests** (closes §0.2). The caller's own id is refused too: the page never lists it.
- A refused row gets one fixed sentence, the same for every scope cause: "Not sent. This person is not one of your direct reports." It carries **no name**, so a guessed id learns nothing.
- Each scope refusal is logged through the existing `access.refuse` with a rule code, the caller and the employee id. No reason text.
- The list the page draws comes through the same scoped reader as `team_days`, never a query of its own (lesson 2).
- `manager_on_behalf_on()` still applies, through `raise_for_report`.

**Test** (as a manager with two direct reports on a test site): one send carrying a direct report, a skip-level report, another manager's report, another company's person, a leaver, a made-up id and the caller's own id. Only the direct report is filed; the six others each get the same sentence with no name; `security.log` gets six lines. Repeat as a login holding the submit right with no HR role: same result. Repeat as a manager whose Employee is Left: nothing filed. With the tenant's manager switch at "0": nothing filed. Fails first: remove the per-row check for `_may_review` callers and watch the Shift Supervisor test file for a stranger.

### SEC-2 · Every row goes through `raise_for_report`, with nothing added around it

- The bulk call is a loop over `raise_for_report`, one savepoint per row. It sets no flag, uses no `ignore_permissions`, and has no copy of any rule. So the reason, the held-day check, the one-punch rule, the time-fit checks and the switch all stay in one place.
- The bulk call files **held-day time fixes only**: a row with no time is refused. One day per row (`to_date` is not accepted).
- A row that fails rolls back to its savepoint and leaves nothing behind. The next row still runs.

**Test:** a send of five rows where row 3 has an empty reason and row 4 is on a day that is no longer Held. Rows 1, 2 and 5 are filed; 3 and 4 are refused with the server's sentence and leave no document. A row without a time is refused. The existing `NoQuietBypass` test covers the new module. Fails first: blank the reason check in `raise_for_report` and watch row 3 get filed.

### SEC-3 · The payload has a fixed shape and a cap of 50

- More than 50 rows: the whole send is refused, nothing filed, with the sentence "50 at most in one send." The server never quietly takes the first 50.
- Each row accepts only: employee, date, time, In/Out, reason. Any other key is ignored. The same person and day twice in one send: the second is refused.
- The reason is plain text, at most 500 characters [my choice, 21 Nov; Surbhi may set another number], and is **escaped wherever it is drawn**: the manager's page, HR's card, the employee's day sheet and Confirm block.
- A malformed payload gets a sentence, never a traceback.

**Test:** 51 rows, nothing filed. A row with an extra key such as `ignore_permissions` or `alvoraa_needs_confirm`: the key has no effect. A duplicate pair: one filed. A 501-character reason: refused. A reason `<img src=x onerror=alert(1)>` filed, then each of the three screens opened in a browser test: shown as text, nothing runs.

### SEC-4 · POST only, CSRF checked, a rate limit per login

- The bulk call is `@frappe.whitelist(methods=["POST"])`.
- It carries the existing per-login limit: `field_app_limits._limited(SELF_KEY, "user", limit=30)` per hour [30 sends an hour is my choice, 21 Nov: 1,500 rows, enough for a 64-person team catching up on a fortnight]. A refusal says "Too many sends. Please wait a while." The real bound stays structural: direct reports only, one open request per person per day.
- **CSRF:** the page must send Frappe's CSRF token. `frappe/auth.py:87` returns early when the session carries no CSRF token (per the agent rule; I did not read the installed source this session). So the test must prove the check runs, not assume it.

**Test:** a GET to the call is refused. A POST from a signed-in session without the `X-Frappe-CSRF-Token` header is refused (run over HTTP, not by calling the Python function). The 31st send in an hour is refused. Fails first: remove the header check from the test client and confirm the refusal came from CSRF, not from something else.

### SEC-5 · A replay or a double send files nothing new

- One open request per person per day stays the rule. The check runs **after locking the day's Attendance row** (`for_update`) inside the row's savepoint, so two sends at the same moment cannot both pass (lesson 5: REPEATABLE READ snapshots).
- A row that already has a request answers "Already waiting with HR", counted as not sent by this send.
- The lost-answer guard (085 AC-30) reads back what was filed before the page offers to send again.

**Test:** send the same payload twice in a row: one request per day. Two sends at once from two threads: one request per day. Lose the answer on purpose, then reload: the page shows what went.

### SEC-6 · Case B is the default; case A is one condition, only on counsel's word

- **Case B (build and test now).** A manager-filed request is marked `alvoraa_needs_confirm = 1` by the server (087 AC-104, `punch_fix.py:318-321`). It cannot be approved until the employee confirms (087 AC-105, `refuse_unconfirmed`).
- **No login, case B:** the server refuses to create the row when the report's `Employee.user_id` is empty **or** the User is disabled. Nothing is filed, so no request waits for ever and blocks the day. The page gets a yes/no `can_confirm`, never the user id or email. Words: "{name} has no login, so this cannot be confirmed in the app. Ask HR to fix this day." (prototype-v2).
- **Case A (only if counsel says the manager's request counts, and Surbhi says yes):** in `_own_the_confirm_fields`, a request that is a held-day time fix, filed by the employee's direct manager at that moment, is not marked for Confirm. The employee still sees a notice and **Not right** on their day sheet. No setting, no switch: one condition in one place, chosen when counsel answers. ⚠ C1, ⚠ C2.

**Test (B):** a manager files for a report with a login: the request is marked, HR's approval is refused, the employee confirms, HR's approval works. For a report with no `user_id`, and for one whose User is disabled: nothing is filed and the page row has no time box. **Test (A, when built):** the request is not marked; the employee's day sheet shows the notice; Not right declines it; a request filed by HR, not the direct manager, is still marked.

### SEC-7 · A request filed for someone else cannot be changed or deleted after filing

- Once filed by anyone other than the employee, its employee, date, time, In/Out, reason and `explanation` cannot be changed through any door (Desk, REST, import). Only `confirm` (Confirm or Not right) and HR's `decide` change its state.
- The filer cannot delete it. Withdraw stays the employee's own act (`withdraw` already checks `doc.employee`).
- **This belongs in 087's validate, because 087 already files for others.** 086 depends on it.

**Test:** as the manager, after filing, `frappe.client.set_value` on `alvoraa_missing_time`: refused. After the employee confirms: still refused, and `alvoraa_confirmed_on` unchanged. `frappe.client.delete` as the manager: refused. The employee editing the manager's request through REST: refused. Fails first: remove the guard and watch the confirm-then-swap test change the time.

### SEC-8 · The record can be rebuilt a year later, in a grievance

From the request alone, with no log:

| Question | Answer from |
|---|---|
| Who filed it, and when | `owner`, `creation` |
| As whose manager | the server stamp in `explanation`: "Raised by {name} ({employee id}), their reporting manager, on behalf of the employee." Today's stamp has the name only (line 2496); add the id, because a name can repeat and `reports_to` changes |
| Sent alone or in a batch | the same stamp: "One of {n} days sent together." No new field |
| What was said | `alvoraa_missing_time`, `alvoraa_missing_log`, the manager's reason in `explanation` |
| Did the employee agree | `alvoraa_confirmed_by`, `alvoraa_confirmed_on`; or Declined by the employee, with `alvoraa_replaces` on their own request (087 AC-110) |
| Who decided, and what they told the employee | `alvoraa_reviewed_by`, `alvoraa_reviewed_on`, `alvoraa_review_note` |
| Refusals and probes | `security.log`. **Recent only, about 2 MB.** Not a long-term record |

- "It is logged" means the fields above. `punch_fix.confirm` writes to `frappe.logger("alvoraa_portal")` at INFO (`punch_fix.py:667`); I did not check that logger's level, so do not count it.

**Test:** file, confirm, approve; then, from a fresh session reading only the request, answer each row of the table. Repeat for Not right.

### PRIV-1 · Collect the time, In/Out and one reason per row. Nothing else

- No shared note, no "same as above", no copied reason (Surbhi, 21 Nov; ALV-418). The page offers no way to copy a reason down.
- No new field, no new copy of personal data, no cache, no export.

**Test:** the payload the real Send button posts carries exactly the five keys per row, with each row's own reason (test what it sends, 28 Oct lesson).

### PRIV-2 · The reason may hold health or family detail, so it goes nowhere new

- The row keeps the warning drawn in prototype-v2: "HR and {name} can read this. No health or family details."
- The reason reaches only: the filing manager, HR in scope, and the employee. Never: `security.log` or any log, the Error Log, a refusal sentence, the bulk call's response (it returns per row a state, the request name and a sentence, **never the reason back**), a notification or email, the Inbox row, or a model prompt.
- An unexpected error on a row is recorded with the request name and employee id only.

**Test:** file a row whose reason holds a marker string. Then search `logs/*.log`, `tabError Log`, `tabEmail Queue`, `tabNotification Log` and the bulk response: no marker. Force an error on one row: the Error Log entry has no marker.

### PRIV-3 · What the employee and HR see, and what nobody sees

- **Employee:** the manager's name, the time, the reason, and Confirm / Not right (B) or the notice and Not right (A). They see everything said in their name.
- **HR:** the filer's name, the reason, the real punches and the Confirm state, as on 087's card.
- **The page's list** carries name, day, punches (time and source) and the shift window. No GPS, no photo, no user id or email, only `can_confirm` yes/no.
- **Nobody:** no per-manager count, no ranking, no "who forgets most" (brief §10 and the 21 Nov update).

**Test:** the list response for a row holds none of `latitude`, `longitude`, photo fields, `user_id`, email. The employee's day sheet shows the reason the manager typed.

### PRIV-4 · Nothing stays on a shared phone

- Typed times and reasons live in page memory only. Nothing in `localStorage` or `sessionStorage`. Back after logout shows nothing.

**Test:** type two rows, check both stores are empty of them; log out, press Back: no row content.

## 7 · Obligations engaged

| Obligation | Source and date checked | What it asks of 086 |
|---|---|---|
| Counsel's conditions ALV-418 (a reason on every request, held days included) and ALV-419 (a request somebody else files waits for the employee's Confirm) | Counsel's written reply of 21 Nov 2026, **relayed by Surbhi**, as recorded in 087's `02-functional-spec.md`. I have not seen counsel's own text | SEC-2 (reason), SEC-6 (Confirm), PRIV-1 |
| DPDP Act 2023 + Rules 2025: accuracy and correction, reasonable security safeguards | `security-compliance-baseline.md` §2, verified 24 Aug 2026: **89 days old today, stale from 22 Nov 2026**. I did not re-verify it this session; I will before the 06 review | SEC-1, SEC-7, SEC-8. No new notice duty for us: the employer holds the notice (counsel, 31 Oct 2026, relayed) |
| Wage records: the attendance register | as 087 01c §8 (secondary sources, searched 20 Nov 2026; gazette and state rules not read) | SEC-8: the record shows who vouched for each time |

### ⚠ COMPLIANCE flags (I am not a lawyer)

- **⚠ C1. Does a held-day request filed by the person's own reporting manager, naming the manager and decided by HR, meet ALV-419, or must the employee press Confirm?** Owner: Surbhi, to counsel (brief gate item 1, 21 Nov). **Blocks: release to production.** Default meanwhile: case B.
- **⚠ C2. Under case A, a person with no login never sees what was filed in their name.** They cannot say Not right. If counsel answers A, ask in the same reply: is A enough for staff with no login, or must HR tell them another way (a printed slip, a word from HR)? **Blocks: case A for no-login staff only.**

## 8 · What must exist before each control can be seen working

Without these, "0 findings" means nothing (lesson 1). On a test site, never ppj.dev's `alv085-test` rows:
- a company with the held-day switch on, and at least one **Held** day with one punch and one with three;
- a manager with direct reports: one with an enabled login, one with no `user_id`, one whose User is disabled; plus a skip-level report, a leaver report, another manager's report, a person in a second company;
- a held day that already has a request;
- a login with the submit right and no HR role; a manager whose own Employee is Left;
- the tenant's manager switch both unset and set to "0".

## 9 · What I could not check

- How each screen draws `explanation` (escaping), SEC-3. I would need to read `portal.js` for the HR card, the day sheet and the Confirm block.
- Whether the confirm-then-swap edit (§0.1) really goes through on a site. I would need a bench and a manager login with User Permissions from `manager_scope`.
- Whether `frappe/auth.py:87` in the installed Frappe skips CSRF as described. I would need to read it inside the bench container.
- Whether stock's overlap check holds under two sends at once. Needs a threaded test.
- Whether a skip-level manager, who can read the deep line's month, can also read a request's `explanation`. I would need `_subject`'s readers and a site.
- Whether any 087 notification carries the reason (PRIV-2). I did not grep for it.
- Tenant Custom DocPerm on Attendance Request. Needs read-only site access.
- How many DTC held-day staff have a login (brief N5; Surbhi is counting).

## 10 · Residual risk (proposed. Owner: Surbhi. Nothing is accepted until she says so)

| # | Risk | Label |
|---|---|---|
| R1 | A manager and an employee agree on a false later time. Confirm does not stop it; only HR's look at the punches does | intentional trade-off, **needs her name and date** |
| R2 | Case A for no-login staff: nobody but HR sees what was filed in their name | open until counsel answers (⚠ C2) |
| R3 | Confirm then swap (§0.1), in 087's code today | **dangerous debt: escalate now.** Owner `hrms-fullstack-engineer` on 087. Closed by SEC-7 |
| R4 | Despite the warning, a reason may hold health or family detail. It goes nowhere new (PRIV-2) | acceptable simplification, needs her yes |
| R5 | `security.log` keeps about 2 MB, so probe refusals are not a long-term record | acceptable simplification; the durable trail is the request fields |
| R6 | The baseline's DPDP entry goes stale on 22 Nov 2026 | temporary debt; I re-verify before the 06 review |

## 11 · Questions

**Must know**
- **Q1 (Surbhi, to counsel): ⚠ C1, with ⚠ C2 in the same message.** Blocks release. Default: case B.
- **Q2 (engineer on 087, then Surbhi): does SEC-7 land in 087?** My reading: yes, because 087 already files for others. If it stays out of 087, 087 carries R3 to production. Default: no release of either slice without it.

**Should know**
- **Q3 (Surbhi): 30 sends an hour per login, and 500 characters per reason?** Both are my choices, made today. Default: those numbers.

**Nice to know**
- **Q4 (Surbhi): an HR report of declined requests grouped by filer** would show managers who guess (A1). It is a per-manager count, which the brief rules out for managers' own view. Default: not built; HR can make one in Report Builder if she wants it.

## 12 · Subtract pass

I removed:
- a server check that refuses identical reasons across rows. Counsel asks for a reason on each, not a unique one, and the page offers no copy;
- a new batch-id field. The stamp text carries "one of n";
- a daily cap per manager. The structural bound and the rate limit are enough;
- a DPIA. No new kind of data and no new purpose: this is attendance correction, which exists;
- a separate requirement for leavers. It is part of SEC-1's test.

I added no new gate, no new log pipeline, no new tooling and no setting.

**Governance note.** I wrote 087's 01c in the same role, and I will write this slice's `06-security-review.md`. The technofunctional reviewer should check SEC-1 and SEC-7 independently.
