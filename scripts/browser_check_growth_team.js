/* Do the Growth and Team panels actually work in a REAL browser?
 *
 * Slice 045's sibling to `browser_check_frame.js` and
 * `browser_check_time_pay.js`, and here for the same reason.
 *
 * **jsdom is kinder than a browser.** Wave 1 learned it the hard way: its stub
 * called an error path `website.js` never calls, so a promise that never
 * settled looked like a passing test, and a whole error-handling gap hid for a
 * week. Wave 4 met the same shape in miniature - jsdom has no `TextEncoder` on
 * its window, so the byte counter silently took its fallback and a test
 * asserting "an English character costs one byte" got nine. The fork is gone
 * now, but the lesson is why this file exists.
 *
 * `next_growth_team_test.js` covers these panels in jsdom against real payload
 * shapes, which is worth having. What it cannot do at all:
 *
 *   * prove the two new script files parse and run in a browser engine;
 *   * measure anything, because jsdom has no layout - so the 44px rating
 *     buttons and the "no sideways scroll at 390px" rule are only ever really
 *     checked here (`01b` finding N4 measured those buttons at 32px on a
 *     phone, on the one screen that has to finish in two minutes);
 *   * prove the frame's sheet really traps focus and really gives it back on
 *     Escape, with a real keyboard.
 *
 * **And one thing only a real site can prove: that the two Team sections draw
 * the right counts against real records, and that an action the SERVER refuses
 * is not offered.** The second one is checked by calling the endpoint by hand
 * from the page and comparing what came back with what is on screen - a screen
 * that hides a button is not an access rule, and a screen that offers one the
 * server refuses is worse.
 *
 * It is NOT part of CI. It needs a running site, a real login and a browser.
 * Run it in your OWN container, never the shared bench.
 *
 *   apt-get install -y chromium                       # as root, once
 *   mkdir -p /tmp/browser && cd /tmp/browser
 *   npm init -y && npm install puppeteer-core
 *   bench --site <site> serve --port 8000 &           # your own site
 *   PROBE_USR=... PROBE_PWD=... node scripts/browser_check_growth_team.js
 *
 * **Give the probe its OWN login, not a test fixture's person.** The preview
 * page needs `portal_preview` in the site config and a System Manager role,
 * and slice 043's first run borrowed a fixture employee and granted him one -
 * two Python tests then failed because he could suddenly open a colleague's
 * month, and they looked like permission bugs in code that had not changed. A
 * login is shared state on a site.
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
  /* A phone, because Rahul is on a factory floor with a phone. 390px is the
     width the design was measured at. */
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

  /* ── Team: two sections, real counts ───────────────────────────────────── */

  const resp = await page.goto(BASE + PAGE + "#team",
                               { waitUntil: "networkidle0", timeout: 30000 });
  is(resp.status(), 200, "the preview page answers 200");
  await wait(2500);

  /* **The frame itself, first, and the run stops if it did not load.**
     Added after the first real run of this file: every ess asset 404'd on the
     site being served - the sites volume carried a stale copy of the app's
     public folder with no `ess` folder in it at all - so NOTHING ran, and
     three assertions below passed anyway against the server-rendered markup.
     "Team is not showing an error" was true because the state box starts
     hidden, and "the skeleton was put away" was true because it starts hidden
     too. A check that passes when the page is dead is worse than no check. */
  const frameUp = await page.evaluate(() => ({
    frame: !!window.NextFrame,
    team: !!window.NextTeam,
    growth: !!window.NextGrowth,
  }));
  is(frameUp.frame, true, "next-frame.js ran at all - if this fails, the " +
     "assets are not being served and nothing below means anything");
  if (!frameUp.frame) {
    console.error("The page loaded but no script ran. Check that " +
                  "/assets/alvoraa_portal/js/ess/next-frame.js answers 200 on " +
                  "the site you are serving.");
    await browser.close();
    process.exit(1);
  }

  const team = await page.evaluate(async () => {
    const screens = document.getElementById("nf-screens");
    const state = document.getElementById("nf-state");
    /* The SERVER's own answer, asked again from the page, so the screen can be
       compared with it rather than with a fixture.

       The CSRF header is the same one the frame sends. Without it Frappe
       answers 400 and this check would silently compare the screen against an
       empty object - which would pass, and prove nothing. `"None"` is what
       Frappe prints into the page when there is no token, and it is truthy, so
       it is filtered out the way `next-frame.js` filters it. */
    const raw = (window.frappe && window.frappe.csrf_token) || "";
    const token = (raw === "None" || raw === "null" || raw === "undefined") ? "" : raw;
    const headers = { "Content-Type": "application/json" };
    if (token) { headers["X-Frappe-CSRF-Token"] = token; }
    const r = await fetch("/api/method/alvoraa_portal.team_api.get_team", {
      method: "POST", headers: headers, credentials: "same-origin", body: "{}",
    });
    const payload = r.ok ? ((await r.json()).message || {}) : { __failed: r.status };
    const titles = Array.from(screens.querySelectorAll(".nf-card-title"))
      .map((n) => n.textContent);
    return {
      loaded: !!window.NextTeam,
      state: state && !state.hidden ? state.getAttribute("data-kind") : null,
      titles: titles,
      rows: screens.querySelectorAll(".nf-person").length,
      skeleton: document.getElementById("nf-skeleton-team")
        ? document.getElementById("nf-skeleton-team").hidden : null,
      text: screens.textContent.slice(0, 4000),
      payload: payload,
      /* The one check jsdom cannot do at all: it has no layout. */
      sideways: document.documentElement.scrollWidth
                > document.documentElement.clientWidth,
      /* Every rating-sized control on this screen, measured. */
      smallTargets: Array.from(screens.querySelectorAll("button"))
        .map((b) => b.getBoundingClientRect())
        .filter((r2) => r2.height > 0 && (r2.height < 44 || r2.width < 44)).length,
      tinyText: Array.from(screens.querySelectorAll("*"))
        .filter((n) => n.children.length === 0 && n.textContent.trim())
        .map((n) => parseFloat(getComputedStyle(n).fontSize))
        .filter((s) => s < 12).length,
    };
  });

  is(team.payload.__failed, undefined,
     "the by-hand get_team call was answered, so the comparisons below mean " +
     "something (status " + team.payload.__failed + ")");
  is(team.loaded, true, "next-team.js ran in a real browser");
  is(team.state, null, "Team is not showing an error or a spinner");
  is(team.skeleton, true, "the skeleton was put away once the answer landed");
  is(team.sideways, false, "no sideways scroll on Team at 390px");
  is(team.tinyText, 0, "nothing on Team is under 12px");

  /* **The counts equal the lists, against real records.** */
  const direct = team.payload.direct || { rows: [], total: 0 };
  const covered = team.payload.covered;
  const wantDirect = team.payload.has_direct
    ? (direct.capped
        ? `Your team — showing the first ${direct.rows.length} of ${direct.total}`
        : `Your team (${direct.rows.length})`)
    : null;
  if (wantDirect) {
    is(team.titles.includes(wantDirect), true,
       `the Your team heading matches the server's own list: "${wantDirect}"`);
  } else {
    is(team.text.indexOf("Your team"), -1,
       "with no direct reports the Your team heading is absent from the page");
  }
  if (team.payload.has_covered) {
    const wantCovered = covered.capped
      ? `You cover — showing the first ${covered.rows.length} of ${covered.total}`
      : `You cover (${covered.rows.length})`;
    is(team.titles.includes(wantCovered), true,
       `the You cover heading matches the server's own list: "${wantCovered}"`);
  } else {
    is(team.text.indexOf("You cover"), -1,
       "with no HR scope the You cover heading is absent from the page");
  }
  const drawn = (direct.rows.length || 0) +
                (team.payload.has_covered ? covered.rows.length : 0);
  is(team.rows, drawn, `every drawn row is on screen (${drawn})`);
  /* No combined total anywhere. Checked by arithmetic, not by key name. */
  const combined = (direct.total || 0) +
                   (team.payload.has_covered ? covered.total : 0);
  if (team.payload.has_direct && team.payload.has_covered) {
    is(new RegExp("\\b" + combined + "\\b").test(team.titles.join(" ")), false,
       `no heading carries the combined total (${combined})`);
  }

  /* **An action the server refuses is not offered.** */
  if (drawn) {
    const sheet = await page.evaluate(async () => {
      const btn = document.querySelector("#nf-screens [data-person]");
      btn.click();
      await new Promise((r) => setTimeout(r, 400));
      const wrap = document.getElementById("nf-sheet-wrap");
      const who = btn.getAttribute("data-person");
      return {
        opened: !wrap.hidden,
        /* The title takes focus, or a screen reader stays where the click was
           and reads nothing. */
        focused: document.activeElement
          && document.activeElement.id === "nf-sheet-title",
        who: who,
        text: document.getElementById("nf-sheet-body").textContent,
        offered: Array.from(
          document.querySelectorAll("#nf-sheet-body [data-act]"))
          .map((n) => n.getAttribute("data-act")),
      };
    });
    is(sheet.opened, true, "tapping a person opens the sheet in a browser");
    is(sheet.focused, true, "and the sheet's title takes focus");

    /* Ask the server, by hand, whether each offered action is really allowed
       for that person. Anything offered and refused is the failure this whole
       file is for. */
    const rowFor = (direct.rows || []).concat(
      team.payload.has_covered ? covered.rows : [])
      .find((r) => r.name === sheet.who) || { actions: [] };
    const extra = sheet.offered.filter((a) => rowFor.actions.indexOf(a) === -1);
    is(extra.length, 0,
       "the sheet offers nothing the server did not allow for that person" +
       (extra.length ? " (offered anyway: " + extra.join(", ") + ")" : ""));
    /* And nothing the server allowed is silently dropped: whatever is not
       offered as a control has to be on the sheet as text. */
    const missing = rowFor.actions.filter(
      (a) => sheet.offered.indexOf(a) === -1 && sheet.text.length === 0);
    is(missing.length, 0, "and nothing it allowed vanished without a word");
    /* An HR override never reads plain "Approve". */
    if (rowFor.actions.indexOf("act_as_hr") !== -1) {
      is(/Approve as HR/.test(sheet.text), true,
         "AC-82: the HR act is named as one");
    }

    /* Escape closes it, and focus goes back. Real keyboard, real browser. */
    await page.keyboard.press("Escape");
    await wait(300);
    const closed = await page.evaluate(() => ({
      hidden: document.getElementById("nf-sheet-wrap").hidden,
      back: document.activeElement
        && document.activeElement.hasAttribute("data-person"),
    }));
    is(closed.hidden, true, "Escape closes the person sheet");
    is(closed.back, true, "and focus goes back to the row that opened it");
  } else {
    console.log("  SKIP  the person sheet: this login has nobody on Team. " +
                "Run as a manager or an HR user.");
  }

  /* ── Growth ────────────────────────────────────────────────────────────── */

  await page.goto(BASE + PAGE + "#growth",
                  { waitUntil: "networkidle0", timeout: 30000 });
  await wait(2500);

  const growth = await page.evaluate(() => {
    const screens = document.getElementById("nf-screens");
    const state = document.getElementById("nf-state");
    return {
      loaded: !!window.NextGrowth,
      state: state && !state.hidden ? state.getAttribute("data-kind") : null,
      text: screens.textContent.slice(0, 4000),
      sideways: document.documentElement.scrollWidth
                > document.documentElement.clientWidth,
      opens: !!document.getElementById("nf-growth-open"),
    };
  });
  is(growth.loaded, true, "next-growth.js ran in a real browser");
  is(growth.state, null, "Growth is not showing an error or a spinner");
  is(growth.sideways, false, "no sideways scroll on Growth at 390px");
  /* Colour is never the only signal: a trajectory is words. */
  is(/On Track|At Risk|Off Track|Not set yet|no review running|No goals/
     .test(growth.text), true,
     "the screen says something in words - a state, or why there is nothing");

  /* ── the wizard: it saves, and it resumes ──────────────────────────────── */

  if (!growth.opens) {
    console.log("  SKIP  the wizard: this login has no open review. Seed one " +
                "and run again.");
  } else {
    await page.goto(BASE + PAGE + "#growth/review",
                    { waitUntil: "networkidle0", timeout: 30000 });
    await wait(2500);

    const wizard = await page.evaluate(() => {
      const screens = document.getElementById("nf-screens");
      const rates = screens.querySelectorAll("[data-rate]");
      const boxes = Array.from(rates).map((b) => b.getBoundingClientRect());
      return {
        loaded: !!window.NextGrowth,
        rates: rates.length,
        /* **The measurement jsdom cannot make.** `01b` finding N4 found these
           at 32px on a phone. */
        small: boxes.filter((r) => r.height < 44 || r.width < 44).length,
        sliders: screens.querySelectorAll('input[type="range"]').length,
        room: (document.getElementById("nf-wiz-room") || {}).textContent || "",
        step: (document.getElementById("nf-wiz-progress") || {}).textContent || "",
        sideways: document.documentElement.scrollWidth
                  > document.documentElement.clientWidth,
      };
    });
    is(wizard.loaded, true, "the wizard ran in a real browser");
    is(wizard.rates >= 5, true, `the whole-point buttons are there (${wizard.rates})`);
    is(wizard.small, 0,
       "and every one of them is at least 44px, measured in a browser (01b N4)");
    is(wizard.sliders, 0, "there is no slider - a slider can be un-snapped");
    is(/characters left/.test(wizard.room), true,
       "the room left is on screen before anything is typed");
    is(wizard.sideways, false, "no sideways scroll in the wizard at 390px");

    /* Type something, let the autosave go, then RELOAD and look for it. This
       is the check that matters most: a wizard that saves and does not resume
       is a wizard that lost somebody's afternoon. */
    const mark = "probe " + Date.now();
    await page.evaluate(async (m) => {
      const box = document.querySelector("#nf-screens textarea");
      if (!box) { return; }
      box.value = m;
      box.dispatchEvent(new Event("input", { bubbles: true }));
      /* Past the idle timer, so the autosave really fires. */
      await new Promise((r) => setTimeout(r, 6000));
    }, mark);
    await wait(1500);
    const saved = await page.evaluate(() =>
      (document.getElementById("nf-wiz-room") || {}).textContent || "");
    is(/Saved at/.test(saved), true,
       "the autosave landed and the screen says when - the SERVER's time");

    /* **This was a `goto` to the URL the browser was already on, fragment and
       all - which Chrome treats as a same-document navigation.** Nothing
       reloaded, so the assertion read the value still sitting in the DOM and
       passed while the draft really was being lost. A marker on `window`
       proves the document was thrown away before anything is read from it.
       The wizard's own checks live in `browser_check_self_review.js`. */
    await page.evaluate(() => { window.__alvoraaSameDocument = 1; });
    await page.reload({ waitUntil: "networkidle0", timeout: 30000 });
    await wait(3000);
    is(await page.evaluate(() => !window.__alvoraaSameDocument), true,
       "the document really was reloaded - without this the next check reads " +
       "the value that never left the browser");
    const resumed = await page.evaluate((m) => {
      const boxes = Array.from(
        document.querySelectorAll("#nf-screens textarea")).map((b) => b.value);
      return boxes.some((v) => v.indexOf(m) !== -1);
    }, mark);
    is(resumed, true, "and it is still there after a reload - the wizard resumes");
  }

  is(pageErrors.length, 0,
     "no uncaught JavaScript errors: " + JSON.stringify(pageErrors));

  await browser.close();
  console.log("\nGrowth and Team in a real browser: " + pass + " passed, " +
              fail + " failed");
  process.exit(fail ? 1 : 0);
}

main().catch((e) => { console.error("check failed to run:", e); process.exit(1); });
