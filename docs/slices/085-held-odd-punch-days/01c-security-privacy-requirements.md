---
slice: 085-held-odd-punch-days
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-11-19
status: draft for the business analyst. Recommendations only. Surbhi decides; I approve nothing.
risk tier: 1 (pay, release rights, a bulk write of pay-bearing rows)
inputs:
  - 01-product-brief.md, incl. the Brief gate (Surbhi, 19 Nov 2026)
  - 01b-ux-design.md, incl. the Design gate (Surbhi, 19 Nov 2026)
  - prototype-v1.html (read as text, not opened in a browser)
  - 07-devops-inputs.md §1 and §2
  - code in this worktree at fd658eff (branch slice/085-held-odd-punch-days)
---

# 085 · Security and privacy requirements: a held day is a pay gate

## 0 · The short version

**Bad news first.**

1. **Today, an HR person can make their own odd-punch day paid from the Desk, with no second person.** Four doors are open: tick "Out Time Confirmed" on their own Attendance row; cancel and amend their own row to Present; add or delete a punch on their own record; and, for a manager who also holds HR, raise a request for a report and then submit it from the Desk. Once Held becomes a pay gate, these doors are how the gate gets skipped. SEC-2 and SEC-3 close them.
2. **The release scope fails open for an HR login with no company.** `_scope_conditions` returns None, and then `decide` narrows nothing (`attendance_correction.py:323-329`, `:358`). That contradicts Surbhi's rule of 19 Nov (ALV-385: no company means nobody). Closing it cuts off `hr@grace.alvoraa.co`, the login Grace uses, unless it is first given a Company User Permission. **Must-know question Q1.**
3. **A phone punch is not proof of presence, so it must never release a day.** The geofence (ALV-338) is off unless HR Settings tracking is on, the branch has a pin and a radius over 0. Field workers are exempt, and the phone supplies its own coordinates (`branch_geofence.py:1-21`, `:133-145`). Only a punch filed by the machine account may release a day automatically (SEC-5).
4. **Stock Frappe pays a Held day.** The slip's unpaid-day query reads only Absent, Half Day and On Leave (`hrms/.../salary_slip.py:824`). SEC-1 is therefore the core requirement, not a formality.

**Counts: 7 SEC, 3 PRIV. One ⚠ COMPLIANCE flag (§7).**

**What I checked.** Verified in code: the files and lines cited throughout, in this worktree at `fd658eff`. `origin/dev` is 6 commits ahead (joiner work and instruction files, ALV-353/384). None of them touch attendance, correction or punch code; I checked by `git diff --stat HEAD origin/dev`. Verified by running: I read the stock `company.json` inside the `alv084-bench` container (Company permissions, §4). **Not run:** no test, no site query, no production access. Every permission statement is about the **stock role rows in the code**. A tenant's Custom DocPerm can differ, and I could not check it on any site.

## 1 · Threat model, four questions

1. **Who wants it, and what is the cheapest way?** It is the employee who wants a held day paid without anyone looking. For a staff member, the cheapest way is a phone punch from home later. For an HR person, it is a tick on their own row in the Desk. For an HR person who is also a manager, it is raising a request for a report and approving it themselves. A curious colleague wants a peer's punch times. Those are already fenced (`checkin_has_permission`, `field_app_access.py:246-273`), and 085 must not open a new reader.
2. **Blast radius.** One release affects one person's pay for one day. The company switch affects every employee of one company. The backfill affects all of Grace's November (about 166 days). A stolen machine-sync key affects every employee on that site. Each site is one tenant, so nothing here is cross-tenant. Cross-company exposure exists inside a multi-company site (SEC-4).
3. **What becomes possible that was not.** An automatic pay hold on non-DTC companies, which is an automated decision about pay. A new automatic release door (the late machine punch). A per-company setting that changes pay for everybody at once. A one-off bulk write that turns 80 paid days unpaid.
4. **How would we find out?** Today, mostly when a customer tells us. The refusal line goes to `frappe.logger("security")` (`access.py:28-48`). **I did not verify that this logger writes anywhere** (§8). The durable trace is the Attendance Version history (`track_changes: 1`, `attendance.json:327`), but `db_set`/`set_value` writes bypass it. Hence SEC-7, and the "who released it" record in PRIV-3.

## 2 · Data inventory: what 085 adds

