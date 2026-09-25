/* Does the self-review really save, really resume, and really send?
 *
 * **This file exists because the check that said it did was wrong.**
 *
 * `browser_check_growth_team.js` asserted "and it is still there after a
 * reload - the wizard resumes", and it passed. It was reading the value still
 * sitting in the DOM: its "reload" was
 * `page.goto(BASE + PAGE + "#growth/review")` to **the URL the browser was
 * already on, fragment and all**, which Chrome treats as a same-document
 * navigation. Nothing reloaded. Meanwhile the draft really was being lost -
 * `get_self_review` handed back the whole `page_data` while the save wrote
 * under `page_data["wizard"]`, so a reload showed an empty wizard and each
 * save buried the one before it a level deeper.
 *
 * So every reload here is `page.reload()`, and **every one of them is proved**
 * by a marker put on `window` first: if the marker is still there, the
 * document did not reload and the assertion that follows would be worthless.
 * That guard is the point of the file. jsdom cannot make this mistake and
 * cannot catch it either - it has no navigation at all.
 *
 * It is NOT part of CI. It needs a running site, a real login and a browser.
 * Run it in your OWN container, never the shared bench.
 *
 *   apt-get install -y chromium                       # as root, once
 *   mkdir -p /tmp/browser && cd /tmp/browser
 *   npm init -y && npm install puppeteer-core
 *   bench --site <site> execute alvoraa_portal.tests.make_browser_probe.main
 *   bench --site <site> serve --port 8000 &
 *   PROBE_USR=... PROBE_PWD=... node scripts/browser_check_self_review.js
 *
 * **Run `make_browser_probe.main` again before every run.** It puts the
 * probe's review back to a draft, because the last thing this file does is
 * send it - and a sent review cannot be typed in again, which is the whole
 * point of AC-95.
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

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

/* Put a marker on the window, so the next assertion can prove the document
   really was thrown away. A "reload" that keeps it reloaded nothing. */
const MARK = "__alvoraaSameDocument";
const mark = (page) => page.evaluate((k) => { window[k] = 1; }, MARK);
const reloaded = (page) => page.evaluate((k) => !window[k], MARK);

