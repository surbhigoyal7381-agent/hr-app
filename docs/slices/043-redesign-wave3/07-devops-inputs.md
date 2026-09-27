---
slice: 043-redesign-wave3
artifact: 07-devops-inputs
author: hrms-devops-engineer
date: 2026-09-24
status: draft — §3 (requirements) and an early §4 (strategy). §5 (release readiness) is written when the build is done
inputs: [02-functional-spec.md revision 1, ../042-redesign-wave2/07-devops-inputs.md, ../034-redesign-wave1/07-devops-inputs.md (OPS-1 to OPS-19 and §3b), ../034-redesign-wave1/03-implementation-notes.md §4, .claude/context/nfr-budget.md §1 §2 §3 §5 §8, deploy/nginx.conf, deploy/compose/docker-compose.app.yml, deploy/Dockerfile, .github/workflows/deploy.yml, scripts/refresh_bench_files.sh, alvoraa_portal/.../www/hrms-employee.html and hrms_employee.py (OPS-31 work in progress in the 034 worktree)]
---

# Wave 3 — Time and Pay: DevOps inputs

**I advise. Every Decision column below is blank and is Surbhi's.** I changed no code, ran
nothing on any server, and touched no bench. Everything here is either read from a file in
this repository, quoted from Wave 1's measurements, or labelled as an estimate. What I did
and did not check is listed at the end.

Item IDs are `OPS-W3-n`. Where an item is the same as Wave 2's, I say so rather than
repeat the reasoning — the two waves share one platform and should not get two answers.

---

## Read this first — the four that stop the build

**1. Wave 3 must not add a fifth include file, and today there is no free slot.** Wave 1
measured the cliff over real HTTP: four include files cost +1.1 %, five cost +97 %,
fifteen cost +46 %, twenty-four cost +565 % (034 `03-implementation-notes.md` §4, measured
2026-09-23). It is a step, not a slope. Wave 3 adds **two** panels — Time and Pay — to the
same four files Wave 2 is also editing. **Fact**, read in the notes.

**2. OPS-31 must not reach production before ALV-112's asset refresh reaches `main`.**
`scripts/refresh_bench_files.sh` is absent from `origin/main`, and `main`'s copy of
`.github/workflows/deploy.yml` mentions it **zero** times (**Fact**, checked with
`git cat-file` and `git show origin/main:...` today). If OPS-31 moves the portal's style
and script into `/assets/`, those files are served from the **sites volume**, and a
production deploy does not refresh the volume. Production would run the new HTML against
August's script. Nothing would error. Full reasoning and the proof steps are in
`../042-redesign-wave2/07-devops-inputs.md` §3.7; they are not repeated here.

**3. The payslip PDF is the one piece of real CPU work in this wave, and it lands on the
web tier.** The spec estimates 1–3 s of `wkhtmltopdf` per PDF. Production's web tier is
**gunicorn, 4 workers × 2 threads = 8 requests at a time**, one backend replica, request
timeout 120 s (**Fact**, `deploy/compose/docker-compose.app.yml` line 223). **Inference:**
nine people downloading payslips at once fill every slot, and everyone else's portal waits.
Payday is not a random moment — it is the same hour for the whole tenant. Nobody has
measured this. §3.4 says how.

**4. Wave 3 changes something that reaches people outside the product.** Spec D-1 fixes the
manager's deduction email so it stops carrying a report's loss of pay in rupees. That is
the right fix, and it is also a behaviour change to live email. Email is muted on
production until the first client's go-live, so the change will first be real on dev — it
needs a deliberate send to a test address, and a note on release day. §4.5.

---

## §3 Requirements · 2026-09-24 · hrms-devops-engineer

### 3.1 The Jinja cliff — what Wave 3 may and may not do before OPS-31 lands

Frappe builds its Jinja environment with `cache_size=32` — 32 compiled templates per worker
process, shared across every page that worker serves. The portal page's chain already uses
about 27. Each include file takes one more slot. Past 32 the cache evicts on every request
and the whole million-byte page is compiled again on every visit.

