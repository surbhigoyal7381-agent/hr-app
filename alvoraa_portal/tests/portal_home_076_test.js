/* Slice 076, Part A: Home's Pending and Notices cards, the leave sheet, the
   bell, and the grid, driven in jsdom against the real page and the real
   portal.js. The server is a stub; the markup, the script and the rules about
   what is drawn are the real ones.

   Pin tests (a bad merge that drops the feature fails by name):
     - the Activity card is gone
     - Pending is oldest first across kinds, five rows
     - the card's "N unread" is the bell's number
     - nothing a person wrote becomes an element
     - no "Send a notice" button exists in Part A

   Run: node alvoraa_portal/tests/portal_home_076_test.js alvoraa_portal/alvoraa_portal/www/hrms-employee.html */
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };
const eq = (got, want, m) => (JSON.stringify(got) === JSON.stringify(want) ? ok(m) : bad(m + ": got <" + JSON.stringify(got) + "> want <" + JSON.stringify(want) + ">"));
const yes = (cond, m) => (cond ? ok(m) : bad(m));

const method = s => String(s).split(".").pop();
/* What the page asks for as it starts, before any test has set a route. */
const BASE_ROUTES = {get_checkin_status: {ok: {no_employee: 1}}, get_portal_context: {ok: {}},
  get_employee_dashboard: {ok: {no_employee: true}}};
let ROUTES = Object.assign({}, BASE_ROUTES);
const CALLS = [];
const HOSTILE = "<img src=x onerror=alert(1)>";

const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://grace.localhost/hrms-employee",
  beforeParse(w) {
    w.fetch = (url, opts) => {
      const name = method(url);
      CALLS.push({name, args: opts && opts.body ? JSON.parse(opts.body) : {}});
      const h = ROUTES[name] === undefined ? {ok: {}} : ROUTES[name];
      if (h === "drop") return Promise.reject(new TypeError("Failed to fetch"));
      const v = typeof h.ok === "function" ? h.ok(CALLS[CALLS.length - 1].args) : h.ok;
      return Promise.resolve({ok: true, status: 200, json: () => Promise.resolve({message: v})});
    };
    /* api() goes through frappe.call: answer the callback with the route's value. */
    const call = (o) => {
      const name = method(o.method);
      CALLS.push({name, args: o.args || {}});
      const h = ROUTES[name] === undefined ? {ok: {}} : ROUTES[name];
      setTimeout(() => {
        if (h === "drop") { o.always && o.always({}); return; }
        o.callback && o.callback({message: h.ok});
        o.always && o.always({});
      }, 0);
      return {status: 200};
    };
    w.frappe = {call, csrf_token: "x", boot: {}, ui: {}, _messages: {}, utils: {escape_html: s => s}, msgprint: () => {}};
  },
});
const {window} = dom, doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));
const $ = id => doc.getElementById(id);
const click = el => el.dispatchEvent(new window.MouseEvent("click", {bubbles: true}));
const callsTo = n => CALLS.filter(c => c.name === n);
const alerts = [];
window.alert = m => alerts.push(m);

/* ── fixtures ─────────────────────────────────────────────────────────── */
function iso(daysAgo) {
  const d = new Date(); d.setDate(d.getDate() - daysAgo);
  const p = n => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + " 09:00:00";
}
const part = (key, rows, count) => ({key, count: count === undefined ? rows.length : count, rows});
function inbox(parts) {
  const total = parts.reduce((n, p) => n + p.count, 0);
  return {total, approvals_total: 0, has_employee: true, parts};
}
const leaveRow = (name, who, ago) => ({name, employee_name: who, from_date: "2026-11-06", to_date: "2026-11-08",
  leave_type: "Casual Leave", total_days: 3, action: "leave", waiting_since: iso(ago)});
const goalRow = (name, who, ago, kind) => ({name, kind: kind || "goal", document: (kind === "kpi" ? "KPI-" : "GOAL-") + name,
  employee_name: who, subject: "Sell 40 units", action: "goal_update", waiting_since: iso(ago)});
const fixRow = (name, who, ago) => ({name, employee_name: who, from_date: "2026-10-21", to_date: "2026-10-21", action: "attendance_fix", waiting_since: iso(ago)});
const polRow = (name, title, ago) => ({name, title, version: 2, action: "policy", waiting_since: iso(ago)});
const noteRow = (name, text, read) => ({name, text, link: null, when: "2026-10-27 16:10:00", read: read ? 1 : 0});
const feed = (items, unread, any) => ({unread, any: any === undefined ? items.length > 0 : any, items});

