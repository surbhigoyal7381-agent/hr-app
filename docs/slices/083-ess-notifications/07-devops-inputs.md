# 083 ESS notifications — DevOps inputs

Slice: **083-ess-notifications** (ALV-322) · Advisory only. Every row below is a
recommendation with the **Decision column left blank for Surbhi**.

`07-devops-inputs.md` grows by dated sections, each dated and added without rewriting the
ones before it. §1 Brief (OPS-1 to OPS-12), §2 Design (OPS-13 to OPS-20) and §3 Requirements
(OPS-21 to OPS-30) were written on 6 November 2026 and are **unchanged**. **§4 Strategy
(OPS-31 to OPS-40) was added on 11 November 2026.** §5 Release readiness is still to come.

---

## §1 Brief — 6 November 2026

**Answer first: this slice is cheap to run, and nothing in it needs new infrastructure.**
No new container, no new volume, no new scheduled job, no new worker, no new dependency,
no `deploy/nginx.conf` change — **provided part 2 is a hash route inside the existing
`/hrms-employee` page and not a new web page.** If it becomes a new page, the cost jumps
and it touches the one nginx file that serves the live site. That is the single thing in
this slice I would stop and ask about (OPS-4).

Nothing here is a P0. Two P1 items: the route shape (OPS-4) and "the bell takes the counts
call, never the inbox call" (OPS-1).

### What I read, and what I did not

**Fact — files read today, in the worktree
`C:\Surbhi-Git\hr-app\.claude\worktrees\083-ess-notifications` at `814d540f`:**
`alvoraa_portal/alvoraa_portal/notices.py` (100 lines) · `inbox_api.py` (1,198 lines, all
seven `_part_*` builders) · `call_cache.py` · `attendance_correction.py`
(`review_queue_filters`, `_with_decide_flag`) · `auth.py` lines 480–560 · `home_api.py`
header · `public/js/ess/portal.js` (the bell block at 6,790–6,900 and the boot at 18,393) ·
`public/js/ess/next-frame.js` header · `templates/includes/ess/frame.html` (the bell
markup) · `public/css/ess/frame.css` (`.mob-header`, `.mob-notif`) ·
`www/hrms_employee.py` · `deploy/nginx.conf` (compression and route blocks) · `hooks.py`
`scheduler_events` · the query-budget tests `tests/test_inbox_parts_042.py`,
`tests/test_notices_076.py`, `tests/test_scale_flatness_044.py`, `tests/measure_076.py` ·
`.claude/context/nfr-budget.md`, `no-over-engineering.md`, `data-doors.md`,
`handoff-contract.md` · `docs/slices/042-redesign-wave2/07-devops-inputs.md` and
`034-redesign-wave1/00g-decision-register.md` for the recorded measurements.

**I measured nothing today.** I ran no bench command, touched no site, and did not go near
dev or production. Every number below is labelled **Fact** (I read it in a file),
**Measured** (someone else measured it, on a named date and site), or **Estimate**.

### 1 · What this adds to run

**The honest headline: parts 1 and 2 add no server work at all. Part 3 adds one extra
API call per page load, and that is the whole cost of the slice.**

#### Part 1 — the desktop bell: zero new run cost

**Fact.** `ntBellBoot()` already runs on **every** portal page outside Home, desktop
included — `portal.js` line 18393 schedules it 1.5 s after load, with no device test. It
calls `notices.notices_feed(see_all=0)` and paints `#notif-badge`.

**Fact.** The bell's markup already exists on desktop. `templates/includes/ess/frame.html`
line 135 draws `#mob-notif-btn` inside `<header class="mob-header">`, and `frame.css` line
231 sets `.mob-header{display:none}` — panels.css turns it on below 768 px. So on a desktop
the call is already made and the answer already arrives; only the element is hidden.

**Inference, resting on those two facts:** part 1 is markup and CSS — give the bell a home
in the desktop top bar or rail. **It costs nothing extra to run.** It is the cheapest of
the three parts by a wide margin.

#### Part 2 — the notifications page: zero new server work if filters are client-side

**Fact.** `notices_feed(see_all=1)` already returns the last 30 days, unread first, capped
at `READ_CAP = 100` rows (`notices.py` lines 42–44, 68–75). The existing "See all" sheet
(`ntOpenAll`, portal.js 6875) already calls it.

So a page that shows the same 100 rows with filters applied **in the browser** reuses an
endpoint that already exists and already has a query-count test. That is rung 1–4 of the
cost ladder with no new server rung at all.

**It stops being free the moment a filter has to reach the server** — "older than 30 days",
"by sender", or more than 100 rows. Then the window and the cap both change, pagination
appears, and the query-count test has to be re-measured. See the decision at OPS-5.

#### Part 3 — merging the feeds: this is where the cost is

**Fact — the two feeds do not meet today, except on Home.**

| Page | What the live portal calls today | Fact |
|---|---|---|
| Home | `inbox_api.get_inbox` (portal.js 6551) **and** `notices.notices_feed` (6814) | Both feeds already run on Home. Part 3 adds nothing there |
| Every other page | `notices.notices_feed` only, via `ntBellBoot` | The bell's number is notices only |

**Fact.** `inbox_api.get_nav_counts` — the counts-only call, 638 bytes — is **not wired
into the live portal at all.** A repo-wide grep found it only in
`public/js/ess/next-frame.js` (the frame of the discarded redesign, served by
`www/hrms-employee-next.html`) and in tests. So part 3 is not "turn on a call that is
already running"; on every non-Home page it is a genuinely new request.

**Measured — by slice 044, September 2026, on fixture sites `test044` (981 people, 4
companies) and `test044s` (20 people), five personas, 20 warm calls each. Recorded in
`docs/slices/042-redesign-wave2/07-devops-inputs.md` lines 133 and 169. I did not
re-measure.**

| Call | Statements | Payload | p95 |
|---|---|---|---|
| `get_nav_counts` | **21** worst case (store HR and company HR) | 638 B | the worst p95 across all measured calls was **215 ms**, against the ≤ 500 ms API budget (`nfr-budget.md` §2) |
| `get_inbox` | **26** | no byte figure recorded | same measurement run |
| `get_home` | **28** | | |
| `notices_feed` | **≤ 12**, asserted (`test_notices_076.py`, `test_the_query_count_does_not_grow_with_the_number_of_notices`) | small | not measured separately |

**Every one of those counts was identical at 20 people and at 981.** That flatness is the
property the project protects (`nfr-budget.md` §2: *"the gate is that the count is the SAME
for twenty people as for a thousand"*), and `tests/test_scale_flatness_044.py` is the gate
that holds it.

**So the estimate for a non-Home page load after part 3:**

| Shape | Statements per page load | What leaves the server |
|---|---|---|
| Today | ~12 | a number and up to 5 notice rows |
| Part 3 done with **`get_nav_counts`** | **~33** (12 + 21) | a number and 638 B of counts |
| Part 3 done with **`get_inbox`** | **~38** (12 + 26) | **colleague names, leave types, claim amounts and notes, on every page** |

**Recommend the first and refuse the second.** The bell needs a number; `get_inbox` returns
rows. Sending approval rows to a browser on every page is a privacy regression that buys
nothing — and it is exactly the shape Wave 1's biggest security finding had (`home_api.py`
header: a start-up call that shipped every caller's date of birth, phone and manager into
every screenshot). Rows belong in the sheet or page the person taps, which is where Home
already gets them.

#### What this costs at DTC

**Estimate. Based on:** ~600 employees of whom 441 are on shared factory handsets (memory
note, 25 Oct 2026), and the measured 21 statements / 215 ms p95 above. I have not counted
real page views — nobody has, and I could not check from here.

- Assume office and desk staff (~160) view 15 portal pages a working day, and handset staff
  3 sessions × 3 pages. That is roughly **6,400 non-Home page views a day**.
- 6,400 × 21 extra statements ≈ **134,000 extra statements a day**, ≈ **23 minutes of extra
  database time spread over a ten-hour day**, at the measured p95.
- The burst that matters is the 11 AM punch quarter. Even 200 handset sign-ins inside 15
  minutes is under **one extra call a second**. On a single-server Compose stack with the
  workers already running, that is noise.

**And the perspective that matters more:** the portal page itself is **~1.05 MB of HTML,
~235 KB gzipped** (Fact — measured 22 Sep 2026 and written into `deploy/nginx.conf` lines
83–92). Part 3 adds **638 bytes**. On a shop-floor phone the page weight is the problem;
the bell is not. Do not let this slice be the one that gets a performance argument it did
not cause.

#### The N+1 risks I found in the `_part_*` builders

I read all seven. They are in better shape than the file's size suggests — most already
read "one query for the whole page" and say so in a comment. Three things are worth naming:

1. **`_dtc_row_facts(r)` is called once per row** — `inbox_api.py` line 544, inside
   `_part_leave_approvals.rows_fn`. Each call runs `leave_rules.rule_set_for`,
   `chain_of(employee)`, `_special_day`, and for Leave Without Pay `lwp_in_play`. **Fact.**
   At DTC the pay rule set is enabled for all ticked companies (memory, 26 Oct 2026), so
   **every** leave row takes that branch — up to the 50-row list cap.
   **It does not touch the bell's number** (`count_fn` is `_count_rows`, one statement), so
   part 3 is safe from it. It bites the Inbox screen and Home's pending card, which already
   run today. And the existing guard
   (`test_inbox_parts_042.test_more_rows_do_not_mean_more_queries`, allowance +1) inserts
   leave in its own test company, where no rule set is enabled — **so this branch is not
   covered by the flatness test.** P2, and strictly speaking pre-existing: see OPS-7 and
   the scope note at the end.
2. **`_part_attendance_fixes` reads the whole queue uncapped** to produce its count
   (`limit_page_length=0`, line 838), then runs `_with_decide_flag`, which costs one
   permission question per distinct (employee, day, raiser) — memoised in `call_cache` and
   with managers pre-loaded in two queries. **Fact.** Flat in headcount; **grows with the
   depth of the correction backlog.** At DTC that backlog has been thousands of rows
   (memory: bulk delete dies at 750). This is already in every Home load today, and part 3
   would put it on every page load too. P2 — OPS-3.
3. **`_part_my_requests` and `_part_policies` both read uncapped**, but over the caller's
   own rows and the tenant's published policies. Bounded in practice. FYI only.

Two smaller things, noted and deliberately not proposed as work: `_my_employee` is asked
twice per `get_nav_counts` (once in `_Who`, once for `has_employee`), and `inbox_api` never
opens `call_cache`, so parts that each ask `permitted_companies()` ask it separately. Both
are worth about a handful of statements. Fixing them is not this slice.

### 2 · Can the count be cached? My answer is no, and here is the invalidation story

**`call_cache.py` is the wrong tool, by its own design.** **Fact** — its docstring says it
"lives for exactly one call and dies with it… there is no key that outlives the call,
nothing in redis, nothing on the session". The bell is a separate HTTP request from
everything else, so a per-call memo saves nothing across page loads. It *would* help inside
a single merged endpoint (see OPS-2), and that is the only place to use it.

**A cross-request cache of the number is not justified and I recommend against it.** Three
reasons, in the project's own priority order:

1. **There is no measured miss.** `nfr-budget.md` §2 budgets a whitelisted API call at
   ≤ 500 ms p95. The measured worst p95 is **215 ms**. `no-over-engineering.md` §2 bans a
   cache "until a measured number says the simple version misses the NFR budget". Nothing
   here misses it.
2. **The invalidation story is large and partly impossible.** To keep one badge honest you
   would have to clear it on: leave applied / approved / rejected / cancelled; expense
   submitted / decided; goal or KPI progress logged / decided; attendance correction raised
   / decided / withdrawn; shift request raised / decided; policy published, version bumped,
   or acknowledged; a Notification Log row inserted or marked read; an Employee going
   Active or Left; **and every change to a role row, a User Permission, a company or a
   branch scope** — because `permitted_companies` and `permitted_employees` decide whose
   rows are counted, and a permission change has no document event our hooks can hang on
   reliably. That is roughly fifteen write paths across four apps, plus one class of change
   that cannot be hooked.
3. **This project has already paid for a cache with no invalidation.** `auth.py` line 496,
   `_JOINER_CACHE = "alvoraa_is_a_joiner"` — a redis hash, deliberately never cleared, with
   an eleven-line comment arguing why that is safe, and a real lockout at the Amata tenant
   behind it. The comment may be right about that flag; the lesson still stands. And
   `34`'s own decision register says it plainly: **"Memoising `permitted_companies` is
   explicitly NOT the answer — a memo that outlives a request hands a background job a
   stale scope"** (W1D-23).

**And the product reason, which is the strongest one.** `inbox_api.py`'s first rule is *"a
count must equal the list it links to. Not about equal."* A cached badge is stale for its
TTL — including the seconds right after the person themselves approves something. The
project has already shipped the fix for exactly that feeling (`hmDropPending` decrements
the number the moment a row is decided, portal.js 6799). A cache would undo it.

**If a cache is ever forced by a real measurement**, the only defensible shape is per-user,
30–60 s TTL, with the user's role-and-scope stamp inside the key, plus an explicit clear on
the write paths the portal itself owns. Say so then, with the number. Not now.

### 3 · Rough run cost

| Line | Change |
|---|---|
| Containers, volumes, images | **None.** No new service, no Compose change, no Dockerfile change |
| Scheduled jobs / workers | **None.** Both feeds are read-on-demand. No queue, no job, no new failure mode to alert on |
| `deploy/nginx.conf` | **None, if part 2 is a hash route.** See OPS-4 |
| Database CPU | **Estimate** ~134,000 extra statements/day at DTC ≈ 23 minutes of database time spread over the day; well under one extra call per second even in the 11 AM burst |
| Bytes to a phone | **+638 B** per page load (Measured, slice 044), against a page that is already ~235 KB gzipped |
| Money | **₹0 extra.** No new spend, no vendor, no AI call, no storage |
| Permanent maintenance | One more endpoint on the bell's critical path. That is the whole ongoing cost |

### 4 · Red flags

**P1 — the notifications page must not become a new web page.** `deploy/nginx.conf` names
the compressible pages **exactly**, in two server blocks (lines 344 and 518):
`^/(hrms-employee|alvoraa-login|desk|…|update-password)?$`. A new address such as
`/notifications` would fall through to `location /`, which has **`gzip off`** — so it would
go out uncompressed, and the BREACH note above it (lines 302–322) explains why that default
is deliberate and must not be changed without checking the page reflects nothing from the
path or query string. Adding the name to that list means **editing
`deploy/nginx.conf`**, and **one nginx container serves production and dev from that one
file: a dev push carrying it changes the live site's proxy and restarts it.** A hash route
such as `#notices` inside `/hrms-employee` needs no nginx change, inherits the compression,
and inherits the sign-in gate. See OPS-4.

**P1 — never public, and the limit must not live in our page code.** `www/hrms_employee.py`
redirects Guest to the login page (**Fact**, read today), and a hash route inherits that.
But `data-doors.md` applies: Notification Log is also reachable through
`/api/resource/Notification Log`, `frappe.desk.reportview.get`, `frappe.client.get_list`
and link search. `notices.py`'s docstring says Frappe's own permission condition for
Notification Log pins `for_user` to the caller — **Inference from that docstring; I did not
read Frappe's source today, and nobody should take my word for it.** The security engineer
and the test engineer should prove it as a plain staff login through the API on a fresh
site. See OPS-9 and OPS-10.

**P2 — no background worker is needed, and no scheduler change.** **Fact** — the only
nearby scheduled job is `alvoraa_portal.announcements.send_due_announcements`, on the
`"all"` (every-tick) list in `hooks.py` line 507. The project's reality is that an
"every minute" tick really runs every **3–4 minutes**; dev was set to 60 s and production
was still outstanding at the 043 release (memory note, 25 Sep 2026; **[ASSUMPTION]** still
outstanding — I could not check, and I will not probe production). **Consequence for this
slice:** if the notifications page shows a "sent" or "scheduled for" time, it must not
promise a minute. Nothing in parts 1–3 should add to that list.

**P2 — the bell inherits the Inbox's blast radius.** ALV-250 (`inbox_api.py` lines 223–240):
one part raising `PermissionError` took the whole panel down, counts included, because
`parts()` builds every part before returning anything. `_may_read` fixed that. After part
3, that call runs on **every page** instead of only Home, so the failure surface widens.
Today's `ntBellBoot` already swallows its own error and leaves the bell as it was
(portal.js 6840). **Keep that behaviour exactly, for both calls.** See OPS-6.

