#!/bin/bash
# Kinexus HRMS – Tenant Provisioning Script
#
# Creates a new isolated Frappe site (= one tenant) and installs all Kinexus apps.
# Run from INSIDE the frappe container:
#
#   docker exec <frappe-container> bash /workspace/provision_tenant.sh <subdomain> [options]
#
# Examples:
#   docker exec kinexus-frappe-1 bash /workspace/provision_tenant.sh acmecorp
#   docker exec kinexus-frappe-1 bash /workspace/provision_tenant.sh acmecorp "Acme Corporation" business
#
# Environment variables (override defaults):
#   DB_ROOT_PASSWORD   MariaDB root password (must match running MariaDB container)
#   ADMIN_PASSWORD     Initial admin password for the new site (auto-generated if blank)
#   BASE_DOMAIN        Domain suffix, default: kinexus.in
#   PRIMARY_COLOR      Hex brand color, default: #1a7f5a
#   SUPPORT_EMAIL      Support address shown in tenant UI

set -e

# ── Arguments ──────────────────────────────────────────────────────────────
SUBDOMAIN="${1:?ERROR: subdomain required. Usage: provision_tenant.sh <subdomain> [\"Tenant Name\"] [plan]}"
TENANT_NAME="${2:-$SUBDOMAIN}"
PLAN="${3:-starter}"

# ── Config ─────────────────────────────────────────────────────────────────
BASE_DOMAIN="${BASE_DOMAIN:-kinexus.in}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:?ERROR: DB_ROOT_PASSWORD must be set. Never fall back to a default — set it from the secret store.}"
SUPPORT_EMAIL="${SUPPORT_EMAIL:-support@kinexus.in}"
PRIMARY_COLOR="${PRIMARY_COLOR:-#1a7f5a}"

SITE_NAME="${SUBDOMAIN}.${BASE_DOMAIN}"

# Auto-generate a secure admin password if not provided
if [ -z "$ADMIN_PASSWORD" ]; then
    ADMIN_PASSWORD=$(tr -dc 'A-Za-z0-9!@#$%' </dev/urandom 2>/dev/null | head -c 16 || \
                     openssl rand -base64 16 | tr -d '/+=' | head -c 16)
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   Kinexus HRMS – Provisioning New Tenant         ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Site:   $SITE_NAME"
echo "║  Name:   $TENANT_NAME"
echo "║  Plan:   $PLAN"
echo "╚══════════════════════════════════════════════════╝"
echo ""

cd /home/frappe/frappe-bench

# ── Guard: site must not already exist ────────────────────────────────────
if [ -d "sites/$SITE_NAME" ]; then
    echo "ERROR: Site '$SITE_NAME' already exists. Aborting."
    exit 1
fi

# ── 1. Create site ────────────────────────────────────────────────────────
echo "[1/6] Creating site: $SITE_NAME"
bench new-site "$SITE_NAME" \
    --mariadb-root-password "$DB_ROOT_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" \
    --no-mariadb-socket

# ── 2. Install apps ───────────────────────────────────────────────────────
echo "[2/6] Installing apps (erpnext → hrms → grace_vendor_portal → grace_goals)"
bench --site "$SITE_NAME" install-app erpnext
bench --site "$SITE_NAME" install-app hrms
bench --site "$SITE_NAME" install-app grace_vendor_portal
bench --site "$SITE_NAME" install-app grace_goals

# ── 3. Apply per-tenant branding config ───────────────────────────────────
echo "[3/6] Writing tenant config to site_config.json"
bench --site "$SITE_NAME" set-config tenant_name       "$TENANT_NAME"
bench --site "$SITE_NAME" set-config subscription_plan "$PLAN"
bench --site "$SITE_NAME" set-config primary_color     "$PRIMARY_COLOR"
bench --site "$SITE_NAME" set-config support_email     "$SUPPORT_EMAIL"
bench --site "$SITE_NAME" set-config home_page         "/kinexus-login"
bench --site "$SITE_NAME" set-config host_name         "https://${SITE_NAME}"

# Plan → module flags
case "$PLAN" in
    starter)
        MODULES='["hrms"]'
        ;;
    business)
        MODULES='["hrms","vendor_portal","goals"]'
        ;;
    enterprise)
        MODULES='["hrms","vendor_portal","goals","analytics"]'
        ;;
    *)
        MODULES='["hrms","vendor_portal","goals"]'
        ;;
esac
bench --site "$SITE_NAME" set-config modules_enabled "$MODULES"

# ── 4. Scheduler + cache ──────────────────────────────────────────────────
echo "[4/6] Enabling scheduler and clearing cache"
bench --site "$SITE_NAME" enable-scheduler
bench --site "$SITE_NAME" clear-cache

# ── 5. Reload bench workers so new site is recognised ─────────────────────
echo "[5/6] Reloading bench workers"
# Send SIGHUP to gunicorn to reload without downtime
pkill -HUP gunicorn 2>/dev/null || true

# ── 6. Summary ────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   ✅  Tenant provisioned successfully!            ║"
echo "╠══════════════════════════════════════════════════╣"
printf "║  URL:      https://%-30s║\n" "${SITE_NAME}"
printf "║  Login:    Administrator%-25s║\n" ""
printf "║  Password: %-38s║\n" "${ADMIN_PASSWORD}"
printf "║  Plan:     %-38s║\n" "${PLAN}"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "⚠️  Save the admin password now — it will not be shown again."
echo ""
echo "Next steps:"
echo "  1. Point DNS: ${SITE_NAME} → this server's IP"
echo "  2. Visit https://${SITE_NAME}/kinexus-login to verify"
echo "  3. Log in as Administrator and configure Company, Employees, Vendors"
echo ""
