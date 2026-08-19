#!/usr/bin/env bash
# Replace symlinks under sites/assets with real files.
#
# `bench build` links each app's public directory:
#     sites/assets/frappe -> /home/frappe/frappe-bench/apps/frappe/frappe/public
#
# That is fine for the backend container, which has /apps. It is NOT fine for nginx,
# which mounts only the sites volume and has no /apps at all - so it follows a dangling
# link and returns 404 for every CSS and JS file. The visible symptom is a portal with no
# styling and panels stuck on "Loading...", which looks like an application fault and is
# not one.
#
# Run this after ANY `bench build` that writes into the sites volume.
#
#   docker exec compose-backend-1 bash /path/materialise_assets.sh
#
# Idempotent: with no symlinks left it reports 0 and changes nothing.
set -euo pipefail

ASSETS="${1:-/home/frappe/frappe-bench/sites/assets}"
cd "$ASSETS" || { echo "no assets dir at $ASSETS"; exit 1; }

converted=0
for link in $(find . -maxdepth 1 -type l); do
    target="$(readlink -f "$link")"
    if [ -d "$target" ]; then
        rm -f "$link"
        cp -r "$target" "$link"
        echo "materialised ${link#./}"
        converted=$((converted + 1))
    else
        echo "WARNING: ${link#./} points at ${target}, which is not a directory - left alone"
    fi
done

echo "converted=${converted} remaining_symlinks=$(find . -maxdepth 1 -type l | wc -l)"
