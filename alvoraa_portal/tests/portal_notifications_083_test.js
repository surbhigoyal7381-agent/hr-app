/* Slice 083: the notifications page, the bell on a laptop, and the one number,
   driven in jsdom against the real page and the real portal.js. The server is a
   stub; the markup, the script and the rules about what is drawn are real.

   Pin tests (a bad merge that drops the feature fails by name):
     - the page has an address: a VISIBLE nav item, so reload and Back work
     - the badge is work owed + unread notices, and is written in ONE place
     - the three chips send no request
     - five rows per group under All, with the TRUE total in the footer
     - tapping work owed sends nothing
     - "Mark all as read" exists in the notices group only, and is a POST
     - no setInterval, no polling, nothing in client storage

   Run: node alvoraa_portal/tests/portal_notifications_083_test.js \
          alvoraa_portal/alvoraa_portal/www/hrms-employee.html */
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const PAGE = process.argv[2];
const html = readPortalSource(PAGE);
const SOURCE = fs.readFileSync(
  path.join(__dirname, "..", "alvoraa_portal", "public", "js", "ess", "portal.js"), "utf8");

let pass = 0, fail = 0;
const ok = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };
const eq = (got, want, m) => (JSON.stringify(got) === JSON.stringify(want)
  ? ok(m) : bad(m + ": got <" + JSON.stringify(got) + "> want <" + JSON.stringify(want) + ">"));
const yes = (cond, m) => (cond ? ok(m) : bad(m));

const method = s => String(s).split(".").pop();
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
      CALLS.push({name, args: opts && opts.body ? JSON.parse(opts.body) : undefined,
                  method: (opts && opts.method) || "GET"});
      const h = ROUTES[name] === undefined ? {ok: {}} : ROUTES[name];
      if (h === "drop") return Promise.reject(new TypeError("Failed to fetch"));
      const v = typeof h.ok === "function" ? h.ok(CALLS[CALLS.length - 1].args || {}) : h.ok;
      return Promise.resolve({ok: true, status: 200, json: () => Promise.resolve({message: v})});
    };
    const call = (o) => {
      const name = method(o.method);
      CALLS.push({name, args: o.args || {}, method: "POST"});
      const h = ROUTES[name] === undefined ? {ok: {}} : ROUTES[name];
      setTimeout(() => {
        if (h === "drop") { o.always && o.always({}); return; }
        o.callback && o.callback({message: h.ok});
        o.always && o.always({});
      }, 0);
      return {status: 200};
    };
    w.frappe = {call, csrf_token: "x", boot: {}, ui: {}, _messages: {},
                utils: {escape_html: s => s}, msgprint: () => {}};
  },
});
const {window} = dom, doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));
const $ = id => doc.getElementById(id);
const click = el => el.dispatchEvent(new window.MouseEvent("click", {bubbles: true}));
const callsTo = n => CALLS.filter(c => c.name === n);
const text = id => ($(id) ? $(id).textContent : "");
const rows = sel => [...doc.querySelectorAll("#nf-body " + sel)];
const groups = () => rows(".nf-grp").length;
const headings = () => [...doc.querySelectorAll("#nf-body .nf-gh")].map(h => h.textContent.trim());
window.alert = () => {};

/* ── fixtures ─────────────────────────────────────────────────────────── */
function iso(daysAgo) {
  const d = new Date(); d.setDate(d.getDate() - daysAgo);
  const p = n => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + " 09:00:00";
}
const part = (key, rws, count, extra) => Object.assign(
  {key, count: count === undefined ? rws.length : count, rows: rws,
   shown: rws.length, cap: null, capped: false}, extra || {});
function inbox(parts) {
  const total = parts.reduce((n, p) => n + p.count, 0);
  const approvals = parts.filter(p => p.key !== "policies" && p.key !== "my_requests")
    .reduce((n, p) => n + p.count, 0);
  return {total, approvals_total: approvals, has_employee: true, parts};
}
const leaveRow = (name, who, ago) => ({name, employee_name: who, from_date: "2026-11-06",
  to_date: "2026-11-08", leave_type: "Casual Leave", total_days: 3, action: "leave",
  waiting_since: iso(ago)});
const fixRow = (name, who, ago) => ({name, employee_name: who, from_date: "2026-10-21",
  to_date: "2026-10-21", action: "attendance_fix", waiting_since: iso(ago)});
const polRow = (name, title, ago) => ({name, title, version: 2, action: "policy", waiting_since: iso(ago)});
const myRow = (name, title, ago) => ({name, kind: "my_leave", title, from_date: "2026-11-20",
  to_date: "2026-11-21", state: "Open", says: "Waiting for your manager", action: "my_leave",
  waiting_since: iso(ago)});
