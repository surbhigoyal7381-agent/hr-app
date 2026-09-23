"""The deploy must check every /assets/ file the employee portal loads (F1).

Slice 034 moved the portal's styles and script out of the page. They are three
static files now, served by nginx with `try_files $uri =404` and told to cache
for 30 days. A 404 on `portal.js` is the WHOLE PORTAL GONE, silently: the page
still renders its shell, nothing runs, nothing reaches the backend, and so
nothing appears in any log. The smoke test in the deploy does not catch it - it
asks the API, not the assets.

So `.github/workflows/deploy.yml` fetches all three after the smoke test and
fails the deploy if any is missing or empty. This keeps that gate honest:

  * the step must still be there, and
  * it must name every asset the page actually loads.

A page file gets renamed far more often than a workflow gets read. Without this,
renaming a stylesheet would leave the gate checking a file nobody loads while
the one that matters goes unchecked - a gate that cannot fail, which is the
shape of the thing this slice has been bitten by twice.

Why a script and not only a bench test: the bench test
(`test_preview_page_034.TestTheDeployGateChecksTheFilesThePageActuallyLoads`)
can only reach `.github/` when the app is checked out inside the repository. On
a bench where the app is MOUNTED it skips, and a skipped check protects nobody.
This one always runs. Same reasoning, and same shape, as check_preview_flag.py.

    python scripts/check_portal_assets_gate.py              exit 0 = pass
    python scripts/check_portal_assets_gate.py --self-test  prove it can fail
"""

import argparse
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(REPO, ".github", "workflows", "deploy.yml")
PAGES = (
	os.path.join(REPO, "alvoraa_portal", "alvoraa_portal", "www", "hrms-employee.html"),
)
STEP_NAME = "Portal assets must be served"

# <link rel="stylesheet" href="/assets/alvoraa_portal/css/ess/frame.css?v=123">
# <script src="/assets/alvoraa_portal/js/ess/portal.js?v=123" defer></script>
ASSET_RE = re.compile(r'(?:href|src)="(/assets/alvoraa_portal/[^"?]+)(?:\?[^"]*)?"')


def assets_loaded_by(page_text):
	"""Every /assets/alvoraa_portal/ address the page asks a browser for."""
	return sorted(set(ASSET_RE.findall(page_text)))


def check(workflow_text, pages):
	"""A list of problems. Empty means the gate covers what the pages load.

	`pages` is a list of (label, text) so the self-test can hand in its own.
	"""
	problems = []
	if STEP_NAME not in workflow_text:
		problems.append(
			f'the deploy step "{STEP_NAME}" is gone. Nothing then proves the '
			f"portal's files arrived, and a 404 on portal.js is a portal that "
			f"renders and does nothing, with nothing in any log.")

	for label, text in pages:
		loaded = assets_loaded_by(text)
		if not loaded:
			problems.append(f"{label} loads no /assets/alvoraa_portal files at all - "
			                f"either it changed shape or this check is looking at the "
			                f"wrong file.")
			continue
		for address in loaded:
			if address not in workflow_text:
				problems.append(
					f"{label} loads {address}, and the deploy does not check that it "
					f"arrived. Add it to the \"{STEP_NAME}\" step.")
	return problems


def _read(path):
	return io.open(path, encoding="utf-8", errors="ignore").read()


def main_check():
	if not os.path.isfile(WORKFLOW):
		print(f"deploy workflow not found at {WORKFLOW}")
		return 1

	pages = []
	for path in PAGES:
		if not os.path.isfile(path):
			print(f"portal page not found at {path}")
			return 1
		pages.append((os.path.relpath(path, REPO), _read(path)))

	problems = check(_read(WORKFLOW), pages)
	if problems:
		print("FAIL - the deploy does not check every file the portal loads:")
		for p in problems:
			print("  " + p)
		return 1

	checked = sum(len(assets_loaded_by(text)) for _label, text in pages)
	print(f"portal asset gate: {checked} asset address(es) across {len(pages)} page(s)")
	print("OK - the deploy checks every one of them")
	return 0


def self_test():
	"""The positive control: prove this check can FAIL.

	A guard nobody has watched fail is not a guard, and the two ways this one
	goes wrong are both quiet: the step gets deleted in a workflow tidy-up, or a
	stylesheet gets renamed and the gate keeps checking the old address.
	"""
	good_workflow = (
		"      - name: " + STEP_NAME + "\n"
		"        run: |\n"
		"          /assets/alvoraa_portal/css/ess/frame.css\n"
		"          /assets/alvoraa_portal/js/ess/portal.js\n")
	good_page = (
		'<link rel="stylesheet" href="/assets/alvoraa_portal/css/ess/frame.css?v=1">\n'
		'<script src="/assets/alvoraa_portal/js/ess/portal.js?v=1" defer></script>\n')

	cases = [
		("the real shape passes", good_workflow, good_page, 0),
		("a renamed stylesheet is caught", good_workflow,
		 good_page.replace("frame.css", "frame-v2.css"), 1),
		("a newly added asset is caught", good_workflow,
		 good_page + '<script src="/assets/alvoraa_portal/js/ess/extra.js"></script>\n', 1),
		("the step being deleted is caught",
		 good_workflow.replace(STEP_NAME, "Something else"), good_page, 1),
		("a page that loads nothing is caught", good_workflow,
		 "<html><body>no assets here</body></html>", 1),
		("the query string is not part of the address", good_workflow,
		 good_page.replace("?v=1", "?v=999999"), 0),
	]

	failed = 0
	for label, workflow, page, expected in cases:
		problems = check(workflow, [("a test page", page)])
		got = 1 if problems else 0
		ok = got == expected
		failed += 0 if ok else 1
		print(("ok   " if ok else "FAIL ") + label + ("" if ok else f": {problems}"))
	return failed


def main(argv=None):
	parser = argparse.ArgumentParser(description="See the module docstring.")
	parser.add_argument("--self-test", action="store_true",
	                    help="prove the check fails on a deliberately bad pair")
	args = parser.parse_args(argv)

	if args.self_test:
		failed = self_test()
		print(f"check_portal_assets_gate self-test: "
		      f"{'OK' if not failed else str(failed) + ' FAILED'}")
		return 1 if failed else 0

	return main_check()


if __name__ == "__main__":
	sys.exit(main())
