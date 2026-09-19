# Demo & Seed Scripts

Scripts in this folder are **dev-only**. They populate `dev.alvoraa.co` with
realistic demo data and fix data discrepancies. They never run on production.

## A seed writes records the app has to read. Make it write what the app writes.

**This is the rule that costs the most when it is broken**, because the result
does not look like a broken seed. It looks like a broken product.

On 2026-09-19 three release blockers were traced to one script,
`pp_jewellers/seed_performance.py`. All three had the same shape: the seed wrote
a field in a shape the app does not read, and nothing anywhere compared the two.

| What the seed wrote | What the app reads | What people saw |
|---|---|---|
| `"page_config": "[]"` | the page list a cycle shows | **Nobody in the tenant had ever seen an objective or a KPI inside a review.** Every review held its items and had no page to show them on, and said nothing about it |
| `"signed_on": "2026-07-12"` | `signed_at` | The calibration sign-off named the signer and then stopped before the date |
| a list, `[]` | the wizard writes an object, `{key: true}` | The empty list was read as "wizard is broken", and the hunt started in the wrong code |

None of these was a bug in the product. Two of them were reported as one, and the
first guess at the cause was the cycle wizard — which was correct all along.

**So, when you add or change a seed:**

1. **Copy the shape from the code that normally writes the record**, not from
   what looks reasonable. Find the function the app uses — `save_cycle_wizard`,
   `save_calibration_signoff` — and match its keys exactly.
2. **Then open the screen** that reads it and check the value appears. A seeded
   record that no screen renders is worse than no record: it looks like data.
3. **Prefer calling the app's own function** over building the dict by hand.
   Where that is not practical, leave a comment naming the function whose shape
   you copied, so the next person knows what to keep it in step with.
4. **If a field is a list of what to show, never seed it empty.** An empty list
   is indistinguishable from "configured to show nothing", and every screen will
   obey it in silence.

There are now two pins in `alvoraa_portal/tests/test_review_render_027.py`
comparing this seed against the app for those two fields. They read the seed's
text, which is cheap but narrow. **The test still worth writing** is one that
runs a seed against a scratch site and asserts the app can read back what it
wrote. That would have caught all three of these at once.

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
