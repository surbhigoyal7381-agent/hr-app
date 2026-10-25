/* Trays, drawers and dialogs must open against the WINDOW, not inside a panel.
 *
 * THE BUG THIS PINS, 22 Oct 2026. The Positions seat tray opened about 460 px
 * wide but 108 px down the page, its grey backdrop covered only the panel, and
 * a white strip showed on the right: it looked like a page inside a frame.
 * The cause was one word. The panel fade-in ran with `animation-fill-mode:
 * both`, so after it finished it KEPT `transform: none` applied as an
 * animation value. In Chrome an element with a transform animation in effect
 * becomes the frame (the "containing block") for every position:fixed child.
 * Every tray, dialog and popover that lives inside a panel - not only
 * Positions - was laid out against the panel instead of the window. Dropping
 * the fill mode fixed all of them at once, with no visible change.
 *
 * TWO PARTS.
 *
 * 1. Static (`--static`, no browser, runs in CI). Lists every position:fixed
 *    element in the employee portal's stylesheets and templates and fails when
 *    one is not in INVENTORY below - so a new tray must be added here, and so
 *    gets the browser check. It also fails when an animation that moves or
 *    filters keeps its end state (`both`/`forwards`) on anything that is not
 *    itself an overlay, or when a panel rule sets transform, filter,
 *    perspective, contain or will-change.
 *
 * 2. Browser (default). NOT part of CI: it needs a running THROWAWAY site, a
 *    login and Playwright.
 *
 *      BASE=http://127.0.0.1:8065 PROBE_USR=... PROBE_PWD=... \
 *        PLAYWRIGHT=<path to playwright> node scripts/check_portal_trays.js
 *
 *    At a 1440, 1280 and 1024 window, each at 100, 125 and 150 % zoom (zoom
 *    is emulated as a smaller CSS viewport with a matching pixel ratio, which
 *    is what browser zoom does), in the real shell with the sidebar:
 *    - every panel is opened and no position:fixed element anywhere has an
 *      ancestor with transform, filter, backdrop-filter, perspective, contain
 *      or will-change; and every fixed element on the page is in INVENTORY;
 *    - every right-hand tray is opened and must touch the right edge, run
 *      from the top to the bottom of the window, be the top-most thing at its
 *      own top edge (not under the top bar), and its backdrop must cover the
 *      whole window and be top-most beside it;
 *    - every full-window backdrop or dialog is opened and must cover the
 *      whole window.
 *    The Positions trays are opened by their real functions. The other
 *    drawers are opened by setting the same class or style their opener sets,
 *    because their openers need payslips, goals or an employee to load.
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..", "alvoraa_portal", "alvoraa_portal");

/* Every position:fixed thing in the employee portal (/hrms-employee) and the
   -next page. kind: tray = right-hand drawer, scrim = its backdrop, dialog =
   full-window backdrop of a centred dialog, shell = the page frame itself,
   popover/toast = small floating things placed by script. `open` says how
   the browser part opens it; `tray`/`scrim` pair a drawer with its backdrop. */
const INVENTORY = {
  // Page frame (always on screen, outside every panel)
  "nav.navbar":           { page: "portal", kind: "shell" },
  ".sidebar":             { page: "portal", kind: "shell" },
  ".sidebar-overlay":     { page: "portal", kind: "shell" },
  ".bottom-nav":          { page: "portal", kind: "shell" },
  ".loading-overlay":     { page: "portal", kind: "shell" },
  ".notif-panel":         { page: "portal", kind: "popover" },
  ".toast-wrap":          { page: "portal", kind: "toast" },
  ".gp-toast-wrap":       { page: "portal", kind: "toast" },
  ".tv-toast":            { page: "portal", kind: "toast" },
  ".tv-menu":             { page: "portal", kind: "popover" },
  ".tv-pop":              { page: "portal", kind: "popover" },
  ".aps-page-menu":       { page: "portal", kind: "popover" },
  // Right-hand trays and their backdrops
  ".pos-sheet":           { page: "portal", kind: "tray", scrim: ".pos-scrim", panel: "positions", open: "positions" },
  ".pos-scrim":           { page: "portal", kind: "scrim" },
  "#gp-detail-panel":     { page: "portal", kind: "tray", scrim: "#gp-detail-overlay", open: "class+style" },
  "#gp-detail-overlay":   { page: "portal", kind: "scrim" },
  ".emp-drawer":          { page: "portal", kind: "tray", scrim: ".emp-drawer-overlay", open: "class",
                            ids: [["#emp-drawer", "#emp-drawer-overlay"], ["#payslip-drawer", "#payslip-drawer-overlay"],
                                  ["#goal-drawer", "#goal-drawer-overlay"]] },
  ".emp-drawer-overlay":  { page: "portal", kind: "scrim" },
  // Full-window backdrops of centred dialogs (every .gp-backdrop dialog,
  // including #pos-editor, #pos-delete, #pos-person, #pos-setup, #dr-confirm)
  ".gp-backdrop":         { page: "portal", kind: "dialog", open: "class" },
  ".tv-pop-backdrop":     { page: "portal", kind: "dialog", open: "class" },
  "#cal-signoff-modal":   { page: "portal", kind: "dialog", open: "style" },
  // The -next page (a separate document; left rail and bottom sheet only)
  ".nf-rail":             { page: "next", kind: "shell" },
  ".nf-scrim":            { page: "next", kind: "scrim" },
  ".nf-sheet-wrap":       { page: "next", kind: "dialog" },
  ".nf-toasts":           { page: "next", kind: "toast" },
  ".nf-bottom":           { page: "next", kind: "shell" },
};

