# 07 DevOps inputs, slice 087 attendance follows the punches

## §1 Brief, first look (20 Nov 2026)

Read: worktree `087-attendance-follows-punches` at dev `2e31151f`; `alvoraa_portal/alvoraa_portal/held_day.py` (`release_on_machine_punch`, `refresh_slip_job`) and its `hooks.py` entry. **No server command run. Nothing measured.** Every number below is an estimate or a count from code, and is marked.

**Red flags first**

1. **P1: the hook must never do the re-work inline.** Today's Held hook (fact, read in code) does the rework inside the punch request: a role check, `_punches()` (a read of that day's punches), `worked_out`, a write, then it enqueues the slip job. That is acceptable for Held days only (rare). If it runs for every punch of every status, each punch on the sync path pays for a re-work. A bad one stalls the sync tool's whole batch.
2. **P1: the sync tool halts a batch on an unknown refusal** (given). The existing try/except around the hook is right and must stay the outermost layer. Also a lock wait or a deadlock is an error that can reach the punch's own transaction; the hook must not hold a lock the punch needs.
3. **P2: the slip refresh is the expensive part** (inference: it re-saves a whole Salary Slip, which re-runs the pay engine for the month). It must never run once per punch.
4. **P2: the `refresh_slip_job` argument shape is fine** (employee id and date, no secrets). Keep it so.
5. **P2: the guards need one test each, with a failing run first:** leave, hand-marked, submitted slip. "Hand-marked" has no field today that I have read `[ASSUMPTION]`; the engineer must say how it is told apart from a machine-made row, or the hook will overwrite HR's decision.

**Per-punch cost on the sync path**

- Estimate, not measured: a normal punch today pays one role check (`files_as_machine`) plus the usual insert. The new design adds, for every punch, one lookup of that day's Attendance and a decision. That is one indexed read, small.
- The cost that matters is only on a punch for a day that already has Attendance. Recommend: the hook does the one read, and if a re-work is needed it **only records "this employee-day is dirty" and enqueues**. It does the re-work in the job, not in the request. Recommend measuring the added time per punch on a dev copy before anyone calls it fine (target: no visible change in a batch of 200 punches).

**The burst after a machine is emptied**

