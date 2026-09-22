"""No production deployment file may turn the portal preview page on (SEC-1).

`/hrms-employee-next` exists only where `frappe.conf` carries `portal_preview`.
The page itself checks that flag before it checks anything else, so the flag is
the first of its two locks - and the reason it can be relied on is that nothing
in this repository sets it for production.

This is a repository check, not a site check, so it needs no bench, no database
and no site. It runs the way `check_app_integrity.py` does.

Why it is a script rather than only a test: the bench test of the same rule
(`test_preview_page_034.TestNoProductionConfigTurnsThePreviewOn`) can only reach
`deploy/` when the app is checked out inside the repository. On a bench where
the app is MOUNTED it skips - and a skipped check protects nobody. This one
always runs.

A dev or test deployment file may name the flag. A production one may not.
"""
import io, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY = os.path.join(REPO, "deploy")
FLAG = "portal_preview"

# Only a file whose name plainly marks it as a DEV or TEST one may set it.
#
# "example" is deliberately NOT here. deploy/envs/production.env.example is the
# template somebody copies to make the real production env, so a flag written
# into it reaches production by the shortest possible route. The first version
# of this script allowed "example" and therefore passed a deliberately broken
# production file; that is exactly the failure this check exists to catch.
ALLOWED_MARKERS = ("dev", "test")


def main():
	if not os.path.isdir(DEPLOY):
		print(f"deploy/ not found at {DEPLOY}")
		return 1

	checked, offenders = 0, []
	for folder, _dirs, files in os.walk(DEPLOY):
		for name in sorted(files):
			path = os.path.join(folder, name)
			try:
				text = io.open(path, encoding="utf-8", errors="ignore").read()
			except OSError:
				continue
			checked += 1
			if FLAG not in text:
				continue
			lowered = name.lower()
			if any(marker in lowered for marker in ALLOWED_MARKERS):
				continue
			offenders.append(os.path.relpath(path, REPO))

	if offenders:
		print(f"FAIL - {FLAG} is set in a production deployment file:")
		for path in offenders:
			print(f"  {path}")
		print()
		print("The preview page would then exist on production. It must not (SEC-1).")
		return 1

	print(f"preview flag: {checked} deployment files checked")
	print(f"OK - no production file sets {FLAG}")
	return 0


if __name__ == "__main__":
	sys.exit(main())