| Item | Class (A1 vocabulary; A1 is not built) | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| Attendance `status = Held` (new Select value) | sensitive: personal attendance that decides pay | pay accuracy | inherits Attendance; no new clock | the employee; their manager on today's line view; HR in scope; System Manager |
| Release record: how (HR decision / machine punch + checkin id), who, when | internal | defend a pay decision in a grievance | as the Attendance row | the same as above |
| The missing time sent on a held day | sensitive (already exists on Attendance Request) | the correction | as today | the same as today |
| Company settings: hold switch, monthly limit, exempt roles | internal, not personal | configuration | life of the setting | read: anyone with Company read (stock: Employee holds read); write: see SEC-6 |
| Live "N days will be held" count | aggregate, no names | an informed save | not stored | HR Manager in scope |
| Backfill undo list: Attendance names, old status, new status, run id | personal by reference (ids only) | rollback | outside git, on the server; deleted when Surbhi confirms Grace's November pay is final. The Version rows stay with Attendance | Surbhi and the operator |

No new collection about a person: the held state is drawn from punches we already hold.

## 3 · Access intent, including who must NOT

| Actor | May | Must NOT |
|---|---|---|
| Employee | see own held days, why, and the pay effect; send the missing time | release their own day by any door; see a colleague's days |
| Line manager | see a direct report's held day and punch times (today's view); send a time for a **direct** report where the manager route is on | decide it; see a reason; see a team-wide held list or ranking |
| HR (User/Manager) in scope | see and decide held days of people in their companies/branches | decide **their own** day; decide a request **they raised**; touch anyone outside their scope |
| HR login with no company and no branch | nothing (Surbhi, 19 Nov, ALV-385) | release anything |
| HR Manager in scope | change the hold switch, limit and exempt roles for their companies | change another company's settings |
| HR User, Accounts Manager | read the settings | change them (stock Company write includes Accounts Manager, §4) |
| Machine sync account | file punches; a punch it files may release a day | anything else |
| CXO / System Manager | as today | nothing new is built for them |

**Correction to the brief.** The manager route is **not** a company switch. It is a site default, `alvoraa_manager_on_behalf_enabled`, and unset means on (`attendance_correction.py:1383-1400`). 085 does not need to change that.

## 4 · Abuse cases

| # | Actor and act | Today | Closed by |
|---|---|---|---|
| A1 | Staff member with a one-punch Held day phone-punches from home at 23:00, or calls `/api/resource/Employee Checkin` with `device_id` set to a store machine's name | Would release the day if release were "count is now even" | SEC-5 |
| A2 | HR User whose own day is Held ticks `alvoraa_held_confirmed` on their own row (permlevel 0, `allow_on_submit`, `payroll_fields.py:47-61`; Attendance has no validate hook, `hooks.py:160-164`) | Open | SEC-2 |
| A3 | The same HR User cancels their own Held row and amends it to Present in the Desk. Attendance has no `refuse_own_submit` (`hooks.py:160-164`) | Open | SEC-2 |
| A4 | HR User adds or deletes a punch on their **own** record: `checkin_has_permission` returns True for any HR role before any own-record check (`field_app_access.py:259-261`) | Open | SEC-2 |
| A5 | A manager who also holds HR raises for a report (`raise_for_report`), then submits the Attendance Request from the Desk or REST. The raiser check lives only in portal `decide` → `not_yours_yet` (`attendance_correction.py:1611`). The `before_submit` hook checks only the subject (`access.py:184-190`) | Open on Desk/REST | SEC-3 |
| A6 | HR login with no company decides any employee's request on a multi-company site | Open (`attendance_correction.py:323-329`) | SEC-4 |
| A7 | Accounts Manager turns the hold switch off for a company in the Desk | Would be open if the fields sit on Company with no permlevel | SEC-6 |
| A8 | The backfill is run twice, on the wrong site, or over October | Would be open without guards | SEC-7 |
| A9 | Someone with the machine-sync API key posts fake machine punches | Pays even days today; would release held days | Residual risk R2 |

A leaver cannot raise a request: `_employee_for` filters `status = Active` (`attendance_correction.py:277-283`, verified).

## 5 · Requirements

Each one says what must be true and how it is tested. "Fresh CI site" means one built by migrate alone, with no hand fixes (OPS-6, OPS-10).

### SEC-1 · A Held day is never paid while held, and is paid once released

- On every pay reader, Held counts as an unpaid day exactly as Absent does: the Salary Slip, and every reader in OPS-9's list, including those it marks "not checked".
- A release re-saves **only that employee's** draft slip (OPS-3). It does not rely on the batch job, which has been stalled since 18 Nov.
- When a release lands on a day inside a **submitted** slip, the release must not claim "your salary slip is updated". HR is told the slip is final (see Q3).
- A cancelled or deleted Held row must not fall back to "unmarked", because with `consider_unmarked_attendance_as = Present` that pays the day. SEC-2 refuses those doors.

