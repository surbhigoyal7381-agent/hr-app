/* Slice 070 (ALV-217): readable and honest on a cheap phone.

   The pin test for the slice: if a merge drops the 15-second end, the honest
   send words, the check before a resend, the one date format or the weekly
   off label, a check here fails by name.

   The stubs behave like the real page, not like a kinder one. This page loads
   website.js's frappe.call: it calls `always` FIRST and `callback` only on an
   HTTP 200, and NEVER calls `error` (slice 034's lesson). gpFetch uses fetch,
   so a lost connection is a rejected fetch.

   Run: node alvoraa_portal/tests/portal_phone_070_test.js alvoraa_portal/alvoraa_portal/www/hrms-employee.html */
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };
const eq = (got, want, m) => (got === want ? ok(m) : bad(m + ": got <" + got + "> want <" + want + ">"));
const has = (text, want, m) => (String(text).indexOf(want) >= 0 ? ok(m) : bad(m + ": missing <" + want + "> in <" + String(text).slice(0, 200) + ">"));
const hasNot = (text, want, m) => (String(text).indexOf(want) < 0 ? ok(m) : bad(m + ": should not show <" + want + ">"));

/* What the "server" does with each method. A handler returns one of:
     {ok: value}                    - HTTP 200
     {status: 417|500, body: {...}} - an error answer
     "drop"                         - the connection drops (fetch rejects; frappe.call gets status 0)
     {hold: ms, then: <handler>}    - answer after `ms`
     "never"                        - no answer at all */
let ROUTES = {
  get_portal_context: {ok: {employee_id: "E1", employee_name: "Rahul Kumar", dashboard: {}, cycle: null}},
  get_checkin_status: {ok: {no_employee: 1}},
};
let ONLINE = true;
const sent = [];        // every method that LEFT the phone, in order
const msgprints = [];   // every Frappe pop-up
const method = s => String(s).split(".").pop();
const answer = (fn, hnd) => (typeof hnd === "function" ? hnd() : hnd) || {ok: []};

const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://grace.localhost/hrms-employee",
  beforeParse(w) {
    Object.defineProperty(w.navigator, "onLine", {configurable: true, get: () => ONLINE});
    const respond = (fn) => {
      const h = answer(fn, ROUTES[fn]);
      if (h === "never") return new Promise(() => {});
      if (h === "drop") return Promise.reject(new TypeError("Failed to fetch"));
      if (h.hold) return new Promise(r => setTimeout(r, h.hold)).then(() => respondWith(h.then));
      return respondWith(h);
    };
    const respondWith = (h) => {
      if (h === "drop") return Promise.reject(new TypeError("Failed to fetch"));
      const status = h.status || 200;
      const body = h.ok !== undefined ? {message: h.ok} : h.body;
      return Promise.resolve({ok: status === 200, status, json: () => Promise.resolve(body), text: () => Promise.resolve("")});
    };
    w.fetch = (url) => { const fn = method(url); sent.push(fn); return respond(fn); };
    /* website.js's frappe.call: always() first, then callback() on a 200 only;
       server messages pop up unless `error_msg` is given. */
    const call = (o) => {
      const fn = method(o.method);
      sent.push(fn);
      const xhr = {status: 0};
      const finish = (h) => {
        if (h === "never") return;
        if (h === "drop") { xhr.status = 0; o.always && o.always({}); return; }
        if (h.hold) { setTimeout(() => finish(h.then), h.hold); return; }
        xhr.status = h.status || 200;
        const data = h.ok !== undefined ? {message: h.ok} : (h.body || {});
        if (data._server_messages && !o.error_msg) msgprints.push(data._server_messages);
        o.always && o.always(data);
        if (xhr.status === 200 && o.callback) o.callback(data);
      };
      setTimeout(() => finish(answer(fn, ROUTES[fn])), 0);
      return xhr;
    };
    w.frappe = {call, csrf_token: "x", boot: {}, ui: {}, _messages: {}, utils: {escape_html: s => s},
                msgprint: (m) => msgprints.push(m)};
  },
});
const {window} = dom, doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));
const txt = id => (doc.getElementById(id) || {}).textContent || "";
const count = (fn) => sent.filter(s => s === fn).length;
const serverSays = (m) => JSON.stringify([JSON.stringify({message: m})]);

