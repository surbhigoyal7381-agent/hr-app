/* Honest connectors on the real Positions page (slice 064).
 *
 * THE RULE: no line may suggest a box reports to anything but its real
 * parent. For every drawn connector - the CSS lines of a family and the SVG
 * line from an opened team lead to its "Under ..." strip - this finds the
 * box the line belongs to and every box it touches. It fails when a line
 * touches a box whose real parent is not that owner, runs through or below
 * a box instead of arriving on its top edge, touches somebody else's group
 * or strip, or when a visible seat is linked to nobody.
 *
 * Ported from the designer's check for the prototypes
 * (hrlocal-data/ux-review/2026-10-21-slice064/check-connectors.js), pointed
 * at the product's own markup and data (POS.nav).
 *
 * NOT part of CI: it needs a running site, a login and a browser. Run it on
 * a THROWAWAY site, never a real one:
 *
 *   BASE=http://127.0.0.1:8064 PROBE_USR=... PROBE_PWD=... \
 *     PLAYWRIGHT=<path to playwright> node scripts/check_positions_connectors.js
 *
 * It walks the views in light and dark, on a 1440 desktop and a 390 phone,
 * opens families, opens every level, and switches views after every open
 * state (the sequence that crashed the approved prototype). Any script
 * error on the page fails it too.
 */
const { chromium } = require(process.env.PLAYWRIGHT || "playwright");

const BASE = process.env.BASE || "http://127.0.0.1:8000";
const USR = process.env.PROBE_USR, PWD = process.env.PROBE_PWD;
const SHOTS = process.env.SHOTS || "";

function audit() {
  const app = document.getElementById("pos-body");
  const nav = POS.nav;
  const realParent = (id) => (nav.parent[id] === undefined ? null : nav.parent[id]);
  const label = (id) => (nav.by[id] ? nav.by[id].title + " · " + nav.by[id].branch : (nav.holder[id] || {}).title || id);
  const boxes = [...app.querySelectorAll(".pos-box[data-id]")].filter((b) => b.getClientRects().length);
  function ownerOf(el) {
    let n = el;
    while (n && n !== app) {
      if (n.classList && n.classList.contains("pos-strip")) return n.getAttribute("data-parent");
      if (n !== el && n.classList && n.classList.contains("pos-br") && n.firstElementChild
          && n.firstElementChild.classList.contains("pos-box")) return n.firstElementChild.getAttribute("data-id");
      n = n.parentElement;
    }
    return null;
  }
  const segs = [];
  app.querySelectorAll(".pos-kids, .pos-kids > .pos-br, .pos-sibwrap").forEach((el) => {
    ["::before", "::after"].forEach((ps) => {
      const cs = getComputedStyle(el, ps);
      if (!cs || cs.content === "none" || cs.display === "none") return;
      const w = parseFloat(cs.width), h = parseFloat(cs.height);
      if (!(w > 0 && h > 0)) return;
      const r = el.getBoundingClientRect();
      const left = r.left + parseFloat(cs.left), top = r.top + parseFloat(cs.top);
      const host = el.classList.contains("pos-br") ? el.parentElement : el;   // a child's tick belongs to its family
      segs.push({ kind: "css", owner: ownerOf(host), x1: left, y1: top, x2: left + w, y2: top + h, what: el.className + ps });
    });
  });
  app.querySelectorAll("svg.pos-links path").forEach((p) => {
    const svg = p.ownerSVGElement.getBoundingClientRect();
    const pts = (p.getAttribute("d").match(/-?[\d.]+/g) || []).map(Number);
    for (let i = 0; i + 3 < pts.length; i += 2) {
      const ax = svg.left + pts[i], ay = svg.top + pts[i + 1], bx = svg.left + pts[i + 2], by = svg.top + pts[i + 3];
      segs.push({ kind: "svg", owner: p.getAttribute("data-from"), x1: Math.min(ax, bx) - 0.75, y1: Math.min(ay, by) - 0.75,
                  x2: Math.max(ax, bx) + 0.75, y2: Math.max(ay, by) + 0.75, what: "link" });
    }
  });
  const hit = (s, r) => s.x1 < r.right + 0.5 && s.x2 > r.left - 0.5 && s.y1 < r.bottom + 0.5 && s.y2 > r.top - 0.5;
  const bad = [], linked = {};
  segs.forEach((s) => {
    boxes.forEach((b) => {
      const id = b.getAttribute("data-id"), r = b.getBoundingClientRect();
      if (!hit(s, r)) return;
      if (id === s.owner) { if (s.y1 < r.bottom - 2) bad.push(`${s.what} from ${label(id)} runs through its own box`); return; }
      const onTop = s.y2 <= r.top + 2 && s.y2 >= r.top - 2;
      if (realParent(id) === s.owner && onTop) { linked[id] = 1; return; }
      if (realParent(id) === s.owner) { bad.push(`${s.what} from ${label(s.owner)} passes through "${label(id)}" instead of arriving on top`); return; }
      bad.push(`${s.what} from ${s.owner ? label(s.owner) : "?"} touches "${label(id)}", whose parent is ${realParent(id) ? label(realParent(id)) : "none"}`);
    });
    app.querySelectorAll(".pos-sibs, .pos-strip").forEach((g) => {
      if (!hit(s, g.getBoundingClientRect())) return;
      const gp = g.getAttribute("data-parent");
      const own = s.owner && app.querySelector('.pos-box[data-id="' + CSS.escape(s.owner) + '"]');
      if (g.classList.contains("pos-sibs") && s.owner !== gp && !(own && g.contains(own))) bad.push(`${s.what} from ${s.owner} touches the group of ${gp}`);
      if (g.classList.contains("pos-strip") && s.kind === "svg" && gp !== s.owner) bad.push(`link from ${s.owner} lands on the strip of ${gp}`);
    });
  });
  boxes.forEach((b) => {
    const id = b.getAttribute("data-id"), rp = realParent(id);
    if (rp == null || linked[id]) return;
    const g = b.closest(".pos-sibs");
    if (g && g.getAttribute("data-parent") === rp) return;
    bad.push(`"${label(id)}" is linked to nobody (parent ${label(rp)})`);
  });
  const cw = app.querySelector(".pos-chartwrap");
  return { segs: segs.length, boxes: boxes.length, bad, w: cw ? cw.scrollWidth : null, f: cw ? cw.clientWidth : null,
           page: document.documentElement.scrollWidth - innerWidth };
}

