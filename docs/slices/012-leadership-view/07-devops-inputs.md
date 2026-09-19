# 012 — Leadership view — DevOps inputs

**I advise. I decide nothing and I deploy nothing.** Every row ends in a Decision
column that is yours to fill.

One dated section per stage. Later sections are added below; nothing here gets
rewritten.

---

# §1 · 14 September 2026 — Brief

## Read this first — a scoping hole in code the slice may reuse

**`get_hr_analytics()` in `alvoraa_portal/alvoraa_portal/hr_api.py` (line 376) is
not limited to a branch or a company.** It counts with raw SQL, and it lists
"confirmations due" with `ignore_permissions=True`. Raw SQL skips Frappe's User
Permissions — the per-user rules that limit someone to one branch.

What that means today:

- A store HR person (HR User plus a Branch permission, the slice 011 set-up) opening
  HR analytics gets **every branch's** headcount, attendance rate and leave numbers,
  plus the **names, designations and joining dates** of people due for confirmation
  in other branches.
- On a site with more than one company, every number mixes all companies.

**How sure I am:** I read the code. I did not run it on dev or production, and I did
not check which environments have store HR users set up. It is an exposure inside one
tenant, not across tenants. It sits in slice 011's territory, so I suggest the
security engineer confirms it and decides whether it belongs in slice 010/011 or here.
**Whatever is decided, the leadership view must not be built on top of this function.**

## The answer in short

- **At PP Jewellers' size (403 people), this is cheap.** My heaviest test query ran in
  0.2 s on the local copy. No new service, no new spend.
- **At 5,000 people it is not cheap.** Year-long trends grow about 12 times, to an
  **estimated** 2–12 s per query. That is over the 2 s line where
  `nfr-budget.md` says work must move to a background job.
- **Three things drive the size of the slice more than the tiles do:** missing
  indexes, a cache that must never mix branches or show pay to the wrong person, and
  existing endpoints that cannot be reused as they are.

## What I measured (local bench, `ppj.localhost`, read-only, 14 Sep 2026)

This is a Docker bench on a laptop, not the server. Treat the times as relative.

| Check | Result |
|---|---|
| Rows | 403 employees, 6 branches, 1 company · 24,264 Attendance (11 May – 9 Sep 2026) · 45,141 Employee Checkin · 3,510 KPI · 806 Appraisal · 800 Salary Slip |
| Attendance by branch and status, all rows | **0.20 s** |
| Same, last 30 days only | **0.13 s** — MariaDB still walked every employee's rows; the date index did not help |
| Headcount by branch | 0.001 s |
| KPIs for one branch | 0.06 s — **full table read, no index on `employee`** |
| Pay total by branch | 0.007 s |
| Indexes on `tabEmployee` | only `status`, `designation`, `attendance_device_id`, `lft`, `rgt`. **None on `branch`, `company`, `department`, `reports_to`, `date_of_joining`, `relieving_date`** |
| Indexes on `tabKPI` | **none** beyond `name`, `creation`, `modified` (confirms slice 010) |
| Indexes on `tabAppraisal` | `employee` only — **none on `appraisal_cycle`** |
| Indexes on `tabIndividual Goal` | `employee` only |
| `alvoraa_branch` on Attendance | **not on this local copy yet** — slice 011's migrate has not run on `ppj.localhost` |

## How it grows — **estimate**

Based on the times above, scaled by row count. Attendance assumes about 26 working
days a month per person.

| Tenant | Attendance rows, 12 months | Year trend query | 30-day tiles |
|---|---|---|---|
| 400 people | ~125,000 | under 1 s | under 0.2 s |
| 2,000 people | ~620,000 | ~1–5 s | ~0.5 s |
| 5,000+ people | ~1,560,000 | **~2–12 s** | ~1–2 s |

Also relevant:

- Each stack has **8 web request slots** (gunicorn: 4 workers × 2 threads, 120 s
  timeout, `deploy/compose/docker-compose.app.yml`). Two leaders opening a slow page
  at month-end can hold a quarter of them while employees try to apply for leave.
- Redis is **one instance for both cache and job queue, with `noeviction`** (it
  refuses new writes when full instead of dropping old ones). A cache that grows
  without limits can stop jobs from being queued.

## What this adds to run

| Item | What it is |
|---|---|
| New endpoints | Probably 4–6 whitelisted calls, one per tile group, loaded as the page scrolls. Plus one drill-down call, paginated |
| Queries per page load | **estimate** 15–25 grouped queries if built as SQL `GROUP BY`. Thousands if built by reusing the per-person code listed below |
| Payload | Totals only: small (**estimate** under 20 KB). Drill-down: must be paginated |
| Redis | **estimate** ~20 KB per scope per period. PP Jewellers: 7 scopes × 3 periods ≈ 0.5 MB. A 50-branch customer ≈ 3 MB |
| Background work | None needed at 400. A nightly summary job on the existing `long` queue is worth considering above ~2,000 |
| New services, domains, storage | None |
| New spend | None at PP Jewellers' size. At 5,000 people the database may need more memory; I cannot size that without server numbers I have not been asked to read |

## Recommendations, ranked

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-1 | **Recommend:** build every number from one scope check, done on the server: resolve the leader's company or branch first, then filter every query by it. Do not reuse `get_hr_analytics()`. | That function ignores branch and company (see the top of this section). | A branch head sees every branch. The product's main promise for this persona fails on day one. | Recommend | |
| OPS-2 | **Recommend:** cache totals only, never the list of people. Build the key from: scope type + scope value + drill-down setting + pay setting + period + a settings version number. | Frappe already puts the site name in front of every cache key, so tenants stay apart (checked in `frappe/utils/redis_wrapper.py`). The real risk is **inside** one tenant: two branches, or pay-on and pay-off, sharing one key. | One branch head sees another branch's numbers, or pay totals appear after pay is turned off. Hard to spot, because the page looks normal. | Recommend | |
| OPS-3 | **Recommend:** do not cache pay totals at all. Query them live. | Pay totals took 7 ms. Redis here writes to disk (`appendonly yes`), so cached pay would sit in the `redis-data` volume and in its backups. | Pay figures live outside the database's access controls, on disk, with no audit trail. | Recommend | |
| OPS-4 | **Recommend:** refresh the cache on a timer (for example 10–15 minutes) and show "as of 10:40" on the page. Clear it when either org setting changes. Do not clear it from document hooks. | Attendance and check-ins arrive all day from biometric devices. Clearing on every save would empty the cache constantly and gain nothing. | Either stale numbers with no stamp, which erodes trust, or a cache that never hits. | Recommend | |
| OPS-5 | **Recommend:** add the missing indexes through our own app, never by editing Frappe or ERPNext doctype files: `Employee` (`company`, `branch`, `department`, `date_of_joining`, `relieving_date`), `KPI` (`employee`, `appraisal_cycle`), `Appraisal` (`appraisal_cycle`), and a combined `Attendance` (`alvoraa_branch`, `attendance_date`). | Measured: none of these exist. Every leadership query filters by them. | Numbers that load in 0.2 s at PP Jewellers take many seconds at 5,000 people. Adding indexes later on a large live table locks it during migrate. | Recommend | |
| OPS-6 | **Recommend:** do the counting in SQL `GROUP BY`, not in Python. Do not reuse these as they are: `attendance_analytics._analyse` (loads every attendance row into memory), `goals_api.get_team_goals` (one query per person, line 797), `hr_api._mark_actionable` (loads every pending leave one by one, line 570). | Reusing the arithmetic is fine. Reusing the way they fetch data is not. | At 5,000 people × 90 days, `_analyse` pulls ~450,000 rows per click. `get_team_goals` for a 1,000-person branch runs 1,000 queries. | Recommend | |
| OPS-7 | **Recommend:** assert a fixed query count per endpoint in tests, and time each endpoint on a synthetic 2,000-person site (not a copy of real data). Budget: ≤ 500 ms per call, ≤ 3 s for the page (`nfr-budget.md` §2). | The budget calls query-count tests "the cheapest scale defence you have". | Slowness is found by the first large customer, not by us. | Recommend | |
| OPS-8 | **Consider:** a nightly job that stores one summary row per branch per day (headcount, present, absent, late, short, on leave). Trends then read ~365 small rows instead of ~1.5 million. Run it on the existing `long` queue. | It turns year-long trends from "grows with employees × days" into "grows with branches × days". It also gives true month-start headcount for attrition, which the Employee table cannot give reliably. | Year trends breach the 2 s line above ~2,000 people. Attrition history stays an approximation. | Consider | |
| OPS-9 | **Recommend:** if OPS-8 is taken, the job gets a timeout, a failure record that someone sees, and a check that a `long` worker is running in both stacks. | Lesson paid for: tenant provisioning once sat queued forever because `worker-long` was missing. | Trends silently stop updating. | Recommend | |
| OPS-10 | **Recommend:** every cache key has an expiry, and keys are per scope, not per user. | Redis is shared with the job queue and set to refuse writes when full. | A cache that grows without limit can block job queueing for every tenant on that stack. | Recommend | |
| OPS-11 | **Recommend:** no pay figure, employee name or scope in logs, error messages or URLs. Send filters in the request body, not the query string. | Gunicorn writes every URL to its access log (`--access-logfile -`). | Pay or names end up in container logs kept for 180 days (CERT-In retention). | Recommend | |
| OPS-12 | **FYI:** the drill-down and any export must use `frappe.get_list` (which applies User Permissions), be paginated, and export only what the setting allows. Pay never appears in drill-down unless both org settings are on. | Exports are where scoped data usually leaks. | A branch head exports another branch's people. | FYI | |
| OPS-13 | **FYI:** `Employee Checkin` (45,141 rows) should not feed any leadership tile directly. Use Attendance, which already holds late and short-day flags. | Check-ins grow fastest and are not needed for totals. | The slowest table ends up on the busiest page. | FYI | |

## For the product manager, before sizing

1. **The scope model is the biggest unknown.** How is someone made "head of a branch"
   or "head of the company"? Reusing slice 011's Branch User Permission keeps it
   simple. A new role or a new field adds work and tests. Settle this in the brief.
2. **Suggested order by run cost and risk:** People + Attendance + Leave first (data
   exists, cheap at 400) → Performance (needs OPS-5 indexes first) → Pay (needs its
   own permission tests) → Compliance (I did not check whether document and policy
   acknowledgement records exist).
3. **Attrition is only as good as `relieving_date`.** If leavers are not marked
   consistently, attrition % will be wrong however fast the query is. Worth a data
   check on PP Jewellers before promising the tile.
4. **"Up to 5,000 employees" is 2.5 times the budget's design ceiling of 2,000**
   (`nfr-budget.md` §1). If that customer size is real, OPS-8 moves from Consider to
   Recommend, and the NFR budget needs updating.
5. The scoping hole at the top should be settled before this slice starts building,
   so the fix is not done twice.

## What I did and did not check

- **Did:** read the code named above; read `deploy/compose/docker-compose.app.yml`;
  ran read-only SQL (row counts, index lists, five timed `SELECT`s) on the local bench
  site `ppj.localhost`; read Frappe's cache key code inside `hrlocal-bench`.
- **One slip to report:** I copied a small SQL file into `hrlocal-bench:/tmp` with
  `docker cp`, which `CLAUDE.md` §2 lists as needing approval. I deleted it straight
  away and ran the queries through standard input instead. Nothing else on the bench
  changed.
- **Did not:** touch dev or production; read `deploy/server.env`; check server CPU,
  memory or database size; check whether slice 011's indexes exist on dev; check the
  ERPNext compliance doctypes; time anything at 2,000 or 5,000 people. Every number
  for larger tenants above is an **estimate**.

---

# §2 · 15 September 2026 — Design

Inputs read: `01-product-brief.md` (with the gate decision of 15 Sep), `01b-ux-design.md`,
`prototype-v1/index.html`, §1 above, `nfr-budget.md`. Plus the repo files named in each row.
**No bench, dev or server command was run for this section.** Checks that need one are
listed at the end as proposals.

## Read this first

1. **The page the Home card sits on may already miss the 3G budget, before 012 adds
   anything.** `alvoraa_portal/www/hrms-employee.html` is **970 KB** as a file (measured,
   file size on disk). Its controller sets `no_cache = 1`, so the phone downloads it again
   on every Home open. I found **no `gzip` line in `deploy/nginx.conf`**. If the page is sent
   uncompressed, a 3G phone needs an **estimated 5–19 s** for the page alone. The budget is
   2.5 s. I could not check whether the live nginx or Frappe compresses it (the live nginx
   config has blocks not in git). This is not caused by 012, but the WOW card inherits it.
2. **D11 ("in so far today") is cheap only with a new index.** `Employee Checkin` has
   indexes on `employee`, `shift` and `alvoraa_branch`, but **not on `time`**. Without one,
   a branch's count reads that branch's whole check-in history, which grows every day.
   With the index it reads about 2 rows per person. So: **yes, with the index**.
3. **Group size must be counted from the people inside each figure, not from today's
   headcount.** Slice 011 copies the branch onto Attendance when the record is saved, and
   keeps it after a transfer (`branch_scope.py`, decided 14 Sep). A branch with 6 people
   today can have September attendance from only 4 of them. Counting "6" would show a
   figure about 4 people.

## Page weight and load time on a 3G phone

**Estimate**, based on: 3G at 400 kbps to 1.6 Mbps down and ~400 ms per round trip
(typical phone throttling profiles; not measured on our pages), gzip shrinking HTML and
script about 5 times (common for text; not measured on this file).

| What loads | Size | Round trips | 3G time, estimate |
|---|---|---|---|
| Portal shell, uncompressed | 970 KB (measured) | 1 | **5–19 s** |
| Portal shell, if compressed | ~200 KB | 1 | ~1–4 s |
| Leader Home call (WOW + Today), totals only | under 5 KB | 1 | ~0.4–0.6 s plus server time |
| Overview, as designed (Today + 3 cards + trend + last 7 days + table) | under 20 KB total | **7** | ~1–1.5 s over HTTP/2, but see OPS-15 |
| Prototype file | 90 KB | — | Not what ships. Do not paste it in |

What already helps: `deploy/nginx.conf` has `http2 on`, so parallel calls share one
connection. The portal sends arguments in the POST body (`gpSend`), which already meets
OPS-11. There is no service worker, so no stale figures sit on the phone.

## D11 — "in so far today"

**Answer: cheap enough, with one index. The "expected" figure beside it costs more than the
check-in count.**

- **Query:** count distinct employees with a check-in between today 00:00 and now, for the
  scope. Branch scope filters on `alvoraa_branch`. Company scope joins `Employee` by its
  primary key, because `Employee Checkin` has no company field.
- **Index:** `(alvoraa_branch, time)` for branch scope, and `(time)` for company scope.
- **Rows read, estimate:** about 2 check-ins per person per day. 2,000 people ≈ 4,000 rows,
  a few milliseconds. Without the index: the branch's full history, about 1.2 million rows
  a year company-wide at 2,000 people (2 × 2,000 × 300 days).
- **"Expected"** needs the rota, holiday lists and today's approved leave. It must be a few
  grouped queries, never a loop over employees. This is where N+1 risk sits.
- **Freshness:** check-ins arrive when the biometric device syncs, not when people walk in.
  "As of 10:40" can mislead. Show "last check-in received 10:32" instead (a `MAX(time)`
  read on the same index).

## D5 — doubtful days (≥ 95% absent and < 5% checked in)

**Answer: store the result, one small record per branch per day.** Computing it on every
read means grouping every check-in in the period by day: **estimate** ~100,000 rows for one
month at 2,000 people. Stored, a trend reads a few hundred small rows.

The design needs storage anyway. D5b says a day stays left out "until HR fixes or confirms
it". A confirmation has to live somewhere.

## Caching — what, keys, expiry, clearing

**Cache the finished leader answer, after small groups are removed. Never the raw counts.**

| Part | Cache? | Expiry | Key parts after Frappe's site prefix |
|---|---|---|---|
| Home (WOW + Today) | Yes | 3 min | `ldr:home:{scope type}:{scope value}:{min group}:{formula v}:{data up to}:{doubtful v}` |
| Cards + branch or department table | Yes | 15 min | same parts + `{period}` + `{inherited hidden: y/n}` |
| 6-month trend | Yes | 60 min | same parts + `{months}` |
| "Show the figure with those days" | Yes, separate key | 15 min | same parts + `raw` |
| Scope and role check | **No — every request, before the cache read** | — | — |
| Settings "live impact" line, "Who has leader access" | **No** — live, System Manager and HR Manager only | — | — |

How the key stops stale un-hidden numbers:

- **The key holds the minimum group value itself** (for example `min5`), read fresh from
  the settings. It does not rely on a version counter. The dangerous change is *raising*
  the minimum (5 → 7): old answers would still show groups of 5 and 6. With the value in
  the key, a request after the change can never find the old answer. Old keys just expire.
- **On save of the settings, also delete every `ldr:` key** as a second guard.
- **`data up to`** is `MAX(attendance_date)` for the scope. With the OPS-5 index it is an
  index-only read. A new day of data then shows at once, without waiting for expiry.
- **`doubtful v`** is the latest change time of the stored doubtful-day records in scope.
  When HR confirms a day, the key changes.
- **Inheritance (design §7 rule 4):** a branch page decides "hidden by inheritance" from the
  company-level table computed with the same minimum. That flag is part of the key.
- **Attendance and leave saves do not clear anything** (OPS-4 stands). Employee changes are
  different, see OPS-18.

## What must never be cached, logged or sent

- **Suppressed figures.** Removed before the payload is built, so they never reach Redis
  either (Redis writes to disk here, §1 OPS-3).
- **Employee IDs, names, leave types, reasons**, even inside a cached intermediate result.
- **Pay**, in any form (OPS-3; out of this slice anyway).
- **The authorisation decision.** A User Permission change must work on the next request.

## Settings change history (P2)

**Recommend the Frappe-first option: a Single doctype for the leader settings with
`track_changes` on, and the reason as a field on it.** Each save then writes a `Version`
record with who, when, before and after, including the reason.

