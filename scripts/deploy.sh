#!/bin/bash
# Grace Drinks HRMS – Hot deploy script
# ──────────────────────────────────────
# Called automatically by GitHub Actions on every push to `main`.
# Can also be run manually on the Oracle VM:
#   bash /opt/hr-app/scripts/deploy.sh
#
# What it does (without restarting the container):
#   1. git pull on the outer repo (updates deploy/ scripts)
#   2. git pull inside hrms/ (updates the bind-mounted HRMS app)
#   3. bench migrate  – applies any schema / fixture changes
#   4. bench build    – recompiles JS/CSS if frontend files changed
#   5. bench clear-cache

set -e

APP_DIR="/opt/hr-app"

log() { echo ""; echo "━━━ $* ━━━"; }

# ── 1. Pull latest code ───────────────────────────────────────────────────────
log "[1/5] Pulling latest code"
cd "$APP_DIR"
git pull origin main

# The hrms/ subfolder has its own git history (frappe/hrms + our commits)
if [ -d "$APP_DIR/hrms/.git" ]; then
    echo "  → Updating hrms app..."
    git -C "$APP_DIR/hrms" fetch --all
    # follow whichever branch was checked out; default is develop
    HRMS_BRANCH=$(git -C "$APP_DIR/hrms" rev-parse --abbrev-ref HEAD)
    git -C "$APP_DIR/hrms" pull origin "$HRMS_BRANCH"
fi

# ── 2. Locate the running frappe container ────────────────────────────────────
CONTAINER=$(docker ps \
    --filter "name=frappe" \
    --filter "status=running" \
    --format "{{.Names}}" \
    | grep -v mariadb | grep -v redis | grep -v nginx \
    | head -1 || true)

if [ -z "$CONTAINER" ]; then
    log "Frappe container not running – starting the full stack"
    cd "$APP_DIR/deploy"
    docker compose up -d
    echo "  → Stack starting.  Watch with:  docker compose logs -f frappe"
    echo "  → First startup takes ~20-30 min.  Re-run this script once up."
    exit 0
fi

log "[2/5] Frappe container: $CONTAINER"

# ── 3. Database migrations ────────────────────────────────────────────────────
log "[3/5] Running bench migrate"
docker exec "$CONTAINER" bash -c "
    cd /home/frappe/frappe-bench
    bench --site hrms.localhost migrate
"

# ── 4. Rebuild frontend assets (only needed if JS/CSS changed) ────────────────
log "[4/5] Rebuilding frontend assets (hrms)"
docker exec "$CONTAINER" bash -c "
    cd /home/frappe/frappe-bench
    bench --site hrms.localhost build --app hrms
" || echo "  (build step failed or not needed – continuing)"

# ── 5. Clear cache ────────────────────────────────────────────────────────────
log "[5/5] Clearing cache"
docker exec "$CONTAINER" bash -c "
    cd /home/frappe/frappe-bench
    bench --site hrms.localhost clear-cache
"

echo ""
echo "════════════════════════════════════════════"
echo "  Deploy complete  $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Site: http://$(curl -s ifconfig.me 2>/dev/null || echo '<oracle-ip>')"
echo "════════════════════════════════════════════"
