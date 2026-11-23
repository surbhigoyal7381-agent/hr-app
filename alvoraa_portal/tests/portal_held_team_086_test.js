/* Slice 086: the Held view on the Whole team page, driven the way a manager drives it.

   Pins what the page SENDS (the 28 Oct 2026 rule): exactly five keys per row, the kind
   the page worked out, the reason as typed, and nothing when a guard stops it. Also pins
   that a day with no reason is not sent, that a refusal keeps what was typed, and that
   nothing typed is written to browser storage (PRIV-4). */

const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok  = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };
const check = (c, m) => (c ? ok(m) : bad(m));

const ME = "HR-EMP-00003";
const calls = [];
let SEND_ANSWER = null;       // what send_held answers
const SHIFT = { start: "09:00", end: "18:00" };
const ROWS = [
  { employee: "HR-EMP-00011", employee_name: "Sunita Devi", date: "2026-11-20", shift: SHIFT,
    punches: [{ time: "09:02", m: 542, source: "Machine" }], single_is_out: false },
  { employee: "HR-EMP-00012", employee_name: "Ramesh Kumar", date: "2026-11-20", shift: SHIFT,
    punches: [{ time: "09:00", m: 540, source: "Machine" }, { time: "13:00", m: 780, source: "Machine" },
              { time: "14:00", m: 840, source: "Machine" }], single_is_out: false },
];

function reply(url, body) {
  const m = /held_team\.(\w+)/.exec(url) || [];
  calls.push({ fn: m[1] || "", body });
  if (m[1] === "held_days")
    return { nobody: false, hold_on: true, day: "2026-11-20", days: [{ date: "2026-11-20", count: 2 }],
             total: 2, start: 0, page_length: 50, rows: ROWS };
  if (m[1] === "send_held") return SEND_ANSWER;
  return [];
}

const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://dtc.localhost/hrms-employee",
  beforeParse(w) {
    w.fetch = (url, opts) => Promise.resolve({ ok: true, status: 200,
      json: () => Promise.resolve({ message: reply(String(url), opts && opts.body) }),
      text: () => Promise.resolve("") });
    w.frappe = { call: () => Promise.resolve({ message: [] }), csrf_token: "x", boot: { user: { full_name: "Mgr" } },
                 session: { user: "mgr@example.com" }, ui: {}, _messages: {} };
  },
});
const { window } = dom;
const doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));
const sent = fn => calls.filter(c => c.fn === fn);
const type = (id, v) => { const el = doc.getElementById(id); el.value = v; el.dispatchEvent(new window.Event("input", { bubbles: true })); };
const K1 = "HR-EMP-00011|2026-11-20";

(async function run() {
  await settle(60);
  for (const id of ["tr-chips", "tr-body", "tr-pager"]) {
    const d = doc.createElement("div"); d.id = id; doc.body.appendChild(d);
  }
  window.trSet("only", "held");
  await settle(40);

  check(sent("held_days").length === 1, "opening the Held view asks the server once for the list");
  check(doc.querySelectorAll(".hdl-row").length === 2, "one block per held day");
  check(!doc.getElementById("hdl-bar-host"), "no send bar until a day is ready");
  check(/What time did Sunita leave\?/.test(doc.body.textContent), "a one-punch day (an arrival) asks when she left, by first name");

  type("hdl-t-" + K1, "18:30");
  check(!doc.getElementById("hdl-send"), "a time with no reason is not ready, so no Send button");
  type("hdl-r-" + K1, "   ");
  check(!doc.getElementById("hdl-send"), "a reason of spaces is not a reason");
  type("hdl-r-" + K1, "Forgot to scan out");
  const bar = doc.getElementById("hdl-send");
  check(!!bar && /Send 1 to HR/.test(bar.textContent), "time and reason make the day ready: Send 1 to HR");
  check(doc.getElementById("hdl-bar-host").parentNode === doc.body, "the send bar lives on <body>, not in a panel");
  check(sent("send_held").length === 0, "typing sends nothing");

  window.hdlAsk();
  check(!!doc.getElementById("hdl-go") && /Forgot to scan out/.test(doc.getElementById("pfx-sheet").textContent),
        "the confirm shows the reason that will be sent");
  window.hdlClose();
  check(sent("send_held").length === 0, "Go back sends nothing");

  /* A refusal keeps what was typed and says why. */
  SEND_ANSWER = { sent: 0, not_sent: 1, results: [{ employee: "HR-EMP-00011", date: "2026-11-20", ok: false,
                  sentence: "Not sent. 18:30 fits as a leaving, not an arrival." }] };
  window.hdlAsk();
  doc.getElementById("hdl-go").click();
  await settle(60);
  const rows = JSON.parse(JSON.parse(sent("send_held")[0].body).rows);
  const row = rows[0];
  check(Object.keys(row).sort().join() === "date,employee,in_or_out,reason,time", "a row carries exactly five keys");
  check(row.employee === "HR-EMP-00011" && row.date === "2026-11-20" && row.time === "18:30"
        && row.reason === "Forgot to scan out", "the row carries what the manager typed");
  check(row.in_or_out === "OUT", "one punch at 09:02 (an arrival) means the missing one is OUT");
  check(rows.length === 1, "only the ready day went, not the untouched one");
  check(/not sent|Nothing sent/i.test(doc.body.textContent) && /fits as a leaving/.test(doc.body.textContent),
        "the server's sentence is shown on the day");
  check(doc.getElementById("hdl-r-" + K1) && doc.getElementById("hdl-r-" + K1).value === "Forgot to scan out",
        "what was typed is still there after a refusal");

  let stored = 0;
  try { stored = window.localStorage.length + window.sessionStorage.length; } catch (e) { stored = 0; }
  check(stored === 0, "nothing typed is written to browser storage");

  /* Sent: the answer clears the day's typing. */
  SEND_ANSWER = { sent: 1, not_sent: 0, results: [{ employee: "HR-EMP-00011", date: "2026-11-20", ok: true, request: "ATT-REQ-1" }] };
  window.hdlAsk();
  doc.getElementById("hdl-go").click();
  await settle(60);
  check(sent("send_held").length === 2 && /1 of 1 sent to HR/.test(doc.body.textContent), "an accepted send says so");
  check(sent("held_days").length >= 3, "after a send the list is asked for again, not guessed");

  console.log("### 086 held view DOM test: " + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})();