Checked in Frappe `version-16` source on GitHub (the branch `deploy/Dockerfile` pins), 15 Sep
2026: System Manager may read `Version` but **not delete** it; only Administrator may delete.
`Version` is **not** in Frappe's default log clean-up list, so it is not pruned by default.

| Option | Good | Bad |
|---|---|---|
| **Single doctype + `track_changes`** | No new log code. Frappe writes it | Administrator and direct database access can still delete. The design copy "nobody can delete it, including System Managers" is true for System Managers, not for Administrator |
| New append-only log doctype | Can shape the columns exactly | More code and tests for the same result |
| Frappe Defaults via `set_org_setting` (today's store) | Exists | **No history at all**, and any HR user can write any key (LV7 / F-15). Do not use |

## Recommendations, ranked (continues from OPS-13)

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-14 | **Recommend:** before building the WOW card, measure the transfer size and time of the Home page on a 3G profile (proposed check A). If it is sent uncompressed, raise compression as its own small change, outside this slice. | The shell is 970 KB, not cached, and I found no compression setting in the repo. | The WOW moment takes 5–19 s on a store head's phone. They stop opening it. | Recommend | |
| OPS-15 | **Recommend:** a separate, cheap Home endpoint returning WOW + Today in one call, cached 3 min. Make **no call** for users without the Leadership role (decide from roles already on the page). | Every leader opens Home every day. Employees open Home too, and a refused call per employee is wasted server work. | Trend queries run on every Home open; hundreds of useless 403 calls a day. | Recommend | |
| OPS-16 | **Recommend:** load the overview in 2 calls, not 7: one "summary" (cards, table, data up to, doubtful days), one "trend". Give each section its own error field, and let "Try again" ask for one section. | Each stack has 8 web request slots (§1). Seven calls from one leader can hold 7 of them. nginx allows 120 API calls a minute per IP address, and a store's Wi-Fi puts many staff behind one address. | One leader's page load blocks employees' leave requests; retries hit the rate limit. | Recommend | |
| OPS-17 | **Recommend:** cache only the finished answer after small groups are removed. Put the actual minimum group value, formula version, data-up-to date and doubtful-day change time in the key. Delete all leader keys when the settings are saved. Check role and scope on every request before reading the cache. | Raising the minimum is the risky direction; a value in the key cannot be skipped. | After a System Manager raises the minimum, leaders keep seeing figures for small groups for up to 15 minutes. | Recommend | |
| OPS-18 | **Consider:** clear the leader keys for one company when an Employee's branch, department, company or status changes. Not for attendance or leave saves. | These are rare events, and they change group sizes. | A group that just dropped below the minimum shows figures until the key expires (up to 15 min). | Consider | |
| OPS-19 | **Recommend:** count group size as the distinct people inside each figure for its period. Ask the security engineer to confirm this in 01c. | Attendance keeps the branch it was saved with (`branch_scope.py`); Employee holds today's branch. | A figure about 4 people passes the check because the branch has 6 today. | Recommend | |
| OPS-20 | **Recommend:** accept D11, with indexes `(alvoraa_branch, time)` and `(time)` on `Employee Checkin`, added through our app. Count people, never return IDs. Show "last check-in received" time. Build "expected" from grouped queries. If the scope has no check-ins in the last 7 days, show "on leave today" only. | Measured in the repo: no `time` index. Check-ins are the fastest-growing table (§1 OPS-13). | The Today strip gets slower every day; a tenant without devices shows "0 in so far". | Recommend | |
| OPS-21 | **Recommend:** store doubtful days, one record per branch per day (date, branch, company, expected, absent, checked in, status, who confirmed). A scheduled job re-checks the last 35 days early each morning; one day is re-checked when HR confirms it. The engineer checks first for an existing doctype that fits. | Stored reads are tiny. HR confirmation needs a home. Branch level, because one branch's device can fail alone. | A check-in scan on every page load; confirmations with nowhere to live. | Recommend | |
| OPS-22 | **FYI:** the doubtful-day rule on small branches. In a 4-person branch, "95% absent" means everyone off. Consider applying it only when expected people are at least the minimum group. In a tenant with no check-ins, the rule becomes "95% absent" alone. | Real days off in tiny branches would be wrongly left out. | Tiny branches show fewer days than they worked. | FYI | |
| OPS-23 | **Recommend:** settings as a Single doctype with `track_changes` and a reason field. HR Manager reads the history through one endpoint filtered to this doctype. **Do not give HR Manager read access to `Version`.** | Frappe-first; no new log code. Read access to `Version` shows every document's change history, including salary edits. | Either new code to maintain, or HR Managers reading every change in the system. | Recommend | |
| OPS-24 | **Recommend:** leader-view script ships only to Leadership users and stays small; **estimate** budget 30 KB before compression. Do not add the prototype's 90 KB. | The shell is already 970 KB. | Every employee downloads leader code they cannot use. | Recommend | |
| OPS-25 | **FYI:** in the query-count tests (OPS-7), add one for "a settings save followed by a leader load returns no figure for the new small groups", for both lowering and raising the minimum. | Design §16 item 20 only tests that the new rule applies, not that the old answer is gone. | The stale-cache case ships untested. | FYI | |

## Proposed checks — not run, each needs your word

| # | Check | Where | Why |
|---|---|---|---|
| A | Load Home with DevTools 3G throttling; note transfer size, `Content-Encoding`, time to first card | Local bench first; dev only if you ask | OPS-14 |
| B | `EXPLAIN` the "in so far today" count before and after the OPS-20 index | Local bench, a copy with slice 011 migrated | OPS-20 |
| C | Response headers on one leader endpoint show no browser caching (`no-store` or similar) | Local bench | Figures must not sit in a shared phone's browser cache |
| D | As a System Manager on the local bench, try to delete a `Version` record | Local bench | Confirms OPS-23 on our real build, not just the source |

## What I did and did not check

- **Did:** read the four slice files and the NFR budget; read `deploy/nginx.conf`,
  `branch_scope.py`, `hr_api.py` (`get_org_setting`, `set_org_setting`, cache use), the
  `Employee Checkin` and `Attendance` doctype files, the portal's call helper and file sizes;
  read Frappe `version-16` `version.json` and `hooks.py` on GitHub (15 Sep 2026).
- **Did not:** run anything on the bench, dev or production; measure any load time; check
  whether the live nginx or Frappe compresses responses; check whether slice 011's indexes
  exist on any site. Every time and row count above is an **estimate** unless marked measured.

---

# §2a · 15 September 2026 — Portal page speed (measured)

**This section is about the whole employee portal, not only the leadership view.** It lives
here because §2 (OPS-14) raised it. Any slice that touches `hrms-employee.html` inherits it.

The user approved, on 15 Sep 2026: measuring on the local bench, and read-only HTTP requests
to `dev.alvoraa.co`. Nothing was sent to production (`alvoraa.co`). No nginx, Compose or app
file was changed.

## Read this first

1. **Nothing is compressed anywhere — measured on the local bench and on dev.** Asking for
   `gzip, br` gets exactly the same bytes as not asking. No `Content-Encoding` header on the
   page, the login page, or any JS, CSS or SVG file. The nginx image (`nginx:alpine`) has
   gzip built in; our config just never turns it on.
2. **A first visit to the portal on a 3G phone took 18.4 s (measured, throttled browser).**
   The budget is 2.5 s (`nfr-budget.md`, employee surface on 3G, p95). A repeat visit, with
   the files already on the phone, still took **5.7 s**, because the 977 KB page itself is
   downloaded again every time.
3. **Compression alone will not bring a first visit under 2.5 s.** Estimate after
   compression: about 6–7 s for a first visit. It does bring repeat visits to about
   **1.5–2 s**, which is inside the budget. First visits need a bigger, separate change
   (OPS-33).
4. **A push to `dev` changes the nginx that serves production.** There is one nginx for
   both. The deploy workflow checks out the pushed branch in the one server folder and then
   restarts that nginx (`.github/workflows/deploy.yml`, lines 172–175 and 326). So the
   nginx config on `dev` goes live for `alvoraa.co` as soon as a dev deploy runs. "Test on
   dev first" still works for **behaviour** (if the settings sit only in the dev server
   block), but **a typing mistake in the file takes down every site**, production
   included. The config must be tested before the push, not after.
5. **The portal HTML must never be cached, by Frappe or by the browser.** It carries the
   user's email and their CSRF token (a secret that proves a request came from our page).
   Frappe's page cache stores a page by its address only (`website_page::/hrms-employee`),
   not by user. Turning off `no_cache` would hand one person's page, token included, to the
   next person. `no_cache = 1` must stay.

## How I measured

| What | How |
|---|---|
| Local page | `hrlocal-bench`, site `ppj.localhost`, through `localhost:8010`. Logged in as Administrator with `curl`, then fetched `/hrms-employee` 3 times with `Accept-Encoding: identity` and 3 times with `gzip, br`. Recorded size, headers and time to first byte (TTFB — the wait before the first byte arrives) |
| Local assets | Every JS, CSS, icon and font file the page loads, fetched the same way. List taken from a real headless Chromium load |
| Compressed sizes | Not served by anything, so **computed**: the exact served bytes run through `gzip -1`, `gzip -5` and `brotli -q 5` on this PC. These are real sizes for those settings, not guesses |
| Dev | `curl` from this PC, no login, with and without `Accept-Encoding`: `/hrms-employee`, `/alvoraa-login`, and the four files the login page loads. Connect and TLS time split out |
| 3G load | Playwright (Chromium 1223, from an existing install on this PC), phone screen 390 × 844, network throttled through Chrome DevTools Protocol. Two profiles: **1.6 Mbps down / 750 kbps up / 150 ms latency**, and Chrome's **"Fast 3G"-like** 1.44 Mbps / 562 ms. Each run: a cold load (empty cache), then a warm reload |
| nginx | Read `deploy/nginx.conf`, the three Compose files, `deploy.yml` and `DEPLOYMENT_RUNBOOK.md`. Listed the modules of the local `nginx:alpine` image (1.31.2) with a throwaway `docker run --rm`. Dev reports nginx 1.31.5 |
| Frappe caching | Read `frappe/website/utils.py` (`can_cache`, `cache_html`), `page_renderers/template_page.py` and `utils/jinja_globals.py` inside `hrlocal-bench` |

**Limits of these numbers:**

- The local bench runs `bench serve` (Werkzeug, the Python development server) with no nginx
  in front. Dev runs gunicorn behind nginx. Local sizes and headers match what the page
  sends; local server times do not match the server.
- I logged in as Administrator. Administrator has no Employee record, so the Home screen
  made only one data call. A real employee's Home makes more calls after the page loads.
  That time is **not** in these figures.
- I could not load `/hrms-employee` on dev. Without logging in it redirects to the login
  page, and I was not asked to log in to dev.
- Dev times depend on this PC's connection to the server. Read them as rough.

## What I measured

### The portal page (local, `ppj.localhost`)

| Check | Result |
|---|---|
| Size as served | **999,450 bytes (977 KB)**, both with and without `Accept-Encoding: gzip, br` |
| `Content-Encoding` | **none** |
| `Cache-Control` | `no-store,no-cache,must-revalidate,max-age=0` (from `no_cache = 1`) |
| `ETag` | none |
| TTFB (local server) | 0.17–0.26 s warm; 0.89 s on the first request |
| Same user, two requests | Byte-for-byte identical. The only per-user parts are the email, CSRF token, tenant name and support email |

What the 977 KB is made of (measured by splitting the served page):

| Part | Size | gzip level 5 |
|---|---|---|
| One inline `<script>` block (lines 4848–17145 of the file) | 647 KB | 153 KB |
| Inline `<style>` blocks (portal CSS 156 KB + design system 31 KB) | 188 KB | 33 KB |
| Everything else: markup, 144 inline SVG icons, small scripts | 165 KB | **29 KB** |
| **Whole page** | **999 KB** | **214 KB** (gzip 1: 267 KB · brotli 5: 189 KB) |

### Files the portal page loads (local, first visit, from a real Chromium load)

| File | Size sent | gzip 5 | Cache-Control locally | Needed by the portal? |
|---|---|---|---|---|
| `/hrms-employee` (the page) | 977 KB | 209 KB | no-store | yes |
| `frappe-web.bundle.js` | 806 KB | 244 KB | 12 h | lightly — the portal uses about 5 Frappe functions (`show_alert`, `csrf_token`, `msgprint`, `call`, `escape_html`) |
| `website.bundle.css` | 458 KB | 74 KB | 12 h | not checked |
| Icon sprite `lucide/icons.svg` | 440 KB | 77 KB | 12 h | **no** — the portal never references a sprite icon; Frappe preloads it |
| `file_uploader.bundle.js` | 207 KB | 73 KB | 12 h | not checked |
| Icon sprite `espresso/icons.svg` | 193 KB | 59 KB | 12 h | **no** |
| Inter font, 4 weights × 109 KB | 436 KB | already compressed (woff2) | 12 h | yes, but 4 weights is a lot |
| Icon sprite `timeless/icons.svg` | 71 KB | 20 KB | 12 h | **no** |
| Other small files and data calls | ~12 KB | — | — | — |
| **Total, first visit** | **3,600 KB in 29 requests** | **≈ 1,210 KB** | | |

Locally the asset headers come from Werkzeug (`max-age=43200`, with an ETag). On dev and
production nginx serves them instead — see below.

### Dev (`dev.alvoraa.co`), read-only

| Request | Result |
|---|---|
| `/hrms-employee`, no login | **301** redirect to `/alvoraa-login?redirect-to=/hrms-employee`, `no-store`. Nothing more to measure without logging in |
| `/alvoraa-login` | **173,163 bytes with and without `gzip, br` — no compression.** Would be 28 KB with gzip 5. TTFB 0.73–1.08 s, of which about 0.35 s is connecting and TLS from this PC |
| `frappe-web.bundle.JTAQXGLM.js` | 823,720 bytes, **not compressed**, `application/javascript` |
| `website.bundle.MDPQJBEC.css` | 468,851 bytes, **not compressed** |
| `lucide/icons.svg`, `espresso/icons.svg` | 450,258 and 197,404 bytes, **not compressed** |
| Cache headers on all `/assets/` files | `Expires` 30 days, `Cache-Control: max-age=2592000` **and** a second `Cache-Control: public, immutable` line, plus `ETag` and `Last-Modified`. Good for caching; the doubled header is harmless |
| Security headers on `/assets/` files | **Missing.** Pages get `X-Frame-Options`, `X-Content-Type-Options: nosniff` and `Referrer-Policy`; asset files get none. Cause: nginx drops the server-level `add_header` lines in any `location` block that has its own `add_header` (the `/assets/` block adds `Cache-Control`). Low risk, but worth fixing in the same edit (OPS-30) |

### 3G load in a real browser (measured, throttled Chromium)

| Page | Profile | Pass | First paint | Page `load` | Network quiet | Transferred |
|---|---|---|---|---|---|---|
| Local `/hrms-employee` | 1.6 Mbps / 150 ms | cold | 11.6 s | **18.4 s** | 20.7 s | 3,600 KB |
| Local `/hrms-employee` | 1.6 Mbps / 150 ms | warm | 1.5 s | **5.7 s** | 8.1 s | 984 KB |
| Local `/hrms-employee` | Fast 3G-like | cold | 13.5 s | **20.5 s** | 23.2 s | 3,600 KB |
| Local `/hrms-employee` | Fast 3G-like | warm | 2.0 s | **6.7 s** | 9.5 s | 984 KB |
| Dev `/alvoraa-login` | 1.6 Mbps / 150 ms | cold | 14.4 s | **17.5 s** | 19.4 s | 2,784 KB |
| Dev `/alvoraa-login` | 1.6 Mbps / 150 ms | warm | 1.3 s | **1.3 s** | 1.9 s | 171 KB |
| Dev `/alvoraa-login` | Fast 3G-like | cold | 12.6 s | **16.2 s** | 18.8 s | 2,784 KB |
| Dev `/alvoraa-login` | Fast 3G-like | warm | 1.5 s | **1.7 s** | 2.6 s | 171 KB |

"Warm" still downloads the whole page, because the page is `no-store`. That is why the
portal's warm load is 5.7 s and the login page's is 1.3 s.

### nginx and Frappe, as configured

| Question | Answer |
|---|---|
| `gzip` in `deploy/nginx.conf` | **None.** The stock `nginx:alpine` main config has `#gzip on;` commented out, so it is off |
| Brotli | **Not available.** The `nginx:alpine` image ships with acme, geoip, image_filter, njs and xslt modules only (listed from the local image, 1.31.2). Brotli would need a different image. Not recommended now |
| `gzip_static` (serve ready-made `.gz` files) | Built into the image, but `bench build` writes no `.gz` files (0 found in `sites/assets`). No gain without a build change |
| Caching of `/assets/` | `expires 30d` + `public, immutable` on both server blocks. **Good.** Frappe's built bundles have a content hash in the name, so a new build gets a new address |
| Does Frappe compress? | No. Frappe does not compress responses; it expects the proxy to |
| Frappe page cache for `/hrms-employee` | **Off, and must stay off.** `no_cache = 1` in `hrms_employee.py`. Frappe's cache key is the path only, not the user (see "Read this first", point 5) |
| Is the live nginx config the same as git? | **I could not check.** Commit `9f200b4` says the repo file was made to match the server, and the file now has the TLS blocks. The memory note that says otherwise is 33 days old. The server file was not read (production wall) |
| How the config reaches the server | `docker-compose.app.yml` bind-mounts `../nginx.conf` from `/var/www/html/hr-app`. Dev and production deploys both check out their branch in that one folder, then run `docker restart compose-nginx-1` |
| Does `nginx -s reload` pick up a new file after `git checkout`? | **Probably not — not verified on the server.** A single-file bind mount keeps pointing at the old file when git replaces it with a new one. A container restart re-reads it. That is why the deploy restarts nginx, and why "reload, not restart" does not apply to a git-delivered change |

## What can be cached, and what cannot

