#!/usr/bin/env bash
# ALV-149 (D5) dry-run: what the brand_text patch WOULD change on each site.
#
# READ-ONLY. Plain SELECTs through `bench mariadb`; it writes nothing and needs
# none of this slice's code on the server, so it runs against the image that is
# there today. Surbhi reads its output BEFORE the patch runs on that server.
#
# The rules below must match alvoraa_portal/brand_text.py exactly -
# tests/test_brand_text_149.py fails if a value is in one and not the other.
#
# Run it inside the backend container, from the repo on your machine:
#
#   docker exec -i <backend-container> bash -s < scripts/brand_text_dry_run.sh
#   docker exec -i <backend-container> bash -s -- dtc.alvoraa.co < scripts/brand_text_dry_run.sh
#
# With no site names it reads every site in sites/. Running it on dev or
# production is a server command: ask first (CLAUDE.md section 2).
set -euo pipefail

BENCH=${BENCH:-/home/frappe/frappe-bench}
cd "$BENCH"

if [ "$#" -gt 0 ]; then
  SITES="$*"
else
  SITES=$(for d in sites/*/; do d=${d%/}; d=${d#sites/}; [ -f "sites/$d/site_config.json" ] && echo "$d"; done)
fi

read -r -d '' SQL <<'SQL' || true
SELECT IF(COALESCE(s.value,'') IN ('','Frappe','ERPNext','Alvoraa','Alvoraa HR','Alvoraa HRMS'),'change','leave') AS action,
       CONCAT(d.dt,'.app_name') AS setting, COALESCE(s.value,'(not set)') AS current_value,
       IF(COALESCE(s.value,'') IN ('','Frappe','ERPNext','Alvoraa','Alvoraa HR','Alvoraa HRMS'),'Alvora HRMS','(left alone)') AS proposed
FROM (SELECT 'Website Settings' AS dt UNION ALL SELECT 'System Settings') d
LEFT JOIN tabSingles s ON s.doctype = d.dt AND s.field = 'app_name'
WHERE COALESCE(s.value,'') <> 'Alvora HRMS'
UNION ALL
SELECT IF(TRIM(value) IN ('Alvoraa','Alvoraa HR','Alvoraa HRMS','© Alvoraa','Powered by Alvoraa'),'change','leave'),
       CONCAT('Website Settings.',field), value,
       IF(TRIM(value) IN ('Alvoraa','Alvoraa HR','Alvoraa HRMS','© Alvoraa','Powered by Alvoraa'),
          REPLACE(value,'Alvoraa','Alvora'),'(left alone)')
FROM tabSingles
WHERE doctype = 'Website Settings' AND field IN ('brand_html','copyright','footer_powered','title_prefix')
  AND (value LIKE BINARY '%Alvoraa%' OR value LIKE BINARY '%ALVORAA%')
UNION ALL
SELECT IF(name IN ('Alvoraa','Alvoraa HR','Alvoraa HRMS'),'change','leave'),
       'Email Account (From name)', name,
       IF(name IN ('Alvoraa','Alvoraa HR','Alvoraa HRMS'),REPLACE(name,'Alvoraa','Alvora'),'(left alone)')
FROM `tabEmail Account` WHERE name LIKE '%Alvoraa%'
UNION ALL
SELECT 'change', 'Desk Help menu item', item_label, 'hidden'
FROM `tabNavbar Item`
WHERE parent = 'Navbar Settings' AND parentfield = 'help_dropdown'
  AND item_label IN ('Frappe Support') AND hidden = 0
UNION ALL
SELECT IF(item_type = 'Route','change','ok'), 'Desk menu: Switch to Employee Portal (ALV-152)',
       CONCAT(item_type,' ',COALESCE(route,action,'')),
       IF(item_type = 'Route','Action window.location.assign(''/hrms-employee'')','(already right)')
FROM `tabNavbar Item`
WHERE parent = 'Navbar Settings' AND parentfield = 'settings_dropdown'
  AND item_label = 'Switch to Employee Portal'
UNION ALL
SELECT 'report', 'Emails queued, not sent (keep their old text)', COUNT(*), ''
FROM `tabEmail Queue` WHERE status = 'Not Sent';
SQL

for site in $SITES; do
  echo "=== $site"
  if grep -q '"alvoraa_control_plane"' "sites/$site/site_config.json" 2>/dev/null; then
    echo "(control plane: Email Account names are reported but never renamed here)"
  fi
  grep -o '"tenant_name": *"Alvoraa"' "sites/$site/site_config.json" 2>/dev/null \
    && echo "(report only: site_config tenant_name is \"Alvoraa\" - not changed by the patch)" || true
  bench --site "$site" mariadb -e "$SQL" 2>&1 || echo "(could not read $site)"
done
