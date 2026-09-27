/* ALV-149, ALV-152, ALV-153 in a REAL browser.
 *
 * The unit tests prove the data (an Action row, two CSS selectors, en.csv) and
 * pin the Frappe lines the fixes rely on. What they cannot prove is the click:
 * the ALV-152 bug hid for a month behind tests that read a script's text. So:
 *
 *   1. /hrms-employee: Frappe's avatar menu shows neither "Switch To Desk" nor
 *      "Apps"; "My Account" and "Log out" are still there (ALV-153).
 *   2. The desk user menu has "Switch to Employee Portal", and clicking it lands
 *      on /hrms-employee (ALV-152).
 *   3. The desk shows "Alvora Position", not "Alvoraa Position" (ALV-149).
 *   4. No visible "Alvoraa" on the portal page or the desk list page.
 *
 * NOT part of CI: it needs a running site, a login and a browser. Run it inside
 * your own container, never the shared bench:
 *
 *   apt-get install -y chromium                       # as root, once
 *   mkdir -p /tmp/browser && cd /tmp/browser && npm init -y && npm install puppeteer-core
 *   bench --site <site> serve --port 8000 &
 *   # a user with System Manager AND an Employee record
 *   PROBE_USR=... PROBE_PWD=... NODE_PATH=/tmp/browser/node_modules \
 *     node scripts/browser_check_brand_menus.js
 *
 * Prints one line per check and exits non-zero if any fails.
 */
"use strict";

const puppeteer = require("puppeteer-core");

const BASE = process.env.BASE_URL || "http://127.0.0.1:8000";
const USR = process.env.PROBE_USR;
const PWD = process.env.PROBE_PWD;
const CHROME = process.env.CHROME || "/usr/bin/chromium";

let failed = 0;
function check(ok, what, detail) {
  console.log((ok ? "ok   " : "FAIL ") + what + (detail ? "  (" + detail + ")" : ""));
  if (!ok) failed += 1;
}

const visibleBrandText = () => {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const hits = [];
  while (walker.nextNode()) {
    const n = walker.currentNode;
    const el = n.parentElement;
    if (!el || ["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"].includes(el.tagName)) continue;
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden") continue;
    if (/Alvoraa|ALVORAA/.test(n.nodeValue)) hits.push(n.nodeValue.trim().slice(0, 80));
  }
  return hits.concat(/Alvoraa|ALVORAA/.test(document.title) ? ["<title> " + document.title] : []);
};

(async () => {
  if (!USR || !PWD) throw new Error("set PROBE_USR and PROBE_PWD");
  const browser = await puppeteer.launch({ executablePath: CHROME, args: ["--no-sandbox"] });
  const page = await browser.newPage();
  page.setDefaultTimeout(30000);

  const login = await page.goto(BASE + "/api/method/login", { waitUntil: "load" });
  const res = await page.evaluate(async (u, p) => {
    const r = await fetch("/api/method/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usr: u, pwd: p }),
    });
    return r.status;
  }, USR, PWD);
  check(res === 200, "logged in", "HTTP " + res + " (first page " + login.status() + ")");

  // ── 1 · the portal's avatar menu (ALV-153) ──────────────────────────────
  await page.goto(BASE + "/hrms-employee", { waitUntil: "networkidle2" });
  const menu = await page.evaluate(() => {
    const shown = (sel) => {
      const el = document.querySelector(sel);
      return el ? getComputedStyle(el).display !== "none" : null;
    };
    return {
      desk: shown("#website-post-login .switch-to-desk"),
      apps: shown("#website-post-login .apps"),
      myAccount: [...document.querySelectorAll("#website-post-login a.dropdown-item")]
        .some((a) => a.getAttribute("href") && a.getAttribute("href").endsWith("/me")),
    };
  });
  check(menu.desk === false, "portal avatar menu: Switch To Desk is hidden", JSON.stringify(menu));
  check(menu.apps === false, "portal avatar menu: Apps is hidden");
  check(menu.myAccount === true, "portal avatar menu: My Account is still there");
  const portalHits = await page.evaluate(visibleBrandText);
  check(portalHits.length === 0, "portal page: no visible Alvoraa", portalHits.join(" | "));

  // ── 2 · the desk menu item (ALV-152) ─────────────────────────────────────
  // The menu hangs off the sidebar header, which a workspace page draws (a
  // list page such as /desk/alvoraa-position may not). Its title is also a
  // translated workspace name, so it is checked here too.
  await page.goto(BASE + "/desk/alvoraa-portal", { waitUntil: "networkidle2" });
  await page.waitForSelector(".sidebar-header");
  const header = await page.evaluate(() =>
    (document.querySelector(".sidebar-header .header-title") || {}).textContent || "");
  check(header.trim() === "Alvora Portal", "desk workspace header says Alvora Portal", header.trim());
  await page.click(".sidebar-header");
  await page.waitForSelector(".frappe-menu.context-menu .dropdown-menu-item");
  const clicked = await page.evaluate(() => {
    const item = [...document.querySelectorAll(".frappe-menu.context-menu .dropdown-menu-item")]
      .find((d) => d.textContent.trim() === "Switch to Employee Portal");
    if (!item) return false;
    item.click();
    return true;
  });
  check(clicked, "desk menu: Switch to Employee Portal is there");
  if (clicked) {
    await page.waitForFunction(() => location.pathname === "/hrms-employee", { timeout: 15000 })
      .catch(() => {});
    const where = await page.evaluate(() => location.pathname);
    check(where === "/hrms-employee", "desk menu: the click lands on the portal", where);
  }

  // ── 3 · desk labels (ALV-149) ────────────────────────────────────────────
  await page.goto(BASE + "/desk/alvoraa-position", { waitUntil: "networkidle2" });
  await page.waitForSelector(".page-title .title-text", { timeout: 30000 }).catch(() => {});
  const title = await page.evaluate(() => {
    const t = document.querySelector(".page-title .title-text");
    return t ? t.textContent.trim() : "";
  });
  check(title === "Alvora Position", "desk list title says Alvora Position", title);
  const deskHits = await page.evaluate(visibleBrandText);
  check(deskHits.length === 0, "desk list page: no visible Alvoraa", deskHits.join(" | "));

  await browser.close();
  console.log(failed ? `${failed} check(s) FAILED` : "all checks passed");
  process.exit(failed ? 1 : 0);
})().catch((e) => {
  console.error("FAIL " + e.message);
  process.exit(2);
});
