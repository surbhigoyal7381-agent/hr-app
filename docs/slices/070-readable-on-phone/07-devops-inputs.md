# 070 Readable on a phone — DevOps inputs

## §1 Brief — 2026-10-24

**Answer first: this slice adds nothing to run.** No new container, worker, job, volume,
route or dependency. Run cost: zero extra. **No red flag that should change its priority.**

What I checked (all **Fact**, read in this worktree at `6aaf9ffd`):

- **Phones will get the new CSS and JS.** The portal pages add `?v={{ asset_version }}`
  to every `css/ess/*` and `js/ess/*` link (`www/hrms-employee-next.html`,
  `www/hrms_employee.py:28`, `www/hrms_employee_next.py:84`). `asset_version` is
  `get_build_version()`, the modified time of `sites/assets/assets.json`.
  `scripts/refresh_bench_files.sh` (ALV-112, e7efecd) rewrites that manifest last on
  every deploy (`deploy.yml:505`). New deploy, new address, so the 30-day `immutable`
  cache in `deploy/nginx.conf:211-218` and `:414-418` cannot pin old files.
- Template parts are cached under the same build version (`ess_parts.py:51`), so they
  refresh with the deploy too.
- The only service worker is on `/checkin` (`field-checkin.html:1215`), not the portal.
- No web font is loaded; `frame.css` uses the phone's own system fonts.

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-1 | Recommend: no new web font, icon font or image. Get bigger text from the system font. | NFR: employee page ≤ 2.5 s on a 3G phone (`nfr-budget.md`). A web font is often 20-100 KB per weight (**estimate**, typical sizes, not measured). | Slower first paint on cheap phones — the opposite of this slice. | Recommend · P3 | |
| OPS-2 | Recommend: no change to `deploy/nginx.conf` or any route. If one turns up, run `scripts/check_nginx_parses.sh` first. | One nginx serves dev and production (lesson 13). | A dev deploy would restart the live site's proxy. | Recommend · P2 if it happens | |
| OPS-3 | Recommend: add any new `ess` CSS/JS file with the same `?v={{ asset_version }}` stamp. Existing tests in `test_portal_split_034.py` and `test_panel_source_042.py` already check it. | A link without the stamp is cached for 30 days. | Phones keep last release's file for a month. | Recommend · P2 | |
| OPS-4 | FYI: the "Try again" retry should be one tap by the user, not an automatic loop. | An automatic retry on a failing server adds load when it is least able to take it. | Many phones hammering a sick backend. | FYI · P3 | |

**Unknown:** I did not check that the dev or production volume's `assets.json` really
changes on each deploy today; I read the script, I did not run it. Release readiness
(§5) should confirm it by comparing the `?v=` value before and after the dev deploy.

**Subtract pass:** removed a page-weight measurement row — nothing heavy is being added,
so there is nothing to measure at this stage. I will measure in §2 if the design adds weight.

## §2 Design — 2026-10-24

**Answer first: no change to run cost or page weight worth measuring. One real gap: a resent expense claim or advance creates a second record — the server has no guard.** All **Fact** unless marked, read in this worktree at `6aaf9ffd`; nothing run on any server.

