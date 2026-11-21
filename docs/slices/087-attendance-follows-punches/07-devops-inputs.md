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

---

## §4 Strategy (20 Nov 2026)

Read: worktree `087-attendance-follows-punches`, now at `f92f0347` on `origin/dev` `72a046ec` (the engineer's own figures; I did not re-run `git rev-parse` against origin); `00-impact-analysis.md` in full; `held_day.py` lines 66-90; `hooks.py` `after_migrate` (line 724); `.github/workflows/ci.yml` step names. No server command run, nothing executed. **I did not read the 411/412 branch myself;** I rely on the engineer's reading of it.

### Install and deploy order

Each step is a push to dev on Surbhi's word, then main on her word, in the night window. Nothing below is a command for me to run.

1. **ALV-411/412 first** (`slice/alv411-412-security`). Agree with the engineer. It is small, Tier 1, and it closes GET on the four old endpoints. It is based on `7de630df`, two commits behind: it must be rebased and its CI seen green before 087 is rebased on it. The conflict is in the `decide` decorator lines, which the engineer expects.
2. **087 PR 1** (server side, the decide and Inbox changes). One dev deploy, then a read-back on dev (below), then wait.
3. **087 PR 2** (screens). A `portal.js` change: needs the `assets.json` check (OPS-R9) every time.
4. **Do not push 087 to main until** the DTC-copy dry run is done and read, and counsel's answer on an HR-added punch is in (the brief's open point). Dev can carry the code, switched on, before that: I read the engineer's section 12 that the compliance gate is for main only. That is the product's call, not mine.

**Wait-for-CI rule (4 Nov):** one push at a time; check `gh run list` and let CI finish before the next. PR 1 then PR 2 means two dev deploys; the second must not start while the first deploy or CI is running. **Mid-deploy there is a window** where the new image serves requests before migrate has finished (next section).

### Image and Compose

- **Expected none, and I agree.** No new app, dependency, container, volume, queue, schedule or env value. The diff must show `deploy/Dockerfile`, `deploy/compose/*.yml` and `deploy/nginx.conf` untouched (AC-88 asserts nginx). **Recommend a one-line CI or review check:** `git diff origin/dev --stat -- deploy/` is empty. That keeps the shared nginx lesson cheap.
- After deploy every app container reports the same image tag, and the stack's own pin file names it (dev: `.image.dev.env`). Proof is the three-way check, not a green run.

### Migration risk

Two parts: 8 new Custom Fields, and one patch over existing 085 requests (`alvoraa_for_held_day`).

- **P1, agree with the engineer's trap 3, with a cost note.** Between image start and migrate finishing, `_punches` runs on every judged day, payslip and attendance save. A missing column fails all of them with "Unknown column". The `frappe.db.has_column` guard is right and matches `_decided_as_is_storable`.
  - **Cost, inference not measured:** `has_column` goes through Frappe's cached table-column list, so one cheap read per call; but `_punches` has 7 call sites and `daily_attendance_workings` calls it per employee-day, so at 442 people that is thousands of calls in one report. **Recommend:** remember a True answer for the life of the process (it can never go back to False), and re-ask only while it is False. Measure the Salary Workings report before and after on the dry-run copy.
- **P1, a trap the engineer did not name (inference, please verify on a fresh site):** the 8 Custom Fields are created in `after_migrate` (the pattern in `held_day.py` line 68, and the hook list at `hooks.py` line 724). **Patches normally run before `after_migrate`.** If the `alvoraa_for_held_day` patch writes that column and the field is only made in `after_migrate`, the patch can fail with "Unknown column" on the first migrate of every tenant, or silently do nothing. **Recommend:** the patch calls the field-creation function itself first (it runs by itself twice without harm: `create_custom_fields` updates in place), then updates. Prove it on a fresh site built the way CI builds one, and on a copy that is migrated from before 087, in both cases with the patch row count read back. The same applies to the field the `_punches` filter reads.
- **Patch size:** batch over 500 rows (the engineer plans it); read the row count on the DTC copy before. It must not enqueue per row (5 Nov: 1,780 queued deletes stopped a migrate and later sites were left behind). Before the first migrate on each stack, read the queue depth.
- **"All sites migrated" is a claim.** §5 lists sites in the stack and sites migrated, counted, and names any failure.
- **Rollback of the patch:** none needed. Extra columns are harmless; the flag is only read by 087 code. Previous tag keeps working with the columns present.

