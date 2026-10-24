/* Slice 069: the wall chart in a real browser - the things jsdom cannot
 * measure. NOT part of CI: it needs Playwright and Chromium.
 *
 * No site and no container: it opens the portal page built from THIS
 * checkout (scripts/lib/portal_source.js, the same expansion the CI checks
 * read) with every server call answered empty, and loads the slice's
 * invented fixtures into POS the way position_table would.
 *
 *   PLAYWRIGHT=<path to playwright> node scripts/check_wall_chart_browser.js [OUT_DIR]
 *
 * It reports, and fails on:
 *   sizes    name size at DTC's shape on A3 / A1 / A0, HR copy off and on
 *            (the AC-32 kill line: All on A1 must reach 8 pt)
 *   search   the two-drawing layout is within 0.5 pt of trying every wrap
 *            for real (strategy 2.2)
 *   lines    the 064 connector rule on the paper: every line joins a box to
 *            its real manager, every box is joined (AC-22, AC-50)
 *   light    the paper is white with #2D2622 text in the dark theme (AC-23)
 */
const { chromium } = require(process.env.PLAYWRIGHT || "playwright");
const fs = require("fs");
const path = require("path");
const { readPortalSource } = require("./lib/portal_source");
const F = require("./lib/wall_chart_fixture");

const OUT = process.argv[2] || "";
const fails = [];
const log = (...a) => console.log(...a);
const must = (what, cond, detail) => { if (!cond) fails.push(what + (detail ? " - " + detail : "")); log((cond ? "  ok    " : "  FAIL  ") + what + (detail ? "  (" + detail + ")" : "")); };

/* Runs in the page: the 064 connector rule, pointed at the paper. Boxes are
   known by their title (the fixtures' titles are unique); a box's real
   parent is its seat's reports_to. */
function paperAudit() {
  const wall = document.querySelector("#pos-wall-print .pos-wall");
  const byTitle = {}, byId = {};
  POS.rows.forEach((r) => { byTitle[r.title] = r; byId[r.id] = r; });
  const idOf = (box) => { const t = box && box.querySelector(".ti"); return t ? t.textContent : null; };
  const realParent = (t) => { const r = byTitle[t]; const p = r && byId[r.reports_to]; return p ? p.title : null; };
  const boxes = [...wall.querySelectorAll(".oc-box")];
  const ownerOf = (el) => { const br = el.closest(".oc-branch"); const box = br && br.querySelector(":scope > .oc-node > .oc-box"); return box ? idOf(box) : null; };
  const hostOf = (el) => {
    let host = el.closest(".oc-hang").parentElement;
    if (host.classList.contains("oc-hang-slot")) host = host.parentElement;
    return host;
  };
  const segs = [];
  wall.querySelectorAll(".oc-kids, .oc-kids > .oc-branch, .oc-hang, .oc-hang-item").forEach((el) => {
    ["::before", "::after"].forEach((ps) => {
      const cs = getComputedStyle(el, ps);
      if (!cs || cs.content === "none" || cs.display === "none") return;
      const w = parseFloat(cs.width), h = parseFloat(cs.height);
      if (!(w > 0 && h > 0)) return;
      const r = el.getBoundingClientRect(), left = r.left + parseFloat(cs.left), top = r.top + parseFloat(cs.top);
      const host = (el.classList.contains("oc-hang") || el.classList.contains("oc-hang-item")) ? hostOf(el)
        : (el.classList.contains("oc-kids") ? el.parentElement : el.parentElement.parentElement);
      segs.push({ owner: ownerOf(host.querySelector(":scope > .oc-node") || host), x1: left, y1: top, x2: left + w, y2: top + h });
    });
  });
  wall.querySelectorAll(".pos-wall-bar").forEach((bar) => {
    const r = bar.getBoundingClientRect(), host = hostOf(bar);
    segs.push({ owner: ownerOf(host.querySelector(":scope > .oc-node") || host), x1: r.left, y1: r.top, x2: r.right, y2: r.bottom });
  });
  const linked = {}, bad = [];
  const hit = (s, r) => s.x1 < r.right + 0.5 && s.x2 > r.left - 0.5 && s.y1 < r.bottom + 0.5 && s.y2 > r.top - 0.5;
  segs.forEach((s) => boxes.forEach((b) => {
    const id = idOf(b), r = b.getBoundingClientRect();
    if (!hit(s, r)) return;
    if (id === s.owner) { if (s.y1 < r.bottom - 2) bad.push("line runs through its own box " + id); return; }
    const onTop = (s.y2 <= r.top + 2 && s.y2 >= r.top - 2)
      || (s.y2 - s.y1 <= 3 && s.x2 <= r.left + 2 && s.x2 >= r.left - 2 && s.y1 >= r.top && s.y1 <= r.bottom);
    if (realParent(id) === s.owner && onTop) { linked[id] = 1; return; }
    bad.push(`line from ${s.owner} touches ${id} (parent ${realParent(id)})${onTop ? "" : ", not on its top or left edge"}`);
  }));
  const shown = {};
  boxes.forEach((b) => { shown[idOf(b)] = 1; });
  boxes.forEach((b) => {
    const id = idOf(b), rp = realParent(id);
    if (rp && shown[rp] && !linked[id]) bad.push("linked to nobody: " + id);
  });
  return { boxes: boxes.length, segs: segs.length, bad };
}

