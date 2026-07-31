/* Load the real rendered page in jsdom, click the buttons, and assert the
   modal actually becomes visible. Catches handler/CSS-class mismatches that
   reading the source does not. */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const html = fs.readFileSync(process.argv[2], "utf8");
let pass = 0, fail = 0;
const ok  = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };

const dom = new JSDOM(html, {
  runScripts: "dangerously",
  pretendToBeVisual: true,
  url: "http://grace.localhost/hrms-employee",
  beforeParse(w) {
    // Stub the network and the Frappe JS bundle: we are exercising this page's
    // own DOM wiring, not the server.
    w.fetch = () => Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ message: [] }),
      text: () => Promise.resolve(""),
    });
    w.frappe = {
      csrf_token: "",
      call: () => Promise.resolve({ message: [] }),
      realtime: { on: () => {}, off: () => {} },
    };
    w._version_number = "0";
    w.confirm = () => true;
    w.alert = () => {};
  },
});

const { window } = dom;
const doc = window.document;

// Give inline scripts a tick to define their globals.
setTimeout(() => {
  // 1. Every onclick handler on the page resolves to a real function.
  const handlers = new Set();
  doc.querySelectorAll("[onclick]").forEach(el => {
    const m = /^\s*([A-Za-z_$][\w$]*)\s*\(/.exec(el.getAttribute("onclick"));
    if (m) handlers.add(m[1]);
  });
  const missing = [...handlers].filter(n => typeof window[n] !== "function");
  if (missing.length) bad("undefined onclick handlers: " + missing.join(", "));
  else ok(`all ${handlers.size} onclick handlers are defined`);

  // 2. Clicking a button that opens a modal must actually reveal it.
  const cases = [
    ["+ New KPI",       "pfOpenKpiModal",   "pf-kpi-modal"],
    ["+ New Cycle",     "pfOpenCycleModal", "pf-cycle-modal"],
    ["+ New Cascade",   "pfOpenCascadeModal", "pf-cascade-modal"],
    ["+ Assign KPI",    "pfOpenKpiModal",   "pf-kpi-modal"],
    ["New Goal",        "gpOpenCreateGoal", "gp-create-modal"],
  ];
  for (const [label, fn, modalId] of cases) {
    const modal = doc.getElementById(modalId);
    if (!modal) { bad(`${label}: #${modalId} missing from the page`); continue; }
    modal.className = modal.className.replace(/\bopen\b/g, "").trim();
    try {
      window[fn]();
    } catch (e) {
      bad(`${label}: ${fn}() threw ${e.message}`);
      continue;
    }
    const visible = window.getComputedStyle(modal).display;
    if (modal.classList.contains("open") && visible !== "none") {
      ok(`${label} → #${modalId} visible (display:${visible})`);
    } else {
      bad(`${label} → #${modalId} still hidden (classes="${modal.className}", display:${visible})`);
    }
    window.pfCloseModal ? window.pfCloseModal(modalId) : null;
  }

  // 3. Closing hides it again.
  const kpi = doc.getElementById("pf-kpi-modal");
  window.pfOpenKpiModal();
  window.pfCloseModal("pf-kpi-modal");
  if (window.getComputedStyle(kpi).display === "none") ok("pfCloseModal hides the modal again");
  else bad("pfCloseModal left the modal visible");

  // 4. Error text inside a modal is actually shown.
  window.pfOpenKpiModal();
  window.pfSubmitKpi();               // no name/target -> should surface an error
  const err = doc.getElementById("pf-kpi-error");
  if (err && err.textContent.trim() && window.getComputedStyle(err).display !== "none") {
    ok("validation error is visible: “" + err.textContent.trim() + "”");
  } else {
    bad(`validation error not visible (text="${err && err.textContent}", display=${err && window.getComputedStyle(err).display})`);
  }

  console.log(`### click test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
}, 300);
