# Production release: taking `dev` to `main` — September 2026

**Advice and a plan only. I changed nothing, pushed nothing, deployed nothing, and ran no
command that writes anywhere. Everything marked USER needs your own hands.**

Written 2026-09-19. Every number below was measured today unless it says **estimate**.

---

## 0. Answer first

**Go, with three things fixed before you start — and none of them is the code.**

1. **A production deploy from 17 September is still sitting at "pending" and it blocks the
   new one.** Run `35211643501`. The Deploy job's concurrency group is
   `deploy-production` with `cancel-in-progress: false`, so **a new production deploy will
   queue behind it and never start**. Cancel it first (§1 step 2). If it ever woke up on
   its own it would put the *old* code (`prod-2fc623c`) over the new release.
2. **There is no approval gate on production.** I checked the `production` environment: its
   only protection rule is `branch_policy`. There are **no required reviewers**. So a push
   to `main` starts a production deploy **by itself, with no prompt**. The comment at the
   top of `deploy.yml` says otherwise; the comment is wrong. Decide before the day whether
   you want that stop button (§7, D-1).
3. **The `demo/` guard does not fully work on this merge.** Three files —
   `demo/README.md`, `demo/link_employee_users.py`, `demo/setup_performance.py` — changed
   on `dev` only. A `merge=ours` driver is only called when a file changed on *both* sides,
   so git will take dev's version of those three silently and they will land in `main`. The
   18 `demo/pp_jewellers/` files are safe, because main has stubs for them. §1 step 5 has a
   belt-and-braces fix that does not depend on the driver at all.

**What you are releasing:** `origin/dev` = `886c8c4`, deployed to dev today and verified.
**Recommend releasing exactly that, not your local `dev`.** Your local branch is four
commits ahead (store-HR scoping, tenant logo copy). Those have never run on dev. Releasing
what you tested is the whole point of the three-stage rule.

**Size of the change:** 308 commits, 450 files, and **10 data patches** production has
never run. Three of them rewrite existing rows.

---

## 1. The order of operations

Times are **estimates** based on today's dev deploy and the last production one.

### Step 1 — ME · confirm nothing moved (read-only, 1 minute)

```
cd C:/Surbhi-Git/hr-app
git fetch origin
git rev-parse origin/dev origin/main
```

Expect `886c8c4…` and `2fc623c…`. If `origin/dev` has moved, another session pushed — stop
and re-read this whole plan, because the tested commit is no longer the tip.

### Step 2 — USER · cancel the stuck production run

```
gh run cancel 35211643501
gh run list --limit 5 --json databaseId,name,status,conclusion,headBranch
```

Expect the run to show `cancelled`. **If you skip this, the release deploy will sit in the
queue for ever and look like a hung runner.**

### Step 3 — USER · decide about the four local commits

Recommend: **leave them.** Release `886c8c4`. Push the four to `dev` after this release
lands, in the ordinary way, and they go to production in the next one.

If you want them in, they have to go to `dev` first, get a dev deploy and get tested — that
is another 40 minutes plus your testing time, on the night of a production release. I would
not.

### Step 4 — USER · check the email setting before anything else

The container start-up writes the global mute flag from `deploy/envs/production.env` on
every deploy:

```
bench set-config -gp mute_emails "$MUTE_EMAILS"
```

So **this deploy will overwrite `mute_emails` in `common_site_config.json` with whatever
that file says.** I have not read that file and will not. Read the one key:

```
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@100.127.29.62 \
  "grep -E '^MUTE_EMAILS=' /var/www/html/hr-app/deploy/envs/production.env"
```

| What it says | What happens at deploy |
|---|---|
| `MUTE_EMAILS=1` | Global mute stays on. `aahr.alvoraa.co`'s per-site unmute lives in that site's own `site_config.json` and is **not** touched, so aahr keeps sending. This is today's state and the safe one. |
| `MUTE_EMAILS=0` | **Every production site starts sending email the moment the containers come up** — including `demo.alvoraa.co` with its 157 employees and 363 open appraisals. |

