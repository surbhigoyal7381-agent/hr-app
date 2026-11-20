---
slice: 085-held-odd-punch-days
artifact: 08-release-runbook (US-17, AC-64 to AC-67)
author: hrms-fullstack-engineer
date: 2026-11-19
status: WRITTEN, NOT RUN. Nothing here has been executed on any server. Every deploy step needs Surbhi's own word.
---

# 085 release runbook (ALV-392)

Plain steps for Surbhi or the operator. Each step says what to read back. A step is not done until the read-back is written down. **ONE release** (Surbhi's decision, 20 Nov 2026). The safety doors and Held ship together. The hold switch is OFF for every company, DTC included (the Custom Field default is 0, pinned by a test), and is switched ON for Grace only, after the release, by the steps in section 2. Sections 1 and 2 below are two checklists inside that one release, not two releases.

**Not checked by me:** the server, the job schedule at Grace (the 06:00 slip job is from a memory note), the free disk, the tag names in the package. Read each one on the day.

## 0 · Before the push

1. Window: **00:30 to 05:30 IST** only, on Surbhi's word. Stop at 05:30 whatever is left. Grace's slip job is believed to run at 06:00: read its schedule from the site first and do not overlap it (OPS-18).
2. **Disk and queue gate** (OPS-23): read free disk on the server and the length of the job queue. Stop if disk is low or the queue is not near empty. A big permission clean-up once filled the queue at DTC (5 Nov).
3. Check the previous image tag exists in the `alvoraa-app` package, so rollback is possible (OPS-22).
4. CI is green on `dev` and nobody else's push is running (a new push cancels the running one).

## 1 · The doors checklist (part of the one release)

**Before the push, per tenant (Q1 and the US-13 side effect, OPS-36):** list every login that holds HR Manager or HR User and has **no Employee record and no Company User Permission** (query B in section 7). After this release each of them sees nobody on the attendance month view, the picker and the approve/decline screen. Give each a Company User Permission first. For Grace: `hr@grace.alvoraa.co` (AC-52). Read the permission row back. The count of such logins on dev, DTC, Grace, aahr and PPJ was **not checked** when this was written.

1. Deploy. Prove it landed by three things: the pin file, the running container, and the file itself (not the green tick alone: an old tag can deploy green).
2. After any `docker cp`, bump `sites/assets/assets.json` in the sites volume and compare the volume copy with the image's (OPS-13). Otherwise phones keep the old script.
3. Check: an HR login with a company can approve a colleague's correction; the same login cannot approve its own, cannot cancel or delete its own attendance, and cannot change its own punch. A named System Manager who raised a request cannot submit it.
4. The doors have no data to undo.

## 2 · The Held checklist (part of the one release)

Order matters. Do not skip a read-back.

1. Deploy, prove it landed (as above), bump `assets.json`.
2. **Migrate finished on every site.** Write down: sites migrated, sites that exist. They must match (OPS-14). Do not start step 3 on a half-migrated server; check the queue, re-run the migrate.
3. **Read back on each site** (AC-2): the Attendance `status` options contain `Held`; the three Company fields exist (`alvoraa_hold_odd_punch_days`, `alvoraa_monthly_request_limit`, `alvoraa_limit_exempt_roles`).
4. **Grace only, the three Company values.** In the settings card (or on the Company), as an HR Manager of Grace or a System Manager, set the monthly limit to 3 and the exempt list to `Sales Executive` (a designation; the card accepts a role or a designation). Switch **off** for now. Read the three values back from the live site.
5. **One test day for the limit**, before the script is touched: an ordinary request is refused on the 4th in the month with the new sentence; a Sales Executive is not.
6. **Retire Grace's Server Script "Grace Attendance Regularisation Limits"** (Attendance Request, Before Save): set `disabled = 1`, **do not delete**; read it back as disabled; repeat the test day (AC-44). If both rules ran, a 4th request would be refused twice with two sentences. The new rule counts as the script did: same month of `from_date`, not cancelled, not Declined (the script's "Rejected"), never itself; a held-day request is not counted.
7. **Switch on for Grace** (hold odd-punch days). The card's Save button shows how many days this month would be held. Write the number down.
8. **The November backfill, Grace only.** Run from the bench folder with the bench's own python, never piped into the console:
   - Dry run (the default): `env/bin/python <repo>/scripts/alv392_held_backfill_grace.py --site grace.alvoraa.co --undo-file <a path OUTSIDE the repo>`. It prints a count. It must agree with step 7's number (within the days marked since). Read both.
   - The dry run saves its count beside the undo file (`<undo file>.dryrun`). The real run needs it, and **stops if the live count is different** (AC-63): run the dry run again and read both numbers.
   - Real run: the same command with `--apply` and the SAME undo file. It writes the whole id list to the undo file before changing anything (AC-58), then holds in chunks of 50, committing per chunk. It skips any day inside a submitted salary slip (AC-62). It refuses any other site and any day outside 1 to 30 November 2026.
   - Read back: the count of Held rows for November at Grace equals the count it printed. Keep the undo file safe; copy it off the server.
   - Draft slips re-price when next saved. HR re-saves them, or the next slip run does.
