# Deployment Runbook — `dev` → servers, including the Alvoraa rename

**Status:** Ready for scheduling. Not yet executed.
**Date:** 2026-08-18
**Applies to:** the single bench serving `alvoraa.co`, `dev.alvoraa.co`, `minda.alvoraa.co`, `kinexus.alvoraa.co`

---

## 1. What is being deployed

`dev` is roughly 30 commits ahead of anything running. It contains months of feature work
**plus the complete Alvoraa rename** — apps, modules, doctypes and titles.

| | Running now | After this deploy |
|---|---|---|
| Built from | `backup/dev-rebrand-aug-2026` (`53a8180`, 13 Aug) | `dev` |
| Apps | `alvox_goals`, `alvox_portal` | `alvoraa_goals`, `alvoraa_portal` |
| Modules | Alvox Goals, Alvox Portal | Alvoraa Goals, Alvoraa Portal |
| Doctypes | `Alvox Cycle Config`, `Alvox Rating Scale`, `Alvox Appraisal Extension` | `Alvoraa …` |

---

## 1B. ⚠️ There is an AUTOMATIC deploy workflow

`.github/workflows/deploy.yml` triggers on **every successful Build Image run** for `dev`,
`test` and `main`. It is not manual-only. It swaps the image and runs
`bench --site all migrate` across the whole bench - which is all four sites, production
included.

**The only reason it has not fired is that `secrets.DEPLOY_HOST` is unset.** The job dies
with `Error: missing server host` before reaching the server.

> **Do not set `DEPLOY_HOST` casually.** Setting it makes the next push to `dev` deploy to
> production automatically, unattended.

The workflow did **not** run `premigrate_rename` before migrating. On this release - which
renames the apps - that sequence deletes doctypes, exactly as described in §3. That step
has now been added to the workflow, immediately before migrate.

Two things it does do well, and they are worth keeping: it takes
`bench --site all backup --with-files` before touching anything, and it holds maintenance
mode across the migration.

**Before enabling automatic deploys, decide whether an unattended production migration is
what you want at all.** For this release specifically, prefer the manual procedure below,
where the pre-migrate step and the verification can be watched.

---

## 1A. ✅ Resolved — the goal-progress regression is fixed

This section warned that deploying `dev` would silently stop goal progress updating from
evidence. That is no longer true: the half-finished field rename behind it was completed on
2026-08-19. See `KNOWN_ISSUES.md` KI-1.

Nothing to decide here now. The deploy no longer carries that regression.

---

## 1B. ⚠️ There is an AUTOMATIC deploy workflow

`.github/workflows/deploy.yml` triggers on **every successful Build Image run** for `dev`,
`test` and `main`. It is not manual-only. It swaps the image and runs
`bench --site all migrate` across the whole bench - which is all four sites, production
included.

**The only reason it has not fired is that `secrets.DEPLOY_HOST` is unset.** The job dies
with `Error: missing server host` before reaching the server.

> **Do not set `DEPLOY_HOST` casually.** Setting it makes the next push to `dev` deploy to
> production automatically, unattended.

The workflow did **not** run `premigrate_rename` before migrating. On this release - which
renames the apps - that sequence deletes doctypes, exactly as described in §3. That step
has now been added to the workflow, immediately before migrate.

Two things it does do well, and they are worth keeping: it takes
`bench --site all backup --with-files` before touching anything, and it holds maintenance
mode across the migration.

**Before enabling automatic deploys, decide whether an unattended production migration is
what you want at all.** For this release specifically, prefer the manual procedure below,
where the pre-migrate step and the verification can be watched.

---

## 1A. ⚠️ Known regression this deploy introduces

**Deploying `dev` will stop goal progress updating from evidence.** It is not a risk to weigh -
it is a certainty, and it is understood.

