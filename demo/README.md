# Demo & Seed Scripts

Scripts in this folder are **dev-only**. They populate `dev.alvoraa.co` with
realistic demo data and fix data discrepancies. They never run on production.

## Git isolation

`demo/.gitattributes` marks every file here with `merge=ours`. When `dev` is
merged into `main`, git keeps `main`'s stub copies. Register the driver once
per machine (stored in `.git/config`, not committed):

```bash
git config merge.ours.driver true
```

**Rule when adding a new script**: also add an empty stub file with the same
name to `main` before the next merge, so the driver is triggered for that file.

## Available scripts

| Script | Purpose | Run command |
|---|---|---|
| `fix_hierarchy.py` | Diagnose and auto-fix broken `reports_to` links; rebuilds NSM | See below |
| `rebuild_nsm.py` | Rebuild Employee nested-set (lft/rgt) from scratch | See below |
| `setup_performance.py` | Seed Q1 performance cycle, KRAs, appraisals | See below |

## How to run

All scripts run inside the backend container via bench console:

```bash
# Fix broken reporting hierarchy on dev.alvoraa.co
docker exec -i compose-backend-1 \
  bash -c 'cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co console' \
  < demo/fix_hierarchy.py

# Rebuild NSM only (no data changes)
docker exec -i compose-backend-1 \
  bash -c 'cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co console' \
  < demo/rebuild_nsm.py

# Seed Q1 performance data
docker exec -i compose-backend-1 \
  bash -c 'cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co console' \
  < demo/setup_performance.py
```

Copy the scripts to the server first:
```bash
scp demo/<script>.py root@169.58.108.3:/tmp/
docker exec -i compose-backend-1 \
  bash -c 'cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co console' \
  < /tmp/<script>.py
```
