"""The names a browser sends have to be the names the server declares.

**Why this file exists.** `next-inbox.js` sent `{ name, action, reason }` to
`hr_api.action_leave(leave_id, action)`. Frappe keeps only the arguments a
function declares and drops the rest without a word
(`frappe.get_newargs`, `apps/frappe/frappe/__init__.py`), so that call arrived as
`action_leave(action="approve")` and raised

    TypeError: action_leave() missing 1 required positional argument: 'leave_id'

Every Approve and Decline on the new Inbox failed from Wave 2 until 2026-09-25,
and nothing went red, because **every test on this project calls the Python
directly**. A whole class of fault - the browser and the server disagreeing about
an argument NAME - had no check at all. `test_portal_call_paths` proves the
method path exists; `test_frappe_api_calls` proves our calls into `frappe` match
its signatures. Neither looks at what the browser puts in the request body.

So: read our own JavaScript, collect every endpoint called with an object literal
of arguments, and compare those keys with the Python signature. Two failures, and
they are different bugs:

  * **missing** - a required parameter the browser never sends. TypeError, every
    time, for every user. This is the `action_leave` bug.
  * **undeclared** - a key the server has no parameter for. No error at all; the
    value is dropped on the floor. `reason` was one of these, so the decline
    reason a manager typed on a factory-floor phone went nowhere.

**What this does NOT cover**, said plainly, because a check whose edges are
guessed at is worse than one whose edges are written down:

  * only `alvoraa_portal/public/js/ess/*.js` - the portal. Not the desk, not the
    mobile app, not any other app's JavaScript;
  * only the five call shapes in `_CALLS` below. A call assembled at run time
    from a variable is not readable here and is not read;
  * only argument NAMES. Nothing here checks a type, a value or an order;
  * an endpoint reached by plain navigation rather than an argument call - the
    payslip PDF - has no argument list to check, and is named in `NO_ARG_CALL`.

**It fails loudly rather than quietly.** Two guards stop it checking less than it
claims: the number of call sites found may not fall below `MIN_CALL_SITES`, and
every `alvoraa_portal.*` endpoint named anywhere in those files must be matched
to a call site or listed with a reason. Rewriting a call into a shape the reader
cannot parse fails the test instead of silently leaving it unchecked - the same
rule `tests/portal_source.py` uses for the page's includes.
"""

import inspect
import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase

# ── Where the JavaScript is ────────────────────────────────────────────────

JS_DIRS = (os.path.join("public", "js", "ess"),)

# The panels the redesign owns, plus the page they are replacing. If one of
# these disappears the test says so rather than checking one file fewer.
REQUIRED_FILES = (
	"portal.js", "next-frame.js", "next-home.js", "next-inbox.js",
	"next-time.js", "next-pay.js", "next-team.js", "next-growth.js",
)

# Pinned floor. 220 call sites are read today - 203 of them in portal.js, which
# is more of the page than this test set out to cover. Raise it when call sites
# are added; never lower it to make a refactor pass, because that is how a check
# quietly stops checking.
MIN_CALL_SITES = 200

ENDPOINT_RE = re.compile(r"alvoraa_portal\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*")

# ── Endpoints named in the JavaScript that are not argument calls ──────────
#
# Each needs a reason. An empty reason is not allowed by the test.
NO_ARG_CALL = {
	"alvoraa_portal.hr_api.get_payslip":
		"fetched by plain navigation so the phone's own PDF viewer opens it "
		"(next-pay.js download()), not by an arguments call",
}


# ── Reading an object literal ──────────────────────────────────────────────

_KEY_RE = re.compile(r"""(?:([A-Za-z_$][\w$]*)|"([^"]*)"|'([^']*)')\s*:""")


