#!/usr/bin/env bash
# Replace symlinks under sites/assets with real files - at EVERY depth.
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
# ── Why this now recurses (6 Oct 2026, ALV-112) ──────────────────────────────
#
# Until today this walked `-maxdepth 1` only, so it fixed the top-level links and
# left every NESTED one dangling. One of those matters a great deal:
#
#     apps/frappe/frappe/public/node_modules -> apps/frappe/node_modules
#
# `cp -r` copies a symlink as a symlink, so materialising `assets/frappe` turned the
# directory into real files and faithfully reproduced that dangling link inside it.
# Most of the desk kept working, because its CSS and JS are real files under
# `public/`. But anything served straight out of node_modules 404s - and the one
# people hit is the code editor:
#
#     /assets/frappe/node_modules/ace-builds/src-min-noconflict/ace.js
#
# Frappe's Code field loads Ace from there (`code.js`), then calls
# `window.ace.config.set(...)`. With the file missing the browser shows
# "Cannot read properties of undefined (reading 'config')" and the field renders
# as a label with NO EDITABLE BOX. Found on dtc.alvoraa.co on 6 Oct 2026, where it
# made the Server Script form unusable. It affects every Code field, not that one
# screen.
#
# ── The cost, stated rather than hidden ──────────────────────────────────────
#
# `node_modules` is about 324 MB. Dereferencing it makes the sites volume that much
# bigger, and the copy takes a little time on each deploy. That is the price of
# nginx being able to serve what it is asked for without reaching outside its own
# mount, and it is what upstream frappe_docker does too. ALV-171 is separately
# trying to slim the IMAGE; this is the volume, and the two do not fight.
#
# Run this after ANY `bench build` or asset refresh that writes into the sites
# volume. The deploy workflow does it automatically from 6 Oct 2026.
#
#   docker exec compose-backend-1 bash /path/materialise_assets.sh
#
# Idempotent: with no dangling symlinks left it reports 0 and changes nothing.
set -euo pipefail

ASSETS="${1:-/home/frappe/frappe-bench/sites/assets}"
cd "$ASSETS" || { echo "no assets dir at $ASSETS"; exit 1; }

converted=0
skipped=0

# Top level first, then whatever that uncovers. A top-level link becomes a real
# directory, and the nested links it was hiding only become findable afterwards -
# so a single pass would miss them. Two passes is enough for the shape Frappe
# builds, and the loop below stops as soon as a pass changes nothing.
for pass in 1 2 3; do
	pass_converted=0

	# -type l finds symlinks at any depth. Sorted so the output reads the same way
	# twice, which matters when comparing two deploys' logs.
	while IFS= read -r link; do
		[ -n "$link" ] || continue
		target="$(readlink -f "$link" 2>/dev/null || true)"

		if [ -n "$target" ] && [ -d "$target" ]; then
			rm -rf "$link"
			# -L dereferences links INSIDE the tree as well, so a nested
			# node_modules does not come across as another dangling link.
			cp -rL "$target" "$link"
			echo "materialised ${link#./}"
			converted=$((converted + 1))
			pass_converted=$((pass_converted + 1))
		elif [ -n "$target" ] && [ -f "$target" ]; then
			rm -f "$link"
			cp -L "$target" "$link"
			echo "materialised file ${link#./}"
			converted=$((converted + 1))
			pass_converted=$((pass_converted + 1))
		else
			# A link pointing at nothing reachable. Say so rather than deleting it:
			# an empty path where a file is expected is a 404 either way, and the
			# name is the clue to what is missing.
			echo "WARNING: ${link#./} points at '${target:-nothing}', which is not reachable - left alone"
			skipped=$((skipped + 1))
		fi
	done < <(find . -type l | sort)

	[ "$pass_converted" -eq 0 ] && break
done

remaining=$(find . -type l | wc -l)
echo "converted=${converted} unreachable=${skipped} remaining_symlinks=${remaining}"

# The check that would have caught this in the first place. Frappe's Code field is
# unusable without it, and nothing else in the pipeline looks at node_modules.
ACE="frappe/node_modules/ace-builds/src-min-noconflict/ace.js"
if [ -d "frappe" ] && [ ! -f "$ACE" ]; then
	echo "::warning::$ACE is missing - every Code field will render without an editor"
fi