### CI gates

Read from `ci.yml` step names: `check_api_paths.py --max 0`, `check_app_integrity.py`, nginx conf check, undefined-JS and portal-handler checks, plus the Python tests. Advice:

1. **Add the engineer's pin test to CI, on a site with all 12 apps** (it asserts `frappe.get_hooks("override_doctype_class")["Attendance Request"]` is exactly our one path). **Check that CI's site really installs all 12 apps;** if CI builds fewer, the test passes while proving less than it says (lesson 19: a pass is not a proof). Make the test print how many apps it saw, and fail if that is not the expected count.
2. `check_app_integrity.py` on the new module: the subclass inherits the stock class and redefines no doctype (lesson 7). It must stay green; it is the guard against redefinition.
3. `check_api_paths.py --max 0`: the new endpoints are POST-only and must not add an unlisted path.
4. The `deploy/` diff-empty check above.
5. Each "must be seen to fail first" test the engineer lists (race test, marker-string logs test, door tests) should record the red run in `03-implementation-notes.md`. I will ask for it at §5; I cannot check it from here.
6. Run the suite on the CI-style fresh site, not only ppj.dev (lesson 6).

### Version pinning

- **Fact (engineer, read in a container):** Frappe `v16.33.1` takes `class_overrides[doctype][-1]`, the last app wins, silently, and throws only if the class is not a subclass of stock. **Inference from that:** any later Frappe upgrade, or a new app installed after ours that overrides Attendance Request, would swap our class out with no error, and every punch fix would then fail the stock "status unchanged" check or write wrongly. Nothing in the image would warn.
- **Recommend:** (a) the pin test above, run in CI **and** at the end of §5's post-deploy checks against dev (read the hook in the running container, not only in CI); (b) the subclass delegates to `super()` for anything that is not a punch fix, so its removal falls back to stock; (c) name Frappe `v16.33.1` and the vendored `hrms` SHA in `03-implementation-notes.md`, so a later upgrade knows to re-read the three overridden methods. **Not checked:** the other six apps' hooks (the engineer's own gap); the pin test closes it, but the dry-run must use the real 12-app image, not a local 6-app bench.

### Where I agree and where I disagree with the engineer

| Point | Engineer | Me |
|---|---|---|
| Inline day work and slip refresh; no job or queue | Inline | **Agree.** One day, one click. Move the slip refresh to `short` only if a save measures over ~2 s |
| Link the punch after insert, not at insert (D7) | Amend AC-37 | **Agree.** Same race protection. The race test must still pass in both orders. Say plainly in the test: if the link is missing for a moment, the job can see the punch, and a lock must hold that moment (the approval holds the day's row `for_update` until the link is written) |
| Server-first split, PR 1 about 40 of 64 points | One large PR 1, commit order as review order | **Partly disagree.** Agree no screen PR first (it would leave HR unable to approve). **Disagree that one deploy is safe at that size:** PR 1 carries fields, a patch, the engine filter, the one door, the Inbox and the Desk closure in one deploy. If anything is wrong, a rollback is a redeploy of the previous tag (~7 min, not re-measured) and the one door is closed on the previous tag too only if the old code is back. Recommend: commit 1 (fields, filter, dry run) is deployed to dev **alone first** and read for a day, **if Surbhi accepts a third dev deploy**. This conflicts with the "one push at a time" lesson about too many pushes; the trade-off is hers. My default: keep two pushes, but run the dry run script on dev between them as the engineer's commit order already says |
| Deleting `release_by_hr` | Delete | **Agree**, provided 085's session confirms (the engineer waits for that). Its tests change with it. Rollback note: the previous tag still has the function, so a rollback is clean |
| Daily cap dropped (Surbhi) | Dropped | **Agree.** My OPS-R2 daily-cap row no longer applies; one open fix per employee-day stays |
| Dry run is "a belt check" because the field is empty so the filter is the identity | Honest note | **Agree, and good to say.** It proves the engine is unchanged with no set-asides; it does not prove the set-aside path. The second proof is a before/after of one real approved fix on the copy: set one punch aside on a test employee and read the day, the Attendance row and the draft slip agree. Add that to the dry run |
| `has_column` guard on every `_punches` call | Guard | **Agree** with the process-level True memo above |
| ALV-411/412 first | First | **Agree** |
| Manager loses approval (D4) | Needs Surbhi | **Agree it is a decision, not an ops matter.** Ops view only: HR with no company or branch scope sees nobody, so a tenant with HR users unscoped may find nobody can approve. Count, on each tenant before main, how many HR users can approve a punch fix |
| ALV-291 clears the skip flag (D6) | Ticket, no fix now | **Agree, but with a condition.** ALV-291 is due at DTC after the release (memory notes). If it runs after any fix exists, it silently reinstates a set-aside punch. **Recommend its guard lands before ALV-291 is run at DTC, and that §5 says so in words.** Dangerous debt until then if anyone runs it |
| 20 files read, "not checked" list | Honest | **Agree.** Items (a) to (d) become §5 pre-checks; (b) Custom DocPerm on Employee Checkin is cheap to read and I will list it |

### New rows

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-14 | The `alvoraa_for_held_day` patch creates the fields itself before it writes; proved on a fresh site and on a pre-087 copy | `after_migrate` normally runs after patches | First migrate fails or does nothing | P1, Recommend | |
| OPS-15 | `_punches` guard: remember True per process; measure Salary Workings before and after | Called per employee-day | Thousands of extra column lookups per report | P2, Recommend | |
| OPS-16 | Pin test runs in CI on a site with all 12 apps, prints the app count, and is re-read on dev's running container | Last override wins silently | Punch fixes fail after an upgrade, no error at install | P1, Recommend | |
| OPS-17 | `git diff origin/dev -- deploy/` must be empty for 087 | Shared nginx and image lessons | An unintended nginx or image change | P2, Recommend | |
| OPS-18 | Dry run adds one real before/after fix on the copy (day, row, slip agree) | The empty-field run proves nothing about set-asides | The set-aside path ships unproved | P1, Recommend | |
| OPS-19 | The ALV-291 guard lands before ALV-291 is run at DTC | It clears the skip flag on set-aside punches | A set-aside punch comes back and pay moves | P1, Recommend | |
| OPS-20 | Count HR users who can approve (company and branch scope) per tenant before main | HR with no scope sees nobody | Nobody can approve a fix | P2, Recommend | |

**Subtract pass:** I removed nothing from the engineer's plan; I added seven rows, each tied to a read fact or marked inference. I dropped my OPS-R2 daily cap (Surbhi did). **Not checked:** the 411/412 branch itself, the CI site's installed apps, `has_column` internals and the patch/after_migrate order (inference), any timing. **Left behind:** this appended section only; not committed.

---

## §5 Release readiness (21 Nov 2026)

Read: worktree `087-attendance-follows-punches`, HEAD `94f22878`, base dev `bad23ce0`; `git diff --stat bad23ce0..HEAD` (48 files, +9,603 -114); `punch_fix.py` FIELDS, `columns_ready`, `refuse_slip_while_unconfirmed`; the patch file; `hooks.py` diff; `scripts/087_dry_run.py`; `03-implementation-notes.md`; `deploy.yml` inputs; `REHEARSAL.md` headings; memory notes on Grace's slip job and the asset trap. **No server command run. Nothing timed today. Every command below is quoted, not run, and each is FOR SURBHI TO APPROVE.**

**Bad news first**

1. **P1: the screens are still not seen in a browser** (notes §0.1), and the Confirm/v5 build and the 21 Nov fix round are "built, not run" (notes §10) unless 04-test-report says otherwise. I cannot call this ready until the test engineer's re-run is green on `94f22878`. **Not checked by me.**
2. **P1: AC-59 (the dry run on real data) is still not done.** Details below. Main waits for it.
3. **P1: 087 alone must not reach main without 088.** The slip refusal tells HR to "record the signed register"; the register moved to 088. DTC pays outside the portal, and staff without a login cannot press Confirm. Until 088 exists the only exits are Withdraw or the app. (Inference from the spec move and the hook text.)
4. **P2: the dry-run script can show false "moved" days.** It counts the old way on the calendar day only; `_punches` now reads two days and applies ALV-402's `shift_day` rule. A night-shift day can differ with zero set-aside punches. Read each "moved" name; a night-shift one is ALV-402, not 087. Also its docstring `bench execute alvoraa_portal.scripts_087_dry_run.run` does not exist (the file is in `scripts/`); use the `env/bin/python` line.

### Rollout: does D1 (two pushes) still hold?

**No. Recommend one push to dev, one deploy, then one release to main.** Reason (fact): the later commits (`73716615`, `c0a73d0b`, `7540721c`, `81a6c397`) edit `punch_fix.py`, `portal.js`, `hooks.py` and the tests together; the notes (§7) already said push 2 "cannot be a clean cherry-pick". Inference: the Confirm server rules without the Confirm screen would let a slip be blocked with no way to clear it. I did not try a split. The safety D1 gave (server first, watch it) comes instead from the checks below, run before anyone uses the screens. This replaces my §4 "commit 1 alone first". `[ASSUMPTION]` the engineer agrees; their word needed.

| Step | What | Gate |
|---|---|---|
| Local | Test engineer's green on `94f22878`; screens seen at 360 px; `scripts/check_app_integrity.py`; `git diff origin/dev --stat -- deploy/` empty (it is: no `deploy/` or `.github/` file in the diff) | Surbhi's word to push dev |
| Dev | Fetch `origin/dev`, rebase, read incoming diff; last dev CI **passed** (not just finished); one push; checks below | Surbhi's word for main |
| Main | Night window 00:30-06:00 IST, together with 088 (same night or the next), 086 after. I have not read 086 or 088 | Surbhi's word, then she clicks the `production` approval herself |

**Release order: 087, 088 close together, then 086.** Do not push 087 to main and leave it a week without 088 (point 3). Never start the next push while CI or a Deploy is running.

### Migration dry run on a copy (AC-59 and OPS-R8/12/18)

Throwaway stack per `REHEARSAL.md` §3-5 (dump, start rehearsal stack, restore into `rehearsal.alvoraa.co`). DTC copy preferred; ppj.dev is the fallback and holds fewer real days. **Never production, never `/var/www/html/hr-app`.** Needs Surbhi's yes to take the dump.

1. Before migrate, read and write down: Attendance Request rows total; rows with `alvoraa_missing_log` set (these are the patch's targets); Employee Checkin count; migrate queue depth (`rq` default queue empty, 5 Nov trap).
2. Run `bench --site rehearsal.alvoraa.co migrate` with a stopwatch.
3. **Expected reads:** all 15 columns present (Employee Checkin 4: the added-by, set-aside-by-request, set-aside-by user, set-aside-on; Attendance Request 11); `alvoraa_for_held_day = 1` on exactly the rows counted in step 1 with `alvoraa_missing_log` set, and `0` on every other row; Attendance and Employee Checkin row counts **unchanged** (the patch touches neither); set-aside punches: 0.
4. Run the script from the sites folder: `../env/bin/python <path>/087_dry_run.py rehearsal.alvoraa.co 60`, then again with `90`. Expected: `set-aside punches on the site: 0`, `days whose punch count moved: 0` except night-shift names explained by ALV-402. Record days read, days moved, date, copy name.
5. OPS-18: approve one real fix on a test employee on the copy (set one punch aside); read day, Attendance row and draft slip agree.
6. Re-run the migrate a second time: no change (patch is safe twice).
7. Time the Salary Workings report on the copy before/after the image change (OPS-15; DTC has 442 people).
8. Read `frappe.get_hooks("override_doctype_class")["Attendance Request"]`; expect exactly our class (OPS-16).

**Stop the release if** any non-night day moves, a column is missing, a row count changed outside Attendance Request, or migrate fails.

### Deploy commands (all FOR SURBHI TO APPROVE; I run none)

1. **Dev push** (her word): `git fetch origin dev && git rebase origin/dev`, then `git push origin <branch>:dev`. The automatic dev Deploy runs `main`'s copy of `deploy.yml` (lesson 14); this slice does not change the workflow.
2. **Check the run is the right one** by run id, not by commit: `gh run list --workflow Deploy --limit 5`. Wait for the deploy; the version wait still burns about 7 minutes (lesson 22; not re-measured).
3. **Main** (her word, night window): `git push origin <exact SHA>:main` after the merge she approves. The `production` environment then waits for her click.
4. **Rollback deploy:** `gh workflow run Deploy --ref dev -f environment=<dev|production> -f image_tag=<previous tag> -f run_migrations=false -f image_package=alvoraa-app`. Needs the previous tag to exist in `alvoraa-app`: **check before release** (`gh api` on the package versions). Not checked.

### Checks after deploy (read-only; name stack and container every time)

1. **Three-way landing:** the stack's pin file (`.image.dev.env` on dev, `.image.env` on production) names the new tag; every app container (backend, scheduler, each worker) reports that tag; `punch_fix.py` exists in the container and its md5 equals the image's. Count the containers and say how many matched.
2. **Workers alive, not just Up:** `scripts/check_workers.sh`, plus `docker top` and `rq:workers` (lesson 15). Disk headroom first (lesson 16).
3. **Migrate on every site:** count sites in the stack, count sites migrated, name any failure. Then on each site: 15 columns exist; `frappe.get_hooks("override_doctype_class")["Attendance Request"]` is our class; the patch is listed done.
4. **Assets:** compare `assets.json` in the sites volume against the image's. The volume hides the image's assets (dev and production were stale in September). If the volume copy is old: copy `portal.js` and `panels.css` in, then `touch sites/assets/assets.json` and `clear-cache` (the `?v=` is that file's mtime). Commands for her approval, per stack. Record the new `portal.js` size (was 1,297,945 bytes).
5. **Behaviour:** in a browser, one employee sends a fix, HR approves, the day sheet and slip agree; Desk submit of a punch fix is refused; no "Unknown column" in Error Log; GET on the three calls refused.
6. nginx: no change in the diff, so no nginx restart is planned. If anything touches it, run `scripts/check_nginx_parses.sh` first.

### Grace's daily draft-slip job and the Salary Slip hook

**Effect: none expected, and it does not fix the freeze.** Fact (`hooks.py` diff): the new hook is on Salary Slip `before_submit` only. Inference: the Grace Server Script (not in the repo, I could not read it) calls `save()` on drafts, which does not fire `before_submit`; so the five leavers (HR-EMP-00022, 00045, 00065, 00096, 00101) still roll the whole batch back, exactly as before. The hook also returns at once when the columns are missing. **Two cautions:** (a) if that script or anyone ever submits slips in bulk, one unconfirmed HR-filed change blocks that employee's submit, and a bulk loop with a single commit has the 18 Nov failure shape; (b) on approval `punch_fix.apply` refreshes one employee's draft slip inline; it must not throw for a leaver. A leaver's approval refusing would be a new, visible failure; the test engineer should include one. Fix Grace's loop (catch per row) separately; do not couple it to this release. Existing requests have no flag, so nothing blocks on day one (notes §10 gap 2).

### Monitoring (nothing new)

Error Log read daily for a week, filtered on the feature's titles; `check_workers.sh`; counts from the audit fields (requests, approvals, declines, Confirm waiting, disputes) via the Script Report "Punch fixes this month"; Salary Workings "unconfirmed" column read by HR before payroll. Capacity: no new container or queue; estimated 1,232 queries per 50 cards before, 222 after (engineer's measure, local).

### Rollback (revert only)

Code: redeploy the previous tag with migrations off (about 7 min, not re-measured). The 15 columns and the patch's flag stay and are harmless. **An added punch is never deleted:** undo through a new approved request that sets it aside. Before a rollback, tell HR to stop approving: after it, a punch already set aside counts again only if the old reader runs, so read any day set aside during the window by hand. ALV-291 must not be run at DTC until its guard exists (OPS-19).

### Rows

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-21 | One push to dev and one release, not two (D1 retired) | Commits interleave; Confirm without its screen blocks slips | Half-state live | P1, Recommend | |
| OPS-22 | 087 reaches main only with 088 close behind; 086 after | Slip refusal points to a register that is in 088 | Payroll blocked at DTC with no exit | P1, Recommend | |
| OPS-23 | AC-59 and OPS-18 run on a DTC copy, steps above, before main | Never run on real data | Silent pay change for 442 people | P1, Recommend | |
| OPS-24 | Fix the dry-run docstring; treat night-shift "moved" days as ALV-402 | Script compares one calendar day | False alarm or a missed real move | P3, Recommend | |
| OPS-25 | Confirm the previous tag exists in `alvoraa-app` before release | Rollback depends on it | No rollback | P1, Recommend | |
| OPS-26 | Test: approving a fix for a leaver does not throw in the slip refresh | Grace's job died on leavers | New silent failure | P2, Recommend | |
| OPS-27 | Fix Grace's draft-slip loop separately (per-row catch) | Frozen since 18 Nov; this release does not touch it | Stale draft slips continue | P2, Consider | |

**Subtract pass:** I removed a separate alert rule, a dashboard and any staged server-then-screens deploy (retired D1). I removed nothing else. **Left behind:** this appended section only, committed; no container, file or setting elsewhere.
