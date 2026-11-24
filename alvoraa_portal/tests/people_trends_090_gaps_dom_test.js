/**
 * Slice 090, test-engineer gap tests (jsdom): what the engineer's DOM test did not cover.
 * Skeleton on first paint, the offline line, answers arriving out of order, the 2 s dwell
 * save, keyboard basics, and the text-size rule on the panel's own CSS.
 */
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");
const APP = path.join(__dirname, "..", "alvoraa_portal");
let fails = 0;
const ok = (c, m) => { console.log((c ? "  ok   " : "  FAIL ") + m); if (!c) fails++; };
const wait = ms => new Promise(r => setTimeout(r, ms));

const part = fs.readFileSync(path.join(APP, "templates/includes/ess/parts/people-trends.html"), "utf8");
const script = fs.readFileSync(path.join(APP, "public/js/ess/people-trends.js"), "utf8");
const mk = (period, headcount) => ({
  state: "ok", period, minimum: 5, headline: "Headcount " + headcount + ".",
  window: { start: "2026-08-25", end: "2026-11-22", days: period, clipped: false, records_start: "2020-01-01", compare: null },
  data_up_to: "2026-11-22",
  scope: { company: "Kavya Retail", branch: null, department: null, employment_type: null, branches_only: false, several_companies: false },
  filters: { companies: [], branches: [], departments: [], employment_types: [] },
  people: { headcount, joined: 1, left: 1, net: 0, headcount_start: headcount, attrition: 1.0, before: null },
  early: { shared: false, reason: "whole_company_only" }, chart: { shared: true, points: [{ start: "2026-08-25", joined: 1, left: 0, net: 1 }] }, attendance: { shared: true, absent_pct: 4.6, series: [4.1], left_out_days: 0, before: null }, leave: { shared: true, days: 3, series: [3], pending: 0, before: null, types: [] }, by_company: null, data_quality: null,
});
function page(handler, online) {
  const dom = new JSDOM("<!doctype html><body>" + part + "</body>", { runScripts: "outside-only", url: "http://localhost/hrms-employee", pretendToBeVisual: true });
  const w = dom.window, calls = [];
  if (online === false) Object.defineProperty(w.navigator, "onLine", { get: () => false });
  // fetch, as the panel uses it (OPS-18). `o.callback(body)` answers 200 with body; `o.error({status})` answers with that
  // HTTP status (0 = the connection dropped). The website frappe.call must never be used.
  w.frappe = { csrf_token: "tok", call: () => { throw new Error("frappe.call used"); } };
  w.fetch = (url, opts) => new Promise((resolve, reject) => {
    const o = { method: url, args: JSON.parse(opts.body) };
    o.callback = body => resolve({ status: 200, ok: true, json: () => Promise.resolve(body) });
    o.error = e => e.status ? resolve({ status: e.status, ok: false, json: () => Promise.resolve({}) }) : reject(new Error("network"));
    calls.push(o); handler(o, calls.length);
  });
  w.eval(script);
  return { w, d: w.document, calls };
}
const click = (p, sel) => p.d.querySelector(sel).dispatchEvent(new p.w.MouseEvent("click", { bubbles: true }));

