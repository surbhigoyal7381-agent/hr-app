/**
 * Slice 090: the People trends panel, driven in jsdom (the panel part + people-trends.js).
 * What it proves: what the page SENDS for a chip tap and for a filter (the "test what it
 * sends" rule), that a figure the server did not send is not drawn, the states
 * (not set up, not shared, error with Code PT-LOAD), and that nothing is stored in the browser.
 */
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");
const APP = path.join(__dirname, "..", "alvoraa_portal");
let fails = 0;
const ok = (c, m) => { console.log((c ? "  ok   " : "  FAIL ") + m); if (!c) fails++; };
const tick = () => new Promise(r => setTimeout(r, 20));

const part = fs.readFileSync(path.join(APP, "templates/includes/ess/parts/people-trends.html"), "utf8");
const script = fs.readFileSync(path.join(APP, "public/js/ess/people-trends.js"), "utf8");

const OK = {
  state: "ok", period: 90, minimum: 5, headline: "Headcount 43, up 1 in 3 months. 3 joined, 2 left.",
  window: { start: "2026-08-25", end: "2026-11-22", days: 90, clipped: false, records_start: "2020-01-01", compare: { start: "2026-05-27", end: "2026-08-24" } },
  data_up_to: "2026-11-22",
  scope: { company: "Kavya Retail", branch: null, department: null, employment_type: null, branches_only: false, several_companies: false },
  filters: { companies: [], branches: [{ value: "Civil Lines", shared: true }, { value: "Hilltop Kiosk", shared: false }], departments: [], employment_types: [] },
  people: { headcount: 43, joined: 3, left: 2, net: 1, headcount_start: 42, attrition: 4.7, before: { headcount: 40, joined: 1, left: 1, net: 0, attrition: 2.5 } },
  early: { shared: false, reason: "whole_company_only" },
  chart: { shared: true, points: [{ start: "2026-08-25", joined: 1, left: 0, net: 1 }, { start: "2026-09-01", joined: 2, left: 2, net: 1 }] },
  attendance: { shared: true, absent_pct: 4.6, series: [4.1, 5.0], left_out_days: 0, before: { absent_pct: 4.0 } },
  leave: { shared: true, days: 12, series: [5, 7], pending: 2, before: { days: 10 }, types: [{ type: "Casual", days: 12 }] },
  by_company: null, data_quality: null,
};

function page(answer) {
  const dom = new JSDOM("<!doctype html><body>" + part + "</body>", { runScripts: "outside-only", url: "http://localhost/hrms-employee" });
  const w = dom.window, sent = [];
  w.frappe = { call: opts => { sent.push(opts.args); answer(sent.length, opts); return {}; } };
  w.eval(script);
  return { w, d: w.document, sent };
}
const reply = body => (_n, opts) => setTimeout(() => opts.callback({ message: body }), 0);

(async () => {
  let p = page(reply(OK));
  p.w.ptLoad(); await tick();
  const d = p.d;
  ok(p.sent.length === 1 && p.sent[0].period === undefined, "first load sends no period (the server uses the saved one)");
  ok(d.querySelectorAll('[role="radio"]').length === 5 && d.querySelector('[role="radiogroup"]'), "five chips in a radiogroup");
  ok(d.querySelector('[role="radio"][aria-checked="true"]').textContent === "3 months", "the answer's period is the selected chip");
  ok(/Headcount 43/.test(d.body.textContent) && /Net change/.test(d.body.textContent), "tiles drawn");
  ok(/Early leavers are shown for the whole company only/.test(d.body.textContent), "early leavers say whole company only");
  ok(/Hilltop Kiosk \(Not shared\)/.test(d.body.innerHTML), "a hidden branch is listed as Not shared");
  ok(!/ps-pt-/.test(d.body.innerHTML) && d.body.querySelector("script") === null, "no script in the answer's markup");
  ok(p.w.localStorage.length === 0 && p.w.sessionStorage.length === 0, "nothing stored in the browser");

  d.querySelector('[data-pt-per="30"]').dispatchEvent(new p.w.MouseEvent("click", { bubbles: true }));
  await tick();
  ok(p.sent.length === 2 && p.sent[1].period === 30, "one tap sends exactly one request with that period");

  const sel = d.querySelector('[data-pt-f="branch"]'); sel.value = "Civil Lines";
  sel.dispatchEvent(new p.w.Event("change", { bubbles: true })); await tick();
  ok(p.sent[2].branch === "Civil Lines" && p.sent[2].company === "Kavya Retail", "a filter sends the one filter and the company");

  // a figure the server withheld is not drawn
  const lean = JSON.parse(JSON.stringify(OK)); delete lean.people.left; delete lean.people.net; delete lean.people.attrition;
  p = page(reply(lean)); p.w.ptLoad(); await tick();
  const tileOf = label => [...p.d.querySelectorAll(".pt-tile")].find(t => t.querySelector(".pt-l").textContent === label).querySelector(".pt-v").textContent;
  ok(tileOf("Left") === "Not shared" && tileOf("Net change") === "Not shared" && tileOf("Attrition") === "Not shared" && tileOf("Headcount") === "43",
     "a withheld Left leaves Not shared in Left, Net change and Attrition, and Headcount stays");

  p = page(reply({ state: "not_set_up" })); p.w.ptLoad(); await tick();
  ok(/not set up for you yet/.test(p.d.body.textContent) && !p.d.querySelector('[role="radio"]'), "not set up page shows nothing else");

  p = page(reply({ state: "not_shared", reason: "subtraction", minimum: 5, period: 90, window: OK.window, scope: OK.scope, filters: OK.filters, data_up_to: null }));
  p.w.ptLoad(); await tick();
  ok(/work out a smaller group/.test(p.d.body.textContent) && !/Headcount/.test(p.d.body.textContent), "not shared banner replaces the page");
  p.d.querySelector("[data-pt-why]").dispatchEvent(new p.w.MouseEvent("click", { bubbles: true }));
  ok(!!p.d.querySelector("#pt-sheet") && /fewer than 5 people at any time in the last two years/.test(p.d.querySelector("#pt-sheet").textContent), "the why sheet opens with the two-year sentence");
  p.d.dispatchEvent(new p.w.KeyboardEvent("keydown", { key: "Escape" }));
  ok(!p.d.querySelector("#pt-sheet"), "Escape closes the sheet");

  p = page((_n, opts) => setTimeout(() => opts.error({ status: 500 }), 0)); p.w.ptLoad(); await tick();
  ok(/We could not load People trends/.test(p.d.body.textContent) && /PT-LOAD/.test(p.d.body.textContent), "error shows Code PT-LOAD and no raw message");
  p = page((_n, opts) => setTimeout(() => opts.error({ status: 403 }), 0)); p.w.ptLoad(); await tick();
  ok(/That view is not available to you/.test(p.d.body.textContent) && /PT-SCOPE/.test(p.d.body.textContent), "a refused filter says so without saying whether it exists");

  console.log(fails ? "FAILED " + fails : "all ok");
  process.exit(fails ? 1 : 0);
})();
