#!/bin/bash
# Grace Drinks – hardened bench init.
# Goal: a container RESTART never re-inits; a container RECREATION auto-restores
# from the host backup at /workspace/backups/latest instead of wiping the DB.
set -e

# ── Credentials: override via environment; the defaults below are LOCAL-DEV ONLY ──
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-123}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"

# ── Grace app symlink helper ──────────────────────────────────────────────────
# Grace apps are mounted at /home/frappe/grace_*_src (outside bench) to avoid
# confusing bench init. This function creates the symlinks bench expects.
setup_grace_symlinks() {
    BENCH_APPS=/home/frappe/frappe-bench/apps
    mkdir -p "$BENCH_APPS"
    ln -sfn /home/frappe/grace_goals_src         "$BENCH_APPS/grace_goals"
    ln -sfn /home/frappe/grace_vendor_portal_src "$BENCH_APPS/grace_vendor_portal"
    # Module-subfolder symlinks for Frappe doctype path resolution
    ln -sf "$BENCH_APPS/grace_goals/grace_goals/doctype" \
           "$BENCH_APPS/grace_goals/grace_goals/grace_goals/doctype" 2>/dev/null || true
    ln -sf "$BENCH_APPS/grace_vendor_portal/grace_vendor_portal/doctype" \
           "$BENCH_APPS/grace_vendor_portal/grace_vendor_portal/grace_vendor_portal/doctype" 2>/dev/null || true
    # .pth files so the bench virtualenv can import the grace packages
    SITE_PKGS=$(find /home/frappe/frappe-bench/env/lib -maxdepth 2 -name 'site-packages' -type d | head -1)
    echo "$BENCH_APPS/grace_goals"         > "$SITE_PKGS/grace_goals.pth"
    echo "$BENCH_APPS/grace_vendor_portal" > "$SITE_PKGS/grace_vendor_portal.pth"
}

# ── Fast path: bench already present (normal restart or named-volume recreation) ──
if [ -d "/home/frappe/frappe-bench/apps/frappe" ]; then
    echo "Bench already exists, skipping init"
    cd frappe-bench
    # currentsite.txt: fallback for requests with no matching Host header (direct port 8000 access)
    echo "hrms.localhost" > sites/currentsite.txt
    # Rewrite Procfile to known-good state
    printf 'web: bench serve  --port 8000\n\nsocketio: bench socketio\n\n\n\n\nschedule: bench schedule\n\nworker:  bench worker 1>> logs/worker.log 2>> logs/worker.error.log\n' > Procfile
    setup_grace_symlinks
    bench start
    exit 0
fi

echo "Creating new bench..."
export PATH="${NVM_DIR}/versions/node/v${NODE_VERSION_DEVELOP}/bin/:${PATH}"

# bench init refuses to run if the target directory already exists.
# Docker creates /home/frappe/frappe-bench as the named-volume mountpoint
# even when the volume is empty, so we init to /tmp then merge in.
bench init --skip-redis-config-generation /tmp/frappe-bench-init
cp -a /tmp/frappe-bench-init/. /home/frappe/frappe-bench/
rm -rf /tmp/frappe-bench-init
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

# Create grace app symlinks and register via .pth files
setup_grace_symlinks

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
    bench new-site hrms.localhost --force --mariadb-root-password "$DB_ROOT_PASSWORD" --admin-password "$ADMIN_PASSWORD" --no-mariadb-socket
    bench --site hrms.localhost restore "$DBGZ" \
        ${PUB:+--with-public-files "$PUB"} \
        ${PRIV:+--with-private-files "$PRIV"} \
        --mariadb-root-password "$DB_ROOT_PASSWORD"
    # Register custom apps in apps.txt before installing
    printf 'frappe\nerpnext\nhrms\ngrace_goals\ngrace_vendor_portal\n' > sites/apps.txt
    bench --site hrms.localhost install-app grace_goals
    bench --site hrms.localhost install-app grace_vendor_portal
else
    echo "No host backup found — creating a fresh site"
    bench new-site hrms.localhost --force --mariadb-root-password "$DB_ROOT_PASSWORD" --admin-password "$ADMIN_PASSWORD" --no-mariadb-socket
    printf 'frappe\nerpnext\nhrms\ngrace_goals\ngrace_vendor_portal\n' > sites/apps.txt
    bench --site hrms.localhost install-app hrms
    bench --site hrms.localhost install-app grace_goals
    bench --site hrms.localhost install-app grace_vendor_portal
fi

bench --site hrms.localhost set-config developer_mode 1
bench --site hrms.localhost enable-scheduler
bench --site hrms.localhost clear-cache
bench use hrms.localhost

bench start