**Recommend: confirm it is `1` and release with the mute still on.** Unmute for go-live as a
separate, deliberate change, on a different day, after you have looked at the queue. Two big
changes on one night is how you end up not knowing which one broke things.

### Step 5 — USER (or ME on your word) · build the merge, in its own worktree

Do this in a **separate worktree**, not the shared checkout — other sessions are using
`C:/Surbhi-Git/hr-app` (CLAUDE.md §1).

```
cd C:/Surbhi-Git/hr-app
git config merge.ours.driver true
git worktree add -b release/2026-09-main .claude/worktrees/release-main origin/main
cd .claude/worktrees/release-main
git merge --no-commit --no-ff origin/dev
```

**Expect one conflict: `deploy/nginx.conf`.** Both branches changed the certificate lines.
**Take dev's version** — it already has the wildcard certificate paths *and* the real
client-address hardening, and it is the file the running nginx is serving right now:

```
git checkout --theirs -- deploy/nginx.conf
git add deploy/nginx.conf
grep -n "alvoraa-wildcard" deploy/nginx.conf      # expect 4 hits
```

**Then the `demo/` guard, which does not depend on the merge driver:**

```
git checkout HEAD -- demo/
git add demo/
git diff --cached origin/main -- demo/            # expect NO OUTPUT
```

No output means `main`'s `demo/` folder comes through the merge unchanged. If anything
prints, stop and look — a seed script is about to land in `main`.

Check nothing else is left unresolved, then read what is coming in:

```
git status --short | grep -E "^(UU|AA|DU|UD)"     # expect no output
git diff --cached --stat | tail -5
```

### Step 6 — USER (or ME on your word) · run the gates on your machine, before the push

```
python scripts/check_nginx_conf.py
bash scripts/check_nginx_forwarded.sh deploy/nginx.conf
python scripts/check_api_paths.py --max 2
python scripts/check_app_integrity.py
node scripts/check_portal_handlers.js
node scripts/check_undefined_js.js
```

All must pass. `check_api_paths.py --max 2` — never raise that 2.

Then commit:

```
git commit --no-edit
git log --oneline -1
```

### Step 7 — USER · the push (your hands only)

```
git push origin release/2026-09-main:main
```

**This is the point of no return for the code.** It starts Build Image on `main`, which
produces the image tag `prod-<first 7 of the merge commit>`. Write that tag down — you need
it for the dispatch and for the rollback comparison.

**What happens next, and why the order works.** The Deploy workflow fires on
`workflow_run`, and GitHub runs the copy of the workflow file **on the default branch**.
The push you just made *is* main, so by the time Build Image finishes (10–15 minutes) main
already carries the fixed `deploy.yml` — with the git-token fetch, the registry sign-in, the
nginx parse gate, the image cleanup and the backup. The one push both lands the fix and
uses it.

**If GitHub is still holding main's old file** (a race I cannot rule out — see §6), the
Deploy job fails within seconds at:

```
fatal: could not read Username for 'https://github.com': No such device or address
exit code 128
```

**What that costs:** a full production backup will already have been taken (harmless), the
tree on the server is untouched, production keeps running `prod-d99ba99`, and the old
"Restore service" step restarts `compose-nginx-1` once, unchecked — about 2 seconds of 502
on every hostname. The config on disk at that moment is the one nginx is already serving, so
it comes back. Then do step 8.

### Step 8 — USER · the deploy, by hand if it did not start itself

```
gh workflow run Deploy --ref main \
  -f environment=production \
  -f image_tag=prod-<sha> \
  -f run_migrations=true

gh run list --workflow Deploy --limit 3
gh run watch <run id>
```

`--ref main` makes GitHub use **main's own copy** of the workflow, which is the fixed one.
This is the same trick that made the dev deploys work on 18 and 19 September.

### Step 9 — the deploy runs itself (~35–50 minutes, **estimate**)

