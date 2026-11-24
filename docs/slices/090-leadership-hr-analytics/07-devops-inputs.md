# 07 DevOps inputs — slice 090 leadership HR analytics

## §1 Brief — 2026-11-23

Read: worktree `.claude/worktrees/090-leadership-hr-analytics`, branch `slice/090-leadership-hr-analytics`, SHA 412d5361. Tables and indexes read on the local bench `alv358-bench`, site `test_site` (MariaDB 10.8.8). No production, dev or server access. Nothing changed. Risk tier: **1** (personal data, scope by company, aggregates over people).

### Bottom line

**Recommend: build this as our own portal page reading from our own tables. Do not add Frappe Insights.** Run cost is small if every number comes from one `GROUP BY` on Employee or Attendance. It is not small if it scans Employee Checkin. The risk here is not speed. It is that a total shown to a CXO or HR Manager leaks people they must not see.

### What the local bench shows (proven: queries run 2026-11-23)

| Table | Local rows | Indexes that help this slice | Gap |
|---|---|---|---|
| Employee | 459 | company, branch, department, date_of_joining, relieving_date, status (each single) | No combined index. Fine at 2,000 rows. |
| Attendance | 234 | (company, attendance_date), (alvoraa_branch, attendance_date), status | No department column index. Department needs a join to Employee. |
| Employee Checkin | 305 | (employee, time), (alvoraa_branch, time), time | **No company or date-first index that suits "all staff, last 6 months".** |
| Leave Application | 5 | (employee, from_date, to_date) | Fine. |
| Salary Slip | 11 | (employee, start_date, end_date) | Fine. |

**The local data is tiny. I have no timing at DTC scale, so I give none.** [not checked: DTC row counts; I did not touch production.]

### Run cost (estimate, based on index shape above, not a timing)

- Headcount, joiners, leavers, early attrition: come from Employee alone (`date_of_joining`, `relieving_date`). Cheap at 2,000 rows. Rolling windows are just date arithmetic. [inferred]
- Attendance rates: DTC ~600 staff x 30 days is about 18,000 rows a month, about 110,000 for 6 months and 220,000 for a year. A date-range `GROUP BY` on (company, attendance_date) should be fine as an index range scan. [estimate; ~600 from the brief, not counted]
- **Employee Checkin is the red flag.** A busy site has several punches per person per day, so a year may be about 1 million rows at DTC. A `GROUP BY` there, per page load, per filter change, is the one thing here that can miss the 3 s report budget. [estimate]
- **Recommend: do not read Employee Checkin for headline numbers.** Attendance already holds the day's result. Only open Checkin if a figure truly needs it, and say which.

### Caching and snapshots

Rung on the ladder: first try **no new storage**. Measure the live queries at DTC scale on a copy (`REHEARSAL.md`). Only if one misses 3 s:
1. Frappe cache for a few minutes, keyed by (user, filters). Invalidate by time only, not by events. [Consider]
2. A nightly snapshot table or scheduled job only if step 1 is not enough. It adds a job, a table and a stale-number problem. Do not build it on suspicion. [Consider, after measuring]

**Stale-number rule:** a cached figure must show "as of" time. A cache shared between users is a leak (see below), so the key must hold the user or their exact scope.

### Frappe Insights vs our own page

- Insights is not in the bench's app list (`frappe erpnext india_compliance hrms alvoraa_goals alvoraa_portal`) and not in the image config I searched. [proven for the local bench; not checked for dev or production images]
- Adding it is a new app: image size, build time, upgrade for ever, a second permission model, and it queries the database directly. **Not recommended.** Its own permissions would not know our branch and company scope rules.

### Scheduled jobs

None needed to start. If a snapshot is added later: runs on the `long` queue, a worker must be listening, one bounded retry, and a failure that is visible. Note the scheduler ticks every 3-4 minutes on production (memory 25 Sep), so nothing here should depend on "every minute".

### Page weight on a 3G phone

Leaders mostly use desktops, but CXOs open this on a phone. **Recommend:** send numbers only (a few KB of JSON), draw charts with what the portal already ships, add no chart library, and return the filter lists in the same call. Budget: skeleton in 300 ms, content in 2.5 s on the 3G profile (`nfr-budget.md` §2). [estimate; not timed]

### Red flags, in order

1. **Scope leak through totals (P1).** Each endpoint must apply the caller's company and branch scope inside the query, in the database, never by trimming a list in Python. A CXO sees all companies; an HR Manager only own companies. A filter value the user is not allowed to pick must be refused, not silently ignored. Test as an HR Manager asking for another company's id.
2. **Small-group re-identification (P1).** "Left within 1 week, Ambala branch, Security department" can be one named person. Recommend: hide or merge any group under a set size (for example 5) and say so on screen. Counsel and the security engineer should set the number. Early attrition is the worst case, because the group is small by definition.
3. **Heavy Employee Checkin `GROUP BY` (P2).** See above.
4. **Multi-tenant sites (P2).** Each tenant is its own site and database, so a query cannot cross tenants. Cache keys must still carry the site. Control-plane guard from the performance module (memory) applies.
5. **Cache invalidation (P2).** Time-based expiry only. A rejoin, a corrected `relieving_date` or a back-dated joining date will move figures; "as of" time covers it.
6. **Salary Slip (P1 if pay totals appear).** Pay totals by small group are salary disclosure. Recommend leaving pay out of the first version unless the brief needs it.
7. **Exports.** If an export is added, it needs the same scope, the same small-group rule and an audit row.
8. **No index changes without a measured miss.** Adding indexes on Attendance/Employee Checkin changes a core table and slows every punch write.

### Questions that change the plan

- **Must know:** which figures does the founder need first? If none needs Employee Checkin, the red flag goes away. Default: Employee and Attendance only.
- **Should know:** real row counts at DTC and Grace. I could not check production. Default: measure on a dev copy during §5.

### Decision table (left blank for the user)

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-1 | Own portal page, no Frappe Insights | New app = permanent run, patch and permission cost | Second permission model that ignores our scope | Recommend | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-2 | First version reads Employee and Attendance only; no Checkin scans | Checkin is the largest table | Misses 3 s report budget at DTC | Recommend / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-3 | Scope enforced in the query; test other-company access | Aggregates leak people | Cross-company data exposure | Recommend / P1 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-4 | Minimum group size for small cells | Early attrition names individuals | Re-identification of leavers | Recommend / P1 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-5 | Measure on a dev copy first; cache by time only if a query misses 3 s | No measurement exists yet | Building a cache on suspicion | Consider / P3 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-6 | Leave Salary Slip totals out of v1 | Pay by small group is disclosure | Pay leak | Consider / P1 if included | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |

### Subtract pass

Removed from my first draft: a Redis pre-aggregation design, a new "analytics snapshot" doctype and a list of new indexes. None has a measured need. Left in: one measured-first caching step.

### Left behind

A read-only script was copied to `/tmp/q090.py` inside `alv358-bench`. I could not delete it (permission denied). It only reads row counts and indexes. Nothing else changed.

### §1 addendum, 2026-11-23 — attendance and leave trends (scope added by Surbhi)

Read on `alv358-bench`, site `test_site`, same SHA. Proven = queried today. Nothing changed.

