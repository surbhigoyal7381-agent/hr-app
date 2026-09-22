#!/usr/bin/env bash
# Sargam Metals demo - run every seed block in order on one site.
#
# Local bench:
#   demo/sargam_metals/run_all.sh --site sargam.localhost --bench /home/frappe/frappe-bench
# Server (inside the backend container, after copying the repo folder to /tmp/sargam):
#   docker cp demo/sargam_metals compose-backend-1:/tmp/sargam
#   docker exec compose-backend-1 bash /tmp/sargam/run_all.sh --site sargam.dev.alvoraa.co --bench /home/frappe/frappe-bench
#
# Options: --from <n> starts at block n (1..2); --only <n> runs one block.
# Mirrors demo/pp_jewellers/run_all.sh - see that file for the pattern.
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
export SARGAM_SCRIPT_DIR="$HERE"
export SARGAM_SITE="$SITE"
PY="$BENCH/env/bin/python"
LOG="${SARGAM_LOG:-/tmp/sargam_run_$(date +%Y%m%d_%H%M%S).log}"

BLOCKS=(seed_masters seed_transactions)
NUMS=(1 2)

echo "site=$SITE bench=$BENCH log=$LOG"
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
