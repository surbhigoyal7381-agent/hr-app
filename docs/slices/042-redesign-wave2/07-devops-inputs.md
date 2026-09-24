---
slice: 042-redesign-wave2
artifact: 07-devops-inputs
author: hrms-devops-engineer
date: 2026-09-24
status: draft — §3 (requirements) and an early §4 (strategy). §5 (release readiness) is written when the build is done
inputs: [02-functional-spec.md revision 1, ../034-redesign-wave1/07-devops-inputs.md (OPS-1 to OPS-19 and §3b), ../034-redesign-wave1/03-implementation-notes.md §4, .claude/context/nfr-budget.md §1 §2 §3 §8, deploy/nginx.conf, deploy/compose/docker-compose.app.yml, deploy/Dockerfile, .github/workflows/deploy.yml, scripts/refresh_bench_files.sh, alvoraa_portal/.../www/hrms-employee.html and hrms_employee.py (OPS-31 work in progress in the 034 worktree)]
---

# Wave 2 — Home and Inbox: DevOps inputs

**I advise. Every Decision column below is blank and is Surbhi's.** I changed no code,
ran nothing on any server, and touched no bench. Everything here is either read from a
file in this repository, quoted from Wave 1's measurements, or labelled as an estimate.
The list of what I did and did not check is at the end.

Item IDs are `OPS-W2-n`, so they cannot be confused with Wave 1's `OPS-1` to `OPS-19` or
with slice 012's `OPS-26 / OPS-31 / OPS-33 / OPS-34`.

---

## Read this first — the three that stop the build

**1. Wave 2 must not add a fifth include file, and today it has no free slot at all.**
Wave 1 measured the cliff over real HTTP: four include files cost +1.1 %, five cost
+97 %, twenty-four cost +565 % (034 `03-implementation-notes.md` §4, measured 2026-09-23).
It is a step, not a slope. Until OPS-31 lands, every line of Wave 2's markup, style and
script has to go inside Wave 1's existing four files. **Fact**, read in the notes.

**2. OPS-31 must not reach production before ALV-112's asset refresh reaches `main`.**
`scripts/refresh_bench_files.sh` does not exist on `origin/main`, and `main`'s copy of
`.github/workflows/deploy.yml` mentions it **zero** times (**Fact**, checked with
`git cat-file` and `git show origin/main:...` today). OPS-31 moves the portal's style and
script out of the HTML and into `/assets/`, which are served from the **sites volume**,
and the volume is exactly what a deploy does not refresh. A production deploy today would
put the new HTML in front of August's stylesheet and August's script. The page would not
error; it would simply be a month old, and the `?v=` stamp would be a month old with it,
so nothing on screen would say so. **This is the ALV-112 trap, aimed straight at OPS-31.**

**3. There is no measured number for either tenant shape.** Wave 1 measured page render
time and bytes. Nobody has measured `get_frame`, `get_nav_counts`, page load or query
counts at 1,000 employees or at a 20-person store. **I could not check that** — there is
no fixture and no recorded run. Wave 2's budgets in spec §13 are therefore targets that
have never been tested against anything. §3.5 says what to measure and against what.

---

## §3 Requirements · 2026-09-24 · hrms-devops-engineer

### 3.1 The Jinja cliff — what Wave 2 may and may not do before OPS-31 lands

**Why the cliff exists, in one paragraph.** Frappe builds its Jinja environment with
`cache_size=32` — at most 32 compiled templates per worker process, shared by every page
that worker serves (`frappe/utils/jinja.py`, read by the engineer on the local bench,
034 §4). The portal page's chain already uses about 27 of them. Each include file takes
one more slot. Past 32 the cache throws templates out on every request, so the whole
million-byte page is compiled again on every visit.

| Wave 2 may | Wave 2 may not, before OPS-31 |
|---|---|
| Build `home_api.py`, `inbox_api.py`, the `parts()` helper, the queries, the tests and the fixtures — none of it is a template | **Add any new file under `templates/includes/ess/`.** The fifth file is the worst place to stand: Wave 1 measured the same five-file split at +5 % once and +45 % to +97 % three other times. An unpredictable page is harder to live with than a slower one |
| Edit the contents of the existing four files | **Move the existing drawers into a shared sheet** if that adds a file (spec §12 already defers this) |
| Edit `markup.html` and the script file, accepting that Wave 3 will be editing the same two files at the same time | **Assume the split protects you.** `script.js.html` is 13,441 lines; two sessions in it collide exactly as they did before Wave 1 |