(async () => {
  await settle(400);
  if (typeof window.fmtDate !== "function" || typeof window.lsSend !== "function") {
    bad("the 070 functions are not on the page"); process.exit(1);
  }

  // ── US-3: one date format ─────────────────────────────────────────────
  eq(window.fmtDate("2026-11-06"), "6 Nov 2026", "AC-11: 6 Nov 2026");
  eq(window.fmtDate("2026-09-01"), "1 Sep 2026", "AC-11: September is Sep, never Sept");
  eq(window.fmtDate("2026-11-06 10:30:00"), "6 Nov 2026", "AC-11: a date-time keeps its date");
  eq(window.fmtDate(""), "", "AC-11: empty stays empty");
  eq(window.fmtDate(null), "", "AC-11: null stays empty");
  eq(window.dateInWords("2026-11-06"), "Friday, 6 Nov 2026", "AC-15: the date in words");
  eq(window.lpShort("2026-10-01"), "1 Oct", "AC-16: day labels have no leading zero");
  /* AC-12: built from the ISO parts, so no time zone can move the day. */
  const src = window.fmtDate.toString();
  hasNot(src, "toLocaleDateString", "AC-12: fmtDate does not use the browser's locale or zone");

  // ── US-2: weekly off ──────────────────────────────────────────────────
  const day = {date: "2026-10-01", weekday: "Thursday", holiday: "Thursday", weekly_off: true, future: false,
               state: "holiday", attendance: null, in_time: null, out_time: null, hours: null, expected_hours: null,
               short_by: 0, is_late: false, missing_punch: false, request: null, shift_starts: null};
  window.acState.open = null;
  has(window.acRow(day), ">Weekly off<", "AC-8: a weekly off says Weekly off");
  hasNot(window.acRow(day), ">Holiday<", "AC-8: no chip reads Holiday");
  has(window.acRow(Object.assign({}, day, {date: "2026-10-02", holiday: "Gandhi Jayanti", weekly_off: false})),
      ">Gandhi Jayanti<", "AC-9: a named holiday keeps its name");
  const marked = window.acRow(Object.assign({}, day, {holiday: "<b>Diwali</b><img src=x onerror=alert(1)>", weekly_off: false}));
  has(marked, ">Diwali<", "AC-9: markup in a holiday name shows as plain text");
  hasNot(marked, "<img", "AC-9: and none of it runs");
  const worked = window.acRow(Object.assign({}, day, {date: "2026-10-05", weekday: "Monday", holiday: null, weekly_off: false,
    state: "present", attendance: "ATT-1", status: "Present", in_time: "09:28", out_time: "18:34", hours: 9.1, is_late: false}));
  has(worked, "In 09:28 &middot; Out 18:34 &middot; 9.1h worked &middot; On time", "AC-52: the phone line 2");
  has(worked, 'aria-label="Monday, 5 Oct 2026, open the day"', "AC-52: an openable day is a named button");

  // ── US-5 / US-6: sending a leave request ──────────────────────────────
  const btn = () => doc.getElementById("la-submit-btn");
  const fresh = () => {
    window.lsReset();
    window.LP.subject = null;
    btn().disabled = false; btn().style.display = ""; btn().textContent = "Submit Application";
    sent.length = 0;
  };
  const ARGS = {leave_type: "Earned Leave", from_date: "2026-11-06", to_date: "2026-11-07", half_day: 0,
                half_day_date: null, reason: "Family function"};
  let successes = 0;
  const send = () => window.lsSend(ARGS, () => { btn().textContent = "Submit Application"; }, () => { successes++; });

  // AC-26: no signal - nothing leaves the phone, the form says so, Try again.
  fresh(); ONLINE = false;
  send(); await settle(20);
  eq(count("apply_leave"), 0, "AC-26: with no signal nothing is sent");
  has(txt("la-send-fail"), "We could not reach the office. Nothing was sent.", "AC-26: the no-signal words");
  has(txt("la-send-fail"), "Your details are still here. When you have signal, tap Try again.", "AC-26: the second line");
  eq(btn().textContent, "Try again", "AC-26: the button is Try again");
  eq(doc.activeElement, btn(), "AC-37: focus stays on the button");
  eq(doc.getElementById("la-send-fail").getAttribute("role"), "alert", "AC-37: the message is an alert");
  send(); await settle(20);
  has(txt("la-send-fail"), "Still no signal. Nothing was sent.", "AC-31: still offline");
  // AC-26 then Try again with signal: it sends straight away, no check.
  ONLINE = true; ROUTES.apply_leave = {ok: {name: "LA-1"}};
  send(); await settle(30);
  eq(count("get_leave_summary"), 0, "AC-26: nothing had left the phone, so no check first");
  eq(count("apply_leave"), 1, "AC-26: one send once there is signal");
  eq(successes, 1, "AC-25: success shows");

  // AC-38: a double tap sends once.
  fresh(); successes = 0; ROUTES.apply_leave = {hold: 50, then: {ok: {name: "LA-2"}}};
  send(); send(); await settle(10);
  eq(btn().textContent, "Sending…", "AC-25: Sending… while it goes");
  eq(btn().disabled, true, "SEC-1: the button is locked while sending");
  await settle(100);
  eq(count("apply_leave"), 1, "AC-38: a double tap sends once");

  // AC-32 / SEC-5: a refusal shows the server's own words at the top, and is never resent.
  fresh(); successes = 0;
  ROUTES.apply_leave = {status: 417, body: {exc_type: "ValidationError", _server_messages: serverSays("Leave dates overlap")}};
  send(); await settle(30);
  has(txt("la-error"), "Leave dates overlap", "AC-32 / AC-46: the server's words, unchanged");
  hasNot(txt("la-send-fail"), "may have gone through", "AC-32: a refusal is never 'may have gone through'");
  eq(btn().textContent, "Submit Application", "AC-32: the button comes back to Submit Application");
  eq(count("apply_leave"), 1, "SEC-5: no resend");

  // SEC-4 / AC-45: a 500 carrying a traceback shows only the fixed sentence.
  fresh();
  ROUTES.apply_leave = {status: 500, body: {exc_type: "OperationalError",
    exc: JSON.stringify(["Traceback (most recent call last):\n pymysql.err.OperationalError: tabLeave Application"]),
    _server_messages: serverSays("DocType Alvoraa Payroll Rule Set not found")}};
  send(); await settle(30);
  hasNot(doc.body.textContent, "Traceback", "AC-45: no traceback on the page");
  hasNot(doc.body.textContent, "tabLeave Application", "AC-45: no table name on the page");
  hasNot(doc.body.textContent, "Alvoraa Payroll Rule Set", "AC-45: a 5xx's own text is not shown either");
  has(txt("la-send-fail"), "No answer from the office. It may have gone through.", "AC-27: a 5xx after sending may have gone through");

  // AC-28 / AC-39: the answer is lost, Try again checks, finds it, and sends nothing new.
  fresh(); successes = 0; ROUTES.apply_leave = "drop";
  send(); await settle(30);
  has(txt("la-send-fail"), "No answer from the office. It may have gone through.", "AC-27: a dropped connection");
  has(txt("la-send-fail"), "Tap Try again. We check first, so it is never sent twice.", "AC-27: the second line");
  ROUTES.get_leave_summary = {ok: {applications: [{leave_type: "Earned Leave", from_date: "2026-11-06",
                                                   to_date: "2026-11-07", status: "Open"}]}};
  ROUTES.apply_leave = {ok: {name: "LA-3"}};
  send(); await settle(10);
  eq(btn().textContent, "Checking…", "AC-28: Checking… while it looks");
  await settle(40);
  eq(count("get_leave_summary"), 1, "AC-28: one check");
  eq(count("apply_leave"), 1, "AC-28 / AC-39: found, so nothing is sent again (one send in all)");
  eq(successes, 1, "AC-28: the same success as a normal send");

  // AC-29: the check finds nothing - one send.
  fresh(); successes = 0; ROUTES.apply_leave = "drop";
  send(); await settle(30);
  ROUTES.get_leave_summary = {ok: {applications: [{leave_type: "Earned Leave", from_date: "2026-11-06",
                                                   to_date: "2026-11-07", status: "Cancelled"}]}};
  ROUTES.apply_leave = {ok: {name: "LA-4"}};
  send(); await settle(60);
  eq(count("apply_leave"), 2, "AC-29: a cancelled one is not a match - sent once more");
  eq(successes, 1, "AC-29: success");

  // AC-35 / SEC-3: the check sends employee_id only when HR applies for someone else.
  fresh(); ROUTES.apply_leave = "drop";
  window.LP.subject = {name: "PPJ-0058", label: "Rahul"};
  let checkBody = null;
  const realFetch = window.fetch;
  window.fetch = (url, opts) => { if (method(url) === "get_leave_summary") checkBody = opts && opts.body; return realFetch(url, opts); };
  send(); await settle(30); send(); await settle(40);
  has(checkBody, '"employee_id":"PPJ-0058"', "AC-35: HR's check names the employee");
  fresh(); ROUTES.apply_leave = "drop"; checkBody = null;
  send(); await settle(30); send(); await settle(40);
  eq(checkBody, "{}", "AC-48 / SEC-3: an employee's own check sends no employee_id");
  window.fetch = realFetch;

  // AC-40: lost three times, then the network is back - still one record.
  fresh(); successes = 0; let saved = 0;
  ROUTES.apply_leave = () => { saved++; return "drop"; };
  ROUTES.get_leave_summary = () => (saved ? {ok: {applications: [{leave_type: "Earned Leave", from_date: "2026-11-06",
                                                                   to_date: "2026-11-07", status: "Open"}]}} : {ok: {applications: []}});
  send(); await settle(30);
  ROUTES.get_leave_summary = "drop"; send(); await settle(30);
  has(txt("la-send-fail"), "Still no answer from the office.", "AC-30: the check got no answer either");
  send(); await settle(30);
  ROUTES.get_leave_summary = () => ({ok: {applications: [{leave_type: "Earned Leave", from_date: "2026-11-06",
                                                          to_date: "2026-11-07", status: "Open"}]}});
  send(); await settle(40);
  eq(saved, 1, "AC-40: one record after three lost answers");
  eq(successes, 1, "AC-40: and it says so once");

  // AC-31: a send may have arrived and the signal is now gone.
  fresh(); ROUTES.apply_leave = "drop"; send(); await settle(30);
  ONLINE = false; send(); await settle(20); ONLINE = true;
  has(txt("la-send-fail"), "Still no signal.", "AC-31: still no signal after a lost answer");
  has(txt("la-send-fail"), "We check first, so it is never sent twice.", "AC-31: the check is promised");

  // AC-34: the old DTC sentence is gone.
  hasNot(doc.documentElement.innerHTML, "Not sent: the connection dropped", "AC-34");

  // ── US-7: expense claim ───────────────────────────────────────────────
  ROUTES.get_expense_types = {ok: [{name: "Travel"}]};
  window.openExpenseModal(); await settle(30);
  const ec = doc.getElementById("ec-expense-type");
  ec.innerHTML = '<option value="Travel">Travel</option>'; ec.value = "Travel";
  doc.getElementById("ec-amount").value = "250";
  sent.length = 0; ONLINE = false;
  window.submitExpenseClaim(); await settle(20);
  eq(count("apply_expense_claim"), 0, "AC-43: no signal, nothing sent");
  has(txt("ec-send-fail"), "We could not reach the office. Nothing was sent.", "AC-43: the words");
  eq(txt("ec-submit-btn"), "Try again", "AC-43: Try again is safe - nothing left the phone");
  ONLINE = true; ROUTES.apply_expense_claim = "drop";
  window.submitExpenseClaim(); await settle(30);
  has(txt("ec-send-fail"), "No answer from the office. It may have gone through.", "AC-41: lost answer");
  has(txt("ec-send-fail"), "Look in your list before you send it again.", "AC-41: look in your list");
  eq(doc.getElementById("ec-submit-btn").style.display, "none", "AC-41 / SEC-2: no control sends again");
  eq(txt("ec-close-btn"), "Close", "AC-41: the footer shows Close");

  // ── US-7: advance ─────────────────────────────────────────────────────
  doc.getElementById("adv-purpose").value = "Medical bills";
  doc.getElementById("adv-amount").value = "5000";
  sent.length = 0; ROUTES.submit_advance_request = "drop";
  window.submitAdvanceRequest(); await settle(30);
  has(txt("adv-send-fail"), "Look in your list before you send it again.", "AC-42: lost answer");
  eq(doc.getElementById("adv-submit-btn").disabled, true, "AC-42: Submit stays off while it shows");
  window.submitAdvanceRequest(); await settle(30);
  eq(count("submit_advance_request"), 1, "AC-42 / SEC-2: no second send");
  doc.querySelector("#adv-send-fail button").click(); await settle(20);
  eq(doc.getElementById("adv-send-fail").style.display, "none", "AC-42: Close hides the message");

  // ── US-4 / US-8 through api(): every call ends, and no Frappe pop-up on a 5xx ──
  msgprints.length = 0;
  let got = null;
  ROUTES.get_hr_analytics = {status: 500, body: {exc: "Traceback ...", _server_messages: serverSays("internal detail")}};
  window.api("get_hr_analytics", {}, () => { got = "ok"; }, (e) => { got = e.kind; });
  await settle(20);
  eq(got, "server", "AC-19: a 5xx reaches the error branch");
  eq(msgprints.length, 0, "AC-47: no Frappe pop-up beside the box on a 5xx");
  got = null;
  ROUTES.get_hr_analytics = {status: 403, body: {_server_messages: serverSays("Not permitted")}};
  window.api("get_hr_analytics", {}, () => { got = "ok"; }, (e) => { got = e.kind; });
  await settle(20);
  eq(got, "refused", "a refusal reaches the error branch");
  eq(msgprints.length, 1, "SEC-5: a refusal still shows the server's message, as before");
  ONLINE = false; got = null; sent.length = 0;
  window.api("get_payslips", {}, () => { got = "ok"; }, (e) => { got = e.kind; });
  await settle(10); ONLINE = true;
  eq(got, "offline", "AC-17: no signal ends at once");
  eq(count("get_payslips"), 0, "AC-17: and sends nothing");

  // The failure box: words, role, Try again calls the loader once (AC-17, AC-20).
  const box = doc.createElement("div");
  box.innerHTML = "<p>Loading…</p>";
  doc.body.appendChild(box);
  let retried = 0;
  window.failBox(box, {kind: "offline"}, () => { retried++; });
  has(box.textContent, "We could not reach the office.", "AC-17: heading");
  has(box.textContent, "Check your signal, then tap Try again.", "AC-17: reason line");
  eq(box.querySelector(".fail").getAttribute("role"), "alert", "AC-17: role=alert");
  box.querySelector(".fail button").click();
  eq(retried, 1, "AC-20: Try again calls the loader once");
  has(box.textContent, "Loading…", "AC-20: Loading… shows again");
  window.failBox(box, {kind: "offline"}, () => { retried++; });
  has(box.textContent, "Still could not reach the office.", "AC-20: the second failure says Still");
  window.failBox(box, {kind: "server"}, () => {});
  has(box.textContent, "Something went wrong at the office.", "AC-19: 5xx heading");
  has(box.textContent, "Tap Try again in a minute. If it keeps happening, tell HR.", "AC-19: 5xx line");

  // ── OPS-S4: answers that come at 16 s, one read and one write, at the real limit ──
  console.log("  ...  waiting 16 s for the slow answers (OPS-S4)");
  fresh(); successes = 0;
  // A read through api(): the box at 15 s, then the data replaces it, once.
  const panel = doc.createElement("div");
  panel.innerHTML = "<p>Loading…</p>";
  doc.body.appendChild(panel);
  let painted = 0;
  ROUTES.get_payslips = {hold: 16000, then: {ok: {payslips: []}}};
  window.api("get_payslips", {}, () => { painted++; panel.innerHTML = "<p>the data</p>"; },
             (e) => window.failBox(panel, e, () => {}));
  // A write through api(): at 15 s it must not unlock its button (OPS-S3).
  const wbtn = doc.createElement("button"); wbtn.disabled = true; doc.body.appendChild(wbtn);
  ROUTES.submit_shift_request = {hold: 16000, then: {ok: {name: "SR-1"}}};
  window.api("submit_shift_request", {}, () => { wbtn.textContent = "done"; },
             (e) => { if (window.mayHaveGone(e)) { window.sayMayHaveGone(); return; } wbtn.disabled = false; });
  // A leave send through gpFetch, held past the limit.
  ROUTES.apply_leave = {hold: 16000, then: {ok: {name: "LA-9"}}};
  send();
  await settle(15300);
  has(panel.textContent, "The office did not answer in 15 seconds. Tap Try again.", "AC-18: the read ends at 15 s");
  eq(wbtn.disabled, true, "OPS-S3: a timed-out write never unlocks its button");
  has(txt("la-send-fail"), "No answer from the office. It may have gone through.", "AC-27: the send ends at 15 s");
  eq(btn().textContent, "Try again", "AC-27: Try again");
  await settle(1200);
  has(panel.textContent, "the data", "AC-21: the late answer replaces the box by itself");
  eq(painted, 1, "AC-21: once");
  eq(successes, 1, "AC-33: the late send shows success once");
  eq(count("submit_shift_request"), 1, "OPS-R3 / AC-24: nothing retried by itself");
  eq(count("get_payslips"), 1, "AC-24: nothing retried by itself");
  eq(count("apply_leave"), 1, "AC-24: nothing resent by itself");

  console.log(`### phone 070 DOM test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
