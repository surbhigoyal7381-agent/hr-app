#!/usr/bin/env bash
# PP Jewellers demo - run every seed block in order on one site.
#
# Local bench:
#   demo/pp_jewellers/run_all.sh --site ppj.localhost --bench /home/frappe/frappe-bench
# Server (inside the backend container, after copying the repo folder to /tmp/ppj):
#   docker cp demo/pp_jewellers compose-backend-1:/tmp/ppj && docker cp docs/pp_jewellers/data compose-backend-1:/tmp/ppj/data
#   docker exec compose-backend-1 bash /tmp/ppj/run_all.sh --site ppj.dev.alvoraa.co --bench /home/frappe/frappe-bench
#
# Options: --from <n> starts at block n (1..8); --only <n> runs one block.
set -euo pipefail

SITE=""; BENCH="/home/frappe/frappe-bench"; FROM=1; ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --site) SITE="$2"; shift 2 ;;
    --bench) BENCH="$2"; shift 2 ;;
    --from) FROM="$2"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    *) echo "unknown option $1"; exit 1 ;;
  esac
done
[ -n "$SITE" ] || { echo "usage: run_all.sh --site <site> [--bench <path>] [--from n] [--only n]"; exit 1; }

HERE="$(cd "$(dirname "$0")" && pwd)"
export PPJ_SCRIPT_DIR="$HERE"
export PPJ_DATA_DIR="${PPJ_DATA_DIR:-$HERE/data}"
[ -d "$PPJ_DATA_DIR" ] || PPJ_DATA_DIR="$(cd "$HERE/../../docs/pp_jewellers/data" 2>/dev/null && pwd || echo "$PPJ_DATA_DIR")"
export PPJ_DATA_DIR
export PPJ_SITE="$SITE"
PY="$BENCH/env/bin/python"
LOG="${PPJ_LOG:-/tmp/ppj_run_$(date +%Y%m%d_%H%M%S).log}"

BLOCKS=(seed_masters seed_employees seed_attendance seed_payroll seed_recruitment seed_onboarding seed_policies seed_performance)
# block numbers follow the checklist: 1 masters, 2 employees, 3 attendance, 4 payroll, 5 recruitment, 6 onboarding, 7 policies, 8 performance
NUMS=(1 2 3 4 5 6 7 8)

echo "site=$SITE bench=$BENCH data=$PPJ_DATA_DIR log=$LOG"
cd "$BENCH/sites"
for i in "${!BLOCKS[@]}"; do
  n="${NUMS[$i]}"; s="${BLOCKS[$i]}"
  if [ -n "$ONLY" ] && [ "$ONLY" != "$n" ]; then continue; fi
  if [ -z "$ONLY" ] && [ "$n" -lt "$FROM" ]; then continue; fi
  echo "=== Block $n: $s ($(date +%H:%M:%S)) ===" | tee -a "$LOG"
  "$PY" "$HERE/$s.py" --site "$SITE" 2>&1 | tee -a "$LOG"
  echo "=== Block $n done ($(date +%H:%M:%S)) ===" | tee -a "$LOG"
done
echo "all done. log: $LOG"
