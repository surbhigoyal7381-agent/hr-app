/* Slice 066: a grooming call that gets no answer says "no answer, try again".

   Slice 070 (ALV-217) changed what a lost portal call looks like: gpFetch now
   rejects with an Error carrying `kind` (offline, network, timeout, server,
   refused), never fetch's raw TypeError. gmIsNet used to look for the
   TypeError, so a lost undo read as a refusal ("the undo window has closed")
   and a lost Today card just vanished. This pins the fix.

   Run: node alvoraa_portal/tests/portal_grooming_066_test.js alvoraa_portal/alvoraa_portal/www/hrms-employee.html */
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };
const eq = (got, want, m) => (got === want ? ok(m) : bad(m + ": got <" + got + "> want <" + want + ">"));
const has = (text, want, m) => (String(text).indexOf(want) >= 0 ? ok(m) : bad(m + ": missing <" + want + "> in <" + String(text).slice(0, 200) + ">"));

/* {ok: value} - HTTP 200 · {status, body} - an error answer · "drop" - the
   connection drops (fetch rejects) · "never" - no answer at all. */
let ROUTES = {
  get_portal_context: {ok: {employee_id: "E1", employee_name: "Ravi", dashboard: {}, cycle: null}},
  get_checkin_status: {ok: {no_employee: 1}},
};
let ONLINE = true;
const method = s => String(s).split(".").pop();

const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://grace.localhost/hrms-employee",
  beforeParse(w) {
    Object.defineProperty(w.navigator, "onLine", {configurable: true, get: () => ONLINE});
    w.fetch = (url) => {
      const h = ROUTES[method(url)] || {ok: []};
      if (h === "never") return new Promise(() => {});
      if (h === "drop") return Promise.reject(new TypeError("Failed to fetch"));
      const status = h.status || 200;
      const body = h.ok !== undefined ? {message: h.ok} : h.body;
      return Promise.resolve({ok: status === 200, status, json: () => Promise.resolve(body)});
    };
    const call = (o) => { const xhr = {status: 0}; setTimeout(() => o.always && o.always({}), 0); return xhr; };
    w.frappe = {call, csrf_token: "x", boot: {}, ui: {}, _messages: {}, utils: {escape_html: s => s},
                msgprint: () => {}};
  },
});
const {window} = dom, doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));
const alerts = [];
window.alert = m => alerts.push(m);

const row = () => ({employee: "E2", first: "Kiran", employee_name: "Kiran K",
                    mark: {name: "GM-1", mine: true, has_login: true, reason: "Not in uniform"}});
async function undo() {
  alerts.length = 0;
  window.gmState.today = {show: true, day: "Mon 26 Oct", rows: [row()], not_in: [], count: 1};
  await window.gmUndo(0);
  return window.gmState.today.rows[0].mark;
}

(async () => {
  await settle(400);
  if (typeof window.gmIsNet !== "function" || typeof window.gmUndo !== "function") {
    bad("the grooming functions are not on the page"); process.exit(1);
  }

  // ── what gmIsNet calls "no answer" ───────────────────────────────────────
  for (const kind of ["offline", "network", "timeout"]) eq(window.gmIsNet({kind}), true, kind + " is no answer");
  for (const kind of ["refused", "server"]) eq(window.gmIsNet({kind}), false, kind + " is the office answering");

  // ── a lost undo: try again, never "the window has closed" ────────────────
  ROUTES.undo = "drop";
  let m = await undo();
  has(alerts[0], "Check your connection and try again", "dropped connection: the undo says try again");
  eq(!!m.locked, false, "dropped connection: the undo is not locked as if refused");

  ROUTES.undo = {ok: {}};
  ONLINE = false;
  m = await undo();
  ONLINE = true;
  has(alerts[0], "Check your connection and try again", "offline: the undo says try again");
  eq(!!m.locked, false, "offline: the undo is not locked");

  ROUTES.undo = {status: 417, body: {exc_type: "ValidationError",
    _server_messages: JSON.stringify([JSON.stringify({message: "Too late to undo."})])}};
  m = await undo();
  eq(alerts.length, 0, "a refusal shows no connection alert");
  eq(m.locked, true, "a refusal locks the undo (the window has closed)");

  // ── the Today card: a load with no answer says so, with Try again ────────
  window.CALL_LIMIT_MS = 200;
  ROUTES.today = "never";
  await window.gmToday();
  const el = doc.getElementById("gm-today");
  has(el.textContent, "did not answer", "timeout: the Today card says the office did not answer");
  eq(!!el.querySelector(".fail button"), true, "timeout: with a Try again button");

  ROUTES.today = {status: 403, body: {exc_type: "PermissionError",
    _server_messages: JSON.stringify([JSON.stringify({message: "Not permitted"})])}};
  await window.gmToday();
  eq(el.innerHTML, "", "a refusal still shows no card");

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
