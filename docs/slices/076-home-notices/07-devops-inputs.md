# 076 · DevOps inputs (ALV-240)

DevOps advisor · 27 Oct 2026 · Advice only. Nothing was run, deployed or touched on any server. Decision column is blank for Surbhi.
Sources read: `portal.js` `loadHome()` (line 5562), `hr_api.get_employee_dashboard` (line 412), `inbox_api.get_inbox` (line 1007), `hooks.py` scheduler_events, `nfr-budget.md` §2, `usage-discipline.md`, `02-design.md`. **I did not read 01-product-brief.md or 01b in full, and I measured nothing. Every number below is Fact (code read) or Estimate.**

**Bad news first.**
1. **Home gets heavier.** It adds `get_inbox` (six parts, each with a count query plus a row query) on every load. No measured before/after exists. Nobody has timed it.
2. **A scheduled send runs on a 3-4 minute tick on production.** One send must finish well inside a tick, or the next tick can start the same send twice.
3. **No notice can be recalled once sent.** Rollback of the code is safe; rollback of sent data is not possible.

## §1 Performance (nfr-budget §2: API p95 <= 500 ms, phone page <= 2.5 s, query count must be the same for 20 or 1,000 people)

| # | Item | Today (Fact, code) | After (Estimate) |
|---|---|---|---|
| OPS-1 | Home load calls | `get_checkin_status`, `get_portal_activity`, `get_employee_dashboard` (+ policies, documents, goals) | Drop activity. Add `get_inbox`, notices, birthdays. Net: +2 calls, and `get_inbox` is the heavy one |
| OPS-2 | `get_inbox` cost | The frame already calls `get_nav_counts` (the counts) on every page load. `get_inbox` repeats every count, then adds one row query per non-empty part (cap 50) | Roughly 2x the count queries plus up to 6 row queries. Estimate only: **measure the count on the local bench** |

**OPS-2 Recommendation (Recommend, P2).** Home needs only 5 rows per kind plus counts. Do not ship a second full `get_inbox`. Options, cheapest first:
a. Reuse the counts `get_nav_counts` already fetched in the frame and call `get_inbox` with a small `limit` argument (a reviewed change to a whitelisted endpoint). No cache, no staleness.
b. If still over budget after measuring: a per-user cache of the Pending block for 30-60 seconds. **Stale-data cost:** an approval made in another tab shows for up to 60 s; the Decide sheet must clear that user's key on every decision (leave, expense) and the bell number must come from the same cached object, or the card and bell disagree (design says they must be equal). Not recommended before a measurement misses the budget.
c. Do not cache notices. Unread state must be exact the moment someone opens one.
Decision: ______

**OPS-3 Notices and birthdays (Recommend, P2).** Query shape must be flat in headcount:
- Notices: one query for the caller's unread (join to the recipient/read table, index on `(user, read)` or the equivalent; check the Notification Log existing index on `for_user` before adding any). One count query for the bell. No per-row query.
- Birthdays: one query, scope (own branch) and the leaver / opt-out filters **inside SQL**, month filter on `MONTH(date_of_birth)` (cannot use an index; fine at 5,000 employees, one branch at a time). Do not read branch employee ids into Python (nfr-budget §2 scope rule).
- Payload: 3 cards x 5 rows is small (Estimate under 5 KB). Birthdays must never send age or birth year in the JSON, even hidden (security).
Decision: ______

**OPS-4 Home calls in parallel (Consider, P3).** Fire the new calls together with the existing ones, each card with its own skeleton and its own failure box (design §11).
Decision: ______

