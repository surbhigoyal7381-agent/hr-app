/* Does the Positions page draw the organisation it is given, as Surbhi
 * approved it (prototype-v9, 21 Oct 2026)?
 *
 * WHY A NODE CHECK AND NOT A PYTHON TEST. The chart is built in the browser
 * from the rows `position_table` returns, so `bench run-tests` cannot reach
 * it. Each section names the feature it pins, so a bad merge that drops one
 * fails here. It runs in CI through alvoraa_portal/tests/portal_positions_test.js.
 *
 * The lines themselves - that no line suggests a box reports to anything
 * but its real parent - need a real layout, so they are checked in a real
 * browser by scripts/check_positions_connectors.js.
 *
 *     node scripts/check_positions_tree.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const PORTAL = path.join(__dirname, "..", "alvoraa_portal", "alvoraa_portal", "public",
                         "js", "ess", "portal.js");

/* ── a DOM just real enough ────────────────────────────────────────────── */
function stub(name) {
  return new Proxy(function () {}, {
    get: (t, p) => (p === Symbol.toPrimitive || p === "toString") ? () => "" :
                   (p === "length" ? 0 : stub(name + "." + String(p))),
    apply: () => stub(name + "()"),
    construct: () => stub("new " + name),
    set: () => true,
  });
}

function makeContext(values, opts) {
  opts = opts || {};
  const els = {};
  const el = (id) => (els[id] = els[id] || {
    id, value: values[id] || "", innerHTML: "", textContent: "",
    style: {}, checked: false, hidden: false, clientWidth: opts.width || 1440,
    focus() { ctx.__focused = id; }, setAttribute() {}, scrollIntoView() {},
  });
  ["pos-body", "pos-tiles", "pos-sub", "pos-asat", "pos-focusline", "pos-layer",
   "pos-reset-wrap", "pos-filters", "pos-filters-on", "pos-all-wrap", "pos-all-btn",
   "pos-f-branch", "pos-f-dept", "pos-f-role", "pos-f-open", "pos-add-btn",
   "pos-find", "pos-hits"].forEach(el);

  const ctx = { console: { log() {}, warn() {}, error() {} } };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx; ctx.top = ctx;
  for (const g of ["frappe", "localStorage", "sessionStorage", "navigator",
                   "location", "history", "L", "Chart", "html2canvas", "moment"])
    ctx[g] = stub(g);
  ctx.document = {
    // A focus target or a scroll target the page asks for by id is real
    // enough to record; anything else is absent.
    getElementById: (id) => (els[id] !== undefined ? els[id]
      : (/^pos-(b|r|g|sh)-|^pos-sh-t$|^pos-nomgr-box$|^pos-find$|^pos-hits$/.test(id) ? el(id) : null)),
    createElement: () => stub("el"),
    addEventListener() {}, removeEventListener() {},
    querySelector: () => null, querySelectorAll: () => [],
    body: { contains: () => true }, documentElement: stub("html"),
    activeElement: null,
  };
  ctx.addEventListener = () => {}; ctx.removeEventListener = () => {};
  ctx.matchMedia = () => ({ matches: !!opts.phone, addEventListener() {}, addListener() {} });
  ctx.getComputedStyle = () => stub("cs");
  ctx.requestAnimationFrame = () => 0;
  ctx.setTimeout = () => 0; ctx.setInterval = () => 0;
  ctx.clearTimeout = () => {}; ctx.clearInterval = () => {};
  ctx.confirm = () => true; ctx.alert = () => {}; ctx.prompt = () => "";
  ctx.fetch = () => new Promise(() => {});
  ctx.open = () => {};
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(PORTAL, "utf8"), ctx, { filename: PORTAL });
  ctx.__els = els;
  return ctx;
}

/* ── the organisations under test ────────────────────────────────────────── */
const TODAY = "2026-10-21";

function seat(id, title, parent, extra) {
  return Object.assign({
    id, title, reports_to: parent || "",
    reports_to_title: parent ? parent.replace(/^P-/, "") : "",
    branch: "Sector 34", department: "Sales", designation: "", grade: "",
    company: "DTC", status: "Active", key: false, created: "2026-10-14",
    seats: 1, filled: 1, open: 0, people: [{ employee: "E-" + id, name: "Holder of " + title,
                                             weight: 100, covering: false }],
  }, extra || {});
}

