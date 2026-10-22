/* Does the Positions structure view draw the organisation it is given?
 *
 * WHY A NODE CHECK AND NOT A PYTHON TEST. Nothing changed on the server: the
 * tree is built in the browser from `reports_to`, which `position_table`
 * already returns on every row. So `bench run-tests` cannot reach any of this,
 * and the thing most likely to be wrong - a seat that silently disappears -
 * leaves no trace anywhere a server test can see.
 *
 * The three mistakes this is here to catch:
 *
 *   A SEAT THAT VANISHES. Every seat must appear exactly once, whatever shape
 *   the data is. One missing from a chart reads as "we do not have that role",
 *   which is a worse answer than drawing it in the wrong place.
 *
 *   A LOOP THAT HANGS THE BROWSER. The doctype refuses a seat that reports
 *   into its own chain, twice over, so this needs deliberately broken data to
 *   reach. It is checked because a frozen portal is a poor way to find out.
 *
 *   A FILTER THAT HIDES THE SHAPE. The filters grey rather than drop here
 *   (Surbhi, 15 Oct 2026), so a filtered tree must still hold every seat.
 *
 *     node scripts/check_positions_tree.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const PORTAL = path.join(__dirname, "..", "alvoraa_portal", "alvoraa_portal", "public",
                         "js", "ess", "portal.js");

/* ── a DOM just real enough ──────────────────────────────────────────────────
   Only the handful of elements the Positions panel touches. Everything else
   falls through to a proxy that absorbs whatever is done to it, so loading the
   rest of the portal cannot fail this check. */
function stub(name) {
  return new Proxy(function () {}, {
    get: (t, p) => (p === Symbol.toPrimitive || p === "toString") ? () => "" :
                   (p === "length" ? 0 : stub(name + "." + String(p))),
    apply: () => stub(name + "()"),
    construct: () => stub("new " + name),
    set: () => true,
  });
}

function makeContext(values) {
  const els = {};
  const el = (id) => (els[id] = els[id] || {
    id, value: values[id] || "", innerHTML: "", textContent: "",
    style: {}, checked: false,
  });
  ["pos-body", "pos-count", "pos-filter-note", "pos-f-branch", "pos-f-dept",
   "pos-f-role", "pos-f-open", "pos-f-view", "pos-add-btn",
   "pos-tiles", "pos-f-arrange", "pos-arrange-wrap"].forEach(el);

  const ctx = { console: { log() {}, warn() {}, error() {} } };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx; ctx.top = ctx;
  for (const g of ["frappe", "localStorage", "sessionStorage", "navigator",
                   "location", "history", "L", "Chart", "html2canvas", "moment"])
    ctx[g] = stub(g);
  ctx.document = {
    getElementById: (id) => (els[id] !== undefined ? els[id] : null),
    createElement: () => stub("el"),
    addEventListener() {}, removeEventListener() {},
    querySelector: () => null, querySelectorAll: () => [],
    body: stub("body"), documentElement: stub("html"),
  };
  ctx.addEventListener = () => {}; ctx.removeEventListener = () => {};
  ctx.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
  ctx.getComputedStyle = () => stub("cs");
  ctx.requestAnimationFrame = () => 0;
  ctx.setTimeout = () => 0; ctx.setInterval = () => 0;
  ctx.clearTimeout = () => {}; ctx.clearInterval = () => {};
  ctx.confirm = () => true; ctx.alert = () => {}; ctx.prompt = () => "";
  ctx.fetch = () => new Promise(() => {});
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(PORTAL, "utf8"), ctx, { filename: PORTAL });
  ctx.__els = els;
  return ctx;
}

/* ── the organisation under test ─────────────────────────────────────────────
   Shaped like DTC's: a head office seat, two stores under it, and staff under
   those. `outsider` reports to a seat this reader cannot see, which is every
   seat a branch head looks at. */
function seat(id, title, parent, extra) {
  return Object.assign({
    id, title, reports_to: parent || "",
    reports_to_title: parent ? parent.replace(/^P-/, "") : "",
    branch: "Sector 34", department: "Sales", designation: "", grade: "",
    company: "DTC", status: "Active", key: false,
    seats: 1, filled: 1, open: 0, people: [{ employee: "E", name: "A Person",
                                             weight: 100, covering: false }],
  }, extra || {});
}

