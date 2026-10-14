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
   "pos-f-open", "pos-f-view", "pos-add-btn"].forEach(el);

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
function ok(what, cond, detail) {
  if (!cond) problems.push(what + (detail ? " - " + detail : ""));
}

function render(rows, values, collapsed) {
  const ctx = makeContext(Object.assign({ "pos-f-view": "tree" }, values || {}));
  ctx.POS.rows = rows;
  ctx.POS.may_edit = true;
  ctx.POS.collapsed = collapsed || {};
  ctx.posPaint();
  return {
    html: ctx.__els["pos-body"].innerHTML,
    count: ctx.__els["pos-count"].textContent,
    note: ctx.__els["pos-filter-note"].style.display,
  };
}

/* ── 1. every seat is drawn, exactly once ───────────────────────────────── */
{
  const out = render(ROWS);
  ROWS.forEach((r) => {
    // By id, not by title: a parent's title legitimately appears again in
    // each child's "Reports to" cell, so counting titles counted those too.
    const n = out.html.split("posOpenEditor('" + r.id + "')").length - 1;
    ok("every seat appears exactly once", n === 1,
       r.title + " appears " + n + " time(s)");
  });
}

/* ── 2. children are indented under their parent ────────────────────────── */
{
  const out = render(ROWS);
  const at = (t) => out.html.indexOf(">" + t);
  ok("a child is drawn after its parent", at("Cashier") > at("Store Manager"));
  // The indent is the only thing that says "under". Depth 2 must be wider
  // than depth 1, or the tree reads as a flat list with arrows on it.
  const width = (t) => {
    const seg = out.html.slice(0, at(t));
    const m = [...seg.matchAll(/padding-left:(\d+)px/g)];
    return m.length ? Number(m[m.length - 1][1]) : -1;
  };
  ok("a child is indented further than its parent",
     width("Cashier") > width("Store Manager"),
     "child " + width("Cashier") + "px vs parent " + width("Store Manager") + "px");
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
  ROWS.forEach((r) => {
    ok("a filter hides nothing", out.html.includes(">" + r.title),
       r.title + " disappeared when filtering to Ambala");
  });
  ok("non-matching seats are greyed", out.html.includes("opacity:.45"));
  ok("the count says how many match", /\bmatch\b/.test(out.count),
     "count read: " + out.count);
  ok("the greying is explained on screen", out.note !== "none");
}

/* ── 5. a closed branch says what it is covering up ─────────────────────── */
{
  const out = render(ROWS, {}, { "P-Sector34": true });
  ok("a closed branch hides its children",
     !out.html.includes(">Cashier"));
  ok("a closed branch reports the seats below it",
     out.html.includes("2 below"), "expected '2 below'");
  ok("a closed branch reports the vacancies below it",
     /2 below, 1 open/.test(out.html),
     "a collapsed branch must not hide a vacancy");
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
  // The notices span the table, so a narrower table needs a narrower span.
  ok("a notice spans the narrower table", !html.includes('colspan="8"'));
}

if (problems.length) {
  console.error("positions tree: " + problems.length + " problem(s)");
  problems.forEach((p) => console.error("  FAIL " + p));
  process.exit(1);
}
console.log("positions tree: every seat drawn, filters grey, loops and deep "
            + "chains survive");