In order, with what each step means:

| # | Step | What it does | If it fails |
|---|---|---|---|
| 1 | nginx config must parse | Reads `origin/main:deploy/nginx.conf` and tests it in a throwaway nginx | Stops in ~20 seconds. Nothing pulled, swapped or restarted. Production untouched. |
| 2 | Backup all sites | `bench --site all backup --with-files` **plus** a tar of every `site_config.json`. **This is your rollback point.** | Deploy stops. Nothing changed. |
| 3 | Sign in to the image registry | `docker login ghcr.io` with the job's own token | Deploy stops before the pull. |
| 4 | Deploy → fetch + checkout | Server tree moves from `886c8c4` to the merge commit | Stops with no trap installed, so nginx is **not** restarted. |
| 5 | Deploy → nginx parse, second time | Tests the file now on disk | Same — nginx not restarted, production keeps serving. |
| 6 | Deploy → pull | Up to 6 attempts over 5 minutes. IPv6 resets are normal here. | Stops after six. Containers untouched. |
| 7 | Deploy → `up -d` | **The container swap.** All production app containers move to the new image. | nginx is restarted so sites do not stay 502. |
| 8 | Deploy → maintenance on, per site | Every production site goes to 503 | |
| 9 | Deploy → `premigrate_rename` | Prints "nothing to do" on an ordinary release | |
| 10 | Deploy → `bench --site all migrate` | **The long one.** 10 new patches per site, plus doctype sync. | See §2 and §3. |
| 11 | Deploy → `clear-cache`, maintenance off | Sites come back | |
| 12 | Deploy → restart `compose-nginx-1` | ~2 seconds of 502 on every hostname, **dev included** | |
| 13 | Deploy → image cleanup | Keeps the 2 newest prod tags and 3 newest dev tags | |
| 14 | Restore service | Belt-and-braces: clears maintenance on every site again, re-checks nginx.conf, restarts nginx | |
| 15 | Smoke test | `https://alvoraa.co/api/method/ping`, 30 tries | Red run. See §3. |
| 16 | Stack and scheduler health | `docker compose ps` and `bench doctor` | Non-blocking. |

**Note the shared proxy.** Steps 12 and 14 restart the one nginx that also serves
`dev.alvoraa.co` and every tenant subdomain. Budget **up to ~10 seconds of interruption on
every hostname**, in two moments about a minute apart.

### Step 10 — the first automatic deploy after this

Once `main` carries the new workflow, **automatic deploys start working again**. The next
push to `dev` will produce an auto Deploy run that finally gets past `git fetch`, takes a
dev backup, runs the nginx gate and deploys dev — no more hand-dispatching with
`--ref dev`. The three failed `main`-labelled runs you have been seeing (`35453990893`,
`35371729875`, `35368582484`) were exactly that failure.

**And a push to `main` will deploy production with no prompt.** See §7, D-1.

---

## 2. What to watch, in order, and what it means if it is wrong

### 2.1 The migrate output, per site

This is the only part worth staring at. `bench --site all migrate` prints a block per site.

**First — get the site list.** I did not run anything against the production stack, so I am
not going to guess it:

```
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@100.127.29.62 \
  "docker exec compose-backend-1 ls -1 /home/frappe/frappe-bench/sites"
```

For each site, expect these ten patches to appear once:

| Patch | What it does | Wrong looks like |
|---|---|---|
| `hrms…add_esi_fields_for_india` | Adds custom fields | Any traceback |
| `hrms…add_attendance_score_fields` | Adds custom fields | |
| `hrms…add_employee_document_fields` | Adds custom fields | |
| `hrms…add_screening_fields` | Adds custom fields | |
| `hrms…add_policy_library_fields` | Adds custom fields | |
| `alvoraa_goals…make_evidence_files_private` | Moves public evidence files to `/private/files/` | Prints `N links made private, F failed, M rows with no File record`. **Any `failed` above 0 is worth reading the Error Log for** — it logs document names only. |
| `alvoraa_goals…take_review_copies` | **The review-copy backfill.** | Prints `Review copies: R reviews, C copies, F failed`. See 2.2. |
| `alvoraa_goals…stamp_lock_release_days` | Writes today's HR Settings value onto every review that has copies | Silent. No output is correct. |
| `alvoraa_portal…fill_branch_on_hr_records` | Creates the branch field and fills it on existing HR records | Silent |
| `alvoraa_portal…redact_field_checkin_error_logs` | **Blanks photos, coordinates and names already sitting in Error Log rows.** Irreversible. | Slow if a site has a large `Error Log` table — it scans with `LIKE '%…%'`, which cannot use an index. |

**If migrate stops on one site, it stops there.** Sites after it in the list are left on the
old schema with the new image running against them. Maintenance mode is still on for all of
them at that point, and the "Restore service" step will clear it — so **a half-finished
migrate ends with some sites live on a schema that does not match the code.** That is the
worst realistic outcome of this release. §3 is what you do about it.

### 2.2 The review-copy backfill counts

**Before the deploy, get the expected shape.** This is read-only and changes nothing, but it
runs inside a production container, so it is **yours to run, not mine**:

```
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@100.127.29.62

docker exec compose-backend-1 \
  bench --site demo.alvoraa.co execute alvoraa_goals.review_backfill.report 2>&1 | tail -40
```

Capture **both** stdout and stderr — `bench execute` swallows the real error and prints its
own fallback on stdout.

| Site | What to expect | What it means if it is wrong |
|---|---|---|
| `demo.alvoraa.co` | Roughly the 363-appraisal shape. Not every appraisal produces a review record — Not Started and Cancelled ones are skipped by design — so **a number well below 363 is normal**. A number well *above* it is not. | Zero reviews copied on a site with open appraisals means the extension records are not where the patch looks. Stop and ask before migrating production. |
| `dtc.alvoraa.co`, `aahr.alvoraa.co` | Near zero, unless someone has already opened reviews there | A large count on a tenant created on 18 September would mean seed data nobody expected |
| `alvoraa.co` | 2 employees, so single digits or zero | |
| `ppj.alvoraa.co` | Compare against dev's PPJ numbers: **806 reviews / 3,934 copies** today. Production PPJ is a different database with different data, so do **not** expect the same figures — expect the same *ratio*, roughly 5 copies per review. | A ratio far off 5 means the copy is picking up the wrong items |

`failed` should be `0`. Anything above `0`: the review is listed by name in the Error Log,
nothing was half-written (each review commits on its own), and the patch can be re-run.

### 2.3 Error-log deltas

