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

  if (problems.length) {
    console.error("wall chart: " + problems.length + " problem(s) in " + checks + " checks");
    problems.forEach((p) => console.error("  FAIL " + p));
    process.exit(1);
  }
  console.log("wall chart: " + checks + " checks - nothing private reaches paper with the HR copy off or on, "
              + "the copy holds only allowed keys, every seat and every name prints, identical seats merge");
  process.exit(0);
})();