def _strip_noise(src, strings=True):
	"""Blank out comments - and, with `strings`, string bodies too.

	Every character position is kept, because the reader below works on offsets
	into the real source. A brace inside a comment or a string must not be
	counted, which is what the `strings=True` copy is for; the `strings=False`
	copy keeps string CONTENT readable, which is how an endpoint path written
	inside quotes is still found while a commented-out one is not.
	"""
	out = list(src)
	i, n = 0, len(src)
	while i < n:
		c = src[i]
		if c == "/" and i + 1 < n and src[i + 1] == "/":
			while i < n and src[i] != "\n":
				out[i] = " "
				i += 1
		elif c == "/" and i + 1 < n and src[i + 1] == "*":
			out[i] = out[i + 1] = " "
			i += 2
			while i < n and not (src[i] == "*" and i + 1 < n and src[i + 1] == "/"):
				if src[i] != "\n":
					out[i] = " "
				i += 1
			if i < n:
				out[i] = out[i + 1] = " "
				i += 2
		elif strings and c in "\"'`":
			quote = c
			i += 1
			while i < n and src[i] != quote:
				if src[i] == "\\":
					out[i] = " "
					i += 1
					if i < n:
						out[i] = " "
						i += 1
					continue
				if src[i] != "\n":
					out[i] = " "
				i += 1
			if i < n:
				i += 1
		else:
			i += 1
	return "".join(out)


def _literal_end(clean, start):
	"""Index just past the `}` matching the `{` at `start`, or None."""
	depth = 0
	for i in range(start, len(clean)):
		if clean[i] == "{":
			depth += 1
		elif clean[i] == "}":
			depth -= 1
			if depth == 0:
				return i + 1
	return None


def _follows_a_separator(clean, i, start):
	"""True when position `i` begins a property, not the arm of a ternary.

	`{ half_day_date: hd ? fd : null }` has two colons in it and only one key.
	A property name is preceded - past whitespace - by the opening brace or by
	a comma. `fd` is preceded by a `?`, so it is a value, not a name.
	"""
	j = i - 1
	while j > start and clean[j] in " \t\r\n":
		j -= 1
	return j <= start or clean[j] in ",{"


def _object_keys(src, clean, start):
	"""Top-level key names of the object literal whose `{` is at `start`.

	Returns None when the literal does not close - an unreadable file must not
	silently produce an empty key set.
	"""
	end = _literal_end(clean, start)
	if end is None:
		return None
	keys, depth = [], 0
	i = start
	while i < end:
		c = clean[i]
		if c in "{[(":
			depth += 1
			if depth == 1 and c == "{":
				i += 1
				continue
		elif c in "}])":
			depth -= 1
		elif depth == 1:
			m = _KEY_RE.match(clean, i)
			if m and _follows_a_separator(clean, i, start):
				# The key text comes from the REAL source: quoted keys are
				# blanked in `clean`.
				keys.append(next(g for g in m.groups() if g is not None)
				            if m.group(1) else src[m.start():m.end() - 1].strip().strip("\"'"))
				i = m.end()
				continue
		i += 1
	return keys


# ── The call shapes we read ────────────────────────────────────────────────
#
# (helper name, how the first argument becomes an endpoint). Everything else
# about a call is ignored; only argument 1 and argument 2 matter.
_CALLS = (
	# next-*.js: ctx.api(CONST_OR_LITERAL, { ... })
	(re.compile(r"\bctx\.api\s*\("), "resolve"),
	# portal.js: api("short_name", { ... })  ->  alvoraa_portal.hr_api.<name>
	(re.compile(r"(?<![.\w$])api\s*\("), "hr_api"),
	# portal.js: gpFetch("full.endpoint.path", { ... })
	(re.compile(r"\bgpFetch\s*\("), "resolve"),
	# portal.js: pf("kra_api.get_my_kras", { ... }) -> PF + it
	(re.compile(r"(?<![.\w$])pf\s*\("), "pf"),
)

_CONST_RE = re.compile(
	r"""\b(?:var|let|const)\s+([A-Z][A-Z0-9_]*)\s*=\s*["'](alvoraa_portal\.[^"']+)["']""")
_PF_RE = re.compile(r"""\bPF\s*=\s*["'](alvoraa_portal\.[a-z_]+\.)["']""")

# next-inbox.js's ACTIONS table: the endpoint and its arguments are two
# properties of one object, and the arguments come back from a function.
_ACTION_RE = re.compile(
	r"""approve\s*:\s*["'](alvoraa_portal\.[^"']+)["']\s*,\s*args\s*:\s*function[^{]*\{""")