**P3 — double counting is the correctness trap in part 3.** `notices.py` restricts
Notification Log to `NOTICE_DOCTYPES` — grooming Mark, grooming Review, Announcement
(**Fact**, lines 36–38). The Inbox's seven parts read Leave Application, Expense Claim, KPI,
Individual Goal, Attendance Request, Shift Request and Policy Document. **The two sets are
disjoint today, so a merged number is honest today.** It stops being honest the first time
anyone writes a Notification Log row for a leave approval. See OPS-8.

### 5 · Effort, split so part 3 can be dropped

Engineering days, **Estimate**, including tests. The engineer owns the real number; this is
so Surbhi can see the proportions.

| Part | Server work | Browser work | Estimate | Run cost it adds |
|---|---|---|---|---|
| **1 · Desktop bell** | **None** — the call already runs on every page | Markup placement in the desktop bar, CSS, focus and keyboard behaviour for the sheet on a wide screen, a jsdom test | **0.5 day** | **Nil** |
| **2 · Notifications page, filters in the browser** | **None** — `notices_feed(see_all=1)` already returns the window | A hash route, the list, the filter chips, empty states, "last 30 days" wording, mark-as-read already exists | **1–1.5 days** | **Nil** |
| **2b · Filters that must reach the server** | New window, new cap, pagination, re-measure the query budget | the above, plus paging | **+1.5–2 days** | A new query shape to keep flat |
| **3 · Merge the feeds** | **None**, if the browser adds two existing numbers. +0.5 day if a thin server endpoint wraps both | Add the two numbers, keep the 1.5 s defer, keep the swallow-the-error behaviour, a test that the number equals the two lists | **0.5–1 day** | **+21 statements and 638 B per non-Home page load** |

**If part 3 is dropped**, parts 1 and 2 still stand on their own, change no server code at
all, and the bell keeps meaning "notices". That is a clean place to stop. Part 3's cost is
not out of proportion — it is the only part with any run cost, and the cost is small — but
it is the only part that can be deferred without leaving a half-finished screen.

**Where I am on the cost ladder** (`no-over-engineering.md` §1): part 1 is rung 3–4 (markup
and CSS on an existing page). Part 2 is rung 4 (a page in an existing JS file, reusing an
existing endpoint) — rungs 1–3 were rejected because there is no Frappe or ERPNext
employee-facing notifications page; Frappe's own Notification Log list view is a Desk
screen and ESS staff have no Desk. Part 3 is rung 4 at most, and **zero new server code**
in its recommended shape. **No new DocType and no new app anywhere in this slice.**

### 6 · The OPS rows

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| **OPS-1** | **The bell's number comes from `inbox_api.get_nav_counts`, never from `get_inbox`.** Rows only when the person taps | `get_nav_counts` is 21 statements and 638 B of pure numbers (Measured, slice 044). `get_inbox` is 26 statements and ships colleague names, leave types and claim amounts | Every page load on every phone carries approval rows in its payload — Wave 1's worst security finding, repeated | **Recommend · P1** | |
| **OPS-2** | **Decide where the two numbers are added: in the browser, or in one thin server endpoint.** My default: **in the browser**, both calls fired together, as Home already does today. A server endpoint is worth +0.5 day only if the extra 3G round trip is measured as a problem — and then it should open `call_cache` around both feeds | Browser-side is zero new server code and zero new permission surface. Server-side saves one round trip (~0.2–0.5 s on 3G, **Estimate**) and lets the two feeds share repeated scope reads | Either a wasted round trip on a shop phone, or a new endpoint nobody needed | **Recommend · P2** | |
| **OPS-3** | **Measure `get_nav_counts` on a DTC-shaped copy before part 3 ships** — pay rule set enabled, a deep attendance-correction backlog, as an HR caller and as a plain employee. Record the statement count and p95 with the date | The 21/215 ms figures are from September 2026 on fixture sites with no rule set enabled. `_part_attendance_fixes` reads its whole queue uncapped and `_dtc_row_facts` runs per row | The one call now on every page is the one call nobody has measured in the configuration that actually runs it | **Recommend · P1** | |
| **OPS-4** | **Part 2 is a hash route inside `/hrms-employee` (e.g. `#notices`). No new web page, and no `deploy/nginx.conf` change.** If a real page is wanted, it is a separate decision with an nginx change behind it | `nginx.conf` whitelists compressible pages by exact name (lines 344, 518); anything else gets `gzip off`. One nginx container serves dev **and** production from that one file, so a dev push carrying it restarts the live site's proxy | A ~1 MB uncompressed page on a shop phone, or a dev push that restarts production's nginx | **Recommend · P1** | |
| **OPS-5** | **⚠ DECISION — do the filters work on the 100 rows already fetched, or must they search beyond 30 days / beyond 100 rows?** My recommendation: browser-side over the existing payload for v1, with "Last 30 days" said on the screen | It is the only question in this slice that changes server cost. Browser-side = no server change. Server-side = new window, new cap, pagination, a re-measured query budget, +1.5–2 days | Either the page quietly shows a 30-day slice people think is everything, or the slice doubles in size without anyone choosing that | **Recommend · P1** | |
| **OPS-6** | **Keep the bell deferred (~1.5 s after load) and keep both calls failing silently** — the badge stays as it was, no toast, no blanked page | `ntBellBoot` already does both (portal.js 18393, 6840). After part 3 the Inbox's failure surface is on every page, and ALV-250 showed one part can throw | A tenant with one odd role row gets an error on every page instead of a missing badge | **Recommend · P2** | |
| **OPS-7** | **Put the DTC leave-row branch under the existing flatness test** — `test_inbox_parts_042.test_more_rows_do_not_mean_more_queries` with a pay rule set enabled | `_dtc_row_facts` runs per row (line 544); the test's company has no rule set, so the branch is untested. **This is pre-existing, not caused by this slice** | The N+1 that only appears at the tenant that has 600 staff stays invisible until someone complains | **Consider · P2** | |
| **OPS-8** | **Define the merged number as the sum of two disjoint sets, and assert the sets stay disjoint** — `notices.NOTICE_DOCTYPES` against the Inbox's seven doctypes, in a test | They are disjoint today (Fact). The day a leave approval also writes a Notification Log row, the bell double-counts and `inbox_api`'s first rule breaks | A badge that says 4 when the lists hold 3 — the exact failure slices 034/042/076 were built to prevent | **Recommend · P2** | |
| **OPS-9** | **No new whitelisted endpoint, and no client-supplied filter that selects a doctype, a field or a user.** Filters are fixed names mapped server-side, or applied in the browser | `nfr-budget.md` §4: never let a client string select a doctype, field or code path. The window and `for_user` must stay server-decided | A notifications filter becomes a way to read somebody else's log | **Recommend · P1** | |
| **OPS-10** | **Run the `data-doors.md` door list against Notification Log as a plain staff login, on a fresh site** — `/api/resource`, `reportview.get`, `frappe.client.get_list`, link search, report view and export, share | Our page's limit is not the limit. `notices.py` says Frappe's own condition pins `for_user`; that is an Inference from a docstring and needs proving. ALV-249 is what this rule is made of | A staff login reads colleagues' notification subjects through a door we never opened on purpose | **Recommend · P1** | |
| **OPS-11** | **No cache of the badge number.** Not `call_cache` (it dies with the call), not redis | Measured p95 is 215 ms against a 500 ms budget, so there is no miss to fix; the invalidation list runs to ~15 write paths plus permission changes that cannot be hooked; and `auth.py`'s never-cleared joiner flag is the lesson already paid for | A badge that is wrong for a minute after the person acts, and a stale-scope bug waiting for a background job | **Recommend · P2** | |
| **OPS-12** | **Nothing new to deploy, nothing new to monitor.** No Compose change, no image change, no scheduler entry, no worker, no alert. If that stops being true at the strategy stage, it is a change of shape and should be said out loud | Every new moving part is something that breaks at 2 a.m. and must be upgraded for ever | A small UI slice grows an operational tail | **FYI · P3** | |

### 7 · What I could not check

- **Real page-view volume at DTC.** My 6,400 views/day is an Estimate built from headcount.
  Nobody has counted. It only matters if it is ten times out.
- **Whether production's scheduler tick is still 3–4 minutes.** I will not probe production.
  It only affects the wording of a "scheduled for" time on the new page.
- **Any number on dev or production.** I ran nothing anywhere. The 21 / 26 / 215 ms figures
  are slice 044's, from September 2026, on fixture sites.
- **Frappe's own `permission_query_conditions` for Notification Log.** I inferred it from
  `notices.py`'s docstring and did not read Frappe's source.

### 8 · Scope creep I am deliberately leaving alone

Noted, not proposed as work in this slice (`no-over-engineering.md` §6): the per-row
`_dtc_row_facts` N+1 (OPS-7 asks only for a test that would catch it), `_my_employee` asked
twice per `get_nav_counts`, and `inbox_api` never opening `call_cache`. All pre-existing,
all small, all for Surbhi to schedule separately.

### 9 · Subtract pass

Read once more asking only what I could delete. **Removed:** a proposed 30-second
per-user badge cache with a scope-stamped key and seven invalidation hooks (there is no
measured miss, so it was my instinct, not the requirement); a proposed new
`notifications_feed` endpoint with server-side filters and paging (reduced to the decision
at OPS-5, because the existing `notices_feed` already returns the window the page needs);
a proposed alert on `get_nav_counts` error rate (the bell already fails silently and the
existing health collection already reports error counts — a new alert was a new moving part
for no new failure mode); and a proposed payload-byte budget row (slice 042's OPS-W2-7
already set one; repeating it here would be a second source for one number).

**Kept deliberately:** the DTC-shaped measurement (OPS-3), because it is the one number
this slice genuinely does not have.

---

## §2 Design — 6 November 2026

Appended. **§1 above is unchanged.**

**Answer first: the designer's P1 fix is cheap, and I can now settle the question it
raised. The true unread count costs two extra statements, stays flat as rows grow, and
does not break the flatness gate — but it cannot be a plain `COUNT(*)`.** The grooming
readability gate has to run over **every unread grooming row**, not just the page's. That
sounds expensive and is not: `grooming._readable` asks a **fixed** number of queries
whatever the row count, so a bigger input makes the lists longer, not the query count
higher. Announcements need no gate at all, so they really are a `COUNT(*)`. Split the
count by kind and the whole thing is +2 statements.

**Second answer: nothing in this design needs `deploy/nginx.conf` touched.** The page
already sends `Cache-Control: no-store` (OPS-19), the hash route from §1 still holds, and
the panel adds no new address, no image and no new file.

**The one thing in §2 that could multiply the run cost tenfold is a single line of
JavaScript: a `setInterval` refresh.** Today's refresh fires on navigation, never on a
timer. A 60-second poll on 441 DTC handsets is about **15 extra calls a second, all day**,
against roughly zero today. See OPS-14 — it is the biggest number in this slice and it is
one habit away.

No P0. Nothing here is dangerous debt.

### 2.0 · What I read today, and what I ran

**Fact — in the worktree `.claude/worktrees/083-ess-notifications` at `814d540f`:**
`docs/slices/083-ess-notifications/01b-ux-design.md` (615 lines) and `01-product-brief.md` ·
the prototype `C:/Surbhi-Git/hrlocal-data/prototypes/083-ess-notifications/prototype-v1.html`
(39,274 bytes) · `notices.py` in full · `grooming.py` (`_readable`, `hr_scope`,
`_active_employee`, `my_notices_seen`) · `inbox_api.py` (`get_inbox`, `LIST_CAP`,
`CORRECTIONS_CAP`, `ROW_KEYS`) · `tests/test_notices_076.py` · `auth.py`
(`lock_until_password_chosen`, `_has_chosen_own_password`) · `www/hrms_employee.py` ·
`templates/includes/ess/frame.html` (the bell) · `public/js/ess/portal.js` (`HM_STALE_MS`,
`hmRefreshIfStale`, `WRITE_CALL`, `gpFetch`) · `deploy/nginx.conf` (gzip block, `/assets/`
location) · `.claude/context/nfr-budget.md`, `no-over-engineering.md`.

**Fact — I also read Frappe's own source, inside the local bench container, read-only:**
`frappe/desk/doctype/notification_log/notification_log.json` and `notification_log.py`,
`frappe/hooks.py`, `frappe/app.py`, `frappe/website/utils.py`,
`frappe/website/page_renderers/template_page.py`, `frappe/commands/utils.py`,
`frappe/database/database.py`, `frappe/desk/notifications.py`.
Every command was a `cat`, `sed` or `grep` **inside the container's app folder**. I ran no
`bench` command, opened no site, read no site database, and changed nothing. I went nowhere
near dev or production.

**Measured today — local file sizes, `gzip -6`** (nginx uses `gzip_comp_level 5`, so the
wire figure is a little larger):

| File | Raw | Gzipped |
|---|---|---|
| `public/js/ess/portal.js` | 1,269,713 B (24,124 lines) | **333,322 B** |
| `public/css/ess/panels.css` | 227,066 B (3,264 lines) | **46,004 B** |
| `public/css/ess/frame.css` | 21,839 B | **6,603 B** |

That gives **52.6 bytes per line** and a **3.81 : 1** compression ratio, which is what the
estimates below are built on.

**One Git Bash trap worth recording** (lesson 19): my first `docker exec … cat /home/frappe/…`
returned *"cat: 'C:/Program Files/Git/home/frappe/…': No such file or directory"* — Git Bash
rewrote the leading-slash path. Every command below is written for **PowerShell**, where the
problem does not arise; in Git Bash, prefix with `MSYS_NO_PATHCONV=1`. **A command that
failed this way can look like a clean answer** if you only read the exit code.

---

### 2.1 · The P1 fix, costed

#### What makes it not a `COUNT(*)`

**Fact.** `notices.py` restricts to three document types: `Grooming Mark`,
`Grooming Review`, `Announcement`. The gate `grooming._readable` is then applied to the
grooming rows **only** — an announcement row "is the person's own copy: nothing more to
gate" (the code's own comment).

**Fact — the gate really does change the number.** `_readable` recomputes the reader's
relationship to each grooming document *now*: own record, HR scope, or
`manager and getdate(d.mark_date) == today`. So a manager's mark notice stops being
readable the day after, and a reader who leaves the company stops seeing any of them.
`test_notices_076.test_a_notice_is_hidden_when_its_reader_may_no_longer_read_the_mark`
proves it: the same user's `unread` goes **1 → 0** when their Employee record is set to
Left, with no row changed.

**So a plain uncapped `COUNT(*)` over the three types would over-count.** It would not
just be untidy: it would hand back a badge larger than the list beneath it, breaking
`inbox_api.py`'s first rule — *"a count must equal the list it links to"* — and it would
fail that existing test. **An unfiltered count is the wrong answer, and I am ruling it
out.**

#### How expensive is the gate at volume? Flat in queries, linear in Python

**Fact — `_readable` asks a fixed number of queries whatever you pass it:** at most two
`get_all`s for the documents (one per type, `name in (…)`), one `_active_employee`, one
`get_all` for managers, and `hr_scope`'s one query. Every one uses an `IN` list. There is
**no per-row query** — no N+1. The per-row work is a Python dict comparison.

| Unread grooming rows for one person | Extra queries | Python work (**Estimate**, ~2 µs/row) | SQL text for the `IN` list (**Estimate**, ~20 B/name) |
|---|---|---|---|
| 100 | 0 | 0.2 ms | 2 KB |
| 1,000 | 0 | 2 ms | 20 KB |
| 5,000 | 0 | 10 ms | 100 KB |

**Inference, resting on those facts: safe at 5,000 rows for one user, with room to spare.**
The limiting factor is the size of the SQL statement, not the database, and 100 KB is far
under MariaDB's default `max_allowed_packet`. **I did not run this. These are estimates
from reading the code, not timings.**

#### The index, and what the count really scans

**Fact — read in `notification_log.json` today:** `for_user` carries `"search_index": 1`,
and so does `document_name`. **`read` is a Check with no index, and `document_type` is a
Link with no `search_index`.** The only useful index for us is the single column
`for_user`.

**Inference:** `WHERE for_user = ? AND read = 0 AND document_type IN (3)` uses the
`for_user` index to reach that person's rows, then tests `read` and `document_type` on each
one. So the cost grows with **everything that person has ever been sent, of every kind** —
not with the three kinds we care about.

