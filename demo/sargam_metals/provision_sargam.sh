#!/usr/bin/env bash
# Sargam Metals demo - Block 0 on the server: create the tenant, add its TLS
# name, and record the subscription. Runs ON THE SERVER, from the repo checkout.
# Mirrors demo/pp_jewellers/provision_ppj.sh - see that file for the pattern
# this follows and docs/sargam_metals/00-demo-instance-and-plan.md for why
# the module list below is what it is.
#
#   CONTROL_SITE=alvoraa.co demo/sargam_metals/provision_sargam.sh
#
# What it does, in order (each step is one command you can also run by hand):
#   1. create_tenant on the control-plane site  -> queues provisioning on the long worker
#   2. waits for the job to report Done          -> prints the Administrator password once
#   3. deploy/add_tenant_cert.sh <site>          (dry run first, then real)
#   4. Alvoraa Subscription record, status Internal, plan Custom
#
# NOT TESTED from this Claude Code session - it has no docker, no bench, and
# no network path to any Alvoraa server (verified: no docker daemon socket,
# and the egress proxy blocks demo.alvoraa.co on org policy). Read every step
# before running it. Nothing here touches production sites.
#
# UNRESOLVED before you run this: docs/sargam_metals/00-demo-instance-and-plan.md
# §0 - is the target really the shared demo.alvoraa.co, or a dedicated
# sargam.dev.alvoraa.co the way ppj. was dedicated to PP Jewellers? Defaults
# below assume the dedicated-subdomain reading; override SITE to use the
# literal demo.alvoraa.co instead.
set -euo pipefail

CONTROL_SITE="${CONTROL_SITE:-alvoraa.co}"          # the site that serves /alvoraa-admin
BACKEND="${BACKEND:-compose-backend-1}"
SUBDOMAIN="${SUBDOMAIN:-sargam}"
BASE_DOMAIN="${BASE_DOMAIN:-dev.alvoraa.co}"
SITE="${SITE:-${SUBDOMAIN}.${BASE_DOMAIN}}"          # override with SITE=demo.alvoraa.co if that's the real target
TENANT_NAME="Sargam Metals (demo)"

# No Alvoraa HR features needed (2026-09-22 decision: Sargam doesn't need
# Alvoraa HR). ERPNext modules are opt-in per tenant and only selectable on
# the Custom plan (alvoraa_portal/subscription.py) - ticking any one of these
# is what makes the tenant "custom" automatically.
# Deliberately NOT including erp_crm: that is ERPNext's old Desk-based
# Lead/Opportunity module, not the Frappe CRM app the proposal's AI
# lead-capture feature needs. That app isn't in this bench yet - see
# docs/sargam_metals/00-demo-instance-and-plan.md §3 before adding it here.
MODULES='["erp_stock","erp_buying","erp_manufacturing","erp_quality_management","erp_selling","erp_accounts"]'

bench_exec() {   # bench_exec <site> <dotted.path> <json kwargs>
  docker exec "$BACKEND" bash -lc "cd /home/frappe/frappe-bench && bench --site $1 execute $2 --kwargs '$3'"
}

echo "== 1. create tenant $SITE on control plane $CONTROL_SITE"
KW=$(cat <<JSON
{"subdomain":"$SUBDOMAIN","tenant_name":"$TENANT_NAME","company_name":"Sargam Metals Pvt Ltd","company_abbr":"SML",
 "country":"India","currency":"INR","timezone":"Asia/Kolkata","fy_start_date":"2026-04-01",
 "primary_color":"#1c3d5a","modules":$MODULES}
JSON
)
OUT=$(bench_exec "$CONTROL_SITE" alvoraa_portal.tenant_api.create_tenant "$(echo "$KW" | tr -d '\n')")
echo "$OUT"
JOB=$(echo "$OUT" | grep -o '"job_id": *"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
[ -n "$JOB" ] || { echo "no job_id in the response; check the control plane"; exit 1; }

echo "== 2. wait for provisioning job $JOB"
for i in $(seq 1 60); do
  ST=$(bench_exec "$CONTROL_SITE" alvoraa_portal.tenant_api.get_provision_status "{\"job_id\":\"$JOB\"}")
  echo "$ST" | grep -q '"status": *"Done"' && { echo "$ST"; break; }
  echo "$ST" | grep -q '"status": *"Failed"' && { echo "$ST"; exit 1; }
  sleep 20
done
echo "Save the Administrator password printed above. It is not shown again."

echo "== 3. TLS name"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
bash "$REPO/deploy/add_tenant_cert.sh" "$SITE" --dry-run
bash "$REPO/deploy/add_tenant_cert.sh" "$SITE"

echo "== 4. Alvoraa Subscription (Internal, Custom)"
PLAN=$(docker exec "$BACKEND" bash -lc "cd /home/frappe/frappe-bench && bench --site $CONTROL_SITE execute frappe.client.get_list --kwargs '{\"doctype\":\"Alvoraa Plan\",\"filters\":{\"name\":[\"like\",\"%Custom%\"]},\"limit_page_length\":1}'" | grep -o '"name": *"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
docker exec "$BACKEND" bash -lc "cd /home/frappe/frappe-bench && bench --site $CONTROL_SITE execute frappe.client.insert --kwargs '{\"doc\":{\"doctype\":\"Alvoraa Subscription\",\"site_name\":\"$SITE\",\"status\":\"Internal\",\"plan\":\"$PLAN\",\"billing_frequency\":\"Monthly\",\"started_on\":\"$(date +%F)\",\"notes\":\"Sargam Metals sales demo tenant. Never invoiced.\"}}'"
