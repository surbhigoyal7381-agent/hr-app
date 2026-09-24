/* Do the Time and Pay panels actually work in a REAL browser?
 *
 * Slice 043's sibling to `browser_check_frame.js`, and here for the same
 * reason. **jsdom is kinder than a browser.** Wave 1 learned that the hard
 * way: its stub called an error path `website.js` never calls, so a promise
 * that never settled looked like a passing test. `next_time_pay_test.js` covers
 * these panels in jsdom against real payload shapes, which is worth having -
 * but it cannot prove the two new script files parse and run in a browser
 * engine, that the calendar grid lays out, or that the Why? sheet opens with
 * real records behind it rather than a fixture.
 *
 * One thing this script is careful about, because it is the whole point of the
 * Why? sheet: **it asserts the sheet's wording against a REAL Attendance
 * Deduction on a real site.** The false remedy - the sentence revision 1 of the
 * spec would have shipped, telling people a correction undoes a deduction - is
 * checked for by hand here as well as by the static check, because this is the
 * only place the rendered page is a real rendered page.
 *
 * It is NOT part of CI. It needs a running site, a real login and a browser.
 * Run it in your OWN container, never the shared bench.
 *
 *   apt-get install -y chromium                       # as root, once
 *   mkdir -p /tmp/browser && cd /tmp/browser
 *   npm init -y && npm install puppeteer-core
 *   bench --site <site> serve --port 8000 &           # your own site
 *   PROBE_USR=... PROBE_PWD=... node scripts/browser_check_time_pay.js
 *
 * **Give the probe its OWN login, not a test fixture's person.** The preview
 * page needs `portal_preview` in the site config and a System Manager role, and
 * the first run of this script borrowed a fixture employee and granted him one.
 * Two tests in `test_time_api_043` then failed - he could suddenly open a
 * colleague's month, because System Manager may review - and they looked like
 * permission bugs in code that had not changed. A login is shared state on a
 * site. The fixture now sets its roles exactly, which fixes it from the other
 * end, but borrowing a fixture person is still the wrong thing to do.
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

async function main() {
  if (!USR || !PWD) {
    console.error("Set PROBE_USR and PROBE_PWD to a user with an Employee " +
                  "record on the site you are serving.");
    process.exit(2);
  }

  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME || "/usr/bin/chromium",
    args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });
  const page = await browser.newPage();
  /* A phone, because Rahul is on a factory floor with a phone (AC-41). 390px
     is the width the design was measured at. */
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

  /* ── Time ──────────────────────────────────────────────────────────────── */

  const resp = await page.goto(BASE + PAGE + "#time",
                               { waitUntil: "networkidle0", timeout: 30000 });
  is(resp.status(), 200, "the preview page answers 200");
  await wait(2500);

  const time = await page.evaluate(() => {
    const state = document.getElementById("nf-state");
    const screens = document.getElementById("nf-screens");
    const cells = screens.querySelectorAll(".nf-cal-day");
    const named = screens.querySelectorAll(".nf-cal-day .nf-sr");
    return {
      loaded: !!window.NextTime,
      state: state && !state.hidden ? state.getAttribute("data-kind") : null,
      cells: cells.length,
      named: named.length,
      tabs: screens.querySelectorAll(".nf-tab-btn").length,
      skeleton: document.getElementById("nf-skeleton-time")
        ? document.getElementById("nf-skeleton-time").hidden : null,
      text: screens.textContent.slice(0, 4000),
      /* Does the page scroll sideways at 390px? This is the one check jsdom
         cannot do at all: it has no layout. */
      sideways: document.documentElement.scrollWidth
                > document.documentElement.clientWidth,
    };
  });
  is(time.loaded, true, "next-time.js ran in a real browser");
  is(time.state, null, "Time is not showing an error or a spinner");
  is(time.cells > 27, true, "the month grid was drawn: " + time.cells + " cells");
  is(time.named, time.cells,
     "and every cell carries its state in words (colour is never the only signal)");
  is(time.tabs, 3, "the three tabs are there");
  is(time.skeleton, true, "the skeleton was put away once the answer landed");
  is(time.sideways, false, "AC-41: no sideways scroll at 390px");

  /* The day sheet, opened by a real click in a real browser. */
  const sheet = await page.evaluate(async () => {
    const btn = document.querySelector("#nf-screens .nf-cal-btn");
    if (!btn) { return { opened: false, why: "no tappable day" }; }
    btn.click();
    await new Promise((r) => setTimeout(r, 400));
    const wrap = document.getElementById("nf-sheet-wrap");
    return {
      opened: !wrap.hidden,
      /* The title takes focus, or a screen reader stays where the click was
         and reads nothing. */
      focused: document.activeElement
        && document.activeElement.id === "nf-sheet-title",
      text: document.getElementById("nf-sheet-body").textContent.slice(0, 1500),
    };
  });
  is(sheet.opened, true, "tapping a day opens the day sheet in a browser");
  is(sheet.focused, true, "and the sheet's title takes focus");
  is(/grace/i.test(sheet.text), true,
     "AC-5: the grace row is on the sheet, naming where the figure came from");

  /* Escape closes it, and focus goes back. Real keyboard, real browser. */
  await page.keyboard.press("Escape");
  await wait(300);
  const closed = await page.evaluate(() => ({
    hidden: document.getElementById("nf-sheet-wrap").hidden,
    back: document.activeElement
      && document.activeElement.classList.contains("nf-cal-btn"),
  }));
  is(closed.hidden, true, "Escape closes the day sheet");
  is(closed.back, true, "and focus goes back to the day that opened it");

  /* Each tab draws without asking the server again - it is the same answer,
     and a second call would be a second age of the truth. */
  const tabs = await page.evaluate(async () => {
    const out = {};
    for (const name of ["leave", "rule"]) {
      document.querySelector('[data-tab="' + name + '"]').click();
      await new Promise((r) => setTimeout(r, 300));
      out[name] = document.getElementById("nf-time-body").textContent.slice(0, 1200);
    }
    return out;
  });
  is(/Leave|leave/.test(tabs.leave), true, "the Leave tab draws");
  is(tabs.rule.length > 10, true, "the Late rule tab draws");
  is(/\bMonday\b|\bSunday\b/.test(tabs.rule), true,
     "and the rule's week-start day came from the record, not from the copy");

  /* ── Pay, and the Why? sheet ───────────────────────────────────────────── */

  await page.goto(BASE + PAGE + "#pay", { waitUntil: "networkidle0", timeout: 30000 });
  await wait(2500);

  const pay = await page.evaluate(() => {
    const state = document.getElementById("nf-state");
    const screens = document.getElementById("nf-screens");
    return {
      loaded: !!window.NextPay,
      state: state && !state.hidden ? state.getAttribute("data-kind") : null,
      whys: screens.querySelectorAll("[data-why]").length,
      text: screens.textContent.slice(0, 3000),
      sideways: document.documentElement.scrollWidth
                > document.documentElement.clientWidth,
    };
  });
  is(pay.loaded, true, "next-pay.js ran in a real browser");
  is(pay.state, null, "Pay is not showing an error or a spinner");
  is(pay.sideways, false, "AC-41: no sideways scroll on Pay at 390px");

  if (pay.whys < 1) {
    console.log("  SKIP  the Why? sheet: this site has no deduction line with " +
                "an Additional Salary behind it. Seed one and run again.");
  } else {
    const why = await page.evaluate(async () => {
      document.querySelector("#nf-screens [data-why]").click();
      await new Promise((r) => setTimeout(r, 900));
      const wrap = document.getElementById("nf-sheet-wrap");
      return { opened: !wrap.hidden,
               text: document.getElementById("nf-sheet-body").textContent };
    });
    is(why.opened, true, "the Why? sheet opens against a REAL deduction");
    is(/automatically/.test(why.text), true,
       "AC-57: it says the figure was worked out automatically");
    is(/Nobody looked at your week by hand/.test(why.text), true,
       "and that nobody looked at the week by hand");
    is(/does not undo this deduction/.test(why.text), true,
       "AC-58: the remedy it states is the one that exists");
    /* The sentence revision 1 of the spec would have shipped. It is false, and
       this is the only place the RENDERED page is a real rendered page. */
    is(/the rule follows the attendance record/.test(why.text), false,
       "and the false remedy from revision 1 is nowhere on the rendered page");
    is(/contact/i.test(why.text), true, "AC-60: it gives a route to somebody");
  }

  is(pageErrors.length, 0,
     "no uncaught JavaScript errors: " + JSON.stringify(pageErrors));

  await browser.close();
  console.log("\nTime and Pay in a real browser: " + pass + " passed, " +
              fail + " failed");
  process.exit(fail ? 1 : 0);
}

main().catch((e) => { console.error("check failed to run:", e); process.exit(1); });
