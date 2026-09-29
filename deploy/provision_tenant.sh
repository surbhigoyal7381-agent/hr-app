#!/bin/bash
# Alvoraa HRMS – Tenant Provisioning Script
#
# Creates a new isolated Frappe site (= one tenant) and installs all Alvoraa apps.
# Run from INSIDE the frappe container:
#
#   docker exec <frappe-container> bash /workspace/provision_tenant.sh <subdomain> [options]
#
# Examples:
#   docker exec compose-frappe-1 bash /workspace/provision_tenant.sh acmecorp
#   docker exec compose-frappe-1 bash /workspace/provision_tenant.sh acmecorp "Acme Corporation" business
#
# Environment variables (override defaults):
#   DB_ROOT_PASSWORD   MariaDB root password (must match running MariaDB container)
#   ADMIN_PASSWORD     Initial admin password for the new site (auto-generated if blank)
#   BASE_DOMAIN        Domain suffix, default: alvoraa.co
#   PRIMARY_COLOR      Hex brand color, default: #1a7f5a
#   SUPPORT_EMAIL      Support address shown in tenant UI

set -e

# ── Arguments ──────────────────────────────────────────────────────────────
SUBDOMAIN="${1:?ERROR: subdomain required. Usage: provision_tenant.sh <subdomain> [\"Tenant Name\"] [plan]}"
TENANT_NAME="${2:-$SUBDOMAIN}"
PLAN="${3:-starter}"
# Comma-separated feature ids, passed by tenant_api._run_provision. Left empty by
# a manual run, which then behaves as it always did and installs everything.
FEATURES="${4:-}"

has_feature() {
    [ -z "$FEATURES" ] && return 0          # not told: assume sold
    case ",$FEATURES," in *",$1,"*) return 0 ;; *) return 1 ;; esac
}

# ── Config ─────────────────────────────────────────────────────────────────
BASE_DOMAIN="${BASE_DOMAIN:-alvoraa.co}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:?ERROR: DB_ROOT_PASSWORD must be set. Never fall back to a default — set it from the secret store.}"
SUPPORT_EMAIL="${SUPPORT_EMAIL:-support@alvoraa.co}"
PRIMARY_COLOR="${PRIMARY_COLOR:-#1a7f5a}"

SITE_NAME="${SUBDOMAIN}.${BASE_DOMAIN}"

# Auto-generate a secure admin password if not provided
if [ -z "$ADMIN_PASSWORD" ]; then
    ADMIN_PASSWORD=$(tr -dc 'A-Za-z0-9!@#$%' </dev/urandom 2>/dev/null | head -c 16 || \
                     openssl rand -base64 16 | tr -d '/+=' | head -c 16)
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   Alvoraa HRMS – Provisioning New Tenant         ║"
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
# erpnext and hrms are not optional: Frappe HR depends on ERPNext for Bank
# Account, Journal Entry, Supplier and more, so removing it breaks payroll and
# expenses on every plan. alvoraa_portal is the product itself.
#
# alvoraa_goals IS optional, and it is the only REAL denial we have: doctypes
# that were never installed cannot be reached by any URL, role or API call.
# Which is also why a downgrade must never uninstall it - dropping the app drops
# the customer's data.
echo "[2/6] Installing apps (erpnext → hrms → alvoraa_portal)"
bench --site "$SITE_NAME" install-app erpnext
bench --site "$SITE_NAME" install-app hrms
bench --site "$SITE_NAME" install-app alvoraa_portal

if has_feature goals; then
    echo "      + alvoraa_goals (sold)"
    bench --site "$SITE_NAME" install-app alvoraa_goals
else
    echo "      - alvoraa_goals skipped: not part of this plan"
fi

# Indian statutory compliance. Installed only when sold: its doctypes all hang
# off Sales Invoice, Purchase Invoice or the Accounts module, so on an HR-only
# tenant there is nothing for it to act on. create_tenant refuses the selection
# unless Accounts, Selling and Buying were bought too, so by the time we get
# here the modules it needs are present.
if has_feature india_compliance; then
    echo "      + india_compliance (sold)"
    bench --site "$SITE_NAME" install-app india_compliance
else
    echo "      - india_compliance skipped: not part of this plan"
fi

