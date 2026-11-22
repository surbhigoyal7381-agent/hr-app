/* Slice 089: the leaver report as a person meets it, and what Send actually posts.

   Drives the real rendered page in jsdom. The server is a stub, so what this
   proves is the SCREEN: the icon is there only when the server says
   `can_report`, the sheet is a real dialog, Send posts the person and the date
   and nothing else, every failure keeps the date, and the personal card draws
   only the keys it was sent. It does not prove the server's rules; the Python
   suite does that. */
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok  = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };
const check = (cond, m) => (cond ? ok(m) : bad(m));

const REPORT = "HR-EMP-00005";
let SCORECARD = null;
let SEND = "ok";            // ok | refuse | offline
let REFUSAL = "";
const posts = [];           // every fetch the page makes: {url, method, body}

function scorecard(over) {
  return Object.assign({
    employee: { name: REPORT, employee_name: "Ravi Kumar", designation: "Sales", department: "Retail",
                date_of_joining: "2025-01-01", status: "Active" },
    personal: {}, can_report: true, open_report: null,
    month_att_summary: {}, avg_hours: 0, monthly_att: [], leave_balances: [], pending_leaves: [],
    goals: [], goals_available: false, appraisal_history: [],
  }, over || {});
}

function reply(url) {
  if (/get_portal_context/.test(url)) return { employee_id: "HR-EMP-00003", employee_name: "Meena", is_manager: true, team: [], dashboard: {}, cycle: null };
  if (/get_employee_scorecard/.test(url)) return SCORECARD;
  if (/get_available_features/.test(url)) return {};
  if (/get_checkin_status/.test(url))
    return { no_employee: 0, employee: { name: "HR-EMP-00003", employee_name: "Meena Sharma",
             designation: "Store Manager", department: "Retail" },
             checked_in: 0, last_action: null, todays_checkins: [] };
  return [];
}

const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://grace.localhost/hrms-employee",
  beforeParse(w) {
    w.fetch = (url, opts) => {
      const u = String(url);
      posts.push({ url: u, method: (opts && opts.method) || "GET", body: opts && opts.body ? JSON.parse(opts.body) : null });
      if (/send_leaver_report/.test(u)) {
        if (SEND === "offline") return Promise.reject(new Error("net"));
        if (SEND === "refuse")
          return Promise.resolve({ ok: false, status: 403, json: () => Promise.resolve({
            exc_type: "PermissionError",
            _server_messages: JSON.stringify([JSON.stringify({ message: REFUSAL })]) }), text: () => Promise.resolve("") });
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({
          message: { ok: true, last_working_day: posts[posts.length - 1].body.last_working_day, reported_on: "2026-11-22" } }),
          text: () => Promise.resolve("") });
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ message: reply(u) }), text: () => Promise.resolve("") });
    };
    w.frappe = {
      call: (o) => { const out = reply(String(o.method || "")); setTimeout(() => { o.callback && o.callback({ message: out }); }, 0); return Promise.resolve({ message: out }); },
      csrf_token: "x", boot: {}, ui: {}, _messages: {},
    };
  },
});

const { window } = dom;
const doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));
const $ = id => doc.getElementById(id);