That matters because of two numbers the designer found: **2,016 Notification Log rows at
PPJ, with four users over 400 each, and the heaviest carrying 407 rows / 406 unread — all
of `document_type = "Employee"`, which our page never shows.** So today's heaviest real
count would scan 407 index entries to return 0. **Estimate: a few milliseconds.** At 5,000
rows for one user, still **Estimate: tens of milliseconds at worst**, against the ≤ 500 ms
p95 budget in `nfr-budget.md` §2.

**I am not recommending a new composite index.** `no-over-engineering.md` bans one until a
measured number misses the budget, and nothing here does. If a measurement ever does miss,
the shape is `(for_user, read, document_type)` — write it down then, with the number.

#### The shape I recommend

Split the count by kind, because only one kind needs the gate:

1. **Announcements — one count statement.** `for_user = me`, `document_type = "Announcement"`,
   `read = 0`. Exact, no gate, no rows loaded. This is the kind that will actually pile up:
   one sender reaches all 597 DTC staff at once.
2. **Grooming — one uncapped read of three small fields** (`name`, `document_type`,
   `document_name`) for `read = 0`, folded into the **same** `_readable` call the function
   already makes. **Zero extra queries for the gate.**
3. `unread` = (1) + the readable part of (2). `capped` = the page read hit `READ_CAP`.

**+2 statements.** I prefer this to the obvious one-statement version (a single uncapped
read of all three types) because that one would pull **announcement rows** into memory for
no reason, and announcements are the unbounded kind. Two statements is nothing; an
unbounded row load is the thing worth avoiding.

**Answering the designer's direct question — does this threaten the ≤ 12 assertion in
`test_notices_076.py`?** Yes, and the fix is to raise the number, not to change the shape:

- `self.assertLessEqual(big.n, 12)` becomes **14**.
- `self.assertEqual(small.n, big.n)` — **the flatness assertion — is untouched and still
  passes.** That is the gate that matters, and the fix does not weaken it.
- Both new statements are flat in headcount and flat in row count. Say the new number out
  loud in the commit, with the reason, so nobody later reads 14 as drift.

**One trap for whoever writes it.** `frappe.db.count` builds its query through
`frappe.qb.get_query` and **does not apply** Frappe's permission condition (read in
`frappe/database/database.py:1285`). So an explicit `for_user: frappe.session.user` filter
is the protection, not decoration. Counting through `frappe.get_list` with
`fields=["count(name) as n"]` applies the condition as well — belt and braces, same one
statement. Either is fine; the explicit filter is not optional. (**Inference** — I read
both code paths, I ran neither.)

**Mark all as read is the other half of this fix, and it is easy to get wrong.** See
OPS-15: the badge only reaches zero if the write is one set-based `UPDATE`. A true count
with a 100-row write would still leave the badge stuck.

---

### 2.2 · Page weight and 3G

**Bad news first, and it is not this slice's fault: the portal's first load after a release
already misses the ≤ 2.5 s 3G budget, by about 25%.** This slice adds roughly 2–3% to the
asset payload. Do not let it carry the pre-existing problem, and do not let the
pre-existing problem be used to block it.

**Fact.** `/assets/` is served with `expires 30d; add_header Cache-Control "public, immutable"`
(`deploy/nginx.conf:211–218`) and is gzipped by the http-level `gzip on`, with
`application/javascript` and `text/css` in `gzip_types`. `www/hrms_employee.py` stamps every
asset URL with `get_build_version()`, so **every release is a new address and every phone
re-downloads the lot once.**

