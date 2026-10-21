/* Does the Positions screen actually work in a real browser? (slice 064, v9)
 *
 * The node check (check_positions_tree.js) proves what the page draws; the
 * connector check (check_positions_connectors.js) proves the lines are
 * honest. This one drives the screen the way a person would and writes
 * screenshots somebody can look at.
 *
 * NOT part of CI. It needs a running site, a login and a browser. Run it on
 * a THROWAWAY site, never a real one:
 *
 *   BASE=http://127.0.0.1:8064 PROBE_USR=... PROBE_PWD=... \
 *     PLAYWRIGHT=<path to playwright> node scripts/browser_check_positions.js
 *
 * It prints a line per check, saves PNGs to $SHOTS, and exits non-zero if
 * any check fails.
 */
const { chromium } = require(process.env.PLAYWRIGHT || "playwright");

const BASE = process.env.BASE || "http://127.0.0.1:8000";
const USR = process.env.PROBE_USR, PWD = process.env.PROBE_PWD;
const SHOTS = process.env.SHOTS || "/tmp/shots/";

let pass = 0, fail = 0;
const ok = (cond, msg, detail) => cond ? (pass++, console.log("  PASS  " + msg))
  : (fail++, console.log("  FAIL  " + msg + (detail ? "  (" + detail + ")" : "")));

(async () => {
  if (!USR || !PWD) { console.error("Set PROBE_USR and PROBE_PWD for a user on a THROWAWAY site."); process.exit(2); }
  const b = await chromium.launch();
  const page = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  const errors = [], requests = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("request", (r) => requests.push(r.url()));
  await page.goto(BASE + "/alvoraa-login", { waitUntil: "networkidle" });
  await page.fill("#kx-email", USR); await page.fill("#kx-password", PWD);
  await Promise.all([page.waitForNavigation({ waitUntil: "networkidle" }).catch(() => {}),
                     page.click("#kx-login-form button[type=submit]")]);
  await page.goto(BASE + "/hrms-employee", { waitUntil: "networkidle" });
  await page.evaluate(() => switchPanel("positions"));
  await page.waitForFunction(() => window.POS && POS.rows && POS.rows.length > 0, null, { timeout: 30000 });
  await page.waitForTimeout(800);

  const home = await page.evaluate(() => ({
    pressed: (document.querySelector('#pos-view button[aria-pressed="true"]') || {}).textContent,
    boxes: document.querySelectorAll("#pos-body .pos-box").length,
    groups: document.querySelectorAll("#pos-body .pos-sibs").length,
    width: Math.round((document.querySelector("#pos-body .pos-box") || { getBoundingClientRect: () => ({ width: 0 }) }).getBoundingClientRect().width),
    page: document.documentElement.scrollWidth - innerWidth,
  }));
  ok(home.pressed === "Reporting lines", "the page opens on Reporting lines", home.pressed);
  ok(home.boxes > 1 && home.groups >= 1, "the chart draws boxes and a group", home.boxes + " boxes");
  ok(home.width > 150, "a box has real width on screen", home.width + "px");
  ok(home.page <= 0, "the page itself never scrolls sideways", home.page + "px");
  await page.screenshot({ path: SHOTS + "positions-home.png", fullPage: true });

  // A team opens below its group, with its own line.
  await page.click("#pos-body .pos-sibs .pos-fold");
  await page.waitForTimeout(400);
  const opened = await page.evaluate(() => ({
    strip: document.querySelectorAll("#pos-body .pos-strip").length,
    line: document.querySelectorAll("#pos-body svg.pos-links path").length,
  }));
  ok(opened.strip === 1 && opened.line === 1, "opening a team draws its strip and one line", JSON.stringify(opened));
  await page.screenshot({ path: SHOTS + "positions-team-open.png", fullPage: true });

  // The seat sheet: a dialog, focus on its heading, Escape closes it.
  await page.click("#pos-body .pos-box[data-id]");
  await page.waitForTimeout(300);
  const sheet = await page.evaluate(() => ({
    dialog: !!document.querySelector('#pos-layer [role="dialog"]'),
    focus: document.activeElement && document.activeElement.id,
  }));
  ok(sheet.dialog && sheet.focus === "pos-sh-t", "a box opens the seat sheet with focus on its heading", JSON.stringify(sheet));
  await page.screenshot({ path: SHOTS + "positions-seat-sheet.png" });
  await page.keyboard.press("Escape");
  ok(await page.evaluate(() => !document.querySelector('#pos-layer [role="dialog"]')), "Escape closes it");

  // Find makes no request while typing.
  const before = requests.length;
  await page.fill("#pos-find", "Sta");
  await page.waitForTimeout(400);
  ok(requests.length === before, "typing in Find sends nothing to the server", (requests.length - before) + " requests");
  ok(await page.evaluate(() => document.querySelectorAll("#pos-hits .pos-hit").length > 0), "Find lists matches");
  await page.keyboard.press("Escape");

  for (const v of ["branch", "department", "list"]) {
    await page.evaluate((vv) => posSetView(vv), v);
    await page.waitForTimeout(400);
    const html = await page.evaluate(() => document.getElementById("pos-body").innerHTML);
    ok(html.length > 100 && !/undefined|NaN/.test(html), "the " + v + " view draws, nothing reads undefined");
    await page.screenshot({ path: SHOTS + "positions-" + v + ".png", fullPage: true });
  }

  // An editor's "Change this seat" still opens today's dialog.
  await page.evaluate(() => { posSetView("reporting"); posSeatSheet(POS.rows[0].id); });
  const canEdit = await page.evaluate(() => POS.may_edit);
  if (canEdit) {
    await page.click("text=Change this seat");
    await page.waitForTimeout(500);
    ok(await page.evaluate(() => document.getElementById("pos-editor").classList.contains("open")), "Change this seat opens today's dialog");
  }

  ok(errors.length === 0, "no JavaScript errors on the page", errors.slice(0, 2).join(" | "));
  await b.close();
  console.log("\n  " + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})();