Count before, count after. Before (read-only, USER's hands, per site):

```
docker exec compose-backend-1 bench --site <site> mariadb \
  -e "SELECT COUNT(*) FROM \`tabError Log\` WHERE creation > NOW() - INTERVAL 1 DAY" 2>&1 | tail -3
```

After the deploy, run the same thing. **A handful of new rows is normal** — the two patches
above log by design when they cannot move a file. What is not normal:

- **more than ~20 new rows on one site** — something is failing on every request;
- rows with `ImportError` or `get_controller` in the title — a doctype did not sync;
- rows mentioning `wkhtmltopdf` or `ConnectionRefused` — PDF generation. Production runs
  `DEVELOPER_MODE=0`, so the new `http_port 443` line does **not** apply there. If you see
  this, production's env file has developer mode on, which it must not.

Today's dev deploy showed **0 new errors**. That is the bar.

### 2.4 The smoke test and the shared nginx

The workflow's own smoke test only checks `alvoraa.co`. Check the rest yourself:

```
for h in alvoraa.co demo.alvoraa.co dtc.alvoraa.co aahr.alvoraa.co ppj.alvoraa.co minda.alvoraa.co dev.alvoraa.co ppj.dev.alvoraa.co; do
  printf '%-26s %s\n' "$h" "$(curl -sk -o /dev/null -w '%{http_code}' https://$h/api/method/ping)"
done
```

Every one should be `200`.

- **503** — that site is still in maintenance. It has happened three times, always the site
  that sorts first alphabetically. Fix: `docker exec compose-backend-1 bench --site <site>
  set-config -p maintenance_mode 0`.
- **502** — nginx is talking to containers that no longer exist. Fix:
  `docker restart compose-nginx-1`.
- **A certificate warning on a tenant subdomain** — nginx came back on the wrong certificate
  block. Check `docker logs --tail 40 compose-nginx-1` for `emerg`.

And the lesson that cost a week: **every app container in the stack must report the same
tag.**

```
docker ps --format '{{.Names}}\t{{.Image}}' | grep '^compose-'
```

All five of `compose-backend-1`, `compose-scheduler-1`, `compose-socketio-1`,
`compose-worker-default-1`, `compose-worker-long-1` on `prod-<sha>`. A worker left on
`prod-d99ba99` will crash on the first job that uses a new argument, and nothing on screen
will say so.

### 2.5 Disk

```
df -h /
```

116 GB free of 193 GB right now (40% used). The new image is about 11 GB, so the low point
is roughly 105 GB free before the cleanup step trims old tags. **Comfortable.** Watch it
anyway: on 10 September this disk hit 100%, three deploys hung silently for ~27 minutes
each, and the workers were dead for nine days.

### 2.6 Workers and the scheduler

```
docker exec compose-backend-1 bench --site alvoraa.co doctor
```

Expect the scheduler enabled and all three queues (`default`, `short`, `long`) with a worker
listening. **Tenant provisioning runs on `long`** — if `compose-worker-long-1` is missing,
new tenants queue for ever and nothing errors.

---

## 3. Rollback — and what it cannot undo

### 3.1 Code

**Image tag to go back to: `prod-d99ba99`.** It is running right now and still on the box, so
the rollback needs no pull.

```
gh workflow run Deploy --ref main \
  -f environment=production \
  -f image_tag=prod-d99ba99 \
  -f run_migrations=false
```

About 5 minutes. **Do not** set `run_migrations=true` on a rollback.

One catch: `--ref main` now means main's *new* workflow, which is what you want. But the
server tree will still be at the merge commit, so `deploy/nginx.conf` stays at dev's
version. That is fine — it is the file nginx is already serving today.

### 3.2 Data

The pre-deploy backup from step 2 of the run. Find it:

```
docker exec compose-backend-1 bash -c \
  "ls -lt /home/frappe/frappe-bench/sites/*/private/backups/ | head -20; \
   ls -lt /home/frappe/frappe-bench/sites/site-configs-*.tgz | head -3"
```

Restore per site:

```
docker exec -it compose-backend-1 bench --site <site> restore <dump>.sql.gz \
  --with-private-files <files>.tar --with-public-files <files>.tar
```

**`bench restore` does not restore `site_config.json`.** The encryption key lives there.
Keep the config tarball beside the dump or the restored site cannot decrypt its own
passwords.

### 3.3 What rollback cannot undo — read this before you need it

| Change | Reversible? | The truth |
|---|---|---|
| `redact_field_checkin_error_logs` | **No.** | The photos, coordinates, employee IDs and names are **overwritten in place** with `********`. Restoring a backup is the only way back, and you would not want to — the whole point is that they should never have been there. **Treat this as permanent the moment migrate passes it.** |
| `make_evidence_files_private` | Partly | Files were **moved on disk** from `/files/` to `/private/files/` and every row repointed. Rolling the code back leaves the rows pointing at private URLs the old code can still read. Undoing it means setting each File back to public by hand. Practically: leave it. |
| `take_review_copies` (the backfill) | Partly, and **only if you act first** | `undo_backfill()` removes copies **only from reviews nobody has touched since**. Any review someone opened, rated or completed after the deploy is kept and left alone. Worse: **once the patch is in the patch log, a later release will not re-run it**, so undoing it on a site that will get this release again destroys those history copies for good. |
| Ratings given during the window | **Only if you act before the code rollback** | New code writes ratings onto the review *copies*. Old code reads them off the live KPIs. Roll the code back without moving them and **every rating entered since the deploy vanishes from the screen** — it is still in the database, just nowhere the old code looks. |
| `stamp_lock_release_days` | Harmless | Writes a value into a **new** field. Old code does not read it. Rolling back leaves a stray column. Nothing to undo. |
| `fill_branch_on_hr_records` | Harmless | Same shape — fills a new field. |
| The five `hrms` field patches | Harmless | They add custom fields. Old code ignores them. |
| New doctypes and columns from the sync | Not undone | They stay in the database after a code rollback. Frappe tolerates this. |

**So the rollback order is: ratings first, then code.** On your word, before the image goes
back:

```
# dry run first — changes nothing, prints what it would move
docker exec compose-backend-1 \
  bench --site <site> execute alvoraa_goals.review_backfill.copy_ratings_back_for_rollback \
  --kwargs '{"dry_run": 1}' 2>&1 | tail -30

# then, only if the dry run looks right
docker exec compose-backend-1 \
  bench --site <site> execute alvoraa_goals.review_backfill.copy_ratings_back_for_rollback \
  --kwargs '{"dry_run": 0}' 2>&1 | tail -30
```

Repeat per site. Capture stderr, as above.

### 3.4 If migrate fails halfway through the site list

**Do not roll the code back first.** Sites that already migrated are fine on the new code;
sites that did not are the problem.

1. Put the un-migrated sites back into maintenance by name, so nobody uses them.
2. Read the actual failure from the run log for that one site.
3. If it is a single site's data problem, fix that site and re-run
   `bench --site <site> migrate` — the other sites need nothing.
4. Only if the failure is in the code itself: restore the failed sites from the pre-deploy
   backup, then roll the whole stack back to `prod-d99ba99`, doing §3.3's ratings step first
   on the sites that did migrate.

---

## 4. Go / no-go — sign each line

| # | Check | How | Status |
|---|---|---|---|
| 1 | Dev testing done and accepted | Your own testing on `dev.alvoraa.co` and `ppj.dev.alvoraa.co` since today's deploy: 806 reviews / 3,934 copies, 0 new errors, every site answering | |
| 2 | Releasing `886c8c4`, not local `dev` | `git rev-parse origin/dev` = `886c8c4` | |
| 3 | Stuck production run `35211643501` cancelled | `gh run list` | |
| 4 | `MUTE_EMAILS=1` in `deploy/envs/production.env` | §1 step 4 | |
| 5 | ghcr package **left public** | It is public today (checked). The runbook's rule stands: **it stays public until both sign-in fixes have deployed from `main` once.** That happens at step 9 of this release. Make it private **after**, not before. | |
| 6 | Repo already private | Checked: `PRIVATE`, default branch `main` | |
| 7 | Disk headroom | 116 GB free of 193 GB (40% used), measured today. Needs ~11 GB. | |
| 8 | Workers healthy | All five `compose-*` app containers up on `prod-d99ba99`; `worker-long` up 32h, `worker-default` up 9h | |
| 9 | You know production has **no** approval gate | §0 point 2, §7 D-1 | |
| 10 | Nobody is demonstrating in the next hour | The nginx restarts hit every hostname | |
| 11 | Backfill dry run read on `demo.alvoraa.co` and both client tenants | §2.2 | |
| 12 | Error Log counts recorded per site, before | §2.3 | |
| 13 | You have `prod-d99ba99` written down as the rollback tag | §3.1 | |

**Outstanding blockers as I see them:** #3 (hard blocker — the deploy cannot start),
#4 (release-blocking if it reads `0`), #9 (a decision, not a blocker).

---

## 5. What this does to the two client tenants

`dtc.alvoraa.co` and `aahr.alvoraa.co` were created on 18 September, on `prod-d99ba99` —
**code from before this year's work**. They get the biggest jump of any site here.

### What the migrate does to them

Everything: the full doctype sync for 308 commits of changes, all five `hrms` field patches,
and all five Alvoraa patches. On a tenant with almost no data this is **fast** (**estimate**:
under a minute each) and low-risk, because the patches mostly have nothing to find.

- `fill_branch_on_hr_records` — creates the branch field, fills nothing or almost nothing.
- `make_evidence_files_private` — nothing to move unless someone uploaded evidence.
- `redact_field_checkin_error_logs` — nothing to redact unless a field check-in failed there.
- `stamp_lock_release_days` — nothing, unless reviews exist.

### Does the review-copy backfill touch them?

**Only if reviews already exist there.** The patch copies items onto review records that have
none. A tenant with no appraisals in progress gets `0 reviews, 0 copies`. **Run the dry run
(§2.2) on both before the deploy** — if either comes back with a non-zero count, someone
seeded them and you want to know that before go-live, not after.

### The thing to configure afterwards — the cycle page list

**This is the one that has already cost a tenant a whole quarter.** An appraisal cycle needs
an `Alvoraa Cycle Config` record with a `page_config` saying which pages the review shows.
A cycle created through the wizard gets one. **A cycle created by a seed script does not** —
and until this release, a review on such a cycle rendered as a short, tidy, completely empty
wizard, with nothing on screen to say anything was missing.

**Good news:** this release adds the warning. After the deploy, a review holding items on a
cycle with no pages shows a banner: *"This review cannot show its objectives and KPIs …
Ask HR to add the objectives page to the cycle."*

**USER — check both tenants before you invite anyone (read-only):**

```
for s in dtc.alvoraa.co aahr.alvoraa.co; do
  echo "== $s"
  docker exec compose-backend-1 bench --site $s mariadb -e \
    "SELECT c.name, c.status, cc.name AS cfg, LENGTH(cc.page_config) AS cfg_len
       FROM \`tabAppraisal Cycle\` c
       LEFT JOIN \`tabAlvoraa Cycle Config\` cc ON cc.appraisal_cycle = c.name" 2>&1 | tail -20
done
```

- `cfg` NULL, or `cfg_len` 0 or 2 (`{}`) → **that cycle shows nothing.** Open the cycle in
  the wizard and add the pages before anyone logs in.
- A cycle created through the wizard will have a config with real content.

**Also worth checking on both before go-live:** the company's HR Settings values the review
uses (`lock_release_days` in particular — `stamp_lock_release_days` will freeze whatever it
reads on the day into every review that has copies), and that each tenant has its own logo
and branch/store records if they use store-level HR scoping. The store-HR scoping fix is in
your **local** four commits, not in this release.

---

## 6. Risks I would refuse to carry

| # | I will not | Instead |
|---|---|---|
| 1 | Run any command that writes to production, or approve/trigger a deploy | Every deploy command here is yours. I will read the run log with you. |
| 2 | Recommend unmuting email in this release | Do it as its own change, after this one is stable, with the queue checked first. Two large changes on one night means you cannot tell which one broke what. |
| 3 | Recommend pushing your four local commits in this release | They have never run on dev. Release what you tested. |
| 4 | Make the ghcr package private in this window | It has to stay public until the sign-in fix has deployed from `main` once — which is this release. Flip it after, then push one trivial commit to `dev` and watch a full deploy through. |
| 5 | Promise the merge is conflict-free | I did not perform the merge. 450 files differ across 308 commits; I predict one conflict in `deploy/nginx.conf`, and I could be wrong about the rest. Step 5 tells you how to check rather than assume. |
| 6 | Claim I know how long migrate takes on production | I ran nothing against production. The `redact_field_checkin_error_logs` scan is `O(rows)` on `Error Log` and I do not know how many rows production has. §2.3's pre-count gives you the number. |
| 7 | Say the workflow-file race in step 7 cannot happen | GitHub resolves the workflow file from the default branch at the moment the `workflow_run` event fires. I believe the merge commit will already be there. I have not tested the race, and step 7 says exactly what a miss costs. |
| 8 | Leave the shared-nginx design unchallenged | It is the biggest structural risk here: one nginx, one config file, one working tree, serving dev *and* production. A dev mistake is a production outage. Worth its own slice. |

---

## 7. Decisions I need from you before the day

| ID | Decision | Why it matters | Recommend / Consider / FYI | Decision |
|---|---|---|---|---|
| D-1 | Add a **required reviewer** to the `production` GitHub Environment before the push? | Today a push to `main` deploys production with no prompt. Adding a reviewer gives you a stop button and makes the release a deliberate two-step. Cost: one settings change, and every future production deploy waits for you. | **Recommend** | |
| D-2 | Release `886c8c4` only, holding back the four local commits? | Releasing untested code on a release night | **Recommend** | |
| D-3 | Keep email muted through this release; unmute as a separate change? | §1 step 4 | **Recommend** | |
| D-4 | Make the ghcr package private **after** this release, then watch one dev deploy? | The package is the whole application. It is public today. | **Recommend** | |
| D-5 | What time? The nginx restarts hit every hostname for ~10 seconds, and the window is the last two minutes of a ~45-minute run you cannot time. | Late evening or early morning IST. Not during a demo. | **Recommend** | |
| D-6 | Cancel the stuck run `35211643501`, or investigate why it is stuck first? | It blocks the release either way. I could not work out why it is "pending" — `pending_deployments` is empty and there are no required reviewers, so I do not know. Cancelling is safe and unblocks you. | **Recommend cancel** | |
| D-7 | Run the §2.2 backfill dry runs on production **before** the release? | It is the only way to know the shape of the biggest data change before it happens. Read-only, but it runs inside a production container, so it needs your word. | **Recommend** | |
| D-8 | A follow-up slice to stop one nginx config serving two environments from one shared checkout? | §6 risk 8 | Consider | |

---

## 8. Honesty notes

- **Measured today, read-only:** repository and branch SHAs; `deploy.yml`, `ci.yml` and
  `build-image.yml` on both branches; the `demo/` merge behaviour (via `git diff` against
  the merge base `b084f7c`); the patch list; `df -h /`; `docker ps`; the server's git HEAD
  (`886c8c4`, clean bar four known untracked files); both image pin files; GitHub run
  history; the `production` environment's protection rules; repository visibility
  (`PRIVATE`); package visibility (`public`).
- **I ran nothing against the production stack** — no `docker exec` into
  `compose-backend-1`, no database query, no bench command. Every production check in this
  runbook is written for your hands.
- **Not verified by me:** the production site list; row counts on any production site; the
  contents of `deploy/envs/production.env`; whether the merge conflicts beyond
  `deploy/nginx.conf`; the workflow-file race in step 7.
- **Estimates, clearly marked:** all timings, taken from today's dev deploy and the run
  history.
- The `demo/` merge-driver gap in §0 point 3 is inferred from git's documented behaviour
  (a merge driver is invoked only for files changed on both sides) plus the measured fact
  that those three files changed on `dev` only. I did not perform a trial merge. Step 5's
  `git checkout HEAD -- demo/` makes the question moot either way.

---

## 9. Follow-up, 2026-09-22 — the image package moves

Go/no-go row 5 and decision D-4 assumed the `hr-app` package could be made private after
this release. **It cannot** — GitHub does not let a public package go private again. The
image moves to a new private package, `alvoraa-app`, carried by the next release to
`main`. §3.1's rollback command still works until then; after it, rollbacks to
`prod-65878e8` and `prod-d99ba99` use copies inside the new package. Everything —
order, rollback before/during/after, and the checks before the old package is deleted —
is in `2026-09-private-image-package.md`.