**OPS-5 Read counts (Recommend, P2).** "Read by 212 of 238" must be one `COUNT` per announcement over an indexed `(announcement)` column, shown only on "Notices I sent" (at most the sender's own list, capped). Never on Home, never per recipient row. Do not store a counter that has to be kept in step.
Decision: ______

**OPS-6 Indexes (Consider, only after the local measure).** Notification Log is a framework table with an index on `for_user` only (Estimate, from memory of the framework; **I could not check it in this run, confirm in the bench with `SHOW INDEX`**). With 1,200 rows per CXO send and weekly sends, 5,000-employee tenants reach tens of thousands of rows a month. Add an index only if `EXPLAIN` shows a scan. Announcement lookups (due-to-send by status and send time) are tiny tables; no index needed at first.
Decision: ______

## §2 The send job

**OPS-7 Batching and chunking (Recommend, P1).** One tick must not carry a whole send.
- Use the existing scheduler (rung: already there). Each tick picks only Announcements whose status is "Scheduled" and time has passed, **at most one or two per tick**.
- Per announcement: write recipient rows in **chunks of 200 with a commit after each chunk** (Estimate: 1,200 rows = 6 commits, under 10 seconds; measure it). Save the cursor (count sent / last recipient) on the Announcement so the next tick resumes.
- Bell and Home read the Notification Log, so no email, no push, no outbound call is needed for the core send.
- The scheduler job should only enqueue a worker job on the `long` queue and return. Check that the default worker has a listener (lesson 1: a missing worker left work queued forever).

**OPS-8 Locking against double send (Recommend, P1).** Two ticks, or two workers, must not send the same notice.
- First act in the job: a single `UPDATE ... SET status='Sending' WHERE name=%s AND status='Scheduled'` and check rows affected. Zero means someone else has it; stop. This is atomic in the database and needs no Redis lock.
- A unique key on `(announcement, recipient user)` in the recipient rows makes a replayed chunk harmless (nfr-budget §3: re-running never double-counts).
- "Send now" (25 people or fewer) uses the same function in the request, so the same status guard applies.

**OPS-9 Half-completed send and scheduler down (Recommend, P1).**
- Half-complete: status stays "Sending" with the cursor; a later tick finds "Sending" older than 10 minutes and resumes (idempotent because of the unique key). After 3 resumes with no progress, mark "Failed" and log one Error Log row naming the announcement, never the message text or names.
- Scheduler down: nothing sends; "Scheduled" notices go late, not lost. When it comes back, due items send in order. The Compose screen's "up to 4 minutes later" hint is true only while the scheduler is healthy. **Check the production scheduler is enabled and its tick time before release**: the memory note says 3-4 minutes on production, 60 s on dev, and production "still needs it" set to 60 s at the 043 release. [ASSUMPTION] that change is not yet made; I could not check.
- Error Log noise: log one row per failed announcement, not one per recipient. A bad recipient (no user, disabled) is counted and skipped, not an error.

**OPS-10 Email (Recommend, P2).** The email tick is off by default and absent when email is not active (D4). Production email is muted until DTC go-live. The send job must read the same "email active" test the Compose screen uses, and must not queue any Email Queue rows when it is off. If it is on, queue emails after the bell rows, in the same chunks, without the message in logs. Check the Email Queue size before unmuting (memory: Brevo note).
Decision: ______

## §3 Release

**OPS-11 Migration and patch order (Recommend, P1).**
1. New DocType Announcement (and recipient child table or table) arrives with `bench migrate`.
2. The Notice Sender role-seeding patch runs after the DocType exists, and must be safe to run twice (nfr-budget §9). It gives the role to existing HR Managers once (Q8). Check the patch name is listed in `patches.txt` and written so a second migrate does not re-grant a role Surbhi has removed.
3. Org settings fields: the birthdays switch default must be explicit. Check which default the brief decided; a default of "on" on a live tenant starts showing names the day after deploy.
4. Dry run on a copy per `REHEARSAL.md`. [UNKNOWN] whether a copy of a large tenant exists to time it; I could not check.

**OPS-12 Known traps for this release (Recommend, P1).**
- Sites-volume assets are stale on every deploy (memory, 23 Sep). The new portal JS lives under the app's `public/js`; **verify the served `portal.js` is the new one** by fetching it from dev after deploy and looking for a string only the new version has. Do not trust a green deploy.
- Nginx is shared by dev and production. Do **not** change `deploy/nginx.conf` in this slice. If a new route is needed (none is expected: these are whitelisted API calls), stop and run `scripts/check_nginx_parses.sh` first.
- Deploy pause refuses biometric posts for about 1 minute (release 26 Oct note). Deploy outside the DTC punch peak (morning, shift change).
- Demo-safe recipe: no `demo/` file lands in main (CLAUDE.md §5; a demo file new on dev must be `git rm`-ed). Seed nothing on production. The birthdays default and Notice Sender seeding should leave a tenant looking the same except for the new cards.
- After deploy, every app container reports the same image tag (lesson 2). Check `docker top` for workers, not `docker ps` (lesson 15). Disk headroom before the pull (lesson 16).

**OPS-13 Rollback (Recommend, P1).**
- Home: the old code can come back with a redeploy of the previous tag, migrations off (lesson 20). The old page does not read Announcement, so there is **no data loss and no break**: the new tables simply sit unused. Confirm that the previous tag exists in the package production pulls from (`alvoraa-app`). I could not check.
- Real time: allow about 7 minutes for the deploy script's wait on `bench version` (lesson 22), plus the nginx restart.
- Scheduled announcements on rollback: they stay "Scheduled" and **never send** while the old code runs (the job does not exist). They go out late when the new code returns. If Surbhi does not want that, someone must cancel them first. Sent notices stay in Notification Log; the old bell would show them as ordinary alerts, which is acceptable.
- Removing `get_portal_activity`: if any other caller exists, rollback would hide the break; the engineer must grep for callers before removing (CLAUDE.md §2 step 1).
- The role-seeding patch is not reversed by a rollback; Notice Sender stays on the users. Harmless without the code.

**OPS-14 Path (Recommend).** Local bench, then dev (on her word), then main (on her word, after she tests on dev). Batch all 076 changes into one push to dev (CLAUDE.md §1). The dev tick is 60 s, so a "send later" test on dev takes about a minute; a test on production would take 3-4. Test the real 3-4 minute behaviour once by temporarily noting the production tick, not by changing it.
Decision: ______

## §4 What to measure on the local bench before dev

Seed to 500 and then 5,000 employees (nfr-budget §1 rule: no scale claim on three rows). Mark each as measured with the date and where.
1. Query count of Home before (old code) and after, **the same at 500 and 5,000** (the property). Use `frappe.db.sql` counting or the debug log, not a guess.
2. p95 of `get_inbox`, notices and birthdays at 500 and 5,000; target <= 500 ms each.
3. Time to send to 1,200 recipients, number of commits, peak memory; confirm it finishes in one tick, and that a second job started during it does not duplicate (the status guard).
4. Replay: kill the job mid-send, tick again; confirm the total is exactly the recipient count, no duplicates.
5. `EXPLAIN` on the unread query and the read-count query with 100,000 Notification Log rows.
6. Birthdays with 5,000 employees in one branch (worst case): query time and payload.
7. Bell number equals the Notices chip, with a scheduled send in the middle.

## Subtract pass

Removed from my own advice: a Redis lock (the status update is enough), a cache on Pending (kept as a fallback only after a measurement), a new index (conditional on `EXPLAIN`), any new worker or queue (use the existing `long` queue), any change to nginx.
Left behind: nothing. No files other than this one were written; no containers started.

## Unknowns I could not check

- Whether the previous image tag exists in `alvoraa-app`.
- The production scheduler tick value today.
- The actual indexes on `tabNotification Log`.
- The brief and 01b were not read in full.
