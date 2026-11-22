/* Slice 089, defect D-1: the report icon on the Scorecard must be the thing a
   finger lands on.

   jsdom has no layout, so the DOM test can click() an icon that is drawn under
   the "Joined" badge and still pass. This one needs a real browser: it lays out
   the real Scorecard header (the template's own markup, frame.css and
   panels.css, and portal.js's own lvHeader) and asks the browser what is on top
   at the icon's centre, at 360 px, 390 px and desktop width.

   Run: node alvoraa_portal/tests/portal_leaver_report_089_layout_chrome.js
   It needs a headless Chromium (env CHROME, or the Playwright cache). It is
   named *_chrome.js, not *_test.js, because CI has no Chromium and
   scripts/run_dom_tests.js runs every *_test.js. If no Chromium is found it
   FAILS rather than passing quietly. */
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const APP = path.join(__dirname, "..", "alvoraa_portal");
const CSS = ["frame.css", "panels.css"].map(f => path.join(APP, "public", "css", "ess", f));
const PORTAL = fs.readFileSync(path.join(APP, "public", "js", "ess", "portal.js"), "utf8");
const PART = fs.readFileSync(path.join(APP, "templates", "includes", "ess", "parts", "appraisals.html"), "utf8");

function findChrome() {
  if (process.env.CHROME) return process.env.CHROME;
  const base = path.join(os.homedir(), "Library", "Caches", "ms-playwright");
  if (fs.existsSync(base)) {
    for (const d of fs.readdirSync(base).filter(x => x.startsWith("chromium_headless_shell"))) {
      const dir = path.join(base, d);
      for (const sub of fs.readdirSync(dir)) {
        const exe = path.join(dir, sub, "chrome-headless-shell");
        if (fs.existsSync(exe)) return exe;
      }
    }
  }
  return null;
}

function between(src, from, to) {
  const a = src.indexOf(from);
  const b = src.indexOf(to, a);
  if (a < 0 || b < 0) throw new Error("cannot find <" + from + "> in the source");
  return src.slice(a, b);
}

/* The page under test: the real header markup, the real CSS, the real lvHeader. */
const topbar = between(PART, '<div class="sc-topbar">', '<div class="sc-body"');
const lvFns = between(PORTAL, "function lvFirst(", "function lvNote(");
const page = "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
  + CSS.map(f => "<style>" + fs.readFileSync(f, "utf8") + "</style>").join("")
  + "</head><body><div class='panel active' id='panel-scorecard'>" + topbar + "</div><script>"
  + "var LV={}; function drT(t,a){return String(t).replace('{0}',(a||[])[0]);} function lvOpen(){}\n"
  + lvFns + "\n"
  + "document.getElementById('sc-emp-name').textContent='Asha Rao';"
  + "document.getElementById('sc-emp-role').textContent='Store Associate • Retail';"
  + "document.getElementById('sc-avatar').textContent='AR';"
  + "document.getElementById('sc-join-badge').textContent='Joined 1 Jan 2025';"
  + "lvHeader({can_report:true, employee:{name:'HR-EMP-1', employee_name:'Asha Rao'}});"
  + "</script></body></html>";

const PROBE = `(function(){
  var b=document.getElementById('sc-left-btn'); if(!b) return {noIcon:true};
  var r=b.getBoundingClientRect(), t=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2);
  return {w:r.width, h:r.height, onTop: !!t && (t===b || b.contains(t)),
          topIs: t ? t.tagName+'.'+String(t.className && t.className.baseVal!==undefined ? t.className.baseVal : t.className) : null,
          inView: r.left>=0 && r.right<=innerWidth,
          sideways: document.documentElement.scrollWidth>innerWidth};
})()`;

let pass = 0, fail = 0;
const check = (c, m) => { if (c) { pass++; console.log("  PASS  " + m); } else { fail++; console.log("  FAIL  " + m); } };

(async () => {
  const chrome = findChrome();
  if (!chrome) { console.log("  FAIL  no headless Chromium found; set CHROME to its path"); process.exit(1); }
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "alv089-")), "scorecard.html");
  fs.writeFileSync(file, page);
  const port = 9300 + Math.floor(Math.random() * 500);
  const proc = spawn(chrome, ["--remote-debugging-port=" + port, "--no-first-run",
    "--user-data-dir=" + path.dirname(file), "about:blank"], { stdio: "ignore" });
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  let ws;
  for (let i = 0; i < 50 && !ws; i++) {
    try {
      const pg = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(x => x.type === "page");
      if (pg) ws = new WebSocket(pg.webSocketDebuggerUrl);
    } catch (e) { await sleep(200); }
  }
  if (!ws) { proc.kill(); console.log("  FAIL  Chromium did not start"); process.exit(1); }
  await new Promise(r => (ws.onopen = r));
  let id = 0; const pend = new Map();
  ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } };
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  try {
    for (const [w, h] of [[360, 780], [390, 844], [1280, 800]]) {
      await send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: w < 600 });
      await send("Page.navigate", { url: "file://" + file });
      await sleep(900);
      const r = (await send("Runtime.evaluate", { expression: PROBE, returnByValue: true })).result.result.value;
      check(r && !r.noIcon, w + " px: the icon is drawn");
      if (!r || r.noIcon) continue;
      check(r.onTop, w + " px: the icon is the top element at its centre (top is " + r.topIs + ")");
      check(r.w >= 44 && r.h >= 44, w + " px: the tap area is at least 44 x 44 (" + Math.round(r.w) + " x " + Math.round(r.h) + ")");
      check(r.inView && !r.sideways, w + " px: inside the screen, no sideways scroll");
    }
  } finally { ws.close(); proc.kill(); }
  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
