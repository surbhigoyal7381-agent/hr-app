#!/usr/bin/env bash
# ALV-174 dry-run: what the email_brand patch WOULD change on each site.
#
# READ-ONLY. Plain SELECTs through `bench mariadb`, the same shape as
# scripts/brand_text_dry_run.sh (ALV-149/D5); it writes nothing and needs
# none of this slice's Python on the server, so it runs against the image
# that is there today. Surbhi reads its output BEFORE the patch runs there.
#
# The rules must match alvoraa_portal/email_brand.py exactly -
# alvoraa_portal/alvoraa_portal/tests/test_email_brand_174.py has a test that
# runs this SQL on a site with near-miss values and fails if its "change"
# rows differ from what the patch would actually do.
#
# `tenant_name` is not in the database - it is site_config.json, like
# tenant_context.get_branding() reads it - so this script pulls it from that
# file per site, the same way it already checks for alvoraa_control_plane.
#
# Run it inside the backend container, from the repo on your machine:
#
#   docker exec -i <backend-container> bash -s < scripts/email_brand_dry_run.sh
#   docker exec -i <backend-container> bash -s -- dtc.alvoraa.co < scripts/email_brand_dry_run.sh
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
-- @tenant_footer and @mark/@logo are set per site by the shell loop below.
-- Every text comparison is BINARY, matching the Python (which does not fold
-- case or ignore trailing space either).
SELECT IF(BINARY COALESCE(s.value,'0') IN ('0',''),'change','leave'),
       'System Settings.disable_standard_email_footer', COALESCE(s.value,'0'),
       IF(BINARY COALESCE(s.value,'0') IN ('0',''),'1','(already off)')
FROM (SELECT 1) x
LEFT JOIN tabSingles s ON s.doctype = 'System Settings' AND s.field = 'disable_standard_email_footer'
UNION ALL
SELECT IF(BINARY COALESCE(s.value,'') = @tenant_footer,'ok',
          IF(TRIM(COALESCE(s.value,'')) = '' OR RIGHT(s.value, LENGTH('Powered by AllAboutHR')) = 'Powered by AllAboutHR',
             'change','leave')),
       'System Settings.email_footer_address', COALESCE(s.value,'(not set)'),
       IF(TRIM(COALESCE(s.value,'')) = '' OR RIGHT(COALESCE(s.value,''), LENGTH('Powered by AllAboutHR')) = 'Powered by AllAboutHR'
             OR BINARY COALESCE(s.value,'') = @tenant_footer,
          @tenant_footer,'(left alone - the tenant set it)')
FROM (SELECT 1) x
LEFT JOIN tabSingles s ON s.doctype = 'System Settings' AND s.field = 'email_footer_address'
WHERE BINARY COALESCE(s.value,'') <> @tenant_footer
UNION ALL
SELECT IF(TRIM(COALESCE(e.brand_logo,'')) = '' OR RIGHT(e.brand_logo, LENGTH(@mark)) = @mark
             OR RIGHT(e.brand_logo, LENGTH(@logo)) = @logo,
          'change','leave'),
       CONCAT('Email Account.brand_logo (',e.name,')'), COALESCE(e.brand_logo,'(not set)'),
       IF(TRIM(COALESCE(e.brand_logo,'')) = '' OR RIGHT(e.brand_logo, LENGTH(@mark)) = @mark
             OR RIGHT(e.brand_logo, LENGTH(@logo)) = @logo,
          @wanted_logo,'(left alone - the tenant set it)')
FROM `tabEmail Account` e
WHERE e.enable_outgoing = 1 AND COALESCE(e.brand_logo,'') <> @wanted_logo;
SQL

for site in $SITES; do
  echo "=== $site"
  TENANT_NAME=$(grep -o '"tenant_name" *: *"[^"]*"' "sites/$site/site_config.json" 2>/dev/null \
    | sed -E 's/.*: *"([^"]*)"/\1/' | head -1) || true
  TENANT_NAME=${TENANT_NAME:-Alvora}
  # SQL-escape a single quote the way the site's own name might contain one.
  TENANT_NAME_ESC=${TENANT_NAME//\'/\'\'}
  TENANT_FOOTER="${TENANT_NAME_ESC}\nPowered by AllAboutHR"
  SITE_URL=$(bench --site "$site" execute frappe.utils.get_url 2>/dev/null | tr -d "'\"" || echo "")
  MARK="/assets/alvoraa_portal/images/alvoraa-mark.png"
  LOGO="/assets/alvoraa_portal/images/alvoraa-logo.png"
  WANTED_LOGO="${SITE_URL}${LOGO}"
  bench --site "$site" mariadb -e "
    SET @tenant_footer = '${TENANT_FOOTER}';
    SET @mark = '${MARK}';
    SET @logo = '${LOGO}';
    SET @wanted_logo = '${WANTED_LOGO}';
    $SQL" 2>&1 || echo "(could not read $site)"
done
