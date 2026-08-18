/* Manager Notes tab: a manager must be able to WRITE a note here, not only
   read the list. Previously the only add form lived in an employee's drawer. */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const html = fs.readFileSync(process.argv[2], "utf8");
let pass = 0, fail = 0;
const ok  = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };

const NOTES = {
  notes: [{ id: "N1", employee_id: "HR-EMP-00005", employee_name: "Vikram Joshi",
            date: "2026-07-28", text: "Handled the Q3 escalation well.",
            owner: "rahul", modified: "2026-07-28 10:00:00" }],
  employees: { "HR-EMP-00005": "Vikram Joshi", "HR-EMP-00004": "Priya Mehta" },
};

const calls = [];
function reply(url, body) {
  const m = /hr_api\.(\w+)|goals_api\.(\w+)|performance_api\.(\w+)/.exec(url) || [];
  const fn = m[1] || m[2] || m[3] || "";
  calls.push({ fn, body });
  if (fn === "get_manager_notes") return NOTES;
  if (fn === "save_manager_note") return { id: "N2", status: "created" };
  if (fn === "get_portal_context")
    return { employee_id: "HR-EMP-00003", employee_name: "Rahul", is_manager: true,
             team: [{ name: "HR-EMP-00005", employee_name: "Vikram Joshi" },
                    { name: "HR-EMP-00004", employee_name: "Priya Mehta" }],
             goals_installed: true, dashboard: {}, cycle: null };
  if (fn === "get_available_features") return { goals: true };
  // The shell boots several unrelated widgets; give them a shape they can read
  // rather than letting an undefined blow up the page under test.
  if (fn === "get_checkin_status")
    return { no_employee: 0, employee: { name: "HR-EMP-00003", employee_name: "Rahul Sharma",
             designation: "Regional Manager", department: "Sales" },
             checked_in: 0, last_action: null, todays_checkins: [] };
  if (fn === "get_team_overview" || fn === "get_team_attendance")
    return { team: [{ name: "HR-EMP-00005", employee_name: "Vikram Joshi" },
                    { name: "HR-EMP-00004", employee_name: "Priya Mehta" }], rows: [] };
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
    // This page reaches the server through frappe.call, not fetch. Keep our
    // implementation even though the page reassigns window.frappe on load.
    const call = (o) => {
      const out = reply(String(o.method || ""), JSON.stringify(o.args || {}));
      setTimeout(() => { o.callback && o.callback({ message: out }); }, 0);
    };
    let store = { csrf_token: "", call };
    Object.defineProperty(w, "frappe", {
      configurable: true,
      get: () => store,
      set: (v) => { store = Object.assign(v || {}, { call, csrf_token: "" }); },
    });
    w._version_number = "0"; w.confirm = () => true; w.alert = () => {};
  },
});
const { window } = dom, doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));
const vis = el => el && window.getComputedStyle(el).display !== "none";

(async () => {
  await settle(400);
  // Seed the team map the way loadPortalContext does, then open the tab.
  window.switchPanel("team");
  await settle(200);
  window.switchTeamTab("notes");
  await settle(300);

  // ── There must be a way to add, not just read ──────────────────────
  const addBtn = Array.from(doc.querySelectorAll("#tv-notes-panel button"))
    .find(b => /add note/i.test(b.textContent));
  addBtn ? ok("Manager Notes tab offers an Add Note action")
         : bad("no Add Note control on the Manager Notes tab");

  const form = doc.getElementById("tn-add-form");
  form ? ok("an add-note form exists on the tab") : bad("no add-note form");
  vis(form) === false ? ok("form starts hidden so the list leads")
                      : bad("add form is open by default");

  addBtn.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
  await settle(120);
  vis(form) ? ok("Add Note reveals the form") : bad("Add Note did not reveal the form");

  // ── The form has what a note needs ─────────────────────────────────
  const sel = doc.getElementById("tn-new-emp");
  const date = doc.getElementById("tn-new-date");
  const text = doc.getElementById("tn-new-text");
  (sel && date && text) ? ok("form asks for employee, date and text")
                        : bad("form is missing a field");
  const opts = Array.from(sel.options).map(o => o.textContent);
  opts.includes("Vikram Joshi") && opts.includes("Priya Mehta")
    ? ok(`employee picker lists the team (${opts.join(", ")})`)
    : bad("employee picker not populated: " + opts.join(", "));
  /^\d{4}-\d{2}-\d{2}$/.test(date.value)
    ? ok(`date defaults to today (${date.value})`) : bad("date not pre-filled: " + date.value);

  // ── Validation before hitting the server ───────────────────────────
  calls.length = 0;
  window.tnSaveNote();
  await settle(80);
  const errEl = doc.getElementById("tn-new-err");
  (!calls.some(c => c.fn === "save_manager_note") && errEl.textContent.length)
    ? ok(`empty note refused client-side: “${errEl.textContent}”`)
    : bad("empty note was submitted");

  // ── A real save posts the right payload and refreshes ──────────────
  sel.value = "HR-EMP-00004";
  date.value = "2026-07-20";
  text.value = "Led the audit close-out.";
  calls.length = 0;
  window.tnSaveNote();
  await settle(250);
  const saved = calls.find(c => c.fn === "save_manager_note");
  if (!saved) { bad("save_manager_note was never called"); }
  else {
    const sent = JSON.parse(saved.body || "{}");
    (sent.employee_id === "HR-EMP-00004" && sent.note_date === "2026-07-20" &&
     /audit close-out/.test(sent.note_text))
      ? ok("save posts employee, date and text")
      : bad("wrong payload: " + JSON.stringify(sent));
  }
  calls.some(c => c.fn === "get_manager_notes")
    ? ok("the list refreshes after saving") : bad("list not reloaded after save");
  vis(form) === false ? ok("form closes once the note is saved")
                      : bad("form stayed open after save");

  // ── The empty state should also offer a way in ─────────────────────
  window.renderTeamNotesList([], {});
  const emptyBtn = Array.from(doc.querySelectorAll("#tn-list button"))
    .find(b => /add note/i.test(b.textContent));
  emptyBtn ? ok("empty state offers Add Note rather than dead-ending")
           : bad("empty state has no way to add the first note");

  console.log(`### notes DOM test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
