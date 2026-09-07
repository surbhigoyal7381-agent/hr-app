"""
PP Jewellers demo - simulated ESSL punch generator.

Reads  docs/pp_jewellers/data/employees.csv
Writes docs/pp_jewellers/data/punches.csv             (attendance_device_id, timestamp, log_type, device_id)
       docs/pp_jewellers/data/expected_deductions.csv (what the quarter-day rule should produce, for verification)

Period: 2026-07-01 to 2026-09-06. Deterministic (seeded).
Run from the repo root:  python3 demo/pp_jewellers/generate_punches.py
"""
import csv
import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

random.seed(20260907)
DATA = Path(__file__).resolve().parents[2] / "docs" / "pp_jewellers" / "data"
START, END = date(2026, 7, 1), date(2026, 9, 6)
HO_BRANCH = "PPJ Head Office Chandigarh"
HO_HOLIDAYS = {date(2026, 8, 15)}          # stores stay open on 15 Aug
SHIFT_START, SHIFT_END = time(9, 30), time(18, 30)
LATE_THRESHOLD_MIN, EARLY_THRESHOLD_MIN = 60, 60      # quarter-day rule thresholds
FREE_PER_WEEK, PER_VIOLATION, ROUND_UP_FROM, ROUND_UP_TO = 1, 0.25, 0.75, 1.0

STORE_CODE = {
    "PPJ Chandigarh Sector 17": "CHD", "PPJ Ambala City": "AMB", "PPJ Noida Sector 18": "NOI",
    "PPJ Delhi Karol Bagh": "DKB", "PPJ Delhi South Extension": "DSE", HO_BRANCH: "HO",
}
WEEKDAY = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}

# Scripted weeks: employee -> {date: ("late", HH:MM) | ("early", HH:MM)}
SCRIPTED = {
    # Persona employee: 3 violations in week 17-23 Aug -> 0.5 day, all from Casual Leave
    "PPJ-0054": {
        date(2026, 8, 18): ("late", "10:47"),
        date(2026, 8, 20): ("late", "10:52"),
        date(2026, 8, 22): ("early", "17:05"),
    },
    # Chronic late-comer: burns Casual Leave in July, then loss of pay in August
    # (weekly off is Thursday, so no scripted dates fall on a Thursday)
    "PPJ-0058": {
        date(2026, 7, 6): ("late", "10:41"), date(2026, 7, 7): ("late", "10:36"),
        date(2026, 7, 8): ("early", "17:10"), date(2026, 7, 10): ("late", "11:02"),     # 4 -> 1.0 day
        date(2026, 7, 13): ("late", "10:45"), date(2026, 7, 14): ("late", "10:50"),
        date(2026, 7, 15): ("late", "10:38"), date(2026, 7, 17): ("early", "16:55"),    # 4 -> 1.0 day
        date(2026, 7, 20): ("late", "10:44"), date(2026, 7, 21): ("late", "10:58"),
        date(2026, 7, 22): ("early", "17:12"),                                           # 3 -> 0.5 day
        date(2026, 8, 3): ("late", "10:40"), date(2026, 8, 4): ("late", "10:35"),
        date(2026, 8, 5): ("early", "17:10"), date(2026, 8, 7): ("late", "11:00"),      # 4 -> 1.0 day (0.5 CL + 0.5 LWP)
    },
}


def _t(h, m):
    return time(h, m)