Commit `6351af3` replaced `Goal Evidence.extracted_order_count` / `extracted_amount` with a
generic `value` field, but 38 references to the old names remain, including
`controllers.goal.recalculate_progress`. That commit is not in the deployed image, so the servers
are correct today and become wrong the moment this ships.

On an existing site the failure is **silent**: Frappe leaves the old database column in place, so
the query still runs and simply sums a column nothing writes to. Approving evidence will appear to
work while progress stays at zero. On any newly provisioned tenant it fails loudly instead.

Full detail in `KNOWN_ISSUES.md` (KI-1).

**Decide before the window:** accept it, because the KPI automation work replaces this path
entirely and users are not yet relying on it - or fix it first, and delay the rename. Do not
discover it afterwards.

---

## 2. Three facts that shape everything

**One bench, four sites.** App code lives at `/home/frappe/frappe-bench/apps` and is shared.
Only the databases are separate. **There is no way to deploy code to `dev.alvoraa.co` alone** —
the image swap changes all four sites at once. Plan it as a production change, because it is one.

**The containers do not auto-migrate.** `deploy/compose/docker-compose.app.yml` runs a
`configurator` that only writes config, then gunicorn. Nothing calls `bench migrate`. So migrate
timing is under our control — which is what makes this safe.

**The image is built by CI.** `.github/workflows/build-image.yml` fires on push to `dev`, `test`
or `main`, publishing `ghcr.io/<repo>/hr-app:dev-<sha>`. The image for this deploy therefore
already exists, or will as soon as `dev` is pushed.

---

## 3. The hazard — read before doing anything

`bench migrate` finishes by calling `remove_orphan_doctypes()`. That helper loads every doctype's
controller class and **deletes any doctype whose controller raises `ImportError`**.

After the image swap, the site database still says its apps are `alvox_goals` / `alvox_portal`.
Those packages no longer exist on disk. So every doctype in those modules fails to import.

**If `bench migrate` runs in that state, it will delete them.** This is not theoretical — it
happened during testing, and it took four doctypes with it. See commit `a590375`.

The rename must therefore be written into the database **before** migrate runs, and it cannot be
done by a patch: patches are discovered per installed app, so a patch inside `alvoraa_goals` is
invisible while the site still believes the app is `alvox_goals`.

That is what `alvoraa_goals.deploy_utils.premigrate_rename` exists for.

---

## 4. Before the window

1. **Push `dev`** and confirm CI produced the image. Note the tag: `dev-<sha>`.
2. **Confirm the current image tag**, so rollback is a known value, not a guess:
   ```bash
   docker inspect compose-backend-1 --format '{{.Config.Image}}'
   ```
3. **Rehearse on a scratch stack.** Full procedure in **`REHEARSAL.md`** — a separate compose
   project with its own sites volume, restored from a live dump, running the new image. It
   exercises the whole premigrate + migrate sequence on real data and cannot reach production.
   This is the step that turns an unknown into a known.
4. **Confirm the DB root password is to hand.** `bench restore` prompts for it interactively, and
   a rollback at 2am is the wrong time to go looking.
5. **Announce the window.** All four sites, including production, will be down for the duration.

---

## 5. The deploy

### 5.1 Back up every site — not just production

```bash
for SITE in alvoraa.co dev.alvoraa.co minda.alvoraa.co kinexus.alvoraa.co; do
  docker exec compose-backend-1 bash -lc \
    "cd /home/frappe/frappe-bench && bench --site $SITE backup --with-files"
done
```

Verify each dump exists and has a sane size before continuing. A backup you have not looked at
is not a backup.

### 5.2 Stop serving

```bash
docker compose -f deploy/compose/docker-compose.app.yml stop backend socketio queue-long queue-short scheduler
```

Nothing should serve traffic while the code and the database disagree.

### 5.3 Swap the image

Set `KINEXUS_IMAGE` to the new `dev-<sha>` tag, then bring up **only** a shell — not the web
service — so the fixup can run before anything serves or migrates.

