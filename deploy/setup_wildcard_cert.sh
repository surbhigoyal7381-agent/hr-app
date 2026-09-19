#!/usr/bin/env bash
#
# The durable replacement for add_tenant_cert.sh.
#
#   deploy/setup_wildcard_cert.sh [--dry-run]
#
# add_tenant_cert.sh has to be run BY HAND for every new tenant, because an
# HTTP-01 challenge can only prove a name that already exists. That is a manual
# step in the middle of automated provisioning, and it is the reason
# ppj.dev.alvoraa.co came up with no certificate at all.
#
# A wildcard certificate removes the step entirely: every future tenant is
# already covered on the day it is created. Wildcards require DNS-01, which
# means certbot must be able to write a TXT record.
#
# WHY TWO WILDCARDS AND NOT ONE
# A wildcard covers exactly ONE label. `*.alvoraa.co` matches demo.alvoraa.co
# but NOT ppj.dev.alvoraa.co, which is two labels deep. Production tenants are
# <tenant>.alvoraa.co and dev tenants are <tenant>.dev.alvoraa.co, so both are
# needed. Getting this wrong is the most likely way to do all this work and
# still have no certificate for a dev tenant.
#
# LIMITS THAT GO AWAY
#   * the 100-names-per-certificate ceiling
#   * the 5-duplicate-certificates-per-week cap
#   * needing the hostname to serve HTTP before issuance
#   * a retired tenant breaking renewal for everybody
#
# BEFORE THIS WILL RUN
# DNS for alvoraa.co is on GoDaddy (ns07/ns08.domaincontrol.com), and GoDaddy
# has no official certbot plugin. See docs/slices/008-field-checkin/
# 09-wildcard-certificate.md for the decision this needs. This script assumes
# the Cloudflare route, which is the recommended one.

set -euo pipefail

CERT_NAME="alvoraa-wildcard"
DOMAIN="alvoraa.co"
CREDS="/root/.secrets/cloudflare.ini"
NGINX_CONTAINER="compose-nginx-1"
DRY_RUN="${1:-}"

# Both apex and both wildcard levels. See the note above.
DOMAINS="-d ${DOMAIN} -d *.${DOMAIN} -d *.dev.${DOMAIN}"

echo "== checks =="

command -v certbot >/dev/null || { echo "certbot not installed" >&2; exit 1; }

if ! certbot plugins 2>/dev/null | grep -q dns-cloudflare; then
  cat >&2 <<'MSG'
ERROR: the dns-cloudflare plugin is not installed.

  certbot here is the apt build, so install the matching apt package:

      apt-get update && apt-get install -y python3-certbot-dns-cloudflare

  Do NOT pip-install it alongside an apt certbot: two copies of the plugin API
  is how certbot upgrades start failing silently at renewal time, which is the
  worst moment to find out.
MSG
  exit 1
fi

if [ ! -f "$CREDS" ]; then
  cat >&2 <<MSG
ERROR: no Cloudflare credentials at $CREDS

  Create it with a SCOPED token - never a Global API Key, which can do anything
  to the account:

      mkdir -p /root/.secrets
      cat > $CREDS <<'INI'
      dns_cloudflare_api_token = <token>
      INI
      chmod 600 $CREDS

  The token needs exactly one permission: Zone / DNS / Edit, on ${DOMAIN} only.
MSG
  exit 1
fi

# certbot refuses a world-readable credentials file, and it is right to.
PERMS="$(stat -c '%a' "$CREDS")"
[ "$PERMS" = "600" ] || { echo "ERROR: $CREDS is mode $PERMS, must be 600" >&2; exit 1; }

echo "  certbot        : $(certbot --version 2>&1)"
echo "  dns plugin     : present"
echo "  credentials    : $CREDS (600)"
echo "  requesting     : $DOMAINS"

echo
echo "== issuing =="

# propagation-seconds: Cloudflare is fast, but a TXT record checked too early
# fails the whole order and wastes a rate-limit slot. 30s is the safe default.
# shellcheck disable=SC2086
certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials "$CREDS" \
  --dns-cloudflare-propagation-seconds 30 \
  --cert-name "$CERT_NAME" \
  --non-interactive --agree-tos --keep-until-expiring \
  $DOMAINS ${DRY_RUN:+--dry-run}

if [ "$DRY_RUN" = "--dry-run" ]; then
  echo
  echo "dry run only - nothing issued, nginx untouched."
  echo "Next: run without --dry-run, then point nginx at:"
  echo "  /etc/letsencrypt/live/${CERT_NAME}/fullchain.pem"
  echo "  /etc/letsencrypt/live/${CERT_NAME}/privkey.pem"
  exit 0
fi

cat <<MSG

== issued ==

  /etc/letsencrypt/live/${CERT_NAME}/fullchain.pem
  /etc/letsencrypt/live/${CERT_NAME}/privkey.pem

NOT switched over. nginx still serves the old per-name certificate, on purpose:
swapping the live certificate is a separate, reviewable step, and doing it in
the same run as issuance means a mistake takes the site down with no way back.

To switch:
  1. Point ssl_certificate / ssl_certificate_key in deploy/nginx.conf at the
     paths above.
  2. docker exec ${NGINX_CONTAINER} nginx -t
  3. docker exec ${NGINX_CONTAINER} nginx -s reload
  4. Check a tenant that is NOT on the old certificate, e.g.
     curl -sI https://<something-new>.dev.${DOMAIN}/api/method/ping
  5. Keep the old certificate until that passes. Then let it expire; do not
     delete it by hand.

Renewal is already automated by certbot.timer and needs no change.
MSG
