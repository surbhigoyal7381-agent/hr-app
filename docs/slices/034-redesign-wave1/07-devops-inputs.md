---
slice: 034-redesign-wave1
artifact: 07-devops-inputs
author: hrms-fullstack-engineer (§1–3 written at the coordinator's request; hrms-devops-engineer to review and add §4)
date: 2026-09-22
status: draft
inputs: [00-impact-analysis.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, ../012-leadership-view/07-devops-inputs.md (OPS-26, OPS-31, OPS-33, OPS-34), ../013-mobile-app/00-sequencing-recommendation.md, .claude/context/nfr-budget.md §2 §3, deploy/nginx.conf, deploy/Dockerfile]
---

# Wave 1 frame — DevOps inputs

**Short, and written by the engineer, not the DevOps engineer.** The DevOps engineer
should review §1–3 and write §4 (their view on the strategy). Where they disagree, they
say so; the user decides.

The Decision column holds what the user has already decided (22 Sep). Blank means not
yet decided.

## §1–3 · 2026-09-22 · What the frame needs from the platform

### The speed budget, made specific

The portal is now every tenant's landing page (slice 024), so these are the numbers the
frame is measured against (nfr-budget §2):

| What | Budget | Measured how |
|---|---|---|
| Something on screen (the shell and a page skeleton) | ≤ 300 ms after the HTML starts arriving | Throttled "Slow 3G / low-end phone" profile, local copy, before and after |
| Home usable on a 3G phone, p95 | ≤ 2.5 s | Same profile |
| `frame_api.get_frame` | ≤ 500 ms p95, ≤ 15 queries warm | Timed test with query count, at the "Typical" 250-employee tenant and a 1,000-employee fixture |
| `inbox_api.get_nav_counts` | ≤ 500 ms p95, ≤ 15 queries whatever the team size | Same |
| Start-up calls | 2 (`get_frame`, `get_nav_counts`), down from 4, with no 1.5 s delay | Count in the browser's network log |

### Where the page stands today

| Fact | Value | Source |
|---|---|---|
| Page size | **1.04 MB** (1,042,972 bytes) | the file, `origin/dev` `1c4e84c` |
| Compressed, if it were compressed | 224 KB (gzip on this PC) | measured today |
| Compression on the server | **None** — `deploy/nginx.conf` has no `gzip` lines | read today |
| Of that, inline script / style | 702 KB / 159 KB | measured today |

**So the frame cannot meet the 3G budget on its own.** It adds roughly 30–40 KB. The
two things that move the number are compression and cached script files — neither is
frame code.

### OPS items

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| **OPS-1** | **Compression must be live on dev before the swap goes to dev, and on production before the swap goes to production.** This slice depends on the separate compression slice; it does not build it | 1.04 MB → about 224 KB per visit. The biggest speed win available | The first page everyone sees takes many seconds on a phone; the 2.5 s budget is missed by a wide margin | Recommend | **Taken as its own slice (decision 13).** Dependency recorded here |
| **OPS-2** | **Ship by a parallel preview page and one swap commit.** `/hrms-employee-next` exists during the wave; the swap commit points `/hrms-employee` at the new frame and deletes the preview | Keeps `dev` releasable to production every day while the frame is built | A half-built frame reaches the live tenants in the next release, or releases wait | Recommend | **Approved (decision 2)** |
| **OPS-3** | **Rollback is `git revert` of the swap commit and a normal deploy.** No migration, no data change, no `bench build`, so the revert is clean. The DevOps engineer should state in §4 how long a production deploy takes end to end — that is the real rollback time | nfr-budget §3 asks for rollback ≤ 15 min | We promise a rollback time we have never measured | Recommend | |
| **OPS-4** | **The swap reaches production only after the first client's go-live has settled** (decision 4). Proposed meaning of "settled": the go-live week is over and no portal issue from the client is open. The user confirms the date | A frame change during go-live week would mix two causes of trouble | A go-live problem and a frame problem cannot be told apart | Recommend | **Approved: after go-live settles.** Meaning of "settled" still to confirm |
| **OPS-5** | **What a deploy of each step needs.** Include files are templates read from the app folder, and new `www` pages and Python modules need no migration. So no step in Wave 1 should need `bench migrate` or `bench build`. On the local bench, templates are read from the mounted main checkout; **check before the first bench test whether the page cache needs `bench clear-cache`** (that command needs the user's approval) | Keeps each deploy boring | A surprise migration or build on the release day | FYI | |
| **OPS-6** | **The CI static checks must follow the includes in the same commit as the split.** `check_design_system.py`, `check_portal_handlers.js`, `check_undefined_js.js`, `check_contrast_rendered.py`, `check_attendance_strip.js`, `check_rating_bands.js`, and the JS DOM tests get one shared helper that expands the includes. A check that finds no includes where the page has them fails | These checks are CI's only guard on the page's JavaScript | They pass while reading an empty shell — the checks quietly check less, which looks like safety | Recommend | |
| **OPS-7** | **The page split is pushed to `dev` on its own**, as soon as it passes, so other sessions rebase onto it early. It changes nothing on screen, so it is safe to release | Every branch with page edits must re-apply them in the new files; the sooner, the smaller | Long-lived branches drift further from the split and their merges get risky | Recommend | **Freeze approved in principle (decision 11)**; the coordinator schedules it |
| **OPS-8** | **OPS-31 (move script and style into cached files) comes right after the swap, as its own step.** The include files hold no Jinja, so the move is a rename plus one tag each. Before it, check that the address carries a version so phones do not keep old code (012's OPS-34) | Downloaded once per release, not on every visit | Every visit keeps downloading the page's full script | Recommend | **Approved (decision 12)** |
| **OPS-9** | **Measure before and after on the local copy**: first paint, full load on the 3G profile, bytes, and the two endpoints' query counts. Record them in the implementation notes. Re-measure on dev after the swap | A speed claim needs a number | "Faster" with no number | Recommend | |
| **OPS-10** | **The preview page on production** (if a release happens mid-wave) answers only to System Manager (01c SEC-1). No monitoring needed beyond the usual | It exists for 2–3 weeks | — | FYI | **Approved (decision 3)** |
| **OPS-11** | **The `--fs-xs` change reaches six pages at once** (employee, driver and vendor portals use the token). It rides in its own commit so it can be reverted alone | One line with a wide reach | A layout problem on the driver portal cannot be undone without undoing the frame | Recommend | **Applies to every page (decision 10)** |

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | How long does a production deploy take, end to end? (the real rollback time) | DevOps engineer, §4 | OPS-3 |
| 2 | What counts as "go-live has settled" for the swap date? | Surbhi | OPS-4, the production swap |
| 3 | Does the local bench need `bench clear-cache` to pick up new include files? | Engineer, checked at the first bench test, with approval if needed | Step 1's bench test |
| 4 | Is anything in front of nginx on production (a CDN) already compressing? I could not check | DevOps engineer | OPS-1's measured "before" |

## Assumptions

- `[ASSUMPTION]` Figures are for the file, not a browser load. No load was measured today.
- `[ASSUMPTION]` Templates in the production image are baked at build time, like the rest
  of the app, so a deploy is enough for them to take effect.

## Handoff note

To the DevOps engineer: please write §4. The three things I most want checked are OPS-3
(the rollback time), OPS-5 (whether any step needs a build, migration or cache clear
anywhere), and whether OPS-1's dependency order — compression first, then the swap — fits
your plan for the compression slice.

---

## Review of §1–3 · 2026-09-22 · hrms-devops-engineer

**Verdict: Ready with changes.** Code can start. Four things should be settled before
the step that needs them: the preview page must turn off Frappe's page cache (OPS-12,
step 2), the speed budget needs a named test profile (OPS-17, before the first
measurement), the page split needs a server-time check (OPS-13, step 1), and the rollback
plan needs rewording (OPS-14). I changed no code and touched no server except the
read-only checks listed at the end.

**Bad news first.**

1. **OPS-3 says rollback is a `git revert` and a normal deploy. On production that takes
   about 30–75 minutes, not 15.** The fast path already exists and is measured: redeploy
   the previous image tag with migrations off. That took **9 min 33 s** on dev today.
   The revert still has to happen, but afterwards, so that `main` matches what production
   runs. Details in §4.
2. **Every deploy, including a rollback, wastes about 7 minutes.** The deploy waits for
   `bench version` to succeed before it goes on. `bench version` never succeeds on our
   image. It crashes with `module 'alvoraa_goals' has no attribute '__version__'` (checked
   read-only on the dev backend today). So the loop runs all 60 turns, about 7 minutes,
   then carries on as if all were well. The gap shows in both of the last two runs I
   read: 6 min 54 s on dev today, 7 min 09 s on production on 20 Sep. This is not 034's
   code, but it is the biggest part of the rollback time (OPS-15).
3. **The "3G" budget cannot be met on Chrome's "3G" setting, even with compression.**
   Chrome's preset named "3G" is 400 kbps with 2 s of delay per round trip (Chrome
   DevTools docs, checked 2026-09-22). The page compressed to 224 KB takes about 4.5 s
   just to download on it; uncompressed, about 21 s. `nfr-budget.md` does not say which
   profile it means. You need to choose one before any number is worth recording (OPS-17).

### Where I agree and where I do not

| Item | My view |
|---|---|
| OPS-1 compression first | **Agree.** Checked today: dev sends the 175 KB login page with no `Content-Encoding`, even when the browser asks for gzip. There is **no CDN** (a service that serves files from a location close to the user) in front. The DNS is at Cloudflare, but the address is the server's own and the response carries no Cloudflare headers, so Cloudflare is not in the path. Production uses the same nginx, so it is the same there (inferred — I did not probe production). This answers open question 4: the "before" is 1.04 MB on the wire |
| OPS-2 preview page + one swap | **Agree**, with OPS-12 added |
| OPS-3 rollback by revert | **Disagree in part.** See §4.1 and OPS-14 |
| OPS-4 after go-live settles | **Agree.** Add OPS-16 (the swap goes out in a release of its own) |
| OPS-5 no migrate, no build | **Agree, and checked** against Frappe v16.33.1 source on the local bench. See §4.2 |
| OPS-6, OPS-7 checks follow includes; split pushed early | **Agree.** Add OPS-13 (server time before and after the split) |
| OPS-8 cached files after the swap | **Agree.** One warning for later: today everything is inside the HTML, and the HTML is never cached (`Cache-Control: no-store`). That is why a rollback is clean for phones today. Once script moves into files, a rollback also needs versioned file addresses, or phones keep the new script with the old page |
| OPS-9 measure before and after | **Agree.** Made specific in §4.4 |
| OPS-10, OPS-11 | **Agree** |

---

## §4 Strategy · 2026-09-22 · hrms-devops-engineer

### 4.1 The real rollback time

**Answer: about 10 minutes of machine time, 12–15 minutes from the moment someone
decides.** That is by redeploying the previous production image with migrations off. It
fits the 15-minute budget only just, and only if the runner is free. Fixing the wasted
wait (OPS-15) would bring it to about 3 minutes (**estimate**: 9 min 33 s minus the
6 min 54 s wait).

**Path A — redeploy the previous image (the fast path).** Measured on dev today, run
`35754074313`, migrations off, image already on the server:

| Part | Time | Source |
|---|---|---|
| Plan job and runner pick-up | ~12 s | measured |
| nginx gate and disk check | ~3 s | measured |
| Backup of every site | 1 min 15 s (production on 20 Sep: 1 min 07 s) | measured |
| Image pull (already on the server) | 2 s | measured |
| Recreate and start containers | ~32 s | measured |
| **Waiting for `bench version`, which never succeeds** | **6 min 54 s** | measured; cause checked (OPS-15) |
| Image clean-up, maintenance flag, nginx restart | ~45 s | measured |
| Smoke test and worker check | ~6 s | measured |
| **Total** | **9 min 33 s** | measured, dev |

For production the same path has not been timed with migrations off. **Estimate: 9–11
minutes**, based on the dev run above and on production's 20 Sep run, where the backup
and the 7-minute wait took the same time as on dev. Add 2–5 minutes of human time to
notice, pick the tag and start the run.

The production image from before the swap is still on the server after the swap: the
deploy keeps the two newest `prod-` images. So there is no pull.

**Path B — `git revert` and a normal deploy (what OPS-3 describes).**

| Part | Time | Source |
|---|---|---|
| Build the image on `main` | 3–21 min (last three `main` builds: 2 min 44 s, 13 min 51 s, 20 min 54 s) | measured |
| Deploy with migrations, 4 production sites | 23 min 20 s on 20 Sep, which included a 5-minute pull and 10 data patches | measured |
| The same deploy with no patches | 15–18 min | **estimate**: 20 Sep minus the patch time |
| If the revert goes through `dev` first, as `CLAUDE.md` §1 asks | +15–30 min | dev deploys today took 9–22 min, plus a dev build |
| **Total** | **about 30–75 minutes** | |

**Two things can make either path slower, or visible to users.**

- **There is one runner.** The server has one self-hosted runner, and it runs one job at
  a time. A dev deploy already running (9–22 minutes today) makes a production rollback
  wait in line. On 20 Sep the production job waited **3 h 12 min** before it started; I
  could not find why.
- **A normal deploy puts every production tenant in maintenance mode.** On 20 Sep that
  window was about 6 min 45 s of "503" for all four sites. Path A with migrations off has
  no maintenance window at all.

### 4.2 Does anything in Wave 1 need a migrate, a build or a cache clear?

**No migrate and no build. No cache clear on dev or production. One care point for the
new page, and one for the local bench.** Checked against Frappe v16.33.1 and Jinja 3.1.6
on the local bench, read-only, today.

| What 034 adds | Migrate? | Build? | Cache clear? | Why |
|---|---|---|---|---|
| `frame_api.py`, `inbox_api.py` | No | No | No | Whitelisted functions are imported when called. No doctype, no fixture, no hook |
| ~25 Jinja include files | No | No | No | Templates are read from the app folder, which is baked into the image (`deploy/Dockerfile` copies the whole app). `bench build` only bundles `public/` files; includes are not part of it |
| `www/hrms-employee-next.html` + `.py` | No | No | Normally no — see below | Frappe finds a `www` page by looking for the file on disk on every request. There is no routing table to rebuild |
| `design_system.html`, `brand_color.html` edits | No | No | No | Templates |
| `_search_scope`, `_pending_approvals_scope` bodies | No | No | No | Python only |
| The swap commit (deletes the preview page) | No | No | No | The deleted page simply stops being found |

The care points:

1. **Frappe keeps the finished HTML of a `www` page for 30 minutes, unless the page says
   `no_cache`.** The kept copy is stored by address only, not by user, and it is used
   before `get_context` runs. Today's page sets `context.no_cache = 1`, so it is safe.
   **The preview page must set it too.** Without it, the first System Manager's page
   would be kept and handed to the next person who opens the address, and the System
   Manager check in `get_context` would not run for them (OPS-12).
2. **Frappe remembers "not found" answers in Redis until the cache is cleared.** If
   anyone opens `/hrms-employee-next` on a site before the file exists, that site keeps
   answering "not found" after the file arrives. Redis keeps its data across a deploy. A
   normal deploy runs `clear-cache`, which empties this list. A Path A rollback does not.
   On the local bench `developer_mode` is off, so this applies there too.

**Answer to open question 3:** no `clear-cache` is needed on the local bench to pick up
new or changed include files — Jinja checks the file's date and reloads by itself. Only
a remembered "not found" needs clearing, and the narrow command for that is
`bench --site <site> clear-website-cache` — it still needs your approval. Changes to
Python files that are already loaded need the bench process restarted (lesson 12).

**Does the split into ~25 includes change build or asset behaviour?** No for the build and
the assets. **Possibly yes for server time** — see OPS-13. Frappe keeps only **32**
compiled templates per worker process (`cache_size=32` in `frappe/utils/jinja.py`). Today
the page needs about 10: the page, `design_system`, `brand_color`, and Frappe's own
`web.html`, `base.html` and their includes. After the split it needs about 35. That is
more than the store holds, so the oldest are pushed out and compiled again on a later
request. Compiling ~1 MB of template text again on each visit could add tens to hundreds
of milliseconds to every page load (**estimate** — not measured). Step 1's byte-for-byte
test proves the output is the same. It does not prove the time is the same.

### 4.3 Install order, image, Compose and CI

| Topic | Advice |
|---|---|
| Install order | Nothing to install. Order of releases: (1) 033's private package and 026's worker guard run on production at least once, in their own release; (2) slice 036 compression live on dev, then on production; (3) the swap on dev; (4) the swap on production after go-live settles, in a release of its own (OPS-16). This fits OPS-1's order |
| Image | No change. It grows only by the new text files |
| Compose | No change. No new service, queue or worker |
| `deploy/nginx.conf` | **034 must not touch it.** Compression belongs to 036. A dev push that edits it restarts production's proxy with it |
| Migrations and patches | None. See OPS-18 for a guard |
| Version pinning | Nothing new to pin. No new app, package or outside call |
| Shared nginx | Each dev deploy restarts the nginx that also serves production (a few seconds). 034's pushes to dev should be batched, as `CLAUDE.md` §1 already asks |

### 4.4 How the speed budget is measured

| What | On what | Tool | Pass line |
|---|---|---|---|
| Skeleton on screen | Local copy, with the same compression as the target (none until 036; gzip after) | Chrome DevTools, the profile chosen in OPS-17, 4× CPU slow-down, cache off. Time from the first byte of HTML to the first paint of the shell | ≤ 300 ms, median of 5 loads. Also record the bytes that come **before** the shell's markup — that is what decides this number |
| Home usable | Same | Same, 20 loads, with a `performance.mark` when `get_frame` has answered and Home's first card has drawn | ≤ 2.5 s at p95 (the 19th of 20 loads) |
| Server time for the page | Local copy, logged in, 20 warm requests | `curl` with `time_starttransfer` | After the split, no more than 10 % slower than before (OPS-13) |
| `get_frame`, `get_nav_counts` | Test fixtures at 250 and 1,000 employees | The existing query-count test pattern (as in `test_hr_analytics_scope_012`), plus a timer over 20 calls | ≤ 15 queries; ≤ 500 ms p95 |
| Start-up calls | Local copy | DevTools network log | 2 calls, no 1.5 s delay |
| Bytes on the wire | Local copy, then dev | DevTools "transferred" size | Record only |

**When:** (0) on `origin/dev` before any 034 commit — the baseline; (1) after the split;
(2) on the preview page before the swap; (3) on dev after 036 is live; (4) on dev after
the swap. Dev measurements only when you ask for them. On production, only on your
say-so, from an ordinary logged-in browser — never a server command. Each number goes in
the implementation notes with the date and the commit.

### 4.5 New items

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| **OPS-12** | Recommend: the preview page's `get_context` sets `context.no_cache = 1`, as today's page does, and a test pins it | Frappe keeps a page's finished HTML for 30 minutes unless it says `no_cache`. The kept copy is shared by everyone and skips `get_context`, so it skips the System Manager check | The preview page, with a System Manager's details, is served to any logged-in user for up to 30 minutes | Recommend | |
| **OPS-13** | Recommend: time the page on the server before and after the split (§4.4). If it is more than 10 % slower, use fewer, larger include files (about 15 in total), or bring OPS-31 forward | Frappe keeps 32 compiled templates per worker. About 35 will not fit, so some are compiled again on later visits | Every page load gets slower on the server, and the byte-for-byte test cannot see it | Recommend | |
| **OPS-14** | Recommend: rewrite OPS-3's rollback as two steps. (1) Redeploy the previous production image with migrations off: *Actions → Deploy → Run workflow*, `environment: production`, `image_tag: <previous prod tag>`, `image_package: alvoraa-app`, `run_migrations: false` — **for the user to approve**. (2) Afterwards, `git revert` the swap commit through dev and main in the usual way. Write the previous tag down before the swap goes out | Step 1 takes about 10 minutes and needs no build. Step 2 alone takes 30–75 minutes | A 15-minute promise that the chosen method cannot keep | Recommend | |
| **OPS-15** | Recommend: a small DevOps fix, outside 034, so the deploy waits for something that can succeed — for example the same `ping` the health check already uses — instead of `bench version` | `bench version` crashes on our image, so every deploy waits the full ~7 minutes, and the loop hides the crash | Every deploy and every rollback is ~7 minutes slower than it needs to be. If the backend really were broken, the loop would not say so | Recommend | |
| **OPS-16** | Recommend: the swap goes to production in a release that carries only the swap, or the swap plus changes that need no migration. Not in the same release as the first production run of 033 or 026 | A Path A rollback rolls back the whole image, not one commit | Rolling back the frame also rolls back unrelated fixes; or a deploy problem and a frame problem arrive together | Recommend | |
| **OPS-17** | Consider: name the test profile in `nfr-budget.md`. My suggestion: Chrome "Slow 4G" (1.44 Mbps, 562 ms delay — the preset that used to be called "Fast 3G") with 4× CPU slow-down. Chrome's "3G" preset (400 kbps, 2 s delay) cannot meet 2.5 s for any page over about 100 KB | The budget says "3G" but not which 3G | Numbers from different profiles get compared, or the budget is failed by definition | Consider | |
| **OPS-18** | Consider: a CI check on the swap commit that fails if it touches `patches.txt`, `hooks.py`, doctype `.json`, `fixtures/` or `public/` | Keeps "no migrate, no build" true, so the Path A rollback stays clean | A later edit makes the swap need a migrate, and the 10-minute rollback stops being safe | Consider | |
| **OPS-19** | Recommend: no pushes to dev in the hour after the production swap | One runner, one job at a time | A rollback waits behind a dev deploy for 9–22 minutes | Recommend | |

### Things for you to decide

1. OPS-17 — which phone profile the 2.5 s and 300 ms budgets mean.
2. OPS-14 — the two-step rollback in place of "revert and deploy".
3. OPS-15 — whether the `bench version` wait is fixed, as its own small change, before
   the swap reaches production.
4. OPS-16 — the swap travels alone.
5. Open question 2 (what "settled" means) is still yours.

### Checks I ran, all read-only, 2026-09-22

- GitHub Actions run history and step times for Deploy and Build Image (`gh run list`,
  `gh run view`); production environment rules (a branch rule only, no reviewer); the
  runner list (one runner, online).
- One command on the **dev** backend over Tailscale: `bench version` (it fails, see
  above). Nothing on production.
- One ordinary HTTPS request to `https://dev.alvoraa.co/alvoraa-login` to read its
  headers. A DNS look-up of `alvoraa.co`.
- Frappe v16.33.1 and Jinja 3.1.6 source on the local bench (`hrlocal-bench`), read-only.

Sources, checked 2026-09-22:
[Chrome DevTools network reference](https://developer.chrome.com/docs/devtools/network/reference/),
[Chrome DevTools throttling](https://developer.chrome.com/docs/devtools/settings/throttling),
[Lighthouse throttling notes](https://github.com/GoogleChrome/lighthouse/blob/main/docs/throttling.md).

---

## §3b · 2026-09-22 (later the same day) · Decisions recorded · hrms-fullstack-engineer

Earlier sections are not rewritten (handoff contract rule 6). This section records what
the user decided after reading §4, and what each decision does to the items above.

| Item | Decision, 22 Sep 2026 | Effect |
|---|---|---|
| **OPS-1** compression first | **Taken as its own slice** (slice 036), because it speeds up the live site today. 034 does not build it | Unchanged as a release gate: compression is live on dev before the swap goes to dev, and live on production before the swap goes to production |
| **OPS-3** rollback by revert | **Superseded by OPS-14** | Read OPS-3 as history. The rollback is OPS-14's two steps |
| **OPS-14** two-step rollback | **Accepted.** Rollback is redeploying the previous image (about 10 minutes), not revert-and-deploy (30–75 minutes). The `git revert` follows afterwards, so `main` matches what production runs | The previous production image tag is written down before the swap goes out, and it goes in the release-readiness note |
| **OPS-16** the swap travels alone | **Accepted.** The swap ships in a release of its own | It does not travel with 033's or 026's first production run |
| **OPS-4** "after go-live settles" | **Accepted, with the meaning now fixed:** at least **10 working days** after DTC goes live; **no client-blocking issue for 5 days**; **outside payroll close**; **compression live**; and **the frame on dev for 5 days** | Closes open question 2. These five become release-readiness checks |
| **OPS-17** which phone profile | **Accepted:** a mid-range phone on **Chrome "Slow 4G" with 4× CPU slow-down**. The undefined "3G" is not used | Every speed number in this slice is measured on that profile. `nfr-budget.md` is the DevOps engineer's to correct, not this slice's |
| **OPS-12** `no_cache` on the preview page | **Accepted** — it is also security requirement SEC-1 | A test pins it |
| **OPS-13** time the page on the server before and after the split | **Adopted by the engineer.** It costs one `curl` loop | If the split makes the page more than 10 % slower on the server, the include files are merged into about 15, or OPS-31 is brought forward |
| **OPS-19** no pushes to dev in the hour after the production swap | **Adopted by the engineer** | Written into the release note |
| **OPS-15** the wasted ~7-minute wait on `bench version` | **Still the user's** — a DevOps fix outside 034 | If it is not fixed, the rollback stays about 10 minutes instead of about 3 |
| **OPS-18** CI guard on the swap commit | **Still the user's** — it edits a workflow file, which is not part of a feature slice | Without it, a later edit could make the swap need a migration, and the fast rollback would stop being safe |

### One thing this changes in the spec

The speed acceptance checks now read "Chrome Slow 4G, 4× CPU slow-down, on the local
copy, cache off", and the 2.5 s target is stated as depending on slice 036 being live.
`02-functional-spec.md` carries that wording.

### Still open for the DevOps engineer

- OPS-15 and OPS-18, if the user takes them.
- §5 (release readiness) is written when the build is done.