(async () => {
  if (!USR || !PWD) { console.error("Set PROBE_USR and PROBE_PWD for a user on a THROWAWAY site."); process.exit(2); }
  const b = await chromium.launch();
  let total = 0;
  for (const theme of ["light", "dark"]) for (const [dev, w, h] of [["desk", 1440, 900], ["phone", 390, 844]]) {
    const ctx = await b.newContext({ viewport: { width: w, height: h } });
    const p = await ctx.newPage();
    const errs = [];
    p.on("pageerror", (e) => errs.push(e.message));
    await p.goto(BASE + "/alvoraa-login", { waitUntil: "networkidle" });
    await p.fill("#kx-email", USR); await p.fill("#kx-password", PWD);
    await Promise.all([p.waitForNavigation({ waitUntil: "networkidle" }).catch(() => {}),
                       p.click("#kx-login-form button[type=submit]")]);
    await p.goto(BASE + "/hrms-employee", { waitUntil: "networkidle" });
    await p.evaluate((t) => document.documentElement.setAttribute("data-theme", t), theme);
    await p.evaluate(() => switchPanel("positions"));
    await p.waitForFunction(() => window.POS && POS.rows && POS.rows.length > 0, null, { timeout: 30000 });
    await p.waitForTimeout(800);
    const states = [];
    const run = async (name) => {
      await p.waitForTimeout(150);
      const r = await p.evaluate(audit);
      states.push([name, r]);
      if (SHOTS && theme === "light") await p.screenshot({ path: `${SHOTS}${dev}-${name.replace(/[^a-z0-9]+/gi, "-")}.png`, fullPage: true });
    };
    const leadOf = (title) => p.evaluate((t) => POS.rows.filter((r) => r.title === t)[0].id, title);
    const top = await p.evaluate(() => POS.nav.top[0]);
    await p.evaluate(() => posSetView("reporting"));
    await run("reporting default");
    if (dev === "desk") {
      const del = await leadOf("Manager"), bo = await leadOf("Back Office"), hoo = await leadOf("Head of Operations");
      await p.evaluate(([t, id]) => posGroupFold("c:" + t, id, false), [top, del]); await run("reporting Delhi opened");
      await p.evaluate(([t, id]) => posGroupFold("c:" + t, id, false), [top, bo]); await run("reporting Back Office opened");
      await p.evaluate(([t, id]) => posGroupFold("c:" + t, id, false), [top, hoo]); await run("reporting Head of Operations opened");
      await p.evaluate(() => posToggleAll()); await run("reporting everything opened");
      await p.evaluate(() => posToggleAll());
      // The prototype's crash: open Delhi, By branch, Open every level.
      await p.evaluate(([t, id]) => posGroupFold("c:" + t, id, false), [top, del]);
      await p.evaluate(() => posSetView("branch")); await p.evaluate(() => posToggleAll());
      await run("Delhi open, By branch, every level");
      await p.evaluate(() => posToggleAll());
    } else {
      await p.evaluate((id) => posDown(id), top); await run("phone drilled to the top");
    }
    for (const v of ["branch", "department", "list", "reporting"]) {
      await p.evaluate((vv) => posSetView(vv), v);
      await run(v + " default");
      if (dev === "desk" && v !== "list") { await p.evaluate(() => posToggleAll()); await run(v + " everything opened"); await p.evaluate(() => posToggleAll()); }
    }
    for (const [name, r] of states) {
      total += r.bad.length;
      console.log(theme, dev, name.padEnd(38), `segments ${String(r.segs).padStart(3)} boxes ${String(r.boxes).padStart(3)} width ${r.w}/${r.f} page+${r.page}`,
                  r.bad.length ? `FAIL ${r.bad.length}: ${r.bad.slice(0, 3).join(" | ")}` : "ok");
    }
    if (errs.length) { console.log("SCRIPT ERRORS", errs); total++; }
    await ctx.close();
  }
  console.log("TOTAL FALSE OR MISSING LINKS", total);
  await b.close();
  process.exit(total ? 1 : 0);
})();