- **Held days live on Attendance** as `alvoraa_held` and `alvoraa_held_confirmed`. There is no separate doctype. Neither field has an index (index list above). [proven] So a held-days trend is a date-range scan on (company, attendance_date) with a filter on the held flag. Fine at ~110,000 rows per 6 months, ~220,000 per year. [estimate, same basis as above]
- **Leave Ledger Entry (41 rows locally) has no date index.** It has only employee, transaction_type and transaction_name. `from_date` and `to_date` are not indexed. [proven] A 1-year leave-trend on it at DTC is a scan per employee set. **P2: leave trends should read Leave Application** (indexed on employee, from_date, to_date) for "who took what, when". Use the ledger only for balances, not trends. [inferred]
- **Attendance trends:** read Attendance only, by month or week buckets, not by day, for 6 and 12 month windows. Bucketing cuts the rows sent to the browser from thousands to about 12 to 52. [recommend]
- **Employee Checkin trends (P2):** still the red flag. Only (employee, time) and (alvoraa_branch, time) exist, with no company-first index. A year of punches for a whole company is the heaviest query in this slice. Recommend: no Checkin in any trend; held days already come from Attendance.
- **Leave dates cross windows.** A leave from 28 Dec to 3 Jan belongs to two buckets. Say how it is split (by day), or the totals will not match the payroll figures. Two reports giving two numbers is a defect (`nfr-budget.md` §9). [inferred]
- **Extra privacy flags (P1):** a leave-type trend for a small group can reveal medical or maternity leave. Group by leave type only above the small-group size (OPS-4). Held-day and absence counts per person must not appear in a leader view; counts only.
- **Cost of filters:** each filter is a `WHERE` on indexed Employee columns (company, branch, department), joined to Attendance. Department needs that join. Expect one extra join, not a new index. [inferred; not timed]
- **Cache:** a rolling window moves every day, so the key must carry today's date plus user scope. Time-based expiry only (see above).

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-7 | Leave trends read Leave Application, not Leave Ledger Entry | Ledger has no date index | Slow scan at DTC scale | Recommend / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-8 | Trends in week or month buckets; no per-day payload beyond 3 months | 3G page weight and query rows | Heavy page on a phone | Recommend / P3 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-9 | Count-only for held days and leave types in small groups | Medical or maternity leave inference | Personal data exposure | Recommend / P1 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-10 | State how a leave across a window edge is counted; match payroll | One number per figure | Two reports, two answers | Recommend / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |

Subtract pass: removed a suggested index on Leave Ledger Entry; reading Leave Application avoids it. Left behind: `/tmp/q090b.py` in `alv358-bench` (read-only, could not be removed, same as the first).

## §2 Design — 2026-11-23

Read: `01b-ux-design.md` and `prototype-v1.html` in this worktree (SHA 412d5361). Measured on the file only; nothing run on any server. Risk tier 1.

**Nothing here blocks the design. Two things must be written into the spec: the server withholds hidden figures (never hides them in the browser), and the endpoint is POST-only and role-checked.**

### Page weight and 3G (the 2.5 s budget, `nfr-budget.md` §2)
- **Measured (file, today):** the prototype is 32,326 bytes raw, 11,976 bytes gzipped. It has zero external links, zero script or stylesheet files, one inline SVG, and no browser storage. [proven: grep and gzip]
- **Not a real page weight.** The prototype has invented data and no portal shell. The real page adds the portal's own shell, CSS and JS, which I did not measure. [not checked]
- **Inference:** nginx gzip is on (`deploy/nginx.conf` line 89, level 5). With the chart as plain SVG and no library, 12 KB over a ~1.6 Mbps 3G link is about 60 ms of transfer. Round trips (page, then one data call) decide the time, not bytes. [estimate; not timed on a 3G profile]
- **Recommend:** one data call per period change, returning every figure, chart point and the headline inputs together (no per-tile calls). Skeleton from the page shell within 300 ms. Time it on the 3G profile on a dev copy at DTC size before release (§5). [P2]

### Payload size per period (estimate, from the bucket rules in the design)
Rows are buckets, not people, so size does not grow with headcount. [inferred]

| Period | Chart buckets | Estimated JSON, uncompressed |
|---|---|---|
| 1 week | 7 days | 3 to 5 KB |
| 1 month | ~5 weeks | 3 to 5 KB |
| 3 months | ~13 weeks | 4 to 6 KB |
| 6 months | 6 months | 3 to 5 KB |
| 1 year | 12 months | 3 to 5 KB |

About 1.5 KB gzipped. Basis: five tiles, three early-leaver cells, three trend series, leave types folded under Other, a By company block. [estimate; not built]
**Recommend: a test that fails if the response grows with headcount.** The property that matters is the same size for 20 people as for 2,000 (nfr-budget query rule).

### Caching
- **Recommend: no cache in v1; measure first** (OPS-5). The design's "Data up to" line is cheap to show without a snapshot: it is the time the query ran.
- **Consider, only if a period misses 3 s on a dev copy:** a Frappe cache entry of 5 minutes. The key must carry **site, user (or exact role and scope), period, filters and today's date.** A shared key would show one person's scope to another. Expire by time only.
- **Cost the design adds:** the "next-smallest" rule (hidden by subtraction) needs sibling groups computed on every request. That is a fixed number of extra grouped queries, not a loop per branch. Assert that the query count is the same for 3 branches and 30. [P2]
- The period is saved on the server per person (a small write on each chip tap). Recommend saving it once the user stays on a chip, not on every tap, and as a User setting, not a new DocType. [P3]

### What must never be public or leak
1. **POST-only, role-checked endpoint.** Allow only the Leadership role with Company or Branch scope and the HR roles. No guest, no GET. Check the caller on the server on every call. Frappe's `allow_guest` stays off, and the website-pages-post-to-`/` trap applies (a path gate is blind to `cmd`, see memory); test the real call. [P1]
2. **No names, no ids, no reasons.** The response carries counts, bucket labels and company or branch labels only. No employee id, no leave reason, no per-person absence. Test by scanning the response for any Employee id pattern. [P1]
3. **Withheld means absent, not hidden.** For a Not shared cell the server sends no number, only a flag. If the number is sent and the browser hides it, anyone reading the network tab sees it. Same for the headline sentence: build it server-side from shown figures only. [P1]
4. **The filter list is scoped too.** An HR Manager must not receive company or branch names outside their scope, and a filter value outside scope is refused, not ignored. [P1]
5. **Not cacheable by shared caches.** Send `Cache-Control: private, no-store`, so no proxy or the browser keeps one person's figures. Page stores nothing in the browser, as the design says. [P2]
6. **No export, no print-to-file endpoint** in this slice (design says none). Keep it out until it has its own audit row. [FYI]
7. **Logs:** log endpoint, caller role, period, duration and outcome. Not the filter values for small groups, and no figures. [P2]
8. **Rate limit.** `kinexus_api` allows 120 requests a minute per IP (`nginx.conf` line 70). That is enough for chip taps. No new nginx rule is needed. If the nginx file is touched anyway, the one-nginx rule applies (OPS lesson 13). [FYI]

### Decision table (left blank for the user)

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-11 | Server sends no number for a Not shared cell | Network tab shows hidden values | Small-group leak | Recommend / P1 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-12 | POST-only, role-checked, scope-checked, private no-store | HR data, aggregate endpoint | Guest or cross-company read | Recommend / P1 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-13 | One data call per period; test response size does not grow with headcount | 3G budget; bounded cost | Slow page, wrong scale test | Recommend / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-14 | Fixed query count for sibling-group (subtraction) checks | Per-branch loop grows with company | Slow at many branches | Recommend / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-15 | No cache in v1; if added, key = site + user scope + period + filters + date, 5 min | Shared key leaks | Wrong person's figures | Consider / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-16 | Time the page on a 3G profile at DTC size on a dev copy | Only an estimate exists | Missing 2.5 s budget unseen | Recommend / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |

Subtract pass: removed a pre-aggregated snapshot table, a CDN note and a new nginx limit rule. None has a measured need. Left behind: nothing new; the two earlier read-only scripts remain in `alv358-bench`.

## §3 Requirements — 2026-11-23

Read: `deploy/nginx.conf` (lines 292-298 `/api/` rate limit, 344 page-route list, 317 compression note), `hrms/hrms/alvoraa_hr_core/access.py` (`security_logger`, last changed in 8bd77bf9), and memory notes on the `/` plus `cmd` trap and ALV-391. Same worktree, SHA 412d5361. Read-only. OPS-11 to OPS-16 were accepted by Surbhi on 23 Nov and are requirements too. [Decision column stays blank.]

**Two things to trace into stories: the page route decides whether the HTML is compressed, and a scope refusal must be written to a log that is really open.**

### Findings that shape the requirements
- **Fact (read):** only a fixed list of page routes (`hrms-employee`, `desk`, `pms-*` and others, nginx line 344) is proxied; any other page falls to `location /`, which the file's own note says is **not compressed**. A new People trends page route outside the list is served uncompressed. On 3G that is a real cost. Adding it to the list edits `deploy/nginx.conf`, which one nginx serves for production and dev (lesson 13), so it needs `nginx -t` first. [Recommend: decide the route at build; see OPS-19.]
- **Fact (read):** data calls from a portal page that use `fetch` to `/api/method/<dotted>` hit `location /api/`: 120 requests a minute per address, burst 30. Chip taps stay far below that. [proven by reading the file; not load-tested]
- **Fact (read from memory note, confirmed in code path name only):** the refusal logger `security_logger()` exists and raises its level to INFO (ALV-391). On production it is **fixed only after the next release to main**; until then the file is 0 bytes. [not checked on production; I may not probe it]

### Requirements (numbered for the business analyst)