**Cold cache, first load after a release (Estimate, from today's measured sizes):**

| Part | Gzipped |
|---|---|
| The HTML page | ~235 KB (Measured 22 Sep 2026, quoted in §1) |
| `portal.js` | **333 KB** (Measured today) |
| `panels.css` | **46 KB** (Measured today) |
| `frame.css` | **7 KB** (Measured today) |
| **Total** | **~621 KB** |

- At Chrome's **"Fast 3G"** profile (1.6 Mbit/s ≈ 200 KB/s): **~3.1 s of transfer alone**,
  before any round trip. **Misses the 2.5 s budget.**
- At **"Slow 3G"** (400 kbit/s ≈ 50 KB/s): ~12 s.
- **Warm cache** (the normal case between releases): the HTML only, ~235 KB ≈ **1.2 s at
  Fast 3G. Inside budget.**

**What this panel adds. Estimate, built on today's measured 52.6 B/line and 3.81 : 1 ratio:**

| Where | Estimate |
|---|---|
| New JavaScript in `portal.js` (panel, three chips, three groups, nine states, the five-row footer, the paint function) | 450–700 lines → 24–37 KB raw → **+6–10 KB gzipped** |
| New CSS in `panels.css` / `frame.css` | ~120 lines → **+1–2 KB gzipped** |
| New HTML in `frame.html` (the desktop bell + the sidebar `<button>`) | ~15 lines → **+600 B raw, on the warm-cache path** |
| **Total on a cold cache** | **+8–12 KB gzipped, about 2–3% of the asset payload** |
| **Transfer cost of that at Fast 3G** | **+0.04–0.06 s** |
| **Total on a warm cache** | **+600 B.** Effectively nothing |

**The panel's own first paint:** two API calls fired together, each measured at 215 ms p95
in September 2026 on fixture sites (§1). On 3G the round trip dominates — **Estimate
0.6–1.2 s to filled rows**, with the skeleton drawn locally well inside the 300 ms rule.
Inside the ≤ 1.5 s self-service figure on broadband, and inside 2.5 s on 3G **provided the
assets are warm**.

**A question I cannot answer from here, and it changes the verdict:** `nfr-budget.md` §2
says "a 3G phone profile" without naming which one. Fast 3G and Slow 3G are a factor of
four apart, and the cold-load answer flips from "misses by 25%" to "misses by 5×". **My
recommended default: Chrome DevTools "Fast 3G" (1.6 Mbit/s, 562 ms RTT), stated in the
test**, because it is the profile a repeatable automated test can set. See OPS-16.

---

### 2.3 · Caching — confirmed, nothing reintroduces one

**Confirmed. The design adds no cache, and OPS-11 stands.** I checked each place one could
have crept in:

| Where a cache could hide | What the design actually does | Verdict |
|---|---|---|
| The badge number | Summed **in the browser** from the two answers already fetched (design §5) | A local variable inside one page load. Not a cache |
| `ntPaintBadge` as "one writer" | One function, three call sites (Home's paint, `ntBellBoot`, after a decision) | Fewer writers, not a stored value |
| The refresh | **Fact** — `HM_STALE_MS = 60000` is used only by `hmRefreshIfStale`, which fires **on returning to the panel**, never on a timer (`portal.js:6411`, `6567`) | Navigation-triggered. **Must stay that way** — OPS-14 |
| `call_cache` | Not used by either feed, and still dies with the call | Unchanged |
| Server-side page cache | **Fact** — `www/hrms_employee.py` sets `context.no_cache = 1`, so Frappe's `cache_html` never stores the page | No stale HTML, and no `private,max-age=300` header |

**The third moment the badge repaints** (after a decision taken on the new page) makes the
no-cache position stronger, exactly as the designer said. A stored number would be wrong in
the second after the person acted, which is the second that matters most.

---

### 2.4 · What must never be public

**Good news, and it closes an unknown from §1.** **Fact — I read Frappe's own source today,
in `frappe/desk/doctype/notification_log/notification_log.py`:**

- `get_permission_query_conditions(for_user)` (line 104) returns
  `` (`tabNotification Log`.for_user = <escaped session user>) `` for everyone except
  Administrator.
- `has_permission(doc, ptype, user)` (line 114) returns
  `user == "Administrator" or doc.for_user == user`.
- Both are registered in `frappe/hooks.py` — line **117** (`permission_query_conditions`)
  and line **151** (`has_permission`).

**So §1's inference from a docstring is now confirmed at the code level, in both the list
door and the single-document door.** OPS-10's door-list test still stands — a condition is
not the same as a proof, and the doctype's own permission row grants role **"All"**
`read`, `report`, `export` and `share` — but the **Unknown is closed**. Nobody has to take
my word for it any more; the line numbers are above.

**The hash-route decision from §1 holds.** Nothing in the design adds an address.
`www/hrms_employee.py` redirects Guest to `/alvoraa-login?redirect-to=/hrms-employee`
(**Fact**, read again today), and a `#notices` route inherits it. **No `deploy/nginx.conf`
change.**

**The shared-handset question — are the designer's two acceptance criteria enough, or does
the page need a cache-control header?**

**The header is already there, and no nginx change is needed.** Traced today:
`context.no_cache = 1` → `can_cache(1)` is False in `frappe/website/utils.py:548` → the
`private,max-age=300,stale-while-revalidate=10800` header is never set → `process_response`
in `frappe/app.py:291` applies its default,
**`Cache-Control: no-store,no-cache,must-revalidate,max-age=0`**. nginx does not override
it: the only `add_header Cache-Control` lines are on `/assets/` and `/files/`.
**Inference from code read end to end; I did not observe a real response header.**

**So are the two criteria enough?** Nearly, and I would add one and keep one open:

1. **Nothing in `localStorage` or `sessionStorage`** — necessary and testable. **Fact:** the
   portal keeps exactly one key today, `sb-pinned` (`portal.js:24101`, `24109`), and both
   sign-out links already remove it (`frame.html:148`, `174`). A second key would have to
   be removed in **both** places, which is a thing to get wrong. Keep the criterion.
2. **Back after `/logout` renders nothing** — keep it, **and assert the response header in
   the same test**, so a future change to `hrms_employee.py` that drops `no_cache` is caught
   by something cheaper than a browser.
3. **Open, and I will not guess:** Chrome on Android has been rolling out back/forward-cache
   for `no-store` pages, evicting the entry when an **HttpOnly** cookie changes. Logout does
   change `sid`, so I **expect** eviction and a blank Back. **I could not check that**, and
   it is a browser behaviour, not a header we control. The honest answer is to test it once
   on a real Android handset rather than add a header that would not change it. See OPS-19.

**Media — confirmed: nothing.** **Fact:** the bell is an **inline SVG** inside
`frame.html:137`, so the desktop copy is markup, not a file — no new network request, no new
image, no font. The prototype contains **zero** `<img>` tags, zero `background-image` and
zero `url(data:…)` (counted today). No volume growth, no backup growth, no CDN question.

---

### 2.5 · The five-rows-per-group change — confirmed, no server paging

**Confirmed. The rows are already in the payload, and no endpoint changes.** **Fact:**

| Feed | What it already returns |
|---|---|
| `notices_feed(see_all=1)` | up to `READ_CAP = 100` rows for the window |
| `get_inbox` | `LIST_CAP = 50` and `CORRECTIONS_CAP = 50` per part, **and already returns `count`, `shown` and `capped` per part** so a screen can say "Showing the first 50 of 63" |

Showing 5 of them is a slice of an array in the browser. The "See all 86 notices" footer
sets an existing chip and fetches nothing. **This is the cheapest possible answer to a
6,744 px page: zero statements, zero bytes, one `.slice()`.** It also *reduces* render work
on a shop-floor phone — fewer DOM nodes on first paint.

The one thing to hold: the footer's **"86"** must come from the feed's own count (and, after
the P1 fix, from the true count), never from `items.length`. Otherwise the footer says
"See all 100 notices" to a person with 150. Same fault, new place.

---

### 2.6 · The two operational findings handed to me

#### 1 · Every demo login on `ppj.localhost` lands on "Set Password" — ⚠ DECISION, OPS-20

**I agree with the diagnosis, and I have not run anything.** **Fact — `auth.py`:**
`lock_until_password_chosen` lets a request through when `_has_chosen_own_password(user)` is
true, which is true only when `User.last_password_reset_date` is set (checked at line 306,
memoised in redis at 307). It then exempts anyone with **no** Employee record (line 394),
which is exactly why the designer's HR Manager account worked.

**The smallest safe fix: set `last_password_reset_date` on ONE demo employee user, on the
local bench only.** It changes no password — the demo password keeps working — and it
exempts that one account from the first-use lock from then on. No `bench migrate`, no
`clear-cache` (the redis memo is a positive-only cache, so setting the field is enough), no
restart, no code change, no site config change.

**Which user:** I deliberately did not query the site database, so I cannot name the email.
The designer's line-manager persona is **Sakshi Verma, a real PPJ Floor Manager** — the
right choice, because it is the persona every future review needs (a manager with a team,
pending approvals and a sidebar). Step 1 below finds the exact email; **step 2 is Surbhi's
to approve.**

**Step 1 — read-only, finds the candidates and the exact email:**

```powershell
docker exec hrlocal-bench bench --site ppj.localhost execute frappe.get_all --kwargs "{'doctype':'Employee','filters':{'user_id':['is','set'],'status':'Active'},'fields':['name','employee_name','designation','user_id'],'limit_page_length':10}" 2>&1
```

> **DONE — 11 November 2026, authorised by Surbhi.** The account is
> **`ashok.mittal336@ppjewellers.demo`** — Ashok Mittal, *Floor Manager – Diamond*,
> employee `PPJ-0336`. `last_password_reset_date` is set to `2026-11-11`, verified by
> step 3. No password was changed, no migrate, no cache clear, no restart.
>
> **Use this account to review the portal as an employee on `ppj.localhost`.** Note that
> the designer's persona "Sakshi Verma" does not exist on the bench — it was invented and
> tagged *Sample*. Ashok Mittal is the real equivalent and holds the same role.
>
> Still true, and separate: **PPJ holds zero rows of the three notice kinds and zero
> pending approvals**, so this login reaches the portal but the notifications page will be
> empty. Demo seeding is its own need.

**Step 2 — the one write. For Surbhi to approve and run; I have not run it.** Replace
`<email>` with the one chosen in step 1:

```powershell
docker exec hrlocal-bench bench --site ppj.localhost execute frappe.db.set_value --kwargs "{'dt':'User','dn':'<email>','field':'last_password_reset_date','val':'2026-11-06'}" 2>&1
```

**Step 3 — prove it landed, read-only:**

```powershell
docker exec hrlocal-bench bench --site ppj.localhost execute frappe.db.get_value --kwargs "{'doctype':'User','filters':'<email>','fieldname':'last_password_reset_date'}" 2>&1
```

**Four things about those commands, each of which has cost this project time:**

- **`bench execute` commits by itself.** **Fact** — `frappe/commands/utils.py:316`:
  `if frappe.db: frappe.db.commit()`. So step 2 is a real, immediate write. There is no dry
  run.
- **`bench execute` hides the real error.** **Fact** — same file, lines 298–305: if the
  method call raises, it falls back to `eval`ing the string and reports **that** failure
  instead. The `2>&1` on every line above is why. Read both streams, and never trust step 2
  without step 3.
- **Git Bash would mangle these.** Run them in **PowerShell** as written, or prefix with
  `MSYS_NO_PATHCONV=1` in Git Bash.
- **Local bench only.** This must never be run on dev and never on production, and never on
  a DTC user. It deliberately removes a security control for one demo account. Say which
  account in the slice record, so the next agent does not have to rediscover it.

**Why it is worth doing:** it unblocks browser-based review for every future slice. **But
the bench is shared with other sessions and the account is a real one — Surbhi decides.**

**A second thing the designer could not see, and it is more limiting than the lock:** PPJ
holds **zero** rows of the three notice kinds and zero pending approvals. Even with a demo
login fixed, this page has no data to show. Whoever reviews it will need seeded rows (the
`demo/` folder is the place, and it never reaches `main`). Not my call to make, but worth
knowing before someone expects a populated screenshot.

#### 2 · The five stale sidebar badges

**Purely cosmetic — no operational risk.** They are client-side paints with no server call
behind them, so there is nothing to time out, nothing to alert on and no extra query; the
only cost is that a person learns the sidebar numbers are not to be trusted, which is a
product problem for the follow-up slice, not an ops one.

---

### 2.7 · What I confirmed, in one place

| The question | Answer | Label |
|---|---|---|
| Does the hash-route decision (OPS-4) still hold? | **Yes.** The design adds no address | Fact — design read |
| Does the panel need `deploy/nginx.conf` changed? | **No.** No new page, no new header, no new file type | Fact |
| Does the panel inherit the Guest redirect? | **Yes** — `www/hrms_employee.py` redirects Guest; a hash route is the same page | Fact |
| Does the page already send `no-store`? | **Yes** — `context.no_cache = 1` → Frappe's default header. nginx does not override it | Inference from code read end to end |
| Does Frappe pin `for_user` on Notification Log? | **Yes**, in both doors — `notification_log.py:104` and `:114`, hooked at `frappe/hooks.py:117` and `:151` | Fact — Frappe source read today |
| Does the design reintroduce a cache? | **No.** The badge is summed in the browser; the refresh is navigation-triggered | Fact |
| Does the design add media? | **No.** Inline SVG bell; zero images in the prototype | Fact |
| Does the five-row rule need server paging? | **No.** The rows are already in both payloads | Fact |
| Does the P1 fix break the flatness gate? | **No.** `small.n == big.n` still holds; only the ≤ 12 ceiling moves to 14 | Inference from the code and the test |
| Is an uncapped count safe at 5,000 rows for one user? | **Yes**, with room — tens of milliseconds against a 500 ms budget | Estimate, not measured |

---

### 2.8 · The OPS rows — continuing from OPS-12

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| **OPS-13** | **Build the true unread count as two statements split by kind:** one `COUNT` for unread Announcements (no gate needed — the row is the person's own copy), and one uncapped read of three small fields for unread grooming rows **folded into the existing `_readable` call**. Raise `test_notices_076`'s ceiling from **≤ 12 to ≤ 14**, say why in the commit, and **leave `small.n == big.n` exactly as it is**. Keep an explicit `for_user: frappe.session.user` filter on the count, because `frappe.db.count` does **not** apply Frappe's permission condition | A plain `COUNT(*)` over the three types would over-count: `_readable` genuinely removes rows (a manager's mark notice expires the next day; a Left reader loses all of them), and `test_a_notice_is_hidden_when_its_reader_may_no_longer_read_the_mark` already proves it. The gate asks a **fixed** number of queries whatever the row count, so running it over all unread rows adds **zero** queries — just longer `IN` lists | Either a badge bigger than its own list (the fault slices 034/042/076 exist to prevent, and a failing test), or an unbounded row load for the one kind that will actually pile up | **Recommend · P1** | |
| **OPS-14** | **No `setInterval`, no polling, anywhere in this panel.** The refresh stays navigation-triggered, the way `hmRefreshIfStale` already works at `HM_STALE_MS = 60000` | **Fact** — nothing in the portal polls today. A 60-second poll of two calls on 441 DTC handsets is **441 × 2 ÷ 60 ≈ 15 extra calls a second, all day** (Estimate from the handset count), against roughly zero now — about 300 extra statements a second at the measured 21 per call. It is the only change in this slice that could multiply the run cost, and it is one line | The cheapest slice in the quarter becomes the one that needs a capacity conversation | **Recommend · P1** | |
| **OPS-15** | **"Mark all as read" is ONE set-based `UPDATE`, scoped to `for_user = me` AND the three `NOTICE_DOCTYPES`.** Not a loop over `mark_as_read`, and **not** Frappe's own `mark_all_as_read` | **Fact** — the portal calls Frappe's single-row `mark_as_read` today (`portal.js:6408`), so 86 unread would be **86 POSTs — Estimate 10–20 s on 3G and 86 writes** — and it would re-create the stuck badge the true count was meant to fix. **Fact** — Frappe's `mark_all_as_read` (`notification_log.py:271`) filters on `for_user` **only**, so it would also clear rows our page never showed: at PPJ's heaviest user that is **406 unread `Employee` rows** belonging to the Desk bell. `grooming.my_notices_seen` already shows the right pattern — one `set_value` with a filter dict — and is no longer called from the portal | A button that takes twenty seconds, or quietly wipes another surface's notifications | **Recommend · P1** | |
| **OPS-16** | **⚠ DECISION — name the 3G profile the ≤ 2.5 s budget means, and record it in the test.** My recommendation: Chrome DevTools **"Fast 3G"** (1.6 Mbit/s, 562 ms RTT). And accept, in writing, that **the first load after a release already misses that budget** — Measured today: ~621 KB gzipped cold (235 KB HTML + 333 KB `portal.js` + 46 KB `panels.css` + 7 KB `frame.css`) ≈ **3.1 s of transfer alone**, against 2.5 s. **This slice adds ~8–12 KB gzipped, about 2–3%, and ~600 B on the warm-cache path** | `nfr-budget.md` §2 says "a 3G phone profile" without naming one, and Fast and Slow 3G are a factor of four apart. Without a named profile the gate cannot fail honestly, and this slice will be argued about for a cost it did not cause | Either a budget nobody can test, or a 2–3% addition blamed for a 25% pre-existing miss | **Recommend · P2** | |
| **OPS-17** | **Record that nothing trims Notification Log, and make retention a separate decision — not part of this slice.** **Fact** — Frappe's only scheduled job near it, `frappe.desk.notifications.clear_notifications`, deletes **redis cache keys**, not rows (read today). Rows are kept for ever | PPJ already holds **2,016** rows with four users over 400 (the designer's count). The count's cost is linear in a person's **total** row count of **every** kind, because the only usable index is `for_user` alone (`search_index: 1` in the doctype JSON; `read` and `document_type` are not indexed). It is cheap today and it never gets cheaper on its own. There are binding legal retention periods on the file already | A badge query that quietly grows for years, and personal notification subjects kept past any period counsel agreed | **Consider · P2** | |
| **OPS-18** | **OPS-10's door test still runs, but its headline unknown is closed — update the wording rather than repeating the doubt.** **Fact, read in Frappe's source today:** `get_permission_query_conditions` pins `for_user` to the session user (`notification_log.py:104`) and `has_permission` does the same per document (`:114`); both are hooked (`frappe/hooks.py:117`, `:151`). **Still worth proving through the API**, because the doctype grants role **"All"** `read`, `report`, `export` **and** `share` | §1 and the design both carried this as an inference from a docstring. It is now source-level fact, with line numbers. The test engineer should spend their time on the doors the condition does **not** cover — export, report view and share — not on re-proving `for_user` | Time spent re-deriving something now written down, or a door left untried because the easy one passed | **Recommend · P2** | |
| **OPS-19** | **Do not add a cache-control header, and do not touch nginx. Assert the one that is already there, and test Back on a real Android handset once.** The page sends `Cache-Control: no-store,no-cache,must-revalidate,max-age=0` because `context.no_cache = 1` stops Frappe's page cache and its default header applies (`frappe/app.py:291`). Add the header assertion to the same test as PM-AC-B | **One nginx container serves production and dev from one `deploy/nginx.conf`, so a dev push carrying that file changes the live site's proxy and restarts it.** There is nothing to gain here that would justify going near it. Separately, **I could not check** whether Chrome on Android back/forward-caches a `no-store` page; logout changes the HttpOnly `sid` cookie, which I **expect** evicts it — a browser behaviour no header of ours would change | A needless edit to the one file that can restart the live site — or a confident claim about a shared handset that nobody tested | **Recommend · P2** | |
| **OPS-20** | **⚠ DECISION — unblock demo review on the local bench: set `last_password_reset_date` on ONE named demo employee user on `ppj.localhost`, and record which.** The three commands are in §2.6 — step 1 read-only to find the email, step 2 the single write, step 3 to prove it. **I have run none of them.** Local bench only: never dev, never production, never a DTC user. Note that PPJ also holds **zero** notice rows and zero pending approvals, so seeded demo data is a second, separate need | **Fact** — `auth.py:306` gates on that one field, and `:394` exempts accounts with no Employee record, which is why only the HR Manager login worked. It changes no password and needs no migrate, cache clear or restart. It blocks browser review of the portal as an employee for every agent, in every future slice | Every future slice loses an hour, and designs get reviewed against the wrong persona — or a shared bench is written to without Surbhi's word | **Recommend · P2** | |

---

### 2.9 · What I could not check

- **Any timing.** Every millisecond figure in §2 is an Estimate from reading code, or
  slice 044's September 2026 measurement on fixture sites. **I timed nothing today.**
- **DTC's Notification Log counts.** Still nobody's number. The designer could not get it
  authorised and I did not try. It decides nothing in §2 — the recommended shape is safe at
  5,000 rows per user either way — but it is the number OPS-17 would be argued from.
- **Whether a real response actually carries `no-store`.** I traced the code end to end; I
  did not fetch the page.
- **Chrome Android's back/forward-cache behaviour for a `no-store` page.** Expectation
  stated, not proved.
- **The real byte size of the new panel.** The +8–12 KB gzipped is an estimate from today's
  measured 52.6 B/line and 3.81 : 1 ratio, against an assumed 450–700 new lines.

### 2.10 · What I left behind

**Nothing.** No container started or stopped, no file written outside this artifact, no
bench command, no site opened, no site setting changed. Every read of Frappe's source was a
`cat`, `sed` or `grep` inside the already-running `hrlocal-bench` container's app folder.
Nothing in this section is a secret or a path to one.

### 2.11 · Subtract pass

Read once more asking only what I could delete. **Removed:**

- **A composite index recommendation** on `(for_user, read, document_type)`. I had written
  it, then measured nothing that missed the budget — so it was my instinct, not the
  requirement. The shape is named inside §2.1 for whoever ever has the number, and it is not
  an OPS row.
- **A `COUNT_CAP` constant** to bound the grooming read. The gate adds no queries and the
  Python cost at 5,000 rows is an estimated 10 ms, so a cap would be a number invented to
  protect against nothing. If a DTC count ever shows tens of thousands for one person, add
  one line then.
- **An OPS row about `gpFetch`'s 15-second write timeout.** I thought a new
  `mark_all_read` endpoint might be misclassified; **Fact** — `WRITE_CALL` is tested against
  `String(method).split(".").pop()` (`portal.js:15514`) and matches `^mark(_|$)`, so it is
  already correct. Nothing to report, so I removed the row rather than leave a reassurance
  nobody needed.
- **An OPS row asking for a p95 measurement of the new count.** OPS-3 already asks for
  `get_nav_counts` and `notices_feed` to be measured on a DTC-shaped copy before part 3
  ships; the new statements ride along in that same measurement. A second row would be a
  second owner for one number.
- **A monitoring and alerting row.** OPS-12 already says there is nothing new to monitor,
  and §2 adds no new failure mode — both calls still fail silently and leave the badge as it
  was.
- **A recommendation to seed PPJ with demo notice rows.** It is real, but it is a demo-data
  decision, not an infrastructure one; it is named in §2.6 as a consequence and left for
  Surbhi, not turned into an OPS row I would then own.

**Kept deliberately, each with a reason:** the two-statement split (OPS-13) because the
one-statement version loads the unbounded kind; the no-polling row (OPS-14) because it is
the only ten-fold risk in the slice; and the 3G profile question (OPS-16) because without a
named profile the budget cannot fail honestly.

---

## §3 Requirements — 6 November 2026

Appended. **§1 and §2 above are unchanged.** Numbering continues from OPS-20.

**Answer first: this slice needs no new infrastructure, and after today only one thing
is still open — OPS-20, the demo-login write, which is held awaiting Surbhi.** Everything
else in §1 and §2 is now either settled or written down as an operational requirement the
business analyst can trace into a user story.

**Bad news, in one line and not new:** **ALV-299 is still open — there is no off-server
copy of any backup.** This slice adds nothing to what must be backed up, so it does not
make ALV-299 worse, but a release plan that does not say the words is a release plan that
quietly assumes a backup it cannot prove. See OPS-24.

**The single biggest run-cost risk in this slice remains one line of JavaScript.** §2
costed it: a 60-second `setInterval` on 441 DTC handsets is roughly **15 extra calls a
second, all day**, against about zero today. §3 turns that into a hard requirement with the
number inside it, so a later change cannot reintroduce it by accident (OPS-27).

No P0.

### 3.0 · The two answers from Surbhi, recorded

| Row | Status today, 6 November 2026 |
|---|---|
| **OPS-16 — the 3G profile** | **Settled. The profile is Chrome DevTools "Fast 3G"** (1.6 Mbit/s, 562 ms RTT), and it is the profile the test must set. **The pre-existing cold-load miss is accepted in writing on 6 November 2026:** ~621 KB gzipped on a first load after a release ≈ **3.1 s of transfer alone**, against the ≤ 2.5 s budget in `nfr-budget.md` §2 (Measured today, §2.2). **This slice adds 2–3% on a cold cache (~8–12 KB gzipped) and ~600 B on the warm-cache path.** It is **not this slice's debt**, and it is now written down rather than carried in anyone's head. `nfr-budget.md`'s own honesty rule requires a dated, named exception for a missed number — this is it. **No longer a ⚠ DECISION** |
| **OPS-20 — the demo-login write** | **DONE 11 Nov 2026, authorised by Surbhi.** Account `ashok.mittal336@ppjewellers.demo` (Ashok Mittal, Floor Manager – Diamond, `PPJ-0336`), `last_password_reset_date = 2026-11-11`, verified. The commands remain in §2.6 for reference. Separately, and still true: **PPJ holds zero rows of the three notice kinds and zero pending approvals** (the designer's read-only count, §2.3), so a fixed login still shows an empty page. **Demo seeding is its own need, not part of this slice** |

**Also now closed by the design, without needing Surbhi:** §1's **OPS-5** (do the filters
reach the server?). The design keeps every chip and every group a slice of the rows already
fetched, and the "See all 86 notices" footer sets a chip rather than paging — confirmed in
§2.5. **So the answer is browser-side, no server change, and the 2b column of §1's effort
table is not spent.**

### 3.1 · Queues and workers — none, and this is the row that says so

**Confirmed in writing: this slice needs no queue, no worker, no scheduled job and no
background job.** Both feeds are read-on-demand inside the request that asks for them, and
the one write ("mark all as read") is a single set-based `UPDATE` that finishes in the
request. **Fact** — `hooks.py` `scheduler_events` gains nothing; the only nearby entry is
`alvoraa_portal.announcements.send_due_announcements`, which already exists and is not
touched.

Three consequences worth stating, because each is a thing somebody could add later:

- **No `frappe.enqueue` anywhere in this slice.** Nothing here takes more than the ≤ 2 s
  that `nfr-budget.md` §2 sends to a background job. The measured worst p95 on the calls
  involved is 215 ms (slice 044, September 2026).
- **So there is no queue to pick, and no "is a worker listening on it" question.** Lesson 1
  (the hand-listed `docker compose up` that left `worker-long` out) cannot bite this slice,
  because it adds nothing to any queue.
- **No secret and no personal data travels as a job argument**, because there is no job.

### 3.2 · Rate limits — one write needs one, and there is an exact precedent

**The two reads need no limit.** `notices.notices_feed` and `inbox_api.get_nav_counts` are
already whitelisted, already called from Home on every load, and bounded by their own caps
(`READ_CAP = 100`, `LIST_CAP = 50`). Adding a limit to a call the page itself makes on every
load would refuse an ordinary person navigating quickly. **Recommend: no limit on the
reads.**

**The targeted bulk mark-as-read is different, and I recommend a limit.** It is a write a
page can fire, it is new, and the project already has the cheapest possible pattern for it.

**Fact — the precedent, read today.** `alvoraa_portal/alvoraa_portal/field_app_limits.py`
provides `_limited(SELF_KEY, "user", limit=N)`: one decorator, keyed on the **signed-in
user hashed**, `WINDOW_SECONDS = 3600`, `ip_based=False`, `methods=["POST"]`. It is already
used on seven portal endpoints — `my_profile` at 30/hour, `employee_photo` at 20,
`expense_evidence` and `employee_documents_read` at 60, `positions_profile` at 240. **This
is rung 1 of the cost ladder: the thing already exists and takes one line.**

**My recommendation: `@_limited(SELF_KEY, "user", limit=30)`** — thirty clears an hour per
person. A person cannot plausibly clear their notices thirty times in an hour; a loop can.
It sits between `my_profile`'s 30 and `employee_photo`'s 20, so it needs no new reasoning.

**Three traps, each of which this project has already paid for once:**

1. **A no-argument call is sent as a GET, and `methods=["POST"]` skips the limiter
   entirely.** **Fact** — `portal.js:15464`: `gpSend` chooses
   `args !== undefined ? "POST" : "GET"`. **Fact** — Frappe's `rate_limiter.py:133` returns
   early for a method not in the list. So a mark-all call made with no arguments would be an
   unlimited endpoint that *looks* limited. **Requirement: the call passes an args object
   (even an empty one), and the test asserts the refusal by calling past the limit — not by
   reading the source.**
2. **The existing limit test reads prose, not behaviour.** `test_expense_evidence_081.py:634`
   asserts `methods=["POST"]` appears in `inspect.getsource(fn)`. The decorator line carries
   `limit=60`, but `methods=["POST"]` appears only in the function's **docstring**. So that
   half of the assertion passes on a comment. **Inference — I read both files, I ran
   neither.** Do not copy that shape here.
3. **The refusal must be a sentence, not a stack trace.** `refuse()` goes through
   `frappe.throw`, so the sentence lands in `_server_messages` and the portal's `gpErr` can
   show it (**Fact**, `field_app_errors.py:140–144`). Good as it stands.

**And one honest correction to §1's OPS-9.** OPS-9 said "no new whitelisted endpoint". The
bulk mark-as-read **is** one. OPS-9's intent was *no new **read** endpoint with a
client-supplied filter*, and that still holds exactly. The write endpoint is compatible with
it because it takes **no doctype, no field and no user from the client**: the scope is
`for_user = frappe.session.user` **and** `document_type in NOTICE_DOCTYPES`, both decided
server-side. If the design later lets a chip choose *which* group to clear, the chip's value
must be a fixed name mapped server-side to that filter — never a doctype string. I am naming
the conflict rather than letting §1 read as broken.

### 3.3 · Route rules — restated as a requirement

**Requirement: the notifications page is a hash route inside the existing
`/hrms-employee` page (for example `#notices`). No new web address, and
`deploy/nginx.conf` is not edited in this slice.**

Why, in plain words. **One nginx container serves production `alvoraa.co` and
`dev.alvoraa.co`, and its config is bind-mounted from the single file `deploy/nginx.conf`.**
So a push to `dev` that carries a change to that file changes the **live** site's proxy, and
the deploy restarts that nginx — **Fact**, `deploy.yml:203–211` and `:582–586` say so in
their own comments. There is nothing in this slice worth going near that for.

Two further facts that make the hash route the cheap answer:

- `nginx.conf` names the compressible pages **by exact name** in two server blocks
  (lines 344 and 518). Anything else falls through to `location /`, which has **`gzip off`**
  deliberately (the BREACH note at lines 302–322). A new `/notifications` address would ship
  a ~1 MB page **uncompressed** to a shop-floor phone.
- `www/hrms_employee.py` redirects Guest to `/alvoraa-login?redirect-to=/hrms-employee`
  (**Fact**, read again today). A hash route inherits that sign-in gate; a new page would
  have to repeat it, which is a thing to get wrong.

**If a real page is ever wanted, that is a separate decision with an nginx change behind
it, and `scripts/check_nginx_parses.sh` must pass on the exact file first** — in a throwaway
container, with the result confirmed to have actually run (lesson 19: a zero from a failed
command looks exactly like a zero from a clean file).

### 3.4 · Backups — nothing changes, and ALV-299 is still open

**This slice changes nothing about what must be backed up.** It adds **no DocType, no custom
field, no file, no volume and no new table**. Every row it reads or writes is an existing
`Notification Log` row, already inside `bench backup`'s dump of each site. Retention is
unchanged by this slice — and unchanged means *for ever*, which is OPS-17's point, not this
slice's to fix.

**ALV-299 is still open as far as I can tell: there is no off-server copy of any backup.**
`BACKUP_BUCKET` is unset and each `bench backup` deletes the set older than ~23 hours. I am
quoting slice 081's DevOps and security artifacts (`07-devops-inputs.md` and
`01c-security-privacy-requirements.md`, 3 November 2026), **not** a check I ran today — I
did not probe the server. **Label: Inference from a three-day-old written finding.** It is
**carried, not re-argued**: it does not block this slice, and it should not be made to look
like this slice's problem.