**My recommendation, plainly: do not start Wave 2's panel markup, style or script until
OPS-31 is on `dev` and measured.** That is the same answer the analyst gives in 042 D-6
and 043 D-5 and the same answer the engineer gives in 034 §4. Server-side work can start
today and is not affected.

**What OPS-31 buys, and a place where I disagree with the engineer in writing.**
034 §4 says that once the style and script become static files, "the remaining markup
could then be split as finely as anyone likes for free". **Inference, and I think it is
wrong:** markup includes are still templates and still take slots. OPS-31 removes three
template files (`frame.css.html`, `panels.css.html`, `script.js.html` — confirmed by the
staged renames in the 034 worktree today). Four files fitted and five did not, so the
chain sits right on the edge at about 28 of 32. Removing three files frees about **three**
slots, not an unlimited number. So after OPS-31 the two waves together get roughly three
or four new include files, shared between them — enough for one Home file, one Inbox file
and one Time-or-Pay file, and then the cliff is back. **Measure the real number before
planning the fine-grained split** (§3.3, OPS-W2-4).

### 3.2 How we would know OPS-31 did not actually fix it

Four measurements. None of them exists today. Each says what, on what, against what
number, and who looks.

| # | Measurement | On what | Pass line | Who looks, and when |
|---|---|---|---|---|
| **M1 · server render time** | 25 warm signed-in GETs of `/hrms-employee`, `curl -w %{time_starttransfer}`, median and p95, before and after in the same window | Local bench first; then dev after the deploy, on Surbhi's say-so | Median no worse than Wave 1's pre-split baseline **0.174 s plus 10 % = 0.191 s**, and **no single warm sample above 0.30 s**. 0.343 s was the five-file cliff | Engineer records it in `03-implementation-notes.md` with date and commit; I re-measure on dev at release readiness |
| **M2 · the free-slot count — the early warning** | After one page render, read how many templates the worker's Jinja environment is holding (`len(frappe.get_jenv().cache)`) and the installed `cache_size` | Local bench, one `bench execute`, **capturing stdout and stderr** (lesson 8: `bench execute` swallows the real error and prints its own) | The page's chain leaves **at least 3 free slots of 32** | Engineer, once, at the OPS-31 commit. This is the number the CI gate in §3.3 is then built on |
| **M3 · variance, not just the median** | The same 25 samples as M1 | Local bench and dev | **p95 ÷ median ≤ 1.5.** Eviction shows up as instability before it shows up in the median | Engineer, same run |
| **M4 · did OPS-31 take effect on this environment at all** | Bytes of the HTML on the wire for `/hrms-employee`, and the `?v=` value on two consecutive loads | Local bench, then dev, then (on the day) production from an ordinary signed-in browser | HTML **≤ 250 KB uncompressed** (estimate: 1,043 KB minus 702 KB of script and 159 KB of style ≈ 182 KB, plus the new link and script lines). **And the `?v=` value must be the same on two loads in a row** | Engineer locally; me on dev; Surbhi's browser on production |

**M4's second half is the one people will skip, and it is the one that silently undoes
OPS-31.** `asset_version` comes from Frappe's `get_build_version()`, which is the modified
time of `sites/assets/assets.json` — **and when that file is missing it returns a random
eight-character string instead** (read today on frappe's `version-15` and `version-16`
branches on GitHub; confirm on our v16.33.1 bench). A random stamp on every request means
every phone downloads the half-megabyte script on every visit, for ever, and the page
still looks perfect. Two loads, same `?v=`. That is the whole test.

### 3.3 How the limit is defended permanently

Timing gates are flaky and nobody re-runs them. **A counting gate is deterministic and
runs on every commit.** Recommend `scripts/check_template_budget.py`, using the expander
Wave 1 already built (`alvoraa_portal/tests/portal_source.py`), that:

1. counts the template files the portal page's chain pulls in;
2. reads `cache_size` out of the installed Frappe rather than trusting a comment;
3. fails the build when the count leaves fewer than three free slots;
4. holds the ceiling in **one constant**, which 042 AC-44 and 043 AC-44 both import, so
   the number moves in one place when OPS-31 moves it.

Without it, Wave 4 or Wave 5 adds the file that walks back over the cliff, the page gets
about 250 times more expensive to render, and every check in CI still passes.

### 3.4 Query count, payload size, and the N+1 risks in a Home screen