/* DTC's shape: one top with 5 team leads and 17 seats with nobody under them;
   every team lead's family is all seats with nobody under them. */
function dtc() {
  const rows = [seat("own", "Owner", "")];
  ["Admin", "Back Office", "FM", "Manager", "S-RE Manager"].forEach((t, i) => {
    rows.push(seat("tl" + i, t, "own", { branch: ["Ambala", "Sector 34", "Sector 22", "Delhi", "Noida"][i] }));
    for (let k = 0; k < 6 + i; k++) {
      rows.push(seat("tl" + i + "s" + k, t + " staff " + k, "tl" + i,
        { branch: ["Ambala", "Sector 34", "Sector 22", "Delhi", "Noida"][i] }));
    }
  });
  for (let k = 0; k < 17; k++) {
    rows.push(seat("leaf" + k, "Office seat " + String.fromCharCode(65 + k), "own",
      k === 3 ? { branch: "Sector 22" } : {}));
  }
  return rows;
}

/* DTC plus an 8-level line and a second line, for the window tests. */
function deep() {
  const rows = dtc();
  rows.push(seat("hoo", "Head of Operations", "own"));
  rows.push(seat("rm", "Regional Manager North", "hoo"));
  for (let i = 1; i <= 10; i++) {
    rows.push(seat("am" + i, "Area Manager " + (i < 10 ? "0" + i : i), "rm"));
    rows.push(seat("sm" + i, "Store Manager " + i, "am" + i));
  }
  rows.push(seat("fs", "Floor Supervisor", "sm1"));
  rows.push(seat("sl", "Section Lead", "fs"));
  ["Ring", "Chain", "Bangle", "Set", "Earring", "Cashier"].forEach((t) =>
    rows.push(seat("sl-" + t, t, "sl", { seats: 3, filled: 3 })));
  rows.push(seat("hos", "Head of Sales", "own"));
  rows.push(seat("sales", "Sales Lead", "hos"));
  rows.push(seat("sales1", "Sales One", "sales"));
  rows.push(seat("sales2", "Sales Two", "sales"));
  return rows;
}

const problems = [];
let checks = 0;
function ok(what, cond, detail) {
  checks++;
  if (!cond) problems.push(what + (detail ? " - " + detail : ""));
}
function count(html, needle) { return html.split(needle).length - 1; }

function load(rows, values, extra, opts) {
  const ctx = makeContext(values || {}, opts);
  ctx.POS.rows = rows;
  ctx.POS.may_edit = true;
  ctx.POS.today = TODAY;
  ctx.POS.may_see_leaving = true;
  ctx.POS.departments = {};
  Object.assign(ctx.POS, extra || {});
  ctx.posPaint();
  return ctx;
}
function body(ctx) { return ctx.__els["pos-body"].innerHTML; }
function layer(ctx) { return ctx.__els["pos-layer"].innerHTML; }