9. **Look at the first two daily runs.** Count Error Log entries that mention "Held" (not released, not refreshed) since the release. Check the queue workers by `rq:workers` registration and heartbeat, not by `docker ps` (OPS-21).

## 3 · Held days must be looked at before pay

HR opens the Attendance list, chooses status Held, and releases or leaves each day **before** the salary slips are made. A day released after its slip is submitted changes nothing: HR adds an Additional Salary for it. One count to keep: releases that landed on a submitted slip (the HR card says so each time).

## 4 · Rollback (AC-65)

- **The doors (if only they must go):** redeploy the previous image tag with migrations off. Nothing to restore.
- **Held:** **first restore the backfilled rows from the undo file** (`--undo --undo-file <the same file>`; it puts back only rows still Held and leaves any a human released). **Then** redeploy the previous image tag with migrations off. If the old code runs while rows are still Held, those days are paid as normal days. The Property Setter that adds `Held` may stay: an unused status option is harmless. Expect the broken `bench version` wait of about 7 minutes (22 Sep reading, not re-measured).
- Days that became Held after the backfill (from normal marking) have no undo file. Release them by hand or leave the switch on.

## 5 · Cache headers (AC-66, OPS-12)

Read in `deploy/nginx.conf`: `Cache-Control "public, immutable"` appears only on `/assets/` (two blocks, production and dev). No block adds a cache header to the whitelisted calls the Held sheet uses. **Not proved:** what Frappe itself sends on those responses. Before the push, open the month call in the browser's network tab and read the response headers; none may allow storing.

## 6 · Read-through checklist for Surbhi (AC-64)

- [ ] HR logins without a company counted per tenant and given one (query B, expect 0)
- [ ] Each HR login's permitted companies compared with the companies it approves for (section 7, S-1)
- [ ] Sync accounts: rows read back, one test punch per account, stray-row count read (section 7, OPS-35 and S-3)
- [ ] Migration rehearsed on copies of the Grace and DTC backups (section 7, OPS-38)
- [ ] Window, disk and queue read; previous tag exists
- [ ] Deploy proved by pin file, container and file; `assets.json` bumped
- [ ] Migrate: sites migrated equals sites existing; `Held` and three fields read back
- [ ] Grace limit, exempt list saved and read back; test day passed
- [ ] Script disabled (not deleted) and read back; test day passed again
- [ ] Switch on; card's count written down
- [ ] Dry run count agrees; real run; Held count read back; undo file copied off the server
- [ ] First two daily runs: Error Log count read
- [ ] Rollback order understood: undo list first, old image second

## Added 20 Nov 2026 (one release, and three risks closed)
- **Company permissions for HR and for sync accounts.** After this release an HR login may add, change or delete punches, and approve attendance, only for the companies it may act for (its Company User Permissions, else the company on its own Employee record, else nothing). Count HR logins with neither, per tenant, and fix them BEFORE the push (same list as the first checklist).
- **Sync accounts (R2).** A sync account is limited to its companies only once it has Company User Permission rows. Until then it files for everyone, as today, so no tenant repeats the 2 Nov outage. **Operator step per tenant: add one Company User Permission row per sync account for each company it serves, then file one test punch and read the security log for an R2 line when a punch outside the list is tried.**
- **Monthly limit.** A request HR files for an employee neither counts nor is refused.

## 7 · Checks to run before the push (added 20 Nov 2026; OPS-35 to OPS-38, S-1, S-3)

Read-only queries are run per tenant from the bench folder with `bench --site <site> mariadb`, not piped into `bench console` (13 Nov: piped scripts lose lines). Write each result down in the release record. None of this has been run.