(async () => {
  // AC-95: skeleton on first paint, before any answer, with the stated words
  let held = [];
  let p = page(o => held.push(o));
  const t0 = Date.now(); p.w.ptLoad();
  ok(p.d.querySelectorAll(".pt-sk").length >= 2 && Date.now() - t0 < 300 &&
     /Loading People trends\. The period bar stays usable; figures fill in as they arrive\./.test(p.d.body.textContent),
     "AC-95 skeleton blocks and the stated words are on screen straight after the call is sent (no answer yet)");

  // AC-31: two taps, answers arrive in the wrong order: the page shows the LAST tap
  held = []; p = page(o => held.push(o));
  p.w.ptLoad(); held[0].callback({ message: mk(90, 43) }); await wait(20);
  click(p, '[data-pt-per="30"]'); click(p, '[data-pt-per="365"]');
  ok(held.length === 3 && held[1].args.period === 30 && held[2].args.period === 365, "AC-25 each tap sent its own request");
  held[2].callback({ message: mk(365, 365) }); held[1].callback({ message: mk(30, 30) }); await wait(20);   // newest first, then the stale one
  ok(/Headcount 365/.test(p.d.body.textContent) && !/Headcount 30\./.test(p.d.body.textContent) &&
     p.d.querySelector('[role="radio"][aria-checked="true"]').textContent === "1 year",
     "AC-31 a late answer to an older tap does not replace the answer to the last tap");
  // same, and the older request FAILS after the newest succeeded: no error note
  held = []; p = page(o => held.push(o)); p.w.ptLoad(); held[0].callback({ message: mk(90, 43) }); await wait(20);
  click(p, '[data-pt-per="30"]'); click(p, '[data-pt-per="365"]');
  held[2].callback({ message: mk(365, 365) }); held[1].error({ status: 500 }); await wait(20);
  ok(!/did not load|could not load/.test(p.d.body.textContent), "AC-31 a stale request that fails later shows nothing");

  // AC-97: network drop on a chip tap keeps the old figures and says so
  held = []; p = page(o => held.push(o)); p.w.ptLoad(); held[0].callback({ message: mk(90, 43) }); await wait(20);
  click(p, '[data-pt-per="30"]'); held[1].error({ status: 0 }); await wait(20);
  ok(/Headcount 43/.test(p.d.body.textContent) && /The new figures did not load\. These figures are still for 3 months\./.test(p.d.body.textContent) &&
     !!p.d.querySelector("[data-pt-retry]"), "AC-97 old figures stay and the line names the previous chip, with Try again");
  // AC-97 offline (browser says so): same line, and no request leaves the page
  held = []; p = page(o => held.push(o)); p.w.ptLoad(); held[0].callback({ message: mk(90, 43) }); await wait(20);
  Object.defineProperty(p.w.navigator, "onLine", { get: () => false });
  click(p, '[data-pt-per="365"]'); await wait(30);
  ok(held.length === 1 && /These figures are still for 3 months/.test(p.d.body.textContent), "AC-97 offline: no request sent, the same line shows");
  // offline on first load: the PT-LOAD page
  held = []; p = page(o => held.push(o), false); p.w.ptLoad(); await wait(30);
  ok(held.length === 0 && /PT-LOAD/.test(p.d.body.textContent), "AC-96 offline on first load: PT-LOAD page, nothing sent");

  // AC-29: three taps inside 1 s -> one save, about 2 s after the last tap, with the last chip
  held = []; p = page(o => held.push(o)); p.w.ptLoad(); held[0].callback({ message: mk(90, 43) }); await wait(20);
  ["30", "180", "365"].forEach(v => click(p, '[data-pt-per="' + v + '"]'));
  const saves = () => p.calls.filter(o => /save_people_trends_period/.test(o.method));
  await wait(1500);
  ok(saves().length === 0, "AC-29 no save before the chip has been kept for 2 s");
  await wait(900);
  ok(saves().length === 1 && saves()[0].args.period === 365, "AC-29 three quick taps give exactly one save, for the last chip");

  // AC-107 keyboard basics: chips are real buttons (Tab, Enter, Space work), focus stays on the chip, every select has a visible label
  held = []; p = page(o => held.push(o)); p.w.ptLoad();
  const ans = mk(90, 43); ans.filters.branches = [{ value: "Civil Lines", shared: true }];
  held[0].callback({ message: ans }); await wait(20);
  ok([...p.d.querySelectorAll('[role="radio"]')].every(b => b.tagName === "BUTTON" && b.type === "button"), "AC-107 every chip is a real button (keyboard reachable)");
  ok([...p.d.querySelectorAll("select")].length >= 1 && [...p.d.querySelectorAll("select")].every(s => s.closest("label") && s.closest("label").textContent.trim().length > 0), "AC-107 every filter has a visible label wrapping it");
  click(p, '[data-pt-per="30"]'); held[1].callback({ message: mk(30, 30) }); await wait(20);
  ok(p.d.activeElement && p.d.activeElement.getAttribute("data-pt-per") === "30", "AC-25 the tapped chip keeps focus after the answer");
  ok(/Showing 1 month/.test(p.d.getElementById("pt-live").textContent) && p.d.getElementById("pt-live").getAttribute("aria-live") === "polite", "AC-25/107 the polite live region reads the new chip");
  // sheet: focus moves in, returns on close
  const why = mk(90, 43); why.state = "not_shared"; why.reason = "few";
  held = []; p = page(o => held.push(o)); p.w.ptLoad(); held[0].callback({ message: why }); await wait(20);
  const btn = p.d.querySelector("[data-pt-why]"); btn.focus(); btn.click();
  ok(p.d.activeElement && p.d.activeElement.id === "pt-sheet-x" && p.d.getElementById("pt-sheet").getAttribute("role") === "dialog", "AC-107 the why sheet takes focus and is a dialog");
  p.d.dispatchEvent(new p.w.KeyboardEvent("keydown", { key: "Escape" }));
  ok(p.d.activeElement === btn, "AC-107 focus returns to the button that opened the sheet on Escape");

  // AC-74 / AC-106: no text under 12 px in the panel's own CSS or its markup (tokens from design_system.html)
  const ds = fs.readFileSync(path.join(APP, "templates/includes/design_system.html"), "utf8");
  const tok = {}; for (const m of ds.matchAll(/--(fs-[a-z0-9]+):(\d+)px/g)) tok[m[1]] = +m[2];
  const css = part.match(/<style>([\s\S]*?)<\/style>/)[1];
  const small = [];
  for (const rule of css.split("}")) {
    const m = rule.match(/font-size:var\(--(fs-[a-z0-9]+)\)/) || [];
    if (m[1] && tok[m[1]] < 12) small.push(rule.split("{")[0].trim() + " = " + tok[m[1]] + "px");
  }
  ok(small.length === 0, "AC-74/106 no text smaller than 12 px in the panel CSS" + (small.length ? " (found: " + small.join("; ") + ")" : ""));

  console.log(fails ? "FAILED " + fails : "all ok");
  process.exit(fails ? 1 : 0);
})();
