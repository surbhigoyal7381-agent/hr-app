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

/* The people this caller may open - which is to say, exactly what the server
   would hand back. `whose_months_i_can_open` scopes to the caller's own
   reporting line, so these two are the whole universe for this manager. */
const SCOPED = [
  { name: REPORT, employee_name: "Neha Kumar", designation: "Executive",
    department: "Sales" },
  { name: "HR-EMP-00009", employee_name: "Vikas Rana", designation: "Fitter",
    department: "Plant" },
];
/* Matches "neh" and is NOT in the line. The server never returns it, so it
   must never appear on screen - which is only true while the SEARCH is the
   server's job. A picker that filtered a list in the browser would have to be
   handed a staff directory first, and this name is how we would find out. */
const OUTSIDER = "Nehal Verma";

const calls = [];
const REVIEW_ROWS = [];
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
  if (fn === "whose_months_i_can_open") {
    const term = String((JSON.parse(body || "{}") || {}).search || "").toLowerCase();
    return SCOPED.filter(p => !term
      || p.employee_name.toLowerCase().indexOf(term) >= 0
      || p.name.toLowerCase().indexOf(term) >= 0);
  }
  if (fn === "month") {
    const a = JSON.parse(body || "{}");
    const who = a.employee || ME;
    const hit = SCOPED.filter(p => p.name === who)[0];
    return { employee: who, employee_name: hit ? hit.employee_name : "Rahul Sharma",
             is_self: who === ME, can_request: who !== ME, can_review: false,
             can_request_from: null, can_request_basis: null,
             on_behalf_enabled: true, tolerance_mins: 15,
             year: a.year, month: a.month, days: [],
             totals: { present: 0, hours_worked: 0, short_days: 0,
                       missing_punches: 0, late_days: 0, leave: 0 } };
  }
  if (fn === "team_days") return { people: [], rows: [], total: 0 };
  if (fn === "to_review") return REVIEW_ROWS;
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

  // ── One press, one request (18 Oct 2026) ───────────────────────────
  // The error log held two calls 35ms apart, and the second arrived with no
  // body at all - so a correct refusal reached the screen as a Python error
  // about missing arguments. Nothing in this file sent twice, but nothing
  // stopped a second press either. Now a press while one is in flight does
  // nothing.
  putForm("Marked Absent by Mistake");
  window.acState.employee = REPORT;
  window.acState.data = { employee: REPORT, employee_name: "Neha Kumar",
                          is_self: false, can_request: true, days: [] };
  calls.length = 0;
  window.acSubmit("2026-10-14");
  window.acSubmit("2026-10-14");
  await settle(250);
  const pressed = calls.filter(c => c.fn === "raise_for_report").length;
  pressed === 1 ? ok("two presses send one request")
                : bad("two presses sent " + pressed + " requests");

  // Nothing incomplete leaves the page: JSON.stringify drops an undefined
  // value silently, which is how a missing employee became an unhelpful
  // server error.
  putForm("Marked Absent by Mistake");
  window.acState.employee = null;
  window.acState.data = { employee: null, employee_name: "Neha Kumar",
                          is_self: false, can_request: true, days: [] };
  calls.length = 0;
  window.acSubmit("2026-10-14");
  await settle(250);
  /* Only correction calls count. The page's bell timers (the goals badge at
     1.5 s, and since slice 066 the grooming notices) fire on their own clock
     and used to land inside this window, failing the run at random. */
  const sent = calls.filter(c => c.fn);
  sent.length === 0
    ? ok("a request with nobody named is never sent")
    : bad("an incomplete request was sent: " + JSON.stringify(sent));

  // ── The form is offered exactly where the server would accept it ───
  // `can_request_from` is the oldest day a manager may file for. Blank now
  // means NO LIMIT, so it comes back as null far more often than it did -
  // and null must mean "offer every day", never "hide everything".
  const day = (date) => ({
    date: date, weekday: "Wed", status: "Present", hours: 8, expected_hours: 8,
    short_by: 0, late_by_mins: 0, grace_mins: 0, punches: [], attendance: "A1",
    missing_punch: false, request: null, holiday: null, leave_type: null,
    shift_starts: "09:00", shift_ends: "18:00", in_time: "09:00",
    out_time: "18:00", is_future: false,
  });
  const totals = { present: 1, hours_worked: 8, short_days: 0,
                   missing_punches: 0, late_days: 0, leave: 0 };
  const paint = (extra) => {
    window.acState.open = null;
    window.acState.employee = REPORT;
    window.acState.data = Object.assign(
      { employee: REPORT, employee_name: "Neha Kumar", is_self: false,
        can_request: true, tolerance_mins: 15, totals: totals,
        days: [day("2026-10-01"), day("2026-10-14")] }, extra);
    window.acToggle("2026-10-01");
    return (doc.getElementById("ac-body") || {}).innerHTML || "";
  };

  const noLimit = paint({ can_request_from: null, can_request_basis: null });
  /ac-form/.test(noLimit)
    ? ok("no limit offers the form on an old day")
    : bad("no limit hid the form - null must mean 'offer every day'");

  const bounded = paint({ can_request_from: "2026-10-10",
                          can_request_basis: "working days on this person's own holiday list" });
  !/ac-form/.test(bounded)
    ? ok("a day older than the window is not offered a form")
    : bad("the form was offered on a day the server would refuse");
  /10 Oct 2026/.test(bounded)
    ? ok("and the page says which day is the oldest they can ask about")
    : bad("the oldest day was not named: " + bounded.slice(0, 400));

  const switchedOff = paint({ can_request: false, can_request_from: null,
                              on_behalf_enabled: false });
  /does not let a manager/.test(switchedOff)
    ? ok("with the setting off the page says so, in plain words")
    : bad("the switched-off page did not explain itself");

  // ── Whose record: the person picker (19 Oct 2026) ──────────────────
  // Surbhi, on a 403-entry dropdown: "there should be a way to do a text
  // based search with the drop down". What is pinned here is the three things
  // that make it safe as well as usable - the search happens on the server,
  // "Whole team" survives, and the whole control works from the keyboard.
  const key = (k) => {
    const box = doc.getElementById("ac-pick-q");
    const ev = new window.KeyboardEvent("keydown", { key: k, bubbles: true,
                                                     cancelable: true });
    box.dispatchEvent(ev);
    return ev;
  };
  const rows = () => Array.from(doc.querySelectorAll("#ac-pick-list .ac-pick-o"))
                          .map(li => li.textContent);

  window.acState.people = null;        // as a fresh page would be
  window.acState.employee = null;
  window.acState.team = false;
  await window.acOpen();
  await settle(300);

  const box = doc.getElementById("ac-pick-q");
  box ? ok("the picker is a text box you can type in")
      : bad("there is no search box on the attendance bar");
  if (!box) {
    console.log(`### correction DOM test: ${pass} passed, ${fail} failed`);
    process.exit(1);
  }
  (box.getAttribute("role") === "combobox")
    ? ok("it tells a screen reader it is a combobox")
    : bad("the box has no combobox role");
  (doc.querySelector('label[for="ac-pick-q"]') !== null)
    ? ok("and it has a label")
    : bad("the search box has no label");

  // An empty box must not be an empty list: twelve reports should be there
  // without typing a letter. A click is what opens it - focus deliberately
  // does not, or choosing somebody would reopen the list it just closed.
  box.focus();
  box.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
  const idle = rows();
  (idle.length === 2 + SCOPED.length)
    ? ok("an empty box lists everyone it can, with no typing")
    : bad("an empty box listed " + idle.length + " rows: " + JSON.stringify(idle));
  /Whole team/.test(idle[0] || "")
    ? ok('"Whole team" is the first entry')
    : bad('"Whole team" is not first: ' + JSON.stringify(idle));

  // Typing narrows it, and the narrowing is the SERVER's.
  calls.length = 0;
  box.value = "neh";
  window.acPickType("neh");
  await settle(420);
  const asked = calls.filter(c => c.fn === "whose_months_i_can_open");
  const sentTerm = asked.length
    ? (JSON.parse(asked[asked.length - 1].body || "{}").search || "") : "";
  (sentTerm === "neh")
    ? ok("the typed words are sent to whose_months_i_can_open")
    : bad("the search was not sent to the server: " + JSON.stringify(calls));
  const narrowed = rows();
  (narrowed.length === 1 && /Neha Kumar/.test(narrowed[0]))
    ? ok("typing narrows the list to the match")
    : bad("typing did not narrow the list: " + JSON.stringify(narrowed));
  !narrowed.some(t => t.indexOf(OUTSIDER) >= 0)
    ? ok("somebody outside the manager's line never appears")
    : bad("a name from outside the reporting line was shown: "
          + JSON.stringify(narrowed));
  /HR-EMP-00005/.test(narrowed[0] || "")
    ? ok("the row shows the employee ID as well as the name")
    : bad("the row does not show the employee ID: " + narrowed[0]);

  // Arrow keys, Enter, Escape - and the highlight a screen reader reads.
  const down = key("ArrowDown");
  down.defaultPrevented
    ? ok("ArrowDown moves the highlight instead of the cursor")
    : bad("ArrowDown was not handled");
  (box.getAttribute("aria-activedescendant") || "").indexOf("ac-pick-o") === 0
    ? ok("the highlighted row is named in aria-activedescendant")
    : bad("no aria-activedescendant: "
          + box.getAttribute("aria-activedescendant"));
  (doc.querySelectorAll('#ac-pick-list [aria-selected="true"]').length === 1)
    ? ok("exactly one row is marked selected")
    : bad("the selected row is not marked");

  calls.length = 0;
  const enter = key("Enter");
  await settle(300);
  enter.defaultPrevented
    ? ok("Enter takes the highlighted row")
    : bad("Enter was not handled");
  (window.acState.employee === REPORT)
    ? ok("and the page moves to that person's record")
    : bad("Enter did not open the person: " + window.acState.employee);
  (doc.getElementById("ac-pick-list").hidden === true)
    ? ok("the list closes once a choice is made")
    : bad("the list stayed open after a choice");
  (doc.activeElement && doc.activeElement.id === "ac-pick-q")
    ? ok("the keyboard stays in the search box after a choice")
    : bad("the keyboard was thrown out of the box: "
          + (doc.activeElement && doc.activeElement.id));

  window.acPickShow();
  const esc = key("Escape");
  (esc.defaultPrevented && doc.getElementById("ac-pick-list").hidden === true)
    ? ok("Escape closes the list")
    : bad("Escape did not close the list");

  // "Whole team" still switches to the cross-person list.
  window.acPickShow();
  window.acPickChoose(0);
  await settle(300);
  (window.acState.team === true)
    ? ok('"Whole team" still switches to the whole-team list')
    : bad('"Whole team" did not switch the page');
  (doc.getElementById("ac-team").style.display !== "none")
    ? ok("and the whole-team list is the thing on screen")
    : bad("the whole-team list is still hidden");

  // ── HR's review rows follow the server's can_decide (068) ─────────────
  // DTC, 22 Oct 2026: Approve was offered on a request still inside the
  // manager's two working days, and the server refused it with a 403.
  const WAIT = "This is still with Vaneet Garg until 24-10-2026. You can decide it as HR from then.";
  REVIEW_ROWS.push(
    { name: "ATR-1", employee: REPORT, employee_name: "Neha Kumar", reason: "On Duty",
      from_date: "2026-10-20", to_date: "2026-10-20", can_decide: true, not_yet: null },
    { name: "ATR-2", employee: "HR-EMP-00009", employee_name: "Vikas Rana",
      reason: "On Duty", from_date: "2026-10-21", to_date: "2026-10-21",
      can_decide: false, not_yet: WAIT });
  await window.acReviewQueue();
  const cards = [...doc.querySelectorAll("#ac-review .ac-req")];
  const decideIn = (el) => [...el.querySelectorAll("button")]
    .filter(b => /acDecide/.test(b.getAttribute("onclick") || "")).length;
  (cards.length === 2) ? ok("both waiting requests are listed")
                       : bad("expected two review rows, got " + cards.length);
  (cards[0] && decideIn(cards[0]) === 2)
    ? ok("a request HR may decide today has Approve and Decline")
    : bad("the decidable row lost its buttons");
  (cards[1] && decideIn(cards[1]) === 0)
    ? ok("a request HR may not decide yet has no Approve or Decline")
    : bad("a button the server will refuse is still offered");
  (cards[1] && cards[1].textContent.indexOf("still with Vaneet Garg until 24-10-2026") >= 0)
    ? ok("and it says who has it and until when")
    : bad("the waiting row does not say why");
  (cards[1] && /See their month/.test(cards[1].textContent))
    ? ok("the waiting row can still open the month")
    : bad("the waiting row lost 'See their month'");

  console.log(`### correction DOM test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
