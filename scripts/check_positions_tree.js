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

const PORTAL = path.join("alvoraa_portal", "alvoraa_portal", "public", "js",
                         "ess", "portal.js");

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
   "pos-tiles"].forEach(el);

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
  // And clicking a box must still DO something for them. Pointing their click
  // at an editor-only handler would mean it silently did nothing.
  ok("a reader's click still folds the branch",
     html.includes("posToggle("));
}

/* ── 10. an editor's click opens the seat ───────────────────────────────── */
{
  const out = render(ROWS);
  ok("an editor's click opens the seat", out.html.includes("posOpenEditor("));
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

if (problems.length) {
  console.error("positions tree: " + problems.length + " problem(s)");
  problems.forEach((p) => console.error("  FAIL " + p));
  process.exit(1);
}
console.log("positions tree: " + checks + " checks - every seat drawn, "
            + "identical siblings grouped without losing anybody, filters "
            + "grey, loops and deep chains survive");
