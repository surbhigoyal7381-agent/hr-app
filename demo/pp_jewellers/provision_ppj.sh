#!/usr/bin/env bash
# PP Jewellers demo - Block 0 on the server: create the ppj tenant, add its TLS
# name, and record the subscription. Runs ON THE SERVER, from the repo checkout.
#
#   CONTROL_SITE=alvoraa.co deploy/../demo/pp_jewellers/provision_ppj.sh
#
# What it does, in order (each step is one command you can also run by hand):
#   1. create_tenant on the control-plane site  -> queues provisioning on the long worker
#   2. waits for the job to report Done          -> prints the Administrator password once
#   3. deploy/add_tenant_cert.sh ppj.dev.alvoraa.co   (dry run first, then real)
#   4. Alvoraa Subscription record, status Internal, plan Enterprise
#
# NOT TESTED from the development container (it has no server access). Read
# each step before running it. Nothing here touches production sites.
set -euo pipefail

CONTROL_SITE="${CONTROL_SITE:-alvoraa.co}"          # the site that serves /alvoraa-admin
BACKEND="${BACKEND:-compose-backend-1}"
SUBDOMAIN="${SUBDOMAIN:-ppj}"
BASE_DOMAIN="${BASE_DOMAIN:-dev.alvoraa.co}"
SITE="${SUBDOMAIN}.${BASE_DOMAIN}"
TENANT_NAME="PP Jewellers (demo)"
# The full Enterprise bundle. Vendor stays ticked so the derived plan label is "enterprise".
MODULES='["portal","leaves","attendance","expenses","hr_setup","tenure","recruitment","payroll","tax_benefits","performance","goals","analytics","vendor"]'

bench_exec() {   # bench_exec <site> <dotted.path> <json kwargs>
  docker exec "$BACKEND" bash -lc "cd /home/frappe/frappe-bench && bench --site $1 execute $2 --kwargs '$3'"
}

echo "== 1. create tenant $SITE on control plane $CONTROL_SITE"
KW=$(cat <<JSON
{"subdomain":"$SUBDOMAIN","tenant_name":"$TENANT_NAME","company_name":"PP Jewellers Pvt Ltd","company_abbr":"PPJ",
 "country":"India","currency":"INR","timezone":"Asia/Kolkata","fy_start_date":"2026-04-01",
 "primary_color":"#7a1f2b","modules":$MODULES}
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

echo "== 4. Alvoraa Subscription (Internal, Enterprise)"
PLAN=$(docker exec "$BACKEND" bash -lc "cd /home/frappe/frappe-bench && bench --site $CONTROL_SITE execute frappe.client.get_list --kwargs '{\"doctype\":\"Alvoraa Plan\",\"filters\":{\"name\":[\"like\",\"%Enterprise%\"]},\"limit_page_length\":1}'" | grep -o '"name": *"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
docker exec "$BACKEND" bash -lc "cd /home/frappe/frappe-bench && bench --site $CONTROL_SITE execute frappe.client.insert --kwargs '{\"doc\":{\"doctype\":\"Alvoraa Subscription\",\"site_name\":\"$SITE\",\"status\":\"Internal\",\"plan\":\"$PLAN\",\"billing_frequency\":\"Monthly\",\"started_on\":\"$(date +%F)\",\"notes\":\"PP Jewellers sales demo tenant. Never invoiced.\"}}'"

echo "== done. Next: run a health check and a usage collection from the console tenant page, then:"
echo "   docker cp demo/pp_jewellers $BACKEND:/tmp/ppj && docker cp docs/pp_jewellers/data $BACKEND:/tmp/ppj/data"
echo "   docker exec $BACKEND bash /tmp/ppj/run_all.sh --site $SITE"
