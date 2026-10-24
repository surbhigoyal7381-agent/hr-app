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
 * The repository pins no Playwright. Use one whose browser is installed:
 * a newer Playwright than its downloaded Chromium stops at launch ("Executable
 * doesn't exist"). Run on 25 Oct 2026 with Playwright 1.59.1 + Chromium.
 * The 10x step takes several minutes on its own.
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
    ? r.fulfill({ contentType: "text/html; charset=utf-8", body: html }) : r.fulfill({ status: 404, body: "" }));
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
      // The layout keeps only markup (review m1); draw it back to audit it.
      const html = posWallLayout(posWallCopy(start, typeof lv === "string" ? 99 : lv, true, false)).html; posWallHolder().innerHTML = html;
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
    const html = posWallLayout(posWallCopy("top", 2, true, false)).html; posWallHolder().innerHTML = html;
    const w = document.querySelector("#pos-wall-print .pos-wall"), cs = getComputedStyle(w);
    const root = getComputedStyle(w.querySelector(".oc-node.root > .oc-box"));
    const box = getComputedStyle(w.querySelector(".oc-box"));
    document.documentElement.removeAttribute("data-theme");
    return { bg: cs.backgroundColor, color: cs.color, boxBg: box.backgroundColor, rootBorder: root.borderTopWidth + " " + root.borderTopColor };
  });
  must("AC-23: dark theme, the paper is white with #2D2622 text", dark.bg === "rgb(255, 255, 255)" && dark.color === "rgb(45, 38, 34)" && dark.boxBg === "rgb(255, 255, 255)", JSON.stringify(dark));
  must("AC-23: the starting box has a 2 px #5B4B8A border", dark.rootBorder === "2px rgb(91, 75, 138)", dark.rootBorder);

  /* ── the panel at DTC's size: warning words and timings (AC-33, AC-35) ── */
  await load(F.dtc90());
  await page.evaluate(() => { window.print = () => { window.__printed = (window.__printed || 0) + 1; }; POS.wall = null; posWallOpen(); });
  const waitL = () => page.waitForFunction(() => POS.wall && POS.wall.L, null, { timeout: 30000 });
  await waitL();
  await page.evaluate(() => { posWallSet("levels", "3"); });
  await waitL();
  const warn = await page.evaluate(() => document.querySelector(".pos-wall-result").innerText.replace(/\s+/g, " "));
  log("  All on A3, result box: " + warn);
  must("AC-33: the warning names the paper that reaches 8 pt and the sheets", /Warning: that is too small to read on a wall\./.test(warn)
       && /Use A1 \(names at 9 pt\)/.test(warn) && /Use 9 A3 sheets/.test(warn), warn);
  const timing = await page.evaluate(async () => {
    const frame = () => new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0)));
    const out = {};
    const med = (a) => a.slice().sort((x, y) => x - y)[Math.floor(a.length / 2)];
    const changes = { paper: ["A2", "A1", "A0", "A4", "A3"], sheets: ["several", "one", "several", "one", "several"],
                      start: [], levels: ["2", "3", "2", "3", "2"], vacant: [false, true, false, true, false], hr: [true, false, true, false, true] };
    const t = posKids(POS.rows);
    changes.start = ["top"].concat(t.kids[t.roots[0].id].filter((r) => (t.kids[r.id] || []).length).slice(0, 4).map((r) => r.id));
    for (const k of Object.keys(changes)) {
      const words = [], done = [];
      for (const v of changes[k]) {
        POS.wall.fast = true;
        const t0 = performance.now();
        posWallSet(k, v);
        words.push(performance.now() - t0);
        while (!POS.wall.L) await frame();
        done.push(performance.now() - t0);
        await frame();
      }
      out[k] = { first: Math.round(med(words)), final: Math.round(med(done)) };
    }
    return out;
  });
  log("  AC-35 median of 5 changes, ms until the panel's words change / until the final line: "
      + Object.keys(timing).map((k) => `${k} ${timing[k].first}/${timing[k].final}`).join(", "));
  await page.evaluate(() => { posWallSet("start", "top"); });
  await waitL();
  await page.evaluate(() => { posWallSet("levels", "3"); });
  await waitL();
  must("AC-35: every change shows its line within 300 ms", Object.values(timing).every((x) => x.first <= 300 && x.final <= 300), JSON.stringify(timing));

  /* ── the PDF: page size in mm, page count (AC-37, AC-42 in Chromium, AC-45) ── */
  const pdfBox = (buf) => {
    const s = buf.toString("latin1");
    const m = /\/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]/.exec(s);
    return { w: Math.round(+m[1] * 25.4 / 72), h: Math.round(+m[2] * 25.4 / 72), pages: (s.match(/\/Type\s*\/Page[^s]/g) || []).length };
  };
  const PAPER = { A4: [210, 297], A3: [297, 420], A2: [420, 594], A1: [594, 841], A0: [841, 1189] };
  for (const paper of Object.keys(PAPER)) {
    for (const portrait of [false, true]) {
      await page.evaluate(([paper, portrait]) => {
        posWallSet("sheets", "one"); posWallSet("paper", paper);
        if (portrait) POS.wall.L = Object.assign({}, POS.wall.L, { w: 500, h: 2000 });
        posWallPrint();
      }, [paper, portrait]);
      const pdf = await page.pdf({ preferCSSPageSize: true, printBackground: true });
      const b = pdfBox(pdf);
      const want = portrait ? PAPER[paper] : [PAPER[paper][1], PAPER[paper][0]];
      must(`PDF ${paper} ${portrait ? "portrait" : "landscape"}: ${b.w} x ${b.h} mm, ${b.pages} page`,
           Math.abs(b.w - want[0]) <= 1 && Math.abs(b.h - want[1]) <= 1 && b.pages === 1, `wanted ${want.join(" x ")}`);
      if (OUT && paper === "A1" && !portrait) fs.writeFileSync(path.join(OUT, "wall-A1.pdf"), pdf);
      await page.evaluate(() => { window.dispatchEvent(new Event("afterprint")); POS.wall.key = ""; posWallSet("levels", "3"); });
      await waitL();
    }
  }
  /* several sheets: All on A3 */
  await page.evaluate(() => { posWallSet("paper", "A3"); posWallSet("sheets", "several"); posWallSet("hr", true); });
  await waitL();
  const tiles = await page.evaluate(() => { const P = posWallPlan(POS.wall.L, "A3", "several", true); posWallPrint(); return P.cols * P.rows; });
  /* while it prints: only the wall chart (AC-40) */
  await page.emulateMedia({ media: "print" });
  const only = await page.evaluate(() => ({
    others: [...document.querySelectorAll("body > :not(#pos-wall-print)")].filter((e) => e.getClientRects().length).length,
    sheets: [...document.querySelectorAll("#pos-wall-print .pos-wall-sheet")].filter((e) => e.getClientRects().length).length }));
  await page.emulateMedia({ media: "screen" });
  must(`AC-40: in print only the ${only.sheets} sheets show, nothing else`, only.others === 0 && only.sheets === tiles, JSON.stringify(only));
  const onScreen = await page.evaluate(() => getComputedStyle(document.getElementById("pos-wall-print")).visibility);
  must("AC-40: on screen the wall chart is never visible", onScreen === "hidden", onScreen);
  const sev = pdfBox(await page.pdf({ preferCSSPageSize: true, printBackground: true }));
  must(`AC-45/46: All on A3, several sheets: ${sev.pages} PDF pages for ${tiles} sheets, ${sev.w} x ${sev.h} mm`, sev.pages === tiles && sev.w === 420 && sev.h === 297);
  if (OUT) fs.writeFileSync(path.join(OUT, "wall-A3-sheets-hr.pdf"), await page.pdf({ preferCSSPageSize: true, printBackground: true }));
  await page.evaluate(() => { window.dispatchEvent(new Event("afterprint")); posCloseSheet(); });
  const after = pdfBox(await page.pdf({ preferCSSPageSize: true, printBackground: true }));
  must(`SEC-4: afterwards the portal's own A4 landscape rule is back (${after.w} x ${after.h} mm), as a payslip needs`, after.w === 297 && after.h === 210);

  /* ── 10x: several sheets (R-4) ──────────────────────────────────────── */
  await load(F.scaled(10));
  const big = await page.evaluate(async () => {
    POS.wall = null; posWallOpen();
    while (!POS.wall.L) await new Promise((r) => setTimeout(r, 20));
    posWallSet("levels", String(posWallLevels(posKids(POS.rows)).slice(-1)[0][0]));
    while (!POS.wall.L) await new Promise((r) => setTimeout(r, 20));
    posWallSet("paper", "A4"); posWallSet("sheets", "several");
    const P = posWallPlan(POS.wall.L, "A4", "several", false);
    const t0 = performance.now();
    posWallPrint();
    const build = performance.now() - t0;
    const t1 = performance.now();
    document.getElementById("pos-wall-print").getBoundingClientRect();
    const boxes = document.querySelectorAll("#pos-wall-print .oc-box").length;
    return { seats: POS.rows.length, sheets: P.cols * P.rows, across: P.cols, down: P.rows, build: Math.round(build), layout: Math.round(performance.now() - t1), boxes, htmlMB: (document.getElementById("pos-wall-print").innerHTML.length / 1e6).toFixed(1) };
  });
  const t2 = Date.now();
  const bigPdf = pdfBox(await page.pdf({ preferCSSPageSize: true, printBackground: true }));
  log(`  R-4, 10x (${big.seats} seats) on A4, several sheets: ${big.sheets} sheets (${big.across} x ${big.down}), ${big.boxes} boxes in the print page (${big.htmlMB} MB of markup); building it ${big.build} ms, laying it out ${big.layout} ms; Chromium's PDF of it ${Date.now() - t2} ms, ${bigPdf.pages} pages`);
  await page.evaluate(() => { window.dispatchEvent(new Event("afterprint")); posCloseSheet(); });

  /* ── Ctrl+P on the screen chart (AC-3, AC-3a) ───────────────────────── */
  const sent = F.dtc90({ sentinel: true });
  sent.unseated = [{ name: "Nomgr Person", branch: "Noida", no_manager: true }];
  // Opening the panel runs the page's own load, so position_table answers with the fixture.
  await page.evaluate((p) => { window.gpFetch = (m) => Promise.resolve(/position_table/.test(m) ? p : {}); switchPanel("positions"); }, sent);
  await page.waitForFunction(() => POS.rows.length > 0 && POS.unseated);
  const ctrlP = await page.evaluate(() => {
    const sb = document.getElementById("sb-name"); if (sb) sb.textContent = "PRINTER-SNTL";
    const sd = document.getElementById("sb-desig"); if (sd) sd.textContent = "ROLE-SNTL";
    document.getElementById("pos-f-view").value = "tree";
    POS.expanded = {}; POS.rows.forEach((r) => { POS.expanded[r.id] = true; }); posPaint();
    return { flags: document.querySelectorAll("#pos-body .oc-flag").length, tags: document.querySelectorAll("#pos-body .oc-tag").length,
             nomgr: document.querySelectorAll("#pos-body .pos-nomgr-row").length };
  });
  await page.emulateMedia({ media: "print" });
  const pr = await page.evaluate(() => {
    const vis = (s) => [...document.querySelectorAll(s)].filter((e) => e.getClientRects().length).length;
    return { titles: vis("#pos-body .oc-box .ti"), names: vis("#pos-body .oc-who"), banned: vis("#pos-body .oc-flag, #pos-body .oc-tag, .pos-nomgr-row, .private, [data-private]"),
             head: (document.querySelector("#pos-body .pos-printhead") || {}).innerText || "" };
  });
  await page.emulateMedia({ media: "screen" });
  log(`  Ctrl+P: on screen ${ctrlP.flags} flags, ${ctrlP.tags} tags, ${ctrlP.nomgr} HR box; in print ${pr.titles} seat titles, ${pr.names} name lines, ${pr.banned} of those visible; header "${pr.head.replace(/\s+/g, " ")}"`);
  must("AC-3: Ctrl+P prints the chart's seats and names", pr.titles > 20 && pr.names > 20);
  must("AC-3: and no flag, tag, HR box or private mark (there were some on screen)", pr.banned === 0 && ctrlP.flags > 0 && ctrlP.tags > 0 && ctrlP.nomgr > 0);
  must("AC-3a: the print header names nobody", !/PRINTER-SNTL|ROLE-SNTL|printed by/.test(pr.head) && /Positions/.test(pr.head) && /seats as at/.test(pr.head) && / on /.test(pr.head), pr.head);

  /* ── review M1: Ctrl+P on "As a list" ──────────────────────────────── */
  const listPr = await page.evaluate(async () => {
    document.getElementById("pos-f-view").value = "list"; posPaint();
    return document.querySelectorAll("#pos-body tbody tr").length;
  });
  await page.emulateMedia({ media: "print" });
  const listText = await page.evaluate(() => document.getElementById("pos-body").innerText);
  await page.emulateMedia({ media: "screen" });
  await page.evaluate(() => { document.getElementById("pos-f-view").value = "tree"; posPaint(); });
  const leaks = ["leaving", "key seat", "Frozen", "covering", "50%", "30 Nov", "1 Jan"].filter((w) => listText.includes(w));
  must(`M1: Ctrl+P on the list view (${listPr} rows): no leaving date, key seat, Frozen, covering or %`, listPr > 80 && !leaks.length
       && listText.includes("Owner and Managing Director"), leaks.join(", "));

  /* ── review m3: portrait A4, several sheets, HR copy: the footer fits ── */
  await load(F.dtc90());
  const foot = await page.evaluate(async () => {
    POS.wall = null; posWallOpen();
    while (!POS.wall.L) await new Promise((r) => setTimeout(r, 20));
    posWallSet("hr", true);
    while (!POS.wall.L) await new Promise((r) => setTimeout(r, 20));
    posWallSet("paper", "A4"); posWallSet("sheets", "several");
    POS.wall.L = Object.assign({}, POS.wall.L, { w: 700, h: 5000 });   // taller than wide: portrait
    posWallPrint();
    const feet = [...document.querySelectorAll("#pos-wall-print .pos-wall-foot")];
    const out = { sheets: feet.length, cut: feet.filter((f) => f.scrollHeight > f.clientHeight + 1 || f.scrollWidth > f.clientWidth + 1).length,
                  first: feet[0] && feet[0].textContent, style: document.getElementById("pos-wall-page").textContent };
    window.dispatchEvent(new Event("afterprint")); posCloseSheet();
    return out;
  });
  must(`m3: portrait A4, ${foot.sheets} HR sheets: no footer is cut (${foot.cut} cut); "${foot.first}"`,
       foot.cut === 0 && /^HR use only - not for display · Sheet 1 of/.test(foot.first) && /210mm 297mm/.test(foot.style), foot.style);

  /* ── the phone (AC-5) ───────────────────────────────────────────────── */
  await page.setViewportSize({ width: 390, height: 844 });
  await load(F.dtc90());
  const phone = await page.evaluate(() => {
    const b = document.getElementById("pos-wall-btn"); b.style.display = "";
    const bar = b.parentElement.getBoundingClientRect(), r = b.getBoundingClientRect();
    POS.wall = null; posWallOpen();
    const chip = document.querySelector(".pos-wall-chip span").getBoundingClientRect();
    const sheet = document.querySelector(".pos-sheet").getBoundingClientRect();
    posCloseSheet();
    return { w: Math.round(r.width), bar: Math.round(bar.width), h: Math.round(r.height), chip: Math.round(chip.height), sheetTop: Math.round(sheet.top), sheetW: Math.round(sheet.width) };
  });
  must(`AC-5: on a phone the button spans the toolbar (${phone.w} of ${phone.bar} px) and is ${phone.h} px tall`, phone.w === phone.bar && phone.h >= 44);
  must(`AC-6: on a phone the panel is a bottom sheet (${phone.sheetW} px wide, top at ${phone.sheetTop}) with 44 px paper chips (${phone.chip})`, phone.sheetW === 390 && phone.sheetTop > 0 && phone.chip >= 44);

  must("no script errors", !errs.length, errs.slice(0, 3).join(" | "));
  await browser.close();
  log(fails.length ? `\nwall chart (browser): ${fails.length} FAILED` : "\nwall chart (browser): all passed");
  process.exit(fails.length ? 1 : 0);
})();
