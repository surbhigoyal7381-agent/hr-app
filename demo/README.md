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

## Passwords: set them, never commit them

Any script here that creates login users reads its password from an environment
variable. There is no built-in default, and a script stops before writing
anything if the variable is missing.

| Script | Variable |
|---|---|
| `link_employee_users.py` | `HR_DEMO_PASSWORD` |
| `pp_jewellers/seed_employees.py`, `pp_jewellers/run_all.sh` | `PPJ_DEMO_PASSWORD` |
| `alvoraa_portal/alvoraa_portal/demo_setup.py` (outside this folder) | `PORTAL_DEMO_PASSWORD` |

```bash
export HR_DEMO_PASSWORD='<a new, strong password>'
```

Pass it into the container with `docker exec -e HR_DEMO_PASSWORD=...`. Pick a
fresh value each time, keep it out of git and out of chat, and change it on the
tenant when the demo is over. `scripts/check_no_demo_passwords.py` fails the
build if a password is ever written back into these files.

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
scp demo/<script>.py root@<server-ip>:/tmp/
docker exec -i compose-backend-1 \
  bash -c 'cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co console' \
  < /tmp/<script>.py
```
