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
