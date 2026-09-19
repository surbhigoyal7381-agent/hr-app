#!/usr/bin/env python3
"""Is the portal's visual language a system, or an accumulation?

Every number here is an acceptance criterion from
docs/slices/002-ess-home-redesign/02-functional-spec.md. They are counted rather
than judged, because "looks more professional" is otherwise an argument nobody
can win and the kind of goal that quietly gets dropped.

Run it before the work to get the baseline, and in CI afterwards so the page
cannot drift back. It reached 120 colours because every individual change was
reasonable; only a counter notices the aggregate.

    python scripts/check_design_system.py            # check, exit 1 on failure
    python scripts/check_design_system.py --report   # show the detail, never fail
"""
from __future__ import annotations

import colorsys
import glob
import os
import re
import sys

WWW = os.path.join("alvoraa_portal", "alvoraa_portal", "www")

# The page background and body text each theme is judged against.
GROUNDS = {"light": "#F8F6F3", "dark": "#1A1815"}

LIMITS = {
	# AC-1 is not "few colours" but "no colour chosen outside the system".
	# A two-theme token set is forty-odd values by arithmetic, so a low cap on
	# the palette was never reachable and would have been gamed rather than met.
	# What matters is that nothing paints itself outside the tokens.
	"loose_colours": 0,
	"font_sizes": 7,    # AC-2
	"shadows": 3,       # AC-3
	"radii": 3,         # AC-4
	"undefined_vars": 0,
	"gradients": 0,     # AC-5
	"emoji": 0,         # AC-6
}

# Pages that carry their own visual language. goals-portal is a 15-line stub.
PAGES = ["hrms-employee.html", "driver-portal.html", "vendor-portal.html",
         "alvoraa-admin.html", "alvoraa-login.html"]

INCLUDE = os.path.join("alvoraa_portal", "alvoraa_portal", "templates",
                       "includes", "design_system.html")
SHARED_TOKENS = set()
if os.path.exists(INCLUDE):
	SHARED_TOKENS = set(re.findall(r"(--[a-z0-9-]+)\s*:",
	                               open(INCLUDE, encoding="utf-8").read()))


# ── measuring ────────────────────────────────────────────────────────────────

def strip_noise(t: str) -> str:
	"""Remove comments so a colour named in a note is not counted as a colour."""
	t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)      # CSS and JS block comments
	t = re.sub(r"<!--.*?-->", "", t, flags=re.S)     # HTML comments
	t = re.sub(r"^\s*//.*$", "", t, flags=re.M)      # JS line comments
	return t