| Wave 3 may | Wave 3 may not, before OPS-31 |
|---|---|
| Build `time_api.py`, `pay_api.py`, the month payload change, the `Holiday.weekly_off` addition, the feature gate on `get_payslips`, the company scope on `get_shift_types`, the encashment fix, the email fix, and every test | **Add any new file under `templates/includes/ess/`.** Five files is not merely slower, it is unstable: Wave 1 measured the same five-file split at +5 % once and +45 % to +97 % three other times |
| Retire `get_attendance_calendar` and `submit_attendance_request` and their panels — that is deletion, not addition | **Assume the split protects two sessions.** `script.js.html` is 13,441 lines. Wave 2 is in it too |

**My recommendation, plainly: OPS-31 first, then Wave 2's panels, then Wave 3's.** That is
the analyst's recommendation in 043 D-5 and 042 D-6 and the engineer's in 034 §4. I agree
with all three, and I would add one thing they do not say: **OPS-31 does not give the waves
unlimited files.** It removes three template files (`frame.css.html`, `panels.css.html`,
`script.js.html` — confirmed by the staged renames in the 034 worktree today), so it frees
about **three** slots, not an unlimited number. Wave 2 and Wave 3 between them get roughly
three or four new include files, then the cliff is back. **Inference from Wave 1's
numbers**, and the reason OPS-W3-4 asks for the slot count to be measured rather than
assumed. Full reasoning in Wave 2's §3.1.

### 3.2 How we would know OPS-31 did not actually fix it

Identical to Wave 2's §3.2 and must not be measured twice with two rigs. Repeated here in
short so this document stands alone:

| # | Measurement | Pass line | Who looks |
|---|---|---|---|
| **M1** | 25 warm signed-in GETs of `/hrms-employee`, `curl -w %{time_starttransfer}`, median and p95 | median ≤ **0.191 s** (Wave 1's 0.174 s baseline plus 10 %), and no warm sample above **0.30 s** (0.343 s was the five-file cliff) | engineer on the local bench at the commit; me on dev at release readiness |
| **M2** | the number of templates the worker's Jinja environment holds after one render, and the installed `cache_size` | at least **3 free slots of 32** | engineer, once, at the OPS-31 commit, with stdout **and** stderr captured (lesson 8) |
| **M3** | variance across the same 25 samples | **p95 ÷ median ≤ 1.5** | engineer, same run |
| **M4** | bytes of HTML on the wire, and the `?v=` value on two loads in a row | HTML **≤ 250 KB** uncompressed; **the `?v=` identical on both loads** | engineer locally, me on dev, Surbhi's browser on production |

**M4's second half is the one that silently undoes OPS-31.** `asset_version` is Frappe's
`get_build_version()`, the modified time of `sites/assets/assets.json` — **and when that
file is missing it returns a random eight-character string** (read on frappe's
`version-15` and `version-16` branches on GitHub today; confirm on our v16.33.1). A random
stamp means every phone downloads the half-megabyte script on every visit, for ever, and
the screen looks perfect.

**One measurement that belongs to Wave 3 alone.** Time and Pay are the two heaviest panels
in markup. After OPS-31, re-run M1 with Wave 3's panels in place, because the markup file
keeps growing even when the file count does not: **the page's own size is still compiled
on every eviction.** Record the markup file's byte size beside the timing.

### 3.3 How the limit is defended permanently

The same single gate as Wave 2: `scripts/check_template_budget.py`, blocking in CI, which
counts the templates the page's chain pulls in (using Wave 1's expander,
`alvoraa_portal/tests/portal_source.py`), reads `cache_size` out of the installed Frappe
rather than trusting a comment, fails when fewer than three slots are free, and holds the
ceiling in **one constant** that both 042 AC-44 and 043 AC-44 import. One gate, one number,
two waves. A timing gate would be flaky; a counting gate is deterministic and cannot be
forgotten.

### 3.4 Query count, payload size, N+1 risks, and the one piece of real CPU

`nfr-budget.md` has no payload-size number anywhere. These are mine, and they are
estimates, marked as such.

