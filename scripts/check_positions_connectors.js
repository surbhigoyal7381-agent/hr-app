/* Honest connectors on the real Positions page (slice 064, the live chart
 * with the improvements approved on 23 Oct 2026: prototype-old-v2).
 *
 * THE RULE: no line may suggest a box reports to anything but its real
 * parent. For every drawn line - the chart's row lines and the hanging
 * column's lines and ticks - it finds the box the line belongs to and every
 * box it touches. It fails when a line touches a box whose real parent is
 * not the line's owner, meets a box anywhere but its top edge (a row) or its
 * left edge (a hanging column), or runs through its own box; or when a
 * visible seat is joined to nobody.
 *
 * It also checks, in every state:
 *   - filters: a match is never faded, everything else drawn is faded, and
 *     nothing is drawn that is neither a match nor above one;
 *   - layout: no sideways page scroll on desktop, tools and the No reporting
 *     manager box at least 24 px tall (44 on a phone), nothing position:fixed
 *     inside the zoom wrapper, no script error;
 *   - print (Branch Delhi): the header shows, tools, filters and tiles do
 *     not, nothing private is visible, and the PDF page count.
 *
 * Ported from the designer's check for the prototype
 * (hrlocal-data/ux-review/2026-10-22-old-chart/old-audit2.js), pointed at
 * the product page.
 *
 * NOT part of CI: it needs a running THROWAWAY site, a login and Playwright.
 *
 *   BASE=http://127.0.0.1:8065 PROBE_USR=... PROBE_PWD=... \
 *     PLAYWRIGHT=<path to playwright> [SHOTS=<dir/prefix>] \
 *     node scripts/check_positions_connectors.js
 *
 * The filter states use the demo's branch, department and job role names
 * when they exist (Delhi, Sales - DTCD, Cashier, RSO) and skip them when
 * they do not. On a 390 px phone the page's 2 px sideways scroll is a known
 * fault of the portal frame (to be fixed with I6), reported but not failed.
 */
const { chromium } = require(process.env.PLAYWRIGHT || "playwright");
const fs = require("fs");

const BASE = process.env.BASE || "http://127.0.0.1:8000";
const USR = process.env.PROBE_USR, PWD = process.env.PROBE_PWD;
const SHOTS = process.env.SHOTS || "";