- **Weight:** `frame.css` is 14,575 bytes today; a phone-only `@media` block and a small timeout helper add an **estimated** 1-3 KB before gzip — well inside the ≤ 2.5 s 3G budget. No font, image or new file.
- **Timeouts:** nginx `proxy_read_timeout 120s` (`deploy/nginx.conf:165`), gunicorn `--timeout 120` (`docker-compose.app.yml:263`). 15 s is far below both, so the client always gives up first. **An abandoned request keeps running on the server and still commits** (`doc.insert` + `frappe.db.commit()`). That is why "Try again" must never blindly resend a write.
- **Leave resend:** `apply_leave` (`hr_api.py:2475`) calls `doc.insert`, which runs HRMS `validate_leave_overlap` (Open/Approved, same employee). So a duplicate leave is already refused server-side; the check-then-resend read only turns that error into plain words. `employee`, `leave_type`, `from_date`, `to_date` all carry `search_index: 1` in `leave_application.json`. One read per user tap: load is negligible.
- **Expense / advance:** `apply_expense_claim` (`hr_api.py:2429`) and `submit_advance_request` (`:2796`) insert with no duplicate check. The designer is right.
- **Caching:** new CSS/JS keeps the `?v={{ asset_version }}` stamp (OPS-3). Write calls and the own-leave read are POST/whitelisted calls — never cache them.
- **Never public:** the own-leave read must use the session's own employee (`_get_employee()`), never an employee id sent by the phone.

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-5 | Recommend: for expense and advance, after a timeout show "We could not confirm — check your list before trying again" and link to the list; no one-tap resend. Cheapest rung; no server change. | Abandoned request still commits; server has no guard. | Double claims or advances that HR must spot and cancel; a paid duplicate is money out. | Recommend · P2 | |
| OPS-6 | Consider: if the PM wants one-tap resend for expense/advance too, the same check-then-read pattern (own list, same date + amount, last few minutes) — client-side only. | Matches leave. | More JS to test; matching on amount can miss or wrongly match. | Consider · P3 | |
| OPS-7 | Recommend: the leave check reads only the caller's own records via `_get_employee()`; no `employee` argument. | Privacy — a parameter is an enumeration hole. | Any employee could list another's leave. | Recommend · P2 | |
| OPS-8 | FYI: no nginx or gunicorn timeout change is needed for this slice. | 15 s < 120 s. | — | FYI · P4 | |

**Subtract pass:** removed a row proposing a server-side request key for expenses — it is new code and a new field when a plain message meets the need. Removed a load estimate table; one indexed read per tap needs none.

## §3 Requirements — 2026-10-25

**Answer first: eight build requirements, one decision for Surbhi (OPS-R8). Nothing new to run.** Design approved 25 Oct (D2 = OPS-5 as written). All rows are **Fact** from §1/§2 reads unless marked; nothing run on any server.

| ID | Requirement the build must meet | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-R1 (was OPS-3) | Every changed or new `css/ess/*` / `js/ess/*` link carries `?v={{ asset_version }}`; the existing tests in `test_portal_split_034.py` / `test_panel_source_042.py` stay green and cover any new file. | nginx caches these 30 days, `immutable`. | Phones keep the old file for a month. | Recommend · P1 | |
| OPS-R2 (was OPS-1, OPS-2, OPS-8) | No new font, image, file host, nginx or gunicorn change. If `deploy/nginx.conf` is touched after all, `scripts/check_nginx_parses.sh` must pass first. | 3G ≤ 2.5 s budget; one nginx serves dev and production. | Slower pages; a dev deploy restarts the live proxy. | Recommend · P2 | |
| OPS-R3 (was OPS-4) | No automatic retry anywhere. "Try again" is one user tap, leave form only; it runs the own-leave check before resending. | An abandoned request still commits on the server. | Phones hammer a sick backend; duplicate records. | Recommend · P1 | |
| OPS-R4 (was OPS-5) | Expense and advance forms: after a timeout, "Look in your list before you send it again" + Close; no resend button (D2). | Server has no duplicate guard there. | Paid duplicate claims or advances. | Recommend · P1 | |
| OPS-R5 (was OPS-7) | The own-leave read takes **no** `employee` argument; it uses `_get_employee()` from the session only. Test: a call with a foreign employee id still returns only the caller's rows. | Privacy — an id parameter lets anyone list others' leave. | Any employee reads another's leave. | Recommend · P1 | |
| OPS-R6 | Post-deploy check on dev (read-only, **for the user to approve**): fetch the portal page before and after; the `?v=` value must change, and the new CSS file must contain the phone `@media` block. Then open the page on a real phone. | §1 Unknown: I read the refresh script, never saw it run. | A "green" deploy that serves last release's CSS. | Recommend · P2 | |
| OPS-R7 | Rollback: no migration and no schema change, so roll back by redeploying the previous tag with migrations off; the refresh step bumps `?v=` again. Confirm that tag exists in the package dev pulls from before pushing. Allow ~7 min (measured 22 Sep, lesson 22). | Production only pulls during a deploy (lesson 20). | No way back if the tag is missing. | Recommend · P2 | |
| OPS-R8 | No new endpoint or table to count client timeouts. nginx already logs 499 (phone gave up) in its access log; count those on dev for a week after release if wanted. | Cheapest rung — the data already exists. | Without it we will not know how often the 15 s limit fires. | Consider · P3 | **Surbhi: count 499s or not?** |

