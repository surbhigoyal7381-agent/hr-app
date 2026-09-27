/* Slice 051: the salary drawer, driven in a real DOM.
 *
 * This loads the assembled portal page in jsdom and calls `openPayslip` the way
 * a click does, with `frappe.call` answering the way the server answers. It
 * asserts what is on the screen, not what is in the source - a check that read
 * portal.js for the string "Exact amount" would pass while the line sat inside
 * a branch that never runs.
 *
 * Four things are proved here, and each one was a decision:
 *
 *   1. Both pay figures appear when payroll's rounding moved the number, and
 *      the exact line does NOT appear when the two agree. 555 of 800 PP
 *      Jewellers slips print a net the bank does not pay; the old screen showed
 *      one figure and never said which.
 *   2. The year-so-far line appears only when payroll worked one out. A
 *      confident zero is worse than no line.
 *   3. A "Why?" control sits on a deduction the server can explain, and on
 *      nothing else - not on an earning, not on a deduction with no link.
 *   4. The explanation is rendered as the server sent it, including the
 *      sentence saying a correction does not undo the deduction.
 *
 * Run by scripts/run_dom_tests.js with the page as argv[2].
 */
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };

/* A payslip whose rounded total and exact net disagree by 39 paise - the shape
   that made this slice necessary. One deduction carries an `additional_salary`
   link, one does not; the earning carries one too, to prove the Why? control
   follows the section and not merely the key. */
const SLIP = {
  name: "SAL-0001",
  start_date: "2026-10-01",
  end_date: "2026-10-31",
  currency: "INR",
  total_working_days: 27,
  payment_days: 25,
  leave_without_pay: 2,
  gross_pay: 52000,
  total_deduction: 3765.39,
  net_pay: 48234.61,
  rounded_total: 48235,
  year_to_date: 482350,
  gross_year_to_date: 560000,
  earnings: [{ component: "Basic", amount: 52000, additional_salary: "ADS-EARN" }],
  deductions: [
    { component: "Attendance Deduction", amount: 1240, additional_salary: "ADS-0001" },
    { component: "Professional Tax", amount: 2525.39 },
  ],
};

const WHY = {
  how_it_was_decided: "SERVER-SENTENCE-HOW",
  week_start: "2026-10-12",
  week_end: "2026-10-18",
  violations: [
    { attendance_date: "2026-10-14", violation_type: "Late", actual_time: "09:48", minutes: 18, counted: false },
    { attendance_date: "2026-10-21", violation_type: "Late", actual_time: "10:05", minutes: 35, counted: true },
  ],
  rounded_up: false,
  taken_from_leave: [],
  if_a_day_is_wrong: "SERVER-SENTENCE-WRONG",
  what_a_correction_does_not_do: "SERVER-SENTENCE-CORRECTION",
  getting_it_put_back: "SERVER-SENTENCE-PUTBACK",
  who_to_go_to: "SERVER-SENTENCE-WHO",
};

/* Every server call this test allows, so an unexpected one is visible rather
   than silently answered. Showing an explanation must WRITE nothing. */
const calls = [];

const dom = new JSDOM(html, {
  runScripts: "dangerously",
  pretendToBeVisual: true,
  url: "http://ppj.localhost/hrms-employee",
  beforeParse(w) {
    w.fetch = () => Promise.resolve({
      ok: true, status: 200,
      json: () => Promise.resolve({ message: [] }),
      text: () => Promise.resolve(""),
    });
    w.frappe = {
      csrf_token: "",
      /* The real `api()` helper passes `callback`, so this stub must call it -
         a stub that only returns a promise leaves `renderPayslip` unreached and
         every assertion below vacuously green. */
      call: (opts) => {
        calls.push(opts.method);
        /* Only the payslip call is answered. The page's own start-up calls are
           left hanging, exactly as the other DOM tests leave them - answering
           them with an empty list makes the Home loader throw on a shape it
           never asked for, and that noise buries a real failure here. */
        if (/get_payslip$/.test(opts.method)) { opts.callback({ message: SLIP }); }
        return Promise.resolve({ message: [] });
      },
      realtime: { on: () => {}, off: () => {} },
    };
    w._version_number = "0";
    w.confirm = () => true;
    w.alert = () => {};
  },
});

const { window } = dom;
const doc = window.document;

function body() { return doc.getElementById("ps-body").innerHTML; }