const ROWS = [
  seat("P-Director", "Director", ""),
  seat("P-Sector34", "Store Manager", "P-Director"),
  seat("P-Ambala", "Store Manager Ambala", "P-Director", { branch: "Ambala" }),
  seat("P-Cashier", "Cashier", "P-Sector34",
       { seats: 3, filled: 2, open: 1, people: [] }),
  seat("P-Counter", "Counter Staff", "P-Sector34"),
  seat("P-Cleaner", "Housekeeping", "P-Ambala",
       { branch: "Ambala", department: "Back Office" }),
  // The branch-head case: a real parent that is outside what this reader sees.
  seat("P-Orphan", "Area Manager", "P-NotVisibleToMe"),
];

const problems = [];
let checks = 0;
function ok(what, cond, detail) {
  checks++;
  if (!cond) problems.push(what + (detail ? " - " + detail : ""));
}

function render(rows, values, collapsed, expanded) {
  const ctx = makeContext(Object.assign({ "pos-f-view": "tree" }, values || {}));
  ctx.POS.rows = rows;
  ctx.POS.may_edit = true;
  ctx.POS.collapsed = collapsed || {};
  ctx.POS.expanded = expanded || {};
  ctx.POS.onPath = {};
  ctx.POS.departments = (values && values.__departments) || {};
  ctx.posPaint();
  return {
    html: ctx.__els["pos-body"].innerHTML,
    tiles: ctx.__els["pos-tiles"].innerHTML,
    note: ctx.__els["pos-filter-note"].style.display,
  };
}

/* ── 1. every seat is drawn, exactly once ───────────────────────────────── */
{
  const out = render(ROWS);
  ROWS.forEach((r) => {
    // Counted by the card's own title span, which renders exactly once per
    // card. Counting the id double-counts now that an editor's card carries
    // it twice - once on the click, once on the Change button - and counting
    // a bare title caught the "Reports to" text as well.
    const n = out.html.split('<span class="ti">' + r.title + "</span>").length - 1;
    ok("every seat appears exactly once", n === 1,
       r.title + " appears " + n + " time(s)");
  });
}

/* ── 2. it is drawn as the organisation chart, not as a table ───────────── */
{
  const out = render(ROWS);
  // The point of the rewrite. An indented table read as a list with arrows on
  // it; these are the chart's own classes, so the two screens cannot drift
  // into drawing a hierarchy two different ways.
  ok("drawn with the chart's boxes", out.html.includes('class="oc-box'));
  ok("drawn with the chart's connectors", out.html.includes('class="oc-kids"'));
  ok("wrapped as a chart", out.html.includes('class="oc-tree"'));
  ok("not a table", !out.html.includes("<table"));

  // Nesting is now structural: a child's markup sits INSIDE its parent's
  // branch, so "under" is in the document rather than in a padding number.
  const parent = out.html.indexOf(">Store Manager<");
  const kids = out.html.indexOf('class="oc-kids"', parent);
  const child = out.html.indexOf(">Cashier<");
  ok("a child sits inside its parent's branch",
     kids > parent && child > kids);
}

/* ── 3. a seat whose parent is out of view says so ──────────────────────── */
{
  const out = render(ROWS);
  ok("a seat reporting above the reader's view is marked",
     out.html.includes("reports above your view"));
  // And only that one. Saying it on a genuine top-level seat would be a lie.
  ok("a genuine top seat is not marked",
     out.html.split("reports above your view").length - 1 === 1);
}

/* ── 4. a filter greys, it does not hide ────────────────────────────────── */
{
  const out = render(ROWS, { "pos-f-branch": "Ambala" });
  // A filter must not make a MATCH disappear. Seats it does not match are
  // greyed where they are drawn and folded where they are deep - folded is
  // not hidden, because the card that holds them says how many it has.
  ROWS.forEach((r) => {
    ok("a filter hides nothing", out.html.includes(">" + r.title),
       r.title + " disappeared when filtering to Ambala");
  });
  ok("non-matching seats are greyed", out.html.includes("opacity:.45"));
  // The count used to be grey text counting the WHOLE company whatever the
  // filter said. It is three tiles now, computed over the filtered rows.
  ok("the tiles are drawn", /oc-stat|pf-card/.test(out.tiles),
     "tiles read: " + out.tiles.slice(0, 80));
  ok("the greying is explained on screen", out.note !== "none");
}