def _first_arg_and_object(src, clean, open_paren):
	"""Split `helper(A, {...})`. Returns (text of A, index of `{`) or (A, None)."""
	depth, i, n = 0, open_paren, len(clean)
	comma = None
	while i < n:
		c = clean[i]
		if c in "([{":
			depth += 1
		elif c in ")]}":
			depth -= 1
			if depth == 0:
				break
		elif c == "," and depth == 1:
			comma = i
			break
		i += 1
	if comma is None:
		return src[open_paren + 1:i].strip(), None
	first = src[open_paren + 1:comma].strip()
	j = comma + 1
	while j < n and clean[j] in " \t\r\n":
		j += 1
	return first, (j if j < n and clean[j] == "{" else None)


def _call_sites(path):
	"""[(endpoint, keys_or_None, line)] for one file. keys None = args not a literal."""
	src = open(path, encoding="utf-8-sig").read()
	clean = _strip_noise(src)
	# Comments blanked, strings kept. The endpoint paths this reader looks for
	# live INSIDE quotes, so searching `clean` for them found nothing - which is
	# how the whole of next-inbox.js's ACTIONS table went unread on the first
	# run while the test still passed. Same offsets, both copies.
	quoted = _strip_noise(src, strings=False)

	consts = {m.group(1): m.group(2) for m in _CONST_RE.finditer(quoted)}
	pf = _PF_RE.search(quoted)
	pf_prefix = pf.group(1) if pf else None

	def line_of(idx):
		return src.count("\n", 0, idx) + 1

	def resolve(text, mode):
		text = text.strip()
		lit = re.fullmatch(r"""["'](alvoraa_portal\.[a-z_0-9.]+)["']""", text)
		if mode == "hr_api":
			short = re.fullmatch(r"""["']([a-z_0-9]+)["']""", text)
			return "alvoraa_portal.hr_api." + short.group(1) if short else None
		if mode == "pf":
			short = re.fullmatch(r"""["']([a-z_0-9.]+)["']""", text)
			return (pf_prefix + short.group(1)) if (short and pf_prefix) else None
		if lit:
			return lit.group(1)
		return consts.get(text)

	found = []
	for pattern, mode in _CALLS:
		for m in pattern.finditer(clean):
			open_paren = clean.index("(", m.end() - 1)
			first, brace = _first_arg_and_object(src, clean, open_paren)
			endpoint = resolve(first, mode)
			if not endpoint:
				continue
			keys = _object_keys(src, clean, brace) if brace is not None else None
			found.append((endpoint, keys, line_of(m.start())))

	for m in _ACTION_RE.finditer(quoted):
		brace = clean.index("{", m.end() - 1)
		body_end = _literal_end(clean, brace)
		ret = clean.find("return", brace, body_end or len(clean))
		if ret == -1:
			continue
		obj = clean.find("{", ret, body_end or len(clean))
		if obj == -1:
			continue
		found.append((m.group(1), _object_keys(src, clean, obj), line_of(m.start())))

	return found


def _js_files():
	base = frappe.get_app_path("alvoraa_portal")
	for rel in JS_DIRS:
		d = os.path.join(base, rel)
		for fn in sorted(os.listdir(d)):
			if fn.endswith(".js"):
				yield fn, os.path.join(d, fn)


# One `inspect` per distinct endpoint, not per call site.
_SIG_CACHE = {}


def _signature(endpoint):
	"""(all parameter names, required names, takes **kwargs) or None if unknown."""
	try:
		fn = frappe.get_attr(endpoint)
	except Exception:
		return None
	try:
		sig = inspect.signature(fn)
	except (TypeError, ValueError):
		return None
	names, required, var_kw = set(), set(), False
	for p in sig.parameters.values():
		if p.kind is inspect.Parameter.VAR_KEYWORD:
			var_kw = True
			continue
		if p.kind is inspect.Parameter.VAR_POSITIONAL:
			continue
		names.add(p.name)
		if p.default is inspect.Parameter.empty:
			required.add(p.name)
	return names, required, var_kw