def measure(text: str) -> dict:
	t = strip_noise(text)
	# Colours declared inside a :root{...} block are the palette. Anything else
	# is a value somebody painted by hand, which is what we are hunting.
	tokens = "\n".join(re.findall(r":root[^{]*\{[^}]*\}", t, flags=re.S))
	outside = re.sub(r":root[^{]*\{[^}]*\}", "", t, flags=re.S)
	return {
		"colours": sorted({m.lower() for m in
		                   re.findall(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", tokens)}),
		"loose_colours": sorted({m.lower() for m in
		                         re.findall(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", outside)}),
		# Only values chosen by hand are counted. A var() reference IS the
		# system, so counting those as separate values would mean the check
		# could never pass however tidy the page became.
		"font_sizes": sorted({float(x) for x in
		                      re.findall(r"font-size:\s*([0-9.]+)px", t)}),
		"shadows": sorted({s.strip() for s in
		                   re.findall(r"box-shadow:\s*([^;}\"']+)", t)
		                   if "none" not in s and "var(" not in s}),
		# Per-corner values and percentages are shapes, not palette drift:
		# `50%` is a circle and `0 3px 3px 0` is a tab. Neither is a choice
		# the token system should be making.
		"radii": sorted({r.strip() for r in
		                 re.findall(r"border-radius:\s*([^;}\"']+)", t)
		                 if "var(" not in r and "%" not in r
		                 and len(re.findall(r"[0-9.]+px", r)) == 1}),
		# A var() with nothing behind it is invisible until somebody looks at
		# the page. `font-family: var(--font)` with no --font falls back to the
		# browser's default serif, which is how the login page ended up looking
		# like a 1998 document after its own :root block was removed in favour
		# of the shared include.
		"undefined_vars": sorted(set(re.findall(r"var\((--[a-z0-9-]+)", t))
		                         - set(re.findall(r"(--[a-z0-9-]+)\s*:", t))
		                         - SHARED_TOKENS),
		"gradients": re.findall(r"(?:linear|radial|conic)-gradient", t),
		"emoji": [c for c in t if _is_emoji(c)],
	}


def _is_emoji(c: str) -> bool:
	o = ord(c)
	# Pictographs and dingbats. Box-drawing (used in source comments) excluded,
	# and so are the arrows and typographic marks the page uses as real content.
	return (0x1F300 <= o <= 0x1FAFF) or (0x2600 <= o <= 0x27BF) or o in (0x2B50, 0xFE0F)


# ── contrast ─────────────────────────────────────────────────────────────────

def _lum(h: str) -> float:
	h = h.lstrip("#")
	if len(h) == 3:
		h = "".join(c * 2 for c in h)
	ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
	ch = [(x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4) for x in ch]
	return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast(a: str, b: str) -> float:
	la, lb = _lum(a), _lum(b)
	la, lb = max(la, lb), min(la, lb)
	return round((la + 0.05) / (lb + 0.05), 2)


def is_dark(h: str) -> bool:
	h = h.lstrip("#")
	if len(h) == 3:
		h = "".join(c * 2 for c in h)
	r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
	return colorsys.rgb_to_hls(r, g, b)[1] < 0.5


def text_colours(colours: list[str]) -> list[str]:
	"""Colours dark enough to be used as text on the light ground.

	A background fill is not held to the text standard - judging a pale tint as
	unreadable text would make the check cry wolf and get switched off.
	"""
	return [c for c in colours if is_dark(c)]


# ── reporting ────────────────────────────────────────────────────────────────

def main() -> int:
	report = "--report" in sys.argv
	if not os.path.isdir(WWW):
		print("run me from the repository root")
		return 2

	failures, rows = [], []
	for name in PAGES:
		path = os.path.join(WWW, name)
		if not os.path.exists(path):
			continue
		m = measure(open(path, encoding="utf-8").read())
		counts = {k: len(v) for k, v in m.items()}
		rows.append((name, counts))

		for key, limit in LIMITS.items():
			if counts[key] > limit:
				failures.append("%s: %d %s (limit %d)" % (name, counts[key], key, limit))

		# AC-7 / AC-8: anything dark enough to be text must be readable.
		for c in text_colours(m["colours"] + m["loose_colours"]):
			if contrast(c, GROUNDS["light"]) < 4.5 and contrast(c, GROUNDS["dark"]) < 4.5:
				failures.append("%s: %s is unreadable on both grounds (%.2f / %.2f)"
				                % (name, c, contrast(c, GROUNDS["light"]),
				                   contrast(c, GROUNDS["dark"])))

		if report:
			print("\n" + "=" * 70)
			print(name)
			print("=" * 70)
			for k in ("loose_colours", "undefined_vars", "font_sizes", "shadows",
			          "radii", "gradients", "emoji"):
				mark = "ok " if counts[k] <= LIMITS[k] else "OVER"
				print("  %-11s %4d  (limit %2d)  %s" % (k, counts[k], LIMITS[k], mark))
			bad = [c for c in text_colours(m["colours"] + m["loose_colours"])
			       if contrast(c, GROUNDS["light"]) < 4.5
			       and contrast(c, GROUNDS["dark"]) < 4.5]
			if bad:
				print("  unreadable as text on either ground:")
				for c in bad:
					print("     %s  light %5.2f  dark %5.2f"
					      % (c, contrast(c, GROUNDS["light"]), contrast(c, GROUNDS["dark"])))

	print()
	hdr = ("page", "palette", "loose", "undef", "sizes", "shadows", "radii",
	       "gradient", "emoji")
	fmt = "%-24s %7s %6s %6s %6s %8s %6s %9s %6s"
	print(fmt % hdr)
	for name, c in rows:
		print(fmt % (name, c["colours"], c["loose_colours"], c["undefined_vars"],
		             c["font_sizes"], c["shadows"], c["radii"], c["gradients"],
		             c["emoji"]))
	print(fmt % ("LIMIT", "-", LIMITS["loose_colours"], LIMITS["undefined_vars"],
	             LIMITS["font_sizes"], LIMITS["shadows"], LIMITS["radii"],
	             LIMITS["gradients"], LIMITS["emoji"]))

	if report:
		return 0
	if failures:
		print("\nFAIL - %d problem(s):" % len(failures))
		for f in failures[:40]:
			print("   " + f)
		if len(failures) > 40:
			print("   ... and %d more" % (len(failures) - 40))
		return 1
	print("\nOK - the visual system holds")
	return 0


if __name__ == "__main__":
	sys.exit(main())
