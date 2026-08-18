# Rehearsal — test the Alvoraa deploy on real data without touching production

**Purpose:** prove the deployment on a copy of a live database, on a stack that cannot reach
production. This is §4.3 of `DEPLOYMENT_RUNBOOK.md`, written out.

**Why it exists:** all four live sites share one bench and one image, so there is no way to try
the new code on `dev.alvoraa.co` alone — swapping the image changes production at the same moment.
A throwaway stack is the only safe way to see the new code running on real data.

---

## 1. What makes it safe

Three separations. Get these right and the rehearsal cannot touch anything live.

| Separation | How | Why it matters |
|---|---|---|
| **Containers and volumes** | `COMPOSE_PROJECT_NAME=rehearsal` | Compose prefixes the named `sites` volume with the project, so the rehearsal gets its **own** sites directory. Without this it writes into the live one |
| **Site name** | `rehearsal.alvoraa.co` — a name no live site uses | A site is one database. A new name means a new database |
| **Network exposure** | Bind to a spare port; do **not** add it to nginx | Nothing routes to it from the internet |

The rehearsal may share the same MariaDB and Redis. Each site has its own database, so a new
site name is enough isolation there.

> **The one mistake that would hurt:** reusing the live `COMPOSE_PROJECT_NAME`. That attaches the
> rehearsal to the production `sites` volume. Check it before every command.

---

## 2. Prerequisites

- The image built from `dev` — `ghcr.io/<repo>/hr-app:dev-<sha>`. Created by CI on push.
- A recent dump of the site you want to mirror. `dev.alvoraa.co` is the sensible choice: same
  Alvox-era naming as production, lower stakes if the dump is mishandled.
- `DB_ROOT_PASSWORD` from `deploy/envs/*.env` — lets `bench restore` run without prompting.

---

## 3. Take the dump

```bash
docker exec compose-backend-1 bash -lc \
  "cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co backup"
```

Note the path it prints. Read-only on the live stack — this changes nothing.

---

## 4. Start the rehearsal stack

```bash
cd deploy/compose
cp ../envs/dev.env.example rehearsal.env      # then edit: KINEXUS_IMAGE=<the dev-<sha> tag>

COMPOSE_PROJECT_NAME=rehearsal \
docker compose --env-file rehearsal.env -f docker-compose.app.yml up -d configurator backend
```

Only `configurator` and `backend`. No scheduler, no workers, no socketio — a rehearsal should not
send emails or run background jobs against copied data.

Confirm the isolation before going further:

```bash
docker volume ls | grep rehearsal      # expect rehearsal_sites, separate from the live volume
```

---

## 5. Create the site and restore into it

```bash
REH=rehearsal-backend-1

docker exec $REH bash -lc \
  "cd /home/frappe/frappe-bench && bench new-site rehearsal.alvoraa.co \
     --db-root-password '<DB_ROOT_PASSWORD>' --admin-password '<pick-one>' --no-mariadb-socket"

# copy the dump in, then restore
docker cp <dump.sql.gz> $REH:/tmp/dump.sql.gz
docker exec $REH bash -lc \
  "cd /home/frappe/frappe-bench && bench --site rehearsal.alvoraa.co --force restore /tmp/dump.sql.gz \
     --db-root-password '<DB_ROOT_PASSWORD>'"
```

The site now holds real data with the **old** Alvox naming, running against the **new** Alvoraa
image. That mismatch is exactly what the deployment will face.

---

## 6. Rehearse the deployment

This is the part that matters. Run it in the same order as the real thing.

```bash
# 6a. Record the starting state
docker exec $REH bash -lc "cd /home/frappe/frappe-bench && bench --site rehearsal.alvoraa.co console"
```
```python
frappe.get_installed_apps()          # expect alvox_goals / alvox_portal, possibly duplicated
frappe.db.exists("DocType", "Alvox Cycle Config")     # expect True
```

```bash
# 6b. Pre-migrate rename  — MUST come before migrate
docker exec $REH bash -lc \
  "cd /home/frappe/frappe-bench && bench --site rehearsal.alvoraa.co execute alvoraa_goals.deploy_utils.premigrate_rename"

# 6c. Only now, migrate
docker exec $REH bash -lc \
  "cd /home/frappe/frappe-bench && bench --site rehearsal.alvoraa.co migrate"
```

**Watch the migrate output for `Orphaned DocType(s) found:`.** `Mode of Payment` there is
pre-existing and expected. **Any of ours in that list is a stop.**

### Worth doing once: prove the guard is real

On a throwaway site you can afford to see the failure mode. Restore a second copy, skip step 6b,
and run migrate directly. The Alvoraa doctypes will be deleted. Ten minutes, and afterwards nobody
on the team will be tempted to skip that step on production.

---

## 7. Verify

```python
frappe.get_installed_apps()
# expect exactly: ['frappe', 'erpnext', 'hrms', 'alvoraa_portal', 'alvoraa_goals']  - no duplicates

frappe.db.count("DocType", {"module": "Alvoraa Goals"})     # 21
frappe.db.count("DocType", {"module": "Alvoraa Portal"})    # 22

all(frappe.db.exists("DocType", d) for d in
    ["Alvoraa Cycle Config", "Alvoraa Rating Scale",
     "Alvoraa Rating Scale Item", "Alvoraa Appraisal Extension"])     # True

# real data survived the doctype rename
frappe.db.count("Individual Goal"), frappe.db.count("KPI")
```

Compare those last counts against the live site. **They must match.** A rename that loses rows is
the failure worth catching here.

### Then click through it

Point a browser at the rehearsal. Add a hosts entry so the Host header matches the site name:

```
<server-ip>   rehearsal.alvoraa.co
```

and browse to `http://rehearsal.alvoraa.co:<port>`.

These are the paths this deploy repairs, so they are the ones to check:

- Goals page loads; open a goal; create, edit, delete
- Update progress; add a check-in
- Manager: team goals, approvals inbox, approve an update
- Appraisal screen; save a self-assessment
- Company values; rating scale dropdown populated

**Then log in as an ordinary employee** and confirm you see only your own goals. The permission
hooks are dotted paths in `hooks.py`; if one is wrong Frappe does not error, it just stops
filtering. It fails *open*, so this must be checked by a person.

---

## 8. Tear down

```bash
cd deploy/compose
COMPOSE_PROJECT_NAME=rehearsal docker compose --env-file rehearsal.env -f docker-compose.app.yml down -v
docker volume ls | grep rehearsal      # expect nothing
rm rehearsal.env
```

`-v` removes the rehearsal volume. Safe **only** because the project name is `rehearsal`; run it
with the live project name and it destroys production's sites volume. Check the variable before
pressing enter.

---

## 9. What a green rehearsal tells you

- The premigrate + migrate sequence works on real data
- Row counts survive the doctype rename
- The repaired portal paths work in a browser
- Permission scoping still holds for a normal employee

That is the entire risk of the production deploy, exercised. What it does **not** cover is
scale, concurrent users, and the fact that production carries three other sites — so keep the
maintenance window and the backups regardless.