**Home is the tenant's landing page and it assembles seven things at once.** That is the
classic place a query lands inside a loop. The spec's budgets (§13) are the right shape;
they need a payload budget beside them, because there is none anywhere in
`nfr-budget.md`.

**Numbers updated 24 Sep 2026.** The query column was an estimate in every row; slice
044 measured it on a 981-person and a 20-person tenant, and slice 044's R1/R4 fixes then
moved it. What is written below is what was measured after the fixes, on both sites, and
it is the same on both. The payload column was an estimate too — it is measured now, and
it is nowhere near its budget.

| Endpoint | Queries — measured, worst persona | Payload — budget | Payload — measured at 981 |
|---|---|---|---|
| `get_frame` (Wave 1) | **5** (HR personas), 3 otherwise — *was ≤ 15* | ≤ 4 KB | 1,368 B |
| `get_nav_counts` | **21** (store HR, company HR) — *was ≤ 15, measured 23 before the fixes* | ≤ 1 KB | 638 B |
| `get_home` | **28** (System Manager) — *was ≤ 20, measured 30–31 before the fixes, at both tenant sizes* | ≤ 30 KB | 1,470 B |
| `get_inbox` | **26** (store HR, company HR) — *was ≤ 25, measured 26–28 before the fixes* | ≤ 60 KB at the 50-row cap | 18,351 B |

The gate is **flatness**, not these numbers: every one of them is identical for twenty
people and for 981, and that is what the tests assert. See §13 of the spec.

**The N+1 risks, named so the engineer can write the assertion rather than hunt the bug:**

| Where | The trap | The shape that is safe |
|---|---|---|
| The six count parts | one query per part is fine; one query **per row** to fetch an employee's name, an approver's name or a leave type is not | one `get_all` per part with an `in` filter, then **one** name-resolution query for every id on the page |
| Attendance gaps (spec §11) | a query per day of a two-month window — 60 queries for one card | one query per source doctype for the whole date range, then the rule applied in Python |
| The team goal summary | one goals query per report — 19 for Sandeep, up to 1,000 for company-wide HR | one grouped query over `employee in (...)` |
| The peer card | one check-in lookup per peer | one query over the peer ids |
| Policies to acknowledge | one acknowledgement lookup per policy | `readable_policy_names()` once, acknowledgements once |
| `_pending_approvals_scope` | this is the helper the old bell used, and the old bell took **16.4 s for HR** because it walked one employee at a time (spec §2, confirmed in source) | set-based, and asserted at 1,000 employees, not at 250 |

**One thing in the spec that costs double and nobody has noticed.** Spec §8 puts `counts`
inside `get_home`'s payload "so Home need not make a fourth call" — but the frame already
calls `get_nav_counts`, which computes the same six parts. So **every Home load counts the
six parts twice**, and those are the most expensive queries on the page. Either Home drops
`counts` from `get_home` and reads the badge's number, or Home skips `get_nav_counts` and
the frame takes its number from `get_home`. Two calls, not three (OPS-W2-6).

### 3.5 What a 1,000-employee tenant does, and what a 20-person store does

**Wave 1 measured neither. Neither shape exists as a fixture.** Both matter, for opposite
reasons.

**At 1,000 employees** the risk is fan-out: company-wide HR is in scope for everybody, so
every count part and the team summary are queries over a thousand rows, run on the landing
page, for the person who opens it most often.

| Measure | On what | Against |
|---|---|---|
| Query count and p95 for `get_nav_counts`, `get_home`, `get_inbox` | **Done** (slice 044): sites `test044` (981 people, 4 companies) and `test044s` (20 people), five personas, 20 warm calls each | **the same count on both sites** — measured, for every call and every persona. The counts themselves are 21 / 28 / 26 worst case, which replaces the spec's original 15 / 20 / 25. p95 worst **215 ms** against **≤ 500 ms** (`nfr-budget` §2) |
| The same, with **50 open requests per approver** | the same fixture | queries must not move with the row count — that is the assertion, not the timing |
| Home usable, p95 | the W1D-09 rig (Chrome Slow 4G, 4× CPU slow-down) | **≤ 2.5 s** (`nfr-budget` §2), with slice 036's compression live |
| Concurrency | 20 signed-in Home loads at once against the local bench | production's web tier is **gunicorn, 4 workers × 2 threads = 8 requests at a time**, one backend replica (**Fact**, `deploy/compose/docker-compose.app.yml` line 223). `nfr-budget` §1 designs for **300 concurrent users**. Three calls per Home load, times a 09:30 shift-start spike, is the load event nobody has sized |