/* ── 5. a closed branch says what it is covering up ─────────────────────── */
{
  const out = render(ROWS, {}, { "P-Sector34": true });
  ok("a closed branch hides its children",
     !out.html.includes(">Cashier<"));
  // The chart puts the count on the toggle itself, which is better than the
  // text the old table appended - it is visible without reading the row.
  ok("a closed branch says how many are below it",
     /<span class="c">2<\/span>/.test(out.html),
     "expected the toggle to carry the count 2");
  ok("a closed branch offers a way back in",
     out.html.includes("oc-more") || out.html.includes("oc-toggle"));
}

/* ── 6. the list view still filters rather than greys ───────────────────── */
{
  const out = render(ROWS, { "pos-f-view": "list", "pos-f-branch": "Ambala" });
  ok("the list drops what does not match", !out.html.includes(">Cashier"));
  ok("the list keeps what does match", out.html.includes(">Housekeeping"));
  ok("the greying note is hidden in the list", out.note === "none");
}

/* ── 7. a loop neither hangs nor swallows a seat ─────────────────────────── */
{
  // Deliberately impossible data: the doctype refuses this both ways. If it
  // ever reaches the browser, these two seats must still be visible.
  const looped = [
    seat("P-A", "Loop One", "P-B"),
    seat("P-B", "Loop Two", "P-A"),
    seat("P-Fine", "Normal Seat", ""),
  ];
  const out = render(looped);
  ok("a loop does not hide its seats",
     out.html.includes(">Loop One") && out.html.includes(">Loop Two"));
  ok("a loop is named as the problem it is",
     out.html.includes("report in a circle"));
  ok("the rest of the chart still draws", out.html.includes(">Normal Seat"));
}

/* ── 8. a very deep chain stops, and says it stopped ────────────────────── */
{
  const deep = [];
  for (let i = 0; i < 60; i++) {
    deep.push(seat("P-" + i, "Level " + i, i ? "P-" + (i - 1) : ""));
  }
  const out = render(deep);
  ok("a chain deeper than makes sense is cut off",
     out.html.includes("deeper than makes sense"));
  ok("the shallow end still draws", out.html.includes(">Level 0"));
}

/* ── 9. no edit column for a reader who may not edit ────────────────────── */
{
  const ctx = makeContext({ "pos-f-view": "tree" });
  ctx.POS.rows = ROWS;
  ctx.POS.may_edit = false;
  ctx.POS.collapsed = {};
  ctx.posPaint();
  const html = ctx.__els["pos-body"].innerHTML;
  ok("a reader who may not edit gets no Change button",
     !html.includes("posOpenEditor"));
  ok("but still sees the chart", html.includes('class="oc-box'));
  // And clicking a box must still DO something for them. Since slice 064 a
  // seat opens its tray for every reader; folding keeps its own button.
  ok("a reader's click opens the seat tray", html.includes("posSeatSheet("));
  ok("and a reader can still fold a branch", html.includes("posToggle("));
}

/* ── 10. an editor's click opens the seat tray ──────────────────────────── */
{
  const out = render(ROWS);
  ok("an editor's click opens the seat tray (Change is inside it)",
     out.html.includes("posSeatSheet('P-Cashier')") || out.html.includes("posSeatSheet(&#39;P-Cashier&#39;)"),
     out.html.match(/onclick="[^"]*P-Cashier[^"]*"/) && out.html.match(/onclick="[^"]*P-Cashier[^"]*"/)[0]);
  // There is no separate Change button any more. The card IS the button, so
  // a second one said the same thing twice - and once the card became a real
  // <button>, the nested one was invalid HTML and the browser hoisted it out
  // to float below the card. A screenshot showed that; nothing else could.
  ok("and there is no second button saying the same thing",
     !out.html.includes(">Change<"));
}

