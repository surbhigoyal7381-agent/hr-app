#!/bin/bash
# Kinexus HRMS – Production init script
# Runs inside the frappe/bench container on every container start.
#
# Fast path  (bench volume already present)  → bench start
# First run  (empty frappe-bench volume)     → full install + first tenant site
#
# Custom apps (grace_goals, grace_vendor_portal) are bind-mounted from the
# host git repo, so `git pull` on the host makes changes live instantly.

set -e

DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-changeme}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
BASE_DOMAIN="${BASE_DOMAIN:-kinexus.in}"
FIRST_TENANT="${FIRST_TENANT:-demo}"
SITE_NAME="${FIRST_TENANT}.${BASE_DOMAIN}"

BENCH=/home/frappe/frappe-bench
BENCH_APPS=$BENCH/apps

# ── Fast path: bench already present (restart / redeploy) ─────────────────
if [ -d "$BENCH_APPS/frappe" ]; then
    echo "[kinexus] Bench present – starting Kinexus HRMS."
    cd $BENCH

    # Rewrite Procfile to a known-good state on every start
    printf 'web: bench serve --port 8000\n\nsocketio: bench socketio\n\n\nschedule: bench schedule\n\nworker: bench worker 1>> logs/worker.log 2>> logs/worker.error.log\n' > Procfile

    # Ensure .pth registrations survive container recreation
    SITE_PKGS=$(find $BENCH/env/lib -maxdepth 2 -name 'site-packages' -type d | head -1)
    echo "$BENCH_APPS/grace_goals"          > "$SITE_PKGS/grace_goals.pth"
    echo "$BENCH_APPS/grace_vendor_portal"  > "$SITE_PKGS/grace_vendor_portal.pth"

    # Ensure module-subfolder symlinks exist (Frappe doctype resolution)
    ln -sf "$BENCH_APPS/grace_goals/grace_goals/doctype" \
           "$BENCH_APPS/grace_goals/grace_goals/grace_goals/doctype" 2>/dev/null || true
    ln -sf "$BENCH_APPS/grace_vendor_portal/grace_vendor_portal/doctype" \
           "$BENCH_APPS/grace_vendor_portal/grace_vendor_portal/grace_vendor_portal/doctype" 2>/dev/null || true

    bench start
    exit 0
fi

# ── First run: full install ────────────────────────────────────────────────
echo "[kinexus] First-run setup – this takes ~25-35 minutes."
export PATH="${NVM_DIR}/versions/node/v${NODE_VERSION_DEVELOP}/bin/:${PATH}"

bench init --skip-redis-config-generation frappe-bench
cd $BENCH

bench set-mariadb-host mariadb
bench set-redis-cache-host   redis://redis:6379
bench set-redis-queue-host   redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

sed -i '/redis/d' ./Procfile
sed -i '/watch/d' ./Procfile

# ── Download ERPNext + HRMS from upstream ─────────────────────────────────
bench get-app erpnext
bench get-app hrms

# ── Register grace apps via .pth (bind-mounted; no pip install needed) ────
SITE_PKGS=$(find $BENCH/env/lib -maxdepth 2 -name 'site-packages' -type d | head -1)
echo "$BENCH_APPS/grace_goals"          > "$SITE_PKGS/grace_goals.pth"
echo "$BENCH_APPS/grace_vendor_portal"  > "$SITE_PKGS/grace_vendor_portal.pth"

# Module-subfolder symlinks (Frappe doctype path resolution)
ln -sf "$BENCH_APPS/grace_goals/grace_goals/doctype" \
       "$BENCH_APPS/grace_goals/grace_goals/grace_goals/doctype" 2>/dev/null || true
ln -sf "$BENCH_APPS/grace_vendor_portal/grace_vendor_portal/doctype" \
       "$BENCH_APPS/grace_vendor_portal/grace_vendor_portal/grace_vendor_portal/doctype" 2>/dev/null || true

# ── Restore from backup or create first tenant site ───────────────────────
DBGZ=$(ls -t /workspace/backups/latest/*-database.sql.gz 2>/dev/null | head -1 || true)

bench new-site "$SITE_NAME" \
    --force \
    --mariadb-root-password "$DB_ROOT_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" \
    --no-mariadb-socket

if [ -n "$DBGZ" ]; then
    echo "[kinexus] Restoring from backup: $DBGZ"
    PUB=$(ls -t /workspace/backups/latest/*-files.tar 2>/dev/null | grep -v private | head -1 || true)
    PRIV=$(ls -t /workspace/backups/latest/*-private-files.tar 2>/dev/null | head -1 || true)
    bench --site "$SITE_NAME" restore "$DBGZ" \
        ${PUB:+--with-public-files  "$PUB"}  \
        ${PRIV:+--with-private-files "$PRIV"} \
        --mariadb-root-password "$DB_ROOT_PASSWORD"
    bench --site "$SITE_NAME" install-app grace_goals
    bench --site "$SITE_NAME" install-app grace_vendor_portal
else
    echo "[kinexus] No backup – installing fresh first tenant: $SITE_NAME"
    bench --site "$SITE_NAME" install-app erpnext
    bench --site "$SITE_NAME" install-app hrms
    bench --site "$SITE_NAME" install-app grace_goals
    bench --site "$SITE_NAME" install-app grace_vendor_portal
fi

# ── Per-tenant branding defaults (first tenant = demo) ────────────────────
bench --site "$SITE_NAME" set-config tenant_name      "Kinexus HRMS Demo"
bench --site "$SITE_NAME" set-config primary_color    "#1a7f5a"
bench --site "$SITE_NAME" set-config subscription_plan "demo"
bench --site "$SITE_NAME" set-config home_page        "/kinexus-login"
bench --site "$SITE_NAME" set-config host_name        "https://${SITE_NAME}"

bench --site "$SITE_NAME" set-config developer_mode 1
bench --site "$SITE_NAME" enable-scheduler
bench --site "$SITE_NAME" clear-cache

echo "[kinexus] First-run complete."
echo "  Demo tenant: https://${SITE_NAME}"
echo "  Admin password: ${ADMIN_PASSWORD}"
echo "  To add a new tenant: docker exec <frappe-container> bash /workspace/provision_tenant.sh <subdomain> \"Tenant Name\""

bench start
