"""
PP Jewellers demo - July 2026 sales actuals per salesperson, with the illustrative incentive.

Reads  docs/pp_jewellers/data/employees.csv, docs/pp_jewellers/data/sales_targets.csv
Writes docs/pp_jewellers/data/sales_actuals_july.csv

Deterministic (seeded). Run from the repo root: python3 demo/pp_jewellers/generate_sales_actuals.py
"""
import csv
import random
from collections import defaultdict
from pathlib import Path

random.seed(20260907)
DATA = Path(__file__).resolve().parents[2] / "docs" / "pp_jewellers" / "data"
SHARE = {"Senior Sales Executive": 1.5, "Sales Executive": 1.0, "Trainee Sales Executive": 0.5}
FLOOR_CAT = {"Floor Manager - Gold": "Gold", "Floor Manager - Diamond": "Diamond", "Floor Manager - Silver & Fashion": "Silver & Fashion"}
# quarterly category share of store target; Platinum & Gemstone is sold from the Diamond floor
FLOOR_SHARE = {"Gold": 0.60, "Diamond": 0.25 + 0.07, "Silver & Fashion": 0.08}
COMPONENT = {"Gold": "Gold Incentive", "Diamond": "Diamond Incentive", "Silver & Fashion": "Silver & Fashion Incentive"}
# slab: (lower attainment bound, rate) per category, for own-sales roles
SLABS = {"Gold": [(1.20, 0.0050), (1.00, 0.0035), (0.90, 0.0020)],
         "Diamond": [(1.20, 0.0120), (1.00, 0.0090), (0.90, 0.0060)],
         "Silver & Fashion": [(1.20, 0.0070), (1.00, 0.0050), (0.90, 0.0030)]}
JULY_ATT = {"PPJ Chandigarh Sector 17": 1.06, "PPJ Ambala City": 0.89, "PPJ Noida Sector 18": 1.13,
            "PPJ Delhi Karol Bagh": 0.95, "PPJ Delhi South Extension": 1.21}
SCRIPTED = {"PPJ-0054": 1.06}   # persona: exactly the store's attainment, so numbers in the spec are stable

emps = {e["employee_id"]: e for e in csv.DictReader((DATA / "employees.csv").open())}
q2_store = defaultdict(float)
for r in csv.DictReader((DATA / "sales_targets.csv").open()):
    if r["period"].startswith("Q2"):
        q2_store[r["branch"]] += float(r["target_inr"])

members = defaultdict(list)
for e in emps.values():
    if e["designation"] in SHARE:
        members[e["reports_to"]].append(e)

rows = []
for fm_id, team in members.items():
    fm = emps[fm_id]
    cat = FLOOR_CAT[fm["designation"]]
    store = fm["branch"]
    floor_month_target = q2_store[store] * FLOOR_SHARE[cat] / 3
    shares = sum(SHARE[m["designation"]] for m in team)
    for m in team:
        target = floor_month_target * SHARE[m["designation"]] / shares
        att = SCRIPTED.get(m["employee_id"], max(0.55, random.gauss(JULY_ATT[store], 0.12)))
        actual = target * att
        rate = next((r for lo, r in SLABS[cat] if att >= lo), 0.0)
        incentive = round(actual * rate / 100) * 100
        rows.append([m["employee_id"], m["employee_name"], store, m["designation"], cat, fm_id,
                     round(target), round(actual), f"{att*100:.0f}%", COMPONENT[cat], int(incentive)])
rows.sort()
with (DATA / "sales_actuals_july.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["employee_id", "employee_name", "branch", "designation", "category", "floor_manager",
                "july_target_inr", "july_actual_inr", "attainment", "incentive_component", "incentive_inr"])
    w.writerows(rows)
print("rows:", len(rows), " with incentive:", sum(1 for r in rows if r[-1] > 0))
for r in rows:
    if r[0] in ("PPJ-0054", "PPJ-0058"):
        print(r)