**At a 20-person store** the risk is not size. It is two other things.

1. **The nginx rate limit is keyed on the IP address, and a store is one IP address.**
   `limit_req_zone $binary_remote_addr zone=kinexus_api rate=120r/m` with
   `burst=30 nodelay` on `location /api/` (**Fact**, `deploy/nginx.conf` lines 70 and 270).
   Twenty people opening Home within a few seconds of the shift bell, at three API calls
   each, is **60 requests from one address**; 30 are absorbed by the burst and the rest are
   refused. The same applies to a fleet of phones behind a mobile carrier's shared address.
   **Inference from the config, not measured.** Measure it: count the API calls one Home
   load makes and one five-minute session makes, then decide. Changing the limit means
   editing `deploy/nginx.conf`, which is the one file the single nginx serves **both** dev
   and production from (lesson 13), so it is its own slice with the `nginx -t` gate — never
   a line inside Wave 2.
2. **Every empty and small state is the normal state.** No shift assigned, no holiday list,
   no payroll, a manager who is also HR and is their own approver, and a peer group under
   five where the spec's small-group rule hides the numbers. A 1,000-employee fixture never
   reaches these. Measure nothing; **test everything** — spec §9's table against a 20-person
   fixture.

### 3.6 Caching — what may be kept, for how long, and what clears it

**Wave 1's rule stands and must not be softened: the portal page is not cached.**
`context.no_cache = 1` is set in `hrms_employee.py` (**Fact**, read today, line 12).
Frappe otherwise keeps a `www` page's finished HTML for 30 minutes, **keyed by address
only, not by user**, and serves it before `get_context` runs. On a page that draws one
person's work queue, that is one employee's Home handed to the next person who opens it.

| Thing | May it be cached? | For how long | What clears it |
|---|---|---|---|
| The portal HTML | **No** | — | `no_cache = 1`, pinned by a test |
| Any endpoint answer, anywhere shared (Redis, a module-level dict, a file) | **No** for anything that varies by person: counts, rows, leave balances, gaps, the team summary | — | — |
| Within **one request**: the caller's Active Employee row, their shift row, their holiday rows | **Yes** — plain local memoisation, which is not a cache | the request | it ends with the request |
| Tenant-wide settings everyone shares: Holiday List rows, Shift Types, late-rule settings | **Consider**, in Redis, **keyed by site** | ≤ 5 minutes | a `doc_events` hook on those doctypes. If that hook is not written, do not add the cache |
| Browser caching of API answers | **No.** Assert `Cache-Control: no-store` on the portal's `/api/method/...` answers. **I could not check this today** — it needs a signed-in session | — | — |
| **Payslip data** | **Never, anywhere shared.** Not in Redis, not in a module variable, not in an nginx cache, not in the browser. That is Wave 3's screen, named here because a "let us just cache the counts" change in Wave 2 is how a shared cache first appears | — | — |

**No module-level dict, list or set that changes at run time** — the spec already says so
(AC-42), and it matters here for a reason beyond correctness: production runs **4 gunicorn
worker processes**, so a module-level cache is four caches that disagree, and it lives
across users inside one process.

### 3.7 Static asset delivery after OPS-31, and proving the deployed files are the new ones

**How it is wired today** (all read in this repository, 2026-09-24):

- The page links `/assets/alvoraa_portal/css/ess/frame.css?v={{ asset_version }}` and
  `/assets/alvoraa_portal/js/ess/portal.js?v={{ asset_version }}`.
- `asset_version` is `frappe.utils.get_build_version()` — the modified time of
  `sites/assets/assets.json`, or **a random string when that file is missing** (read on
  GitHub today, `version-15` and `version-16`; confirm on our v16.33.1).
- nginx serves `/assets/` from the **sites volume** with `expires 30d;` and
  `Cache-Control: public, immutable` (lines 207–211 for production; dev has its own volume
  at lines 391–395).
- gzip is on for `text/css` and `application/javascript`, `gzip_min_length 1024`, level 5,
  `gzip_vary on`; **`gzip_static` is deliberately off** because Frappe's build writes no
  `.gz` files (lines 85–113, live since 2026-09-23).
- The image runs `bench build --production --app alvoraa_portal` and then
  `scripts/materialise_assets.sh`, so the image ships real files, not symlinks
  (`deploy/Dockerfile` steps 4 and 4b).