### 3.5 · Monitoring — what to watch, and what must NOT get an alert

**Watch these three for one week after release. None of them is a new alert.**

| What to watch | Where it already shows | Why |
|---|---|---|
| Error Log rows naming `notices` or `inbox_api` | the Desk Error Log, already read after every release | A tenant with an odd role row is the failure mode ALV-250 taught; the bell swallows it, so the log is the only place it appears |
| The portal's existing refusal counters | already collected | If the bulk write starts refusing, it shows as `TOO_MANY_TRIES` in the counters `field_app_housekeeping.py:342` already sums |
| The count and the list agreeing, once, on a real tenant | by hand, once | `inbox_api`'s first rule. A test proves it on fixtures; one human look proves it on real data |

**Explicitly NOT to be added, and this is deliberate:**

- **No alert on `get_nav_counts` or `notices_feed` error rate.** Ruled out in §1's subtract
  pass and still ruled out. Both calls already fail silently and leave the badge as it was,
  so there is no new failure mode — and a new alert is a new moving part that must be tuned,
  owned and upgraded for ever.
- **No new dashboard, no new metric, no new log shipper, no new container.**
- **No alert on the badge number being "wrong".** There is no server-side definition of
  wrong to alert against; the test is the gate, not a monitor.

`nfr-budget.md` §8 asks for named alerts with named owners for failed background jobs,
integration failures and permission-denied spikes. **This slice creates none of those
three**, which is why it earns no alert.

### 3.6 · Secrets — none

**Confirmed: no secret is involved anywhere in this slice.** No credential, no token, no
key, no environment variable, no `site_config.json` entry, no `deploy/server.env` read. The
rate limit's Redis key holds a **SHA-256 hash of the user's email**, never the email itself
(`field_app_limits._hash`, **Fact**) — and nothing in this slice has a secret to hash in the
first place. Nothing in §3 is a secret or a path to one.