(async () => {
  const html = readPortalSource();
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", (e) => { if (!/Unexpected token '\{'/.test(e.message)) errs.push(e.message); });
  await page.addInitScript(() => {
    window.fetch = () => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ message: {} }), text: () => Promise.resolve("") });
    window.frappe = { call: () => Promise.resolve({ message: {} }), csrf_token: "x", boot: {}, ui: {}, _messages: {}, utils: { escape_html: (s) => s } };
  });
  // A real origin, so the page's localStorage works as it does on a site.
  await page.route("http://wall.test/**", (r) => r.request().url() === "http://wall.test/hrms-employee"
    ? r.fulfill({ contentType: "text/html", body: html }) : r.fulfill({ status: 404, body: "" }));
  await page.goto("http://wall.test/hrms-employee", { waitUntil: "load" });
  await page.waitForTimeout(300);
  const load = (p) => page.evaluate((p) => {
    POS.rows = p.rows; POS.today = p.as_at; POS.may_see_leaving = !!p.may_see_leaving; POS.may_edit = !!p.may_edit;
    POS.unseated = "unseated" in p ? p.unseated : null; POS.active_people = p.active_people || 0; POS.ungrouped = {};
  }, p);
  const measure = (start, levels, vacant, hr) => page.evaluate(([s, l, v, h]) => {
    const start = s === "top" ? "top" : POS.rows.find((r) => r.title === s).id;
    const L = posWallLayout(posWallCopy(start, l, v, h));
    const pt = {};
    POS_WALL_ORDER.forEach((p) => { pt[p] = posWallPlan(L, p, "one", h).pt; });
    const sev = posWallPlan(L, "A3", "several", h);
    return { w: L.w, h: L.h, K: L.K, KU: L.KU, ms: L.ms, pt, sheetsA3: sev.cols * sev.rows + " (" + sev.cols + " x " + sev.rows + ")" };
  }, [start, levels, vacant, hr]);
  const f1 = (n) => (Math.floor(n * 10) / 10).toFixed(1);

  /* ── sizes (AC-32) ───────────────────────────────────────────────────── */
  log("\nName sizes at DTC's shape (F-DTC90: 90 seats, 363 people), one sheet, Show Vacant on");
  await load(F.dtc90());
  const rows = [];
  for (const [label, lv, hr] of [["2 levels, HR copy off", 2, false], ["All, HR copy off", 99, false],
                                  ["2 levels, HR copy on", 2, true], ["All, HR copy on", 99, true]]) {
    const m = await measure("top", lv, true, hr);
    rows.push([label, m]);
    log(`  ${label.padEnd(24)} ${m.w} x ${m.h} px  K ${m.K} KU ${m.KU}  A4 ${f1(m.pt.A4)}  A3 ${f1(m.pt.A3)}  A2 ${f1(m.pt.A2)}  A1 ${f1(m.pt.A1)}  A0 ${f1(m.pt.A0)} pt  several A3: ${m.sheetsA3}  ${m.ms} ms`);
  }
  const allA1 = rows[1][1].pt.A1;
  must("AC-32 kill line: All on A1 reaches 8 pt with the full box", allA1 >= 8, f1(allA1) + " pt");

  /* every seat's designation different from its title: the fullest box */
  await load(Object.assign(F.dtc90(), { rows: F.dtc90().rows.map((r) => Object.assign({}, r, { designation: "Designation of " + r.title.slice(0, 12) })) }));
  const worst = await measure("top", 99, true, false);
  log(`  All, every designation shown (worst case)  ${worst.w} x ${worst.h} px  A1 ${f1(worst.pt.A1)}  A0 ${f1(worst.pt.A0)} pt`);

  /* ── the two-drawing choice against trying every wrap for real ──────── */
  for (const [label, payload] of [["DTC", F.dtc90()], ["10x DTC (891 seats)", F.scaled(10)]]) {
    await load(payload);
    const r = await page.evaluate(() => {
      const copy = posWallCopy("top", 99, true, false);
      const t0 = performance.now();
      const L = posWallLayout(copy);
      const ours = performance.now() - t0;
      const host = posWallHolder();
      let best = null;
      const t1 = performance.now();
      POS_WALL_KS.forEach((K) => { for (let KU = 2; KU <= Math.min(K, 5); KU++) {
        host.innerHTML = posWallHtml(copy, K, KU); posWallBars(host);
        const rc = host.firstChild.getBoundingClientRect();
        const pt = posWallPlan({ w: Math.ceil(rc.width), h: Math.ceil(rc.height) }, "A1", "one", false).pt;
        if (!best || pt > best.pt) best = { K, KU, pt };
      } });
      const full = performance.now() - t1;
      return { ours: posWallPlan(L, "A1", "one", false).pt, K: L.K, KU: L.KU, best, msOurs: Math.round(ours), msFull: Math.round(full) };
    });
    log(`  ${label}: two drawings give A1 ${f1(r.ours)} pt (K ${r.K}, KU ${r.KU}) in ${r.msOurs} ms; every wrap drawn gives ${f1(r.best.pt)} pt (K ${r.best.K}, KU ${r.best.KU}) in ${r.msFull} ms`);
    must(label + ": the two-drawing layout is within 0.5 pt of the full search", r.ours >= r.best.pt - 0.5, f1(r.ours) + " vs " + f1(r.best.pt));
  }

  /* ── lines on paper (AC-22, AC-50) ──────────────────────────────────── */
  const severalTops = F.dtc90();
  const lh = { id: "POS-LH", title: "Loose Head", reports_to: "", branch: "Noida", department: "Sales", designation: "Loose Head", company: "Sample Fashions Pvt Ltd", status: "Active", people: [{ name: "Lata Loose" }] };
  severalTops.rows.push(lh, Object.assign({}, lh, { id: "POS-LA", title: "Loose A", reports_to: "POS-LH", designation: "Loose A" }),
                        Object.assign({}, lh, { id: "POS-LB", title: "Loose B", reports_to: "POS-LH", designation: "Loose B", people: [] }));
  for (const [label, payload, lv] of [["2 levels", F.dtc90(), 2], ["All", F.dtc90(), 99], ["several tops, All", severalTops, 99],
                                       ["several tops, 2 levels", severalTops, 2], ["Owner (loose boxes)", F.owner(), 99],
                                       ["Back Office Manager, All", F.dtc90(), "Back Office Manager"]]) {
    await load(payload);
    const a = await page.evaluate((lv) => {
      const start = typeof lv === "string" ? POS.rows.find((r) => r.title === lv).id : "top";
      posWallLayout(posWallCopy(start, typeof lv === "string" ? 99 : lv, true, false));
      return null;
    }, lv);
    const r = await page.evaluate(paperAudit);
    must(`AC-22 lines on paper, ${label}: ${r.boxes} boxes, ${r.segs} lines, 0 false or missing links`, !r.bad.length, r.bad.slice(0, 3).join(" | "));
    if (OUT) await page.evaluate(() => { const h = document.getElementById("pos-wall-print"); h.style.cssText = "position:static;visibility:visible"; });
    if (OUT) { await page.locator("#pos-wall-print .pos-wall").screenshot({ path: path.join(OUT, "paper-" + label.replace(/[^a-z0-9]+/gi, "-") + ".png") }); await page.evaluate(() => { document.getElementById("pos-wall-print").style.cssText = ""; }); }
  }

  /* ── always light (AC-23) ───────────────────────────────────────────── */
  await load(F.dtc90());
  const dark = await page.evaluate(() => {
    document.documentElement.setAttribute("data-theme", "dark");
    posWallLayout(posWallCopy("top", 2, true, false));
    const w = document.querySelector("#pos-wall-print .pos-wall"), cs = getComputedStyle(w);
    const root = getComputedStyle(w.querySelector(".oc-node.root > .oc-box"));
    const box = getComputedStyle(w.querySelector(".oc-box"));
    document.documentElement.removeAttribute("data-theme");
    return { bg: cs.backgroundColor, color: cs.color, boxBg: box.backgroundColor, rootBorder: root.borderTopWidth + " " + root.borderTopColor };
  });
  must("AC-23: dark theme, the paper is white with #2D2622 text", dark.bg === "rgb(255, 255, 255)" && dark.color === "rgb(45, 38, 34)" && dark.boxBg === "rgb(255, 255, 255)", JSON.stringify(dark));
  must("AC-23: the starting box has a 2 px #5B4B8A border", dark.rootBorder === "2px rgb(91, 75, 138)", dark.rootBorder);

  must("no script errors", !errs.length, errs.slice(0, 3).join(" | "));
  await browser.close();
  log(fails.length ? `\nwall chart (browser): ${fails.length} FAILED` : "\nwall chart (browser): all passed");
  process.exit(fails.length ? 1 : 0);
})();
