#!/usr/bin/env bash
#
# Add a hostname to the alvoraa.co certificate.
#
#   deploy/add_tenant_cert.sh demo.alvoraa.co [--dry-run]
#
# Provisioning a tenant creates a Frappe site, but nothing gives that hostname a
# certificate - so a new tenant comes up on HTTP and fails on HTTPS. This closes
# that gap.
#
# It uses HTTP-01 (webroot), the mechanism already in place. That means one
# certificate carrying every tenant name, reissued on each addition.
#
# LIMITS, because they decide when this stops being good enough:
#   * a Let's Encrypt certificate holds at most 100 names
#   * "duplicate certificate" is capped at 5 per week, so repeated additions in
#     one week can lock you out temporarily - use --dry-run while testing
#   * every tenant needs an nginx-served hostname BEFORE issuance, so the
#     challenge can be answered
#
# The durable answer is a wildcard certificate via DNS-01, which needs no work
# per tenant. That requires API access to DNS. Until then, this.

set -euo pipefail

CERT_NAME="alvoraa.co"
WEBROOT="/opt/hr-app/acme"
NGINX_CONTAINER="compose-nginx-1"

# Hosts to drop from the certificate when it is next reissued. Retired sites
# would otherwise be renewed forever, and a name that no longer resolves makes
# the whole renewal fail.
RETIRED="minda.alvoraa.co kinexus.alvoraa.co"

NEW_HOST="${1:?usage: add_tenant_cert.sh <hostname> [--dry-run]}"
DRY_RUN="${2:-}"

command -v certbot >/dev/null || { echo "certbot not installed" >&2; exit 1; }

# Current names on the certificate
CURRENT="$(certbot certificates --cert-name "$CERT_NAME" 2>/dev/null \
  | awk -F': *' '/Domains:/ {print $2; exit}')"
[ -n "$CURRENT" ] || { echo "no certificate named $CERT_NAME" >&2; exit 1; }

echo "current names : $CURRENT"
echo "adding        : $NEW_HOST"

# Build the new list: existing, minus retired, plus the new host, de-duplicated.
KEEP=""
for d in $CURRENT; do
  skip=""
  for r in $RETIRED; do [ "$d" = "$r" ] && skip=1; done
  [ -n "$skip" ] && { echo "dropping      : $d (retired)"; continue; }
  KEEP="$KEEP $d"
done

for d in $KEEP; do
  if [ "$d" = "$NEW_HOST" ]; then
    echo "$NEW_HOST is already on the certificate - nothing to do"
    exit 0
  fi
done

ARGS=""
for d in $KEEP $NEW_HOST; do ARGS="$ARGS -d $d"; done
echo "requesting    :$ARGS"

# The hostname must answer HTTP before issuance, or the challenge cannot be
# served. nginx serves /.well-known/acme-challenge/ from $WEBROOT for every host,
# so this works even before the Frappe site exists.
# nginx serves this location with `root $WEBROOT`, so the URI path is appended:
# the file must sit at $WEBROOT/.well-known/acme-challenge/, not at $WEBROOT.
CHALLENGE_DIR="$WEBROOT/.well-known/acme-challenge"
mkdir -p "$CHALLENGE_DIR"
probe="$(mktemp -p "$CHALLENGE_DIR" probe-XXXXXX)"
trap 'rm -f "$probe"' EXIT
echo ok > "$probe"
# mktemp creates 0600 and nginx runs as another user - without this it 403s.
chmod 644 "$probe"
if ! curl -fsS -m 10 "http://${NEW_HOST}/.well-known/acme-challenge/$(basename "$probe")" | grep -q ok; then
  echo "WARNING: http://${NEW_HOST}/.well-known/acme-challenge/ did not answer." >&2
  echo "         Check DNS resolves and nginx serves this host, or issuance will fail." >&2
  [ "$DRY_RUN" = "--dry-run" ] || { echo "refusing to burn a rate-limit slot" >&2; exit 1; }
fi
rm -f "$probe"; trap - EXIT

# shellcheck disable=SC2086
certbot certonly --webroot -w "$WEBROOT" \
  --cert-name "$CERT_NAME" --expand --non-interactive --agree-tos \
  --keep-until-expiring \
  $ARGS ${DRY_RUN:+--dry-run}

if [ "$DRY_RUN" = "--dry-run" ]; then
  echo "dry run only - no certificate issued, nginx untouched"
  exit 0
fi

# Reload rather than restart: a restart would drop the dev network if nginx were
# recreated, and reload is instant. See DEPLOYMENT_RUNBOOK.md 5.8.
docker exec "$NGINX_CONTAINER" nginx -t
docker exec "$NGINX_CONTAINER" nginx -s reload
echo "certificate updated and nginx reloaded"
