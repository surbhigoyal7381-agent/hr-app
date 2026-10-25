/* Does the Positions screen actually work in a real browser?
 *
 * The original chart (the one live on main, kept by Surbhi on 22 Oct 2026)
 * with the trays and dialogs slice 064 added: clicking a seat opens its
 * tray, the tray offers Change, the two people tiles open their trays, and
 * the seat dialog, the person picker and the delete dialog still open.
 *
 * NOT part of CI. It needs a running site, a login and a browser. Run it on
 * a THROWAWAY site, never a real one:
 *
 *   BASE=http://127.0.0.1:8064 PROBE_USR=... PROBE_PWD=... \
 *     PLAYWRIGHT=<path to playwright> node scripts/browser_check_positions.js
 *
 * It prints a line per check, saves PNGs to $SHOTS, and exits non-zero if
 * any check fails. Nothing is saved or deleted: the delete dialog is opened
 * and closed with "Keep it".
 */
const { chromium } = require(process.env.PLAYWRIGHT || "playwright");

const BASE = process.env.BASE || "http://127.0.0.1:8000";
const USR = process.env.PROBE_USR, PWD = process.env.PROBE_PWD;
const SHOTS = process.env.SHOTS || "";

let pass = 0, fail = 0;
const ok = (cond, msg, detail) => cond ? (pass++, console.log("  PASS  " + msg))
  : (fail++, console.log("  FAIL  " + msg + (detail ? "  (" + detail + ")" : "")));