/* ── 11. identical siblings draw as one box ─────────────────────────────── */
{
  // Five Sales Executives in one shop under one manager. At the first tenant
  // this is twenty-five, which is twenty-five boxes saying one thing.
  const many = [seat("P-Boss", "Store Manager", "")];
  for (let i = 1; i <= 5; i++) {
    many.push(seat("P-SE" + i, "Sales Executive", "P-Boss", {
      people: [{ employee: "E" + i, name: "Person " + i,
                 weight: 100, covering: false }],
    }));
  }
  const out = render(many);

  ok("the five draw as one box",
     out.html.split('<span class="ti">Sales Executive</span>').length - 1 === 1,
     "expected one card, not five");
  ok("the box says how many it stands for",
     out.html.includes("5 of these"));

  // The whole risk of grouping: somebody vanishing into a tidy box. Only
  // three names are drawn now - a 25-person seat was 25 lines - so what has
  // to hold is that the rest are COUNTED, never silently dropped.
  for (let i = 1; i <= 3; i++) {
    ok("the first names are drawn",
       out.html.includes("Person " + i), "Person " + i + " is not drawn");
  }
  ok("and the rest are counted, not dropped",
     out.html.includes("+2 more in this seat"),
     "five people, three shown, so two must be counted");
  ok("a group offers a way into its seats", out.html.includes("posUngroup("));
  ok("and no Change button, because there is no single seat to change",
     !/posOpenEditor\('P-SE/.test(out.html));
}

/* ── 12. a role with people under it is never folded in with another ────── */
{
  // Two "Supervisor" seats, one of which has a report. Merging them would
  // merge their teams, which is a different organisation from the real one.
  const risky = [
    seat("P-Top", "Director", ""),
    seat("P-S1", "Supervisor", "P-Top"),
    seat("P-S2", "Supervisor", "P-Top"),
    seat("P-Under", "Their Report", "P-S1"),
  ];
  const out = render(risky);
  ok("the one with a team is drawn on its own",
     out.html.split('<span class="ti">Supervisor</span>').length - 1 === 2,
     "both Supervisors must be separate cards");
  ok("and its report is still under it", out.html.includes(">Their Report<"));
}

/* ── 13. a group a filter does not touch is greyed, not emptied ─────────── */
{
  const mixed = [
    seat("P-Boss2", "Store Manager", ""),
    seat("P-A1", "Clerk", "P-Boss2", { branch: "Ambala" }),
    seat("P-A2", "Clerk", "P-Boss2", { branch: "Ambala" }),
  ];
  const out = render(mixed, { "pos-f-branch": "Noida" });
  ok("a group matching nothing is greyed", out.html.includes("opacity:.45"));
  ok("but it is still drawn", out.html.includes(">Clerk<"));
}

/* ── 14. the three filters narrow each other ────────────────────────────── */
{
  // A filter that can be set to a combination returning nothing teaches
  // people not to trust it.
  const mix = [
    seat("P-H", "Head", "", { branch: "Ambala", designation: "Head" }),
    seat("P-C", "Clerk", "P-H", { branch: "Ambala", designation: "Clerk" }),
    seat("P-D", "Driver", "P-H", { branch: "Noida", designation: "Driver" }),
  ];

  const ctx = makeContext({ "pos-f-view": "tree", "pos-f-branch": "Ambala" });
  ctx.POS.rows = mix;
  ctx.POS.may_edit = true;
  ctx.POS.collapsed = {};
  ctx.POS.ungrouped = {};
  ctx.posPaint();

  const roles = ctx.__els["pos-f-role"].innerHTML;
  ok("picking a branch narrows the job roles",
     roles.includes("Clerk") && !roles.includes("Driver"),
     "the role list must only offer roles that exist in Ambala");

  // And the branch list must NOT narrow itself, or it would offer exactly
  // the one option already chosen and could never be changed back.
  const branches = ctx.__els["pos-f-branch"].innerHTML;
  ok("the branch list does not narrow itself",
     branches.includes("Noida"),
     "a list that filtered itself could never be changed back");
}

/* ── 15. somebody working their notice ──────────────────────────────────── */
{
  // Nothing is stored for this. Somebody is on notice when they are still
  // Active and their last day is already known - so the chart can tell "full"
  // apart from "full until the 30th", which it could not before.
  const notice = [
    seat("P-Mgr", "Store Manager", "", {
      leaving_on: "2026-11-30",
      people: [{ employee: "E9", name: "Leaving Soon",
                 weight: 100, covering: false, leaving: "2026-11-30" }],
    }),
    seat("P-Staff", "Counter Staff", "P-Mgr"),
  ];
  const out = render(notice);
  ok("the person is marked as leaving", out.html.includes("leaving 30 Nov"));
  ok("and the seat carries it as a flag",
     (out.html.match(/leaving 30 Nov/g) || []).length >= 2,
     "expected it on the person AND on the seat");
  ok("the full date is kept for hovering", out.html.includes("2026-11-30"));
  ok("a seat nobody is leaving says nothing about it",
     out.html.indexOf(">Counter Staff<") > 0
     && !/Counter Staff[\s\S]{0,400}leaving/.test(out.html));
}

/* ── 16. a group must not hide the one person leaving ───────────────────── */
{
  const many = [seat("P-B3", "Head", "")];
  for (let i = 1; i <= 4; i++) {
    many.push(seat("P-G" + i, "Packer", "P-B3", {
      people: [{ employee: "G" + i, name: "Packer " + i,
                 weight: 100, covering: false,
                 leaving: i === 2 ? "2026-12-15" : null }],
      leaving_on: i === 2 ? "2026-12-15" : null,
    }));
  }
  const out = render(many);
  ok("the four draw as one box",
     out.html.split('<span class="ti">Packer</span>').length - 1 === 1);
  ok("and the box says somebody is leaving",
     out.html.includes("1 leaving"),
     "three settled people must not hide the fourth");
  ok("the person is still named with their date",
     out.html.includes("leaving 15 Dec"));
}

/* ── 17. arranged by branch ─────────────────────────────────────────────── */
{
  // The same seats, a different spine. Surbhi: the chart "is just a
  // representation" of reporting, branch or department.
  const mixed = [
    seat("P-Top5", "Director", "", { branch: "Ambala", department: "Head" }),
    seat("P-C1", "Cashier", "P-Top5", { branch: "Ambala", department: "Sales" }),
    seat("P-C2", "Cashier", "P-Top5", { branch: "Noida", department: "Sales" }),
    seat("P-NB", "Floating Seat", "P-Top5", { branch: "", department: "" }),
  ];
  const out = render(mixed, { "pos-f-view": "tree", "pos-f-arrange": "branch" });

  ok("branches become the top layer", out.html.includes(">Ambala<"));
  ok("every branch is there", out.html.includes(">Noida<"));
  ok("a seat with no branch is named, not dropped",
     out.html.includes("No branch"),
     "nothing is allowed to fall off the chart");
  // Branches start closed - "arrange by branch" is a request to see the
  // branches, and opening all of them lays every seat across one row. What
  // is folded says how much it holds.
  ok("a closed branch says how many seats it holds",
     /<span class="c">\d+<\/span>/.test(out.html),
     "folded is only acceptable when it says how much");

  const opened = render(mixed,
    { "pos-f-view": "tree", "pos-f-arrange": "branch" },
    {}, { "br:Ambala": true });
  ok("opening a branch shows its seats",
     opened.html.includes(">Cashier<"));
  // A branch is not a seat, so it must not offer to be edited.
  ok("a branch cannot be opened as a seat",
     !/posOpenEditor\('br:/.test(out.html));
}

/* ── 18. arranged by department, which IS a tree ────────────────────────── */
{
  // Branch is a flat list in ERPNext; Department carries parent_department.
  // So this one nests for real, and the ancestors have to be built even
  // where no seat sits directly in them.
  const rows = [
    seat("P-D1", "Analyst", "", { branch: "Ambala", department: "Payroll - X" }),
    seat("P-D2", "Clerk", "", { branch: "Ambala", department: "Accounts - X" }),
  ];
  const out = render(rows, {
    "pos-f-view": "tree", "pos-f-arrange": "department",
    __departments: {
      "Payroll - X": { parent: "Finance - X", head: null },
      "Accounts - X": { parent: "Finance - X", head: "Asha Head" },
      "Finance - X": { parent: null, head: null },
    },
  });

  ok("the parent department is built even with no seat in it",
     out.html.includes(">Finance<"),
     "otherwise the tree starts halfway up");

  const open2 = render(rows, {
    "pos-f-view": "tree", "pos-f-arrange": "department",
    __departments: {
      "Payroll - X": { parent: "Finance - X", head: null },
      "Accounts - X": { parent: "Finance - X", head: "Asha Head" },
      "Finance - X": { parent: null, head: null },
    },
  }, {}, { "dp:Finance - X": true, "dp:Accounts - X": true,
           "dp:Payroll - X": true });
  ok("its children are under it", open2.html.includes(">Payroll<")
     && open2.html.includes(">Accounts<"));
  ok("the seats are under those", open2.html.includes(">Analyst<"));
  ok("a department head is shown as a person",
     open2.html.includes("Asha Head"));
}

/* ── 19. a branch keeps its own reporting lines ─────────────────────────── */
{
  // Arranging by branch changes what the TOP of the chart is, not whether
  // the shop has a manager. A flat list of seats inside a branch would
  // throw away the thing the chart is for.
  const inside = [
    seat("P-HO", "Head Office Boss", "", { branch: "Head Office" }),
    seat("P-SM", "Store Manager", "P-HO", { branch: "Ambala" }),
    seat("P-CA", "Cashier", "P-SM", { branch: "Ambala" }),
    seat("P-CB", "Cleaner", "P-SM", { branch: "Ambala" }),
  ];
  const out = render(inside,
    { "pos-f-view": "tree", "pos-f-arrange": "branch" },
    {}, { "br:Ambala": true });

  ok("the branch is a top-level box", out.html.includes(">Ambala<"));
  ok("its manager is inside it", out.html.includes(">Store Manager<"));
  ok("and the manager's people are under the MANAGER, not loose in the branch",
     out.html.indexOf('class="oc-kids"', out.html.indexOf(">Store Manager<")) > 0
     && out.html.includes(">Cashier<"),
     "a flat list inside a branch throws away the reporting line");

  // The manager's own boss is in another branch, so this branch starts at
  // the manager rather than dragging Head Office in behind him.
  const ambala = out.html.slice(out.html.indexOf(">Ambala<"));
  ok("a manager whose own boss is elsewhere starts this branch",
     !ambala.slice(0, ambala.indexOf(">Head Office<") + 1 || undefined)
            .includes(">Head Office Boss<"),
     "another branch's line must not be dragged in");

  ok("a folded branch counts every seat in the line, not just the top one",
     /<span class="c">3<\/span>/.test(
       render(inside, { "pos-f-view": "tree", "pos-f-arrange": "branch" }).html)
     || /3 seats/.test(
       render(inside, { "pos-f-view": "tree", "pos-f-arrange": "branch" }).html),
     "Ambala holds a manager and two people under him");
}

/* ── 20. deleting a seat ────────────────────────────────────────────────── */
// The server decides (Frappe's Delete right, and no seat with a past); the
// page only offers the button when told, names the seat before deleting, and
// shows the server's own words when it refuses.
async function deleteChecks() {
  const src = fs.readFileSync(PORTAL, "utf8");
  ok("the Delete button follows the server's may_delete",
     /pos-delete-btn[\s\S]{0,120}\(r && POS\.may_delete\)/.test(src));

  function deleteContext(mayDelete, answer) {
    const ctx = makeContext({});
    ctx.__els["pos-e-name"] = { id: "pos-e-name", value: "P-Cashier" };
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
    ctx.POS.rows = ROWS;
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
    ok("and names the seat", t.ctx.__els["pos-delete-text"].textContent.includes("Cashier"));
    t.opened.add("pos-editor");
    await t.ctx.posDelete();
    ok("a deleted seat closes both dialogs",
       !t.opened.has("pos-delete") && !t.opened.has("pos-editor"));
    ok("and says so", t.toasts.length === 1 && t.toasts[0].textContent.includes("was deleted"));
  }
  {
    const said = "Cashier still has people in it. Take them out of the seat first.";
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

/* ── 21. the trays kept from slice 064, on the original chart ──────────── */
function trayContext(opts) {
  const ctx = makeContext({});
  const focused = [];
  ctx.__els["pos-layer"] = { id: "pos-layer", innerHTML: "", style: {} };
  ctx.__els["pos-sh-t"] = { id: "pos-sh-t", focus() { focused.push("pos-sh-t"); } };
  ctx.__els["back-here"] = { id: "back-here", focus() { focused.push("back-here"); } };
  ctx.document.activeElement = ctx.__els["back-here"];
  ctx.POS.rows = opts.rows || ROWS;
  ctx.POS.may_edit = !!opts.may_edit;
  ctx.POS.may_edit_employee = !!opts.may_edit_employee;
  ctx.POS.unseated = opts.unseated === undefined ? null : opts.unseated;
  ctx.POS.active_people = opts.active || 0;
  ctx.POS.today = "2026-10-22";
  return { ctx, focused, layer: () => ctx.__els["pos-layer"].innerHTML };
}
{
  const t = trayContext({ may_edit: true });
  t.ctx.posSeatSheet("P-Sector34");
  const h = t.layer();
  ok("the seat tray opens as a modal dialog with a heading",
     h.includes('role="dialog"') && h.includes('aria-modal="true"') && h.includes('aria-labelledby="pos-sh-t"'));
  ok("it has a backdrop that closes it", h.includes('class="pos-scrim" onclick="posCloseSheet()"'));
  ok("it says who is in the seat", h.includes("Who is in it") && h.includes("A Person"));
  ok("it says where the seat reports", h.includes("reports to Director"));
  ok("an editor gets Change this seat", h.includes("Change this seat"));
  ok("focus moves to the tray's heading", t.focused.includes("pos-sh-t"));
  ok("the page remembers the tray is open", t.ctx.POS.sheet && t.ctx.POS.sheet.id === "P-Sector34");
  t.ctx.posCloseSheet();
  ok("closing empties the layer", t.layer() === "");
  ok("and puts focus back where it was", t.focused[t.focused.length - 1] === "back-here");
}
{
  const t = trayContext({ may_edit: false });
  t.ctx.posSeatSheet("P-Cashier");
  ok("a reader's tray has no Change and no Advertise",
     !t.layer().includes("Change this seat") && !t.layer().includes("Advertise it"));
  ok("an empty seat says so", t.layer().includes("Nobody is in this seat."));
}
{
  const t = trayContext({ may_edit: true });
  t.ctx.posSeatSheet("P-Orphan");
  ok("a seat whose parent is out of view says so", t.layer().includes("reports to a seat above your view"));
}
{
  // Without HR scope the server sends no lists: no tiles, and the trays refuse.
  const ctx = makeContext({ "pos-f-view": "tree" });
  ctx.POS.rows = ROWS; ctx.POS.unseated = null; ctx.posPaint();
  ok("no people tiles without the lists", !ctx.__els["pos-tiles"].innerHTML.includes("IN NO SEAT"));
  const t = trayContext({ unseated: null });
  t.ctx.posNoMgrSheet(); t.ctx.posUnseatedSheet();
  ok("and neither people tray opens", t.layer() === "");
}
{
  const people = [
    { employee: "HR-EMP-1", name: "Ravi", job_role: "Cashier", branch: "Sector 34", joined: "2026-10-01", no_manager: true },
    { employee: "HR-EMP-2", name: "Asha", job_role: "Cleaner", branch: "Noida", joined: "2025-01-01", no_manager: false },
  ];
  const rows = ROWS.map((r) => (r.id === "P-Cashier" ? Object.assign({}, r, { designation: "Cashier" }) : r))
    .concat([seat("P-Loose", "Loose Seat", "")]);
  const ctx = makeContext({ "pos-f-view": "tree" });
  ctx.POS.rows = rows; ctx.POS.unseated = people; ctx.posPaint();
  const tiles = ctx.__els["pos-tiles"].innerHTML;
  ok("HR see the two people tiles", tiles.includes("IN NO SEAT") && tiles.includes("NO REPORTING MANAGER"));
  ok("each opens its tray", tiles.includes("posUnseatedSheet()") && tiles.includes("posNoMgrSheet()"));

  const t = trayContext({ unseated: people, rows: rows, active: 10 });
  t.ctx.posNoMgrSheet();
  let h = t.layer();
  ok("No reporting manager lists only people with no manager", h.includes("Ravi") && !h.includes("Asha"));
  ok("and the second parentless seat, not the top", h.includes("Loose Seat") && !h.includes(">Director"));
  ok("no Set manager link without Employee write", !h.includes("Set manager"));
  t.ctx.posCloseSheet(true);
  const t2 = trayContext({ unseated: people, rows: rows, active: 10, may_edit_employee: true });
  t2.ctx.posNoMgrSheet();
  ok("Set manager appears with Employee write", t2.layer().includes("/app/employee/HR-EMP-1"));

  t.ctx.posUnseatedSheet();
  h = t.layer();
  ok("In no seat counts against the active people", h.includes("2 of 10 active people"));
  ok("and groups by branch", h.includes("Sector 34 · 1") && h.includes("Noida · 1"));
  ok("a matching seat opens its own tray", h.includes("posSeatSheet('P-Cashier')"));
  ok("a branch with no seat says so", h.includes("There is no seat at Noida."));
}

deleteChecks().then(() => {
  if (problems.length) {
    console.error("positions tree: " + problems.length + " problem(s)");
    problems.forEach((p) => console.error("  FAIL " + p));
    process.exit(1);
  }
  console.log("positions tree: " + checks + " checks - every seat drawn, "
              + "identical siblings grouped without losing anybody, filters "
              + "grey, loops and deep chains survive, a seat is deleted only "
              + "when the server says so, a seat opens its tray, the people "
              + "trays only for HR");
});
