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
    const want = ["below", "branch", "department", "designation", "kids", "names", "title", "vacant"]
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
  ok("D-6: the Noida box has all 3 names and no Vacant", gb[0] && gb[0].querySelectorAll(".nm > div").length === 3 && !gb[0].querySelector(".vac"));
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
  window.posWallPrint(); await settle(20);
  ok("AC-8 / SEC-1: no server call, no new window, no blob, no storage write", called.length === 0, called.join(", "));
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

  if (problems.length) {
    console.error("wall chart: " + problems.length + " problem(s) in " + checks + " checks");
    problems.forEach((p) => console.error("  FAIL " + p));
    process.exit(1);
  }
  console.log("wall chart: " + checks + " checks - nothing private reaches paper with the HR copy off or on, "
              + "the copy holds only allowed keys, every seat and every name prints, identical seats merge");
  process.exit(0);
})();
