/* Slice 069: the wall chart (Positions -> Download wall chart (PDF)).
 *
 * Runs the real portal page in jsdom with the slice's fixtures loaded into
 * POS, the way position_table would have filled it. jsdom does no layout, so
 * sizes are checked in scripts/check_wall_chart_browser.js (Playwright, not
 * CI); this file checks everything that does not need a ruler:
 *
 *   PRIV-1  the paper holds only allowed fields - the sentinel payload, run
 *           with the HR copy off (AC-27a) and on (AC-27b), and the key set of
 *           the copy (AC-28). The HR copy never shows without leaving dates
 *           (AC-65).
 *   counts  every seat and every name, grouping as on screen (AC-21, AC-24,
 *           AC-56, AC-26)
 *
 * In CI through alvoraa_portal/tests/portal_wall_chart_test.js. On its own:
 *
 *     node scripts/check_wall_chart.js
 */
const { JSDOM, VirtualConsole } = require("jsdom");
const { readPortalSource } = require("./lib/portal_source");
const F = require("./lib/wall_chart_fixture");

const problems = [];
let checks = 0;
function ok(what, cond, detail) {
  checks++;
  if (!cond) problems.push(what + (detail ? " - " + String(detail).slice(0, 300) : ""));
}

/* The page's one inline script still holds Jinja tags ({{ support_email }}),
   which only the server fills in. Its syntax error is expected; any other
   script error is printed. */
const vc = new VirtualConsole();
vc.on("jsdomError", (e) => { if (!/Unexpected token '\{'/.test(String(e && e.message))) console.error(e); });
const dom = new JSDOM(readPortalSource(), {
  virtualConsole: vc, runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://grace.localhost/hrms-employee",
  beforeParse(w) {
    w.fetch = () => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ message: {} }),
                                      text: () => Promise.resolve("") });
    w.frappe = { call: () => Promise.resolve({ message: {} }), csrf_token: "x", boot: {}, ui: {}, _messages: {},
                 utils: { escape_html: (s) => s } };
  },
});
const { window } = dom, doc = window.document;
window.Element.prototype.scrollIntoView = function () {};   // jsdom has none; the filters call it
const settle = (ms) => new Promise((r) => setTimeout(r, ms));

/* Load a payload into POS as posLoad would have. */
function load(p) {
  const P = window.POS;
  P.rows = p.rows; P.today = p.as_at || ""; P.may_see_leaving = !!p.may_see_leaving;
  P.may_edit = !!p.may_edit; P.unseated = Object.prototype.hasOwnProperty.call(p, "unseated") ? (p.unseated || []) : null;
  P.active_people = p.active_people || 0; P.ungrouped = {}; P.collapsed = {}; P.expanded = {};
}
/* The paper for a copy, as a detached element to count things in. */
function paper(copy) {
  const boxes = [];
  const html = window.posWallHtml(copy, 99, 99, boxes);
  const el = doc.createElement("div");
  el.innerHTML = html;
  return { html, el, boxes, text: el.textContent };
}
const names = (p) => p.el.querySelectorAll(".nm > div").length;

const SENTINELS = ["EMP-SNTL", "ASG-SNTL", "GRADE-SNTL", "HIRED-SNTL", "TYPE-SNTL", "OPEN-SNTL", "IMG-SNTL",
                   "PLAN-SNTL", "WHO-SNTL", "REASON-SNTL", "UNSEATED-SNTL", "PRINTER-SNTL"];
const BANNED = [".oc-flag", ".oc-tag", ".oc-toggle", ".av", ".pos-nomgr", ".private", "[data-private]"];

function neverPrinted(label, p) {
  SENTINELS.forEach((s) => ok(label + ": no " + s, !p.html.includes(s)));
  ["2099", "Frozen", "covering", "<img", "key seat", "to fill", "Nobody in this seat"].forEach((s) =>
    ok(label + ": no " + s, !p.html.includes(s)));
  BANNED.forEach((sel) => ok(label + ": no " + sel, !p.el.querySelector(sel)));
}