const noteRow = (name, txt, read) => ({name, kind: "alert", from: null, text: txt, link: null,
  when: "2026-10-27 16:10:00", read: read ? 1 : 0});
const feed = (items, unread, any, capped) => ({unread, capped: !!capped,
  any: any === undefined ? items.length > 0 : any, can_send: 0, items});

async function open083(routes) {
  ROUTES = Object.assign({}, BASE_ROUTES, routes);
  CALLS.length = 0;
  window.switchPanel("notifications", null);
  await settle(120);
}

(async () => {
  await settle(400);
  for (const fn of ["ntWorkOwed", "switchPanel", "mayOpenPanel"]) {
    if (typeof window[fn] !== "function") { bad(fn + " is not on the page"); process.exit(1); }
  }

  // ── US-2: the page has an address ────────────────────────────────────
  const nav = doc.querySelector('.nav-item[data-panel="notifications"]');
  yes(nav, "AC-4: a Notifications nav item is in the sidebar");
  yes(nav.style.display !== "none", "it is VISIBLE, which is the only thing that gives the page an address");
  yes(window.mayOpenPanel("notifications"),
      "AC-5: mayOpenPanel says yes, so a reload on #notifications comes back here");
  eq(nav.tagName, "BUTTON", "AC-6: it is a real button, reachable by Tab, not a div with an onclick");
  yes(/Notifications/.test(nav.textContent), "AC-4: and it carries the word, not an icon alone");
  const navItems = [...doc.querySelectorAll(".sidebar-nav .nav-item")];
  eq(navItems.indexOf(nav), 1, "AC-4: second in the rail, straight after Home");
  yes($("panel-notifications"), "the panel markup exists, so switchPanel cannot throw on this route");

  // ── US-1: the bell on a laptop ───────────────────────────────────────
  yes($("nf-bell") && $("nf-bell").tagName === "BUTTON", "AC-1: a desktop bell button is on the page");
  yes($("nf-bell-badge") && $("nf-bell-badge").classList.contains("notif-badge"),
      "AC-2: it carries a badge, and it is the same badge rule as the phone's");
  yes($("nf-bell").closest(".mob-header") === null,
      "the desktop bell is NOT inside the phone-only header that hid it before");

  // ── US-3, US-6: the page, and the one number ────────────────────────
  const ACPAY = {
    get_inbox: {ok: inbox([
      part("leave_approvals", [leaveRow("L1", "Anita Verma", 3), leaveRow("L2", "Bhavna Shah", 9)]),
      part("expense_approvals", [], 1),
      part("goal_updates", []),
      part("attendance_fixes", [fixRow("A1", "Dinesh Pal", 1)]),
      part("shift_requests", [], 3),
      part("policies", []),
      part("my_requests", [myRow("M1", "Casual leave", 4), myRow("M2", "Attendance fix", 6)]),
    ])},
    notices_feed: {ok: feed([noteRow("N1", "A grooming red was marked on Mon 26 Oct."),
                             noteRow("N2", "Diwali hours"), noteRow("N3", "Third")], 3, true)},
  };
  await open083(ACPAY);
  eq(text("nf-title"), "Notifications", "AC-7: the page says what it is");
  eq(text("nf-sub"), "Last 30 days", "AC-7: and names the window in plain words");
  eq($("notif-badge").textContent, "7", "AC-11: the badge is 4 work owed plus 3 unread notices");
  yes($("notif-badge").textContent !== "12" && $("notif-badge").textContent !== "9",
      "AC-11: and it is neither of the two wrong answers the payload offers");
  eq($("nf-bell-badge").textContent, "7", "both bells show the one number");
  eq($("sb-notif-badge").textContent, "7", "and so does the sidebar item");

  const heads = headings();
  eq(heads.length, 3, "AC-8: three groups");
  yes(/^4 waiting on you/.test(heads[0]), "AC-8: group 1 is what needs you, and names the count");
  yes(/^Notices/.test(heads[1]) && /3 unread/.test(heads[1]),
      "AC-8: group 2 is Notices with the unread count beside it as a tag, not inside the heading");
  yes(/Waiting on someone else/.test(heads[2]) && /not counted/.test(heads[2]),
      "AC-8: group 3 is named, and says it is not counted");

  // AC-19: the badge reconciles with the two headings on screen
  const workN = +heads[0].match(/^(\d+)/)[1];
  const unreadN = +heads[1].match(/(\d+) unread/)[1];
  eq(workN + unreadN, +$("notif-badge").textContent,
     "AC-19: the badge is exactly the two counted headings added up, and group 3 is in neither");

  // AC-10: a group 3 row is not a button
  const g3 = rows(".nf-grp")[2];
  eq([...g3.querySelectorAll(".hm-row")].map(r => r.tagName), ["DIV", "DIV"],
     "AC-10: a 'waiting on someone else' row is not a button - there is nothing to do to it");
  yes(!g3.querySelector("button"), "and it carries no dismiss, snooze, swipe or X");

  // AC-9: oldest first across kinds
  const g1rows = [...rows(".nf-grp")[0].querySelectorAll(".hm-row")];
  eq(g1rows.map(r => r.querySelector(".hm-l1").textContent),
     ["Bhavna Shah", "Anita Verma", "Dinesh Pal"], "AC-9: oldest waiting first, across kinds");

  // ── US-19: tapping work owed writes nothing ──────────────────────────
  const before = CALLS.length;
  const realSwitch = window.switchPanel;
  const went = [];
  window.switchPanel = (n) => went.push(n);
  click(g1rows[2]);                       // the attendance fix: navigates
  window.switchPanel = realSwitch;
  eq([CALLS.length, went.length], [before, 1],
     "AC-57: tapping work owed navigates and sends NOTHING");
  yes(!/dismiss|snooze|mark done/i.test($("nf-body").innerHTML),
      "AC-58: the page renders no dismiss, snooze or mark-done control on a work row");

  // a leave row opens the existing sheet, in place
  click(g1rows[0]);
  let dlg = $("hm-sheet");
  yes(dlg && /Leave request/.test(dlg.textContent) && /Casual Leave/.test(dlg.textContent),
      "AC-35: a leave row opens the EXISTING leave sheet, in place");
  click(dlg.querySelector("[data-hm=close]"));

  // ── US-4: the chips ──────────────────────────────────────────────────
  /* Re-queried on every use, never held: nfPaint rewrites the chip row, so a
     captured node is a detached node and a click on one reaches no listener. */
  const chipAt = i => [...doc.querySelectorAll("#nf-chips .nf-chip")][i];
  const chips = [...doc.querySelectorAll("#nf-chips .nf-chip")];
  eq(chips.map(c => c.textContent), ["All", "To do", "Unread notices"], "AC-13: three chips, in one row");
  eq(chips.map(c => c.tagName), ["BUTTON", "BUTTON", "BUTTON"], "AC-13: each is a real button");
  eq(chips.map(c => c.getAttribute("aria-pressed")), ["true", "false", "false"],
     "AC-13: All is pressed by default, and the state is spoken");
  yes(!chips.some(c => c.disabled), "AC-13: none is ever greyed out");
  yes(!chips.some(c => /\d/.test(c.textContent)), "AC-13: and no count sits inside a chip");
  yes($("nf-chips").getAttribute("role") === "group" && $("nf-chips").getAttribute("aria-label"),
      "the chips are a named group");

  const atChip = CALLS.length;
  click(chipAt(1));
  eq(CALLS.length, atChip, "AC-15: pressing a chip sends NO request - the rows are already here");
  eq(groups(), 1, "AC-14: To do shows group 1 alone");
  yes(/waiting on you/.test(headings()[0]), "and it is the work group");
  click(chipAt(2));
  eq(CALLS.length, atChip, "AC-15: still no request");
  eq(groups(), 1, "AC-14: Unread notices shows group 2 alone");
  eq(headings()[0].replace(/Mark all as read/, "").trim(), "3 unread notices",
     "AC-14: and under that chip the heading carries the number, because the list IS the unread ones");
  click(chipAt(0));
  eq(groups(), 3, "All brings the three groups back");

  // ── US-9: Mark all as read ───────────────────────────────────────────
  const markBtns = [...doc.querySelectorAll('#nf-body [data-hm="nf-mark"]')];
  eq(markBtns.length, 1, "AC-28: exactly one Mark all as read");
  eq(markBtns[0].closest(".nf-grp"), rows(".nf-grp")[1],
     "AC-29: and it is inside the NOTICES group - it can never reach a work row");
  ROUTES.mark_all_seen = {ok: {ok: 1}};
  click(markBtns[0]);
  await settle(60);
  const wrote = callsTo("mark_all_seen");
  eq(wrote.length, 1, "it calls mark_all_seen once");
  eq(wrote[0].method, "POST",
     "AC-34: as a POST. A no-argument call goes as a GET, and Frappe's rate limiter " +
     "skips anything that is not a POST - the write would be unlimited while looking limited");
  eq(wrote[0].args, {}, "with an arguments object carrying nothing: no doctype, no user, no filter");
  eq($("notif-badge").textContent, "4", "the badge falls to the work owed alone");
  eq(headings()[1].trim(), "Notices", "the unread tag is gone from the heading");
  eq([...doc.querySelectorAll('#nf-body [data-hm="nf-mark"]')].length, 0,
     "AC-28: and the control is ABSENT when nothing is unread, not greyed");

  // ── US-5 and US-8: five rows per group, and the TRUE total ───────────
  const many = [];
  for (let i = 0; i < 100; i++) many.push(noteRow("N" + i, "Notice " + i));
  await open083({
    get_inbox: {ok: inbox([part("policies", [polRow("P1", "Safety on the floor", 20)])])},
    notices_feed: {ok: feed(many, 150, true, true)},
  });
  const nGroup = rows(".nf-grp")[1];
  eq(nGroup.querySelectorAll(".hm-row").length, 5, "AC-16: five rows under All");
  const foot = nGroup.querySelector(".nf-foot").textContent;
  yes(/Showing 5 of 150/.test(foot),
      "AC-18: the footer's total is the feed's own TRUE count - never items.length, which says 100");
  yes(/See all 150 notices/.test(foot), "AC-16: and the button names it too");
  eq($("notif-badge").textContent, "99+", "above 99 the badge says 99+");
  click(nGroup.querySelector(".nf-foot button"));
  eq(groups(), 1, "AC-17: the footer button SETS THE CHIP - no new screen and no new address");
  eq(doc.querySelectorAll("#nf-chips .nf-chip")[2].getAttribute("aria-pressed"), "true",
     "and the chip it set is Unread notices");
  yes(/Showing the first 100 notices/.test($("nf-body").textContent),
      "AC-25: with the capped list saying so in words");

  // AC-18a: a capped WORK part says so, per part
  await open083({
    get_inbox: {ok: inbox([part("attendance_fixes",
      [fixRow("A1", "One", 2), fixRow("A2", "Two", 3)], 63, {shown: 50, cap: 50, capped: true})])},
    notices_feed: {ok: feed([], 0, true)},
  });
  yes(/Showing the first 50 of 63/.test($("nf-body").textContent),
      "AC-18a: a capped work part says how many of how many");

  // ── US-12: the empty states ──────────────────────────────────────────
  await open083({get_inbox: {ok: inbox([])}, notices_feed: {ok: feed([], 0, true)}});
  yes(/Nothing waiting on you, and no new notices\./.test($("nf-body").textContent),
      "AC-41: nothing at all, for somebody who has had notices before");
  await open083({get_inbox: {ok: inbox([])}, notices_feed: {ok: feed([], 0, false)}});
  yes(/Nothing here yet\./.test($("nf-body").textContent)
      && /We will put a number on the bell when something arrives\./.test($("nf-body").textContent),
      "AC-44: a first morning is told what the page is FOR, not shown a blank");
  await open083({
    get_inbox: {ok: inbox([])},
    notices_feed: {ok: feed([noteRow("N1", "Diwali hours")], 1, true)},
  });
  yes(/Nothing waiting on you\./.test(rows(".nf-grp")[0].textContent)
      && /Requests that need you, and policies to read, appear here\./.test(rows(".nf-grp")[0].textContent),
      "AC-42: work empty, notices not - the tick box is inside group 1");
  await open083({
    get_inbox: {ok: inbox([part("policies", [polRow("P1", "Safety", 2)])])},
    notices_feed: {ok: feed([], 0, true)},
  });
  yes(/You have read everything\./.test(rows(".nf-grp")[1].textContent),
      "AC-43: notices empty, work not - the tick box is inside group 2");

  // ── US-11: one call may fail alone ───────────────────────────────────
  await open083({
    get_inbox: {ok: inbox([part("policies", [polRow("P1", "Safety on the floor", 20)])])},
    notices_feed: "drop",
  });
  await settle(80);
  const before1 = $("notif-badge").textContent;
  yes(/Safety on the floor/.test(rows(".nf-grp")[0].textContent),
      "AC-37: the notices call failed and group 1 drew normally");
  const amber = rows(".nf-grp")[1].querySelector(".fail");
  yes(amber && /Could not load your notices\./.test(amber.textContent)
      && /Your work is shown below\. Nothing has been lost\./.test(amber.textContent),
      "AC-37: an amber box inside the notices group only, in those words");
  yes(amber.querySelector("[data-hm=nf-retry]"), "AC-37: with a Try again");
  yes(!doc.querySelector(".toast-wrap .toast, .gp-toast-wrap > *"),
      "AC-37: and no toast - nothing the person did went wrong");
  eq($("notif-badge").textContent, before1, "AC-37: the bell's number is left exactly as it was");

  ROUTES.notices_feed = {ok: feed([noteRow("N1", "Back again")], 1, true)};
  click(amber.querySelector("[data-hm=nf-retry]"));
  await settle(80);
  yes(/Back again/.test($("nf-body").textContent), "Try again loads the part that failed");

  await open083({get_inbox: "drop", notices_feed: "drop"});
  await settle(120);
  yes(/Could not load this page\./.test($("nf-body").textContent)
      && /Check your connection and try again\. Nothing has been lost\./.test($("nf-body").textContent),
      "AC-38: both calls failed - one amber box and no groups");
  eq(groups(), 0, "AC-38: and nothing is half-drawn");

  // ── US-14: the CXO ───────────────────────────────────────────────────
  window._roles.is_system_manager = true;
  await open083({
    get_inbox: {ok: inbox([
      part("leave_approvals", [leaveRow("L1", "Anita Verma", 3)], 214),
      part("attendance_fixes", [fixRow("A1", "Dinesh Pal", 1)], 63),
      part("policies", [polRow("P1", "Safety", 2)], 1),
    ])},
    notices_feed: {ok: feed([noteRow("N1", "Diwali hours")], 1, true)},
  });
  eq($("notif-badge").textContent, "4",
     "AC-49: a CXO's badge is three kinds plus one unread - 4, not 279");
  yes(/counts by kind/.test(headings()[0]), "AC-48: and the group says it is counts by kind");
  yes(!/Anita Verma|Dinesh Pal/.test(rows(".nf-grp")[0].textContent),
      "AC-48: a CXO's work group names no colleague");
  window._roles.is_system_manager = false;

  // ── nothing a person wrote becomes an element ───────────────────────
  await open083({
    get_inbox: {ok: inbox([part("leave_approvals", [leaveRow("L1", HOSTILE, 2)])])},
    notices_feed: {ok: feed([noteRow("N1", HOSTILE)], 1, true)},
  });
  yes(!$("nf-body").querySelector("img, script") && $("nf-body").textContent.includes("<img src=x"),
      "a name and a notice written as <img onerror> are shown as those characters");

  // ── US-20 and US-21: what the page must NOT do ──────────────────────
  /* The slice's own block, bounded at both ends: everything after it is
     somebody else's code and these are assertions about THIS slice. */
  /* From the OPENING of the block's own comment, so the comment stripper
     below sees a matched pair. */
  const nfFrom = SOURCE.lastIndexOf("/*", SOURCE.indexOf("Notifications, the page (slice 083)"));
  const nfTo = SOURCE.indexOf("Birthdays and anniversaries, My profile");
  yes(nfFrom > 0 && nfTo > nfFrom, "the slice's own block is where these assertions expect it");
  const nf = SOURCE.slice(nfFrom, nfTo);
  /* Comments stripped: these are assertions about what the CODE does, and a
     comment saying "nothing here touches localStorage" must not be what
     makes the assertion about localStorage fail. */
  const nfCode = nf.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
  yes(!/setInterval|requestAnimationFrame\s*\(\s*function\s+poll/.test(nfCode),
      "AC-64: no setInterval and no polling anywhere in the page's own code");
  yes(!/localStorage|sessionStorage|indexedDB|caches\./i.test(nfCode),
      "AC-59: the page writes nothing to client storage - 441 DTC logins share handsets");
  yes(!/frappe\.enqueue/.test(nfCode), "AC-65: no queue and no worker");
  yes(/#notifications|"notifications"/.test(SOURCE),
      "AC-63a: the route is a fixed word, with no employee id, document name or email in it");
  /* AC-12: ONE function writes the badge. Counted over the WHOLE file, not
     just this block, because the defect this guards against is a second writer
     somewhere else. */
  const writers = SOURCE.split("\n").filter(l => /notif-badge|nf-bell-badge|sb-notif-badge/.test(l)
                                                 && !/^\s*(\*|\/\*|\/\/)/.test(l));
  eq(writers.length, 1,
     "AC-12: exactly one line in portal.js names the badge elements, and it is the one " +
     "inside ntPaintBadge. A second place computing this number is the defect.");
  yes(!/ntPaintBadge\((?!\))/.test(SOURCE),
     "AC-12: and nothing passes it a number - it reads the two stored halves itself");
  yes(!/d\.total|approvals_total/.test(nfCode),
      "AC-11: the page never reads d.total or approvals_total, the two wrong answers");

  console.log("### Notifications 083 DOM test: " + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})();
