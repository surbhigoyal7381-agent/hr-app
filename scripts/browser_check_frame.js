/* Does the frame actually boot in a REAL browser, and does frappe.call exist
 * on a Frappe WEBSITE page?
 *
 * This is the assumption the whole browser-side stretch of slice 034 rests on,
 * and until 2026-09-24 nothing had tested it. The evidence was `curl`, which
 * runs no JavaScript, and jsdom, where `frappe.call` was the test's own stub -
 * a stub that called `opts.error` on a failure, which no real browser does.
 *
 * It is NOT part of CI. It needs a running site, a real login and a browser, so
 * it is a hands-on check to run before the swap and after a change to the
 * frame's call path. CI covers the same behaviour in jsdom, against a stub that
 * now matches what this script found.
 *
 * WHAT IT FOUND, 2026-09-24, Frappe v16.33.1, Chromium 153, on a throwaway
 * local site - all four recorded in next-frame.js beside the code they explain:
 *
 *   1. frappe.call IS there on a website page. The frame boots: 18 menu
 *      entries, 5 bottom tabs, the avatar drawn, no error state, no page error.
 *   2. It is website.js's frappe.call, not the desk one, and that version NEVER
 *      calls opts.error - with a stale CSRF token only `always` fired. A
 *      promise built on it never settles, so the old code would have left the
 *      frame on "Loading" for ever with nothing in any log.
 *   3. A session that has ENDED is answered 403 PermissionError, not 401 - and
 *      the same response rewrites the user_id cookie to Guest. That cookie is
 *      what separates "signed out" from "refused".
 *   4. With the fix, a stale token is mended in one round trip and the frame
 *      boots; a dead session lands on the login page.
 *
 * HOW TO RUN IT, inside your own container (never the shared bench):
 *
 *   apt-get install -y chromium                       # as root, once
 *   mkdir -p /tmp/browser && cd /tmp/browser
 *   npm init -y && npm install puppeteer-core
 *   bench --site <site> serve --port 8000 &           # your own site
 *   # a user who is a System Manager AND has an Employee record
 *   PROBE_USR=... PROBE_PWD=... node scripts/browser_check_frame.js
 *
 * It prints a line per check and exits non-zero if any fails.
 */

const puppeteer = require(process.env.PUPPETEER ||
  "/tmp/browser/node_modules/puppeteer-core");

const BASE = process.env.BASE || "http://127.0.0.1:8000";
const PAGE = process.env.PAGE || "/hrms-employee-next";
const USR = process.env.PROBE_USR;
const PWD = process.env.PROBE_PWD;

let pass = 0, fail = 0;
const is = (got, want, msg) =>
  String(got) === String(want)
    ? (pass++, console.log("  PASS  " + msg))
    : (fail++, console.log("  FAIL  " + msg + "  (got " + JSON.stringify(got) +
                           ", wanted " + JSON.stringify(want) + ")"));

async function main() {
  if (!USR || !PWD) {
    console.error("Set PROBE_USR and PROBE_PWD to a System Manager who also has " +
                  "an Employee record on the site you are serving.");
    process.exit(2);
  }

  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME || "/usr/bin/chromium",
    args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });
  const page = await browser.newPage();
  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(e.message));

  /* Sign in through the browser, so the cookies are the real ones. */
  await page.goto(BASE + "/login", { waitUntil: "domcontentloaded" });
  const login = await page.evaluate(async (usr, pwd) => {
    const r = await fetch("/api/method/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      credentials: "same-origin", body: JSON.stringify({ usr, pwd }),
    });
    return r.status;
  }, USR, PWD);
  is(login, 200, "the test user can sign in");

  const resp = await page.goto(BASE + PAGE, { waitUntil: "networkidle0", timeout: 30000 });
  is(resp.status(), 200, "the preview page answers 200 for a System Manager");
  await new Promise((r) => setTimeout(r, 1500));

  /* 1. the assumption itself */
  const facts = await page.evaluate(() => {
    const src = (window.frappe && typeof frappe.call === "function")
      ? frappe.call.toString() : "";
    const state = document.getElementById("nf-state");
    return {
      call_exists: !!(window.frappe && typeof frappe.call === "function"),
      is_website_version: /prepare_call/.test(src),
      booting: document.getElementById("nf-root").hasAttribute("data-nf-booting"),
      state: state && !state.hidden ? state.getAttribute("data-kind") : null,
      menu: document.querySelectorAll("#nf-menu [data-route]").length,
      tabs: document.querySelectorAll("#nf-bottom .nf-tab").length,
      loaded: !!window.NextFrame,
    };
  });
  is(facts.call_exists, true, "frappe.call EXISTS on a Frappe website page");
  is(facts.is_website_version, true,
     "and it is website.js's version, which never calls opts.error - " +
     "which is why the frame does not use it");
  is(facts.loaded, true, "next-frame.js ran");
  is(facts.booting, false, "the frame finished booting");
  is(facts.state, null, "and is not showing an error or a spinner");
  is(facts.menu > 0, true, "the menu was drawn: " + facts.menu + " entries");
  is(facts.tabs > 0, true, "the bottom bar was drawn: " + facts.tabs + " tabs");

  /* 2. a stale CSRF token, the F4 scenario, end to end */
  const stale = await page.evaluate(async () => {
    const before = frappe.csrf_token;
    frappe.csrf_token = "stale-token-deadbeef";
    let outcome;
    try { await window.NextFrame.boot(); outcome = "booted"; }
    catch (e) { outcome = "threw: " + e.message; }
    const state = document.getElementById("nf-state");
    return { outcome,
             mended: frappe.csrf_token === before,
             state: state && !state.hidden ? state.getAttribute("data-kind") : null };
  });
  is(stale.outcome, "booted", "a stale CSRF token does not break the frame (F4)");
  is(stale.mended, true, "the token was read fresh off the page and put back");
  is(stale.state, null, "and the person never saw the error state");

  /* 3. a session that has really ended */
  const client = await page.target().createCDPSession();
  await client.send("Network.deleteCookies", { name: "sid", url: BASE + "/" });
  await page.evaluate(() => { window.NextFrame.boot(); });
  await new Promise((r) => setTimeout(r, 4000));
  is(/\/(alvoraa-)?login/.test(page.url()), true,
     "a session that has ended sends the person to the login page (AC-62), " +
     "landed on " + page.url());

  is(pageErrors.length, 0, "no uncaught JavaScript errors: " + JSON.stringify(pageErrors));

  await browser.close();
  console.log("\nframe in a real browser: " + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
}

main().catch((e) => { console.error("check failed to run:", e); process.exit(1); });