- `deploy.yml` on **`dev`** runs `scripts/refresh_bench_files.sh` straight after the pull
  and before any container swap (line 497). **`main` has neither the script nor the call.**

**What that adds up to.**

| Good | Risk |
|---|---|
| `immutable` plus a per-release `?v=` is the right pairing. A phone cannot keep last release's code, and it does not re-ask for a file it already has | `immutable` on a **path that never changes** is unforgiving. If the `?v=` stamp ever stops moving, the wrong file is stuck on a phone for **30 days** and no reload clears it |
| gzip already covers the new files. About 700 KB of script leaves the HTML and becomes one cached download per release | No `gzip_static`, so nginx compresses about 500 KB of JavaScript again for **every** cold request. A release morning across a whole tenant is the worst case. **Estimate**, not measured |
| The refresh script is careful: bundles first, manifest last, safe to run twice, refuses a volume that is not a sites volume | It is **not on `main`**, so the deploy that matters most does not run it |

**Proving the deployed assets are the ones just built — the exact steps.**

*Best check, and it needs no server access.* The two CSS files and the JS file live under
`public/` and are copied rather than bundled, so the served file should be
**byte-identical to the file in the repository at the deployed commit**.
`[ASSUMPTION]` — confirm once on the bench that `bench build` copies non-bundle files under
`public/` verbatim; if it rewrites them, use the image-side check below instead.

```
# after a deploy, from anywhere
curl -s https://dev.alvoraa.co/assets/alvoraa_portal/js/ess/portal.js | sha256sum
git show <deployed-commit>:alvoraa_portal/alvoraa_portal/public/js/ess/portal.js | sha256sum
```

*Second check, on the server, read-only, and only when Surbhi asks:*

```
docker run --rm --entrypoint sha256sum <image> \
  /home/frappe/frappe-bench/sites/assets/alvoraa_portal/js/ess/portal.js
docker run --rm -v <stack>_sites:/vol alpine \
  sha256sum /vol/assets/alvoraa_portal/js/ess/portal.js
# and the manifest's date, which is what the ?v= stamp is made of
docker run --rm -v <stack>_sites:/vol alpine stat -c %y /vol/assets/assets.json
```

*Third check, from a browser, which is what a non-engineer can do:* open the portal, read
the `?v=` on the stylesheet link, compare it with the last release's value, then reload
once and confirm it did **not** change between two loads.

**Recommend all three become one script, `scripts/check_assets_deployed.sh`, run as a
deploy gate** — the same shape as `scripts/check_nginx_parses.sh`. A stale asset is
invisible by design: the page renders, nothing errors, and the product is a month old.
That is exactly how ALV-112 went unnoticed for four weeks. And remember lesson 19: on Git
Bash a mistyped `docker run -v /tmp/...` mounts nothing and the command still exits zero.
**Confirm the check ran before you believe its result.**

