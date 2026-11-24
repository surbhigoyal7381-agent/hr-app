/* Slice 088's three screens, driven the way a person drives them.

   **What this pins is what each button SENDS**, not what it draws. The rule comes
   from 28 Oct 2026: a test that only reads the HTML passes just as well when the
   handler posts to the wrong endpoint, sends the wrong month, or swallows the
   server's refusal and shows "check your connection" instead. Every assertion here
   is either a payload that went to the server or a payload that deliberately did
   NOT - the client-side guards must stop a call, not merely grey a button out.

   It also pins the two decisions that reverse the drawn prototype, because those are
   the ones a later developer would "fix" back: the sheet prints "HR" with no name,
   and the salary-slip line appears only on a page that really does hold pay. */

const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok  = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };

const ME = "HR-EMP-00003";
const WORKER = "HR-EMP-00011";
const OTHER = "HR-EMP-00012";
const NOTICE = "RN-00007";

const calls = [];
let REFUSE_RECORD = null;    // a sentence the server refuses `record` with
let REFUSE_LIST = null;      // {status, exc_type} for a refused `list_people`
let ROWS = null;             // what list_people hands back

function listRows() {
  if (ROWS) return ROWS;
  return [
    { employee: WORKER, employee_name: "Sunita Devi", employee_number: "1075",
      branch: "DTC Delhi", changed_days: 1, open_days: 1, state: "not_printed",
      uncovered: 1, i_filed: false, printed_at: null, printed_by: null,
      recorded_by: null, recorded_on: null, said: null, notice: null,
      pages: null, can_tick: true, can_record: false },
    /* `pages` is what list_people sends for a printed notice. Ramesh has two sheets.
       It used to be patched on by hand further down, which meant the guard was being
       tested against a key the real server never sent - the server always assumed 1
       and a two-page notice could not be recorded at all. */
    { employee: OTHER, employee_name: "Ramesh Kumar", employee_number: "1080",
      branch: "DTC Delhi", changed_days: 2, open_days: 2, state: "printed",
      uncovered: 0, i_filed: false, printed_at: "2026-11-20 10:00:00",
      printed_by: "hr@example.com", recorded_by: null, recorded_on: null,
      said: null, notice: NOTICE, pages: 2, can_tick: true, can_record: true },
    { employee: "HR-EMP-00013", employee_name: "Anil Filer", employee_number: "1081",
      branch: "DTC Delhi", changed_days: 1, open_days: 1, state: "filer",
      uncovered: 0, i_filed: true, printed_at: "2026-11-20 10:00:00",
      printed_by: "hr@example.com", recorded_by: null, recorded_on: null,
      said: null, notice: "RN-00008", can_tick: true, can_record: false },
  ];
}

const SHEETS = [
  { notice: NOTICE, employee: OTHER, employee_name: "Ramesh Kumar",
    employee_number: "1080", branch: "DTC Delhi", company: "DTC Pvt Ltd",
    month: "2026-11-01", page_no: 1, pages: 2, ref: "1080/2026-11/1-2",
    print_no: NOTICE, pay_line: true,
    changes: [{ day: "Fri 13 Nov", what: ["Out time 18:30 added"], counts: "9 h 0 m",
                filed_role: "HR", filed_by: null, filed_on: "2026-11-14",
                why: "He forgot to punch out", blocks_pay: true }] },
  /* A page of manager additions: no pay line, and the manager IS named. */
  { notice: NOTICE, employee: OTHER, employee_name: "Ramesh Kumar",
    employee_number: "1080", branch: "DTC Delhi", company: "DTC Pvt Ltd",
    month: "2026-11-01", page_no: 2, pages: 2, ref: "1080/2026-11/2-2",
    print_no: NOTICE, pay_line: false,
    changes: [{ day: "Sat 14 Nov", what: ["Scan at 11:02 not counted"], counts: "8 h 0 m",
                filed_role: "Manager", filed_by: "Priya Singh", filed_on: "2026-11-15",
                why: "Double scan at the gate", blocks_pay: false }] },
];

