"""
fix_hierarchy.py — Diagnose and auto-fix broken reports_to links in Employee
=============================================================================
Run via bench console (stdin pipe):
  docker exec -i compose-backend-1 \\
    bash -c 'cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co console' \\
    < demo/fix_hierarchy.py

Phases:
  1. Diagnose  — list all employees whose reports_to value is not a valid Employee ID
  2. Auto-fix  — if the broken value matches another employee's name (case-insensitive),
                 rewrite it to the correct ID
  3. Report    — list anything that could not be resolved automatically
  4. NSM       — rebuild lft/rgt for the corrected tree
"""

# ── Phase 1: Diagnose ──────────────────────────────────────────────────────
all_ids = set(frappe.db.get_all("Employee", pluck="name"))

candidates = frappe.db.get_all(
    "Employee",
    filters=[["status", "=", "Active"]],
    fields=["name", "employee_name", "reports_to", "company", "department"],
)

broken = [e for e in candidates if e.reports_to and e.reports_to not in all_ids]

print(f"\n{'='*60}")
print(f"PHASE 1 — Broken reports_to links: {len(broken)}")
print(f"{'='*60}")
for e in broken:
    print(f"  {e.employee_name:35s} ({e.name}) -> '{e.reports_to}'")

# ── Phase 2: Auto-fix by fuzzy name match ──────────────────────────────────
name_map = {}
for r in frappe.db.get_all("Employee", fields=["name", "employee_name"]):
    key = r.employee_name.strip().lower()
    # last-write wins for duplicates; acceptable for a demo env
    name_map[key] = r.name

fixed, unresolved = 0, []
for e in broken:
    key = e.reports_to.strip().lower()
    candidate = name_map.get(key)
    if candidate and candidate != e.name:
        frappe.db.set_value(
            "Employee", e.name, "reports_to", candidate, update_modified=False
        )
        print(f"  FIXED : {e.employee_name} -> {candidate}  (was '{e.reports_to}')")
        fixed += 1
    else:
        unresolved.append(e)

frappe.db.commit()

print(f"\n{'='*60}")
print(f"PHASE 2 — Auto-fixed: {fixed} | Unresolved: {len(unresolved)}")
print(f"{'='*60}")
if unresolved:
    print("The following require manual correction in the Employee form:")
    for e in unresolved:
        print(f"  {e.employee_name:35s} ({e.name}) | dept={e.department} | co={e.company}")
        print(f"    reports_to='{e.reports_to}' — no matching employee found")

# ── Phase 3: Rebuild NSM ───────────────────────────────────────────────────
from frappe.utils.nestedset import rebuild_node

print(f"\n{'='*60}")
print("PHASE 3 — Rebuilding NSM (lft/rgt)")
print(f"{'='*60}")

right = 1
roots = frappe.db.get_all(
    "Employee",
    filters=[["reports_to", "in", ["", None]], ["status", "=", "Active"]],
    pluck="name",
    order_by="name asc",
)
for r in roots:
    right = rebuild_node("Employee", r, right, "reports_to")

frappe.db.commit()
print(f"Done. {len(roots)} root nodes processed, tree spans lft=1 to rgt={right}")
print(f"\nRun verification: frappe.db.count('Employee', {{'lft': 0, 'status': 'Active'}}) should be 0")