**Test (fresh CI site):**
- A slip with two Held days has payment days 2 lower than the same slip with them Present.
- Release one: that slip goes up by 1, and another employee's slip keeps the same `modified`.
- Run both cases with `consider_unmarked_attendance_as` set to Present and then to Absent.
- A release inside a submitted slip leaves the slip untouched and returns the "slip is final" sentence.
- Break the Held mapping and watch the first test fail.

### SEC-2 · Nobody releases their own Held day, on any door

For a login whose own Employee record has a Held day, each door below is refused with `refuse` (rule SEC-9):
- `decide` (exists);
- Desk or REST submit of their Attendance Request (exists, `refuse_own_submit`);
- ticking `alvoraa_held_confirmed` or setting `alvoraa_confirmed_out_time` on their own row;
- cancel, amend or delete of their own Held row;
- REST `PUT` on the row;
- adding, changing or deleting an Employee Checkin on their own record, other than an ordinary new punch filed "now", which every employee may do and which never releases (SEC-5).

The scheduler and the auto-attendance job run as Administrator and stay unaffected. Suggested rung: reuse `refuse_own_decision` on Attendance (`before_submit`, `before_cancel`, `on_trash`, and `validate` for the two fields), plus an own-record check in `checkin_has_permission` before the HR early return. No new layer.

**Test:**
- An HR Manager and an HR User, each with a Held own day, try each door: all refused.
- The same acts on a colleague in scope succeed.
- The auto-attendance tick still marks and leaves Held rows alone (OPS-11).

### SEC-3 · Whoever raised a request does not decide it, on any door

Move the raiser rule (`owner == session user`, `attendance_correction.py:1611`) from portal-only to the document's `before_submit`, beside `refuse_own_submit`. The Desk, REST and imports then refuse a raiser exactly as `decide` does.

**Test:** a login holding both a manager role and HR User raises for a direct report through `raise_for_report`, then submits that request:
- via `decide`: refused (exists);
- via REST `submit`: refused;
- via Desk `savedocs` submit: refused.

A different HR login in scope then succeeds.

### SEC-4 · Every release and every settings change is scoped, and fails closed

`decide`, the settings endpoint and the live count use `permitted_employee_filters` (or `permitted_companies` for settings) with its fail-closed result:
- no company and no branch means nobody;
- System Manager and Administrator see everyone.

`_scope_conditions` returning None must no longer mean "no narrowing" on these paths.

**Test (a two-company site plus a branch-scoped HR):**
- a no-company HR login is refused on `decide` for every employee;
- company-A HR is refused on a company-B employee's request, and on company B's settings;
- branch HR is refused outside the branch.

Each refusal writes a SEC-17 line. **Blocked by Q1** for Grace's login.

### SEC-5 · Only a machine punch releases a day by itself, judged by who filed it

The automatic release fires on the **insert** of an Employee Checkin whose `owner` passes `is_machine_account` (`field_app_access.py:47-56`). It never fires on any of these:
- the `device_id`, which the sender chooses (`branch_geofence.py:95-98` says so);
- a recount after an edit or a delete;
- a punch added by HR;
- a phone punch (`alvoraa-field-app` runs as Guest, `web-portal`);
- a punch flagged `skip_auto_attendance` (ALV-302 out-of-range date) or folded as a repeat scan (ALV-337).

The count uses the same folded punches the hold marking used. The release record names the checkin.

**Test:**
- `do_checkin` from the portal, a REST insert with a machine's `device_id`, an HR-added punch, and a repeat scan inside the dedupe window: each leaves the day Held.
- A machine-account punch releases it, and the record names that checkin.
- Delete a punch from a 3-punch day as HR: the day stays Held.

### SEC-6 · The hold switch, the limit and the exempt roles are HR Manager's, in scope, on every door

- **Write rights.** Stock Company write is System Manager, Accounts Manager and HR Manager (verified in `alv084-bench`, `erpnext/.../company.json`). If the three settings sit on Company, they go at a permlevel that only HR Manager and System Manager can write (rung 2, configuration). HR User and Accounts Manager can read them, not change them.
- **The settings endpoint** checks the company against `permitted_companies` (SEC-4).
- **Every change is reconstructable** later: who, when, from and to.
- **The monthly limit is enforced on the Attendance Request document** (insert hook), not only in `raise_correction`. A REST or Desk insert is then counted like the portal. Held days never count. Exempt roles are exempt from the limit only, never from the hold.
- **The Grace Server Script is retired** only after the setting is read back live (OPS-5).