| Endpoint | Queries — spec's budget | Payload — my recommended budget | Basis |
|---|---|---|---|
| `get_time` (a full month) | ≤ 40, ≤ 700 ms p95 | **≤ 40 KB** | **Estimate**: 31 day rows at 200–400 bytes, plus punches, totals and the rule settings |
| `get_pay` | ≤ 15, ≤ 500 ms p95 | **≤ 20 KB** | **Estimate**: one slip with earning and deduction lines and a year-to-date block |
| The "Why?" sheet | ≤ 4, ≤ 400 ms p95 | **≤ 8 KB** | **Estimate**: one deduction and its violation rows |
| `download_payslip` | — | 100–400 KB of PDF | **Estimate**, and see below — it is CPU, not queries, that matters here |

**The N+1 risks, named so the engineer writes the assertion instead of hunting the bug:**

| Where | The trap | The safe shape |
|---|---|---|
| The month calendar | a query per day: attendance, holiday, leave, correction, punches — 31 days × 5 is 155 queries for one screen | **one query per doctype for the whole month range**, assembled in Python. `attendance_correction.month` already measured 15 queries / 702 ms for a month — that is the number to beat, and it is the spec's own target |
| Day detail | re-reading the shift row per day | slice 017 already caches one shift row through `_shift_row:233` — reuse it, do not re-derive |
| Past leave | one ledger query per leave type | one query over the ledger for the period |
| The year table ("your record this year") | one query per month — 12 round trips | one query over the year's rows, grouped in Python, as the spec already says |
| Payslip lines | one `get_doc` per Salary Detail row to follow `additional_salary` | return the link on the line, then **one** read when the person taps Why? |
| The team late list | one deduction read per report | `get_team_late_list` is already a fixed field list; keep it set-based, and it must stay days-only |

**The payslip PDF — the capacity question of this wave.**

| What | Number | Label |
|---|---|---|
| CPU per PDF | 1–3 s of `wkhtmltopdf` | **Estimate**, from the spec; nobody has timed ours |
| Concurrent web requests production can serve | **8** (4 gunicorn workers × 2 threads), one backend replica | **Fact**, compose line 223 |
| Request timeout | 120 s | **Fact**, same line |
| Tenant size to design for | 1,000 employees (`nfr-budget` §1) | Fact |

**Inference:** nine simultaneous downloads fill the web tier and every other request on
every tenant on that stack waits behind them. Payslips are released to everybody at once,
so the arrival is synchronised by design. What to measure, before the production release:

1. Time `download_payslip` on the local bench, 20 warm calls, p95, on a real slip.
   Pass line: **≤ 3 s** (`nfr-budget` §2 — anything over 2 s of work should be a
   background job; the spec already concedes the move at 3 s).
2. Run 10 concurrent downloads and watch whether an ordinary portal request still answers
   within its 500 ms budget. Pass line: it does.
3. If either fails, the answer is not "add workers". It is the one the spec already names:
   the PDF becomes a background job with a notification, on the `short` queue, with
   `worker-default` listening (**Fact**: `worker-default` runs `bench worker --queue
   default,short`, compose line 265). And never a bare service list on
   `docker compose up` — lesson 1.

**Do not add "download all payslips".** The spec says so and I agree, in writing: on a
400-person tenant that is 400 × 1–3 s in the web tier.

### 3.5 What a 1,000-employee tenant does, and what a store with 20 does

**Wave 1 measured neither shape, and neither fixture exists. I could not check either
today.**

**At 1,000 employees**, Time and Pay are mostly own-record screens, so the fan-out risk is
smaller than Wave 2's — with three exceptions, and they are the ones to measure:

| Measure | On what | Against |
|---|---|---|
| `get_time` for a manager opening **a report's** month (`_subject:251`), and the team late list | 1,000-employee, 4-company fixture, 20 warm calls | ≤ 40 queries, ≤ 700 ms p95, and **not slower than `attendance_correction.month`'s measured 15 queries / 702 ms today** |
| `get_pay` and the Why? sheet | the same fixture, on a month where the late-rule job produced deductions (PP Jewellers' real figure is about **212 Attendance Deduction rows per quarter**) | ≤ 15 and ≤ 4 queries, ≤ 500 / 400 ms p95 |
| `download_payslip` under concurrency | the same fixture | §3.4's two pass lines |
| Time usable, p95 | the W1D-09 rig (Chrome Slow 4G, 4× CPU slow-down) | **≤ 2.5 s** (`nfr-budget` §2), with slice 036's compression live |

**At a store with 20 people**, size is not the risk. Three other things are:

1. **The nginx rate limit is keyed on the IP address, and a store is one address.**
   `rate=120r/m`, `burst=30 nodelay` on `location /api/` (**Fact**, `deploy/nginx.conf`
   lines 70 and 270). Wave 3 is lighter than Wave 2 here — Time is one call and Pay is one
   call — but the PDF download goes through `/api/` too, and payday is synchronised.
   Measure the call count per session and compare. Any change to the limit is its own
   slice with the `nginx -t` gate, because one nginx serves dev and production from one
   file (lesson 13).
2. **The empty shapes are the normal shapes**: no shift assignment, no holiday list, no
   payroll feature at all (so no Pay salary tab and the endpoints must refuse), a slip with
   no late deduction (so no Why? control), a deduction typed by hand with no Attendance
   Deduction behind it. Measure nothing; test all of them — spec §9.
3. **The print format is per tenant** (spec F-4). A 20-person store that nobody configured
   gets Frappe's generic layout. That is a configuration action on release day, not code,
   and it is not rolled back by an image rollback (§4.4).

### 3.6 Caching — and the one rule that has no exception

**Payslip data is never cached anywhere shared. Not in Redis, not in a module-level
variable, not in an nginx cache, not in a browser cache, not in a log line.** It is the
most sensitive data in the product (`nfr-budget` §5), and a shared cache keyed by anything
other than the user is a cross-employee salary leak, not a performance bug.

| Thing | May it be cached? | For how long | What clears it |
|---|---|---|---|
| The portal HTML | **No.** `context.no_cache = 1` is set in `hrms_employee.py` (**Fact**, read today, line 12) and stays, pinned by a test | — | — |
| `get_pay`, `get_payslips`, the Why? sheet, `download_payslip` | **Never, anywhere shared.** Frappe keeps a `www` page's HTML for 30 minutes **keyed by address only, not by user** — that mechanism must never come near this screen | — | — |
| `get_time`'s month payload | **No shared cache.** A month's attendance changes the moment a correction is decided | — | — |
| Within **one request**: the caller's Active Employee row, the shift row, the holiday rows | **Yes** — plain memoisation, which is not a cache | the request | ends with it |
| Tenant-wide settings: Shift Types, Holiday List rows, the late-rule record | **Consider**, in Redis, **keyed by site**, ≤ 5 minutes, with a `doc_events` invalidation hook written in the same commit | 5 min | the hook. No hook, no cache |
| The PDF | **Never stored, never pre-generated, never written to `/files/`** | — | — |

Two more, specific to this wave:

- **Assert `Cache-Control: no-store`** on `get_pay`, `get_payslips` and `download_payslip`,
  and `Content-Disposition: attachment` on the PDF. **I could not check today** whether
  Frappe already sets them — it needs a signed-in session. This belongs in the slice's own
  `01c` as much as here.
- **The PDF is not compressed and should not be.** nginx's `gzip_types` list deliberately
  leaves out PDFs (**Fact**, `deploy/nginx.conf` lines 104–110); they are compressed
  already. Nothing to do — recorded so nobody "fixes" it.
- **JSON answers under `/api/` are compressed** (line 269–277, with the comment explaining
  that Frappe's JSON never carries the CSRF token, so there is no BREACH secret to guess).
  `get_pay` carries salary figures but no token, so the existing reasoning still holds.
  **It is worth one line in the security artifact rather than a silent assumption.**

### 3.7 Static asset delivery after OPS-31 — see Wave 2, plus one thing

Wave 2's §3.7 carries the full picture: `expires 30d` with `Cache-Control: public,
immutable` on `/assets/`, the `?v=` stamp from `get_build_version()`, gzip on CSS and JS
with no `gzip_static`, the image's `bench build` and `materialise_assets.sh`, and the
ALV-112 refresh that exists on `dev` and not on `main`. The proof steps — compare the
served file's sha256 with the repository file at the deployed commit, compare the image's
copy with the volume's copy, and confirm the `?v=` moved between releases and does **not**
move between two loads — are written out there and apply unchanged.

**The one addition for Wave 3:** Wave 1's OPS-5 promised that no portal step needs
`bench build`. **After OPS-31 that promise no longer covers style and script.** Wave 3
edits the portal script heavily, so from Wave 3 on, every visible change depends on a new
image **and** on the volume refresh. Write that into the runbook rather than leaving it in
a slice document.

---

## §4 Strategy, early · the release plan and the rollback

### 4.1 Order of release

| # | Step | Why it is here |
|---|---|---|
| 1 | ALV-112's refresh step reaches **`main`** | Otherwise no production deploy refreshes assets. Lesson 14: the automatic Deploy runs **`main`'s** copy of the workflow; exercise dev's copy with `gh workflow run Deploy --ref dev` |
| 2 | **OPS-31** on `dev`, with M1–M4 recorded | 043 D-5 |
| 3 | Wave 1's swap, under its five agreed conditions (034 §3b) | Unchanged |
| 4 | Wave 2 on `dev`, then Wave 3 on `dev` | Two waves in one script file at once is what the split was meant to prevent |
| 5 | Wave 3 to production, **in a release of its own** | A rollback rolls back the whole image, not one commit (Wave 1's OPS-16) |
| 6 | **On the day, per tenant:** set the Salary Slip print format | A configuration action, on Surbhi's word, like W1D-21's staff-list tick |

### 4.2 What a Wave 3 deploy needs

| | Answer |
|---|---|
| `bench migrate` | **No.** No doctype, no field, no patch (spec §14) |
| `bench build` | Not for Wave 3's own code — but after OPS-31 the built style and script must reach the volume (§3.7) |
| `bench clear-cache` | Only for a remembered "not found" on a new route; the narrow command is `bench --site <site> clear-website-cache`, and it needs approval |
| Compose, image, nginx | No change. **Wave 3 must not touch `deploy/nginx.conf`.** If the PDF ever needs its own rate limit, that is a separate slice with the `nginx -t` gate |
| New queues or workers | **None today.** If §3.4's measurement pushes the PDF into a background job, it goes on the `short` queue, which `worker-default` already listens to — no new service, and never a hand-listed `docker compose up` (lesson 1) |
| Configuration, per tenant | **Yes** — the Salary Slip print format (spec F-4). Not a deploy step and not covered by a rollback |

### 4.3 Rollback

**Redeploy the previous image tag with migrations off — about 10 minutes of machine time,
12–15 minutes from the moment someone decides.** Measured by me on dev on 2026-09-22:
9 min 33 s, of which **6 min 54 s is the deploy waiting for `bench version`, a command that
never succeeds on our image** (Wave 1's OPS-15, still open). Production has not been timed
with migrations off; **estimate 9–11 minutes**.

The command, **for Surbhi to approve and run** — I do not run it:

*Actions → Deploy → Run workflow* · `environment: production` ·
`image_tag: <the tag production ran before this release>` · `image_package: alvoraa-app` ·
`run_migrations: false`.

**Three things that make Wave 3's rollback different from Wave 1's:**

1. **Two endpoints are deleted** (`get_attendance_calendar`, `submit_attendance_request`).
   An image rollback brings them back with everything else, so this is clean — as long as
   the deletion is its own commit, which the spec already requires.
2. **The email change is not undone by a rollback in the way people expect.** Rolling the
   image back restores the old template, so managers start receiving the rupee amount
   again. That is a privacy regression arriving by rollback. Say it out loud on the day
   and check it afterwards (OPS-W3-9).
3. **The print-format configuration is not rolled back at all.** A setting written on a
   tenant stays written. Note it in the release record so nobody is surprised that the PDF
   still looks new after a rollback.

Before the release, not after: write the previous production tag down and confirm it exists
in `alvoraa-app` (production pulls only during a deploy — there is no `pull_policy` in the
compose files); and no pushes to `dev` in the hour after, because there is one runner and
it runs one job at a time (Wave 1's OPS-19).

### 4.4 After the deploy — what to look at

Disk headroom **before** the pull (lesson 16: a full disk breaks redis, kills the workers
and defeats `restart: unless-stopped`); `docker top` plus the rq worker registration and
heartbeats, never `docker ps` alone (lesson 15); `scripts/check_workers.sh`; M1 and M4 from
§3.2; the asset check from Wave 2's §3.7; and then Wave 3's own three:

1. **One payslip PDF**, timed, from an ordinary signed-in browser. It is the only path in
   this wave that can take the web tier down.
2. **The Error Log count** for `time_api` and `pay_api` in the first hour.
3. **A named alert with a named owner** for a `download_payslip` failure or timeout
   (`nfr-budget` §8 asks for named alerts with named owners; a PDF that fails silently is
   exactly the kind of thing an employee reports weeks later).

### 4.5 The email change (spec D-1) — how it should travel

Email is muted on production until the first client's go-live, so this change is provable
only on dev. Recommend: fix the template, send one deliberate test to an internal address
on dev with `notify_manager` on, read the received message, and confirm the rupee amount is
gone and the days remain. **Never put the amount in a log line while testing it** —
`nfr-budget` §5 forbids personal data in logs, and a loss-of-pay figure is personal data.
This is the one change in Wave 3 that leaves the product and reaches a person's inbox, so
it deserves its own line in the release record.

---

## OPS items

Every Decision is blank and is Surbhi's.

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| **OPS-W3-1** | **OPS-31 lands on `dev`, with M1–M4 recorded, before any Wave 3 markup, style or script is written.** Server-side work starts now. Same item as Wave 2's OPS-W2-1 | Four include files is the whole budget and it is already spent; Wave 3 adds two panels to the same files Wave 2 is editing | Either two sessions edit one 13,441-line script for a month, or somebody adds the fifth file and every portal page gets about 250 times more expensive to render | **Require · P1** | |
| **OPS-W3-2** | **OPS-31 does not reach production until ALV-112's refresh step is on `main`**, proved by one deploy. Same as OPS-W2-2 | `main`'s `deploy.yml` mentions `refresh_bench_files.sh` zero times, and the script is absent from `main` — **Fact**, checked today | Production serves new HTML with August's script and nothing on screen says so | **Require · P0** | |
| **OPS-W3-3** | **Prove the deployed assets are the ones just built, every release** (Wave 2 §3.7's three checks, gathered into `scripts/check_assets_deployed.sh` as a deploy gate). Same as OPS-W2-3 | A stale asset is invisible: the page renders, nothing errors, the product is a month old | ALV-112 again — it hid for four weeks | **Require · P1** | |
| **OPS-W3-4** | **Measure the free Jinja slot count once, at the OPS-31 commit**, and set the CI ceiling from the measurement. Same as OPS-W2-4 | "Split as finely as you like" is an inference from a comment. My reading is that OPS-31 frees about three slots | A later wave walks back over the cliff and every CI check still passes | **Require · P1** | |
| **OPS-W3-5** | **`scripts/check_template_budget.py`, blocking in CI, one constant shared by 042 AC-44 and 043 AC-44** | A counting gate is deterministic; a timing gate is flaky and gets ignored | The limit is defended by a document, which is to say not at all | **Recommend · P2** | |
| **OPS-W3-6** | **Time `download_payslip` (20 warm calls, p95) and run 10 concurrent downloads, before the production release.** If p95 is over 3 s, or an ordinary request misses its 500 ms budget under that load, move the PDF to the `short` queue with a notification | 1–3 s of CPU per PDF against **8** concurrent request slots, on a day when a whole tenant asks at once | The portal stops answering for everybody on payday, and it looks like an outage rather than a queue | **Require · P1** | |
| **OPS-W3-7** | **No pre-generation and no "download all payslips", now or later** | 400 slips × 1–3 s in the web tier | One button takes the stack down for every tenant on it | **Require · P1** | |
| **OPS-W3-8** | **Payslip data is never cached anywhere shared, and `no_cache = 1` stays on the page, pinned by a test** (§3.6) | Frappe keeps a `www` page's HTML for 30 minutes keyed by **address only**, and a shared cache keyed by anything but the user is a salary leak | One employee's pay shown to the next person who opens the address | **Require · P0 if it is ever added; P1 as a standing rule** | |
| **OPS-W3-9** | **Say on release day that an image rollback restores the old deduction email**, and check the template after any rollback | Rolling back the image rolls back the privacy fix with it | A rollback quietly reopens a decided privacy rule (Q-b, 14 Sep) | **Require · P1** | |
| **OPS-W3-10** | **Prove the email fix on dev with one deliberate send**, and never log the amount while testing | Production email is muted until go-live, so dev is the only place this is real | The fix ships unproved, on the one path that leaves the product | **Recommend · P2** | |
| **OPS-W3-11** | **Assert query counts, not only times**, for the month calendar, the year table and the payslip lines, at 1,000 employees | 31 days × 5 doctypes is 155 queries if a loop creeps in; `attendance_correction.month`'s 15 queries / 702 ms is the number to beat | The screen that exists to restore trust becomes the slowest one in the product | **Require · P1** | |
| **OPS-W3-12** | **Add payload budgets beside the query budgets**: `get_time` ≤ 40 KB, `get_pay` ≤ 20 KB, the Why? sheet ≤ 8 KB, asserted in bytes | `nfr-budget` carries no payload number, and the 2.5 s phone budget is mostly bytes | The query count stays honest while the payload grows | **Recommend · P2** | |
| **OPS-W3-13** | **Build the 1,000-employee and 20-person fixtures** (shared with Wave 2 — build them once) and record the numbers with the date and where they were taken | `nfr-budget` §1: no test may claim scale on three seeded rows. Wave 1 measured neither shape | "It is fast" with no number, on the screen that decides whether people trust their pay | **Require · P1** | |
| **OPS-W3-14** | **Wave 3 does not touch `deploy/nginx.conf`.** If the PDF route needs its own rate limit, that is its own slice, tested first with `scripts/check_nginx_parses.sh` | One nginx serves production and dev from one file; a dev deploy that edits it restarts the live site's proxy | A Wave 3 push changes the live site's proxy behaviour | **Require · P1** | |
| **OPS-W3-15** | **Wave 3 ships to production in a release of its own**, with the previous image tag written down and confirmed present in `alvoraa-app`, and the endpoint deletions in a commit of their own | A rollback rolls back the whole image | Rolling back Pay also rolls back unrelated fixes, or the tag is not there | **Require · P1** | |
| **OPS-W3-16** | **The per-tenant print format is a named release-day step, with an owner, and it is not covered by the rollback** | It is a setting on a tenant, not code | The PDF a bank sees carries Frappe's generic layout, or a rollback leaves a half-configured tenant and nobody knows | **Recommend · P2** | |
| **OPS-W3-17** | **A named alert with a named owner for `download_payslip` failures and timeouts** | `nfr-budget` §8. A PDF that fails silently is reported weeks later | We learn about it from an employee | **Consider · P3** | |
| **OPS-W3-18** | **Confirm `Cache-Control: no-store` on the pay endpoints and `Content-Disposition: attachment` on the PDF.** I could not check it today | A cached salary answer is the worst cached answer in the product | A browser or a proxy keeps a payslip | **Recommend · P2** | |
| **OPS-W3-19** | **Wave 1's OPS-15 (the ~7 wasted minutes on `bench version`) still open** | It is most of the rollback time, and Wave 3 is the wave most likely to need a quick one | Every deploy and rollback stays about 7 minutes longer than it needs to be | **Recommend · P2** | |

### Labelled gaps

- **Dangerous debt:** a production deploy does not refresh the sites volume's assets
  (OPS-W3-2). Harmless today; dangerous the moment OPS-31 exists.
- **Temporary debt:** the payslip PDF is unmeasured (OPS-W3-6). Removed by one timing run
  and one concurrency run on the local bench.
- **Intentional trade-off:** the PDF stays on demand in the web tier rather than becoming a
  background job, **on the condition that §3.4's two measurements pass**. If they do not,
  this stops being a trade-off and becomes a defect.
- **Acceptable simplification:** no new queue, no new service, no migration.

---

## Readiness verdict

**Not ready to build the panels. Ready to build the server side and the two defect fixes
today.**

| Question | Answer |
|---|---|
| Can `time_api.py`, `pay_api.py`, the month payload change, the feature gate on `get_payslips`, the company scope on `get_shift_types`, the encashment fix and the email fix start now? | **Yes.** None of it is a template |
| Can Time's and Pay's markup, style and script start now? | **No** — OPS-W3-1 |
| Can Wave 3 go to `dev`? | Yes, once built, when Surbhi says so — and after Wave 2, not beside it |
| Can Wave 3 go to production? | Only after OPS-W3-2, OPS-W3-3, OPS-W3-6, OPS-W3-13 and Wave 1's five swap conditions |
| Is the rollback written, and does its tag exist? | The method is written (§4.3). **The tag is not known yet** — it is written down on the day. And the rollback reopens the email fix (OPS-W3-9) |

---

## What needs Surbhi's decision, not mine

1. **OPS-31 before Wave 3's panels** (043 D-5, the same question as 042 D-6).
   My recommendation: yes — and Wave 3's panels come after Wave 2's, not beside them.
2. **OPS-31 may not go to production until ALV-112's workflow change is on `main`.**
   My recommendation: land the workflow change on `main` on its own, with `[skip ci]`, and
   prove it with one deploy.
3. **The payslip PDF stays in the web tier, on the condition that it is measured first**
   (OPS-W3-6). If Surbhi would rather not spend the measurement, the alternative is to
   accept the risk in writing — not to assume it is fine.
4. **The payload budgets** (OPS-W3-12), since `nfr-budget.md` has none. My recommendation:
   take these three numbers as the starting line and correct them after the first
   measurement.
5. **Wave 1's OPS-15**, the seven wasted minutes in every deploy and every rollback. Still
   open from 22 September.

Spec D-3 (is base pay ÷ calendar days the right daily wage?) is also Surbhi's, but it is a
payroll and legal question, not mine, and I add nothing to the analyst's framing of it.

---

## What I checked today, and what I did not

**Checked, all read-only, 2026-09-24, on this machine:** `deploy/nginx.conf`,
`deploy/Dockerfile`, `deploy/compose/docker-compose.app.yml`,
`.github/workflows/deploy.yml` on `dev` and on `origin/main`,
`scripts/refresh_bench_files.sh`, commit `8718f27` and its message, the 034 worktree's
staged OPS-31 work (`hrms-employee.html`, `hrms_employee.py`, the three renames), Wave 1's
`07-devops-inputs.md` and `03-implementation-notes.md` §4, `nfr-budget.md`,
`../042-redesign-wave2/02-functional-spec.md` and this slice's `02-functional-spec.md`.
Two web reads of frappe's `get_build_version` on GitHub (`version-15`, `version-16`).

**Not checked, and therefore not claimed:** nothing was run on production, on dev or on any
bench. **No number here was measured by me today** — every figure is either Wave 1's, dated
and quoted, or the spec's, or an estimate that says so. I did not time a PDF. I did not
confirm `cache_size` or `get_build_version` against our own v16.33.1. I did not check the
response headers on the pay endpoints. I left nothing behind: no container, no file on a
bench, no changed setting. Nothing above is a secret or a path to one.

## Assumptions

- `[ASSUMPTION]` `bench build` copies non-bundle files under `public/` verbatim, so a
  served asset can be compared with the repository file. Confirm once on the bench.
- `[ASSUMPTION]` The 1–3 s PDF cost in the spec is in the right range for our image and our
  print format. It is the spec's estimate, not a measurement of ours.
- `[ASSUMPTION]` Production's template chain uses about 27 slots, as Wave 1 read on the
  local bench; not measured on the image.
- `[ASSUMPTION]` Production pulls an image only during a deploy — there is no `pull_policy`
  in the compose files — so the rollback tag must already exist in `alvoraa-app`.

## Handoff note

**To the engineer:** the two numbers I most want back are the PDF's p95 under 10 concurrent
downloads, and `get_time`'s query count on a full month for a manager opening a report's
calendar. Both belong in `03-implementation-notes.md` with the date and the commit.

**To the security engineer:** §3.6's "never cached anywhere shared" belongs in this slice's
`01c` as a requirement with a test, not as DevOps advice. So does the `no-store` check in
OPS-W3-18, and one line confirming that compressing the pay JSON under `/api/` is still
safe under the BREACH reasoning written into `deploy/nginx.conf`.

**To the test engineer:** the query-count assertions in OPS-W3-11 and the payload-byte
assertions in OPS-W3-12 go in the same test as the persona checks, at 1,000 employees — not
at 250.
