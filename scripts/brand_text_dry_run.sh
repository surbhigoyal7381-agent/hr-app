#!/usr/bin/env bash
# ALV-149 (D5) dry-run: what the brand_text patch WOULD change on each site.
#
# READ-ONLY. Plain SELECTs through `bench mariadb`; it writes nothing and needs
# none of this slice's code on the server, so it runs against the image that is
# there today. Surbhi reads its output BEFORE the patch runs on that server.
#
# The rules below must match alvoraa_portal/brand_text.py exactly -
# alvoraa_portal/alvoraa_portal/tests/test_brand_spelling_149.py runs this SQL
# on a site with near-miss values and fails if its "change" rows differ from
# what the patches would do.
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
-- Every comparison is BINARY: exact case, and trailing spaces count. MariaDB's
-- default collation would treat 'frappe' and 'Frappe ' as 'Frappe', and the
-- patch (Python) does not - so without BINARY this list would promise changes
-- the patch never makes. @alvoraa_cp is 1 on the control plane (set by the
-- shell below, from site_config.json), where Email Accounts are never renamed -
-- except the ones Surbhi named one by one (brand_text.NAMED_EMAIL_RENAMES,
-- 'Alvoraa HR Admin'): alvoraa.co's own sending account lives there.
SELECT IF(BINARY COALESCE(s.value,'') IN ('','Frappe','ERPNext','Alvoraa','Alvoraa HR','Alvoraa HRMS'),'change','leave') AS action,
       CONCAT(d.dt,'.app_name') AS setting, COALESCE(s.value,'(not set)') AS current_value,
       IF(BINARY COALESCE(s.value,'') IN ('','Frappe','ERPNext','Alvoraa','Alvoraa HR','Alvoraa HRMS'),'Alvora HRMS','(left alone)') AS proposed
FROM (SELECT 'Website Settings' AS dt UNION ALL SELECT 'System Settings') d
LEFT JOIN tabSingles s ON s.doctype = d.dt AND s.field = 'app_name'
WHERE BINARY COALESCE(s.value,'') <> 'Alvora HRMS'
UNION ALL
SELECT IF(BINARY value IN ('Alvoraa','Alvoraa HR','Alvoraa HRMS','© Alvoraa','Powered by Alvoraa'),'change','leave'),
       CONCAT('Website Settings.',field), value,
       IF(BINARY value IN ('Alvoraa','Alvoraa HR','Alvoraa HRMS','© Alvoraa','Powered by Alvoraa'),
          REPLACE(value,'Alvoraa','Alvora'),'(left alone)')
FROM tabSingles
WHERE doctype = 'Website Settings' AND field IN ('brand_html','copyright','footer_powered','title_prefix')
  AND (value LIKE BINARY '%Alvoraa%' OR value LIKE BINARY '%ALVORAA%')
UNION ALL
SELECT IF(((BINARY e.name IN ('Alvoraa','Alvoraa HR','Alvoraa HRMS') AND @alvoraa_cp = 0)
             OR BINARY e.name IN ('Alvoraa HR Admin'))
          AND NOT EXISTS (SELECT 1 FROM `tabEmail Account` n WHERE n.name = REPLACE(e.name,'Alvoraa','Alvora')),
          'change','leave'),
       'Email Account (From name)', e.name,
       IF(((BINARY e.name IN ('Alvoraa','Alvoraa HR','Alvoraa HRMS') AND @alvoraa_cp = 0)
             OR BINARY e.name IN ('Alvoraa HR Admin'))
          AND NOT EXISTS (SELECT 1 FROM `tabEmail Account` n WHERE n.name = REPLACE(e.name,'Alvoraa','Alvora')),
          REPLACE(e.name,'Alvoraa','Alvora'),'(left alone)')
FROM `tabEmail Account` e WHERE e.name LIKE '%Alvoraa%'
UNION ALL
SELECT 'change', 'Desk Help menu item', item_label, 'hidden'
FROM `tabNavbar Item`
WHERE parent = 'Navbar Settings' AND parentfield = 'help_dropdown'
  AND item_label IN ('Frappe Support') AND hidden = 0
UNION ALL
SELECT IF(item_type = 'Action' AND BINARY COALESCE(action,'') = 'window.location.assign(''/hrms-employee'')'
          AND COALESCE(route,'') = '','ok','change'),
       'Desk menu: Switch to Employee Portal (ALV-152)',
       CONCAT(item_type,' ',COALESCE(route,action,'')),
       IF(item_type = 'Action' AND BINARY COALESCE(action,'') = 'window.location.assign(''/hrms-employee'')'
          AND COALESCE(route,'') = '','(already right)','Action window.location.assign(''/hrms-employee'')')
FROM `tabNavbar Item`
WHERE parent = 'Navbar Settings' AND parentfield = 'settings_dropdown'
  AND BINARY item_label = 'Switch to Employee Portal'
UNION ALL
SELECT IF(TRIM(COALESCE(s.value,'')) = '' OR BINARY s.value = 'attach_files:'
          OR TRIM(s.value) LIKE BINARY '/private/files/%' OR TRIM(s.value) LIKE BINARY '/assets/alvoraa_portal/images/%','change','leave'),
       CONCAT(slot.dt,'.',slot.f,' (patch alvora_splash_lockup)'), COALESCE(s.value,'(not set)'),
       IF(TRIM(COALESCE(s.value,'')) = '' OR BINARY s.value = 'attach_files:'
          OR TRIM(s.value) LIKE BINARY '/private/files/%' OR TRIM(s.value) LIKE BINARY '/assets/alvoraa_portal/images/%',
          slot.want,'(left alone - the tenant set it)')
FROM (SELECT 'Website Settings' AS dt, 'favicon' AS f, '/assets/alvoraa_portal/images/alvoraa-favicon.png' AS want
      UNION ALL SELECT 'Website Settings','app_logo','/assets/alvoraa_portal/images/alvoraa-mark.png'
      UNION ALL SELECT 'Website Settings','banner_image','/assets/alvoraa_portal/images/alvoraa-mark.png'
      UNION ALL SELECT 'Website Settings','splash_image','/assets/alvoraa_portal/images/alvoraa-logo.png'
      UNION ALL SELECT 'Navbar Settings','app_logo','/assets/alvoraa_portal/images/alvoraa-mark.png') slot
LEFT JOIN tabSingles s ON s.doctype = slot.dt AND s.field = slot.f
WHERE BINARY COALESCE(s.value,'') <> slot.want
UNION ALL
SELECT 'report', 'Emails queued, not sent (keep their old text)', COUNT(*), ''
FROM `tabEmail Queue` WHERE status = 'Not Sent';
SQL

for site in $SITES; do
  echo "=== $site"
  CP=0
  if grep -Eq '"alvoraa_control_plane": *(1|true)' "sites/$site/site_config.json" 2>/dev/null; then
    CP=1
    echo "(control plane: only the Email Accounts Surbhi named are renamed here)"
  fi
  grep -o '"tenant_name": *"Alvoraa"' "sites/$site/site_config.json" 2>/dev/null \
    && echo "(report only: site_config tenant_name is \"Alvoraa\" - not changed by the patch)" || true
  bench --site "$site" mariadb -e "SET @alvoraa_cp = $CP; $SQL" 2>&1 || echo "(could not read $site)"
done