function reply(url, body) {
  const m = /register_notice\.(\w+)|attendance_correction\.(\w+)|hr_api\.(\w+)|punch_fix\.(\w+)/.exec(url) || [];
  const fn = m[1] || m[2] || m[3] || m[4] || "";
  calls.push({ fn, body });
  if (fn === "list_people")
    return { month: "2026-11-01", rows: listRows(), total: listRows().length,
             done: 0, waiting: listRows().length, start: 0, page: 25 };
  if (fn === "open_notices") return { month: "2026-11-01", sheets: SHEETS };
  if (fn === "record") return { notice: NOTICE, outcome: "Signed", marked: 1, stale: [], photos: 2 };
  if (fn === "my_changes") return { month: "2026-11-01", days: [], changed: 0 };
  if (fn === "get_portal_context")
    return { employee_id: ME, employee_name: "Rahul", is_manager: true, team: [],
             dashboard: {}, cycle: null };
  if (fn === "month")
    return { employee: ME, employee_name: "Rahul", is_self: true, can_request: false,
             can_review: false, year: 2026, month: 11, days: [],
             totals: { present: 0, hours_worked: 0, short_days: 0, missing_punches: 0,
                       late_days: 0, leave: 0 } };
  if (fn === "before_payroll") return { month: "2026-11-01", rows: [] };
  if (fn === "to_review") return [];
  if (fn === "get_available_features") return {};
  if (fn === "get_checkin_status")
    return { no_employee: 0, employee: { name: ME, employee_name: "Rahul" },
             checked_in: 0, last_action: null, todays_checkins: [] };
  return [];
}

const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://dtc.localhost/hrms-employee",
  beforeParse(w) {
    w.fetch = (url, opts) => {
      const u = String(url);
      if (REFUSE_RECORD && /register_notice\.record/.test(u)) {
        calls.push({ fn: "record", body: opts && opts.body });
        return Promise.resolve({ ok: false, status: 417,
          json: () => Promise.resolve({ exc_type: "ValidationError",
            _server_messages: JSON.stringify([JSON.stringify({ message: REFUSE_RECORD })]) }),
          text: () => Promise.resolve("") });
      }
      if (REFUSE_LIST && /register_notice\.list_people/.test(u)) {
        calls.push({ fn: "list_people", body: opts && opts.body });
        return Promise.resolve({ ok: false, status: REFUSE_LIST.status,
          json: () => Promise.resolve({ exc_type: REFUSE_LIST.exc_type }),
          text: () => Promise.resolve("") });
      }
      return Promise.resolve({ ok: true, status: 200,
        json: () => Promise.resolve({ message: reply(u, opts && opts.body) }),
        text: () => Promise.resolve("") });
    };
    const call = (o) => {
      const out = reply(String(o.method || ""), JSON.stringify(o.args || {}));
      setTimeout(() => { o.callback && o.callback({ message: out }); }, 0);
      return Promise.resolve({ message: out });
    };
    w.frappe = { call, csrf_token: "x", boot: { user: { full_name: "Asha HR" } },
                 session: { user: "hr@example.com" }, ui: {}, _messages: {} };
    w.print = () => { calls.push({ fn: "__window_print__", body: null }); };
    /* JSDOM has no object-URL store. The dialog only uses these for the thumbnail
       it shows HR, so a counter is enough and it keeps the revoke path exercised. */
    let urls = 0;
    w.URL.createObjectURL = () => "blob:photo-" + (++urls);
    w.URL.revokeObjectURL = () => {};
  },
});

const { window } = dom;
const doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));

/* The card hangs itself off the attendance panel's review wrapper, so that has to
   exist before `rnLoad` has anywhere to go. The same element the real page draws. */
function putHost() {
  if (doc.getElementById("ac-review-wrap")) return;
  const w = doc.createElement("div");
  w.id = "ac-review-wrap";
  doc.body.appendChild(w);
}