| Thing | Browser cache | Server cache | Why |
|---|---|---|---|
| Portal HTML (`/hrms-employee`) | **No** | **No** | Holds the user's email and CSRF token. Frappe's cache is keyed by path only. A shared phone's browser cache would keep another person's page |
| Leader and employee data calls (`/api/method/...`) | **No** | Per scope, as in OPS-17 | Personal data; a shared phone |
| Frappe's hashed bundles (`*.bundle.<hash>.js/css`) | **Yes, 30 days** — already done | n/a | New build = new file name |
| Portal JS and CSS, if moved out of the page (OPS-31) | **Yes, 30 days**, with a version in the address | n/a | The code is the same for every user and every tenant. It has no Jinja inside (checked: no `{{` or `{%` between lines 4848–17145 or 12–2263) |
| Unhashed files under `/assets/` (for example `portal_switch.js`) | 30 days today, **which is a risk** | n/a | nginx marks them `immutable`, but their address does not change on a new build. A phone can run old code for up to 30 days. Not measured; FYI only |

**So the real caching win is moving the 835 KB of inline script and style out of the page
into files the phone keeps.** The page itself would shrink to 165 KB, or 29 KB compressed.

## The plan — one small change for you to approve, plus one larger one to schedule

### Step 1 — compression (small, nginx only)

**Recommend** these lines in `deploy/nginx.conf`:

```nginx
    # Compression. nginx:alpine has gzip built in; brotli is not available.
    # text/html is always compressed once gzip is on - listing it only adds a warning.
    gzip              on;
    gzip_comp_level   5;
    gzip_min_length   1024;
    gzip_proxied      any;
    gzip_vary         on;
    gzip_types        text/css text/javascript application/javascript application/json
                      image/svg+xml text/plain application/manifest+json;
```

Why these values:

- **`gzip_comp_level 5`** — measured on the portal page: level 1 gives 267 KB, level 5
  gives 214 KB. Above 5 saves almost nothing and costs more CPU.
- **`gzip_min_length 1024`** — tiny responses are not worth compressing.
- **`gzip_proxied any`** — without it, nginx does not compress for requests that came
  through a proxy (a `Via` header). Some mobile networks add one.
- **`gzip_vary on`** — tells caches in between that the answer depends on
  `Accept-Encoding`.
- **Types** match what dev actually sends (`application/javascript`, `text/css`,
  `image/svg+xml`) and Frappe's API (`application/json`). Fonts (woff2) and images are
  already compressed; they are left out on purpose.

**Where, in two commits:**

1. **First commit — inside the `dev.alvoraa.co` server block only**, just after
   `proxy_send_timeout`. Only dev's behaviour changes. Production's server block is
   untouched, so `alvoraa.co` responses stay exactly as they are.
2. **Second commit, after you have tested on dev — the same lines in the `alvoraa.co`
   server block.** This one goes to `main` with the next release, on your word.

**The risk, stated plainly.** Because of "Read this first", point 4, the first commit is
read by the nginx that also serves production, as soon as the dev deploy runs. Settings
inside the dev block do not change production responses. **But if the file does not
parse, nginx will not start, and every site goes down.** The deploy's
`docker restart compose-nginx-1 >/dev/null 2>&1 || true` hides that failure. The smoke test
catches dev being down, but only after production is down too.

**Safe rollout — each step needs your word:**

| # | Step | Who runs it | Where |
|---|---|---|---|
| 1 | Test the edited file on this PC before any push (command below) | You, or an agent you tell to | Local only |
| 2 | Push to `dev` | Agent, on your explicit word | Git |
| 3 | Watch the deploy. When it finishes, check dev and production answer (checks below) | You for production; an agent can do dev | Dev read-only; production by you |
| 4 | Use dev on a phone for a day | You | Dev |
| 5 | Second commit (production block) goes to `main` with the next release | On your word | Git |

Config test for step 1 — **for you to approve**. It starts a throwaway `nginx:alpine`
container on this PC. The fake host entries let nginx resolve the upstream names; the
self-signed certificates only let it read the TLS lines. Nothing on the bench, dev or
production is touched.

```bash
# for the user to approve - local PC only
T="$TEMP/nginx-test"; mkdir -p "$T/ssl/live/alvoraa.co" "$T/ssl/live/alvox.in"
for d in alvoraa.co alvox.in; do
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 -subj "/CN=$d" \
    -keyout "$T/ssl/live/$d/privkey.pem" -out "$T/ssl/live/$d/fullchain.pem" 2>/dev/null
done
docker run --rm \
  --add-host compose-backend-1:127.0.0.1  --add-host compose-socketio-1:127.0.0.1 \
  --add-host devstack-backend-1:127.0.0.1 --add-host devstack-socketio-1:127.0.0.1 \
  -v "C:/Surbhi-Git/hr-app/deploy/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$T/ssl:/etc/nginx/ssl:ro" \
  nginx:alpine nginx -t
# expect: "syntax is ok" and "test is successful", with no "duplicate MIME type" warning
```

Checks after the dev deploy (step 3):

```bash
# dev - read-only, an agent may run these when you ask
curl -s -D - -o /dev/null -H 'Accept-Encoding: gzip' https://dev.alvoraa.co/alvoraa-login | grep -i -E 'content-encoding|vary'
#   expect: Content-Encoding: gzip, Vary: Accept-Encoding
curl -s -o /dev/null -w '%{size_download}\n' -H 'Accept-Encoding: gzip' https://dev.alvoraa.co/alvoraa-login
#   expect: about 28000 (was 173163)
curl -s -o /dev/null -w '%{size_download}\n' -H 'Accept-Encoding: gzip' https://dev.alvoraa.co/assets/frappe/dist/css/website.bundle.MDPQJBEC.css
#   expect: about 75000 (was 468851). The file name changes with each build - take it from the login page
curl -s -o /dev/null -w '%{size_download}\n' https://dev.alvoraa.co/alvoraa-login
#   expect: 173163 - a client that does not ask for gzip still gets plain bytes

# production - for the user to run; agents do not probe production
curl -s -o /dev/null -w '%{http_code}\n' https://alvoraa.co/alvoraa-login
#   expect: 200. Anything else: roll back now
```

**Rollback:**

- **Normal:** `git revert` the commit, then push to `dev` on your word. The deploy checks out
  the old file and restarts nginx. Takes one deploy run.
- **Emergency, nginx will not start:** the fix has to be made in the server folder
  `/var/www/html/hr-app`, which agents never touch. Only you can decide to do that. The
  shape of it is: restore the previous `deploy/nginx.conf` from git in that folder, then
  `docker restart compose-nginx-1`, then check `docker logs --tail 20 compose-nginx-1`.

Downtime to expect: the deploy already restarts nginx on every dev deploy, which the
workflow comments put at about 2 seconds for production. This change adds no extra restart.

### Step 2 — move the portal's inline script and style into cached files (larger; schedule it)

**What:** move the big `<script>` block (lines 4849–17144) into
`alvoraa_portal/public/js/hrms_employee.js`, and the portal `<style>` block (lines 13–2262)
into `alvoraa_portal/public/css/hrms_employee.css`. Move only — not one character changed
inside. Load them with a version in the address:

```html
<link rel="stylesheet" href="/assets/alvoraa_portal/css/hrms_employee.css?v={{ build_version }}">
<script src="/assets/alvoraa_portal/js/hrms_employee.js?v={{ build_version }}"></script>
```

`build_version` is already in every web page's context (`template_page.py`, line 157). It
changes with every build, so the 30-day `immutable` rule stays correct.

**Do not make them `.bundle.js` files.** Frappe's build wraps every bundle in a function
(checked: the built `frappe-web.bundle` starts with `(()=>{`). The portal has **213
top-level names** and **372 inline `on…="…"` handlers** that call them. Wrapped, every
button stops working.

**The design-system `<style>` (31 KB, shared by six pages)** stays inline in this step.

**Honest size of the work:**

| Part | Effort, estimate |
|---|---|
| The move itself | 1–2 hours |
| Update the 8 checks and tests that read `hrms-employee.html` directly: `test_portal_call_paths.py`, `test_portal_csrf.py`, `test_portal_layout.py`, `test_portal_security_010.py`, `test_waves_5_6.py`, `scripts/check_portal_handlers.js`, `scripts/check_attendance_strip.js`, `scripts/check_design_system.py` | half a day to a day |
| Click through every panel on the local bench, as an employee, a manager and HR | half a day |
| **Coordination** — the real cost | see below |

**Coordination.** `hrms-employee.html` is the hottest file in the repo (40 commits in the
last 30 days, measured with `git log`). `parallel-work.md` §6 says: "Do not move, re-indent
or rename existing code." This change breaks that rule by design. Git will not follow code
moved into a new file, so any open branch that edits the script will conflict, and its edits
have to be re-applied by hand in the new file. It needs:

1. A quiet window agreed with slice 009 (portal redesign), the slice 010 session and any other
   row on the work board that names `hrms-employee.html`.
2. All of them merged to `dev` first.
3. One move-only commit, pushed to `dev` on your word.
4. Everyone rebases before touching the portal again.

**Side effect for developers on the local bench:** `bench serve` sends asset files with a
12-hour cache (measured). After the move, an edit to the portal JS needs a hard refresh
to show. Today edits show on a normal refresh.

### Expected result, step by step

Profile: 1.6 Mbps down, 150 ms latency. "Measured" means the throttled browser run above.
"Estimate" is transfer size ÷ 200 KB per second, plus the measured ~0.5 s TTFB and
0.5–1 s for extra requests and running the script.

| Visit | Today (measured) | After step 1: compression (estimate) | After steps 1 + 2 (estimate) | Budget |
|---|---|---|---|---|
| **Repeat visit** — what an employee does every day | **5.7 s**, 984 KB | **~1.5–2 s**, ~215 KB | **~0.8–1.2 s**, ~30 KB plus data calls | 2.5 s |
| **First visit** — new phone, or first open after each release | **18.4 s**, 3,600 KB | **~6–7 s**, ~1,210 KB | ~6–7 s (same bytes, split into more files) | 2.5 s — **still missed** |
| Dev login page, first visit | **17.5 s**, 2,784 KB | ~5–6 s | unchanged by step 2 | 2.5 s — **still missed** |

Step 2 also helps in a way the table does not show. Chrome keeps the compiled form of an
external script it has cached, which it does not do for script written inside the page. So
a repeat visit should also spend less phone CPU starting up. **Estimate; not measured.**

## Recommendations (continues from OPS-25)

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-26 | **Recommend:** turn on gzip in `deploy/nginx.conf` with the settings above: first inside the `dev.alvoraa.co` server block, then (after dev testing) in the `alvoraa.co` block. No brotli. | Measured: nothing is compressed; the portal page shrinks from 977 KB to 209 KB, the login page from 173 KB to 28 KB, the main JS from 806 KB to 244 KB. `nginx:alpine` has gzip and not brotli. | Repeat visits stay at 5.7 s on 3G — more than twice the 2.5 s budget — for every employee, every day. | Recommend | |
| OPS-27 | **Recommend:** test the edited `nginx.conf` on this PC with `nginx -t` (command above) before pushing it to `dev`. | One nginx serves production and dev, and a dev deploy restarts it with dev's file. The restart failure is hidden by `\|\| true`. | A typing mistake in a dev push takes `alvoraa.co` down until someone notices. | Recommend | |
| OPS-28 | **Recommend:** add the same `nginx -t` test as a CI gate in `.github/workflows/ci.yml`, run whenever `deploy/nginx.conf` changes. | It turns OPS-27 from a habit into a check nobody can skip. It uses only public images and fake certificates, so no secrets are needed. | The next nginx edit relies on someone remembering. | Recommend | |
| OPS-29 | **Recommend:** keep `no_cache = 1` on `hrms_employee.py`, and never add browser caching or nginx `proxy_cache` for the portal HTML or any `/api/` answer. | The page holds the user's email and CSRF token. Frappe's page cache key is the path only (`website_page::/hrms-employee`). | One employee receives another's page and token; on a shared phone, the browser keeps a previous user's page. | Recommend | |
| OPS-30 | **Consider:** in the same nginx edit, repeat the security headers (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, each with `always`) inside both `/assets/` blocks. | Measured on dev: asset files come back without them, because nginx drops server-level `add_header` in a block that has its own. | JS and CSS served without `nosniff`. Low risk today; it will show up in any security scan. | Consider | |
| OPS-31 | **Recommend, scheduled with the other sessions:** move the portal's inline script (647 KB) and style (156 KB) into `alvoraa_portal/public/js/hrms_employee.js` and `public/css/hrms_employee.css`, loaded with `?v={{ build_version }}`. Plain files, **not** `.bundle.js`. Move only, in one commit, after slice 009, the slice 010 session and any other open portal work are merged to `dev`. | The script and style are the same for every user and tenant. Moved out, they are downloaded once per release, not on every visit. The page drops to 29 KB compressed. | Every Home open downloads ~215 KB even after compression. Every later change to the file keeps adding to the page every employee downloads each time. | Recommend | |
| OPS-32 | **Recommend:** ask the security engineer to confirm that compressing pages carrying the CSRF token is acceptable. My reading: the risk is low, because the `sid` cookie is `SameSite=Lax` (measured), so another website cannot make the browser fetch the portal page with the user's session and measure the answer size. | Compression plus a secret in the page is the known BREACH pattern (an attack that guesses a secret by watching compressed sizes). | A known attack class is turned on without a written decision. | Recommend | |
| OPS-33 | **Consider, as a separate later piece:** cut first-visit weight. Frappe's web template makes every portal visit preload three icon sprites (704 KB, which the portal never uses), `frappe-web.bundle.js` (806 KB, of which the portal uses about 5 functions) and 4 Inter font weights (436 KB). Options range from dropping the sprite preloads to a lighter base template for the portal. | After OPS-26 and OPS-31, first visits are still an estimated 6–7 s, and a first visit happens on every phone after every release. | New employees and every employee after a release wait 6–7 s on 3G. The budget stays missed for first visits. | Consider | |
| OPS-34 | **FYI:** unhashed files under `/assets/` (for example `alvoraa_portal/js/portal_switch.js`, listed in `hooks.py`) get nginx's 30-day `immutable` header while their address stays the same across builds. | Phones may keep old code for up to 30 days. I did not check whether Frappe adds a version to `app_include_js` links. | A fix to that file does not reach some phones for weeks. | FYI | |
| OPS-35 | **FYI:** after every deploy that touches `nginx.conf`, re-run the four dev `curl` checks above, and add "`Content-Encoding: gzip` on the login page" to the deploy smoke test once OPS-26 is on both blocks. | Compression can be lost silently: a later edit, a different overlay, or a server file that drifts from git. | Pages quietly go back to 5× their size and nobody notices until phones slow down. | FYI | |

## What I did and did not check

- **Did:** logged in to the local bench as Administrator with `curl` and with headless
  Chromium (this adds login session records on `ppj.localhost`; nothing else changed);
  fetched the page and its files; split the page into parts; computed compressed sizes on
  this PC; ran throttled browser loads on the local bench and on the dev login page; sent
  read-only, logged-out requests to `dev.alvoraa.co`; read `deploy/nginx.conf`, the three
  Compose files, `deploy.yml`, `DEPLOYMENT_RUNBOOK.md` and the Frappe caching code; listed the
  local `nginx:alpine` image's modules in a throwaway container. All working files stayed in
  the session scratch folder, outside the repo.