- Count from the facts: 8 machines, sync every ~5 minutes, emptied 12:00-15:45 and 23:00-24:00. A machine at DTC holds up to a few hundred punches `[ESTIMATE: 442 staff over 8 machines is about 55 people per machine, two to six punches each, so roughly 100-300 punches per machine batch]`. Most of those punches belong to days that have no Attendance yet (today's day), so they need no re-work at all. Re-works come from late punches for days already made (yesterday and earlier), which I expect to be a minority. **I could not check how many.** Recommend counting from dev data: punches per day that arrive after that day's Attendance exists.
- Worst case, by arithmetic: if a whole batch of 300 were late punches, plain per-punch queueing gives up to 300 re-works and 300 slip refreshes. The same people punch two to six times, so per employee-day it is about 55-150 per machine. **Recommend deduplicating per employee-day**, not batching by time.
- How: one job per employee-day with a fixed job id (`rework|employee|date`). Frappe's `enqueue(job_id=..., deduplicate=True)` skips a job that is already waiting (`[ASSUMPTION]` the Frappe version here supports `deduplicate`; the engineer must check that in the installed code). That is the smallest thing: no new table, no new scheduler. A separate slip refresh per employee **per month**, not per day (slip covers the month), so one employee with five late days gets one refresh. Recommend the slip refresh is a second job id `slip|employee|period`, queued after the re-work.
- Rejected, cheaper to climb first: a "dirty" table plus a sweeper job. It is another moving part. Use it only if deduplication by job id is shown not to work.

**Queue choice**

- Recommend the `short` queue for the day re-work (small, one employee-day) and `default` for the slip refresh, or `short` for both if the pay engine run is measured under the short timeout `[ASSUMPTION: short is 300 s in Frappe, unverified here]`. Do not use `long`: a burst would sit behind provisioning and migrations, and the reverse (provisioning waiting behind punches).
- Check worker count: which worker listens on `short` in `deploy/compose/*.yml` is **not checked**. A queue with no worker is the failure of lesson 1. The release plan (§5) must prove a worker is registered on the queue, not just that the container is Up (lesson 15).

**Race: Frappe's auto-attendance job against the hook**

- Fact (given): the job runs per Shift Type, every 3-4 minutes on the scheduler tick. It picks Checkins with no `attendance` link and makes the Attendance. The existing hook links the punch to the day (`attendance` set) so the job does not take it as unmarked.
- Race 1: a punch arrives, the job has not yet run, the day has no Attendance. The hook does nothing; the job makes the day. Fine.
- Race 2: the hook re-works a day while the job is writing the same day. Possible results: two Attendance rows for one employee-day (Frappe throws a duplicate error in the job, which then loses that shift's batch of work) or one overwrites the other. **Inference:** this is the real risk of the slice, not the speed.
- Recommend: **the re-work job is the only writer of a day that already has Attendance.** It also re-reads the day inside the job, takes a row lock, and decides again from the punches at that moment, so the last runner always judges from all punches. It must not create a second row.
- Recommend: the engineer proves it with a test that runs the Frappe job and the re-work back to back and in reverse order, and asserts one row.

**Locking**

- Recommend the smallest: `SELECT ... FOR UPDATE` on that Attendance row (`frappe.db.get_value(..., for_update=True)`) inside the re-work job, and the deduplicated job id so two jobs for one day are not queued at once. No Redis lock, no new library.
- Keep the lock short: read, decide, write, commit. Never hold it across the slip refresh. Deadlock risk comes from taking Attendance then Salary Slip in one job while the slip save reads Attendance; keep them as two separate jobs in that order.
- The "Recalculate from punches" button should go through the same job (or the same function under the same lock) so HR and a punch never fight.

**Rough run cost**

- No new container, volume, dependency or schedule. Cost is worker time only.
- Estimate: a re-work of one day is a few queries `[ESTIMATE, not measured]`; a slip save is the heavy one, likely seconds each. At 100 slip refreshes per burst `[ESTIMATE]`, that is minutes of one worker, spread across the day and deduplicated by month. Fits inside a 3-4 minute tick only if the refreshes are deduplicated. **Measure one slip save time on dev before the strategy gate.**
- Month-end and payroll-run time is worse: the pay run and the refreshes compete for the same worker. Recommend not refreshing a slip that HR has open for a run; the engineer already guards submitted slips, and that must also skip when the run is in progress `[ASSUMPTION: no flag exists for that, unchecked]`.

**Other traps carried in from memory (not re-checked today)**

- Absence backfill trap: a re-work must not create Absent for days before joining or after leaving. The re-work should only touch a day that **already has** an Attendance row, never create one for a day with none (that remains the auto-attendance job's task). That also removes most of the race.
- Migrate queue overload (5 Nov): the first run of any patch that touches existing Attendance will make a flood. If the slice ships a backfill, **do not enqueue per row**; run it per employee-day in a throttled loop, or not at all. Recommend no backfill: the button covers old days.
- Fix-request approval inserting a Checkin fires the same hook. It must be marked so it re-works once, not twice (the approval path and the hook both firing).
- Inserted regularised punches are not from the machine account, so the hook's `files_as_machine()` gate skips them. Good for loops, but the approval path then owns its own re-work call and slip refresh.
- `skip_auto_attendance=1` on a wrong punch: the hook ignores it already. Also the job must then un-count it; that changes the day, so it also needs a re-work.

**Priority view**

- Feasible with no new infrastructure. Risk is concentrated in the race and in the slip refresh volume, not in cost. Nothing here should lower its priority; it should be sized as Tier 1 (pay and data).

## Items

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-1 | Hook only decides and enqueues; the re-work runs in a job. Outer try/except stays | Sync tool stops a machine's batch on an unknown refusal | A slow or failing hook stalls punches from a machine | P1, Recommend | |
| OPS-2 | One re-work job per employee-day with a fixed job id; one slip refresh per employee per month | A burst of 100-300 punches per machine batch | Hundreds of whole-slip saves per emptying | P2, Recommend | |
| OPS-3 | Re-work only a day that already has Attendance; one writer; row lock; re-decide from punches inside the job | Race with Frappe's auto-attendance job | Duplicate or overwritten day | P1, Recommend | |
| OPS-4 | Queue `short`; confirm a live worker on it in `deploy/compose/*.yml` and by `rq:workers`, not `docker ps` | Lessons 1 and 15 | Jobs queued forever | P2, Recommend | |
| OPS-5 | Measure on dev: added time per punch; one slip save; late punches per day. Then size | Every number here is an estimate | Wrong sizing | P2, Recommend | |
| OPS-6 | No backfill patch; the button covers old days | 5 Nov migrate overload | Stopped migrate, later sites left behind | P2, Recommend | |
| OPS-7 | Say how a hand-marked day is told apart from a machine-made one | No field I have read does this | HR's decisions overwritten | P1, Recommend | |

**Subtract pass:** I removed a dirty-table design and a Redis lock from the advice (both unneeded for the stated volume). I left out no queue or worker advice that is needed.

**Not checked:** compose queue and worker layout, Frappe version's `deduplicate` support, queue timeouts, any real timing or counts. **Left behind:** nothing but this file; not committed.

---

## §2 Design (20 Nov 2026)

Read: worktree `087-attendance-follows-punches`, dev `2e31151f`; `01b-ux-design.md`, the brief's decisions, `held_day.py`, `attendance_correction.py` `decide()`, vendored `hrms/.../shift_type.py`, `portal.js`, `docker-compose.app.yml`. **No server command run. Nothing timed.** The prototype link given is https://claude.ai/artifact/FWLLW4sa9UmAYKccSHYGpz; I did not open it, I read the design text and the file list only.

**Scope change, first.** Part 1 is held, the button is dropped. OPS-1, 2, 4, 5, 6 fall away from this slice (see the table at the end). The only burst left is one HR person approving one request at a time: no burst.

### Page weight on a 3G phone

- **Fact:** `portal.js` is 1,297,945 bytes raw (1.3 MB), measured by `ls -l` today. The form lives in it. **Not checked:** the gzip size or nginx compression.
- The design says the form adds no call until Send. **Estimate:** the new form and card code is a few KB raw (the 085 held form is the comparable); next to a 1.3 MB file that is noise. This slice does not move the ≤ 2.5 s budget by itself. The first load of that bundle on 3G is the existing cost and is already over any 2.5 s budget `[ESTIMATE: 1.3 MB gzipped is perhaps 300-400 KB; I did not measure]`. Not this slice's debt; FYI.
- Send payload: a time, a kind, a list of punch times, a note. Well under 1 KB `[ESTIMATE]`. No photos, no files on the punch path.
- HR card: a handful of punches plus one result sentence. **P2, Recommend:** the result line is a judge per pending request. With N pending cards that is N day-judgements on page open. Compute them in one request, and measure with about 50 pending requests on dev (the design says a card can be shown for each). If it is slow, compute the sentence only when a card is opened. Do not cache it (see below).
- **P1 for release, not for design:** a new `portal.js` only reaches users if the sites volume's `assets.json` moves. Lessons: the volume hides the image's assets, and `?v=` is one timestamp. §5 must compare `assets.json` in the volume against the image, not trust a green deploy.

### The approval path: inline or a job?

- **Fact:** `decide()` already submits inline, and 085's `release_by_hr` already refreshes the draft slip inline (`held_day.py` line 390, with its own savepoint and try). That is the precedent.
- Work per approval: insert one punch, set one aside, judge one day, one write to the Attendance row, re-save one employee's draft slip. One day, one employee, one click by a person.
- **Recommend: do the day work inline, in the approval's own transaction, so HR sees the real result and the toast is true.** One transaction means a failure rolls back the punch and the status together. No half-fixed day.
- **Recommend: the slip refresh stays where 085 put it (inline, own savepoint, never fails the approval), unless one slip save measures over about 2 s on dev; then use the existing `refresh_slip_job` on `short`, `enqueue_after_commit=True`.** `short` has a worker: `bench worker --queue default,short` (read, `docker-compose.app.yml` line 305). **Unknown:** the slip save time; it is the one number to take on dev. Rung: reuse what exists; no new job, queue or table.
- A decide on a day that went onto a final slip after the request was sent: refuse in words and write nothing (the design has this; I support it).

### Race with Frappe's auto-attendance job: does it still apply?

- **Yes, a smaller version. Do not drop OPS-3.** Fact (read): the job takes Checkins in its window that have no `attendance` link and `skip_auto_attendance` 0, groups them by employee and shift start, and marks a day. An HR-inserted punch on a recent day, with no link, is exactly such a punch. **Inference:** the job could pick it up and try to mark a day that already has a row. I did not read the duplicate-handling code to the end, so I do not say what it does then. **Not checked.**
- **Recommend (cheap, already done in 085, line 415):** when inserting the punch, set its `attendance` link to the day's row in the same transaction. Then the job never sees it. The set-aside punch gets the new field and `skip_auto_attendance=1`, so the job also ignores it. The only writer of the day is then the approval. No lock library.
- **Recommend:** read the Attendance row `for_update` inside the approval, so a double click or two HR people on one request meet a row lock, and the second finds "already decided" (that guard exists: `docstatus != 0`). Keep it short; slip refresh after it.
- Test, with a failing run first: run the job and the approval in both orders on one day; assert one Attendance row and the same count in the day sheet, the row and the engine.
- Back-dated punches only matter inside the job's window. An old day is outside it. FYI, `[ASSUMPTION]` the window is as I read it; the engineer should confirm it on the DTC Shift Types.

### Never cached, never public

- The three new calls (send the fix, list for HR, decide) are signed-in only. **Recommend:** no `allow_guest`; no `frappe.cache` of the result sentence or the punch lists (a cached sentence is a stale pay claim); nothing in the Inbox payload beyond what the HR card shows. The set-aside reason and the employee's note are personal data: HR and the employee only, never in a manager view.
- **Fact:** the only service worker I found is `hrms/frontend/public/sw.js`, and it precaches the Vite manifest only (`precacheAndRoute`). **Not checked:** whether the portal page registers a worker, and whether any worker caches API responses. Recommend the test engineer confirm no API response is cached.
- Refusal sentences must name no leave type and no hand-marker's name (the design already says this). Logs hold ids, not words (next section).

### Audit trail, no free text in logs

- **Fact:** 085 writes release fields on the Attendance row (how, by, when) because `set_value` skips the Version row. Same trap here: the inserted punch has a normal insert (Version/creation/owner exist, if the DocType tracks changes `[not checked]`), but **the set-aside is a flag change and the Attendance write is `set_value`, which leave no history.**
- **Recommend, smallest:** the set-aside punch and the added punch each carry fields (who approved, when, the request name) on the Employee Checkin: `regularised` mark, the request link, the approver's user id, the time. Those are Custom Fields, no new DocType, and the request document already holds the employee's note and HR's note. The log line (and any `frappe.log_error`) carries ids only: request name, checkin name, approver user id, employee id, date. **Never** the note text, the explanation, the time the employee typed is fine (not free text) but the reasons are not.
- Whether the set-aside is reversible (can HR un-set it?) is a product question. If not, say so on the card. Not mine.
- Retention: the added punch is evidence the employee sees as "Added by HR". The compliance question (counsel) is open and blocks switch-on, not the build. The design's kill criterion 3 stands.

### Other run notes

- No new container, volume, queue, schedule or dependency. New Custom Fields only: they need a `bench migrate` on every tenant (§5; check the migrate queue before running, 5 Nov).
- Engine honours the new field: the dry run is the real gate. **Recommend the dry run reads a copy of DTC data and compares every day's verdict before and after, expecting a change only on test days.** Cost of a miss: pay for 442 people changes silently. P1.
- Insert as the approver, or the F1/R4 checks refuse (brief notes). Insert fires `release_on_machine_punch` too, but it exits for non-machine accounts; prove it in a test. An HR add must not trigger a second release (brief notes agree).
- ALV-410 (the missing punch added on approval) is in scope; `release_by_hr` counting the typed time as an "extra" while a real punch is also added would count it twice (brief notes). That is a correctness P1 for the engineer, not an ops one; flagged.

### Which of OPS-1 to OPS-7 still apply

| ID | Status | Why |
|---|---|---|
| OPS-1 hook only enqueues | **Out** (part 1 held) | No punch-path change. Do not touch the sync path in this slice. |
| OPS-2 dedupe per employee-day | **Out** | No burst; one approval is one day. |
| OPS-3 one writer, row lock, re-decide | **Applies, smaller** | Link the inserted punch to the day, set-aside gets the flag, `for_update` in the approval, both-order test. |
| OPS-4 queue and worker check | **Mostly out** | Only if the slip refresh moves to a job; `short` has a worker (read). §5 still proves it by `rq:workers`. |
| OPS-5 measure | **Narrowed** | Only: one slip save time, and the HR card with about 50 pending. Per-punch cost and late-punch counts are out. |
| OPS-6 no backfill | **Applies** | No patch over existing Attendance. The new Custom Fields only. |
| OPS-7 tell hand-marked days from machine-made | **Applies, P1** | The guard is in the design (section 7); the engineer must say which field marks "by hand", or the approval overwrites HR. |

New rows:

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-8 | Day work inline in the approval's transaction; slip refresh per 085 precedent, move to `refresh_slip_job` on `short` only if a save measures over ~2 s | One click, one day; real result for HR | A half-fixed day, or a slow click | P2, Recommend | |
| OPS-9 | Set the inserted punch's `attendance` link at insert; set-aside gets the new field plus `skip_auto_attendance=1` | The auto-attendance job takes unlinked punches in its window | Job re-marks a fixed day | P1, Recommend | |
| OPS-10 | Audit fields on the punch (approver id, time, request link); logs hold ids only | `set_value` leaves no history; notes are personal | No trail for a pay change; notes in logs | P1, Recommend | |
| OPS-11 | No caching and no guest access on the three calls; test no API response is cached | Stale or leaked pay claim | Wrong or exposed pay data | P2, Recommend | |
| OPS-12 | Engine dry run on a DTC copy, every day compared before and after | Engine now honours a new field | Silent pay change for 442 people | P1, Recommend | |
| OPS-13 | Compare `assets.json` in the volume against the image after deploy | Volume hides new `portal.js` | Users keep the old form | P2, Recommend | |

**Subtract pass:** I removed the idea of caching the result line and a possible async path for the day work. Nothing else. **Left behind:** only this appended section; not committed.

---

## §3 Requirements (20 Nov 2026)

Read: worktree `087-attendance-follows-punches`, dev `2e31151f`; the design gate note at the end of `01b-ux-design.md`; `deploy/nginx.conf` (zones near lines 69-80). No server command run. Nothing timed.

**Scope:** one approval inserts or sets aside one punch, re-judges one day, refreshes one employee-month draft slip. One punch per request (gate item 2). Each row is a requirement the analyst traces into a story. Decision column is blank.

| ID | Requirement | How it is proved | Level | Decision |
|---|---|---|---|---|
| OPS-R1 **Queues** | No new queue, worker, schedule or container. The day work (insert, set aside, judge, write) runs inline in the approval's transaction. The slip refresh runs inline with its own savepoint, as 085 does; it moves to `refresh_slip_job` on `short` (`enqueue_after_commit=True`, arguments employee and date only) **only** if one slip save measures over about 2 s on dev. If it moves, release readiness proves a worker is registered on `short` in rq (`bench worker --queue default,short`, read in `docker-compose.app.yml`), not by `docker ps`. A slip refresh failure never fails the approval. | Timing of one slip save recorded in the slice; a test where the refresh raises and the approval still stands | P2 | |
| OPS-R2 **Rate limits** | Do it in the app, not in nginx. Reason: one nginx serves production and dev, and the portal posts to `/` with a `cmd` (a path rule cannot see it). Request call: one open fix request per employee-day (refuse a second in words), and a cap of **[ASSUMPTION: 10 requests per employee per day]** the BA confirms. Approval call: refuse a request already decided (guard exists, `docstatus != 0`), and refuse a request whose day moved onto a final slip since it was sent. No bulk-approve endpoint. A refusal writes an id-only log line. | Tests: second request on one day refused; second approve of one request refused; the 11th request refused | P2 | |
| OPS-R3 **Routes and caching** | All three calls (send, HR list, decide) are signed-in only: no `allow_guest`. Nothing in `deploy/nginx.conf` changes in this slice (the file is shared by production and dev; `scripts/check_nginx_parses.sh` is not needed if it is untouched, and the diff must show it untouched). No `frappe.cache` of the result sentence, the "before → after" line or the punch lists. Responses carry no caching header from our code. The test engineer confirms no API response is held by a service worker or the browser's cache. | Diff shows no `deploy/nginx.conf` change; test lists the three endpoints and asserts a guest call is refused | P1 | |
| OPS-R4 **Logs: ids only** | Every log line and `frappe.log_error` for this feature holds ids only: request name, checkin name, employee id, date, approver user id, outcome code. Never the employee's note, HR's note, the decline reason or the set-aside reason. | A test sends a note with a marker string, runs send, approve and decline, and asserts the marker is in no Error Log and no log line | P1 | |
| OPS-R5 **Audit on the punch** | The added punch and the set-aside punch each carry: approver user id, time of approval, request name, and the "regularised" mark. The Attendance write is `set_value` (no history), so the audit lives on the punch and the request, not the Version row. The name stays in the audit record, not on the employee's screen (gate item 7). | Test reads the fields back after approval and after decline (empty) | P1 | |
| OPS-R6 **Race test with the auto-attendance job** | The inserted punch is linked to the day's Attendance in the same transaction; the set-aside punch gets the new field and `skip_auto_attendance=1`; the approval reads the Attendance row `for_update`. A test runs Frappe's `process_auto_attendance` and the approval **in both orders** on one day, on a fresh site built the way CI builds one, and asserts exactly one Attendance row, one count on the day sheet, the row and the engine, and no new Error Log row. The test must be seen to fail first with the link line removed. | The red-then-green run recorded in the test notes | P1 | |
| OPS-R7 **No second release** | An HR-added punch does not fire `release_on_machine_punch` (it exits for non-machine accounts). The typed time is not also counted as an "extra" in `worked_out` when a real punch is added (no double count). | Tests for both | P1 | |
| OPS-R8 **Dry run on a DTC data copy (OPS-12)** | Before dev is promoted to main: restore a copy of DTC data into a throwaway site (per `REHEARSAL.md`, never production, never `/var/www/html/hr-app`), run the engine before and after the new field, and compare every day's verdict for every employee. Expected change: **only** the test days. Any other changed day stops the release (kill criterion 1). The same run times `bench migrate` for the new Custom Fields, and checks the migrate queue is not full first (5 Nov). Output: counts of days compared and days changed, with the date and the copy's source. | The comparison file kept in the slice folder (counts, not names or pay figures) | P1 | |
| OPS-R9 **Assets landed (OPS-13)** | After each deploy that carries `portal.js`, prove it three ways: the pin file for that stack, every app container on the same image tag, and the new file itself. Then compare `assets.json` in the sites volume against the image's, and bump it if stale (asset version trap). `portal.js` is 1,297,945 bytes today; record the new size. | §5 lists the commands, marked for the user to approve | P2 | |
| OPS-R10 **Monitoring** | No new monitor or alert stack. Use what exists: Error Log filtered on this feature's title, and `scripts/check_workers.sh` (queue depth and worker heartbeats) if the slip refresh moves to a job. Count after release, from the audit fields: requests, approvals, declines, "wrong kind" declines (gate item 8), refresh failures. Alert condition: any Error Log row titled for this feature in the first week is read by a person. | A saved query for the counts in the release notes | P3 | |
| OPS-R11 **Rollback** | **An added punch is never deleted.** To undo: (a) set it aside through the same path (new field plus `skip_auto_attendance=1`), then re-judge the day; or (b) decline/cancel through the request where it is still open. A set-aside is undone the same way, by a new approved request. Code rollback is "redeploy the previous tag with migrations off" (production pulls only during a deploy); the Custom Fields stay and are harmless unread. Before release confirm the previous tag exists **in the package production pulls from**, and take the real rollback time from the run log (about 7 min on the last two deploys, from the earlier runs; not re-measured). A day on a final slip cannot be undone by punches: Additional Salary, as the design says. | §5 names the exact previous tag and proves it is in the package; a test of "set aside an HR-added punch" re-judges the day | P1 | |
| OPS-R12 **Migration** | New Custom Fields only. No backfill patch over existing Attendance or Employee Checkin. Run per tenant; a failed tenant is listed by name and re-run, never assumed done ("all sites migrated" needs a count). | §5 counts sites migrated against sites in the stack | P2 | |

**Out of this slice (from §1/§2):** OPS-1, OPS-2, OPS-4 as a standing item, per-punch cost, burst batching, any hook on the machine path. The sync path is not touched, and the diff should show it untouched (`release_on_machine_punch` and the Employee Checkin machine hooks unchanged).

**Questions for the BA, with my default:** the daily request cap (default 10), and who is told when a day moves onto a final slip after a request is sent (default: the card says so and offers Decline only, as designed).

**Subtract pass:** I removed a separate dashboard, an alert rule and a per-minute rate limit in nginx (one shared nginx, and the portal posts to `/`). **Left behind:** only this appended section; not committed.
