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
ROOT = r"c:\Surbhi-Git\hr-app\alvoraa_portal\alvoraa_portal"
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


def prep(page):
	src = open(os.path.join(ROOT, "www", page + ".html"), encoding="utf-8").read()
	m = re.search(r'\{%\s*include\s*"([^"]+)"\s*%\}', src)
	if m:
		src = src[:m.start()] + open(os.path.join(ROOT, *m.group(1).split("/")),
		                             encoding="utf-8").read() + src[m.end():]
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