def rand_time(lo, hi):
    lo_m = lo.hour * 60 + lo.minute
    hi_m = hi.hour * 60 + hi.minute
    m = random.randint(lo_m, hi_m)
    return time(m // 60, m % 60, random.randint(0, 59))


def main():
    employees = list(csv.DictReader((DATA / "employees.csv").open()))
    profiles = {}
    for e in employees:
        r = random.random()
        profiles[e["employee_id"]] = "normal" if r < 0.80 else ("occasional" if r < 0.95 else "chronic")
    profiles["PPJ-0054"] = "normal"
    profiles["PPJ-0058"] = "chronic"

    punches = []
    per_day = {}   # (emp, date) -> (in_time, out_time)
    for e in employees:
        emp = e["employee_id"]
        off = WEEKDAY[e["weekly_off_day"]]
        is_ho = e["branch"] == HO_BRANCH
        code = STORE_CODE[e["branch"]]
        devices = [f"ESSL-{code}-1", f"ESSL-{code}-2"] if not is_ho else ["ESSL-HO-1"]
        profile = profiles[emp]
        scripted = SCRIPTED.get(emp, {})
        scripted_weeks = {d - timedelta(days=d.weekday()) for d in scripted}
        d = START
        while d <= END:
            if d.weekday() == off or (is_ho and d in HO_HOLIDAYS):
                d += timedelta(days=1)
                continue
            week = d - timedelta(days=d.weekday())
            in_scripted_week = week in scripted_weeks
            if not scripted and random.random() < 0.03:      # absent, no punch
                d += timedelta(days=1)
                continue
            # arrival
            if d in scripted and scripted[d][0] == "late":
                hh, mm = map(int, scripted[d][1].split(":"))
                t_in = time(hh, mm, random.randint(0, 59))
            elif in_scripted_week:
                t_in = rand_time(_t(9, 5), _t(9, 40))
            elif scripted:
                t_in = rand_time(_t(9, 5), _t(9, 40))
            else:
                p_late = {"normal": 0.0, "occasional": 0.08, "chronic": 0.25}[profile]
                if random.random() < p_late:
                    t_in = rand_time(_t(10, 31), _t(11, 30))
                elif random.random() < 0.10:
                    t_in = rand_time(_t(9, 41), _t(10, 20))     # late flag only, under threshold
                else:
                    t_in = rand_time(_t(9, 5), _t(9, 40))
            # departure
            if d in scripted and scripted[d][0] == "early":
                hh, mm = map(int, scripted[d][1].split(":"))
                t_out = time(hh, mm, random.randint(0, 59))
            elif not scripted and random.random() < 0.03:
                t_out = rand_time(_t(16, 30), _t(17, 25))
            else:
                t_out = rand_time(_t(18, 32), _t(19, 20))
            dev = random.choice(devices)
            punches.append((e["attendance_device_id"], datetime.combine(d, t_in), "IN", dev))
            punches.append((e["attendance_device_id"], datetime.combine(d, t_out), "OUT", dev))
            per_day[(emp, d)] = (t_in, t_out)
            d += timedelta(days=1)

    punches.sort(key=lambda p: (p[1], p[0]))
    with (DATA / "punches.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["attendance_device_id", "timestamp", "log_type", "device_id"])
        for code, ts, lt, dev in punches:
            w.writerow([code, ts.strftime("%Y-%m-%d %H:%M:%S"), lt, dev])

    # expected deductions under the quarter-day rule
    grade = {e["employee_id"]: e["employee_grade"] for e in employees}
    weekly = defaultdict(list)
    late_limit = (datetime.combine(date.today(), SHIFT_START) + timedelta(minutes=LATE_THRESHOLD_MIN)).time()
    early_limit = (datetime.combine(date.today(), SHIFT_END) - timedelta(minutes=EARLY_THRESHOLD_MIN)).time()
    for (emp, d), (t_in, t_out) in per_day.items():
        if grade[emp] in ("G5 Head", "G6 Leadership"):
            continue
        week = d - timedelta(days=d.weekday())
        if t_in > late_limit:
            weekly[(emp, week)].append((d, "Late Arrival", t_in.strftime("%H:%M")))
        if t_out < early_limit:
            weekly[(emp, week)].append((d, "Early Exit", t_out.strftime("%H:%M")))
    rows = []
    for (emp, week), v in sorted(weekly.items()):
        v.sort()
        counted = max(0, len(v) - FREE_PER_WEEK)
        computed = counted * PER_VIOLATION
        days = ROUND_UP_TO if computed >= ROUND_UP_FROM else computed
        if days > 0:
            rows.append([emp, week.isoformat(), (week + timedelta(days=6)).isoformat(), len(v), counted, computed, days,
                         "; ".join(f"{d.isoformat()} {k} {t}" for d, k, t in v)])
    with (DATA / "expected_deductions.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["employee_id", "week_start", "week_end", "violations", "counted", "computed_days", "deduction_days", "detail"])
        w.writerows(rows)
    print(f"punches: {len(punches)}  attendance-days: {len(per_day)}  expected deductions: {len(rows)}")
    for r in rows:
        if r[0] in ("PPJ-0054", "PPJ-0058"):
            print(r[:7])


if __name__ == "__main__":
    main()