(async () => {
  if (!USR || !PWD) { console.error("Set PROBE_USR and PROBE_PWD for a user on a THROWAWAY site."); process.exit(2); }
  const b = await chromium.launch();
  const page = await (await b.newContext({ viewport: { width: 1280, height: 1000 } })).newPage();
  const shot = async (n) => { if (SHOTS) await page.screenshot({ path: SHOTS + n + ".png", fullPage: true }); };
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(BASE + "/alvoraa-login", { waitUntil: "networkidle" });
  await page.fill("#kx-email", USR); await page.fill("#kx-password", PWD);
  await Promise.all([page.waitForNavigation({ waitUntil: "networkidle" }).catch(() => {}),
                     page.click("#kx-login-form button[type=submit]")]);
  await page.goto(BASE + "/hrms-employee", { waitUntil: "networkidle" });
  ok(await page.evaluate(() => !!document.getElementById("panel-positions")), "the Positions panel is on the page");
  await page.evaluate(() => switchPanel("positions"));
  await page.waitForFunction(() => window.POS && POS.rows && POS.rows.length > 0, null, { timeout: 30000 });
  await page.waitForTimeout(600);

  // ── it opens on the chart, with Arrange by shown (I1) ─────────────────────
  const opening = await page.evaluate(() => ({
    view: document.getElementById("pos-f-view").value,
    arrange: getComputedStyle(document.getElementById("pos-arrange-wrap")).display !== "none",
    boxes: document.querySelectorAll("#pos-body .oc-box").length,
    zoom: (document.querySelector(".pos-zpct") || {}).textContent,
  }));
  ok(opening.view === "tree" && opening.boxes > 1, "the page opens on the chart");
  ok(opening.arrange, "Arrange by is shown");
  ok(opening.zoom === "100%", "at 100 %", opening.zoom);
  await shot("00-opening");

  // ── the list ──────────────────────────────────────────────────────────────
  await page.selectOption("#pos-f-view", "list");
  await page.waitForTimeout(500);
  ok(await page.evaluate(() => getComputedStyle(document.getElementById("pos-arrange-wrap")).display !== "none"),
     "Arrange by stays shown on the list");
  const list = await page.evaluate(() => ({
    rows: document.querySelectorAll("#pos-body table tbody tr").length,
    body: document.getElementById("pos-body").innerHTML,
  }));
  ok(list.rows > 0, "the list draws rows", "got " + list.rows);
  ok(!/Loading|undefined|NaN/.test(list.body), "it has loaded and nothing reads undefined");
  await shot("01-list");

  // ── the structure view, the original chart ────────────────────────────────
  await page.selectOption("#pos-f-view", "tree");
  await page.evaluate(() => { POS.collapsed = {}; POS.expanded = {}; POS.ungrouped = {}; posPaint(); });
  await page.waitForTimeout(600);
  const tree = await page.evaluate(() => {
    const box = document.querySelector("#pos-body .oc-box");
    return {
      boxes: document.querySelectorAll("#pos-body .oc-box").length,
      kids: document.querySelectorAll("#pos-body .oc-kids").length,
      isTable: !!document.querySelector("#pos-body table"),
      boxWidth: box ? Math.round(box.getBoundingClientRect().width) : 0,
      newChart: !!document.querySelector(".pos-chartwrap, .pos-box, .pos-sibs, .pos-strip"),
    };
  });
  ok(tree.boxes > 1, "the structure view draws the original boxes", "got " + tree.boxes);
  ok(tree.kids > 0, "with connectors between them", "got " + tree.kids);
  ok(!tree.isTable, "and it is not a table");
  ok(tree.boxWidth > 120, "a box has real width on screen", tree.boxWidth + "px");
  ok(!tree.newChart, "none of the discarded chart is drawn");
  await shot("02-structure");
  for (const how of ["branch", "department"]) {
    await page.selectOption("#pos-f-arrange", how);
    await page.waitForTimeout(500);
    const got = await page.evaluate(() => ({ boxes: document.querySelectorAll("#pos-body .oc-box").length,
                                             body: document.getElementById("pos-body").innerHTML }));
    // One box is right for a reader with one branch, or departments under one top.
    ok(got.boxes >= 1 && !/undefined|NaN/.test(got.body), "arranged by " + how + ", the chart draws");
  }
  await page.selectOption("#pos-f-arrange", "reporting");
  await page.waitForTimeout(500);

  // ── one press opens a closed box (the live bug: it took two) ──────────────
  await page.selectOption("#pos-f-arrange", "branch");
  await page.waitForTimeout(400);
  const before = await page.evaluate(() => document.querySelectorAll("#pos-body .oc-box").length);
  await page.click("#pos-body .oc-toggle[aria-expanded=false]");
  await page.waitForTimeout(300);
  const after = await page.evaluate(() => document.querySelectorAll("#pos-body .oc-box").length);
  ok(after > before, "one press opens a closed branch", before + " -> " + after);
  await page.selectOption("#pos-f-arrange", "reporting");
  await page.waitForTimeout(400);

  // ── a filter picks its view and focuses the first match ───────────────────
  const branch = await page.evaluate(() => (document.getElementById("pos-f-branch").options[1] || {}).value || "");
  if (branch) {
    await page.selectOption("#pos-f-branch", branch);
    await page.waitForTimeout(500);
    const f = await page.evaluate(() => ({
      arrange: document.getElementById("pos-f-arrange").value,
      line: (document.getElementById("pos-fline-txt") || {}).textContent || "",
      focused: !!(document.activeElement && document.activeElement.classList.contains("pos-first")),
    }));
    ok(f.arrange === "branch", "a Branch filter switches to By branch");
    ok(/matching, showing the first/.test(f.line), "and says how many match", f.line);
    ok(f.focused, "the first match has the keyboard focus");
    await shot("02b-filter");
    await page.click('#pos-body button:has-text("Clear filter")');
    await page.waitForTimeout(400);
    ok(await page.evaluate(() => document.getElementById("pos-f-arrange").value === "reporting"
                                 && !document.getElementById("pos-f-branch").value),
       "Clear filter puts back the arrangement");
  }

  // ── zoom by keys, and Find ────────────────────────────────────────────────
  await page.evaluate(() => document.activeElement && document.activeElement.blur && document.activeElement.blur());
  await page.keyboard.press("+");
  ok(await page.evaluate(() => document.querySelector(".pos-zpct").textContent) === "110%", "the + key zooms in");
  await page.keyboard.press("0");
  ok(await page.evaluate(() => document.querySelector(".pos-zpct").textContent) === "100%", "0 resets");
  const who = await page.evaluate(() => { const r = POS.rows.filter((x) => x.people.length).slice(-1)[0]; return { name: r.people[0].name, id: r.id }; });
  await page.fill("#pos-find", who.name.slice(0, 5));
  await page.waitForTimeout(200);
  ok(await page.evaluate(() => document.querySelectorAll("#pos-find-res .pos-hit").length > 0), "Find lists people and seats");
  await page.evaluate((id) => posFindPick(id), who.id);
  await page.waitForTimeout(400);
  const found = await page.evaluate((id) => {
    const b = document.querySelector("#pos-body .oc-box.pos-first");
    return !!b && document.activeElement === b;
  }, who.id);
  ok(found, "choosing a result opens the path and outlines the box, with focus");
  await shot("02c-find");

  // ── clicking a seat opens its tray ────────────────────────────────────────
  const target = await page.evaluate(() => {
    const seat = POS.rows.filter((r) => r.people.length)[0];
    const btn = [...document.querySelectorAll("#pos-body [onclick]")]
      .find((e) => (e.getAttribute("onclick") || "").indexOf("posSeatSheet('" + seat.id + "')") === 0);
    if (btn) btn.setAttribute("data-probe", "1");
    return { id: seat.id, found: !!btn };
  });
  ok(target.found, "a seat box on the chart opens the seat tray");
  if (target.found) await page.click("[data-probe='1']"); else await page.evaluate((id) => posSeatSheet(id), target.id);
  await page.waitForTimeout(300);
  const tray = await page.evaluate(() => {
    const s = document.querySelector(".pos-sheet"), r = s ? s.getBoundingClientRect() : null;
    return { open: !!s, right: r ? Math.round(r.right) : 0, top: r ? Math.round(r.top) : -1,
             vw: document.documentElement.clientWidth, text: s ? s.textContent : "",
             focus: document.activeElement && document.activeElement.id };
  });
  ok(tray.open, "the tray opens");
  ok(Math.abs(tray.right - tray.vw) <= 1 && tray.top === 0, "against the window's right edge, from the top",
     "right " + tray.right + " of " + tray.vw + ", top " + tray.top);
  ok(/Who is in it/.test(tray.text), "it says who is in the seat");
  ok(tray.focus === "pos-sh-t", "focus moves to its heading");
  await shot("03-seat-tray");
  const mayEdit = await page.evaluate(() => POS.may_edit);
  if (mayEdit) {
    await page.click(".pos-sheet button:has-text('Change this seat')");
    await page.waitForTimeout(500);
    const dlg = await page.evaluate(() => {
      const el = document.getElementById("pos-editor");
      const r = el.querySelector(".gp-modal").getBoundingClientRect();
      return { open: el.classList.contains("open"), visible: r.width > 100 && r.height > 100,
               tray: !!document.querySelector(".pos-sheet"),
               people: (document.getElementById("pos-people") || {}).innerHTML || "" };
    });
    ok(dlg.open && dlg.visible, "Change this seat opens the seat dialog");
    ok(!dlg.tray, "and the tray closes behind it");
    ok(!/Nobody is in this seat/.test(dlg.people), "a filled seat lists its people");
    await shot("04-seat-dialog");
    await page.evaluate(() => posPickPerson());
    await page.waitForTimeout(1500);
    const pick = await page.evaluate(() => ({ open: document.getElementById("pos-person").classList.contains("open"),
                                              list: document.getElementById("pos-p-list").textContent }));
    ok(pick.open && !/Looking/.test(pick.list), "the person picker opens and finishes looking");
    await page.evaluate(() => posPickClose());
    if (await page.evaluate(() => POS.may_delete)) {
      await page.click("#pos-delete-btn");
      const del = await page.evaluate(() => ({ open: document.getElementById("pos-delete").classList.contains("open"),
                                               focus: document.activeElement && document.activeElement.id }));
      ok(del.open && del.focus === "pos-delete-keep", "Delete seat asks first, with focus on Keep it");
      await page.keyboard.press("Escape");
      ok(!(await page.evaluate(() => document.getElementById("pos-delete").classList.contains("open"))), "Escape keeps the seat");
    }
    await page.evaluate(() => posCloseEditor());
  } else {
    ok(!/Change this seat/.test(tray.text), "a reader's tray has no Change");
    await page.keyboard.press("Escape");
  }
  ok(!(await page.evaluate(() => !!document.querySelector(".pos-sheet"))), "no tray is left open");

  // ── the people tiles, for HR only ─────────────────────────────────────────
  const hr = await page.evaluate(() => POS.unseated !== null);
  const tiles = await page.evaluate(() => document.getElementById("pos-tiles").innerHTML);
  ok(hr === /IN NO SEAT/.test(tiles), hr ? "HR see the In no seat tile" : "a reader without HR scope sees no people tiles");
  if (hr) {
    for (const [fn, title] of [["posUnseatedSheet()", "In no seat"], ["posNoMgrSheet()", "No reporting manager"]]) {
      const has = await page.evaluate((f) => !!document.querySelector("#pos-tiles [onclick='" + f + "']"), fn);
      if (!has) { ok(true, title + " tile has nothing to open (zero)"); continue; }
      await page.click("#pos-tiles [onclick='" + fn + "']");
      await page.waitForTimeout(300);
      const t = await page.evaluate(() => (document.querySelector(".pos-sheet h2") || {}).textContent || "");
      ok(t.indexOf(title) === 0, "the " + title + " tile opens its tray", t);
      await shot("05-" + title.replace(/ /g, "-"));
      await page.keyboard.press("Escape");
    }
  }

  ok(errors.length === 0, "no JavaScript errors on the page", errors.slice(0, 2).join(" | "));
  await b.close();
  console.log("\n  " + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
