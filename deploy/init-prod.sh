#!/bin/bash
# Grace Drinks HRMS – Production init script
# Runs inside the frappe/bench container on every container start.
#
# Fast path  (normal restart / redeploy)  → bench start
# First run  (empty frappe-bench volume)  → full Frappe + ERPNext + HRMS setup
#
# The hrms/ app is bind-mounted from the host git repo, so Python/JS changes
# made via `git pull` on the host are live immediately – no rebuild needed.
# Call `scripts/deploy.sh` (from the host) to migrate + clear-cache after a pull.

set -e

DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-changeme}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"

# ── Fast path ─────────────────────────────────────────────────────────────────
if [ -d "/home/frappe/frappe-bench/apps/frappe" ]; then
    echo "[init-prod] Bench already present – starting Grace Drinks HRMS."
    cd frappe-bench
    bench start
    exit 0
fi

# ── First run ─────────────────────────────────────────────────────────────────
echo "[init-prod] First-run setup – this takes ~20-30 minutes on initial install."
export PATH="${NVM_DIR}/versions/node/v${NODE_VERSION_DEVELOP}/bin/:${PATH}"

bench init --skip-redis-config-generation frappe-bench
cd frappe-bench

# Point services at Docker Compose service names (not localhost)
bench set-mariadb-host mariadb
bench set-redis-cache-host  redis://redis:6379
bench set-redis-queue-host  redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

# Remove redis + watch workers (managed by Docker, not bench Procfile)
sed -i '/redis/d' ./Procfile
sed -i '/watch/d'  ./Procfile

# ERPNext (required dependency of HRMS)
bench get-app erpnext

# HRMS is bind-mounted from the host git repo – register it with pip so
# Python can import it.  We do NOT run `bench get-app hrms` here because
# the directory already exists via the bind mount.
pip install -e apps/hrms

# ── Restore from backup if available, otherwise create fresh site ─────────────
DBGZ=$(ls -t /workspace/backups/latest/*-database.sql.gz 2>/dev/null | head -1 || true)

bench new-site hrms.localhost \
    --force \
    --mariadb-root-password "$DB_ROOT_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" \
    --no-mariadb-socket

if [ -n "$DBGZ" ]; then
    echo "[init-prod] Restoring Grace Drinks data from backup: $DBGZ"
    PUB=$(ls -t /workspace/backups/latest/*-files.tar 2>/dev/null | grep -v private | head -1 || true)
    PRIV=$(ls -t /workspace/backups/latest/*-private-files.tar 2>/dev/null | head -1 || true)
    bench --site hrms.localhost restore "$DBGZ" \
        ${PUB:+--with-public-files  "$PUB"}  \
        ${PRIV:+--with-private-files "$PRIV"} \
        --mariadb-root-password "$DB_ROOT_PASSWORD"
else
    echo "[init-prod] No backup found – installing fresh Grace Drinks HRMS."
    bench --site hrms.localhost install-app erpnext
    bench --site hrms.localhost install-app hrms
fi

bench --site hrms.localhost set-config developer_mode 1
bench --site hrms.localhost enable-scheduler
bench --site hrms.localhost clear-cache
bench use hrms.localhost

echo "[init-prod] First-run setup complete.  Starting Grace Drinks HRMS."
bench start
