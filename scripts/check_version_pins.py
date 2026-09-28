"""Every upstream app in the image is pinned, and the three files agree (ALV-156, slice 055).

`deploy/Dockerfile` fetches upstream apps: frappe, erpnext, india_compliance,
crm, frappe_whatsapp, and - added by slice 166/167 - payments, lms and
telephony (helpdesk is already pinned by release tag, `HELPDESK_TAG`, so it
needs no separate entry here). Until 2026-09-27 three of the original five were
fetched from `version-16` - a MOVING branch - so two builds of the same commit
of our code could contain different framework code, and nothing recorded which
one an image got. Measured that day: production ran Frappe v16.34.0 while dev
ran v16.35.0, from the same branch name.

Two things can undo the fix quietly, and this check catches both:

1. A pin set back to a branch name. A value that is not a release tag
   (`v1.2.3`) or a full-length commit is treated as moving and fails.
2. The files drifting apart. `.github/workflows/ci.yml` builds its own bench for
   the Python tests, so it names Frappe and ERPNext a second time. If it names a
   different version, CI stops testing what the image ships. And a `build-args:`
   entry in `.github/workflows/build-image.yml` WINS over the Dockerfile's `ARG`
   default - which is how a pin can look applied and not be.

No network, no bench, no database: this reads three files in the repository.

    python scripts/check_version_pins.py      exit 0 = pass
    python scripts/check_version_pins.py --self-test

Raising a pin is a decision, not a chore - the procedure is in
docs/slices/055-pin-framework-versions/07-devops-inputs.md §4.
"""

import argparse
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCKERFILE = os.path.join(REPO, "deploy", "Dockerfile")
CI_YML = os.path.join(REPO, ".github", "workflows", "ci.yml")
BUILD_YML = os.path.join(REPO, ".github", "workflows", "build-image.yml")

# ARG name in deploy/Dockerfile -> what a good value looks like.
# A tag is "v" then digits and dots. A commit is 12 or more hex characters.
TAG = re.compile(r"^v\d+(\.\d+)*$")
COMMIT = re.compile(r"^[0-9a-f]{12,40}$")

PINS = ("FRAPPE_TAG", "ERPNEXT_TAG", "INDIA_COMPLIANCE_TAG", "CRM_TAG", "WHATSAPP_COMMIT",
        "PAYMENTS_COMMIT", "LMS_COMMIT", "TELEPHONY_COMMIT")

# ARG name in the Dockerfile -> env name in ci.yml's test-python job.
MUST_MATCH_CI = {"FRAPPE_TAG": "FRAPPE_TAG", "ERPNEXT_TAG": "ERPNEXT_TAG"}


def read_args(dockerfile_text):
	"""{ARG name: value} for every `ARG NAME=value` line."""
	return dict(re.findall(r"^ARG\s+([A-Z0-9_]+)=(\S+)\s*$", dockerfile_text, re.MULTILINE))


def read_ci_env(ci_text):
	"""{name: value} for `NAME: value` lines that name one of our pins."""
	found = {}
	for name in set(MUST_MATCH_CI.values()):
		m = re.search(r"^\s+%s:\s*(\S+)\s*$" % name, ci_text, re.MULTILINE)
		if m:
			found[name] = m.group(1)
	return found


def build_arg_overrides(build_text):
	"""Pin names passed as build-args, which would beat the Dockerfile default."""
	block = re.search(r"^\s+build-args:\s*\|(.*?)(?=^\s+\w[\w-]*:|\Z)", build_text, re.MULTILINE | re.DOTALL)
	if not block:
		return []
	return sorted({n for n in re.findall(r"([A-Z0-9_]+)=", block.group(1))})


