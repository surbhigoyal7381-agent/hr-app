/* Slice 076, Part C: the expense sheet in Pending, the decline reason on the
   employee's own claim, the Birthdays card, My profile's tick and the
   organisation switch - driven in jsdom against the real page and the real
   portal.js. The server is a stub; every save is checked by what it SENDS,
   and every refusal by the server's own words on screen.

   Pin tests (a bad merge that drops the feature fails by name):
     - an expense row says Review and opens the expense sheet
     - Approve sends {name, action: "approve"}; Send decline sends the reason
     - a refusal shows the server's words
     - the Birthdays card is absent while the switch is off
     - the tick sends only {value}; the switch asks before switching off

   Run: node alvoraa_portal/tests/portal_expense_birthdays_076_test.js alvoraa_portal/alvoraa_portal/www/hrms-employee.html */
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };
const eq = (got, want, m) => (JSON.stringify(got) === JSON.stringify(want) ? ok(m) : bad(m + ": got <" + JSON.stringify(got) + "> want <" + JSON.stringify(want) + ">"));
const yes = (cond, m) => (cond ? ok(m) : bad(m));

const method = s => String(s).split(".").pop();
const BASE_ROUTES = {get_checkin_status: {ok: {no_employee: 1}}, get_portal_context: {ok: {}},
  get_employee_dashboard: {ok: {no_employee: true}}};
let ROUTES = Object.assign({}, BASE_ROUTES);
const CALLS = [];
const HOSTILE = "<img src=x onerror=alert(1)>";
const refusal = text => ({refuse: text});

