#!/usr/bin/env bash
#
# Does this nginx config actually PARSE? Run it before anything restarts nginx.
#
# Why this exists (slice 018)
# ---------------------------
# One nginx container serves production alvoraa.co AND dev.alvoraa.co, with its
# config bind-mounted from deploy/nginx.conf. The deploy restarts that container.
# A config nginx cannot read means nginx does not come back, and EVERY site -
# production included - stays down until a human logs in and fixes it.
#
# So: test the exact file first, in a throwaway container, and stop the deploy if
# it fails. A refused deploy costs minutes. A refused nginx costs an outage.
#
# What it checks, and what it does not
# ------------------------------------
# It checks that nginx accepts the file: syntax, directives in legal places,
# modules present, and - because nginx loads certificates at this point - that
# every ssl_certificate path really exists in the certificate directory. A typo
# in a certificate path is exactly the kind of change that lands here.
#
# It does NOT check that the backends are reachable. That is nginx's own job when
# it starts and the deploy's smoke test afterwards. Nor does it check WHAT the
# config says - scripts/check_nginx_conf.py does that in CI, as a text check.
#
# How it stays independent of the running stack
# ---------------------------------------------
# nginx resolves the host names in `upstream { server NAME:port; }` while it is
# loading the config, so a plain `nginx -t` with no network fails with "host not
# found in upstream" - a failure about the network, not about the file. Borrowing
# the running nginx's network namespace would fix that, but then the check could
# not run when nginx is down, which is precisely when it is most needed.
#
# Instead every host name in the file is read out of the file itself and given a
# stub address in the throwaway container's /etc/hosts. Resolution succeeds, the
# parse is honest, and the check needs no network and no running container. A new
# upstream added to the config is picked up automatically, so this does not become
# a list someone forgets to update.
#
# Usage:
#   scripts/check_nginx_parses.sh <nginx.conf> [cert-dir]
#
#   cert-dir defaults to /etc/letsencrypt (TLS_CERT_DIR on the server), mounted
#   READ-ONLY at /etc/nginx/ssl, the same place the real nginx service mounts it.
#
#   NGINX_TEST_IMAGE overrides the image. The default, nginx:alpine, is the same
#   tag docker-compose.app.yml runs - so if that tag ever stops accepting the
#   config, this says so BEFORE the deploy recreates nginx with it.
#
# Exit 0 = the config parses. Exit non-zero = do not restart nginx.

set -euo pipefail

CONF=${1:?usage: check_nginx_parses.sh <nginx.conf> [cert-dir]}
CERT_DIR=${2:-/etc/letsencrypt}
IMAGE=${NGINX_TEST_IMAGE:-nginx:alpine}

[ -f "$CONF" ] || { echo "FAIL  no such config file: $CONF"; exit 1; }
[ -d "$CERT_DIR" ] || { echo "FAIL  no such certificate directory: $CERT_DIR"; exit 1; }

# Absolute paths: `docker run -v` needs them.
CONF=$(cd "$(dirname "$CONF")" && pwd)/$(basename "$CONF")
CERT_DIR=$(cd "$CERT_DIR" && pwd)
CONF_BYTES=$(wc -c < "$CONF" | tr -d ' ')

# Mount paths, which are not always the same as the paths above.
#
# The deploy runs this on Linux, where they are identical. A developer running it
# by hand on Windows goes through Git Bash, which rewrites anything that looks
# like a path inside a `-v` argument and turns the mount into nonsense - docker
# then accepts it as an anonymous volume and mounts NOTHING. nginx happily tests
# its own built-in config and reports success. That false pass is worse than no
# check at all; it cost an hour here before the mount was verified.
#
# So: convert to a form docker on Windows understands, and switch the rewriting
# off for the docker call. On Linux both lines are no-ops.
MOUNT_CONF=$CONF
MOUNT_CERT_DIR=$CERT_DIR
case "$(uname -s)" in
  MINGW* | MSYS* | CYGWIN*)
    MOUNT_CONF=$(cygpath -m "$CONF")
    MOUNT_CERT_DIR=$(cygpath -m "$CERT_DIR")
    export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
    ;;
esac

# Every host name the config asks nginx to resolve. Comments are stripped first.
# Two shapes matter:
#   `server compose-backend-1:8000;`   inside an upstream block
#   `proxy_pass http://some-host:8000` with a literal host instead of an upstream
# Names with an underscore are skipped: a real host name cannot contain one, so
# those are upstream block names (frappe_http), which nginx never resolves.
hosts=$(
  sed 's/#.*//' "$CONF" | awk '
    /^[[:space:]]*server[[:space:]]+[^;{]+;/ {
      name = $2; sub(/;$/, "", name); sub(/:[0-9]+$/, "", name)
      if (name ~ /^[A-Za-z][A-Za-z0-9.-]*$/) print name
    }
    /proxy_pass[[:space:]]+https?:\/\// {
      if (match($0, /:\/\/[A-Za-z][A-Za-z0-9._-]*/)) {
        name = substr($0, RSTART + 3, RLENGTH - 3)
        if (name !~ /_/) print name
      }
    }
  ' | sort -u
)

args=()
for host in $hosts; do
  args+=(--add-host "$host:127.0.0.1")
done

echo "Testing  $CONF"
echo "Certs    $CERT_DIR (read-only)"
echo "Image    $IMAGE"
echo "Stubbed  ${hosts:-none}" | tr '\n' ' '; echo

# --network none: the parse must not depend on any network being up.
# --entrypoint sh: two reasons.
#   1. It skips the image's start-up scripts. One of them runs `sed -i` over
#      /etc/nginx/conf.d to add ipv6only=off - it tries to EDIT the file under
#      test. The read-only mount stops it, but a check has no business writing to
#      the repo's config, and skipping the scripts also drops eight lines of noise.
#   2. It lets the container CONFIRM the config really mounted before testing it.
#      A silently missing mount leaves the image's own tiny default.conf in place,
#      which always parses - a pass that means nothing. The byte count settles it.
# Both mounts are read-only, and --rm removes the container whatever happens.
if docker run --rm --network none "${args[@]}" \
     -v "$MOUNT_CONF:/etc/nginx/conf.d/default.conf:ro" \
     -v "$MOUNT_CERT_DIR:/etc/nginx/ssl:ro" \
     --entrypoint sh "$IMAGE" -c '
       seen=$(wc -c < /etc/nginx/conf.d/default.conf | tr -d " ")
       if [ "$seen" != "'"$CONF_BYTES"'" ]; then
         echo "the config under test did not mount: container sees $seen bytes," \
              "host file is '"$CONF_BYTES"' bytes"
         exit 3
       fi
       [ -d /etc/nginx/ssl/live ] || echo "warning: no live/ under the certificate directory"
       exec nginx -t' 2>&1
then
  echo "OK    nginx accepts this config - safe to restart nginx with it"
  exit 0
fi

echo "FAIL  nginx REFUSES this config, or the check could not run. Restarting"
echo "      nginx with it would take every site down, production included."
echo "      Fix deploy/nginx.conf first."
exit 1
