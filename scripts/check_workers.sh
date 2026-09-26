#!/usr/bin/env bash
#
# Are the background workers actually working? Read-only. Run it anywhere.
#
# Why this exists (slice 026)
# ---------------------------
# On 2026-09-10 at 06:32 server time both production workers stopped, and nobody
# found out for nine days. 700 jobs piled up on the `default` queue - every
# scheduled job alvoraa.co runs. Nothing was broken on any screen, so nothing
# told anyone. The whole chain is written out in
# deploy/compose/docker-compose.app.yml above the worker services; the short
# version is that the disk filled, redis refused writes, rq quit, docker's
# restart then failed for want of disk, and docker could not even record that it
# had failed - so `docker ps` said "Up 12 days" for nine days while `docker top`
# on the same container said "container is not running".
#
# So this script never trusts "Up". It asks four separate questions, and each one
# would have caught 10 Sep on its own:
#
#   1. Does the container's state say running, and can it still run a process
#      (`docker top`)? Those two disagreeing IS the 10 Sep failure.
#   2. Does redis hold a live rq registration for every queue the workers are
#      configured to serve, with a heartbeat inside the last few minutes? The
#      queues are read off the containers' own `bench worker --queue` command, so
#      adding a queue to the compose file does not leave a list here to forget.
#   3. Is a queue deep with no live worker for it? That is the visible symptom.
#   4. Is there disk headroom left? That is the cause, and it is the one thing
#      that breaks everything else, including the recovery.
#
# What it does NOT do
# -------------------
# It never restarts anything. It reports and exits non-zero. Restarting a worker
# mid-job has consequences - a half-run payroll job is worse than a stopped one -
# and this repository's rule is that scripts and agents advise while a human
# decides. See docs/slices/026-worker-health/07-devops-inputs.md.
#
# It also cannot prove the scheduler is firing cron jobs. `bench doctor` is the
# closest cheap thing to that, and the deploy runs it alongside this.
#
# Usage:
#   scripts/check_workers.sh <compose-project> [max-heartbeat-age-seconds]
#
#     compose-project   `compose` for production, `devstack` for dev. Those are
#                       the real project names on the server - see the `plan` job
#                       in .github/workflows/deploy.yml.
#     max-age           default 600. rq's own worker key expires after about 420
#                       seconds, so much below that is the same check with less
#                       warning.
#
# Exit 0 = the workers are doing their job. Exit 1 = a human needs to look.

set -uo pipefail       # deliberately NOT -e: collect every problem, not just the first

PROJECT=${1:?usage: check_workers.sh <compose-project> [max-heartbeat-age-seconds]}
MAX_AGE=${2:-600}
DISK_FAIL_GB=${DISK_FAIL_GB:-20}
DISK_WARN_GB=${DISK_WARN_GB:-40}

problems=0
fail() { echo "FAIL  $*"; problems=$((problems + 1)); }
warn() { echo "WARN  $*"; }
ok()   { echo "ok    $*"; }

echo "Checking compose project: $PROJECT"
echo

# -- 1. The containers, and whether "Up" is telling the truth ----------------
#
# Compose labels are the authoritative source for which container belongs to
# which project and service - the same reason the deploy's `plan` job reads them.
workers=()
while IFS= read -r row; do
  [ -n "$row" ] && workers+=("$row")
done < <(
  docker ps -a \
    --filter "label=com.docker.compose.project=$PROJECT" \
    --format '{{.Names}}	{{.Label "com.docker.compose.service"}}' \
  | awk -F'\t' '$2 ~ /^(worker|scheduler)/ {print $1"\t"$2}' | sort
)

if [ "${#workers[@]}" -eq 0 ]; then
  fail "no worker or scheduler containers found in project '$PROJECT'."
  echo "      Either the project name is wrong or the stack is not up."
  exit 1
fi

expected_queues=""
for row in "${workers[@]}"; do
  name=${row%%$'\t'*}
  svc=${row##*$'\t'}

  state=$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null) || state="missing"
  health=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null) || health="none"

  if [ "$state" != "running" ]; then
    fail "$name is '$state', not running."
    continue
  fi

  # The 10 Sep test. `docker top` asks containerd for the container's processes.
  # A container whose task is gone but whose saved state still says Running
  # answers "container is not running" here while `docker ps` says "Up".
  if ! top_out=$(docker top "$name" 2>&1); then
    fail "$name: docker says Up, but it has no processes -> ${top_out##*: }"
    echo "      This is the 2026-09-10 failure exactly. The container is a shell."
    echo "      It has to be recreated, not restarted. Ask before doing it."
    continue
  fi

  case "$health" in
    unhealthy) fail "$name is marked unhealthy by its own healthcheck." ;;
    starting)  warn "$name healthcheck is still in its start period." ;;
    none)      warn "$name has no healthcheck. Add one - see docker-compose.app.yml." ;;
    healthy)   : ;;
  esac

  # Which queues is this container SUPPOSED to serve? Read it off its own command
  # rather than keeping a list here that drifts from the compose file.
  cmd=$(docker inspect -f '{{json .Config.Cmd}}' "$name" 2>/dev/null)
  qs=$(printf '%s' "$cmd" | sed -n 's/.*"--queue","\([^"]*\)".*/\1/p' | tr ',' ' ')
  if [ -n "$qs" ]; then
    expected_queues="$expected_queues $qs"
    ok "$name ($svc) running, health=$health, serves: $qs"
  else
    ok "$name ($svc) running, health=$health"
  fi
done
echo