| ID | Requirement | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-17 | **Queues and workers: none.** Every figure is computed in the request. No scheduled job, no new queue, no snapshot table. If a period misses 3 s on the dev copy (OPS-23), come back as a new decision, not a quiet addition. | Nothing new to run or break at 2 am | A snapshot job with no worker listening | Recommend / P3 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations"); nginx edit still needs its own deploy approval |
| OPS-18 | **Endpoint route:** one `@frappe.whitelist(methods=["POST"])` function under `/api/method/<dotted>`, never `allow_guest`, never exposed as a website page route or a `cmd` call on `/`. Page JS must use `fetch` to the `/api/method` path. | A `cmd` on `/` bypasses path gates (ALV-248, ALV-422) | A guest or cross-route read; a gate blind to the call | Recommend / P1 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations"); nginx edit still needs its own deploy approval |
| OPS-19 | **CSRF:** the call must send the page's CSRF token and the server must reject a POST without it. Test with a POST that has a valid session and no token. Also test that a GET returns a refusal. The page route must be chosen on purpose: inside the compressed list (needs `nginx -t` first) or accepted uncompressed with the weight measured. | Frappe checks CSRF itself; our page may not send it (joiner page, ALV-343) | "Invalid Request" for real users, or no CSRF at all | Recommend / P1 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations"); nginx edit still needs its own deploy approval |
| OPS-20 | **Rate limit: no new nginx rule.** Rely on `kinexus_api` (120 per minute, burst 30). Add an application guard only if the 3G test shows repeated heavy calls: reject a second identical call from the same user within 1 second. Period save (OPS-15's note) fires after the user stays on a chip, not on every tap. | Existing zone is enough; a new rule edits the shared nginx file | A shared-file edit for no measured need | Recommend / P3 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations"); nginx edit still needs its own deploy approval |
| OPS-21 | **Refusals are logged and the log is proven open.** Every scope refusal, out-of-scope filter value and role refusal writes one line through `security_logger()`: endpoint, caller user, role, reason code. **No figures and no filter values for small groups.** Test reads the log file, not the mock (the ALV-391 trap). | An unread refusal is invisible; mocks hid ALV-391 for months | Probing of other companies goes unseen | Recommend / P1 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations"); nginx edit still needs its own deploy approval |
| OPS-22 | **Timing and slow-query log in the application, not the database.** One structured line per call: endpoint, period, duration, query count, outcome. Warn above 2 s. No personal data. I did not check whether MariaDB's slow query log is on in any stack, so I do not rely on it. [not checked] | Needed to prove the 3 s budget and the fixed query count | A slow page nobody can explain | Recommend / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations"); nginx edit still needs its own deploy approval |
| OPS-23 | **3G timing check on a dev copy at DTC size** (about 600 staff and a year of attendance), before release. Method to write in §5: throttled 3G profile, cold and warm, each of the five periods, with an HR Manager and a CXO login, and record page weight, time to first figures and response time. Seed to DTC size, never copy production data. Pass: skeleton within 300 ms, figures within 2.5 s. Use a dev tenant only, by Surbhi's word. | Today only estimates exist | Release with an unmeasured budget | Recommend / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations"); nginx edit still needs its own deploy approval |
| OPS-24 | **Test that the query count and response size are the same for 20 and for 2,000 people**, and for 3 and 30 branches. | The property that guards scale | A loop per branch that grows with the company | Recommend / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations"); nginx edit still needs its own deploy approval |
| OPS-25 | **Backups: nothing new.** No new DocType and no new files. The saved period is a User setting that the existing site backup already holds. Retention: no new data to keep. | Fewer things to restore | None | FYI | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations"); nginx edit still needs its own deploy approval |
| OPS-26 | **Secrets: none.** No key, no outbound call, no password. Nothing may go into a request argument or a log beyond the OPS-21 line. | Nothing to leak | None | FYI | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations"); nginx edit still needs its own deploy approval |
| OPS-27 | **Image and migrate:** new code lives in `alvoraa_portal` (no new app). No schema change, so no migrate risk is expected. If a field or DocType appears, I must re-read the plan. [inferred from the design] | Keeps the release small | A surprise migrate on DTC | FYI | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations"); nginx edit still needs its own deploy approval |

### Subtract pass
Removed a MariaDB slow-log setting, an nginx limit zone for the new endpoint, and a monitoring alert rule. Each needs a server or shared-file change with no measured need. Left behind: nothing new; the two earlier read-only scripts remain in `alv358-bench`.

## §4 Strategy — 2026-11-23

Read: the engineer's `00-impact-analysis.md` (commit 2fa20cfe), `.github/workflows/ci.yml`, `deploy.yml` (lines 496-503, 696-770), `scripts/check_*.py`, `announcements.make_role`, `deploy/Dockerfile` (line 50), memory notes on stale assets. Queried `alv358-bench`, site `test_site`, read-only. Nothing run on dev or production.

**Where I disagree with the engineer, first: (1) the new `people-trends.js` will fail CI's asset gate unless the deploy gate names it, and (2) R1's go or stop needs a number written down before step 0, and the fallback should be Employee-based populations, not a cache.** Everything else I agree with.

### Install order (for the release, each step on the user's word)
1. Merge to `dev` only after the gates below are green (check the last CI PASSED, not only finished).
2. Deploy to dev with the normal pipeline. The image is the only thing that carries the code; `after_migrate` makes the role on every site. Read the role back on each site (OPS-31).
3. 3G and DTC-size timing on a dev copy (OPS-23) and the property test result, then Surbhi's word for `main`. Night window IST only.
4. Production: same image tag as dev, `run_migrations=true`, role read-back per site.

### Image and Compose: no change (agree)
No new app, no pin, no volume, no worker, no nginx edit. The page lives inside `/hrms-employee`, so `deploy/nginx.conf` is untouched (agree; this removes the shared-nginx risk). **Version pinning:** nothing new to pin. Frappe stays `v16.35.0` (`deploy/Dockerfile` line 50); `check_version_pins.py` holds Dockerfile, CI and build args together and needs no edit. [proven by reading]

### Migration risk: the Leadership role
- **Proven locally:** `test_site` on `alv358-bench` already has Role `Leadership` with `desk_access = 1` and 0 holders in `Has Role`. It comes from the 012 tests. I did not read dev or production. [production not checked]
- **Agree** with the engineer: the hook must set `desk_access` to 0 on an existing role, as `make_role` does for the announcement role.
- **Risk:** `after_migrate` runs on every site at every migrate. On a site where someone really holds a `Leadership` role with desk access, the hook silently removes their Desk. Probability low (no DocPerm rows, so the role gives nothing), but it is a write on a live tenant. **Recommend: before the production release, the user approves a read-only count of holders per site.** For the user to approve, not run by me: `bench --site <site> mariadb -e "select parent from \`tabHas Role\` where role='Leadership'"` on dev first. [command quoted, not run on dev or production]
- **Order trap (read in `make_role`'s docstring):** Frappe makes a role with desk access on when it first meets it in a permission. On a new tenant `after_install` must run after anything that mentions `Leadership`. Put the new hook last in both lists.
- **Scope words:** "every site has desk_access 0" is a claim. After the migrate, count the sites and read the value on each one. The migrate-stops-halfway trap (memory, 5 Nov) means a later site can be left behind; check the queue is clear first.
- **Rollback:** the role is harmless left in place with no permissions. Rollback is to redeploy the previous tag with migrations off. I have not checked that the previous tag exists in `alvoraa-app`; the user checks before the release. [not checked]

### CI gates the new files fall into (read from `ci.yml`)
| Gate | What a new file does to it | Action |
|---|---|---|
| `check_portal_assets_gate.py` | The page will load a new `<script>`. This gate fails if `deploy.yml`'s "Portal assets must be served" step (lines 756-765) does not name every asset the page loads | **Add `/assets/alvoraa_portal/js/ess/people-trends.js` to that step.** That edits `deploy.yml`, a shared file. The automatic Deploy runs `main`'s copy (lesson 14), so the new line only gates production after the release; harmless, but say so in the report. [P2] |
| Stale assets (memory 23 Sep) | A new static file is not in the sites volume unless the deploy copies it; `refresh_bench_files.sh` does so on dev since 24 Sep, **production only after a release carrying it** | Prove the file lands: compare the volume's `assets.json` with the image's and fetch the new JS URL after deploy (OPS-32) |
| `check_api_paths.py --max 0` | The panel's data call path must resolve to a whitelisted function | Run locally; the page uses `gpFetch`, so confirm the script sees it |
| `check_scope_traps.py` | Reads Python by `ast`: bans `dict(permitted_employee_filters(user), name=...)` | The new `leader_scope()` must not use that shape; run it |
| `check_undefined_js`, `check_portal_handlers`, `check_tag_balance`, `check_design_system` | Read the portal files. The design check **counts colours**; the new CSS and inline SVG add to the count | Run all four locally before the commit |
| `check_brand_spelling.py` | On-screen name is "Alvora" | Run it |
| `check_app_integrity.py` | Rejects `from package import submodule`, redefined core doctypes | Run it before the commit (lesson 7) |
| gitleaks and `check_no_demo_passwords.py` | A literal test password trips the scan (slice 089). The 012 fixtures already hold test users | Fixtures take passwords from a generated value, never a literal |
| Python tests, 4 parallel parts | New test files land in a part by the runner's split | Two 012 tests insert Role `Leadership` with desk access on; the new hook sets it to 0. **Test order must not matter** (ALV-360 lesson). Run the new files alone and after the 012 files |

Not found: an `ignore_permissions` counter script among `scripts/check_*`. The engineer's baseline of 632 against 01c's 392 is two different greps, so I agree with recording one command and its number. [not checked whether CI holds a counter elsewhere]

### R1: 730 days of Attendance per call vs the 3 s budget
- **Agree** with step 0 first, before anything else is built, and with "do not add a cache quietly".
- **Disagree on how loose it is.** "Come back as a decision" with no number lets a miss be argued after the work is done. **Recommend the threshold now:** the whole attendance part, cold, on a DTC-size copy, must finish inside **1.5 s** of the 3 s page budget (the rest of the call, the network and the render need the other half). Go if under; stop and decide if over. [P2]
- **Estimate (not measured):** two years at DTC is about 440,000 rows (twice 220,000 from §1). `(company, attendance_date)` finds the range, but "distinct people per stretch" needs the `employee` value for every row, so the database reads each row, not just the index. A warm run may be fast; a cold run after a restart may not.
- **Fallback order I recommend:** (1) read populations from Employee dates (joining and relieving) instead of Attendance, which is fewer rows and already indexed; (2) only then a time-only cache keyed per OPS-15. Reason: the cache adds a stale-number and a scope-leak surface; fewer rows adds neither. The engineer lists both; I only change the order.
- **Concurrency not covered:** the 120 per minute limit is per address, not per database. Several leaders opening the page together make several heavy reads at once. I did not check the gunicorn worker count. Recommend the step 0 test also runs five calls at once. [not checked: worker count]
- **Measure on the same MariaDB version as production** (the local one is 10.8.8; production's version not checked). A Mac Docker timing is a guide, not the budget proof. OPS-23 on dev stays the proof.

### Where I agree with the engineer
No cache, job, queue, schema, patch or nginx line; zero edits to `org_figures.py`, `access.py`, `hr_api.py`; HR off in v1 (BQ-2 option 1 is a Tier 1 change to 13 call sites); own local stack for testing (the shared bench mounts a stale checkout); hot-file edits last, one line each, rebase first; thin slice with a measured go or stop; the 1-line `hooks.py` pin test.

### New requirements
| ID | Requirement | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-28 | R1 go or stop number: attendance part under 1.5 s cold at DTC size, plus five concurrent calls; fallback order Employee-based populations, then time-only cache | Gives step 0 a pass mark | A miss argued after the build | Recommend / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-29 | Add `people-trends.js` to the "Portal assets must be served" step in `deploy.yml` | `check_portal_assets_gate` fails CI otherwise | Red CI, or an unchecked asset | Recommend / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-30 | Read-only holder count of Role `Leadership` per dev and production site before release | The hook sets desk access 0 on an existing role | A real user loses Desk | Recommend / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-31 | After each migrate, read `desk_access` of `Leadership` on every site and report the count of sites read | Scope words are claims | A site left behind | Recommend / P2 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-32 | After deploy, prove the JS landed: volume `assets.json` against the image, and fetch the new asset URL on each stack | Volume hides image assets | A blank panel on production | Recommend / P1 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |
| OPS-33 | Run the 9 local gates in the table before commit; fixtures use generated passwords; new test files pass alone and after the 012 files | Each has failed this repo before | Red CI or a gate that passes without testing | Recommend / P3 | Accepted — Surbhi, 23 Nov 2026 ("go with your recommendations") |

### Subtract pass
Removed from my draft: a separate migration patch, a feature flag for rollback (the role with no permissions is already inert), and a CI counter script for `ignore_permissions` (no measured need in this slice). Left behind: `/tmp/q090c.py` in `alv358-bench` (read-only; could not be removed, as before).

### Leadership role on live sites (OPS-30), 23 Nov 2026

Read-only, counts only. Production (run by Surbhi, step02): aahr, alvoraa.co, demo, dtc, grace, tft — role absent, 0 holders. Dev (read by Claude): amata.dev, dev, ppj.dev, test_site — role absent, 0 holders. Setting desk_access=0 on the new role takes Desk from no one.


## §5 Release readiness — 2026-11-24

Read: worktree `.claude/worktrees/090-leadership-hr-analytics`, branch `slice/090-leadership-hr-analytics`, **commit 8c4763e0** (`git diff 0a181d05..8c4763e0`, 26 files). Also read: `deploy.yml` (steps "Portal assets must be served", "Assets must be real files", the nginx steps), `scripts/refresh_bench_files.sh`, `scripts/materialise_assets.sh`, `deploy/nginx.conf`, `hooks.py`, `people_trends.py`, `ci.yml`, memory notes on assets and releases. Fetched `origin/dev` (read-only). Ran only: `check_design_system.py` on three unpacked copies in the scratchpad, `git merge-tree`, `gh run list`, `py_compile` on the timing script. **No server, no container, no bench touched. Nothing pushed. alv090-bench left alone.** Risk tier: **1**.

**Uncommitted at the time I read it:** `scripts/run_dom_tests.js` (modified) and `people_trends_090_gaps_dom_test.js` (new). They are not in 8c4763e0. They must be committed before any push, or CI runs 28 + 1 tests against a runner that expects another number.

### Bad news first

**P1-A. The CI "Design system" gate will fail on this branch. [proven]** I ran `check_design_system.py` on three unpacked trees: base `0a181d05` passes, current `origin/dev` (`640cd1f5`) passes, slice head `8c4763e0` **fails: `hrms-employee.html: 4 radii (limit 3)`**. The cause is two `border-radius:4px` in `people-trends.js` line 176 (the leave-type bar). **The engineer's note says this failure is "pre-existing on origin/dev". That is wrong for the tree I read: dev passes it, and CI was green on dev at `0a181d05`.** Fix: use `var(--r-sm)` there. `ci.yml` line 105 marks the gate BLOCKING.

**P1-B. `origin/dev` has moved: 21 commits ahead of the branch (all slice 086), and CI on `640cd1f5` is still running. [proven: `gh run list`, 24 Nov 04:27 UTC start]** Do not push on top of a running CI (memory: a new push cancels it). `git merge-tree` shows **one conflict, `scripts/run_dom_tests.js`** (both sides raised `EXPECTED_BROWSER_TESTS` from 28 to 29). The right answer after the rebase is 28 + 086's one + 090's two = **31**, not 29 or 30. Keeping either side silently makes the DOM runner fail its own count check. `portal.js` and `hooks.py` auto-merge (086 added 425 lines to `portal.js`; read the merged result, since both slices touch it).

**P2-C. Speed is unproven at DTC size, and the local numbers miss the budget (OPS-23, below).**

### Does it need a migrate? Yes, and it is a small one

- The Leadership role is made by `people_trends.make_role`, listed **last** in `after_migrate` (every migrate, every site) and in `after_install` (a new tenant). It is **not** a fixture or a patch; there is no `patches.txt` line. [proven: `hooks.py` diff, lines 850 and 948]
- **So the deploy must run with `run_migrations=true`.** Without a migrate the role never appears, nobody can be given it, and the nav item never shows for anyone. That fails safe (no exposure), but the release would look like a no-op.
- Cost of the migrate: one Role insert per site. No schema change, no DocType, no patch, no fixture. [proven by the diff stat: no JSON, no `patches.txt`]
- On a site where the role exists with Desk access on, the hook turns Desk off. OPS-30 read the holders: **0 on all six production sites (aahr, alvoraa.co, demo, dtc, grace, tft) and 0 on the four dev sites (amata.dev, dev, ppj.dev, test_site); the role is absent on all ten** [from 07 §4, read 23 Nov; production by Surbhi]. So the hook takes Desk from nobody. [inferred it still holds on release day; re-read if more than a few days pass]
- Real risk is the old one: a long migrate stopping halfway at a full job queue (5 Nov, 1,780 queued deletes). **Check the queue is empty before the migrate, and count the sites after.**
- Not checked: whether any app listed after `alvoraa_portal` in installed apps runs an `after_migrate` that names Leadership. The read-back below catches it.

### The new deploy step (OPS-29): will "Portal assets must be served" pass?

**Inference, strong, not proof: yes on production, and yes on dev if the step is actually run.** What I read:

1. `people-trends.js` lives in `public/js/ess/`, the same folder as `portal.js`. It reaches nginx the same way: `refresh_bench_files.sh` copies the image's `sites/assets` into the volume (bundles first, `assets.json` last), then `materialise_assets.sh` turns links into real files. `portal.js` has gone out this way on every release since 6 Oct, so a sibling file takes the same road.
2. **The "deploys never refresh sites/assets" trap is closed on both stacks.** Dev since 24 Sep (ALV-112). Production: `8718f273` and `e7efecda` are in `origin/main` history (read with `git log origin/main -- scripts/refresh_bench_files.sh`), and the 20 and 22 Nov releases proved `assets.json` fresh and `portal.js` with the same md5 as the image. [from memory notes; local `origin/main` ref, not re-fetched]
3. **The `?v=` trap does not bite a new file.** The page's `?v=` is the modification time of `assets.json` (`get_build_version`). `refresh_bench_files.sh` copies it with `cp -p`, so it carries the new image's build time, which is different for every image. A new file name has no old browser copy anyway. [inferred; the 22 Nov release saw it move]
4. **The catch (lesson 14).** The automatic Deploy runs **`main`'s** copy of `deploy.yml`. On a dev push the step does **not** name `people-trends.js` (main has no such line), so **dev's automatic deploy will not check the new file**. On the first production deploy main's copy is the merged one and **will** check it, so a miss would fail that deploy at the last gate. **Recommend: after the dev deploy, fetch the URL by hand (check 4 below) rather than trust a green tick.** Alternative, if Surbhi wants the gate to run on dev: `gh workflow run Deploy --ref dev ...` (still the dev copy, not main's).
5. The step fetches with `curl -sk -H "Host: $SITE" https://$SITE...` through nginx and needs HTTP 200 and size over 0. It does not check content. **Not checked:** the service worker (slice 062) holding an old page. A signed-in browser may need one reload to see the nav item; say so in the release note.

### Does the slice need an nginx edit? **No. [proven from the code]**

- `git diff --stat 0a181d05..8c4763e0` lists no file under `deploy/` and no nginx file. The only workflow change is one line in `deploy.yml`.
- The page is `/hrms-employee`, which already has its location block (`nginx.conf` lines 344 and 518). It adds no route.
- The two calls are `/api/method/alvoraa_portal.people_trends.get_people_trends` and `...save_people_trends_period`. Neither matches the special locations (webhook, field_checkin, device, login), so both fall into `location /api/` with the existing `kinexus_api` limit (120 per minute, burst 30) (`nginx.conf` line 292).
- The script is under `/assets/`, served by `alias` from the sites volume (line 211).
- So the shared-nginx risk (lesson 13) does not arise from this slice. **Do not let the 086 or any other change's `nginx.conf` edit ride along unnoticed:** check `git diff origin/main..<release sha> -- deploy/nginx.conf` before the main push. The "nginx edit still needs its own approval" note on OPS-17 to 27 therefore has nothing to apply to; it stays only as a standing rule.
- Rate limit note: a leader moving through five chips fires five calls within a few seconds, well inside burst 30. Five concurrent 1-year calls were about 12 s each on the slow local stack; the gunicorn worker count is **not checked**.

### CI gates affected

| Gate | State at 8c4763e0 | Action |
|---|---|---|
| Design system (`ci.yml` 105) | **FAILS, proven** (P1-A) | Replace the two `4px`; re-run |
| `check_portal_assets_gate.py` | Passes (the page loads the script and `deploy.yml` now names it) [engineer ran it; not re-run by me] | None |
| `check_tag_balance.py` | Passes per engineer; `people-trends.html` pinned at depth 0 | None |
| DOM runner (`run_dom_tests.js`) | Needs `EXPECTED_BROWSER_TESTS` = **31** after the rebase (P1-B) | Resolve the conflict by hand. Local failure `portal_leave_063` "R-88" is on `origin/dev` too, but CI passed dev at `0a181d05`, so I read it as date-dependent on the Mac. [inferred] |
| `check_scope_traps.py` | **Not run on a Python that can parse the whole tree** | Run in a container with the bench's Python, or let CI be the proof. Say that in the report |
| `check_app_integrity`, brand, api paths, demo passwords | Pass per engineer | None |
| Python tests (4 parts) | 55 new tests. Order against the 012 files in one process **not run** | CI is the first run that mixes them |
| Gitleaks | Test passwords generated, no literal [engineer] | A `main` release scans the whole range (22 Nov lesson); read the scan result before the night push |

### Rollout: local, dev, main (each step on Surbhi's word only)

| Step | What | Gate before it |
|---|---|---|
| 0 | Fix P1-A. Commit the two loose files. `git fetch origin dev && git rebase origin/dev`. Resolve `run_dom_tests.js` (31). Read the incoming 086 diff and the merged `portal.js`. Re-run the design check, the DOM runner and the new Python files in `alv090-bench` once the full suite there has finished | Suite in `alv090-bench` finished; CI on `640cd1f5` finished and **green** |
| 1 | Push to dev. **For Surbhi to approve.** | See the commands below |
| 2 | Dev deploy (automatic, or by hand) with migrations on | Disk headroom; job queue empty |
| 3 | Dev checks (below), then the timing run (below), then a browser check at 360 px (AC-106, still owed) | |
| 4 | Surbhi's word for `main`; **night window 00:30 to 06:00 IST only** | Rules in "Should main wait?" |
| 5 | Production deploy, same image content, `run_migrations=true`; production approval gate is real (20 Nov) | Previous tag exists in `alvoraa-app` [not checked] |

### Deploy commands (written for Surbhi to decide; I ran none of them)

**FOR SURBHI TO APPROVE, step 1: push to dev.** Only when CI on dev is idle and the last run passed.
```
cd /Users/mac/hr-app/.claude/worktrees/090-leadership-hr-analytics
git fetch origin dev && git status -sb      # confirm branch, clean, 0 behind
gh run list --branch dev --limit 3          # last CI must be completed + success
git push origin slice/090-leadership-hr-analytics:dev
```
**FOR SURBHI TO APPROVE, step 2: the dev deploy.** The push starts it by itself. By hand (all four inputs are needed; the sha is the short sha of the pushed head):
```
gh workflow run Deploy --ref dev -f environment=dev -f image_tag=dev-<sha> -f image_package=alvoraa-app -f run_migrations=true
```
Before it: on `devstack-backend-1`, queue clear and disk free (read-only checks, listed below). **FOR SURBHI TO APPROVE, step 4: main**, night window, her word, only after dev testing:
```
git diff origin/main..<release sha> -- deploy/nginx.conf     # must be empty, or it needs its own approval
git push origin <exact sha>:main      # use the SHA, not the branch name (12 Nov lesson)
```
Then she approves the `production` environment prompt. `run_migrations=true` is the Deploy's migrate setting; confirm it is on in the run's inputs.

### Checks after the dev deploy (read-only; run on `devstack-*` when Surbhi asks)

1. **Landing, three ways:** pin file `.image.dev.env` names the new tag; `docker ps` shows every app container (backend, workers, scheduler) on that same tag, then `docker top` on each, because "Up" is not alive (lesson 15); `grep -c "people_trends.make_role" /home/frappe/frappe-bench/apps/alvoraa_portal/alvoraa_portal/hooks.py` in `devstack-backend-1` is 2.
2. **Role, every site, with a count:** for each of amata.dev, dev, ppj.dev, test_site read `select desk_access from tabRole where name='Leadership'`. Expect **0 on 4 of 4**. Report "4 of 4 read", not "all".
3. **Assets:** `assets.json` in the volume has the same date as the image's; `md5` of `people-trends.js` in the volume equals the image's.
4. **The file is served** (the gate does not do this on dev): `curl -sk -o /dev/null -w '%{http_code} %{size_download}' -H 'Host: dev.alvoraa.co' https://dev.alvoraa.co/assets/alvoraa_portal/js/ess/people-trends.js` returns `200` and a size over 0; and `curl -s .../hrms-employee | grep -oE 'people-trends\.js\?v=[0-9.]+'` shows a `?v=` that differs from before.
5. **Refusals work live:** a signed-in user without the role calling the endpoint gets a refusal and one `refused` line appears in `security.log` on that site (ALV-391 is on main since the 20 Nov release; dev has it).
6. No new rows in Error Log titled "People trends could not load".

### OPS-23: the speed question

**Measured, 24 Nov, on the engineer's own 8x-slow local stack (`alv090-*`, 600 invented staff, 438,000 attendance rows, production indexes), option 1 applied:** 1 week 1.6 s, 1 month 1.1 s, 3 months 2.0 s, 6 months 4.1 s, 1 year 6.9 s; five 1-year calls at once about 12 s each. Budget: **1.5 s** for the attendance part and **3 s** for the page (07 §4 OPS-28; `nfr-budget.md`). The 8x figure is a calibration of that stack, not a statement about production. If the 8x holds, 1 year would be about 0.9 s there. [estimate: 6.9 / 8, resting on one older comparison; I did not check it]

**Not measured and the real unknown: a DTC-size copy.** I could not check which dev site, if any, holds DTC-size data. From memory, `ppj.dev` carries a handful of demo staff. A timing on a tiny site proves nothing. [unknown] **Must-know question for Surbhi:** *Is there a dev site with about 600 staff and a year of attendance (a restored copy of DTC)?* If yes, name it. If no, putting a DTC copy on dev is a privacy decision of its own and not mine to start. **Default I would use:** run the script's first printout (row counts only) on dev to see; if the data is too small, report that plainly and rely on the local seed result, which already has more rows than DTC.

**The script** (read-only: the session is set `READ ONLY`, so a write would fail rather than pass; runs as Administrator, so it times the same code after the scope step; **one side effect remains**: one `info` line per call in that site's `security.log`, with user Administrator). I only ran `py_compile` on it (passes). **I have not run it anywhere.** Saved at `/private/tmp/claude-501/-Users-mac-hr-app/67b461e9-84fe-425b-b761-79423d0b7215/scratchpad/time_people_trends_090.py`; the text is below.

```python
"""Slice 090, OPS-23: read-only timing of get_people_trends on ONE dev site.
Run with the bench venv python (not bench console). Usage:
  python /tmp/time_people_trends_090.py <site> [company]
  python /tmp/time_people_trends_090.py <site> <company|-> --one <days>   (used for the 5-at-once test)
Writes nothing to the database: the session is set READ ONLY, so a write would fail loudly.
Side effect that remains: one line per call in the site's security log (Call.log)."""
import json, os, statistics, subprocess, sys, time
import frappe

site = sys.argv[1]
company = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "-" else None
os.chdir("/home/frappe/frappe-bench/sites")
frappe.init(site=site, sites_path=".")
frappe.connect()
frappe.db.sql("SET SESSION TRANSACTION READ ONLY")
frappe.set_user("Administrator")          # sees every company; same code path after the scope step
from alvoraa_portal.people_trends import get_people_trends

def one(days):
    t = time.monotonic()
    out = get_people_trends(period=str(days), company=company)
    return (time.monotonic() - t), len(json.dumps(out, default=str)), out.get("state")

if "--one" in sys.argv:
    s, size, state = one(int(sys.argv[sys.argv.index("--one") + 1]))
    print(json.dumps({"s": round(s, 2), "bytes": size, "state": state}))
    frappe.destroy(); sys.exit(0)

print("SITE", site, "COMPANY", company or "(all)")
print("Employee rows:", frappe.db.count("Employee"))
print("Attendance rows, last 365 days:", frappe.db.sql(
    "select count(*) from `tabAttendance` where attendance_date >= date_sub(curdate(), interval 365 day)")[0][0])
print("MariaDB:", frappe.db.sql("select version()")[0][0],
      "| buffer pool MB:", int(frappe.db.sql("select @@innodb_buffer_pool_size")[0][0]) // 1048576)
print("-- one at a time: first call, then 4 repeats (seconds)")
for d in (7, 30, 90, 180, 365):
    runs = [one(d) for _ in range(5)]
    secs = [r[0] for r in runs]
    print(f"{d:>3} days  first {secs[0]:.2f}  repeats median {statistics.median(secs[1:]):.2f}  "
          f"max {max(secs[1:]):.2f}  bytes {runs[0][1]}  state {runs[0][2]}")
frappe.destroy()
print("-- five at once, 365 days (separate processes)")
procs = [subprocess.Popen([sys.executable, __file__, site, company or "-", "--one", "365"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(5)]
for p in procs:
    o, e = p.communicate()
    print((o.strip() or "NO OUTPUT") + ("  ERR " + e.strip()[-200:] if p.returncode else ""))
```

**Steps. FOR SURBHI TO APPROVE (read-only, dev only, `devstack-backend-1`; not run by me):**
```
# 1. copy the file in as a plain file (from the Mac; no bench console, no piping into IPython)
docker exec -i devstack-backend-1 bash -c 'cat > /tmp/time_people_trends_090.py' < /private/tmp/claude-501/-Users-mac-hr-app/67b461e9-84fe-425b-b761-79423d0b7215/scratchpad/time_people_trends_090.py
# 2. row counts and a first look; pick the DTC-sized site. Pick the company name from the site's own Company list.
docker exec devstack-backend-1 bash -lc 'cd /home/frappe/frappe-bench/sites && /home/frappe/frappe-bench/env/bin/python /tmp/time_people_trends_090.py <site> 2>&1' | sed -e 's/\x1b\[[0-9;]*m//g'
# 3. remove the file (it is owned by the container user, so no -u root is needed)
docker exec devstack-backend-1 rm -f /tmp/time_people_trends_090.py
```
This needs the new image on dev (step 2 of the rollout), because the module exists only there. Run it at a quiet moment: no deploy in flight, and not while the dev site is in use for a demo. Read the output; confirm it printed the row counts and five timing lines. A run that prints nothing, or an error, is not a pass. **Check what it ran against: if "Employee rows" is far below about 600 or the attendance count far below about 200,000, it is not the DTC-size proof.** Also owed from this step: the 3G page timing (AC-115, `nfr-budget.md` page budget 2.5 s), done in a browser by a person.

**Pass marks I recommend, from OPS-28 and the NFR budget:** repeat median for 6 months and 1 year **under 1.5 s** on this site; five at once not worse than about 3 s each. If it is over, it comes back to Surbhi as a decision (fewer periods, a time-only cache per OPS-15, or ship with 6 months and 1 year held back). I add nothing before then.

**Should the release to main wait for this timing? Yes. [Recommend, P2.]** Reasons: (1) the only number we have misses the budget by 3x to 4.6x for 6 months and 1 year, on a stack of unknown relation to production; (2) the page is for CXO and leadership at DTC, the one tenant big enough to hurt; (3) the failure is slowness for a leader and heavy database reads at the same time as DTC's biometric punches, not a data leak, so dev can go first without waiting, only main waits. If the DTC-size run passes, release. If no DTC-size dev site exists and Surbhi declines to make one, she should accept the risk in writing (P2 rule), and I would then recommend the release goes out with the person who will open it first told to expect up to several seconds on the longest periods. [Her call.]

### Rollback (revert only)

- **Production pulls an image only during a deploy** (lesson 20). Rollback = `git revert` the release on `main` (or redeploy the previous tag with migrations off), then approve the production prompt. **Measure it: a deploy and a rollback each wait about 7 minutes** in the `bench version` loop (6 min 54 s dev, 7 min 09 s production, read from run logs 22 Sep; not re-measured today).
- **The previous production tag must exist in `alvoraa-app`.** Release 22 Nov put production on `835b1b7a`. I have **not checked** that `prod-835b1b7` is in the package. Surbhi or I read it before the night push (read-only `gh api` on the package versions).
- **What a rollback leaves:** the `Leadership` role stays on each site with Desk off and no permissions. It is inert and needs no cleanup. A saved period (a User Default row) stays and is harmless. No schema, no files, no patch to undo. Revert changes `deploy.yml` back; the automatic Deploy reads main's copy, so that is consistent.
- Nothing here is one-way.

### Monitoring and alerts

- **One structured line per call** in the site's `security.log`: `{event: "people_trends", at, user, role, period, ms, outcome, statements, rule}`. Over 2 s it is written as a warning. Read it after the first days of use: `grep '"event": "people_trends"' .../security.log | grep -c '"outcome": "error"'`, and the highest `ms`. No alert is added (no new service, nothing to run). [Consider P3: a look at the log on day 1 and day 7.]
- **Error Log** title "People trends could not load" = the generic PT-LOAD failure; the type only, no data.
- **The old hole:** before the 20 Nov release every `security.log` was empty on production. Read one production log once after release to prove it writes; if it is empty after a refusal, the monitoring above is blind.
- Capacity: no new disk, no job, no queue. Heavy cost is database reads at the time a leader opens a long period. Watch the first week at DTC for slow lines, and for DTC biometric punches slowing at the same time. [not measured]

### Decision table (left blank for the user)

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-34 | Replace the two `border-radius:4px` in `people-trends.js` (line 176) with `var(--r-sm)`; correct the engineer's note that the design check is "pre-existing on dev" | Design system gate fails on 8c4763e0 and passes on dev | Red CI on the first push; a push into a running CI | P1 / Recommend | |
| OPS-35 | Commit the two loose test files; rebase on `origin/dev`; resolve `run_dom_tests.js` to 31; read the merged `portal.js` | 21 commits (slice 086) came in; one real conflict; the count is a gate | DOM runner red, or a count that hides a lost test | P1 / Recommend | |
| OPS-36 | Wait for CI on `640cd1f5` to finish and pass before any dev push | A new push cancels the running CI | Commits left unchecked | P1 / Recommend | |
| OPS-37 | Deploy with `run_migrations=true`; queue empty and disk headroom first; read `desk_access` on every site after, report "n of n read" | The role is made only by `after_migrate` | A release that looks live and shows nobody the page; a site left behind | P1 / Recommend | |
| OPS-38 | After the dev deploy, fetch `people-trends.js` by hand and compare volume and image md5 (the automatic run uses main's `deploy.yml`, which does not name the file on dev) | Dev's gate will not check the new file | A blank panel found by a leader | P2 / Recommend | |
| OPS-39 | No nginx edit for this slice; check `git diff origin/main..<sha> -- deploy/nginx.conf` is empty before the main push | Other slices may carry one; one nginx serves production and dev | A live proxy change in a night push | P2 / Recommend | |
| OPS-40 | Run the timing script on a DTC-size dev copy, and hold the main release until it passes (median under 1.5 s for 6 months and 1 year) | Local number is 4.1 s and 6.9 s on a slow stack, 3 s budget | A slow page for DTC's leaders on day 1 | P2 / Recommend | |
| OPS-41 | Answer: is there a DTC-size dev site? If not, decide whether to make one, or accept the risk in writing | Cannot be settled from the code | Timing on a toy site passes by accident | P2 / Question | |
| OPS-42 | Read that `prod-835b1b7` (the rollback tag) exists in `alvoraa-app` before the night push | Rollback needs a tag that can be pulled | A rollback that cannot pull | P2 / Recommend | |
| OPS-43 | Run `check_scope_traps.py` on the bench's Python (or accept CI as the first run); do the 360 px browser check (AC-106) on dev | The host Python cannot parse one file; no browser check yet | A gate that was never really run | P3 / Consider | |

### Subtract pass

Removed from my draft: a cache proposal, a monitoring alert or dashboard, a second timing harness for the 3G test (a person with a browser does it), and a hand-written copy of every after-deploy command for production (the production list is the same five checks on `compose-*`, run by Surbhi). Added nothing that needs a new container, job or volume. Left behind: three unpacked trees and the script under the scratchpad folder; nothing in any repo or container.

## Re-check after fix round 1 — 2026-11-24

Read: worktree `.claude/worktrees/090-leadership-hr-analytics`, branch head **cb3677e3**, based on `640cd1f5`. Fetched `origin/dev` = **80dc5cbf**. Ran only `git fetch/log/diff/merge-tree`, `check_design_system.py` on the worktree, `gh run list`, `gh api` (refused). No server, bench or container touched. Nothing pushed or rebased.

| Earlier blocker | Now | Evidence |
|---|---|---|
| P1-A design-system radii | **Cleared** | `check_design_system.py` on cb3677e3: "OK - the visual system holds" [proven, I ran it] |
| P1-B rebase and `run_dom_tests.js` conflict | **Cleared for 640cd1f5; one more rebase needed** | Runner says `EXPECTED_BROWSER_TESTS = 31` and the comment lists the 090, 086 and 089 files [proven, read]. Working tree clean [proven]. |
| P2-C DTC-size timing | **Still open, and slower** | Engineer: 1 year went 5.0 s to 6.3-7.2 s on the 8x-slow stack [engineer's figure, not re-measured by me]. Budget is 3 s. Main still waits for the timing on a DTC-sized dev site. |
| OPS-42 rollback tag `prod-835b1b7` | **Not checked, still open** | `gh api` on package versions returned 403: the token has `gist, read:org, repo, workflow` and lacks `read:packages`. No such git tag exists (`git tag -l`). `build-image.yml` makes `prod-<sha>` on every main push, so it was probably pushed on 22 Nov [inferred]. Surbhi runs `gh auth refresh -s read:packages` or reads the package page herself. |

**What one more rebase brings in [proven]:** `origin/dev` is one commit past the base: **80dc5cbf "The leave card test went red on a date, not on a defect"**, which changes only `alvoraa_portal/tests/portal_leave_063_test.js` (+9 -1). `git merge-tree` of the branch against it: **clean, no conflict**. The runner count stays 31 (no new test file).

**CI on origin/dev is NOT idle and NOT green right now [proven, `gh run list`].** CI `45332031101` and Build Image `45332031275` for 80dc5cbf started 05:15 UTC and are in progress. The run before them, CI `45326494804` (slice 086, 04:27 UTC), **failed** after 43 min: jobs Lint and Python tests (two) failed. The last green CI on dev is `45134843809` (23 Nov, ALV-436). **Do not push on top of a running CI. Wait for 80dc5cbf to finish and read it.** I did not read why 086's run failed; 80dc5cbf looks like the fix for a date-bound test, but that is an inference.

**Timing script [proven, read both]:** `/private/tmp/claude-501/-Users-mac-hr-app/67b461e9-84fe-425b-b761-79423d0b7215/scratchpad/time_people_trends_090.py` calls only `get_people_trends(period, company)`. That signature is unchanged in cb3677e3. The query change is inside the module (`_rows_of_counted_people` lost its `key` argument, and the Attendance queries now sum per person in a sub-select). The script calls none of those, so **no edit was needed**. It is read-only (session set READ ONLY) and I did not run it.

**Row for the decision table (Decision left blank):**

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-43 | Wait for CI on 80dc5cbf to finish green, then rebase, then push to dev only on Surbhi's word. Read why `45326494804` failed first. | A push cancels the running CI; dev's last run was red | Unchecked commits, a cancelled gate | P2 / Recommend | |

**Subtract pass:** removed nothing; this note only reports status.

### OPS-23 / OPS-40 result on dev (24 Nov 2026, after fix round 5)

Dev runs image `dev-2d768a9` (proven: `docker inspect devstack-backend-1`). The migrate ran: the Leadership role exists on dev.alvoraa.co, ppj.dev and amata.dev, held by nobody (proven, read-only query).

**No dev site is DTC-size** (proven, read-only count): ppj.dev 405 active staff and 49,360 attendance rows in the last year; dev.alvoraa.co 363 and 2,844; amata.dev 0. DTC has 495 active staff. So this is the closest copy, not a DTC-size proof (OPS-41 still open).

Timed on ppj.dev, all companies, as Administrator, session READ ONLY, MariaDB 10.8.8 with a 128 MB buffer pool, server-side only (no 3G page test):

| Period | First call | Median of 4 repeats |
|---|---|---|
| 1 week | 1.26 s | 0.95 s |
| 1 month | 1.15 s | 1.16 s |
| 3 months | 1.93 s | 1.78 s |
| 6 months | 2.01 s | 1.76 s |
| 1 year | 1.60 s | 1.71 s |

Five 1-year calls at once: 2.79 to 3.13 s each. Every call returned state ok, and the 1-year view shared attendance (absent 9.0%).

**Against the budget:** all five are under the 3 s page budget. OPS-40's bar (median under 1.5 s for 6 months and 1 year) is **missed** by about 0.2 to 0.3 s. Five at once reach the 3 s line. Side effect: one security-log line per call on ppj.dev, user Administrator.

**Decision, Surbhi, 24 Nov 2026 ("Go ahead" on the recommendation):** accept the small OPS-40 miss. No once-a-day stored check now. Watch DTC response times in the first week after the main release; build the stored check only if they miss 3 s.