/* ── 1. home: the top open, its family in ONE group (US-1, v9) ─────────── */
{
  const ctx = load(dtc());
  const html = body(ctx);
  ok("the top seat is drawn and outlined", /class="pos-box root"[^>]*>[\s\S]{0,40}Owner/.test(html));
  ok("its 22 seats sit in ONE labelled group", count(html, 'class="pos-sibs"') === 1
     && html.includes("22 seats report to Owner"));
  ok("seats with nobody under them come first", html.indexOf("Nobody under them · 17") > -1
     && html.indexOf("Nobody under them · 17") < html.indexOf("Lead a team · 5"));
  ok("the five team leads come last", ["Admin", "Back Office", "FM", "Manager", "S-RE Manager"]
     .every((t) => html.indexOf('<div class="ti">' + t + "</div>") > html.indexOf("Lead a team · 5")));
  ok("no team is opened by itself", !html.includes("pos-strip"));
  ok("a team lead offers its family", /aria-expanded="false" onclick="posGroupFold\('c:own','tl3',false\)">Show the 9 below/.test(html));
  ok("there are no lines inside a group", !/pos-sibs[\s\S]*pos-kids/.test(html.split("pos-strip")[0]));
  ok("the old depth-folded tree is gone", !/POS_OPEN_DEPTH|posToggle\(|ocRender\(n, true, opts\)/.test(fs.readFileSync(PORTAL, "utf8")));
}

/* ── 2. a team opens below the whole group, one at a time ───────────────── */
{
  const ctx = load(dtc());
  ctx.posGroupFold("c:own", "tl3", false);
  let html = body(ctx);
  ok("the opened lead's family sits below the group under its strip",
     html.includes('class="pos-strip" data-parent="tl3"') && html.includes("Under <strong>Manager · Delhi</strong>")
     && html.indexOf("pos-strip") > html.lastIndexOf("Lead a team"));
  ok("the opened lead is outlined and its fold says Fold", /pos-box[^"]* opened" id="[^"]*" data-id="tl3"/.test(html)
     && html.includes(">Fold the 9 below<"));
  ok("its family of nine is a group of its own", html.includes("9 seats report to Manager"));
  ctx.posGroupFold("c:own", "tl4", false);
  html = body(ctx);
  ok("opening another lead in the same group folds the first",
     count(html, 'class="pos-strip"') === 1 && html.includes('data-parent="tl4"') && !html.includes('data-parent="tl3"'));
  ctx.posGroupFold("c:own", "tl4", true);
  ok("folding it leaves no strip", !body(ctx).includes("pos-strip"));
}

/* ── 3. five or fewer hang on the horizontal line ───────────────────────── */
{
  const rows = [seat("b", "Boss", "")];
  for (let i = 0; i < 5; i++) rows.push(seat("x" + i, "Leaf " + i, "b"));
  let html = body(load(rows));
  ok("a family of five is on the line, not in a group", html.includes('class="pos-kids"') && !html.includes("pos-sibs"));
  rows.push(seat("x5", "Leaf 5", "b"));
  html = body(load(rows));
  ok("a family of six is a group", html.includes("6 seats report to Boss") && !html.includes('class="pos-kids"'));
}

/* ── 4. counts on every box add up (US-6, SEC-1 b) ─────────────────────── */
{
  const rows = dtc();
  rows.find((r) => r.id === "tl3s1").open = 1;
  rows.find((r) => r.id === "tl3s2").people[0].leaving = "2026-11-30";
  const html = body(load(rows));
  ok("the top's roll-up counts every seat under it",
     html.includes((rows.length - 1) + " seats below · " + (rows.length - 1) + " people · 1 to fill · 1 leaving"));
  ok("a team lead's roll-up counts its own family", html.includes("9 seats below · 9 people · 1 to fill · 1 leaving"));
  const cut = dtc().filter((r) => r.id !== "tl0s0");
  ok("a child outside the reader's rows is not counted", body(load(cut)).includes((cut.length - 1) + " seats below"));
}

/* ── 5. Open every level, and back ──────────────────────────────────────── */
{
  const ctx = load(deep());
  ctx.posToggleAll();
  let html = body(ctx);
  ok("every level opens, the first team of each group", html.includes('data-parent="tl0"') && html.includes("Admin staff 0"));
  ctx.posGroupFold("c:own", "hoo", false);
  html = body(ctx);
  ok("one team per group: choosing another shows its line all the way down",
     !html.includes('data-parent="tl0"') && html.includes(">Section Lead<") && html.includes("6 seats report to Section Lead"));
  ok("the button says how to fold back", ctx.__els["pos-all-btn"].textContent === "Fold back to two levels");
  ctx.posToggleAll();
  ok("folding back returns home", !body(ctx).includes("pos-strip")
     && ctx.__els["pos-all-btn"].textContent === "Open every level");
}

/* ── 6. a filter greys, and opens the path to every match (v9) ──────────── */
{
  const ctx = load(dtc(), { "pos-f-branch": "Noida" });
  const html = body(ctx);
  ok("the path to the match opens", html.includes('data-parent="tl4"') && html.includes("Under <strong>S-RE Manager · Noida"));
  ok("a seat that does not match is greyed, not dropped", /class="pos-box dim"[^>]*>[\s\S]{0,40}Office seat A/.test(html));
  ok("the filters say they are on", ctx.__els["pos-filters-on"].textContent === " (on)"
     && ctx.__els["pos-reset-wrap"].style.display === "");
  ok("nothing matching says what to do", body(load(dtc(), { "pos-f-branch": "Nowhere" })).includes("No seat matches those filters."));
}

/* ── 7. the list (US-15) ────────────────────────────────────────────────── */
{
  const ctx = load(dtc(), { "pos-f-branch": "Ambala" });
  ctx.POS.view = "list"; ctx.posPaint();
  const html = body(ctx);
  ok("the list drops what does not match", !html.includes("Office seat A") && html.includes("Admin staff 0"));
  ok("the caption counts", /\d+ of \d+ seats/.test(html));
  ok("the columns are as drawn", ["Seat", "Reports to", "Branch", "Department", "Who is in it",
     "Filled", "To fill"].every((c) => html.includes(">" + c + "<")));
  ok("no Open every level in the list", ctx.__els["pos-all-wrap"].style.display === "none");
}

/* ── 8. a loop neither hangs nor swallows a seat; a deep chain is cut ────── */
{
  const looped = [seat("P-A", "Loop One", "P-B"), seat("P-B", "Loop Two", "P-A"), seat("P-Fine", "Normal Seat", "")];
  const html = body(load(looped));
  ok("a loop is named as the problem it is", html.includes("report in a circle") && html.includes("Loop One"));
  ok("the rest of the chart still draws", html.includes(">Normal Seat<"));
  const chain = [];
  for (let i = 0; i < 60; i++) chain.push(seat("L" + i, "Level " + i, i ? "L" + (i - 1) : ""));
  const c2 = load(chain); c2.posToggleAll();
  ok("a chain deeper than makes sense says so", body(c2).includes("deeper than makes sense"));
}

/* ── 9. every reader opens a seat; only an editor changes it (US-11) ────── */
{
  const ctx = load(dtc(), {}, { may_edit: false });
  ok("a box opens the seat sheet for anyone", body(ctx).includes("onclick=\"posSeatSheet('tl0')\""));
  ctx.posSeatSheet("tl0");
  const sheet = layer(ctx);
  ok("the sheet is a dialog with its heading", sheet.includes('role="dialog"') && sheet.includes('aria-modal="true"')
     && sheet.includes(">Admin</h2>") && sheet.includes("reports to Owner · Sector 34"));
  ok("a reader gets no Change", !sheet.includes("Change this seat") && sheet.includes("Show it on the chart"));
  const ed = load(dtc());
  ed.posSeatSheet("tl0");
  ok("an editor gets Change this seat", layer(ed).includes("Change this seat"));
}

/* ── 10. a seat whose parent is out of view; several tops (K7, X-7) ─────── */
{
  const ctx = load([seat("O", "Area Manager", "P-Gone"), seat("K", "Clerk", "O")]);
  ok("a top above the reader's view is marked", body(ctx).includes("reports above your view"));
  ok("the subtitle says it is their part", ctx.__els["pos-sub"].textContent.includes("Your part of the organisation: Area Manager"));
  const h = body(load([seat("X1", "Store A", "P-Gone"), seat("X2", "Store B", "P-Gone")]));
  ok("several tops are all drawn", h.includes(">Store A<") && h.includes(">Store B<"));
}

/* ── 11. by branch and by department ───────────────────────────────────── */
{
  const rows = [seat("t5", "Director", "", { branch: "Ambala", department: "Head" }),
                seat("c1", "Cashier", "t5", { branch: "Ambala" }),
                seat("c2", "Cashier", "t5", { branch: "Noida" }),
                seat("nb", "Floating Seat", "t5", { branch: "", department: "" })];
  const ctx = load(rows);
  ctx.posSetView("branch");
  let html = body(ctx);
  ok("branches are the top level, closed, with their counts", html.includes(">Ambala<") && html.includes("2 seats · 2 people")
     && html.includes("Select to open") && !html.includes(">Director<"));
  ok("a seat with no branch is named, last", html.indexOf(">No branch<") > html.indexOf(">Noida<"));
  ctx.posFold("h:Ambala", 1);
  html = body(ctx);
  ok("opening a branch shows its seats", html.includes(">Director<") && html.includes("Select to fold"));
  const dctx = load([seat("d1", "Analyst", "", { department: "Payroll - X" }),
                     seat("d2", "Clerk", "", { department: "Accounts - X" })], {}, { departments: {
    "Payroll - X": { parent: "Finance - X", head: null }, "Accounts - X": { parent: "Finance - X", head: "Asha Head" },
    "Finance - X": { parent: null, head: null } } });
  dctx.posSetView("department");
  dctx.posFold("h:Finance - X", 1);
  html = body(dctx);
  ok("departments nest, ancestors built", html.includes(">Finance<") && html.includes(">Payroll<") && html.includes("Asha Head"));
}

/* ── 12. the three filters narrow each other (existing) ────────────────── */
{
  const mix = [seat("h", "Head", "", { branch: "Ambala", designation: "Head" }),
               seat("c", "Clerk", "h", { branch: "Ambala", designation: "Clerk" }),
               seat("d", "Driver", "h", { branch: "Noida", designation: "Driver" })];
  const ctx = load(mix, { "pos-f-branch": "Ambala" });
  const roles = ctx.__els["pos-f-role"].innerHTML;
  ok("picking a branch narrows the job roles", roles.includes("Clerk") && !roles.includes("Driver"));
  ok("the branch list does not narrow itself", ctx.__els["pos-f-branch"].innerHTML.includes("Noida"));
}

/* ── 13. tiles, and leaving only where the server allowed it (SEC-4, X-1) ── */
{
  const rows = dtc();
  rows.find((r) => r.id === "tl4s2").people[0].leaving = "2026-11-30";
  Object.assign(rows.find((r) => r.id === "tl1s0"), { open: 1, filled: 0, people: [] });
  const ctx = load(rows);
  const tiles = ctx.__els["pos-tiles"].innerHTML;
  ok("the seats tile counts seats and people", tiles.includes(rows.length + " seats") && tiles.includes("people in them"));
  ok("the to-fill tile shows those seats", tiles.includes("1 to fill") && tiles.includes("Show these seats"));
  ok("the leaving tile counts the leaver", tiles.includes("1 leaving") && tiles.includes("in the next 60 days"));
  ok("the Show filter offers leaving", ctx.__els["pos-f-open"].innerHTML.includes("Only seats where somebody is leaving"));
  const hidden = load(dtc(), {}, { may_see_leaving: false });
  ok("a reader who may not see leavers gets no leaving tile or filter",
     !hidden.__els["pos-tiles"].innerHTML.includes("leaving") && !hidden.__els["pos-f-open"].innerHTML.includes("leaving"));
  ok("nothing to fill says so", load([seat("o", "Only", "")]).__els["pos-tiles"].innerHTML.includes("Every seat is filled"));
}

/* ── 14. people in no seat and with no manager (US-12, US-27; X-2) ──────── */
function unseated() {
  const out = [];
  for (let i = 0; i < 6; i++) out.push({ employee: "U" + i, name: "Pitampura person " + i, job_role: "RSO",
    branch: "DTC Pitampura", joined: "2026-10-01", no_manager: i < 2 });
  out.push({ employee: "U9", name: "Noida person", job_role: "Admin", branch: "Noida", joined: "2025-01-01", no_manager: false });
  return out;
}
{
  const rows = dtc();
  rows.find((r) => r.id === "tl4s0").designation = "Admin";
  rows.push(seat("pit", "Floor Manager", "tl3", { branch: "DTC - PITAMPURA" }));
  const ctx = load(rows, {}, { unseated: unseated(), active_people: 40, may_edit_employee: true });
  const tiles = ctx.__els["pos-tiles"].innerHTML;
  ok("HR gets the two people tiles", tiles.includes("7 in no seat") && tiles.includes("2 no manager"));
  const html = body(ctx);
  const css = fs.readFileSync(path.join(__dirname, "..", "alvoraa_portal", "alvoraa_portal", "public", "css", "ess", "panels.css"), "utf8");
  ok("the no-manager box is pinned to the chart's top-right corner, outside the tree (v10)",
     html.includes('class="pos-br pos-nomgr-slot"') && /\.pos-chart > \.pos-nomgr-slot\{position:absolute;top:0;right:0\}/.test(css));
  ok("a group's columns follow the frame (v10)", /repeat\(var\(--cols\),208px\)/.test(css)
     && /function posFitColumns/.test(fs.readFileSync(PORTAL, "utf8")));
  ok("the no-manager box is dashed and amber", html.includes('class="pos-box dashed amber" id="pos-nomgr-box"')
     && html.includes("Not in any seat, and no manager on their record") && html.includes("Needs a manager"));
  ctx.posNoMgrSheet();
  let sh = layer(ctx);
  ok("its sheet lists them with Set manager", sh.includes("No reporting manager · 2 people") && sh.includes("/app/employee/U0"));
  ok("it does not claim nobody approves their leave (X-5)", !sh.includes("approves their leave"));
  ctx.posUnseatedSheet();
  sh = layer(ctx);
  ok("the in-no-seat sheet counts, groups and matches", sh.includes("7 of 40 active people hold no seat")
     && sh.includes("Most joined in the last two months.") && sh.includes("DTC Pitampura · 6")
     && sh.includes("1 Admin · matching seat:") && sh.includes("6 RSO · no matching seat"));
  ok("a look-alike branch record is named", sh.includes("use a second branch record, &quot;DTC - PITAMPURA&quot;"));
  ctx.posSetView("branch");
  ok("the look-alike branch box carries its chip", body(ctx).includes("Second branch record for DTC Pitampura"));
  const owner = load(dtc(), {}, { may_edit: false });
  ok("a reader without HR scope gets no people tiles and no box", !owner.__els["pos-tiles"].innerHTML.includes("no seat")
     && !body(owner).includes("pos-nomgr-box"));
}

/* ── 15. nothing of slice 065 (AC-81) ───────────────────────────────────── */
{
  const ctx = load(dtc(), {}, { unseated: unseated(), active_people: 40 });
  ctx.posToggleAll();
  const all = body(ctx) + ctx.__els["pos-tiles"].innerHTML + ctx.__els["pos-f-open"].innerHTML;
  ok("no replacement-plan word or control anywhere", !/replacement|planned|Plan a/i.test(all));
}

/* ── 16. the records chips (US-13, US-14; SEC-5, X-3) ───────────────────── */
async function recordsChecks() {
  const rows = dtc();
  const mism = ["tl1s0", "tl1s1", "leaf5"].map((s) => ({ employee: "E-" + s, employee_name: "x", position: s,
    parent_position: "x", chart_says: "x", chart_says_name: "x", reports_to_says: "E-leaf0", reports_to_says_name: "Holder" }));
  const mixed = [{ position: "tl1", manager: "E-tl1", manager_name: "Holder of Back Office", manager_position: "tl1", count: 28 },
                 { position: "tl1", manager: "E-leaf0", manager_name: "CFO", manager_position: "leaf0", count: 6 },
                 { position: "tl1", manager: "E-own", manager_name: "Owner person", manager_position: "own", count: 2 }];
  const ctx = load(rows, {}, { unseated: [], records: { mismatches: mism, mixed: mixed } });
  const html = body(ctx);
  ok("a seat others name as manager on record carries the chip", html.includes("3 report here on their records"));
  ok("a pooled seat says it holds the people of 3 managers", html.includes("Holds people of 3 managers"));
  ctx.posSeatSheet("leaf0");
  let sh = layer(ctx);
  ok("its sheet explains, seat by seat", sh.includes("3 people report to this person on their employee records")
     && sh.includes("so nobody shows under this box") && sh.includes("To fix it, open each seat"));
  ctx.posSeatSheet("tl1");
  ok("the pooled sheet names each manager", layer(ctx).includes("28 report to Holder of Back Office, who is in this seat too"));

  let calls = 0;
  const hr = makeContext({});
  hr.gpFetch = async (m) => { calls++; return m.endsWith("position_table")
    ? { rows: dtc(), as_at: TODAY, unseated: [], active_people: 1 } : { mismatches: [], mixed: [] }; };
  await hr.posLoad();
  await new Promise((r) => setImmediate(r));
  ok("HR's page makes the records call once per load", calls === 2, calls + " calls");
  calls = 0;
  const owner = makeContext({});
  owner.gpFetch = async (m) => { calls++; return m.endsWith("position_table") ? { rows: dtc(), as_at: TODAY } : {}; };
  await owner.posLoad();
  await new Promise((r) => setImmediate(r));
  ok("a reader without HR scope never makes it", calls === 1, calls + " calls");
}

/* ── 17. switching views forgets the old view's open families ──────────────
   The approved prototype crashed on: open Delhi, By branch, Open every level -
   the old view's open-team choice was kept and looked for in the wrong tree. */
{
  const ctx = load(dtc());
  let error = null;
  try {
    ctx.posGroupFold("c:own", "tl3", false);
    ctx.posSetView("branch");
    ctx.posToggleAll();
  } catch (e) { error = e; }
  ok("open a team, By branch, Open every level: no error", !error, error && error.message);
  ok("and the old view's open team is forgotten", Object.keys(ctx.POS.copen).length === 0 || !ctx.POS.copen["c:own"]);
  ok("the branch view draws", body(ctx).includes("pos-box"));
  // Even a stale choice cannot draw another group's family in this one.
  const stale = load(dtc());
  stale.POS.copen = { "c:own": "not-a-lead-here" };
  stale.posPaint();
  ok("a choice that is not one of this group's leads is ignored", !body(stale).includes('data-parent="not-a-lead-here"'));
  // Every view after every kind of open state.
  const views = ["reporting", "branch", "department", "list"];
  let bad = [];
  views.forEach((from) => views.forEach((to) => {
    const c = load(deep(), {}, { unseated: [], active_people: 1 });
    try {
      c.posSetView(from);
      c.posToggleAll();
      if (from === "reporting") { c.posGroupFold("c:own", "tl3", false); c.posFold("hoo", 1); }
      c.posSetView(to);
      c.posToggleAll();
      c.posSetView(from);
    } catch (e) { bad.push(from + " -> " + to + ": " + e.message); }
  }));
  ok("every view switch after any open state draws without an error", !bad.length, bad.join(" | "));
}

/* ── 19. Find, in the browser only (US-7, SEC-3) ───────────────────────── */
{
  const ctx = load(deep(), {}, { unseated: [{ employee: "U1", name: "Pitampura person", job_role: "RSO",
    branch: "DTC Pitampura", joined: "2026-10-01", no_manager: true }], active_people: 9 });
  let calls = 0;
  ctx.gpFetch = async () => { calls++; return {}; };
  ctx.fetch = () => { calls++; return new Promise(() => {}); };
  const type = (q) => { ctx.__els["pos-find"].value = q; ctx.posFindInput(); return ctx.__els["pos-hits"].innerHTML; };
  ok("one letter shows nothing", type("S") === "");
  let hits = type("Section");
  ok("a seat is found with its fill", hits.includes("Section Lead") && hits.includes("Sector 34 · 1 of 1 filled"));
  hits = type("Holder of Ring");
  ok("a person is found with their seat", hits.includes("Holder of Ring") && hits.includes("Ring · Sector 34"));
  hits = type("staff");
  ok("past twelve it says how many more", /\d+ more\. Type more of the name\./.test(hits));
  ok("HR's Find finds a person in no seat", type("Pitampura").includes("In no seat yet · RSO · DTC Pitampura"));
  ok("nothing found says so", type("zzq").includes("No seat or person called that."));
  ok("typing never calls the server", calls === 0, calls + " call(s)");
  ctx.posFindKey({ key: "Escape" });
  ok("Escape empties the field and the list", ctx.__els["pos-find"].value === "" && ctx.__els["pos-hits"].innerHTML === "");
  ctx.posSetView("list");
  type("Holder of Section Lead");
  ctx.posFindPick(0);
  const html = body(ctx);
  ok("a pick from the List switches to Reporting lines", ctx.POS.view === "reporting");
  ok("the path to the pick opens and it is outlined",
     html.includes('data-parent="hoo"') && /class="pos-box[^"]* focus"[^>]*data-id="sl"/.test(html));
  ok("the focus line names who and where", ctx.__els["pos-focusline"].innerHTML.includes("Holder of Section Lead")
     && ctx.__els["pos-focusline"].innerHTML.includes("in Section Lead · Sector 34"));
  ctx.posUnfocus();
  ok("Clear removes the outline", !/ focus"/.test(body(ctx)));
  const owner = load(dtc(), {}, { may_edit: false });
  owner.__els["pos-find"].value = "Pitampura"; owner.posFindInput();
  ok("a reader without HR scope never finds a person in no seat", !owner.__els["pos-hits"].innerHTML.includes("In no seat"));
}

/* ── 20. the phone: one level at a time (US-16, v9) ─────────────────────── */
{
  const ctx = load(dtc(), {}, { unseated: [{ employee: "U1", name: "P", job_role: "RSO", branch: "X",
    joined: "2026-10-01", no_manager: true }], active_people: 9 }, { phone: true, width: 390 });
  let html = body(ctx);
  ok("no chart on a phone", !html.includes("pos-chartwrap") && html.includes("pos-outline"));
  ok("it starts at the top with a hint", html.includes("Top of the organisation. Tap a row to see what is under it."));
  ok("the top seat is a row with a way down", html.includes("posDown('own')") && html.includes("&rsaquo;</span></button>"));
  ok("HR gets the dashed No reporting manager row", html.includes('class="pos-orow dashed amber" id="pos-nomgr-row"')
     && html.includes("1 people · not in any seat"));
  ctx.posDown("own");
  html = body(ctx);
  ok("going down shows the seat's card and its rows", html.includes('class="here"') && html.includes("Who is in this seat")
     && html.includes("Up one level") && html.includes("posDown('tl0')") && html.includes("posSeatSheet('leaf0')"));
  ok("no group on a phone - every seat is a row", !html.includes("pos-sibs"));
  ctx.posTrailUp();
  ok("Up one level goes back", body(ctx).includes("Top of the organisation."));
  ctx.posPick("tl3s2");
  ok("a Find pick on a phone opens the outline at the parent, row outlined",
     ctx.POS.trail.join(">") === "own>tl3" && / focus"/.test(body(ctx)));
}

/* ── 18. deleting a seat (slice 061, kept) ──────────────────────────────── */
async function deleteChecks() {
  const src = fs.readFileSync(PORTAL, "utf8");
  ok("the Delete button follows the server's may_delete",
     /pos-delete-btn[\s\S]{0,120}\(r && POS\.may_delete\)/.test(src));

  function deleteContext(mayDelete, answer) {
    const ctx = makeContext({});
    ctx.__els["pos-e-name"] = { id: "pos-e-name", value: "tl0" };
    const toasts = [];
    const opened = new Set();
    const cls = (id) => ({ add: () => opened.add(id), remove: () => opened.delete(id),
                          contains: () => opened.has(id) });
    for (const id of ["pos-delete", "pos-editor"])
      ctx.__els[id] = { id, style: {}, classList: cls(id) };
    for (const id of ["pos-delete-text", "pos-delete-go", "pos-delete-keep", "pos-delete-btn", "pos-delete-err"])
      ctx.__els[id] = { id, style: {}, textContent: "", disabled: false, hidden: false, focus() {} };
    ctx.__els["toast-wrap"] = { appendChild: (t) => toasts.push(t) };
    ctx.document.createElement = () => ({ className: "", textContent: "", remove() {} });
    ctx.POS.rows = dtc();
    ctx.POS.may_delete = mayDelete;
    ctx.posLoad = async () => {};
    ctx.gpFetch = async () => { if (answer instanceof Error) throw answer; return answer; };
    return { ctx, toasts, opened };
  }
  {
    const t = deleteContext(false);
    t.ctx.posAskDelete();
    ok("without the Delete right nothing opens", !t.opened.has("pos-delete"));
  }
  {
    const t = deleteContext(true, { ok: true });
    t.ctx.posAskDelete();
    ok("the confirm opens", t.opened.has("pos-delete"));
    ok("and names the seat", t.ctx.__els["pos-delete-text"].textContent.includes("Admin"));
    t.opened.add("pos-editor");
    await t.ctx.posDelete();
    ok("a deleted seat closes both dialogs",
       !t.opened.has("pos-delete") && !t.opened.has("pos-editor"));
    ok("and says so", t.toasts.length === 1 && t.toasts[0].textContent.includes("was deleted"));
  }
  {
    const said = "Admin still has people in it. Take them out of the seat first.";
    const t = deleteContext(true, new Error(said));
    t.ctx.posAskDelete();
    await t.ctx.posDelete();
    const why = t.ctx.__els["pos-delete-err"];
    ok("a refusal shows the server's own words inside the dialog",
       why.textContent === said && why.hidden === false);
    ok("the dialog stays open so the reason can be read", t.opened.has("pos-delete"));
    ok("it does not rely on a toast that vanishes", t.toasts.length === 0);
    ok("there is no Delete button left to press for a refused seat",
       t.ctx.__els["pos-delete-go"].hidden === true);
    ok("and the way out is called Close",
       t.ctx.__els["pos-delete-keep"].textContent === "Close");
    t.ctx.posAskDelete();
    ok("asking again starts clean: reason hidden, Delete back",
       t.ctx.__els["pos-delete-err"].hidden === true
       && t.ctx.__els["pos-delete-go"].hidden === false
       && t.ctx.__els["pos-delete-keep"].textContent === "Keep it");
  }
}

recordsChecks().then(deleteChecks).then(() => {
  if (problems.length) {
    console.error("positions: " + problems.length + " problem(s)");
    problems.forEach((p) => console.error("  FAIL " + p));
    process.exit(1);
  }
  console.log("positions: " + checks + " checks - big families in one group, one team open at a time, "
              + "counts that add up, filters that grey, view switches that do not crash, "
              + "loops and deep chains survive, a seat is deleted only when the server says so");
});
