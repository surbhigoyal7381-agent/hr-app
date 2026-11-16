#!/usr/bin/env bash
#
# Are people being turned away from an event form? Read-only. (Slice 082, OPS-27/38, AC-73.)
#
# An attendee refused at a live event just leaves; nobody hears about it until the
# organiser complains. This counts, for the last 60 minutes:
#
#   1. Our own refusals, from each site's `event_form` log
#      (sites/<site>/logs/event_form.log*, written by alvoraa_portal.event_form):
#      reasons `limit` and `closed` are counted per hashed form route; `invalid`,
#      `banned_field` and `error` are listed but not counted (a typo is not a crowd).
#   2. nginx's own refusals of the save call (HTTP 503 from the `kinexus_api`
#      zone), which never reach our log. Only the stack that runs nginx has them.
#
# It FAILS (exit 1) when one route has THRESHOLD or more counted refusals, or when
# nginx refused the save THRESHOLD or more times. The failed run is the alert.
# The lines it prints carry the site, the route HASH and counts - never a name,
# a phone number, an answer or the route's own text.
#
# It changes nothing on any container.
#
# Usage:
#   scripts/check_event_refusals.sh <compose-project>       compose | devstack
#   EVENT_LOG_FILE=<file> [NGINX_LOG_FILE=<file>] scripts/check_event_refusals.sh test
#       reads the two files instead of the containers (the tests use this).
#       EVENT_LOG_FILE lines start with "<site>:" as `grep -H` would print them.
#   scripts/check_event_refusals.sh --self-test
#       proves 29 refusals pass and 30 fail, for our log and for nginx, and that
#       old lines and uncounted reasons are left out. No docker needed (CI runs it).

set -uo pipefail

if [ "${1:-}" = "--self-test" ]; then
  dir=$(mktemp -d); trap 'rm -rf "$dir"' EXIT
  now=$(date '+%Y-%m-%d %H:%M:%S'); old=$(date -d '-3 hours' '+%Y-%m-%d %H:%M:%S')
  lines() {  # <n> <reason> <stamp>
    for _ in $(seq 1 "$1"); do
      echo "s1/logs/event_form.log:$3,000 INFO event_form refused reason=$2 route=ab12cd34ef56ab78"
    done
  }
  nginx() { for _ in $(seq 1 "$1"); do
    echo '10.0.0.1 - - [13/Nov/2026:10:00:00 +0000] "POST /api/method/alvoraa_portal.event_form.save HTTP/1.1" 503 197 "-" "Mozilla"'
  done; }
  failures=0
  expect() {  # <label> <want-exit>
    EVENT_LOG_FILE="$dir/app" NGINX_LOG_FILE="$dir/nginx" bash "$0" test >/dev/null; got=$?
    if [ "$got" = "$2" ]; then echo "  ok   $1"; else echo "  FAIL $1 (exit $got, wanted $2)"; failures=$((failures + 1)); fi
  }
  { lines 20 limit "$now"; lines 9 closed "$now"; } > "$dir/app"; : > "$dir/nginx"
  expect "29 counted refusals pass" 0
  lines 1 limit "$now" >> "$dir/app"
  expect "30 counted refusals fail" 1
  { lines 29 limit "$now"; lines 5 invalid "$now"; lines 10 limit "$old"; } > "$dir/app"
  expect "typos and lines older than an hour are not counted" 0
  : > "$dir/app"; nginx 29 > "$dir/nginx"
  expect "29 nginx 503s pass" 0
  nginx 1 >> "$dir/nginx"
  expect "30 nginx 503s fail" 1
  echo "check_event_refusals --self-test: $((5 - failures))/5 passed"
  [ "$failures" -eq 0 ]; exit $?
fi

PROJECT=${1:?usage: check_event_refusals.sh <compose-project>}
THRESHOLD=${THRESHOLD:-30}
SAVE_PATH="/api/method/alvoraa_portal.event_form.save"

container() {   # <project> <service> -> first matching container name
  docker ps --filter "label=com.docker.compose.project=$1" \
    --filter "label=com.docker.compose.service=$2" --format '{{.Names}}' | head -n 1
}

# -- 1. our refusals -----------------------------------------------------------
if [ -n "${EVENT_LOG_FILE:-}" ]; then
  since=$(date -d '-60 min' '+%Y-%m-%d %H:%M:%S')
  app_lines=$(cat "$EVENT_LOG_FILE")
else
  backend=$(container "$PROJECT" backend)
  if [ -z "$backend" ]; then
    echo "FAIL  no backend container in project '$PROJECT' - cannot read the event_form log"
    exit 1
  fi
  # The log's own clock is the container's, so the cut-off is taken there too.
  since=$(docker exec "$backend" date -d '-60 min' '+%Y-%m-%d %H:%M:%S')
  app_lines=$(docker exec "$backend" sh -c \
    'cd /home/frappe/frappe-bench/sites && grep -H " refused " */logs/event_form.log* 2>/dev/null' || true)
fi

# "<site>/logs/event_form.log:2026-11-13 10:00:01,123 INFO event_form refused reason=limit route=ab12"
report=$(printf '%s\n' "$app_lines" | awk -v since="$since" -v limit="$THRESHOLD" '
  NF == 0 { next }
  {
    split($1, head, ":"); site = head[1]; sub(/\/logs\/.*/, "", site)
    stamp = substr($0, index($0, ":") + 1, 19)
    if (stamp < since) next
    reason = ""; route = ""
    for (i = 1; i <= NF; i++) {
      if ($i ~ /^reason=/) reason = substr($i, 8)
      if ($i ~ /^route=/)  route  = substr($i, 7)
    }
    key = site " route=" route
    all[key " " reason]++
    if (reason == "limit" || reason == "closed") counted[key]++
  }
  END {
    bad = 0
    for (k in counted) {
      if (counted[k] >= limit) { print "FAIL  " k " counted=" counted[k]; bad = 1 }
      else print "ok    " k " counted=" counted[k]
    }
    for (k in all) print "      " k "=" all[k]
    exit bad
  }')
app_rc=$?

# -- 2. nginx's refusals of the save call ---------------------------------------
nginx_count=0
if [ -n "${NGINX_LOG_FILE:-}" ]; then
  nginx_lines=$(cat "$NGINX_LOG_FILE")
elif [ -z "${EVENT_LOG_FILE:-}" ] && nginx=$(container "$PROJECT" nginx) && [ -n "$nginx" ]; then
  nginx_lines=$(docker logs --since 60m "$nginx" 2>&1 || true)
else
  nginx_lines=""
fi
if [ -n "$nginx_lines" ]; then
  nginx_count=$(printf '%s\n' "$nginx_lines" | grep -F "\"POST $SAVE_PATH" | grep -cE '" 503 ' || true)
fi

echo "Event form refusals, last 60 minutes, project '$PROJECT' (fail at $THRESHOLD):"
[ -n "$report" ] && printf '%s\n' "$report" || echo "ok    no refusals logged"
rc=$app_rc
if [ "${nginx_count:-0}" -ge "$THRESHOLD" ]; then
  echo "FAIL  nginx refused the event-form save $nginx_count times (503, all sites on this nginx)"
  rc=1
else
  echo "ok    nginx refused the event-form save ${nginx_count:-0} times"
fi
exit $rc
