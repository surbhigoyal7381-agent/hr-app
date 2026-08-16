"""
rebuild_nsm.py — Rebuild Employee nested-set (lft/rgt) without changing any data
==================================================================================
Use this after any bulk import or manual data change that may have left lft/rgt
values as 0 or stale. Does not touch reports_to — only recalculates tree positions.

Run via:
  docker exec -i compose-backend-1 \\
    bash -c 'cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co console' \\
    < demo/rebuild_nsm.py
"""
from frappe.utils.nestedset import rebuild_node

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
print(f"NSM rebuilt: {len(roots)} root nodes, tree spans lft=1 to rgt={right}")

# Quick verification
zero_count = frappe.db.count("Employee", {"lft": 0, "status": "Active"})
print(f"Employees still at lft=0: {zero_count}  (should be 0)")