### 3.7 · The OPS rows — continuing from OPS-20

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| **OPS-21** | **Written down so nobody adds one later: this slice needs NO queue, NO worker, NO scheduled job and NO `frappe.enqueue`.** If that stops being true, it is a change of shape and must be said out loud before any code is written | Both feeds are read-on-demand; the one write is a single set-based `UPDATE` that finishes inside the request. Nothing here approaches the ≤ 2 s that `nfr-budget.md` §2 sends to a background job, and the measured worst p95 on the calls involved is 215 ms (slice 044, Sep 2026). **Fact** — `hooks.py` `scheduler_events` gains nothing | A UI slice grows an operational tail — a queue nobody watches, a worker nobody listens on, and lesson 1 waiting to happen | **Recommend · P2** | |
| **OPS-22** | **Rate-limit the targeted bulk mark-as-read with the decorator that already exists: `@_limited(SELF_KEY, "user", limit=30)`** — per signed-in user, per hour, POST only, `ip_based=False`. **Leave both reads unlimited.** The call must pass an args object (even an empty one) so it is a POST, and the test must prove the refusal by **calling past the limit**, never by grepping the source | **Fact** — `field_app_limits.py` already does exactly this on seven endpoints (20–240/hour); this is rung 1 of the ladder and one line. **Fact** — `portal.js:15464` sends a no-argument call as a **GET**, and Frappe's `rate_limiter.py:133` skips any method not in the list, so a GET-shaped write would be unlimited while looking limited. The reads need no limit: Home already fires both on every load, so a limit would refuse ordinary navigation | A page-fired write with no ceiling — one stuck loop in one browser writing as fast as the server answers — or, worse, a limit everyone believes in that was never applied | **Recommend · P2** | |
| **OPS-23** | **The page is a hash route inside `/hrms-employee`. `deploy/nginx.conf` is NOT edited in this slice.** If a real address is ever wanted, that is its own decision, and `scripts/check_nginx_parses.sh` must pass on the exact file in a throwaway container first — with the run confirmed, not just its exit code | **One nginx container serves production and dev from that one file** (`deploy.yml:203–211`), so a dev push carrying it changes the live site's proxy **and restarts it**. And `nginx.conf` whitelists compressible pages by exact name (lines 344, 518) — a new address falls through to `location /` where **`gzip off`** is deliberate (BREACH, lines 302–322). The hash route also inherits the Guest redirect in `www/hrms_employee.py` | A ~1 MB uncompressed page on a shop-floor phone, or a dev push that restarts production's proxy — and a sign-in gate re-implemented for no reason | **Recommend · P1** | |
| **OPS-24** | **Record that this slice changes nothing about backups or retention — no DocType, no field, no file, no volume, no table — and that ALV-299 (no off-server copy) is still open and still not this slice's to fix** | Every row involved is an existing `Notification Log` row, already inside each site's dump. **ALV-299:** `BACKUP_BUCKET` unset, each `bench backup` deletes the set older than ~23 hours — quoted from slice 081's artifacts of 3 Nov 2026, **not re-checked today**. `nfr-budget.md` §3 asks for RPO ≤ 1 h, RTO ≤ 4 h and a quarterly restore drill; a backup nobody has restored is a hope | Either this slice gets blamed for a gap it did not create, or the gap goes unmentioned in a release plan and reads as "backups are fine" | **FYI · P2 — carried, not re-argued** | |
| **OPS-25** | **Watch three things for a week after release — Error Log rows naming `notices` or `inbox_api`, the existing `TOO_MANY_TRIES` counter, and one human check that the badge equals the lists on a real tenant. Add NO new alert, NO new metric and NO new dashboard.** The alert on the counts endpoint's error rate stays ruled out | Both calls already fail silently and leave the badge as it was, so this slice adds **no new failure mode** to alert on. `nfr-budget.md` §8 names alerts for failed jobs, integration failures and permission-denied spikes — this slice creates none of the three. A new alert is a new thing to tune, own and upgrade for ever | Either a 2 a.m. page for a hidden badge, or alert fatigue that makes the real alerts ignorable | **Recommend · P3** | |
| **OPS-26** | **Confirmed: no secret, credential, token, key or environment variable is involved anywhere in this slice.** Nothing to store, nothing to rotate, nothing that could reach a log | The rate limit's Redis key holds a SHA-256 hash of the user's email, never the email (`field_app_limits._hash`, **Fact**) — and this slice has no secret to hash in the first place. `deploy/server.env` is not read, and nothing in §3 is a secret or a path to one | A reassurance nobody wrote down gets re-derived at the security gate | **FYI · P4** | |
| **OPS-27** | **Hard requirement, with the number in it: NO `setInterval`, NO `setTimeout` loop and NO polling of either feed, anywhere in this panel, ever. The refresh stays navigation-triggered the way `hmRefreshIfStale` already works.** A later change that adds one is a capacity change and needs its own decision | **Fact** — nothing in the portal polls today; `HM_STALE_MS = 60000` is read only on returning to the panel (`portal.js:6411`, `6567`). **A 60-second poll of the two calls on 441 DTC handsets is 441 × 2 ÷ 60 ≈ 15 extra calls a second, all day** — about **300 extra statements a second** at the measured 21 per call — against roughly zero now (Estimate from the handset count and slice 044's measurement) | The cheapest slice in the quarter becomes the one that needs a capacity conversation, from one line nobody reviewed | **Recommend · P1** | |
| **OPS-28** | **Two test changes, named exactly, so CI does not fail on a stale number.** In `alvoraa_portal/alvoraa_portal/tests/test_notices_076.py`: **line 178, `self.assertLessEqual(big.n, 12)` becomes `14`**, with the reason in the commit message. **Line 177, `self.assertEqual(small.n, big.n)` — the flatness gate — is NOT touched.** `tests/test_scale_flatness_044.py` and `tests/test_inbox_parts_042.py` need **no change** for the count fix. The front-end gates in `ci.yml` this slice will hit are the ones already there: `check_portal_handlers.js`, `check_undefined_js.js`, `check_portal_trays.js --static`, `check_design_system.py`, `check_tag_balance.py`, `check_brand_spelling.py` and the jsdom DOM tests | The true unread count adds exactly two flat statements (§2.1), so the ≤ 12 ceiling is wrong by two while the **property** gate is unaffected. `nfr-budget.md` §2: *"the gate is that the count is the SAME for twenty people as for a thousand; the number itself is a note that makes drift visible"* — raising the note is correct, weakening the property is not. **A new `<button>` and new handlers are precisely what `check_portal_handlers.js` and `check_undefined_js.js` exist to catch** | A red CI on a number everybody knew was going to move, read as a regression — or a later reader seeing 14 as unexplained drift. Worse: `small.n == big.n` quietly relaxed alongside it, and the only real scale defence gone | **Recommend · P1** | |
| **OPS-29** | **Define what "rolled back" means for a front-end-heavy slice, because the obvious answer is wrong.** With no migration in the release, a rollback is **redeploy the previous tag with `run_migrations: false`** — and the tag must exist in the **`alvoraa-app`** package, not the old `hr-app` one. **The workflow fixes the assets by itself; a hand `docker cp` does not.** `get_build_version()` is the **modified time of `sites/assets/assets.json`** (**Fact**, `frappe/utils/__init__.py:944`), and `www/hrms_employee.py` stamps every asset URL with it, while `/assets/` is served `expires 30d; immutable`. `scripts/refresh_bench_files.sh` moves a fresh `assets.json` **last**, so a workflow rollback changes the stamp and every phone fetches the old bundles. **A hand `docker cp` of `portal.js` alone leaves the stamp unchanged, so every browser keeps the cached JS/CSS for up to 30 days** — re-run `refresh_bench_files.sh`, or bump `sites/assets/assets.json`, and prove it from outside **by URL**, never with a server-side `ls` | This is the trap this project paid for twice: dev served the JS of 27 Aug and production the build of 19 Aug for a month (ALV-112), and separately a `docker cp` left every browser on the old bundle (28 Oct 2026). `nfr-budget.md` §3 budgets rollback at **≤ 15 min**; **Measured** 22 Sep 2026 from the run logs, the deploy's wait-for-`bench version` loop burns its full 60 turns (**6 min 54 s on dev, 7 min 09 s on production**) because `bench version` crashes on our image — so budget ~8–10 minutes, not two | A rollback that reports success while every phone still runs the code you rolled back — the most expensive kind of green tick | **Recommend · P1** | |
| **OPS-30** | **The deploy sequence, in the order it must happen, and the dispatch flag that is not optional.** (1) Local: full suite green, including the raised ceiling in OPS-28. (2) `scripts/check_app_integrity.py` with a bench available, before the commit. (3) **Check `gh run list` and let any running CI finish** before pushing — a new push cancels it. (4) Push to `dev` **only on Surbhi's word**, then watch CI. (5) **An automatic Deploy run executes `main`'s copy of `deploy.yml`, not `dev`'s** — so to exercise dev's copy, hand-dispatch: `gh workflow run Deploy --ref dev`. (6) Verify on dev **by pin file, by container and by file**, not by a green tick: every app container reports the same image tag, `.image.dev.env` holds it, and the portal's `?v=` stamp has changed. (7) Surbhi tests on dev. (8) Only then, and only on her word, `main`. **These are written for Surbhi to approve. I have run none of them** | **Fact** — `deploy.yml` triggers on `workflow_run` of "Build Image" for `dev`, `test` and `main`; a `workflow_run` trigger runs the default branch's copy of the workflow, which is why the same dev deploy failed twice identically on 18 Sep 2026. Each stack pins its own file (`.image.dev.env` for dev, `.image.env` for production — `deploy.yml:114`, `:118`). **And the runbook is stale on one point**: `DEPLOYMENT_RUNBOOK.md` §1B still says the automatic deploy cannot fire because `DEPLOY_HOST` is unset; the project's own later lessons say the automatic Deploy does run. **I could not check a repository secret, so treat §1B as out of date, not as reassurance** | A fix to `deploy.yml` on `dev` that does nothing; a green deploy of the wrong tag; or a deploy nobody expected to be automatic | **Recommend · P1** | |

### 3.8 · Requirements the business analyst can trace, in one list

Each line is a user-story-sized operational requirement, with the OPS row behind it:

1. The notifications page is reached by a hash route inside `/hrms-employee`; no new web
   address is added and `deploy/nginx.conf` is unchanged. **OPS-23**
2. The bulk mark-as-read is rate-limited to 30 per user per hour, is sent as a POST, and a
   test proves the refusal by exceeding the limit. **OPS-22**
3. Neither read endpoint gains a rate limit. **OPS-22**
4. No part of the panel polls on a timer; refresh happens on navigation only. **OPS-27**
5. No queue, worker, scheduled job or `frappe.enqueue` is added. **OPS-21**
6. `test_notices_076.py`'s statement ceiling reads 14, and its flatness assertion is
   unchanged. **OPS-28**
7. Nothing new is backed up, and no retention clock changes. **OPS-24**
8. No new alert, metric or dashboard is created. **OPS-25**
9. No secret is introduced. **OPS-26**
10. The release can be rolled back by redeploying the previous `alvoraa-app` tag with
    migrations off, and the asset stamp is proved to have changed by URL. **OPS-29**

### 3.9 · What I could not check

- **Whether `DEPLOY_HOST` is set, and therefore whether a push to `dev` deploys by itself.**
  I cannot read a repository secret and I will not probe. The runbook and the project's
  later lessons disagree; **treat the automatic deploy as live.**
- **Whether ALV-299 is still open.** Quoted from slice 081's artifacts of 3 November 2026,
  not re-checked today.
- **Any timing, on any environment.** I ran nothing against the local bench, dev or
  production in this section. Every millisecond and byte figure in §3 is quoted from §1 or
  §2, with its original date and site.
- **Whether production's scheduler tick is still 3–4 minutes.** Unchanged from §1, and it
  still only affects the wording of a "scheduled for" time.

### 3.10 · What I left behind, and what I ran

**Nothing, and nothing.** No command was run against the local bench, dev or production in
this section. Every file named above was read in this worktree
(`.claude\worktrees\083-ess-notifications`), except `frappe/utils/__init__.py:944` and
`frappe/rate_limiter.py:133`, which were read with `grep` inside the already-running
`hrlocal-bench` container's app folder. No site was opened, no record changed, no setting
touched, no container started or stopped, no throwaway container left running. **OPS-20's
write was not run.** The shared main checkout was not touched.

### 3.11 · Subtract pass

Read §3 once more asking only what I could delete. **Removed:**

- **A separate OPS row for the CI gates this slice must pass.** They are existing gates, not
  gates to add, and gates-to-add belong in §4 Strategy. Folded into **OPS-28** as one
  sentence instead of owning a row.
- **An OPS row proposing a `Notification Log` retention job.** OPS-17 already carries it as
  a separate decision, and repeating it here would create a second owner for one number.
- **A capacity row.** §1 already costed it (~134,000 extra statements a day at DTC, under
  one extra call a second even in the 11 AM burst) and **OPS-27** holds the only thing that
  could change the shape. A second capacity row would have had nothing new in it.
- **A proposed `REHEARSAL.md` migration dry run.** **This slice has no migration and no
  patch** — no DocType, no field, no `patches.txt` entry. A dry run of nothing is theatre.
  If the engineer's strategy adds a patch, this comes straight back as a P1 at §4.
- **A proposed smoke-test addition to the deploy** that fetched the notifications route
  after release. `scripts/check_portal_assets_gate.py` already keeps the deploy's asset
  check honest for the three files the page loads, and the route adds no file — so the new
  step would have asserted nothing the existing one does not.
- **An OPS row on the stale `DEPLOYMENT_RUNBOOK.md` §1B.** It is a documentation fault, not
  this slice's requirement; it is named inside **OPS-30** where it changes the plan, rather
  than becoming work I would then own.

**Kept deliberately, each with a reason:** the timer ban (**OPS-27**) because it is the only
ten-fold run-cost risk in the slice and it is one line away; the rollback definition
(**OPS-29**) because the obvious answer is wrong on this project and has been wrong twice;
and the "no queue, no worker" row (**OPS-21**) because the whole point of §3 is that
somebody later cannot quietly add one.

---

## §4 Strategy — 11 November 2026

Appended. **§1, §2 and §3 above are unchanged.** Numbering continues from OPS-30.

**Answer first: the engineer's strategy is operationally sound and I would not stop it.
Nothing in it needs a new image, a new container, a Compose change or an nginx change — I
checked each one and I confirm it in writing below so nobody adds one.**

**Four things in it are wrong or missing, and all four are cheap:**

1. **The file list is one file short.** A new markup part under `templates/includes/ess/parts/`
   must be given a `PINNED_DEPTH` entry in `scripts/check_tag_balance.py`, or CI fails with
   *"parts/notifications is new and has no pinned depth"*. The engineer's §10.1 says
   "nothing else". **Fact — I read the gate today** (`check_tag_balance.py:242–247`). **OPS-33.**
2. **"No migration" does not mean "no migrate".** The automatic deploy hard-codes
   `migrate=true` (**Fact — `deploy.yml:159`**, read today), so a push to `dev` or to `main`
   runs `bench --site all migrate` with maintenance mode across every tenant, whether or not
   this slice has a patch. My §3 call — that a `REHEARSAL.md` dry run of nothing is theatre —
   **still holds**, but the pre-push check is DTC's job queue, not a dry run. **OPS-32.**
3. **The CI constraint is wider than the engineer found.** `check_design_system.py` is at
   **7 of 7 font sizes _and 3 of 3 border radii_** on this page. **Measured by me today, in
   this worktree** (output below). The engineer named font sizes and colours; the radius
   ceiling is at its limit too, and the badge's ring and the three chips are exactly the
   shapes that want one. **OPS-34.**
4. **The new page's markup is cached server-side for 24 hours**, keyed on the build stamp —
   so there is a shape where the deploy is green, the image is right, and the panel is not
   there. The real deploy is safe (I traced why). A hand `docker cp` is not, and the local
   bench is not. **OPS-36**, and it is the one P1 in this section.

**One more standing-of-evidence point, not a fault: the engineer read Frappe's source inside
`hrlocal-bench`, which runs Frappe 16.33.1. The image and CI pin v16.35.0.** Both facts
measured by me today. Their conclusions are almost certainly right; the line numbers are
from a version production does not run. The fix costs nothing — the behaviour assertions
they are already writing run on CI's bench, which is built on the pinned tag. **OPS-38.**

**No P0. One P1 (OPS-36), three P1-weight process rows (OPS-32, OPS-33, OPS-39).**
Nothing here is dangerous debt. **Nothing is left open for Surbhi except E-6**, answered
in §4.6 with a recommendation she can say yes or no to in one word.

---

### 4.0 · What I read and what I ran, 11 November 2026

**Fact — files read in the worktree `.claude\worktrees\083-ess-notifications` at `814d540f`:**
`docs/slices/083-ess-notifications/00-impact-analysis.md` (656 lines) · `08-dtc-counts.md` ·
my own §1–§3 of this file · `.github/workflows/ci.yml` · `deploy.yml` · `build-image.yml` ·
`deploy/Dockerfile` (the `ARG` block) · `REHEARSAL.md` in full ·
`scripts/refresh_bench_files.sh` · `scripts/check_tag_balance.py` ·
`scripts/check_design_system.py` · `scripts/check_portal_assets_gate.py` ·
`scripts/check_version_pins.py` · `scripts/run_dom_tests.js` · `scripts/lib/portal_source.js` ·
`alvoraa_portal/alvoraa_portal/tests/portal_source.py` · `ess_parts.py` ·
`tests/measure_044.py`, `measure_076.py`, `fixtures_scale_044.py` ·
`docs/slices/044-scale-fixtures/04-test-report.md` · `.claude/context/parallel-work.md` §4 ·
`no-over-engineering.md` · `nfr-budget.md`.

**Measured by me today — five repository gates, run read-only in this worktree. This is the
baseline, so any red after the build belongs to this slice:**

```
$ python scripts/check_design_system.py
page                     palette  loose  undef  sizes  shadows  radii  gradient  emoji
hrms-employee.html             6      0      0      7        0      3         0      0
LIMIT                          -      0      0      7        3      3         0      0
OK - the visual system holds                                          exit 0

$ python scripts/check_app_integrity.py   -> exit 0  "OK - all consistent"
$ python scripts/check_tag_balance.py     -> exit 0  "2 assembled pages, N markup fragments"
$ python scripts/check_brand_spelling.py  -> exit 0
$ python scripts/check_api_paths.py --max 0 -> exit 0
$ python scripts/check_version_pins.py    -> exit 0  FRAPPE_TAG=v16.35.0, ERPNEXT_TAG=v16.36.0,
                                             INDIA_COMPLIANCE_TAG=v16.10.0, CRM_TAG=v1.84.0,
                                             + four pinned commits
```

**Also run by me today, read-only, two commands:**

```
$ git -C C:/Surbhi-Git/hr-app status --porcelain -- <frame.css> <panels.css>
 M alvoraa_portal/alvoraa_portal/public/css/ess/frame.css
 M alvoraa_portal/alvoraa_portal/public/css/ess/panels.css

$ docker exec hrlocal-bench bash -lc 'grep -m1 "__version__" .../apps/frappe/frappe/__init__.py'
__version__ = "16.33.1"
```

**What I did not do.** No bench command, no site opened, no record changed, no cache cleared,
no container started or stopped, nothing against dev or production, no file written outside
this artifact, and **not one byte written to the shared checkout** — the `git status` above is
a read. I started no throwaway container and left none. The `alv318r-*`, `hrlocal-326*`,
`hrlocal-067`, `hrlocal-063-proxy` and `hrlocal-064-demo-proxy` containers were not touched.
**I measured no timing anywhere.** Every millisecond in §4 is quoted from §1/§2 with its
original date, or from slice 044's test report.

---

### 4.1 · Image and Compose changes — none, confirmed in writing

**Nothing in the engineer's strategy touches the image, the stack or the proxy.** I checked
each file that would have to change, and named it, so a later reviewer can diff instead of
wondering:

| File | Changes? | How I know |
|---|---|---|
| `deploy/Dockerfile` | **No** | No new app, no new dependency, no new pip or npm package. The eight `ARG` pins are untouched (**Fact**, read today) |
| `deploy/compose/docker-compose.app.yml` · `.devstack.yml` · `.nginx-multienv.yml` | **No** | No new service, no new volume, no new port, no new environment variable. Nothing in the slice runs outside a web request |
| `deploy/nginx.conf` | **No** | Hash route inside `/hrms-employee` (OPS-4, OPS-23). No new address, no new MIME type, no new header, no new `location` |
| `.github/workflows/build-image.yml` | **No** | No `build-args`, no new pin |
| `.github/workflows/deploy.yml` | **No** | No new asset file, so `check_portal_assets_gate.py`'s "Portal assets must be served" step needs no new name. **Fact** — that gate reads only `/assets/alvoraa_portal/…` addresses the page asks a browser for, and the slice appends to the three files already listed |
| `.github/workflows/ci.yml` | **No** | Every gate the slice must pass is already a step. Nothing to add |
| `hooks.py` · `patches.txt` · any DocType `.json` | **No** | No scheduled job, no patch, no schema |
| `scripts/check_tag_balance.py` | **YES — one line** | A new part file needs a `PINNED_DEPTH` entry. See OPS-33 |

**So the only non-feature file in the whole release is one dictionary entry in one gate
script.** That is worth saying plainly, because "no infrastructure change" has been claimed
on this project before and then quietly grown one.

**Nothing new to run, monitor, patch or upgrade for ever.** OPS-12, OPS-21, OPS-25 and
OPS-26 all stand as written. No new container, job, volume, timer, queue, dependency,
secret or alert.

---

### 4.2 · Migration risk — there is no migration, and the release migrates anyway

**My §3 removed the `REHEARSAL.md` dry run as theatre. That call holds, and I re-checked it
against the engineer's actual strategy, not the spec's:** §10.1 adds no `patches.txt` entry,
no DocType JSON, no Custom Field fixture, no `hooks.py` entry and no schema change of any
kind. There is nothing of ours to rehearse. A rehearsal stack, a DTC dump and a restore to
prove that zero patches run cleanly would cost half a day and prove nothing.

**But the deploy runs `bench --site all migrate` regardless, and that is a different risk
with the same name.** **Fact, read in `deploy.yml` today:** an automatic deploy — the one a
push to `dev` or `main` triggers — sets `migrate=true` at line 159 with no input and no way
to opt out. Only a hand dispatch can set `run_migrations: false`. So this release will:

- put **every tenant** into maintenance mode for the migrate window;
- run every **other** app's pending patches that happen to be waiting, not ours;
- run `bench --site all clear-cache` afterwards — **and only then** (line 571 sits inside the
  `if [ "$MIGRATE" = "true" ]` block, so with migrations off the cache is never cleared. That
  matters for OPS-36, and it is why a rollback is still safe: see below).

**What that means for this release, concretely:**

| Risk | Weight | What I recommend |
|---|---|---|
| A pending patch from another slice runs in this slice's window and fails, and this release is blamed | P2 | Before the push, say out loud which commits are going in. If anything else landed on `dev` since the last deploy, name it |
| The migrate stalls because a tenant's job queue is full | P1 | **This happened on 5 Nov 2026** — 1,780 permission deletes filled DTC's queue, the new image stayed on and later sites were never migrated. Check the queue depth before the push, re-run the migrate if it stalled, and verify **per site**, not by the green tick |
| Maintenance mode refuses biometric posts for about a minute | P2 | **Do not release into DTC's 11 AM punch quarter.** A punch refused during the window is a payroll correction later |
| A rollback with `run_migrations: false` skips `clear-cache` | **not a risk** | Traced: the only site cache this slice depends on is keyed on the build stamp, which `refresh_bench_files.sh` changes unconditionally before any container swaps (`deploy.yml:505`). So the old markup comes back without a cache clear |

**And if the engineer's build turns out to need a patch after all** — a Custom DocPerm row, a
property setter, a field, a data fix, anything in `patches.txt` — **then the dry run comes
straight back as a P1, exactly as §3 said it would.** The shape would be: a `rehearsal` stack
per `REHEARSAL.md` §4, a dump of a site that resembles the target, `bench migrate` watched for
`Orphaned DocType(s) found:` with only `Mode of Payment` acceptable, row counts compared
before and after, then tear down with `-v` and the project name checked twice. That is half a
day. **I do not expect it, and the engineer's strategy says plainly that it is not needed.**

---

### 4.3 · Install order — local, then dev, then main

Each step is one the **user** approves. **I have run none of these.** Where a command is
quoted rather than run, it says so.

#### Local

1. **The front-end gates and the jsdom tests need no bench at all** — they read files. Run
   them **in the worktree**, where the other session's uncommitted CSS cannot reach them:

   ```powershell
   npm ci                                       # there is no node_modules in the worktree today (Fact)
   node scripts/run_dom_tests.js
   node scripts/check_portal_handlers.js
   node scripts/check_portal_trays.js --static
   node scripts/check_undefined_js.js
   python scripts/check_design_system.py
   python scripts/check_tag_balance.py
   python scripts/check_brand_spelling.py
   python scripts/check_api_paths.py --max 0
   ```

   All of the python ones are **green in the worktree today** (§4.0). That is the baseline.

2. **The Python suite needs the bench, and the bench runs the shared checkout's local `dev`**
   (`parallel-work.md` §4: *"The bench runs the main checkout's `dev`"*). So a bench run means
   a `merge --ff-only` into the shared checkout — see §4.5 for the CSS clash and the one check
   that must come first.

3. **Order the commits so the first bench run needs no CSS.** The engineer's own order already
   does this — steps 1 and 2 are `notices.py`, `grooming.py` and the two test files — and it
   is the right order for a second reason: those commits can go to the bench while
   `frame.css` and `panels.css` are still dirty in the shared checkout.

4. **One test run at a time across every session.** Check **both**, because neither alone is
   enough: `docker exec hrlocal-bench pgrep -af run-tests` and `docker ps`. My own
   `alv318r-*` set is running the ALV-318 regression suite right now, so **the bench is busy
   until it finishes**. Claim the board before the run and clear it after.

5. **`scripts/check_app_integrity.py` with a bench available, before the commit** — not just
   the no-bench version CI runs first. The doctype-shadowing half only works with
   `BENCH_APPS_PATH` set.

6. **After editing the new part file, the bench will serve the old markup.** See OPS-36. Bump
   `sites/assets/assets.json` or clear that site's cache, or you will review yesterday's page
   and think the markup is broken.

7. **Browser pass as `ashok.mittal336@ppjewellers.demo` on `ppj.localhost`** (OPS-20, done
   11 Nov). PPJ holds zero notice rows and zero pending approvals, so this proves the layout,
   the empty states and the theme combinations — **not** the filled page. Restart
   `hrlocal-bench` after any `bench use` (lesson 12), and say on the board that you did.

#### dev — only when Surbhi says "push to dev"

8. `gh run list` first and **let any running CI finish**. A new push cancels it.
9. Rebase on `origin/dev`, read every incoming diff, push.
10. **The automatic Deploy runs `main`'s copy of `deploy.yml`, not `dev`'s.** Nothing in this
    slice changes `deploy.yml`, so that is harmless here — but if a deploy misbehaves, a fix
    on `dev` does nothing to the automatic run, and dev's copy is exercised only by
    `gh workflow run Deploy --ref dev`.
11. **Verify by pin file, by container and by file — never by the green tick.** Every app
    container in the dev stack reports the same image tag; `.image.dev.env` holds it; the
    portal's `?v=` stamp has changed. **And the new proof this slice needs:** the delivered
    HTML contains `id="panel-notifications"`. Fetch the page and look. See OPS-36.
12. Surbhi tests on dev.

#### main — only when she says "push to main", after she has tested dev

13. Same sequence. Plus: **not in DTC's 11 AM punch quarter**, and check the job queue first
    (§4.2).
14. **Rollback, unchanged from OPS-29:** redeploy the previous `alvoraa-app` tag with
    `run_migrations: false`, confirm the tag exists **in the `alvoraa-app` package** before
    starting, and prove the asset stamp changed **by URL**, never with a server-side `ls`.
    Budget **~8–10 minutes**, not two: the deploy's wait-for-`bench version` loop burns its
    full 60 turns because `bench version` crashes on our image (**Measured** 22 Sep 2026 from
    the run logs — 6 min 54 s on dev, 7 min 09 s on production). `nfr-budget.md` §3 budgets
    15 minutes, so it fits, but only just.

---

### 4.4 · CI gates — every one this slice must pass, and the mistake each one catches

Every gate below **already exists**. None is being added. The table says which gate would
catch which specific mistake, because a gate list without that is just a list.

| Gate (step name in `ci.yml`) | The mistake it catches in **this** slice |
|---|---|
| **App integrity** · `check_app_integrity.py` — runs **twice**, once without a bench and once with | A `from package import submodule` in the moved `mark_all_seen`, which `bench run-tests` does **not** catch. And, with a bench, a doctype stub shadowing a Frappe one — not a risk here, but it is the run that would find it |
| **Design system** · `check_design_system.py` | **The widest constraint in the slice.** It reads the page with `frame.css`, `panels.css` **and `portal.js` inlined** (Fact — `read_page_source` → `portal_source.py`). So it catches: an 8th pixel font size (7 of 7 today), a **4th border radius (3 of 3 today)**, any hex colour anywhere including inside new **JavaScript** (limit 0), an undefined `var()`, a gradient, an emoji, **and a missing closing brace in any CSS file** — which is how a whole slice's styles once applied only on a phone |
| **The portal pages open and close the same tags** · `check_tag_balance.py` | **A new part file with no `PINNED_DEPTH` entry fails here** (OPS-33). After that, it catches a tag the new panel opens and never closes, and it stops the new fragment silently gaining or losing a tag later |
| **Portal DOM tests (jsdom)** · `run_dom_tests.js` | Three different mistakes. (a) **A new part file the page never asks for** — `portal_source.js` refuses it with *"these markup parts exist but the page never asks for them"*, so a forgotten `{{ ess_part("notifications") }}` line in `www/hrms-employee.html` is caught, which is the engineer's E-4 worry answered. (b) A test file added, renamed or lost — the runner fails rather than running less. (c) The behaviour itself: the badge's single writer, Home and the bell agreeing, the chips firing no request |
| **Portal buttons are wired up** · `check_portal_handlers.js` | The new "Mark all as read" button, the three chips and the sidebar nav item wired to a handler that does not exist. This is precisely what it is for |
| **No undefined identifiers in portal pages** · `check_undefined_js.js` | `ntWorkOwed` or `NT` referenced before it is declared — the most likely slip in a 450–700-line new block inside a 24,000-line file |
| **Trays and dialogs open against the window** · `check_portal_trays.js --static` | The reused `hmLeaveSheet` / `hmExpenseSheet` opened from the new page without being on the window |
| **Front-end API paths resolve** · `check_api_paths.py --max 0` | `notices.mark_all_seen` misspelled, or still pointing at the deleted `grooming.my_notices_seen` after the move (E-3) |
| **No caller's id replaces the employee scope** · `check_scope_traps.py` | A client-supplied `for_user` or employee id reaching the count or the write — SEC-1 and SEC-3's shape |
| **Every screen says Alvora** · `check_brand_spelling.py` | A new user-facing string spelling the brand wrong. Remember "Alvora" with one trailing `a` is **correct** |
| **Semgrep (Frappe security rules)** | Raw SQL or an `ignore_permissions` slipped into `notices.py` |
| **ruff check / format** (`alvoraa_goals alvoraa_portal`) | Formatting on the two Python files |
| **Python tests** · `bench --site test_site run-tests --app alvoraa_portal` | The whole suite, on **a bench built on the pinned Frappe v16.35.0** — which is the right place to prove the four Frappe behaviours the engineer verified on 16.33.1 (OPS-38). **Read both batch summaries**; tailing the output hides a whole batch, usually the bigger one |
| `test_notices_076.py` — **ceiling ≤ 12 → ≤ 14**, flatness line untouched | OPS-28, unchanged. Raising the note is correct; the property gate `small.n == big.n` is the one that must not move |
| **The deploy checks every file the portal loads** · `check_portal_assets_gate.py` | Nothing in this slice — confirmed, no new asset file. Listed so nobody adds a fourth CSS or JS file without noticing this gate exists |
| **Key guard** + gitleaks | Nothing in this slice — no secret anywhere (OPS-26) |

**Two gates that will NOT catch what you might hope:**

- **`check_nginx_parses.sh` never runs in CI.** It runs inside the deploy (`deploy.yml:253`,
  `:395`, `:680`). Irrelevant here because `nginx.conf` is untouched — and that is the
  *reason* it is irrelevant, which is worth stating.
- **`check_version_pins.py` is not wired into any workflow.** **Fact — I grepped
  `.github/` today: the only hit is a comment at `ci.yml:362`.** The gate exists, it passes,
  and nothing runs it. Pre-existing, not this slice's, and recorded as OPS-37.

---

### 4.5 · Is the CSS sequencing plan sufficient? Partly — and the gap is the bench, not CI

**Fact, checked by me today with a read-only `git status` on the shared checkout:** both
`public/css/ess/frame.css` and `panels.css` are modified and uncommitted there.

**The engineer's plan — write prefixed blocks in the worktree, re-read those two files before
any bench run — is sufficient for CI and for every front-end gate, and not sufficient for the
bench run.** Three reasons, in order:

1. **CI is not the exposure.** CI tests committed code. The other session's uncommitted
   edits are invisible to the worktree and to CI, so the worktree is already the right place
   to build, and every front-end gate in §4.4 can run there with no bench and no shared
   checkout at all. That half of the plan is right.
2. **"Does their change overlap my block?" is the wrong question for the bench.** The bench
   runs the shared checkout's local `dev`, so a bench run means
   `git -C C:/Surbhi-Git/hr-app merge --ff-only slice/083-ess-notifications`. Git refuses a
   checkout that would overwrite a locally modified file **whether or not the lines overlap**.
   The right question is **"has that session committed or cleared those two files yet?"** —
   a one-line check, not a diff review.
3. **A refusal is the safe outcome, and the workarounds are the danger.** `git stash`,
   `git checkout .`, `git restore .`, `git add -A` and `git commit -a` in the shared checkout
   all take or destroy the other session's unsaved work, and all five are banned by
   `CLAUDE.md` §1. **The right move when the merge refuses is to stop and ask Surbhi**, which
   is also what `parallel-work.md` §4 step 2 says in so many words.

**What I recommend adding to the engineer's plan — three lines, no new process:**

```powershell
# before any merge into the shared checkout's dev:
git -C C:/Surbhi-Git/hr-app status --porcelain -- `
  alvoraa_portal/alvoraa_portal/public/css/ess/frame.css `
  alvoraa_portal/alvoraa_portal/public/css/ess/panels.css
# non-empty  -> STOP and ask. Do not stash, checkout, restore or add -A.
```

- **Order the work so it does not matter for as long as possible.** Steps 1–4 of the
  engineer's build order are server and `portal.js` only. None of them needs those two CSS
  files on the bench. By the time the CSS has to go in, that session will probably have
  committed. **OPS-39.**
- **One more thing their plan does not cover:** `check_design_system.py` counts braces across
  **every** file under `public/css/**`. So if the other session's half-written CSS lands in
  the shared checkout with an unbalanced brace, the gate fails *there* and reads like this
  slice's fault. Run the gate in the worktree, and if it ever fails in the shared checkout,
  check `git status` before investigating the code (the 3 Nov lesson: **CI red may be site —
  or checkout — state; diff the code path first**).

---

### 4.6 · ⚠ DECISION E-6 — measuring `get_nav_counts` on a "DTC-shaped copy"

**My advice in one line: the measurement is worth having, and I recommend NOT restoring a
copy of DTC to get it. Build it on a throwaway fixture site instead — the question that is
still open is about DTC's _configuration_, not DTC's data, and `08-dtc-counts.md` already
answered the data half.** Surbhi decides; the engineer should not run either version without
her word.

#### What "a DTC-shaped copy" actually means if read literally

The only documented way to make one on this project is `REHEARSAL.md`, and it is **not a
ten-minute job.** Read today, step by step:

| Step | What it really is | The cost or risk |
|---|---|---|
| `bench --site dtc.alvoraa.co backup` on `compose-backend-1` (`REHEARSAL.md` §3) | **A write to the production host** — a dump file, CPU and disk I/O on the live server | **This is the part I would stop at.** `BACKUP_BUCKET` is unset and each `bench backup` deletes the set older than ~23 hours (ALV-299, quoted from slice 081's artifacts of 3 Nov 2026, **not re-checked today**). **Taking this dump rotates out DTC's existing backup.** If a restore were needed in the next day, the copy you rotated away is the one you wanted — for a performance number |
| Disk | A DTC dump of unknown size, then a second database of the same data | **I could not check free disk and I will not probe production.** The deploy has a headroom gate (`deploy.yml:277`); a hand `bench backup` has none. A full disk on this host stopped redis writing its AOF, rq workers quit, and `docker ps` said "Up 12 days" for nine days (10 Sep 2026) |
| `bench restore` into `rehearsal.alvoraa.co` on the same host | **A second copy of 597 real people's HR data**, created for a measurement, which then has to be destroyed | That is a data-processing decision, not an ops chore. It is Surbhi's, and arguably one to mention to counsel given the retention advice already on file |
| Stack up, `migrate`, measure, tear down with `-v` | The project-name trap: the same `down -v` with the live project name destroys production's sites volume | Attended work only, with the variable checked before every enter |
| **Honest total** | | **About half a day of attended work on the production host, with one production write, one backup rotated away, and one copy of personal data to destroy.** Not ten minutes |

**There is a third option I will name and refuse to recommend:** running `measure_044`
read-only against `dtc.alvoraa.co` itself. The instrument is read-only by design
(`measure_076.py`'s docstring: *"Nothing is written while measuring"*), so it is technically
possible. It is still a production probe, it consumes production CPU, and measuring the HR
persona needs `frappe.set_user` impersonation inside the live tenant. **I will not recommend
impersonating a real HR user on production to get a performance figure.** If Surbhi wants it,
it is her call and her word, not mine.

#### What I recommend instead, and why it answers the same question

**The open half of OPS-3 is not "what is DTC's number".** `08-dtc-counts.md` closed the data
half on 11 Nov: DTC holds **zero** rows of all three notice kinds, so the notices side of the
bell is the cheapest possible case there. What is left is `inbox_api.get_nav_counts` under
DTC's **two configuration properties**, and neither needs DTC's data:

- **a pay rule set enabled**, so `_dtc_row_facts` takes its expensive per-row branch on every
  leave row (§1, finding 1);
- **a deep attendance-correction backlog**, so `_part_attendance_fixes`' uncapped read is
  large (§1, finding 2).

**The project already owns every piece needed to build that.** Named, with what each is:

| Piece | What it is | Where |
|---|---|---|
| `fixtures_scale_044.py` | the seed that builds a 1,000-person, 4-company, 16-store tenant through the ORM with validation on; **idempotent** — `is_built(shape)` is one query, so re-running returns in under a second | `alvoraa_portal/alvoraa_portal/tests/` |
| `measure_044.measure_one` | the instrument: every call warmed three times then 20 runs, every statement counted through `frappe.db.sql`, the payload measured as JSON bytes, nothing written | same folder |
| `measure_076.run` | the same instrument already wired to `get_inbox` and `notices_feed` | same folder |

**What I would run — on a throwaway container with its own site, never the shared bench,
never dev, never production. I have run none of this; it is quoted for Surbhi to approve:**

```bash
# 1. a site of its own, built the way CI builds one (ci.yml "Create test site")
bench new-site ops083.localhost --no-mariadb-socket \
      --install-app erpnext --install-app hrms \
      --install-app alvoraa_portal --install-app alvoraa_goals
bench --site ops083.localhost set-config throttle_user_limit 5000   # the seed makes ~70 logins

# 2. the 1,000-person fixture, from the repository
bench --site ops083.localhost execute \
      alvoraa_portal.tests.fixtures_scale_044.build --kwargs "{'shape':'large'}"

# 3. DTC's two properties, which the fixture does NOT have today:
#    (a) enable the pay rule set on the fixture's companies
#    (b) raise the pending-correction count from the seed's 40 to a DTC-shaped number
#        (fixtures_scale_044.py line 84: "corrections": 40)
#    Both are small additions to the existing seed. No new infrastructure, no new file.

# 4. measure, with the instrument that already exists
bench --site ops083.localhost execute \
      alvoraa_portal.tests.measure_044.run --kwargs "{'shape':'large', ...}"
```

**Cost, honestly.** Slice 044's own test report records the build at **about 26 minutes per
site** (980 employees at 46/min ≈ 21 min, plus ≈ 12 min for `bench new-site`) — **Measured by
slice 044, September 2026, not by me.** The measurement itself is minutes. So roughly **an
hour of unattended bench time inside a container that contends with nobody**, plus an hour of
work for steps 3 and 4. Against that: **zero** production touch, **zero** copies of personal
data, **zero** backups rotated away, and a seed that stays in the repository so the next slice
re-runs it for free.

**What a fixture does not give you, said plainly.** It does not reproduce DTC's index
statistics, its real row widths, or the CPU contention on the production box at 11 AM. It
answers *"does the statement count stay flat, and does the shape change, when the pay rule set
is on and the backlog is deep?"* — which is the question OPS-3 asked. It does not answer
*"what is the p95 at DTC"*. **Nothing short of measuring on production answers that, and I am
not recommending it.**

#### And the version that outlasts the number

**A one-off measurement decays; a test does not.** The axis nobody covers is not headcount —
`test_scale_flatness_044.py` holds that — it is **backlog depth**. An assertion in
`test_inbox_parts_042.py` that `get_nav_counts`' statement count does not grow when the
correction queue goes from 40 rows to 400 would hold for ever, runs on every push, and costs
less than the measurement does.

**If only one of the two gets done, do the test.** That is the one place where I part company
with the engineer's framing: they asked for a number, and a gate is worth more. The number is
still worth having, on a fixture, and OPS-40 asks for both with the test first.

---

### 4.7 · Where I agree and disagree with the engineer, item by item

| Their item | My position | Why |
|---|---|---|
| **E-1** · badge digits use `var(--primary-lt)`, no new `--on-primary` token | **Agree, and it is the operationally cheaper answer** | It keeps `design_system.html` — a file **seven pages** include — out of the diff, and it adds nothing to the asset payload. One caution I own: the clamp lives in `brand_color.html`, which renders per tenant, so the four-combination contrast check must include **a tenant with no brand seed**, not only PPJ's black and the Alvora default. The engineer says the clamp covers it; I did not verify the render |
| **E-2** · `ntPaintBadge()` takes no argument; one writer | **Agree. No operational consequence at all** | Fewer writers is fewer failure modes. It changes no call volume, no payload and no permission surface |
| **E-3** · move `my_notices_seen` → `notices.mark_all_seen`, delete the old one | **Agree. One hazard to name, which does not bite here** | Deleting a whitelisted endpoint is safe only because nothing calls it — and I re-confirmed that in §1. The general hazard is the **mixed-version window**: `/assets/` is served `expires 30d; immutable` and stamped with the build version, so right after a release a phone can run **yesterday's `portal.js` against today's server** for the length of its page session. Any endpoint the old JS called and the new server removed would 404 for those people. Here the old JS never called it, so the risk is nil. **Worth writing down because the shape will come back**, and next time it will be an endpoint that *is* called |
| **E-4** · declare the bell in our `frame.html`, move it into Frappe's navbar at boot | **Agree, and I have a second reason they did not give** | Theirs is CI visibility, and it is right — `portal_source.js` and `check_tag_balance.py` only see our own files. Mine is **upgrade safety**: a bell living only inside Frappe's navbar would also be lost silently by a **Frappe pin bump**, and we bump that pin by editing `deploy/Dockerfile`, which no gate connects to the portal's markup. Declared in our file, it survives the bump and the fallback CSS keeps it on screen |
| **E-5** · two CI gates constrain the page | **Agree, and extend it.** Their list is incomplete | **Measured today: `radii` is at 3 of 3**, not just font sizes at 7 of 7. And the gate reads `portal.js` inlined, so **a hex colour in new JavaScript fails the 0-loose-colour limit too**, not only one in CSS. `shadows` has headroom (0 of 3). **OPS-34** |
| Their §10.1 "**Nothing else.** No `patches.txt`, no `hooks.py`, no DocType JSON, no `deploy/` file, no `.github/` file" | **Disagree by one file** | `scripts/check_tag_balance.py` needs a `PINNED_DEPTH` entry for the new part, or CI fails. **OPS-33** |
| Their §10 implication that no migration means no migrate | **Disagree — refine it** | The automatic deploy hard-codes `migrate=true`. **OPS-32** |
| **OPS-1** honoured — the bell calls `get_nav_counts`, never `get_inbox` | **Agree, and this is the disagreement from §1 that stuck.** Keep the fetch-spy assertion on the call **name** | It is the difference between 638 bytes of numbers and colleague names, leave types and claim amounts on every page load |
| **OPS-22** honoured — they found the GET/rate-limiter trap is real and will prove the refusal by exceeding the limit | **Agree, and this is §3's disagreement sticking too** | A limiter that skips a GET looks applied and is not. Proving it by exceeding the limit rather than reading a docstring is the right test |
| **OPS-2** — the two numbers added in the browser | **Agree.** No new endpoint for the sum | Their choice matches my default |
| **OPS-7** not adopted — the per-row `_dtc_row_facts` N+1 is pre-existing and out of slice | **Agree, and I will not re-open it** | It does not reach the bell's number (`count_fn` is one statement). But §4.6's closing point stands: **nothing tests the backlog-depth axis**, and that gap is now on this slice's critical path even though the fault is not |
| Their verification of four Frappe behaviours inside `hrlocal-bench` | **Agree with the conclusions, disagree with the standing of the evidence** | **Measured today: the bench runs 16.33.1; the image and CI pin v16.35.0.** Line numbers from a version production does not run are not evidence about production. The fix is free — their behaviour assertions run on CI's bench, which is built on the pin. **OPS-38** |
| **E-6** · measure on a DTC-shaped copy | **Agree the number is worth having. Disagree with the means.** Fixture, not a restore; and a test before a number | §4.6 |
| Their CSS sequencing plan | **Agree for CI, insufficient for the bench** | §4.5 |

**On the four decisions already accepted (1, 3, 4, 5): I see no operational problem in any of
them, and I am not asking for any of them back.** Items 1 and 3 are cheaper to run than what
they replace. Item 4 removes a whitelisted endpoint without adding one. Item 5 is the only
shape CI can see. Said plainly, as asked.

---

### 4.8 · The OPS rows — continuing from OPS-30

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| **OPS-31** | **Confirmed in writing: no image, Dockerfile, Compose, nginx, `build-image.yml`, `deploy.yml` or `ci.yml` change in this slice. The only non-feature file is one dictionary entry in `scripts/check_tag_balance.py` (OPS-33).** If any of those files appears in the diff, it is a change of shape and must be said out loud before the push | §4.1 checked each file against the engineer's §10.1 and found nothing. No new app, no new dependency, no new service, volume, port, environment variable, job, timer or secret. `check_portal_assets_gate.py` needs no new name because the slice appends to the three asset files already listed and adds no fourth | "No infrastructure change" has been claimed on this project before and then grown one quietly. A `deploy/nginx.conf` line in a dev push restarts the live site's proxy | **Recommend · P2** | |
| **OPS-32** | **"No migration" is not "no migrate" — the release migrates every tenant anyway. Before the push: say which other commits are going in, check the job queue, and do not release into DTC's 11 AM punch quarter.** The `REHEARSAL.md` dry run my §3 removed stays removed — there is nothing of ours to rehearse — **but if the build grows a `patches.txt` entry, a Custom DocPerm row, a property setter or a data fix, the dry run comes straight back as a P1** | **Fact** — `deploy.yml:159`: an automatic deploy (a push to `dev` or `main`) sets `migrate=true` with no input and no opt-out; only a hand dispatch can turn it off. So maintenance mode covers every tenant, every other app's pending patch runs in this window, and `clear-cache` runs at line 571. **5 Nov 2026**: 1,780 permission deletes filled DTC's queue, the migrate stalled, the new image stayed on and later sites were never migrated. Maintenance mode refuses biometric posts for about a minute (26 Oct 2026) | A migrate stalled on a full queue, read as a successful deploy — or a punch refused at 11 AM that becomes a payroll correction | **Recommend · P1** | |
| **OPS-33** | **Add a `PINNED_DEPTH` entry for `notifications` in `scripts/check_tag_balance.py`, in the same commit as the new part file, with a line saying why.** It is missing from the engineer's file list | **Fact — read today**, `check_tag_balance.py:242–247`: a part under `ess/parts/` with no pinned entry fails with *"parts/notifications is new and has no pinned depth. It measures %+d. Add it to PINNED_DEPTH."* The pin then stops the fragment silently gaining or losing a tag in a later merge | A guaranteed red CI on a slice everybody believed was clean, found after the push instead of before it | **Recommend · P1** | |
| **OPS-34** | **Extend the engineer's E-5 constraint: `border-radius` is at 3 of 3 as well as font sizes at 7 of 7, and the gate reads `portal.js` inlined, so a hex colour in new JavaScript fails the 0 limit too.** Every radius in the new badge ring and the three chips must be a `var(--radius-…)`, a percentage, a per-corner value, or one of the three already in use. `shadows` has headroom (0 of 3) | **Measured by me today** in this worktree: `hrms-employee.html` — palette 6, loose 0, undefined 0, **sizes 7 (limit 7)**, shadows 0 (limit 3), **radii 3 (limit 3)**, gradients 0, emoji 0; exit 0. `check_design_system.py` reads the page through `portal_source.py`, which inlines `frame.css`, `panels.css` **and** `portal.js`; a `var()` reference is not counted, a hand-written value is | A red CI late in the build on a visual choice, when a token would have cost nothing — and a scramble to redesign a badge under time pressure | **Recommend · P2** | |
| **OPS-35** | **The new part file may contain no Jinja at all — no `{{`, no `{%`, no `{#`. So no `{{ _("…") }}`.** Every translated string in the panel comes through the JavaScript path, the way the rest of the page does | **Fact** — `ess_parts.py` refuses a part holding a Jinja token rather than rendering it, and **no existing part under `ess/parts/` contains one** (grepped today, all 19 files clean). The reason is in that file's own docstring: Frappe compiles at most 32 templates per worker and this page's chain already uses about 25, so a part is pasted, never compiled | The part is refused at render time and the panel is simply absent — or, worse, Hindi is designed into the markup and has to be rebuilt | **Recommend · P2** | |
| **OPS-36** | **The new panel's markup is cached inside the site for 24 hours, so there is a shape where the deploy is green, the image is right and the panel is not there. After the dev deploy, prove the markup is being served — fetch the page and look for `id="panel-notifications"` — not only that the `?v=` stamp moved.** On the local bench, bump `sites/assets/assets.json` or clear that site's cache after editing the part file, or you will review yesterday's markup | **Fact** — `ess_parts.ess_part` caches each part per site under `ess_part:<get_build_version()>:<name>` for 24 hours, and `get_build_version()` is the **modified time of `sites/assets/assets.json`**. The real deploy is safe: `refresh_bench_files.sh` runs **unconditionally** before any container swaps (`deploy.yml:505`) and moves `assets.json` **last**, so the key changes. Two places it is not safe: **a hand `docker cp`**, which changes no stamp (28 Oct 2026, the same trap for browser JS), and **the local bench**, where nothing bumps it. Note also that `bench --site all clear-cache` runs **only inside the `if MIGRATE` block** (`deploy.yml:571`), so it is not the thing protecting you | A release that reports success while the new page does not exist for up to 24 hours — the most expensive kind of green tick, and the second time this project would have paid for a stamp | **Recommend · P1** | |
| **OPS-37** | **Nothing in this slice touches a pinned version — confirmed by running the gate. Separately, record that `check_version_pins.py` is not wired into any workflow**: it exists, it passes, and nothing runs it. Pre-existing, not this slice's to fix, and not worth a ticket of its own unless a pin ever drifts | **Measured today**: `python scripts/check_version_pins.py` → exit 0, `FRAPPE_TAG=v16.35.0`, `ERPNEXT_TAG=v16.36.0`, `INDIA_COMPLIANCE_TAG=v16.10.0`, `CRM_TAG=v1.84.0` and four pinned commits. **Fact — I grepped `.github/` today: the only hit for the script is a comment at `ci.yml:362`.** No new app, no new dependency, no `build-args` entry, so the eight pins are untouched by this slice | The gate's whole purpose — catching a pin set back to a moving branch, which once left production on v16.34.0 and dev on v16.35.0 from the same branch name — is not actually enforced | **FYI · P3 — acceptable simplification, recorded** | |
| **OPS-38** | **Prove the four Frappe behaviours this slice relies on with assertions in the test suite, not with line numbers from the local bench.** CI builds its own bench on the pinned `FRAPPE_TAG=v16.35.0`, so a test there proves the version production runs. The four are: `db.set_value` with a dict filter is one `UPDATE`; `db.count` applies no permission condition; `Notification Log` pins `for_user` in both doors; the rate limiter skips a non-POST | **Measured today:** `hrlocal-bench` runs Frappe **16.33.1**; `deploy/Dockerfile` and `ci.yml` pin **v16.35.0**. Two patch releases apart. The engineer's conclusions are very probably right and I am not disputing them — but a line number from 16.33.1 is not evidence about the image, and the fix is free because the assertions are being written anyway | A security control argued from a file nobody on the running image has read — and a line-number citation that quietly rots at the next pin bump | **Recommend · P2** | |
| **OPS-39** | **Before any `merge --ff-only` into the shared checkout's `dev`, run `git -C C:/Surbhi-Git/hr-app status --porcelain --` on `frame.css` and `panels.css`. Non-empty means stop and ask Surbhi — never `stash`, `checkout .`, `restore .`, `add -A` or `commit -a`.** Order the build so the first bench runs need no CSS: the server and `portal.js` commits can go to the bench while those files are still dirty. Run every front-end gate and the jsdom tests **in the worktree**, where they need no bench at all | **Fact, checked read-only today:** both files are modified and uncommitted in the shared checkout. The engineer's "re-read and look for an overlap" is the wrong test — git refuses an overwriting checkout whether or not the lines overlap, so the question is whether that session has committed, not whether the hunks collide. A refusal is the safe outcome; the five banned commands are the danger (`CLAUDE.md` §1, `parallel-work.md` §4 step 2). And `check_design_system.py` counts braces across **every** CSS file, so another session's half-written rule fails the gate in the shared checkout and reads as this slice's fault | Another session's unsaved work destroyed — which this repository has rules about because it has happened — or an hour lost investigating a CI red that was checkout state | **Recommend · P1** | |
| **OPS-40** | **⚠ DECISION — E-6. My recommendation: do NOT restore a copy of DTC. Add the backlog-depth assertion to `test_inbox_parts_042.py` first, then measure `get_nav_counts` on a throwaway fixture site built from `fixtures_scale_044.py` with DTC's two configuration properties switched on — a pay rule set enabled and the correction count raised from the seed's 40.** Never the shared bench, never dev, never production. Full commands and costs in §4.6 | `08-dtc-counts.md` already closed the data half (DTC holds **zero** rows of all three notice kinds). What is open is DTC's **configuration**, and that needs no DTC data. The literal route costs **a write to the production host, DTC's existing backup rotated away** (`BACKUP_BUCKET` unset; each `bench backup` deletes the set older than ~23 h), **a second copy of 597 people's HR data to destroy**, and about half a day attended — against **≈1 hour of unattended bench time** in a container that contends with nobody. **Measured by slice 044, Sep 2026: ~26 min to build one 1,000-person site.** And a one-off number decays where an assertion holds for ever | Either the one call now on every page ships having never been measured where it runs — or a tenant's data copied and a backup rotated away to get a figure a fixture would have given | **⚠ DECISION · Recommend · P1** | |

---

### 4.9 · What I could not check

- **Any timing, anywhere.** I measured no milliseconds in §4. Every performance figure is
  quoted from §1/§2 with its original date and site, or from slice 044's test report.
- **Free disk on the production host.** It decides whether the E-6 restore route is even
  possible, and it is the thing that caused the 10 Sep 2026 outage. **I will not probe
  production.**
- **Whether ALV-299 is still open** (no off-server backup copy; each `bench backup` rotates
  the previous set). Quoted from slice 081's artifacts of 3 Nov 2026, **not re-checked**. It
  is the fact OPS-40's strongest argument rests on, so if it has changed, that argument
  weakens.
- **Whether the fixture sites `test044` / `test044s` / `test076l` still exist** on any bench.
  Checking needs a bench command and the bench is busy with another session's run. If they
  are gone, `fixtures_scale_044.py` rebuilds them from the repository — that is the ~26
  minutes in OPS-40, and it is why the number is quoted as a rebuild rather than a reuse.
- **Whether `brand_color.html`'s clamp really runs for a tenant with no brand seed.** I read
  the engineer's reasoning and did not render the page. It is a design-check item, not mine.
- **Whether `DEPLOY_HOST` is set**, i.e. whether a push to `dev` deploys by itself.
  Unchanged from §3: I cannot read a repository secret. **Treat the automatic deploy as
  live** — which is what makes OPS-32's `migrate=true` matter.

### 4.10 · What I left behind

**Nothing.** Five gate scripts run read-only in this worktree, two read-only commands
(`git status` on the shared checkout, and a `grep` of one file inside the already-running
`hrlocal-bench` container), and this artifact. No bench command, no site opened, no record
changed, no cache cleared, no container started or stopped, no throwaway container, no
`npm ci` run, nothing against dev or production, and not one byte written to the shared
checkout. **Nothing in §4 is a secret or a path to one.** Every recommendation above is
advice with the Decision column blank.

### 4.11 · Subtract pass

Read §4 once more asking only what I could delete. **Removed:**

- **A full §5-style release plan** — the rollout table, the post-deploy check list, the
  monitoring plan and the capacity note. They belong in §5 Release readiness, and writing
  them now would create two versions of one plan. §4.3 keeps only the **order**, which is
  what this stage is for.
- **A proposed smoke-test step in `deploy.yml`** that fetched the notifications route after
  release. Deleted twice over: §3 already removed one for the same reason, and OPS-36's
  one-line proof (look for `id="panel-notifications"` in the delivered HTML) does the same
  job with no workflow edit — which is the whole point of OPS-31.
- **An OPS row recommending `pull_policy: always` in the compose files** so a rollback could
  not serve a stale local image. I had written it, then checked: the deploy pulls explicitly
  with a six-attempt retry loop (`deploy.yml:485`), so the row would have added a permanent
  setting to protect against nothing.
- **An OPS row asking for `check_version_pins.py` to be wired into `ci.yml`.** It is a real
  gap and it is not this slice's. Folded into **OPS-37** as a recorded FYI rather than
  becoming work I would then own — the same treatment §3 gave the stale runbook section.
- **A proposed `PINNED_DEPTH` self-test addition.** The script already has a `--self-test`,
  and CI already runs it. I was about to recommend proving a gate that is already proved.
- **A second measurement row** asking for the new count's p95 separately from
  `get_nav_counts`. **OPS-40** covers both in one run, and §2 already deleted this exact row
  once for the same reason. A second owner for one number is how numbers go stale.
- **A capacity paragraph** restating the 134,000-statements-a-day estimate. §1 costed it,
  OPS-27 holds the only thing that could change it, and nothing in the engineer's strategy
  moves either figure.

**Kept despite the pass, each with a reason:** the one-line `check_tag_balance.py` finding
(**OPS-33**), because it is a certain CI red and nobody else has it written down; the
server-side part cache (**OPS-36**), because it is the only way this release can be green and
invisible at the same time; the `migrate=true` fact (**OPS-32**), because "this slice has no
migration" is true and misleading in the same breath; and the fixture-not-a-restore
recommendation (**OPS-40**), because the difference between the two is a production write and
a copy of 597 people's data.

---

**Written by `hrms-devops-engineer`, 11 November 2026. Advisory only. Nothing deployed,
nothing measured on dev or production, nothing changed on the shared bench. I recommend;
Surbhi decides.**