(async () => {
  await settle(300);
  if (typeof window.posWallCopy !== "function") { console.error("posWallCopy is not on the page"); process.exit(1); }
  const sb = doc.getElementById("sb-name");
  if (sb) sb.textContent = "PRINTER-SNTL";

  /* ── PRIV-1, HR copy off (AC-27a) ───────────────────────────────────── */
  load(F.dtc90({ sentinel: true }));
  const off = paper(window.posWallCopy("top", 99, true, false));
  neverPrinted("AC-27a", off);
  ["leaving", "1 Jan", "30 Nov", "Job opening", "HR use only"].forEach((s) =>
    ok("AC-27a: no " + s, !off.text.includes(s)));
  ok("AC-27a: 363 names printed", names(off) === 363, names(off));
  ok("AC-27a: designation and department do print", off.text.includes("DESIG-OK") && off.text.includes("DEPT-OK"));

  /* ── PRIV-1, HR copy on (AC-27b) ────────────────────────────────────── */
  const on = paper(window.posWallCopy("top", 99, true, true));
  neverPrinted("AC-27b", on);
  const nameLine = (who) => [...on.el.querySelectorAll(".nm > div")].map((d) => d.textContent).find((t) => t.indexOf(who) === 0) || "";
  const cfo = F.dtc90({ sentinel: true }).rows.find((r) => r.title === "Chief Financial Officer").people[0].name;
  const guard = F.dtc90({ sentinel: true }).rows.find((r) => r.title === "Security Guard").people[0].name;
  ok("AC-27b: leaving 30 Nov after that person's name", nameLine(cfo) === cfo + " · leaving 30 Nov", nameLine(cfo));
  ok("AC-27b: leaving 1 Jan after the other", nameLine(guard) === guard + " · leaving 1 Jan", nameLine(guard));
  ok("AC-27b: Job opening raised on the seat with the opening", on.text.includes("Job opening raised"));
  ok("AC-27b: 363 names printed", names(on) === 363, names(on));

  /* ── AC-28: the copy holds exactly the allowed keys ─────────────────── */
  function keysOk(copy, hr) {
    // Slice 070 (PRIV-2): plus copy, same and more - a copy's border and its two lines.
    const want = ["below", "branch", "copy", "department", "designation", "kids", "more", "names", "same", "title", "vacant"]
      .concat(hr ? ["opening"] : []).sort().join(",");
    let bad = null;
    (function walk(list) {
      list.forEach((c) => {
        if (Object.keys(c).sort().join(",") !== want) bad = bad || Object.keys(c).join(",");
        if (hr && typeof c.opening !== "number") bad = bad || "opening is " + typeof c.opening;
        c.names.forEach((n) => {
          const k = Object.keys(n).sort().join(",");
          if (!(k === "name" || (hr && k === "leaving,name"))) bad = bad || "a name holds " + k;
        });
        if (c.below && Object.keys(c.below).sort().join(",") !== "people,seats") bad = bad || "below holds " + Object.keys(c.below);
        walk(c.kids);
      });
    })(copy);
    return bad;
  }
  let bad = keysOk(window.posWallCopy("top", 99, true, false), false);
  ok("AC-28: HR copy off - every seat has exactly the allowed keys", !bad, bad);
  bad = keysOk(window.posWallCopy("top", 99, true, true), true);
  ok("AC-28: HR copy on - allowed keys, opening a count", !bad, bad);
  bad = keysOk(window.posWallCopy("top", 2, false, true), true);
  ok("AC-28: 2 levels, Vacant off - same keys", !bad, bad);

  /* ── AC-65: no leaving dates for a reader who is not sent them ─────── */
  load(F.noLeave(true));
  const nl = paper(window.posWallCopy("top", 99, true, true));
  ok("AC-65: a forced leaving value still never prints", !nl.text.includes("leaving") && !nl.text.includes("1 Jan"));
  load(F.noLeave(false));
  const nlOn = window.posWallHtml(window.posWallCopy("top", 99, true, true), 99, 99);
  const nlOff = window.posWallHtml(window.posWallCopy("top", 99, true, false), 99, 99);
  ok("AC-65: with HR copy asked for, the paper is the wall copy", nlOn === nlOff);

  /* ── counts (AC-21, AC-24, AC-20) ───────────────────────────────────── */
  load(F.dtc90());
  const all = paper(window.posWallCopy("top", 99, true, false));
  ok("AC-21: 90 boxes at All", all.el.querySelectorAll(".oc-box").length === 90, all.el.querySelectorAll(".oc-box").length);
  ok("AC-21: 363 name lines", names(all) === 363, names(all));
  ok("AC-20: with All, no box says what is below it", !all.el.querySelector(".below"));
  ok("every box is measured, in the order drawn", all.boxes.length === 90
     && all.boxes.every((c, i) => all.el.querySelectorAll(".oc-box .ti")[i].textContent === c.title));
  const two = paper(window.posWallCopy("top", 2, true, false));
  ok("AC-21: 23 boxes at 2 levels", two.el.querySelectorAll(".oc-box").length === 23, two.el.querySelectorAll(".oc-box").length);
  const belowTxt = [...two.el.querySelectorAll(".below")].map((d) => d.textContent);
  ok("AC-20: the last level says what is below it", belowTxt.length === 5 && belowTxt.includes("14 seats · 52 people below") && belowTxt.includes("10 seats · 71 people below"), belowTxt.join(" | "));
  const root = two.el.querySelector(".oc-node.root > .oc-box");
  ok("AC-24: the starting box has no branch line", root && !root.querySelector(".sub"));
  ok("AC-18: other boxes carry branch · department", two.html.includes("Head Office · Administration"));
  ok("AC-18: designation only when it differs", all.html.includes(">RSO<") && !all.html.includes('<div class="sub">Packing</div>'));
  const bo = window.POS.rows.find((r) => r.title === "Back Office Manager");
  const bom = paper(window.posWallCopy(bo.id, 99, true, false));
  ok("AC-24: Back Office Manager, All: 11 boxes", bom.el.querySelectorAll(".oc-box").length === 11, bom.el.querySelectorAll(".oc-box").length);
  ok("AC-24: and 72 names", names(bom) === 72, names(bom));
  ok("AC-24: nothing above or beside it", !bom.text.includes("Owner and Managing Director") && !bom.text.includes("Admin Head"));
  const backOffice = [...all.el.querySelectorAll(".oc-box")].find((b) => b.querySelector(".ti").textContent === "Back Office");
  ok("AC-18: 36 names in 4 columns, 620 px wide", backOffice && /columns:\s*4/.test(backOffice.innerHTML)
     && /width:\s*620px/.test(backOffice.getAttribute("style")), backOffice && backOffice.outerHTML.slice(0, 120));
  ok("AC-19: an empty seat says Vacant, in its own line", all.el.querySelectorAll(".vac").length === 5);

  /* ── Show Vacant off (AC-56) ────────────────────────────────────────── */
  const novac = paper(window.posWallCopy("top", 99, false, false));
  ok("AC-56: Vacant off - the word appears nowhere", !novac.text.includes("Vacant"));
  ok("AC-56: and every box still prints", novac.el.querySelectorAll(".oc-box").length === 90);

  /* ── identical seats merge (D-6, AC-21) ─────────────────────────────── */
  load(F.group());
  const g = paper(window.posWallCopy("top", 99, true, false));
  const gb = [...g.el.querySelectorAll(".oc-box")].filter((b) => b.querySelector(".ti").textContent === "Cashier");
  ok("D-6: six Cashiers in two branches print as two boxes", gb.length === 2, gb.length);
  // Slice 070 (P-27): a partly filled box says how many are open, never Vacant.
  ok("D-6: the Noida box has all 3 names and no Vacant", gb[0] && gb[0].querySelectorAll(".nm > div").length === 3 && !/Vacant/.test(gb[0].textContent)
     && /1 open/.test(gb[0].textContent));
  ok("D-6: the empty Delhi box says Vacant", gb[1] && !!gb[1].querySelector(".vac"));
  const gOff = paper(window.posWallCopy("top", 99, false, false));
  ok("AC-56: the empty group still prints, with no Vacant", gOff.el.querySelectorAll(".oc-box").length === 3 && !gOff.text.includes("Vacant"));
  const gHr = paper(window.posWallCopy("top", 99, true, true));
  ok("AC-59: one opening in a group says Job opening raised once", gHr.text.split("Job opening raised").length - 1 === 1);
  ok("AC-59: two openings in a group say 2 job openings raised", gHr.text.includes("2 job openings raised"));
  /* AC-26: the screen's own state never reaches the paper */
  window.POS.ungrouped = { ["Cashier\u0000Noida\u0000Sales"]: true };
  window.POS.collapsed = { "G-TOP": true }; window.POS.zoom = 0.6;
  ok("AC-26: Show the N, a fold or the zoom on screen do not change the paper",
     window.posWallHtml(window.posWallCopy("top", 99, true, false), 99, 99) === g.html);
  window.POS.ungrouped = {}; window.POS.collapsed = {}; window.POS.zoom = 1;

  /* ── the button (AC-4, SEC-2) ───────────────────────────────────────── */
  const btn = doc.getElementById("pos-wall-btn");
  ok("AC-4: the button sits before + Add a seat", btn && btn.nextElementSibling && btn.nextElementSibling.id === "pos-add-btn"
     && btn.textContent.trim() === "Download wall chart (PDF)" && btn.classList.contains("btn-outline"));
  const realGp = window.gpFetch;
  const posLoadWith = async (reply) => {
    window.gpFetch = (m) => /position_table/.test(m) ? reply() : Promise.resolve({});
    await window.posLoad(); await settle(20);
  };
  await posLoadWith(() => Promise.resolve(F.dtc90()));
  ok("AC-4: rows give the button", btn.style.display === "");
  await posLoadWith(() => Promise.resolve(Object.assign(F.dtc90(), { rows: [] })));
  ok("AC-4: no rows, no button", btn.style.display === "none");
  await posLoadWith(() => Promise.resolve(F.dtc90()));
  await posLoadWith(() => Promise.reject(new Error("refused")));
  ok("AC-4: a failed load hides the button", btn.style.display === "none");

  /* ── the panel: nothing leaves the page (AC-8, SEC-1) ───────────────── */
  await posLoadWith(() => Promise.resolve(F.dtc90()));
  const called = [];
  const trap = (name) => function () { called.push(name); throw new Error(name + " called by the wall chart"); };
  window.gpFetch = trap("gpFetch"); window.frappe.call = trap("frappe.call"); window.fetch = trap("fetch");
  window.open = trap("window.open"); window.URL.createObjectURL = trap("URL.createObjectURL");
  // On the prototype: assigning localStorage.setItem only stores an item called "setItem".
  const realSetItem = window.Storage.prototype.setItem;
  window.Storage.prototype.setItem = trap("localStorage / sessionStorage setItem");
  const layer = () => doc.getElementById("pos-layer");
  const panelText = () => layer().textContent;
  const val = (id) => (doc.getElementById(id) || {}).value;
  const optTexts = (id) => [...doc.getElementById(id).options].map((o) => o.textContent);
  const ready = async () => { for (let i = 0; i < 40 && !window.POS.wall.L; i++) await settle(10); };
  const set = async (id, v) => {
    const el = doc.getElementById(id);
    el.focus();
    if (el.type === "checkbox" || el.type === "radio") { el.checked = v === undefined ? !el.checked : v; } else el.value = v;
    el.dispatchEvent(new window.Event("change", { bubbles: true }));
    await ready();
  };
  btn.focus(); btn.click(); await ready();
  ok("m1: after measuring, no drawing is left in the page", !doc.getElementById("pos-wall-print") && !!window.POS.wall.L.html);
  const sheet = layer().querySelector(".pos-sheet");
  ok("AC-6: a dialog, labelled by its heading", sheet && sheet.getAttribute("role") === "dialog" && sheet.getAttribute("aria-modal") === "true"
     && doc.getElementById(sheet.getAttribute("aria-labelledby")).textContent === "Download wall chart (PDF)");
  ok("AC-6: focus on the heading", doc.activeElement && doc.activeElement.id === "pos-sh-t");
  /* AC-9 */
  ok("AC-9: Start from the top", optTexts("pos-wall-start")[0] === "The top: Owner and Managing Director" && val("pos-wall-start") === "top");
  ok("AC-9: Levels 2", doc.getElementById("pos-wall-levels").selectedOptions[0].textContent === "2 levels: the top and the 22 seats under it");
  ok("AC-9: A3 with its size", doc.getElementById("pos-wall-paper-A3").checked && panelText().includes("A3 is 297 × 420 mm."));
  ok("AC-9: one sheet, Show Vacant ticked, HR copy not", doc.getElementById("pos-wall-sheets-one").checked
     && doc.getElementById("pos-wall-vacant").checked && !doc.getElementById("pos-wall-hr").checked);
  ok("AC-10: six places to start", optTexts("pos-wall-start").length === 6 && optTexts("pos-wall-start")[1] === "— Admin Head",
     optTexts("pos-wall-start").join(" | "));
  ok("AC-11: two level options, the second All", optTexts("pos-wall-levels").length === 2
     && optTexts("pos-wall-levels")[1] === "All 3 levels: every seat (90 seats, 363 people)", optTexts("pos-wall-levels").join(" | "));
  ok("AC-11: never 'head of department'", !/head of department/i.test(panelText()));
  ok("AC-15: intro and privacy line", panelText().includes("A chart of seats and names for a wall, sized for the paper you choose.")
     && panelText().includes("Only seat names, job titles, departments and people's names print. Flags, leaving dates and HR notes never do."));
  ok("AC-17: names the branches, never 'whole company'",
     panelText().includes("Covers 6 branches: Ambala, Delhi, Gurgaon, Head Office, Noida, Pitampura.") && !/whole company/.test(panelText()));
  ok("AC-14: the people in no seat, with the link", panelText().includes("82 active people are not in any seat, so they are not on the chart. Placing them in a seat first is recommended, not required.")
     && layer().innerHTML.includes("posWallUnseated()"));
  const result = layer().querySelector(".pos-wall-result");
  ok("AC-34: the result is a polite live region", result && result.getAttribute("role") === "status" && result.getAttribute("aria-live") === "polite");
  ok("AC-31: seats and people for the choice", panelText().includes("23 seats · 21 people"));
  ok("AC-13: no filter, no filter note", !panelText().includes("does not apply here"));
  /* AC-11: a start with one level under it offers only All; Levels resets */
  await set("pos-wall-levels", "3");
  await set("pos-wall-start", bo.id);
  ok("AC-11: Back Office Manager offers only All", optTexts("pos-wall-levels").length === 1
     && optTexts("pos-wall-levels")[0] === "All 2 levels: every seat (11 seats, 72 people)", optTexts("pos-wall-levels").join(" | "));
  await set("pos-wall-start", "top");
  ok("AC-11: changing Start from resets Levels to its first option", val("pos-wall-levels") === "2");
  /* change everything (AC-8) */
  await set("pos-wall-levels", "3"); await set("pos-wall-paper-A1", true); await set("pos-wall-sheets-several", true);
  await set("pos-wall-vacant", false); await set("pos-wall-hr", true);
  ok("AC-62: HR copy on - the office note and its privacy line", panelText().includes("Print in the office, not at a print shop.")
     && panelText().includes("This HR copy also prints leaving dates and job openings. Replacement plans and HR notes never print."));
  ok("AC-12: the size follows the paper", panelText().includes("A1 is 594 × 841 mm."));
  ok("focus stays on the control that was changed", doc.activeElement && doc.activeElement.id === "pos-wall-hr", doc.activeElement && doc.activeElement.id);
  let printed = 0;
  window.print = () => { printed++; };
  window.posWallPrint(); await settle(20);
  ok("AC-8 / SEC-1: no server call, no new window, no blob, no storage write", called.length === 0, called.join(", "));
  ok("AC-8: window.print called once", printed === 1);
  window.dispatchEvent(new window.Event("afterprint"));
  /* AC-7 and AC-16, AC-58 */
  doc.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  ok("AC-7: Escape closes the panel", !layer().innerHTML);
  ok("AC-7: focus returns to the button", doc.activeElement === btn);
  ok("cleanup: the paper is gone when the panel closes", !doc.getElementById("pos-wall-print"));
  btn.click(); await ready();
  ok("AC-16: choices kept on the same visit", val("pos-wall-levels") === "3" && doc.getElementById("pos-wall-paper-A1").checked
     && doc.getElementById("pos-wall-sheets-several").checked && !doc.getElementById("pos-wall-vacant").checked);
  ok("AC-58: HR copy is unticked every time the panel opens", !doc.getElementById("pos-wall-hr").checked && !panelText().includes("Print in the office"));
  layer().querySelector(".pos-scrim").click();
  ok("AC-7: the dimmed background closes it too", !layer().innerHTML && doc.activeElement === btn);
  window.POS.wall = null;
  /* AC-13 filter notes */
  const fb = doc.getElementById("pos-f-branch"), fr = doc.getElementById("pos-f-role");
  fb.innerHTML = '<option value="">All</option><option value="Noida">Noida</option>'; fb.value = "Noida";
  btn.click(); await ready();
  ok("AC-13: one filter", panelText().includes("Your Branch filter does not apply here. The wall chart uses only the choices below."));
  ok("AC-13: counts are all 90 seats", optTexts("pos-wall-levels")[1].includes("90 seats"));
  window.posCloseSheet();
  fr.innerHTML = '<option value="">All</option><option value="RSO">RSO</option>'; fr.value = "RSO";
  btn.click(); await ready();
  ok("AC-13: two filters", panelText().includes("Your Branch and Job role filters do not apply here. The wall chart uses only the choices below."));
  window.posCloseSheet(); fb.value = ""; fr.value = "";
  /* AC-14 variants, D-5 */
  window.POS.unseated = null; btn.click(); await ready();
  ok("AC-14: no list sent - only people in a seat, no link", panelText().includes("Only people placed in a seat are on the chart.") && !layer().innerHTML.includes("posWallUnseated"));
  window.posCloseSheet(); window.POS.unseated = []; btn.click(); await ready();
  ok("D-5: nobody unseated - no people note", !panelText().includes("not in any seat") && !panelText().includes("Only people placed"));
  window.posCloseSheet(); window.POS.wall = null;
  /* AC-65: no tick without leaving dates */
  load(F.noLeave(false)); btn.click(); await ready();
  ok("AC-65: no HR copy checkbox in the DOM", !doc.getElementById("pos-wall-hr") && !panelText().includes("HR copy"));
  window.posCloseSheet(); window.POS.wall = null;
  /* AC-65 (Surbhi, 25 Oct 2026): the HR copy is for HR only. A manager who
     is sent leaving dates for their own reports never gets the tick; HR does,
     and it is off every time the panel opens. */
  load(F.manager()); btn.click(); await ready();
  ok("HR only: a manager who sees leaving dates gets no HR copy tick", window.POS.may_see_leaving
     && window.POS.unseated === null && !doc.getElementById("pos-wall-hr") && !panelText().includes("HR copy"));
  const mgr = paper(window.posWallCopy("top", 99, true, true));
  ok("HR only: and asking for it anyway prints no leaving date", !mgr.text.includes("leaving") && !mgr.text.includes("Job opening"));
  ok("HR only: the manager's copy holds no HR keys", !keysOk(window.posWallCopy("top", 99, true, true), false));
  window.posCloseSheet(); window.POS.wall = null;
  load(F.dtc90());
  for (const round of [1, 2, 3]) {
    btn.click(); await ready();
    const tick = doc.getElementById("pos-wall-hr");
    ok("HR only: an HR user gets the tick, unticked on opening " + round, tick && !tick.checked);
    if (tick) await set("pos-wall-hr", true);
    window.posCloseSheet();
  }
  window.POS.wall = null;
  /* the soft warning over 20 sheets */
  btn.click(); await ready();
  await set("pos-wall-sheets-several", true); await set("pos-wall-paper-A4", true);
  window.POS.wall.L = { html: "", w: 33440, h: 2118 };
  window.posWallPaint();
  const many = window.posWallPlan(window.POS.wall.L, "A4", "several", false);
  ok("over 20 sheets: a soft warning with the number", many.cols * many.rows > 20 && panelText().includes(
     "This will make about " + many.cols * many.rows + " sheets and may take a minute. Choose a larger paper size to use fewer sheets."));
  ok("over 20 sheets: not a block - Open print preview is still there", !!doc.getElementById("pos-wall-go") && !doc.getElementById("pos-wall-go").disabled);
  window.POS.wall.L = { html: "", w: 3344, h: 2118 };
  window.posWallPaint();
  ok("20 sheets or fewer: no such warning", !panelText().includes("may take a minute"));
  window.posCloseSheet(); window.POS.wall = null;

  /* AC-48: the Owner */
  load(F.owner()); btn.click(); await ready();
  ok("AC-48: scope note", panelText().includes("You can see 1 branch, Pitampura, so the chart covers Pitampura only. Its seats report to managers in other branches, so they print side by side with no lines above them."));
  ok("AC-48: one start, one level", optTexts("pos-wall-start").join("|") === "The top of what you can see (8 seats)"
     && optTexts("pos-wall-levels").join("|") === "All: 1 level, 8 seats side by side", optTexts("pos-wall-levels").join("|"));
  ok("AC-14: branch-limited people note", panelText().includes("35 active Pitampura people are not in any seat"));
  const own = paper(window.posWallCopy("top", 1, true, false));
  ok("AC-49: 8 boxes, his 34 people and nothing else", own.el.querySelectorAll(".oc-box").length === 8 && names(own) === 34
     && !!own.el.querySelector(".pos-wall-grid"));
  window.posCloseSheet(); window.POS.wall = null;
  window.gpFetch = realGp; window.Storage.prototype.setItem = realSetItem;

  /* ── Open print preview (AC-37 to AC-41, AC-60, AC-61, SEC-4, PRIV-2) ── */
  load(F.dtc90());
  doc.title = "Alvoraa portal";
  let seen = null, prints = 0;
  window.print = () => {
    prints++;
    const st = doc.getElementById("pos-wall-page");
    seen = { title: doc.title, style: st ? st.textContent : null, last: doc.body.lastElementChild === st,
             styles: doc.querySelectorAll("#pos-wall-page").length, printing: doc.body.classList.contains("pos-wall-printing"),
             sheets: [...doc.querySelectorAll("#pos-wall-print .pos-wall-sheet")].map((s) => ({
               banner: (s.querySelector(".pos-wall-banner") || {}).textContent || "", foot: s.querySelector(".pos-wall-foot").textContent,
               at: s.querySelector(".pos-wall-at").getAttribute("style") })),
             text: (doc.getElementById("pos-wall-print") || {}).textContent || "" };
  };
  const printWith = async (choices, L) => {
    window.POS.wall = null;
    btn.click(); await ready();
    for (const [id, v] of choices) await set(id, v);
    if (L) window.POS.wall.L = Object.assign({ html: '<div class="pos-wall"></div>' }, L);
    seen = null; prints = 0;
    window.posWallPrint();
    return seen;
  };
  const allNames = F.dtc90().rows.flatMap((r) => r.people.map((p) => p.name));
  let s = await printWith([["pos-wall-levels", "3"], ["pos-wall-paper-A1", true]], { w: 3344, h: 2118 });
  ok("AC-37: one style, after the portal's rule, in millimetres", s && s.styles === 1 && s.last && /size:\s*\d+mm \d+mm/.test(s.style) && !/A[0-4]/.test(s.style), s && s.style);
  ok("AC-37: A1 landscape is 841mm 594mm", s && s.style === "@page{size:841mm 594mm;margin:10mm}", s && s.style);
  ok("AC-37: window.print called once", prints === 1);
  ok("AC-38: the file name", s && s.title === "Wall chart - Sample Fashions Pvt Ltd - all levels - A1 - 2026-10-24", s && s.title);
  ok("AC-38: it matches the pattern and names nobody", s && /^Wall chart - .+ - (\d+ levels|all levels) - A[0-4] - \d{4}-\d{2}-\d{2}$/.test(s.title)
     && !allNames.some((n) => s.title.includes(n)) && !s.title.includes("PRINTER-SNTL") && !s.title.includes("Owner"));
  ok("AC-41: the footer", s && s.sheets.length === 1 && s.sheets[0].foot
     === "Sample Fashions Pvt Ltd · 6 branches · all levels from the top · as at 24 Oct 2026 · 90 seats · 363 people in seats", s && s.sheets[0] && s.sheets[0].foot);
  ok("AC-41 / D5: nobody's name on the paper's words", s && !/printed by|PRINTER-SNTL/.test(s.text));
  ok("AC-60: wall copy - no banner, no HR words", s && !s.sheets[0].banner && !s.text.includes("HR use only"));
  ok("AC-40: printing marks the page so only the wall chart prints", s && s.printing);
  window.dispatchEvent(new window.Event("afterprint"));
  ok("AC-39: after printing, the page size is gone", !doc.getElementById("pos-wall-page"));
  ok("AC-39: the title is back", doc.title === "Alvoraa portal", doc.title);
  ok("AC-39: Ctrl+P is the screen chart again", !doc.body.classList.contains("pos-wall-printing") && !doc.getElementById("pos-wall-print"));
  ok("AC-44: the panel is still open", !!layer().querySelector(".pos-sheet") && panelText().includes("names at"));
  window.posCloseSheet();
  s = await printWith([["pos-wall-paper-A0", true]], { w: 1000, h: 1500 });
  ok("AC-37: A0 portrait is 841mm 1189mm", s && s.style === "@page{size:841mm 1189mm;margin:10mm}", s && s.style);
  ok("AC-38: 2 levels in the name", s && s.title === "Wall chart - Sample Fashions Pvt Ltd - 2 levels - A0 - 2026-10-24", s && s.title);
  window.posCloseSheet();
  ok("AC-39: closing without the print window firing afterprint still cleans up",
     !doc.getElementById("pos-wall-page") && doc.title === "Alvoraa portal" && !doc.body.classList.contains("pos-wall-printing"));
  s = await printWith([["pos-wall-levels", "3"], ["pos-wall-paper-A3", true], ["pos-wall-hr", true]], { w: 3344, h: 2138 });
  ok("AC-61: the HR copy's file name", s && s.title === "HR copy - Wall chart - Sample Fashions Pvt Ltd - all levels - A3 - 2026-10-24"
     && /^HR copy - Wall chart - .+ - (\d+ levels|all levels) - A[0-4] - \d{4}-\d{2}-\d{2}$/.test(s.title), s && s.title);
  ok("AC-60: the banner at the top of the sheet", s && s.sheets[0].banner === "HR use only - not for display");
  ok("AC-60: and at the start of its footer", s && s.sheets[0].foot.indexOf("HR use only - not for display · Sample Fashions") === 0, s && s.sheets[0].foot);
  window.posCloseSheet();
  /* ── several sheets (AC-45 to AC-47, AC-63) ─────────────────────────── */
  s = await printWith([["pos-wall-levels", "3"], ["pos-wall-paper-A3", true], ["pos-wall-sheets-several", true], ["pos-wall-hr", true]], { w: 3344, h: 2118 });
  const P3 = window.posWallPlan({ w: 3344, h: 2118 }, "A3", "several", true);
  ok("AC-45: n sheets, c across, r down", s && s.sheets.length === P3.cols * P3.rows && P3.cols === 3 && P3.rows >= 3, s && s.sheets.length + " " + P3.cols + "x" + P3.rows);
  ok("AC-46 / m3: each footer says where the sheet goes, right after the HR tag", s && s.sheets.every((sh, i) =>
     sh.foot.indexOf("HR use only - not for display · Sheet " + (i + 1) + " of " + s.sheets.length + " (row " + (Math.floor(i / P3.cols) + 1)
       + ", column " + (i % P3.cols + 1) + ") · Sample Fashions") === 0),
     s && s.sheets[4] && s.sheets[4].foot);
  const offs = s ? s.sheets.map((sh) => sh.at.match(/left:(-?[\d.]+)px;top:(-?[\d.]+)px/).slice(1).map(Number)) : [];
  ok("AC-46: side by side the sheets cover the chart with no gap and no overlap", offs.length && offs.every(([x, y], i) =>
     Math.abs(x + (i % P3.cols) * P3.pw) < 0.01 && Math.abs(y + Math.floor(i / P3.cols) * P3.ph) < 0.01)
     && P3.cols * P3.pw >= 3344 * P3.scale && (P3.cols - 1) * P3.pw < 3344 * P3.scale
     && P3.rows * P3.ph >= 2118 * P3.scale && (P3.rows - 1) * P3.ph < 2118 * P3.scale);
  ok("AC-63: every HR copy sheet: the banner, and the footer starts with it", s && s.sheets.every((sh) =>
     sh.banner === "HR use only - not for display" && sh.foot.indexOf("HR use only - not for display ·") === 0));
  window.dispatchEvent(new window.Event("afterprint")); window.posCloseSheet();
  s = await printWith([["pos-wall-sheets-several", true]], { w: 1128, h: 608 });
  ok("AC-47: several sheets that fit on one at 10 pt print as one", s && s.sheets.length === 1 && !s.sheets[0].foot.includes("Sheet 1"));
  ok("AC-47: and the panel says so", panelText().includes("It fits on one sheet at this size, so it prints as one. Readable"));
  window.dispatchEvent(new window.Event("afterprint")); window.posCloseSheet();

  /* review m2: afterprint never came, and HR left Positions with the panel
     open - the next panel's print is not the wall chart */
  s = await printWith([["pos-wall-hr", true]], { w: 3344, h: 2118 });
  const pn = doc.getElementById("panel-positions"), wasActive = pn.classList.contains("active");
  pn.classList.add("active");
  window.dispatchEvent(new window.Event("beforeprint"));
  ok("m2: on Positions, its own print keeps the wall chart", doc.body.classList.contains("pos-wall-printing"));
  pn.classList.remove("active");
  window.dispatchEvent(new window.Event("beforeprint"));
  ok("m2: from another panel, the wall chart, its page size and its title are gone before printing",
     !doc.body.classList.contains("pos-wall-printing") && !doc.getElementById("pos-wall-page")
     && !doc.getElementById("pos-wall-print") && doc.title === "Alvoraa portal", doc.title);
  if (wasActive) pn.classList.add("active");
  window.posCloseSheet();

  /* security F2: Ctrl+P with Show = "somebody is leaving" (or "key seats")
     prints the chart without that filter */
  {
    const show = doc.getElementById("pos-f-open"), view = doc.getElementById("pos-f-view");
    const pnl = doc.getElementById("panel-positions"), was = pnl.classList.contains("active");
    pnl.classList.add("active");
    for (const v of ["leaving", "key"]) {
      for (const how of ["tree", "list"]) {
        view.value = how; show.value = v; window.posFilterChanged("");
        if (how === "list") { view.value = "list"; window.posPaint(); }
        const before = doc.getElementById("pos-body").innerHTML.length;
        window.dispatchEvent(new window.Event("beforeprint"));
        const body = doc.getElementById("pos-body").innerHTML;
        ok("F2: Ctrl+P clears Show = " + v + " (" + how + " view first)", show.value === "" && before > 0
           && !/Show: Only/.test(body) && body.includes("Owner and Managing Director") && body.includes("IT Head"));
        window.dispatchEvent(new window.Event("afterprint"));
        const back = doc.getElementById("pos-body").innerHTML;
        ok("F2: after printing the filter and the view are back (" + v + ", " + how + ")", show.value === v && view.value === how
           && !back.includes("IT Head"));
      }
    }
    show.value = "open"; window.posFilterChanged("");
    window.dispatchEvent(new window.Event("beforeprint"));
    ok("F2: other filters are left as they are", show.value === "open");
    window.posClearFilter();
    if (!was) pnl.classList.remove("active");
  }

  /* printing while the size is still being worked out waits for it (AC-35) */
  window.POS.wall = null; btn.click(); await ready();
  await set("pos-wall-paper-A2", true);
  window.POS.wall.fast = false;   // as if the last drawing had been slow
  doc.getElementById("pos-wall-start").value = bo.id; window.posWallSet("start", bo.id);
  prints = 0; window.posWallPrint();
  ok("AC-35: Open print preview while working waits", prints === 0 && !window.POS.wall.L);
  await settle(80);
  ok("AC-35: and prints once the size is ready", prints === 1);
  window.dispatchEvent(new window.Event("afterprint")); window.posCloseSheet(); window.POS.wall = null;

  /* ── AC-2: one window.print() in the Positions code, the wall chart's ── */
  const src = require("fs").readFileSync(require("path").join(__dirname, "..", "alvoraa_portal", "alvoraa_portal", "public", "js", "ess", "portal.js"), "utf8");
  const posCode = src.slice(src.indexOf("window.posLoad = "), src.indexOf("function ocPaint"));
  const fnStart = posCode.indexOf("window.posWallPrint = function");
  const fnBody = posCode.slice(fnStart, posCode.indexOf("\n};", fnStart));
  ok("AC-2: no onclick=\"window.print()\" in the Positions code", !/onclick="window\.print\(\)"/.test(posCode));
  ok("AC-2: exactly one window.print(), inside the wall chart's print", (posCode.match(/window\.print\(\)/g) || []).length === 1 && fnBody.includes("window.print()"));

  /* ── slice 070: the paper prints what Reporting lines draws (AC-55 - AC-60, PRIV-2) ── */
  {
    const d = F.reporting();
    load(d);
    const box = (p, title, copy) => [...p.el.querySelectorAll(".oc-box")].filter((b) => b.querySelector(".ti").textContent === title
      && b.classList.contains("copy") === copy);
    const all = paper(window.posWallCopy("top", 99, true, false));
    const printed = [...all.el.querySelectorAll(".nm > div")].map((x) => x.textContent).sort().join("|");
    const everyone = d.rows.reduce((a, r) => a.concat(r.people.map((p) => p.name)), []).sort().join("|");
    ok("070 AC-55: every person prints exactly once", printed === everyone, names(all) + " printed");
    const copies = [...all.el.querySelectorAll(".oc-box.copy")];
    ok("070 AC-55: copies print dashed, each with its line", copies.length >= 10
       && copies.every((b) => /^(Same seat as under|Set up under) /.test((b.querySelector(".oc-same") || {}).textContent || "")), copies.length);
    ok("070 AC-55: a copy says it is the same seat", (box(all, "Office Executive", true)[0] || { textContent: "" }).textContent
       .includes("Same seat as under Owner and Managing Director · 6 in all"));
    ok("070 AC-55: a home says where its other people are", (box(all, "Back Office", false)[0] || { textContent: "" }).textContent
       .includes("63 more shown under 2 other managers"));
    const mis = box(all, "MIS", false)[0];
    ok("070 AC-57: a home with all its people elsewhere says None here, and its open slot", mis
       && /None here: all 1 under Chief Financial Officer/.test(mis.textContent) && /1 open/.test(mis.textContent) && !/Vacant/.test(mis.textContent));
    ok("070 AC-57: Vacant only on a seat with nobody at all", [...all.el.querySelectorAll(".vac")].filter((v) => v.textContent === "Vacant").length === 5);
    ok("070 AC-23 on paper: a home with nothing left does not print", !box(all, "Store Auditor", false).length
       && /Set up under Owner and Managing Director/.test((box(all, "Store Auditor", true)[0] || { textContent: "" }).textContent));
    const novac = paper(window.posWallCopy("top", 99, false, false));
    ok("070 AC-57: with Show Vacant off, no Vacant and no open count", !/Vacant| open\b/.test(novac.text));
    const bo = d.rows.find((r) => r.title === "Back Office"), bx = d.rows.find((r) => r.title === "Backoffice Executive");
    const one = window.posWallCopy(bo.id, 1, true, false)[0];
    ok("070 AC-59: below counts each seat and person once, never the box's own seat", one.below && one.below.seats === 3 && one.below.people === 65,   // BX, and copies of Back Office, Data Entry, Billing under it
       JSON.stringify(one.below));
    window.POS.wall = { start: "top" };
    const starts = window.posWallStarts(window.posKids(window.POS.rows)).map((s) => s[0]);
    ok("070 AC-60: a seat with only copies under it is a place to start", starts.includes(bx.id));
    const fromBx = paper(window.posWallCopy(bx.id, 99, true, false));
    ok("070 AC-60: and starting there prints its copies", fromBx.el.querySelectorAll(".oc-box.copy").length === 3 && names(fromBx) === 1 + 57 + 4 + 3,
       names(fromBx));
    window.POS.wall = null;
    // AC-56: the footer counts seat records and people once.
    let shot = null;
    window.print = () => { shot = doc.querySelector("#pos-wall-print .pos-wall-foot").textContent; };
    window.posWallOpen(); await settle(80);
    window.posWallSet("levels", String(window.posWallLevels(window.posKids(window.POS.rows)).slice(-1)[0][0])); await settle(80);
    window.posWallPrint();
    ok("070 AC-56: the footer reads seats · people in seats", shot && shot.endsWith(" · " + d.rows.length + " seats · "
       + d.rows.reduce((a, r) => a + r.people.length, 0) + " people in seats"), shot);
    window.dispatchEvent(new window.Event("afterprint")); window.posCloseSheet(); window.POS.wall = null;

    // PRIV-2: manager ids, the unseated manager's name, plans and every 069 sentinel stay off paper.
    const s = F.reporting();
    s.rows.forEach((r) => r.people.forEach((p) => Object.assign(p, { assignment: "ASG-SNTL", hired_on: "HIRED-SNTL", type: p.type,
      plan: { note: "PLAN-SNTL" }, image: "IMG-SNTL" })));
    s.rows.find((r) => r.title === "Packing").people[0].manager = "MGR-SNTL";
    s.unseated.push({ employee: "MGR-SNTL", name: "MGRNAME-SNTL", branch: "Noida", no_manager: false });
    load(s);
    for (const hr of [false, true]) {
      const p = paper(window.posWallCopy("top", 99, true, hr));
      ok("070 PRIV-2 (HR copy " + (hr ? "on" : "off") + "): no manager id, unseated name, employee id or plan reaches paper",
         !/MGR-SNTL|MGRNAME-SNTL|HR-EMP|ASG-SNTL|HIRED-SNTL|PLAN-SNTL|IMG-SNTL/.test(p.html));
      const bad = keysOk(window.posWallCopy("top", 99, true, hr), hr);
      ok("070 PRIV-2 (HR copy " + (hr ? "on" : "off") + "): copies hold exactly the allowed keys", !bad, bad);
    }
  }

  if (problems.length) {
    console.error("wall chart: " + problems.length + " problem(s) in " + checks + " checks");
    problems.forEach((p) => console.error("  FAIL " + p));
    process.exit(1);
  }
  console.log("wall chart: " + checks + " checks - nothing private reaches paper with the HR copy off or on, "
              + "the copy holds only allowed keys, every seat and every name prints, identical seats merge");
  process.exit(0);
})();