setTimeout(() => {
  if (typeof window.openPayslip !== "function") {
    bad("openPayslip is not defined - the page did not load its script");
    return done();
  }

  /* ── 1. both figures ─────────────────────────────────────────────────── */
  window.openPayslip("SAL-0001");
  const paid = body();

  if (/48,235/.test(paid)) ok("the rounded figure - what the bank paid - is the big number");
  else bad("the rounded figure is missing: " + paid.slice(0, 200));

  if (/Exact amount on the payslip/.test(paid) && /48,234\.61/.test(paid)) {
    ok("the exact net is shown beside it, to the paisa");
  } else {
    bad("the exact net is not shown - the 39 paise gap is still hidden");
  }

  /* ── 2. and NOT shown when the two agree ─────────────────────────────── */
  const level = Object.assign({}, SLIP, { net_pay: 48235, rounded_total: 48235 });
  window.frappe.call = (opts) => {
    calls.push(opts.method);
    if (/get_payslip$/.test(opts.method)) { opts.callback({ message: level }); }
    return Promise.resolve({ message: [] });
  };
  window.openPayslip("SAL-0001");
  if (!/Exact amount on the payslip/.test(body())) {
    ok("no exact line when the two figures agree");
  } else {
    bad("a second identical figure is drawn, which reads as a fault");
  }

  /* ── 3. the year so far ──────────────────────────────────────────────── */
  if (/This financial year so far/.test(paid) && /4,82,350/.test(paid)) {
    ok("the year so far is shown, read off the slip");
  } else {
    bad("the year-so-far line is missing");
  }

  const noYear = Object.assign({}, SLIP, { year_to_date: 0, gross_year_to_date: 0 });
  window.frappe.call = (opts) => {
    calls.push(opts.method);
    if (/get_payslip$/.test(opts.method)) { opts.callback({ message: noYear }); }
    return Promise.resolve({ message: [] });
  };
  window.openPayslip("SAL-0001");
  if (!/This financial year so far/.test(body())) {
    ok("no year line when payroll has not worked one out");
  } else {
    bad("a confident zero is drawn for the year so far");
  }

  /* ── 4. the Why? control sits only where the server can answer ───────── */
  window.frappe.call = (opts) => {
    calls.push(opts.method);
    if (/get_payslip$/.test(opts.method)) { opts.callback({ message: SLIP }); }
    return Promise.resolve({ message: [] });
  };
  window.openPayslip("SAL-0001");

  const whyButtons = [...doc.querySelectorAll("#ps-body button")]
    .filter(b => /Why\?/.test(b.textContent));
  if (whyButtons.length === 1) ok("exactly one Why? control, on the explainable deduction");
  else bad(`expected 1 Why? control, found ${whyButtons.length}`);

  if (whyButtons.length && /ADS-0001/.test(whyButtons[0].getAttribute("onclick"))) {
    ok("it carries the server's link, not a name the client made up");
  } else {
    bad("the Why? control does not carry the server's additional_salary link");
  }

  const rows = [...doc.querySelectorAll("#ps-body tr")];
  const basicRow = rows.find(r => /Basic/.test(r.textContent));
  if (basicRow && !/Why\?/.test(basicRow.textContent)) ok("an earning gets no Why?");
  else bad("a Why? control appeared on an earning");

  const ptRow = rows.find(r => /Professional Tax/.test(r.textContent));
  if (ptRow && !/Why\?/.test(ptRow.textContent)) ok("a deduction with no link gets no Why?");
  else bad("a Why? control appeared on a deduction the server cannot explain");

  /* ── 5. the explanation, rendered as the server sent it ──────────────── */
  const asked = [];
  window.gpFetch = (method, args) => {
    asked.push({ method, args });
    return Promise.resolve(WHY);
  };
  const before = calls.length;
  window.psWhy("ADS-0001");

  setTimeout(() => {
    const shown = body();

    if (asked.length === 1 &&
        asked[0].method === "alvoraa_portal.pay_api.get_deduction_explanation" &&
        asked[0].args.additional_salary === "ADS-0001") {
      ok("it asks the explanation endpoint, with the link it was given");
    } else {
      bad("wrong call: " + JSON.stringify(asked));
    }

    const sentences = ["SERVER-SENTENCE-HOW", "SERVER-SENTENCE-WRONG",
                       "SERVER-SENTENCE-CORRECTION", "SERVER-SENTENCE-PUTBACK",
                       "SERVER-SENTENCE-WHO"];
    const lost = sentences.filter(s => !shown.includes(s));
    if (!lost.length) ok("every sentence the server sent is on the screen, unaltered");
    else bad("the screen dropped or rewrote: " + lost.join(", "));

    if (/Counted/.test(shown) && /Free/.test(shown)) {
      ok("each day says whether it was counted or free");
    } else {
      bad("the week's days do not say which ones counted");
    }

    if (calls.length === before) ok("showing the explanation wrote nothing and called nothing else");
    else bad("an extra server call happened while showing the explanation");

    /* ── 6. back, without asking again ─────────────────────────────────── */
    const callsBeforeBack = calls.length;
    window.psBack();
    if (/Take-home pay/.test(body())) ok("Back returns to the payslip");
    else bad("Back did not return to the payslip");
    if (calls.length === callsBeforeBack) ok("Back asks the server for nothing");
    else bad("Back made a second call for a payslip already in hand");

    /* ── 7. hand-entered: the sentence, and no week ────────────────────── */
    window.gpFetch = () => Promise.resolve({ hand_entered: true });
    window.psWhy("ADS-0001");
    setTimeout(() => {
      const hand = body();
      if (/entered by hand/.test(hand)) ok("a hand-entered component says so");
      else bad("a hand-entered component draws no explanation");
      if (!/The week/.test(hand)) ok("and draws no empty week");
      else bad("an empty week is drawn, which reads as an accusation about no days");
      done();
    }, 0);
  }, 0);
}, 0);

function done() {
  console.log(`\n  ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
}