async function main() {
  if (!USR || !PWD) {
    console.error("Set PROBE_USR and PROBE_PWD to a user with an open review " +
                  "on the site you are serving.");
    process.exit(2);
  }

  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME || "/usr/bin/chromium",
    args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });
  const page = await browser.newPage();
  /* A phone. Rahul is on a factory floor with one. */
  await page.setViewport({ width: 390, height: 780, deviceScaleFactor: 2 });
  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(e.message));

  await page.goto(BASE + "/login", { waitUntil: "domcontentloaded" });
  const login = await page.evaluate(async (usr, pwd) => {
    const r = await fetch("/api/method/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      credentials: "same-origin", body: JSON.stringify({ usr, pwd }),
    });
    return r.status;
  }, USR, PWD);
  is(login, 200, "the probe user can sign in");

  await page.goto(BASE + PAGE + "#growth/review",
                  { waitUntil: "networkidle0", timeout: 30000 });
  await wait(2500);

  /* Nothing below means anything if the scripts did not run. Asserted first,
     because a dead page answers "no error showing" exactly as a live one
     does - the trap that cost this project a week in Wave 1. */
  const up = await page.evaluate(() => ({
    frame: !!window.NextFrame, growth: !!window.NextGrowth,
    rates: document.querySelectorAll("[data-rate]").length,
  }));
  is(up.frame && up.growth, true,
     "the frame and the wizard really ran - if this fails, look at " +
     "/assets/alvoraa_portal/ess/ before reading anything below");
  is(up.rates >= 5, true, "the whole-point buttons are on the screen");

  /* ── a rating and a typed answer, then a REAL reload ─────────────────── */

  const typed = "probe " + Date.now();
  const rated = await page.evaluate(async (t) => {
    const btn = document.querySelector('[data-block="goals"][data-rate="4"]');
    if (btn) { btn.click(); }
    /* Painting replaces the nodes, so the box is found after the click. */
    const box = document.querySelector("#nf-screens textarea");
    box.value = t;
    box.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 6000));   /* past the idle timer */
    return !!btn;
  }, typed);
  is(rated, true, "a goal rating was pressed");
  await wait(1500);
  is(/Saved at/.test(await page.evaluate(() =>
       (document.getElementById("nf-wiz-room") || {}).textContent || "")), true,
     "the autosave landed and the screen says when - the SERVER's time");

  await mark(page);
  await page.reload({ waitUntil: "networkidle0", timeout: 30000 });
  await wait(3000);
  is(await reloaded(page), true,
     "the document really was reloaded - without this the next two checks " +
     "read the value that never left the browser");

  const resumed = await page.evaluate((t) => {
    const state = window.NextGrowth._state();
    return {
      text: Array.from(document.querySelectorAll("#nf-screens textarea"))
              .map((b) => b.value).some((v) => v.indexOf(t) !== -1),
      chosen: !!document.querySelector(".nf-rate-on"),
      depth: JSON.stringify(state.answers).indexOf("wizard"),
      step: (document.getElementById("nf-wiz-progress") || {}).textContent || "",
    };
  }, typed);
  is(resumed.text, true,
     "AC-97: what was typed is still there after a REAL reload");
  is(resumed.chosen, true, "and the rating is still chosen");
  is(resumed.depth, -1,
     "AC-97: the answers came back at the top level, not buried under a " +
     "'wizard' key that the next save would bury again");
  is(/Step [1-9]/.test(resumed.step), true,
     'AC-28: "step n of 5" counts the draft that came back');

  /* ── Send: refused while something is unrated, then sent ─────────────── */

  const last = await page.evaluate(async () => {
    const steps = window.NextGrowth._state().review.steps.length;
    for (let i = 0; i < steps; i++) {
      const next = document.getElementById("nf-wiz-next");
      if (!next) { break; }
      next.click();
      await new Promise((r) => setTimeout(r, 400));
    }
    return {
      send: !!document.getElementById("nf-wiz-send"),
      disabled: (document.getElementById("nf-wiz-send") || {}).disabled,
      blank: /leaving these empty/.test(
        document.getElementById("nf-screens").textContent),
    };
  });
  is(last.send, true, "the last step offers Send");
  is(last.disabled, false,
     "and it is never greyed out - the server says what is missing");
  is(last.blank, true,
     "D-13: the written steps left empty are named before sending");

  await page.evaluate(() => document.getElementById("nf-wiz-send").click());
  /* Read the toast while it is still on screen - it removes itself after four
     seconds, and a check that waits longer than the message lives is a check
     that fails for a reason that has nothing to do with the product. */
  await wait(2000);
  const refused = await page.evaluate(() => ({
    said: (document.getElementById("nf-toasts") || {}).textContent || "",
    still: !!document.getElementById("nf-wiz-send"),
  }));
  is(/still needs? a rating/.test(refused.said), true,
     "AC-89: the values are not rated, so the SERVER refuses and names what " +
     "is missing - it said: " + JSON.stringify(refused.said.slice(0, 160)));
  is(refused.still, true, "and the wizard is still there to finish");

  /* Rate every value, then send for real. */
  await page.evaluate(async () => {
    const state = window.NextGrowth._state();
    state.review.values.forEach((v) => {
      state.answers.values = state.answers.values || {};
      state.answers.values[v.name] = { rating: 4 };
    });
  });
  await page.evaluate(() => document.getElementById("nf-wiz-send").click());
  await wait(4000);
  is(/Sent\. Your manager has your review now/.test(
       await page.evaluate(() => document.body.textContent)), true,
     "AC-87/AC-96: a finished review sends, and the screen says so");

  await mark(page);
  await page.reload({ waitUntil: "networkidle0", timeout: 30000 });
  await wait(3000);
  is(await reloaded(page), true, "the document really was reloaded again");
  const after = await page.evaluate(() => ({
    sent: /Sent\. Your manager has your review now/.test(document.body.textContent),
    send: !!document.getElementById("nf-wiz-send"),
  }));
  is(after.sent, true, "AC-95: it still reads as sent after a reload");
  is(after.send, false, "and there is no second Send to press");

  is(pageErrors.length, 0,
     "no uncaught JavaScript errors: " + JSON.stringify(pageErrors));

  await browser.close();
  console.log("\nThe self-review in a real browser: " + pass + " passed, " +
              fail + " failed");
  process.exit(fail ? 1 : 0);
}

main().catch((e) => { console.error("check failed to run:", e); process.exit(1); });