def check(args, ci_env, overrides):
	problems = []

	for name in PINS:
		value = args.get(name)
		if value is None:
			problems.append(f"{name} is not set in deploy/Dockerfile - every upstream app must be pinned")
		elif not (TAG.match(value) or COMMIT.match(value)):
			problems.append(
				f"{name}={value} is not a release tag or a full commit. "
				"A branch moves on its own, so two builds of the same commit would differ"
			)

	for arg_name, env_name in MUST_MATCH_CI.items():
		want, got = args.get(arg_name), ci_env.get(env_name)
		if got is None:
			problems.append(f"ci.yml does not set {env_name} - its test bench would not match the image")
		elif want is not None and got != want:
			problems.append(
				f"ci.yml {env_name}={got} but deploy/Dockerfile {arg_name}={want} - "
				"CI would test a different framework from the one the image ships"
			)

	clash = [n for n in overrides if n in PINS or n.endswith(("_TAG", "_BRANCH", "_COMMIT"))]
	if clash:
		problems.append(
			"build-image.yml passes " + ", ".join(clash) + " as build-args. "
			"A build-arg beats the Dockerfile's ARG default, so the pin in deploy/Dockerfile "
			"would be ignored. Remove it, or change the Dockerfile instead"
		)

	return problems


def self_test():
	good_args = {
		"FRAPPE_TAG": "v16.35.0",
		"ERPNEXT_TAG": "v16.36.0",
		"INDIA_COMPLIANCE_TAG": "v16.10.0",
		"CRM_TAG": "v1.84.0",
		"WHATSAPP_COMMIT": "08bc1f6af2e3",
		"PAYMENTS_COMMIT": "cca07d9f9392e2ea0e521c5975151db9e4b6c321",
		"LMS_COMMIT": "87168fc7b2f24559e474ea4702cf1aa63b0db4e8",
		"TELEPHONY_COMMIT": "039cf39f245d6818ead03cf94eea6ce7f9c1e1f7",
	}
	good_ci = {"FRAPPE_TAG": "v16.35.0", "ERPNEXT_TAG": "v16.36.0"}
	cases = [
		("a clean set passes", good_args, good_ci, [], 0),
		("a branch is caught", dict(good_args, FRAPPE_TAG="version-16"), good_ci, [], 1),
		("a short commit is caught", dict(good_args, WHATSAPP_COMMIT="08bc1f"), good_ci, [], 1),
		("a missing pin is caught", {k: v for k, v in good_args.items() if k != "CRM_TAG"}, good_ci, [], 1),
		("ci.yml disagreeing is caught", good_args, dict(good_ci, FRAPPE_TAG="v16.34.0"), [], 1),
		("ci.yml silent is caught", good_args, {"ERPNEXT_TAG": "v16.36.0"}, [], 1),
		("a build-arg override is caught", good_args, good_ci, ["FRAPPE_TAG"], 1),
	]
	failures = 0
	for label, a, c, o, expected in cases:
		problems = check(a, c, o)
		ok = (len(problems) > 0) == (expected > 0)
		print(("  ok   " if ok else "  FAIL ") + label + ("" if ok else f" -> {problems}"))
		failures += 0 if ok else 1
	print(f"check_version_pins --self-test: {len(cases) - failures}/{len(cases)} passed")
	return 1 if failures else 0


def main():
	p = argparse.ArgumentParser(description=__doc__)
	p.add_argument("--self-test", action="store_true", help="run the rule's own tests")
	opts = p.parse_args()
	if opts.self_test:
		return self_test()

	try:
		with open(DOCKERFILE, encoding="utf-8") as f:
			args = read_args(f.read())
		with open(CI_YML, encoding="utf-8") as f:
			ci_env = read_ci_env(f.read())
		with open(BUILD_YML, encoding="utf-8") as f:
			overrides = build_arg_overrides(f.read())
	except OSError as exc:
		print(f"check_version_pins: cannot read a file: {exc}")
		return 1

	problems = check(args, ci_env, overrides)
	for problem in problems:
		print("check_version_pins: " + problem)
	if not problems:
		print("check_version_pins: OK (" + ", ".join(f"{n}={args[n]}" for n in PINS) + ")")
	return 1 if problems else 0


if __name__ == "__main__":
	sys.exit(main())