function audit(dev) {
  const body = document.getElementById("pos-body");
  const tree = body.querySelector(".oc-tree");
  const idOf = (btn) => { const m = (btn.getAttribute("onclick") || "").match(/\('([^']+)'\)/); return m ? m[1] : null; };
  const rows = POS.rows, byId = {};
  rows.forEach((r) => { byId[r.id] = r; });
  const how = (document.getElementById("pos-f-arrange") || {}).value || "reporting";
  // Slice 070: a copy's real parent is a seat its people's manager sits in,
  // worked out here from the rows and the manager keys - never from posPlace.
  const byTitle = {}, seatsOf = {};
  rows.forEach((r) => { byTitle[r.title] = r; r.people.forEach((p) => { (seatsOf[p.employee] = seatsOf[p.employee] || []).push(r.id); }); });
  const isCopy = (b) => b.classList.contains("copy");
  const seatOf = (b) => (isCopy(b) ? byTitle[b.querySelector(".ti").textContent] : byId[idOf(b)]);
  function realParents(b) {
    if (!isCopy(b)) return [realParent(idOf(b))];
    const r = seatOf(b), out = [];
    b.querySelectorAll(".oc-who:not(.oc-empty) > span:last-child").forEach((s) => {
      const p = r && r.people.find((q) => q.name === s.firstChild.textContent);
      (p && p.manager ? seatsOf[p.manager] || [] : []).forEach((id) => { if (out.indexOf(id) < 0) out.push(id); });
    });
    return out;
  }
  function realParent(id) {
    if (!id) return null;
    if (id.indexOf("grp:") === 0) { const key = id.slice(4); const m = rows.filter((r) => posGroupKey(r) === key); return m.length ? realParent(m[0].id) : null; }
    if (id.indexOf("br:") === 0) return null;
    if (id.indexOf("dp:") === 0) { const d = id.slice(3); const meta = (POS.departments || {})[d] || {}; return meta.parent ? "dp:" + meta.parent : null; }
    const r = byId[id];
    if (!r) return null;
    if (how === "branch") return (r.reports_to && byId[r.reports_to] && byId[r.reports_to].branch === r.branch) ? r.reports_to : "br:" + (r.branch || "");
    if (how === "department") return (r.reports_to && byId[r.reports_to] && byId[r.reports_to].department === r.department) ? r.reports_to : "dp:" + (r.department || "");
    return r.reports_to && byId[r.reports_to] ? r.reports_to : null;
  }
  const boxes = tree ? [...tree.querySelectorAll(".oc-box")].filter((b) => b.getClientRects().length) : [];
  const ownerOf = (el) => { const br = el.closest(".oc-branch"); const box = br && br.querySelector(":scope > .oc-node > .oc-box"); return box ? idOf(box) : null; };
  const segs = [];
  if (tree) tree.querySelectorAll(".oc-kids, .oc-kids > .oc-branch, .oc-hang, .oc-hang-item").forEach((el) => {
    ["::before", "::after"].forEach((ps) => {
      const cs = getComputedStyle(el, ps);
      if (!cs || cs.content === "none" || cs.display === "none") return;
      const z = el.currentCSSZoom || 1;   // computed lengths are unzoomed; rects are zoomed
      const w = parseFloat(cs.width) * z, h = parseFloat(cs.height) * z;
      if (!(w > 0 && h > 0)) return;
      const r = el.getBoundingClientRect(), left = r.left + parseFloat(cs.left) * z, top = r.top + parseFloat(cs.top) * z;
      let host;
      if (el.classList.contains("oc-hang") || el.classList.contains("oc-hang-item")) {
        host = el.closest(".oc-hang").parentElement;
        if (host.classList.contains("oc-hang-slot")) host = host.parentElement;
      } else host = el.classList.contains("oc-kids") ? el.parentElement : el.parentElement.parentElement;
      segs.push({ owner: ownerOf(host.querySelector(":scope > .oc-node") || host), x1: left, y1: top, x2: left + w, y2: top + h });
    });
  });
  const linked = {}, bad = [];
  const hit = (s, r) => s.x1 < r.right + 0.5 && s.x2 > r.left - 0.5 && s.y1 < r.bottom + 0.5 && s.y2 > r.top - 0.5;
  segs.forEach((s) => boxes.forEach((b) => {
    const id = idOf(b), r = b.getBoundingClientRect();
    if (!hit(s, r)) return;
    if (id === s.owner) { if (s.y1 < r.bottom - 2) bad.push("line runs through its own box " + id); return; }
    const onTop = (s.y2 <= r.top + 2 && s.y2 >= r.top - 2)
      || (s.y2 - s.y1 <= 3 && s.x2 <= r.left + 2 && s.x2 >= r.left - 2 && s.y1 >= r.top && s.y1 <= r.bottom);
    if (realParents(b).indexOf(s.owner) >= 0 && onTop) { linked[id] = 1; return; }
    bad.push(`line from ${s.owner} touches ${id} (parent ${realParents(b).join("/")})${onTop ? "" : ", not on its top or left edge"}`);
  }));
  if (dev !== "phone") boxes.forEach((b) => {
    const id = idOf(b), rp = realParents(b);
    if (rp.some((x) => x) && !linked[id] && boxes.some((x) => rp.indexOf(idOf(x)) >= 0)) bad.push("linked to nobody: " + id);
  });
  // Slice 070: a copy is an end box; a home with nobody, no open slot and
  // nothing under it is not drawn.
  boxes.forEach((b) => {
    const node = b.closest(".oc-node"), br = node.parentElement.classList.contains("oc-branch") ? node.parentElement : null;
    if (isCopy(b) && (node.querySelector(".oc-toggle") || (br && br.querySelector(":scope > .oc-node") === node
        && br.querySelector(":scope > .oc-kids, :scope > .oc-fam")))) bad.push("a copy with a fold or boxes under it: " + idOf(b));
    if (!isCopy(b) && /None here/.test(b.textContent) && !b.querySelector(".oc-tag.v") && !node.querySelector(".oc-toggle"))
      bad.push("a home with nobody, no open slot and nothing under it is drawn: " + idOf(b));
  });
  const fbad = [];
  if (posAnyFilter()) {
    const match = {};
    rows.filter(posMatches).forEach((r) => { match[r.id] = 1; match["grp:" + posGroupKey(r)] = 1; });
    boxes.forEach((b) => { if (isCopy(b) && posMatches(seatOf(b))) match[idOf(b)] = 1; });
    boxes.forEach((b) => {
      const id = idOf(b);
      if (!id || id.indexOf("br:") === 0 || id.indexOf("dp:") === 0 || b.classList.contains("pos-nomgr")) return;
      const faded = (b.closest(".oc-node").getAttribute("style") || "").indexOf("opacity") > -1;
      if (match[id] && faded) fbad.push("a match is faded: " + id);
      if (!match[id] && !faded) fbad.push("a non-match is not faded: " + id);
      if (!match[id]) {
        const isAnc = rows.some((r) => {
          if (!posMatches(r)) return false;
          let a = byId[r.reports_to], k = 0;
          while (a && k < 40) { if (a.id === id) return true; a = byId[a.reports_to]; k++; }
          return false;
        });
        if (!isAnc) fbad.push("neither a match nor above one: " + id);
      }
    });
  }
  const root = tree ? tree.querySelector(".oc-node.root > .oc-box") || boxes[0] : null;
  let rootIn = null;
  if (root && tree) { const rr = root.getBoundingClientRect(), f = tree.getBoundingClientRect(); rootIn = rr.left >= f.left - 1 && rr.right <= f.right + 1; }
  const first = body.querySelector(".oc-box.pos-first");
  let firstIn = null;
  if (first && tree) { const rr = first.getBoundingClientRect(), f = tree.getBoundingClientRect(); firstIn = rr.left >= f.left - 1 && rr.right <= f.right + 1 && rr.top >= 0 && rr.bottom <= innerHeight; }
  const lim = dev === "phone" ? 44 : 24;
  const panel = document.getElementById("panel-positions");
  const small = [...panel.querySelectorAll(".pos-ztools button, .pos-nomgr")].filter((e) => e.getClientRects().length && e.getBoundingClientRect().height < lim).length;
  const fixedInZoom = [...(body.querySelector(".oc-zoom") || document.createElement("i")).querySelectorAll("*")].filter((e) => getComputedStyle(e).position === "fixed").length;
  return { frame: tree ? tree.clientWidth : body.clientWidth, chart: tree ? tree.scrollWidth : body.scrollWidth,
    height: tree ? Math.round(tree.scrollHeight) : null, page: document.documentElement.scrollWidth - innerWidth,
    boxes: boxes.length, rootIn, firstIn, focusOnFirst: !!(first && document.activeElement === first),
    line: (document.getElementById("pos-fline-txt") || {}).textContent || "", segs: segs.length, bad, fbad, small, fixedInZoom,
    zoom: (document.querySelector(".pos-zpct") || {}).textContent || "", arrange: (document.getElementById("pos-f-arrange") || {}).value };
}

/* Slice 070: FIXTURE=reporting runs with no site - the page is built from
 * this checkout and position_table answers with the census-shaped fixture
 * (scripts/lib/wall_chart_fixture.js reporting()), as check_wall_chart_browser.js does. */
const FIXTURE = process.env.FIXTURE || "";

(async () => {
  if (!FIXTURE && (!USR || !PWD)) { console.error("Set PROBE_USR and PROBE_PWD for a user on a THROWAWAY site, or FIXTURE=reporting."); process.exit(2); }
  const b = await chromium.launch();
  let state;
  const reply = FIXTURE ? require("./lib/wall_chart_fixture")[FIXTURE]() : null;
  const html = FIXTURE ? require("./lib/portal_source").readPortalSource() : null;
  if (!FIXTURE) {
    const login = await (await b.newContext()).newPage();
    await login.goto(BASE + "/alvoraa-login");
    await login.fill("#kx-email", USR); await login.fill("#kx-password", PWD);
    await Promise.all([login.waitForNavigation().catch(() => {}), login.click("#kx-login-form button[type=submit]")]);
    state = await login.context().storageState();
  }
  let fails = 0, known = 0;
  for (const theme of ["light", "dark"]) for (const [name, w, h, dev] of [["1440", 1440, 900, "desk"], ["1280", 1280, 800, "desk"], ["1024", 1024, 768, "desk"], ["390", 390, 844, "phone"]]) {
    const ctx = await b.newContext(Object.assign({ viewport: { width: w, height: h } }, state ? { storageState: state } : {}));
    const p = await ctx.newPage();
    const errs = [];
    p.on("pageerror", (e) => { if (!FIXTURE || !/Unexpected token '\{'/.test(e.message)) errs.push(e.message); });
    if (FIXTURE) {
      await p.addInitScript(() => {
        window.fetch = () => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ message: {} }), text: () => Promise.resolve("") });
        window.frappe = { call: () => Promise.resolve({ message: {} }), csrf_token: "x", boot: {}, ui: {}, _messages: {}, utils: { escape_html: (s) => s } };
      });
      await p.route("http://wall.test/**", (r) => r.request().url() === "http://wall.test/hrms-employee"
        ? r.fulfill({ contentType: "text/html; charset=utf-8", body: html }) : r.fulfill({ status: 404, body: "" }));
      await p.goto("http://wall.test/hrms-employee", { waitUntil: "load" });
      await p.evaluate((d) => { window.gpFetch = (m) => Promise.resolve(/position_table/.test(m) ? JSON.parse(JSON.stringify(d)) : {}); }, reply);
    } else {
      await p.goto(BASE + "/hrms-employee", { waitUntil: "networkidle" });
    }
    await p.evaluate((t) => document.documentElement.setAttribute("data-theme", t), theme);
    await p.evaluate(() => switchPanel("positions"));
    await p.waitForFunction(() => window.POS && POS.rows && POS.rows.length > 0, null, { timeout: 30000 });
    await p.waitForTimeout(500);
    const out = [];
    const run = async (label) => {
      const m = await p.evaluate(audit, dev);
      out.push([label, m]);
      if (SHOTS && theme === "light") await p.screenshot({ path: `${SHOTS}${name}-${label.replace(/[^a-z0-9]+/gi, "-")}.png`, fullPage: true });
    };
    const openAll = async () => {
      for (let i = 0; i < 400; i++) {
        const t = await p.$("#pos-body .oc-toggle[aria-expanded=false], #pos-body .oc-more");
        if (!t) break;
        await t.click(); await p.waitForTimeout(15);
      }
    };
    const clear = async () => {
      const c = await p.$('#pos-body button:has-text("Clear filter"), #pos-body button:has-text("Clear the filter")');
      if (c) { await c.click(); await p.waitForTimeout(200); }
    };
    await run("opening view");
    // Slice 070: the five cases, each opened the way Find opens it.
    for (const [label, title, also] of [["070 split seat", "Office Executive", "Chief Financial Officer"], ["070 vacancy on home only", "Back Office", "Backoffice Executive"],
                                  ["070 hidden empty home", "Store Auditor"], ["070 manager in no seat", "Packing"],
                                  ["070 manager outside scope", "RSO Noida"]]) {
      // `also`: the manager's seat a copy hangs under, opened too.
      const has = await p.evaluate(([t, a]) => { const r = POS.rows.find((x) => x.title === t); if (!r) return false;
        POS.collapsed = {}; POS.expanded = {}; posFindPick(r.id);
        const m = a && POS.rows.find((x) => x.title === a); if (m) { POS.expanded[m.id] = true; posPaint(); }
        return true; }, [title, also]);
      if (has) { await p.waitForTimeout(150); await run(label); }
    }
    await p.evaluate(() => { POS.collapsed = {}; POS.expanded = {}; posPaint(); });
    const d = await p.$('#pos-body .oc-toggle[aria-label*="Delhi"][aria-expanded=false]');
    if (d) { await d.click(); await p.waitForTimeout(150); await run("Delhi opened"); }
    await openAll(); await run("reporting everything opened");
    for (const arr of ["branch", "department"]) {
      await p.selectOption("#pos-f-arrange", arr); await p.waitForTimeout(150);
      await run(arr + " as opened"); await openAll(); await run(arr + " everything opened");
    }
    await p.selectOption("#pos-f-arrange", "reporting");
    await p.evaluate(() => { POS.collapsed = {}; POS.expanded = {}; posPaint(); });
    if (dev === "desk") {
      for (const [lbl, act] of [["zoom 40", () => p.evaluate(() => { for (let i = 0; i < 9; i++) posZoom(-1); })],
                                ["zoom 200", () => p.evaluate(() => { for (let i = 0; i < 20; i++) posZoom(1); })],
                                ["fit to width", () => p.evaluate(() => posZoomFit())]]) {
        await act(); await p.waitForTimeout(100); await run(lbl);
      }
      await p.evaluate(() => { document.activeElement && document.activeElement.blur && document.activeElement.blur(); });
      await p.keyboard.press("0"); await p.keyboard.press("-"); await p.waitForTimeout(80);
      const kz = await p.evaluate(() => document.querySelector(".pos-zpct").textContent);
      out.push(["keys 0 then -", { bad: kz === "90%" ? [] : ["keys gave " + kz], fbad: [], kz }]);
      await p.evaluate(() => posZoom(0));
    }
    const sel = async (id, v) => {
      const has = await p.evaluate(([i, val]) => [...document.getElementById(i).options].some((o) => o.value === val), [id, v]);
      if (has) { await p.selectOption("#" + id, v); await p.waitForTimeout(250); }
      return has;
    };
    if (await sel("pos-f-branch", "Delhi")) await run("filter Branch Delhi");
    if (await sel("pos-f-role", "RSO")) await run("filter Branch Delhi + Job role RSO");
    await clear(); await run("after Clear filter");
    if (await sel("pos-f-dept", "Sales - DTCD")) await run("filter Department Sales");
    await clear();
    if (await sel("pos-f-role", "Cashier")) await run("filter Job role Cashier");
    await clear();
    if (await sel("pos-f-open", "open")) await run("filter Show open seats");
    await clear();
    if (await sel("pos-f-branch", "Ambala")) { await sel("pos-f-open", "leaving"); await run("no match (Ambala + leaving)"); await clear(); }
    if (dev === "desk" && theme === "light") {
      await sel("pos-f-branch", "Delhi");
      await p.emulateMedia({ media: "print" });
      const pr = await p.evaluate(() => {
        const vis = (s) => [...document.querySelectorAll(s)].filter((e) => e.getClientRects().length).length;
        return { head: (document.querySelector("#panel-positions .pos-printhead") || {}).innerText,
                 tools: vis(".pos-ztools"), filters: vis("#pos-f-branch"), tiles: vis("#pos-tiles > *"),
                 frame: vis("nav.navbar, .sidebar"), privateShown: vis(".private, [data-private]") };
      });
      if (SHOTS) await p.screenshot({ path: `${SHOTS}${name}-print-view.png`, fullPage: true });
      await p.emulateMedia({ media: "screen" });
      const pdf = await p.pdf({ landscape: true, format: "A4", printBackground: true, preferCSSPageSize: true });
      const pages = (pdf.toString("latin1").match(/\/Type\s*\/Page[^s]/g) || []).length;
      if (SHOTS) fs.writeFileSync(`${SHOTS}${name}-print.pdf`, pdf);
      const pbad = [];
      if (!pr.head || !/Positions/.test(pr.head)) pbad.push("no print header");
      if (pr.tools || pr.filters || pr.tiles || pr.frame) pbad.push("tools, filters, tiles or the portal frame print");
      if (pr.privateShown) pbad.push("something private prints");
      out.push(["print (Branch Delhi)", { bad: pbad, fbad: [], pr, pages }]);
      await clear();
    }
    for (const [label, m] of out) {
      const pageFail = m.page > 0 && dev !== "phone";
      if (m.page > 0 && dev === "phone") known++;
      const f = (m.bad || []).length + (m.fbad || []).length + (pageFail ? 1 : 0) + (m.small ? 1 : 0) + (m.fixedInZoom ? 1 : 0);
      fails += f;
      if (m.pr) { console.log(theme, name, label, JSON.stringify(m.pr), "pdf pages", m.pages, f ? "FAIL " + m.bad.join(" | ") : "ok"); continue; }
      if (m.kz) { console.log(theme, name, label, "->", m.kz, f ? "FAIL" : "ok"); continue; }
      console.log(theme.padEnd(5), name.padEnd(4), label.padEnd(34),
        `chart ${m.chart}/${m.frame} h ${m.height} page+${m.page} boxes ${m.boxes} zoom ${m.zoom} arrange ${m.arrange} top-in-view ${m.rootIn} first-in-view ${m.firstIn} focus-on-first ${m.focusOnFirst} "${m.line}"`,
        f ? `FAIL ${[...(m.bad || []), ...(m.fbad || [])].slice(0, 2).join(" | ")} ${pageFail ? "page scrolls" : ""} ${m.small ? "small targets " + m.small : ""} ${m.fixedInZoom ? "fixed inside zoom" : ""}` : `ok (${m.segs} lines)`);
    }
    if (errs.length) { console.log("PAGE ERRORS", errs.slice(0, 3)); fails++; }
    await ctx.close();
  }
  console.log(`TOTAL FAILURES ${fails} (false or missing links, wrong fading, page scroll, small targets, fixed inside zoom, print, errors)`
    + (known ? ` · known phone frame sideways scroll in ${known} states (I6)` : ""));
  await b.close();
  process.exit(fails ? 1 : 0);
})();
