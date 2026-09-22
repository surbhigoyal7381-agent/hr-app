"""The app-version floor honours the 90-day rule (slice 013, AC-37 / OPS-48 / OPS-58).

`MIN_APP_VERSION` in `alvoraa_portal/alvoraa_portal/field_app_errors.py` is the
oldest app build the server still answers. Every phone below it gets
`APP_TOO_OLD` and can do nothing until the person updates. Raising it is a
lock-out, so the rule for the life of the app is: the floor may only rise to a
version that has been available in the store for 90 days, counted from its
first store release. That gives every phone three months of "please update"
before it is refused.

This check reads the floor from the source and the store releases from
`mobile/field-app/releases.json`, and fails the build when the floor names a
version released less than 90 days ago, or a version that was never released.
It passes while nothing has been released yet (the pilot runs on test builds),
and when the floor is at or below the earliest store release, which locks out
nobody.

Runs in CI (`ci.yml`, lint job). No bench, no database, no network.

    python scripts/check_min_app_version.py                exit 0 = pass
    python scripts/check_min_app_version.py --today 2027-01-15
    python scripts/check_min_app_version.py --self-test    the rule's own tests

`releases.json` is a list of {"version": "MAJOR.MINOR.PATCH", "released":
"YYYY-MM-DD"} - the date the build first appeared in a store. Add a line when a
build is released; never edit a date afterwards.
"""

import argparse
import datetime
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERRORS_PY = os.path.join(REPO, "alvoraa_portal", "alvoraa_portal", "field_app_errors.py")
RELEASES_JSON = os.path.join(REPO, "mobile", "field-app", "releases.json")

GRACE_DAYS = 90

_MIN_LINE = re.compile(r'^MIN_APP_VERSION\s*=\s*"([^"]*)"', re.MULTILINE)


def parse_version(raw):
	"""Three numbers or None - the same rule the server applies."""
	if not isinstance(raw, str):
		return None
	parts = raw.strip().split(".")
	if len(parts) != 3:
		return None
	try:
		numbers = tuple(int(p) for p in parts)
	except ValueError:
		return None
	return numbers if all(n >= 0 for n in numbers) else None


def read_min_version(source_text):
	match = _MIN_LINE.search(source_text)
	return match.group(1) if match else None


def check(min_version, releases, today):
	"""The problems with this floor against these releases on this day. Empty = pass."""
	problems = []
	floor = parse_version(min_version)
	if floor is None:
		return [f'MIN_APP_VERSION "{min_version}" is not MAJOR.MINOR.PATCH.']

	dated = {}
	for entry in releases:
		version = parse_version((entry or {}).get("version"))
		raw_date = (entry or {}).get("released")
		if version is None:
			problems.append(f"releases.json: version {entry.get('version')!r} is not MAJOR.MINOR.PATCH.")
			continue
		try:
			released = datetime.date.fromisoformat(str(raw_date))
		except (TypeError, ValueError):
			problems.append(f"releases.json: {entry.get('version')} has no YYYY-MM-DD release date.")
			continue
		if version in dated:
			problems.append(f"releases.json: {entry.get('version')} is listed twice.")
			continue
		dated[version] = released
	if problems:
		return problems

	if not dated:
		# Nothing in a store yet: there is nobody to lock out.
		return []

	earliest = min(dated)
	if floor <= earliest:
		# At or below the first store build: every store build is still served.
		return []

	if floor not in dated:
		return [f"MIN_APP_VERSION {min_version} was never released to a store "
		        f"(releases.json lists {', '.join('.'.join(map(str, v)) for v in sorted(dated))}). "
		        f"The floor can only be a version phones have been able to install."]

	released = dated[floor]
	allowed_from = released + datetime.timedelta(days=GRACE_DAYS)
	if today < allowed_from:
		age = (today - released).days
		return [f"MIN_APP_VERSION {min_version} was released on {released} - {age} day(s) ago. "
		        f"The floor may only rise to a version that has been in the store for "
		        f"{GRACE_DAYS} days (OPS-48); it can become {min_version} from {allowed_from}."]
	return []


def load_releases(path):
	with open(path, encoding="utf-8") as f:
		data = json.load(f)
	releases = data.get("releases") if isinstance(data, dict) else data
	if not isinstance(releases, list):
		raise ValueError("releases.json must hold a list under \"releases\"")
	return releases


def self_test():
	"""The rule, exercised. Kept here so it runs in the same CI step: the bench
	does not mount scripts/, so a unit test in the app could not import this."""
	d = datetime.date
	rel = [{"version": "1.0.0", "released": "2026-10-01"},
	       {"version": "1.1.0", "released": "2026-12-01"}]
	cases = [
		("nothing released yet, any floor passes", "1.0.0", [], d(2026, 9, 23), 0),
		("floor at the first release passes", "1.0.0", rel, d(2026, 10, 2), 0),
		("floor below the first release passes", "0.9.0", rel, d(2026, 10, 2), 0),
		("a fresh release cannot be the floor", "1.1.0", rel, d(2026, 12, 15), 1),
		("89 days is still too soon", "1.1.0", rel, d(2027, 2, 28), 1),
		("90 days on, it may", "1.1.0", rel, d(2027, 3, 1), 0),
		("a version never released cannot be the floor", "1.0.5", rel, d(2027, 6, 1), 1),
		("a malformed floor fails", "1.0", rel, d(2027, 6, 1), 1),
		("a malformed release fails", "1.0.0", [{"version": "x", "released": "2026-10-01"}],
		 d(2027, 6, 1), 1),
		("a release with no date fails", "1.0.0", [{"version": "1.0.0"}], d(2027, 6, 1), 1),
		("1.10.0 is newer than 1.9.0", "1.9.0",
		 [{"version": "1.9.0", "released": "2026-01-01"}, {"version": "1.10.0", "released": "2027-01-01"}],
		 d(2026, 6, 1), 0),
	]
	failed = 0
	for label, floor, releases, today, expected in cases:
		problems = check(floor, releases, today)
		ok = (len(problems) > 0) == (expected > 0)
		print(("ok   " if ok else "FAIL ") + label + ("" if ok else f": {problems}"))
		failed += 0 if ok else 1
	return failed


def main(argv=None):
	parser = argparse.ArgumentParser()
	parser.add_argument("--today", help="YYYY-MM-DD, for a dry run on another day")
	parser.add_argument("--self-test", action="store_true")
	args = parser.parse_args(argv)

	if args.self_test:
		failed = self_test()
		print(f"check_min_app_version self-test: {'OK' if not failed else str(failed) + ' FAILED'}")
		return 1 if failed else 0

	today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
	with open(ERRORS_PY, encoding="utf-8") as f:
		min_version = read_min_version(f.read())
	if min_version is None:
		print(f"check_min_app_version: MIN_APP_VERSION not found in {ERRORS_PY}")
		return 1
	try:
		releases = load_releases(RELEASES_JSON)
	except (OSError, ValueError) as exc:
		print(f"check_min_app_version: cannot read {RELEASES_JSON}: {exc}")
		return 1

	problems = check(min_version, releases, today)
	for p in problems:
		print("check_min_app_version: " + p)
	if not problems:
		print(f"check_min_app_version: OK (floor {min_version}, {len(releases)} store release(s) listed)")
	return 1 if problems else 0


if __name__ == "__main__":
	sys.exit(main())
