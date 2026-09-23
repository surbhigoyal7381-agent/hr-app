"""Render every portal page in a real browser and find text nobody can read.

This exists because the static checker was not enough. It compares hex values,
and the worst bug of the design pass used none: the check-in hero was
`rgba(255,255,255,.5)` on a background that flattening a gradient had turned
white. White on white, and nothing flagged it.

This measures what the browser actually paints - the computed colour of each
piece of text against the nearest ancestor that paints a background - in both
themes. It found five separate instances of the same mistake across four pages.

NOT in CI: it needs a browser (`python -m playwright install chromium`). Run it
by hand after any change to colour or background:

    python scripts/check_contrast_rendered.py
"""

import io, os, re, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
# Resolved from this file, not hard-coded, so the check reads the checkout or
# worktree it was actually run from (slice 034 US-10).
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "alvoraa_portal", "alvoraa_portal")
PAGES = ["hrms-employee", "driver-portal", "vendor-portal", "alvoraa-admin", "alvoraa-login"]

JS = """() => {
  const lum = (r,g,b) => {
    const f = v => { v/=255; return v<=.03928 ? v/12.92 : Math.pow((v+.055)/1.055, 2.4); };
    return .2126*f(r)+.7152*f(g)+.0722*f(b);
  };
  const parse = s => (s.match(/[\\d.]+/g)||[]).map(Number);
  // The colour actually behind an element: walk up until something paints.
  const bgOf = el => {
    for (let n = el; n && n !== document.documentElement; n = n.parentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c.length >= 3 && (c[3] === undefined || c[3] > .5)) return c;
    }
    const b = parse(getComputedStyle(document.body).backgroundColor);
    return b.length >= 3 ? b : [255,255,255];
  };
  const out = [];
  document.querySelectorAll('*').forEach(el => {
    if (el.children.length) return;                       // leaf nodes only
    const txt = (el.textContent||'').trim();
    if (!txt) return;
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) return;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return;
    const fg = parse(s.color); if (fg.length < 3) return;
    const a = fg[3] === undefined ? 1 : fg[3];
    const bg = bgOf(el);
    // Flatten the text colour over its background before comparing.
    const mix = [0,1,2].map(i => fg[i]*a + bg[i]*(1-a));
    const L1 = lum(mix[0],mix[1],mix[2]) + .05, L2 = lum(bg[0],bg[1],bg[2]) + .05;
    const ratio = L1 > L2 ? L1/L2 : L2/L1;
    if (ratio < 2.0) {
      out.push({t: txt.slice(0,40), ratio: Math.round(ratio*100)/100,
                sel: el.tagName.toLowerCase() + '.' + String(el.className||'').slice(0,30)});
    }
  });
  return out.slice(0, 10);
}"""


# Every include, not just the first. The page used to carry one include tag
# (design_system.html); since slice 034 US-10 it carries several more, and the
# blanket "strip every {% %}" below would have deleted them - leaving this check
# measuring an empty page and passing. Expanding them all is the whole guard.
# OPS-31. The portal's styles left the Jinja includes and became static files
# under public/, loaded with <link href="/assets/...">. Stripping those, as the
# blanket Jinja strip below once did to the include tags, would leave this check
# measuring an unstyled page - every colour would come out 1.00:1 and the check
# would report a disaster that is not real, or a healthy page as broken. So the
# asset tags are pasted back in as <style> blocks, the same way the shared
# expander does it for the tests.
ASSET_LINK_RE = re.compile(
	r'<link[^>]*href="/assets/alvoraa_portal/(css/ess/[^"?]+)(?:\?[^"]*)?"[^>]*>')
ASSET_SCRIPT_RE = re.compile(
	r'<script[^>]*src="/assets/alvoraa_portal/(js/ess/[^"?]+)(?:\?[^"]*)?"[^>]*>\s*</script>')


# The markup is split by area into parts that hold no Jinja and are pasted in by
# {{ ess_part("home") }} rather than compiled (alvoraa_portal/ess_parts.py). The
# blanket "{{ ... }} becomes empty" substitution below would delete every one of
# them and leave this check measuring a page with no content - which is exactly
# what it did for one run: it reported nought unreadable elements on a page that
# was not there. The parts are pasted back in first.
PART_RE = re.compile(r'\{\{\s*ess_part\(\s*"([a-z0-9-]+)"\s*\)\s*\}\}')