**OPS-35 · Sync accounts and their Company rows (R2).** An account with no row files for everyone, so R2 does nothing until the rows exist.
```
select r.parent as account, count(p.name) as company_rows, group_concat(p.for_value) as companies
from `tabHas Role` r
left join `tabUser Permission` p on p.user = r.parent and p.allow = 'Company'
where r.parenttype = 'User' and r.role = 'Biometric Sync'
  and not exists (select 1 from `tabEmployee` e where e.user_id = r.parent)
group by r.parent;
```
First find which companies each sync account really punches for (last 30 days). This assumes the sync tool files punches as its own account, so `owner` is that account. Read one punch to confirm before trusting the result:
```
select c.owner as account, e.company, count(*) as punches
from `tabEmployee Checkin` c join `tabEmployee` e on e.name = c.employee
where c.time >= now() - interval 30 day
  and c.owner in (select parent from `tabHas Role` where parenttype = 'User' and role = 'Biometric Sync')
group by c.owner, e.company;
```
**Having no rows is the planned state at release** (03 §17). This is R2a, and it **waits for Surbhi's named, dated acceptance**. Do not push to main without it. Adding rows is a **separate step after the release, on Surbhi's word**. Each account's rows must cover EVERY company in the query above. A narrower row refuses that machine's punches for the missing company, and the sync tool stops the batch. When that step is approved, add the row with `apply_to_all_doctypes` OFF and `applicable_for` = Employee Checkin (the narrow pattern). Then file ONE test punch per sync account for an employee of its company and read that it saved. Prove the refusal on **dev**, not production: a punch for another company, then the `R2` line in `security.log`. On a one-company tenant write "R2 adds nothing here". On DTC the count of accounts is read, not assumed to be 8.

**S-3 · Stray rows (count, expect 0 or rows that apply).** A row that does not apply to punches is ignored since this fix, but read it anyway:
```
select p.user, p.for_value, p.applicable_for, p.apply_to_all_doctypes
from `tabUser Permission` p join `tabHas Role` r on r.parent = p.user and r.role = 'Biometric Sync'
where p.allow = 'Company';
```
Every row listed either applies to all doctypes or has `applicable_for` = Employee Checkin, and names a company the machine serves. A row for any other doctype does nothing and can be removed.

**OPS-36 · HR logins with no company (M-2 lock-out).**
```
select u.name from `tabUser` u
join `tabHas Role` r on r.parent = u.name and r.parenttype = 'User' and r.role in ('HR Manager','HR User')
where u.enabled = 1 and u.name <> 'Administrator'
  and not exists (select 1 from `tabHas Role` s where s.parent = u.name and s.role = 'Biometric Sync')
  and not exists (select 1 from `tabEmployee` e where e.user_id = u.name and e.status = 'Active' and ifnull(e.company,'') <> '')
  and not exists (select 1 from `tabUser Permission` p where p.user = u.name and p.allow = 'Company')
group by u.name;
```
Expect 0 rows. Each name returned needs a Company User Permission first. (`permitted_companies` reads only an **Active** Employee record, so an HR login whose own record has left counts as having no company.)

**S-1 · Permitted companies against the companies each login really approves for (per tenant).** For every login holding HR Manager or HR User (and every CXO without System Manager): list its permitted companies (its Company User Permission rows, else the company on its own Employee record) and the companies whose Attendance Requests and Leave Applications it decided in the last 60 days. Any company it decided for that is not in its permitted list needs a Company row first. Otherwise, from the morning after, that login is refused when it approves, cancels or amends Attendance and Attendance Requests, or writes punches (R4, R5). A System Manager sees every company and is not affected. **Leave approval is not limited by this** (stock code skips the hook, S-2). The one exception: approving a leave that covers a holiday cancels that day's Attendance, and that cancel is checked.

The companies each login decided for (submitted requests, last 60 days; `modified_by` is the last person to act, which for a submitted request is normally the approver):
```
select d.modified_by as login, e.company, count(*) as decided
from `tabAttendance Request` d join `tabEmployee` e on e.name = d.employee
where d.docstatus = 1 and d.modified >= now() - interval 60 day
group by d.modified_by, e.company
union all
select d.modified_by, e.company, count(*)
from `tabAttendance` d join `tabEmployee` e on e.name = d.employee
where d.docstatus in (1, 2) and d.modified >= now() - interval 60 day
  and d.modified_by in (select parent from `tabHas Role` where role in ('HR Manager','HR User'))
group by d.modified_by, e.company;
```
Compare each login's companies here with its permitted companies: its Company User Permission rows, else the company on its own **Active** Employee record. Every login and company pair here that is not permitted needs a row before the push.

**OPS-37 · hr@grace is a read-back, not a grant.** The row was granted on 20 Nov 2026 (Surbhi, in that session). Read it back before the push and write the value:
```
select user, allow, for_value, applicable_for, apply_to_all_doctypes
from `tabUser Permission` where user = 'hr@grace.alvoraa.co' and allow = 'Company';
```
Expect one row whose `for_value` is Grace's company exactly as the Company record spells it.

**OPS-38 · Migration dry run on copies (once, before main).** In a throwaway stack following `REHEARSAL.md`: restore the latest Grace and DTC backups (write the file names and dates). Record `select count(*) from `tabCustom DocPerm`` and the job-queue length. Run `bench --site <copy> migrate`. Record both again. Read that Attendance `status` options include Held, that the three Company fields exist, and that the hold switch is 0 for every company. Run the backfill's dry run against the Grace copy. **Stop if the Custom DocPerm count or the queue length moves.** Remove the throwaway stack and say so.