- **Did not:** send anything to `alvoraa.co`; read the live nginx config or
  `deploy/server.env`; log in to dev; measure a real employee's Home with its data calls;
  measure anything after compression (nothing serves it yet — every "after" figure is an
  **estimate**); test `nginx -t` on the proposed lines; check whether dev serves HTTP/2 to
  browsers (this PC's `curl` cannot ask for it); check whether Frappe versions
  `app_include_js` links.

---

## Decisions (2026-09-15)

The user accepted the recommendations for portal page speed:

| OPS | Decision |
|---|---|
| OPS-26 compression (dev server block first, production only after testing on dev) | **Approved** |
| OPS-27 / OPS-28 test `nginx -t` on this PC before any push; later a CI check | **Approved** |
| OPS-30 add the missing security headers to `/assets/` in the same edit | **Approved** |
| OPS-31 move the portal's inline script and style into versioned cached files | **Approved**, scheduled in a quiet window agreed with slice 009 and the slice 010 session |
| OPS-32 security sign-off on compressing pages that carry the CSRF token (BREACH) | **Approved** — goes to the security engineer |

Also approved: the database indexes recommended in §1 and §2 (including `Employee Checkin.time` for D11).
The page speed change is portal-wide. It goes through its own change process (impact analysis,
approval, local test, push only on the user's word) and is not built inside slice 012.

---

# §3 · 15 September 2026 — Requirements

Inputs read: `01-product-brief.md` (Gate decision 15 Sep), `01b-ux-design.md` (§7, §8.8–§8.10,
§9, §16, §17, Design check decision 15 Sep), `prototype-v2/index.html`, §1, §2, §2a and the
Decisions above, `nfr-budget.md`, `definition-of-ready-done.md`. Repo files read:
`deploy/compose/docker-compose.app.yml`, `docker-compose.devstack.yml`, `deploy/nginx.conf`,
`alvoraa_portal/hooks.py` (`scheduler_events`), `branch_scope.py`, `hr_api.py`,
`attendance_deduction.py`, `REHEARSAL.md`, `DEPLOYMENT_RUNBOOK.md`, slice 010
`03d-implementation-notes-group-d.md`. Frappe `version-16` source on GitHub, read 15 Sep 2026:
`rate_limiter.py`, `scheduled_job_type.py`, `database/mariadb/database.py`.

**No bench, dev, server or deploy command was run for this section.** Every time and size
below is an **estimate** unless marked measured or read.

**These are requirements for the business analyst to trace into stories.** Each one says how it
is tested. The portal-wide page speed work (OPS-26 to OPS-35) is **not** part of this slice. It
is its own change; the only link is that the 3G phone test (brief S4) should run after it.

## Read this first

1. **Redis has no memory ceiling on either stack (read in the Compose files).** It runs with
   `noeviction` (refuse writes when full) but no `--maxmemory`, so there is no "full" — the cache
   and the job queue grow until the server runs out of memory. Not caused by 012, and setting a
   ceiling is an infrastructure change **that needs your word, outside this slice**. 012 must keep
   its own share small, bounded and self-expiring (OPS-44, OPS-45).
2. **Frappe's built-in `@rate_limit` counts requests per IP address** (read in `version-16`
   `rate_limiter.py`). A store's staff share one Wi-Fi address. Used on leader endpoints, one busy
   store could lock out its own branch head. Any limit here must count per user (OPS-40).
3. **The "people inside each figure" rule (OPS-19) changes what a nightly summary (OPS-8) can
   be.** Daily counts cannot be added up into "distinct people this month". If OPS-8 is ever
   needed, it must store one row per group per **period**, not per day. Not needed now (OPS-51).
4. **Adding an index does not stop reads and writes on MariaDB 10.8, but it can make them
   wait.** Each `ALTER TABLE … ADD INDEX` needs a short exclusive lock at start and end. If a long
   query is running on that table, the `ALTER` waits for it, and every new read and write on that
   table waits behind the `ALTER`. On `Employee Checkin` during a device sync, check-ins would
   queue. Migrate belongs inside the runbook's backup-and-maintenance hold (OPS-54).
5. **Two items from §1 leave this slice's list.** The KPI indexes were already added by slice
   010 (`d099aa7`, `kpi.json`, tested in `test_review_copies_010d.py`). The `Appraisal.appraisal_cycle`
   index is only needed by the Performance slice. Neither is repeated here.

## A · Endpoints and call pattern

**Decision asked of me in 01b §17: two calls for the overview, not one per card.** The design
needs each card to show its own loading, error and "Try again". That is met by giving each
section of the response its own `ok` / `error` field, and letting "Try again" ask for one
section. It does not need seven calls.

Why two and not seven: each stack has **8 web request slots** (§1). nginx allows **120 API calls
a minute per IP address, burst 30** (`deploy/nginx.conf`, lines 28 and 130), and a store's
staff sit behind one address. Seven calls per scope switch, times a few switches, plus every
employee's Home calls at shift start, reaches the burst.

| Endpoint (names are placeholders for the engineer) | Who may call | Returns | Calls per use |
|---|---|---|---|
| `leader_home` | Leadership role | WOW card + Today for the saved scope. Built from the **same cached Attendance section** as the overview, so Home and overview never show two different figures | 1 per Home open. **None** for users without the role |
| `leader_summary(view, sections?)` | Leadership role | Today, Attendance, Leave, People, last 7 days, by-branch or by-department table, data up to, doubtful days, Needs review flags, the list of scopes for the switcher. Each section has its own `ok` / `error`. Records the chosen view as the user's last choice (one user default write, only when it changed) | 1 per scope load; 1 per "Try again" (that section only) |
| `leader_trend(view)` | Leadership role | 6-month trend | 1 per scope load, sent in parallel with summary |
| `data_review_items` | HR Manager; store HR for their branch | Doubtful days, leave and leavers items, with counts and dates. Re-runs the cheap leave and leavers checks for the caller's scope (OPS-49) | 1 per page open |
| `data_review_confirm(item, action)` | HR Manager; store HR for their branch | Stores the confirmation, clears that company's leader cache | 1 per confirmation |
| `leader_settings` | System Manager, HR Manager (read) | Saved minimum, the live impact line **for all values 3–10 at once** (so the stepper makes no call per tap), leader access list, change history (paged, 20 rows) | 1 per page open |
| `leader_settings_save(min_group, reason)` | System Manager only | Saves; history written by `track_changes` | 1 per save |
| `get_hr_analytics` (Step 0 rewrite) | HR roles, scoped to their company or branch | Same shared calculation as the leader view, without small-group hiding | unchanged |

| ID | Requirement | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-36 | **Recommend:** every leader and data-review endpoint resolves role and scope on the server **before** any cache read, on every request. Arguments go in the POST body (the portal's `gpSend` already does this). **Test:** a user with no Leadership role, and a leader with no Company or Branch permission, get a refusal and no figures from each endpoint; removing a User Permission takes effect on the very next call. | OPS-1, OPS-17. The cache must never answer the question "may this person see it?" | A removed leader keeps seeing figures for up to 60 minutes. | Recommend | |
| OPS-37 | **Recommend:** the overview uses two calls (`leader_summary`, `leader_trend`) with a per-section `ok` / `error` field, and "Try again" asks for one section. Server code computes each section separately, so one failing section never fails the call. **Test:** force the Attendance section to raise; the response still carries People and Leave, and Attendance carries a plain error with no server text. | Meets 01b §17 (per-card states) at 2 web slots per leader instead of 7. | One leader's scope switch holds most of a stack's 8 slots; stores hit nginx's burst. | Recommend | |
| OPS-38 | **Recommend:** `leader_home` makes no call for users without the Leadership role (decided from roles already on the page) and reads the Attendance figure from the overview's cached section, not a separate calculation. **Test:** load Home as an employee — zero leader calls in the network log; Home's WOW % equals the overview's Attendance % for the same scope and moment. | OPS-15. "One authoritative number" (brief S2). | Wasted calls for every employee; Home and overview disagree for up to 15 minutes. | Recommend | |
| OPS-39 | **Recommend:** the scope switcher needs **no extra endpoint**. The scope list comes inside the summary response; the last choice is saved by the summary call as a user default, only when it changed. The client ignores a second tap on the switcher while a load is running. **Test:** switching scope 5 times fast sends at most 5 summary + 5 trend calls and writes at most 5 defaults. | Keeps the switcher inside the call budget. | Double calls on every nervous tap; a write on every page load. | Recommend | |

## B · Rate limits

| ID | Requirement | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-40 | **Recommend:** do **not** use Frappe's `@rate_limit` with its IP default on these endpoints. If a limit is added, count per signed-in user: leader reads **60 per minute per user**; settings save **10 per hour**; data-review confirm **30 per hour**. Over the limit returns HTTP 429 and "Too many requests. Wait a minute and try again." **Test:** 61 summary calls in a minute from one user get one 429; a second user on the same IP is not affected. | Read in `version-16`: the decorator's identity is the IP, or a value the client sends. A store's staff share one IP. Normal use is under 10 leader calls a minute. | Either one store locks itself out, or a stuck client loop holds web slots for everyone. | Recommend | |
| OPS-41 | **FYI:** no nginx change in this slice. The existing `/api/` zone (120 a minute per IP, burst 30) stays. Leader pages add at most 3 calls per open. Whether stores already hit 429 at shift start is **not measured** — worth counting 429s per client address in the nginx log during the dev test week. | Leader load is small next to employee Home calls. | A limit problem that belongs to the whole portal gets blamed on this slice, or the reverse. | FYI | |

## C · Caching

Every key sits behind Frappe's site prefix (§1), so tenants never mix. The parts below stop
mixing **inside** one tenant.

**Key:** `ldr:{section}:{company}:{set}:{view}:min{n}:f{formula version}:d{data up to}:r{review version}[:{period}]`

| Part | What it holds | Why it is in the key |
|---|---|---|
| `section` | `today`, `att`, `leave`, `people`, `week`, `table`, `trend`, `att_raw` | One cache entry per card, so one slow part never blocks another |
| `company` | The company | Lets OPS-43 clear one company only |
| `set` | `C` for company scope, or a short hash of the leader's **sorted list of linked branches** | Rule 5c (01b §7): what a branch shows depends on the leader's whole set, not just that branch |
| `view` | `all`, or the branch being viewed | The switcher |
| `min{n}` | The minimum group value, read fresh from settings | Raising the minimum can never find an old answer (OPS-17) |
| `f` | A formula version constant in code | A Step 0 fix to the calculation never serves an answer from the old formula |
| `d` | `MAX(attendance_date)` in scope (index read) | A new day of data shows at once |
| `r` | Latest change time of the doubtful-day and data-review records for the company | An HR confirmation shows at once |
| `period` | Month for cards; `6m` for trend | — |

| Section | Expiry |
|---|---|
| `today` | 3 min |
| `att`, `leave`, `people`, `week`, `table`, `att_raw` | 15 min |
| `trend` | 60 min |
| Scope and role check, settings page, data-review page, HR Analytics | **not cached** |

| ID | Requirement | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-42 | **Recommend:** cache only the finished answer after small groups are removed, with exactly the key parts and expiries above. No names, employee IDs, leave types, pay or hidden figures ever reach Redis. **Test:** after a full walk of every view on a seeded site, scan every `ldr:` value for seeded names, IDs and a marker figure planted in a hidden group — none found. | Redis writes to disk here (`appendonly yes`, OPS-3). | Hidden figures sit on disk in `redis-data` and its backups. | Recommend | |
| OPS-43 | **Recommend:** clearing. (a) **Settings save:** after commit, delete every `ldr:` key for the site. (b) **HR confirmation:** after commit, delete that company's `ldr:` keys. (c) **Employee change** to `status`, `relieving_date`, `date_of_joining`, `branch`, `department` or `company`: after commit, delete that company's `ldr:` keys (compare with the record before save; do nothing for other fields). (d) **Attendance, check-in and leave saves: clear nothing** — the `d` part and the expiry cover them. **Test:** OPS-25's raise-and-lower test; and marking an employee Left with a date changes the People card on the next call. | OPS-4, OPS-18. Employee changes are rare and change headcount and leavers, which are shown to everyone in scope. Attendance changes are constant. | Stale leaver and headcount figures for 15 minutes after HR fixes them — exactly when HR checks whether "Needs review" cleared. | Recommend | |
| OPS-44 | **Recommend:** every `ldr:` key is written with an expiry (never above 60 min), and 012's cache stays under **10 MB per site**. **Estimate** at 5 KB per section: PP Jewellers (6 branches, ~13 views × 8 sections) ≈ 0.5 MB; a 50-branch tenant with 60 leaders (~160 views) ≈ 6.4 MB, briefly double while old keys expire. **Test:** after the full walk on the 2,000-person site, every `ldr:` key has a TTL > 0, and total bytes are under 10 MB. | Redis is shared with the job queue and has no memory ceiling (Read this first, 1). | The cache can crowd out the job queue for every tenant on the stack. | Recommend | |
| OPS-45 | **Recommend:** a failed cache read or write never fails the request. Compute the answer, return it, and log one line (OPS-56). The scope check is never skipped when Redis is down. **Test:** with the cache wrapper patched to raise, every leader endpoint still returns correct, correctly hidden figures. | Redis refusing writes is how `noeviction` behaves once a ceiling is set. | A cache problem blanks every leader page. | Recommend | |
| OPS-46 | **Consider:** a short build lock per key (set `ldr:…:building` only if absent, 30 s expiry) so two leaders missing the same key at 9 a.m. do not both compute it; the second waits up to 2 s for the first, then computes anyway. | Cold misses are the expensive path at 2,000 people. | At month start, several leaders compute the same answer at once and hold several web slots. | Consider | |
| OPS-47 | **Ask the user, outside this slice:** set a Redis memory ceiling, or split cache and queue into two Redis instances as the Compose comment already suggests (cache: `allkeys-lru`, no disk; queue: `noeviction`, AOF). | Read this first, 1. A new service or memory setting needs your approval. | A runaway cache from any feature can stop job queueing on the whole stack. | Consider | |

## D · Scheduled jobs

One job, **"leader data checks"**, does the doubtful-day check and both "Needs review" checks.

| Property | Requirement |
|---|---|
| When | `scheduler_events["cron"]["30 6 * * *"]` — 06:30 site time, after overnight device sync and HRMS auto-attendance |
| Queue | **`long`.** Read in `version-16`: a `cron` entry always runs on `default` (only frequencies with "Long" go to `long`). So the cron entry only calls `frappe.enqueue(…, queue="long", timeout=900, job_id="leader-data-checks", deduplicate=True)` |
| Work | For each company, then each branch: doubtful days for the **last 35 days** (D5, only groups of at least the minimum, OPS-22); leave check D6; leavers check D18. Grouped queries only — never a loop over employees |
| Storage | One record per branch per day **only when a day was ever doubtful**, and one record per leave or leavers item. Fields include status, counts, `confirmed_by`, `confirmed_on`. `track_changes` on |
| Idempotent | Unique on (company, branch, date) or (company, item). A re-run updates counts **only when they changed**, never touches a confirmed status, and marks a day "cleared" instead of deleting it |
| Transactions | Commit per company, so a failure in one company keeps the others |
| Cost, **estimate** | 2,000 people: ~140,000 check-ins and ~70,000 attendance rows grouped by branch and day, with the OPS-52 indexes. Under 60 s per site |

| ID | Requirement | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-48 | **Recommend:** the job as specified above: 06:30 cron that enqueues onto `long`, 900 s timeout, job ID deduplication, grouped queries, commit per company, writes only on change, never overwrites an HR confirmation. **Test:** run it twice on the seeded site — the second run changes zero rows and adds zero `Version` rows; kill it mid-run, re-run, the result equals one clean run; confirm a day, re-run, still confirmed. | `nfr-budget.md` §2 "writes only on change"; §3 "a defined end state". Lesson 1: a job nobody listens to sits queued forever. | Duplicate or flapping "Needs review" items; a morning `Version` flood; confirmations silently undone. | Recommend | |
| OPS-49 | **Recommend:** `data_review_items` re-runs the cheap leave (D6) and leavers (D18) checks for the caller's scope when HR opens the page, and saves only changes. Doubtful days stay on the morning run, plus a re-check of one day when HR confirms it. **Test:** give the 14 leavers a date, open Data to review — the item is gone without waiting for 06:30. | 01b §8.10: "Clears by itself once every leaver has a leaving date." Counts on indexed Employee fields are cheap. | HR fixes the data and still sees the item until tomorrow; they fix it again. | Recommend | |
| OPS-50 | **Recommend:** failure is visible. On error, log with a fixed title ("Leader data checks failed"), the company and stage, and the error type — **not** the full traceback with local values, which can hold group counts. Store "last successful run" time. Data to review shows "Last checked 06:32"; if older than 26 hours it shows an amber line "Checks have not run since …". The existing `health.collect_scheduled` carries the error count to the control plane. **Test:** force a failure — an Error Log row exists with no names or counts, and the page shows the amber line once the stamp is old. | OPS-9. `nfr-budget.md` §8 "failed background jobs" alert. | Doubtful days stop being found and every leader sees wrong attendance without warning. | Recommend | |
| OPS-51 | **Recommend, re-ranked from §1 OPS-8:** no nightly pre-aggregation in this slice. It becomes **required** when any of these is true: the cold `leader_trend` call is over **1 s p95** on the 2,000-person site; the cold `leader_summary` call is over **2 s p95** there; or a real customer above 2,000 employees is signed (brief P8). If required, store one row per group (company, branch, department) per **month**, with distinct-person counts, recomputed for the current month only. | Read this first, 3. `nfr-budget.md` §2: anything over 2 s moves to a background job. | Either unneeded work now, or a per-day summary that cannot give the distinct-people counts the privacy rule needs. | Recommend | |

## E · Database indexes

All approved on 15 Sep. **Every one is added through our app, never by editing a Frappe, ERPNext
or Frappe HR doctype file** (lesson 7, `nfr-budget.md` §9).

| Table | Index | Serves |
|---|---|---|
| `tabEmployee` | `company` · `branch` · `department` · `date_of_joining` · `relieving_date` (five single-column) | Scope, headcount, joiners, leavers, D18 |
| `tabEmployee Checkin` | `(alvoraa_branch, time)` and `(time)` | D11 "in so far today", doubtful-day check |
| `tabAttendance` | `(alvoraa_branch, attendance_date)` | Branch scope figures, data up to, trend |
| `tabKPI` | `employee`, `appraisal_cycle` | **Already added by slice 010** (`d099aa7`). Not repeated |
| `tabAppraisal` | `appraisal_cycle` | **Not in 012.** Moves to the Performance slice |

**How, Frappe-first:** `frappe.db.add_index(doctype, fields)` in an `after_migrate` function in
`alvoraa_portal`, beside `branch_scope.after_migrate`. Read in `version-16`: it checks for the
index first and runs `ALTER TABLE … ADD INDEX IF NOT EXISTS`, so a second run does nothing. It is
the same call `attendance_deduction.py` already uses. The other Frappe-first route, a Property
Setter with `search_index`, **cannot make a two-column index** and only builds the index when
that doctype is next synced, so it is not recommended here.

**Time and locking, estimate** (based on common InnoDB build speeds of roughly 50,000–200,000
rows a second on modest hardware; not measured on our server):

| Rows in the table | Time per index | Extra disk per index |
|---|---|---|
| Employee, up to 5,000 | under 1 s | negligible |
| 45,000 (Checkin today, PP Jewellers) | under 1 s | ~2–5 MB |
| 125,000 (Attendance, 400 people, 1 year) | ~1–3 s | ~5–15 MB |
| 500,000 | ~3–10 s | ~20–60 MB |
| 1,200,000 (Checkin, 2,000 people, 1 year) | ~6–25 s | ~50–150 MB |

Backups (`bench backup`, a SQL dump) hold no index data, so backup size does not change.
**Restore time does grow**, because indexes are rebuilt on restore.

| ID | Requirement | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-52 | **Recommend:** add the eight indexes in the table above with `frappe.db.add_index` in `after_migrate`, safe to run twice. **Test:** after migrate on a fresh site built the way CI builds one (lesson 6), `frappe.db.get_column_index` finds each one; running migrate again changes nothing; `EXPLAIN` on each main leader query shows the index in use and no full scan of Attendance or Employee Checkin. | Measured in §1: none of these exist. `EXPLAIN` is the only proof the query uses them. | Queries stay fast at 400 people and fall over at 2,000. | Recommend | |
| OPS-53 | **Recommend:** time the index migration on a copy before it reaches dev or production: first on the synthetic 2,000-person site, then on a rehearsal copy of a dev dump (`REHEARSAL.md`). Record time per table in the implementation notes. | The table above is an estimate. | A migrate that holds `Employee Checkin` for longer than expected during a live deploy. | Recommend | |
| OPS-54 | **Recommend:** run the migrate that adds these indexes inside the runbook's existing hold (`bench --site all backup --with-files` first, maintenance on, `DEPLOYMENT_RUNBOOK.md`), and not while a long report or job is running on the same tables. Production has four sites on one database, so allow for the sum of all sites. | Read this first, 4: the brief exclusive lock waits behind long queries, and everything else queues behind it. | Check-ins and attendance writes stall for the length of the longest running query. | Recommend | |
| OPS-55 | **FYI:** slice 011's single-column `alvoraa_branch` index on Attendance and Employee Checkin becomes partly redundant once the two-column ones exist. Leave it — it belongs to 011's custom field, and dropping it saves little. A `(company, attendance_date)` index for multi-company tenants is **not approved**; add it only if `EXPLAIN` on a two-company synthetic site shows a full scan. | Keeps 012 inside what was approved. | — | FYI | |

## F · Monitoring and logging

| ID | Requirement | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-56 | **Recommend:** every leader, data-review and settings endpoint writes **one** log line when it takes over **1 s**: endpoint, section, scope type (`company` / `branch` / `set`), number of branches in view, cache hit or miss, query count, duration in ms. Use a named Frappe logger (for example `frappe.logger("leader_view")`). **Test:** force a slow path — exactly one line appears, holding only those fields. | `nfr-budget.md` §8: "someone on call at 2 a.m. can answer why". Slow cold misses are the risk to watch. | Slowness is reported by a customer before we see it. | Recommend | |
| OPS-57 | **Recommend:** these must **never** appear in any log line, error message, Error Log, URL or response to a leader: any figure (shown or hidden), group sizes, employee names or IDs, leave types or reasons, pay, branch or department names. **Test:** run the leader test module with seeded names and a planted marker figure in a hidden group; scan test output, Error Log rows and the logger file — none found (`nfr-budget.md` §4 CI gate 4). | OPS-11. Gunicorn prints every URL (`--access-logfile -`). | Personal data in container logs kept for 180 days. | Recommend | |
| OPS-58 | **Recommend:** audit trail from Frappe, not new log code. Settings: a Single doctype with `track_changes` and a required `reason` field (OPS-23). HR confirmations: `confirmed_by`, `confirmed_on` and `action` on the record, with `track_changes`. HR Manager reads settings history through one endpoint filtered to that doctype, **not** through read access to `Version`. **Test:** a save and a confirmation each add one `Version` row with before, after and the user; HR Manager calling `frappe.get_list("Version")` directly is refused. | 01b §16 items 15a and 19. | Either new code to maintain, or HR Managers reading every change in the system, salary edits included. | Recommend | |
| OPS-59 | **Consider:** named owners for three alerts, per `nfr-budget.md` §8: "leader data checks failed" (Error Log count via `health.collect_scheduled`), "last successful check older than 26 hours", and "more than 10 slow leader calls in an hour" (from OPS-56). **The owner is a person you name.** | The budget requires named owners; I cannot pick them. | Alerts fire into nobody's inbox. | Consider | |

## G · Backups and retention

| ID | Requirement | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-60 | **Recommend:** settings history (`Version` rows) and HR confirmation records live in the site database, so the existing `bench backup` covers them. Keep both for the life of the tenant; no automatic clean-up in this slice. `Version` is not in Frappe's default log clean-up (checked in §2). The doubtful-day and data-review records follow the same retention as Attendance (36 months online, `nfr-budget.md` §5, marked there as needing counsel). **Test:** the quarterly restore drill checks that the newest settings history row and the newest confirmation exist after restore. | They are the proof of who changed a privacy rule and who declared an absence real. | The evidence is gone exactly when a dispute needs it. | Recommend | |
| OPS-61 | **FYI to security (01c):** the required "reason" on a settings change is free text and is kept for ever. Someone may type a name into it. Suggest hint text "Do not name employees" and a PRIV decision on whether it is ever redacted. | Free text in a permanent record. | Personal data in an undeletable history. | FYI | |
| OPS-62 | **FYI:** after any database restore, delete the site's `ldr:` keys. The `d` and `min` key parts make most old answers unreachable anyway, and every key expires within 60 minutes. The engineer checks whether `bench clear-cache` deletes custom keys; if not, the restore checklist gets one line. | A restored older database with a newer cache. | Up to an hour of figures from data that no longer exists. | FYI | |

## H · Performance budget per endpoint

From `nfr-budget.md` §2: whitelisted call **≤ 500 ms p95**; report or dashboard **≤ 3 s**;
skeleton **≤ 300 ms**; anything **over 2 s** goes to a background job. Times are server time on
the test site. "Warm" is a cache hit; "cold" is a miss.

| Endpoint | Warm p95 | Cold p95, 400 people | Cold p95, 2,000 people | Payload (uncompressed JSON) |
|---|---|---|---|---|
| `leader_home` | ≤ 150 ms | ≤ 300 ms | ≤ 500 ms | ≤ 5 KB |
| `leader_summary` | ≤ 200 ms | ≤ 500 ms | ≤ 500 ms target; **≤ 2 s hard limit** (over 500 ms needs a dated exception in the implementation notes; over 2 s triggers OPS-51) | ≤ 20 KB |
| `leader_trend` | ≤ 150 ms | ≤ 500 ms | ≤ 1 s (over 1 s triggers OPS-51) | ≤ 5 KB |
| `data_review_items` | not cached | ≤ 500 ms | ≤ 500 ms | ≤ 10 KB |
| `data_review_confirm`, `leader_settings_save` | — | ≤ 500 ms | ≤ 500 ms | tiny |
| `leader_settings` (impact for 3–10 in one go) | not cached | ≤ 500 ms | ≤ 500 ms | ≤ 15 KB |
| `get_hr_analytics` after Step 0 | not cached | ≤ 500 ms | ≤ 1 s | unchanged |
| Leader data checks job | — | ≤ 20 s | ≤ 60 s; 900 s timeout | — |
| Overview page, broadband | skeleton ≤ 300 ms; all cards ≤ 3 s | | | |

Every endpoint has a **fixed query count** that does not grow with employees or branches.
The engineer sets the numbers at strategy; the tests hold them.

## I · Test plan at 400 and 2,000 employees

**Where:** the local bench only, on two new synthetic sites built the way CI builds one (lesson
6). **Creating them is a bench action and needs your word.** Never a copy of real data
(`nfr-budget.md` §5). The concurrency step needs gunicorn, which the local bench does not run
(it runs `bench serve`), so that step runs on a rehearsal stack (`REHEARSAL.md`), also on your word.

| Seed | 400-person site | 2,000-person site |
|---|---|---|
| Companies / branches / departments | 1 / 6 / 12 | 2 / 25 / 40 |
| Attendance, 12 months | ~125,000 | ~620,000 |
| Check-ins, 12 months | ~250,000 | ~1,200,000 |
| Must include | one 4-person branch; a 42-person branch hidden by subtraction; 3 doubtful days; 14 Left with no date; one leader of 2 branches; one leader with no permission | same, plus a leader of 6 branches |

| ID | Requirement | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-63 | **Recommend:** query-count tests for every endpoint in section A, run in CI on `test_site`: the count is identical with 10 and with 100 seeded employees, and with 2 and 8 branches. | `nfr-budget.md` §2: "the cheapest scale defence you have". | A loop over employees ships unnoticed. | Recommend | |
| OPS-64 | **Recommend:** timed runs on both synthetic sites: for company scope, one branch, a 2-branch set and a set holding the 4-person branch — 30 cold calls (cache cleared each time) and 30 warm calls per endpoint; report p50 and p95 against section H; `EXPLAIN` each main query. Also time the leader data checks job and the index migrate (OPS-53). | Turns every estimate in this file into a measurement. | The first 2,000-person customer does the load test for us. | Recommend | |
| OPS-65 | **Recommend:** a concurrency run on the rehearsal stack: 10 leaders loading the overview at once while 50 simulated employees open Home. Pass: no request over 2 s, no 5xx, no app-level 429 for normal use. | Proves the 8 web slots are enough at month start. | Leaders' pages slow down employees' leave requests. | Recommend | |
| OPS-66 | **Consider, only if OPS-51 fires:** a 5,000-person site (~1.56 M attendance rows) to size the monthly summary. | 5,000 is 2.5 times the design ceiling (§1). | — | Consider | |

## J · Rollout, switch and rollback

**No feature flag. The Leadership role is the switch** (CLAUDE.md §4: no feature flags unless
required). The role is created on migrate but held by nobody. Without it there is no menu entry,
no Home call (OPS-38) and every endpoint refuses (OPS-36). Turning the view off for one tenant,
without a deploy, is removing the role in Desk — inside the budget's 15-minute rollback
(`nfr-budget.md` §3). Plan gating (`analytics`, brief P6) is a separate, existing gate.

**Step 0 has no switch.** It changes numbers every HR user sees: HR Analytics becomes scoped
(LV4), doubtful days are left out, leave use uses this leave year only. **Tell each tenant's HR
before it reaches them.**

| Order | What | Why this order | Rollback |
|---|---|---|---|
| 1 | **Indexes** (section E) | Changes no behaviour. Makes Step 0 and the morning job fast from their first run. Its migrate time is measured on its own | Leave them in place. They are harmless |
| 2 | **Step 0**: shared calculation, HR Analytics scoped to company or branch, doubtful-day and data-review records, the morning job, Data to review page | Closes the LV4 leak that exists today. The leader view's explanation text is only true after it | `git revert`, deploy on your word. New tables stay (Frappe does not drop them) and are harmless. The job's Scheduled Job Type goes on migrate |
| 3 | **Leader view**: role, endpoints, cache, settings page, Home card, employee line | Built on 1 and 2 | Remove the role from users (no deploy). Full removal: `git revert`, deploy; `ldr:` keys expire within 60 minutes |

| ID | Requirement | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-67 | **Recommend:** the order above, as **two pushes to `dev`**, each on your word: push 1 = indexes + Step 0; push 2 = leader view. Then to `main` in the same order, after dev testing. Batch the revisions of each push (CLAUDE.md §1: six pushes in an hour made deploys cancel each other). | Step 0 fixes a live leak and should not wait for the leader screens; the screens should not ship before Step 0. | Either the leak waits for the whole slice, or leaders see figures the HR page contradicts. | Recommend | |
| OPS-68 | **Recommend:** no feature flag; the Leadership role is the switch, and Step 0 ships with a short note to each tenant's HR. **Test:** a fresh site after migrate has the role, nobody holds it, and no user sees a leader menu or makes a leader call. | CLAUDE.md §4. The role already fails closed. | A flag nobody removes; or HR sees numbers change with no warning. | Recommend | |
| OPS-69 | **Recommend:** release checks carried into §5 for this slice: bare `docker compose up -d`, never a service list (lesson 1); every app container on the same image tag, `worker-long` included, because it runs the morning job (lesson 2); exactly one scheduler; the site scheduler is enabled; the morning after deploy, the job's "last successful run" is today and the Error Log has no "Leader data checks failed". | Lessons already paid for. The job is this slice's first dependency on `worker-long`. | The morning check silently never runs, and doubtful days go unwarned. | Recommend | |

## What I did and did not check

- **Did:** read the slice files, the NFR budget and the definition of ready; read the Compose files,
  `deploy/nginx.conf`, `alvoraa_portal/hooks.py`, `branch_scope.py`, `hr_api.py` (cache use),
  `attendance_deduction.py`, `REHEARSAL.md`, `DEPLOYMENT_RUNBOOK.md` (backup lines) and slice 010's
  group D notes; read three Frappe `version-16` files on GitHub (15 Sep 2026) for rate limiting,
  scheduled job queues and `add_index`.
- **Did not:** run anything on the bench, dev or production; measure any endpoint, index build or
  job (they do not exist yet); check the server's memory or current Redis size; check whether
  `bench migrate` turns on maintenance mode by itself in `version-16`; check whether
  `bench clear-cache` removes custom keys; check whether `User Permission` keeps change history.
  Every time, size and row count above is an **estimate** unless marked measured or read.

---

# §4 · 15 September 2026 — Strategy (push 1 only)

Inputs read: `00-impact-analysis.md` (engineer, push 1), `02-functional-spec.md` (US-1 to US-10,
§10, "User decisions (2026-09-15)"), §1–§3 above, `.claude/work-in-progress.md`,
`.github/workflows/ci.yml` and `deploy.yml`, `deploy/Dockerfile`, both Compose files,
`REHEARSAL.md`, `DEPLOYMENT_RUNBOOK.md`, `scripts/check_app_integrity.py`,
`alvoraa_portal/hooks.py`, `test_portal_security_010.py` (the `ignore_permissions` counter).
Frappe source read **inside `hrlocal-bench`, Frappe 16.33.1, on 15 Sep 2026**. Line numbers below
are from that copy.

**Nothing was changed.** I read files inside the container and ran one read-only `SELECT` on
`ppj.localhost` (Property Setters and Custom Fields on Employee). No `docker cp`, no migrate, no
bench-changing command, nothing on dev or production.

## Read this first

1. **On the index method, the engineer is right and my §3 was wrong.** Frappe removes a
   one-column index from a standard table whenever it re-syncs that table and the field is not
   marked "indexed" (`search_index`). `frappe.db.add_index` would normally mark the field for us,
   but it skips that step during migrate and install — exactly where we call it. Evidence and the
   recommended method are in section A.
2. **The risk is bigger than "on the next upgrade".** The re-sync also runs **at any time** when
   someone saves a Custom Field on Employee or Employee Checkin — from the desk, from any app's
   installer, or from Customize Form. Outside migrate, nothing puts the index back until the next
   deploy. `ppj.localhost` already has 24 Custom Fields on Employee (measured).
3. **HR numbers will change twice, not once, unless the check runs at deploy.** Doubtful days are
   only left out once the 06:30 morning check has created them. On deploy day HR sees one figure;
   the next morning it jumps. On the demo tenant that is **65.8% on deploy day, then 97.0%** the
   next morning. Section E proposes running the check once at the end of migrate.
4. **A full rollback of push 1 reopens the three leaks it closes (G1, G2, G3).** Fixing forward is
   the better default for a small fault. Section F.
5. **The deploy workflow's standard rollback advice ("previous tag, migrations off") is the wrong
   one for push 1.** With migrate off, the 06:30 job stays registered and calls code that no longer
   exists, every morning. Section F.

---

## A · The index method — who is right, with evidence

**Verdict: the engineer (D-14).** Recommend: a Property Setter `search_index = 1` plus
`add_index` for the **six one-column** indexes; `add_index` alone for the **two two-column** ones.

### What Frappe does, step by step

| # | What happens | Where (Frappe 16.33.1) |
|---|---|---|
| 1 | When Frappe syncs a table, it builds each column's "should be indexed" flag **only** from the field's `search_index` (after Property Setters are applied) | `frappe/database/schema.py:105` |
| 2 | It reads "is indexed now" from the database: true if the column is **first** in any non-unique index | `frappe/database/mariadb/database.py:341-357` |
| 3 | Indexed now, but not flagged → the column goes on the drop list | `frappe/database/schema.py:310-312` |
| 4 | Before dropping, it looks up the index with `get_column_index`, which **skips any index that has a second column** | `frappe/database/mariadb/database.py:389-417` |
| 5 | So a one-column index is dropped; a two-column index is never dropped | `frappe/database/mariadb/schema.py:141-144`, run at `:161` |
| 6 | `add_index` creates the index, and adds a Property Setter to protect it **only when not in migrate or install** | `frappe/database/mariadb/database.py:432-442` |
| 7 | `in_migrate` is true for the whole migrate, including `after_migrate` hooks | `frappe/migrate.py:96`, hooks run at `:200-203` |
| 8 | `in_install` is set during `install-app`, which runs `after_install` | `frappe/installer.py:300, 313` |

### When the re-sync (step 1) runs

| Trigger | Where | When it happens to us |
|---|---|---|
| A standard doctype's JSON changed | `core/doctype/doctype/doctype.py:537` | An ERPNext update changes `employee.json`; a commit in our HRMS fork changes `employee_checkin.json`. Both Dockerfile and CI follow the moving `version-16` branch, so this can arrive with any image build |
| A Custom Field is saved on that doctype | `custom/doctype/custom_field/custom_field.py:222` | **Any time.** A System Manager adds a field in the desk; `field_checkin.after_migrate` changes one of our Checkin fields; India Compliance or HRMS change their Employee fields |
| `create_custom_fields` changed something | `custom_field.py:385` | Any app's installer, on migrate |
| Customize Form save | `custom/doctype/customize_form/customize_form.py:245` | Any time, from the desk |
| Customization files synced | `modules/utils.py:239` | On migrate |

### What that means for the eight indexes

| Index | Survives with `add_index` alone? | Why |
|---|---|---|
| Employee `company`, `branch`, `department`, `date_of_joining`, `relieving_date` | **No** | One column, field not flagged (engineer read the JSON; I confirmed no `search_index` Property Setter exists on ppj) |
| Employee Checkin `(time)` | **No** | One column, `time` not flagged |
| Employee Checkin `(alvoraa_branch, time)` | Yes | Two columns — step 4 skips it. `alvoraa_branch` is also flagged by slice 011 |
| Attendance `(alvoraa_branch, attendance_date)` | Yes | Two columns |

Two things that confirm the pattern. Every existing `add_index` call in our repo is two-column
(`attendance_deduction.py:212`, and in the HRMS fork `leave_application.py:1564`,
`leave_ledger_entry.py:278`, `salary_slip.py:2646`). So the spec's precedent (G-11) is only a
precedent for two-column indexes. And the cost of losing the index is not only a slow query: on the
next deploy `after_migrate` rebuilds it, which on `Employee Checkin` at 1,000 people is an
**estimated** few seconds of table lock per deploy, every time it was dropped.

### Where my §3 went wrong

§3 said a Property Setter "only builds the index when that doctype is next synced, so it is not
recommended". The first half is true. I missed that the same sync **removes** an unflagged
one-column index. The two methods are not alternatives; for one-column indexes you need both.

### The recommended method, exactly

1. For each of the six one-column indexes: **if** no Property Setter exists for (doctype, field,
   `search_index`), call `make_property_setter(doctype, field, "search_index", "1", "Check",
   for_doctype=False)`. Then `frappe.db.add_index(doctype, [field])`.
2. For the two two-column indexes: `frappe.db.add_index` only.
3. **Keep the check "if it does not exist".** Without it, each migrate deletes and re-inserts the
   Property Setter (`property_setter.py:103-114`) and clears Employee's cache — harmless, but churn.
4. **Keep `is_system_generated` at its default, `True`** (`property_setter.py:82`). "Reset to
   defaults" in Customize Form deletes only Property Setters with `is_system_generated = False`
   (`customize_form.py:688-701`). So a System Manager resetting Employee will not remove the
   protection.
5. The index name `add_index` uses (`company_index`, `database.py:1386-1389`) is the same name
   Frappe's own sync would use (`mariadb/schema.py:88-90`, which also checks by column first). No
   duplicate index can appear.

### What a Property Setter on Employee means

Employee is an ERPNext standard doctype. A Property Setter is a **site customisation**: a row in
`tabProperty Setter` in that tenant's database.

- It travels with the site: in every backup and restore, and it stays if `alvoraa_portal` is ever
  uninstalled or push 1 is reverted.
- It shows as "Index" ticked on those six fields in Customize Form. Nothing else changes for users.
- If anyone runs "Export Customizations" for Employee into an app, these six rows go with it. FYI.
- It does not edit ERPNext's files, so lesson 7 (never redefine a Frappe or ERPNext doctype) holds.

---

## B · Install order, image and Compose, migration risk

### Order inside the one push-1 deploy

Push 1 is one deploy with one migrate. Frappe fixes the order inside migrate; I read it in
`frappe/migrate.py`:

| Step | What runs | Push 1 part | Where |
|---|---|---|---|
| 0 | Backup of every site, with files | Rollback point | `deploy.yml:150` |
| 1 | `up -d` — new image on every container, `worker-long` included | **Step 0 code** is live, against the old schema, for seconds | `deploy.yml:271` |
| 2 | Maintenance on, per site; the scheduler stops | — | `deploy.yml:192-212, 289`; `utils/scheduler.py:151` |
| 3 | Patches, then doctype sync | **The two new doctypes** created (empty) | `migrate.py:139-145` |
| 4 | `sync_jobs` | **The 06:30 cron entry** registered | `migrate.py:162` |
| 5 | Customizations, orphan clean-up | — | `migrate.py:180-189` |
| 6 | `after_migrate` hooks, app by app, in list order | `branch_scope.after_migrate` (makes `alvoraa_branch` exist) **then** `data_review.after_migrate` (**indexes**, then — if OPS-72 is taken — enqueue the first check) | `migrate.py:200-203` |
| 7 | `clear-cache`, maintenance off, nginx restart, smoke test | — | `deploy.yml:311-326` |

So the order you asked for holds where it matters: the indexes exist before the job's first run,
and the job cannot run during migrate because the scheduler is stopped.

**Two ordering rules the engineer must keep:**

- `data_review.after_migrate` sits **after** `branch_scope.after_migrate` in both `after_migrate`
  and `after_install`. The two-column indexes need the `alvoraa_branch` column, and on a tenant where
  slice 011's migrate has not run yet (ppj today), `branch_scope` creates it in the same migrate.
- Inside `data_review.after_migrate`: indexes first, enqueue last.

### Image and Compose changes

**None.** Confirmed by reading `deploy/Dockerfile` and both Compose files:

| Question | Answer |
|---|---|
| New app, new dependency, new service | No. The new doctypes and modules are inside `alvoraa_portal`, which the Dockerfile copies from the commit (`Dockerfile:53`) |
| New queue | No. `long` exists; `worker-long` runs in `docker-compose.app.yml:184-186`, and devstack uses the same file |
| nginx, env var, secret | No |
| Image size, build time | No measurable change (a few Python and JSON files) |
| Portal page weight | **Grows.** The Data to review panel is added inline to `hrms-employee.html`, already 977 KB and downloaded on every visit (§2a). See OPS-82 |

### Migration risk

| Risk | Dev | Production (later) | What covers it |
|---|---|---|---|
| Index builds lock `Employee Checkin` briefly | Dev owns its own database; sizes not measured by me | Four sites on one database; the times add up. Row counts **not measured** (production wall) | OPS-53: timed on the synthetic 1,000-person site and a rehearsal copy of a dev dump, recorded in `03` |
| An `ALTER` waits behind a long running query | Same | Same | Migrate waits at most 5 minutes for a lock, then fails (`migrate.py:220-227`). Maintenance stops the scheduler but **not** jobs already running on the workers. OPS-73: pick the deploy time |
| New code runs before its tables exist (step 1 to step 3) | HR Analytics may fail for a few seconds | Same | FYI only. Maintenance comes on seconds later. The job does not run in that window |
| `alvoraa_branch` missing on a tenant | Covered by list order above | Same | The engineer's column check plus the ordering rule |
| Migrate fails half-way through `--site all` | Some sites migrated, some not | Same | Existing: the workflow's trap turns maintenance off; restore from step 0's backup if a site is broken |
| Existing data changed | No. AC-161: no Attendance, Leave or Employee record changes | Same | AC-161 test |

### The maintenance hold (OPS-54)

**Already in the workflow; no runbook change needed.** `deploy.yml` takes the backup, turns
maintenance on per site, migrates, clears the cache, and turns maintenance off (lines 150, 192-212,
289-312). What OPS-54 still needs is **timing**, in OPS-73.

---

## C · CI gates for push 1

### What already guards push 1 (blocking, in `ci.yml`)

| Gate | Covers in push 1 |
|---|---|
| App integrity, no bench (`ci.yml:88-89`) | New doctype folder, file and class names. **Every** dotted string in `hooks.py` must resolve, which includes the new cron entry and the `after_migrate` / `after_install` lines (`check_app_integrity.py:104-120`) |
| App integrity, with bench (`ci.yml:272-275`) | The new doctype names do not shadow an upstream one |
| Front-end API paths (`ci.yml:82-83`) | The page's new calls to `data_review_items` / `data_review_confirm` point at real functions |
| Portal buttons wired, no undefined identifiers (`ci.yml:116-127`) | The new panel's handlers |
| Design system (`ci.yml:100-101`) | The new panel's colours, font sizes and contrast |
| Python tests (`ci.yml:278-282`) | `alvoraa_goals` and `alvoraa_portal` suites, on a site built with `install-app` (so `after_install`, not `after_migrate`) |

### Gaps I found

1. **CI never runs the HRMS fork's tests.** `ci.yml:281-282` runs only `alvoraa_goals` and
   `alvoraa_portal`. The engineer puts the AC-11 pin (appraisal attendance scores do not move) in
   `hrms/alvoraa_hr_core/tests/test_attendance_score.py`, so CI would never run it.
2. **The `ignore_permissions` counter only checks files it lists.** `test_portal_security_010.py:708-716`
   walks a fixed `CEILINGS` table. `org_figures.py` and `data_review.py` are new files and are not in
   it, so "the counter does not rise" (AC-45, SEC-8) proves nothing for them.
3. **Nothing tests that an index survives a re-sync.** CI builds its site with `install-app`, never
   migrates, and never re-syncs Employee. Section A's failure would pass CI.
4. **The string inside `frappe.enqueue("alvoraa_portal.data_review.run_morning_checks", …)` is not
   checked.** The integrity script reads `hooks.py` only. A typo fails silently at 06:30.
5. FYI: ruff and Semgrep are non-blocking (`ci.yml:57, 130`). Not push 1's to change.

### Version pinning

- **Push 1 installs no app, so there is nothing new to pin.**
- But push 1 leans on Frappe details: the index rules in section A, `enqueue(deduplicate=…)`, and
  cron jobs running on `default`. The Dockerfile (`:25-26`) and CI (`ci.yml:163-164`) both follow the
  moving `version-16` branch, so the image that reaches `main` can carry a newer Frappe than the one
  tested on dev. Pinning Frappe by commit is ARCHITECTURE decision 6, outside this slice. Inside the
  slice, the OPS-71 test is the tripwire, and OPS-77 records the version.

---

## D · Sequencing with slice 010 group D

**Confirmed, and the gap has grown.** At 15 Sep, local `dev` is **16 commits** ahead of
`origin/dev` (c27fb56), not 14 — two more group D test commits (4c30722, 4bb3d8d) landed after the
engineer's check. The work board shows group D phase 2 still building, with phases 3–4 to come.
Pushing `dev` pushes all of it, so push 1 cannot go first without splitting group D out of `dev`.
That is a call for you and the 010 session.

**Rollout implication: one push each, one CI and one deploy each, never overlapping.**

- CI cancels a running check when a newer push lands on the same branch (`ci.yml:16-18`), and the
  deploy only starts when CI succeeds. Two pushes close together means the first one's deploy never
  runs, and both land in one migrate — the 10 Sep pattern.
- Each push has its own migrate: group D adds HR Settings fields, review doctypes and patches; push 1
  adds two doctypes, a job and eight indexes. Separate deploys mean a failed migrate names its cause,
  and one can be rolled back without the other.
- The same order applies later for `main`: group D's release first, push 1 in its own release.

---

## E · "HR numbers change on day 1"

**What changes, per HR user:** the attendance formula (Work From Home counted, doubtful days left
out, the period), scope (store HR and single-company HR see less), leave used (this leave year only),
and an HR login with no company link sees the "not linked" message instead of figures.

**Bad news: without a change, it changes twice.** The engineer's page re-check clears items but does
not create doubtful-day items (D-5). They first appear at 06:30. So:

| Moment | Demo tenant (ppj) September attendance |
|---|---|
| Before push 1 | 65.8% |
| Deploy day, after migrate | about 65.8% (new formula, but no doubtful days stored yet; ppj has 0 Half Day and 0 WFH rows) — **estimate** from the engineer's measured counts |
| Next morning, after 06:30 | 97.0% (7–9 Sep left out) |

**Recommend (OPS-72): enqueue the morning check once, at the end of `data_review.after_migrate`,**
with the same `job_id` and `deduplicate`. Then the figure changes once, minutes after the deploy.
The job skips tenants without `analytics` (D-9) and writes only on change, so a second migrate costs
a few seconds of reading. Not in `after_install` — a new site has no data. Maintenance mode does not
stop workers from running a queued job (no maintenance check in `utils/background_jobs.py`); it runs
as soon as `worker-long` picks it up. **The engineer should confirm this is safe; I have not run it.**

**What to tell tenant HR** (OPS-79) — a short note, plain words:

1. "Attendance % now counts work-from-home days and leaves out days where the attendance device looks
   broken (almost everyone absent and almost nobody checked in). Your figure may go up or down."
2. "You now see only your own company, or your own store if you are store HR."
3. "A new page, **Data to review**, lists figures that look wrong. Fix the data or confirm it is right.
   Company and branch heads will later see 'Needs review' until you do."
4. "If you see 'not linked to a company', ask your System Manager to link your login."

**When:** before the push that reaches that tenant. For dev tenants used by real people, before the
dev push. For production, at least two working days before `main`. **Who sends it is yours to name
(BA-Q14).**

**Is dev testing enough before `main`?** Recommend yes, **if** all four are true (OPS-80):

1. Dev stays deployed through **at least one 06:30 run**, and the "last successful run" stamp is that
   morning with no "Leader data checks failed" in Error Log.
2. HR Analytics and Data to review are checked as an HR Manager, a store HR user and an HR login with
   no link.
3. The index migrate has been timed on the rehearsal copy (OPS-53).
4. Production still has no live customer. My memory note says none on 14 Sep 2026; please confirm
   at release time. If one is live by then, a rehearsal on a **production** dump is worth considering —
   that needs production access, so it is your decision, not mine.

---

## F · Rollback for push 1

**Bad news first: reverting push 1 reopens G1, G2 and G3** — store HR would again see every store's
names and figures, and any HR user could again write any org setting. **Prefer fixing forward** for a
small fault. The engineer's commit plan helps: G2 (commit 2) and G3 (commit 3) do not depend on the
calculation, so a figures problem can be reverted without them. G1 lives in commit 6 with the
calculation, so reverting the figures reopens G1.

**If a full rollback is needed:** `git revert` of push 1's commits, pushed to `dev` on your word. The
normal deploy runs migrate for branch pushes (`deploy.yml:104`). **Keep migrate on.**

**Emergency path, faster (no image build):** Actions → Deploy → the previous image tag with
**`run_migrations: true`**. Follow with the revert commit so `dev` matches what runs.

**Do not use "previous tag, migrations off"** (the workflow's printed advice, `deploy.yml:420-433`)
for this push. With migrate off the Scheduled Job Type stays, and at 06:30 every day the scheduler
calls a function that no longer exists.

What happens to each piece — read in Frappe 16.33.1:

| Piece | After revert **with** migrate | Evidence |
|---|---|---|
| The 06:30 job | Deleted | `sync_jobs` → `clear_events` removes jobs no longer in hooks (`core/doctype/scheduled_job_type/scheduled_job_type.py:296-312`) |
| The two doctypes | The DocType records are deleted as orphans; **the tables are not dropped**. Data review items, confirmations and the settings value stay in the database. Re-applying push 1 later brings them back with their data | `model/sync.py:165-198` ("Deleting the entry doesn't delete any data"); `migrate.py:188-189`; `model/delete_doc.py` has no `DROP TABLE` |
| `Version` rows for confirmations and settings | Stay | Not touched by orphan clean-up |
| The eight indexes | Stay. Harmless | Nothing removes them |
| The six Property Setters | Stay, so Frappe keeps protecting the six indexes. Harmless. **Do not delete them in a rollback** — that would drop the indexes on the next re-sync | Section A |
| A job already queued at revert time | Fails once on import; one Error Log row | — |
| Cache | Nothing to clear — push 1 adds no cache (engineer 6.11) | — |
| HR figures | Back to the old formula and tenant-wide scope. **Tell HR again** | — |
| Database restore | **Not needed** for push 1 — no existing record is changed (AC-161). Only if the migrate itself breaks a site. A restore loses any confirmation made after the deploy | — |

**Time:** the emergency path is one deploy run. A revert commit adds an image build. I have not
measured either, so I cannot say whether they meet the 15-minute rollback in `nfr-budget.md` §3.

---

## G · Where I agree and disagree with the engineer

### Agree

| Engineer's point | Note |
|---|---|
| D-14 index method: Property Setter + `add_index` | **I was wrong in §3.** Section A |
| D-15 push 1 after group D | Section D; now 16 commits, not 14 |
| No image, Compose or nginx change | Confirmed, section B |
| Cron entry only enqueues onto `long`, 900 s, `job_id`, dedupe; commit per company | Matches OPS-48 |
| One leave-year query per company | Grows with companies (1–2), not people or branches. The query-count test should run with 1 and 2 companies, as well as 10/100 people and 2/8 branches |
| D-1 settings doctype in push 1; "last run" stamp with `set_single_value` | No Version row per run, which keeps AC-18 true |
| Error Log with a fixed title and the error type, never the traceback | Matches OPS-50, OPS-57 |
| Per-user limit in Frappe's cache | Matches OPS-40. Give each key an expiry (one hour); Redis has no memory ceiling (§3, OPS-47) |
| No cache in push 1 | Nothing to clear on deploy or rollback |
| Tables and indexes stay on rollback | True, **with migrate on** — see below |

### Disagree or add

| # | Engineer wrote | My view |
|---|---|---|
| 1 | Risk: indexes dropped "on a later upgrade" | **Wider:** any Custom Field save on Employee or Employee Checkin drops them, at any time, and nothing rebuilds them until the next deploy (section A) |
| 2 | Property Setter written each run ("safe to run twice") | Safe, but it deletes and re-inserts each migrate. Check it exists first; keep `is_system_generated` True so "Reset to defaults" does not remove it |
| 3 | "The cron entry disappears on migrate" (6.13) | Only if the rollback deploy runs migrate. The workflow's printed rollback turns migrate off. Say "migrate on" in the rollback plan |
| 4 | New items appear at 06:30 (D-5); HR told before release | HR figures then change twice. Enqueue the check once at the end of `after_migrate` (OPS-72) |
| 5 | AC-11 pin test in `hrms/alvoraa_hr_core/tests` | CI does not run HRMS tests. Put it where CI runs it (OPS-74) |
| 6 | "The `ignore_permissions` counter must not rise" | The counter only reads listed files. Add the two new files at 0 (OPS-75) |
| 7 | `after_migrate` line "at the end" | Agree, and make the reason explicit: it must follow `branch_scope.after_migrate` |
| 8 | Page changes in `hrms-employee.html` | Record the size added; the page is already 977 KB per visit (OPS-82) |
| 9 | Rollback: `git revert`, deploy | Add: reverting reopens G1–G3; prefer fixing forward; G2 and G3 can stay (section F) |

---

## Recommendations (continues from OPS-69)

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-70 | **Recommend:** replace OPS-52's method. For the six one-column indexes (Employee `company`, `branch`, `department`, `date_of_joining`, `relieving_date`; Employee Checkin `time`), create a Property Setter `search_index = 1` **only if missing**, with `is_system_generated` left True, then `frappe.db.add_index`. For the two two-column indexes, `add_index` only. OPS-52's tests stay. | Section A: Frappe drops unflagged one-column indexes on any re-sync, and `add_index` does not flag them during migrate or install. | Six indexes vanish after an ERPNext update or a desk Custom Field; queries slow down silently; each later deploy rebuilds them under a table lock. | Recommend | |
| OPS-71 | **Recommend:** a CI test that the indexes **survive a re-sync**: after install, call `frappe.db.updatedb("Employee")` and `frappe.db.updatedb("Employee Checkin")`, then assert all eight indexes and six Property Setters exist. Also run the hook once with `frappe.flags.in_migrate = True` and assert the same. | CI builds with `install-app` and never re-syncs, so section A's failure would pass today. It also catches a future Frappe change to these rules. | The method can break unnoticed after a Frappe update on the moving `version-16` branch. | Recommend | |
| OPS-72 | **Recommend:** list `data_review.after_migrate` after `branch_scope.after_migrate` in both hook lists; inside it, add indexes first and, last, enqueue the morning check once (same `job_id`, `deduplicate`, `long`). Not in `after_install`. The engineer confirms the cost. | The two-column indexes need `alvoraa_branch`. Running the check at deploy makes HR's figure change once instead of twice. | A tenant without slice 011's column fails migrate; HR sees 65.8% on deploy day and 97.0% the next morning and loses trust. | Recommend | |
| OPS-73 | **Recommend:** choose the deploy time for push 1, on `dev` and later `main`: not between 06:15 and 07:30 site time, and not while a long job on Attendance or Employee Checkin is running. | Maintenance stops the scheduler but not running jobs; migrate waits up to 5 minutes for a table lock, then fails (`migrate.py:220-227`). | A failed migrate half-way through `--site all`. | Recommend | |
| OPS-74 | **Recommend:** make the AC-11 pin test run in CI — either in `alvoraa_portal/tests`, or by adding a `run-tests --module` line for it in `ci.yml`. | `ci.yml:281-282` runs only `alvoraa_goals` and `alvoraa_portal`. | The one test that proves appraisal scores do not move never runs where it counts. | Recommend | |
| OPS-75 | **Recommend:** add `alvoraa_portal/org_figures.py` and `alvoraa_portal/data_review.py` to the `ignore_permissions` `CEILINGS` table at 0, and lower `hr_api.py`'s ceiling if G1 removes a use. | The counter only checks listed files (`test_portal_security_010.py:708-716`). | AC-45 and SEC-8 pass while new files add `ignore_permissions`. | Recommend | |
| OPS-76 | **Consider:** a test that the path passed to `frappe.enqueue` resolves (`frappe.get_attr`), or pass the function itself instead of a string. | The integrity script checks `hooks.py` only. | A typo shows up as a job failure at 06:30 on dev, not in CI. | Consider | |
| OPS-77 | **Recommend:** record `bench version` for the image tested on dev in `03`, and in §5 compare it with the image going to `main`. | Frappe and ERPNext follow the moving `version-16` branch (`Dockerfile:25-26`, `ci.yml:163-164`), and push 1 relies on Frappe details. | `main` runs a Frappe nobody tested this push on. | Recommend | |
| OPS-78 | **Recommend:** order of pushes: group D to `dev` → its CI green → its deploy finished and checked on dev → 012 rebases onto `origin/dev` and reruns the full suite → push 1 to `dev`, on your word. Same order, as separate releases, to `main`. | Local `dev` holds 16 unpushed group D commits; CI cancels overlapping runs (`ci.yml:16-18`); separate migrates keep failures and rollbacks separate. | Group D's unfinished work ships with push 1, or both land in one migrate that is hard to diagnose or roll back. | Recommend | |
| OPS-79 | **Recommend:** send the four-point HR note in section E before the push reaches each tenant: before the dev push for dev tenants used by real people; at least two working days before `main` for production. You name the sender (BA-Q14). | Step 0 has no switch. | HR sees different numbers, less scope or a "not linked" message with no warning. | Recommend | |
| OPS-80 | **Recommend:** treat dev testing as enough before `main` only when: one 06:30 run is seen succeeding on dev; HR Manager, store HR and not-linked HR are checked; the index migrate is timed on the rehearsal copy; and production still has no live customer. If one is live, **ask**: a rehearsal on a production dump needs production access. | Section E. | A job or scope fault reaches production that dev would have shown the next morning. | Recommend | |
| OPS-81 | **Recommend:** rollback plan for §5: fix forward by default; a full revert only with migrate **on**; emergency path is the previous image tag with `run_migrations: true`; never "migrations off" for this push; never delete the Property Setters or indexes as part of a rollback. | Section F. Reverting reopens G1–G3; with migrate off the 06:30 job calls missing code every day. | Leaks reopened without a decision; a daily failing job; indexes dropped by a clean-up. | Recommend | |
| OPS-82 | **Recommend:** record in `03` how many KB push 1 adds to `hrms-employee.html`, and aim for **20 KB or less** before compression (estimate, same spirit as OPS-24). | The page is 977 KB and downloaded on every visit (§2a). | Every employee's daily load grows for a panel only HR uses. | Recommend | |
| OPS-83 | **FYI:** for a few seconds between `up -d` and maintenance on, the new code runs against the old schema; HR Analytics may fail for anyone opening it in that window. No action. | Workflow order, `deploy.yml:259-289`. | — | FYI | |

## What I did and did not check

- **Did:** read the engineer's strategy, the spec's push 1 stories and decisions, the work board, CI
  and deploy workflows, Dockerfile, Compose files, `REHEARSAL.md`, the runbook's migrate notes, the
  integrity script, `alvoraa_portal/hooks.py` and the `ignore_permissions` counter test. Read Frappe
  16.33.1 inside `hrlocal-bench`: `database/schema.py`, `database/mariadb/schema.py`,
  `database/mariadb/database.py`, `migrate.py`, `installer.py`, `model/sync.py`,
  `model/delete_doc.py`, `custom_field.py`, `customize_form.py`, `property_setter.py`,
  `scheduled_job_type.py`, and grepped `utils/scheduler.py` and `utils/background_jobs.py` for
  maintenance mode. Ran one read-only `SELECT` on `ppj.localhost`: no `search_index` Property Setters
  on Employee, Employee Checkin or Attendance; 24 Custom Fields on Employee. Counted
  `origin/dev..dev` with `git`.
- **Did not:** run a migrate, `updatedb`, test or job; prove the index drop by running it (source
  reading only — OPS-71 turns it into a test); check dev or production row counts, sites or indexes;
  check whether `health.collect_scheduled` reports the job's errors; measure rollback time; check
  whether an image build for a revert fits the 15-minute rollback budget. Every time above is an
  **estimate** unless marked measured or read.

---

# §5 · 16 September 2026 — Release readiness (push 1)

Inputs read: `00-impact-analysis.md` (strategy approval, D-1 to D-15), `03-implementation-notes.md`
(including fix round 1 and its measured p95s), `04-test-report.md` (both runs), `02-functional-spec.md`
(push 1 stories, AC-3, AC-5, AC-30, AC-31, AC-40, AC-161), §1–§4 above, `.claude/work-in-progress.md`,
`.github/workflows/deploy.yml` and `ci.yml`, `REHEARSAL.md`, `DEPLOYMENT_RUNBOOK.md`,
`alvoraa_portal/data_review.py` (the index installer).

**I ran nothing. No bench command, no deploy, no push, nothing on dev or production.** Every command
below is written **for you to approve**. Times are estimates unless the source says measured.

## Read this first

1. **A dev deploy takes no backup.** `deploy.yml:141` skips the backup step when the environment is
   `dev` (`if: needs.plan.outputs.environment != 'dev'`). Push 1 runs a migrate that builds nine
   indexes and creates two doctypes on **every site in the dev stack**. If you want a rollback point
   on dev, someone has to take it by hand first (OPS-84).
2. **One push at a time, and slice 010 group D goes first** (D-15, OPS-78). Local `dev` holds group D
   and push 1 together. Pushing `dev` pushes both. Two pushes close together make CI cancel the first
   one's deploy and both land in one migrate (`ci.yml:16-18`).
3. **The index-migrate time (AC-5) is still unmeasured.** Section B says how to measure it on a copy.
   On a ~200,000-row Attendance table the estimate in §3 E is a few seconds per index; it is an
   estimate, not a measurement.
4. **DEF-8 is still open** (test report R1): store HR still see no-branch colleagues, with leave
   types, in Attendance Insights' organisation list. It is not caused by push 1, but after fix round 1
   two screens apply two different rules. **Your call before the push: fix it in push 1, or record it
   as accepted** (OPS-94).
5. **A dev deploy restarts the one nginx that also serves production** (`deploy.yml:326`, about two
   seconds by the workflow's own comment). Nothing about push 1 makes that worse, but it is a
   production blip caused by a dev push. Pick a quiet moment (OPS-97).

---

## A · Rollout, local → dev → main

Every command is **for you to approve**. Nothing here is run by an agent on its own.

### Stage 1 — finish on the local bench (before any push)

| # | Step | Command (for you to approve) | What it does | Rough time |
|---|---|---|---|---|
| 1.1 | See what is on top of `origin/dev` | `git -C C:/Surbhi-Git/hr-app fetch origin dev` then `git -C C:/Surbhi-Git/hr-app log --oneline origin/dev..dev` | Read-only. Shows exactly what a push would send. Read the incoming diff before you push (CLAUDE.md §1) | seconds |
| 1.2 | Browser check on a migrated local site (still missing, test report R6) | `docker exec hrlocal-bench bash -lc "cd /home/frappe/frappe-bench && bench --site ppj.localhost migrate" 2>&1` — and if you switch sites with `bench use`, `docker restart hrlocal-bench` afterwards | Creates the two doctypes and the nine indexes on the demo copy so the page can be opened in a browser. **Changes a local site** | migrate 2–10 min (estimate) |
| 1.3 | Whole-suite proof already exists | none | Test report R-1/R-2: 1,065 `alvoraa_portal` tests and 18 `alvoraa_goals` tests at local `dev` 5aad1ae, only the 14 known local failures | — |
| 1.4 | Re-run the suite **after** the DEF-8 fix lands | `docker exec hrlocal-bench bash -lc "cd /home/frappe/frappe-bench && bench --site test_site run-tests --app alvoraa_portal" 2>&1` | The current green run does not include that commit | ~38–45 min (measured by the test engineer) |
| 1.5 | Record the version the push was proven on (OPS-77) | `docker exec hrlocal-bench bash -lc "cd /home/frappe/frappe-bench && bench version" 2>&1` | Frappe / ERPNext / HRMS versions, for the comparison before `main`. Capture both streams — `bench` hides the real error otherwise (lesson 8) | seconds |

### Stage 2 — push 1 to `dev`

| # | Step | Command (for you to approve) | What it does | Rough time |
|---|---|---|---|---|
| 2.1 | Group D is already on `origin/dev`, its deploy finished and checked | — | D-15 / OPS-78. See section C | — |
| 2.2 | Rebase push 1 on what is really on the remote | `git -C C:/Surbhi-Git/hr-app fetch origin dev`, then in the worktree `git rebase origin/dev` | Keeps history linear and shows anyone else's work that came in | minutes |
| 2.3 | Optional dev rollback point (OPS-84) | `docker exec devstack-backend-1 bash -lc "cd /home/frappe/frappe-bench && bench --site all backup --with-files" 2>&1` | The dev deploy will **not** do this for you. A server command — yours to run, or to tell an agent to run | 2–15 min (estimate) |
| 2.4 | Send the HR note (OPS-79, OPS-90) | — | Section D. Before the push, to anyone using a dev tenant for real work | — |
| 2.5 | **The push** | `git -C C:/Surbhi-Git/hr-app push origin dev` | This *is* the deploy. CI runs, then Build Image, then Deploy to dev, all automatically (`deploy.yml` `workflow_run`) | push: seconds |
| 2.6 | CI | automatic | `ci.yml`: app integrity, API paths, portal handlers, design system, then the `alvoraa_goals` and `alvoraa_portal` suites | tens of minutes (not measured) |
| 2.7 | Build Image | automatic | Builds and pushes `ghcr.io/<repo>/hr-app:dev-<sha>` | tens of minutes (not measured) |
| 2.8 | Deploy to dev | automatic | Bare `docker compose … up -d --remove-orphans` (never a service list — lesson 1), maintenance on per site, `premigrate_rename`, `bench --site all migrate`, `clear-cache`, maintenance off, restart `compose-nginx-1`, smoke test `/api/method/ping` | the image pull alone can retry for 5 min; the job's own limit is 90 min |
| 2.9 | Post-deploy checks | section E | Read-only. An agent may run the dev ones when you ask | 15–30 min, plus the next morning |

**There is no separate `bench migrate` for you to run.** The deploy runs it inside the workflow.
Running one by hand as well would only repeat the work.

### Stage 3 — to `main` (a separate release, later, on your word)

| # | Step | Command (for you to approve) | What it does |
|---|---|---|---|
| 3.1 | Everything in section H is done | — | The before-`main` list |
| 3.2 | Group D's own release to `main` has already happened | — | Same order as dev (OPS-78) |
| 3.3 | Compare versions (OPS-95) | read `bench version` on the dev stack, and on the image built for `main` | Frappe and ERPNext follow the moving `version-16` branch, so `main` can carry a newer Frappe than dev tested |
| 3.4 | HR note to production tenants, **at least two working days earlier** | — | Section D |
| 3.5 | The merge and push | `git -C C:/Surbhi-Git/hr-app fetch origin` · `git checkout main` · `git merge --ff-only origin/dev` · `git push origin main` | **`main` is production.** Only on your explicit word (CLAUDE.md §1, §3) |
| 3.6 | Production deploy | automatic after Build Image, **held at the `production` GitHub Environment approval** | It takes a full backup with files first (`deploy.yml:141-167`), then the same migrate sequence across four sites on one database |
| 3.7 | Pick the time (OPS-73) | — | Not between 06:15 and 07:30 site time, and not while a long job is running on Attendance or Employee Checkin |

---

## B · Migration dry run on a copy — and how to time the indexes (AC-5)

**Nothing here touches real data in place.** It restores a **copy** of a dev dump into a throwaway
stack, as `REHEARSAL.md` sets out. Two things must be right, or it is not safe:

- `COMPOSE_PROJECT_NAME=rehearsal` on **every** command, so the rehearsal gets its own `sites` volume.
- The site name `rehearsal.alvoraa.co`, which no live site uses.

| # | Step | Command (for you to approve) | Why |
|---|---|---|---|
| B1 | Take a dump of a dev site | `docker exec devstack-backend-1 bash -lc "cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co backup" 2>&1` | Read-only on the live stack |
| B2 | Start the rehearsal stack | `REHEARSAL.md` §4, with `KINEXUS_IMAGE` set to push 1's `dev-<sha>` tag | Only `configurator` and `backend`. No workers, so nothing emails or runs jobs against copied data |
| B3 | Prove the isolation | `docker volume ls` filtered for `rehearsal` | Expect a separate `rehearsal_sites` volume. If you see the live one, stop |
| B4 | Create the site and restore the dump | `REHEARSAL.md` §5 | The copy now holds real-shaped data |
| B5 | **Record the sizes before the migrate** | in `bench --site rehearsal.alvoraa.co console`: a `select count(*)` on `tabAttendance`, on `tabEmployee Checkin` and on `tabEmployee` | An index time means nothing without the row count beside it |
| B6 | **Time each index on its own — this is the AC-5 measurement** | in the same console, **before** the migrate: `import time`, then for each of the nine, `t=time.perf_counter(); frappe.db.add_index(<doctype>, [<fields>]); print(<name>, round(time.perf_counter()-t, 2))` | `add_index` is the exact call the migrate makes, and it does nothing when the index already exists. One at a time is the only way to get a time **per table** |
| B7 | Then run the real thing | `bench --site rehearsal.alvoraa.co migrate` with the output saved to a file | Watch for `Orphaned DocType(s) found:` — `Mode of Payment` is expected, any of ours is a stop. The indexes already exist from B6, so this shows the rest of the cost: doctype sync, `sync_jobs`, customisations |
| B8 | Check the two doctypes (AC-161) | `frappe.db.exists("DocType", "Alvoraa Data Review Item")`, `frappe.db.count("Alvoraa Data Review Item")` | Expect `True` and `0` |
| B9 | **Rehearse the post-migrate morning run (OPS-72)** | `bench --site rehearsal.alvoraa.co execute alvoraa_portal.data_review.run_morning_checks`, with **stdout and stderr both saved** | The rehearsal has **no worker**, so the queued job never runs there. Running the method directly is the only way to see it. `bench execute` prints its own fallback and hides the real error (lesson 8) |
| B10 | Time it, and read what it found | `time` on B9, then `frappe.db.count("Alvoraa Data Review Item", {"status": "Open"})` and one read of the kinds found | Gives the real first-run cost and — more useful — **how many "Needs review" items real data produces on day one**. Local measurement: 675 ms for one company at 1,000 people |
| B11 | Run it twice (AC-18) | B9 again | Expect zero changed records and zero new `Version` rows |
| B12 | Tear the stack down | `COMPOSE_PROJECT_NAME=rehearsal docker compose … down -v` | Removes the copy and its volume. **Copied HR data must not sit around** (`nfr-budget.md` §5) |

**Where it runs.** `REHEARSAL.md` puts this on the server host beside the live stacks. That is a
server action and your decision. Restoring a dev dump onto a laptop instead would put real-shaped HR
data on a personal machine; I do not recommend it.

**Write the numbers from B5, B6, B7 and B10 into `03-implementation-notes.md`.** That closes AC-5 and
OPS-53.

---

## C · Order with slice 010 group D

One push, one CI run, one deploy, checked — then the next. Never two in flight.

| # | What | Check before moving on |
|---|---|---|
| C1 | Group D goes to `origin/dev`, on your word | Afterwards `git log --oneline origin/dev..dev` shows **only** push 1's commits |
| C2 | Group D's CI is green and its deploy finished | Actions: CI success, Build Image success, Deploy success, smoke test "ping OK" |
| C3 | Group D is checked on dev | Its migrate adds HR Settings fields, review doctypes and patches. A failure there must not be mixed into push 1's migrate |
| C4 | 012 rebases onto `origin/dev` and re-runs the whole suite | Only the known local failures |
| C5 | Push 1 goes to `dev`, on your word | Section A, stage 2 |

**Why it matters:** CI cancels a running check when a newer push lands on the same branch
(`ci.yml:16-18`), so two pushes close together mean the first deploy never runs and both migrations
land at once. That is the 10 September pattern CLAUDE.md §1 already records.

---

## D · What changes for users the moment push 1 lands

**There is no switch.** HR sees the change as soon as the deploy finishes (§3 J, OPS-68).

| What changes | Who notices | Size of the change |
|---|---|---|
| HR Analytics attendance % uses the shared calculation, counts work-from-home days and leaves out doubtful days | every HR user | On the demo tenant: **65.8% → about 97.0%** once the checks have run. Other tenants will differ |
| The figure changes **once, minutes after the deploy**, not twice | every HR user | Because the check is queued at the end of `after_migrate` (OPS-72). If that enqueue fails, it is logged and the figure moves at 06:30 the next morning instead |
| HR Analytics is scoped | store HR see their branch only; single-company HR see their company only | Store HR **lose** visibility they had. This closes the leak found in §1 |
| "Not linked to a company" | an HR login with no company link | They see a message instead of figures |
| Leave used counts this leave year only | every HR user | The old figure divided by every allocation ever made |
| A new menu item **Data to review**, with a badge counting open items | HR only | A new page, and one extra permission-checked read per HR portal page load |
| "Needs review" wording | HR only in push 1 | Leaders see it in push 2 |
| The portal page grows about 19.5 KB before compression | every employee's page load | `hrms-employee.html` is already 977 KB per visit (§2a) |

**Who to tell, and when** (OPS-79, OPS-90 — you name the sender, BA-Q14):

- **Dev:** before the dev push, to anyone using a dev tenant for real work.
- **Production:** at least **two working days** before the `main` release.
- **There are no live customers today** (memory note, 14 September 2026 — please confirm at release
  time). So the production note is for your own team and the demo tenants. If a customer is live by
  then, the note is not optional, and a rehearsal on a production dump becomes worth discussing —
  that needs production access, so it is your decision, not mine.

The four plain sentences to send are already written in §4 E.

---

## E · Post-deploy checks on dev, in order

Read-only. An agent may run the dev ones **when you ask**. "Good" is the right-hand column.

| # | Check | How | Good looks like |
|---|---|---|---|
| E1 | The workflow itself | GitHub Actions: CI → Build Image → Deploy to dev | All green; the Smoke test step prints `ping OK` |
| E2 | The migrate log | the Deploy job's output, the `bench --site all migrate` step | No traceback. No `Orphaned DocType(s) found:` naming one of ours (`Mode of Payment` is expected). Every site reaches the end |
| E3 | **Same image everywhere** (lesson 2) | `docker ps --filter name=devstack --format "{{.Names}} {{.Image}}"` | One tag, `dev-<sha>`, on **every** container — backend, scheduler, `worker-long`, `worker-short`, `worker-default`. `worker-long` runs the morning job; an old image there is the failure this slice is most exposed to |
| E4 | One scheduler, and it is enabled | `docker exec devstack-backend-1 bash -lc "cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co doctor" 2>&1` (the workflow also runs this in "Stack and scheduler health") | Scheduler enabled and running; exactly one scheduler container in E3's list |
| E5 | **The nine indexes really exist** | in `bench --site dev.alvoraa.co console`: `show index from` each of `tabEmployee`, `tabEmployee Checkin`, `tabAttendance` | Employee: `company_index`, `branch_index`, `department_index`, `date_of_joining_index`, `relieving_date_index` · Employee Checkin: `time_index`, `alvoraa_branch_time_index` · Attendance: `alvoraa_branch_attendance_date_index`, `company_attendance_date_index` |
| E6 | The six markers that keep them | `frappe.get_all("Property Setter", filters={"property": "search_index"}, fields=["doc_type", "field_name"])` | Six rows: the five Employee fields and Employee Checkin `time`. Without these, Frappe drops those indexes the next time anyone saves a Custom Field (§4 A) |
| E7 | The two doctypes exist and start empty (AC-161) | `frappe.db.count("Alvoraa Data Review Item")` | `0` before the first check runs; items appear after it |
| E8 | The 06:30 job is registered | `frappe.get_all("Scheduled Job Type", filters={"method": ["like", "%data_review%"]}, fields=["name", "stopped", "cron_format"])` | One row, `stopped = 0`, cron `30 6 * * *` |
| E9 | The post-migrate run happened (OPS-72) | the "last successful run" stamp on `Alvoraa Leader View Settings`; and `frappe.get_all("Error Log", filters={"error": ["like", "%Leader data checks failed%"]})` | A stamp from **today, minutes after the deploy**; no error rows. If the stamp is missing, the figures move at 06:30 instead — not broken, but tell HR (OPS-89) |
| E10 | If you do not want to wait: one run by hand | `docker exec devstack-backend-1 bash -lc "cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co execute alvoraa_portal.data_review.run_morning_checks" 2>&1` | Finishes, writes a stamp, no traceback. Capture both streams (lesson 8). This proves the **code**, not the cron — E11 proves the cron |
| E11 | **One real 06:30 run** (AC-40, OPS-80) | the next morning: the stamp is that morning, and there is no "Leader data checks failed" row | The only proof that the scheduler, the cron entry and `worker-long` work together. Do not skip it before `main` |
| E12 | HR Analytics for a scoped HR user | in a browser on dev, as an HR Manager linked to a company | The page loads, figures appear, the attendance % has moved as expected, no error |
| E13 | The "not linked" case | as an HR login with no company link | The "not linked to a company" message — not figures, and not an error |
| E14 | The Data to review page | as the same HR Manager | The list, the cards, "Last checked <time>", and a confirm action that clears an item |
| E15 | The badge | open any portal page as HR | The menu badge shows the number of open items **from the first paint** (the DEF-3 fix) |
| E16 | **Store HR sees only their branch** | as a store HR user with a Branch permission | HR Analytics counts their branch only; Data to review shows their branch's items only, and no company-wide ones. **Also open Attendance Insights' organisation list** — if DEF-8 is still open, no-branch colleagues appear there. That is the known gap, not a new one |
| E17 | Endpoint hygiene | the browser's network tab on the Data to review call | POST, `Cache-Control: no-store`, and no names or figures in the address |
| E18 | Speed | the same network tab, or the slow-call log | Under 500 ms warm for HR Analytics and Data to review at dev's size. Local measurement at 1,000 people: 283 ms and 243 ms warm |
| E19 | Production is untouched | `curl -s -o /dev/null -w "%{http_code}" https://alvoraa.co/` — **for you to run, not an agent** | `200`. The dev deploy restarts the shared nginx, so this is worth one look |

---

## F · Rollback

**Fix forward is the default (OPS-81).** Reverting push 1 reopens the three holes it closed: store HR
seeing every store's names and figures (G1, G3), and any HR user writing any org setting (G2). A
small fault is better fixed with a new commit than by putting those back.

| Situation | What to do | Notes |
|---|---|---|
| Something looks wrong, nobody is blocked | **Fix forward.** New commit, local test, push on your word | The normal case |
| A figure is wrong and you want the old HR Analytics back | `git revert` the calculation commit (commit 6) and push to `dev` on your word. G2 (commit 2) and G3 (commit 3) can stay — they do not depend on it | This reopens G1 only |
| The deploy failed, or dev is down | Actions → Deploy → Run workflow → environment `dev`, the **previous** image tag, **`run_migrations: true`** | About one deploy run. Follow it with a revert commit so the branch matches what runs |
| — | **Never use `run_migrations: false` for this push** | With migrate off, the Scheduled Job Type stays and calls code that is no longer there, every morning at 06:30 |
| A site's migrate broke that site | Restore that site from the pre-deploy backup | On dev there **is no automatic pre-deploy backup** (OPS-84). On production there is |

**What survives a rollback, and must not be tidied up by hand:**

| Piece | After a revert with migrate on |
|---|---|
| The nine indexes | Stay. Harmless. **Leave them** |
| The six Property Setters | Stay. **Do not delete them** — deleting them drops six indexes at the next re-sync |
| The two doctypes | The DocType records are removed as orphans; **the tables and their rows stay**. Re-applying push 1 brings the data back |
| HR confirmations and their `Version` history | Stay. They are the evidence of who declared an absence real |
| The 06:30 job | Deleted by `sync_jobs` — but only if migrate ran |
| Existing Attendance, Leave and Employee records | Never changed by push 1 (AC-161), so a database restore is **not** part of a rollback. Only if a migrate itself broke a site |
| HR's numbers | Back to the old formula and tenant-wide scope. **Tell HR again** |

**Time:** the previous-tag path is one deploy run; a revert commit adds an image build. Neither is
measured, so I cannot say whether either fits the 15-minute rollback in `nfr-budget.md` §3.

---

## G · Monitoring for the first week

| # | Watch | Where | Normal | Wrong |
|---|---|---|---|---|
| G1 | The morning job ran | the "last successful run" stamp on `Alvoraa Leader View Settings` | A stamp from this morning, every morning | Older than 26 hours — the page itself then shows an amber line |
| G2 | Job failures | Error Log, title "Leader data checks failed" | No rows | Any row. It carries the company, the stage and the error type only, by design |
| G3 | Slow calls | the `leader_view` logger — one line per call over 1 second, with no names or figures | A handful a day at most | More than 10 in an hour |
| G4 | `worker-long` alive and on the right image | `docker ps --filter name=devstack` | One `worker-long`, same tag as the rest | Missing, restarting, or an older tag |
| G5 | Queue backlog | the length of the `long` queue | Near zero | Growing — the morning job would then be late or never run |
| G6 | Disk | `df -h /` on the host (the deploy prints it) | The indexes add roughly tens of MB per large table (**estimate**, §3 E) | A jump much larger than that |
| G7 | What HR says | your own inbox | Questions about the changed attendance % | Anyone saying a number "looks wrong" — check first whether it is a doubtful day left out, not a bug |
| G8 | Nothing leaked | one spot check as store HR during the week | Their branch only | Anything else — tell the security engineer at once |

**Three alerts.** `nfr-budget.md` §8 requires a **named owner** for each. The owner is yours to name
(OPS-92); I cannot pick a person.

| Alert | Fires when | Owner |
|---|---|---|
| Leader data checks failed | an Error Log row with that title appears | *(to confirm)* |
| Checks have not run | the last successful run is older than 26 hours | *(to confirm)* |
| Leader view slow | more than 10 slow-call lines in an hour | *(to confirm)* |

**Capacity, plainly.** No new service, no new spend. One extra job a day (675 ms for one company at
1,000 people, measured locally). One extra permission-checked read per HR portal page load for the
badge. Nine indexes cost some disk and make writes very slightly slower; both are small next to what
the reads save. The eight web request slots per stack are unchanged.

---

## H · Before `main` — separate from `dev`

| # | Item | Why | Source |
|---|---|---|---|
| H1 | **The 2,000-employee run**, on separate synthetic sites (400 / 1,000 / 2,000), 30 cold and 30 warm calls per scope, with `EXPLAIN` | 1,000 people is measured and inside budget; 2,000 is the design ceiling and has never been run. The spread between runs on this laptop is large, which is exactly why separate sites matter | AC-3, OPS-64 |
| H2 | **Index-migrate timing on a copy** | Still unmeasured. Section B | AC-5, OPS-53 |
| H3 | **Browser checks**: 360 px, 200% zoom, keyboard through the confirm dialog, the screen reader on the alert dialog, the desk links from the cards | Never done in a browser; the page was traced by reading the code | test report R6 |
| H4 | **One real 06:30 run seen on dev**, with no failure row | The only proof that the cron, the scheduler and `worker-long` work together | AC-40, OPS-80 |
| H5 | HR Manager, store HR and not-linked HR all checked on dev | The three personas whose view changes | OPS-80 |
| H6 | `bench version` compared: the dev image against the image built for `main` | Frappe and ERPNext follow the moving `version-16` branch, and push 1 leans on Frappe's index, orphan and job behaviour | OPS-77, OPS-95 |
| H7 | DEF-8 decided: fixed, or accepted in writing | Two screens apply two different rules to the same people today | test report R1 |
| H8 | Two people confirming the same item at the same second, checked once by hand on dev | Proven only by the row lock in the code | test report R6, OPS-65 |
| H9 | The HR note sent, at least two working days ahead | Step 0 has no switch | OPS-79 |
| H10 | Confirm production still has no live customer | If one is live, a rehearsal on a production dump is worth discussing — that needs production access and is your decision | OPS-80 |
| H11 | Deploy time chosen: not 06:15–07:30 site time, and no long job running on Attendance or Employee Checkin | Migrate waits at most 5 minutes for a table lock, then fails. Production has four sites on one database, so the times add up | OPS-73, OPS-54 |

---

## Recommendations (continues from OPS-83)

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-84 | **Recommend:** take a backup by hand before push 1's dev deploy — `bench --site all backup --with-files` on `devstack-backend-1` — or record in writing that dev needs no rollback point. | `deploy.yml:141` skips the backup step for dev. Push 1 is a schema change on every dev site. | If a migrate breaks a dev site there is nothing to restore, and dev tenants are used for demos. | Recommend | |
| OPS-85 | **Recommend:** before the push, run `git log --oneline origin/dev..dev` and read the incoming diff. Push only when it holds push 1's commits and nothing unexpected. | CLAUDE.md §1: a force-push once hid a block of obfuscated JavaScript in three config files. Several sessions share this checkout. | Someone else's unfinished work ships inside push 1's deploy. | Recommend | |
| OPS-86 | **Recommend:** do the rehearsal in section B before `main`, and write the row counts, the nine per-index times, the migrate time and the first-run item count into `03`. Tear the copy down with `down -v` afterwards. | AC-5 and OPS-53 are still unmeasured; §3 E's numbers are estimates. A copy of HR data must not linger. | A production migrate of unknown length on a 200,000-row table, and copied HR data left on disk. | Recommend | |
| OPS-87 | **Recommend:** run the section E checks in that order after the dev deploy, and record E3, E5, E6 and E9 in writing. | Lessons 1, 2 and 5, and §4 A's index-drop risk. The indexes and the markers cannot be seen from any screen. | A worker left on an old image, or six indexes that Frappe quietly drops later. | Recommend | |
| OPS-88 | **Recommend:** treat E10 (a run by hand) as a convenience only. The release is not proven until E11 — one real 06:30 run — has been seen on dev. | A manual run proves the code, not the cron entry, the scheduler or `worker-long`. Lesson 1: a job nobody listens to sits queued for ever. | The morning check never runs in production, and doubtful days go unwarned. | Recommend | |
| OPS-89 | **Recommend:** if the E9 stamp is missing after the deploy, tell HR that their attendance figure will move once more at 06:30 the next morning, and check the Error Log for the queue failure. | The enqueue is best-effort by design: a failure is logged and the migrate carries on. | HR sees the figure change twice with no warning — exactly what OPS-72 was for. | Recommend | |
| OPS-90 | **Recommend:** send the four-sentence HR note (§4 E) before the dev push for anyone using a dev tenant for real work, and at least two working days before `main`. You name the sender. | Step 0 has no switch; the numbers change without warning. | HR's first sight of a 30-point jump in attendance % is on their own screen. | Recommend | |
| OPS-91 | **Recommend:** the rollback in section F — fix forward by default; a full revert only with migrate **on**; the emergency path is the previous image tag with `run_migrations: true`; never "migrations off"; never delete the indexes or the six Property Setters. | Reverting reopens G1–G3; with migrate off the 06:30 job calls missing code every day; deleting a Property Setter drops an index at the next re-sync. | Holes reopened without a decision, a daily failing job, or silent slowness months later. | Recommend | |
| OPS-92 | **Recommend:** name an owner for each of the three alerts in section G before push 1 reaches `main`. **I cannot pick a person.** | `nfr-budget.md` §8 requires named owners. | Alerts fire into nobody's inbox, which is the same as having none. | Recommend | |
| OPS-93 | **Recommend:** watch section G's eight items for the first week on dev, and again for the first week after `main`. | The job, the queue and `worker-long` are this slice's new moving parts. | A silent stop, found when a leader asks why a number is wrong. | Recommend | |
| OPS-94 | **Recommend:** decide DEF-8 before the push — fix it in push 1, or record it as accepted with a date and a reason, and name it in the release note. | After fix round 1, two screens apply two different rules to the same people, and the organisation list shows more (names, leave types) than the screens that now refuse. | A privacy gap nobody owns, inside code the next push builds on. | Recommend | |
| OPS-95 | **Recommend:** record `bench version` for the image running on dev, and compare it with the image built for `main` before the production release. | Frappe and ERPNext follow the moving `version-16` branch (`Dockerfile:25-26`), and push 1 leans on Frappe's index, orphan and job behaviour. | `main` runs a Frappe that nobody tested this push against. | Recommend | |
| OPS-96 | **Consider:** a check in the deploy or in CI that every app container reports the same image tag, so lesson 2 is caught by a machine instead of by a person reading `docker ps`. | It has already cost this repo one incident, and this slice is the first to depend on `worker-long`. | The same failure again, found by a missing morning run. | Consider | |
| OPS-97 | **FYI:** a dev deploy restarts the one nginx that also serves production — about two seconds of blip (`deploy.yml:326` and its own comment). Pick a quiet moment for the push. | One nginx serves every environment and caches the backend address, so the restart is not optional. | A short production blip at a bad moment. | FYI | |

## What I did and did not check

- **Did:** read the impact analysis, the implementation notes (including fix round 1), both runs of
  the test report, the push 1 stories and their acceptance criteria, §1–§4 above, the work board,
  `deploy.yml`, `ci.yml`, `REHEARSAL.md`, `DEPLOYMENT_RUNBOOK.md` and
  `alvoraa_portal/data_review.py` (the index installer, to get the nine index names right). Read
  `git log` for the current head.
- **Did not:** run any bench, Docker or deploy command; push anything; open dev or production; read
  `deploy/server.env`; measure CI, build, deploy, migrate or rollback times; check which sites the
  dev stack currently holds; check whether `health.collect_scheduled` carries this job's errors to
  the control plane. **Every time in this section is an estimate** unless it says measured, and the
  measured ones come from the engineer's and the test engineer's local runs, not from a server.
