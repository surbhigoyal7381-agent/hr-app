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
import argparse
import io
import os
import shutil
import sys
import tempfile

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


def scan(deploy_dir, repo_root):
	"""Every file under `deploy_dir` that names the flag and is not plainly a
	dev or test file. Returns (files read, offending paths)."""
	checked, offenders = 0, []
	for folder, _dirs, files in os.walk(deploy_dir):
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
			offenders.append(os.path.relpath(path, repo_root))
	return checked, offenders


def check(deploy_dir, repo_root):
	"""0 when no production deployment file sets the flag, 1 when one does."""
	if not os.path.isdir(deploy_dir):
		print(f"deploy/ not found at {deploy_dir}")
		return 1

	checked, offenders = scan(deploy_dir, repo_root)

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


def self_test():
	"""The positive control: prove this check can FAIL.

	A guard nobody has watched fail is not a guard. This one has already been
	wrong once in exactly the way that matters - its first version passed
	`production.env.example`, the file somebody copies to make the real
	production env - and a check that only ever prints OK would have hidden
	that. So the rule is exercised against a throwaway deploy/ folder, built
	here, with a file of each shape in it.

	`--self-test` used to be accepted and ignored: nothing read sys.argv, so CI
	ran the same check twice and called one of them a positive control. That is
	the same shape as the hollow tests this slice has paid for twice.
	"""
	cases = [
		# (filename, contents, must this file be caught?)
		("production.env", f"{FLAG}=1\n", True),
		("production.env.example", f"{FLAG}=1\n", True),
		("docker-compose.yml", f"  - {FLAG}=1\n", True),
		("nested/prod-site-config.json", '{"%s": 1}' % FLAG, True),
		("dev.env", f"{FLAG}=1\n", False),
		("docker-compose.test.yml", f"  - {FLAG}=1\n", False),
		("production.env.clean", "SOME_OTHER_SETTING=1\n", False),
	]

	failed = 0
	root = tempfile.mkdtemp(prefix="preview-flag-self-test-")
	try:
		deploy = os.path.join(root, "deploy")
		for name, body, _caught in cases:
			path = os.path.join(deploy, name)
			os.makedirs(os.path.dirname(path), exist_ok=True)
			io.open(path, "w", encoding="utf-8").write(body)

		_checked, offenders = scan(deploy, root)
		found = {o.replace("\\", "/") for o in offenders}
		for name, _body, caught in cases:
			want = os.path.join("deploy", name).replace("\\", "/")
			got = want in found
			ok = got == caught
			failed += 0 if ok else 1
			verdict = "caught" if caught else "left alone"
			print(("ok   " if ok else "FAIL ") + f"{name} is {verdict}")

		# And the whole check, end to end: it must RETURN 1 on a bad folder and
		# 0 once that folder is clean. An offender list nobody acts on is the
		# other half of the same hollow guard.
		print("--- what the check prints when it catches one, on purpose: ---")
		code_bad = check(deploy, root)
		print("--- end of the deliberate failure; the build is not failing here ---")
		print(("ok   " if code_bad == 1 else "FAIL ") + "a deliberately bad deploy/ exits 1")
		failed += 0 if code_bad == 1 else 1

		for name, _body, caught in cases:
			if caught:
				os.remove(os.path.join(deploy, name))
		code_good = check(deploy, root)
		print(("ok   " if code_good == 0 else "FAIL ") + "the same folder, cleaned, exits 0")
		failed += 0 if code_good == 0 else 1
	finally:
		shutil.rmtree(root, ignore_errors=True)

	return failed


def main(argv=None):
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--self-test", action="store_true",
	                    help="prove the check fails on a deliberately bad file")
	args = parser.parse_args(argv)

	if args.self_test:
		failed = self_test()
		print(f"check_preview_flag self-test: {'OK' if not failed else str(failed) + ' FAILED'}")
		return 1 if failed else 0

	return check(DEPLOY, REPO)


if __name__ == "__main__":
	sys.exit(main())
