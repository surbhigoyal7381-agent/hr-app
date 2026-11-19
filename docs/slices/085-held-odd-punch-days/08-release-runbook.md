---
slice: 085-held-odd-punch-days
artifact: 08-release-runbook (US-17, AC-64 to AC-67)
author: hrms-fullstack-engineer
date: 2026-11-19
status: WRITTEN, NOT RUN. Nothing here has been executed on any server. Every deploy step needs Surbhi's own word.
---

# 085 release runbook (ALV-392)

Plain steps for Surbhi or the operator. Each step says what to read back. A step is not done until the read-back is written down. Two releases: **Release 1** (safety doors) ships alone; **Release 2** (Held) comes after.

**Not checked by me:** the server, the job schedule at Grace (the 06:00 slip job is from a memory note), the free disk, the tag names in the package. Read each one on the day.

## 0 · Before either release

1. Window: **00:30 to 05:30 IST** only, on Surbhi's word. Stop at 05:30 whatever is left. Grace's slip job is believed to run at 06:00: read its schedule from the site first and do not overlap it (OPS-18).
2. **Disk and queue gate** (OPS-23): read free disk on the server and the length of the job queue. Stop if disk is low or the queue is not near empty. A big permission clean-up once filled the queue at DTC (5 Nov).
3. Check the previous image tag exists in the `alvoraa-app` package, so rollback is possible (OPS-22).
4. CI is green on `dev` and nobody else's push is running (a new push cancels the running one).

## 1 · Release 1 (the doors)

**Before the push, per tenant (Q1 and the US-13 side effect):** list every login that holds HR Manager or HR User and has **no Employee record and no Company User Permission**. After Release 1 each of them sees nobody on the attendance month view, the picker and the approve/decline screen. Give each a Company User Permission first. For Grace: `hr@grace.alvoraa.co` (AC-52). Read the permission row back. The count of such logins on dev, DTC, Grace, aahr and PPJ was **not checked** when this was written.

1. Deploy. Prove it landed by three things: the pin file, the running container, and the file itself (not the green tick alone: an old tag can deploy green).
2. After any `docker cp`, bump `sites/assets/assets.json` in the sites volume and compare the volume copy with the image's (OPS-13). Otherwise phones keep the old script.
3. Check: an HR login with a company can approve a colleague's correction; the same login cannot approve its own, cannot cancel or delete its own attendance, and cannot change its own punch. A named System Manager who raised a request cannot submit it.
4. Release 1 has no data to undo.

## 2 · Release 2 (Held)

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
   - Real run: the same command with `--apply`. It writes the undo list before each chunk of 50 and commits per chunk. It refuses any other site and any day outside 1 to 30 November 2026.
   - Read back: the count of Held rows for November at Grace equals the count it printed. Keep the undo file safe; copy it off the server.
   - Draft slips re-price when next saved. HR re-saves them, or the next slip run does.
9. **Look at the first two daily runs.** Count Error Log entries that mention "Held" (not released, not refreshed) since the release. Check the queue workers by `rq:workers` registration and heartbeat, not by `docker ps` (OPS-21).

## 3 · Held days must be looked at before pay

HR opens the Attendance list, chooses status Held, and releases or leaves each day **before** the salary slips are made. A day released after its slip is submitted changes nothing: HR adds an Additional Salary for it. One count to keep: releases that landed on a submitted slip (the HR card says so each time).

## 4 · Rollback (AC-65)

- **Release 1:** redeploy the previous image tag with migrations off. Nothing to restore.
- **Release 2:** **first restore the backfilled rows from the undo file** (`--undo --undo-file <the same file>`; it puts back only rows still Held and leaves any a human released). **Then** redeploy the previous image tag with migrations off. If the old code runs while rows are still Held, those days are paid as normal days. The Property Setter that adds `Held` may stay: an unused status option is harmless. Expect the broken `bench version` wait of about 7 minutes (22 Sep reading, not re-measured).
- Days that became Held after the backfill (from normal marking) have no undo file. Release them by hand or leave the switch on.

## 5 · Cache headers (AC-66, OPS-12)

Read in `deploy/nginx.conf`: `Cache-Control "public, immutable"` appears only on `/assets/` (two blocks, production and dev). No block adds a cache header to the whitelisted calls the Held sheet uses. **Not proved:** what Frappe itself sends on those responses. Before Release 2, open the month call in the browser's network tab and read the response headers; none may allow storing.

## 6 · Read-through checklist for Surbhi (AC-64)

- [ ] Release 1: HR logins without a company counted per tenant and given one
- [ ] Window, disk and queue read; previous tag exists
- [ ] Deploy proved by pin file, container and file; `assets.json` bumped
- [ ] Migrate: sites migrated equals sites existing; `Held` and three fields read back
- [ ] Grace limit, exempt list saved and read back; test day passed
- [ ] Script disabled (not deleted) and read back; test day passed again
- [ ] Switch on; card's count written down
- [ ] Dry run count agrees; real run; Held count read back; undo file copied off the server
- [ ] First two daily runs: Error Log count read
- [ ] Rollback order understood: undo list first, old image second