def _expand_parts(src):
	def swap(m):
		path = os.path.join(ROOT, "templates", "includes", "ess", "parts",
		                    m.group(1) + ".html")
		with open(path, encoding="utf-8") as fh:
			return fh.read()

	out = PART_RE.sub(swap, src)
	if "hrms-employee" in src and out == src and "ess_part(" in src:
		raise RuntimeError("markup parts were not expanded")
	return out


def _expand_assets(src):
	def swap(m, tag):
		path = os.path.join(ROOT, "public", *m.group(1).split("/"))
		with open(path, encoding="utf-8") as fh:
			return "<%s>%s</%s>" % (tag, fh.read(), tag)

	src = ASSET_LINK_RE.sub(lambda m: swap(m, "style"), src)
	return ASSET_SCRIPT_RE.sub(lambda m: swap(m, "script"), src)


# Thirty, not eight: driver-portal.html includes design_system.html four times
# and each copy pulls in brand_color.html, which is eight substitutions on its
# own - the old limit fired on a healthy page.
def _expand_includes(src):
	for _ in range(30):
		m = re.search(r'\{%\s*include\s*"([^"]+)"\s*%\}', src)
		if not m:
			return src
		path = os.path.join(ROOT, *m.group(1).split("/"))
		with open(path, encoding="utf-8") as fh:
			src = src[:m.start()] + fh.read() + src[m.end():]
	raise RuntimeError("include files are nested too deep")


def prep(page):
	src = open(os.path.join(ROOT, "www", page + ".html"), encoding="utf-8").read()
	src = _expand_parts(_expand_assets(_expand_includes(src)))
	src = re.sub(r"\{%\s*extends[^%]*%\}|\{%\s*block\s+\w+\s*%\}|\{%\s*endblock[^%]*%\}", "", src)
	src = re.sub(r"\{#[\s\S]*?#\}", "", src)
	V = {"tenant_name": "PP Jewellers", "primary_color": "#5B4B8A",
	     "support_email": '"a@b.c"'}
	src = re.sub(r"\{\{([^}]*)\}\}",
	             lambda mm: str(V.get(mm.group(1).strip().split("|")[0].strip(), "")), src)
	return re.sub(r"\{%[^%]*%\}", "", src)


from playwright.sync_api import sync_playwright

bad_total = 0
with sync_playwright() as p:
	b = p.chromium.launch()
	for page in PAGES:
		body = prep(page)
		for theme in ("light", "dark"):
			fn = os.path.join(os.path.dirname(os.path.abspath(__file__)),
			                  "_c_%s_%s.html" % (page, theme))
			# Styles belong in <head>. The admin console replaces body.innerHTML
			# on a non-control-plane site, which wiped a stylesheet left in the
			# body and made every element on that page look unreadable. Frappe
			# puts these in head via {% block head_include %}; the harness must
			# match, or it reports faults that do not exist.
			import re as _re
			styles = "".join(_re.findall(r"<style>[\s\S]*?</style>", body))
			stripped = _re.sub(r"<style>[\s\S]*?</style>", "", body)
			open(fn, "w", encoding="utf-8").write(
				'<!doctype html><html data-theme="%s"><head><meta charset="utf-8">%s'
				"</head><body>%s</body></html>" % (theme, styles, stripped))
			pg = b.new_page(viewport={"width": 1366, "height": 950})
			pg.goto("file:///" + fn.replace("\\", "/"))
			pg.wait_for_timeout(900)
			bad = pg.evaluate(JS)
			pg.close()
			mark = "ok" if not bad else "%d UNREADABLE" % len(bad)
			print("%-18s %-5s  %s" % (page, theme, mark))
			for x in bad[:5]:
				print("      %5.2f:1  %-32s %s" % (x["ratio"], x["sel"][:32], x["t"]))
			bad_total += len(bad)
	b.close()
print("\ntotal unreadable elements: %d" % bad_total)