/* `n` photographs of a signed page, handed to the dialog the way a phone hands them
   over: real File objects through the real picker. `rnPickPhotos` reads each one with
   FileReader, which is asynchronous, so this waits for the dialog to redraw. */
async function pickPhotos(n) {
  const files = [];
  for (let i = 0; i < n; i++) {
    files.push(new window.File([new Uint8Array([0xff, 0xd8, 0xff, i])],
                               "page" + i + ".jpg", { type: "image/jpeg" }));
  }
  window.rnPickPhotos({ files: files });
  for (let tries = 0; tries < 20; tries++) {
    await settle(10);
    const imgs = doc.querySelectorAll("#rn-scrim .rn-thumbs img");
    if (imgs.length === n) return;
  }
}

function sent(fn) { return calls.filter(c => c.fn === fn); }
function lastBody(fn) {
  const hit = sent(fn).slice(-1)[0];
  if (!hit || !hit.body) return {};
  try { return JSON.parse(hit.body); } catch (e) { return {}; }
}
function cardText() {
  const el = doc.getElementById("rn-card");
  return el ? el.textContent.replace(/\s+/g, " ") : "";
}
function click(sel) {
  const el = typeof sel === "string" ? doc.querySelector(sel) : sel;
  if (!el) return false;
  el.click();
  return true;
}
function buttonSaying(words, root) {
  const all = (root || doc).querySelectorAll("button");
  for (let i = 0; i < all.length; i++) {
    if (all[i].textContent.indexOf(words) >= 0) return all[i];
  }
  return null;
}