**Subtract pass:** removed a client-side error-reporting call (new endpoint, new noise) and a separate "unstamped asset" CI script — the existing tests already do that job.

## §4 Strategy — 2026-10-25

**Answer first: I agree with the plan. Nothing to install, no image, Compose or migration change. One real risk: after 15 s, `api()` now calls the error branch *and later* the success branch on the same request — 75 callers were never written for both.** Read in this worktree at `6aaf9ffd`; nothing run, no timings taken.

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-S1 | FYI: install order none; no image, Compose, nginx or migration change. Rollback = OPS-R7 (previous tag, migrations off). | Fact: four files, all CSS/JS/HTML (impact analysis §3). | — | FYI · P4 | |
| OPS-S2 | Recommend: gates before commit — `scripts/check_app_integrity.py`; every jsdom test that stubs `frappe.call` or `gpFetch`; `test_portal_split_034.py` / `test_panel_source_042.py` for the `?v={{ asset_version }}` stamp (OPS-R1). Update `portal_leave_063_test.js:281` (R-48) — it fails `apply_leave` through the `api()` stub; under E1 the send goes through `gpFetch`, so the stub must move or R-48 tests nothing. | Fact: read the test lines. | A green suite that no longer touches the leave send. | Recommend · P1 | |
| OPS-S3 | Recommend: an `api()` time-out must never re-enable a *write* button. Writes still on `api()`: `action_leave`, `cancel_leave`, `submit_shift_request`, `submit_attendance_request`, `submit_leave_encashment`, `publish_policy`, `save_policy`, `save_manager_note`, `update_goal_status`, `submit_goal_evidence_portal`, `do_checkin`. Their error branches now fire on a slow answer while the server still commits. | Inference from `api()` (`portal.js:5`) and §2: an abandoned request still commits. | A tap after "no answer" makes a second check-in, approval or request. | Recommend · P1 | |
| OPS-S4 | Recommend: test the slow path once per kind, in jsdom, with a stub that answers at 16 s: one read (error box, then replaced by data, once), one write (no resend offered, button stays off). Then on the local bench time the likely-slow reads on ppj.localhost: `get_hr_analytics`, `get_team_scorecard`, `get_manager_dashboard`, `hr_document_compliance`, `get_all_active_employees`. Any over 10 s needs a decision before dev. | **Unknown**: I have no timing for these; they are whole-company reads (`hr_api.py:808`, `:1390`, `:532`, `:3911`). File upload uses its own `fetch` (`portal.js:3087`) and is not affected. | HR sees "no answer" on a report that would have loaded at 18 s. | Recommend · P2 | |
| OPS-S5 | FYI: 066-grooming also edits `acRow`/`acPaint`. Whichever reaches `dev` second rebases and re-runs both slices' JS tests. | Fact: impact analysis §1. | A silent lost line in a hot file. | FYI · P3 | |

**Where I stand on the engineer's plan.** Agree: one fix in `api()` rather than 61; keep `frappe.call` (no `fetch` rewrite); E1 (sends through the existing `gpFetch`); E2 (AC-22's ~25 places, others get the limit and existing text). Add only OPS-S3: the plan covers late answers for reads but says nothing about `api()` writes.

**Subtract pass:** removed a row proposing a longer limit for report calls — not justified until OPS-S4 gives a number.

## §5 Release readiness — 2026-10-25

