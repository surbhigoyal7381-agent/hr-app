/* Does the Positions screen actually draw in a real browser?
 *
 * Everything else about this screen is checked without one: the markup
 * balances, the handlers resolve, the tree renders in a VM, the endpoints have
 * tests. None of that can see a screen that LOOKS wrong, and this screen was
 * rebuilt once for exactly that reason - an indented table that read as a list
 * passed every check it had.
 *
 * So this opens it, drives it, and writes screenshots somebody can look at.
 *
 * NOT part of CI. It needs a running site, a real login and a browser, so it
 * is a hands-on check to run in YOUR OWN container - never the shared bench -
 * after a change to this screen.
 *
 *   apt-get install -y chromium                   # as root, once
 *   mkdir -p /tmp/browser && cd /tmp/browser
 *   npm init -y && npm install puppeteer-core
 *   bench --site <throwaway site> serve --port 8000 &
 *   PROBE_USR=... PROBE_PWD=... node scripts/browser_check_positions.js
 *
 * It prints a line per check, saves PNGs to /tmp/shots, and exits non-zero if
 * any check fails.
 */

const fs = require("fs");
const puppeteer = require(process.env.PUPPETEER ||
  "/tmp/browser/node_modules/puppeteer-core");

const BASE = process.env.BASE || "http://127.0.0.1:8000";
const USR = process.env.PROBE_USR;
const PWD = process.env.PROBE_PWD;
const SHOTS = process.env.SHOTS || "/tmp/shots";
const CHROME = process.env.CHROME || "/usr/bin/chromium";

let pass = 0, fail = 0;
const ok = (cond, msg, detail) =>
  cond ? (pass++, console.log("  PASS  " + msg))
       : (fail++, console.log("  FAIL  " + msg
            + (detail ? "  (" + detail + ")" : "")));

async function shot(page, name) {
  fs.mkdirSync(SHOTS, { recursive: true });
  const at = SHOTS + "/" + name + ".png";
  await page.screenshot({ path: at, fullPage: true });
  console.log("  shot  " + at);
}

async function main() {
  if (!USR || !PWD) {
    console.error("Set PROBE_USR and PROBE_PWD for a user on the site you are "
                  + "serving. Use a THROWAWAY site, never a real one.");
    process.exit(2);
  }
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 1000 });

  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));

  // ── sign in ───────────────────────────────────────────────────────────────
  await page.goto(BASE + "/login", { waitUntil: "networkidle2" });
  await page.type("#login_email", USR);
  await page.type("#login_password", PWD);
  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle2" }),
    page.click(".btn-login"),
  ]);

  // ── the portal, then the Positions panel ──────────────────────────────────
  await page.goto(BASE + "/hrms-employee", { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 2500));

  const hasPanel = await page.evaluate(() =>
    !!document.getElementById("panel-positions"));
  ok(hasPanel, "the Positions panel is on the page");
  if (!hasPanel) { await shot(page, "00-no-panel"); await browser.close();
                   process.exit(1); }

  await page.evaluate(() => switchPanel("positions"));
  await new Promise((r) => setTimeout(r, 2500));

  // ── the list, which is the default ────────────────────────────────────────
  const list = await page.evaluate(() => ({
    rows: document.querySelectorAll("#pos-body table tbody tr").length,
    count: (document.getElementById("pos-count") || {}).textContent || "",
    body: (document.getElementById("pos-body") || {}).innerHTML || "",
  }));
  ok(list.rows > 0, "the list draws rows", "got " + list.rows);
  ok(/seat/.test(list.count), "the count says something", list.count);
  ok(!/Loading/.test(list.body), "it is not still loading");
  await shot(page, "01-list");

  // ── the structure view, which is the thing that was wrong before ──────────
  await page.evaluate(() => {
    document.getElementById("pos-f-view").value = "tree";
    posPaint();
  });
  await new Promise((r) => setTimeout(r, 1200));

  const tree = await page.evaluate(() => {
    const body = document.getElementById("pos-body");
    const box = document.querySelector("#pos-body .oc-box");
    return {
      boxes: document.querySelectorAll("#pos-body .oc-box").length,
      kids: document.querySelectorAll("#pos-body .oc-kids").length,
      isTable: !!document.querySelector("#pos-body table"),
      // The thing a VM cannot tell you: does a box have real width on screen?
      boxWidth: box ? Math.round(box.getBoundingClientRect().width) : 0,
      wide: body ? body.scrollWidth > body.clientWidth : false,
    };
  });
  ok(tree.boxes > 1, "the structure view draws boxes", "got " + tree.boxes);
  ok(tree.kids > 0, "with connectors between them", "got " + tree.kids);
  ok(!tree.isTable, "and it is NOT a table");
  ok(tree.boxWidth > 120, "a box has real width on screen",
     tree.boxWidth + "px");
  await shot(page, "02-structure");

  // ── grouping: five identical seats should be one box ──────────────────────
  const grouped = await page.evaluate(() =>
    (document.getElementById("pos-body").innerHTML.match(/of these/g) || []).length);
  ok(grouped > 0, "identical seats are grouped into one box",
     "found " + grouped + " group box(es)");

  // ── the seat dialog ───────────────────────────────────────────────────────
  await page.evaluate(() => {
    const id = POS.rows.filter((r) => r.people.length)[0].id;
    posOpenEditor(id);
  });
  await new Promise((r) => setTimeout(r, 900));
  const dlg = await page.evaluate(() => {
    const el = document.getElementById("pos-editor");
    const r = el ? el.getBoundingClientRect() : null;
    return {
      open: !!(el && el.classList.contains("open")),
      visible: !!(r && r.width > 100 && r.height > 100),
      people: (document.getElementById("pos-people") || {}).innerHTML || "",
      offscreen: r ? (r.top < -50 || r.left < -50) : true,
    };
  });
  ok(dlg.open, "clicking a seat opens the dialog");
  ok(dlg.visible, "and the dialog has real size on screen");
  ok(!dlg.offscreen, "and it is not off the edge of the window");
  ok(!/Nobody is in this seat/.test(dlg.people),
     "a filled seat lists its people");
  await shot(page, "03-seat-dialog");

  // ── the person picker ─────────────────────────────────────────────────────
  await page.evaluate(() => posPickPerson());
  await new Promise((r) => setTimeout(r, 1800));
  const pick = await page.evaluate(() => ({
    open: document.getElementById("pos-person").classList.contains("open"),
    list: (document.getElementById("pos-p-list") || {}).textContent || "",
  }));
  ok(pick.open, "the person picker opens");
  ok(!/Looking/.test(pick.list), "and it finishes looking");
  await shot(page, "04-person-picker");

  ok(errors.length === 0, "no JavaScript errors on the page",
     errors.slice(0, 2).join(" | "));

  await browser.close();
  console.log("\n  " + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(1); });