async function loadHomeWith(routes) {
  ROUTES = Object.assign({}, BASE_ROUTES, routes);
  CALLS.length = 0;
  window.loadHome();
  await settle(120);
}
const rowsOf = id => [...$(id).querySelectorAll(".hm-row")];
const lines = b => b.querySelector(".hm-l1").textContent;

(async () => {
  await settle(400);
  for (const fn of ["loadHome", "homePending", "homeNotices", "homeReflow", "ntOpenAll", "hmPaintPending"]) {
    if (typeof window[fn] !== "function") { bad(fn + " is not on the page"); process.exit(1); }
  }

  // ── the page ─────────────────────────────────────────────────────────
  yes(!$("home-activity-card"), "the Activity card is gone");
  yes(!doc.querySelector(".home-body-grid, .home-left-col, .home-actions-col"), "there is no fixed side column");
  yes(typeof window.renderActivityFeed === "undefined" && typeof window.homeActivity === "undefined",
      "homeActivity and renderActivityFeed are gone");
  yes($("home-grid") && $("home-pending-card") && $("home-notices-card"), "the grid, Pending and Notices cards are on the page");
  yes($("day-widget").closest(".checkin-hero"), "the Today strip sits inside the check-in card");
  const order = [...$("home-grid").children].map(c => c.id);
  eq(order.slice(0, 3), ["home-pending-card", "home-notices-card", "home-leave-card"], "card order: Pending, Notices, Leave balance");
  yes(![...doc.querySelectorAll("button, a")].some(b => /send a notice/i.test(b.textContent)),
      "no 'Send a notice' button exists in Part A");
  yes(!/Send a notice|expense_approvals|Expense claim/i.test($("home-grid").innerHTML),
      "no sender or expense markup is hidden on the page");

  // ── Pending: oldest first across kinds, five rows ────────────────────
  await loadHomeWith({
    get_inbox: {ok: inbox([
      part("leave_approvals", [leaveRow("L1", "Anita Verma", 3), leaveRow("L2", "Bhavna Shah", 9)]),
      part("goal_updates", [goalRow("G1", "Charu Sethi", 6)]),
      part("attendance_fixes", [fixRow("A1", "Dinesh Pal", 1), fixRow("A2", "Esha Ghosh", 12)]),
      part("shift_requests", []),
      part("policies", [polRow("P1", "Safety on the floor", 20)]),
      part("my_requests", []),
    ])},
    notices_feed: {ok: feed([], 0, false)},
  });
  let rows = rowsOf("home-pending-body");
  eq(rows.length, 5, "Pending shows at most 5 rows");
  eq(rows.map(lines), ["Safety on the floor", "Esha Ghosh", "Bhavna Shah", "Charu Sethi", "Anita Verma"],
     "Pending is oldest first across kinds");
  eq($("home-pending-chip").textContent, "6 waiting", "the chip says '6 waiting'");
  yes(rows.every(b => b.tagName === "BUTTON"), "every row is a real button");
  yes(/Review/.test(rows[2].textContent) && /Open/.test(rows[0].textContent), "leave rows say Review, the others say Open");
  yes(/waiting 9 days/.test(rows[2].textContent), "a leave row says how many days it has waited");
  yes($("home-pending-foot").style.display !== "none" && /See all 6/.test($("home-pending-foot").textContent), "See all 6 is offered when there are more than 5");
  eq(callsTo("get_inbox").length, 1, "Pending reads get_inbox once");

  // see all, focus, escape
  const seeAll = $("home-pending-foot").querySelector("button");
  seeAll.focus(); click(seeAll);
  let dlg = doc.querySelector("#hm-ov [role=dialog]");
  yes(dlg && dlg.getAttribute("aria-modal") === "true", "See all opens a modal dialog");
  eq(dlg.querySelectorAll(".hm-row").length, 6, "See all lists every row");
  doc.dispatchEvent(new window.KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
  yes(!$("hm-ov"), "Escape closes the sheet");
  yes(doc.activeElement === seeAll, "focus returns to the button that opened it");

  // hostile names are text
  await loadHomeWith({
    get_inbox: {ok: inbox([part("leave_approvals", [leaveRow("L9", HOSTILE, 2)]),
      part("goal_updates", []), part("attendance_fixes", []), part("shift_requests", []),
      part("policies", []), part("my_requests", [])])},
    notices_feed: {ok: feed([], 0, false)},
  });
  yes(!$("home-pending-body").querySelector("img, script") && $("home-pending-body").textContent.includes("<img src=x"),
      "a name written as <img onerror> is shown as text on the Pending card");

  // empty stays a short card
  await loadHomeWith({
    get_inbox: {ok: inbox(["leave_approvals", "goal_updates", "attendance_fixes", "shift_requests", "policies", "my_requests"].map(k => part(k, [])))},
    notices_feed: {ok: feed([], 0, false)},
  });
  yes($("home-pending-card").style.display !== "none", "an empty Pending card is not hidden");
  yes(/Nothing waiting on you\./.test($("home-pending-body").textContent) &&
      /Requests that need you, and policies to read, appear here\./.test($("home-pending-body").textContent), "the empty Pending sentences are as drawn");
  yes($("home-pending-chip").style.display === "none" && $("home-pending-foot").style.display === "none", "no chip and no footer when empty");
  yes(/No notices\./.test($("home-notices-body").textContent) &&
      /Messages from HR and management, and alerts about your work, appear here\./.test($("home-notices-body").textContent), "the empty Notices sentences are as drawn");
  yes($("home-notices-foot").style.display === "none", "no See all when there has never been a notice");

  // ── shift changes stay out; goal updates open the Team panel ─────────
  await loadHomeWith({
    get_inbox: {ok: inbox([part("leave_approvals", []),
      part("goal_updates", [goalRow("G1", "Charu Sethi", 6)]), part("attendance_fixes", []),
      part("shift_requests", [{name: "SR1", employee_name: "Imran Khan", from_date: "2026-11-09", to_date: "2026-11-09", shift_type: "B", action: "shift_request", waiting_since: iso(4)}]),
      part("policies", []), part("my_requests", [])])},
    notices_feed: {ok: feed([], 0, false)},
  });
  eq(rowsOf("home-pending-body").map(lines), ["Charu Sethi"], "a shift change row is left out of Pending (no screen decides it)");
  eq($("home-pending-chip").textContent, "1 waiting", "and the chip does not count it");
  const opened = [];
  const real = {g: window.gpOpenGoalDetail, k: window.pfOpenLog, s: window.switchPanel};
  window.gpOpenGoalDetail = (d, r) => opened.push(["goal", d, r]);
  window.pfOpenLog = (d, r) => opened.push(["kpi", d, r]);
  window.switchPanel = (n) => opened.push(["panel", n]);
  click(rowsOf("home-pending-body")[0]);
  eq(opened, [["goal", "GOAL-G1", "G1"]], "a goal update opens its goal drawer, on that update, where Approve and Reject are");
  opened.length = 0;
  await loadHomeWith({get_inbox: {ok: inbox([part("leave_approvals", []), part("goal_updates", [goalRow("K1", "Dinesh Pal", 2, "kpi")]),
    part("attendance_fixes", []), part("shift_requests", []), part("policies", []), part("my_requests", [])])}, notices_feed: {ok: feed([], 0, false)}});
  click(rowsOf("home-pending-body")[0]);
  eq(opened, [["kpi", "KPI-K1", "K1"]], "a KPI update opens the KPI log on that update");
  opened.length = 0;
  const noId = goalRow("G2", "Esha Ghosh", 2); delete noId.document;
  await loadHomeWith({get_inbox: {ok: inbox([part("leave_approvals", []), part("goal_updates", [noId]),
    part("attendance_fixes", []), part("shift_requests", []), part("policies", []), part("my_requests", [])])}, notices_feed: {ok: feed([], 0, false)}});
  click(rowsOf("home-pending-body")[0]);
  eq(opened, [["panel", "team"]], "a goal update with no goal id falls back to the Team panel");
  window.gpOpenGoalDetail = real.g; window.pfOpenLog = real.k; window.switchPanel = real.s;

  // ── Team goals on Home: three people, one goal each, then View all ───────────────────
  const by = {};
  for (let i = 0; i < 8; i++) by["E" + i] = {employee: {employee_name: "Person " + i}, goals: [{name: "g" + i, goal_name: "Goal", progress_pct: 10, trajectory: "On Track"}]};
  window.renderTeamGoals({available: true, by_employee: by});
  eq($("home-team-goals-list").querySelectorAll(".hg-member").length, 3, "Team goals shows three people");
  yes(/See your team of 8/.test($("home-team-goals-list").textContent) && !/View all/.test($("home-team-goals-list").textContent), "with a button that says it opens the team, not a goals list");
  window.renderTeamGoals({available: true, by_employee: {E0: by.E0}});
  yes(!/See your team/.test($("home-team-goals-list").textContent), "no button when everyone fits");

  // ── a CXO: counts by kind, no people ─────────────────────────────────
  window._roles.is_system_manager = true;
  await loadHomeWith({
    get_inbox: {ok: inbox([
      part("leave_approvals", [leaveRow("L1", "Anita Verma", 3)], 14),
      part("goal_updates", [goalRow("G1", "Charu Sethi", 6)], 9),
      part("attendance_fixes", [], 5), part("shift_requests", [], 3), part("policies", [], 1),
      part("my_requests", [], 2)])},
    notices_feed: {ok: feed([], 0, false)},
  });
  rows = rowsOf("home-pending-body");
  eq(rows.map(lines), ["Leave approvals", "Goal and KPI updates", "Attendance fixes", "Policies to read"],
     "a CXO sees one row per kind, most first");
  yes(!/Anita|Charu/.test($("home-pending-body").textContent), "a CXO's Pending names no person");
  yes(/14 waiting/.test(rows[0].textContent), "each row carries its count");
  eq($("home-pending-chip").textContent, "29 waiting", "the CXO chip adds the kinds shown");
  yes(/your queue/.test(rows[0].textContent) && !/across your companies/.test($("home-pending-body").textContent), "the CXO label says 'your queue'");
  window._roles.is_system_manager = false;

  // ── Notices: the card's number is the bell's ─────────────────────────
  const notes = [noteRow("N1", "A grooming red was marked on Mon 26 Oct."), noteRow("N2", HOSTILE), noteRow("N3", "Third")];
  await loadHomeWith({
    get_inbox: {ok: inbox([])},
    notices_feed: {ok: a => feed(a.see_all ? notes.concat([noteRow("N0", "Old one", true)]) : notes, 3, true)},
  });
  rows = rowsOf("home-notices-body");
  eq(rows.length, 3, "Notices lists the unread notices");
  eq($("home-notices-chip").textContent, "3 unread", "the chip says '3 unread'");
  eq($("notif-badge").textContent, "3", "the bell shows the same number");
  eq($("mob-notif-btn").getAttribute("aria-label"), "Notices, 3 unread", "the bell's accessible name carries the number");
  yes(!$("home-notices-body").querySelector("img, script") && $("home-notices-body").textContent.includes("<img src=x"),
      "a notice written as <img onerror> is shown as text on the card");

  // open one: the whole text, marked read through Frappe's own call
  ROUTES.mark_as_read = {ok: {}};
  click(rows[0]);
  dlg = doc.querySelector("#hm-ov [role=dialog]");
  yes(dlg && /A grooming red was marked on Mon 26 Oct\./.test(dlg.textContent), "tapping a notice opens it in a sheet");
  await settle(60);
  eq(callsTo("mark_as_read").map(c => c.args), [{docname: "N1"}], "it is marked read with Frappe's mark_as_read, by name");
  eq($("home-notices-chip").textContent, "2 unread", "the chip falls to 2");
  eq($("notif-badge").textContent, "2", "and so does the bell");
  eq(rowsOf("home-notices-body").length, 2, "the read notice leaves the card");
  click(dlg.querySelector("[data-hm=close]"));

  // the hostile one in the sheet, and See all and the bell
  click(rowsOf("home-notices-body")[0]);
  dlg = $("hm-sheet");
  yes(!dlg.querySelector("img, script") && dlg.textContent.includes("<img src=x"), "a hostile notice is text in the sheet too");
  click(dlg.querySelector("[data-hm=close]"));
  await settle(60);
  window.toggleNotifPanel();      // the bell
  await settle(60);
  dlg = $("hm-sheet");
  yes(dlg && /Notices, last 30 days/.test(dlg.textContent), "the bell opens the Notices sheet");
  yes([...dlg.querySelectorAll(".hm-row")].some(b => /Read/.test(b.textContent)), "the sheet marks read notices 'Read'");
  yes(!dlg.querySelector("img, script"), "no element is made from a notice in See all");
  eq(callsTo("notices_feed").pop().args, {see_all: 1}, "See all asks the same function with see_all=1");
  doc.dispatchEvent(new window.KeyboardEvent("keydown", {key: "Escape", bubbles: true}));

  // ── the leave sheet ──────────────────────────────────────────────────
  const leaveInbox = () => inbox([part("leave_approvals", [leaveRow("L1", "Anita Verma", 3), leaveRow("L2", "Bhavna Shah", 9)]),
    part("goal_updates", []), part("attendance_fixes", []), part("shift_requests", []), part("policies", []), part("my_requests", [])]);
  await loadHomeWith({get_inbox: {ok: leaveInbox()}, notices_feed: {ok: feed([], 0, false)}, action_leave: {ok: {status: "Approved"}}});
  rows = rowsOf("home-pending-body");
  eq(rows.map(lines), ["Bhavna Shah", "Anita Verma"], "two leave rows, oldest first");
  click(rows[0]);
  dlg = $("hm-sheet");
  yes(dlg && /Leave request/.test(dlg.textContent) && /Casual Leave/.test(dlg.textContent) && /3 days/.test(dlg.textContent) && /6–8 Nov/.test(dlg.textContent),
      "the sheet shows the name, 'Leave request', the type, the dates and the days");
  // decline needs a reason
  click($("hm-decline"));
  yes($("hm-reason").style.display !== "none" && $("hm-decline").textContent === "Send decline", "Decline asks for a reason and becomes 'Send decline'");
  yes($("hm-approve").style.display === "none", "Approve steps aside while declining");
  click($("hm-decline"));
  yes($("hm-why-e").style.display !== "none" && callsTo("action_leave").length === 0, "no reason, no decline: nothing is sent");
  eq($("hm-why").getAttribute("maxlength"), "140", "the reason field stops at 140 characters");
  $("hm-why").value = "Two people are away that week.";
  click($("hm-decline"));
  await settle(60);
  eq(callsTo("action_leave").map(c => c.args), [{leave_id: "L2", action: "reject", reason: "Two people are away that week."}], "Send decline calls action_leave with the reason");
  yes(!$("hm-ov"), "the sheet closes after the decision");
  eq(rowsOf("home-pending-body").map(lines), ["Anita Verma"], "the decided row leaves the card");
  eq($("home-pending-chip").textContent, "1 waiting", "and the chip follows");
  // approve sends no reason, and a double tap sends once
  click(rowsOf("home-pending-body")[0]);
  click($("hm-approve")); click($("hm-approve"));
  await settle(60);
  eq(callsTo("action_leave").slice(1).map(c => c.args), [{leave_id: "L1", action: "approve"}], "Approve sends two arguments, once even when tapped twice");
  yes(/Nothing waiting on you\./.test($("home-pending-body").textContent), "the last decision leaves the empty card");

  // ── a failed load says so and tries again ────────────────────────────
  await loadHomeWith({get_inbox: "drop", notices_feed: "drop"});
  await settle(80);
  yes($("home-pending-body").querySelector(".fail button"), "a failed Pending load shows a Try again button");
  yes($("home-notices-body").querySelector(".fail button"), "a failed Notices load shows a Try again button");
  ROUTES.get_inbox = {ok: leaveInbox()};
  click($("home-pending-body").querySelector(".fail button"));
  await settle(80);
  eq(rowsOf("home-pending-body").length, 2, "Try again loads the card");

  // ── coming back to Home after a minute asks again ─────────────────────
  const before = callsTo("get_inbox").length;
  window.hmRefreshIfStale();
  eq(callsTo("get_inbox").length, before, "a fresh Home is not asked for again");
  window.HM.at = Date.now() - 61000;
  window.hmRefreshIfStale();
  await settle(60);
  eq([callsTo("get_inbox").length, callsTo("notices_feed").length > 0], [before + 1, true], "a stale Home asks Pending and Notices again");

  // ── the grid: a lone last card spans the row ─────────────────────────
  const grid = $("home-grid");
  const shown = () => [...grid.children].filter(c => c.style.display !== "none");
  window.homeReflow();
  const odd = shown().length % 2 === 1;
  eq(grid.querySelectorAll(".hm-span2").length, odd ? 1 : 0, "reflow spans the last card only when the count is odd");
  const extra = doc.createElement("div"); extra.className = "card"; extra.id = "probe"; grid.appendChild(extra);
  window.homeReflow();
  eq(grid.querySelectorAll(".hm-span2").length, shown().length % 2 === 1 ? 1 : 0, "a card added changes which card spans");
  if (shown().length % 2 === 1) yes(grid.lastElementChild.classList.contains("hm-span2"), "the span is on the LAST visible card");
  extra.style.display = "none";
  window.homeReflow();
  eq(grid.querySelectorAll(".hm-span2").length, odd ? 1 : 0, "a hidden card drops out and the rest reflow");

  console.log(`\n### Home 076 DOM test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