**Verdict: ready for dev once Surbhi says push. Not ready for main until AC-62 and AC-64 pass on dev.** **Fact** (`git diff --stat origin/dev...HEAD`, base `f207e82c`): CSS, JS, three templates, tests, docs only — no `.py` outside tests, no patch, no doctype JSON, no `nginx.conf`, Compose, Dockerfile or workflow. No migration, no nginx restart. Page weight +7.5 KB gz JS, +1.4 KB gz CSS (04, measured) — accepted as D2/P3.

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-RR1 | Rollout, **each step FOR SURBHI'S APPROVAL**: (1) `git fetch origin dev && git rebase origin/dev`, re-run the JS suite if anything came in; (2) `git push origin slice/070-readable-on-phone:dev` — build + automatic Deploy to devstack; (3) the checks in OPS-RR2 plus a week of use; (4) only on her word, the normal `dev` → `main` release. Nothing run by me. | Lessons 1, 14; CLAUDE.md §1. | A push nobody tested on dev reaches production. | Recommend · P1 | |
| OPS-RR2 | After the dev deploy, read-only, **for Surbhi to approve** (on the server over Tailscale): `docker ps --filter label=com.docker.compose.project=devstack --format '{{.Names}} {{.Image}}'` — every app container `alvoraa-app:dev-<new sha>`, `devstack-backend-1` included; `docker exec devstack-backend-1 stat -c %Y sites/assets/assets.json` before and after — the number (the `?v=` value) must change, and the page source of `/hrms-employee` (logged in) must show the new `frame.css?v=`; `curl -s https://dev.alvoraa.co/assets/alvoraa_portal/css/ess/frame.css \| grep -c "Slice 070"` must print 1 (prints 0 = old CSS served; a blank line = curl failed, lesson 19). Then a real cheap Android on 3G-ish data (AC-64). | §1 Unknown; lesson 2; memory: deploys did not always refresh `sites/assets`. | A green deploy serving last release's CSS. | Recommend · P1 | |
| OPS-RR3 | Rollback (OPS-R7): Deploy by hand with `environment: dev`, `image_tag: dev-f207e82`, `package: alvoraa-app`, `run_migrations: false` — **for Surbhi to approve**. **Fact** (gh api, 25 Oct): `dev-f207e82` exists in `alvoraa-app` and is what dev runs now (Deploy run 40192156354). Allow ~7 min (**estimate**, measured 22 Sep, lesson 22); the last full dev deploy took 16 min 45 s with migrations (**measured** from run times, 25 Oct). For main: read production's current `prod-` tag from its last Deploy run before the main push — **I could not check it today**. | No schema change, so the old image runs on the same database. | No tested way back. | Recommend · P1 | |
| OPS-R8 (if she says yes) | Count portal calls the phone gave up on (499) on dev, on day 7, read-only, **for Surbhi to approve**: `docker logs --since 168h compose-nginx-1 2>/dev/null \| grep 'dev\.alvoraa\.co' \| grep '"[A-Z]* /api/method/' \| awk '$9==499{split($7,a,"?");c[a[1]]++} END{for(k in c) print c[k],k}' \| sort -rn`. Drop the `$9==499` test to get the total for a ratio. | Data already exists. **Inference:** nginx:alpine's default log has no host field, so dev is picked out by the Referer, which browsers send on same-site calls; one nginx serves both stacks, so this reads the production container's log (read only). `docker logs` loses everything if nginx is recreated — run before any production deploy. Container name `compose-nginx-1` is `[ASSUMPTION]`; confirm with `docker ps --filter name=nginx`. | We never learn how often the 15 s limit fires. | Consider · P3 | |
| OPS-RR4 | Monitoring: nothing new. Watch the 499 count (OPS-R8) and Error Log on dev for the week; `worker-health.yml` is unchanged. | No new job, queue or route. | — | FYI · P4 | |

**Subtract pass:** removed a separate migration dry-run row (no migration) and an nginx `-t` gate (no nginx change). Nothing left behind: I ran only `git` and read-only `gh` commands.