const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://grace.localhost/hrms-employee",
  beforeParse(w) {
    w.fetch = (url, opts) => {
      const name = method(url);
      CALLS.push({name, args: opts && opts.body ? JSON.parse(opts.body) : {}});
      const h = ROUTES[name] === undefined ? {ok: {}} : ROUTES[name];
      if (h.refuse) {
        const body = {exc_type: "ValidationError", _server_messages: JSON.stringify([JSON.stringify({message: h.refuse})])};
        return Promise.resolve({ok: false, status: 417, json: () => Promise.resolve(body)});
      }
      const v = typeof h.ok === "function" ? h.ok(CALLS[CALLS.length - 1].args) : h.ok;
      return Promise.resolve({ok: true, status: 200, json: () => Promise.resolve({message: v})});
    };
    const call = (o) => {
      const name = method(o.method);
      CALLS.push({name, args: o.args || {}});
      const h = ROUTES[name] === undefined ? {ok: {}} : ROUTES[name];
      setTimeout(() => { o.callback && o.callback({message: h.ok}); o.always && o.always({}); }, 0);
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
const toasts = () => [...doc.querySelectorAll("#toast-wrap .toast")].map(t => t.textContent);

function iso(daysAgo) {
  const d = new Date(); d.setDate(d.getDate() - daysAgo);
  const p = n => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + " 09:00:00";
}
const part = (key, rows, count) => ({key, count: count === undefined ? rows.length : count, rows});
const empty = ["leave_approvals", "goal_updates", "attendance_fixes", "shift_requests", "policies", "my_requests"];
function inbox(parts) {
  const have = parts.map(p => p.key);
  const all = parts.concat(empty.filter(k => !have.includes(k)).map(k => part(k, [])));
  return {total: all.reduce((n, p) => n + p.count, 0), approvals_total: 0, has_employee: true, parts: all};
}
const expRow = (name, who, ago, amount, note) => ({name, employee_name: who, expense_type: "Travel",
  expense_date: "2026-10-20", amount: amount || 2300, note: note === undefined ? "Taxi to the supplier visit" : note,
  waiting_since: iso(ago), action: "expense"});
const today = new Date();
const bday = (name, kind, day, years) => Object.assign({name, kind, day, month: today.getMonth() + 1}, years ? {years} : {});

async function loadHomeWith(routes) {
  ROUTES = Object.assign({}, BASE_ROUTES, routes);
  CALLS.length = 0;
  window.loadHome();
  await settle(120);
}
const rowsOf = id => [...$(id).querySelectorAll(".hm-row")];

(async () => {
  await settle(400);
  for (const fn of ["loadHome", "homeBirthdays", "hmExpenseSheet", "mpLoad", "bsLoad", "loadExpenses"]) {
    if (typeof window[fn] !== "function") { bad(fn + " is not on the page"); process.exit(1); }
  }

  // ── the expense row and its sheet ────────────────────────────────────
  await loadHomeWith({get_inbox: {ok: inbox([part("expense_approvals", [expRow("EC1", "Pooja Mishra", 8), expRow("EC2", HOSTILE, 1, 50, HOSTILE)])])},
    notices_feed: {ok: {unread: 0, any: false, items: []}}, birthdays_this_month: {ok: {on: 0}}});
  let rows = rowsOf("home-pending-body");
  eq(rows.length, 2, "both claims are in Pending");
  yes(/Pooja Mishra/.test(rows[0].textContent) && /Expense claim · ₹2,300 · Travel · waiting 8 days/.test(rows[0].textContent),
      "the row says whose, 'Expense claim', the amount, the type and how long it has waited");
  yes(/Review/.test(rows[0].textContent), "an expense row says Review");
  yes(!$("home-pending-body").querySelector("img") && $("home-pending-body").textContent.includes("<img src=x"), "a hostile name is text on the card");
  click(rows[0]);
  let dlg = $("hm-sheet");
  yes(dlg && $("hm-sh-t").textContent === "Expense claim", "the sheet is titled 'Expense claim'");
  yes(/₹2,300/.test(dlg.querySelector(".hm-amt").textContent), "the amount is in large type");
  yes(/Travel · 20 Oct/.test(dlg.textContent) && /Taxi to the supplier visit/.test(dlg.textContent), "the type, the date and the note");
  yes(/Waiting 8 days\. Approving passes it to accounts for payment\. You cannot take it back here\./.test(dlg.textContent),
      "the sheet says what approving does, as drawn");
  ROUTES.decide_expense = {ok: {name: "EC1", approval_status: "Approved"}};
  click($("hm-approve")); click($("hm-approve"));
  await settle(80);
  eq(callsTo("decide_expense").map(c => c.args), [{name: "EC1", action: "approve"}], "Approve sends {name, action: approve}, once even when tapped twice");
  yes(toasts().includes("Approved. Pooja Mishra's claim of ₹2,300 goes to accounts."), "the toast names the person and the amount");
  eq(rowsOf("home-pending-body").length, 1, "the decided claim leaves the card");

  // decline: a reason first, then exactly that reason is sent
  click(rowsOf("home-pending-body")[0]);
  dlg = $("hm-sheet");
  yes(!dlg.querySelector("img") && dlg.textContent.includes("<img src=x"), "a hostile note is text in the sheet");
  click($("hm-decline"));
  yes($("hm-decline").textContent === "Send decline" && $("hm-approve").style.display === "none", "Decline asks for a reason");
  click($("hm-decline"));
  yes($("hm-why-e").style.display !== "none" && callsTo("decide_expense").length === 1, "no reason, nothing is sent");
  $("hm-why").value = "  No receipt attached.  ";
  ROUTES.decide_expense = {ok: {name: "EC2", approval_status: "Rejected"}};
  click($("hm-decline"));
  await settle(80);
  eq(callsTo("decide_expense")[1].args, {name: "EC2", action: "decline", reason: "No receipt attached."}, "Send decline sends the trimmed reason");
  yes(toasts().some(t => /^Declined\. .* will see your reason\.$/.test(t)), "the decline toast");

  // a refusal shows the server's words, and the buttons come back
  await loadHomeWith({get_inbox: {ok: inbox([part("expense_approvals", [expRow("EC3", "Ravi Kumar", 2)])])},
    notices_feed: {ok: {unread: 0, any: false, items: []}}, birthdays_this_month: {ok: {on: 0}},
    decide_expense: refusal("This claim has already been decided.")});
  click(rowsOf("home-pending-body")[0]);
  click($("hm-approve"));
  await settle(80);
  yes(toasts().includes("This claim has already been decided."), "the server's refusal is shown in its own words");
  yes(!$("hm-approve").disabled, "the buttons are back on after a refusal");
  click($("hm-sheet").querySelector("[data-hm=close]"));

  // a CXO: one row for expenses, which opens the oldest claim
  window._roles = window._roles || {};
  window._roles.is_system_manager = true;
  await loadHomeWith({get_inbox: {ok: inbox([part("expense_approvals", [expRow("EC9", "Old Claim", 9)], 6)])},
    notices_feed: {ok: {unread: 0, any: false, items: []}}, birthdays_this_month: {ok: {on: 0}}});
  rows = rowsOf("home-pending-body");
  yes(rows.length === 1 && /Expense claims/.test(rows[0].textContent) && /6 waiting · opens the oldest/.test(rows[0].textContent),
      "a CXO sees 'Expense claims, 6 waiting', no names");
  click(rows[0]);
  yes($("hm-sheet") && /Old Claim/.test($("hm-sheet").textContent), "it opens the oldest claim's sheet");
  click($("hm-sheet").querySelector("[data-hm=close]"));
  window._roles.is_system_manager = false;

  // ── the employee's own claim shows the reason ────────────────────────
  ROUTES.get_expense_claims = {ok: {claims: [
    {name: "EC5", remark: null, posting_date: "2026-10-20", total_claimed_amount: 400, approval_status: "Rejected", decline_reason: HOSTILE},
    {name: "EC6", remark: "Lunch", posting_date: "2026-10-21", total_claimed_amount: 90, approval_status: "Approved", decline_reason: null}]}};
  window.loadExpenses();
  await settle(60);
  const list = $("expense-list");
  yes(list.textContent.includes("Declined: <img src=x onerror=alert(1)>") && !list.querySelector("img"), "a declined claim shows 'Declined: <reason>' as text");
  eq(list.querySelectorAll(".expense-why").length, 1, "only the declined claim carries a reason line");

  // ── Birthdays: absent when off ───────────────────────────────────────
  await loadHomeWith({get_inbox: {ok: inbox([])}, notices_feed: {ok: {unread: 0, any: false, items: []}}, birthdays_this_month: {ok: {on: 0}}});
  yes($("home-bday-card").style.display === "none", "the Birthdays card is absent while the switch is off");
  eq(callsTo("birthdays_this_month").map(c => c.args), [{see_all: 0}], "Home asks once for the card");

  const d = today.getDate();
  const card = [bday("Meera Kapoor", "birthday", d), bday("Sunil Yadav", "anniversary", Math.min(d + 1, 28), 5),
    bday(HOSTILE, "birthday", d), bday("One Year", "anniversary", d, 1), bday("Lata Devi", "birthday", Math.max(d - 1, 1))];
  await loadHomeWith({get_inbox: {ok: inbox([])}, notices_feed: {ok: {unread: 0, any: false, items: []}},
    birthdays_this_month: {ok: a => a.see_all ? {on: 1, total: 7, rows: card.concat([bday("Six", "birthday", 1), bday("Seven", "birthday", 2)])}
                                              : {on: 1, hidden: 0, total: 7, rows: card}}});
  yes($("home-bday-card").style.display !== "none", "the card shows when the switch is on");
  eq($("home-bday-h").textContent, "Birthdays and anniversaries this month", "its title, as drawn");
  rows = rowsOf("home-bday-body");
  eq(rows.length, 5, "five rows on the card");
  yes(/Meera Kapoor/.test(rows[0].textContent) && /Birthday/.test(rows[0].textContent) && /Today/.test(rows[0].textContent), "a birthday today says 'Today'");
  yes(/Work anniversary · 5 years/.test(rows[1].textContent), "an anniversary says the years");
  yes(/Work anniversary · 1 year(?!s)/.test(rows[3].textContent), "one year is 'year'");
  if (d > 1) yes(/earlier this month/.test(rows[4].textContent), "an earlier day is marked 'earlier this month'");
  yes(!$("home-bday-body").querySelector("img") && $("home-bday-body").textContent.includes("<img src=x"), "a hostile name is text");
  yes(!/19\d\d|20\d\d/.test($("home-bday-body").textContent), "no year anywhere on the card");
  yes(/Showing 5 of 7/.test($("home-bday-foot").textContent) && /See all 7/.test($("home-bday-foot").textContent), "See all 7 when there are more");
  click($("home-bday-foot").querySelector("button"));
  await settle(60);
  dlg = $("hm-sheet");
  yes(dlg && /Birthdays and anniversaries, /.test($("hm-sh-t").textContent) && dlg.querySelectorAll(".hm-row").length === 7,
      "See all opens the whole month");
  yes(/Only people in your own branch who share their dates\./.test(dlg.textContent), "and says whose dates they are");
  click(dlg.querySelector("[data-hm=close]"));

  await loadHomeWith({get_inbox: {ok: inbox([])}, notices_feed: {ok: {unread: 0, any: false, items: []}},
    birthdays_this_month: {ok: {on: 1, hidden: 0, total: 0, rows: []}}});
  yes(/No birthdays or anniversaries this month\./.test($("home-bday-body").textContent)
      && /People in your branch who share these dates appear here\./.test($("home-bday-body").textContent), "the empty sentences, as drawn");

  // ── My profile: the tick ─────────────────────────────────────────────
  yes([...$("mob-acct-menu").querySelectorAll("a")].some(a => /My profile/.test(a.textContent) && /my-profile/.test(a.getAttribute("onclick") || "")), "the account menu opens My profile");
  ROUTES.birthdays_this_month = {ok: {on: 1, hidden: 0, total: 0, rows: []}};
  ROUTES.set_birthday_hide = {ok: {hidden: 1}};
  window.switchPanel("my-profile", null);
  await settle(80);
  const tick = $("mp-share");
  yes(tick && tick.checked, "the tick is on by default");
  yes(/Show my birthday and work anniversary on Home to colleagues in my branch/.test($("mp-body").textContent), "the tick's words (with 'on Home', her decision 5)");
  yes(/They see your name, the day and month, and your years of service\. Never your age or birth year\. You can change this at any time\./.test($("mp-body").textContent),
      "the explanation, as drawn");
  tick.checked = false;
  tick.dispatchEvent(new window.Event("change", {bubbles: true}));
  await settle(60);
  eq(callsTo("set_birthday_hide").map(c => c.args), [{value: 1}], "unticking sends only {value: 1}, no employee");
  yes(toasts().includes("You are hidden from the birthdays and anniversaries card."), "and says so");
  ROUTES.set_birthday_hide = refusal("Your login is not linked to an active employee record. Ask HR to link it.");
  tick.checked = true;
  tick.dispatchEvent(new window.Event("change", {bubbles: true}));
  await settle(60);
  yes(!tick.checked && toasts().includes("Your login is not linked to an active employee record. Ask HR to link it."),
      "a refusal puts the tick back and shows the server's words");
  ROUTES.birthdays_this_month = {ok: {on: 0}};
  window.switchPanel("my-profile", null);
  await settle(80);
  yes(!$("mp-share") && /There is nothing to set here right now\./.test($("mp-body").textContent), "switch off: no tick, and the page says so");

  // ── Organisation settings: the switch ────────────────────────────────
  ROUTES.birthdays_switch_state = {ok: {on: 1, people: 412, changed_by: "Kavita Rao", changed_on: "2026-10-20"}};
  ROUTES.set_birthdays_switch = {ok: a => ({on: a.value, people: 412, changed_by: "Kavita Rao", changed_on: "2026-10-29"})};
  window.bsLoad();
  await settle(60);
  const sw = $("bs-btn");
  yes($("org-bday-card").style.display !== "none" && sw.getAttribute("role") === "switch" && sw.getAttribute("aria-checked") === "true", "HR sees the switch, on");
  eq($("bs-state").textContent, "On", "its state is a word, not only a colour");
  yes(/Last changed by Kavita Rao, 20 Oct 2026/.test($("bs-changed").textContent), "who last changed it, and when");
  click(sw);
  dlg = $("hm-sheet");
  yes(dlg && $("hm-sh-t").textContent === "Switch off birthdays and anniversaries?"
      && /Home will stop showing this card for everyone in the organisation \(412 people\)\./.test(dlg.textContent), "switching off asks first, with the head count");
  yes(/Keep it on/.test(dlg.textContent) && /Switch off/.test(dlg.querySelector("[data-bs=off]").textContent), "the two buttons, as drawn");
  eq(callsTo("set_birthdays_switch").length, 0, "nothing is sent until it is confirmed");
  click(dlg.querySelector("[data-bs=off]"));
  await settle(60);
  eq(callsTo("set_birthdays_switch").map(c => c.args), [{value: 0}], "Switch off sends {value: 0}");
  yes(sw.getAttribute("aria-checked") === "false" && $("bs-state").textContent === "Off", "the switch shows Off");
  click(sw);
  await settle(60);
  yes(!$("hm-sheet"), "switching on asks nothing");
  eq(callsTo("set_birthdays_switch").map(c => c.args)[1], {value: 1}, "switching on is one tap and sends {value: 1}");
  ROUTES.birthdays_switch_state = refusal("Only an HR Manager can change this.");
  window.bsLoad();
  await settle(60);
  yes($("org-bday-card").style.display === "none", "anyone the server refuses sees no switch");

  console.log(`\n### Expense and birthdays 076 DOM test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