(async () => {
  await settle(400);
  if (typeof window.openEmpScorecard !== "function" || typeof window.lvOpen !== "function") {
    bad("openEmpScorecard / lvOpen are not reachable from the page"); finish(); return;
  }

  /* 1. the icon: present only when the server said so */
  SCORECARD = scorecard();
  window.openEmpScorecard(REPORT, "#123"); await settle(100);
  const icon = $("sc-left-btn");
  check(!!icon && icon.getAttribute("aria-label") === "Report that Ravi left" && icon.title === "Report that Ravi left",
        "the exit icon is beside the name, labelled with the person's first name");
  check(!!icon && icon.parentNode.classList.contains("sc-topbar"),
        "D-1: the icon sits in the header row beside the name block, not inside it where it was squeezed under the badge");
  SCORECARD = scorecard({ can_report: false });
  window.openEmpScorecard(REPORT, "#123"); await settle(100);
  check(!$("sc-left-btn"), "no icon when the server says can_report is false (no greyed control either)");

  /* 2. the sheet is a real dialog */
  SCORECARD = scorecard();
  window.openEmpScorecard(REPORT, "#123"); await settle(100);
  $("sc-left-btn").click(); await settle(20);
  const sheet = $("lv-sheet");
  check(!!sheet && sheet.getAttribute("role") === "dialog" && sheet.getAttribute("aria-modal") === "true",
        "the sheet is a dialog (role, aria-modal)");
  check(doc.activeElement === $("lv-date"), "focus goes to Last working day");
  check(/You are reporting: Ravi Kumar/.test($("lv-prev").textContent), "the preview names the person and the date");
  check(!!doc.querySelector('label[for="lv-date"]'), "the date has a visible label");

  /* 3. what Send posts: the person and the date, nothing else */
  const date = $("lv-date").value;
  $("lv-send").click(); await settle(80);
  const post = posts.filter(p => /send_leaver_report/.test(p.url))[0];
  check(!!post && post.method === "POST", "Send is a POST");
  check(post && /alvoraa_portal\.leaver_report\.send_leaver_report/.test(post.url), "it calls the leaver report method");
  check(post && JSON.stringify(Object.keys(post.body).sort()) === JSON.stringify(["employee", "last_working_day"]),
        "the body carries only the person and the date (no free text, no confirmer, no status)");
  check(post && post.body.employee === REPORT && post.body.last_working_day === date, "the right person and the date shown");
  check(/Sent for confirmation/.test($("lv-sheet").textContent) && /Wrong person or date\? Ask HR\./.test($("lv-sheet").textContent),
        "the sent message says what happens and who to ask");

  /* 4. Done: icon gone, note up, focus off the closed sheet */
  doc.querySelector("#lv-sheet .btn-primary").click(); await settle(20);
  check(!$("lv-sheet"), "Done closes the sheet");
  check(!$("sc-left-btn"), "the icon is gone once reported");
  check(/Reported, not yet confirmed\./.test($("sc-body").textContent), "the reported note is at the top of the page");

  /* 5. refusal: the server's own sentence, the date kept, the sheet stays open */
  SCORECARD = scorecard(); SEND = "refuse"; REFUSAL = "You already reported this person on 20 Nov 2026. It has not been confirmed yet.";
  window.openEmpScorecard(REPORT, "#123"); await settle(100);
  $("sc-left-btn").click(); await settle(20);
  $("lv-date").value = "2026-11-25"; $("lv-date").dispatchEvent(new window.Event("input", { bubbles: true }));
  $("lv-send").click(); await settle(80);
  check($("lv-err") && $("lv-err").textContent === REFUSAL, "a refusal shows the server's sentence, word for word");
  check($("lv-date").value === "2026-11-25", "the date is kept after a refusal");
  check($("lv-err").getAttribute("role") === "alert", "the error is announced (role=alert)");

  /* 6. no signal: the exact words, the date kept, Try again */
  SEND = "offline";
  $("lv-send").click(); await settle(80);
  check($("lv-err").textContent === "Not sent. We kept your date. Try again when you have signal.", "offline words are the approved sentence");
  check($("lv-send").textContent === "Try again" && $("lv-date").value === "2026-11-25", "Try again is offered and the date is kept");

  /* 7. Escape closes and focus returns to the icon */
  const ev = new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true });
  $("lv-sheet").dispatchEvent(ev); await settle(20);
  check(!$("lv-sheet") && doc.activeElement === $("sc-left-btn"), "Escape closes the sheet and focus returns to the icon");

  /* 8. the personal card draws only what it was sent */
  SCORECARD = scorecard({ personal: { cell_number: "9876543210", person_to_be_contacted: "Kamla", relation: "Mother", emergency_phone_number: "98100 12345" } });
  window.openEmpScorecard(REPORT, "#123"); await settle(100);
  const card = doc.querySelector(".lv-personal");
  check(!!card && /Personal phone/.test(card.textContent) && /Emergency contact/.test(card.textContent) && /Kamla, Mother, 98100 12345/.test(card.textContent),
        "the personal card shows the ticked rows");
  check(!/Home address/.test(card.textContent), "an unticked row is not drawn");
  check(!/personal_email|company_email|gender/i.test($("sc-body").innerHTML), "the page holds no email or gender");
  SCORECARD = scorecard({ personal: {} });
  window.openEmpScorecard(REPORT, "#123"); await settle(100);
  check(!doc.querySelector(".lv-personal"), "nothing ticked: no card and no placeholder");
  SCORECARD = scorecard({ personal: { cell_number: "9876543210" }, employee: { name: REPORT, employee_name: "Ravi Kumar", status: "Left" } });
  window.openEmpScorecard(REPORT, "#123"); await settle(100);
  check(!doc.querySelector(".lv-personal"), "a person who has Left: no card");

  /* 9. the Team line and the employee's line */
  check(window.lvTeamLine({ [REPORT]: { last_day: "2026-11-30" } }, REPORT).indexOf("Reported, not yet confirmed") >= 0, "the Team card shows the grey line for a reported person");
  check(window.lvTeamLine({}, REPORT) === "" && window.lvTeamLine(undefined, REPORT) === "", "and nothing for anybody else");
  const line = window.lvEmployeeLine({ leaver_report: { by: "Meena Sharma", last_day: "2026-11-30" } });
  check(/Your manager Meena Sharma reported that your last working day is/.test(line) && /Not right\? Speak to HR\./.test(line) && !/<button/.test(line),
        "the employee's line has the manager's name, the date and no button");
  check(window.lvEmployeeLine({}) === "", "no line when there is no open report");
  check(window.lvEmployeeLine({ leaver_report: { by: "<img src=x onerror=1>", last_day: "2026-11-30" } }).indexOf("<img") < 0, "the manager's name is escaped");

  /* 10. the Administrator card: what Save posts */
  window.OCS.data = { manager_sees_fields: [], manager_sees_choices: [], manager_sees_people: 45,
                      leaver_confirm_role: "HR Manager", leaver_confirm_roles: ["HR Manager", "Payroll team"],
                      leaver_confirm_holders: 2, last_changed: { by: "Surbhi", on: "2026-11-22" } };
  window.lvAdminPaint(window.OCS.data);
  check(/None\. Managers see no personal details of their team\./.test($("lv-admin-body").textContent), "day one: the empty sentence");
  check(/2 enabled people hold HR Manager/.test($("lv-admin-body").textContent), "the role row says how many people hold it");
  $("lv-see-btn").click(); await settle(20);
  const boxes = doc.querySelectorAll('#lv-dlg input[type=checkbox]');
  check(boxes.length === 3, "exactly three ticks are offered (phone, address, emergency contact)");
  boxes[0].checked = true; boxes[0].dispatchEvent(new window.Event("change", { bubbles: true }));
  check(/Save — managers see 1 details about 45 people/.test($("lv-save").textContent), "Save names its effect with the real count");
  $("lv-save").click(); await settle(80);
  const save = posts.filter(p => /set_people_setting/.test(p.url)).pop();
  check(save && save.body.key === "alvoraa_manager_sees_team_details" && save.body.value === "cell_number", "Save posts the key and the ticked field");

  finish();
})();

function finish() {
  console.log(pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
}