# -- 2. Does redis hold a live rq registration for every expected queue? -----
#
# A worker process can be alive and still not be working: on 10 Sep redis was
# refusing writes, so no heartbeat could be recorded. rq puts every live worker
# in the set `rq:workers` and lets the per-worker hash expire, so a worker that
# stops writing disappears from here within about seven minutes.
REDIS_C="${PROJECT}-redis-1"
if ! docker inspect "$REDIS_C" >/dev/null 2>&1; then
  REDIS_C=$(docker ps --filter "label=com.docker.compose.project=$PROJECT" \
                      --filter "label=com.docker.compose.service=redis" \
                      --format '{{.Names}}' | head -1)
fi

if [ -z "${REDIS_C:-}" ]; then
  fail "cannot find the redis container for project '$PROJECT' - queue state unknown."
else
  # The queue lives in whichever redis database the app was told to use.
  # Production uses /1; the dev stack's env file has no suffix at all, which means
  # /0 - the same database as the cache. Read it rather than assuming, and never
  # hardcode 1.
  BACKEND_C=$(docker ps --filter "label=com.docker.compose.project=$PROJECT" \
                        --filter "label=com.docker.compose.service=backend" \
                        --format '{{.Names}}' | head -1)
  QUEUE_URL=$(docker exec "$BACKEND_C" printenv REDIS_QUEUE 2>/dev/null | tr -d '\r')
  DB=$(printf '%s' "$QUEUE_URL" | sed -n 's|.*:[0-9][0-9]*/\([0-9][0-9]*\)$|\1|p')
  DB=${DB:-0}
  echo "redis: $REDIS_C, queue database $DB (from REDIS_QUEUE=${QUEUE_URL:-unset})"

  now=$(date -u +%s)
  live_queues=""
  while read -r wkey; do
    [ -n "$wkey" ] || continue
    hb=$(docker exec "$REDIS_C" redis-cli -n "$DB" hget "$wkey" last_heartbeat 2>/dev/null | tr -d '\r')
    qn=$(docker exec "$REDIS_C" redis-cli -n "$DB" hget "$wkey" queues 2>/dev/null | tr -d '\r')
    # An empty hash means the key expired: the worker stopped writing. rq leaves
    # the name in the set, and that stale entry is exactly what must not be
    # mistaken for a living worker.
    if [ -z "$hb" ]; then
      warn "stale registration $wkey - its heartbeat key has expired. Ignoring it."
      continue
    fi
    # Strip the fraction; `date -d` is happy without it everywhere.
    hb_secs=$(date -u -d "${hb%.*}Z" +%s 2>/dev/null) || hb_secs=0
    if [ "${hb_secs:-0}" -eq 0 ]; then
      warn "could not read the heartbeat time '$hb' on $wkey."
      continue
    fi
    age=$((now - hb_secs))
    if [ "$age" -gt "$MAX_AGE" ]; then
      fail "$wkey last reported ${age}s ago (limit ${MAX_AGE}s) - it is not working."
      continue
    fi
    # rq namespaces queues as `home-frappe-frappe-bench:default`. Keep the tail.
    for q in ${qn//,/ }; do
      live_queues="$live_queues ${q##*:}"
    done
    ok "${wkey#rq:worker:} heartbeat ${age}s ago, serving: ${qn//,/ }"
  done < <(docker exec "$REDIS_C" redis-cli -n "$DB" smembers rq:workers 2>/dev/null | tr -d '\r')
  echo

  # -- 3. Every queue the compose file staffs must have a live worker, and a
  #       queue nobody is draining must not be allowed to grow quietly.
  for q in $(printf '%s\n' $expected_queues | sort -u); do
    depth=$(docker exec "$REDIS_C" redis-cli -n "$DB" llen \
              "rq:queue:home-frappe-frappe-bench:$q" 2>/dev/null | tr -d '\r')
    depth=${depth:-0}
    if printf '%s\n' $live_queues | grep -qx "$q"; then
      if [ "$depth" -gt 500 ]; then
        warn "queue '$q' has $depth jobs waiting. A worker is alive, but it is behind."
      else
        ok "queue '$q': $depth waiting, a live worker is on it."
      fi
    else
      fail "queue '$q' has NO live worker. $depth jobs are waiting and nothing will run them."
    fi
  done
fi
echo

# -- 4. Disk headroom - the actual cause of 2026-09-10 ----------------------
#
# Below about 20 GB a deploy cannot pull an image (~11 GB), redis cannot write its
# append-only file, and - the part that turned an incident into nine days - docker
# cannot mount a root filesystem to RESTART anything. The recovery needs exactly
# the disk that the failure just consumed.
avail_gb=$(df -BG --output=avail / 2>/dev/null | tail -1 | tr -dc '0-9')
avail_gb=${avail_gb:-0}
if [ "$avail_gb" -lt "$DISK_FAIL_GB" ]; then
  fail "only ${avail_gb} GB free on /. Below ${DISK_FAIL_GB} GB nothing can restart."
  echo "      This is what happened on 2026-09-10. Largest consumers:"
  docker system df 2>/dev/null | sed 's/^/      /'
elif [ "$avail_gb" -lt "$DISK_WARN_GB" ]; then
  warn "${avail_gb} GB free on /. Under ${DISK_WARN_GB} GB - clean up before the next deploy."
else
  ok "${avail_gb} GB free on /."
fi
echo

if [ "$problems" -gt 0 ]; then
  echo "FAILED  $problems problem(s). Background jobs are not running properly on '$PROJECT'."
  echo "        Nothing has been changed. Decide what to restart, then do it by hand."
  exit 1
fi
echo "PASSED  every queue on '$PROJECT' has a live worker, and there is disk headroom."
exit 0