### 5.4 Run the pre-migrate rename, per site

```bash
for SITE in alvoraa.co dev.alvoraa.co minda.alvoraa.co kinexus.alvoraa.co; do
  echo "=== $SITE"
  docker exec compose-backend-1 bash -lc \
    "cd /home/frappe/frappe-bench && bench --site $SITE execute alvoraa_goals.deploy_utils.premigrate_rename"
done
```

Each site should print the changes it made. It is idempotent — re-running is safe, and a site
already renamed prints `nothing to do`.

This also **deduplicates `installed_apps`**, which is currently corrupt on `dev.alvoraa.co`
(every custom app listed twice).

### 5.5 Only now, migrate

```bash
for SITE in alvoraa.co dev.alvoraa.co minda.alvoraa.co kinexus.alvoraa.co; do
  echo "=== $SITE"
  docker exec compose-backend-1 bash -lc \
    "cd /home/frappe/frappe-bench && bench --site $SITE migrate"
done
```

**Watch for the line `Orphaned DocType(s) found:`.** Anything of ours in that list means the
rename did not fully apply — stop and roll back rather than continuing.

### 5.6 Clear caches and start

```bash
docker exec compose-backend-1 bash -lc \
  "cd /home/frappe/frappe-bench && bench --site all clear-cache && bench --site all clear-website-cache"
docker compose -f deploy/compose/docker-compose.app.yml up -d

# MANDATORY. `up -d` gives the backend a NEW IP; nginx resolved the old one at
# startup and keeps using it, so EVERY site returns 502 - production included.
# See 5.7. Do not treat this as optional: it took production down on 2026-08-19
# because a deploy was run from a command list that omitted this line.
docker restart compose-nginx-1
```

---

## 5.7 Assets: two traps that look like application faults

Both were hit for real on 2026-08-19 and cost more time than the migration itself.

### Stale assets served from the volume

`sites/` is a Docker volume, so `sites/assets` **survives an image swap**. Browsers then get
JavaScript built against the *old* Frappe while the backend runs the new one. The symptom was:

```
Failed to get method for command frappe.core.doctype.background_task...
No module named 'frappe.core.doctype.background_task'
```

`Background Task` exists in Frappe `develop` but not `version-16`, so the doctype was correctly
removed while the old bundle kept calling it. Rebuild assets into the volume after the swap:

```bash
docker exec compose-backend-1 bench build --production
```

### Symlinked assets that nginx cannot follow

`bench build` links `sites/assets/<app>` → `apps/<app>/<app>/public`. The backend has `/apps`;
**nginx mounts only the sites volume and does not**. It follows a dangling link and returns 404
for every CSS and JS file.

The portal then renders with no styling and every panel stuck on "Loading…" — the profile menu
drops out of the corner into the middle of the page. It looks like a broken application. It is a
404 on a stylesheet.

**After any `bench build` that writes into the volume:**

```bash
docker cp scripts/materialise_assets.sh compose-backend-1:/tmp/
docker exec compose-backend-1 bash /tmp/materialise_assets.sh
docker exec compose-nginx-1 nginx -s reload
```

Confirm before declaring success — a 404 here is invisible from the server side:

```bash
curl -s -o /dev/null -w '%{http_code}
' https://<site>/assets/frappe/dist/css/website.bundle.*.css
```

The image now dereferences these at build time (`Dockerfile` §4b), so a plain image swap is safe.
This step is only needed when `bench build` is run **inside a live container**.

### Always restart nginx after replacing the backend

nginx resolves the backend's IP at startup. Replace or restart `compose-backend-1` and nginx keeps
the old address, serving **502** while the backend is perfectly healthy:

```bash
docker restart compose-nginx-1
```

---

## 6. Verify — per site, not just once

```bash
docker exec compose-backend-1 bash -lc \
  "cd /home/frappe/frappe-bench && bench --site <site> console"
```

