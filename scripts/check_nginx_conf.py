"""Pin test for deploy/nginx.conf: callers cannot choose their own IP address.

Slice 014, OPS-19. Frappe believes the FIRST address in X-Forwarded-For and keys
its rate limits, its login lock and the "Restrict IP" check on it. The old config
passed `$proxy_add_x_forwarded_for`, which keeps whatever the caller wrote, so
anyone could get a fresh rate-limit bucket on every request.

This is a text check with no nginx and no docker, so it runs in CI on every
push. It fails if a merge brings any of these back:

  1. `$proxy_add_x_forwarded_for` anywhere;
  2. an `X-Forwarded-For` header set to anything but `$remote_addr`;
  3. the Cloudflare `real_ip_header CF-Connecting-IP` missing, or a
     `set_real_ip_from` that is not a plain IP range (a hostname or 0.0.0.0/0
     would let anybody set their own address);
  4. a server block with a `/api/` location but no login-limited location that
     covers /api/method/login, /api/v1/method/login and /api/v2/method/login.

That the file actually PARSES, and behaves, is checked by
scripts/check_nginx_forwarded.sh in throwaway containers - run it before any
push that changes nginx.conf.

Usage: python scripts/check_nginx_conf.py [path]   (exit 0 = pass)
"""

import ipaddress
import re
import sys
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent.parent / "deploy" / "nginx.conf"
LOGIN_PATHS = ("/api/method/login", "/api/v1/method/login", "/api/v2/method/login")


def _strip_comments(text):
	return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _server_blocks(text):
	"""(server_name line, block text) for each top-level server { } block."""
	blocks = []
	for match in re.finditer(r"\bserver\s*\{", text):
		depth, i = 0, match.end() - 1
		while i < len(text):
			if text[i] == "{":
				depth += 1
			elif text[i] == "}":
				depth -= 1
				if depth == 0:
					break
			i += 1
		body = text[match.start():i + 1]
		name = re.search(r"server_name\s+([^;]+);", body)
		blocks.append((name.group(1).strip() if name else "?", body))
	return blocks


def _locations(block):
	"""(modifier, pattern, body) for each location in a server block."""
	out = []
	for match in re.finditer(r"location\s+(=|~\*|~|\^~)?\s*(\S+)\s*\{", block):
		depth, i = 0, match.end() - 1
		while i < len(block):
			if block[i] == "{":
				depth += 1
			elif block[i] == "}":
				depth -= 1
				if depth == 0:
					break
			i += 1
		out.append((match.group(1) or "", match.group(2), block[match.end():i]))
	return out


def check(path):
	problems = []
	text = _strip_comments(Path(path).read_text(encoding="utf-8"))

	if "$proxy_add_x_forwarded_for" in text:
		problems.append("$proxy_add_x_forwarded_for is back: callers can forge their address")

	for value in re.findall(r"proxy_set_header\s+X-Forwarded-For\s+([^;]+);", text, re.I):
		if value.strip() != "$remote_addr":
			problems.append(f"X-Forwarded-For is set to {value.strip()!r}, not $remote_addr")

	if not re.search(r"^\s*real_ip_header\s+CF-Connecting-IP\s*;", text, re.M):
		problems.append("real_ip_header CF-Connecting-IP is missing")
	ranges = re.findall(r"^\s*set_real_ip_from\s+([^;]+);", text, re.M)
	if not ranges:
		problems.append("no set_real_ip_from lines (Cloudflare ranges) found")
	for value in ranges:
		try:
			net = ipaddress.ip_network(value.strip(), strict=True)
		except ValueError:
			problems.append(f"set_real_ip_from {value.strip()!r} is not a plain IP range")
			continue
		if net.prefixlen < 8:
			problems.append(f"set_real_ip_from {value.strip()} trusts far too much")

	for name, block in _server_blocks(text):
		locations = _locations(block)
		proxies_api = any(pattern.startswith("/api") and "proxy_pass" in body
		                  for _, pattern, body in locations)
		if not proxies_api:
			continue
		for login in LOGIN_PATHS:
			covered = False
			for modifier, pattern, body in locations:
				if "zone=kinexus_login" not in body:
					continue
				if modifier == "=" and pattern == login:
					covered = True
				elif modifier in ("~", "~*") and re.search(
						pattern, login, re.I if modifier == "~*" else 0):
					covered = True
			if not covered:
				problems.append(f"server {name}: {login} is not under the login limit")

	return problems


def main():
	path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
	problems = check(path)
	for p in problems:
		print(f"FAIL  {p}")
	if problems:
		return 1
	print(f"OK    {path}: no caller-chosen addresses; Cloudflare ranges valid; all login paths limited")
	return 0


if __name__ == "__main__":
	sys.exit(main())
