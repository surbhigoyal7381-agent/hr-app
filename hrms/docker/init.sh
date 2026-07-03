#!/bin/bash
# Grace Drinks – hardened bench init.
# Goal: a container RESTART never re-inits; a container RECREATION auto-restores
# from the host backup at /workspace/backups/latest instead of wiping the DB.
set -e

# ── Fast path: bench already present (normal restart) → just start, never re-init ──
if [ -d "/home/frappe/frappe-bench/apps/frappe" ]; then
    echo "Bench already exists, skipping init"
    cd frappe-bench
    bench start
    exit 0
fi

echo "Creating new bench..."
export PATH="${NVM_DIR}/versions/node/v${NODE_VERSION_DEVELOP}/bin/:${PATH}"

bench init --skip-redis-config-generation frappe-bench
cd frappe-bench

# Use containers instead of localhost
bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

# Remove redis, watch from Procfile
sed -i '/redis/d' ./Procfile
sed -i '/watch/d' ./Procfile

bench get-app erpnext
bench get-app hrms

# ── Re-apply Grace Drinks app-switcher branding (hooks.py lives in the container layer) ──
HOOKS=apps/hrms/hrms/hooks.py
sed -i 's#app_title = "Frappe HR"#app_title = "Grace Drinks"#' "$HOOKS" || true
sed -i 's#/assets/hrms/images/frappe-hr-logo.svg#/files/grace_global_logo.png#g' "$HOOKS" || true
sed -i 's#"title": "Frappe HR",#"title": "Grace Drinks",#' "$HOOKS" || true

# ── Restore Grace Drinks data+files from the host backup, else create a fresh site ──
DBGZ=$(ls -t /workspace/backups/latest/*-database.sql.gz 2>/dev/null | head -1 || true)
if [ -n "$DBGZ" ]; then
    echo "Restoring Grace Drinks from host backup: $DBGZ"
    PUB=$(ls -t /workspace/backups/latest/*-files.tar 2>/dev/null | grep -v private | head -1 || true)
    PRIV=$(ls -t /workspace/backups/latest/*-private-files.tar 2>/dev/null | head -1 || true)
    bench new-site hrms.localhost --force --mariadb-root-password 123 --admin-password admin --no-mariadb-socket
    bench --site hrms.localhost restore "$DBGZ" \
        ${PUB:+--with-public-files "$PUB"} \
        ${PRIV:+--with-private-files "$PRIV"} \
        --mariadb-root-password 123
else
    echo "No host backup found — creating a fresh site"
    bench new-site hrms.localhost --force --mariadb-root-password 123 --admin-password admin --no-mariadb-socket
    bench --site hrms.localhost install-app hrms
fi

bench --site hrms.localhost set-config developer_mode 1
bench --site hrms.localhost enable-scheduler
bench --site hrms.localhost clear-cache
bench use hrms.localhost

bench start