**Test:**
- HR User, Accounts Manager, and an HR Manager of another company: each is refused through the endpoint and through REST `PUT /api/resource/Company`.
- An HR Manager in scope saves, and a Version or Comment row records the change.
- A fourth REST-inserted request in a month with limit 3 is refused.
- A request for a Held day is accepted at any count.

### SEC-7 · The backfill is dry-run first, narrow, undoable and attributable

- **Scope.** A named script. Dry run is the default. Grace only, November 2026 only, odd-punch days only (Brief gate 3, Design gate D5).
- **Hard stops.** It refuses to run on any other company or month. It skips and reports any row inside a submitted Salary Slip. It stops if the live counts differ from the dry run.
- **Undo list first.** The undo list (ids only, §2) is written **before** the first change.
- **Audit row per change.** Each changed row gets an entry that survives a year: run id, from and to, when, and who ran it. If the script uses `db_set`, it must write this entry itself.
- **Re-runs are harmless.** A second run changes 0 rows.
- **Output.** Counts and Attendance ids only; no names.
- **Execution.** Run as a file with `env/bin/python`, not piped into `bench console` (memory: piped multi-line blocks are lost silently). Run after the deploy lands (OPS-7).

**Test (a copy of Grace's data):**
- The dry run writes nothing: row count and `modified` are unchanged.
- The real run matches the dry-run count, and the re-run reports 0.
- The undo restores every row's prior status exactly.
- A row in a submitted slip is skipped and listed.
- A run on another company or on October refuses.

### PRIV-1 · No new reader, no wider view

- Held and its punch times appear only where that person's day is already visible: own month, the manager's existing line view, and HR's in-scope register through its existing filter with one new value. The settings count is a number.
- **Not built:** no team held list, no ranking, no CXO figure, no new report, no new public route, no guest access, no new cache of attendance.

**Test:**
- A colleague is refused a peer's month.
- A manager is refused a non-report's month.
- Company-A HR's register filtered to Held shows no company-B row.
- The settings count response holds only an integer.
- The diff adds no `allow_guest` and no new `ignore_permissions`: the per-file ceilings in `test_portal_security_010` stay where they are.

### PRIV-2 · Collect the time only; nothing personal in logs, errors or files

> **PRIV-2 / no reason box: reversed by counsel, 21 Nov 2026 (ALV-418).** A reason is now required on every attendance request, a held day included. Built in slice 087. The rest of this item (nothing personal in logs, errors or files) stands.

- **The form.** The held-day form sends only the date, the missing time and In/Out. There is no reason box (Design gate D1).
- **Errors and logs.** Refusals and errors name no person the caller cannot already see. Log lines carry ids only (the `log_refusal` pattern).
- **The notice list.** The list of the 80 people Grace must tell is read by Grace HR in the register (Held filter), not exported or emailed by us.

**Test:**
- Press Send in a browser test and assert the payload's keys (memory: test what it sends).
- Grep the backfill and refusal output for `employee_name`: no hits.

### PRIV-3 · The automatic hold is visible to the person and can be challenged, and its record lasts

This is an automated decision about pay, so it gets the access-and-grievance treatment from counsel's 18 Sep line (memory file; I have not read the written advice):
- the person sees on their own day that it is Held, why (one punch, or three or five), that it is unpaid, and how it was released (by HR at a time, or by a machine punch at a time);
- the release record stays with the Attendance row.

**Test:**
- The employee's day sheet API returns the state, the reason code, the pay effect and the release source for each of the four states in the prototype.
- A year-old release can be traced to a person or a checkin id from the database alone.

## 6 · What must exist before each control can be seen working

Without these, "0 findings" means nothing (lesson 1):
- a company with the switch on and at least one odd-punch day **marked Held**;
- a machine account (Biometric Sync role, no Employee record) on the test site;
- a site with **two companies** and a branch-scoped HR login (SEC-4);
- a **draft** salary slip for the employee. Grace's draft-slip job has been stalled since 18 Nov (OPS-3), so a test must create its own.

## 7 · Obligations engaged

| Obligation | Source and date checked | What it asks of 085 |
|---|---|---|
| DPDP 2023 + Rules 2025: security safeguards, accuracy and correction, grievance | baseline §2, verified 24 Aug 2026. That was 87 days ago today; **stale from 22 Nov 2026** | SEC-2..6, PRIV-3. No new collection, so no new notice duty for us |
| Wage law: holding pay for a day | Code on Wages 2019 in force from 21 Nov 2025 per law-firm summaries ([DLA Piper](https://knowledge.dlapiper.com/dlapiperknowledge/globalemploymentlatestdevelopments/2025/government-of-india-notifies-the-labour-codes-ushers-a-new-era-of-compliances), [KS&K](https://ksandk.com/labour-employment/all-four-labour-codes-enforced-from-21-november-2025/)), searched 19 Nov 2026. **I did not find or read the text on deductions for absence** | see the flag below |

**⚠ COMPLIANCE.** "Q1 settled" in the Brief gate (19 Nov 2026) is **Surbhi's decision, not counsel's written view**. Her words: held days are regularised at month end, before salaries are paid. A one-punch day is evidence the person was present. Whether withholding that day's pay at cut-off is a lawful deduction under the Code on Wages and the state rules for Grace's state has not been put to counsel in writing, as far as I can see. I am not a lawyer. **I do not block on it.** I record it as accepted by Surbhi on 19 Nov 2026 (R1). If she wants it closed, the question for counsel is in Q4.

## 8 · What I could not check

- Whether `frappe.logger("security")` lines reach a file on dev or production. **Not checked.** To check, I would need to read `logs/security.log` on a bench after a refusal.
- Tenant Custom DocPerm on Attendance, Employee Checkin and Company. **Not checked.** I would need read-only site access.
- Which production sites hold more than one company (the real blast radius of SEC-4). **Not checked.**
- Whether HR Settings geolocation tracking is on at Grace. **Not checked.** SEC-5 does not depend on it.
- Whether Company has `track_changes` on the sites (SEC-6's audit). **Not checked.**

## 9 · Residual risk (proposed. Owner: Surbhi. Nothing is accepted until she says so)

| # | Risk | Label |
|---|---|---|
| R1 | Wage-law basis for withholding a day at cut-off rests on Surbhi's decision of 19 Nov 2026, not counsel's written view | intentional trade-off, **named and dated** |
| R2 | Anyone with a site's machine-sync API key can file punches for anyone, which pays even days today and would release held ones | temporary debt. Removed by a key-rotation runbook and an IP allow-list on the sync account (separate ticket) |
| R3 | A phone punch that makes a day even **before** marking is paid as today; 085 holds only odd counts | acceptable simplification. Not new, not widened |
| R4 | Any HR role can write **another company's** punches by record name (`field_app_access.py:259-261`, no company check). SEC-2 closes only the own-record door. A Major, pre-existing finding: **ticket it separately**, P2, owner `hrms-fullstack-engineer` | dangerous if left untracked; ticket now |

## 10 · Questions

**Must know**
- **Q1 (Surbhi).** My reading: HR with no company is HR for nobody, everywhere (your ALV-385 rule). The ALV-385 commit says this would cut off `hr@grace.alvoraa.co`. **Shall it get a Company User Permission for Grace Drinks before the switch is turned on?** Fail-closed default meanwhile: SEC-4 as written. Grace's HR cannot release until that is done.

**Should know**
- **Q2 (Surbhi).** After SEC-2, an HR person's own held day is decided by another HR person. At Grace, is there a second HR login? If not, the System Manager decides. That is acceptable, but say so.
- **Q3 (Surbhi, BA).** What should happen to a day released after the slip is submitted: arrears next month, or nothing? Default: no automatic pay change. HR is told, and the employee sees "paid in a later slip" only once you choose.

**Nice to know**
- **Q4 (counsel, only if Surbhi wants R1 closed).** "Under the Code on Wages 2019 and [Grace's state] rules, may an employer withhold a day's wage at payroll cut-off when the person punched in but not out, pending correction, where the day is released and paid on correction?"

## 11 · Subtract pass

I removed these:
- a separate requirement for the exempt-roles list (folded into SEC-6);
- a held-day notification requirement (none is being built);
- a requirement to scope HR punch writes by company (now R4, its own ticket, because it is pre-existing and wider than 085);
- a DPIA (no new collection; the processing already exists on DTC's engine);
- a request for a new log pipeline (§8 asks only to read the existing sink).

I added no new gate and no new tooling.

**Governance note.** I will also write `06-security-review.md` for this slice, which means verifying requirements I wrote. The technofunctional reviewer should check SEC-2 and SEC-5 independently.