```python
frappe.get_installed_apps()
# expect exactly: ['frappe', 'erpnext', 'hrms', 'alvoraa_portal', 'alvoraa_goals']
# no duplicates

[m.name for m in frappe.get_all("Module Def", filters={"app_name": ["like", "alvoraa%"]}, fields=["name"])]
# expect: ['Alvoraa Goals', 'Alvoraa Portal']

frappe.db.count("DocType", {"module": "Alvoraa Goals"})    # expect 21
frappe.db.count("DocType", {"module": "Alvoraa Portal"})   # expect 22

all(frappe.db.exists("DocType", d) for d in
    ["Alvoraa Cycle Config", "Alvoraa Rating Scale",
     "Alvoraa Rating Scale Item", "Alvoraa Appraisal Extension"])   # expect True
```

Then, in a browser, on **one** site — these are the paths that were broken and are fixed by this
deploy, so they are the ones worth a human eye:

- Goals page loads; open a goal; create, edit and delete a goal
- Update progress; add a check-in
- Manager: team goals, approvals inbox, approve an update
- Appraisal screen; save a self-assessment
- Company values list; rating scale dropdown populated

Finally, as a **non-privileged employee**: confirm you see only your own goals. The permission
hooks are dotted paths in `hooks.py`, and a missed rename there fails *open* rather than loudly.
This one must be checked by logging in, not inferred.

---

## 7. Rollback

Rollback is restore-from-backup, not revert-the-commit. Once migrate has renamed doctypes and
tables, the code and database have moved together.

1. Stop the app containers.
2. Set `KINEXUS_IMAGE` back to the tag recorded in §4.2.
3. Restore each site from its §5.1 dump:
   ```bash
   docker exec -it compose-backend-1 bash -lc \
     "cd /home/frappe/frappe-bench && bench --site <site> --force restore <dump.sql.gz>"
   ```
   Interactive — it prompts for the DB root password.
4. `bench --site all clear-cache`, then start the containers.

**Decision point:** roll back if a site fails to migrate, if our doctypes appear in the orphan
list, or if the permission check in §6 shows an employee other people's data. Cosmetic problems
are not rollback triggers — fix forward.

---

## 8. After the deploy

- **`deploy/Dockerfile` was wrong and is now fixed** — it installed `grace_goals` /
  `grace_vendor_portal`, which matched no server. Phase 4 corrected it to the `alvoraa_*` names.
  Worth confirming the next CI build actually uses it, since the running image did not.
- **`backup/dev-rebrand-aug-2026` stops being the deployed branch.** Keep it, but it is now
  history rather than the source of truth.
- **Then the objectives/KPI restructure begins**, against a green test suite and servers that
  finally match the repo.

---

## 9. Known gaps, stated plainly

- **No staging that mirrors production.** The scratch-site rehearsal in §4.3 is the substitute.
  A separate bench for `dev.alvoraa.co` would remove this whole class of risk and is worth doing
  before the next large change.
- **`Mode of Payment` disappearing on migrate is explained.** It is a regression in Frappe
  `develop`: `remove_orphan_doctypes` treats *all* doctypes, core ones included, as orphaned when
  `sync_all()` produces an empty module map. Diagnosed on the deployed branch in commit `53a8180`,
  which pinned Frappe and ERPNext to `version-16` to avoid it. That pin has now been applied to
  `dev` as well, so it should not recur. Note this is separate from the controller-class bug in
  `a590375`, which was ours and is fixed.
- **Nine tests fail in `alvoraa_portal`** and are not addressed here; that app is due to be
  rebuilt.


---

## Appendix A · Deploying without GitHub Actions

Actions is not required. The server has room to build for itself: 6 cores, ~8 GB free and
124 GB of disk, verified 2026-08-19.

### A.1 What is actually on the server

Worth knowing before anything else, because none of it matches what the workflow assumes.

