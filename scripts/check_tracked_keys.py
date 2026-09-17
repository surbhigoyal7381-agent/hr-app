"""Key guard: no signing key or app secret file may ever be tracked by git.

Slice 013, OPS-6 / OPS-37 / OPS-71, SEC-23. This repository is public. A signing
key is published the moment it is pushed, whatever CI says afterwards, so this
check runs in two places:

  * in CI (`ci.yml`, lint job) on every push and pull request, with no path filter;
  * by hand in the worktree before every push:  python scripts/check_tracked_keys.py

`.gitignore` already lists the same patterns, but `git add -f` walks straight past
an ignore rule. This reads what git actually tracks (`git ls-files`), so a file
added with `-f` still fails the build.

GitHub's push protection looks for known token patterns. It does not recognise a
binary Android keystore, which is why this list is about file NAMES.

Usage: python scripts/check_tracked_keys.py [--list-file FILE]   (exit 0 = pass)
       --list-file reads paths from FILE instead of `git ls-files` (for tests).
"""

import fnmatch
import subprocess
import sys

# One list, matched against every tracked path (always with forward slashes).
# Keep in step with the "Signing keys and app secrets" block in .gitignore.
KEY_PATTERNS = [
	"*.jks",
	"*.keystore",
	"*.p12",
	"*.p8",
	"*.cer",
	"*.mobileprovision",
	"keystore.properties",
	"local.properties",
	"google-services.json",
	"GoogleService-Info.plist",
	"ExportOptions.plist",
	"*.local.xcconfig",
	# Built packages carry the signature and are never source.
	"*.apk",
	"*.aab",
]

# Folders whose contents are never source.
KEY_FOLDERS = [
	"xcuserdata/",
	"android/app/release/",
	"android/app/build/",
]


def offending(paths):
	"""The tracked paths that match a key pattern or sit in a key folder."""
	bad = []
	for raw in paths:
		path = raw.strip().replace("\\", "/")
		if not path:
			continue
		name = path.rsplit("/", 1)[-1]
		if any(fnmatch.fnmatchcase(name, p) for p in KEY_PATTERNS):
			bad.append(path)
			continue
		probe = "/" + path
		if any("/" + folder in probe for folder in KEY_FOLDERS):
			bad.append(path)
	return bad


def tracked_paths():
	out = subprocess.run(["git", "ls-files", "-z"], check=True,
	                     capture_output=True).stdout
	return [p.decode("utf-8", "replace") for p in out.split(b"\0") if p]


def main(argv):
	if len(argv) == 3 and argv[1] == "--list-file":
		with open(argv[2], encoding="utf-8") as f:
			paths = f.read().splitlines()
	elif len(argv) == 1:
		paths = tracked_paths()
	else:
		print(__doc__)
		return 2

	bad = offending(paths)
	if bad:
		print("FAIL: git tracks files that look like signing keys or app secrets.")
		print("Remove them from git (git rm --cached <file>), move the key OUT of every")
		print("git folder, and treat the key as leaked if it was ever pushed:")
		for path in bad:
			print(f"  {path}")
		return 1

	print(f"OK: none of {len(paths)} tracked files looks like a key or app secret.")
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv))
