#!/usr/bin/env bash
# Copy the bench-level files the image carries into the sites volume.
#
#   scripts/refresh_bench_files.sh <image> <sites volume>
#   e.g. scripts/refresh_bench_files.sh ghcr.io/.../alvoraa-app:dev-d158670 devstack_sites
#
# Why this exists. The bench's sites/ folder is a Docker volume, so it survives
# every image swap - that is the point of it, the tenants' databases-of-files
# live there. But three things in sites/ belong to the IMAGE, not to the data:
#
#   apps.txt     which apps are on the bench. `bench install-app crm` refuses
#                with "App not in apps.txt" while the volume's copy is stale.
#   apps.json    the same list with versions, for `bench version`.
#   assets/      every app's built JS and CSS and the manifest (assets.json)
#                that names the current bundle hashes. nginx serves /assets/
#                straight from the volume.
#
# Nothing copied them across until 23 Sep 2026 (ALV-112). Dev was serving the
# JS/CSS built on 27 Aug, production the build of 19 Aug, while the images held
# builds a month newer. Pages looked right because the manifest and the bundles
# were old TOGETHER. And a new app had no assets folder at all - /crm was blank.
#
# Order matters: bundles first, the manifest last. A page served mid-copy names
# only files that already exist. Old bundles are left in place for the same
# reason; only the folder of an app that is no longer on the bench is removed.
#
# Safe to run twice. Refuses a volume that does not look like a sites volume,
# because `docker run -v name:/vol` silently CREATES an empty volume for a
# mistyped name.
set -euo pipefail

IMAGE="${1:?usage: refresh_bench_files.sh <image> <sites volume>}"
VOLUME="${2:?usage: refresh_bench_files.sh <image> <sites volume>}"

# As root inside the container: a fresh volume is root-owned and the image runs
# as frappe (uid 1000), so an unprivileged copy fails on the first file. `-p`
# and `-a` keep the image's ownership (frappe:frappe) on everything copied, and
# a directory this script itself creates is handed to frappe below.
docker run --rm --user 0:0 -v "${VOLUME}:/vol" --entrypoint bash "$IMAGE" -c '
  set -euo pipefail
  src=/home/frappe/frappe-bench/sites
  if [ ! -f /vol/common_site_config.json ]; then
    echo "refresh_bench_files: /vol has no common_site_config.json - not a sites volume, refusing" >&2
    exit 1
  fi

  cp -p "$src/apps.txt" /vol/.apps.txt.new && mv -f /vol/.apps.txt.new /vol/apps.txt
  if [ -f "$src/apps.json" ]; then
    cp -p "$src/apps.json" /vol/.apps.json.new && mv -f /vol/.apps.json.new /vol/apps.json
  fi

  mkdir -p /vol/assets && chown 1000:1000 /vol/assets
  cd "$src/assets"
  for entry in *; do
    case "$entry" in assets.json|assets-rtl.json) continue ;; esac
    cp -a "$entry" /vol/assets/
  done
  cp -p assets.json /vol/assets/.assets.json.new && mv -f /vol/assets/.assets.json.new /vol/assets/assets.json
  [ -f assets-rtl.json ] && cp -p assets-rtl.json /vol/assets/assets-rtl.json

  for dir in /vol/assets/*/; do
    name=$(basename "$dir")
    case "$name" in css|js|locale) continue ;; esac
    if ! grep -qx "$name" /vol/apps.txt && [ ! -d "$src/assets/$name" ]; then
      echo "refresh_bench_files: removing assets of an app no longer on the bench: $name"
      rm -rf "$dir"
    fi
  done

  echo "refresh_bench_files: apps.txt = $(tr "\n" " " < /vol/apps.txt)"
  echo "refresh_bench_files: assets manifest dated $(stat -c %y /vol/assets/assets.json | cut -d. -f1)"
'