| | |
|---|---|
| Stack runs from | `/var/www/html/hr-app/deploy/compose` |
| `deploy.yml` expects | `/opt/hr-app` — **exists but is empty**, so the automated deploy would have failed here regardless of the missing secret |
| Server checkout | branch `main`, commit `72c89e1` "Add Performance Distribution (Bell Curve) tab" |
| Running image | `ghcr.io/…/hr-app:dev-53a8180`, built from the rebrand branch |
| Env file in use | `deploy/envs/production.env` |

Note the checkout and the image come from **different lineages**: the working copy is from
the AllAboutHR line, the image from the rebrand line. The `docker-compose.app.yml` on the
server also differs from `dev`'s (different md5). Compare them before reusing either.

> `/var/www/html/hr-app` is the directory `CLAUDE.md` says never to modify. The procedure
> below therefore **builds somewhere else entirely** and changes only which image the stack
> runs. Nothing in that directory is edited except the one-line image pin.

### A.2 Build in a separate directory

Building does not disturb the running containers, so this part needs no maintenance window
and no downtime.

```bash
# a clean checkout, away from the live tree
sudo mkdir -p /opt/build && sudo chown "$USER" /opt/build
cd /opt/build
git clone https://github.com/surbhigoyal7381-agent/hr-app.git . 2>/dev/null || git fetch --all
git checkout --detach origin/dev
git log --oneline -1          # confirm the commit you intend to ship

docker build -f deploy/Dockerfile -t hr-app:dev-$(git rev-parse --short HEAD) .
```

Expect 15–30 minutes cold. It clones frappe and erpnext and bundles assets for five apps.
No registry is involved — the image stays on this machine, which is where it is needed.

### A.3 Compare the compose file before swapping

The server's `docker-compose.app.yml` is not the same as `dev`'s. Decide deliberately
whether to adopt the new one:

```bash
diff /var/www/html/hr-app/deploy/compose/docker-compose.app.yml      /opt/build/deploy/compose/docker-compose.app.yml
```

If it differs in ways the new image depends on, copy it across as part of the window — and
keep the old one so it can be put back.

### A.4 Deploy — the same sequence as §5

Only the image source changes. Everything else, including the ordering that matters, is
identical to the main procedure:

```bash
cd /var/www/html/hr-app/deploy/compose
DC="docker compose -f docker-compose.app.yml --env-file ../envs/production.env"

# 1. back up every site FIRST
for S in alvoraa.co dev.alvoraa.co minda.alvoraa.co kinexus.alvoraa.co; do
  $DC exec -T backend bench --site $S backup --with-files
done

# 2. record the current image so rollback is a known value
docker inspect compose-backend-1 --format '{{.Config.Image}}'

# 3. point the stack at the locally built image
echo "KINEXUS_IMAGE=hr-app:dev-<sha>" > .image.env
DC="$DC --env-file .image.env"

$DC exec -T backend bench --site all set-maintenance-mode on
$DC up -d --remove-orphans

# 4. rename in the database BEFORE migrate - see §3
$DC exec -T backend bench --site all execute alvoraa_goals.deploy_utils.premigrate_rename

# 5. only now
$DC exec -T backend bench --site all migrate
$DC exec -T backend bench --site all clear-cache
$DC exec -T backend bench --site all set-maintenance-mode off

# MANDATORY - see the note in 5.6/5.7. `up -d` re-IPs the backend and nginx
# still points at the old address, so every site 502s until this runs.
docker restart compose-nginx-1
```

Then verify per §6, including the non-privileged employee check.

### A.5 Rollback

Put the old tag back in `.image.env`, `$DC up -d`, and restore from the §A.4 step-1 dumps if
migrate has already run. Identical to §7.

### A.6 Why this is arguably better for this release

The build happens with the site still serving, so the only downtime is the swap and migrate.
And it removes GitHub Actions, the registry and the deploy secrets from the critical path —
three things that have each broken separately this week.