# Frappe CRM is NOT installed here, on purpose, even when sold. Its
# setup_wizard_complete hook seeds three fake @example.com users with Sales
# roles plus fake leads on any site where it is present when the setup wizard
# finishes - and the wizard runs AFTER this script (tenant_api._run_provision
# calls complete_company_setup). tenant_api installs it once the wizard is done.
# A manual run has no tenant_api, so it says what to do instead.
if has_feature crm; then
    echo "      ~ crm (sold): installed by tenant_api AFTER the setup wizard."
    echo "        Manual run? Finish the wizard first, then:"
    echo "        bench --site $SITE_NAME install-app crm"
fi

# Frappe WhatsApp has no setup-wizard hook and no ERPNext dependency, so it
# can go in here like india_compliance. Its doctypes are System Manager only;
# the tenant's administrator configures the Meta account afterwards.
if has_feature whatsapp; then
    echo "      + frappe_whatsapp (sold)"
    bench --site "$SITE_NAME" install-app frappe_whatsapp
else
    echo "      - frappe_whatsapp skipped: not part of this plan"
fi

# Frappe LMS. No setup-wizard hook, so - like india_compliance and WhatsApp -
# it can go in here directly. It declares required_apps = ["frappe/payments"];
# Payments is infrastructure for it, not a separate purchase, so it is
# installed here too, unconditionally inside this branch, never on its own.
# Once both apps are on the site, alvoraa_portal.lms_defaults.apply_safe_defaults
# turns off guest access, self sign-up and the public jobs board - see that
# module for why this must run before anyone can reach the site.
if has_feature lms; then
    echo "      + payments (infrastructure for lms)"
    bench --site "$SITE_NAME" install-app payments
    echo "      + lms (sold)"
    bench --site "$SITE_NAME" install-app lms
    echo "      + applying LMS privacy defaults"
    bench --site "$SITE_NAME" execute alvoraa_portal.lms_defaults.apply_safe_defaults
else
    echo "      - lms skipped: not part of this plan"
fi

# Frappe Helpdesk. No setup-wizard hook of its own, so it can go in here
# directly, the same as LMS above. It declares required_apps = ["telephony"];
# Telephony is infrastructure for it, installed here too, never sold on its
# own. alvoraa_portal.helpdesk_defaults turns off the public defaults its
# customer portal ships with - see that module.
if has_feature helpdesk; then
    echo "      + telephony (infrastructure for helpdesk)"
    bench --site "$SITE_NAME" install-app telephony
    echo "      + helpdesk (sold)"
    bench --site "$SITE_NAME" install-app helpdesk
    echo "      + applying Helpdesk privacy defaults"
    bench --site "$SITE_NAME" execute alvoraa_portal.helpdesk_defaults.apply_safe_defaults
else
    echo "      - helpdesk skipped: not part of this plan"
fi

# ── 3. Apply per-tenant branding config ───────────────────────────────────
echo "[3/6] Writing tenant config to site_config.json"
bench --site "$SITE_NAME" set-config tenant_name       "$TENANT_NAME"
bench --site "$SITE_NAME" set-config subscription_plan "$PLAN"
bench --site "$SITE_NAME" set-config primary_color     "$PRIMARY_COLOR"
bench --site "$SITE_NAME" set-config accent_color      "${ACCENT_COLOR:-#f59e0b}"
bench --site "$SITE_NAME" set-config support_email     "$SUPPORT_EMAIL"
bench --site "$SITE_NAME" set-config home_page         "/alvoraa-login"
bench --site "$SITE_NAME" set-config host_name         "https://${SITE_NAME}"

# `modules_enabled` is the legacy label list the tenant console displays. It used
# to be a hardcoded plan->modules case statement here: a FIFTH copy of the plan
# definition, agreeing with none of the other four. Derived from what was
# actually sold now, so it cannot drift.
#
# Entitlement itself does NOT come from this key - tenant_api writes `features`,
# which subscription.enabled_features() reads first.
if [ -n "$FEATURES" ]; then
    MODULES=$(printf '%s' "$FEATURES" | awk -F, '{printf "["; for(i=1;i<=NF;i++){printf "%s\"%s\"", (i>1?",":""), $i}; printf "]"}')
else
    MODULES='["hrms"]'
fi
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
echo "  2. Visit https://${SITE_NAME}/alvoraa-login to verify"
echo "  3. Log in as Administrator and configure Company, Employees, Vendors"
echo ""