(async function run() {
  await settle(60);
  putHost();

  /* ── the card ─────────────────────────────────────────────────────────── */
  await window.rnLoad("2026-11-01");
  await settle(40);

  const body = lastBody("list_people");
  body.month === "2026-11-01" && body.start === 0
    ? ok("the card asks for the month it is showing, from row 0")
    : bad("the card asked for " + JSON.stringify(body));

  cardText().indexOf("Not printed yet") >= 0
    ? ok("a person with no notice reads \"Not printed yet\"")
    : bad("the not-printed state is missing: " + cardText().slice(0, 160));

  cardText().indexOf("Waiting for the signature") >= 0
    ? ok("a printed notice says the print was opened and is waiting")
    : bad("the printed state is missing");

  cardText().indexOf("another HR person records the signature") >= 0
    ? ok("the filer is told why they cannot record it")
    : bad("the filer sentence is missing");

  const filerRow = Array.prototype.slice.call(doc.querySelectorAll("#rn-card .rn-list li"))
    .filter(li => li.textContent.indexOf("Anil Filer") >= 0)[0];
  filerRow && !buttonSaying("Signed on the register", filerRow)
    ? ok("the filer is offered no record button")
    : bad("the filer row still offers the record button");

  /* ── print: what it sends ─────────────────────────────────────────────── */
  calls.length = 0;
  const printBtn = buttonSaying("Print notice");
  printBtn ? printBtn.click() : bad("there is no Print notice button");
  await settle(40);

  const printed = lastBody("open_notices");
  (printed.employees || [])[0] === WORKER && printed.month === "2026-11-01"
    ? ok("Print notice sends that one person and the month on screen")
    : bad("Print notice sent " + JSON.stringify(printed));

  /* ── the sheet ────────────────────────────────────────────────────────── */
  const pv = doc.getElementById("rn-pv");
  pv ? ok("the preview opens") : bad("no preview was drawn");
  const pages = pv ? pv.querySelectorAll(".rn-a4") : [];
  pages.length === 2 ? ok("one A4 page per sheet the server sent")
                     : bad("drew " + pages.length + " pages, expected 2");

  if (pages.length === 2) {
    const p1 = pages[0].textContent.replace(/\s+/g, " ");
    const p2 = pages[1].textContent.replace(/\s+/g, " ");

    p1.indexOf("Out time 18:30 added") >= 0 && p1.indexOf("This day now counts 9 h 0 m.") >= 0
      ? ok("the sheet says what changed and what the day now counts")
      : bad("the sheet's change line is wrong: " + p1.slice(0, 200));

    p1.indexOf("Your salary slip for this month waits") >= 0
      ? ok("the pay line prints on a page that holds pay")
      : bad("the pay line is missing from a page that holds pay");

    p2.indexOf("Your salary slip for this month waits") < 0
      ? ok("the pay line does NOT print on a page of manager additions")
      : bad("a page of manager additions tells the worker their pay is held");

    /* Surbhi's OQ-1 decision, both halves on one print.

       Checked on the "Who filed it" CELL, not the whole page, and that distinction
       is a real one I got wrong first time. Her decision is that the employee is not
       told WHICH HR person changed their day. The footer still reads "Printed by Asha
       HR on ...", because that is the approved prototype's own `s_foot` string and
       the parity rule says build what was drawn. Whether the footer should also hide
       the name is a question for her, not for this test - it is raised with her and
       NOT quietly decided here. */
    const whoCell1 = pages[0].querySelectorAll("tbody td")[2];
    const filedBy1 = whoCell1 ? whoCell1.textContent : "";
    filedBy1.indexOf("HR") >= 0 && filedBy1.indexOf("Asha") < 0
      ? ok("an HR filing names \"HR\" in the Who filed it column, never the person")
      : bad("the Who filed it column says: " + filedBy1);
    const whoCell2 = pages[1].querySelectorAll("tbody td")[2];
    const filedBy2 = whoCell2 ? whoCell2.textContent : "";
    filedBy2.indexOf("Priya Singh") >= 0 && filedBy2.indexOf("Manager") >= 0
      ? ok("a manager's change IS named in that column, which is the other half")
      : bad("the manager column says: " + filedBy2);

    p1.indexOf("1080/2026-11/1-2") >= 0 && p1.indexOf(NOTICE) >= 0
      ? ok("the page reference carries the month, the page and the print number")
      : bad("the reference or the print number is missing");

    p1.indexOf("Signature or thumb print") >= 0 && p1.indexOf("I have read the changes") >= 0
      ? ok("the sign box and the read line are on the page")
      : bad("the sign box or the read line is missing");

    p1.indexOf("This page is only about you") >= 0
      ? ok("the footer tells the worker to keep it private")
      : bad("the privacy line is missing from the footer");

    /* No Hindi anywhere: her 21 Nov decision. Devanagari is one range, so one test. */
    /[ऀ-ॿ]/.test(p1 + p2)
      ? bad("Hindi reached the printed page, which was not built")
      : ok("the page is English only, as decided");
  }

  const pr = buttonSaying("Print 2 sheets", pv);
  pr ? (pr.click(), sent("__window_print__").length === 1
          ? ok("Print opens the browser's own print dialog")
          : bad("the print dialog was not opened"))
     : bad("there is no Print button on the preview");

  window.rnClosePreview();
  doc.getElementById("rn-pv") ? bad("the preview did not close") : ok("Back closes the preview");

  /* ── recording: the guards must stop the CALL ─────────────────────────── */
  await window.rnLoad("2026-11-01");
  await settle(40);
  window.rnOpenRecord(NOTICE);
  await settle(10);
  const dlg = doc.getElementById("rn-scrim");
  dlg ? ok("the record dialog opens") : bad("no record dialog");

  calls.length = 0;
  buttonSaying("Record signature", dlg).click();
  await settle(30);
  sent("record").length === 0 && dlg.textContent.indexOf("Add the photo of the signed notice first") >= 0
    ? ok("Record signature with no photo sends nothing and says what is missing")
    : bad("a signature with no photo reached the server, or said nothing");

  /* One photo for a two-page notice: refused here, with both numbers.

     The photos go in through the dialog's OWN picker, as real File objects, so this
     exercises the FileReader path that actually runs in a shop. Reaching into the
     dialog's private state would have tested the guard and skipped the reading. */
  window.rnOpenRecord(NOTICE);
  await settle(10);
  const dlg2 = doc.getElementById("rn-scrim");
  await pickPhotos(1);
  calls.length = 0;
  buttonSaying("Record signature", dlg2).click();
  await settle(30);
  sent("record").length === 0
    && dlg2.textContent.indexOf("Add 2 photos, one for each page. You added 1.") >= 0
    ? ok("one photo for a two-page notice sends nothing and counts both")
    : bad("the photo count guard let the call through or worded it wrongly: "
          + dlg2.textContent.replace(/\s+/g, " ").slice(0, 160));

  /* Two photos: now it sends, and it sends the outcome and both photos. */
  await pickPhotos(2);
  calls.length = 0;
  buttonSaying("Record signature", dlg2).click();
  await settle(40);
  const rec = lastBody("record");
  rec.notice === NOTICE && rec.outcome === "Signed" && (rec.photos || []).length === 2
    ? ok("Record signature sends the notice, the outcome and one photo per page")
    : bad("record sent " + JSON.stringify(Object.keys(rec)) + " " + JSON.stringify(rec.outcome));

  /* ── says it is not right ─────────────────────────────────────────────── */
  window.rnOpenRecord(NOTICE);
  await settle(10);
  const dlg3 = doc.getElementById("rn-scrim");
  calls.length = 0;
  buttonSaying("Says it is not right", dlg3).click();
  await settle(30);
  sent("record").length === 0 && dlg3.textContent.indexOf("Write what they said is not right") >= 0
    ? ok("an objection with no words sends nothing and asks for them")
    : bad("an empty objection reached the server");

  doc.getElementById("rn-nr").value = "  I was there till 7  ";
  calls.length = 0;
  buttonSaying("Says it is not right", dlg3).click();
  await settle(40);
  const nr = lastBody("record");
  nr.outcome === "Not right" && nr.reason === "I was there till 7" && !nr.photos
    ? ok("an objection sends the trimmed words, the outcome, and no photo")
    : bad("the objection sent " + JSON.stringify(nr));

  /* ── the server's refusal is the words on screen ──────────────────────── */
  REFUSE_RECORD = "A newer notice was printed. Use the newer one.";
  window.rnOpenRecord(NOTICE);
  await settle(10);
  const dlg4 = doc.getElementById("rn-scrim");
  doc.getElementById("rn-nr").value = "anything";
  buttonSaying("Says it is not right", dlg4).click();
  await settle(50);
  const shown = doc.getElementById("rn-scrim");
  shown && shown.textContent.indexOf("A newer notice was printed") >= 0
    ? ok("the server's own refusal is shown, not a connection message")
    : bad("the refusal was swallowed: " + (shown ? shown.textContent.slice(0, 140) : "dialog gone"));
  REFUSE_RECORD = null;
  window.rnCloseRecord();

  /* ── a user with no HR role sees no card at all ───────────────────────── */
  REFUSE_LIST = { status: 403, exc_type: "PermissionError" };
  await window.rnLoad("2026-11-01");
  await settle(40);
  cardText() === ""
    ? ok("a refused list leaves no card and no error on the page")
    : bad("a user with no business here was shown something: " + cardText().slice(0, 120));
  REFUSE_LIST = null;

  /* ── an empty month says so, and the forward arrow stops at this month ── */
  ROWS = [];
  await window.rnLoad("2026-10-01");
  await settle(40);
  cardText().indexOf("No changed days in October 2026") >= 0
    ? ok("an empty month names the month")
    : bad("the empty state is wrong: " + cardText().slice(0, 140));
  ROWS = null;

  const arrows = doc.querySelectorAll("#rn-card .rn-mbar button");
  arrows.length === 2 && !arrows[1].disabled
    ? ok("the forward arrow works on an earlier month")
    : bad("the forward arrow is wrong on an earlier month");

  /* The same "### name: N passed" line every other suite prints, so the runner's
     summary names this one too. Without it the suite was invisible in a 27-line
     run - it passed, but nobody reading the output could see that it had. */
  console.log("### 088 change notice DOM test: " + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})();
