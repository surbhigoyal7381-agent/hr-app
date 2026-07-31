#!/bin/bash
# Kinexus HRMS – Tenant Provisioning Script
#
# Args: <subdomain> [tenant_name] [plan] [modules]
#   modules = comma-separated IDs: hrms,payroll,recruitment,vendor,goals,analytics
#
# Environment variables:
#   DB_ROOT_PASSWORD   MariaDB root password
#   ADMIN_PASSWORD     Initial Administrator password (auto-generated if blank)
#   BASE_DOMAIN        Domain suffix (default: localhost)
#   PRIMARY_COLOR      Hex brand colour (default: #16A373)
#   SUPPORT_EMAIL      Help address shown in tenant UI

set -e

# ── Arguments ──────────────────────────────────────────────────────────────
SUBDOMAIN="${1:?ERROR: subdomain required. Usage: provision_tenant.sh <subdomain> [name] [plan] [modules]}"
TENANT_NAME="${2:-$SUBDOMAIN}"
PLAN="${3:-starter}"
MODULES="${4:-hrms}"   # comma-separated module IDs from the admin UI

# ── Config ─────────────────────────────────────────────────────────────────
BASE_DOMAIN="${BASE_DOMAIN:-localhost}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-123}"
SUPPORT_EMAIL="${SUPPORT_EMAIL:-support@kinexus.in}"
PRIMARY_COLOR="${PRIMARY_COLOR:-#16A373}"
SITE_NAME="${SUBDOMAIN}.${BASE_DOMAIN}"

# Password must be alphanumeric — special chars like $ break shell interpolation
# into bench execute later. Python generator also produces alphanumeric only now.
if [ -z "$ADMIN_PASSWORD" ]; then
    ADMIN_PASSWORD=$(tr -dc 'A-Za-z0-9' </dev/urandom 2>/dev/null | head -c 18 || \
                     openssl rand -base64 18 | tr -dc 'A-Za-z0-9' | head -c 18)
fi

# ── Module flags ────────────────────────────────────────────────────────────
has_module() { echo ",$MODULES," | grep -q ",$1,"; }

INSTALL_VENDOR=0; has_module "vendor"      && INSTALL_VENDOR=1 || true
INSTALL_GOALS=0;  has_module "goals"       && INSTALL_GOALS=1  || true
INSTALL_RECRUIT=0;has_module "recruitment" && INSTALL_RECRUIT=1|| true

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   Kinexus HRMS – Provisioning New Tenant         ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Site:    $SITE_NAME"
echo "║  Name:    $TENANT_NAME"
echo "║  Plan:    $PLAN"
echo "║  Modules: $MODULES"
echo "╚══════════════════════════════════════════════════╝"
echo ""

cd /home/frappe/frappe-bench

# ── Guard: site must not already exist ─────────────────────────────────────
if [ -d "sites/$SITE_NAME" ]; then
    echo "ERROR: Site '$SITE_NAME' already exists. Aborting."
    exit 1
fi

# ── 1. Create site ─────────────────────────────────────────────────────────
echo "[1/6] Creating Frappe site: $SITE_NAME"
bench new-site "$SITE_NAME" \
    --mariadb-root-password "$DB_ROOT_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" \
    --no-mariadb-socket

# ── 2. Install apps based on selected modules ───────────────────────────────
echo "[2/6] Installing apps for: $MODULES"
bench --site "$SITE_NAME" install-app erpnext
bench --site "$SITE_NAME" install-app hrms

if [ "$INSTALL_VENDOR" = "1" ]; then
    echo "       → grace_vendor_portal (Vendor & Delivery)"
    bench --site "$SITE_NAME" install-app grace_vendor_portal
fi
if [ "$INSTALL_GOALS" = "1" ]; then
    echo "       → grace_goals (Goals & OKR)"
    bench --site "$SITE_NAME" install-app grace_goals
fi

# ── 3. Branding + site config ──────────────────────────────────────────────
echo "[3/6] Writing tenant config"
bench --site "$SITE_NAME" set-config tenant_name       "$TENANT_NAME"
bench --site "$SITE_NAME" set-config subscription_plan "$PLAN"
bench --site "$SITE_NAME" set-config primary_color     "$PRIMARY_COLOR"
bench --site "$SITE_NAME" set-config support_email     "$SUPPORT_EMAIL"
bench --site "$SITE_NAME" set-config host_name         "http://${SITE_NAME}"

# Non-admin employees land on the wrapper portal after login;
# Administrator's desk home_page is set separately in step 4.
bench --site "$SITE_NAME" set-config home_page "/hrms-employee"

# Build modules_enabled JSON from MODULES arg
MOD_JSON='["hrms"'
has_module "payroll"     && MOD_JSON="${MOD_JSON},\"Payroll\""       || true
has_module "recruitment" && MOD_JSON="${MOD_JSON},\"Recruitment\""   || true
has_module "vendor"      && MOD_JSON="${MOD_JSON},\"Vendor Portal\"" || true
has_module "goals"       && MOD_JSON="${MOD_JSON},\"Goals\""         || true
has_module "analytics"   && MOD_JSON="${MOD_JSON},\"Analytics\""     || true
MOD_JSON="${MOD_JSON}]"
bench --site "$SITE_NAME" set-config modules_enabled "$MOD_JSON"

# ── 4. Post-install: lock in password + set landing pages ──────────────────
echo "[4/6] Configuring Administrator user"

# Explicitly set password — re-affirms it in case any install hook changed it.
# ADMIN_PASSWORD is alphanumeric so safe to inline in the Python string.
bench --site "$SITE_NAME" execute \
    "__import__('frappe.utils.password',fromlist=['update_password']).update_password('Administrator','$ADMIN_PASSWORD') or frappe.db.commit()" \
    2>/dev/null || echo "       [warn] explicit password update failed — bench new-site value applies"

# Administrator lands on HR Setup workspace (not the generic desk home).
bench --site "$SITE_NAME" execute \
    "frappe.db.set_value('User','Administrator','home_page','/app/hr-setup') or frappe.db.commit()" \
    2>/dev/null || echo "       [warn] could not set Administrator home_page — set manually in User record"

# ── 5. Scheduler + cache ───────────────────────────────────────────────────
echo "[5/6] Enabling scheduler and clearing cache"
bench --site "$SITE_NAME" enable-scheduler
bench --site "$SITE_NAME" clear-cache

# ── 6. Reload workers ──────────────────────────────────────────────────────
echo "[6/6] Reloading bench workers"
pkill -HUP gunicorn 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   ✅  Tenant provisioned successfully!            ║"
echo "╠══════════════════════════════════════════════════╣"
printf "║  URL:      http://%-31s║\n" "${SITE_NAME}"
printf "║  Login:    Administrator%-25s║\n" ""
printf "║  Password: %-38s║\n" "${ADMIN_PASSWORD}"
printf "║  Modules:  %-38s║\n" "${MODULES}"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "⚠️  Save the admin password — it will not be shown again."
echo ""
echo "  Admin desk:      http://${SITE_NAME}/app/hr-setup"
echo "  Employee portal: http://${SITE_NAME}/hrms-employee"
echo ""