/* Elements allowed to keep the end of a moving animation: single messages
   inside a toast stack. They never contain a tray or a dialog. */
const FILL_OK = [".toast", ".gp-toast.gp-toast-out"];

const KILLS_FIXED = /\b(transform|filter|backdrop-filter|perspective|contain|will-change)\s*:/;

function walk(dir, out) {
  for (const f of fs.readdirSync(dir)) {
    const p = path.join(dir, f);
    if (fs.statSync(p).isDirectory()) walk(p, out); else out.push(p);
  }
  return out;
}

function sources() {
  return [
    ...walk(path.join(ROOT, "public", "css", "ess"), []),
    ...walk(path.join(ROOT, "templates", "includes"), []),
    path.join(ROOT, "www", "hrms-employee.html"),
    path.join(ROOT, "www", "hrms-employee-next.html"),
    ...walk(path.join(ROOT, "public", "js", "ess"), []),
  ].filter((f) => /\.(css|html|js)$/.test(f));
}

const rel = (f) => path.relative(ROOT, f).replace(/\\/g, "/");
const noComments = (t) => t.replace(/\/\*[\s\S]*?\*\//g, "");
const split = (sel) => sel.split(",").map((s) => s.trim().replace(/\s+/g, " ")).filter(Boolean);

function staticCheck() {
  const bad = [], found = new Set(), keyframes = {}, fills = [];
  for (const f of sources()) {
    const t = noComments(fs.readFileSync(f, "utf8"));
    if (/\.(css|html)$/.test(f)) {
      for (const m of t.matchAll(/@keyframes\s+([\w-]+)\s*\{((?:[^{}]*\{[^{}]*\})*[^{}]*)\}/g)) keyframes[m[1]] = m[2];
      for (const m of t.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
        const sels = split(m[1]), body = m[2];
        if (/position\s*:\s*fixed/.test(body)) sels.forEach((s) => found.add(s + "\u0000" + rel(f)));
        const anim = body.match(/animation\s*:\s*([^;}]+)/);
        const fill = body.match(/animation-fill-mode\s*:\s*([^;}]+)/);
        if ((anim && /\b(both|forwards)\b/.test(anim[1])) || (fill && /\b(both|forwards)\b/.test(fill[1]))) {
          fills.push({ sels, names: (anim ? anim[1] : "").split(",").map((a) => a.trim().split(/\s+/)[0]), file: rel(f) });
        }
        sels.filter((s) => /(^|[\s>+~])(\.panel\b|#panel-)[^\s>+~]*$/.test(s) && !/::?(before|after)/.test(s))
          .forEach((s) => { if (KILLS_FIXED.test(body.replace(/text-transform|transition[^;]*/g, ""))) bad.push(`${rel(f)}: "${s}" sets ${body.match(KILLS_FIXED)[1]} on a panel. That makes the panel the frame for every tray and dialog inside it.`); });
      }
      if (f.endsWith(".html")) {
        for (const m of t.matchAll(/<[a-z]+\b[^>]*style="[^"]*position\s*:\s*fixed[^"]*"[^>]*>/gi)) {
          const id = (m[0].match(/\bid="([^"]+)"/) || [])[1];
          found.add((id ? "#" + id : "(inline element without an id)") + "\u0000" + rel(f));
        }
      }
    }
    if (f.endsWith(".js")) {
      t.split("\n").forEach((l, i) => {
        if (/position\s*:\s*["']?fixed/.test(l)) found.add(`(set by script at ${rel(f)}:${i + 1})\u0000${rel(f)}`);
      });
    }
  }
  const seen = new Set();
  for (const k of found) {
    const [sel, file] = k.split("\u0000");
    seen.add(sel);
    if (!INVENTORY[sel]) bad.push(`${file}: "${sel}" is position:fixed but is not in INVENTORY in scripts/check_portal_trays.js. Add it, with how it opens, so the browser check proves it opens against the window.`);
  }
  for (const sel of Object.keys(INVENTORY)) if (!seen.has(sel)) bad.push(`INVENTORY lists "${sel}" but no stylesheet or template makes it position:fixed any more. Remove it from the list.`);
  const overlays = new Set(Object.keys(INVENTORY));
  for (const { sels, names, file } of fills) {
    const moves = names.some((n) => keyframes[n] && /\b(transform|filter|perspective)\s*:/.test(keyframes[n]));
    if (!moves) continue;
    const own = sels.every((s) => FILL_OK.includes(s)) || sels.every((s) => [...overlays].some((o) => s === o || s.startsWith(o + ".") || s.startsWith(o + ":") || s.startsWith(o + "[")));
    if (!own) bad.push(`${file}: "${sels.join(", ")}" keeps the end of a moving animation (both/forwards). That leaves a transform on the element, so any tray or dialog inside it opens inside it instead of the window. Drop the fill mode.`);
  }
  return { bad, count: found.size };
}

/* ---------------------------------------------------------------- browser */

function pageScan(inventory) {
  const why = (n) => {
    const cs = getComputedStyle(n), hit = [];
    if (cs.transform !== "none") hit.push("transform " + cs.transform);
    if (cs.filter !== "none") hit.push("filter");
    if (cs.backdropFilter && cs.backdropFilter !== "none") hit.push("backdrop-filter");
    if (cs.perspective !== "none") hit.push("perspective");
    if (/paint|layout|strict|content/.test(cs.contain)) hit.push("contain " + cs.contain);
    if (/transform|filter|perspective/.test(cs.willChange)) hit.push("will-change " + cs.willChange);
    if (cs.containerType && cs.containerType !== "normal") hit.push("container-type");
    return hit;
  };
  const name = (n) => (n.id ? "#" + n.id : n.tagName.toLowerCase() + (n.className && typeof n.className === "string" ? "." + n.className.trim().split(/\s+/).join(".") : ""));
  const out = [];
  for (const el of document.querySelectorAll("body *")) {
    if (getComputedStyle(el).position !== "fixed") continue;
    const known = Object.keys(inventory).some((s) => { try { return el.matches(s); } catch (e) { return false; } });
    if (!known) out.push(`${name(el)} is position:fixed on the page but matches nothing in INVENTORY`);
    for (let n = el.parentElement; n && n !== document.documentElement; n = n.parentElement) {
      const h = why(n);
      if (h.length) out.push(`${name(el)} sits inside ${name(n)}, which has ${h.join(", ")}: it opens inside that box, not the window`);
    }
  }
  return out;
}

function measure([traySel, scrimSel]) {
  const vw = document.documentElement.clientWidth, vh = window.innerHeight, bad = [];
  const tray = document.querySelector(traySel), scrim = scrimSel ? document.querySelector(scrimSel) : null;
  if (!tray) return [`${traySel} did not open`];
  const r = tray.getBoundingClientRect();
  const near = (a, b) => Math.abs(a - b) <= 1;
  if (!near(r.right, vw)) bad.push(`${traySel} ends at x=${Math.round(r.right)}, not the window's right edge ${vw}`);
  if (!near(r.top, 0)) bad.push(`${traySel} starts ${Math.round(r.top)} px down, not at the top of the window`);
  if (!near(r.bottom, vh)) bad.push(`${traySel} ends at y=${Math.round(r.bottom)}, not the window's bottom ${vh}`);
  if (r.width < 200) bad.push(`${traySel} is only ${Math.round(r.width)} px wide`);
  const topAt = (x, y) => document.elementFromPoint(x, y);
  const t = topAt(Math.max(r.left + 24, 0), 8);
  if (!t || !tray.contains(t)) bad.push(`at the top of ${traySel} the top-most thing is ${t ? (t.id || t.className || t.tagName) : "nothing"}, so the tray is painted underneath it`);
  if (scrim) {
    const s = scrim.getBoundingClientRect();
    const full = r.left <= 1;              // on a narrow window the tray takes the whole width, by design
    if (!(near(s.left, 0) && near(s.top, 0) && s.right >= vw - 1 && s.bottom >= vh - 1)) bad.push(`${scrimSel} covers ${Math.round(s.left)},${Math.round(s.top)} to ${Math.round(s.right)},${Math.round(s.bottom)}, not the whole ${vw}x${vh} window`);
    (full ? [] : [[6, 6], [6, vh - 6], [Math.max(r.left - 6, 6), vh / 2]]).forEach(([x, y]) => {
      const e = topAt(x, y);
      if (!e || (e !== scrim && !scrim.contains(e))) bad.push(`at ${Math.round(x)},${Math.round(y)} the top-most thing is ${e ? (e.id || e.className || e.tagName) : "nothing"}, not ${scrimSel}: the backdrop does not cover the window there`);
    });
  }
  return bad;
}

function cover(sel) {
  const vw = document.documentElement.clientWidth, vh = window.innerHeight;
  const el = document.querySelector(sel);
  if (!el) return [`${sel} not found`];
  const s = el.getBoundingClientRect();
  return (Math.abs(s.left) <= 1 && Math.abs(s.top) <= 1 && s.right >= vw - 1 && s.bottom >= vh - 1) ? []
    : [`${sel} covers ${Math.round(s.left)},${Math.round(s.top)} to ${Math.round(s.right)},${Math.round(s.bottom)}, not the whole ${vw}x${vh} window`];
}

/* Wait until nothing on the page is still sliding or fading in. */
async function settle(p) {
  await p.evaluate(() => Promise.all(document.getAnimations().filter((a) => a.playState === "running"
    && isFinite(a.effect.getComputedTiming().endTime)).map((a) => a.finished.catch(() => {}))));
}

/* A dialog can sit inside a tab that is closed until its own screen opens it.
   Show those tabs while the dialog is measured, as the real opener does, and
   put them back afterwards. */
function showTabs([id, on]) {
  const el = document.getElementById(id);
  if (on) {
    window.__shown = [];
    for (let n = el.parentElement; n && !n.classList.contains("panel") && n !== document.body; n = n.parentElement) {
      if (getComputedStyle(n).display === "none") { window.__shown.push([n, n.style.display]); n.style.display = "block"; }
    }
  } else {
    (window.__shown || []).forEach(([n, d]) => { n.style.display = d; });
  }
}

async function browserCheck() {
  const { chromium } = require(process.env.PLAYWRIGHT || "playwright");
  const BASE = process.env.BASE || "http://127.0.0.1:8000";
  const USR = process.env.PROBE_USR, PWD = process.env.PROBE_PWD;
  if (!USR || !PWD) { console.log("set PROBE_USR and PROBE_PWD (a login on a throwaway site)"); process.exit(2); }
  const browser = await chromium.launch();
  const login = await (await browser.newContext()).newPage();
  await login.goto(BASE + "/alvoraa-login");
  await login.fill("#kx-email", USR);
  await login.fill("#kx-password", PWD);
  await Promise.all([login.waitForNavigation().catch(() => {}), login.click("#kx-login-form button[type=submit]")]);
  const state = await login.context().storageState();
  const fails = [];
  let checks = 0;
  for (const w of [1440, 1280, 1024]) {
    for (const zoom of [1, 1.25, 1.5]) {
      const tag = `${w} window at ${Math.round(zoom * 100)}%`;
      const ctx = await browser.newContext({ storageState: state, viewport: { width: Math.round(w / zoom), height: Math.round(900 / zoom) }, deviceScaleFactor: zoom });
      const p = await ctx.newPage();
      const errors = [];
      p.on("pageerror", (e) => errors.push(e.message));
      await p.goto(BASE + "/hrms-employee", { waitUntil: "networkidle" });
      const panels = await p.evaluate(() => [...document.querySelectorAll(".panel[id^=panel-]")].map((x) => x.id.slice(6)));
      const scan = new Set();
      for (const id of panels) {
        await p.evaluate((id) => { try { switchPanel(id); } catch (e) {} }, id);
        await p.waitForTimeout(350);          // past the 140 ms fade-in
        (await p.evaluate(pageScan, INVENTORY)).forEach((m) => scan.add(`${m} (panel ${id})`));
      }
      checks++; scan.forEach((m) => fails.push(`${tag}: ${m}`));

      // Positions: the three trays, opened by their real functions.
      await p.evaluate(() => switchPanel("positions"));
      await p.waitForFunction(() => window.POS && POS.rows && POS.rows.length > 0, null, { timeout: 30000 }).catch(() => {});
      await p.waitForTimeout(400);
      for (const [what, fn] of [["seat tray", "posSeatSheet(POS.rows[0].id)"], ["no reporting manager tray", "posNoMgrSheet()"], ["in no seat tray", "posUnseatedSheet()"]]) {
        const opened = await p.evaluate((fn) => { try { posCloseSheet(true); eval(fn); return !!document.querySelector(".pos-sheet"); } catch (e) { return String(e); } }, fn);
        checks++;
        if (opened !== true) { fails.push(`${tag}: Positions ${what} did not open (${opened})`); continue; }
        await settle(p);
        (await p.evaluate(measure, [".pos-sheet", ".pos-scrim"])).forEach((m) => fails.push(`${tag}: Positions ${what}: ${m}`));
        await p.keyboard.press("Escape");
        if (await p.evaluate(() => !!document.querySelector(".pos-sheet"))) fails.push(`${tag}: Positions ${what} did not close on Escape`);
      }

      // The other right-hand drawers, opened the way their openers open them.
      for (const [tray, scrim] of INVENTORY[".emp-drawer"].ids) {
        await p.evaluate(([t, s]) => { document.querySelector(s).classList.add("open"); document.querySelector(t).classList.add("open"); }, [tray, scrim]);
        await settle(p);                      // the 320 ms slide-in
        checks++;
        (await p.evaluate(measure, [tray, scrim])).forEach((m) => fails.push(`${tag}: ${m}`));
        await p.evaluate(([t, s]) => { document.querySelector(s).classList.remove("open"); document.querySelector(t).classList.remove("open"); }, [tray, scrim]);
      }
      await p.evaluate(() => { document.getElementById("gp-detail-panel").classList.add("open"); document.getElementById("gp-detail-overlay").style.display = "block"; });
      await settle(p);
      checks++;
      (await p.evaluate(measure, ["#gp-detail-panel", "#gp-detail-overlay"])).forEach((m) => fails.push(`${tag}: ${m}`));
      await p.evaluate(() => { document.getElementById("gp-detail-panel").classList.remove("open"); document.getElementById("gp-detail-overlay").style.display = "none"; });

      // Full-window backdrops, each in the panel it lives in.
      const dialogs = await p.evaluate(() => [...document.querySelectorAll(".gp-backdrop[id], .tv-pop-backdrop[id], #cal-signoff-modal")]
        .map((d) => ({ id: d.id, panel: (d.closest(".panel") || {}).id || "" })));
      for (const d of dialogs) {
        if (d.panel) { await p.evaluate((id) => { try { switchPanel(id); } catch (e) {} }, d.panel.slice(6)); await p.waitForTimeout(350); }
        await p.evaluate(showTabs, [d.id, true]);
        await p.evaluate((id) => { const e = document.getElementById(id); if (id === "cal-signoff-modal") e.style.display = "flex"; else e.classList.add("open"); }, d.id);
        await settle(p);
        checks++;
        (await p.evaluate(cover, "#" + d.id)).forEach((m) => fails.push(`${tag}: dialog ${m}`));
        await p.evaluate((id) => { const e = document.getElementById(id); if (id === "cal-signoff-modal") e.style.display = "none"; else e.classList.remove("open"); }, d.id);
        await p.evaluate(showTabs, [d.id, false]);
      }
      errors.forEach((e) => fails.push(`${tag}: script error on the page: ${e}`));
      console.log(`${tag}: ${panels.length} panels scanned, ${dialogs.length} dialogs, 7 trays`);
      await ctx.close();
    }
  }
  await browser.close();
  return { fails, checks };
}

(async () => {
  const st = staticCheck();
  st.bad.forEach((m) => console.log("FAIL " + m));
  console.log(`static: ${st.count} position:fixed elements found, ${Object.keys(INVENTORY).length} in INVENTORY, ${st.bad.length} problems`);
  if (process.argv.includes("--static")) process.exit(st.bad.length ? 1 : 0);
  const br = await browserCheck();
  br.fails.forEach((m) => console.log("FAIL " + m));
  console.log(`browser: ${br.checks} checks, ${br.fails.length} failures`);
  process.exit(st.bad.length || br.fails.length ? 1 : 0);
})();
