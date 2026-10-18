/* Which endpoint "Ask HR to fix this day" sends to.

   THE BUG THIS PINS, 18 Oct 2026. `can_request` was widened so the button
   appears on a DIRECT REPORT's day, and the handler was left calling
   `raise_correction` - the endpoint that raises for the CALLER and refuses to
   take anybody else's name, deliberately, so a field naming somebody else
   cannot rewrite their attendance. Pressing it returned 403, and the error was
   invisible behind a dialog, so it looked like a dead button.

   A manager's on-behalf request is `raise_for_report`: it checks the reporting
   line and stamps who vouched for the day.

   Nothing in the suite noticed. `test_browser_call_args_045` checks the shape
   of the arguments a call sends, not whether the right method was chosen for
   the situation - and the situation is the whole bug. */
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok  = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };

const ME = "HR-EMP-00003";
const REPORT = "HR-EMP-00005";

const calls = [];
function reply(url, body) {
  const m = /attendance_correction\.(\w+)|hr_api\.(\w+)/.exec(url) || [];
  const fn = m[1] || m[2] || "";
  calls.push({ fn, body });
  if (fn === "reasons")
    return [{ value: "Marked Absent by Mistake", help: "The day shows as absent.",
              becomes: "Present" }];
  if (fn === "raise_correction" || fn === "raise_for_report")
    return { name: "ATT-REQ-0001" };
  if (fn === "get_portal_context")
    return { employee_id: ME, employee_name: "Rahul", is_manager: true,
             team: [], dashboard: {}, cycle: null };
  if (fn === "get_available_features") return {};
  if (fn === "get_checkin_status")
    return { no_employee: 0, employee: { name: ME, employee_name: "Rahul Sharma",
             designation: "Regional Manager", department: "Sales" },
             checked_in: 0, last_action: null, todays_checkins: [] };
  return [];
}

const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://grace.localhost/hrms-employee",
  beforeParse(w) {
    w.fetch = (url, opts) => Promise.resolve({
      ok: true, status: 200,
      json: () => Promise.resolve({ message: reply(String(url), opts && opts.body) }),
      text: () => Promise.resolve(""),
    });
    const call = (o) => {
      const out = reply(String(o.method || ""), JSON.stringify(o.args || {}));
      setTimeout(() => { o.callback && o.callback({ message: out }); }, 0);
      return Promise.resolve({ message: out });
    };
    w.frappe = { call, csrf_token: "x", boot: {}, ui: {}, _messages: {} };
  },
});

const { window } = dom;
const doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));

/* The form reads its two fields straight from the DOM, so they have to exist
   for either branch to send anything at all. */
function putForm(reason) {
  const host = doc.createElement("div");
  host.innerHTML =
    '<select id="ac-reason"><option value="' + reason + '" selected>r</option></select>' +
    '<textarea id="ac-explain">Please regularise her attendance.</textarea>';
  doc.body.appendChild(host);
}

(async () => {
  await settle(400);

  if (typeof window.acSubmit !== "function") {
    bad("acSubmit is not reachable from the page");
    console.log(`### correction DOM test: ${pass} passed, ${fail} failed`);
    process.exit(1);
  }
  ok("acSubmit is reachable from the page");

  putForm("Marked Absent by Mistake");

  // ── Somebody else's month: the manager's endpoint ──────────────────
  window.acState.employee = REPORT;
  window.acState.data = { employee: REPORT, employee_name: "Neha Kumar",
                          is_self: false, can_request: true, days: [] };
  calls.length = 0;
  window.acSubmit("2026-10-14");
  await settle(250);

  const onBehalf = calls.find(c => c.fn === "raise_for_report");
  const wrongOne = calls.find(c => c.fn === "raise_correction");

  onBehalf ? ok("a report's day is sent to raise_for_report")
           : bad("raise_for_report was never called for a report's day");
  wrongOne ? bad("raise_correction was called for somebody else's day - "
                 + "that endpoint raises for the CALLER and returns 403")
           : ok("raise_correction is not used for somebody else's day");

  if (onBehalf) {
    const sent = JSON.parse(onBehalf.body || "{}");
    const args = sent.args || sent;
    (args.employee === REPORT)
      ? ok("the request names the employee it is for")
      : bad("employee not sent, or wrong: " + JSON.stringify(args));
    (args.from_date === "2026-10-14")
      ? ok("the request carries the day being corrected")
      : bad("from_date not sent, or wrong: " + JSON.stringify(args));
  }

  // ── My own month: the ordinary endpoint, unchanged ─────────────────
  // Narrowing what an employee may ask about their OWN attendance would be a
  // regression, so this half is pinned too.
  putForm("Marked Absent by Mistake");
  window.acState.employee = null;
  window.acState.data = { employee: ME, employee_name: "Rahul Sharma",
                          is_self: true, can_request: true, days: [] };
  calls.length = 0;
  window.acSubmit("2026-10-14");
  await settle(250);

  calls.find(c => c.fn === "raise_correction")
    ? ok("my own day still goes to raise_correction")
    : bad("my own day no longer reaches raise_correction");
  calls.find(c => c.fn === "raise_for_report")
    ? bad("my own day was sent on-behalf, which names me as my own manager")
    : ok("my own day is not sent on-behalf");

  console.log(`### correction DOM test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