**One release-model change nobody has written down yet.** Wave 1's OPS-5 said no step needs
`bench migrate` or `bench build`. **After OPS-31 that is no longer true for style and
script.** A change to `portal.js` reaches a browser only if the image is rebuilt (the
Dockerfile's `bench build`) **and** the volume is refreshed (ALV-112). Three consequences:
the release always needs a new image, never a config nudge; a rollback must roll the assets
back too — the refresh script runs on a rollback deploy as well, because it sits right
after the pull (**Fact**, `deploy.yml` line 497 on `dev`); and the **local bench
development loop changes** — an edit to `portal.js` will not show up until the file is
visible under `sites/assets`. The engineer should check that at the first OPS-31 bench
test, before a day is lost to "my change does nothing".

---

## §4 Strategy, early · the release plan and the rollback

### 4.1 Order of release

| # | Step | Why it is here |
|---|---|---|
| 1 | ALV-112's refresh step reaches **`main`** | Otherwise no production deploy refreshes assets. Lesson 14: the automatic Deploy runs **`main`'s** copy of the workflow. Exercise dev's copy with `gh workflow run Deploy --ref dev` |
| 2 | **OPS-31** on `dev`, with M1–M4 recorded | Wave 2's build order depends on it (D-6), and so does Wave 3's |
| 3 | Wave 1's swap, under its five agreed conditions (034 §3b) | Unchanged |
| 4 | Wave 2 built and on `dev` | Panels only after step 2 |
| 5 | Wave 2 to production, **in a release of its own** (Wave 1's OPS-16) | A rollback rolls back the whole image, not one commit |

### 4.2 What a Wave 2 deploy needs

| | Answer |
|---|---|
| `bench migrate` | **No.** No doctype, no field, no patch (spec §14) |
| `bench build` | **No new need from Wave 2 itself** — but the image is rebuilt anyway, and after OPS-31 the built assets must reach the volume (§3.7) |
| `bench clear-cache` | Only if someone opened a new route before the file existed: Frappe remembers "not found" in Redis across deploys (034 §4.2). The narrow command is `bench --site <site> clear-website-cache`, and it needs approval |
| Compose, image, nginx | No change. **Wave 2 must not touch `deploy/nginx.conf`** — one nginx serves dev and production from that one file |
| New queues or workers | None. Nothing in Wave 2 takes over 2 s (spec §13) |
| Pinning | Nothing new to pin |

### 4.3 Rollback

**Redeploy the previous image tag with migrations off — about 10 minutes of machine time,
12–15 from the moment someone decides.** Measured by me on dev on 2026-09-22: 9 min 33 s,
of which **6 min 54 s is the deploy waiting for `bench version`, which never succeeds on
our image** (Wave 1's OPS-15, still open). Production has not been timed with migrations
off; **estimate 9–11 minutes**.

The command, **for Surbhi to approve and run** — I do not run it:

*Actions → Deploy → Run workflow* · `environment: production` ·
`image_tag: <the tag production ran before this release>` · `image_package: alvoraa-app` ·
`run_migrations: false`.

Three things to do before the release, not after:

1. **Write the previous production tag down** and check it still exists in the
   `alvoraa-app` package. Production pulls only during a deploy; a tag you cannot pull is
   not a rollback.
2. **No pushes to `dev` in the hour after** (Wave 1's OPS-19). There is one runner and it
   runs one job at a time.
3. After the rollback, run the asset check from §3.7. A rollback that leaves the new assets
   in the volume behind the old HTML is the ALV-112 failure in reverse.

### 4.4 After the deploy — what to look at

Disk headroom **before** the pull (lesson 16: a full disk breaks redis, kills the workers
and defeats `restart: unless-stopped`); `docker top` and the rq worker registration, never
`docker ps` alone (lesson 15); `scripts/check_workers.sh`; the page over HTTP with M1 and
M4 from §3.2; the asset check from §3.7; and the Error Log count for `home_api` and
`inbox_api` in the first hour. `nfr-budget` §8 asks for a **named alert with a named
owner** on a response-time breach. Wave 2 makes the portal's landing page the page every
employee opens every morning, so this is the slice where that alert should start existing.

---

## OPS items

Every Decision is blank and is Surbhi's.

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| **OPS-W2-1** | **OPS-31 lands on `dev`, with M1–M4 recorded, before any Wave 2 markup, style or script is written.** Server-side work starts now | Four include files is the whole budget, and it is spent. The fifth costs +97 % and is unstable | Either Wave 2 has no file of its own and two sessions fight over a 13,441-line script, or somebody adds the fifth file and the landing page gets about 250 times more expensive to render | **Require · P1** | |
| **OPS-W2-2** | **OPS-31 does not reach production until ALV-112's refresh step is on `main`** and a production deploy has been proved to run it | `main`'s `deploy.yml` mentions `refresh_bench_files.sh` zero times, and the script is absent from `main` — **Fact**, checked today | Production serves the new HTML with August's stylesheet and script, and nothing on screen says so | **Require · P0** | |
| **OPS-W2-3** | **Prove the deployed assets are the ones just built, every release**, by the three checks in §3.7, gathered into `scripts/check_assets_deployed.sh` and run as a deploy gate | A stale asset is invisible: the page renders and the product is a month old | ALV-112 again — it hid for four weeks | **Require · P1** | |
| **OPS-W2-4** | **Measure the free Jinja slot count (M2) once, at the OPS-31 commit**, and set the CI ceiling from that measurement rather than from a count of files | "Split as finely as you like" is an inference from a comment, not a number. My reading is that OPS-31 frees about three slots, not an unlimited number | Wave 4 adds the file that walks back over the cliff, and every CI check still passes | **Require · P1** | |
| **OPS-W2-5** | **`scripts/check_template_budget.py` as a blocking CI check** (§3.3), with one shared constant behind 042 AC-44 and 043 AC-44 | Timing gates are flaky; a counting gate is deterministic | The limit is defended by a paragraph in a document, which is to say not at all | **Recommend · P2** | |
| **OPS-W2-6** | **Count the six parts once per page load, not twice.** Either `get_home` drops `counts`, or Home does not call `get_nav_counts` | Spec §8 and §13 together compute the most expensive queries on the page twice | The landing page carries double its heaviest cost for the life of the product | **Recommend · P2** | |
| **OPS-W2-7** | **Add a payload-size budget beside the query budget**: `get_nav_counts` ≤ 1 KB, `get_home` ≤ 30 KB, `get_inbox` ≤ 60 KB, asserted in bytes in the same test as the query count | `nfr-budget` has no payload number anywhere, and a 3G budget is mostly about bytes | The query count stays honest while the payload quietly grows | **Recommend · P2** | |
| **OPS-W2-8** | **Build a 1,000-employee fixture and a 20-person fixture, and measure both** (§3.5). Record the numbers with the date and where they were taken | `nfr-budget` §1's rule: no test may claim scale on three seeded rows. Wave 1 measured neither shape | "It is fast" with no number, on the page every employee opens every morning | **Require · P1** | |
| **OPS-W2-9** | **Assert the query count, not only the time**, per persona, at 1,000 employees — especially `_pending_approvals_scope`, the gap rule and the team summary | The old bell took 16.4 s for HR because it walked one employee at a time, and that helper is being reused | The same defect ships again behind a faster-looking screen | **Require · P1** | |
| **OPS-W2-10** | **Measure how many API calls one Home load and one five-minute session make, and compare with the nginx limit** — 120 requests a minute per **IP address**, burst 30 | A 20-person store is one address. Twenty people at the shift bell is about 60 requests in a few seconds | People are refused at exactly the moment the product is meant to be used, and it reads as the app being broken | **Recommend · P2** | |
| **OPS-W2-11** | **Wave 2 does not touch `deploy/nginx.conf`.** If the rate limit has to change, that is its own slice, tested first with `scripts/check_nginx_parses.sh` | One nginx serves production and dev from one file; a dev deploy that changes it restarts the live site's proxy | A Wave 2 push changes the live site's proxy behaviour | **Require · P1** | |
| **OPS-W2-12** | **No shared cache on anything that varies by person**, and `no_cache = 1` stays on the page, pinned by a test (§3.6) | Frappe keeps a `www` page's HTML for 30 minutes keyed by **address only** | One person's work queue served to the next person who opens the address | **Require · P1** | |
| **OPS-W2-13** | **If a tenant-wide settings cache is added**, key it by site, cap it at 5 minutes, and write the invalidation hook in the same commit | Four gunicorn workers means four caches that disagree | Stale settings nobody can explain and nobody can clear | **Consider · P3** | |
| **OPS-W2-14** | **Wave 2 ships to production in a release of its own**, with the previous image tag written down and confirmed present in `alvoraa-app` | A rollback rolls back the whole image, not one commit | Rolling back Home also rolls back unrelated fixes, or the tag turns out not to be there | **Require · P1** | |
| **OPS-W2-15** | **Size the 09:30 spike before the production release**: 20 concurrent Home loads against 8 request slots | Home is the landing page and check-in is time-bound, so the load is synchronised by design | The busiest sixty seconds of the day is the one nobody measured | **Recommend · P2** | |
| **OPS-W2-16** | **A named alert with a named owner for a response-time breach on the portal's landing page**, per `nfr-budget` §8 | A change you cannot see working is not finished | A slow Home is reported by an employee, not by us | **Consider · P3** | |
| **OPS-W2-17** | **Check the local-bench loop at the first OPS-31 test**: does an edit to `portal.js` show up without a build step? | After OPS-31 the file is served from `sites/assets`, not read from the app folder | A day lost to "my change does nothing" | **Note · P3** | |
| **OPS-W2-18** | **Wave 1's OPS-15 (the wasted ~7-minute `bench version` wait) matters more now.** Still Surbhi's, still outside this slice | A stale-asset rollback is now one of the likelier rollbacks, and 7 of its 10 minutes are a loop waiting for a command that cannot succeed | Every deploy and every rollback stays about 7 minutes longer than it needs to be | **Recommend · P2** | |

### Labelled gaps

- **Dangerous debt, and it is at the top for a reason:** a production deploy does not
  refresh the sites volume's assets (OPS-W2-2). It is dangerous the moment OPS-31 exists,
  and harmless before it.
- **Temporary debt:** no fixture at either tenant shape (OPS-W2-8). Removed by building the
  two fixtures, which Wave 2 needs for its own tests anyway.
- **Intentional trade-off:** Wave 2's panels sharing Wave 1's four files, if Surbhi decides
  against bringing OPS-31 forward. Say so in writing if that is the choice, because the
  cost lands on the engineer's calendar rather than on the screen.
- **Acceptable simplification:** no background jobs and no new queue. Nothing in Wave 2
  takes over two seconds.

---

## Readiness verdict

**Not ready to build the panels. Ready to build the server side today.**

| Question | Answer |
|---|---|
| Can `home_api.py`, `inbox_api.py`, `parts()`, the queries and the tests start now? | **Yes.** None of it is a template and none of it touches the deploy |
| Can Home's and Inbox's markup, style and script start now? | **No** — OPS-W2-1. The template budget is spent |
| Can Wave 2 go to `dev`? | Yes, once built, under the usual rule that Surbhi says so |
| Can Wave 2 go to production? | Only after OPS-W2-2, OPS-W2-3, OPS-W2-8 and Wave 1's five swap conditions |
| Is the rollback written and does its tag exist? | The method is written (§4.3). **The tag is not known yet** — it is written down on the day |

---

## What needs Surbhi's decision, not mine

1. **OPS-31 before Wave 2's panels** (042 D-6, the same question as 043 D-5).
   My recommendation: yes — and neither wave writes panel code until M1–M4 are recorded.
2. **OPS-31 may not go to production until ALV-112's workflow change is on `main`.**
   My recommendation: land the workflow change on `main` on its own, with `[skip ci]`, and
   prove it with one deploy.
3. **One count or two** (OPS-W2-6). My recommendation: `get_home` keeps `counts` and Home
   makes two calls, not three.
4. **The payload budgets** (OPS-W2-7), since `nfr-budget.md` has none. My recommendation:
   take the three numbers above as the starting line and correct them after the first
   measurement.
5. **Wave 1's OPS-15**, the seven wasted minutes in every deploy and every rollback. Still
   open from 22 September.

---

## What I checked today, and what I did not

**Checked, all read-only, 2026-09-24, on this machine:** `deploy/nginx.conf`,
`deploy/Dockerfile`, `deploy/compose/docker-compose.app.yml`,
`.github/workflows/deploy.yml` on `dev` and on `origin/main`,
`scripts/refresh_bench_files.sh`, commit `8718f27` and its message, the 034 worktree's
staged OPS-31 work (`hrms-employee.html`, `hrms_employee.py`, the three renames), Wave 1's
`07-devops-inputs.md` and `03-implementation-notes.md` §4, `nfr-budget.md`, and this
slice's `02-functional-spec.md`. Two web reads of frappe's `get_build_version` on GitHub
(`version-15` and `version-16` branches).

**Not checked, and therefore not claimed:** nothing was run on production, on dev or on any
bench. **No number here was measured by me today** — every figure is either Wave 1's, dated
and quoted, or an estimate that says so. I did not confirm `cache_size` or
`get_build_version` against our own v16.33.1. I did not check whether the portal's API
answers carry `Cache-Control: no-store`. I left nothing behind: no container, no file on a
bench, no changed setting. Nothing above is a secret or a path to one.

## Assumptions

- `[ASSUMPTION]` `bench build` copies non-bundle files under `public/` verbatim, so a
  served asset can be compared with the repository file. Confirm once on the bench.
- `[ASSUMPTION]` Production's template chain uses about 27 slots, as Wave 1 read on the
  local bench. The same count has not been measured on the image.
- `[ASSUMPTION]` Production still pulls an image only during a deploy — there is no
  `pull_policy` in the compose files — so the rollback tag must already exist in
  `alvoraa-app`.

## Handoff note

**To the engineer:** three things I would like back in `03-implementation-notes.md` —
M2's slot count, M1/M3's timings before and after OPS-31, and a yes or no on whether the
local bench serves an edited `portal.js` without a build step.

**To the security engineer:** §3.6 is where a shared cache would first appear in this
slice. If Wave 2's `01c` adds a caching requirement, please make it say *keyed by user and
site, or not at all*.

**To the test engineer:** the query-count assertions in OPS-W2-9 and the payload-byte
assertions in OPS-W2-7 belong in the same test as the persona checks, at 1,000 employees —
not at 250.
