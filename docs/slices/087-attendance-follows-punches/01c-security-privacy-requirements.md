---
slice: 087-attendance-follows-punches
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-11-20
status: draft for the business analyst. Recommendations only. Surbhi decides; I approve nothing.
risk tier: 1 (pay, who may add or set aside a punch, an audit record of a pay change)
inputs:
  - 01-product-brief.md, incl. Decisions and the 085-session notes (Surbhi, 20 Nov 2026)
  - 01a-ux-opportunities.md
  - 01b-ux-design.md, incl. v2 and the Design gate (Surbhi, 20 Nov 2026)
  - prototype-v2.html (read as text, not opened in a browser)
  - 07-devops-inputs.md §1 and §2
  - docs/slices/085-held-odd-punch-days/01c-security-privacy-requirements.md (the baseline for held days and punch rights)
  - code in this worktree at 2e31151f
---

# 087 · Security and privacy requirements: a fix request adds or sets aside a punch

## 0 · The short version

**Bad news first.**

1. **Reusing 085's "missing time" fields for ordinary days opens two existing gates.** A request that carries a missing time skips the monthly request limit (`held_day.py:204`, `enforce_monthly_limit` returns at once when `_has_time`). It also skips the employee's filing window (`attendance_correction.py:1599-1600`). Today that is safe, because `validate_missing_time` refuses a time on any day that is not Held (`held_day.py:240-249`). 087 must loosen that check so ordinary days can carry a time. **Then every punch fix would skip both limits, for any past day.** SEC-4 closes this.
2. **The Inbox "no inline approval" rule is only a screen rule, unless the server enforces it.** The Inbox approves by calling the same `decide` endpoint with just the request name (`next-inbox.js:64-68`). Any caller can do the same. The Desk "Submit" button is another door: submitting *is* approving (`hooks.py:203-208`). SEC-1 makes the server refuse any punch-fix approval that does not carry what the approver was shown.
3. **The employee can edit their own draft request after HR has looked at it.** Stock Frappe HR gives the Employee role write on Attendance Request with no owner limit (`attendance_request.json`, read). So the time or the ticked punch can change between HR's preview and HR's click. SEC-1 also closes this.
4. **`decide` accepts a plain GET link.** It is `@frappe.whitelist()` with no method limit (`attendance_correction.py:1929`). From my knowledge of Frappe (not read in the installed source this session), a GET call skips the CSRF check (CSRF: a forged request from another site that rides on HR's login). So a link clicked by a signed-in HR person could approve a request. Today that changes a status. After 087 it inserts a punch. SEC-2 makes these calls POST-only. This app already does that in 39 places.
5. **The ⚠ COMPLIANCE question now blocks the release to production, not just a "switch-on".** Decision 3 puts the feature on for every company, with no switch. So there is nothing to leave off while counsel answers. See §8 and must-know question Q1.

**Counts: 8 SEC, 4 PRIV. One ⚠ COMPLIANCE flag (§8).**

## 1 · What I read, and on which checkout

- **Worktree** `087-attendance-follows-punches`, HEAD `2e31151f`. I ran `git fetch origin dev`. `origin/dev` is `7de630df`, 5 commits ahead. All 5 are ALV-394, the joiner sign-in (`auth.py`, `hooks.py` +9 lines, one login page, two test files). **None of them touch `held_day.py`, `attendance_correction.py`, `field_app_access.py` or `payroll_rules_apply.py`.** I checked this with `git diff --stat HEAD origin/dev`. So what I say about `held_day.py` holds on `origin/dev` too. The brief expected 085 commits there. They are already in this HEAD (`ce0e69b3`, 085 fix round 3).
- **Verified in code** (read this session): `held_day.py` (all of it), `field_app_access.py:40-135, 195-384, 445-492`, `attendance_doors.py`, `hooks.py:160-282, 585-620`, `attendance_correction.py` (`raise_correction`, `withdraw`, `_scope_conditions`, `_refuse_outside_scope`, `decide`, `decided_as`, `not_yours_yet`, `to_review`, `refuse_own_day_outside_window`, the month punch reader at 550-570), `hrms/alvoraa_hr_core/access.py:25-135, 229-300`, `payroll_rules_apply._punches` (365-391), `punch_dedupe.skip_repeat_scan`, `inbox_api._part_attendance_fixes`, `next-inbox.js:55-70`. In stock Frappe HR (vendored): `attendance_request.py:109-180`, `attendance_request.json` and `employee_checkin.json` permissions, `shift_type.py:145, 256-257`, `employee_checkin.py:70-85`.
- **Not run:** no test, no site query, no container, no production access. Every permission statement is about the **stock role rows in the code**. A tenant's Custom DocPerm can differ, and I could not check it on any site.

## 2 · Threat model, four questions

1. **Who wants it, and what is the cheapest way?** Mostly the employee, who wants a late day paid as on time. The cheapest way is to claim an earlier arrival and set aside the real late punch (case (a), turned round). Next is an HR person who wants their own day fixed, or who will approve a friend's request without looking. Then a manager who wants to file for a report on a path 087 does not mean to open (086 owns that). A curious colleague wants the note or the photo on someone else's punch.
2. **Blast radius.** One approval is one person's pay for one day. A fault in the shared reader that 087 changes (`_punches`) is every day of every employee at a company with a pay rule set: 442 people at DTC (DevOps §2, OPS-12). Each site is one tenant, so nothing here is cross-tenant. Cross-company exposure exists on a multi-company site (SEC-3).
3. **What becomes possible that was not.** A punch that no device recorded, created on a person's word, which changes pay. A device punch that stays on record but stops counting. A free-text note on the fix. A second meaning of "this punch does not count", next to the two `skip_auto_attendance` already has.
4. **How would we find out?** Today only if a customer tells us. Refusals go to `frappe.logger("security")`. That logger now writes at INFO (ALV-391, `access.py:29-68`), but it rotates at about 2 MB, so it is not a record anyone can query a year later. **The durable trail must be fields on the records** (PRIV-3). Collusion is found by looking at those fields (§7), not by a log.

## 3 · Data inventory: what 087 adds

Class uses the A1 vocabulary. A1 (field sensitivity classes) is not built, so these classes are written down here and enforced by nothing automatic.

| Item | Where | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|---|
| The added time and its In/Out | Attendance Request: reuse `alvoraa_missing_time`, `alvoraa_missing_log` | sensitive (it decides pay) | the correction | as the request; no new clock | employee; HR in scope; line manager (they read the request today, see PRIV-2) |
| Which punch(es) to set aside | Attendance Request, **new**: Employee Checkin ids only, no times copied | sensitive, by reference | the correction | as the request | as above |
| The employee's optional note | Attendance Request: **reuse `explanation`**. No new free-text field | sensitive free text (people write health or family reasons) | context for HR | as the request | employee; HR in scope; line manager (today). **Never** in a log, an error, the Inbox row, a notification or a model prompt |
| HR's note | existing `alvoraa_review_note` | sensitive free text | tell the employee | as the request | as above |
| "Added by fix": request link, approver, when | Employee Checkin, **new** Custom Fields | internal (ids and a time) | audit; defend the pay figure | as the punch | the employee (own punches); HR in scope; manager in today's line view sees the **words** "Added by HR", not the fields |
| "Set aside by fix": request link, approver, when | Employee Checkin, **new** Custom Fields | internal | audit; the pay engine's filter | as the punch | as above |
| The day before and after (status, hours, late) | Attendance Request, written at approval | sensitive (pay) | audit | as the request | employee; HR in scope |
| The preview HR saw | not stored; compared at approval (SEC-1) | n/a | stops a blind or stale approval | not stored | HR |

**No new collection about a person's location, face or device.** The punch photo and GPS stay where they are, and no 087 payload carries them (PRIV-2).

**Retention.** Nothing in 087 gets a new clock. Employee Checkin, Attendance and Attendance Request keep whatever they keep today. Counsel has not given a retention period for attendance or wage records. The 18 Sep 2026 conflict is still open: counsel's 6-month post-exit erasure against wage-record minimums (questions Q7 and Q10 in that proposal were not answered). 087 adds no deletion path, and it must not add one. A punch with a fix mark cannot be deleted (SEC-6).

## 4 · Access intent, including who must NOT

| Actor | May | Must NOT |
|---|---|---|
| Employee (active) | raise a fix for their **own** day: one added time, set-aside ticks, a note; withdraw it while waiting; see the result and every mark on their own day sheet | approve anything; name a punch that is not on their own day; edit the request after HR has looked and still have it approved (SEC-1); set or clear a fix mark by any door |
| Employee who has left | nothing (`_me` filters `status = "Active"`, `attendance_correction.py:278-294`) | raise or keep a request alive (SEC-5 refuses approval for a leaver) |
| Line manager (Employee role only) | see a direct report's punches and the words "Added by HR" / "Set aside", as in today's line view | file a punch fix or a set-aside in 087 (086 owns that). The 085 held-day route `raise_for_report` keeps doing what it does today |
| Any login holding the submit right on Attendance Request but no HR role (a tenant's Shift Supervisor, W1D-14) | what it may do today on ordinary requests | approve a punch fix (SEC-3) |
| HR User / HR Manager in scope | approve or decline a punch fix for people in their companies and branches | approve **their own** day, including as a leaver who keeps an HR login; approve a request **they raised**; act outside their companies or branches; approve from the Inbox row, the Desk or REST (SEC-1) |
| HR login with no company and no branch | nothing (085 SEC-4, `_scope_conditions`, `attendance_correction.py:308-336`) | anything |
| System Manager | as HR, every company (`permitted_companies`) | approve their own day |
| Machine sync account | file punches, as today | set or clear a fix mark |
| CXO | nothing new | n/a |

## 5 · Abuse cases

| # | Actor and act | Today, read in code | Closed by |
|---|---|---|---|
| A1 | **Fake punch to inflate pay.** An employee who arrived at 11:15 claims 10:30 and ticks 11:15 as wrong. If HR approves, the late mark goes and the hours grow | No such path today. After 087 it is the design's own path. Only an HR person who looks stands in the way | SEC-1 (HR sees the before and after, from the same function the approval runs); PRIV-3 (the mark stays for ever, the employee's word is on the record); the card says where each punch came from (SEC-1); residual R2 |
| A2 | **Set-aside hides a real late arrival.** As A1, but the punch set aside is a **machine** punch, which is the strongest evidence there is | n/a | SEC-1 names the source of every punch on the card and says in words when a machine punch is being set aside; Q6 |
| A3 | **Gate dodge.** An employee raises fixes for many old days, past the monthly limit and the filing window | Would be open once `validate_missing_time` is loosened (`held_day.py:204`, `attendance_correction.py:1599`) | SEC-4 |
| A4 | **Naming someone else's punch.** An employee puts a colleague's Employee Checkin id into the set-aside list. HR, seeing a long card, approves | The field does not exist yet. Checkin ids are sequential and easy to guess | SEC-4 |
| A5 | **HR fixes their own day.** An HR User raises a fix for their own day and approves it, or adds the punch in the Desk | `decide` refuses own (`refuse_own_decision`, `attendance_correction.py:1979`); `before_submit` refuses own (`refuse_own_submit`, `hooks.py:230`); `checkin_has_permission` refuses HR adding or changing a punch on their own record, leavers included (F1 and SEC-2, `field_app_access.py:325-336`) | SEC-3 keeps all three and tests them on the new path |
| A6 | **HR collusion.** HR person A approves a friend's request without looking, or HR A and HR B approve each other's days | Not preventable by structure: both are allowed to approve | detection (§7) and residual R1 |
| A7 | **Blind approval from the Inbox.** HR presses Approve on an Inbox row that shows no punches and no result | Open: `next-inbox.js:64-68` calls `decide` directly | SEC-1 |
| A8 | **Approval through the Desk or REST.** HR submits the request in the Desk, or `POST /api/resource/Attendance Request/<name>` with `docstatus: 1` | Submit is approve (`hooks.py:203-208`). The 085 hooks scope it but do not demand a preview | SEC-1 |
| A9 | **Stale approval.** The employee edits the draft (time or ticks) after HR has opened the card, or a machine punch arrives, and HR then approves what they did not see | Open: the Employee role holds write on Attendance Request (stock `attendance_request.json`) | SEC-1 |
| A10 | **A manager files a punch fix.** A manager uses `raise_for_report` with a time on an ordinary day | `raise_for_report` already takes `missing_time` (`attendance_correction.py:2342-2344`). Today `validate_missing_time` limits it to Held days | SEC-4: ordinary-day fixes and set-asides are only for the employee's own login, until 086 |
| A11 | **Replay.** The employee sends the same fix again after approval, or HR cancels the approved request and amends it, so the punch is added twice | Stock refuses a second request that overlaps any request not cancelled (`attendance_request.py:109-132`, read, not run). Cancel and amend is open: stock `on_cancel` cancels the day's Attendance (`attendance_request.py:145-152`). The added punch stays, and an amended copy would add another one | SEC-7 |
| A12 | **Approving twice.** Two HR people, or one double-click, approve at the same moment | `decide` checks `docstatus != 0` (`attendance_correction.py:1980`), but nothing locks the row before that check | SEC-7 |
| A13 | **Race with Frappe's auto-attendance job.** The job takes any punch with no `attendance` link and `skip_auto_attendance = 0` (`shift_type.py:256-257`). An added punch with no link is exactly that | 085 links its punch for this reason (`held_day.py:415`) | SEC-7 |
| A14 | **Desk edits to the new marks.** HR ticks "set aside" on a colleague's punch in the Desk with no request, or clears it to undo a fix with no record. An employee sets the "added by HR" mark on a new punch of their own through REST (the Employee role may create its own punches) | The fields do not exist yet. Frappe's `read_only` does not stop an API write | SEC-6 |
| A15 | **Deleting the evidence.** HR deletes an HR-added punch, or a set-aside one, from the Desk | HR holds delete on Employee Checkin (stock json); R4 scopes it to their companies (`field_app_access.py:340-346`); nothing protects a fix-marked punch | SEC-6 |
| A16 | **A forged link.** Someone sends HR a link to `/api/method/...decide?name=...&approve=1` | Possible if GET skips CSRF (Inference, see §0 point 4) | SEC-2 |
| A17 | **The curious colleague** wants the note, the set-aside reason or the punch photo | A colleague cannot read another person's request or punch (User Permissions; `checkin_has_permission`) | PRIV-2 keeps it so: no new reader |

## 6 · Requirements

Each one says what must be true and how it is tested. **"Fails first"** means: break the control, watch that exact test fail, then put it back (verify rule 5). "Punch fix" means a request that adds a punch, sets one aside, or both.

### SEC-1 · A punch fix is approved only through the card, on exactly what the approver saw

- **One door.** A punch fix is submitted only by `decide`. A `before_submit` hook refuses a punch fix unless `decide` set a flag on the document. A flag cannot be sent from the Desk, REST or an import. So the Desk Submit, `PUT`/`POST` with `docstatus: 1`, and the Inbox's inline Approve are all refused.
- **What HR saw.** `decide(approve=1)` on a punch fix must carry what the card was drawn from: the request's `modified` time and the ids of the day's punches. The server works the preview out again inside the approval. If any of these differs, it refuses with a sentence such as: "This day changed after you opened it. Open it again." This covers an employee edit (A9), a new machine punch, and an Inbox call that carries nothing (A7).
- **The card names the source of every punch.** Machine, this portal, the field app, or added by HR. When the request asks to set aside a machine punch, the card says so in words (A2).
- An ordinary request with no punch-fix fields keeps today's behaviour, Inbox included.

**Test:**
- The Inbox path: `decide(name, 1)` with no preview data is refused for a punch fix, and still works for an ordinary request.
- The Desk path: `savedocs` submit of a punch fix is refused, and so is REST `docstatus: 1`.
- Stale preview: open the card, edit `alvoraa_missing_time` as the employee, approve with the old data. Refused, and no punch is added.
- Stale punches: open the card, insert a machine punch for that day, approve. Refused.
- The happy path: the card's data is sent, the approval is accepted, and the result equals the card's "if approved" line.
- Fails first: remove the `before_submit` check and watch the Desk test go green when it should not.

### SEC-2 · Calls that change attendance are POST-only

`decide`, `raise_correction`, `raise_for_report` and `withdraw` become `@frappe.whitelist(methods=["POST"])`. Any new 087 endpoint does the same. The portal and the Inbox already post (frappe.call posts by default, an Inference I have not traced for every caller), so the check is that nothing breaks.

**Test:** a GET to each endpoint, as a signed-in HR user, is refused and changes nothing. The portal and Inbox browser tests still pass. Fails first: drop `methods` on `decide`, and the GET test changes a request.

### SEC-3 · Only HR in scope approves, and never for their own day

On the document (`before_submit`), so every door meets it. The approver of a punch fix must:
- hold HR User, HR Manager or System Manager. Having the submit right alone (a Shift Supervisor) is not enough. Being the manager alone is not enough either. **An HR person who is also the line manager may approve**, as HR;
- pass `_refuse_outside_scope` for the employee (company, then branch, fail-closed for HR with neither);
- not be the employee. `refuse_own_decision` already reads `user_id` whatever the Employee status (`access.py:108-121`), so a leaver with an HR login is still refused;
- not be the raiser (`refuse_raiser_submit`, exists);
- and the employee must still be **Active** at the moment of approval (brief §10).

The punch insert and the set-aside write run **as the approver**, through `doc.insert()` and `doc.save()`, with **no `ignore_permissions`**. Then `checkin_has_permission` F1 and R4 (`field_app_access.py:303-346`) are a second, independent lock: HR cannot add or change a punch on their own record, nor on a record outside their companies.

**Test:**
- An HR User and an HR Manager, each approving a fix for their **own** day: refused at `decide`, at `before_submit`, and at the punch insert (call `checkin_has_permission` directly with `ptype="create"`).
- The same for a leaver whose HR login is still active.
- A login with the submit right and no HR role: refused.
- Company-A HR on a company-B employee: refused, and the refusal is logged with rule R5 or SEC-17.
- A no-company HR login: refused.
- A request for an employee who left after raising it: refused, nothing written.
- Another HR in scope: succeeds, and the added punch's `owner` is that HR user, not Administrator.
- Fails first: patch `refuse_own_decision` to do nothing, and watch the punch-insert check still refuse (this proves the second lock is real).

### SEC-4 · A request can only name its own day, and the gates still count it

Checked on `validate`, so every new draft and every edit of one is checked. Checked again at approval.
- **Set-aside ids.** Every Employee Checkin named must belong to the request's `employee`, fall on the request's single day, and not already be set aside. A name that fails any of these is refused in words, and the refusal is logged with ids only.
- **The added time.** At most one per request. It must be on that day and fit between the punches either side, with the night-shift rule `worked_out` already applies (`held_day.py:296-298`).
- **Who may raise.** A punch fix on a day that is **not Held**, or any set-aside, may be raised only by the employee's own login, until 086. `raise_for_report` keeps its 085 held-day use and nothing more.
- **The gates.** The monthly limit and the employee filing window skip a request **only when its day is Held**, which is 085's rule. A punch fix on an ordinary day counts against both, like any other request. The test for "Held" is the day's Attendance status, never "the request carries a time". **Q2** asks Surbhi to confirm; this is the fail-closed default meanwhile.

**Test:**
- A set-aside naming another employee's checkin: refused. The same for a checkin from the next day.
- A second added time in one request: refused.
- A time outside its neighbours: refused, with the design's sentence.
- `raise_for_report` with a time for an ordinary day, and with a set-aside: both refused. With a time for a Held day: accepted, as today.
- With a limit of 3, a fourth punch fix on ordinary days in one month: refused. A fix on a Held day: accepted at any count.
- With an employee window of 5 working days, a fix for a day 10 working days back: refused.
- Fails first: restore the `_has_time` early return in `enforce_monthly_limit`, and watch the limit test pass the fourth request.

### SEC-5 · A day that cannot be fixed is refused at the server, on every door

The design shows these days up front. The server must refuse them anyway: at raise, and again at approval, because the day can change in between.
- **A day inside a submitted Salary Slip.** `is_in_final_slip`, exists (`held_day.py:333-335`).
- **A day covered by approved leave**, including a half-day leave.
- **A hand-marked day.** The engineer must say which field tells one apart (OPS-7). Until then this guard cannot be tested.
- **A day with no submitted Attendance row yet.** Fail-closed (Q5): no fix for a day the job has not marked. This removes the job-creates-a-second-row race at its root.
- **An employee who has left** (SEC-3).

Refusal sentences name no leave type and no person (design §7).

**Must exist to see it work:** at DTC, payroll is done outside the portal, in Excel (memory, 26 Oct 2026). If DTC has no submitted slips, the "final slip" guard **never fires there**. A fix to an October day made in December would quietly change the Salary Workings figure after the money was paid. The employee filing window (SEC-4) is then the only fence on how far back a fix can go. **I could not check** whether DTC has submitted slips or a filing window set. To check, I would need read-only access to `tabSalary Slip` and `tabDefaultValue` on DTC.

**Test:** one test per guard, each failing first, at raise and at approval. One extra test: the slip becomes final between raise and approval, and the approval is refused with nothing written.

### SEC-6 · The fix marks are written only by the approval, and a marked punch is never removed

- **The new Employee Checkin fields** (added-by and set-aside: request, approver, time) are refused in `validate` on every door (insert or save), unless the approval code set a document flag. Read-only and permlevel are not enough: HR holds write at permlevel 1, and `read_only` does not stop an API write.
- **A punch carrying either mark** cannot be deleted (`on_trash`), and its `time`, `employee` and `log_type` cannot change on any door, HR and System Manager included. **Administrator is the one exception**, kept only for a future retention job, and every such change must be logged. A wrong fix is reversed by a new request, never by an edit.
- **A set-aside punch** keeps `skip_auto_attendance = 1` (decision 1b). That flag cannot be cleared while the set-aside mark is on.
- **The set-aside is written with `doc.save()`, not `db.set_value`.** Then the Version row records it (Employee Checkin has `track_changes: 1` in the stock json; not checked on a tenant), and `checkin_has_permission` R4 applies.

**Test:**
- An employee's REST `POST` of a new own punch with the added-by field set: refused (or stored empty, so long as it is never stored as sent).
- HR in the Desk ticks set-aside on a colleague's punch with no request: refused.
- HR deletes an added-by-fix punch, and a set-aside one: refused.
- HR clears `skip_auto_attendance` on a set-aside punch: refused.
- A System Manager does each of these: refused.
- After an approval, the set-aside punch has a Version row naming the approver.
- Fails first: remove the flag check and watch the Desk-tick test write the field.

### SEC-7 · A fix happens exactly once, whatever the timing

- **Lock first.** `decide` reads the request (and the day's Attendance row) `for_update` before the "already decided" check. Two approvals at once give one punch, and the second caller is told "already decided".
- **Link at insert.** The added punch has its `attendance` link set to the day's row in the same transaction (OPS-9). So Frappe's job never takes it for an unmarked punch.
- **No second release.** The insert must not fire `release_on_machine_punch` into a release (it exits for non-machine owners, `held_day.py:400`; prove it).
- **No cancel.** Cancelling an approved punch fix is refused, on every door, with a sentence: "Raise a new request to change this day." Stock `on_cancel` would cancel the day and leave the added punch behind, and an amend would add a second one (A11).
- **One transaction.** The punch, the set-aside and the day's new values commit together or not at all (OPS-8). The slip refresh keeps its own savepoint, as in 085.

**Test:**
- `decide` called twice in a row: one punch.
- Two sessions approving at once, with a barrier (a forced wait) between the read and the submit: one punch, one clear refusal.
- Frappe's job and the approval, run in both orders on one day: one Attendance row, and the same count on the day sheet, on the row and in the engine.
- Cancel of an approved punch fix, from the Desk and from REST: refused.
- Force an error after the punch insert: no punch, no mark, no status change remain.

### SEC-8 · Pay reads one list of punches, and the change moves nothing else

**Lesson 2 applies.** 087 adds a third meaning of "this punch does not count". Every reader that turns punches into **pay or a pay-visible figure** must leave out set-aside punches, and must read only the new field for it. Widening the `skip_auto_attendance` filter would also drop repeat scans and ALV-302 punches, and change DTC counts.

The readers I found, by grep, that build their own punch query:

| Reader | File:line | Pay-bearing? | Must honour set-aside |
|---|---|---|---|
| `_punches` (engine; also used by the hold, the machine release and `attendance_onload`) | `payroll_rules_apply.py:378` | yes | **yes** |
| `_day_logs` (`worked_out`, `preview`) | `held_day.py:278-284` | yes | yes (already filters `skip_auto_attendance`, which the set-aside also carries) |
| Month view punches and `times_by_date` for the break | `attendance_correction.py:559-570` | shows the break the engine counts | **yes for the break; still shows the punch, marked** |
| Attendance analytics break | `attendance_analytics.py:653-659` | as above | **yes** |
| Team days (manager flags) | `attendance_correction.py:2100-2106` | flags only | decide with the BA; must not contradict the day |
| Grooming first punch | `grooming.py:332-337` | grooming marks can become fines | decide with the BA |
| Salary Workings report | `salary_components_and_workings.py` | yes | **not checked**: I did not read where it gets its punches |
| Today's check-in status (three readers) | `hr_api.py:1305, 1521, 1750`, `home_api.py:236` | no (today only; SEC-5 stops fixes on unmarked days) | no |

The Frappe job, `punch_dedupe` and the photo reader read `skip_auto_attendance` or are unaffected.

- **One result.** The HR preview, the Attendance row after approval, the engine's verdict, and the day sheet give the same count and status (the brief's kill criterion 2).
- **No double count.** The 085 `extra` time is not passed into `worked_out` once the punch really exists.
- **The dry run (OPS-12) is the gate.** Before any mark exists, the reader change must move **0** verdicts.

**Test:**
- One day with 3 punches, one set aside: each "yes" reader in the table counts 2.
- The same day with a repeat scan inside 2 minutes: the engine count is unchanged from today.
- The preview and the result match for case (a), case (b), and "stays Held".
- Release a held day by a fix at a company with a rule set: the engine no longer holds it (ALV-410).
- Fails first: take the filter out of `_punches`, and watch the ALV-410 test go red.

### PRIV-1 · Collect the time, the ticks and an optional note. Nothing else

- **The send payload** holds the request's day, one time or none, the set-aside checkin ids, and the note. The kind (In or Out) is worked out on the server from the time's position (design v2.2), and is not trusted from the client.
- **No new free-text field.** The note reuses `explanation`. There is no separate "set-aside reason" box: the reason for a set-aside is the same note.
- **No photo, no location, no file** on the punch-fix path. 081's file attach stays on the old reason form only.

**Test:** press Send in a browser test and assert the payload's keys (memory: test what it sends). Send a forged `log_type` that disagrees with the position: the server stores the derived one.

### PRIV-2 · No new reader, no wider view, and the note goes nowhere new

- **The note.** The note, HR's note and the set-aside link appear only where the request is already readable: the employee, HR in scope, and the line manager. Managers read requests today through the User Permission on Attendance Request (`manager_scope.py:52-55`), and the reason form already says so: "Your manager reads this request..." (`portal.js:11369`). **The prototype's "Note for HR (optional)" is therefore not true as built.** The form must say who reads the note, in the existing sentence. This changes words in the approved prototype, so it needs Surbhi's yes (Q3).
- **Manager views** show the marks as words ("Added by HR", "Set aside"). Never the note, and never who approved.
- **No punch photo URL and no GPS** in any 087 payload: the card, the day sheet, the Inbox row or the preview. Opening the photo stays in the Desk, where `log_photo_view` records it (`field_app_access.py:449-492`). A photo in the card would skip that record.
- **The Inbox row payload** gains nothing beyond a "this is a punch fix" flag (no note, no times), so the row can show Review instead of Approve.
- **Logs, errors and refusal sentences** carry ids only: request, checkin, employee, user. Never the note, never a leave type.
- **No caching** of the preview, the result line or the punch list. No `allow_guest`. No new `ignore_permissions`: the per-file ceilings in `test_portal_security_010` stay where they are.

**Test:**
- A colleague is refused a peer's request and punch by name.
- The manager's team view returns the mark words and no `explanation` or `alvoraa_review_note`.
- The card, day sheet and Inbox responses contain no key ending in `photo`, and no latitude or longitude.
- Force an error on approval and grep the Error Log and `security.log` output for the note's text: no hits.
- The `ignore_permissions` ceiling test is unchanged.

### PRIV-3 · The person sees every change to their punches, and it can be rebuilt a year later from the database

- **The employee's own day sheet** shows every added and set-aside punch, in words and not by colour alone, with the date and "from your request". A set-aside punch keeps its time on screen. Nothing is hidden.
- **From the database alone**, for any added or set-aside punch, a person can answer: who asked, what they said, who approved, when, which punch was added or set aside, and what the day was before and after. §7 lists where each answer lives.
- **Before and after.** Stock Frappe writes a Comment with the old and new **status** when a request changes a day (`attendance_request.py:170-178`). It records no hours. So 087 records the status, hours and late mark before and after, on the request, at approval, in fields nobody can edit after submit.

**Test:**
- The employee's day sheet API returns the marks for case (a) and case (b).
- A query using only the Employee Checkin and Attendance Request tables rebuilds every answer in §7 for one approved fix.
- The "before" fields hold the pre-approval status and hours.

### PRIV-4 · The dry run does not copy a customer's data

The `_punches` change can be proved without DTC's personal data: the new field is set on no row until 087 runs. **Recommend:**
- the dry run runs on `ppj.dev`, which has the DTC rule set on (memory, 19 Nov 2026), and on a fresh CI site;
- it compares every day's verdict before and after;
- its output is counts and Attendance ids only.

If Surbhi still wants it run against DTC's own data, it runs read-only, on the production bench, prints ids only, keeps nothing afterwards, and needs her explicit word, because it is a production read.

**Test:** the dry-run script's output contains no `employee_name` and no times; a second run reports the same counts.

## 7 · The audit trail

**What counsel said, quoted, not paraphrased.** I did not find a line "log every change" in `security-compliance-baseline.md`. The nearest written lines are:
- **The baseline, §2, "Accuracy & correction":** "Employee-initiated correction request with a routed workflow and an audit trail" (verified 24 Aug 2026; 88 days old today, **stale from 22 Nov 2026**). This is the team's engineering reading of DPDP, not counsel's words.
- **Counsel on the joiner form, 31 Oct 2026, relayed by Surbhi (memory):** "log every export in an audit trail". That ruling is about exports.

I am treating "every change to a punch or a day through 087 leaves a durable record" as the requirement. That is a stricter reading than either source says, and **it is my choice, made today**. If counsel's "log every change" line exists in writing, I have not seen it. Please point me to it.

**Where each answer lives (PRIV-3):**

| Question in a grievance | Answer from |
|---|---|
| Who asked, and when | Attendance Request `owner`, `creation` |
| What they said | `alvoraa_missing_time`, `alvoraa_missing_log`, the set-aside ids, `explanation` |
| Who approved, when, in what capacity | `alvoraa_reviewed_by`, `alvoraa_reviewed_on`, `alvoraa_decided_as` (existing) |
| What HR told them | `alvoraa_review_note` |
| Which punch was added | Employee Checkin with the added-by fields; `owner` = the approver |
| Which punch was set aside | Employee Checkin set-aside fields, plus its Version row |
| The day before and after | the new before/after fields on the request; the stock status Comment |
| Every refusal (including probes) | `security.log`, rule and ids. **Recent only, about 2 MB** (`access.py:46-50`) |

**Detection, with no new tooling:** a Report Builder view on Employee Checkin, grouped by approver and by employee per month, built from the fields above. That is configuration, not code. It is how A6 (collusion) would be found. Whether someone looks at it is a process question for Surbhi.

**Durability:** these rows are never deleted by 087 (SEC-6). Version rows can be removed by a System Manager in the Desk. **Not checked** whether any role on a tenant holds delete on Version.

## 8 · Obligations engaged

| Obligation | Source and date checked | What it asks of 087 |
|---|---|---|
| DPDP 2023 + Rules 2025: accuracy and correction, security safeguards, grievance | baseline §2, verified 24 Aug 2026, **stale from 22 Nov 2026** `[re-verify before quoting]` | 087 *is* an accuracy-and-correction route. SEC-1, SEC-3, PRIV-3. No new notice duty for us: we are the processor; the employer holds the notice (counsel, 31 Oct 2026, relayed) |
| Wage records: the attendance register | Wages (Central) Rules 2026 under the Code on Wages 2019, notified 8 May 2026, per secondary sources ([PRS](https://prsindia.org/billtrack/code-on-wages-central-rules-2026), [Taxmann](https://www.taxmann.com/post/blog/wages-central-rules-2026-code-on-wages-chapter-wise-guide/), [BDO](https://www.bdo.in/en-gb/insights/alerts-updates/alert-final-central-rules-notified-under-all-four-labour-codes)), searched 20 Nov 2026. These summaries name an "Attendance Register-cum-Muster Roll" (Form IX) and say registers may be kept electronically. **I did not read the gazette text.** State rules for DTC's Delhi and Haryana stores and for Grace: **not checked** | see the flag below |

**⚠ COMPLIANCE: is a punch added by HR, on the employee's word, acceptable attendance evidence?** I am not a lawyer.

- **Why it matters.** After 087, a day's pay can rest on a time that no device recorded. Only the employee says it, and only a named HR person accepted it. A device punch can also stop counting while it stays on record. If a labour inspector or a court treats the attendance register as evidence, both acts must be defensible.
- **What the product does to make it defensible:** the mark is plain and permanent (SEC-6); it is linked to the request and to both people (PRIV-3); the original device punch is never edited or deleted; HR cannot do it for themselves (SEC-3).
- **What it blocks.** Decision 3 has no per-company switch. So this blocks **the release to production**, not a switch-on. Must-know Q1.
- **The question for counsel (Surbhi to send):** "Under the Code on Wages 2019 and the Wages (Central) Rules 2026 (the Form IX attendance register), and under the shop and establishment rules for Delhi, Haryana and Grace's state, may an employer record a day's attendance from a punch that no device recorded? The punch is entered by a named HR person on the employee's written statement. The record shows it was entered by hand, by whom, when and on whose request, and the device punches are kept unchanged. May the employer also mark a device punch as 'not counted' while keeping it on record? Is anything more needed: the employee's confirmation, a reason, a time limit, or a second approver?"

## 9 · What must exist before each control can be seen working

Without these, "0 findings" means nothing (lesson 1):
- a company **with a pay rule set** (ppj.dev has DTC's on) and one **without** one (Grace-like);
- on the test site, at least: a Held day, an ordinary day with a portal punch, a day with a machine punch, an approved leave day, a hand-marked day (once OPS-7 names the field), a day inside a **submitted** slip, a day with **no Attendance row yet**, a **draft** slip for the employee;
- two HR logins in one company, one HR login in a second company, a no-company HR login, a login with the submit right and no HR role, a leaver with an active HR login;
- a machine account (Biometric Sync role, no Employee record);
- the employee filing window and the monthly limit both **set** (both are blank or 0 by default, which turns SEC-4's gates off);
- the ppj.dev rows with `device_id alv085-test` are in use by testers: **do not touch them** (brief).

## 10 · What I could not check

- Whether a GET call to a whitelisted method skips CSRF in the **installed** Frappe. **Inference** from my knowledge of Frappe. I would need to read `frappe/auth.py` and `frappe/handler.py` inside the bench container. SEC-2 is cheap either way.
- Whether DTC has submitted Salary Slips, a filing window or a monthly limit set (SEC-5, SEC-4). I would need read-only access to DTC's `tabSalary Slip`, `tabDefaultValue` and `tabCompany`.
- Where the Salary Workings report gets its punches (SEC-8 table). Not read.
- Tenant Custom DocPerm on Attendance Request, Employee Checkin and Version. I would need read-only site access.
- Whether `logs/security.log` now gets lines after ALV-391. I would need to read it on a bench after a refusal.
- Whether a counsel line "log every change" exists in writing (§7).
- The gazette text of the Wages (Central) Rules 2026, and the state rules (§8).

## 11 · Residual risk (proposed. Owner: Surbhi. Nothing is accepted until she says so)

| # | Risk | Label |
|---|---|---|
| R1 | Collusion: HR approving a friend's request without looking, or two HR people approving each other's days. Allowed by design; found only by looking at the fields (§7) | intentional trade-off, **needs her name and date** |
| R2 | The added time rests on the employee's word and one HR approval. Lawfulness as evidence is the ⚠ COMPLIANCE question | **open until counsel answers; blocks main** (Q1) |
| R3 | HR can still add a punch for a colleague directly in the Desk, with no request. It is in scope (R4) and labelled "added by HR" by owner (`attendance_correction.py:554-566`), but carries no request link and no second person. So the sentence "every HR-added punch is linked to a request" is **false**. The true sentence is "every punch added **through a fix request** is linked to it". Pre-existing | temporary debt; Q4 decides whether to close it |
| R4 | `checkin_query_conditions` returns no filter for any HR role (`field_app_access.py:258-259`). So on a multi-company site, an HR User of company A can probably **list** company B's punches, photos included, in the Desk. The hooks note says a Company User Permission never reaches Employee Checkin. **Inference from code, not run.** Pre-existing; 087 must not rely on that list for scope | **dangerous if untracked: ticket it now**, P2, owner `hrms-fullstack-engineer` |
| R5 | `security.log` keeps about 2 MB, so refusals are not a long-term record | acceptable simplification; the durable trail is the record fields |
| R6 | The baseline's DPDP entry goes stale on 22 Nov 2026 | temporary debt; I re-verify it before the 06 review |

## 12 · Questions

**Must know**
- **Q1 (Surbhi, with counsel). The ⚠ COMPLIANCE question blocks main.** My reading: with no switch, the release itself switches it on everywhere. Options: (a) hold main until counsel answers (recommended); (b) accept R2 in writing, with a date; (c) add a per-company switch. Option (c) goes against decision 3 and adds a switch, so I do not recommend it. Fail-closed default meanwhile: build and test, but do not release to main.
- **Q2 (Surbhi).** Does a punch fix on an **ordinary** day count against the monthly limit and the employee filing window? My reading: yes. Only Held days were exempted, and that was for a reason specific to Held days. Default: SEC-4 as written.
- **Q3 (Surbhi).** The prototype says "Note for HR". Managers can read the request today. Options: (a) use the existing sentence "Your manager reads this request" (recommended, words only); (b) hide notes from managers (a new restriction, more code). Default: (a), as a parity change that needs her yes.

**Should know**
- **Q4 (Surbhi).** Should HR keep adding punches for colleagues directly in the Desk once 087 exists (R3)? Default: leave it open. It is a working flow at DTC, and closing it is her call. The sentence we use about it stays the smaller one.
- **Q5 (Surbhi, BA).** Should a day with no Attendance row yet be fixable? Default: no (SEC-5). It removes a race. The person waits until the day is marked.
- **Q6 (Surbhi).** May an employee ask to set aside a **machine** punch? Default: yes, with the card saying so in words (SEC-1).
- **Q7 (Surbhi).** Should cancelling an approved punch fix be refused, with a new request as the only way to reverse it? Default: yes (SEC-7).

**Nice to know**
- **Q8 (counsel, with decision 7).** The employee sees "HR", not a name. But they can already read `alvoraa_reviewed_by` on their own request through the API, and they will be able to read the approver field on their punch. So decision 7 is about the screen only. Is that acceptable?

## 13 · Found on the way (for the BA; not security)

- **Stock blocks a second request for the same day** while any request for it exists that is not cancelled, including a **Declined** one, which stays a draft (`attendance_request.py:109-132`; read, not run). The design's "send this first and add the next after HR decides", and "Declined: the timeline is editable again", may both hit "Overlapping Attendance Request". The BA should check before writing those criteria.
- The month view already labels a punch "added by HR" from its `owner` and `device_id` (`attendance_correction.py:554-566`). A punch owned by `Administrator` is treated as **not** by hand. The new field should decide the 087 label, and SEC-3 makes sure the owner is the approver.
- `skip_repeat_scan` flags any new punch within 2 minutes of a kept punch (`punch_dedupe.py:77-90`, `DUPLICATE_PUNCH_MINUTES = 2`). An added time that close to an existing punch would be stored but not counted. SEC-8's "preview equals result" test catches it. The BA may want a plain refusal instead.

## 14 · Subtract pass

I removed these:
- a separate requirement for a "seen" token in the Inbox, folded into SEC-1 (one door, one check);
- a new audit DocType or ledger. Fields on the existing records, the stock Comment and Version are enough for one approval about one day;
- a requirement for a collusion report. It became a Report Builder view (configuration) in §7;
- a requirement for a second approver ("four eyes") on set-aside of a machine punch. Not asked for, and it adds a role and a state. It is left as a question for counsel inside the §8 question;
- a DPIA. No new category of data and no new purpose: the processing is attendance correction, which exists;
- a per-company switch (decision 3 rejected it; Q1 names it only as an option).

I added no new gate, no new log pipeline and no new tooling.

**Governance note.** I will also write `06-security-review.md` for this slice, which means verifying requirements I wrote. The technofunctional reviewer should check SEC-1 and SEC-4 independently.