class TestTheBrowserSendsTheNamesTheServerDeclares(FrappeTestCase):
	"""One read of the portal's JavaScript, three questions asked of it."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.files = dict(_js_files())
		cls.sites = {}
		for name, path in cls.files.items():
			cls.sites[name] = _call_sites(path)

	# ── The guards: this test may not quietly check less than it says ──

	def test_every_file_it_claims_to_read_is_there(self):
		missing = [f for f in REQUIRED_FILES if f not in self.files]
		self.assertEqual(
			missing, [],
			"These files are named in REQUIRED_FILES but are not on disk, so "
			"this check is reading less than it claims: %s" % missing)

	def test_it_still_finds_the_calls(self):
		total = sum(len(v) for v in self.sites.values())
		self.assertGreaterEqual(
			total, MIN_CALL_SITES,
			"Only %d call sites were read, below the pinned floor of %d. Either "
			"calls were deleted, or they were rewritten into a shape this reader "
			"cannot parse - in which case they are no longer checked and the "
			"reader must be taught the new shape, not the floor lowered."
			% (total, MIN_CALL_SITES))

	def test_no_endpoint_is_named_but_never_read(self):
		"""A method path in the source that no call site matched is unchecked."""
		called = {e for v in self.sites.values() for (e, _k, _l) in v}
		orphans = {}
		for name, path in self.files.items():
			src = open(path, encoding="utf-8-sig").read()
			for endpoint in set(ENDPOINT_RE.findall(src)):
				if endpoint in called or endpoint in NO_ARG_CALL:
					continue
				orphans.setdefault(endpoint, set()).add(name)
		self.assertEqual(
			orphans, {},
			"These endpoints are named in the portal's JavaScript but no call "
			"site was read for them, so their arguments are unchecked. Teach the "
			"reader the shape, or add the endpoint to NO_ARG_CALL with a "
			"reason:\n" + "\n".join("  %s  in %s" % (e, ", ".join(sorted(f)))
			                        for e, f in sorted(orphans.items())))

	def test_no_arg_call_entries_all_give_a_reason(self):
		for endpoint, why in NO_ARG_CALL.items():
			self.assertTrue(why and why.strip(),
			                "%s is excused with no reason given." % endpoint)

	# ── The two real checks ──

	def test_no_call_leaves_out_an_argument_the_server_requires(self):
		"""The `action_leave` bug. A TypeError for every user, every time."""
		bad = []
		for name, sites in sorted(self.sites.items()):
			for endpoint, keys, line in sites:
				if keys is None:
					continue
				sig = self._sig_or_skip(endpoint)
				if sig is None:
					continue
				_names, required, _var_kw = sig
				missing = sorted(required - set(keys))
				if missing:
					bad.append("  %s:%d  %s()  never sent: %s  (browser sends: %s)"
					           % (name, line, endpoint, ", ".join(missing),
					              ", ".join(sorted(keys)) or "nothing"))
		self.assertEqual(
			bad, [],
			"The browser leaves out an argument the server requires. Frappe "
			"drops what it does not recognise, so the call reaches Python "
			"missing a positional argument and raises TypeError:\n"
			+ "\n".join(bad))

	def test_no_call_sends_a_name_the_server_does_not_declare(self):
		"""The quiet one. Nothing raises; the value is dropped on the floor."""
		bad = []
		for name, sites in sorted(self.sites.items()):
			for endpoint, keys, line in sites:
				if keys is None:
					continue
				sig = self._sig_or_skip(endpoint)
				if sig is None:
					continue
				names, _required, var_kw = sig
				if var_kw:
					continue
				extra = sorted(set(keys) - names)
				if extra:
					bad.append("  %s:%d  %s()  has no parameter for: %s"
					           % (name, line, endpoint, ", ".join(extra)))
		self.assertEqual(
			bad, [],
			"The browser sends names the server does not declare. "
			"`frappe.get_newargs` drops them silently, so whatever the person "
			"typed never arrives and nothing goes wrong loudly:\n" + "\n".join(bad))

	def _sig_or_skip(self, endpoint):
		if endpoint not in _SIG_CACHE:
			_SIG_CACHE[endpoint] = _signature(endpoint)
		return _SIG_CACHE[endpoint]
