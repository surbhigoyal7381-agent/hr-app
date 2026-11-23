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
